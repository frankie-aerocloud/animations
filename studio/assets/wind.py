"""Wind for the Los Angeles production: tumbling debris streams, dust streaks, bursting windows,
objects torn loose and thrown, crashing surf and embers. Wind blows toward local -X unless a
direction is given. Every effect can wait for the first gust (`start`, seconds)."""

from __future__ import annotations

import math

from studio.assets.meshes import merged_boxes
from studio.blender.primitives import fcurves, ico, key, mesh_from_pydata, set_interp

DEBRIS = ("plywood", "stucco_debris", "roof_tile", "sheet_metal", "frond", "paper", "plastic_blue", "dark_steel")


def appear(ctx, obj, start):
    """Hidden until `start` seconds, then visible (the gust arrives)."""
    if start <= 0:
        return
    frame = max(2, ctx.frame(start))
    obj.hide_render = True
    key(obj, "hide_render", 1)
    key(obj, "hide_render", frame - 1)
    obj.hide_render = False
    key(obj, "hide_render", frame)


def _loop(obj, frames, offset):
    start = tuple(obj.location)
    key(obj, "location", 1, start)
    key(obj, "location", 1 + frames, (start[0] + offset[0], start[1] + offset[1], start[2] + offset[2]))
    set_interp(obj, "LINEAR", path="location")
    for curve in fcurves(obj, "location"):
        curve.modifiers.new("CYCLES")


def debris(ctx, name, centre, extent=(60.0, 40.0, 14.0), count=400, speed=55.0, clusters=12, sizes=(0.15, 1.2), kinds=DEBRIS, start=0.0, tumble=1.5, lift=0.0):
    """A storm of tumbling debris crossing a box around centre = (x, y, ground z), blowing toward -X.
    Pieces are grouped into compact clusters; each cluster tumbles about its own centre while it
    races across the box and wraps around at the far edge (make the box wider than the shot), with
    staggered phases so the stream never thins out."""
    rng = ctx.rng
    cx, cy, cz = centre
    w, d, h = extent
    mats = [ctx.mat(k, roughness=0.8) for k in kinds]
    objs = []
    per = max(1, count // clusters)
    for c in range(clusters):
        y, z = cy + rng.uniform(-d / 2, d / 2), cz + rng.uniform(1.0, h)
        boxes = []
        for _ in range(per):
            s = rng.uniform(*sizes)
            shape = rng.random()
            size = (s, s * rng.uniform(0.4, 1.0), s * 0.06) if shape < 0.6 else ((s, s * 0.15, s * 0.15) if shape < 0.85 else (s * 0.5, s * 0.5, s * 0.5))
            boxes.append(((rng.uniform(-5, 5), rng.uniform(-5, 5), rng.uniform(-2.5, 2.5)), size, rng.randrange(len(mats))))
        obj = merged_boxes(ctx, f"{name}{c}", boxes, mats, (cx + w / 2, y, z))
        obj.visible_shadow = False
        period = max(2, round(w / speed * ctx.fps * rng.uniform(0.85, 1.15)))
        phase = round(c / clusters * period)
        key(obj, "location", 1 - phase, (cx + w / 2, y, z))
        key(obj, "location", 1 - phase + period, (cx - w / 2, y + rng.uniform(-4, 4), z + lift))
        set_interp(obj, "LINEAR", path="location")
        for curve in fcurves(obj, "location"):
            curve.modifiers.new("CYCLES")
        obj.rotation_euler = (rng.uniform(0, 6), rng.uniform(0, 6), rng.uniform(0, 6))
        key(obj, "rotation_euler", 1)
        obj.rotation_euler = (obj.rotation_euler.x + tumble * rng.uniform(-6, 6), obj.rotation_euler.y + tumble * rng.uniform(-6, 6), obj.rotation_euler.z + tumble * rng.uniform(-3, 3))
        key(obj, "rotation_euler", ctx.frames)
        set_interp(obj, "LINEAR", path="rotation_euler")
        appear(ctx, obj, start)
        ctx.tag("debris", obj)
        objs.append(obj)
    return objs


def streaks(ctx, name, centre, extent=(80.0, 50.0, 20.0), count=900, speed=90.0, colour="dust", strength=0.0, alpha=0.35, length=(3.0, 9.0), start=0.0):
    """Thin horizontal dust streaks racing downwind: the wind made visible."""
    rng = ctx.rng
    cx, cy, cz = centre
    w, d, h = extent
    boxes = []
    for _ in range(count):
        x, y, z = rng.uniform(-w / 2, w / 2), rng.uniform(-d / 2, d / 2), rng.uniform(0.2, h)
        size = (rng.uniform(*length), 0.025, 0.025)
        for copy in (0.0, 1.0):
            boxes.append(((x + copy * w, y, z), size, 0))
    material = ctx.palette.make(f"{name} dust", ctx.palette.colour(colour), roughness=1.0, emission=strength, alpha=alpha)
    obj = merged_boxes(ctx, name, boxes, [material], (cx, cy, cz))
    obj.visible_shadow = False
    _loop(obj, max(2, round(w / speed * ctx.fps)), (-w, 0.0, 0.0))
    appear(ctx, obj, start)
    ctx.tag("streaks", obj)
    return obj


def glass_burst(ctx, name, origin, normal, at, count=40, spread=6.0, colour="glass_shard"):
    """Shards bursting out of a window at `at` seconds and blowing downwind."""
    rng = ctx.rng
    ox, oy, oz = origin
    nx, ny = normal
    material = ctx.palette.make(f"{name} shards", ctx.palette.colour(colour), roughness=0.05, metallic=0.2)
    boxes = []
    for _ in range(count):
        s = rng.uniform(0.08, 0.45)
        boxes.append(((rng.uniform(-1.0, 1.0), rng.uniform(-1.0, 1.0), rng.uniform(-0.8, 0.8)), (s, s * 0.7, 0.02), 0))
    obj = merged_boxes(ctx, name, boxes, [material], (ox, oy, oz))
    obj.visible_shadow = False
    f0 = max(2, ctx.frame(at))
    obj.scale = (0.2, 0.2, 0.2)
    key(obj, "scale", f0)
    key(obj, "location", f0)
    obj.scale = (spread / 2, spread / 2, spread / 3)
    obj.location = (ox + nx * spread - 18.0, oy + ny * spread, oz - 6.0)
    key(obj, "scale", f0 + round(1.6 * ctx.fps))
    key(obj, "location", f0 + round(1.6 * ctx.fps))
    obj.rotation_euler = (0, 0, 0)
    key(obj, "rotation_euler", f0)
    obj.rotation_euler = (rng.uniform(2, 5), rng.uniform(2, 5), rng.uniform(1, 3))
    key(obj, "rotation_euler", f0 + round(1.6 * ctx.fps))
    set_interp(obj, "QUAD", "EASE_OUT", path="location")
    appear(ctx, obj, at)
    ctx.tag("glass", obj)
    return obj


def fly(ctx, obj, start, end, offset, spin=(2.0, 3.0, 1.0), arc=6.0):
    """Tear an object loose at `start` and throw it downwind by `offset`, tumbling (cars, roofs,
    signs, palms). The arc lifts it `arc` metres at mid-flight; it lands at the end."""
    f0, f1 = ctx.frame(start), max(ctx.frame(start) + 2, ctx.frame(end))
    x, y, z = obj.location
    rx, ry, rz = obj.rotation_euler
    key(obj, "location", f0, (x, y, z))
    key(obj, "location", (f0 + f1) // 2, (x + offset[0] / 2, y + offset[1] / 2, z + offset[2] / 2 + arc))
    key(obj, "location", f1, (x + offset[0], y + offset[1], z + offset[2]))
    key(obj, "rotation_euler", f0, (rx, ry, rz))
    key(obj, "rotation_euler", f1, (rx + spin[0] * math.tau, ry + spin[1] * math.tau, rz + spin[2] * math.tau))
    set_interp(obj, "SINE", "EASE_IN_OUT", path="location")
    set_interp(obj, "LINEAR", path="rotation_euler")
    ctx.tag("thrown", obj)
    return obj


def topple(ctx, obj, at, duration=1.2, angle=-80.0, axis=1):
    """Tip an object over about its base (poles, palms, signs) starting at `at` seconds."""
    f0, f1 = ctx.frame(at), ctx.frame(at + duration)
    start = tuple(obj.rotation_euler)
    key(obj, "rotation_euler", f0, start)
    end = list(start)
    end[axis] += math.radians(angle)
    key(obj, "rotation_euler", f1, tuple(end))
    set_interp(obj, "QUAD", "EASE_IN", path="rotation_euler")
    return obj


def surf(ctx, name, shore_y, width, count=5, height=6.0, speed=9.0, start_y=None, colour="sea_wave"):
    """Big storm waves: crests that roll toward the shore (toward -Y) and repeat, with white tops."""
    rng = ctx.rng
    start_y = shore_y + 260.0 if start_y is None else start_y
    water = ctx.palette.make(f"{name} water", ctx.palette.colour(colour), roughness=0.2)
    foam = ctx.mat("foam", roughness=0.9)
    period = max(2, round((start_y - shore_y) / speed * ctx.fps))
    objs = []
    # wave profile in (y, z) from the gentle back to the curling lip that faces the shore (-Y)
    profile = [(40.0, 0.0), (26.0, 0.25), (14.0, 0.55), (7.0, 0.8), (3.0, 0.95), (0.0, 1.0), (-2.5, 0.93), (-3.4, 0.78), (-2.6, 0.62), (-1.2, 0.5), (-0.8, 0.25), (-1.5, 0.0)]
    for i in range(count):
        verts, faces, face_mats = [], [], []
        for x in (-width / 2, width / 2):
            for y, z in profile:
                verts.append((x, y * height / 10.0 * 1.6, z * height))
        n = len(profile)
        for k in range(n - 1):
            faces.append((k, k + 1, n + k + 1, n + k))
            face_mats.append(1 if 3 <= k <= 6 else 0)  # white only along the lip; the face stays sea-coloured
        crest = mesh_from_pydata(ctx, f"{name}{i}", verts, faces, [water, foam], (0.0, start_y, 0.0), face_mats=face_mats, smooth=True)
        offset = round(i / count * period)
        key(crest, "location", 1 - offset, (rng.uniform(-6, 6), start_y, -height * 0.55))
        key(crest, "location", 1 - offset + period, (rng.uniform(-6, 6), shore_y, -height * 0.1))
        set_interp(crest, "LINEAR", path="location")
        for curve in fcurves(crest, "location"):
            curve.modifiers.new("CYCLES")
        crest.visible_shadow = False
        ctx.tag("surf", crest)
        objs.append(crest)
    return objs


def plume(ctx, name, base, height=220.0, drift=(600.0, 0.0), colour="smoke_light", alpha=0.55):
    """Smoke after the wind drops: a thin rising stem that bends over into a long, flat, drifting sheet."""
    rng = ctx.rng
    material = ctx.palette.make(f"{name} smoke", ctx.palette.colour(colour), roughness=1.0, alpha=alpha)
    x, y, z = base
    objs = []
    for i in range(4):
        t = i / 3
        puff = ico(ctx, f"{name}.stem{i}", 14.0 + 10.0 * t, (x + drift[0] * 0.05 * t, y + drift[1] * 0.05 * t, z + height * 0.8 * t), material, subdiv=2, scale=(1.0, 1.0, 1.6), smooth=True)
        objs.append(puff)
    for i in range(9):
        t = (i + 1) / 9
        r = 30.0 + 50.0 * t
        puff = ico(ctx, f"{name}.sheet{i}", r, (x + drift[0] * t, y + drift[1] * t + rng.uniform(-25, 25), z + height + rng.uniform(-10, 25) * t), material, subdiv=2, scale=(1.8, 1.2, 0.35), smooth=True)
        objs.append(puff)
    for puff in objs:
        puff.visible_shadow = False
    return objs


def embers(ctx, name, centre, extent=(50.0, 30.0, 18.0), count=500, speed=30.0, start=0.0):
    """Glowing embers streaming downwind from fires."""
    rng = ctx.rng
    cx, cy, cz = centre
    w, d, h = extent
    boxes = []
    for _ in range(count):
        x, y, z = rng.uniform(-w / 2, w / 2), rng.uniform(-d / 2, d / 2), rng.uniform(0.5, h)
        s = rng.uniform(0.05, 0.16)
        for copy in (0.0, 1.0):
            boxes.append(((x + copy * w, y, z), (s, s, s), 0))
    glow = ctx.palette.emissive(f"{name} glow", "ember", 2.5)  # brighter saturates to white
    obj = merged_boxes(ctx, name, boxes, [glow], (cx, cy, cz))
    obj.visible_shadow = False
    _loop(obj, max(2, round(w / speed * ctx.fps)), (-w, 0.0, 3.0))
    appear(ctx, obj, start)
    ctx.tag("embers", obj)
    return obj


def smoke_column(ctx, name, base, height=120.0, lean=0.9, puffs=14, colour="smoke", width=1.0):
    """A wind-bent smoke plume: puffs that grow and lean downwind with height (`width` scales them)."""
    rng = ctx.rng
    material = ctx.palette.make(f"{name} smoke", ctx.palette.colour(colour), roughness=1.0, alpha=0.75)
    x, y, z = base
    objs = []
    for i in range(puffs):
        t = i / max(1, puffs - 1)
        r = (6.0 + 22.0 * t) * width
        puff = ico(ctx, f"{name}.{i}", r, (x - lean * height * t * t, y + rng.uniform(-6, 6), z + height * t), material, subdiv=2, scale=(1.6, 1.0, 0.8), smooth=True)
        puff.visible_shadow = False
        objs.append(puff)
    return objs
