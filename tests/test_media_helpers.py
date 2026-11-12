from pathlib import Path
import tempfile
import unittest
import wave

from studio.audio.sound_design import render_ambient_bed
from studio.audio.subtitles import write_srt


class MediaHelperTests(unittest.TestCase):
    def test_srt_cues_are_split_and_remain_inside_scene_boundaries(self):
        with tempfile.TemporaryDirectory() as temp:
            target = write_srt(
                [
                    {"duration": 2.0, "narration": "First line."},
                    {"duration": 1.5, "narration": "Second line."},
                ],
                Path(temp) / "captions.srt",
            )
            contents = target.read_text(encoding="utf-8")
            self.assertIn("00:00:00,200 --> 00:00:01,800", contents)
            self.assertIn("00:00:02,200 --> 00:00:03,300", contents)

    def test_long_narration_is_broken_into_mobile_sized_cues(self):
        with tempfile.TemporaryDirectory() as temp:
            target = write_srt(
                [
                    {
                        "duration": 8.0,
                        "narration": "Imagine waking up tomorrow and discovering the world has run out of usable water.",
                    }
                ],
                Path(temp) / "captions.srt",
            )
            contents = target.read_text(encoding="utf-8")
            self.assertEqual(contents.count(" --> "), 2)
            self.assertIn("00:00:00,200 -->", contents)
            self.assertIn("\n\n2\n", contents)
            self.assertNotIn("00:00:08,", contents)

    def test_ambient_bed_has_expected_duration_and_pcm(self):
        with tempfile.TemporaryDirectory() as temp:
            target = render_ambient_bed([0.25, 0.25], Path(temp) / "bed.wav", sample_rate=8000)
            with wave.open(str(target), "rb") as audio:
                self.assertEqual(audio.getnchannels(), 1)
                self.assertEqual(audio.getframerate(), 8000)
                self.assertEqual(audio.getnframes(), 4000)
                self.assertGreater(len(audio.readframes(4000)), 0)


if __name__ == "__main__":
    unittest.main()
