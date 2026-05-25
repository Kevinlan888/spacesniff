from __future__ import annotations

import shutil
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Label, ListItem, ListView, Static

from spacesniff.clipboard import copy_to_clipboard
from spacesniff.models import EntryInfo, ScanStatus
from spacesniff.scanner import format_bytes, get_entry_details, iter_directory_sizes, list_entries


class DeleteConfirmScreen(ModalScreen[bool]):
    CSS = """
    DeleteConfirmScreen {
        align: center middle;
    }

    #delete-dialog {
        width: 72;
        max-width: 90%;
        border: round $error;
        background: $surface;
        padding: 1 2;
    }

    #delete-actions {
        height: auto;
        align-horizontal: right;
        padding-top: 1;
    }

    .delete-path {
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel", show=False),
    ]

    def __init__(self, entry: EntryInfo) -> None:
        super().__init__()
        self.entry = entry

    def compose(self) -> ComposeResult:
        item_type = "directory" if self.entry.is_dir else "file"
        yield Vertical(
            Static(f"Delete this {item_type}?"),
            Static(self.entry.name),
            Static(str(self.entry.path), classes="delete-path"),
            Horizontal(
                Button("Cancel", id="cancel", variant="default"),
                Button("Delete", id="confirm", variant="error"),
                id="delete-actions",
            ),
            id="delete-dialog",
        )

    @on(Button.Pressed, "#cancel")
    def cancel_delete(self) -> None:
        self.dismiss(False)

    @on(Button.Pressed, "#confirm")
    def confirm_delete(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class EntryRow(ListItem):
    DEFAULT_CSS = """
    EntryRow {
        height: 1;
    }

    .entry-line {
        width: 100%;
        height: 1;
    }

    .entry-name {
        width: 1fr;
    }

    .entry-size {
        width: 14;
        text-align: right;
    }
    """

    def __init__(self, entry: EntryInfo) -> None:
        self.name_label = Label("", markup=False, classes="entry-name")
        self.size_label = Label("", markup=False, classes="entry-size")
        self.line = Horizontal(self.name_label, self.size_label, classes="entry-line")
        super().__init__(self.line)
        self.entry = entry
        self.refresh_line()

    def refresh_line(self) -> None:
        name_prefix = "[DIR] " if self.entry.is_dir else "      "
        self.name_label.update(f"{name_prefix}{self.entry.name}")
        self.size_label.update(self._size_text())

    def _size_text(self) -> str:
        if self.entry.status == ScanStatus.ERROR:
            return "Error"
        if self.entry.is_dir and self.entry.aggregate_size is None:
            return "Scanning..."
        return format_bytes(self.entry.aggregate_size)


class SpaceSnifferApp(App[None]):
    CSS = """
    Screen {
        layout: vertical;
    }

    #body {
        height: 1fr;
    }

    #entries {
        width: 2fr;
        border: round $accent;
    }

    #details {
        width: 1fr;
        border: round $accent;
        padding: 1 2;
    }

    #status {
        height: 1;
        padding: 0 1;
        background: $surface;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("up", "cursor_up", "Up", show=False),
        Binding("down", "cursor_down", "Down", show=False),
        Binding("enter", "open_selection", "Open"),
        Binding("backspace", "go_up", "Back"),
        Binding("r", "refresh_directory", "Refresh"),
        Binding("d", "delete_selection", "Delete"),
        Binding("c", "copy_path", "Copy Path"),
        Binding("i", "refresh_details", "Refresh Details"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, root_path: Path) -> None:
        super().__init__()
        self.root_path = root_path
        self.current_path = root_path
        self.history: list[Path] = []
        self.snapshot_cache: dict[Path, list[EntryInfo]] = {}
        self.row_index: dict[Path, EntryRow] = {}
        self.selected_entry: EntryInfo | None = None
        self.scanning_paths: set[Path] = set()
        self.scanned_paths: set[Path] = set()
        self.scan_tokens: dict[Path, int] = {}
        self.next_scan_token = 0

    def compose(self) -> ComposeResult:
        yield Horizontal(
            ListView(id="entries"),
            Static(id="details"),
            id="body",
        )
        yield Static("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "spacesniff"
        self.load_directory(self.root_path)
        self.query_one(ListView).focus()

    def action_cursor_up(self) -> None:
        self.query_one(ListView).action_cursor_up()

    def action_cursor_down(self) -> None:
        self.query_one(ListView).action_cursor_down()

    def action_open_selection(self) -> None:
        if self.selected_entry is None or not self.selected_entry.is_dir:
            self.action_refresh_details()
            return
        self.history.append(self.current_path)
        self.load_directory(self.selected_entry.path)

    def action_go_up(self) -> None:
        if self.current_path == self.root_path and not self.history:
            self.set_status("already at the scan root")
            return
        target = self.history.pop() if self.history else self.current_path.parent
        if self.root_path not in [target, *target.parents] and target != self.root_path:
            target = self.root_path
        self.load_directory(target)

    def action_refresh_directory(self) -> None:
        self.invalidate_subtree(self.current_path)
        self.load_directory(self.current_path, force_refresh=True)

    def action_delete_selection(self) -> None:
        if self.selected_entry is None:
            self.set_status("no selection")
            return
        self.push_screen(
            DeleteConfirmScreen(self.selected_entry),
            self._handle_delete_confirmation,
        )

    def _handle_delete_confirmation(self, confirmed: bool) -> None:
        if not confirmed or self.selected_entry is None:
            self.set_status("delete cancelled")
            return
        self.delete_entry(self.selected_entry)

    def delete_entry(self, entry: EntryInfo) -> None:
        try:
            if entry.is_dir:
                shutil.rmtree(entry.path)
            else:
                entry.path.unlink()
        except OSError as exc:
            self.set_status(f"delete failed for {entry.path}: {exc}")
            return

        self.invalidate_subtree(entry.path)
        parent_entries = self.snapshot_cache.get(self.current_path)
        if parent_entries is not None:
            self.snapshot_cache[self.current_path] = [
                item for item in parent_entries if item.path != entry.path
            ]
        self.selected_entry = None
        self.load_directory(self.current_path)
        self.set_status(f"deleted {entry.path}")

    def action_copy_path(self) -> None:
        if self.selected_entry is None:
            self.set_status("no selection")
            return
        ok, message = copy_to_clipboard(str(self.selected_entry.path))
        if ok:
            self.set_status(message)
            return
        self.set_status(f"{message}: {self.selected_entry.path}")

    def action_refresh_details(self) -> None:
        if self.selected_entry is None:
            self.update_details(None)
            return
        self.selected_entry = get_entry_details(self.selected_entry)
        self.update_details(self.selected_entry)
        row = self.row_index.get(self.selected_entry.path)
        if row is not None:
            row.entry = self.selected_entry
            row.refresh_line()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if not isinstance(event.item, EntryRow):
            return
        self.selected_entry = event.item.entry
        self.update_details(self.selected_entry)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if not isinstance(event.item, EntryRow):
            return
        self.selected_entry = event.item.entry
        self.update_details(self.selected_entry)
        if self.selected_entry.is_dir:
            self.history.append(self.current_path)
            self.load_directory(self.selected_entry.path)

    def load_directory(self, path: Path, force_refresh: bool = False) -> None:
        self.current_path = path

        snapshot_entries = self.snapshot_cache.get(path)
        if snapshot_entries is None:
            try:
                snapshot = list_entries(path)
            except OSError as exc:
                self.set_status(f"cannot open {path}: {exc}")
                if self.history:
                    fallback = self.history.pop()
                    if fallback != path:
                        self.current_path = fallback
                        self.load_directory(fallback)
                else:
                    self.update_details(None)
                return
            snapshot_entries = snapshot.entries
            self.snapshot_cache[path] = snapshot_entries

        self._render_entries(snapshot_entries)

        if force_refresh or path not in self.scanned_paths and path not in self.scanning_paths:
            self.set_status(f"scanning {path}")
            self.start_scan(path)
            return
        if path in self.scanning_paths:
            self.set_status(f"scanning cached {path}")
            return
        self.set_status(f"loaded from cache: {path}")

    def start_scan(self, path: Path) -> None:
        self.next_scan_token += 1
        token = self.next_scan_token
        self.scan_tokens[path] = token
        self.scanning_paths.add(path)
        self.scanned_paths.discard(path)
        self.scan_directory(path, token)

    def invalidate_subtree(self, path: Path) -> None:
        descendants = [cached_path for cached_path in self.snapshot_cache if cached_path == path or path in cached_path.parents]
        for cached_path in descendants:
            self.snapshot_cache.pop(cached_path, None)
            self.scanning_paths.discard(cached_path)
            self.scanned_paths.discard(cached_path)
            self.scan_tokens.pop(cached_path, None)

    def update_details(self, entry: EntryInfo | None) -> None:
        panel = self.query_one("#details", Static)
        if entry is None:
            panel.update(f"Current path:\n{self.current_path}\n\nThis directory is empty.")
            return
        detail_entry = get_entry_details(entry)
        kind = "Directory" if detail_entry.is_dir else "File"
        modified = (
            datetime.fromtimestamp(detail_entry.modified_at).strftime("%Y-%m-%d %H:%M:%S")
            if detail_entry.modified_at is not None
            else "Unknown"
        )
        child_count = "-"
        if detail_entry.is_dir:
            child_count = "Unknown" if detail_entry.child_count is None else str(detail_entry.child_count)
        status = detail_entry.status.value
        error = f"\nError: {detail_entry.error}" if detail_entry.error else ""
        panel.update(
            "\n".join(
                [
                    f"Current path:\n{self.current_path}",
                    "",
                    f"Name: {detail_entry.name}",
                    f"Path: {detail_entry.path}",
                    f"Type: {kind}",
                    f"Size: {format_bytes(detail_entry.aggregate_size)}",
                    f"Modified: {modified}",
                    f"Children: {child_count}",
                    f"Status: {status}",
                ]
            )
            + error
        )

    def set_status(self, message: str) -> None:
        self.query_one("#status", Static).update(message)

    @work(thread=True)
    def scan_directory(self, path: Path, token: int) -> None:
        for child_path, (size, error) in iter_directory_sizes(path):
            self.call_from_thread(self.apply_scan_result, path, token, child_path, size, error)
        self.call_from_thread(self.finish_scan, path, token)

    def apply_scan_result(
        self,
        directory: Path,
        token: int,
        child_path: Path,
        size: int | None,
        error: str | None,
    ) -> None:
        if token != self.scan_tokens.get(directory):
            return

        cached = self.snapshot_cache.get(directory)
        if cached is None:
            return

        for index, entry in enumerate(cached):
            if entry.path != child_path:
                continue
            new_status = ScanStatus.ERROR if error else ScanStatus.READY
            updated = replace(entry, aggregate_size=size, status=new_status, error=error)
            cached[index] = updated
            row = self.row_index.get(child_path)
            if row is not None and directory == self.current_path:
                row.entry = updated
                row.refresh_line()
            if self.selected_entry is not None and self.selected_entry.path == child_path:
                self.selected_entry = updated
                if directory == self.current_path:
                    self.update_details(updated)
            break

    def finish_scan(self, path: Path, token: int) -> None:
        if token != self.scan_tokens.get(path):
            return

        cached = self.snapshot_cache.get(path)
        if cached is not None:
            cached.sort(key=lambda item: (item.aggregate_size is None, -(item.aggregate_size or 0), item.name.lower()))

        self.scanning_paths.discard(path)
        self.scanned_paths.add(path)

        if path == self.current_path:
            self._render_entries(cached or [])
            self.set_status(f"loaded {path}")

    def _render_entries(self, entries: list[EntryInfo]) -> None:
        list_view = self.query_one(ListView)
        selected_path = self.selected_entry.path if self.selected_entry is not None else None
        list_view.clear()
        self.row_index.clear()
        selected_index = 0
        for index, entry in enumerate(entries):
            row = EntryRow(entry)
            self.row_index[entry.path] = row
            list_view.append(row)
            if selected_path == entry.path:
                selected_index = index
        if entries:
            list_view.index = selected_index
            self.selected_entry = entries[selected_index]
            self.update_details(self.selected_entry)
        else:
            self.selected_entry = None
            self.update_details(None)


def run_app(root_path: Path) -> None:
    app = SpaceSnifferApp(root_path)
    app.run()
