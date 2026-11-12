"""Build the current QC scene. Scene building is intentionally idempotent."""

from __future__ import annotations
import bpy
from mathutils import Vector
from studio.environments.kitchen import create_kitchen
from studio.characters.generator import build_character, animate_reach


def point_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def build_quality_scene(profile="preview", output=None):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, 300
    scene.render.fps = 30
    scene.render.resolution_x, scene.render.resolution_y = 1080, 1920
    scene.render.resolution_percentage = 50 if profile == "preview" else 100
    # Blender API engine identifier changed between major releases.
    engine_items = bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items
    available = {item.identifier for item in engine_items}
    scene.render.engine = next(
        (e for e in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE") if e in available), "CYCLES"
    )
    if scene.render.engine == "CYCLES":
        scene.cycles.samples = 32 if profile == "preview" else 64
        scene.cycles.device = "CPU"
    else:
        scene.eevee.taa_render_samples = 48 if profile == "preview" else 96
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "AgX"
    world = bpy.data.worlds.new("Kitchen QC | deep blue ambience")
    world.use_nodes = True
    world.color = (0.025, 0.034, 0.045)
    background = world.node_tree.nodes.get("Background")
    if background:
        background.inputs["Color"].default_value = (0.025, 0.034, 0.045, 1.0)
        background.inputs["Strength"].default_value = 0.35
    scene.world = world
    create_kitchen()
    rig, parts = build_character("adult_neutral", (-1.2, -0.15, 0.03))
    animate_reach(rig)
    # Three-quarter portrait composition: face, reaching hand, tap and empty tumbler stay visible.
    bpy.ops.object.camera_add(location=(1.3, -5.0, 2.0))
    cam = bpy.context.object
    cam.name = "QC | kitchen dolly"
    point_at(cam, (-0.75, 0.35, 1.45))
    cam.data.lens = 70
    cam.data.dof.use_dof = True
    cam.data.dof.focus_object = None
    cam.data.dof.focus_distance = 5.5
    cam.data.dof.aperture_fstop = 7.1
    scene.camera = cam
    for f, pos, focus in (
        (1, (1.55, -5.8, 2.12), (-0.78, 0.32, 1.42)),
        (105, (1.35, -5.1, 2.02), (-0.78, 0.32, 1.43)),
        (220, (1.22, -4.85, 1.98), (-0.78, 0.32, 1.46)),
        (300, (1.22, -4.85, 1.98), (-0.78, 0.32, 1.46)),
    ):
        cam.location = pos
        point_at(cam, focus)
        cam.keyframe_insert(data_path="location", frame=f)
        cam.keyframe_insert(data_path="rotation_euler", frame=f)

    def area(name, loc, power, color, size, target):
        bpy.ops.object.light_add(type="AREA", location=loc)
        light = bpy.context.object
        light.name = name
        light.data.energy = power
        light.data.color = color
        light.data.shape = "DISK"
        light.data.size = size
        point_at(light, target)

    area("Window key | soft morning", (1.8, -2.6, 4.5), 520, (1.0, 0.77, 0.52), 4.0, (0, 0, 1))
    area("Cool frontal fill", (-3, -4, 2.8), 360, (0.48, 0.68, 1.0), 4.0, (0, 0, 1.3))
    area("Warm cabinet bounce", (1, 1.0, 3.3), 210, (1.0, 0.56, 0.29), 2.5, (0, 0, 1.1))
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(output or "//qc.png")
    scene.render.use_file_extension = True
    scene.render.image_settings.color_depth = "8"
    scene.camera.data.lens = 70
    # Filmic-like contrast curve with warm highlight lift.
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.frame_set(1)
    return scene
