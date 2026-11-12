"""Load and validate project YAML without coupling to Blender."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast


def load_project(path: str | Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as exc:
        raise RuntimeError(
            "PyYAML is required. Install with: python3 -m pip install -r requirements.txt"
        ) from exc
    config_path = Path(path)
    if config_path.is_dir():
        config_path = config_path / "project.yaml"
    with config_path.open("r", encoding="utf-8") as stream:
        data = cast(dict[str, Any], yaml.safe_load(stream))
    validate_project(data)
    return data


def validate_project(data: Any) -> None:
    if not isinstance(data, dict) or not isinstance(data.get("project"), dict):
        raise ValueError("Project config must contain a 'project' mapping")
    if not isinstance(data.get("render"), dict):
        raise ValueError("Project config must contain a 'render' mapping")
    fps = data["render"].get("fps")
    if not isinstance(fps, int) or fps < 1:
        raise ValueError("render.fps must be a positive integer")
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("Project must contain at least one scene")
    seen: set[str] = set()
    for scene in scenes:
        if not isinstance(scene, dict) or not scene.get("id"):
            raise ValueError("Each scene must have an id")
        if scene["id"] in seen:
            raise ValueError(f"Duplicate scene id: {scene['id']}")
        seen.add(scene["id"])
        if float(scene.get("duration", 0)) <= 0:
            raise ValueError(f"Scene {scene['id']} duration must be positive")
