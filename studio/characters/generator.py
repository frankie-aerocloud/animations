"""Asset-backed, human-proportioned characters and reusable skeletal actions."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Callable

import bmesh
import bpy
from mathutils import Matrix

from .registry import CHARACTERS

ASSET_ROOT = (
    Path(__file__).resolve().parents[2]
    / "assets"
    / "characters"
    / "quaternius-universal-base-characters"
)
SOURCE_HEIGHT = 1.775
_instance = 0

CONTROL_BONES = {
    "spine": "spine_02",
    "chest": "spine_03",
    "head": "Head",
    "shoulder.L": "upperarm_l",
    "elbow.L": "lowerarm_l",
    "hand.L": "hand_l",
    "shoulder.R": "upperarm_r",
    "elbow.R": "lowerarm_r",
    "hand.R": "hand_r",
    "hip.L": "thigh_l",
    "knee.L": "calf_l",
    "foot.L": "foot_l",
    "hip.R": "thigh_r",
    "knee.R": "calf_r",
    "foot.R": "foot_r",
}
NATURAL_ARM_Z = {"L": -1.24, "R": 1.24}


def _material(name: str, color: tuple[float, float, float, float], roughness=0.72):
    material = bpy.data.materials.new(name)
    material.diffuse_color = color
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    if shader:
        shader.inputs["Base Color"].default_value = color
        shader.inputs["Roughness"].default_value = roughness
    return material


def _import_gltf(path: Path) -> list[Any]:
    if not path.exists():
        raise RuntimeError(
            f"Humanoid asset is missing: {path}. Restore the registered character asset."
        )
    before = {obj.as_pointer() for obj in bpy.data.objects}
    result = bpy.ops.import_scene.gltf(filepath=str(path))
    if "FINISHED" not in result:
        raise RuntimeError(f"Blender could not import humanoid asset: {path}")
    return [obj for obj in bpy.data.objects if obj.as_pointer() not in before]


def _remove_export_helpers(objects: list[Any]) -> None:
    for obj in list(objects):
        if obj.type == "MESH" and obj.name.startswith("Icosphere") and not obj.data.materials:
            bpy.data.objects.remove(obj, do_unlink=True)
            objects.remove(obj)


def _tint_skin(body, tint: tuple[float, float, float, float]) -> None:
    """Tint the source skin lightly while retaining its painted facial detail."""
    for slot in body.material_slots:
        if not slot.material:
            continue
        material = slot.material.copy()
        material.name = f"{body.name} | skin texture"
        slot.material = material
        material.use_nodes = True
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        shader = nodes.get("Principled BSDF")
        if not shader:
            continue
        base = shader.inputs.get("Base Color")
        if not base or not base.is_linked:
            continue
        source = base.links[0].from_socket
        links.remove(base.links[0])
        mix = nodes.new("ShaderNodeMixRGB")
        mix.name = "Subtle skin-tone variation"
        mix.blend_type = "MIX"
        mix.inputs[0].default_value = 0.12
        mix.inputs[2].default_value = tint
        links.new(source, mix.inputs[1])
        links.new(mix.outputs[0], base)


def _dominant_group(body, vertex) -> str:
    if not vertex.groups:
        return ""
    weighted = max(vertex.groups, key=lambda assignment: assignment.weight)
    return body.vertex_groups[weighted.group].name


def _body_layer(
    body,
    rig,
    name: str,
    material,
    keep: Callable[[str, Any], bool],
    offset: float,
):
    """Make fitted clothing from the source topology so every joint deforms smoothly."""
    layer = body.copy()
    layer.data = body.data.copy()
    layer.name = name
    layer.data.name = f"{name} | fitted topology"
    bpy.context.collection.objects.link(layer)
    layer.parent = rig
    layer.matrix_parent_inverse = Matrix.Identity(4)
    for modifier in layer.modifiers:
        if modifier.type == "ARMATURE":
            modifier.object = rig

    keep_indices = {
        vertex.index
        for vertex in body.data.vertices
        if keep(_dominant_group(body, vertex), vertex.co)
    }
    mesh = layer.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(
        bm,
        geom=[vertex for vertex in bm.verts if vertex.index not in keep_indices],
        context="VERTS",
    )
    bm.to_mesh(mesh)
    bm.free()
    mesh.validate()
    mesh.update()
    for vertex in mesh.vertices:
        vertex.co += vertex.normal * offset
    mesh.materials.clear()
    mesh.materials.append(material)
    solidify = layer.modifiers.new("Tailored cloth thickness", "SOLIDIFY")
    solidify.thickness = 0.005
    solidify.offset = 0.0
    return layer


def _bind_rigid_accessory(obj, rig, bone_name: str):
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    obj.select_set(False)
    obj.parent = rig
    obj.matrix_parent_inverse = Matrix.Identity(4)
    group = obj.vertex_groups.new(name=bone_name)
    group.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
    modifier = obj.modifiers.new("Follow humanoid rig", "ARMATURE")
    modifier.object = rig
    return obj


def _add_role_clothing(instance: str, body, rig, cfg: dict[str, Any]) -> list[Any]:
    shirt = _material(f"{instance} | shirt", cfg["shirt"], 0.72)
    trousers = _material(f"{instance} | trousers", cfg["trousers"], 0.78)
    shoes = _material(f"{instance} | shoes", cfg.get("shoes", (0.04, 0.05, 0.06, 1)), 0.4)
    long_sleeves = bool(cfg.get("long_sleeves", True))
    trouser_groups = {"pelvis", "thigh_l", "thigh_r", "calf_l", "calf_r"}

    top = _body_layer(
        body,
        rig,
        f"{instance} | fitted role shirt",
        shirt,
        lambda group, co: (
            0.98 < co.z
            < 1.48 + 0.08 * min(abs(co.x) / 0.12, 1.0)
            and abs(co.x) < (0.64 if long_sleeves else 0.40)
        ),
        0.008,
    )
    pants = _body_layer(
        body,
        rig,
        f"{instance} | fitted trousers",
        trousers,
        lambda group, co: group in trouser_groups and co.z > 0.035,
        0.009,
    )
    parts = [top, pants]

    bpy.ops.mesh.primitive_torus_add(
        major_radius=0.105,
        minor_radius=0.014,
        major_segments=36,
        minor_segments=10,
        location=(0, -0.002, 1.485),
    )
    collar = bpy.context.object
    collar.name = f"{instance} | fitted collar"
    collar.scale = (1.0, 0.82, 1.0)
    collar.data.materials.append(shirt)
    parts.append(_bind_rigid_accessory(collar, rig, "spine_03"))

    for side, center_x in (("L", 0.11), ("R", -0.11)):
        half_width = 0.095
        front, back = -0.18, 0.11
        bottom = 0.012
        vertices = [
            (center_x - half_width, front, bottom),
            (center_x + half_width, front, bottom),
            (center_x + half_width * 0.86, back, bottom),
            (center_x - half_width * 0.86, back, bottom),
            (center_x - half_width * 0.92, front, 0.09),
            (center_x + half_width * 0.92, front, 0.09),
            (center_x + half_width * 0.78, back, 0.14),
            (center_x - half_width * 0.78, back, 0.14),
        ]
        faces = [
            (0, 1, 2, 3),
            (4, 7, 6, 5),
            (0, 4, 5, 1),
            (1, 5, 6, 2),
            (2, 6, 7, 3),
            (3, 7, 4, 0),
        ]
        mesh = bpy.data.meshes.new(f"{instance} | shoe last {side}")
        mesh.from_pydata(vertices, [], faces)
        mesh.materials.append(shoes)
        shoe = bpy.data.objects.new(f"{instance} | structured shoe {side}", mesh)
        bpy.context.collection.objects.link(shoe)
        bevel = shoe.modifiers.new("Rounded shoe last", "BEVEL")
        bevel.width = 0.035
        bevel.segments = 4
        parts.append(_bind_rigid_accessory(shoe, rig, f"foot_{side.lower()}"))

    if cfg.get("role") == "farmer":
        hat_material = _material(
            f"{instance} | field hat", cfg.get("hat_colour", (0.68, 0.45, 0.18, 1)), 0.82
        )
        bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.245, depth=0.025, location=(0, 0, 1.77))
        brim = bpy.context.object
        brim.name = f"{instance} | field hat brim"
        brim.data.materials.append(hat_material)
        parts.append(_bind_rigid_accessory(brim, rig, "Head"))
        bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.145, depth=0.14, location=(0, 0.015, 1.83))
        crown = bpy.context.object
        crown.name = f"{instance} | field hat crown"
        crown.data.materials.append(hat_material)
        bevel = crown.modifiers.new("Soft hat crown", "BEVEL")
        bevel.width = 0.025
        bevel.segments = 3
        parts.append(_bind_rigid_accessory(crown, rig, "Head"))
    return parts


def _add_hair(instance: str, rig, cfg: dict[str, Any]) -> list[Any]:
    path = ASSET_ROOT / "hair" / f"{cfg['hair_asset']}.gltf"
    imported = _import_gltf(path)
    _remove_export_helpers(imported)
    source_rig = next((obj for obj in imported if obj.type == "ARMATURE"), None)
    hair_parts = [obj for obj in imported if obj.type == "MESH"]
    if source_rig is None or not hair_parts:
        raise RuntimeError(f"Hairstyle asset has no usable rigged mesh: {path}")
    hair_material = _material(
        f"{instance} | hair", cfg.get("hair_colour", (0.08, 0.045, 0.025, 1)), 0.58
    )
    for index, obj in enumerate(hair_parts):
        obj.name = f"{instance} | hair {index + 1}"
        obj.parent = rig
        obj.matrix_parent_inverse = Matrix.Identity(4)
        for modifier in obj.modifiers:
            if modifier.type == "ARMATURE":
                modifier.object = rig
        obj.data.materials.clear()
        obj.data.materials.append(hair_material)
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
    bpy.data.objects.remove(source_rig, do_unlink=True)
    return hair_parts


def _add_face_shapes(instance: str, body, eyes, brows) -> None:
    if eyes and eyes.type == "MESH":
        eyes.name = f"{instance} | eyes"
        eyes.shape_key_add(name="Basis")
        blink = eyes.shape_key_add(name="Blink")
        center = sum(vertex.co.z for vertex in eyes.data.vertices) / max(1, len(eyes.data.vertices))
        for point in blink.data:
            point.co.z = center + (point.co.z - center) * 0.08
    if brows and brows.type == "MESH":
        brows.name = f"{instance} | eyebrows"
        brows.shape_key_add(name="Basis")
        concern = brows.shape_key_add(name="Concern")
        alarm = brows.shape_key_add(name="Alarm")
        for source, concerned, alarmed in zip(
            brows.data.vertices, concern.data, alarm.data, strict=True
        ):
            inner_weight = max(0.0, 1.0 - abs(source.co.x) / 0.075)
            concerned.co.z += 0.013 * inner_weight - 0.003 * (1.0 - inner_weight)
            alarmed.co.z += 0.014


def _pose_bone(rig, control: str):
    return rig.pose.bones[CONTROL_BONES[control]]


def _key_rotation(bone, frame: int, rotation: tuple[float, float, float]) -> None:
    bone.rotation_mode = "XYZ"
    bone.rotation_euler = rotation
    bone.keyframe_insert(data_path="rotation_euler", frame=int(frame))


def _set_natural_pose(rig) -> None:
    for side in ("L", "R"):
        upper = _pose_bone(rig, f"shoulder.{side}")
        lower = _pose_bone(rig, f"elbow.{side}")
        upper.rotation_mode = "XYZ"
        lower.rotation_mode = "XYZ"
        upper.rotation_euler = (0.08, 0.0, NATURAL_ARM_Z[side])
        lower.rotation_euler = (0.10, 0.0, -0.08 if side == "L" else 0.08)


def build_character(name: str = "adult_neutral", origin=(0.0, 0.0, 0.0)):
    """Import, dress and return a human-proportioned character and humanoid rig."""
    global _instance
    _instance += 1
    if name not in CHARACTERS:
        raise ValueError(f"Unknown character style {name!r}; choose one of {sorted(CHARACTERS)}")
    cfg: dict[str, Any] = CHARACTERS[name]
    instance = f"{name}_{_instance:02d}"
    gender = cfg.get("gender", "male")
    path = ASSET_ROOT / "base" / f"Superhero_{gender.title()}_FullBody.gltf"
    imported = _import_gltf(path)
    _remove_export_helpers(imported)
    rig = next((obj for obj in imported if obj.type == "ARMATURE"), None)
    meshes = [obj for obj in imported if obj.type == "MESH"]
    body = max(meshes, key=lambda obj: len(obj.data.vertices), default=None)
    if rig is None or body is None:
        raise RuntimeError(f"Humanoid asset is incomplete: {path}")

    def uses_material(obj, prefix: str) -> bool:
        return any(
            slot.material and slot.material.name.startswith(prefix)
            for slot in obj.material_slots
        )

    eyes = next((obj for obj in meshes if uses_material(obj, "MI_Eyes")), None)
    brows = next((obj for obj in meshes if uses_material(obj, "MI_Hair")), None)

    rig.name = f"{instance} | humanoid rig"
    body.name = f"{instance} | anatomical body"
    _tint_skin(body, cfg["skin"])
    for polygon in body.data.polygons:
        polygon.use_smooth = True
    _add_face_shapes(instance, body, eyes, brows)
    clothing = _add_role_clothing(instance, body, rig, cfg)
    hair = _add_hair(instance, rig, cfg)

    scale = float(cfg.get("height", 1.72)) / SOURCE_HEIGHT
    rig.scale = (scale, scale, scale)
    rig.location = origin
    rig["character_id"] = instance
    rig["style"] = name
    rig["height"] = float(cfg.get("height", 1.72))
    rig["backend"] = "quaternius_humanoid"
    _set_natural_pose(rig)
    parts = [obj for obj in imported if obj.type == "MESH"] + clothing + hair
    return rig, parts


def set_expression(rig, expression: str, frame: int):
    """Animate subtle eyebrow expressions on the imported human face."""
    if expression not in {"neutral", "concern", "alarm", "smile"}:
        expression = "concern"
    brows = bpy.data.objects.get(f"{rig.get('character_id', '')} | eyebrows")
    if not brows or not brows.data.shape_keys:
        return
    keys = brows.data.shape_keys.key_blocks
    values = {
        "Concern": 1.0 if expression == "concern" else 0.0,
        "Alarm": 1.0 if expression == "alarm" else 0.0,
    }
    for key_name, value in values.items():
        if key_name in keys:
            keys[key_name].value = value
            keys[key_name].keyframe_insert(data_path="value", frame=int(frame))


def pose_head(rig, turn: float, frame: int) -> None:
    """Turn the head without exposing asset-specific bone names to scene builders."""
    head = _pose_bone(rig, "head")
    head.rotation_mode = "XYZ"
    head.rotation_euler[1] = turn
    head.keyframe_insert(data_path="rotation_euler", frame=int(frame))


def animate_idle(rig, duration_frames: int, seed: int = 0):
    """Add breathing, gaze changes and two natural blinks."""
    duration_frames = int(round(duration_frames))
    phase = (seed % 7) * 0.31
    spine = _pose_bone(rig, "spine")
    head = _pose_bone(rig, "head")
    for frame in (1, max(2, duration_frames // 3), max(3, duration_frames * 2 // 3), duration_frames):
        t = frame / max(1, duration_frames)
        _key_rotation(spine, frame, (0.014 * math.sin(math.tau * t + phase), 0.0, 0.0))
        _key_rotation(head, frame, (0.0, 0.025 * math.sin(math.tau * t * 1.4 + phase), 0.0))
    eyes = bpy.data.objects.get(f"{rig.get('character_id', '')} | eyes")
    if eyes and eyes.data.shape_keys and "Blink" in eyes.data.shape_keys.key_blocks:
        blink_key = eyes.data.shape_keys.key_blocks["Blink"]
        for blink in (max(5, round(duration_frames * 0.29)), max(8, round(duration_frames * 0.73))):
            for offset, value in ((0, 0.0), (2, 1.0), (4, 0.0)):
                blink_key.value = value
                blink_key.keyframe_insert(data_path="value", frame=blink + offset)


def animate_walk(rig, duration_frames: int, cycle_frames: int = 24):
    """Walk with opposing limbs, bent knees and naturally lowered arms."""
    duration_frames = int(round(duration_frames))
    frames = list(range(1, duration_frames + 1, 6))
    if frames[-1] != duration_frames:
        frames.append(duration_frames)
    for frame in frames:
        phase = math.tau * (frame - 1) / cycle_frames
        swing = math.sin(phase)
        for side, sign in (("L", 1), ("R", -1)):
            _key_rotation(_pose_bone(rig, f"hip.{side}"), frame, (0.34 * sign * swing, 0, 0))
            _key_rotation(
                _pose_bone(rig, f"knee.{side}"),
                frame,
                (-0.42 * max(0.0, -sign * swing), 0, 0),
            )
            _key_rotation(
                _pose_bone(rig, f"shoulder.{side}"),
                frame,
                (-0.20 * sign * swing, 0, NATURAL_ARM_Z[side]),
            )
            _key_rotation(
                _pose_bone(rig, f"elbow.{side}"),
                frame,
                (0.12 + 0.08 * max(0.0, sign * swing), 0, -0.08 if side == "L" else 0.08),
            )


def animate_point(rig, duration_frames: int):
    """Lift one arm from rest and point toward the scene."""
    duration_frames = int(round(duration_frames))
    upper = _pose_bone(rig, "shoulder.L")
    lower = _pose_bone(rig, "elbow.L")
    for frame, amount in ((1, 0.0), (round(duration_frames * 0.36), 1.0), (round(duration_frames * 0.62), 1.0), (duration_frames, 0.0)):
        _key_rotation(upper, frame, (0.16 + 0.10 * amount, 0, NATURAL_ARM_Z["L"] * (1 - amount)))
        _key_rotation(lower, frame, (0.10 + 0.12 * amount, 0, -0.08 * (1 - amount)))


def animate_carry(rig, duration_frames: int):
    """Bring both forearms forward into a believable carrying pose."""
    duration_frames = int(round(duration_frames))
    for side, sign in (("L", -1), ("R", 1)):
        upper = _pose_bone(rig, f"shoulder.{side}")
        lower = _pose_bone(rig, f"elbow.{side}")
        for frame, amount in ((1, 0.0), (round(duration_frames * 0.30), 1.0), (duration_frames, 1.0)):
            _key_rotation(
                upper,
                frame,
                (0.35 * amount + 0.08 * (1 - amount), 0, sign * (1.24 - 0.29 * amount)),
            )
            _key_rotation(lower, frame, (0.18 + 1.02 * amount, 0, sign * 0.08))


def animate_reach(rig, duration_frames: int = 300):
    """Reach toward the tap, pause, then settle into concern."""
    duration_frames = int(round(duration_frames))
    upper = _pose_bone(rig, "shoulder.L")
    lower = _pose_bone(rig, "elbow.L")
    head = _pose_bone(rig, "head")
    for frame, reach in ((1, 0.0), (round(duration_frames * 0.26), 0.2), (round(duration_frames * 0.37), 1.0), (round(duration_frames * 0.49), 0.92), (round(duration_frames * 0.62), 0.12), (duration_frames, 0.0)):
        _key_rotation(upper, frame, (0.10 + 0.10 * reach, 0, NATURAL_ARM_Z["L"] * (1 - reach)))
        _key_rotation(lower, frame, (0.10 + 0.12 * reach, 0, -0.08 * (1 - reach)))
        _key_rotation(head, frame, (-0.04 * reach, 0.0, -0.05 * reach))
    set_expression(rig, "concern", round(duration_frames * 0.55))
