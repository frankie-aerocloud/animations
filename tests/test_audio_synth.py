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

    def test_rain_bed_is_opt_in_and_audible(self):
        def score(rain):
            music = [{"intensity": 0.4}, {"intensity": 0.4}]
            if rain is not None:
                for entry in music:
                    entry["rain"] = rain
            scenes = [{"duration": 0.5, "music": music[0]}, {"duration": 0.5, "music": music[1]}]
            with tempfile.TemporaryDirectory() as temp:
                return render_score(scenes, Path(temp) / "score.wav", sample_rate=8000).read_bytes()

        # films without rain render byte for byte as before; a rain level changes the score
        self.assertEqual(score(None), score(0.0))
        self.assertNotEqual(score(None), score(0.8))


if __name__ == "__main__":
    unittest.main()
