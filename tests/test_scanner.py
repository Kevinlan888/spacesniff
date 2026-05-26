from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from spacesniff.models import ScanStatus
from spacesniff.scanner import (
    build_scan_options,
    compute_directory_size,
    format_bytes,
    get_entry_details,
    list_entries,
    should_skip_path,
)


class ScannerTests(unittest.TestCase):
    def test_format_bytes(self) -> None:
        self.assertEqual(format_bytes(512), "512 B")
        self.assertEqual(format_bytes(1024), "1.0 KB")
        self.assertEqual(format_bytes(None), "Scanning...")

    def test_list_entries_and_compute_directory_size(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "child").mkdir()
            (root / "file.txt").write_text("abcd", encoding="utf-8")
            (root / "child" / "nested.bin").write_bytes(b"123456")

            options = build_scan_options(root)
            snapshot = list_entries(root, options)
            self.assertEqual([entry.name for entry in snapshot.entries], ["file.txt", "child"])

            file_entry = next(entry for entry in snapshot.entries if entry.name == "file.txt")
            dir_entry = next(entry for entry in snapshot.entries if entry.name == "child")

            self.assertFalse(file_entry.is_dir)
            self.assertEqual(file_entry.aggregate_size, 4)
            self.assertEqual(file_entry.status, ScanStatus.READY)

            self.assertTrue(dir_entry.is_dir)
            self.assertIsNone(dir_entry.aggregate_size)
            self.assertEqual(dir_entry.status, ScanStatus.PENDING)

            size, error = compute_directory_size(root / "child", options)
            self.assertEqual(size, 6)
            self.assertIsNone(error)

    def test_get_entry_details_counts_children(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "child").mkdir()
            (root / "child" / "a").write_text("1", encoding="utf-8")
            (root / "child" / "b").write_text("2", encoding="utf-8")

            options = build_scan_options(root)
            entry = next(item for item in list_entries(root, options).entries if item.name == "child")
            detailed = get_entry_details(entry, options)
            self.assertEqual(detailed.child_count, 2)

    def test_exclude_patterns_filter_by_name_and_path_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "node_modules").mkdir()
            (root / "node_modules" / "cache.bin").write_bytes(b"123")
            (root / "keep").mkdir()
            (root / "keep" / "file.txt").write_text("ok", encoding="utf-8")

            options = build_scan_options(
                root,
                exclude_patterns=("node_modules", str((root / "keep").resolve())),
            )
            snapshot = list_entries(root, options)
            self.assertEqual(snapshot.entries, [])

    def test_linux_virtual_filesystem_roots_are_skipped(self) -> None:
        root = Path("/")
        options = build_scan_options(root)
        self.assertTrue(should_skip_path(Path("/proc"), options))
        self.assertTrue(should_skip_path(Path("/proc/1"), options))
        self.assertTrue(should_skip_path(Path("/sys/class"), options))
        self.assertFalse(should_skip_path(Path("/home"), options))

    def test_one_file_system_skips_different_device_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "same").mkdir()
            (root / "other").mkdir()
            (root / "same.txt").write_text("same", encoding="utf-8")

            real_scandir = __import__("os").scandir

            class FakeDirEntry:
                def __init__(self, entry, fake_dev: int | None = None):
                    self._entry = entry
                    self.path = entry.path
                    self.name = entry.name
                    self._fake_dev = fake_dev

                def stat(self, *, follow_symlinks: bool = True):
                    result = self._entry.stat(follow_symlinks=follow_symlinks)
                    if self._fake_dev is None:
                        return result
                    return SimpleNamespace(
                        st_dev=self._fake_dev,
                        st_mode=result.st_mode,
                        st_ino=result.st_ino,
                        st_nlink=result.st_nlink,
                        st_uid=result.st_uid,
                        st_gid=result.st_gid,
                        st_size=result.st_size,
                        st_atime=result.st_atime,
                        st_mtime=result.st_mtime,
                        st_ctime=result.st_ctime,
                    )

                def is_dir(self, *, follow_symlinks: bool = True):
                    return self._entry.is_dir(follow_symlinks=follow_symlinks)

                def is_symlink(self):
                    return self._entry.is_symlink()

            class FakeScandir:
                def __init__(self, path):
                    self._path = Path(path)
                    self._entries = []

                def __enter__(self):
                    with real_scandir(self._path) as iterator:
                        for entry in iterator:
                            fake_dev = None
                            if Path(entry.path) == root / "other":
                                fake_dev = root.stat().st_dev + 999
                            self._entries.append(FakeDirEntry(entry, fake_dev=fake_dev))
                    return iter(self._entries)

                def __exit__(self, exc_type, exc, tb):
                    return False

            options = build_scan_options(root, one_file_system=True)
            with patch("spacesniff.scanner.os.scandir", lambda path: FakeScandir(path)):
                snapshot = list_entries(root, options)
            self.assertEqual([entry.name for entry in snapshot.entries], ["same.txt", "same"])


if __name__ == "__main__":
    unittest.main()
