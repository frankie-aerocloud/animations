"""Small props: taps, containers, shelves, street furniture, pipes, animals and signage."""

from __future__ import annotations

import math

from mathutils import Vector

import bpy

from studio.blender.primitives import add_noise, box, cone, cylinder, ico, key, multi_box, parent, set_interp, text


def tap(ctx, name, loc, rot=0.0, scale=1.0):
    """Chrome mixer tap; the spout tip is registered as anchor '<name>.spout'."""
    x, y, z = loc
    steel = ctx.mat("steel", roughness=0.25, metallic=0.9)
    root = cylinder(ctx, f"{name}.base", 0.035 * scale, 0.22 * scale, (x, y, z), steel, segments=10, anchor="base")
    neck = box(ctx, f"{name}.neck", (0.04 * scale, 0.24 * scale, 0.04 * scale), (0, 0.10 * scale, 0.22 * scale), steel, bevel=0.012)
    parent(neck, root)
    spout = cylinder(ctx, f"{name}.spout", 0.02 * scale, 0.08 * scale, (0, 0.21 * scale, 0.17 * scale), steel, segments=8, anchor="top")
    parent(spout, root)
    lever = box(ctx, f"{name}.lever", (0.12 * scale, 0.03 * scale, 0.025 * scale), (0.0, -0.01, 0.25 * scale), steel, bevel=0.008)
    parent(lever, root)
    root.rotation_euler = (0, 0, rot)
    ctx.anchor(f"{name}.spout", (x, y + 0.21 * scale * math.cos(rot), z + 0.09 * scale))
    return root


def drip(ctx, name, loc, radius=0.02):
    """A single water drop; animate with a 'move' event."""
    drop = cylinder(ctx, name, radius, radius * 1.6, loc, ctx.palette.water(f"{name} drop", "pool", roughness=0.05), segments=8, radius2=radius * 0.4)
    ctx.tag("drop", drop)
    return drop


def sink(ctx, name, loc, size=(0.9, 0.5)):
    x, y, z = loc
    w, d = size
    box(ctx, f"{name}.rim", (w, d, 0.04), (x, y, z), ctx.mat("steel", roughness=0.3, metallic=0.8), bevel=0.01, anchor="base")
    box(ctx, f"{name}.basin", (w - 0.12, d - 0.12, 0.3), (x, y, z - 0.28), ctx.mat("dark_steel", roughness=0.35), anchor="base")


def held(ctx, name, kind):
    """A hand prop built at the origin, to be parented to a character's torso."""
    if kind == "bottle":
        body = cylinder(ctx, name, 0.045, 0.28, (0, 0, 0), ctx.palette.water(f"{name} pet", "bottle", roughness=0.15), segments=10, anchor="base")
        cap = cylinder(ctx, f"{name}.cap", 0.022, 0.03, (0, 0, 0.28), ctx.mat("cap"), segments=8, anchor="base")
        parent(cap, body)
        return body
    if kind == "bucket":
        return cylinder(ctx, name, 0.16, 0.3, (0, 0, 0), ctx.mat("jerrycan", roughness=0.5), segments=12, anchor="base", radius2=0.12)
    if kind == "box":
        return box(ctx, name, (0.42, 0.32, 0.3), (0, 0, 0.15), ctx.mat("sand", roughness=0.9), bevel=0.01)
    if kind == "pan":
        body = cylinder(ctx, name, 0.16, 0.12, (0, 0, 0), ctx.mat("steel", roughness=0.3, metallic=0.8), segments=14, anchor="base")
        handle = box(ctx, f"{name}.handle", (0.04, 0.22, 0.03), (0, -0.24, 0.1), ctx.mat("black"))
        parent(handle, body)
        return body
    return jerrycan(ctx, name, (0, 0, 0))


def jerrycan(ctx, name, loc, colour="jerrycan", rot=0.0):
    x, y, z = loc
    mat = ctx.mat(colour, roughness=0.55)
    body = box(ctx, name, (0.34, 0.17, 0.42), (x, y, z), mat, bevel=0.025, anchor="base", rot=(0, 0, rot))
    handle = box(ctx, f"{name}.handle", (0.22, 0.05, 0.04), (0, 0, 0.47), mat, bevel=0.012)
    parent(handle, body)
    for dx in (-0.09, 0.09):
        post = box(ctx, f"{name}.post", (0.04, 0.05, 0.07), (dx, 0, 0.43), mat)
        parent(post, body)
    spout = cylinder(ctx, f"{name}.spout", 0.03, 0.06, (0.13, 0, 0.42), ctx.mat("black"), segments=8, anchor="base")
    parent(spout, body)
    return body


def bottle_pallet(ctx, name, loc, layers=4, rot=0.0):
    """Pallet of shrink-wrapped bottles as one mesh; tagged 'bottles' so it can be depleted."""
    x, y, z = loc
    boxes = [((0, 0, 0.07), (1.2, 1.0, 0.14), 1)]
    for layer in range(layers):
        for i in range(5):
            for j in range(4):
                boxes.append(((-0.48 + i * 0.24, -0.36 + j * 0.24, 0.14 + layer * 0.3 + 0.14), (0.2, 0.2, 0.28), 0))
                boxes.append(((-0.48 + i * 0.24, -0.36 + j * 0.24, 0.14 + layer * 0.3 + 0.29), (0.08, 0.08, 0.03), 2))
    obj = multi_box(ctx, name, boxes, [ctx.palette.water(f"{name} pet", "bottle", roughness=0.2), ctx.mat("trunk"), ctx.mat("cap")], (x, y, z), (0, 0, rot))
    ctx.tag("bottles", obj)
    return obj


def shelf_unit(ctx, name, loc, length=12.0, levels=4, rot=0.0, stock=1.0, groups=6, product="bottle"):
    """Retail gondola; bottles are split into `groups` meshes along the length (tagged 'bottles')."""
    x, y, z = loc
    frame = ctx.mat("steel", roughness=0.5)
    boxes = [((0, 0, 0.05), (length, 1.0, 0.1), 0), ((0, 0.45, 1.1), (length, 0.08, 2.2), 0)]
    for level in range(levels):
        zz = 0.1 + level * 0.52
        boxes.append(((0, 0.05, zz), (length, 0.9, 0.05), 0))
    for ux in (-length / 2 + 0.05, length / 2 - 0.05):
        boxes.append(((ux, 0.05, 1.1), (0.08, 0.9, 2.2), 0))
    unit = multi_box(ctx, name, boxes, [frame], (x, y, z), (0, 0, rot), bevel=0.01)
    pet = ctx.palette.water(f"{name} pet", "bottle", roughness=0.18)
    cap = ctx.mat("cap")
    label = ctx.mat("teal")
    per_group = length / groups
    for g in range(groups):
        items = []
        gx = -length / 2 + per_group * (g + 0.5)
        for level in range(levels):
            zz = 0.125 + level * 0.52
            n = max(1, int(per_group / 0.17))
            for i in range(n):
                if ctx.rng.random() > stock:
                    continue
                bx = gx - per_group / 2 + 0.085 + i * 0.17
                for by in (-0.28, -0.05, 0.18):
                    items.append(((bx, by, zz + 0.16), (0.12, 0.12, 0.32), 0))
                    items.append(((bx, by, zz + 0.34), (0.06, 0.06, 0.04), 1))
                    items.append(((bx, by, zz + 0.15), (0.125, 0.125, 0.1), 2))
        if items:
            group = multi_box(ctx, f"{name}.stock{g}", items, [pet, cap, label], (x, y, z), (0, 0, rot))
            group["order"] = g
            ctx.tag("bottles", group)
    return unit


def trolley(ctx, name, loc, rot=0.0):
    x, y, z = loc
    steel = ctx.mat("steel", roughness=0.4, metallic=0.6)
    basket = box(ctx, name, (0.6, 0.95, 0.5), (x, y, z + 0.45), steel, bevel=0.02, rot=(0, 0, rot))
    handle = box(ctx, f"{name}.handle", (0.64, 0.04, 0.04), (0, -0.5, 0.42), ctx.mat("red"), bevel=0.01)
    parent(handle, basket)
    for dx in (-0.25, 0.25):
        for dy in (-0.4, 0.4):
            wheel = cylinder(ctx, f"{name}.wheel", 0.06, 0.04, (dx, dy, -0.4), ctx.mat("black"), segments=8, rot=(0, math.pi / 2, 0))
            parent(wheel, basket)
    return basket


def tent(ctx, name, loc, size=(6.0, 4.0), height=3.0, rot=0.0, colour="canvas"):
    x, y, z = loc
    w, d = size
    canvas = ctx.mat(colour, roughness=0.9)
    roof = cone(ctx, f"{name}.roof", max(w, d) * 0.72, height * 0.45, (x, y, z + height * 0.6), canvas, segments=4, tip=0.0)
    roof.rotation_euler = (0, 0, rot + math.pi / 4)
    roof.scale = (w / max(w, d), d / max(w, d), 1.0)
    for sx in (-1, 1):
        for sy in (-1, 1):
            cylinder(ctx, f"{name}.pole", 0.05, height * 0.6, (x + sx * w / 2 * 0.9, y + sy * d / 2 * 0.9, z), ctx.mat("steel"), segments=6, anchor="base")
    box(ctx, f"{name}.table", (w * 0.6, 0.8, 0.08), (x, y, z + 0.9), ctx.mat("white"), anchor="base")
    return roof


def barrier(ctx, name, loc, rot=0.0, length=2.4):
    x, y, z = loc
    steel = ctx.mat("steel", roughness=0.4)
    rail = box(ctx, name, (length, 0.05, 1.1), (x, y, z), steel, bevel=0.01, anchor="base", rot=(0, 0, rot))
    for dx in (-length / 2 + 0.2, length / 2 - 0.2):
        foot = box(ctx, f"{name}.foot", (0.12, 0.6, 0.06), (dx, 0, 0.0), steel, anchor="base")
        parent(foot, rail)
    return rail


def lamp_post(ctx, name, loc, height=7.0, rot=0.0, lit=False):
    x, y, z = loc
    steel = ctx.mat("dark_steel")
    pole = cylinder(ctx, name, 0.12, height, (x, y, z), steel, segments=8, anchor="base")
    arm = box(ctx, f"{name}.arm", (0.12, 1.6, 0.12), (0, 0.7, height - 0.1), steel, anchor="base")
    parent(arm, pole)
    lamp_mat = ctx.mat("lamp", emission=5.0 if lit else 0.0)
    head = box(ctx, f"{name}.lamp", (0.3, 0.6, 0.18), (0, 1.3, height - 0.2), lamp_mat, bevel=0.02)
    parent(head, pole)
    if lit:
        if lamp_mat not in ctx.tags.get("street_lights", []):
            ctx.tag("street_lights", lamp_mat)
        data = bpy.data.lights.new(f"{name}.light", "POINT")
        data.energy = 600.0
        data.color = (1.0, 0.82, 0.55)
        data.shadow_soft_size = 0.6
        light = bpy.data.objects.new(f"{name}.light", data)
        light.location = (0, 1.3, height - 0.5)
        ctx.link(light)
        parent(light, pole)
        ctx.tag("street_lamps", light)
    pole.rotation_euler = (0, 0, rot)
    return pole


def fire(ctx, name, loc, size=3.0, flames=True, smoke=True, light=True):
    """Flickering low-poly flames, a rising smoke column and an orange point light (tags: flame, smoke, fire_light)."""
    x, y, z = loc
    rng = ctx.rng
    hot = ctx.palette.emissive(f"{name} hot", "yellow", 4.5)
    warm = ctx.palette.emissive(f"{name} warm", "orange", 3.2)
    if flames:
        for i in range(6):
            radius = size * rng.uniform(0.45, 1.0)
            height = size * rng.uniform(1.6, 3.4)
            flame = cone(ctx, f"{name}.flame{i}", radius, height, (x + rng.uniform(-size, size) * 0.8, y + rng.uniform(-size, size) * 0.8, z), hot if i % 2 else warm, segments=6, tip=0.05)
            flame.rotation_euler = (rng.uniform(-0.18, 0.18), rng.uniform(-0.18, 0.18), 0.0)
            key(flame, "scale", 1, (1.0, 1.0, 1.0))
            add_noise(flame, "scale", 0.28, 1, ctx.frames, scale=2.0, phase=i * 3.1)
            ctx.tag("flame", flame)
    if smoke:
        smoke_mat = ctx.mat("rock" if flames else "stone", roughness=1.0, alpha=0.72)
        for i in range(7):
            puff = ico(ctx, f"{name}.smoke{i}", size * (0.8 + 0.3 * i), (x + i * size * 0.5, y + i * size * 0.35, z + size * 1.8 + i * size * 1.7), smoke_mat, subdiv=2, scale=(1.3, 1.2, 0.9), smooth=True)
            key(puff, "location", 1)
            puff.location.z += size * 2.5
            puff.location.x += size * 1.2
            key(puff, "location", ctx.frames)
            set_interp(puff, "LINEAR")
            ctx.tag("smoke", puff)
    if light and flames:
        data = bpy.data.lights.new(f"{name}.light", "POINT")
        data.energy = 3000.0 * size
        data.color = (1.0, 0.45, 0.12)
        data.shadow_soft_size = size
        lamp = bpy.data.objects.new(f"{name}.light", data)
        lamp.location = (x, y, z + size * 1.5)
        ctx.link(lamp)
        key(data, "energy", 1)
        add_noise(data, "energy", 1000.0 * size, 1, ctx.frames, scale=3.0)
        ctx.tag("fire_light", lamp)
    ctx.anchor(name, (x, y, z + size * 1.5))


def stretcher(ctx, name, loc, rot=0.0, occupied=True):
    x, y, z = loc
    frame = box(ctx, name, (0.7, 2.0, 0.08), (x, y, z + 0.6), ctx.mat("white"), bevel=0.01, rot=(0, 0, rot))
    for dx, dy in ((-0.3, -0.85), (0.3, -0.85), (-0.3, 0.85), (0.3, 0.85)):
        leg = box(ctx, f"{name}.leg", (0.05, 0.05, 0.6), (dx, dy, -0.6), ctx.mat("dark_steel"), anchor="base")
        parent(leg, frame)
    if occupied:
        body = box(ctx, f"{name}.blanket", (0.6, 1.7, 0.28), (0, -0.1, 0.18), ctx.mat("teal", roughness=0.9), bevel=0.06)
        parent(body, frame)
        head = box(ctx, f"{name}.head", (0.24, 0.24, 0.24), (0, 0.85, 0.16), ctx.mat("skin_2"), bevel=0.05)
        parent(head, frame)
    return frame


def bench(ctx, name, loc, rot=0.0):
    x, y, z = loc
    wood = ctx.mat("trunk", roughness=0.8)
    seat = box(ctx, name, (1.8, 0.5, 0.08), (x, y, z + 0.45), wood, bevel=0.01, rot=(0, 0, rot))
    back = box(ctx, f"{name}.back", (1.8, 0.08, 0.45), (0, 0.22, 0.25), wood, bevel=0.01, anchor="base")
    parent(back, seat)
    for dx in (-0.75, 0.75):
        leg = box(ctx, f"{name}.leg", (0.08, 0.45, 0.45), (dx, 0, -0.45), ctx.mat("dark_steel"), anchor="base")
        parent(leg, seat)
    return seat


def pipe(ctx, name, points, radius=0.5, colour="steel"):
    """Cylinders along a polyline of 3D points, with joints."""
    mat = ctx.mat(colour, roughness=0.45, metallic=0.4)
    for i in range(1, len(points)):
        a, b = Vector(points[i - 1]), Vector(points[i])
        seg = cylinder(ctx, f"{name}.{i}", radius, (b - a).length, a, mat, segments=12, anchor="base")
        seg.rotation_euler = (b - a).to_track_quat("Z", "Y").to_euler()
        cylinder(ctx, f"{name}.joint{i}", radius * 1.25, radius * 1.1, a, mat, segments=12)
    return None


def valve(ctx, name, loc, radius=0.7, rot=(0, 0, 0)):
    x, y, z = loc
    red = ctx.mat("red", roughness=0.5)
    wheel = cylinder(ctx, name, radius, 0.08, (x, y, z), red, segments=18, rot=rot)
    for i in range(4):
        spoke = box(ctx, f"{name}.spoke{i}", (radius * 1.9, 0.07, 0.06), (0, 0, 0), red)
        spoke.rotation_euler = (0, 0, i * math.pi / 4)
        parent(spoke, wheel)
    ctx.objects[name] = wheel
    return wheel


def sprinkler(ctx, name, loc, height=1.4, spray=True):
    x, y, z = loc
    cylinder(ctx, f"{name}.post", 0.05, height, (x, y, z), ctx.mat("dark_steel"), segments=6, anchor="base")
    if spray:
        jet = cone(ctx, f"{name}.spray", 2.8, 0.9, (x, y, z + height - 0.9), ctx.palette.water(f"{name} spray", "pool", alpha=0.45), segments=12, tip=0.05)
        jet.rotation_euler = (math.pi, 0, 0)
        jet.location = (x, y, z + height)
        ctx.tag("spray", jet)


def cow(ctx, name, loc, rot=0.0, colour="white"):
    x, y, z = loc
    hide = ctx.mat(colour, roughness=0.85)
    body = box(ctx, name, (0.75, 1.5, 0.8), (x, y, z + 0.95), hide, bevel=0.08, rot=(0, 0, rot))
    head = box(ctx, f"{name}.head", (0.42, 0.55, 0.42), (0, 0.95, 0.05), hide, bevel=0.06)
    parent(head, body)
    for dx in (-0.22, 0.22):
        ear = box(ctx, f"{name}.ear", (0.16, 0.08, 0.1), (dx * 1.3, 0.8, 0.28), hide)
        parent(ear, body)
    for dx in (-0.25, 0.25):
        for dy in (-0.55, 0.55):
            leg = box(ctx, f"{name}.leg", (0.18, 0.2, 0.75), (dx, dy, -0.4), ctx.mat("roof_dark"), anchor="top")
            parent(leg, body)
    patch = box(ctx, f"{name}.patch", (0.76, 0.5, 0.4), (0, -0.2, 0.1), ctx.mat("roof_dark"))
    parent(patch, body)
    return body


def fence(ctx, name, start, end, z=0.0, height=1.2, post_gap=3.0):
    sx, sy = start
    ex, ey = end
    length = math.hypot(ex - sx, ey - sy)
    angle = math.atan2(ey - sy, ex - sx)
    wood = ctx.mat("trunk")
    boxes = []
    n = max(2, int(length / post_gap))
    for i in range(n + 1):
        boxes.append(((-length / 2 + length * i / n, 0, height / 2), (0.14, 0.14, height), 0))
    for rail_z in (height * 0.45, height * 0.85):
        boxes.append(((0, 0, rail_z), (length, 0.06, 0.1), 0))
    return multi_box(ctx, name, boxes, [wood], ((sx + ex) / 2, (sy + ey) / 2, z), (0, 0, angle))


def road(ctx, name, start, end, width=8.0, z=0.02, lines=True):
    """Straight asphalt strip with dashed centre line as a merged mesh."""
    sx, sy = start
    ex, ey = end
    length = math.hypot(ex - sx, ey - sy)
    angle = math.atan2(ey - sy, ex - sx)
    boxes = [((0, 0, 0), (length, width, 0.06), 0)]
    if lines:
        n = int(length / 6)
        for i in range(n):
            boxes.append(((-length / 2 + 6 * (i + 0.5), 0, 0.035), (3.0, 0.22, 0.01), 1))
        for side in (-1, 1):
            boxes.append(((0, side * (width / 2 - 0.3), 0.035), (length, 0.18, 0.01), 1))
    obj = multi_box(ctx, name, boxes, [ctx.mat("asphalt", roughness=0.85), ctx.mat("road_line")], ((sx + ex) / 2, (sy + ey) / 2, z), (0, 0, angle))
    ctx.tag("road", obj)
    return obj


def pavement(ctx, name, loc, size, z=0.0):
    return box(ctx, name, (size[0], size[1], 0.18), (loc[0], loc[1], z), ctx.mat("pavement"), bevel=0.04, anchor="base")


def container(ctx, name, loc, rot=0.0, colour=None):
    colours = ("red", "orange", "teal", "navy", "rust", "yellow")
    return box(ctx, name, (2.4, 6.0, 2.6), loc, ctx.mat(colour or ctx.rng.choice(colours), roughness=0.7), bevel=0.04, anchor="base", rot=(0, 0, rot))


def sign_text(ctx, name, body, loc, size=0.6, rot=(math.pi / 2, 0, 0), colour="white", emission=0.0, weight=0.01):
    mat = ctx.mat(colour, emission=emission) if not emission else ctx.palette.emissive(f"{name} glow", colour, emission)
    return text(ctx, name, body, size, mat, loc, rot, weight=weight, extrude=0.02)


def cross(ctx, name, loc, size=3.0, rot=(0, 0, 0), colour="red"):
    """Red cross emblem (two boxes) for hospitals and ambulances."""
    mat = ctx.mat(colour, roughness=0.5)
    boxes = [((0, 0, 0), (size, 0.12, size / 3), 0), ((0, 0, 0), (size / 3, 0.12, size), 0)]
    return multi_box(ctx, name, boxes, [mat], loc, rot)
