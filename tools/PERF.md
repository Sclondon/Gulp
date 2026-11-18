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

## Before and after (390x844, the sea's picture 195x422)

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
