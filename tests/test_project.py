import copy
import unittest
from pathlib import Path

from studio.core.project import load_project, validate_project

PROJECT = "projects/water-crisis"


class ProjectValidationTests(unittest.TestCase):
    def setUp(self):
        self.project = load_project(PROJECT)

    def test_shipped_project_is_valid(self):
        self.assertEqual(validate_project(self.project), [])
        self.assertGreaterEqual(self.project.duration, 60.0)
        self.assertLessEqual(self.project.duration, 180.0)

    def assertProblem(self, text):
        problems = validate_project(self.project)
        self.assertTrue(any(text in p for p in problems), f"expected a problem containing {text!r}, got {problems}")

    def test_duplicate_scene_ids(self):
        self.project.scenes.append(copy.deepcopy(self.project.scenes[0]))
        self.assertProblem("duplicate scene id")

    def test_zero_duration(self):
        self.project.scenes[1]["duration"] = 0
        self.assertProblem("duration must be a positive")

    def test_unknown_environment_and_shot(self):
        self.project.scenes[0]["environment"]["type"] = "moon_base"
        self.project.scenes[0]["camera"]["shot"] = "crane_shot"
        self.assertProblem("environment.type")
        self.assertProblem("camera.shot")

    def test_transition_too_long(self):
        self.project.scenes[2]["transition"] = {"type": "dissolve", "duration": 99}
        self.assertProblem("transition.duration")

    def test_bad_fps_and_odd_resolution(self):
        self.project.render["fps"] = 0
        self.project.render["width"] = 1081
        self.assertProblem("render.fps")
        self.assertProblem("render.width")

    def test_line_references_missing_scene_and_late_offset(self):
        self.project.lines[0]["scene"] = "nope"
        self.project.lines[1]["at"] = 999
        self.assertProblem("unknown scene")
        self.assertProblem("must lie inside scene")

    def test_missing_recorded_narration_file(self):
        self.project.lines[0]["audio"] = "audio/narration/does-not-exist.wav"
        self.assertProblem("recorded narration file is missing")

    def test_missing_music_file(self):
        self.project.audio["music_file"] = "audio/music/missing.wav"
        self.assertProblem("music_file is missing")

    def test_missing_asset_path_and_licence(self):
        self.project.assets.append({"id": "tree_pack", "type": "model", "path": "assets/models/missing.glb", "source": "somewhere"})
        self.assertProblem("file is missing")
        self.assertProblem("missing licence")

    def test_event_outside_scene(self):
        self.project.scenes[0]["events"].append({"type": "hide", "target": "tag:water", "at": 500})
        self.assertProblem("event hide")

    def test_caption_without_text(self):
        self.project.scenes[0]["captions"].append({"text": "   ", "at": 0, "until": 1})
        self.assertProblem("captions need text")

    def test_lion_actors_are_validated_against_lion_actions(self):
        self.project.scenes[0].setdefault("actors", []).append({"id": "leo", "kind": "lion", "action": "prowl"})
        self.assertEqual(validate_project(self.project), [])
        self.project.scenes[0]["actors"].append({"id": "bad", "kind": "lion", "action": "point"})
        self.assertProblem("lion bad action")
        self.project.scenes[0]["actors"].append({"id": "odd", "kind": "dragon"})
        self.assertProblem("kind must be one of")

    def test_rain_level_must_be_between_zero_and_one(self):
        self.project.scenes[0]["music"] = {"intensity": 0.5, "rain": 1.5}
        self.assertProblem("music.rain")

    def test_unknown_sfx(self):
        self.project.scenes[0]["sfx"].append({"sound": "explosion", "at": 1})
        self.assertProblem("sfx sound")


class ShippedProjectsTests(unittest.TestCase):
    def test_every_shipped_project_is_valid_and_short_form(self):
        for project_dir in sorted(Path("projects").iterdir()):
            if not (project_dir / "storyboard.yaml").exists():
                continue  # e.g. the legacy projects/world-runs-out-of-water from the first attempt
            with self.subTest(project=project_dir.name):
                project = load_project(project_dir)
                self.assertEqual(validate_project(project), [])
                self.assertTrue(90.0 <= project.duration <= 180.0, project.duration)


if __name__ == "__main__":
    unittest.main()
