"""Frame-by-frame resumable render of a built scene."""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

parser = argparse.ArgumentParser()
parser.add_argument("--profile", choices=("preview", "standard", "high"), default="preview")
parser.add_argument("--blend", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
import bpy  # noqa: E402
from studio.core.configuration import PROFILES  # noqa: E402

blend = Path(args.blend)
root = Path(args.output)
frames = root / "frames"
frames.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(blend))
scene = bpy.context.scene
profile = PROFILES[args.profile]
scene.render.resolution_percentage = round(profile.scale * 100)
if scene.render.engine == "CYCLES":
    scene.cycles.samples = profile.samples
    scene.cycles.use_denoising = profile.denoise
for frame in range(scene.frame_start, scene.frame_end + 1):
    target = frames / f"frame_{frame:04d}.png"
    if target.exists() and target.stat().st_size > 1000:
        continue
    scene.frame_set(frame)
    scene.render.filepath = str(target)
    bpy.ops.render.render(write_still=True)
    print(f"Rendered frame {frame}/{scene.frame_end}", flush=True)
