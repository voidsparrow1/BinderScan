#!/usr/bin/env python3
"""Builds data/cm.json: for every Cardmarket Magic single, its expansion and version number (V.n), so the app can
write exact Cardmarket wants-list lines like "1 Card Name (V.2) (Expansion Name)".

Sources (both public): Cardmarket's product catalogue, and MTGJSON's set list for Cardmarket's expansion names.
Cardmarket keeps showcase/borderless/extended printings in a separate "<Set>: Extras" expansion, and numbers
several printings of the same card within one expansion as V.1, V.2, … in the order they were added (by product id).

Format: {"built": unix, "exp": {idExpansion: name}, "p": [[idProduct delta, idExpansion, v], ...]} with products
sorted by id and ids delta-encoded; v is 0 when the card has only one printing in that expansion.
"""
import collections, json, os, time, urllib.request

UA = {"User-Agent": "Sleevescope-catalogue/1.0 (personal collection app)"}


def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
        return json.loads(r.read())


def main():
    root = os.path.dirname(os.path.abspath(__file__))
    products = get_json("https://downloads.s3.cardmarket.com/productCatalog/productList/products_singles_1.json")["products"]
    sets = get_json("https://mtgjson.com/api/v5/SetList.json")["data"]

    exp = {}
    for s in sets:
        if s.get("mcmId") and s.get("mcmName"):
            exp[int(s["mcmId"])] = s["mcmName"]
        if s.get("mcmIdExtras") and s.get("mcmName"):
            exp[int(s["mcmIdExtras"])] = s.get("mcmNameExtras") or s["mcmName"] + ": Extras"

    groups = collections.defaultdict(list)
    for p in products:
        groups[(p["idExpansion"], p["name"])].append(p["idProduct"])
    version = {}
    for ids in groups.values():
        ids.sort()
        for i, pid in enumerate(ids):
            version[pid] = i + 1 if len(ids) > 1 else 0

    rows, last = [], 0
    for p in sorted(products, key=lambda p: p["idProduct"]):
        rows.append([p["idProduct"] - last, p["idExpansion"], version[p["idProduct"]]])
        last = p["idProduct"]
    used = {p["idExpansion"] for p in products}
    out = {"built": int(time.time()), "exp": {str(k): v for k, v in sorted(exp.items()) if k in used}, "p": rows}

    os.makedirs(os.path.join(root, "data"), exist_ok=True)
    path = os.path.join(root, "data", "cm.json")
    text = json.dumps(out, separators=(",", ":"), ensure_ascii=False)
    old = open(path, encoding="utf-8").read() if os.path.exists(path) else ""
    if json.loads(old or "{}").get("p") != rows or json.loads(old or "{}").get("exp") != out["exp"]:
        open(path, "w", encoding="utf-8").write(text)
        print(f"::notice title=build_cm::cm.json written: {len(rows)} products, {len(out['exp'])} named expansions, {len(text)/1e6:.1f} MB")
    else:
        print("::notice title=build_cm::cm.json unchanged")


if __name__ == "__main__":
    main()
