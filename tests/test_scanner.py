from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from spacesniff.models import ScanStatus
from spacesniff.scanner import compute_directory_size, format_bytes, get_entry_details, list_entries


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

            snapshot = list_entries(root)
            self.assertEqual([entry.name for entry in snapshot.entries], ["file.txt", "child"])

            file_entry = next(entry for entry in snapshot.entries if entry.name == "file.txt")
            dir_entry = next(entry for entry in snapshot.entries if entry.name == "child")

            self.assertFalse(file_entry.is_dir)
            self.assertEqual(file_entry.aggregate_size, 4)
            self.assertEqual(file_entry.status, ScanStatus.READY)

            self.assertTrue(dir_entry.is_dir)
            self.assertIsNone(dir_entry.aggregate_size)
            self.assertEqual(dir_entry.status, ScanStatus.PENDING)

            size, error = compute_directory_size(root / "child")
            self.assertEqual(size, 6)
            self.assertIsNone(error)

    def test_get_entry_details_counts_children(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "child").mkdir()
            (root / "child" / "a").write_text("1", encoding="utf-8")
            (root / "child" / "b").write_text("2", encoding="utf-8")

            entry = next(item for item in list_entries(root).entries if item.name == "child")
            detailed = get_entry_details(entry)
            self.assertEqual(detailed.child_count, 2)


if __name__ == "__main__":
    unittest.main()
