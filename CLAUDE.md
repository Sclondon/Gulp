# Gulp: notes for future sessions

Read `README.md` first. Started 2026-11-17 by an agent, from nothing. **"Gulp" is a placeholder name** (Claude's).

## The brief (the user's words, 2026-11-17)

"lets also start a new agent to make a new game like Odell Down under where you start as a small sea creature and
eat to get bigger, but in 3d, using moon jellies and salmon run as a base for assets"

That sentence is all the user has said about this game. It was read as: an original eat-and-grow game in 3D. Only
the genre idea is taken from Odell Down Under: none of its name, species list, numbers, screens, text, art or sound.
Keep it that way.

## The second brief (the user's words, 2026-11-17, evening, one after another while work went on)

- "Lets work on gulp- theres several new fish models we need to add the that gif agent has been working on so
  we'll need all those" (GameCommon's creatures made for the Diorama GIFs), "as well as sardines and sword fish and
  sail fish"
- "blue fin tuna, blue marlin, mahi mahi, wahoo, barracuda, sea bass, mackerel, big eye tuna, grouper, snapper,
  rockfish, perch, pacific bonito, blue shark, leopard shark, kelp bass, garibaldi, halibut, anchovy, rays, lobsters,
  shrimp, crabs"
- "and we need to add a kelp forest and rocky area, a open ocean shelf, and then a sea grass bed area, a nudibranch,
  also probalby a smaller reef area, and a sandy open area with garden eels"
- "the fish should be able to open their mouths"
- "And you should be able to jump above the waters surface ala salmon run"
- "we need sharks whales dolphins otters and seals and sea lions as well", "octopus", "humbolt squid", "humpback,
  gray, sperm, and blue whales", "and orcas", "and fin whales", "whale shark"
- "devil rays, manta rays, cuttlefish, spotted eagle rays, butterflyfish, lionfish, parrotfish, wrasse, surgeon fish,
  clownfish, blue tang, multiple buttflyshi types, angelfish,"
- "there should also be a mangrove / river entrance area for fresh water fish as well, arowana, pirahna, cat fish,
  trout, pike, perch, walleye, carp, koi, gar, lampray,"
- "There should be branching paths as you evolve in size with choices"
- "tetras, guppys, bettas, and other commmon small aquarium fish as well", "plankton, and krill also", "ammonites",
  "horseshoe craps"
- "there should also bea trench area", "with trench fish, angler fish, and other types"
- "and it should be an online arena like the other \",.io\" style games on the arcade", "with a high schore"
- 2026-11-18: "the eyes for most of them should be more cartoony and personalized"; "the contols UI should be old timey
  submarine themed, and there needs to be a lever to control speed around the boost button instead of just swimming
  same speed all the time"; then the list of more animals quoted at the top of `tools/NEXT_BUILDERS.md` (marine
  reptiles, Paleozoic animals, turtles, walrus, narwhal, pufferfish, seahorses, echinoderms, slugs, shells, anemones,
  shrimps, more jellyfish, glowing things, seaweed).

### What is done of it (2026-11-17)

- The creatures are GameCommon components in `creatures/` (installed with `kit.sh`); `scripts/species.gd` is the one
  table of every kind (what draws it, where it lives, how many, how it behaves). **A kind whose creature is not
  installed is left out of the sea by itself**, so installing a finished component and running `--import` is all it
  takes for a kind already in the table (check its script path and class there).
- **Every animal the user named is built and installed** (87 folders in `creatures/`, about 290 animals and 20
  schools stocked): see `Species.ALL` for the list. Schools (one draw each): krill, sardine, anchovy, mackerel,
  piranha, neon tetra, zebra danio, lanternfish. Plankton clouds feed a fish under 0.45 m. The old code-built shark
  is only a fallback now (`white_shark` is installed).
- The sea is a coast (`Sea.ZONES`, `Sea.ground`): river mouth, sea grass, sand flats, kelp, reef, the shelf's edge,
  open ocean, a trench. `scripts/scenery.gd` plants it from GameCommon's `plants/` and `scenery/`: kelp on rocks
  (with an arch), sea grass, a coral reef with clownfish anemones, cliffs along the shelf's edge, garden eels in the
  sand (they sink; one still out can be eaten), mangroves along the river. Rocks, coral heads, cliffs and mangrove
  roots stop a swimmer through `Sea.add_rock` (spheres in a grid of 8 m squares). The old rock outcrops are retired
  (`models/sea_floor.glb` is unused). The trench has no scenery of its own and is no darker than the rest.
- **A web build has not been made since, and would be far too big as it stands**: the models are about 105 MB of
  `.glb` (each creature loads its full and its low model). Before a push: export low models only for the web, or
  cut the list of kinds there. Phones are untried (about 6 ms a frame at the reef on the desktop).
- Unused so far: lionfish spines do not sting; the betta's `flare`, cuttlefish patterns, the otter's `afloat`, the
  gar's `snap`, the arowana's and whales' `arch`, the manta's `scoops`, the anglerfish's `lure` are never driven;
  nothing but the player leaps; air-breathers do not go up for air.
- Bot (tests): from sardine to an 8 m orca in 300 s with no deaths, so the sea is too easy as tuned.
- Learned: Godot's importer makes automatic LOD meshes, and a body bent in its vertex shader then bends in straight
  pieces far off; `Fish._wear` sets `lod_bias` 64 on every creature mesh to stop it (some newer components also
  strip the LODs themselves).
- Branching growth (`Player.GROWTH`, the cards in `Hud.ChoiceCard`), the leap (`Player.in_air`), mouths (`Fish.bite`).
- The online arena (`scripts/arena.gd`, `arena_net.gd`; after Liquid Metal's): players share a room on the site's
  server and eat each other by the one rule; each game keeps its own sea life (Claude's simplification); the high
  scores are the longest fish by name, kept in the server's memory only (lost on a deploy: not the site's
  leaderboard yet). The server part is the branch `gulp-arena` in the worktree `C:/Projects/scareathon/wt-gulp-arena`
  (one commit, NOT pushed or merged: the live server has no /gulp/ws yet, so a web build plays alone until it is).
  `sh tests/arena.sh /c/Projects/scareathon/wt-gulp-arena/server` passes (a tuna eats a sardine, two copies).
- Bubbles, spray and splashes (`scripts/effects.gd`, `scripts/splash.gd`, `shaders/splash.gdshader`) are Salmon Run 2's
  (its `scripts/fx/splash.gd` and the particles in `scripts/player/salmon.gd`, at its a34aa80) with its track taken
  out and sized to the fish; the user: "The bubble and particle and splash effects should be based on the salmon run
  ones in game common". They were not in GameCommon (only `godot/water`, a different water, cites Salmon Run 2):
  these copies are worth saving there as a component.
- Not started: sound, the shore and sky above the water, a darker trench, the site's leaderboard for the high score.

### The model builders

Every model was built by an agent into its own folder in `C:\Projects\GameCommon\godot` (the first wave was cut off
by the account's usage limit and restarted on another model). The brief they followed is kept at
`tools/CREATURE_BRIEF.md`; `tools/PENDING_BUILDERS.md` is the queue as it stood (all of it is now built). The new
components are not yet in GameCommon's README index. The new octopus is `giant-pacific-octopus`
(`GiantPacificOctopus`): GameCommon's `octopus` is Warren's and was left alone.

### Claude's picks in this round (change freely)

The Californian species where the user's word was loose (kelp bass, garibaldi, leopard shark and bonito pointed
that way); the coast's layout and depths; which kind lives in which zone, how many and how big; that whales and
the whale shark are harmless giants; the growth tree itself; that the sea stands still while a choice is made;
leaping by swimming up fast through the surface (no button); far animals hidden beyond 55 m; `.blend` files of the
creatures not kept in this repo (GitHub Pages serves it; they are in GameCommon).

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

## Model weight, and the Twilight Princess yardstick (2026-11-18)

The user: "We should have a twilight princess model to compare to so we can make low poly versions while maintaining
high quality looks and silhouettes", then "we literally have model references": use the data on this machine, not web
figures. The references (looked at and measured only; nothing of them is copied into any project):
`Gloaming/ConceptArt/GameCube - ... - Link (Sumo).zip` (4,174 triangles) and, in `C:\Users\stewa\Downloads`, the same
set's `Link (Zora Armor)` (5,671), `Bosses - Dangoro` (2,451 with its floor pieces) and `Locations - Palace of
Twilight`. Gloaming's own figures were cut to that fidelity (`man_tp.glb`, about 4,500 dressed).

Gulp's models as built (`tests/wire.gd` counts every kind and saves a wireframe of each): full 5,000 to 73,000
triangles (most fish 30,000 to 60,000), low 450 to 6,400; 3.1 million against 251,000 in all. The full ones spend
their triangles as an even fine grid; the reference spends them unevenly: dense at the face, hands and edges of the
outline, a few big triangles across flat stretches. Not yet done: a "game" model of each at that budget.

## The control panel and the title (2026-11-18)

The user's words, in order: "the contols UI should be old timey submarine themed, and there needs to be a lever to
control speed around the boost button"; "There should be a whole control panel on the bottom part, that also shows speed
and your evolution level and maybe any special ability buttons, with and old rusted and e gad frankenstein technology
aesthetic"; (of two rounds of generated pictures) "the non interactive parts are a little too busy, and it looks a
little too obviopusly ai"; "lets recreate the ui as a 3d model to interact with"; "The sonar map should be bigger and
hust off center to the left, the speed dial should be above the boost and soeed controls to the right and bigger, and
the evolution dial should be above the joystick to the left. There can be a little dwpth dial next to sonar"; "the model
should be very similar in style to the first concpet art- though the texture needs to be less noisy"; "the ui model is
too blocky and not lumpy and greebled like the concept"; "The electrodes are fine".

- The panel is a 3D model: `tools/build_panel.py` -> `models/control_panel.glb` (three housings: Helm, Engine, Gauges;
  the script's docstring lists the parts). `scripts/panel_model.gd` (PanelModel) draws it in its own SubViewport and moves
  the parts; `scripts/touch_pad.gd` takes the touches and draws the sonar and the spark over it. The numbers in capitals
  are in both the build script and PanelModel: change both. `shaders/panel.gdshader` paints it (unshaded, no lights).
- **Decision (Claude's pick): a SubViewport with its own World3D and a clear background**, the usual Godot way to put
  3D things in a 2D interface. Alternatives: a second camera on a render layer (the game's half-size dithered picture
  would shrink and dither it), or parenting to the game camera (the water's fog would tint it). The camera is a narrow
  lens straight on, so faces sit where a flat panel would and `PanelModel.to_screen` matches touches to parts by sum.
- The first concept picture is `tools/art_src/panel_concept_1.png`; both rounds of generated pictures and the flat
  panel made from them are retired in `tools/art_src` and `textures/panel` (not used by the game).
- Claude's picks: the burst dial beside the depth dial; the vacuum tubes dropped (the evolution dial replaced them);
  two switches and a grille kept for abilities that do not exist; the instrument housing sunk on wide screens so it
  does not stand over the fish; about 37,000 triangles (not yet trimmed for phones).
- The dials are not labelled. Speed (engine housing), evolution (helm housing, a full turn at 8 stages), depth (small,
  upper, by the sonar), burst left (small, lower).

The title (the user): "the main menu / start of the game should be the boy from warren, a sea captain, and and oldtimy
diver on a shrimping boat (look up reference pics). In the open back cabin of the shrimping boat should be a old timey
franketstein computer hooked up to a helmet on the boys head- the controls for the pc are the controls for the game".
`scripts/title.gd` (Title, and Title.Card for the name and the start button) stands a boat on the surface over the
fish's start; the computer is the panel's own model on a bench; `tools/build_helmet.py` -> `models/brain_helmet.glb`
(helmet, cable, bench). Main opens on it unless a test, bot or picture is driving (`--title` forces it), and on start
sends the eye down through the surface to the fish. Tests skip it.

## More animals (2026-11-18)

In the sea from the user's second list: ichthyosaur, mosasaur, plesiosaur, walrus, narwhal (open ocean, no cold sea yet),
four sea turtles, pufferfish, three seahorses, cleaner/mantis/pistol shrimps, three starfish, three urchins, feather
star and sea lily. `Species` gained `slow` (pace beside a fish of its length; 0 stays put). Installed but NOT yet in
the sea (they need placing like scenery or the nettles, not as swimmers): `anemone` (three kinds), `lions_mane_jelly`,
`box_jelly`, `fried_egg_jelly`, `man_o_war` (floats on the waterline). Places, numbers and sizes are Claude's picks.
