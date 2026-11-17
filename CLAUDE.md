# Gulp: notes for future sessions

Read `README.md` first. Started 2026-11-17 by an agent, from nothing. **"Gulp" is a placeholder name** (Claude's).

## The brief (the user's words, 2026-11-17)

"lets also start a new agent to make a new game like Odell Down under where you start as a small sea creature and
eat to get bigger, but in 3d, using moon jellies and salmon run as a base for assets"

That sentence is all the user has said about this game. It was read as: an original eat-and-grow game in 3D. Only
the genre idea is taken from Odell Down Under: none of its name, species list, numbers, screens, text, art or sound.
Keep it that way.

## Whose calls

The user's: the sentence above (the genre, 3D, starting small, Moon Jellies and Salmon Run 2 as the asset base).

Claude's picks (change freely, none is a rule; the user has not seen or played any of this yet):
- The name "Gulp" and the folder.
- **GL Compatibility, phone first** (the `new-game` skill's default), every control on screen as a symbol. Moon
  Jellies and Salmon Run 2 are both Forward+ projects; see "What Compatibility changed" below.
- The chain: sardine, young salmon (smolt), salmon, tuna, shark, all Salmon Run 2's fish. The player is always a
  fish; moon jellies are in the sea, not in the chain.
- One rule for everything: a mouth eats what is no longer than 0.8 of its owner. The player ignores food under 0.08
  of its own length (a shark parked in a krill cloud grew to full size in the bot's hands before this). Bigger fish
  hunt the player only (they do not eat each other), ignore a player under 0.3 of their length, and give up a chase
  after 4 s.
- A moon jelly wider than the player can eat **stings and ends the run**; smaller ones are food (poor food).
- The fish always swims forward; a stick turns it; one button is a burst with a stamina ring.
- A round sea 44 m in radius and 16 m deep, lighter than Moon Jellies' (hunters must be seen coming).
- The half-size picture with Salmon Run 2's dither (a retro filter for phone budgets, as the skill suggests).
- What is eaten comes back 5 to 16 s later, at least 24 m from the player, so the sea never empties.
- At the last stage the shark only grows to 6 m and the run goes on. There is no win screen.
- The longest length is kept in `user://gulp.cfg`. No sound, no title screen, no menu, no lore.
- A few bubbles where something is eaten, and a red edge while hunted (feedback the loop needed; small).

## Where the assets came from

- **Moon Jellies** at its 642f9bd (2026-11-17), plus what was uncommitted on disk then (another session was still
  working in it): `scripts/moon_jelly.gd`, `shaders/moon_jelly.gdshader`, `aura.gdshader`, `sea_floor.gdshader`,
  `water.gdshader`, `post.gdshader`, `psx_common.gdshaderinc`, `models/moon_jelly.glb`, `textures/foam_noise.png`,
  `tools/build_moon_jelly.py` and its `.blend`: all unchanged. `scripts/sea.gd` is a rewrite of its `sea.gd`
  (bigger, lighter, CPU snow). `tools/build_sea_floor.py` is its script changed (26 outcrops over the bigger sea,
  320-triangle rocks, the spheres file); the rocks were built again from it.
- **Salmon Run 2** at its 37b2825: `scripts/world/props.gd` and `scripts/util/mesh_builder.gd` unchanged (kept at
  the same paths so that they stay so), `shaders/bubble.gdshader` unchanged, `shaders/fish.gdshader` changed (see
  its top).
- **GameCommon**: `godot/sand` unchanged; `godot/flock` with one method added in `flock/flock.gd`, `move_boid(i, at)`
  (puts one boid somewhere else, calm: for boids that are eaten). Worth pulling back to GameCommon if it is kept.
- Nothing was changed in Moon Jellies, Salmon Run 2 or GameCommon.

**The fish are code-built meshes** (Salmon Run 2's `props.gd` makes them with its MeshBuilder), which is against
the user's general rule of models built in Blender. They were reused as they are because the user named Salmon
Run 2 as the asset base. Only the rocks were built new, in Blender. If the fish are to be reworked, build them in
Blender then.

## What Compatibility changed from the Moon Jellies look

- The marine snow is `CPUParticles3D` (500 specks round the camera), not 5000 GPU particles with turbulence.
- No depth-of-field blur, no 4x MSAA, no sun shadows.
- Glow is switched on in the Environment but its effect under Compatibility was not compared with Forward+.
- The jelly itself (added light, beating bell, rope arms, aura and sparkles, its own lamp) draws as in Moon Jellies:
  checked in a picture close up. Each jelly's lamp is a real OmniLight3D: nine of them
  (`limits/opengl/max_lights_per_object` is 12 for the sand).

## Things to know

- `Sea.ground` and `ground` in `tools/build_sea_floor.py` are the same sum: change one, change the other, build the
  rocks again (it also rewrites `models/sea_rocks.json`).
- Rocks stop fish only as spheres (`Sea.clear_of_rocks`); nothing uses physics. The camera can pass through a rock.
- `ARM_*` numbers in the jelly are in three places that must agree (see Moon Jellies' CLAUDE.md).
- A jelly's "length" for the eating rule is its bell's width (`size * 2`).
- Flocks: `Flock.predators` is set by `Life` each frame (the player, once it can eat them); the `flock_predators`
  group is not used. Schools and jellies too far off to see are not moved or drawn (`Life.*_SEEN`).
- Tests steer the player themselves: with `--check` the real keys, pad and touches are ignored; with `--bot` the bot
  is the only input. The touch test's window never takes focus.
- New `class_name`s need `godot --headless --path . --import` before a test run.
- The post shader, water and fish need the `water_clock` and `psx_wobble` shader globals (in `project.godot`;
  `psx_wobble` is 0: no PS1 vertex jitter).

## State (2026-11-17)

First playable. Verified by the tests in the README (smoke, bot, touch, winding) and by pictures at 390x844,
720x1170, 844x390 and 1280x720. About 5 ms a frame on the desktop (RTX 4080) with vsync off.

Not verified or rough:
- Nobody has played it by hand: the feel of the steering, the camera and the difficulty are tuned only by the bot
  (from the start it reaches the second or third fish in five minutes of game time, dying about once; before the
  hunters were made fairer it died every ten seconds).
- Never run on a phone or as a web build; the cost there is unknown (ten flocks, nine jelly lamps, the sand).
- The top of the chain has been reached only by the bot started as the tuna (`-- --bot --stage=3`: it grew into the
  shark and to its full 6 m in under 400 s, about 100 meals). No run has gone from sardine to shark.
- The camera does not avoid rocks. Fish turn away from rocks only by being pushed out of their spheres.
- The red edge is drawn as nested rings and shows faint lines. The picture is very blue; fish colours are muted.
- No sound at all. No attract script, no dev panel (the arguments stand in for one), no web export preset.
