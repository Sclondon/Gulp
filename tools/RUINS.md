# The Atlantis ruins: design sheet and record

The user (2026-11-18): "another location should be atlanits ruins"; then concept art made at the user's request
("We need a concept are solution": concept first, then build to it): `tools/art_src/concept_atlantis.jpg`. The user
also said where it goes: "in the lower spot of the trench" (the map agent places it). Everything else here is
Claude's design (see "Whose calls").

Files: `tools/build_ruins.py` (Blender 4.3) builds `tools/blend/atlantis_ruins.blend`, `models/atlantis_ruins.glb`
and bakes `textures/ruins_atlas.png` (2048, the stone) and `textures/ruins_atlas_statue.png` (1024, her face, the
statue, the reliefs); `scripts/ruins.gd` (`class_name Ruins`) draws it with `shaders/ruins.gdshader`;
`tests/ruins_view.gd` runs the checks and takes the pictures.

## The idea

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

## Reference looked at (2026-11-18)

- Minoan columns (Knossos: Evans; Janson; Blomfield, Greek Architecture): shafts that narrow downwards, a fat
  cushion capital, a square abacus. Kept: the downward taper (0.38 m at the foot, 0.5 at the top), the capitals.
  The red shafts of the first design were dropped for the concept's grey-green stone.
- Mycenae: the Lion Gate (a lintel over the way in, carved above) and the Treasury of Atreus (a corbelled dome
  14.5 m across). Here: a dome 16 m across, a lintel 9.6 m long on carved posts.
- Drowned stone (Baiae): sand metres deep over floors, stone broken into many pieces, tops furred with growth. Here:
  everything sinks into the sand, tops greened in the paint, the paving tilted and gappy.

## Scale and axes

Metres. Godot axes: origin in the middle of the precinct, y = 0 on the sea bed (everything reaches 1 to 2 m below,
so it sits on uneven ground). The processional way runs along +Z: a visitor comes in from +Z swimming towards -Z,
through the gate at the left front. +X is the visitor's right. About 64 m (x -22 to 40) by 66 m (z -30 to 36), 20.6 m
high at the crystal's tip.

## Plan (Godot x across, z down the page; the visitor comes from the bottom)

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

## The buildings (as built)

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

## Swim routes (tested: `tests/ruins_view.gd -- --check` walks each every 0.4 m through `Sea.clear_of_rocks`)

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

## Palette

From the concept: grey-green stone streaked darker green, pale creamy marble for her head and hand, verdigris
panels, copper inlays (spirals, bands, waves, leaves) that glow faintly (red-gold), a pale cyan crystal glowing. The
baked paint adds growth on every top, silt at every foot, occlusion in the hollows, lamplight inside (the chamber,
her head, under the dome) so no interior is black.

## Budget and how it is drawn (as built)

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

## Checks

- Inside-out: Blender, every piece by itself (a ray from each face along its normal leaves the piece an even number
  of times, three rays voting): 373 pieces, 1 face of 6,000 flagged (a ray grazing an edge on one column drum).
  Godot, read back from the .glb (`ruins_view.gd -- --check`): every part 100% of triangles wound with their
  normals and positive volume (slivers under 5 cm2 from triangulating long concave faces are skipped).
- Headless import; every route open; `sh tests/smoke.sh`: GULP SMOKE PASSED.

## Quality passes (pictures in the scratchpad, read by Claude each time)

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

### Against the concept (`concept_view` picture beside `concept_atlantis.jpg`)

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

## Whose calls

The user's: Atlantis ruins as a location; concept art first, then build to it; its place, "in the lower spot of the
trench". The coordinator's brief (not the user's words): the list of buildings, swim routes and sizes, the budget,
the files, one shader, the checks.

Claude's (change freely): the people and their style (bronze-age, part Minoan, part Mycenaean, spirals and copper);
the sea queen; following the concept over the brief where they differ: dropping the quay and stone ship, the
cyclopean towers, the cella, the stoa's back wall and fresco, and the crown (the concept's head has none: the
statue's route is a tunnel through her hollow head instead); a second, smaller picture for the statue; lamps baked
in at the lantern spots; collision spheres allowed 0.25 m proud; the mouth only for small fish (room 0.1).

## Not verified

- Never seen in the game itself, under its post tint, in the trench, at night, on a phone or in a web build (its two
  pictures add about 4 MB; one more shader to compile at start).
- The cost of 940 spheres where many fish swim near them; the 86 pieces of sea life (51,600 triangles) on phones.
- Whether the game hangs lights at `lanterns()` (the pictures did; the ruins themselves do not light anything).
