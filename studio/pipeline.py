"""Production pipeline: validate, render scenes (only changed ones), narrate, subtitle, overlay,
assemble with FFmpeg, validate the MP4 and write the manifest."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from studio.audio import mixer, music, narration, sfx, subtitles
from studio.audio.narration import LineAudio
from studio.audio.subtitles import Cue
from studio.core.configuration import OUTPUT_DIR, REPO_ROOT, RenderProfile
from studio.core.hashing import fingerprint, source_files
from studio.core.project import Project, validate_project
from studio.video import assemble, manifest, validate

BLENDER_ENTRY = REPO_ROOT / "studio" / "blender" / "scene_builder.py"
Log = Callable[[str], None]


class PipelineError(RuntimeError):
    """A step failed in a way the user has to act on."""


@dataclass
class SceneResult:
    id: str
    frames_dir: Path
    frames: int
    skipped: bool
    clip: Path | None = None


class Pipeline:
    def __init__(self, project: Project, profile: str = "preview", force: bool = False, log: Log = print) -> None:
        self.project = project
        profiles = project.profiles
        if profile not in profiles:
            raise PipelineError(f"unknown render profile {profile!r}; choose one of {', '.join(profiles)}")
        self.profile: RenderProfile = profiles[profile]
        self.force = force
        self.log = log
        self.out = OUTPUT_DIR / project.id
        self.scenes_dir = self.out / "scenes"
        self.audio_dir = self.out / "audio"
        self.overlay_dir = self.out / "overlay" / self.profile.name
        self.logs = self.out / "logs"
        self.final = self.out / f"{project.id}-{self.profile.name}.mp4"

    # ----- validation -----------------------------------------------------------------
    def validate(self) -> list[str]:
        return validate_project(self.project)

    def require_valid(self) -> None:
        errors = self.validate()
        if errors:
            raise PipelineError("project configuration is invalid:\n  - " + "\n  - ".join(errors))

    # ----- Blender --------------------------------------------------------------------
    def _blender(self, spec: dict[str, Any], name: str) -> Path:
        blender = shutil.which("blender")
        if not blender:
            raise PipelineError("Blender is not on PATH (macOS: brew install --cask blender)")
        self.logs.mkdir(parents=True, exist_ok=True)
        spec_path = self.logs / f"{name}.json"
        spec_path.write_text(json.dumps(spec, indent=1, default=str), encoding="utf-8")
        log_path = self.logs / f"{name}.log"
        cmd = [blender, "-b", "--factory-startup", "--python-exit-code", "1", "--python", str(BLENDER_ENTRY), "--", str(spec_path)]
        with log_path.open("w", encoding="utf-8") as handle:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            assert process.stdout is not None
            for line in process.stdout:
                handle.write(line)
                if line.startswith("[studio]") or "Error" in line or "Traceback" in line:
                    self.log(f"  {line.rstrip()}")
            code = process.wait()
        if code != 0:
            tail = "".join(log_path.read_text(encoding="utf-8").splitlines(keepends=True)[-25:])
            raise PipelineError(f"Blender failed for {name} (exit {code}); full log: {log_path}\n{tail}")
        return log_path

    def _blender_sources(self) -> list[Path]:
        return source_files(REPO_ROOT / "studio" / "blender", REPO_ROOT / "studio" / "assets", REPO_ROOT / "studio" / "core")

    def scene_dir(self, scene_id: str) -> Path:
        return self.scenes_dir / scene_id / self.profile.name

    def scene_spec(self, scene: dict[str, Any], still: int | None = None) -> dict[str, Any]:
        scene_dir = self.scene_dir(str(scene["id"]))
        frames_dir = scene_dir / ("stills" if still is not None else "frames")
        return {
            "mode": "scene",
            "repo_root": str(REPO_ROOT),
            "font": str(self.project.style.get("font", "Inter.woff2")),
            "project": {"id": self.project.id, "title": self.project.title},
            "render": {key: self.project.render.get(key) for key in ("width", "height", "fps", "engine")},
            "profile": self.profile.as_dict(),
            "style": self.project.style,
            "scene": scene,
            "output": {"dir": str(scene_dir), "frames_dir": str(frames_dir)},
            "still": still,
            "save_blend": bool(self.project.render.get("save_blend", True)),
        }

    def scene_hash(self, scene: dict[str, Any]) -> str:
        spec = self.scene_spec(scene)
        return fingerprint({key: spec[key] for key in ("render", "profile", "style", "scene", "font")}, self._blender_sources())

    def render_scene(self, scene_id: str, still: float | None = None) -> SceneResult:
        scene = self.project.scene(scene_id)
        scene_dir = self.scene_dir(scene_id)
        total = int(scene["frames"]) + int(scene["handle_frames"])
        digest = self.scene_hash(scene)
        hash_file = scene_dir / "scene.hash"
        frames_dir = scene_dir / "frames"
        if still is not None:
            frame = max(1, min(total, 1 + round(still * self.project.fps)))
            spec = self.scene_spec(scene, still=frame)
            self.log(f"[scene] {scene_id}: still at {still:.2f}s (frame {frame})")
            self._blender(spec, f"{scene_id}-{self.profile.name}-still")
            return SceneResult(scene_id, scene_dir / "stills", 1, False)
        unchanged = hash_file.exists() and hash_file.read_text(encoding="utf-8").strip() == digest
        if unchanged and not self.force and validate.frames_complete(frames_dir, total):
            self.log(f"[scene] {scene_id}: unchanged, {total} frames already rendered")
            return SceneResult(scene_id, frames_dir, total, True)
        if frames_dir.exists() and (self.force or not unchanged):
            shutil.rmtree(frames_dir)
            (scene_dir / "clip.mp4").unlink(missing_ok=True)
        elif frames_dir.exists():
            validate.remove_partial_frames(frames_dir)
        scene_dir.mkdir(parents=True, exist_ok=True)
        # Written before rendering: the frames in this folder belong to this fingerprint, so an
        # interrupted render resumes from its last complete frame instead of starting over.
        hash_file.write_text(digest, encoding="utf-8")
        done = len(list(frames_dir.glob("frame_*.png"))) if frames_dir.exists() else 0
        self.log(f"[scene] {scene_id}: rendering {total - done} of {total} frames ({self.profile.name})")
        self._blender(self.scene_spec(scene), f"{scene_id}-{self.profile.name}")
        missing = validate.missing_frames(frames_dir, total)
        if missing:
            raise PipelineError(f"scene {scene_id}: {len(missing)} frames missing after render (first: {missing[0]})")
        return SceneResult(scene_id, frames_dir, total, False)

    def render_scenes(self, scene_ids: list[str] | None = None) -> list[SceneResult]:
        ids = scene_ids or [str(scene["id"]) for scene in self.project.scenes]
        return [self.render_scene(scene_id) for scene_id in ids]

    # ----- audio ----------------------------------------------------------------------
    def narration(self) -> list[LineAudio]:
        lines = narration.synthesise(self.project, self.audio_dir / "narration", self.log)
        problems = narration.check_fit(lines, self.project.duration)
        if problems:
            raise PipelineError("narration does not fit the storyboard:\n  - " + "\n  - ".join(problems))
        return lines

    def subtitles(self, lines: list[LineAudio]) -> tuple[list[Cue], Path]:
        max_chars = int(self.project.style.get("overlay", {}).get("subtitle", {}).get("max_chars", 44))
        cues = subtitles.make_cues(lines, max_chars=max_chars)
        problems = subtitles.validate_cues(cues, self.project.duration)
        if problems:
            raise PipelineError("subtitle timing is invalid:\n  - " + "\n  - ".join(problems))
        return cues, subtitles.write_srt(cues, self.out / "subtitles.srt")

    def music(self) -> Path:
        configured = self.project.audio.get("music_file")
        if configured:
            return self.project.resolve_path(str(configured))
        path = self.audio_dir / "music.wav"
        digest = fingerprint([{"duration": s.get("duration"), "music": s.get("music")} for s in self.project.scenes] + [{"style": self.project.meta.get("music_style", "tense")}], [REPO_ROOT / "studio" / "audio" / "music.py"])
        stamp = self.audio_dir / "music.hash"
        if not (path.exists() and stamp.exists() and stamp.read_text(encoding="utf-8") == digest):
            self.log("[music] rendering procedural score")
            music.render_score(self.project.scenes, path, style=str(self.project.meta.get("music_style", "tense")))
            stamp.write_text(digest, encoding="utf-8")
        return path

    def sfx_cues(self) -> list[mixer.SfxCue]:
        recorded_dir = self.project.root / str(self.project.audio.get("sfx_dir", "audio/sfx"))
        cues: list[mixer.SfxCue] = []
        for scene in self.project.scenes:
            for cue in scene.get("sfx") or []:
                name = str(cue["sound"])
                recorded = recorded_dir / f"{name}.wav"
                path = recorded if recorded.exists() else sfx.render(name, self.audio_dir / "sfx" / f"{name}.wav")
                cues.append(mixer.SfxCue(path, float(scene["start"]) + float(cue.get("at", 0.0)), float(cue.get("gain_db", 0.0))))
        return cues

    def mix(self, lines: list[LineAudio]) -> Path:
        self.log("[audio] mixing narration, music and effects")
        return mixer.mix(lines, self.music(), self.sfx_cues(), self.project.audio, self.project.duration, self.audio_dir / "mix.wav")

    # ----- overlay --------------------------------------------------------------------
    def overlay_spec(self, cues: list[Cue]) -> dict[str, Any]:
        cards: list[dict[str, Any]] = []
        keys: list[list[float]] = []
        visible: list[list[float]] = []
        subs: list[dict[str, Any]] = []
        scenes = self.project.scenes
        for i, scene in enumerate(scenes):
            start = float(scene["start"])
            duration = float(scene["duration"])
            end = start + duration
            for caption in scene.get("captions") or []:
                cards.append({"kind": caption.get("kind", "caption"), "text": str(caption["text"]), "sub": caption.get("sub"), "start": start + float(caption.get("at", 0.0)), "end": start + float(caption.get("until", duration)), "y": caption.get("y")})
            hud = scene.get("hud")
            if hud:
                show = start + float(hud.get("show_at", 0.0))
                hours = float(hud.get("hours", 0.0))
                next_hud = scenes[i + 1].get("hud") if i + 1 < len(scenes) else None
                hours_end = float(hud.get("hours_end", next_hud.get("hours", hours) if next_hud else hours))
                keys += [[show, hours], [end, hours_end]]
                if visible and abs(visible[-1][1] - show) < 1e-6:
                    visible[-1][1] = end
                else:
                    visible.append([show, end])
                if hud.get("sub"):
                    subs.append({"text": str(hud["sub"]), "start": show, "end": end})
        cards = [{**card, "y": card["y"]} if card["y"] is not None else {k: v for k, v in card.items() if k != "y"} for card in cards]
        return {
            "mode": "overlay",
            "repo_root": str(REPO_ROOT),
            "font": str(self.project.style.get("font", "Inter.woff2")),
            "render": {key: self.project.render.get(key) for key in ("width", "height", "fps", "engine")},
            "profile": self.profile.as_dict(),
            "style": self.project.style,
            "fps": self.project.fps,
            "total_frames": self.project.total_frames,
            "cards": cards,
            "hud": {"label": str(self.project.meta.get("hud_label", "ELAPSED")), "keys": keys, "visible": visible, "subs": subs, "wrap": int(self.project.meta.get("hud_wrap") or 0)},
            "subtitles": [{"start": cue.start, "end": cue.end, "text": cue.text} for cue in cues],
            "output": {"dir": str(self.overlay_dir), "frames_dir": str(self.overlay_dir / "frames")},
        }

    def render_overlay(self, cues: list[Cue]) -> Path:
        spec = self.overlay_spec(cues)
        frames_dir = self.overlay_dir / "frames"
        digest = fingerprint({key: spec[key] for key in ("render", "profile", "style", "cards", "hud", "subtitles", "total_frames", "font")}, [REPO_ROOT / "studio" / "blender" / "overlay.py", REPO_ROOT / "studio" / "blender" / "primitives.py"])
        hash_file = self.overlay_dir / "overlay.hash"
        total = self.project.total_frames
        unchanged = hash_file.exists() and hash_file.read_text(encoding="utf-8").strip() == digest
        if unchanged and not self.force and validate.frames_complete(frames_dir, total):
            self.log(f"[overlay] unchanged, {total} frames already rendered")
            return frames_dir
        if frames_dir.exists() and (self.force or not unchanged):
            shutil.rmtree(frames_dir)
        elif frames_dir.exists():
            validate.remove_partial_frames(frames_dir)
        self.overlay_dir.mkdir(parents=True, exist_ok=True)
        hash_file.write_text(digest, encoding="utf-8")
        self.log(f"[overlay] rendering {total} caption/subtitle frames")
        self._blender(spec, f"overlay-{self.profile.name}")
        missing = validate.missing_frames(frames_dir, total)
        if missing:
            raise PipelineError(f"overlay pass left {len(missing)} frames missing")
        return frames_dir

    # ----- assembly -------------------------------------------------------------------
    def clips(self, results: list[SceneResult]) -> list[Path]:
        clips: list[Path] = []
        for result in results:
            scene_dir = self.scene_dir(result.id)
            clip = scene_dir / "clip.mp4"
            stamp = scene_dir / "clip.hash"
            digest = (scene_dir / "scene.hash").read_text(encoding="utf-8").strip() if (scene_dir / "scene.hash").exists() else ""
            if not (clip.exists() and stamp.exists() and stamp.read_text(encoding="utf-8") == digest):
                self.log(f"[clip] encoding {result.id}")
                assemble.encode_clip(result.frames_dir, self.project.fps, result.frames, clip)
                stamp.write_text(digest, encoding="utf-8")
            result.clip = clip
            clips.append(clip)
        return clips

    def assemble(self, results: list[SceneResult], audio: Path | None, srt: Path | None, overlay_frames: Path | None) -> Path:
        clips = self.clips(results)
        self.log(f"[assemble] {len(clips)} clips -> {self.final.name}")
        return assemble.assemble(clips, self.project.scenes, overlay_frames, audio, srt, self.final, self.project.fps, self.project.duration, dict(self.project.render.get("encode") or {}))

    def allowed_black(self) -> list[tuple[float, float]]:
        windows: list[tuple[float, float]] = []
        for scene in self.project.scenes:
            transition = scene.get("transition") or {}
            if transition.get("type") == "fade_black":
                end = float(scene["start"]) + float(scene["duration"])
                windows.append((end - 0.1, end + float(transition.get("duration", 0.0)) + 0.1))
        return windows

    def expected_size(self) -> tuple[int, int]:
        """Output size for this profile: the project resolution scaled, kept even for yuv420p."""
        render = self.project.render
        return tuple(max(2, int(round(int(render[key]) * self.profile.scale)) // 2 * 2) for key in ("width", "height"))  # type: ignore[return-value]

    def validate_output(self, path: Path) -> list[str]:
        width, height = self.expected_size()
        problems = validate.validate_output(path, width, height, self.project.fps, self.project.duration)
        if not problems:
            black = validate.unexpected_black(path, self.allowed_black())
            problems += [f"unexpected black frames at {start:.2f}-{end:.2f}s" for start, end in black]
        return problems

    def write_manifest(self, final: Path, results: list[SceneResult], lines: list[LineAudio], srt: Path, audio: Path, problems: list[str]) -> Path:
        info = validate.probe(final)
        video: dict[str, Any] = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), {})
        data = {
            "project": {"id": self.project.id, "title": self.project.title, "language": self.project.language},
            "output": {"path": str(final), "size_bytes": final.stat().st_size, "duration_seconds": float(info.get("format", {}).get("duration", 0.0)), "width": video.get("width"), "height": video.get("height"), "frame_rate": video.get("r_frame_rate"), "video_codec": video.get("codec_name"), "pixel_format": video.get("pix_fmt")},
            "validation": {"passed": not problems, "problems": problems},
            "tools": {"blender": manifest.tool_version("blender", "--version"), "ffmpeg": manifest.tool_version("ffmpeg"), "piper-tts": manifest.package_version("piper-tts"), "python": sys.version.split()[0]},
            "render": {"profile": self.profile.as_dict(), "engine": self.project.render.get("engine"), "encode": self.project.render.get("encode")},
            "scenes": [{"id": s["id"], "start": s["start"], "duration": s["duration"], "frames": s["frames"], "environment": s["environment"].get("type"), "shot": s["camera"].get("shot"), "lighting": s.get("lighting", "soft_daylight"), "transition": (s.get("transition") or {}).get("type", "cut"), "rendered": not next(r.skipped for r in results if r.id == s["id"])} for s in self.project.scenes],
            "assets": [{"id": a.get("id"), "type": a.get("type"), "path": a.get("path"), "source": a.get("source"), "licence": a.get("licence") or a.get("license")} for a in self.project.assets],
            "audio": {"mix": str(audio), "narration": [{"id": line.id, "start": line.start, "duration": round(line.duration, 3), "path": str(line.path)} for line in lines], "music": str(self.music()), "sfx": [str(c.path) for c in self.sfx_cues()], "voice": (self.project.audio.get("narration") or {}).get("voice")},
            "subtitles": str(srt),
        }
        return manifest.write_manifest(self.out / f"manifest-{self.profile.name}.json", data)

    # ----- whole build ----------------------------------------------------------------
    def build(self, scene_ids: list[str] | None = None) -> Path:
        self.require_valid()
        lines = self.narration()
        cues, srt = self.subtitles(lines)
        results = self.render_scenes(scene_ids)
        overlay_frames = self.render_overlay(cues)
        audio = self.mix(lines)
        final = self.assemble(results, audio, srt, overlay_frames)
        problems = self.validate_output(final)
        manifest_path = self.write_manifest(final, results, lines, srt, audio, problems)
        self.log(f"[manifest] {manifest_path}")
        if problems:
            raise PipelineError("final video failed validation:\n  - " + "\n  - ".join(problems))
        self.log(f"[done] {final}")
        return final
