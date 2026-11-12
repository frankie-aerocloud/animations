"""Reusable Blender builders for the seven-scene water-short production."""

from __future__ import annotations

import math
import random
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

from studio.characters.generator import (
    animate_carry,
    animate_idle,
    animate_point,
    animate_reach,
    animate_walk,
    build_character,
    pose_head,
    set_expression,
)
from studio.environments.kitchen import create_kitchen


def mat(name, color, roughness=0.62, metallic=0.0, emission=0.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1.0)
    m.use_nodes = True
    nodes = m.node_tree.nodes
    shader = nodes.get("Principled BSDF")
    if shader:
        shader.inputs["Base Color"].default_value = (*color, 1.0)
        shader.inputs["Roughness"].default_value = roughness
        shader.inputs["Metallic"].default_value = metallic
        if "Emission Color" in shader.inputs:
            shader.inputs["Emission Color"].default_value = (*color, 1.0)
            shader.inputs["Emission Strength"].default_value = emission
    return m


def box(name, loc, size, material, bevel=0.035):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if material:
        o.data.materials.append(material)
    if bevel:
        mod = o.modifiers.new("Soft crafted edges", "BEVEL")
        mod.width = bevel
        mod.segments = 3
        o.modifiers.new("Weighted corner normals", "WEIGHTED_NORMAL")
    return o


def orb(name, loc, scale, material, segments=32, ring_count=20):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=ring_count, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    o.data.materials.append(material)
    bpy.ops.object.shade_smooth()
    return o


def cylinder(name, loc, radius, depth, material, rotation=(0, 0, 0), vertices=32):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices, radius=radius, depth=depth, location=loc, rotation=rotation
    )
    o = bpy.context.object
    o.name = name
    o.data.materials.append(material)
    for face in o.data.polygons:
        face.use_smooth = True
    bevel = o.modifiers.new("Rounded edge", "BEVEL")
    bevel.width = min(radius * 0.18, 0.035)
    bevel.segments = 2
    return o


def animate(obj, path, keys):
    for frame, value in keys:
        setattr(obj, path, value)
        obj.keyframe_insert(data_path=path, frame=frame)


def parent_keep(child, parent):
    child.parent = parent
    child.matrix_parent_inverse = Matrix.Identity(4)


def add_camera(scene, start, target, end=None, lens=58):
    bpy.ops.object.camera_add(location=start)
    camera = bpy.context.object
    camera.name = "Cinematic camera"
    camera.data.lens = lens
    camera.data.clip_end = 300
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera
    if end:
        camera.keyframe_insert(data_path="location", frame=1)
        camera.keyframe_insert(data_path="rotation_euler", frame=1)
        camera.location = end
        camera.rotation_euler = (
            (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
        )
        camera.keyframe_insert(data_path="location", frame=scene.frame_end)
        camera.keyframe_insert(data_path="rotation_euler", frame=scene.frame_end)
    return camera


def area_light(name, loc, target, power, color, size):
    bpy.ops.object.light_add(type="AREA", location=loc)
    light = bpy.context.object
    light.name = name
    light.data.energy = power
    light.data.color = color
    light.data.shape = "DISK"
    light.data.size = size
    light.rotation_euler = (Vector(target) - light.location).to_track_quat("-Z", "Y").to_euler()
    return light


def emission(name, color, strength=1.0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    nodes = m.node_tree.nodes
    nodes.clear()
    emit = nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (*color, 1)
    emit.inputs["Strength"].default_value = strength
    output = nodes.new("ShaderNodeOutputMaterial")
    m.node_tree.links.new(emit.outputs[0], output.inputs["Surface"])
    return m


EARTH_TEXTURES = Path(__file__).resolve().parents[2] / "earth-textures"


def _load_packed_texture(filename: str, *, non_color: bool = False):
    """Load a project-local texture and pack it into the generated blend file."""
    path = EARTH_TEXTURES / filename
    if not path.is_file():
        raise FileNotFoundError(f"Earth texture is missing: {path}")
    image = bpy.data.images.load(str(path), check_existing=True)
    image.name = filename
    if non_color:
        image.colorspace_settings.name = "Non-Color"
    if not image.packed_file:
        image.pack()
    return image


def _earth_surface_material():
    material = bpy.data.materials.new("Earth | mapped photographic surface")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    shader = nodes.get("Principled BSDF")
    if shader is None:
        raise RuntimeError("Blender did not create the Earth Principled shader")

    uv = nodes.new("ShaderNodeTexCoord")
    diffuse = nodes.new("ShaderNodeTexImage")
    diffuse.name = "Earth albedo | 6K"
    diffuse.image = _load_packed_texture("Earth_Diffuse_6K.jpg")
    links.new(uv.outputs["UV"], diffuse.inputs["Vector"])
    links.new(diffuse.outputs["Color"], shader.inputs["Base Color"])

    gloss = nodes.new("ShaderNodeTexImage")
    gloss.name = "Earth ocean gloss | 6K"
    gloss.image = _load_packed_texture("Earth_Glossiness_6K.jpg", non_color=True)
    links.new(uv.outputs["UV"], gloss.inputs["Vector"])
    gloss_bw = nodes.new("ShaderNodeRGBToBW")
    links.new(gloss.outputs["Color"], gloss_bw.inputs["Color"])
    roughness = nodes.new("ShaderNodeMath")
    roughness.operation = "SUBTRACT"
    roughness.inputs[0].default_value = 1.0
    links.new(gloss_bw.outputs["Val"], roughness.inputs[1])
    links.new(roughness.outputs["Value"], shader.inputs["Roughness"])

    normal_image = nodes.new("ShaderNodeTexImage")
    normal_image.name = "Earth relief | normal 6K"
    normal_image.image = _load_packed_texture("Earth_NormalNRM_6K.jpg", non_color=True)
    links.new(uv.outputs["UV"], normal_image.inputs["Vector"])
    normal = nodes.new("ShaderNodeNormalMap")
    normal.inputs["Strength"].default_value = 0.28
    links.new(normal_image.outputs["Color"], normal.inputs["Color"])
    links.new(normal.outputs["Normal"], shader.inputs["Normal"])

    lights = nodes.new("ShaderNodeTexImage")
    lights.name = "Earth city lights | 6K"
    lights.image = _load_packed_texture("Earth_Illumination_6K.jpg")
    links.new(uv.outputs["UV"], lights.inputs["Vector"])
    emission_color = shader.inputs.get("Emission Color")
    emission_strength = shader.inputs.get("Emission Strength")
    if emission_color and emission_strength:
        links.new(lights.outputs["Color"], emission_color)
        emission_strength.default_value = 0.28
    return material


def _earth_cloud_material():
    material = bpy.data.materials.new("Earth | high cloud veil")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    uv = nodes.new("ShaderNodeTexCoord")
    cloud_image = nodes.new("ShaderNodeTexImage")
    cloud_image.name = "Earth cloud density | 6K"
    cloud_image.image = _load_packed_texture("Earth_Clouds_6K.jpg", non_color=True)
    links.new(uv.outputs["UV"], cloud_image.inputs["Vector"])
    density = nodes.new("ShaderNodeRGBToBW")
    links.new(cloud_image.outputs["Color"], density.inputs["Color"])
    mask = nodes.new("ShaderNodeValToRGB")
    mask.color_ramp.elements[0].position = 0.54
    mask.color_ramp.elements[1].position = 0.76
    links.new(density.outputs["Val"], mask.inputs["Fac"])
    transparent = nodes.new("ShaderNodeBsdfTransparent")
    cloud = nodes.new("ShaderNodeBsdfPrincipled")
    cloud.inputs["Base Color"].default_value = (0.72, 0.82, 0.92, 1)
    cloud.inputs["Roughness"].default_value = 0.92
    mix = nodes.new("ShaderNodeMixShader")
    links.new(mask.outputs["Color"], mix.inputs[0])
    links.new(transparent.outputs[0], mix.inputs[1])
    links.new(cloud.outputs[0], mix.inputs[2])
    output = nodes.new("ShaderNodeOutputMaterial")
    links.new(mix.outputs[0], output.inputs["Surface"])
    material.surface_render_method = "DITHERED"
    return material


def _earth_space_world(scene):
    world = scene.world
    if world is None:
        world = bpy.data.worlds.new("Earth | textured deep-space sky")
        scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    background = nodes.get("Background")
    if background is None:
        background = nodes.new("ShaderNodeBackground")
    texcoord = nodes.new("ShaderNodeTexCoord")
    haze = nodes.new("ShaderNodeTexEnvironment")
    haze.name = "Blue space haze"
    haze.image = _load_packed_texture("Blue_Haze.jpg")
    stars = nodes.new("ShaderNodeTexEnvironment")
    stars.name = "Star field"
    stars.image = _load_packed_texture("Stars_1K.jpg")
    links.new(texcoord.outputs["Generated"], haze.inputs["Vector"])
    links.new(texcoord.outputs["Generated"], stars.inputs["Vector"])
    combine = nodes.new("ShaderNodeMixRGB")
    combine.blend_type = "SCREEN"
    combine.inputs[0].default_value = 0.62
    links.new(haze.outputs["Color"], combine.inputs[1])
    links.new(stars.outputs["Color"], combine.inputs[2])
    links.new(combine.outputs["Color"], background.inputs["Color"])
    background.inputs["Strength"].default_value = 0.45


def camera_text(camera, title, subline=""):
    """Unified portrait safe areas: contrast plate at top, scene caption at bottom."""
    overlay_scale = camera.data.lens / 55.0
    overlay_depth = 5.0 * overlay_scale
    white = emission("Typography | warm white", (0.97, 0.95, 0.88), 1.35)
    aqua = emission("Typography | glacial cyan", (0.20, 0.78, 0.84), 1.2)
    plate_mat = emission("Typography | midnight plate", (0.018, 0.035, 0.055), 0.95)
    top_plate = box(
        "Safe area | headline plate",
        (0, 0, 0),
        (1.62 * overlay_scale, 0.72 * overlay_scale, 0.018 * overlay_scale),
        plate_mat,
        0.045 * overlay_scale,
    )
    parent_keep(top_plate, camera)
    top_plate.location = (0, 0.69 * overlay_scale, -overlay_depth)
    accent = box(
        "Title accent | fixed left rail",
        (0, 0, 0),
        (0.028 * overlay_scale, 0.34 * overlay_scale, 0.012 * overlay_scale),
        aqua,
        0.012 * overlay_scale,
    )
    parent_keep(accent, camera)
    accent.location = (
        -0.70 * overlay_scale,
        0.69 * overlay_scale,
        -overlay_depth + 0.025 * overlay_scale,
    )
    font_curve = bpy.data.curves.new("Scene headline", "FONT")
    font_curve.body = title.upper()
    font_curve.align_x = "LEFT"
    font_curve.align_y = "CENTER"
    longest_line = max(len(line) for line in title.splitlines())
    font_curve.size = min(0.105, 1.13 / max(12, longest_line * 0.54)) * overlay_scale
    font_curve.extrude = 0.0008
    text = bpy.data.objects.new("Scene headline", font_curve)
    bpy.context.collection.objects.link(text)
    text.data.materials.append(white)
    parent_keep(text, camera)
    text.location = (
        -0.61 * overlay_scale,
        0.82 * overlay_scale,
        -overlay_depth + 0.045 * overlay_scale,
    )
    sub_curve = bpy.data.curves.new("Scene supporting line", "FONT")
    sub_curve.body = subline.upper()
    sub_curve.align_x = "LEFT"
    sub_curve.align_y = "CENTER"
    sub_curve.size = min(0.046, 1.22 / max(16, len(subline) * 0.54)) * overlay_scale
    subtitle = bpy.data.objects.new("Scene supporting line", sub_curve)
    bpy.context.collection.objects.link(subtitle)
    subtitle.data.materials.append(aqua)
    parent_keep(subtitle, camera)
    subtitle.location = (
        -0.61 * overlay_scale,
        0.38 * overlay_scale,
        -overlay_depth + 0.045 * overlay_scale,
    )
    accent.scale = (0.01, 1, 1)
    accent.keyframe_insert(data_path="scale", frame=1)
    accent.scale = (1, 1, 1)
    accent.keyframe_insert(data_path="scale", frame=18)
    text.scale = (0.92, 0.92, 0.92)
    text.keyframe_insert(data_path="scale", frame=1)
    text.scale = (1, 1, 1)
    text.keyframe_insert(data_path="scale", frame=18)
    return text, subtitle


def setup(scene_id, duration, fps, profile):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = round(duration * fps)
    scene.render.fps = fps
    scene.render.resolution_x, scene.render.resolution_y = 1080, 1920
    scene.render.resolution_percentage = 50 if profile == "preview" else 100
    engine_ids = {
        x.identifier for x in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items
    }
    scene.render.engine = next(
        (x for x in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE") if x in engine_ids), "CYCLES"
    )
    if scene.render.engine == "CYCLES":
        scene.cycles.device = "CPU"
        scene.cycles.samples = (
            20 if profile == "preview" else (64 if profile == "standard" else 128)
        )
    else:
        scene.eevee.taa_render_samples = (
            48 if profile == "preview" else (96 if profile == "standard" else 128)
        )
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "AgX - Medium High Contrast"
    world = bpy.data.worlds.new(f"{scene_id} | atmosphere")
    world.use_nodes = True
    world_colours = {
        "opening": (0.008, 0.018, 0.043, 1),
        "hour_1": (0.055, 0.078, 0.105, 1),
        "hour_3": (0.018, 0.045, 0.073, 1),
        "hour_6": (0.075, 0.12, 0.16, 1),
        "hour_12": (0.035, 0.075, 0.13, 1),
        "hour_18": (0.10, 0.19, 0.31, 1),
        "hour_24": (0.025, 0.055, 0.11, 1),
    }
    world.node_tree.nodes["Background"].inputs["Color"].default_value = world_colours.get(
        scene_id, (0.02, 0.035, 0.06, 1)
    )
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.22
    scene.world = world
    lighting = {
        "opening": ((0.55, 0.72, 1.0), (0.18, 0.34, 0.67), (1.0, 0.42, 0.19)),
        "hour_1": ((1.0, 0.77, 0.56), (0.43, 0.68, 0.88), (0.95, 0.42, 0.19)),
        "hour_3": ((0.55, 0.76, 1.0), (0.12, 0.62, 0.73), (0.95, 0.47, 0.20)),
        "hour_6": ((0.74, 0.86, 1.0), (0.34, 0.59, 0.69), (0.88, 0.57, 0.34)),
        "hour_12": ((0.40, 0.60, 0.86), (0.90, 0.53, 0.28), (0.20, 0.48, 0.72)),
        "hour_18": ((1.0, 0.70, 0.37), (0.39, 0.62, 0.83), (0.94, 0.34, 0.13)),
        "hour_24": ((0.40, 0.57, 0.83), (0.91, 0.49, 0.27), (0.18, 0.36, 0.68)),
    }
    key, fill, rim = lighting.get(
        scene_id, ((1.0, 0.77, 0.55), (0.52, 0.72, 1.0), (1.0, 0.48, 0.25))
    )
    area_light("Key | scene-shaped softbox", (-4.5, -5.5, 7.0), (0, 0, 1.2), 720, key, 5.0)
    area_light("Fill | scene bounce", (4.0, -3.5, 4.2), (0, 0, 1.2), 390, fill, 4.5)
    area_light("Rim | atmosphere", (0, 4.0, 6.0), (0, 0, 1.2), 860, rim, 3.0)
    return scene


def actor(style, loc, duration, walk=False, gesture="idle", expression="concern"):
    duration_frames = int(round(duration))
    rig, parts = build_character(style, loc)
    animate_idle(rig, duration_frames=duration_frames, seed=len(rig.name))
    set_expression(rig, expression, 1)
    set_expression(rig, expression, max(1, round(duration_frames * 0.62)))
    if walk:
        animate_walk(rig, duration_frames=duration_frames)
    elif gesture == "reach":
        animate_reach(rig, duration_frames=duration_frames)
    elif gesture == "point":
        animate_point(rig, duration_frames=duration_frames)
    elif gesture == "carry":
        animate_carry(rig, duration_frames=duration_frames)
    if walk:
        rig.location.x -= 0.45
        rig.keyframe_insert(data_path="location", frame=1)
        rig.location.x += 0.45
        rig.keyframe_insert(data_path="location", frame=round(duration_frames * 0.72))
        rig.location.x += 0.04
        rig.keyframe_insert(data_path="location", frame=duration_frames)
    return rig, parts


def scene_opening(scene, duration, fps):
    _earth_space_world(scene)
    globe = orb(
        "Planet Earth",
        (0, 0, 0),
        (1.55, 1.55, 1.55),
        _earth_surface_material(),
        segments=128,
        ring_count=64,
    )
    bpy.context.view_layer.objects.active = globe
    globe.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    globe.select_set(False)
    # The independently mapped cloud shell turns slightly faster than the land.
    clouds = orb(
        "Planetary cloud veil",
        (0, 0, 0),
        (1.566, 1.566, 1.566),
        _earth_cloud_material(),
        segments=128,
        ring_count=64,
    )
    parent_keep(clouds, globe)
    clouds.keyframe_insert(data_path="rotation_euler", frame=1)
    clouds.rotation_euler.z = math.tau * 0.025
    clouds.keyframe_insert(data_path="rotation_euler", frame=round(duration * fps))
    # Fresnel atmosphere only glows near the silhouette; no flat ring artifact.
    atmosphere = bpy.data.materials.new("Atmosphere | grazing blue glow")
    atmosphere.use_nodes = True
    atmosphere_nodes = atmosphere.node_tree.nodes
    atmosphere_nodes.clear()
    transparent = atmosphere_nodes.new("ShaderNodeBsdfTransparent")
    glow = atmosphere_nodes.new("ShaderNodeEmission")
    glow.inputs["Color"].default_value = (0.04, 0.39, 0.82, 1)
    glow.inputs["Strength"].default_value = 1.8
    facing = atmosphere_nodes.new("ShaderNodeLayerWeight")
    ramp = atmosphere_nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.52
    ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    ramp.color_ramp.elements[1].position = 0.92
    ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    mix = atmosphere_nodes.new("ShaderNodeMixShader")
    output = atmosphere_nodes.new("ShaderNodeOutputMaterial")
    links = atmosphere.node_tree.links
    links.new(facing.outputs["Facing"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], mix.inputs[0])
    links.new(transparent.outputs[0], mix.inputs[1])
    links.new(glow.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], output.inputs["Surface"])
    atmosphere.surface_render_method = "DITHERED"
    shell = orb("Atmosphere | spherical glow", (0, 0, 0), (1.585, 1.585, 1.585), atmosphere, 64)
    parent_keep(shell, globe)
    animate(
        globe,
        "rotation_euler",
        [(1, (0, 0, 0)), (round(duration * fps), (0.04, 0, math.tau * 0.12))],
    )
    sun = emission("Distant sun", (1.0, 0.43, 0.17), 1.5)
    orb("Sun on the horizon", (-4, 4, 3.8), (0.82, 0.82, 0.82), sun)
    cam = add_camera(scene, (0, -8.8, 0.4), (0, 0, 0), (0, -5.15, 0.2), 32)
    camera_text(cam, "What if the world\nran out of water?", "Usable freshwater—not Earth's oceans")


def scene_hour_1(scene, duration, fps):
    create_kitchen()
    rig, _ = actor(
        "adult_neutral", (-1.2, -0.15, 0.03), duration * fps, gesture="reach", expression="concern"
    )
    cam = add_camera(scene, (1.35, -5.5, 2.12), (-0.78, 0.32, 1.42), (1.15, -4.95, 1.98), 68)
    cam.data.dof.use_dof = True
    cam.data.dof.focus_distance = 5.5
    cam.data.dof.aperture_fstop = 9.0
    camera_text(cam, "Hour 1 | taps stop", "Water no longer reaches the kitchen")


def scene_hour_3(scene, duration, fps):
    wall = mat("Market | midnight blue", (0.035, 0.085, 0.13))
    floor = mat("Market | polished slate", (0.12, 0.16, 0.18), roughness=0.3)
    shelf = mat("Retail shelving | graphite", (0.18, 0.22, 0.24), metallic=0.2)
    label = mat("Bottle label | turquoise", (0.06, 0.47, 0.60), roughness=0.4)
    bottle = mat("Bottle | PET blue", (0.20, 0.56, 0.72), roughness=0.18)
    cap = mat("Bottle cap", (0.93, 0.67, 0.24), roughness=0.4)
    box("Market floor", (0, 1, -0.15), (10, 14, 0.3), floor)
    box("Back wall", (0, 3.2, 2.7), (9, 0.25, 5.4), wall)
    for row, z in enumerate((0.75, 1.55, 2.35)):
        box("Shelf frame", (0, 1.65, z), (6.6, 0.48, 0.12), shelf, 0.02)
        for x in (-3.15, -1.6, 0, 1.6, 3.15):
            box("Shelf upright", (x, 1.72, z + 0.34), (0.075, 0.36, 0.68), shelf, 0.018)
        for column in range(19):
            x = -3.0 + column * 0.33
            body = cylinder(
                "Water bottle | PET", (x, 1.35, z + 0.25), 0.085, 0.46, bottle, vertices=20
            )
            label_obj = box("Bottle label", (x, 1.255, z + 0.24), (0.12, 0.012, 0.10), label, 0.01)
            cap_obj = cylinder("Bottle cap", (x, 1.35, z + 0.50), 0.042, 0.045, cap, vertices=16)
            # Bottles disappear progressively as shoppers clear the display.
            hide_at = round((3 + (column / 18) * 6) * fps)
            for bottle_part in (body, label_obj, cap_obj):
                bottle_part.keyframe_insert(data_path="hide_render", frame=1)
                bottle_part.hide_render = True
                bottle_part.keyframe_insert(data_path="hide_render", frame=hide_at)
    for x in (-3.2, -1.6, 0, 1.6, 3.2):
        for z in (0.4, 1.2, 2.0):
            box("Shelf support", (x, 1.72, z), (0.065, 0.28, 0.1), shelf, 0.014)
    actor("adult_neutral", (-0.20, -0.2, 0), duration * fps, walk=True, expression="alarm")
    actor("adult_alt", (0.70, 0.1, 0), duration * fps, walk=True, expression="concern")
    # The shopping trolley gives the foreground a strong directional line.
    trolley = box("Shopping trolley basket", (-0.2, -0.95, 0.65), (0.75, 0.58, 0.48), shelf, 0.06)
    handle = box("Trolley handle", (-0.2, -1.24, 0.92), (0.72, 0.055, 0.055), cap, 0.025)
    wheels = [
        cylinder("Trolley wheel", (x, y, 0.13), 0.08, 0.055, shelf, (math.pi / 2, 0, 0))
        for x in (-0.50, 0.10)
        for y in (-1.15, -0.72)
    ]
    for obj in [trolley, handle, *wheels]:
        start = obj.location.copy()
        obj.location.x -= 0.8
        obj.keyframe_insert(data_path="location", frame=1)
        obj.location.x = start.x
        obj.keyframe_insert(data_path="location", frame=round(duration * fps))
    cam = add_camera(scene, (0, -7.2, 2.0), (0, 1.0, 1.5), (-0.3, -6.6, 1.65), 70)
    camera_text(cam, "Hour 3 | panic buying", "Bottled water disappears from shelves")


def scene_hour_6(scene, duration, fps):
    floor = mat("Hospital | warm terrazzo", (0.48, 0.51, 0.48), roughness=0.32)
    wall = mat("Hospital | pale sage", (0.60, 0.71, 0.65))
    teal = mat("Hospital | deep teal", (0.045, 0.29, 0.31))
    white = mat("Hospital | enamel", (0.88, 0.89, 0.82), roughness=0.27)
    red = mat("Emergency vermilion", (0.77, 0.12, 0.10))
    blue = mat("Oxygen blue", (0.18, 0.56, 0.68), roughness=0.35)
    box("Hospital floor", (0, 1, -0.14), (9, 12, 0.28), floor)
    box("Hospital back wall", (0, 3, 2.6), (9, 0.2, 5.2), wall)
    for x in (-3.3, -1.3, 0.7, 2.7):
        box("Tall clinic window", (x, 2.84, 2.5), (1.5, 0.08, 2.5), blue, 0.04)
        box("Window frame", (x, 2.78, 2.5), (0.055, 0.06, 2.5), white, 0.01)
    # Bed, linen, rails and clinical details.
    box("Bed frame", (0.75, 0.25, 0.54), (2.85, 1.25, 0.22), teal, 0.11)
    box("Bed mattress", (0.75, 0.13, 0.77), (2.8, 1.22, 0.31), white, 0.13)
    box("Folded blanket", (1.25, 0.05, 0.97), (1.55, 1.05, 0.14), blue, 0.08)
    box("Pillow", (-0.43, 0.1, 0.99), (0.55, 0.78, 0.18), white, 0.09)
    for x in (-0.6, 2.05):
        cylinder("Bed leg", (x, 0.25, 0.27), 0.06, 0.54, teal)
        box("Bed rail", (x, -0.47, 1.08), (0.07, 0.08, 0.58), white, 0.035)
    for x in (-0.2, 1.7):
        bpy.ops.mesh.primitive_torus_add(
            major_radius=0.075,
            minor_radius=0.018,
            location=(x, -0.49, 1.2),
            rotation=(math.pi / 2, 0, 0),
        )
        bpy.context.object.name = "Bed rail grip"
        bpy.context.object.data.materials.append(teal)
    # Monitor with animated trace and simple ECG line geometry.
    box("Patient monitor", (-1.65, 0.25, 1.75), (0.82, 0.38, 0.72), teal, 0.08)
    screen = mat("Monitor glass", (0.012, 0.065, 0.075), roughness=0.18)
    box("Monitor screen", (-1.65, 0.035, 1.78), (0.68, 0.035, 0.52), screen, 0.025)
    trace = emission("ECG | mint phosphor", (0.25, 0.94, 0.68), 1.5)
    points = [
        (-1.94, -0.005, 1.75),
        (-1.83, -0.005, 1.75),
        (-1.78, -0.005, 1.84),
        (-1.72, -0.005, 1.61),
        (-1.66, -0.005, 1.98),
        (-1.60, -0.005, 1.75),
        (-1.38, -0.005, 1.75),
    ]
    for a, b in zip(points, points[1:]):
        curve = bpy.data.curves.new("ECG luminous trace", "CURVE")
        curve.dimensions = "3D"
        curve.bevel_depth = 0.012
        curve.bevel_resolution = 3
        spline = curve.splines.new("POLY")
        spline.points.add(1)
        spline.points[0].co = (*a, 1)
        spline.points[1].co = (*b, 1)
        obj = bpy.data.objects.new("ECG trace segment", curve)
        bpy.context.collection.objects.link(obj)
        obj.data.materials.append(trace)
    # Red-cross wall medallion and empty emergency-water carafe.
    box("Wall medallion", (2.75, 2.75, 3.5), (0.62, 0.12, 0.62), white, 0.12)
    box("Medical cross vertical", (2.75, 2.65, 3.5), (0.14, 0.035, 0.44), red, 0.025)
    box("Medical cross horizontal", (2.75, 2.64, 3.5), (0.44, 0.035, 0.14), red, 0.025)
    glass = mat("Empty sterile jug", (0.64, 0.82, 0.80), roughness=0.12, metallic=0.12)
    cylinder("Empty water carafe", (-0.1, -0.4, 1.0), 0.18, 0.52, glass, vertices=40)
    cylinder("Carafe neck", (-0.1, -0.4, 1.29), 0.075, 0.11, glass, vertices=32)
    box("Water-supply alert panel", (-2.2, -0.15, 2.8), (1.5, 0.08, 0.48), red, 0.06)
    alert = emission("Alert lettering", (1, 0.91, 0.72), 1.2)
    alert_curve = bpy.data.curves.new("Supply alert lettering", "FONT")
    alert_curve.body = "SUPPLY LOW"
    alert_curve.size = 0.13
    alert_text = bpy.data.objects.new("Supply alert lettering", alert_curve)
    bpy.context.collection.objects.link(alert_text)
    alert_text.location = (-2.79, -0.202, 2.77)
    alert_text.rotation_euler[0] = math.pi / 2
    alert_text.data.materials.append(alert)
    # Camera-facing message is carried by typography, while the wall panel remains a visual cue.
    nurse, _ = actor(
        "nurse", (-0.35, -0.45, 0), duration * fps, gesture="carry", expression="alarm"
    )
    pose_head(nurse, turn=-0.12, frame=round(duration * fps * 0.65))
    bpy.ops.object.light_add(type="POINT", location=(-2.2, -0.23, 2.8))
    bpy.context.object.name = "Supply alert | pulse"
    bpy.context.object.data.color = (1, 0.12, 0.06)
    bpy.context.object.data.energy = 0
    for f, power in (
        (1, 0),
        (fps * 3, 48),
        (fps * 3 + 8, 0),
        (fps * 5, 48),
        (fps * 5 + 8, 0),
        (duration * fps, 0),
    ):
        bpy.context.object.data.energy = power
        bpy.context.object.data.keyframe_insert(data_path="energy", frame=f)
    cam = add_camera(scene, (0, -7.2, 2.3), (0, 0.4, 1.65), (-0.25, -6.75, 1.65), 72)
    camera_text(cam, "Hour 6 | hospitals strained", "Hygiene and essential care depend on water")


def scene_hour_12(scene, duration, fps):
    night = mat("City | blue dusk", (0.10, 0.17, 0.24))
    asphalt = mat("City | wet asphalt", (0.055, 0.09, 0.12), roughness=0.28)
    concrete = mat("City | concrete", (0.30, 0.36, 0.39))
    glass = mat("City | blue glass", (0.08, 0.24, 0.34), metallic=0.25, roughness=0.22)
    amber = emission("Windows | warm occupied", (1.0, 0.49, 0.19), 1.0)
    box("City road", (0, 1, -0.18), (20, 18, 0.36), asphalt, 0.025)
    box("Horizon wall", (0, 5, 4), (30, 0.3, 9), night)
    rng = random.Random(12)
    for i, x in enumerate((-8, -6.2, -4.4, -2.4, -0.5, 1.3, 3.2, 5.2, 7.1)):
        width = rng.uniform(1.25, 1.9)
        height = rng.uniform(3.2, 7.0)
        depth = rng.uniform(0.55, 1.0)
        box(f"Civic tower {i}", (x, 3.3, height / 2), (width, depth, height), concrete, 0.09)
        box(
            "Facade glass panel",
            (x, 2.78, height * 0.56),
            (width * 0.82, 0.025, height * 0.58),
            glass,
            0.025,
        )
        for row in range(max(2, int(height / 0.55))):
            for col in range(2, 5):
                wx = x - width * 0.34 + (col - 2) * width * 0.30
                z = 0.8 + row * 0.52
                if z < height - 0.25 and (row + col + i) % 4 == 0:
                    box("Lit city window", (wx, 2.75, z), (0.15, 0.018, 0.20), amber, 0.012)
    # Water-treatment plant tanks and the pressure-main pipe ending at a sealed valve.
    facility = mat("Treatment plant | desaturated teal", (0.16, 0.34, 0.37), metallic=0.18)
    for x, radius, height in ((-2.8, 0.76, 1.2), (-1.0, 0.62, 1.65), (1.0, 0.88, 1.35)):
        cylinder("Treatment clarifier", (x, 0.8, height / 2), radius, height, facility, vertices=48)
        bpy.ops.mesh.primitive_torus_add(
            major_radius=radius * 0.94, minor_radius=0.035, location=(x, 0.8, height)
        )
        bpy.context.object.name = "Clarifier rim"
        bpy.context.object.data.materials.append(concrete)
    cylinder(
        "Water main | horizontal",
        (-0.3, -0.2, 0.82),
        0.10,
        4.8,
        mat("Water main steel", (0.25, 0.40, 0.43), metallic=0.72),
        (0, math.pi / 2, 0),
        40,
    )
    for x in (-2.45, -0.8, 0.7, 2.0):
        cylinder(
            "Main pipe coupling", (x, -0.2, 0.82), 0.14, 0.10, concrete, (0, math.pi / 2, 0), 28
        )
    valve = cylinder(
        "Isolation valve",
        (2.2, -0.2, 1.12),
        0.23,
        0.075,
        mat("Valve red", (0.70, 0.15, 0.10), metallic=0.2),
        (math.pi / 2, 0, 0),
        32,
    )
    animate(
        valve,
        "rotation_euler",
        [
            (1, (math.pi / 2, 0, 0)),
            (fps * 3, (math.pi / 2, 0, 0)),
            (fps * 5, (math.pi / 2, 0, 1.35)),
            (duration * fps, (math.pi / 2, 0, 1.35)),
        ],
    )
    # A short steam plume drifts from one industrial stack.
    smoke = mat("Stack vapour", (0.70, 0.77, 0.78), roughness=0.95)
    for i in range(9):
        puff = orb(
            "Factory steam",
            (3.2 + (i % 3) * 0.14, 2.6, 1.8 + i * 0.32),
            (0.24 + i * 0.018, 0.22, 0.22),
            smoke,
        )
        puff.keyframe_insert(data_path="location", frame=1)
        puff.location.x += 0.22
        puff.keyframe_insert(data_path="location", frame=duration * fps)
    # Headlights and a small traffic flow cut across the foreground.
    carmat = mat("Taxi | muted ochre", (0.70, 0.37, 0.12), roughness=0.3)
    for i, y in enumerate((-2.1, -3.1)):
        car = box("Taxi body", (-3.5, y, 0.42), (1.25, 0.68, 0.42), carmat, 0.11)
        roof = box("Taxi roof", (-3.5, y, 0.70), (0.58, 0.52, 0.24), glass, 0.05)
        for wheel_x in (-3.9, -3.1):
            cylinder(
                "Taxi wheel",
                (wheel_x, y - 0.34, 0.19),
                0.16,
                0.08,
                asphalt,
                (math.pi / 2, 0, 0),
                24,
            )
        for obj in (car, roof):
            obj.location.x = -4.0 - i * 0.5
            obj.keyframe_insert(data_path="location", frame=1)
            obj.location.x = 4.0 + i * 0.5
            obj.keyframe_insert(data_path="location", frame=duration * fps)
    actor("adult_alt", (-0.25, -2.0, 0), duration * fps, walk=True, expression="concern")
    actor("shop_assistant", (0.55, -2.3, 0), duration * fps, walk=True, expression="alarm")
    cam = add_camera(scene, (0, -8.2, 3.5), (0, 1.0, 2.1), (0.6, -7.4, 2.55), 58)
    camera_text(cam, "Hour 12 | cities struggle", "Industry and essential services slow")


def scene_hour_18(scene, duration, fps):
    soil = mat("Field | dry loam", (0.30, 0.20, 0.11), roughness=0.95)
    ridge = mat("Field | sun-baked furrows", (0.43, 0.29, 0.15), roughness=0.98)
    leaf = mat("Crops | stressed green", (0.34, 0.40, 0.15), roughness=0.86)
    dry = mat("Crops | drying tips", (0.67, 0.47, 0.16), roughness=0.8)
    sky = mat("Sky | blue to amber horizon", (0.20, 0.36, 0.52), roughness=0.9)
    sky_nodes = sky.node_tree.nodes
    sky_links = sky.node_tree.links
    sky_shader = sky_nodes.get("Principled BSDF")
    generated = sky_nodes.new("ShaderNodeTexCoord")
    separate = sky_nodes.new("ShaderNodeSeparateXYZ")
    gradient = sky_nodes.new("ShaderNodeValToRGB")
    gradient.color_ramp.elements[0].position = 0.0
    gradient.color_ramp.elements[0].color = (0.70, 0.31, 0.14, 1)
    gradient.color_ramp.elements[1].position = 0.83
    gradient.color_ramp.elements[1].color = (0.13, 0.30, 0.48, 1)
    sky_links.new(generated.outputs["Generated"], separate.inputs["Vector"])
    sky_links.new(separate.outputs["Z"], gradient.inputs["Fac"])
    if sky_shader:
        sky_links.new(gradient.outputs["Color"], sky_shader.inputs["Base Color"])
    box("Farm earth", (0, 1, -0.16), (16, 17, 0.32), soil, 0.03)
    box("Far horizon", (0, 7, 3.0), (20, 0.3, 6), sky)
    # Parallel furrows recede into the field to make the drought legible at a glance.
    for x in (-5.3, -4.3, -3.3, -2.3, -1.3, -0.3, 0.7, 1.7, 2.7, 3.7, 4.7):
        furrow = box("Raised dry crop row", (x, 1.5, 0.04), (0.48, 9.0, 0.12), ridge, 0.11)
        furrow.rotation_euler[0] = math.radians(2)
    crop_objs = []
    for row, x in enumerate((-4.3, -2.3, -0.3, 1.7, 3.7)):
        for j, y in enumerate((-2.0, -0.4, 1.2, 2.8, 4.2)):
            stem = cylinder("Corn stalk", (x, y, 0.55), 0.035, 1.0, leaf, vertices=12)
            crop_objs.append(stem)
            for side in (-1, 1):
                blade = orb(
                    "Wilting corn leaf",
                    (x + side * 0.18, y, 0.45 + j * 0.012),
                    (0.26, 0.055, 0.045),
                    leaf,
                    20,
                )
                blade.rotation_euler[1] = side * 0.58
                crop_objs.append(blade)
            tassel = orb("Dry tassel", (x, y, 1.1), (0.085, 0.07, 0.22), dry, 16)
            crop_objs.append(tassel)
    # Leaves droop over the scene, a subtle time-based environmental beat.
    for obj in crop_objs:
        original = obj.rotation_euler.copy()
        obj.rotation_euler = original
        obj.keyframe_insert(data_path="rotation_euler", frame=1)
        obj.rotation_euler[1] += 0.13
        obj.keyframe_insert(data_path="rotation_euler", frame=duration * fps)
    farmer, _ = actor(
        "farmer", (0.60, -1.5, 0), duration * fps, gesture="point", expression="concern"
    )
    pose_head(farmer, turn=0.15, frame=round(duration * fps * 0.55))
    sunmat = emission("Late sun | amber", (1.0, 0.40, 0.11), 1.5)
    orb("Bleached afternoon sun", (3.5, 4.5, 5.5), (0.70, 0.70, 0.70), sunmat)
    for i in range(20):
        dust = orb(
            "Dry field dust",
            (
                random.Random(i).uniform(-5, 5),
                random.Random(i + 2).uniform(-1, 4),
                random.Random(i + 4).uniform(0.2, 2.2),
            ),
            (0.018, 0.018, 0.018),
            dry,
            8,
        )
        dust.keyframe_insert(data_path="location", frame=1)
        dust.location.x += 0.4
        dust.location.z += 0.2
        dust.keyframe_insert(data_path="location", frame=duration * fps)
    cam = add_camera(scene, (2.8, -7.5, 2.5), (0, 1.1, 1.15), (1.6, -6.7, 2.1), 60)
    camera_text(cam, "Hour 18 | harvest at risk", "Dry fields put food production under pressure")


def scene_hour_24(scene, duration, fps):
    dusk = mat("Finale | blue-hour skyline", (0.13, 0.24, 0.34))
    ground = mat("Finale | civic plaza", (0.11, 0.15, 0.18), roughness=0.3)
    stone = mat("Finale | sandstone", (0.47, 0.39, 0.29))
    window = mat("Finale | city lights", (0.98, 0.51, 0.22), emission=0.1)
    box("Civic plaza", (0, 1, -0.18), (22, 17, 0.36), ground)
    box("Distant skyline", (0, 8, 3.2), (24, 0.4, 6.4), dusk)
    for i, x in enumerate((-9, -7, -5, -3, 0, 2.2, 4.5, 6.6, 8.5)):
        height = 3.0 + (i * 37 % 5) * 0.58
        width = 1.35 + (i % 3) * 0.2
        box("Distant apartment block", (x, 7.3, height / 2), (width, 0.7, height), stone, 0.08)
        for row in range(2, int(height / 0.52)):
            for col in (-0.35, 0.0, 0.35):
                if (row + i + int(col * 10)) % 3 == 0:
                    box(
                        "Apartment window",
                        (x + col, 6.92, row * 0.52),
                        (0.11, 0.02, 0.16),
                        window,
                        0.008,
                    )
    # People cluster around an emergency collection point, with meaningful spacing and scale.
    positions = [(-1.35, -0.2), (-0.68, 0.3), (-0.04, -0.4), (0.64, 0.2), (1.32, -0.15)]
    styles = ("adult_neutral", "adult_alt", "nurse", "shop_assistant", "farmer")
    emotions = ("concern", "alarm", "concern", "concern", "alarm")
    for i, (x, y) in enumerate(positions):
        gesture = "carry" if i == 1 else "idle"
        rig, _ = actor(
            styles[i], (x, y, 0), duration * fps, gesture=gesture, expression=emotions[i]
        )
        pose_head(
            rig,
            turn=-0.07 if i % 2 else 0.07,
            frame=round(duration * fps * 0.7),
        )
    # Reusable empty containers in the foreground reinforce the premise without text walls.
    vessel = mat("Empty emergency jerrycan | pale blue", (0.38, 0.62, 0.68), roughness=0.28)
    for i, x in enumerate((-1.35, -0.7, 0.0, 0.7, 1.35)):
        box("Empty water container", (x, -1.8, 0.35), (0.42, 0.30, 0.62), vessel, 0.08)
        box("Jerrycan neck", (x + 0.11, -1.8, 0.69), (0.14, 0.16, 0.13), vessel, 0.035)
        bpy.ops.mesh.primitive_torus_add(
            major_radius=0.24, minor_radius=0.026, location=(x, -1.8, 0.72)
        )
        bpy.context.object.name = "Jerrycan handle"
        bpy.context.object.data.materials.append(vessel)
    sun = emission("Horizon | last warm light", (1, 0.38, 0.14), 1.0)
    orb("Horizon glow", (0, 7, 3.8), (1.0, 0.12, 0.58), sun)
    cam = add_camera(scene, (0, -8.5, 2.9), (0, 1, 1.35), (0, -10.5, 3.1), 55)
    camera_text(cam, "Water is life.", "24 hours. Everything depends on it.")


BUILDERS = {
    "opening": scene_opening,
    "hour_1": scene_hour_1,
    "hour_3": scene_hour_3,
    "hour_6": scene_hour_6,
    "hour_12": scene_hour_12,
    "hour_18": scene_hour_18,
    "hour_24": scene_hour_24,
}


def build_story_scene(scene_id, duration, fps, profile, output):
    scene = setup(scene_id, duration, fps, profile)
    builder = BUILDERS.get(scene_id)
    if builder is None:
        raise ValueError(f"Unknown production scene: {scene_id}")
    builder(scene, duration, fps)
    scene.render.filepath = str(output / "frames" / "frame_0001.png")
    scene.frame_set(1)
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output / f"{scene_id}.blend"))
