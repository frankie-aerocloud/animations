"""Asset manifest checks: every third-party asset needs a source, a licence and a present file."""

from __future__ import annotations

from pathlib import Path
from typing import Any

REQUIRED = ("id", "path", "source", "type")


def validate_manifest(entries: list[dict[str, Any]], root: Path) -> list[str]:
    errors: list[str] = []
    for item in entries:
        ident = item.get("id", "<unknown>")
        for key in REQUIRED:
            if not item.get(key):
                errors.append(f"asset {ident}: missing {key}")
        if not (item.get("licence") or item.get("license")):
            errors.append(f"asset {ident}: missing licence")
        path = item.get("path")
        if path and not (root / str(path)).exists():
            errors.append(f"asset {ident}: file is missing: {path}")
    return errors
