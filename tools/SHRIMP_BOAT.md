# Shrimp boat

The boat of the title screen, also used as it is for the two trawlers seen from under water (`scripts/fishers.gd`).
What the user said (2026-11-18):
- "the main menu / start of the game should be the boy from warren, a sea captain, and and oldtimy diver on a
  shrimping boat (look up reference pics)". In the open back cabin there should be "a old timey franketstein
  computer hooked up to a helmet on the boys head".
- After seeing it: "The boat should be perpendicular in the start scene, and the pc against the portside wall",
  "And hooked up to a monitor".
- "spend more time coming up with a design ... for the boat as well and do a couple qualitu passes".
- "The captain needs to be driving the boat(which should be moving), the boy sitting on a stool plugged into the vr
  head set, and the diver operating machinery in the back".
- "the boat needs a quality pass, theres som clipping and nonsense geometry, the captions room shouldnt havea
  cutout for example, and the masts and fishing euipment need to make sense".

Only the boat is here. The figures, the computer, the monitor and the helmet are made elsewhere.

- Built by `tools/build_shrimp_boat.py` (Blender 4.3: `blender --background --factory-startup --python
  tools/build_shrimp_boat.py`). It writes `tools/blend/shrimp_boat.blend` (editable) and `models/shrimp_boat.glb`,
  and prints the inside-out and clipping checks. Run `godot --headless --path . --import` afterwards.

## Design sheet

**What it is.** An old wooden Gulf of Mexico double-rigged shrimp trawler, of the 1950s-70s kind out of Bayou La
Batre or the Carolinas. The house is forward and the working deck aft. It is old and salty and kept going by hand,
but it is not a wreck. In the title it is **under way** at a few knots:
- the anchor is stowed on the foredeck;
- there are no mooring lines;
- the trawl doors are up at the outrigger ends and the nets are lashed along the outriggers;
- the tyre fenders stay hanging (my call).

**The broadside silhouette.** The title shows the boat from starboard, abeam, with the bow to the right:
- **Sheer:** low and flat over the working deck aft, sweeping up to a high, flared bow and a tall stem head.
- **Stern:** a raked stem, a flat transom, and a short rudder and propeller.
- **Wheelhouse:** a proper closed room forward of amidships, a step higher than the open cabin behind it.
  - Framed, glazed windows go right round at standing height: three across the front and a row along each side.
  - In the aft half of the starboard side is a door. It stands open, folded forward flat against the house side and
    hooked there.
  - A flat roof with teal trim, a brow over the front windows, and running lights at the front corners.
  - On the roof: a searchlight, a horn and a whip aerial.
- **Open cabin:** behind the wheelhouse, open to the camera, with a dark board wall to port.
- **Stack:** black, with a slanted top, standing up through the cabin roof.
- **Mast:** one bare wooden mast just abaft the cabin.
- **Outriggers:** two, raised 65 degrees in a V, each with its net lashed along it and its pair of trawl doors hung
  at its end.
- **Boom:** a cargo boom swung aft over the working deck.

**Palette:** weathered white, a dull teal stripe and rubbing strake, red-brown bottom paint, warm grey-brown deck
planks and spars, dark bottle-green nets with orange floats, rust, black for the stack and tyres, and brass for small
fittings.

**Hull:** lapped strakes (clinker), each plank's lower edge standing 3 cm proud of the one below. There is one seam
in the bulwark and four between the deck and the boot top. Two teal bands: one at the sheer under the rail cap, and
one strake low on the side ending in a rubbing strake.

**Wear and repair:**
- Thin rust runs below some scuppers, the cleats and the hawse, fading to a pale rust.
- One plank renewed and left in red-lead primer.
- Blank name boards on the bows and the transom.
- Planks of different tints, with stains and a few new ones.
- Rust under the house's sills and roof, and a run down one trawl door.

**Deck furniture:**
- The trawl winch just abaft the mast.
- The diver's two-cylinder air pump a little to port of the middle, its big crank wheel seen face on from
  starboard, with its hose coiled by it.
- The fish-hold hatch aft of the pump.
- A coil of rope, crates and baskets aft.
- The anchor on the foredeck and a life ring on the starboard bow.

## The rig as built

The rig follows the usual Gulf double-rigger, simply: one mast with outriggers pivoting on it, topping lifts and fore
and aft guys, a trawl winch abaft the house whose cables lead through heel blocks and out to towing blocks at the
outrigger ends, and the doors hung there when the gear is up. Sources: NOAA Fishery Leaflet 470 (1958) Fig. 1, and
Oregon Sea Grant g03007.

The mast is spar-wood, stepped through the deck at Blender y -1.62 (Godot z +1.62), just abaft the open cabin. It
rises to 9.5 m. On it:
- a steel step at the deck;
- the outrigger pivot collar at 3.65 m, with a pin each side;
- two heel blocks hung on straps aft of the collar;
- cleats for the lazy lines;
- the boom's gooseneck at 4.1 m;
- a crosstree at 7.6 m;
- a forestay tang;
- the masthead crane with three eyes (two for the outriggers, one aft for the boom);
- a cap and the masthead light.

| Line | From | To |
| --- | --- | --- |
| Forestay (wire) | tang at the masthead | stem head |
| Backstays, 2 (wire) | masthead | padeyes on the rail at the quarters (y -6.27) |
| Shrouds, 2 (wire, with turnbuckles) | crosstree ends | padeyes on the rail just aft of the mast (y -2.05) |
| Outrigger topping lifts, 2 (rope) | eye on each outrigger's end band | the masthead crane's side eyes |
| Fore guys, 2 (rope) | outrigger end eye | padeyes on the bow rail (y 4.6) |
| Aft guys, 2 (rope) | outrigger end eye | padeyes on the quarter rail (y -5.6) |
| Trawl cable leads, 2 (wire) | top of each side's winch drum | that side's heel block |
| Trawl cables, 2 (wire) | heel block, along the outrigger's underside | towing block at the outrigger's end |
| Trawl cable falls, 2 (wire) | towing block | a ring |
| Door bridles, 4 per side (chain) | the ring | the tops of that side's two trawl doors |
| Lazy lines, 2 (rope) | cod end at the bundle's heel | cleat on the mast |
| Net lashings, 4 per side (rope loops) | round outrigger and net bundle | (closed loops) |
| Boom topping lift (rope) | masthead crane's aft eye | eye on the boom's end band |
| Boom block strop | boom end band | boom block |
| Whip (rope) | boom block | hook |
| Whip hauling part (rope) | boom block, along the boom's side | cleat near the boom's heel |

- **Outriggers:** each is a spar-wood pole 6.5 m long raised 65 degrees. Its heel has a steel jaw and ferrule on the
  collar's pin. Its end has a steel band with an eye on top and a towing block hung under it.
- **Trawl doors:** two per side, hung below the towing block in the travelling ("doors up") position. Each is a
  wooden otter board with a steel shoe and braces.
- **Nets:** each is bundled along the forward side of its outrigger and lashed at four points, sagging between them.
  Floats run along the headrope. The cod end, with chafing gear, is at the heel and made fast to the mast by the lazy
  line.
- **Trawl winch:** on the middle line just abaft the mast. A drum each side for the trawl cables, a narrow middle drum
  for the try net, a gearbox and a warping head each end.

Every line starts and ends on a fitting. The build checks this (LINE ENDS below).

**The outriggers' origins changed.** The rig moved from the wheelhouse to abaft the cabin, so the `OutriggerPort` and
`OutriggerStarboard` origins (their pivots) moved too, to Godot (±0.42, 3.65, +1.62); they were at (±0.42, 3.65,
-1.85). Neither `title.gd` nor `fishers.gd` refers to these two nodes. The Wheel, PumpWheel, all markers and the axes
are unchanged.

## The mind machine's aerial (2026-11-18)

The user: "their boat needs an antenna sticking off the bottom from the vr machine". The panel concept
(`tools/art_src/panel_concept_1.png`) sets the style: brass, copper and iron.

- **On deck:** a junction box on the cabin's forward wall, beside the console's forward end, at Godot about
  (-1.1, 1.2..1.4, -1.55). The main session's cable from the console can run to it. A heavy rubber cable runs from the
  box across the deck to a brass deck gland at Godot (-0.9, 0.92, -1.46), clear of the console's 2.3 m and of the pipe.
- **Under the hull:** a brass through-hull flange and an iron housing, 0.35 m to port of the keel under the cabin's
  forward end (Godot (-0.35, -0.8, -1.45)). From them hangs an iron mast, a little crooked, carrying:
  - three brass struts to a collar;
  - three pale insulator discs;
  - a copper coil of three turns;
  - a brass loop;
  - a brass tip ball.
- **Marker:** `Aerial` (Node3D) sits at the tip ball, at Godot (-0.436, -2.731, -1.414). It reaches about 1.9 m below
  the hull's bottom.
- **Clearance:** it is far from the propeller and rudder (5.5 m forward of them) and 0.35 m to port of the keel.
- **Cost:** about 750 triangles in all, about 560 of them the aerial itself.
- **Checks:** clipping check zeros; inside-out 0.
- Its deliberate set-ins are listed in `SET_INTO`.

## Axes, size and nodes

The origin is on the centre line amidships at the waterline. In Godot the bow points to **-Z** and starboard is +X.
Overall, in Godot: x -3.52..3.52, y -2.80 (the aerial's tip; the keel is at -0.99) to 9.69 (masthead light), z -6.62 (stem head) to 6.55. The hull is
13 m by 4.2 m and modelled down to the keel.

| Node | Kind | Triangles | What it is |
| --- | --- | --- | --- |
| `Boat` | MeshInstance3D | 16,419 | everything fixed |
| `Wheel` | MeshInstance3D | 824 | the ship's wheel (rim radius 0.3 m), hub at Godot (0, 2.016, -3.2): 1.05 m above the deck under CaptainSpot and 0.45 m ahead of it; turns about its local Z |
| `PumpWheel` | MeshInstance3D | 520 | the air pump's crank wheel (radius 0.35 m), hub at Godot (-0.2, 1.879, 3.5): 1.0 m above the deck under DiverSpot and 0.5 m aft of it; turns about its local X; handle at radius 0.22 m at the top when unturned |
| `OutriggerPort` | MeshInstance3D | 1,938 | pivot at (-0.42, 3.65, 1.62): pole, fittings, its lines, two doors and the lashed net |
| `OutriggerStarboard` | MeshInstance3D | 1,938 | the same at (0.42, 3.65, 1.62) |

The total is **21,639 triangles**. The outriggers turn about their local Z; their lines are right only at the built
angle.

**Markers** (Node3D; each marker's -Z is the way it faces). All are unchanged except the new `Aerial`.

| Marker | Godot position | Faces |
| --- | --- | --- |
| `ConsoleSpot` | (-1.37, 0.924, -0.175) | starboard |
| `BoySpot` | (-0.15, 0.924, -0.175) | port (his stool; the deck there is clear) |
| `HelmetCable` | (-1.37, 2.224, -0.175) | starboard |
| `MonitorSpot` | (-1.37, 2.674, -0.175) | starboard |
| `CaptainSpot` | (0, 0.966, -2.75) | the bow |
| `DiverSpot` | (-0.2, 0.879, 3.0) | aft |
| `BowWave` | (0, 0, -5.115) | aft |
| `Wake` | (0, 0, 6.5) | aft |
| `Aerial` | (-0.436, -2.731, -1.414) | the bow (no meaning; the aerial's tip ball, for a spark or pulse) |
| `Waterline` | (0, 0, 0) | the bow |

**The cabin inside** is 2.85 m fore and aft and 2.74 m from the port wall to the open starboard edge, with 2.13 to
2.16 m headroom. The port wall is lined with dark boards. Pipes rise at both ends of the wall (clear of the
console's 2.3 m) and run under the roof.

## Materials and colours

Plain named colours with no image textures:

`basket`, `bottom_red`, `brass`, `cabin_wood`, `crate_wood`, `deck_wood`, `door_wood`, `float_orange`, `glass`,
`hose_rubber`, `hull_stripe`, `hull_white`, `lamp_glass`, `lamp_green`, `life_red`, `mast_white`, `metal_dark`,
`metal_rust`, `copper`, `name_board`, `net_green`, `primer_red`, `roof`, `rope`, `rust`, `spar_wood`, `trim`, `wire`.

- `glass` is pale and only lightly tinted, with alpha 0.22, exported as BLEND.
- Every part is a closed solid.
- Vertex colours (attribute `Col`, exported as COLOR_0) multiply the material colour.
- Godot leaves `vertex_color_use_as_albedo` off on each mesh's first surface. Those first surfaces are `basket` and
  `door_wood`, whose vertex colours are white.

## The clipping check (in the build script)

Each run of the build tests every part against every other, in place, across all five objects:
- It compares bounding boxes first, then tests triangle overlap with a BVH.
- For pairs whose faces cross, it measures how deep each part's corners sit inside the other. It uses a ray-parity
  inside test, then the distance to the surface.
- A pair deeper than 4 mm is printed as **CLIP**, unless it is in `SET_INTO`. That list holds the parts meant to be
  set into one another, each with its reason: walls through the deck, posts into roofs, a pin through a jaw, a
  lashing drawn into a net, a line's eye in a fitting.

It also prints:
- **ZFIGHT:** coincident faces turned the same way.
- **FLOATING:** parts touching nothing.
- **NOT JOINED TO THE HULL:** parts not connected to the hull through what they touch.
- **LINE ENDS:** line ends made fast to nothing within 3 cm.

| Check | First run | Final run |
| --- | --- | --- |
| Parts checked | 653 | 651 |
| Pairs with touching boxes | 2,237 | 2,216 |
| Pairs whose faces cross | 1,352 | 1,322 |
| Set in on purpose, deeper than 4 mm | 630 | 737 |
| **CLIP pairs not meant** | **123** | **0** |
| ZFIGHT | 17 | 0 |
| FLOATING | 4 | 0 |
| NOT JOINED TO THE HULL | 13 | 0 |
| LINE ENDS made fast to nothing | 3 (once the test was limited to lines) | 0 |

Real faults it found, and their fixes:
- **Propeller in the hull** (25 cm deep): its upper blade was inside the hull's bottom. It is now smaller and lower,
  between skeg and rudder above the shoe, with no blade straight up.
- **Life ring** (5 cm into the planking and through the rub rail): it now hangs below the rub rail and clear of the
  laps.
- **Tyres** (2 cm into the hull): moved out.
- **Pipe clip in the cabin's aft post:** the pipe moved forward.
- **Backstay padeyes on the stern cleats:** moved aft.
- **Trawl cable through the net lashings and the block strap:** it now runs along the outrigger's underside, from
  heel block to towing block.
- **Floats through lashings:** floats are kept off the lashing points.
- **Pump shaft and crank wheel in the air:** they stood above the pump chest, so the chest was raised.
- **Rope coil turns not touching:** closed up.
- **Two propeller blades not touching the hub:** fixed.
- **Rust run slabs with coincident back faces:** offset.
- **Ring lanyard and tyre ropes ending in the air:** led over the rail.

## Quality pass (2026-11-18, the user's "clipping and nonsense geometry" pass)

**What was wrong:**
- The wheelhouse had a door-high hole cut in its side (from the concept-art pass): no glass, no door.
- There were two masts. The main mast stood inside the wheelhouse, and the mizzen carried only the boom.
- The outriggers' lines went nowhere sensible:
  - topping lifts ended at the mast's side;
  - guys ended in the air above the rail;
  - one trawl door hung against the hull and one hung in mid-air from the middle of a pole.
- Nets hung as bags from the outrigger tips. The swag net hung from the boom to the rail.
- There was no trawl cable, no towing block and no heel block. The winch led nowhere.
- Clipping and floating parts, as listed above.

**What changed:**
- The wheelhouse is a closed room with framed, glazed windows round it and a real door standing open.
- There is one rig on one mast abaft the house, as in the table above. The nets are lashed along the outriggers, the
  doors hang at the towing blocks, and the winch's cables lead to them.
- The mizzen and the swag net are gone. The winch moved to just abaft the mast.

**Pass 1** (title camera at Godot (10.5, 3, 0.4), both quarters, bow-on, stern-on, above, below, and close on the
wheelhouse door, the outrigger pivot, the masthead, an outrigger's end with its doors, and the winch):
- The captain reads through the open doorway; the wheel and his stand-in show through the door's window.
- The rig reads: topping lifts to the crane, guys forward and aft to padeyes, doors hanging in pairs on bridles
  under the towing blocks, the cables down from them, and the winch cables up to the heel blocks.
- Found: the net bundles' heel ends closed in a flat disc, which read as cups; the square heel ferrule let the round
  pole poke through its faces, so it looked like strips along the pole.
- Fixed: the bundle ends close in over three rings, and the ferrule is round.

**Pass 2** (the same views):
- The ferrules and bundle ends look right.
- The glass was made paler and more see-through (alpha 0.22).
- The title view shows the diver at the pump, the winch and mast, the cabin with the boy at the console, the open
  door, and the captain through the doorway and windows.
- The fore guy crosses in front of the wheelhouse's forward windows (not the captain) as seen from abeam. A real fore
  guy leads there, so it stays.

## Earlier passes, in short

- **First build (camera aft):** the raked stem pushed the outer skin inside the bulwarks; fixed by raking the stem
  below the deck only.
- **Broadside rework:** rust, primer and the bottom paint were reworked. The cabin was opened to starboard and walled
  to port.
- **Moving title:** the helm, pump, stool place and foam markers were added.
- **Concept-art passes** (`tools/art_src/concept_boat.jpg`): clinker planking, two teal bands, the stem head, teal
  roof trims, the dark board cabin wall with pipes, the slanted stack and a muted palette. What the concept has that
  the model still lacks:
  - a stubbier hull with a higher freeboard aft;
  - nets in wide swags;
  - a single roofline;
  - heavier rust.

## Checked

- Inside-out faces in Blender, part by part: 0 of 21,639 face inwards across 671 parts.
- The clipping check above is all zeros.
- In Godot after `--import`, read back from the .glb:
  - winding agrees with the normals on 100% of triangles in all 5 meshes, and each mesh encloses a positive volume;
  - node names are as listed;
  - the markers sit and face as listed;
  - COLOR_0 is on every surface.

## Not verified

- Never seen in the game, on the water, under the game's light or post shader, or on a phone (20.9k triangles and
  blended glass).
- The real figures, console, monitor and helmet have not stood at the markers; only boxes and cylinders have.
- A small dip shows in the keel line near the forefoot from below. It is not fixed.
- The clipping check proves contact and depth, not good looks. Some set-in pairs (posts into roofs and so on) are
  allowed by name pattern, so a wrong one with the same names would pass.

## Whose calls

The user's: a shrimping boat; an open back cabin with the computer; the boy, captain and diver on it; the boat
broadside in the title; the computer against the port wall with a monitor; design and quality passes; the captain
driving with the boat under way; the boy on a stool; the diver at machinery; no cutout in the captain's room; masts
and fishing gear that make sense.

The main session's brief: the size, the layout, the marker names and places, the camera places, the cabin's size,
the door in the wheelhouse's aft half hooked back flat, windows round the house, one mast properly stayed, the
outriggers, winch, doors-up position and lashed nets, the clipping check, the axes and the budget.

Mine (change freely):
- Design:
  - the design sheet;
  - the mast just abaft the open cabin rather than through the wheelhouse;
  - the door folding forward over a window that lines up with its own;
  - the winch drums and the try-net drum.
- Rigging layout:
  - where the padeyes are;
  - the heel blocks aft of the collar;
  - the cables along the outriggers' undersides;
  - the nets lashed forward of the outriggers;
  - the lazy lines to the mast;
  - the boom's whip led to a cleat on the boom.
- Deck and wear:
  - the stowed anchor;
  - the tyres left hanging;
  - the hatch and the deck furniture's places.

Sources (shape and rig only):
- NOAA Fishery Leaflet 470 (https://spo.nmfs.noaa.gov/sites/default/files/legacy-pdfs/leaflet470.pdf).
- Oregon Sea Grant g03007 (https://seagrant.oregonstate.edu/sites/seagrant.oregonstate.edu/files/sgpubs/onlinepubs/g03007.pdf).
- Louisiana Sea Grant, "Shrimping Vessels History" (https://www.laseagrant.org/wp-content/uploads/ShrimpingVessels-History.pdf).
