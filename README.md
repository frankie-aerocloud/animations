# Low-Poly Animation Studio

A code-first, fully local production system for polished vertical (9:16) short-form 3D animations.
Blender builds and renders stylised low-poly scenes from YAML storyboards through its Python API;
FFmpeg assembles the film with transitions, captions, narration, music, effects and subtitles.
Everything is free and open-source software and runs on one machine: no cloud rendering, no SaaS,
no accounts.

Seven productions ship with the repository:

- **"What Happens If The World Runs Out Of Water In 24 Hours?"** (`projects/water-crisis`): a
  hypothetical scenario told hour by hour (1, 2, 4, 8, 12, 15, 20, 24) in eighteen shots over
  118 seconds, from the first dry tap to a city-wide blackout, night fires and a dawn aerial that
  ends on "What would you do?".
- **"What If One Million Seagulls Attacked New York?"** (`projects/seagulls-nyc`): a dark-comedy
  disaster mockumentary in twenty-one shots over 168 seconds, from a dawn sighting off Brooklyn to
  the Statue of Liberty under birds, a Times Square stampede, grounded airliners, the National Guard,
  a night roost on the bridge and a dawn ending on "What happens when they start breeding?".
- **"What If One Million Lions Attacked Las Vegas?"** (`projects/vegas-lions`): a cinematic disaster
  mockumentary in twenty-four shots over 163 seconds under a running 24-hour countdown, from a quiet
  Mojave sunrise to hordes crossing the desert, lions on the Strip, emergency alerts, a military
  perimeter, a district-by-district blackout and an army of eyes in the dark, ending at dawn on a
  rooftop roar and "What happens when they get hungry again?".
- **"365 Days Underwater: The London Disaster"** (`projects/london-rain`): a slow-burn hypothetical in
  thirty-one shots over 177 seconds, counting the days as it rains on London for a year. The city is
  never drowned: recognisable London (red buses and phone boxes, terraces, the Underground,
  Westminster, the Thames Barrier) slowly becomes unliveable, from flooded underpasses and basements
  to black mould, a sparking substation and evacuation zones, until the clouds break over
  Westminster and the film ends on "Could London ever be the same again?".
- **"When The Wind Took Everything"** (`projects/la-wind`): a 300 mph wind tears through Los Angeles
  for 24 hours in thirty-eight shots over 165 seconds, under a time-of-day clock. Sunny palm-lined
  boulevards give way to flying debris, bursting towers, thrown cars, a battered pier, downed power
  lines and wind-driven fires, cut against the people sheltering inside, until the wind stops at
  sunrise on a devastated city.
- **"The Day The World Stopped Making Plastic"** (`projects/plastic-pause`): every plastics plant on
  Earth stops for 24 hours, in fifty-seven shots over 175 seconds. Production lines halt and the
  halls fall silent; volunteers clear beaches, an Indonesian waterway, an Indian storm drain and
  British rivers; industry and households rethink packaging; the ocean's plastic is still there at
  night; and production restarts at sunrise, changed.
- **"The Month America Ditched McDonald's"** (`projects/burger-boycott`): a hypothetical 30-day
  economic experiment under a day counter, in fifty-four shots over 179 seconds. Drive-throughs
  empty, franchise owners cut hours and count the days, suppliers redirect produce, rival chains
  and independent diners fill up, families cook at home, and when the boycott ends the queues
  return, but not all of them; it closes on whether America got healthier or just switched
  chains. The chains on screen are generic colour schemes and plain words, never real logos.

All seven are built from the same pipeline; only the YAML files and the environments they call differ.

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
python -m studio.cli check projects/water-crisis --profile standard    # re-run every check on the finished MP4
```

The final check decodes every video frame and audio sample, as a player does, and verifies
resolution, frame rate, codecs, duration, matching audio and video lengths, black or frozen picture,
strobing (more than three general flashes in any second, the photosensitivity limit in WCAG 2.3.1),
loudness (EBU R128 against `audio.master.target_lufs`) and true peak, audio dropouts, the embedded
subtitle track, that the file streams before it finishes downloading (`moov` before `mdat`), and
YouTube Shorts limits (9:16, at most 180 s). `build` runs it and records each result in the manifest.

`build` runs: validate configuration → validate assets and audio → build Blender scenes → render
scenes → generate subtitles → render the caption overlay → mix audio → assemble with FFmpeg →
validate the MP4 → write `output/<project>/manifest-<profile>.json`.

Every scene is fingerprinted from its storyboard entry, style and render profile, and records the
code files it actually imported (`deps.json`, with content hashes). Re-running `render` or `build`
only re-renders a scene when its fingerprint changed or one of its own code files changed, so adding a
new production's environments never invalidates another film. Each environment family is a separate
module (`studio/core/catalogue.py` maps environment types to modules) and is imported only by the
scenes that use it. `--force` rebuilds everything; `adopt` marks existing frames as current after a
code change you know does not affect that film. Interrupted renders resume from the last complete frame, so a long film can be
rendered in several sittings: run `render` as often as needed, then `assemble`. A frame cut
short mid-write (no PNG end marker) is detected and redrawn. On macOS the CLI holds a
`caffeinate -s` assertion while it runs, so idle or maintenance sleep does not pause Blender on
mains power; on battery the Mac sleeps normally and the render continues when it wakes.

`project.yaml` also accepts `hud_label` (clock caption), `hud_wrap: 24` (a time-of-day clock that
rolls over at midnight; omit it for an elapsed-time clock), `hud_format: hms` (hours, minutes and
seconds; `day` shows a day counter, DAY 14, with day numbers as the hud values; the default is
hours and minutes) and `music_style` (`tense`, `quirky`, `epic` for a string ostinato, brass
swells and timpani, or `hopeful` for a major-key piano arpeggio over a warm chord pad). A scene's `music.rain` and `music.wind` (0 to 1) add a rain bed or a howling
wind bed to the score that crossfade at each cut, `music.mute` silences the score for a scene, and
`audio.narration.length_scale` speeds the voice up (below 1) or slows it down. Piper varies each
line's length slightly between runs; `audio.narration.noise_w: 0` fixes it, so a storyboard timed
against measured lines still fits after the narration cache is cleared.

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
  depletion, sun), `captions`, `hud` (elapsed-time clock keys), `sfx` cues, `music` (`intensity`
  and an optional `rain` level) and the outgoing `transition` (`cut`, the default, joins the
  shots frame-accurately with no blend; the others blend over their `duration`). Keep `flicker`
  events to a `rate` of about 2.5 or less with modest `strength`: faster, brighter flicker strobes
  and fails the check.
- `script.yaml`: narration lines anchored to a scene and an offset; subtitles are generated from them
  and timed against the rendered narration.

Camera behaviours: `aerial_establish`, `push_in`, `tracking`, `orbit`, `side_follow`,
`first_person`, `close_up`, `wide`, `reveal`, `static`, with depth of field (`fstop`, `focus`),
`shake`, `lens_to`, and `whip_in`/`whip_out` for fast location changes that pair with the `whip`
transition. The near clip grows with the camera's height and its distance from the subject (1% of
the smaller, at least 5 cm), so roads and yards a few centimetres above the ground do not z-fight
(flash in and out) in aerial shots.
Environments: `coastal_city` (variants `normal`, `crisis`, `fire`, `night`,
`night_fires`, `dawn`, plus flags `dry`, `night`, `emergency`, `fires`, `smoke`, `helicopters`,
`jam`), `residential_street`, `kitchen_interior`, `supermarket_interior`, `distribution_point`,
`hospital_exterior` (`crisis`), `farm` (`health`, `dry`), `industrial`, `reservoir`, `port`
(`night`), `desert`, `highway` (`jam`, `night`), and the New York set in
`studio/blender/environments_nyc.py`: `harbour_dawn` (`swarms`, `flocks`, `swarm_near`),
`metropolis` (`focus`, `night`, `birds` 0-3, `splats` 0-1, `jam`, `guard`, `closed`, `rubbish`,
`nests`, `roost`, `helicopters`) and `airport` (`birds`, `splats`). The bird library
(`studio/assets/birds.py`) provides rigged flapping flocks, merged distant swarms, perched roosts,
nests, droppings and dives; `studio/assets/landmarks.py` provides the statue, spire and tapered
towers, the suspension bridge, billboards, food carts, cafe tables, bins, rubbish, airliners,
drones, army trucks, loudspeaker vans and police cars. The Las Vegas set is in
`studio/blender/environments_vegas.py`: `mojave` (`truck`, `dust`, `hordes`, `horde_size`,
`horde_radius`, `ridge`, `skyline`), `vegas_strip` (`focus`, `night`, `dusk`, `lions` 0-3,
`lion_action`, `cars`, `car_count`, `abandoned`, `barricades`, `guard`, `perimeter`, `helicopters`,
`heli_path`, `rooftops`, `valley_hordes`, `districts`, `districts_dark`, `eyes`, `eye_count`,
`eye_size`, `eye_strength`, `fountains`, `closed`, `marquee`), `casino_floor`, `desert_airport`
(`lions`) and `desert_suburb` (the residential street's flags). The lion library
(`studio/assets/lions.py`) provides rigged lions (actors with `kind: lion` and actions walk, prowl,
run, idle, roar, lie), merged hordes with dust plumes and eye-shine, resting prides and fields of
eyes. The London set is in `studio/blender/environments_london.py`: `london_street` (`kind`
high_street, residential or mixed; `night`, `rain`, `rain_at`, `puddles`, `flood`, `lightwells`,
`drains`, `buses`, `bus_at`, `diverted`, `traffic`, `traffic_lane`, `walkers`, `sandbags`, `pumps`,
`shutters`, `boarded`, `to_let`, `damp`, `tape`, `evacuation`, `road_closed`, `scaffolding`,
`sinkhole`, `debris`, `viaduct` with a train and a flooding underpass, `station`), `london_park`,
`london_aerial` and `westminster` (the Thames, Westminster, the Eye, St Paul's and the Shard; `night`,
`clouds`, `cloud_base`, `cloud_hole`, `part` for the clouds breaking, `system` for the weather system
seen from above, `dark_districts`, `cranes`, `flood_pools`), `thames` (`outfall`, `barrier`),
`london_interior` (`mould`, `buckets`, `child`, `adult`), `sports_hall`, `london_works` (a stalled
building site, or `kind: substation`) and `london_hospital`. `studio/assets/london.py` holds the
terraces, shops, buses, cabs, phone and pillar boxes, the landmarks and the flood props;
`studio/assets/weather.py` the looping rain, puddles, cloud decks, rain shafts and the cyclone; and
`studio/assets/meshes.py` builds very large merged meshes in linear time. The Los Angeles set is in
`studio/blender/environments_la.py`: `la_street` (`kind` boulevard or residential; `wind`, `gust_at`,
`wind_at` (the camera's x, y: flying debris, dust and embers keep clear of that line, as anything
crossing the lens fills the frame for a frame), `uproot`, `thrown`, `roofs`, `ripped`, `burst_at`, `poles_down`, `lights_torn`,
`collapse`, `fires`, `night`, `blackout`, `aftermath`, `crews`, `people`), `la_downtown` (`shatter`,
`broken`), `la_freeway` (`thrown`, `truck_over`, `helicopter`), `la_hills`, `la_airport` (`slew`),
`la_pier` (`waves`, `wheel_spin`), `la_interior` (`kind` living, office, garage, hallway, apartment
or hospital; `shatter_at`, `door_open`) and `la_aerial`. `studio/assets/la.py` holds palms that bend
and uproot, strip malls, houses whose roofs tear away, power lines, freeway pieces, towers, the pier
and the airport arches; `studio/assets/wind.py` the debris storms, dust streaks, window bursts,
thrown objects, surf, embers and smoke. The plastic film's set is in
`studio/blender/environments_plastic.py`: `plastic_plant` (`district`, `night`, `lit`, `stop_at`,
`stopped`, `restart_at`, `lights_off`, `birds`), `plastic_factory` (`kind` bottles, packaging, film,
bags, products, recycling, refill, store or control; `stop_at`, `stopped`, `restart_at`,
`lights_off`, `lights_on`, `lamps`, `people`, `gathered`, `maintenance`, `dust`, `alert_at`),
`clean_up` (`kind` uk_beach, sand_beach, river, street or square; `litter`, `cleared`,
`volunteers`, `area`, `piles`, `van`, `crew_at`, `chain`, `turtles`, `placards`, `screen`),
`waterway`, `drain`, `ocean` (`kind` surface or underwater) and `plastic_interior` (`kind`
supermarket, refill, restaurant, lab, hospital_store, press, council, studio or kitchen).
`studio/assets/plastic.py` holds production lines whose belts, rolls and presses run, halt and
restart, litter on land and water, sacks and bales, beach huts, stilt houses, wooden boats, a river
boom, a sea turtle and fish. The fast-food film's set is in `studio/blender/environments_fastfood.py`:
`burger_strip` (per-chain `queue`, `parked` and `walkers`; `traffic`, `passers`, `night`, `lit`,
`giant_dim`, `lights_on_at`, `promo`, `billboards`, `celebrate`, `staff_outside`),
`burger_interior` (`kind` giant, rival, office, kitchen, dock, diner or cafe; `customers`, `staff`,
`wiping`, `table_trays`, `counter_trays`, `counter_nuggets`, `running`, `crossed`, `struck`,
`chart`), `food_home` (`kind` kitchen, dinner, backyard or fridge), `food_supply` (`kind`
warehouse, yard or farm; `leaving`), `tv_studio`, `main_street` (`busy`, `walkers`, `queue`) and
`town_aerial`. `studio/assets/fastfood.py` holds the generic restaurants with drive-through lanes
and menu boards, food and kitchen kit, pallets, produce, balloons, billboards and a franchise
office's paperwork. Character roles: civilian, shopper, child,
nurse, doctor, paramedic, worker, farmer, police, soldier, fisherman; actions: idle, walk, run,
look_around, point, fall, carry, gather, react, queue, crouch, stand, scatter. Events include water levels, visibility,
movement, spin, flicker, flash, scale, depletion, sun and `blackout` (staggered switch-off of lit
windows and lamps). Caption kinds: `title`, `caption`, `chapter` (large hour card with an
optional `sub` line) and `alert` (red emergency-alert banner). The full vocabulary is in
`studio/core/catalogue.py`, and `validate` rejects anything outside it.

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

## Continuous integration and cloud renders

`.github/workflows/ci.yml` runs ruff, mypy, the fast tests and `validate` for every production on each
push to `main` and on pull requests. `.github/workflows/render.yml` renders in the cloud: run it from
the Actions tab for one film or all of them, or push a `v*` tag to render every film at standard.
Each scene renders in its own job (`render-scene --encode-clip`), then one job per film assembles the
fingerprinted clips (`assemble --from-clips`), checks the MP4 and uploads it, optionally to a release.

- GitHub-hosted runners have no GPU, so Eevee renders in software under Xvfb: expect it to be much
  slower than on a Mac, and a hosted job stops at 6 hours.
- One run can start at most 256 scene jobs; the seven films have 243 scenes between them.
- Blender, FFmpeg and the Piper voice are checked against pinned SHA-256 checksums and the actions
  are pinned to commit SHAs: change a version and its checksum or SHA together.
- A new production is validated automatically; add it to the `project` choices in `render.yml` to
  render it there.
- GitHub recommends self-hosted runners only for private repositories, and this one is public.
