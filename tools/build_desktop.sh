#!/usr/bin/env sh
set -eu

PROJECT_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_ROOT"

PYTHON=${PYTHON:-python3}
"$PYTHON" -m pip install -r requirements-dev.txt
"$PYTHON" tools/build_package.py

echo "Application created under dist/OpenCANAnalyzer"
