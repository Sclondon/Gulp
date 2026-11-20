# Gulp

*(Gulp is a placeholder name.)*

An eat-and-grow game in a 3D sea. You start as a sardine. Eat what is smaller than you, keep clear of what is
bigger, and grow: sardine, young salmon, salmon, tuna, shark. Being eaten ends the run and you start again small.
The top of the screen shows the row of fish you grow through, how far you have eaten towards the next, and how long
you are; the longest you have ever been is kept.

Godot 4.7, GL Compatibility, phone first (upright or on its side), also playable on a PC. On the arcade as an early-access cart since 2026-11-17 (github.com/Sclondon/Gulp, served from `build/` by GitHub Pages; export with `godot --headless --path . --export-release "Web" build/index.html`, push, then bump `GULP_URL`'s `?v=` in the site's `games.tsx`).

## Playing

First you drive the shrimp boat. After the start button you are at its helm, seen from behind, and the same panel
drives it: **the stick** steers (left and right), **the lever** is the throttle (at the bottom it stops), **the round
button** a short burst of speed (two seconds, then it fills again). It cannot go into the shallows, onto rocks or out
of the bay: it is pushed back. **The dive switch** (the right knife switch under the scope, lit amber with a down arrow;
or Enter, a gamepad's X) drops the fish in where the boat is; the boat stays there with its net out, and from then on
the panel steers the fish.

- **The stick** (bottom left; or A/D and W/S, the arrow keys, a gamepad's left stick) turns the fish: left and right
  round, up and down for its nose. It always swims the way it points.
- **The round button** (bottom right; or Space, Shift, a gamepad's A) is a burst of speed while held. The ring round
  it is how much burst is left; it fills again when you let go.
- **The sonar switch** (the left knife switch under the scope; or E, a gamepad's Y) pings: a ring sweeps out over
  the scope and what you can eat shows as gold diamonds, what can eat you as red triangles, each on a stalk up or down
  to its height (dim and hollow: food deeper than you can go yet), fading after a few seconds. The switch creeps back
  up as it charges again (10 s); its lamp shows green when it is ready.
- In the sea, what you can eat now has a thin gold rim and a few gold sparkles; what can eat you a faint red rim.
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

## Editing the bay

The whole layout of the bay is in one file, `data/layout.json`, and you can change it in the Godot editor without
starting the game.

**Open it.** In the Godot editor, open `editor/bay_layout.tscn` (FileSystem panel, the `editor` folder). It opens in a
second or two: the sea floor coloured by depth (a darker line every 5 m, the shore in light blue, each biome's
colour laid over it), the set pieces as plain blocks with their names, and coloured outlines and rings for
everything else. No animals, no water, no loading screen. A bar with the bay's buttons appears over the 3D view.
(If the bar is not there: Project > Project Settings > Plugins, and tick "Bay layout".)

**What you can change, and how.** Everything is in the Scene panel on the left; click a name there, or click it in
the view.

- *Places* (Start, Liner, Pirate ship, Atlantis, Seal rock, South islet, the docks, the kelp arch, Carmel pier, the
  markets, the dune anchors, the old one): drag them with the move arrows. Turn the liner, the pirate ship and the
  dune anchors with the rotate tool. What belongs to a set piece is inside it in the Scene panel and moves with it:
  the liner's two seats, its reef and the reef's outline; the pirate ship's hollow and zone; Atlantis's zone and
  basin; the docks' zones and harbours. Moving Atlantis moves its whole plan of buildings and stairs too, but the
  ruins were built to fit their canyon walls: after a move, rebuild them (tools/RUINS.md).
- *Areas and lines* (the biomes under Biomes: kelp, dunes, grass, crags; the reef inside Liner; the Trench; the
  River's course; the garden eel colonies; the dune fields' boxes): select one and use the path buttons in the bar
  at the top of the view: move a point by dragging it, add points with the add-point button, remove them with the
  delete-point button. To make another area of the same biome, select one and press ctrl+D, then move it.
  The trench, the beach strip and the river's banks are biomes the game works out by itself (the trench by depth,
  the beach along every shore), so they follow the floor.
- *Rings* (the spawn zones under Zones, the harbours, the shelves the wrecks rest on, the river mouth, Atlantis's
  basin, the reef-back's walk): drag the ring to move it, drag the round handle on its edge to make it bigger or
  smaller (or type the size in the Inspector on the right). A harbour's or shelf's depth is in the Inspector too.
- *Animals*: select a zone; in the Inspector, "Kinds" lists the kinds of animal that live in it: add or remove names.
  How many of each kind there are: select "Animals" and change the numbers. Which zones the schools (krill,
  sardines, anchovies...) keep to: "Schools". Where the krill and anchovies stay near the start: the Start's
  "Extra" (room: how far from the start, depth: how deep).
- *The floor*: in the bar, pick a brush (Raise, Lower or Smooth), set its Size and Strength, and paint on the
  floor with the left mouse button. Raise the floor above the water to make land; lower land to make water. Your
  painting is kept separately from the real map of the bay, which is never changed, so it can always be undone.
  Set the brush back to Off to move things again. "Floor numbers" (inside Trench) has the numbers the floor is
  made with: the terraces in the trench, how much bigger the Monterey Peninsula is, the easing near the shore.
- Ctrl+Z undoes anything, painting included.

**Save.** Ctrl+S (or Save in the bar) writes the layout file. The floor's picture is then made again in the
background (about 1 to 2 seconds; the bar says when it is ready).

**Rebake floor.** Painting the floor, changing the trench or the floor numbers needs the floor baked again.
Rebake does it and redraws the floor: about 2 seconds. Until then the bar says "brush edits not baked yet" (what
you painted is shown already, but the game does not have it yet).

**Play here.** Saves, rebakes if it has to, and starts the game with your fish where the 3D view's camera is (if
the camera is above the water, where it is looking, a few metres over the floor). There is no depth limit in a
run started this way, and it is not saved as your best. Things are a little jerky for the first few seconds,
because it skips the loading screen.

What it does not cover yet: the plants and rocks of a few small places stay where they are when you move the thing
they belong to (the kelp around Monterey's docks, Carmel's reef and beach, the rocky points along the coast), and
so do the fishing nets and the surf breaks. They are still written in the code (CLAUDE.md, "Decision: the bay's
layout in one file").

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
| `godot --headless --path . --audio-driver Dummy -s res://tests/layout_check.gd [-- --out=<file>]` | Fingerprints the layout as the game sees it (floor, biomes, zones, places, each kind's zones): the same before and after a change that should change nothing |
| `godot --editor --headless --path . --audio-driver Dummy -- --bay-layout-test` | The bay editor in a headless editor: opens it, saves unchanged, moves and undoes, brushes, rebakes and undoes byte for byte, ctrl+S, Play here; puts every file back. `BAY EDITOR PASS` |
| `godot --path . --audio-driver Dummy --resolution 1280x900 -s res://tests/bay_layout_view.gd -- --out=<folder>` | Pictures of the bay editor's scene (slanted and from above) |
| `tests/hitboxes.gd`, `giants_solid.gd`, `camera_clear.gd`, `floor_clip.gd`, `setpiece_hits.gd` | Hit boxes and clipping against what is drawn (headless `-s`; how to run each and what it prints: `tools/QUALITY.md`) |

`godot --path . --audio-driver Dummy --disable-vsync -- --bot --seconds=12` prints what a frame costs (`GULP COST`, `GULP RAN`).

What a frame costs place by place (a window; `tests/perf.gd`, `tools/PERF.md`): `godot --path . --audio-driver Dummy
--disable-vsync --resolution 390x844 --position 2600,60 -- --perf=start,kelp,reef,pirate,ruins,docks,ball` prints a
`PERF ROW` a place (frame, scripts, draws, triangles), the heaviest things in view and what each really draws;
`--perf=title` the title and the start-up times; `--perf-shots=<folder>` saves a picture of each place.
`godot --headless --path . --audio-driver Dummy -s res://tests/rocks_bench.gd` times `Sea.clear_of_rocks`.

Driving the boat: `-- --helm` starts the game at the helm without the loading screen (`--dive` drops in at once, for
tests). `godot --path . --audio-driver Dummy --fixed-fps 30 --resolution 390x844 -s res://tests/boat_gif.gd -- --helm
--offline --move=turn|swell|surf|shore|drop --dir=<folder>` saves frames of a drive for a GIF and prints a `BOAT` line a
frame (speed, depth under it, heel, pitch, the camera's height and roll).

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
