"""Flat-shaded terrain: noise hills, coastlines, reservoir bowls and flattened city zones."""

from __future__ import annotations

import math

from mathutils import Vector
from mathutils import noise as mnoise

from studio.blender.primitives import grid
from studio.core.motion import smoothstep


def ground(ctx, name, size=(400, 400), divisions=(80, 80), amplitude=0.0, seed=0, material=None, coast=None, bowl=None, flat=(), rise=None, noise_scale=0.012, z=0.0):
    """Terrain grid. coast={y,depth,width}; bowl={centre,radius,depth}; flat=[(x0,y0,x1,y1,blend)]; rise={axis,start,end,height}."""

    def height(x, y):
        h = amplitude * mnoise.fractal(Vector((x * noise_scale + seed * 13.7, y * noise_scale + seed * 7.1, 0.0)), 1.0, 2.0, 4)
        if rise:
            v = x if rise.get("axis", "y") == "x" else y
            t = smoothstep((v - rise["start"]) / max(1e-6, rise["end"] - rise["start"]))
            h += rise["height"] * t + rise.get("extra_noise", 0.0) * t * mnoise.fractal(Vector((x * 0.03, y * 0.03, 1.0)), 1.0, 2.0, 3)
        for x0, y0, x1, y1, blend in flat:
            dx = max(x0 - x, 0.0, x - x1)
            dy = max(y0 - y, 0.0, y - y1)
            d = math.hypot(dx, dy)
            if d < blend:
                h *= smoothstep(d / blend)
        if coast:
            d = coast["y"] - y
            if d > 0:
                t = smoothstep(min(1.0, d / coast.get("width", 30.0)))
                h = h * (1.0 - t) - coast["depth"] * t
        if bowl:
            cx, cy = bowl["centre"]
            r = math.hypot(x - cx, y - cy) / bowl["radius"]
            if r < 1.0:
                h -= bowl["depth"] * (1.0 - smoothstep(r))
        return z + h

    obj = grid(ctx, name, size, divisions, material or ctx.mat("sand"), height=height)
    ctx.tag("ground", obj)
    return obj
