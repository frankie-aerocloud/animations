#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
PYTHON_BIN="${PYTHON:-python3.14}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python 3.14 was not found. Install Python 3.14, then rerun this script." >&2
  exit 1
fi
"$PYTHON_BIN" -m venv .venv
".venv/bin/python" -m pip install -r requirements-dev.txt
for required_tool in blender ffmpeg ffprobe; do
  if ! command -v "$required_tool" >/dev/null 2>&1; then echo "Missing system tool: $required_tool"; fi
done
echo "Activate with: source .venv/bin/activate"
echo "Install missing macOS tools with Homebrew: brew install --cask blender && brew install ffmpeg"
