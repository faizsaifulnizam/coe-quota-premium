"""Reconcile the entire processed generation to its raw bytes before consuming it."""
import csv
from datetime import date
import io
import json
from pathlib import Path

from src.download import FILE, validate


def load_exercise(con, root, parquet):
    """Require exact manifest metadata, row multiplicity, values and derived fields."""
    try:
        data = (root / 'data/raw' / FILE).read_bytes()
        info, problems = validate(data)
        manifest = json.loads((root / 'data/raw/pull_manifest.json').read_text(encoding='utf-8'))
        if problems or manifest['files'][FILE] != info:
            raise ValueError('raw bytes or coverage do not match manifest')
        expected = []
        for row in csv.DictReader(io.StringIO(data.decode('utf-8-sig'))):
            month = date.fromisoformat(row['month'] + '-01')
            quota, received, success, premium = (int(row[k].replace(',', '')) for k in
                                                ('quota', 'bids_received', 'bids_success', 'premium'))
            expected.append((month, int(row['bidding_no']), row['vehicle_class'], quota, received,
                             success, premium, received / quota, success / received,
                             'post' if month >= date(2022, 5, 1) else 'pre'))
        con.read_parquet(str(parquet)).create_view('exercise', replace=True)
        actual = con.execute('SELECT month, round_no, category, quota, bids_received, bids_success, '
                             'premium, bids_per_quota, success_rate, regime FROM exercise').fetchall()
        if sorted(actual) != sorted(expected):
            raise ValueError('processed rows differ from raw source (including derived fields)')
    except Exception as exc:
        raise ValueError('raw/manifest/parquet reconciliation failed; rebuild from validated source') from exc
