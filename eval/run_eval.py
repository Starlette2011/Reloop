"""Score Reloop against hand-labeled cases.

Usage (from the repo root):  python eval/run_eval.py eval/cases.csv [--out eval/results.csv]

Compares two systems on the same cases:
  baseline : no location, so every answer is general guidance
  reloop   : the place you typed, so bundled city packs apply where they exist
Rows with a blank `expected` are skipped, so unlabeled rows never inflate the score.
"""
import argparse, csv, os, sys

os.environ.pop("ANTHROPIC_API_KEY", None)  # evaluate the rule engine only, not the AI
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi.testclient import TestClient
from server import app

ACTIONS = {"recycle", "compost", "trash", "dropoff"}
client = TestClient(app)

def ask(place, item):
    r = client.post("/api/classify", json={"place": place, "text": item})
    r.raise_for_status()
    return r.json()

def score(rows, use_place):
    n = right = safe = harmful = cautious = 0
    misses = []
    for r in rows:
        d = ask(r["place"] if use_place else "", r["item"])
        n += 1
        if d["safe"]:
            safe += 1
            if r["expected"] == "recycle":
                cautious += 1  # a recyclable item sent to trash
            misses.append((r, d))
        elif d["action"] == r["expected"]:
            right += 1
        else:
            if d["action"] == "recycle":
                harmful += 1  # told to recycle something that contaminates the load
            elif r["expected"] == "recycle":
                cautious += 1
            misses.append((r, d))
    return dict(n=n, right=right, safe=safe, harmful=harmful, cautious=cautious), misses

def pct(a, n):
    return f"{a / n:.0%}" if n else "n/a"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cases")
    ap.add_argument("--out", help="write every miss to this CSV")
    a = ap.parse_args()
    all_rows = list(csv.DictReader(open(a.cases, encoding="utf-8")))
    rows, bad = [], 0
    for r in all_rows:
        e = (r.get("expected") or "").strip().lower()
        if not e:
            continue
        if e not in ACTIONS:
            bad += 1
            print(f"Skipping '{r['place']} / {r['item']}': expected must be one of {sorted(ACTIONS)}, got '{e}'")
            continue
        r["expected"] = e
        rows.append(r)
    print(f"{len(rows)} labeled cases scored, {len(all_rows) - len(rows) - bad} unlabeled skipped, {bad} invalid skipped.")
    if not rows:
        sys.exit("Fill in the `expected` column from official city guides first.")
    results = {}
    for name, use_place in (("No location (baseline)", False), ("Reloop with city packs", True)):
        s, misses = score(rows, use_place)
        results[name] = (s, misses)
        print(f"\n{name}")
        print(f"  correct:                    {pct(s['right'], s['n'])} ({s['right']}/{s['n']})")
        print(f"  safe default (not sure):    {pct(s['safe'], s['n'])}")
        print(f"  HARMFUL (wrongly recycle):  {pct(s['harmful'], s['n'])} ({s['harmful']})")
        print(f"  too cautious (not recycled):{pct(s['cautious'], s['n'])} ({s['cautious']})")
    _, misses = results["Reloop with city packs"]
    if misses:
        print("\nMisses for Reloop with city packs (report these honestly):")
        for r, d in misses:
            print(f"  {r['place']} | {r['item']} | expected {r['expected']} | got {d['action']} ({d['scope']})")
    if a.out:
        with open(a.out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["place", "item", "expected", "got", "answer_source"])
            for r, d in misses:
                w.writerow([r["place"], r["item"], r["expected"], d["action"], d["scope"]])
        print(f"\nWrote {len(misses)} misses to {a.out}")

if __name__ == "__main__":
    main()
