#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -x .venv/bin/python ]]; then
  echo "error: missing virtual environment at .venv" >&2
  echo "run: python3 -m venv .venv && .venv/bin/pip install -e . pyinstaller" >&2
  exit 1
fi

if ! .venv/bin/python -m pip show pyinstaller >/dev/null 2>&1; then
  echo "error: pyinstaller is not installed in .venv" >&2
  echo "run: .venv/bin/pip install pyinstaller" >&2
  exit 1
fi

rm -rf build dist

.venv/bin/pyinstaller \
  --noconfirm \
  --clean \
  --onefile \
  --name spacesniff \
  --collect-all textual \
  --collect-all rich \
  spacesniff/__main__.py

echo
echo "Standalone binary created at: $ROOT_DIR/dist/spacesniff"
