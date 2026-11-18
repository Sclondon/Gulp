# Pirate wreck

A location of the sea. The user (2026-11-18): "and another location should be pirate ship wreck". The map is made
by another session: it puts this node in a sandy hollow by `PirateWreck.new()`, a position, `rotation.y`,
`add_child`. The liner wreck (tools/WRECK.md) and the ruins of Atlantis are other agents' places: this one is meant
to be small, wooden, sunlit, a treasure wreck.

- Built by `tools/build_pirate_wreck.py` (Blender 4.3, `blender -b --factory-startup --python
  tools/build_pirate_wreck.py [-- --no-bake]`). Writes `tools/blend/pirate_wreck.blend` (editable),
  `models/pirate_wreck.glb`, `models/pirate_wreck.json` (the collision spheres, the swim routes' check points and the
  test's camera views) and `textures/pirate_atlas.png`. Then `godot --headless --path . --import`.
- Drawn by `scripts/pirate_wreck.gd` (`class_name PirateWreck`) with `shaders/pirate_wreck.gdshader`.
- Pictures: `tests/pirate_view.gd` (see the end of this file).

## Reference (looked at for shape and scale only)

- Whydah Gally (Sam Bellamy's, lost off Cape Cod 1717): a three-masted ship-rigged galley of about 300 tons, about
  100 ft (30 m) long, 18 guns as built and 28 as a pirate ship (Wikipedia and the Whydah museum's figures).
- Queen Anne's Revenge (Blackbeard's, lost at Beaufort Inlet 1718): a French-built ship of about 200 tons and up to 40
  guns. The wreck site (31CR314) is a low mound about 25 x 15 ft at its core: a ballast pile with cannon, anchors,
  cask hoops, rigging iron and a cluster of shot; part of the keel and the stern post survive (qaronline.org field
  summaries; Carleton College shipwreck pages).
- A small English sixth rate of about 1700 (20-24 guns): about 100 ft on the gun deck, 28 ft of beam, about 9 ft
  in the hold, one gun deck, a raised quarterdeck with the great cabin under it, a small forecastle, a beakhead with a
  figurehead, a flat transom with a row of stern windows and carved work above them, quarter galleries.
- How wooden wrecks really lie: a ship that settles upright on sand heels over onto her bilge (here to starboard),
  sand fills her and builds a scour mound against the low side and the stern; masts break at the deck and fall over
  the low side with their rigging; guns break their breechings and slide to the low side; above the sand, shipworm
  and rot strip the planking first and leave the frames (ribs) standing. In warm water a real wreck of 1700 is long
  gone but for the ballast mound and the iron; this one is a storybook wreck, much better kept than any real one
  (Claude's call: the brief asks for a ship you can swim through).

## What she is (the design)

An original small frigate of about 1700, taken by pirates: three masts, square rigged, one gun deck of nine ports a
side, a raised quarterdeck and forecastle, a flat stern with a gallery of windows. Her real size would be about
30 m on deck and 8.5 m of beam; the game's is about **36 m on deck (39 m with the beakhead) and 10.6 m of beam**, and
her decks are stretched far taller than a real ship's (2.7 m clear between decks instead of about 1.7 m) so that
a 2.2 x 1.8 m swim route fits through every space it must.

**How she lies.** On the sand, heeled 20 degrees to starboard, her bow lifted 6.5 degrees on a rock under her
forefoot, her stern sunk about 2 m into the sand with a drift of sand banked against her starboard side and stern.
Her back is not broken. Model axes (Godot): the origin is the middle of the keel's resting line, y = 0 at the sand,
**the bow points to -Z**, starboard is +X (the low side), port is -X (the high side, which faces up and out).

**The silhouette** (it must read as a pirate ship at a glance and at phone size):
- the high stern: the transom with a gallery of windows (the middle three broken out into one hole), a balcony
  ledge with balusters under them, carved work above (a scallop fan between scrolls, pilasters, an arched crest), a
  quarter gallery on each corner, the big stern lantern on the crest;
- the step of the quarterdeck and forecastle above the low waist;
- the beakhead with the head rails and a mermaid figurehead (after the concept art: her tail curled down the knee,
  arms crossed, hair down her back, weathered pale stone-green), the bowsprit up from it;
- the foremast still standing but sprung (leaning a further 8 degrees to starboard), with its top, a yard cock-
  billed across it hung with shreds of sail; the mizzen standing too, shorter, with its yard, rags and the rag of a
  black flag (a skull and crossed bones, the generic sign) on the stump of its topmast;
- the mainmast broken at the deck and lying over the starboard rail into the sand as a ramp of spar, top and yard,
  with its shrouds draped from the hull to the masthead and loose ropes hanging;
- the dark tarred hull below the lower wale, the bleached grey-brown timber above it, two wales along the side;
- ribs showing where planking has gone (a big patch at the hold on the port side, a smaller one at the gun deck aft);
- the anchor's cable from the port hawse hole over the sand to the anchor; barrels, chests and shot on the sand.

**Inside** (her interiors are thick-walled solids: the camera goes in):
- the great cabin under the quarterdeck, 2.4 m clear, its stern windows broken out; a small chest of coins;
- the waist, open to the sky, with a grating, and a wide hole where the deck has fallen in onto the gun deck;
- the gun deck, 2.7 m clear, the length of the ship: guns at their ports on both sides (two of the port guns have
  slid down to starboard), a lantern on a beam, the mainmast through it;
- the forward hold, 2.5 m clear, under a hatch in the gun deck; one gun has fallen through the gun deck into it;
  **the treasure**: a heap of gold coins with a crown on it, two open chests, goblets, ingots, loose coins, a lantern;
  the aft hold is full of sand (solid);
- the hold's port side has lost its planking: ribs, and a wide gap where two ribs have gone.

## Swim routes (main: at least 2.2 m wide and 1.8 m high in the ship's own frame)

1. **Stern**: in through the broken stern windows (2.8 x 2.2 m), through the great cabin, out of its doorway
   (2.8 x 2.25 m) into the waist, then
2. **down** the fallen deck (a hole about 6 x 6.5 m) into the gun deck and **along it** past the mainmast to the
   main hatch, then
3. **down** the hatch (3 x 3 m) into the hold, past the treasure and **out** through the gap in the port side
   (3.2 m between ribs, 2.25 m high).
4. **Under the bow**: athwartships under the lifted forefoot and beakhead, ahead of the rock.
5. **Through the fallen rigging**: along the starboard side between the hull and the fallen mainmast, under the
   mast, its shrouds overhead and loose ropes hanging either side.
Small fish also get: the gun ports (0.65 x 0.65 m), the gaps between ribs (0.6 to 0.8 m), the two side windows of
the stern gallery (0.6 x 1.4 m).

## Palette

Bleached and weedy grey-brown timber above the lower wale (plank seams baked in), dark tarred hull below it, dull
dark brown inside, silted deck planks, rusted iron (hoops, anchor, lanterns, shot), verdigris bronze guns, faded red
and old gilt on the carving, grey-brown rope and sail rags, a black flag with a bone-white skull, pale sand and
grey rock to sit in the game's sand. **Gold** is the one bright warm thing: emissive in the baked colour, and the
shader makes it glint.

## Budget

About 15,000 triangles in all, low-poly Twilight Princess style: big flat planes where the hull is plain, the
triangles spent on the outline (stern carving, figurehead, masts, the fallen rig, ribs), the detail in one baked
2048 atlas (`textures/pirate_atlas.png`). Objects: `PirateHull` (everything fixed, including what lies on the sand),
`PirateRig` (masts, spars, rigging, sails, flag: can be hidden or culled apart), `PirateTreasure` (drawn with the
gold's glint). Empties: `ReefSpot00`..`ReefSpot23` (+Y the surface normal, where sea life grows), `FishSpot00`..
`FishSpot07`, `TreasureSpot` (the middle of the hoard), `Lantern00`..`Lantern03` (stern, cabin, gun deck, hold).

## Whose calls

- The user's: that there is a pirate ship wreck location.
- The brief's (the main session's): a wooden three-master of about 1700 lying heeled, her parts, the routes and
  their sizes, the budget, the objects and empties, one shader, collision as `Sea.add_rock` spheres.
- The concept art's (the user asked for it): the mood, palette, two standing masts, the mermaid, where things lie.
- Claude's (change freely): the 1.2x scale and the stretched decks; 20 degrees of heel
  and 6.5 of pitch; the sprung foremast; which guns are where; the treasure's layout; the scallop and scroll
  carving; the colours; the sea life at the reef spots (tropical pieces of GameCommon's sea floor kit); the bake's
  lights; that the aft hold is full of sand.

## The concept art (arrived mid-build) and what changed for it

`tools/art_src/concept_pirate_wreck.jpg` (made at the user's request: "We need a concept are solution"). Built to it:
warm honey-brown timber with gilt trim (the upper wale, the carving) and a dark brown bottom (not grey and black);
**two standing masts with tattered sails and one fallen** (the mizzen now stands, with the black flag's rag, instead
of a stump; the foremast stands; the mainmast is the fallen one); a **mermaid** figurehead (the sea-dragon is
dropped); the anchor close under the bow on a taut chain; two lanterns on the stern's top corners; red port lids;
open rails on posts round the quarterdeck and forecastle; deadeyes on the channels; an open chest of gold spilled on
the sand below the breach; light rippling over what faces the sky (the shader). The swim routes, budget and files are
the brief's and stand.

Side by side (the concept, and `tests/pirate_view.gd`'s `concept_angle` shot, light fog):
- **Matches**: what is where (carved stern with its window gallery and quarter gallery to the left, a row of ports
  with lids and muzzles, a hole low in the side with ribs, bow and figurehead to the right, anchor at the bow,
  chests, barrels and shot on the sand); the palette of the timber and trim; the heel showing the deck; tattered
  sails; the light ripples.
- **Still differs**: the masts are far shorter (her highest point must stay under 15 m of water; the concept's are
  twice as tall); the fallen mast lies over the side into the sand (the brief's "through the fallen rigging" route),
  not across the forecastle; the game's water is deep blue and foggy where the concept's is bright turquoise (that is
  the sea's look, not the wreck's: `tint` can warm her); the sand is the game's, not white; no seaweed strands or
  octopus (sea life is only the reef pieces at her ReefSpots; the octopus is a creature for the main session); the
  hull is plainer (no broken plank ends round every opening, no gilt on the rails); the stern windows are fewer and
  bigger.

## Quality passes

**Pass 1** (first render, `shots_2`): the sand drift was a white slab with a hard edge, far brighter than the game's
sand and much bigger than her contact with it; the shader's light ripples also lay over the cabin and gun deck
floors; inside was bare cardboard (no beams) with hot spots from the bake's fill lights near the ceilings; the timber
was greyer than the concept; the mermaid was too small to read from the side; the sail rags were small; the gold heap
glowed as one blob; the stern lanterns were small; a barrel sponge on the bowsprit tip looked like a balloon; the
"above" picture was taken from above the water. **Fixed**: the drift made smaller (3 m of slope from her side) and
the colour of the game's sand under its light; a per-vertex "open sky" value (rays up from every point, kept as the
model's vertex colour) so the ripples fall only where the sky shows; deck beams under all three decks (290
triangles); fill lights lowered and dimmed (the hold now dark round its glowing gold); warmer timber and a less blue
`tint`; the mermaid half as big again; longer and more sail rags; gold's baked glow halved; stern lanterns 1.4x;
no barrel sponges in her sea life; the camera put under the surface.

**Pass 2** (`shots_3`): reads as a pirate ship from every side; the interiors read as decks of a ship (beams,
guns at their ports, slid guns, the fallen deck's light, the treasure's glow in a dark hold); the breach with its
ribs and the gold inside it shows from outside; the bow sits on its rock with the way under it clear. Remaining and
fixed: the drift was still paler than the sand (darkened again); two small hull faces at the forward end of the gun
deck's ceiling came out of the Booleans facing in (normals recalculated after the clean-up: they still count as
inward in Blender's ray test, but Godot's read-back finds 99.8% of the hull's triangles wound with their normals:
see Checks).

**Pass 3** (final, `final_light` and `final_game`): no new faults found; the comparison with the concept is above.

## Numbers

- **Triangles: 14,782** (PirateHull 11,870, PirateRig 1,704, PirateTreasure 1,208). The hull itself is 3,354; the
  guns about 1,300 with their carriages; the sea life drawn on her adds 24 pieces of the sea floor kit (low models
  for the heavy ones).
- **Texel density** (2048 atlas, 40% of it covered by islands): about 20 texels a metre on plain hull and decks
  (5 cm a texel), **29 on the stern carving** and the figurehead, **58 on the gold** (38 on the chests), 9 on the
  sand drift and 11 on rope.
- **Size**: 36 m on deck, 39 m with the beakhead, 10.6 m of beam; with what lies round her she spans x -10.7..22.7
  and z -25.4..24.1 (Godot), and stands **14.3 m** above the sand at most (the foremast's stump): she wants at least
  15.5 m of water over the sand.
- **Collision**: **705 spheres** (`models/pirate_wreck.json`); at most 302 in one of the sea's 8 m squares near her;
  `Sea.clear_of_rocks` there takes 15 to 33 us a call on this desktop (the rest of the sea's squares hold tens).
  Spheres reach at most 0.6 m into a space inside her, 1.2 m out into open sea, and never into a swim route's tube.
  Small trim (rails, lids, deadeyes, carving, lanterns, chests, coins, rope) does not stop a swimmer.

## Checks

- Blender, per part: every part a closed solid, a ray out of each face leaves its skin an even number of times
  (`inside_out`): 463 parts, 2 faces of 3,306 on the hull flagged (above).
- Godot, read back from the imported .glb (`tests/pirate_view.gd`): each triangle's winding against its normals and
  the volume enclosed: hull 99.8%, rig 100%, treasure 100%, all volumes positive: ok.
- Swim routes: 985 check points (each route's middle line every 0.4 m with 0.9 m of room, and 1.1 m either side
  and 0.88 m above and below it with none): 0 blocked by her spheres in Blender, 0 by `PirateWreck.routes_blocked()`,
  0 moved by `Sea.clear_of_rocks` in Godot; the solid mesh is at least 1.10 m from every route's middle line.
  `_ready` asserts the routes are clear of her own rocks.
- `sh tests/smoke.sh`: GULP SMOKE PASSED (one earlier run failed on the barracuda pack check, another session's
  work; the rerun passed).
- Not verified: a web build (the one shader's compile time in a browser, the 2048 atlas's VRAM there); a phone; the
  frame cost in the real map; how she sits in the map's hollow and beside its outcrop; the gun ports and rib gaps
  for small fish are open in the mesh and kept clear of spheres by the cutters, but no fish has been swum through.

## Pictures

`sh`: `godot --path . --audio-driver Dummy --resolution 1280x720 -s res://tests/pirate_view.gd -- --out=<dir>
[--fog=light]`; headless `-- --check` runs only the checks.
