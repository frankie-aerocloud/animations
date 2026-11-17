import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from studio.video.validate import PNG_END, detect_black, frames_complete, missing_frames, remove_partial_frames, validate_output

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


def fake_png(path, complete=True):
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 2000 + (b"\x00\x00\x00\x00" + PNG_END if complete else b""))
    return path


class FrameCompletenessTests(unittest.TestCase):
    def test_missing_tiny_and_truncated_frames_are_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for frame in (1, 2, 4):
                fake_png(root / f"frame_{frame:04d}.png")
            (root / "frame_0003.png").write_bytes(b"x")
            fake_png(root / "frame_0005.png", complete=False)
            self.assertEqual(missing_frames(root, 5), [3, 5])
            self.assertFalse(frames_complete(root, 5))
            self.assertEqual([p.name for p in remove_partial_frames(root)], ["frame_0003.png", "frame_0005.png"])
            fake_png(root / "frame_0003.png")
            fake_png(root / "frame_0005.png")
            self.assertTrue(frames_complete(root, 5))


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(FFMPEG, "ffmpeg is not installed")
class DeepCheckTests(unittest.TestCase):
    def test_faststart_and_decode_checks(self):
        from studio.video.validate import decode_errors, top_level_atoms

        with tempfile.TemporaryDirectory() as temp:
            slow = synth(Path(temp) / "slow.mp4")
            fast = Path(temp) / "fast.mp4"
            subprocess.run([FFMPEG, "-y", "-v", "error", "-i", str(slow), "-c", "copy", "-movflags", "+faststart", str(fast)], check=True)
            self.assertLess(top_level_atoms(fast).index("moov"), top_level_atoms(fast).index("mdat"))
            self.assertGreater(top_level_atoms(slow).index("moov"), top_level_atoms(slow).index("mdat"))
            self.assertEqual(decode_errors(fast), [])
            broken = Path(temp) / "broken.mp4"
            data = fast.read_bytes()
            broken.write_bytes(data[: len(data) // 2])
            self.assertTrue(decode_errors(broken))

    def test_frozen_picture_is_detected(self):
        from studio.video.validate import frozen_frames

        with tempfile.TemporaryDirectory() as temp:
            still = synth(Path(temp) / "still.mp4", seconds=3.0, black=True)
            moving = synth(Path(temp) / "moving.mp4", seconds=3.0)
            self.assertEqual(frozen_frames(still, 3.0), [(0.0, 3.0)])  # frozen to the very end: no freeze_end logged
            self.assertEqual(frozen_frames(moving, 3.0), [])

    def test_strobing_is_flagged_but_a_single_flash_is_not(self):
        from studio.video.validate import flashes

        with tempfile.TemporaryDirectory() as temp:
            strobe = Path(temp) / "strobe.mp4"  # white for 3 frames, black for 3: five flashes a second
            subprocess.run([FFMPEG, "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=108x192:r=30:d=2", "-vf", "geq=lum='if(lt(mod(N,6),3),235,16)':cb=128:cr=128", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(strobe)], check=True)
            single = Path(temp) / "single.mp4"  # one white burst in two seconds
            subprocess.run([FFMPEG, "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=108x192:r=30:d=2", "-vf", "geq=lum='if(between(N,20,22),235,16)':cb=128:cr=128", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(single)], check=True)
            self.assertGreater(flashes(strobe, 30)[0], 3)
            self.assertLessEqual(flashes(single, 30)[0], 1)
            self.assertEqual(flashes(synth(Path(temp) / "moving.mp4", 108, 192, seconds=2.0, audio=False), 30)[0], 0)

    def test_loudness_and_silence_parsing(self):
        from studio.video.validate import SILENCE, parse_intervals, parse_loudness

        stderr = "Summary:\n  Integrated loudness:\n    I:         -14.2 LUFS\n  Loudness range:\n    LRA:         6.1 LU\n  True peak:\n    Peak:       -1.3 dBFS\n"
        self.assertEqual(parse_loudness(stderr), {"integrated_lufs": -14.2, "range_lu": 6.1, "true_peak_dbfs": -1.3})
        silences = "[silencedetect] silence_start: 12.5\n[silencedetect] silence_end: 15.25 | silence_duration: 2.75\n"
        self.assertEqual(parse_intervals(silences, SILENCE), [(12.5, 15.25)])
