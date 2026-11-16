"""Las Vegas environments for the lions production: the Mojave highway at sunrise, the Strip (resorts,
neon, fountain lake, garage, valley districts), a casino floor, and desert variants of the airport and
suburb. Shapes are generic: no real logos or signage."""

from __future__ import annotations

import math

import bpy
from mathutils import noise as mnoise
from mathutils import Vector

from studio.assets import buildings, landmarks, lions, props, terrain, vegetation, vehicles, water
from studio.blender import environments, environments_nyc, lighting
from studio.blender.primitives import box, cone, cylinder, grid, ico, key, mesh_from_pydata, multi_box, set_interp

FOCUS = {"strip": (0.0, 0.0), "fountains": (-60.0, 520.0), "entrance": (-48.0, 250.0), "buffet": (48.0, -20.0), "garage": (95.0, -360.0), "rooftops": (-120.0, 120.0), "valley": (0.0, 0.0), "north": (0.0, 600.0)}
MARQUEES = ("BUFFET", "SHOWS NIGHTLY", "JACKPOTS", "OPEN 24 HOURS", "POOL PARTY", "MAGIC SHOW")


def _glow(name, rgb, strength, alpha):
    """Semi-transparent emission (light beams)."""
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes, links = material.node_tree.nodes, material.node_tree.links
    nodes.clear()
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (*rgb, 1.0)
    emit.inputs["Strength"].default_value = strength
    clear = nodes.new("ShaderNodeBsdfTransparent")
    mix = nodes.new("ShaderNodeMixShader")
    mix.inputs[0].default_value = alpha
    out = nodes.new("ShaderNodeOutputMaterial")
    links.new(clear.outputs[0], mix.inputs[1])
    links.new(emit.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], out.inputs["Surface"])
    material.surface_render_method = "BLENDED"
    return material


def _desert_ground(ctx, name="ground", size=(8000, 8000), amplitude=3.0, seed=21):
    material = ctx.palette.terrain("desert floor", [(-4.0, "soil"), (0.0, "desert_sand"), (6.0, "beach"), (40.0, "mesa"), (160.0, "rock")], noise_mix=0.12)
    return terrain.ground(ctx, name, size, (80, 80), amplitude=amplitude, seed=seed, material=material, noise_scale=0.004)


def ridge(ctx, name, centre, length, width, height, rot=0.0, seed=0):
    """Low-poly mountain ridge along local X (flat-shaded, mesa-banded)."""

    def height_at(x, y):
        across = 1.0 - min(1.0, (y / (width / 2.0)) ** 2)
        along = 1.0 - min(1.0, abs(x) / (length / 2.0)) ** 3
        bumps = 0.65 + 0.35 * mnoise.noise(Vector((x * 0.004 + seed, y * 0.004, 0.0)))
        return max(0.0, height * across * along * bumps)

    material = ctx.palette.terrain(f"{name} rock", [(0.0, "desert_sand"), (height * 0.25, "mesa"), (height * 0.7, "rock"), (height, "stone")], noise_mix=0.1)
    obj = grid(ctx, name, (length, width), (40, 14), material, (centre[0], centre[1], -1.0), height=height_at)
    obj.rotation_euler.z = math.radians(rot)
    return obj


def mountain_ring(ctx, radius=3200.0, height=520.0, seed=3):
    for i in range(8):
        a = math.tau * i / 8 + 0.2
        ridge(ctx, f"range{i}", (radius * math.cos(a), radius * math.sin(a)), 2900.0, 900.0, height * ctx.rng.uniform(0.6, 1.1), math.degrees(a) + 90.0, seed + i)


def joshua_tree(ctx, name, loc, scale=1.0):
    x, y, z = loc
    rng = ctx.rng
    s = scale * rng.uniform(0.8, 1.3)
    boxes = [((0, 0, 1.6 * s), (0.35 * s, 0.35 * s, 3.2 * s), 0)]
    for i in range(rng.randint(2, 4)):
        a = rng.uniform(0, math.tau)
        bx, by, bz = math.cos(a) * 0.9 * s, math.sin(a) * 0.9 * s, (2.6 + rng.uniform(0, 1.0)) * s
        boxes += [((bx * 0.5, by * 0.5, bz - 0.3 * s), (0.25 * s, 0.25 * s, 1.0 * s), 0), ((bx, by, bz + 0.5 * s), (0.25 * s, 0.25 * s, 1.0 * s), 0), ((bx, by, bz + 1.1 * s), (0.75 * s, 0.75 * s, 0.6 * s), 1)]
    multi_box(ctx, name, boxes, [ctx.mat("trunk", roughness=0.95), ctx.mat("leaf_dark", roughness=0.9)], (x, y, z))


def scrub(ctx, name, centre, radius, count, avoid_x=12.0):
    rng = ctx.rng
    boxes = []
    for _ in range(count):
        px, py = rng.uniform(-radius, radius), rng.uniform(-radius, radius)
        if abs(centre[0] + px) < avoid_x:
            continue
        s = rng.uniform(0.6, 1.4)
        boxes.append(((px, py, 0.35 * s), (1.2 * s, 1.1 * s, 0.7 * s), rng.randrange(2)))
    multi_box(ctx, name, boxes, [ctx.mat("grass_dry", roughness=0.95), ctx.mat("leaf_dark", roughness=0.95)], (centre[0], centre[1], 0.0))


def dust_cloud(ctx, name, centre, length=900.0, height=60.0, drift=(0.0, 0.0), count=26):
    rng = ctx.rng
    material = ctx.mat("beach", roughness=1.0, alpha=0.55)
    puffs = []
    for i in range(count):
        px = centre[0] + rng.uniform(-length / 2, length / 2)
        py = centre[1] + rng.uniform(-60, 60)
        r = rng.uniform(height * 0.4, height)
        puff = ico(ctx, f"{name}.{i}", r, (px, py, r * 0.6), material, subdiv=2, scale=(1.6, 1.2, 0.8), smooth=True)
        key(puff, "location", 1)
        puff.location.x += drift[0]
        puff.location.y += drift[1]
        key(puff, "location", ctx.frames)
        set_interp(puff, "LINEAR")
        ctx.tag("dust", puff)
        puffs.append(puff)
    return puffs


def skyline(ctx, centre, lit=None):
    """Distant Strip silhouette for desert shots."""
    rng = ctx.rng
    cx, cy = centre
    boxes = []
    for i in range(22):
        h = rng.uniform(60, 220)
        boxes.append(((rng.uniform(-260, 260), rng.uniform(-80, 80), h / 2), (rng.uniform(25, 60), rng.uniform(20, 45), h), 0))
    multi_box(ctx, "skyline", boxes, [ctx.mat("plaster")], (cx, cy, 0.0))
    cylinder(ctx, "skyline.needle", 7.0, 300.0, (cx + 180.0, cy + 60.0, 0.0), ctx.mat("concrete"), segments=10, anchor="base")
    cylinder(ctx, "skyline.pod", 18.0, 20.0, (cx + 180.0, cy + 60.0, 270.0), ctx.mat("white"), segments=14, anchor="base")
    ico(ctx, "skyline.sphere", 45.0, (cx - 120.0, cy + 20.0, 40.0), lit or ctx.palette.emissive("skyline sphere", "neon_blue", 1.5), subdiv=3, smooth=True)


def mojave(ctx, spec):
    """Highway through the Mojave at sunrise. Flags: truck, dust, hordes, ridge (rigged lions), skyline."""
    rng = ctx.rng
    _desert_ground(ctx)
    for i, (cx, cy, length, height, rot) in enumerate(((-2200, 1800, 2600, 380, 20), (2400, 2200, 3000, 460, -15), (2600, -1200, 2200, 300, 70), (-2600, -1400, 2400, 340, 105), (300, 3400, 3600, 520, 0))):
        ridge(ctx, f"mesa{i}", (cx, cy), length, 700.0, height, rot, i)
    props.road(ctx, "highway", (0.0, -4200.0), (0.0, 4200.0), 11.0, 0.05)
    poles = [((-9.0, -1500.0 + k * 60.0, 5.5), (0.35, 0.35, 11.0), 0) for k in range(60)]
    poles += [((-9.0, -1500.0 + k * 60.0, 10.6), (3.2, 0.25, 0.25), 0) for k in range(60)]
    multi_box(ctx, "power_poles", poles, [ctx.mat("trunk", roughness=0.9)])
    for i in range(70):
        x, y = rng.uniform(-700, 700), rng.uniform(-900, 1400)
        if abs(x) > 18:
            joshua_tree(ctx, f"joshua{i}", (x, y, 0.0), 1.0)
    for i in range(10):
        scrub(ctx, f"scrub{i}", (rng.uniform(-500, 500), rng.uniform(-600, 900)), 120.0, 60)
    for i in range(30):
        ico(ctx, f"rock{i}", rng.uniform(0.8, 3.5), (rng.uniform(-600, 600), rng.uniform(-600, 1200), 0.0), ctx.mat("rock"), subdiv=1, scale=(1.4, 1.0, 0.6))
    if spec.get("skyline", True):
        skyline(ctx, (0.0, -3600.0))
    if spec.get("truck", True):
        truck = vehicles.lorry(ctx, "truck", (2.6, 600.0, 0.05), math.pi, "red", "container", lit=True)
        speed = float(spec.get("truck_speed", 22.0))
        vehicles.drive(ctx, truck, [(2.6, 600.0), (2.6, 600.0 - speed * (ctx.duration + 1.0))], 0.0, ctx.duration + 1.0, speed=speed, z=0.05)
    if spec.get("dust"):
        dust_cloud(ctx, "dust", (900.0, 1500.0), 1600.0, 70.0, drift=(-120.0, -260.0))
    for i in range(int(spec.get("hordes", 0))):
        a = math.radians(rng.uniform(20, 160))
        start = (1700.0 * math.cos(a), 1700.0 * math.sin(a))
        target = (start[0] * 0.25, start[1] * 0.25 - 900.0)
        lions.horde(ctx, f"horde{i}", int(spec.get("horde_size", 700)), start, (220.0, 120.0), path=[start, target], groups=8, speed=12.0)
    ridge_count = int(spec.get("ridge", 0))
    if ridge_count:
        lions.spawn(ctx, {"id": "pride", "count": ridge_count, "area": (60.0, 230.0, 60.0, 30.0), "action": "run", "to": [10.0, 60.0], "jitter": 10.0, "stagger": 1.2, "start": float(spec.get("ridge_start", 0.5)), "speed": 9.0})
    ctx.anchor("truck", (2.6, 600.0, 2.5))
    ctx.anchor("highway", (0.0, 400.0, 1.0))
    ctx.anchor("horizon", (900.0, 1600.0, 40.0))
    ctx.anchor("city", (0.0, -3600.0, 120.0))
    return None


# ----- the Strip ---------------------------------------------------------------------------------
def _resort_slab(ctx, name, loc, size, glass="glass", lit=None, rot=0.0, seed=0, crown=None):
    body = buildings.building(ctx, name, loc, size, "plaster", "flat", rot, seed, glass=glass, window=(2.2, 2.6), floor_height=3.6, door=False, units=False, lit=lit, trim="stone")
    if crown:
        w, d, h = size
        multi_box(ctx, f"{name}.crown", [((0, 0, h + 3), (w * 0.9, d * 0.9, 6), 0), ((0, 0, h + 9), (w * 0.6, d * 0.6, 6), 0), ((0, 0, h + 13), (w * 0.3, d * 0.3, 4), 1)], [ctx.mat("plaster"), crown], loc, (0, 0, rot))
    return body


def y_tower(ctx, name, centre, height=190.0, lit=None, glass="gold_glass"):
    for i in range(3):
        a = math.radians(90 + 120 * i)
        cx, cy = centre[0] + 34.0 * math.cos(a), centre[1] + 34.0 * math.sin(a)
        _resort_slab(ctx, f"{name}.wing{i}", (cx, cy, 0.0), (68.0, 22.0, height - i * 12.0), glass, lit, math.degrees(a) * math.pi / 180.0, 40 + i)
    cylinder(ctx, f"{name}.core", 16.0, height + 8.0, (centre[0], centre[1], 0.0), ctx.mat("plaster"), segments=12, anchor="base")
    ctx.anchor(f"{name}.roof", (centre[0], centre[1], height))


def crescent(ctx, name, centre, radius=140.0, height=150.0, lit=None):
    """Curved tower west of `centre`, concave towards the boulevard."""
    for i in range(7):
        a = math.radians(140 + i * 13.33)
        cx, cy = centre[0] + radius * math.cos(a), centre[1] + radius * math.sin(a)
        _resort_slab(ctx, f"{name}.seg{i}", (cx, cy, 0.0), (52.0, 24.0, height + (12 if i == 3 else 0)), "glass", lit, a + math.pi / 2, 60 + i)
    ctx.anchor(f"{name}.roof", (centre[0] - radius, centre[1], height))


def pyramid(ctx, name, centre, size=150.0, height=105.0, night=False):
    x, y = centre
    h = size / 2
    verts = [(-h, -h, 0), (h, -h, 0), (h, h, 0), (-h, h, 0), (0, 0, height)]
    faces = [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4), (3, 2, 1, 0)]
    mesh_from_pydata(ctx, name, verts, faces, [ctx.mat("glass", roughness=0.15, metallic=0.4)], (x, y, 0.0), bevel=0.4)
    if night:
        beam = cylinder(ctx, f"{name}.beam", 2.5, 2400.0, (x, y, height), _glow(f"{name} beam", (0.85, 0.92, 1.0), 6.0, 0.45), segments=10, anchor="base", radius2=9.0)
        ctx.tag("beam", beam)
    ctx.anchor(f"{name}.top", (x, y, height))


def needle(ctx, name, base, height=330.0, lit=None):
    x, y = base
    cylinder(ctx, name, 9.0, height, (x, y, 0.0), ctx.mat("concrete"), segments=12, anchor="base", radius2=6.0)
    multi_box(ctx, f"{name}.legs", [((sx * 14, sy * 14, 30), (4, 4, 60), 0) for sx in (-1, 1) for sy in (-1, 1)], [ctx.mat("concrete")], (x, y, 0.0))
    cylinder(ctx, f"{name}.pod", 26.0, 24.0, (x, y, height - 30.0), ctx.mat("white"), segments=18, anchor="base", radius2=22.0)
    cylinder(ctx, f"{name}.ring", 27.0, 3.0, (x, y, height - 20.0), lit or ctx.palette.glass(f"{name} glass"), segments=18, anchor="base")
    cone(ctx, f"{name}.spire", 3.0, 60.0, (x, y, height - 6.0), ctx.mat("steel"), segments=8, tip=0.3)
    ctx.anchor(f"{name}.top", (x, y, height))


def sphere_arena(ctx, name, centre, radius=58.0, night=False):
    x, y = centre
    colour = ctx.palette.emissive(f"{name} skin", "neon_blue", 4.0 if night else 1.2)
    orb = ico(ctx, name, radius, (x, y, radius * 0.82), colour, subdiv=3, smooth=True)
    socket = orb.active_material.node_tree.nodes[0].inputs.get("Color") if orb.active_material.node_tree.nodes else None
    if socket is not None and night:
        for f, rgb in ((1, (0.15, 0.55, 1.0, 1)), (ctx.frames // 3, (1.0, 0.25, 0.6, 1)), (2 * ctx.frames // 3, (1.0, 0.75, 0.2, 1)), (ctx.frames, (0.15, 0.55, 1.0, 1))):
            socket.default_value = rgb
            socket.keyframe_insert("default_value", frame=f)
    ctx.tag("sphere", orb)
    ctx.anchor(name, (x, y, radius * 1.6))


def fountain_lake(ctx, name, centre, size=(110.0, 210.0), dancing=True):
    x, y = centre
    w, d = size
    box(ctx, f"{name}.rim", (w + 4, d + 4, 1.2), (x, y, 0.0), ctx.mat("stone"), bevel=0.2, anchor="base")
    lake = water.surface(ctx, name, (w, d), (x, y, 1.0), "pool", divisions=(22, 40), tags=("water", "lake"))
    jet_mat = ctx.palette.water(f"{name} jets", "pool", alpha=0.6, roughness=0.05)
    jets = []
    for i in range(28):
        jy = y - d / 2 + 8 + i * (d - 16) / 27
        jet = cone(ctx, f"{name}.jet{i}", 0.9, 1.0, (x + w / 2 - 10, jy, 1.0), jet_mat, segments=8, tip=0.08)
        jets.append(jet)
        ctx.tag("jet", jet)
        if dancing:
            f = 1
            while f <= ctx.frames:
                t = (f - 1) / ctx.fps
                height = 6.0 + 22.0 * max(0.0, math.sin(t * 1.6 + i * 0.45)) * (0.6 + 0.4 * math.sin(t * 0.4 + i * 0.2))
                key(jet, "scale", f, (1.0, 1.0, max(0.5, height)))
                f += 6
            set_interp(jet, "SINE", "EASE_IN_OUT")
        else:
            jet.scale = (1.0, 1.0, 0.01)
    ctx.anchor(name, (x, y, 2.0))
    return lake


def garage(ctx, name, centre, size=(70.0, 110.0), levels=6, cars=40):
    x, y = centre
    w, d = size
    concrete = ctx.mat("concrete", roughness=0.85)
    boxes = []
    for k in range(levels):
        z = k * 3.4
        boxes.append(((0, 0, z + 0.25), (w, d, 0.5), 0))
        boxes += [((sx * (w / 2 - 0.3), 0, z + 1.2), (0.6, d, 1.0), 0) for sx in (-1, 1)]
        boxes += [((cx, cy, z + 1.9), (0.7, 0.7, 3.4), 0) for cx in (-w / 3, 0, w / 3) for cy in (-d / 3, 0, d / 3)]
    boxes.append(((w / 2 + 4, 0, levels * 1.7), (8, 22, levels * 3.4), 0))
    multi_box(ctx, name, boxes, [concrete], (x, y, 0.0))
    rng = ctx.rng
    for i in range(cars):
        level = rng.randrange(levels)
        vehicles.car(ctx, f"{name}.car{i}", (x + rng.uniform(-w / 2 + 4, w / 2 - 4), y + rng.uniform(-d / 2 + 4, d / 2 - 4), level * 3.4 + 0.5), rng.choice((0.0, math.pi)) + rng.uniform(-0.1, 0.1))
    for level in range(levels):
        ctx.anchor(f"{name}.level{level}", (x, y, level * 3.4 + 0.5))
    ctx.anchor(name, (x, y, levels * 3.4))


def podium(ctx, name, centre, length, facing, lit=None, neon=None, message=None, night=False, seed=0):
    """Casino podium along the boulevard: entrance canopy, neon trim and a marquee (facing +1 east, -1 west)."""
    x, y = centre
    buildings.building(ctx, name, (x, y, 0.0), (36.0, length, 16.0), "cream", "flat", 0.0, seed, window=(0.1, 0.1), door=False, units=False, trim="neon_gold", lit=None)
    front = x + facing * 18.0
    if neon is not None:
        ctx.tag("neon", box(ctx, f"{name}.neon", (0.6, length, 1.0), (front + facing * 0.4, y, 15.0), neon, anchor="base"))
    canopy = box(ctx, f"{name}.canopy", (14.0, 30.0, 1.4), (front + facing * 7.0, y, 7.0), ctx.mat("gold_glass" if seed % 2 else "plaster", roughness=0.3, metallic=0.4), bevel=0.1, anchor="base")
    for sy in (-12, 12):
        cylinder(ctx, f"{name}.col{sy}", 0.6, 7.0, (front + facing * 12.5, y + sy, 0.0), ctx.mat("neon_gold" if night else "stone", emission=2.0 if night else 0.0), segments=8, anchor="base")
    box(ctx, f"{name}.doors", (0.4, 16.0, 5.0), (front + facing * 0.3, y, 0.0), ctx.palette.emissive(f"{name} lobby", (1.0, 0.82, 0.55), 2.5 if night else 0.8), anchor="base")
    if message:
        sign_x = front + facing * 13.0  # on the sidewalk, clear of the traffic lanes
        cylinder(ctx, f"{name}.pylon", 1.2, 14.0, (sign_x, y + length / 2 - 16, 0.0), ctx.mat("dark_steel"), segments=8, anchor="base")
        landmarks.billboard(ctx, f"{name}.marquee", (sign_x, y + length / 2 - 16, 19.0), (16.0, 9.0), math.pi / 2 if facing > 0 else -math.pi / 2, colour=(1.0, 0.86, 0.5), strength=4.5 if night else 2.2, message=message)
        ctx.anchor(f"{name}.marquee", (sign_x, y + length / 2 - 16, 19.0))
    ctx.anchor(f"{name}.entrance", (front + facing * 7.0, y, 1.0))
    return canopy


def valley(ctx, districts=6, night=False, radius=(450.0, 1700.0)):
    """Suburban grid around the Strip split into districts; each district shares one lit-window material."""
    rng = ctx.rng
    for k in range(districts):
        glow = ctx.palette.make(f"district {k} windows", (1.0, 0.72, 0.38), 0.6, 0.0, 2.2 if night else 0.0)
        ctx.tag(f"district_{k}", glow)
        houses = []
        a0, a1 = math.tau * k / districts, math.tau * (k + 1) / districts
        for _ in range(260):
            a = rng.uniform(a0, a1)
            r = rng.uniform(*radius)
            hx, hy = r * math.cos(a), r * math.sin(a)
            if abs(hx) < 330 and abs(hy) < 950:
                continue
            w, d, h = rng.uniform(10, 16), rng.uniform(9, 13), rng.uniform(4, 7)
            houses += [((hx, hy, h / 2), (w, d, h), 0), ((hx, hy, h + 0.6), (w + 1, d + 1, 1.2), 1), ((hx, hy - d / 2 - 0.05, h * 0.45), (w * 0.5, 0.15, 1.2), 2)]
        multi_box(ctx, f"district{k}", houses, [ctx.mat(rng.choice(("cream", "sand", "plaster"))), ctx.mat("terracotta"), glow])
        for i in range(6):
            a = rng.uniform(a0, a1)
            r = rng.uniform(radius[0] + 100, radius[1] - 100)
            props.road(ctx, f"district{k}.road{i}", (r * math.cos(a) - 300 * math.sin(a), r * math.sin(a) + 300 * math.cos(a)), (r * math.cos(a) + 300 * math.sin(a), r * math.sin(a) - 300 * math.cos(a)), 9.0, 0.03, lines=False)


def vegas_strip(ctx, spec):
    """The Strip. Flags: focus, night, lions (0-3), cars (abandoned), tourists, barricades, guard,
    perimeter, helicopters, eyes (night), fountains (dancing jets), closed (marquees say CLOSED)."""
    rng = ctx.rng
    night = bool(spec.get("night", False))
    level = int(spec.get("lions", 0))
    fx, fy = FOCUS[str(spec.get("focus", "strip"))]
    lit = [ctx.palette.make(f"windows lit {i}", (1.0, 0.76, 0.42), 0.5, 0.0, 1.6) for i in range(4)] if night else []
    for material in lit:
        ctx.tag("strip_windows", material)
    pick = (lambda: rng.choice(lit)) if lit else (lambda: None)
    neon = {name: ctx.palette.emissive(f"neon {name}", name, 7.0 if night else 1.5) for name in ("neon_pink", "neon_blue", "neon_gold")}
    for material in neon.values():
        ctx.tag("neon", material)
    _desert_ground(ctx, amplitude=2.0)
    mountain_ring(ctx)
    # boulevard
    for side in (-1, 1):
        props.road(ctx, f"blvd{side}", (side * 11.0, -950.0), (side * 11.0, 950.0), 19.0, 0.05)
        props.pavement(ctx, f"walk{side}", (side * 27.0, 0.0), (10.0, 1900.0), 0.0)
    box(ctx, "median", (3.0, 1900.0, 0.6), (0.0, 0.0, 0.0), ctx.mat("stone"), anchor="base")
    for i, y in enumerate(range(-930, 931, 30)):
        vegetation.palm(ctx, f"mpalm{i}", (0.0, float(y), 0.6), rng.uniform(1.0, 1.3))
        if i % 2 == 0:
            for side in (-1, 1):
                vegetation.palm(ctx, f"spalm{i}{side}", (side * 31.5, float(y) + 15.0, 0.18), rng.uniform(0.9, 1.2))
    for y in range(-900, 901, 60):
        for side in (-1, 1):
            props.lamp_post(ctx, f"blvd_lamp{y}{side}", (side * 22.5, float(y), 0.18), 10.0, math.pi if side > 0 else 0.0, night and abs(y - fy) < 260)
    for i, y in enumerate((-220.0, 380.0)):
        multi_box(ctx, f"bridge{i}", [((0, 0, 9.5), (70.0, 8.0, 1.2), 0), ((0, 3.5, 11.2), (70.0, 0.4, 2.2), 1), ((0, -3.5, 11.2), (70.0, 0.4, 2.2), 1)] + [((sx * 34, 0, 4.5), (4.0, 6.0, 9.0), 0) for sx in (-1, 1)], [ctx.mat("plaster"), ctx.palette.glass("bridge glass")], (0.0, y, 0.0))
    # resorts, west side (x < 0) and east side (x > 0)
    fountain_lake(ctx, "fountains", (-95.0, 520.0), dancing=bool(spec.get("fountains", True)))
    crescent(ctx, "crescent", (-95.0, 520.0), 150.0, 140.0, pick())
    y_tower(ctx, "ytower", (-175.0, 240.0), 190.0, pick())
    podium(ctx, "west_podium", (-58.0, 250.0), 150.0, 1, pick(), neon["neon_gold"], None, night, 1)
    _resort_slab(ctx, "crown", (-150.0, -40.0, 0.0), (90.0, 30.0, 175.0), "glass", pick(), 0.0, 7, neon["neon_pink"])
    podium(ctx, "crown_podium", (-58.0, -40.0), 160.0, 1, pick(), neon["neon_pink"], MARQUEES[3] if not spec.get("closed") else "CLOSED", night, 2)
    pyramid(ctx, "pyramid", (-170.0, -420.0), 150.0, 105.0, night)
    podium(ctx, "pyramid_podium", (-58.0, -420.0), 140.0, 1, pick(), neon["neon_blue"], MARQUEES[5] if not spec.get("closed") else "CLOSED", night, 3)
    needle(ctx, "needle", (180.0, 720.0), 330.0, pick())
    sphere_arena(ctx, "sphere", (190.0, 330.0), 58.0, night)
    for i, (dy, h) in enumerate(((-55.0, 160.0), (15.0, 185.0))):
        _resort_slab(ctx, f"twin{i}", (165.0, dy, 0.0), (36.0, 44.0, h), "gold_glass", pick(), 0.0, 20 + i, neon["neon_gold"])
    buffet = spec.get("marquee") or (MARQUEES[0] if not spec.get("closed") else "CLOSED")
    podium(ctx, "buffet", (58.0, -20.0), 170.0, -1, pick(), neon["neon_gold"], buffet, night, 4)
    podium(ctx, "east_podium", (58.0, 330.0), 150.0, -1, pick(), neon["neon_blue"], MARQUEES[1] if not spec.get("closed") else "CLOSED", night, 5)
    garage(ctx, "garage", (105.0, -360.0), (70.0, 110.0), 6, 34)
    _resort_slab(ctx, "garage_hotel", (190.0, -360.0, 0.0), (40.0, 90.0, 120.0), "glass", pick(), 0.0, 30)
    valley(ctx, int(spec.get("districts", 6)), night and not spec.get("districts_dark"))
    # street life
    if spec.get("cars", True):
        for i in range(int(spec.get("car_count", 26))):
            lane = rng.choice((-17.0, -11.0, -5.0, 5.0, 11.0, 17.0))
            y = fy + rng.uniform(-220, 220)
            rot = (0.0 if lane > 0 else math.pi) + (rng.uniform(-0.9, 0.9) if spec.get("abandoned", True) else rng.uniform(-0.05, 0.05))
            vehicles.car(ctx, f"rental{i}", (lane + rng.uniform(-1.5, 1.5), y, 0.08), rot, rng.choice(("white", "red", "navy", "taxi", "stone", "teal")), lit=night)
    if spec.get("barricades"):
        for i in range(10):  # in front of the west podium doors (front face x = -40) and the buffet doors (x = 40)
            props.barrier(ctx, f"barricade{i}", (-34.0 - (i % 2) * 1.5, 232.0 + i * 3.6, 0.18), math.pi / 2)
            props.barrier(ctx, f"barricade_e{i}", (34.0 + (i % 2) * 1.5, -38.0 + i * 3.6, 0.18), math.pi / 2)
    if spec.get("guard"):
        for i in range(6):
            landmarks.army_truck(ctx, f"army{i}", (-17.0 + (i % 2) * 34.0, fy - 140.0 + (i // 2) * 16.0, 0.08), 0.0 if i % 2 else math.pi, lit=night)
        for i in range(3):
            landmarks.police_car(ctx, f"police{i}", (-5.0 + i * 5.0, fy + 40.0, 0.08), math.pi / 2, lit=night)
    if spec.get("perimeter"):
        for i in range(14):
            props.barrier(ctx, f"perimeter{i}", (-24.0 + i * 3.6, fy - 30.0, 0.08), 0.0)
        for i, x in enumerate((-30.0, -10.0, 10.0, 30.0)):  # behind the barrier line, aimed out at the approach
            floodlight(ctx, f"flood{i}", (x, fy - 22.0, 0.08), (x * 0.5, fy - 110.0, 0.0), night or bool(spec.get("dusk")))
        for i in range(4):
            landmarks.army_truck(ctx, f"perimeter_truck{i}", (-21.0 + i * 14.0, fy - 12.0, 0.08), math.pi / 2, lit=night)
    for i in range(int(spec.get("helicopters", 0))):
        path = spec.get("heli_path") or [[fx - 220.0, fy - 260.0, 95.0], [fx + 60.0, fy + 240.0, 90.0]]
        path = [(p[0] + i * 40.0, p[1] - i * 60.0, p[2] + i * 15.0) for p in path]
        heli = vehicles.helicopter(ctx, f"heli{i}", path[0], 0.0, searchlight=night, lit=True)
        vehicles.drive(ctx, heli, path, 0.0, ctx.duration, z=path[0][2])
    # lions
    if level >= 1:
        lions.spawn(ctx, {"id": "street_pride", "count": 8 + 6 * level, "area": (fx, fy - 60.0, 30.0, 40.0), "action": spec.get("lion_action", "walk"), "to": [fx, fy + 140.0], "jitter": 8.0, "stagger": 2.0, "roar_chance": 0.15})
    if level >= 2:
        for i in range(3):
            lane = rng.choice((-14.0, 14.0))
            lions.horde(ctx, f"blvd_horde{i}", 260, (lane, fy - 260.0 - i * 160.0), (26.0, 140.0), path=[(lane, fy - 260.0 - i * 160.0), (lane, fy + 500.0)], groups=5, speed=9.0)
    if level >= 3 or spec.get("rooftops"):
        points = []
        for roof in ("west_podium", "crown_podium", "buffet", "east_podium", "pyramid_podium"):
            obj = bpy.data.objects.get(roof)
            if obj is not None:
                points += [(obj.location.x + rng.uniform(-14, 14), obj.location.y + rng.uniform(-60, 60), 16.75) for _ in range(14)]
        points += [(105.0 + rng.uniform(-30, 30), -360.0 + rng.uniform(-50, 50), 6 * 3.4 + 0.5) for _ in range(18)]
        lions.resting(ctx, "rooftop_lions", points, 1.0)
    for i in range(int(spec.get("valley_hordes", 0))):
        a = math.tau * i / max(1, int(spec.get("valley_hordes", 0))) + 0.3
        start, end_point = (2300.0 * math.cos(a), 2300.0 * math.sin(a)), (900.0 * math.cos(a), 900.0 * math.sin(a))
        lions.horde(ctx, f"valley_horde{i}", 600, start, (260.0, 160.0), path=[start, end_point], groups=6, speed=12.0)
    if night and spec.get("eyes"):
        pts = []
        for _ in range(int(spec.get("eye_count", 2600))):
            a = rng.uniform(0, math.tau)
            r = rng.uniform(1700, 2600)
            pts.append((r * math.cos(a), r * math.sin(a), 1.1))
        lions.eyes(ctx, "eyes", pts, float(spec.get("eye_strength", 40.0)), float(spec.get("eye_size", 0.3)))
    for name, (ax, ay) in FOCUS.items():
        ctx.anchor(name, (ax, ay, 2.0))
    ctx.anchor("sphere_top", (190.0, 330.0, 100.0))
    ctx.anchor("pyramid_top", (-170.0, -420.0, 105.0))
    return None


def floodlight(ctx, name, loc, target, on=True):
    x, y, z = loc
    multi_box(ctx, name, [((0, 0, 4.5), (0.4, 0.4, 9.0), 0), ((0, 0, 9.2), (2.4, 0.6, 1.2), 1), ((0, 0, 0.6), (2.6, 2.0, 1.2), 0)], [ctx.mat("dark_steel"), ctx.palette.emissive(f"{name} lamp", (1.0, 0.97, 0.9), 12.0 if on else 0.0)], (x, y, z))
    if on:
        data = bpy.data.lights.new(f"{name}.spot", "SPOT")
        data.energy = 60000.0
        data.spot_size = math.radians(70)
        data.spot_blend = 0.4
        light = bpy.data.objects.new(f"{name}.spot", data)
        light.location = (x, y, z + 9.6)
        light.rotation_euler = (Vector(target) - Vector(light.location)).to_track_quat("-Z", "Y").to_euler()
        ctx.link(light)


# ----- interiors and desert variants ----------------------------------------------------------------
def casino_floor(ctx, spec):
    """Casino floor: carpet, slot banks, tables, chandeliers and a glass frontage onto the street."""
    carpet = ctx.palette.cracked("casino carpet", "carpet", "neon_gold", 1.6)
    box(ctx, "floor", (70.0, 50.0, 0.1), (0.0, 0.0, -0.1), carpet, anchor="base")
    box(ctx, "ceiling", (70.0, 50.0, 0.3), (0.0, 0.0, 7.0), ctx.mat("roof_dark"), anchor="base")
    box(ctx, "back_wall", (70.0, 0.4, 7.0), (0.0, 25.0, 0.0), ctx.mat("carpet", roughness=0.8), anchor="base")
    for sx in (-1, 1):
        box(ctx, f"side_wall{sx}", (0.4, 50.0, 7.0), (sx * 35.0, 0.0, 0.0), ctx.mat("carpet", roughness=0.8), anchor="base")
    box(ctx, "frontage", (70.0, 0.3, 6.2), (0.0, -25.0, 0.0), ctx.palette.glass("frontage glass"), anchor="base")
    multi_box(ctx, "mullions", [((x, 0, 3.1), (0.3, 0.4, 6.2), 0) for x in range(-34, 35, 6)], [ctx.mat("neon_gold", roughness=0.4, metallic=0.6)], (0.0, -25.0, 0.0))
    box(ctx, "street", (90.0, 30.0, 0.1), (0.0, -40.0, -0.1), ctx.mat("pavement"), anchor="base")
    props.road(ctx, "street_road", (-45.0, -47.0), (45.0, -47.0), 12.0, 0.02)
    for i, x in enumerate((-30.0, -12.0, 8.0, 26.0)):
        vegetation.palm(ctx, f"palm{i}", (x, -31.0, 0.0), 1.0)
    box(ctx, "daylight", (200.0, 1.0, 120.0), (0.0, -120.0, 0.0), ctx.palette.emissive("sky outside", (0.85, 0.9, 1.0), 2.5), anchor="base")
    screens = [ctx.palette.emissive(f"slot screen {c}", c, 3.0) for c in ("neon_pink", "neon_blue", "neon_gold")]
    for row in range(5):
        for side in (-1, 1):
            boxes, glow = [], []
            for k in range(9):
                x = side * (6.0 + k * 2.2)
                y = -12.0 + row * 7.0
                boxes += [((x, y, 0.6), (1.6, 1.2, 1.2), 0), ((x, y - 0.2, 1.6), (1.4, 0.9, 0.9), 1), ((x, y, 2.3), (1.0, 0.5, 0.4), 0)]
                glow.append(((x, y - 0.66, 1.65), (1.1, 0.05, 0.7), 2 + (k + row) % 3))
            multi_box(ctx, f"slots{row}{side}", boxes + glow, [ctx.mat("dark_steel", roughness=0.4, metallic=0.5), ctx.mat("black"), *screens])
    for i, (x, y) in enumerate(((-4.0, -16.0), (4.0, -8.0), (-4.0, 4.0), (4.0, 12.0))):
        cylinder(ctx, f"table{i}", 1.8, 0.9, (x, y, 0.0), ctx.mat("felt", roughness=0.9), segments=16, anchor="base", bevel=0.1)
        cylinder(ctx, f"table{i}.rim", 1.95, 0.2, (x, y, 0.85), ctx.mat("trunk"), segments=16, anchor="base")
    for i, (x, y) in enumerate(((-18.0, -8.0), (18.0, -8.0), (-18.0, 12.0), (18.0, 12.0), (0.0, 2.0))):
        ico(ctx, f"chandelier{i}", 1.6, (x, y, 5.6), ctx.palette.emissive(f"chandelier {i}", (1.0, 0.85, 0.6), 8.0), subdiv=1)
        lighting.area_light(ctx, f"chandelier{i}.light", (x, y, 6.6), 1400.0, 5.0, (1.0, 0.82, 0.6))
    for x in (-24.0, 24.0):
        for y in (-16.0, 0.0, 16.0):
            cylinder(ctx, f"column{x}{y}", 0.8, 7.0, (x, y, 0.0), ctx.mat("neon_gold", roughness=0.35, metallic=0.7), segments=12, anchor="base")
    ctx.anchor("floor", (0.0, 0.0, 1.2))
    ctx.anchor("doors", (0.0, -24.0, 1.4))
    ctx.anchor("street", (0.0, -40.0, 1.0))
    ctx.anchor("slots", (10.0, -5.0, 1.4))
    return None


def desert_airport(ctx, spec):
    """The airport environment re-dressed for the desert, with lions on the runways."""
    environments_nyc.airport(ctx, {k: v for k, v in spec.items() if k != "type"} | {"birds": 0})
    ground = bpy.data.objects.get("ground")
    if ground is not None:
        ground.data.materials[0] = ctx.palette.terrain("airport desert", [(-1.0, "soil"), (0.0, "desert_sand"), (3.0, "beach")])
    mountain_ring(ctx, 2600.0, 420.0, 7)
    rng = ctx.rng
    level = int(spec.get("lions", 2))
    lions.resting(ctx, "runway_lions", [(rng.uniform(-600, 600), -150.0 + rng.uniform(-18, 18), 0.05) for _ in range(90 * level)], 1.0)
    lions.horde(ctx, "airport_horde", 500 * level, (-200.0, 90.0), (500.0, 80.0), path=[(-700.0, 120.0), (300.0, 40.0)], groups=6, speed=10.0)
    return None


def desert_suburb(ctx, spec):
    """The residential street re-dressed for the Las Vegas valley."""
    environments.residential_street(ctx, {k: v for k, v in spec.items() if k != "type"})
    ground = bpy.data.objects.get("ground")
    if ground is not None:
        ground.data.materials[0] = ctx.palette.terrain("suburb desert", [(-1.0, "soil"), (0.0, "desert_sand"), (2.0, "beach")])
    for i in range(3):
        ridge(ctx, f"ridge{i}", (-900.0 + i * 900.0, 1400.0), 1600.0, 600.0, 320.0, 0.0, i)
    return None


BUILDERS = {"mojave": mojave, "vegas_strip": vegas_strip, "casino_floor": casino_floor, "desert_airport": desert_airport, "desert_suburb": desert_suburb}
FOG_EXTENT = {"mojave": (9000, 9000, 700), "vegas_strip": (7000, 7000, 700), "casino_floor": (0, 0, 0), "desert_airport": (6000, 6000, 500), "desert_suburb": (3000, 3000, 400)}


def build(ctx, spec):
    return BUILDERS[spec["type"]](ctx, spec)
