from __future__ import annotations

import fnmatch
import os
import sys
from pathlib import Path

from spacesniff.models import DirectorySnapshot, EntryInfo, ScanOptions, ScanStatus

LINUX_VIRTUAL_FILESYSTEM_ROOTS = (
    Path("/proc"),
    Path("/sys"),
    Path("/dev"),
    Path("/run"),
)


def build_scan_options(
    root_path: Path,
    *,
    one_file_system: bool = False,
    exclude_patterns: tuple[str, ...] = (),
) -> ScanOptions:
    root_device = None
    if one_file_system:
        root_device = root_path.stat(follow_symlinks=False).st_dev

    ignore_virtual = sys.platform.startswith("linux")
    virtual_roots = tuple(
        candidate
        for candidate in LINUX_VIRTUAL_FILESYSTEM_ROOTS
        if candidate == root_path or candidate in root_path.parents or root_path in candidate.parents
    )
    return ScanOptions(
        root_path=root_path,
        one_file_system=one_file_system,
        exclude_patterns=exclude_patterns,
        ignore_virtual_filesystems=ignore_virtual,
        virtual_roots=virtual_roots,
        root_device=root_device,
    )


def format_bytes(num_bytes: int | None) -> str:
    if num_bytes is None:
        return "Scanning..."
    if num_bytes < 1024:
        return f"{num_bytes} B"
    value = float(num_bytes)
    for unit in ("KB", "MB", "GB", "TB", "PB"):
        value /= 1024
        if value < 1024:
            return f"{value:.1f} {unit}"
    return f"{value:.1f} EB"


def list_entries(path: Path, options: ScanOptions) -> DirectorySnapshot:
    entries: list[EntryInfo] = []
    with os.scandir(path) as iterator:
        for item in iterator:
            item_path = Path(item.path)
            if should_skip_path(item_path, options):
                continue
            try:
                stat_result = item.stat(follow_symlinks=False)
                if should_skip_device(stat_result.st_dev, options):
                    continue
                is_dir = item.is_dir(follow_symlinks=False)
            except OSError as exc:
                entries.append(
                    EntryInfo(
                        path=item_path,
                        name=item.name,
                        is_dir=False,
                        direct_size=None,
                        aggregate_size=None,
                        modified_at=None,
                        child_count=None,
                        status=ScanStatus.ERROR,
                        error=str(exc),
                    )
                )
                continue

            entries.append(
                EntryInfo(
                    path=item_path,
                    name=item.name,
                    is_dir=is_dir,
                    direct_size=stat_result.st_size if not is_dir else None,
                    aggregate_size=None if is_dir else stat_result.st_size,
                    modified_at=stat_result.st_mtime,
                    child_count=None,
                    status=ScanStatus.PENDING if is_dir else ScanStatus.READY,
                )
            )

    entries.sort(key=_sort_key)
    return DirectorySnapshot(path=path, entries=entries)


def count_children(path: Path, options: ScanOptions) -> int | None:
    try:
        with os.scandir(path) as iterator:
            count = 0
            for item in iterator:
                item_path = Path(item.path)
                if should_skip_path(item_path, options):
                    continue
                try:
                    stat_result = item.stat(follow_symlinks=False)
                except OSError:
                    continue
                if should_skip_device(stat_result.st_dev, options):
                    continue
                count += 1
            return count
    except OSError:
        return None


def get_entry_details(entry: EntryInfo, options: ScanOptions) -> EntryInfo:
    if not entry.is_dir or entry.child_count is not None:
        return entry
    return EntryInfo(
        path=entry.path,
        name=entry.name,
        is_dir=entry.is_dir,
        direct_size=entry.direct_size,
        aggregate_size=entry.aggregate_size,
        modified_at=entry.modified_at,
        child_count=count_children(entry.path, options),
        status=entry.status,
        error=entry.error,
    )


def compute_directory_size(path: Path, options: ScanOptions) -> tuple[int | None, str | None]:
    total = 0
    try:
        with os.scandir(path) as iterator:
            for item in iterator:
                try:
                    item_path = Path(item.path)
                    if item.is_symlink() or should_skip_path(item_path, options):
                        continue
                    stat_result = item.stat(follow_symlinks=False)
                    if should_skip_device(stat_result.st_dev, options):
                        continue
                    if item.is_dir(follow_symlinks=False):
                        size, error = compute_directory_size(item_path, options)
                        if size is not None:
                            total += size
                        if error is not None:
                            return total, error
                    else:
                        total += stat_result.st_size
                except OSError as exc:
                    return total, str(exc)
    except OSError as exc:
        return None, str(exc)
    return total, None


def iter_directory_sizes(path: Path, options: ScanOptions):
    snapshot = list_entries(path, options)
    for entry in snapshot.entries:
        if not entry.is_dir:
            continue
        yield entry.path, compute_directory_size(entry.path, options)


def should_skip_path(path: Path, options: ScanOptions) -> bool:
    if path == options.root_path:
        return False
    if options.ignore_virtual_filesystems:
        for virtual_root in options.virtual_roots:
            if path == virtual_root or virtual_root in path.parents:
                return True
    path_text = str(path)
    for pattern in options.exclude_patterns:
        if fnmatch.fnmatch(path.name, pattern) or fnmatch.fnmatch(path_text, pattern):
            return True
        if path_text.startswith(pattern.rstrip(os.sep) + os.sep):
            return True
        if path_text == pattern.rstrip(os.sep):
            return True
    return False


def should_skip_device(device: int, options: ScanOptions) -> bool:
    return options.one_file_system and options.root_device is not None and device != options.root_device


def _sort_key(entry: EntryInfo) -> tuple[int, int, str]:
    if entry.aggregate_size is None:
        return (1, 0, entry.name.lower())
    return (0, -entry.aggregate_size, entry.name.lower())
