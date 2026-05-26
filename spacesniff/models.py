from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class ScanStatus(StrEnum):
    PENDING = "pending"
    SCANNING = "scanning"
    READY = "ready"
    ERROR = "error"


@dataclass(slots=True)
class EntryInfo:
    path: Path
    name: str
    is_dir: bool
    direct_size: int | None
    aggregate_size: int | None
    modified_at: float | None
    child_count: int | None
    status: ScanStatus
    error: str | None = None


@dataclass(slots=True)
class DirectorySnapshot:
    path: Path
    entries: list[EntryInfo]


@dataclass(slots=True)
class ScanOptions:
    root_path: Path
    one_file_system: bool = False
    exclude_patterns: tuple[str, ...] = ()
    ignore_virtual_filesystems: bool = True
    virtual_roots: tuple[Path, ...] = field(default_factory=tuple)
    root_device: int | None = None
