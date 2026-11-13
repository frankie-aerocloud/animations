#!/bin/sh
# Local setup: Python venv, Piper voice and a check for the system tools.
set -eu
cd "$(dirname "$0")/.."
PYTHON_BIN="${PYTHON:-python3}"
"$PYTHON_BIN" -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m piper.download_voices en_GB-cori-high --download-dir assets/voices
for required_tool in blender ffmpeg ffprobe; do
  command -v "$required_tool" >/dev/null 2>&1 || echo "Missing system tool: $required_tool (macOS: brew install --cask blender; brew install ffmpeg)"
done
.venv/bin/python -m studio.cli doctor
