"""Blender entry point: `blender -b --python scene_builder.py -- spec.json` builds and renders one scene
(or the overlay pass) from a JSON spec written by studio.pipeline."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path


def main():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    spec_path = Path(argv[0])
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    root = spec["repo_root"]
    if root not in sys.path:
        sys.path.insert(0, root)
    import bpy

    from studio.blender import overlay

    started = time.time()
    output = Path(spec["output"]["dir"])
    output.mkdir(parents=True, exist_ok=True)
    if spec["mode"] == "overlay":
        overlay.run(spec)
        print(f"[studio] overlay pass finished in {time.time() - started:.1f}s", flush=True)
        return
    from studio.blender import animation, camera, environments, lighting, rendering
    from studio.assets import characters
    from studio.blender.materials import Palette
    from studio.blender.primitives import Ctx, load_font

    scene_spec = spec["scene"]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    fps = int(spec["render"]["fps"])
    nominal = int(scene_spec["frames"])
    handle = int(scene_spec.get("handle_frames", 0))
    scene.frame_start = 1
    scene.frame_end = max(1, nominal + handle)
    profile = overlay._Profile(spec["profile"])
    rendering.configure(scene, spec["render"], profile)
    collection = bpy.data.collections.new(scene_spec["id"])
    scene.collection.children.link(collection)
    ctx = Ctx(scene, collection, Palette(spec["style"]), spec["style"], profile, fps, nominal, handle, seed=int(scene_spec.get("seed", scene_spec.get("index", 0) + 1)))
    ctx.font = load_font(spec["font"])
    env = scene_spec["environment"]
    lighting.apply(ctx, scene_spec.get("lighting", "soft_daylight"), scene_spec.get("lighting_overrides"), fog_extent=environments.FOG_EXTENT.get(env["type"], (700, 700, 160)))
    environments.build(ctx, env)
    for actor_spec in scene_spec.get("actors") or []:
        characters.spawn(ctx, actor_spec)
    animation.apply_events(ctx, scene_spec.get("events") or [])
    camera.setup(ctx, scene_spec["camera"])
    scene.frame_set(1)
    objects = len(bpy.data.objects)
    print(f"[studio] built {scene_spec['id']} ({objects} objects) in {time.time() - started:.1f}s; {scene.frame_end} frames", flush=True)
    if spec.get("save_blend", True):
        bpy.ops.wm.save_as_mainfile(filepath=str(output / f"{scene_spec['id']}.blend"), compress=True)
    render_started = time.time()
    rendered = rendering.render(scene, spec["output"]["frames_dir"], spec.get("still"))
    seconds = time.time() - render_started
    (output / "done.json").write_text(json.dumps({"frames": scene.frame_end, "rendered": rendered, "seconds": round(seconds, 1), "objects": objects}), encoding="utf-8")
    print(f"[studio] rendered {rendered} frames in {seconds:.1f}s", flush=True)


main()
