"""Pipeline spec generation (no Blender or FFmpeg needed)."""

import unittest

from studio.audio.subtitles import Cue
from studio.core.project import load_project
from studio.pipeline import Pipeline, PipelineError


class PipelineSpecTests(unittest.TestCase):
    def setUp(self):
        self.project = load_project("projects/water-crisis")
        self.pipeline = Pipeline(self.project, "preview", log=lambda _: None)

    def test_unknown_profile_is_rejected(self):
        with self.assertRaises(PipelineError):
            Pipeline(self.project, "cinema")

    def test_scene_spec_carries_timeline_and_output_paths(self):
        scene = self.project.scenes[1]
        spec = self.pipeline.scene_spec(scene)
        self.assertEqual(spec["mode"], "scene")
        self.assertEqual(spec["render"]["fps"], 30)
        self.assertEqual(spec["scene"]["start"], self.project.scenes[0]["duration"])
        self.assertGreater(spec["scene"]["handle_frames"], 0)
        self.assertTrue(spec["output"]["frames_dir"].endswith("frames"))
        still = self.pipeline.scene_spec(scene, still=5)
        self.assertEqual(still["still"], 5)
        self.assertTrue(still["output"]["frames_dir"].endswith("stills"))

    def test_scene_hash_changes_with_the_storyboard(self):
        scene = self.project.scenes[0]
        before = self.pipeline.scene_hash(scene)
        scene["camera"]["lens"] = 999
        self.assertNotEqual(before, self.pipeline.scene_hash(scene))

    def test_overlay_spec_uses_absolute_times_and_merges_hud_windows(self):
        cues = [Cue(0.5, 2.0, "Hello"), Cue(2.1, 3.0, "World")]
        spec = self.pipeline.overlay_spec(cues)
        self.assertEqual(spec["total_frames"], self.project.total_frames)
        self.assertEqual(len(spec["subtitles"]), 2)
        first_title = next(card for card in spec["cards"] if card["kind"] == "title")
        self.assertEqual(first_title["start"], 0.6)
        hud = spec["hud"]
        self.assertEqual(hud["label"], "TIME WITHOUT WATER")
        # the HUD appears mid-way through the hook and then stays on through every later scene
        self.assertEqual(len(hud["visible"]), 1)
        self.assertAlmostEqual(hud["visible"][0][1], self.project.duration)
        self.assertEqual(hud["keys"][-1][1], 24.0)
        self.assertTrue(all(0 <= card["start"] < card["end"] <= self.project.duration for card in spec["cards"]))

    def test_expected_size_follows_profile_scale(self):
        self.assertEqual(self.pipeline.expected_size(), (540, 960))
        self.assertEqual(Pipeline(self.project, "standard", log=lambda _: None).expected_size(), (1080, 1920))

    def test_sfx_cues_are_placed_on_the_film_timeline(self):
        cues = self.pipeline.sfx_cues()
        self.assertTrue(cues)
        self.assertTrue(all(0 <= cue.start <= self.project.duration for cue in cues))
        self.assertTrue(all(cue.path.suffix == ".wav" for cue in cues))


if __name__ == "__main__":
    unittest.main()
