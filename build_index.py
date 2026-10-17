#!/usr/bin/env python3
"""Builds data/index.bin for BinderScan: a perceptual hash of every paper Magic card image on Scryfall.

Run by .github/workflows/build-index.yml. Images already hashed are kept in .cache/ between runs,
so only new cards are downloaded after the first build.

Index format (little-endian):
  16-byte header: b"BSIX", version u32, count u32, reserved u32
  count x 16 bytes  Scryfall card id (UUID bytes)
  count x 1 byte    face (0 = front, 1 = back), padded to a multiple of 4
  count x 4 u32     full-card pHash (2 words), art-box pHash (2 words)
The hash maths must match cardHash() in index.html.
"""
import concurrent.futures as cf
import gzip, io, json, os, struct, sys, time, traceback, urllib.request, uuid

import numpy as np
from PIL import Image

HN, HM = 128, 176                      # intermediate card size (63:88)
ART = (0.08, 0.11, 0.92, 0.56)         # art box as fractions: x0, y0, x1, y1
SKIP_LAYOUTS = {"art_series", "token", "double_faced_token", "emblem", "vanguard", "planar", "scheme"}
UA = {"User-Agent": "BinderScan-index-builder/1.0 (personal collection app)", "Accept": "application/json;q=0.9,*/*;q=0.8"}

D8 = np.array([[(np.sqrt(1 / 32) if k == 0 else np.sqrt(2 / 32)) * np.cos(np.pi * (2 * n + 1) * k / 64)
                for n in range(32)] for k in range(8)], dtype=np.float64)


def weights(a, b, n, length):
    """Area-average resampling matrix (n x length) for the span [a, b)."""
    m = np.zeros((n, length))
    step = (b - a) / n
    for i in range(n):
        lo, hi = a + step * i, a + step * (i + 1)
        for p in range(max(0, int(np.floor(lo))), min(length, int(np.ceil(hi)))):
            w = min(hi, p + 1) - max(lo, p)
            if w > 0:
                m[i, p] = w
        s = m[i].sum()
        if s:
            m[i] /= s
    return m


WF = (weights(0, HM, 32, HM), weights(0, HN, 32, HN))
WA = (weights(ART[1] * HM, ART[3] * HM, 32, HM), weights(ART[0] * HN, ART[2] * HN, 32, HN))


def phash(a):
    low = (D8 @ a @ D8.T).flatten()
    bits = low > np.median(low)
    w0 = sum(1 << j for j in range(32) if bits[j])
    w1 = sum(1 << j for j in range(32) if bits[32 + j])
    return w0, w1


def card_hash(im):
    im = im.convert("RGB").resize((HN, HM), Image.BICUBIC)
    a = np.asarray(im, dtype=np.float64)
    g = a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114
    return (*phash(WF[0] @ g @ WF[1].T), *phash(WA[0] @ g @ WA[1].T))


def fetch(url, tries=4, timeout=60):
    for t in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except Exception:
            if t == tries - 1:
                raise
            time.sleep(2 * (t + 1))


def note(msg):
    """Progress line that also shows up as an annotation on the workflow run."""
    print(f"::notice title=build_index::{msg}", flush=True)


def save_cache(cache, path):
    tmp = path + ".tmp"
    with gzip.open(tmp, "wt") as f:
        json.dump(cache, f)
    os.replace(tmp, path)


def find_download(bulk):
    """Locate the default_cards bulk file; Scryfall has changed this response's field names before."""
    items = bulk.get("data", bulk if isinstance(bulk, list) else [])
    entry = next((b for b in items if str(b.get("type", "")).replace("-", "_") == "default_cards"), None)
    if entry is None:
        raise RuntimeError("no default_cards entry; types: " + ", ".join(str(b.get("type")) for b in items))

    def pick(d):
        for k in ("download_uri", "download_url", "file_uri", "file_url"):
            if isinstance(d.get(k), str):
                return d[k]
        for k, v in d.items():
            if isinstance(v, str) and v.startswith("http") and ".json" in v and "api.scryfall.com/bulk-data" not in v:
                return v
        return None

    uri = pick(entry)
    if not uri and isinstance(entry.get("uri"), str):
        detail = json.loads(fetch(entry["uri"]))
        uri = pick(detail)
        if not uri:
            raise RuntimeError("no download link; fields: " + ", ".join(f"{k}={str(v)[:60]}" for k, v in detail.items()))
    if not uri:
        raise RuntimeError("no download link; fields: " + ", ".join(f"{k}={str(v)[:60]}" for k, v in entry.items()))
    return uri


def main():
    import ijson
    root = os.path.dirname(os.path.abspath(__file__))
    data_dir, cache_dir = os.path.join(root, "data"), os.path.join(root, ".cache")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, "hashes.json.gz")
    cache = {}
    if os.path.exists(cache_path):
        with gzip.open(cache_path, "rt") as f:
            cache = json.load(f)
    note(f"cached hashes: {len(cache)}")

    bulk = json.loads(fetch("https://api.scryfall.com/bulk-data"))
    uri = find_download(bulk)
    cards_path = os.path.join(cache_dir, "default_cards.json")
    print("downloading", uri, flush=True)
    with urllib.request.urlopen(urllib.request.Request(uri, headers=UA), timeout=900) as r, open(cards_path, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)

    entries = []  # (card id, face, image url)
    with open(cards_path, "rb") as f:
        for c in ijson.items(f, "item"):
            if c.get("digital") or "paper" not in (c.get("games") or []):
                continue
            if c.get("layout") in SKIP_LAYOUTS or c.get("oversized") or c.get("image_status") in ("missing", "placeholder"):
                continue
            if c.get("image_uris"):
                entries.append((c["id"], 0, c["image_uris"]["small"]))
            else:
                for i, face in enumerate((c.get("card_faces") or [])[:2]):
                    if face.get("image_uris"):
                        entries.append((c["id"], i, face["image_uris"]["small"]))
    os.remove(cards_path)
    todo = [e for e in entries if e[2] not in cache]
    note(f"card images: {len(entries)}, new to hash: {len(todo)}")

    def work(e):
        try:
            return e[2], card_hash(Image.open(io.BytesIO(fetch(e[2]))))
        except Exception as ex:
            print("skipped", e[2], ex, file=sys.stderr)
            return e[2], None

    t0, done = time.time(), 0
    with cf.ThreadPoolExecutor(16) as pool:
        for url, h in pool.map(work, todo):
            if h:
                cache[url] = list(h)
            done += 1
            if done % 2000 == 0:
                print(f"{done}/{len(todo)} hashed, {time.time() - t0:.0f}s", flush=True)
                save_cache(cache, cache_path)

    keep = {e[2] for e in entries}
    cache = {k: v for k, v in cache.items() if k in keep}
    save_cache(cache, cache_path)

    rows = sorted((e for e in entries if e[2] in cache), key=lambda e: (e[0], e[1]))
    buf = bytearray(b"BSIX" + struct.pack("<III", 1, len(rows), 0))
    for e in rows:
        buf += uuid.UUID(e[0]).bytes
    buf += bytes(e[1] for e in rows)
    while len(buf) % 4:
        buf += b"\0"
    buf += np.array([cache[e[2]] for e in rows], dtype="<u4").tobytes()

    index_path = os.path.join(data_dir, "index.bin")
    old = open(index_path, "rb").read() if os.path.exists(index_path) else b""
    if bytes(buf) != old:
        with open(index_path, "wb") as f:
            f.write(buf)
        with open(os.path.join(data_dir, "meta.json"), "w") as f:
            json.dump({"version": 1, "count": len(rows), "built": int(time.time())}, f)
        note(f"index written: {len(rows)} card faces, {len(buf) / 1e6:.1f} MB")
    else:
        note("index unchanged")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        tb = traceback.format_exc().strip().splitlines()
        print("\n".join(tb), file=sys.stderr)
        msg = " | ".join(tb[-4:]).replace("%", "%25").replace("\r", "").replace("\n", " ")
        print(f"::error title=build_index failed::{msg}", flush=True)
        sys.exit(1)
