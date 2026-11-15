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
        result = pipeline.render_scene("s02_tap", still=1.0)
        stills = sorted(result.frames_dir.glob("frame_*.png"))
        self.assertTrue(stills, "no still produced")
        self.assertGreater(stills[-1].stat().st_size, 2000)


if __name__ == "__main__":
    unittest.main()
