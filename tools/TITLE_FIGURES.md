# The title figures

Three standing figures for the title scene, 2026-11-18: the boy from Warren, a sea captain and an old-time diver.
The scene, the boat, the computer and the boy's helmet are made elsewhere.

The user's words:

- "the main menu / start of the game should be the boy from warren, a sea captain, and and oldtimy diver on a
  shrimping boat (look up reference pics). In the open back cabin of the shrimping boat should be a old timey
  franketstein computer hooked up to a helmet on the boys head- the controls for the pc are the controls for the
  game".
- Then, on the first version: "Looks like you made new models for the captain and diver instead lf using our existing
  human models" and "The captain needs the same smooth mask style face as rhe boy- except maybe a big nose and beard".
- Then: "spend more time coming up with a design for the their outfits ... and do a couple qualitu passes".

So the captain and the diver were made again on the existing man, from the design sheets below. The first version
(new bodies built from tubes) is gone, replaced in the same files.

## Files and use

- `tools/build_title_figures.py`: builds all three.
  1. `blender -b --factory-startup --python tools/build_title_figures.py` (about a minute now).
  2. `godot --headless --path . --import`.
  - `-- --try boy|captain|diver <folder>` builds one figure alone into that folder (its glb and a .blend of it),
    leaving `tools/blend/title_figures.blend` and `models/` alone: for trying changes out.
- `tools/art_src/captain_tattoos.png`: the captain's skin picture with his tattoos, painted by the build script
  (`paint_tattoos`) and packed into his glb.
- `shaders/ink/hair_ink.gdshader` and `shaders/ink/ink.gdshaderinc`: GameCommon ink-figure's hair shader and its
  include, copied unchanged (see "The hair shader" below).
- Retired, kept: `tools/retired/title_boy_warren.glb` (the boy as Warren had him), `tools/retired/title_captain_gansey.glb`
  (the captain before the open-coat outfit), `tools/retired/title_figures_warren_boy.blend` (the .blend before both).
- `tools/blend/title_figures.blend`: the editable file, a collection each (`boy`, `captain`, `diver`), overwritten
  by the script.
- `models/title_boy.glb`, `title_captain.glb`, `title_diver.glb`.
- `scripts/title_figures.gd` (`TitleFigures`): `boy()`, `captain()`, `diver()`, `head_node(figure)`,
  `look_at_point(figure, world_point)`, `look_about(figure)`.
  - Each figure has its origin on the deck under him, faces -Z, and does its task once in the tree (see "At work"; `stand(figure)` gives the standing idle described here).
  - Each is a `TitleFigures.Idle`. Under it, `Model` is the glb, turned 180 degrees and, for the adults, scaled 1.44.
  - The Idle poses a few bones every frame:
    - the arms brought down from the T pose all three are made in (`ARM_DOWN`: 80, 79 and 70 degrees), the elbows a
      little bent, the fingers curled;
    - breath and a slow sway;
    - the head turned toward the point given (the diver turns his top half, his helmet being fixed to his
      breastplate).
  - Every mesh has `lod_bias` 64.

**The boy's head, for the helmet:** `head_node(boy)` is `Boy/Model/boy_armature/Skeleton3D/HeadMount`, a
BoneAttachment3D on the bone `head`. It sits at (0, 1.012, 0) above his feet when he stands straight. In its own
frame +Y is up and +Z is the way he faces. Measured from that joint:

| | x (side to side) | y (up) | z (back to front) |
| --- | --- | --- | --- |
| skin | -0.110 .. 0.110 | -0.049 .. 0.235 | -0.106 .. 0.119 |

- Top of the head: (0, 0.235, 0) on the skin.
- Middle of the skull: about (0, 0.093, 0.006).
- His hair is two meshes (the sailor boy, below): `boy_hair`, which always shows and stays clear of the title's
  helmet, and `boy_hairtop`, the wind-tossed crown, which `TitleFigures` hides while anything is on the head mount.

## At work (the default)

The user (2026-11-18): "The captain needs to be driving the boat(which should be moving), the boy sitting on a
stool plugged into the vr head set, and the diver operating machinery in the back".

A figure made by `boy()`, `captain()` or `diver()` does its task once it is in the tree. `TitleFigures.stand(figure)`
gives the old standing idle, and `work(figure)` puts him back to his task.

The arms and legs are placed by a two-bone solve each frame (`Idle._arm`, `_leg`), so the hands and feet really are
on their marks. The constants below are in the figure's own space: metres from his origin on the deck, Y up, -Z
ahead of him, +X to his right.

### The boy, at the console

- **Stool:** `BOY_SEAT_HEIGHT` 0.42. The stool stands at his origin; his hip joints are 0.479 up, his seat 0.06
  under them, on the stool's top.
- **Feet:** on a rung, `BOY_RUNG` (0, 0.14, -0.2), soles `BOY_FEET_APART` 0.16 apart. His legs are too short to reach
  the deck from 0.42.
- **Hands:**
  - `BOY_LEFT_HAND` (-0.2, 0.8, -0.32) round the ball of a stick;
  - `BOY_RIGHT_HAND` (0.2, 0.74, -0.32) on a button.

  These are the middle of each grip. The targets first asked for, (-0.28, 0.98, -0.5) and (0.28, 0.9, -0.5), are
  out of a 1.27 m boy's reach when seated: from his shoulders (about 0.78 up) they are 0.56 m away, against an arm
  of about 0.42 m. So the constants were moved in to where his hands land with the elbows a little bent. The console
  should be lined up with these.
- **Life:** the stick moves in small slow circles (about 3 cm), and he leans with it. He breathes, presses the button
  now and then, and looks about a little (or at `look_at_point`).
- **The head mount when seated:** `head_node(boy)` is at about (-0.014, 0.888, -0.028) in his root space. Its +Z (the
  way he faces) is about (0.13, -0.17, -0.98), its up (-0.03, 0.98, -0.17): he is looking a little down and to the
  side as he wanders. It moves with the idle look by up to about 0.1 rad.

### The captain, at the wheel

- `CAPTAIN_WHEEL_HUB` (0, 1.05, -0.45), `CAPTAIN_WHEEL_RADIUS` 0.3. The wheel's axis is along his facing.
- Both hands are on the rim at ten and two, going round with it.
- `wheel_turn(captain)` is the wheel's turn in radians. Positive turns its top to his right (clockwise as he sees
  it). Over 15 s it ranged -0.42 to 0.43.
- **Life:**
  - his weight shifts from foot to foot (the feet stay planted, the knees taking it);
  - he breathes;
  - every 8 s he glances out to his left, then to his right.

### The diver, at the pump

- `DIVER_CRANK_HUB` (0, 1.0, -0.34), `DIVER_CRANK_RADIUS` 0.2, one turn every `DIVER_CRANK_TURN` 2.4 s.
- `crank_angle(diver)` is the angle in radians: 0 has the handle straight up from the hub, and it grows as the top
  of the crank goes forward, away from him. The handle is at `DIVER_CRANK_HUB + DIVER_CRANK_RADIUS * (0, cos a,
  -sin a)`.
- Both hands are on the handle's bar (which sticks out across him), 11 cm apart, backs of the hands up.
- The hub is 0.34 ahead rather than the 0.5 asked for: at 0.5 even a full lean left his hands 5 to 8 cm short of the
  far side of the turn.
- **Life:** he leans into it, more as the handle goes away and down, his hips going back and down. His top half
  rocks with the turn; the helmet goes with it, fixed to the corselet.

### Checked

Each was run for 15 s (headless, 60 frames a second):

| Figure | Hand-to-target, worst (left, right) |
| --- | --- |
| Boy | 3 mm, 2 mm |
| Captain | 9 mm, 9 mm |
| Diver | 17 mm, 15 mm (at the near-top of the turn, where the bar comes close to his chest) |

- No bone turned more than 0.25 rad between two frames (0 SHAKE).
- **Pictures:** windowed, of all three with stand-in props (a stool, a stick and a button, a wheel, a crank and its
  machine) at four moments, 0.6 s apart: front, back, both sides, above, three-quarter, and close from three sides.
  All were looked at.
  - That showed the diver's dress coming out through the corselet at the front of the shoulders as his arms
    went forward. Fixed:
    - the dress under the middle of the corselet now goes with the chest;
    - the corselet stands further off over the shoulders.

    Looked at again over the whole turn: clean.
  - No thigh came through the body or below the seat. No arm went through a chest or the beard. The beard cleared
    the arms at the wheel.

## Where each comes from

All sources are read in place by the build script. Nothing is copied, and nothing in GameCommon, Gloaming or Warren
was changed.

| Figure | Existing model | What of it | What is new, and why |
| --- | --- | --- | --- |
| Boy (1.27 m, 9,038 tris as the sailor boy) | GameCommon character controller: `models/boy_tp.glb` (hands, boots), `models/boy.glb` (bare body, mask head) | skeleton, hands, boots, mask head (HeadShape "inside_round", Warren's), and the bare body his clothes are grown from | the sailor boy's clothes and hair (below) |
| Captain (1.76 m, 6,309 tris) | GameCommon `godot/man/files/models/man.glb` (Gloaming's man) | skeleton, proportions, build keys (`heavy` 0.5, `body_gut` 0.35, `body_shoulders` 0.3, `body_neck` 0.4), hands, his own `man_legs__trousers` piece (trousers into boots, recoloured oilskin and rubber), and the gansey grown from his own body's surface | see below |
| | GameCommon `models/boy.glb` `boy_head__base` | the boy's mask head, reshaped as HeadShape `mask_long`, scaled to 0.64 and set on the man's neck | |
| Diver (1.83 m, 6,286 tris) | the same `man.glb`, no keys | skeleton, proportions, hands, and the canvas dress grown from his body's surface | the bonnet, corselet, brails, weights, belt fittings, knife, boots and hose |

**Made new, and why:**

- **The diver's gear:** nothing like it exists in GameCommon or Gloaming. It is built with the character
  controller's `build_character.py` Builder, in place.
- **Captain:**
  - the nose and moustache, the one feature the user asked for besides the beard;
  - the cap, its peak and cord;
  - the roll collar and the ribbed hem and cuff bands, so the garment edges are clean;
  - the pipe.

  These are small Builder pieces fitted to the measured head and garment.
- **Grown from existing surfaces, not modelled anew:**
  - the beard and the hair are the mask head's own surface, cut out and stood off it;
  - the gansey and the dress are the man's own surface, cut out and stood off it.

  This is how Gloaming's `build_man.py` makes his braies.

The man's head is not used: the captain wears the boy's mask head, and the diver's head is hidden by the helmet.
His body under the clothes is dropped too, so it cannot poke through. Only his hands show.

## Design sheets

### What the scene asks of them

They stand on the open back deck of a shrimp boat, next to a rusted-brass Frankenstein computer. They are seen
whole, about 100 to 250 pixels tall on a phone and sometimes only 60, lit from above on a pale deck. So each one has
to read from its silhouette and two or three big blocks of colour, not from detail. All three share one family:

- the boy's smooth mask head, with form but no eyes and no mouth;
- plain matte colour, no texture, no outline.

The boat and the computer bring the rust, brass and dull paint. So the figures keep to a few strong, quiet colours
of their own. Each has one warm accent so the eye finds him: the boy's red shirt, the captain's yellow oilskins,
the diver's copper helmet.

### The boy

Replaced on 2026-11-18 by the sailor boy (his own section below). Warren's look (bowl cut, dull red shirt, dark
trousers) is retired in `tools/retired/title_boy_warren.glb`.

### The captain: the old skipper

- **Character:** weathered, warm and stocky. He is past sixty and has stood on this deck for forty years.
- **At 60 pixels:**
  - a dark cap on top;
  - a big pale beard;
  - a dark navy body;
  - bright yellow legs;
  - black boots.

  The yellow trousers are what tell him from the boy and the diver.
- **Silhouette from the front:** a broad barrel. The shoulders are wide and round, with no padded corners, and he
  narrows a little to the legs. The head is small on that body, the beard making a wedge under it.
- **Silhouette from the side:**
  - a belly carried forward;
  - the beard jutting;
  - a big nose;
  - the cap's peak pointing forward;
  - boots with a slight toe.
- **Body:** Gloaming's man (GameCommon `godot/man`) with his build turned heavier (`heavy`, `body_gut`), so he is
  stocky, not a strongman. His own hands are kept.
- **Head:** the boy's mask head (GameCommon's character controller `boy_head__base`, reshaped as one of HeadShape's
  masks), sized to an adult. It has a big bulbous nose, the one feature allowed. Like the boy he has no eyes and no
  mouth.
- **Garments and gear, each with a reason:**
  - **Gansey:** a navy knitted fisherman's jersey, close-fitting and worsted, the skipper's working dress from the
    1900s to the 1950s. It is plain, since the patterns were fading by the 1930s. It has a ribbed roll collar,
    ribbed cuffs and a ribbed hem, made as bands standing a little proud.
  - **Oilskin trousers:** mustard yellow, tucked into his boots. They are the man's existing `legs__trousers` piece
    in oilskin colours; that piece's own boots become his sea boots.
  - **Sea boots:** black rubber.
  - **Skipper's cap:** a navy peaked cap with a soft crown, a short black glossy peak, and a dull brass cord over the
    peak. It is the one thing that makes him "captain" rather than "deckhand".
  - **Beard:** full, short and rounded, white going grey. It is one smooth shell grown from his own face and fuller
    at the chin, plus a moustache under the nose. It is smooth like the boy's hair, not strands.
  - **Hair:** grey, close under the cap at the back and sides, smooth like the beard.
  - **Pipe:** a short briar pipe in the corner of the beard, kept only if it sits well with a mask face.
- **Palette** (sRGB):
  - navy gansey and cap (0.17, 0.20, 0.30);
  - oilskin yellow (0.82, 0.62, 0.20);
  - black rubber (0.10, 0.10, 0.10);
  - weathered skin (0.80, 0.60, 0.48);
  - beard and hair, white going grey (0.86, 0.85, 0.82);
  - nose warmer (0.84, 0.54, 0.44);
  - peak (0.06, 0.06, 0.07);
  - cord brass (0.72, 0.58, 0.30);
  - pipe (0.36, 0.22, 0.13).

### The diver: the old hard-hat

- **Character:** heavy, old-fashioned, patient. All brass and canvas, he stands like a statue. You never see his
  face; the helmet's lights are dark.
- **At 60 pixels:** a big round copper head with a dark front light, a shining collar over the shoulders, a baggy tan
  body, dark lumps of weights front and back, heavy feet, and a black hose curving off him. The round copper helmet
  makes him unmistakable.
- **Silhouette from the front:** a light bulb on a sack. The helmet is wider than his neck could ever be. The
  corselet makes a wide sloped yoke; the sleeves are baggy, with black cuffs and bare hands; the legs are baggy into
  big boots.
- **Silhouette from the side:**
  - the helmet's lights and valve sticking out;
  - the weights jutting front and back;
  - the hose looping from the back of the helmet down to the deck;
  - the boots longer than a man's foot.
- **Body:** the same man, average build (no keys), with his own hands. The dress is grown from his body's surface,
  stood well off it and smoothed, so it bags like canvas over a man. His head is not kept: the helmet hides it.
- **Gear** (after the Siebe Gorman 12-bolt and the US Navy Mark V; shapes only):
  - **The bonnet:** a spun-copper helmet with four lights: the big round front light, two side lights behind guard
    bars, and a small top light. It has an exhaust valve low on his right and the air inlet's goose-neck at the back.
  - **The corselet:** a tinned-copper breastplate (rendered copper, to sit with the helmet). It rests on the chest
    and back over the shoulders, with a brass neck ring the helmet screws onto. A broad brass band runs round its
    edge where the brails clamp the dress's rubber collar, with twelve studs (the "12 bolt").
  - **Weights:** a lead weight hung on the front of the corselet and another on the back, dark grey slabs.
  - **Belt and knife:** a leather belt, with a brass-sheathed knife on his right hip.
  - **Wrist cuffs:** black rubber at the end of each sleeve.
  - **Boots:** canvas uppers, lead soles, brass toe caps, leather straps at the ankle.
  - **Air hose:** black rubber, from the goose-neck down his back to the deck, where it runs off toward the pump.
    The lifeline is left out (one line reads better than two).
- **Palette** (sRGB):
  - canvas tan (0.60, 0.53, 0.40);
  - copper (0.74, 0.44, 0.27, metallic);
  - brass (0.78, 0.62, 0.32, metallic);
  - lead (0.34, 0.35, 0.37);
  - rubber (0.12, 0.11, 0.10);
  - leather (0.32, 0.20, 0.12);
  - dark green-black glass (0.10, 0.14, 0.13);
  - skin as the captain's.

## References looked at (shape and dress only)

- Fishermen's ganseys: worsted, close-fitting, gussets under the arms, navy, plainer by the 1930s:
  flamboroughmanor.co.uk/ganseys/history.htm, ichscotland.org/node/162, and the Lloyd's Register Foundation's
  "Guardians of the fishers: ganseys, oilskins and PFDs" (hec.lrfoundation.org.uk).
- Standard dress: the corselet as an oval collar on chest and back, tinned copper with a broad band round its edge,
  12 bolts clamping the dress (collections.sea.museum, Siebe Gorman helmet; divingheritage.com/siebekern.htm). The
  Mark V bonnet is about 14 in wide and 13.5 in high, with four lights, a front light that opens and an exhaust valve
  (divedesco.com, landandseacollection.com, navalunderseamuseum.org).

## The captain's face

It is the boy's head, so it reads as the same family of figure:

- `boy_head__base` from GameCommon's `boy.glb`, reshaped by HeadShape's `mask_long`. That is one of HeadShape's own
  shapes (a longer chin and narrower jaw, for a grown man); `head_shaped()` in the build script is `HeadShape._shaped`
  line for line.
- Scaled to 0.64 of the boy's size, its joint set on the man's head joint and 18 mm forward.
- No eyes, no mouth and no brows.

Added to it:

- **A big round nose**, set at 40 % of the way from the head joint to the crown, on the face's own front (found by a
  ray). It is four fused ellipsoids: bridge, bulb and two wings, in a warmer skin colour.
- **The beard:** the face's own surface below the nose, stood off it. It is thickest at the chin (about 2 cm,
  modelled), thins to nothing at its edges so it lies on the skin, and hangs a little under the chin.
- **The moustache:** two soft rolls under the nose.
- **The hair:** the head's own surface at the back and sides under the cap, stood off it, in a darker grey than the
  beard.

The pipe was kept: it comes out of the beard where a mouth would be, and with the beard hiding the mouth it reads
well on the mask (pictures at title size and close up).

## Quality passes

Each pass rendered:

- in Blender, every figure from the front, back, both sides, three-quarter and above, plus close-ups of the head and a
  hand;
- in Godot, all three posed (standing about, and turned to look at a point) on a pale deck lit from above:
  - from the front, back, both sides, above and three-quarter;
  - close on each head (front, side, back, above) and a hand;
  - at title-scene size (about 120 and 220 pixels tall).

Every picture was looked at against the design sheets.

1. **First build:**
   - The gansey, the hands and the dress came out in shards: the glTF splits its points at seams, so the surface
     stood off in pieces. Fixed by joining the points first (`weld`).
   - The belly was too big. `body_gut` went from 0.7 to 0.35.
   - The roll collar was a tall drum. It was made lower and closer.
   - The cap stood straight up like a kepi. It now has a soft crown flaring over the band.
2. **Second:**
   - The beard covered only under the chin. Blender's volume-keeping smooth had dragged the open shell 4 cm down.
     Fixed with a plain smooth that holds the edges.
   - The hair showed skin through it and had ragged edges. The head is now cut away under the cap and decimated
     less, and the hair stands off further.
   - The gansey's hem and cuffs were ragged. They are now cut by planes, with ribbed bands round them.
   - Yellow trousers showed above the hem. The trouser top is cut lower and drawn in.
   - The diver's cuffs were ragged. They are now rubber rings fitted to the measured sleeve.
   - The diver's dress showed through the corselet in patches. The corselet was given a wider margin.
   - The lead weights stood off too far. They now hang closer.
   - The skin of the man's own neck showed at the gansey's neck. That neck piece was dropped; the collar covers the
     join.
3. **Third:**
   - The diver's boots were too small and set too far back, so the dress came out of them by 5 cm. They are now
     sized from the measured legs, as ellipses.
   - The hair was the beard's white and read as a white cap from behind. It is now a darker grey.
   - Triangles were trimmed: the dress, the rims of the lights, the hose and the gansey.
4. **Fourth:** a grey patch of hair at the temple met the beard in a jagged line. The hair no longer comes forward
   of the ears. After that, nothing that matters was found, so the passes stopped.

For the user to judge, pictures of the finished figures are in the session's scratch folder:

- `concept_sheet.png`: front, side, three-quarter and title size;
- `concept_heads.png`.

## Checks (final build)

- **Clipping, measured** in Blender at rest, by ray parity for closed pieces, and for open shells by a ray out from the
  body's middle:
  - captain head through cap: 0 of 103 points;
  - captain hair through cap: 6 of 27 points, by up to 6 mm, at the very edge under the band;
  - captain trousers through gansey: 2 of 54 points, by up to 5 mm;
  - captain wrists past the cuffs: 9 of 75 points, by up to 1 cm (where the hands come out);
  - diver dress through the corselet: 3 of 139 points, by up to 5 mm;
  - diver dress through the boots: 11 of 67 points, by up to 5 mm;
  - diver dress through the cuffs: 0 of 32 points.

  In the posed pictures, with the heads turned, nothing came through anything.
- **Inside-out faces:**
  - In Godot every surface of the three .glb files is wound with its normals (WINDING OK). The worst is 3 of 950
    near-degenerate triangles in the diver's dress.
  - In Blender, the shells grown from the body face outward: 98 % of the gansey's faces and 95 % of the dress's point
    away from the body's middle. The rest sit in the armpits and crotch, where that test is loose.
- **Headless run:** all three made with TitleFigures, added to a tree and stepped 300 frames, with no errors.
- **Gulp's smoke test** (`sh tests/smoke.sh`): GULP SMOKE PASSED.

## Not verified

- Not seen in the real title scene, by the boat, under Gulp's post shader, or on a phone.
- The idle was checked only in stills.
- The boy's helmet was not tried on.
- Triangles are slightly over 6,000 for every figure (6,093, 6,309 and 6,286). The diver's brass takes about 2,000
  of his.
- The captain's arms come down from a T pose by linear skinning. His shoulders were not looked at with the arms
  moving.

## Whose calls

The user's:

- the three figures and the scene;
- the existing human models;
- the boy's mask face for the captain, with a big nose and a beard;
- the design work and the quality passes.

Claude's picks, all changeable:

- the design sheets: the navy gansey, yellow oilskins, black boots and the skipper's cap; the diver's Mark V and Siebe
  12-bolt mix, with no lifeline;
- HeadShape `mask_long` for the captain, and the head scale;
- the captain's build keys;
- keeping the pipe;
- dropping the man's body under the clothes and his head;
- the colours apart from the boy's, which are Warren's.

## For GameCommon (not changed here)

- `build_character.py`'s Builder and `make_armature` serve well in place. Its `export` writes under its own `ROOT`,
  so it was not used.
- `character_rig.gd` names the controller's `Player` class, which Gulp already has. That is why the controller was
  not installed and TitleFigures poses the figures itself.
- The way garments are grown here could become a small shared tool:
  - copy the body, cut it by planes, stand it off and smooth it, holding the border;
  - add bands sized from the measured garment.

## Matching the concept art (2026-11-18)

The targets were `tools/art_src/concept_characters.jpg` (the three, front and back) and `concept_boat.jpg` (at work
on the boat). The bodies, the captain's mask head, the poses, the constants and the API are all unchanged.

### What changed

- **Captain:**
  - darker, greyed navy for the gansey and cap, faded mustard oilskins, a redder nose, greyer beard and hair;
  - ribbed bands at the hem, cuffs and a thicker roll collar. The ribs are alternate rings of points shaded
    darker (vertex colour), not noise, with faint knit ribs up the gansey;
  - dark braces laid on the gansey's surface from steel clips at the hem, over the shoulders, into a Y at his back;
  - hands 1.15 times bigger;
  - **the pipe is kept in the corner of his mouth.** He steers with both hands, so it cannot be held in a hand as
    the concept shows.
- **Diver:**
  - greyed tan dress with soft darker stains, dirtier toward the boots (vertex colour);
  - copper and brass with darker tarnish patches;
  - black rubber gauntlet gloves: his own hands 1.18 times bigger in black, with flared gauntlet cuffs;
  - grilles over the lights: a cross over the front light, three bars over each side light, and a grid over a top
    light moved up onto the dome;
  - a small brass plate on the corselet;
  - two grey lead weights on the chest, on leather straps that run up under the corselet's edge and down to the
    belt, with leather straps crossed on his back;
  - a steel buckle and a leather pouch on his left hip;
  - grey boot uppers with black straps;
  - the air hose now runs down his right side, and a three-loop coil of spare hose hangs on his back on the left.
- **Boy:** unchanged in that pass (Warren's look); replaced later the same day by the sailor boy (below).

**Vertex colours:** the adults' glb files now carry a `Tint` vertex colour (1 = as the material is), and
`TitleFigures` turns on `vertex_color_use_as_albedo` for their materials.

### Passes

Each pass rendered the figures standing (front, back, both sides, three-quarter, title size), close up, and at work
over the cycle. The pictures were read beside the concept.

1. **First:**
   - the two weights read as one block (they were laid by rays from the middle line, which pulled them together);
   - the stains and the tarnish were too faint to see;
   - the braces were too dark to read on the navy.

   Fixed: the rays now start under each point; the stains and tarnish are stronger; the braces are lighter.
   Triangles were cut (fewer ribs, strap and hose segments, lighter gloves and dress, smaller studs).
2. **Second:** at work, the coil's three loops fanned out behind his bending back like fins. They now lie closer
   together.

   Left as they are:
   - small dark bits where the braces meet the gansey at the back of the shoulders, seen only close;
   - the coil sits on his back, not over the top of his shoulder as in the concept (draped over the shoulder, it
     would be in the way of his arms as he cranks).

### Still different from the concept

- No closed-eye hints on the faces: the masks stay eyeless, as the user asked.
- The captain is not as short-legged as drawn: he keeps the man's own legs.
- His trousers have no fly or pockets, and his gansey sits over the trousers rather than tucked in.
- The diver's helmet is not dented.
- The diver's coil is on his back, not over his shoulder, and his knife is small.

### Checks

- **Triangles:**

  | Figure | Triangles |
  | --- | --- |
  | Boy | 6,093 (then; the sailor boy is 9,038) |
  | Captain | 7,069 |
  | Diver | 6,792 |

  The adults are over the 6,000 aim: the ribs are about 1,200 of the captain's and the brass about 2,000 of the
  diver's.
- **Clipping at rest:**
  - braces lie 0.4 to 8 mm off the gansey, none under it;
  - none of the hose or coil is inside the corselet;
  - dress through the boots: 11 of 66 points, by up to 5 mm;
  - dress through the cuffs: 1 of 24 points, by 3 mm;
  - dress through the corselet: 2 of 132 points, by 5 mm;
  - nothing of the head comes through the cap.
- **At work:** hands on their targets to 3, 9 and 17 mm at worst over 15 s, with no SHAKE. The gloves close round
  the crank handle all the way round. The coil and the weights clear the arms through the whole turn (four moments
  per cycle, three sides each).
- **Winding:** OK in Godot for all three; the worst is 9 of 700 near-degenerate triangles in the gloves.
- **Headless run:** 300 frames and 15 s of work, no errors.

## The sailor boy (2026-11-18)

The user, with a picture of the cover of the novel "Nick of Time" by Ted Bell: "Nick of Time by Ned Bell is part of
the inspiration, and the art on the cover- the boy needs and old timey sailor boy outfit". The cover was taken for
mood only. Then: "sthe boys hair should use our hair shader to recreate that look", and "and if you need to upgrade
the hair shader, look up how hair is normally done for stuff like this".

Built to `tools/art_src/concept_sailor_boy.jpg` (front, back, side, seated in the helmet). Only the boy changed; the
skeleton, the HeadMount, his size and origin, and everything `scripts/title.gd` and `TitleFigures` use are as they were.

### What he is

Everything is grown from GameCommon's bare boy (`boy.glb` `boy_body__bare`), as the captain's clothes are from the man:

- **Shirt:** loose cream cotton, his body stood off 5 to 17 mm (loosest on the arms), the neck open in a V; tucked
  in (its hem cut level under the belt). **Sleeves rolled above the elbow:** each sleeve cut at |x| 0.29 (the elbow
  is at 0.32) under a roll, a band of the sleeve made solid.
- **Collar, open:** two laid strips of shirt round the back of the neck to points on the chest either side of the V.
- **Neckerchief, faded navy:** a triangle flap on his back; a band close round his neck on each side, then steeply
  down in a narrow V to a flat knot at his throat; two tails, one longer, splayed.
- **Trousers:** khaki canvas, his hips and legs stood off 12 to 34 mm (wide in the leg, high at the waist), cut at the
  ankle under **turn-ups** (a solid band).
- **Belt:** a worn leather band of the trousers made solid, with a square iron buckle and tongue.
- **Clasp knife on a lanyard:** from the belt on his right hip, its handle and short blade lying on his thigh,
  skinned as the trousers there, so it rides on his lap when he sits.
- **Rope bracelet** on his right wrist (its twist painted as vertex tint).
- **Boots:** the boy's own, scuffed brown.
- **Skin that shows:** only his neck and open chest, forearms and ankles are kept of the body, so it cannot poke
  through the clothes.
- **Face:** the boy's smooth mask (HeadShape "inside_round"), unchanged.
- **Hair:** sandy, wind-tossed: a shell grown from his scalp plus flat, arched locks swept to his right and back.
  Split at the helmet's rim into `boy_hair` (the locks below the rim, a short fringe on the brow included, all inside
  or under the helmet) and `boy_hairtop` (the crown and its tufts). `TitleFigures` hides `boy_hairtop` while anything
  is on the head mount, so the title's helmet never shows hair through it; standing bareheaded he has the full crown.
- Weathering: soft stains on shirt, trousers and neckerchief, darker hems, scuffs on boots and belt (vertex tint;
  `TitleFigures` now turns vertex colour on for the boy too).

Colours (sRGB): shirt (0.80, 0.76, 0.65), neckerchief (0.21, 0.25, 0.35), trousers (0.55, 0.50, 0.36), belt
(0.38, 0.23, 0.13), boots (0.40, 0.26, 0.16), hair (0.74, 0.61, 0.40), skin (0.78, 0.62, 0.51), rope (0.66, 0.56, 0.39).

### The hair shader (decision)

- **What:** his hair (and the captain's chest hair) is drawn with GameCommon ink-figure's `hair_ink.gdshader`, the
  hair style Warren's boy is dressed with (`InkFigure.dress(..., {"hair": "ink"})`), copied unchanged from
  `C:\Projects\GameCommon\godot\ink-figure\files\shaders\ink\` with its include `ink.gdshaderinc` (the shader cannot
  compile without it) to `shaders/ink/`. GameCommon's copy and Character Studio's are the same file; Warren's
  `shaders/ink/hair_ink.gdshader` differs (a local change there) and was not used. It is one more shader program,
  used only by the title.
- **How the mesh feeds it:** the shader reads UV.x along each lock (root 0 to tip 1), UV2 in metres, and a tangent
  along the lock. The locks get these from GameCommon's Builder; the scalp shell gets them from `hair_uvs` (along:
  from the crown down; round: round the head, the seam kept on one side). Godot makes the tangents from UV on import.
  The hair meshes are separate from his body, whose surfaces have no such coordinates.
- **Tuning (in `TitleFigures.HAIR_COLOURS` and `_hair_material`, not in the shader):** sandy albedo, pale and flick
  colours, a brown ink, finer and fainter strand lines (`strand_gap` 1.4 mm, `lit_lines` 0.05), softer gaps and
  shadow (`gap_ink` 0.18, `wrap` 0.4, `shadow_fill` 0.4). The defaults are an inked comic print; the concept is painted.
- **Practice looked up:** stylised game hair is clumps or cards whose UVs run along the strands, lit by a tangent
  (Kajiya-Kay) highlight, usually two shifted bands, cut harder for a toon look, the bands following the clump shapes
  (Scheuermann's GDC 2004 hair notes; the Galacean and Cocos hair-shader docs; Polycount threads on stylised
  Kajiya-Kay). `hair_ink` already is that: strand-direction UVs, a Kajiya-Kay highlight cut into flicks, ink between
  clumps. So it was not upgraded, and GameCommon was not touched.
- **Alternatives:** alpha-tested hair cards with a strand texture (finer, but thin and noisy at 100 to 250 pixels,
  needs textures and sorting care, and reads less like the concept's chunky clumps); ink-figure's `sheen` (softer and
  closer to paint, but not the style the boy has in Warren); a wind sway in the vertex shader (not asked for; under
  the helmet in the only place he appears).
- **Whose call:** using the shared hair shader, and allowing an upgrade, were the user's; keeping it un-upgraded, the
  tuning, and how the meshes carry their coordinates were Claude's.

### Checks

- **Triangles:** 6,093 before (Warren's boy). Now 9,038 standing bareheaded: body 7,425 (head 1,300, hands 898,
  shirt 950, trousers 950, the rest small), `boy_hair` 818, `boy_hairtop` 795; 8,243 drawn under the helmet.
- **Hair against the helmet** (the title's: tools/build_helmet.py's cap at `HEAD` 0.128, (0, 0.1, 0.005) on the
  mount; measured in the build on every point): of `boy_hair`, 0 points inside the helmet's shell above its rim. The
  crown is hidden under the helmet. In pictures of the title seated (back, both sides, above, front, close) no hair
  shows through; the brow and side locks show under the rim.
- **Clipping, measured** in Blender at rest and in the seated pose taken from the running title (each bone's pose
  exported from Godot and applied to the .blend; the wrists landed 5 to 7 cm short of the grips' middles, which is
  the hand's length): a point of an inner layer counts as through when the outer layer is behind it along its
  normal (within 1.2 to 3 cm) and not in front of it.
  - skin through shirt: 0 of 85 at rest, 1 of 92 by 0.6 mm seated;
  - skin through neckerchief, trousers and boots: 0;
  - shirt through belt, trousers through belt, trousers through the knife: 0;
  - the shirt's hem lies over the trousers' waist by design (1 to 4 cm, under the belt): those 33 points are the
    blouse, not a poke;
  - shirt through neckerchief: 35 of 115, up to 7 mm, at the strips' edges where the collar and the V's edge lie
    close under them; seen close as one or two small cream specks at the neck (left);
  - head skin through hair: 1 of 465, 5 mm at rest, at the hairline.
- **Inside-out:** every mesh of the three glb files winds with its normals in Godot (the rule of `tests/winding.gd`,
  run on them from a scratch script): boy 99.6 %, `boy_hair` and `boy_hairtop` 100 %, captain 99.9 %, his outfits
  99.3 and 100 %, chest hair 100 %, diver 99.85 %; all enclose their volume the same way round as the unchanged diver.
- **Pictures,** in Godot with the real title (the hull hidden): seated from front, back, both sides, above,
  three-quarter, close on the head and chest; standing from four sides and close; and the game's own
  `--title --offline --shot=3`. Two passes against the concept: (1) the neckerchief lay out across his shoulders like
  wings (sloping rays met the shoulder tops; level rays now), its flap's corners lay on the backs of his arms
  (straight rays from behind now), the shirt's hem showed below the belt (cut under it now), chest skin showed through
  the shirt (only the skin that shows is kept), the trousers' top edge showed at his sides (cut just above the belt),
  the hair was spikes (flat arched clumps now); (2) the collar specks were reduced (collar laid wider, the
  neckerchief laid over it in 7 rows), the crown and nape locks made irregular, the brow fringe widened so it reads
  as hair pressed under the rim.
- **Runs:** the title runs (`--title --offline --shot=3`) with no script errors. Gulp's smoke test fails one check,
  "pack hunters at a swarm take from it and ball it up" (the schooling work, another builder's), nothing here.

### Still different from the concept

- No buttons, pockets, belt loops or back pocket; no light stripe on the neckerchief's edge.
- The hair is clumps in the ink-figure style, chunkier than the painting; under the helmet only the fringe and the
  sides show (the concept's helmet covers all of it).
- The neckerchief's back flap is smaller than drawn; one or two specks of collar show at the neck close up.
- The boots are the boy's own, lower than the concept's lace-up boots.

### Claude's picks

The colours; the knife on his right hip, lying on his thigh; the bracelet on his right wrist only; the hair split
and the crown hidden under the helmet; the shirt bloused over the waistband.

`scripts/title_figures.gd`, every change: vertex colour turned on for the boy too (it was the adults only);
`HAIR_SHADER`, `HAIR_COLOURS` and `_hair_material` (the hair shader on `boy_hair`, `boy_hairtop` and
`captain_chesthair__open`); the crown hidden while the head mount holds anything (`child_entered_tree` and
`child_exiting_tree` on the mount); `wear(figure, outfit)`, and the captain put in "open" when made.

## The captain's second outfit, tattoos and chest hair (2026-11-18, in progress)

The user: "captian should have bushy chest hair and tattoos"; "the captain should have a tasteful bulge"; "the
captain should have the outfit from teh first concept as well to switch into"; then, on seeing work in progress, "he
looks a little to tall and lanky so far in what I can see you are working on", "make sure to capture his staunch
proportions", "he should have hear shaped boxers pose so you can add clothes on top", "his eyes should just be
wrinkly slits", "maybe added on as afacial feature", and "no we need the tpose".

**Superseded in part:** he was rebuilt on his base body later the same day (the next section). What follows was the
first pass, on his old tall body (about 7.4 heads tall, 1.8 m, against the concept's 5 to 5.5); its outfits, tattoos,
chest hair and eyes carried over, as that section says.

### Built so far

- **Two outfits, switchable:** `TitleFigures.wear(captain, "open")` (the default) or `"closed"`. His model is the
  body common to both (`captain`: head, mask face, nose, eyes, beard, hair, cap, pipe, hands, oilskin trousers and
  boots) and a mesh per outfit, named as Gloaming's man's pieces are (`man_<slot>__<option>`):
  `captain_outfit__open`, `captain_chesthair__open` and `captain_outfit__closed`. `wear` shows the meshes whose
  name ends `__<outfit>` and hides the others. Nothing in the game switches it yet.
- **Closed** (`concept_characters.jpg`): the navy gansey, ribbed bands, roll collar and braces, as before.
- **Open** (`concept_captain.jpg`): a navy coat hanging open (his body stood 3 to 5 cm off, open down the front by
  two slanting cuts, made solid so its lining shows, sleeves pushed up below the elbow with rolls, a turned-down
  collar); a cream and navy striped undershirt cut in a low U (the stripes cut into its faces, 28 mm each); braces on
  the undershirt in front and over the coat behind (as the concept draws them); a bush of grey chest hair in the
  neckline (a shell and tufts, drawn by the hair shader); heavier bare forearms; tattoos; a gold hoop in his left ear.
- **Tattoos:** painted by the build script into `tools/art_src/captain_tattoos.png` and laid round each forearm and
  over his chest by UV: an anchor and a compass star on his right forearm; a swallow, a ship on a ribbon and a heart
  on his left; a small anchor on his chest beside the hair. Faded blue-black, no letters.
- **Fullness at the fly:** the front of the oilskin trousers eased out 6 mm at the fly, smoothly.
- **Eyes:** on the mask, as the nose is: a dark narrow slit between a puffy upper and lower lid, a heavy white brow
  over it, three crow's-feet creases at the outer corner. No eyeballs.

### Checks so far

- **Triangles:** 7,069 before. Now the common body 5,120 (the eyes about 690 of it); open outfit 5,721 and chest hair
  940 (11,781 drawn); closed outfit 2,639 (7,759 drawn).
- **At the wheel** (his pose from the running title, applied in Blender): no point of either outfit (hands apart)
  within 2 cm of the wheel's disc; the nearest is 5.6 cm (open) and 4.7 cm (closed) from its plane in model units
  (8 and 7 cm in the game). Pictures from the front, back, both sides, above, three-quarter and close on the arm agree.
- **Clipping** (the boy's measure, at the wheel): forearm skin through the rolls 0; chest skin through the undershirt
  1 of 91; undershirt through the coat 11 of 155 (up to 11 mm, at the shoulders by the neck); the braces' edges dip
  up to 7 mm into the cloth in places (the closed outfit's as before); trousers through the closed gansey 3 of 12,
  2.6 mm.
- A point of each sleeve roll was thrown metres out by Blender's solidify (a sliver at the cut): that was a long dark
  line in the first pictures. `band_of` now puts any point thrown more than 5 cm back on the surface.
- The diver's glb came out byte for byte the same.

## The captain on his base body, three looks, a painted face (2026-11-18)

The user: "no we need the tpose"; "make sure to overly the model onto the tpose until it looks right"; "and if you
need more poses for concept art ask for them"; and, of a trial sheet of faces, "can the models look that good?
remember twilight princess", then "lets try it".

Sheets used: `tools/art_src/concept_captain_tpose.jpg` (his base body, front, side, back, arms hanging low),
`concept_captain_tpose_clothed.jpg` (the same in the open coat), `concept_captain_head.jpg` (his head from the front,
three-quarter, side, back and top), `concept_faces_trial.jpg` (the face test's look). `concept_captain_tpose2.jpg`
was read (its arms hang low too: there is still no true T-pose) and `concept_captain_hands_wheel.jpg` and
`concept_captain_closed.jpg` were not yet built to (see "Not done").

### His proportions (the skeleton changed, not only the mesh)

Everything of him is built on Gloaming's man as before, then given his proportions in one step at rest
(`WARP` and `warp_captain` in the build script): each bone is moved to a new joint and its flesh scaled along and
across it, and every piece (skin, clothes, hair, head) takes the change by its own skin weights (linear blend
skinning done once). The skeleton's bones keep their names; their rest positions are the new joints. The table is
tuned by overlaying him on the sheet (below). Numbers in his model's units (TitleFigures stands him 1.44 times
bigger):

| Joint | Gloaming's man | The captain |
| --- | --- | --- |
| hips | 0.643 | 0.55 |
| chest | 0.842 | 0.75 |
| neck / head | 1.0 / 1.053 | 0.925 / 0.96 |
| shoulder (x, y) | 0.131, 0.934 | 0.225, 0.815 |
| elbow, wrist (x) | 0.341, 0.484 | 0.414, 0.578 |
| hip (x, y), knee, ankle | 0.063, 0.613; 0.323; 0.06 | 0.115, 0.528; 0.222; 0.054 |

Flesh across the bones: hips 1.2, belly 1.28 wide and 1.25 deep, chest 1.2 wide and 1.45 deep, neck 1.45, upper
arms 1.15 to 1.2, forearms 1.3, hands 1.15, thighs 1.3, shins 1.9 wide and 1.75 deep, feet 1.75 wide; the head 1.25
all round. The build key `body_gut` is still 0.35.

Measured, before and after: 1.8 m and about 7.4 heads before; now 1.60 m to his crown (1.70 m to the cap's top),
5.4 heads (his mask head) or about 5 (the painted head, whose beard hangs lower). Shoulder joint 0.73 of his height
(the sheet 0.73); shoulder to wrist 0.32 (the sheet, along the drawn arm, 0.33); hip joint 0.47 (the sheet 0.46);
head 0.185 of his height (the sheet 0.17 to 0.2).

### The overlay (the measure of done)

His orthographic renders from the front, side and back, in the sheet's pose (arms 64 degrees down from level, the
elbows a little bent), scaled and placed on the sheet's floor and cap-top lines, laid over the painting at half
opacity and as an outline, three views each. Rounds 1 to 9 are kept in the scratch folder. Fixes by round: (1) to (2)
shoulders too high and square, arms too long and thick at the top; (2) to (3) legs too thin and too close together,
feet too small; (3) to (4) the hips grew a ledge; (5) to (9) the clothed look: the coat stood too far off, its skirt
added (the sheet's coat reaches the thigh) and drawn in, the trousers slimmed to the sheet's (narrower than his bare
legs: the skin under them is hidden). Worst remaining difference: about 2 to 2.5 % of his height (3 to 4 cm in the
game), at the hips of the clothed look (the coat's skirt) and the outside of the thighs; the bare body is within
about 2 % everywhere but the cap and beard of the mask head, which the painted head replaces.

### Three looks: `TitleFigures.wear(captain, "open" | "closed" | "boxers")`

His glb holds one body cut into the pieces each look leaves bare, and clothes over it; meshes are named
`<part>__<looks>`: `captain_skin__boxers`, `captain_forearms__open_boxers`, `captain_neck__open_boxers`,
`captain_scoop__open_boxers` (the chest in the undershirt's low neck), `captain_chesthair__open_boxers`,
`captain_bellyhair__boxers`, `captain_shorts__boxers`, `captain_legs__open_closed` (oilskins and boots),
`captain_outfit__open`, `captain_outfit__closed`. The covered skin is not drawn, so nothing pokes through. "open" is
the default.

- **Boxers** (his base body): loose white shorts with red hearts (a picture, `tools/art_src/captain_boxers.png`,
  repeated round him), a plain waistband, the same modest fullness at the fly.
- **Body hair:** a tufted grey bush on his chest and a trail down his belly (the hair shader, as the boy's hair);
  the light fuzz on his forearms, legs and back is painted on his skin.
- **Tattoos,** painted on his skin's picture (`tools/art_src/captain_skin.png`, laid on by region: arms, legs, front,
  back): forearms (an anchor, swallows, a compass star, a ship on a ribbon, a heart), upper arms (a ship; a heart and
  a swallow), his chest (an anchor), a swallow by his right shoulder, and across his back a ship, swallows, a heart and
  a compass star. No letters.
- **Open:** the coat now hugs him and has a skirt to the thigh (a laid sheet round him, open in front); the
  undershirt, braces, rolls as before.
- **Closed:** the gansey as before, on the new body. (It is not yet rebuilt to the new closed sheet: see below.)

### The painted face (the test): `TitleFigures.face(captain, "painted" | "mask")`

- **Method,** as games of that era did it: a low-poly head built to the head turnaround's own silhouettes (rings row
  by row, as wide as the front view and as deep as the side view: the cap, the head, the beard as one mass, the neck;
  the nose lofted down the side view's profile; ears; the cap's peak; a gold hoop where the sheet has it), 1,860
  triangles with its earring, one UV island set (Blender's smart projection), and one 512-square picture painted by
  projecting the turnaround's front, side and back views onto it, each texel taking the view it faces most squarely
  (and only where that view shows him, not its background), blended, the gaps between islands filled out. All in the
  build script (`painted_head`, `paint_face`, `silhouette`), from crops it makes itself
  (`tools/art_src/captain_face_front.png`, `_side`, `_back`); the result is `captain_face_painted.png`. No hand
  touch-up. Eyes, brows, wrinkles, cheeks and lips are paint, not geometry.
- **How it is drawn:** a StandardMaterial3D (the glTF's own) with its picture, set unlit by TitleFigures. Lit again
  by the scene, the painting's own light and shade went dark and muddy (seen side by side); unlit, it sits as the
  panel's baked paint does. No new shader program. Claude's pick.
- **The mask face** (the smooth mask with slits for eyes, its cap and pipe) is kept as the other face; the painted
  head brings its own cap (painted, badge and buttons included) and has no pipe (the head sheet has none).
- **Judged at the game's distances** (a picture of the three beside the concept): close up it holds well from the
  front and the side (the eyes, brows, wrinkles, nose and beard read as the painting); waist-up at a third of a
  1280 by 720 screen it reads as the concept; from the title's camera he is a few pixels in the wheelhouse window and
  either face would do. Where it falls short: the ears are rough boxes painted from the side view; the nose's sides
  catch a little background colour; the beard meets the neck in a hard line where the body's neck piece starts; the
  back of the cap is plain; the picture's 512 pixels go soft at full-screen close-ups; the face does not take the
  scene's light (it is unlit).

### At the wheel

He stands on a low oak grating, 12 cm, part of his model (not skinned) at his origin: the wheel stays where the boat
has it, and he is now short enough that he would otherwise reach up to it. His hands are on the rim to within 5 and
3 mm (the solve's own measure) over the run. No point of either coat (hands apart) comes within 2 cm of the wheel's
disc; the nearest is 4.2 cm (open) and 2.9 cm (closed) in model units (6 and 4 cm in the game). From the title's
camera his cap and face show through the wheelhouse's window. `scripts/title_figures.gd`'s wheel numbers are
unchanged.

### Checks

- Triangles drawn, with the painted head (1,860) and the grating (160): open 10,124, closed 5,818, boxers 8,677
  (his old closed look was 7,069). His glb holds all three looks and both faces: 20,970 in all.
- Winding against normals, every mesh of his glb: 98.9 to 100 %.
- Clipping at the wheel, the pose taken from the running title: forearm skin through the rolls 3 of 137 (up to 9 mm),
  undershirt through the coat 30 of 644 (up to 11 mm, at the shoulders by the neck), braces' edges dip up to 8 mm.
- The boy's and the diver's glb files came out byte for byte the same.

### Not done (asked for, still to do)

- The closed look rebuilt to `concept_captain_closed.jpg` (a buttoned double-breasted pea coat, collar up, over the
  gansey) and overlaid on it.
- His hands to `concept_captain_hands_wheel.jpg` (they are the man's hands, 1.15 times bigger), and his stance at the
  wheel compared with its side and three-quarter views.
- Views still wanted from the image generator: a true T-pose (arms level), for the arms' length and shoulders.

### Whose calls

The user's: the T-pose sheet as the measure, the overlay method, the boxers base body, the painted-face test, more
views when needed. Claude's: the bone table's numbers, the grating, the coat's skirt, trousers slimmer than his legs,
the painted face drawn unlit, the painted head with its own cap and no pipe, the earring in both faces, the tattoos'
places where the sheet was unclear.

## The captain: painted body, planned UVs, hair-shader beard, movable tattoos (2026-11-18, in progress)

The user, in order: "make sure things have textures that fit our art style"; "Dont try to model the beard it should
be made with a hair shader"; "the tattoos need to be moveable so we can postion them eventually"; "instead of
projecting hte concept art onto it we should make proper uvs no?"; "I downloaded some more references models for you
to compare to".

### Planned UVs (decision)

- **What:** every piece of the captain is unwrapped by plan in the build script (`plan_uvs`), not by Blender's smart
  projection: each face goes to a named part by where it is (arms, hands, legs, front, back; on the painted head the
  face, the round of the head and cap, the cap's top); each part is unwrapped by the projection that suits it (a strip
  round each arm with its seam underneath; a strip round each leg with its seam on the inside; flat front and back
  panels meeting at the sides under the arms; the face flat from the front; the head and cap a strip with its seam down
  the back), at true scale times its share of texels (face 3.2, hands 1.6, front 1.3, arms 1.0, back 0.8, legs 0.6),
  mirrored left onto right for the clothes (coat, undershirt, trousers and boots, boxers) but not for the bare skin, and
  shelf-packed into one atlas with padding. Beside each atlas the build writes a layout picture (every face's edges,
  each island named) and a JSON of where each part is: `tools/art_src/captain_<atlas>_layout.png` and `.json` for the
  atlases skin (1024), boxers (512), open (1024), legs (512), closed (1024), and `captain_face_layout.png` (1024). The
  face takes 442 by 384 pixels of its 1024 picture.
- **Why:** the user's call; smart projection gave a jumble of small islands nobody could paint on, and could not be
  mirrored. This is how the Twilight Princess figures on this machine are laid out (see the yardstick below).
- **Practice:** planned seams where they hide, limbs as strips, mirrored halves, texel density by importance (the
  usual game-character unwrap). **Alternative:** hand-unwrapping in Blender (better islands, not repeatable from the
  script).
- The sheets are still projected into this layout as the first paint (`paint_from_sheet`, in the sheet's pose), and
  what no view sees is filled from its neighbours.

### Painted body and clothes

The body and each look are painted from their sheets (base body from `concept_captain_tpose.jpg`, open from
`concept_captain_tpose_clothed.jpg`, closed from `concept_captain_closed.jpg`), drawn unlit like the head. The tufted
chest-hair mesh is dropped (`TUFTED_HAIR = False`): the sheet's painted chest and belly hair read better and match the
rest. The skin's projection is cleaned of the sheet's tattoos (ink is painted out from the skin round it), since the
tattoos are now an overlay.

### Movable tattoos

- Each tattoo is its own picture with a clear background: `textures/tattoos/anchor.png`, `swallow.png`, `star.png`,
  `heart.png`, `ship.png` (drawn by the build, faded blue-black, no letters). They live under `textures/`, not
  `tools/`, because `tools/` is hidden from Godot.
- The table is `textures/tattoos/captain_tattoos.json`: one row per placed tattoo. The build writes it only if it is
  missing, so edit it freely. Positions are in the part's own island: on an arm `x` runs round it (0.5 on top, more
  toward the front) and `y` from the shoulder (0) to the wrist (1); on `front` and `back`, `x` across and `y` up from
  his hips; `size` is the tattoo's width on his skin in metres; `turn` in degrees; `mirror`; `strength` 0 to 1. Parts:
  `arm_l`, `arm_r`, `hand_l`, `hand_r`, `front`, `back`, `leg_l`, `leg_r` (the islands of
  `textures/tattoos/captain_skin_layout.json`).
- Example row (an anchor on his right forearm): `{"picture": "anchor", "part": "arm_r", "x": 0.55, "y": 0.72,
  "size": 0.07, "turn": 0, "mirror": false, "strength": 0.85}`. To move it, change `x`/`y` and either rebuild (the
  build composites `textures/tattoos/captain_tattoo_overlay.png` in a second or two) or, in the game, call
  `TitleFigures.lay_tattoos(captain)` (it reads the table and composites the overlay once, about 30 ms).
- The overlay is drawn as a second, see-through copy of each bare piece (`*_ink*` meshes, StandardMaterial3D with
  alpha), 0.6 mm off the skin. No new shader program.
- The same scheme serves any figure: a skin picture, a table, an overlay.

### Beard as hair

The beard, moustache, sideburns and the hair under his cap are hair-shader hair (`head_hair`): flat card clumps
(`card_lock`) rooted over the head's own triangles in each region, combed down along the surface, with UV along each
clump. The head's lower part stays as the beard's core, painted a grey root shadow. 486 clumps, about 14,600 triangles,
on both faces. Brows stay paint (`BROW_TUFTS = False`): the painted brows read closer to the sheet.

### Still to do (this round is not finished)

- **The beard reads as white shingles, not a soft bushy beard:** too regular and too bright under the hair shader's
  ink edges, and heavy (about 14,600 triangles). It needs fewer, larger, softer cards with a strand texture, or the
  `sheen` style.
- **The closed coat does not match its sheet:** the sheet's pea coat is bulkier, its arms stand further out, its
  collar is higher, so its projected paint is misplaced. Its overlay is in the scratch folder.
- The coat's lapels are not yet brought in to the open sheet.
- The waist-up framing has not been matched to the concept's camera.
- Hands to the hands sheet and the stance against the wheel views are not done.
- The triangle budget (4,000 to 5,000 a look) is not done: the glb holds 56,647 triangles across all looks, both faces
  and both beards. Drawn per look, without the beard, it is about 10,000.
- Picture weight: the captain's glb is 3.4 MB (JPEG pictures inside); the source PNGs in `tools/art_src` and
  `textures/tattoos` are about 10 MB, unused by the game except the tattoo pictures and their table.

### The Twilight Princess yardstick (measured only, nothing copied)

Measured in Blender from the user's references in the session's scratch folder (`tp_refs`):

| Figure | Triangles | Main body picture | Mirrored share of body texels |
| --- | --- | --- | --- |
| Shad | 2,663 (head 653, torso 1,058, legs 514, arms 438) | 512 by 512, itself a 256 square mirrored four ways | 77 % |
| Telma | 2,308 (head 468, torso 972, legs 442, arms 426) | 256 by 256 | 93 % |
| Hylian Knight | 2,533 (head 614, torso 572, legs 741, arms 606) | 512 by 256 | 83 % (armour pieces 100 %) |

What they show: about 2,300 to 2,700 triangles a figure; one small body picture, mostly mirrored; the face and eyes
on their own small tiles (32 to 128 pixels); folds, seams and trim painted in, not modelled. The captain draws about
10,000 triangles a look without his beard: about four times that.
