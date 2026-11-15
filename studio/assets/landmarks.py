"""New York style landmarks and street dressing: statue, spire and tapered towers, suspension bridge,
billboards, food carts, cafe tables, bins, rubbish, airliners, drones, army trucks and police cars."""

from __future__ import annotations

import math

from studio.assets import vehicles
from studio.blender.primitives import box, cone, cylinder, empty, key, mesh_from_pydata, multi_box, parent, set_interp


def statue_of_liberty(ctx, name, loc, rot=0.0, scale=1.0):
    """Pedestal plus statue (about 93 m at scale 1), torch tagged 'torch'."""
    x, y, z = loc
    patina = ctx.mat("patina", roughness=0.7)
    stone = ctx.mat("stone")
    root = empty(ctx, name, (x, y, z), (0, 0, rot))
    root.scale = (scale, scale, scale)
    base = multi_box(ctx, f"{name}.pedestal", [((0, 0, 4), (48, 48, 8), 0), ((0, 0, 14), (30, 30, 12), 0), ((0, 0, 31), (22, 22, 22), 0), ((0, 0, 44), (18, 18, 4), 0)], [stone], bevel=0.3)
    parent(base, root)
    robe = cylinder(ctx, f"{name}.robe", 7.0, 26.0, (0, 0, 46), patina, segments=10, anchor="base", radius2=4.0)
    parent(robe, root)
    torso = box(ctx, f"{name}.torso", (7.0, 5.5, 9.0), (0, 0, 72), patina, bevel=0.5, anchor="base")
    parent(torso, root)
    head = box(ctx, f"{name}.head", (3.4, 3.4, 4.2), (0, 0, 81), patina, bevel=0.6, anchor="base")
    parent(head, root)
    crown = cylinder(ctx, f"{name}.crown", 2.4, 1.2, (0, 0, 85), patina, segments=7, anchor="base")
    parent(crown, root)
    for i in range(7):
        angle = -math.pi * 0.85 + i * (math.pi * 1.7 / 6)
        spike = box(ctx, f"{name}.spike{i}", (0.5, 3.6, 0.4), (2.4 * math.sin(angle), 2.4 * math.cos(angle) * -1 + 0.4, 85.6), patina)
        spike.rotation_euler = (math.radians(-35), 0, -angle)
        parent(spike, root)
    arm = box(ctx, f"{name}.arm", (2.2, 2.2, 15.0), (3.6, -0.5, 75), patina, bevel=0.3, anchor="base")
    arm.rotation_euler = (0, math.radians(-8), 0)
    parent(arm, root)
    torch = cylinder(ctx, f"{name}.torch", 1.4, 3.0, (5.6, -0.5, 89.5), ctx.mat("yellow", roughness=0.5), segments=8, anchor="base")
    parent(torch, root)
    flame = cone(ctx, f"{name}.flame", 1.6, 3.4, (5.6, -0.5, 92.5), ctx.palette.emissive(f"{name} flame", "orange", 5.0), segments=6, tip=0.1)
    parent(flame, root)
    ctx.tag("torch", flame)
    tablet = box(ctx, f"{name}.tablet", (4.5, 1.2, 6.5), (-5.2, 1.2, 68), patina, bevel=0.2, anchor="base")
    tablet.rotation_euler = (0, math.radians(10), 0)
    parent(tablet, root)
    ctx.anchor(name, (x, y, z + 70 * scale))
    ctx.anchor(f"{name}.torch", (x + 5.6 * scale, y, z + 92 * scale))
    ctx.anchor(f"{name}.crown", (x, y, z + 86 * scale))
    ctx.anchor(f"{name}.base", (x, y, z + 46 * scale))
    return root


def spire_tower(ctx, name, loc, height=300.0, lit=None):
    """Stepped art-deco tower with a spire (Empire State silhouette)."""
    x, y, z = loc
    body = multi_box(ctx, f"{name}.steps", [((0, 0, height * 0.1), (60, 40, height * 0.2), 0), ((0, 0, height * 0.42), (40, 28, height * 0.44), 0), ((0, 0, height * 0.72), (28, 20, height * 0.16), 0), ((0, 0, height * 0.84), (16, 14, height * 0.08), 0)], [ctx.mat("stone")], (x, y, z), bevel=0.4)
    windows = []
    glow = lit or ctx.palette.glass(f"{name} glass")
    for k in range(int(height * 0.8 / 4.5)):
        zz = 3.0 + k * 4.5
        w = 60 if zz < height * 0.2 else 40 if zz < height * 0.64 else 28 if zz < height * 0.8 else 16
        d = 40 if zz < height * 0.2 else 28 if zz < height * 0.64 else 20 if zz < height * 0.8 else 14
        for i in range(int(w / 3.6)):
            ox = -w / 2 + 1.8 + i * 3.6
            windows.append(((ox, d / 2 + 0.05, zz), (1.6, 0.1, 2.4), 0))
            windows.append(((ox, -d / 2 - 0.05, zz), (1.6, 0.1, 2.4), 0))
        for i in range(int(d / 3.6)):
            oy = -d / 2 + 1.8 + i * 3.6
            windows.append(((w / 2 + 0.05, oy, zz), (0.1, 1.6, 2.4), 0))
            windows.append(((-w / 2 - 0.05, oy, zz), (0.1, 1.6, 2.4), 0))
    multi_box(ctx, f"{name}.windows", windows, [glow], (x, y, z))
    cylinder(ctx, f"{name}.mast", 4.0, height * 0.12, (x, y, z + height * 0.88), ctx.mat("steel", roughness=0.4), segments=8, anchor="base", radius2=2.0)
    cone(ctx, f"{name}.spire", 2.0, height * 0.1, (x, y, z + height), ctx.mat("steel", roughness=0.4), segments=8, tip=0.1)
    ctx.anchor(f"{name}.top", (x, y, z + height * 1.05))
    ctx.anchor(name, (x, y, z + height * 0.5))
    ctx.anchor(f"{name}.roof", (x, y, z + height * 0.88))
    return body


def tapered_tower(ctx, name, loc, height=330.0, lit=None):
    """Square-to-square tapering glass tower turned 45 degrees at the top (One WTC silhouette)."""
    x, y, z = loc
    w = 60.0
    bottom = [(-w / 2, -w / 2, 0), (w / 2, -w / 2, 0), (w / 2, w / 2, 0), (-w / 2, w / 2, 0)]
    t = w * 0.35
    top = [(0, -t, height), (t, 0, height), (0, t, height), (-t, 0, height)]
    verts = bottom + top
    faces = [(0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7), (3, 2, 1, 0)]
    glass = lit or ctx.palette.glass(f"{name} glass", "glass")
    body = mesh_from_pydata(ctx, name, verts, faces, [ctx.mat("steel", roughness=0.25, metallic=0.4)], (x, y, z), bevel=0.5)
    stripes = [((0, 0, 20 + k * 20), (w * (1 - 0.65 * (20 + k * 20) / height) + 0.6, w * (1 - 0.65 * (20 + k * 20) / height) + 0.6, 0.6), 0) for k in range(int(height / 20) - 1)]
    multi_box(ctx, f"{name}.bands", stripes, [glass], (x, y, z))
    cylinder(ctx, f"{name}.mast", 2.5, 90.0, (x, y, z + height), ctx.mat("steel"), segments=8, anchor="base", radius2=0.6)
    ctx.anchor(f"{name}.top", (x, y, z + height + 90))
    ctx.anchor(name, (x, y, z + height * 0.5))
    ctx.anchor(f"{name}.roof", (x, y, z + height))
    return body


def suspension_bridge(ctx, name, start, end, deck_z=24.0, tower_height=84.0):
    """Two-tower suspension bridge between two shore points (cables and hangers merged)."""
    sx, sy = start
    ex, ey = end
    length = math.hypot(ex - sx, ey - sy)
    angle = math.atan2(ey - sy, ex - sx)
    mid = ((sx + ex) / 2, (sy + ey) / 2)
    stone = ctx.mat("stone")
    steel = ctx.mat("dark_steel")
    boxes = [((0, 0, deck_z), (length + 60, 26, 2.2), 0), ((0, 11.5, deck_z + 1.8), (length + 60, 1.2, 1.6), 1), ((0, -11.5, deck_z + 1.8), (length + 60, 1.2, 1.6), 1)]
    for tx in (-length * 0.25, length * 0.25):
        for ty in (-9, 9):
            boxes.append(((tx, ty, tower_height / 2), (10, 6, tower_height), 2))
        boxes.append(((tx, 0, tower_height - 8), (10, 24, 10), 2))
        boxes.append(((tx, 0, tower_height * 0.5), (10, 24, 6), 2))
    segments = 24
    for side in (-1, 1):
        points = []
        for i in range(segments + 1):
            t = -0.5 + i / segments
            px = t * length
            if abs(px) < length * 0.25:
                u = px / (length * 0.25)
                pz = deck_z + 6 + (tower_height - deck_z - 6) * u * u
            else:
                u = (abs(px) - length * 0.25) / (length * 0.25 + 30)
                pz = tower_height - (tower_height - deck_z - 2) * u
            points.append((px, side * 10.5, pz))
        for (ax, ay, az), (bx, by, bz) in zip(points, points[1:], strict=False):
            seg_len = math.hypot(bx - ax, bz - az)
            boxes.append((((ax + bx) / 2, ay, (az + bz) / 2), (seg_len + 0.5, 0.7, 0.7), 1))
            if abs(ax) < length * 0.25 or True:
                boxes.append(((ax, ay, (az + deck_z) / 2), (0.3, 0.3, max(0.5, az - deck_z)), 1))
    body = multi_box(ctx, name, boxes, [ctx.mat("asphalt"), steel, stone], (mid[0], mid[1], 0.0), (0, 0, angle), bevel=0.3)
    ctx.anchor(f"{name}.mid", (mid[0], mid[1], deck_z + 2))
    ctx.anchor(f"{name}.tower", (mid[0] - math.cos(angle) * length * 0.25, mid[1] - math.sin(angle) * length * 0.25, tower_height))
    ctx.objects[name] = body
    return body


def billboard(ctx, name, loc, size=(18.0, 10.0), rot=0.0, colour=None, strength=4.0):
    colours = ((1.0, 0.2, 0.3), (0.2, 0.6, 1.0), (1.0, 0.8, 0.1), (0.3, 1.0, 0.5), (1.0, 0.4, 0.9), (0.95, 0.95, 0.95))
    rgb = colour or ctx.rng.choice(colours)
    frame = box(ctx, f"{name}.frame", (size[0] + 1.0, 0.6, size[1] + 1.0), loc, ctx.mat("dark_steel"), rot=(0, 0, rot))
    panel = box(ctx, name, (size[0], 0.3, size[1]), (0, -0.4, 0), ctx.palette.emissive(f"{name} glow", rgb, strength))
    parent(panel, frame)
    ctx.tag("billboard", panel)
    return frame


def food_cart(ctx, name, loc, rot=0.0, open_umbrella=True):
    x, y, z = loc
    body = box(ctx, name, (1.2, 2.0, 1.1), (x, y, z + 0.55), ctx.mat("steel", roughness=0.4), bevel=0.04, rot=(0, 0, rot))
    stripe = box(ctx, f"{name}.stripe", (1.22, 2.02, 0.3), (0, 0, 0.1), ctx.mat("red"))
    parent(stripe, body)
    for dy in (-0.7, 0.7):
        wheel = cylinder(ctx, f"{name}.wheel", 0.25, 0.1, (-0.62, dy, -0.3), ctx.mat("black"), segments=10, rot=(0, math.pi / 2, 0))
        parent(wheel, body)
    pole = cylinder(ctx, f"{name}.pole", 0.04, 1.6, (0, 0, 0.5), ctx.mat("steel"), segments=6, anchor="base")
    parent(pole, body)
    canopy = cone(ctx, f"{name}.umbrella", 1.4 if open_umbrella else 0.35, 0.5 if open_umbrella else 1.2, (0, 0, 2.0 if open_umbrella else 1.3), ctx.mat(ctx.rng.choice(("yellow", "red", "teal")), roughness=0.9), segments=8, tip=0.05)
    parent(canopy, body)
    return body


def cafe_table(ctx, name, loc, rot=0.0, umbrella=True):
    x, y, z = loc
    top = cylinder(ctx, f"{name}.top", 0.6, 0.05, (x, y, z + 0.75), ctx.mat("white"), segments=10)
    leg = cylinder(ctx, f"{name}.leg", 0.04, 0.75, (0, 0, -0.75), ctx.mat("dark_steel"), segments=6, anchor="base")
    parent(leg, top)
    for i in range(3):
        a = rot + i * math.tau / 3
        chair = box(ctx, f"{name}.chair{i}", (0.4, 0.4, 0.05), (0.95 * math.cos(a), 0.95 * math.sin(a), -0.3), ctx.mat("dark_steel"))
        parent(chair, top)
        back = box(ctx, f"{name}.back{i}", (0.4, 0.05, 0.4), (1.13 * math.cos(a), 1.13 * math.sin(a), -0.1), ctx.mat("dark_steel"), rot=(0, 0, a + math.pi / 2))
        parent(back, top)
    if umbrella:
        pole = cylinder(ctx, f"{name}.pole", 0.03, 1.8, (0, 0, 0), ctx.mat("steel"), segments=6, anchor="base")
        parent(pole, top)
        canopy = cone(ctx, f"{name}.umbrella", 1.5, 0.5, (0, 0, 1.6), ctx.mat(ctx.rng.choice(("red", "cream", "teal")), roughness=0.9), segments=8, tip=0.05)
        parent(canopy, top)
    return top


def bin_(ctx, name, loc, knocked=False):
    x, y, z = loc
    obj = cylinder(ctx, name, 0.4, 1.0, (x, y, z), ctx.mat("dark_steel", roughness=0.6), segments=10, anchor="base")
    if knocked:
        obj.rotation_euler = (math.radians(80), 0, ctx.rng.uniform(0, math.tau))
        obj.location.z = z + 0.4
    return obj


def rubbish_pile(ctx, name, loc, size=1.0, count=6):
    x, y, z = loc
    rng = ctx.rng
    boxes = []
    for i in range(count):
        boxes.append(((rng.uniform(-size, size), rng.uniform(-size, size), size * 0.35 * rng.uniform(0.5, 1.0)), (size * 0.8, size * 0.6, size * 0.7), i % 2))
    obj = multi_box(ctx, name, boxes, [ctx.mat("black", roughness=0.6), ctx.mat("trousers_2", roughness=0.8)], (x, y, z), bevel=0.08)
    ctx.tag("rubbish", obj)
    return obj


def airliner(ctx, name, loc, rot=0.0, colour="white", tail_colour=None):
    """Low-poly twin-jet airliner, about 38 m long, nose towards local +Y."""
    root = empty(ctx, name, loc, (0, 0, rot))
    paint = ctx.mat(colour, roughness=0.35)
    accent = ctx.mat(tail_colour or ctx.rng.choice(("red", "navy", "teal", "orange")), roughness=0.4)
    fuselage = cylinder(ctx, f"{name}.fuselage", 2.1, 34.0, (0, 0, 3.6), paint, segments=12, rot=(math.pi / 2, 0, 0), bevel=0.3)
    parent(fuselage, root)
    nose = cone(ctx, f"{name}.nose", 2.1, 5.0, (0, 17.0, 3.6), paint, segments=12, tip=0.4)
    nose.rotation_euler = (math.radians(-90), 0, 0)
    parent(nose, root)
    tail_cone = cone(ctx, f"{name}.tailcone", 2.1, 7.0, (0, -17.0, 4.2), paint, segments=12, tip=0.5)
    tail_cone.rotation_euler = (math.radians(90), 0, 0)
    parent(tail_cone, root)
    for sign in (-1, 1):
        wing = box(ctx, f"{name}.wing{sign}", (17.0, 5.0, 0.5), (sign * 9.5, -1.0, 2.6), paint, bevel=0.1)
        wing.rotation_euler = (0, 0, sign * math.radians(-18))
        parent(wing, root)
        engine = cylinder(ctx, f"{name}.engine{sign}", 1.2, 4.5, (sign * 6.5, 1.5, 1.6), ctx.mat("steel", roughness=0.4), segments=10, rot=(math.pi / 2, 0, 0))
        parent(engine, root)
        stab = box(ctx, f"{name}.stab{sign}", (6.0, 2.4, 0.3), (sign * 4.0, -17.5, 4.8), paint)
        stab.rotation_euler = (0, 0, sign * math.radians(-25))
        parent(stab, root)
    fin = box(ctx, f"{name}.fin", (0.4, 5.5, 7.0), (0, -17.0, 8.5), accent, bevel=0.1)
    fin.rotation_euler = (math.radians(-28), 0, 0)
    parent(fin, root)
    stripe = box(ctx, f"{name}.stripe", (4.3, 24.0, 0.6), (0, 0, 3.0), accent)
    parent(stripe, root)
    for dx, dy in ((0, 12.0), (-2.5, -1.5), (2.5, -1.5)):
        gear = cylinder(ctx, f"{name}.gear", 0.5, 0.6, (dx, dy, 0.5), ctx.mat("black"), segments=8, rot=(0, math.pi / 2, 0))
        parent(gear, root)
        strut = box(ctx, f"{name}.strut", (0.3, 0.3, 1.2), (dx, dy, 0.9), ctx.mat("steel"), anchor="base")
        parent(strut, root)
    ctx.objects[name] = root
    ctx.tag("plane", root)
    return root


def drone(ctx, name, loc, path=None, start=0.0, end=None, speed=8.0):
    root = empty(ctx, name, loc)
    body = box(ctx, f"{name}.body", (0.5, 0.5, 0.2), (0, 0, 0), ctx.mat("dark_steel"), bevel=0.04)
    parent(body, root)
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        arm = box(ctx, f"{name}.arm", (0.9, 0.08, 0.06), (sx * 0.35, sy * 0.35, 0), ctx.mat("dark_steel"), rot=(0, 0, math.atan2(sy, sx)))
        parent(arm, root)
        prop = cylinder(ctx, f"{name}.prop", 0.32, 0.02, (sx * 0.7, sy * 0.7, 0.08), ctx.mat("steel", roughness=0.3, alpha=0.5), segments=10)
        parent(prop, root)
        key(prop, "rotation_euler", 1, (0, 0, 0))
        key(prop, "rotation_euler", ctx.frames, (0, 0, math.tau * 20 * ctx.frames / ctx.fps))
        set_interp(prop, "LINEAR")
    beacon = box(ctx, f"{name}.beacon", (0.12, 0.12, 0.08), (0, 0, 0.14), ctx.palette.emissive(f"{name} beacon", "beacon_red", 6.0))
    parent(beacon, root)
    key(root, "location", 1, loc)
    from studio.blender.primitives import add_noise

    add_noise(root, "location", 0.4, 1, ctx.frames, scale=4.0)
    if path:
        vehicles.drive(ctx, root, path, start, end, speed, z=loc[2])
    ctx.tag("drone", root)
    return root


def army_truck(ctx, name, loc, rot=0.0, lit=False):
    root = vehicles.lorry(ctx, name, loc, rot, "olive", "flatbed", lit=lit)
    canvas = box(ctx, f"{name}.canvas", (2.4, 7.0, 2.4), (0, -0.9, 1.0), ctx.mat("olive", roughness=0.9), bevel=0.25, anchor="base")
    parent(canvas, root)
    return root


def loudspeaker_van(ctx, name, loc, rot=0.0, lit=False):
    root = vehicles.van(ctx, name, loc, rot, "white", "van", lit=lit)
    for sx in (-0.5, 0.5):
        horn = cone(ctx, f"{name}.horn{sx}", 0.45, 0.9, (sx, 0.5, 2.5), ctx.mat("dark_steel"), segments=8, tip=0.12)
        horn.rotation_euler = (math.radians(-80), 0, 0)
        parent(horn, root)
    return root


def police_car(ctx, name, loc, rot=0.0, lit=False):
    root = vehicles.car(ctx, name, loc, rot, "white", lit=lit)
    bar = box(ctx, f"{name}.bar", (1.3, 0.3, 0.18), (0, -0.2, 1.55), ctx.palette.emissive(f"{name} beacon", "beacon_blue", 0.0), bevel=0.03)
    parent(bar, root)
    ctx.tag("beacon", bar)
    return root
