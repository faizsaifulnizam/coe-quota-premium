"""Analysis regressions; source checks need the local raw CSV and parquet.

Run: .venv/Scripts/python.exe -m unittest discover -s tests -p test_analysis_regressions.py -v
All writes use isolated trees under Hermes scratch, never repository outputs.
Audit anchors use the Jan-2010–Sep-2026 snapshot; later rows remain checked for
raw/parquet agreement but cannot drift the audit's fixed numeric expectations.
"""
import contextlib
import csv
import datetime as dt
import io
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import analysis


def spearman(xs, ys):
    # Independent stdlib oracle: count smaller/equal values, not SQL window ranks.
    def ranks(values):
        return [1 + sum(w < v for w in values) + (sum(w == v for w in values) - 1) / 2
                for v in values]
    return statistics.correlation(ranks(xs), ranks(ys))


@unittest.skipUnless(Path(analysis.PARQUET).exists() and analysis.RAW.exists(),
                     "local source CSV and processed parquet required")
class LiveAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.con = duckdb.connect()
        self.con.execute(f"CREATE TABLE exercise AS SELECT * FROM read_parquet('{analysis.PARQUET}') "
                         "WHERE month <= DATE '2026-09-01'")
        analysis.run_script(self.con, ROOT / "sql/02_metrics.sql")
        self.addCleanup(self.con.close)

    def test_ab_definition_scope_counts(self):
        groups = self.con.sql(f"SELECT category, regime, count(*) FROM deltas WHERE {analysis.BASE_SAMPLE} "
                              "GROUP BY 1,2 ORDER BY 1,2").fetchall()
        self.assertEqual(groups, [
            ('Category A', 'post', 105), ('Category A', 'pre', 190),
            ('Category B', 'post', 105), ('Category B', 'pre', 190),
            ('Category C', 'post', 106), ('Category C', 'pre', 288),
            ('Category D', 'post', 106), ('Category D', 'pre', 288),
            ('Category E', 'post', 106), ('Category E', 'pre', 288)])
        self.assertEqual(sum(row[2] for row in groups), 1772)
        self.assertEqual(self.con.sql(f"SELECT count(*) FROM deltas WHERE {analysis.INCL_GAP_SAMPLE}").fetchone()[0], 1777)

    @contextlib.contextmanager
    def run_analysis(self, future_rounds=(), setup_out=None, script=False):
        scratch = Path(os.environ.get('TMPDIR') or tempfile.gettempdir())
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='coe-analysis-test-', dir=scratch) as tmp:
            tree = Path(tmp)
            shutil.copytree(ROOT / 'sql', tree / 'sql')
            (tree / 'data/raw').mkdir(parents=True)
            shutil.copy2(analysis.RAW, tree / 'data/raw/coe-bidding-results.csv')
            (tree / 'data/processed').mkdir(parents=True)
            parquet = tree / 'data/processed/coe_exercises.parquet'
            for rd in future_rounds:
                self.con.execute("""INSERT INTO exercise
                    SELECT DATE '2026-10-01', ?, category, 10000, 20000, 10000, 200000,
                           2.0, 0.5, 'post' FROM exercise
                    WHERE month = DATE '2026-09-01' AND round_no = 2""", [rd])
            self.con.sql(f"COPY exercise TO '{parquet.as_posix()}' (FORMAT PARQUET)")
            out = tree / 'outputs'
            out.mkdir()
            if setup_out:
                setup_out(out)
            stdout = io.StringIO()
            cwd = Path.cwd()
            try:
                if script:
                    (tree / 'src').mkdir()
                    for name in ('analysis.py', 'publish.py'):
                        shutil.copy2(ROOT / 'src' / name, tree / 'src' / name)
                    result = subprocess.run([sys.executable, str(tree / 'src/analysis.py')], cwd=scratch,
                                            env={**os.environ, 'PYTHONUTF8': '1', 'PYTHONPATH': ''},
                                            capture_output=True, text=True, encoding='utf-8', timeout=60)
                    status = result.returncode
                    stdout.write(result.stdout + result.stderr)
                else:
                    with patch.multiple(analysis, ROOT=tree, RAW=tree / 'data/raw/coe-bidding-results.csv',
                                        PARQUET=parquet.as_posix(), OUT=out), contextlib.redirect_stdout(stdout):
                        try:
                            analysis.main()
                        except SystemExit as exc:
                            status = exc.code
                        except Exception as exc:
                            status = exc
                yield status, stdout.getvalue(), out
            finally:
                os.chdir(cwd)

    def test_main_counted_scope_reconciliation(self):
        with self.run_analysis() as (status, stdout, out):
            self.assertEqual(status, 0, stdout)
            self.assertIn('1772 deltas kept of 1975', stdout)
            self.assertIn('early A/B scope 196', stdout)
            self.assertIn('[PASS] exclusion reconciliation', stdout)
            self.assertEqual(len(list(out.glob('*.csv'))), 4)

    def test_later_csv_staging_failure_preserves_entire_batch(self):
        names = ('coe_pressure.csv', 'coe_jumps.csv', 'coe_attribution.csv', 'sensitivity.csv')
        def block_second_stage(out):
            for name in names:
                (out / name).write_bytes(b'previous validated run\n')
            (out / 'coe_jumps.csv.tmp').mkdir()
        with self.run_analysis(setup_out=block_second_stage) as (status, stdout, out):
            self.assertIsInstance(status, (IsADirectoryError, PermissionError))
            for name in names:
                self.assertEqual((out / name).read_bytes(), b'previous validated run\n')

    def test_script_execution_outside_repository(self):
        with self.run_analysis(script=True) as (status, stdout, out):
            self.assertEqual(status, 0, stdout)
            self.assertIn('RESULT: ALL CHECKS PASS', stdout)
            self.assertEqual(len(list(out.glob('*.csv'))), 4)

    def test_promotion_failure_rolls_back_entire_batch(self):
        names = ('coe_pressure.csv', 'coe_jumps.csv', 'coe_attribution.csv', 'sensitivity.csv')
        def seed(out):
            for name in names:
                (out / name).write_bytes(b'previous validated run\n')
        real_replace = Path.replace
        def fail_second_stage(path, target):
            if path.name == 'coe_jumps.csv.tmp':
                raise OSError('injected second promotion failure')
            return real_replace(path, target)
        with patch.object(Path, 'replace', fail_second_stage), self.run_analysis(setup_out=seed) as (status, stdout, out):
            self.assertIsInstance(status, OSError)
            for name in names:
                self.assertEqual((out / name).read_bytes(), b'previous validated run\n')
            self.assertEqual(list(out.glob('*.bak')), [])

    def test_analysis_accepts_normal_post_regime_growth(self):
        for rounds, post, kept in [((1,), 107, 1777), ((1, 2), 108, 1782)]:
            with self.subTest(rounds=rounds), self.run_analysis(rounds) as (status, stdout, out):
                self.assertEqual(status, 0, stdout)
                self.assertIn(f"('post', {post})", stdout)
                self.assertIn(f'{kept} deltas kept', stdout)
                self.assertEqual(len(list(out.glob('*.csv'))), 4)
                print(f'GROWTH ORACLE rounds={rounds}: post={post}, retained={kept}, exit={status}')
            self.con.execute("DELETE FROM exercise WHERE month = DATE '2026-10-01'")

    def test_jan_sep_headlines_do_not_include_october(self):
        with self.run_analysis() as (status, stdout, out):
            self.assertEqual(status, 0, stdout)
            baseline = [line for line in stdout.splitlines()
                        if 'Cat A 2024 (full)' in line or 'Cat A Jan–Sep both years' in line]
            self.assertEqual(len(baseline), 2)
            self.assertIn('quota 962 → 1,252 (+30.2%) · premium 88,078 → 119,812', baseline[1])
        with self.run_analysis((1, 2)) as (status, stdout, out):
            self.assertEqual(status, 0, stdout)
            refreshed = [line for line in stdout.splitlines()
                         if 'Cat A 2024 (full)' in line or 'Cat A Jan–Sep both years' in line]
            self.assertEqual(refreshed, baseline)

    def test_staging_allows_only_latest_single_r1(self):
        self.con.execute("""INSERT INTO exercise SELECT DATE '2026-10-01', 1, category,
                            quota, bids_received, bids_success, premium, bids_per_quota, success_rate, 'post'
                            FROM exercise WHERE month = DATE '2026-09-01' AND round_no = 2""")
        def violations():
            return dict(self.con.execute((ROOT / 'sql/05_checks.sql').read_text(encoding='utf-8')).fetchall())
        self.assertEqual(violations()['two rounds per month'], 0)
        self.assertEqual(violations()['all five categories per exercise'], 0)
        self.con.execute("UPDATE exercise SET round_no = 2 WHERE month = DATE '2026-10-01'")
        self.assertEqual(violations()['two rounds per month'], 1)
        self.con.execute("UPDATE exercise SET round_no = 1 WHERE month = DATE '2026-10-01'")
        self.con.execute("DELETE FROM exercise WHERE month = DATE '2026-09-01' AND round_no = 2")
        self.assertEqual(violations()['two rounds per month'], 1)
        self.con.execute("DELETE FROM exercise WHERE month = DATE '2026-10-01' AND category = 'Category E'")
        self.assertEqual(violations()['all five categories per exercise'], 1)

    def test_correlation_csvs_keep_full_precision(self):
        expected = {(c, rg): (rq, rb) for c, rg, n, rq, rb
                    in analysis.attribution(self.con, analysis.BASE_SAMPLE)}
        clean_expected = {(c, rg): (rq, rb) for c, rg, n, rq, rb
                          in analysis.attribution(self.con, analysis.SOURCE_CONFLICT_SAMPLE)}
        with self.run_analysis() as (status, stdout, out):
            self.assertEqual(status, 0, stdout)
            for name in ('coe_attribution.csv', 'sensitivity.csv'):
                with (out / name).open(newline='', encoding='utf-8') as f:
                    rows = list(csv.DictReader(f))
                for row in rows:
                    variant = row.get('variant', 'base: % changes, gap + break deltas excluded')
                    if variant == 'base: % changes, gap + break deltas excluded':
                        oracle = expected
                    elif variant == 'excluding deltas touching source conflicts (all categories)':
                        oracle = clean_expected
                    else:
                        continue
                    rq, rb = oracle[(row['category'], row['regime'])]
                    self.assertAlmostEqual(float(row['rho_premium_quota']), rq, places=12)
                    self.assertAlmostEqual(float(row['rho_premium_bpq']), rb, places=12)
                b_post = next(r for r in rows if r['category'] == 'Category B' and r['regime'] == 'post')
                self.assertEqual(f"{float(b_post['rho_premium_bpq']):.2f}", '0.55')

    def test_attribution_is_repeatable_at_full_precision(self):
        # Parallel aggregate order must not change serialized correlation bytes.
        for rank in (True, False):
            first = analysis.attribution(self.con, analysis.BASE_SAMPLE, rank=rank)
            for _ in range(8):
                self.assertEqual(analysis.attribution(self.con, analysis.BASE_SAMPLE, rank=rank), first)

    def test_source_conflict_sensitivity_covers_all_categories(self):
        with self.run_analysis() as (status, stdout, out):
            self.assertEqual(status, 0, stdout)
            with (out / 'sensitivity.csv').open(newline='', encoding='utf-8') as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 30)
            clean = {(r['category'], r['regime']): r for r in rows
                     if r['variant'] == 'excluding deltas touching source conflicts (all categories)'}
            self.assertEqual(len(clean), 10)
            d_pre = clean[('Category D', 'pre')]
            self.assertEqual(int(d_pre['n']), 286)
            self.assertAlmostEqual(float(d_pre['rho_premium_quota']), -0.133685127974, places=3)
            self.assertAlmostEqual(float(d_pre['rho_premium_bpq']), 0.062274919855, places=3)
            self.assertEqual(int(clean[('Category B', 'pre')]['n']), 190)
            self.assertIn('4 affected deltas', stdout)
            self.assertIn('1770 retained + 2 excluded == 1772 base', stdout)
        # Check both incoming/outgoing deltas for both cells before A/B scope hides B.
        excluded = self.con.sql(f"SELECT category, month, round_no FROM deltas "
                                f"WHERE d_premium_pct IS NOT NULL AND NOT {analysis.SOURCE_CONFLICT_FREE} "
                                "ORDER BY 1,2,3").fetchall()
        self.assertEqual(excluded, [('Category B', dt.date(2010, 2, 1), 1),
                                    ('Category B', dt.date(2010, 2, 1), 2),
                                    ('Category D', dt.date(2010, 1, 1), 2),
                                    ('Category D', dt.date(2010, 2, 1), 1)])

    def test_raw_parquet_agreement_and_independent_review_receipts(self):
        with analysis.RAW.open(newline='', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        raw = {(dt.date.fromisoformat(r['month'] + '-01'), int(r['bidding_no']), r['vehicle_class']):
               tuple(int(r[k].replace(',', '')) for k in ('quota', 'bids_received', 'bids_success', 'premium'))
               for r in rows}
        parquet = {tuple(r[:3]): tuple(r[3:]) for r in self.con.sql(
            'SELECT month, round_no, category, quota, bids_received, bids_success, premium '
            f"FROM read_parquet('{analysis.PARQUET}')").fetchall()}
        self.assertEqual(raw, parquet)
        raw = {key: value for key, value in raw.items() if key[0] <= dt.date(2026, 9, 1)}
        self.assertEqual(len(raw), 1980)
        self.assertEqual(raw[(dt.date(2010, 1, 1), 2, 'Category D')][-1], 20090)
        self.assertEqual(raw[(dt.date(2010, 2, 1), 1, 'Category B')][0], 1154)
        for year in (2024, 2026):
            window = [v for k, v in raw.items()
                      if k[2] == 'Category A' and dt.date(year, 1, 1) <= k[0] <= dt.date(year, 9, 1)]
            mq, mp = statistics.mean(v[0] for v in window), statistics.mean(v[3] for v in window)
            self.assertEqual(len(window), 18)
            self.assertAlmostEqual(mq, 961.9444444444445 if year == 2024 else 1252.1666666666667, places=10)
            self.assertEqual(mp, 88077.5 if year == 2024 else 119812.0)
            print(f'RAW ORACLE Cat A Jan-Sep {year}: n={len(window)} quota={mq:.12f} premium={mp:.12f}')
        actual = {(cat, regime): (n, rq, rb) for cat, regime, n, rq, rb
                  in analysis.attribution(self.con, analysis.BASE_SAMPLE)}
        clean_actual = {(cat, regime): (n, rq, rb) for cat, regime, n, rq, rb
                        in analysis.attribution(self.con, analysis.SOURCE_CONFLICT_SAMPLE)}
        for cat in analysis.CATS:
            ordered = sorted((k, v) for k, v in raw.items() if k[2] == cat)
            groups = {'pre': [], 'post': []}
            for (prev, pv), (key, val) in zip(ordered, ordered[1:]):
                if prev[0] == dt.date(2020, 3, 1) and key[0] == dt.date(2020, 7, 1):
                    continue
                if cat in ('Category A', 'Category B') and (
                        prev[0] < dt.date(2014, 2, 1) or
                        prev[0] < dt.date(2022, 5, 1) <= key[0]):
                    continue
                groups['post' if key[0] >= dt.date(2022, 5, 1) else 'pre'].append(
                    (key, 100.0 * (val[3] - pv[3]) / pv[3],
                     100.0 * (val[0] - pv[0]) / pv[0], val[1] / val[0] - pv[1] / pv[0]))
            for regime, deltas in groups.items():
                rq = spearman([v[1] for v in deltas], [v[2] for v in deltas])
                rb = spearman([v[1] for v in deltas], [v[3] for v in deltas])
                print(f'RAW ORACLE {cat} {regime}: n={len(deltas)} quota={rq:.12f} bpq={rb:.12f}')
                with self.subTest(category=cat, regime=regime):
                    n, actual_rq, actual_rb = actual[(cat, regime)]
                    self.assertEqual(n, len(deltas))
                    self.assertAlmostEqual(actual_rq, rq, places=12)
                    self.assertAlmostEqual(actual_rb, rb, places=12)
                if cat == 'Category D' and regime == 'pre':
                    clean = [v for v in deltas if v[0][:2] not in (
                        (dt.date(2010, 1, 1), 2), (dt.date(2010, 2, 1), 1))]
                    print(f'RAW ORACLE D pre conflicts excluded: n={len(clean)} '
                          f'quota={spearman([v[1] for v in clean], [v[2] for v in clean]):.12f} '
                          f'bpq={spearman([v[1] for v in clean], [v[3] for v in clean]):.12f}')
                    n, clean_rq, clean_rb = clean_actual[(cat, regime)]
                    self.assertEqual(n, len(clean))
                    self.assertAlmostEqual(clean_rq, spearman([v[1] for v in clean], [v[2] for v in clean]), places=12)
                    self.assertAlmostEqual(clean_rb, spearman([v[1] for v in clean], [v[3] for v in clean]), places=12)


if __name__ == '__main__':
    unittest.main()
