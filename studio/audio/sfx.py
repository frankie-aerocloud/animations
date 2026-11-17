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


def gulls(duration: float = 4.0) -> list[float]:
    """A colony of gulls: overlapping gliding screeches over a distant chatter bed."""
    n = int(duration * RATE)
    rng = random.Random(21)
    calls = [(rng.uniform(0.0, duration - 0.5), rng.uniform(0.18, 0.5), rng.uniform(1100.0, 2300.0), rng.uniform(0.35, 1.0)) for _ in range(14)]
    bed = _lowpass(_noise(n, 22), lambda t: 0.25)
    out = []
    for i in range(n):
        t = i / RATE
        value = bed[i] * 0.25 * (0.6 + 0.4 * math.sin(math.tau * 2.3 * t))
        for start, length, freq, gain in calls:
            if start <= t < start + length:
                u = (t - start) / length
                f = freq * (1.0 - 0.35 * u) * (1.0 + 0.04 * math.sin(math.tau * 28.0 * t))
                env = math.sin(math.pi * u) ** 0.6
                value += (math.sin(math.tau * f * t) + 0.45 * math.sin(math.tau * f * 2.0 * t) + 0.2 * math.sin(math.tau * f * 3.0 * t)) * env * gain * 0.28
        out.append(value)
    return out


def flapping(duration: float = 3.0) -> list[float]:
    n = int(duration * RATE)
    noise = _lowpass(_noise(n, 23), lambda t: 0.12)
    out = []
    for i, s in enumerate(noise):
        t = i / RATE
        beat = max(0.0, math.sin(math.tau * 4.6 * t)) ** 2.5 + 0.5 * max(0.0, math.sin(math.tau * 3.1 * t + 1.0)) ** 2.5
        out.append(s * 5.0 * beat * math.sin(math.pi * i / n) ** 0.5)
    return out


def drone_buzz(duration: float = 4.0) -> list[float]:
    n = int(duration * RATE)
    out = []
    for i in range(n):
        t = i / RATE
        f = 185.0 * (1.0 + 0.02 * math.sin(math.tau * 0.7 * t))
        value = sum(math.sin(math.tau * f * k * t) / k for k in range(1, 9))
        out.append(value * 0.12 * math.sin(math.pi * i / n) ** 0.4)
    return out


def loudspeaker(duration: float = 4.0) -> list[float]:
    """Muffled public-address announcement: syllable bursts of band-limited tone."""
    n = int(duration * RATE)
    rng = random.Random(24)
    syllables = []
    t = 0.3
    while t < duration - 0.3:
        length = rng.uniform(0.12, 0.3)
        syllables.append((t, length, rng.uniform(140.0, 220.0)))
        t += length + rng.uniform(0.03, 0.18)
    raw = []
    for i in range(n):
        t = i / RATE
        value = 0.0
        for start, length, f in syllables:
            if start <= t < start + length:
                u = (t - start) / length
                env = math.sin(math.pi * u) ** 0.5
                value += (math.sin(math.tau * f * t) + 0.6 * math.sin(math.tau * f * 2 * t) + 0.4 * math.sin(math.tau * f * 3 * t) + 0.25 * math.sin(math.tau * f * 4.5 * t)) * env
        raw.append(value * 0.22)
    return _lowpass(raw, lambda t: 0.18)


def jets(duration: float = 5.0) -> list[float]:
    n = int(duration * RATE)
    noise = _lowpass(_noise(n, 25), lambda t: 0.04 + 0.1 * math.sin(math.pi * t))
    return [s * 7.0 * (0.5 + 0.5 * math.sin(math.pi * i / n)) for i, s in enumerate(noise)]


def splat(duration: float = 0.35) -> list[float]:
    n = int(duration * RATE)
    noise = _lowpass(_noise(n, 26), lambda t: 0.3)
    out = []
    for i, s in enumerate(noise):
        t = i / RATE
        plop = math.sin(math.tau * (220.0 - 150.0 * min(1.0, t * 10.0)) * t) * math.exp(-t * 30.0)
        out.append(s * math.exp(-t * 18.0) * 1.5 + plop * 0.5)
    return out


SOUNDS.update({"gulls": gulls, "flapping": flapping, "drone_buzz": drone_buzz, "loudspeaker": loudspeaker, "jets": jets, "splat": splat})


def _bandpass(samples: list[float], freq: float, q: float) -> list[float]:
    w = math.tau * freq / RATE
    alpha = math.sin(w) / (2.0 * q)
    a0, a1, a2 = 1.0 + alpha, -2.0 * math.cos(w), 1.0 - alpha
    out, x1, x2, y1, y2 = [], 0.0, 0.0, 0.0, 0.0
    for x in samples:
        y = (alpha * x - alpha * x2 - a1 * y1 - a2 * y2) / a0
        x2, x1, y2, y1 = x1, x, y1, y
        out.append(y)
    return out


def roar(duration: float = 2.4) -> list[float]:
    """Big-cat roar: a rough, falling growl through two vocal-tract resonances, soft-clipped."""
    n = int(duration * RATE)
    rng = random.Random(31)
    noise = _noise(n, 32)
    source, phase = [], 0.0
    for i in range(n):
        t = i / RATE
        f0 = 92.0 + 34.0 * math.sin(math.pi * min(1.0, t / duration)) + 7.0 * math.sin(math.tau * 9.0 * t) + rng.uniform(-5.0, 5.0)
        phase += math.tau * f0 / RATE
        saw = sum(math.sin(phase * k) / k for k in range(1, 10))
        source.append(saw * 0.7 + noise[i] * 0.6)
    voiced = [a + b * 0.8 for a, b in zip(_bandpass(source, 420.0, 2.0), _bandpass(source, 1050.0, 3.0), strict=False)]
    chest = _lowpass(source, lambda t: 0.04)
    out = []
    for i in range(n):
        t = i / RATE
        env = min(1.0, t / 0.16) * (1.0 if t < duration * 0.5 else max(0.0, 1.0 - (t - duration * 0.5) / (duration * 0.5)) ** 1.5)
        out.append(math.tanh((voiced[i] * 2.5 + chest[i] * 2.0) * 1.8) * env)
    return out


def alert(duration: float = 2.6) -> list[float]:
    """Broadcast-style attention chime (three falling bell tones, twice). Deliberately not the EAS tone."""
    n = int(duration * RATE)
    out = [0.0] * n
    for repeat in (0.0, 1.25):
        for k, freq in enumerate((988.0, 784.0, 523.0)):
            start = int((repeat + k * 0.3) * RATE)
            for i in range(start, min(n, start + int(1.0 * RATE))):
                t = (i - start) / RATE
                bell = math.sin(math.tau * freq * t) + 0.4 * math.sin(math.tau * freq * 2.76 * t) + 0.2 * math.sin(math.tau * freq * 5.4 * t)
                out[i] += bell * math.exp(-t * 4.5) * 0.35
    return out


def radio(duration: float = 1.6) -> list[float]:
    """Radio static burst with crackle and a squelch tail."""
    n = int(duration * RATE)
    rng = random.Random(33)
    hiss = _bandpass(_noise(n, 34), 1800.0, 0.8)
    out = []
    for i, s in enumerate(hiss):
        t = i / RATE
        crackle = rng.uniform(-1.0, 1.0) if rng.random() < 0.002 else 0.0
        squelch = math.sin(math.tau * 1100.0 * t) * 0.25 if t > duration - 0.18 else 0.0
        out.append((s * 3.0 + crackle) * min(1.0, t / 0.02) + squelch)
    return out


SOUNDS.update({"roar": roar, "alert": alert, "radio": radio})


def thunder(duration: float = 5.0) -> list[float]:
    """A close crack that rolls away into a long low rumble."""
    n = int(duration * RATE)
    crack = _lowpass(_noise(n, 31), lambda t: 0.6)
    roll = _lowpass(_lowpass(_noise(n, 32), lambda t: 0.012), lambda t: 0.03)
    rng = random.Random(33)
    swells = [(rng.uniform(0.2, duration * 0.7), rng.uniform(0.4, 1.2)) for _ in range(5)]
    out = []
    for i in range(n):
        t = i / RATE
        value = crack[i] * math.exp(-t * 14.0) * 0.9
        envelope = min(1.0, t / 0.15) * math.exp(-t * 0.55)
        for start, width in swells:
            envelope += 0.5 * math.exp(-(((t - start) / width) ** 2)) * math.exp(-t * 0.4)
        out.append(value + roll[i] * 9.0 * envelope)
    return out


def birds(duration: float = 5.0) -> list[float]:
    """Dawn chorus: scattered chirps and short warbles, fading in."""
    n = int(duration * RATE)
    rng = random.Random(41)
    calls = []
    for _ in range(26):
        start = rng.uniform(0.0, duration - 0.4)
        notes = rng.randint(1, 4)
        base = rng.uniform(2600.0, 5200.0)
        for k in range(notes):
            calls.append((start + k * rng.uniform(0.08, 0.14), rng.uniform(0.05, 0.12), base * rng.uniform(0.9, 1.25), rng.uniform(-0.5, 0.5), rng.uniform(0.3, 1.0)))
    out = []
    for i in range(n):
        t = i / RATE
        value = 0.0
        for start, length, freq, bend, gain in calls:
            if start <= t < start + length:
                u = (t - start) / length
                f = freq * (1.0 + bend * u)
                value += math.sin(math.tau * f * t) * math.sin(math.pi * u) * gain * 0.35
        out.append(value * min(1.0, t / 1.2))
    return out


SOUNDS.update({"thunder": thunder, "birds": birds})


def gust(duration: float = 3.2) -> list[float]:
    """A violent gust: noise through a resonant filter that sweeps up and back, swelling then dying."""
    n = int(duration * RATE)
    rng = random.Random(51)
    low = band = 0.0
    out = []
    for i in range(n):
        t = i / RATE
        u = t / duration
        f = 250.0 + 900.0 * math.sin(math.pi * u) ** 1.5
        tune = 2.0 * math.sin(math.pi * f / RATE)
        x = rng.uniform(-1.0, 1.0)
        low += tune * band
        band += tune * (x - low - 0.12 * band)
        envelope = min(1.0, t / 0.35) * math.exp(-max(0.0, t - 0.8) * 1.4)
        out.append((band * 0.6 + low * 0.25) * envelope)
    return out


SOUNDS.update({"gust": gust})


def powerdown(duration: float = 2.2) -> list[float]:
    """Machinery winding down: a motor whine falling in pitch and fading, ending in a soft clunk."""
    n = int(duration * RATE)
    rng = random.Random(61)
    out = []
    phase = 0.0
    hum = 0.0
    for i in range(n):
        t = i / RATE
        u = t / duration
        freq = 40.0 + 360.0 * (1.0 - u) ** 2.2
        phase += math.tau * freq / RATE
        hum += 0.05 * (rng.uniform(-1.0, 1.0) - hum)
        whine = (math.sin(phase) + 0.4 * math.sin(2 * phase) + 0.2 * math.sin(3 * phase)) * (1.0 - u) ** 1.4
        clunk = math.sin(math.tau * 55.0 * (t - duration * 0.82)) * math.exp(-(t - duration * 0.82) * 18.0) if t > duration * 0.82 else 0.0
        out.append(whine * 0.5 + hum * 2.0 * (1.0 - u) + clunk * 0.8)
    return out


def machinery(duration: float = 4.0) -> list[float]:
    """A busy production line: a steady motor hum under rhythmic clacks and the hiss of air."""
    n = int(duration * RATE)
    rng = random.Random(62)
    out = []
    phase = 0.0
    hiss = 0.0
    for i in range(n):
        t = i / RATE
        phase += math.tau * 98.0 / RATE
        hum = math.sin(phase) * 0.25 + math.sin(2 * phase) * 0.12
        beat = t % 0.36
        clack = rng.uniform(-1.0, 1.0) * math.exp(-beat * 70.0) * (0.8 if int(t / 0.36) % 2 else 0.5)
        hiss += 0.3 * (rng.uniform(-1.0, 1.0) - hiss)
        out.append((hum + clack * 0.6 + hiss * 0.08) * min(1.0, t / 0.2, (duration - t) / 0.3))
    return out


def surf(duration: float = 6.0) -> list[float]:
    """Waves on a beach: slow swells of filtered noise breaking and washing back."""
    n = int(duration * RATE)
    noise = _lowpass(_noise(n, 63), lambda t: 0.08)
    out = []
    for i, s in enumerate(noise):
        t = i / RATE
        swell = 0.25 + 0.75 * max(0.0, math.sin(math.tau * t / 3.0)) ** 2
        out.append(s * 3.0 * swell * min(1.0, t / 0.5, (duration - t) / 0.8))
    return out


SOUNDS.update({"powerdown": powerdown, "machinery": machinery, "surf": surf})
