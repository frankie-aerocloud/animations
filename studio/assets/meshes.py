"""Linear-time mesh building for very large merges (whole districts, heavy rain).

primitives.multi_box adds one bmesh operator call per box, and each call touches the whole mesh, so
a 12,000-box district takes minutes. Building the vertex and face lists directly stays linear."""

from __future__ import annotations

import bpy

FACES = ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7))


def merged_boxes(ctx, name, boxes, mats, loc=(0.0, 0.0, 0.0), rot=(0.0, 0.0, 0.0)):
    """One mesh object from (centre, size, material_index) boxes, like primitives.multi_box."""
    verts, faces, face_mats = [], [], []
    for (cx, cy, cz), (sx, sy, sz), index in boxes:
        hx, hy, hz = sx / 2, sy / 2, sz / 2
        base = len(verts)
        verts += [(cx - hx, cy - hy, cz - hz), (cx + hx, cy - hy, cz - hz), (cx + hx, cy + hy, cz - hz), (cx - hx, cy + hy, cz - hz), (cx - hx, cy - hy, cz + hz), (cx + hx, cy - hy, cz + hz), (cx + hx, cy + hy, cz + hz), (cx - hx, cy + hy, cz + hz)]
        faces += [(base + a, base + b, base + c, base + d) for a, b, c, d in FACES]
        face_mats += [index] * 6
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    for material in mats:
        mesh.materials.append(material)
    mesh.polygons.foreach_set("material_index", face_mats)
    obj = bpy.data.objects.new(name, mesh)
    obj.location = loc
    obj.rotation_euler = rot
    ctx.link(obj)
    return obj
