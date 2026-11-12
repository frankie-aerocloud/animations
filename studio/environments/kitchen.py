"""Stylised, camera-ready residential kitchen for the 10-second QC sequence."""

from __future__ import annotations
import bpy


def material(name, color, metallic=0.0, roughness=0.6):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*color, 1)
    p.inputs["Metallic"].default_value = metallic
    p.inputs["Roughness"].default_value = roughness
    return m


def box(name, loc, scale, mat, bevel=0.03):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if mat:
        o.data.materials.append(mat)
    if bevel:
        b = o.modifiers.new("Soft manufactured edges", "BEVEL")
        b.width, b.segments = bevel, 3
        o.modifiers.new("Weighted corner normals", "WEIGHTED_NORMAL")
    return o


def _cylinder(name, loc, radius, depth, mat, direction=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=radius, depth=depth, location=loc)
    o = bpy.context.object
    o.name = name
    o.data.materials.append(mat)
    if direction:
        o.rotation_euler = direction
    for p in o.data.polygons:
        p.use_smooth = True
    return o


def create_kitchen():
    oak = material("Honey oak", (0.38, 0.19, 0.085), roughness=0.36)
    pale = material("Warm ivory cabinetry", (0.78, 0.72, 0.59))
    tile = material("Sage ceramic tile", (0.23, 0.40, 0.38), roughness=0.32)
    wall = material("Plaster | warm limestone", (0.65, 0.56, 0.44))
    steel = material("Brushed chrome", (0.42, 0.52, 0.56), metallic=0.82, roughness=0.23)
    black = material("Tap shadow", (0.025, 0.045, 0.05), metallic=0.25)
    glass = material("Glass | clear", (0.7, 0.9, 0.93), metallic=0.18, roughness=0.1)
    floor = material("Terrazzo floor", (0.28, 0.29, 0.27))
    green = material("Window garden", (0.17, 0.31, 0.20))
    box("Floor", (0, 0, -0.12), (7.5, 7.0, 0.24), floor, 0.02)
    box("Back wall", (0, 2.1, 2.0), (7.5, 0.22, 4.25), wall)
    # Counter run, drawer fronts and timber worktop.
    box("Base cabinetry", (0, 1.02, 0.49), (5.9, 1.5, 0.98), pale, 0.07)
    box("Oak worktop", (0, 0.93, 1.03), (6.1, 1.65, 0.16), oak, 0.055)
    for x in (-2.2, -1.1, 0, 1.1, 2.2):
        box("Drawer front", (x, 0.24, 0.52), (0.99, 0.045, 0.73), pale, 0.025)
        box("Drawer pull", (x, 0.19, 0.60), (0.36, 0.06, 0.045), steel, 0.018)
    # Large glazed window gives the kitchen layered daylight and depth.
    window = material("Window glass | morning", (0.14, 0.34, 0.43), metallic=0.12, roughness=0.25)
    box("Window recess", (1.85, 1.95, 2.7), (2.35, 0.14, 1.75), black, 0.025)
    box("Window pane", (1.85, 1.86, 2.7), (2.16, 0.035, 1.57), window, 0.01)
    box("Window sill", (1.85, 1.66, 1.79), (2.55, 0.38, 0.11), oak, 0.035)
    box("Window mullion", (1.85, 1.82, 2.7), (0.055, 0.07, 1.62), pale, 0.012)
    box("Window rail", (1.85, 1.82, 2.7), (2.25, 0.07, 0.055), pale, 0.012)
    # Tile backsplash, individually beveled tiles in a quiet grid.
    for row in range(3):
        for col in range(13):
            x = -2.9 + col * 0.48
            box(
                "Handmade backsplash tile",
                (x, 1.93, 1.32 + row * 0.32),
                (0.45, 0.035, 0.29),
                tile,
                0.025,
            )
    # Sink basin and recognisable high-neck chrome mixer.
    box("Sink lip", (-0.88, 0.78, 1.12), (1.08, 0.88, 0.055), steel, 0.075)
    box("Sink dark basin", (-0.88, 0.78, 1.145), (0.83, 0.62, 0.035), black, 0.12)
    _cylinder("Mixer base", (-0.88, 1.02, 1.18), 0.10, 0.09, steel)
    bpy.ops.mesh.primitive_torus_add(
        major_radius=0.33,
        minor_radius=0.045,
        major_segments=48,
        minor_segments=12,
        location=(-0.88, 1.04, 1.49),
    )
    arch = bpy.context.object
    arch.name = "Curved chrome mixer"
    arch.data.materials.append(steel)
    arch.scale = (1, 0.58, 1)
    _cylinder("Mixer spout", (-0.88, 0.86, 1.40), 0.045, 0.29, steel, (1.57, 0, 0))
    box("Mixer lever", (-0.62, 1.00, 1.25), (0.07, 0.29, 0.06), steel, 0.025)
    # Empty tumbler has thick rim and foot; a moving bead sells the failed flow beat.
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=48, radius=0.14, depth=0.39, location=(-0.05, 0.68, 1.315)
    )
    tumbler = bpy.context.object
    tumbler.name = "Empty drinking glass"
    tumbler.data.materials.append(glass)
    tumbler.modifiers.new("Glass wall", "SOLIDIFY").thickness = 0.012
    bevel = tumbler.modifiers.new("Glass edge", "BEVEL")
    bevel.width = 0.012
    bevel.segments = 3
    bpy.ops.mesh.primitive_torus_add(
        major_radius=0.14, minor_radius=0.014, location=(-0.05, 0.68, 1.51)
    )
    bpy.context.object.name = "Glass rim"
    bpy.context.object.data.materials.append(glass)
    drop_mat = material("Last water bead", (0.13, 0.53, 0.78), metallic=0.1, roughness=0.12)
    bpy.ops.mesh.primitive_uv_sphere_add(
        segments=24, ring_count=16, radius=0.045, location=(-0.88, 0.86, 1.29)
    )
    drop = bpy.context.object
    drop.name = "Last falling droplet"
    drop.data.materials.append(drop_mat)
    for f, z in ((1, 1.50), (49, 1.45), (52, 1.15), (58, 1.16), (68, 1.16)):
        drop.location.z = z
        drop.keyframe_insert(data_path="location", frame=f)
    # Upper cabinets with inset faces, handles and under-cabinet glow.
    for x in (-1.95, -0.72, 0.51):
        box("Upper oak cabinet", (x, 1.77, 2.26), (1.12, 0.58, 1.04), oak, 0.055)
        box("Ivory inset panel", (x, 1.46, 2.26), (0.98, 0.055, 0.88), pale, 0.035)
        box("Cabinet pull", (x + 0.36, 1.41, 2.22), (0.045, 0.04, 0.19), steel, 0.018)
    # Potted herb, carefully framed details.
    terracotta = material("Terracotta", (0.46, 0.20, 0.12))
    _cylinder("Herb pot", (2.75, 0.56, 1.25), 0.18, 0.26, terracotta)
    for i in range(5):
        leaf = box(
            "Basil leaf",
            (2.75 + (i - 2) * 0.07, 0.56, 1.49 + (i % 2) * 0.09),
            (0.045, 0.07, 0.27),
            green,
            0.025,
        )
        leaf.rotation_euler[1] = (i - 2) * 0.3
    # Ceiling valance and architectural shadows.
    box("Ceiling edge", (0, 1.2, 4.15), (7.5, 2.2, 0.18), pale, 0.025)
    return {"drop": drop, "glass": tumbler}
