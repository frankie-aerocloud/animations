"""Stylised low-poly people: parented block limbs, role wardrobes and procedural actions.

Characters face local +Y; root rotation Z is the heading. Limb pivots sit at the joints so
rotating a limb object swings it naturally. Forward swing of a limb is +X rotation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from mathutils import Vector

from studio.assets import props
from studio.blender.primitives import box, cylinder, empty, key, parent, set_interp
from studio.core.motion import heading, polyline_length, unwrap

ROLES = {
    "civilian": dict(top=("shirt_1", "shirt_2", "shirt_3", "shirt_4", "shirt_5", "shirt_6"), bottom=("trousers_1", "trousers_2", "trousers_3")),
    "shopper": dict(top=("shirt_1", "shirt_2", "shirt_3", "shirt_4", "shirt_5", "shirt_6"), bottom=("trousers_1", "trousers_2", "trousers_3")),
    "child": dict(top=("shirt_1", "shirt_3", "shirt_4", "shirt_6"), bottom=("trousers_1", "trousers_3"), scale=0.62, head=1.18),
    "nurse": dict(top=("scrubs",), bottom=("scrubs",), hat="cap", hat_colour="scrubs"),
    "doctor": dict(top=("shirt_5",), bottom=("trousers_1",), coat=True),
    "paramedic": dict(top=("medic",), bottom=("medic",), vest="hi_vis"),
    "worker": dict(top=("hi_vis",), bottom=("trousers_2",), hat="hard_hat", hat_colour="yellow"),
    "farmer": dict(top=("shirt_4", "shirt_3"), bottom=("trousers_3",), hat="brim", hat_colour="sand"),
    "police": dict(top=("navy",), bottom=("navy",), hat="cap", hat_colour="navy", vest="hi_vis"),
}
SKINS = ("skin_1", "skin_2", "skin_3", "skin_4")
HAIR = ("hair_1", "hair_2", "hair_3", "hair_4")
WALK = dict(period=0.9, speed=1.35, leg=30.0, arm=24.0, lean=3.0, bob=0.025)
RUN = dict(period=0.52, speed=3.6, leg=58.0, arm=55.0, lean=14.0, bob=0.05)
REST = (0.0, 0.0, 0.0)


@dataclass
class Actor:
    id: str
    role: str
    root: object
    hips: object
    torso: object
    head: object
    arms: dict
    legs: dict
    height: float = 1.85
    prop: object = None


def build(ctx, spec):
    rng = ctx.rng
    role = spec.get("role", "civilian")
    style = ROLES[role]
    aid = str(spec["id"])
    s = float(spec.get("scale", style.get("scale", 1.0))) * rng.uniform(0.96, 1.04)
    hs = float(style.get("head", 1.0))
    skin = ctx.mat(spec.get("skin") or rng.choice(SKINS), roughness=0.8)
    top = ctx.mat(spec.get("top") or rng.choice(style["top"]), roughness=0.85)
    bottom = ctx.mat(spec.get("bottom") or rng.choice(style["bottom"]), roughness=0.85)
    hair = ctx.mat(spec.get("hair") or rng.choice(HAIR), roughness=0.75)
    shoes = ctx.mat("black", roughness=0.5)
    eyes = ctx.mat("eyes", roughness=0.3)
    at = list(spec.get("at", (0.0, 0.0)))
    root = empty(ctx, aid, (float(at[0]), float(at[1]), float(at[2]) if len(at) > 2 else 0.0))
    root.rotation_euler = (0.0, 0.0, math.radians(float(spec.get("face", 0.0))))
    root.scale = (s, s, s)
    hips = box(ctx, f"{aid}.hips", (0.34, 0.22, 0.20), (0, 0, 0.90), bottom, bevel=0.03)
    parent(hips, root)
    torso = box(ctx, f"{aid}.torso", (0.40, 0.24, 0.52), (0, 0, 0.08), top, bevel=0.04, anchor="base")
    parent(torso, hips)
    head = box(ctx, f"{aid}.head", (0.26 * hs, 0.25 * hs, 0.28 * hs), (0, 0, 0.55), skin, bevel=0.06 * hs, anchor="base")
    parent(head, torso)
    cap = box(ctx, f"{aid}.hair", (0.275 * hs, 0.265 * hs, 0.09 * hs), (0, -0.012 * hs, 0.235 * hs), hair, bevel=0.03 * hs, anchor="base")
    parent(cap, head)
    fringe = box(ctx, f"{aid}.fringe", (0.275 * hs, 0.05 * hs, 0.07 * hs), (0, 0.11 * hs, 0.20 * hs), hair, bevel=0.015, anchor="base")
    parent(fringe, head)
    for sx in (-0.058, 0.058):
        eye = box(ctx, f"{aid}.eye", (0.038 * hs, 0.012, 0.042 * hs), (sx * hs, 0.126 * hs, 0.165 * hs), eyes)
        parent(eye, head)
    arms = {}
    for side, sx in (("l", 0.255), ("r", -0.255)):
        arm = box(ctx, f"{aid}.arm_{side}", (0.11, 0.11, 0.50), (sx, 0, 0.49), top, bevel=0.025, anchor="top")
        parent(arm, torso)
        hand = box(ctx, f"{aid}.hand_{side}", (0.09, 0.08, 0.10), (0, 0, -0.52), skin, bevel=0.02)
        parent(hand, arm)
        arms[side] = arm
    legs = {}
    for side, sx in (("l", 0.095), ("r", -0.095)):
        leg = box(ctx, f"{aid}.leg_{side}", (0.15, 0.17, 0.84), (sx, 0, -0.06), bottom, bevel=0.03, anchor="top")
        parent(leg, hips)
        shoe = box(ctx, f"{aid}.shoe_{side}", (0.15, 0.26, 0.09), (0, 0.045, -0.84), shoes, bevel=0.02, anchor="base")
        parent(shoe, leg)
        legs[side] = leg
    _wardrobe(ctx, aid, style, head, torso, hs)
    actor = Actor(aid, role, root, hips, torso, head, arms, legs, height=1.85 * s)
    prop_name = spec.get("prop")
    if prop_name:
        actor.prop = props.held(ctx, f"{aid}.prop", prop_name)
        parent(actor.prop, torso)
        actor.prop.location = (0.0, 0.30, 0.02)
    ctx.actors[aid] = actor
    return actor


def _wardrobe(ctx, aid, style, head, torso, hs):
    hat = style.get("hat")
    hat_mat = ctx.mat(style.get("hat_colour", "white"), roughness=0.8)
    if hat == "cap":
        c = box(ctx, f"{aid}.cap", (0.27 * hs, 0.27 * hs, 0.09 * hs), (0, 0, 0.245 * hs), hat_mat, bevel=0.03, anchor="base")
        parent(c, head)
        peak = box(ctx, f"{aid}.peak", (0.22 * hs, 0.10 * hs, 0.02), (0, 0.17 * hs, 0.25 * hs), hat_mat, bevel=0.008, anchor="base")
        parent(peak, head)
    elif hat == "hard_hat":
        c = cylinder(ctx, f"{aid}.hat", 0.165 * hs, 0.13 * hs, (0, 0, 0.23 * hs), hat_mat, segments=14, anchor="base", bevel=0.03)
        parent(c, head)
        brim = cylinder(ctx, f"{aid}.brim", 0.20 * hs, 0.02, (0, 0, 0.235 * hs), hat_mat, segments=14, anchor="base")
        parent(brim, head)
    elif hat == "brim":
        brim = cylinder(ctx, f"{aid}.brim", 0.25 * hs, 0.02, (0, 0, 0.26 * hs), hat_mat, segments=14, anchor="base")
        parent(brim, head)
        crown = cylinder(ctx, f"{aid}.crown", 0.135 * hs, 0.12 * hs, (0, 0, 0.27 * hs), hat_mat, segments=12, anchor="base", bevel=0.02)
        parent(crown, head)
    if style.get("coat"):
        coat = box(ctx, f"{aid}.coat", (0.44, 0.28, 0.36), (0, 0, -0.14), ctx.mat("white", roughness=0.85), bevel=0.03, anchor="base")
        parent(coat, torso)
    if style.get("vest"):
        vest = box(ctx, f"{aid}.vest", (0.43, 0.27, 0.34), (0, 0, 0.16), ctx.mat(style["vest"], roughness=0.85), bevel=0.03, anchor="base")
        parent(vest, torso)


def spawn(ctx, spec):
    """Create one actor or a crowd (spec has `count`) from a storyboard entry and animate it."""
    if "count" in spec:
        return crowd(ctx, spec)
    actor = build(ctx, spec)
    animate(ctx, actor, spec)
    return [actor]


def crowd(ctx, spec):
    rng = ctx.rng
    n = int(spec["count"])
    x, y, w, d = spec["area"]
    roles = spec.get("roles") or ["civilian"]
    action = spec.get("action", "idle")
    actors = []
    for i in range(n):
        sub = {k: v for k, v in spec.items() if k not in ("count", "area", "roles", "props", "to", "stagger", "jitter", "radius", "direction", "gap")}
        sub["id"] = f"{spec['id']}_{i:02d}"
        sub["role"] = rng.choice(roles)
        px, py = x + rng.uniform(-w / 2, w / 2), y + rng.uniform(-d / 2, d / 2)
        sub["at"] = (px, py)
        to = spec.get("to")
        if action in ("walk", "run") and to:
            jitter = float(spec.get("jitter", 2.0))
            sub["path"] = [[px, py], [to[0] + rng.uniform(-jitter, jitter), to[1] + rng.uniform(-jitter, jitter)]]
            sub["start"] = float(spec.get("start", 0.0)) + rng.uniform(0.0, float(spec.get("stagger", 0.6)))
        elif action == "gather" and to:
            radius = float(spec.get("radius", 2.5)) * rng.uniform(0.8, 1.3)
            angle = rng.uniform(0, math.tau)
            sub["path"] = [[px, py], [to[0] + radius * math.cos(angle), to[1] + radius * math.sin(angle)]]
            sub["face_at"] = [to[0], to[1]]
            sub["start"] = float(spec.get("start", 0.0)) + rng.uniform(0.0, float(spec.get("stagger", 1.0)))
        elif action == "scatter":
            radius = float(spec.get("radius", 12.0)) * rng.uniform(0.6, 1.3)
            angle = rng.uniform(0, math.tau)
            sub["path"] = [[px, py], [px + radius * math.cos(angle), py + radius * math.sin(angle)]]
            sub["action"] = "run"
            sub["start"] = float(spec.get("start", 0.0)) + rng.uniform(0.0, float(spec.get("stagger", 0.8)))
        elif action == "queue" and to:
            dx, dy = spec.get("direction", [-1, 0])
            gap = float(spec.get("gap", 0.85))
            sub["at"] = (to[0] + dx * gap * (i + 1) + rng.uniform(-0.15, 0.15), to[1] + dy * gap * (i + 1) + rng.uniform(-0.2, 0.2))
            sub["face_at"] = [to[0], to[1]]
        elif to:
            sub["face_at"] = [to[0], to[1]]
        if action in ("react", "fall", "point", "look_around", "crouch") and spec.get("stagger"):
            sub["start"] = float(spec.get("start", 0.0)) + rng.uniform(0.0, float(spec["stagger"]))
        if spec.get("props") and rng.random() < float(spec.get("prop_chance", 0.6)):
            sub["prop"] = rng.choice(spec["props"])
        actor = build(ctx, sub)
        animate(ctx, actor, sub)
        actors.append(actor)
    return actors


def animate(ctx, actor, spec):
    action = spec.get("action", "idle")
    f0 = ctx.frame(spec.get("start", 0.0))
    f1 = min(ctx.frames, ctx.frame(spec["end"])) if "end" in spec else ctx.frames
    seed = sum(map(ord, actor.id))
    face_at = spec.get("face_at")
    _idle(ctx, actor, seed)
    if action in ("walk", "run", "gather"):
        gait = RUN if action == "run" else WALK
        loc = actor.root.location
        path = spec.get("path") or [[loc.x, loc.y], [loc.x, loc.y + 3.0]]
        if "end" not in spec or action == "gather":
            speed = float(spec.get("speed", gait["speed"]))
            f1 = min(ctx.frames, f0 + max(2, round(polyline_length(path) / speed * ctx.fps)))
        _move_along(ctx, actor, path, f0, f1, gait, face_at)
    elif action == "look_around":
        _look_around(ctx, actor, f0, f1, seed)
    elif action == "point":
        _point(ctx, actor, f0, f1, spec.get("side", "r"))
    elif action == "fall":
        _fall(ctx, actor, f0)
    elif action == "carry":
        _carry(ctx, actor, f0)
    elif action == "react":
        _react(ctx, actor, f0)
    elif action == "crouch":
        _crouch(ctx, actor, f0, f1)
    elif action == "queue":
        _queue(ctx, actor, f0, f1, spec, seed)
    if face_at and action not in ("walk", "run", "gather"):
        actor.root.rotation_euler.z = heading(actor.root.location, (face_at[0], face_at[1]))
    if actor.prop is not None and action not in ("carry", "crouch"):
        _carry(ctx, actor, 1)


def _idle(ctx, actor, seed):
    rng_phase = (seed % 13) * 0.4
    for f in range(1, ctx.frames + 1, 24):
        t = (f - 1) / ctx.fps
        key(actor.hips, "location", f, (0.0, 0.0, 0.90 + 0.006 * math.sin(math.tau * t / 3.1 + rng_phase)))
    f = 1
    while f < ctx.frames:
        yaw = math.radians(((seed * 7 + f) % 41) - 20) * 0.6
        key(actor.head, "rotation_euler", f, (0.0, 0.0, yaw))
        f += 30 + (seed + f) % 40
    key(actor.head, "rotation_euler", ctx.frames, (0.0, 0.0, 0.0))
    set_interp(actor.hips, "SINE", "EASE_IN_OUT")
    set_interp(actor.head, "SINE", "EASE_IN_OUT")


def _cycle(ctx, actor, f0, f1, gait):
    period = gait["period"] * ctx.fps
    step = max(2, round(period / 4))
    leg, arm = math.radians(gait["leg"]), math.radians(gait["arm"])
    rest_before = max(1, f0 - 2)
    for part in (*actor.legs.values(), *actor.arms.values()):
        key(part, "rotation_euler", rest_before, REST)
    f = f0
    while f <= f1:
        phase = (f - f0) / period * math.tau
        s = math.sin(phase)
        key(actor.legs["l"], "rotation_euler", f, (leg * s, 0.0, 0.0))
        key(actor.legs["r"], "rotation_euler", f, (-leg * s, 0.0, 0.0))
        key(actor.arms["l"], "rotation_euler", f, (-arm * s, 0.0, 0.0))
        key(actor.arms["r"], "rotation_euler", f, (arm * s, 0.0, 0.0))
        f += step
    key(actor.torso, "rotation_euler", rest_before, REST)
    key(actor.torso, "rotation_euler", f0, (-math.radians(gait["lean"]), 0.0, 0.0))
    key(actor.torso, "rotation_euler", f1, (-math.radians(gait["lean"]), 0.0, 0.0))
    if f1 + 6 <= ctx.frames:
        for part in (*actor.legs.values(), *actor.arms.values(), actor.torso):
            key(part, "rotation_euler", f1 + 6, REST)
    for part in (*actor.legs.values(), *actor.arms.values(), actor.torso):
        set_interp(part, "SINE", "EASE_IN_OUT")


def _move_along(ctx, actor, path, f0, f1, gait, face_at=None):
    points = [Vector((float(p[0]), float(p[1]), 0.0)) for p in path]
    total = polyline_length(points)
    previous = actor.root.rotation_euler.z
    travelled = 0.0
    key(actor.root, "location", max(1, f0 - 1), points[0])
    for i, point in enumerate(points):
        if i:
            travelled += (points[i] - points[i - 1]).length
        frame = f0 + round((f1 - f0) * (travelled / total if total else 0.0))
        key(actor.root, "location", frame, point)
        if i < len(points) - 1:
            previous = unwrap(previous, heading(point, points[i + 1]))
            key(actor.root, "rotation_euler", max(1, frame - 4), (0.0, 0.0, actor.root.rotation_euler.z))
            key(actor.root, "rotation_euler", frame + 5, (0.0, 0.0, previous))
    if face_at:
        facing = unwrap(previous, heading(points[-1], (float(face_at[0]), float(face_at[1]), 0.0)))
        key(actor.root, "rotation_euler", f1, (0.0, 0.0, previous))
        key(actor.root, "rotation_euler", f1 + 10, (0.0, 0.0, facing))
    set_interp(actor.root, "LINEAR", path="location")
    set_interp(actor.root, "SINE", "EASE_IN_OUT", path="rotation_euler")
    _cycle(ctx, actor, f0, f1, gait)


def _look_around(ctx, actor, f0, f1, seed):
    span = max(12, f1 - f0)
    for t, yaw, pitch in ((0.0, 0, 0), (0.25, -38, -4), (0.45, -30, -2), (0.7, 32, -6), (0.9, 25, 0), (1.0, 0, 0)):
        key(actor.head, "rotation_euler", f0 + round(span * t), (math.radians(pitch), 0.0, math.radians(yaw)))
        key(actor.torso, "rotation_euler", f0 + round(span * t), (0.0, 0.0, math.radians(yaw) * 0.25))
    set_interp(actor.head, "SINE", "EASE_IN_OUT")
    set_interp(actor.torso, "SINE", "EASE_IN_OUT")


def _point(ctx, actor, f0, f1, side="r"):
    arm = actor.arms[side]
    key(arm, "rotation_euler", f0, REST)
    key(arm, "rotation_euler", f0 + 12, (math.radians(95), 0.0, math.radians(-10 if side == "r" else 10)))
    key(arm, "rotation_euler", max(f0 + 14, f1 - 8), (math.radians(95), 0.0, math.radians(-10 if side == "r" else 10)))
    key(arm, "rotation_euler", max(f0 + 16, f1), REST)
    key(actor.head, "rotation_euler", f0 + 12, (math.radians(-6), 0.0, math.radians(18 if side == "l" else -18)))
    set_interp(arm, "SINE", "EASE_IN_OUT")


def _fall(ctx, actor, f0):
    key(actor.root, "rotation_euler", f0, (0.0, 0.0, actor.root.rotation_euler.z))
    key(actor.root, "rotation_euler", f0 + 14, (math.radians(-84), 0.0, actor.root.rotation_euler.z))
    for arm in actor.arms.values():
        key(arm, "rotation_euler", f0, REST)
        key(arm, "rotation_euler", f0 + 10, (math.radians(100), 0.0, 0.0))
    set_interp(actor.root, "EXPO", "EASE_IN", path="rotation_euler")


def _carry(ctx, actor, f0):
    for side, arm in actor.arms.items():
        key(arm, "rotation_euler", max(1, f0), (math.radians(72), 0.0, math.radians(-14 if side == "l" else 14)))


def _react(ctx, actor, f0):
    back = Vector((math.sin(actor.root.rotation_euler.z), -math.cos(actor.root.rotation_euler.z), 0.0)) * 0.45
    start = actor.root.location.copy()
    key(actor.root, "location", f0, start)
    key(actor.root, "location", f0 + 12, start + back)
    for arm in actor.arms.values():
        key(arm, "rotation_euler", f0, REST)
        key(arm, "rotation_euler", f0 + 8, (math.radians(110), 0.0, 0.0))
        key(arm, "rotation_euler", f0 + 30, (math.radians(40), 0.0, 0.0))
    key(actor.head, "rotation_euler", f0, REST)
    key(actor.head, "rotation_euler", f0 + 8, (math.radians(16), 0.0, 0.0))
    key(actor.torso, "rotation_euler", f0, REST)
    key(actor.torso, "rotation_euler", f0 + 8, (math.radians(9), 0.0, 0.0))
    for part in (actor.root, actor.head, actor.torso, *actor.arms.values()):
        set_interp(part, "QUAD", "EASE_OUT")


def _crouch(ctx, actor, f0, f1):
    key(actor.torso, "rotation_euler", max(1, f0 - 1), REST)
    key(actor.torso, "rotation_euler", f0 + 12, (math.radians(-62), 0.0, 0.0))
    key(actor.torso, "rotation_euler", f1, (math.radians(-62), 0.0, 0.0))
    for arm in actor.arms.values():
        key(arm, "rotation_euler", max(1, f0 - 1), REST)
        key(arm, "rotation_euler", f0 + 12, (math.radians(40), 0.0, 0.0))
    key(actor.head, "rotation_euler", f0 + 12, (math.radians(-20), 0.0, 0.0))
    set_interp(actor.torso, "SINE", "EASE_IN_OUT")


def _queue(ctx, actor, f0, f1, spec, seed):
    direction = spec.get("direction", [-1, 0])
    step = Vector((-float(direction[0]), -float(direction[1]), 0.0)) * 0.5
    pos = actor.root.location.copy()
    f = f0 + 20 + seed % 50
    key(actor.root, "location", f0, pos)
    while f < f1:
        key(actor.root, "location", f, pos)
        pos = pos + step
        key(actor.root, "location", f + 14, pos)
        f += 70 + (seed * 3) % 60
    set_interp(actor.root, "SINE", "EASE_IN_OUT", path="location")
