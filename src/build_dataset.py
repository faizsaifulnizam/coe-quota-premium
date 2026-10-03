"""Build the processed dataset: raw CSV -> staging (sql/01) -> checks (sql/05) -> parquet.

Run (repo root): python src/build_dataset.py
Receipts printed: in/out row counts, exclusion breakdown, check results. Exit 1 if any check fails.

Order matters: every check runs BEFORE the parquet is produced, and the file is written
to a temp path then atomically replaced — a failing run never touches the existing output.
"""
import os
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
STAGING = ROOT / "sql/01_staging.sql"
CHECKS = ROOT / "sql/05_checks.sql"
OUT_DIR = ROOT / "data/processed"
RAW = (ROOT / "data/raw/coe-bidding-results.csv").as_posix()

# Exclusion rules — must mirror the WHERE clause in sql/01. A row is excluded if ANY rule matches.
CATS = "'Category A', 'Category B', 'Category C', 'Category D', 'Category E'"
RULES = [
    ("month label unparseable", "TRY_CAST(month_label || '-01' AS DATE) IS NULL"),
    ("round not 1/2", "TRY_CAST(round_label AS INTEGER) IS NULL OR TRY_CAST(round_label AS INTEGER) NOT IN (1, 2)"),
    ("unexpected category", f"category NOT IN ({CATS})"),
    ("value unparseable",
     "TRY_CAST(replace(quota_raw, ',', '') AS BIGINT) IS NULL "
     "OR TRY_CAST(replace(received_raw, ',', '') AS BIGINT) IS NULL "
     "OR TRY_CAST(replace(success_raw, ',', '') AS BIGINT) IS NULL "
     "OR TRY_CAST(replace(premium_raw, ',', '') AS BIGINT) IS NULL"),
]
ANY_RULE = "(" + " OR ".join(expr for _, expr in RULES) + ")"

PARSED = (f"SELECT month AS month_label, bidding_no AS round_label, vehicle_class AS category, "
          f"quota AS quota_raw, bids_success AS success_raw, bids_received AS received_raw, premium AS premium_raw "
          f"FROM read_csv_auto('{RAW}', all_varchar = true)")


def q(con, sql):
    return con.sql(sql).fetchall()


def main():
    os.chdir(ROOT)  # sql/01 references data/raw relatively
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()

    raw_rows = q(con, f"SELECT count(*) FROM ({PARSED})")[0][0]
    con.execute("CREATE OR REPLACE VIEW raw_long AS " + PARSED)
    con.execute(STAGING.read_text(encoding="utf-8"))

    staged = q(con, "SELECT count(*) FROM exercise")[0][0]
    excl_any = q(con, f"SELECT count(*) FROM raw_long WHERE {ANY_RULE}")[0][0]
    print(f"raw rows:     {raw_rows}")
    print(f"staged:       {staged}  ({q(con, 'SELECT count(DISTINCT category) FROM exercise')[0][0]} categories × "
          f"{q(con, 'SELECT count(DISTINCT (month, round_no)) FROM exercise')[0][0]} exercises)")
    print(f"excluded:     {raw_rows - staged}  ({100 * (raw_rows - staged) / raw_rows:.3f}%)")
    print("exclusion rules (per-rule counts; a row may match more than one):")
    for rule, expr in RULES:
        k = q(con, f"SELECT count(*) FROM raw_long WHERE {expr}")[0][0]
        print(f"    rule [{rule}]: {k}")
    ok_recon = (staged + excl_any) == raw_rows
    print(f"    [{'PASS' if ok_recon else 'FAIL'}] retained + excluded == raw rows "
          f"({staged} + {excl_any} vs {raw_rows})")

    print("checks:")
    failed = not ok_recon
    for name, v in con.execute(CHECKS.read_text(encoding="utf-8")).fetchall():
        status = "PASS" if v == 0 else "FAIL"
        print(f"    [{status}] {name}  (violations: {v})")
        if v:
            failed = True

    if failed:
        print("checks failed — parquet NOT written (existing file left untouched)")
        sys.exit(1)

    pq = OUT_DIR / "coe_exercises.parquet"
    tmp = OUT_DIR / "coe_exercises.parquet.tmp"
    con.sql(f"COPY exercise TO '{tmp.as_posix()}' (FORMAT PARQUET)")
    os.replace(tmp, pq)
    print(f"wrote: {pq.as_posix()}  ({pq.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
