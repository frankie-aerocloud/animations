"""Environments for "The Day The World Stopped Making Plastic": the plastics plant and its halls
(running, halting, dark, restarting), clean-ups on beaches, rivers and streets, an Indonesian
waterway, an Indian storm drain, the ocean above and below the surface, and the rooms where
companies, shops, labs, hospitals, councils and households rethink plastic.

Coordinates are metres. Production lines run along X; machine fronts face -Y. Shores and rivers
lie toward +Y. Timed flags are seconds from the start of the shot."""

from __future__ import annotations

import math
import random

import bpy
from mathutils import Vector

from studio.assets import birds, buildings, characters, plastic, props, terrain, vegetation, vehicles
from studio.assets.meshes import merged_boxes
from studio.blender.primitives import add_noise, box, cylinder, empty, fcurves, grid, ico, key, parent

ROLES = ("civilian", "shopper", "civilian", "child")
VOLUNTEERS = ("civilian", "shopper", "civilian", "civilian", "child")
HUTS = ("hut_blue", "hut_yellow", "hut_red", "hut_mint", "hut_pink", "hut_navy", "hut_white")
FACADES = ("facade_pink", "facade_turquoise", "facade_yellow", "facade_cream", "facade_green", "facade_blue", "facade_white", "facade_ochre")


# ----- shared pieces -------------------------------------------------------------------------------
def _light(ctx, name, kind, loc, energy, colour=(1.0, 0.95, 0.88), size=0.4, target=None, angle=60.0):
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


def _energy(ctx, light, points):
    """Hold a light's energy at (seconds, value) points (constant between them)."""
    for seconds, value in points:
        light.data.energy = value
        light.data.keyframe_insert("energy", frame=ctx.frame(seconds))
    for curve in fcurves(light.data, "energy"):
        for point in curve.keyframe_points:
            point.interpolation = "CONSTANT"


def _switch(ctx, lights, materials, on=True, off_window=None, on_window=None, seed=3):
    """Lights (with their glowing fittings) going off one after another across off_window =
    [start, end], or coming on across on_window; otherwise simply on, or off."""
    order = list(range(len(lights)))
    random.Random(seed).shuffle(order)
    for rank, i in enumerate(order):
        light, material = lights[i], materials[i]
        energy = light.data.energy
        if off_window or on_window:
            start, end = off_window or on_window
            t = start + (end - start) * rank / max(1, len(order) - 1)
            _energy(ctx, light, [(0.0, energy if off_window else 0.0), (t, 0.0 if off_window else energy)])
            plastic.glow(ctx, material, [(0.0, 6.0 if off_window else 0.0), (t, 0.0 if off_window else 6.0)])
        elif not on:
            light.data.energy = 0.0
            plastic.glow(ctx, material, [(0.0, 0.0)])


def _people(ctx, name, spots, roles=ROLES, action="idle", start=0.0, face_at=None, props_for=None):
    """People at (x, y, facing degrees) spots, or (x, y, facing, z); `props_for(actor, i)` may hand
    them something to carry. `action` may be a list, used in turn."""
    rng = ctx.rng
    actors = []
    for i, spot in enumerate(spots):
        x, y, face = spot[:3]
        z = spot[3] if len(spot) > 3 else 0.0
        actor = characters.build(ctx, {"id": f"{name}{i}", "role": roles[i % len(roles)] if isinstance(roles, list) else rng.choice(roles), "at": (x, y, z), "face": face})
        if props_for:
            props_for(actor, i)
        what = action if isinstance(action, str) else action[i % len(action)]
        spec = {"action": what, "start": start + rng.uniform(0.0, 0.5)}
        if face_at and what not in ("walk", "gather"):
            spec["face_at"] = face_at
        if what in ("walk", "gather"):
            heading = math.radians(face + 90.0)
            dist = rng.uniform(2.0, 4.0) if what == "gather" else rng.uniform(4.0, 7.0)
            spec["path"] = [[x, y], [x + math.cos(heading) * dist, y + math.sin(heading) * dist]]
        characters.animate(ctx, actor, spec)
        actors.append(actor)
    return actors


def _room(ctx, name, size, wall="hall_panel", floor="floor_epoxy", ceiling="ceiling_white", z=0.0):
    """Floor, ceiling and four walls over x in [-w/2, w/2], y in [-d/2, d/2], z in [0, h]."""
    w, d, h = size
    boxes = [((0, 0, -0.05), (w + 0.4, d + 0.4, 0.1), 1), ((0, 0, h + 0.05), (w + 0.4, d + 0.4, 0.1), 2), ((-w / 2 - 0.1, 0, h / 2), (0.2, d + 0.4, h), 0), ((w / 2 + 0.1, 0, h / 2), (0.2, d + 0.4, h), 0), ((0, -d / 2 - 0.1, h / 2), (w + 0.4, 0.2, h), 0), ((0, d / 2 + 0.1, h / 2), (w + 0.4, 0.2, h), 0)]
    return merged_boxes(ctx, name, boxes, [ctx.mat(wall, roughness=0.85), ctx.mat(floor, roughness=0.5), ctx.mat(ceiling, roughness=0.9)], (0.0, 0.0, z))


def _water(ctx, name, size, loc, colour, waves=0.15, width=8.0, divisions=None):
    """A water surface in a production colour, with gentle moving waves."""
    divisions = divisions or (max(4, min(400, int(size[0] / 6))), max(4, min(400, int(size[1] / 6))))
    obj = grid(ctx, name, size, divisions, ctx.palette.water(f"{name} water", colour), loc)
    if waves > 0:
        wave = obj.modifiers.new("Wave", "WAVE")
        wave.height = waves
        wave.width = width
        wave.narrowness = 1.4
        wave.speed = 0.2
        wave.start_position_x = ctx.rng.uniform(-40, 40)
        wave.start_position_y = ctx.rng.uniform(-40, 40)
    return obj


def _held(ctx, kind):
    """Something for a volunteer to carry: a sack, a bucket or a jar."""

    def give(actor, i):
        what = kind if isinstance(kind, str) else kind[i % len(kind)]
        if what == "sack":
            plastic.held_sack(ctx, actor, plastic.SACKS[i % len(plastic.SACKS)])
        elif what == "jar":
            jar = cylinder(ctx, f"{actor.id}.jar", 0.07, 0.2, (0, 0, 0), ctx.mat("jar_glass", roughness=0.08, alpha=0.5), segments=12, anchor="base")
            plastic.hold(actor, jar, (0.0, 0.3, -0.1))
        elif what in ("bucket", "box", "bottle"):
            actor.prop = props.held(ctx, f"{actor.id}.prop", what)
            parent(actor.prop, actor.torso)
            actor.prop.location = (0.0, 0.30, 0.02)

    return give


# ----- the plant -----------------------------------------------------------------------------------
def _steam(ctx, name, top, size=5.0, stop_at=None, restart_at=None):
    """A rising plume of white process steam; it thins away from stop_at (or returns at restart_at)."""
    holder = empty(ctx, name, top)
    material = ctx.mat("steam", roughness=1.0, alpha=0.8)
    rise = size * 10.0
    for i in range(8):
        puff = ico(ctx, f"{name}.{i}", size, (0.0, 0.0, 0.0), material, subdiv=2, scale=(1.3, 1.0, 0.8), smooth=True)
        puff.visible_shadow = False
        parent(puff, holder)
        plastic.cycle(ctx, puff, "location", [(0.0, 0.0, 0.0), (size * 2.5, 0.0, rise)], 8.0, i / 8, closed=False)
        plastic.cycle(ctx, puff, "scale", [(0.4, 0.4, 0.4), (1.2, 1.2, 1.1), (2.0, 2.0, 1.7), (0.01, 0.01, 0.01)], 8.0, i / 8, closed=False)
    if stop_at is not None or restart_at is not None:
        t = restart_at if restart_at is not None else stop_at
        a, b = (0.001, 1.0) if restart_at is not None else (1.0, 0.001)
        holder.scale = (a, a, a)
        holder.keyframe_insert("scale", frame=1)
        holder.keyframe_insert("scale", frame=max(1, ctx.frame(t)))
        holder.scale = (b, b, b)
        holder.keyframe_insert("scale", frame=ctx.frame(t + 3.0))
    return holder


def _plant(ctx, name, origin, night, lit, stop_at=None, restart_at=None, steam=True):
    """One plastics works: production halls, pellet silos, a process tower, stacks with steam, a
    pipe rack and lorries at the loading bays."""
    ox, oy = origin
    for i, (x, y, w, d, h) in enumerate(((-60, 40, 90, 40, 14), (-60, 96, 90, 30, 12), (62, 100, 70, 36, 14))):
        buildings.warehouse(ctx, f"{name}.hall{i}", (ox + x, oy + y, 0.0), (w, d, h), 0.0, "hall_panel")
        material = lit[i % len(lit)] if lit else ctx.mat("glass_dark", roughness=0.2)
        strips = [((ox + x + sx, oy + y - d / 2 - 0.15, h * 0.62), (6.0, 0.2, 1.6), 0) for sx in range(int(-w / 2 + 5), int(w / 2 - 4), 9)]
        merged_boxes(ctx, f"{name}.windows{i}", strips, [material])
    plastic.sign(ctx, f"{name}.sign", "POLYMER WORKS", (ox - 60.0, oy + 19.7, 10.5), size=3.0, colour="sign_white")
    for i in range(10):
        x, y = ox + 22.0 + (i % 5) * 15.0, oy + (18.0, 34.0)[i // 5]
        cylinder(ctx, f"{name}.silo{i}", 4.0, 26.0, (x, y, 0.0), ctx.mat("silo_white", roughness=0.4), segments=18, anchor="base")
        cylinder(ctx, f"{name}.silo{i}.cap", 4.0, 3.0, (x, y, 26.0), ctx.mat("silo_white", roughness=0.4), segments=18, anchor="base", radius2=0.6)
    merged_boxes(ctx, f"{name}.catwalk", [((ox + 52.0, oy + 26.0, 27.5), (66.0, 2.0, 0.3), 0)] + [((ox + 22.0 + k * 15.0, oy + 26.0, 13.75), (0.4, 0.4, 27.5), 0) for k in range(5)], [ctx.mat("steel_dark", roughness=0.5)])
    tower = [((ox + 130 + sx, oy + 30 + sy, 22.0), (0.6, 0.6, 44.0), 0) for sx in (-6, 6) for sy in (-6, 6)]
    tower += [((ox + 130, oy + 30, z), (13.0, 13.0, 0.4), 1) for z in (8, 16, 24, 32, 40)]
    merged_boxes(ctx, f"{name}.tower", tower, [ctx.mat("safety_yellow", roughness=0.5), ctx.mat("steel_dark", roughness=0.5)])
    for i, (dx, dy, r, h) in enumerate(((-2.5, -2.5, 1.6, 34.0), (3.0, 2.0, 1.2, 28.0), (2.0, -3.0, 0.9, 40.0))):
        cylinder(ctx, f"{name}.vessel{i}", r, h, (ox + 130 + dx, oy + 30 + dy, 0.0), ctx.mat("steel_light", roughness=0.3, metallic=0.6), segments=14, anchor="base")
    for i, (x, y, h) in enumerate(((150.0, 64.0, 58.0), (164.0, 64.0, 50.0))):
        cylinder(ctx, f"{name}.stack{i}", 2.6, h, (ox + x, oy + y, 0.0), ctx.mat("concrete", roughness=0.8), segments=16, anchor="base", radius2=1.9)
        cylinder(ctx, f"{name}.stack{i}.band", 2.05, 2.0, (ox + x, oy + y, h - 4.0), ctx.mat("red", roughness=0.6), segments=16, anchor="base")
        if steam:
            _steam(ctx, f"{name}.steam{i}", (ox + x, oy + y, h + 2.0), 7.0, stop_at, restart_at)
    rack = [((ox + x, oy + 4.0, 8.0), (0.5, 6.0, 0.5), 0) for x in range(-100, 141, 12)] + [((ox + x, oy + 4.0, 4.0), (0.4, 0.4, 8.0), 0) for x in range(-100, 141, 12)]
    rack += [((ox + 20.0, oy + 4.0 + dy, 8.6), (240.0, 0.7, 0.7), 1 + (k % 2)) for k, dy in enumerate((-2.0, -0.8, 0.4, 1.6))]
    merged_boxes(ctx, f"{name}.rack", rack, [ctx.mat("steel_dark", roughness=0.5), ctx.mat("steel_light", roughness=0.3, metallic=0.6), ctx.mat("pipe_green", roughness=0.5)])
    for i in range(5):
        vehicles.lorry(ctx, f"{name}.lorry{i}", (ox - 96.0 + i * 9.0, oy + 12.0, 0.05), 0.0, ("white", "navy", "red", "teal", "white")[i], ("container", "tanker", "container", "flatbed", "container")[i], lit=night)


def plastic_plant(ctx, spec):
    """A plastics works beside a river, or a district of them along it (district: n) for the wide
    shots. Flags: night, lit (windows glowing by day), lights_off [start, end] (a wave of windows
    going dark), stop_at (the steam thins away, plant by plant), stopped (no steam), restart_at
    (the steam returns), birds (a flock crossing)."""
    night = bool(spec.get("night"))
    stopped = bool(spec.get("stopped"))
    stop_at = spec.get("stop_at")
    restart_at = spec.get("restart_at")
    count = int(spec.get("district", 1))
    box(ctx, "land", (12000.0, 6000.0, 0.2), (0.0, 2895.0, -0.2), ctx.mat("field_green", roughness=0.95), anchor="base")
    box(ctx, "riverbed", (12000.0, 140.0, 0.2), (0.0, -170.0, -3.0), ctx.mat("bank_mud", roughness=0.95), anchor="base")
    _water(ctx, "river", (12000.0, 130.0), (0.0, -170.0, -0.4), "river_plant", 0.05, 6.0, (400, 6))
    box(ctx, "bank", (12000.0, 14.0, 0.3), (0.0, -111.0, -0.25), ctx.mat("bank_mud", roughness=0.95), anchor="base")
    box(ctx, "far_bank", (12000.0, 4000.0, 0.2), (0.0, -2225.0, -0.2), ctx.mat("field_green", roughness=0.95), anchor="base")
    lit = [ctx.palette.make(f"plant windows {i}", ctx.palette.colour("window_warm"), 0.5, 0.0, 5.0) for i in range(4)] if night or spec.get("lit") else []
    centres = [(p - (count - 1) / 2) * 460.0 for p in range(count)]
    for p, ox in enumerate(centres):
        box(ctx, f"yard{p}", (380.0, 230.0, 0.1), (ox + 30.0, 30.0, 0.0), ctx.mat("yard_concrete", roughness=0.85), anchor="base")
        delay = (p - (count - 1) / 2) * 0.5
        _plant(ctx, f"plant{p}", (ox, 0.0), night, lit, None if stop_at is None else max(0.0, float(stop_at) + delay), None if restart_at is None else float(restart_at) + delay, steam=not stopped)
        props.fence(ctx, f"fence{p}", (ox - 160, -86), (ox + 220, -86), 0.0, 2.4, 8.0)
        for i in range(6):
            props.lamp_post(ctx, f"lamp{p}_{i}", (ox - 120.0 + i * 60.0, -70.0, 0.0), 10.0, 0.0, night)
    vegetation.scatter_trees(ctx, "trees", (0.0, 600.0, 0.0), 1400.0, 260, avoid=[(ox - 180.0, -100.0, ox + 240.0, 160.0) for ox in centres] + [(-9000.0, -9000.0, 9000.0, -95.0)])
    if spec.get("lights_off") and lit:
        start, end = (float(v) for v in spec["lights_off"])
        for k, material in enumerate(lit):
            plastic.glow(ctx, material, [(0.0, 5.0), (start + (end - start) * k / max(1, len(lit) - 1), 0.0)])
    if spec.get("birds"):
        birds.flock(ctx, "birds", int(spec["birds"]), (-150.0, -60.0, 45.0), (30.0, 18.0, 6.0), path=[(-150.0, -60.0, 45.0), (250.0, 140.0, 75.0)], speed=12.0, scale=1.6)
    ctx.anchor("plant", (0.0, 40.0, 10.0))
    return None


# ----- the halls -----------------------------------------------------------------------------------
def _hall_lights(ctx, w, d, h, spec):
    lights, materials = [], []
    dim = float(spec.get("lamps", 1.0))
    for i, x in enumerate(range(int(-w / 2 + 8), int(w / 2 - 4), 12)):
        for j, y in enumerate((-d / 4, d / 4)):
            material = ctx.palette.emissive(f"high bay {i}{j}", "lamp_white", 6.0 * dim)
            cylinder(ctx, f"bay{i}{j}", 0.45, 0.25, (x, y, h - 1.4), material, segments=12)
            materials.append(material)
            lights.append(_light(ctx, f"bay_light{i}{j}", "AREA", (x, y, h - 1.6), 650.0 * dim, size=3.0))
    off, on = spec.get("lights_off"), spec.get("lights_on")
    _switch(ctx, lights, materials, not spec.get("dark"), [float(v) for v in off] if off else None, [float(v) for v in on] if on else None)


def _line(ctx, name, y, kind, status, stop_at, restart_at, speed=0.45):
    """One production line along X at y: a feeding machine, a belt of products through a machine
    part way along, and a packing machine at the end that swallows the stream."""
    plastic.machine(ctx, f"{name}.feed", (-20.0, y), 0.0, (5.0, 2.4, 2.8), "machine_blue", status)
    plastic.conveyor(ctx, f"{name}.belt", (-17.5, y), 0.0, 33.0)
    spacing = {"bottle": 0.16, "tray": 0.34, "tub": 0.3, "glass": 0.16, "mixed": 0.2, "pellets": 0.7}.get(kind, 0.3)
    plastic.belt_items(ctx, f"{name}.items", (-17.5, y), 0.0, 33.0, kind, spacing, speed, stop_at, restart_at, lanes=2 if kind in ("bottle", "glass") else 1)
    plastic.machine(ctx, f"{name}.mid", (0.0, y), 0.0, (3.0, 2.2, 2.4), "machine_grey", status)
    plastic.machine(ctx, f"{name}.pack", (18.0, y), 0.0, (5.0, 2.4, 2.8), "machine_teal", status)


def plastic_factory(ctx, spec):
    """A production hall. kind: bottles, packaging (food trays), film (blown film towers), bags,
    products (injection moulding), recycling, refill (glass bottles, recycled pellets), store
    (racking full of stock) or control (the control room). Flags: stop_at, stopped, restart_at,
    lights_off [start, end], lights_on [start, end], dark, lamps (brightness 0-1), night, people,
    people_action, people_start, gathered ([x, y] of a briefing), maintenance, dust, alert_at
    (control room)."""
    rng = ctx.rng
    kind = str(spec.get("kind", "bottles"))
    if kind == "control":
        return _control_room(ctx, spec)
    stop_at = 0.0 if spec.get("stopped") else spec.get("stop_at")
    stop_at = None if stop_at is None else float(stop_at)
    restart_at = None if spec.get("restart_at") is None else float(spec["restart_at"])
    w, d, h = 64.0, 34.0, (15.0 if kind == "film" else 10.0)
    _room(ctx, "hall", (w, d, h))
    material = ctx.palette.emissive("high windows", "window_night" if spec.get("night") else "window_sky", 0.25 if spec.get("night") else 2.2)
    merged_boxes(ctx, "high_windows", [((x, sy * (d / 2 - 0.02), h - 1.6), (5.0, 0.06, 1.6), 0) for x in range(int(-w / 2 + 4), int(w / 2 - 2), 7) for sy in (-1, 1)], [material])
    merged_boxes(ctx, "walkways", [((0, y, 0.006), (w - 4, 0.12, 0.012), 0) for y in (-8.5, -1.6, 1.6, 8.5)], [ctx.mat("safety_yellow", roughness=0.6)])
    frame = [((x, sy * 13.0, h / 2), (0.5, 0.5, h), 0) for x in range(-28, 29, 8) for sy in (-1, 1)]
    frame += [((x, sy * 13.0, 0.6), (0.7, 0.7, 1.2), 1) for x in range(-28, 29, 8) for sy in (-1, 1)]
    frame += [((x, 0.0, h - 0.4), (0.4, d, 0.6), 0) for x in range(-28, 29, 8)]
    merged_boxes(ctx, "structure", frame, [ctx.mat("steel_blue", roughness=0.5), ctx.mat("safety_yellow", roughness=0.6)])
    services = [((0.0, sy * 9.0, h - 2.6), (w - 4, 1.1, 1.1), 0) for sy in (-1, 1)]
    services += [((0.0, sy * 7.6 + k * 0.35, h - 3.4), (w - 4, 0.18, 0.18), 1 + k) for sy in (-1, 1) for k in range(3)]
    services += [((0.0, sy * 3.2, h - 3.0), (w - 4, 0.5, 0.08), 4) for sy in (-1, 1)]
    services += [((x, sy * 5.0, (h - 2.6 + 2.9) / 2), (0.3, 0.3, h - 2.6 - 2.9), 0) for x in (-20.0, -6.0, 8.0) for sy in (-1, 1)]
    merged_boxes(ctx, "services", services, [ctx.mat("duct_silver", roughness=0.35, metallic=0.6), ctx.mat("pipe_green", roughness=0.5), ctx.mat("pipe_red", roughness=0.5), ctx.mat("pipe_blue", roughness=0.5), ctx.mat("steel_dark", roughness=0.5)])
    for i, (x, words) in enumerate(((-24.0, "SAFETY FIRST"), (10.0, "LINE 1"), (-10.0, "LINE 2"))):
        plastic.sign(ctx, f"wall_sign{i}", words, (x, d / 2 - 0.05, 5.2), size=0.7, colour="safety_yellow")
    _hall_lights(ctx, w, d, h, spec)
    status = plastic.status_lights(ctx, stop_at, restart_at)
    items = {"bottles": "bottle", "packaging": "tray", "refill": "glass", "recycling": "mixed", "products": "tub"}.get(kind)
    if items:
        for k, y in enumerate((-5.0, 5.0)):
            _line(ctx, f"line{k}", y, items, status, stop_at, restart_at)
    if kind == "products":
        for i, x in enumerate((-10.0, 8.0)):
            plastic.moulder(ctx, f"moulder{i}", (x, -9.6), 0.0, status, stop_at, restart_at)
    if kind == "film":
        for i, x in enumerate((-12.0, 8.0)):
            plastic.film_tower(ctx, f"film{i}", (x, 3.0), h - 1.5, stop_at, restart_at)
    if kind == "bags":
        for i, (x, y) in enumerate(((-22.0, -6.0), (-6.0, -6.0), (10.0, -6.0), (-22.0, 5.0), (-6.0, 5.0), (10.0, 5.0))):
            plastic.bag_machine(ctx, f"bagger{i}", (x, y), 0.0, 8.0, status, stop_at, restart_at)
        for i in range(12):
            box(ctx, f"carton{i}", (0.9, 0.7, 0.7), (24.0 + (i % 3) * 1.0, -6.0 + (i // 3) * 3.0, 0.35 + (i % 2) * 0.7), ctx.mat("cardboard", roughness=0.9))
    if kind == "recycling":
        plastic.machine(ctx, "shredder", (24.0, 0.0), 0.0, (5.0, 4.0, 4.5), "machine_green", status)
        plastic.sign(ctx, "recycling_sign", "RECYCLING", (24.0, -2.1, 3.7), size=0.55, colour="sign_white")
        for i in range(10):
            plastic.bale(ctx, f"bale{i}", (-27.0 + (i % 5) * 1.3, -12.5 + (i // 5) * 1.0, 0.0), heading=rng.uniform(-0.1, 0.1))
        for i in range(6):
            plastic.big_bag(ctx, f"pellets{i}", (-27.0 + i * 1.3, 12.0, 0.0), "RECYCLED")
    if kind == "refill":
        for i in range(16):
            crate = [((0, 0, 0.15), (0.9, 0.6, 0.3), 0)] + [((-0.32 + a * 0.16, -0.2 + b * 0.2, 0.42), (0.07, 0.07, 0.28), 1) for a in range(5) for b in range(3)]
            merged_boxes(ctx, f"crate{i}", crate, [ctx.mat("crate_green", roughness=0.6), ctx.mat("glass_green", roughness=0.15)], (-27.0 + (i % 8) * 1.1, -12.5 + (i // 8) * 0.9, 0.0))
        for i in range(5):
            plastic.big_bag(ctx, f"recycled{i}", (-27.0 + i * 1.3, 12.0, 0.0), "RECYCLED")
        plastic.sign(ctx, "refill_sign", "REFILL & REUSE", (0.0, 16.8, 7.0), size=1.4, colour="sign_white")
    if kind == "store":
        _racking(ctx)
    if spec.get("maintenance"):
        _maintenance(ctx)
    _workers(ctx, spec, kind)
    if spec.get("dust"):
        motes = [((rng.uniform(-30, 30), rng.uniform(-15, 15), rng.uniform(1.0, h - 2.0)), (0.07, 0.07, 0.07), 0) for _ in range(300)]
        dust = merged_boxes(ctx, "dust", motes, [ctx.palette.emissive("dust glint", "dust_glint", 1.0)])
        key(dust, "location", 1, (0.0, 0.0, 0.0))
        add_noise(dust, "location", 0.4, 1, ctx.frames, scale=60.0)
    ctx.anchor("aisle", (0.0, 0.0, 1.6))
    return None


def _racking(ctx):
    """High-bay racking full of shrink-wrapped pallets of bottles, film, cartons and tubs."""
    rng = ctx.rng
    boxes = []
    for y in (-12.0, -4.5, 4.5, 12.0):
        for x in range(-28, 25, 3):
            boxes.append(((x - 1.45, y, 4.0), (0.12, 1.2, 8.0), 0))
            for level in range(4):
                z = 0.15 + level * 2.0
                boxes += [((x, y, z), (2.9, 1.2, 0.12), 1), ((x, y, z + 0.8), (2.6, 1.05, 1.4), rng.choice((2, 2, 3, 4, 5)))]
    merged_boxes(ctx, "racking", boxes, [ctx.mat("rack_blue", roughness=0.5), ctx.mat("safety_orange", roughness=0.5), ctx.mat("film_milky", roughness=0.25), ctx.mat("pet_blue", roughness=0.2), ctx.mat("cardboard", roughness=0.9), ctx.mat("tub_yellow", roughness=0.3)])


def _maintenance(ctx):
    """Machines opened up for servicing: guard doors open, toolboxes, a scissor lift and the
    flicker of welding arcs."""
    rng = ctx.rng
    for i, (x, y) in enumerate(((-20.0, -6.25), (0.0, 3.85), (18.0, -6.25))):
        box(ctx, f"open_panel{i}", (1.4, 0.05, 1.2), (x - 1.2, y - 0.6, 1.6), ctx.mat("machine_blue", roughness=0.45), rot=(0.0, 0.0, -1.2))
        box(ctx, f"toolbox{i}", (0.6, 0.35, 0.35), (x + 1.2, y - 1.4, 0.18), ctx.mat("tool_red", roughness=0.5))
    lift = [((0, 0, 0.3), (2.4, 1.2, 0.3), 0), ((0, 0, 3.2), (2.4, 1.2, 0.12), 0)] + [((sx * 0.9, 0, 1.75), (0.08, 0.08, 2.9), 1) for sx in (-1, 1)] + [((0, sy * 0.58, 3.7), (2.4, 0.05, 0.9), 0) for sy in (-1, 1)]
    merged_boxes(ctx, "scissor_lift", lift, [ctx.mat("safety_orange", roughness=0.5), ctx.mat("steel_dark", roughness=0.5)], (6.0, -1.0, 0.0))
    for i, (x, y) in enumerate(((-18.5, -3.7), (2.0, 2.7))):
        arc = _light(ctx, f"weld{i}", "POINT", (x, y, 1.3), 0.0, (0.75, 0.85, 1.0), 0.05)
        t = 0.0
        while t < ctx.frames / ctx.fps:
            arc.data.energy = rng.uniform(25.0, 45.0)
            arc.data.keyframe_insert("energy", frame=ctx.frame(t))
            t += 4.0 / ctx.fps
        sparks = [((rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4), rng.uniform(-0.3, 0.3)), (0.025, 0.025, 0.025), 0) for _ in range(40)]
        spray = merged_boxes(ctx, f"sparks{i}", sparks, [ctx.palette.emissive(f"spark {i}", "spark_white", 8.0)], (x, y, 1.3))
        key(spray, "scale", 1, (1.0, 1.0, 1.0))
        add_noise(spray, "scale", 0.4, 1, ctx.frames, scale=5.0)


def _workers(ctx, spec, kind):
    count = int(spec.get("people", 0))
    if not count:
        return
    rng = ctx.rng
    action = spec.get("people_action", "idle")
    start = float(spec.get("people_start", 0.0))
    if spec.get("gathered"):
        cx, cy = spec["gathered"]
        ring = [(cx + math.cos(a) * r, cy + math.sin(a) * r, 0.0) for a, r in ((math.radians(rng.uniform(-30, 210)), rng.uniform(1.6, 3.4)) for _ in range(count - 1))]
        _people(ctx, "worker", ring, ("worker",), action, start, face_at=(cx, cy))
        _people(ctx, "supervisor", [(cx, cy, 180.0)], ("civilian",), "point", start)
        return
    spots = []
    for i in range(count):
        line = (-5.0, 5.0)[i % 2]
        x = rng.uniform(-14.0, 14.0)
        if kind == "recycling" and i < count * 0.7:
            side = 1.0 if i % 4 < 2 else -1.0
            spots.append((x, line + side * 0.95, 180.0 if side > 0 else 0.0))
        else:
            spots.append((x, line + rng.choice((-1.7, 1.7)), rng.choice((0.0, 180.0, 90.0, -90.0))))
    _people(ctx, "worker", spots, ("worker",), action, start)


def _control_room(ctx, spec):
    """The plant control room: an arc of consoles facing a video wall that turns red with STOP
    PRODUCTION at alert_at while beacons sweep the room."""
    rng = ctx.rng
    _room(ctx, "control", (16.0, 12.0, 3.6), wall="office_wall", floor="carpet_grey")
    for i in range(6):
        plastic.screen(ctx, f"wall_screen{i}", (-5.0 + (i % 3) * 5.0, 5.85, 1.6 + (i // 3) * 1.4), (4.8, 1.3), "screen_blue", 2.0)
    traces = [((-5.0 + (i % 3) * 5.0 + rng.uniform(-1.6, 1.6), 5.8, 1.6 + (i // 3) * 1.4 + rng.uniform(-0.4, 0.4)), (rng.uniform(0.6, 2.0), 0.02, 0.06), 0) for i in range(6) for _ in range(5)]
    merged_boxes(ctx, "wall_traces", traces, [ctx.palette.emissive("trace green", "trace_green", 3.0)])
    desks = []
    for k in range(7):
        a = math.radians(-45 + k * 15)
        x, y = math.sin(a) * 6.0, -math.cos(a) * 6.0 + 4.5
        desks.append((x, y, a))
        plastic.scatter_mesh(ctx, f"desk{k}", [((x, y, 0.38), (1.8, 0.8, 0.76), a, 0), ((x - math.sin(a) * 0.25, y + math.cos(a) * 0.25, 1.05), (1.4, 0.06, 0.5), a, 1)], [ctx.mat("desk_grey", roughness=0.6), ctx.palette.emissive(f"monitor {k}", "screen_blue", 1.6)])
    if spec.get("alert_at") is not None:
        at = float(spec["alert_at"])
        alarm = ctx.palette.emissive("alarm red", "alarm_red", 0.0)
        panel = box(ctx, "alert_panel", (14.6, 0.05, 2.7), (0.0, 5.8, 2.3), alarm)
        plastic.visible(ctx, panel, at)
        points, t, on = [(0.0, 0.0)], at, True
        while t < ctx.frames / ctx.fps + 0.5:
            points.append((t, 3.2 if on else 1.4))
            t, on = t + 0.45, not on
        plastic.glow(ctx, alarm, points)
        words = plastic.sign(ctx, "alert_words", "STOP\nPRODUCTION", (0.0, 5.7, 2.55), size=0.8, colour="sign_white", emission=3.0)
        plastic.visible(ctx, words, at)
        for i, x in enumerate((-6.0, 6.0)):
            beacon = _light(ctx, f"beacon{i}", "SPOT", (x, 5.0, 3.4), 0.0, (1.0, 0.08, 0.04), 0.1, target=(x, 0.0, 0.0), angle=40.0)
            _energy(ctx, beacon, [(0.0, 0.0), (at, 900.0)])
            key(beacon, "rotation_euler", ctx.frame(at))
            beacon.rotation_euler.z += math.tau * 3
            key(beacon, "rotation_euler", ctx.frames + 1)
    for i in range(3):
        _light(ctx, f"ceiling{i}", "AREA", (-4.0 + i * 4.0, 0.0, 3.5), 220.0, size=2.5)
    spots = [(x + math.sin(a) * 0.9, y - math.cos(a) * 0.9, math.degrees(a)) for x, y, a in desks[: int(spec.get("people", 5))]]
    _people(ctx, "operator", spots, ("civilian",), spec.get("people_action", "idle"), float(spec.get("people_start", 0.0)))
    ctx.anchor("wall", (0.0, 5.8, 2.0))
    return None


# ----- clean-ups -----------------------------------------------------------------------------------
def _shore(ctx, spec, kind):
    """Beach, sea and surf: the shoreline is y = 0 with the sea beyond."""
    sand = "shingle" if kind == "uk_beach" else "sand"
    box(ctx, "beach", (1600.0, 60.0, 0.5), (0.0, -30.0, -0.5), ctx.mat(sand, roughness=0.95), anchor="base")
    box(ctx, "strand", (1600.0, 5.0, 0.02), (0.0, -1.5, 0.0), ctx.mat("sand_wet", roughness=0.4), anchor="base")
    _water(ctx, "sea", (6000.0, 2000.0), (0.0, 1000.0, -0.12), "sea_grey" if kind == "uk_beach" else "sea_day", 0.12, 9.0)
    foam = ctx.mat("foam_white", roughness=0.6)
    for i in range(3):
        line = box(ctx, f"surf{i}", (1600.0, 0.7, 0.05), (0.0, 0.0, -0.05), foam)
        plastic.cycle(ctx, line, "location", [(0.0, 9.0, -0.05), (0.0, 0.6, 0.0)], 4.5, i / 3, closed=False)
        plastic.cycle(ctx, line, "scale", [(1.0, 0.2, 1.0), (1.0, 1.6, 1.0), (1.0, 0.05, 1.0)], 4.5, i / 3, closed=False)


def clean_up(ctx, spec):
    """Volunteers clearing plastic. kind: uk_beach (shingle, chalk cliffs, beach huts, groynes),
    sand_beach (dunes), river (a British river with trees, reeds and a footbridge), street (a
    neighbourhood recycling drive) or square (a town square: a rally with placards, or a news
    screen). Flags: litter (count), cleared [start, end, share], volunteers (count), action (or a list),
    piles, van, crew_at ([x, y]: volunteers kitting up there), area ([x, y, width, depth] for
    the litter and volunteers), chain ([x0, y0, x1, y1]: a line passing sacks), night (red
    torches), turtles (hatchlings, from nest), birds, placards (list of words), screen (text),
    people (bystanders)."""
    rng = ctx.rng
    kind = str(spec.get("kind", "sand_beach"))
    night = bool(spec.get("night"))
    if kind in ("uk_beach", "sand_beach"):
        _shore(ctx, spec, kind)
        box(ctx, "land", (4000.0, 3000.0, 0.2), (0.0, -1560.0, 0.0), ctx.mat("field_green", roughness=0.95), anchor="base")
        if kind == "uk_beach":
            _uk_seafront(ctx)
        else:
            for i in range(40):
                ico(ctx, f"dune{i}", rng.uniform(5.0, 10.0), (rng.uniform(-200, 200), rng.uniform(-75, -55), -2.0), ctx.mat("sand", roughness=0.95), subdiv=2, scale=(2.2, 1.2, 0.5), smooth=True)
            tufts = [((rng.uniform(-200, 200), rng.uniform(-70, -50), 1.5), (0.08, 0.08, rng.uniform(0.5, 0.9)), rng.uniform(0, 3), 0) for _ in range(900)]
            plastic.scatter_mesh(ctx, "marram", tufts, [ctx.mat("marram", roughness=0.8)])
        area = ((0.0, -8.0), (160.0, 14.0))
        stand = (-34.0, -3.0)
    elif kind == "river":
        _uk_river(ctx)
        area = ((0.0, 1.0), (60.0, 6.0))
        stand = (-6.0, 1.5)
    elif kind == "street":
        _street(ctx)
        area = ((0.0, 0.0), (60.0, 12.0))
        stand = (-5.0, 5.0)
    else:
        _square(ctx, spec)
        area = ((0.0, 0.0), (40.0, 30.0))
        stand = (-10.0, 10.0)
    if spec.get("area"):
        ax, ay, aw, ad = (float(v) for v in spec["area"])
        area = ((ax, ay), (aw, ad))
    if int(spec.get("litter", 0)):
        (cx, cy), (ex, ey) = area
        clusters = plastic.litter(ctx, "litter", (cx, cy), (ex, ey), int(spec["litter"]), clusters=14, z=0.0)
        if spec.get("cleared"):
            start, end, share = ([float(v) for v in spec["cleared"]] + [1.0])[:3]
            plastic.clear(ctx, clusters[: max(1, round(len(clusters) * share))], start, end)
    for i in range(int(spec.get("piles", 0))):
        plastic.sack_pile(ctx, f"pile{i}", (stand[0] + i * 9.0 + rng.uniform(-2, 2), stand[1] - rng.uniform(4.0, 10.0), 0.0), rng.randint(6, 12))
    if spec.get("van"):
        vehicles.van(ctx, "van", (stand[0] - 6.0, stand[1] - 14.0, 0.0), math.pi / 2, "van_green")
        for i in range(6):
            plastic.sack(ctx, f"van_sack{i}", (stand[0] - 3.0 + (i % 3) * 0.7, stand[1] - 14.0 + (i // 3) * 0.7, 0.0), plastic.SACKS[i % 4])
        merged_boxes(ctx, "kit", [((0.0, 0.0, 0.3), (1.2, 0.8, 0.6), 0), ((1.4, 0.2, 0.25), (0.8, 0.6, 0.5), 1)], [ctx.mat("crate_orange", roughness=0.6), ctx.mat("bag_blue", roughness=0.5)], (stand[0] - 2.0, stand[1] - 11.0, 0.0))
    if spec.get("crew_at"):
        kx, ky = (float(v) for v in spec["crew_at"])
        crew = [(kx + math.cos(a) * 1.6, ky + math.sin(a) * 1.3, math.degrees(a) + 90.0) for a in (0.3, 1.3, 2.3, 3.4, 4.4, 5.4)]
        _people(ctx, "kitting", crew, VOLUNTEERS, ["idle", "carry", "point", "idle", "carry", "look_around"], 0.0, props_for=_held(ctx, ("sack", "bucket", None, "sack", "box", None)))
    count = int(spec.get("volunteers", 0))
    if count:
        (cx, cy), (ex, ey) = area
        spots = [(cx + rng.uniform(-ex / 2, ex / 2), cy + rng.uniform(-ey / 2, ey / 2), rng.uniform(0, 360)) for _ in range(count)]
        action = spec.get("action", ["gather", "crouch", "carry", "gather", "idle"])
        _people(ctx, "volunteer", spots, VOLUNTEERS, action, float(spec.get("people_start", 0.0)), props_for=_held(ctx, ("sack", "sack", "bucket", "sack")))
    if spec.get("chain"):
        x0, y0, x1, y1 = spec["chain"]
        n = 8
        spots = [(x0 + (x1 - x0) * k / (n - 1), y0 + (y1 - y0) * k / (n - 1), math.degrees(math.atan2(y1 - y0, x1 - x0)) - 90.0 + (0 if k % 2 else 180)) for k in range(n)]
        _people(ctx, "chain", spots, VOLUNTEERS, "carry", 0.0, props_for=_held(ctx, "sack"))
    if spec.get("turtles"):
        tx, ty = spec.get("nest", (0.0, -10.0))
        for i in range(int(spec["turtles"])):
            plastic.turtle(ctx, f"hatchling{i}", (tx + rng.uniform(-1.5, 1.5), ty + rng.uniform(-1.0, 1.0), 0.05), math.radians(90 + rng.uniform(-20, 20)), 0.16, rng.uniform(0.08, 0.16), 0.5)
    if night:
        for i in range(int(spec.get("torches", 4))):
            x, y = stand[0] + 28.0 + i * 2.2, stand[1] - 4.0 - (i % 2) * 1.5
            _light(ctx, f"torch{i}", "SPOT", (x, y, 1.2), 140.0, (1.0, 0.15, 0.08), 0.05, target=(x + rng.uniform(-1, 1), y + 6.0, 0.0), angle=35.0)
            _people(ctx, f"ranger{i}", [(x, y - 0.3, 0.0)], ("civilian",), "idle", 0.0)
    if spec.get("birds"):
        birds.flock(ctx, "gulls", int(spec["birds"]), (0.0, 10.0, 14.0), (30.0, 12.0, 5.0), path=[(-60.0, 10.0, 14.0), (80.0, 20.0, 18.0)], speed=6.0, scale=1.0)
    ctx.anchor("shore", (0.0, 0.0, 1.0))
    return None


def _uk_seafront(ctx):
    """A British seafront: promenade wall, a row of beach huts, groynes and white chalk cliffs."""
    box(ctx, "sea_wall", (1600.0, 2.0, 2.4), (0.0, -46.0, 0.0), ctx.mat("concrete", roughness=0.85), anchor="base")
    box(ctx, "promenade", (1600.0, 12.0, 2.4), (0.0, -53.0, 0.0), ctx.mat("paving", roughness=0.85), anchor="base")
    merged_boxes(ctx, "railings", [((0.0, -45.2, 3.4), (1600.0, 0.06, 0.06), 0)] + [((x, -45.2, 2.9), (0.06, 0.06, 1.0), 0) for x in range(-160, 161, 3)], [ctx.mat("trim_white", roughness=0.5)])
    for i, x in enumerate(range(-70, 71, 3)):
        plastic.beach_hut(ctx, f"hut{i}", (float(x), -50.5, 2.4), HUTS[i % len(HUTS)], math.pi)
    posts = []
    for gx in (-45.0, 45.0):
        posts += [((gx, y, 0.6), (0.25, 0.25, 1.2), 0) for y in range(-30, 16, 1)] + [((gx + 0.2, -7.0, 0.5), (0.1, 46.0, 0.6), 0)]
    merged_boxes(ctx, "groynes", posts, [ctx.mat("groyne_wood", roughness=0.9)])
    _cliffs(ctx)
    plastic.sign(ctx, "banner", "BEACH CLEAN", (-34.0, -44.9, 1.3), size=0.9, colour="sign_white", rot=math.pi)


def _cliffs(ctx):
    """White chalk cliffs west of the beach: a ragged, layered face with a green cap, slumped
    blocks at the foot, receding along the coast."""
    rng = ctx.rng
    blocks = []
    for k in range(26):
        y = -150.0 + k * 9.0
        face = -112.0 - k * 4.5 - rng.uniform(0.0, 6.0)
        height = rng.uniform(34.0, 46.0)
        for layer in range(4):
            inset = layer * rng.uniform(1.5, 3.5)
            z0 = layer * height / 4
            blocks.append(((face - 30.0 - inset, y, z0 + height / 8), (60.0, 9.6, height / 4 + 0.6), rng.uniform(-0.05, 0.05), 0))
        blocks.append(((face - 32.0 - 4 * 2.5, y, height + 0.9), (64.0, 9.8, 1.8), 0.0, 1))
        for _ in range(2):
            s = rng.uniform(2.0, 6.0)
            blocks.append(((face + rng.uniform(1.0, 8.0), y + rng.uniform(-4, 4), s / 2), (s, s * 1.2, s), rng.uniform(0, math.tau), 0))
    plastic.scatter_mesh(ctx, "cliffs", blocks, [ctx.mat("chalk", roughness=0.9), ctx.mat("grass_top", roughness=0.9)])


def _uk_river(ctx):
    """A British river: grassy banks, willows, reeds and a footbridge; the river is y 4 to 28."""
    rng = ctx.rng
    box(ctx, "bank_near", (900.0, 400.0, 0.3), (0.0, -196.0, -0.3), ctx.mat("grass_field", roughness=0.95), anchor="base")
    box(ctx, "bank_far", (900.0, 400.0, 0.3), (0.0, 228.0, -0.3), ctx.mat("grass_field", roughness=0.95), anchor="base")
    box(ctx, "mud_near", (900.0, 3.0, 0.2), (0.0, 3.5, -0.5), ctx.mat("bank_mud", roughness=0.95), anchor="base")
    box(ctx, "riverbed", (900.0, 30.0, 0.2), (0.0, 16.0, -1.4), ctx.mat("bank_mud", roughness=0.95), anchor="base")
    _water(ctx, "river", (900.0, 26.0), (0.0, 16.0, -0.45), "river_uk", 0.03, 4.0)
    reeds = [((rng.uniform(-120, 120), rng.uniform(2.0, 5.0), 0.3), (0.05, 0.05, rng.uniform(0.8, 1.6)), 0.0, 0) for _ in range(700)]
    plastic.scatter_mesh(ctx, "reeds", reeds, [ctx.mat("reed_green", roughness=0.8)])
    for i in range(18):
        vegetation.tree(ctx, f"willow{i}", (rng.uniform(-120, 120), rng.uniform(31, 45), 0.0), "round", rng.uniform(1.2, 1.8))
    deck = [((30.0, 16.0, 1.4), (3.0, 30.0, 0.3), 0)] + [((30.0 + sx * 1.4, 16.0, 2.0), (0.08, 30.0, 0.08), 1) for sx in (-1, 1)] + [((30.0 + sx * 1.4, y, 1.7), (0.08, 0.08, 0.7), 1) for sx in (-1, 1) for y in range(2, 31, 2)] + [((30.0, y, 0.5), (2.6, 0.4, 1.8), 2) for y in (8, 16, 24)]
    merged_boxes(ctx, "footbridge", deck, [ctx.mat("plank_light", roughness=0.8), ctx.mat("steel_dark", roughness=0.5), ctx.mat("concrete", roughness=0.85)])
    props.trolley(ctx, "trolley", (4.0, 6.5, -0.7), 0.6)
    plastic.floating(ctx, "drift", (0.0, 14.0), (80.0, 18.0), 260, -0.45, (-0.25, 0.0), clusters=8)
    canoe = vehicles.boat(ctx, "canoe", (-8.0, 12.0, -0.9), math.pi / 2, 4.5, "canoe_red")
    canoe.scale = (0.7, 1.0, 0.5)


def _street(ctx):
    """A neighbourhood recycling drive: houses both sides, gazebos with sorting tables, colour-coded
    bins and a banner."""
    rng = ctx.rng
    box(ctx, "ground", (600.0, 600.0, 0.2), (0.0, 0.0, -0.2), ctx.mat("grass_field", roughness=0.95), anchor="base")
    props.road(ctx, "road", (-200.0, 9.0), (200.0, 9.0), 8.0, 0.02)
    box(ctx, "pavement", (400.0, 10.0, 0.15), (0.0, 0.0, 0.0), ctx.mat("paving", roughness=0.85), anchor="base")
    for i, x in enumerate(range(-90, 91, 12)):
        buildings.house(ctx, f"house_n{i}", (float(x), 22.0, 0.0), seed=i, rot=math.pi)
        buildings.house(ctx, f"house_s{i}", (float(x), -12.0, 0.0), seed=50 + i)
    for i, x in enumerate((-12.0, 0.0)):
        props.tent(ctx, f"gazebo{i}", (x, 1.0, 0.15), (6.0, 4.0), 3.0, 0.0, "gazebo_green")
    bins = [("bin_green", "GLASS"), ("bin_blue", "PLASTIC"), ("bin_grey", "CANS"), ("bin_brown", "PAPER")]
    for i, (colour, label) in enumerate(bins * 2):
        x = 8.0 + i * 1.1
        merged_boxes(ctx, f"bin{i}", [((0, 0, 0.5), (0.6, 0.7, 1.0), 0), ((0, -0.02, 1.03), (0.64, 0.74, 0.06), 0)], [ctx.mat(colour, roughness=0.5)], (x, 2.5, 0.15))
        plastic.sign(ctx, f"bin_label{i}", label, (x, 2.13, 0.85), size=0.09, colour="sign_white")
    plastic.sign(ctx, "banner", "RECYCLING DRIVE", (-6.0, -1.0, 3.6), size=0.7, colour="sign_white")
    box(ctx, "banner_cloth", (7.5, 0.05, 1.0), (-6.0, -0.95, 3.75), ctx.mat("banner_green", roughness=0.8))
    for i in range(6):
        vehicles.car(ctx, f"parked{i}", (-60.0 + i * 22.0 + rng.uniform(-3, 3), 6.2, 0.0), math.pi / 2)


def _square(ctx, spec):
    """A town square: paving, trees, benches and buildings around it; a rally with placards, or an
    outdoor news screen that people stop to watch."""
    rng = ctx.rng
    box(ctx, "square", (400.0, 400.0, 0.2), (0.0, 0.0, -0.2), ctx.mat("paving", roughness=0.85), anchor="base")
    for i in range(10):
        side = i % 2
        buildings.building(ctx, f"block{i}", (-60.0 + (i // 2) * 30.0, 34.0 if side else -40.0, 0.0), (26.0, 14.0, rng.uniform(14.0, 24.0)), rng.choice(("facade_cream", "facade_white", "facade_ochre", "facade_blue")), "flat", math.pi if side else 0.0, seed=i)
    for i in range(8):
        vegetation.tree(ctx, f"tree{i}", (-28.0 + i * 8.0, 20.0, 0.0), "round", 1.1)
        props.bench(ctx, f"bench{i}", (-26.0 + i * 8.0, 17.0, 0.0), math.pi)
    if spec.get("screen"):
        plastic.screen(ctx, "news", (0.0, 26.9, 9.0), (14.0, 6.0), "screen_news", 2.0)
        plastic.sign(ctx, "news_text", str(spec["screen"]), (0.0, 26.8, 8.6), size=0.75, colour="sign_white", emission=2.5)
        plastic.sign(ctx, "news_flag", "BREAKING NEWS", (0.0, 26.8, 10.8), size=0.6, colour="alarm_red", emission=2.5)
    words = spec.get("placards")
    if words:
        n = int(spec.get("crowd", 24))
        spots = [(rng.uniform(-7, 7), rng.uniform(-3, 5), 180.0 + rng.uniform(-15, 15)) for _ in range(n)]

        def give(actor, i):
            if i % 2 == 0:
                plastic.placard(ctx, actor, words[(i // 2) % len(words)], ("placard_white", "placard_yellow", "placard_green")[i % 3])

        _people(ctx, "marcher", spots, VOLUNTEERS, ["idle", "point", "idle", "react"], 0.0, props_for=give)
    if int(spec.get("people", 0)):
        spots = [(rng.uniform(-15, 15), rng.uniform(-6, 12), rng.uniform(-30, 30)) for _ in range(int(spec["people"]))]
        _people(ctx, "passer", spots, ROLES, ["look_around", "idle", "walk", "idle"], 0.0, face_at=(0.0, 27.0))


def _centre(obj):
    """Mean of a mesh object's vertices (its rough middle) in its own coordinates."""
    count = max(1, len(obj.data.vertices))
    return tuple(sum(v.co[k] for v in obj.data.vertices) / count for k in range(3))


# ----- an Indonesian waterway ----------------------------------------------------------------------
def waterway(ctx, spec):
    """An Indonesian river choked with plastic between stilt houses, palms and banana plants, with a
    floating boom across it and volunteers in wooden boats netting the plastic. The river runs along
    X between y = -18 and 18. Flags: plastic (count), cleared [start, end, share] (the share of
    the plastic nearest the boats that is netted out), boats, volunteers, boom, night."""
    rng = ctx.rng
    for sy in (-1, 1):
        box(ctx, f"land{sy}", (3000.0, 1500.0, 0.2), (0.0, sy * 769.0, -0.2), ctx.mat("earth_red", roughness=0.95), anchor="base")
    box(ctx, "riverbed", (3000.0, 38.0, 0.3), (0.0, 0.0, -2.3), ctx.mat("bank_mud", roughness=0.95), anchor="base")
    for sy in (-1, 1):
        box(ctx, f"bank{sy}", (3000.0, 3.0, 2.4), (0.0, sy * 19.5, -2.2), ctx.mat("bank_mud", roughness=0.95), rot=(sy * 0.5, 0.0, 0.0), anchor="base")
    _water(ctx, "river", (3000.0, 38.0), (0.0, 0.0, -0.6), "river_murky", 0.04, 5.0)
    for side, y, face in ((1, 23.0, 0.0), (-1, -23.0, math.pi)):
        x = -120.0
        while x < 160.0:
            if rng.random() < 0.85:
                plastic.stilt_house(ctx, f"house{side}_{int(x)}", (x, y + rng.uniform(-1.0, 1.0), -0.6), face, rng.choice(("roof_rust", "roof_teal", "roof_zinc", "roof_rust")), rng.choice(("wood_plank", "wood_plank", "facade_turquoise", "facade_cream", "facade_pink")), rng.uniform(1.8, 2.6))
            x += rng.uniform(7.5, 10.0)
    for i in range(46):
        side = rng.choice((-1, 1))
        x, y = rng.uniform(-140, 170), side * rng.uniform(30.0, 60.0)
        if rng.random() < 0.6:
            vegetation.palm(ctx, f"palm{i}", (x, y, 0.0), rng.uniform(1.6, 2.4))
        else:
            vegetation.bush(ctx, f"banana{i}", (x, y, 0.0), rng.uniform(1.4, 2.2))
    hills = terrain.ground(ctx, "hills", (2400, 900), (60, 24), amplitude=40.0, seed=4, material=ctx.mat("jungle", roughness=0.95), rise={"axis": "y", "start": -300.0, "end": 300.0, "height": 160.0}, noise_scale=0.006)
    hills.location.y = 650.0
    deck = [((70.0, 0.0, 1.2), (2.4, 46.0, 0.2), 0)] + [((70.0 + sx * 1.1, 0.0, 1.8), (0.08, 46.0, 0.08), 1) for sx in (-1, 1)] + [((70.0 + sx * 1.0, y, -0.4), (0.25, 0.25, 3.2), 1) for sx in (-1, 1) for y in range(-20, 21, 5)]
    merged_boxes(ctx, "footbridge", deck, [ctx.mat("plank_light", roughness=0.85), ctx.mat("pile_wood", roughness=0.9)])
    if spec.get("boom", True):
        plastic.boom(ctx, "boom", [(-28.0, -17.5), (-8.0, 0.0), (8.0, 17.5)], -0.55)
    count = int(spec.get("plastic", 2500))
    jam = plastic.floating(ctx, "jam", (12.0, 0.0), (44.0, 36.0), int(count * 0.7), -0.55, (0.0, 0.0), clusters=12)
    loose = plastic.floating(ctx, "loose", (40.0, 0.0), (160.0, 36.0), int(count * 0.3), -0.55, (-0.3, 0.0), clusters=8)
    if spec.get("cleared"):
        start, end, share = ([float(v) for v in spec["cleared"]] + [1.0])[:3]
        nearest = sorted(jam + loose, key=lambda o: abs(_centre(o)[0] - 7.0))
        plastic.clear(ctx, nearest[: max(1, round(len(nearest) * share))], start, end)
    for i in range(int(spec.get("boats", 3))):
        x, y = -2.0 + i * 9.0, rng.uniform(-9.0, 9.0)
        boat = plastic.perahu(ctx, f"boat{i}", (x, y, -0.65), rng.uniform(-0.4, 0.4), ("boat_blue", "boat_red", "boat_green")[i % 3])
        for k in range(3):
            sack = plastic.sack(ctx, f"boat{i}.sack{k}", (-0.6 + k * 0.6, 0.1, 0.1), plastic.SACKS[k % 4], 0.75)
            parent(sack, boat)
        crew = _people(ctx, f"crew{i}_", [(x - 1.2, y, 90.0, -0.35), (x + 1.4, y, -90.0, -0.35)], VOLUNTEERS, ["crouch", "gather"], rng.uniform(0, 0.5))
        for actor in crew:
            net = merged_boxes(ctx, f"{actor.id}.net", [((0, 0, 0.0), (0.04, 0.04, 2.2), 0), ((0, 0, -1.2), (0.45, 0.45, 0.35), 1)], [ctx.mat("pole_wood", roughness=0.8), ctx.mat("net_green", roughness=0.8)])
            plastic.hold(actor, net, (0.0, 0.45, 0.3))
            net.rotation_euler = (math.radians(-55), 0.0, 0.0)
    count = int(spec.get("volunteers", 0))
    if count:
        spots = [(rng.uniform(-30, 30), rng.uniform(-22.0, -20.5), rng.uniform(-30, 30)) for _ in range(count)]
        _people(ctx, "bank", spots, VOLUNTEERS, ["carry", "gather", "idle"], 0.0, props_for=_held(ctx, "sack"))
        plastic.sack_pile(ctx, "bank_pile", (-12.0, -24.0, 0.0), 10)
    ctx.anchor("boom", (-8.0, 0.0, 0.0))
    return None


# ----- an Indian storm drain -----------------------------------------------------------------------
def drain(ctx, spec):
    """A storm drain in an Indian city, choked with plastic and rubbish between colourful three- and
    four-storey buildings, cleared by the neighbourhood. The channel runs along Y (x from -4 to 4,
    bed at z = -2.6). Flags: cleared [start, end, share] (the nearest share of the blockage is
    cleared, from y = 15 upwards), volunteers (count), truck, rubbish (count)."""
    rng = ctx.rng
    for sx in (-1, 1):
        box(ctx, f"ground{sx}", (600.0, 1000.0, 0.2), (sx * 304.4, 100.0, -0.2), ctx.mat("dust_ground", roughness=0.95), anchor="base")
        box(ctx, f"wall{sx}", (0.4, 360.0, 2.9), (sx * 4.2, 100.0, -2.7), ctx.mat("drain_concrete", roughness=0.9), anchor="base")
        box(ctx, f"path{sx}", (3.2, 360.0, 0.12), (sx * 6.0, 100.0, 0.0), ctx.mat("paving_worn", roughness=0.9), anchor="base")
    box(ctx, "bed", (8.0, 360.0, 0.3), (0.0, 100.0, -2.9), ctx.mat("sludge", roughness=0.9), anchor="base")
    _water(ctx, "water", (8.0, 360.0), (0.0, 100.0, -2.3), "drain_water", 0.02, 3.0, (8, 90))
    for k, y in enumerate((60.0, 140.0)):
        box(ctx, f"crossing{k}", (9.2, 3.0, 0.35), (0.0, y, -0.15), ctx.mat("drain_concrete", roughness=0.9), anchor="base")
    mound = [((rng.uniform(-3.4, 3.4), y, -2.15), (rng.uniform(1.0, 2.6), rng.uniform(1.0, 2.4), rng.uniform(0.3, 0.7)), rng.uniform(0, 3), 0) for y in range(15, 181, 2)]
    plastic.scatter_mesh(ctx, "sludge_mound", mound, [ctx.mat("sludge", roughness=0.9)])
    layers = []
    for z in (-2.2, -1.95, -1.7):
        layers += plastic.litter(ctx, f"rubbish{int(-z * 100)}", (0.0, 98.0), (7.4, 166.0), int(spec.get("rubbish", 5000)) // 3, clusters=12, z=z, along="y")
    if spec.get("cleared"):
        start, end, share = ([float(v) for v in spec["cleared"]] + [1.0])[:3]
        by_y = sorted(layers, key=lambda o: _centre(o)[1])
        plastic.clear(ctx, by_y[: max(1, round(len(by_y) * share))], start, end)
    for side in (-1, 1):
        y = -40.0
        while y < 200.0:
            depth, width, floors = rng.uniform(9.0, 13.0), rng.uniform(6.0, 10.0), rng.choice((3, 3, 4, 4, 2))
            _shophouse(ctx, f"block{side}_{int(y)}", (side * (7.8 + depth / 2), y + width / 2), (depth, width, floors), side)
            y += width + rng.uniform(0.0, 0.6)
    cables = [((rng.uniform(-6, 6), rng.uniform(-30, 190), rng.uniform(6.5, 9.5)), (rng.uniform(14.0, 18.0), 0.03, 0.03), rng.uniform(-0.5, 0.5), 0) for _ in range(140)]
    plastic.scatter_mesh(ctx, "cables", cables, [ctx.mat("cable_black", roughness=0.6)])
    count = int(spec.get("volunteers", 0))
    if count:
        inside = [(rng.uniform(-2.5, 2.5), rng.uniform(4.0, 16.0), rng.choice((0.0, 15.0, -15.0)), -2.3) for _ in range(count // 2)]
        _people(ctx, "digger", inside, ("worker", "civilian"), ["crouch", "gather", "idle"], 0.0, props_for=_held(ctx, ("bucket", "sack", "bucket")))
        bank = [(rng.choice((-1, 1)) * rng.uniform(5.0, 7.0), rng.uniform(0.0, 20.0), rng.uniform(0, 360)) for _ in range(count - count // 2)]
        _people(ctx, "helper", bank, VOLUNTEERS, ["carry", "idle", "gather"], 0.0, props_for=_held(ctx, ("sack", "bucket", "sack")))
        plastic.sack_pile(ctx, "path_pile", (6.0, -2.0, 0.0), 12, 1.2)
    if spec.get("truck"):
        vehicles.lorry(ctx, "tipper", (7.0, -14.0, 0.05), 0.0, "truck_blue", "flatbed")
        plastic.sack_pile(ctx, "truck_load", (7.0, -15.5, 1.4), 8, 0.8)
    ctx.anchor("drain", (0.0, 20.0, -1.5))
    return None


def _shophouse(ctx, name, centre, size, side):
    """A narrow city building: a shop shutter at street level, windows and balconies above, a flat
    roof with a black water tank, painted in a bright colour. Faces the drain (side -1 faces +X)."""
    rng = ctx.rng
    depth, width, floors = size
    cx, cy = centre
    h = floors * 3.0 + 0.6
    face = cx - side * depth / 2
    out = -side
    boxes = [((cx, cy, h / 2), (depth, width - 0.1, h), 0), ((face + out * 0.05, cy, 1.4), (0.1, width * 0.7, 2.6), 1)]
    for f in range(1, floors):
        z = f * 3.0
        boxes.append(((face + out * 0.6, cy, z), (1.2, width * 0.8, 0.15), 2))
        boxes.append(((face + out * 1.15, cy, z + 0.5), (0.05, width * 0.8, 0.9), 3))
        for wy in (-width * 0.22, width * 0.22):
            boxes.append(((face + out * 0.03, cy + wy, z + 1.4), (0.06, 1.1, 1.3), 4))
    boxes.append(((cx, cy, h + 0.4), (depth * 0.3, width * 0.3, 0.8), 5))
    boxes.append(((face + out * 0.06, cy, 3.2), (0.08, width * 0.6, 0.7), 6))
    mats = [ctx.mat(rng.choice(FACADES), roughness=0.85), ctx.mat("shutter_grey", roughness=0.6), ctx.mat("drain_concrete", roughness=0.9), ctx.mat("railing_dark", roughness=0.5), ctx.mat("glass_dark", roughness=0.2), ctx.mat("tank_black", roughness=0.5), ctx.mat(rng.choice(("sign_red", "sign_yellow", "sign_blue", "sign_green")), roughness=0.5)]
    if floors > 1 and rng.random() < 0.7:
        line_z = rng.randint(1, floors - 1) * 3.0 + 1.9
        boxes.append(((face + out * 1.1, cy, line_z), (0.02, width * 0.8, 0.02), 3))
        for k in range(rng.randint(3, 7)):
            boxes.append(((face + out * 1.1, cy - width * 0.35 + k * width * 0.12, line_z - 0.3), (0.05, 0.4, 0.55), 7 + k % 3))
        mats += [ctx.mat(c, roughness=0.8) for c in ("cloth_red", "cloth_yellow", "cloth_blue")]
    merged_boxes(ctx, name, boxes, mats)


# ----- the ocean -----------------------------------------------------------------------------------
def ocean(ctx, spec):
    """The open sea. kind: surface (floating plastic, gulls, a conservation boat hauling a ghost net
    under work lights) or underwater (a bright, rippling surface overhead, light shafts, a sea
    turtle, drifting bags and bottles, a shoal of fish over sand and seagrass). Flags: night,
    debris (count), boat, net_at (the net rises out of the water), turtle, fish, birds."""
    rng = ctx.rng
    night = bool(spec.get("night"))
    if str(spec.get("kind", "surface")) == "underwater":
        return _underwater(ctx, spec)
    _water(ctx, "sea", (8000.0, 8000.0), (0.0, 0.0, 0.0), "sea_night" if night else "sea_deep", 0.35, 14.0, (220, 220))
    debris = int(spec.get("debris", 600))
    if debris:
        plastic.floating(ctx, "debris", (0.0, 30.0), (90.0, 90.0), debris, 0.0, (-0.15, 0.0), clusters=10)
        strands = [((rng.uniform(-2.5, 2.5), rng.uniform(-1.5, 1.5), rng.uniform(-0.1, 0.25)), (rng.uniform(0.6, 2.0), 0.04, 0.04), rng.uniform(0, math.pi), 0) for _ in range(160)]
        net = plastic.scatter_mesh(ctx, "ghost_net", strands, [ctx.mat("net_green", roughness=0.8)], (6.0, 22.0, 0.0))
        key(net, "location", 1)
        if spec.get("net_at") is not None:
            at = float(spec["net_at"])
            net.location = (6.0, 22.0, 0.0)
            key(net, "location", ctx.frame(at))
            net.location = (6.0, 22.0, 4.5)
            key(net, "location", ctx.frame(at + 3.0))
        add_noise(net, "location", 0.06, 1, ctx.frames, scale=16.0)
    if spec.get("boat"):
        boat = vehicles.boat(ctx, "survey", (14.0, 22.0, -0.6), math.pi / 2, 16.0, "boat_white")
        key(boat, "location", 1)
        add_noise(boat, "location", 0.12, 1, ctx.frames, scale=26.0)
        merged_boxes(ctx, "crane", [((0, 0, 4.5), (0.4, 0.4, 7.0), 0), ((-4.0, 0, 7.8), (8.5, 0.35, 0.35), 0), ((-8.0, 0, 5.0), (0.05, 0.05, 5.5), 1)], [ctx.mat("safety_yellow", roughness=0.5), ctx.mat("steel_dark", roughness=0.5)], (14.0, 22.0, 1.0))
        for i, x in enumerate((8.0, 12.0)):
            _light(ctx, f"work{i}", "SPOT", (x, 21.0, 6.5), 4000.0 if night else 0.0, (1.0, 0.95, 0.85), 0.3, target=(6.0, 22.0, 0.0), angle=55.0)
            box(ctx, f"lamp{i}", (0.5, 0.3, 0.3), (x, 21.0, 6.5), ctx.palette.emissive(f"work lamp {i}", "lamp_white", 8.0 if night else 0.0))
        _people(ctx, "crew", [(10.0, 20.6, 90.0, 0.8), (12.0, 23.0, 90.0, 0.8), (16.0, 22.0, 90.0, 0.8)], ("fisherman", "worker", "fisherman"), ["point", "idle", "gather"], 0.0)
    if night:
        moon = ico(ctx, "moon", 40.0, (-900.0, 2600.0, 700.0), ctx.palette.emissive("moon", "moon_white", 2.5), subdiv=2, smooth=True)
        moon.visible_shadow = False
    if spec.get("birds"):
        birds.flock(ctx, "gulls", int(spec["birds"]), (0.0, 40.0, 10.0), (20.0, 15.0, 4.0), path=[(-40.0, 40.0, 10.0), (60.0, 60.0, 14.0)], speed=5.0, scale=1.0)
    if spec.get("turtle"):
        plastic.turtle(ctx, "turtle", (-6.0, 12.0, -0.25), math.radians(15), 1.0, 0.35)
    ctx.anchor("net", (6.0, 22.0, 0.0))
    return None


def _underwater(ctx, spec):
    rng = ctx.rng
    murk = bpy.data.materials.new("Underwater")
    murk.use_nodes = True
    nodes = murk.node_tree.nodes
    nodes.clear()
    scatter = nodes.new("ShaderNodeVolumeScatter")
    scatter.inputs["Density"].default_value = float(spec.get("murk", 0.05))
    scatter.inputs["Color"].default_value = (*ctx.palette.colour("water_scatter"), 1.0)
    scatter.inputs["Anisotropy"].default_value = 0.5
    absorb = nodes.new("ShaderNodeVolumeAbsorption")
    absorb.inputs["Density"].default_value = float(spec.get("murk", 0.05)) * 0.8
    absorb.inputs["Color"].default_value = (*ctx.palette.colour("water_absorb"), 1.0)
    mix = nodes.new("ShaderNodeAddShader")
    out = nodes.new("ShaderNodeOutputMaterial")
    murk.node_tree.links.new(scatter.outputs[0], mix.inputs[0])
    murk.node_tree.links.new(absorb.outputs[0], mix.inputs[1])
    murk.node_tree.links.new(mix.outputs[0], out.inputs["Volume"])
    water_volume = box(ctx, "water_volume", (1200.0, 1200.0, 15.0), (0.0, 30.0, -15.0), murk, anchor="base")
    water_volume.display_type = "WIRE"
    surface = grid(ctx, "surface", (1600.0, 1600.0), (200, 200), ctx.palette.make("surface from below", ctx.palette.colour("surface_glow"), 0.2, 0.0, 0.9), (0.0, 0.0, 0.0))
    wave = surface.modifiers.new("Wave", "WAVE")
    wave.height, wave.width, wave.narrowness, wave.speed = 0.25, 4.0, 1.4, 0.1
    box(ctx, "seabed", (600.0, 600.0, 0.4), (0.0, 0.0, -14.4), ctx.mat("seabed_sand", roughness=0.95), anchor="base")
    for i in range(70):
        ico(ctx, f"rock{i}", rng.uniform(0.4, 2.0), (rng.uniform(-60, 60), rng.uniform(-10, 90), -14.0), ctx.mat("rock_grey", roughness=0.9), subdiv=1, scale=(1.4, 1.0, 0.6))
    grass = [((rng.uniform(-60, 60), rng.uniform(-10, 90), -13.6), (0.06, 0.06, rng.uniform(0.6, 1.4)), 0.0, 0) for _ in range(1500)]
    weed = plastic.scatter_mesh(ctx, "seagrass", grass, [ctx.mat("seagrass", roughness=0.8)])
    key(weed, "rotation_euler", 1)
    add_noise(weed, "rotation_euler", 0.01, 1, ctx.frames, scale=40.0)
    shaft = ctx.palette.make("light shaft", ctx.palette.colour("surface_glow"), 1.0, 0.0, 0.6, alpha=0.06)
    for i in range(14):
        x, y = rng.uniform(-25, 25), rng.uniform(5, 60)
        beam = box(ctx, f"shaft{i}", (rng.uniform(0.8, 2.5), 0.05, 16.0), (x, y, -7.0), shaft, rot=(0.0, math.radians(rng.uniform(15, 25)), rng.uniform(0, math.pi)))
        beam.visible_shadow = False
    bags = []
    for i in range(int(spec.get("debris", 40))):
        x, y, z = rng.uniform(-12, 12), rng.uniform(4, 40), rng.uniform(-9.0, -1.0)
        bag = ico(ctx, f"bag{i}", rng.uniform(0.22, 0.4), (x, y, z), ctx.mat(rng.choice(("bag_white", "bag_white", "bag_white", "bag_blue")), roughness=0.4, alpha=0.6), subdiv=1, scale=(1.0, 0.25, 1.4), smooth=True)
        bag.visible_shadow = False
        key(bag, "location", 1)
        key(bag, "rotation_euler", 1)
        add_noise(bag, "location", 0.5, 1, ctx.frames, scale=50.0, phase=i)
        add_noise(bag, "rotation_euler", 0.5, 1, ctx.frames, scale=40.0, phase=i * 2)
        bags.append(bag)
    if spec.get("turtle", True):
        plastic.turtle(ctx, "turtle", (-6.0, 14.0, -5.0), math.radians(10), 1.2, 0.45, 2.2)
    if spec.get("fish", True):
        plastic.fish_shoal(ctx, "shoal", (6.0, 24.0, -7.0), 70, 3.5, 0.06)
    ctx.anchor("turtle", (-6.0, 14.0, -5.0))
    return None


# ----- rooms ---------------------------------------------------------------------------------------
def plastic_interior(ctx, spec):
    """Rooms where people rethink plastic. kind: supermarket (aisles of packaged goods; loose:
    true for unwrapped produce), refill (a refill shop), restaurant (a takeaway counter going
    reusable), lab (testing products to last), hospital_store (medical supplies), press (a press
    conference with camera flashes), council (a chamber debating policy), studio (packaging
    designers) or kitchen (a home kitchen at night, cupboard open). Flags: people, night."""
    kind = str(spec.get("kind", "supermarket"))
    return {"supermarket": _supermarket, "refill": _refill, "restaurant": _restaurant, "lab": _lab, "hospital_store": _hospital_store, "press": _press, "council": _council, "studio": _studio, "kitchen": _kitchen}[kind](ctx, spec)


def _ceiling_lights(ctx, w, d, h, energy=300.0, step=6.0):
    for i, x in enumerate(range(int(-w / 2 + step / 2), int(w / 2), int(step))):
        for j, y in enumerate(range(int(-d / 2 + step / 2), int(d / 2), int(step))):
            _light(ctx, f"ceiling{i}_{j}", "AREA", (x, y, h - 0.1), energy * 0.55, size=2.5)


def _goods(ctx, name, x, y, length, levels=4, z0=0.35, rot=0.0, kinds=("bottle", "tray", "bag", "tub")):
    """Shelves of plastic-packaged goods along local X."""
    rng = ctx.rng
    items = [((length / 2, 0, 0.05), (length, 0.9, 0.1), 0), ((length / 2, 0.42, 1.0), (length, 0.06, 2.0), 0)]
    for level in range(levels):
        z = z0 + level * 0.45
        items.append(((length / 2, 0.0, z - 0.03), (length, 0.85, 0.04), 0))
        px = 0.15
        kind = kinds[level % len(kinds)]
        while px < length - 0.15:
            for part in plastic.product(kind, px, rng.uniform(-0.2, 0.2), rng):
                (ix, iy, iz), size, m = part
                items.append(((ix, iy, iz + z), size, m + 1))
            px += {"bottle": 0.12, "tray": 0.3, "bag": 0.45, "tub": 0.22, "glass": 0.12}.get(kind, 0.3)
    return merged_boxes(ctx, name, items, [ctx.mat("shelf_white", roughness=0.5)] + plastic.materials(ctx, plastic.ITEM_COLOURS), (x, y, 0.0), (0.0, 0.0, rot))


def _supermarket(ctx, spec):
    rng = ctx.rng
    _room(ctx, "shop", (30.0, 24.0, 5.0), wall="shop_wall", floor="floor_tile", ceiling="ceiling_white")
    _ceiling_lights(ctx, 30.0, 24.0, 5.0, 380.0)
    strips = [((x, y, 4.95), (0.3, 5.0, 0.06), 0) for x in (-12, -6, 0, 6, 12) for y in (-8, 0, 8)]
    merged_boxes(ctx, "strip_lights", strips, [ctx.palette.emissive("strip light", "lamp_white", 5.0)])
    for i, x in enumerate((-9.0, -3.0, 3.0, 9.0)):
        for side in (-1, 1):
            _goods(ctx, f"aisle{i}{side}", x + side * 0.6, -9.0 if side > 0 else 5.0, 14.0, rot=side * math.pi / 2)
    loose = bool(spec.get("loose"))
    produce = []
    for i in range(10):
        cx, cy = -12.0 + (i % 5) * 2.0, 8.0 + (i // 5) * 1.6
        produce.append(((cx, cy, 0.45), (1.6, 1.2, 0.9), 0))
        for k in range(18):
            fx, fy = cx + rng.uniform(-0.65, 0.65), cy + rng.uniform(-0.45, 0.45)
            produce.append(((fx, fy, 0.97 + rng.uniform(0, 0.08)), (0.12, 0.12, 0.12), 1 + i % 5))
            if not loose and k % 3 == 0:
                produce.append(((fx, fy, 0.97), (0.34, 0.26, 0.1), 6))
    merged_boxes(ctx, "produce", produce, [ctx.mat("crate_wood", roughness=0.8)] + [ctx.mat(c, roughness=0.5) for c in ("apple_red", "orange_fruit", "banana_yellow", "lime_green", "tomato_red")] + [ctx.mat("film_milky", roughness=0.2, alpha=0.6)])
    if loose:
        plastic.sign(ctx, "loose_sign", "LOOSE FRUIT & VEG", (-8.0, 11.85, 3.0), size=0.6, colour="sign_green")
    for i in range(8):
        crate = box(ctx, f"stock{i}", (0.7, 0.5, 0.5), (11.0 + (i % 4) * 0.8, 8.0 + (i // 4) * 0.7, 0.25 + (i % 2) * 0.5), ctx.mat("cardboard", roughness=0.9))
        if i < 4:
            label = plastic.sign(ctx, f"stock_label{i}", "PACKAGING", (0.0, -0.26, 0.0), size=0.08, colour="ink_black")
            parent(label, crate)
            label.location = (0.0, -0.26, 0.05)
    count = int(spec.get("people", 4))
    spots = [(10.5, 6.5, 0.0)] + [(rng.uniform(-11, 11), rng.uniform(-10, 5), rng.uniform(0, 360)) for _ in range(count - 1)]
    _people(ctx, "shopper", spots, ["civilian"] + ["shopper"] * count, ["look_around"] + ["walk", "idle"] * count, 0.0, props_for=_held(ctx, ["box", None, None]))
    return None


def _refill(ctx, spec):
    rng = ctx.rng
    _room(ctx, "shop", (14.0, 10.0, 3.4), wall="shop_wall_warm", floor="floor_wood", ceiling="ceiling_white")
    _ceiling_lights(ctx, 14.0, 10.0, 3.4, 260.0, 4.0)
    plastic.dispensers(ctx, "wall_a", (-3.2, 4.6), 0.0, 10)
    plastic.dispensers(ctx, "wall_b", (3.4, 4.6), 0.0, 8)
    plastic.sign(ctx, "refill_sign", "REFILL", (0.0, 4.85, 2.85), size=0.45, colour="sign_green")
    jars = []
    for side in (-1, 1):
        for level in range(4):
            jars.append(((side * 6.75, 0.0, 0.6 + level * 0.45), (0.4, 6.0, 0.04), 0))
            for k in range(20):
                jars.append(((side * 6.7, -2.8 + k * 0.29, 0.72 + level * 0.45), (0.14, 0.14, 0.2), 1))
    merged_boxes(ctx, "jar_shelves", jars, [ctx.mat("counter_wood", roughness=0.7), ctx.mat("jar_glass", roughness=0.08, alpha=0.45)])
    box(ctx, "counter", (3.0, 0.8, 1.0), (4.0, -3.0, 0.0), ctx.mat("counter_wood", roughness=0.7), anchor="base")
    box(ctx, "scale", (0.4, 0.35, 0.08), (3.3, -3.0, 1.04), ctx.mat("steel_light", roughness=0.3, metallic=0.6))
    for i in range(6):
        vegetation.bush(ctx, f"plant{i}", (-6.2 + i * 2.5, -4.6, 0.0), 0.35)
    count = int(spec.get("people", 4))
    spots = [(rng.uniform(-4.0, 4.0), rng.uniform(2.6, 3.4), 0.0) for _ in range(count - 1)] + [(4.0, -3.7, 0.0)]
    _people(ctx, "shopper", spots, ["shopper", "civilian", "child", "shopper", "civilian"], ["idle", "point", "idle", "look_around"], 0.0, props_for=_held(ctx, ["jar", "jar", None, "jar"]))
    return None


def _restaurant(ctx, spec):
    rng = ctx.rng
    _room(ctx, "cafe", (12.0, 9.0, 3.2), wall="cafe_wall", floor="floor_tile_dark", ceiling="ceiling_white")
    _ceiling_lights(ctx, 12.0, 9.0, 3.2, 240.0, 4.0)
    box(ctx, "counter", (8.0, 0.9, 1.05), (0.0, 1.6, 0.0), ctx.mat("counter_wood", roughness=0.7), anchor="base")
    box(ctx, "back_bar", (10.0, 0.6, 0.95), (0.0, 4.1, 0.0), ctx.mat("steel_light", roughness=0.3, metallic=0.6), anchor="base")
    for i in range(3):
        plastic.screen(ctx, f"menu{i}", (-3.0 + i * 3.0, 4.35, 2.4), (2.4, 1.0), "menu_glow", 1.4)
    reusable = [((-3.0 + (i % 6) * 0.42, 1.5 + (i // 18) * 0.0, 1.1 + ((i // 6) % 3) * 0.12), (0.36, 0.26, 0.11), (i // 6) % 2) for i in range(18)]
    merged_boxes(ctx, "reusables", reusable, [ctx.mat("steel_container", roughness=0.25, metallic=0.7), ctx.mat("tub_green", roughness=0.3)])
    plastic.sign(ctx, "reuse_sign", "RETURN & REUSE", (-2.0, 1.12, 0.6), size=0.2, colour="sign_green")
    single = [((2.4 + (i % 3) * 0.3, 1.6, 1.1 + (i // 3) * 0.1), (0.25, 0.2, 0.09), 0) for i in range(15)]
    merged_boxes(ctx, "disposables", single, [ctx.mat("foam_white", roughness=0.6)])
    box(ctx, "returns_crate", (0.9, 0.6, 0.5), (3.8, -0.4, 0.0), ctx.mat("crate_green", roughness=0.6), anchor="base")
    count = int(spec.get("people", 4))
    staff = [(-1.5, 2.8, 180.0), (2.6, 2.8, 180.0)]
    guests = [(rng.uniform(-3.5, 3.5), rng.uniform(-2.0, 0.4), 0.0) for _ in range(max(0, count - 2))]
    _people(ctx, "staff", staff, ["civilian"], ["carry", "idle"], 0.0, props_for=_held(ctx, ["box", None]))
    _people(ctx, "guest", guests, ROLES, ["idle", "look_around"], 0.0)
    return None


def _lab(ctx, spec):
    rng = ctx.rng
    _room(ctx, "lab", (14.0, 10.0, 3.4), wall="lab_wall", floor="floor_tile", ceiling="ceiling_white")
    _ceiling_lights(ctx, 14.0, 10.0, 3.4, 320.0, 4.0)
    benches = []
    for i, y in enumerate((-2.0, 1.5)):
        benches += [((0.0, y, 0.45), (8.0, 1.2, 0.9), 0), ((0.0, y, 0.93), (8.2, 1.3, 0.06), 1)]
    merged_boxes(ctx, "benches", benches, [ctx.mat("bench_grey", roughness=0.6), ctx.mat("lab_white", roughness=0.4)])
    plastic.machine(ctx, "test_rig", (3.0, 4.2), 0.0, (2.0, 1.0, 2.2), "machine_grey", None)
    ram = box(ctx, "ram", (0.25, 0.25, 0.8), (3.0, 3.4, 1.8), ctx.mat("steel_light", roughness=0.3, metallic=0.7))
    plastic.strokes(ctx, ram, "location", 2, 1.8, 1.45, 0.9)
    box(ctx, "sample", (0.4, 0.4, 0.25), (3.0, 3.4, 1.12), ctx.mat("tub_red", roughness=0.3))
    for i in range(4):
        plastic.screen(ctx, f"graph{i}", (-4.5 + i * 2.2, 4.9, 2.0), (1.8, 1.0), "screen_blue", 1.8)
    traces = [((-4.5 + (i % 4) * 2.2 + rng.uniform(-0.6, 0.6), 4.85, 2.0 + rng.uniform(-0.3, 0.3)), (rng.uniform(0.3, 0.9), 0.02, 0.04), 0) for i in range(16)]
    merged_boxes(ctx, "traces", traces, [ctx.palette.emissive("graph line", "trace_green", 3.0)])
    samples = [((-3.0 + i * 0.35, -2.0, 1.05), (0.12, 0.12, 0.18), i % 4) for i in range(16)] + [((-3.0 + i * 0.5, 1.5, 1.08), (0.3, 0.2, 0.24), (i + 1) % 4) for i in range(10)]
    merged_boxes(ctx, "samples", samples, plastic.materials(ctx, ("tub_yellow", "pet_blue", "tub_green", "steel_container")))
    count = int(spec.get("people", 4))
    spots = [(-2.0, -3.2, 0.0), (1.5, 0.3, 180.0), (3.6, 2.6, 30.0), (-1.0, 2.7, 180.0)][:count]
    _people(ctx, "scientist", spots, ["doctor", "worker", "doctor", "civilian"], ["point", "idle", "look_around", "idle"], 0.0)
    return None


def _hospital_store(ctx, spec):
    rng = ctx.rng
    _room(ctx, "store", (10.0, 8.0, 3.0), wall="hospital_wall", floor="floor_tile", ceiling="ceiling_white")
    _ceiling_lights(ctx, 10.0, 8.0, 3.0, 300.0, 4.0)
    shelves = []
    for side, x in ((-1, -4.6), (1, 4.6)):
        for level in range(5):
            z = 0.2 + level * 0.5
            shelves.append(((x, 0.0, z), (0.6, 7.0, 0.04), 0))
            for k in range(14):
                shelves.append(((x, -3.2 + k * 0.48, z + 0.16), (0.45, 0.42, 0.3), rng.choice((1, 1, 2, 3, 4, 5))))
    for k in range(10):
        shelves.append(((-2.0 + k * 0.45, 3.85, 1.8), (0.25, 0.04, 0.35), 6))
    merged_boxes(ctx, "shelving", shelves, [ctx.mat("steel_light", roughness=0.3, metallic=0.6), ctx.mat("box_blue", roughness=0.7), ctx.mat("box_white", roughness=0.7), ctx.mat("glove_purple", roughness=0.6), ctx.mat("box_green", roughness=0.7), ctx.mat("pet_clear", roughness=0.2), ctx.mat("bag_white", roughness=0.4, alpha=0.7)])
    props.trolley(ctx, "trolley", (0.8, -1.5, 0.0), 0.3)
    count = int(spec.get("people", 3))
    spots = [(-3.6, 0.5, -90.0), (3.5, -1.0, 90.0), (0.0, -2.6, 0.0)][:count]
    _people(ctx, "nurse", spots, ["nurse"], ["carry", "idle", "walk"], 0.0, props_for=_held(ctx, ["box", None, "box"]))
    return None


def _press(ctx, spec):
    rng = ctx.rng
    _room(ctx, "hall", (18.0, 14.0, 5.0), wall="press_wall", floor="carpet_blue", ceiling="ceiling_white")
    _ceiling_lights(ctx, 18.0, 14.0, 5.0, 260.0)
    box(ctx, "stage", (10.0, 3.0, 0.4), (0.0, 5.0, 0.0), ctx.mat("stage_dark", roughness=0.6), anchor="base")
    box(ctx, "backdrop", (12.0, 0.1, 4.2), (0.0, 6.8, 0.4), ctx.mat("backdrop_blue", roughness=0.7), anchor="base")
    plastic.sign(ctx, "logo", str(spec.get("logo", "NOVAPAK")), (0.0, 6.7, 3.4), size=0.9, colour="sign_white")
    plastic.sign(ctx, "slogan", str(spec.get("slogan", "LESS PACKAGING. MORE REUSE.")), (0.0, 6.7, 2.5), size=0.4, colour="sign_green")
    box(ctx, "lectern", (0.9, 0.6, 1.15), (0.0, 4.6, 0.4), ctx.mat("podium_wood", roughness=0.6), anchor="base")
    merged_boxes(ctx, "mics", [((dx, 4.3, 1.7), (0.03, 0.03, 0.3), 0) for dx in (-0.12, 0.0, 0.12)], [ctx.mat("ink_black", roughness=0.5)])
    _light(ctx, "stage_key", "SPOT", (0.0, -2.0, 4.6), 1800.0, (1.0, 0.96, 0.9), 0.3, target=(0.0, 5.0, 1.6), angle=40.0)
    _people(ctx, "speaker", [(0.0, 5.0, 180.0, 0.4)], ["civilian"], "point", 0.0)
    spots = [(-5.0 + (i % 8) * 1.4 + rng.uniform(-0.2, 0.2), -1.0 - (i // 8) * 1.5, 0.0) for i in range(int(spec.get("people", 20)))]
    _people(ctx, "reporter", spots, ROLES[:2], ["idle", "idle", "point"], 0.0, face_at=(0.0, 5.0))
    for i, x in enumerate((-5.5, 5.5)):
        merged_boxes(ctx, f"camera{i}", [((0, 0, 1.55), (0.35, 0.6, 0.35), 0), ((0, 0.4, 1.55), (0.18, 0.2, 0.18), 0), ((0, 0, 0.7), (0.05, 0.05, 1.4), 1)], [ctx.mat("ink_black", roughness=0.4), ctx.mat("steel_dark", roughness=0.5)], (x, -4.5, 0.0))
    # camera flashes: small, local pops staggered so the picture never strobes (at most about one
    # a second across the room, well under the three-a-second photosensitivity limit)
    t = 0.4
    for i in range(int(ctx.frames / ctx.fps / 1.1)):
        flash = _light(ctx, f"flash{i}", "POINT", (rng.uniform(-5, 5), rng.uniform(-4.5, -2.5), 1.7), 0.0, (1.0, 1.0, 1.0), 0.05)
        _energy(ctx, flash, [(0.0, 0.0), (t, 350.0), (t + 2.0 / ctx.fps, 0.0)])
        t += rng.uniform(0.9, 1.3)
    return None


def _council(ctx, spec):
    _room(ctx, "chamber", (18.0, 14.0, 5.5), wall="chamber_wood", floor="carpet_green", ceiling="ceiling_white")
    _ceiling_lights(ctx, 18.0, 14.0, 5.5, 260.0)
    desks, seats = [], []
    for k in range(13):
        a = math.radians(-80 + k * (160 / 12))
        x, y = math.sin(a) * 6.0, -math.cos(a) * 6.0 + 2.0
        desks.append(((x, y, 0.4), (1.5, 0.6, 0.8), a, 0))
        desks.append(((x - math.sin(a) * 0.2, y + math.cos(a) * 0.2, 0.95), (0.03, 0.03, 0.3), a, 1))
        seats.append((x - math.sin(a) * 0.75, y + math.cos(a) * 0.75 - 0.0, math.degrees(a) + 180.0))
    plastic.scatter_mesh(ctx, "desks", desks, [ctx.mat("desk_wood", roughness=0.6), ctx.mat("ink_black", roughness=0.5)])
    plastic.screen(ctx, "screen", (0.0, 6.85, 2.8), (7.0, 2.6), "screen_policy", 1.6)
    plastic.sign(ctx, "screen_title", str(spec.get("screen", "WASTE REDUCTION PLAN")), (0.0, 6.8, 3.2), size=0.45, colour="sign_white", emission=2.0)
    plastic.sign(ctx, "screen_sub", "LESS SINGLE-USE PLASTIC", (0.0, 6.8, 2.4), size=0.3, colour="sign_white", emission=2.0)
    _people(ctx, "member", seats[: int(spec.get("people", 11))], ["civilian"], ["idle", "point", "idle", "look_around"], 0.0, face_at=(0.0, 2.0))
    return None


def _studio(ctx, spec):
    rng = ctx.rng
    _room(ctx, "studio", (14.0, 10.0, 3.4), wall="studio_wall", floor="floor_wood", ceiling="ceiling_white")
    _ceiling_lights(ctx, 14.0, 10.0, 3.4, 300.0, 4.0)
    box(ctx, "table", (5.0, 2.0, 0.9), (0.0, 0.5, 0.0), ctx.mat("desk_wood", roughness=0.6), anchor="base")
    models = [((-1.8 + i * 0.5, 0.5 + rng.uniform(-0.6, 0.6), 0.9 + h / 2), (0.3, 0.25, h), m) for i, (h, m) in enumerate(((0.3, 0), (0.2, 1), (0.35, 2), (0.25, 0), (0.15, 3), (0.3, 1), (0.22, 2), (0.28, 0)))]
    merged_boxes(ctx, "prototypes", models, [ctx.mat("cardboard", roughness=0.9), ctx.mat("jar_glass", roughness=0.08, alpha=0.5), ctx.mat("kraft_paper", roughness=0.9), ctx.mat("steel_container", roughness=0.25, metallic=0.7)])
    box(ctx, "whiteboard", (4.5, 0.05, 1.8), (0.0, 4.9, 1.7), ctx.mat("board_white", roughness=0.3))
    notes = [((-1.8 + (i % 6) * 0.6 + rng.uniform(-0.1, 0.1), 4.86, 1.2 + (i // 6) * 0.45), (0.25, 0.01, 0.25), i % 3) for i in range(18)]
    merged_boxes(ctx, "notes", notes, [ctx.mat(c, roughness=0.8) for c in ("note_yellow", "note_pink", "note_green")])
    sketches = [((rng.uniform(-2.0, 2.0), 4.86, rng.uniform(1.0, 2.4)), (rng.uniform(0.3, 1.0), 0.01, 0.03), 0) for _ in range(14)]
    merged_boxes(ctx, "sketches", sketches, [ctx.mat("ink_black", roughness=0.5)])
    spots = [(-2.0, -1.0, 20.0), (2.2, -0.9, -20.0), (0.0, 2.2, 180.0), (-3.0, 1.5, -80.0)][: int(spec.get("people", 4))]
    _people(ctx, "designer", spots, ["civilian", "shopper", "civilian", "civilian"], ["point", "idle", "look_around", "idle"], 0.0, face_at=(0.0, 0.5))
    return None


def _kitchen(ctx, spec):
    rng = ctx.rng
    _room(ctx, "kitchen", (5.0, 4.0, 2.6), wall="kitchen_wall", floor="floor_tile", ceiling="ceiling_white")
    units = [((x, 1.7, 0.45), (0.6, 0.6, 0.9), 0) for x in (-2.0, -1.4, -0.8, 0.8, 1.4, 2.0)] + [((0.0, 1.7, 0.92), (5.0, 0.62, 0.04), 1), ((0.0, 1.82, 1.9), (5.0, 0.35, 0.8), 0)]
    merged_boxes(ctx, "units", units, [ctx.mat("kitchen_unit", roughness=0.5), ctx.mat("worktop", roughness=0.4)])
    pantry = [((0.0, 1.85, 0.05), (1.2, 0.35, 0.1), 0)] + [((0.0, 1.85, z), (1.2, 0.35, 0.03), 0) for z in (0.5, 1.0, 1.5, 2.0)]
    for z in (0.52, 1.02, 1.52, 2.02):
        x = -0.5
        while x < 0.5:
            kind = rng.choice(("bottle", "tub", "tray", "bag"))
            for (ix, iy, iz), size, m in plastic.product(kind, x, 1.8, rng):
                pantry.append(((ix, iy, iz + z), size, m + 1))
            x += 0.16
    merged_boxes(ctx, "pantry", pantry, [ctx.mat("kitchen_unit", roughness=0.5)] + plastic.materials(ctx, plastic.ITEM_COLOURS))
    door = box(ctx, "pantry_door", (0.6, 0.04, 2.1), (-0.3, 0.0, 1.05), ctx.mat("kitchen_unit", roughness=0.5))
    hinge = empty(ctx, "pantry_hinge", (-0.6, 1.66, 0.0), (0.0, 0.0, math.radians(-110)))
    parent(door, hinge)
    door.location = (0.3, 0.0, 1.05)
    box(ctx, "window_night", (1.2, 0.05, 0.9), (2.49, 0.0, 1.5), ctx.palette.emissive("night window", "window_night", 0.4), rot=(0.0, 0.0, math.pi / 2))
    _light(ctx, "pantry_light", "POINT", (0.0, 1.2, 2.2), 25.0, (1.0, 0.85, 0.65), 0.2)
    _light(ctx, "lamp", "POINT", (-1.8, -1.0, 1.6), 30.0, (1.0, 0.78, 0.5), 0.3)
    _people(ctx, "resident", [(0.1, 0.6, 0.0)], ["civilian"], "look_around", 0.0)
    return None


BUILDERS = {
    "plastic_plant": plastic_plant,
    "plastic_factory": plastic_factory,
    "clean_up": clean_up,
    "waterway": waterway,
    "drain": drain,
    "ocean": ocean,
    "plastic_interior": plastic_interior,
}
FOG_EXTENT = {"plastic_plant": (14000, 14000, 1200), "plastic_factory": (70, 40, 16), "clean_up": (2400, 2400, 300), "waterway": (1600, 1600, 300), "drain": (600, 600, 120), "ocean": (3000, 3000, 300), "plastic_interior": (0, 0, 0)}


def build(ctx, spec):
    return BUILDERS[spec["type"]](ctx, spec)
