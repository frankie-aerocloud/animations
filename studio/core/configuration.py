"""Render profiles shared by build and render commands."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RenderProfile:
    scale: float
    samples: int
    denoise: bool


PROFILES = {
    "preview": RenderProfile(0.5, 16, False),
    "standard": RenderProfile(1.0, 48, True),
    "high": RenderProfile(1.0, 96, True),
}
