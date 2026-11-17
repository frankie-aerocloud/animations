"""Assets for "The Day The World Stopped Making Plastic": production lines whose belts, rolls and
machines run, halt and restart, the plastic they make, litter on land and water, collected sacks
and bales, refill dispensers, beach huts, stilt houses, wooden boats, a river boom, a sea turtle
and a shoal of fish. Lines run along local +X; machine fronts face local -Y."""

from __future__ import annotations

import math

import bpy

from studio.assets import props
from studio.assets.meshes import FACES, merged_boxes
from studio.blender.primitives import add_noise, box, cylinder, empty, fcurves, ico, key, mesh_from_pydata, parent

ITEM_COLOURS = ("pet_clear", "pet_blue", "pet_green", "cap_white", "cap_blue", "glass_amber", "glass_green", "glass_clear", "steel_light", "tray_black", "film_milky", "bag_white", "bag_blue", "bag_green", "tub_yellow", "tub_red", "tub_green", "sack_white")
LITTER_COLOURS = ("pet_clear", "pet_blue", "pet_green", "bag_white", "bag_blue", "bag_red", "cap_red", "cap_blue", "crate_orange", "net_green", "foam_white", "tub_yellow")
SACKS = ("sack_black", "sack_blue", "sack_orange", "sack_clear")


# ----- timing ------------------------------------------------------------------------------------
def visible(ctx, obj, start=0.0, end=None):
    """Shown from `start` seconds until `end` (hidden before and after)."""
    states = []
    if start > 0:
        states += [(1, True), (ctx.frame(start), False)]
    elif end is not None:
        states.append((1, False))
    if end is not None:
        states.append((max(2, ctx.frame(end)), True))
    for frame, hidden in states:
        obj.hide_render = hidden
        key(obj, "hide_render", frame)


def _emission(material):
    nodes = material.node_tree.nodes
    for node in nodes:
        if node.type == "EMISSION":
            return node.inputs["Strength"]
    return nodes["Principled BSDF"].inputs["Emission Strength"]


def glow(ctx, material, points, interpolation="CONSTANT"):
    """Key a material's emission strength through (seconds, strength) points."""
    socket = _emission(material)
    for seconds, value in points:
        socket.default_value = value
        socket.keyframe_insert("default_value", frame=ctx.frame(seconds))
    for curve in fcurves(material.node_tree):
        for point in curve.keyframe_points:
            point.interpolation = interpolation


def drive(ctx, obj, speed, stop_at=None, restart_at=None, path="location", axis=0):
    """Advance obj.path[axis] at `speed` units per second. From `stop_at` it eases to a halt over
    0.8 s; with `restart_at` it sits still until then and eases back up to speed. Returns the
    furthest distance travelled during the scene."""
    end = ctx.frames / ctx.fps + 0.2
    if speed == 0 or (stop_at is not None and stop_at <= 0):
        points = [(0.0, 0.0, "CONSTANT")]
    elif restart_at is not None:
        points = [(0.0, 0.0, "CONSTANT"), (restart_at, 0.0, "EASE_IN"), (restart_at + 0.8, speed * 0.4, "LINEAR"), (end, speed * max(0.4, end - restart_at - 0.4), "LINEAR")]
    elif stop_at is not None:
        points = [(0.0, 0.0, "LINEAR"), (stop_at, speed * stop_at, "EASE_OUT"), (stop_at + 0.8, speed * (stop_at + 0.4), "CONSTANT")]
    else:
        points = [(0.0, 0.0, "LINEAR"), (end, speed * end, "LINEAR")]
    base = getattr(obj, path)[axis]
    for seconds, value, _ in points:
        getattr(obj, path)[axis] = base + value
        obj.keyframe_insert(path, index=axis, frame=ctx.frame(seconds))
    curve = next(c for c in fcurves(obj, path) if c.array_index == axis)
    for point, (_, _, mode) in zip(curve.keyframe_points, points):
        point.interpolation = "QUAD" if mode.startswith("EASE") else mode
        if mode.startswith("EASE"):
            point.easing = mode
    return max(abs(value) for _, value, _ in points)


def cycle(ctx, obj, path, values, period, phase=0.0, closed=True):
    """Loop obj.path through `values` (evenly spaced over `period` seconds), starting `phase` (0-1)
    of the way through. closed=False jumps from the last value back to the first (a sawtooth)."""
    frames = period * ctx.fps
    offset = phase * frames
    values = [*values, values[0]] if closed else list(values)
    for k, value in enumerate(values):
        setattr(obj, path, value)
        obj.keyframe_insert(path, frame=1 - offset + frames * k / (len(values) - 1))
    for curve in fcurves(obj, path):
        for point in curve.keyframe_points:
            point.interpolation = "LINEAR"
        curve.modifiers.new("CYCLES")


def strokes(ctx, obj, path, axis, rest, reach, period, stop_at=None, restart_at=None):
    """Repeated out-and-back strokes (a sealing head, a press, a picking arm) while the line runs."""
    end = ctx.frames / ctx.fps
    start = restart_at or 0.0
    finish = min(end, stop_at) if stop_at is not None else end
    values = getattr(obj, path)
    values[axis] = rest
    obj.keyframe_insert(path, index=axis, frame=1)
    t = start
    while t + period <= finish + period * 0.5 and t < end:
        for offset, value in ((0.0, rest), (period * 0.35, reach), (period * 0.7, rest)):
            values[axis] = value
            obj.keyframe_insert(path, index=axis, frame=ctx.frame(t + offset))
        t += period


# ----- meshes ------------------------------------------------------------------------------------
def scatter_mesh(ctx, name, items, mats, loc=(0.0, 0.0, 0.0)):
    """One mesh from (centre, size, heading, material index) boxes, each turned about Z."""
    verts, faces, face_mats = [], [], []
    for (cx, cy, cz), (sx, sy, sz), heading, index in items:
        c, s = math.cos(heading), math.sin(heading)
        hx, hy, hz = sx / 2, sy / 2, sz / 2
        base = len(verts)
        for dz in (-hz, hz):
            for dx, dy in ((-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy)):
                verts.append((cx + dx * c - dy * s, cy + dx * s + dy * c, cz + dz))
        faces += [tuple(base + i for i in face) for face in FACES]
        face_mats += [index] * 6
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    for material in mats:
        mesh.materials.append(material)
    mesh.polygons.foreach_set("material_index", face_mats)
    obj = bpy.data.objects.new(name, mesh)
    obj.location = loc
    ctx.link(obj)
    return obj


def materials(ctx, names, shiny=("pet", "glass", "cap", "tub", "film")):
    return [ctx.mat(n, roughness=0.18 if n.startswith(shiny) else 0.55) for n in names]


# ----- production lines -------------------------------------------------------------------------
def product(kind, x, y, rng):
    """Boxes for one product standing on a belt at local (x, y); z from the belt top."""
    if kind == "bottle":
        m = rng.choice((0, 0, 1, 2))
        return [((x, y, 0.11), (0.085, 0.085, 0.22), m), ((x, y, 0.24), (0.06, 0.06, 0.04), m), ((x, y, 0.275), (0.035, 0.035, 0.03), rng.choice((3, 4)))]
    if kind == "glass":
        m = rng.choice((5, 6, 7))
        return [((x, y, 0.1), (0.08, 0.08, 0.2), m), ((x, y, 0.23), (0.045, 0.045, 0.06), m), ((x, y, 0.275), (0.032, 0.032, 0.03), 8)]
    if kind == "tray":
        return [((x, y, 0.025), (0.26, 0.19, 0.05), 9), ((x, y, 0.052), (0.25, 0.18, 0.006), 10)]
    if kind == "bag":
        return [((x, y, 0.03), (0.42, 0.28, 0.06), rng.choice((11, 12, 13)))]
    if kind == "tub":
        return [((x, y, 0.08), (0.18, 0.18, 0.16), rng.choice((14, 15, 16, 12))), ((x, y, 0.165), (0.19, 0.19, 0.012), 3)]
    if kind == "pellets":
        return [((x, y, 0.09), (0.5, 0.34, 0.18), 17)]
    # mixed: collected plastic on a sorting line, lying every which way
    pick = rng.random()
    if pick < 0.5:
        return [((x, y + rng.uniform(-0.15, 0.15), 0.045), (0.24, 0.085, 0.085), rng.choice((0, 0, 1, 2)))]
    if pick < 0.75:
        return [((x, y + rng.uniform(-0.12, 0.12), 0.03), (rng.uniform(0.2, 0.35), rng.uniform(0.15, 0.25), 0.05), rng.choice((11, 12, 13)))]
    return [((x, y, 0.08), (0.16, 0.16, 0.14), rng.choice((14, 15, 16)))]


def belt_items(ctx, name, origin, rot, length, kind="bottle", spacing=0.2, speed=0.5, stop_at=None, restart_at=None, lanes=1, z=0.95):
    """Products riding a belt from origin along local +X for `length` metres. The stream reaches
    back upstream far enough to keep the belt full while it moves; machines at both ends hide the
    surplus. Returns the moving object."""
    rng = ctx.rng
    holder = empty(ctx, f"{name}.line", (origin[0], origin[1], z), (0.0, 0.0, rot))
    travel = speed * (ctx.frames / ctx.fps + 0.4)
    boxes = []
    x = -travel - spacing
    while x < length:
        for lane in range(lanes):
            boxes += product(kind, x + rng.uniform(-0.02, 0.02) * spacing, (lane - (lanes - 1) / 2) * 0.24, rng)
        x += spacing
    obj = merged_boxes(ctx, name, boxes, materials(ctx, ITEM_COLOURS))
    parent(obj, holder)
    drive(ctx, obj, speed, stop_at, restart_at)
    return obj


def conveyor(ctx, name, origin, rot, length, width=0.7, z=0.95):
    """A belt conveyor along local +X: dark belt, steel side rails, legs every 2 m."""
    boxes = [((length / 2, 0.0, z - 0.04), (length, width, 0.08), 0)]
    for side in (-1, 1):
        boxes.append(((length / 2, side * (width / 2 + 0.04), z - 0.02), (length, 0.06, 0.16), 1))
    legs = max(2, int(length / 2.0) + 1)
    for i in range(legs):
        for side in (-1, 1):
            boxes.append(((i * length / (legs - 1), side * width * 0.42, (z - 0.1) / 2), (0.07, 0.07, z - 0.1), 1))
    return merged_boxes(ctx, name, boxes, [ctx.mat("belt_black", roughness=0.8), ctx.mat("steel_light", roughness=0.35, metallic=0.6)], (origin[0], origin[1], 0.0), (0.0, 0.0, rot))


def status_lights(ctx, stop_at=None, restart_at=None):
    """Shared beacon materials for every machine: green while running, red once stopped."""
    green = ctx.palette.emissive("status green", "status_green", 4.0)
    amber = ctx.palette.emissive("status amber", "status_amber", 0.4)
    red = ctx.palette.emissive("status red", "status_red", 0.0)
    if restart_at is not None:
        glow(ctx, green, [(0.0, 0.0), (restart_at, 4.0)])
        glow(ctx, red, [(0.0, 5.0), (restart_at, 0.0)])
    elif stop_at is not None and stop_at <= 0:
        glow(ctx, green, [(0.0, 0.0)])
        glow(ctx, red, [(0.0, 5.0)])
    elif stop_at is not None:
        glow(ctx, green, [(0.0, 4.0), (stop_at, 0.0)])
        glow(ctx, red, [(0.0, 0.0), (stop_at, 5.0)])
    return green, amber, red


def machine(ctx, name, origin, rot=0.0, size=(4.0, 2.2, 2.6), colour="machine_blue", status=None, window=True):
    """A production machine: housing on a dark plinth, a guard window and control panel on the
    front (local -Y), and a green/amber/red light stack on top using the shared `status` materials."""
    w, d, h = size
    boxes = [((0, 0, 0.15), (w, d, 0.3), 1), ((0, 0, 0.3 + (h - 0.3) / 2), (w, d, h - 0.3), 0), ((0, 0, h + 0.05), (w * 0.96, d * 0.96, 0.1), 2)]
    if window:
        boxes.append(((0, -d / 2 - 0.01, h * 0.6), (w * 0.5, 0.03, h * 0.35), 3))
    boxes.append(((w * 0.36, -d / 2 - 0.15, 1.3), (0.45, 0.3, 0.5), 2))
    mats = [ctx.mat(colour, roughness=0.45), ctx.mat("steel_dark", roughness=0.5), ctx.mat("machine_grey", roughness=0.5), ctx.mat("glass_dark", roughness=0.1)]
    if status:
        mats += list(status)
        for k, index in enumerate((4, 5, 6)):
            boxes.append(((-w * 0.4, 0.0, h + 0.17 + k * 0.13), (0.11, 0.11, 0.12), index))
    return merged_boxes(ctx, name, boxes, mats, (origin[0], origin[1], 0.0), (0.0, 0.0, rot))


def film_tower(ctx, name, origin, height=11.0, stop_at=None, restart_at=None):
    """Blown film: an extruder feeding a die at the base, a tall milky bubble of film inside a
    yellow frame, nip rollers at the top and the flattened film running down to a turning roll."""
    x, y = origin
    boxes = [((sx, sy, height / 2), (0.25, 0.25, height), 0) for sx in (-1.8, 1.8) for sy in (-1.8, 1.8)]
    for z in (3.0, height * 0.6, height - 0.3):
        boxes += [((0, -1.8, z), (3.85, 0.2, 0.2), 0), ((0, 1.8, z), (3.85, 0.2, 0.2), 0), ((-1.8, 0, z), (0.2, 3.85, 0.2), 0), ((1.8, 0, z), (0.2, 3.85, 0.2), 0)]
    boxes += [((0, 0, height - 0.55), (3.6, 3.6, 0.12), 1), ((0, 0, 0.6), (2.2, 2.2, 1.2), 2), ((3.4, 0, 0.8), (3.6, 1.1, 1.6), 2), ((4.6, 0, 2.0), (0.8, 0.8, 0.9), 2)]
    boxes += [((0, 0, height - 0.95), (2.9, 0.35, 0.35), 1), ((-1.2, 0, height * 0.5), (0.08, 0.08, height - 2.4), 3), ((-2.6, 0, 0.9), (1.4, 0.08, 0.08), 3)]
    merged_boxes(ctx, f"{name}.frame", boxes, [ctx.mat("safety_yellow", roughness=0.5), ctx.mat("steel_dark", roughness=0.5), ctx.mat("machine_grey", roughness=0.5), ctx.mat("film_milky", roughness=0.3)], (x, y, 0.0))
    bubble = cylinder(ctx, f"{name}.bubble", 1.05, height - 3.2, (x, y, 1.2), ctx.mat("film_milky", roughness=0.25, alpha=0.6), segments=24, anchor="base", radius2=1.3, smooth=True)
    bubble.visible_shadow = False
    roll = cylinder(ctx, f"{name}.roll", 0.55, 2.4, (x - 3.4, y, 0.85), ctx.mat("film_milky", roughness=0.3), segments=20, rot=(math.pi / 2, 0.0, 0.0))
    drive(ctx, roll, -3.0, stop_at, restart_at, path="rotation_euler", axis=1)
    merged_boxes(ctx, f"{name}.stand", [((0, -1.3, 0.45), (0.2, 0.2, 0.9), 0), ((0, 1.3, 0.45), (0.2, 0.2, 0.9), 0)], [ctx.mat("steel_dark", roughness=0.5)], (x - 3.4, y, 0.0))
    for i in range(4):
        cylinder(ctx, f"{name}.stock{i}", 0.5, 2.3, (x - 6.5 - (i % 2) * 1.1, y + 2.5, 0.5 + (i // 2) * 1.0), ctx.mat("film_milky", roughness=0.3), segments=18, rot=(math.pi / 2, 0.0, 0.0))
    return bubble


def bag_machine(ctx, name, origin, rot=0.0, length=6.0, status=None, stop_at=None, restart_at=None):
    """Bag making: a film web along a long table into a sealing head that stamps down and up, and
    a growing stack of finished carrier bags."""
    root = empty(ctx, name, (origin[0], origin[1], 0.0), (0.0, 0.0, rot))
    table = merged_boxes(ctx, f"{name}.table", [((length / 2, 0, 0.85), (length, 1.4, 0.1), 0), ((length / 2, 0, 0.92), (length, 1.1, 0.02), 1)] + [((x, sy, 0.4), (0.1, 0.1, 0.8), 0) for x in (0.2, length / 2, length - 0.2) for sy in (-0.6, 0.6)], [ctx.mat("steel_light", roughness=0.35, metallic=0.6), ctx.mat("film_milky", roughness=0.3)])
    parent(table, root)
    housing = machine(ctx, f"{name}.sealer", (length * 0.7, 0.0), 0.0, (1.6, 1.8, 2.0), "machine_teal", status, window=False)
    parent(housing, root)
    head = box(ctx, f"{name}.head", (1.2, 1.3, 0.2), (length * 0.7, 0.0, 1.25), ctx.mat("steel_dark", roughness=0.4))
    parent(head, root)
    strokes(ctx, head, "location", 2, 1.25, 1.0, 0.7, stop_at, restart_at)
    stack = merged_boxes(ctx, f"{name}.bags", [((0, 0, 0.0 + k * 0.025), (0.5, 0.4, 0.022), k % 3) for k in range(14)], materials(ctx, ("bag_white", "bag_blue", "bag_green")), (length + 0.5, 0.0, 0.95))
    parent(stack, root)
    return root


def moulder(ctx, name, origin, rot=0.0, status=None, stop_at=None, restart_at=None):
    """Injection moulding: a long machine with a hopper, a sliding guard over the moving clamp, and
    a pick arm that swings finished parts onto the belt."""
    root = empty(ctx, name, (origin[0], origin[1], 0.0), (0.0, 0.0, rot))
    body = machine(ctx, f"{name}.body", (0.0, 0.0), 0.0, (6.0, 1.9, 2.1), "machine_teal", status)
    parent(body, root)
    hopper = cylinder(ctx, f"{name}.hopper", 0.45, 0.9, (-2.0, 0.0, 2.2), ctx.mat("machine_grey", roughness=0.4), segments=12, anchor="base", radius2=0.6)
    parent(hopper, root)
    platen = box(ctx, f"{name}.platen", (0.3, 1.5, 1.5), (1.4, -0.2, 1.25), ctx.mat("steel_light", roughness=0.3, metallic=0.6))
    parent(platen, root)
    strokes(ctx, platen, "location", 0, 1.4, 2.0, 1.6, stop_at, restart_at)
    arm = merged_boxes(ctx, f"{name}.arm", [((0, 0, 0.0), (0.18, 0.18, 0.6), 0), ((0.6, 0, 0.3), (1.2, 0.14, 0.14), 0), ((1.2, 0, 0.05), (0.12, 0.3, 0.3), 1)], [ctx.mat("safety_yellow", roughness=0.5), ctx.mat("steel_dark")], (2.4, 0.0, 2.4))
    parent(arm, root)
    strokes(ctx, arm, "rotation_euler", 2, 0.0, math.radians(-110), 1.6, stop_at, restart_at)
    return root


def bale(ctx, name, loc, size=(1.1, 0.8, 0.9), heading=0.0):
    """A compressed bale of crushed bottles, tubs and film under wire straps."""
    rng = ctx.rng
    w, d, h = size
    items = []
    n = (6, 4, 5)
    for i in range(n[0]):
        for j in range(n[1]):
            for k in range(n[2]):
                c = (-w / 2 + (i + 0.5) * w / n[0] + rng.uniform(-0.03, 0.03), -d / 2 + (j + 0.5) * d / n[1] + rng.uniform(-0.03, 0.03), (k + 0.5) * h / n[2])
                items.append((c, (w / n[0] * 1.15, d / n[1] * 1.15, h / n[2] * 1.1), rng.uniform(-0.4, 0.4), rng.choice((0, 0, 0, 1, 2, 3, 4, 5, 6))))
    for k in range(3):
        items.append(((0.0, 0.0, h * (k + 0.5) / 3), (w + 0.04, d + 0.04, 0.03), 0.0, 7))
    obj = scatter_mesh(ctx, name, items, materials(ctx, ("pet_clear", "pet_blue", "pet_green", "bag_white", "cap_red", "tub_yellow", "bag_blue", "steel_dark")), loc)
    obj.rotation_euler.z = heading
    return obj


def big_bag(ctx, name, loc, label=None, colour="sack_white"):
    """A one-tonne bulk bag of pellets with lifting loops, optionally labelled."""
    bag = merged_boxes(ctx, name, [((0, 0, 0.5), (1.0, 1.0, 1.0), 0), ((0, 0, 1.03), (0.9, 0.9, 0.06), 0)] + [((sx * 0.42, sy * 0.42, 1.12), (0.08, 0.08, 0.2), 1) for sx in (-1, 1) for sy in (-1, 1)], [ctx.mat(colour, roughness=0.8), ctx.mat("strap_blue", roughness=0.7)], loc)
    if label:
        tag = props.sign_text(ctx, f"{name}.label", label, (0.0, -0.51, 0.55), size=0.14, colour="safety_green")
        parent(tag, bag)
    return bag


# ----- litter and sacks ---------------------------------------------------------------------------
def _litter_piece(rng, x, y, z):
    pick = rng.random()
    turn = rng.uniform(0, math.tau)
    if pick < 0.38:
        return ((x, y, z + 0.038), (0.22, 0.075, 0.075), turn, rng.choice((0, 0, 0, 1, 2)))
    if pick < 0.63:
        return ((x, y, z + 0.012), (rng.uniform(0.12, 0.3), rng.uniform(0.1, 0.22), 0.024), turn, rng.choice((3, 3, 4, 5)))
    if pick < 0.77:
        return ((x, y, z + 0.012), (0.035, 0.035, 0.024), 0.0, rng.choice((6, 7)))
    if pick < 0.87:
        return ((x, y, z + 0.03), (rng.uniform(0.08, 0.18), rng.uniform(0.06, 0.12), 0.05), turn, 10)
    if pick < 0.93:
        return ((x, y, z + 0.05), (0.1, 0.1, 0.1), turn, 11)
    if pick < 0.98:
        return ((x, y, z + 0.04), (rng.uniform(0.25, 0.5), rng.uniform(0.2, 0.35), 0.08), turn, 9)
    return ((x, y, z + 0.12), (0.45, 0.32, 0.25), turn, 8)


def litter(ctx, name, centre, extent, count, clusters=1, z=0.0, along="x"):
    """Plastic litter scattered over an area: lying bottles, crumpled bags, caps, foam, tangles of
    net, tubs and the odd crate. Split into `clusters` strips along `along` so they can be cleared
    one after another. Returns the cluster objects."""
    rng = ctx.rng
    cx, cy = centre
    ex, ey = extent
    mats = materials(ctx, LITTER_COLOURS)
    groups = [[] for _ in range(clusters)]
    for _ in range(count):
        u, v = rng.uniform(-0.5, 0.5), rng.uniform(-0.5, 0.5)
        index = min(clusters - 1, int(((u if along == "x" else v) + 0.5) * clusters))
        groups[index].append(_litter_piece(rng, cx + u * ex, cy + v * ey, z))
    return [scatter_mesh(ctx, f"{name}{i}", items, mats) for i, items in enumerate(groups) if items]


def clear(ctx, objs, start, end, reverse=False):
    """Hide objects one after another between `start` and `end` seconds (litter picked up)."""
    order = list(reversed(objs)) if reverse else list(objs)
    for i, obj in enumerate(order):
        visible(ctx, obj, 0.0, start + (end - start) * (i + 1) / max(1, len(order)))


def floating(ctx, name, centre, extent, count, z=0.0, drift=(0.0, 0.0), clusters=6):
    """Litter floating on water: bobbing clusters drifting slowly with the current."""
    objs = litter(ctx, name, centre, extent, count, clusters, z - 0.03)
    for i, obj in enumerate(objs):
        key(obj, "location", 1)
        key(obj, "rotation_euler", 1)
        for axis, speed in enumerate(drift):
            if speed:
                drive(ctx, obj, speed, axis=axis)
        add_noise(obj, "location", 0.05, 1, ctx.frames, scale=14.0, phase=i * 2.3)
        add_noise(obj, "rotation_euler", 0.03, 1, ctx.frames, scale=20.0, phase=i * 1.1)
    return objs


def sack(ctx, name, loc, colour="sack_black", scale=1.0):
    """A filled rubbish sack, knotted at the top."""
    x, y, z = loc
    body = ico(ctx, name, 0.3 * scale, (x, y, z + 0.33 * scale), ctx.mat(colour, roughness=0.3), subdiv=2, scale=(1.0, 0.85, 1.15), smooth=True)
    knot = cylinder(ctx, f"{name}.knot", 0.05 * scale, 0.14 * scale, (0.0, 0.0, 0.36 * scale), ctx.mat(colour, roughness=0.3), segments=6, anchor="base", radius2=0.09 * scale)
    parent(knot, body)
    return body


def sack_pile(ctx, name, loc, count=8, spread=1.4):
    rng = ctx.rng
    x, y, z = loc
    for i in range(count):
        layer = 0 if i < count * 0.65 else 1
        sack(ctx, f"{name}{i}", (x + rng.uniform(-spread, spread) * (0.5 if layer else 1.0), y + rng.uniform(-spread, spread) * 0.6, z + layer * 0.5), rng.choice(SACKS), rng.uniform(0.85, 1.15))


def hold(actor, obj, offset=(0.0, 0.30, 0.02)):
    """Give an actor something to carry in front of them (the carry pose follows)."""
    parent(obj, actor.torso)
    obj.location = offset
    actor.prop = obj
    return obj


def held_sack(ctx, actor, colour="sack_black"):
    return hold(actor, sack(ctx, f"{actor.id}.sack", (0.0, 0.0, -0.35), colour, 0.75), (0.0, 0.28, -0.3))


def placard(ctx, actor, words, colour="placard_white"):
    """A hand-lettered placard on a pole, held up above the head, its words facing forward."""
    board = merged_boxes(ctx, f"{actor.id}.placard", [((0, 0, 0.0), (0.8, 0.03, 0.5), 0), ((0, 0.02, -0.55), (0.04, 0.04, 0.8), 1)], [ctx.mat(colour, roughness=0.8), ctx.mat("pole_wood", roughness=0.8)])
    label = props.sign_text(ctx, f"{actor.id}.words", words, (0.0, 0.02, -0.04), size=0.11, colour="placard_ink")
    parent(label, board)
    label.location = (0.0, 0.02, -0.04)
    label.rotation_euler = (math.pi / 2, 0.0, math.pi)
    return hold(actor, board, (0.0, 0.2, 1.05))


# ----- places and things ---------------------------------------------------------------------------
def beach_hut(ctx, name, loc, colour, rot=0.0):
    """A British beach hut: a painted timber box under a pitched roof, white trim and double doors."""
    root = empty(ctx, name, loc, (0.0, 0.0, rot))
    w, d, h = 2.2, 2.4, 2.2
    body = merged_boxes(ctx, f"{name}.body", [((0, 0, 0.15), (w + 0.2, d + 0.2, 0.3), 2), ((0, 0, 0.3 + h / 2), (w, d, h), 0), ((-0.42, -d / 2 - 0.02, 1.25), (0.8, 0.04, 1.8), 1), ((0.42, -d / 2 - 0.02, 1.25), (0.8, 0.04, 1.8), 1)] + [((sx * w / 2, -d / 2, 0.3 + h / 2), (0.1, 0.1, h), 1) for sx in (-1, 1)], [ctx.mat(colour, roughness=0.6), ctx.mat("trim_white", roughness=0.6), ctx.mat("pole_wood", roughness=0.8)])
    parent(body, root)
    top = 0.3 + h
    gable = mesh_from_pydata(ctx, f"{name}.gable", [(-w / 2, -d / 2, top), (w / 2, -d / 2, top), (0, -d / 2, top + 0.75), (-w / 2, d / 2, top), (w / 2, d / 2, top), (0, d / 2, top + 0.75)], [(0, 1, 2), (3, 5, 4)], [ctx.mat(colour, roughness=0.6)])
    parent(gable, root)
    for side in (-1, 1):
        slab = box(ctx, f"{name}.roof{side}", (1.42, d + 0.4, 0.08), (side * 0.6, 0.0, top + 0.4), ctx.mat("roof_hut", roughness=0.7), rot=(0.0, side * 0.6, 0.0))
        parent(slab, root)
    return root


def stilt_house(ctx, name, loc, rot=0.0, roof="roof_rust", wall="wood_plank", stilts=2.2):
    """A timber house on stilts over the riverbank: piles, plank deck, board walls with dark
    windows and a door, and a corrugated metal roof."""
    rng = ctx.rng
    root = empty(ctx, name, loc, (0.0, 0.0, rot))
    w, d = rng.uniform(5.0, 7.0), rng.uniform(4.5, 6.0)
    boxes = [((sx * (w / 2 - 0.3), sy * (d / 2 - 0.3), stilts / 2), (0.22, 0.22, stilts), 2) for sx in (-1, 0, 1) for sy in (-1, 1)]
    boxes += [((0, -0.6, stilts), (w + 0.4, d + 1.4, 0.15), 2), ((0, 0.3, stilts + 1.35), (w, d - 0.6, 2.6), 0)]
    boxes += [((x, -d / 2 + 0.29, stilts + 1.5), (0.8, 0.04, 0.7), 3) for x in (-w * 0.3, w * 0.3)] + [((0, -d / 2 + 0.29, stilts + 1.1), (0.8, 0.04, 1.8), 1)]
    boxes += [((0, -d / 2 - 1.2, stilts + 0.5), (w + 0.4, 0.06, 0.08), 2)]
    body = merged_boxes(ctx, f"{name}.body", boxes, [ctx.mat(wall, roughness=0.85), ctx.mat("door_teal", roughness=0.7), ctx.mat("pile_wood", roughness=0.9), ctx.mat("glass_dark", roughness=0.2)])
    parent(body, root)
    top = stilts + 2.65
    for side in (-1, 1):
        slab = box(ctx, f"{name}.roof{side}", (w + 0.8, d / 2 + 0.7, 0.06), (0.0, side * (d / 4 + 0.1) + 0.3, top + 0.55), ctx.mat(roof, roughness=0.45, metallic=0.4), rot=(-side * 0.42, 0.0, 0.0))
        parent(slab, root)
    return root


def perahu(ctx, name, loc, heading=0.0, colour="boat_blue", length=7.0):
    """A long, narrow wooden boat with raised, pointed ends and a painted band, bobbing gently."""
    root = empty(ctx, name, loc, (0.0, 0.0, heading))
    half = length / 2
    boxes = [((0, 0, 0.25), (length - 1.6, 1.1, 0.5), 0), ((0, 0, 0.47), (length - 1.6, 1.16, 0.12), 1), ((0, 0, 0.08), (length - 1.8, 0.9, 0.06), 2)]
    for sx in (-1, 1):
        boxes += [((sx * (half - 0.55), 0, 0.35), (0.7, 0.75, 0.6), 0), ((sx * (half - 0.15), 0, 0.5), (0.4, 0.4, 0.75), 0), ((sx * (half - 0.15), 0, 0.85), (0.3, 0.3, 0.12), 1)]
    boxes += [((x, 0, 0.32), (0.25, 1.0, 0.06), 3) for x in (-1.2, 0.2, 1.4)]
    hull = merged_boxes(ctx, f"{name}.hull", boxes, [ctx.mat("boat_wood", roughness=0.8), ctx.mat(colour, roughness=0.6), ctx.mat("pile_wood", roughness=0.9), ctx.mat("plank_light", roughness=0.8)])
    parent(hull, root)
    key(hull, "location", 1, (0.0, 0.0, 0.0))
    add_noise(hull, "location", 0.05, 1, ctx.frames, scale=22.0, phase=loc[0])
    key(hull, "rotation_euler", 1, (0.0, 0.0, 0.0))
    add_noise(hull, "rotation_euler", 0.04, 1, ctx.frames, scale=26.0, phase=loc[1])
    return root


def boom(ctx, name, points, z=0.0, spacing=1.1):
    """A floating barrier of orange floats strung along a polyline, with a dark skirt beneath."""
    items = []
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        length = math.hypot(x1 - x0, y1 - y0)
        heading = math.atan2(y1 - y0, x1 - x0)
        for k in range(max(1, int(length / spacing))):
            t = (k + 0.5) / max(1, int(length / spacing))
            items.append(((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, z + 0.12), (spacing * 0.85, 0.45, 0.4), heading, 0))
        items.append((((x0 + x1) / 2, (y0 + y1) / 2, z - 0.15), (length, 0.05, 0.4), heading, 1))
    obj = scatter_mesh(ctx, name, items, [ctx.mat("buoy_orange", roughness=0.45), ctx.mat("steel_dark", roughness=0.8)])
    key(obj, "location", 1, (0.0, 0.0, 0.0))
    add_noise(obj, "location", 0.04, 1, ctx.frames, scale=18.0)
    return obj


def turtle(ctx, name, loc, heading=0.0, scale=1.0, speed=0.0, stroke=1.6):
    """A green sea turtle: domed shell, head and four flippers that stroke as it swims forward."""
    root = empty(ctx, name, loc, (0.0, 0.0, heading))
    s = scale
    shell = ico(ctx, f"{name}.shell", 0.5 * s, (0.0, 0.0, 0.0), ctx.mat("turtle_shell", roughness=0.5), subdiv=2, scale=(1.0, 0.82, 0.32), smooth=True)
    parent(shell, root)
    belly = ico(ctx, f"{name}.belly", 0.46 * s, (0.0, 0.0, -0.05 * s), ctx.mat("turtle_belly", roughness=0.6), subdiv=2, scale=(1.0, 0.8, 0.18), smooth=True)
    parent(belly, root)
    head = ico(ctx, f"{name}.head", 0.13 * s, (0.6 * s, 0.0, 0.03 * s), ctx.mat("turtle_skin", roughness=0.6), subdiv=1, scale=(1.4, 0.9, 0.8), smooth=True)
    parent(head, root)
    end = ctx.frames / ctx.fps
    for fx, fy, size, sweep in ((0.25, 1, (0.22, 0.6, 0.04), 38.0), (0.25, -1, (0.22, 0.6, 0.04), 38.0), (-0.38, 1, (0.18, 0.3, 0.04), 18.0), (-0.38, -1, (0.18, 0.3, 0.04), 18.0)):
        pivot = empty(ctx, f"{name}.pivot{fx}{fy}", (fx * s, fy * 0.3 * s, -0.02 * s))
        parent(pivot, root)
        flipper = box(ctx, f"{name}.flipper{fx}{fy}", (size[0] * s, size[1] * s, size[2] * s), (0.0, fy * size[1] * s / 2, 0.0), ctx.mat("turtle_skin", roughness=0.6), bevel=0.02 * s)
        parent(flipper, pivot)
        t, phase = 0.0, 0.0 if fx > 0 else stroke / 2
        while t <= end + stroke:
            for offset, angle in ((0.0, sweep), (stroke / 2, -sweep)):
                pivot.rotation_euler = (math.radians(angle) * fy, 0.0, math.radians(-25.0 * fy if fx > 0 else 10.0 * fy))
                pivot.keyframe_insert("rotation_euler", frame=ctx.frame(t + offset + phase))
            t += stroke
    drive(ctx, root, speed * math.cos(heading), axis=0)
    drive(ctx, root, speed * math.sin(heading), axis=1)
    key(root, "location", 1, index=2)
    add_noise(root, "location", 0.06 * s, 1, ctx.frames, scale=30.0)
    return root


def fish_shoal(ctx, name, centre, count=40, radius=4.0, turns=0.08):
    """Small silver fish circling as one shoal (`turns` per second)."""
    rng = ctx.rng
    root = empty(ctx, name, centre)
    items = []
    for i in range(count):
        a = rng.uniform(0, math.tau)
        r = radius * rng.uniform(0.6, 1.0)
        items.append(((math.cos(a) * r, math.sin(a) * r, rng.uniform(-0.8, 0.8)), (0.22, 0.05, 0.08), a + math.pi / 2, 0))
    fish = scatter_mesh(ctx, f"{name}.fish", items, [ctx.mat("fish_silver", roughness=0.25, metallic=0.5)])
    parent(fish, root)
    drive(ctx, root, turns * math.tau, path="rotation_euler", axis=2)
    return root


def dispensers(ctx, name, origin, rot=0.0, count=8):
    """A refill station: a row of gravity dispensers (clear tubes of rice, pasta, lentils, oats and
    nuts) on a timber frame, with levers and chutes, above a counter of empty glass jars."""
    rng = ctx.rng
    root = empty(ctx, name, (origin[0], origin[1], 0.0), (0.0, 0.0, rot))
    width = count * 0.5
    frame = merged_boxes(ctx, f"{name}.frame", [((0, 0.15, 2.5), (width + 0.2, 0.5, 0.08), 0), ((0, 0.3, 1.5), (width + 0.2, 0.06, 2.0), 0), ((0, -0.1, 0.45), (width + 0.4, 0.7, 0.9), 0)] + [((sx * (width / 2 + 0.05), 0.15, 1.3), (0.1, 0.5, 2.6), 0) for sx in (-1, 1)], [ctx.mat("counter_wood", roughness=0.7)])
    parent(frame, root)
    foods = ("rice", "pasta", "lentil_red", "oats", "nuts", "rice", "pasta", "lentil_red")
    glass = ctx.mat("jar_glass", roughness=0.08, alpha=0.35)
    for i in range(count):
        x = -width / 2 + 0.25 + i * 0.5
        tube = cylinder(ctx, f"{name}.tube{i}", 0.17, 0.75, (x, 0.0, 1.55), glass, segments=16, anchor="base")
        parent(tube, root)
        tube.visible_shadow = False
        fill = cylinder(ctx, f"{name}.fill{i}", 0.155, 0.75 * rng.uniform(0.4, 0.85), (x, 0.0, 1.56), ctx.mat(foods[i % len(foods)], roughness=0.9), segments=16, anchor="base")
        parent(fill, root)
        bits = merged_boxes(ctx, f"{name}.chute{i}", [((0, 0, 1.4), (0.12, 0.12, 0.3), 0), ((0.16, -0.05, 1.42), (0.18, 0.04, 0.04), 1)], [ctx.mat("steel_dark", roughness=0.5), ctx.mat("lever_black", roughness=0.5)], (x, 0.0, 0.0))
        parent(bits, root)
    jars = [((-width / 2 + 0.2 + i * 0.28, -0.25, 1.0), (0.14, 0.14, 0.2), 0) for i in range(int(width / 0.28))]
    jar_obj = merged_boxes(ctx, f"{name}.jars", jars + [((c[0], c[1], 1.11), (0.15, 0.15, 0.03), 1) for c, _, _ in jars], [glass, ctx.mat("lid_steel", roughness=0.3, metallic=0.7)])
    parent(jar_obj, root)
    return root


def screen(ctx, name, loc, size, colour="screen_blue", strength=2.5, rot=(0.0, 0.0, 0.0)):
    """A flat emissive screen (front faces local -Y)."""
    return box(ctx, name, (size[0], 0.04, size[1]), loc, ctx.palette.emissive(f"{name} light", colour, strength), rot=rot)


def sign(ctx, name, words, loc, size=0.5, colour="white", emission=0.0, rot=0.0):
    """Upright lettering facing local -Y (turned by `rot` about Z)."""
    label = props.sign_text(ctx, name, words, loc, size=size, colour=colour, emission=emission)
    label.rotation_euler = (math.pi / 2, 0.0, rot)
    return label
