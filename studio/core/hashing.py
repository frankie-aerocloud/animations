"""Content fingerprints used to skip renders whose inputs have not changed."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def source_files(*directories: Path) -> list[Path]:
    files: list[Path] = []
    for directory in directories:
        files.extend(sorted(directory.rglob("*.py")))
    return files


def fingerprint(data: Any, files: Iterable[Path] = ()) -> str:
    digest = hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode("utf-8"))
    for path in sorted(files):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()
