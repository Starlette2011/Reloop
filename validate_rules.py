"""Validate rule packs. Run: python validate_rules.py  (used by tests and CI)"""
import glob, json, sys
ACTIONS = {"recycle", "compost", "trash", "dropoff"}
def problems():
    out, packs = [], {}
    for p in sorted(glob.glob("rules/*.json")):
        d = json.load(open(p, encoding="utf-8")); packs[p] = d
        for f in ("id", "name", "lang", "items"):
            if f not in d: out.append(f"{p}: missing {f}")
        if d.get("verified") and not d.get("source_url"): out.append(f"{p}: verified packs need source_url")
    g = next((d for d in packs.values() if d.get("id") == "global"), None)
    if not g: return out + ["rules/global.json missing"]
    for p, d in packs.items():
        for k, e in d.get("items", {}).items():
            if k not in g["items"]: out.append(f"{p}: unknown item key {k}")
            if len(e) != 4 or e[1] not in ACTIONS: out.append(f"{p}: bad entry {k}")
    return out
if __name__ == "__main__":
    pr = problems(); print("\n".join(pr) or "OK"); sys.exit(1 if pr else 0)
