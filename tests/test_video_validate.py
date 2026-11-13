import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from studio.video.validate import detect_black, frames_complete, missing_frames, validate_output

FFMPEG = shutil.which("ffmpeg")


def synth(path, width=1080, height=1920, fps=30, seconds=1.0, audio=True, black=False):
    source = f"color=c=black:s={width}x{height}:r={fps}:d={seconds}" if black else f"testsrc2=s={width}x{height}:r={fps}:d={seconds}"
    cmd = [FFMPEG, "-y", "-v", "error", "-f", "lavfi", "-i", source]
    if audio:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(fps)]
    if audio:
        cmd += ["-c:a", "aac", "-shortest"]
    cmd += ["-t", str(seconds), str(path)]
    subprocess.run(cmd, check=True)
    return path


@unittest.skipUnless(FFMPEG, "ffmpeg is not installed")
class VideoValidationTests(unittest.TestCase):
    def test_valid_vertical_video_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            path = synth(Path(temp) / "ok.mp4")
            self.assertEqual(validate_output(path, 1080, 1920, 30, 1.0), [])

    def test_wrong_dimensions_frame_rate_duration_and_missing_audio(self):
        with tempfile.TemporaryDirectory() as temp:
            path = synth(Path(temp) / "bad.mp4", width=720, height=1280, fps=25, seconds=1.0, audio=False)
            problems = validate_output(path, 1080, 1920, 30, 2.0)
        text = " ".join(problems)
        self.assertIn("resolution", text)
        self.assertIn("frame rate", text)
        self.assertIn("no audio stream", text)
        self.assertIn("duration", text)

    def test_black_video_is_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = synth(Path(temp) / "black.mp4", black=True)
            self.assertTrue(detect_black(path))
            self.assertFalse(detect_black(synth(Path(temp) / "ok.mp4")))

    def test_missing_file_reports_cleanly(self):
        self.assertTrue(validate_output(Path("/nonexistent/out.mp4"), 1080, 1920, 30, 1.0))


class FrameCompletenessTests(unittest.TestCase):
    def test_missing_and_tiny_frames_are_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for frame in (1, 2, 4):
                (root / f"frame_{frame:04d}.png").write_bytes(b"x" * 2000)
            (root / "frame_0003.png").write_bytes(b"x")
            self.assertEqual(missing_frames(root, 5), [3, 5])
            self.assertFalse(frames_complete(root, 5))
            (root / "frame_0003.png").write_bytes(b"x" * 2000)
            (root / "frame_0005.png").write_bytes(b"x" * 2000)
            self.assertTrue(frames_complete(root, 5))


if __name__ == "__main__":
    unittest.main()
