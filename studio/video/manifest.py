"""Production manifest written next to every completed video."""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def tool_version(name: str, flag: str = "-version") -> str:
    path = shutil.which(name)
    if not path:
        return "not installed"
    try:
        result = subprocess.run([path, flag], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"
    first = (result.stdout or result.stderr).strip().splitlines()
    return first[0] if first else "unknown"


def package_version(name: str) -> str:
    from importlib import metadata

    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "not installed"


def write_manifest(path: Path, data: dict[str, Any]) -> Path:
    payload = {"generated_at": datetime.now(UTC).isoformat(timespec="seconds"), **data}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return path
