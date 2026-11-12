"""Deterministic frame-based timeline helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
