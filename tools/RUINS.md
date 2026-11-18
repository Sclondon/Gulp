# The Atlantis ruins: design sheet and record

Atlantis is built into the stepped walls of the Monterey Canyon's deep south-western basin. The user, in order
(2026-11-18): "another location should be atlanits ruins"; "atlantis shouldn't just be a giant crater"; "The Atlantis
ruines area shouldnt just be a big open flat area, it should be built into the trench sides"; "the ruins need to be way
further out in the deepest part of the trench" (circled about world (-60, 53)); "the trench needs to be carved out
with terrace like steps, no just one huge cliff" (done in the floor: CLAUDE.md "Terraced trench"); "Keep going with
atlantis". Concept, made at the user's request ("We need a concept are solution"):
`tools/art_src/concept_atlantis_canyon.png` (Atlantis in canyon walls: a temple on a jutting ledge, rock-cut fronts
in the cliffs, stairs down the walls, a pyramid half into a wall, an arch across, the fallen head and hand on the
floor, the glowing crystal pillar); each building's look is the first concept's, `tools/art_src/concept_atlantis.jpg`.

## Files

- `data/ruins_layout.json`: THE table. Where every building, ledge and stair is (world x, z and depth), read by the
  model's build, by `Bay` (the floor under them) and by `Ruins` (routes, plants kept off). Change it here only.
- `tools/ruins_ground.gd` -> `tools/ruins_ground.json`: `Sea.ground` round the site in the ruins' own space, with the
  table's ledges, for the build (footings, rubble, the bake's shadowing floor).
- `tools/build_atlantis_canyon.py` (Blender 4.3, about 15 minutes with the bake; `-- --no-bake` skips it) ->
  `tools/blend/atlantis_canyon.blend`, `models/atlantis_canyon.glb`, `textures/ruins_canyon_atlas.png` (4096, the
  stone) and `textures/ruins_canyon_statue.png` (1024, her face and the reliefs). Its shapes, columns, head and paint
  are `tools/build_ruins.py`'s top part, run from it.
- `models/ruins_canyon_extra.json`: extra collision spheres (`tests/setpiece_hits.gd --fit-ruins`).
- `scripts/ruins.gd` (`class_name Ruins`) draws it with `shaders/ruins.gdshader`; `Sea.RUINS_AT` is the table's origin.
- `tests/ruins_view.gd`: `-- --check` (the checks below) and the pictures (`--out=`, `--sides`, `--only=`).
- After a change to the table or the floor: `godot -s res://tools/ruins_ground.gd`, the build, `--import`,
  `tests/setpiece_hits.gd -- --fit-ruins --no-ruins-extra` (the extra spheres), then `tests/ruins_view.gd -- --check`.
- Retired, kept unused: the first, flat Atlantis (`tools/build_ruins.py`'s model, `tools/blend/atlantis_ruins.blend`,
  `models/atlantis_ruins.glb`, `textures/ruins_atlas*.png`, `models/ruins_extra.json`) and `Bay.RUINS_TERRACE`.

## The basin and the layout

The floor (raw, without ledges): the canyon comes in from the north-east (x -50, z 16, 54 m), opens into a basin whose
floor is 82 m at (-60, 53) and 96 m at (-78, 64) and runs on west. Its walls are the trench's terraces: a flat tread
every 14 m of depth (26, 40, 54, 68, 82, 96) with a steep riser between, the north wall from z about 32 (26 m) down to
z 56, the east wall from x -34 down to x -60, the south wall from z 80 down to z 64. Every building stands on a tread.

| Building | Where (world x, z) | Wall | Depth | What |
| --- | --- | --- | --- | --- |
| Gate | (-64, 23) | north rim, on the shelf | 26 | the way in from the shelf: paving, gate posts, lintel, broken columns |
| Temple | (-80, 27) | north rim, jutting over the drop on a crag | 26.5 | round temple, twelve columns, broken dome |
| StairRim | (-62.5, 27.8) to (-72.5, 44) | down the north wall | 26.5, landing 39.8, 53.8 | from the gate to the colonnade, zig-zag: a flight, a landing, a turn, a flight |
| Colonnade | (-79, 43.5) | north wall, third tread | 54 | a row of columns with a beam, its terrace's spiral frieze |
| FacadeNorth | (-79, 40.5) | north wall's riser behind the colonnade | 54 | rock-cut front, a doorway into a chamber |
| Bridge | (-48, 30), x -60 to -36 | across the canyon where it enters the basin | 40 | deck on a round arch, piers down to the floor |
| Landing | (-34, 30) | east rim, second tread | 40 | the bridge's east end; the crystal pillar |
| StairEast | (-38, 35) to (-49, 45) | down the east wall | 40.2, then down to 54.2 | from the landing to the 54 m tread over the pyramid |
| Pyramid | (-51.4, 57.5), facing west | east wall, half into it, fourth tread | 68 | five tiers, stair to a high door, chamber and shaft |
| FacadeSouth | (-68, 69.5), facing north | south wall's riser | 70 | rock-cut front facing the basin |
| FacadeTomb | (-76, 56) | foot of the north wall | 82 | rock-cut tomb front on the basin floor's edge |
| Queen | (-85, 66) | the basin floor, levelled 7.5 m round | 96 | the fallen head (hollow) and hand of the sea queen |
| Field | basin floor and treads | | | frieze blocks, drums, fallen columns, capitals, jars, rubble |

The deepest thing to reach, her head, is at 95 to 96 m: inside the 100 m amplifier's limit (100 + 3 give). The gate,
temple, bridge and crystal (26 to 40 m) are reachable with the 50 m amplifier, the colonnade at 54 with 100 m.

Kept clear: the pirate ship (-65, 19, -42) and its lane, the seal rock (-93, -52), OUTCROP_SOUTH (-74, -14), the liner
(-37, 14, 126): the nearest building to any of them is the gate, 65 m from the pirate ship.

## Decisions

- **Built on the trench's own treads, not on a flat** (Claude's design to the user's "built into the trench sides").
  What: each building stands at the depth of a tread of the terraced wall (26, 40, 54, 68, 82, 96); facades stand at
  the foot of a riser with their rock running back into it. Why: the floor's risers ARE the cliffs the concept carves
  its fronts into. Practice: set pieces snapped to the terrain's own levels, with the terrain locally edited under
  them (as level designers stamp terrain under buildings). Alternatives: a flat precinct on the floor (the user
  rejected it twice), carving a new cliff mesh for each building (more geometry, and the floor's rock shading would
  not match).
- **Ledges from the table: `cut`, `fill` or `both`** (Claude's). What: `Bay.ruins_ledges()` makes a small rectangle or circle
  under each building, stair flight and landing, at its depth, blended over 1.5 to 3 m: `cut` only lowers the floor to
  it (behind a facade, so the wall does not fill its chamber; the temple's circle), `both` levels it (terraces, stairs,
  the tread before each facade, the gate's paving, her head). Why `both` for terraces and stairs (second pass): with
  `cut` only, every terrace over a drop stood on masonry and rock blocks reaching down to the floor below, and from the
  basin they hung like curtains and towers (pictures `look0_Colonnade`, `north_wall_from_basin` of the first pass).
  Filled, the floor itself carries each terrace and stair as a tread or ramp of the wall, painted as rock on its steep
  sides by the sand shader like every other riser. Alternatives: rock footings shaped as crags (kept only under the
  temple's jut, where the concept has one), bigger blends (soft mounds, not ledges).
- **One table** (Claude's). What: `data/ruins_layout.json` read by the build, Bay and Ruins. Why: three places that
  must agree on where a building is; one copy cannot disagree (`ruins_view --check` also checks `Sea.RUINS_AT`).
- **Sea life and collision as before** (the flat Atlantis's methods): spheres fitted per piece in Blender (only the
  skin above the floor), extra spheres from `setpiece_hits.gd --fit-ruins`, kit pieces at reef spots.
- **Rock-cut fronts buried in a cliff the floor makes** (Claude's). What: each front has three ledges, in order: a
  `fill` behind it, 6 m wider than the front (`above` its height + 1.5 m, raising the floor only where it is lower, so
  its rock box is buried in a riser, sides too), a `cut` just round its chamber (so that fill does not fill the
  chamber; the tomb's kept tight, as a wider one dug a pit under the colonnade's edge), and a `both` tread before
  it (blend 1 m, so it does not pull the floor down behind the front). Bay gained the `fill` mode and `above` for this.
  Why: the box of rock behind each front stood out of the risers as a plain slab (pictures of the third pass); making
  the box itself taller made bigger slabs. Alternatives: rock boxes shaped to the floor in Blender (the floor's
  stripes and the baked rock never matched), no box at all (the chamber needs walls).
- **Fills square to the world's axes** (Claude's). The pyramid faced -2.1 rad, the south front -2.36: their fills
  came out saw-toothed along the floor's grid (pictures of the first and second passes). Now the pyramid faces west
  (-pi/2) out of the east wall, the south front north (pi), the east stair runs along x. The temple (a circle) and the
  head (a circle) may turn freely.
- **A flight off a landing at a turn starts at the landing's edge** (Claude's, in the build and in `Ruins.routes`):
  from its middle, the landing's slab covered its first steps and blocked the route down.
- **The bridge lighter**: its arch 8 m in radius springing 10 m under the deck (was 6 and 14: a dam with a hole in it).

## Checks (2026-11-18, the final build)

- `tests/ruins_view.gd -- --check`: RUINS CHECK PASSED. 18 routes open: the way and gate; round the temple; between
  its columns and out of the dome; through her head; into her mouth (room 0.1); the colonnade's aisle and four gaps;
  the pyramid's door, chamber, shaft and high door; over and under the bridge; into the three rock-cut doorways
  (room 0.6); down both stairs. `Sea.RUINS_AT` is the table's origin.
- Winding (Godot, read back from the .glb): every part 100% of triangles wound with their normals, positive volume.
  Blender's own ray test: 3 faces of 443 pieces flagged (one on a pyramid tier with cuts, two on her head: rays
  grazing edges). The first build had a stair at 99.0% (folded faces of a 0.4 m rock block under a landing's band):
  blocks under 0.6 m are no longer made (they lay buried anyway).
- Footing (each part's lowest stone in every 1 m column against `Sea.ground`): nothing floats over 0.3 m but what is
  meant to: the gate's lintel (1.4% of its columns), the temple's jut over the drop on its crag (12.5%), the bridge's
  arch over the canyon (47%) and the rim of the hole through her head where it opens just over the floor (3 columns).
- Clipping between parts (Blender, faces crossing above the floor): only where parts meet by design (the colonnade's
  terrace with the stair onto it and the front behind it, the bridge's deck on the landing, the gate's paving at the
  temple's edge).
- Each part alone from four sides and above (Blender workbench) and each building in the water from four sides and
  above (`--sides`): parts set into a wall have their backs in rock, as meant.
- `sh tests/smoke.sh`: GULP SMOKE PASSED (its swarm check had failed twice earlier the same afternoon, while another
  session was working on it).
- Perf (`--perf=start,kelp,pirate,ruins`, 390x844, vsync off, RTX 4080 desktop): ruins 6.75 ms a frame (95th 10.7),
  start 6.2, kelp 8.7, pirate 6.3. In view there: 162,000 triangles, 141 draws; the ruins' own 80,000 triangles at most
  (21 parts and the sea life's MultiMeshes).

## Budget (as built)

- Triangles: 26,534 (Godot's count; Blender's 26,770: Gate 2,376, Temple 5,024, Colonnade 1,714, each rock-cut front
  930, Bridge 448, Landing 460, Pyramid 434, Queen 5,218 (her head and hand), StairRim 732, StairEast 360, Field
  3,870, RuinsGlow 3,344). Sea life on it: 111 pieces of GameCommon's kit, 68,550 triangles.
- Collision: 3,771 spheres (1,655 fitted per piece in the build, 2,116 extra from `setpiece_hits.gd --fit-ruins`).
- Pictures: the stone 4096 (8.5 to 16 px/m), the statue 1024 (her face 29 px/m).

## Quality passes against `concept_atlantis_canyon.png` (pictures in the scratchpad, read by Claude)

1. As the first builder left it: every terrace and stair hung off the wall on masonry and rock blocks reaching down
   to the floor below, like curtains and towers; the rock-cut fronts stood out as boxes; a stair's 0.4 m blocks
   folded inside out; the hand of the queen was in a pit. Fixed: terraces, stairs and the tread before each front
   are floor fills (`both`); blocks under 0.6 m dropped; her floor levelled 7.5 m round.
2. The fills along diagonal headings came out saw-toothed; the bridge read as a dam; the fronts' boxes still showed
   (making the boxes taller to meet the wall made bigger slabs: undone). Fixed: headings square to the axes, a
   lighter arch; the fronts' rock boxes buried by a `fill` behind each; her head moved 7 m west, off the tomb's
   tread; the stairs' flights off a landing start at its edge.
3. Rock teeth still hung under the colonnade's and landing's edges (their fills ended exactly at the terrace's edge,
   so the floor fell away under its rim) and the fronts' box sides showed beside them. Fixed: terrace fills 1 m wider
   all round, the fills behind the fronts 6 m wider, the tomb moved 2 m south and its chamber cut kept to its
   chamber (it dug under the colonnade's edge, 28 m above it); rubble no longer placed on the lip of a riser.
4. Matches now: the temple on its crag jutting from the north rim over the drop; the colonnade on a tread of the
   north wall with a rock-cut front behind it; stairs cut down both walls; the arch across the canyon's mouth; the
   crystal pillar on the far rim; the pyramid half into the east wall with its stair to the high door; rock-cut fronts
   low in the walls; her head and hand on the deepest floor. Still differs: the walls are the floor's regular
   striped terraces (the concept's are broken rock with overhangs); the view is narrower and darker (the game's fog
   at 70 to 96 m; the test has no post tint, so it is bluer than the concept's teal); no light shaft, no jellies (not
   this set piece's); the concept packs everything into one view, the basin spreads it over 50 m, so no one view
   holds all of it.

## Whose calls

The user's: Atlantis ruins as a location; concept art first; "built into the trench sides"; at the circle in the
deepest part of the trench (-60, 53); the trench carved in terrace steps. Claude's (change freely): the layout above
(which building on which wall and tread), the fills and their modes, the headings, the bridge's size, her place on
the floor, the one table, the retirement of the flat Atlantis.

## Not verified

- Never swum by hand; never seen in the game itself under its post tint, at night, on a phone or in a web build.
- The cost of 3,771 spheres where many fish swim (the grids keep a call about 1 us elsewhere).
- Plants kept off by `Ruins.covers` were not looked at around the fills' edges.
- Rough: from some angles in the basin a rock-cut front's box of rock still shows a plain side where the wall beside it
  falls away; the stone is cleaner and blockier than the concept's; the floor's fills are steep-sided blocks painted
  as rock by the sand shader, not modelled cliffs.
- The bake's floor is the build's own copy of the floor (`ruins_ground.json`): after any later floor change the
  stone's baked shadows will not match until it is rebuilt.

## The first, flat Atlantis (retired 2026-11-18; its look and helpers are reused)

The record of the first build (`tools/build_ruins.py`, `models/atlantis_ruins.glb`), kept because the canyon
build runs its helpers and keeps its buildings' look. Its plan and positions no longer apply.

### The idea

A sacred precinct of a lost bronze-age sea people, drowned and half buried. Part Minoan (columns with cushion
capitals and square abaci, horns of consecration were in the first design), part Mycenaean (a lintel on great posts,
a beehive dome), part its own: running spirals and wave bands everywhere, copper/orichalcum inlays gone green with a
few still red-gold. No film's or game's Atlantis copied. The heart of it is a colossal sea queen, her mask-like head
and her hand fallen before her own temple.

What makes it "Atlantis" at a glance, at phone size and through the fog:
1. A round temple ringed with columns, its dome broken open.
2. A colossal fallen face with empty eyes, pale against the grey-green stone.
3. One tall pillar with a glowing crystal on top: the only light of its own.
4. A stepped pyramid with a stair, and carved spiral blocks strewn in the sand.

### Reference looked at (2026-11-18)

- Minoan columns (Knossos: Evans; Janson; Blomfield, Greek Architecture): shafts that narrow downwards, a fat
  cushion capital, a square abacus. Kept: the downward taper (0.38 m at the foot, 0.5 at the top), the capitals.
  The red shafts of the first design were dropped for the concept's grey-green stone.
- Mycenae: the Lion Gate (a lintel over the way in, carved above) and the Treasury of Atreus (a corbelled dome
  14.5 m across). Here: a dome 16 m across, a lintel 9.6 m long on carved posts.
- Drowned stone (Baiae): sand metres deep over floors, stone broken into many pieces, tops furred with growth. Here:
  everything sinks into the sand, tops greened in the paint, the paving tilted and gappy.

### Scale and axes

Metres. Godot axes: origin in the middle of the precinct, y = 0 on the sea bed (everything reaches 1 to 2 m below,
so it sits on uneven ground). The processional way runs along +Z: a visitor comes in from +Z swimming towards -Z,
through the gate at the left front. +X is the visitor's right. About 64 m (x -22 to 40) by 66 m (z -30 to 36), 20.6 m
high at the crystal's tip.

### Plan (Godot x across, z down the page; the visitor comes from the bottom)

```
 z=-27        colonnade (two rows of six columns along x, aisle between)
 z=-21        | | | | | |
 z= -6     ( temple, dome )                 [ pyramid, stair to +Z ]        
 z=  6                                                         (P) crystal pillar
 z= 10            (HEAD) (hand)
 z= 14  [gate]
 z= 20    |      frieze blocks, drums, amphorae, rubble
 z= 36    way
       x=-18     x=-2   x=5                 x=26              x=38
```

### The buildings (as built)

- **Processional way** (x -18, z 18 to 36): paving slabs tilted and gappy, column stumps either side, two toppled
  columns; more paving across the court.
- **The gate** (x -18, z 14): two carved posts 1.8 m square and 8.5 m high on plinths, each face with a verdigris
  panel and three copper spirals; a lintel 9.6 m long with a frieze of five spirals each side and a cornice (a corner
  of it fallen). Opening 5 m wide, 8.5 m high.
- **The temple** (middle x -2, z -6): a stepped round platform 21 m across, twelve columns (radius 7.4 m, 7 m
  shafts, copper bands) carrying a round beam with spiral rosettes, a corbelled dome to 15.9 m broken open at its
  front; one column broken, one fallen; fallen dome stones; the empty pedestal she stood on, her broken feet on it.
- **The colossal head** (x 5.2, z 9.8): a sea queen in the archaic manner: deep almond eye hollows (the concept's
  empty eyes), a straight nose, full lips in the archaic smile, parted, a roll of waves on the brow and curls over the
  crown. 8.3 m from neck to crown. She lies tilted back, face to the way in, sunk in the sand to her cheeks. She is
  hollow (a 0.6 m shell) and broken through at both temples: a fish swims in one side and out the other; her parted
  lips (1.7 by 0.9 m) lead small fish into the hollow; her eyes are open to it too.
- **Her hand** (x 11.6, z 12.4): palm down on the paving, fingers spread and curled into the sand, a bracelet.
- **The colonnade** (x 0 to 19, z -21 and -27): two rows of six columns, an aisle 6 m wide, a beam over four of the
  front row, the back row more broken (a beam fallen across, a column fallen out).
- **The stepped pyramid** (middle x 26, z -6): five tiers and a pointed cap to 14.6 m, a stair up its front between
  low walls to a small high door; a dark doorway at its foot beside the stair (3 by 2.8 m, a lintel and a copper
  spiral over it) into a chamber 7 m square and 4.2 m high; a shaft 3 m square up from the chamber to the high door.
- **The crystal pillar** (x 38, z 6): a slender shaft 1.7 m thick, two copper bands, a cushion capital, a cup of
  red-gold leaves, the crystal (glows).
- **The field**: four carved frieze blocks (four spirals over a copper wave band), drums, two fallen columns,
  capitals, amphorae, rubble.
- Dropped from the first design, to follow the concept: the cyclopean gate towers, the cella wall round the head,
  the long stoa with its back wall and fresco, the quay with mooring rings and the stone ship with a bull's head,
  the horns of consecration, the red Minoan shafts.

### Swim routes (tested: `tests/ruins_view.gd -- --check` walks each every 0.4 m through `Sea.clear_of_rocks`)

`room` is a swimmer's clearance (Player: 0.3 of its length): 0.9 takes a fish about 3 m long.

| Route | Opening (geometry) | Tested at room |
| --- | --- | --- |
| Up the way, through the gate, across the court | 5 m by 8.5 m | 0.9: open |
| Round the temple (outside its columns) | 2.7 m between columns and the platform's edge | 0.9: open |
| Between its columns, under the dome, out of the hole | gaps 3.1 m; hole about 8 m | 0.9: open |
| Through her head, temple to temple | holes 3.5 m across; hollow 4.4 m | 0.9: open |
| Into her mouth and on into the hollow | 1.7 by 0.9 m | 0.1 (small fish only): open |
| Down the colonnade's aisle | 6 m wide | 0.9: open |
| Between the colonnade's front columns (five gaps) | 2.6 m | 0.9: open |
| Pyramid: doorway, chamber, up the shaft, out the high door | 3 x 2.8 m; 7 x 4.2 m; 3 x 3 m; 3 x 2.6 m | 0.9: open |

### Palette

From the concept: grey-green stone streaked darker green, pale creamy marble for her head and hand, verdigris
panels, copper inlays (spirals, bands, waves, leaves) that glow faintly (red-gold), a pale cyan crystal glowing. The
baked paint adds growth on every top, silt at every foot, occlusion in the hollows, lamplight inside (the chamber,
her head, under the dome) so no interior is black.

### Budget and how it is drawn (as built)

- **Triangles: 23,070** (RuinsGate 2,902, RuinsTemple 10,374 of which her head about 4,700, RuinsStoa 1,778,
  RuinsPyramid 442, RuinsField 4,554, RuinsGlow 3,020). Sea life grown on it: 86 pieces of GameCommon's kit,
  about 51,600 triangles more (their light models where they have over 1,300).
- **Texel density**: her face 33.8 px/m (its own 1024 picture, one island wrapped round her head); column shafts
  11.2 px/m, masonry 9.7 px/m, plain stone 9.9 px/m (the 2048 picture). The shader adds a fine world-space grain so
  the stone holds up close.
- **One shader** (`shaders/ruins.gdshader`): the baked picture lit by the sea's lights, fogged by its water, `tint`
  for day and night, `glow` on only for the glowing parts' material (three materials of the one shader).
- **Collision: 940 spheres** (`Sea.add_rock`), fitted per piece in Blender: candidates inside the stone (and under
  the sand: a few big spheres cover a platform's top), the fewest that cover 92% of the skin above the sand within
  0.34 m. They may stand 0.25 m proud of the stone (a swimmer keeps that much further off a wall).
- Parts hide beyond 60 m plus their own size (`visibility_range_end`), as Scenery's plants.

### Checks

- Inside-out: Blender, every piece by itself (a ray from each face along its normal leaves the piece an even number
  of times, three rays voting): 373 pieces, 1 face of 6,000 flagged (a ray grazing an edge on one column drum).
  Godot, read back from the .glb (`ruins_view.gd -- --check`): every part 100% of triangles wound with their
  normals and positive volume (slivers under 5 cm2 from triangulating long concave faces are skipped).
- Headless import; every route open; `sh tests/smoke.sh`: GULP SMOKE PASSED.

### Quality passes (pictures in the scratchpad, read by Claude each time)

1. First build (my own layout, before the concept arrived): routes blocked by spheres 5 to 9 m across: the inside
   test for sphere centres (the nearest face's normal) was wrong at near ties by the rim of a ring, so spheres filled
   the cella's air. Fixed with a three-ray parity vote. Spheres 3,697 at first, then 1,134 (sand counted solid,
   spheres 0.25 m proud, 92% cover).
2. Concept arrived: layout rebuilt to it (above). Then: her face looked at the sky, not at the visitor; the temple's
   columns were stubby under the dome; the hand's finger segments read as separate blocks; red barrel sponges looked
   like pumpkins; the pyramid chamber was black. Fixed: head turned to face the way in and sunk to the cheeks;
   column shafts 5.6 to 7 m; fingers overlapped and smoothed; barrel sponges taken out of the life list.
3. Her face read as a flat slab with faint eyes and a round "O" mouth; UV seams drew a stair-step grid across it.
   Fixed: deep almond eye hollows (the concept's empty eyes), a narrower slit for the lips, a rounder skull, curls over
   the crown, and her face as one island wrapped round her head (seams gone). Foreground drums looked like tin cans:
   halved in number.
4. Interiors (chamber, her hollow) baked black: no sky reaches them. Fixed: lamps at the lantern spots during the
   bake; first too bright (washed-out cyan), then a quarter of that. The temple floor was a bare disc: added the
   empty pedestal with her broken feet. The tunnel through her head closed by 0.16 m when the spheres shifted:
   bigger holes, centred on the hollow.

#### Against the concept (`concept_view` picture beside `concept_atlantis.jpg`)

Matches: what is where (gate left, temple middle, head and hand before it, colonnade behind, pyramid right, pillar
far right); the gate's carved posts with inlaid spirals and its spiral frieze; the open ring of columns under a
broken dome; the mask-like face with empty eyes, sunk in the sand; the palm-down hand; the stepped pyramid with a
stair to a high door and a dark doorway at its foot; the pillar with copper bands and a crystal in a cup of leaves;
the spiral-and-wave frieze blocks, drums and amphorae in front.

Still differs: the colour (the test scene is the game's navy water without the game's teal post tint, so it reads
bluer and flatter than the concept's teal-green); no beam of light falling on the head, no jellies or shark (not
mine); the concept's stone is more broken and chipped at every edge, mine is cleaner low-poly; her hand is blockier
(a box palm); the dome is masonry-coursed where the concept's is smooth; the pyramid is wider and less steep;
the concept has more columns in the colonnade and a second colonnade beyond.

### Whose calls

The user's: Atlantis ruins as a location; concept art first, then build to it; its place, "in the lower spot of the
trench". The coordinator's brief (not the user's words): the list of buildings, swim routes and sizes, the budget,
the files, one shader, the checks.

Claude's (change freely): the people and their style (bronze-age, part Minoan, part Mycenaean, spirals and copper);
the sea queen; following the concept over the brief where they differ: dropping the quay and stone ship, the
cyclopean towers, the cella, the stoa's back wall and fresco, and the crown (the concept's head has none: the
statue's route is a tunnel through her hollow head instead); a second, smaller picture for the statue; lamps baked
in at the lantern spots; collision spheres allowed 0.25 m proud; the mouth only for small fish (room 0.1).

### Not verified

- Never seen in the game itself, under its post tint, in the trench, at night, on a phone or in a web build (its two
  pictures add about 4 MB; one more shader to compile at start).
- The cost of 940 spheres where many fish swim near them; the 86 pieces of sea life (51,600 triangles) on phones.
- Whether the game hangs lights at `lanterns()` (the pictures did; the ruins themselves do not light anything).
