# The sea as Monterey Bay (decision record, 2026-11-18)

## What the user asked

With a picture of a carved wooden chart of Monterey Bay (north up; Santa Cruz at the top, the Monterey Peninsula and
Carmel at the bottom right, Moss Landing and Elkhorn Slough half way down the east shore where the canyon comes in, a
red X on the water off Carmel / Point Lobos):

- "the map should be based on monterey bay, with the reef wreck at the x"
- "another location should be the docks / marina"
- "another location should be atlanits ruins", "and another location should be pirate ship wreck"
- Then the user drew the layout over the chart themselves: "heres how the map should be laid out- find a spot for
  atlanits", "in the lower spot of the trench", and "and theres should be more docks by santa cruise / marina at the
  dock".
- "also- the margrove river part goes in the center part where that river meets the bay"
- "the map doesnt need to be super huge either, nicely curated and big enough areas to recreate the intetion of hte
  map"
- "there shoule be an outcropping of rocks near the pirate ship, pillars and shards and an island that seals rest on"
- Earlier (2026-11-17), the places themselves: "a kelp forest and rocky area, a open ocean shelf, and then a sea grass
  bed area, ... a smaller reef area, and a sandy open area with garden eels", "a mangrove / river entrance area for
  fresh water fish", "a trench area".
- The docks are built to the concept art made at the user's request (`tools/art_src/concept_docks.jpg`: rows of dark,
  mussel-crusted pilings, the wharf's slatted underside overhead, hulls from beneath, a breakwater of dumped rock, a
  tyre, a chain, a crab pot, an anchor, fishing lines, seals, kelp at the edge).

**The layout is the user's own drawing** (described to this agent in words; the picture itself was not saved).

## The map

Coordinates are the world's metres: x east, z south (north is -Z, the sonar's N). `tools/bay_map.gd` draws it.

| On the drawing | Zone | Where (world) | Depth | The real place it stands for |
| --- | --- | --- | --- | --- |
| BEACH (magenta), all round the shore | `beach` (a strip, not a circle) | the first 14 m out from every shore | 0 to 5 m | the surf-zone sand from Santa Cruz round to Monterey |
| KELP (red), north-east | `kelp` (second patch) | round (54, -64), r 19 | 8 to 14 m | kelp off Capitola and Aptos, north of the canyon |
| KELP (red), inner south-east, the bigger | `kelp` | round (53, 42), r 30 | 8 to 16 m | the kelp along Monterey, Cannery Row and Pacific Grove |
| SAND (yellow), north-west | `sand` | round (-74, -78), r 34 | 12 to 22 m | the sandy shelf off Santa Cruz (garden eels) |
| TRENCH (blue) | `trench` (its water over 45 m deep) | head at (94, -8), Moss Landing; an arm west to (-6, -6); a basin from (-24, 4) to (-74, 102) | 22 m at the head, 70 to 100 m in the basin | the Monterey Submarine Canyon, whose head is about 150 m off Moss Landing harbour |
| the pirate ship (black) | `pirate` | a sandy hollow round (-80, -13), 50 m across | 18 to 22 m | (fantasy) on the canyon's western rim, south of the sand |
| (the user's next words) | (part of `pirate`) | the outcrop the ship struck, round (-98, -24): six sea stacks and nine leaning shards round a low flat rock 8 m across standing 1.1 m out of the water, three harbour seals and a sea lion hauled out on it | 22 m | Seal Rock off Pebble Beach / Bird Rock |
| ATLANTIS ("in the lower spot of the trench") | `ruins` | a level terrace round (-75, 74), 70 m across, standing up out of the canyon's floor | 42 m, the canyon 90 to 100 m round it | (fantasy) the lower end of the canyon's basin |
| GRASS (purple) | `grass` | round (-11, 78), r 15 | 1 to 7 m | eelgrass off the peninsula's west side (Monterey's real eelgrass is the Del Monte meadow, 6 to 9 m) |
| REEF (green), the X | `reef` | the liner's shelf round (-40, 130), 56 m flat and 77 m across | 25 to 35 m | off Point Lobos at the head of the Carmel Canyon |
| DOCKS (cyan), Monterey | `docks` | round (35, 78), r 14 | 6 m (dredged) | Monterey harbour: Fisherman's Wharf, the commercial wharf, the Coast Guard breakwater |
| docks by Santa Cruz | `docks` (second patch) | round (-27, -107), r 13 | 4.5 to 9 m | the Santa Cruz wharf and small craft harbour |
| EDGE (orange) | `open` west of it | the shelf's edge at x = -112 (wavering); the world ends at x = -157 | 60 to 70 m beyond | the shelf break and the open Pacific |
| ("the margrove river part goes in the center part where that river meets the bay") | `river` | Elkhorn Slough, a channel 13 m wide winding inland from (86, -18), mangroves on both banks | 4 m | Elkhorn Slough at Moss Landing, beside the canyon's head |

Also: the Carmel Canyon runs from Carmel Bay (13, 142) west past the liner's shelf and round to the north-west (18 to
85 m deep); the Monterey Canyon also runs on west out to sea from its basin, across the shelf's edge.

`Sea.WRECK_AT = (-40, 10, 129.6)`, `Sea.WRECK_HEADING = 1.4` (the hull along the coast, roughly east-west; a lane
64 x 14 m kept clear). `Sea.RUINS_AT = (-75.2, -2, 73.6)`, `Sea.RUINS_HEADING = -0.785` (its front, -Z, faces north-east
up the canyon). `Sea.PIRATE_AT = (-80, 19, -12.8)`, `Sea.PIRATE_HEADING = 0.3` (a lane 34 x 12 m). Each is on the floor:
the shelves are level at their middles and the floor's bumps are left off them.

## How it is built

- `scripts/bay.gd` is the one sum of the floor, drawn on a chart of its own metres and scaled into the world by
  `Bay.K` (0.8): land as capsules (the shore is a radius out from a segment), the beach slope, the shelf, Elkhorn
  Slough cut through the land, harbours dredged level, the drop past the shelf's edge, the canyons as polylines (each
  point a half width and a floor depth), and the three level shelves. `Sea.ground` reads it from a 2 m grid made the
  first time it is asked (0.2 to 0.4 s on the desktop; under a microsecond a call after). The sand mesh is built on
  the same grid. Depths are not scaled.
- `Sea.ZONES` keeps every key the code used (river, grass, sand, kelp, reef, open, trench) and adds docks, ruins,
  pirate, beach. A zone may have more patches (`also`); `Sea.place(rng, "kelp", ...)` picks one by its size.
  `beach` is any water near the shore; `trench` is the canyon's water over 45 m deep; `open` is the strip west of the
  shelf's edge or, half the time, the water over the canyon's basin (the whales need the room). `Sea.START` is where a
  run starts (Main's `_start` and Fishers' `START` read it).
- `tools/build_docks.py` -> `models/docks.glb` and `tools/blend/docks.blend` (3,100 triangles in all): a pile crusted
  with barnacles and hanging mussel clumps, a 4 m length of slatted wharf deck on stringers, a floating dock, a moored
  sailboat, a tyre, a crab pot, a run of chain, an anchor, and the outcrop's sea stack, shard and seal rock.
  `scripts/scenery.gd` lays them out as MultiMeshes, one set a site (Monterey, Santa Cruz, the outcrop), hidden beyond
  80 m; the docks keep their own size and are anchored at `Scenery.MONTEREY` and `Scenery.SANTA_CRUZ`. The moored skiff
  is the fishing gear's, the trawler alongside the commercial wharf is `models/shrimp_boat.glb`, both used as they
  are. The breakwater is GameCommon's rock pieces. Piles, floats, hulls and the outcrop stop a swimmer through
  `Sea.add_rock`. The seals on the rock are the installed creatures posed still (no resting pose exists; they do not
  slip into the water).
- `tools/bay_map.gd`: the chart from above, zones outlined and named, the wrecks' and Atlantis's boxes, the beach
  strip's edge dotted, the seal rock and the title boat's circle:
  `godot --path . --audio-driver Dummy -s tools/bay_map.gd -- --out=<png>` (a short window, for the names).
  `tools/bay_shot.gd` takes pictures of each place (sea and scenery only, no life).

## The scale

The real bay is about 50 km from Santa Cruz to Point Lobos; the game's is 291 m north to south and 277 m east to
west, the shapes squeezed to the user's drawing rather than to scale (roughly 1 m of game to 170 m of bay), about 1.2
times the old sea's area: compact, as the user asked. Depths are squeezed far more: the real canyon is 1,000 to 2,000 m
deep in the bay; here it is 100 m, deep enough to be dark.

## Choices that were Claude's (change freely)

- Every number above, and where exactly each patch sits within the area the user drew.
- **The start** is (-52.8, -36.8), over the sand between the north kelp and the pirate ship. The coordinator suggested
  near the kelp or the docks, but the title's boat steams round a circle 45 m in radius with its middle 45 m east of
  the start, which must be over water at least 6 m deep and clear of rocks and kelp; in the user's layout the kelp and
  docks are against the east and south shores, so the only room is the open water of the bay's north-west.
- The liner's lane runs east-west along the coast; Atlantis faces north-east, up the canyon; the pirate ship lies
  along the canyon's rim with its outcrop at its north-west end.
- The sonar's "reef" sign is now a liner's hull with two funnels; new signs: an anchor for the docks, a temple front for
  Atlantis, crossed cutlasses for the pirate ship. There is no sign for the beach (a strip has no one place) and each
  zone shows only its first patch (Main's `_sound_out` reads `Sea.ZONES[zone].at`).
- Who lives where (`Species.ALL` "zones").
- The fishing gear was moved off the old map's coordinates (Fishers' NETS and LOOPS were fixed points that now fell on
  land): the trawlers work the open water past the edge and down the canyon's basin, the drift nets hang past the edge,
  the bottom net lies in the sand off Santa Cruz; four more float rigs on the beaches and in the docks (anglers' lines).
- The wharf deck stands 0.9 m over the water (lower than a real one) so that its slatted underside is seen from below,
  as in the concept.

## Alternatives considered

- A real bathymetry grid of the bay, scaled down: rejected; the user drew their own layout.
- A baked height map image: the grid made at start-up from the sum is the same at run time and keeps the sum
  editable in one place.
- Separate zone names for the second patches ("kelp_north", "docks_north"): rejected, as every kind living in the
  kelp would have needed both names.

## Not done / not verified

- `tools/build_sea_floor.py` and `models/sea_floor.glb` / `sea_rocks.json` are retired (nothing loads them).
- Main's `--near=` takes only the old zone names, and its warm-up behind the title counts kelp, grass, sand and reef as
  the start's waters. Those are Main's to change.
- Nobody has swum it by hand.
