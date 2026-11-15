"""Encode scene clips and assemble the film: xfade transitions, overlay composite, audio and subtitles."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from studio.core import catalogue


def _ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise RuntimeError("ffmpeg is required (macOS: brew install ffmpeg)")
    return path


def encode_clip(frames_dir: Path, fps: int, frames: int, out: Path, crf: int = 14) -> Path:
    """Lossless-ish intermediate clip from a PNG sequence (frame_0001.png ...)."""
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        _ffmpeg(), "-y", "-v", "error", "-framerate", str(fps), "-start_number", "1", "-i", str(frames_dir / "frame_%04d.png"),
        "-frames:v", str(frames), "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf), "-pix_fmt", "yuv420p", "-r", str(fps), "-an", str(out),
    ]
    subprocess.run(cmd, check=True)
    return out


def assemble(clips: list[Path], scenes: list[dict[str, Any]], overlay_dir: Path | None, audio: Path | None, srt: Path | None, out: Path, fps: int, total: float, encode: dict[str, Any]) -> Path:
    """Stitch clips with per-scene transitions, composite the overlay, mux audio and a soft subtitle track."""
    if len(clips) != len(scenes) or not clips:
        raise ValueError("one clip per scene is required")
    cmd = [_ffmpeg(), "-y", "-v", "error"]
    for clip in clips:
        cmd += ["-i", str(clip)]
    filters = [f"[{i}:v]fps={fps},format=yuv420p,setpts=PTS-STARTPTS[v{i}]" for i in range(len(clips))]
    previous = "v0"
    offset = 0.0
    for i in range(1, len(clips)):
        scene = scenes[i - 1]
        transition = scene.get("transition") or {}
        kind = catalogue.TRANSITIONS[str(transition.get("type", "cut"))]
        duration = int(scene["handle_frames"]) / fps
        offset += float(scene["duration"])
        filters.append(f"[{previous}][v{i}]xfade=transition={kind}:duration={duration:.4f}:offset={offset:.4f}[x{i}]")
        previous = f"x{i}"
    index = len(clips)
    if overlay_dir is not None:
        cmd += ["-framerate", str(fps), "-start_number", "1", "-i", str(overlay_dir / "frame_%04d.png")]
        filters.append(f"[{index}:v]format=rgba[ovl]")
        filters.append(f"[{previous}][ovl]overlay=eof_action=pass:format=auto[pic]")
        previous = "pic"
        index += 1
    filters.append(f"[{previous}]format=yuv420p[vout]")
    maps = ["-map", "[vout]"]
    if audio is not None:
        cmd += ["-i", str(audio)]
        maps += ["-map", f"{index}:a:0"]
        index += 1
    if srt is not None:
        cmd += ["-i", str(srt)]
        maps += ["-map", f"{index}:s:0"]
        index += 1
    cmd += ["-filter_complex", ";".join(filters), *maps]
    cmd += ["-c:v", "libx264", "-preset", str(encode.get("preset", "medium")), "-crf", str(encode.get("crf", 18)), "-profile:v", "high", "-level", "4.2", "-pix_fmt", "yuv420p", "-r", str(fps)]
    cmd += ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-movflags", "+faststart", "-t", f"{total:.4f}"]
    if audio is not None:
        cmd += ["-c:a", "aac", "-b:a", str(encode.get("audio_bitrate", "192k")), "-ar", "48000"]
    if srt is not None:
        cmd += ["-c:s", "mov_text", "-metadata:s:s:0", "language=eng"]
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd.append(str(out))
    subprocess.run(cmd, check=True)
    return out
