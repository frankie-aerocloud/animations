"""Weather for the London production: looping rain, puddles, low cloud decks, rain shafts and a
cloud break. Everything is merged into a few meshes so heavy rain stays cheap to render."""

from __future__ import annotations

import math

from studio.assets.meshes import merged_boxes
from studio.blender.primitives import empty, fcurves, ico, key, mesh_from_pydata, multi_box, parent, set_interp


def _loop(obj, frames, offset):
    """Key `obj` from its location to location + offset over `frames`, repeating forever."""
    start = tuple(obj.location)
    key(obj, "location", 1, start)
    key(obj, "location", 1 + frames, (start[0] + offset[0], start[1] + offset[1], start[2] + offset[2]))
    set_interp(obj, "LINEAR", path="location")
    for curve in fcurves(obj, "location"):
        curve.modifiers.new("CYCLES")


def rain(ctx, name, centre, extent=(36.0, 36.0, 22.0), count=6000, speed=10.0, length=0.7, width=0.008, slant=(0.10, 0.04), strength=0.25, colour=(0.80, 0.85, 0.92), alpha=0.4, clear=2.5):
    """Falling rain streaks filling a box around `centre` (x, y, ground z). Two identical layers are
    stacked one box-height apart and the mesh falls one layer per cycle, so the loop is seamless.
    `strength` is the streaks' emission: higher reads better against dark backgrounds. No streak
    falls within `clear` metres of the centre, where the camera usually is."""
    rng = ctx.rng
    cx, cy, cz = centre
    w, d, h = extent
    sx, sy = slant
    tilt = (math.atan(sy), -math.atan(sx))
    boxes = []
    for _ in range(count):
        x, y, z = rng.uniform(-w / 2, w / 2), rng.uniform(-d / 2, d / 2), rng.uniform(0.0, h)
        if math.hypot(x, y) < clear:
            continue
        streak = length * rng.uniform(0.7, 1.2)
        for layer in (0.0, 1.0):
            boxes.append(((x + sx * h * layer, y + sy * h * layer, z + h * layer), (width, width, streak), 0))
    material = ctx.palette.make(f"{name} rain", colour, roughness=0.2, emission=strength, alpha=alpha)
    obj = merged_boxes(ctx, name, boxes, [material], (cx, cy, cz - 1.0))
    # streaks lean with the wind; the fall direction matches the lean
    obj.rotation_euler = (tilt[0], tilt[1], 0.0)
    obj.visible_shadow = False
    _loop(obj, max(2, round(h / speed * ctx.fps)), (-sx * h, -sy * h, -h))
    ctx.tag("rain", obj)
    return obj


def _blob(rng, cx, cy, rx, ry, z, sides=9):
    verts = []
    for k in range(sides):
        a = math.tau * k / sides
        r = rng.uniform(0.75, 1.15)
        verts.append((cx + rx * r * math.cos(a), cy + ry * r * math.sin(a), z))
    return verts


def puddles(ctx, name, area, count, size=(0.8, 3.0), z=0.035, material=None, avoid=()):
    """Flat irregular puddles scattered inside area = (x0, y0, x1, y1), merged into one mesh.
    `avoid` is a list of (x0, y0, x1, y1) rectangles kept dry."""
    rng = ctx.rng
    x0, y0, x1, y1 = area
    verts, faces = [], []
    placed = 0
    for _ in range(count * 4):
        if placed >= count:
            break
        cx, cy = rng.uniform(x0, x1), rng.uniform(y0, y1)
        if any(a <= cx <= c and b <= cy <= e for a, b, c, e in avoid):
            continue
        rx = rng.uniform(*size) / 2
        ry = rx * rng.uniform(0.4, 1.0)
        ring = _blob(rng, cx, cy, rx, ry, z)
        base = len(verts)
        verts.extend(ring)
        faces.append(tuple(range(base, base + len(ring))))
        placed += 1
    material = material or murky(ctx, f"{name} water", "puddle", roughness=0.06)
    obj = mesh_from_pydata(ctx, name, verts, faces, [material])
    obj.visible_shadow = False
    ctx.tag("puddle", obj)
    return obj


def wet(ctx, colour, roughness=0.3, specular=0.18):
    """Rain-soaked tarmac or paving: darker and glossier, without mirroring the whole sky."""
    key_ = ("wet", str(colour), roughness, specular)
    material = ctx.palette._cache.get(key_)
    if material is None:
        material = ctx.palette.make(f"wet {colour}", ctx.palette.colour(colour), roughness=roughness)
        material.node_tree.nodes["Principled BSDF"].inputs["Specular IOR Level"].default_value = specular
        ctx.palette._cache[key_] = material
    return material


def murky(ctx, name, colour="flood_brown", roughness=0.4, bump=0.15, scale=2.5, specular=0.12):
    """Opaque, dull floodwater or puddle surface: little sky glare, a faint ripple bump."""
    material = ctx.palette.make(name, ctx.palette.colour(colour), roughness=roughness)
    nodes, links = material.node_tree.nodes, material.node_tree.links
    bsdf = nodes["Principled BSDF"]
    bsdf.inputs["Specular IOR Level"].default_value = specular
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale
    bump_node = nodes.new("ShaderNodeBump")
    bump_node.inputs["Strength"].default_value = bump
    links.new(noise.outputs["Fac"], bump_node.inputs["Height"])
    links.new(bump_node.outputs["Normal"], bsdf.inputs["Normal"])
    return material


def cloud_deck(ctx, name, centre, extent, base, count=60, puff=(90.0, 220.0), colour="cloud_dark", alpha=1.0, thickness=0.35, hole=None):
    """A low ceiling of flattened puffs over centre = (x, y). hole = (x, y, radius) leaves a gap.
    Returns the puff objects (for parting the clouds)."""
    rng = ctx.rng
    cx, cy = centre
    w, d = extent
    material = ctx.palette.make(f"{name} cloud", ctx.palette.colour(colour), roughness=1.0, alpha=alpha)
    puffs = []
    for i in range(count):
        x, y = cx + rng.uniform(-w / 2, w / 2), cy + rng.uniform(-d / 2, d / 2)
        if hole and math.hypot(x - hole[0], y - hole[1]) < hole[2]:
            continue
        r = rng.uniform(*puff)
        z = base + rng.uniform(0.0, r * thickness * 0.6)
        obj = ico(ctx, f"{name}.{i}", r, (x, y, z), material, subdiv=2, scale=(1.0, rng.uniform(0.7, 1.3), thickness), smooth=True)
        obj.visible_shadow = False
        ctx.tag("cloud", obj)
        puffs.append(obj)
    return puffs


def part_clouds(ctx, puffs, centre, start, end, distance=900.0):
    """Push puffs away from centre = (x, y) between start and end seconds (the clouds break)."""
    f0, f1 = ctx.frame(start), ctx.frame(end)
    for obj in puffs:
        x, y, z = obj.location
        dx, dy = x - centre[0], y - centre[1]
        r = max(1.0, math.hypot(dx, dy))
        push = distance * max(0.2, 1.0 - r / (distance * 2.5))
        key(obj, "location", f0, (x, y, z))
        key(obj, "location", f1, (x + dx / r * push, y + dy / r * push, z + 30.0))
        set_interp(obj, "SINE", "EASE_IN_OUT", path="location")


def spiral(ctx, name, centre, radius, arms=3, count=560, base=1500.0, spin=6.0, colour="cloud_white"):
    """A cyclonic cloud system seen from above: flat, overlapping puffs on spiral arms around a dense
    core (the ground shows between the arms), turning `spin` degrees over the shot."""
    rng = ctx.rng
    material = ctx.palette.make(f"{name} cloud", ctx.palette.colour(colour), roughness=1.0)
    core = ctx.palette.make(f"{name} core", ctx.palette.colour("cloud_light"), roughness=1.0)
    root = empty(ctx, name, (centre[0], centre[1], 0.0))
    for i in range(count):
        if i < count * 0.2:
            r, a = radius * 0.16 * rng.random() ** 0.5, rng.uniform(0, math.tau)
            mat = core
        else:
            t = rng.random()
            arm = rng.randrange(arms)
            a = arm * math.tau / arms + t * 2.6 * math.pi + rng.uniform(-0.12, 0.12)
            r = radius * (0.16 + 0.84 * t) + rng.uniform(-radius * 0.03, radius * 0.03)
            mat = material
        size = rng.uniform(0.035, 0.07) * radius * (0.6 + 0.6 * r / radius)
        stretch = rng.uniform(1.5, 2.6)  # puffs elongate along the arm, so the arms read as streaks
        puff = ico(ctx, f"{name}.{i}", size, (r * math.cos(a), r * math.sin(a), base + rng.uniform(0, size * 0.25)), mat, subdiv=2, scale=(stretch, 1.0, 0.16), rot=(0.0, 0.0, a + math.pi / 2), smooth=True)
        puff.visible_shadow = False
        parent(puff, root)
    key(root, "rotation_euler", 1, (0.0, 0.0, 0.0))
    key(root, "rotation_euler", ctx.frames, (0.0, 0.0, math.radians(spin)))
    set_interp(root, "LINEAR", path="rotation_euler")
    ctx.tag("cloud", root)
    return root


def rain_shafts(ctx, name, centre, extent, count=14, top=380.0, colour="rain_shaft", alpha=0.12):
    """Grey translucent columns hanging under a cloud deck: rain seen from a distance."""
    rng = ctx.rng
    cx, cy = centre
    w, d = extent
    boxes = []
    for _ in range(count):
        x, y = cx + rng.uniform(-w / 2, w / 2), cy + rng.uniform(-d / 2, d / 2)
        r = rng.uniform(120.0, 320.0)
        boxes.append(((x, y, top / 2), (r, r * rng.uniform(0.6, 1.2), top), 0))
    material = ctx.palette.make(f"{name} shaft", ctx.palette.colour(colour), roughness=1.0, alpha=alpha)
    obj = multi_box(ctx, name, boxes, [material], bevel=0.0)
    obj.visible_shadow = False
    ctx.tag("rain_shaft", obj)
    return obj
