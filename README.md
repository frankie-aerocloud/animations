# Local Blender Animation Studio

Code-first production tooling for documentary-style vertical animations. Blender generates the 3D scenes and image sequences; FFmpeg encodes the final MP4. The pipeline is designed to work locally and keeps scene timings deterministic.

## Current production stage

The first production is **What If The World Ran Out Of Water? — The First 24 Hours**. The seven scene builders and 90-second script are implemented. The opening Earth uses the local equirectangular diffuse, glossiness, normal, illumination and cloud maps in `earth-textures/`; the maps are packed into the opening Blender file so that render can reopen without external texture paths. The project also uses the local star and blue-haze maps for its space background. Earth texture provenance and licensing were not included with those files, so their original terms need checking before publication. The updated Blender render still needs to be run and reviewed locally before calling the film final.

The kitchen QC shot is 300 frames at 30 fps. The full scene timeline is frame-based (90 seconds = 2,700 frames). Rendered frames are kept as PNGs so an interrupted run can skip frames that already completed.

## Local setup

This repository uses Python 3.14 in `.venv` for the CLI and development utilities:

```sh
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

Install the non-Python production tools separately. On macOS with Homebrew:

```sh
brew install --cask blender
brew install ffmpeg
```

`ffmpeg` installs `ffprobe` as well. Check the local toolchain with `python studio.py doctor`.

The project `.venv` uses Python 3.14.8. The required Python dependencies and the Blender/FFmpeg system tools have since been installed. They are setup dependencies, not runtime web-service dependencies.

## Run the quality-control animation

```sh
source .venv/bin/activate
python studio.py doctor
python studio.py quality-test --profile preview
```

This builds `output/world-runs-out-of-water/quality-test/kitchen-qc.blend`, renders PNGs into `frames/`, and encodes `kitchen-qc.mp4`. `preview` renders 540×960 frames; `standard` and `high` use 1080×1920. Each quality-test rebuild starts a fresh frame sequence. To resume an interrupted render without rebuilding, run `python studio.py render world-runs-out-of-water --profile preview`.

Render the complete seven-scene short with:

```sh
python studio.py render-film world-runs-out-of-water --profile preview
```

Use `--force` to rebuild all seven scenes after changing their builders. The production render writes per-scene Blender files and resumable PNG sequences under `output/world-runs-out-of-water/scenes/`, then uses FFmpeg to join them with short dissolves, create the local sound bed, add available macOS `say` narration, mux subtitles, and validate the final MP4 with FFprobe. If system speech returns no audio, the export still contains subtitles and the generated ambience bed; a user-supplied WAV can be added under the configured narration assets path.

Useful commands:

```sh
python studio.py validate world-runs-out-of-water
python studio.py build world-runs-out-of-water
python studio.py render world-runs-out-of-water --profile standard
python studio.py export output/world-runs-out-of-water/quality-test --fps 30
python studio.py init my-new-video
python studio.py clean world-runs-out-of-water
```

`build` and `render` currently apply to the kitchen QC shot. The seven-scene YAML is the approved timing/script input for subsequent scene development, not a claim that all seven animations are already built.

## Architecture

- `studio/core/project.py` loads and validates project YAML.
- `studio/core/timeline.py` maps durations to contiguous, inclusive frame ranges.
- `studio/characters/` imports the CC0 Quaternius humanoid bases, creates fitted role clothing and accessories, adapts the full humanoid skeleton, and authors reusable motions and facial cues.
- `studio/environments/kitchen.py` builds the QC environment and props from Blender geometry.
- `studio/blender/scene_builder.py` assembles camera, lighting, character, animation and version-aware Eevee settings.
- `studio/blender/story_scenes.py` contains reusable builders for Earth, kitchen, supermarket, hospital, city infrastructure, farm and final city shots.
- `scripts/blender/` contains standalone Blender background entry points.
- `studio.py` orchestrates environment checks, resumable scene rendering, crossfades, audio, subtitles, and FFmpeg/FFprobe export.
- `projects/*/assets.yaml` records asset provenance and licences. Current QC assets are original generated geometry; nothing is downloaded.

Scene animation is authored in Blender keyframes. Rendering evaluates explicit frame numbers, not wall-clock timers. Frame files are the resumability boundary. Blender uses the Eevee engine identifier exposed by its installed version, and falls back to CPU Cycles if Eevee is unavailable.

The character system uses local CC0 Quaternius male and female humanoid bases with finished facial topology, eyes, hairstyles and full fingered skeletons. The generator adds project-original fitted clothing for each role, subtle skin and hair variation, blink and brow controls, and reusable idle, walk, reach, point and carry actions. Source and licence details are recorded beside the extracted asset and in the project asset manifest.

## Add scenes

1. Add a scene module under `projects/world-runs-out-of-water/scenes/` or a reusable environment under `studio/environments/`.
2. Expose a builder that creates the props, camera, lighting and keyframes in a supplied Blender scene.
3. Keep action timings in frames derived from project FPS; do not use independent timers.
4. Add the scene id, duration, narration and environment to `project.yaml`. Scene starts derive from preceding durations.
5. Register external assets in `assets.yaml` with source, local path, exact licence and attribution requirements. Never use assets with unclear terms.
6. Add tests for frame ranges and asset paths, then render the scene preview before the full sequence.

## Characters and asset licensing

Add reusable character styles to `studio/characters/registry.py`; build or import them through a stable function in `generator.py`. Animate bones/actions using named rig controls. For a third-party model, retain its source, licence text, attribution, and required modifications in the asset manifest. No third-party assets are bundled.

## Audio and export

The pipeline can use a local WAV narration or macOS's built-in Daniel voice through `say`; no hosted TTS endpoint is called. It creates a small deterministic ambient underscore using the Python standard library and FFmpeg encodes audio as AAC. SRT subtitles are also muxed into the MP4. A Piper voice model can be added by extending the local narration adapter and recording its licence in the assets manifest.

## Tests and quality checks

```sh
python -m unittest discover -s tests -v
python -m pytest
python -m ruff check studio.py studio tests
python -m mypy studio
```

Automated timeline/config tests are included. Blender render tests cannot run until Blender is installed. Inspect rendered frames for composition, proportions, lighting and interaction before advancing beyond the QC gate.
