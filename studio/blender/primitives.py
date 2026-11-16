"""Build context plus bmesh-based primitives shared by every asset and environment builder.

Everything goes through the data API (no bpy.ops) so it behaves identically in background mode.
"""

from __future__ import annotations

import math
import random

import bmesh
import bpy
from mathutils import Matrix, Vector


class Ctx:
    """Per-scene build context: materials, collection, timing, anchors, tags and actors."""

    def __init__(self, scene, collection, palette, style, profile, fps, nominal_frames, handle_frames=0, seed=0):
        self.scene = scene
        self.collection = collection
        self.palette = palette
        self.style = style
        self.profile = profile
        self.fps = fps
        self.nominal = nominal_frames
        self.frames = nominal_frames + handle_frames
        self.rng = random.Random(seed)
        self.anchors = {}
        self.objects = {}
        self.tags = {}
        self.actors = {}
        self.font = None

    def link(self, obj):
        self.collection.objects.link(obj)
        return obj

    def anchor(self, name, value):
        """Register a named world-space point (a Vector/tuple or an unparented object)."""
        if isinstance(value, bpy.types.Object):
            self.objects[name] = value
            self.anchors[name] = Vector(value.location)
        else:
            self.anchors[name] = Vector(value)
        return value

    def tag(self, name, obj):
        self.tags.setdefault(name, []).append(obj)
        return obj

    def tagged(self, name):
        return list(self.tags.get(name, []))

    def frame(self, seconds):
        """Scene-local seconds -> frame number (frame 1 is t=0)."""
        return 1 + int(round(float(seconds) * self.fps))

    def mat(self, name, **kwargs):
        return self.palette.get(name, **kwargs)

    @property
    def duration(self):
        return self.nominal / self.fps


def _finish(ctx, name, bm, materials, loc, rot, bevel=0.0, smooth=False, segments=2):
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for material in materials:
        if material is not None:
            mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    obj.location = loc
    obj.rotation_euler = rot
    if bevel:
        add_bevel(obj, bevel, segments)
    if smooth:
        mesh.shade_smooth()
    ctx.link(obj)
    return obj


def add_bevel(obj, width, segments=2, angle=40.0):
    mod = obj.modifiers.new("Bevel", "BEVEL")
    mod.width = width
    mod.segments = segments
    mod.limit_method = "ANGLE"
    mod.angle_limit = math.radians(angle)
    mod.harden_normals = True
    return mod


def _place(verts, size, anchor="center", offset=(0.0, 0.0, 0.0)):
    sx, sy, sz = size
    ox, oy, oz = offset
    shift = {"center": 0.0, "base": sz / 2.0, "top": -sz / 2.0}[anchor]
    for v in verts:
        v.co = Vector((ox + v.co.x * sx, oy + v.co.y * sy, oz + v.co.z * sz + shift))


def box(ctx, name, size, loc=(0, 0, 0), mat=None, bevel=0.0, rot=(0, 0, 0), anchor="center"):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    _place(bm.verts, size, anchor)
    return _finish(ctx, name, bm, [mat], loc, rot, bevel)


def multi_box(ctx, name, boxes, mats, loc=(0, 0, 0), rot=(0, 0, 0), bevel=0.0):
    """One mesh from many boxes: (centre, size, material_index) triples."""
    bm = bmesh.new()
    for centre, size, index in boxes:
        created = bmesh.ops.create_cube(bm, size=1.0)
        _place(created["verts"], size, "center", centre)
        for face in {f for v in created["verts"] for f in v.link_faces}:
            face.material_index = index
    return _finish(ctx, name, bm, list(mats), loc, rot, bevel)


def multi_shape(ctx, name, boxes, cylinders, mats, loc=(0, 0, 0), rot=(0, 0, 0), bevel=0.0):
    """One mesh from boxes (centre, size, material_index) and cylinders (centre, radius, depth, axis, material_index)."""
    bm = bmesh.new()
    for centre, size, index in boxes:
        created = bmesh.ops.create_cube(bm, size=1.0)
        _place(created["verts"], size, "center", centre)
        for face in {f for v in created["verts"] for f in v.link_faces}:
            face.material_index = index
    for centre, radius, depth, axis, index in cylinders:
        created = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=10, radius1=radius, radius2=radius, depth=depth)
        rotation = {"z": Matrix.Identity(4), "x": Matrix.Rotation(math.pi / 2, 4, "Y"), "y": Matrix.Rotation(math.pi / 2, 4, "X")}[axis]
        bmesh.ops.transform(bm, matrix=Matrix.Translation(Vector(centre)) @ rotation, verts=created["verts"])
        for face in {f for v in created["verts"] for f in v.link_faces}:
            face.material_index = index
    return _finish(ctx, name, bm, list(mats), loc, rot, bevel)


def cylinder(ctx, name, radius, depth, loc=(0, 0, 0), mat=None, segments=16, rot=(0, 0, 0), bevel=0.0, anchor="center", radius2=None, smooth=False):
    bm = bmesh.new()
    bmesh.ops.create_cone(
        bm,
        cap_ends=True,
        cap_tris=False,
        segments=segments,
        radius1=radius,
        radius2=radius if radius2 is None else radius2,
        depth=depth,
    )
    if anchor != "center":
        shift = depth / 2.0 if anchor == "base" else -depth / 2.0
        for v in bm.verts:
            v.co.z += shift
    return _finish(ctx, name, bm, [mat], loc, rot, bevel, smooth)


def cone(ctx, name, radius, depth, loc=(0, 0, 0), mat=None, segments=12, rot=(0, 0, 0), anchor="base", tip=0.0):
    return cylinder(ctx, name, radius, depth, loc, mat, segments, rot, 0.0, anchor, radius2=tip)


def ico(ctx, name, radius, loc=(0, 0, 0), mat=None, subdiv=1, scale=(1, 1, 1), rot=(0, 0, 0), smooth=False):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius)
    _place(bm.verts, scale)
    return _finish(ctx, name, bm, [mat], loc, rot, smooth=smooth)


def mesh_from_pydata(ctx, name, verts, faces, mats, loc=(0, 0, 0), rot=(0, 0, 0), bevel=0.0, face_mats=None, smooth=False):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    mesh.update()
    for material in mats:
        if material is not None:
            mesh.materials.append(material)
    if face_mats:
        for polygon, index in zip(mesh.polygons, face_mats, strict=False):
            polygon.material_index = index
    obj = bpy.data.objects.new(name, mesh)
    obj.location = loc
    obj.rotation_euler = rot
    if bevel:
        add_bevel(obj, bevel)
    if smooth:
        mesh.shade_smooth()
    ctx.link(obj)
    return obj


def grid(ctx, name, size, divisions, mat, loc=(0, 0, 0), height=None):
    """Flat-shaded grid mesh; `height(x, y)` may displace vertices (used by terrain and water)."""
    sx, sy = size
    nx, ny = divisions
    verts = []
    for j in range(ny + 1):
        for i in range(nx + 1):
            x = -sx / 2.0 + sx * i / nx
            y = -sy / 2.0 + sy * j / ny
            verts.append((x, y, height(x, y) if height else 0.0))
    faces = []
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    return mesh_from_pydata(ctx, name, verts, faces, [mat], loc)


def empty(ctx, name, loc=(0, 0, 0), rot=(0, 0, 0)):
    obj = bpy.data.objects.new(name, None)
    obj.location = loc
    obj.rotation_euler = rot
    obj.empty_display_size = 0.2
    ctx.link(obj)
    return obj


def parent(child, parent_obj):
    """Parent without inverse so the child's transform is expressed in parent space."""
    child.parent = parent_obj
    return child


def key(block, path, frame, value=None, index=-1):
    """Set `block.path = value` (optional) and insert a keyframe for it."""
    if value is not None:
        setattr(block, path, value)
    block.keyframe_insert(data_path=path, frame=int(frame), index=index)


def fcurves(block, path=None):
    """F-curves of an animated ID block (Blender 4.4+ slotted actions, with legacy fallback)."""
    anim = getattr(block, "animation_data", None)
    if anim is None or anim.action is None:
        return []
    action = anim.action
    curves = []
    if hasattr(action, "layers"):
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    curves.extend(bag.fcurves)
    elif hasattr(action, "fcurves"):
        curves.extend(action.fcurves)
    if path is not None:
        curves = [c for c in curves if c.data_path == path]
    return curves


def clear_keys(block, path, frame_start, frame_end):
    """Delete the keyframes of `path` between two frames (inclusive) so new keys replace them."""
    for curve in fcurves(block, path):
        doomed = [i for i, point in enumerate(curve.keyframe_points) if frame_start <= point.co.x <= frame_end]
        for index in reversed(doomed):
            curve.keyframe_points.remove(curve.keyframe_points[index])


def set_interp(block, interpolation="BEZIER", easing="AUTO", path=None, frames=None):
    for curve in fcurves(block, path):
        for point in curve.keyframe_points:
            if frames is not None and int(point.co.x) not in frames:
                continue
            point.interpolation = interpolation
            point.easing = easing
            if interpolation == "BEZIER":
                point.handle_left_type = "AUTO_CLAMPED"
                point.handle_right_type = "AUTO_CLAMPED"


def add_noise(block, path, strength, frame_start, frame_end, scale=8.0, phase=0.0, blend=4):
    """Noise F-modifier on every channel of `path`, restricted to a frame range."""
    for curve in fcurves(block, path):
        mod = curve.modifiers.new("NOISE")
        mod.strength = strength
        mod.scale = scale
        mod.phase = phase + curve.array_index * 7.3
        mod.use_restricted_range = True
        mod.frame_start = frame_start
        mod.frame_end = frame_end
        mod.blend_in = blend
        mod.blend_out = blend


def look_rotation(src, dst):
    return (Vector(dst) - Vector(src)).to_track_quat("-Z", "Y").to_euler()


def load_font(name):
    """Resolve a font by absolute path or from Blender's bundled datafiles/fonts directory."""
    import os

    path = name if os.path.isabs(name) else os.path.join(bpy.utils.system_resource("DATAFILES"), "fonts", name)
    for font in bpy.data.fonts:
        if font.filepath == path:
            return font
    return bpy.data.fonts.load(path)


def text(ctx, name, body, size, mat, loc=(0, 0, 0), rot=(0, 0, 0), align="CENTER", width=None, weight=0.0, tracking=1.0, extrude=0.0):
    curve = bpy.data.curves.new(name, "FONT")
    curve.body = body
    curve.size = size
    if ctx.font is not None:
        curve.font = ctx.font
    curve.align_x = align
    curve.align_y = "CENTER"
    curve.offset = weight
    curve.space_character = tracking
    curve.extrude = extrude
    if width:
        curve.text_boxes[0].width = width
        curve.text_boxes[0].x = -width / 2.0 if align == "CENTER" else 0.0
    obj = bpy.data.objects.new(name, curve)
    obj.location = loc
    obj.rotation_euler = rot
    if mat is not None:
        curve.materials.append(mat)
    ctx.link(obj)
    return obj
