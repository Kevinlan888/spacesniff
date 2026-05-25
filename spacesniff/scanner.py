from __future__ import annotations

import os
from pathlib import Path

from spacesniff.models import DirectorySnapshot, EntryInfo, ScanStatus


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


def list_entries(path: Path) -> DirectorySnapshot:
    entries: list[EntryInfo] = []
    with os.scandir(path) as iterator:
        for item in iterator:
            item_path = Path(item.path)
            try:
                stat_result = item.stat(follow_symlinks=False)
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


def count_children(path: Path) -> int | None:
    try:
        with os.scandir(path) as iterator:
            return sum(1 for _ in iterator)
    except OSError:
        return None


def get_entry_details(entry: EntryInfo) -> EntryInfo:
    if not entry.is_dir or entry.child_count is not None:
        return entry
    return EntryInfo(
        path=entry.path,
        name=entry.name,
        is_dir=entry.is_dir,
        direct_size=entry.direct_size,
        aggregate_size=entry.aggregate_size,
        modified_at=entry.modified_at,
        child_count=count_children(entry.path),
        status=entry.status,
        error=entry.error,
    )


def compute_directory_size(path: Path) -> tuple[int | None, str | None]:
    total = 0
    try:
        with os.scandir(path) as iterator:
            for item in iterator:
                try:
                    if item.is_symlink():
                        continue
                    if item.is_dir(follow_symlinks=False):
                        size, error = compute_directory_size(Path(item.path))
                        if size is not None:
                            total += size
                        if error is not None:
                            return total, error
                    else:
                        total += item.stat(follow_symlinks=False).st_size
                except OSError as exc:
                    return total, str(exc)
    except OSError as exc:
        return None, str(exc)
    return total, None


def iter_directory_sizes(path: Path):
    snapshot = list_entries(path)
    for entry in snapshot.entries:
        if not entry.is_dir:
            continue
        yield entry.path, compute_directory_size(entry.path)


def _sort_key(entry: EntryInfo) -> tuple[int, int, str]:
    if entry.aggregate_size is None:
        return (1, 0, entry.name.lower())
    return (0, -entry.aggregate_size, entry.name.lower())
