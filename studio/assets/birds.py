"""Low-poly seagulls: flapping flocks for close shots, merged 'dot' swarms for distant masses,
perched roosts for rooftops and bridges, and droppings. All birds are tagged 'bird'."""

from __future__ import annotations

import math

from mathutils import Vector

from studio.blender.primitives import add_noise, box, empty, key, mesh_from_pydata, multi_box, parent, set_interp
from studio.core.motion import heading, polyline_length, unwrap


def _materials(ctx):
    return ctx.mat("white", roughness=0.8), ctx.mat("gull_grey", roughness=0.8), ctx.mat("orange", roughness=0.6)


def gull(ctx, name, loc, scale=1.0, facing=0.0, flap=True, period=0.36, amplitude=42.0, phase=0.0, soar=False):
    """One rigged gull: body, head, beak, tail and two wings pivoting at the shoulder (tags: bird)."""
    white, grey, orange = _materials(ctx)
    root = empty(ctx, name, loc, (0.0, 0.0, facing))
    root.scale = (scale, scale, scale)
    body = multi_box(ctx, f"{name}.body", [((0, 0, 0), (0.16, 0.5, 0.14), 0), ((0, 0.31, 0.06), (0.12, 0.15, 0.12), 0), ((0, -0.32, 0.03), (0.14, 0.18, 0.03), 1), ((0, 0.43, 0.05), (0.04, 0.12, 0.04), 2)], [white, grey, orange], bevel=0.03)
    parent(body, root)
    wings = []
    for side, sign in (("l", 1), ("r", -1)):
        wing = multi_box(ctx, f"{name}.wing_{side}", [((sign * 0.3, 0.0, 0.0), (0.6, 0.22, 0.02), 0), ((sign * 0.58, -0.03, 0.0), (0.16, 0.14, 0.02), 1)], [white, grey])
        wing.location = (sign * 0.08, 0.02, 0.07)
        parent(wing, root)
        wings.append((wing, sign))
    if flap:
        frames = ctx.frames
        step = max(2, round(period * ctx.fps / 4))
        amp = math.radians(amplitude if not soar else amplitude * 0.25)
        f = 1
        while f <= frames + step:
            t = (f - 1) / ctx.fps
            angle = amp * math.sin(math.tau * t / period + phase)
            for wing, sign in wings:
                key(wing, "rotation_euler", f, (0.0, -sign * angle, 0.0))
            f += step
        for wing, _ in wings:
            set_interp(wing, "SINE", "EASE_IN_OUT")
    else:
        for wing, sign in wings:
            wing.rotation_euler = (0.0, -sign * math.radians(70), 0.0)
            wing.scale = (0.55, 1.0, 1.0)
    ctx.tag("bird", root)
    return root


def flock(ctx, name, count, centre, extent=(30.0, 30.0, 12.0), path=None, start=0.0, end=None, speed=14.0, scale=1.0, wander=1.2, soar=False):
    """Rigged birds spread inside an ellipsoid, carried along `path` by a root empty, each wandering."""
    rng = ctx.rng
    root = empty(ctx, name, centre)
    ex, ey, ez = extent
    for i in range(count):
        u, v, w = rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)
        offset = Vector((u * ex, v * ey, w * ez))
        bird = gull(ctx, f"{name}.{i}", offset, scale * rng.uniform(0.8, 1.25), rng.uniform(-0.25, 0.25), True, rng.uniform(0.3, 0.46), 40.0, rng.uniform(0, math.tau), soar)
        parent(bird, root)
        if wander:
            key(bird, "location", 1, offset)
            add_noise(bird, "location", wander, 1, ctx.frames, scale=6.0, phase=i * 1.7)
    if path:
        _carry(ctx, root, path, start, end, speed)
    ctx.objects[name] = root
    return root


def _carry(ctx, root, path, start, end, speed):
    points = [Vector((p[0], p[1], p[2] if len(p) > 2 else root.location.z)) for p in path]
    total = polyline_length(points)
    f0 = ctx.frame(start)
    f1 = ctx.frame(end) if end is not None else min(ctx.frames, f0 + max(2, round(total / max(0.1, speed) * ctx.fps)))
    previous = root.rotation_euler.z
    travelled = 0.0
    for i, point in enumerate(points):
        if i:
            travelled += (points[i] - points[i - 1]).length
        frame = f0 + round((f1 - f0) * (travelled / total if total else 0.0))
        key(root, "location", frame, point)
        if i < len(points) - 1:
            previous = unwrap(previous, heading(point, points[i + 1]))
            key(root, "rotation_euler", frame, (0.0, 0.0, previous))
    set_interp(root, "LINEAR", path="location")
    set_interp(root, "SINE", "EASE_IN_OUT", path="rotation_euler")


def swarm(ctx, name, count, centre, extent=(200.0, 200.0, 60.0), path=None, start=0.0, end=None, speed=20.0, size=1.1, groups=8):
    """Thousands of distant gulls as a few merged 'V' meshes that drift and jitter independently."""
    rng = ctx.rng
    white = ctx.mat("white", roughness=0.9)
    root = empty(ctx, name, centre)
    ex, ey, ez = extent
    per_group = max(1, count // groups)
    for g in range(groups):
        verts, faces = [], []
        gx, gy, gz = rng.uniform(-ex * 0.6, ex * 0.6), rng.uniform(-ey * 0.6, ey * 0.6), rng.uniform(-ez * 0.6, ez * 0.6)
        for i in range(per_group):
            x = gx + rng.uniform(-ex * 0.5, ex * 0.5)
            y = gy + rng.uniform(-ey * 0.5, ey * 0.5)
            z = gz + rng.uniform(-ez * 0.5, ez * 0.5)
            s = size * rng.uniform(0.7, 1.4)
            base = len(verts)
            verts += [(x - s, y - s * 0.25, z + s * 0.15), (x, y + s * 0.35, z), (x + s, y - s * 0.25, z + s * 0.15), (x, y - s * 0.15, z)]
            faces += [(base, base + 1, base + 3), (base + 1, base + 2, base + 3)]
        group = mesh_from_pydata(ctx, f"{name}.g{g}", verts, faces, [white])
        parent(group, root)
        key(group, "location", 1, (0.0, 0.0, 0.0))
        add_noise(group, "location", 4.0, 1, ctx.frames, scale=9.0, phase=g * 2.3)
        group.data.materials[0].use_backface_culling = False
        ctx.tag("swarm", group)
    if path:
        _carry(ctx, root, path, start, end, speed)
    ctx.objects[name] = root
    return root


def roost(ctx, name, points, scale=1.0, jitter=0.3):
    """Perched gulls (folded wings) at the given world points, merged into one mesh."""
    rng = ctx.rng
    white = ctx.mat("white", roughness=0.8)
    grey = ctx.mat("gull_grey", roughness=0.8)
    orange = ctx.mat("orange", roughness=0.6)
    boxes = []
    for x, y, z in points:
        s = scale * rng.uniform(0.8, 1.2)
        jx, jy = rng.uniform(-jitter, jitter), rng.uniform(-jitter, jitter)
        boxes.append(((x + jx, y + jy, z + 0.1 * s), (0.18 * s, 0.5 * s, 0.16 * s), 0))
        boxes.append(((x + jx, y + jy, z + 0.17 * s), (0.2 * s, 0.34 * s, 0.05 * s), 1))
        boxes.append(((x + jx, y + jy + 0.3 * s, z + 0.19 * s), (0.12 * s, 0.14 * s, 0.12 * s), 0))
        boxes.append(((x + jx, y + jy + 0.42 * s, z + 0.17 * s), (0.04 * s, 0.1 * s, 0.04 * s), 2))
    obj = multi_box(ctx, name, boxes, [white, grey, orange])
    ctx.tag("bird", obj)
    ctx.tag("roost", obj)
    return obj


def roost_area(ctx, name, centre, size, count, z, scale=1.0):
    rng = ctx.rng
    cx, cy = centre
    w, d = size
    return roost(ctx, name, [(cx + rng.uniform(-w / 2, w / 2), cy + rng.uniform(-d / 2, d / 2), z) for _ in range(count)], scale)


def roost_line(ctx, name, start, end, count, scale=1.0):
    sx, sy, sz = start
    ex, ey, ez = end
    return roost(ctx, name, [(sx + (ex - sx) * i / max(1, count - 1), sy + (ey - sy) * i / max(1, count - 1), sz + (ez - sz) * i / max(1, count - 1)) for i in range(count)], scale, jitter=0.1)


def splats(ctx, name, points, scale=1.0):
    """Droppings: flat irregular white patches at the given points (tag: splat)."""
    rng = ctx.rng
    white = ctx.mat("white", roughness=0.95)
    verts, faces = [], []
    for x, y, z in points:
        r = scale * rng.uniform(0.25, 0.7)
        base = len(verts)
        sides = rng.randint(6, 9)
        verts.append((x, y, z + 0.01))
        for k in range(sides):
            angle = math.tau * k / sides
            rr = r * rng.uniform(0.6, 1.3)
            verts.append((x + rr * math.cos(angle), y + rr * math.sin(angle), z + 0.01))
        for k in range(sides):
            faces.append((base, base + 1 + k, base + 1 + (k + 1) % sides))
    obj = mesh_from_pydata(ctx, name, verts, faces, [white])
    ctx.tag("splat", obj)
    return obj


def splat_area(ctx, name, centre, size, count, z, scale=1.0):
    rng = ctx.rng
    cx, cy = centre
    w, d = size
    return splats(ctx, name, [(cx + rng.uniform(-w / 2, w / 2), cy + rng.uniform(-d / 2, d / 2), z) for _ in range(count)], scale)


def dive(ctx, bird, target, start, duration=0.9):
    """Send a rigged gull (or flock root) down to `target` and back up: a strafing dive."""
    origin = bird.location.copy()
    f0 = ctx.frame(start)
    f1 = ctx.frame(start + duration)
    key(bird, "location", f0, origin)
    key(bird, "location", (f0 + f1) // 2, Vector(target))
    key(bird, "location", f1, origin + Vector((0.0, 6.0, 0.0)))
    set_interp(bird, "QUAD", "EASE_IN_OUT", path="location")


def nest(ctx, name, loc, eggs=3, bird=True):
    x, y, z = loc
    rng = ctx.rng
    ring = multi_box(ctx, f"{name}.ring", [((0.45 * math.cos(a), 0.45 * math.sin(a), 0.06), (0.3, 0.14, 0.12), 0) for a in [math.tau * k / 10 for k in range(10)]], [ctx.mat("trunk", roughness=0.95)], (x, y, z), (0, 0, rng.uniform(0, 1)))
    for i in range(eggs):
        box(ctx, f"{name}.egg{i}", (0.12, 0.16, 0.12), (x + rng.uniform(-0.18, 0.18), y + rng.uniform(-0.18, 0.18), z + 0.1), ctx.mat("cream", roughness=0.6), bevel=0.04)
    if bird:
        roost(ctx, f"{name}.sitter", [(x, y - 0.1, z + 0.08)], 1.1, jitter=0.0)
    return ring
