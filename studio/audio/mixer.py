"""FFmpeg mix: placed narration, ducked music, sound-effect cues, fades, limiter and loudness."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from studio.audio.narration import LineAudio


@dataclass(frozen=True)
class SfxCue:
    path: Path
    start: float
    gain_db: float = 0.0


def _db(value: Any) -> str:
    return f"{float(value):.2f}dB"


def mix(lines: list[LineAudio], music: Path | None, cues: list[SfxCue], settings: dict[str, Any], total: float, out: Path) -> Path:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to mix audio")
    narration_cfg = settings.get("narration") or {}
    music_cfg = settings.get("music") or {}
    sfx_cfg = settings.get("sfx") or {}
    master = settings.get("master") or {}
    cmd = [ffmpeg, "-y", "-v", "error"]
    filters: list[str] = []
    index = 0
    labels: list[str] = []
    for line in lines:
        cmd += ["-i", str(line.path)]
        delay = int(round(line.start * 1000))
        filters.append(f"[{index}:a]aresample=48000,aformat=channel_layouts=stereo,volume={_db(narration_cfg.get('gain_db', 0))},adelay={delay}|{delay}[n{index}]")
        labels.append(f"[n{index}]")
        index += 1
    if labels:
        filters.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:dropout_transition=0,apad=whole_dur={total:.3f}[nar]")
        filters.append("[nar]asplit=2[nar_mix][nar_key]")
    mix_inputs: list[str] = ["[nar_mix]"] if labels else []
    if music is not None:
        cmd += ["-i", str(music)]
        fade_in = float(music_cfg.get("fade_in", 1.5))
        fade_out = float(music_cfg.get("fade_out", 3.0))
        chain = f"[{index}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{total:.3f},apad=whole_dur={total:.3f},volume={_db(music_cfg.get('gain_db', -16))},afade=t=in:d={fade_in:.2f},afade=t=out:st={max(0.0, total - fade_out):.2f}:d={fade_out:.2f}[mus]"
        filters.append(chain)
        index += 1
        if labels:
            duck = music_cfg.get("duck") or {}
            filters.append(
                f"[mus][nar_key]sidechaincompress=threshold={float(duck.get('threshold', 0.03))}:ratio={float(duck.get('ratio', 8))}"
                f":attack={float(duck.get('attack_ms', 40))}:release={float(duck.get('release_ms', 650))}:makeup=1[mus_d]"
            )
            mix_inputs.append("[mus_d]")
        else:
            mix_inputs.append("[mus]")
    for cue in cues:
        cmd += ["-i", str(cue.path)]
        delay = int(round(cue.start * 1000))
        filters.append(f"[{index}:a]aresample=48000,aformat=channel_layouts=stereo,volume={_db(float(sfx_cfg.get('gain_db', -10)) + cue.gain_db)},adelay={delay}|{delay}[s{index}]")
        mix_inputs.append(f"[s{index}]")
        index += 1
    if not mix_inputs:
        raise RuntimeError("nothing to mix: no narration, music or sound effects")
    final = f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:normalize=0:dropout_transition=0,atrim=0:{total:.3f},apad=whole_dur={total:.3f}"
    if master.get("loudnorm", True):
        final += f",loudnorm=I={float(master.get('target_lufs', -14))}:TP={float(master.get('true_peak', -1.5))}:LRA=11"
    final += ",alimiter=limit=0.95[out]"
    filters.append(final)
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd += ["-filter_complex", ";".join(filters), "-map", "[out]", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", "-t", f"{total:.3f}", str(out)]
    subprocess.run(cmd, check=True)
    return out
