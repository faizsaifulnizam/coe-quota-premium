"""Download the raw LTA COE dataset from data.gov.sg into data/raw/.

One official file:
  - coe-bidding-results.csv  (COE Bidding Results / Prices, dataset d_69b3380ad7e51aff3a7dcc84eba52b8a)

Flow: initiate-download -> poll-download -> signed URL (data.gov.sg v1 public API).
Run: python src/download.py [--force]   (validates an existing cache before reuse)

Downloads are staged and structurally validated BEFORE publication: header set,
month labels, round + category enums, comma-stripped numerics, unique keys,
5 categories per exercise, coverage and freshness floors. Raw bytes and their
manifest are published together with rollback on ordinary replacement failures;
this does not guarantee crash/power-loss safety or atomic concurrent reads.
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
sys.path.insert(0, str(ROOT))
from src.publish import publish_files

RAW = ROOT / "data/raw"
MANIFEST = RAW / "pull_manifest.json"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

DATASET_ID = "d_69b3380ad7e51aff3a7dcc84eba52b8a"
FILE = "coe-bidding-results.csv"

HEADER = ["month", "bidding_no", "vehicle_class", "quota", "bids_success", "bids_received", "premium"]
MONTH = re.compile(r"([0-9]{4})-([0-9]{2})")
CATEGORIES = {"Category A", "Category B", "Category C", "Category D", "Category E"}
ROUNDS = {"1", "2"}
NUM = re.compile(r"(?:[0-9]+|[1-9][0-9]{0,2}(?:,[0-9]{3})+)")
BIGINT_MAX = 9223372036854775807

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
    except Exception as exc:  # a 403 and "not ready yet" must not look the same
        print(f"  poll-download ({type(exc).__name__}): {ascii(str(exc))}")
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
        return None, "no signed URL returned - try again in a minute"
    data = get(url)
    part.parent.mkdir(parents=True, exist_ok=True)
    part.write_bytes(data)
    return data, None


def num(v):
    """Parse a count/premium cell; comma thousands-separators are present in the raw file."""
    return v.replace(",", "")


def validate(text):
    """Structural validation + summary. Returns (info, problems).

    Pass bytes to retain the source byte count and SHA (including CRLF and BOM).
    Decoding is strict UTF-8; text input is retained for existing callers.

    Parses with the csv module: the file quotes comma-formatted thousands
    (e.g. "1,438" in bids_received) — a naive split(',') miscounts fields.
    """
    data = text if isinstance(text, bytes) else text.encode("utf-8")
    try:
        text = data.decode("utf-8")
        rows = [r for r in csv.reader(io.StringIO(text.lstrip("\ufeff")), strict=True) if r and any(c.strip() for c in r)]
    except (UnicodeDecodeError, csv.Error) as exc:
        return None, [f"invalid UTF-8 or CSV: {ascii(str(exc))}"]
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
        m = MONTH.fullmatch(month)
        if not m or not (1 <= int(m.group(1)) <= 9999 and 1 <= int(m.group(2)) <= 12):
            problems.append(f"row {i + 2}: bad month '{month}'")
            continue
        if round_no not in ROUNDS:
            problems.append(f"row {i + 2}: bad bidding_no '{round_no}'")
        if cat not in CATEGORIES:
            problems.append(f"row {i + 2}: unknown vehicle_class '{cat}'")
        for f in ("quota", "bids_success", "bids_received", "premium"):
            value = r[HEADER.index(f)]
            digits = num(value).lstrip('0') or '0'
            if (not NUM.fullmatch(value) or len(digits) > 19
                    or int(digits) > BIGINT_MAX):
                problems.append(f"row {i + 2}: non-numeric {f} '{r[HEADER.index(f)]}'")
        months.append(month)
        keys[(month, round_no, cat)] += 1
        exercises[(month, round_no)].add(cat)
        cats[cat] += 1
        if len(problems) > 20:
            problems.append("... stopping after 20 problems")
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
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "rows": len(body),
        "months": len(mset),
        "month_min": mset[0],
        "month_max": mset[-1],
        "exercises": len(exercises),
        "categories": sorted(cats),
    }, []


def write_manifest(info, retrieved_at, target):
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
    target.write_text(json.dumps(m, indent=2), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-download even if the file exists")
    args = ap.parse_args()

    out = RAW / FILE
    manifest_part = MANIFEST.with_name(MANIFEST.name + ".part")
    if out.exists() and not args.force:
        info, problems = validate(out.read_bytes())
        if problems:
            raise SystemExit(f"existing {FILE} failed validation:\n  - " + "\n  - ".join(problems))
        if MANIFEST.exists():
            try:
                manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
                expected = manifest["files"][FILE]["sha256"]
                if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
                    raise ValueError("invalid sha256")
            except (OSError, ValueError, KeyError, TypeError) as exc:
                raise SystemExit("cached manifest is invalid; use --force to fetch and validate a new copy") from exc
            if info["sha256"] != expected:
                raise SystemExit(f"cached {FILE} does not match its manifest; use --force to fetch and validate a new copy")
        else:
            mtime = datetime.fromtimestamp(out.stat().st_mtime).astimezone().isoformat(timespec="seconds")
            try:
                write_manifest(info, mtime, manifest_part)
                publish_files([(manifest_part, MANIFEST)])
            finally:
                manifest_part.unlink(missing_ok=True)
        print("raw cache validated; use --force to refresh")
        return 0

    part = out.with_name(out.name + ".part")
    print(f"downloading {DATASET_ID} ...")
    try:
        _, err = fetch_to_part(DATASET_ID, part)
        if err:
            raise SystemExit(f"{FILE}: {err} - existing file left untouched")
        info, problems = validate(part.read_bytes())
        if problems:
            raise SystemExit(f"{FILE} failed structure validation - kept existing file:\n  - " + "\n  - ".join(problems))
        write_manifest(info, datetime.now().astimezone().isoformat(timespec="seconds"), manifest_part)
        publish_files([(part, out), (manifest_part, MANIFEST)])
    finally:
        part.unlink(missing_ok=True)
        manifest_part.unlink(missing_ok=True)
    print(f"  ok: {info['bytes']} bytes | {info['rows']} rows | {info['exercises']} exercises | "
          f"coverage {info['month_min']} -> {info['month_max']}")
    print(f"manifest: {MANIFEST.name} | sha256 {info['sha256']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
