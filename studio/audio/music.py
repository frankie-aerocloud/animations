"""Procedural underscore: a dark pad that follows each scene's `music.intensity`, with a pulse
that quickens as the story escalates and a riser into every scene whose intensity rises."""

from __future__ import annotations

import math
import random
import wave
from array import array
from pathlib import Path
from typing import Any

RATE = 24000
ROOTS = (55.0, 87.31, 98.0, 82.41, 73.42, 87.31, 82.41, 65.41, 55.0, 98.0, 82.41, 55.0)


def render_score(scenes: list[dict[str, Any]], path: Path, sample_rate: int = RATE, seed: int = 1, style: str = "tense") -> Path:
    """Write a mono WAV covering the whole timeline. style 'quirky' adds a staccato plucked arpeggio."""
    plan = []
    cursor = 0.0
    for index, scene in enumerate(scenes):
        duration = float(scene.get("duration") or 0.0)
        intensity = float((scene.get("music") or {}).get("intensity", 0.4))
        plan.append((cursor, cursor + duration, intensity, ROOTS[index % len(ROOTS)]))
        cursor += duration
    total = cursor
    n = int(total * sample_rate)
    rng = random.Random(seed)
    samples = array("h")
    pad_phase = [0.0, 0.0, 0.0]
    detune = (1.0, 1.004, 0.5015)
    pulse_phase = 0.0
    last_beat = -10.0
    noise_state = 0.0
    scene_index = 0
    for i in range(n):
        t = i / sample_rate
        while scene_index + 1 < len(plan) and t >= plan[scene_index][1]:
            scene_index += 1
        start, end, intensity, root = plan[scene_index]
        next_intensity = plan[scene_index + 1][2] if scene_index + 1 < len(plan) else 0.0
        # pad: three detuned partials, slow tremolo, scene crossfade over 0.8 s
        blend = min(1.0, (t - start) / 0.8) if scene_index else 1.0
        previous_root = plan[scene_index - 1][3] if scene_index else root
        pad = 0.0
        for k in range(3):
            freq = root * detune[k] * blend + previous_root * detune[k] * (1.0 - blend)
            pad_phase[k] += math.tau * freq / sample_rate
            pad += math.sin(pad_phase[k]) * (0.6 if k == 2 else 1.0)
        pad *= 0.12 * (0.45 + 0.55 * intensity) * (0.85 + 0.15 * math.sin(math.tau * 0.23 * t))
        # pulse
        pulse = 0.0
        if intensity >= 0.35:
            bpm = 68.0 + 58.0 * intensity
            beat = 60.0 / bpm
            since = (t - start) % beat
            if since < 0.005 and t - last_beat > beat * 0.5:
                last_beat = t - since
                pulse_phase = 0.0
            tk = t - last_beat
            if 0.0 <= tk < 0.3:
                pulse_phase += math.tau * (52.0 + 40.0 * math.exp(-tk * 30.0)) / sample_rate
                pulse = math.sin(pulse_phase) * math.exp(-tk * 16.0) * 0.5 * intensity
        # quirky: plucked minor arpeggio on every half beat
        pluck = 0.0
        if style == "quirky" and intensity >= 0.2:
            bpm = 96.0 + 50.0 * intensity
            half = 30.0 / bpm
            since_pluck = (t - start) % half
            step_index = int((t - start) / half)
            if since_pluck < 0.16:
                ratio = (2.0, 2.4, 3.0, 4.0, 3.0, 2.4)[step_index % 6]
                pluck = math.sin(math.tau * root * ratio * since_pluck) * math.exp(-since_pluck * 26.0) * 0.16 * (0.5 + 0.5 * intensity)
        # tension shimmer
        shimmer = math.sin(math.tau * 440.0 * t) * (0.5 + 0.5 * math.sin(math.tau * 6.5 * t)) * max(0.0, intensity - 0.55) * 0.07
        # riser into the next scene when the intensity rises
        riser = 0.0
        remaining = end - t
        if next_intensity > intensity and remaining < 1.8:
            ramp = 1.0 - remaining / 1.8
            noise_state += (rng.uniform(-1.0, 1.0) - noise_state) * (0.02 + 0.3 * ramp)
            riser = noise_state * ramp * ramp * 0.5 * next_intensity
        value = pad + pulse + shimmer + riser + pluck
        fade = min(1.0, t / 1.5, max(0.0, (total - t) / 3.0))
        samples.append(int(max(-1.0, min(1.0, value * fade)) * 32767))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(samples.tobytes())
    return path
