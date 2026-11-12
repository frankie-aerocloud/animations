"""Build and save the stage-4 kitchen quality-control Blender file."""

from __future__ import annotations
import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

parser = argparse.ArgumentParser()
parser.add_argument("--profile", choices=("preview", "standard", "high"), default="preview")
parser.add_argument("--output", required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])
from studio.blender.scene_builder import build_quality_scene  # noqa: E402

output = Path(args.output)
output.mkdir(parents=True, exist_ok=True)
shutil.rmtree(output / "frames", ignore_errors=True)
(output / "kitchen-qc.mp4").unlink(missing_ok=True)
build_quality_scene(args.profile, output / "frames" / "frame_0001.png")
blend_path = output / "kitchen-qc.blend"
import bpy  # noqa: E402

bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
print(f"Saved kitchen QC scene: {blend_path}")
