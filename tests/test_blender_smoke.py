"""Slow integration test: builds the cheapest scene inside Blender and renders one small still."""

import shutil
import unittest

import pytest

from studio.core.project import load_project
from studio.pipeline import Pipeline


@pytest.mark.slow
@unittest.skipUnless(shutil.which("blender") and shutil.which("ffmpeg"), "blender and ffmpeg are required")
class BlenderSmokeTest(unittest.TestCase):
    def test_kitchen_still_renders(self):
        project = load_project("projects/water-crisis")
        project.render["profiles"]["smoke"] = {"scale": 0.1, "samples": 2}
        pipeline = Pipeline(project, "smoke", log=lambda _: None)
        kitchen = next(scene["id"] for scene in project.scenes if scene["environment"]["type"] == "kitchen_interior")
        result = pipeline.render_scene(kitchen, still=1.0)
        stills = sorted(result.frames_dir.glob("frame_*.png"))
        self.assertTrue(stills, "no still produced")
        self.assertGreater(stills[-1].stat().st_size, 2000)

    def test_los_angeles_shelter_still_renders(self):
        # exercises the LA environments, bending palms, debris storms and the shelter interiors
        project = load_project("projects/la-wind")
        project.render["profiles"]["smoke"] = {"scale": 0.1, "samples": 2}
        pipeline = Pipeline(project, "smoke", log=lambda _: None)
        shelter = next(scene["id"] for scene in project.scenes if scene["environment"]["type"] == "la_interior" and scene["environment"].get("kind") == "apartment")
        result = pipeline.render_scene(shelter, still=1.0)
        stills = sorted(result.frames_dir.glob("frame_*.png"))
        self.assertTrue(stills, "no still produced")
        self.assertGreater(stills[-1].stat().st_size, 2000)

    def test_london_flat_still_renders(self):
        # exercises the London environments, terraces, looping rain and the linear-time mesher
        project = load_project("projects/london-rain")
        project.render["profiles"]["smoke"] = {"scale": 0.1, "samples": 2}
        pipeline = Pipeline(project, "smoke", log=lambda _: None)
        flat = next(scene["id"] for scene in project.scenes if scene["environment"]["type"] == "london_interior")
        result = pipeline.render_scene(flat, still=1.0)
        stills = sorted(result.frames_dir.glob("frame_*.png"))
        self.assertTrue(stills, "no still produced")
        self.assertGreater(stills[-1].stat().st_size, 2000)


if __name__ == "__main__":
    unittest.main()
