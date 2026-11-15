"""Engine configuration from render profiles and a resumable frame renderer."""

from __future__ import annotations

from pathlib import Path

import bpy


def configure(scene, render, profile):
    engines = {item.identifier for item in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items}
    wanted = "CYCLES" if render.get("engine") == "cycles" else "BLENDER_EEVEE"
    if wanted not in engines:
        wanted = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "CYCLES"
    scene.render.engine = wanted
    scene.render.resolution_x = int(render["width"])
    scene.render.resolution_y = int(render["height"])
    scene.render.resolution_percentage = max(1, round(float(profile.scale) * 100))
    scene.render.fps = int(render["fps"])
    scene.render.fps_base = 1.0
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.compression = 30
    scene.render.film_transparent = False
    scene.render.use_motion_blur = bool(profile.motion_blur)
    scene.render.motion_blur_shutter = 0.5
    if wanted.startswith("BLENDER_EEVEE"):
        eevee = scene.eevee
        eevee.taa_render_samples = int(profile.samples)
        eevee.use_shadows = True
        eevee.shadow_ray_count = 2 if profile.raytracing else 1
        eevee.shadow_step_count = 4 if profile.raytracing else 2
        eevee.use_raytracing = bool(profile.raytracing)
        if profile.raytracing:
            eevee.ray_tracing_options.resolution_scale = "2"
            eevee.use_fast_gi = True
        eevee.motion_blur_steps = 2 if profile.motion_blur else 1
    else:
        cycles = scene.cycles
        cycles.samples = int(profile.samples)
        cycles.use_denoising = bool(profile.denoise)
        preferences = bpy.context.preferences.addons.get("cycles")
        if preferences is not None:
            try:
                preferences.preferences.compute_device_type = "METAL"
                preferences.preferences.get_devices()
                cycles.device = "GPU"
            except (TypeError, AttributeError):
                cycles.device = "CPU"
    return wanted


def frame_path(frames_dir, frame):
    return Path(frames_dir) / f"frame_{frame:04d}.png"


def _complete(path):
    return path.exists() and path.stat().st_size > 1000


def render(scene, frames_dir, still=None):
    """Render all frames into frames_dir (resuming after the last complete frame) or one still."""
    frames_dir = Path(frames_dir)
    frames_dir.mkdir(parents=True, exist_ok=True)
    if still is not None:
        target = frame_path(frames_dir, int(still))
        scene.frame_set(int(still))
        scene.render.filepath = str(target)
        bpy.ops.render.render(write_still=True)
        print(f"[studio] still frame {still} -> {target}", flush=True)
        return 1
    first_missing = next((f for f in range(scene.frame_start, scene.frame_end + 1) if not _complete(frame_path(frames_dir, f))), None)
    if first_missing is None:
        print(f"[studio] all {scene.frame_end} frames already rendered", flush=True)
        return 0
    scene.frame_start = first_missing
    scene.render.filepath = str(frames_dir / "frame_")
    scene.render.use_file_extension = True
    print(f"[studio] rendering frames {first_missing}..{scene.frame_end} at {scene.render.resolution_percentage}%", flush=True)
    bpy.ops.render.render(animation=True)
    return scene.frame_end - first_missing + 1
