"""Data audit for the raw COE file (B2) — stdlib only, independent of the DuckDB pipeline by design.

Profiles data/raw/coe-bidding-results.csv, resolves the spec [VERIFY]s against the
live file, and prints the receipts that feed docs/data_audit.md.

Run (repo root):  python src/audit.py
"""
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw/coe-bidding-results.csv"

CATS = ["Category A", "Category B", "Category C", "Category D", "Category E"]
MONTH = re.compile(r"^(\d{4})-(\d{2})$")


def num(v):
    return int(v.replace(",", ""))


def midx(m):
    return int(m[:4]) * 12 + int(m[5:]) - 1


def main():
    with RAW.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    print(f"== shape: {len(rows)} rows · {len(rows[0])} fields: {list(rows[0].keys())} ==")
    months = sorted({r["month"] for r in rows})
    ex = defaultdict(set)
    for r in rows:
        ex[(r["month"], r["bidding_no"])].add(r["vehicle_class"])
    print(f"months: {months[0]} → {months[-1]} ({len(months)} distinct) · exercises: {len(ex)} "
          f"· rounds per month: {sorted(set(Counter(m for m, _ in ex).values()))}")
    print(f"categories: {sorted({r['vehicle_class'] for r in rows})}")

    # [VERIFY] 1 — round structure
    print("\n== [VERIFY] round structure ==")
    rp = Counter(r["bidding_no"] for r in rows)
    print(f"  bidding_no values: {dict(sorted(rp.items()))} — both rounds live in the single CSV "
          f"(no separate round-1/round-2 files)")
    # [VERIFY] 2 — category completeness
    sizes = Counter(len(v) for v in ex.values())
    print("\n== [VERIFY] category completeness ==")
    print(f"  exercises with exactly 5 categories: {sizes.get(5, 0)} of {len(ex)} "
          f"(other sizes: {[k for k in sizes if k != 5] or 'none'})")
    percat = Counter(r["vehicle_class"] for r in rows)
    print(f"  rows per category: {dict(sorted(percat.items()))}")
    for c in CATS:
        miss = [m for m, s in ((k[0], v) for k, v in ex.items()) if c not in s]
        print(f"  {c}: missing in {len(set(miss))} months")
    # month gaps
    gaps = []
    for a, b in zip(months, months[1:]):
        if midx(b) - midx(a) != 1:
            gaps.append((a, b))
    print(f"  month gaps: {gaps} — the COVID bidding pause (no exercises Apr–Jun 2020)")

    # value ranges + dirty cells
    print("\n== ranges (comma-stripped) ==")
    for f_ in ("quota", "bids_success", "bids_received", "premium"):
        vals = [num(r[f_]) for r in rows]
        commacells = sum(1 for r in rows if "," in r[f_])
        print(f"  {f_:<14} min {min(vals):>8,} max {max(vals):>8,} · comma-formatted cells: {commacells}")
    print("\nper-category premium ranges (S$):")
    for c in CATS:
        vals = [num(r["premium"]) for r in rows if r["vehicle_class"] == c]
        print(f"  {c:<12} min {min(vals):>7,} max {max(vals):>7,}")

    # integrity relationships
    print("\n== integrity ==")
    dup = Counter((r["month"], r["bidding_no"], r["vehicle_class"]) for r in rows)
    print(f"  duplicate keys: {sum(1 for v in dup.values() if v > 1)}")
    print(f"  bids_success > bids_received: {sum(1 for r in rows if num(r['bids_success']) > num(r['bids_received']))}")
    print(f"  bids_success > quota: {sum(1 for r in rows if num(r['bids_success']) > num(r['quota']))}")
    under = [r for r in rows if num(r["bids_received"]) < num(r["quota"])]
    print(f"  undersubscribed exercises (bids_received < quota): {len(under)}")
    for r in under:
        print(f"    {r['month']} R{r['bidding_no']} {r['vehicle_class']}: quota {r['quota']}, received {r['bids_received']}, success {r['bids_success']}")
    filled = sum(1 for r in rows if num(r["bids_success"]) == num(r["quota"]))
    print(f"  exercises where every certificate was taken (bids_success == quota): {filled} of {len(rows)}")
    print(f"  premium <= 0: {sum(1 for r in rows if num(r['premium']) <= 0)}")

    # definition break
    print("\n== definition break (A/B, May-2022) ==")
    for c in ("Category A", "Category B"):
        pre = [r for r in rows if r["vehicle_class"] == c and r["month"] == "2022-04" and r["bidding_no"] == "2"][0]
        post = [r for r in rows if r["vehicle_class"] == c and r["month"] == "2022-05" and r["bidding_no"] == "1"][0]
        print(f"  {c}: last old-definition {pre['month']} R{pre['bidding_no']} quota {pre['quota']} premium {num(pre['premium']):,} "
              f"→ first new {post['month']} R{post['bidding_no']} quota {post['quota']} premium {num(post['premium']):,}")

    # latest exercise
    print("\n== latest exercise ==")
    last = [r for r in rows if r["month"] == months[-1]]
    for r in sorted(last, key=lambda r: (r["bidding_no"], r["vehicle_class"])):
        bpq = num(r["bids_received"]) / num(r["quota"])
        sr = num(r["bids_success"]) / num(r["bids_received"])
        print(f"  {r['month']} R{r['bidding_no']} {r['vehicle_class']:<12} quota {num(r['quota']):>5,} "
              f"received {num(r['bids_received']):>5,} success {num(r['bids_success']):>5,} "
              f"premium {num(r['premium']):>7,} · bids/quota {bpq:.2f} · success {sr:.1%}")


if __name__ == "__main__":
    main()
