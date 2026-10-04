"""Offline regression checks; every file mutation is in Hermes scratch."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src import download


def csv_bytes(newline="\n", premium="100", encoding="utf-8"):
    rows = [",".join(download.HEADER)]
    for year in range(2010, 2027):
        for month in range(1, 13):
            if year == 2026 and month > 9:
                break
            for round_no in (1, 2):
                for category in sorted(download.CATEGORIES):
                    rows.append(f"{year}-{month:02d},{round_no},{category},100,100,200,{premium}")
    return (newline.join(rows) + newline).encode(encoding)


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(self.tmp.cleanup)
        self.raw = Path(self.tmp.name)
        self.out = self.raw / download.FILE
        self.manifest = self.raw / "pull_manifest.json"
        self.enterContext(patch.object(download, "RAW", self.raw))
        self.enterContext(patch.object(download, "MANIFEST", self.manifest))
        self.old = csv_bytes()
        self.new = csv_bytes(premium="101")

    def cache(self, data=None):
        data = self.old if data is None else data
        self.out.write_bytes(data)
        info, problems = download.validate(data.decode("utf-8"))
        self.assertFalse(problems)
        info.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        self.manifest.write_text(json.dumps({"files": {download.FILE: info}}), encoding="utf-8")

    def run_download(self, data=None, force=False, cp1252=False):
        data = self.new if data is None else data
        output = io.TextIOWrapper(io.BytesIO(), encoding="cp1252" if cp1252 else "utf-8")
        def get(url, ref="https://data.gov.sg/"):
            return data if url == "https://fixture.test/data.csv" else json.dumps({"data": {"url": "https://fixture.test/data.csv"}}).encode()
        with patch.object(download, "get", side_effect=get) as network, patch("sys.argv", ["download.py"] + (["--force"] if force else [])), contextlib.redirect_stdout(output):
            result = download.main()
        return result, network.call_count

    def test_fresh_download_on_cp1252(self):
        self.assertEqual(self.run_download(cp1252=True)[0], 0)
        self.assertEqual(self.out.read_bytes(), self.new)
        self.assertTrue(self.manifest.is_file())

    def test_corrupt_cache_with_manifest_is_rejected(self):
        self.cache()
        before = self.manifest.read_bytes()
        self.out.write_bytes(b"not a csv")
        with self.assertRaises(SystemExit):
            self.run_download()
        self.assertEqual(self.manifest.read_bytes(), before)

    def test_valid_cache_is_checked_without_network_or_manifest_rewrite(self):
        self.cache(csv_bytes(newline="\r\n"))
        before = self.manifest.read_bytes()
        self.assertEqual(self.run_download(cp1252=True), (0, 0))
        self.assertEqual(self.manifest.read_bytes(), before)

    def test_cache_without_manifest_creates_byte_hash_without_network(self):
        data = csv_bytes(newline="\r\n")
        self.out.write_bytes(data)
        self.assertEqual(self.run_download(cp1252=True), (0, 0))
        self.assertEqual(self.out.read_bytes(), data)
        info = json.loads(self.manifest.read_text())["files"][download.FILE]
        self.assertEqual(info["sha256"], hashlib.sha256(data).hexdigest())

    def test_matching_manifest_does_not_bypass_structural_validation(self):
        self.out.write_bytes(b"not a csv")
        self.manifest.write_text(json.dumps({"files": {download.FILE: {"sha256": hashlib.sha256(b"not a csv").hexdigest()}}}))
        with self.assertRaises(SystemExit) as error:
            self.run_download()
        self.assertIn("failed validation", str(error.exception))

    def test_force_replaces_changed_cache_with_matching_manifest(self):
        self.cache()
        self.out.write_bytes(csv_bytes(premium="999"))
        self.assertEqual(self.run_download(force=True)[0], 0)
        self.assertEqual(self.out.read_bytes(), self.new)
        info = json.loads(self.manifest.read_text())["files"][download.FILE]
        self.assertEqual(info["sha256"], hashlib.sha256(self.new).hexdigest())

    def test_pair_publication_failure_restores_existing_and_absent_targets(self):
        replace = Path.replace
        for existing in (False, True):
            for failed_target in (self.out, self.manifest):
                with self.subTest(existing=existing, failed_target=failed_target):
                    self.out.unlink(missing_ok=True)
                    self.manifest.unlink(missing_ok=True)
                    if existing:
                        self.cache()
                        before = self.manifest.read_bytes()
                    def fail(stage, target):
                        if stage.suffix == ".part" and target == failed_target:
                            raise OSError("injected promotion failure")
                        return replace(stage, target)
                    with patch.object(Path, "replace", fail), self.assertRaises(OSError):
                        self.run_download(force=True)
                    if existing:
                        self.assertEqual(self.out.read_bytes(), self.old)
                        self.assertEqual(self.manifest.read_bytes(), before)
                    else:
                        self.assertFalse(self.out.exists())
                        self.assertFalse(self.manifest.exists())
                    self.assertFalse(list(self.raw.glob("*.part")))

    def test_valid_changed_cache_is_rejected_without_blessing(self):
        self.cache()
        before = self.manifest.read_bytes()
        self.out.write_bytes(self.new)
        with self.assertRaises(SystemExit):
            self.run_download()
        self.assertEqual(self.manifest.read_bytes(), before)

    def test_invalid_manifest_is_rejected_without_overwriting(self):
        for value in (b"not json", b"{}", b"[]", b'{"files": null}', b'{"files": {"coe-bidding-results.csv": {"sha256": 5}}}'):
            with self.subTest(value=value):
                self.out.write_bytes(self.old)
                self.manifest.write_bytes(value)
                with self.assertRaises(SystemExit):
                    self.run_download()
                self.assertEqual(self.manifest.read_bytes(), value)

    def test_legacy_canonical_text_hash_is_not_silently_blessed(self):
        data = csv_bytes(newline="\r\n")
        self.cache(data)
        manifest = json.loads(self.manifest.read_text())
        manifest["files"][download.FILE]["sha256"] = hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()
        self.manifest.write_text(json.dumps(manifest))
        before = self.manifest.read_bytes()
        with self.assertRaises(SystemExit) as error:
            self.run_download()
        self.assertIn("does not match its manifest", str(error.exception))
        self.assertEqual(self.manifest.read_bytes(), before)

    def test_crlf_download_is_preserved_and_hashed_as_bytes(self):
        data = csv_bytes(newline="\r\n")
        self.assertEqual(self.run_download(data=data)[0], 0)
        self.assertEqual(self.out.read_bytes(), data)
        info = json.loads(self.manifest.read_text())["files"][download.FILE]
        self.assertEqual(info["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(info["bytes"], len(data))

    def test_invalid_utf8_preserves_existing_pair(self):
        self.cache()
        before = self.manifest.read_bytes()
        with self.assertRaises(SystemExit):
            self.run_download(data=self.new + b"\xff", force=True)
        self.assertEqual(self.out.read_bytes(), self.old)
        self.assertEqual(self.manifest.read_bytes(), before)

    def test_manifest_write_failure_preserves_raw(self):
        self.out.write_bytes(self.old)
        self.manifest.mkdir()
        with self.assertRaises(OSError):
            self.run_download(force=True)
        self.assertEqual(self.out.read_bytes(), self.old)


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR"))
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.pairs = [(self.root / f"stage{i}", self.root / f"target{i}") for i in range(3)]
        for stage, target in self.pairs:
            stage.write_bytes(b"new")
            target.write_bytes(b"old")

    def test_missing_stage_and_duplicate_targets_fail_before_publication(self):
        from src.publish import publish_files
        self.pairs[2][0].unlink()
        with self.assertRaises(FileNotFoundError):
            publish_files(self.pairs)
        self.pairs[2][0].write_bytes(b"new")
        with self.assertRaises(ValueError):
            publish_files(self.pairs + [(self.pairs[1][0], self.pairs[0][1])])
        for stage, target in self.pairs:
            self.assertEqual(target.read_bytes(), b"old")
            self.assertEqual(stage.read_bytes(), b"new")

    def test_backup_failure_does_not_change_any_target(self):
        from src import publish
        copy = publish.shutil.copy2
        def fail(source, backup):
            if source == self.pairs[1][1]:
                raise OSError("injected backup failure")
            return copy(source, backup)
        with patch.object(publish.shutil, "copy2", fail), self.assertRaises(OSError):
            publish.publish_files(self.pairs)
        for stage, target in self.pairs:
            self.assertEqual(target.read_bytes(), b"old")
            self.assertEqual(stage.read_bytes(), b"new")
        self.assertFalse(list(self.root.glob("*.bak")))

    def test_rollback_failure_retains_original_backups(self):
        from src.publish import publish_files
        replace = Path.replace
        def fail(stage, target):
            if stage == self.pairs[1][0] or (stage.suffix == ".bak" and target == self.pairs[0][1]):
                raise OSError("injected replacement failure")
            return replace(stage, target)
        with patch.object(Path, "replace", fail), self.assertRaises(RuntimeError) as error:
            publish_files(self.pairs)
        self.assertIn("retained backups", str(error.exception))
        backups = list(self.root.glob("*.bak"))
        self.assertTrue(backups)
        self.assertTrue(all(backup.read_bytes() == b"old" for backup in backups))
        self.assertTrue(any("target0" in backup.name for backup in backups))
        self.assertEqual(self.pairs[1][1].read_bytes(), b"old")

    def test_success_consumes_stages_and_removes_backups(self):
        from src.publish import publish_files
        publish_files(self.pairs)
        for stage, target in self.pairs:
            self.assertEqual(target.read_bytes(), b"new")
            self.assertFalse(stage.exists())
        self.assertFalse(list(self.root.glob("*.bak")))

    def test_batch_rolls_back_replacement_failure(self):
        from src import publish
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as directory:
            root = Path(directory)
            pairs = [(root / f"stage{i}", root / f"target{i}") for i in range(3)]
            replace = Path.replace
            for absent in (False, True):
                for failed_index in range(3):
                    for i, (stage, target) in enumerate(pairs):
                        stage.write_bytes(b"new")
                        target.unlink(missing_ok=True)
                        if not absent or i == 2:
                            target.write_bytes(b"old")
                    def fail(stage, target):
                        if stage == pairs[failed_index][0]:
                            raise OSError("injected promotion failure")
                        return replace(stage, target)
                    with patch.object(Path, "replace", fail), self.assertRaises(OSError):
                        publish.publish_files(pairs)
                    for i, (_, target) in enumerate(pairs):
                        if absent and i != 2:
                            self.assertFalse(target.exists())
                        else:
                            self.assertEqual(target.read_bytes(), b"old")


class TempDirectoryPortabilityTests(unittest.TestCase):
    def test_setup_without_tmpdir(self):
        with patch.dict(os.environ):
            os.environ.pop("TMPDIR", None)
            for cls in (DownloadTests, PublicationTests):
                case = cls()
                try:
                    case.setUp()
                    self.assertTrue(Path(case.tmp.name).is_dir())
                finally:
                    case.doCleanups()


if __name__ == "__main__":
    unittest.main()
