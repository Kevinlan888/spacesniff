# spacesniff

A Python terminal disk usage explorer inspired by SpaceSniffer.

## Setup

Create a project-local virtual environment and install the package:

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

## Usage

Scan a specific root directory:

```bash
.venv/bin/spacesniff /home/kevin
```

## Standalone Build

Build a standalone executable with PyInstaller:

```bash
.venv/bin/pip install pyinstaller
./scripts/build-standalone.sh
```

The output binary will be created at:

```bash
dist/spacesniff
```

## Features

- Interactive terminal UI built with Textual
- Up/down navigation with `Enter` to open directories
- Right-side detail panel for the current selection
- Background directory size scanning with cached results
- Manual refresh for the current directory subtree
- Delete files or directories with a confirmation dialog that shows the full path
- Copy the selected path to the system clipboard when available

## Controls

- `Up` / `Down`: move selection
- `Enter`: open directory
- `Backspace`: go to parent directory
- `r`: refresh current directory and invalidate its cached subtree
- `d`: delete selected file or directory after confirmation
- `c`: copy current path
- `i`: refresh current item details
- `q`: quit

## Verification

Run the test suite:

```bash
.venv/bin/python -m unittest discover -s tests -v
```
