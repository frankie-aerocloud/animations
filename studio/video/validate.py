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


def flashes(path: Path, fps: int, share: float = 0.25, step: int = 25, shift: float = 6.0) -> tuple[int, float]:
    """The most general flashes in any one-second window, and where that window starts. A
    transition is a jump between consecutive frames that changes at least `share` of the picture by
    `step` luma levels and moves its mean brightness by `shift`; a flash is a pair of opposing
    transitions. More than three a second risks photosensitive seizures (WCAG 2.3.1)."""

    def averages(chain: str) -> list[float]:
        result = subprocess.run([_ffmpeg(), "-hide_banner", "-i", str(path), "-map", "0:v", "-vf", f"scale=64:114,format=yuv420p,{chain}signalstats,metadata=print:key=lavfi.signalstats.YAVG", "-f", "null", "-"], capture_output=True, text=True)
        return [float(v) for v in re.findall(r"YAVG=([\d.]+)", result.stderr)]

    mean = averages("")
    changed = averages("tblend=all_mode=difference,lutyuv=y='if(gte(val,%d),255,0)'," % step)
    offset = len(mean) - len(changed)  # tblend drops the first frame
    events = []
    for k, amount in enumerate(changed):
        t = k + offset
        if t > 0 and amount / 255.0 >= share and abs(mean[t] - mean[t - 1]) >= shift:
            events.append((t, 1 if mean[t] > mean[t - 1] else -1))
    worst, when = 0, 0.0
    for i, (t0, _) in enumerate(events):
        directions = [d for t, d in events[i:] if t < t0 + fps]
        runs = sum(1 for k, d in enumerate(directions) if k == 0 or d != directions[k - 1])
        if runs // 2 > worst:
            worst, when = runs // 2, t0 / fps
    return worst, when


# ----- deep check: everything a viewer or YouTube would trip over --------------------------------
SILENCE = re.compile(r"silence_start: (?P<start>-?[\d.]+).*?silence_end: (?P<end>[\d.]+)", re.S)


def _ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required")
    return ffmpeg


def decode_errors(path: Path) -> list[str]:
    """Decode every video frame and audio sample, as a player does; returns FFmpeg's error lines."""
    result = subprocess.run([_ffmpeg(), "-v", "error", "-i", str(path), "-map", "0:v", "-map", "0:a?", "-f", "null", "-"], capture_output=True, text=True)
    errors = [line for line in result.stderr.splitlines() if line.strip()]
    if result.returncode and not errors:
        errors.append(f"ffmpeg exited with status {result.returncode}")
    return errors


def parse_loudness(stderr: str) -> dict[str, float]:
    """Integrated loudness, loudness range and true peak from the ebur128 summary."""
    stats: dict[str, float] = {}
    for key, pattern in (("integrated_lufs", r"\bI:\s+(-?[\d.]+) LUFS"), ("range_lu", r"LRA:\s+([\d.]+) LU"), ("true_peak_dbfs", r"Peak:\s+(-?[\d.]+|-inf) dBFS")):
        found = re.findall(pattern, stderr)
        if found:
            stats[key] = float(found[-1]) if found[-1] != "-inf" else float("-inf")
    return stats


def parse_intervals(stderr: str, pattern: re.Pattern[str]) -> list[tuple[float, float]]:
    return [(float(m.group("start")), float(m.group("end"))) for m in pattern.finditer(stderr)]


def audio_analysis(path: Path, silence_db: float = -45.0, silence_seconds: float = 1.5) -> tuple[dict[str, float], list[tuple[float, float]]]:
    """One pass over the audio: EBU R128 loudness plus gaps quieter than `silence_db`."""
    result = subprocess.run([_ffmpeg(), "-nostats", "-hide_banner", "-i", str(path), "-vn", "-af", f"ebur128=peak=true,silencedetect=noise={silence_db}dB:d={silence_seconds}", "-f", "null", "-"], capture_output=True, text=True)
    return parse_loudness(result.stderr), parse_intervals(result.stderr, SILENCE)


def parse_freezes(stderr: str, end_of_video: float) -> list[tuple[float, float]]:
    """freezedetect logs a freeze's end only when the picture moves again, so a frozen ending has none."""
    starts = [float(value) for value in re.findall(r"freeze_start: ([\d.]+)", stderr)]
    ends = [float(value) for value in re.findall(r"freeze_end: ([\d.]+)", stderr)]
    return [(start, ends[i] if i < len(ends) else end_of_video) for i, start in enumerate(starts)]


def frozen_frames(path: Path, end_of_video: float, min_seconds: float = 2.0) -> list[tuple[float, float]]:
    result = subprocess.run([_ffmpeg(), "-hide_banner", "-i", str(path), "-map", "0:v", "-vf", f"freezedetect=n=0.001:d={min_seconds}", "-f", "null", "-"], capture_output=True, text=True)
    return parse_freezes(result.stderr, end_of_video)


def top_level_atoms(path: Path) -> list[str]:
    """Top-level MP4 boxes in file order (e.g. ftyp, moov, mdat)."""
    atoms: list[str] = []
    total = path.stat().st_size
    offset = 0
    with path.open("rb") as handle:
        while offset + 8 <= total:
            handle.seek(offset)
            header = handle.read(16)
            size = int.from_bytes(header[:4], "big")
            if size == 1:
                size = int.from_bytes(header[8:16], "big")
            elif size == 0:
                size = total - offset
            if size < 8:
                break
            atoms.append(header[4:8].decode("latin-1"))
            offset += size
    return atoms


def deep_check(path: Path, width: int, height: int, fps: int, duration: float, allowed_black: list[tuple[float, float]], subtitle_file: Path | None = None, max_seconds: float = 180.0, target_lufs: float = -14.0) -> list[tuple[str, bool, str]]:
    """Every check as (name, passed, detail). Informational rows always pass."""
    rows: list[tuple[str, bool, str]] = []
    basics = validate_output(path, width, height, fps, duration)
    info = probe(path) if path.exists() else {}
    streams = info.get("streams", [])
    video: dict[str, Any] = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio: dict[str, Any] = next((s for s in streams if s.get("codec_type") == "audio"), {})
    actual = float(info.get("format", {}).get("duration", 0.0) or 0.0)
    rows.append(("format", not basics, "; ".join(basics) or f"{video.get('width')}x{video.get('height')} {video.get('codec_name')} {video.get('profile')} {video.get('pix_fmt')} {video.get('r_frame_rate')} fps, {audio.get('codec_name')} {audio.get('sample_rate')} Hz {audio.get('channels')} ch, {actual:.2f} s"))
    if basics and not info:
        return rows
    errors = decode_errors(path)
    rows.append(("plays end to end", not errors, f"{len(errors)} decode errors, first: {errors[0]}" if errors else "every video frame and audio sample decodes"))
    v_len, a_len = float(video.get("duration", 0) or 0), float(audio.get("duration", 0) or 0)
    rows.append(("audio/video length", abs(v_len - a_len) <= 0.1, f"video {v_len:.2f} s, audio {a_len:.2f} s"))
    black = unexpected_black(path, allowed_black)
    rows.append(("black frames", not black, ", ".join(f"{s:.2f}-{e:.2f} s" for s, e in black) or "none outside fade-to-black transitions"))
    frozen = frozen_frames(path, actual)
    long_freezes = [(s, e) for s, e in frozen if e - s >= 4.0]
    rows.append(("frozen picture", not long_freezes, ", ".join(f"{s:.1f}-{e:.1f} s" for s, e in frozen) or "no still stretch of 2 s or more"))
    strobe, at = flashes(path, fps)
    rows.append(("flashing", strobe <= 3, f"{strobe} general flashes within one second at {at:.1f} s (limit 3)" if strobe > 3 else f"at most {strobe} general flash(es) in any second (limit 3)"))
    loudness, silences = audio_analysis(path)
    lufs, peak = loudness.get("integrated_lufs"), loudness.get("true_peak_dbfs")
    rows.append(("loudness", lufs is not None and abs(lufs - target_lufs) <= 2.0, f"{lufs} LUFS integrated (target {target_lufs}), range {loudness.get('range_lu')} LU"))
    rows.append(("true peak", peak is not None and peak <= -0.5, f"{peak} dBFS"))
    gaps = [(s, e) for s, e in silences if s > 1.6 and e < actual - 3.1]
    rows.append(("audio dropouts", not gaps, ", ".join(f"{s:.1f}-{e:.1f} s" for s, e in gaps) or "no silence over 1.5 s except the fade in and out"))
    subtitle_streams = [s for s in streams if s.get("codec_type") == "subtitle"]
    cues = subtitle_file.read_text(encoding="utf-8").count(" --> ") if subtitle_file and subtitle_file.exists() else 0
    rows.append(("subtitles", bool(subtitle_streams) and cues > 0, f"{len(subtitle_streams)} embedded track(s) ({', '.join(str(s.get('codec_name')) for s in subtitle_streams)}), {cues} cues in {subtitle_file.name if subtitle_file else 'no sidecar'}"))
    atoms = top_level_atoms(path)
    fast = "moov" in atoms and "mdat" in atoms and atoms.index("moov") < atoms.index("mdat")
    rows.append(("streams before download ends", fast, " > ".join(atoms)))
    portrait = bool(video) and int(video.get("height", 0)) * 9 == int(video.get("width", 0)) * 16
    rows.append(("Shorts limits", portrait and actual <= max_seconds, f"9:16 {'yes' if portrait else 'no'}, {actual:.1f} s of {max_seconds:.0f} s maximum"))
    return rows
