from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from spacesniff.cli import validate_root


class ValidateRootTests(unittest.TestCase):
    def test_rejects_missing_path(self) -> None:
        root, error = validate_root("/tmp/spacesniff-definitely-missing")
        self.assertIsNone(root)
        self.assertIn("does not exist", error or "")

    def test_rejects_file(self) -> None:
        with tempfile.NamedTemporaryFile() as handle:
            root, error = validate_root(handle.name)
            self.assertIsNone(root)
            self.assertIn("not a directory", error or "")

    def test_accepts_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, error = validate_root(temp_dir)
            self.assertEqual(root, Path(temp_dir).resolve())
            self.assertIsNone(error)

    def test_rejects_unreadable_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("spacesniff.cli.os.access", return_value=False):
                root, error = validate_root(temp_dir)
            self.assertIsNone(root)
            self.assertIn("not readable", error or "")
