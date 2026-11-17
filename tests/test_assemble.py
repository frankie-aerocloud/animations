import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from studio.video.assemble import assemble

FFMPEG = shutil.which("ffmpeg")


def clip(path, colour, frames, fps=30):
    subprocess.run([FFMPEG, "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c={colour}:s=64x112:r={fps}", "-frames:v", str(frames), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)], check=True)
    return path


def luma(path, w=64, h=112):
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", str(path), "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
    return [raw[i * w * h + (h // 2) * w + w // 2] for i in range(len(raw) // (w * h))]


@unittest.skipUnless(FFMPEG, "ffmpeg is not installed")
class AssembleTests(unittest.TestCase):
    def test_hard_cuts_have_no_blended_frame_and_dissolves_blend(self):
        # three 10-frame shots: a cut, then a 6-frame dissolve; each clip carries its handle frames
        scenes = [
            {"start": 0.0, "duration": 1 / 3, "frames": 10, "handle_frames": 2, "transition": {"type": "cut"}},
            {"start": 1 / 3, "duration": 1 / 3, "frames": 10, "handle_frames": 6, "transition": {"type": "dissolve", "duration": 0.2}},
            {"start": 2 / 3, "duration": 1 / 3, "frames": 10, "handle_frames": 0, "transition": {}},
        ]
        with tempfile.TemporaryDirectory() as temp:
            clips = [clip(Path(temp) / f"{i}.mp4", colour, 10 + scene["handle_frames"]) for i, (colour, scene) in enumerate(zip(("white", "black", "white"), scenes))]
            out = assemble(clips, scenes, None, None, None, Path(temp) / "film.mp4", 30, 1.0, {})
            values = luma(out)
        self.assertEqual(len(values), 30)
        self.assertTrue(all(v > 200 for v in values[:10]), values[:12])
        self.assertTrue(all(v < 40 for v in values[10:20]), values[8:22])  # the cut lands exactly on frame 10, unblended
        self.assertTrue(any(60 < v < 200 for v in values[20:26]), values[18:30])  # the dissolve does blend
        self.assertTrue(all(v > 200 for v in values[27:]), values[24:])


if __name__ == "__main__":
    unittest.main()
