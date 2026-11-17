"""Los Angeles environments for "When The Wind Took Everything": sunny LA torn apart by a 24-hour,
300 mph wind, seen from the street, the freeway, the hills, downtown, the airport, the pier, the air,
and from inside the rooms where people shelter.

Coordinates are metres. Streets run along Y; US traffic keeps right (northbound x > 0). The wind
blows toward -X. Most builders take `wind` (0-1) and `gust_at` (seconds): calm before the gust,
violent after it. `aftermath` shows the morning after."""

from __future__ import annotations

import math

import bpy
from mathutils import Matrix, Vector

from studio.assets import buildings, characters, la, landmarks, props, terrain, vehicles, wind
from studio.assets.meshes import merged_boxes
from studio.blender import environments_nyc
from studio.blender.primitives import add_noise, box, cylinder, key, multi_box, set_interp
from studio.core.motion import smoothstep

CAR_COLOURS = ("white", "black", "stone", "red", "navy", "dark_steel", "teal", "silver")
ROLES = ("civilian", "shopper", "civilian", "child")


# ----- shared pieces -------------------------------------------------------------------------------
def _lights_material(ctx, night, strength=2.4):
    if not night:
        return None
    material = ctx.palette.make("la windows lit", (1.0, 0.78, 0.5), 0.5, 0.0, strength)
    ctx.tag("window_lights", material)
    return material


def _storm(ctx, spec, default_at=(0.0, 0.0, 0.0), extent=(90.0, 60.0, 16.0)):
    """Debris and dust streaks around spec['wind_at'] (the camera's x, y), once the gust arrives."""
    level = float(spec.get("wind", 0.0))
    if level <= 0:
        return
    at = spec.get("wind_at") or default_at
    centre = (float(at[0]), float(at[1]), float(at[2]) if len(at) > 2 else 0.0)
    start = float(spec.get("gust_at", 0.0))
    night = bool(spec.get("night"))
    wind.debris(ctx, "debris", centre, extent, int(420 * level * float(spec.get("debris", 1.0))), speed=40.0 + 30.0 * level, clusters=14, start=start, clear=8.0)
    wind.streaks(ctx, "streaks", centre, (extent[0] * 1.3, extent[1], extent[2] + 6.0), int(1100 * level), speed=70.0 + 50.0 * level, colour="dust_night" if night else "dust", alpha=0.25 if night else 0.35, start=start, clear=1.5)


def _people(ctx, name, count, area, action="walk", roles=ROLES, run_dir=(0.0, 1.0), start=0.0, face=None):
    """A handful of people inside area = (x0, y0, x1, y1): walking along Y, running, or standing."""
    rng = ctx.rng
    x0, y0, x1, y1 = area
    actors = []
    for i in range(count):
        x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        actor = characters.build(ctx, {"id": f"{name}{i}", "role": rng.choice(roles), "at": (x, y, 0.16), "face": face if face is not None else rng.uniform(0, 360)})
        if action in ("walk", "run"):
            dist = rng.uniform(6, 14) if action == "walk" else rng.uniform(10, 22)
            characters.animate(ctx, actor, {"action": action, "path": [[x, y], [x + run_dir[0] * dist, y + run_dir[1] * dist]], "start": start + rng.uniform(0, 1.0)})
        else:
            characters.animate(ctx, actor, {"action": action, "start": start + rng.uniform(0, 0.6)})
        actors.append(actor)
    return actors


# ----- streets -------------------------------------------------------------------------------------
def la_street(ctx, spec):
    """A Los Angeles boulevard (kind: boulevard) or palm-lined residential street (kind: residential).
    Flags: wind, gust_at, wind_at, debris, traffic, parked, people, people_action, uproot (palm
    times), thrown (car times), roofs (roof-loss times), ripped, burst_at, poles_down, lights_torn,
    fires (count), night, blackout, aftermath, crews."""
    rng = ctx.rng
    night = bool(spec.get("night"))
    after = bool(spec.get("aftermath"))
    level = float(spec.get("wind", 0.0))
    gust = float(spec.get("gust_at", 0.0))
    lit = _lights_material(ctx, night and not spec.get("blackout"))
    kind = str(spec.get("kind", "boulevard"))
    length = 320.0
    box(ctx, "ground", (900.0, 900.0, 0.2), (0.0, 0.0, -0.22), ctx.mat("lot_tarmac", roughness=0.9), anchor="base")
    uproot = list(spec.get("uproot") or [])
    thrown = list(spec.get("thrown") or [])
    roofs = list(spec.get("roofs") or [])
    if kind == "boulevard":
        _, half = la.us_road(ctx, "boulevard", length, 3, sidewalk=4.5)
        front = half + 0.2 + 4.5
        la.strip_mall(ctx, "west_shops", (-front, -length / 2 + 10, 0.0), 20, math.pi / 2, seed=3, lit=lit, ripped=float(spec.get("ripped", 0.0)), burst_at=spec.get("burst_at"))
        la.strip_mall(ctx, "east_shops", (front, length / 2 - 10, 0.0), 20, -math.pi / 2, seed=7, lit=lit, ripped=float(spec.get("ripped", 0.0)), burst_at=spec.get("burst_at"))
        palm_x = half + 2.2
        lanes = [-(1.8 + 3.6 * (k + 0.5)) for k in range(3)] + [1.8 + 3.6 * (k + 0.5) for k in range(3)]
        for i, y in enumerate(range(int(-length / 2 + 20), int(length / 2 - 20), 32)):
            for side in (-1, 1):
                torn = spec.get("lights_torn")
                la.streetlight(ctx, f"light{i}{side}", (side * (half + 0.6), float(y) + (16 if side > 0 else 0), 0.16), side * math.pi / 2, lit=night and not spec.get("blackout"), torn_at=(float(torn) + rng.uniform(0, 1.5)) if torn is not None and abs(y) < 60 else None)
        landmarks.billboard(ctx, "billboard", (-front - 6.0, 30.0, 16.0), (16.0, 7.0), math.pi / 2, strength=0.0 if spec.get("blackout") else (3.0 if night else 0.0), message=str(spec.get("billboard", "OPEN 24 HOURS")))
    else:
        _, half = la.us_road(ctx, "street", length, 1, lane=3.75, sidewalk=1.6, turn_lane=False, parkway=2.5)
        palm_x = half + 1.4
        lanes = [-1.9, 1.9]
        front = half + 0.2 + 2.5 + 1.6
        for side in (-1, 1):
            for i, y in enumerate(range(int(-length / 2 + 12), int(length / 2 - 12), 17)):
                hx = side * (front + 9.0 + 6.0)
                torn = roofs[i % len(roofs)] if roofs and abs(y) < 80 and rng.random() < 0.6 else None
                la.house(ctx, f"house{side}_{i}", (hx, float(y), 0.0), math.pi / 2 if side < 0 else -math.pi / 2, seed=i * 3 + (side > 0), lit=lit, roof_torn_at=(torn + rng.uniform(0, 1.2)) if torn is not None else None, roofless=after and rng.random() < 0.55)
        la.power_line(ctx, "lines", half + 2.0, -length / 2 + 10, length / 2 - 10, down_at=spec.get("poles_down"))
    # palms: the skyline of Los Angeles
    palms = []
    for i, y in enumerate(range(int(-length / 2 + 8), int(length / 2 - 8), 16 if kind == "boulevard" else 20)):
        for side in (-1, 1):
            loc = (side * palm_x + rng.uniform(-0.3, 0.3), float(y) + (8.0 if side > 0 else 0.0), 0.16)
            if after:
                if rng.random() < 0.5:
                    la.fallen_palm(ctx, f"palm{side}_{i}", loc, heading=rng.uniform(-0.6, 0.6) + (math.pi if rng.random() < 0.3 else 0.0))
                elif rng.random() < 0.7:
                    cylinder(ctx, f"stump{side}_{i}", 0.34, rng.uniform(3.0, 9.0), loc, ctx.mat("palm_trunk", roughness=0.9), segments=7, anchor="base", radius2=0.3)
                continue
            up = None
            if uproot and abs(loc[1] - float(spec.get("uproot_y", 0.0))) < 40 and len(palms) < len(uproot):
                up = float(uproot[len(palms)])
                palms.append(up)
            la.palm(ctx, f"palm{side}_{i}", loc, 22.0, level, gust, uproot_at=up)
    # traffic and parked cars
    vehicles_made = 0
    if not after:
        for i in range(int(spec.get("traffic", 6))):
            lane = rng.choice(lanes)
            heading = 0.0 if lane > 0 else math.pi
            y = rng.uniform(-length / 2 + 20, length / 2 - 20)
            car = vehicles.car(ctx, f"car{i}", (lane, y, 0.0), heading, rng.choice(CAR_COLOURS), lit=night)
            speed = 12.0 if level <= 0 else 0.0
            if speed:
                end = y + speed * (ctx.duration + 1.0) * (1 if lane > 0 else -1)
                vehicles.drive(ctx, car, [(lane, y), (lane, end)], 0.0, ctx.duration + 1.0, speed=speed)
            vehicles_made += 1
    for i, t in enumerate(thrown):
        lane = lanes[i % len(lanes)]
        y = float(spec.get("thrown_y", 0.0)) + rng.uniform(-25, 25)
        car = vehicles.car(ctx, f"thrown{i}", (lane, y, 0.0), rng.uniform(-0.3, 0.3), rng.choice(CAR_COLOURS))
        wind.fly(ctx, car, float(t), float(t) + rng.uniform(1.2, 1.8), (-rng.uniform(18, 34), rng.uniform(-6, 6), 0.0), spin=(rng.uniform(0.25, 0.75), rng.uniform(0.5, 1.25), rng.uniform(-0.25, 0.25)), arc=rng.uniform(3, 8))
    if after:
        near = spec.get("debris_near")
        if near:
            for i in range(50):
                s = rng.uniform(0.5, 2.8)
                box(ctx, f"near_rubble{i}", (s, s * rng.uniform(0.3, 1.0), s * 0.15), (float(near[0]) + rng.uniform(-9, 9), float(near[1]) + rng.uniform(4, 30), 0.1), ctx.mat(rng.choice(wind.DEBRIS + ("roof_tile",)), roughness=0.9), rot=(rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), rng.uniform(0, 3)))
            for i in range(3):
                la.fallen_palm(ctx, f"near_palm{i}", (float(near[0]) + rng.uniform(-6, 6), float(near[1]) + 8 + i * 9, 0.0), heading=rng.uniform(-0.5, 0.5))
        for i in range(int(spec.get("wrecks", 10))):
            car = vehicles.car(ctx, f"wreck{i}", (rng.uniform(-half, half), rng.uniform(-80, 80), 0.0), rng.uniform(0, 6), rng.choice(CAR_COLOURS))
            if rng.random() < 0.5:
                car.rotation_euler = (0.0, math.radians(rng.choice((90, 180))), car.rotation_euler.z)
                car.location.z = 0.9 if abs(car.rotation_euler.y - math.pi) > 0.1 else 1.6
        for i in range(60):
            s = rng.uniform(0.6, 3.0)
            box(ctx, f"rubble{i}", (s, s * rng.uniform(0.3, 1.0), s * 0.15), (rng.uniform(-front, front), rng.uniform(-90, 90), 0.1), ctx.mat(rng.choice(wind.DEBRIS), roughness=0.9), rot=(rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), rng.uniform(0, 3)))
        if kind == "boulevard":
            la.power_line(ctx, "fallen_lines", half + 2.0, -60.0, 60.0, down_at=0.0, sparks=False)
    if spec.get("crews"):
        la.fire_truck(ctx, "engine", (lanes[-1], 18.0, 0.0), math.pi, lit=True)
        landmarks.police_car(ctx, "police", (lanes[0], -6.0, 0.0), 0.3, lit=True)
        _people(ctx, "crew", 6, (-6, 4, 6, 24), action="walk", roles=("paramedic", "worker", "police"))
    if int(spec.get("people", 0)):
        _people(ctx, "walker", int(spec["people"]), (-front + 1.0, -30.0, -half - 1.0, 10.0), action=str(spec.get("people_action", "walk")), run_dir=(0.0, 1.0), start=float(spec.get("people_start", 0.0)))
    if spec.get("collapse") is not None:
        lattice = [((sx, sy, 11.0), (0.35, 0.35, 22.0), 0) for sx in (-1.6, 1.6) for sy in (-1.6, 1.6)]
        lattice += [((0, sy, z), (3.6, 0.15, 0.15), 0) for sy in (-1.6, 1.6) for z in range(2, 22, 3)]
        lattice += [((0, 0, 25.0), (14.0, 0.5, 7.0), 1)]
        tower_sign = merged_boxes(ctx, "sign_tower", lattice, [ctx.mat("dark_steel", roughness=0.5), ctx.mat("sign_blue", roughness=0.5)], (-front - 4.0, float(spec.get("collapse_y", 24.0)), 0.0))
        wind.topple(ctx, tower_sign, float(spec["collapse"]), duration=1.6, angle=-82.0, axis=1)
    if int(spec.get("fires", 0)) and hasattr(ctx.scene.eevee, "shadow_pool_size"):
        ctx.scene.eevee.shadow_pool_size = "1024"  # fire lights and smoke overflow the default pool
    for i in range(int(spec.get("fires", 0))):
        fx = rng.choice((-1, 1)) * (front + rng.uniform(4, 14))
        fy = rng.uniform(-60, 60)
        la.wind_fire(ctx, f"fire{i}", (fx, fy, 0.5), size=rng.uniform(4.0, 7.0))
        if level > 0:
            camera = spec.get("wind_at")
            wind.embers(ctx, f"embers{i}", (fx - 20.0, fy, 0.0), (60.0, 18.0, 16.0), 260, start=0.0, clear_y=float(camera[1]) if camera else None)
    _storm(ctx, spec)
    ctx.anchor("street", (0.0, 0.0, 2.0))
    return None


# ----- downtown --------------------------------------------------------------------------------------
def la_downtown(ctx, spec):
    """A downtown street canyon of glass and stone towers. Flags: wind, gust_at, wind_at, shatter
    [start, end] (windows burst on the windward faces), broken (share of blown-out panels), night,
    blackout, aftermath, traffic."""
    rng = ctx.rng
    if hasattr(ctx.scene.eevee, "shadow_pool_size"):
        ctx.scene.eevee.shadow_pool_size = "1024"  # hundreds of window panels overflow the default pool
    night = bool(spec.get("night"))
    lit = _lights_material(ctx, night and not spec.get("blackout"))
    la.us_road(ctx, "grand", 600.0, 2, sidewalk=5.0, turn_lane=False)
    la.us_road(ctx, "cross", 300.0, 2, sidewalk=5.0, turn_lane=False, centre=(0.0, 70.0), rot=math.pi / 2)
    box(ctx, "ground", (1200.0, 1200.0, 0.2), (0.0, 0.0, -0.22), ctx.mat("concrete", roughness=0.9), anchor="base")
    broken = float(spec.get("broken", 0.0))
    kinds = ("glass", "stone", "glass", "spire", "glass", "stone", "glass", "cylinder")
    towers = []
    for i, y in enumerate((-200.0, -130.0, -40.0, 140.0, 220.0)):
        for side in (-1, 1):
            w, d, h = rng.uniform(34, 50), rng.uniform(34, 50), rng.uniform(110, 260)
            kind = kinds[(i * 2 + (side > 0)) % len(kinds)]
            if kind == "cylinder":
                w = d = rng.uniform(40, 48)
            x = side * (17.0 + w / 2)
            towers.append(la.tower(ctx, f"tower{i}{side}", (x, y, 0.0), (w, d, h), kind, lit=lit, broken=broken * (1.0 if side < 0 else 0.4), seed=i * 7 + side))
            if spec.get("shatter"):
                t0, t1 = spec["shatter"]
                face = x + w / 2 + 0.3 if side < 0 else x - w / 2 - 0.3
                for k in range(int(spec.get("bursts", 7))):
                    wind.glass_burst(ctx, f"burst{i}{side}_{k}", (face, y + rng.uniform(-d / 2.5, d / 2.5), rng.uniform(8, min(90, h - 10))), (-side * 1.0, 0.0), rng.uniform(t0, t1), count=36, spread=8.0)
    for i in range(int(spec.get("traffic", 6))):
        lane = rng.choice((-5.5, -1.9, 1.9, 5.5))
        vehicles.car(ctx, f"car{i}", (lane, rng.uniform(-150, 150), 0.0), (0.0 if lane > 0 else math.pi) + (rng.uniform(-0.8, 0.8) if spec.get("aftermath") or float(spec.get("wind", 0)) > 0.5 else 0.0), rng.choice(CAR_COLOURS), lit=night and not spec.get("blackout"))
    for i, y in enumerate(range(-240, 240, 30)):
        for side in (-1, 1):
            props.lamp_post(ctx, f"light{i}{side}", (side * 9.4, float(y), 0.16), 8.0, side * math.pi / 2, lit=night and not spec.get("blackout"))
    if spec.get("aftermath"):
        for i in range(80):
            s = rng.uniform(0.6, 3.5)
            box(ctx, f"rubble{i}", (s, s * rng.uniform(0.3, 1.0), s * 0.12), (rng.uniform(-14, 14), rng.uniform(-150, 150), 0.08), ctx.mat(rng.choice(("glass_shard", "stucco_debris", "sheet_metal", "concrete")), roughness=0.5), rot=(0, 0, rng.uniform(0, 3)))
    _storm(ctx, spec, extent=(120.0, 80.0, 40.0))
    ctx.anchor("downtown", (0.0, 0.0, 60.0))
    return None


# ----- freeway -------------------------------------------------------------------------------------
def la_freeway(ctx, spec):
    """A ten-lane freeway with an interchange overhead, sound walls and palms. Flags: wind, gust_at,
    wind_at, traffic, jam, thrown (times), truck_over, aftermath (lanes buried in debris), signs."""
    rng = ctx.rng
    night = bool(spec.get("night"))
    after = bool(spec.get("aftermath"))
    level = float(spec.get("wind", 0.0))
    box(ctx, "ground", (1600.0, 1600.0, 0.2), (0.0, 0.0, -0.22), ctx.mat("dry_grass", roughness=0.95), anchor="base")
    _, half = la.freeway(ctx, "freeway", 900.0, 5)
    la.overpass(ctx, "interchange", (-260.0, 70.0), (260.0, 70.0), z=14.0)
    la.overpass(ctx, "ramp", (-200.0, -40.0), (60.0, 120.0), z=8.0, width=10.0)
    la.freeway_sign(ctx, "sign_a", (half / 2, 30.0, 0.0), str(spec.get("sign", "DOWNTOWN LOS ANGELES")), 0.0, width=12.0)
    la.freeway_sign(ctx, "sign_b", (-half / 2, 38.0, 0.0), "SANTA MONICA", math.pi, width=10.0)
    walls = []
    for side in (-1, 1):
        walls.append(((side * (half + 4.0), 0.0, 2.5), (0.6, 900.0, 5.0), 0))
    merged_boxes(ctx, "sound_walls", walls, [ctx.mat("stucco_sand", roughness=0.9)])
    for i, y in enumerate(range(-400, 400, 24)):
        for side in (-1, 1):
            la.palm(ctx, f"palm{side}_{i}", (side * (half + 9.0), float(y), 0.0), 20.0, level, float(spec.get("gust_at", 0.0)))
    for i in range(40):
        side = rng.choice((-1, 1))
        la.house(ctx, f"house{i}", (side * (half + 30 + rng.uniform(0, 90)), rng.uniform(-400, 400), 0.0), rng.uniform(0, 6), seed=i, roofless=after and rng.random() < 0.5)
    lanes = [-(1.2 + 3.7 * (k + 0.5)) for k in range(5)] + [1.2 + 3.7 * (k + 0.5) for k in range(5)]
    cars = int(spec.get("traffic", 40))
    jam = bool(spec.get("jam")) or level > 0 or after
    for i in range(cars):
        lane = rng.choice(lanes)
        y = rng.uniform(-250, 250)
        heading = 0.0 if lane > 0 else math.pi
        skew = rng.uniform(-0.9, 0.9) if after or level > 0.6 else rng.uniform(-0.05, 0.05)
        if rng.random() < 0.12:
            v = vehicles.lorry(ctx, f"truck{i}", (lane, y, 0.0), heading + skew * 0.3, rng.choice(("white", "red", "navy")), "container", lit=night)
        else:
            v = vehicles.car(ctx, f"car{i}", (lane, y, 0.0), heading + skew, rng.choice(CAR_COLOURS), lit=night)
        if not jam:
            end = y + 22.0 * (ctx.duration + 1.0) * (1 if lane > 0 else -1)
            vehicles.drive(ctx, v, [(lane, y), (lane, end)], 0.0, ctx.duration + 1.0, speed=22.0)
        elif after and rng.random() < 0.3:
            v.rotation_euler = (0.0, math.radians(90), v.rotation_euler.z)
            v.location.z = 0.9
    for i, t in enumerate(spec.get("thrown") or []):
        lane = lanes[(i * 3) % len(lanes)]
        car = vehicles.car(ctx, f"thrown{i}", (lane, float(spec.get("thrown_y", 0.0)) + rng.uniform(-20, 20), 0.0), rng.uniform(-0.2, 0.2), rng.choice(CAR_COLOURS))
        wind.fly(ctx, car, float(t), float(t) + rng.uniform(1.3, 2.0), (-rng.uniform(15, 30), rng.uniform(-8, 8), 0.0), spin=(rng.uniform(0.5, 1.0), rng.uniform(0.75, 1.5), rng.uniform(-0.3, 0.3)), arc=rng.uniform(4, 9))
    if spec.get("truck_over"):
        truck = vehicles.lorry(ctx, "fallen_truck", (lanes[6], float(spec.get("truck_y", 10.0)), 0.0), 0.2, "white", "container", lit=night)
        if float(spec["truck_over"]) > 0:
            wind.topple(ctx, truck, float(spec["truck_over"]), duration=1.0, angle=-88.0, axis=1)
        else:
            truck.rotation_euler = (0.0, -math.radians(88), 0.2)
    if after:
        for i in range(140):
            s = rng.uniform(0.8, 4.0)
            box(ctx, f"rubble{i}", (s, s * rng.uniform(0.3, 1.0), s * rng.uniform(0.1, 0.4)), (rng.uniform(-half, half), rng.uniform(-200, 200), 0.1), ctx.mat(rng.choice(wind.DEBRIS + ("frond", "frond")), roughness=0.9), rot=(rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), rng.uniform(0, 3)))
        for i in range(10):
            la.fallen_palm(ctx, f"fallen{i}", (rng.uniform(-half, half), rng.uniform(-150, 150), 0.0), heading=rng.uniform(0, 6))
    if spec.get("helicopter"):
        heli = vehicles.helicopter(ctx, "rescue", (-10.0, 10.0, 34.0), math.pi / 2, searchlight=False, lit=True)
        key(heli, "location", 1, (-10.0, 10.0, 34.0))
        key(heli, "location", ctx.frames, (-48.0, 16.0, 26.0))
        set_interp(heli, "SINE", "EASE_IN_OUT", path="location")
        heli.rotation_euler = (math.radians(-14.0), math.radians(10.0), math.pi / 2)
        add_noise(heli, "rotation_euler", math.radians(14.0), 1, ctx.frames, scale=9.0)
        add_noise(heli, "location", 2.5, 1, ctx.frames, scale=10.0)
        for i in range(3):
            vehicles.van(ctx, f"ambulance{i}", (half - 2.0, -20.0 + i * 9.0, 0.0), 0.0, "white", "ambulance", lit=True)
    _storm(ctx, spec, extent=(120.0, 90.0, 18.0))
    ctx.anchor("freeway", (0.0, 0.0, 3.0))
    return None


# ----- the hills -------------------------------------------------------------------------------------
HILL = {"axis": "y", "start": 40.0, "end": 520.0, "height": 170.0}


def _hill_z(y):
    return HILL["height"] * smoothstep((y - HILL["start"]) / (HILL["end"] - HILL["start"]))


def la_hills(ctx, spec):
    """Houses on the hillsides above the basin, with the city spread below. Flags: wind, gust_at,
    wind_at, roofs (times), fires, night, blackout, aftermath, debris."""
    rng = ctx.rng
    night = bool(spec.get("night"))
    after = bool(spec.get("aftermath"))
    level = float(spec.get("wind", 0.0))
    lit = _lights_material(ctx, night and not spec.get("blackout"))
    terrain.ground(ctx, "hillside", (1800, 1400), (90, 70), amplitude=6.0, seed=5, material=ctx.mat("chaparral", roughness=0.95), rise=HILL, noise_scale=0.01)
    roofs = list(spec.get("roofs") or [])
    for i in range(70):
        x, y = rng.uniform(-420, 420), rng.uniform(80, 560)
        z = _hill_z(y)
        torn = roofs[i % len(roofs)] + rng.uniform(0, 2.0) if roofs and rng.random() < 0.5 else None
        body, roof = la.house(ctx, f"hill_house{i}", (x, y, z), rng.choice((math.pi, math.pi + 0.3, math.pi - 0.3)), seed=40 + i, lit=lit, roof_torn_at=torn, roofless=after and rng.random() < 0.5)
        multi_box(ctx, f"stilts{i}", [((dx, -6.0, -4.0), (0.4, 0.4, 8.0), 0) for dx in (-5, 0, 5)], [ctx.mat("concrete", roughness=0.8)], (x, y, z))
    for i in range(60):
        x, y = rng.uniform(-500, 500), rng.uniform(60, 600)
        la.palm(ctx, f"hill_palm{i}", (x, y, _hill_z(y)), rng.uniform(14, 20), level, float(spec.get("gust_at", 0.0)))
    # the basin below: low city, freeway and downtown in the haze
    blocks = []
    for gx in range(-30, 31):
        for gy in range(-30, -1):
            if rng.random() < 0.8:
                h = rng.uniform(4, 12)
                blocks.append(((gx * 40.0 + rng.uniform(-6, 6), gy * 40.0, h / 2), (rng.uniform(16, 30), rng.uniform(16, 30), h), rng.randrange(4)))
    merged_boxes(ctx, "basin", blocks, [ctx.mat(c, roughness=0.9) for c in ("stucco_cream", "stucco_sand", "stucco_white", "roof_flat")])
    for i, (x, h) in enumerate(((-140, 220), (-60, 260), (20, 180), (90, 240), (160, 150))):
        la.tower(ctx, f"distant_tower{i}", (x, -1400.0, 0.0), (40, 40, h), "glass", lit=lit, seed=i)
    for i in range(int(spec.get("fires", 0))):
        x, y = rng.uniform(-300, 300), rng.uniform(120, 420)
        la.wind_fire(ctx, f"fire{i}", (x, y, _hill_z(y) + 0.5), size=rng.uniform(5.0, 9.0))
    at = spec.get("wind_at") or (0.0, 150.0)
    if level > 0:
        z = _hill_z(float(at[1]))
        wind.debris(ctx, "debris", (float(at[0]), float(at[1]), z), (160.0, 120.0, 40.0), int(700 * level * float(spec.get("debris", 1.0))), speed=50.0 + 30.0 * level, clusters=20, sizes=(0.4, 2.4), start=float(spec.get("gust_at", 0.0)))
        wind.streaks(ctx, "streaks", (float(at[0]), float(at[1]), z), (220.0, 140.0, 40.0), int(1400 * level), speed=90.0, colour="dust", alpha=0.3, start=float(spec.get("gust_at", 0.0)))
    ctx.anchor("hills", (0.0, 250.0, _hill_z(250.0) + 5.0))
    return None


# ----- the airport -----------------------------------------------------------------------------------
def la_airport(ctx, spec):
    """The airport (runways, terminal, gates) with its arched landmark and palms. Flags: wind,
    gust_at, wind_at, slew (time the parked jets start to swing), aftermath, night."""
    rng = ctx.rng
    level = float(spec.get("wind", 0.0))
    environments_nyc.airport(ctx, {"type": "airport", "birds": 0, "night": bool(spec.get("night"))})
    la.theme_building(ctx, "theme", (140.0, 600.0, 0.0), 0.4)
    for i in range(30):
        la.palm(ctx, f"palm{i}", (-700.0 + i * 48.0, 520.0, 0.0), 18.0, level, float(spec.get("gust_at", 0.0)))
    slew = spec.get("slew")
    if slew is not None:
        for name, obj in list(ctx.objects.items()):
            if name.startswith("gate") and obj.type == "EMPTY":
                rz = obj.rotation_euler.z
                key(obj, "rotation_euler", ctx.frame(float(slew)), (0.0, 0.0, rz))
                key(obj, "rotation_euler", ctx.frame(float(slew) + rng.uniform(2.0, 4.0)), (rng.uniform(-0.05, 0.05), rng.uniform(-0.08, 0.08), rz + rng.uniform(0.3, 0.9)))
                key(obj, "location", ctx.frame(float(slew)))
                obj.location.x -= rng.uniform(4, 16)
                key(obj, "location", ctx.frame(float(slew) + rng.uniform(2.0, 4.0)))
                set_interp(obj, "QUAD", "EASE_OUT")
    for i in range(int(spec.get("carts", 12))):
        cart = box(ctx, f"cart{i}", (1.6, 2.6, 1.2), (rng.uniform(-200, 200), rng.uniform(250, 300), 0.6), ctx.mat(rng.choice(("yellow", "white", "orange")), roughness=0.6))
        if level > 0:
            t = float(spec.get("gust_at", 0.0)) + rng.uniform(0.2, 3.0)
            wind.fly(ctx, cart, t, t + rng.uniform(1.0, 1.8), (-rng.uniform(30, 60), rng.uniform(-10, 10), 0.0), spin=(rng.uniform(0.5, 1.5), rng.uniform(0.5, 1.5), 0.3), arc=rng.uniform(2, 6))
    if spec.get("aftermath"):
        for i in range(90):
            s = rng.uniform(1.0, 5.0)
            box(ctx, f"rubble{i}", (s, s * rng.uniform(0.3, 1.0), s * 0.2), (rng.uniform(-300, 300), rng.uniform(150, 400), 0.15), ctx.mat(rng.choice(wind.DEBRIS), roughness=0.9), rot=(0, 0, rng.uniform(0, 3)))
    _storm(ctx, spec, extent=(220.0, 160.0, 30.0))
    ctx.anchor("apron", (0.0, 320.0, 3.0))
    return None


# ----- the pier --------------------------------------------------------------------------------------
def la_pier(ctx, spec):
    """The beach and pier with its Ferris wheel and coaster, storm surf rolling in. Flags: wind,
    gust_at, wind_at, waves (height), wheel_spin, night, aftermath."""
    rng = ctx.rng
    night = bool(spec.get("night"))
    level = float(spec.get("wind", 0.0))
    box(ctx, "beach", (1400.0, 400.0, 0.4), (0.0, -200.0, -0.4), ctx.mat("beach", roughness=0.95), anchor="base")
    sea = box(ctx, "sea", (2400.0, 1600.0, 0.2), (0.0, 800.0, -0.6), ctx.mat("sea_storm" if level > 0 else "sea_calm", roughness=0.15 if level <= 0 else 0.3))
    ctx.tag("sea", sea)
    la.pier(ctx, "pier", (0.0, -60.0), 340.0, 26.0, 7.0)
    la.ferris_wheel(ctx, "wheel", (12.0, 200.0, 7.0), 26.0, spin=float(spec.get("wheel_spin", 0.05)), rot=0.0, lit=night)
    la.coaster(ctx, "coaster", (-8.0, 236.0, 7.0))
    la.strip_mall(ctx, "arcade", (-12.0, 120.0, 7.0), 4, math.pi / 2, seed=11, lit=_lights_material(ctx, night))
    for i, y in enumerate(range(-50, 270, 20)):
        for side in (-1, 1):
            props.lamp_post(ctx, f"pier_lamp{i}{side}", (side * 12.0, float(y), 7.3), 5.0, -side * math.pi / 2, lit=night)
    for i in range(24):
        la.palm(ctx, f"palm{i}", (-300.0 + i * 26.0, -120.0, 0.0), 20.0, level, float(spec.get("gust_at", 0.0)))
    for i in range(30):
        h = rng.uniform(8, 30)
        buildings.building(ctx, f"front{i}", (-400.0 + i * 28.0, -220.0, 0.0), (22.0, 20.0, h), rng.choice(("white", "cream", "sand")), "flat", 0.0, 60 + i, window=(1.6, 1.8))
    if float(spec.get("waves", 0.0)) > 0:
        wind.surf(ctx, "surf", 30.0, 1400.0, count=7, height=float(spec["waves"]), speed=8.0, start_y=380.0)
        spray = wind.streaks(ctx, "spray", (0.0, 120.0, 4.0), (300.0, 260.0, 24.0), 1500, speed=60.0, colour="foam", alpha=0.45, length=(1.0, 4.0), start=float(spec.get("gust_at", 0.0)))
        spray.name = "spray"
    _storm(ctx, spec, extent=(160.0, 120.0, 30.0))
    ctx.anchor("wheel", (12.0, 200.0, 40.0))
    ctx.anchor("pier", (0.0, 100.0, 8.0))
    return None


# ----- inside: where people shelter -----------------------------------------------------------------
def _room(ctx, name, size, wall="interior_wall", floor="floor_tile", window=None, z=0.0):
    """Walls, floor and ceiling over x in [-w/2, w/2], y in [0, d], z in [0, h]; window = (x0, x1, z0,
    z1) opens the y = d wall."""
    w, d, h = size
    boxes = [((0, d / 2, -0.05), (w + 0.4, d + 0.4, 0.1), 1), ((0, d / 2, h + 0.05), (w + 0.4, d + 0.4, 0.1), 2), ((-w / 2 - 0.1, d / 2, h / 2), (0.2, d + 0.4, h), 0), ((w / 2 + 0.1, d / 2, h / 2), (0.2, d + 0.4, h), 0), ((0, -0.1, h / 2), (w + 0.4, 0.2, h), 0)]
    if window:
        x0, x1, z0, z1 = window
        boxes += [((-(w / 2) + (x0 + w / 2) / 2, d + 0.1, h / 2), (x0 + w / 2, 0.2, h), 0), ((x1 + (w / 2 - x1) / 2, d + 0.1, h / 2), (w / 2 - x1, 0.2, h), 0)]
        if z0 > 0:
            boxes.append((((x0 + x1) / 2, d + 0.1, z0 / 2), (x1 - x0, 0.2, z0), 0))
        if z1 < h:
            boxes.append((((x0 + x1) / 2, d + 0.1, (z1 + h) / 2), (x1 - x0, 0.2, h - z1), 0))
    else:
        boxes.append(((0, d + 0.1, h / 2), (w + 0.4, 0.2, h), 0))
    return multi_box(ctx, name, boxes, [ctx.mat(wall, roughness=0.9), ctx.mat(floor, roughness=0.6), ctx.mat("ceiling_white", roughness=0.9)], (0, 0, z))


def _point(ctx, name, loc, energy, colour=(1.0, 0.85, 0.65), tag=None):
    data = bpy.data.lights.new(name, "POINT")
    data.energy = energy
    data.color = colour
    data.shadow_soft_size = 0.4
    light = bpy.data.objects.new(name, data)
    light.location = loc
    ctx.link(light)
    if tag:
        ctx.tag(tag, light)
    return light


def _outside(ctx, spec, y0, z0=0.0):
    """The world beyond a window: palms, a house opposite, sky, and the storm when it comes."""
    rng = ctx.rng
    level = float(spec.get("wind", 0.0))
    gust = float(spec.get("gust_at", 0.0))
    box(ctx, "yard", (80.0, 60.0, 0.2), (0.0, y0 + 30.0, z0 - 0.4), ctx.mat("lawn", roughness=0.9), anchor="base")
    for i, x in enumerate((-9.0, -2.5, 5.0, 11.0)):
        la.palm(ctx, f"yard_palm{i}", (x + rng.uniform(-1, 1), y0 + rng.uniform(8, 16), z0 - 0.2), rng.uniform(12, 18), level, gust)
    la.house(ctx, "opposite", (0.0, y0 + 34.0, z0 - 0.2), math.pi, seed=91, lit=_lights_material(ctx, bool(spec.get("night")) and not spec.get("blackout")))
    if level > 0:
        wind.debris(ctx, "debris", (0.0, y0 + 10.0, z0), (40.0, 14.0, 8.0), int(260 * level), speed=45.0, clusters=12, sizes=(0.1, 0.9), start=gust)
        wind.streaks(ctx, "streaks", (0.0, y0 + 10.0, z0), (50.0, 16.0, 10.0), int(700 * level), speed=80.0, colour="dust", alpha=0.3, start=gust)


def la_interior(ctx, spec):
    """Where people shelter. kind: living (morning room, sliding door onto palms), office (high floor,
    glass wall that can burst inward at shatter_at), garage (underground car park full of people),
    hallway (windowless; a family on the floor by torchlight), apartment (taped window, the storm
    outside), hospital (corridor on emergency power). Flags: wind, gust_at, night, blackout, people,
    flicker (light flickers), door_open (sunrise beyond an opening door at that time)."""
    rng = ctx.rng
    kind = str(spec.get("kind", "living"))
    night = bool(spec.get("night"))
    if kind == "living":
        w, d, h = 7.0, 5.6, 2.8
        _room(ctx, "room", (w, d, h), window=(-2.6, 2.6, 0.0, 2.4))
        pane = box(ctx, "glass_door", (5.2, 0.03, 2.4), (0.0, d + 0.05, 1.2), ctx.palette.make("door glass", ctx.palette.colour("glass"), roughness=0.05, alpha=0.15))
        pane.visible_shadow = False
        multi_box(ctx, "furniture", [((-2.6, 2.2, 0.25), (1.0, 2.4, 0.5), 0), ((-3.05, 2.2, 0.65), (0.25, 2.4, 0.8), 0), ((2.3, 1.2, 0.45), (2.0, 0.9, 0.9), 1), ((0.4, 2.4, 0.22), (1.1, 0.6, 0.44), 1), ((3.38, 3.4, 1.3), (0.06, 1.6, 0.9), 2)], [ctx.mat("sofa_beige", roughness=0.9), ctx.mat("kitchen_white", roughness=0.4), ctx.palette.emissive("tv alert", "alert_red", 2.5)])
        props.sign_text(ctx, "tv_text", "EXTREME WIND", (3.33, 3.4, 1.35), size=0.12, rot=(math.pi / 2, 0, math.pi / 2), colour="white", emission=2.0)
        for i, (role, x, y, face) in enumerate((("civilian", 1.4, 3.2, -95.0), ("child", 1.0, 2.5, -80.0), ("civilian", 0.2, 3.6, -70.0))[: int(spec.get("people", 3))]):
            actor = characters.build(ctx, {"id": f"family{i}", "role": role, "at": (x, y, 0.0), "face": face})
            characters.animate(ctx, actor, {"action": "idle" if i else "look_around"})
        _outside(ctx, spec, d + 0.2)
        _point(ctx, "lamp", (1.5, 1.0, 2.4), 60.0)
    elif kind == "office":
        w, d, h, z = 22.0, 14.0, 3.2, 120.0
        _room(ctx, "office", (w, d, h), wall="office_wall", floor="carpet_grey", window=(-w / 2, w / 2, 0.0, h), z=z)
        pane = box(ctx, "curtain_wall", (w, 0.04, h), (0.0, d + 0.05, z + h / 2), ctx.palette.make("office glass", ctx.palette.colour("tower_glass"), roughness=0.05, alpha=0.25))
        pane.visible_shadow = False
        desks = []
        for r in range(3):
            for c in range(5):
                x, y = -8.0 + c * 4.0, 3.0 + r * 3.4
                desks += [((x, y, z + 0.74), (1.8, 0.9, 0.05), 0), ((x, y + 0.3, z + 1.0), (0.6, 0.05, 0.4), 1), ((x, y, z + 0.37), (1.6, 0.8, 0.02), 0)]
        merged_boxes(ctx, "desks", desks, [ctx.mat("desk_white", roughness=0.5), ctx.mat("black", roughness=0.4)])
        for i in range(5):
            la.tower(ctx, f"view_tower{i}", (-90.0 + i * 45.0, d + 60.0 + rng.uniform(0, 80), 0.0), (36, 36, rng.uniform(140, 240)), "glass", seed=i)
        shatter = spec.get("shatter_at")
        if shatter is not None:
            key(pane, "hide_render", ctx.frame(float(shatter)) - 1)
            pane.hide_render = True
            key(pane, "hide_render", ctx.frame(float(shatter)))
            for k in range(8):
                wind.glass_burst(ctx, f"inward{k}", (-9.0 + k * 2.6, d - 0.5, z + rng.uniform(1.0, 2.6)), (0.0, -1.0), float(shatter) + rng.uniform(0.0, 0.25), count=40, spread=7.0)
            wind.debris(ctx, "papers", (0.0, d / 2, z + 0.2), (30.0, d, 2.4), 260, speed=24.0, clusters=12, sizes=(0.15, 0.35), kinds=("paper", "paper", "plastic_blue"), start=float(shatter), tumble=2.0)
        for i in range(int(spec.get("people", 8))):
            x, y = rng.uniform(-9, 9), rng.uniform(2, 9)
            actor = characters.build(ctx, {"id": f"worker{i}", "role": rng.choice(("civilian", "shopper")), "at": (x, y, z), "face": 180.0})
            characters.animate(ctx, actor, {"action": rng.choice(("crouch", "crouch", "react")), "start": float(shatter or 0.5) + rng.uniform(0.0, 0.4)})
        _point(ctx, "office_light", (0.0, 5.0, z + 3.0), 400.0, (0.95, 0.97, 1.0), tag="flicker_light")
    elif kind == "garage":
        w, d, h = 40.0, 30.0, 2.7
        _room(ctx, "garage", (w, d, h), wall="concrete", floor="asphalt_la", window=(8.0, 16.0, 0.0, h))
        cols = [((x, y, h / 2), (0.6, 0.6, h), 0) for x in range(-16, 17, 8) for y in range(4, 28, 8)]
        strips = [((x, y, h - 0.05), (2.4, 0.2, 0.06), 1) for x in range(-16, 17, 8) for y in range(2, 29, 6)]
        merged_boxes(ctx, "structure", cols + strips, [ctx.mat("concrete", roughness=0.8), ctx.palette.emissive("strip lights", (0.9, 0.95, 1.0), 3.0)])
        for i in range(10):
            vehicles.car(ctx, f"parked{i}", (-17.0 + (i % 5) * 4.0, 25.0 if i < 5 else 3.0, 0.0), 0.0 if i < 5 else math.pi, rng.choice(CAR_COLOURS))
        for i in range(int(spec.get("people", 34))):
            x, y = rng.uniform(-14, 6), rng.uniform(7, 21)
            actor = characters.build(ctx, {"id": f"sheltering{i}", "role": rng.choice(ROLES), "at": (x, y, 0.0), "face": rng.uniform(0, 360)})
            characters.animate(ctx, actor, {"action": rng.choice(("crouch", "crouch", "idle", "look_around"))})
        for i in range(4):
            data = bpy.data.lights.new(f"garage_light{i}", "AREA")
            data.energy = 140.0
            data.size = 4.0
            light = bpy.data.objects.new(f"garage_light{i}", data)
            light.location = (-12.0 + i * 8.0, 14.0, h - 0.1)
            ctx.link(light)
            ctx.tag("flicker_light", light)
        _outside(ctx, spec, d + 0.2)
    elif kind == "hallway":
        w, d, h = 2.4, 5.0, 2.6
        _room(ctx, "hall", (w, d, h), wall="interior_wall", floor="floor_wood")
        multi_box(ctx, "doors", [((-1.19, 1.5, 1.05), (0.06, 0.9, 2.1), 0), ((1.19, 3.2, 1.05), (0.06, 0.9, 2.1), 0)], [ctx.mat("door_white", roughness=0.6)])
        hinge = box(ctx, "front_door", (0.9, 0.06, 2.1), (-0.45, 4.97, 0.0), ctx.mat("door_white", roughness=0.6))
        hinge.data.transform(Matrix.Translation((0.45, 0.0, 1.05)))  # origin on the hinge, at the floor
        if spec.get("door_open") is not None:
            key(hinge, "rotation_euler", ctx.frame(float(spec["door_open"])), (0.0, 0.0, 0.0))
            key(hinge, "rotation_euler", ctx.frame(float(spec["door_open"]) + 1.2), (0.0, 0.0, math.radians(-100.0)))
            set_interp(hinge, "SINE", "EASE_OUT", path="rotation_euler")
            box(ctx, "doorway_glow", (0.9, 0.05, 2.1), (0.0, 5.25, 1.05), ctx.palette.emissive("sunrise doorway", (1.0, 0.82, 0.58), 6.0))
        blanket = box(ctx, "blanket", (1.8, 1.4, 0.08), (0.0, 2.4, 0.04), ctx.mat("blanket_red", roughness=1.0))
        blanket.visible_shadow = True
        family = [("civilian", -0.5, 2.0, 30.0), ("civilian", 0.45, 2.3, -20.0), ("child", -0.1, 2.9, 180.0), ("child", 0.5, 3.1, 200.0)]
        for i, (role, x, y, face) in enumerate(family[: int(spec.get("people", 4))]):
            actor = characters.build(ctx, {"id": f"family{i}", "role": role, "at": (x, y, 0.0), "face": face})
            characters.animate(ctx, actor, {"action": "crouch"})
        torch = bpy.data.lights.new("torch", "SPOT")
        torch.energy = 260.0
        torch.spot_size = math.radians(70)
        torch.spot_blend = 0.5
        torch.color = (1.0, 0.9, 0.7)
        torch_obj = bpy.data.objects.new("torch", torch)
        torch_obj.location = (0.6, 1.2, 1.1)
        torch_obj.rotation_euler = (Vector((0.0, 2.8, 0.6)) - Vector(torch_obj.location)).to_track_quat("-Z", "Y").to_euler()
        _point(ctx, "lantern", (0.2, 2.6, 0.25), 18.0, (1.0, 0.75, 0.45))
        ctx.link(torch_obj)
        add_noise(torch_obj, "rotation_euler", math.radians(4), 1, ctx.frames, scale=8.0)
        _point(ctx, "ceiling_light", (0.0, 2.5, h - 0.2), 0.0 if spec.get("blackout") else 80.0, tag="flicker_light")
    elif kind == "apartment":
        w, d, h = 6.0, 5.0, 2.7
        _room(ctx, "flat", (w, d, h), window=(-1.4, 1.4, 0.8, 2.3))
        pane = box(ctx, "window_glass", (2.8, 0.03, 1.5), (0.0, d + 0.05, 1.55), ctx.palette.make("flat glass", ctx.palette.colour("glass"), roughness=0.05, alpha=0.2))
        pane.visible_shadow = False
        tape = ctx.mat("tape_tan", roughness=0.8)
        for sign in (-1, 1):
            strip = box(ctx, f"tape{sign}", (3.1, 0.02, 0.07), (0.0, d + 0.03, 1.55), tape, rot=(0.0, sign * math.atan2(1.5, 2.8), 0.0))
            strip.visible_shadow = False
        multi_box(ctx, "flat_furniture", [((-2.2, 1.6, 0.25), (1.0, 2.2, 0.5), 0), ((1.8, 1.0, 0.4), (1.2, 0.7, 0.8), 1)], [ctx.mat("sofa_beige", roughness=0.9), ctx.mat("kitchen_white", roughness=0.5)])
        for i in range(int(spec.get("people", 3))):
            actor = characters.build(ctx, {"id": f"resident{i}", "role": ("civilian", "child", "civilian")[i % 3], "at": (-0.2 + i * 0.75, 2.6 + (i % 2) * 0.35, 0.0), "face": 10.0 - i * 12})
            characters.animate(ctx, actor, {"action": "crouch" if i else "look_around"})
        _outside(ctx, spec, d + 0.2)
        _point(ctx, "candle", (1.2, 0.8, 0.9), 25.0 if night else 0.0, (1.0, 0.65, 0.35), tag="flicker_light")
    elif kind == "hospital":
        w, d, h = 3.6, 34.0, 3.0
        _room(ctx, "corridor", (w, d, h), wall="hospital_wall", floor="floor_tile")
        beds = []
        for i in range(7):
            y = 3.0 + i * 4.4
            beds += [((-1.1, y, 0.55), (0.9, 2.0, 0.12), 0), ((-1.1, y + 0.7, 0.66), (0.6, 0.35, 0.1), 1)]
        merged_boxes(ctx, "beds", beds, [ctx.mat("blanket_blue", roughness=0.9), ctx.mat("white", roughness=0.9)])
        lamps = [((1.75, y, 2.6), (0.05, 0.6, 0.15), 0) for y in range(2, 34, 5)]
        merged_boxes(ctx, "emergency_lamps", lamps, [ctx.palette.emissive("emergency lamp", (1.0, 0.45, 0.2), 6.0)])
        for i, y in enumerate(range(3, 33, 6)):
            _point(ctx, f"emergency{i}", (1.4, float(y), 2.4), 35.0, (1.0, 0.5, 0.25))
        for i in range(int(spec.get("people", 6))):
            role = ("nurse", "doctor", "civilian")[i % 3]
            y = rng.uniform(3, 30)
            actor = characters.build(ctx, {"id": f"staff{i}", "role": role, "at": (rng.uniform(0.2, 1.2), y, 0.0), "face": 0.0 if i % 2 else 180.0})
            characters.animate(ctx, actor, {"action": "walk" if role != "civilian" else "idle", "path": [[actor.root.location.x, y], [actor.root.location.x, y + (5 if i % 2 else -5)]]})
    door = spec.get("door_open")
    if door is not None:
        data = bpy.data.lights.new("sunrise", "AREA")
        data.energy = 0.0
        data.size = 2.0
        data.color = (1.0, 0.8, 0.55)
        sun_light = bpy.data.objects.new("sunrise", data)
        sun_light.location = (0.0, 5.3 if kind == "hallway" else 6.0, 1.2)
        sun_light.rotation_euler = (math.radians(90), 0.0, math.pi)
        ctx.link(sun_light)
        key(data, "energy", ctx.frame(float(door)), 0.0)
        key(data, "energy", ctx.frame(float(door) + 1.5), 900.0)
    ctx.anchor("room", (0.0, 2.5, 1.2))
    return None


# ----- from the air ----------------------------------------------------------------------------------
def la_aerial(ctx, spec):
    """Los Angeles from the air: a flat grid of low stucco blocks and palms, freeways, downtown towers
    and the hills. Flags: wind, gust_at, night, blackout (share of districts dark), fires, smoke,
    aftermath (roofless blocks, debris), dust."""
    rng = ctx.rng
    night = bool(spec.get("night"))
    after = bool(spec.get("aftermath"))
    box(ctx, "land", (12000.0, 12000.0, 0.2), (0.0, 0.0, -0.2), ctx.mat("asphalt_la", roughness=0.95), anchor="base")
    hills = terrain.ground(ctx, "hills", (9000, 3000), (60, 20), amplitude=40.0, seed=9, material=ctx.mat("chaparral", roughness=0.95), rise={"axis": "y", "start": -900.0, "end": 900.0, "height": 420.0}, noise_scale=0.004)
    hills.location.y = 3300.0  # the San Gabriel side of the basin: rises from y 2400 to 4200
    districts = 8
    dark = float(spec.get("blackout", 0.0))
    mats = [ctx.mat(c, roughness=0.9) for c in ("stucco_cream", "stucco_sand", "stucco_white", "stucco_peach", "roof_flat", "roof_tile", "roof_tile_dark", "lawn", "tree_green", "tree_olive")]
    void = ctx.mat("void", roughness=1.0)
    rubble = ctx.mat("stucco_debris", roughness=0.9)
    buckets = [[] for _ in range(districts)]
    lights = [[] for _ in range(districts)]
    cell = 70.0
    roofless = float(spec.get("roofless", 0.4 if after else 0.0))
    for gx in range(-48, 49):
        for gy in range(-40, 34):
            cx, cy = gx * cell + rng.uniform(-4, 4), gy * cell + rng.uniform(-4, 4)
            if abs(cy - 300.0) < 40 or abs(cx - 600.0) < 40:
                continue  # freeway corridors
            if math.hypot(cx, cy - 1200.0) < 260:
                continue  # downtown
            k = int((math.atan2(cy, cx) + math.pi) / math.tau * districts) % districts
            bucket = buckets[k]
            commercial = rng.random() < 0.25
            bucket.append(((cx, cy, 0.05), (cell - 12.0, cell - 12.0, 0.1), 4 if commercial else 7))  # lot: car park or lawns
            for _ in range(rng.choice((2, 3)) if commercial else rng.choice((4, 5, 6))):
                bx, by = cx + rng.uniform(-22, 22), cy + rng.uniform(-22, 22)
                if commercial:
                    w, d, h = rng.uniform(18, 30), rng.uniform(14, 26), rng.uniform(5, 12)
                    roof = 4
                else:
                    w, d, h = rng.uniform(9, 13), rng.uniform(9, 12), 4.0
                    roof = rng.choice((5, 5, 6))
                bucket.append(((bx, by, h / 2), (w, d, h), rng.randrange(4)))
                if after and rng.random() < roofless:
                    bucket.append(((bx, by, h + 0.05), (w * 0.85, d * 0.85, 0.12), 10))  # roof gone: dark shell
                    bucket.append(((bx + rng.uniform(-30, -8), by + rng.uniform(-8, 8), 0.3), (rng.uniform(3, 7), rng.uniform(2, 5), 0.5), 11))
                else:
                    bucket.append(((bx, by, h + 0.6), (w + 0.6, d + 0.6, 1.2), roof))
                if night and rng.random() < 0.5:
                    lights[k].append(((bx + w / 2 + 0.2, by, h * 0.5), (0.3, 2.0, 1.2), 12))
            for _ in range(rng.randint(2, 5)):
                tx, ty = cx + rng.uniform(-30, 30), cy + rng.uniform(-30, 30)
                if after and rng.random() < 0.4:
                    bucket.append(((tx - 6.0, ty, 0.8), (14.0, 1.2, 1.2), 9))  # blown-down tree
                else:
                    s = rng.uniform(4.0, 8.0)
                    bucket.append(((tx, ty, 6.0), (s, s, s * 0.7), rng.choice((8, 9))))
            if night and rng.random() < 0.8:
                lights[k].append(((cx + cell / 2, cy, 8.0), (3.0, 3.0, 1.0), 12))
    for k in range(districts):
        lit = ctx.palette.make(f"district {k} lights", (1.0, 0.72, 0.42), 0.6, 0.0, 0.0 if rng.random() < dark else 7.0) if night else void
        if night:
            ctx.tag(f"district_{k}", lit)
        merged_boxes(ctx, f"district{k}", buckets[k] + lights[k], [*mats, void, rubble, lit])
    traffic = []
    if not night:
        for i in range(500):
            on_ew = rng.random() < 0.5
            lane = rng.uniform(-14, 14)
            pos = rng.uniform(-3200, 3200)
            colour = rng.randrange(4)
            traffic.append(((pos, 300.0 + lane, 1.0), (4.5, 1.9, 1.5), colour) if on_ew else ((600.0 + lane, pos, 1.0), (1.9, 4.5, 1.5), colour))
        merged_boxes(ctx, "freeway_traffic", traffic, [ctx.mat(c, roughness=0.4) for c in ("white", "red", "black", "silver")])
    la.freeway(ctx, "freeway_ew", 7000.0, 5, centre=(0.0, 300.0), rot=math.pi / 2, z=0.3)
    la.freeway(ctx, "freeway_ns", 7000.0, 5, centre=(600.0, 0.0), z=0.3)
    lit = _lights_material(ctx, night and dark < 1.0)
    for i in range(14):
        a = rng.uniform(0, math.tau)
        r = rng.uniform(0, 220)
        kind = ("glass", "stone", "glass", "spire", "cylinder")[i % 5]
        w = rng.uniform(34, 50)
        la.tower(ctx, f"tower{i}", (r * math.cos(a), 1200.0 + r * math.sin(a), 0.0), (w, w if kind == "cylinder" else rng.uniform(34, 50), rng.uniform(110, 300) if i else 330.0), kind, lit=lit, broken=0.5 if after else 0.0, seed=i)
    for i in range(int(spec.get("fires", 0))):
        x, y = rng.uniform(-2500, 2500), rng.uniform(-1800, 2200)
        la.wind_fire(ctx, f"fire{i}", (x, y, 2.0), size=rng.uniform(14.0, 26.0), lean=0.9)
    for i in range(int(spec.get("smoke", 0))):
        x, y = rng.uniform(-2500, 2500), rng.uniform(-200, 2200)  # beyond the aerial cameras, which sit south
        if after:
            wind.plume(ctx, f"haze{i}", (x, y, 0.0), height=rng.uniform(180, 300), drift=(rng.uniform(-700, -400), rng.uniform(-150, 150)))
        else:
            wind.smoke_column(ctx, f"haze{i}", (x, y, 0.0), height=rng.uniform(250, 450), lean=1.0, colour="smoke_light", width=2.5)
    level = float(spec.get("wind", 0.0))
    if level > 0:
        at = spec.get("wind_at") or (0.0, 0.0)
        wind.debris(ctx, "debris", (float(at[0]), float(at[1]), 20.0), (1600.0, 1200.0, 160.0), int(900 * level), speed=120.0, clusters=30, sizes=(1.5, 6.0), start=float(spec.get("gust_at", 0.0)))
        wind.streaks(ctx, "streaks", (float(at[0]), float(at[1]), 10.0), (2400.0, 1600.0, 200.0), int(1600 * level), speed=200.0, colour="dust", alpha=0.25, length=(20.0, 60.0), start=float(spec.get("gust_at", 0.0)))
    ctx.anchor("downtown", (0.0, 1200.0, 120.0))
    return None


BUILDERS = {
    "la_street": la_street,
    "la_downtown": la_downtown,
    "la_freeway": la_freeway,
    "la_hills": la_hills,
    "la_airport": la_airport,
    "la_pier": la_pier,
    "la_interior": la_interior,
    "la_aerial": la_aerial,
}
FOG_EXTENT = {"la_street": (900, 900, 200), "la_downtown": (1200, 1200, 400), "la_freeway": (1600, 1600, 200), "la_hills": (2400, 3200, 500), "la_airport": (3000, 3000, 400), "la_pier": (2400, 2400, 300), "la_interior": (0, 0, 0), "la_aerial": (12000, 12000, 1200)}


def build(ctx, spec):
    return BUILDERS[spec["type"]](ctx, spec)
