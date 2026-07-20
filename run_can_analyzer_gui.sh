#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR"

if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON=python
else
  echo "Python 3 not found. Install Python 3 and pyserial."
  exit 1
fi

if ! "$PYTHON" -c "import serial" >/dev/null 2>&1; then
  echo "pyserial not found. Install it with:"
  echo "$PYTHON -m pip install -r requirements.txt"
  exit 1
fi

exec "$PYTHON" can_analyzer_gui.py
