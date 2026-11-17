"""London assets: Victorian terraces and high-street shops, double-decker buses, black cabs, phone and
pillar boxes, a railway viaduct, an Underground station front, Westminster, the Eye, the Shard,
St Paul's, the Thames Barrier, and the props of a city coping with a year of rain (sandbags, pumps,
road-closed signs, police tape, boarded windows, scaffolding, tower cranes, mould).

Shapes are generic and low-poly: no real logos, liveries or operator names."""

from __future__ import annotations

import math
import random

from studio.assets import characters, props
from studio.assets.meshes import merged_boxes
from studio.assets.vehicles import _lights, _wheels, drive
from studio.blender.primitives import box, clear_keys, cone, cylinder, empty, ico, key, mesh_from_pydata, multi_box, multi_shape, parent, set_interp

WALLS = {
    "residential": ("london_brick", "london_brick", "red_brick", "stucco", "london_brick"),
    "shops": ("london_brick", "red_brick", "stucco", "london_brick"),
    "mansion": ("red_brick",),
}
DOORS = ("door_red", "door_blue", "door_green", "door_black", "door_black", "door_blue")
SHOP_NAMES = ("CAFE", "PHARMACY", "NEWS", "BAKERY", "HARDWARE", "BOOKS", "LAUNDRETTE", "BARBER", "GROCER", "OFF LICENCE", "DRY CLEANER", "KEBABS", "FLORIST", "BUTCHER")
FASCIAS = ("fascia_green", "fascia_navy", "fascia_red", "fascia_black", "fascia_teal", "fascia_plum")
UMBRELLAS = ("umbrella_black", "umbrella_black", "umbrella_black", "umbrella_navy", "door_red", "umbrella_tartan", "fascia_green")
COATS = ("navy", "black", "coat_beige", "dark_steel", "coat_olive", "trousers_2", "coat_grey")


def _row_point(origin, rot, x, y):
    c, s = math.cos(rot), math.sin(rot)
    return (origin[0] + x * c - y * s, origin[1] + x * s + y * c)


# ----- terraces and shops ------------------------------------------------------------------------
def terrace(ctx, name, origin, count, rot=0.0, seed=0, kind="residential", lit=None, lit_fraction=0.45, boarded=0.0, shutters=0.0, to_let=0.0, damp=0.0, signs=True):
    """A row of attached houses running along local +X from origin = (x, y, z), fronts facing local -Y
    (the street side), rotated by `rot`. kind: residential (raised ground floor over a basement
    lightwell behind railings), shops (shopfronts with fascia signs) or mansion (taller red-brick
    blocks). Returns a dict with the row object, door points, lightwell rectangles and length."""
    rng = random.Random(seed)
    ox, oy, oz = origin
    walls = WALLS[kind]
    mats = [ctx.mat(w, roughness=0.9) for w in ("london_brick", "red_brick", "stucco")]  # 0..2 walls
    mats += [ctx.mat("sash_white", roughness=0.6), ctx.palette.glass(f"{name} glass", "glass_dark"), ctx.mat("slate", roughness=0.7), ctx.mat("black", roughness=0.5)]  # 3 trim, 4 glass, 5 slate, 6 iron
    mats += [ctx.mat(d, roughness=0.5) for d in DOORS]  # 7..12 doors
    mats += [lit or mats[4], ctx.mat("plywood", roughness=0.9), ctx.mat("shutter_grey", roughness=0.5, metallic=0.4), ctx.mat("damp_stain", roughness=1.0)]  # 13 lit, 14 plywood, 15 shutter, 16 damp
    mats += [ctx.mat(f, roughness=0.6) for f in FASCIAS]  # 17.. fascias
    wall_index = {"london_brick": 0, "red_brick": 1, "stucco": 2}
    boxes = []
    doors, wells, fronts = [], [], []
    x = 0.0
    tall = kind == "mansion"
    for i in range(count):
        w = rng.uniform(5.2, 6.4) if not tall else rng.uniform(14.0, 18.0)
        storeys = rng.choice((3, 4, 4)) if not tall else rng.choice((5, 6))
        wall = wall_index[rng.choice(walls)]
        depth = 10.0 if not tall else 14.0
        raised = 0.9 if kind == "residential" else 0.0
        heights = [3.3] + [3.6] + [3.0] * (storeys - 2) if not tall else [3.4] * storeys
        top = raised + sum(heights)
        cx = x + w / 2
        boxes.append(((cx, depth / 2, top / 2), (w - 0.02, depth, top), wall))
        # party-wall piers and cornice give each house its own rhythm
        boxes.append(((x + 0.12, -0.06, top / 2), (0.24, 0.14, top), 2 if wall != 2 else 3))
        boxes.append(((cx, -0.18, top + 0.15), (w, 0.4, 0.3), 3))
        boxes.append(((cx, 0.4, top + 0.65), (w, 0.3, 1.0), wall))  # parapet
        # slate roof (mansard slope) and chimney stack on the party wall
        verts_roof = [(x, 0.7, top + 0.2), (x + w, 0.7, top + 0.2), (x + w, depth, top + 0.2), (x, depth, top + 0.2), (x, 2.4, top + 2.6), (x + w, 2.4, top + 2.6), (x + w, depth - 1.0, top + 2.6), (x, depth - 1.0, top + 2.6)]
        boxes.append(((x + w, depth * 0.45, top + 3.1), (0.9, 2.6, 2.0), wall))
        for k in range(3):
            boxes.append(((x + w, depth * 0.45 - 0.8 + k * 0.8, top + 4.4), (0.3, 0.3, 0.6), 1))
        fronts.append((verts_roof, 5))
        # floors and windows
        z = raised
        boarded_house = rng.random() < boarded
        dark_house = boarded_house or rng.random() < 0.15
        for floor, fh in enumerate(heights):
            bays = 2 if not tall else 5
            for b in range(bays):
                bx = x + w * (b + 0.5) / bays
                ground = floor == 0
                if ground and kind == "residential" and b == 0:
                    # front door with fanlight, door case and steps over the lightwell
                    door_mat = 7 + rng.randrange(len(DOORS))
                    boxes.append(((bx, -0.10, z + 1.2), (1.05, 0.12, 2.4), door_mat))
                    boxes.append(((bx, -0.12, z + 2.65), (1.05, 0.08, 0.4), 4))
                    boxes.append(((bx, -0.14, z + 1.45), (1.6, 0.1, 2.9), 3))
                    for step in range(3):
                        boxes.append(((bx, -0.35 - step * 0.35, z - 0.15 - step * 0.3), (1.6, 0.7, 0.3), 3))
                    boxes.append(((bx, -1.0, raised - 0.05), (1.7, 2.0, 0.1), 3))
                    doors.append(_row_point((ox, oy), rot, bx, -2.1))
                    continue
                if ground and kind == "shops":
                    continue
                ww, wh = (1.15, fh * 0.62) if not tall else (1.5, fh * 0.55)
                wz = z + fh * 0.52
                boxes.append(((bx, -0.07, wz), (ww + 0.24, 0.1, wh + 0.24), 3))
                if boarded_house:
                    boxes.append(((bx, -0.16, wz), (ww + 0.3, 0.06, wh + 0.3), 14))
                else:
                    lit_here = lit is not None and not dark_house and rng.random() < lit_fraction
                    boxes.append(((bx, -0.13, wz), (ww, 0.04, wh), 13 if lit_here else 4))
                    boxes.append(((bx, -0.155, wz), (ww, 0.04, 0.06), 3))  # sash meeting rail
                    if damp > 0 and rng.random() < damp:
                        boxes.append(((bx + rng.uniform(-0.3, 0.3), -0.105, wz - wh / 2 - 0.9), (ww * rng.uniform(0.5, 1.1), 0.02, 1.6), 16))
                boxes.append(((bx, -0.15, wz - wh / 2 - 0.16), (ww + 0.4, 0.2, 0.1), 3))  # sill
            z += fh
            if floor == 0 and not tall:
                boxes.append(((cx, -0.1, z), (w, 0.16, 0.22), 3))  # string course
        if kind == "residential":
            # lightwell: a pit in front of the house with a basement window, behind iron railings
            wells.append((x, -1.6, x + w, 0.0))
            boxes.append(((cx, -0.8, -1.3), (w - 0.1, 1.6, 0.1), 3))
            boxes.append(((cx, 0.15, -0.65), (w, 0.3, 1.4), wall))
            boxes.append(((cx, -1.7, -0.6), (w, 0.14, 1.5), 3))
            boxes.append(((x + 0.06, -0.8, -0.6), (0.12, 1.6, 1.5), 3))
            boxes.append(((cx + w * 0.22, -0.1, -0.9), (1.1, 0.1, 1.4), 4))
            for k in range(int(w / 0.22)):
                boxes.append(((x + 0.11 + k * 0.22, -1.62, 0.55), (0.035, 0.035, 1.1), 6))
            boxes.append(((cx, -1.62, 1.08), (w, 0.06, 0.05), 6))
        elif kind == "shops":
            fascia = 17 + rng.randrange(len(FASCIAS))
            boxes.append(((cx, -0.2, 3.65), (w - 0.3, 0.3, 0.75), fascia))
            boxes.append(((cx, -0.08, 0.25), (w - 0.3, 0.12, 0.5), fascia))
            for px in (x + 0.2, x + w - 0.2):
                boxes.append(((px, -0.14, 1.65), (0.3, 0.24, 3.3), 3))
            closed = rng.random() < shutters
            if closed:
                boxes.append(((cx, -0.25, 1.85), (w - 0.5, 0.1, 2.75), 15))
                for k in range(9):
                    boxes.append(((cx, -0.31, 0.6 + k * 0.3), (w - 0.5, 0.03, 0.04), 6))
            else:
                lit_shop = lit is not None and rng.random() < 0.7
                boxes.append(((cx + 0.6, -0.1, 1.85), (w - 2.2, 0.06, 2.6), 13 if lit_shop else 4))
                boxes.append(((x + 0.85, -0.1, 1.5), (0.95, 0.06, 2.4), 4))
            if signs:
                label = SHOP_NAMES[(seed * 7 + i * 3) % len(SHOP_NAMES)]
                sx_, sy_ = _row_point((ox, oy), rot, cx, -0.37)
                txt = props.sign_text(ctx, f"{name}.sign{i}", label, (sx_, sy_, oz + 3.5), size=0.42, rot=(math.pi / 2, 0, rot), colour="sign_cream")
                ctx.tag("shop_sign", txt)
            doors.append(_row_point((ox, oy), rot, x + 0.85, -1.0))
        if rng.random() < to_let:
            px, py = x + w * 0.7, -0.4
            boxes.append(((px, py, top * 0.55 + 2.0), (0.08, 0.08, 3.0), 3))
            boxes.append(((px, py - 0.1, top * 0.55 + 3.2), (1.2, 0.05, 0.8), 3))
            sx_, sy_ = _row_point((ox, oy), rot, px, py - 0.16)
            props.sign_text(ctx, f"{name}.let{i}", "TO LET", (sx_, sy_, oz + top * 0.55 + 3.05), size=0.28, rot=(math.pi / 2, 0, rot), colour="fascia_red")
        x += w
    row = merged_boxes(ctx, name, boxes, mats, (ox, oy, oz), (0, 0, rot))
    # mansard roofs as one extra mesh
    verts, faces = [], []
    for quad, _ in fronts:
        base = len(verts)
        verts.extend(quad)
        faces += [(base + 0, base + 1, base + 5, base + 4), (base + 4, base + 5, base + 6, base + 7), (base + 7, base + 6, base + 2, base + 3), (base + 0, base + 4, base + 7, base + 3), (base + 1, base + 2, base + 6, base + 5)]
    roofs = mesh_from_pydata(ctx, f"{name}.roofs", verts, faces, [ctx.mat("slate", roughness=0.7)], (ox, oy, oz), (0, 0, rot))
    parent(roofs, row)
    roofs.location = (0, 0, 0)
    roofs.rotation_euler = (0, 0, 0)
    ctx.tag("terrace", row)
    world_wells = []
    for x0, y0, x1, y1 in wells:
        pts = [_row_point((ox, oy), rot, px, py) for px, py in ((x0, y0), (x1, y1))]
        world_wells.append(pts)
    return {"row": row, "doors": doors, "wells": world_wells, "length": x}


def lightwell_water(ctx, name, wells, origin_z=0.0, level=-2.3):
    """Water planes inside basement lightwells (raise them with a water_level event on tag:lightwell)."""
    from studio.assets.weather import murky

    material = murky(ctx, f"{name} water", "flood_brown")
    objs = []
    for i, (a, b) in enumerate(wells):
        cx, cy = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        # the well is axis-aligned in world space: size it from its own corners
        obj = box(ctx, f"{name}{i}", (abs(b[0] - a[0]) - 0.12, abs(b[1] - a[1]) - 0.12, 0.04), (cx, cy, origin_z + level), material)
        ctx.tag("lightwell", obj)
        objs.append(obj)
    return objs


# ----- street furniture and vehicles -------------------------------------------------------------
def double_decker(ctx, name, loc, rot=0.0, lit=False, route="25", destination="OXFORD CIRCUS"):
    """Red double-decker bus (11 m) facing local +Y, with a lit destination blind."""
    root = empty(ctx, name, loc, (0, 0, rot))
    red = ctx.mat("bus_red", roughness=0.35)
    glass = ctx.palette.glass(f"{name} glass", "glass_dark")
    blind_bg = ctx.mat("black", roughness=0.4)
    boxes = [
        ((0, 0, 1.25), (2.5, 11.0, 1.9), 0),
        ((0, 0, 3.15), (2.5, 10.8, 1.75), 0),
        ((0, 0, 4.12), (2.42, 10.6, 0.2), 2),
        ((0, 0, 2.2), (2.53, 10.9, 0.06), 3),
        ((0, 0, 0.32), (2.4, 10.6, 0.18), 2),
    ]
    for side in (-1, 1):
        boxes.append(((side * 1.255, -0.6, 1.62), (0.02, 8.8, 0.95), 1))
        boxes.append(((side * 1.255, 0.0, 3.25), (0.02, 10.0, 1.0), 1))
    boxes += [((0, 5.505, 1.55), (2.2, 0.02, 1.25), 1), ((0, 5.405, 3.25), (2.2, 0.02, 1.0), 1), ((0, 5.51, 2.45), (1.5, 0.03, 0.34), 4), ((0, -5.505, 3.25), (2.0, 0.02, 0.9), 1)]
    body = multi_box(ctx, f"{name}.body", boxes, [red, glass, ctx.mat("dark_steel"), ctx.mat("sash_white"), blind_bg], bevel=0.08)
    parent(body, root)
    _wheels(ctx, name, root, ((-1.05, 3.4), (1.05, 3.4), (-1.05, -3.0), (1.05, -3.0)), 0.5, 0.3)
    blind = props.sign_text(ctx, f"{name}.blind", f"{route} {destination}", (0.0, 5.56, 2.39), size=0.2, rot=(math.pi / 2, 0, math.pi), colour="blind_amber", emission=2.5)
    parent(blind, root)
    blind.location = (0.0, 5.56, 2.39)
    blind.rotation_euler = (math.pi / 2, 0, math.pi)
    if lit:
        _lights(ctx, name, root, 5.52, -5.52, 0.75, 0.9)
        interior = box(ctx, f"{name}.interior", (2.3, 9.0, 2.9), (0, -0.3, 2.3), ctx.palette.emissive(f"{name} cabin", (1.0, 0.9, 0.7), 0.8))
        parent(interior, root)
    ctx.objects[name] = root
    ctx.tag("vehicle", root)
    ctx.tag("bus", root)
    return root


def black_cab(ctx, name, loc, rot=0.0, lit=False):
    """London taxi: tall rounded black body with an amber roof sign."""
    root = empty(ctx, name, loc, (0, 0, rot))
    paint = ctx.mat("cab_black", roughness=0.25)
    glass = ctx.palette.glass(f"{name} glass", "glass_dark")
    sign = ctx.palette.emissive(f"{name} sign", "blind_amber", 4.0 if lit else 1.2)
    body = multi_box(ctx, f"{name}.body", [((0, 0, 0.66), (1.85, 4.55, 0.7), 0), ((0, -0.35, 1.35), (1.72, 2.6, 0.72), 1), ((0, -0.35, 1.74), (1.68, 2.5, 0.08), 0), ((0, 0.25, 1.83), (0.62, 0.22, 0.16), 2), ((0, 2.28, 0.62), (1.4, 0.06, 0.3), 3)], [paint, glass, sign, ctx.mat("steel", roughness=0.3, metallic=0.8)], bevel=0.12)
    parent(body, root)
    _wheels(ctx, name, root, ((-0.86, 1.45), (0.86, 1.45), (-0.86, -1.4), (0.86, -1.4)), 0.36, 0.24)
    if lit:
        _lights(ctx, name, root, 2.28, -2.28, 0.72, 0.64)
    ctx.objects[name] = root
    ctx.tag("vehicle", root)
    return root


def phone_box(ctx, name, loc, rot=0.0, lit=False):
    red = ctx.mat("bus_red", roughness=0.4)
    glass = ctx.palette.glass(f"{name} glass", "glass_dark") if not lit else ctx.palette.emissive(f"{name} lamp", (1.0, 0.92, 0.75), 1.5)
    boxes = [((0, 0, 1.3), (1.0, 1.0, 2.6), 0), ((0, 0, 2.72), (1.08, 1.08, 0.25), 0), ((0, 0, 2.92), (0.8, 0.8, 0.18), 0), ((0, 0, 0.07), (1.1, 1.1, 0.14), 0)]
    for face in range(4):
        a = face * math.pi / 2
        for row in range(6):
            for col in range(3):
                px, pz = -0.3 + col * 0.3, 0.75 + row * 0.27
                fx, fy = math.cos(a) * 0.505 - math.sin(a) * px, math.sin(a) * 0.505 + math.cos(a) * px
                size = (0.04, 0.24, 0.22) if abs(math.cos(a)) > 0.5 else (0.24, 0.04, 0.22)
                boxes.append(((fx, fy, pz), size, 1))
        boxes.append(((math.cos(a) * 0.52, math.sin(a) * 0.52, 2.45), (0.06, 0.7, 0.14) if abs(math.cos(a)) > 0.5 else (0.7, 0.06, 0.14), 2))
    return multi_box(ctx, name, boxes, [red, glass, ctx.mat("sign_cream", emission=1.5 if lit else 0.0)], loc, (0, 0, rot), bevel=0.02)


def pillar_box(ctx, name, loc):
    red = ctx.mat("bus_red", roughness=0.4)
    return multi_shape(ctx, name, [((0, 0.27, 1.12), (0.3, 0.03, 0.05), 1)], [((0, 0, 0.75), 0.28, 1.5, "z", 0), ((0, 0, 1.55), 0.31, 0.12, "z", 0), ((0, 0, 0.05), 0.31, 0.1, "z", 1)], [red, ctx.mat("black")], loc)


def bus_stop(ctx, name, loc, rot=0.0):
    steel = ctx.mat("dark_steel", roughness=0.4)
    glass = ctx.palette.make(f"{name} glass", ctx.palette.colour("glass"), roughness=0.1, alpha=0.35)
    boxes = [((0, 0, 2.5), (3.4, 1.5, 0.1), 0), ((-1.65, 0, 1.25), (0.08, 1.4, 2.5), 0), ((1.65, 0, 1.25), (0.08, 1.4, 2.5), 0), ((0, 0.7, 1.3), (3.3, 0.04, 2.2), 1), ((0, 0.4, 0.5), (2.6, 0.4, 0.06), 0)]
    return multi_box(ctx, name, boxes, [steel, glass], loc, (0, 0, rot))


def kerb_and_road(ctx, name, length, width=10.0, pavement=4.0, wet=True, bus_lane=True, centre=(0.0, 0.0), double_yellow=True, rot=0.0):
    """Road along local Y with UK markings (dashed centre, bus lane, double yellow lines), raised kerbs
    and pavements (pavement = width or (west, east) widths), as one mesh rotated by `rot`."""
    cx, cy = centre
    left, right = (pavement, pavement) if isinstance(pavement, (int, float)) else pavement
    from studio.assets.weather import wet as wet_surface

    tarmac = wet_surface(ctx, "tarmac_wet") if wet else ctx.mat("asphalt", roughness=0.85)
    paving = wet_surface(ctx, "pavement_wet", 0.4) if wet else ctx.mat("pavement", roughness=0.85)
    lines = ctx.mat("road_line", roughness=0.4)
    yellow = ctx.mat("line_yellow", roughness=0.4)
    lane = ctx.mat("bus_lane", roughness=0.25 if wet else 0.8)
    boxes = [((0, 0, -0.03), (width, length, 0.06), 0)]
    n = int(length / 9)
    for i in range(n):
        boxes.append(((0, -length / 2 + 9 * (i + 0.5), 0.005), (0.15, 4.0, 0.01), 2))
    if bus_lane:
        boxes.append(((width / 2 - 1.6, 0, 0.004), (3.0, length, 0.01), 4))
        boxes.append(((width / 2 - 3.15, 0, 0.006), (0.25, length, 0.01), 2))
    if double_yellow:
        for side in (-1, 1):
            for off in (0.25, 0.45):
                boxes.append(((side * (width / 2 - off), 0, 0.007), (0.1, length, 0.01), 3))
    for side, walk in ((-1, left), (1, right)):
        boxes.append(((side * (width / 2 + walk / 2), 0, 0.08), (walk, length, 0.16), 1))
        boxes.append(((side * (width / 2 + 0.1), 0, 0.085), (0.2, length, 0.17), 5))
    road = multi_box(ctx, name, boxes, [tarmac, paving, lines, yellow, lane, ctx.mat("stone", roughness=0.6)], (cx, cy, 0.0), (0, 0, rot))
    ctx.tag("road", road)
    return road


def umbrella(ctx, name, colour):
    canopy = cone(ctx, name, 0.55, 0.28, (0, 0, 0), ctx.mat(colour, roughness=0.4), segments=8, anchor="base")
    shaft = cylinder(ctx, f"{name}.shaft", 0.012, 0.85, (0, 0, -0.42), ctx.mat("black"), segments=6)
    parent(shaft, canopy)
    canopy.visible_shadow = True
    return canopy


def walkers(ctx, name, lanes, count, length, umbrellas=0.8, start=0.0, centre=0.0, roles=("civilian", "shopper", "civilian"), run=0.0, clear=None):
    """Pedestrians along pavement lanes: lanes = [(x, direction), ...] with paths along Y over
    `length`. Most carry umbrellas (the arm holding it stops swinging). clear = (x, y, r) keeps
    everyone's path at least r metres from a point (the camera)."""
    rng = ctx.rng
    actors = []
    for i in range(count * 3):
        if len(actors) >= count:
            break
        lane_x, direction = rng.choice(lanes)
        y0 = centre + rng.uniform(-length / 2, length / 2)
        travel = length * rng.uniform(0.3, 0.6) * direction
        x = lane_x + rng.uniform(-0.6, 0.6)
        if clear and abs(x - clear[0]) < clear[2] and min(y0, y0 + travel) - clear[2] < clear[1] < max(y0, y0 + travel) + clear[2]:
            continue
        aid = f"{name}{i}"
        actor = characters.build(ctx, {"id": aid, "role": rng.choice(roles), "at": (x, y0, 0.16), "top": rng.choice(COATS)})
        action = "run" if rng.random() < run else "walk"
        characters.animate(ctx, actor, {"action": action, "path": [[x, y0], [x, y0 + travel]], "start": start + rng.uniform(0.0, 1.2)})
        if rng.random() < umbrellas and actor.role != "child":
            arm = actor.arms["r"]
            clear_keys(arm, "rotation_euler", 1, ctx.frames + 10)
            arm.rotation_euler = (math.radians(55.0), 0.0, math.radians(-8.0))
            brolly = umbrella(ctx, f"{aid}.umbrella", rng.choice(UMBRELLAS))
            parent(brolly, actor.torso)
            brolly.location = (-0.22, 0.22, 1.25)
        actors.append(actor)
    return actors


def sandbags(ctx, name, points, rows=2, width=1.6, facing=0.0):
    """Stacked sandbags across doorways at the given (x, y) points."""
    rng = ctx.rng
    boxes = []
    for px, py in points:
        for row in range(rows):
            n = int(width / 0.55)
            for k in range(n):
                off = -width / 2 + (k + 0.5) * width / n + (0.27 if row % 2 else 0.0)
                if abs(off) > width / 2:
                    continue
                dx, dy = math.cos(facing) * off, math.sin(facing) * off
                boxes.append(((px + dx, py + dy, 0.24 + row * 0.2), (0.55 if abs(math.cos(facing)) > 0.5 else 0.34, 0.34 if abs(math.cos(facing)) > 0.5 else 0.55, 0.2 + rng.uniform(-0.02, 0.02)), 0))
    return multi_box(ctx, name, boxes, [ctx.mat("sandbag", roughness=1.0)], bevel=0.06)


def pump(ctx, name, loc, hose_to, rot=0.0):
    body = multi_box(ctx, name, [((0, 0, 0.3), (0.6, 0.45, 0.45), 0), ((0, 0, 0.6), (0.4, 0.2, 0.15), 1)], [ctx.mat("yellow", roughness=0.5), ctx.mat("black")], loc, (0, 0, rot), bevel=0.04)
    props.pipe(ctx, f"{name}.hose", [(loc[0], loc[1], 0.3), ((loc[0] + hose_to[0]) / 2, (loc[1] + hose_to[1]) / 2, 0.12), (hose_to[0], hose_to[1], 0.1)], radius=0.05, colour="black")
    return body


def road_closed(ctx, name, loc, rot=0.0, text="ROAD CLOSED"):
    """Red-and-white barrier with a ROAD CLOSED sign."""
    x, y, z = loc
    boxes = [((0, 0, 0.9), (3.0, 0.08, 0.3), 0), ((0, 0, 0.9), (0.6, 0.085, 0.3), 1), ((-1.2, 0, 0.9), (0.4, 0.085, 0.3), 1), ((1.2, 0, 0.9), (0.4, 0.085, 0.3), 1)]
    for dx in (-1.35, 1.35):
        boxes += [((dx, 0, 0.45), (0.08, 0.08, 0.9), 2), ((dx, 0, 0.04), (0.1, 0.7, 0.08), 2)]
    boxes += [((0, -0.06, 1.75), (1.5, 0.04, 0.9), 1), ((0, -0.055, 1.75), (1.6, 0.03, 1.0), 0), ((0, 0, 1.25), (0.06, 0.06, 0.6), 2)]
    sign = multi_box(ctx, name, boxes, [ctx.mat("barrier_red", roughness=0.5), ctx.mat("white", roughness=0.5), ctx.mat("dark_steel")], loc, (0, 0, rot))
    label = props.sign_text(ctx, f"{name}.text", text, (0, -0.09, 1.66), size=0.2, colour="barrier_red")
    parent(label, sign)
    label.location = (0, -0.09, 1.66)
    label.rotation_euler = (math.pi / 2, 0, 0)
    ctx.tag("road_closed", sign)
    return sign


def police_tape(ctx, name, points, z=0.95):
    boxes = []
    for (ax, ay), (bx, by) in zip(points, points[1:], strict=False):
        length = math.hypot(bx - ax, by - ay)
        angle = math.atan2(by - ay, bx - ax)
        n = max(1, int(length / 0.5))
        for k in range(n):
            t = (k + 0.5) / n
            boxes.append(((ax + (bx - ax) * t, ay + (by - ay) * t, z + 0.03 * math.sin(t * math.pi)), (length / n, 0.01, 0.07), k % 2, angle))
    mats = [ctx.mat("tape_blue", roughness=0.4), ctx.mat("white", roughness=0.4)]
    verts, faces, face_mats = [], [], []
    for (px, py, pz), (sx, sy, sz), m, angle in boxes:
        c, s = math.cos(angle), math.sin(angle)
        base = len(verts)
        for dx, dz in ((-sx / 2, -sz / 2), (sx / 2, -sz / 2), (sx / 2, sz / 2), (-sx / 2, sz / 2)):
            verts.append((px + dx * c, py + dx * s, pz + dz))
        faces.append((base, base + 1, base + 2, base + 3))
        face_mats.append(m)
    return mesh_from_pydata(ctx, name, verts, faces, mats, face_mats=face_mats)


def scaffolding(ctx, name, origin, length, height, rot=0.0, depth=1.2, netting=True):
    """Tube-and-board scaffold on a facade: origin is the facade's front-left foot, along local +X."""
    tube = ctx.mat("scaffold", roughness=0.4, metallic=0.6)
    boards = ctx.mat("plywood", roughness=0.9)
    boxes = []
    bays = max(1, int(length / 2.4))
    lifts = max(1, int(height / 2.0))
    for b in range(bays + 1):
        for dy in (-0.25, -0.25 - depth):
            boxes.append(((b * length / bays, dy, height / 2), (0.05, 0.05, height), 0))
    for lift in range(1, lifts + 1):
        z = lift * height / lifts
        for dy in (-0.25, -0.25 - depth):
            boxes.append(((length / 2, dy, z), (length, 0.05, 0.05), 0))
        boxes.append(((length / 2, -0.25 - depth / 2, z - 0.03), (length, depth, 0.04), 1))
    objs = [multi_box(ctx, name, boxes, [tube, boards], origin, (0, 0, rot))]
    if netting:
        net = ctx.palette.make(f"{name} net", ctx.palette.colour("netting"), roughness=0.9, alpha=0.55)
        n = box(ctx, f"{name}.net", (length, 0.02, height), (length / 2, -0.3 - depth, height / 2), net)
        parent(n, objs[0])
        n.location = (length / 2, -0.3 - depth, height / 2)
        n.visible_shadow = False
    ctx.tag("scaffold", objs[0])
    return objs[0]


def tower_crane(ctx, name, loc, height=60.0, jib=50.0, rot=0.0, spin=None):
    """Luffing-free tower crane: lattice mast, jib, counter-jib with ballast, cab and hook.
    spin = (start_s, end_s, degrees) slews the jib."""
    yellow = ctx.mat("crane_yellow", roughness=0.5)
    steel = ctx.mat("dark_steel", roughness=0.5)
    mast_boxes = [((0, 0, 0.5), (6.0, 6.0, 1.0), 1)]
    for cx_, cy_ in ((-0.9, -0.9), (0.9, -0.9), (-0.9, 0.9), (0.9, 0.9)):
        mast_boxes.append(((cx_, cy_, height / 2), (0.22, 0.22, height), 0))
    for k in range(int(height / 3.0)):
        z = 1.5 + k * 3.0
        mast_boxes += [((0, -0.9, z), (1.8, 0.12, 0.12), 0), ((0, 0.9, z), (1.8, 0.12, 0.12), 0), ((-0.9, 0, z), (0.12, 1.8, 0.12), 0), ((0.9, 0, z), (0.12, 1.8, 0.12), 0)]
    mast = multi_box(ctx, name, mast_boxes, [yellow, steel], loc)
    head = empty(ctx, f"{name}.slew", (0, 0, height), (0, 0, rot))
    parent(head, mast)
    head.location = (0, 0, height)
    jib_boxes = [((0, jib / 2, 0.8), (1.2, jib, 1.4), 0), ((0, -8.0, 0.8), (1.4, 16.0, 1.2), 0), ((0, -14.0, -0.2), (2.4, 3.0, 2.2), 1), ((1.4, 2.0, -0.6), (1.6, 2.0, 1.8), 0), ((0, 0, 4.0), (0.6, 0.6, 7.0), 0)]
    jib_obj = multi_box(ctx, f"{name}.jib", jib_boxes, [yellow, ctx.mat("concrete")])
    parent(jib_obj, head)
    hook = multi_box(ctx, f"{name}.hook", [((0, jib * 0.7, -height * 0.3), (0.05, 0.05, height * 0.6), 0), ((0, jib * 0.7, -height * 0.6), (0.6, 0.6, 0.8), 1)], [steel, yellow])
    parent(hook, head)
    if spin:
        f0, f1 = ctx.frame(spin[0]), ctx.frame(spin[1])
        key(head, "rotation_euler", f0, (0, 0, rot))
        key(head, "rotation_euler", f1, (0, 0, rot + math.radians(spin[2])))
        set_interp(head, "SINE", "EASE_IN_OUT", path="rotation_euler")
    ctx.tag("crane", mast)
    return mast


# ----- big structures -----------------------------------------------------------------------------
def viaduct(ctx, name, start, end, height=7.0, width=9.0, span=9.0, street=(-9.5, 9.5)):
    """Victorian railway viaduct between two (x, y) points: brick arches every `span` metres, and an
    iron girder bridge (painted, ribbed) over the street between local x = street[0]..street[1]."""
    sx, sy = start
    ex, ey = end
    length = math.hypot(ex - sx, ey - sy)
    angle = math.atan2(ey - sy, ex - sx)
    brick = ctx.mat("viaduct_brick", roughness=0.95)
    paint = ctx.mat("bridge_green", roughness=0.5)
    boxes = [((0, 0, height + 0.6), (length, width, 1.2), 0), ((0, width / 2 - 0.2, height + 1.6), (length, 0.4, 0.8), 0), ((0, -width / 2 + 0.2, height + 1.6), (length, 0.4, 0.8), 0)]
    a, b = street
    pos = -length / 2
    while pos < length / 2 - 0.1:
        nxt = min(length / 2, pos + span)
        if nxt <= a or pos >= b:
            mid, w = (pos + nxt) / 2, nxt - pos
            boxes += [((pos + 0.8, 0, height / 2), (1.6, width, height), 0), ((mid, 0, height - 0.9), (w - 1.6, width, 1.8), 0), ((mid, 0, height - 2.0), (w - 3.0, width, 0.6), 0), ((mid, 0, height - 2.6), (w - 4.2, width, 0.6), 0)]
        pos = nxt
    for edge in (a - 1.6, b + 1.6):
        boxes.append(((edge, 0, height / 2), (3.2, width + 0.6, height + 0.4), 0))
    span_len = b - a
    for side in (-1, 1):
        boxes.append((((a + b) / 2, side * (width / 2 + 0.15), height - 0.2), (span_len + 0.4, 0.5, 1.9), 1))
        for k in range(int(span_len / 1.2) + 1):
            boxes.append(((a + k * 1.2, side * (width / 2 + 0.45), height - 0.2), (0.12, 0.12, 1.8), 1))
    boxes.append((((a + b) / 2, 0, height - 0.95), (span_len + 0.4, width, 0.3), 1))
    for side in (-1, 1):
        for rail in (-0.75, 0.75):
            boxes.append(((0, side * 2.2 + rail, height + 1.28), (length, 0.08, 0.12), 2))
    obj = multi_box(ctx, name, boxes, [brick, paint, ctx.mat("steel", roughness=0.3, metallic=0.7)], ((sx + ex) / 2, (sy + ey) / 2, 0.0), (0, 0, angle))
    ctx.tag("viaduct", obj)
    return obj


def train(ctx, name, path, cars=6, start=0.0, speed=14.0, z=8.3, lit=True):
    """Commuter train of `cars` carriages that runs along path (list of (x, y))."""
    root = empty(ctx, name, (path[0][0], path[0][1], z))
    body = ctx.mat("train_white", roughness=0.4)
    stripe = ctx.mat("fascia_navy", roughness=0.4)
    glass = ctx.palette.glass(f"{name} glass", "glass_dark") if not lit else ctx.palette.emissive(f"{name} windows", (1.0, 0.92, 0.75), 1.2)
    boxes = []
    for c in range(cars):
        y = -c * 20.6
        boxes += [((0, y, 1.9), (2.8, 20.0, 3.4), 0), ((0, y, 1.05), (2.82, 20.0, 0.35), 1)]
        for side in (-1, 1):
            boxes.append(((side * 1.405, y, 2.35), (0.02, 18.0, 0.9), 2))
    carriages = multi_box(ctx, f"{name}.cars", boxes, [body, stripe, glass], bevel=0.15)
    parent(carriages, root)
    drive(ctx, root, [(p[0], p[1], z) for p in path], start, None, speed, z)
    return root


def station_front(ctx, name, loc, rot=0.0, width=12.0, closed=True, lit=False):
    """Oxblood-tiled Edwardian Underground station front with arched openings and a sign band."""
    tile = ctx.mat("oxblood", roughness=0.25)
    boxes = [((0, 5.0, 4.5), (width, 10.0, 9.0), 0), ((0, -0.15, 8.6), (width + 0.4, 0.3, 0.8), 0), ((0, -0.2, 4.6), (width - 0.2, 0.14, 0.9), 1)]
    for k in range(3):
        ax = -width / 3 + k * width / 3
        boxes += [((ax, -0.05, 1.8), (2.6, 0.12, 3.6), 3 if closed else 2), ((ax, -0.06, 6.6), (2.2, 0.12, 2.4), 2)]
        for b in range(5):
            boxes.append(((ax, -0.12, 3.65 + b * 0.08), (2.6 - b * 0.35, 0.12, 0.1), 0))
    mats = [tile, ctx.mat("fascia_navy", roughness=0.4), ctx.palette.glass(f"{name} glass", "glass_dark") if not lit else ctx.palette.emissive(f"{name} lit", (1.0, 0.92, 0.75), 1.5), ctx.mat("shutter_grey", roughness=0.5, metallic=0.4)]
    front = multi_box(ctx, name, boxes, mats, loc, (0, 0, rot))
    sign = props.sign_text(ctx, f"{name}.sign", "UNDERGROUND", (0, -0.3, 4.38), size=0.55, colour="white", emission=1.5 if lit else 0.0)
    parent(sign, front)
    sign.location = (0, -0.3, 4.38)
    sign.rotation_euler = (math.pi / 2, 0, 0)
    if closed:
        notice = props.sign_text(ctx, f"{name}.notice", "STATION CLOSED", (0, -0.2, 2.3), size=0.3, colour="barrier_red")
        parent(notice, front)
        notice.location = (0, -0.2, 2.3)
        notice.rotation_euler = (math.pi / 2, 0, 0)
        plate = box(ctx, f"{name}.notice_plate", (3.0, 0.05, 0.8), (0, -0.16, 2.4), ctx.mat("white", roughness=0.5))
        parent(plate, front)
        plate.location = (0, -0.16, 2.4)
    ctx.tag("station", front)
    return front


def elizabeth_tower(ctx, name, loc, scale=1.0, lit=False):
    """The clock tower at Westminster (96 m): panelled shaft, four lit clock faces, belfry, spire."""
    s = scale
    stone = ctx.mat("westminster_stone", roughness=0.8)
    shade = ctx.mat("westminster_shade", roughness=0.8)
    gilt = ctx.mat("gilt", roughness=0.35, metallic=0.8)
    slate = ctx.mat("spire_slate", roughness=0.5)
    face = ctx.palette.emissive(f"{name} face", "clock_face", 3.0) if lit else ctx.mat("clock_face", roughness=0.4)
    hands = ctx.mat("black", roughness=0.4)
    w = 12.0 * s
    boxes = [((0, 0, 27.5 * s), (w, w, 55 * s), 0), ((0, 0, 2.0 * s), (w + 1.2 * s, w + 1.2 * s, 4 * s), 0)]
    for k in range(6):
        off = (-w / 2 + (k + 0.5) * w / 6)
        for side in (-1, 1):
            boxes.append(((off, side * (w / 2 + 0.08), 30 * s), (0.5 * s, 0.2, 44 * s), 1))
            boxes.append(((side * (w / 2 + 0.08), off, 30 * s), (0.2, 0.5 * s, 44 * s), 1))
    boxes.append(((0, 0, 62 * s), (w + 1.6 * s, w + 1.6 * s, 14 * s), 0))
    for side in (-1, 1):
        boxes.append(((0, side * (w / 2 + 0.85 * s), 62 * s), (8.2 * s, 0.2, 8.2 * s), 2))
        boxes.append(((side * (w / 2 + 0.85 * s), 0, 62 * s), (0.2, 8.2 * s, 8.2 * s), 2))
    boxes.append(((0, 0, 72 * s), (w - 0.5 * s, w - 0.5 * s, 6 * s), 0))
    for cx_, cy_ in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        boxes.append(((cx_ * (w / 2 + 0.3), cy_ * (w / 2 + 0.3), 72 * s), (1.2 * s, 1.2 * s, 9 * s), 2))
    tower = multi_box(ctx, name, boxes, [stone, shade, gilt], loc)
    disc_boxes = []
    cylinders = []
    for a in range(4):
        ang = a * math.pi / 2
        nx, ny = math.cos(ang), math.sin(ang)
        cx_, cy_ = nx * (w / 2 + 1.0 * s), ny * (w / 2 + 1.0 * s)
        axis = "x" if abs(nx) > 0.5 else "y"
        cylinders.append(((cx_, cy_, 62 * s), 3.5 * s, 0.25, axis, 0))
        hx, hy = nx * (w / 2 + 1.2 * s), ny * (w / 2 + 1.2 * s)
        disc_boxes.append(((hx, hy, 62.9 * s), (0.25 if axis == "x" else 0.35 * s, 0.35 * s if axis == "x" else 0.25, 2.2 * s), 1))
        disc_boxes.append(((hx + (0 if axis == "x" else 1.0 * s), hy + (1.0 * s if axis == "x" else 0), 62 * s), (0.25 if axis == "x" else 2.4 * s, 2.4 * s if axis == "x" else 0.25, 0.3 * s), 1))
    faces = multi_shape(ctx, f"{name}.faces", disc_boxes, cylinders, [face, hands], loc)
    parent(faces, tower)
    faces.location = (0, 0, 0)
    spire = cone(ctx, f"{name}.spire", (w - 1.0 * s) * 0.72, 22 * s, (0, 0, 75 * s), slate, segments=4, anchor="base", rot=(0, 0, math.pi / 4))
    parent(spire, tower)
    spire.location = (0, 0, 75 * s)
    tip = cone(ctx, f"{name}.tip", 0.8 * s, 6 * s, (0, 0, 96 * s), gilt, segments=6, anchor="base")
    parent(tip, tower)
    tip.location = (0, 0, 96 * s)
    ctx.tag("landmark", tower)
    ctx.anchor(f"{name}.clock", (loc[0], loc[1], loc[2] + 62 * s))
    ctx.anchor(f"{name}.top", (loc[0], loc[1], loc[2] + 100 * s))
    return tower


def palace(ctx, name, loc, length=260.0, rot=0.0, lit=None):
    """Palace of Westminster river front along local +X from loc, facing local -Y (the river):
    buttressed Gothic range with pinnacles, a slate roof, the central spire and Victoria Tower."""
    stone = ctx.mat("westminster_stone", roughness=0.85)
    shade = ctx.mat("westminster_shade", roughness=0.85)
    slate = ctx.mat("spire_slate", roughness=0.6)
    glass = ctx.palette.glass(f"{name} glass", "glass_dark")
    mats = [stone, shade, slate, glass, lit or glass, ctx.mat("gilt", roughness=0.35, metallic=0.8)]
    rng = random.Random(11)
    depth, height = 32.0, 24.0
    boxes = [((length / 2, depth / 2, height / 2), (length, depth, height), 0), ((length / 2, depth / 2, height + 4.0), (length - 4, depth - 6, 8.0), 2)]
    bays = int(length / 5.5)
    for b in range(bays + 1):
        bx = b * length / bays
        boxes.append(((bx, -0.3, height / 2 + 1.5), (0.8, 0.8, height + 3.0), 1))
        boxes.append(((bx, -0.3, height + 3.6), (0.5, 0.5, 2.6), 0))
    for b in range(bays):
        bx = (b + 0.5) * length / bays
        for z in (5.0, 11.5, 18.0):
            boxes.append(((bx, -0.08, z), (2.4, 0.12, 4.2), 4 if rng.random() < 0.5 else 3))
    for px in (0.0, length * 0.33, length * 0.66):
        boxes.append(((px + 6, -2.0, height / 2 + 3), (12.0, 4.0, height + 6), 0))
        boxes.append(((px + 6, -2.0, height + 7.5), (12.6, 4.6, 1.2), 1))
    body = multi_box(ctx, name, boxes, mats, loc, (0, 0, rot))
    # Victoria Tower at the start of the range (the south end when the range runs north) and the
    # octagonal central spire, in palace-local space
    vt = multi_box(ctx, f"{name}.victoria", [((0, 0, 44), (22, 22, 88), 0), ((0, 0, 90), (23, 23, 4), 1)] + [((cx_ * 11, cy_ * 11, 50), (2.4, 2.4, 100), 1) for cx_ in (-1, 1) for cy_ in (-1, 1)] + [((0, -11.1, 30 + k * 14), (3.0, 0.2, 9.0), 3) for k in range(4)], mats, (8, 18, 0))
    central = cylinder(ctx, f"{name}.central", 7.0, 58, (length * 0.45, 16, 0), stone, segments=8, anchor="base")
    spire = cone(ctx, f"{name}.central_spire", 7.5, 34, (length * 0.45, 16, 58), slate, segments=8, anchor="base")
    for obj in (vt, central, spire):
        parent(obj, body)
    ctx.tag("landmark", body)
    return body


def london_eye(ctx, name, loc, rot=0.0, radius=60.0, lit=False):
    """The observation wheel: rim, spokes, 32 capsules and the A-frame legs, facing local Y."""
    white = ctx.mat("eye_white", roughness=0.35, metallic=0.4)
    pod = ctx.palette.glass(f"{name} pods", "glass") if not lit else ctx.palette.emissive(f"{name} pods", (0.85, 0.9, 1.0), 2.0)
    hub_z = radius + 8.0
    cyl = []
    boxes = []
    n = 48
    for k in range(n):
        a0, a1 = math.tau * k / n, math.tau * (k + 1) / n
        x0, z0 = radius * math.cos(a0), hub_z + radius * math.sin(a0)
        x1, z1 = radius * math.cos(a1), hub_z + radius * math.sin(a1)
        seg = math.hypot(x1 - x0, z1 - z0)
        boxes.append((((x0 + x1) / 2, 0, (z0 + z1) / 2), (seg, 1.6, 1.0), 0, -math.atan2(z1 - z0, x1 - x0)))
    for k in range(32):
        a = math.tau * k / 32
        boxes.append(((radius / 2 * math.cos(a), 0, hub_z + radius / 2 * math.sin(a)), (radius, 0.2, 0.2), 0, -a))
    verts, faces, face_mats = [], [], []
    for (px, py, pz), (sx, sy, sz), m, ry in boxes:
        c, s = math.cos(ry), math.sin(ry)
        base = len(verts)
        for dx, dy, dz in ((-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1), (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)):
            lx, ly, lz = dx * sx / 2, dy * sy / 2, dz * sz / 2
            verts.append((px + lx * c + lz * s, py + ly, pz - lx * s + lz * c))
        faces += [(base, base + 1, base + 2, base + 3), (base + 4, base + 7, base + 6, base + 5), (base, base + 4, base + 5, base + 1), (base + 1, base + 5, base + 6, base + 2), (base + 2, base + 6, base + 7, base + 3), (base + 3, base + 7, base + 4, base)]
        face_mats += [m] * 6
    wheel = mesh_from_pydata(ctx, name, verts, faces, [white], loc, (0, 0, rot), face_mats=face_mats)
    for k in range(32):
        a = math.tau * k / 32
        cyl.append(((radius * 1.04 * math.cos(a), 0, hub_z + radius * 1.04 * math.sin(a)), 1.6, 3.6, "y", 0))
    pods = multi_shape(ctx, f"{name}.pods", [], cyl, [pod])
    parent(pods, wheel)
    legs = multi_box(ctx, f"{name}.legs", [((0, -radius * 0.35, hub_z / 2), (2.0, 2.0, hub_z * 1.15), 0), ((0, -radius * 0.35 - 6, hub_z / 2 - 4), (2.0, 2.0, hub_z * 1.1), 0), ((0, 0, hub_z), (5.0, 5.0, 5.0), 0)], [white])
    parent(legs, wheel)
    legs.rotation_euler = (math.radians(-18), 0, 0)
    ctx.tag("landmark", wheel)
    return wheel


def shard(ctx, name, loc, height=310.0, lit=False):
    glass = ctx.mat("shard_glass", roughness=0.12, metallic=0.5)
    tower = cone(ctx, name, 28.0, height * 0.9, loc, glass, segments=8, anchor="base", tip=3.5)
    for k in range(4):
        a = k * math.pi / 2 + 0.4
        spike = cone(ctx, f"{name}.shard{k}", 2.4, height * 0.14, (2.2 * math.cos(a), 2.2 * math.sin(a), height * 0.86), glass, segments=3, anchor="base")
        parent(spike, tower)
    if lit:
        beacon = ico(ctx, f"{name}.beacon", 1.2, (0, 0, height * 0.98), ctx.palette.emissive(f"{name} beacon", "beacon_red", 8.0))
        parent(beacon, tower)
    ctx.tag("landmark", tower)
    return tower


def st_pauls(ctx, name, loc, rot=0.0):
    stone = ctx.mat("portland_stone", roughness=0.85)
    lead = ctx.mat("lead_grey", roughness=0.6)
    body = multi_box(ctx, name, [((0, 0, 14), (34, 150, 28), 0), ((0, 15, 14), (75, 30, 26), 0), ((0, -72, 18), (40, 10, 36), 0)] + [((sx * 14, -76, 34), (8, 8, 30), 0) for sx in (-1, 1)], [stone], loc, (0, 0, rot))
    drum = cylinder(ctx, f"{name}.drum", 17.0, 22.0, (0, 15, 26), stone, segments=16, anchor="base")
    dome = ico(ctx, f"{name}.dome", 17.0, (0, 15, 47), lead, subdiv=2, scale=(1, 1, 1.15))
    lantern = cylinder(ctx, f"{name}.lantern", 3.0, 16.0, (0, 15, 64), stone, segments=8, anchor="base")
    cross = cone(ctx, f"{name}.cross", 1.4, 8.0, (0, 15, 80), ctx.mat("gilt", roughness=0.35, metallic=0.8), segments=6, anchor="base")
    for obj in (drum, dome, lantern, cross):
        parent(obj, body)
    ctx.tag("landmark", body)
    return body


def bridge(ctx, name, start, end, width=26.0, deck=9.0, arches=5, colour="bridge_green", lit=False):
    sx, sy = start
    ex, ey = end
    length = math.hypot(ex - sx, ey - sy)
    angle = math.atan2(ey - sy, ex - sx)
    paint = ctx.mat(colour, roughness=0.5)
    stone = ctx.mat("portland_stone", roughness=0.85)
    boxes = [((0, 0, deck), (length, width, 1.4), 0), ((0, width / 2 - 0.3, deck + 1.2), (length, 0.5, 1.1), 0), ((0, -width / 2 + 0.3, deck + 1.2), (length, 0.5, 1.1), 0), ((0, 0, deck + 0.75), (length, width - 1.2, 0.1), 2)]
    for i in range(1, arches):
        px = -length / 2 + i * length / arches
        boxes.append(((px, 0, deck / 2 - 1), (5.0, width + 1.0, deck + 2), 1))
    obj = multi_box(ctx, name, boxes, [paint, stone, ctx.mat("tarmac_wet", roughness=0.2)], ((sx + ex) / 2, (sy + ey) / 2, 0.0), (0, 0, angle))
    ctx.tag("bridge", obj)
    return obj


def thames_barrier(ctx, name, start, end, piers=9, level=4.0):
    """Row of piers topped with stainless-steel hoods across the river; gates raised between them."""
    sx, sy = start
    ex, ey = end
    length = math.hypot(ex - sx, ey - sy)
    angle = math.atan2(ey - sy, ex - sx)
    concrete = ctx.mat("concrete", roughness=0.8)
    shell = ctx.mat("barrier_steel", roughness=0.15, metallic=0.95)
    gate = ctx.mat("dark_steel", roughness=0.5)
    boxes = []
    hoods = []
    for i in range(piers):
        px = -length / 2 + (i + 0.5) * length / piers
        boxes.append(((px, 0, 2.0), (8.0, 46.0, 14.0), 0))
        if i < piers - 1:
            boxes.append(((px + length / piers / 2, 0, level - 2.0), (length / piers - 8.0, 2.2, 9.0), 1))
        hoods.append(px)
    obj = multi_box(ctx, name, boxes, [concrete, gate], ((sx + ex) / 2, (sy + ey) / 2, -6.0), (0, 0, angle))
    verts, faces = [], []
    n = 10
    for px in hoods:
        # a pointed stainless shell along the river: left eave, ridge, right eave per section
        base = len(verts)
        for k in range(n + 1):
            t = k / n
            bulge = math.sin(math.pi * t)
            y = (t - 0.5) * 32.0
            verts += [(px - 0.8 - 5.6 * bulge ** 0.5, y * 1.3, 9.0), (px, y * 1.3, 9.0 + 18.0 * bulge), (px + 0.8 + 5.6 * bulge ** 0.5, y * 1.3, 9.0)]
        for k in range(n):
            a = base + 3 * k
            faces += [(a, a + 3, a + 4, a + 1), (a + 1, a + 4, a + 5, a + 2)]
    hoods_obj = mesh_from_pydata(ctx, f"{name}.hoods", verts, faces, [shell], smooth=True)
    parent(hoods_obj, obj)
    ctx.tag("barrier", obj)
    return obj


def substation(ctx, name, loc, rot=0.0):
    """Fenced electricity substation: transformers with cooling fins, bus bars and a danger sign."""
    grey = ctx.mat("transformer_grey", roughness=0.4, metallic=0.1)
    boxes = []
    for k in range(3):
        tx = -8 + k * 8
        boxes.append(((tx, 0, 1.6), (4.0, 3.0, 3.2), 0))
        for f in range(8):
            boxes.append(((tx - 1.6 + f * 0.45, -1.7, 1.6), (0.12, 0.4, 2.8), 0))
        for b in range(3):
            boxes.append(((tx - 1.0 + b, 0.6, 3.9), (0.25, 0.25, 1.4), 2))
    boxes.append(((0, 0.6, 5.0), (20.0, 0.15, 0.15), 1))
    for side in (-1, 1):
        boxes.append(((side * 13, 0, 1.2), (0.08, 12.0, 2.4), 3))
        boxes.append(((0, side * 6, 1.2), (26.0, 0.08, 2.4), 3))
    fence = ctx.palette.make(f"{name} fence", ctx.palette.colour("dark_steel"), roughness=0.6, alpha=0.3)
    obj = multi_box(ctx, name, boxes, [grey, ctx.mat("steel", roughness=0.3, metallic=0.7), ctx.mat("white", roughness=0.3), fence], loc, (0, 0, rot))
    sign = props.sign_text(ctx, f"{name}.danger", "DANGER OF DEATH", (0, -6.1, 1.5), size=0.3, colour="barrier_red")
    parent(sign, obj)
    sign.location = (0, -6.1, 1.5)
    sign.rotation_euler = (math.pi / 2, 0, 0)
    ctx.tag("substation", obj)
    return obj


def mould_patch(ctx, name, centre, normal_axis, size, seed=0):
    """Black mould on a wall plane (normal_axis 'x' or 'y'): a dark core with a ring of speckled
    spores around it, one mesh tagged `mould` (grow it with a scale event)."""
    rng = random.Random(seed)
    material = ctx.palette.make(f"{name} spores", ctx.palette.colour("mould"), roughness=1.0, alpha=0.88)
    verts, faces = [], []

    def blob(cu, cv, radius, sides):
        base = len(verts)
        for k in range(sides):
            a = math.tau * k / sides
            r = radius * rng.uniform(0.5, 1.2)
            u, v = cu + r * math.cos(a), cv + r * math.sin(a) * 0.8
            verts.append((0.0, u, v) if normal_axis == "x" else (u, 0.0, v))
        faces.append(tuple(range(base, base + sides)))

    blob(0.0, 0.0, size * 0.6, 16)
    for _ in range(40):
        a, r = rng.uniform(0, math.tau), size * rng.uniform(0.45, 1.2)
        blob(r * math.cos(a), r * math.sin(a) * 0.8, size * rng.uniform(0.03, 0.12), 6)
    obj = mesh_from_pydata(ctx, name, verts, faces, [material], centre)
    obj.visible_shadow = False
    ctx.tag("mould", obj)
    return obj
