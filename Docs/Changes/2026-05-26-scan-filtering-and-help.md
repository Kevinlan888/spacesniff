# Scan Filtering and Help Update

Date: 2026-05-26

## Summary

Added Linux-aware scan filtering defaults and new CLI filtering controls, then updated the README to document the new behavior and help output.

## Delivered

- Added default Linux virtual filesystem ignores for `/proc`, `/sys`, `/dev`, and `/run`.
- Added `--one-file-system` to prevent crossing filesystem boundaries during recursive scans.
- Added repeatable `--exclude PATTERN` support for file names, directory names, glob patterns, and absolute path prefixes.
- Threaded scan options through the TUI so navigation, refresh, and detail views all respect the same filters.
- Updated README usage examples and documented the new CLI options and Linux scanning defaults.

## Validation

Verified with:

```bash
.venv/bin/python -m spacesniff --help
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m compileall spacesniff tests
```

## Notes

- The filter defaults only auto-ignore virtual filesystems on Linux.
- `--exclude` is repeatable and combines cleanly with `--one-file-system`.
