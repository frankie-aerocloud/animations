"""Environments for "The Month America Ditched McDonald's", a 30-day economic experiment: the
strip where the giant chain and its rivals face each other across a six-lane road, the inside of
the restaurants and the franchise office, independent diners and cafés on Main Street, home
kitchens and backyards, the supply chain from warehouse to farm, a TV studio and the town from the
air. The chains are generic (colour schemes and plain words), never real logos.

Coordinates are metres. The strip road runs along X at y = 0; the giant's restaurant faces it from
y = +34 and the rivals from y = -34. Timed flags are seconds from the start of the shot."""

from __future__ import annotations

import math

import bpy
from mathutils import Vector

from studio.assets import buildings, characters, fastfood, props, vegetation, vehicles
from studio.assets.meshes import merged_boxes
from studio.blender.primitives import box, cylinder, fcurves, key

ROLES = ("civilian", "shopper", "civilian", "child")
STAFF = ("civilian",)  # in the chain's colours via `dress`
# where each restaurant stands on the strip: (x, y, facing radians)
PADS = {"giant": (0.0, 34.0, 0.0), "taco": (-62.0, 34.0, 0.0), "flame": (34.0, -34.0, math.pi), "square": (-34.0, -34.0, math.pi)}


# ----- shared pieces -------------------------------------------------------------------------------
def _light(ctx, name, kind, loc, energy, colour=(1.0, 0.92, 0.8), size=0.5, target=None, angle=60.0):
    data = bpy.data.lights.new(name, kind)
    data.energy = energy
    data.color = colour
    if kind == "AREA":
        data.size = size
    else:
        data.shadow_soft_size = size
    if kind == "SPOT":
        data.spot_size = math.radians(angle)
        data.spot_blend = 0.4
    light = bpy.data.objects.new(name, data)
    light.location = loc
    if target is not None:
        light.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    ctx.link(light)
    return light


def _people(ctx, name, spots, roles=ROLES, action="idle", start=0.0, face_at=None, hold=None, dress=None):
    """People at (x, y, facing degrees[, z]); `action` may be a list used in turn; walkers walk
    the way they face; `hold` names a prop (box, bucket, bottle) some of them carry; `dress`
    overrides clothes (a uniform: {"top": "giant_red"})."""
    rng = ctx.rng
    actors = []
    for i, spot in enumerate(spots):
        x, y, face = spot[:3]
        z = spot[3] if len(spot) > 3 else 0.0
        role = roles[i % len(roles)] if isinstance(roles, list) else rng.choice(roles)
        spec = {"id": f"{name}{i}", "role": role, "at": (x, y, z), "face": face, **(dress or {})}
        if hold and i % 2 == 0:
            spec["prop"] = hold
        actor = characters.build(ctx, spec)
        what = action if isinstance(action, str) else action[i % len(action)]
        anim = {"action": what, "start": start + rng.uniform(0.0, 0.6)}
        if what in ("walk", "run", "gather"):
            heading = math.radians(face + 90.0)
            dist = rng.uniform(5.0, 9.0) if what != "gather" else rng.uniform(2.0, 4.0)
            anim["path"] = [[x, y], [x + math.cos(heading) * dist, y + math.sin(heading) * dist]]
        elif face_at:
            anim["face_at"] = face_at
        characters.animate(ctx, actor, anim)
        actors.append(actor)
    return actors


def _room(ctx, name, size, wall, floor, ceiling="ceiling_ff", z=0.0):
    w, d, h = size
    boxes = [((0, 0, -0.05), (w + 0.4, d + 0.4, 0.1), 1), ((0, 0, h + 0.05), (w + 0.4, d + 0.4, 0.1), 2), ((-w / 2 - 0.1, 0, h / 2), (0.2, d + 0.4, h), 0), ((w / 2 + 0.1, 0, h / 2), (0.2, d + 0.4, h), 0), ((0, -d / 2 - 0.1, h / 2), (w + 0.4, 0.2, h), 0), ((0, d / 2 + 0.1, h / 2), (w + 0.4, 0.2, h), 0)]
    return merged_boxes(ctx, name, boxes, [ctx.mat(wall, roughness=0.8), ctx.mat(floor, roughness=0.5), ctx.mat(ceiling, roughness=0.9)], (0.0, 0.0, z))


def _ceiling_lights(ctx, w, d, h, energy=160.0, step=4.0, colour=(1.0, 0.94, 0.84)):
    for i, x in enumerate(range(int(-w / 2 + step / 2), int(w / 2), int(step))):
        for j, y in enumerate(range(int(-d / 2 + step / 2), int(d / 2), int(step))):
            _light(ctx, f"ceiling{i}_{j}", "AREA", (x, y, h - 0.1), energy, colour, size=2.0)


def _count(spec, name, brand, default=0):
    """Per-chain numbers in the storyboard: queue: {giant: 1, flame: 7} (or one number for all)."""
    value = spec.get(name, default)
    return int(value.get(brand, default) if isinstance(value, dict) else value)


# ----- the strip -----------------------------------------------------------------------------------
def burger_strip(ctx, spec):
    """A suburban American strip: a six-lane road along X with a centre turn lane, the giant's
    restaurant on the north side between a taco place and a car park, rival burger chains facing it
    from the south. Flags per chain (a number, or {chain: number}): queue (cars in the drive-
    through), parked, walkers (people heading in). Also traffic, night, lit (signs and windows on),
    giant_dim (the giant's sign and windows dimmed), lights_on_at (they flicker back on), promo (banner words on the giant), billboards
    ([words, ...]), celebrate (balloons and waving staff at the rivals), staff_outside (the giant's
    crew waiting at the door), passers (people walking by on the sidewalks)."""
    rng = ctx.rng
    night = bool(spec.get("night"))
    lit = night or bool(spec.get("lit"))
    box(ctx, "ground", (2400.0, 2400.0, 0.2), (0.0, 0.0, -0.2), ctx.mat("verge_grass", roughness=0.95), anchor="base")
    lanes = merged_boxes(ctx, "road", [((0, 0, 0.01), (1200.0, 26.0, 0.02), 0)] + [((0, y, 0.025), (1200.0, 0.15, 0.01), 1) for y in (-6.5, -3.2, 3.2, 6.5)] + [((0, sy * 1.6, 0.025), (1200.0, 0.15, 0.01), 2) for sy in (-1, 1)], [ctx.mat("asphalt_ff", roughness=0.9), ctx.mat("lane_white", roughness=0.6), ctx.mat("lane_yellow", roughness=0.6)])
    lanes.visible_shadow = False
    for sy in (-1, 1):
        box(ctx, f"sidewalk{sy}", (1200.0, 3.0, 0.15), (0.0, sy * 14.5, 0.0), ctx.mat("sidewalk", roughness=0.85), anchor="base")
        box(ctx, f"lots{sy}", (1200.0, 44.0, 0.05), (0.0, sy * 38.0, 0.0), ctx.mat("lot_asphalt", roughness=0.9), anchor="base")
        for x in range(-300, 301, 40):
            props.lamp_post(ctx, f"lamp{sy}{x}", (float(x), sy * 13.6, 0.0), 9.0, 0.0 if sy > 0 else math.pi, lit)
    promo = spec.get("promo")
    for brand, (x, y, rot) in PADS.items():
        dim = brand == "giant" and (spec.get("giant_dim") or spec.get("lights_on_at") is not None)
        fastfood.restaurant(ctx, brand, (x, y, 0.05), rot, brand, lit=lit and not dim, promo=promo if brand == "giant" else None)
        _bays(ctx, brand, (x, y), rot, _count(spec, "parked", brand, 3 if brand != "giant" else 1), night)
        fastfood.queue(ctx, f"{brand}_queue", (x, y), rot, _count(spec, "queue", brand), lit=night)
        walkers = _count(spec, "walkers", brand)
        if walkers:
            door = (x - math.sin(rot) * 0.0, y + (-8.5 if rot == 0.0 else 8.5))
            spots = [(door[0] + rng.uniform(-6, 6), door[1] + (-rng.uniform(4, 12) if rot == 0.0 else rng.uniform(4, 12)), 0.0 if rot == 0.0 else 180.0) for _ in range(walkers)]
            _people(ctx, f"{brand}_walker", spots, ROLES, "walk", 0.0)
        if spec.get("celebrate") and brand != "giant":
            fastfood.balloons(ctx, f"{brand}_balloons", (x - 8.0, y + 8.5 if rot else y - 8.5, 0.0))
            fastfood.balloons(ctx, f"{brand}_balloons2", (x + 8.0, y + 8.5 if rot else y - 8.5, 0.0))
            _people(ctx, f"{brand}_crew", [(x + dx, y + (8.0 if rot else -8.0), 0.0 if rot else 180.0) for dx in (-2.0, 0.0, 2.0)], STAFF, "react", 0.3, dress={"top": fastfood.BRANDS[brand][1]})
    if spec.get("lights_on_at") is not None:
        _relight(ctx, float(spec["lights_on_at"]))
    passers = int(spec.get("passers", 0))
    if passers:
        spots = [(rng.uniform(-60, 60), sy * rng.uniform(14.0, 15.0), 90.0 if sy > 0 else -90.0) for sy in (rng.choice((-1, 1)) for _ in range(passers))]
        _people(ctx, "passer", spots, ROLES, "walk", 0.0)
    if spec.get("staff_outside"):
        _people(ctx, "giant_crew", [(-1.5, 25.0, 180.0), (1.2, 25.3, 200.0)], STAFF, ["idle", "look_around"], 0.0, dress={"top": "giant_red"})
    for k, words in enumerate(spec.get("billboards") or []):
        fastfood.billboard(ctx, f"billboard{k}", (-120.0 + k * 90.0, 22.0, 0.0), str(words), 0.0)
    for i in range(int(spec.get("traffic", 0))):
        lane = rng.choice((-8.0, -4.8, 4.8, 8.0))
        car = vehicles.car(ctx, f"traffic{i}", (rng.uniform(-260, 260), lane, 0.05), -math.pi / 2 if lane < 0 else math.pi / 2, rng.choice(fastfood.CAR_COLOURS), lit=night)
        key(car, "location", 1)
        car.location.x += (1 if lane < 0 else -1) * 14.0 * (ctx.frames / ctx.fps + 1.0)
        key(car, "location", ctx.frames + 30)
        for curve in fcurves(car, "location"):
            for point in curve.keyframe_points:
                point.interpolation = "LINEAR"
    for i in range(40):
        side = rng.choice((-1, 1))
        vegetation.tree(ctx, f"tree{i}", (rng.uniform(-300, 300), side * rng.uniform(64.0, 90.0), 0.0), "round", rng.uniform(0.9, 1.4))
    for i in range(14):
        buildings.house(ctx, f"house{i}", (-280.0 + i * 42.0, 120.0, 0.0), seed=i, rot=math.pi)
        buildings.house(ctx, f"house_s{i}", (-280.0 + i * 42.0, -120.0, 0.0), seed=40 + i)
    ctx.anchor("giant", (0.0, 34.0, 2.0))
    return None


def _bays(ctx, name, centre, rot, cars, night):
    """Painted parking bays in front of a restaurant, `cars` of them occupied."""
    rng = ctx.rng
    x0, y0 = centre
    out = -1.0 if rot == 0.0 else 1.0
    lines = [((x0 - 15.0 + k * 3.0, y0 + out * 12.5, 0.06), (0.12, 5.0, 0.01), 0) for k in range(11)]
    merged_boxes(ctx, f"{name}_bays", lines, [ctx.mat("lane_white", roughness=0.6)])
    for k in rng.sample(range(10), min(10, cars)):
        vehicles.car(ctx, f"{name}_parked{k}", (x0 - 13.5 + k * 3.0, y0 + out * 12.5, 0.05), 0.0, rng.choice(fastfood.CAR_COLOURS), lit=night)


def _relight(ctx, at):
    """Midnight: the giant's sign and windows flicker and come back on."""
    face = ctx.palette.emissive("relit sign", "giant_yellow", 0.0)
    glass = ctx.palette.emissive("relit windows", "window_warm", 0.0)
    merged_boxes(ctx, "relit_sign", [((12.0, 21.15, 11.2), (3.8, 0.02, 2.2), 0)], [face])
    merged_boxes(ctx, "relit_windows", [((x, 34.0 - 6.55, 1.7), (2.6, 0.08, 2.6), 0) for x in (-6.0, -3.0, 3.0, 6.0)], [glass])
    for material, level in ((face, 2.5), (glass, 3.0)):
        socket = material.node_tree.nodes["Emission"].inputs["Strength"]
        for t, v in ((0.0, 0.0), (at, 0.0), (at + 0.15, level), (at + 0.3, 0.2), (at + 0.45, level), (at + 0.6, 0.6), (at + 0.8, level)):
            socket.default_value = v
            socket.keyframe_insert("default_value", frame=ctx.frame(t))
        for curve in fcurves(material.node_tree):
            for point in curve.keyframe_points:
                point.interpolation = "CONSTANT"


# ----- inside --------------------------------------------------------------------------------------
def burger_interior(ctx, spec):
    """Inside a restaurant. kind: giant (the chain's dining room and counter), rival (a busy rival
    in its own colours), office (the franchise owner's back office), kitchen (fryers, grill and
    the walk-in of unused produce), dock (the delivery door), diner (an independent diner) or cafe
    (a family café). Flags: customers (count), staff, staff_action, wiping, table_trays, counter_trays and
    counter_nuggets (food waiting on the counter), running (kitchen), boxes (dock), crossed and
    struck (office calendar and rota), chart, owner_action."""
    kind = str(spec.get("kind", "giant"))
    return {"giant": _dining, "rival": _dining, "office": _office, "kitchen": _kitchen, "dock": _dock, "diner": _diner, "cafe": _cafe}[kind](ctx, spec)


def _dining(ctx, spec):
    rng = ctx.rng
    rival = spec.get("kind") == "rival"
    brand = "flame" if rival else "giant"
    walls, band, roof, accent, words = fastfood.BRANDS[brand]
    _room(ctx, "dining", (16.0, 12.0, 3.4), walls, "floor_ff_dark" if rival else "floor_ff")
    _ceiling_lights(ctx, 16.0, 12.0, 3.4, 150.0)
    counter = [((0, 3.6, 0.55), (8.0, 0.9, 1.1), 0), ((0, 3.6, 1.12), (8.2, 1.0, 0.05), 1), ((0, 5.9, 2.4), (9.0, 0.08, 1.2), 2)]
    counter += [((-3.0 + k * 3.0, 5.85, 2.4), (2.6, 0.04, 1.0), 3) for k in range(3)]
    for k in range(3):
        counter += [((cx - 3.0 + k * 3.0, y, cz), size, index + 4) for (cx, y, cz), size, index in fastfood.menu_items(5.82, 2.4, 0.9, 2.4)]
    merged_boxes(ctx, "counter", counter, [ctx.mat(band, roughness=0.5), ctx.mat("steel_ff", roughness=0.3, metallic=0.7), ctx.mat("steel_dark_ff", roughness=0.4), ctx.palette.emissive("menu boards", "menu_light", 1.6), ctx.mat("steel_dark_ff", roughness=0.4), ctx.mat("steel_dark_ff", roughness=0.4), ctx.mat("ink_black_ff", roughness=0.6), ctx.mat(band, roughness=0.5), ctx.mat("bun", roughness=0.6), ctx.mat("fries", roughness=0.6)])
    fastfood.sign(ctx, "wall_words", words, (0.0, 5.8, 3.05), size=0.32, colour=accent)
    for k in range(2):
        merged_boxes(ctx, f"kiosk{k}", [((0, 0, 0.9), (0.6, 0.3, 1.8), 0), ((0, -0.16, 1.3), (0.5, 0.02, 0.8), 1)], [ctx.mat("steel_dark_ff", roughness=0.4), ctx.palette.emissive(f"kiosk {k}", "screen_glow", 1.3)], (-6.5 + k * 1.2, 2.0, 0.0))
    tables = []
    seats = []
    for i in range(3):
        for j in range(3):
            x, y = -5.0 + i * 5.0, -4.0 + j * 2.6
            tables += [((x, y, 0.74), (1.2, 0.8, 0.04), 0), ((x, y, 0.37), (0.1, 0.1, 0.74), 1)]
            tables += [((x, y + sy * 0.75, 0.45), (1.3, 0.45, 0.06), 2) for sy in (-1, 1)]
            seats += [(x + rng.uniform(-0.3, 0.3), y + sy * 0.75, 0.0 if sy < 0 else 180.0) for sy in (-1, 1)]
    merged_boxes(ctx, "tables", tables, [ctx.mat("table_top", roughness=0.4), ctx.mat("steel_dark_ff", roughness=0.4), ctx.mat(accent if not rival else band, roughness=0.5)])
    for k in range(int(spec.get("counter_trays", 0))):
        fastfood.tray(ctx, f"waiting_tray{k}", (-2.4 + k * 0.6, 3.45, 1.15), 0.0, "tray_red" if not rival else "tray_blue")
    for k in range(int(spec.get("counter_nuggets", 0))):
        fastfood.nuggets(ctx, f"waiting_nuggets{k}", (-2.2 + k * 0.45, 3.75, 1.15))
    if spec.get("table_trays"):
        for i in range(3):
            for j in range(3):
                x, y = -5.0 + i * 5.0, -4.0 + j * 2.6
                fastfood.tray(ctx, f"table_tray{i}{j}a", (x - 0.25, y - 0.15, 0.76), 0.0, "tray_red" if not rival else "tray_blue")
                fastfood.tray(ctx, f"table_tray{i}{j}b", (x + 0.25, y + 0.15, 0.76), math.pi, "tray_red" if not rival else "tray_blue")
    customers = int(spec.get("customers", 0))
    if customers:
        rng.shuffle(seats)
        _people(ctx, "diner", seats[:customers], ROLES, ["idle", "look_around", "idle", "react"], 0.0)
        for k, (x, y, face) in enumerate(seats[: min(customers, 9)]):
            fastfood.tray(ctx, f"tray{k}", (x, y + (0.38 if face == 0.0 else -0.38), 0.76), 0.0, "tray_red" if not rival else "tray_blue")
        queue = [(1.0 + k * 0.9 - 2.0, 1.6 - (k % 2) * 0.5, 0.0) for k in range(min(6, customers // 2))]
        _people(ctx, "queue", queue, ROLES, "queue", 0.0)
    staff = int(spec.get("staff", 3))
    uniform = {"top": band}
    _people(ctx, "crew", [(-2.5 + k * 2.4, 4.6, 180.0) for k in range(staff)], STAFF, spec.get("staff_action", ["idle", "look_around", "idle"]), 0.0, dress=uniform)
    if spec.get("wiping"):
        _people(ctx, "wiper", [(4.6, -1.0, 90.0)], STAFF, "crouch", 0.2, dress=uniform)
    ctx.anchor("counter", (0.0, 3.6, 1.2))
    return None


def _office(ctx, spec):
    _room(ctx, "office", (5.0, 4.0, 2.7), "office_wall_ff", "carpet_ff")
    _light(ctx, "lamp", "POINT", (0.3, 0.4, 2.3), 60.0, (1.0, 0.85, 0.65), 0.3)
    _light(ctx, "screen_glow", "POINT", (0.4, 1.1, 1.0), 6.0, (0.6, 0.75, 1.0), 0.2)
    fastfood.paperwork(ctx, "desk", (0.0, 1.0, 0.0))
    fastfood.calendar(ctx, "calendar", (-1.2, 1.98, 1.7), int(spec.get("crossed", 0)))
    fastfood.rota(ctx, "rota", (1.2, 1.98, 1.65), int(spec.get("struck", 6)))
    merged_boxes(ctx, "chair", [((0, 0, 0.45), (0.5, 0.5, 0.08), 0), ((0, 0.22, 0.8), (0.5, 0.06, 0.7), 0)], [ctx.mat("steel_dark_ff", roughness=0.5)], (0.0, 0.2, 0.0))
    if spec.get("chart"):
        merged_boxes(ctx, "chart", [((0, 0, 0), (1.2, 0.03, 0.8), 0)] + [((-0.45 + k * 0.15, -0.02, -0.3 + h / 2), (0.1, 0.01, h), 1) for k, h in enumerate((0.55, 0.52, 0.45, 0.32, 0.22, 0.15, 0.1))], [ctx.mat("paper_white", roughness=0.8), ctx.mat("ink_red", roughness=0.6)], (2.45, 0.6, 1.6), (0.0, 0.0, -math.pi / 2))
    _people(ctx, "owner", [(0.0, 0.25, 0.0)], ["civilian"], spec.get("owner_action", "look_around"), 0.0)
    return None


def _kitchen(ctx, spec):
    _room(ctx, "kitchen", (10.0, 7.0, 3.0), "kitchen_tile_ff", "floor_ff_dark")
    _ceiling_lights(ctx, 10.0, 7.0, 3.0, 180.0, colour=(0.95, 1.0, 1.0))
    running = bool(spec.get("running"))
    fastfood.fryer_station(ctx, "fryers", (-3.0, 2.8, 0.0), 0.0, running)
    fastfood.grill_line(ctx, "grill", (0.8, 2.8, 0.0), 0.0, 12 if running else 0)
    merged_boxes(ctx, "walk_in", [((3.9, 2.0, 1.25), (2.0, 0.08, 2.5), 0), ((3.9, 1.95, 1.25), (0.9, 0.04, 2.0), 1)], [ctx.mat("steel_ff", roughness=0.3, metallic=0.7), ctx.mat("steel_dark_ff", roughness=0.4)])
    fastfood.produce_crates(ctx, "crates", (2.2, -2.8, 0.0), rows=2, cols=4, layers=3)
    merged_boxes(ctx, "bins", [((-4.2, -2.6, 0.45), (0.6, 0.6, 0.9), 0), ((-3.4, -2.6, 0.45), (0.6, 0.6, 0.9), 0), ((-4.2, -2.6, 0.95), (0.3, 0.3, 0.12), 1)], [ctx.mat("bin_grey_ff", roughness=0.6), ctx.mat("lettuce", roughness=0.7)])
    _people(ctx, "cook", [(1.0, 1.8, 0.0), (2.6, -1.2, 160.0)], STAFF, spec.get("staff_action", ["idle", "look_around"]), 0.0, dress={"top": "giant_red"})
    return None


def _dock(ctx, spec):
    box(ctx, "yard", (80.0, 80.0, 0.1), (0.0, 0.0, -0.1), ctx.mat("lot_asphalt", roughness=0.9), anchor="base")
    box(ctx, "rear_wall", (18.0, 0.4, 4.6), (0.0, 6.5, 0.0), ctx.mat(fastfood.BRANDS["giant"][0], roughness=0.7), anchor="base")
    box(ctx, "rear_door", (2.2, 0.1, 2.6), (2.0, 6.25, 0.0), ctx.mat("steel_ff", roughness=0.3, metallic=0.6), anchor="base")
    vehicles.lorry(ctx, "delivery", (-1.5, -2.0, 0.05), 0.0, "truck_white", "container")
    count = int(spec.get("boxes", 3))
    for k in range(count):
        box(ctx, f"delivery{k}", (0.6, 0.45, 0.4), (1.2 + (k % 3) * 0.65, 4.5, 0.2 + (k // 3) * 0.4), ctx.mat("carton_ff", roughness=0.8))
    _people(ctx, "driver", [(0.8, 3.2, 20.0)], ["worker"], "carry", 0.0, hold="box")
    _people(ctx, "manager", [(3.2, 4.8, 200.0)], STAFF, "look_around", 0.0, dress={"top": "giant_red"})
    return None


def _diner(ctx, spec):
    rng = ctx.rng
    _room(ctx, "diner", (14.0, 8.0, 3.2), "diner_wall", "diner_floor")
    _ceiling_lights(ctx, 14.0, 8.0, 3.2, 150.0, colour=(1.0, 0.9, 0.75))
    counter = [((0, 1.5, 0.55), (10.0, 0.7, 1.1), 0), ((0, 1.5, 1.12), (10.2, 0.8, 0.05), 1), ((0, 3.9, 1.6), (12.0, 0.1, 0.8), 2)]
    counter += [((-4.5 + k * 1.0, 0.7, 0.4), (0.38, 0.38, 0.08), 3) for k in range(10)] + [((-4.5 + k * 1.0, 0.7, 0.2), (0.08, 0.08, 0.4), 4) for k in range(10)]
    booths = []
    for k in range(5):
        x = -5.6 + k * 2.8
        booths += [((x, -2.6, 0.75), (1.4, 1.0, 0.05), 5), ((x - 0.95, -2.6, 0.5), (0.45, 1.1, 1.0), 6), ((x + 0.95, -2.6, 0.5), (0.45, 1.1, 1.0), 6)]
    merged_boxes(ctx, "fit_out", counter + booths, [ctx.mat("diner_teal", roughness=0.4), ctx.mat("chrome", roughness=0.2, metallic=0.9), ctx.mat("diner_menu", roughness=0.6), ctx.mat("diner_red", roughness=0.4), ctx.mat("chrome", roughness=0.2, metallic=0.9), ctx.mat("table_top", roughness=0.4), ctx.mat("diner_red", roughness=0.4)])
    fastfood.sign(ctx, "neon", "EAT", (4.5, 3.8, 2.6), size=0.5, colour="neon_pink", emission=4.0)
    fastfood.sign(ctx, "neon2", "OPEN", (-4.5, 3.8, 2.6), size=0.4, colour="neon_blue", emission=4.0)
    customers = int(spec.get("customers", 12))
    seats = [(-4.5 + k * 1.0, 0.45, 0.0) for k in range(10)] + [(-5.6 + k * 2.8 + sx * 0.75, -2.6, 90.0 if sx < 0 else -90.0) for k in range(5) for sx in (-1, 1)]
    rng.shuffle(seats)
    _people(ctx, "regular", seats[:customers], ROLES, ["idle", "look_around", "react", "idle"], 0.0)
    for k in range(min(5, customers // 2)):
        x = -5.6 + k * 2.8
        fastfood.burger(ctx, f"plate{k}", (x, -2.6, 0.78), 1.4)
    _people(ctx, "cook", [(-1.0, 2.6, 180.0), (2.2, 2.6, 180.0)], STAFF, ["point", "idle"], 0.0, dress={"top": "cup_white"})
    return None


def _cafe(ctx, spec):
    rng = ctx.rng
    _room(ctx, "cafe", (10.0, 7.0, 3.0), "cafe_wall_ff", "floor_wood_ff")
    _ceiling_lights(ctx, 10.0, 7.0, 3.0, 140.0, colour=(1.0, 0.86, 0.68))
    box(ctx, "counter", (4.0, 0.7, 1.05), (2.5, 2.6, 0.0), ctx.mat("counter_wood_ff", roughness=0.6), anchor="base")
    merged_boxes(ctx, "chalkboard", [((0, 0, 0), (2.4, 0.04, 1.2), 0)] + [((-0.8 + rng.uniform(0, 1.2), -0.03, rng.uniform(-0.4, 0.4)), (rng.uniform(0.3, 0.9), 0.01, 0.04), 1) for _ in range(10)], [ctx.mat("chalkboard", roughness=0.9), ctx.mat("chalk_white", roughness=0.9)], (2.5, 3.45, 2.0))
    fastfood.sign(ctx, "cafe_sign", "FAMILY CAFÉ", (-2.0, 3.45, 2.3), size=0.35, colour="cafe_sign")
    tables = []
    spots = []
    for k in range(6):
        x, y = -3.5 + (k % 3) * 2.6, -2.2 + (k // 3) * 2.2
        tables += [((x, y, 0.74), (0.8, 0.8, 0.04), 0), ((x, y, 0.37), (0.08, 0.08, 0.74), 1)]
        spots += [(x - 0.65, y, -90.0), (x + 0.65, y, 90.0)]
    merged_boxes(ctx, "tables", tables, [ctx.mat("counter_wood_ff", roughness=0.6), ctx.mat("steel_dark_ff", roughness=0.4)])
    rng.shuffle(spots)
    _people(ctx, "guest", spots[: int(spec.get("customers", 8))], ROLES, ["idle", "react", "look_around", "idle"], 0.0)
    _people(ctx, "owner", [(2.5, 3.0, 180.0)], ["civilian"], "point", 0.0)
    for k in range(4):
        vegetation.bush(ctx, f"plant{k}", (-4.6 + k * 0.4, 3.2, 0.0), 0.3)
    return None


# ----- home ----------------------------------------------------------------------------------------
def food_home(ctx, spec):
    """At home. kind: kitchen (a family cooking at the hob), dinner (a family at the table with
    homemade burgers), backyard (a grill in the garden) or fridge (one tired person at an open
    fridge late in the evening). Flags: people, night."""
    rng = ctx.rng
    kind = str(spec.get("kind", "kitchen"))
    if kind == "backyard":
        box(ctx, "lawn", (60.0, 60.0, 0.1), (0.0, 0.0, -0.1), ctx.mat("lawn_ff", roughness=0.95), anchor="base")
        buildings.house(ctx, "house", (0.0, 9.0, 0.0), seed=7, rot=math.pi, size=(12.0, 8.0, 6.4))
        box(ctx, "patio", (8.0, 4.0, 0.08), (0.0, 3.0, 0.0), ctx.mat("sidewalk", roughness=0.85), anchor="base")
        props.fence(ctx, "fence_l", (-12.0, -10.0), (-12.0, 6.0), 0.0, 1.8, 2.0)
        props.fence(ctx, "fence_b", (-12.0, -10.0), (12.0, -10.0), 0.0, 1.8, 2.0)
        props.fence(ctx, "fence_r", (12.0, -10.0), (12.0, 6.0), 0.0, 1.8, 2.0)
        fastfood.bbq(ctx, "grill", (-1.0, 1.5, 0.0), 6)
        merged_boxes(ctx, "picnic", [((0, 0, 0.75), (2.0, 0.9, 0.06), 0)] + [((0, sy * 0.75, 0.45), (2.0, 0.3, 0.05), 0) for sy in (-1, 1)] + [((sx * 0.8, 0, 0.37), (0.08, 1.6, 0.74), 1) for sx in (-1, 1)], [ctx.mat("table_wood", roughness=0.7), ctx.mat("table_wood", roughness=0.7)], (2.5, -1.5, 0.0))
        for k in range(3):
            fastfood.burger(ctx, f"plate{k}", (1.9 + k * 0.6, -1.5, 0.79), 1.3)
        for i in range(8):
            vegetation.tree(ctx, f"tree{i}", (rng.uniform(-30, 30), rng.uniform(-30, -14), 0.0), "round", rng.uniform(0.9, 1.3))
        _people(ctx, "family", [(-1.0, 0.8, 0.0), (1.8, -2.4, 0.0), (3.1, -2.3, 0.0), (2.4, -0.6, 180.0)], ["civilian", "child", "civilian", "child"], ["idle", "react", "look_around", "idle"], 0.0, face_at=(1.0, 0.0))
        return None
    _room(ctx, "kitchen", (6.0, 5.0, 2.7), "home_wall", "home_floor")
    lamp = 30.0 if spec.get("night") else 70.0
    _light(ctx, "pendant", "POINT", (0.0, 0.0, 2.3), lamp, (1.0, 0.82, 0.6), 0.4)
    _light(ctx, "window_light", "AREA", (2.9, 0.0, 1.6), 0.0 if spec.get("night") else 120.0, (1.0, 0.95, 0.9), 1.2, target=(0.0, 0.0, 1.0))
    units = [((x, 2.2, 0.45), (0.6, 0.6, 0.9), 0) for x in (-2.4, -1.8, -1.2, -0.6, 0.0, 0.6, 1.2, 1.8, 2.4)] + [((0.0, 2.2, 0.92), (5.6, 0.62, 0.04), 1), ((0.0, 2.38, 1.9), (5.6, 0.35, 0.8), 0)]
    units += [((-1.2, 2.1, 0.96), (0.6, 0.5, 0.02), 2)] + [((-1.35 + (k % 2) * 0.3, 1.95 + (k // 2) * 0.3, 0.98), (0.2, 0.2, 0.02), 3) for k in range(4)]
    merged_boxes(ctx, "units", units, [ctx.mat("home_unit", roughness=0.5), ctx.mat("worktop_ff", roughness=0.4), ctx.mat("steel_dark_ff", roughness=0.4), ctx.mat("hob_ring", roughness=0.5)])
    box(ctx, "window", (0.05, 1.4, 1.0), (2.98, 0.0, 1.5), ctx.palette.emissive("window view", "window_night_ff" if spec.get("night") else "window_day_ff", 0.5 if spec.get("night") else 1.4))
    if kind == "fridge":
        merged_boxes(ctx, "fridge", [((0, 0, 0.95), (0.8, 0.7, 1.9), 0), ((0, -0.36, 1.2), (0.78, 0.04, 1.3), 1)], [ctx.mat("cup_white", roughness=0.4), ctx.palette.emissive("fridge light", "fridge_glow", 2.0)], (-2.2, 0.8, 0.0))
        _people(ctx, "tired", [(-2.2, -0.2, 0.0)], ["civilian"], "look_around", 0.0)
        return None
    if kind == "dinner":
        merged_boxes(ctx, "table", [((0, 0, 0.75), (1.8, 1.0, 0.05), 0), ((0, 0, 0.37), (0.1, 0.1, 0.74), 1)], [ctx.mat("table_wood", roughness=0.6), ctx.mat("steel_dark_ff", roughness=0.4)], (0.0, -0.6, 0.0))
        for k, (x, y) in enumerate(((-0.55, -0.85), (0.55, -0.85), (-0.55, -0.35), (0.55, -0.35))):
            fastfood.burger(ctx, f"homemade{k}", (x, y, 0.78), 1.3)
        _people(ctx, "family", [(-0.55, -1.5, 0.0), (0.55, -1.5, 0.0), (-0.55, 0.3, 180.0), (0.55, 0.3, 180.0)], ["civilian", "child", "civilian", "child"], ["idle", "react", "look_around", "idle"], 0.0)
        return None
    cylinder(ctx, "pan", 0.16, 0.06, (-1.2, 2.05, 1.0), ctx.mat("steel_dark_ff", roughness=0.4), segments=16, anchor="base")
    fastfood.burger(ctx, "patty_pan", (-1.2, 2.05, 1.06), 1.0)
    fastfood.produce_crates(ctx, "veg", (0.8, 2.0, 0.94), rows=1, cols=2, layers=1)
    _people(ctx, "cook", [(-1.2, 1.4, 0.0), (0.4, 1.3, 20.0), (1.4, 0.4, 120.0)], ["civilian", "child", "civilian"], ["idle", "point", "look_around"], 0.0)
    return None


# ----- the supply chain ----------------------------------------------------------------------------
def food_supply(ctx, spec):
    """The supply chain. kind: warehouse (a distribution centre of buns, potatoes and cups with idle
    forklifts), yard (lorries at the loading docks, some pulling away) or farm (a field of lettuce
    being loaded onto a truck bound for a local market). Flags: idle, leaving (lorries driving off),
    people."""
    rng = ctx.rng
    kind = str(spec.get("kind", "warehouse"))
    if kind == "warehouse":
        _room(ctx, "shed", (50.0, 30.0, 11.0), "shed_wall", "shed_floor", "shed_roof")
        _ceiling_lights(ctx, 50.0, 30.0, 11.0, 500.0, 10.0)
        racks = []
        for y in (-10.0, -4.0, 4.0, 10.0):
            for x in range(-22, 20, 3):
                racks.append(((x - 1.45, y, 4.5), (0.12, 1.3, 9.0), 0))
                for level in range(3):
                    racks.append(((x, y, 0.1 + level * 3.0), (2.9, 1.3, 0.12), 1))
        merged_boxes(ctx, "racking", racks, [ctx.mat("rack_blue_ff", roughness=0.5), ctx.mat("rack_orange", roughness=0.5)])
        kinds = ("buns", "potatoes", "patties", "cups")
        for k in range(56):
            row, col = k // 14, k % 14
            y = (-10.0, -4.0, 4.0, 10.0)[row]
            fastfood.pallet(ctx, f"pallet{k}", (-22.0 + col * 3.0 + rng.uniform(-0.2, 0.2), y, 0.16 + 3.0 * rng.randrange(3)), kinds[(k + row) % 4])
        for k in range(10):
            fastfood.pallet(ctx, f"floor_pallet{k}", (-18.0 + k * 3.5, 0.0, 0.0), kinds[k % 4])
        for k, (x, y) in enumerate(((-6.0, 1.8), (8.0, -1.6))):
            merged_boxes(ctx, f"forklift{k}", [((0, 0, 0.7), (1.2, 2.2, 1.1), 0), ((0, -0.3, 1.6), (1.1, 1.0, 0.9), 1), ((0, 1.35, 1.6), (1.0, 0.1, 3.0), 2), ((0, 1.6, 0.2), (1.0, 1.0, 0.06), 2)], [ctx.mat("forklift_yellow", roughness=0.5), ctx.mat("steel_dark_ff", roughness=0.4), ctx.mat("steel_ff", roughness=0.3, metallic=0.7)], (x, y, 0.0), (0.0, 0.0, rng.uniform(-0.3, 0.3)))
        _people(ctx, "picker", [(-2.0, 0.8, 0.0), (3.0, -0.6, 160.0)], ["worker"], ["look_around", "idle"], 0.0)
        return None
    box(ctx, "ground", (2000.0, 2000.0, 0.2), (0.0, 0.0, -0.2), ctx.mat("field_dirt" if kind == "farm" else "lot_asphalt", roughness=0.95), anchor="base")
    if kind == "yard":
        box(ctx, "shed", (90.0, 30.0, 11.0), (0.0, 30.0, 0.0), ctx.mat("shed_wall", roughness=0.7), anchor="base")
        doors = [((x, 14.9, 2.2), (3.4, 0.1, 3.6), 0) for x in range(-40, 41, 8)]
        merged_boxes(ctx, "dock_doors", doors, [ctx.mat("dock_door", roughness=0.5)])
        fastfood.sign(ctx, "shed_sign", "FOOD DISTRIBUTION", (0.0, 14.8, 8.0), size=1.6, colour="sign_white_ff")
        leaving = int(spec.get("leaving", 0))
        for k, x in enumerate(range(-40, 41, 8)):
            if rng.random() < 0.6:
                truck = vehicles.lorry(ctx, f"lorry{k}", (float(x), 6.0, 0.05), math.pi, rng.choice(("truck_white", "truck_red", "truck_blue")), "container")
                if k < leaving:
                    key(truck, "location", 1)
                    truck.location.y -= 30.0
                    key(truck, "location", ctx.frames)
        return None
    rows = [((x, 0.0, 0.15), (0.6, 160.0, 0.3), 0) for x in range(-60, 61, 2)]
    heads = [((x, y, 0.4), (0.4, 0.4, 0.3), 1) for x in range(-60, 61, 2) for y in range(-78, 79, 3)]
    merged_boxes(ctx, "field", rows + heads, [ctx.mat("field_dirt", roughness=0.95), ctx.mat("lettuce", roughness=0.7)])
    vehicles.lorry(ctx, "farm_truck", (4.0, -88.0, 0.05), math.pi / 2, "truck_green", "flatbed")
    fastfood.produce_crates(ctx, "loaded", (0.5, -89.0, 1.25), rows=2, cols=4, layers=2, rot=math.pi / 2)
    fastfood.produce_crates(ctx, "waiting", (-6.0, -84.0, 0.0), rows=2, cols=3, layers=2)
    merged_boxes(ctx, "market_sign", [((0, 0, 1.2), (0.12, 0.12, 2.4), 0), ((0, 0, 2.6), (3.2, 0.12, 1.0), 1)], [ctx.mat("table_wood", roughness=0.7), ctx.mat("cup_white", roughness=0.6)], (14.0, -86.0, 0.0))
    fastfood.sign(ctx, "market_words", "TO: LOCAL MARKET", (14.0, -86.08, 2.5), size=0.3, colour="truck_green")
    _people(ctx, "farmhand", [(-5.0, -86.5, 90.0), (-3.0, -87.5, 90.0), (1.0, -86.0, 200.0)], ["farmer"], ["carry", "carry", "point"], 0.0, hold="box")
    for i in range(16):
        vegetation.tree(ctx, f"windbreak{i}", (-80.0 + i * 10.0, 90.0, 0.0), "round", 1.4)
    return None


# ----- the studio and the town ---------------------------------------------------------------------
def tv_studio(ctx, spec):
    """A TV news studio: a curved desk, a big screen with a plate split between burger and fries
    and salad, a presenter and a nutrition expert."""
    _room(ctx, "studio", (14.0, 10.0, 4.5), "studio_wall_ff", "studio_floor")
    merged_boxes(ctx, "desk", [((0, 0.5, 0.45), (4.0, 1.0, 0.9), 0), ((0, 0.5, 0.92), (4.2, 1.1, 0.05), 1)], [ctx.mat("studio_desk", roughness=0.4), ctx.mat("chrome", roughness=0.2, metallic=0.9)])
    box(ctx, "screen", (7.0, 0.1, 3.6), (0.0, 4.9, 2.4), ctx.palette.emissive("studio screen", "screen_studio", 0.9))
    fastfood.plate_graphic(ctx, "plate", (0.0, 4.8, 2.4), 2.6)
    fastfood.sign(ctx, "screen_title", str(spec.get("screen", "WHAT REPLACES THE BURGER?")), (0.0, 4.82, 3.85), size=0.32, colour="sign_white_ff", emission=2.0)
    _light(ctx, "key", "AREA", (0.0, -3.0, 3.5), 500.0, (1.0, 0.96, 0.9), 3.0, target=(0.0, 0.5, 1.4))
    _light(ctx, "rim", "SPOT", (-4.0, 3.5, 4.0), 400.0, (0.6, 0.75, 1.0), 0.2, target=(0.0, 0.5, 1.2), angle=50.0)
    _people(ctx, "presenter", [(-1.0, 1.25, 180.0), (1.1, 1.25, 200.0)], ["civilian", "doctor"], ["idle", "point"], 0.0)
    return None


def main_street(ctx, spec):
    """A small-town Main Street of independent businesses: a chrome diner, a family café, a local
    burger joint and a bakery, with people heading in. Flags: walkers, night, busy (string lights
    and outdoor tables), queue (outside the burger joint)."""
    rng = ctx.rng
    night = bool(spec.get("night"))
    box(ctx, "ground", (800.0, 800.0, 0.2), (0.0, 0.0, -0.2), ctx.mat("verge_grass", roughness=0.95), anchor="base")
    props.road(ctx, "street", (-200.0, 0.0), (200.0, 0.0), 10.0, 0.02)
    for sy in (-1, 1):
        box(ctx, f"sidewalk{sy}", (400.0, 4.0, 0.15), (0.0, sy * 7.0, 0.0), ctx.mat("sidewalk", roughness=0.85), anchor="base")
    shops = (("DINER", "diner_teal", "chrome"), ("FAMILY CAFÉ", "cafe_wall_ff", "cafe_sign"), ("JOE'S BURGERS", "local_red", "local_cream"), ("BAKERY", "bakery_blue", "cup_white"), ("BOOKS", "brick_ff", "cup_white"), ("HARDWARE", "shed_wall", "truck_green"))
    for i, (words, wall, trim) in enumerate(shops):
        x = -45.0 + i * 15.0
        buildings.building(ctx, f"shop{i}", (x, 15.0, 0.0), (14.0, 12.0, rng.choice((7.0, 8.0, 10.0))), wall, "flat", 0.0, seed=i, lit=ctx.palette.emissive(f"shop {i} windows", "window_warm", 2.0) if night else None)
        merged_boxes(ctx, f"awning{i}", [((x, 8.6, 3.3), (12.0, 1.4, 0.15), 0)], [ctx.mat(trim, roughness=0.5)])
        fastfood.sign(ctx, f"shop{i}_words", words, (x, 8.75, 4.1), size=0.6, colour=trim, emission=2.0 if night else 0.0)
    for i in range(6):
        buildings.building(ctx, f"opposite{i}", (-45.0 + i * 15.0, -15.0, 0.0), (14.0, 12.0, rng.choice((7.0, 8.0))), rng.choice(("brick_ff", "shed_wall", "cafe_wall_ff")), "flat", math.pi, seed=20 + i)
    if spec.get("busy"):
        for i in range(4):
            merged_boxes(ctx, f"terrace{i}", [((0, 0, 0.74), (0.8, 0.8, 0.04), 0), ((0, 0, 0.37), (0.06, 0.06, 0.74), 1)], [ctx.mat("table_top", roughness=0.4), ctx.mat("steel_dark_ff", roughness=0.4)], (-34.0 + i * 2.0, 7.6, 0.15))
        bulbs = [((x, 8.8, 4.4 + 0.25 * math.sin(x)), (0.12, 0.12, 0.12), 0) for x in range(-50, 46, 2)]
        merged_boxes(ctx, "string_lights", bulbs, [ctx.palette.emissive("bulbs", "bulb_warm", 4.0)])
    walkers = int(spec.get("walkers", 14))
    spots = [(rng.uniform(-50, 40), rng.choice((7.5, 6.5, -7.0)), rng.choice((90.0, -90.0))) for _ in range(walkers)]
    _people(ctx, "walker", spots, ROLES, ["walk", "walk", "idle", "walk"], 0.0)
    queue = int(spec.get("queue", 0))
    if queue:
        _people(ctx, "queue", [(-15.0 + k * 0.9, 7.7, -90.0) for k in range(queue)], ROLES, "queue", 0.0)
    for i in range(8):
        vehicles.car(ctx, f"parked{i}", (-60.0 + i * 13.0 + rng.uniform(-2, 2), 3.6, 0.05), math.pi / 2, rng.choice(fastfood.CAR_COLOURS), lit=night)
    for i in range(10):
        vegetation.tree(ctx, f"street_tree{i}", (-55.0 + i * 11.0, -6.5, 0.0), "round", 0.8)
    return None


def town_aerial(ctx, spec):
    """An American town from the air: a grid of streets and houses, the strip of chain restaurants
    along the highway (the giant's lot empty or full), Main Street, parks and trees. Flags: night,
    giant_busy, rivals_busy."""
    rng = ctx.rng
    night = bool(spec.get("night"))
    box(ctx, "land", (6000.0, 6000.0, 0.2), (0.0, 0.0, -0.2), ctx.mat("verge_grass", roughness=0.95), anchor="base")
    streets = [((0, y, 0.02), (2400.0, 9.0, 0.04), 0) for y in range(-600, 601, 100)] + [((x, 0, 0.02), (9.0, 1200.0, 0.04), 0) for x in range(-1200, 1201, 120)]
    streets.append(((0, 0, 0.03), (2400.0, 28.0, 0.05), 1))
    merged_boxes(ctx, "streets", streets, [ctx.mat("asphalt_ff", roughness=0.9), ctx.mat("asphalt_ff", roughness=0.9)])
    blocks = []
    lights = []
    for gx in range(-10, 10):
        for gy in range(-6, 6):
            cx, cy = gx * 120.0 + 60.0, gy * 100.0 + 50.0
            if abs(cy) < 60:
                continue
            for k in range(rng.randint(5, 9)):
                hx, hy = cx + rng.uniform(-45, 45), cy + rng.uniform(-35, 35)
                blocks.append(((hx, hy, 2.5), (rng.uniform(9, 13), rng.uniform(8, 11), 5.0), rng.randrange(3)))
                blocks.append(((hx, hy, 5.4), (rng.uniform(9, 13) + 0.6, 10.0, 0.8), 3))
                if night and rng.random() < 0.5:
                    lights.append(((hx + 5.0, hy, 2.0), (0.4, 2.0, 1.2), 5))
            for _ in range(rng.randint(3, 6)):
                s = rng.uniform(5, 9)
                blocks.append(((cx + rng.uniform(-50, 50), cy + rng.uniform(-40, 40), 5.0), (s, s, s * 0.8), 4))
    lit = ctx.palette.emissive("town windows", "window_warm", 3.0) if night else ctx.mat("glass_shop", roughness=0.1)
    merged_boxes(ctx, "town", blocks + lights, [ctx.mat("house_white", roughness=0.8), ctx.mat("house_cream", roughness=0.8), ctx.mat("house_blue", roughness=0.8), ctx.mat("roof_ff", roughness=0.7), ctx.mat("tree_ff", roughness=0.8), lit])
    for k, (brand, x) in enumerate((("giant", 0.0), ("flame", 90.0), ("square", -90.0), ("taco", 180.0))):
        y = 40.0 if k % 2 == 0 else -40.0
        walls, band, roof, accent, words = fastfood.BRANDS[brand]
        merged_boxes(ctx, f"{brand}_pad", [((x, y, 0.05), (60.0, 40.0, 0.1), 0), ((x, y, 2.4), (18.0, 13.0, 4.8), 1), ((x, y, 5.0), (18.6, 13.6, 0.6), 2)], [ctx.mat("lot_asphalt", roughness=0.9), ctx.mat(walls, roughness=0.7), ctx.mat(band, roughness=0.5)])
        busy = spec.get("giant_busy") if brand == "giant" else spec.get("rivals_busy", True)
        for c in range(14 if busy else 1):
            vehicles.car(ctx, f"{brand}_car{c}", (x - 24.0 + (c % 7) * 7.0, y + (-14.0 if c < 7 else 14.0) * (1 if y > 0 else -1) * 0.8, 0.05), 0.0, rng.choice(fastfood.CAR_COLOURS), lit=night)
        merged_boxes(ctx, f"{brand}_pole", [((x + 14.0, y, 9.0), (0.8, 0.8, 18.0), 0), ((x + 14.0, y, 19.5), (7.0, 1.2, 4.0), 1)], [ctx.mat("steel_dark_ff", roughness=0.5), ctx.palette.emissive(f"{brand} aerial sign", accent, 2.0 if night else 0.8)])
    return None


BUILDERS = {
    "burger_strip": burger_strip,
    "burger_interior": burger_interior,
    "food_home": food_home,
    "food_supply": food_supply,
    "tv_studio": tv_studio,
    "main_street": main_street,
    "town_aerial": town_aerial,
}
FOG_EXTENT = {"burger_strip": (1600, 1600, 200), "burger_interior": (0, 0, 0), "food_home": (200, 200, 60), "food_supply": (1200, 1200, 200), "tv_studio": (0, 0, 0), "main_street": (800, 800, 120), "town_aerial": (6000, 6000, 800)}


def build(ctx, spec):
    return BUILDERS[spec["type"]](ctx, spec)
