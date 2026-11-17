"""Los Angeles assets for "When The Wind Took Everything": tall fan palms that bend, snap and
uproot, stucco strip malls and tile-roofed houses whose roofs can tear away, wooden power poles
with sagging lines, downtown towers that can burst their windows, freeway decks, an interchange,
green freeway signs, a pier with a Ferris wheel and coaster, the arched airport landmark, and fire
trucks. Shapes are generic: no real logos, signs or operator liveries.

Wind blows toward local -X (Santa Ana winds run east to west toward the ocean)."""

from __future__ import annotations

import math
import random

from studio.assets import props, wind
from studio.assets.meshes import merged_boxes
from studio.assets.vehicles import _lights, _wheels
from studio.blender.primitives import add_noise, box, cone, cylinder, empty, key, mesh_from_pydata, multi_box, multi_shape, parent, set_interp

STUCCO = ("stucco_cream", "stucco_peach", "stucco_mint", "stucco_pink", "stucco_sand", "stucco_white")
SHOP_SIGNS = ("TACOS", "DONUTS", "LIQUOR", "NAILS", "PHARMACY", "BURGERS", "LAUNDRY", "COFFEE", "AUTO PARTS", "PIZZA", "MOTEL", "JUICE", "PHO", "DENTIST")


# ----- palms -----------------------------------------------------------------------------------
def palm(ctx, name, loc, height=22.0, wind_level=0.0, gust_at=0.0, uproot_at=None, scale=1.0):
    """A tall, thin fan palm built from stacked trunk segments (each pivots at its base) so it can
    bend downwind. wind_level 0-1 sets how hard it bends after `gust_at`; `uproot_at` tears the
    whole tree out of the ground and throws it."""
    rng = ctx.rng
    h = height * scale * rng.uniform(0.9, 1.1)
    root = empty(ctx, name, loc)
    trunk_mat = ctx.mat("palm_trunk", roughness=0.9)
    segments = 6
    seg = h / segments
    parent_obj = root
    pieces = []
    for i in range(segments):
        r0 = 0.34 - 0.12 * i / segments
        piece = cylinder(ctx, f"{name}.seg{i}", r0 * scale, seg, (0, 0, 0), trunk_mat, segments=7, anchor="base", radius2=(r0 - 0.02) * scale)
        parent(piece, parent_obj)
        piece.location = (0, 0, 0 if i == 0 else seg)
        pieces.append(piece)
        parent_obj = piece
    crown = empty(ctx, f"{name}.crown", (0, 0, 0))
    parent(crown, pieces[-1])
    crown.location = (0, 0, seg)
    skirt = cone(ctx, f"{name}.skirt", 0.75 * scale, 1.6 * scale, (0, 0, -1.4 * scale), ctx.mat("frond_dead", roughness=1.0), segments=8, anchor="base", tip=0.45 * scale)
    parent(skirt, crown)
    skirt.location = (0, 0, -1.4 * scale)
    fronds = []
    for k in range(12):
        a = k * math.tau / 12 + rng.uniform(-0.15, 0.15)
        tilt = rng.uniform(-25, 10)
        fronds.append(((math.cos(a) * 1.1 * scale, math.sin(a) * 1.1 * scale, 0.2 * scale), (2.2 * scale, 0.9 * scale, 0.06), 0, a, tilt))
    verts, faces = [], []
    for (px, py, pz), (sx, sy, sz), _, a, tilt in fronds:
        c, s = math.cos(a), math.sin(a)
        t = math.radians(tilt)
        base = len(verts)
        for dx, dy, dz in ((0, -sy / 2, 0), (sx, -sy / 2, sx * math.sin(t)), (sx, sy / 2, sx * math.sin(t)), (0, sy / 2, 0)):
            verts.append((px + dx * c - dy * s - 0.9 * scale * c, py + dx * s + dy * c - 0.9 * scale * s, pz + dz))
        faces.append((base, base + 1, base + 2, base + 3))
    leaves = mesh_from_pydata(ctx, f"{name}.fronds", verts, faces, [ctx.mat("palm_leaf", roughness=0.8)])
    parent(leaves, crown)
    if wind_level > 0:
        g0 = max(1, ctx.frame(gust_at))
        g1 = g0 + max(2, round(0.5 * ctx.fps))
        total = math.radians(28.0) * wind_level
        for i, piece in enumerate(pieces[1:], 1):
            key(piece, "rotation_euler", 1, (0.0, 0.0, 0.0))
            key(piece, "rotation_euler", g0, (0.0, 0.0, 0.0))
            key(piece, "rotation_euler", g1, (0.0, -total * (i / segments) * 0.55, 0.0))
            add_noise(piece, "rotation_euler", math.radians(5.0) * wind_level, g1, ctx.frames, scale=6.0, phase=i * 0.7)
        key(crown, "rotation_euler", g0, (0.0, 0.0, 0.0))
        key(crown, "rotation_euler", g1, (0.0, -math.radians(55.0) * wind_level, 0.0))
        add_noise(crown, "rotation_euler", math.radians(10.0) * wind_level, g1, ctx.frames, scale=3.0, phase=rng.uniform(0, 9))
    else:
        add_noise(crown, "rotation_euler", math.radians(1.5), 1, ctx.frames, scale=30.0, phase=rng.uniform(0, 9))
    if uproot_at is not None:
        wind.fly(ctx, root, uproot_at, uproot_at + rng.uniform(1.6, 2.4), (-rng.uniform(40, 70), rng.uniform(-8, 8), 0.0), spin=(0.0, -0.25, rng.uniform(-0.3, 0.3)), arc=rng.uniform(6, 14))
    ctx.tag("palm", root)
    return root


def fallen_palm(ctx, name, loc, heading=0.0, scale=1.0):
    """A palm lying across the ground (the morning after)."""
    root = palm(ctx, name, loc, 20.0, 0.0, scale=scale)
    root.rotation_euler = (0.0, -math.radians(88.0), heading)
    root.location = (loc[0], loc[1], loc[2] + 0.35)
    return root


# ----- buildings -------------------------------------------------------------------------------
def strip_mall(ctx, name, origin, count, rot=0.0, seed=0, lit=None, ripped=0.0, signs=True, burst_at=None):
    """A row of one- and two-storey stucco shops with awnings and parapet signs, running along local
    +X with fronts facing local -Y. `ripped` is the share of shopfronts torn open (dark gaps, no
    awnings); `burst_at` makes the remaining windows burst at that time."""
    rng = random.Random(seed)
    ox, oy, oz = origin
    mats = [ctx.mat(c, roughness=0.9) for c in STUCCO]  # 0..5
    mats += [ctx.palette.glass(f"{name} glass", "glass_dark"), ctx.mat("roof_flat", roughness=0.9), ctx.mat("void", roughness=1.0), lit or ctx.palette.glass(f"{name} glass2", "glass_dark")]  # 6 glass, 7 roof, 8 void, 9 lit
    mats += [ctx.mat(c, roughness=0.7) for c in ("awning_red", "awning_green", "awning_blue", "awning_orange")]  # 10..13
    boxes = []
    x = 0.0
    windows = []
    c, s = math.cos(rot), math.sin(rot)
    for i in range(count):
        w = rng.uniform(7.0, 12.0)
        h = rng.choice((4.8, 5.5, 8.5))
        cx = x + w / 2
        wall = rng.randrange(6)
        boxes.append(((cx, 8.0, h / 2), (w - 0.05, 16.0, h), wall))
        boxes.append(((cx, 0.0, h + 0.5), (w, 0.4, 1.0), wall))  # parapet
        boxes.append(((cx, 8.0, h + 0.05), (w - 0.6, 15.0, 0.1), 7))
        torn = rng.random() < ripped
        if torn:
            boxes.append(((cx, -0.05, 1.7), (w - 1.2, 0.12, 3.0), 8))
        else:
            boxes.append(((cx, -0.06, 1.8), (w - 1.6, 0.1, 2.8), 9 if lit is not None and rng.random() < 0.7 else 6))
            boxes.append(((cx, -1.0, 3.5), (w - 0.8, 2.0, 0.12), 10 + rng.randrange(4)))
            windows.append((cx, 1.8))
        if h > 7:
            for k in range(3):
                boxes.append(((x + w * (k + 0.5) / 3, -0.06, 6.4), (1.6, 0.1, 1.4), 9 if lit is not None and rng.random() < 0.5 else 6))
        if signs:
            label = SHOP_SIGNS[(seed * 5 + i * 3) % len(SHOP_SIGNS)]
            sx, sy = ox + cx * c - (-0.25) * s, oy + cx * s + (-0.25) * c
            props.sign_text(ctx, f"{name}.sign{i}", label, (sx, sy, oz + h + 0.15), size=0.7, rot=(math.pi / 2, 0, rot), colour="sign_red" if i % 2 else "sign_blue")
        x += w
    row = merged_boxes(ctx, name, boxes, mats, (ox, oy, oz), (0, 0, rot))
    if burst_at is not None:
        for k, (wx, wz) in enumerate(windows):
            if rng.random() < 0.7:
                px, py = ox + wx * c, oy + wx * s
                # local -Y (the street side) is (sin rot, -cos rot) in world space
                wind.glass_burst(ctx, f"{name}.burst{k}", (px + s * 0.3, py - c * 0.3, oz + wz), (s, -c), burst_at + rng.uniform(0.0, 0.8), count=30, spread=4.0)
    ctx.tag("shops", row)
    return {"row": row, "length": x}


def house(ctx, name, loc, rot=0.0, seed=0, lit=None, roof_torn_at=None, roofless=False):
    """Single-storey stucco house with a red tile hip roof, garage and front lawn; the roof is its
    own object so the wind can tear it off (`roof_torn_at`) or leave it gone (`roofless`)."""
    rng = random.Random(seed)
    w, d, h = rng.uniform(11, 15), rng.uniform(9, 12), 3.4
    wall = ctx.mat(rng.choice(STUCCO), roughness=0.9)
    glass = lit or ctx.palette.glass(f"{name} glass", "glass_dark")
    boxes = [((0, 0, h / 2), (w, d, h), 0), ((-w * 0.25, -d / 2 - 0.05, 1.3), (1.8, 0.1, 1.3), 1), ((w * 0.1, -d / 2 - 0.05, 1.3), (1.4, 0.1, 1.3), 1), ((w * 0.36, -d / 2 - 0.06, 1.2), (3.0, 0.1, 2.3), 2), ((0, -d / 2 - 4.5, 0.03), (w + 4, 9.0, 0.06), 3), ((w * 0.36, -d / 2 - 4.5, 0.05), (3.4, 9.0, 0.06), 4)]
    if roofless:
        boxes.append(((0, 0, h - 0.1), (w - 0.6, d - 0.6, 0.2), 5))
    body = multi_box(ctx, name, boxes, [wall, glass, ctx.mat("garage_door", roughness=0.6), ctx.mat("lawn", roughness=0.9), ctx.mat("concrete", roughness=0.8), ctx.mat("void", roughness=1.0)], loc, (0, 0, rot))
    roof = None
    if not roofless:
        ridge = h + 2.2
        verts = [(-w / 2 - 0.5, -d / 2 - 0.5, h), (w / 2 + 0.5, -d / 2 - 0.5, h), (w / 2 + 0.5, d / 2 + 0.5, h), (-w / 2 - 0.5, d / 2 + 0.5, h), (-w / 4, 0, ridge), (w / 4, 0, ridge)]
        faces = [(0, 1, 5, 4), (2, 3, 4, 5), (1, 2, 5), (3, 0, 4), (0, 3, 2, 1)]
        roof = mesh_from_pydata(ctx, f"{name}.roof", verts, faces, [ctx.mat("roof_tile", roughness=0.8)], loc, (0, 0, rot))
        if roof_torn_at is not None:
            roof.location = (loc[0], loc[1], loc[2])
            wind.fly(ctx, roof, roof_torn_at, roof_torn_at + rng.uniform(1.2, 2.0), (-rng.uniform(35, 60), rng.uniform(-10, 10), rng.uniform(8, 20)), spin=(rng.uniform(0.3, 0.8), rng.uniform(0.6, 1.2), rng.uniform(-0.3, 0.3)), arc=rng.uniform(8, 16))
    ctx.tag("house", body)
    return body, roof


# ----- streets ---------------------------------------------------------------------------------
def us_road(ctx, name, length, lanes_each=3, lane=3.6, sidewalk=4.0, centre=(0.0, 0.0), rot=0.0, turn_lane=True, parkway=0.0):
    """US arterial along local Y: dashed white lane lines, double yellow centre (or a turn lane),
    concrete kerbs and sidewalks, and an optional grass parkway strip between kerb and sidewalk."""
    half = lanes_each * lane + (1.8 if turn_lane else 0.15)
    boxes = [((0, 0, -0.03), (2 * half, length, 0.06), 0)]
    for side in (-1, 1):
        for k in range(1, lanes_each):
            off = side * ((1.8 if turn_lane else 0.15) + k * lane)
            n = int(length / 12)
            for j in range(n):
                boxes.append(((off, -length / 2 + 12 * (j + 0.5), 0.004), (0.14, 3.0, 0.01), 1))
        boxes.append(((side * 0.12, 0, 0.005), (0.1, length, 0.01), 2))
        if turn_lane:
            boxes.append(((side * 1.7, 0, 0.005), (0.12, length, 0.01), 2))
        kx = side * (half + 0.1)
        boxes.append(((kx, 0, 0.08), (0.2, length, 0.16), 3))
        if parkway:
            boxes.append(((side * (half + 0.2 + parkway / 2), 0, 0.06), (parkway, length, 0.12), 4))
        boxes.append(((side * (half + 0.2 + parkway + sidewalk / 2), 0, 0.08), (sidewalk, length, 0.16), 3))
    obj = merged_boxes(ctx, name, boxes, [ctx.mat("asphalt_la", roughness=0.85), ctx.mat("road_line", roughness=0.5), ctx.mat("line_yellow", roughness=0.5), ctx.mat("concrete", roughness=0.85), ctx.mat("lawn", roughness=0.9)], (centre[0], centre[1], 0.0), (0, 0, rot))
    ctx.tag("road", obj)
    return obj, half


def power_line(ctx, name, x, y0, y1, spacing=38.0, height=11.0, down_at=None, sparks=True):
    """Wooden utility poles with crossarms and transformer cans along local Y at x, wires between
    them. `down_at` topples the poles in turn and drops the wires (with arcing lights)."""
    rng = ctx.rng
    wood = ctx.mat("pole_wood", roughness=0.9)
    poles = []
    n = max(2, int((y1 - y0) / spacing) + 1)
    for i in range(n):
        y = y0 + i * (y1 - y0) / (n - 1)
        pole = multi_shape(ctx, f"{name}.pole{i}", [((0, 0, height - 0.6), (2.6, 0.18, 0.18), 0), ((0.8, 0, height - 1.6), (0.5, 0.5, 0.9), 1)], [((0, 0, height / 2), 0.16, height, "z", 0)], [wood, ctx.mat("transformer_grey", roughness=0.5)], (x, y, 0.0))
        poles.append(pole)
    wires = []
    for side in (-1.1, 0.0, 1.1):
        verts, faces = [], []
        for i in range(n - 1):
            ya, yb = y0 + i * (y1 - y0) / (n - 1), y0 + (i + 1) * (y1 - y0) / (n - 1)
            for k in range(6):
                t0, t1 = k / 6, (k + 1) / 6
                za = height - 0.5 - 1.2 * math.sin(math.pi * t0)
                zb = height - 0.5 - 1.2 * math.sin(math.pi * t1)
                base = len(verts)
                verts += [(x + side, ya + (yb - ya) * t0, za), (x + side, ya + (yb - ya) * t1, zb), (x + side, ya + (yb - ya) * t1, zb + 0.04), (x + side, ya + (yb - ya) * t0, za + 0.04)]
                faces.append((base, base + 1, base + 2, base + 3))
        wire = mesh_from_pydata(ctx, f"{name}.wire{side}", verts, faces, [ctx.mat("black", roughness=0.6)])
        wire.visible_shadow = False
        wires.append(wire)
    if down_at is not None:
        for i, pole in enumerate(poles):
            wind.topple(ctx, pole, down_at + i * rng.uniform(0.15, 0.4), duration=rng.uniform(0.8, 1.4), angle=-rng.uniform(70, 88), axis=1)  # falls downwind (-X)
        for wire in wires:
            key(wire, "location", ctx.frame(down_at), (0.0, 0.0, 0.0))
            key(wire, "location", ctx.frame(down_at + 1.4), (-3.0, 0.0, -(height - 0.6)))
            set_interp(wire, "QUAD", "EASE_IN", path="location")
        if sparks:
            import bpy

            for i in range(min(4, n)):
                data = bpy.data.lights.new(f"{name}.arc{i}", "POINT")
                data.energy = 0.0
                data.color = (0.7, 0.85, 1.0)
                arc = bpy.data.objects.new(f"{name}.arc{i}", data)
                arc.location = (x - 4.0, y0 + i * (y1 - y0) / (n - 1), 0.6)
                ctx.link(arc)
                ctx.tag("arc", arc)
    for pole in poles:
        ctx.tag("pole", pole)
    return poles


def streetlight(ctx, name, loc, rot=0.0, lit=False, torn_at=None):
    """Cobra-head streetlight; `torn_at` rips the pole away downwind."""
    pole = props.lamp_post(ctx, name, loc, 9.0, rot, lit=lit)
    if torn_at is not None:
        wind.fly(ctx, pole, torn_at, torn_at + 1.4, (-40.0, ctx.rng.uniform(-6, 6), 0.0), spin=(0.3, 1.1, 0.2), arc=5.0)
    return pole


def freeway_sign(ctx, name, loc, text, rot=0.0, width=10.0):
    """Green overhead freeway gantry sign with white lettering."""
    x, y, z = loc
    gantry = multi_box(ctx, name, [((0, 0, 7.4), (width + 6.0, 0.4, 0.4), 0), ((-(width + 6) / 2, 0, 3.7), (0.4, 0.4, 7.4), 0), (((width + 6) / 2, 0, 3.7), (0.4, 0.4, 7.4), 0), ((0, -0.3, 8.6), (width, 0.15, 2.4), 1)], [ctx.mat("dark_steel", roughness=0.5), ctx.mat("sign_green", roughness=0.4)], loc, (0, 0, rot))
    label = props.sign_text(ctx, f"{name}.text", text, (0, -0.42, 8.4), size=0.75, colour="white")
    parent(label, gantry)
    label.location = (0, -0.42, 8.4)
    label.rotation_euler = (math.pi / 2, 0, 0)
    return gantry


def freeway(ctx, name, length, lanes_each=5, centre=(0.0, 0.0), rot=0.0, z=0.0):
    """A concrete freeway along local Y: lanes each way, a median barrier and edge barriers."""
    lane = 3.7
    half = lanes_each * lane + 1.2
    boxes = [((0, 0, -0.1), (2 * half + 2, length, 0.2), 0)]
    for side in (-1, 1):
        for k in range(1, lanes_each):
            off = side * (1.2 + k * lane)
            for j in range(int(length / 12)):
                boxes.append(((off, -length / 2 + 12 * (j + 0.5), 0.005), (0.15, 3.0, 0.01), 1))
        boxes.append(((side * (half + 0.5), 0, 0.45), (0.5, length, 0.9), 2))
    boxes.append(((0, 0, 0.45), (0.6, length, 0.9), 2))
    obj = merged_boxes(ctx, name, boxes, [ctx.mat("freeway_concrete", roughness=0.85), ctx.mat("road_line", roughness=0.5), ctx.mat("concrete", roughness=0.8)], (centre[0], centre[1], z), (0, 0, rot))
    ctx.tag("freeway", obj)
    return obj, half


def overpass(ctx, name, start, end, z=12.0, width=16.0, spacing=24.0):
    """An elevated freeway connector on round columns between two (x, y) points."""
    sx, sy = start
    ex, ey = end
    length = math.hypot(ex - sx, ey - sy)
    angle = math.atan2(ey - sy, ex - sx)
    boxes = [((0, 0, z), (length, width, 1.4), 0), ((0, width / 2 - 0.25, z + 1.15), (length, 0.5, 0.9), 0), ((0, -width / 2 + 0.25, z + 1.15), (length, 0.5, 0.9), 0)]
    cyl = []
    for i in range(int(length / spacing) + 1):
        px = -length / 2 + i * length / max(1, int(length / spacing))
        boxes.append(((px, 0, z - 1.2), (2.2, width - 2.0, 1.2), 0))
        cyl.append(((px, 0, (z - 1.8) / 2), 1.1, z - 1.8, "z", 0))
    obj = multi_shape(ctx, name, boxes, cyl, [ctx.mat("freeway_concrete", roughness=0.85)], ((sx + ex) / 2, (sy + ey) / 2, 0.0), (0, 0, angle))
    ctx.tag("overpass", obj)
    return obj


# ----- downtown ----------------------------------------------------------------------------------
def tower(ctx, name, loc, size, kind="glass", lit=None, lit_fraction=0.5, broken=0.0, seed=0):
    """Downtown tower: glass curtain wall with mullions, a stone tower with punched windows, a
    cylinder with a stepped crown, or a sail-topped tower with a spire. `broken` darkens a share of
    the panels on the windward (+X) side: windows blown out."""
    rng = random.Random(seed)
    w, d, h = size
    x, y, z = loc
    glass = ctx.mat("tower_glass", roughness=0.12, metallic=0.5)
    stone = ctx.mat("tower_stone", roughness=0.8)
    mull = ctx.mat("mullion", roughness=0.5, metallic=0.4)
    void = ctx.mat("void", roughness=1.0)
    lit_mat = lit or glass
    if kind == "cylinder":
        body = cylinder(ctx, name, w / 2, h, loc, glass, segments=20, anchor="base")
        for k, (r, hh) in enumerate(((w * 0.42, 12.0), (w * 0.34, 10.0), (w * 0.24, 8.0))):
            ring = cylinder(ctx, f"{name}.crown{k}", r, hh, (0, 0, h + k * 10.0), stone if k % 2 else glass, segments=20, anchor="base")
            parent(ring, body)
            ring.location = (0, 0, h + k * 10.0)
        ctx.tag("tower", body)
        return body
    boxes = [((0, 0, h / 2), (w, d, h), 1 if kind == "stone" else 0)]
    floors = int(h / 4.0)
    for side in (-1, 1):
        for k in range(int(w / 3.0) + 1):
            boxes.append(((-w / 2 + k * w / int(w / 3.0), side * (d / 2 + 0.06), h / 2), (0.16, 0.12, h), 2))
        for k in range(int(d / 3.0) + 1):
            boxes.append(((side * (w / 2 + 0.06), -d / 2 + k * d / int(d / 3.0), h / 2), (0.12, 0.16, h), 2))
    for f in range(1, floors, 2):
        for side in (-1, 1):
            boxes.append(((0, side * (d / 2 + 0.07), f * 4.0), (w + 0.2, 0.1, 0.18), 2))
            boxes.append(((side * (w / 2 + 0.07), 0, f * 4.0), (0.1, d + 0.2, 0.18), 2))
    if lit is not None or broken > 0:
        for f in range(1, floors):
            for k in range(int(w / 3.0)):
                for side in (-1, 1):
                    roll = rng.random()
                    px = -w / 2 + (k + 0.5) * w / int(w / 3.0)
                    if side > 0 and roll < broken:
                        boxes.append(((w / 2 + 0.09, px * d / w, f * 4.0 - 1.7), (0.05, 2.6, 3.2), 3))
                    elif lit is not None and roll < lit_fraction * 0.6:
                        boxes.append(((px, side * (d / 2 + 0.09), f * 4.0 - 1.7), (2.6, 0.05, 3.2), 4))
    if kind == "spire":
        boxes += [((0, 0, h + 6.0), (w * 0.8, d * 0.6, 12.0), 0), ((0, 0, h + 16.0), (w * 0.5, d * 0.3, 8.0), 2)]
    body = merged_boxes(ctx, name, boxes, [glass, stone, mull, void, lit_mat], loc)
    if kind == "spire":
        spire = cone(ctx, f"{name}.spire", 1.2, 40.0, (0, 0, h + 20.0), mull, segments=6, anchor="base")
        parent(spire, body)
        spire.location = (0, 0, h + 20.0)
    ctx.tag("tower", body)
    return body


# ----- coast and airport -------------------------------------------------------------------------
def ferris_wheel(ctx, name, loc, radius=26.0, spin=0.0, rot=0.0, lit=False):
    """Pier Ferris wheel (rim, spokes and coloured gondolas) facing local Y; `spin` turns per shot."""
    white = ctx.mat("eye_white", roughness=0.4)
    hub_z = radius + 6.0
    root = empty(ctx, name, (loc[0], loc[1], loc[2] + hub_z), (0, 0, rot))
    wheel = empty(ctx, f"{name}.wheel", (0, 0, 0))
    parent(wheel, root)
    boxes = []
    n = 36
    for k in range(n):
        a0 = math.tau * k / n
        boxes.append(((radius * math.cos(a0), 0, radius * math.sin(a0)), (2 * math.pi * radius / n + 0.3, 0.7, 0.7), 0))
    for k in range(16):
        a = math.tau * k / 16
        boxes.append(((radius / 2 * math.cos(a), 0, radius / 2 * math.sin(a)), (radius, 0.25, 0.25), 0))
    rim = merged_boxes(ctx, f"{name}.rim", boxes, [white])
    parent(rim, wheel)
    gond = []
    colours = [ctx.mat(c, roughness=0.5) for c in ("awning_red", "awning_blue", "awning_orange", "awning_green")]
    for k in range(16):
        a = math.tau * k / 16
        gond.append(((radius * 1.05 * math.cos(a), 0, radius * 1.05 * math.sin(a) - 1.4), (2.0, 1.8, 2.0), k % 4))
    gondolas = merged_boxes(ctx, f"{name}.gondolas", gond, colours)
    parent(gondolas, wheel)
    legs = multi_box(ctx, f"{name}.legs", [((s * radius * 0.35, 0, -hub_z / 2), (1.2, 1.2, hub_z * 1.1), 0) for s in (-1, 1)], [white])
    parent(legs, root)
    legs.rotation_euler = (0, 0, 0)
    if spin:
        key(wheel, "rotation_euler", 1, (0.0, 0.0, 0.0))
        key(wheel, "rotation_euler", ctx.frames, (0.0, spin * math.tau, 0.0))
        set_interp(wheel, "LINEAR", path="rotation_euler")
    if lit:
        bulbs = ctx.palette.emissive(f"{name} bulbs", (1.0, 0.75, 0.45), 6.0)
        ring = merged_boxes(ctx, f"{name}.bulbs", [((radius * 1.01 * math.cos(math.tau * k / 48), 0.4, radius * 1.01 * math.sin(math.tau * k / 48)), (0.4, 0.2, 0.4), 0) for k in range(48)], [bulbs])
        parent(ring, wheel)
    ctx.tag("wheel", root)
    return root


def pier(ctx, name, start, length=280.0, width=24.0, deck=6.0):
    """Wooden pier on piles running along local +Y from start = (x, y)."""
    x, y = start
    wood = ctx.mat("pier_wood", roughness=0.9)
    boxes = [((x, y + length / 2, deck), (width, length, 0.6), 0)]
    cyl = []
    for i in range(int(length / 8) + 1):
        for k in range(4):
            cyl.append(((x - width / 2 + 1.5 + k * (width - 3) / 3, y + i * 8.0, deck / 2 - 2.0), 0.35, deck + 4.0, "z", 0))
    for side in (-1, 1):
        boxes.append(((x + side * (width / 2 - 0.1), y + length / 2, deck + 0.8), (0.15, length, 1.0), 0))
    obj = multi_shape(ctx, name, boxes, cyl, [wood])
    ctx.tag("pier", obj)
    return obj


def coaster(ctx, name, loc, radius=14.0):
    """A small steel coaster loop on trestles."""
    x, y, z = loc
    boxes = []
    for k in range(40):
        a = math.tau * k / 40
        boxes.append(((radius * 1.6 * math.cos(a), radius * math.sin(a), 10.0 + 6.0 * math.sin(2 * a)), (2.6, 1.2, 0.5), 0))
        if k % 4 == 0:
            boxes.append(((radius * 1.6 * math.cos(a), radius * math.sin(a), (10.0 + 6.0 * math.sin(2 * a)) / 2), (0.4, 0.4, 10.0 + 6.0 * math.sin(2 * a)), 1))
    return merged_boxes(ctx, name, boxes, [ctx.mat("awning_red", roughness=0.5), ctx.mat("eye_white", roughness=0.5)], loc)


def theme_building(ctx, name, loc, rot=0.0):
    """Round restaurant under two crossing white parabolic arches (the airport's landmark)."""
    white = ctx.mat("eye_white", roughness=0.5)
    base = cylinder(ctx, name, 8.0, 6.0, (loc[0], loc[1], loc[2] + 10.0), ctx.mat("tower_glass", roughness=0.15, metallic=0.4), segments=20, anchor="base")
    boxes = []
    for arch in (0.0, math.pi / 2):
        for k in range(24):
            u = -1 + 2 * k / 23
            px, pz = u * 34.0, 32.0 * (1 - u * u)
            boxes.append(((px * math.cos(arch), px * math.sin(arch), pz), (3.6, 1.4, 1.4), 0))
    arches = merged_boxes(ctx, f"{name}.arches", boxes, [white], loc, (0, 0, rot))
    parent(base, arches)
    base.location = (0, 0, 10.0)
    ctx.tag("landmark", arches)
    return arches


def wind_fire(ctx, name, loc, size=5.0, lean=0.7, light=True):
    """A wind-driven fire: deep orange tongues leaning hard downwind (-X), flickering, with a low
    smoke plume streaming away and an orange light (tags: flame, fire_light)."""
    rng = ctx.rng
    x, y, z = loc
    mats = [ctx.palette.emissive(f"{name} hot", "flame_hot", 2.6), ctx.palette.emissive(f"{name} deep", "flame_deep", 1.8)]
    for k in range(7):
        r = size * rng.uniform(0.18, 0.32)
        h = size * rng.uniform(0.7, 1.3)
        flame = cone(ctx, f"{name}.flame{k}", r, h, (x + rng.uniform(-size * 0.4, size * 0.4), y + rng.uniform(-size * 0.4, size * 0.4), z), mats[k % 2], segments=5, anchor="base", rot=(rng.uniform(-0.15, 0.15), -lean * rng.uniform(0.7, 1.1), rng.uniform(0, 6)))
        flame.visible_shadow = False
        add_noise(flame, "scale", 0.25, 1, ctx.frames, scale=2.5, phase=k * 1.3)
        ctx.tag("flame", flame)
    wind.smoke_column(ctx, f"{name}.smoke", (x - size, y, z + size * 0.6), height=size * 9.0, lean=2.2, puffs=8, width=size / 12.0)
    if light:
        import bpy

        data = bpy.data.lights.new(f"{name}.light", "POINT")
        data.energy = 900.0 * size
        data.color = (1.0, 0.45, 0.12)
        data.shadow_soft_size = size * 0.4
        lamp = bpy.data.objects.new(f"{name}.light", data)
        lamp.location = (x - size * 0.3, y, z + size * 0.6)
        ctx.link(lamp)
        key(data, "energy", 1)
        add_noise(data, "energy", 300.0 * size, 1, ctx.frames, scale=2.0)
        ctx.tag("fire_light", lamp)


def fire_truck(ctx, name, loc, rot=0.0, lit=True):
    root = empty(ctx, name, loc, (0, 0, rot))
    red = ctx.mat("fire_red", roughness=0.4)
    body = multi_box(ctx, f"{name}.body", [((0, 0, 1.6), (2.5, 9.5, 2.4), 0), ((0, 3.6, 2.9), (2.4, 2.2, 1.0), 1), ((0, -0.8, 3.2), (0.8, 7.5, 0.4), 2)], [red, ctx.palette.glass(f"{name} glass", "glass_dark"), ctx.mat("steel", roughness=0.3, metallic=0.8)], bevel=0.08)
    parent(body, root)
    beacon = box(ctx, f"{name}.beacon", (1.6, 0.35, 0.25), (0, 4.0, 3.55), ctx.palette.emissive(f"{name} beacon", "beacon_red", 0.0), bevel=0.03)
    parent(beacon, root)
    ctx.tag("beacon", beacon)
    _wheels(ctx, name, root, ((-1.1, 3.0), (1.1, 3.0), (-1.1, -2.8), (1.1, -2.8)), 0.55, 0.3)
    if lit:
        _lights(ctx, name, root, 4.76, -4.76, 1.0, 0.9)
    ctx.objects[name] = root
    ctx.tag("vehicle", root)
    return root
