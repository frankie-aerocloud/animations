"""Procedurally synthesised sound effects (standard library only), cached as WAV files."""

from __future__ import annotations

import math
import random
import struct
import wave
from array import array
from collections.abc import Callable
from pathlib import Path

RATE = 48000


def _write(path: Path, samples: list[float], rate: int = RATE) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    peak = max(1e-6, max(abs(s) for s in samples))
    gain = min(1.0, 0.95 / peak)
    data = array("h", (int(max(-1.0, min(1.0, s * gain)) * 32767) for s in samples))
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(data.tobytes())
    return path


def _noise(n: int, seed: int = 1) -> list[float]:
    rng = random.Random(seed)
    return [rng.uniform(-1.0, 1.0) for _ in range(n)]


def _lowpass(samples: list[float], coefficient: Callable[[float], float]) -> list[float]:
    out = []
    y = 0.0
    n = len(samples)
    for i, x in enumerate(samples):
        a = coefficient(i / n)
        y += a * (x - y)
        out.append(y)
    return out


def whoosh(duration: float = 1.1) -> list[float]:
    n = int(duration * RATE)
    noise = _lowpass(_noise(n, 2), lambda t: 0.02 + 0.5 * math.sin(math.pi * t) ** 2)
    return [s * math.sin(math.pi * i / n) ** 1.5 for i, s in enumerate(noise)]


def impact(duration: float = 1.6) -> list[float]:
    n = int(duration * RATE)
    noise = _lowpass(_noise(n, 3), lambda t: 0.3)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / RATE
        freq = 30.0 + 50.0 * math.exp(-t * 9.0)
        phase += math.tau * freq / RATE
        body = math.sin(phase) * math.exp(-t * 2.4)
        crack = noise[i] * math.exp(-t * 28.0) * 0.8
        out.append(body + crack)
    return out


def riser(duration: float = 3.0) -> list[float]:
    n = int(duration * RATE)
    noise = _lowpass(_noise(n, 4), lambda t: 0.01 + 0.45 * t * t)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / n
        phase += math.tau * (90.0 + 420.0 * t * t) / RATE
        out.append((noise[i] * 0.9 + math.sin(phase) * 0.25) * t ** 1.6)
    return out


def swell(duration: float = 2.2) -> list[float]:
    n = int(duration * RATE)
    noise = _lowpass(_noise(n, 5), lambda t: 0.05 + 0.35 * t)
    return [s * (i / n) ** 2.2 for i, s in enumerate(noise)]


def drip(duration: float = 0.45) -> list[float]:
    n = int(duration * RATE)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / RATE
        phase += math.tau * (1500.0 - 900.0 * min(1.0, t * 12.0)) / RATE
        out.append(math.sin(phase) * math.exp(-t * 22.0))
    echo = int(0.11 * RATE)
    return [s + (out[i - echo] * 0.35 if i >= echo else 0.0) for i, s in enumerate(out)]


def alarm(duration: float = 2.0) -> list[float]:
    n = int(duration * RATE)
    out = []
    for i in range(n):
        t = i / RATE
        freq = 880.0 if int(t * 4) % 2 == 0 else 660.0
        gate = 1.0 if (t * 4) % 1.0 < 0.8 else 0.0
        out.append((math.sin(math.tau * freq * t) + 0.3 * math.sin(math.tau * freq * 3 * t)) * gate * 0.6)
    return out


def siren(duration: float = 3.0) -> list[float]:
    n = int(duration * RATE)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / RATE
        phase += math.tau * (700.0 + 250.0 * math.sin(math.tau * 0.9 * t)) / RATE
        env = min(1.0, t * 4.0) * min(1.0, (duration - t) * 2.0)
        out.append((math.sin(phase) + 0.2 * math.sin(2 * phase)) * env * 0.5)
    return out


def rumble(duration: float = 3.5) -> list[float]:
    n = int(duration * RATE)
    noise = _lowpass(_lowpass(_noise(n, 6), lambda t: 0.02), lambda t: 0.05)
    return [s * 8.0 * math.sin(math.pi * i / n) ** 0.7 for i, s in enumerate(noise)]


def tick(duration: float = 0.07) -> list[float]:
    n = int(duration * RATE)
    noise = _lowpass(_noise(n, 7), lambda t: 0.6)
    return [s * math.exp(-i / RATE * 90.0) for i, s in enumerate(noise)]


def thud(duration: float = 0.7) -> list[float]:
    n = int(duration * RATE)
    out = []
    phase = 0.0
    for i in range(n):
        t = i / RATE
        phase += math.tau * (45.0 + 60.0 * math.exp(-t * 14.0)) / RATE
        out.append(math.sin(phase) * math.exp(-t * 7.0))
    return out


def crowd(duration: float = 4.0) -> list[float]:
    n = int(duration * RATE)
    base = _lowpass(_lowpass(_noise(n, 8), lambda t: 0.12), lambda t: 0.2)
    rng = random.Random(9)
    voices = [(rng.uniform(1.5, 4.5), rng.uniform(0, math.tau)) for _ in range(6)]
    out = []
    for i, s in enumerate(base):
        t = i / RATE
        mod = sum(0.5 + 0.5 * math.sin(math.tau * f * t + p) for f, p in voices) / len(voices)
        out.append(s * 6.0 * (0.4 + 0.6 * mod) * math.sin(math.pi * i / n) ** 0.5)
    return out


SOUNDS: dict[str, Callable[[], list[float]]] = {
    "whoosh": whoosh,
    "impact": impact,
    "riser": riser,
    "swell": swell,
    "drip": drip,
    "alarm": alarm,
    "siren": siren,
    "rumble": rumble,
    "tick": tick,
    "thud": thud,
    "crowd": crowd,
}


def render(name: str, path: Path) -> Path:
    if path.exists():
        return path
    return _write(path, SOUNDS[name]())


def wav_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as handle:
        return handle.getnframes() / handle.getframerate()


__all__ = ["RATE", "SOUNDS", "render", "wav_seconds", "struct"]


def fire(duration: float = 4.0) -> list[float]:
    n = int(duration * RATE)
    rng = random.Random(11)
    bed = _lowpass(_noise(n, 12), lambda t: 0.08)
    out = []
    pop = 0.0
    for i, s in enumerate(bed):
        if rng.random() < 0.0004:
            pop = rng.uniform(0.4, 1.0)
        pop *= 0.995
        crackle = (rng.uniform(-1.0, 1.0) * pop) if pop > 0.01 else 0.0
        out.append((s * 4.0 + crackle * 0.6) * math.sin(math.pi * i / n) ** 0.4)
    return out


def horns(duration: float = 3.5) -> list[float]:
    n = int(duration * RATE)
    rng = random.Random(13)
    bursts = [(rng.uniform(0.0, duration - 0.8), rng.uniform(0.3, 0.9), rng.choice((330.0, 392.0, 440.0, 494.0))) for _ in range(6)]
    out = []
    for i in range(n):
        t = i / RATE
        value = 0.0
        for start, length, freq in bursts:
            if start <= t < start + length:
                env = min(1.0, (t - start) * 40.0) * min(1.0, (start + length - t) * 40.0)
                value += (math.sin(math.tau * freq * t) + 0.5 * math.sin(math.tau * freq * 1.26 * t) + 0.25 * math.sin(math.tau * freq * 2.0 * t)) * env * 0.25
        out.append(value)
    return out


def helicopter(duration: float = 5.0) -> list[float]:
    n = int(duration * RATE)
    noise = _lowpass(_noise(n, 14), lambda t: 0.06)
    out = []
    for i, s in enumerate(noise):
        t = i / RATE
        blade = 0.55 + 0.45 * max(0.0, math.sin(math.tau * 13.0 * t)) ** 3
        out.append(s * 6.0 * blade * math.sin(math.pi * i / n) ** 0.5 + 0.08 * math.sin(math.tau * 26.0 * t) * blade)
    return out


def heartbeat(duration: float = 4.0) -> list[float]:
    n = int(duration * RATE)
    out = []
    for i in range(n):
        t = i / RATE
        since = t % 1.0
        beat = 0.0
        for offset, gain in ((0.0, 1.0), (0.18, 0.6)):
            d = since - offset
            if 0.0 <= d < 0.25:
                beat += math.sin(math.tau * (50.0 + 20.0 * math.exp(-d * 30.0)) * d) * math.exp(-d * 14.0) * gain
        out.append(beat * 0.8)
    return out


def glass(duration: float = 1.2) -> list[float]:
    n = int(duration * RATE)
    rng = random.Random(15)
    out = []
    for i in range(n):
        t = i / RATE
        shards = sum(math.sin(math.tau * f * t) * math.exp(-t * d) for f, d in ((2100.0, 6.0), (3300.0, 9.0), (4700.0, 12.0), (1500.0, 5.0)))
        burst = rng.uniform(-1.0, 1.0) * math.exp(-t * 22.0)
        out.append(burst * 0.9 + shards * 0.12)
    return out


SOUNDS.update({"fire": fire, "horns": horns, "helicopter": helicopter, "heartbeat": heartbeat, "glass": glass})
