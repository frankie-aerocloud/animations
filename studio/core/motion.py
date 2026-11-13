"""Pure interpolation helpers (no Blender dependency) used by camera and character animation."""

from __future__ import annotations

import math
from collections.abc import Sequence

Point = Sequence[float]


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def clamp01(t: float) -> float:
    return 0.0 if t < 0.0 else 1.0 if t > 1.0 else t


def smoothstep(t: float) -> float:
    t = clamp01(t)
    return t * t * (3.0 - 2.0 * t)


def ease_in_out(t: float) -> float:
    return smoothstep(t)


def ease_out_expo(t: float) -> float:
    t = clamp01(t)
    return 1.0 if t >= 1.0 else 1.0 - 2.0 ** (-10.0 * t)


def ease_in_expo(t: float) -> float:
    t = clamp01(t)
    return 0.0 if t <= 0.0 else 2.0 ** (10.0 * (t - 1.0))


def distance(a: Point, b: Point) -> float:
    return math.sqrt(sum((float(q) - float(p)) ** 2 for p, q in zip(a, b, strict=False)))


def polyline_length(points: Sequence[Point]) -> float:
    return sum(distance(points[i - 1], points[i]) for i in range(1, len(points)))


def point_along(points: Sequence[Point], travelled: float) -> tuple[float, ...]:
    """Point at arc distance `travelled` along the polyline (clamped to the ends)."""
    if len(points) == 1:
        return tuple(float(v) for v in points[0])
    remaining = max(0.0, travelled)
    for i in range(1, len(points)):
        a, b = points[i - 1], points[i]
        seg = distance(a, b)
        if remaining <= seg or i == len(points) - 1:
            t = 0.0 if seg == 0 else clamp01(remaining / seg)
            return tuple(lerp(float(p), float(q), t) for p, q in zip(a, b, strict=False))
        remaining -= seg
    return tuple(float(v) for v in points[-1])


def heading(a: Point, b: Point) -> float:
    """Rotation about Z (radians) that points local +Y from a towards b."""
    return math.atan2(-(float(b[0]) - float(a[0])), float(b[1]) - float(a[1]))


def unwrap(previous: float, angle: float) -> float:
    """Bring `angle` within pi of `previous` so interpolation takes the short way round."""
    while angle - previous > math.pi:
        angle -= math.tau
    while angle - previous < -math.pi:
        angle += math.tau
    return angle
