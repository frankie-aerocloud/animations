"""Cars, vans, lorries, tractors, boats, ships and cranes; `drive` moves any of them along a path."""

from __future__ import annotations

import math

from mathutils import Vector

from studio.assets.props import cross
import bpy

from studio.blender.primitives import box, cylinder, empty, key, mesh_from_pydata, multi_box, parent, set_interp
from studio.core.motion import heading, polyline_length, unwrap

CAR_COLOURS = ("white", "red", "navy", "teal", "stone", "yellow", "orange", "cream")


def _wheels(ctx, name, root, positions, radius=0.34, width=0.24):
    for i, (x, y) in enumerate(positions):
        wheel = cylinder(ctx, f"{name}.wheel{i}", radius, width, (x, y, radius), ctx.mat("black", roughness=0.7), segments=12, rot=(0, math.pi / 2, 0))
        parent(wheel, root)


def _lights(ctx, name, root, front_y, back_y, z, half_width):
    """Emissive headlights and tail lights for night scenes (one merged mesh)."""
    head = ctx.palette.emissive(f"{name} headlights", (1.0, 0.95, 0.85), 8.0)
    tail = ctx.palette.emissive(f"{name} tail lights", "beacon_red", 4.0)
    boxes = [((sx * half_width, front_y, z), (0.32, 0.08, 0.16), 0) for sx in (-1, 1)] + [((sx * half_width, back_y, z), (0.3, 0.06, 0.14), 1) for sx in (-1, 1)]
    lights = multi_box(ctx, f"{name}.lights", boxes, [head, tail])
    parent(lights, root)
    return lights


def car(ctx, name, loc, rot=0.0, colour=None, lit=False):
    root = empty(ctx, name, loc, (0, 0, rot))
    paint = ctx.mat(colour or ctx.rng.choice(CAR_COLOURS), roughness=0.35)
    glass = ctx.palette.glass(f"{name} glass")
    body = multi_box(ctx, f"{name}.body", [((0, 0, 0.62), (1.85, 4.3, 0.6), 0), ((0, -0.25, 1.15), (1.65, 2.3, 0.52), 1), ((0, -0.25, 1.42), (1.6, 2.2, 0.08), 0)], [paint, glass], bevel=0.08)
    parent(body, root)
    _wheels(ctx, name, root, ((-0.85, 1.35), (0.85, 1.35), (-0.85, -1.35), (0.85, -1.35)))
    if lit:
        _lights(ctx, name, root, 2.16, -2.16, 0.7, 0.62)
    ctx.objects[name] = root
    ctx.tag("vehicle", root)
    return root


def van(ctx, name, loc, rot=0.0, colour="white", kind="van", lit=False):
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
    if lit:
        _lights(ctx, name, root, 2.82, -2.82, 0.9, 0.7)
    ctx.objects[name] = root
    ctx.tag("vehicle", root)
    return root


def lorry(ctx, name, loc, rot=0.0, colour="navy", cargo="tanker", lit=False):
    """Lorry with a tank, a container, a fire-fighting body or a flat bed."""
    root = empty(ctx, name, loc, (0, 0, rot))
    if cargo == "fire":
        colour = "red"
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
    elif cargo == "fire":
        body = multi_box(ctx, f"{name}.pump", [((0, -0.8, 2.0), (2.4, 7.0, 2.0), 0), ((0, -0.8, 3.2), (0.5, 7.5, 0.3), 1), ((0, -1.0, 3.6), (0.6, 8.5, 0.3), 1), ((0, 3.0, 3.2), (2.2, 0.4, 0.3), 2)], [paint, ctx.mat("steel"), ctx.palette.emissive(f"{name} beacon", "beacon_blue", 0.0)], bevel=0.06)
        parent(body, root)
        ladder = box(ctx, f"{name}.ladder", (0.5, 7.0, 0.25), (0, -1.5, 3.9), ctx.mat("steel"), bevel=0.02)
        ladder.rotation_euler = (math.radians(-18), 0, 0)
        parent(ladder, root)
        bar = box(ctx, f"{name}.bar", (1.8, 0.35, 0.22), (0, 3.4, 2.95), ctx.palette.emissive(f"{name} light bar", "beacon_blue", 0.0), bevel=0.03)
        parent(bar, root)
        ctx.tag("beacon", bar)
    _wheels(ctx, name, root, ((-1.1, 3.6), (1.1, 3.6), (-1.1, -1.8), (1.1, -1.8), (-1.1, -3.2), (1.1, -3.2)), 0.5, 0.32)
    if lit:
        _lights(ctx, name, root, 5.12, -5.2, 1.0, 0.85)
    ctx.objects[name] = root
    ctx.tag("vehicle", root)
    return root


def helicopter(ctx, name, loc, rot=0.0, searchlight=True, lit=True):
    """Low-poly helicopter: spinning rotors are keyed for the whole scene; optional sweeping searchlight."""
    root = empty(ctx, name, loc, (0, 0, rot))
    paint = ctx.mat("navy", roughness=0.4)
    body = multi_box(ctx, f"{name}.body", [((0, 0.6, 0), (1.9, 5.2, 1.7), 0), ((0, 1.9, 0.3), (1.6, 1.4, 1.0), 1), ((0, -4.2, 0.3), (0.45, 5.0, 0.55), 0), ((0, -6.4, 0.9), (0.15, 1.0, 1.6), 0), ((-0.9, 0.5, -1.2), (0.12, 3.6, 0.12), 2), ((0.9, 0.5, -1.2), (0.12, 3.6, 0.12), 2)], [paint, ctx.palette.glass(f"{name} canopy"), ctx.mat("dark_steel")], bevel=0.08)
    parent(body, root)
    rotor = empty(ctx, f"{name}.rotor", (0, 0.4, 1.05))
    parent(rotor, root)
    cylinder(ctx, f"{name}.hub", 0.25, 0.4, (0, 0, 0), ctx.mat("dark_steel"), segments=8, anchor="base")
    ctx.collection.objects[-1].parent = rotor
    for i in range(2):
        blade = box(ctx, f"{name}.blade{i}", (0.28, 12.0, 0.06), (0, 0, 0.3), ctx.mat("dark_steel"))
        blade.rotation_euler = (0, 0, i * math.pi / 2)
        parent(blade, rotor)
    tail = box(ctx, f"{name}.tail_rotor", (0.08, 1.6, 0.14), (0.3, -6.4, 0.9), ctx.mat("dark_steel"))
    parent(tail, root)
    key(rotor, "rotation_euler", 1, (0.0, 0.0, 0.0))
    key(rotor, "rotation_euler", ctx.frames, (0.0, 0.0, math.tau * 2.2 * ctx.frames / ctx.fps))
    key(tail, "rotation_euler", 1, (0.0, 0.0, 0.0))
    key(tail, "rotation_euler", ctx.frames, (math.tau * 6.0 * ctx.frames / ctx.fps, 0.0, 0.0))
    set_interp(rotor, "LINEAR")
    set_interp(tail, "LINEAR")
    ctx.tag("rotor", rotor)
    if lit:
        beacon = box(ctx, f"{name}.beacon", (0.3, 0.3, 0.2), (0, -0.5, -0.9), ctx.palette.emissive(f"{name} beacon", "beacon_red", 6.0))
        parent(beacon, root)
    if searchlight:
        data = bpy.data.lights.new(f"{name}.searchlight", "SPOT")
        data.energy = 40000.0
        data.spot_size = math.radians(22)
        data.spot_blend = 0.45
        data.color = (1.0, 0.95, 0.85)
        data.shadow_soft_size = 0.5
        light = bpy.data.objects.new(f"{name}.searchlight", data)
        light.location = (0, 2.2, -0.9)
        light.rotation_euler = (math.radians(32), 0, 0)
        ctx.link(light)
        parent(light, root)
        key(light, "rotation_euler", 1, (math.radians(28), 0.0, math.radians(-14)))
        key(light, "rotation_euler", ctx.frames, (math.radians(36), 0.0, math.radians(16)))
        set_interp(light, "SINE", "EASE_IN_OUT")
        ctx.tag("searchlight", light)
    ctx.objects[name] = root
    return root


def traffic_jam(ctx, name, start, end, lanes=2, gap=7.0, lit=False, lane_width=3.4, lorries=0.15, facing=1):
    """Cars (and some lorries) queued bumper to bumper along a line, in `lanes` parallel lanes."""
    rng = ctx.rng
    sx, sy = start
    ex, ey = end
    length = math.hypot(ex - sx, ey - sy)
    ux, uy = (ex - sx) / length, (ey - sy) / length
    nx, ny = -uy, ux
    heading_rot = math.atan2(-(ux if facing > 0 else -ux), uy if facing > 0 else -uy)
    vehicles = []
    count = 0
    for lane in range(lanes):
        offset = (lane - (lanes - 1) / 2.0) * lane_width
        travelled = rng.uniform(0.0, gap)
        while travelled < length:
            px = sx + ux * travelled + nx * offset + rng.uniform(-0.25, 0.25)
            py = sy + uy * travelled + ny * offset + rng.uniform(-0.25, 0.25)
            rot = heading_rot + rng.uniform(-0.05, 0.05)
            if rng.random() < lorries:
                vehicles.append(lorry(ctx, f"{name}.{count}", (px, py, 0.0), rot, rng.choice(("white", "navy", "red")), "container", lit=lit))
                travelled += gap * 1.9
            else:
                vehicles.append(car(ctx, f"{name}.{count}", (px, py, 0.0), rot, lit=lit))
                travelled += gap * rng.uniform(0.9, 1.3)
            count += 1
    return vehicles


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
    """Move a vehicle root along a 2D or 3D path at constant speed, facing the direction of travel."""
    points = [Vector((p[0], p[1], p[2] if len(p) > 2 else z)) for p in path]
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
