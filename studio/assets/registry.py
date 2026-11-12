"""Small manifest reader; imported assets must include provenance and licence."""

from pathlib import Path


def validate_manifest(entries: list[dict[str, str]], root: Path) -> list[str]:
    errors: list[str] = []
    for item in entries:
        for key in ("id", "path", "source", "license", "type"):
            if not item.get(key):
                errors.append(f"Asset entry missing {key}: {item.get('id', '<unknown>')}")
        if item.get("path") and not (root / item["path"]).exists():
            errors.append(f"Asset file missing: {item['path']}")
    return errors
