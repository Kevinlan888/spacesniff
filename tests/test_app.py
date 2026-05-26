from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from spacesniff.app import SpaceSnifferApp
from spacesniff.scanner import build_scan_options


class TrackingSpaceSnifferApp(SpaceSnifferApp):
    def __init__(self, root_path: Path) -> None:
        super().__init__(root_path, build_scan_options(root_path))
        self.started_scans: list[Path] = []

    def start_scan(self, path: Path) -> None:
        self.started_scans.append(path)
        self.scanning_paths.discard(path)
        self.scanned_paths.add(path)


class AppInteractionTests(unittest.IsolatedAsyncioTestCase):
    async def test_enter_opens_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            child = root / "child"
            child.mkdir()
            (child / "nested.txt").write_text("hello", encoding="utf-8")

            app = SpaceSnifferApp(root, build_scan_options(root))

            async with app.run_test() as pilot:
                await pilot.pause()
                await pilot.press("enter")
                await pilot.pause()

            self.assertEqual(app.current_path, child)

    async def test_back_navigation_uses_cached_parent_without_rescan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            child = root / "child"
            child.mkdir()
            (child / "nested.txt").write_text("hello", encoding="utf-8")

            app = TrackingSpaceSnifferApp(root)

            async with app.run_test() as pilot:
                await pilot.pause()
                await pilot.press("enter")
                await pilot.pause()
                await pilot.press("backspace")
                await pilot.pause()

            self.assertEqual(app.current_path, root)
            self.assertEqual(app.started_scans, [root, child])

    async def test_refresh_restarts_scan_for_current_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "child").mkdir()

            app = TrackingSpaceSnifferApp(root)

            async with app.run_test() as pilot:
                await pilot.pause()
                await pilot.press("r")
                await pilot.pause()

            self.assertEqual(app.started_scans, [root, root])

    async def test_delete_directory_requires_confirmation_and_removes_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            child = root / "child"
            child.mkdir()
            (child / "nested.txt").write_text("hello", encoding="utf-8")

            app = SpaceSnifferApp(root, build_scan_options(root))

            async with app.run_test() as pilot:
                await pilot.pause()
                await pilot.press("d")
                await pilot.pause()
                self.assertTrue(child.exists())
                await pilot.press("tab", "enter")
                await pilot.pause()

            self.assertFalse(child.exists())
            self.assertEqual(app.current_path, root)

    async def test_delete_cancel_keeps_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            child = root / "child"
            child.mkdir()

            app = SpaceSnifferApp(root, build_scan_options(root))

            async with app.run_test() as pilot:
                await pilot.pause()
                await pilot.press("d")
                await pilot.pause()
                await pilot.press("enter")
                await pilot.pause()

            self.assertTrue(child.exists())


if __name__ == "__main__":
    unittest.main()
