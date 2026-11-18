# The sea's places as levels: biomes, foliage and what goes where (design, phase one)

Written 2026-11-18 by the level-design agent. **Phase one is design only: no game file was changed.** Phase two
(building it) waits until the builder now reworking `scripts/scenery.gd`, `sea.gd` and `life.gd` for speed is done.
The design comes first (builders read that); the research and its sources are at the end.

## The user's words

- 2026-11-18: "and the foliage needs a smart realistic distrbtion, do research on kelp forests and othe under sea
  biomes and make good game design \"levels\" out of them as we've described them so far"
- The places, earlier (CLAUDE.md, tools/MONTEREY.md): "a kelp forest and rocky area, a open ocean shelf, and then a sea
  grass bed area, a nudibranch, also probalby a smaller reef area, and a sandy open area with garden eels"; "a mangrove
  / river entrance area for fresh water fish"; "a trench area"; "the map should be based on monterey bay, with the reef
  wreck at the x"; "another location should be the docks / marina"; "atlanits ruins" "in the lower spot of the trench";
  "pirate ship wreck"; "theres should be more docks by santa cruise / marina at the dock"; "the margrove river part goes
  in the center part where that river meets the bay"; "the map doesnt need to be super huge either, nicely curated and
  big enough areas to recreate the intetion of hte map"; "there shoule be an outcropping of rocks near the pirate ship,
  pillars and shards and an island that seals rest on"; "the reef should be built into a ship wreck like an onld timy
  passenger titanic style".
- And (relayed by the coordinator, 2026-11-18): a fish market at Carmel, in the south, along with Monterey and Santa Cruz.

**Every number, place, rule and choice below is Claude's (this agent's) unless it is in quotation marks above.** The
user has seen none of it. Where realism and the user's wishes part, the wish stands and the place is made convincing
around it (section 4).

---

## 1. What is wrong now (from pictures of every place, 2026-11-18)

Taken with `--near=<place> --shot=3` in the game and `tools/bay_shot.gd` (scenery only, no depth static).

1. **The whole floor is one pale rippled sand.** Kelp holdfasts, the breakwater, the canyon's walls, the slough's mud,
   the harbour floor and the reef shelf are all the same sand. Nothing reads as a rocky reef; the canyon walls are
   smooth sand cliffs 40 m high with nothing on them (canyon_head picture).
2. **Kelp stands on sand, in even clumps, with the rocks put down beside it at random** (kelp and kelp_south
   pictures). Giant kelp needs rock: in life the forest *is* the rock reef. There is no canopy over the forest from
   below, no understory, no edge, no channel, no clearing: from inside it is a stand of identical bamboo-like stalks.
3. **The liner's reef is confetti**: 150 tropical pieces scattered evenly over open sand at 30 m, coral heads standing
   alone, nothing thicker on the hull or on high points (wreck_shelf picture). A reef grows on hard structure.
4. **The sand flats are empty**: from the middle of the zone the picture is rippled sand edge to edge (sand picture);
   the eels are in 7 small patches somewhere in a 34 m circle. No landmark, no layer, no way to find anything.
5. **Zones are circles, so plants spill where they cannot live**: the sea grass circle reaches 33 m deep over the
   canyon's lip (probe: 0 to 32.8 m inside it), the reef circle reaches 46 m, the south kelp circle 0 to 15 m; mangrove
   roots stand on the canyon head's rim (canyon_head picture, top); the whale shark cruises over the sea grass (grass
   picture: "open" includes the water over the canyon's basin, which reaches the shallows).
6. **The docks' piles are bare grey posts with a few blue blobs** (docks_santacruz picture), not the mussel-and-anemone
   columns of the concept art; the floor under them is the same clean sand.
7. Depth static: the reef, pirate, ruins, trench and open pictures from the game are all static, because the starting
   amplifier stops at 15 m. That is DESIGN.md working as meant, but it means half the sea is unseen until gear is bought:
   the levels below lean on that ladder (each place's "gear step").
8. Carmel (where the user now wants a fish market) is, on the floor as it is, a flat of 0 to 3 m water behind the
   Carmel Canyon's head (probe below): too shallow for a pier with a net.

```
depth (m) round Carmel, world x -20..80 (step 8), z 120..160 (step 4); # land
z 140   27   24    4    2    8    0    1    2    2    1    #    #    #
z 144   28   21   16   21   17    1    1    1    1    1    0    #    #
z 148   29   26   24    #    #    0    0    0    0    0    0    #    #
```

## 2. The five changes that matter most

1. **A substrate map** (rock, sand, mud, shell, coralline crust) on Bay's 2 m grid, drawn by the floor shader, and read by
   every placement rule. Kelp only on rock, eelgrass only on sand and mud, sea pens only on mud and fine sand, corals
   only on hard things. This one change makes every place read as what it is (section 3.1).
2. **One rule-based placer replacing the hand loops in `scenery.gd`**: per-biome tables of layers (what, on which
   substrate, which depth, which slope, density at the core and at the edge, clump size, spacing, height by depth), a
   noise mask per layer, and keep-outs (paths, clearings, lanes, landmark footprints). Same seed, same sea every time
   (section 3.2, data format in 6).
3. **The kelp forests rebuilt as reefs with channels**: rock fingers running out from the shore with sand channels
   between them (the swim path and the diver's walk), the forest thick at its core and thinning to its edge, a surface
   canopy, an understory of short stipitate kelps, coralline pink rock, and one urchin barren as the open clearing.
4. **Growth on structure, not on sand**: the liner, the pirate ship, Atlantis, the outcrop, the piles and the canyon's
   rock outcrops carry their life on their surfaces (by which way a face looks: up, side, under), thickest on high
   points and edges facing the current; the sand round them gets a rubble halo and thins out with distance.
5. **Zones by habitat, not by circle**: each biome is a mask (its circle or line AND its depth band AND its substrate),
   so nothing grows or swims where it cannot live; the giants keep to deep open water; a few kinds move (section 7).

---

## Phase two: what is built (2026-11-18)

Built at the coordinator's word, on top of the performance pass (tools/PERF.md). The user's six questions (section 9)
were answered with **Claude's defaults, all changeable**: (1) the liner's shelf stays; its chest moves to the armoured
suit (DESIGN.md edited); (2) Carmel Bay deepened (a cove, `Bay.HARBOURS`) and a short Stillwater-Cove-like pier with two
skiffs; (3) the eel garden on its ridge off Santa Cruz plus a small colony beside the liner; (4) mangroves with the real
slough round them; (5) sargassum cut to 3 mats (the asset kept); (6) a subtle warmer, clearer tint in the liner's pocket.

- **Floor types** (`scripts/floor_types.gd`, `FloorTypes`): one byte a corner of Bay's 2 m grid (sand, rock, mud, shell,
  crust, white), by the rules of 3.1 and the reef masks in `Biomes.REEFS`. **No new shader**: GameCommon's sand already
  paints kinds per corner (`SandGround.paint_all`), so rock is its SANDSTONE kind (its banded rock reads as layered
  reef and canyon mudstone), mud its DIRT, shell its COARSE, crust its RED and Carmel's sand its WHITE, recoloured by
  their uniforms. `Sea._ready` calls `FloorTypes.paint(sand)`. The piles' shell rings are painted by `Scenery._paint_shells`.
- **The placer** (`scripts/biomes.gd`, `Biomes`): `REEFS` (kelp south with two channels and the barren, kelp north,
  the outcrop's talus, Carmel's reef) and `TABLES` (kelp_south, kelp_north, outcrop, carmel, grass, slough,
  docks_monterey, points, walls), each a list of layer rules as in section 6. `Biomes.run` fills floor pieces (drawn by
  Scenery's LodField, near 8 m and far now 60 m, matching the plants' `SEEN`), kelp, grass and seaweed (drawn by their
  own components, each in cells with its own near and far). `grow_on` puts pieces on a thing's spheres by which way
  the face looks.
- **Moved into the placer** (retired from `scripts/scenery.gd`): `_place_rocks`, `_plant_kelp`'s clumps, `_plant_grass`'s
  circle and the slough's tufts, `_plant_seaweed`'s zone rows (only the liner's red weed and 3 sargassum mats stay there),
  KELPS, TUFTS, SLOUGH_TUFTS. Still in scenery.gd as before: the cliffs (now with sponges on the canyon walls from the
  placer), the breakwater, the live anemones, the clownfish anemones, the mangroves, the docks, the outcrop's stacks.
- **The kelp forests** (5.2, 5.3): rock fingers with two sand channels in the south (the main one through the arch, now
  turned across it), a pink barren with purple urchins, understory (SEA_PALM as the stand-in), red weed, feather boa,
  fans, sponges, strawberry anemones and stars near the rocks; kelp only on rock, thinning to the edges (its lengths
  short of the surface at the edge, canopy at the core). South 116 plants, north 22, Carmel 4 (139 in all, 180 before).
- **Growth on structures**: the dock piles (mussel clumps hanging under the surface, strawberry anemones on the piles
  under a deck, green anemones on the lit mooring piles, a star at the foot, shell hash round it); the liner's bommies
  (26, thinning from the hull out to 32 m; hard corals and clams on their lit tops, fans, soft corals and sponges on
  their sides; nothing loose on the open sand any more). **Not done:** growth by these rules on the liner's hull, the
  pirate ship, the ruins and the outcrop's stacks (their own scripts place their own; the rules are in 3.4).
- **Limits and moves**: every layer keeps to its depth band and floor type (the eelgrass stops at 8 m, short of the
  canyon's lip; nothing roots in a channel); the 16 kinds of section 7 moved in `scripts/species.gd`; `Sea.place` keeps
  every "open" kind to water 30 m deep or more.
- **Markets**: `Sea.MARKETS` (Monterey's commercial wharf end, the Santa Cruz wharf end, Carmel's pier end). The
  selling is another stage's. Carmel's fish shed is not built.
- **Set pieces**: the old one (GameCommon `old_one`) asleep on the canyon's deep floor at (-40, 26), about 85 m, facing
  Atlantis, its body and head as rocks, `wake` eased towards 1 within 22 to 55 m of the player; the reef back walking a
  15 m loop at 0.45 m/s on the deep floor west of the shelf's edge round (-138, -62); both light models beyond 60 m.
- **The kit** (section 8): see "Phase two, second pass" below for what is built since. Was the order: reef slabs,
  understory kelp, bull kelp, pile sleeves, surfgrass, sea pens, sand dollars, whale fall, kelp rafts (so the open
  ocean still has 3 sargassum mats and no rafts yet).

### The budget, measured (tests/perf.gd, 390x844, the sea's picture; same machine, same harness)

| place | draws before | after | triangles before | after | frame ms before | after |
| --- | --- | --- | --- | --- | --- | --- |
| start | 10 | 20 | 86k | 97k | 5.3 | 5.0 |
| kelp | 79 | 97 | 123k | 136k | 6.5 | 6.8 |
| grass | 57 | 54 | 256k | 248k | 6.9 | 6.1 |
| sand | 8 | 15 | 145k | 147k | 6.1 | 6.1 |
| reef (liner) | 149 | 152 | 338k | 354k | 5.7 | 7.8 |
| pirate | 64 | 73 | 193k | 188k | 6.6 | 5.9 |
| ruins | 72 | 75 | 147k | 142k | 7.0 | 7.1 |
| docks | 166 | 179 | 129k | 140k | 7.0 | 6.8 |
| river | 36 | 25 | 215k | 175k | 9.4 | 9.4 |
| trench | 4 | 11 | 64k | 72k | 5.4 | 5.8 |
| open | 4 | 11 | 64k | 71k | 4.7 | 4.9 |

(kelp, grass, docks, reef "after" are the second run, with the trimmed densities; the rest the first.) Within the proxy
(150k triangles, 150 draws): start, kelp, sand, ruins, trench, open. **Over before and still over**: the liner (its own
reef: PERF.md), grass (102k of it is a sea nettle and 55k a flock: animals, not plants), pirate, river (both on triangles,
lower than before) and the docks on draws (179: the kelp and seaweed cells along the breakwater, two draws a piece type
of the floor kit). The frame's ms vary 1 to 3 ms with other sessions running.

### Phase two, second pass (2026-11-18, later): forests, floor paint, growth on structures, the kit

All choices here are Claude's (the user's asks: "the foliage needs a smart realistic distrbtion ...", "make sure
things have textures that fit our art style", models built in Blender by script).

- **The kelp forests read as forests**: giant kelp now stands in clumps of 4 to 7 plants round one spot (each plant
  three stipes, so 12 to 20 stipes a clump) at fewer, wider-spaced clump sites, the noise leaving lanes between; core
  plants 1.2 to 1.6 times the depth long so they lie along the surface; over each core clump 3 mats of **canopy**
  (`kelp_canopy`) float down-current at the surface: a dark lid with light between seen from below. The understory is
  the new **understory kelp** (Pterygophora and Laminaria variants) instead of the sea palm stand-in; **reef slabs** pave
  the rock; the reef's rock pieces are tinted darker; the sand inside the kelp circles is painted with the sand's damp
  kind (`FloorTypes.UNDER_KELP`), a darker olive floor. Kelp blocks are 12 m (not 8): half the draws.
  The north forest is now the **bull kelp** one (78 plants on the ledges, a few giant kelp deeper); bull kelp also at the
  south forest's and Carmel's outer edges.
- **The floor paint**: rock's beds of colour softened in Sea's copy of the sand shader (one `replace` in `_caustics`,
  the same program); rock darker and warmer; **mud is the sand's DAMP + PACKED kinds** tinted by `damp_tint` (smooth,
  no ripples), no longer DIRT, which drew as cracked dry ground in the harbours.
- **Growth on structures** (`Scenery._grow_on_structures`, `Biomes.grow_on_skin`): on the liner, the pirate ship and
  Atlantis, rays from outside find the real skin of their meshes (`Mesh.generate_triangle_mesh`), so pieces sit on what
  is seen; by which way the face looks (3.4's lists, warm for the liner, cold for the rest), depth, height and the
  current; never within a swim route's room + 1.2 m (each set piece's own routes). On the outcrop's islet, stacks and
  shards, the same rules on their spheres: a waterline band of mussels (0.3 to 2.5 m), anemones and stars on lit tops,
  sponges and fans on the deeper sides. About 600 pieces, drawn by their own LodField with full models only within
  4 m (`GROWTH_NEAR`). wreck_view, pirate_view and ruins_view `--check` pass (growth adds no rocks).
- **The kit** (section 8), each by its own `tools/build_<name>.py` on GameCommon's sea floor kit machinery
  (`tools/kit_build.py` imports it; vertex colours, the kit's own rock and soft shaders, no new program), into
  `models/kit/`, read by `scripts/kit.gd` (Kit: SeaFloorProps' calls, plus the sea's own pieces), each looked at from
  six sides and checked for inside-out faces (closed parts by volume, sheets two-sided): built **reef slabs** (3),
  **understory kelp** (2), **bull kelp**, **surfgrass** (on the rocky points), **sea pens** (orange on the sand flats,
  587; tall white and **sea whips** on the canyon's mud, 1,212), **sand dollar beds** (the 3.5 to 5 m band), the
  **kelp canopy** mat and the **drift kelp paddy** (4 afloat over the open ocean, still: no drift). Not built: pile
  growth sleeves, the whale fall, Carmel's fish shed, and 11 to 16.
- **Not right yet**: growth on the pirate ship reads only close up (the kit's cold pieces are small for a 30 m hull: a
  big plumose anemone piece would carry it); the outcrop's bull kelp ring found no rock shallower than 14 m (the
  outcrop's floor is 18 to 24 m), so the ring is not there; the paddies do not drift; rock still shows faint banding.

| place (390x844) | draws before | after | triangles before | after | frame ms before | after |
| --- | --- | --- | --- | --- | --- | --- |
| start | 19 | 19 | 96k | 94k | 6.5 | 7.3 |
| kelp | 100 | 96 | 146k | 145k | 7.5 | 9.3 |
| grass | 54 | 59 | 247k | 249k | 6.2 | 9.1 |
| sand | 15 | 20 | 147k | 150k | 7.3 | 9.1 |
| reef (liner) | 151 | 171 | 351k | 379k | 8.9 | 6.8 |
| pirate | 71 | 84 | 193k | 217k | 7.6 | 7.2 |
| ruins | 69 | 79 | 137k | 139k | 6.5 | 7.7 |
| docks | 183 | 124 | 146k | 142k | 6.3 | 8.1 |
| river | 25 | 23 | 179k | 172k | 9.8 | 9.7 |
| trench | 9 | 14 | 72k | 74k | 6.3 | 6.7 |
| open | 11 | 16 | 70k | 72k | 6.3 | 6.3 |
| beach | 14 | 15 | 85k | 89k | 7.0 | 7.5 |

(`tests/perf.gd`, same harness both times; frame ms swing 1 to 3 ms with other sessions on the machine: the GPU
column of the after run was 1 ms higher everywhere, the start included. Between the runs another session's title
boat began to draw at the liner: about 20 of its draws there are not this pass's.) Within the proxy (150k triangles,
150 draws): start, kelp, sand, ruins, docks (now), trench, open, beach. Still over: the liner (its own reef), grass
(animals), pirate (the growth added 24k), river.

## The eight biomes (2026-11-18, built to the user's regions and the concept art)

The user: "We need to make proper biomes, with concept art for each considering our needs. Green is kelp forest, yellow
is sand dune sea, red is sea grassy fields, purple is rocky crags" (outlines over the overhead chart); "the green
section should be kelp forest not dune sea"; "You shouldnt be that exact just look at the map and see the areas I was
trying to highlight"; then "Trench, beach shallows, and river need to count as biomes as well, and the reef on the
ship"; and "there should be a seaweedy / grassy area around the mouth instead of regular beach". Concepts (style brief
in CLAUDE.md): `tools/art_src/concept_biome_{kelp,dunes,grass,crags,trench,beach,river,reef}.png`. Everything below
that is not a quote is Claude's pick.

**Where each is: `scripts/biome_regions.gd` (BiomeRegions), the one source.** Worked out once on Bay's 2 m grid: each
corner's biome (the first in `ORDER` that has it: river, reef, trench, beach, crags, kelp, grass, dunes) and how far in
from its edge it is (a chamfer distance), so `at(x, z)`, `weight(name, x, z)` (0..1 over `EDGE` 8 m), `bounds(name)`,
`spot(rng, name, inside)` are lookups. The user's four are rough polygons (`SHAPES`, read by eye, unchanged from the
first reading); the reef is an outline round the liner's bommies; the river is Elkhorn Slough's channel and banks
(`Bay.SLOUGH`, however it winds) plus the estuary within 25 m of its mouth (96, -40) shallower than 10 m; the beach is
the shore's strip (within `Bay.BEACH`, under 6 m); the trench is every floor deeper than 28 m (the bake raises all else
to the 26 m shelf) less Atlantis's basin (`RUINS_CLEAR`, the ruins dress their own). Where a drawn outline runs down a
canyon wall, the trench wins (it is before them in ORDER), so no outline needed smoothing. `shape_weight` reads the
polygons alone, for Bay's dunes (the grid needs the floor, the floor needs the dunes).

**Who reads it.** `Biomes.TABLES` (one table a biome with `"region"`; densities fade over the edge by `weight`; the old
circles kelp_south, kelp_north, outcrop, outcrop_south, grass, sand_flats, slough, points, canyon_floor and walls are
gone, folded into the eight; Carmel's cove reef and the Monterey harbour floor stay as circles); `FloorTypes._type_at`
(the floor's make by biome, below); `FloorTypes.paint` (the kelp's damp dark sand and the dunes' pale sand by `weight`);
`Bay.dune_height`; `Sea.ZONES` ("kelp", "sand" (the dunes), "grass" and a new "crags" carry `"region"`: `Sea.place`
picks a point anywhere in the region, 4 m in from its edge; `zone_at` tries the circle zones first, then the regions);
`Scenery._in_zone` the same. Species: moray, rockfish, octopus, lobster, starfish, purple urchin, crab, seal and
garibaldi also live in "crags"; bat rays and leopard sharks in "grass" too.

| biome | floor (FloorTypes) | what stands and grows (Biomes table, Scenery) | in the sea (desktop count) |
| --- | --- | --- | --- |
| kelp | rock ridges across the current with sand channels between (noise stretched 0.45 x 1.6, turned 0.32), breaking up towards the edge; pink crust barrens; damp dark sand between | giant kelp in clumps of 4 to 7 on rock 5 to 28 m, groves and lanes by a slow noise (0.04), 1.05 to 1.3 times the depth (to the canopy, capped 25 m), canopy mats over the core clumps; boulders, reef slabs, understory kelp, red weed, feather boa shallow, urchins on the barrens and by rocks, fans, sponges, strawberry anemones, stars | 275 kelp plants, 1,237 understory, 1,886 red weed |
| dunes | clean sand painted the sand's PALE kind (paler, more ripples); **the floor's own shape**: `Bay.dune_height` | open and bare: sea pen meadows in patches, sand dollars, scallops, a few lone boulders; garden eels in three colonies (`Scenery.EEL_COLONIES`: the old ridge off Santa Cruz and the liner's colony moved in); two half-buried anchors with chain runs (`DUNE_ANCHORS`, the docks kit's Anchor and Chain scaled 1.6 and 2.2) | 712 sea pens, 260 eels |
| grass | sand with silty mud patches | eelgrass at 520 tufts per 100 m² at the core (clumps of 2 to 4), bare blowouts where the noise is low, five sandy paths (`keep`), sea lettuce; olive and straw colours and a stronger lean (`Scenery._plant_grass`), drawn to 40 m (`GRASS_SEEN`) in 12 m squares | 11,632 tufts |
| crags | rock nearly everywhere, sand pockets, crust patches | leaning pinnacles (`lean` 0.4) and hard-leaning ones as shards (0.75), stacks and ledges, rare arches, boulder piles in clumps, reef slabs: all kept 2 m under the surface, off the islets' columns (`avoid`) and 10 m round the pirate ship's lane (`keep`); on them (`grow` -> `Biomes.grow_spheres`, grown in `Scenery._grow_on_structures`) white plumose anemones, pink strawberry anemone sheets for coralline, stars and urchins; on the floor plumose clumps, strawberry sheets, stars, urchins, hydrocoral, fans, red weed. The outcrops' own stacks and shards now wear the kit's rock, tinted dark (`CRAG_ROCK`) | 15 + 5 pinnacles, 12 stacks, 1 arch, 81 plumose clumps on the floor (more grown on the rocks) |
| trench | the old rules: rock on steep risers in beds, mud on the deep flats | rock ledges down the risers, sponges and fans on them, and on the silted treads (concept: white anemones, sponges, sea pens on every ledge) plumose clumps by the rock, sponges, tall white sea pens and whips (now from 28 m, on sand or mud) | 242 ledges, 287 pens, 31 plumose clumps, 170 sponges |
| beach | the old rules (rocky points, Carmel's white sand) | the rocky points as before (surfgrass, rockweed, feather boa, anemones, mussels, stars) plus tide-pool rock patches on the sandy shores with surfgrass, rockweed, anemones and stars round them (`near_rock`); the sand dollar band, now 2.5 to 6 m and on slopes to 0.5 | 22 tide-pool rocks |
| river | mud and silt (sand in patches out at the mouth) | eelgrass on the banks and the estuary's flats, sea lettuce, red weed; the mangroves (`Scenery._plant_mangroves`) now stand from 2.5 m inside the channel's edge to 2 m up the bank, so their roots arch into the water | 1,291 tufts, 536 weed |
| reef | as before | the liner's own reef and the bommies (unchanged) and now the warm pocket's corals, fans and sponges on the canyon's rims and walls either side of it | 44 |

**New kit piece: `plumose_anemones`** (`tools/build_plumose.py` -> `models/kit/plumose_anemones.glb`, `.json`,
`tools/blend/kit_plumose.blend`): three or four white Metridium columns with lobed, frilled crowns, 1,632 triangles, the
light one 264 (two anemones); closed shapes, checked by the kit's winding test from six sides (ok). The kit's soft
shader, its own sway (`Kit.KELP_SWAY` 0.06). GameCommon's living anemone has a plumose too, but as a node each; this one
draws by the hundred.

**Budget, measured** (`--perf=...`, 390x844, the sea's picture; other sessions on the machine: frame ms swing 1 to 3).
Before (the table above, second pass) -> after. Places are `Sea.ZONES`' middles, and "sand", "grass" moved to their
regions, so those two rows are new places, not the same ones.

| place | draws | triangles | frame ms | note |
| --- | --- | --- | --- | --- |
| start | 19 -> 93 | 94k -> 153k | 7.3 -> 3.8 | the start is at the dunes' edge beside the crags (not looked into further) |
| kelp | 96 -> 97 | 145k -> 126k | 9.3 -> 7.3 | lighter |
| sand (now the dunes) | 20 -> 23 | 150k -> 92k | 9.1 -> 8.4 | |
| grass (now the west meadow) | 59 -> 109 | 249k -> 178k | 9.1 -> 6.2 | 48k of it eelgrass in 10 draws; the rest the pirate ship (31 draws), the kit's far pieces, the sand |
| pirate | 84 -> 92 | 217k -> 171k | 7.2 -> 9.2 | |
| crags (new) | 85 | 131k | 8.9 | |
| river | 23 -> 25 | 172k -> 186k | 9.7 -> 12.8 | 84 animals drawn (their schools), not plants |
| trench | 14 -> 67 | 74k -> 106k | 6.7 -> 7.3 | **heavier**: the treads' anemones, sponges and pens, and the place now looks at a dressed wall |
| reef | 171 -> 161 | 379k -> 254k | 6.8 -> 16.2 | the frame here swung most (render cpu 4.6 ms); triangles lower |
| beach | 15 -> 11 | 89k -> 86k | 7.5 -> 6.1 | |

Within the proxy (150k triangles, 150 draws): kelp, sand, crags, trench, beach; just over on triangles: start (153k),
pirate (171k), grass (178k), river (animals). What got heavier: the start (draws and triangles) and the trench.

**Decisions** (all Claude's, for the user's regions):
- *Regions on a grid, not polygons asked each time.* What: BiomeRegions bakes biome and distance-to-edge once on Bay's
  2 m grid. Why: the placer and FloorTypes ask tens of thousands of times; depth-ruled biomes (trench, beach) need the
  floor anyway. Practice: a biome/splat map over the terrain grid, as terrain systems paint layers. Alternatives:
  point-in-polygon each call (slow, and the trench and beach are not polygons), a picture mask (another file to keep in
  step).
- *Dunes in the floor's height.* What: `Bay.dune_height`: GameCommon's `SandDunes` field of transverse ridges across the
  current (1.5 to 3.2 m, lee faces softened below 2.7 m so the 2 m grid does not draw teeth), only inside the dunes
  outline and on the shelf (faded out above 22 m and past 27 m). Why: the concept's rolling dunes are shape, not paint.
  Practice: a procedural height layer added to a base heightfield, masked by a biome weight. Alternatives: rebaking
  `data/monterey.bin` with them (one more thing to redo on every rebake), ripples only in the shader (flat from any
  distance). Sand streaming off the crests was left out: GameCommon's `SandWind` thickens the level's fog and turns the
  sky sand-coloured (built for a desert), too much to bend for one effect.
- *The crags' shards are the kit's pinnacles leaning hard over*, not the docks kit's Shard and Pillar spread over the
  region (tried first: their plain paint drew pale and flat beside the kit's rock). The two islets keep theirs, now in
  the kit's rock.
- *Growth on the crags' rocks by the same rules as the outcrop* (`grow_on` on each rock's spheres), white plumose and
  pink strawberry sheets standing in for coralline.
- *The trench excludes Atlantis's basin* (a 30 m circle) and the river includes the estuary (the user's mouth meadow),
  both as rules in BiomeRegions.

**Rough or unverified**: nobody has swum them; pictures were taken with `tools/bay_shot.gd --biomes` (no post shader,
no animals) and compared with the concepts by eye, two to three passes each. The trench picture shows its walls but not
its ledges' anemones well; the beach's turquoise water, surf foam and the river's tea-coloured water were not done
(the water's colour is one for the whole sea); the dune sea has no sand streaming off its crests; the kelp's understory
is thinner than the concept's; the grass reads greener than the concept under the game's light. Phones untried.
`tests/setpiece_hits.gd --only=docks` (or kit) prints script errors on the sea's own kit pieces (`Dictionary` has no key
`reef_slab_a`...): not looked at (the test is another agent's, being changed).

---

## 3. The system

### 3.1 The substrate map

`Bay` gets a second grid beside the heights (same 2 m cells, made at the same time): one byte a cell.

| Code | Substrate | Where it comes from (rules, in order; first match wins) | How the floor draws it |
| --- | --- | --- | --- |
| 4 | coralline crust (pink rock) | rock cells inside an urchin barren mask (3.3 kelp) | rock, tinted rose-pink, no ripples |
| 1 | rock | (a) inside a biome's **reef mask** (kelp reefs, the outcrop's talus, rocky points); (b) slope over 0.6 with noise > 0.35 (canyon walls' outcrops, the shelf's edge); (c) within 6 m of a rocky shore segment (`ROCKY_SHORES`: Lighthouse Point, Point Pinos to Cypress Point, Point Lobos, the breakwater) | dark grey-brown stone, a crack pattern, no ripples, caustics kept |
| 2 | mud | the slough, the harbours (dredged), the canyon's floor deeper than 45 m with slope under 0.3, the basin round Atlantis | dark olive-brown, smooth, no ripples, faint pocks |
| 3 | shell hash | a ring 1.2 m round every pile's foot, the rubble halo of the wrecks (0 to 6 m out) | pale, speckled, coarse |
| 0 | sand | everything else | as now (rippled) |

How the floor draws it: `Sea` already makes a patched copy of the sand's shader (for caustics); it also takes an
`ImageTexture` of the substrate grid (R rock, G mud, B shell, A crust, 0..1, linear filtering so the borders are soft),
blends the colours and fades the ripples out on rock and mud. One texture, no new mesh, no new draw. (Claude's pick:
painting the floor is the usual way terrain shows ground types; the alternative, covering rock with rock meshes, would
cost thousands of triangles a reef.) Rock cells also get low relief from the **reef slabs** (kit item 2) placed over
them, so rock is not only a colour.

`Bay.substrate(x, z) -> int` reads it; every placement rule reads it.

### 3.2 The placer

One script, `scripts/biomes.gd` (`Biomes`), reading one table per biome (section 6), replacing `_place_rocks`,
`_place_reef`, `_plant_kelp`, `_plant_grass`, `_plant_seaweed`, `_plant_live_anemones`, `_plant_anemones`,
`_plant_mangroves`, `_plant_eels` (the docks', outcrop's and cliffs' builders stay: they are built structures, and
gain the growth rules of 3.4).

For each biome, for each layer, in the order listed (big things first, so later layers can keep clear of them):

1. **Candidates** on a jittered grid whose cell is the layer's `spacing` (a cheap Poisson-disc: one candidate a cell,
   moved at random inside it; no two closer than `spacing`).
2. **Mask**: the candidate must be inside the biome's area (its zone patch, or its line for the slough and canyon), in
   the layer's `depth` band, on one of its `substrate`s, under its `slope_max` (or over its `slope_min`), and not in a
   keep-out (the biome's `paths`, `clearings`, the wrecks' lanes, Atlantis's terrace, landmark footprints, the run's
   start column under the boat).
3. **Density**: `density[0]` per 100 m² at the core, falling to `density[1]` across the outer `edge` metres of the
   biome's mask (a smoothstep on distance to the mask's edge, measured on the 2 m grid once per biome), times the
   layer's **noise mask** (FastNoiseLite simplex fbm, the layer's own `freq` and `seed`, remapped so `cover` of the
   area is above zero). Keep the candidate with probability density x cell² / 100.
4. **Clumps**: each kept candidate is a parent with `clump` [min, max] children within `clump_r` metres (kelp
   recruits near adults; anemones in clones; urchins in fronts).
5. **Affinity**: some layers want to be near something (`near: ["rock_prop", 2.0]`: urchins and stars at boulder feet,
   lobsters under ledges) or away from it (`away: ["kelp", 1.2]`).
6. **Size and height** by rule: `height` either `[from, to]` metres, or `"reach"` (kelp: the water's depth x
   `reach`, longer than deep means it lies along the surface as canopy), shrinking towards the edge (`edge_reach`).
7. **Draw**: everything into the component that draws it (KelpForest, SeaGrassBed, SeaweedBed, MangroveStand, the
   props' MultiMeshes), each in cells of 8 or 16 m with `far` at the fog, light meshes past `near`.

### 3.3 Paths, clearings, landmarks, breadcrumbs (the level-design layer)

Each biome names, in its table:
- **One landmark** that can be seen from its edge through the fog (30 to 45 m): a tall shape with its own silhouette and,
  where the water is dark, its own light. The sonar's sign for the place points at it.
- **Entrances** (2 or 3): where the neighbouring biomes run into it, each marked by a change you can see from the
  outside (the forest's edge thinning, the eelgrass's rim, a rubble trail).
- **A main path**: a polyline 4 to 8 m wide kept clear of tall things (kelp, cliffs, roots) and of rock props, on a
  floor a diver can walk (slope under 0.35). Fish swim it; the diver walks it; it leads past the landmark.
- **Clearings** (circles 6 to 14 m) where nothing tall grows: places to see out, to fight, to turn round.
- **Hiding places**: thick cover a small fish can slip into and a hunter cannot follow (dense kelp core, eelgrass,
  root tangles, the wreck's interiors, crevices under ledges).
- **A place of danger** and **a place of reward**, both named per biome.
- **Breadcrumbs**: small things laid along the path in a line (shells on sand, a trail of rubble, a chain on the floor,
  a run of anemones) that draw the eye on to the next thing; the usual trick of open worlds (Breath of the Wild's field
  design: tall shapes to aim at, smaller ones on the way).
- **Negative space**: the open sand and blue water between places is kept empty on purpose. It makes the places read
  and keeps the cost down. A transition band (6 to 12 m) blends two neighbours' low layers; tall layers do not cross it.

### 3.4 Growth on structure (piles, wrecks, rocks, ruins)

Sessile life on a built or rock thing is placed on its **surface**, not on the floor: points sampled on the thing's
collision spheres (they are already registered with `Sea.add_rock`; a sphere's surface point and its outward normal
are enough at this size), filtered by which way the face looks:

| Face | Normal's y | Gets (cold water) | Gets (the liner's warm pocket) |
| --- | --- | --- | --- |
| up, lit (top of a rock, a deck, a funnel's rim) | over 0.6 | coralline crust colour, foliose reds, sea stars, giant green anemones (shallow) | table, brain and staghorn corals, giant clams |
| side (walls, hull sides, pile shafts) | -0.3 to 0.6 | plumose anemones, strawberry anemone sheets (shaded sides first), hydrocoral, gorgonian fans across the current, sponges | sea fans across the current, soft corals, sea rods, barrel sponges |
| under (overhangs, under decks, inside) | under -0.3 | strawberry anemones, sponges, nothing green | cup corals (orange), sponges; no hard coral (no light) |

Thickest on high points and edges that face the current (`Scenery`'s current runs (0.3, 0.1), roughly from the west):
weight x (1 + 0.8 x height above the floor / the thing's height) x (1 + 0.5 x max(0, normal . -current)).

### 3.5 The budget (a phone)

Targets for scenery alone (plants, props, floor growth; not animals, not the wrecks' own meshes), in view at once:
**at most about 120,000 triangles sent, 60 draw calls, 2,500 instances**, everything past the fog (`SEEN`, 55 to 60 m)
culled by cells, full meshes only within `near` (8 m kelp, 10 m grass, 12 m seaweed and props). The kit's own counts:
kelp 168 triangles a metre near / 30 far, holdfast 156; a grass tuft 81 to 108 / 27; prop pieces 250 to 6,000 / a fifth
of that. A kelp forest is the dearest thing in the sea (the component's own check: 300 plants in 40 x 40 m, 177,000
triangles from outside, 270,000 to 356,000 inside), so kelp counts are set by the budget first and realism second
(section 5.2). Each biome's own budget is in its section.

---

## 4. Where the wishes and the real bay part (and how each is kept)

| The wish | The real bay | How it is kept convincing |
| --- | --- | --- |
| A coral reef (with clownfish, tangs, butterflyfish) on the liner at the X off Point Lobos | No reef-building corals in California; the nearest are in the Gulf of California. Monterey's reefs are cold-water: hydrocoral, gorgonians, plumose and strawberry anemones, sponges, as colourful as coral in a torch's light | The liner's shelf is **a warm pocket**: its own water tint (warmer, clearer), its own light, a hard edge where cold kelp-coast life stops and coral starts, life only on the wreck and its bommies. Its colonisation follows how real wrecks are colonised (soft corals and fans first, on edges; hard corals last, on lit tops). Whatever made it warm is not written (lore is asked of the user first, DESIGN.md) |
| Mangroves at Elkhorn Slough | No mangroves north of about 26.8 N on the Pacific side of Baja (Elkhorn is about 36.8 N). The real slough is pickleweed salt marsh, mudflats, eelgrass channels, Olympia oysters, sea otters, harbour seals, bat rays, leopard sharks | The mangroves stand where the marsh would (a fringe of red mangroves on the channel's edge, black mangrove's breathing roots on the mud behind), and everything else in the slough is the real Elkhorn: mud, eelgrass in the channel, oyster clumps, otters resting, seals on the mud banks, bat rays and leopard sharks. The water goes fresher up the slough (marine at the mouth, fresh at the top, where Carneros Creek comes in), which is where the aquarium fish live |
| Garden eels in the sand off Santa Cruz | Garden eels are tropical. The nearest, the Cortez garden eel (Heteroconger digueti), lives in the Gulf of California, 2 to 34 m | They stay where the user put them, as **one colony on a low ridge of coarse sand** across the current (where garden eels live: current-swept coarse sand), the rest of the flat being real California sand (sand dollars, sea pens, tube anemones, flatfish). Option for the user: a second small colony on the liner's sand apron, where it is true to life (not done: "only what was asked") |
| Tropical reef fish, lionfish, cuttlefish | Not Californian (cuttlefish are not found in the Americas at all) | Keep them inside the liner's warm pocket and Atlantis, nowhere on the cold coast |
| Horseshoe crabs | Atlantic and Asian, estuarine | Move them to the slough's mud (estuarine, beside the mangroves: the one fantasy place they fit) |
| Walrus, narwhal | Arctic | Left in the open ocean (as now) until there is a cold sea |
| Sargassum mats over the open ocean | Sargassum is Atlantic | Kept few; the Pacific's own drifting thing, a **drift kelp paddy**, becomes the open ocean's landmark (kit item 10) |
| The canyon 100 m deep, the bay 290 m across | The real canyon is 1,000 to 2,000 m deep in the bay | Already the map's call (MONTEREY.md); the canyon's life is taken from its upper 100 to 400 m |

---

## 5. The places

Coordinates are world metres (x east, z south; north is -Z), as in `Sea.ZONES` and MONTEREY.md. Densities are per
100 m². "Fish" is the player as an animal; "diver" is the boy in the suit (DESIGN.md). The gear steps are DESIGN.md's:
amplifier 15 / 30 / 50 / 100 m (how deep the fish may go), suit 10 / 25 / 50 / 100 m (how deep the diver may walk).

### 5.1 The beach strip (all round the shore, 0 to 5 m)

**Real model.** Monterey Bay's shore is long sandy beaches (Santa Cruz to Monterey) broken by rocky points (Lighthouse
Point and Natural Bridges at Santa Cruz; Point Pinos, Lovers Point and Cypress Point on the peninsula; Point Lobos).
The surf-zone sand holds mole crabs, surfperch, flatfish; just outside it, a narrow band of sand dollars standing on
edge. The rocky points are intertidal reefs with clear bands: barnacles high, mussels and goose barnacles in the middle,
surfgrass, feather boa kelp, giant green anemones and pink coralline at the bottom.

**Layers** (surface to floor): foam and swash; surfperch and smolts in the wave-wash; on rocky points the band of
rockweed and mussels at the waterline, surfgrass and feather boa below; on sand, open rippled sand, then the sand dollar
band at 3 to 5 m where the strip meets the shelf.

**Plan**

```
  shore ##########################  rocky point ####
  swash  ~~~~~~~~~~~~~~~~~~~~~~~~~~   :::rock:::  (mussel band, rockweed at 0-1 m)
  0-2 m  sand, surfperch in the wash  surfgrass  (1-4 m, bright green ribbons on rock)
  2-4 m  sand, a few scallops/razors  feather boa, giant green anemones, sea stars
  3-5 m  ||||||| sand dollar band (2-3 m wide, follows the 4 m line) |||||||
  5 m+   -> the shelf's sand / the next biome
```

Landmark: none of its own (a strip has no one place: MONTEREY.md); it is the edge everything else is seen against. The
rocky points are its landmarks locally.

**Placement rules**

| Layer | Substrate | Depth | Slope | Core / edge (per 100 m²) | Clump, spacing | Size |
| --- | --- | --- | --- | --- | --- | --- |
| rockweed (SeaweedBed ROCKWEED) | rock | 0 to 1.5 | any | 60 / 20 | 3-6 within 0.6 m, 0.4 m | 0.25-0.4 |
| mussel clumps (prop `mussel_clump`) | rock | 0 to 2 | any | 40 / 10 | 2-5 within 0.8, 0.5 | 0.9-1.4 x |
| surfgrass (kit 6) | rock | 0.5 to 4 | < 0.8 | 120 / 30, noise cover 0.6 | 4-8 within 1 m, 0.35 | 0.5-1.2 m |
| feather boa (SeaweedBed FEATHER_BOA) | rock | 1 to 5 | < 0.8 | 10 / 3 | 1-3 within 1.5, 1.2 | 1.5-2.5 m |
| giant green anemones (prop or creature, kind GIANT_GREEN) | rock | 0.5 to 5 | any | 15 / 4 | 2-6 within 0.5 (clones), 0.4 | 1-1.6 x |
| ochre / bat stars (prop) | rock | 0 to 5 | any | 6 / 2 | single, 0.6 | tints |
| sand dollars (kit 8) | sand | 3 to 5.5 | < 0.25 | 600 / 0 (a band: only where depth 3.5-5), noise cover 0.7 | beds of 30-80 within 2.5 m, 0.12 | 0.06-0.09 m |
| scallops, razor clams | sand | 1 to 5 | < 0.3 | 2 / 0.5 | single | - |

**Animals by layer.** Wash and top: `surfperch` (real: barred surfperch), `smolt`. Floor: `halibut`, `stingray`,
`horseshoe_crab` (move to the slough: section 7), `scallop`, `razor_clam`, `crab`. Rocky points: `starfish`,
`purple_urchin` in cracks, `otter` resting off the points. Visitors: `leopard_shark`, `bat_ray`, `eagle_ray` (not
Californian: keep to the liner, section 7).

**From far / blending.** Bright sand, foam overhead, the water greenest here. The sand dollar band is a darker grey line
that marks "the shelf starts here"; it fades into the shelf's plain sand. Rocky points blend into kelp where a kelp
biome touches (the south kelp's shore side).

**Play.** Fish: the safe nursery at the start of a run (small food, few hunters; gulls later, when birds come).
Diver: the canvas suit's ground (0 to 5 m), the first photographs at a rocky point. **Gear step: none.**

**Budget.** It is long and thin, so per view: about 400 instances, 25,000 triangles, 10 draws (rockweed, mussels,
surfgrass, boa, anemones, stars, sand dollars, clams).

### 5.2 The big south-east kelp forest (Cannery Row, round (53, 42), r 30, 6 to 16 m)

**Real model.** The kelp along Cannery Row and Pacific Grove: giant kelp on granite reef from just past the surf to
about 20 m, in a mosaic with sand channels; understory of Pterygophora and Laminaria; pink coralline rock; at its
seaward edge a band of Cystoseira and then sand or barren (Pearse and Hines 1979 off Santa Cruz: forest at 3 to 7 m,
understory under the canopy, a Cystoseira band at the seaward edge, beyond it mostly barren with coralline crust).
Since 2014 the peninsula has lost much of its canopy to purple urchins: a patchwork of forest and barrens, the otters
feeding in the forest patches.

**Layers.**
1. Canopy (0 to 2 m): fronds lying along the surface, thick at the core, gaps of light between. Otters float in it.
2. Mid-water (2 m to 3 m off the floor): the stipes, the "trees"; schools of blue rockfish and surfperch, kelp bass.
3. Understory (0.5 to 1.5 m): stipitate kelps standing like palms on the rock.
4. Floor (0 to 0.5 m): foliose red weed, coralline pink crust, sea stars, urchins in cracks, anemones, crabs, lobsters
   under ledges.

**Plan** (north up; shore to the east and south; the canyon's arm to the north)

```
            N   canyon arm (deep, dark: the edge of the forest drops into it)
   . . . . . . . . . . . . . . . . . . .
   .  sand        ~ ~ ~ thin edge ~ ~ ~  ######## shore (Seaside)
   .        RRRRRRR      RRRRRRRRRR      #######
   . west   RRRRRRRRR c  RRR(B)RRRRRR    ######
   . edge   RR{K}RRRR h  RRRRRRRRRRR   rocky
   .(bull   RRRRRRRRR a  RRRRRRRRRRR   point
   . kelp)   RRRRRRR  n  RR  RRRRRR   (surfgrass)
   .          A---arch--n---path---->  shore entrance
   .        RRRRRRRR  e  RRRRRRRRRR
   .        RRRRRRRRR l  RRRRRRRRRR      ######
   .  sand   RRRRRR      RRRRRRRR      #######  Monterey docks (south-east)
   . . . . . . . . . . . . . . . . .
   R = rock reef with kelp   {K} = the cathedral (thickest kelp, the canopy closed)
   (B) = the urchin barren (clearing, pink rock, no kelp)   A = the arch (landmark)
```

Three reef fingers run out from the shore to the west-south-west, two sand channels between them (5 to 8 m wide, the
current runs along them). The main channel (the path) runs from the shore entrance west past the **arch** (the landmark:
the existing `rock_arch` moved onto the path, kelp standing on its top so its silhouette reads from 40 m) and out of
the forest's west edge to the open sand. Entrances: the west edge (from the open bay; thin kelp, bull kelp standing
alone), the north edge (from the canyon's arm, a drop), the shore and the docks to the south-east (shallow, surfgrass).

- Clearings: the **urchin barren** (B, 12 m across on the middle finger: pink rock, purple urchins thick, no kelp: the
  light comes down) and the two channels' mouths.
- Hiding places: the cathedral core (K, kelp at 1 plant to 6 m², too thick for big fish to follow), crevices under the
  ledges.
- Danger: the west edge, where the forest meets open water (`white_shark` and `sea_lion` patrol it, as real white sharks
  hunt along kelp edges near seal haul-outs); the barren is open ground with nowhere to hide.
- Reward: the ledges' foot on the middle finger (lobsters, crabs, prawns, octopus: food); for the diver, a photograph
  in the arch and an abalone shell to sell (Claude's pick of finds).

**Placement rules** (first five are drawn by existing components)

| Layer | Substrate | Depth | Slope | Core / edge | Clump, spacing | Height / size |
| --- | --- | --- | --- | --- | --- | --- |
| reef slabs (kit 2) on every rock cell | rock | 5 to 16 | < 0.6 | 1 a 16 m² cell, 70% | single, 3.5 | 0.3-1.2 m relief |
| boulders and ledges (`rock_boulder`, `rock_split`, `rock_ledge`, `rock_stack`) | rock | 5 to 16 | any | 3 / 1 | 1-3 within 3 m, 3 | 0.8-1.5 x |
| giant kelp (KelpForest) | rock (or a boulder's top) | 6 to 16 | < 0.7 | 12 / 2.5 (edge 8 m), noise cover 0.75 | 2-4 within 1.5 m, 1.6 | depth x 1.05-1.4 (canopy); edge plants depth x 0.6-0.95 |
| bull kelp (kit 4) | rock | 5 to 13 | < 0.7 | 0 at core / 3 in the west edge's outer 8 m only | single, 2.5 | depth x 1.1-1.3 |
| understory kelp (kit 3; SeaweedBed SEA_PALM as a stand-in) | rock | 4 to 15 | < 0.7 | 40 / 10, noise cover 0.6, more where kelp is thick | 5-12 within 2 m, 0.6 | 0.8-1.5 m |
| foliose red weed (SeaweedBed RED_ALGAE) | rock | 3 to 16 | any | 80 / 20, noise cover 0.55 | 6-15 within 1.2, 0.3 | 0.15-0.3 |
| feather boa (FEATHER_BOA) | rock | 2 to 7 | < 0.8 | 6 / 2 | 1-2, 1.5 | 1.8-3 m |
| coralline crust (substrate 4 paint) | barren mask, and 30% of rock (noise) | - | - | (floor paint, no instances) | - | - |
| purple urchins (prop `urchin_purple`, low mesh past 6 m) | rock, crust | 5 to 16 | any | 15 in cracks (near rock props 1.5 m) / 300 in the barren | fronts of 10-30 within 2 m, 0.15 | 0.9-1.3 x |
| red urchins (prop) | rock | 6 to 16 | any | 4 / 1, near rock 1 m | single | - |
| strawberry anemone sheets (prop) | rock props' side and under faces (3.4) | 6 to 16 | - | 1 per 3 m² of face | - | - |
| hydrocoral, sea fans (red, gold), vase / puffball sponges | rock props' side faces | 10 to 16 | - | 1 per 6 m² of face | - | - |
| giant green and plumose anemones (creature, kinds 0 and 2) | rock | 5 to 16 | any | 4 / 1 | clones of 2-4 | 1-1.8 x |
| ochre and bat stars, sunflower stars (props; the creature stars move) | rock, crust | 5 to 16 | any | 6 / 2 | single | tints |

Keep-outs: the channels (polylines, 3 m each side clear of kelp and rocks), the barren (circle), a 4 m circle round the
arch's two openings.

Kelp numbers, from the budget: the forest's rock is about 55% of 2,800 m² (about 1,550 m²); at 12 per 100 m² core and
2.5 at the edge that is about 120 plants (180 for both forests now). Real Macrocystis forests vary widely (the papers
found give method, not one figure; a few adults per 10 m² is a fair reading of the surveys), and the game's is set to
what reads as a forest from inside at phone cost.

**Animals by layer** (kinds in `Species.ALL`).
- Canopy: `otter` (rafts of 2 at the surface, resting, real), `seal` passing, `sea_lion` (2, the west edge).
- Mid-water: `rockfish` (as blue rockfish: midwater schools here, not only on the floor: give it band 0.1 to 0.7 in
  kelp), `surfperch`, `kelp_bass`, `garibaldi` (southern, keep few), `barracuda` (southern; keep to the west edge),
  `bonito` and `mackerel` passing the edge, `salmon` at the edge.
- Floor: `crab`, `lobster` (under ledges), `octopus` (missing from kelp now: add), `eel` (moray: keep to crevices of
  the arch, few), `starfish`, `sunflower_star`, `purple_urchin` (now 10 scattered: put them in the barren's front and
  the cracks), `nudibranch`, `sea_hare`, `thorny_seahorse` (not Californian; keep few), `sea_bass` (giant sea bass,
  hovering at the west edge's floor).
- Edge and channels: `bat_ray`, `halibut`, `leopard_shark` on the channels' sand; `white_shark` at the west edge only.
- Missing animals worth having here (creatures, not kit): lingcod, cabezon, sheephead, señorita, kelp crab, abalone,
  bat stars (props exist).

**From far / blending.** From the open bay: a wall of olive-gold stems under a dark lid of canopy, sunbeams through the
gaps, the arch's dark bulk on its west face. It thins at its west edge into scattered bull kelp then sand (8 m band);
to the north it ends at the canyon's lip (the rock goes on down the wall as outcrops, 5.5); to the south-east it meets
the docks' breakwater (rock to rock, the same red weed and urchins on both).

**Play.** Fish: the first big hunting ground (smolt to salmon sizes), hide in the core, eat in the channels, watch the
west edge. Diver: walk the main channel from the shore, through the arch, out to the barren; canvas suit for the shore
half (to 10 m), hard-hat for the deep west half. **Gear step: amplifier 15 m covers all but the west edge's floor;
suit 10 m the shore half, 25 m all of it.**

**Budget (inside the forest, looking along a channel).** Kelp: about 50 plants within the fog, 10 within `near`:
10 x 12 m x 168 + 40 x 12 m x 30 + holdfasts = about 40,000 triangles, 30 draws. Understory and weed: 600 instances,
20,000 triangles, 6 draws. Props: 40 rocks and 300 small pieces, 35,000 triangles, 14 draws. Total about 95,000
triangles, 50 draws: inside the target.

### 5.3 The north-east kelp (Capitola and Aptos, round (54, -64), r 19, 1 to 11 m)

**Real model.** The north bay's kelp grows on low reefs of soft mudstone and sandstone (the Purisima Formation off
Capitola and Soquel Point): flatter, patchier and shallower than the peninsula's granite; bull kelp is dominant from
Monterey Bay northwards, so this forest is the bull kelp one.

**Layers.** A thinner canopy of bull kelp floats and blades; few stipes in mid-water; low flat reef ledges with
understory, much sand between them.

**Plan**

```
   N  ######## shore (Capitola) ########
      ~~~ beach strip ~~~~~~~~~~~~~~~~~~
        ==ledge==   o  ==ledge==        o = bull kelp alone on a ledge
      ====ledge====    ===LEDGE===  <- the long ledge (landmark: a low wall 2 m high,
         o  o    sand        o          bull kelp along its crest like a fence)
      ==ledge==  o  ==ledge==
   W  (sand flats west)        S -> the canyon's arm (drop)
```

Landmark: **the long ledge**, a 25 m low mudstone wall (made of `rock_ledge` and `rock_slab` in a row, reef slabs in
front), bull kelp standing along its crest like a fence: from far it is a line of floats against the light.
Entrances: from the beach strip (north), from the start's open water (west), from the canyon's arm (south, a drop).
Path: along the foot of the long ledge (its sand side). Clearing: the sand between ledges. Hiding: under the ledges'
overhangs. Danger: the canyon's arm at its south edge (what comes up the canyon: `humboldt` at night). Reward: the
ledges' overhangs (crabs, prawns, octopus).

**Rules** as 5.2, with: giant kelp 3 / 1 (a few, on the deeper ledges only, 8 to 11 m); **bull kelp 10 / 3** on every
ledge's crest and top (single, 1.8 m spacing, depth x 1.1 to 1.3); rock only as ledges (reef mask: noise freq 0.08,
cover 0.35, stretched along the shore 3 to 1); understory 25 / 8; urchins few (no barren here).

**Animals.** Canopy: `otter`. Mid: `surfperch`, `rockfish`, `salmon` passing, `mackerel` at the edge. Floor: `crab`,
`starfish`, `octopus`, `halibut` on the sand, `stingray`. Same kinds as the south forest, fewer of each.

**From far / blending.** A dotted line of floats and a low dark wall; no dark canopy lid (a lighter, greener place
than the south forest: the two forests must not look the same). Blends north into the beach strip, west into the open
sand of the start.

**Play.** Fish: close to the start, the first kelp a run meets. Diver: the canvas suit reaches all of it (to 11 m but
for a few pockets). **Gear step: none (amplifier 15 m, suit 10 m covers most).**

**Budget.** Bull kelp is lighter than giant kelp (one stipe, one float, a crown of blades: kit 4); about 70 plants,
25,000 triangles in view, plus 20,000 of ledges and weed. About 50,000, 30 draws.

### 5.4 The sand flats off Santa Cruz (round (-74, -78), r 34, 12 to 20 m)

**Real model.** Monterey Bay's shelf is mostly sand and mud. Shallow sand looks like the low beach (sand dollars in
dense narrow beds at its shoreward edge, which move with the seasons); deeper it turns to fine sand and mud with sea
pens, sea pansies, tube anemones (Pachycerianthus, low intertidal to at least 20 m), burrowing worms, flatfish, sand
stars, Dungeness crabs, bat rays digging feeding pits. Garden eels are not Californian (section 4).

**Layers.** Water column: sardine and anchovy schools pass over (the start's open water is next door). Floor: ripples;
the sea pen meadow on the deeper, finer half; tube anemones scattered; the eel garden on its ridge; pits dug by bat rays;
the old bottom net (the Fishers' trawl) lying in it.

**Plan**

```
  N  shore (Santa Cruz) ##### beach strip ##### Santa Cruz docks (north-east)
       ||||| sand dollar band (beach edge) |||||
          rippled sand, scallops, sand stars
                .  .  pits  .   .
   W    (/////// eel ridge ///////)  <- the eel garden on a low ridge across the
   shelf    tube anemones  ' ' '          current (landmark: hundreds of eels
   edge   ,,,,,,,,,,,,,,,,,,,,,,,,,,        standing up together, a sunken mooring
          ,, sea pen meadow (deeper) ,,     block with its chain up to a buoy)
          ,,,,,,,,,,,,,,,,,,,,,,,,,,
                   S -> the pirate hollow and the seal rock
```

Landmark: **the eel garden** itself (one colony of about 260 on a ridge 30 m long, 6 m wide, raised 0.8 m: a field of
heads that sways and drops as you come), and **a mooring block with a chain to a surface buoy** (kit 14), the one
vertical line on the flat, seen from 40 m. Entrances: from the beach strip (north, over the sand dollar band), from the
start (east, open water), from the pirate hollow (south, the sand goes on). Path: the eel ridge's crest and on south to
the pirate hollow (breadcrumbs: a line of scallops and sand dollars dragged by the current, then a dropped cutlass, a
barrel stave as the wreck nears; the wreck's owner places those). Clearings: it is all clearing; the point is the
features in it. Hiding: none but the eels' holes (for very small fish: the bat ray pits). Danger: the Fishers' bottom
net dragged across it; `halibut` lying hidden in the sand (ambush). Reward: the eel garden (food for a small fish:
eels taken as they are now), sand dollars and clams.

**Rules**

| Layer | Substrate | Depth | Core / edge | Clump, spacing | Size |
| --- | --- | --- | --- | --- | --- |
| eel ridge (Bay: a low ridge in the height sum, coarse sand) | sand | 13 to 17 | - | one, along -0.3 rad | 30 x 6 m, 0.8 m high |
| garden eels (colony) | the ridge mask only | - | 400 / 80 on the ridge | patches of 20-50 within 3 m, 0.35 | as now |
| sea pens (kit 7) | sand (fine), mud | 15 to 22 | 25 / 3, noise cover 0.5 | 3-8 within 1.5, 0.5 | 0.25-0.45 m |
| tube anemones (creature TUBE) | sand, mud | 12 to 22 | 1 / 0.3 | single, 3 | 1-1.8 x (keep under 20 a view: they are creatures) |
| sand dollars (kit 8) | sand | the beach edge band (5.1) | - | - | - |
| bat ray pits (floor decal: a soft hollow in the sand's dent map, if SandGround's dents allow) | sand | 10 to 20 | 1 / 0.5 | single | 1-1.5 m |
| scallops, razor clams, sand stars | sand | 10 to 20 | 3 / 1 | single | - |
| mooring block, chain, buoy (kit 14) | sand | 15 | one | - | - |

**Animals.** Over it: `sardine` and `anchovy` swarms (the Schooling's riders), `devil_ray` (not Californian: open water
only), `smolt`. Floor: `halibut`, `stingray`, `bat_ray`, `leopard_shark`, `crab`, `pistol_shrimp`, `mantis_shrimp`
(tropical, keep few), `trilobite`, `cheeked_trilobite` (fantasy: fine on sand), `scallop`, `razor_clam`. Missing worth
having: Dungeness crab, sanddab, sand star, angel shark.

**From far / blending.** Pale, bright, open; the eel field moving; the chain's line. Blends north into the beach band,
south into the pirate hollow's sand (no edge: the wreck is the change), west into the shelf's edge (5.13).

**Play.** Fish: crossing open sand is dangerous for a mid-sized fish (no cover); small fish hunt the eels; the bat rays
and halibut are the hunters. Diver: walk the ridge, photographs half buried by the chain's block. **Gear step: amplifier
30 m (it is 12 to 20 m deep), hard-hat suit 25 m.**

**Budget.** Eels 260 x 232 = 60,000 triangles in one draw when all in view (already measured, one MultiMesh); sea pens
600 x about 60 = 36,000 (one draw, light past 10 m); the rest small. About 100,000 at the ridge, 8 draws. If the
phone needs it, the eels' far rows can draw every other eel.

### 5.5 The Monterey Canyon (the head at Moss Landing (94, -8) down the arm to the basin, 22 to 100 m)

**Real model.** The canyon's head starts about 150 m off Moss Landing harbour, so deep water comes right to the shore;
deep-water animals come up the canyon into the shallow head (sixgill and prickly sharks). Its walls are mostly mud,
with rock outcrops on the steeper, rougher parts; long-lived clams and worms bore into the hard mud; on the rock,
sponges, deep corals, feather stars and tunicates, and rockfish shelter among them (Soquel Canyon, its northern branch:
sandstone, mudstone and shell hash; rockfish on high-relief walls and boulder fields). On the floor (the axis): mud,
sea pens and sea whips, brittle stars, sea cucumbers; and whale falls (MBARI found a gray whale at 2,891 m in 2002,
about 20 tonnes of food for the floor, studied for years).

**Layers.** Lip and rim (22 to 40 m): the shelf's sand ends at a crisp lip; rock outcrops along it. Walls (40 to 90 m):
mud with bands of rock outcrop where steep; the life is on the rock. Floor and basin (70 to 100 m): soft mud, sea pens,
brittle stars, the whale fall; the dark.

**Plan** (the arm, west from the head)

```
  north kelp (5.3)                       slough mouth / Moss Landing (5.14)
      \                                     /
  ---- lip --- outcrops -- lip --- outcrops -- HEAD (22 m) <- sixgill shark comes up here
  ~~~~~~~ wall: mud, rock bands with sponges, Metridium, fans, rockfish ~~~~~~~
  ______________ axis: mud, sea pens, brittle stars, sea whips ______________
  ~~~~~~~ wall ~~~~~~~                                           (east)
  ---- lip --- south kelp's north edge (5.2) ----
      |
      v  basin (70-100 m): THE WHALE FALL (landmark, glowing mats) ... Atlantis (5.7) to the south-west
```

Landmarks: **the head** (the shelf breaks off under you: the strongest "here it gets deep" moment of the map), and in
the basin **the whale fall** (kit 9: a gray whale's bones, 12 m, on the mud at about 85 m round (-40, 20), white mats
of bacteria glowing faintly, crabs and hagfish on it). The sleeping old one in the canyon floor (DESIGN.md's last chest)
is the wreck's and the story's: not placed by this design.
Entrances: the head (from the slough and the beach), over either lip (from both kelp forests), up out of the basin
(from Atlantis and the open ocean, along `CANYON_OUT`). Path: the axis, head to basin (a fish follows the floor down;
the diver needs the deep suit). Clearings: the axis is open mud. Hiding: crevices of the rock bands. Danger: the dark
and what lives in it (`giant` squid, `humboldt` packs, `anglerfish` lures), the depth limit. Reward: the whale fall
(food for scavenging fish), deep finds for the diver.

**Rules**

| Layer | Substrate | Depth | Slope | Core / edge | Clump, spacing | Size |
| --- | --- | --- | --- | --- | --- | --- |
| rock outcrop bands (the substrate rule: slope > 0.6, noise > 0.35), drawn with **cliff pieces turned to the wall's downslope direction** and `rock_ledge` / `rock_slab` | rock | 25 to 95 | > 0.6 | 1 piece a 12 m of wall where the band is | rows along the contour | 0.7-1.2 x |
| plumose anemones (creature PLUMOSE, giant: scale 2-3) | rock band faces | 25 to 90 | - | 1 per 5 m² of face | clones 3-6 | 2-3 x |
| sponges (vase, puffball; deep glass sponge kit 15) | rock band faces | 40 to 95 | - | 1 per 8 m² | - | 1.5-2.5 x |
| red sea fans (gorgonian, prop) across the current | rock band side faces | 30 to 90 | - | 1 per 10 m² | - | 1.5-2 x |
| feather stars (creature `feather_star` is tropical; use `sea_lily` deep) | rock band | 60 to 100 | - | 1 per 15 m² | - | - |
| clam and worm burrows (floor decal: holes in mud) | mud on walls | 30 to 90 | 0.3-0.6 | (paint) | - | - |
| sea pens (kit 7, taller deep variant) and sea whips | mud | 60 to 100 | < 0.3 | 15 / 3, noise cover 0.5 | 4-10 within 2 m | 0.4-1.0 m |
| brittle star carpets (creature `brittle_star` as kinds; props for the many) | mud | 60 to 100 | < 0.3 | patches 1 / 0.2 | carpets of 20-60 within 2 m | - |
| the whale fall (kit 9) | mud | 80 to 90 | < 0.2 | one | - | 12 m |

**Animals by layer.** Lip: `rockfish`, `lingcod` (missing), `prawn` (spot prawn: move here from the reef and the docks:
real spot prawns live on deep rock), `octopus`. Walls: `rockfish`, `prawn`, `brittle_star`, `sea_lily`. Mid-water over
the canyon: `humboldt` (move some here from the open: real in the canyon since about 2000), `firefly_squid`,
`comb_jelly`, `pyrosome`, `lanternfish` swarm (night, up), `viperfish`, `gulper`. Floor: `anglerfish`, `giant` (the
giant squid), `dumbo_octopus`, `cheeked_trilobite`, `ammonite` (fantasy, keep), `cameroceras`. Head: a sixgill shark
coming up (missing creature: `blue_shark` is the nearest; no). Missing worth having: ratfish, sablefish, hagfish,
sixgill shark, basket star.

**From far / blending.** From the lip: blue-black falling away, pale rock bands with white Metridium like snow on a
cliff, the axis invisible. The lip is a crisp edge (the shelf's sand stops; rock outcrops start); it blends at the head
into the slough's mud and the beach.

**Play.** Fish: the way down to everything deep; the head is where small fish are safest from the deep and where the
deep's hunters come up at night. Diver: only with the deep suit. **Gear step: amplifier 50 m for the arm's upper
walls, 100 m for the floor and the whale fall; suit 50 / 100 m.**

**Budget.** Cliff pieces (light model) 20 in view x 1,200 = 24,000; anemones and sponges 150 instances 30,000; sea pens
and stars 400 instances 25,000. About 80,000 triangles, 20 draws. The dark (fog close at depth) culls the rest.

### 5.6 The pirate ship and the seal rock (pirate hollow (-80, -13), 18 to 24 m; the outcrop (-98, -24))

**Real model.** Seal Rock and Bird Rock off Pebble Beach: bare rocks in the surge where harbour seals and sea lions haul
out, ringed by bull kelp and giant kelp, granite boulder talus round their feet; white sharks visit seal rocks. A cold
wreck on sand at 20 m: in Californian water a wooden wreck is soon covered in plumose anemones (they carpet cold-water
wrecks on their high points), with rockfish in its holds and lingcod on it.

**Layers.** The islet's top (out of the water): seals and a sea lion (as now). Waterline and surge (0 to 3 m, on the
stacks): barnacles and mussels, rockweed, sea palms on the most exposed stack (sea palm is a surge-zone plant: its one
truthful home in the map). 3 to 12 m: a ring of bull kelp round the outcrop. 12 to 22 m: the stacks' faces (strawberry
anemones in the shade, hydrocoral, red fans, sponges), and at their feet a talus of fallen boulders spreading towards the
ship. The hollow (18 to 24 m): sand, the wreck lying in it, its scour drift.

**Plan**

```
                 N   sand flats (5.4)
        stacks  |  |   shards / /
       |  (ISLET: seals)  |   bull kelp ring (o)
        o o o  talus  o o o
          \\\ boulder talus \\\   (breadcrumbs: barrel, cannonballs, a cutlass)
             \\\    ___________________
    W            \ <  PIRATE SHIP (heeled) >   hold: rockfish, the chest
  shelf's           ~~~~~~~ scour drift ~~~
  edge              sand, anchor and cable out to the east
                      S -> the canyon's lip (5.5)
```

Landmark: **the islet and its stacks** (out of the water: seen from the surface and from below as dark pillars against
the light) and the ship's high stern and leaning foremast. Entrances: from the sand flats (north), the canyon's lip
(south-east), the open ocean past the edge (west). Path: from the north along the talus, between the stacks, down onto
the ship's deck by the fallen mainmast's ramp (PIRATE_WRECK.md's routes), out by the anchor cable. Clearing: the hollow's
sand to the east. Hiding: the hold, the gun deck; the crevices of the talus. Danger: `white_shark` patrolling the
seal rock (real), `eel` (moray) in the hold. Reward: the hold's chest (crowbar: DESIGN.md), the outcrop's crabs and
lobsters for the fish.

**Rules**

| Layer | Substrate / where | Depth | Core / edge | Notes |
| --- | --- | --- | --- | --- |
| barnacle and mussel band (props `mussel_clump` on the stacks' sides) | stack faces | 0 to 2.5 | 1 per 0.6 m² of face | a crisp band at the waterline |
| rockweed | stack faces and the islet's foot | 0 to 1.5 | 1 per 0.5 m² | |
| sea palms (SEA_PALM) | the most west-facing stack's top shelf | 0 to 1 | 8 a stack | the surge side only |
| bull kelp (kit 4) | rock (talus, stack feet) | 3 to 14 | 8 / 2, a ring 6 to 16 m from the islet | Claude's pick: the outcrop's kelp is its ring, so the ship sits in open sand under light |
| strawberry anemone sheets, hydrocoral, red fans, sponges | stacks' and shards' side and under faces | 10 to 22 | 3.4 rules | thickest on the west (current) side |
| talus boulders (`rock_boulder`, `rock_boulder_small`, `rock_split`) | sand round the outcrop, falling off with distance | 18 to 24 | 6 at the stacks' feet / 0 at 18 m out | the ship's bow rests on the last of them (PIRATE_WRECK.md: "a rock under her forefoot") |
| plumose anemones on the wreck (white and orange) | the wreck's high points: mastheads, rails, the stern's carving, the bowsprit | - | 1 per 1.5 m of rail; clones of 3-5 | real cold-wreck look; the wreck's owner places them on its own points |
| shell hash (substrate 3) | sand within 5 m of the hull | - | (paint) | |
| red weed, sea stars, urchins | talus tops | 18 to 22 | as kelp floor, half | |

**Animals.** Surface and islet: `seal`, `sea_lion` (move `sea_lion` from "reef" to "pirate" and "docks": the reef has
no haul-out). Ring: `otter`, `rockfish`, `kelp_bass`, `surfperch`. Wreck: `rockfish` (in the hold), `eel`, `octopus`,
`lobster`, `crab`, `garibaldi` (few), `pufferfish` (tropical, few), `snapper` (keep out: tropical; liner only).
Danger: `white_shark` (add "pirate" to its zones; it already has "kelp").

**From far / blending.** Dark vertical stacks over pale sand, the ship's silhouette below them; bull kelp floats at the
surface round the islet. Blends north into the sand flats (the talus thins out), west over the shelf's edge (5.13).

**Play.** Fish: a hunting ground with a refuge (the hold) and a hunter (the white shark). Diver: the first real wreck,
the crowbar's chest. **Gear step: amplifier 30 m, hard-hat suit 25 m, crowbar.**

**Budget.** Stacks and shards exist (Outcrop site); growth on them 250 instances 30,000 triangles; bull kelp 40 plants
15,000; talus 40 rocks 25,000; total about 70,000 plus the wreck's own model.

### 5.7 Atlantis (the terrace round (-75, 74), 42 m, the canyon 90 to 100 m round it)

**Real model.** None for the city. For its life: what grows on high rock in the upper canyon at 40 to 100 m (5.5):
giant plumose anemones, sponges, gorgonians, feather stars, brittle stars on the sand, rockfish hanging in clouds over
the high points; the light dim and blue-green.

**Layers.** Over it: drifting glowing things (`comb_jelly`, `pyrosome`, `firefly_squid`). Its tops (dome, columns'
capitals, the crystal pillar, the pyramid's steps): giant Metridium and sponges, thickest on the up-canyon side.
Its faces: sponges, fans, crust. Its sand: sea pens and brittle stars, the processional way's paving half buried.
The terrace's edge: a drop on every side into the canyon's dark.

**Plan:** RUINS.md's own plan (the processional way from +Z, the gate, the temple, the fallen head, the pyramid, the
crystal pillar). This design adds only the life and the edge:

```
            canyon (90-100 m, dark)
     .  .  .  terrace edge (sea pens thin out, the drop)  .  .  .
     .   colonnade (Metridium on every capital, white crowns in a row)
     .  (temple dome: sponges on the rim)        [pyramid: fans up its stair]
     .            (HEAD) (hand)                       (P) crystal: the light
     .  [gate]  brittle-star carpet on the paving
     .    way: sea pens either side, columns' stumps
     .  .  .  the way in (from the canyon's axis, north-east)  .  .  .
```

Landmark: **the crystal pillar's light** (RUINS.md's), the one light in the basin, seen from far down the canyon. A row
of white Metridium on the colonnade's capitals is the second read (Claude's pick). Entrances: up the processional way
from the canyon's axis (north-east), over the terrace's edges. Path: the processional way. Clearings: the court before
the temple. Hiding: the temple, under the fallen hand. Danger: the edge's drop and the deep's hunters (`blue_shark`,
`white_shark` in "ruins" now: replace with deep hunters; `anglerfish`, `viperfish`, `humboldt`). Reward: the temple's
chest (lamp, armoured suit: DESIGN.md), photographs.

**Rules.** All on the ruins' surfaces by 3.4 (the ruins' owner places them on its own points, this design gives the
rules): plumose anemones, scale 2.5 to 4 (the giant deep form), 1 per capital and 1 per 2 m² of any top facing up;
sponges 1 per 4 m² of side faces; red fans across the current on edges; no kelp, no weed (no light at 42 m in this
game's dark). On the sand: sea pens 20 / 5, brittle star carpets, `sea_lily` 1 per 20 m². Nothing on the paving of the
way itself (kept clear as the path).

**Animals.** Keep: `grouper` (as a big hanging fish), `lionfish` (fantasy), `dumbo_octopus`, `sea_lily`, `brittle_star`,
`spiny_trilobite`, `ammonite`, `cameroceras`, `comb_jelly`, `pyrosome`, `firefly_squid`, `anglerfish`, `viperfish`,
`green_turtle` / `hawksbill` / `loggerhead` (fantasy at 42 m; keep few). Add: `rockfish` clouds over the tops.
Remove from "ruins": `blue_shark` (an open-ocean surface shark), `white_shark` (coastal).

**From far / blending.** A cool point of light in the dark, the white crowns of the anemones, pale stone. The terrace's
sand blends into the canyon's mud at its edge (substrate: sand on the terrace, mud off it).

**Play.** Fish: the deep's richest place, dangerous to reach. Diver: the armoured suit's goal. **Gear step: amplifier
50 m, armoured suit 50 m, the lamp.**

**Budget.** Growth 300 instances, 45,000 triangles; sea pens and stars 30,000; plus the ruins' own model.

### 5.8 The sea grass (eelgrass off the peninsula, round (-11, 78), r 15, 1 to 8 m)

**Real model.** Eelgrass (Zostera marina) grows in sheltered bays and estuaries on sand and mud in the shallow subtidal:
in Monterey, the Del Monte meadow at 6 to 9 m and Elkhorn Slough's channels. Meadows are patchy, with bare "blowouts"
inside them; densest and longest in the middle, shorter and sparser at the edge. They are nurseries: richest in species
of any of the three habitats (eelgrass, algae, bare) in the Elkhorn study; pipefish, juvenile rockfish, surfperch, kelp
crabs, sea hares, bat rays and leopard sharks feeding in and round them. Sea otters, by eating crabs, help the meadows
grow (Hughes et al. 2013).

**Layers.** Over the grass: small fish schools (surfperch, juveniles). In it (0 to 1.2 m): the blades and what clings to
them (seahorses, pipefish, sea hares, nudibranchs). Floor: sand and mud, clams, crabs, flatfish in the blowouts.

**Plan**

```
       N  canyon's lip (deep: the meadow stops at 8 m, well short of it)
       .  .  sparse edge  .  .
     .  ::::::::::::::::::::::  .
    .  ::::::  ( )  ::::::::::::  .     ( ) = blowouts (bare sand holes, 3-6 m)
    .  ::::::::::::::::  ( )  ::  .     the meadow's core: long grass, thick
    .  :::: ( ) ::::::::::::::::  .     ===  the path: a winding trail of lower,
    .  =====trail======>:::::::  .          sparser grass (bat rays use it)
     .  ::::::::::::::::::::::  .
       .  .  .  beach strip / peninsula shore (east)  .  .
```

Landmark: eelgrass meadows have no tall thing, so the landmark is the
meadow's own shape (a bright green field seen from above, the brightest green in the sea) and one **anchored skiff's
mooring** over it (shared kit 14). Entrances: from the beach (east), from the docks (to the east), over the lip from
the canyon (north). Path: the trail. Clearings: the blowouts (where flatfish and rays lie). Hiding: anywhere in the
grass for a small fish (it lies over the fish: `push_radius`). Danger: `leopard_shark` and `bat_ray` sweeping the
trail; `halibut` in the blowouts. Reward: seahorses, shrimp, clams (small food), photographs for the canvas suit.

**Rules**

| Layer | Substrate | Depth | Slope | Core / edge | Clump, spacing | Height |
| --- | --- | --- | --- | --- | --- | --- |
| eelgrass (SeaGrassBed) | sand, mud | 1.5 to 8 | < 0.3 | 400 / 80 (edge 5 m), noise cover 0.85, blowouts cut out (noise below -0.55) | patches of 6-12 within 1 m, 0.25 | 0.9-1.2 m core, 0.4-0.7 m edge; 0.5-0.7 on the trail |
| sea lettuce (SEA_LETTUCE) | sand | 1 to 8 | any | 10 / 4 | 2-4, 0.5 | 0.25-0.5 |
| razor clams, scallops | sand | 1 to 8 | - | 2 / 1 (more in blowouts) | | |

The meadow's area by these rules is about 400 to 500 m² (the circle's 700 m² less the deep part): 1,600 to 2,000 tufts.
The circle should move about 6 m south-east, nearer the shore, so the whole meadow fits its depth band (a Bay change,
the map owner's).

**Animals.** In it: `seahorse`, `sea_hare`, `nudibranch`, `oyster` (move to the slough and docks), `razor_clam`,
`horseshoe_crab` (move: section 7), `green_turtle` (fantasy, keep), `surfperch`, `smolt`. Over it: `perch` and `trout`
(fresh-water fish in a salt meadow: move to the river's upper end), `loach` (tropical fresh-water: river only),
`cuttlefish` (move to the liner). Visitors: `bat_ray`, `leopard_shark`, `halibut`, `otter`. Missing worth having:
bay pipefish, kelp crab, juvenile Dungeness crab.

**From far / blending.** A bright green carpet with dark holes, moving all together. The edge (5 m) thins and shortens
into plain sand, the beach on one side, the shelf's sand towards the canyon's lip.

**Play.** Fish: the small fish's safe meadow (hide in the grass). Diver: canvas suit. **Gear step: none.**

**Budget.** 2,000 tufts: near 300 x 100 + far 1,000 x 27 = about 57,000 triangles, 18 draws (the component's measure);
OK alone, so the grass's view must not also hold kelp (they are far apart: fine).

### 5.9 The liner's reef (the X off Point Lobos: the shelf round (-40, 130), 25 to 35 m)

**Real model.** None in the bay (section 4). Its pattern is a coral reef's and a wreck's:
- Coral reefs are zoned by light, depth and waves: the crest (0 to 2 m, waves: coralline algae, stout branching and
  encrusting corals), the slope (most varied, densest corals; plate and table forms spread to catch light deeper), and
  fewer corals below about 30 m.
- Wrecks are colonised in order: a film of microbes, then barnacles, tubeworms and hydroids within weeks (HMS Scylla:
  within a month; most of its kinds by year five), soft corals as pioneers, hard corals last because they grow slowly
  (the President Coolidge). The ship is the reef; the sand round it is not.

**Layers.** The hull's top (boat deck, funnels, upward faces: the "crest", nearest the light, about 20 to 24 m): table,
brain and staghorn corals, giant clams, anemones with clownfish. The hull's sides (the "slope"): sea fans across the
current, soft corals, sea rods, sponges, encrusting colour. The interiors (no light): sponges and orange cup corals
(kit 12), no hard corals. The sand: a rubble halo 0 to 6 m (shell, broken plates, coral rubble), then bommies thinning
with distance (patch reefs 2 to 4 m across), then plain sand down to the Carmel Canyon's edge.

**Plan**

```
                        N  (the ruins' canyon, far, dark)
          o           o                       o = bommies (patch reefs), fewer out
     o        :rubble halo:::::::::::::::::     o
          ::[==bow=====|br|===(F1)(F2)/  \ (F4)==stern==]::   <- the liner: F = funnels
     o    :::::::::::::::::::::::::::::::::     o     (F2 standing: the landmark)
        o      anemones with clownfish (on the lit deck)   o
     sand slope ................ the Carmel Canyon's edge (a drop, S and W)
                        S  Point Lobos / Carmel (the fish market, 5.12)
```

Landmark: **the second funnel**, still standing (WRECK.md), with corals on its rim and a cloud of reef fish round it;
the warm water's colour (a teal tint against the cold coast's blue-green) shows from 40 m. Entrances: from Carmel and the
Carmel Canyon's head (east), from Atlantis's canyon (north, up the slope), from the open ocean (west). Path: WRECK.md's
swim routes (the colonnade along the promenade deck, the break between the halves), and on the sand a walk round the
hull from bow to stern for the diver. Clearings: the sand between the bommies. Hiding: the wreck's interiors. Danger:
`grouper` and `barracuda` at the hull's ends, `lionfish` stings, the canyon's edge. Reward: the saloon's chest (key
ring: DESIGN.md), the clownfish's anemones, parrotfish and tangs (food for mid sizes).

**Rules** (3.4 on the wreck's surfaces; the wreck's owner places what is on the ship, this table is the rule)

| Layer | Where | Density | Size |
| --- | --- | --- | --- |
| table, brain, staghorn, pillar corals | wreck faces up (normal y > 0.6), above 2 m over the floor | 1 per 2 m² on the boat deck and funnels' rims, 1 per 5 m² on lower decks | 0.8-1.6 x |
| giant clams, clownfish anemones | lit deck faces | 4 clams, 7 anemones (as now) | |
| sea fans (purple), soft corals, sea rods | wreck side faces, across the current (west side twice the east) | 1 per 3 m² | 1-1.8 x |
| barrel sponges | side faces low on the hull, and the rubble | 1 per 10 m² | |
| cup corals and sponges (kit 12) | under and inside faces | 1 per 2 m² inside, where the swim routes are lit by the player's view | |
| rubble halo (shell hash paint + kit 13 pieces) | sand 0 to 6 m from the hull | 6 pieces / 100 m² near, 0 at 6 m | |
| bommies (`bommie_*`) | sand 8 to 30 m from the hull's middle | 2 / 100 m² at 8 m, 0.3 at 30 m | 0.9-1.5 x |
| corals on bommies (same rules, on the bommie's own faces) | | 4 to 8 a bommie | |
| tropical pieces on open sand | **none** (they move onto the hull and bommies) | | |
| red weed (RED_ALGAE) | the rubble, bommies' sides | 20 / 5 | |

**Animals.** All the reef kinds stay here (`threadfin`, `raccoon`, `copperband`, `longnose`, `bannerfish`, `emperor`,
`queen`, `french`, `parrotfish`, `cleaner`, `wrasse`, the tangs, `clownfish`, `lionfish`, `snapper`, `grouper`,
`giant_clam`, `long_spined_urchin`, `pencil_urchin`, `feather_star`, `pygmy_seahorse`, `cleaner_shrimp`,
`spanish_dancer`, `hawksbill`, `eagle_ray`, `cuttlefish`, `manta` visiting). Layers: the deck and funnels: butterflyfish,
tangs, anemonefish, parrotfish grazing the corals; mid-water over it: `snapper` shoals, `barracuda`; the hull's ends:
`grouper`, `eel`; the sand: `eagle_ray`, `mantis_shrimp`. Remove: `sea_lion` from "reef".

**From far / blending.** A dark hull with a bright fringe of colour along its top, fish clouds round the funnel, the
water a little warmer and clearer. A sharp change of life at the shelf's edge: cold coast's red weed and urchins stop at
the rubble halo, corals start (a fantasy place should have a clean edge, not a fade, so it reads as one).

**Play.** Fish: the richest small-fish place, reached late. Diver: the third chest. **Gear step: amplifier 50 m (the
shelf is 25 to 35 m: 30 m reaches only its top); suit: DESIGN.md says hard-hat (25 m) for the liner's saloon but the
shelf is 30 m deep: a decision for the user (section 9).**

**Budget.** Growth on the hull 500 instances, 60,000 triangles (corals are 1,000 to 5,000 each full: use the low meshes
past 8 m); bommies 25 x 2,000 = 50,000; rubble 10,000. About 120,000: at the target's edge, so the corals' low meshes
and the far cut (45 m) must be on here.

### 5.10 Monterey docks (round (35, 78), r 14, 4 to 6 m dredged)

**Real model.** Under Monterey's wharves the piles carry bands: barnacles at the top (above and at the low tide line),
mussels below, then plumose anemones (Metridium), strawberry anemones (Corynactis) on the shaded piles under the deck
(a 1955 study found Corynactis colonies under the Monterey wharf where no direct sunlight reached them, and Metridium
and Corynactis keeping to different piles), "piling moss" (the tubes of a polychaete worm), sea stars at the foot, a
ring of fallen shells round each pile's foot. Sea lions rest on floats and buoys; sea otters in the harbour.

**Layers.** The deck overhead (the slatted underside: done). The pile bands, from the top: splash (barnacles, grey-
white) at +0.9 to 0 m; mussel band 0 to -1.5 m (blue-black, the clumps hanging); below, anemones to the floor
(white/orange plumose on the lit outer piles, strawberry sheets red-pink on the shaded inner ones), tubeworm fuzz; the
shell ring at the foot, sea stars. The floor: harbour mud (substrate 2), litter (as now), crab pots.

**Plan** (MONTEREY.md's layout; this adds what grows)

```
   breakwater (rock: rockweed, red weed, urchins, feather boa: the kelp forest's floor rules, shallow)
     \\\\\\
      \\\\\   [wharf 1: piles, OUTER row lit / INNER rows shaded]   [wharf 2 (commercial)] + trawler
       \\\\    floats ==  == (sea lions on them)
              moored boats (hull bottoms with weed fringe)
        harbour mud: crab pots, tyres, chain, the anchor (litter as now)
```

Landmark: **the wharves' forest of piles** with the deck's light-slatted roof, and the trawler's hull from below.
Entrances: from the south kelp (round the breakwater's end), from the sea grass (west), from the beach. Path: under
wharf 1, between its shaded piles (dark, red with strawberry anemones), out under wharf 2. Clearings: the marina's open
water between floats. Hiding: among the piles (a big fish must weave). Danger: the anglers' lines (Fishers' float rigs)
and `sea_lion`s. Reward: the treasure's first chest under the wharf (DESIGN.md), crabs and shrimp at the piles' feet.

**Rules** (per pile; `_pile` gets them)

| Band | Height (m from the surface) | What (kit) | Which piles |
| --- | --- | --- | --- |
| barnacles | +0.9 to -0.2 | barnacle crust (piling sleeve, kit 5) | all |
| mussels | -0.2 to -1.5 | `mussel_clump` x 4-6 round the pile (as hanging clumps), or the sleeve | all; thicker on the outer (lit) row |
| plumose anemones | -1.5 to the floor | creature PLUMOSE, 2-4 a pile (orange 1 in 3) | outer and end piles (current, light) |
| strawberry anemone sheet | -1 to the floor | prop `strawberry_anemones` x 3-5 a pile | inner piles under the deck (shaded) |
| tubeworm fuzz | -1.5 to the floor | sleeve (kit 5) | all |
| sea stars at the foot | floor, within 1 m | `ochre_star`, `bat_star` (props), `sunflower_star` creature | 1 a pile, 1 in 2 |
| shell ring | floor, 1.2 m round | substrate 3 paint | all |
| weed fringe on floats and hulls | waterline | sea lettuce, rockweed (SeaweedBed) | floats, moored hulls |

On the floor: harbour mud (no ripples), sea lettuce patches 5 / 1, a few `crab`s, `oyster` clumps, `sea_hare`.

**Animals.** Floats: `sea_lion` (hauled out, posed as on the islet), `seal`. Water: `surfperch` (pile perch: real),
`rockfish` (juveniles), `smolt`, `kelp_bass` (not Monterey: few), anchovy swarm. Floor: `crab`, `octopus`,
`starfish`, `sunflower_star`, `nudibranch`, `sea_hare`, `purple_urchin` (on the breakwater, not the mud), `bat_ray`,
`oyster`. Remove: `prawn` (deep: canyon).

**Budget.** 50 piles x (4 mussel + 3 anemone or sheet + 1 star) = 400 instances, 40,000 triangles (low meshes past
8 m), plus the docks' own 3,100-triangle kit; 15 draws.

### 5.11 Santa Cruz docks (round (-27, -107), r 13, 4.5 to 9 m)

**Real model.** The Santa Cruz Wharf (a long wooden pier on the open coast over sand) and the small craft harbour
beside it. California sea lions rest on the wharf's horizontal cross-beams under the deck: the place's signature.
Open-coast piles: goose barnacles on the outermost, mussels, Metridium; sand under the wharf, not mud.

**Layers and rules** as 5.10, with: the wharf's floor sand (not mud), goose barnacles (kit 5 variant) on the outer
piles; the harbour's floats and floor as Monterey's (mud).

**Plan**

```
   N  shore #### Santa Cruz ####   small craft harbour (floats, mud, boats)
        ||  wharf: one long row of bents running south out to sea  ||
        ||  SEA LIONS ON THE CROSS-BEAMS under the deck (landmark)   ||
        ||  piles: barnacles / mussels / Metridium; sand below        ||
        S -> the sand flats (5.4), the eel ridge to the south-west
```

Landmark: **the sea lions on the cross-beams** (posed, as the islet's are, on the wharf's stringers 0.3 to 0.8 m over
the water: visible from below as dark bodies against the light). Path: along under the wharf, out to the end, off to the
sand flats. Danger: anglers' lines; sea lions in the water. Reward: crabs and the start of the sand flats' food.

**Animals.** `sea_lion` (hauled out on the beams: 4 to 6, Claude's pick), `seal`, `surfperch`, `halibut` on the sand,
`crab`, `starfish`, anchovy swarm.

**Budget.** As Monterey's, fewer piles: 25,000 triangles, 12 draws.

### 5.12 Carmel's fish market (the south; new, the user's wish)

**Real model.** Carmel has no working fish wharf. Close by: the small pier at **Stillwater Cove** (Pebble Beach) and
the historic boat landing at **Whalers Cove, Point Lobos** (a whaling station and an abalone cannery in the past). Carmel
Bay's floor: granite and conglomerate reefs with giant and bull kelp along Point Lobos and Stillwater Cove, white sand
off Carmel Beach, and the Carmel Canyon's head close to the beach (at Monastery Beach).

**What the map needs first (the map owner's call).** As the floor is now, Carmel is a 0 to 3 m flat behind the canyon's
head (section 1). For a market pier with a sale net hanging off it, Carmel Bay must be deepened: Claude's suggestion, a
cove dredged like the harbours (`HARBOURS`) about 7 m deep round chart (35, 176) (world (28, 141)), radius 12 chart m,
opening west onto the Carmel Canyon's head. The fish market stands on the shore above it (the boat's world, not this
design's).

**Layers and plan**

```
        N  the liner's shelf (5.9) to the north-west
    W  Carmel Canyon's head (deep, the drop)  |  cove (7 m): the market's short pier
       granite reef on the south side (Point Lobos): giant kelp, bull kelp at its outer edge
       white sand off Carmel Beach to the east (sand dollars at its edge)
        S  Point Lobos ####
```

Landmark: **the short pier and the market's lit windows over the water**, and the kelp on the Point Lobos side.
Path: from the liner's shelf, over the canyon's head, into the cove. Rules: the south side's reef is a small kelp
biome (5.2's table, 6 to 12 m, 40 plants), the pier is 5.10's piles (three bents), the floor sand (Carmel's beach is
white: tint the sand paler here, Claude's pick). Animals: as the kelp and the docks, and `otter`.

**Play.** The southern place to sell a catch (DESIGN.md's net), next to the liner and the canyon's head. **Gear step:
the boat's anchorage step to reach the south.**

**Budget.** Small: 40 kelp plants, 6 piles, 40,000 triangles.

### 5.13 The open ocean (west of the shelf's edge at x about -112; and over the canyon's basin)

**Real model.** Open water over the shelf break: nothing to stand on; things drift. In Monterey Bay: drifting kelp rafts
(paddies) that gather juvenile fish (rockfish, yellowtail and others take refuge in the tangle), by-the-wind sailors
(Velella), salps and pyrosomes, sea nettles and moon jellies, ocean sunfish (Mola), the bait balls that whales, dolphins,
sea lions and birds hunt. The shelf's edge is the one wall.

**Layers.** Surface: drift kelp paddies, sargassum (few, section 4), flying fish, birds later. Epipelagic (0 to 30 m):
bait balls, tunas, sailfish, dolphins, whales. Below: the dark, the canyon's mouth.

**Plan**

```
    shelf's edge (cliffs: the existing CLIFF row, now with rock-band life: 5.5's rules)
  |  ~~~ paddy ~~~           ~~~ paddy ~~~        the paddies drift slowly with the
  |        (bait ball: sardines driven up by tunas/dolphins)     current, 3-5 of them
  |   ~~~ paddy ~~~                     whale
  |              ...the dark...         ~~~ paddy ~~~
  world's west end (x = -157)
```

Landmarks: **the shelf's edge wall** (a cliff 16 m high running north-south: the open ocean's one fixed thing; the
cliffs get 5.5's rock-band life) and **the drift kelp paddies** (kit 10: 3 to 5, each 4 to 8 m across, with fish under
them), and the bait balls when they happen. Entrances: over the edge from anywhere on the shelf. Path: along the edge
wall. Clearings: everywhere. Hiding: under a paddy (small fish). Danger: everything big. Reward: the paddies (juvenile
fish food), the bait balls.

**Rules.** Paddies: 3 to 5, drifting with the current at 0.05 m/s, wrapping round inside the open zone; each paddy is a
small Life school's home (`habit: "home"` for juvenile rockfish and `mahi` under it: real, mahi and yellowtail gather
under drift kelp). Sargassum: down from 70 to 20 mats, kept round the paddies (Claude's pick). Cliffs: plumose
anemones and sponges on their faces by 3.4.

**Animals.** As now (all the pelagic kinds and giants). Change: the giants (`whale_shark`, the whales, `manta`,
`leviathan`, `mosasaur`, `plesiosaur`, `sea_serpent`) keep to water deeper than 30 m and at least 10 m from the shelf's
lip; the "half the time over the canyon's basin" placement must check depth under them (the grass picture's whale
shark was over 8 m of water). Missing worth having: ocean sunfish (Mola mola), by-the-wind sailors.

**From far / blending.** Deep blue fading to black; the paddies as dark shapes against the bright surface. The shelf's
edge is a hard line.

**Play.** Fish: the big fish's hunting ground. Diver: none (no floor). **Gear step: none for the surface waters;
amplifier for depth.**

**Budget.** Paddies 5 x 3,000 = 15,000; cliffs (light) 10 x 1,200 = 12,000; their growth 10,000. The open's cost is its
animals, not its scenery.

### 5.14 The mangrove slough (Elkhorn Slough, the channel from (86, -18) east, 4 m)

**Real model** (the parts that are real): Elkhorn Slough is a tidal estuary: about 290 acres of subtidal channels, 1,600
of mudflats, 800 of salt marsh; pickleweed marsh with bare mud; the channels and creeks are fish nurseries; sea otters
rest in the marsh's wider creeks; eelgrass in the channel; Olympia oysters; bat rays, leopard sharks and halibut use
it. The mangroves are the user's (section 4); how mangroves really stand: red mangroves on the water's edge on prop
roots (their roots a nursery: juvenile fish shelter in them and forage out into the eelgrass), black mangroves behind on
the mud, their breathing roots (pneumatophores) poking up out of it.

**Layers.** Over the water: the mangroves' canopy (dark green, closing over the narrow upper channel). Waterline and
roots: prop roots in arches down into the mud, oysters and barnacles on them at the waterline. Channel: eelgrass on the
shallow edges, mud in the middle; fish among the roots. Banks behind: mud with pneumatophores, pickleweed at the top of
the bank.

**Plan** (the mouth at the west, the canyon's head beside it)

```
  canyon head  |  MOUTH (marine: bat rays, leopard sharks, seals on the mud bank, otters)
   ~~~~~~~~~~~~|~~~ beach strip
       mud bank (seals hauled out)  \  eelgrass edges  /  oyster clumps
          rRrRrRr  red mangroves (prop roots in the water) rRrRrRr
   channel  ===== mid (brackish: the mangroves, the ambushers) =====>  bend
          rRrRrRr  bbbb pneumatophore mud bbbb                         rRrR
                                       ... UPPER END (fresh: Carneros Creek pool,
                                           arowana, koi, guppies, bettas, catfish)
```

Landmark: **the mangroves' tunnel** where the canopy closes over the channel (dark, green-lit), and at the top **the
fresh-water pool** (clear, golden water, lily pads at the surface: Claude's pick of a look, needs kit), where the aquarium
fish are. Entrances: the mouth only (from the canyon's head and the beach). Path: the channel itself (13 m wide, 4 m
deep). Clearings: the mouth's mud bank, the pool. Hiding: the prop roots (a small fish among them cannot be followed by
a big one: the roots stop swimmers already). Danger: `gar` and `pike` waiting in the roots, `piranha` in the upper end
(fantasy), `leopard_shark` at the mouth. Reward: the aquarium fish (tiny food), the oysters' pearls (the `oyster` has
`pearl`).

**Rules**

| Layer | Where | Rule | Notes |
| --- | --- | --- | --- |
| red mangroves (MangroveStand trees a-d) | the channel's banks | shore distance 0 to 3 m, water depth 0.5 to 3 m, **not within 10 m of the canyon or the beach strip's mouth** | one every 3.5-5.5 m each side (as now) |
| mangrove root clusters (roots_a, roots_b) | between trees, nearer the water | 1 between each pair, on the outer bend's side | thickens the bank |
| pneumatophore field (kit 11) | the mud behind the trees, 3 to 10 m from the water | 300 spikes per 100 m² (one instance draws a patch of 50) | |
| eelgrass (SeaGrassBed) | the channel's shallow edges | depth 1 to 2.5, 400 / 100 | the real slough's eelgrass |
| oyster clumps (`oyster` and kit: an oyster-clump prop would be better than creatures) | roots' feet, the channel's edge | 5 a 10 m of bank | Olympia oysters: real |
| sea lettuce | mud | 10 / 3 | |
| mud (substrate 2) | the whole slough | - | |
| the pool (upper end) | the last bend | a widening (Bay: SLOUGH's end radius 10) | fresh-water tint |

**Animals by stretch** (a salinity gradient along the channel: Claude's pick, and the real slough's own gradient).
- Mouth (marine): `bat_ray`, `leopard_shark` (Elkhorn is a real nursery for both), `halibut`, `seal` (hauled out on the
  mud bank: posed like the islet's), `otter` (resting at the surface), `smolt`, `surfperch`, `oyster`, `horseshoe_crab`
  (fantasy, moved here).
- Middle (brackish, the mangroves): `gar`, `pike` (fantasy: fresh-water fish), `perch`, `trout` (moved from the grass),
  `catfish`, `lamprey`, `walleye`, `carp`, `arowana` (at the surface under the canopy).
- Upper end (the pool, fresh): `koi`, `goldfish`, `guppy`, `platy`, `betta`, `neon_tetra`, `zebra_danio`,
  `corydoras`*, `loach` (moved from the grass), `piranha`.

**From far / blending.** From the canyon's head: a dark green mouth with light at its end. The mouth blends into the
beach strip's sand and the canyon head's mud.

**Play.** Fish: the fresh-water line's home; a gauntlet of ambushers in the roots. Diver: canvas suit (4 m), walking
the mud among the roots. **Gear step: none.**

**Budget.** Mangroves are dear (the component's own measure: 296,000 triangles among the roots with `near` 22 m):
`near` must come down to 10 m here, about 30 trees in view: 60,000 triangles, 20 draws; pneumatophores 40 patches x
800 = 32,000.

---

## 6. The placer's data (replacing `scenery.gd`'s hand loops)

What goes from `scripts/scenery.gd` into the placer: `_place_rocks`, `_place_reef`, `_plant_kelp`, `_plant_grass`,
`_plant_seaweed`, `_plant_live_anemones`, `_plant_anemones`, `_plant_mangroves`, `_plant_eels`, and the constants KELPS,
TUFTS, SLOUGH_TUFTS, EEL_COUNT. What stays: the docks (`_build_docks`, `_wharf`, `_pile` + the pile bands of 5.10),
the outcrop (`_build_outcrop` + 5.6's growth), `_place_cliffs` (+ 5.5's growth), `_place_breakwater`, the landmarks,
the eels' eating in `_process`.

One table per biome, in `scripts/biomes.gd` (or a `biomes/*.tres` each; a GDScript const is simpler to diff):

```gdscript
const KELP_SOUTH := {
	"area": {"zone": "kelp", "patch": 0},           # or {"line": "SLOUGH", "half": 9.0}
	"depth": [5.0, 16.5],                            # the biome's own band; outside it nothing of it grows
	"reef": {"freq": 0.05, "seed": 21, "cover": 0.55, "stretch": Vector2(1.0, 2.5), "turn": 0.4},  # rock mask
	"paths": [{"points": [Vector2(70, 40), Vector2(48, 48), Vector2(26, 50)], "half": 3.0}],
	"clearings": [{"at": Vector2(55, 30), "r": 6.0, "substrate": "crust", "name": "barren"}],
	"landmark": {"piece": "rock_arch", "at": Vector2(43, 48), "turn": 0.6, "big": 1.2},
	"edge": 8.0,                                      # metres over which core density falls to edge density
	"layers": [
		{"what": "props", "pieces": ["rock_boulder", "rock_split", "rock_ledge", "rock_stack"], "on": ["rock"],
		 "depth": [5, 16], "density": [3.0, 1.0], "spacing": 3.0, "clump": [1, 3, 3.0], "big": [0.8, 1.5], "lift": -0.25},
		{"what": "kelp", "on": ["rock"], "depth": [6, 16], "slope_max": 0.7, "density": [12.0, 2.5],
		 "noise": {"freq": 0.09, "seed": 3, "cover": 0.75}, "spacing": 1.6, "clump": [2, 4, 1.5],
		 "height": "reach", "reach": [1.05, 1.4], "edge_reach": [0.6, 0.95]},
		{"what": "seaweed", "kind": "SEA_PALM", "as": "understory", "on": ["rock"], "depth": [4, 15],
		 "density": [40.0, 10.0], "noise": {"freq": 0.15, "seed": 4, "cover": 0.6}, "spacing": 0.6,
		 "clump": [5, 12, 2.0], "size": [0.8, 1.5]},
		{"what": "props", "pieces": ["urchin_purple"], "on": ["rock", "crust"], "depth": [5, 16],
		 "density": [15.0, 5.0], "near": ["rock_prop", 1.5], "in_clearing": {"barren": 300.0}, "clump": [10, 30, 2.0]},
		{"what": "growth", "on_faces": "side", "pieces": ["strawberry_anemones", "hydrocoral", "sea_fan_red"],
		 "depth": [6, 16], "per_m2": 0.3},
		# ...
	],
	"budget": {"triangles": 95000, "draws": 50},     # checked by a test: the placer prints what it made
}
```

Rules the placer implements once: `on` (substrate list), `depth`, `slope_max` / `slope_min`, `density` with `edge`,
`noise`, `spacing`, `clump`, `near` / `away`, `in_clearing`, `on_faces` (3.4), `height` / `reach` / `edge_reach`,
`size`, `lift`, `keep_out` (implicit: paths, clearings, lanes, the start's column, landmarks' footprints).
A test (`tests/biomes_check.gd`, headless) prints each biome's counts and estimated triangles, and fails if any plant
stands on the wrong substrate or depth, or a budget is exceeded.

## 7. Species to move (who is in the wrong place now)

| Kind | Now | Should be | Why |
| --- | --- | --- | --- |
| giants (`whale_shark`, whales, `manta`, `leviathan`, `mosasaur`, `plesiosaur`, `sea_serpent`) | "open", half the time over the canyon's basin, which reaches the shallows | the same zones, but only where the water is over 30 m deep and 10 m from any lip | seen over the eelgrass in the picture |
| `loach` (clown loach) | river, grass | river (upper end) | tropical fresh-water fish |
| `trout`, `perch` | river, grass | river | fresh-water fish in a salt meadow |
| `cuttlefish` | reef, grass | reef | no cuttlefish in the Americas; the warm pocket only |
| `horseshoe_crab` | sand, grass, beach | river (the mouth's mud) | estuarine, and not Pacific: the fantasy slough |
| `prawn` (spot prawn) | reef, grass, docks | trench (the canyon's walls), ruins | lives on deep rock, 50 m and more |
| `sea_lion` | kelp, docks, reef | kelp, docks, pirate (hauled out at the islet and the Santa Cruz beams) | the reef has nowhere to haul out |
| `white_shark` | open, kelp, ruins | open, kelp (west edge), pirate | coastal, hunts at seal rocks; not at 42 m in a canyon |
| `blue_shark` | open, ruins | open | surface open-ocean shark |
| `rockfish` | reef, kelp, docks, pirate | + trench (walls), ruins; band 0.1-0.7 in kelp | blue rockfish school in mid-water; rockfish on canyon walls |
| `octopus` | reef, ruins, pirate, docks | + kelp | the giant Pacific octopus is a kelp reef animal |
| `oyster` | river, grass, docks | river, docks | Olympia oysters on hard bits in the slough and harbour |
| `humboldt` | open | open, trench | in Monterey's canyon since about 2000 |
| `eagle_ray` | reef, sand, beach | reef | spotted eagle rays are tropical |
| `devil_ray` | open, sand | open | pelagic, tropical |
| `purple_urchin` | kelp, docks | kelp (barren and cracks), docks (breakwater only) | placed by the floor rules |
| `halibut` | sand, beach | + river (the mouth) | Elkhorn is a halibut nursery |

## 8. What is missing from the kit (priority order, one-line briefs)

Each to be built in Blender (the user's rule), looked at from four sides, checked for inside-out faces, with a full and
a light mesh, its base at y = 0, tinted by instance colour like `sea_floor_props` (GL Compatibility: `use_colors` on).

1. **Substrate paint** (not a model): the floor shader blend of rock, mud, shell hash and coralline crust from a 2 m
   substrate texture (3.1). Everything else depends on it.
2. **Reef slabs**: 4 low, wide rock tiles (3 to 5 m across, 0.3 to 1.2 m relief, cracks and steps on top, about 300
   triangles full, 60 light) that pave a rock reef cheaply; the "rock" shader.
3. **Understory kelp** (Pterygophora / Laminaria setchellii): a stiff woody stipe 0.6 to 1.2 m with a crown of 10 to 16
   strap blades drooping like a palm; 3 variants; about 120 / 24 triangles; swaying in the seaweed shader.
4. **Bull kelp** (Nereocystis): one thin stipe rising to a single round float 10 to 15 cm across with a mop of 20 to 30
   long strap blades streaming down-current from it; a KelpForest variant (the stipe in 1 m pieces so it bends as the
   giant kelp does).
5. **Piling growth sleeves** for the docks' piles (kit for `_pile`): a barnacle crust band, a mussel band with hanging
   clumps, a tubeworm-fuzz sleeve with Metridium, a strawberry-anemone sheet; each a cylinder band 0.42 m in radius,
   1 to 3 m tall, 200 to 500 triangles; plus a goose-barnacle variant for exposed outer piles.
6. **Surfgrass** (Phyllospadix): bright emerald-green very long thin ribbon blades (1 m) in dense tufts on rock in the
   surge; a SeaGrassBed variant with its own colour and thinner, longer blades.
7. **Sea pens** (Ptilosarcus): an orange feather 0.25 to 0.45 m on a fleshy stalk, standing in the sand; a deep, taller
   white variant (to 1 m) and a sea whip (a bare whip 1 m); retracts into the sand (a `retract` like the anemone's);
   about 60 / 12 triangles.
8. **Sand dollar bed**: grey-purple discs standing half buried on edge, leaning down-current, in patches of 50 as one
   instance (about 400 triangles a patch).
9. **Whale fall**: a gray whale's skeleton 12 m long (skull, jaw, spine in a curve, ribs fallen outwards, flippers'
   bones) on the mud, white mats and orange bacterial fuzz on the bones (emissive a little), about 6,000 triangles,
   with spheres for swimmers; scavengers are animals.
10. **Drift kelp paddy**: a floating tangle of giant kelp fronds and floats 4 to 8 m across at the surface, a few fronds
    hanging 2 to 3 m down; drifts; about 3,000 triangles.
11. **Pneumatophore field**: a patch of 50 pencil-thin breathing roots 10 to 30 cm out of mud, and a mud-bank edge
    piece with pickleweed on top (for the slough's banks).
12. **Cup corals and encrusting sponges** for wreck interiors and under-faces: orange cup coral clusters (Tubastraea-
    like), yellow and red encrusting sponge patches; flat, 100 to 400 triangles.
13. **Rubble pieces** for the liner's halo: hull plates, a porthole, a davit, coral rubble (the wreck's owner may have
    them; else a set of six).
14. **Mooring block, chain and buoy**: a concrete block, a chain rising to a buoy at the surface (the chain as a rope
    or a run of links); also for the docks' moorings and the sea grass's skiff mooring.
15. **Deep glass / cloud sponge** (1 m, pale, lobed) and a **basket star** for the canyon's walls and Atlantis.
16. **Fresh-water pool kit**: lily pads at the surface and a sunken log, for the slough's upper end.

Animals that would make the places truer (creatures, not kit; for the creature builders): lingcod, cabezon, sheephead,
señorita, kelp crab, abalone (kelp); bay pipefish (grass); sanddab, Dungeness crab, sand star, angel shark (sand);
ratfish, sablefish, hagfish, sixgill shark (canyon); ocean sunfish (Mola mola), by-the-wind sailors (open).

## 9. What the user must decide

1. **The liner's depth against the suits**: the shelf is 25 to 35 m but DESIGN.md has the liner's chest on the hard-hat
   suit (25 m). Raise the wreck's shelf to about 22 to 25 m (a Bay change), or move that chest to the armoured suit.
2. **Carmel's market** needs Carmel Bay deepened (a cove about 7 m: section 5.12), and Carmel has no real fish wharf:
   model it on Stillwater Cove's small pier or on Whalers Cove at Point Lobos (an old whaling and abalone landing)?
3. **The garden eels**: stay off Santa Cruz on their ridge (as asked), or also a small colony on the liner's sand
   (where garden eels really live, next to a reef)?
4. **The mangroves**: as designed, mangroves with the real Elkhorn around them; or pickleweed marsh in the lower slough
   and mangroves only up the slough?
5. **Sargassum** (Atlantic): keep a few mats, or replace them with the Pacific's drift kelp paddies only?
6. Whether a **warm-water tint** for the liner's pocket is wanted (it makes the coral read as a separate place).

## 10. Phase two: order of building

1. The substrate grid and floor paint (Bay, Sea's sand shader copy). Pictures of every place.
2. The placer with the kelp south table only, its check and its budget numbers; then each other biome's table.
3. Growth on structure (piles first, then the outcrop, the canyon's cliffs; the wrecks' and ruins' owners use the same
   rules on their own points).
4. The species moves (section 7: a table edit in `species.gd` and the giants' depth check in Life/Sea.place).
5. Kit pieces in the order of section 8, each built, checked from four sides, then put into its table.

Nothing of this is done. Pictures used for section 1 are not kept in the repo.

---

## Research and sources

### Kelp forests (Monterey Bay and the California coast)

- Monterey Bay National Marine Sanctuary (SIMoN), "Kelp Forests": giant kelp (Macrocystis pyrifera) and bull kelp
  (Nereocystis luetkeana) dominate; bull kelp on exposed shores, giant kelp abundant except at the most exposed sites;
  kelp from just past the breakers to under 30 m; understory of Pterygophora californica and Laminaria; canopy gives
  vertical habitat; kelp forests are nurseries for nearshore rockfish (blue rockfish most abundant juveniles 2000-04);
  drift kelp exports carbon and nitrogen to deeper habitats; sea otters forage there.
  <https://sanctuarysimon.org/monterey-bay-nms/kelp-forest/>
- SIMoN species database, giant kelp: depth 3 to 30 m (to 53 m), conical holdfast of haptera up to 1 m tall in old
  plants, many stipes from one holdfast, holdfasts shelter small invertebrates; large stands in sheltered Monterey and
  Carmel bays; wave exposure pushes the upper limit deeper.
  <https://sanctuarysimon.org/dbtools/species-database/species-info-ajax.php?sID=40>
- Pearse and Hines 1979 (northern Monterey Bay): forest at about 3 to 7 m, understory Laminaria dentigera and
  Pterygophora, a band of Cystoseira osmundacea at the seaward edge, beyond it mostly barren with encrusting coralline.
  <https://biomar.fciencias.unam.mx/Sobretiros/Informacion%20algas/Algas/nueva%20informacion/J.S.%20PEARSE%20AND%20A.H.%20HINES%201979.pdf>
- McLean, Carmel-area subtidal survey: Pterygophora as a forest on bottom rocks, Laminaria setchellii dense on vertical
  walls. <https://archive.org/download/biostor-8347/biostor-8347.pdf>
- Bodkin (Fishery Bulletin 1986), kelp forest fish of central California.
  <https://fisherybulletin.nmfs.noaa.gov/sites/default/files/pdf-content/1986/844/bodkin.pdf>
- SBC LTER protocol, density of giant kelp (method: plants over 1 m counted in 20 x 1 m swaths).
  <https://sbclter.msi.ucsb.edu/external/Reef/Protocols/Kelp_Forest_Community_Dynamics/KFCS_Protocol_Density_of_giant_kelp.pdf>
- Reed et al. 2008, Ecology (standing crop tracks frond density more than plant density).
  <https://sbclter.msi.ucsb.edu/external/eemb595p_wtr2011/2011-01-19/Reed_et_al_2008_Ecology.pdf>
- Buschmann et al. 2004 (Macrocystis densities, Chile).
  <https://biomar.fciencias.unam.mx/Sobretiros/2019/Informacion%20algas/Algas/Feofitas/Buschmann%20et.al.%202004.pdf>
- Bull kelp: one pneumatocyst on a hollow stipe, annual, dominant canopy kelp from Monterey northwards (Lenfest fact
  sheet; Springer et al.).
  <https://lenfestocean.org/en/news-and-publications/fact-sheet/ecology-and-management-of-the-bull-kelp-nereocystis-luetkeana?amp=1>
  <https://www.lenfestocean.org/~/media/legacy/lenfest/pdfs/springer_underlying_report_0.pdf>
- Urchin barrens and coralline crust: coralline cover higher, less diverse in barrens (PMC6660763); Pacific Grove site
  deforested to crustose coralline (SIMoN 2017); the peninsula as a patchwork of barrens and forest; otters feed in the
  forest patches, not the barrens; >80% canopy loss Monterey Harbor to Carmel Highlands (WHOI).
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC6660763>
  <https://sanctuarysimon.org/2017/07/urchins-continue-to-dominate-parts-of-monterey-bay/>
  <https://www.eeb.ucsc.edu/academics/undergrad/undergraduate-research/gullikson-abstract1.pdf>
  <https://news.ucsc.edu/2021/03/kelp-forests-monterey/>
  <https://www.whoi.edu/press-room/news-release/new-study-uncovers-unprecedented-declines-in-iconic-kelp-forests-along-monterey-peninsula>
  <https://www.sciencenews.org/article/how-kelp-forests-california-urchin-takeover-sea-otter>
- Drift kelp paddies shelter juvenile fish (yellowtail, rockfish); juvenile rockfish at the surface with drift kelp
  (DAN Alert Diver; CalCOFI Lenarz et al. 1991).
  <https://dan.org/alert-diver/article/kelp-paddies/>
  <https://calcofi.org/downloads/publications/calcofireports/v32/Vol_32_Lenarz_etal.pdf>

### Eelgrass, the slough, sand

- Elkhorn Slough eelgrass: species richness highest in Zostera of eelgrass, algae and bare habitat; nursery (CSUMB
  thesis). <https://digitalcommons.csumb.edu/caps_thes/71>
- Sea otters promote eelgrass expansion at Elkhorn Slough (Hughes et al. 2013, PNAS).
  <https://www.mmc.gov/wp-content/uploads/Hughes_etal_2013_PNAS_otters_eelgrass.pdf>
- Elkhorn Slough habitats (293 acres channels, 1,605 mudflat, 796 salt marsh; otters rest in wider marsh creeks):
  State of the Estuary 2023. <https://elkhornslough.org/files/State_of_Estuary_2023.pdf>
  and the reserve's older page:
  <https://webarchive.library.unt.edu/eot2008/20090825004257/http://nerrs.noaa.gov/ElkhornSlough/welcome.html>
- Monterey Bay shallow soft bottoms: sand dollars (Dendraster) in narrow subtidal bands at the shoreward edge, moving
  with the seasons. <https://montereybay.noaa.gov/sitechar/shallow2.html>
- Tube anemones (Pachycerianthus) on sand and mud, low intertidal to at least 20 m; sea pens rebury themselves.
  <https://cadivingnews.com/not-your-average-anemones-examining-unusual-species>
  <https://cadivingnews.com/exploring-a-not-so-barren-landscape-the-sand-biome>
- Sand dollars exclude sea pansies at 6 to 9 m (Oecologia). <https://link.springer.com/article/10.1007/BF00367957>
- Cortez garden eel (Heteroconger digueti): Gulf of California to Jalisco, 2 to 34 m.
  <https://www.fws.gov/species/cortez-garden-eel-heteroconger-digueti> <https://fishbase.net.br/summary/13601>

### Piles and wharves, rocky shores

- Anemones on the Monterey wharf's piles (Anthopleura, Metridium, Corynactis; Corynactis on unlit piles; the two
  species on different piles). <https://miller-library.github.io/taxa-ocr-output/pv780dk7934.html>
- Corynactis californica on wharf pilings and floats, under ledges, in currents.
  <https://inverts.wallawalla.edu/Cnidaria/Class-Anthozoa/Subclass_Zoantharia/Order_Corallimorpharia/Corynactis_californica.html>
- "Piling moss" is polychaete tubes (CCSF piling lab). <https://fog.ccsf.edu/~chom/ocanpdfs/pilinglab.pdf>
- Rocky shores, zonation (MBNMS). <https://sanctuarysimon.org/monterey-bay-nms/rocky-shores/>
  <https://montereybay.noaa.gov/sitechar/rock3.html>
- Sea lions on the Santa Cruz Wharf's beams. <https://ucscsciencenotes.com/?p=2833>
  <https://en.wikipedia.com/wiki/Santa_Cruz_Wharf>

### Canyon, deep

- MBARI, Monterey Canyon: walls to about 1,700 m, sponges, deep corals, tunicates and anemones on exposed bedrock;
  whale fall at 2,891 m (2002), about 20,000 kg of food. <https://www.mbari.org/?p=98460> <https://www.mbari.org/?p=89017>
  <https://www.mbari.org/wp-content/uploads/2016/02/MontereyCanyonPoster2012.pdf>
- SIMoN, submarine canyons and deep sea (canyon head at Moss Landing, walls shoaling; clams and worms in hard mud;
  deep species coming up into the head). <https://sanctuarysimon.org/monterey-bay-nms/submarine-canyons/>
  <https://sanctuarysimon.org/monterey-bay-nms/deep-sea/>
- USGS seafloor character (walls mostly mud; steep rough walls rock).
  <https://pubs.usgs.gov/of/2016/1072/ofr20161072_sheet7.pdf>
- Soquel Canyon (Purisima sandstone, mudstone, shell hash; rockfish, deep corals and sponges).
  <https://www.californiampas.org/v1/pubs/mpa/trainthetrainers/CentralCoastMPAFactSheets/3_soquel_fin.pdf>
- NOAA 2022 deep benthic habitats of Monterey Bay.
  <https://sanctuaries.noaa.gov/media/docs/2022-monterey-bay-exploration-characterization-and-monitoring-of-deep-sea-benthic-habitats.pdf>

### Coral reefs, wrecks, mangroves

- Reef zonation (crest coralline and stout branching, slope densest and most varied, plates to catch light, fewer
  corals below about 30 m): Living Oceans Foundation; MarineSpecies traits wiki.
  <https://www.livingoceansfoundation.org/wp-content/uploads/2015/04/U11-Reef-Zonation-Background.pdf>
  <https://marinespecies.org/traits/wiki/Coral_reefs>
- Wreck colonisation: biofilm first (NOAA Ocean Explorer, Healthy Seas); HMS Scylla barnacles, tubeworms and hydroids
  within a month, most species by year five; President Coolidge, soft corals pioneers, hard corals last.
  <https://oceanexplorer.noaa.gov/wp-content/uploads/2024/08/maritime-heritage-ecology-fact-sheet.pdf>
  <https://www.healthyseas.org/blog/biofilm-shipwrecks-reef-formation/>
  <https://hawaiitribune-herald.com/?p=313840>
- Mangroves: red mangrove at the water's edge on prop roots, black mangrove landward with pneumatophores, juvenile reef
  fish in prop roots foraging into seagrass; zonation not universal (Florida FWC; NOAA MARES).
  <https://ocean.floridamarine.org/Boating_Guides/Tampa_Bay/products/brochures/mangroves.pdf>
  <https://www.aoml.noaa.gov/ocd/ocdweb/docs/MARES/MARES_SEFC_ICEM__20131001_Appendix_Mangroves.pdf>
- Northern limit of mangroves on Baja's Pacific coast about 26 45 N (CIBNOR).
  <https://dspace.cibnor.mx:8443/handle/123456789/1719>

### Games and placement

- ABZÛ (Matt Nava, GDC 2017 "Creating the Art of ABZÛ"; interviews): mood carried by lighting, "atmospheric density"
  and colour; fog pushed in and out to move the player's feeling; colour where you do not expect it (a gold kelp
  forest); the fish as vertex-shader animation (SCHOOLING.md). <https://gdcvault.com/play/1024409/Creating-the-Art-of-ABZ>
  <https://80.lv/articles/interview-with-the-creative-director-of-abzu/>
  <https://www.unrealengine.com/en-US/developer-interviews/get-to-know-the-ocean-in-journey-like-diving-adventure-abzu>
- Subnautica: depth as the level structure; wrecks set mid-biome as landmarks because players get lost; no map, so
  terrain shapes are the navigation; unclear boundaries are a known weakness (Robert Yang's critique; Charlie
  Cleveland's GDC talk). <https://www.blog.radiator.debacle.us/2018/02/mapping-sea-floors-of-subnautica.html>
  <https://gdcvault.com/play/1026273/contactUs>
- Breath of the Wild's field design (CEDEC 2017, Fujibayashi and Yonezu): triangular shapes of several sizes that hide
  and reveal, landmarks that draw the player off the path. <https://gist.github.com/idbrii/e39fe96279aa1670319bfa521d907399>
  <https://80.lv/articles/the-design-secrets-of-breath-of-the-wild/>
- Dave the Diver: the Blue Hole by depth bands (0-50, 50-130, 130-250 m), special areas (caves, vents, glacier) at set
  depths, fish fixed to depth ranges. <https://labs.invenglobal.com/articles/21659/the-depth-of-dave-the-diver>
- Rule-based foliage placement: density with elevation, slope and convexity driving placement (Serious Sam 4, GDC
  2019); masks to exclude; stacking filters (slope, difference) in UE5's PCG; per-biome rule sets with density curves,
  slope constraints, spacing and exclusion masks.
  <https://gpuopen.com/gdc-presentations/2019/gdc-2019-agtd2-4-million-acres-serious-sam-4.pdf>
  <https://docs.unrealengine.com/4.27/en-US/BuildingWorlds/OpenWorldTools/Overview>
  <https://uhiyama-lab.com/en/notes/ue/pcg-basics/>
  <https://www.strayspark.studio/blog/how-we-populated-16km-open-world>

Not found (said plainly): a sourced figure for giant kelp plants per square metre at Monterey (the numbers used are a
reading of the surveys' methods and of the budget, Claude's); Endless Ocean's environment design; ABZÛ's own numbers for
fog or plant density.
