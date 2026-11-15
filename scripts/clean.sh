#!/bin/sh
# Remove generated output for one project (default: water-crisis).
set -eu
cd "$(dirname "$0")/.."
.venv/bin/python -m studio.cli clean "${1:-projects/water-crisis}"
