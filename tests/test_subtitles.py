import tempfile
import unittest
from pathlib import Path

from studio.audio.narration import LineAudio, check_fit
from studio.audio.subtitles import Cue, make_cues, phrases, timecode, validate_cues, write_srt


def line(lid, start, duration, text):
    return LineAudio(lid, "s", start, duration, Path(f"{lid}.wav"), text)


class SubtitleTests(unittest.TestCase):
    def test_phrases_respect_max_chars_and_punctuation(self):
        parts = phrases("Six hours in, supermarket shelves would be stripped of bottled water, and emergency distribution points would open.", 40)
        self.assertTrue(all(len(p) <= 40 for p in parts))
        self.assertEqual(" ".join(parts).replace("  ", " "), "Six hours in, supermarket shelves would be stripped of bottled water, and emergency distribution points would open.")

    def test_cues_stay_inside_their_line(self):
        cues = make_cues([line("n01", 2.0, 6.0, "What if, in a single day, every tap, river and reservoir on Earth simply stopped giving us water?")], max_chars=36)
        self.assertGreater(len(cues), 1)
        self.assertEqual(cues[0].start, 2.0)
        self.assertLessEqual(cues[-1].end, 8.0 + 0.01)
        self.assertEqual(validate_cues(cues, 10.0), [])

    def test_validate_cues_reports_bad_timestamps(self):
        problems = validate_cues([Cue(1.0, 0.5, "x"), Cue(0.4, 2.0, "y"), Cue(3.0, 40.0, "")], 10.0)
        self.assertTrue(any("ends before it starts" in p for p in problems))
        self.assertTrue(any("overlaps" in p for p in problems))
        self.assertTrue(any("outside the film" in p for p in problems))
        self.assertTrue(any("empty" in p for p in problems))

    def test_srt_format(self):
        with tempfile.TemporaryDirectory() as temp:
            path = write_srt([Cue(0.2, 1.8, "First line."), Cue(2.2, 3.3, "Second line.")], Path(temp) / "captions.srt")
            contents = path.read_text(encoding="utf-8")
        self.assertIn("1\n00:00:00,200 --> 00:00:01,800\nFirst line.", contents)
        self.assertIn("2\n00:00:02,200 --> 00:00:03,300\nSecond line.", contents)
        self.assertEqual(timecode(3661.5), "01:01:01,500")

    def test_narration_overlap_detected(self):
        problems = check_fit([line("a", 0.0, 5.0, "x"), line("b", 4.0, 2.0, "y")], 10.0)
        self.assertTrue(any("runs into" in p for p in problems))
        self.assertEqual(check_fit([line("a", 0.0, 3.0, "x"), line("b", 4.0, 2.0, "y")], 10.0), [])
        self.assertTrue(check_fit([line("a", 0.0, 3.0, "x")], 2.0))


if __name__ == "__main__":
    unittest.main()
