"""Deterministic frame-based timeline helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Even a hard cut gets a two-frame crossfade so every xfade has handle material to blend.
MIN_HANDLE_FRAMES = 2


@dataclass(frozen=True)
class SceneSpan:
    id: str
    start: int
    end: int

    @property
    def duration(self) -> int:
        return self.end - self.start + 1


def make_timeline(scenes: list[dict[str, Any]], fps: int) -> list[SceneSpan]:
    cursor = 1
    spans: list[SceneSpan] = []
    for scene in scenes:
        frames = round(float(scene["duration"]) * fps)
        if frames <= 0:
            raise ValueError(f"Scene {scene.get('id', '<unknown>')} has no frames")
        spans.append(SceneSpan(str(scene["id"]), cursor, cursor + frames - 1))
        cursor += frames
    return spans


def handle_frames(scene: dict[str, Any], fps: int, is_last: bool) -> int:
    """Extra frames rendered after a scene's nominal end so the outgoing transition has material."""
    if is_last:
        return 0
    transition = scene.get("transition") or {}
    seconds = float(transition.get("duration", 0.0) or 0.0)
    return max(MIN_HANDLE_FRAMES, round(seconds * fps))


def annotate(scenes: list[dict[str, Any]], fps: int) -> None:
    """Add index, start (seconds), frames and handle_frames to each scene in place."""
    cursor = 0.0
    for index, scene in enumerate(scenes):
        duration = float(scene.get("duration") or 0.0)
        scene["index"] = index
        scene["start"] = round(cursor, 6)
        scene["frames"] = max(0, round(duration * fps))
        scene["handle_frames"] = handle_frames(scene, fps, index == len(scenes) - 1)
        cursor += duration
