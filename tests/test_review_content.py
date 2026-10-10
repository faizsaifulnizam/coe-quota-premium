"""Check the repaired review surface against the committed CSVs; stdlib only."""
import csv
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ReviewContentTests(unittest.TestCase):
    def test_report_has_main_heading_and_semantic_figure_captions(self):
        from html.parser import HTMLParser
        class ReportParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.stack, self.headings, self.main_count, self.captions = [], [], 0, 0
            def handle_starttag(self, tag, attrs):
                if tag == 'main':
                    self.main_count += 1
                if tag == 'h1':
                    self.headings.append('')
                    self_in_main = 'main' in self.stack
                    if not self_in_main:
                        raise AssertionError('H1 outside main')
                if tag == 'figcaption':
                    if 'figure' not in self.stack:
                        raise AssertionError('caption outside figure')
                    self.captions += 1
                if tag not in ('meta', 'link', 'img', 'source', 'br', 'hr', 'input'):
                    self.stack.append(tag)
            def handle_endtag(self, tag):
                if tag in self.stack:
                    del self.stack[self.stack.index(tag):]
            def handle_data(self, data):
                if 'h1' in self.stack:
                    self.headings[-1] += data
        parser = ReportParser()
        parser.feed((ROOT / 'docs/index.html').read_text(encoding='utf-8'))
        self.assertEqual(parser.main_count, 1)
        self.assertEqual(len(parser.headings), 1)
        self.assertIn('COE', parser.headings[0])
        self.assertGreaterEqual(parser.captions, 2)

    def test_frozen_snapshot_is_packaged_with_original_manifest(self):
        import hashlib
        import subprocess
        for name, expected in (
            ('coe-bidding-results.csv', '361d5ae2ba641be1e834ca822e4cb66a91f42b6f7663847f42fcc4a4062b4bac'),
            ('pull_manifest.json', '389de31b701d6c9318b84695367a225c5aee2ac51e06e51020f91da89e364039'),
        ):
            path = ROOT / 'data/raw' / name
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)
            ignored = subprocess.run(['git', 'check-ignore', '--no-index', str(path)], cwd=ROOT,
                                     capture_output=True, text=True)
            self.assertEqual(ignored.returncode, 1, ignored.stdout + ignored.stderr)
        for name in ('README.md', 'docs/index.html'):
            self.assertIn('frozen snapshot', (ROOT / name).read_text(encoding='utf-8'))

    def test_ci_runs_offline_pipeline_regressions_and_csv_compare(self):
        text = (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8')
        for command in ('pip install -r requirements.txt', 'python src/download.py',
                        'python src/build_dataset.py', 'python src/analysis.py',
                        'python src/figures.py', "discover('tests'", 'result.skipped',
                        "git diff --exit-code -- 'outputs/*.csv'", 'sha256sum -c'):
            self.assertIn(command, text)
        self.assertNotIn('--force', text)

    def test_definition_consistent_earlier_sample(self):
        with (ROOT / 'outputs/coe_attribution.csv').open(encoding='utf-8', newline='') as f:
            rows = list(csv.DictReader(f))
        for cat in ('Category A', 'Category B'):
            row = next(r for r in rows if r['category'] == cat and r['regime'] == 'pre')
            self.assertEqual(int(row['n']), 190)
        total = sum(int(r['n']) for r in rows)
        self.assertIn(f'{total:,}', (ROOT / 'README.md').read_text(encoding='utf-8'))

    def test_prose_rounds_directly_from_csv(self):
        with (ROOT / 'outputs/coe_attribution.csv').open(encoding='utf-8', newline='') as f:
            rows = list(csv.DictReader(f))
        readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        for r in rows:
            if r['regime'] == 'post' and r['category'] in ('Category A', 'Category B', 'Category C', 'Category D'):
                for column in ('rho_premium_quota', 'rho_premium_bpq'):
                    value = f"{float(r[column]):+.2f}".replace('-', '−')
                    self.assertIn(value, readme)

    def test_banners_match_site_and_remove_stale_range(self):
        for name in ('banner.svg', 'banner-dark.svg'):
            text = (ROOT / 'assets' / name).read_text(encoding='utf-8')
            self.assertEqual(text, (ROOT / 'docs/img' / name).read_text(encoding='utf-8'))
            self.assertNotIn('336–2,218', text)
            self.assertNotIn('lowest successful bid', text)
            self.assertNotIn('the 2026 records', text)

    def test_two_large_quota_cuts_are_disclosed(self):
        with (ROOT / 'outputs/coe_jumps.csv').open(encoding='utf-8', newline='') as f:
            cuts = [r for r in csv.DictReader(f) if float(r['d_quota_pct']) < -40]
        self.assertEqual({(r['category'], r['month'], r['round']) for r in cuts},
                         {('Category C', '2023-02', '1'), ('Category D', '2020-08', '1')})
        for file in ('README.md', 'docs/decision_memo.md', 'docs/index.html'):
            text = (ROOT / file).read_text(encoding='utf-8')
            for r in cuts:
                self.assertIn(r['month'], text)
                self.assertIn(f"{abs(float(r['d_quota_pct'])):.1f}", text)


if __name__ == '__main__':
    unittest.main()
