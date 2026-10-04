"""Real figures.main regressions; all outputs live in an isolated scratch tree.

Run: .venv/Scripts/python.exe -m unittest discover -s tests -p test_figures_publication.py -v
"""
import contextlib
import io
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import duckdb
from matplotlib.figure import Figure
from src import figures

NAMES = [f"{stem}{suffix}.png" for stem in
         ("f1_quota_premium", "f2_pressure", "f3_scatter") for suffix in ("", "-dark")]


class FiguresPublicationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for relative in ("sql/02_metrics.sql", "data/processed/coe_exercises.parquet",
                         "data/raw/pull_manifest.json"):
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        self.outputs = [self.root / folder / name for folder in
                        ("reports/figures", "docs/img") for name in NAMES]
        for target in self.outputs:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"previous:" + target.name.encode())
        self.before = {target: target.read_bytes() for target in self.outputs}

    def run_main(self):
        cwd = Path.cwd()
        try:
            with patch.multiple(figures, ROOT=self.root,
                                PARQUET=(self.root / "data/processed/coe_exercises.parquet").as_posix(),
                                FIGDIR=self.root / "reports/figures"), contextlib.redirect_stdout(io.StringIO()) as out:
                figures.main()
            return out.getvalue()
        finally:
            os.chdir(cwd)
            figures.plt.close("all")

    def assert_preserved(self):
        for target in self.outputs:
            self.assertTrue(target.read_bytes() == self.before[target], f"changed previous target: {target}")
        self.assertFalse(list(self.root.rglob("*.tmp")), "staged files leaked after failure")
        self.assertFalse(list(self.root.rglob("*.bak")), "rollback backups leaked")

    def test_mirror_write_failure_preserves_entire_previous_batch(self):
        original = Path.write_bytes
        failed = False

        def fail_after_write(path, data):
            nonlocal failed
            result = original(path, data)
            if path == self.root / "docs/img/f2_pressure.png.tmp":
                failed = True
                raise OSError("injected mirror staging failure")
            return result

        with patch.object(Path, "write_bytes", fail_after_write):
            with self.assertRaisesRegex(OSError, "injected mirror staging failure"):
                self.run_main()
        self.assertTrue(failed)
        self.assert_preserved()

    def test_promotion_failure_rolls_back_reports_and_site_copies(self):
        original = os.replace
        promotions = []
        failed = False

        def fail_once(source, destination, *args, **kwargs):
            nonlocal failed
            source, destination = Path(source), Path(destination)
            if source.suffix == ".tmp" and destination in self.outputs:
                if not promotions:
                    stages = list(self.root.rglob("*.tmp"))
                    self.assertEqual(len(stages), 12, "publication started before all PNGs/site copies staged")
                    for stage in stages:
                        self.assertTrue(stage.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
                    for target in self.outputs:
                        self.assertTrue(target.read_bytes() == self.before[target])
                if destination == self.root / "docs/img/f2_pressure.png" and not failed:
                    failed = True
                    raise OSError("injected eighth promotion failure")
                promotions.append(destination)
            return original(source, destination, *args, **kwargs)

        with patch.object(os, "replace", fail_once):
            with self.assertRaisesRegex(OSError, "injected eighth promotion failure"):
                self.run_main()
        self.assertTrue(failed)
        self.assertEqual(len(promotions), 7)
        self.assert_preserved()

    def test_render_failure_preserves_entire_previous_batch(self):
        original = Figure.savefig
        calls = 0

        def fail_after_write(fig, path, *args, **kwargs):
            nonlocal calls
            calls += 1
            original(fig, path, *args, **kwargs)
            if calls == 4:
                raise OSError("injected PNG write failure")

        with patch.object(Figure, "savefig", fail_after_write):
            with self.assertRaisesRegex(OSError, "injected PNG write failure"):
                self.run_main()
        self.assertEqual(calls, 4)
        self.assert_preserved()

    def test_full_history_has_definition_markers_and_correct_clearing_note(self):
        rendered = []
        original = Figure.savefig

        def observe(fig, path, *args, **kwargs):
            # Observe the real renderer boundary, never substitute a figure function.
            self.assertEqual(kwargs.get("format"), "png")
            self.assertTrue(str(path).endswith(".png.tmp"))
            rendered.append((Path(path).name,
                             [t.get_text() for t in fig.findobj(figures.matplotlib.text.Text)],
                             [[list(line.get_xdata()) for line in ax.lines] for ax in fig.axes],
                             [[(collection.get_label(), len(collection.get_offsets()))
                               for collection in ax.collections] for ax in fig.axes]))
            return original(fig, path, *args, **kwargs)

        with patch.object(Figure, "savefig", observe):
            receipt = self.run_main()
        self.assertEqual(len(rendered), 6)
        boundary = figures.mdates.datestr2num("2014-02-01")
        con = duckdb.connect()
        expected = con.execute("""SELECT category,
                                  count(*) FILTER (WHERE month < DATE '2014-02-01'), count(*)
                                  FROM read_parquet(?)
                                  WHERE category IN ('Category A', 'Category B')
                                  GROUP BY category ORDER BY category""",
                               [str(self.root / "data/processed/coe_exercises.parquet")]).fetchall()
        con.close()
        for name, texts, lines, collections in rendered:
            text = "\n".join(texts)
            if name.startswith(("f1", "f2")):
                self.assertIn("Feb 2014", text)
                # Two A/B timeline panels, not just a caption with no plotted marker.
                self.assertEqual(sum(any(len(x) == 2 and x == [boundary, boundary]
                                         for x in axis) for axis in lines), 2)
            if name.startswith(("f1", "f3")):
                self.assertIn("common auction clearing premium", text)
                self.assertIn("not PQP", text)
                self.assertNotIn("lowest successful bid", text)
            if name.startswith("f3"):
                self.assertIn("earlier definitions", text)
                self.assertIn("not comparable populations", text)
                for axis, (_, count, total) in zip(collections, expected):
                    historical = [n for label, n in axis if "earlier definitions" in label]
                    self.assertEqual(historical, [count])
                    self.assertEqual(sum(n for _, n in axis), total, "full history was dropped")
            published = self.root / "reports/figures" / name.removesuffix(".tmp")
            self.assertTrue(published.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertEqual(published.read_bytes(), (self.root / "docs/img" / published.name).read_bytes())
        self.assertNotIn("[FAIL]", receipt)
        self.assertEqual(receipt.count("in-bounds"), 6)
        self.assertEqual(receipt.count("annotation overlaps"), 6)
        self.assertEqual(receipt.count("legend vs annotations"), 6)


if __name__ == "__main__":
    unittest.main()
