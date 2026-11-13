"""Procedural low-poly buildings and infrastructure, one mesh per building (windows included)."""

from __future__ import annotations

import math
import random

from studio.assets import water
from studio.assets.props import cross
from studio.blender.primitives import box, cone, cylinder, ico, mesh_from_pydata, multi_box, parent


def building(ctx, name, loc, size, wall="concrete", roof="flat", rot=0.0, seed=0, glass="glass", window=(1.2, 1.4), floor_height=3.2, door=True, trim="stone", units=True, tank=False):
    """Box building with window grid, parapet or pitched/dome roof. Returns the body object."""
    w, d, h = size
    rng = random.Random(seed)
    mats = [ctx.mat(wall), ctx.palette.glass(f"{name} glass", glass), ctx.mat(trim), ctx.mat("roof_dark")]
    boxes = [((0, 0, h / 2), (w, d, h), 0)]
    ww, wh = window
    floors = max(1, int(h / floor_height))
    for k in range(floors):
        z = (k + 0.55) * (h / floors)
        for axis, extent, other in (("x", w, d), ("y", d, w)):
            n = max(1, int((extent - 1.2) / (ww + 1.0)))
            for i in range(n):
                offset = -extent / 2 + (extent / n) * (i + 0.5)
                for sign in (-1, 1):
                    if k == 0 and door and axis == "y" and sign == -1 and i == n // 2:
                        boxes.append(((offset, sign * (other / 2), 1.2), (1.4, 0.16, 2.4), 3))
                        continue
                    if rng.random() < 0.08:
                        continue
                    if axis == "x":
                        boxes.append(((offset, sign * (other / 2), z), (ww, 0.14, wh), 1))
                    else:
                        boxes.append(((sign * (other / 2), offset, z), (0.14, ww, wh), 1))
    if roof == "flat":
        for cx, cy, sx, sy in ((0, d / 2, w, 0.3), (0, -d / 2, w, 0.3), (w / 2, 0, 0.3, d), (-w / 2, 0, 0.3, d)):
            boxes.append(((cx, cy, h + 0.35), (sx + 0.3, sy + 0.3, 0.7), 2))
        if units:
            for _ in range(rng.randint(1, 3)):
                boxes.append(((rng.uniform(-w * 0.3, w * 0.3), rng.uniform(-d * 0.3, d * 0.3), h + 0.5), (rng.uniform(1.2, 2.4), rng.uniform(1.2, 2.0), 1.0), 2))
    body = multi_box(ctx, name, boxes, mats, loc, (0, 0, rot), bevel=min(0.12, w * 0.02))
    if roof == "pitched":
        ridge = h + min(w, d) * 0.35
        verts = [(-w / 2 - 0.5, -d / 2 - 0.5, h), (w / 2 + 0.5, -d / 2 - 0.5, h), (w / 2 + 0.5, d / 2 + 0.5, h), (-w / 2 - 0.5, d / 2 + 0.5, h), (-w / 2 - 0.5, 0, ridge), (w / 2 + 0.5, 0, ridge)]
        faces = [(0, 1, 5, 4), (2, 3, 4, 5), (1, 2, 5), (3, 0, 4), (0, 3, 2, 1)]
        roof_obj = mesh_from_pydata(ctx, f"{name}.roof", verts, faces, [ctx.mat(rng.choice(("terracotta", "roof_dark", "terracotta")))], bevel=0.05)
        parent(roof_obj, body)
    elif roof == "dome":
        dome = ico(ctx, f"{name}.dome", min(w, d) * 0.45, (0, 0, h), ctx.mat("teal"), subdiv=2)
        parent(dome, body)
    if tank:
        tank_obj = water.tank(ctx, f"{name}.tank", (loc[0] + w * 0.25, loc[1] - d * 0.2, loc[2] + h), radius=1.1, height=1.5)
        ctx.tag("roof_tank", tank_obj)
    ctx.tag("building", body)
    return body


def house(ctx, name, loc, seed=0, rot=0.0, size=None):
    rng = random.Random(seed)
    w, d, h = size or (rng.uniform(7, 10), rng.uniform(6, 8), rng.uniform(3.2, 3.6) * rng.choice((1, 1, 2)))
    wall = rng.choice(("white", "cream", "plaster", "sand"))
    body = building(ctx, name, loc, (w, d, h), wall, "pitched", rot, seed, window=(1.1, 1.2), floor_height=3.2, units=False)
    chimney = box(ctx, f"{name}.chimney", (0.7, 0.7, 1.6), (w * 0.3, d * 0.2, h + 0.6), ctx.mat("stone"), anchor="base")
    parent(chimney, body)
    return body


def tower(ctx, name, loc, seed=0, height=None, rot=0.0):
    rng = random.Random(seed)
    h = height or rng.uniform(24, 60)
    w, d = rng.uniform(12, 18), rng.uniform(12, 18)
    wall = rng.choice(("concrete", "plaster", "white", "stone"))
    return building(ctx, name, loc, (w, d, h), wall, "flat", rot, seed, window=(1.6, 1.8), floor_height=3.4, tank=rng.random() < 0.4)


def apartment(ctx, name, loc, seed=0, rot=0.0):
    rng = random.Random(seed)
    return building(ctx, name, loc, (rng.uniform(12, 22), rng.uniform(9, 14), rng.uniform(9, 18)), rng.choice(("cream", "plaster", "white", "sand")), "flat", rot, seed, tank=rng.random() < 0.5)


def hospital(ctx, name, loc, rot=0.0):
    x, y, z = loc
    body = building(ctx, name, loc, (56, 26, 18), "white", "flat", rot, 7, window=(1.8, 1.6), floor_height=3.6, trim="teal")
    wing = building(ctx, f"{name}.wing", (x + 30, y + 8, z), (22, 42, 11), "white", "flat", rot, 8, window=(1.6, 1.6), trim="teal", door=False)
    canopy = box(ctx, f"{name}.canopy", (14, 8, 0.6), (0, -17, 4.5), ctx.mat("teal"), bevel=0.05, anchor="base")
    parent(canopy, body)
    for dx in (-5, 5):
        post = cylinder(ctx, f"{name}.post", 0.3, 4.5, (dx, -20, 0), ctx.mat("steel"), segments=8, anchor="base")
        parent(post, body)
    emblem = cross(ctx, f"{name}.cross", (0, -13.2, 14), 5.0)
    parent(emblem, body)
    pad = cylinder(ctx, f"{name}.helipad", 7, 0.3, (12, 4, 18.7), ctx.mat("roof_dark"), segments=24, anchor="base")
    parent(pad, body)
    ring = cylinder(ctx, f"{name}.helipad_ring", 6.2, 0.1, (12, 4, 19.0), ctx.mat("white"), segments=24, anchor="base", radius2=6.2)
    parent(ring, body)
    ctx.anchor(f"{name}.entrance", (x, y - 20, z))
    return body, wing


def supermarket(ctx, name, loc, rot=0.0):
    x, y, z = loc
    body = building(ctx, name, loc, (46, 32, 7.5), "plaster", "flat", rot, 11, window=(0.1, 0.1), door=False, units=False)
    front = box(ctx, f"{name}.glass", (36, 0.3, 4.0), (0, -16.1, 0.4), ctx.palette.glass(f"{name} front"), anchor="base")
    parent(front, body)
    sign = box(ctx, f"{name}.sign", (20, 0.6, 2.2), (0, -16.3, 5.0), ctx.mat("teal"), bevel=0.05, anchor="base")
    parent(sign, body)
    ctx.anchor(f"{name}.entrance", (x, y - 17, z))
    return body


def warehouse(ctx, name, loc, size=(40, 24, 9), rot=0.0, colour="steel"):
    w, d, h = size
    body = building(ctx, name, loc, size, colour, "flat", rot, 5, window=(0.1, 0.1), door=False, units=False, trim="dark_steel")
    ridge = h + 2.5
    verts = [(-w / 2, -d / 2, h), (w / 2, -d / 2, h), (w / 2, d / 2, h), (-w / 2, d / 2, h), (-w / 2, 0, ridge), (w / 2, 0, ridge)]
    faces = [(0, 1, 5, 4), (2, 3, 4, 5), (1, 2, 5), (3, 0, 4)]
    roof_obj = mesh_from_pydata(ctx, f"{name}.roof", verts, faces, [ctx.mat("dark_steel")])
    parent(roof_obj, body)
    return body


def barn(ctx, name, loc, rot=0.0):
    body = building(ctx, name, loc, (16, 24, 6), "red", "pitched", rot, 3, window=(0.1, 0.1), door=False, units=False, trim="white")
    return body


def silo(ctx, name, loc, radius=3.0, height=14.0):
    x, y, z = loc
    cylinder(ctx, name, radius, height, loc, ctx.mat("steel", roughness=0.5), segments=16, anchor="base", bevel=0.05)
    cone(ctx, f"{name}.top", radius + 0.2, 2.2, (x, y, z + height), ctx.mat("dark_steel"), segments=16, tip=0.3)


def clarifier(ctx, name, loc, radius=9.0, level=0.9):
    """Circular water-treatment tank with a rotating bridge; the water disc is tagged."""
    x, y, z = loc
    cylinder(ctx, f"{name}.wall", radius, 3.0, loc, ctx.mat("concrete"), segments=32, anchor="base", bevel=0.08)
    liquid = cylinder(ctx, f"{name}.water", radius - 0.4, 0.1, (x, y, z + 3.0 * level), ctx.palette.water(f"{name} water", "lake", scale=1.5), segments=32, anchor="base")
    ctx.tag("water", liquid)
    ctx.tag("treatment_water", liquid)
    bridge = box(ctx, f"{name}.bridge", (radius * 2.1, 1.2, 0.5), (x, y, z + 3.3), ctx.mat("steel"), bevel=0.04, anchor="base")
    box(ctx, f"{name}.hub", (1.4, 1.4, 1.4), (x, y, z + 3.2), ctx.mat("dark_steel"), bevel=0.05, anchor="base")
    ctx.objects[f"{name}.bridge"] = bridge
    return liquid


def cooling_tower(ctx, name, loc, radius=14.0, height=48.0, steam=True):
    x, y, z = loc
    cylinder(ctx, name, radius, height, loc, ctx.mat("concrete", roughness=0.8), segments=24, anchor="base", radius2=radius * 0.62)
    cylinder(ctx, f"{name}.lip", radius * 0.68, 1.5, (x, y, z + height), ctx.mat("stone"), segments=24, anchor="base", radius2=radius * 0.66)
    if steam:
        rng = ctx.rng
        for i in range(7):
            puff = ico(ctx, f"{name}.steam{i}", radius * rng.uniform(0.35, 0.6), (x + rng.uniform(-4, 4), y + rng.uniform(-4, 4), z + height + 4 + i * 5), ctx.mat("steam", roughness=1.0, alpha=0.85), subdiv=2, scale=(1.3, 1.2, 0.8), smooth=True)
            ctx.tag("steam", puff)


def storage_tank(ctx, name, loc, radius=8.0, height=10.0, colour="white"):
    x, y, z = loc
    cylinder(ctx, name, radius, height, loc, ctx.mat(colour, roughness=0.6), segments=24, anchor="base", bevel=0.1)
    cylinder(ctx, f"{name}.rim", radius + 0.3, 0.5, (x, y, z + height - 0.5), ctx.mat("dark_steel"), segments=24, anchor="base")
    box(ctx, f"{name}.stair", (1.2, radius * 1.4, 0.3), (x + radius + 0.2, y, z + height * 0.5), ctx.mat("dark_steel"), rot=(0, math.radians(-40), 0))


def water_tower(ctx, name, loc, height=18.0, radius=4.0):
    x, y, z = loc
    for dx, dy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        cylinder(ctx, f"{name}.leg", 0.25, height, (x + dx * radius * 0.6, y + dy * radius * 0.6, z), ctx.mat("dark_steel"), segments=8, anchor="base")
    cylinder(ctx, f"{name}.tank", radius, radius * 1.3, (x, y, z + height), ctx.mat("steel", roughness=0.5), segments=16, anchor="base", bevel=0.1)
    cone(ctx, f"{name}.roof", radius + 0.3, 2.0, (x, y, z + height + radius * 1.3), ctx.mat("rust"), segments=16, tip=0.3)


def chimney(ctx, name, loc, radius=3.0, height=60.0, smoke=True):
    x, y, z = loc
    cylinder(ctx, name, radius, height, loc, ctx.mat("concrete"), segments=16, anchor="base", radius2=radius * 0.7)
    for i in range(3):
        band = cylinder(ctx, f"{name}.band{i}", radius * (1.0 - 0.1 * i) + 0.2, 1.5, (x, y, z + height * (0.3 + 0.25 * i)), ctx.mat("red" if i % 2 == 0 else "white"), segments=16, anchor="base", radius2=radius * (1.0 - 0.1 * i) + 0.15)
        ctx.tag("chimney_band", band)
    if smoke:
        for i in range(5):
            puff = ico(ctx, f"{name}.smoke{i}", radius * (1.2 + 0.4 * i), (x + i * 2.5, y + i * 1.5, z + height + 3 + i * 6), ctx.mat("steam", roughness=1.0, alpha=0.85), subdiv=2, scale=(1.2, 1.1, 0.7), smooth=True)
            ctx.tag("steam", puff)


def dam(ctx, name, loc, length=160.0, height=24.0, thickness=12.0, rot=0.0):
    """Gravity dam cross-section extruded along X (upstream face towards +Y)."""
    verts = [
        (-length / 2, -thickness, 0), (length / 2, -thickness, 0), (length / 2, thickness * 0.9, 0), (-length / 2, thickness * 0.9, 0),
        (-length / 2, -thickness * 0.25, height), (length / 2, -thickness * 0.25, height), (length / 2, thickness * 0.25, height), (-length / 2, thickness * 0.25, height),
    ]
    faces = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7), (3, 2, 1, 0)]
    body = mesh_from_pydata(ctx, name, verts, faces, [ctx.mat("concrete")], loc, (0, 0, rot), bevel=0.4)
    for i in range(int(length / 12)):
        tower_x = -length / 2 + 6 + i * 12
        pier = box(ctx, f"{name}.pier{i}", (1.2, thickness * 0.6, 2.2), (tower_x, 0, height), ctx.mat("stone"), anchor="base")
        parent(pier, body)
    road = box(ctx, f"{name}.crest", (length, thickness * 0.5, 0.3), (0, 0, height), ctx.mat("asphalt"), anchor="base")
    parent(road, body)
    ctx.objects[name] = body
    return body


def intake_tower(ctx, name, loc, height=26.0):
    x, y, z = loc
    cylinder(ctx, name, 3.0, height, loc, ctx.mat("concrete"), segments=14, anchor="base")
    box(ctx, f"{name}.house", (7, 7, 4), (x, y, z + height), ctx.mat("stone"), bevel=0.1, anchor="base")
    box(ctx, f"{name}.bridge", (1.6, 30, 0.6), (x, y + 15, z + height + 0.5), ctx.mat("steel"), anchor="base")
