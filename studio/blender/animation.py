"""Storyboard events: water levels, visibility, movement, spinning, flicker, flashes and scaling."""

from __future__ import annotations

import math
import random

import bpy
from mathutils import Vector

from studio.blender.primitives import clear_keys, fcurves, key, set_interp
from studio.core.motion import heading, polyline_length, unwrap

EASE = {"in_out": ("SINE", "EASE_IN_OUT"), "in": ("QUAD", "EASE_IN"), "out": ("QUAD", "EASE_OUT"), "linear": ("LINEAR", "AUTO"), "expo_in": ("EXPO", "EASE_IN"), "expo_out": ("EXPO", "EASE_OUT")}


def targets(ctx, ref):
    refs = ref if isinstance(ref, list) else [ref]
    found = []
    for item in refs:
        kind, _, name = str(item).partition(":")
        if kind == "tag":
            found.extend(ctx.tagged(name))
        elif kind == "object":
            found.append(ctx.objects[name])
        elif kind == "actor":
            found.append(ctx.actors[name].root)
        else:
            raise ValueError(f"unknown event target {item!r}")
    return found


def _range(ctx, event):
    start = float(event.get("start", event.get("at", 0.0)))
    end = float(event.get("end", start + float(event.get("duration", 1.0))))
    return ctx.frame(start), max(ctx.frame(start) + 1, ctx.frame(end))


def apply_events(ctx, events):
    for event in events or []:
        HANDLERS[event["type"]](ctx, event)


def water_level(ctx, event):
    f0, f1 = _range(ctx, event)
    delta = float(event.get("delta", -1.0))
    shrink = event.get("shrink")
    for obj in targets(ctx, event["target"]):
        key(obj, "location", f0)
        obj.location.z += delta
        key(obj, "location", f1)
        if shrink:
            obj.scale = (1.0, 1.0, 1.0)
            key(obj, "scale", f0)
            obj.scale = (float(shrink), float(shrink), 1.0)
            key(obj, "scale", f1)
        set_interp(obj, *EASE[event.get("ease", "in")])


def hide(ctx, event):
    frame = ctx.frame(event.get("at", event.get("start", 0.0)))
    for obj in targets(ctx, event["target"]):
        obj.hide_render = False
        key(obj, "hide_render", max(1, frame - 1))
        obj.hide_render = True
        key(obj, "hide_render", frame)


def show(ctx, event):
    frame = ctx.frame(event.get("at", event.get("start", 0.0)))
    for obj in targets(ctx, event["target"]):
        obj.hide_render = True
        key(obj, "hide_render", 1)
        key(obj, "hide_render", max(1, frame - 1))
        obj.hide_render = False
        key(obj, "hide_render", frame)


def move(ctx, event):
    f0, f1 = _range(ctx, event)
    for obj in targets(ctx, event["target"]):
        # the event owns the motion inside its range: drop keys an asset (e.g. a flock loop) set there
        clear_keys(obj, "location", f0, f1)
        if event.get("face"):
            clear_keys(obj, "rotation_euler", f0, f1)
        points = [Vector((p[0], p[1], p[2] if len(p) > 2 else obj.location.z)) for p in event["path"]]
        total = polyline_length(points)
        travelled = 0.0
        previous = obj.rotation_euler.z
        for i, point in enumerate(points):
            if i:
                travelled += (points[i] - points[i - 1]).length
            frame = f0 + round((f1 - f0) * (travelled / total if total else 0.0))
            key(obj, "location", frame, point)
            if event.get("face") and i < len(points) - 1:
                previous = unwrap(previous, heading(point, points[i + 1]))
                key(obj, "rotation_euler", frame, (0.0, 0.0, previous))
        set_interp(obj, *EASE[event.get("ease", "linear")], path="location")


def spin(ctx, event):
    f0, f1 = _range(ctx, event)
    axis = {"x": 0, "y": 1, "z": 2}[event.get("axis", "z")]
    turns = float(event.get("turns", 1.0))
    for obj in targets(ctx, event["target"]):
        key(obj, "rotation_euler", f0)
        obj.rotation_euler[axis] += turns * math.tau
        key(obj, "rotation_euler", f1)
        set_interp(obj, *EASE[event.get("ease", "linear")], path="rotation_euler")


def flicker(ctx, event):
    f0, f1 = _range(ctx, event)
    rate = max(1, round(ctx.fps / float(event.get("rate", 4.0))))
    strength = float(event.get("strength", 30.0))
    for obj in targets(ctx, event["target"]):
        socket = _emission_socket(obj)
        light = getattr(obj, "data", None) if obj.type == "LIGHT" else None
        on = True
        for frame in range(f0, f1 + 1, rate):
            if light is not None:
                key(light, "energy", frame, strength if on else 0.0)
            elif socket is not None:
                socket.default_value = strength if on else 0.0
                socket.keyframe_insert("default_value", frame=frame)
            on = not on
        if light is not None:
            key(light, "energy", f1 + 1, 0.0)
            set_interp(light, "CONSTANT")
        elif socket is not None:
            socket.default_value = 0.0
            socket.keyframe_insert("default_value", frame=f1 + 1)
            for curve in fcurves(obj.active_material.node_tree):
                for point in curve.keyframe_points:
                    point.interpolation = "CONSTANT"


def _emission_socket(obj):
    material = getattr(obj, "active_material", None)
    if material is None or not material.use_nodes:
        return None
    nodes = material.node_tree.nodes
    principled = nodes.get("Principled BSDF")
    if principled is not None:
        return principled.inputs["Emission Strength"]
    for node in nodes:
        if node.type == "EMISSION":
            return node.inputs["Strength"]
    return None


def flash(ctx, event):
    """Exposure spike: a hard, bright beat for 'the water is gone'."""
    frame = ctx.frame(event.get("at", event.get("start", 0.0)))
    amount = float(event.get("amount", 2.6))
    view = ctx.scene.view_settings
    base = view.exposure
    for f, value in ((frame - 2, base), (frame, base + amount), (frame + 2, base + amount * 0.6), (frame + round(0.5 * ctx.fps), base)):
        view.exposure = value
        view.keyframe_insert("exposure", frame=max(1, f))
    view.exposure = base


def scale(ctx, event):
    f0, f1 = _range(ctx, event)
    start = event.get("from")
    end = event.get("to", [0.001, 0.001, 0.001])
    for obj in targets(ctx, event["target"]):
        if start is not None:
            obj.scale = tuple(float(v) for v in start)
        key(obj, "scale", f0)
        obj.scale = tuple(float(v) for v in end)
        key(obj, "scale", f1)
        set_interp(obj, *EASE[event.get("ease", "in")], path="scale")


def deplete(ctx, event):
    """Hide tagged objects one after another, ordered along an axis (or by 'order' property)."""
    f0, f1 = _range(ctx, event)
    axis = {"x": 0, "y": 1, "z": 2}.get(event.get("order", "x"))
    objects = targets(ctx, event["target"])
    if axis is None:
        objects.sort(key=lambda o: o.get("order", 0))
    else:
        objects.sort(key=lambda o: o.location[axis], reverse=bool(event.get("reverse", False)))
    for i, obj in enumerate(objects):
        frame = f0 + round((f1 - f0) * i / max(1, len(objects) - 1))
        obj.hide_render = False
        key(obj, "hide_render", max(1, frame - 1))
        obj.hide_render = True
        key(obj, "hide_render", frame)


def sun(ctx, event):
    f0, f1 = _range(ctx, event)
    light = ctx.objects["sun"].data
    key(light, "energy", f0)
    if "energy" in event:
        light.energy = float(event["energy"])
    key(light, "energy", f1)
    if "colour" in event:
        key(light, "color", f0)
        light.color = tuple(event["colour"])
        key(light, "color", f1)


def _material_emission(material):
    if material is None or not material.use_nodes:
        return None
    nodes = material.node_tree.nodes
    principled = nodes.get("Principled BSDF")
    if principled is not None:
        return principled.inputs["Emission Strength"]
    for node in nodes:
        if node.type == "EMISSION":
            return node.inputs["Strength"]
    return None


def blackout(ctx, event):
    """Switch tagged emissive materials (and tagged lights) off in a staggered sweep."""
    f0, f1 = _range(ctx, event)
    refs = event["target"] if isinstance(event["target"], list) else [event["target"]]
    items = []
    for ref in refs:
        kind, _, name = str(ref).partition(":")
        items.extend(ctx.tagged(name))
    if event.get("shuffle", True):
        random.Random(int(event.get("seed", 7))).shuffle(items)
    for i, item in enumerate(items):
        frame = f0 + round((f1 - f0) * i / max(1, len(items) - 1))
        if isinstance(item, bpy.types.Material):
            socket = _material_emission(item)
            if socket is None:
                continue
            socket.keyframe_insert("default_value", frame=max(1, frame - 1))
            socket.default_value = 0.0
            socket.keyframe_insert("default_value", frame=frame)
            for curve in fcurves(item.node_tree):
                for point in curve.keyframe_points:
                    point.interpolation = "CONSTANT"
        elif getattr(item, "type", None) == "LIGHT":
            key(item.data, "energy", max(1, frame - 1))
            key(item.data, "energy", frame, 0.0)
            set_interp(item.data, "CONSTANT")


HANDLERS = {
    "water_level": water_level,
    "hide": hide,
    "show": show,
    "move": move,
    "spin": spin,
    "flicker": flicker,
    "flash": flash,
    "scale": scale,
    "deplete": deplete,
    "sun": sun,
    "blackout": blackout,
}
