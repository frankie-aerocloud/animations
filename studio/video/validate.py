"""Technical checks on rendered frames and the final MP4 (ffprobe and FFmpeg's blackdetect)."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path
from typing import Any

BLACK = re.compile(r"black_start:(?P<start>[\d.]+)\s+black_end:(?P<end>[\d.]+)")
PNG_END = b"IEND\xaeB`\x82"  # last 8 bytes of every complete PNG (IEND chunk type + CRC)


def frame_path(frames_dir: Path, frame: int) -> Path:
    return frames_dir / f"frame_{frame:04d}.png"


def png_complete(path: Path) -> bool:
    """True for a fully written PNG; a render killed mid-write leaves a file without the IEND trailer."""
    try:
        with path.open("rb") as handle:
            if handle.seek(0, 2) < 1000:
                return False
            handle.seek(-len(PNG_END), 2)
            return handle.read() == PNG_END
    except OSError:
        return False


def missing_frames(frames_dir: Path, count: int) -> list[int]:
    return [f for f in range(1, count + 1) if not png_complete(frame_path(frames_dir, f))]


def remove_partial_frames(frames_dir: Path) -> list[Path]:
    """Delete truncated frames so the resumed render redraws them."""
    partial = [path for path in sorted(frames_dir.glob("frame_*.png")) if not png_complete(path)]
    for path in partial:
        path.unlink()
    return partial


def frames_complete(frames_dir: Path, count: int) -> bool:
    return count > 0 and not missing_frames(frames_dir, count)


def probe(path: Path) -> dict[str, Any]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("ffprobe is required (installed with ffmpeg)")
    result = subprocess.run([ffprobe, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)], capture_output=True, text=True)
    if result.returncode != 0:
        raise ValueError(f"not a readable media file: {path}: {result.stderr.strip()}")
    data: dict[str, Any] = json.loads(result.stdout or "{}")
    return data


def validate_output(path: Path, width: int, height: int, fps: int, duration: float, tolerance: float = 0.25, require_audio: bool = True) -> list[str]:
    problems: list[str] = []
    if not path.exists() or path.stat().st_size < 1000:
        return [f"output file is missing or empty: {path}"]
    try:
        info = probe(path)
    except ValueError as exc:
        return [str(exc)]
    video = [s for s in info.get("streams", []) if s.get("codec_type") == "video"]
    audio = [s for s in info.get("streams", []) if s.get("codec_type") == "audio"]
    if not video:
        problems.append("no video stream")
    else:
        stream = video[0]
        if (stream.get("width"), stream.get("height")) != (width, height):
            problems.append(f"resolution is {stream.get('width')}x{stream.get('height')}, expected {width}x{height}")
        rate = Fraction(str(stream.get("r_frame_rate", "0/1")))
        if abs(float(rate) - fps) > 0.01:
            problems.append(f"frame rate is {float(rate):.3f}, expected {fps}")
        if stream.get("codec_name") != "h264":
            problems.append(f"video codec is {stream.get('codec_name')}, expected h264")
        if stream.get("pix_fmt") != "yuv420p":
            problems.append(f"pixel format is {stream.get('pix_fmt')}, expected yuv420p")
    if require_audio:
        if not audio:
            problems.append("no audio stream")
        elif audio[0].get("codec_name") != "aac":
            problems.append(f"audio codec is {audio[0].get('codec_name')}, expected aac")
    actual = float(info.get("format", {}).get("duration", 0.0))
    if abs(actual - duration) > tolerance:
        problems.append(f"duration is {actual:.2f}s, expected {duration:.2f}s (+/- {tolerance}s)")
    return problems


def detect_black(path: Path, min_duration: float = 0.1, picture_threshold: float = 0.98) -> list[tuple[float, float]]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required")
    result = subprocess.run([ffmpeg, "-hide_banner", "-i", str(path), "-vf", f"blackdetect=d={min_duration}:pic_th={picture_threshold}", "-an", "-f", "null", "-"], capture_output=True, text=True)
    return [(float(m.group("start")), float(m.group("end"))) for m in BLACK.finditer(result.stderr)]


def unexpected_black(path: Path, allowed: list[tuple[float, float]], min_duration: float = 0.1) -> list[tuple[float, float]]:
    """Black intervals that do not overlap an allowed window (e.g. a fade-to-black transition)."""
    found = detect_black(path, min_duration)
    return [(start, end) for start, end in found if not any(start <= b + 0.05 and end >= a - 0.05 for a, b in allowed)]
