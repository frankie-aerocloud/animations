"""Command line interface: python -m studio.cli <command> <project> [options]."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from studio.core.configuration import OUTPUT_DIR
from studio.core.project import load_project, validate_project
from studio.pipeline import Pipeline, PipelineError, failures

PROFILE_HELP = "render profile from config/render.yaml (preview, standard, high)"


def keep_awake() -> None:
    """macOS idle and maintenance sleep pause Blender for minutes at a time, so hold a sleep
    assertion until this process exits. `-s` applies on mains power only; batteries drain normally."""
    caffeinate = shutil.which("caffeinate")
    if sys.platform == "darwin" and caffeinate:
        subprocess.Popen([caffeinate, "-s", "-w", str(os.getpid())], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def doctor() -> int:
    print(f"python   {sys.version.split()[0]} ({sys.executable})")
    missing = []
    for name in ("blender", "ffmpeg", "ffprobe"):
        path = shutil.which(name)
        print(f"{name:8} {path or 'MISSING'}")
        missing.append(name) if not path else None
    for module, label in (("yaml", "PyYAML"), ("piper", "piper-tts")):
        try:
            __import__(module)
            print(f"{label:8} available")
        except ImportError:
            print(f"{label:8} MISSING ({'required' if module == 'yaml' else 'optional: offline narration'})")
    voices = sorted((Path(__file__).resolve().parents[1] / "assets" / "voices").glob("*.onnx"))
    print(f"voices   {', '.join(v.stem for v in voices) if voices else 'none downloaded (see assets/voices/README.md)'}")
    return 2 if missing else 0


def storyboard(pipeline: Pipeline, stills: bool) -> int:
    project = pipeline.project
    rows = []
    for scene in project.scenes:
        lines = [str(line["id"]) for line in project.lines if line.get("scene") == scene["id"]]
        captions = [str(c["text"]) for c in scene.get("captions") or []]
        rows.append((scene["id"], f"{scene['start']:.1f}", f"{scene['duration']:.1f}", scene["environment"]["type"], scene["camera"]["shot"], scene.get("lighting", "soft_daylight"), (scene.get("transition") or {}).get("type", "cut"), ", ".join(lines), " | ".join(captions)))
    header = ("scene", "start", "dur", "environment", "shot", "lighting", "out", "narration", "captions")
    widths = [max(len(str(r[i])) for r in [header, *rows]) for i in range(len(header))]
    text = [" ".join(str(cell).ljust(widths[i]) for i, cell in enumerate(row)) for row in [header, *rows]]
    print("\n".join(text))
    print(f"\n{len(project.scenes)} scenes, {project.duration:.1f}s, {project.total_frames} frames at {project.fps} fps")
    pipeline.out.mkdir(parents=True, exist_ok=True)
    md = ["# Storyboard: " + project.title, "", "| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    md += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    (pipeline.out / "storyboard.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    if stills:
        paths = []
        for scene in project.scenes:
            result = pipeline.render_scene(str(scene["id"]), still=float(scene["duration"]) / 2)
            paths.append(next(iter(sorted(result.frames_dir.glob("frame_*.png")))))
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg and paths:
            columns = min(4, len(paths))
            rows_n = -(-len(paths) // columns)
            inputs = [arg for p in paths for arg in ("-i", str(p))]
            graph = "".join(f"[{i}:v]scale=270:-1[s{i}];" for i in range(len(paths))) + "".join(f"[s{i}]" for i in range(len(paths))) + f"xstack=inputs={len(paths)}:layout=" + "|".join(f"{(i % columns) * 274}_{(i // columns) * 484}" for i in range(len(paths))) + ":fill=black[out]"
            sheet = pipeline.out / f"storyboard-{pipeline.profile.name}.png"
            subprocess.run([ffmpeg, "-y", "-v", "error", *inputs, "-filter_complex", graph, "-map", "[out]", "-frames:v", "1", str(sheet)], check=True)
            print(f"contact sheet: {sheet} ({columns}x{rows_n})")
    print(f"storyboard: {pipeline.out / 'storyboard.md'}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m studio.cli", description="Local, code-first low-poly animation studio (Blender + FFmpeg)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="check Blender, FFmpeg, Python packages and voices")

    def project_command(name: str, help_text: str) -> argparse.ArgumentParser:
        command = sub.add_parser(name, help=help_text)
        command.add_argument("project", help="project directory, e.g. projects/water-crisis")
        command.add_argument("--profile", default="preview", help=PROFILE_HELP)
        command.add_argument("--force", action="store_true", help="ignore cached renders and rebuild")
        return command

    project_command("validate", "validate project, storyboard, script and asset manifest")
    story = project_command("storyboard", "print the shot list; --stills renders one frame per scene into a contact sheet")
    story.add_argument("--stills", action="store_true")
    project_command("preview", "full build at the preview profile (low resolution, fast)")
    one = project_command("render-scene", "render one or more scenes")
    one.add_argument("--scene", action="append", required=True, help="scene id (repeatable)")
    one.add_argument("--still", type=float, help="render a single frame at this time (seconds) instead of the animation")
    project_command("render", "render every scene whose inputs changed")
    project_command("assemble", "narration, subtitles, overlay, audio mix, FFmpeg assembly, validation and manifest")
    project_command("build", "the complete pipeline")
    check = project_command("check", "play the finished MP4 end to end and run every technical check")
    check.add_argument("--file", type=Path, help="check this MP4 instead of the profile's output")
    clean = sub.add_parser("clean", help="delete generated output for a project")
    clean.add_argument("project")
    args = parser.parse_args(argv)
    if args.command == "doctor":
        return doctor()
    try:
        project = load_project(args.project)
        if args.command == "validate":
            errors = validate_project(project)
            for error in errors:
                print(f"error: {error}")
            print(f"{'INVALID' if errors else 'valid'}: {project.title} | {len(project.scenes)} scenes | {project.duration:.1f}s | {project.fps} fps | {len(project.lines)} narration lines")
            return 1 if errors else 0
        if args.command == "clean":
            target = OUTPUT_DIR / project.id
            if target.exists():
                shutil.rmtree(target)
            print(f"removed {target}")
            return 0
        pipeline = Pipeline(project, "preview" if args.command == "preview" else args.profile, force=args.force, log=lambda message: print(message, flush=True))
        if args.command == "check":
            target = args.file or pipeline.final
            if not target.exists():
                if args.file:
                    print(f"error: {target} does not exist", file=sys.stderr)
                    return 1
                done, total = pipeline.progress()
                print(f"{target.name} has not been built yet: {done} of {total} scene frames rendered ({100 * done // max(1, total)}%).")
                print(f"Build it with: python -m studio.cli build {args.project} --profile {pipeline.profile.name}")
                return 1
            rows = pipeline.deep_check(target)
            width = max(len(name) for name, _, _ in rows)
            print(f"{target}")
            for name, passed, detail in rows:
                print(f"  {'PASS' if passed else 'FAIL'}  {name.ljust(width)}  {detail}")
            print("FAILED:\n  " + "\n  ".join(failures(rows)) if failures(rows) else "all checks passed")
            return 1 if failures(rows) else 0
        keep_awake()
        if args.command == "storyboard":
            return storyboard(pipeline, args.stills)
        pipeline.require_valid()
        if args.command == "render-scene":
            for scene_id in args.scene:
                result = pipeline.render_scene(scene_id, still=args.still)
                print(f"{scene_id}: {result.frames} frame(s) in {result.frames_dir}")
            return 0
        if args.command == "render":
            for result in pipeline.render_scenes():
                print(f"{result.id}: {'cached' if result.skipped else 'rendered'} ({result.frames} frames)")
            return 0
        if args.command in ("assemble", "preview", "build"):
            if args.command == "assemble":
                results = pipeline.render_scenes()  # verifies every scene is rendered (cached ones are instant)
                lines = pipeline.narration()
                cues, srt = pipeline.subtitles(lines)
                overlay_frames = pipeline.render_overlay(cues)
                audio = pipeline.mix(lines)
                final = pipeline.assemble(results, audio, srt, overlay_frames)
                checks = pipeline.deep_check(final)
                pipeline.write_manifest(final, results, lines, srt, audio, checks)
                problems = failures(checks)
                if problems:
                    raise PipelineError("final video failed validation:\n  - " + "\n  - ".join(problems))
                print(f"done: {final}")
            else:
                print(f"done: {pipeline.build()}")
            return 0
    except PipelineError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"error: command failed ({exc.returncode}): {' '.join(str(a) for a in exc.cmd[:3])} ...", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
