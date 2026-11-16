"""Pipeline spec generation (no Blender or FFmpeg needed)."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

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


def write_deps(scene_dir, relative="studio/core/motion.py", digest=None):
    path = Path(__file__).resolve().parents[1] / relative
    scene_dir.mkdir(parents=True, exist_ok=True)
    (scene_dir / "deps.json").write_text(json.dumps({relative: digest or hashlib.sha256(path.read_bytes()).hexdigest()}), encoding="utf-8")


class DependencyTests(unittest.TestCase):
    def test_scene_hash_ignores_code_and_deps_track_imported_files(self):
        project = load_project("projects/water-crisis")
        pipeline = Pipeline(project, "preview", log=lambda _: None)
        with tempfile.TemporaryDirectory() as temp:
            scene_dir = Path(temp)
            self.assertFalse(pipeline.deps_current(scene_dir))
            write_deps(scene_dir)
            self.assertTrue(pipeline.deps_current(scene_dir))
            write_deps(scene_dir, digest="0" * 64)
            self.assertFalse(pipeline.deps_current(scene_dir))
            write_deps(scene_dir, relative="studio/core/missing.py", digest="0" * 64)
            self.assertFalse(pipeline.deps_current(scene_dir))

    def test_every_environment_maps_to_a_module_that_builds_it(self):
        from studio.core import catalogue

        root = Path(__file__).resolve().parents[1]
        for env_type, module in catalogue.ENVIRONMENTS.items():
            source = (root / (module.replace(".", "/") + ".py")).read_text(encoding="utf-8")
            self.assertIn(f"def {env_type}(", source, f"{module} does not define {env_type}")
            self.assertIn(f'"{env_type}": {env_type}', source, f"{module} does not register {env_type}")
            self.assertIn("def build(ctx, spec):", source)


class ProgressTests(unittest.TestCase):
    def test_progress_counts_only_frames_for_the_current_fingerprint(self):
        from tests.test_video_validate import fake_png

        project = load_project("projects/water-crisis")
        pipeline = Pipeline(project, "preview", log=lambda _: None)
        scene = project.scenes[0]
        with tempfile.TemporaryDirectory() as temp:
            pipeline.scenes_dir = Path(temp)
            done, total = pipeline.progress()
            self.assertEqual(done, 0)
            self.assertEqual(total, sum(s["frames"] + s["handle_frames"] for s in project.scenes))
            frames = pipeline.scene_dir(scene["id"]) / "frames"
            frames.mkdir(parents=True)
            for frame in range(1, 6):
                fake_png(frames / f"frame_{frame:04d}.png")
            (frames.parent / "scene.hash").write_text("stale", encoding="utf-8")
            self.assertEqual(pipeline.progress()[0], 0)
            (frames.parent / "scene.hash").write_text(pipeline.scene_hash(scene), encoding="utf-8")
            self.assertEqual(pipeline.progress()[0], 0)  # no record of the code it was rendered with
            write_deps(frames.parent)
            self.assertEqual(pipeline.progress()[0], 5)


class ResumeTests(unittest.TestCase):
    def test_interrupted_scene_render_resumes_without_discarding_frames(self):
        from tests.test_video_validate import fake_png

        project = load_project("projects/water-crisis")
        pipeline = Pipeline(project, "preview", log=lambda _: None)
        scene = project.scenes[1]
        total = scene["frames"] + scene["handle_frames"]
        with tempfile.TemporaryDirectory() as temp:
            pipeline.scenes_dir = Path(temp)
            frames_dir = pipeline.scene_dir(scene["id"]) / "frames"

            def killed(spec, name):
                write_deps(frames_dir.parent)  # Blender records dependencies before drawing frames
                frames_dir.mkdir(parents=True, exist_ok=True)
                for frame in range(1, 11):
                    fake_png(frames_dir / f"frame_{frame:04d}.png")
                fake_png(frames_dir / "frame_0011.png", complete=False)
                raise PipelineError("render stopped")

            seen = []

            def finishes(spec, name):
                seen.append(len(list(frames_dir.glob("frame_*.png"))))
                write_deps(frames_dir.parent)
                for frame in range(1, total + 1):
                    path = frames_dir / f"frame_{frame:04d}.png"
                    if not path.exists():
                        fake_png(path)

            pipeline._blender = killed
            with self.assertRaises(PipelineError):
                pipeline.render_scene(scene["id"])
            pipeline._blender = finishes
            self.assertFalse(pipeline.render_scene(scene["id"]).skipped)
            self.assertEqual(seen, [10])  # ten good frames kept, the truncated one redrawn
            self.assertTrue(pipeline.render_scene(scene["id"]).skipped)


if __name__ == "__main__":
    unittest.main()
