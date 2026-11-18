# Shrimp boat

The boat of the title screen. The user (2026-11-18): the boy, a sea captain and an old-time diver "on a shrimping
boat (look up reference pics). In the open back cabin of the shrimping boat should be a old timey franketstein
computer hooked up to a helmet on the boys head"; then, after seeing it: "The boat should be perpendicular in the
start scene, and the pc against the portside wall", "And hooked up to a monitor"; and "spend more time coming up with
a design ... for the boat as well and do a couple qualitu passes"; then "The captain needs to be driving the boat(which
should be moving), the boy sitting on a stool plugged into the vr head set, and the diver operating machinery in the
back". Only the boat is here; the figures, the computer,
the monitor and the helmet are made elsewhere.

- Built by `tools/build_shrimp_boat.py` (Blender 4.3: `blender --background --factory-startup --python
  tools/build_shrimp_boat.py`). It writes `tools/blend/shrimp_boat.blend` (editable) and `models/shrimp_boat.glb`.
  Run `godot --headless --path . --import` afterwards.

## Design sheet

**What it is.** An old wooden Gulf of Mexico shrimp trawler of the 1950s-70s kind out of Bayou La Batre or the
Carolinas: a double-rigger, house forward, working deck aft. Old and salty, kept going by hand, not a wreck. In the
title it is **under way** at a few knots: the anchor is stowed on the foredeck, no mooring lines; the tyre fenders
stay hanging (many working boats leave them so: my call).

**The broadside silhouette** (the title shows the boat from starboard, abeam, so this is the whole picture), bow to
the right as the camera sees it:
- A strong **sheer**: low and flat over the working deck aft (0.45 m of bulwark above a deck 0.8 m above the water),
  sweeping up to a high, flared bow (deck 1.5 m, rail 2.3 m). This sweep is the first thing that says "workboat".
- A raked stem and a flat **transom** with a short rudder and propeller under it.
- The **wheelhouse** forward of amidships: a tall white box a step higher than the cabin behind it, with a brow over
  three front windows and two port side windows; to starboard (the camera's side) one big open window at standing
  height and the door standing open, hooked back aft, so the captain shows at the wheel; running lights at its front
  corners, a searchlight,
  a horn and a whip aerial on the roof, and a tall black **stack** behind it.
- The **open cabin** behind it, lower-roofed: from this side a lit box open to the camera, posts at its corners, a
  grab rail on its roof. The computer stands against its far (port) wall.
- The **mast** rising through the wheelhouse to 9.5 m, a crosstree, and the two **outriggers** raised 65 degrees in a
  V, with the green **nets** hung from their tips to dry, the floats on them, and the otter doors. This V of booms
  and hanging nets is the shrimp boat's signature: it must read even at phone size.
- A **boom** swung aft over the working deck with a block and hook.

**Reads at a glance and at phone size:** the sheer sweep, the white house forward, the V of outriggers with the two
dark nets, the dark stripe and red bottom paint, the black stack. Fine stuff (lines, tyres, rust) is only there for
the close-up.

**Palette** (small, warm and weathered, to sit with the rusted brass computer): weathered white (hull and house,
uneven from station to station, grimy at the foot of the house and above the waterline), a faded teal stripe under
a varnished brown rail cap, red-brown bottom paint showing 0.25 m above the water, warm grey-brown deck planks, dark
bottle-green nets with orange floats, rust brown, black for the stack, tyres and scupper slots, brass for small
fittings, red and white for the life ring. One spot of green (the starboard running light).

**Wear and repair** (character, kept calm):
- Rust weeping in thin runs from some scuppers, from the cleats and from the anchor at the bow: white paint tinted
  rust brown at the top, fading into the white (vertex colours on the white).
- A plank below the stripe renewed and left in red-lead primer.
- Blank name boards on both bows and across the transom (the name is left off on purpose).
- Old tyres hung as fenders on ropes from the starboard rail.
- The deck: planks of different weathered tints, oil and fish stains, one or two new pale planks put in.
- The wheelhouse door's varnish gone grey; a rust run down one otter door.

**Deck furniture**, placed so nothing stands between the camera and the cabin: the trawl winch on the middle line
aft of the cabin, the diver's air pump a little to port of the middle (an old two-cylinder pump in a wooden chest
with brass bands, two brass cylinders and a crosshead on its lid, a gauge, and a big crank wheel on its starboard side
seen face on by the camera) with its hose to a coil on deck and on to the diver's feet, a fish-hold hatch with battens
aft of it, a coil of rope to port, crates at the port quarter, shrimp baskets at the starboard quarter and one more to
port, the anchor lashed down on the foredeck, a life ring on the starboard bow bulwark, cleats on the rail.

**The starboard side is kept clear for the camera:** the cabin's starboard side is open from deck to roof; the
starboard otter door is hauled up high under its outrigger, beside the net (above the roof line as seen from abeam);
the starboard net is hauled up short; the starboard aft guy lands well aft of the cabin; the shrouds land forward of
the wheelhouse's open window and pass above the captain as seen from abeam. The port side keeps its door hung low against the hull and its net long.

## Axes, size and nodes

Origin on the centre line amidships at the waterline (y = 0 in Godot is the sea's surface). In Godot the bow points
to **-Z** and starboard is +X (in Blender the bow is +Y). Overall, in Godot: x -3.78..3.82, y -0.99 (keel) to 9.64
(masthead light), z -6.57 (stem) to 6.55 (transom). Hull 13 m long, 4.2 m beam. The hull is modelled down to the
keel, so the boat can rock.

| Node | Kind | What it is |
| --- | --- | --- |
| `Boat` | MeshInstance3D | everything fixed (12,751 triangles) |
| `Wheel` | MeshInstance3D | the ship's wheel (rim radius 0.3 m), origin at its hub, Godot (0, 2.016, -3.2): 1.05 m above the deck under CaptainSpot and 0.45 m ahead of it; turns about its local Z, the boat's length (824) |
| `PumpWheel` | MeshInstance3D | the air pump's crank wheel (radius 0.35 m), origin at its hub, Godot (-0.2, 1.879, 3.5): 1.0 m above the deck under DiverSpot and 0.5 m aft of it; turns about its local X (athwartships); its handle is at radius 0.22 m at the top when unturned, the grip sticking out to starboard (520) |
| `OutriggerPort` | MeshInstance3D | origin at its hinge (-0.42, 3.65, -1.85), with its net, floats, otter door and lines (2,744) |
| `OutriggerStarboard` | MeshInstance3D | the same at (0.42, 3.65, -1.85) (2,744) |

Total **19,583 triangles**. Both outriggers are raised 65 degrees; they turn about their local Z. Their lines
(topping lift, guys, door line) are in their own objects and only look right at the built angle.

**Markers** (Node3D). Each marker's -Z is the way it faces.

| Marker | Godot position | Faces | What it is |
| --- | --- | --- | --- |
| `ConsoleSpot` | (-1.37, 0.924, -0.175) | starboard (+X) | cabin floor against the port wall's inside face, at the middle of its length |
| `BoySpot` | (-0.15, 0.924, -0.175) | port (-X) | where he sits on his stool: 0.62 m to starboard of the console's face (the face taken as 0.6 m out from the wall, the bench depth), level with ConsoleSpot; the deck there is clear |
| `HelmetCable` | (-1.37, 2.224, -0.175) | starboard | 1.3 m above ConsoleSpot |
| `MonitorSpot` | (-1.37, 2.674, -0.175) | starboard | on the port wall 1.75 m above the deck; the wall is plain there |
| `CaptainSpot` | (0, 0.966, -2.75) | the bow (-Z) | inside the wheelhouse at the wheel |
| `DiverSpot` | (-0.2, 0.879, 3.0) | aft (+Z) | aft deck, a little to port of the middle, at the pump's crank wheel |
| `BowWave` | (0, 0, -5.115) | aft | the stem on the waterline (foam) |
| `Wake` | (0, 0, 6.5) | aft | the middle of the transom on the waterline (foam) |
| `Waterline` | (0, 0, 0) | the bow | |

The diver's air hose runs from the pump's outlet to a coil on deck at Godot (0.42, 0.9, 3.75) and ends on the deck
near his feet at (0.15, 0.92, 2.75).

**The cabin inside:** 2.85 m fore and aft (wheelhouse wall to the open aft end; 2.73 m between the aft posts and the
wall), 2.74 m from the port wall's inside face to the open starboard edge, 2.13 to 2.16 m from the plank tops to the
roof's underside. The port wall is a plain full wall from deck to roof; the wheelhouse's back wall closes the forward
end. Starboard: one post at the aft corner (the wheelhouse's corner post holds the forward end). Aft: open, with a
post at each corner. Room for the main session's console (2.3 m bench along the wall, 0.6 deep, 0.5 high, a 1.0 m
computer on it, a monitor reaching 2.0 m above the deck), checked with stand-in boxes in the renders.

## Materials and colours

Plain named colours, no image textures: `basket`, `bottom_red`, `brass`, `cabin_wood`, `crate_wood`, `deck_wood`,
`door_wood`, `float_orange`, `glass` (alpha 0.4, exported as BLEND), `hose_rubber`, `hull_stripe`, `hull_white`,
`lamp_glass`, `lamp_green`, `life_red`, `mast_white`, `metal_dark`, `metal_rust`, `name_board`, `net_green`,
`primer_red`, `roof`, `rope`, `rust`, `trim`, `wire`. Nothing is two-sided: every part is a closed solid.

Vertex colours ARE used (attribute `Col`, exported as COLOR_0, multiplied over the material colour): plank tints,
stains and the dark seams, uneven paint and grime on the hull, grime at the foot of the house walls, the rust runs
on the white, the nets' mesh pattern. Godot 4.7's importer leaves `vertex_color_use_as_albedo` off on the first
surface of each mesh; the build sorts materials by name so those first surfaces are `basket` (Boat) and `door_wood`
(outriggers), whose vertex colours are all white. If the game swaps in its own materials, turn vertex colours on
for all of them.

## Quality passes (2026-11-18, broadside rework)

Each pass: EEVEE renders from the title camera (Godot (11, 3, 0) looking at (0, 1.8, 0)), the second title view
(Godot (9, 2.2, 1) at ConsoleSpot), port, front, back, above, below, two three-quarter views, close on the cabin, the
wheelhouse and the aft deck gear, with stand-in boxes for the console, monitor and the three people at the markers,
and over a flat sea at the waterline. Each picture was read against the sheet above.

**Pass 1** (after the rework to the broadside layout) found:
- Rust streaks read as orange carrot-shaped teeth under every scupper: too wide, too saturated, hard-edged, regular.
- The red primer patch read as a pink sticker.
- The starboard otter door, hung just above the wheelhouse roof, read as a billboard on the roof.
- Almost no bottom paint showed above the water: the red read as a thin line.
- Scupper slots a little big.
Changed: rust is now thin runs (three per source, each its own length) of white tinted rust brown at the top and
fading into the white, only under some scuppers, the cleats and the anchor; the primer patch became one renewed
plank, a duller red; the starboard door hangs high beside its net; the boot top rose from 0.15 to 0.25 m; smaller
scuppers.

**Pass 2** found:
- The cabin's forward starboard post stood beside the wheelhouse's corner post: a doubled post.
- The tyres and the nets looked faceted (crumpled paper on the nets).
- The primer plank was still too pink.
Changed: dropped the cabin's forward starboard post; tyres made rounder (18 segments); nets smoothed more (the
outriggers are shaded smooth to 65 degrees) and cut from 16 to 14 sides to stay within budget; the primer plank darker.

**Pass 3** (check, no stand-ins): the cabin, the port wall and the people's places read clearly from the title
camera; nothing on the starboard side crosses the cabin opening; the sheer, house, stack, V of outriggers and nets
read in the side views. Left as they are: the boom and its hook fill the upper left of the title view (it is a real
part of the rig); the hull white is calm and clean between the rust runs.

**Pass 4** (the moving title: captain at the wheel, boy on a stool, diver at the pump; stand-ins at the new
markers, title camera at Godot (10.5, 3, 0.4) looking at (0, 1.9, 0.1), plus a close view of the helm and all the
earlier views). The title view shows, left to right: the diver standing side on at the pump with its crank wheel
face on and the two brass cylinders behind it, the winch, the open cabin with the boy seated in front of the console
at the port wall, the open wheelhouse door hooked back, and the captain at the wheel through the big open side window
(head, shoulders and the wheel in view; the wheel itself is edge on, as it stands across the boat). No rigging line
crosses the window, the cabin opening or either man. The stowed anchor lies below the bow bulwark, out of sight from
abeam. Nothing needed changing after it.

Earlier first build (2026-11-17/18, camera aft): the bow's raked stem pushed the outer skin inside the bulwarks (63
faces inside out); fixed by raking the stem below the deck only. The glass was made see-through so the wheel shows.

## Checked

- Inside-out faces in Blender: every one of the 580 closed parts on its own; a ray out of each triangle (from three
  points of it) must leave the part's skin an even number of times. 0 of 19,583 face inwards (`INSIDE-OUT PASSED`).
- In Godot after `--import`, read back from the .glb: winding agrees with the normals on 100% of triangles and every
  mesh encloses a positive volume; node names and classes as above (no import-hint suffixes); markers face as listed;
  COLOR_0 on every surface; 19,583 triangles.

## Not verified

- Never seen in the game, with the game's water, lighting or post shader, or on a phone (19.6k triangles and blended
  glass panes).
- The real figures, console, monitor and helmet have not stood at the markers; only boxes and cylinders (boy 1.2 m,
  adults 1.8 m) did. From the title camera the bulwark hides the people's legs below the knee.
- The thin rust runs and the nets' mesh pattern may vanish at phone size (that is intended: they are close-up detail).

## Whose calls

The user's: a shrimping boat; an open back cabin holding the computer; the boy, captain and diver on it; the boat
broadside (perpendicular) in the title; the computer against the port wall with a monitor; a design pass and quality
passes.

The main session's brief: the size (13 m by 4.2 m), the layout, the gear list, the marker names and places (port
wall console, boy 0.85 m to starboard, helmet cable 1.3 m up, monitor 1.75 m up, captain forward by the wheelhouse
door or bow, diver aft by the pump, all facing as listed), the camera places, the cabin's size, the axes, the budget.

Mine (change freely): the whole design sheet above (palette, the wear and where it is, tyre fenders, name boards
left blank, the hatch, the running lights, aerial, brow and roof rail), the wheelhouse a step higher than the cabin,
the low aft bulwark (0.45 m), the mast stepped inside the wheelhouse, the starboard door hauled up high and its net
hauled up short (the port ones hang low), the helm on the middle line with the big open window and the door hooked open aft, the pump
chest to port of its crank wheel, the stowed anchor on the foredeck, the tyres left hanging, where the
winch, pump, hatch, rope, crates and baskets stand, the see-through glass. The brief once asked for the bow on
Blender -Y "so in Godot the bow points to -Z"; those two disagree, so the bow is on Blender +Y to get the Godot result.

Reference used for shape only: Louisiana Sea Grant, "Shrimping Vessels History"
(https://www.laseagrant.org/wp-content/uploads/ShrimpingVessels-History.pdf); NOAA Marine Fisheries Review
(https://fisherybulletin.nmfs.noaa.gov/sites/default/files/pdf-content/mfr28123.pdf); Scenic 98 Coastal, "The last
true craftsmen: history of the wooden boats on Mobile Bay"
(https://scenic98coastal.com/posts/the-last-true-craftsmen-history-of-the-wooden-boats-on-mobile-bay).
