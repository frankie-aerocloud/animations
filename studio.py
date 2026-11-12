#!/usr/bin/env python3
"""Command line entry point for the local Blender animation studio."""

from __future__ import annotations
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECTS = ROOT / "projects"


def tool(name: str) -> str | None:
    return shutil.which(name)


def doctor() -> int:
    print(f"Python:   {sys.version.split()[0]} ({sys.executable})")
    required = {"blender": tool("blender"), "ffmpeg": tool("ffmpeg"), "ffprobe": tool("ffprobe")}
    for name, path in required.items():
        print(f"{name:9} {path or 'MISSING'}")
    try:
        import yaml  # noqa: F401

        print("PyYAML:   available")
    except ImportError:
        print("PyYAML:   MISSING (install .venv/bin/python -m pip install -r requirements-dev.txt)")
    print(f".venv:    {'active' if sys.prefix != sys.base_prefix else 'not active'}")
    return 0 if all(required.values()) else 2


def project_path(identifier: str) -> Path:
    candidate = Path(identifier)
    if not candidate.is_absolute():
        candidate = PROJECTS / candidate
    return candidate


def load(identifier: str):
    from studio.core.project import load_project

    return load_project(project_path(identifier))


def validate(identifier: str) -> int:
    from studio.core.timeline import make_timeline

    config = load(identifier)
    spans = make_timeline(config["scenes"], config["render"]["fps"])
    duration = sum(float(s["duration"]) for s in config["scenes"])
    print(
        f"Valid: {config['project']['title']} | {len(spans)} scenes | {duration:g}s | {config['render']['fps']}fps"
    )
    return 0


def blender_command(script: Path, *args: str) -> list[str]:
    blender = tool("blender")
    if not blender:
        raise RuntimeError(
            "Blender is not installed or not on PATH. Install Blender, then rerun `python studio.py doctor`."
        )
    return [
        blender,
        "--background",
        "--factory-startup",
        "--python-exit-code",
        "1",
        "--python",
        str(script),
        "--",
        *args,
    ]


def quality_test(profile: str) -> int:
    out = ROOT / "output" / "world-runs-out-of-water" / "quality-test"
    out.mkdir(parents=True, exist_ok=True)
    build = ROOT / "scripts" / "blender" / "build_kitchen_qc.py"
    render = ROOT / "scripts" / "blender" / "render_frames.py"
    subprocess.run(blender_command(build, "--profile", profile, "--output", str(out)), check=True)
    subprocess.run(
        blender_command(
            render,
            "--profile",
            profile,
            "--blend",
            str(out / "kitchen-qc.blend"),
            "--output",
            str(out),
        ),
        check=True,
    )
    if tool("ffmpeg"):
        subprocess.run(
            [sys.executable, str(ROOT / "studio.py"), "export", str(out), "--profile", profile],
            check=True,
        )
    else:
        print(f"Rendered PNG frames in {out / 'frames'}; FFmpeg is required to create MP4.")
    return 0


def export_frames(frame_dir: Path, output: Path, fps: int) -> int:
    ffmpeg, ffprobe = tool("ffmpeg"), tool("ffprobe")
    if not ffmpeg or not ffprobe:
        raise RuntimeError(
            "FFmpeg and FFprobe are required for export. Install ffmpeg (includes ffprobe)."
        )
    pattern = str(frame_dir / "frame_%04d.png")
    cmd = [
        ffmpeg,
        "-y",
        "-framerate",
        str(fps),
        "-start_number",
        "1",
        "-i",
        pattern,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "19",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output),
    ]
    subprocess.run(cmd, check=True)
    probe = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "stream=codec_name,width,height,r_frame_rate",
            "-of",
            "default=noprint_wrappers=1",
            str(output),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    print(probe.stdout.strip())
    return 0


def _encode_scene_frames(frames: Path, output: Path, fps: int, count: int) -> None:
    ffmpeg = tool("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required to encode scene clips.")
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-v",
            "error",
            "-framerate",
            str(fps),
            "-start_number",
            "1",
            "-i",
            str(frames / "frame_%04d.png"),
            "-frames:v",
            str(count),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(output),
        ],
        check=True,
    )


def _stitch_scene_clips(clips: list[Path], durations: list[float], output: Path, fps: int) -> None:
    ffmpeg = tool("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required to join the scene clips.")
    fade = 0.24
    args = [ffmpeg, "-y", "-v", "error"]
    for clip in clips:
        args.extend(["-i", str(clip)])
    filters = []
    for index in range(len(clips)):
        pad = f",tpad=stop_mode=clone:stop_duration={fade}" if index else ""
        filters.append(
            f"[{index}:v]fps={fps},setsar=1,settb=1/{fps},setpts=PTS-STARTPTS{pad}[v{index}]"
        )
    previous = "v0"
    elapsed = 0.0
    for index in range(1, len(clips)):
        elapsed += durations[index - 1]
        offset = max(0.0, elapsed - fade)
        result = f"x{index}"
        filters.append(
            f"[{previous}][v{index}]xfade=transition=fade:duration={fade}:offset={offset:.6f}[{result}]"
        )
        previous = result
    total = sum(durations)
    filters.append(f"[{previous}]trim=duration={total:.6f},format=yuv420p[film]")
    args.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[film]",
            "-t",
            f"{total:.6f}",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "19",
            "-r",
            str(fps),
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )
    subprocess.run(args, check=True)


def render_film(identifier: str, profile: str, force: bool = False) -> int:
    from studio.audio.narration import assemble_narration, render_scene_narration
    from studio.audio.sound_design import render_ambient_bed
    from studio.audio.subtitles import write_srt
    from studio.core.timeline import make_timeline

    config = load(identifier)
    fps = int(config["render"]["fps"])
    scenes = config["scenes"]
    timeline = make_timeline(scenes, fps)
    durations = [float(scene["duration"]) for scene in scenes]
    output_root = ROOT / "output" / str(config["project"]["id"])
    scene_root = output_root / "scenes"
    if force and scene_root.exists():
        shutil.rmtree(scene_root)
    scene_clips: list[Path] = []
    build_script = ROOT / "scripts" / "blender" / "build_story_scene.py"
    render_script = ROOT / "scripts" / "blender" / "render_frames.py"
    for scene, span in zip(scenes, timeline, strict=True):
        scene_id = str(scene["id"])
        scene_dir = scene_root / scene_id / profile
        blend = scene_dir / f"{scene_id}.blend"
        clip = scene_dir / f"{scene_id}.mp4"
        frames = scene_dir / "frames"
        expected = span.duration
        frame_paths = [frames / f"frame_{n:04d}.png" for n in (1, expected)]
        if not blend.exists():
            scene_dir.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                blender_command(
                    build_script,
                    "--scene-id",
                    scene_id,
                    "--duration",
                    str(scene["duration"]),
                    "--fps",
                    str(fps),
                    "--profile",
                    profile,
                    "--output",
                    str(scene_dir),
                ),
                check=True,
            )
        if not all(path.exists() and path.stat().st_size > 1000 for path in frame_paths):
            subprocess.run(
                blender_command(
                    render_script,
                    "--profile",
                    profile,
                    "--blend",
                    str(blend),
                    "--output",
                    str(scene_dir),
                ),
                check=True,
            )
        if not clip.exists():
            _encode_scene_frames(frames, clip, fps, expected)
        scene_clips.append(clip)
        print(f"Scene ready: {scene_id} ({expected} frames)", flush=True)

    video_only = output_root / "film-picture.mp4"
    _stitch_scene_clips(scene_clips, durations, video_only, fps)
    subtitle_file = write_srt(scenes, output_root / "subtitles.srt")
    audio_dir = output_root / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    narration = None
    audio_config = config.get("audio", {})
    supplied_voice = audio_config.get("narration_wav")
    if supplied_voice:
        voice_path = Path(str(supplied_voice))
        if not voice_path.is_absolute():
            voice_path = project_path(identifier) / voice_path
        if not voice_path.exists():
            raise RuntimeError(f"Configured narration WAV was not found: {voice_path}")
        narration = audio_dir / "narration.wav"
        subprocess.run(
            [
                tool("ffmpeg"),
                "-y",
                "-v",
                "error",
                "-i",
                str(voice_path),
                "-ar",
                "48000",
                "-ac",
                "1",
                "-af",
                f"apad,atrim=duration={sum(durations):.6f}",
                "-c:a",
                "pcm_s16le",
                str(narration),
            ],
            check=True,
        )
        print(f"Narration: supplied local WAV ({voice_path}).")
    voice_clips = (
        []
        if narration
        else render_scene_narration(
            scenes,
            audio_dir,
            tool("ffmpeg") or "ffmpeg",
            str(audio_config.get("tts_voice", "Daniel")),
        )
    )
    if narration is None and len(voice_clips) == len(scenes):
        narration = assemble_narration(
            voice_clips, durations, audio_dir / "narration.wav", tool("ffmpeg") or "ffmpeg"
        )
        print("Narration: local macOS Daniel voice generated.")
    elif narration is None:
        print(
            "Narration: local system speech output was unavailable; rendering atmospheric bed and subtitles."
        )
    bed = render_ambient_bed(durations, audio_dir / "ambient-bed.wav")
    mixed = audio_dir / "mix.wav"
    ffmpeg = tool("ffmpeg")
    if narration:
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-v",
                "error",
                "-i",
                str(narration),
                "-i",
                str(bed),
                "-filter_complex",
                "[0:a]loudnorm=I=-18:TP=-2:LRA=7[v];[1:a]volume=0.42[m];[v][m]amix=inputs=2:duration=longest:normalize=0,alimiter=limit=0.95[a]",
                "-map",
                "[a]",
                "-ar",
                "48000",
                "-c:a",
                "pcm_s16le",
                str(mixed),
            ],
            check=True,
        )
    else:
        shutil.copyfile(bed, mixed)
    final = output_root / f"{config['project']['id']}.mp4"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-v",
            "error",
            "-i",
            str(video_only),
            "-i",
            str(mixed),
            "-i",
            str(subtitle_file),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-map",
            "2:s:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-c:s",
            "mov_text",
            "-shortest",
            "-movflags",
            "+faststart",
            str(final),
        ],
        check=True,
    )
    ffprobe = tool("ffprobe")
    probe = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_name,width,height,r_frame_rate",
            "-of",
            "default=noprint_wrappers=1",
            str(final),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    print(f"Exported: {final}\n{probe.stdout.strip()}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Code-first local Blender animation studio")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="check Blender, FFmpeg, Python and dependencies")
    init = sub.add_parser("init", help="create a project from the local template")
    init.add_argument("id")
    val = sub.add_parser("validate", help="validate project YAML and frame timeline")
    val.add_argument("project")
    qc = sub.add_parser("quality-test", help="build and render the 10-second kitchen QC scene")
    qc.add_argument("--profile", choices=("preview", "standard", "high"), default="preview")
    build = sub.add_parser("build", help="build the 10-second kitchen Blender scene")
    build.add_argument("project", nargs="?", default="world-runs-out-of-water")
    render = sub.add_parser("render", help="render the kitchen QC sequence")
    render.add_argument("project", nargs="?", default="world-runs-out-of-water")
    render.add_argument("--profile", choices=("preview", "standard", "high"), default="preview")
    film = sub.add_parser(
        "render-film", help="build, render, narrate and export the complete story"
    )
    film.add_argument("project", nargs="?", default="world-runs-out-of-water")
    film.add_argument("--profile", choices=("preview", "standard", "high"), default="preview")
    film.add_argument(
        "--force", action="store_true", help="discard prior scene renders and rebuild all scenes"
    )
    exp = sub.add_parser("export", help="encode an image sequence to H.264 MP4")
    exp.add_argument("frames")
    exp.add_argument("--output")
    exp.add_argument("--fps", type=int, default=30)
    exp.add_argument("--profile", choices=("preview", "standard", "high"), default="preview")
    clean = sub.add_parser("clean", help="remove generated output for a project")
    clean.add_argument("project", nargs="?", default="world-runs-out-of-water")
    args = parser.parse_args()
    try:
        if args.command == "doctor":
            return doctor()
        if args.command == "init":
            target = project_path(args.id)
            target.mkdir(parents=True, exist_ok=True)
            template = PROJECTS / "world-runs-out-of-water" / "project.yaml"
            shutil.copyfile(template, target / "project.yaml")
            print(f"Created {target / 'project.yaml'} (edit project id/title and scenes)")
            return 0
        if args.command == "validate":
            return validate(args.project)
        if args.command == "quality-test":
            return quality_test(args.profile)
        if args.command == "build":
            out = ROOT / "output" / "world-runs-out-of-water" / "quality-test"
            out.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                blender_command(
                    ROOT / "scripts/blender/build_kitchen_qc.py",
                    "--profile",
                    "preview",
                    "--output",
                    str(out),
                ),
                check=True,
            )
            return 0
        if args.command == "render":
            validate(args.project)
            out = ROOT / "output" / "world-runs-out-of-water" / "quality-test"
            subprocess.run(
                blender_command(
                    ROOT / "scripts/blender/render_frames.py",
                    "--profile",
                    args.profile,
                    "--blend",
                    str(out / "kitchen-qc.blend"),
                    "--output",
                    str(out),
                ),
                check=True,
            )
            return 0
        if args.command == "render-film":
            return render_film(args.project, args.profile, args.force)
        if args.command == "export":
            frame_dir = Path(args.frames)
            out = Path(args.output) if args.output else frame_dir / "kitchen-qc.mp4"
            return export_frames(
                frame_dir / "frames" if (frame_dir / "frames").is_dir() else frame_dir,
                out,
                args.fps,
            )
        if args.command == "clean":
            path = ROOT / "output" / Path(args.project).name
            if path.exists():
                shutil.rmtree(path)
            print(f"Cleaned {path}")
            return 0
    except (RuntimeError, ValueError, OSError, subprocess.CalledProcessError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
