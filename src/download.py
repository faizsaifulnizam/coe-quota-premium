"""Download the raw LTA COE dataset from data.gov.sg into data/raw/.

One official file:
  - coe-bidding-results.csv  (COE Bidding Results / Prices, dataset d_69b3380ad7e51aff3a7dcc84eba52b8a)

Flow: initiate-download -> poll-download -> signed URL (data.gov.sg v1 public API).
Run: python src/download.py [--force]   (skips if the file already exists)

Downloads land in a .part file and are structurally validated BEFORE replacing any
existing CSV (validate-before-write; a failed pull leaves the existing file untouched):
header set, month labels, round + category enums, comma-stripped numerics, unique
(month, round, category) keys, 5 categories per exercise, coverage and a freshness
floor. On success writes data/raw/pull_manifest.json (sha256, rows, coverage,
exercises, retrieval time).
"""
import argparse
import csv
import hashlib
import io
import json
import re
import sys
import time
import urllib.request as u
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data/raw"
MANIFEST = RAW / "pull_manifest.json"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

DATASET_ID = "d_69b3380ad7e51aff3a7dcc84eba52b8a"
FILE = "coe-bidding-results.csv"

HEADER = ["month", "bidding_no", "vehicle_class", "quota", "bids_success", "bids_received", "premium"]
MONTH = re.compile(r"^(\d{4})-(\d{2})$")
CATEGORIES = {"Category A", "Category B", "Category C", "Category D", "Category E"}
ROUNDS = {"1", "2"}
NUM = re.compile(r"^\d+$")          # after comma-strip; no negatives/decimals in this file

# Freshness + coverage floors: a truncated or stale pull must fail loudly.
MONTH_FLOOR_EARLY = "2010-03"        # data must start at/before this month
MONTH_FLOOR_LATE = "2025-06"         # data must run at least to this month
ROW_FLOOR = 1900


def get(url, ref="https://data.gov.sg/"):
    r = u.Request(url, headers={"User-Agent": UA, "Accept": "*/*", "Referer": ref})
    with u.urlopen(r, timeout=180) as resp:
        return resp.read()


def fetch_to_part(dataset_id, part):
    base = f"https://api-open.data.gov.sg/v1/public/api/datasets/{dataset_id}"
    url = ""
    try:
        j = json.loads(get(base + "/poll-download"))
        url = (j.get("data") or {}).get("url") or ""
    except Exception:
        pass
    if not url:
        get(base + "/initiate-download")
        for _ in range(15):
            time.sleep(1.5)
            try:
                j = json.loads(get(base + "/poll-download"))
                url = (j.get("data") or {}).get("url") or ""
            except Exception:
                continue
            if url:
                break
    if not url:
        return None, "no signed URL returned — try again in a minute"
    data = get(url)
    part.parent.mkdir(parents=True, exist_ok=True)
    part.write_bytes(data)
    return data, None


def num(v):
    """Parse a count/premium cell; comma thousands-separators are present in the raw file."""
    return v.replace(",", "")


def validate(text):
    """Structural validation + summary. Returns (info, problems).

    Parses with the csv module: the file quotes comma-formatted thousands
    (e.g. "1,438" in bids_received) — a naive split(',') miscounts fields.
    """
    rows = [r for r in csv.reader(io.StringIO(text.lstrip("\ufeff"))) if r and any(c.strip() for c in r)]
    problems = []
    if not rows:
        return None, ["file is empty"]
    header = rows[0]
    if header != HEADER:
        return None, [f"header is {header}, expected {HEADER}"]
    body = rows[1:]
    if len(body) < ROW_FLOOR:
        problems.append(f"only {len(body)} rows (< floor {ROW_FLOOR})")

    months, keys = [], Counter()
    exercises = defaultdict(set)
    cats = Counter()
    for i, r in enumerate(body):
        if len(r) != len(HEADER):
            problems.append(f"row {i + 2} has {len(r)} fields, expected {len(HEADER)}")
            continue
        month, round_no, cat = r[0], r[1], r[2]
        m = MONTH.match(month)
        if not m or not (1 <= int(m.group(2)) <= 12):
            problems.append(f"row {i + 2}: bad month '{month}'")
            continue
        if round_no not in ROUNDS:
            problems.append(f"row {i + 2}: bad bidding_no '{round_no}'")
        if cat not in CATEGORIES:
            problems.append(f"row {i + 2}: unknown vehicle_class '{cat}'")
        for f in ("quota", "bids_success", "bids_received", "premium"):
            if not NUM.match(num(r[HEADER.index(f)])):
                problems.append(f"row {i + 2}: non-numeric {f} '{r[HEADER.index(f)]}'")
        months.append(month)
        keys[(month, round_no, cat)] += 1
        exercises[(month, round_no)].add(cat)
        cats[cat] += 1
        if len(problems) > 20:
            problems.append("… stopping after 20 problems")
            return None, problems

    dups = [k for k, v in keys.items() if v > 1]
    if dups:
        problems.append(f"duplicate (month, round, category) keys: {dups[:5]}")
    incomplete = {k: len(v) for k, v in exercises.items() if len(v) != 5}
    if incomplete:
        problems.append(f"exercises without exactly 5 categories: {sorted(incomplete.items())[:5]}")
    if sorted(cats) != sorted(CATEGORIES):
        problems.append(f"categories present: {sorted(cats)}, expected {sorted(CATEGORIES)}")

    mset = sorted(set(months))
    if not mset:
        return None, problems or ["no month rows"]
    if mset[0] > MONTH_FLOOR_EARLY:
        problems.append(f"earliest month {mset[0]} is later than the floor {MONTH_FLOOR_EARLY}")
    if mset[-1] < MONTH_FLOOR_LATE:
        problems.append(f"latest month {mset[-1]} is below the freshness floor {MONTH_FLOOR_LATE}")
    if problems:
        return None, problems

    return {
        "bytes": len(text.encode("utf-8")),
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "rows": len(body),
        "months": len(mset),
        "month_min": mset[0],
        "month_max": mset[-1],
        "exercises": len(exercises),
        "categories": sorted(cats),
    }, []


def write_manifest(info, retrieved_at):
    m = {
        "source": "data.gov.sg — api-open v1 public API (signed URL flow)",
        "dataset": {
            "id": DATASET_ID,
            "url": f"https://data.gov.sg/datasets/{DATASET_ID}/view",
            "name": "COE Bidding Results / Prices (LTA)",
        },
        "retrieved_at": retrieved_at,
        "files": {FILE: info},
    }
    MANIFEST.write_text(json.dumps(m, indent=2), encoding="utf-8")
    print("manifest:", MANIFEST.as_posix())
    print(f"    {FILE}: {info['bytes']} bytes · sha256 {info['sha256'][:12]}… · "
          f"coverage {info['month_min']} → {info['month_max']} · {info['rows']} rows · {info['exercises']} exercises")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-download even if the file exists")
    args = ap.parse_args()

    out = RAW / FILE
    if out.exists() and not args.force:
        print("raw file already present — use --force to refresh")
        print("  ", out.as_posix())
        if not MANIFEST.exists():
            info, problems = validate(out.read_text(encoding="utf-8", errors="replace"))
            if problems:
                raise SystemExit(f"existing {FILE} failed validation:\n  - " + "\n  - ".join(problems))
            mtime = datetime.fromtimestamp(out.stat().st_mtime).astimezone().isoformat(timespec="seconds")
            write_manifest(info, mtime)
        return 0

    part = out.with_name(out.name + ".part")
    print(f"downloading {DATASET_ID} …")
    data, err = fetch_to_part(DATASET_ID, part)
    if err:
        part.unlink(missing_ok=True)
        raise SystemExit(f"{FILE}: {err} — existing file left untouched")
    text = part.read_text(encoding="utf-8", errors="replace")
    info, problems = validate(text)
    if problems:
        part.unlink(missing_ok=True)
        raise SystemExit(f"{FILE} failed structure validation — kept existing file:\n  - " + "\n  - ".join(problems))
    part.replace(out)
    print(f"  ok: {info['bytes']} bytes · {info['rows']} rows · {info['exercises']} exercises · "
          f"coverage {info['month_min']} → {info['month_max']}")
    write_manifest(info, datetime.now().astimezone().isoformat(timespec="seconds"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
