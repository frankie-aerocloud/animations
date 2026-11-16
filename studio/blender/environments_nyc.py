"""New York style environments for the seagull production: a dawn harbour off Brooklyn, a Manhattan
style metropolis (Times Square, Central Park, landmarks, bridge, statue) and an airport."""

from __future__ import annotations

import math

from studio.assets import birds, buildings, landmarks, props, terrain, vegetation, vehicles, water
from studio.assets import characters
from studio.blender.primitives import box, cylinder
from studio.core.motion import heading

AVENUES = (-200, -120, -40, 40, 120, 200)
BLOCK_X = (-160, -80, 0, 80, 160)
STREETS = tuple(range(-680, 881, 60))
PARK = (-120.0, 400.0, 120.0, 900.0)
BILLBOARD_MESSAGES = ("STAY INDOORS", "HIDE YOUR FRIES", "BREAKING: GULLS", "ALL FLIGHTS CANCELLED", "DO NOT FEED THE BIRDS", "UMBRELLAS HALF PRICE", "SHELTER THIS WAY", "PIZZA $1", "COVER YOUR LUNCH")
FOCUS_POINTS = {
    "times_square": (0.0, 70.0),
    "midtown": (0.0, 160.0),
    "park": (0.0, 650.0),
    "downtown": (-60.0, -520.0),
    "bridge": (240.0, -330.0),
    "statue": (-330.0, -780.0),
    "harbour": (-200.0, -820.0),
}


def _in_park(x, y):
    return PARK[0] - 30 < x < PARK[2] + 30 and PARK[1] - 30 < y < PARK[3] + 30


def harbour_dawn(ctx, spec):
    """Brooklyn shoreline at first light looking out over the Atlantic; swarms approach from the sea."""
    rng = ctx.rng
    water.surface(ctx, "sea", (3000, 3000), (0.0, 400.0, -0.6), "sea", tags=("sea",))
    box(ctx, "shore", (1600.0, 700.0, 3.0), (0.0, -380.0, -3.3), ctx.mat("sand"), anchor="base")
    box(ctx, "promenade", (600.0, 30.0, 1.0), (0.0, -35.0, -0.3), ctx.mat("pavement"), bevel=0.1, anchor="base")
    box(ctx, "pier", (10.0, 100.0, 1.4), (0.0, 20.0, -0.8), ctx.mat("trunk", roughness=0.9), bevel=0.05, anchor="base")
    for i in range(10):
        cylinder(ctx, f"pile{i}", 0.3, 3.0, (-5.0 + 10.0 * (i % 2), -20.0 + 9.0 * (i // 2), -2.0), ctx.mat("trunk"), segments=8, anchor="base")
    for i, x in enumerate(range(-260, 261, 40)):
        buildings.house(ctx, f"house{i}", (x, -80.0, -0.3), 50 + i, 0.0, (14.0, 10.0, 4.0 * rng.choice((1, 2, 2))))
    for i, x in enumerate((-160.0, 120.0)):
        buildings.apartment(ctx, f"apt{i}", (x, -140.0, -0.3), 60 + i)
    cylinder(ctx, "lighthouse", 3.0, 18.0, (230.0, -40.0, -0.3), ctx.mat("white"), segments=12, anchor="base", radius2=2.2)
    cylinder(ctx, "lighthouse.cap", 3.2, 2.5, (230.0, -40.0, 17.7), ctx.mat("red"), segments=12, anchor="base", radius2=0.3)
    for i, x in enumerate(range(-250, 251, 50)):
        props.lamp_post(ctx, f"lamp{i}", (x, -28.0, 0.7), 6.0, 0.0, True)
    for i in range(6):
        props.bench(ctx, f"bench{i}", (-150.0 + i * 60.0, -32.0, 0.7), 0.0)
    for i in range(10):
        vegetation.tree(ctx, f"tree{i}", (-280.0 + i * 60.0, -58.0, -0.3), "round", 1.0)
    vehicles.boat(ctx, "trawler", (6.0, 84.0, -0.5), 0.0, 10.0, "navy")
    vehicles.boat(ctx, "dinghy", (-14.0, 28.0, -0.5), 0.4, 5.0, "white")
    vehicles.ship(ctx, "freighter", (420.0, 700.0, -0.6), math.radians(80), 110.0, "rust")
    # Manhattan on the horizon
    for i in range(14):
        h = rng.uniform(90, 260)
        box(ctx, f"skyline{i}", (rng.uniform(30, 60), rng.uniform(30, 60), h), (-900.0 + i * 55.0 + rng.uniform(-10, 10), -220.0 - abs(i - 7) * 20.0, -0.3), ctx.mat("stone"), bevel=0.3, anchor="base")
    landmarks.spire_tower(ctx, "empire_far", (-560.0, -260.0, -0.3), 300.0)
    swarms = int(spec.get("swarms", 0))
    near = bool(spec.get("swarm_near", False))
    for i in range(swarms):
        far = (rng.uniform(-150, 150), (520.0 if near else 900.0) + i * 140.0, (70.0 if near else 90.0) + i * 20.0)
        close = (rng.uniform(-60, 60), (-40.0 if near else 120.0) + i * 50.0, (26.0 if near else 55.0) + i * 12.0)
        birds.swarm(ctx, f"swarm{i}", int(spec.get("swarm_count", 2400)), far, (220.0, 200.0, 60.0), path=[far, close], start=0.0, end=ctx.duration + 1.0, size=1.6 if near else 1.3)
    for i in range(int(spec.get("flocks", 0))):
        birds.flock(ctx, f"flock{i}", 28, (rng.uniform(-60, 60), 420.0 + i * 80.0, 30.0 + i * 8.0), (26.0, 26.0, 10.0), path=[(rng.uniform(-60, 60), 420.0 + i * 80.0, 30.0 + i * 8.0), (rng.uniform(-30, 30), -60.0, 22.0 + i * 6.0)], start=float(spec.get("flock_start", 0.0)) + i * 0.8, speed=20.0, scale=1.1)
    ctx.anchor("boat", (6.0, 84.0, 1.2))
    ctx.anchor("deck", (6.0, 80.0, 0.9))
    ctx.anchor("pier_end", (0.0, 66.0, 0.8))
    ctx.anchor("horizon", (0.0, 900.0, 60.0))
    ctx.anchor("shore", (0.0, -30.0, 1.0))
    ctx.anchor("skyline", (-560.0, -260.0, 150.0))
    ctx.anchor("sea_mid", (0.0, 400.0, 20.0))
    return None


def _manhattan_grid(ctx, spec, night, lit, focus):
    rng = ctx.rng
    roosting = int(spec.get("birds", 0)) >= 3 or bool(spec.get("roost", False))
    perches = []
    seed = int(spec.get("seed", 3))
    glow_pick = (lambda: rng.choice(lit)) if lit else (lambda: None)
    for x in AVENUES:
        if abs(x) == 40:
            props.road(ctx, f"ave{x}", (x, -690), (x, 400), 14.0, 0.02)
        else:
            props.road(ctx, f"ave{x}", (x, -690), (x, 890), 14.0, 0.02)
    for y in STREETS:
        if PARK[1] <= y <= PARK[3]:
            props.road(ctx, f"st{y}w", (-240, y), (-120, y), 10.0, 0.02)
            props.road(ctx, f"st{y}e", (120, y), (240, y), 10.0, 0.02)
        else:
            props.road(ctx, f"st{y}", (-240, y), (240, y), 10.0, 0.02)
    count = 0
    for yi in range(len(STREETS) - 1):
        yc = STREETS[yi] + 30.0
        for xc in BLOCK_X:
            count += 1
            if _in_park(xc, yc):
                continue
            if xc == 0 and yc == 70.0:
                continue  # Times Square plaza
            if xc == 0 and yc == 190.0:
                landmarks.spire_tower(ctx, "empire", (0.0, 190.0, 0.0), 300.0, glow_pick())
                continue
            if xc == -80 and yc == -530.0:
                landmarks.tapered_tower(ctx, "wtc", (-80.0, -530.0, 0.0), 330.0, glow_pick())
                continue
            block_seed = seed * 1000 + count
            brng = __import__("random").Random(block_seed)
            if -100 <= yc <= 340:
                heights = (brng.uniform(60, 190), brng.uniform(50, 150))
                for i, (dx, dy) in enumerate(((-16, -12), (16, 12))):
                    buildings.building(ctx, f"b{count}.{i}", (xc + dx, yc + dy, 0.0), (brng.uniform(22, 30), brng.uniform(18, 24), heights[i]), brng.choice(("concrete", "stone", "plaster", "steel")), "flat", 0.0, block_seed + i, window=(1.6, 2.0), floor_height=3.6, lit=glow_pick(), units=True)
            elif yc <= -430:
                for i, (dx, dy) in enumerate(((-16, -12), (16, 12))):
                    buildings.building(ctx, f"b{count}.{i}", (xc + dx, yc + dy, 0.0), (brng.uniform(22, 30), brng.uniform(18, 24), brng.uniform(70, 230)), brng.choice(("steel", "concrete", "stone")), "flat", 0.0, block_seed + i, window=(1.8, 2.2), floor_height=3.8, lit=glow_pick(), trim="dark_steel")
            else:
                for i, (dx, dy) in enumerate(((-16, -12), (16, -12), (-16, 12), (16, 12))):
                    buildings.building(ctx, f"b{count}.{i}", (xc + dx, yc + dy, 0.0), (brng.uniform(22, 28), brng.uniform(16, 20), brng.uniform(18, 48)), brng.choice(("cream", "terracotta", "stone", "plaster")), "flat", 0.0, block_seed + i, window=(1.3, 1.6), lit=glow_pick(), tank=False)
    # Times Square plaza and dressing
    props.pavement(ctx, "ts_plaza", (0.0, 70.0), (64.0, 48.0), 0.0)
    closed = bool(spec.get("closed", False))
    for i, (dx, dy, rot) in enumerate(((-20, -14, 0.3), (-8, 10, 1.2), (6, -16, 2.0), (18, 6, 0.4), (24, -8, 1.5), (-24, 2, 2.8))):
        landmarks.food_cart(ctx, f"cart{i}", (dx, 70.0 + dy, 0.18), rot, open_umbrella=not closed)
    for i, (dx, dy) in enumerate(((-12, -4), (-4, -6), (4, -2), (12, -5), (-10, 16), (0, 18), (10, 16), (-18, 14))):
        landmarks.cafe_table(ctx, f"table{i}", (dx, 70.0 + dy, 0.18), rng.uniform(0, 3), umbrella=not closed)
    for i, (dx, dy) in enumerate(((-30, -22), (30, -22), (-30, 22), (30, 22), (0, -22), (0, 22), (-15, 0), (15, 0))):
        landmarks.bin_(ctx, f"bin{i}", (dx, 70.0 + dy, 0.18), knocked=closed and i % 2 == 0)
    for i, (dx, dy) in enumerate(((-28, -20), (28, -20), (-28, 20), (28, 20))):
        props.lamp_post(ctx, f"ts_lamp{i}", (dx, 70.0 + dy, 0.18), 8.0, 0.0, night)
        perches += [(dx, 70.0 + dy + arm, 8.2) for arm in (0.15, 0.6, 1.05)]
    for i, (x, y, rot, z) in enumerate(((-36, 70, math.pi / 2, 20), (-36, 70, math.pi / 2, 36), (36, 70, -math.pi / 2, 24), (36, 70, -math.pi / 2, 42), (0, 97, math.pi, 22), (-20, 97, math.pi, 40), (20, 97, math.pi, 58), (0, 43, 0.0, 26), (18, 43, 0.0, 46))):
        landmarks.billboard(ctx, f"billboard{i}", (x, y, z), (18.0 if i % 2 else 24.0, 10.0 if i % 2 else 14.0), rot, strength=5.0 if night else 3.0, message=BILLBOARD_MESSAGES[i % len(BILLBOARD_MESSAGES)])
    # Central Park
    box(ctx, "park_lawn", (240.0, 500.0, 0.4), (0.0, 650.0, 0.0), ctx.mat("grass"), anchor="base")
    water.surface(ctx, "park_lake", (110, 70), (0.0, 640.0, 0.42), "lake", tags=("water", "lake"))
    box(ctx, "park_path", (3.0, 480.0, 0.05), (-60.0, 650.0, 0.4), ctx.mat("sand"), anchor="base")
    box(ctx, "park_path2", (3.0, 480.0, 0.05), (60.0, 650.0, 0.4), ctx.mat("sand"), anchor="base")
    vegetation.scatter_trees(ctx, "park_trees", (0.0, 650.0, 0.4), 230.0, int(spec.get("park_trees", 140)), ("round", "round", "conifer"), avoid=[(-60, 600, 60, 680), (-125, 380, 125, 420)])
    # harbour, statue, bridge, piers
    landmarks.statue_of_liberty(ctx, "statue", (-330.0, -780.0, 0.0), heading((-330.0, -780.0), (0.0, -200.0)))
    landmarks.suspension_bridge(ctx, "bridge", (240.0, -330.0), (620.0, -430.0), 24.0, 84.0, roost=roosting, lights=night)
    for i, y in enumerate((-250, -150, -50, 50, 150)):
        box(ctx, f"pier{i}", (100.0, 14.0, 2.0), (-290.0, float(y), -1.5), ctx.mat("concrete"), bevel=0.1, anchor="base")
    for i in range(10):
        buildings.apartment(ctx, f"brooklyn{i}", (330.0 + (i % 5) * 60.0, -250.0 - (i // 5) * 90.0, -0.3), 90 + i)
    for i in range(8):
        buildings.apartment(ctx, f"jersey{i}", (-330.0 - (i % 4) * 70.0, -50.0 + (i // 4) * 120.0, -0.3), 110 + i)
    fx, fy = focus
    for i, x in enumerate((-40, 40)):
        for j, y in enumerate(range(-600, 881, 120)):
            if _in_park(x, y):
                continue
            props.lamp_post(ctx, f"lamp{i}{j}", (x + 9.0, float(y) + 3.0, 0.02), 8.0, 0.0, night and math.hypot(x - fx, y - fy) < 500)
            perches += [(x + 9.0, float(y) + 3.0 + arm, 8.04) for arm in (0.15, 0.6, 1.05)]
    if roosting:
        birds.roost(ctx, "roost.streetlights", perches, 1.0, jitter=0.0)
    return None


def metropolis(ctx, spec):
    """Manhattan-style island city. Flags: night, birds (0-3), splats (0-1), jam, guard, closed,
    nests, roost, rubbish, traffic, focus (times_square | midtown | park | downtown | bridge | statue | harbour)."""
    rng = ctx.rng
    night = bool(spec.get("night", False))
    focus = FOCUS_POINTS[str(spec.get("focus", "times_square"))]
    fx, fy = focus
    lit = []
    if night:
        for i in range(6):
            material = ctx.palette.make(f"windows lit {i}", (1.0, 0.7, 0.36), 0.5, 0.0, 1.4)
            ctx.tag("window_lights", material)
            lit.append(material)
    water.surface(ctx, "sea", (4000, 4000), (0.0, 0.0, -0.6), "sea", tags=("sea",))
    box(ctx, "manhattan", (480.0, 1600.0, 4.0), (0.0, 100.0, -4.0), ctx.mat("pavement"), anchor="base")
    box(ctx, "brooklyn", (1000.0, 1500.0, 3.0), (830.0, -200.0, -3.3), ctx.mat("pavement"), anchor="base")
    box(ctx, "jersey", (1000.0, 1800.0, 3.0), (-830.0, 100.0, -3.3), ctx.mat("pavement"), anchor="base")
    box(ctx, "liberty_island", (90.0, 90.0, 3.0), (-330.0, -780.0, -3.0), ctx.mat("grass"), anchor="base")
    _manhattan_grid(ctx, spec, night, lit, focus)
    # traffic: taxis
    for i in range(int(spec.get("traffic", 12))):
        x = rng.choice(AVENUES) + rng.choice((-4.0, 4.0))
        direction = 1 if x % 8 else -1
        start_y = rng.uniform(fy - 300, fy + 300)
        taxi = vehicles.car(ctx, f"taxi{i}", (x, start_y, 0.05), rot=0.0 if direction > 0 else math.pi, colour="taxi" if rng.random() < 0.7 else None, lit=night)
        vehicles.drive(ctx, taxi, [(x, start_y), (x, start_y + direction * 260.0)], 0.0, speed=11.0, z=0.05)
    if spec.get("jam", False) and abs(fy) < 600:
        reach = float(spec.get("jam_reach", 130.0))
        for x in (-40.0, 40.0):
            vehicles.traffic_jam(ctx, f"jam{x}", (x + 4.0, fy - reach), (x + 4.0, fy + reach), lanes=1, gap=7.5, lit=night, lane_width=3.2, lorries=0.1)
            vehicles.traffic_jam(ctx, f"jam{x}b", (x - 4.0, fy + reach), (x - 4.0, fy - reach), lanes=1, gap=10.0, lit=night, lane_width=3.2, lorries=0.1)
    if spec.get("guard", False):
        for i in range(5):
            landmarks.army_truck(ctx, f"army{i}", (-52.0, fy - 60.0 + i * 11.0, 0.05), 0.0, lit=night)
        for i in range(2):
            landmarks.loudspeaker_van(ctx, f"pa{i}", (52.0, fy - 30.0 + i * 30.0, 0.05), math.pi, lit=night)
        for i in range(3):
            landmarks.police_car(ctx, f"police{i}", (fx - 30.0 + i * 12.0, fy - 30.0, 0.05), math.pi / 2, lit=night)
        for i in range(4):
            angle = i * math.tau / 4
            landmarks.drone(ctx, f"drone{i}", (fx + 20.0 * math.cos(angle), fy + 16.0 * math.sin(angle), 26.0 + 4.0 * i), path=[(fx + 20.0 * math.cos(angle), fy + 16.0 * math.sin(angle), 26.0 + 4.0 * i), (fx + 20.0 * math.cos(angle + 1.6), fy + 16.0 * math.sin(angle + 1.6), 30.0 + 3.0 * i)], start=0.0, end=ctx.duration, speed=6.0)
    if spec.get("rubbish", False):
        for i in range(16):
            landmarks.rubbish_pile(ctx, f"rubbish{i}", (fx + rng.uniform(-60, 60), fy + rng.uniform(-50, 50), 0.18), rng.uniform(0.6, 1.1))
    # birds
    level = int(spec.get("birds", 0))
    roofs = sorted(((p.x - fx) ** 2 + (p.y - fy) ** 2, name, p) for name, p in ctx.anchors.items() if name.endswith(".roof") and 15 < p.z < 320)
    if level >= 1:
        for i in range(3 if level < 3 else 5):
            radius = 45.0 + 25.0 * i
            z = 40.0 + 30.0 * i
            loop = [(fx + radius * math.cos(a), fy + radius * math.sin(a), z + 8.0 * math.sin(2 * a)) for a in [math.tau * k / 8 + i for k in range(9)]]
            birds.flock(ctx, f"flock{i}", 26 if level >= 2 else 18, loop[0], (24.0, 24.0, 10.0), path=loop, start=0.0, end=ctx.duration + 2.0, scale=1.1)
    if level >= 2:
        for i in range(3):
            birds.swarm(ctx, f"swarm{i}", 2200, (fx + rng.uniform(-150, 150), fy + rng.uniform(-150, 150), 150.0 + i * 50.0), (260.0, 260.0, 60.0), path=[(fx - 300.0 + i * 80.0, fy + 200.0 - i * 150.0, 150.0 + i * 50.0), (fx + 300.0 - i * 80.0, fy - 200.0 + i * 150.0, 140.0 + i * 50.0)], start=0.0, end=ctx.duration + 2.0, size=1.4)
        for _, name, roof in roofs[:14]:
            birds.roost_area(ctx, f"roost.{name}", (roof.x, roof.y), (18.0, 14.0), 26 if level == 2 else 44, roof.z + 0.7, 1.1)
    if level >= 3 or spec.get("roost", False):
        birds.roost_area(ctx, "roost.plaza", (fx, fy), (60.0, 44.0), 120, 0.3, 1.1)
    statue_focus = str(spec.get("focus")) == "statue"
    if statue_focus and level >= 1:
        crown = ctx.anchors["statue.crown"]
        base = ctx.anchors["statue.base"]
        birds.roost_area(ctx, "roost.statue_base", (base.x, base.y), (40.0, 40.0), 90, base.z, 1.0)
        birds.roost_area(ctx, "roost.pedestal", (base.x, base.y), (26.0, 26.0), 40, 44.0, 1.0)
        for i in range(2):
            loop = [(crown.x + 40.0 * math.cos(a), crown.y + 40.0 * math.sin(a), crown.z - 20.0 + 12.0 * math.sin(3 * a) + i * 15.0) for a in [math.tau * k / 8 for k in range(9)]]
            birds.flock(ctx, f"statue_flock{i}", 40, loop[0], (18.0, 18.0, 10.0), path=loop, start=0.0, end=ctx.duration + 2.0, scale=1.1)
    coverage = float(spec.get("splats", 0.0))
    if coverage > 0:
        for _, name, roof in roofs[:18]:
            birds.splat_area(ctx, f"splat.{name}", (roof.x, roof.y), (22.0, 18.0), int(70 * coverage), roof.z + 0.72, 0.9)
        birds.splat_area(ctx, "splat.streets", (fx, fy), (170.0, 150.0), int(900 * coverage), 0.2, 0.9)
        birds.splat_area(ctx, "splat.plaza", (fx, fy), (64.0, 48.0), int(300 * coverage), 0.2, 1.0)
    if spec.get("nests", False):
        for i in range(60):
            birds.nest(ctx, f"nest{i}", (rng.uniform(-100, 100), 650.0 + rng.uniform(-200, 200), 0.42), rng.randint(2, 4), bird=i % 3 != 0)
        for i in range(24):
            birds.nest(ctx, f"nest_close{i}", (-44.0 + rng.uniform(-14, 14), 596.0 + rng.uniform(-9, 9), 0.42), rng.randint(2, 4), bird=i % 4 != 0)
        birds.roost_area(ctx, "roost.park", (0.0, 650.0), (200.0, 420.0), 260, 0.45, 1.1)
    altitude = float(spec.get("heli_alt", 205.0))  # above every midtown roof (max 190 m)
    for i in range(int(spec.get("helicopters", 0))):
        # path runs west of the spire tower at x = 0
        start = (fx - 200.0 - i * 60.0, fy - 140.0, altitude + i * 12.0)
        heli = vehicles.helicopter(ctx, f"heli{i}", start, 0.0, searchlight=night, lit=True)
        vehicles.drive(ctx, heli, [start, (fx - 40.0 - i * 60.0, fy + 160.0, altitude - 4.0 + i * 12.0)], 0.0, ctx.duration, z=altitude)
    for i in range(int(spec.get("people", 0))):
        px, py = fx + rng.uniform(-28, 28), fy + rng.uniform(-20, 20)
        qx, qy = fx + rng.uniform(-28, 28), fy + rng.uniform(-20, 20)
        actor = characters.build(ctx, {"id": f"pedestrian{i}", "role": rng.choice(("civilian", "shopper", "civilian", "child")), "at": (px, py, 0.18)})
        characters.animate(ctx, actor, {"action": "walk", "path": [[px, py], [qx, qy]], "start": rng.uniform(0.0, 1.5)})
    ctx.anchor("times_square", (0.0, 70.0, 2.0))
    ctx.anchor("midtown", (0.0, 150.0, 80.0))
    ctx.anchor("park", (0.0, 650.0, 2.0))
    ctx.anchor("park_lake", (0.0, 640.0, 1.0))
    ctx.anchor("downtown", (-50.0, -500.0, 90.0))
    ctx.anchor("harbour", (-200.0, -860.0, 2.0))
    ctx.anchor("hudson", (-330.0, 0.0, 0.0))
    ctx.anchor("pier", (-290.0, 50.0, 1.0))
    ctx.anchor("brooklyn_shore", (330.0, -350.0, 1.0))
    ctx.anchor("focus", (fx, fy, 2.0))
    return None


def airport(ctx, spec):
    """Two runways, taxiways, an apron with parked airliners, terminal and tower. Flags: birds (0-3), night."""
    night = bool(spec.get("night", False))
    terrain.ground(ctx, "ground", (2600, 2200), (26, 22), amplitude=0.0, seed=1, material=ctx.mat("grass_dry"))
    for i, y in enumerate((-150.0, 150.0)):
        props.road(ctx, f"runway{i}", (-700.0, y), (700.0, y), 45.0, 0.02)
        for k in range(8):
            box(ctx, f"threshold{i}{k}", (24.0, 1.6, 0.02), (-660.0 + k * 4.5, y - 14.0 + (k % 2) * 28.0, 0.03), ctx.mat("road_line"), anchor="base")
    for x in (-600.0, 0.0, 600.0):
        props.road(ctx, f"taxiway{x}", (x, -150.0), (x, 330.0), 20.0, 0.02, lines=False)
    props.road(ctx, "taxiway_main", (-700.0, 0.0), (700.0, 0.0), 20.0, 0.02, lines=False)
    box(ctx, "apron", (760.0, 200.0, 0.08), (0.0, 330.0, 0.0), ctx.mat("asphalt"), anchor="base")
    buildings.building(ctx, "terminal", (0.0, 450.0, 0.0), (340.0, 56.0, 18.0), "plaster", "flat", 0.0, 77, window=(2.4, 2.4), floor_height=4.5, trim="teal", units=True)
    for i, x in enumerate((-180.0, 180.0)):
        buildings.building(ctx, f"pier{i}", (x, 380.0, 0.0), (26.0, 120.0, 9.0), "plaster", "flat", 0.0, 78 + i, window=(1.8, 1.8), door=False, units=False)
    cylinder(ctx, "tower", 6.0, 60.0, (-280.0, 450.0, 0.0), ctx.mat("concrete"), segments=12, anchor="base", radius2=4.5)
    box(ctx, "tower.cab", (18.0, 18.0, 8.0), (-280.0, 450.0, 60.0), ctx.palette.glass("tower glass"), bevel=0.3, anchor="base")
    for i in range(2):
        buildings.warehouse(ctx, f"hangar{i}", (520.0 + i * 160.0, 440.0, 0.0), (120.0, 90.0, 26.0), 0.0, "steel")
    for i, x in enumerate(range(-210, 211, 60)):
        landmarks.airliner(ctx, f"gate{i}", (float(x), 318.0, 0.0), 0.0, "white")
    landmarks.airliner(ctx, "taxiing_a", (-480.0, -150.0, 0.0), math.pi / 2, "white", "red")
    landmarks.airliner(ctx, "taxiing_b", (330.0, 150.0, 0.0), -math.pi / 2, "white", "navy")
    landmarks.airliner(ctx, "holding", (600.0, 60.0, 0.0), 0.0, "white", "teal")
    for i in range(3):
        vehicles.lorry(ctx, f"fuel{i}", (-60.0 + i * 70.0, 270.0, 0.08), math.pi / 2, "white", "tanker", lit=night)
    for i, x in enumerate(range(-600, 601, 150)):
        props.lamp_post(ctx, f"lamp{i}", (float(x), 240.0, 0.08), 14.0, 0.0, night)
    level = int(spec.get("birds", 0))
    if level >= 1:
        birds.roost_area(ctx, "roost.runway_a", (0.0, -150.0), (1300.0, 40.0), 420 * min(level, 3), 0.05, 1.3)
        birds.roost_area(ctx, "roost.apron", (0.0, 300.0), (600.0, 80.0), 160 * min(level, 3), 0.1, 1.3)
        for i in range(3):
            loop = [(-200.0 + 200.0 * math.cos(a) + i * 150.0, 60.0 + 160.0 * math.sin(a), 45.0 + 15.0 * i + 10.0 * math.sin(2 * a)) for a in [math.tau * k / 8 + i for k in range(9)]]
            birds.flock(ctx, f"flock{i}", 36, loop[0], (30.0, 30.0, 12.0), path=loop, start=0.0, end=ctx.duration + 2.0, scale=1.2)
    if level >= 2:
        for i in range(3):
            birds.swarm(ctx, f"swarm{i}", 2400, (-300.0 + i * 300.0, 100.0, 120.0 + i * 40.0), (400.0, 300.0, 60.0), path=[(-300.0 + i * 300.0, 100.0, 120.0 + i * 40.0), (-100.0 + i * 300.0, -100.0, 110.0 + i * 40.0)], start=0.0, end=ctx.duration + 2.0, size=1.4)
    if float(spec.get("splats", 0.0)) > 0:
        birds.splat_area(ctx, "splat.apron", (0.0, 320.0), (700.0, 180.0), int(900 * float(spec["splats"])), 0.12, 1.6)
        birds.splat_area(ctx, "splat.runway", (0.0, -150.0), (1300.0, 44.0), int(700 * float(spec["splats"])), 0.05, 1.6)
    ctx.anchor("runway", (0.0, -150.0, 1.0))
    ctx.anchor("runway_end", (-650.0, -150.0, 1.0))
    ctx.anchor("terminal", (0.0, 450.0, 10.0))
    ctx.anchor("tower", (-280.0, 450.0, 66.0))
    ctx.anchor("apron", (0.0, 320.0, 3.0))
    ctx.anchor("gates", (0.0, 330.0, 6.0))
    ctx.anchor("holding", (600.0, 60.0, 5.0))
    return None


BUILDERS = {"harbour_dawn": harbour_dawn, "metropolis": metropolis, "airport": airport}
FOG_EXTENT = {"harbour_dawn": (3000, 3000, 300), "metropolis": (2400, 3200, 420), "airport": (2600, 2200, 260)}
