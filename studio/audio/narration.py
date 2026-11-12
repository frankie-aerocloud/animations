"""Offline narration rendering adapters; macOS `say` and supplied WAV files."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any


def render_scene_narration(
    scenes: list[dict[str, Any]], output_dir: Path, ffmpeg: str, voice: str = "Daniel"
) -> list[Path]:
    say = shutil.which("say")
    afinfo = shutil.which("afinfo")
    if not say:
        return []
    rendered: list[Path] = []
    for scene in scenes:
        text = str(scene.get("narration", "")).strip()
        if not text:
            return []
        stem = output_dir / f"voice-{scene['id']}"
        aiff = stem.with_suffix(".aiff")
        wav = stem.with_suffix(".wav")
        subprocess.run([say, "-v", voice, "-r", "168", "-o", str(aiff), text], check=True)
        if not aiff.exists() or aiff.stat().st_size < 5000:
            return []
        if afinfo:
            info = subprocess.run(
                [afinfo, str(aiff)], check=True, text=True, capture_output=True
            ).stdout
            if "audio bytes: 0" in info:
                return []
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-v",
                "error",
                "-i",
                str(aiff),
                "-ar",
                "48000",
                "-ac",
                "1",
                "-c:a",
                "pcm_s16le",
                str(wav),
            ],
            check=True,
        )
        rendered.append(wav)
    return rendered


def assemble_narration(
    clips: list[Path], durations: list[float], output: Path, ffmpeg: str
) -> Path:
    args = [ffmpeg, "-y"]
    for clip in clips:
        args.extend(["-i", str(clip)])
    chains = []
    labels = []
    for index, duration in enumerate(durations):
        label = f"n{index}"
        chains.append(
            f"[{index}:a]aresample=48000,apad,atrim=duration={duration:.6f},asetpts=PTS-STARTPTS[{label}]"
        )
        labels.append(f"[{label}]")
    chains.append(f"{''.join(labels)}concat=n={len(labels)}:v=0:a=1[narration]")
    args.extend(
        [
            "-filter_complex",
            ";".join(chains),
            "-map",
            "[narration]",
            "-c:a",
            "pcm_s16le",
            str(output),
        ]
    )
    subprocess.run(args, check=True)
    return output
