from __future__ import annotations

import argparse
import os
from pathlib import Path

from spacesniff.scanner import build_scan_options


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spacesniff",
        description="Interactive terminal disk usage explorer.",
    )
    parser.add_argument("path", help="Root directory to scan.")
    parser.add_argument(
        "--one-file-system",
        action="store_true",
        help="Do not cross filesystem boundaries while scanning.",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="PATTERN",
        help="Exclude a file, directory name, glob, or absolute path prefix. Repeatable.",
    )
    return parser


def validate_root(path_arg: str) -> tuple[Path | None, str | None]:
    root = Path(path_arg).expanduser().resolve()
    if not root.exists():
        return None, f"path does not exist: {root}"
    if not root.is_dir():
        return None, f"path is not a directory: {root}"
    if not os.access(root, os.R_OK | os.X_OK):
        return None, f"path is not readable: {root}"
    return root, None


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    root, error = validate_root(args.path)
    if error is not None or root is None:
        parser.exit(2, f"spacesniff: error: {error}\n")

    options = build_scan_options(
        root,
        one_file_system=args.one_file_system,
        exclude_patterns=tuple(Path(pattern).expanduser().resolve().as_posix() if pattern.startswith(("~", "/")) else pattern for pattern in args.exclude),
    )

    try:
        from spacesniff.app import run_app
    except ModuleNotFoundError as exc:
        if exc.name == "textual":
            parser.exit(
                1,
                "spacesniff: error: textual is not installed. "
                "Run `python3 -m pip install -e .` first.\n",
            )
        raise

    run_app(root, options)
    return 0
