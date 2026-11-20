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
- Schooling and habits (2026-11-18, `tools/SCHOOLING.md`): krill, sardines, anchovies, lanternfish and mackerel are
  swarms of 160 to 1,600 (Flock's riders mode: a few dozen guides simulated, the rest placed by flock.gdshader);
  creatures keep together in groups by Species' `social`/`group`/`mix`, and live by a `habit` (ambush, stalk, pack,
  filter, graze, cleaner, shy, hop, cling, home, drift, sting, display, strike, float) plus `breathes`, `leaps`,
  `visits`, `nocturnal`. Lionfish sting (a hurt, not a death). Still never driven: cuttlefish patterns.
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

### Later the same day (2026-11-18): the panel low-poly, the title built, more planted

- The user: "Still not enough pipes / wires shaping the ui outline"; "the dials need labels"; "Pipes and wires need
  proper connections, nails need proper models / textures, and make it low poly twilight princess style"; "The gaps
  between the wires and side pipes and details should be smaller- rhey should hug the panel tighter".
- So `tools/build_panel.py` now builds a LOW-POLY model (about 17,000 triangles) and BAKES its paint with Cycles into
  one picture, `textures/panel/panel_atlas.png` (about 2.5 minutes a build; `-- --no-bake` skips it). Procedural
  Blender materials give the rust and brass; the bake adds light from the upper left and contact shadow. The housings
  are baked with the moving parts hidden, then the moving parts. `shaders/panel.gdshader` draws the picture unlit with a
  shine by material name (`PanelModel.PAINTS`). Every pipe and wire goes through `run(...)`, which ends it in a flange
  (`"Y"` a face, `"X"`/`"-X"` a side, `"Z"` a top). Dial labels are symbols (`sign`): fish = evolution, chevrons = speed,
  wave and arrow = depth, bolt = burst left. The atlas packs loosely (much of it is empty): worth repacking if the
  picture needs to be sharper or smaller.
- `tools/build_helmet.py` runs the top of build_panel.py for its helpers and bakes `textures/panel/helmet_atlas.png`
  for the helmet, cable and bench.
- The title is built: `models/shrimp_boat.glb` (`tools/SHRIMP_BOAT.md`), the three figures (`scripts/title_figures.gd`,
  `tools/TITLE_FIGURES.md`: on the boy's skeleton with their own small idle, because GameCommon's character-controller
  cannot be installed here while Gulp has its own `Player` and `Dust` classes), the computer, the helmet on the boy's
  head mount with two cables. `--title` shows it for a picture, `--dive` starts the dive by itself. The boy's hair and
  skin are plain materials, not Warren's ink-figure look (that needs `godot/ink-figure`).
- Planted by `scripts/scenery.gd`: GameCommon `seaweed` (six kinds; sargassum afloat over the open ocean) and living
  `anemone`s. Also in the sea: cameroceras, anomalocaris, three trilobites, dumbo octopus, firefly squid, comb jelly,
  pyrosome. Installed but not yet used: `sea_sparkle` (needs `stir` from Life), the four new jellyfish (need Life's
  jelly handling), `sea_slug`/`clam`/`oyster` when their builder finishes.
- About 9 ms a frame on the desktop in the kelp now (it was about 6).

## The places as levels (2026-11-18): floor types and the rule-based placer

The user: "the foliage needs a smart realistic distrbtion, do research on kelp forests and othe under sea biomes and
make good game design \"levels\" out of them". `tools/BIOMES.md` is the design (research, each place's plan and rules,
what kit is missing) and, under "Phase two", what is built and the budget table. In short: `scripts/floor_types.gd`
says what the floor is at every 2 m corner (rock, sand, mud, shell, crust, white) and paints it with the sand's own
kinds (no new shader); `scripts/biomes.gd` places plants and floor pieces by per-place rule tables (floor type, depth,
slope, density at core and edge, noise, clumps); kelp grows only on rock. `Sea.MARKETS` holds the three fish markets'
landings. The old one and the reef back lie and walk in the deep (`Scenery._add_giants`). Every choice there is
Claude's, and the user's six open questions were answered with Claude's defaults (BIOMES.md section 9): change freely.

## Asked for on 2026-11-18 and where each stands (the user's words; update as they land)

How to work on anything visual here (the user: "We need a concept are solution", "spend more time coming up with a design
... maybe generate concept art ... and do a couple qualitu passes"): CONCEPT ART FIRST. Generate it with Gemini in the
user's Chrome (gemini.google.com, signed in; free; ChatGPT's free image limit runs out after three), keep it in
`tools/art_src/concept_*.jpg`, give it to whoever builds, and have them do quality passes against it. Gemini drops the
first prompt typed right after the page loads (send it twice), and a new picture often shows only after a reload.

In progress with builders (each has a notes file in tools/): the Monterey Bay map with docks, beach, two kelp forests,
the mangrove river at the centre, a pirate-wreck outcrop with a seal island, Atlantis in the lower trench
(`MONTEREY.md`; the user drew the layout: it is described in the map builder's brief, not saved as a picture); the
liner wreck reef (`WRECK.md`), the Atlantis ruins (`RUINS.md`), the pirate wreck (`PIRATE_WRECK.md`); water effects,
day and night, the jump and splash (`WATER_FX.md`); schooling, swarms and species habits (`SCHOOLING.md`); the boat's
quality pass (`SHRIMP_BOAT.md`).

Not started:
- "come up with some special abilities like inking as a squid" (the two switches on the panel are for them).
- "Pause menu and other Uis need the same treat ment as the the controls, and we need a way to view the evolution
  tree, and to add some roguelike elements" (concept: `tools/art_src/concept_menus.jpg`).
- "we should take the current concept from salmon run like rails to get around the map faster".
- "there should also be classic under water mines".
- "we should add some birds, cormoratns, sea gulls etc", "some sea gulls on the boat at the beginning and following
  along windwaker style".
- "try to think of any animals we're missing and do a pass making them".
- "look up how abzu animated their animals and we need to do an animtaion quality pass on how the fish turning and
  stuff works, the flapping needs to be tied to acceleration for example, and some animals need special case passes
  like the whales, squids, crustcateans. Im a big fan of phscially based and rope phsysics and seing soft body
  reactions".
- "the loading screen needs to be a swarm of sardines making up the wayside interactive logo sequence while it loads".
- "the sonar needs to point out things you can eat, or something on the ui does i think, or maybe they need to have a
  subtle outline and sparkle"; "the sonar map needs to show objects relation to you in 3d".
- "the logo needs to be made up of a bunch of our fish models making the letters, trying to eat each other"
  (concept: `tools/art_src/concept_fish_logo.jpg`; the picture logo on the title now is a stand-in).
- "the little antenna on the control panel needs to be a bit shorter"; "the boat needs a wake" (foam puffs exist; a
  proper V wake does not).

Web build: a browser on Windows compiles each shader in about a second, so (1) animals get their models only when first
seen (`Creature.become(kind, bare)`, `Life.mark_dressed`), (2) every kind and material is shown once to a tiny view
on the loading screen, and nothing after (`scripts/warmer.gd`; "Decision: everything compiled on the loading screen"
below). Build the web export from the clean worktree `../Gulp-build` (`git checkout
--detach main` there; `git checkout -- build` first if it refuses), after `sh tools/web_excludes.sh` here.

## Performance (2026-11-18): the pass, and the decisions it made

`tools/PERF.md` has the numbers, how they were measured (`-- --perf=<places>`, `tests/perf.gd`; `tests/rocks_bench.gd`)
and what is still heavy. The user asked for the pass ("yes do a performance pass and then push everything"); the
choices below are Claude's.

- **Decision: two grids for the rocks** (`Sea.add_rock`, `Sea.clear_of_rocks`). What: besides the 8 m squares of floor
  (now only a quick "no rock near here"), every sphere is also kept in each 2 m cube it overlaps, and a swimmer is tried
  only against the cubes its own room reaches (at most `Sea.REACH`, 3 m). Why: beside the liner, the pirate ship and
  Atlantis one 8 m square held up to 398 spheres, and a call cost 9 to 12 us; with 190 animals a frame that was 2 ms.
  Now about 1.2 us there (10 times less), 0.35 ms a frame. The practice: a uniform grid (spatial hash) sized near the
  objects' own size, the usual broad phase for many small static colliders. Alternatives: a finer 2D grid (still every
  sphere up the wreck's 17 m height in one cell), a bounding volume tree (more code, no faster for spheres this even in
  size), a box per set piece first (still hundreds inside it). Points deep inside overlapping spheres can come out at a
  slightly different place than before (1 to 2% of random test points; none on the swim routes: the wreck, pirate and
  ruins checks pass).
- **Decision: scenery near and far** (`scripts/lod_field.gd`, `LodField`). What: the sea floor kit's pieces (the
  liner's reef, about 1,100 pieces; the kelp's rocks, the reef zone's corals, the cliffs) are drawn two MultiMeshes a
  piece, the full model within 8 m of the eye (`Wreck.REEF_NEAR`, `Scenery.PIECES_NEAR`, to the edge of the piece) and
  the kit's light model (a fifth of the triangles or fewer) out to `far` (the wreck's SEEN, 60 m; 70 m for the rest),
  none beyond; refilled by 4 m cubes only when the eye has moved half a metre. Why: the liner's reef was one MultiMesh
  of full models a piece: 2.7 million triangles placed, 600,000 drawn at the wreck. Now about 330,000 there (the near
  pieces are still most of it). The practice: distance LOD with instancing (Godot's own visibility ranges and HLOD
  advice); refilling the instance lists on the CPU keeps it to two draws a piece instead of one per piece per chunk.
  Alternatives: chunked MultiMeshes with visibility ranges (five to ten times the draw calls), Godot's automatic mesh
  LODs (picked per MultiMesh, by its whole box: no help when the eye is inside the reef). Looks: from 8 m out the
  pieces are their light models (fewer folds on a brain coral, simpler fans); nearer, nothing changed.
- Smaller ones, each measured (PERF.md): far animals (beyond 20 m) are stepped every other frame; a fish sends its look
  only what changed; the sonar's picture is drawn in five layers, each redrawn only when it changes; jellies, nettles
  and the garden eels are not drawn beyond sight; behind the title every other material of the sea is shown once too
  (`Main._materials_to_warm`), so that the wrecks and plants do not freeze a browser when first seen.
- **Decision: only nearby animals are awake** (2026-11-18, after the user: "Gulp's performance on phone is still very
  choppy and it crashed- are spawning and simming all the fish on the whole map? Probably only need nearby ones"). What:
  all 495 animals are still made at the start (as bare records, no model), but each sleeps where it is beyond
  `Life.SLEEP` (65 m, less two of its lengths) and wakes within `Life.WAKE` (55 m); a group wakes when any member is
  near and sleeps when all are far. A sleeper is hidden, never stepped, and gives its model back (`Creature.undress`);
  `Life.awake` is the only list stepped or searched each frame (Life, the sonar, the fishers, the bot). A tenth of them
  are looked at a frame, all of them when the player jumps more than 10 m (a new run, a test). At most `DRESS_EACH` (2)
  models are made a frame. Drawn within `FISH_SEEN` 45 m (was 55: the fog leaves a fifth of a thing's colour there);
  stepped every frame within 20 m, every other to 32 m, every third beyond. Before, every animal on the map was stepped
  (beyond sight every 8th frame) and kept its model once seen. Why: Life's own time at the start 1.75 -> 0.65 ms, kelp
  2.11 -> 1.24, the liner's reef 2.73 -> 1.87 (desktop; 60 of 495 awake at the start, 131 at the reef). The practice: a
  simulation bubble round the player (entities beyond it frozen and unloaded, woken with a margin past sight, as
  open-world games stream their creatures by cells). Alternatives: spawning fresh animals in a ring round the player by
  zone density (keeps the count steady anywhere but loses where each one was; more rework of groups and stations), or
  only stepping far ones less often (what it was). Tests that put an animal beside the player call `Life.wake(each)`.
  Not verified on a phone; the crash's cause is not known (memory is the likeliest: every kind's shader is compiled
  behind the title and the pack is 40 MB).
- **Decision: everything compiled on the loading screen; creatures drawn from baked paint; lit per vertex**
  (2026-11-19; replaces "shaders warmed by nearness", the same day). The user's calls: "there should be no freezing",
  "whats the point of loading if you have to load after pressing start anyways??", "All loading should just happen at
  the start you shouldnt have to wait for buttons or anything"; and, of baking: "cant you use the shader to generate the
  textures? We dont need the shader for the color textures after its already made tho right", then that baked textures
  "should be standard for most game objects". How it is done is Claude's. What:
  - **One loading screen, then nothing.** `scripts/warmer.gd` (Warmer) shows every animal kind (dressed as the game
    dresses it, its far model too) and every other material of the sea (by shader and MultiMesh format; the eelgrass
    fields, made later, added by Main) to a 32 px view under the sea, a batch a frame: under the water's light, and what is
    lit per pixel (water, sand) again under the air's light (`Warmer.above`: Main sets the sea's light from it while
    warming). No second time beside a lamp since 2026-11-19 (late): a black omni light over the whole sea
    (`Warmer.add_null_lamp`, Claude's pick) means each lit program is only ever drawn in the version an omni light
    reaches, so the jellies' lamps make no second version (12 s less in Chrome, first visit and second; no look change).
    Real Chrome timings and how to take them: tools/PERF.md, "Real Chrome". Then Main shows the
    screens drawn over play once each under the loading screen (`Main._warm_screens`: panel, HUD, a growth card for every
    fish the player may become, the sale, the shop). The sea's own picture is not drawn while the loading screen is up
    (it would compile all it shows in one frame). The loading screen's sardines form the logo by the share done, and a thin
    silver bar with the share in figures under it shows the same real share (the user asked for real progress); when it lifts the title's
    start button is live at once. No warming in play, on menus or for the growth choices any more.
  - **Creatures drawn from baked paint** (GameCommon `godot/baked-look`: `tools/bake_looks.gd`, `scripts/baked_look.gd`;
    its README is the full record). Each component's markings are rendered once from its own shader into a picture on
    a second set of UVs; a copy of its shader keeps its vertex code (swimming, jaw, fins) and reads the picture. Applied in
    `Species.make` (and to Scenery's anemones and hauled-out seals); the baked meshes go into the component's own mesh
    cache, so its own game and far models are never loaded and the web pack leaves them out (`baked/primed.txt`,
    `tools/web_excludes.sh`). The old per-kind shaders stay on disk, unused for drawing (each component script still
    preloads its own, so they ship, a few KB each, never compiled). Kept unbaked: the squids, comb jelly, anglerfish,
    firefly squid (living colour), the ghost whale (added light), the big jellies (their own `light()`).
  - **Lit per vertex**: the baked creatures, the kinds kept unbaked, the plants (kelp, sea grass, seaweed, mangroves), the
    kit's rocks and soft corals, the liner's and Atlantis' paints, the net, flock, plankton, garden eels, nettles, the
    figures' hair (`render_mode vertex_lighting`), and every StandardMaterial3D (`Warmer.light_per_vertex`; not
    the creatures' own: the submarine's stay per pixel, as a material made per animal would compile again). The water and the sand stay per pixel (their light is in their
    fragment: normals, glints).
  Why (tools/PERF.md, "Shader programs"): under ANGLE (as Chrome on Windows) a program lit per pixel costs 1.45 s to
  compile before it draws anything, per vertex 0.27 s; a creature's own shader 2.5 s on average, baked and lit per
  vertex 0.6 s. About 300 programs at the old cost were 10+ minutes, so they could not all be loaded up front. The
  practice: Godot's documented cure for GL Compatibility (no ubershaders or pipeline precompilation there): show every
  material once during loading; plus baking procedural materials to textures, and per-vertex lighting on small
  low-poly models, as mobile games do. Alternatives: one shared creature ubershader (113 of 132 vertex functions
  differ; a single huge program is itself a long freeze, and Godot 3's web ubershaders were withdrawn for browser bugs);
  warming in play by nearness (what it replaces: freezes moved, not gone); unshaded with hand-written light (0.15 s a
  program cheaper again, but every creature's light matched by hand). Measured (desktop, ANGLE, cache cleared, 390x844,
  `-- --dive --tour`, which now passes or fails): see tools/PERF.md, "Everything at the start".
  What looks different: tools/PERF.md lists it kind by kind (eyes fixed looking ahead, no grazing-angle sheen or sparkle,
  koi and guppies three patterns each, fine speckles softer, shine broader).
  GameCommon: the bake tool, `BakedLook` and `tools/compile_cost.gd` are the component `godot/baked-look`, and each creature
  component there carries its `baked/` folder (baked here, with Gulp's settings). After changing them here, pull them back:
  `sh /c/Projects/GameCommon/kit.sh pull godot/baked-look .`, and for a re-baked creature `kit.sh pull godot/<creature> .` (its
  FILES.txt lists its baked files; a new bake makes new mesh names: list them). Re-bake after changing a creature's shader
  or models: `godot --path . --audio-driver Dummy --resolution 320x240 -s res://tools/bake_looks.gd -- --components=<folder>`
  (Scenery's anemones: `--plan=res://tools/bake_scenery.json`), then `--import`, then `tests/baked_compare.gd` to look.
- **Decision: motion families** (2026-11-19, night; the user's call: "each animal should not need its own shader for
  swimming or motion", and they chose a few shared motion families, each animal setting its numbers as
  uniforms; how it is done is Claude's). What: animals drawn from baked paint wear one of four shaders in
  `shaders/motion/` (GameCommon `godot/motion-families`): **swim** (a wave along the body, side to side or up and down,
  the tail plate, curl and arch: 72 kinds of fish, sharks, whales, seals, otter, reptiles, monsters), **swim_sheer**
  (the same, see-through: the flying fish's fins), **flap** (rays' wings bent along the span: manta, devil, eagle and
  bat rays) and **jointed** (only moves: crustaceans' legs on a stride, shells on hinges, turtles, seahorses,
  cuttlefish, urchins, slugs, starfish, the sea myths). A fifth, **radial** (the same moves drawn two-sided), has no
  animal now. Every family shares up to 24 "moves" (turn, move, scale, draw, bend, leg) run on each point, each
  driven by a live setting (`phase`, `sway`, `gape`, `walk`...) the animal's script sets as before. Each animal's
  numbers and moves are its spec, `creatures/<kind>/baked/<shader>_motion.gd`, and what each point of its model is
  (part, weights, a hinge point, a way) is written into its baked meshes' CUSTOM0.zw..CUSTOM3 by
  `tools/motion_labels.gd` (run it in a window, after a re-bake or a spec's `label()` change). `BakedLook` puts the
  family on (`Motion.wear`, scripts/motion.gd) in place of the baked copy of the animal's own shader; with no spec it
  keeps the copy. `tests/motion_compare.gd` draws own against family frame by frame. Why: about 110 creature programs
  were still compiled on the loading screen, one per kind; now 4 (plus 6 kept and 9 unbaked). A first visit is ready at
  68 s (was 137 to 157), a second at 11 s (was 23; the warm-up also shows a batch a frame when frames are quick), the
  cold tour still passes (tools/PERF.md, "Motion families"). The practice: data-driven shaders (one program,
  per-material parameters and per-vertex masks/weights), as engines do with a few master materials and material
  instances (Unreal) or uber shaders with feature parameters, rather than a program per asset. Alternatives: one shared
  ubershader with every kind's own code (a huge program, itself a long freeze), baked vertex animation (exact motion, but
  textures per kind and the numbers no longer tunable), keeping a program per kind (what it replaces).
  Kept on their own baked copies: the moray, octopus and channel catfish (points follow ropes their scripts write into a
  texture), Scenery's anemones, the clownfish's host anemone and the crinoid (they sway by `water_clock` and where they
  stand). What moves differently: tools/PERF.md lists it (urchins' spines, a guppy's tail, a seahorse's grip and the
  flying fish's wings in between, the betta flaring, trilobites rolled up); each spec's comment says what it changed.
  Costs: about 29 MB more vertex memory on the GPU (the labels, full floats: half floats draw wrong here) and 2.8 MB
  more pack. Writing a spec: read the old shader's vertex code, port each part's move as an op, `label()` from the
  model's own part codes; compare to 0.01 or better.
- **Decision: a phone tier** (2026-11-19; Claude's pick of what to turn down). `scripts/tier.gd`: `Tier.phone()` is
  true on web_android/web_ios, a mobile build, or a phone or tablet user agent (an iPad's Safari says Mac, with touch);
  `-- --phone` / `-- --desktop` force it. Desktops, in a browser or not, are unchanged. It turns down what costs a phone
  most (scripts and draw calls, not fill: the sea's picture is 360x779 whatever the phone): the animal bubble and
  stepping (`Life.PHONE`), sand quality 0, eelgrass (lowest quality, `Scenery.PHONE_GRASS`), kelp and LodField
  distances (`LodField.PHONE_*`), water rings (`Sea.PHONE_RING_CELL`), breaker spray, the panel's MSAA, and the panel
  and sonar drawn every other frame. tools/PERF.md lists the numbers. Not verified on a phone. Also:
  `scripts/still_batch.gd` merges a model's still parts into one mesh a material (the shrimp boats, 45 draws to 16).
  Memory (2026-11-20, after the user's iPhone tab was killed on the loading screen; Claude's picks): a phone loads the
  liner's, pirate ship's and Atlantis' atlases at 1024 (`Tier.texture`, copies in `textures/phone/` written by
  `tools/phone_textures.gd`: run it after rebuilding those atlases); the Atlantis atlas is 2048 everywhere (was 4096:
  85 MB of GPU and a 128 MB spike of heap); canvas item buffers 4096. The page held about 790 MB on the iPhone path,
  now about 600 (budget ~600). Measure with `tools/mem_load.js`; tools/PERF.md, "Memory on phones", has the numbers,
  why VRAM compression was not the cause (no picture here is VRAM-compressed) and the choices left for the user.
  Never give a picture over 2048 a side to the web build.
- The web pack leaves out the figures not in the game (tools/web_excludes.sh; 76 MB -> 38 MB); take a figure out of
  that list when the game uses it, and run `tests/web_deps.gd` after changing the list.
- **The sky** (2026-11-18, the user: "Whys the sky just gray"): it was one flat background colour, greyed further by
  the fog and the filmic tone map. Now `shaders/sky.gdshader` (Claude's pick of look, no concept art yet): a gradient,
  pale at the horizon and deeper overhead, the sun or moon with a glow, sparse soft clouds drifting; colours from the
  hour in `Sea._look`, shown only with the eye above water (under it the background is the water colour as before). It
  lights nothing (ambient stays a colour, reflections off) and is redrawn into its small radiance only when `_look`
  changes it (the drift is a uniform, not TIME).
- **Decision: caustics as one pass over the picture** (2026-11-18, the user: "The caustics need to appear on fish and
  props etc"; the way is Claude's pick). What: `scripts/caustics.gd` (made by `Sea._caustics`) draws one full-screen
  quad with `shaders/caustics.gdshader`, first among the see-through things (`render_priority` lowest, so before the
  water's surface, jellies, bubbles and shafts). It reads `hint_depth_texture` and `hint_screen_texture`, rebuilds each
  pixel's world position (Compatibility's depth is turned to NDC as `vec3(SCREEN_UV, depth) * 2 - 1`, through
  `INV_PROJECTION_MATRIX`; tested), takes the surface's facing from `dFdx`/`dFdy` of that position, and lights what
  faces up with the sand's old net (same texture, scale, drift, `water_clock`, depth and distance fades); the fog's
  share of the pixel is taken out first so far things are not lit through the murk. The net is no longer put into the
  sand's shader (`_caustics` still makes the sand's copy for the rock walls), so floor and animals agree exactly. Why:
  one program for every surface (about 156 programs otherwise, 130 of them GameCommon creatures', and a browser
  compiles each on first draw), nothing to keep in step, and its cost is per pixel of a half-size picture, not per
  object. The practice: deferred/screen-space decals and "projected caustics" (world position rebuilt from depth,
  pattern projected from above, masked by facing), as in Godot's own advanced post-processing recipe and Unity/Unreal
  water kits. Alternatives: (b) a shared include and a global sampler in every material (150-odd shaders to edit,
  GameCommon's to fork, every program bigger), (c) a light cookie on the sun (Godot's projector textures work only on
  omni and spot lights, not directional ones, and the sea has no sun shadows; a spot light the size of the view would
  light everything, faces down too, and costs a light per object in Compatibility). Costs measured on the desktop
  (`--perf`, with and without `--no-caustics`): one more draw, GPU time within the run-to-run noise (0.15 to 0.5 ms
  either way). What Compatibility adds for it: one copy of the colour and depth buffers after the solid pass. Rough:
  the facing from neighbouring pixels speckles on thin, busy plants, and the net is about a metre a cell, so a small
  fish only brightens and dims as it swims through it. Not tried in a browser or on a phone.
- The user (2026-11-18, of the overhead chart): "The giant monsters should not just spawn, those will need special
  conditions, and the map needs a lot of work, should be based on a real topography of the bay". So the leviathan, sea
  serpent and ghost whale (Species `monster`) and the old one and reef-back (`Scenery.MONSTERS` off) are no longer in
  the sea; what calls them up is not designed yet. Which kinds count as monsters is Claude's reading (the mermaids,
  kelpies, mosasaur and other marine reptiles are still stocked). The real topography: `tools/bay_real.gd` previews
  GMRT's grid of the bay (MBARI multibeam, about 60 m a sample; the download URL is in the tool) fitted to the game at
  180 real m a game m and depths squeezed by `game_depth`; it replaces MONTEREY.md's "real bathymetry: rejected".
  Built the same day (below).
- **Decision: the real bay** (2026-11-18; the user picked "whole bay as shown" and "real shape, tuned for play"). What:
  `tools/bake_bay.gd` bakes GMRT's grid (lon -122.25 to -121.75, lat 36.48 to 37.0; the curl line is in the tool)
  into `data/monterey.bin` (depth and shore distance every 1 m, 630 KB; the web export includes `data/*.bin`), and
  `Bay` reads it in place of its drawn shapes (its public names are kept; `K` is 1). 180 real m a game m, 244 x 320 m;
  depths squeezed by `game_depth` (true to 10 m, 100 m real is 25, 2,000 m is about 100). Tuned for play in the bake:
  canyons widened 2 m, smoothed (GMRT's survey seams showed as steps once squeezed), the near shore eased (5 m deep
  14 m out, no steeper than 0.6 to 25 to 40 m out, but a canyon dropping far below that keeps its depth). Over it, in
  `Bay`: Elkhorn Slough's channel, the harbours, and the three shelves (uneven sides, never right up to a shore; the
  liner's is long along its hull). Everything placed moved to its real place (Sea's ZONES, set pieces, markets,
  START; Scenery's docks, outcrop, pier, eels; Biomes' areas; FloorTypes' rocky points; Fishers' nets and loops):
  the liner on a ledge at the head of the Carmel Canyon (the real coast there drops 60 m within metres), Atlantis in
  the canyon's deep reach west of the bend, the pirate ship on its north rim, Monterey's docks east of the wharf
  off Del Monte (wharves run only north or south, and there the shore faces north), Carmel's pier at Stillwater
  Cove, the kelp off Point Pinos to Cannery Row and off Capitola, the grass off Seaside. The old wall of cliffs along
  the drawn shelf edge is off (`Scenery.CLIFF_WALL`). The practice: a real DEM resampled to the game's grid, with
  vertical exaggeration/compression and hand fixes over it, as games built on real places do. Alternatives: the
  old hand-drawn sum (the user asked for real topography), the real depths unsmoothed and unwidened (the canyon
  head and slough are under a game metre wide), a bigger map (the user chose this size). Tools: `tools/bay_chart.gd`
  (the floor with a 20 m grid, `--zones`), `tools/bay_probe.gd` (depth and shore at points). Not yet tuned to the new
  floor: the floor painting (`FloorTypes`: blocky 2 m patches, rock over every steep wall, which the real canyons
  make much more of), the biomes' depth bands, the land's look; nobody has swum it.
- The user, of the first real-bay map: "atlantis shouldn't just be a giant crater, same with the reef, and we need to
  work on a way to make the trench cliffs look good, stretched terrain looks bad". So: set pieces stand on the floor's
  own depth where it is flattest (`tools/bay_probe.gd --flat=`), levelled only by the difference, with uneven sides
  (`Bay.shelf_weight`, its spread capped) and never right up to a shore. Atlantis: the deep basin's flattest ground,
  93 m down (it now needs the 100 m amplifier; it was 42 m on a raised terrace). The liner: first moved to the level
  shelf off Pacific Grove (the user's pick of three), then the user: "The ship should be off the coast of carmel not
  in the kelp forest". The floor off Carmel is the Carmel Canyon's head (`tools/bay_probe.gd --fit=` found no hull
  placement under 30 degrees there), so it lies along the coast between Cypress Point and Point Lobos, 40 m down
  (needs the 50 m amplifier), on a broad spur raised for it. Then the user: "The liner should sit across the carmel
  trench top like a bridge". Now it spans the Carmel Canyon's head nearly north-south (heading 0.13, middle (6, 124)),
  its ends on the two rims 33 m down, the canyon open under its middle to 60 to 70 m (`tools/bay_probe.gd --span=`
  found it: the rims within 0.3 m of each other). The ends rest on two small seats, `Bay.WRECK_SHELF` (north) and
  `WRECK_SEAT_SOUTH`, whose 7th item makes a shelf fill only (never dig), level under what rests on it.
- **The trench is the user's drawing after all** (2026-11-18, current; latest of the notes below): of the overhead
  traced from their lines the user said "This had the best layout", so `tools/bake_bay.gd` is back to
  `USE_TRENCH_MASK` on and `WIDEN` 2 (`data/monterey.bin` is byte for byte 0835d1c's). On that chart they also moved
  the liner west along the Carmel Canyon ("The liner needs to be further off the coast"; then "There should be a
  canyone leading up to carmel like the overlay I drew"): it now bridges the drawn Carmel Canyon at (-37, 126),
  north-south, its ends on the rims 26 m down, about 90 m under its middle, 40 m off Carmel. And the start, circled
  by the user: `Sea.START` (-65, -42), on the shelf south-west of the pirate ship; the seal rock (`Scenery.OUTCROP`)
  moved to (-50, -86) so the title boat's circle clears it by 8 m.
- **The peninsula: growing it went wrong, undone** (2026-11-18). The user: "The peninsula needs to be a little
  bigger"; Claude moved the Monterey Peninsula's coast 6 m out evenly (`_grow_peninsula`), which filled Carmel Bay
  and rounded the points; the user: "Nope you totally ruined the shape of the peninsula". It is off
  (`PENINSULA_GROW` 0; the floor is byte for byte as before) and Carmel's pier, harbour, market, beach and reef are
  back. Lesson: an even offset of a coastline loses its bays and points; if it is to be bigger, scale its shape, and
  show a picture before building it. Then redone that way, approved ("The bigger peninsula looks good"): the bake
  reads the floor round the peninsula from a copy scaled `PEN_SCALE` (1.15) from where it joins the land
  (`peninsula_source`: inside an ellipse, blended out to 1.4 times it, so the trench, the liner and Monterey's
  docks barely move). What was placed by its coast moved by `peninsula_target`: Carmel's pier, harbour, market,
  white beach and reef, the south kelp and its arch.
- **Art style brief** (the user, 2026-11-18: "The cover art of the nick of time by ted bell should be mentioned (or
  that style) in the art style brief"). Gulp's look: stylized low-poly with hand-painted baked textures (Twilight
  Princess / Abzu) painted in the manner of a classic boys' sea-adventure novel cover like the cover of Ted Bell's
  Nick of Time: rich warm painterly colour, dramatic light, old-fashioned nautical adventure. Style and mood only:
  never copy that cover's picture, characters or text. Every concept prompt says it (in words; the image generator
  is not shown the cover).
- **Biome concepts** (2026-11-18, made in the set-pieces Gemini conversation, in that style):
  `tools/art_src/concept_biome_kelp.png` (golden giant kelp groves to a canopy with a sea otter, sand channels
  between rock ridges, garibaldi, rockfish, urchins; `_kelp_v1.png` is the first try before the style brief,
  retired), `concept_biome_dunes.png` (rolling rippled dunes with sand streaming off the crests, caustics, garden
  eels, sea pens, a half-buried anchor and chain, sardines overhead, a shark in the blue: open and exposed),
  `concept_biome_grass.png` (eelgrass meadows leaning in the current, sandy paths through them, seahorses, bat rays,
  a leopard shark, crabs), `concept_biome_crags.png` (leaning pinnacles and sea stacks under a rock island, pink
  coralline, white plumose anemones, sea stars, urchins, a moray, a seal, the pirate ship among the rocks).
- **Biomes the user drew** (2026-11-18): "We need to make proper biomes, with concept art for each considering our
  needs. Green is kelp forest, yellow is sand dune sea, red is sea grassy fields, purple is rocky crags" (coloured
  outlines over the overhead chart, kept as `tools/art_src/user_biome_lines.png`); then "This trench needs to be
  enlarged and then the green section should be kelp forest not dune sea" (`tools/art_src/user_trench_soquel.png`);
  and, when Claude began tracing the colours pixel by pixel: "You shouldnt be that exact just look at the map and see
  the areas I was trying to highlight". So `scripts/biome_regions.gd` (BiomeRegions) holds rough outlines read off
  the drawings by eye, world metres, kelp over dunes where they overlap (`at`, `weight`); `tests/overhead.gd
  --biomes` draws them. The Soquel branch of the trench is wider (`bake_bay.gd` `TRENCH_ADD`). Built since:
  the next note.
- **The eight biomes are built** (2026-11-18; the user added "Trench, beach shallows, and river need to count as biomes
  as well, and the reef on the ship", and an estuary meadow at the river mouth). `BiomeRegions` is the one source of where
  each is (kelp, dunes, grass, crags as drawn; trench by depth; beach the shore strip; river the slough and its mouth;
  reef round the liner), on Bay's 2 m grid; `Biomes.TABLES` has one table each (the old circle places are folded in),
  `FloorTypes` paints each one's floor, `Bay.dune_height` shapes the dune sea, `Sea.ZONES` kelp/sand/grass/crags place
  animals anywhere in their region. New kit piece: white plumose anemones (`tools/build_plumose.py`). Each biome, its
  rules, budget, decisions and what is rough: tools/BIOMES.md, "The eight biomes". In-water pictures:
  `tools/bay_shot.gd -- --biomes [--only=<name>]`; the chart: `tests/overhead.gd -- --biomes` tints every biome.
- **The eelgrass is Warren's grass spawning now** (2026-11-18; the user asked "Is the grass using our warren grass
  spawning system?" and answered "Yep" to bringing it into GameCommon `sea-grass`). Each "grass" layer in
  `Biomes.TABLES` (the grass biome, the river) is a `SeaGrassBed.field` over its place's box (`Biomes.grass_fields`:
  the layer's own rules as a mask, the floor from `Sea.ground`), filled square by square as the eye nears, thinned with
  distance and sunk into the floor at the far edge (no hard cut at 40 m); quality follows `Sand.quality`
  (`Scenery._plant_grass`, `GRASS_DENSITY`). The player and the three fish nearest it lay it aside (`Scenery.life`). The
  placer no longer walks the grass grids, so every later layer's random draws shifted: the same rules, other spots.
  `tools/bay_shot.gd` fills the grass before each picture; its grass views look at `GRASS_SPOT`. Decision record:
  GameCommon's `godot/sea-grass/README.md`; numbers: tools/BIOMES.md, "The eight biomes".
- **The kelp forest made dense** (2026-11-18, the user: "The kelp forest needs to be much denser look up real images to
  reference and try to match that look and vibe"): about 700 giant kelp plants in place of 275, each drawn 1.3 to 1.9
  times as wide, columns about 2 m apart with lanes; amber colours; teal water, a green surface and stronger shafts
  inside the forest (`Sea._kelp_at`, `Sea.post_tint`); a far level in GameCommon's kelp (`KelpForest.far_piece`) and
  blades dithered away near the camera (`eye_clear`). The reference, numbers, budget and decision: tools/BIOMES.md, "The
  dense kelp". All Claude's picks.
- **A second rocky islet** (2026-11-18, the user: "lets add another rocky outcrop island just south south west of the
  pirate ship to fill in that empty spot a bit as well"): `Scenery.OUTCROP_SOUTH` (-74, -14), built by the same
  `_build_outcrop` (now taking its middle, a name, the islet's turn and whether seals lie on it: these have none;
  Claude's pick) with its own growth (`Biomes` "outcrop_south", a copy of the outcrop's).
- **The pirate ship moved** (2026-11-18): on the overlay the user's red line ran from the pirate ship to a circle;
  Claude first read it as moving the start; the user: "why havent you moved the pirate ship like I showed in the
  overlay". `Sea.PIRATE_AT` (-65, 19, -42) and its hollow, the seal rock (`Scenery.OUTCROP` (-93, -52), off its west
  end as before), and the start back at (-40, -55), east of it.
- **Terraced trench** (2026-11-18, the user: "the trench needs to be carved out with terrace like steps, no just one
  huge cliff"): inside the drawn trench the floor may be no deeper than `_steps(distance in from its edge)`: every
  `TERRACE_WIDE` (6) m in, a `TERRACE_STEP` (14) m drop, flat for the first `TERRACE_TREAD` (0.6) of it, then a steep
  riser (the wall-rock shading paints the risers as rock, the treads as silt). By distance, not depth: the real
  walls drop 60 m in a few metres, where depth-steps came out a metre wide (tried first, kept unused as `_terrace`).
  The trench is shallower for it in its narrow parts (the main canyon by Moss Landing about 53 m at x 30, the Carmel
  Canyon under the liner about 38 m); the broad south-western basin still reaches 95 m. Outside the trench the floor
  is raised to 26 m right up to its edge (an ease there left a moat). Same message: "the ruins need to be way further
  out in the deepest part of the trench", circled at about (-60, 53): passed to the Atlantis builder.
- **Atlantis is built into the stepped walls of that basin** (2026-11-18; the user: "The Atlantis ruines area
  shouldnt just be a big open flat area, it should be built into the trench sides", then the circle above; concept
  `tools/art_src/concept_atlantis_canyon.png`). `tools/RUINS.md` has the layout, depths and decisions. In short: ONE
  table, `data/ruins_layout.json`, says where every building, ledge and stair is; the model's build
  (`tools/build_atlantis_canyon.py` -> `models/atlantis_canyon.glb`, about 15 minutes with its bake),
  `Bay.ruins_ledges()` (small ledges under each, never a flat disc; `Bay.RUINS_TERRACE` is gone) and `Ruins` (routes,
  `covers` for the plants) all read it. A ledge `cut`s (only lowers the floor: round a rock-cut front's chamber),
  `fill`s (only raises it: behind each rock-cut front, burying its box of rock in a cliff) or levels `both` ways
  (terraces, stairs, the tread before each front): the floor itself carries each terrace and stair as a tread of the
  wall (masonry footings hung from them looked like curtains, the fronts' boxes like slabs).
  Fills are kept square to the world's axes: a diagonal one came out saw-toothed on the floor's grid. After a floor
  rebake or a table change: `tools/ruins_ground.gd`, the build, `--import`, `tests/setpiece_hits.gd -- --fit-ruins
  --no-ruins-extra`, then `tests/ruins_view.gd -- --check`. Every building stands on one of the trench's treads: the
  gate and the temple on the north rim (26 m, the temple jutting over the drop on a crag), the bridge across the
  canyon's mouth and the crystal on the east rim at 40, the colonnade and its rock-cut front at 54, the pyramid half
  into the east wall at 68, rock-cut fronts at 70 (south wall) and 82 (foot of the north wall), the fallen head on the
  basin floor at 96 (needs the 100 m amplifier). The first, flat Atlantis (`build_ruins.py`,
  `atlantis_ruins.glb` and its atlases, `ruins_extra.json`) is retired, unused; its helpers are still run by the new
  build.
- **Skinnier canyons** (2026-11-18, superseded by the note above). The user drew rough lines over the overhead chart ("The trench area
  needs to be skinner, just showing roughish boundaries"), and the first try traced them (below); then: "I didnt want
  it to be based exactly on my rough drawing just meant trench needs to be skinnier". So the bake now keeps the real
  canyons' courses and narrows them: no widening (`WIDEN` 0, was 2), and below `NARROW_FROM` (24 m) the first `LIFT`
  (14) metres of every wall are lifted to the shelf, the rest stretched back down to 106 m (`_narrow`): the gentle
  upper walls become shelf, the canyons narrow, steep cuts. The drawn mask is off (`USE_TRENCH_MASK`), its files kept.
  The liner re-seated over the narrower Carmel Canyon: (4, 122), heading 0.26, ends on the rims 20 m down, about 50 m
  of water under its middle.
- (Superseded) **The trench as the user drew it** (red lines kept as `tools/art_src/user_trench_lines.png`). `tools/trench_mask.gd`
  turns the lines into `data/trench_mask.png` (1 m a pixel): it joins their loose ends to the shore or the map's edge
  (`CLOSE`, Claude's reading), fills the deep water from `SEEDS` (the canyon, the Soquel branch the user drew, the open
  west, the deep south-west, the Carmel Canyon) and keeps it out of the slough. `tools/bake_bay.gd` then raises the
  floor outside the mask to the shelf (26 m) and inside cuts at least a wall 3 m down a metre from its edge (so the
  Soquel branch, shallow in the real floor, is a canyon), never within 12 m of a shore. Re-run both after changing
  either. Reading of the drawing (Claude's): the west of the map beyond the north line is deep open water, as is the
  south-west between the lines; the south of the Carmel Canyon's south line is shelf. The liner now spans the narrow
  Carmel Canyon at (6, 119), its ends on the rims 25 m down (it needs only the 30 m amplifier now).
- `tests/overhead.gd` now tints the land and draws the shoreline in cyan (the user: "Need too see where the shoreline
  is on the map").
- **Decision: rock walls** (the cliffs). What: steep floor (`wall_from`/`wall_to` on 1 - the normal's y) is painted
  as rock from the sides in the sand's shader (`Sea.WALL_ROCK`/`WALL_MIX`, put into the sand's code as the caustics
  are): level beds that waver, a silted lip and shadowed foot each, which also tip the light, upright joints here and
  there; the sand's ripples are taken out of the light there. And Biomes' "walls" puts three times the rock pieces
  (bigger, tinted to the wall) on rock steeper than 0.5. Why: the sand is painted from above, so a heightfield's
  walls stretched it into bands. The practice: triplanar texturing on steep terrain plus rock meshes over the cliffs
  (the usual heightfield cure; Star Wars Battlefront blends scanned rocks into its terrain shader the same way).
  Alternatives: real cliff meshes along every wall (the kit's 12 x 16 m cliff pieces: they need a straight edge to
  run along, and the canyon's walls wind), a finer grid (stretches less, never fixes vertical faces), voxel terrain
  (far too heavy for phones). Concept: `tools/art_src/concept_canyon_wall.png` (Gemini, 2026-11-18): blocky stepped
  ledges, rubble at the foot, silt on every ledge; the shader matches its beds and silt; its chunky overhanging
  blocks are only as good as the scattered rock pieces so far.
- `tests/overhead.gd` draws the whole bay from straight above as a labelled chart (no water, fog or culling; tiles
  stitched): `godot --path . --audio-driver Dummy --resolution 400x400 -s res://tests/overhead.gd -- --out=<folder>`.
- **The web pack** (62.5 MB -> 33 MB): `tools/web_excludes.sh` also turns off automatic LODs and shadow meshes in every
  creature model's import (they were half of each model's weight; nothing here casts shadows and the creatures never
  used their LODs, but schools and clouds keep theirs), and leaves out the concept art, the retired rocks and the retired
  flat panel's pictures. The wreck, pirate and ruins atlases are imported lossy with mipmaps, the liner's bow atlas at
  2048 (from 4096): the game draws at half size, where 4096 showed only within a couple of metres of the hull.
  After running it, `godot --headless --path . --import`, and commit the changed `.import` files before exporting from
  `../Gulp-build`.

### More asked on 2026-11-18 (late), the user's words

- (with the cover of Ted Bell's novel Nick of Time) "Nick of Time by Ned Bell is part of the inspiration, and the art
  on the cover- the boy needs and old timey sailor boy outfit": mood only, nothing copied. Concept:
  `tools/art_src/concept_sailor_boy.jpg`; a builder is changing the boy in `tools/build_title_figures.py`.
- "there should also be a submarine" (concept `concept_submarine.jpg`; GameCommon `submarine`, being built) and
  "and remoras" (GameCommon `remora`, being built; it needs to ride sharks, rays and whales: not written).
- "w4e also need to come up with leviathan, sea monster, cthulu old one, and godzilla like designs": concept
  `concept_monsters.jpg`; GameCommon `leviathan`, `sea-serpent`, `old-one`, `reef-back`, being built. They are our own
  designs: the last two must never be made to look like Godzilla or any published Cthulhu.
- "the boy should also have a diving suit that you can play as to walk along the sea floor": not started (a new way
  to play: needs a concept, a design and the character controller question solved, see the title figures note).
- Landed since the list above: the Monterey map and docks, schooling and habits, water effects with day and night, the
  boat's quality pass, the fish logo (`scripts/title_logo.gd`; the picture logo is retired).
- An idea, not yet a request ("Thinking about adding a mode where you return tomo, the boatm as the most valuable fish
  you can become- you sell fish for money to unlock better / deeper diving equipment so that you can open chests /
  look for your lost treasure plot"): a run ends by swimming back to the boat; the fish you have become is sold; money
  buys diving gear that goes deeper; the boy in his suit walks the floor to open chests and follow a lost-treasure
  story. It would tie together the diving suit, the roguelike elements, the evolution tree and the set pieces
  (liner, pirate ship, Atlantis). Nothing built; ask before building.
- The sonar shows height (2026-11-18): a blip above or below the fish is an arrowhead on a stalk (`Sonar.high`).
  The smoke test's "pack hunters at a swarm" check failed once in three runs: it is flaky, not yet looked at.
- Another idea in the same breath ("and there could also be a regular fishing mode rather than only the odell down
  under"): fishing from the boat with a rod as a second way to play, feeding the same sell-for-money loop. GameCommon
  has a `fishing` component to start from. Nothing built; ask before building.
- "ther eshould be mermaids, kelpies/ hippocampus, old ones fish spawn creatues of the deep, skeleton ghost whales
  and other ghost fish", "and spinosaurus", and (with a picture of a signed drawing: a shaggy brown-furred beast
  standing upright with a caiman's head, clawed scaly hands and feet and a broad scaly tail) "and whatever this is":
  not started; concept first. The last is someone's artwork: make our own furry crocodile-headed river beast in that
  spirit, never a copy of the drawing.
- "the control ui also needs an alarm that starts flashing when a chasing fish gets close": done (a red lamp on the
  scope's head in `build_panel.py`, markers Alarm/AlarmEdge; `TouchPad.alarm`, set in `Main._sound_out`). The antenna
  is shorter. The water is green-blue near the top and deep blue by 35 m down (`Sea._look`, Claude's pick).
- "yes make the design and implement it" (the treasure mode above, 2026-11-18): the design is `DESIGN.md`.
- The Wayside Interactive logo for the loading screen is in `C:\Projects\scareathon\trailer\wayside-logo\out`
  (`png/WaysideInteractive_mark.png`, `_seal.png`, `_stacked.png`, and the animated sequences as mp4).
- "he should be a gay captain"; "captian should have bushy chest hair and tattoos" (2026-11-18): the captain's
  love in the photographs is a man (DESIGN.md "The photographs"); his figure gets an open shirt, chest hair and
  old sailor's tattoos (concept first, then `tools/build_title_figures.py`).
- Concept art, the user (2026-11-18): "use the previous concept arts as part of the prompts for new ones for
  character consistency". So a new picture of a character or thing that already has a concept is asked for IN THE
  SAME Gemini conversation as its earlier picture, naming that picture as the reference ("the same captain as in the
  sheet above, changes only: ..."), or with the earlier picture attached. The figures' conversation is
  gemini.google.com/app/62f2ff6ee62c21f9 (the boy, captain and diver sheet, the boat); the set pieces, sailor boy,
  diving suits, monsters and creatures are in /app/d2fe19426ff0ebc4. Check a new sheet still has the mask faces (no
  eyes or mouth): a fresh prompt drew the captain with eyes.
- The loading screen is built but NOT yet shown by the game: `scripts/loading_swarm.gd` (LoadingSwarm: set `progress`,
  call `finish()`, wait for `done`), seen alone with `tests/loading_view.gd`. To wire in: show it over everything from
  the first frame, feed it the warm-up's share done (`Main._warm`), finish it when the title is ready. The captain
  also gets "a tasteful bulge" (the user), passed to the figure builder.
- The loading screen uses the real sardine (the user: "it needs to be actual sardines making the wayside logo in the
  loading"): `Sardine.school_mesh()` WITHOUT its automatic LODs (seen small, Godot drew the crudest one: a few spikes),
  in a SubViewport world of its own with the schools' shader; the round mark only is made of fish (about 700), the
  lettering is the logo's own, shown as they settle (Claude's pick: the letters are too fine for fish that read as
  fish). The two smaller logo copies in textures/loading (`_small`, `_116`) are retired.
- "yes the arena should still be part of the fish control aspect" (the user, 2026-11-18): the online arena stays,
  inside the fish runs of DESIGN.md.
- "the captain should have the outfit from teh first concept as well to switch into" (the user, 2026-11-18): two
  outfits on the captain (the first sheet's closed coat, and the open coat with chest hair and tattoos), switchable in
  `scripts/title_figures.gd`; nothing in the game switches it yet.

## The treasure loop, stage 1 (2026-11-18): money, the net and the sale, the shop, the depth limit

DESIGN.md's "Order of building" item 1, built at the user's "yes make the design and implement it". Plain screens;
stage 2 rebuilds them in brass, so each is its own script with a small interface.

- `scripts/purse.gd` (Purse): money, the amplifier's step, kinds sold, treasure pieces (unused), the longest fish, in
  `user://gulp.cfg` (the old `[best] length` is read and written as before). `path` empty keeps it in memory: Main does
  that whenever a test, the bot or a picture drives. The checks write `user://gulp_check.cfg`.
- Worth (`Purse.WORTH`, money a metre, a table of its own, not in Species): sardine 8; flying fish 18, mackerel 16,
  smolt 18, surfperch 16; bonito and barracuda 24, salmon 28, kelp bass and rockfish 26; snapper, leopard shark and
  grouper 36, tuna, mahi and wahoo 40; sea bass 50, blue shark 55, bluefin and sailfish 60; swordfish 80, marlin 85,
  white shark 90; orca 120 (the old code-built shark 50). Price = worth x length (rounded), x2 for the last of a line
  at full length (`Player.is_biggest`), plus a first-sale bonus of one metre's worth (`FIRST_METRES`).
- The amplifier (`Purse.AMP_DEPTH`/`AMP_PRICE`): 15 m (had from the start), 30 m for 30, 50 m for 150, 100 m for 600.
  The start is about 20 m deep, the shelf 20 to 24 m, the canyon 45 to 75 m. A salmon at 0.72 m fetches 48 the first
  time; a full sardine 11 and a mackerel at 0.48 m 24 (so one or two small sales buy 30 m).
- The boat stays: once the dive starts, `Title.heave_to` stops it where it is (tests and pictures: hove-to 4 m south
  of `Sea.START`), and its net (`tools/build_boat_net.py` -> `models/boat_net.glb`: a 0.8 m steel hoop, a 2.4 m net
  bag drawn two-sided with `shaders/net.gdshader`, a 12 m line to the starboard outrigger's end, measured off the boat
  at (3.41, 8.39, 1.78): the hoop is 3.6 m under) hangs out. While hove-to, the figures, computer, bench and cables
  are drawn only with the eye above water within 45 m. The sonar shows it as "boat" (`Sonar.LANDMARKS`).
- The sale: the fish's mouth within 0.9 m of the hoop's middle (or 0.4 of its length, for big fish), after the run has
  gone 4 s (`Main.NET_*`), ends the run (`Player.haul`, not `died`). `scripts/sale.gd` (Sale: `show_receipt`, `done`)
  shows the animal, length x worth, the crown x2, the star bonus, the sum and the purse; its arrow (Enter, Space, A)
  opens `scripts/shop.gd` (Shop: `open(purse)`, `bought`, `dive`): the four steps, the next one pressable when it can
  be paid (or B); its down arrow (Enter, Space, A) starts a new run and sends the eye down from the boat
  (`Main._dive_again`, the title's dive). The bot skips the screens and swims again.
- The depth limit: `Player.deepest` (from the purse): below it the fish is turned nose-up (whatever the stick says) and
  is never let more than `Player.LIMIT_GIVE` (3 m) deeper. The post shader's one new uniform `signal_loss` draws the
  static, from 3 m above the limit to full 2 m below. The depth dial's full scale is now the limit (its needle at the
  stop = the limit). `Main.limited` (the smoke checks turn it off but for their own check).
- Tests: four checks at the end of the smoke test (the net ends the run as a sale; the right sum, saved; the bonus once
  and the doubling; buying a step; the new run from the shop with the new limit; static and turned back) and three in
  the touch test (the sale's button, a step, the shop's button, all by touch). Pictures: `-- --as=tuna --sell` or
  `--shop` with `--shot`, `--near=boat` looks at the net, `--near=trench` shows the static.
- Claude's picks: every number above; the worth table being Purse's; the shop showing only the amplifier (the suit,
  anchorages, tools and tackle are left out until the stages that use them); dying still goes to the old "again"
  button, not the shop (so money can only be spent after a sale); the boat stays where the first dive started (it
  can stop anywhere on its title circle); the name of the kind written under it on the sale screen.
- Rough or unverified: nobody has played the loop by hand; the arena does not know about a sale (the player just
  vanishes for the others); the `--dive` picture argument now waits until the start button is ready.
- "we might add a manual sailing minigame where you conrtol the captain" (an idea, 2026-11-18: not designed or built).
  "the diver is the older brother to the vr kid" (the user): the diver on the boat is the boy's older brother.
  "and make the concpet art for other outfits as well, and make sure to capture his staunch proportions": the
  captain's outfit sheet is `tools/art_src/concept_captain_outfits.jpg`.
- In the sea: `leviathan` (a harmless giant, open ocean and canyon) and `sea_serpent` (a stalker, open ocean); both
  wear one shared shader, `creatures/sea_monster/sea_monster.gdshader` (a copy ships with each component: keep them alike).
- The captain (the user, 2026-11-18): "make concept art of the captain tposing for the model to be based on"; "he
  looks a little to tall and lanky so far"; "he should have hear shaped boxers pose so you can add clothes on top"
  (a base body in heart-print boxers, outfits modelled over it); "his eyes should just be wrinkly slits" (not the
  blank mask: creased squints, no eyeballs). "their boat needs an antenna sticking off the bottom from the vr
  machine": done in `tools/build_shrimp_boat.py` (marker `Aerial` at its tip).
- Gemini's image limit ran out at about 3 AM on 2026-11-18 ("Limit reached, resets 3:15 AM") after some twenty
  pictures: the captain's T-pose base-body sheet (heart boxers, slit eyes "added on as afacial feature", stout build)
  is still owed as `tools/art_src/concept_captain_tpose.jpg`; ask for it in the figures conversation. Clicking a
  download button on a picture that failed to appear opened Google's upgrade page instead: check the picture is
  there first.

### Asked in the small hours of 2026-11-18 (the user's words) and where each stands

- "no we need the tpose" (the captain is built from his T-pose sheet, not the other sheets); "do it once the reset
  lifts". "yes do a performance pass and then push everything" (the pass: `tools/PERF.md`, a builder; then the push).
- "you should create a writing room agent to fill in the plot based on what you know of my art projects and the
  pictuers should be \"in game\" sepia"; "there should be other plots written up too, and tother things to find on the
  sea floor (not just pics other treasure)": `STORY.md`, being written. The photographs are staged scenes captured by
  the game's own camera and toned sepia, not generated pictures.
- The family: "the diver is the older brother to the vr kid"; "the older brother is a budding handsom curly dark
  haired sailor about 19, the younger boy 13 and eager and fresh blonde, captain is their gay grandpa".
- "the fish markets should be at monteray, santa cruz, and carmel": the sale belongs at three markets (stage one sells
  at the boat's net: to be changed; Carmel is by the liner at the south).
- "the boy and older brother need oufit concepts and tposes etc"; "maybe try a pass with faces although it would need
  to by twilight princess style maybe": concept sheets owed for both brothers (outfits, T-pose base bodies) and one
  trial sheet of the three with Twilight Princess-style faces. Not started (image limit).
- "also do a quality pass on clipping adn hit boxes"; "and make sure things have textures that fit our art style": a
  quality pass owed after the performance pass (which is changing the collision grid): every model checked for
  clipping, every swimmer-stopping shape against what is seen, and every surface's paint against the baked brass and
  painted look of the panel, the wrecks and the creatures (the boat and its figures are still plain materials).
- Landed: the sailor boy (`models/title_boy.glb`, hair in GameCommon ink-figure's `hair_ink.gdshader`, copied to
  `shaders/ink/`); the captain's open and closed outfits on his OLD too-tall body (`TitleFigures.wear`), to be redone
  on the T-pose body; the submarine and remoras in the sea (`creatures/submarine`, `creatures/remora`).
- "and the foliage needs a smart realistic distrbtion, do research on kelp forests and othe under sea biomes and make
  good game design \"levels\" out of them as we've described them so far" (the user, 2026-11-18): research and a level
  design for every place is being written to `tools/BIOMES.md` (phase one: no game files changed); building it
  (a rule-based placer in place of `scripts/scenery.gd`'s scattering, new kit pieces) follows the performance pass.
- Installed but NOT yet placed in the sea (2026-11-18): `creatures/old_one` (OldOne: a sleeping set piece about 50 m
  across, `wake` 0..1 set by the game; to stand in the canyon basin by Atlantis with `Sea.add_rock` spheres) and
  `creatures/reef_back` (ReefBack: 35 m, walks on a skeleton with baked clips, `step(velocity)`; to walk a slow loop on
  the deep floor). Their builder's placing notes are in each component's README in GameCommon. Each has its own shader.
- "the older brother is the one who does the regular fishing so he needs outfits for that" (the user, 2026-11-18):
  the fishing mode is played as the older brother (rod from the boat), so his outfit sheet includes fishing rigs
  (oilskin bib and braces, waders, a gansey, a hot-day rig) beside his diver's dress; he tends the boy's air pump on
  the title as now.
- CORRECTION (the user, 2026-11-18): "no the older brohter is the walkerin the diving suitt bruh". The OLDER brother
  (19, dark curly hair; the diver on the title) walks the sea floor in the diving suit AND does the fishing; the
  younger boy (13, blond) is only the fish. Claude had written the younger boy as the diver, from the user's earlier
  "diving as the boy". `tools/art_src/concept_diving_suits.jpg` shows the suits on the younger boy: redo them on the
  older brother. DESIGN.md has a "Who does what" section.
- `STORY.md` (2026-11-18): the writing room's story bible: the captain's love story as twelve photographs and a
  thirteenth taken at the ending, eight side stories, a catalogue of things to find, the three markets, staging briefs
  for capturing each photograph in the game in sepia, the new models it needs, and twelve questions for the user.
  ALL of it is a proposal (names included) until the user has read it: nothing in it is the user's decision yet.
- `tools/BIOMES.md` (2026-11-18): the level designer's research and a level design for every place (phase one, no game
  files changed). Its findings: the floor is one pale sand everywhere; kelp stands on sand in even clumps; the liner's
  reef is scattered confetti; zones are circles that spill where things cannot live; dock piles are bare. Its five
  changes: a floor-type map on the 2 m grid; one rule-based placer (`scripts/biomes.gd`) in place of scenery.gd's
  loops; kelp as rock reefs with sand channels, canopy, understory and an urchin barren; growth placed on structures;
  kinds limited to their depth and floor. Building it is phase two, after the performance pass. It asks the user:
  liner depth against the suits; what Carmel's market is modelled on; garden eels, mangroves and sargassum against
  realism; a warmer tint for the coral pocket.
- Modelling sheets now in tools/art_src: `concept_captain_tpose.jpg` (base body), `_tpose_clothed`, `_outfits`;
  `concept_brother_tpose.jpg` and `concept_brother_outfits.jpg` (four fishing rigs, four diving suits: these replace
  `concept_diving_suits.jpg`, which drew them on the younger boy); `concept_boy_tpose.jpg`; a trial with faces is
  `concept_faces_trial.jpg` when made.
- THE STORY, the user's corrections to the writing room's first version (2026-11-18, fixed): "the captain should have
  been in the navy and thats where he met fell in love, not named teo (they are white italian and irish scottish),
  the boys are his biological grandkids, the captain and his buddy didnt truly didnt get together until later after
  captains wife dies". STORY.md is being rewritten to this; its first version (Teo the inventor, the baby from the
  liner, a loss in 1898) is superseded.
- Faces (the user, 2026-11-18): "I like the face concept art but can the models look that good? remember twilight
  princess"; told it could reach that standard by a painted face texture projected from the concept, and offered a
  test on one head: "lets try it". The captain's rebuild includes a painted-face head beside the mask-with-slits head
  (`concept_faces_trial.jpg`); the brothers wait on the user's verdict.
- How a figure is checked against its modelling sheet (the user, 2026-11-18): "make sure to overly the model onto the
  tpose until it looks right". Render the model orthographically in the sheet's pose and scale and lay it half-clear
  (and as an outline) over each view of the sheet; fix and repeat until the silhouettes agree. This is the standard
  for the captain and for the brothers after him.
- "and if you need more poses for concept art ask for them" (the user, 2026-11-18): builders are to ask for any view
  they lack (a level-armed T-pose, head turnarounds, hands, seated) rather than guess; Claude generates it in the
  figure's own Gemini conversation.
- More captain sheets (2026-11-18): `concept_captain_head.jpg` (head turnaround, five views), `concept_captain_closed.jpg`,
  `concept_captain_hands_wheel.jpg`, `concept_captain_tpose2.jpg`. The generator will not draw level arms: two tries at a
  true T-pose both came out with the arms hanging low, so figures are built and overlaid in the sheet's own pose.
  Gemini's limit: about ten pictures, then a five-hour wait (used up again at 3:34 AM, resets 8:15 AM).
- The older brother's look (the user, 2026-11-18, with nine reference photographs of real men, used for general look
  only, described in words: never uploaded, never copied into the repo, no one man's likeness): a thick tousled mop of
  curls, shorter at the sides, falling on the forehead; a broad open face, strong jaw, thick neck, light blue-grey
  eyes, a big easy grin; a real moustache with stubble (a short full beard as a second look: Claude's pick); a big
  athletic build with heavy forearms and old-style forearm tattoos. Hair colour, the user: "it should be dark hair but
  amberish red in the right light" (dark brown curls with amber-red lights where the sun catches them). His sheets
  made earlier (`concept_brother_tpose.jpg`, `_outfits.jpg`) predate this and are to be redone after 8:15 AM.
- "Dont try to model the beard it should be made with a hair shader" (the user, 2026-11-18): beards, moustaches and
  head hair on the figures are locks drawn with the shared hair shader (`shaders/ink/hair_ink.gdshader`), never a
  sculpted mass and never painted onto the face texture. Applies to the captain now and both brothers after.
- More Twilight Princess figures to measure against (the user, 2026-11-18: "I downloaded some more references models
  for you to compare to"), in `C:\Users\stewa\Downloads` as zips: Non-Playable Characters - Hylian Knight (2,533
  triangles, body texture 512x256), Telma (2,308; 256x256 plus small face tiles), Shad (2,663; 512x512 plus tiles),
  Ordona. Look and measure only; copy nothing. A whole person there is about 2,300 to 2,700 triangles with one small
  mirrored hand-painted body picture and separate small face tiles; Gulp's captain drew 10,124 in his open look.
- "the tattoos need to be moveable so we can postion them eventually" (the user, 2026-11-18): tattoos are never baked
  into a figure's skin picture. Each is its own small picture, placed by a table (which picture, where on which body
  part, size, turn), laid over the skin as an overlay that can be rebuilt from the table; a positioning tool comes
  later. The captain first, the older brother's forearms after.
- "instead of projecting hte concept art onto it we should make proper uvs no?" (the user, 2026-11-18): figures get
  planned UVs (seams hidden, a big face island, mirrored halves, a readable layout with a layout picture kept beside
  the texture), as the Twilight Princess figures have; projecting a concept sheet is only how the first paint gets
  into that layout. No smart-project UVs on figures.

### The captain's model: what failed and the method that replaces it (2026-11-18)

The user, of the rebuilt captain: "the captain model does not match the conept art", "its deformted". True of both
rounds: the body was the tall shared man's mesh warped by a bone table into a short stout shape (so it looked
squashed, not built), the hair-shader beard was flat white shingles, and the closed coat did not fit its sheet. What
did work was the HEAD, which was built from nothing, row by row, to the head sheet's silhouettes. The third round's
files are kept in `tools/retired/captain_round3/` (it holds useful parts: planned UVs, the movable tattoo table and
overlay, `TitleFigures.lay_tattoos`); the game has the earlier recorded captain meanwhile.
The method from here: build each figure's body FROM ITS OWN SHEET, cross-section by cross-section from the front and
side silhouettes, as the head was, on its own skeleton fitted to that body, never by warping another figure's mesh.
Pushed 2026-11-18: game 0864fe9, site PR #212 (the push does not include the failed captain).

## The quality pass on clipping, hit boxes and textures (2026-11-18)

The user: "also do a quality pass on clipping adn hit boxes"; "and make sure things have textures that fit our art
style". `tools/QUALITY.md` has the tables, the checks (`tests/hitboxes.gd`, `giants_solid.gd`, `camera_clear.gd`,
`floor_clip.gd`, `setpiece_hits.gd` and four picture tools), the art verdicts and what is left. Every choice below is
Claude's.

- **Decision: touch is measured to the body as drawn.** What: a mouth (`Fish.mouth()`, at the kind's `mouth` share
  behind the nose: billfish at the bill's root, squids among their arms) reaches `Life.TAKES` (0.2) of the player's
  length + 0.03 m (eating) or `Life.JAWS` (0.1) of a hunter's length (being eaten) to the nearest of the other's body
  (`Fish.gap_to`: the line nose to tail, less 0.1 of the length). Why: measured from the middles, a white shark took a
  sardine a metre off and an orca ate a fish 2.7 m from its mouth. The practice: a capsule along the body against a
  sphere at the mouth (the usual cheap hit volume for long bodies), and generous to the player (a little suction when
  eating, a strict bite when being eaten). Alternatives: per-kind boxes from the models (more data, little gain at
  these sizes), physics shapes (the game has no physics). The bot grew the same under both rules.
- **Decision: solid giants.** What: anything 1.5 times the player's length (`Life.SOLID`), unless it is hunting the
  player and could eat it, is a rounded rod down its middle 0.11 of its length thick (`Life.BODY`), and the player is
  pushed out each frame (`Life.push_off`); the reef-back's trunk is one in `Life.solids`. Why: the player swam through
  whales, the leviathan, the submarine and the reef-back. Practice: a capsule per moving body with a push-out (a
  character controller's depenetration), measured as a few multiplications for the animals in sight. Alternatives:
  spheres along each body moved every frame into `Sea`'s rock grids (re-gridding moving spheres each frame costs more
  and the grids are built for still rocks), or per-bone shapes (bodies bend; not worth it at this size). Bodies bent
  into a turn are treated straight. The old one is static and keeps its three spheres in `scenery.gd` (too few: QUALITY.md).
- **The camera** keeps out of the rock spheres and the floor (`Main._camera_clear`): it stops short along its way, or
  looks down from higher, never nearer than its fish's body. Animals do not stop it.
- **Floor animals** stand at their own drawn height (`Creature._belows`, measured when first dressed), walk on the floor
  and lie along its slope.
- **The boat and the fishing gear** have baked painted atlases (2048 and 1024), drawn LIT by the game's sun (not unlit
  like the panel: the boat turns on its circle and lives through the night above water). Other offenders, ranked, are
  in QUALITY.md (the docks and the outcrops first).
- The plant kit (2026-11-18, second biome pass): `scripts/kit.gd` and `models/kit/*.glb` (reef slabs, understory kelp,
  bull kelp, kelp canopy mats, surfgrass, sea pens, sand dollar beds, drift kelp rafts), each built by its own
  `tools/build_<name>.py` over `tools/kit_build.py`; placed by rule in `scripts/biomes.gd`. See tools/BIOMES.md,
  "Phase two, second pass" for what is built, the budget table and what is next (pile sleeves, a big plumose
  anemone for the cold wrecks, the whale fall, Carmel's fish shed).
- The captain's hair, fourth method (2026-11-18): many separate pieces (cards, strands, clumps) all read as shingles from
  the side; what works better is ONE smooth shell per mass (beard, moustache lobes, a shell under the cap) with its UVs
  laid along the growth, and the hair shader (`shaders/ink/hair_ink.gdshader`, new `locks`, `lock_width`,
  `lock_length`, off at 0 so the boy's hair is unchanged) drawing broad soft light and dark bands along it. Chest hair
  is the sheet's painting on the skin, no raised tufts. Still wrong: the shell over the ear reads as a slab from the
  side, the beard is greyer and flatter than the painting, the skin is paler than the sheet. `models/captain.glb`
  (tools/build_captain.py, tests/captain_view.gd) is NOT in the game yet; the title still uses `title_captain.glb`.
- Pushed twice on 2026-11-18 (morning): game 0864fe9 with site PR #212, then game 27495d9 with site PR #213 (the
  biome rebuild and the quality pass). Both tried in Chrome on this machine first (loading screen, title, the dive).
  First load of 27495d9 took three to four minutes there before the title showed (the title now warms about 173 more
  materials): too long; the warm-up needs to move off the path to the title. Not tried on a phone. The pack is 39.6 MB.
  The new captain (`models/captain.glb`) ships in the pack though the game does not use it yet: leave it out of the
  web export until it is wired in.
- The older brother's sheets, redone (2026-11-18, morning): `tools/art_src/concept_brother_tpose2.jpg` (base body, three
  views), `concept_brother_head.jpg` (five-view head), `concept_brother_fishing.jpg` (four fishing rigs),
  `concept_brother_diving.jpg` (canvas, hard-hat, armoured, deep suit). These replace `concept_brother_tpose.jpg` and
  `_outfits.jpg` (kept, retired). The user, of the first try: "olde bro face looks a little too mature, still needs to be
  rugged but still boyish": the kept sheets are the boyish second try (rounder cheeks, a thin first moustache, light
  stubble). He is drawn squat like the captain: the user has not said whether he should be taller. Still owed (Gemini
  dropped the request four times in a row that morning; a prompt sent right after clicking a download is lost, and a
  new picture can take 90 s before a reload shows it): the captain's side view with the arm, his beard from below, his
  hands; the younger boy's outfit sheet.
- The captain (the user, 2026-11-18, of the sheet-against-model comparison): "Looks like his face and waist need work"
  (circled: the boxers' tall flat waistband, the head from the side); "his hands / fingers also seemed scuffed"; "let me
  see the model without the textures" (in plain grey he has almost no face or body forms: the paint was carrying it).
- The captain, rounds five and six (2026-11-18, `tools/build_captain.py`, still NOT in the game): forms are modelled, not
  only painted (brow, cheeks, eye slits, lips, a bigger nose, pecs, a belly roll over the band, kneecaps; `refine()`,
  `FACE_FORMS`, `BODY_FORMS`); the boxers are their own garment with a thin low band and a procedurally painted cloth
  (clean hearts, fly, hem); head paint is taken from one sheet view at a time (no doubled features); the hands are one
  welded surface (wrist, wedge palm, short fingers grown from the palm's quads) and are kept out of the outline fitting.
  Hair shader: new uniforms, all off at 0: `root_ragged`, `side_ragged`, `ragged_width`, `lock_gaps`, `tufts`,
  `tuft_width`, `tuft_length`, `under_shade`. Check a figure in plain grey as well as painted (the user asked to "see the
  model without the textures", which showed the paint had been carrying a formless mesh). Body, head and hands: 5,626
  triangles. Still wrong: the moustache is one big pale blob and the beard a smooth plate (the hair is the stubborn
  part after six rounds); the painted hands are flat-coloured with hard seams; the eye slits are shallow.
- The user (2026-11-18, late morning): "The captain model shouldnt have a beard- we will add that on top. His belly has
  an issue its sharp, his hands still seem poor quality compared to like twilight princess hands, and his shoulders
  need a little work."; "We should make the captain model without a hat as well". So a figure's BASE model is the bare
  person (no beard, no head hair, no hat): hair and hats are separate pieces added on top (the captain's hair shells go
  to an optional `models/captain_hair.glb`, his cap is its own hideable mesh). Hands are judged against the Twilight
  Princess reference hands.
- The older brother (the user, same message): "should be the tallest of the 3, a little taller and rugby built, with a
  less pointy more rugged square face like" a named American football player (a real person: his look is used only as
  a general type, described in words: broad square face, wide jaw, squared chin, thick neck; never his name in a
  prompt, never his photo, no likeness). `tools/art_src/concept_brother_tpose3.jpg` is the square-faced sheet; Gemini
  kept drawing him squat (and refused a prompt that called the proportions dwarf-like), so
  `concept_brother_tpose3_tall.jpg` is that sheet with the legs lengthened by Claude (legs x1.55 below the drawers'
  hem): build him to the tall one. His head, fishing and diving sheets predate the square face. Gemini's prompt box
  moves with the window's height (y 693 or 727 at this size): several "dropped" prompts were clicks that missed it.
- The user (2026-11-18, about 10:35 AM): "And we need the models for the other characters not just the captain"; (of
  Claude's leg-stretched sheet) "No make new concept art"; "Older brother needs body hair as well"; "And make gifs of
  the 3 in their walk / run cycles jumping swimming etc, and in different outfits once they are done". So: never
  doctor a concept sheet to stand in for a new one (`concept_brother_tpose3_tall.jpg` is retired); the brother's sheet
  to build from is `tools/art_src/concept_brother_tpose4.jpg` (tall, rugby build, square face, body hair), made in the
  OTHER Gemini conversation (/app/d2fe19426ff0ebc4), which is not anchored to the captain's squat build. His new head
  turnaround is owed (limit reached 10:40 AM, resets 1:15 PM), as are the captain's extra views and the younger boy's
  outfits. Builders: `tools/build_brother.py` -> `models/brother.glb`, `tools/build_boy.py` -> `models/boy.glb` (bare
  base bodies by the captain's method). OWED once the three are done: animation cycles (walk, run, jump, swim) on
  their shared bone names, outfits, and GIFs of each for the user.
- The older brother's look, settled by the user (2026-11-18, circling the head on `concept_brother_tpose3.jpg`): "I
  like the face of this version, but with the newer body". FACE = tpose3 (softer boyish square face, rosy nose, thin
  moustache); BODY = `concept_brother_tpose4.jpg` (tall, rugby build, hairy). New sheets of him are asked for with that
  face on that body.
- Heads and hands (the user, 2026-11-18, midday, of all three figures): "The heads and hands need a lot of work on all
  three- make sure you are matching pose silhouettes aggressively"; "I upgraded so we have more gemini usage" (the
  account is now Pro); "Make sure to regen the brothers look too". What works: every figure gets a BARE head sheet
  (shaved, clean-shaven, five or six views) and a HANDS sheet (six views), and the builder matches each view by a
  filled-silhouette difference picture (model against sheet, red and cyan), reporting the worst gap, not by eye.
  Sheets: `concept_captain_head_bare.jpg`, `concept_captain_hands.jpg`; `concept_brother_tpose5.jpg` (the settled
  look: soft boyish square face on the tall hairy rugby body; made in the /app/d2fe19426ff0ebc4 conversation, since
  the figures conversation draws everyone squat), `concept_brother_head2.jpg`, `concept_brother_hands.jpg`;
  `concept_boy_head.jpg`, `concept_boy_hands.jpg`. Gemini: a new picture shows only after the NEXT prompt is sent or
  about two minutes and a reload; type into the box found by `find` (its place moves). Still owed: the younger boy's
  outfits, the brother's outfits redrawn on the tall body, the captain's side view with the arm.
- The older brother's build (the user, 2026-11-18, with a photograph of a real man as a build reference, described in
  words only, never uploaded or kept in the repo): "He shouldn't be too ripped- needs a stocky build". Thick and padded:
  barrel chest, heavy round shoulders and arms without sharp definition, no abs, a solid soft middle, very hairy chest
  and belly. Sheet: `tools/art_src/concept_brother_tpose6.jpg` (replaces tpose5 for the body; tpose5's face stands).
- Heads and hands from a base mesh (2026-11-18, afternoon): the user asked to "find any free models online to use as
  reference and look up ways to best generate models" and approved the downloads ("you can download those things").
  `tools/FIGURE_HEADS.md` is the decision record and method: heads, ears and hands are fitted from Blender Studio's CC0
  Human Base Meshes (kept outside the repo in `C:\Projects\reference\human-base-meshes`), not lofted; bodies stay ours.
  Lessons that led there, in the user's words: "why is his jaw just straight flat across? Are you misunderstanding where
  there jaw is ?" (a head lofted from level rings has no jawline: the outline can match while the forms are missing, so
  judge in grey beside each sheet view and by landmarks); "See how the head connection is totally messed up and doesn't
  match reference" (the head was 21% too small with an invented neck: size and place the head from the BODY sheet).
  The user follows on a phone: send a short line between steps, and do not go quiet during long browser or build work
  ("I only stopped you because you weren't responding to my messages on my phone").
- Townsfolk (NPC) bodies (the user, 2026-11-18, afternoon): "I've like all thr older brother bodys you've sent, so we
  should make different models for each and generate a lanky build and women builds and we need models for them so we
  can make npcs out of them". So every body sheet becomes its own NPC base body (bare, on the shared bone names, heads
  and hands by `tools/FIGURE_HEADS.md`): from the brother's earlier sheets `concept_brother_tpose2.jpg` (short, sturdy,
  lean), `_tpose3.jpg` (short, sturdy, square-faced), `_tpose4.jpg` (tall, athletic, defined), `_tpose5.jpg` (tall,
  solid); and new sheets `concept_npc_man_lanky.jpg`, `concept_npc_woman_slender.jpg`, `_stout.jpg`, `_tall.jpg`,
  `_old.jpg` (women in period chemise and drawers). The NPC sheets were made in a NEW Gemini conversation,
  gemini.google.com/app/a896ddb450545c99 (a fresh chat draws fast and shows the picture at once; the set-pieces
  conversation /app/d2fe19426ff0ebc4 is also used by another session for biome covers: do not type into it while it is
  generating). Builder: `tools/build_npc.py` -> `models/npc/<name>.glb`. Which builds, faces, names and outfits the
  townsfolk get is not decided: ask.
- The independent critic (the user, 2026-11-18, late afternoon): "All 3 still need a LOT of polish"; "Many of their body
  parts are scuffed and incorrectly formed- after a build you should show the model in tpose and face and hand close ups
  to an agent that has no context, then ask it for critiques compared to the concept art so you can get good prompts to
  fix the issues". Standing procedure now: `tools/critic_pack.py` renders the pack, a fresh no-context agent writes the
  critique against the concept sheets, and that critique is the builder's next brief (`tools/FIGURE_HEADS.md`, last
  section). Builders also judge lit perspective renders as the game shows the figure, not only flat sheet views.
- Townsfolk bodies, first pass (2026-11-18, evening): `tools/build_npc.py` (`-- <name>|all [--pics <dir>]`, `-- lineup
  --pics <dir>`) builds nine base bodies into `models/npc/` (`man_lanky`, `man_short_lean`, `man_short_sturdy`,
  `man_tall_athletic`, `man_tall_solid`, `woman_slender`, `woman_stout`, `woman_tall`, `woman_old`), each bare, on the
  shared 51 bones, with a base-mesh head and hands and `<name>_underwear` as its own mesh. Rough: blocky shoulders,
  generic narrow heads, straight spread fingers, the women's tops a strapless tube, smeared paint; the two short men
  and the two tall men are near-duplicates (their sheets are). They wait for the three leads' polish to settle (feet,
  shorts, paint, shoulders), then get the same fixes and the independent critic. NOT in the game. Before any web
  build: leave `models/npc`, `textures/npc`, `models/captain*`, `models/brother*`, `models/boy*` and their textures out of
  the export (about 50 MB unused), in `tools/web_excludes.sh`.
- Figures, evening of 2026-11-18, what was learned and decided:
  - Why skin looked dark and muddy though the texture matched the sheet: Blender's default AgX view transform darkens
    comparison renders (set `view_transform = "Standard"`; `tools/critic_pack.py` does), and a sheet's painted light and
    shade is lit a second time in the game (`delight()` in `tools/build_brother.py` takes the broad shading out and
    keeps local colour).
  - Eyes are modelled open (an opening cut to the sheet's lids, lids with thickness, separate eyeballs on the head
    bone with a painted iris); the captain's stay wrinkly slits, modelled as a squint.
  - Feet come from the bundle's `Foot - Stylized`, fitted as the hands are; shorts are real garments (waistband, crotch,
    two legs, a hem with thickness), not a tube.
  - The younger boy is rebuilt to NEW sheets, `concept_boy_tpose2.jpg` and `concept_boy_head2.jpg` (slight, wiry,
    clearly thirteen). CLAUDE'S PICK, recommended to the user and not yet confirmed by them: his first sheet draws a
    squat muscular little man and the model matched it. The old sheets are kept, retired.
  - Lit perspective "beauty" pictures (`tests/<figure>_view.gd --persp`/`--beauty`, `tests/captain_beauty.gd`) are what
    the user is shown; the tiled sheet comparisons are for checking.

## Surf and rogue waves (2026-11-18)

The user: "Can we work on simulating crashing waves by the shoreline, and also rogue waves? Looking up solutions for
actual wave cresting etc so we can enhance our water / ocean system". `tools/WATER_FX.md`, "Surf and rogue waves", has
the research (with sources), the numbers, what is checked and what is rough. Concepts: `tools/art_src/concept_waves_shore.png`,
`concept_waves_rogue.png`.

- **Decision (Claude's pick): shore-distance surf on rings round the eye, a scripted rogue swell.** What: the shores are
  baked at start into a small map (`Surf.bake`: shore distance, depth, openness every 2 m); one train of Gerstner waves
  runs in to every shore, phased by the distance to it, growing by Green's law, breaking at McCowan's 0.78 of the depth,
  its crest thrown forward (Fournier-Reeves), foam where the surface folds (Tessendorf's Jacobian) and in the broken
  bore behind; the water mesh is five rings round the eye (0.5 m squares near, 8 m far, `Sea._rings`); a rogue wave is
  one travelling hump 4.5 m high with a trough before it, rare (240 to 480 s) and gentle in its push. Why: GL
  Compatibility on phones has no compute (no FFT or shallow-water simulation); a vertex sum is cheap; Bay's shore is
  already baked. Practice: GPU Gems Gerstner waves, Crest's LOD rings and shallow-water foam, a baked shore mask as AC
  III's. Alternatives: FFT, a simulation grid, breaker sheet meshes along the coast, a finer fixed mesh, a shore strip.
- One surface for everything: `Sea.surface_height(x, z)` (the swell, the surf and any rogue wave, as drawn), used by the
  leap, the camera, the splashes and spray, the title boat. `Sea.rogue_wave(at, heading, over)` sends one (`-- --rogue`
  for a test); `Sea.surge(at)` is its push (player and awake animals near the top). `scripts/surf.gd` and
  `shaders/surf.gdshaderinc` hold the same sums: change both.
- The water shader writes depth now (`depth_draw_always`: a tall wave's far side showed through its face).
- Pictures: `tests/surf_shot.gd` (an eye out from a shore, `--shore=x,z`, or anywhere; `--rogue=metres,age`; strips).
- Not in GameCommon (tied to this shader and Bay's shore); a candidate component if another game wants surf.
- **Barrels** (2026-11-18, the user: "The whole point of the wave agent was for real curling barrels on the waves, so
  research that"). `tools/WATER_FX.md`, "Barrels", has the research (Horizon Forbidden West, Moana, Lopatin, Iribarren),
  numbers, checks and what is rough. **Decision (Claude's pick): a breaker sheet along each break.** What:
  `scripts/breakers.gd` lays a strip of sections along the coast at each break (Steamer Lane west of the Santa Cruz
  wharf, and the Marina beach on the east shore); each carries one wave and draws it with the water's own sums except
  round the crest, where a breaking profile from a baked 64 x 48 picture (steep face, lip thrown, open tube, landing,
  collapse) is blended in by height only (so it never folds through itself); sections break one after another, so the
  barrel peels. The water mesh is discarded where the shore map's fourth channel says a sheet stands for it, the sheet
  everywhere else; both use the water's material, so they meet seamlessly. The rogue wave gets a moving sheet and curls
  too. Why: phones and the web have no compute; a heightfield cannot curl. Practice: a breaking cross-section swept
  along the wavefront (Horizon Forbidden West, Moana's profile deformer), baked like a vertex animation texture.
  Alternatives: Houdini FLIP baked to a VAT, curling Gerstner (loops, no tube), lip-only meshes, a gentler beach (the
  floor was NOT re-baked: per the Iribarren number a gentler slope spills; the steep beach is right for plunging).
- The shader's breaker path (`breaker_point`, `breaker_crest`, `surface_at` in water.gdshader and surf.gdshaderinc)
  and `Breakers.point` are the same sums: change both. Pictures: `tests/barrel_shot.gd` (a held stage, views side,
  inside, under, beach, sea, high; `--debug=4` which mesh draws). `-- --no-breakers` leaves them out; `-- --perf=barrel`.
- Barrels, second pass (2026-11-18, the user after six-angle GIFs: "Definitely needs another round"; Claude's picks):
  bigger, rounder tubes with a thick lip, longer strips that peel faster, shoulders that taper, two-tone painted foam,
  painted spray puffs (plume, burst, bubbles), a clearer look from under the water, and `Sea.surface_height(x, z, y)`
  aware of the lip (in the tube the surface is its floor). `tools/WATER_FX.md`, "Second pass".
- Barrels, third pass: the crash (2026-11-18, the user: "the splash timing and effects when the wave crashes needs
  work"; Claude's picks): each section's crash starts when its own lip lands (`Breakers.contact()` reads the landing
  stage off the profile, 1.00; `Breakers.landing` times it per section), so it runs along with the peel; drawn by
  `shaders/crash.gdshader` from the water's clock (splash-up, a second splash, mist, spit, a rolling bore, the back's
  air burst, bubbles), and the sheet's white water grows out from the landing. `tests/barrel_shot.gd --run` runs the
  clock (frames as the player sees them). `tools/WATER_FX.md`, "Third pass: the crash".
- The "scan line between each wave" (the user, 2026-11-18) was each breaker section jumping to the next wave's layout
  while its neighbour had not (a 13 m seam standing up between them); the points now slide from one wave's layout to
  the next while neither breaks (`Breakers.handover`, water.gdshader `breaker_lay`). `tools/WATER_FX.md`, "The hand-over".
- Pose sheets and the pose test (the user, 2026-11-18, evening): "Make some concept art of the 3 mains in different
  poses- laughing, shock, swim etc and match the models to the poses as well to make sure the topology is poseablw".
  Sheets: `tools/art_src/concept_captain_poses.jpg`, `concept_brother_poses.jpg`, `concept_boy_poses.jpg`. The test and
  the decision on how faces move (a `jaw` bone plus a few shared blend shapes, a mouth inside) are in
  `tools/FIGURE_HEADS.md`, "The pose test". Also the user, of the captain: "The captains wrist area needs a lot of
  work why are his forearms and wrists such different sizes" (a base hand's slim wrist loop zipped to a swelled
  forearm: taper the forearm to a thick wrist and size the hand's loop to meet it); "stop his chin and jaw phasing into
  his neck- have a pose where he is looking up to see what I mean" (judge every head with the head tilted back).
- The older brother's body, changed again (the user, 2026-11-18, evening): "The older brothers is a bit too bulky a big
  gutted, though I like how it works so make it a different grown man model". So the bulky big-bellied body fitted to
  `concept_brother_tpose6.jpg` is kept as a townsperson, `models/npc/man_big.glb` (a grown man; a face of his own is
  owed), and the brother's body sheet is now `tools/art_src/concept_brother_tpose7.jpg` (tall, stocky, hairy, a nearly
  flat stomach, no gut; made in the NPC conversation /app/a896ddb450545c99). `tools/build_brother.py` builds both by
  `-- --figure brother|man_big`. His pose sheet `concept_brother_poses.jpg` shows the bulkier build: use it for poses
  only.
- And again (the user, 2026-11-18, 5:40 PM, of `concept_brother_tpose7.jpg`): "Not stocky enough now and he lost thair,
  though make a body on that one". So tpose7 is a townsperson too (`models/npc/man_trim.glb`), tpose6 is `man_big`, and
  the BROTHER'S body is still owed: `concept_brother_tpose8.jpg`, between the two: thick and stocky like tpose6 with a
  full firm stomach but no hanging gut, and as hairy as tpose6. Gemini's limit was reached again at 5:42 PM (resets
  6:15 PM) even on the upgraded plan after about 25 pictures in the afternoon: draw tpose8 then, in the NPC
  conversation, and tell the brother's builder. `tools/build_brother.py` is to build `brother`, `man_big` and `man_trim`
  by `-- --figure`.
- The brother's nose (the user, 2026-11-18, 5:45 PM): "hes a bit too red button nosed, needs to be a tad angular": less
  red, less of a round button; a slightly more angular nose (and, Claude's reading, a touch more definition in the face,
  still boyish). Goes into `concept_brother_tpose8.jpg` and a new head sheet `concept_brother_head3.jpg` (two rows: with
  hair, and shaved), both owed after 6:15 PM.
- The brother's eyes (the user, 2026-11-18, about 5:50 PM): "The brother should have a bit down turned eyes and more
  prominent world weary bags for soft gentle kind eyes". Outer corners a little lower than the inner, a slightly heavy
  outer upper lid, clear soft bags under each eye, relaxed brows: gentle and kind, a little tired. Into
  `concept_brother_head3.jpg` and the model.
- The brother's eye colour (the user, 2026-11-18): "And tehy should be amber brown green": hazel, amber-brown shading to
  green (not the blue-grey of his earlier sheets).

## Pushed 2026-11-19 (night)
Game build a8f72f7 (source 8856d6e), site PR #217 (cart ?v=a8f72f7): animals on baked textures and four shared motion
shaders, everything compiled on the loading screen with a progress bar, one program each (the null lamp), no freezes
in play on the cold tour. Pack 51 MB. Real Chrome on the desktop: about 60-67 s first visit, 22 s after. Not tried on
a phone. Look choices left with the user: submarine per vertex, baking the squids/nettle/anglerfish/comb jelly, water.

## Pushed 2026-11-19
Game build a64b400 (source c0c574c), site PR #216 (cart ?v=a64b400), after 2d56cec / PR #215 (barrels, crash timing,
crest spray, the seam between waves): shaders warmed by nearness, the phone tier, boats batched, figures left out of
the web pack (37.9 MB, was 76). Not tried on a real phone. When a push of main and a push of the build land a minute
apart, Pages cancels the first and `pages/builds/latest` reports "errored" though the second deployed: check
`gh run list` and the live pck's Content-Length instead.

## Pushed 2026-11-18 (evening)
Game build a8f7d82 (source 3eb0d1e), site PR #214 (cart ?v=a8f7d82): the real bay with the drawn trench and terraced
walls, the eight biomes, denser kelp, sea grass on Warren's field spawning, Atlantis in the canyon basin, caustics on
everything, surf with curling barrels and rogue waves, only nearby animals awake. The pack is 61 MB (it was 39.6):
first load on a phone is a worry. The preview film on the arcade is still the old one. Not tried on a phone or in a
browser after this push.
- State at 6:30 PM, 2026-11-18 (figures; nothing is in the game):
  - The brother's settled sheets: body `concept_brother_tpose8.jpg`; head `concept_brother_head3.jpg` TOP row (its
    bottom row drew a different child-like face: ignore it) and `concept_brother_head3_bare.jpg` (the same man shaved,
    two rows: build to the bottom row). `concept_brother_head2.jpg`, tpose5/6/7 are retired for him (6 = `man_big`,
    7 = `man_trim`). When asking Gemini for a shaved row, say "exactly the same grown man, nothing else changed" and
    check it: it turned him into a child once.
  - Hair exists: `tools/build_hair.py` (under-shell + alpha-cut lock cards + normals from one hull),
    `shaders/hair_cards.gdshader`, `models/hair/*`, viewer `tests/hair_view.gd`. The user asked "Is there a hair agent
    running?" (there was not): keep one going alongside the figures.
  - Facial movement (the user: "We should start working on facial movements as well"; "Make sure it does research"):
    `tools/face_rig.py`, `tools/FACE_RIG.md` (research with sources, then the decision), test outputs `models/face/*`.
  - Every figure's builder now runs the pose test against its pose sheet; critiques by a no-context reviewer drive
    each round; lit "beauty" pictures are what the user is shown.
- Facial movement, second pass (2026-11-18, evening; `tools/FACE_RIG.md` is the record): `tools/face_rig.py` adds, as a
  post-process on a built figure, a `jaw` bone, `eye_l`/`eye_r` bones (bone numbers after `head` shift by three; names
  do not change), a mouth inside (arched teeth, tongue), 20 shared shapes, and expression recipes built from FACS
  (`models/face/face_expressions.json`). `rig_face(...)` is one call for the build scripts; `-- <in.glb> --selftest`
  checks a head. Beards and moustaches follow the face through `bind_to_face`. Test copies only (`models/face/*`), not
  in the game. What the figures' builders owe it: the lips' meeting line as a real edge loop on the painted mouth line
  (the cut otherwise costs about 500 triangles a figure, not 250); the boy's lids painted as skin with lashes a thin
  line; a heavier loop under the captain's chin. Small folded faces remain in laughs (its self-test fails on them).
- The captain's pose test is `tests/captain_beauty.gd -- --poses`, the boy's `tests/boy_view.gd -- --poses`; all three
  rigs already have three bones a finger and thumb (`finger_<name>_1..3_<side>`, `thumb_1..3_<side>`).
- **Figures are adjusted, not rebuilt** (the user, 2026-11-18, late evening, after about ten rounds a figure): "Are you
  rebuilding the whole head each revision? I'm not seeing improvement, you should just be making adjustments". What was
  happening: every round regenerated the model from its build script and a fresh builder edited steps in the middle of
  it, so one fix moved other things (the brother's nose shortened, the captain's jaw folding more), and Claude had just
  ordered a whole new head for the brother. The rule now, for heads, hands and feet of every figure: the current mesh is
  FROZEN as a saved base the build loads; the earlier steps that made it are not edited and nothing is refitted; changes
  are a final ordered list of small named adjustments (one feature each, a local move with smooth falloff, its own
  switch and amount); every adjustment is shown as a before/after pair (same camera and light, grey and lit, beside
  the sheet's view) and kept only if it visibly moves toward the sheet. The user is shown those pairs. Paint the same
  way: adjust what is there.
- The brother's head to keep is the one of 6:00 PM, 2026-11-18 (commit 61a8380, pictures in the session's `brother7`): the
  user, late that evening: "The brother had a much better earlier head unless I'm mistaken". They were right: the refit
  to the shaved sheet (commit 3a063ac) made him gaunt and old, and the "youth" pass after it erased his nose and
  character. That earlier head is restored as his frozen base on the current body, and only the user's own asks are
  adjusted on it (nose a tad angular and less red, eyes a bit downturned with bags, hazel). Before a figure's next round,
  put its head from several rounds side by side: later is not better by default.
- Face rig and mouth paint (found 2026-11-18): `tools/face_rig.py` finds the mouth from the darkness of the PAINTED mouth
  line, so any mouth paint has to stay on the lips' seam edge; a painted smile curving off it sent the mouth corners
  45 mm out and folded five expressions on the boy. Worth changing the rig to take the lip loop from the mesh instead.
- The boy's late adjustments are `late_adjust` in `tools/build_boy.py` (switches listed near `eye_margins`); trial
  builds go to `--glb <path>` and are viewed with `tests/boy_view.gd -- --glb=... --face`.
- **One body part at a time** (the user, 2026-11-18, late evening, of the figures): "Target just one body part until it
  looks correct". A figure's round takes ONE part (a nose, the hands, the eyes), works it as adjustments on the frozen
  base in the game's light, close up, beside the sheet's same part at the same scale, and repeats (name the biggest
  remaining difference, fix it, look again) until it reads as the same part as the drawing; only then the next part.
  No lists of eight things a round. The user is shown that part's rows, iteration by iteration. First parts
  (Claude's pick): the captain's hands, the brother's nose, the boy's nose.
- The brother's nose stays buttony (the user, 2026-11-18, late evening, of the restored 6 PM head): "I think I actually
  like the more buttony nose on the brother". This replaces their earlier "a bit too red button nosed, needs to be a tad
  angular": leave the frozen head's nose shape alone (only its redness was eased, `nose_less_red`). His part in work is
  the eyes (downturned, soft bags, hazel).
- **THE FIGURES ARE TABLED** (the user, 2026-11-19, about 2 AM, after some forty builder rounds over a day): of the
  brother's eyes after four passes: "No he looks totally bugeyed now, I'm more worried about his busted ass jaw and
  neck"; then "Ehhh we're not making good progress lets table this work for now", and they stopped the three running
  builders themselves. Do not restart figure work unless the user asks. Where it was left (nothing is in the game):
  the captain (`models/captain.glb`: frozen base + named adjustments; hands on their third pass: repainted, fist still
  blocky), the brother (`models/brother.glb`: his 6 PM head restored and frozen; eyes enlarged over four passes, which
  the user dislikes: "bugeyed"; his jaw and neck, in side view a slack lower face running into a thick patchy neck, are
  what the user wants fixed first), the boy (`models/boy.glb`: frozen head; nose on its third pass), townsfolk bodies,
  hair (five passes), the face rig (two passes). The stopped builders' half-done script edits were not recorded; a
  copy of that diff was put in the session's scratchpad (`tabled\unfinished_rounds.patch`, which a clean-up may lose).
  What Claude takes from the day (its own reading, not the user's words): scripted, agent-built figures converged on
  bodies but not on faces and hands; dozens of rounds of critique-and-fix moved slowly and often sideways; if this is
  picked up again, start by asking the user how they want faces made (for example by hand in Blender, from a bought or
  commissioned base, or a simpler stylised face like the mask heads the user's other games use) before running builders.
- **The older brother's character bible** (the user, 2026-11-19, with five pictures they generated themselves: "I've
  generated new key art for the character these should be the the character bible"). These five ARE his look now and
  every earlier brother sheet is retired for him (kept in place; `tpose6`/`tpose7` are still the townsfolk `man_big` /
  `man_trim`): `tools/art_src/concept_brother_bible_face.jpg` (front close-up), `_bible_body.jpg` (front, side, back
  in white drawers), `_bible_head.jpg` (five-view head with hair), `_bible_bare.jpg` (the same man shaved bald and
  clean-shaven, five-view head and three-view body: the sheet to model the bare base from), `_bible_poses.jpg` (six
  expressions; four poses in his work rig). What they show (Claude's reading of the pictures): a tousled mop of brown
  curls falling on the forehead; a broad square face on a thick neck; a round button nose; hazel-green eyes, a bit
  downturned with soft bags; a small mole on each cheek under the eye; a thick ginger-auburn moustache, ginger stubble
  and sideburns (redder than his hair); stocky and padded with a soft belly, hairy chest, belly, forearms and legs;
  tattoos: an anchor on his right forearm, a swallow over a rope knot on his left forearm, an anchor on his left upper
  arm; work rig: cream henley with rolled sleeves, stained blue bib overalls with rolled cuffs, brown boots. The sheets
  draw him short-legged; the user's earlier "should be the tallest of the 3" has not been withdrawn: ask before
  building. Figure work is still tabled (below is unchanged): this only replaces what he is built to when it resumes.
- **Figures restart as an editor, not build scripts** (the user, 2026-11-19, lifting the tabling for this method: "Lets
  try to build a new model from scratch and this time rather than adjust minute details, lets take a generic model,
  then categorize the vertices so that we can make intelligent edits ... so we can essentially make a character
  editor. Then we use these functions to sculpt the body to fit the art for the most part, and THEN we can work on
  tiny detail corrections"; and of the brother: "He should still be the tallest, but those proportions are correct").
  `tools/figed/` (README there is the decision record): a figure is MakeHuman's CC0 generic human (outside the repo,
  `C:\Projects\reference\makehuman\mpfb2`) plus a table of slider values (`tools/figed/figures/brother.json`), and
  `figed_fit.py` moves the sliders by itself until the outline matches the bible's sheets. The old figure builders
  (`build_brother.py`, `build_captain.py`, `build_boy.py`, `build_npc.py`) stay tabled. Nothing is in the game.
