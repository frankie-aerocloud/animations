"""Build one reusable scene from the first production."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

parser = argparse.ArgumentParser()
parser.add_argument("--scene-id", required=True)
parser.add_argument("--duration", type=float, required=True)
parser.add_argument("--fps", type=int, default=30)
parser.add_argument("--profile", choices=("preview", "standard", "high"), default="preview")
parser.add_argument("--output", required=True)
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else [])

output = Path(args.output)
output.mkdir(parents=True, exist_ok=True)

from studio.blender.story_scenes import build_story_scene  # noqa: E402

build_story_scene(args.scene_id, args.duration, args.fps, args.profile, output)
print(f"Built {args.scene_id}: {args.duration:g}s @ {args.fps}fps -> {output}")
