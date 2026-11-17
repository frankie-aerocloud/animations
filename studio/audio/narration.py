"""Narration: recorded WAVs per line take priority, otherwise Piper TTS renders them offline."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import wave
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from studio.core.configuration import REPO_ROOT
from studio.core.project import Project


@dataclass(frozen=True)
class LineAudio:
    id: str
    scene: str
    start: float
    duration: float
    path: Path
    text: str

    @property
    def end(self) -> float:
        return self.start + self.duration


def audio_duration(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as handle:
            return handle.getnframes() / float(handle.getframerate())
    except (wave.Error, EOFError):
        ffprobe = shutil.which("ffprobe")
        if not ffprobe:
            raise RuntimeError(f"cannot read duration of {path}: ffprobe is not installed") from None
        result = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)], check=True, capture_output=True, text=True)
        return float(result.stdout.strip())


def piper_available(voice_path: Path) -> bool:
    try:
        import piper  # noqa: F401
    except ImportError:
        return False
    return voice_path.exists()


def _voice_path(settings: dict[str, Any]) -> Path:
    voices_dir = Path(str(settings.get("voices_dir", "assets/voices")))
    if not voices_dir.is_absolute():
        voices_dir = REPO_ROOT / voices_dir
    return voices_dir / f"{settings.get('voice', 'en_GB-cori-high')}.onnx"


def _synthesise_piper(text: str, voice_path: Path, settings: dict[str, Any], out: Path) -> None:
    from piper import PiperVoice
    from piper.config import SynthesisConfig

    voice = _PIPER_CACHE.get(voice_path)
    if voice is None:
        voice = PiperVoice.load(str(voice_path))
        _PIPER_CACHE[voice_path] = voice
    # noise_w 0 makes Piper's stochastic duration predictor deterministic, so a line's length never
    # changes between runs and a storyboard timed against it always fits
    noise_w = settings.get("noise_w")
    config = SynthesisConfig(length_scale=float(settings.get("length_scale", 1.0)), noise_w_scale=None if noise_w is None else float(noise_w), normalize_audio=True)
    with wave.open(str(out), "wb") as handle:
        voice.synthesize_wav(text, handle, syn_config=config)


_PIPER_CACHE: dict[Path, Any] = {}


def synthesise(project: Project, out_dir: Path, log: Callable[[str], None] = print) -> list[LineAudio]:
    """Return narration audio for every script line, rendering with Piper when no recording exists."""
    out_dir.mkdir(parents=True, exist_ok=True)
    settings = dict(project.audio.get("narration") or {})
    engine = str(settings.get("engine", "piper"))
    recorded_dir = project.root / str(project.audio.get("narration_dir", "audio/narration"))
    voice_path = _voice_path(settings)
    lines: list[LineAudio] = []
    for line in project.lines:
        lid = str(line["id"])
        text = " ".join(str(line["text"]).split())
        start = project.line_start(line)
        recorded = project.resolve_path(str(line["audio"])) if line.get("audio") else recorded_dir / f"{lid}.wav"
        if recorded.exists():
            path = recorded
        elif engine == "piper" and piper_available(voice_path):
            path = out_dir / f"{lid}.wav"
            noise_w = settings.get("noise_w")
            digest = hashlib.sha256(f"{voice_path.name}|{settings.get('length_scale', 1.0)}|{text}{'' if noise_w is None else f'|noise_w={noise_w}'}".encode()).hexdigest()
            stamp = out_dir / f"{lid}.json"
            if not (path.exists() and stamp.exists() and json.loads(stamp.read_text()).get("sha256") == digest):
                log(f"[narration] piper: {lid}")
                _synthesise_piper(text, voice_path, settings, path)
                stamp.write_text(json.dumps({"sha256": digest, "text": text}), encoding="utf-8")
        else:
            raise RuntimeError(
                f"no narration for line {lid}: record it as {recorded} or install Piper and download the "
                f"voice ({voice_path.name}); see assets/voices/README.md"
            )
        lines.append(LineAudio(lid, str(line["scene"]), start, audio_duration(path), path, text))
    lines.sort(key=lambda item: item.start)
    return lines


def check_fit(lines: list[LineAudio], total: float) -> list[str]:
    """Problems when narration lines overlap each other or run past the end of the film."""
    problems: list[str] = []
    for current, following in zip(lines, lines[1:], strict=False):
        if current.end > following.start + 0.05:
            problems.append(f"narration {current.id} ({current.end:.2f}s) runs into {following.id} ({following.start:.2f}s)")
    if lines and lines[-1].end > total + 0.05:
        problems.append(f"narration {lines[-1].id} ends at {lines[-1].end:.2f}s after the film ends at {total:.2f}s")
    return problems
