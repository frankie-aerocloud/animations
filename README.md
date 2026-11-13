# Low-Poly Animation Studio

A code-first, fully local production system for polished vertical (9:16) short-form 3D animations.
Blender builds and renders stylised low-poly scenes from YAML storyboards through its Python API;
FFmpeg assembles the film with transitions, captions, narration, music, effects and subtitles.
Everything is free and open-source software and runs on one machine: no cloud rendering, no SaaS,
no accounts.

The first production is **"What Happens If The World Runs Out Of Water In 24 Hours?"**
(`projects/water-crisis`), a hypothetical scenario told in twelve shots over 80 seconds.

## Toolchain

| Tool | Role | Licence |
|---|---|---|
| Blender 5.2 LTS (Eevee; Cycles optional) | scene construction and rendering via `bpy` | GPL |
| FFmpeg 9 | clip encoding, transitions, overlay composite, audio mix, muxing, validation | LGPL/GPL |
| Python 3.13+ with PyYAML | configuration, pipeline, CLI | PSF / MIT |
| Piper TTS 1.8 (optional) | offline narration | GPL-3 |
| Inter font (bundled with Blender) | captions, HUD and subtitles | SIL OFL 1.1 |

Verified on macOS (Apple Silicon). Blender renders with Metal; Piper runs on CPU.

## Setup

```sh
brew install --cask blender && brew install ffmpeg      # macOS; any platform with these on PATH works
python3 -m venv .venv && .venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m piper.download_voices en_GB-cori-high --download-dir assets/voices   # optional, ~115 MB
.venv/bin/python -m studio.cli doctor
```

`scripts/setup.sh` runs the same steps. Without Piper, put a recorded WAV per narration line in
`projects/<project>/audio/narration/<line id>.wav`.

## Workflow

```sh
python -m studio.cli validate projects/water-crisis                 # project, storyboard, script, assets
python -m studio.cli storyboard projects/water-crisis --stills      # shot list + one still per scene (contact sheet)
python -m studio.cli render-scene projects/water-crisis --scene s01_hook --still 3.5   # look-dev: one frame
python -m studio.cli preview projects/water-crisis                  # complete film at 540x960, 8 samples
python -m studio.cli render-scene projects/water-crisis --scene s02_tap --profile standard
python -m studio.cli render projects/water-crisis --profile standard   # only scenes whose inputs changed
python -m studio.cli assemble projects/water-crisis --profile standard # narration, subtitles, overlay, mix, MP4
python -m studio.cli build projects/water-crisis --profile standard    # everything, then validate + manifest
```

`build` runs: validate configuration → validate assets and audio → build Blender scenes → render
scenes → generate subtitles → render the caption overlay → mix audio → assemble with FFmpeg →
validate the MP4 → write `output/<project>/manifest-<profile>.json`.

Every scene is fingerprinted (storyboard entry, style, render profile and the Blender-side source
files). Re-running `render` or `build` only re-renders scenes whose fingerprint changed; `--force`
rebuilds everything. Interrupted renders resume from the last complete frame.

Outputs live under `output/<project>/`: `scenes/<scene>/<profile>/` (frames, `.blend`, `clip.mp4`),
`overlay/<profile>/frames/`, `audio/` (narration per line, procedural score, effects, final mix),
`subtitles.srt`, the final `<project>-<profile>.mp4`, the manifest, `storyboard.md` and logs.

## Render profiles (`config/render.yaml`)

| Profile | Scale | Samples | Motion blur | Volumetric haze | Ray tracing |
|---|---|---|---|---|---|
| preview | 50 % | 8 | no | no | no |
| standard | 100 % | 32 | yes | yes | yes |
| high | 100 % | 64 | yes | yes | yes |

Output is always 1080x1920 at 30 fps (preview renders at half size), H.264 high profile, yuv420p,
AAC audio, soft `mov_text` subtitles plus a sidecar `.srt`: YouTube Shorts ready.
Set `engine: cycles` in a project's `render:` block to render with Cycles (Metal GPU when available).

## Repository layout

```
config/            render.yaml (profiles, encoding), style.yaml (palette, surfaces, typography), audio.yaml
projects/<id>/     project.yaml, storyboard.yaml, script.yaml, assets/manifest.yaml, audio/{narration,music,sfx}
studio/cli.py      command line interface
studio/pipeline.py orchestration, change detection, Blender invocation, assembly, manifest
studio/core/       project loading + validation, timeline, motion maths, catalogue of names, hashing
studio/blender/    runs inside Blender: scene_builder (entry), environments, camera, lighting, animation
                   events, materials, primitives, rendering, overlay (captions/HUD/subtitles pass)
studio/assets/     procedural library: buildings, characters, vehicles, vegetation, water, terrain, props
studio/audio/      narration (Piper / recorded), subtitles, procedural music and effects, FFmpeg mixer
studio/video/      FFmpeg assembly, technical validation, manifest writer
assets/voices/     Piper voices (downloaded, documented provenance)
references/        reference-short.mp4 (visual reference, not committed)
tests/             pytest suite (fast) plus a Blender smoke test marked `slow`
```

The legacy modules from the first attempt (`studio.py`, `scripts/blender/`,
`studio/blender/story_scenes.py`, `studio/characters/`, `studio/environments/`) are superseded by this
pipeline and are not used by it.

## Authoring a production

A project is three YAML files plus optional audio:

- `project.yaml`: id, title, HUD label, overrides for `render:`, `style:` and `audio:`.
- `storyboard.yaml`: one entry per shot with `environment` (type + parameters), `lighting` preset
  (and `lighting_overrides`), `camera` (shot behaviour and coordinates), `actors` (single or crowds
  with `count`/`area`), `events` (water levels, visibility, movement, spin, flicker, flash, scale,
  depletion, sun), `captions`, `hud` (elapsed-time clock keys), `sfx` cues, `music.intensity` and
  the outgoing `transition`.
- `script.yaml`: narration lines anchored to a scene and an offset; subtitles are generated from them
  and timed against the rendered narration.

Camera behaviours: `aerial_establish`, `push_in`, `tracking`, `orbit`, `side_follow`,
`first_person`, `close_up`, `wide`, `reveal`, `static`, with depth of field (`fstop`, `focus`),
`shake`, `lens_to`, and `whip_in`/`whip_out` for fast location changes that pair with the `whip`
transition. Environments: `coastal_city`, `residential_street`, `kitchen_interior`,
`supermarket_interior`, `distribution_point`, `hospital_exterior`, `farm`, `industrial`,
`reservoir`, `port`, `desert`. Character roles: civilian, shopper, child, nurse, doctor, paramedic,
worker, farmer, police; actions: idle, walk, run, look_around, point, fall, carry, gather, react,
queue, crouch, stand. The full vocabulary is in `studio/core/catalogue.py`, and `validate` rejects
anything outside it.

Coordinates are metres in each environment's world space; every builder in
`studio/blender/environments.py` documents its layout and registers named anchors (`anchor:plaza`)
usable from camera and event specs.

## Assets and licences

Geometry, characters, music and effects are procedural and project-original. External assets
(the Piper voice and the Inter font) are listed in `projects/water-crisis/assets/manifest.yaml`
with source and licence; `assets/voices/README.md` records the voice download and its SHA-256.
Add any third-party asset to the manifest with its exact licence; `validate` fails on entries
without a licence or with a missing file. `earth-textures/` (unverified licence) is unused and
ignored by Git.

## Tests and checks

```sh
.venv/bin/python -m pytest -q -m "not slow"   # configuration, timing, subtitles, audio synthesis, video validation
.venv/bin/python -m pytest -q                 # also the Blender smoke test (renders one small still)
.venv/bin/python -m ruff check studio tests
.venv/bin/python -m mypy
```

Final-video validation checks resolution, frame rate, codecs, pixel format, audio presence,
duration and unexpected black frames; missing scene frames stop the pipeline before assembly.
