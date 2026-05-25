from __future__ import annotations

from dataclasses import dataclass
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
