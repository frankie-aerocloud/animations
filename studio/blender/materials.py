"""Palette-driven materials: flat low-poly surfaces, water, terrain ramps and emissives."""

from __future__ import annotations

import bpy


class Palette:
    def __init__(self, style):
        self.colours = {name: tuple(float(c) for c in rgb) for name, rgb in style["palette"].items()}
        self.roughness = float(style.get("roughness", 0.72))
        self._cache = {}

    def colour(self, name):
        if isinstance(name, str):
            return self.colours[name]
        return tuple(float(c) for c in name)

    def get(self, name, roughness=None, metallic=0.0, emission=0.0, alpha=1.0):
        cache_key = (str(name), roughness, metallic, emission, alpha)
        material = self._cache.get(cache_key)
        if material is None:
            material = self.make(str(name), self.colour(name), roughness, metallic, emission, alpha)
            self._cache[cache_key] = material
        return material

    def make(self, name, rgb, roughness=None, metallic=0.0, emission=0.0, alpha=1.0):
        material = bpy.data.materials.new(name)
        material.use_nodes = True
        bsdf = material.node_tree.nodes["Principled BSDF"]
        bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
        bsdf.inputs["Roughness"].default_value = self.roughness if roughness is None else roughness
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Specular IOR Level"].default_value = 0.35
        if emission:
            bsdf.inputs["Emission Color"].default_value = (*rgb, 1.0)
            bsdf.inputs["Emission Strength"].default_value = emission
        if alpha < 1.0:
            bsdf.inputs["Alpha"].default_value = alpha
            material.surface_render_method = "BLENDED"
        material.diffuse_color = (*rgb, 1.0)
        return material

    def emissive(self, name, rgb, strength=1.0):
        material = bpy.data.materials.new(name)
        material.use_nodes = True
        nodes = material.node_tree.nodes
        nodes.clear()
        emit = nodes.new("ShaderNodeEmission")
        emit.inputs["Color"].default_value = (*self.colour(rgb), 1.0)
        emit.inputs["Strength"].default_value = strength
        out = nodes.new("ShaderNodeOutputMaterial")
        material.node_tree.links.new(emit.outputs[0], out.inputs["Surface"])
        return material

    def water(self, name, rgb, roughness=0.08, alpha=1.0, bump=0.25, scale=0.4):
        material = self.make(name, self.colour(rgb), roughness, 0.0, 0.0, alpha)
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        bsdf = nodes["Principled BSDF"]
        fresnel = nodes.new("ShaderNodeLayerWeight")
        fresnel.inputs["Blend"].default_value = 0.55
        mix = nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        base = self.colour(rgb)
        mix.inputs[6].default_value = (*base, 1.0)
        mix.inputs[7].default_value = (min(1, base[0] + 0.35), min(1, base[1] + 0.35), min(1, base[2] + 0.30), 1.0)
        links.new(fresnel.outputs["Fresnel"], mix.inputs[0])
        links.new(mix.outputs[2], bsdf.inputs["Base Color"])
        noise = nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = scale
        noise.inputs["Detail"].default_value = 3.0
        bump_node = nodes.new("ShaderNodeBump")
        bump_node.inputs["Strength"].default_value = bump
        links.new(noise.outputs["Fac"], bump_node.inputs["Height"])
        links.new(bump_node.outputs["Normal"], bsdf.inputs["Normal"])
        bsdf.inputs["Specular IOR Level"].default_value = 0.6
        return material

    def terrain(self, name, stops, roughness=0.9, noise_mix=0.08):
        """Height-banded material: stops = [(z, colour_name), ...] from low to high (object space Z)."""
        material = self.make(name, self.colour(stops[-1][1]), roughness)
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        bsdf = nodes["Principled BSDF"]
        coords = nodes.new("ShaderNodeTexCoord")
        separate = nodes.new("ShaderNodeSeparateXYZ")
        links.new(coords.outputs["Object"], separate.inputs[0])
        map_range = nodes.new("ShaderNodeMapRange")
        z_min, z_max = stops[0][0], stops[-1][0]
        map_range.inputs["From Min"].default_value = z_min
        map_range.inputs["From Max"].default_value = z_max
        links.new(separate.outputs["Z"], map_range.inputs["Value"])
        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.interpolation = "LINEAR"
        ramp.color_ramp.elements[0].position = 0.0
        ramp.color_ramp.elements[0].color = (*self.colour(stops[0][1]), 1.0)
        ramp.color_ramp.elements[1].position = 1.0
        ramp.color_ramp.elements[1].color = (*self.colour(stops[-1][1]), 1.0)
        for z, colour in stops[1:-1]:
            element = ramp.color_ramp.elements.new((z - z_min) / max(1e-6, z_max - z_min))
            element.color = (*self.colour(colour), 1.0)
        links.new(map_range.outputs[0], ramp.inputs[0])
        noise = nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 0.05
        mix = nodes.new("ShaderNodeMix")
        mix.data_type = "RGBA"
        mix.inputs[0].default_value = noise_mix
        links.new(ramp.outputs[0], mix.inputs[6])
        links.new(noise.outputs["Color"], mix.inputs[7])
        links.new(mix.outputs[2], bsdf.inputs["Base Color"])
        return material

    def cracked(self, name, rgb, crack="mud", scale=0.35):
        """Dry, cracked ground: Voronoi edge lines darken a base colour."""
        material = self.make(name, self.colour(rgb), 0.95)
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        bsdf = nodes["Principled BSDF"]
        voronoi = nodes.new("ShaderNodeTexVoronoi")
        voronoi.feature = "DISTANCE_TO_EDGE"
        voronoi.inputs["Scale"].default_value = scale
        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.0
        ramp.color_ramp.elements[0].color = (*self.colour(crack), 1.0)
        ramp.color_ramp.elements[1].position = 0.08
        ramp.color_ramp.elements[1].color = (*self.colour(rgb), 1.0)
        links.new(voronoi.outputs["Distance"], ramp.inputs[0])
        links.new(ramp.outputs[0], bsdf.inputs["Base Color"])
        return material

    def glass(self, name="glass", rgb="glass"):
        return self.get(rgb, roughness=0.18, metallic=0.15)
