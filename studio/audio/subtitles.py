"""SRT subtitle generation from scene-boundary narration cues."""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any


def _timecode(seconds: float) -> str:
    millis = round(seconds * 1000)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1_000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_srt(scenes: list[dict[str, Any]], path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    cursor = 0.0
    cues: list[str] = []
    for index, scene in enumerate(scenes, start=1):
        narration = str(scene.get("narration", "")).strip()
        if narration:
            duration = float(scene["duration"])
            words = narration.split()
            # Keep each cue short enough to read on a phone. Roughly 7 words
            # per card gives portrait subtitles two compact lines at most.
            groups = [words[start : start + 7] for start in range(0, len(words), 7)]
            visible_duration = max(0.5, duration - 0.4 - 0.08 * (len(groups) - 1))
            cue_start = cursor + 0.2
            for cue_index, group in enumerate(groups):
                cue_duration = visible_duration * len(group) / len(words)
                cue_end = cue_start + cue_duration
                body = textwrap.fill(" ".join(group), width=42)
                cue_number = len(cues) + 1
                cues.append(
                    f"{cue_number}\n{_timecode(cue_start)} --> {_timecode(cue_end)}\n{body}\n"
                )
                cue_start = cue_end + (0.08 if cue_index < len(groups) - 1 else 0.0)
        cursor += float(scene["duration"])
    output.write_text("\n".join(cues), encoding="utf-8")
    return output
