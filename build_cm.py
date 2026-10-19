#!/usr/bin/env python3
"""Builds data/cm.json: for every Cardmarket Magic single, its expansion and version number (V.n), so the app can
write exact Cardmarket wants-list lines like "1 Card Name (V.2) (Expansion Name)".

Cardmarket keeps showcase/borderless/extended printings in a separate "<Set>: Extras" expansion and numbers several
printings of the same card within one expansion V.1, V.2, … in the order they were added (by product id).

Expansion names come from MTGJSON's Cardmarket names. MTGJSON often lacks the "Extras" expansion of recent sets;
an unnamed expansion holding a set's showcase/borderless printings (per Scryfall) next to a main expansion MTGJSON
knows is named "<main name>: Extras". Expansions without a reliable name are left out (the app then copies the card
as any version).

Format: {"built": unix, "exp": {idExpansion: name}, "p": [[idProduct delta, idExpansion, v], ...]}.
"""
import collections, gzip, json, os, time, urllib.request
import build_index as BI   # Scryfall bulk-data helpers

UA = {"User-Agent": "Sleevescope-catalogue/1.0 (personal collection app)"}
VARIANT_EFFECTS = {"showcase", "extendedart", "inverted", "etched", "fullart"}
def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
        return json.loads(r.read())


def scryfall_by_cmid(cache_dir):
    """cardmarket_id → (set code, set name, is_variant_printing) from Scryfall's default_cards."""
    uri = BI.find_download(json.loads(BI.fetch("https://api.scryfall.com/bulk-data")))
    path = os.path.join(cache_dir, "cm_default_cards.json")
    with urllib.request.urlopen(urllib.request.Request(uri, headers=BI.UA), timeout=900) as r, open(path, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    gz = open(path, "rb").read(2) == b"\x1f\x8b"
    out = {}
    with (gzip.open(path, "rb") if gz else open(path, "rb")) as f:
        head = f.read(4096).lstrip()
    with (gzip.open(path, "rb") if gz else open(path, "rb")) as f:
        cards = BI.iter_json_lines(f) if head[:1] != b"[" else json.load(f)
        for c in cards:
            if not isinstance(c, dict) or not c.get("cardmarket_id"):
                continue
            variant = bool(set(c.get("frame_effects") or []) & VARIANT_EFFECTS) or c.get("border_color") == "borderless" \
                or bool(c.get("promo_types")) and "boosterfun" in c["promo_types"]
            out[int(c["cardmarket_id"])] = (c["set"], c["set_name"], variant)
    os.remove(path)
    return out


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    cache_dir = os.path.join(root, ".cache"); os.makedirs(cache_dir, exist_ok=True)
    base = "https://downloads.s3.cardmarket.com/productCatalog/productList/"
    singles = get_json(base + "products_singles_1.json")["products"]
    sets = get_json("https://mtgjson.com/api/v5/SetList.json")["data"]
    sf = scryfall_by_cmid(cache_dir)

    known = {}
    for s in sets:
        if s.get("mcmId") and s.get("mcmName"):
            known[int(s["mcmId"])] = s["mcmName"]
        if s.get("mcmIdExtras") and s.get("mcmName"):
            known[int(s["mcmIdExtras"])] = s.get("mcmNameExtras") or s["mcmName"] + ": Extras"

    # per Cardmarket expansion: which Scryfall set it mostly holds, and how many of its printings are showcase-style
    stats = collections.defaultdict(lambda: {"sets": collections.Counter(), "names": {}, "variant": 0, "n": 0})
    for p in singles:
        rec = sf.get(p["idProduct"])
        if rec:
            st = stats[p["idExpansion"]]
            st["sets"][rec[0]] += 1; st["names"][rec[0]] = rec[1]; st["variant"] += rec[2]; st["n"] += 1

    by_set = collections.defaultdict(list)
    for e, st in stats.items():
        if st["n"]:
            code = st["sets"].most_common(1)[0][0]
            by_set[code].append(e)

    # Only one kind of name is derived: an unnamed expansion that holds a set's showcase/borderless printings, next to
    # a main expansion MTGJSON knows, is that set's "<main name>: Extras" (Cardmarket's pattern, like ": Promos").
    derived = {}
    for code, exps in by_set.items():
        share = {e: stats[e]["variant"] / stats[e]["n"] for e in exps}
        mains = [e for e in exps if e in known and share[e] < 0.5 and not known[e].endswith((": Extras", ": Promos"))]
        extras = [e for e in exps if e not in known and share[e] >= 0.5]
        if len(mains) == 1 and len(extras) == 1:
            derived[extras[0]] = known[mains[0]] + ": Extras"
    explicit = [s.get("mcmNameExtras") for s in sets if s.get("mcmNameExtras")]
    print(f"::notice title=build_cm::{len(derived)} Extras expansions named from their main set; "
          f"MTGJSON's own Extras names (pattern check): {explicit[:6]}; derived examples: {list(derived.values())[-6:]}")

    exp = {**derived, **known}
    groups = collections.defaultdict(list)
    for p in singles:
        groups[(p["idExpansion"], p["name"])].append(p["idProduct"])
    version = {}
    for ids in groups.values():
        ids.sort()
        for i, pid in enumerate(ids):
            version[pid] = i + 1 if len(ids) > 1 else 0
    rows, last = [], 0
    for p in sorted(singles, key=lambda p: p["idProduct"]):
        rows.append([p["idProduct"] - last, p["idExpansion"], version[p["idProduct"]]])
        last = p["idProduct"]
    used = {p["idExpansion"] for p in singles}
    out_exp = {str(k): v for k, v in sorted(exp.items()) if k in used}
    recent = [p for p in singles if p["idProduct"] >= 850000]
    cov = sum(1 for p in recent if str(p["idExpansion"]) in out_exp) / max(1, len(recent))
    out = {"built": int(time.time()), "exp": out_exp, "p": rows}

    path = os.path.join(root, "data", "cm.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    old = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
    if old.get("p") != rows or old.get("exp") != out_exp:
        text = json.dumps(out, separators=(",", ":"), ensure_ascii=False)
        open(path, "w", encoding="utf-8").write(text)
        print(f"::notice title=build_cm::cm.json written: {len(rows)} products, {len(out_exp)} named expansions "
              f"({len(known)} from MTGJSON), recent-set coverage {100*cov:.0f}%, {len(text)/1e6:.1f} MB")
    else:
        print(f"::notice title=build_cm::cm.json unchanged, recent-set coverage {100*cov:.0f}%")


if __name__ == "__main__":
    main()
