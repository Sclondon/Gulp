# Shrimp boat

The boat of the title screen (the user, 2026-11-18: the boy, a sea captain and an old-time diver "on a shrimping boat
(look up reference pics). In the open back cabin of the shrimping boat should be a old timey franketstein computer").
Only the boat is here; the figures, the computer and the helmet are made elsewhere.

- Built by `tools/build_shrimp_boat.py` (Blender 4.3, `blender --background --factory-startup --python
  tools/build_shrimp_boat.py`). It writes `tools/blend/shrimp_boat.blend` (editable) and `models/shrimp_boat.glb`.
  Run `godot --headless --path . --import` afterwards.
- A wooden Gulf of Mexico double-rigged shrimp trawler, Florida style: wheelhouse forward, working deck aft, two
  outriggers from the mast. Reference photos were used for the shape only.

## Axes and size

Origin on the centre line amidships at the waterline (y = 0 in Godot is the sea's surface). In Godot the bow points
to **-Z** and starboard is +X (in Blender the bow is +Y). Overall, in Godot: x -3.76..3.83 (outriggers and nets),
y -0.99 (keel, rudder shoe) to 9.64 (masthead light), z -6.57 (stem) to 6.53 (transom). The hull is 13 m long and
4.2 m in beam. The deck is 0.80 m above the water at the transom and rises to 1.5 m at the bow, with the bulwark
0.55 m above it. The hull is modelled all the way down to the keel, so the boat can rock.

## Nodes

| Node | Kind | What it is |
| --- | --- | --- |
| `Boat` | MeshInstance3D | everything fixed: hull, deck, houses, mast, boom, rigging, gear (10,583 triangles) |
| `Wheel` | MeshInstance3D | the ship's wheel, origin at its hub, Godot (0, 2.02, -3.35); it turns about its local Z (824) |
| `OutriggerPort` | MeshInstance3D | port outrigger, origin at its hinge (-0.42, 3.5, -1.85), with its net, floats, otter door and lines (2,896) |
| `OutriggerStarboard` | MeshInstance3D | the same at (0.42, 3.5, -1.85) (2,896) |
| markers | Node3D | below |

Total 17,199 triangles. Both outriggers are raised 65 degrees from level; they turn about their local Z to swing.
Everything tied to an outrigger (net, door, topping lift, fore and aft guys) is in its object and turns rigidly
with it, so a big swing makes those lines wrong: they are only right at the built angle.

Markers. Each is a floor point (the top of the deck planks). A marker's -Z is the way the figure or thing faces: 0
faces the bow, 180 faces aft.

| Marker | Godot position | Faces |
| --- | --- | --- |
| `ConsoleSpot` | (0, 0.944, -1.6): middle of the console's foot, against the cabin's forward wall | aft |
| `BoySpot` | (0, 0.932, -0.7): 0.9 m aft of ConsoleSpot | the bow (towards the console) |
| `CaptainSpot` | (-0.95, 0.874, 3.4): aft deck, port | aft |
| `DiverSpot` | (0.95, 0.868, 3.8): aft deck, starboard, just aft of the air pump | aft |
| `HelmetCable` | (0, 2.444, -1.6): 1.5 m above ConsoleSpot | aft |
| `Waterline` | (0, 0, 0) | the bow |

Not a marker: the diver's air hose ends on the deck at Godot (1.25, 0.90, 3.55), next to DiverSpot.

## What is in it

- Hull: one lofted solid from transom to stem with the deck and bulwarks: white topsides, a teal sheer stripe with a
  rub rail under it, red-brown bottom paint from 0.15 m above the water, a varnished rail cap, a flared bow with a
  stem bar, a flat transom with its bulwark board, skeg, rudder, shoe and a four-bladed bronze propeller. Plank frames
  inside the bulwarks aft; cleats on the rail.
- Deck: separate planks (15 cm, staggered joints), each a slightly different tint, with dark seams between them.
- Wheelhouse (forward, 2.7 m wide, 2.3 m deep): three front windows, two port, one starboard, a door on the
  starboard side with a small window and knob, see-through glass, the wheel on a pedestal and a shelf under the front
  windows, a roof with a searchlight, a horn and an exhaust stack.
- Open-backed cabin behind it: 2.74 m wide inside, 2.3 m deep, 2.13 m from floor to roof. The wheelhouse's back
  wall is its forward wall (plain, for the console). Waist-high side walls, closed above the waist only in the forward
  half, posts at the aft corners, and nothing across the back: from the title camera's place (Godot (0, 3.5, 13.5))
  the whole forward wall and floor are in view. A life ring hangs on the port side outside.
- Mast (to 9.5 m) with a crosstree and masthead light, an outrigger collar, a boom swung aft over the deck with a
  block and hook, a forestay, backstays and shrouds.
- Each outrigger: a pole with a tip block, a green net hanging from the tip to dry (a lumpy bag with a mesh pattern
  in its vertex colours, a head rope with six orange floats, a dark lead line, a tie at the cod end) and a wooden
  otter door with a steel shoe and braces, hung against the hull's side from the pole by a line and bridle.
- Aft deck: a winch just aft of the cabin (starboard of the middle, low enough not to hide the console), the diver's
  air pump (a wooden box with a big wheel and crank at each end, a gauge, a brass outlet) with a hose to a coil and a
  hose from the coil to the diver's feet, a coil of rope to port, crates at the port quarter, shrimp baskets at the
  starboard quarter. An anchor hangs on the starboard bow, its stock across the rail.

## Materials and colours

Plain named colours, no image textures: `basket`, `bottom_red`, `brass`, `cabin_wood`, `crate_wood`, `deck_wood`,
`door_wood`, `float_orange`, `glass` (alpha 0.4, exported as BLEND), `hose_rubber`, `hull_stripe`, `hull_white`,
`lamp_glass`, `life_red`, `mast_white`, `metal_dark`, `metal_rust`, `net_green`, `roof`, `rope`, `trim`, `wire`.
Nothing is two-sided: every part is a closed solid (no `_2sided` material).

Vertex colours ARE used (attribute `Col`, exported as COLOR_0, multiplied over the material colour): plank tints and
the dark seams, grime at the boot top, a darker foot to the bulwarks, the nets' mesh pattern. Godot 4.7's importer
leaves `vertex_color_use_as_albedo` off on the first surface of each mesh (seen here on whichever material came first);
the build sorts the materials by name so that the first surfaces are `basket` (Boat) and `door_wood` (outriggers),
whose vertex colours are all white, so nothing is lost. If the game swaps in its own materials, turn vertex colours
on for all of them.

## Checked

- Inside-out faces, in Blender: every one of the 502 closed parts on its own, a ray out of each triangle must leave
  the part's skin an even number of times. 0 of 17,199 triangles face inwards (the build prints `INSIDE-OUT PASSED`).
  The first build had 63 wrong at the bow, where the raked stem pushed the outer skin inside the bulwarks; fixed by
  raking the stem below the deck only.
- In Godot, after `--import`, from the .glb: every triangle's winding agrees with its normals (100%) and each mesh
  encloses a positive volume; the node names and classes above came through (no import-hint suffixes), COLOR_0 is
  present on every surface, triangle count 17,199.
- Renders (EEVEE) from port, starboard, front, back, above, below, two three-quarter views, the title camera's place
  (Godot (0, 3.5, 13.5) looking at the cabin) and close at the wheelhouse window (the wheel shows through the glass).

## Not verified

- Never seen in the game, on the water, with the game's lighting or post shader, or on a phone (17k triangles and six
  blended glass panes).
- The figures, the console and the helmet have not been stood at the markers; heights assume a 1.2 m boy and 1.8 m
  adults standing on the plank tops.
- The nets' mesh pattern is a checker of vertex colours: it reads as fine diagonal stripes close up.

## Whose calls

The user's: a shrimping boat, an open back cabin holding the computer, the boy, the captain and the diver on it.

The main session's brief: the size (13 m by 4.2 m), the layout (wheelhouse forward, open-backed cabin behind it,
working deck aft), the list of gear, the marker names and places, the axes and origin, the triangle budget.

Mine (change freely): the colours (white, teal stripe, red-brown bottom), the cabin's half-closed side walls and two
posts, the mast stepped inside the wheelhouse just forward of the console wall with the outriggers hinged on a collar
above the roof, the boom swung aft, nets hung from the outrigger tips and doors hung against the hull, the anchor on
the starboard bow, where the winch, pump, rope, crates and baskets stand, the captain and diver facing aft (towards
the title camera), the see-through glass, the shelf in the wheelhouse.
The brief asked for the bow on Blender's -Y "so in Godot the bow points to -Z"; those two disagree (Blender -Y
becomes Godot +Z), so the bow is on Blender +Y to give the Godot result asked for.
