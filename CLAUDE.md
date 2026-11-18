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
seen (`Creature.become(kind, bare)`, `Life.mark_dressed`), (2) behind the title each kind is shown once to a tiny view
(`Main._begin_warm`), the start button waiting for the starting waters' kinds. First load is still about a minute and
a half on a Windows desktop browser. Build the web export from the clean worktree `../Gulp-build` (`git checkout
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
- **The sky** (2026-11-18, the user: "Whys the sky just gray"): it was one flat background colour, greyed further by
  the fog and the filmic tone map. Now `shaders/sky.gdshader` (Claude's pick of look, no concept art yet): a gradient,
  pale at the horizon and deeper overhead, the sun or moon with a glow, sparse soft clouds drifting; colours from the
  hour in `Sea._look`, shown only with the eye above water (under it the background is the water colour as before). It
  lights nothing (ambient stays a colour, reflections off) and is redrawn into its small radiance only when `_look`
  changes it (the drift is a uniform, not TIME).
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
  (needs the 50 m amplifier), on a broad spur raised for it: `Bay.WRECK_SHELF`'s 7th item makes a shelf fill only
  (never dig: Carmel Cove keeps its 8 to 13 m for the pier), level under the hull itself, its sides spread to 84 m.
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
