#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
".venv/bin/python" studio.py clean "${1:-world-runs-out-of-water}"
