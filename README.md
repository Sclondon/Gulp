# Gulp

*(Gulp is a placeholder name.)*

An eat-and-grow game in a 3D sea. You start as a sardine. Eat what is smaller than you, keep clear of what is
bigger, and grow: sardine, young salmon, salmon, tuna, shark. Being eaten ends the run and you start again small.
The top of the screen shows the row of fish you grow through, how far you have eaten towards the next, and how long
you are; the longest you have ever been is kept.

Godot 4.7, GL Compatibility, phone first (upright or on its side), also playable on a PC. On the arcade as an early-access cart since 2026-11-17 (github.com/Sclondon/Gulp, served from `build/` by GitHub Pages; export with `godot --headless --path . --export-release "Web" build/index.html`, push, then bump `GULP_URL`'s `?v=` in the site's `games.tsx`).

## Playing

- **The stick** (bottom left; or A/D and W/S, the arrow keys, a gamepad's left stick) turns the fish: left and right
  round, up and down for its nose. It always swims the way it points.
- **The round button** (bottom right; or Space, Shift, a gamepad's A) is a burst of speed while held. The ring round
  it is how much burst is left; it fills again when you let go.
- **The round arrow**, when the run is over (or Enter, Space, a gamepad's A), starts another.

What you can eat: anything no longer than four fifths of your own length (and not too small to bother with: under
a twelfth or so of it), when your mouth reaches it. Krill (pink
clouds near the surface) are the food of the smallest; then sardines, small fish, young salmon, salmon, tuna and
sharks as you outgrow each; and moon jellies smaller than you (not much of a meal). What can end the run: a fish big
enough to eat you that catches you (the screen's edges go red while one is after you; it gives up after a few seconds),
and touching a moon jelly wider than you can eat (it stings).

## Running it

```
godot --path .                       # play (sound on: there is none yet)
godot --path . -- --stage=3          # start runs as the fourth fish (0..4)
godot --path . -- --calm             # nothing hunts
godot --path . -- --near=jelly       # start beside a jelly (or shark, salmon, tuna, smolt, sardines, krill)
godot --path . -- --bot              # it plays itself
```

Godot is `C:\Program Files (x86)\Steam\steamapps\common\Godot Engine\godot.windows.opt.tools.64.exe`.

## Tests

All silent (`--audio-driver Dummy`), each prints PASSED or FAILED.

| | |
| --- | --- |
| `sh tests/smoke.sh` | Headless. The checks in `tests/checks.gd`: the sea is stocked, you start small, eat a krill, cannot eat your own size, grow into the next fish, a shark does not graze on krill, a smaller fish flees, a bigger one hunts you down, the run ends, the next starts small, a big jelly stings |
| `sh tests/bot.sh [seconds]` | Headless, faster than real time. The bot (`scripts/bot.gd`) plays for 240 s of game time; passes if it grew at least one stage. Prints what ended each run |
| `sh tests/touch.sh` | A small window for a few seconds (headless puts touches in the wrong place). Fingers work the stick, the burst button and the start-again button |
| `godot --headless --path . --audio-driver Dummy -s res://tests/winding.gd` | Inside-out check of every mesh drawn (the fish, the rocks, the jelly) |
| `sh tests/shots.sh <new folder>` | Pictures of the game and the run-over screen at phone and desktop sizes, and a jelly close up |
| `godot --path . --audio-driver Dummy --resolution 390x844 -s res://tests/caustics_view.gd -- --near=docks --hour=12 --out=<folder> [--no-caustics] [--only=<name>]` | Pictures in the game of the caustics on the floor, rocks, the pirate ship, the liner's reef and animals (no depth limit) |
| `tests/hitboxes.gd`, `giants_solid.gd`, `camera_clear.gd`, `floor_clip.gd`, `setpiece_hits.gd` | Hit boxes and clipping against what is drawn (headless `-s`; how to run each and what it prints: `tools/QUALITY.md`) |

`godot --path . --audio-driver Dummy --disable-vsync -- --bot --seconds=12` prints what a frame costs (`GULP COST`, `GULP RAN`).

What a frame costs place by place (a window; `tests/perf.gd`, `tools/PERF.md`): `godot --path . --audio-driver Dummy
--disable-vsync --resolution 390x844 --position 2600,60 -- --perf=start,kelp,reef,pirate,ruins,docks,ball` prints a
`PERF ROW` a place (frame, scripts, draws, triangles), the heaviest things in view and what each really draws;
`--perf=title` the title and the start-up times; `--perf-shots=<folder>` saves a picture of each place.
`godot --headless --path . --audio-driver Dummy -s res://tests/rocks_bench.gd` times `Sea.clear_of_rocks`.

## What is in it

| | |
| --- | --- |
| `scripts/main.gd` | The game: the sea in a half-size SubViewport shown through the post shader, the camera, the controls, starting and ending runs, the arguments |
| `scripts/sea.gd` (`Sea`) | The sea: sand floor, rocks, water overhead, light, fog, marine snow; its size (`RADIUS`, `SURFACE`), `ground`, `keep_in`, `clear_of_rocks` |
| `scripts/fish.gd` (`Fish`) | A fish of any kind at any length (the meshes, the tail wag); `Fish.pace` is how fast a length swims |
| `scripts/player.gd` (`Player`) | The player's fish: steering, the burst, eating and growing through `STAGES` |
| `scripts/creature.gd` (`Creature`) | One of the other fish: wanders, flees, hunts |
| `scripts/life.gd` (`Life`) | Everything else alive and who eats whom (`can_eat`, `BITE`): krill and sardine flocks, the fish, the jellies; what is eaten comes back later far away |
| `scripts/hud.gd` (`Hud`), `scripts/touch_pad.gd` (`TouchPad`) | The row of fish, bar and lengths, the red edge, the run-over screen; the stick and the burst button |
| `scripts/bot.gd` (`Bot`) | Plays by itself, for the tests |
| `scripts/moon_jelly.gd`, `shaders/moon_jelly.gdshader`, `shaders/aura.gdshader`, `models/moon_jelly.glb` | The moon jelly, copied from Moon Jellies unchanged |
| `scripts/world/props.gd`, `scripts/util/mesh_builder.gd` | Salmon Run 2's low-poly models, copied unchanged (only its fish are used) |
| `shaders/water.gdshader`, `post.gdshader`, `psx_common.gdshaderinc`, `bubble.gdshader`, `textures/foam_noise.png` | Salmon Run 2's water, underwater picture and bubble, copied (the water as Moon Jellies has it) |
| `shaders/fish.gdshader` | Salmon Run 2's fish shader, changed to fit a fish of any length (the changes are listed at its top) |
| `shaders/sea_floor.gdshader`, `models/sea_floor.glb`, `models/sea_rocks.json` | The rocks: Moon Jellies' rock shader; the model built by `tools/build_sea_floor.py` |
| `flock/` | GameCommon's `godot/flock`, with `move_boid` and a riders mode for swarms of thousands added (`tools/SCHOOLING.md`) |
| `scripts/sand*.gd`, `scripts/dust.gd` | GameCommon's `godot/sand`, unchanged |

## Models

Built in Blender by script, with an editable `.blend` in `tools/blend/`:

```
"C:\Program Files\Blender Foundation\Blender 4.3\blender.exe" --background --python tools/build_sea_floor.py
"C:\Program Files\Blender Foundation\Blender 4.3\blender.exe" --background --python tools/build_moon_jelly.py
```

Add `-- <folder>` for pictures from every side. Both print a `WINDING` line (the inside-out check).
`build_sea_floor.py` also writes `models/sea_rocks.json` (each rock as a sphere, for the fish to swim round) and has
the same `ground` sum as `Sea.ground`: change one, change the other, and build again.

## Tuning

- Who eats whom: `Life.BITE` (0.8), `Life.WORTH` (the player ignores food under 0.08 of its length), `Life.TOO_SMALL`
  (hunters ignore a player under 0.3 of their length).
- How many of what, and how long: `Life.FISH`, `KRILL_*`, `SARDINE*`, `JELLIES`.
- The player's stages and lengths: `Player.STAGES`; how fast eating fills a stage: `Player.MEAL`; the burst: `BOOST*`.
- Hunters: `Creature.CHASE`, `TIRED`, `SIGHT`, `SIGHT_PER_LENGTH`; speeds: `Fish.pace`.
- The look: the Environment in `Sea._light`, the post shader's settings in `main.gd`, `lit` in the fish shader.
