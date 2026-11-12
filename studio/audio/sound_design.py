"""Deterministic, locally synthesized atmospheric bed for the short."""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path


def render_ambient_bed(durations: list[float], path: Path, sample_rate: int = 24000) -> Path:
    """Render a quiet evolving drone and transition chimes with the Python standard library."""
    total = sum(durations)
    notes = (55.0, 49.0, 58.27, 65.41, 58.27, 49.0, 43.65)
    starts = []
    cursor = 0.0
    for duration in durations:
        starts.append(cursor)
        cursor += duration
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        chunk = bytearray()
        boundaries = [round(start * sample_rate) for start in starts]
        scene_index = 0
        for frame in range(round(total * sample_rate)):
            while scene_index + 1 < len(boundaries) and frame >= boundaries[scene_index + 1]:
                scene_index += 1
            time = frame / sample_rate
            root = notes[scene_index % len(notes)]
            phase = 0.18 * math.sin(math.tau * time / 13.0)
            tone = 0.021 * math.sin(math.tau * root * time + phase)
            tone += 0.010 * math.sin(math.tau * root * 1.5 * time + phase * 0.7)
            tone += 0.004 * math.sin(math.tau * root * 2.0 * time)
            # A single soft bell marks each cut; the exponential tail stays behind narration.
            if scene_index > 0:
                delta = time - starts[scene_index]
                if 0 <= delta < 0.8:
                    tone += (
                        0.022
                        * math.exp(-5.0 * delta)
                        * math.sin(math.tau * (392 + scene_index * 31) * delta)
                    )
            fade = min(1.0, time / 2.0, (total - time) / 3.0)
            sample = max(-1.0, min(1.0, tone * max(0.0, fade)))
            chunk.extend(struct.pack("<h", round(sample * 32767)))
            if len(chunk) >= 65536:
                audio.writeframesraw(chunk)
                chunk.clear()
        if chunk:
            audio.writeframesraw(chunk)
    return path
