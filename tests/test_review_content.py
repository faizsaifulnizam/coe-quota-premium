"""Check the repaired review surface against the committed CSVs; stdlib only."""
import csv
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ReviewContentTests(unittest.TestCase):
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
