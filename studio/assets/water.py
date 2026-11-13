"""Water surfaces, pools, fountains, rivers and tanks. Every water body is tagged 'water'."""

from __future__ import annotations

import math

from studio.blender.primitives import box, cone, cylinder, grid, mesh_from_pydata, multi_box, parent

KINDS = {"sea": ("sea", 0.18, 9.0), "lake": ("lake", 0.08, 7.0), "pool": ("pool", 0.0, 1.0), "river": ("river", 0.05, 3.0)}


def surface(ctx, name, size, loc, kind="sea", divisions=None, tags=("water",), bed=False):
    """Water grid with gentle waves. bed=True adds a dry-bed slab just below (revealed when the level drops)."""
    colour, wave_height, wave_width = KINDS[kind]
    if bed:
        box(ctx, f"{name}.bed", (size[0], size[1], 0.4), (loc[0], loc[1], loc[2] - 1.2), ctx.mat("dry_bed", roughness=0.95), anchor="base")
    divisions = divisions or (max(4, int(size[0] / 10)), max(4, int(size[1] / 10)))
    obj = grid(ctx, name, size, divisions, ctx.palette.water(f"{name} water", colour), loc)
    if wave_height > 0:
        wave = obj.modifiers.new("Wave", "WAVE")
        wave.height = wave_height
        wave.width = wave_width
        wave.narrowness = 1.4
        wave.speed = 0.25
        wave.use_x = True
        wave.use_y = True
        wave.start_position_x = ctx.rng.uniform(-50, 50)
        wave.start_position_y = ctx.rng.uniform(-50, 50)
    for tag in tags:
        ctx.tag(tag, obj)
    return obj


def pool(ctx, name, loc, size=(8.0, 4.0), deck=True):
    """Raised pool deck with a dark basin and a water slab that can be lowered to 'drain' it."""
    w, d = size
    x, y, z = loc
    if deck:
        box(ctx, f"{name}.deck", (w + 2.4, d + 2.4, 0.3), (x, y, z), ctx.mat("plaster"), bevel=0.05, anchor="base")
    tile = ctx.mat("white", roughness=0.4)
    walls = [((0, 0, 0.05), (w, d, 0.1), 0), ((0, d / 2 - 0.08, 0.65), (w, 0.16, 1.2), 0), ((0, -d / 2 + 0.08, 0.65), (w, 0.16, 1.2), 0), ((w / 2 - 0.08, 0, 0.65), (0.16, d, 1.2), 0), ((-w / 2 + 0.08, 0, 0.65), (0.16, d, 1.2), 0)]
    multi_box(ctx, f"{name}.basin", walls, [tile], (x, y, z + 0.32))
    water = box(ctx, f"{name}.water", (w - 0.3, d - 0.3, 0.12), (x, y, z + 1.3), ctx.palette.water(f"{name} water", "pool", alpha=0.9, scale=2.0, bump=0.15), anchor="base")
    ctx.tag("water", water)
    ctx.tag("pool", water)
    return water


def fountain(ctx, name, loc, radius=3.0):
    x, y, z = loc
    cylinder(ctx, f"{name}.basin", radius, 0.7, (x, y, z), ctx.mat("stone"), segments=24, anchor="base", bevel=0.05)
    water = cylinder(ctx, f"{name}.water", radius - 0.3, 0.1, (x, y, z + 0.55), ctx.palette.water(f"{name} water", "pool", scale=3.0), segments=24, anchor="base")
    cylinder(ctx, f"{name}.column", 0.35, 2.2, (x, y, z + 0.5), ctx.mat("stone"), segments=10, anchor="base")
    cylinder(ctx, f"{name}.bowl", 1.1, 0.35, (x, y, z + 2.5), ctx.mat("stone"), segments=16, anchor="base", radius2=0.9)
    jet = cone(ctx, f"{name}.jet", 0.28, 2.2, (x, y, z + 2.8), ctx.palette.water(f"{name} jet", "pool", alpha=0.75), segments=10, tip=0.05)
    for tag in ("water", "fountain"):
        ctx.tag(tag, water)
    ctx.tag("jet", jet)
    return water


def river(ctx, name, points, width=8.0, z=0.12, bed=True, bank=True):
    """Ribbon of water along a polyline, with a wider dark bed and low banks so it reads as a channel."""

    def ribbon(label, w, zz, mat):
        verts, faces = [], []
        for i, (px, py) in enumerate(points):
            if i == 0:
                dx, dy = points[1][0] - px, points[1][1] - py
            elif i == len(points) - 1:
                dx, dy = px - points[i - 1][0], py - points[i - 1][1]
            else:
                dx, dy = points[i + 1][0] - points[i - 1][0], points[i + 1][1] - points[i - 1][1]
            length = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / length * w / 2, dx / length * w / 2
            verts += [(px + nx, py + ny, zz), (px - nx, py - ny, zz)]
            if i:
                a = 2 * (i - 1)
                faces.append((a, a + 1, a + 3, a + 2))
        return mesh_from_pydata(ctx, label, verts, faces, [mat])

    if bed:
        ribbon(f"{name}.bed", width + 3.0, 0.02, ctx.mat("mud", roughness=0.95))
    if bank:
        ribbon(f"{name}.bank", width + 5.0, 0.01, ctx.mat("stone"))
        for side in (-1, 1):
            pass
    water = ribbon(name, width, z, ctx.palette.water(f"{name} water", "river", scale=1.2, bump=0.2))
    ctx.tag("water", water)
    ctx.tag("river", water)
    return water


def tank(ctx, name, loc, radius=1.2, height=1.6, level=0.8, legs=True):
    """Rooftop water tank; the inner water disc is tagged so events can lower it."""
    x, y, z = loc
    base = z
    if legs:
        for dx, dy in ((-0.6, -0.6), (0.6, -0.6), (0.6, 0.6), (-0.6, 0.6)):
            cylinder(ctx, f"{name}.leg", 0.08, 1.0, (x + dx * radius, y + dy * radius, z), ctx.mat("dark_steel"), segments=8, anchor="base")
        base = z + 1.0
    cylinder(ctx, f"{name}.shell", radius, height, (x, y, base), ctx.mat("steel", roughness=0.55), segments=16, anchor="base", bevel=0.04)
    water = cylinder(ctx, f"{name}.water", radius - 0.08, 0.06, (x, y, base + height * level), ctx.palette.water(f"{name} water", "lake"), segments=16, anchor="base")
    ctx.tag("water", water)
    ctx.tag("tank_water", water)
    return water


def trough(ctx, name, loc, size=(3.0, 0.9)):
    x, y, z = loc
    w, d = size
    box(ctx, f"{name}.shell", (w, d, 0.6), (x, y, z), ctx.mat("steel", roughness=0.5), bevel=0.03, anchor="base")
    box(ctx, f"{name}.inside", (w - 0.16, d - 0.16, 0.5), (x, y, z + 0.12), ctx.mat("dark_steel"), anchor="base")
    water = box(ctx, f"{name}.water", (w - 0.2, d - 0.2, 0.05), (x, y, z + 0.48), ctx.palette.water(f"{name} water", "lake"), anchor="base")
    ctx.tag("water", water)
    ctx.tag("trough_water", water)
    return water


def float_on(ctx, obj, water):
    """Parent an object to a water surface so it drops when the water level drops."""
    world = obj.location.copy()
    parent(obj, water)
    obj.location = world - water.location
    return obj
