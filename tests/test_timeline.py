import unittest

from studio.core.timeline import make_timeline
from studio.core.project import validate_project


class TimelineTests(unittest.TestCase):
    def test_scene_spans_are_contiguous_and_frame_inclusive(self):
        spans = make_timeline([{"id": "a", "duration": 2}, {"id": "b", "duration": 1}], 30)
        self.assertEqual((spans[0].start, spans[0].end), (1, 60))
        self.assertEqual((spans[1].start, spans[1].end), (61, 90))
        self.assertEqual(spans[1].duration, 30)

    def test_90_second_story_has_expected_total_frames(self):
        durations = [8, 12, 12, 13, 13, 15, 17]
        scenes = [{"id": f"s{i}", "duration": duration} for i, duration in enumerate(durations)]
        self.assertEqual(make_timeline(scenes, 30)[-1].end, 2700)

    def test_duplicate_ids_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            validate_project(
                {
                    "project": {},
                    "render": {"fps": 30},
                    "scenes": [{"id": "x", "duration": 1}, {"id": "x", "duration": 2}],
                }
            )

    def test_zero_duration_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "positive"):
            validate_project(
                {"project": {}, "render": {"fps": 30}, "scenes": [{"id": "x", "duration": 0}]}
            )


if __name__ == "__main__":
    unittest.main()
