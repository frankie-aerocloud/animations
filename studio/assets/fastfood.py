"""Assets for "The Month America Ditched McDonald's": generic fast-food restaurants (no real logos,
names or trade dress: each chain is a colour scheme and a plain word on its sign), drive-through
lanes, menu boards and pole signs, an independent diner and café, trays of food, kitchen kit,
delivery pallets, produce crates, a backyard grill and a struggling franchise's paperwork.
Restaurant fronts face local -Y; the drive-through window is on local +X."""

from __future__ import annotations

import math

from studio.assets import props, vehicles
from studio.assets.meshes import merged_boxes
from studio.blender.primitives import add_noise, box, cylinder, empty, ico, key, mesh_from_pydata, parent

# chain -> (walls, band, roof, accent, sign words). The giant is the chain the film is about.
BRANDS = {
    "giant": ("giant_wall", "giant_red", "giant_roof", "giant_yellow", "BURGERS"),
    "flame": ("flame_wall", "flame_blue", "flame_roof", "flame_orange", "GRILL HOUSE"),
    "square": ("square_wall", "square_red", "square_roof", "square_white", "BURGER BAR"),
    "taco": ("taco_wall", "taco_purple", "taco_roof", "taco_pink", "TACOS"),
}
CAR_COLOURS = ("white", "black", "stone", "red", "navy", "dark_steel", "teal", "silver_car")


def sign(ctx, name, words, loc, size=0.5, colour="sign_white", emission=0.0, rot=0.0):
    """Upright lettering facing local -Y (turned by `rot` about Z)."""
    label = props.sign_text(ctx, name, words, loc, size=size, colour=colour, emission=emission)
    label.rotation_euler = (math.pi / 2, 0.0, rot)
    return label


def restaurant(ctx, name, loc, rot, brand, lit=False, promo=None, closed=False):
    """A free-standing fast-food restaurant in a chain's colours: glazed front with doors, a
    coloured band and roof edge, the drive-through window on +X, a pole sign with the chain's
    word and a drive-through menu board. promo puts a banner across the front."""
    walls, band, roof, accent, words = BRANDS[brand]
    root = empty(ctx, name, loc, (0.0, 0.0, rot))
    w, d, h = 18.0, 13.0, 4.6
    glow = ctx.palette.emissive(f"{name} windows", "window_warm", 2.5) if lit else ctx.mat("glass_shop", roughness=0.1)
    boxes = [((0, 0, h / 2), (w, d, h), 0), ((0, 0, h + 0.6), (w + 0.6, d + 0.6, 1.2), 1), ((0, 0, h + 1.25), (w + 0.2, d + 0.2, 0.1), 2)]
    boxes += [((x, -d / 2 - 0.02, 1.7), (2.6, 0.06, 2.6), 3) for x in (-6.0, -3.0, 3.0, 6.0)]
    boxes += [((0, -d / 2 - 0.03, 1.25), (2.2, 0.06, 2.5), 4)]
    boxes += [((w / 2 + 0.02, 1.0, 1.6), (0.06, 2.2, 1.4), 3), ((w / 2 + 0.8, 1.0, 2.6), (1.6, 3.0, 0.15), 1)]
    boxes += [((x, -d / 2 - 0.05, h - 0.35), (0.5, 0.1, 0.5), 5) for x in (-8.0, 8.0)]
    body = merged_boxes(ctx, f"{name}.body", boxes, [ctx.mat(walls, roughness=0.7), ctx.mat(band, roughness=0.5), ctx.mat(roof, roughness=0.6), glow, ctx.mat("door_glass", roughness=0.1), ctx.mat(accent, roughness=0.5)])
    parent(body, root)
    pole = merged_boxes(ctx, f"{name}.pole", [((0, 0, 5.0), (0.5, 0.5, 10.0), 0), ((0, 0, 11.2), (4.2, 0.6, 2.6), 1), ((0, -0.32, 11.2), (3.8, 0.04, 2.2), 2)], [ctx.mat("steel_dark_ff", roughness=0.5), ctx.mat(band, roughness=0.4), ctx.palette.emissive(f"{name} sign face", accent, 1.6 if lit else 0.6)], (w / 2 + 3.0, -d / 2 - 6.0, 0.0))
    parent(pole, root)
    label = sign(ctx, f"{name}.sign_words", words, (w / 2 + 3.0, -d / 2 - 6.4, 10.95), size=0.55, colour=band, emission=0.0)
    parent(label, root)
    front = sign(ctx, f"{name}.front_words", words, (0.0, -d / 2 - 0.35, h + 0.45), size=0.7, colour=accent)
    parent(front, root)
    board = merged_boxes(ctx, f"{name}.menu_board", [((0, 0, 1.2), (0.2, 2.4, 1.6), 0), ((-0.11, 0, 1.25), (0.02, 2.2, 1.4), 1), ((0, -1.6, 0.6), (0.3, 0.3, 1.2), 0)] + menu_items(-0.125, 2.2, 1.4, 1.25, axis="y"), [ctx.mat("steel_dark_ff", roughness=0.5), ctx.palette.emissive(f"{name} menu", "menu_light", 1.4), ctx.mat("ink_black_ff", roughness=0.6), ctx.mat(band, roughness=0.5), ctx.mat("bun", roughness=0.6), ctx.mat("fries", roughness=0.6)], (w / 2 + 4.5, d / 2 - 1.0, 0.0))
    parent(board, root)
    lane = [((w / 2 + 3.5, 0.5, 0.015), (3.4, d + 11.0, 0.03), 0), ((0.0, d / 2 + 5.5, 0.015), (w + 10.4, 3.4, 0.03), 0), ((-w / 2 - 3.5, -1.5, 0.015), (3.4, d + 9.0, 0.03), 0)]
    lane += [((w / 2 + 1.6, 0.5, 0.08), (0.3, d + 8.0, 0.16), 1), ((-w / 2 - 1.6, 0.5, 0.08), (0.3, d + 6.0, 0.16), 1), ((0.0, d / 2 + 3.6, 0.08), (w + 3.0, 0.3, 0.16), 1)]
    surface = merged_boxes(ctx, f"{name}.lane", lane, [ctx.mat("lane_asphalt", roughness=0.9), ctx.mat("curb", roughness=0.8)])
    parent(surface, root)
    painted = props.sign_text(ctx, f"{name}.lane_words", "DRIVE THRU", (-w / 2 - 3.5, -d / 2 - 3.0, 0.04), size=0.7, rot=(0.0, 0.0, math.pi / 2), colour="lane_white")
    parent(painted, root)
    if promo:
        banner = merged_boxes(ctx, f"{name}.banner", [((0, 0, 0), (9.0, 0.08, 1.3), 0)], [ctx.mat("banner_yellow", roughness=0.7)], (0.0, -d / 2 - 0.2, h - 1.2))
        parent(banner, root)
        words_obj = sign(ctx, f"{name}.banner_words", promo, (0.0, -d / 2 - 0.27, h - 1.45), size=0.55, colour="giant_red")
        parent(words_obj, root)
    if closed:
        shut = sign(ctx, f"{name}.closed", "CLOSED", (0.0, -d / 2 - 0.08, 1.9), size=0.35, colour="giant_red")
        parent(shut, root)
    return root


def menu_items(x, width, height, z, axis="x", rows=5, cols=3):
    """Boxes for a lit menu board's contents: food pictures, item lines and prices in columns,
    laid on a board facing -X (axis "y": the board runs along Y) or -Y (axis "x")."""
    boxes = []
    for c in range(cols):
        for r in range(rows):
            u = -width / 2 + (c + 0.5) * width / cols
            v = z + height / 2 - (r + 0.7) * height / (rows + 0.4)
            for du, size, index in ((-0.12 * width / cols * 2, 0.16 * width / cols * 2, 4 if r % 2 else 5), (0.05 * width / cols * 2, 0.22 * width / cols * 2, 2), (0.22 * width / cols * 2, 0.07 * width / cols * 2, 3)):
                if axis == "y":
                    boxes.append(((x, u + du, v), (0.01, size, height / (rows + 0.4) * (0.6 if index > 3 else 0.2)), index))
                else:
                    boxes.append(((u + du, x, v), (size, 0.01, height / (rows + 0.4) * (0.6 if index > 3 else 0.2)), index))
    return boxes


def lane_points(loc, rot, d=13.0, w=18.0):
    """Car positions along a restaurant's drive-through lane, nearest the window first: world
    (x, y, car heading in degrees). The lane enters at the front left, runs up the -X side, along
    the back and down the +X side to the window."""
    x0, y0 = loc
    c, s = math.cos(rot), math.sin(rot)
    local = [(w / 2 + 3.5, 1.0, 180.0), (w / 2 + 3.5, 7.0, 180.0)]
    local += [(w / 2 - 2.0 - k * 6.0, d / 2 + 5.5, -90.0) for k in range(5)]
    local += [(-w / 2 - 3.5, d / 2 + 1.0 - k * 6.0, 0.0) for k in range(4)]
    out = []
    for lx, ly, heading in local:
        out.append((x0 + lx * c - ly * s, y0 + lx * s + ly * c, heading + math.degrees(rot)))
    return out


def queue(ctx, name, loc, rot, count, lit=False):
    """Cars waiting in a restaurant's drive-through lane, the first at the window."""
    rng = ctx.rng
    for i, (x, y, heading) in enumerate(lane_points(loc, rot)[:count]):
        vehicles.car(ctx, f"{name}{i}", (x, y, 0.05), math.radians(heading), rng.choice(CAR_COLOURS), lit=lit)


def burger(ctx, name, loc, scale=1.0):
    """A burger: bun, lettuce, patty, cheese, bun."""
    s = scale
    x, y, z = loc
    parts = [(0.0, 0.03, 0.06, "bun"), (0.06, 0.012, 0.064, "lettuce"), (0.072, 0.025, 0.062, "patty"), (0.097, 0.008, 0.065, "cheese"), (0.105, 0.045, 0.06, "bun")]
    top = None
    for k, (dz, height, radius, colour) in enumerate(parts):
        piece = cylinder(ctx, f"{name}.{k}", radius * s, height * s, (x, y, z + dz * s), ctx.mat(colour, roughness=0.6), segments=14, anchor="base", radius2=radius * s * (0.7 if k == 4 else 1.0))
        top = top or piece
    return top


def tray(ctx, name, loc, rot=0.0, colour="tray_red"):
    """A tray with a burger, a carton of fries and a drink."""
    x, y, z = loc
    root = empty(ctx, name, loc, (0.0, 0.0, rot))
    t = box(ctx, f"{name}.tray", (0.42, 0.32, 0.02), (0.0, 0.0, 0.01), ctx.mat(colour, roughness=0.5))
    parent(t, root)
    b = burger(ctx, f"{name}.burger", (-0.08, 0.02, 0.02), 1.0)
    parent(b, root)
    fries = merged_boxes(ctx, f"{name}.fries", [((0, 0, 0.06), (0.08, 0.05, 0.1), 0)] + [((dx, dy, 0.13), (0.012, 0.012, 0.07), 1) for dx in (-0.025, -0.008, 0.01, 0.026) for dy in (-0.01, 0.012)], [ctx.mat("fries_box", roughness=0.5), ctx.mat("fries", roughness=0.7)], (0.1, -0.06, 0.02))
    parent(fries, root)
    cup = cylinder(ctx, f"{name}.cup", 0.04, 0.16, (0.12, 0.08, 0.02), ctx.mat("cup_white", roughness=0.5), segments=12, anchor="base", radius2=0.048)
    parent(cup, root)
    return root


def nuggets(ctx, name, loc, rot=0.0):
    """A carton of chicken nuggets, lid open."""
    rng = ctx.rng
    boxes = [((0, 0, 0.04), (0.16, 0.11, 0.08), 0), ((0, 0.07, 0.11), (0.16, 0.03, 0.1), 0)]
    boxes += [((rng.uniform(-0.05, 0.05), rng.uniform(-0.03, 0.03), 0.09), (0.045, 0.035, 0.025), 1) for _ in range(6)]
    return merged_boxes(ctx, name, boxes, [ctx.mat("fries_box", roughness=0.5), ctx.mat("nugget", roughness=0.7)], loc, (0.0, 0.0, rot))


def fryer_station(ctx, name, loc, rot=0.0, running=False):
    """Twin fryers with their baskets hung up out of the oil (or down in it), a fry dump with a
    small heap of fries under the heat lamp, a stack of empty fry cartons and a hood above."""
    rng = ctx.rng
    root = empty(ctx, name, loc, (0.0, 0.0, rot))
    lift = 1.0 if running else 1.32
    boxes = [((0, 0, 0.45), (1.6, 0.8, 0.9), 0), ((-0.4, 0, 0.92), (0.66, 0.56, 0.04), 1), ((0.4, 0, 0.92), (0.66, 0.56, 0.04), 1), ((1.3, 0, 0.45), (1.0, 0.8, 0.9), 0), ((1.3, 0, 0.93), (0.9, 0.7, 0.04), 0)]
    for bx in (-0.4, 0.4):
        boxes += [((bx, -0.05, lift), (0.5, 0.35, 0.02), 3), ((bx - 0.24, -0.05, lift + 0.1), (0.02, 0.35, 0.2), 3), ((bx + 0.24, -0.05, lift + 0.1), (0.02, 0.35, 0.2), 3), ((bx, -0.22, lift + 0.1), (0.5, 0.02, 0.2), 3), ((bx, 0.12, lift + 0.1), (0.5, 0.02, 0.2), 3), ((bx, -0.42, lift + 0.15), (0.04, 0.3, 0.04), 3)]
    for _ in range(60):
        along = rng.random() < 0.5
        boxes.append(((1.3 + rng.uniform(-0.25, 0.25), rng.uniform(-0.18, 0.18), 0.97 + rng.uniform(0.0, 0.05)), (0.08, 0.014, 0.014) if along else (0.014, 0.08, 0.014), 2))
    boxes += [((1.3, 0, 1.55), (1.0, 0.45, 0.06), 4), ((0.4, 0.15, 2.5), (2.8, 0.9, 0.5), 3)]
    boxes += [((2.05, 0.1, 0.93 + k * 0.035), (0.11, 0.07, 0.03), 5) for k in range(10)]
    kit = merged_boxes(ctx, f"{name}.kit", boxes, [ctx.mat("steel_ff", roughness=0.3, metallic=0.7), ctx.mat("oil", roughness=0.1), ctx.mat("fries", roughness=0.7), ctx.mat("steel_dark_ff", roughness=0.4), ctx.palette.emissive(f"{name} heat lamp", "heat_lamp", 2.0 if running else 0.15), ctx.mat("fries_box", roughness=0.5)])
    parent(kit, root)
    return root


def grill_line(ctx, name, loc, rot=0.0, patties=0):
    """A flat-top grill with (or without) patties sizzling on it."""
    root = empty(ctx, name, loc, (0.0, 0.0, rot))
    boxes = [((0, 0, 0.45), (1.8, 0.8, 0.9), 0), ((0, 0, 0.93), (1.7, 0.7, 0.06), 1)]
    boxes += [((-0.7 + (k % 6) * 0.27, -0.2 + (k // 6) * 0.25, 0.975), (0.18, 0.18, 0.03), 2) for k in range(patties)]
    kit = merged_boxes(ctx, f"{name}.kit", boxes, [ctx.mat("steel_ff", roughness=0.3, metallic=0.7), ctx.mat("steel_dark_ff", roughness=0.4), ctx.mat("patty", roughness=0.7)])
    parent(kit, root)
    return root


def produce_crates(ctx, name, loc, rows=3, cols=4, layers=2, rot=0.0):
    """Stacked crates of lettuce, tomatoes, onions and potatoes."""
    rng = ctx.rng
    boxes = []
    for r in range(rows):
        for c in range(cols):
            for layer in range(layers):
                x, y, z = c * 0.62, r * 0.45, layer * 0.32
                kind = rng.randrange(4)
                boxes.append(((x, y, z + 0.13), (0.58, 0.4, 0.26), 0))
                boxes += [((x + dx, y + dy, z + 0.29), (0.1, 0.1, 0.08), 1 + kind) for dx in (-0.18, 0.0, 0.18) for dy in (-0.1, 0.1)]
    return merged_boxes(ctx, name, boxes, [ctx.mat("crate_wood_ff", roughness=0.8), ctx.mat("lettuce", roughness=0.7), ctx.mat("tomato", roughness=0.4), ctx.mat("onion", roughness=0.6), ctx.mat("potato", roughness=0.8)], loc, (0.0, 0.0, rot))


def pallet(ctx, name, loc, kind="buns", rot=0.0):
    """A shrink-wrapped pallet: bun trays, sacks of potatoes, boxed patties or cups."""
    goods = {"buns": "bun_bag", "potatoes": "potato_sack", "patties": "carton_ff", "cups": "cup_white"}[kind]
    boxes = [((0, 0, 0.07), (1.2, 1.0, 0.14), 0)]
    for layer in range(4):
        for i in range(3):
            for j in range(2):
                boxes.append(((-0.4 + i * 0.4, -0.25 + j * 0.5, 0.3 + layer * 0.32), (0.38, 0.48, 0.3), 1))
    boxes.append(((0, 0, 0.82), (1.22, 1.02, 1.36), 2))
    return merged_boxes(ctx, name, boxes, [ctx.mat("pallet_wood", roughness=0.9), ctx.mat(goods, roughness=0.7), ctx.mat("wrap_film", roughness=0.15, alpha=0.35)], loc, (0.0, 0.0, rot))


def calendar(ctx, name, loc, crossed=0, rot=0.0):
    """A wall calendar of 30 days with the first `crossed` struck through in red."""
    boxes = [((0, 0, 0), (1.4, 0.03, 1.2), 0)]
    for k in range(30):
        cx, cz = -0.54 + (k % 7) * 0.18, 0.38 - (k // 7) * 0.2
        boxes.append(((cx, -0.02, cz), (0.15, 0.01, 0.16), 1))
        if k < crossed:
            boxes.append(((cx, -0.035, cz), (0.16, 0.01, 0.03), 2))
    return merged_boxes(ctx, name, boxes, [ctx.mat("paper_white", roughness=0.8), ctx.mat("paper_cream", roughness=0.8), ctx.mat("ink_red", roughness=0.6)], loc, (0.0, 0.0, rot))


def billboard(ctx, name, loc, words, rot=0.0, colour="banner_yellow", ink="giant_red", sub=None):
    """A roadside billboard on two legs with big promotional lettering."""
    root = empty(ctx, name, loc, (0.0, 0.0, rot))
    frame = merged_boxes(ctx, f"{name}.frame", [((sx, 0.3, 4.5), (0.4, 0.4, 9.0), 0) for sx in (-4.0, 4.0)] + [((0, 0, 10.5), (12.0, 0.4, 4.0), 1), ((0, -0.22, 10.5), (11.6, 0.04, 3.6), 2)], [ctx.mat("steel_dark_ff", roughness=0.5), ctx.mat("steel_dark_ff", roughness=0.5), ctx.mat(colour, roughness=0.6)])
    parent(frame, root)
    label = sign(ctx, f"{name}.words", words, (0.0, -0.3, 10.8 if sub else 10.3), size=1.05, colour=ink)
    parent(label, root)
    if sub:
        under = sign(ctx, f"{name}.sub", sub, (0.0, -0.3, 9.4), size=0.55, colour=ink)
        parent(under, root)
    return root


def balloons(ctx, name, loc, count=7):
    """A bunch of party balloons on strings, swaying."""
    rng = ctx.rng
    root = empty(ctx, name, loc)
    for i in range(count):
        dx, dy, dz = rng.uniform(-0.6, 0.6), rng.uniform(-0.6, 0.6), rng.uniform(2.6, 3.4)
        ball = ico(ctx, f"{name}.{i}", 0.28, (dx, dy, dz), ctx.mat(rng.choice(("balloon_red", "balloon_blue", "balloon_yellow", "balloon_green")), roughness=0.25), subdiv=2, scale=(1.0, 1.0, 1.2), smooth=True)
        parent(ball, root)
        string = box(ctx, f"{name}.{i}.string", (0.01, 0.01, dz), (dx * 0.5, dy * 0.5, dz / 2), ctx.mat("cup_white", roughness=0.8))
        parent(string, root)
    key(root, "rotation_euler", 1)
    add_noise(root, "rotation_euler", 0.06, 1, ctx.frames, scale=30.0)
    return root


def bbq(ctx, name, loc, patties=6):
    """A backyard kettle grill with burgers cooking, and a side table."""
    x, y, z = loc
    kettle = cylinder(ctx, f"{name}.kettle", 0.33, 0.35, (x, y, 0.62), ctx.mat("grill_black", roughness=0.4), segments=16, anchor="base", radius2=0.4)
    merged_boxes(ctx, f"{name}.legs", [((x + dx, y + dy, 0.31), (0.04, 0.04, 0.62), 0) for dx, dy in ((0.25, 0), (-0.13, 0.22), (-0.13, -0.22))] + [((x, y, 0.985), (0.7, 0.7, 0.02), 1)] + [((x - 0.2 + (k % 3) * 0.2, y - 0.1 + (k // 3) * 0.2, 1.01), (0.13, 0.13, 0.03), 2) for k in range(patties)], [ctx.mat("grill_black", roughness=0.4), ctx.mat("steel_ff", roughness=0.3, metallic=0.7), ctx.mat("patty", roughness=0.7)])
    merged_boxes(ctx, f"{name}.table", [((0, 0, 0.75), (1.0, 0.6, 0.05), 0)] + [((dx, dy, 0.37), (0.05, 0.05, 0.74), 0) for dx in (-0.45, 0.45) for dy in (-0.25, 0.25)] + [((-0.25, 0.0, 0.8), (0.4, 0.3, 0.05), 1), ((0.2, 0.0, 0.82), (0.25, 0.25, 0.08), 2)], [ctx.mat("table_wood", roughness=0.7), ctx.mat("lettuce", roughness=0.7), ctx.mat("bun", roughness=0.6)], (x + 1.0, y, z))
    return kettle


def paperwork(ctx, name, loc, rot=0.0):
    """A desk heaped with bills and invoices, a laptop and a calculator."""
    rng = ctx.rng
    boxes = [((0, 0, 0.74), (1.6, 0.8, 0.04), 0)] + [((dx, dy, 0.37), (0.05, 0.05, 0.74), 1) for dx in (-0.75, 0.75) for dy in (-0.35, 0.35)]
    for k in range(12):
        boxes.append(((rng.uniform(-0.6, 0.3), rng.uniform(-0.25, 0.25), 0.765 + k * 0.004), (0.21, 0.29, 0.003), 2 if k % 4 else 3))
    boxes += [((0.5, 0.05, 0.77), (0.34, 0.24, 0.02), 4), ((0.5, 0.17, 0.89), (0.34, 0.02, 0.22), 5), ((-0.2, -0.28, 0.77), (0.1, 0.15, 0.02), 4)]
    return merged_boxes(ctx, name, boxes, [ctx.mat("table_wood", roughness=0.6), ctx.mat("steel_dark_ff", roughness=0.4), ctx.mat("paper_white", roughness=0.8), ctx.mat("ink_red", roughness=0.7), ctx.mat("steel_dark_ff", roughness=0.4), ctx.palette.emissive(f"{name} screen", "screen_glow", 1.2)], loc, (0.0, 0.0, rot))


def rota(ctx, name, loc, struck=6, rot=0.0):
    """A staff rota on the wall: a grid of shifts with some struck off."""
    boxes = [((0, 0, 0), (1.5, 0.03, 1.0), 0)]
    for r in range(6):
        for c in range(7):
            boxes.append(((-0.6 + c * 0.2, -0.02, 0.35 - r * 0.14), (0.17, 0.01, 0.1), 1))
            if (r * 7 + c) % 5 == 0 and struck > 0:
                struck -= 1
                boxes.append(((-0.6 + c * 0.2, -0.03, 0.35 - r * 0.14), (0.19, 0.01, 0.025), 2))
    return merged_boxes(ctx, name, boxes, [ctx.mat("paper_white", roughness=0.8), ctx.mat("shift_blue", roughness=0.7), ctx.mat("ink_red", roughness=0.6)], loc, (0.0, 0.0, rot))


def plate_graphic(ctx, name, loc, size=2.6):
    """A big plate split down the middle: a burger and fries on one side, a salad on the other."""
    x, y, z = loc
    plate = cylinder(ctx, f"{name}.plate", size / 2, 0.06, (x, y, z), ctx.mat("cup_white", roughness=0.4), segments=32, rot=(math.pi / 2, 0.0, 0.0))
    mesh_from_pydata(ctx, f"{name}.divider", [(x - 0.02, y - 0.05, z - size / 2), (x + 0.02, y - 0.05, z - size / 2), (x + 0.02, y - 0.05, z + size / 2), (x - 0.02, y - 0.05, z + size / 2)], [(0, 1, 2, 3)], [ctx.mat("ink_black_ff", roughness=0.5)])
    left = [((x - size * 0.22, y - 0.1, z + dz), (size * 0.28, 0.06, 0.12), m) for dz, m in ((-0.15, 0), (0.0, 1), (0.08, 2), (0.2, 0))] + [((x - size * 0.3 + k * 0.08, y - 0.1, z - 0.55), (0.04, 0.06, 0.3), 3) for k in range(5)]
    right = [((x + size * 0.2 + dx, y - 0.1, z + dz), (0.16, 0.06, 0.16), 4 + (k % 3)) for k, (dx, dz) in enumerate(((-0.25, 0.2), (0.0, 0.3), (0.25, 0.15), (-0.2, -0.15), (0.1, -0.05), (0.3, -0.3), (-0.05, -0.4)))]
    merged_boxes(ctx, f"{name}.food", left + right, [ctx.mat("bun", roughness=0.6), ctx.mat("patty", roughness=0.7), ctx.mat("cheese", roughness=0.5), ctx.mat("fries", roughness=0.7), ctx.mat("lettuce", roughness=0.7), ctx.mat("tomato", roughness=0.4), ctx.mat("carrot", roughness=0.6)])
    return plate
