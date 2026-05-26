# spacesniff

A Python terminal disk usage explorer inspired by SpaceSniffer.

## Platform Support

- Linux: supported
- macOS: expected to work, not yet verified in this repo
- Windows: supported from source, with a dedicated PowerShell standalone build script

## Setup

### Linux / macOS

Create a project-local virtual environment and install the package:

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

### Windows PowerShell

Create a project-local virtual environment and install the package:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\pip install -e .
```

## Usage

### Linux / macOS

```bash
.venv/bin/spacesniff /home/kevin
.venv/bin/spacesniff / --one-file-system --exclude node_modules --exclude /var/cache
```

### Windows PowerShell

```powershell
.\.venv\Scripts\spacesniff C:\Users\kevin
.\.venv\Scripts\spacesniff C:\ --exclude node_modules --exclude C:\Windows\Temp
```

## CLI Options

Current help output:

```text
usage: spacesniff [-h] [--one-file-system] [--exclude PATTERN] path
```

Options:

- `path`: root directory to scan
- `--one-file-system`: do not cross filesystem boundaries while scanning
- `--exclude PATTERN`: exclude a file name, directory name, glob, or absolute path prefix; repeatable

## Linux Scanning Defaults

On Linux, spacesniff ignores common virtual filesystem roots by default:

- `/proc`
- `/sys`
- `/dev`
- `/run`

This avoids scanning pseudo-filesystems that do not represent normal disk usage.

## Standalone Build

### Linux / macOS

```bash
.venv/bin/pip install pyinstaller
./scripts/build-standalone.sh
```

Output:

```bash
dist/spacesniff
```

### Windows PowerShell

```powershell
.\.venv\Scripts\pip install pyinstaller
.\scripts\build-standalone.ps1
```

Output:

```powershell
dist\spacesniff.exe
```

## Features

- Interactive terminal UI built with Textual
- Up/down navigation with `Enter` to open directories
- Right-side detail panel for the current selection
- Background directory size scanning with cached results
- Manual refresh for the current directory subtree
- Delete files or directories with a confirmation dialog that shows the full path
- Copy the selected path to the system clipboard when available
- Optional filesystem-boundary restriction and manual exclude filters

## Controls

- `Up` / `Down`: move selection
- `Enter`: open directory
- `Backspace`: go to parent directory
- `r`: refresh current directory and invalidate its cached subtree
- `d`: delete selected file or directory after confirmation
- `c`: copy current path
- `i`: refresh current item details
- `q`: quit

## Windows Notes

- The current clipboard helper already tries `clip.exe`, so copy-path should work on Windows terminals that expose it.
- The Linux binary under `dist/spacesniff` does not run on Windows. Build `dist\spacesniff.exe` on a Windows machine.
- `Textual` works in modern Windows terminals such as Windows Terminal and recent PowerShell sessions.

## Verification

Run the test suite:

### Linux / macOS

```bash
.venv/bin/python -m unittest discover -s tests -v
```

### Windows PowerShell

```powershell
.\.venv\Scripts\python -m unittest discover -s tests -v
```
