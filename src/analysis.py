"""S2 analysis runner — pressure metrics → jump events → descriptive attribution.

Run: python src/analysis.py   (from the repo root; reads data/processed/coe_exercises.parquet)

The core move: exercise-over-exercise changes per category. Premium moves are compared
with quota moves (supply) and bids-per-quota moves (count pressure) using Spearman rank
correlation on % changes — descriptive only, "associated with", never "caused".
The file contains bid counts, not bid values; premiums are set by the marginal
successful bid value, which is not observable here (stated everywhere it matters).

Sample discipline (counted, reconciled):
  - deltas exist for every exercise after a category's first: 395 per category;
  - the delta spanning the Apr–Jun 2020 pause is excluded (gap_spanning, 1/category);
  - for Categories A & B the delta crossing the May-2022 definition break is excluded
    (crosses_break); for C/D/E no definition changed, so the same-date delta stays.

Receipts printed:
  1. counts + flag reconciliation (retained + excluded)
  2. hand-checks: 3 dated cells recomputed from the RAW CSV with stdlib only
  3. identity asserts (metric + delta consistency)
  4. headline reads (latest exercise, top jumps, regime medians)
  5. attribution + sensitivity tables

Validation runs BEFORE any output file is written; a failing run leaves existing
outputs untouched. Writes: outputs/coe_pressure.csv · coe_jumps.csv ·
coe_attribution.csv · sensitivity.csv
"""
import csv
import os
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
PARQUET = (ROOT / "data/processed/coe_exercises.parquet").as_posix()
RAW = ROOT / "data/raw/coe-bidding-results.csv"
OUT = ROOT / "outputs"

CATS = ["Category A", "Category B", "Category C", "Category D", "Category E"]
AB = ("'Category A', 'Category B'")

# Sample predicates (counted + reconciled below)
BASE_SAMPLE = (f"d_premium_pct IS NOT NULL AND NOT gap_spanning "
               f"AND NOT (crosses_break AND category IN ({AB}))")
INCL_GAP_SAMPLE = (f"d_premium_pct IS NOT NULL "
                   f"AND NOT (crosses_break AND category IN ({AB}))")

HAND_CHECK_CELLS = [  # (month, round, category) — recomputed from the raw CSV, stdlib only
    ("2013-01", "1", "Category A"),
    ("2022-05", "2", "Category B"),
    ("2026-09", "2", "Category E"),
]


def q(con, sql):
    return con.sql(sql).fetchall()


def run_script(con, path):
    text = "\n".join(l.split("--", 1)[0] for l in Path(path).read_text(encoding="utf-8").splitlines())
    for stmt in text.split(";"):
        if stmt.strip():
            con.execute(stmt)


def num(v):
    return int(v.replace(",", ""))


def load_raw():
    """Raw CSV straight to a stdlib dict — the independent path for hand-checks."""
    with RAW.open(newline="", encoding="utf-8") as f:
        return {(r["month"], r["bidding_no"], r["vehicle_class"]): r for r in csv.DictReader(f)}


def attribution(con, sample, x="d_premium_pct", y_quota="d_quota_pct", y_bpq="d_bpq",
                rank=True, cats=None):
    """Per (category, regime): n + correlation of premium moves with quota moves and bpq moves.

    rank=True -> Spearman (corr of ranks); rank=False -> Pearson on the raw values.
    """
    cat_filter = f"AND category IN ({cats})" if cats else ""
    if rank:
        xr = "rank() OVER (PARTITION BY category, regime ORDER BY x)"
        qr = "rank() OVER (PARTITION BY category, regime ORDER BY yq)"
        br = "rank() OVER (PARTITION BY category, regime ORDER BY yb)"
    else:
        xr, qr, br = "x", "yq", "yb"
    return q(con, f"""
        WITH base AS (SELECT category, regime, {x} AS x, {y_quota} AS yq, {y_bpq} AS yb
                      FROM deltas WHERE {sample} {cat_filter}),
        ranked AS (SELECT category, regime, {xr} AS rp, {qr} AS rq, {br} AS rb FROM base)
        SELECT category, regime, count(*) AS n, corr(rp, rq) AS rho_quota, corr(rp, rb) AS rho_bpq
        FROM ranked GROUP BY category, regime ORDER BY category, regime""")


def write_csv(path, header, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"wrote: {path.as_posix()}  ({path.stat().st_size} bytes, {len(rows)} rows)")


def r(x, nd):
    return None if x is None else round(float(x), nd)


def main():
    os.chdir(ROOT)
    OUT.mkdir(exist_ok=True)
    con = duckdb.connect()
    con.execute(f"CREATE OR REPLACE VIEW exercise AS SELECT * FROM read_parquet('{PARQUET}')")
    failed = False

    print("== deltas (sql/02) ==")
    run_script(con, ROOT / "sql/02_metrics.sql")
    n_rows = q(con, "SELECT count(*) FROM exercise")[0][0]
    n_ex = q(con, "SELECT count(DISTINCT (month, round_no)) FROM exercise")[0][0]
    n_deltas = q(con, "SELECT count(*) FROM deltas")[0][0]
    per_cat = q(con, "SELECT category, count(*), count(d_premium) FROM deltas GROUP BY 1 ORDER BY 1")
    print(f"exercises: {n_ex} · rows: {n_rows} · deltas: {n_deltas} (first exercise per category has none)")
    for c, total, with_d in per_cat:
        print(f"   {c}: {total} rows · {with_d} deltas")

    # ---- flag reconciliation (counted exclusions) ----
    gap = q(con, "SELECT count(*) FROM deltas WHERE gap_spanning")[0][0]
    cross = q(con, "SELECT count(*) FROM deltas WHERE crosses_break")[0][0]
    base_n = q(con, f"SELECT count(*) FROM deltas WHERE {BASE_SAMPLE}")[0][0]
    excluded = n_deltas - 5 - base_n   # -5 first-rows have no delta at all
    print(f"flags: gap_spanning {gap} (expect 5) · crosses_break {cross} (expect 5)")
    print(f"attribution sample: {base_n} deltas kept of {n_deltas - 5} · excluded {excluded} "
          f"(gap 5 + A/B break-crossing 2)")
    ok_recon = gap == 5 and cross == 5 and base_n == (n_deltas - 5 - 7)
    print(f"   [{'PASS' if ok_recon else 'FAIL'}] exclusion reconciliation (kept + excluded == deltas)")
    failed |= not ok_recon

    # ---- identity asserts (metric + delta consistency, full precision) ----
    print()
    print("== identity asserts ==")
    bad = q(con, """SELECT count(*) FROM exercise
                    WHERE abs(bids_per_quota - bids_received::DOUBLE / quota) > 1e-12
                       OR abs(success_rate - bids_success::DOUBLE / bids_received) > 1e-12""")[0][0]
    print(f"   [{'PASS' if bad == 0 else 'FAIL'}] derived metrics exact (bids_per_quota, success_rate) ({bad} violations)")
    failed |= bad != 0
    bad = q(con, """SELECT count(*) FROM deltas WHERE d_premium IS NOT NULL AND (
                      abs((premium - prev_premium) - d_premium) > 1e-9
                   OR abs(d_premium_pct - 100.0 * (premium - prev_premium) / prev_premium) > 1e-9)""")[0][0]
    print(f"   [{'PASS' if bad == 0 else 'FAIL'}] deltas consistent with their own values ({bad} violations)")
    failed |= bad != 0
    pre_post = q(con, "SELECT regime, count(DISTINCT (month, round_no)) FROM exercise GROUP BY 1 ORDER BY 1")
    print(f"   regimes: {pre_post} (expect pre 290 · post 106 exercises)")
    failed |= pre_post != [("post", 106), ("pre", 290)]

    # ---- hand-checks: 3 dated cells from the RAW CSV, stdlib only ----
    print()
    print("== hand-checks (independent recompute from the RAW CSV, stdlib only) ==")
    raw = load_raw()
    for month, round_no, cat in HAND_CHECK_CELLS:
        r_ = raw[(month, round_no, cat)]
        quota, recv, succ, prem = num(r_["quota"]), num(r_["bids_received"]), num(r_["bids_success"]), num(r_["premium"])
        row = q(con, f"""SELECT quota, bids_received, bids_success, premium, bids_per_quota, success_rate
                         FROM exercise WHERE month = DATE '{month}-01' AND round_no = {round_no} AND category = '{cat}'""")[0]
        ok = (int(row[0]) == quota and int(row[1]) == recv and int(row[2]) == succ and int(row[3]) == prem
              and abs(float(row[4]) - recv / quota) < 1e-12 and abs(float(row[5]) - succ / recv) < 1e-12)
        print(f"   [{'PASS' if ok else 'FAIL'}] {month} R{round_no} {cat}: quota {quota:,} · received {recv:,} · "
              f"success {succ:,} · premium {prem:,} · bpq {recv / quota:.4f} · sr {succ / recv:.4f}")
        failed |= not ok
    # one delta hand-check: 2026-09 R2 Cat A vs R1
    ra = raw[("2026-09", "1", "Category A")]
    d_expected = num(raw[("2026-09", "2", "Category A")]["premium"]) - num(ra["premium"])
    d_row = q(con, "SELECT d_premium FROM deltas WHERE month = DATE '2026-09-01' AND round_no = 2 AND category = 'Category A'")[0][0]
    ok = abs(float(d_row) - d_expected) < 1e-9
    print(f"   [{'PASS' if ok else 'FAIL'}] delta check: 2026-09 R2 Cat A premium move {d_expected:+,} (raw) vs {float(d_row):+,.0f} (pipeline)")
    failed |= not ok

    # ---- jump events (top 5 premium moves per category, ranked by the S$ move) ----
    # Basis: the S$ change — the unit COE prices are quoted in. % moves on the early
    # low-base values are dominated by small-denominator noise; the S$ column and the
    # % column both ship in the table. One source anomaly (Cat D 2010-01 R2: 889 →
    # 20,090, reverting next exercise) stays visible and is noted, not trimmed.
    print()
    print("== jump events (top 5 premium moves per category, ranked by S$ change) ==")
    jumps = q(con, f"""
        SELECT category, month, round_no, prev_month, prev_round,
               prev_premium, premium, d_premium, d_premium_pct,
               prev_quota, quota, d_quota_pct, prev_bpq, bids_per_quota, d_bpq,
               prev_success_rate, success_rate, regime, crosses_break, gap_spanning,
               row_number() OVER (PARTITION BY category ORDER BY d_premium DESC) AS rn
        FROM deltas WHERE d_premium IS NOT NULL
        QUALIFY rn <= 5
        ORDER BY category, rn""")
    print(f"   jump rows: {len(jumps)} (expect 25)")
    failed |= len(jumps) != 25
    for cat in CATS:
        cj = [j for j in jumps if j[0] == cat]
        j1 = cj[0]
        print(f"   {cat}: biggest {str(j1[1])[:7]} R{j1[2]}: {float(j1[5]):,.0f} → {float(j1[6]):,.0f} "
              f"({float(j1[7]):+,.0f}, {float(j1[8]):+.1f}%) · quota {float(j1[9]):,.0f}→{float(j1[10]):,.0f} "
              f"({float(j1[11]):+.1f}%) · bpq {float(j1[12]):.2f}→{float(j1[13]):.2f}")

    # ---- attribution (base) + sensitivity variants ----
    print()
    print("== attribution: premium moves vs quota moves / bid pressure (Spearman on % changes) ==")
    attr = attribution(con, BASE_SAMPLE)
    print(f"   {'category':<12} {'regime':<5} {'n':>4} {'rho prem~quota':>15} {'rho prem~bpq':>13}")
    for cat, regime, n, rq_, rb_ in attr:
        print(f"   {cat:<12} {regime:<5} {int(n):>4} {float(rq_):>15.3f} {float(rb_):>13.3f}")

    print()
    print("== sensitivity (variants; Categories A & B) ==")
    sens = []
    variants = [
        ("base: % changes, gap + break deltas excluded", attribution(con, BASE_SAMPLE, cats=AB)),
        ("including the 2020 resume delta", attribution(con, INCL_GAP_SAMPLE, cats=AB)),
        ("absolute S$ change basis", attribution(con, BASE_SAMPLE, x="d_premium", y_quota="d_quota", cats=AB)),
        ("Pearson on % changes", attribution(con, BASE_SAMPLE, rank=False, cats=AB)),
    ]
    for label, rows in variants:
        for cat, regime, n, rq_, rb_ in rows:
            sens.append((label, cat, regime, n, rq_, rb_))
            print(f"   {label:<44} {cat:<12} {regime:<5} n={int(n):>4} rho_quota {float(rq_):+.3f} · rho_bpq {float(rb_):+.3f}")
    failed |= len(sens) != 16

    # ---- headline reads ----
    print()
    print("== headline reads ==")
    latest = q(con, """SELECT month, round_no, category, quota, bids_received, bids_success, premium,
                              bids_per_quota, success_rate FROM exercise
                       WHERE month = (SELECT max(month) FROM exercise) ORDER BY round_no, category""")
    for m, rd, cat, quota, recv, succ, prem, bpq, sr in latest:
        print(f"   {m} R{rd} {cat:<12} quota {int(quota):>5,} · received {int(recv):>5,} · "
              f"premium {int(prem):>7,} · bpq {float(bpq):.2f} · sr {float(sr):.1%}")
    med = q(con, """SELECT category, regime, median(quota), median(bids_per_quota), median(success_rate), median(premium)
                    FROM exercise GROUP BY 1, 2 ORDER BY 1, 2""")
    print("   regime medians (quota · bpq · success rate · premium):")
    for cat, regime, mq, mb, ms, mp in med:
        print(f"   {cat:<12} {regime:<5} quota {float(mq):>7,.0f} · bpq {float(mb):.2f} · sr {float(ms):.1%} · premium {float(mp):>8,.0f}")
    a25 = q(con, """SELECT avg(quota), avg(premium), avg(bids_per_quota) FROM exercise
                    WHERE category = 'Category A' AND month BETWEEN DATE '2024-01-01' AND DATE '2024-12-31'""")[0]
    a26 = q(con, """SELECT avg(quota), avg(premium), avg(bids_per_quota) FROM exercise
                    WHERE category = 'Category A' AND month >= DATE '2026-01-01'""")[0]
    print(f"   Cat A 2024 vs 2026 (partial): quota {float(a25[0]):,.0f} → {float(a26[0]):,.0f} "
          f"({100 * (float(a26[0]) / float(a25[0]) - 1):+.0f}%) · premium {float(a25[1]):,.0f} → {float(a26[1]):,.0f} "
          f"· bpq {float(a25[2]):.2f} → {float(a26[2]):.2f}")
    rec = q(con, """SELECT category, month, round_no, premium FROM exercise
                    WHERE premium = (SELECT max(premium) FROM exercise WHERE category = 'Category A')
                      AND category = 'Category A'""")[0]
    print(f"   Cat A record premium: {int(rec[3]):,} at {rec[1]} R{rec[2]}")

    if failed:
        print()
        print("validation failed — output files NOT written (existing outputs left untouched)")
        sys.exit(1)

    # ---- all validation passed: write the outputs ----
    print()
    press = q(con, """SELECT month, round_no, category, quota, bids_received, bids_success, premium,
                             bids_per_quota, success_rate, regime
                      FROM exercise ORDER BY category, month, round_no""")
    write_csv(OUT / "coe_pressure.csv",
              ["month", "round", "category", "quota", "bids_received", "bids_success", "premium",
               "bids_per_quota", "success_rate", "regime"],
              [[str(m), int(rd), cat, int(qq), int(rc), int(sc), int(pr), r(bq, 4), r(sr, 4), rg]
               for m, rd, cat, qq, rc, sc, pr, bq, sr, rg in press])

    write_csv(OUT / "coe_jumps.csv",
              ["category", "rank_in_category", "month", "round", "prev_month", "prev_round",
               "premium_before", "premium_after", "d_premium", "d_premium_pct",
               "quota_before", "quota_after", "d_quota_pct", "bpq_before", "bpq_after", "d_bpq",
               "success_rate_before", "success_rate_after", "regime", "crosses_break", "gap_spanning"],
              [[j[0], int(j[20]), str(j[1])[:7], int(j[2]), str(j[3])[:7], int(j[4]),
                int(j[5]), int(j[6]), int(j[7]), r(j[8], 2),
                int(j[9]), int(j[10]), r(j[11], 2), r(j[12], 3), r(j[13], 3), r(j[14], 3),
                r(j[15], 4), r(j[16], 4), j[17], bool(j[18]), bool(j[19])] for j in jumps])

    write_csv(OUT / "coe_attribution.csv",
              ["category", "regime", "n", "rho_premium_quota", "rho_premium_bpq"],
              [[cat, regime, int(n), r(rq_, 3), r(rb_, 3)] for cat, regime, n, rq_, rb_ in attr])

    write_csv(OUT / "sensitivity.csv",
              ["variant", "category", "regime", "n", "rho_premium_quota", "rho_premium_bpq"],
              [[v, cat, regime, int(n), r(rq_, 3), r(rb_, 3)] for v, cat, regime, n, rq_, rb_ in sens])

    print()
    print("RESULT: ALL CHECKS PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
