"""Low-poly lions: rigged animals for close shots (walk, prowl, run, roar, idle, lie), merged horde
silhouettes for distant masses, glowing eyes for night shots and static lions for rooftops.

A lion faces local +Y; its root's rotation Z is the heading. Every part is tagged 'lion'."""

from __future__ import annotations

import math
from dataclasses import dataclass

from mathutils import Vector

from studio.blender.primitives import add_noise, empty, key, multi_box, parent, set_interp
from studio.core.motion import heading, polyline_length, unwrap

GAITS = {
    # period (s), leg swing (deg), body bob (m), body pitch (deg), speed (m/s), phase per leg (BL, FL, BR, FR)
    "walk": dict(period=1.1, swing=24.0, bob=0.025, pitch=1.5, speed=1.5, phases=(0.0, 0.25, 0.5, 0.75)),
    "prowl": dict(period=1.6, swing=18.0, bob=0.015, pitch=1.0, speed=0.9, phases=(0.0, 0.25, 0.5, 0.75)),
    "run": dict(period=0.55, swing=48.0, bob=0.08, pitch=7.0, speed=8.0, phases=(0.0, 0.5, 0.1, 0.6)),
}
LEGS = (("bl", -0.19, -0.55), ("fl", -0.19, 0.55), ("br", 0.19, -0.55), ("fr", 0.19, 0.55))
REST = (0.0, 0.0, 0.0)


@dataclass
class Lion:
    id: str
    root: object
    body: object
    head: object
    jaw: object
    tail: object
    legs: dict
    male: bool


def _materials(ctx):
    return (ctx.mat("lion", roughness=0.9), ctx.mat("lion_light", roughness=0.9), ctx.mat("mane", roughness=0.95), ctx.mat("lion_nose", roughness=0.6))


def build(ctx, spec):
    rng = ctx.rng
    lid = str(spec["id"])
    male = bool(spec.get("male", rng.random() < 0.45))
    s = float(spec.get("scale", 1.0)) * rng.uniform(0.92, 1.08) * (1.0 if male else 0.9)
    fur, light, mane, dark = _materials(ctx)
    at = list(spec.get("at", (0.0, 0.0)))
    root = empty(ctx, lid, (float(at[0]), float(at[1]), float(at[2]) if len(at) > 2 else 0.0))
    root.rotation_euler = (0.0, 0.0, math.radians(float(spec.get("face", 0.0))))
    root.scale = (s, s, s)
    body = multi_box(ctx, f"{lid}.body", [((0, 0, 0), (0.55, 1.5, 0.55), 0), ((0, 0.5, 0.04), (0.6, 0.55, 0.66), 0), ((0, -0.55, 0.02), (0.5, 0.45, 0.55), 0), ((0, 0.05, -0.28), (0.44, 1.1, 0.16), 1)], [fur, light], bevel=0.05)
    body.location = (0.0, 0.0, 0.95)
    parent(body, root)
    head_boxes = [((0, 0.18, 0.05), (0.42, 0.48, 0.42), 0), ((0, 0.48, -0.03), (0.26, 0.26, 0.2), 1), ((0, 0.62, 0.03), (0.12, 0.06, 0.08), 3)]
    head_boxes += [((sx * 0.15, 0.06, 0.27), (0.1, 0.05, 0.12), 0) for sx in (-1, 1)]
    head_boxes += [((sx * 0.11, 0.42, 0.12), (0.06, 0.02, 0.04), 3) for sx in (-1, 1)]
    if male:
        head_boxes += [((0, 0.02, 0.02), (0.82, 0.44, 0.86), 2), ((0, -0.12, -0.3), (0.56, 0.5, 0.5), 2), ((0, 0.2, 0.36), (0.6, 0.3, 0.22), 2)]
    head = multi_box(ctx, f"{lid}.head", head_boxes, [fur, light, mane, dark], bevel=0.04)
    head.location = (0.0, 0.82, 0.3)
    parent(head, body)
    jaw = multi_box(ctx, f"{lid}.jaw", [((0, 0.15, -0.04), (0.24, 0.3, 0.07), 0)], [light], bevel=0.02)
    jaw.location = (0.0, 0.3, -0.13)
    parent(jaw, head)
    tail = multi_box(ctx, f"{lid}.tail", [((0, 0, -0.42), (0.07, 0.07, 0.85), 0), ((0, 0, -0.88), (0.14, 0.14, 0.18), 1)], [fur, mane])
    tail.location = (0.0, -0.78, 0.15)
    tail.rotation_euler = (math.radians(-35), 0.0, 0.0)
    parent(tail, body)
    legs = {}
    for name, x, y in LEGS:
        leg = multi_box(ctx, f"{lid}.leg_{name}", [((0, 0, -0.45), (0.17, 0.2, 0.9), 0), ((0, 0.05, -0.88), (0.2, 0.28, 0.1), 1)], [fur, light], bevel=0.03)
        leg.location = (x, y, 0.0)
        parent(leg, body)
        legs[name] = leg
    for obj in (root, body, head, jaw, tail, *legs.values()):
        ctx.tag("lion", obj)
    lion = Lion(lid, root, body, head, jaw, tail, legs, male)
    ctx.objects[lid] = root
    return lion


def _cycle(ctx, lion, f0, f1, gait):
    g = GAITS[gait]
    period = g["period"] * ctx.fps
    step = max(2, round(period / 6))
    swing, pitch = math.radians(g["swing"]), math.radians(g["pitch"])
    low = -0.12 if gait == "prowl" else 0.0
    f = f0
    while f <= f1 + step:
        t = (f - f0) / period
        for (name, _, _), phase in zip(LEGS, g["phases"], strict=False):
            key(lion.legs[name], "rotation_euler", f, (swing * math.sin(math.tau * (t - phase)), 0.0, 0.0))
        key(lion.body, "location", f, (0.0, 0.0, 0.95 + low + g["bob"] * math.sin(math.tau * 2 * t)))
        key(lion.body, "rotation_euler", f, (pitch * math.sin(math.tau * t), 0.0, 0.0))
        key(lion.head, "rotation_euler", f, (math.radians(-10 if gait == "prowl" else -3) + math.radians(3) * math.sin(math.tau * 2 * t + 1.0), 0.0, 0.0))
        key(lion.tail, "rotation_euler", f, (math.radians(-35 if gait != "run" else -10), 0.0, math.radians(14) * math.sin(math.tau * 0.5 * t)))
        f += step
    for part in (*lion.legs.values(), lion.body, lion.head, lion.tail):
        set_interp(part, "SINE", "EASE_IN_OUT")


def _idle(ctx, lion, seed):
    f = 1
    while f <= ctx.frames:
        t = (f - 1) / ctx.fps
        key(lion.body, "location", f, (0.0, 0.0, 0.95 + 0.01 * math.sin(math.tau * t / 2.4 + seed)))
        key(lion.head, "rotation_euler", f, (0.0, 0.0, math.radians(25) * math.sin(math.tau * t / 7.0 + seed)))
        key(lion.tail, "rotation_euler", f, (math.radians(-35), 0.0, math.radians(20) * math.sin(math.tau * t / 3.0 + seed)))
        f += 12
    for part in (lion.body, lion.head, lion.tail):
        set_interp(part, "SINE", "EASE_IN_OUT")


def roar(ctx, lion, start, hold=1.0):
    """Head up, jaw open, hold, close (the roar sound is a separate sfx cue)."""
    f0 = ctx.frame(start)
    up, hold_end, close = f0 + round(0.25 * ctx.fps), f0 + round((0.25 + hold) * ctx.fps), f0 + round((0.75 + hold) * ctx.fps)
    for frame, head_x, jaw_x in ((f0, 0.0, 0.0), (up, 24.0, -38.0), (hold_end, 20.0, -34.0), (close, 0.0, 0.0)):
        key(lion.head, "rotation_euler", frame, (math.radians(head_x), 0.0, 0.0))
        key(lion.jaw, "rotation_euler", frame, (math.radians(jaw_x), 0.0, 0.0))
    add_noise(lion.head, "rotation_euler", 0.03, up, hold_end, scale=1.5)
    set_interp(lion.head, "QUAD", "EASE_OUT")
    set_interp(lion.jaw, "QUAD", "EASE_OUT")


def lie(ctx, lion):
    """Resting pose: belly down, front legs forward, back legs tucked."""
    key(lion.body, "location", 1, (0.0, 0.0, 0.42))
    for name, leg in lion.legs.items():
        key(leg, "rotation_euler", 1, (math.radians(84 if name.startswith("f") else -84), 0.0, 0.0))
    key(lion.tail, "rotation_euler", 1, (math.radians(-80), 0.0, math.radians(30)))


def move_along(ctx, lion, path, f0, f1, gait, face_at=None):
    points = [Vector((float(p[0]), float(p[1]), float(p[2]) if len(p) > 2 else lion.root.location.z)) for p in path]
    total = polyline_length(points)
    previous = lion.root.rotation_euler.z
    travelled = 0.0
    key(lion.root, "location", max(1, f0 - 1), points[0])
    for i, point in enumerate(points):
        if i:
            travelled += (points[i] - points[i - 1]).length
        frame = f0 + round((f1 - f0) * (travelled / total if total else 0.0))
        key(lion.root, "location", frame, point)
        if i < len(points) - 1:
            previous = unwrap(previous, heading(point, points[i + 1]))
            key(lion.root, "rotation_euler", max(1, frame - 3), (0.0, 0.0, lion.root.rotation_euler.z))
            key(lion.root, "rotation_euler", frame + 4, (0.0, 0.0, previous))
    if face_at:
        facing = unwrap(previous, heading(points[-1], (float(face_at[0]), float(face_at[1]), 0.0)))
        key(lion.root, "rotation_euler", f1 + 8, (0.0, 0.0, facing))
    set_interp(lion.root, "LINEAR", path="location")
    set_interp(lion.root, "SINE", "EASE_IN_OUT", path="rotation_euler")
    _cycle(ctx, lion, f0, f1, gait)


def animate(ctx, lion, spec):
    action = spec.get("action", "idle")
    f0 = ctx.frame(spec.get("start", 0.0))
    seed = sum(map(ord, lion.id)) % 97 * 0.13
    if action in GAITS:
        speed = float(spec.get("speed", GAITS[action]["speed"]))
        loc = lion.root.location
        path = spec.get("path") or [[loc.x, loc.y], [loc.x, loc.y + speed * ctx.duration]]
        f1 = ctx.frame(spec["end"]) if "end" in spec else min(ctx.frames, f0 + max(2, round(polyline_length(path) / speed * ctx.fps)))
        move_along(ctx, lion, path, f0, f1, action, spec.get("face_at"))
    elif action == "lie":
        lie(ctx, lion)
    else:
        _idle(ctx, lion, seed)
        if spec.get("face_at"):
            lion.root.rotation_euler.z = heading(lion.root.location, spec["face_at"])
    if action == "roar" or spec.get("roar_at") is not None:
        roar(ctx, lion, float(spec.get("roar_at", spec.get("start", 0.0))), float(spec.get("hold", 1.0)))


def spawn(ctx, spec):
    """One lion, or a pride (spec has `count` and `area`) heading `to` a point or scattering."""
    if "count" not in spec:
        lion = build(ctx, spec)
        animate(ctx, lion, spec)
        return [lion]
    rng = ctx.rng
    x, y, w, d = spec["area"]
    lions = []
    for i in range(int(spec["count"])):
        sub = {k: v for k, v in spec.items() if k not in ("count", "area", "to", "jitter", "stagger", "radius")}
        sub["id"] = f"{spec['id']}_{i:02d}"
        px, py = x + rng.uniform(-w / 2, w / 2), y + rng.uniform(-d / 2, d / 2)
        sub["at"] = (px, py, float(spec.get("z", 0.0)))
        sub["start"] = float(spec.get("start", 0.0)) + rng.uniform(0.0, float(spec.get("stagger", 0.8)))
        to = spec.get("to")
        action = spec.get("action", "walk")
        if action in GAITS and to:
            jitter = float(spec.get("jitter", 4.0))
            sub["path"] = [[px, py], [to[0] + (px - x) + rng.uniform(-jitter, jitter), to[1] + (py - y) + rng.uniform(-jitter, jitter)]]
        elif to:
            sub["face_at"] = [to[0] + rng.uniform(-3, 3), to[1] + rng.uniform(-3, 3)]
        if action in GAITS and not to:
            sub["face"] = float(spec.get("face", 0.0)) + rng.uniform(-8, 8)
        if spec.get("roar_chance") and rng.random() < float(spec["roar_chance"]):
            sub["roar_at"] = float(spec.get("start", 0.0)) + rng.uniform(0.5, 3.0)
        lions.extend(spawn(ctx, sub))
    return lions


def _silhouette(ox, oy, oz, male, s):
    boxes = [((ox, oy, oz + 0.95 * s), (0.55 * s, 1.5 * s, 0.55 * s), 0), ((ox, oy + 0.95 * s, oz + 1.2 * s), (0.42 * s, 0.5 * s, 0.42 * s), 0)]
    boxes += [((ox + lx * s, oy + ly * s, oz + 0.38 * s), (0.17 * s, 0.2 * s, 0.76 * s), 0) for _, lx, ly in LEGS]
    boxes.append(((ox, oy - 1.0 * s, oz + 0.85 * s), (0.06 * s, 0.6 * s, 0.06 * s), 0))
    if male:
        boxes.append(((ox, oy + 0.75 * s, oz + 1.15 * s), (0.78 * s, 0.42 * s, 0.82 * s), 1))
    return boxes


def horde(ctx, name, count, centre, extent=(160.0, 80.0), path=None, start=0.0, end=None, groups=8, bob=0.06, z=0.0, facing=None, speed=None, eyes=False):
    """Thousands of lions as a few merged meshes that sweep along `path` (local +Y faces the travel).
    eyes=True adds eye-shine so the horde reads at night."""
    rng = ctx.rng
    fur, mane = ctx.mat("lion", roughness=0.9), ctx.mat("mane", roughness=0.95)
    shine = ctx.palette.emissive(f"{name} eyeshine", (1.0, 0.7, 0.25), 60.0)
    cx, cy = centre[0], centre[1]
    root = empty(ctx, name, (cx, cy, z))
    if path and len(path) > 1:
        root.rotation_euler.z = heading(path[0], path[1])
    elif facing is not None:
        root.rotation_euler.z = math.radians(facing)
    w, d = extent
    per = max(1, count // groups)
    for g in range(groups):
        gx, gy = rng.uniform(-w * 0.35, w * 0.35), rng.uniform(-d * 0.35, d * 0.35)
        boxes = []
        for _ in range(per):
            lx, ly, ls = gx + rng.gauss(0.0, w * 0.08), gy + rng.gauss(0.0, d * 0.08), rng.uniform(0.85, 1.1)  # round packs, not rectangles
            boxes += _silhouette(lx, ly, 0.0, rng.random() < 0.4, ls)
            if eyes:
                boxes += [((lx + side * 0.3 * ls, ly + 1.22 * ls, 1.25 * ls), (0.32 * ls, 0.1, 0.24 * ls), 2) for side in (-1, 1)]
        group = multi_box(ctx, f"{name}.g{g}", boxes, [fur, mane, shine])
        parent(group, root)
        key(group, "location", 1, (0.0, 0.0, 0.0))
        add_noise(group, "location", 1.5, 1, ctx.frames, scale=12.0, phase=g * 2.1)
        ctx.tag("horde", group)
        ctx.tag("lion", group)
    if path:
        points = [Vector((p[0], p[1], z)) for p in path]
        f0 = ctx.frame(start)
        total = polyline_length(points)
        f1 = f0 + round(total / speed * ctx.fps) if speed else (ctx.frame(end) if end is not None else ctx.frames)
        travelled = 0.0
        for i, point in enumerate(points):
            if i:
                travelled += (points[i] - points[i - 1]).length
            key(root, "location", f0 + round((f1 - f0) * (travelled / total if total else 0.0)), point)
        set_interp(root, "LINEAR", path="location")
    ctx.objects[name] = root
    return root


def resting(ctx, name, points, scale=1.0):
    """Static lying lions (merged) at world points, e.g. on casino rooftops (tag: lion)."""
    rng = ctx.rng
    fur, mane, light = ctx.mat("lion", roughness=0.9), ctx.mat("mane", roughness=0.95), ctx.mat("lion_light", roughness=0.9)
    boxes = []
    for x, y, z in points:
        s = scale * rng.uniform(0.9, 1.1)
        a = rng.uniform(0, math.tau)
        ca, sa = math.cos(a), math.sin(a)

        def at(px, py, pz, size, index, x=x, y=y, z=z, s=s, ca=ca, sa=sa):
            # axis-aligned boxes cannot rotate, so lions face one of four directions
            if abs(ca) >= abs(sa):
                return ((x + px * s * (1 if ca > 0 else -1), y + py * s * (1 if ca > 0 else -1), z + pz * s), (size[0] * s, size[1] * s, size[2] * s), index)
            return ((x + py * s * (1 if sa > 0 else -1), y + px * s * (1 if sa > 0 else -1), z + pz * s), (size[1] * s, size[0] * s, size[2] * s), index)

        boxes += [at(0, 0, 0.3, (0.55, 1.5, 0.5), 0), at(0, 0.95, 0.62, (0.42, 0.5, 0.42), 0), at(0, 1.2, 0.56, (0.24, 0.26, 0.2), 2)]
        boxes += [at(sx * 0.19, 0.95, 0.07, (0.17, 0.6, 0.12), 2) for sx in (-1, 1)]
        boxes.append(at(0.35, -0.9, 0.06, (0.6, 0.07, 0.07), 0))
        if rng.random() < 0.45:
            boxes.append(at(0, 0.8, 0.58, (0.78, 0.42, 0.82), 1))
    obj = multi_box(ctx, name, boxes, [fur, mane, light])
    ctx.tag("lion", obj)
    return obj


def eyes(ctx, name, points, strength=9.0, size=0.07):
    """Pairs of eye-shine dots for night shots (tag: eyes). Distant eyes need an exaggerated `size`
    to survive anti-aliasing; the pairs keep their spacing in proportion."""
    glow = ctx.palette.emissive(f"{name} eyeshine", (1.0, 0.7, 0.25), strength)
    boxes = []
    for x, y, z in points:
        for side in (-1, 1):
            boxes.append(((x + side * size * 1.4, y, z), (size, size, size * 0.7), 0))
    obj = multi_box(ctx, name, boxes, [glow])
    ctx.tag("eyes", obj)
    return obj
