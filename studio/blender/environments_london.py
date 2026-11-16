"""London environments for "365 Days Underwater": recognisable London slowly becoming unliveable,
never a drowned city. Streets, a park, Westminster and the Thames, aerials under a trapped weather
system, flats with black mould, a shelter, a stalled building site, a substation and a hospital.

Coordinates are metres. Street builders run along Y; UK traffic keeps left (northbound x < 0)."""

from __future__ import annotations

import math

import bpy
from mathutils import Vector

from studio.assets import buildings, characters, landmarks, london, props, vegetation, vehicles, weather
from studio.assets.meshes import merged_boxes
from studio.blender.primitives import add_noise, box, cylinder, fcurves, ico, key, mesh_from_pydata, multi_box, parent, set_interp

CAR_COLOURS = ("white", "navy", "black", "stone", "red", "dark_steel", "teal")


# ----- shared pieces -------------------------------------------------------------------------------
def _window_lights(ctx, night, strength=2.2):
    """Lit-window material for night scenes, tagged so a blackout event can switch it off."""
    if not night:
        return None
    material = ctx.palette.make("london windows lit", (1.0, 0.78, 0.48), 0.5, 0.0, strength)
    ctx.tag("window_lights", material)
    return material


def _rain(ctx, spec, default_at=(0.0, 0.0), extent=(34.0, 34.0, 20.0), count=4200):
    """Streak rain around spec['rain_at'] (set it to the camera's x, y). spec['rain'] False = dry."""
    if not spec.get("rain", True):
        return None
    at = spec.get("rain_at") or default_at
    night = bool(spec.get("night"))
    strength = float(spec.get("rain_strength", 0.7 if night else 0.45))
    heavy = float(spec.get("rain_heavy", 1.0))
    z = float(at[2]) if len(at) > 2 else 0.0
    return weather.rain(ctx, "rain", (float(at[0]), float(at[1]), z), extent, int(count * heavy), speed=11.0, strength=strength)


def _flood_plane(ctx, name, size, centre, depth, colour="flood_brown", tag="flood"):
    material = weather.murky(ctx, f"{name} water", colour)
    obj = box(ctx, name, (size[0], size[1], 0.04), (centre[0], centre[1], depth), material)
    obj.visible_shadow = False
    ctx.tag(tag, obj)
    return obj


def _drains(ctx, name, points, night=False):
    """Overflowing gully drains: water boils up through the grate, spits droplets, spreads into a
    wide pool and runs along the gutter."""
    rng = ctx.rng
    water = weather.murky(ctx, f"{name} water", "flood_brown", roughness=0.12, bump=0.5, scale=4.0)
    objs = []
    for i, (x, y) in enumerate(points):
        side = 1.0 if x > 0 else -1.0
        box(ctx, f"{name}{i}.grate", (0.5, 0.8, 0.02), (x, y, 0.004), ctx.mat("black"))
        dome = ico(ctx, f"{name}{i}", 0.55, (x, y, 0.02), water, subdiv=2, scale=(1.0, 1.4, 0.35), smooth=True)
        add_noise(dome, "scale", 0.25, 1, ctx.frames, scale=2.0, phase=i * 1.7)
        for k in range(7):
            drop = ico(ctx, f"{name}{i}.spit{k}", rng.uniform(0.04, 0.08), (x, y, 0.05), water, subdiv=1)
            dx, dy = rng.uniform(-0.35, 0.35), rng.uniform(-0.5, 0.5)
            period = rng.randint(9, 16)
            phase = rng.randint(0, period)
            key(drop, "location", 1 - phase, (x, y, 0.05))
            key(drop, "location", 1 - phase + period // 2, (x + dx / 2, y + dy / 2, rng.uniform(0.25, 0.6)))
            key(drop, "location", 1 - phase + period, (x + dx, y + dy, 0.03))
            for curve in fcurves(drop, "location"):
                curve.modifiers.new("CYCLES")
        pool = mesh_from_pydata(ctx, f"{name}{i}.pool", [(x + 2.4 * math.cos(a) * (0.6 + 0.4 * math.sin(3 * a + i)) - side * 0.6, y + 3.2 * math.sin(a), 0.012) for a in [k * math.tau / 14 for k in range(14)]], [tuple(range(14))], [water])
        pool.visible_shadow = False
        stream = box(ctx, f"{name}{i}.gutter", (0.55, 16.0, 0.03), (x, y - 8.0, 0.015), water)
        stream.visible_shadow = False
        objs.append(dome)
    return objs


def _rows(ctx, prefix, side, x_front, y_from, y_to, kind, gaps, seed, lit, spec):
    """Terrace rows on one side of a street between y_from and y_to, skipping `gaps` [(y0, y1)].
    side -1 = west (fronts face +X), +1 = east (fronts face -X)."""
    segments = []
    cursor = y_from
    for g0, g1 in sorted(gaps):
        if g0 > cursor:
            segments.append((cursor, g0))
        cursor = max(cursor, g1)
    if y_to > cursor:
        segments.append((cursor, y_to))
    results = []
    for i, (a, b) in enumerate(segments):
        length = b - a
        if length < 6.0:
            continue
        count = max(1, int(length / (5.8 if kind != "mansion" else 16.0)))
        if side < 0:
            origin, rot = (x_front, a, 0.0), math.pi / 2
        else:
            origin, rot = (x_front, b, 0.0), -math.pi / 2
        results.append(london.terrace(ctx, f"{prefix}{i}", origin, count, rot, seed=seed + i * 13, kind=kind, lit=lit, boarded=float(spec.get("boarded", 0.0)), shutters=float(spec.get("shutters", 0.0)), to_let=float(spec.get("to_let", 0.0)), damp=float(spec.get("damp", 0.0))))
    return results


def _traffic(ctx, spec, length, night, lanes=(-2.6, 2.6)):
    rng = ctx.rng
    if spec.get("traffic_lane") == "north":
        lanes = (lanes[0], lanes[0])
    span = length / 2 - 10
    placed = [tuple(p) for p in spec.get("bus_at") or []]
    for i in range(max(int(spec.get("buses", 1)), len(placed))):
        lane = placed[i][0] if i < len(placed) else lanes[i % 2]
        heading = 0.0 if lane < 0 else math.pi
        y = placed[i][1] if i < len(placed) else rng.uniform(-span * 0.6, span * 0.4) * (1 if lane < 0 else -1)
        dest = "DIVERTED" if spec.get("diverted") else rng.choice(("OXFORD CIRCUS", "VICTORIA", "ALDWYCH", "ELEPHANT & CASTLE", "WATERLOO"))
        bus = london.double_decker(ctx, f"bus{i}", (lane, y, 0.0), heading, lit=night, route=rng.choice(("25", "38", "73", "159", "12")), destination=dest)
        speed = float(spec.get("traffic_speed", 5.0))
        end_y = y + (speed * (ctx.duration + 1.0)) * (1 if lane < 0 else -1)
        vehicles.drive(ctx, bus, [(lane, y), (lane, end_y)], 0.0, ctx.duration + 1.0, speed=speed)
    for i in range(int(spec.get("traffic", 6))):
        lane = lanes[i % 2]
        heading = 0.0 if lane < 0 else math.pi
        y = rng.uniform(-span, span)
        if rng.random() < 0.45:
            car = london.black_cab(ctx, f"cab{i}", (lane, y, 0.0), heading, lit=night)
        else:
            car = vehicles.car(ctx, f"car{i}", (lane, y, 0.0), heading, rng.choice(CAR_COLOURS), lit=night)
        speed = float(spec.get("traffic_speed", 5.0)) * rng.uniform(0.8, 1.2)
        end_y = y + speed * (ctx.duration + 1.0) * (1 if lane < 0 else -1)
        vehicles.drive(ctx, car, [(lane, y), (lane, end_y)], 0.0, ctx.duration + 1.0, speed=speed)


# ----- street ---------------------------------------------------------------------------------------
def london_street(ctx, spec):
    """A London street in the rain. Flags: kind (high_street | residential | mixed), night, rain,
    rain_at, wet, puddles, flood (surface-water depth), lightwells (flooding basements), drains,
    buses, traffic, diverted, parked, walkers, umbrellas, sandbags, pumps, shutters, boarded,
    to_let, damp, tape, evacuation, road_closed, scaffolding, sinkhole, debris, viaduct (railway
    bridge at viaduct_y with a train and underpass flood), station (Underground front at
    station_y), station_closed."""
    rng = ctx.rng
    night = bool(spec.get("night"))
    wet = bool(spec.get("wet", True))
    kind = str(spec.get("kind", "high_street"))
    length = float(spec.get("length", 240.0))
    lit = _window_lights(ctx, night)
    left_kind, right_kind = {"high_street": ("shops", "shops"), "residential": ("residential", "residential"), "mixed": ("shops", "residential")}[kind]
    pav = {"shops": 4.0, "residential": 2.4, "mansion": 4.0}
    london.kerb_and_road(ctx, "street", length, 10.0, (pav[left_kind], pav[right_kind]), wet=wet, bus_lane=kind != "residential")
    box(ctx, "ground", (600.0, 600.0, 0.1), (0.0, 0.0, -1.42), ctx.mat("stone"), anchor="base")
    gaps_left, gaps_right = [], []
    vy = float(spec.get("viaduct_y", 30.0))
    sy = float(spec.get("station_y", -20.0))
    if spec.get("viaduct"):
        gaps_left.append((vy - 7.0, vy + 7.0))
        gaps_right.append((vy - 7.0, vy + 7.0))
    if spec.get("station"):
        gaps_right.append((sy - 7.0, sy + 7.0))
    junction = float(spec.get("junction_y", 70.0))
    gaps_left.append((junction - 6.0, junction + 6.0))
    gaps_right.append((junction - 6.0, junction + 6.0))
    rows = _rows(ctx, "west", -1, -9.0, -length / 2 + 4, length / 2 - 4, left_kind, gaps_left, 3, lit, spec)
    rows += _rows(ctx, "east", 1, 9.0, -length / 2 + 4, length / 2 - 4, right_kind, gaps_right, 41, lit, spec)
    # side street at the junction
    london.kerb_and_road(ctx, "side_street", 120.0, 8.0, (3.0, 3.0), wet=wet, bus_lane=False, centre=(-70.0, junction), rot=math.pi / 2)
    london.terrace(ctx, "side_south", (-12.0, junction - 9.0, 0.0), 19, math.pi, seed=69, kind="residential", lit=lit)
    london.terrace(ctx, "side_north", (-130.0, junction + 9.0, 0.0), 19, 0.0, seed=71, kind="residential", lit=lit)
    wells = [w for r in rows for w in r["wells"]]
    doors = [d for r in rows for d in r["doors"]]
    if spec.get("lightwells"):
        london.lightwell_water(ctx, "lightwell", wells, level=float(spec.get("lightwell_level", -1.25)))
    # street furniture
    for i, y in enumerate(range(int(-length / 2 + 15), int(length / 2 - 10), 28)):
        for side in (-1, 1):
            props.lamp_post(ctx, f"lamp{i}{side}", (side * 5.35, float(y) + (8.0 if side > 0 else 0.0), 0.16), 7.5, side * math.pi / 2, lit=night)
    london.phone_box(ctx, "phone_box", (-7.6, -8.0, 0.16), 0.0, lit=night)
    london.pillar_box(ctx, "pillar_box", (-6.2, -12.5, 0.16))
    london.bus_stop(ctx, "bus_stop", (7.2, 12.0, 0.16), math.pi / 2)
    if kind == "residential":
        for i, y in enumerate(range(int(-length / 2 + 20), int(length / 2 - 20), 22)):
            vegetation.tree(ctx, f"plane{i}", (rng.choice((-5.9, 5.9)), float(y), 0.16), "round", 1.25)
        for i in range(int(spec.get("parked", 14))):
            side = rng.choice((-1, 1))
            vehicles.car(ctx, f"parked{i}", (side * 3.9, rng.uniform(-length / 2 + 10, length / 2 - 10), 0.0), 0.0 if side < 0 else math.pi, rng.choice(CAR_COLOURS), lit=False)
    _traffic(ctx, spec, length, night, lanes=(-2.6, 2.6) if kind != "residential" else (-1.6, 1.6))
    # people
    lanes = [(-5.0 - pav[left_kind] / 2, 1), (-5.0 - pav[left_kind] / 2, -1), (5.0 + pav[right_kind] / 2, 1), (5.0 + pav[right_kind] / 2, -1)]
    if int(spec.get("walkers", 0)):
        london.walkers(ctx, "walker", lanes, int(spec.get("walkers", 0)), float(spec.get("walkers_span", 70.0)), umbrellas=float(spec.get("umbrellas", 0.85)), centre=float(spec.get("walkers_y", 0.0)), run=float(spec.get("run", 0.0)), clear=spec.get("walkers_clear"))
    # water
    if wet and int(spec.get("puddles", 50)):
        n = int(spec.get("puddles", 50))
        weather.puddles(ctx, "puddles", (-4.8, -length / 2, 4.8, length / 2), n, size=(0.8, 3.6), z=0.012)
        edge_l, edge_r = 5.0 + pav[left_kind] - 0.2, 5.0 + pav[right_kind] - 0.2
        weather.puddles(ctx, "pavement_pools", (-edge_l, -length / 2, edge_r, length / 2), n // 2, size=(0.6, 2.0), z=0.172, avoid=[(-5.2, -length, 5.2, length)])
    if float(spec.get("flood", 0.0)) > 0:
        _flood_plane(ctx, "surface_water", (18.0, length), (0.0, float(spec.get("flood_y", 0.0))), float(spec["flood"]))
    if spec.get("drains"):
        _drains(ctx, "drain", [(-4.75, y) for y in (-24.0, -6.0, 12.0)] + [(4.75, y) for y in (-15.0, 4.0)], night)
    if spec.get("sandbags"):
        london.sandbags(ctx, "sandbags", doors[: int(spec.get("sandbag_doors", 40))], rows=3, width=1.7, facing=math.pi / 2)
    for i in range(int(spec.get("pumps", 0))):
        if doors:
            dx, dy = doors[(i * 7) % len(doors)]
            london.pump(ctx, f"pump{i}", (dx + (0.8 if dx < 0 else -0.8), dy + 1.5, 0.16), (math.copysign(5.0, dx), dy + 3.0))
    if spec.get("road_closed"):
        rc = float(spec.get("road_closed_y", 25.0))
        for k, x in enumerate((-3.0, 0.0, 3.0)):
            london.road_closed(ctx, f"closed{k}", (x, rc, 0.0), 0.0, "ROAD CLOSED" if k != 1 else "FLOODING")
    if spec.get("tape") and doors:
        pts = [(d[0] + (0.5 if d[0] < 0 else -0.5), d[1]) for d in doors[:12]]
        london.police_tape(ctx, "tape", sorted(pts, key=lambda p: p[1]))
    if spec.get("evacuation"):
        for k, y in enumerate((-12.0, 18.0)):
            sign = london.road_closed(ctx, f"evac{k}", (0.0 + (k - 0.5) * 3.0, y, 0.0), 0.0, "EVACUATION ZONE")
            sign.scale = (1.3, 1.0, 1.0)
    for i in range(int(spec.get("scaffolding", 0))):
        side = int(spec.get("scaffold_side", -1))
        y = float(spec.get("scaffold_y", 0.0)) + i * 12.5 * (1 if side < 0 else -1)
        london.scaffolding(ctx, f"scaffold{i}", (side * 9.0, y, 0.16), 11.5, 12.5, math.pi / 2 if side < 0 else -math.pi / 2)
    if spec.get("sinkhole"):
        sh = float(spec.get("sinkhole_y", -6.0))
        size = float(spec.get("sinkhole_size", 1.0))
        hole = mesh_from_pydata(ctx, "sinkhole", [(math.cos(a) * 2.6 * size * (0.85 + 0.15 * math.sin(3 * a)), sh + math.sin(a) * 1.8 * size, 0.01) for a in [k * math.tau / 12 for k in range(12)]], [tuple(range(12))], [ctx.mat("black", roughness=1.0)])
        hole.visible_shadow = False
        for k in range(8):
            a = k * math.tau / 8
            box(ctx, f"sinkhole.slab{k}", (rng.uniform(0.6, 1.2), rng.uniform(0.4, 0.9), 0.12), (math.cos(a) * 2.9, sh + math.sin(a) * 2.1, 0.02), ctx.mat("tarmac_wet", roughness=0.3), rot=(rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), rng.uniform(0, 3)))
        for k in range(6):
            a = k * math.tau / 6
            props.barrier(ctx, f"sinkhole.barrier{k}", (math.cos(a) * 4.2, sh + math.sin(a) * 3.2, 0.0), a + math.pi / 2)
    if spec.get("debris"):
        for i in range(10):
            landmarks.rubbish_pile(ctx, f"debris{i}", (rng.choice((-6.5, 6.5)) + rng.uniform(-1, 1), rng.uniform(-60, 60), 0.16), rng.uniform(0.7, 1.2))
        weather.puddles(ctx, "silt", (-4.8, -80.0, 4.8, 80.0), 24, size=(2.0, 6.0), z=0.01, material=ctx.mat("silt", roughness=0.9))
        weather.puddles(ctx, "silt_pavement", (-7.2, -80.0, 7.2, 80.0), 16, size=(1.0, 3.0), z=0.168, material=ctx.mat("silt", roughness=0.9), avoid=[(-5.2, -100, 5.2, 100)])
    if spec.get("viaduct"):
        london.viaduct(ctx, "viaduct", (-80.0, vy), (80.0, vy), height=7.0)
        if spec.get("train", True):
            london.train(ctx, "train", [(-140.0, vy - 2.2), (140.0, vy - 2.2)], cars=6, start=float(spec.get("train_start", 0.0)), speed=12.0, z=8.3, lit=True)
        if float(spec.get("underpass", 0.0)) > 0:
            _flood_plane(ctx, "underpass_water", (18.0, 30.0), (0.0, vy), float(spec["underpass"]), tag="underpass")
        if spec.get("stuck_car"):
            vehicles.car(ctx, "stuck_car", (-1.6, vy - 5.0, 0.0), 0.25, "red", lit=night)
    if spec.get("station"):
        london.station_front(ctx, "station", (9.0, sy, 0.0), -math.pi / 2, closed=bool(spec.get("station_closed", True)), lit=night)
        if spec.get("station_water"):
            _flood_plane(ctx, "station_water", (4.0, 11.0), (7.0, sy), 0.2, tag="station_water")
    _rain(ctx, spec)
    ctx.anchor("street", (0.0, 0.0, 1.6))
    ctx.anchor("viaduct", (0.0, vy, 4.0))
    ctx.anchor("station", (9.0, sy, 2.5))
    return None


def london_park(ctx, spec):
    """A waterlogged London square or park: sodden grass, spreading puddles, plane trees, railings,
    benches and terraces around it. Flags: rain, rain_at, night, walkers, flood (standing water)."""
    rng = ctx.rng
    night = bool(spec.get("night"))
    lit = _window_lights(ctx, night)
    box(ctx, "lawn", (120.0, 90.0, 0.2), (0.0, 0.0, -0.2), ctx.mat("park_grass", roughness=0.55), anchor="base")
    box(ctx, "square_paving", (200.0, 180.0, 0.1), (0.0, 0.0, -0.12), ctx.mat("pavement_wet", roughness=0.3), anchor="base")
    box(ctx, "ground", (600.0, 600.0, 0.1), (0.0, 0.0, -1.42), ctx.mat("stone"), anchor="base")
    for k, (a, b) in enumerate((((-60, -2), (60, -2)), ((-2, -45), (-2, 45)))):
        props.road(ctx, f"path{k}", a, b, 3.2, 0.01, lines=False)
    weather.puddles(ctx, "standing_water", (-58.0, -43.0, 58.0, 43.0), int(spec.get("puddles", 70)), size=(2.0, 9.0), z=0.02)
    if float(spec.get("flood", 0.0)) > 0:
        _flood_plane(ctx, "pond", (40.0, 30.0), (16.0, -12.0), float(spec["flood"]), colour="puddle")
    vegetation.scatter_trees(ctx, "trees", (0.0, 0.0, 0.0), 55.0, 26, ("round", "round", "conifer"), avoid=[(-6, -46, 4, 46), (-60, -6, 60, 4)])
    for i in range(8):
        props.bench(ctx, f"bench{i}", (rng.choice((-3.5, 3.5)), -40.0 + i * 11.0, 0.0), math.pi / 2)
    fence_mat = ctx.mat("black", roughness=0.5)
    rail = []
    for x in range(-60, 61, 1):
        for y in (-45.5, 45.5):
            rail.append(((float(x), y, 0.6), (0.04, 0.04, 1.2), 0))
    for y in range(-45, 46, 1):
        for x in (-60.5, 60.5):
            rail.append(((x, float(y), 0.6), (0.04, 0.04, 1.2), 0))
    merged_boxes(ctx, "railings", rail, [fence_mat])
    london.kerb_and_road(ctx, "square_road_n", 140.0, 8.0, (3.0, 3.0), wet=True, bus_lane=False, centre=(0.0, 52.0), rot=math.pi / 2)
    london.terrace(ctx, "north_row", (-70.0, 61.0, 0.0), 24, 0.0, seed=5, kind="residential", lit=lit)
    london.terrace(ctx, "east_row", (68.0, 50.0, 0.0), 18, -math.pi / 2, seed=9, kind="residential", lit=lit)
    london.terrace(ctx, "west_row", (-68.0, -48.0, 0.0), 6, math.pi / 2, seed=17, kind="mansion", lit=lit)
    if int(spec.get("walkers", 0)):
        london.walkers(ctx, "park_walker", [(-1.0, 1), (1.0, -1)], int(spec["walkers"]), 60.0, umbrellas=0.9)
    _rain(ctx, spec)
    ctx.anchor("park", (0.0, 0.0, 1.0))
    return None


# ----- the river city: aerials and Westminster ------------------------------------------------------
RIVER = [(-1800, -3200), (-500, -2000), (30, -1100), (30, 200), (250, 900), (900, 1300), (1800, 1350), (2700, 1100), (3600, 1200), (4600, 1600)]
RIVER_WIDTH = 260.0
TOWER = (-122.0, -280.0)  # Elizabeth Tower, north end of the palace on the west bank
CITY = (1900.0, 1850.0)


def _smooth(points, steps=6):
    """Catmull-Rom curve through points (x, y)."""
    pts = [points[0], *points, points[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for k in range(steps):
            t = k / steps
            out.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t * t * t) for j in range(2)))
    out.append(points[-1])
    return out


def _river_distance(path, x, y):
    best = 1e9
    for (ax, ay), (bx, by) in zip(path, path[1:], strict=False):
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)))
        best = min(best, math.hypot(x - ax - t * dx, y - ay - t * dy))
    return best


def _ribbon(ctx, name, path, width, z, material, offset=0.0, height=None):
    """A flat strip along path (or a vertical wall when height is given), shifted sideways by offset."""
    verts, faces = [], []
    for i, (x, y) in enumerate(path):
        a, b = path[max(0, i - 1)], path[min(len(path) - 1, i + 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        n = math.hypot(tx, ty) or 1.0
        nx, ny = -ty / n, tx / n
        cx, cy = x + nx * offset, y + ny * offset
        if height is None:
            verts += [(cx - nx * width / 2, cy - ny * width / 2, z), (cx + nx * width / 2, cy + ny * width / 2, z)]
        else:
            verts += [(cx, cy, z), (cx, cy, z + height)]
        if i:
            base = 2 * (i - 1)
            faces.append((base, base + 2, base + 3, base + 1))
    return mesh_from_pydata(ctx, name, verts, faces, [material])


def _river(ctx, spec, path):
    level = float(spec.get("river_level", -3.5))
    water = weather.murky(ctx, "thames water", "thames", roughness=0.16, bump=0.25, scale=0.05, specular=0.35)
    river = _ribbon(ctx, "thames", path, RIVER_WIDTH, level, water)
    ctx.tag("river", river)
    _ribbon(ctx, "riverbed", path, RIVER_WIDTH + 30, -8.0, ctx.mat("mud", roughness=1.0))
    stone = ctx.mat("portland_stone", roughness=0.85)
    for side in (-1, 1):
        _ribbon(ctx, f"embankment{side}", path, 0.0, -8.0, stone, offset=side * RIVER_WIDTH / 2, height=8.6)
    return river


def _city_blocks(ctx, spec, path, night, exclude, area, cell=95.0, districts=8, focus=TOWER):
    """Thousands of generic London buildings merged into one mesh per district (tag district_k).
    Terraces and mansion blocks everywhere, towers in the City; lit windows and street lights at night."""
    rng = ctx.rng
    x0, y0, x1, y1 = area
    walls = [ctx.mat(c, roughness=0.9) for c in ("london_brick", "red_brick", "stucco", "portland_stone", "concrete")]
    roof, glass = ctx.mat("slate", roughness=0.7), ctx.mat("shard_glass", roughness=0.15, metallic=0.4)
    buckets = [[] for _ in range(districts)]
    lights = [[] for _ in range(districts)]
    dark = float(spec.get("dark_districts", 0.0))
    nx_, ny_ = int((x1 - x0) / cell), int((y1 - y0) / cell)
    for gx in range(nx_):
        for gy in range(ny_):
            cx = x0 + (gx + 0.5) * cell + rng.uniform(-8, 8)
            cy = y0 + (gy + 0.5) * cell + rng.uniform(-8, 8)
            if _river_distance(path, cx, cy) < RIVER_WIDTH / 2 + 45:
                continue
            if any(a <= cx <= c and b <= cy <= d for a, b, c, d in exclude):
                continue
            k = int((math.atan2(cy - focus[1], cx - focus[0]) + math.pi) / math.tau * districts) % districts
            city = math.hypot(cx - CITY[0], cy - CITY[1]) < 650
            for _ in range(rng.choice((2, 3, 3, 4))):
                bx, by = cx + rng.uniform(-cell * 0.3, cell * 0.3), cy + rng.uniform(-cell * 0.3, cell * 0.3)
                long_x = rng.random() < 0.5
                if city and rng.random() < 0.45:
                    w, d, h = rng.uniform(25, 45), rng.uniform(25, 45), rng.uniform(60, 230)
                    buckets[k].append(((bx, by, h / 2), (w, d, h), 6))
                elif rng.random() < 0.2:
                    w, d, h = rng.uniform(20, 40), rng.uniform(16, 30), rng.uniform(18, 34)
                    buckets[k].append(((bx, by, h / 2), (w, d, h), rng.choice((1, 3, 4))))
                    buckets[k].append(((bx, by, h + 0.6), (w + 0.4, d + 0.4, 1.2), 5))
                else:
                    w, d, h = (rng.uniform(40, 70), 11.0, rng.uniform(10, 15)) if long_x else (11.0, rng.uniform(40, 70), rng.uniform(10, 15))
                    buckets[k].append(((bx, by, h / 2), (w, d, h), rng.choice((0, 0, 0, 1, 1, 2))))
                    buckets[k].append(((bx, by, h + 1.2), (w - 1.0, d - 1.0, 2.4), 5))
                if night:
                    for _ in range(rng.randint(2, 6)):
                        side = rng.choice((-1, 1))
                        hz = rng.uniform(3, min(h - 2, 60))
                        if long_x:
                            lights[k].append(((bx + rng.uniform(-w / 2.5, w / 2.5), by + side * (d / 2 + 0.2), hz), (2.4, 0.3, 1.6), 7))
                        else:
                            lights[k].append(((bx + side * (w / 2 + 0.2), by + rng.uniform(-d / 2.5, d / 2.5), hz), (0.3, 2.4, 1.6), 7))
            if night and rng.random() < 0.7:
                lights[k].append(((cx + cell / 2, cy, 6.0), (2.5, 2.5, 1.0), 7))
                lights[k].append(((cx, cy + cell / 2, 6.0), (2.5, 2.5, 1.0), 7))
    for k in range(districts):
        lit = ctx.palette.make(f"district {k} lights", (1.0, 0.70, 0.40), 0.6, 0.0, 0.0 if rng.random() < dark else 6.0) if night else glass
        if night:
            ctx.tag(f"district_{k}", lit)
            ctx.tag("window_lights", lit)
        mats = [*walls, roof, glass, lit]
        if buckets[k]:
            merged_boxes(ctx, f"district{k}", buckets[k] + lights[k], mats)
    return None


def _landmarks(ctx, spec, night, lit):
    london.palace(ctx, "palace", (-108.0, -560.0, 0.0), 260.0, math.pi / 2, lit=lit)
    london.elizabeth_tower(ctx, "elizabeth_tower", (TOWER[0], TOWER[1], 0.0), 1.0, lit=night or bool(spec.get("clock_lit")))
    london.london_eye(ctx, "eye", (215.0, -40.0, 0.0), math.pi / 2, 60.0, lit=night)
    london.st_pauls(ctx, "st_pauls", (1300.0, 1720.0, 0.0), 0.3)
    london.shard(ctx, "shard", (2150.0, 900.0, 0.0), 310.0, lit=night)
    buildings.building(ctx, "county_hall", (260.0, -190.0, 0.0), (60.0, 110.0, 24.0), "portland_stone", "flat", 0.0, 3, window=(1.6, 2.0), floor_height=4.0, lit=lit)
    buildings.building(ctx, "st_thomas", (250.0, -520.0, 0.0), (50.0, 200.0, 30.0), "concrete", "flat", 0.0, 4, window=(1.6, 1.8), lit=lit)
    for i, y in enumerate((-250.0, -760.0, 190.0)):
        london.bridge(ctx, f"bridge{i}", (-130.0, y), (190.0, y), width=26.0, deck=0.4, arches=7, colour="bridge_green" if i == 0 else "portland_stone")
    box(ctx, "st_james_park", (480.0, 260.0, 0.3), (-560.0, -330.0, 0.0), ctx.mat("park_grass", roughness=0.6), anchor="base")
    box(ctx, "hyde_park", (1100.0, 900.0, 0.3), (-2100.0, 300.0, 0.0), ctx.mat("park_grass", roughness=0.6), anchor="base")
    box(ctx, "parliament_square", (90.0, 70.0, 0.25), (-210.0, -260.0, 0.0), ctx.mat("park_grass", roughness=0.6), anchor="base")


def _thames_city(ctx, spec, detail):
    rng = ctx.rng
    night = bool(spec.get("night"))
    if hasattr(ctx.scene.eevee, "shadow_pool_size"):
        ctx.scene.eevee.shadow_pool_size = "1024"  # thousands of buildings overflow the default pool
    lit = _window_lights(ctx, night, 3.0)
    path = _smooth(RIVER, 8)
    box(ctx, "land", (16000.0, 16000.0, 0.2), (0.0, 0.0, -0.2), ctx.mat("city_ground", roughness=0.9), anchor="base")
    _river(ctx, spec, path)
    _landmarks(ctx, spec, night, lit)
    exclude = [(-260, -620, -60, -150), (-800, -470, -320, -190), (-2650, -150, -1550, 750), (150, -650, 330, -120), (1220, 1640, 1380, 1800), (2080, 830, 2220, 970), (-260, -300, -160, -220)]
    reach = float(spec.get("reach", 1.0))
    _city_blocks(ctx, spec, path, night, exclude, (-3600 * reach, -3400 * reach, 4600 * reach, 3600 * reach), cell=float(spec.get("cell", 80.0)))
    if detail:
        # Westminster Bridge traffic, people and the embankment
        for i in range(int(spec.get("buses", 3))):
            x = -90.0 + i * 85.0
            bus = london.double_decker(ctx, f"bridge_bus{i}", (x, -253.5 if i % 2 else -246.5, 0.4), -math.pi / 2 if i % 2 == 0 else math.pi / 2, lit=night)
            dx = 5.0 * (ctx.duration + 1.0) * (1 if i % 2 == 0 else -1)
            vehicles.drive(ctx, bus, [(x, bus.location.y), (x + dx, bus.location.y)], 0.0, ctx.duration + 1.0, speed=5.0, z=0.4)
        for i in range(int(spec.get("traffic", 6))):
            x = rng.uniform(-100, 160)
            lane = rng.choice((-252.0, -248.0))
            car = london.black_cab(ctx, f"bridge_cab{i}", (x, lane, 0.4), -math.pi / 2 if lane > -250 else math.pi / 2, lit=night)
            dx = 6.0 * (ctx.duration + 1.0) * (1 if lane > -250 else -1)
            vehicles.drive(ctx, car, [(x, lane), (x + dx, lane)], 0.0, ctx.duration + 1.0, speed=6.0, z=0.4)
        for i, y in enumerate(range(-560, 120, 30)):
            props.lamp_post(ctx, f"embankment_lamp{i}", (-96.0, float(y), 0.3), 6.0, math.pi / 2, lit=night)
            if i % 2 == 0:
                vegetation.tree(ctx, f"embankment_tree{i}", (-88.0 if y > -200 else -92.0, float(y) + 15, 0.3), "round", 1.3)
        if int(spec.get("people", 0)):
            for i in range(int(spec["people"])):
                aid = f"bridge_walker{i}"
                x = rng.uniform(-90, 150)
                y = rng.choice((-261.5, -238.5))
                actor = characters.build(ctx, {"id": aid, "role": rng.choice(("civilian", "shopper", "child")), "at": (x, y, 0.4), "top": rng.choice(london.COATS)})
                characters.animate(ctx, actor, {"action": spec.get("people_action", "walk"), "path": [[x, y], [x + rng.choice((-1, 1)) * 12, y]], "start": rng.uniform(0, 1.5)})
    if float(spec.get("clouds", 1.0)) > 0:
        hole = spec.get("cloud_hole")
        puffs = weather.cloud_deck(ctx, "clouds", tuple(spec.get("cloud_centre", (0.0, 0.0))), tuple(spec.get("cloud_extent", (9000.0, 8000.0))), float(spec.get("cloud_base", 480.0)), int(380 * float(spec.get("clouds", 1.0))), puff=(200.0, 460.0), colour=str(spec.get("cloud_colour", "cloud_dark")), thickness=0.28, hole=tuple(hole) if hole else None)
        if spec.get("part"):
            start, end = spec["part"]
            weather.part_clouds(ctx, puffs, TOWER, float(start), float(end), float(spec.get("part_distance", 1400.0)))
    if spec.get("shafts", True) and spec.get("rain", True):
        weather.rain_shafts(ctx, "shafts", (0.0, 0.0), (7000.0, 6000.0), int(spec.get("shaft_count", 18)), top=float(spec.get("cloud_base", 480.0)))
    if spec.get("system"):
        weather.spiral(ctx, "system", tuple(spec.get("system_centre", (0.0, 0.0))), float(spec.get("system_radius", 14000.0)), base=float(spec.get("system_base", 1500.0)), spin=float(spec.get("system_spin", 6.0)))
    for i in range(int(spec.get("cranes", 0))):
        spot = [(-400, -900), (600, 400), (1500, 1500), (2300, 1500), (-900, 700), (900, -700)][i % 6]
        london.tower_crane(ctx, f"crane{i}", (spot[0], spot[1], 0.0), 70.0, 55.0, rng.uniform(0, 6), spin=(0.3 + i * 0.4, ctx.duration, rng.choice((-1, 1)) * rng.uniform(40, 90)) if spec.get("crane_spin") else None)
    for i in range(int(spec.get("flood_pools", 0))):
        px, py = rng.choice(path[8:30])
        side = rng.choice((-1, 1))
        _flood_plane(ctx, f"pool{i}", (rng.uniform(60, 160), rng.uniform(40, 110)), (px + side * (RIVER_WIDTH / 2 + 90), py + rng.uniform(-60, 60)), 0.35)
    if detail:
        _rain(ctx, spec, extent=(60.0, 60.0, 30.0), count=6000)
    ctx.anchor("westminster", (TOWER[0], TOWER[1], 60.0))
    ctx.anchor("clock", (TOWER[0], TOWER[1], 62.0))
    ctx.anchor("eye", (215.0, -40.0, 68.0))
    ctx.anchor("city", (CITY[0], CITY[1], 80.0))
    return None


def london_aerial(ctx, spec):
    """London from the air under a trapped weather system. Flags: night, clouds (0-1), cloud_base,
    cloud_hole, part [start, end] (the clouds break over Westminster), shafts, system (the spiral
    seen from above), dark_districts, cranes, crane_spin, flood_pools, river_level, reach, cell."""
    return _thames_city(ctx, spec, detail=False)


def westminster(ctx, spec):
    """The Palace, Elizabeth Tower and Westminster Bridge with traffic, the Eye across the river, and
    rain around rain_at. Same flags as london_aerial plus buses, traffic, people, clock_lit."""
    return _thames_city(ctx, spec, detail=True)


# ----- the Thames close up ----------------------------------------------------------------------------
def _outfall(ctx, name, loc, length=9.0):
    """Brown sewage overflow gushing from a pipe in the river wall: looping blobs along an arc."""
    x, y, z = loc
    pipe = cylinder(ctx, name, 0.9, 1.4, (x - 0.2, y, z), ctx.mat("black", roughness=0.8), segments=12, rot=(0, math.pi / 2, 0))
    rim = cylinder(ctx, f"{name}.rim", 1.15, 0.3, (x + 0.4, y, z), ctx.mat("dark_steel", roughness=0.6), segments=12, rot=(0, math.pi / 2, 0))
    parent(rim, pipe)
    rim.location = (0, 0, 0.6)
    water = weather.murky(ctx, f"{name} water", "flood_brown", roughness=0.2, bump=0.6, scale=6.0)
    frames = round(0.9 * ctx.fps)
    for k in range(24):
        blob = ico(ctx, f"{name}.blob{k}", 1.0, (x + 0.6, y, z), water, subdiv=1, scale=(1.6, 1.2, 0.9))
        shift = round(k / 24 * frames)  # stagger the blobs along the loop so the stream is continuous
        points = [(x + 0.6 + t * length, y + math.sin(t * 7 + k) * 0.35, z - (t * 1.6) ** 2) for t in (0.0, 0.33, 0.66, 1.0)]
        for i, point in enumerate(points):
            key(blob, "location", 1 - shift + round((i / 3) * frames), point)
        set_interp(blob, "LINEAR", path="location")
        for curve in fcurves(blob, "location"):
            curve.modifiers.new("CYCLES")
    foam = ico(ctx, f"{name}.foam", 7.0, (x + length, y, z - 2.5), ctx.mat("silt", roughness=0.9), subdiv=2, scale=(1.4, 1.2, 0.08))
    add_noise(foam, "scale", 0.15, 1, ctx.frames, scale=4.0)
    plume = ico(ctx, f"{name}.plume", 30.0, (x + length + 28, y + 12, z - 2.56), ctx.mat("flood_brown", roughness=0.4), subdiv=2, scale=(1.6, 0.9, 0.01))
    plume.visible_shadow = False
    return pipe


def thames(ctx, spec):
    """The Victoria Embankment and the swollen river. Flags: river_level, outfall, barrier (the Thames
    Barrier across a wider river instead), rain, rain_at, night, traffic, walkers."""
    rng = ctx.rng
    night = bool(spec.get("night"))
    lit = _window_lights(ctx, night)
    level = float(spec.get("river_level", -2.0))
    width = 520.0 if spec.get("barrier") else 250.0
    box(ctx, "riverbed", (width + 40, 1400.0, 0.2), (width / 2, 0.0, -9.0), ctx.mat("mud"), anchor="base")
    river = box(ctx, "river", (width, 1400.0, 0.1), (width / 2, 0.0, level), weather.murky(ctx, "thames close", "thames", roughness=0.16, bump=0.4, scale=0.3, specular=0.35))
    ctx.tag("river", river)
    for side, x in ((-1, 0.0), (1, width)):
        # river walls stand on the land side of each bank, faces flush with the water's edge
        multi_box(ctx, f"wall{side}", [((x + side * 0.5, 0, -4.0), (1.0, 1400.0, 9.0), 0), ((x + side * 0.6, 0, 0.55), (1.3, 1400.0, 1.1), 0)] + [((x + side * 0.05, y, -1.0), (0.4, 0.6, 0.6), 1) for y in range(-690, 700, 18)], [ctx.mat("portland_stone", roughness=0.85), ctx.mat("black", roughness=0.6)])
    box(ctx, "embankment_walk", (7.0, 1400.0, 0.3), (-3.5, 0.0, 0.0), ctx.mat("pavement_wet", roughness=0.3), anchor="base")
    london.kerb_and_road(ctx, "embankment_road", 1400.0, 12.0, (3.0, 4.0), wet=True, bus_lane=True, centre=(-16.0, 0.0))
    for i, y in enumerate(range(-300, 300, 24)):
        props.lamp_post(ctx, f"lamp{i}", (-1.2, float(y), 0.3), 5.5, -math.pi / 2, lit=night)
        if i % 2:
            vegetation.tree(ctx, f"plane{i}", (-6.0, float(y) + 12, 0.3), "round", 1.3)
    london.terrace(ctx, "mansions", (-27.0, -300.0, 0.0), 30, math.pi / 2, seed=21, kind="mansion", lit=lit)
    for i in range(30):
        h = rng.uniform(14, 40)
        buildings.building(ctx, f"south_bank{i}", (width + 30 + rng.uniform(0, 60), -500 + i * 34.0, 0.0), (rng.uniform(20, 34), rng.uniform(20, 30), h), rng.choice(("concrete", "portland_stone", "london_brick")), "flat", 0.0, 50 + i, window=(1.6, 1.8), lit=lit)
    if not spec.get("barrier"):
        london.london_eye(ctx, "eye", (width + 60.0, 320.0, 0.0), math.pi / 2, 60.0, lit=night)
    for i in range(int(spec.get("boats", 2))):
        vehicles.boat(ctx, f"boat{i}", (40.0 + i * 60.0, -60.0 + i * 150.0, level - 0.4), rng.uniform(-0.3, 0.3), 14.0, rng.choice(("white", "navy")))
    if spec.get("outfall"):
        _outfall(ctx, "outfall", (0.2, float(spec.get("outfall_y", 0.0)), level + 1.2))
    if spec.get("barrier"):
        london.thames_barrier(ctx, "barrier", (0.0, 0.0), (width, 0.0), piers=10, level=level)
        _flood_plane(ctx, "upstream", (width, 600.0), (width / 2, 300.0), level + 1.2, colour="thames", tag="river_high")
    _traffic(ctx, {"buses": spec.get("buses", 1), "traffic": spec.get("traffic", 6), "traffic_speed": 6.0}, 600.0, night, lanes=(-18.6, -13.4))
    if int(spec.get("walkers", 0)):
        london.walkers(ctx, "walker", [(-3.5, 1), (-3.5, -1)], int(spec["walkers"]), 60.0, umbrellas=0.9, clear=spec.get("walkers_clear"))
    _rain(ctx, spec, extent=(50.0, 50.0, 26.0), count=6000)
    ctx.anchor("outfall", (0.0, float(spec.get("outfall_y", 0.0)), level + 1.0))
    ctx.anchor("barrier", (width / 2, 0.0, 6.0))
    return None


# ----- interiors -------------------------------------------------------------------------------------
def _room_shell(ctx, name, size, wall="wallpaper", floor="floor_wood", window=None):
    """Walls, floor and ceiling of a room spanning x in [-w/2, w/2], y in [0, d], z in [0, h]. window =
    (x0, x1, z0, z1) cut into the y = d wall."""
    w, d, h = size
    wall_mat = ctx.mat(wall, roughness=0.9)
    boxes = [((0, d / 2, -0.05), (w + 0.4, d + 0.4, 0.1), 1), ((0, d / 2, h + 0.05), (w + 0.4, d + 0.4, 0.1), 2), ((-w / 2 - 0.1, d / 2, h / 2), (0.2, d + 0.4, h), 0), ((w / 2 + 0.1, d / 2, h / 2), (0.2, d + 0.4, h), 0), ((0, -0.1, h / 2), (w + 0.4, 0.2, h), 0)]
    if window:
        x0, x1, z0, z1 = window
        boxes += [((-(w / 2) + (x0 + w / 2) / 2, d + 0.1, h / 2), (x0 + w / 2, 0.2, h), 0), ((x1 + (w / 2 - x1) / 2, d + 0.1, h / 2), (w / 2 - x1, 0.2, h), 0), (((x0 + x1) / 2, d + 0.1, z0 / 2), (x1 - x0, 0.2, z0), 0), (((x0 + x1) / 2, d + 0.1, (z1 + h) / 2), (x1 - x0, 0.2, h - z1), 0)]
        boxes += [(((x0 + x1) / 2, d + 0.02, z0 - 0.05), (x1 - x0 + 0.3, 0.3, 0.06), 3), (((x0 + x1) / 2, d + 0.12, (z0 + z1) / 2), (x1 - x0, 0.06, 0.06), 3), (((x0 + x1) / 2, d + 0.12, (z0 + z1) / 2), (0.06, 0.06, z1 - z0), 3)]
    else:
        boxes.append(((0, d + 0.1, h / 2), (w + 0.4, 0.2, h), 0))
    return multi_box(ctx, name, boxes, [wall_mat, ctx.mat(floor, roughness=0.6), ctx.mat("ceiling", roughness=0.9), ctx.mat("sash_white", roughness=0.5)])


def _drips(ctx, name, points, ceiling, floor=0.35):
    """Water dripping from the ceiling into buckets, looping."""
    drop_mat = weather.murky(ctx, f"{name} drop", "puddle", roughness=0.05)
    for i, (x, y) in enumerate(points):
        drop = ico(ctx, f"{name}{i}", 0.025, (x, y, ceiling - 0.03), drop_mat, subdiv=1, scale=(1, 1, 1.6))
        frames = round(0.7 * ctx.fps)
        key(drop, "location", 1 + i * 5, (x, y, ceiling - 0.03))
        key(drop, "location", 1 + i * 5 + frames, (x, y, floor))
        set_interp(drop, "LINEAR", path="location")
        for curve in fcurves(drop, "location"):
            curve.modifiers.new("CYCLES")
        bucket = cylinder(ctx, f"{name}{i}.bucket", 0.18, 0.32, (x, y, 0.0), ctx.mat(("yellow", "red", "teal")[i % 3], roughness=0.5), segments=12, anchor="base", radius2=0.14)
        ctx.tag("bucket", bucket)


def london_interior(ctx, spec):
    """A rented London flat: sofa, lamp and a sash window onto the rain. Flags: mould (patches tagged
    `mould`, grow them with a scale event), damp, buckets (dripping ceiling), child (at the window),
    adult, night, rain_at (outside)."""
    night = bool(spec.get("night"))
    w, d, h = 5.0, 4.6, 2.7
    _room_shell(ctx, "room", (w, d, h), window=(-0.9, 0.9, 0.85, 2.25))
    glass = ctx.palette.make("window glass", ctx.palette.colour("glass"), roughness=0.05, alpha=0.18)
    pane = box(ctx, "window_pane", (1.8, 0.02, 1.4), (0.0, d + 0.06, 1.55), glass)
    pane.visible_shadow = False
    multi_box(ctx, "furniture", [((-1.7, 1.4, 0.25), (0.9, 2.1, 0.5), 0), ((-2.05, 1.4, 0.65), (0.25, 2.1, 0.8), 0), ((-1.7, 0.35, 0.45), (0.9, 0.2, 0.5), 0), ((-1.7, 2.45, 0.45), (0.9, 0.2, 0.5), 0), ((0.2, 1.6, 0.22), (1.0, 0.6, 0.44), 1), ((2.2, 0.8, 0.9), (0.4, 1.4, 1.8), 1), ((0.0, d - 0.12, 0.45), (1.4, 0.1, 0.6), 2), ((0.0, 2.0, 0.01), (2.6, 1.8, 0.02), 3)], [ctx.mat("sofa", roughness=0.9), ctx.mat("floor_wood", roughness=0.6), ctx.mat("white", roughness=0.4), ctx.mat("blanket_1", roughness=1.0)])
    lamp_mat = ctx.palette.emissive("lamp shade", (1.0, 0.82, 0.55), 3.0 if night else 0.6)
    cylinder(ctx, "lamp", 0.2, 0.3, (-2.1, 3.4, 1.55), lamp_mat, segments=10, anchor="base", radius2=0.14)
    cylinder(ctx, "lamp_pole", 0.02, 1.55, (-2.1, 3.4, 0.0), ctx.mat("black"), segments=6, anchor="base")
    data = bpy.data.lights.new("lamp_light", "POINT")
    data.energy = 120.0 if night else 40.0
    data.color = (1.0, 0.8, 0.55)
    light = bpy.data.objects.new("lamp_light", data)
    light.location = (-2.1, 3.4, 1.7)
    ctx.link(light)
    box(ctx, "dehumidifier", (0.35, 0.25, 0.6), (1.5, 3.9, 0.0), ctx.mat("white", roughness=0.4), anchor="base")
    if float(spec.get("mould", 0.0)) > 0:
        rng = ctx.rng
        spots = [((-1.1, d - 0.11, 2.45), "y", 0.55), ((1.2, d - 0.11, 2.4), "y", 0.6), ((-2.39, d - 0.6, 2.35), "x", 0.5), ((2.39, d - 0.5, 2.3), "x", 0.55), ((1.3, d - 0.11, 0.35), "y", 0.35), ((-1.3, d - 0.11, 0.3), "y", 0.3), ((-2.39, 1.0, 2.5), "x", 0.4)]
        for i, (loc, axis, size) in enumerate(spots[: max(1, int(len(spots) * float(spec["mould"])))]):
            london.mould_patch(ctx, f"mould{i}", loc, axis, size * rng.uniform(0.9, 1.3), seed=i)
    if spec.get("buckets"):
        _drips(ctx, "drip", [(0.9, 1.2), (-0.6, 3.2)], h)
    if spec.get("child"):
        child = characters.build(ctx, {"id": "child", "role": "child", "at": (0.15, d - 0.75, 0.0), "face": 0.0})
        characters.animate(ctx, child, {"action": "idle"})
    if spec.get("adult"):
        adult = characters.build(ctx, {"id": "adult", "role": "civilian", "at": (-1.2, 1.0, 0.0), "face": 40.0, "top": "coat_grey"})
        characters.animate(ctx, adult, {"action": spec.get("adult_action", "idle")})
    # the street outside: a terrace opposite, in the rain
    london.terrace(ctx, "opposite", (-30.0, d + 22.0, -0.3), 10, 0.0, seed=33, kind="residential", lit=_window_lights(ctx, night))
    box(ctx, "outside_street", (80.0, 20.0, 0.2), (0.0, d + 10.0, -3.6), ctx.mat("tarmac_wet", roughness=0.2), anchor="base")
    _rain(ctx, {**spec, "rain_at": [0.0, d + 9.0, -3.5]}, extent=(16.0, 10.0, 12.0), count=2500)
    ctx.anchor("window", (0.0, d, 1.5))
    ctx.anchor("room", (0.0, d / 2, 1.3))
    return None


def sports_hall(ctx, spec):
    """A leisure-centre sports hall turned into a rest centre: rows of camp beds under strip lights."""
    rng = ctx.rng
    w, d, h = 40.0, 24.0, 9.0
    shell = _room_shell(ctx, "hall", (w, d, h), wall="stucco", floor="gym_floor")
    shell.location.y = -d / 2
    lines = [((0, 0, 0.012), (0.12, d - 2, 0.01), 0), ((0, 0, 0.012), (w - 2, 0.12, 0.01), 0), ((0, 0, 0.012), (6.0, 0.12, 0.01), 0)]
    multi_box(ctx, "court_lines", lines, [ctx.mat("court_line", roughness=0.5)])
    trusses = [((x, 0, h - 0.6), (0.3, d, 0.6), 0) for x in range(-18, 19, 6)]
    windows = [((x, d / 2 - 0.02, h - 1.6), (4.0, 0.06, 1.6), 1) for x in range(-16, 17, 8)]
    multi_box(ctx, "roof_steel", trusses + windows, [ctx.mat("dark_steel", roughness=0.5), ctx.palette.emissive("hall windows", (0.55, 0.6, 0.68), 1.4)])
    beds = []
    blankets = []
    for row in range(int(spec.get("rows", 5))):
        for col in range(int(spec.get("cols", 11))):
            x, y = -17.0 + col * 3.3, -8.0 + row * 3.8
            beds += [((x, y, 0.35), (0.85, 2.0, 0.08), 0), ((x - 0.4, y, 0.17), (0.05, 2.0, 0.34), 1), ((x + 0.4, y, 0.17), (0.05, 2.0, 0.34), 1)]
            blankets.append(((x, y - 0.2, 0.42), (0.8, 1.4, 0.08), rng.randrange(3)))
            blankets.append(((x, y + 0.8, 0.43), (0.5, 0.3, 0.1), 3))
            if rng.random() < 0.5:
                blankets.append(((x + 0.7, y + 0.6, 0.25), (0.45, 0.3, 0.5), 4))
    multi_box(ctx, "camp_beds", beds, [ctx.mat("camp_bed", roughness=0.9), ctx.mat("dark_steel", roughness=0.5)])
    multi_box(ctx, "bedding", blankets, [ctx.mat(c, roughness=1.0) for c in ("blanket_1", "blanket_2", "blanket_3")] + [ctx.mat("white", roughness=1.0), ctx.mat("navy", roughness=0.8)])
    for i in range(6):
        data = bpy.data.lights.new(f"strip{i}", "AREA")
        data.energy = 900.0
        data.size = 6.0
        data.color = (0.92, 0.96, 1.0)
        light = bpy.data.objects.new(f"strip{i}", data)
        light.location = (-15.0 + i * 6.0, 0.0, h - 1.0)
        ctx.link(light)
    for i in range(int(spec.get("people", 22))):
        role = rng.choice(("civilian", "civilian", "child", "shopper", "paramedic"))
        x, y = rng.uniform(-18, 18), rng.uniform(-9, 9)
        actor = characters.build(ctx, {"id": f"resident{i}", "role": role, "at": (x, y, 0.0), "face": rng.uniform(0, 360)})
        characters.animate(ctx, actor, {"action": rng.choice(("idle", "idle", "look_around", "crouch")) if role != "paramedic" else "walk", "path": [[x, y], [x + rng.uniform(-6, 6), y]]})
    ctx.anchor("hall", (0.0, 0.0, 1.5))
    return None


# ----- works, substation, hospital -------------------------------------------------------------------
def london_works(ctx, spec):
    """A stalled building site (flooded basement dig, idle tower cranes, hoarding) or, with
    kind: substation, a flooded electricity substation that sparks (tag spark) beside terraces."""
    rng = ctx.rng
    night = bool(spec.get("night"))
    lit = _window_lights(ctx, night)
    box(ctx, "ground", (600.0, 600.0, 0.2), (0.0, 0.0, -0.2), ctx.mat("mud", roughness=0.9), anchor="base")
    london.kerb_and_road(ctx, "road", 300.0, 9.0, (3.0, 3.0), wet=True, bus_lane=False, centre=(-30.0, 0.0))
    if spec.get("kind", "site") == "substation":
        london.substation(ctx, "substation", (8.0, 10.0, 0.0), 0.0)
        _flood_plane(ctx, "substation_flood", (40.0, 30.0), (8.0, 8.0), float(spec.get("flood", 0.35)))
        # arcing: point lights that a flicker event flashes (an emissive ball would go black between flashes)
        for i, x in enumerate((0.0, 8.0, 16.0)):
            data = bpy.data.lights.new(f"arc{i}", "POINT")
            data.energy = 0.0
            data.color = (0.7, 0.82, 1.0)
            arc = bpy.data.objects.new(f"arc{i}", data)
            arc.location = (x, 10.0, 4.2)
            ctx.link(arc)
            ctx.tag("spark", arc)
        data = bpy.data.lights.new("security_light", "SPOT")
        data.energy = 40000.0
        data.spot_size = math.radians(75)
        data.color = (0.85, 0.9, 1.0)
        light = bpy.data.objects.new("security_light", data)
        light.location = (-6.0, -2.0, 7.5)
        light.rotation_euler = (Vector((8.0, 10.0, 1.5)) - Vector(light.location)).to_track_quat("-Z", "Y").to_euler()
        ctx.link(light)
        multi_box(ctx, "security_pole", [((-6.0, -2.0, 3.8), (0.2, 0.2, 7.6), 0), ((-6.0, -2.0, 7.7), (0.9, 0.5, 0.4), 1)], [ctx.mat("dark_steel"), ctx.palette.emissive("security lamp", (0.85, 0.9, 1.0), 8.0 if night else 0.0)])
        for i, y in enumerate((-6.0, 14.0, 30.0)):
            props.lamp_post(ctx, f"near_lamp{i}", (-3.0, y, 0.0), 7.0, -math.pi / 2, lit=night)
        london.terrace(ctx, "houses", (-40.0, 40.0, 0.0), 14, 0.0, seed=8, kind="residential", lit=lit)
        london.terrace(ctx, "houses_b", (40.0, -40.0, 0.0), 12, math.pi, seed=9, kind="residential", lit=lit)
        for i, y in enumerate(range(-60, 60, 25)):
            props.lamp_post(ctx, f"lamp{i}", (-25.2, float(y), 0.16), 7.0, math.pi / 2, lit=night)
    else:
        hoard = []
        for x in range(-5, 66, 2):
            hoard.append(((float(x), -12.0, 1.2), (2.0, 0.1, 2.4), 0))
        for y in range(-12, 50, 2):
            hoard.append(((-5.0, float(y), 1.2), (0.1, 2.0, 2.4), 0))
        multi_box(ctx, "hoarding", hoard, [ctx.mat("hoarding", roughness=0.8)])
        props.sign_text(ctx, "hoarding_sign", "SITE CLOSED - FLOODING", (-5.12, 14.0, 1.6), size=0.5, rot=(math.pi / 2, 0, -math.pi / 2), colour="white")
        box(ctx, "pit_water", (30.0, 26.0, 0.1), (25.0, 18.0, float(spec.get("flood", -0.6))), weather.murky(ctx, "pit water", "flood_brown"))
        frame = []
        for cx_ in range(0, 4):
            for cy_ in range(0, 3):
                for lvl in range(4):
                    frame.append(((44.0 + cx_ * 6.0, 8.0 + cy_ * 6.0, lvl * 3.5 + 1.75), (0.5, 0.5, 3.5), 0))
        for lvl in range(1, 5):
            frame.append(((53.0, 14.0, lvl * 3.5), (20.0, 14.0, 0.3), 0))
        multi_box(ctx, "frame", frame, [ctx.mat("concrete", roughness=0.8)])
        for i, (x, y) in enumerate(((20.0, 30.0), (60.0, 34.0))):
            london.tower_crane(ctx, f"crane{i}", (x, y, 0.0), 48.0 + i * 8, 42.0, rng.uniform(0, 6), spin=(0.5, ctx.duration, rng.uniform(30, 80)) if spec.get("crane_spin") else None)
        for i in range(4):
            box(ctx, f"cabin{i}", (2.6, 8.0, 2.6), (8.0 + (i % 2) * 3.0, 40.0, (i // 2) * 2.6), ctx.mat("portakabin", roughness=0.6), anchor="base")
        buildings.warehouse(ctx, "warehouse", (110.0, 10.0, 0.0), (60.0, 40.0, 12.0), 0.0, "steel")
        _flood_plane(ctx, "yard_flood", (80.0, 70.0), (110.0, 10.0), 0.25)
    weather.puddles(ctx, "puddles", (-20.0, -40.0, 90.0, 60.0), 60, size=(1.5, 6.0), z=0.01)
    _rain(ctx, spec, extent=(50.0, 50.0, 26.0), count=6000)
    ctx.anchor("site", (25.0, 18.0, 2.0))
    ctx.anchor("substation", (8.0, 10.0, 2.5))
    return None


def london_hospital(ctx, spec):
    """A London hospital's A&E entrance in the rain with ambulances queuing, beacons tagged `beacon`."""
    night = bool(spec.get("night"))
    lit = _window_lights(ctx, night)
    box(ctx, "ground", (600.0, 600.0, 0.2), (0.0, 0.0, -0.2), weather.wet(ctx, "tarmac_wet", roughness=0.55, specular=0.12), anchor="base")
    london.kerb_and_road(ctx, "road", 300.0, 10.0, (4.0, 4.0), wet=True, bus_lane=True, centre=(0.0, -30.0), rot=math.pi / 2)
    london.terrace(ctx, "opposite", (-120.0, -45.0, 0.0), 40, 0.0, seed=14, kind="shops", lit=lit)
    for i in range(10):
        vehicles.car(ctx, f"parked{i}", (-40.0 + i * 3.2, -8.0, 0.0), math.pi / 2, CAR_COLOURS[i % len(CAR_COLOURS)])
    buildings.building(ctx, "hospital", (0.0, 40.0, 0.0), (90.0, 30.0, 32.0), "portland_stone", "flat", 0.0, 7, window=(1.8, 1.6), floor_height=4.0, trim="fascia_navy", lit=lit)
    marks = [((0, 8.0, 0.006), (22.0, 0.2, 0.01), 0), ((0, -1.0, 0.006), (22.0, 0.2, 0.01), 0), ((-11.0, 3.5, 0.006), (0.2, 9.0, 0.01), 0), ((11.0, 3.5, 0.006), (0.2, 9.0, 0.01), 0)]
    marks += [((-10.0 + k * 2.0, 3.5, 0.007), (0.25, 9.0, 0.01), 0) for k in range(11)]
    multi_box(ctx, "bay_markings", marks, [ctx.mat("line_yellow", roughness=0.4)])
    for k in range(8):
        cylinder(ctx, f"bollard{k}", 0.1, 1.0, (-12.0 + k * 3.4, -2.2, 0.0), ctx.mat("dark_steel"), segments=8, anchor="base")
    buildings.building(ctx, "hospital_wing", (70.0, 30.0, 0.0), (40.0, 40.0, 20.0), "london_brick", "flat", 0.0, 8, window=(1.6, 1.6), lit=lit)
    multi_box(ctx, "canopy", [((0, 17.0, 4.2), (24.0, 10.0, 0.4), 0)] + [((x, 13.0, 2.0), (0.3, 0.3, 4.0), 1) for x in (-11, -4, 4, 11)], [ctx.mat("white", roughness=0.5), ctx.mat("dark_steel")])
    box(ctx, "ae_board", (8.0, 0.3, 1.6), (0.0, 12.2, 5.4), ctx.mat("barrier_red", roughness=0.5), anchor="base")
    props.sign_text(ctx, "ae_sign", "A&E", (0.0, 12.0, 5.75), 1.0, colour="white", emission=2.0 if night else 0.6, weight=0.02)
    for i in range(int(spec.get("ambulances", 6))):
        if i < 2:
            loc, rot = (-4.0 + i * 8.0, 15.5, 0.0), math.pi
        else:
            loc, rot = (-4.0, 6.0 - (i - 2) * 7.2, 0.0), 0.0
        vehicles.van(ctx, f"ambulance{i}", loc, rot, "white", "ambulance", lit=True)
    for i, y in enumerate(range(-40, 40, 20)):
        props.lamp_post(ctx, f"lamp{i}", (-22.0, float(y), 0.0), 7.0, -math.pi / 2, lit=night)
    london.terrace(ctx, "houses", (-90.0, -30.0, 0.0), 12, -math.pi / 2, seed=12, kind="residential", lit=lit)
    if int(spec.get("walkers", 0)):
        london.walkers(ctx, "walker", [(-6.0, 1), (6.0, -1)], int(spec["walkers"]), 30.0, umbrellas=0.9, centre=0.0, roles=("civilian", "nurse", "civilian", "paramedic"))
    weather.puddles(ctx, "puddles", (-40.0, -40.0, 40.0, 12.0), 50, size=(1.0, 4.5), z=0.01)
    _rain(ctx, spec, extent=(44.0, 44.0, 24.0), count=6000)
    ctx.anchor("entrance", (0.0, 13.0, 2.0))
    return None


BUILDERS = {
    "london_street": london_street,
    "london_park": london_park,
    "london_aerial": london_aerial,
    "westminster": westminster,
    "thames": thames,
    "london_interior": london_interior,
    "sports_hall": sports_hall,
    "london_works": london_works,
    "london_hospital": london_hospital,
}
FOG_EXTENT = {"london_street": (700, 700, 160), "london_park": (700, 700, 160), "london_aerial": (16000, 16000, 1200), "westminster": (6000, 6000, 900), "thames": (2000, 2000, 300), "london_interior": (0, 0, 0), "sports_hall": (0, 0, 0), "london_works": (700, 700, 200), "london_hospital": (700, 700, 200)}


def build(ctx, spec):
    return BUILDERS[spec["type"]](ctx, spec)
