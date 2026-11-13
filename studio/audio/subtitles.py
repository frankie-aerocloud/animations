"""Subtitle cues from narration lines: short phrases, timed proportionally within each line."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from studio.audio.narration import LineAudio

SPLIT = re.compile(r"(?<=[,;:.!?…])\s+|\s+(?=[—–-]\s)")


@dataclass(frozen=True)
class Cue:
    start: float
    end: float
    text: str


def phrases(text: str, max_chars: int) -> list[str]:
    """Split text at punctuation, then pack/split so every phrase fits max_chars."""
    pieces = [piece.strip() for piece in SPLIT.split(text) if piece.strip()]
    packed: list[str] = []
    for piece in pieces:
        if packed and len(packed[-1]) + 1 + len(piece) <= max_chars and not packed[-1].endswith((".", "!", "?")):
            packed[-1] = f"{packed[-1]} {piece}"
        else:
            packed.append(piece)
    result: list[str] = []
    for phrase in packed:
        words = phrase.split()
        current = ""
        for word in words:
            if current and len(current) + 1 + len(word) > max_chars:
                result.append(current)
                current = word
            else:
                current = f"{current} {word}".strip()
        if current:
            result.append(current)
    return result


def make_cues(lines: list[LineAudio], max_chars: int = 44, gap: float = 0.06, min_duration: float = 0.7) -> list[Cue]:
    cues: list[Cue] = []
    for line in lines:
        parts = phrases(line.text, max_chars)
        if not parts:
            continue
        usable = max(min_duration, line.duration - 0.15)
        weights = [len(part) + 6 for part in parts]
        total = float(sum(weights))
        cursor = line.start
        for i, (part, weight) in enumerate(zip(parts, weights, strict=False)):
            length = usable * weight / total
            end = cursor + length - (gap if i < len(parts) - 1 else 0.0)
            cues.append(Cue(round(cursor, 3), round(max(cursor + 0.3, end), 3), part))
            cursor += length
    return cues


def validate_cues(cues: list[Cue], total: float) -> list[str]:
    problems: list[str] = []
    for i, cue in enumerate(cues):
        if cue.end <= cue.start:
            problems.append(f"cue {i + 1} ends before it starts ({cue.start:.2f} -> {cue.end:.2f})")
        if cue.start < 0 or cue.end > total + 0.01:
            problems.append(f"cue {i + 1} lies outside the film (0 .. {total:.2f}s)")
        if i and cue.start < cues[i - 1].end - 0.001:
            problems.append(f"cue {i + 1} overlaps cue {i}")
        if not cue.text.strip():
            problems.append(f"cue {i + 1} is empty")
    return problems


def timecode(seconds: float) -> str:
    millis = round(seconds * 1000)
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1_000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_srt(cues: list[Cue], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    blocks = [f"{i}\n{timecode(cue.start)} --> {timecode(cue.end)}\n{cue.text}\n" for i, cue in enumerate(cues, start=1)]
    path.write_text("\n".join(blocks), encoding="utf-8")
    return path
