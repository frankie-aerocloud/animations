"""Load a project (project, storyboard, script, asset manifest) merged with repository config."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeGuard

from studio.core import catalogue
from studio.core.configuration import (
    CONFIG_DIR,
    PROJECTS_DIR,
    REPO_ROOT,
    RenderProfile,
    deep_merge,
    load_profiles,
    load_yaml,
)
from studio.core.timeline import annotate


@dataclass
class Project:
    root: Path
    id: str
    title: str
    language: str
    render: dict[str, Any]
    style: dict[str, Any]
    audio: dict[str, Any]
    scenes: list[dict[str, Any]]
    lines: list[dict[str, Any]]
    assets: list[dict[str, Any]]
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def fps(self) -> int:
        return int(self.render["fps"])

    @property
    def duration(self) -> float:
        return float(sum(float(scene.get("duration") or 0.0) for scene in self.scenes))

    @property
    def total_frames(self) -> int:
        return int(sum(int(scene.get("frames") or 0) for scene in self.scenes))

    @property
    def profiles(self) -> dict[str, RenderProfile]:
        return load_profiles(self.render)

    def scene(self, scene_id: str) -> dict[str, Any]:
        for scene in self.scenes:
            if scene.get("id") == scene_id:
                return scene
        raise KeyError(f"unknown scene {scene_id!r}")

    def line_start(self, line: dict[str, Any]) -> float:
        scene = self.scene(str(line["scene"]))
        return float(scene["start"]) + float(line.get("at", 0.0) or 0.0)

    def resolve_path(self, value: str) -> Path:
        path = Path(value)
        if path.is_absolute():
            return path
        candidate = self.root / path
        return candidate if candidate.exists() else REPO_ROOT / path


def project_dir(identifier: str | Path) -> Path:
    path = Path(identifier)
    if path.is_file():
        path = path.parent
    if not path.is_absolute() and not path.exists():
        path = PROJECTS_DIR / path
    return path.resolve()


def load_project(identifier: str | Path) -> Project:
    root = project_dir(identifier)
    meta = load_yaml(root / "project.yaml")
    render = deep_merge(load_yaml(CONFIG_DIR / "render.yaml"), meta.get("render") or {})
    style = deep_merge(load_yaml(CONFIG_DIR / "style.yaml"), meta.get("style") or {})
    audio = deep_merge(load_yaml(CONFIG_DIR / "audio.yaml"), meta.get("audio") or {})
    scenes = copy.deepcopy(list(load_yaml(root / "storyboard.yaml").get("scenes") or []))
    script_path = root / "script.yaml"
    lines = copy.deepcopy(list(load_yaml(script_path).get("lines") or [])) if script_path.exists() else []
    manifest_path = root / str(meta.get("assets", "assets/manifest.yaml"))
    assets = list(load_yaml(manifest_path).get("assets") or []) if manifest_path.exists() else []
    fps = render.get("fps", 30)
    if isinstance(fps, int) and fps > 0:
        annotate(scenes, fps)
    return Project(
        root=root,
        id=str(meta.get("id", root.name)),
        title=str(meta.get("title", root.name)),
        language=str(meta.get("language", "en-GB")),
        render=render,
        style=style,
        audio=audio,
        scenes=scenes,
        lines=lines,
        assets=assets,
        meta=meta,
    )


def _positive_int(value: Any) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _number(value: Any) -> TypeGuard[float]:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_project(project: Project) -> list[str]:
    """Return a list of human-readable problems; an empty list means the project is valid."""
    errors: list[str] = []
    render = project.render
    if not _positive_int(render.get("fps")):
        errors.append("render.fps must be a positive integer")
    for key in ("width", "height"):
        value = render.get(key)
        if not (_positive_int(value) and value % 2 == 0):
            errors.append(f"render.{key} must be a positive even integer")
    try:
        load_profiles(render)
    except ValueError as exc:
        errors.append(str(exc))
    if not project.scenes:
        errors.append("storyboard.yaml defines no scenes")
    seen: set[str] = set()
    for scene in project.scenes:
        sid = scene.get("id")
        label = f"scene {sid!r}"
        if not isinstance(sid, str) or not sid:
            errors.append("every scene needs a string id")
            continue
        if sid in seen:
            errors.append(f"duplicate scene id {sid!r}")
        seen.add(sid)
        raw_duration = scene.get("duration")
        duration = float(raw_duration) if _number(raw_duration) and raw_duration > 0 else 0.0
        if duration <= 0:
            errors.append(f"{label}: duration must be a positive number of seconds")
        env = scene.get("environment")
        if not isinstance(env, dict) or env.get("type") not in catalogue.ENVIRONMENTS:
            errors.append(f"{label}: environment.type must be one of {', '.join(catalogue.ENVIRONMENTS)}")
        camera = scene.get("camera")
        if not isinstance(camera, dict) or camera.get("shot") not in catalogue.SHOTS:
            errors.append(f"{label}: camera.shot must be one of {', '.join(catalogue.SHOTS)}")
        lighting = scene.get("lighting", "soft_daylight")
        if lighting not in catalogue.LIGHTING:
            errors.append(f"{label}: lighting must be one of {', '.join(catalogue.LIGHTING)}")
        transition = scene.get("transition") or {}
        if not isinstance(transition, dict):
            errors.append(f"{label}: transition must be a mapping")
        else:
            kind = transition.get("type", "cut")
            if kind not in catalogue.TRANSITIONS:
                errors.append(f"{label}: transition.type must be one of {', '.join(catalogue.TRANSITIONS)}")
            length = transition.get("duration", 0.0)
            if not (_number(length) and length >= 0 and (not duration or length <= duration / 2)):
                errors.append(f"{label}: transition.duration must be between 0 and half the scene duration")
        for actor in scene.get("actors") or []:
            if not isinstance(actor, dict) or not actor.get("id"):
                errors.append(f"{label}: every actor needs an id")
                continue
            kind = actor.get("kind", "person")
            if kind not in catalogue.ACTOR_KINDS:
                errors.append(f"{label}: actor {actor['id']} kind must be one of {', '.join(catalogue.ACTOR_KINDS)}")
            elif kind == "lion":
                if actor.get("action", "walk") not in catalogue.LION_ACTIONS:
                    errors.append(f"{label}: lion {actor['id']} action must be one of {', '.join(catalogue.LION_ACTIONS)}")
            else:
                if actor.get("role", "civilian") not in catalogue.ROLES:
                    errors.append(f"{label}: actor {actor['id']} role must be one of {', '.join(catalogue.ROLES)}")
                for role in actor.get("roles") or []:
                    if role not in catalogue.ROLES:
                        errors.append(f"{label}: actor {actor['id']} roles contains unknown role {role!r}")
                if actor.get("action", "idle") not in catalogue.ACTIONS:
                    errors.append(f"{label}: actor {actor['id']} action must be one of {', '.join(catalogue.ACTIONS)}")
            if actor.get("prop") and actor.get("prop") not in catalogue.PROPS:
                errors.append(f"{label}: actor {actor['id']} prop must be one of {', '.join(catalogue.PROPS)}")
            for time_key in ("start", "end"):
                if time_key in actor and (not _number(actor[time_key]) or actor[time_key] < 0):
                    errors.append(f"{label}: actor {actor['id']} {time_key} must be a non-negative time")
        for event in scene.get("events") or []:
            if not isinstance(event, dict) or event.get("type") not in catalogue.EVENTS:
                errors.append(f"{label}: event type must be one of {', '.join(catalogue.EVENTS)}")
                continue
            start = event.get("start", event.get("at", 0.0))
            end = event.get("end", start)
            if not (_number(start) and _number(end) and 0 <= start <= end <= duration + 1.0):
                errors.append(f"{label}: event {event['type']} must have 0 <= start <= end <= scene duration")
        for caption in scene.get("captions") or []:
            if not isinstance(caption, dict) or not str(caption.get("text", "")).strip():
                errors.append(f"{label}: captions need text")
                continue
            at, until = caption.get("at", 0.0), caption.get("until", duration)
            if not (_number(at) and _number(until) and 0 <= at < until <= duration + 0.5):
                errors.append(f"{label}: caption {caption['text']!r} must have 0 <= at < until <= scene duration")
            if caption.get("kind", "caption") not in catalogue.CARD_KINDS:
                errors.append(f"{label}: caption kind must be one of {', '.join(catalogue.CARD_KINDS)}")
        for cue in scene.get("sfx") or []:
            if not isinstance(cue, dict) or cue.get("sound") not in catalogue.SFX:
                errors.append(f"{label}: sfx sound must be one of {', '.join(catalogue.SFX)}")
            elif not (_number(cue.get("at", 0.0)) and 0 <= float(cue.get("at", 0.0)) <= duration):
                errors.append(f"{label}: sfx {cue['sound']} at must lie inside the scene")
        hud = scene.get("hud")
        if hud is not None and (not isinstance(hud, dict) or not _number(hud.get("hours", 0))):
            errors.append(f"{label}: hud.hours must be a number")
        music = scene.get("music", {})
        if music and (not isinstance(music, dict) or not _number(music.get("intensity", 0.5))):
            errors.append(f"{label}: music.intensity must be a number")
    # narration script
    line_ids: set[str] = set()
    starts: list[tuple[float, str]] = []
    for line in project.lines:
        lid = str(line.get("id", ""))
        if not lid:
            errors.append("every script line needs an id")
            continue
        if lid in line_ids:
            errors.append(f"duplicate script line id {lid!r}")
        line_ids.add(lid)
        if not str(line.get("text", "")).strip():
            errors.append(f"line {lid}: text is empty")
        scene_id = line.get("scene")
        if scene_id not in seen:
            errors.append(f"line {lid}: references unknown scene {scene_id!r}")
            continue
        scene = project.scene(str(scene_id))
        at = line.get("at", 0.0)
        if not (_number(at) and 0 <= at < float(scene.get("duration") or 0.0)):
            errors.append(f"line {lid}: at must lie inside scene {scene_id}")
        else:
            starts.append((float(scene["start"]) + float(at), lid))
        audio_file = line.get("audio")
        if audio_file and not project.resolve_path(str(audio_file)).exists():
            errors.append(f"line {lid}: recorded narration file is missing: {audio_file}")
    starts.sort()
    for (a, lid_a), (b, lid_b) in zip(starts, starts[1:], strict=False):
        if b <= a:
            errors.append(f"lines {lid_a} and {lid_b} start at the same time")
    music_file = project.audio.get("music_file")
    if music_file and not project.resolve_path(str(music_file)).exists():
        errors.append(f"audio.music_file is missing: {music_file}")
    # asset manifest
    for item in project.assets:
        if not isinstance(item, dict):
            errors.append("asset manifest entries must be mappings")
            continue
        ident = item.get("id", "<unknown>")
        for key in ("id", "path", "source", "type"):
            if not item.get(key):
                errors.append(f"asset {ident}: missing {key}")
        if not (item.get("licence") or item.get("license")):
            errors.append(f"asset {ident}: missing licence")
        path = item.get("path")
        if path and not project.resolve_path(str(path)).exists():
            errors.append(f"asset {ident}: file is missing: {path}")
    return errors
