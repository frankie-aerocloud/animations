"""Cars, vans, lorries, tractors, boats, ships and cranes; `drive` moves any of them along a path."""

from __future__ import annotations

import math

from mathutils import Vector

from studio.assets.props import cross
from studio.blender.primitives import box, cylinder, empty, key, mesh_from_pydata, multi_box, parent, set_interp
from studio.core.motion import heading, polyline_length, unwrap

CAR_COLOURS = ("white", "red", "navy", "teal", "stone", "yellow", "orange", "cream")


def _wheels(ctx, name, root, positions, radius=0.34, width=0.24):
    for i, (x, y) in enumerate(positions):
        wheel = cylinder(ctx, f"{name}.wheel{i}", radius, width, (x, y, radius), ctx.mat("black", roughness=0.7), segments=12, rot=(0, math.pi / 2, 0))
        parent(wheel, root)


def car(ctx, name, loc, rot=0.0, colour=None):
    root = empty(ctx, name, loc, (0, 0, rot))
    paint = ctx.mat(colour or ctx.rng.choice(CAR_COLOURS), roughness=0.35)
    glass = ctx.palette.glass(f"{name} glass")
    body = multi_box(ctx, f"{name}.body", [((0, 0, 0.62), (1.85, 4.3, 0.6), 0), ((0, -0.25, 1.15), (1.65, 2.3, 0.52), 1), ((0, -0.25, 1.42), (1.6, 2.2, 0.08), 0)], [paint, glass], bevel=0.08)
    parent(body, root)
    _wheels(ctx, name, root, ((-0.85, 1.35), (0.85, 1.35), (-0.85, -1.35), (0.85, -1.35)))
    ctx.objects[name] = root
    ctx.tag("vehicle", root)
    return root


def van(ctx, name, loc, rot=0.0, colour="white", kind="van"):
    root = empty(ctx, name, loc, (0, 0, rot))
    paint = ctx.mat(colour, roughness=0.4)
    glass = ctx.palette.glass(f"{name} glass")
    boxes = [((0, 0, 1.0), (2.1, 5.6, 1.4), 0), ((0, 0, 2.0), (2.1, 5.6, 0.8), 0), ((0, 2.5, 1.7), (1.9, 0.3, 0.9), 1)]
    mats = [paint, glass, ctx.mat("red"), ctx.mat("yellow")]
    if kind == "ambulance":
        boxes += [((0, 0, 1.0), (2.14, 5.0, 0.3), 3), ((1.07, -0.6, 1.2), (0.05, 1.5, 1.5), 2), ((-1.07, -0.6, 1.2), (0.05, 1.5, 1.5), 2)]
    body = multi_box(ctx, f"{name}.body", boxes, mats, bevel=0.07)
    parent(body, root)
    if kind == "ambulance":
        emblem = cross(ctx, f"{name}.cross", (0, -2.82, 1.7), 1.0, rot=(0, 0, 0))
        parent(emblem, root)
        bar = box(ctx, f"{name}.bar", (1.6, 0.35, 0.22), (0, 1.5, 2.5), ctx.palette.emissive(f"{name} beacon", "beacon_blue", 0.0), bevel=0.03)
        parent(bar, root)
        ctx.tag("beacon", bar)
    _wheels(ctx, name, root, ((-0.95, 1.8), (0.95, 1.8), (-0.95, -1.8), (0.95, -1.8)), 0.4, 0.26)
    ctx.objects[name] = root
    ctx.tag("vehicle", root)
    return root


def lorry(ctx, name, loc, rot=0.0, colour="navy", cargo="tanker"):
    """Lorry with a tank, a container or a flat bed."""
    root = empty(ctx, name, loc, (0, 0, rot))
    paint = ctx.mat(colour, roughness=0.4)
    glass = ctx.palette.glass(f"{name} glass")
    cab = multi_box(ctx, f"{name}.cab", [((0, 3.9, 1.6), (2.4, 2.4, 2.3), 0), ((0, 4.5, 2.2), (2.2, 1.2, 0.9), 1), ((0, 0.5, 0.75), (2.3, 9.5, 0.5), 2)], [paint, glass, ctx.mat("dark_steel")], bevel=0.08)
    parent(cab, root)
    if cargo == "tanker":
        tank = cylinder(ctx, f"{name}.tank", 1.25, 7.0, (0, -0.6, 2.3), ctx.mat("white", roughness=0.35), segments=18, rot=(math.pi / 2, 0, 0), bevel=0.15)
        parent(tank, root)
        band = cylinder(ctx, f"{name}.band", 1.3, 0.3, (0, -0.6, 2.3), ctx.mat("cap"), segments=18, rot=(math.pi / 2, 0, 0))
        parent(band, root)
        tap_obj = cylinder(ctx, f"{name}.tap", 0.12, 0.8, (1.25, -3.2, 1.2), ctx.mat("steel", metallic=0.8, roughness=0.3), segments=8, rot=(0, math.pi / 2, 0))
        parent(tap_obj, root)
        ctx.anchor(f"{name}.tap", (loc[0] + 1.8 * math.cos(rot) + 3.2 * math.sin(rot), loc[1] + 1.8 * math.sin(rot) - 3.2 * math.cos(rot), loc[2] + 1.1))
    elif cargo == "container":
        box_obj = box(ctx, f"{name}.container", (2.4, 7.5, 2.6), (0, -0.8, 1.0), ctx.mat(ctx.rng.choice(("red", "teal", "orange", "navy", "rust"))), bevel=0.05, anchor="base")
        parent(box_obj, root)
    _wheels(ctx, name, root, ((-1.1, 3.6), (1.1, 3.6), (-1.1, -1.8), (1.1, -1.8), (-1.1, -3.2), (1.1, -3.2)), 0.5, 0.32)
    ctx.objects[name] = root
    ctx.tag("vehicle", root)
    return root


def tractor(ctx, name, loc, rot=0.0):
    root = empty(ctx, name, loc, (0, 0, rot))
    paint = ctx.mat("red", roughness=0.4)
    body = multi_box(ctx, f"{name}.body", [((0, 0.6, 1.2), (1.2, 2.6, 0.9), 0), ((0, -0.9, 1.9), (1.4, 1.4, 1.3), 1), ((0.3, 1.6, 2.2), (0.12, 0.12, 1.0), 2)], [paint, ctx.palette.glass(f"{name} glass"), ctx.mat("dark_steel")], bevel=0.06)
    parent(body, root)
    for x in (-0.9, 0.9):
        back = cylinder(ctx, f"{name}.rear", 0.85, 0.5, (x, -0.8, 0.85), ctx.mat("black"), segments=14, rot=(0, math.pi / 2, 0))
        parent(back, root)
        front = cylinder(ctx, f"{name}.front", 0.45, 0.3, (x * 0.8, 1.6, 0.45), ctx.mat("black"), segments=10, rot=(0, math.pi / 2, 0))
        parent(front, root)
    ctx.objects[name] = root
    ctx.tag("vehicle", root)
    return root


def boat(ctx, name, loc, rot=0.0, length=8.0, colour=None, sail=False):
    root = empty(ctx, name, loc, (0, 0, rot))
    hull_colour = ctx.mat(colour or ctx.rng.choice(("white", "red", "navy", "teal")), roughness=0.4)
    w = length * 0.3
    verts = [(-w / 2, -length / 2, 0), (w / 2, -length / 2, 0), (w / 2, length * 0.25, 0), (0, length / 2, 0.2), (-w / 2, length * 0.25, 0),
             (-w / 2 * 1.05, -length / 2, 1.2), (w / 2 * 1.05, -length / 2, 1.2), (w / 2 * 1.05, length * 0.25, 1.3), (0, length / 2 + 0.3, 1.6), (-w / 2 * 1.05, length * 0.25, 1.3)]
    faces = [(0, 1, 2, 3, 4), (0, 5, 6, 1), (1, 6, 7, 2), (2, 7, 8, 3), (3, 8, 9, 4), (4, 9, 5, 0), (5, 9, 8, 7, 6)]
    hull = mesh_from_pydata(ctx, f"{name}.hull", verts, faces, [hull_colour], bevel=0.08)
    parent(hull, root)
    deck = box(ctx, f"{name}.deck", (w * 0.9, length * 0.7, 0.12), (0, -length * 0.05, 1.2), ctx.mat("cream"), anchor="base")
    parent(deck, root)
    if sail:
        mast = cylinder(ctx, f"{name}.mast", 0.08, length * 1.1, (0, 0.2, 1.3), ctx.mat("trunk"), segments=6, anchor="base")
        parent(mast, root)
        sail_obj = mesh_from_pydata(ctx, f"{name}.sail", [(0.05, 0.25, 1.6), (0.05, 0.25, length * 1.1), (0.05, -length * 0.4, 1.8)], [(0, 1, 2)], [ctx.mat("white")])
        parent(sail_obj, root)
    else:
        cabin = box(ctx, f"{name}.cabin", (w * 0.6, length * 0.25, 1.2), (0, -length * 0.1, 1.3), ctx.mat("white"), bevel=0.05, anchor="base")
        parent(cabin, root)
    ctx.objects[name] = root
    ctx.tag("boat", root)
    return root


def ship(ctx, name, loc, rot=0.0, length=90.0, colour="navy"):
    root = empty(ctx, name, loc, (0, 0, rot))
    w = length * 0.16
    verts = [(-w / 2, -length / 2, -2), (w / 2, -length / 2, -2), (w / 2, length * 0.3, -2), (0, length / 2, -1), (-w / 2, length * 0.3, -2),
             (-w / 2, -length / 2, 6), (w / 2, -length / 2, 6), (w / 2, length * 0.3, 6.5), (0, length / 2 + 2, 8), (-w / 2, length * 0.3, 6.5)]
    faces = [(0, 1, 2, 3, 4), (0, 5, 6, 1), (1, 6, 7, 2), (2, 7, 8, 3), (3, 8, 9, 4), (4, 9, 5, 0), (5, 9, 8, 7, 6)]
    hull = mesh_from_pydata(ctx, f"{name}.hull", verts, faces, [ctx.mat(colour, roughness=0.5)], bevel=0.3)
    parent(hull, root)
    stripe = box(ctx, f"{name}.stripe", (w + 0.2, length * 0.8, 1.2), (0, -length * 0.1, 0.6), ctx.mat("red"), anchor="base")
    parent(stripe, root)
    bridge = multi_box(ctx, f"{name}.bridge", [((0, -length * 0.32, 6), (w * 0.8, length * 0.14, 9), 0), ((0, -length * 0.32, 15), (w * 0.6, length * 0.1, 3.5), 0), ((0, -length * 0.4, 18.5), (3, 3, 7), 1)], [ctx.mat("white"), ctx.mat("red")], bevel=0.2, loc=(0, 0, 0))
    bridge.location = (0, 0, 0)
    parent(bridge, root)
    for i in range(4):
        cargo = box(ctx, f"{name}.cargo{i}", (w * 0.7, length * 0.1, 5), (0, -length * 0.18 + i * length * 0.14, 6), ctx.mat(ctx.rng.choice(("red", "teal", "orange", "navy"))), bevel=0.1, anchor="base")
        parent(cargo, root)
    ctx.objects[name] = root
    ctx.tag("boat", root)
    return root


def crane(ctx, name, loc, rot=0.0, height=40.0, reach=50.0):
    root = empty(ctx, name, loc, (0, 0, rot))
    steel = ctx.mat("orange", roughness=0.5)
    boxes = []
    for x, y in ((-10, -6), (10, -6), (-10, 6), (10, 6)):
        boxes.append(((x, y, height / 2), (1.6, 1.6, height), 0))
    boxes.append(((0, 0, height + 1), (24, 14, 2), 0))
    boxes.append(((0, reach / 2 - 7, height + 3), (3, reach, 2.2), 0))
    boxes.append(((0, 0, height / 2), (1.0, 14, 1.0), 0))
    boxes.append(((0, reach * 0.3, height - 6), (4, 4, 4), 1))
    body = multi_box(ctx, f"{name}.frame", boxes, [steel, ctx.mat("yellow")], bevel=0.1)
    parent(body, root)
    ctx.objects[name] = root
    return root


def drive(ctx, obj, path, start=0.0, end=None, speed=12.0, z=0.0):
    """Move a vehicle root along a 2D path at constant speed, facing the direction of travel."""
    points = [Vector((p[0], p[1], z)) for p in path]
    total = polyline_length(points)
    f0 = ctx.frame(start)
    f1 = ctx.frame(end) if end is not None else min(ctx.frames, f0 + round(total / max(0.1, speed) * ctx.fps))
    previous = obj.rotation_euler.z
    travelled = 0.0
    for i, point in enumerate(points):
        if i:
            travelled += (points[i] - points[i - 1]).length
        frame = f0 + round((f1 - f0) * (travelled / total if total else 0.0))
        key(obj, "location", frame, point)
        if i < len(points) - 1:
            previous = unwrap(previous, heading(point, points[i + 1]))
            key(obj, "rotation_euler", frame, (0, 0, previous))
    set_interp(obj, "LINEAR", path="location")
    set_interp(obj, "SINE", "EASE_IN_OUT", path="rotation_euler")
    return f1
