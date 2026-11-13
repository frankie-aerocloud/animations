"""Reusable environments composed from the asset library. Each builder registers anchors
(world points for cameras) and tags (object groups for events) on the context."""

from __future__ import annotations

import math

from studio.assets import buildings, props, terrain, vegetation, vehicles, water
from studio.assets import characters
from studio.blender import lighting
from studio.blender.primitives import box, cylinder, empty, ico, multi_box, parent
from studio.core import catalogue

FOG_EXTENT = {
    "coastal_city": (900, 900, 220),
    "reservoir": (900, 900, 260),
    "farm": (700, 700, 140),
    "industrial": (600, 600, 160),
    "port": (700, 700, 140),
    "desert": (900, 900, 220),
    "kitchen_interior": (0, 0, 0),
    "supermarket_interior": (0, 0, 0),
}


def _city_block(ctx, name, centre, size, kind, seed, dry=False, pools=True):
    rng = ctx.rng
    cx, cy = centre
    w, d = size
    props.pavement(ctx, f"{name}.pavement", (cx, cy), (w + 4, d + 4), 0.0)
    if kind == "plaza":
        box(ctx, f"{name}.paving", (w, d, 0.1), (cx, cy, 0.18), ctx.mat("plaster"), anchor="base")
        water.fountain(ctx, f"{name}.fountain", (cx, cy, 0.28), radius=4.0)
        hall = buildings.building(ctx, f"{name}.hall", (cx, cy + d / 2 - 7, 0.2), (26, 12, 9), "white", "dome", 0.0, seed, window=(1.4, 2.2), trim="stone", units=False)
        for i, (dx, dy) in enumerate(((-12, -10), (12, -10), (-12, 4), (12, 4))):
            vegetation.tree(ctx, f"{name}.tree{i}", (cx + dx, cy + dy, 0.28), "round", 0.9)
        for i, (dx, dy, rot) in enumerate(((-7, -4, 0.0), (7, -4, 0.0), (0, -13, math.pi))):
            props.bench(ctx, f"{name}.bench{i}", (cx + dx, cy + dy, 0.28), rot)
        for i, (dx, dy) in enumerate(((-15, -15), (15, -15), (-15, 12), (15, 12))):
            props.lamp_post(ctx, f"{name}.lamp{i}", (cx + dx, cy + dy, 0.28), 6.0, 0.0, dry)
        ctx.anchor("plaza", (cx, cy, 0.3))
        ctx.anchor("fountain", (cx, cy, 1.0))
        ctx.anchor("hall", (cx, cy + d / 2 - 7, 9.0))
        return hall
    if kind == "towers":
        n = rng.randint(2, 3)
        for i in range(n):
            x = cx - w / 2 + (w / n) * (i + 0.5) + rng.uniform(-2, 2)
            y = cy + rng.uniform(-d * 0.2, d * 0.2)
            buildings.tower(ctx, f"{name}.tower{i}", (x, y, 0.18), seed * 10 + i)
        return None
    if kind == "apartments":
        for i, (sx, sy) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
            if rng.random() < 0.15:
                vegetation.tree(ctx, f"{name}.tree{i}", (cx + sx * w * 0.25, cy + sy * d * 0.25, 0.18), "round")
                continue
            buildings.apartment(ctx, f"{name}.apt{i}", (cx + sx * w * 0.25, cy + sy * d * 0.25, 0.18), seed * 10 + i)
        return None
    if kind == "commercial":
        buildings.warehouse(ctx, f"{name}.store", (cx, cy, 0.18), (w * 0.8, d * 0.45, 7), 0.0, "plaster")
        box(ctx, f"{name}.carpark", (w * 0.8, d * 0.4, 0.05), (cx, cy - d * 0.27, 0.18), ctx.mat("asphalt"), anchor="base")
        for i in range(5):
            vehicles.car(ctx, f"{name}.car{i}", (cx - w * 0.3 + i * 6.0, cy - d * 0.3, 0.23), rot=0.0)
        return None
    # houses (residential / resort)
    cols, rows = 3, 2
    for i in range(cols):
        for j in range(rows):
            x = cx - w / 2 + (w / cols) * (i + 0.5)
            y = cy - d / 2 + (d / rows) * (j + 0.5)
            rot = 0.0 if j == 0 else math.pi
            buildings.house(ctx, f"{name}.house{i}{j}", (x + rng.uniform(-1, 1), y + (3.0 if j == 0 else -3.0), 0.18), seed * 10 + i * 2 + j, rot)
            garden_y = y - 4.5 if j == 0 else y + 4.5
            if pools and rng.random() < (0.55 if kind == "resort" else 0.25):
                water.pool(ctx, f"{name}.pool{i}{j}", (x, garden_y, 0.18), (5.0, 2.8))
                if "pool_1" not in ctx.anchors:
                    ctx.anchor("pool_1", (x, garden_y, 1.6))
            else:
                box(ctx, f"{name}.lawn{i}{j}", (7.0, 4.0, 0.08), (x, garden_y, 0.18), ctx.mat("grass_dry" if dry else "grass"), anchor="base")
                vegetation.tree(ctx, f"{name}.tree{i}{j}", (x + 2.5, garden_y, 0.18), "palm" if kind == "resort" else "round", 0.8, dry)
    return None


def coastal_city(ctx, spec):
    """Coastal city: plaza, towers, apartments, resort houses with pools, river, reservoir and port."""
    rng = ctx.rng
    seed = int(spec.get("seed", 1))
    dry = spec.get("variant") == "crisis"
    pal = ctx.palette
    ground_mat = pal.terrain("city ground", [(-9.0, "mud"), (-1.5, "beach"), (0.0, "sand"), (0.6, "pavement"), (5.0, "grass"), (16.0, "grass_dry"), (32.0, "rock"), (46.0, "stone")])
    terrain.ground(ctx, "ground", (900, 900), (120, 120), amplitude=5.0, seed=seed, material=ground_mat, coast={"y": -70.0, "depth": 9.0, "width": 36.0}, flat=[(-175, -66, 175, 120, 14)], rise={"axis": "y", "start": 118, "end": 260, "height": 42, "extra_noise": 10.0}, bowl={"centre": (60.0, 165.0), "radius": 45.0, "depth": 14.0}, noise_scale=0.02)
    water.surface(ctx, "sea", (1000, 300), (0.0, -214.0, -0.5), "sea", tags=("sea",))
    ctx.anchor("sea", (0.0, -120.0, -0.5))
    water.surface(ctx, "reservoir", (82, 82), (60.0, 165.0, 10.5), "lake", tags=("water", "reservoir"), bed=True)
    buildings.dam(ctx, "dam", (60.0, 121.0, 0.5), 72.0, 16.0, 7.0)
    water.river(ctx, "river", [(60, 118), (40, 105), (28, 84), (23, 60), (23, 10), (23, -40), (24, -68)], width=9.0, z=0.4)
    columns = (-138, -92, -46, 0, 46, 92, 138)
    rows = (-46, 0, 46, 92)
    for y in (-23, 23, 69, 115):
        props.road(ctx, f"road.h{y}", (-166, y), (166, y), 10.0, 0.22)
    for x in (-115, -69, -23, 69, 115, 161):
        props.road(ctx, f"road.v{x}", (x, -66), (x, 118), 10.0, 0.22)
    props.road(ctx, "road.coast", (-200, -64), (200, -64), 10.0, 0.22)
    for y in (-64, -23, 23, 69, 115):
        box(ctx, f"bridge{y}", (16.0, 11.0, 0.9), (23.0, y, 0.3), ctx.mat("stone"), bevel=0.08, anchor="base")
    for i, x in enumerate(range(-190, 191, 14)):
        if abs(x - 23) > 9:
            vegetation.palm(ctx, f"palm{i}", (x, -72.0, 0.0), rng.uniform(0.9, 1.2))
    block_index = 0
    for y in rows:
        for x in columns:
            block_index += 1
            if 14 < x < 32:
                continue
            distance = math.hypot(x, y - 20)
            if x == 0 and y == 0:
                kind = "plaza"
            elif distance < 60:
                kind = "towers"
            elif y == -46:
                kind = "resort" if rng.random() < 0.7 else "apartments"
            elif distance < 115:
                kind = "apartments" if rng.random() < 0.7 else "commercial"
            else:
                kind = "houses"
            _city_block(ctx, f"block{block_index}", (x, y), (36, 36), kind, seed * 100 + block_index, dry)
    # port
    quay = box(ctx, "quay", (70, 18, 2.2), (-150.0, -74.0, -1.0), ctx.mat("concrete"), bevel=0.1, anchor="base")
    for i, x in enumerate((-168, -140)):
        vehicles.crane(ctx, f"crane{i}", (x, -78.0, 1.2), 0.0, 26.0, 34.0)
    for i in range(10):
        props.container(ctx, f"container{i}", (-178 + (i % 5) * 5.0, -70.0 + (i // 5) * 7.0, 1.2), 0.0)
    vehicles.ship(ctx, "ship", (-150.0, -98.0, -0.5), math.pi / 2, 70.0)
    for i in range(4):
        vehicles.boat(ctx, f"boat{i}", (-118 + i * 7.0, -82.0 - i * 2.0, -0.4), rng.uniform(-0.3, 0.3), 7.0, sail=i % 2 == 0)
    vehicles.boat(ctx, "river_boat", (23.0, -56.0, 0.5), 0.0, 6.0)
    ctx.anchor("port", (-150.0, -80.0, 1.2))
    ctx.anchor("ship", (-150.0, -98.0, 4.0))
    ctx.anchor("river_mouth", (23.0, -62.0, 0.5))
    ctx.anchor("river_mid", (23.0, 30.0, 0.5))
    ctx.anchor("reservoir", (60.0, 165.0, 10.5))
    ctx.anchor("dam", (60.0, 121.0, 16.0))
    ctx.anchor("towers", (0.0, 46.0, 24.0))
    ctx.anchor("city_centre", (0.0, 20.0, 2.0))
    ctx.anchor("coast", (0.0, -70.0, 0.0))
    ctx.anchor("hills", (60.0, 215.0, 36.0))
    ctx.anchor("resort", (-46.0, -46.0, 1.0))
    # traffic
    for i in range(int(spec.get("traffic", 10))):
        y = rng.choice((-23, 23, 69))
        direction = 1 if i % 2 else -1
        start_x = rng.uniform(-150, 150)
        car_obj = vehicles.car(ctx, f"traffic{i}", (start_x, y + direction * 2.5, 0.25), rot=math.pi / 2 if direction > 0 else -math.pi / 2)
        vehicles.drive(ctx, car_obj, [(start_x, y + direction * 2.5), (start_x + direction * 220.0, y + direction * 2.5)], 0.0, speed=11.0, z=0.25)
    # ambient pedestrians on the plaza
    people = int(spec.get("people", 14))
    for i in range(people):
        px, py = rng.uniform(-15, 15), rng.uniform(-16, 12)
        qx, qy = rng.uniform(-15, 15), rng.uniform(-16, 12)
        actor = characters.build(ctx, {"id": f"pedestrian{i}", "role": "civilian", "at": (px, py, 0.3)})
        characters.animate(ctx, actor, {"action": "walk", "path": [[px, py], [qx, qy]], "start": rng.uniform(0.0, 1.5)})
    if dry:
        for obj in ctx.tagged("water"):
            obj.location.z -= 7.0 if obj.name == "reservoir" else 1.6
        for obj in ctx.tagged("jet"):
            obj.scale = (0.01, 0.01, 0.01)
        vehicles.lorry(ctx, "tanker", (-8.0, -8.0, 0.3), math.pi / 2, "navy", "tanker")
        for i in range(2):
            vehicles.van(ctx, f"ambulance{i}", (12.0 + i * 4.0, -12.0, 0.3), math.pi, "white", "ambulance")
        for i, (dx, dy) in enumerate(((-14, 2), (-12, -14), (6, 4))):
            props.tent(ctx, f"tent{i}", (dx, dy, 0.3), (5.0, 3.5), 2.8, 0.0)
        for i in range(6):
            props.bottle_pallet(ctx, f"pallet{i}", (2.0 + (i % 3) * 1.6, -4.0 + (i // 3) * 1.4, 0.3), 2)
        characters.crowd(ctx, {"id": "queue", "count": 22, "area": (-6.0, -6.0, 2.0, 2.0), "roles": ["civilian", "civilian", "child"], "action": "queue", "to": [-6.0, -6.0], "direction": [1, -0.15], "gap": 0.85, "props": ["jerrycan", "bottle", "bucket"]})
        characters.crowd(ctx, {"id": "gatherers", "count": 10, "area": (0.0, -20.0, 20.0, 8.0), "roles": ["civilian", "civilian", "worker"], "action": "gather", "to": [-8.0, -8.0], "radius": 6.0, "stagger": 2.0, "props": ["jerrycan", "bucket"]})
    return quay


def residential_street(ctx, spec):
    rng = ctx.rng
    seed = int(spec.get("seed", 2))
    pal = ctx.palette
    terrain.ground(ctx, "ground", (300, 300), (40, 40), amplitude=0.6, seed=seed, material=pal.terrain("lawn", [(-1.0, "grass"), (0.0, "grass"), (2.0, "grass_dry")]), noise_scale=0.05)
    props.road(ctx, "street", (-80, 0), (80, 0), 8.0, 0.02)
    for side in (-1, 1):
        props.pavement(ctx, f"pavement{side}", (0, side * 5.5), (160, 3.0), 0.0)
    for i, x in enumerate(range(-45, 46, 15)):
        for side in (-1, 1):
            name = f"house{i}{'n' if side > 0 else 's'}"
            rot = 0.0 if side > 0 else math.pi
            buildings.house(ctx, name, (x, side * 18.0, 0.0), seed * 10 + i * 2 + (side > 0), rot, (9.0, 7.5, 3.4 * rng.choice((1, 1, 2))))
            box(ctx, f"{name}.drive", (3.2, 9.0, 0.05), (x + 5.5, side * 11.5, 0.0), ctx.mat("asphalt"), anchor="base")
            if rng.random() < 0.5:
                vehicles.car(ctx, f"{name}.car", (x + 5.5, side * 11.0, 0.05), rot=math.pi / 2)
            if rng.random() < 0.3:
                water.pool(ctx, f"{name}.pool", (x - 2.0, side * 10.0, 0.0), (4.5, 2.6), deck=False)
            vegetation.tree(ctx, f"{name}.tree", (x - 5.0, side * 9.5, 0.0), "round", rng.uniform(0.7, 1.0))
            props.fence(ctx, f"{name}.fence", (x - 7.5, side * 7.2), (x + 7.5, side * 7.2), 0.0, 0.9)
    for i, x in enumerate(range(-60, 61, 20)):
        props.lamp_post(ctx, f"lamp{i}", (x, 6.5, 0.0), 6.0, math.pi)
    # house_1 (x = -30, north side) carries the roof tank and garden tap used by the storyboard
    water.tank(ctx, "roof_tank", (-28.0, 20.0, 6.9), 1.0, 1.3, legs=False)
    cylinder(ctx, "tap_post", 0.06, 0.8, (-28.0, 9.0, 0.0), ctx.mat("dark_steel"), segments=6, anchor="base")
    props.tap(ctx, "garden_tap", (-28.0, 9.0, 0.8), rot=math.pi, scale=1.2)
    props.jerrycan(ctx, "can1", (-27.4, 8.3, 0.0), rot=0.4)
    props.jerrycan(ctx, "can2", (-28.6, 8.2, 0.0), rot=-0.3)
    held = props.held(ctx, "bucket1", "bucket")
    held.location = (-27.0, 9.2, 0.0)
    ctx.anchor("street", (0.0, 0.0, 0.0))
    ctx.anchor("house_1", (-30.0, 18.0, 2.0))
    ctx.anchor("garden_tap", (-28.0, 8.9, 0.95))
    ctx.anchor("roof_tank", (-28.0, 20.0, 7.6))
    ctx.anchor("pavement_n", (-28.0, 5.5, 0.2))
    return None


def kitchen_interior(ctx, spec):
    pal = ctx.palette
    box(ctx, "floor", (6.0, 5.2, 0.1), (0.0, 0.0, -0.1), ctx.mat("stone", roughness=0.4), anchor="base")
    box(ctx, "wall_back", (6.0, 0.2, 2.9), (0.0, 2.3, 0.0), ctx.mat("cream"), anchor="base")
    box(ctx, "wall_left", (0.2, 5.2, 2.9), (-3.0, 0.0, 0.0), ctx.mat("cream"), anchor="base")
    box(ctx, "wall_right", (0.2, 5.2, 2.9), (3.0, 0.0, 0.0), ctx.mat("plaster"), anchor="base")
    box(ctx, "counter", (4.6, 0.65, 0.88), (0.0, 1.88, 0.0), ctx.mat("white", roughness=0.5), bevel=0.02, anchor="base")
    box(ctx, "worktop", (4.7, 0.7, 0.05), (0.0, 1.88, 0.88), ctx.mat("trunk", roughness=0.4), bevel=0.01, anchor="base")
    doors = [((-2.3 + 0.78 * i + 0.39, -0.33, 0.44), (0.72, 0.03, 0.78), 0) for i in range(6)]
    doors += [((-2.3 + 0.78 * i + 0.39, -0.35, 0.72), (0.2, 0.02, 0.03), 1) for i in range(6)]
    multi_box(ctx, "cupboards", doors, [ctx.mat("teal", roughness=0.5), ctx.mat("steel", metallic=0.8, roughness=0.3)], (0.0, 1.88, 0.0))
    uppers = [((-2.3 + 0.78 * i + 0.39, 0.0, 0.0), (0.74, 0.36, 0.7), 0) for i in range(6) if i not in (2, 3)]
    multi_box(ctx, "upper_cupboards", uppers, [ctx.mat("teal", roughness=0.5)], (0.0, 2.05, 2.0), bevel=0.01)
    props.sink(ctx, "sink", (0.4, 1.75, 0.93), (0.8, 0.46))
    props.tap(ctx, "tap", (0.4, 2.02, 0.93), rot=math.pi, scale=1.0)
    box(ctx, "window_frame", (1.5, 0.08, 1.1), (0.4, 2.18, 1.35), ctx.mat("white"), bevel=0.01, anchor="base")
    box(ctx, "window_pane", (1.34, 0.03, 0.96), (0.4, 2.16, 1.42), pal.emissive("daylight pane", (0.78, 0.88, 1.0), 3.0), anchor="base")
    multi_box(ctx, "window_bars", [((0.0, 0.0, 0.0), (0.04, 0.05, 0.96), 0), ((0.0, 0.0, 0.0), (1.34, 0.05, 0.04), 0)], [ctx.mat("white")], (0.4, 2.15, 1.9))
    cylinder(ctx, "glass", 0.045, 0.14, (0.42, 1.6, 0.93), ctx.palette.water("glass tumbler", "bottle", roughness=0.1, alpha=0.5), segments=12, anchor="base")
    props.held(ctx, "pan", "pan").location = (1.7, 1.85, 0.93)
    box(ctx, "fridge", (0.8, 0.7, 1.9), (2.5, 1.8, 0.0), ctx.mat("steel", roughness=0.35, metallic=0.6), bevel=0.03, anchor="base")
    box(ctx, "table", (1.3, 0.9, 0.05), (-1.3, -0.6, 0.75), ctx.mat("trunk", roughness=0.5), bevel=0.01, anchor="base")
    for dx, dy in ((-0.55, -0.35), (0.55, -0.35), (-0.55, 0.35), (0.55, 0.35)):
        box(ctx, "table_leg", (0.06, 0.06, 0.75), (-1.3 + dx, -0.6 + dy, 0.0), ctx.mat("dark_steel"), anchor="base")
    for i, (dx, dy) in enumerate(((-0.4, -1.2), (0.5, -1.2))):
        box(ctx, f"chair{i}", (0.45, 0.45, 0.05), (-1.3 + dx, -0.6 + dy, 0.45), ctx.mat("teal"), anchor="base")
        box(ctx, f"chair{i}.back", (0.45, 0.05, 0.45), (-1.3 + dx, -0.6 + dy - 0.2, 0.5), ctx.mat("teal"), anchor="base")
    for i in range(3):
        bottle = props.held(ctx, f"bottle{i}", "bottle")
        bottle.location = (-2.0 + i * 0.14, 1.75, 0.93)
    props.drip(ctx, "drop", (0.4, 1.81, 1.0))
    lighting.area_light(ctx, "fill", (0.0, -1.5, 2.7), 140.0, 4.0, (1.0, 0.93, 0.84), (math.radians(20), 0, 0))
    ctx.anchor("tap", (0.4, 1.81, 1.02))
    ctx.anchor("spout", (0.4, 1.81, 1.02))
    ctx.anchor("sink", (0.4, 1.75, 0.9))
    ctx.anchor("glass", (0.42, 1.6, 1.0))
    ctx.anchor("window", (0.4, 2.15, 1.9))
    ctx.anchor("room", (0.0, 0.3, 1.2))
    return None


def supermarket_interior(ctx, spec):
    pal = ctx.palette
    box(ctx, "floor", (44.0, 40.0, 0.1), (0.0, 0.0, -0.1), ctx.mat("pavement", roughness=0.3), anchor="base")
    box(ctx, "ceiling", (44.0, 40.0, 0.2), (0.0, 0.0, 5.2), ctx.mat("white"), anchor="base")
    for name, loc, size in (("wall_back", (0, 20, 0), (44, 0.3, 5.2)), ("wall_left", (-22, 0, 0), (0.3, 40, 5.2)), ("wall_right", (22, 0, 0), (0.3, 40, 5.2))):
        box(ctx, name, size, loc, ctx.mat("cream"), anchor="base")
    box(ctx, "front_glass", (44.0, 0.2, 5.0), (0.0, -20.0, 0.0), ctx.palette.glass("front glass"), anchor="base")
    strips = [((x, y, 0.0), (0.3, 6.0, 0.08), 0) for x in (-14, -7, 0, 7, 14) for y in range(-15, 16, 10)]
    multi_box(ctx, "light_strips", strips, [pal.emissive("strip light", (1.0, 0.98, 0.92), 6.0)], (0.0, 0.0, 5.15))
    for x, y in ((-10, -10), (-10, 8), (10, -10), (10, 8), (0, 0)):
        lighting.area_light(ctx, f"ceiling_light{x}{y}", (x, y, 5.0), 900.0, 8.0, (1.0, 0.98, 0.92))
    props.shelf_unit(ctx, "shelf_water_r", (2.9, 0.0, 0.0), 26.0, 4, -math.pi / 2, 1.0, 8)
    props.shelf_unit(ctx, "shelf_water_l", (-2.9, 0.0, 0.0), 26.0, 4, math.pi / 2, 1.0, 8)
    for x, rot in ((-8.5, math.pi / 2), (-9.5, -math.pi / 2), (8.5, math.pi / 2), (9.5, -math.pi / 2), (-15.5, -math.pi / 2), (15.5, math.pi / 2)):
        props.shelf_unit(ctx, f"shelf{x}", (x, 0.0, 0.0), 26.0, 4, rot, 0.0, 1)
        boxes = []
        for i in range(60):
            boxes.append(((-12.5 + i * 0.42, -0.1, 0.33 + (i % 4) * 0.52), (0.36, 0.5, 0.36), i % 4))
        multi_box(ctx, f"shelf{x}.goods", boxes, [ctx.mat("red"), ctx.mat("yellow"), ctx.mat("teal"), ctx.mat("orange")], (x, 0.0, 0.0), (0, 0, rot))
    for i in range(4):
        box(ctx, f"checkout{i}", (1.0, 3.0, 0.95), (-9.0 + i * 5.0, -16.0, 0.0), ctx.mat("stone"), bevel=0.02, anchor="base")
        box(ctx, f"checkout{i}.screen", (0.4, 0.1, 0.3), (-9.0 + i * 5.0, -15.0, 1.1), ctx.mat("dark_steel"), anchor="base")
    props.sign_text(ctx, "sign", "WATER", (0.0, 14.0, 3.6), 0.9, colour="white", emission=2.0, weight=0.015)
    box(ctx, "sign_board", (6.5, 0.2, 1.5), (0.0, 14.15, 2.9), ctx.mat("teal"), bevel=0.03, anchor="base")
    props.trolley(ctx, "trolley0", (1.2, -5.0, 0.0), 0.2)
    props.trolley(ctx, "trolley1", (-1.4, 9.0, 0.0), -0.4)
    ctx.anchor("aisle", (0.0, -4.0, 1.4))
    ctx.anchor("aisle_end", (0.0, 12.0, 1.4))
    ctx.anchor("shelf_water", (2.6, 0.0, 1.2))
    ctx.anchor("entrance", (0.0, -18.0, 1.5))
    ctx.anchor("sign", (0.0, 14.0, 3.6))
    return None


def distribution_point(ctx, spec):
    rng = ctx.rng
    pal = ctx.palette
    terrain.ground(ctx, "ground", (400, 400), (40, 40), amplitude=0.5, seed=5, material=pal.terrain("lot ground", [(-1.0, "grass"), (0.0, "grass"), (2.0, "grass_dry")]), noise_scale=0.05)
    box(ctx, "car_park", (80.0, 56.0, 0.08), (0.0, 0.0, 0.0), ctx.mat("asphalt", roughness=0.85), anchor="base")
    bays = [((-34 + i * 4.0, y, 0.0), (0.18, 5.0, 0.01), 0) for i in range(18) for y in (-22.0, 22.0)]
    multi_box(ctx, "bay_lines", bays, [ctx.mat("road_line")], (0.0, 0.0, 0.085))
    tanker = vehicles.lorry(ctx, "tanker", (0.0, 12.0, 0.08), 0.0, "navy", "tanker")
    for i, (x, y, rot) in enumerate(((16.0, -4.0, 0.0), (20.0, 7.0, 0.3), (-20.0, 10.0, -0.2))):
        props.tent(ctx, f"tent{i}", (x, y, 0.08), (6.0, 4.0), 3.0, rot, rng.choice(("canvas", "white", "teal")))
    for i in range(10):
        props.barrier(ctx, f"barrier{i}", (-4.0 - i * 2.5, 5.0, 0.08), 0.0)
        props.barrier(ctx, f"barrier_b{i}", (-4.0 - i * 2.5, 8.5, 0.08), 0.0)
    for i in range(8):
        props.bottle_pallet(ctx, f"pallet{i}", (6.0 + (i % 4) * 1.6, -8.0 + (i // 4) * 1.5, 0.08), 3)
    vehicles.van(ctx, "aid_van", (26.0, 14.0, 0.08), math.pi / 2, "white", "van")
    vehicles.van(ctx, "ambulance", (-30.0, -16.0, 0.08), 0.0, "white", "ambulance")
    vehicles.car(ctx, "police", (30.0, -18.0, 0.08), math.pi / 2, "white")
    for i, x in enumerate((-60, -20, 20, 60)):
        buildings.apartment(ctx, f"apt{i}", (x, 52.0, 0.0), 30 + i)
    buildings.supermarket(ctx, "store", (0.0, -62.0, 0.0), math.pi)
    for i, (x, y) in enumerate(((-48, -20), (-48, 20), (48, -20), (48, 20), (-30, 34), (30, 34))):
        vegetation.tree(ctx, f"tree{i}", (x, y, 0.0), "round", 1.1)
    for i, (x, y) in enumerate(((-38, -26), (38, -26), (-38, 26), (38, 26))):
        props.lamp_post(ctx, f"lamp{i}", (x, y, 0.08), 7.0)
    ctx.anchor("tanker", (0.0, 12.0, 1.5))
    ctx.anchor("tap", ctx.anchors.get("tanker.tap", (1.8, 8.8, 1.1)))
    ctx.anchor("queue_front", (-3.0, 6.8, 0.1))
    ctx.anchor("tents", (18.0, 1.0, 1.5))
    ctx.anchor("lot", (0.0, 0.0, 0.1))
    return tanker


def hospital_exterior(ctx, spec):
    pal = ctx.palette
    terrain.ground(ctx, "ground", (400, 400), (40, 40), amplitude=0.5, seed=6, material=pal.terrain("hospital ground", [(-1.0, "grass"), (0.0, "grass"), (2.0, "grass_dry")]), noise_scale=0.05)
    box(ctx, "forecourt", (96.0, 64.0, 0.08), (0.0, -6.0, 0.0), ctx.mat("asphalt", roughness=0.85), anchor="base")
    props.road(ctx, "road", (-120, -34), (120, -34), 10.0, 0.02)
    props.road(ctx, "approach", (-20, -34), (-20, -6), 8.0, 0.1, lines=False)
    buildings.hospital(ctx, "hospital", (0.0, 34.0, 0.0))
    for i in range(2):
        vehicles.van(ctx, f"parked_ambulance{i}", (12.0 + i * 4.5, 4.0, 0.08), math.pi, "white", "ambulance")
    vehicles.lorry(ctx, "bowser", (-16.0, 4.0, 0.08), math.pi / 2, "white", "tanker")
    for i in range(4):
        props.bottle_pallet(ctx, f"pallet{i}", (-8.0 + i * 1.6, 2.0, 0.08), 3)
    for i, (x, y) in enumerate(((-40, 6), (40, 6), (-44, -28), (44, -28))):
        vegetation.tree(ctx, f"tree{i}", (x, y, 0.0), "round", 1.2)
    for i, (x, y) in enumerate(((-30, -20), (30, -20), (-12, -18), (12, -18))):
        props.lamp_post(ctx, f"lamp{i}", (x, y, 0.08), 7.0)
    for i, x in enumerate((-70, 70)):
        buildings.apartment(ctx, f"apt{i}", (x, 40.0, 0.0), 40 + i)
    props.sign_text(ctx, "sign", "EMERGENCY", (0.0, 13.6, 3.2), 1.1, colour="white", emission=2.0, weight=0.02)
    box(ctx, "sign_board", (12.0, 0.3, 2.0), (0.0, 13.9, 2.4), ctx.mat("red"), bevel=0.03, anchor="base")
    ctx.anchor("entrance", (0.0, 12.0, 1.5))
    ctx.anchor("bay", (14.0, 4.0, 1.5))
    ctx.anchor("roof", (12.0, 38.0, 19.0))
    ctx.anchor("road_west", (-70.0, -34.0, 1.0))
    ctx.anchor("forecourt", (0.0, -8.0, 1.0))
    ctx.anchor("hospital", (0.0, 34.0, 9.0))
    return None


def farm(ctx, spec):
    rng = ctx.rng
    pal = ctx.palette
    terrain.ground(ctx, "ground", (700, 700), (70, 70), amplitude=4.0, seed=8, material=pal.terrain("farm ground", [(-3.0, "soil"), (0.0, "grass_dry"), (1.5, "grass"), (12.0, "grass_dry"), (40.0, "rock")]), flat=[(-140, -110, 140, 120, 30)], rise={"axis": "y", "start": 150, "end": 350, "height": 60, "extra_noise": 12.0}, noise_scale=0.01)
    vegetation.crop_rows(ctx, "field_west", (-70.0, 55.0, 0.0), (110.0, 90.0), 1.8, 1.0)
    vegetation.crop_rows(ctx, "field_pivot", (70.0, 60.0, 0.0), (104.0, 104.0), 1.8, 1.0, circle=True)
    # centre-pivot irrigator: root empty at the centre, truss with towers and sprays
    pivot = empty(ctx, "pivot", (70.0, 60.0, 0.0))
    hub = cylinder(ctx, "pivot.hub", 0.6, 4.0, (0, 0, 0), ctx.mat("steel"), segments=10, anchor="base")
    parent(hub, pivot)
    truss = box(ctx, "pivot.truss", (50.0, 0.5, 0.5), (25.0, 0.0, 3.8), ctx.mat("steel"), bevel=0.05)
    parent(truss, pivot)
    for i in range(1, 5):
        tower = box(ctx, f"pivot.tower{i}", (0.3, 2.0, 3.5), (i * 12.0, 0.0, 0.0), ctx.mat("dark_steel"), anchor="base")
        parent(tower, pivot)
        for dy in (-1.0, 1.0):
            wheel = cylinder(ctx, f"pivot.wheel{i}", 0.7, 0.4, (i * 12.0, dy, 0.7), ctx.mat("black"), segments=10, rot=(math.pi / 2, 0, 0))
            parent(wheel, pivot)
        spray = box(ctx, f"pivot.spray{i}", (10.0, 4.0, 0.4), (i * 12.0 - 6.0, 0.0, 2.4), ctx.palette.water(f"pivot spray {i}", "pool", alpha=0.45), anchor="base")
        parent(spray, pivot)
        ctx.tag("spray", spray)
    ctx.objects["pivot"] = pivot
    for i in range(10):
        props.sprinkler(ctx, f"sprinkler{i}", (-118.0 + i * 11.0, 8.0, 0.0), 1.4, spray=True)
    buildings.barn(ctx, "barn", (-80.0, -70.0, 0.0), 0.0)
    buildings.house(ctx, "farmhouse", (-45.0, -92.0, 0.0), 9, 0.0, (12.0, 9.0, 3.6))
    buildings.silo(ctx, "silo", (-104.0, -70.0, 0.0), 3.0, 14.0)
    buildings.water_tower(ctx, "water_tower", (-125.0, -30.0, 0.0), 16.0, 3.5)
    props.fence(ctx, "fence_s", (-50, -72), (10, -72), 0.0)
    props.fence(ctx, "fence_n", (-50, -28), (10, -28), 0.0)
    props.fence(ctx, "fence_w", (-50, -72), (-50, -28), 0.0)
    props.fence(ctx, "fence_e", (10, -72), (10, -28), 0.0)
    water.trough(ctx, "trough", (-20.0, -50.0, 0.0), (4.0, 1.0))
    for i, (dx, dy, rot) in enumerate(((-3.5, 1.4, 0.9), (-1.0, 1.9, 0.2), (2.0, 1.6, -0.4), (3.6, -1.8, 2.6), (0.5, -2.2, 3.2), (-3.0, -2.4, 2.9))):
        props.cow(ctx, f"cow{i}", (-20.0 + dx, -50.0 + dy, 0.0), rot, rng.choice(("white", "white", "rust")))
    vehicles.tractor(ctx, "tractor", (-40.0, -40.0, 0.0), 0.4)
    props.road(ctx, "track", (-140, -10), (140, -10), 6.0, 0.02, lines=False)
    vegetation.scatter_trees(ctx, "trees", (0.0, -120.0, 0.0), 120.0, 14, ("round", "conifer"), avoid=[(-120, -110, 30, -20)])
    vegetation.scatter_trees(ctx, "hill_trees", (0.0, 200.0, 0.0), 160.0, 18, ("conifer", "round"))
    ctx.anchor("pivot", (70.0, 60.0, 2.0))
    ctx.anchor("pivot_tip", (120.0, 60.0, 4.0))
    ctx.anchor("trough", (-20.0, -50.0, 0.6))
    ctx.anchor("paddock", (-20.0, -48.0, 1.0))
    ctx.anchor("barn", (-80.0, -70.0, 4.0))
    ctx.anchor("fields", (0.0, 50.0, 1.0))
    ctx.anchor("farmhouse", (-45.0, -92.0, 2.0))
    ctx.anchor("sprinklers", (-65.0, 8.0, 1.0))
    return pivot


def industrial(ctx, spec):
    pal = ctx.palette
    terrain.ground(ctx, "ground", (600, 600), (60, 60), amplitude=1.5, seed=9, material=pal.terrain("yard ground", [(-2.0, "stone"), (0.0, "concrete"), (3.0, "grass_dry"), (20.0, "rock")]), flat=[(-120, -90, 120, 130, 20)], noise_scale=0.02)
    buildings.cooling_tower(ctx, "tower_a", (-40.0, 60.0, 0.0), 14.0, 48.0)
    buildings.cooling_tower(ctx, "tower_b", (0.0, 72.0, 0.0), 14.0, 48.0)
    buildings.warehouse(ctx, "turbine_hall", (55.0, 60.0, 0.0), (60.0, 90.0, 24.0), 0.0, "concrete")
    buildings.chimney(ctx, "chimney", (84.0, 108.0, 0.0), 3.0, 60.0)
    for i, (x, y) in enumerate(((-60, -10), (-42, -28), (-74, -36))):
        buildings.storage_tank(ctx, f"tank{i}", (x, y, 0.0), 8.0, 10.0, "white")
    props.pipe(ctx, "pipe_a", [(-20, -70, 3), (-20, 40, 3), (-20, 40, 3)], 0.6, "steel")
    props.pipe(ctx, "pipe_b", [(-17, -70, 3), (-17, 40, 3)], 0.5, "rust")
    for i in range(12):
        box(ctx, f"pipe_support{i}", (5.0, 0.6, 2.6), (-18.5, -66.0 + i * 9.5, 0.0), ctx.mat("dark_steel"), anchor="base")
    props.valve(ctx, "valve", (-20.0, -12.0, 4.2), 1.1, rot=(math.pi / 2, 0, 0))
    buildings.clarifier(ctx, "clarifier_a", (34.0, -50.0, 0.0), 9.0)
    buildings.clarifier(ctx, "clarifier_b", (56.0, -50.0, 0.0), 9.0)
    buildings.building(ctx, "control", (8.0, -24.0, 0.0), (22.0, 12.0, 7.0), "plaster", "flat", 0.0, 12, trim="dark_steel")
    for i in range(6):
        box(ctx, f"transformer{i}", (3.0, 2.4, 3.2), (-90.0 + i * 5.0, 30.0, 0.0), ctx.mat("dark_steel"), bevel=0.05, anchor="base")
        cylinder(ctx, f"insulator{i}", 0.3, 2.5, (-90.0 + i * 5.0, 30.0, 3.2), ctx.mat("white"), segments=8, anchor="base")
    for i in range(4):
        multi_box(ctx, f"pylon{i}", [((0, 0, 16), (1.2, 1.2, 32), 0), ((0, 0, 24), (12, 0.6, 0.6), 0), ((0, 0, 30), (8, 0.6, 0.6), 0)], [ctx.mat("dark_steel")], (-110.0 + i * 40.0, 100.0, 0.0))
    props.road(ctx, "yard_road", (-120, -60), (120, -60), 8.0, 0.02)
    vehicles.lorry(ctx, "lorry", (-30.0, -58.0, 0.05), math.pi / 2, "red", "container")
    for i, (x, y) in enumerate(((-100, -70), (100, -70), (-100, 80), (100, 20))):
        props.lamp_post(ctx, f"lamp{i}", (x, y, 0.0), 9.0)
    props.fence(ctx, "fence_s", (-120, -75), (120, -75), 0.0, 2.2, 6.0)
    ctx.anchor("towers", (-20.0, 66.0, 26.0))
    ctx.anchor("tower_top", (-40.0, 60.0, 50.0))
    ctx.anchor("valve", (-20.0, -12.0, 4.2))
    ctx.anchor("tanks", (-58.0, -25.0, 5.0))
    ctx.anchor("plant", (45.0, -50.0, 1.0))
    ctx.anchor("chimney_top", (84.0, 108.0, 62.0))
    ctx.anchor("yard", (0.0, 0.0, 2.0))
    return None


def reservoir(ctx, spec):
    rng = ctx.rng
    pal = ctx.palette
    ground_mat = pal.terrain("valley", [(-30.0, "mud"), (-16.0, "dry_bed"), (-4.6, "dry_bed"), (-3.0, "grass_dry"), (2.0, "grass"), (30.0, "rock"), (75.0, "white")])
    terrain.ground(ctx, "ground", (700, 700), (110, 110), amplitude=9.0, seed=10, material=ground_mat, bowl={"centre": (0.0, 70.0), "radius": 125.0, "depth": 26.0}, rise={"axis": "y", "start": 90, "end": 330, "height": 70, "extra_noise": 16.0}, flat=[(-70, -120, 70, -60, 25)], noise_scale=0.012)
    lake = water.surface(ctx, "reservoir", (300, 300), (0.0, 70.0, -4.0), "lake", tags=("water", "reservoir"))
    buildings.dam(ctx, "dam", (0.0, -52.0, -0.5), 170.0, 26.0, 13.0)
    buildings.intake_tower(ctx, "intake", (16.0, -14.0, -16.0), 30.0)
    for i, (x, y) in enumerate(((-16, -96), (6, -96), (28, -96))):
        buildings.clarifier(ctx, f"clarifier{i}", (x, y, 0.0), 8.0)
    buildings.building(ctx, "pump_house", (-40.0, -92.0, 0.0), (18.0, 10.0, 6.0), "plaster", "flat", 0.0, 13, trim="dark_steel")
    props.pipe(ctx, "penstock", [(-10, -62, 2), (-10, -84, 1.5)], 1.2, "steel")
    props.road(ctx, "valley_road", (-200, -70), (200, -70), 8.0, 0.02)
    for i in range(3):
        craft = vehicles.boat(ctx, f"boat{i}", (-64.0 + i * 9.0, 18.0 + i * 4.0, -4.0), rng.uniform(-0.6, 0.6), 6.5, sail=i == 1)
        water.float_on(ctx, craft, lake)
    box(ctx, "jetty", (3.0, 30.0, 0.8), (-70.0, 6.0, -4.5), ctx.mat("trunk"), anchor="base")
    vegetation.scatter_trees(ctx, "trees", (0.0, 60.0, 0.0), 260.0, 40, ("conifer", "round", "conifer"), avoid=[(-125, -55, 125, 195)], dry=False)
    ctx.anchor("dam", (0.0, -52.0, 0.0))
    ctx.anchor("dam_crest", (0.0, -52.0, 26.0))
    ctx.anchor("water", (0.0, 70.0, -4.0))
    ctx.anchor("intake", (16.0, -14.0, 12.0))
    ctx.anchor("plant", (6.0, -96.0, 2.0))
    ctx.anchor("overview", (0.0, 50.0, -4.0))
    ctx.anchor("shore_west", (-110.0, 40.0, -2.0))
    return lake


def port(ctx, spec):
    rng = ctx.rng
    pal = ctx.palette
    terrain.ground(ctx, "ground", (600, 600), (60, 60), amplitude=1.0, seed=11, material=pal.terrain("port ground", [(-10.0, "mud"), (-1.0, "beach"), (0.0, "concrete"), (4.0, "grass_dry")]), coast={"y": -20.0, "depth": 11.0, "width": 40.0}, noise_scale=0.02)
    water.surface(ctx, "sea", (800, 400), (0.0, -230.0, -0.6), "sea", tags=("sea",))
    box(ctx, "quay", (260.0, 40.0, 2.2), (0.0, -4.0, -1.0), ctx.mat("concrete"), bevel=0.1, anchor="base")
    for i, x in enumerate((-80, 0, 80)):
        vehicles.crane(ctx, f"crane{i}", (x, -14.0, 1.2), 0.0, 44.0, 56.0)
    for i in range(36):
        props.container(ctx, f"container{i}", (-110.0 + (i % 12) * 9.0, 4.0 + (i // 12) * 7.0, 1.2), 0.0)
    for i in range(14):
        props.container(ctx, f"container_top{i}", (-104.0 + i * 11.0, 11.0, 3.8), 0.0)
    vehicles.ship(ctx, "ship", (0.0, -50.0, -0.6), math.pi / 2, 130.0, "navy")
    vehicles.ship(ctx, "ship_far", (110.0, -120.0, -0.6), math.radians(70), 90.0, "red")
    for i in range(3):
        vehicles.boat(ctx, f"boat{i}", (-150.0 + i * 8.0, -40.0, -0.5), rng.uniform(-0.4, 0.4), 7.0)
    props.road(ctx, "port_road", (-200, 32), (200, 32), 10.0, 0.02)
    for i in range(9):
        vehicles.lorry(ctx, f"lorry{i}", (-120.0 + i * 16.0, 29.5, 0.05), math.pi / 2, rng.choice(("white", "red", "navy", "teal")), "container")
    for i, x in enumerate((-90, -30, 40, 100)):
        buildings.warehouse(ctx, f"warehouse{i}", (x, 62.0, 0.0), (44.0, 26.0, 10.0), 0.0, rng.choice(("steel", "stone", "concrete")))
    for i, (x, y) in enumerate(((-120, 20), (-60, 20), (0, 20), (60, 20), (120, 20))):
        props.lamp_post(ctx, f"lamp{i}", (x, y, 1.2), 12.0)
    ctx.anchor("quay", (0.0, -2.0, 2.2))
    ctx.anchor("crane", (0.0, -14.0, 20.0))
    ctx.anchor("ship", (0.0, -50.0, 6.0))
    ctx.anchor("ship_bow", (65.0, -50.0, 8.0))
    ctx.anchor("trucks", (-40.0, 30.0, 2.0))
    ctx.anchor("overview", (0.0, 0.0, 2.0))
    return None


def desert(ctx, spec):
    rng = ctx.rng
    pal = ctx.palette
    terrain.ground(ctx, "ground", (800, 800), (90, 90), amplitude=16.0, seed=12, material=pal.terrain("desert ground", [(-6.0, "dry_bed"), (0.0, "sand"), (14.0, "beach"), (60.0, "cliff"), (120.0, "rock")]), flat=[(-90, -90, 90, 90, 40)], rise={"axis": "y", "start": 160, "end": 400, "height": 110, "extra_noise": 30.0}, noise_scale=0.008)
    box(ctx, "lake_bed", (170.0, 130.0, 0.1), (40.0, 40.0, 0.02), pal.cracked("cracked bed", "dry_bed", "mud", 0.3), anchor="base")
    water.river(ctx, "riverbed", [(-220, -120), (-120, -60), (-30, -30), (40, -40), (120, 10), (200, 90)], width=14.0, z=-0.3, bed=True, bank=False)
    for obj in ctx.tagged("water"):
        obj.location.z -= 2.0
    for i in range(12):
        vegetation.tree(ctx, f"dead{i}", (rng.uniform(-160, 160), rng.uniform(-160, 120), 0.0), "dead")
    for i in range(24):
        ico(ctx, f"rock{i}", rng.uniform(1.0, 4.0), (rng.uniform(-200, 200), rng.uniform(-200, 150), 0.0), ctx.mat("rock"), subdiv=1, scale=(1.4, 1.0, 0.7))
    craft = vehicles.boat(ctx, "stranded", (40.0, 50.0, 0.0), 0.8, 8.0, "white")
    craft.rotation_euler = (0.0, math.radians(14), 0.8)
    ctx.anchor("riverbed", (0.0, -30.0, 0.0))
    ctx.anchor("lake_bed", (40.0, 40.0, 0.0))
    ctx.anchor("boat", (40.0, 50.0, 1.0))
    ctx.anchor("dunes", (-120.0, 100.0, 12.0))
    return None


BUILDERS = {
    "coastal_city": coastal_city,
    "residential_street": residential_street,
    "kitchen_interior": kitchen_interior,
    "supermarket_interior": supermarket_interior,
    "distribution_point": distribution_point,
    "hospital_exterior": hospital_exterior,
    "farm": farm,
    "industrial": industrial,
    "reservoir": reservoir,
    "port": port,
    "desert": desert,
}
assert set(BUILDERS) == set(catalogue.ENVIRONMENTS), "environment catalogue and builders differ"


def build(ctx, spec):
    return BUILDERS[spec["type"]](ctx, spec)
