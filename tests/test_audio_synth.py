import tempfile
import unittest
import wave
from pathlib import Path

from studio.audio import sfx
from studio.audio.music import render_score


class AudioSynthTests(unittest.TestCase):
    def test_every_sound_renders_a_valid_wav(self):
        with tempfile.TemporaryDirectory() as temp:
            for name in sfx.SOUNDS:
                path = sfx.render(name, Path(temp) / f"{name}.wav")
                with wave.open(str(path), "rb") as handle:
                    self.assertEqual(handle.getframerate(), sfx.RATE)
                    self.assertEqual(handle.getnchannels(), 1)
                    self.assertGreater(handle.getnframes(), 100)

    def test_score_matches_timeline_length_and_scene_intensity(self):
        scenes = [{"duration": 0.5, "music": {"intensity": 0.2}}, {"duration": 0.75, "music": {"intensity": 0.9}}]
        with tempfile.TemporaryDirectory() as temp:
            path = render_score(scenes, Path(temp) / "score.wav", sample_rate=8000)
            with wave.open(str(path), "rb") as handle:
                self.assertEqual(handle.getnframes(), 10000)
                self.assertEqual(handle.getframerate(), 8000)


if __name__ == "__main__":
    unittest.main()
