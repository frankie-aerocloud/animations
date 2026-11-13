"""Repository paths, YAML loading, config merging and render profiles."""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "config"
PROJECTS_DIR = REPO_ROOT / "projects"
OUTPUT_DIR = REPO_ROOT / "output"


def load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover - environment problem, not logic
        raise RuntimeError(
            "PyYAML is required: .venv/bin/python -m pip install -r requirements.txt"
        ) from exc
    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a mapping at the top level")
    return data


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


@dataclass(frozen=True)
class RenderProfile:
    name: str
    scale: float
    samples: int
    motion_blur: bool
    volumetrics: bool
    raytracing: bool
    denoise: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_profiles(render: dict[str, Any]) -> dict[str, RenderProfile]:
    raw = render.get("profiles") or {}
    if not isinstance(raw, dict) or not raw:
        raise ValueError("render.profiles must define at least one profile")
    profiles: dict[str, RenderProfile] = {}
    for name, item in raw.items():
        if not isinstance(item, dict):
            raise ValueError(f"render.profiles.{name} must be a mapping")
        profiles[str(name)] = RenderProfile(
            name=str(name),
            scale=float(item.get("scale", 1.0)),
            samples=int(item.get("samples", 16)),
            motion_blur=bool(item.get("motion_blur", False)),
            volumetrics=bool(item.get("volumetrics", False)),
            raytracing=bool(item.get("raytracing", False)),
            denoise=bool(item.get("denoise", False)),
        )
    return profiles
