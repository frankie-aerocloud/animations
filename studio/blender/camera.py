"""Reusable cinematography: shot behaviours, depth of field, shake and whip transitions."""

from __future__ import annotations

import math

import bpy
from mathutils import Vector

from studio.blender.primitives import add_noise, empty, key, set_interp
from studio.core.motion import ease_in_out

SHOT_DEFAULTS = {
    "aerial_establish": dict(lens=28, fstop=8.0, ease="in_out"),
    "push_in": dict(lens=40, fstop=4.0, ease="in_out"),
    "tracking": dict(lens=35, fstop=4.0, ease="linear"),
    "orbit": dict(lens=35, fstop=5.6, ease="in_out"),
    "side_follow": dict(lens=35, fstop=4.0, ease="linear"),
    "first_person": dict(lens=22, fstop=2.8, ease="in_out"),
    "close_up": dict(lens=65, fstop=2.0, ease="in_out"),
    "wide": dict(lens=24, fstop=11.0, ease="in_out"),
    "reveal": dict(lens=32, fstop=5.6, ease="out"),
    "static": dict(lens=35, fstop=5.6, ease="linear"),
}
EASING = {"in_out": ("SINE", "EASE_IN_OUT"), "out": ("QUAD", "EASE_OUT"), "in": ("QUAD", "EASE_IN"), "linear": ("LINEAR", "AUTO")}


def resolve(ctx, ref, default=None):
    """World point from [x, y, z], 'anchor:name', 'actor:id', 'object:name' or {ref, offset}."""
    if ref is None:
        if default is None:
            raise ValueError("camera reference missing")
        return Vector(default)
    if isinstance(ref, str):
        kind, _, name = ref.partition(":")
        if kind == "anchor":
            return Vector(ctx.anchors[name])
        if kind == "actor":
            actor = ctx.actors[name]
            point = Vector(actor.root.location)
            point.z += actor.height * 0.55
            return point
        if kind == "object":
            return Vector(ctx.objects[name].location)
        raise ValueError(f"unknown camera reference {ref!r}")
    if isinstance(ref, dict):
        base = resolve(ctx, ref.get("ref"), (0.0, 0.0, 0.0))
        return base + Vector(ref.get("offset", (0.0, 0.0, 0.0)))
    return Vector((float(ref[0]), float(ref[1]), float(ref[2])))


def setup(ctx, spec):
    shot = spec.get("shot", "static")
    defaults = SHOT_DEFAULTS[shot]
    data = bpy.data.cameras.new("Camera")
    data.lens = float(spec.get("lens", defaults["lens"]))
    data.clip_start = 0.05
    data.clip_end = 5000.0
    data.dof.use_dof = bool(spec.get("dof", True))
    data.dof.aperture_fstop = float(spec.get("fstop", defaults["fstop"]))
    data.dof.aperture_blades = 6
    cam = bpy.data.objects.new("Camera", data)
    ctx.link(cam)
    ctx.scene.camera = cam
    ctx.objects["camera"] = cam
    if shot == "first_person":
        _first_person(ctx, cam, data, spec)
        _shake(ctx, cam, "rotation_euler", spec, 0.02)
        _lens(ctx, data, spec)
        return cam
    target = empty(ctx, "CameraTarget")
    track = cam.constraints.new("TRACK_TO")
    track.target = target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"
    data.dof.focus_object = target
    if spec.get("focus"):
        focus = empty(ctx, "CameraFocus", resolve(ctx, spec["focus"]))
        data.dof.focus_object = focus
    if shot == "orbit":
        cam_keys, look_keys = _orbit(ctx, spec)
    else:
        cam_keys, look_keys = _two_point(ctx, spec)
    whip_in = spec.get("whip_in")
    whip_out = spec.get("whip_out")
    if whip_in is True:
        whip_in = {}
    if whip_out is True:
        whip_out = {}
    f_in = ctx.frame(whip_in.get("duration", 0.35)) if whip_in else 1
    f_out = max(f_in + 2, ctx.nominal - round(float(whip_out.get("duration", 0.35)) * ctx.fps)) if whip_out else ctx.frames
    interp, easing = EASING[spec.get("ease", defaults["ease"])]
    following = spec.get("follow") if shot in ("tracking", "side_follow") else None
    for obj, keys in ((cam, cam_keys), (target, look_keys)):
        if obj is target and following:
            continue
        for t, point in keys:
            key(obj, "location", f_in + round((f_out - f_in) * t), point)
        set_interp(obj, interp, easing) if len(keys) <= 2 else set_interp(obj, "BEZIER")
    if following:
        actor = ctx.actors[following]
        copy = target.constraints.new("COPY_LOCATION")
        copy.target = actor.root
        copy.use_offset = True
        target.location = (0.0, 0.0, actor.height * 0.55)
    lateral_in = _lateral(cam_keys[0][1], look_keys[0][1], whip_in) if whip_in else None
    if lateral_in is not None:
        key(cam, "location", 1, cam_keys[0][1] - lateral_in * 0.35)
        if not following:
            key(target, "location", 1, look_keys[0][1] - lateral_in)
        set_interp(cam, "EXPO", "EASE_OUT", frames={1})
        set_interp(target, "EXPO", "EASE_OUT", frames={1})
    if whip_out:
        lateral_out = _lateral(cam_keys[-1][1], look_keys[-1][1], whip_out)
        key(cam, "location", ctx.frames, cam_keys[-1][1] + lateral_out * 0.35)
        if not following:
            key(target, "location", ctx.frames, look_keys[-1][1] + lateral_out)
        set_interp(cam, "EXPO", "EASE_IN", frames={f_out})
        set_interp(target, "EXPO", "EASE_IN", frames={f_out})
    distance = (cam_keys[0][1] - look_keys[0][1]).length
    _shake(ctx, target, "location", spec, max(0.05, distance / 40.0))
    _lens(ctx, data, spec)
    return cam


def _two_point(ctx, spec):
    start = resolve(ctx, spec.get("from"))
    end = resolve(ctx, spec.get("to"), start)
    look = resolve(ctx, spec.get("look"), start + Vector((0.0, 10.0, -2.0)))
    look_to = resolve(ctx, spec.get("look_to"), look)
    return [(0.0, start), (1.0, end)], [(0.0, look), (1.0, look_to)]


def _orbit(ctx, spec):
    centre = resolve(ctx, spec.get("centre"))
    radius = float(spec.get("radius", 30.0))
    height = float(spec.get("height", 15.0))
    a0 = math.radians(float(spec.get("angle_from", 0.0)))
    a1 = math.radians(float(spec.get("angle_to", 90.0)))
    look = resolve(ctx, spec.get("look"), centre)
    look_to = resolve(ctx, spec.get("look_to"), look)
    samples = max(4, ctx.frames // 3)
    linear = spec.get("ease", "in_out") == "linear"
    cam_keys = []
    for i in range(samples + 1):
        t = i / samples
        angle = a0 + (a1 - a0) * (t if linear else ease_in_out(t))
        cam_keys.append((t, Vector((centre.x + radius * math.cos(angle), centre.y + radius * math.sin(angle), centre.z + height))))
    return cam_keys, [(0.0, look), (1.0, look_to)]


def _lateral(cam_pos, look_pos, whip):
    forward = (look_pos - cam_pos)
    distance = forward.length
    forward.normalize()
    right = forward.cross(Vector((0.0, 0.0, 1.0)))
    if right.length < 1e-6:
        right = Vector((1.0, 0.0, 0.0))
    right.normalize()
    direction = whip.get("direction", "right")
    vector = {"right": right, "left": -right, "up": Vector((0.0, 0.0, 1.0)), "down": Vector((0.0, 0.0, -1.0))}[direction]
    return vector * float(whip.get("distance", 0.6)) * distance


def _first_person(ctx, cam, data, spec):
    actor = ctx.actors[spec["actor"]]
    cam.parent = actor.head
    cam.location = (0.0, 0.16, 0.14)
    cam.rotation_euler = (math.radians(90.0 - float(spec.get("pitch", 8.0))), 0.0, 0.0)
    data.dof.focus_distance = float(spec.get("focus_distance", 1.5))
    key(cam, "rotation_euler", 1)
    add_noise(cam, "rotation_euler", 0.012, 1, ctx.frames, scale=14.0)


def _shake(ctx, obj, path, spec, base):
    shake = spec.get("shake")
    if not shake:
        return
    if not obj.animation_data:
        key(obj, path, 1)
    strength = float(shake.get("strength", 1.0)) * base
    f0 = ctx.frame(shake.get("start", 0.0))
    f1 = ctx.frame(shake.get("end", ctx.duration))
    add_noise(obj, path, strength, f0, f1, scale=float(shake.get("scale", 5.0)))


def _lens(ctx, data, spec):
    if "lens_to" in spec:
        key(data, "lens", 1, float(spec.get("lens", data.lens)))
        key(data, "lens", ctx.nominal, float(spec["lens_to"]))
        set_interp(data, "SINE", "EASE_IN_OUT")
