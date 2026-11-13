"""Trees, palms, bushes and crop rows in the flat-shaded low-poly style."""

from __future__ import annotations

import math

from studio.blender.primitives import box, cone, cylinder, ico, multi_box


def tree(ctx, name, loc, kind="round", scale=1.0, dry=False):
    x, y, z = loc
    rng = ctx.rng
    leaf = ctx.mat("grass_dry" if dry else rng.choice(("leaf", "leaf_dark", "leaf")))
    trunk = ctx.mat("trunk")
    s = scale * rng.uniform(0.85, 1.2)
    if kind == "conifer":
        cylinder(ctx, f"{name}.trunk", 0.22 * s, 1.2 * s, (x, y, z), trunk, segments=7, anchor="base")
        for i, (r, h, zz) in enumerate(((2.2, 2.6, 1.0), (1.7, 2.3, 2.6), (1.2, 2.0, 4.1))):
            cone(ctx, f"{name}.tier{i}", r * s, h * s, (x, y, z + zz * s), leaf, segments=8)
        return
    if kind == "palm":
        palm(ctx, name, loc, s)
        return
    if kind == "dead":
        cylinder(ctx, f"{name}.trunk", 0.2 * s, 3.4 * s, (x, y, z), trunk, segments=6, anchor="base")
        for i in range(3):
            angle = rng.uniform(0, math.tau)
            box(ctx, f"{name}.branch{i}", (0.14 * s, 0.14 * s, 1.8 * s), (x, y, z + (2.0 + 0.5 * i) * s), trunk, rot=(math.radians(55), 0, angle), anchor="base")
        return
    cylinder(ctx, f"{name}.trunk", 0.2 * s, 1.5 * s, (x, y, z), trunk, segments=7, anchor="base")
    ico(ctx, f"{name}.crown", 1.6 * s, (x, y, z + 2.7 * s), leaf, subdiv=1, scale=(1.0, 1.0, 1.15))
    if rng.random() < 0.5:
        ico(ctx, f"{name}.crown2", 1.0 * s, (x + 0.7 * s, y + 0.3 * s, z + 2.2 * s), leaf, subdiv=1)


def palm(ctx, name, loc, scale=1.0):
    x, y, z = loc
    rng = ctx.rng
    lean = rng.uniform(-0.12, 0.12)
    trunk = cylinder(ctx, f"{name}.trunk", 0.18 * scale, 5.5 * scale, (x, y, z), ctx.mat("trunk"), segments=7, anchor="base", radius2=0.12 * scale)
    trunk.rotation_euler = (lean, rng.uniform(-0.12, 0.12), 0)
    top_x = x - math.sin(lean) * 5.5 * scale * 0.0
    for i in range(7):
        angle = i * math.tau / 7 + rng.uniform(-0.2, 0.2)
        frond = box(ctx, f"{name}.frond{i}", (0.45 * scale, 2.6 * scale, 0.06), (top_x, y, z + 5.5 * scale), ctx.mat("leaf"), bevel=0.02, anchor="center")
        frond.rotation_euler = (math.radians(-28), 0, angle)
        frond.location = (x + math.sin(angle) * -1.1 * scale, y + math.cos(angle) * 1.1 * scale, z + 5.3 * scale)


def bush(ctx, name, loc, scale=1.0, dry=False):
    x, y, z = loc
    ico(ctx, name, 0.7 * scale, (x, y, z + 0.5 * scale), ctx.mat("grass_dry" if dry else "leaf_dark"), subdiv=1, scale=(1.3, 1.0, 0.8))


def crop_rows(ctx, name, loc, size=(60.0, 40.0), spacing=1.6, health=1.0, circle=False):
    """One merged mesh of plant clumps in rows. health 1.0 = green and tall, 0.0 = dry and wilted."""
    x0, y0, z0 = loc
    w, d = size
    rng = ctx.rng
    boxes = []
    colour = ctx.mat("crop") if health > 0.5 else ctx.mat("crop_dry")
    soil = ctx.mat("soil")
    rows = int(w / spacing)
    for r in range(rows):
        rx = -w / 2 + spacing * (r + 0.5)
        boxes.append(((rx, 0.0, 0.06), (spacing * 0.5, d, 0.12), 1))
        n = int(d / 0.9)
        for i in range(n):
            ry = -d / 2 + 0.9 * (i + 0.5)
            if circle and math.hypot(rx, ry) > min(w, d) / 2:
                continue
            h = (0.5 + 0.5 * health) * rng.uniform(0.55, 0.85)
            boxes.append(((rx + rng.uniform(-0.1, 0.1), ry, 0.1 + h / 2), (0.45, 0.5, h), 0))
    obj = multi_box(ctx, name, boxes, [colour, soil], (x0, y0, z0))
    ctx.tag("crops", obj)
    return obj


def scatter_trees(ctx, name, centre, radius, count, kinds=("round", "round", "conifer"), avoid=(), dry=False):
    rng = ctx.rng
    cx, cy, cz = centre
    placed = 0
    attempts = 0
    while placed < count and attempts < count * 10:
        attempts += 1
        x = cx + rng.uniform(-radius, radius)
        y = cy + rng.uniform(-radius, radius)
        if any(ax0 <= x <= ax1 and ay0 <= y <= ay1 for ax0, ay0, ax1, ay1 in avoid):
            continue
        tree(ctx, f"{name}.{placed}", (x, y, cz), rng.choice(kinds), dry=dry)
        placed += 1
