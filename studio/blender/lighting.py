"""Lighting presets: sun, gradient sky, optional volumetric haze (fog box) and colour management."""

from __future__ import annotations

import math

import bpy

from studio.blender.primitives import box

PRESETS = {
    "soft_daylight": dict(sun=5.0, angle=2.0, elevation=48, azimuth=-35, colour=(1.0, 0.95, 0.88), zenith=(0.20, 0.42, 0.84), horizon=(0.60, 0.72, 0.88), ambient=0.55, fog=0.0010, fog_colour=(0.78, 0.85, 0.94), exposure=-0.25),
    "golden_hour": dict(sun=4.0, angle=2.0, elevation=14, azimuth=-110, colour=(1.0, 0.68, 0.40), zenith=(0.22, 0.34, 0.66), horizon=(0.94, 0.66, 0.42), ambient=0.45, fog=0.0016, fog_colour=(0.92, 0.80, 0.66), exposure=-0.1),
    "overcast": dict(sun=2.6, angle=10.0, elevation=58, azimuth=-20, colour=(0.92, 0.94, 1.0), zenith=(0.46, 0.52, 0.60), horizon=(0.74, 0.76, 0.78), ambient=0.8, fog=0.0018, fog_colour=(0.82, 0.84, 0.86), exposure=-0.25),
    "harsh_noon": dict(sun=6.5, angle=1.0, elevation=74, azimuth=10, colour=(1.0, 0.98, 0.94), zenith=(0.20, 0.44, 0.86), horizon=(0.80, 0.82, 0.80), ambient=0.5, fog=0.0007, fog_colour=(0.92, 0.90, 0.84), exposure=-0.35),
    "dusk_urgent": dict(sun=2.4, angle=2.5, elevation=7, azimuth=-125, colour=(1.0, 0.42, 0.22), zenith=(0.06, 0.10, 0.28), horizon=(0.86, 0.38, 0.22), ambient=0.4, fog=0.0017, fog_colour=(0.64, 0.48, 0.44), exposure=0.0),
    "night_emergency": dict(sun=0.4, angle=4.0, elevation=35, azimuth=60, colour=(0.55, 0.65, 1.0), zenith=(0.02, 0.03, 0.08), horizon=(0.10, 0.08, 0.14), ambient=0.35, fog=0.0015, fog_colour=(0.16, 0.14, 0.22), exposure=0.4),
    "interior_day": dict(sun=3.0, angle=5.0, elevation=38, azimuth=-55, colour=(1.0, 0.94, 0.84), zenith=(0.55, 0.65, 0.82), horizon=(0.80, 0.78, 0.72), ambient=0.75, fog=0.0, fog_colour=(0.9, 0.9, 0.9), exposure=-0.35),
}


def apply(ctx, name="soft_daylight", overrides=None, fog_extent=(700, 700, 160), fog_centre=(0, 0)):
    preset = dict(PRESETS[name])
    preset.update(overrides or {})
    scene = ctx.scene
    sun_data = bpy.data.lights.new("Sun", "SUN")
    sun_data.energy = float(preset["sun"])
    sun_data.angle = math.radians(float(preset["angle"]))
    sun_data.color = tuple(preset["colour"])
    sun = bpy.data.objects.new("Sun", sun_data)
    ctx.link(sun)
    sun.rotation_euler = (math.radians(90.0 - float(preset["elevation"])), 0.0, math.radians(float(preset["azimuth"])))
    ctx.objects["sun"] = sun
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    scene.world = world
    nodes, links = world.node_tree.nodes, world.node_tree.links
    coords = nodes.new("ShaderNodeTexCoord")
    separate = nodes.new("ShaderNodeSeparateXYZ")
    map_range = nodes.new("ShaderNodeMapRange")
    ramp = nodes.new("ShaderNodeValToRGB")
    map_range.inputs["From Min"].default_value = -0.02
    map_range.inputs["From Max"].default_value = 0.32
    links.new(coords.outputs["Generated"], separate.inputs[0])
    links.new(separate.outputs["Z"], map_range.inputs["Value"])
    links.new(map_range.outputs[0], ramp.inputs[0])
    ramp.color_ramp.elements[0].color = (*preset["horizon"], 1.0)
    ramp.color_ramp.elements[1].color = (*preset["zenith"], 1.0)
    background = nodes["Background"]
    links.new(ramp.outputs[0], background.inputs["Color"])
    background.inputs["Strength"].default_value = float(preset["ambient"])
    ctx.world_strength = background.inputs["Strength"]
    if ctx.profile.volumetrics and float(preset["fog"]) > 0.0:
        _fog_box(ctx, float(preset["fog"]), preset["fog_colour"], fog_extent, fog_centre)
    view = scene.view_settings
    view.view_transform = "AgX"
    try:
        view.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    view.exposure = float(preset["exposure"])
    return sun


def _fog_box(ctx, density, colour, extent, centre):
    """Eevee world volumes render black in Blender 5.2, so haze is a scatter volume inside a box."""
    material = bpy.data.materials.new("Haze")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    scatter = nodes.new("ShaderNodeVolumeScatter")
    scatter.inputs["Density"].default_value = density
    scatter.inputs["Color"].default_value = (*colour, 1.0)
    scatter.inputs["Anisotropy"].default_value = 0.3
    output = nodes.new("ShaderNodeOutputMaterial")
    material.node_tree.links.new(scatter.outputs[0], output.inputs["Volume"])
    w, d, h = extent
    fog = box(ctx, "Haze", (w, d, h), (centre[0], centre[1], -2.0), material, anchor="base")
    fog.display_type = "WIRE"
    eevee = ctx.scene.eevee
    eevee.volumetric_tile_size = "8"
    eevee.volumetric_samples = 48
    eevee.volumetric_start = 0.5
    eevee.volumetric_end = 2000.0
    return fog


def area_light(ctx, name, loc, power=1500.0, size=6.0, colour=(1.0, 0.97, 0.9), rot=(0, 0, 0)):
    data = bpy.data.lights.new(name, "AREA")
    data.energy = power
    data.size = size
    data.color = colour
    data.shape = "RECTANGLE"
    data.size_y = size * 0.6
    light = bpy.data.objects.new(name, data)
    light.location = loc
    light.rotation_euler = rot
    ctx.link(light)
    ctx.tag("light", light)
    return light
