"""Caller-facing offline repairs: real subprocess stages, isolated file generations."""
import csv
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class PipelineRepairs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.tmp.cleanup)
        self.tree = Path(self.tmp.name) / 'ordinary tree'
        for directory in ('src', 'sql', 'assets', 'outputs', 'reports/figures', 'docs/img', 'data/raw', 'data/processed'):
            shutil.copytree(ROOT / directory, self.tree / directory)

    def run_stage(self, stage):
        result = subprocess.run([sys.executable, str(self.tree / 'src' / stage)], cwd=self.tmp.name,
                                env={**os.environ, 'PYTHONUTF8': '1'}, capture_output=True,
                                text=True, encoding='utf-8', timeout=120)
        return result

    def generation(self):
        return {p.relative_to(self.tree).as_posix(): p.read_bytes()
                for folder in ('outputs', 'reports/figures', 'docs/img')
                for p in (self.tree / folder).glob('*') if p.is_file()}

    def test_all_producers_in_apostrophe_path_match_csvs(self):
        target = self.tree.with_name("space and apostrophe'tree")
        self.tree.rename(target)
        self.tree = target
        before = {p.name: p.read_bytes() for p in (self.tree / 'outputs').glob('*.csv')}
        for stage in ('build_dataset.py', 'analysis.py', 'figures.py'):
            with self.subTest(stage=stage):
                result = self.run_stage(stage)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual({p.name: p.read_bytes() for p in (self.tree / 'outputs').glob('*.csv')}, before)
        for p in (self.tree / 'reports/figures').glob('*.png'):
            self.assertEqual(p.read_bytes(), (self.tree / 'docs/img' / p.name).read_bytes())

    def test_consumers_reject_processed_only_changes_before_publication(self):
        import duckdb
        parquet = self.tree / 'data/processed/coe_exercises.parquet'
        original = parquet.read_bytes()
        for mutation in (
            "UPDATE t SET premium=150000 WHERE month=DATE '2026-08-01' AND round_no=1 AND category='Category A'",
            "UPDATE t SET regime='pre' WHERE month=DATE '2026-08-01'",
            "UPDATE t SET bids_per_quota=NULL WHERE month=DATE '2026-08-01'",
            "INSERT INTO t SELECT * FROM t LIMIT 1",
            "DELETE FROM t WHERE month=DATE '2026-08-01' AND round_no=1 AND category='Category A'",
        ):
            parquet.write_bytes(original)
            with duckdb.connect() as con:
                con.read_parquet(str(parquet)).create('t')
                con.execute(mutation)
                con.execute('COPY t TO ? (FORMAT PARQUET)', [str(parquet)])
            for stage in ('analysis.py', 'figures.py'):
                with self.subTest(stage=stage, mutation=mutation):
                    before = self.generation()
                    result = self.run_stage(stage)
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn('raw/manifest/parquet', result.stdout + result.stderr)
                    self.assertTrue(self.generation() == before, 'previous generation changed')

    def test_consumers_reject_manifest_drift_preserving_generation(self):
        manifest_path = self.tree / 'data/raw/pull_manifest.json'
        original = manifest_path.read_bytes()
        for field, value in (('sha256', '0' * 64), ('rows', 1985), ('month_max', '2026-10')):
            manifest = json.loads(original)
            manifest['files']['coe-bidding-results.csv'][field] = value
            manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
            for stage in ('analysis.py', 'figures.py'):
                with self.subTest(stage=stage, field=field):
                    before = self.generation()
                    result = self.run_stage(stage)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('raw/manifest/parquet', result.stderr)
                    self.assertTrue(self.generation() == before)
        manifest_path.unlink()
        for stage in ('analysis.py', 'figures.py'):
            result = self.run_stage(stage)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('raw/manifest/parquet', result.stderr)

    def test_builder_rejects_bad_numeric_tokens_preserving_parquet(self):
        raw = self.tree / 'data/raw/coe-bidding-results.csv'
        original = raw.read_bytes()
        parquet = self.tree / 'data/processed/coe_exercises.parquet'
        before = parquet.read_bytes()
        for field in ('quota', 'bids_success', 'bids_received', 'premium'):
            for token in ('1,00', '１２３', '9223372036854775808'):
                with self.subTest(field=field, token=token):
                    parquet.write_bytes(before)
                    rows = list(csv.reader(io.StringIO(original.decode())))
                    rows[1][rows[0].index(field)] = token
                    text = io.StringIO(newline='')
                    csv.writer(text).writerows(rows)
                    raw.write_bytes(text.getvalue().encode())
                    result = self.run_stage('build_dataset.py')
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(parquet.read_bytes(), before)
