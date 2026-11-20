# Gulp: the performance pass (2026-11-18)

The user: "yes do a performance pass and then push everything". Done by an agent before the push; the decisions are
Claude's and are recorded in CLAUDE.md ("Performance"). The web build is what matters most: phone first, on the arcade.

## How it was measured

- `-- --perf=<places>` (Main loads `tests/perf.gd`): the fish (a sardine, nothing hunting, the depth limit off) is put
  at each place, the sea settles 4 s, then 300 frames are measured in a real window with vsync off:
  the whole frame; the scripts' `_process` work (a node that runs first to one that runs last); Life's own parts; what
  the sea's half-size picture drew (draws, triangles); its render time. Then `PERF HEAVY` (an estimate of triangles by
  owner) and `PERF DRAWN` (each of the eight heaviest hidden for a few frames: what the picture really loses).
  `--perf-shots=<folder>` saves a picture of each place; `--perf=title` measures the title and start-up.
  Perf runs draw the sand as a web build does (`Sand.quality = 1`; a desktop draws it finer: 162,000 triangles, not 62,000).
- Places: `start` (where a run starts), `kelp`, `reef` (the liner: the eye inside its reef), `pirate`, `ruins`
  (Atlantis), `docks`, `ball` (inside the bait ball of 1,600 sardines), `title`.
- Scripts by function: Warren's `tools/gdprof.mjs` (`node ../TheClearing/tools/gdprof.mjs 6071 out.txt`, game run with
  `--remote-debug tcp://127.0.0.1:6071 -- --perf=reef`; perf.gd prints PROFILE START/STOP round each place).
- `tests/rocks_bench.gd` (headless): `Sea.clear_of_rocks` old and new, 4,000 points round each set piece.
- Before: a worktree of HEAD (cfc6bee) with only the perf harness added, so the same harness measured both. The working
  tree has a few more animals than HEAD (the main session was installing creatures meanwhile: a submarine, a ghost
  whale...), so a place can show more fish after than before.
- RTX 4080 desktop, Windows, Godot 4.7.2, GL Compatibility. Other sessions were running on the machine: frame times vary
  by 1 to 3 ms between runs; triangles, draws and the scripts' share are the steadier numbers.

## Before and after (390x844; the sea's picture is 360x779 there, measured 2026-11-19: the half-size picture is half the 720-wide layout, not half the window)

| place | frame ms before | after | scripts ms before | after | draws before | after | triangles before | after |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| start | 6.2 | 5.0 | 2.8 | 2.3 | 29 | 10 | 128k | 85k |
| kelp | 7.3 | 6.6 | 3.3 | 2.7 | 77 | 78 | 165k | 121k |
| reef (liner) | 12.5 | 8.2 | 5.5 | 3.3 | 122 | 149 | 614k | 330k |
| pirate | 10.6 | 8.2 | 4.5 | 3.8 | 65 | 58 | 207k | 186k |
| ruins | 7.1 | 8.4 | 4.0 | 3.7 | 57 | 59 | 117k | 144k* |
| docks | 8.2 | 6.3 | 3.4 | 3.2 | 172 | 166 | 163k | 127k |
| ball | 8.5 | 5.5 | 3.4 | 2.4 | 109 | 66 | 221k | 161k |
| title | 8.1 | 5.9 | 2.8 | 3.1 | 242 | 210 | 376k** | 239k |

At 1280x720 (picture 640x360): reef 13.6 -> 8.5 ms, 626k -> 361k triangles, 156 -> 199 draws; start 7.3 -> 7.1 ms,
161k -> 115k; ball 8.9 -> 7.0 ms; docks 10.1 -> 7.1 ms; the rest within a millisecond.

\* more animals in view after (new kinds installed meanwhile: a Humboldt squid pack, the submarine, a ghost whale);
Atlantis itself and its scenery are unchanged (30k triangles, 36 draws both times). \*\* the first title run drew the
sand at desktop fineness.

## What was changed, biggest first

1. **The rocks' grid** (`Sea.add_rock`, `Sea.clear_of_rocks`; CLAUDE.md "Decision: two grids for the rocks"). A 2 m
   cube grid besides the 8 m squares. `Sea.clear_of_rocks` beside the liner 11.5 -> 1.1 us a call, pirate 12.5 -> 1.5,
   ruins 8.8 -> 1.2, kelp 3.5 -> 1.0, open water 0.75 -> 0.36 (rocks_bench). In the frame at the reef: 2.03 ms -> 0.35
   ms (gdprof). Up to 398 spheres in one 8 m square, now at most 29 in a 2 m cube. The wreck, pirate and ruins route
   checks still pass (no route point moved).
2. **Scenery near and far** (`scripts/lod_field.gd`; "Decision: scenery near and far"). The liner's reef and the kit's
   pieces in Scenery: full models within 8 m, light ones to 60 or 70 m, none beyond. The liner's reef placed 2.7M
   triangles of full models (1.9M of them the reef); drawn at the reef 614k -> 330k (the near pieces are still 140k of
   it). Scenery's pieces were whole-map MultiMeshes drawn wherever any of them was in view (the start drew 25k
   triangles of red sea fans 200 m off). **Looks:** from 8 m out a piece is its light model: a brain coral loses its
   folds, fans and anemones are simpler (pictures compared: the wreck from its bow, all full against near 8 m).
3. **Far animals stepped every other frame** (`Life.STEP_NEAR`, 20 m and two lengths): at the reef 184 animals were
   stepped every frame. Beyond 20 m a fish moves less than a pixel of the half-size picture a frame.
4. **A fish's look is sent only what changed** (`Fish.pose`): the `in` lookups on the creature object every frame
   (swim, sway, wings, walk, gape, low) are found once when it is worn; curl, gape and the holder's scale are sent
   only when they change. `Fish.pose` 1.06 ms for 195 calls -> 0.82 ms for 139 (gdprof at the reef; with 3., fewer calls); Life's "fish"
   (all the animals) 4.5 -> 2.5 ms there with 1. and 3.
5. **The sonar's picture in layers** (`scripts/sonar.gd`): drawn whole every frame it cost 0.72 ms; now rings once,
   the sweep every frame, the landmarks when Main sends new ones, the blips every other frame (their brightening as the
   sweep passes moves under 1% a frame), the compass when the heading turns: about 0.4 ms. Looks the same.
6. **Hidden when out of sight**: the moon jellies (18,000 triangles and a lamp each) and the nettles beyond 48 m
   (`Life.JELLY_DRAWN`); the garden eels (260 in one draw, 60k triangles) when the eye is more than 60 m beyond the
   sand. All were drawn at any distance, under the fog.
7. **Shaders compiled behind the title** (`Main._materials_to_warm`): besides each animal kind, every other material
   in the sea (173: the wrecks, Atlantis, the kit, plants, docks, boats, schools, jellies...) is shown once to the
   little warm-up view, after the starting waters' kinds, so the start button is not held up. In a browser each new
   program freezes the game for about a second when first drawn: the wrecks and Atlantis did that in play.
8. **The web pack** (`sh tools/web_excludes.sh`, then `--import`): see below.
9. **The flaky check** "pack hunters at a swarm take from it and ball it up" (failed about one run in three): the pack's
   first dash came only 3 s in and the next up to 7 s later, and a dash takes a fish only now and then (a 4-a-second
   chance while its mouth is in the swarm), so 10 s often saw one dash and no fish. The check now starts each hunter with
   its dash due and waits up to 20 s, stopping when both are seen. The game is unchanged.

## Only nearby animals awake (2026-11-18, later)

After the user found the phone build choppy and saw it crash. CLAUDE.md, "Decision: only nearby animals are awake".
`--perf` now also prints `PERF <place> animals: N awake of 495, M drawn`. 390x844, desktop:

| place | life ms before | after | awake | drawn |
| --- | --- | --- | --- | --- |
| start | 1.75 | 0.65 | 60 | 29 |
| kelp | 2.11 | 1.24 | 56 | 50 |
| reef (liner) | 2.73 | 1.87 | 131 | 120 |
| ruins | | 1.16 | 147 | 61 |

The reef is still the densest: its own stock is that many fish within 45 m.

## The web pack

| | before | after |
| --- | --- | --- |
| index.pck | 65.7 MB (62.5 MB of files) | 35.0 MB (33.2 MB) |
| models (.scn) | 38.4 MB | 23.1 MB |
| pictures (.ctex) | 17.7 MB | 6.4 MB |

- Creature models without automatic LODs and shadow meshes: half of each model's weight (the leviathan's game model
  283 KB -> 145 KB). Nothing casts a shadow in Gulp, and the creatures never used their LODs (`Fish._wear` sets
  lod_bias 64; most components strip them anyway). Schools and clouds (`*_school`, plankton and sea sparkle specks,
  the garden eel colony) keep their LODs: without them the bait ball alone drew 500,000 more triangles.
- Atlases: the liner's bow 4096 lossless without mipmaps (4.74 MB in the pack, 64 MB on the GPU) -> 2048 lossy with
  mipmaps (0.44 MB, 21 MB); the stern, pirate and ruins atlases lossy with mipmaps (stern 1.92 -> 0.32 MB, pirate 2.67
  -> 0.46 MB, ruins 2.40 -> 0.42 MB, statue 1.06 -> small). The wreck's shader already asked for mipmaps the picture
  did not have. **Looks:** the hull close up is a little softer (bow rail pictures compared); at the half-size picture
  the difference shows only within a couple of metres of the hull.
- Left out of the web pack: `conceptart/` (1.6 MB: a map reference picture was being exported), `models/sea_floor.glb`
  (the retired rocks, 1 MB), the retired flat panel's pictures (`textures/panel/*_module.png` and the rest, 2.5 MB).
- Largest files after: sea_floor_props.glb 2.55 MB, submarine_atlas.png 1.51 MB (lossless, no mipmaps: a new creature;
  not touched), sea_nettle.glb 1.41 MB, panel_atlas.png 1.21 MB (the panel, drawn close and large: kept lossless),
  moon_jelly.glb 1.05 MB, atlantis_ruins.glb 0.69 MB, pirate_wreck.glb, logo.png, control_panel.glb, title_captain.glb,
  helmet_atlas.png, shrimp_boat.glb, sea_floor_props_lo.glb, mangroves.

## Start-up

`--perf=title` at 390x844; times from the engine's start. "Cold" is with Godot's shader cache
(`%APPDATA%/Godot/app_userdata/Gulp/shader_cache`) moved aside, as on a first visit; it was put back afterwards.

| | first frame | start button live | every kind (and material) shown once |
| --- | --- | --- | --- |
| native GL, cache warm, before | 2.2 s | 2.8 s | 6.5 s |
| native GL, cache warm, after | 2.4 s | 3.2 s | 13.5 s (173 materials more) |
| ANGLE (D3D11), cold, before | 10.7 s | 80.7 s | not done in 240 s |
| ANGLE, cold, after | 11.0 s | 88.4 s | not done in 240 s |
| ANGLE, cache warm, after | 2.1 s | 2.9 s | 11.0 s |

- Cold under ANGLE each animal kind takes 2 to 4 s to compile (the first sardine 7 s, a Humboldt squid 6 s), the
  set pieces' and plants' materials 0.2 to 3 s; the start button waits for the 22 kinds of the starting waters, so
  about 80 s. That is the "minute and a half" of a first load in a Windows browser. The pass did not shorten it (the
  difference above is noise); what it changed is that the materials of the wrecks, Atlantis, the kit and the plants are
  now compiled on the title too, after those 22 kinds, instead of freezing play when first seen. If the player starts
  before they are done, the rest compile in play as before.
- The creature shaders are GameCommon's and were not touched. Fewer programs (a shared creature shader) or fewer
  kinds in the starting waters are the levers left for the first load.

## Shader programs

About 156 `.gdshader` files can be drawn: about 130 are the creatures' (one a kind, from GameCommon), the rest the
game's and the plants'. Each is a program a browser compiles when first drawn. Could share: the liner's and Atlantis'
paints (both lit, a baked atlas: one shader with `lift`/`grain`/`glow` uniforms); the pirate ship's is unshaded with
caustics (a different program anyway). The creatures' shaders could share only if GameCommon's creatures did (a common
body shader with the markings in uniforms or a texture): not done here. `shaders/sea_floor.gdshader` (the retired
rocks) and `shaders/fish.gdshader` (the old shark, only for a kind not installed) are not drawn in play.

## What is still heavy

- The liner's reef with the eye inside it: about 330k triangles at 390x844 (140k of it the full pieces within 8 m)
  and 149 draws (199 at 1280x720: two MultiMeshes a piece). Nearer 5 m would halve it, at a visible cost.
- The sand: 62,000 triangles everywhere at web quality (GameCommon's sand clipmap, 8 rings).
- The title: 210 draws (the boat and the three figures: 168 of them), 239k triangles (the fish logo 72k); 3 ms of
  scripts (the figures' idle, the logo).
- `TitleLogo._process` still runs in play (0.17 ms a frame) though the logo is hidden once the dive starts.
- Scripts: 2.3 to 3.8 ms a frame on this desktop, most of it the animals (`Creature.step`, `Fish.pose`,
  `Life._step_creatures`). A browser runs GDScript several times slower; a phone slower still.
- The loading screen: 610 fish placed by script each frame, 0.87 ms on this desktop; left as it is (fewer fish would
  thin the logo).
- 0 frames were measured on a phone or in a real browser.

## Not measured

- Phones: no phone here. The proxy: under about 5 ms of scripts, 150k triangles and 150 draws in view at 390x844 on
  the desktop. Met at the start, the kelp, the docks and the bait ball; over on triangles at the liner (330k), the pirate
  ship (186k) and Atlantis (144k with new animals in view).
- A real browser's frame rate: not driven here. ANGLE on the desktop (`--rendering-driver opengl3_angle`) stood in for
  start-up.

## Hitches, the phone tier and the pack (2026-11-19)

The user: "the game is very stuttery on mobile, with lots of freezes" (and on 2026-11-18: "Gulp's performance on phone is
still very choppy and it crashed"). Decisions in CLAUDE.md: "Decision: shaders warmed by nearness" and "Decision: a phone
tier". No phone here: everything below is a Windows desktop (RTX 4080) standing in.

### How the hitches were found

- `-- --hitches` (`scripts/hitches.gd`) prints a `GULP HITCH` line for every frame of 50 ms or more: its length, the
  scripts' share, what other code noted that frame (`Hitches.note`: an animal dressed, a thing warmed, a jelly shown),
  which nodes were added, and which materials came into view for the first time (keyed as the warm-up keys them: shader
  and MultiMesh format). `report()` sums them by stage.
- `-- --dive --tour` (`tests/tour.gd`) starts the moment the start button is live (as an eager player does), then
  carries the fish at 6 m/s through every biome: sand, the Steamer Lane barrels, a leap, the beach, trench, river,
  Marina breakers, docks, kelp, the liner's reef, Atlantis, grass, open ocean, crags, pirate ship (a breadth-first way
  through the water between them). Then the hitches and frame times.
- Cold, as a first visit in a browser: `--rendering-driver opengl3_angle` (D3D11 under ANGLE, as Chrome on Windows)
  with Godot's shader cache (`%APPDATA%/Godot/app_userdata/Gulp/shader_cache`, which also holds ANGLE's own blob cache)
  moved aside. "Before" is the pushed build's code (2d56cec) with only the logger added.

### What froze it

Nearly every freeze was a shader program compiled the first time something was drawn: 1.5 to 6 s each under ANGLE
(a browser on a phone compiles faster, but the same programs, at the same moments). The logger's lines named them:
animal kinds dressed as they came into sight (the river: 19 freezes, 53 s, as walleye, guppies, platies, bettas,
pike, catfish... came into view together, the worst 10.2 s), kelp, eelgrass fields (made only as the eye nears, so never
warmed), mangroves, splashes, the fishers' gear, Atlantis. Main's warm-up behind the title covered them, but stopped the
moment the start button was pressed, which it allowed once the 22 starting kinds were done: everything else (about 280
programs) was compiled in play, in bursts, in sight. Also seen: a kind's far (`_lo`) model loaded the first time one is
far off (10 to 25 ms of script on the desktop); the host anemones never loaded at all in the web build (their full model
is left out of the pack).

The jellies' lamps (OmniLight3D) were a suspect (a material lit by an omni light is another program variant in
Compatibility); the logger notes each jelly as it is shown, and no hitch fell on one. Not changed.

### Cold tour, before and after (390x844, ANGLE, cache cleared; in play = after the title)

| | before | after |
| --- | --- | --- |
| title until start (first frame alone 46 to 52 s) | 118 s | 142 s (start waits up to 60 s more) |
| in play: frames over 50 ms | 107 | 100 |
| of those, a program compiled at first sight (or on dressing) | 49 (124 s) | 9 (25 s) |
| of those, unexplained by the logger | 58 (87 s; most were title-warmed things not yet drawn) | 15 (4 s) |
| of those, a warm-up out of sight, ahead of the fish | - | 76 (183 s) |
| worst in play | 10.2 s (river: four kinds at once) | 5.8 s (one program) |
| frame time over the tour: median / 95th / 99th | 6.5 / 11.6 / 14.4 ms | 6.5 / 11.4 / 14.1 ms |

Read honestly: on a Windows desktop's first visit the compiling costs the same in total (the tour sees nearly the
whole sea), but it now happens one program at a time, out of sight, before the thing is seen, and never four at
once. On a phone the same order applies with far shorter compiles. A browser keeps compiled programs for later visits
(Chrome's GPU program cache), which this cannot measure.

### Steady cost (`--perf`, 390x844, `Sand.quality` 1, native GL)

Frame ms / scripts ms / draws in the sea's picture / triangles (k) / all draws (with the panel and sonar):

| place | before | after, desktop | after, `--phone` |
| --- | --- | --- | --- |
| start | 3.9 / 1.9 / 108 / 190 / 300 | 3.5 / 1.7 / 81 / 192 / 272 | 2.8 / 1.4 / 65 / 131 / 226 |
| kelp | 3.9 / 1.9 / 100 / 166 / 313 | 3.5 / 1.7 / 99 / 165 / 312 | 3.3 / 1.6 / 91 / 96 / 274 |
| grass | 3.8 / 1.9 / 110 / 190 / 291 | 3.1 / 1.5 / 109 / 190 / 290 | 2.7 / 1.3 / 101 / 110 / 255 |
| reef (liner) | 8.3 / 3.0 / 109 / 181 / 409 | 6.2 / 2.5 / 90 / 160 / 391 | 5.0 / 2.4 / 143 / 140 / 413 |
| ruins | 8.9 / 2.0 / 141 / 163 / 328 | 7.0 / 1.8 / 121 / 166 / 307 | 3.2 / 1.5 / 110 / 114 / 266 |
| beach | 2.4 / 1.1 / 12 / 103 / 192 | 2.1 / 1.0 / 12 / 103 / 192 | 2.5 / 1.0 / 12 / 52 / 163 |
| barrel | 2.9 / 1.3 / 18 / 118 / 200 | 2.3 / 1.1 / 18 / 118 / 200 | 2.3 / 1.2 / 15 / 66 / 167 |
| crags | 4.0 / 1.9 / 87 / 162 / 282 | 3.3 / 1.6 / 87 / 162 / 281 | 2.9 / 1.4 / 82 / 97 / 246 |
| river | 7.1 / 4.2 / 36 / 210 / 290 | 5.8 / 3.5 / 37 / 222 / 293 | 5.5 / 3.4 / 30 / 155 / 257 |

(Draw counts move with what animals happen to be in view; the reef's phone run had more fish in sight.) Animals awake
on the phone tier: 62 at the start (83 desktop), 47 at the ruins (54), 53 in the grass (78).

- What dominates on a phone (an estimate, no phone measured): scripts are 1 to 3.5 ms here, and GDScript in a phone's
  browser runs perhaps five to ten times slower; draws are 160 to 410 a frame, each dear in WebGL. Of those, the
  control panel's SubViewport is 59 and the sonar's scope about 120 (lines and dots): the phone tier draws both every
  other frame. The shrimp boats were 45 draws each (now 16: `scripts/still_batch.gd`). The panel model was already one
  mesh a material per housing (59 objects before and after merging was tried: the merge is not used there).
- The sea's picture is 360x779 on a phone-shaped screen whatever the phone's pixels (half the 720-wide layout): fill
  rate there is modest. The panel's SubViewport is 720x1558 with 2x MSAA (none on the phone tier).
- Caustics were kept on phones: one draw and a copy of colour and depth at 360x779; turning them off is a one-line
  change in `Sea._caustics` if a phone shows them to be dear.

### What the phone tier turns down (`Tier.phone()`; `-- --phone` to try it on a desktop)

Sand quality 0 (GameCommon's own lowest step); eelgrass at its lowest quality and 0.8 of the tufts; kelp's full pieces
within 3.5 m (5) and light ones to 10.5 m (15), nothing past 50 m (60); the kit's and the reef's full pieces within
0.6 of their reach and nothing past 50 m; animals drawn within 38 m (45), awake within 48/58 m (55/65), stepped every
frame within 14 m (20), every other to 24 m (32), one dressed a frame (2); water rings of 1 m squares (0.5: a quarter
of the 36,000 triangles); half the breaker spray; the panel without MSAA; panel and sonar drawn every other frame.

### The web pack

`index.pck` 76.2 MB -> 37.9 MB. Left out now (`tools/web_excludes.sh`): the figures that are not in the game (models/boy*,
brother*, captain*, face/, hair/, npc/ and textures/boy, brother, captain, tattoos, face, hair, npc: about 35 MB), the
first, flat Atlantis (model, atlases, table) and the old rocks' table. `tests/web_deps.gd` (headless) checks that
nothing kept depends on anything left out. The title's figures (models/title_*) are kept.

## Everything at the start (2026-11-19, later)

The user: "there should be no freezing", "whats the point of loading if you have to load after pressing start
anyways??", "All loading should just happen at the start you shouldnt have to wait for buttons or anything", and of
baking: "cant you use the shader to generate the textures?". CLAUDE.md, "Decision: everything compiled on the loading
screen; creatures drawn from baked paint; lit per vertex". GameCommon `godot/baked-look` has the bake's own record.

### Shader programs: what one costs (`tools/compile_cost.gd`, ANGLE D3D11, cold, desktop)

`godot --path . --audio-driver Dummy --rendering-driver opengl3_angle --resolution 320x240 -s res://tools/compile_cost.gd
-- --synthetic --variants --kinds=<k,...> --parts --shaders=<res://...>` times the first frame a thing is drawn in.
Each program is salted, so no cache has it.

| program | first draw |
| --- | --- |
| an empty spatial shader lit per pixel (or a StandardMaterial3D) | 1.4 to 1.5 s |
| the same lit per vertex (`vertex_lighting`) | 0.27 s |
| the same unshaded | 0.14 s |
| soft shadow filters off, Lambert over Burley | no change |
| `limits/opengl/max_lights_per_object` 1 (12 here) | slower: 2.6 s |
| another version of a compiled program: an omni light near / spot / no fog / a sky | 0.08 / 0.08 / 0.04 / 0.14 s (per vertex: 0.07 / 0.07 / 0.04 / 0.00) |
| a MultiMesh of a compiled program | 0 |

Eight creatures (garibaldi, sardine, octopus, crab, orca, blue whale, dumbo octopus, nudibranch), seconds:

| | per pixel | per vertex | per vertex, fragment one texture (baked) | unshaded, texture |
| --- | --- | --- | --- | --- |
| mean | 2.51 | 1.01 | 0.60 | 0.42 |
| range | 1.56 to 3.78 | 0.46 to 1.99 | 0.45 to 0.78 | 0.28 to 0.58 |

So a creature program was about 1.4 s of Godot's per-pixel lighting, 0.3 s of the program itself, 0.3 s of its own
vertex code and 0.5 to 2 s of its procedural markings (noise, scales, spots, loops, cartoon eyes). Turning unused
varyings into locals saved nothing (FXC prunes them). Scenery shaders, per pixel -> per vertex: kelp 1.55 -> 0.54,
mangrove 2.56 -> 0.81, sea grass 1.42 -> 0.51, seaweed 1.43 -> 0.47, kit rock 1.58 -> 0.35, kit soft 1.41 -> 0.41,
ruins 1.48 -> 0.33, wreck 0.89 -> 0.27, net 0.90 -> 0.29, flock 1.61 -> 0.56, plankton 1.62 -> 0.46, garden eels 1.94
-> 0.54, anemone 2.15 -> 0.70, hair 2.05 -> 0.55, nettle 2.94 -> 1.37; the water 7.0 s (kept per pixel: its light is
its fragment).

### Programs, before and after

About the same number of programs (the hitch logger saw 297 shader-and-format keys; each creature component still has
its own, as their vertex code differs), each far cheaper: 110 creature shaders baked (from 2.5 s to about 0.6 s), 9
creature shaders kept unbaked but lit per vertex (the squids, comb jelly, anglerfish, firefly squid, nettle, ghost
whale's is unshaded), 16 scenery and plant shaders lit per vertex, every StandardMaterial3D of the sea lit per vertex.
Only the water and the sand (and a few unshaded effects) are compiled per pixel.

### Cold tour (390x844, ANGLE, Godot's shader cache moved aside, `-- --dive --tour`, which now passes or fails)

| | before (pushed 2026-11-19) | after |
| --- | --- | --- |
| loading: everything compiled | never (the start waited for 75 m round the start, then ~280 programs compiled in play) | 137 to 157 s from the engine's start (five runs; 128 to 134 s of it warming) |
| title start button | live at 118 to 142 s | live when the title shows |
| in play: frames over 50 ms | 100 (worst 5.8 s; 183 s of warm-ups in play) | 0 (PASSED; worst frame 31 ms) |
| in play: frames over 33 ms | not counted | 0 |
| frame time in play, median / 95th / 99th | 6.5 / 11.4 / 14.1 ms | 6.2 / 10.3 / 11.9 ms |
| second visit (cache kept) | 2.9 s to the start button | everything compiled at 23 s |

The loading screen's time, split (tour 1 of the new scheme): the sea's first frames 23 s (the water alone is 7 s);
each creature kind 0.45 to 0.9 s (median 0.63; the octopus 4.5 s, its arms' loops); the same lit by a lamp 0.12 s
each (18 s in all); materials 0.1 to 0.9 s.

A Windows desktop's first visit in Chrome is the worst case (FXC); a phone's GL driver compiles faster, and a browser
keeps compiled programs for later visits.

### Looks: every kind compared (`tests/baked_compare.gd`, the old shader beside the baked look, side and three-quarter)

Same markings for nearly every kind. Different:
- Eyes no longer look about or blink: baked looking ahead, open (`eye_look`, `blink` were live).
- No sheen or rim at grazing angles (the shaders' `VIEW` terms), no sparkle on starfish and urchins, no wrinkles
  drawn as normals (sperm whale).
- Koi and guppies: three baked patterns each, not one per fish.
- Fine speckles on small fish (guppies' dots, corydoras' freckles, the leatherback's spots, a seal's or narwhal's
  mottling) are softer; the emperor angelfish's stripes needed a sharper mipmap (`texture(..., -1.0)`).
- Light per vertex: the shine is broader and softer on everything lit per vertex.
- Not baked (look as before): Humboldt and giant squid (living colour cells), comb jelly, deep anglerfish (pulsing lure),
  firefly squid, the ghost whale (added light), the big jellies (own `light()`), the submarine (already a texture).

### Pack and memory

186 baked pictures, 6.5 MB imported (lossy WebP with mipmaps), about 88 MB of RGBA8 on the GPU, all loaded at the start;
baked meshes 14 MB (compressed as the importer does; the atlas UVs full floats: half floats came out empty), against
about 14 MB of game and far models that a web build now leaves out (listed in `creatures/*/baked/*primed.txt`). A web
export from the working checkout: index.pck 55.1 MB, of which about 7 MB were another session's uncommitted title-captain
pictures: about 48 MB from what is committed, against 37.9 MB at the last push.

Found on the way (each fixed): the warm-up showed particles as plain meshes, but particles draw as a MultiMesh
with colours and custom data, another version (the first leap at Steamer Lane stalled 62 ms); a component that shows its
far model only when stepped (the octopus) or keeps its script under another name (the shrimps) was baked without it;
lighting the submarine's own materials per vertex as each one was made came with 200 to 380 ms frames on
the dive (gone without it), so creatures' own plain materials stay per pixel and are compiled once on the loading screen.

### Left

- Native GL (not a browser): a steady 130 ms frame on the way to the sand flats with a warm cache, absent under ANGLE.
- Not tried in a real browser or on a phone.

## Motion families (2026-11-19, night)

The user: "each animal should not need its own shader for swimming or motion"; they chose a few shared motion families,
each animal setting its numbers as uniforms. CLAUDE.md, "Decision: motion families"; GameCommon
`godot/motion-families`. After the bake each creature still had a copy of its own shader for its vertex code, so about
110 creature programs were compiled on the loading screen; now 98 of the 104 baked creature shaders move by one of four.

### Programs

| | before | after |
| --- | --- | --- |
| creature programs (baked, plus kept unbaked) | 104 + 9 | 4 families (swim, swim_sheer, flap, jointed) + 6 kept on their baked copy + 9 unbaked |
| shader-and-format keys the hitch logger saw (whole sea) | 297 | 226 |
| a family's program under ANGLE (`tools/compile_cost.gd --shaders=`) | (a baked creature 0.45 to 0.9 s) | swim 1.5 s, flap 1.4, jointed 1.3 on a sphere; jointed about 3 s on its first animal (the leg routine) |

The `radial` family (two-sided arms) exists but has no animal: the starfish, its only one, moved to `jointed`.
Left on their own baked copies: the moray, giant Pacific octopus and channel catfish (their scripts move points along
ropes they write into a texture each frame) and Scenery's anemones, the clownfish's host anemone and the crinoid (they
sway by the global `water_clock` and where they stand, not by `phase`).

### Loading (390x844, ANGLE, Godot's shader cache moved aside, `-- --dive --tour`)

| | before | families | families + batched warm-up |
| --- | --- | --- | --- |
| first visit: everything ready | 137 to 157 s | 81.7 s (72 s warming) | 67.9 s (59 s warming) |
| second visit (cache kept) | 23 s | 25.3 s | 11.1 s |
| in play: frames over 50 ms / over 33 ms | 0 / 0 | 0 / 0 (PASSED) | 0 / 0 (PASSED) |
| frame time in play, median / 95th / 99th | 6.2 / 10.3 / 11.9 ms | 6.3 / 9.9 / 11.7 | 7.1 / 11.3 / 13.3 |

One run each. With programs cached the warm-up was paced at one thing every two frames (about 1,300 frames), so the
Warmer now shows a batch while frames come back under 60 ms (doubling to 16) and one at a time after a frame over 300 ms
(`Warmer.BATCH_*`). What is left of a first visit: the sea's first two frames (about 20 s: the water, sand, sky and
the rest at once), the first frame of each family (1.5 to 3 s), the kept unbaked shaders (the squids, firefly squid,
comb jelly, anglerfish, nettle: 1.5 to 2.5 s each), the submarine's plain materials per pixel (about 3 s), the docks'
and outcrops' plain materials, the breakers.

### Motion: own shader against family (`tests/motion_compare.gd`)

Every kind, 8 frames through a beat plus mouth open, turning and arched, from above and the side; the number is the
share of the drawn outline where they disagree. 0.000 to 0.003 for nearly every fish, whale, ray and crustacean.
Larger, each looked at: long-spined urchin 0.31, pencil 0.09, purple 0.08 (each spine swings back and forth along its old
ellipse, so single thin spines differ; the urchin reads the same); guppy males 0.02 (the tail's turn behind the joint);
dumbo octopus 0.016 (the web's curve as a straight move); cameroceras 0.014; Spanish dancer 0.013; sea serpent 0.015.
Differences only at settings the game sets through a middle value: the seahorse's grip at a half (0.06 to 0.09:
straight from loose to gripped), the flying fish's spread wings (0.08: they bend with the wave where they were stiff),
the betta flaring (0.04), trilobites rolled up (0.06 to 0.22: their legs and spines bend with the body). Unused by
the game: the remora riding a host and the sea lion's `fold` lose their stilling of the wave. Every spec file's
comment lists what it does differently. Eyes: as baked (looking ahead, open). Where an old shader also squashed the eye's shape to blink, the family does too;
the painted look and blink are not back (each kind's eye drawn per pixel again would add its fragment code back).

### Pack and memory

Each baked vertex carries its labels (CUSTOM0 grows from 2 to 4 floats, CUSTOM1 to CUSTOM3 are 4 floats each): 557,163
vertices in 273 baked meshes, 522,580 labelled, 56 bytes more each: about 29 MB more vertex memory on the GPU when
every kind is loaded, 2.5 MB more on disk (baked meshes 12.9 -> 15.4 MB) and about 2.8 MB more in the pack (a web export
from the working checkout: 57.9 MB, against 55.1 MB the same way before). Half floats would halve it but draw wrong in
GL Compatibility. Texture memory is unchanged (the families read the same baked pictures, about 88 MB).
