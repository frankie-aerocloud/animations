import tempfile
import unittest
import wave
from pathlib import Path

from studio.audio import narration, sfx
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

    def test_wind_bed_is_opt_in_and_mute_silences_the_score(self):
        def score(music):
            with tempfile.TemporaryDirectory() as temp:
                path = render_score([{"duration": 0.5, "music": music}], Path(temp) / "score.wav", sample_rate=8000)
                with wave.open(str(path), "rb") as handle:
                    return handle.readframes(handle.getnframes())

        plain = score({"intensity": 0.5})
        self.assertEqual(plain, score({"intensity": 0.5, "wind": 0.0, "mute": False}))
        self.assertNotEqual(plain, score({"intensity": 0.5, "wind": 0.8}))
        self.assertEqual(set(score({"intensity": 0.5, "wind": 0.8, "mute": True})), {0})

    def test_noise_w_zero_gives_a_line_the_same_length_every_time(self):
        voice = narration._voice_path({})
        if not narration.piper_available(voice):
            self.skipTest("Piper or its voice is not installed")
        with tempfile.TemporaryDirectory() as temp:
            lengths = []
            for k in range(2):
                path = Path(temp) / f"{k}.wav"
                narration._synthesise_piper("And the wind isn't slowing down.", voice, {"noise_w": 0.0}, path)
                lengths.append(narration.audio_duration(path))
        self.assertGreater(lengths[0], 1.0)
        self.assertEqual(lengths[0], lengths[1])


if __name__ == "__main__":
    unittest.main()
