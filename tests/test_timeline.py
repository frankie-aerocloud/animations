import unittest

from studio.core.timeline import MIN_HANDLE_FRAMES, annotate, handle_frames, make_timeline


class TimelineTests(unittest.TestCase):
    def test_scene_spans_are_contiguous_and_frame_inclusive(self):
        spans = make_timeline([{"id": "a", "duration": 2}, {"id": "b", "duration": 1}], 30)
        self.assertEqual((spans[0].start, spans[0].end), (1, 60))
        self.assertEqual((spans[1].start, spans[1].end), (61, 90))
        self.assertEqual(spans[1].duration, 30)

    def test_zero_frames_rejected(self):
        with self.assertRaisesRegex(ValueError, "no frames"):
            make_timeline([{"id": "a", "duration": 0.001}], 30)

    def test_handle_frames_follow_transition_but_never_below_minimum(self):
        self.assertEqual(handle_frames({"transition": {"type": "whip", "duration": 0.35}}, 30, False), 10)
        self.assertEqual(handle_frames({"transition": {"type": "cut", "duration": 0}}, 30, False), MIN_HANDLE_FRAMES)
        self.assertEqual(handle_frames({"transition": {"type": "cut"}}, 30, True), 0)

    def test_annotate_adds_absolute_starts_and_frame_counts(self):
        scenes = [{"id": "a", "duration": 1.5}, {"id": "b", "duration": 2.0, "transition": {"duration": 0.5}}, {"id": "c", "duration": 1.0}]
        annotate(scenes, 30)
        self.assertEqual([s["start"] for s in scenes], [0.0, 1.5, 3.5])
        self.assertEqual([s["frames"] for s in scenes], [45, 60, 30])
        self.assertEqual([s["handle_frames"] for s in scenes], [2, 15, 0])


if __name__ == "__main__":
    unittest.main()
