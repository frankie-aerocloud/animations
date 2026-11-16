"""Overlay pass: titles, captions, the elapsed-time HUD and burned-in subtitles as RGBA frames.

Rendered once per project over the whole timeline with an orthographic camera whose frame maps
to x in [-0.5, 0.5] and y in [-0.889, 0.889] (portrait 9:16). Composited by FFmpeg afterwards.
"""

from __future__ import annotations

from pathlib import Path

import bpy

from studio.blender import rendering
from studio.blender.primitives import Ctx, load_font, text


class Overlay:
    def __init__(self, spec):
        self.spec = spec
        self.fps = int(spec["fps"])
        self.style = spec["style"]["overlay"]
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.scene = bpy.context.scene
        self.scene.frame_start = 1
        self.scene.frame_end = int(spec["total_frames"])
        profile = rendering.Profile(spec["profile"])
        rendering.configure(self.scene, spec["render"], profile)
        self.scene.render.film_transparent = True
        self.scene.render.image_settings.color_mode = "RGBA"
        self.scene.render.use_motion_blur = False
        self.scene.eevee.taa_render_samples = 4
        self.scene.view_settings.view_transform = "Standard"
        self.scene.view_settings.look = "None"
        collection = bpy.data.collections.new("Overlay")
        self.scene.collection.children.link(collection)
        self.ctx = Ctx(self.scene, collection, None, spec["style"], profile, self.fps, self.scene.frame_end)
        self.ctx.font = load_font(spec["font"])
        cam_data = bpy.data.cameras.new("OverlayCamera")
        cam_data.type = "ORTHO"
        cam_data.sensor_fit = "HORIZONTAL"
        cam_data.ortho_scale = 1.0
        cam = bpy.data.objects.new("OverlayCamera", cam_data)
        cam.location = (0.0, 0.0, 10.0)
        collection.objects.link(cam)
        self.scene.camera = cam
        self.fade = float(self.style.get("fade", 0.25))
        self.counter = 0

    def material(self, rgb, strength=1.0):
        self.counter += 1
        material = bpy.data.materials.new(f"overlay.{self.counter}")
        material.use_nodes = True
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        nodes.clear()
        emission = nodes.new("ShaderNodeEmission")
        emission.inputs["Color"].default_value = (*rgb, 1.0)
        emission.inputs["Strength"].default_value = strength
        transparent = nodes.new("ShaderNodeBsdfTransparent")
        mix = nodes.new("ShaderNodeMixShader")
        output = nodes.new("ShaderNodeOutputMaterial")
        mix.inputs[0].default_value = 0.0
        links.new(transparent.outputs[0], mix.inputs[1])
        links.new(emission.outputs[0], mix.inputs[2])
        links.new(mix.outputs[0], output.inputs["Surface"])
        material.surface_render_method = "BLENDED"
        material.use_backface_culling = False
        return material, mix.inputs[0]

    def card(self, name, body, size, rgb, x, y, align="CENTER", width=None, weight=0.0, tracking=1.0, shadow=0.75, z=0.0):
        """Text plus a soft dark offset copy for contrast. Returns (objects, alpha sockets)."""
        objects, sockets = [], []
        if shadow:
            shadow_mat, shadow_fac = self.material((0.0, 0.0, 0.0), 1.0)
            back = text(self.ctx, f"{name}.shadow", body, size, shadow_mat, (x + 0.0022, y - 0.0022, z - 0.02), align=align, width=width, weight=weight + 0.0015, tracking=tracking)
            objects.append(back)
            sockets.append((shadow_fac, shadow))
        material, fac = self.material(rgb, 1.0)
        front = text(self.ctx, name, body, size, material, (x, y, z), align=align, width=width, weight=weight, tracking=tracking)
        objects.append(front)
        sockets.append((fac, 1.0))
        return objects, sockets

    def plate(self, name, x, y, w, h, rgb, alpha, z=-0.05):
        material, fac = self.material(rgb, 1.0)
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata([(-w / 2, -h / 2, 0), (w / 2, -h / 2, 0), (w / 2, h / 2, 0), (-w / 2, h / 2, 0)], [], [(0, 1, 2, 3)])
        mesh.materials.append(material)
        obj = bpy.data.objects.new(name, mesh)
        obj.location = (x, y, z)
        self.ctx.link(obj)
        bevel = obj.modifiers.new("Round", "BEVEL")
        bevel.width = min(w, h) * 0.25
        bevel.segments = 6
        bevel.affect = "VERTICES"
        return obj, [(fac, alpha)]

    def visible(self, sockets, start, end, fade=None, pop=None):
        """Keyframe alpha: 0 before start, fade in, hold, fade out, 0 after end."""
        fade = self.fade if fade is None else fade
        f0, f1 = self.frame(start), self.frame(end)
        fi = min(f1 - 1, f0 + round(fade * self.fps))
        fo = max(fi, f1 - round(fade * self.fps))
        for socket, peak in sockets:
            for frame, value in ((max(1, f0 - 1), 0.0), (f0, 0.0), (fi, peak), (fo, peak), (f1, 0.0)):
                socket.default_value = value
                socket.keyframe_insert("default_value", frame=frame)
        if pop is not None:
            for obj in pop:
                obj.scale = (0.94, 0.94, 1.0)
                obj.keyframe_insert("scale", frame=f0)
                obj.scale = (1.0, 1.0, 1.0)
                obj.keyframe_insert("scale", frame=fi + 2)

    def frame(self, seconds):
        return max(1, min(self.scene.frame_end, 1 + int(round(float(seconds) * self.fps))))

    def dimensions(self, obj):
        bpy.context.view_layer.update()
        return obj.dimensions.x, obj.dimensions.y

    def build(self):
        safe = float(self.style.get("safe_width", 0.82))
        titles = self.style["title"]
        captions = self.style["caption"]
        chapters = self.style.get("chapter", titles)
        for i, card in enumerate(self.spec.get("cards", [])):
            kind = card.get("kind", "caption")
            cfg = {"title": titles, "chapter": chapters}.get(kind, captions)
            body = card["text"] if kind == "title" else card["text"].upper()
            y = float(card.get("y", cfg["y"]))
            objects, sockets = self.card(f"card{i}", body, float(cfg["size"]), tuple(cfg["colour"]), 0.0, y, width=safe, weight=float(cfg.get("weight", 0.0)), tracking=float(cfg.get("tracking", 1.0)))
            if card.get("sub"):
                sub_objects, sub_sockets = self.card(f"card{i}.sub", str(card["sub"]).upper(), float(cfg.get("sub_size", captions["size"])), tuple(cfg.get("accent", cfg["colour"])), 0.0, y - float(cfg["size"]) * 1.15, width=safe, weight=float(captions.get("weight", 0.0)), tracking=1.15)
                objects += sub_objects
                sockets += sub_sockets
            self.visible(sockets, card["start"], card["end"], pop=objects if kind in ("title", "chapter") else None)
        self.hud()
        self.subtitles()

    def hud(self):
        hud = self.spec.get("hud") or {}
        visible = hud.get("visible") or []
        if not visible:
            return
        cfg = self.style["hud"]
        x, y = float(cfg["x"]), float(cfg["y"])
        colour, accent = tuple(cfg["colour"]), tuple(cfg["accent"])
        label_objs, label_sockets = self.card("hud.label", hud.get("label", "").upper(), float(cfg["label_size"]), accent, x, y, align="LEFT", weight=0.0006, tracking=1.25)
        clock_objs, clock_sockets = self.card("hud.clock", "00:00", float(cfg["clock_size"]), colour, x, y - float(cfg["clock_size"]) * 0.95, align="LEFT", weight=0.0022, tracking=1.02)
        for start, end in visible:
            self.visible(label_sockets + clock_sockets, start, end)
        keys = sorted((float(t), float(h)) for t, h in hud.get("keys", []))
        clock_curves = [obj.data for obj in clock_objs]
        fps = self.fps
        wrap = int(hud.get("wrap") or 0)

        def update_clock(scene):
            t = (scene.frame_current - 1) / fps
            hours = _interpolate(keys, t)
            total_minutes = int(round(hours * 60.0))
            if wrap:
                total_minutes %= wrap * 60
            body = f"{total_minutes // 60:02d}:{total_minutes % 60:02d}"
            for curve in clock_curves:
                curve.body = body

        bpy.app.handlers.frame_change_pre.append(update_clock)
        for i, sub in enumerate(hud.get("subs", [])):
            objects, sockets = self.card(f"hud.sub{i}", sub["text"].upper(), float(cfg["sub_size"]), colour, x, y - float(cfg["clock_size"]) * 1.75, align="LEFT", weight=0.0005, tracking=1.2)
            self.visible(sockets, sub["start"], sub["end"])

    def subtitles(self):
        cfg = self.style["subtitle"]
        safe = float(self.style.get("safe_width", 0.82))
        y = float(cfg["y"])
        for i, cue in enumerate(self.spec.get("subtitles", [])):
            objects, sockets = self.card(f"sub{i}", cue["text"], float(cfg["size"]), tuple(cfg["colour"]), 0.0, y, width=safe, weight=float(cfg.get("weight", 0.0)), shadow=0.0, z=0.0)
            width, height = self.dimensions(objects[-1])
            plate, plate_sockets = self.plate(f"sub{i}.plate", 0.0, y, min(safe + 0.06, width + 0.07), height + 0.045, tuple(cfg["plate"]), float(cfg["plate_alpha"]))
            self.visible(sockets + plate_sockets, cue["start"], cue["end"], fade=0.12)

    def render(self):
        frames_dir = Path(self.spec["output"]["frames_dir"])
        return rendering.render(self.scene, frames_dir)


def _interpolate(keys, t):
    if not keys:
        return 0.0
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, h0), (t1, h1) in zip(keys, keys[1:], strict=False):
        if t0 <= t <= t1:
            return h0 if t1 == t0 else h0 + (h1 - h0) * (t - t0) / (t1 - t0)
    return keys[-1][1]


def run(spec):
    overlay = Overlay(spec)
    overlay.build()
    print(f"[studio] overlay: {len(spec.get('cards', []))} cards, {len(spec.get('subtitles', []))} subtitles, {spec['total_frames']} frames", flush=True)
    return overlay.render()
