# The reef wreck: a sunken four-funnel liner

The user (2026-11-18): "the reef should be built into a ship wreck like an onld timy passenger titanic style", and
of the map: "with the reef wreck at the x". The map's code adds it: `Wreck.new()`, placed at `Sea.WRECK_AT`, turned
to `Sea.WRECK_HEADING` (rotation.y), `add_child`. Nothing else is needed from the map.

Files: `tools/build_wreck.py` (Blender 4.3, background) builds `tools/blend/wreck_liner.blend` (editable, with its
procedural paint), `models/wreck_liner.glb`, `models/wreck_liner.json` (collision spheres and the swim routes),
`textures/wreck_atlas_bow.png` and `textures/wreck_atlas_stern.png`. `scripts/wreck.gd` (`Wreck`) draws it with
`shaders/wreck.gdshader`, registers its spheres with `Sea.add_rock`, and grows the reef on it.
`tests/wreck_view.gd` checks it (headless, `-- --check`) and takes pictures of it (in a window).

## Design sheet (written before building)

**What it is.** An original ship in the manner of the great four-funnel liners of 1910-1914 (Olympic class and
their kind): a long black hull with a plumb stem and a rounded counter stern, a white superstructure in one long
band, four tall raked funnels, a forecastle and a well deck forward, a poop aft. No name, no real ship's plan, no
one's model or texture.

**Scale (Claude's call).** About 60 m long (the real ships were about 270 m: 0.22 of that) and 7 m in beam, as
asked; the heights are stretched (keel to boat deck 9.9 m, funnels 7.5 m above it: about 1.6 times the true
proportion) so that a deck is 2.3 m clear inside and a fish can swim through it. A real liner's profile is about
0.2 as tall as it is long from keel to funnel tops (53 m on 269 m); this one is 0.29.

**How it lies.** On the sea bed, broken in two a little aft of amidships (between the third and fourth funnels,
through the aft grand staircase, as the famous wreck broke). The bow section lists 12 degrees to port, its nose a
little down and dug in; the stern section lies 5 to 7 m off, swung 20 degrees, rolled 5 degrees the other way and
sunk deeper, its propeller half buried.

**Local axes (Godot).** Origin: the middle of the keel's resting line, y = 0 at the sea bed (the keel is sunk about
half a metre below it). The bow points to -Z (Godot's forward), starboard is +X, up is +Y.

**The parts.**
- Hull: plumb stem; flare at the bow; a flat-bottomed parallel middle body; the run aft to a sternpost, a rudder and
  a three-bladed propeller under the overhanging counter. Black topsides, red anti-fouling below the old waterline,
  two rows of portholes (0.5 m; the upper row really open where a room is behind it).
- Forecastle (raised, with the bow rail still standing, two capstans, anchor chains to the hawse pipes, the anchors
  in them, rusticles hanging off its edges); the well deck behind it with two open cargo hatches; the foremast
  fallen aft across the well deck onto the collapsed bridge.
- Superstructure: the promenade deck (a long row of windows on the starboard side, open, with the corridor behind
  them), the boat deck on top with empty davits, cowl ventilators, deckhouses, a few runs of railing left.
- Funnels: the first is a stump open down into the boiler room; the second still stands, raked; the third has
  fallen across the deck to port (a hollow tube lying there); the fourth (on the stern section) is a stump open
  down into the engine room.
- The bridge: the front collapsed, the wheelhouse roof sagging down to the deck, the telemotor standing alone.
- The break: torn plating and decks, a boiler lying in the gap, torn plates on the sand.

**Swim routes (each is checked: `tests/wreck_view.gd -- --check`).**
1. The tear: in through a rip in the starboard side (the high side) into the boiler room, past the boilers, up the
   first funnel's shaft and out through its stump.
2. The hatches: down the well deck's hatch into the hold, along it, up the forecastle hatch; or from the hold
   through the broken bulkhead door into the boiler room.
3. The colonnade: in through a promenade window, along the corridor (2.4 m wide, 2.35 m high) behind the row of
   windows, out on to the saloon's gallery, down over the grand staircase, out through the break.
4. The skylight: down through the empty dome over the staircase into the saloon, and out through the break.
5. The gap between the two halves, from side to side.
6. A porthole (small fish only): into the boiler room.
7. The fourth funnel: down its stump into the engine room, out through the break.

**Palette.** Hull black gone rust (orange-brown patches and runs, pale growth on what faces up); anti-fouling red
gone dull brick; deck planking rotten grey-green with dark seams; superstructure white gone grey-green with rust
runs; funnels buff gone ochre with black tops; brass gone verdigris; saloon panelling dark oak; machinery and
interiors rust; windows and holes black. One painted picture per section, baked in Blender (colour times how open
to the sea each spot is: dark inside, light on top), drawn lit by the sea's own light.

**Budget.** About 25,000 triangles; spent on the outline, the bow, the openings and the staircase; long plating in
big triangles.

## Concept art (arrived mid-build)

`tools/art_src/concept_liner_wreck.jpg` (the user asked for concept art first, then to build to it). Built to it:
- the palette (slate-blue hull plate with orange rust runs, dull red bottom, grimy white, warm brown decks, moss on
  what faces up, green weed hanging off the deck edges);
- the row of square promenade windows in the dark plate, open, some shutters fallen open below them;
- the forecastle's white strake with its own portholes, the bow rail, the anchors in their hawse pipes;
- the grand staircase under a round dome of clouded glass (panes missing, bare ribs), opened by the break;
- one funnel standing, buff with a black top; the stern beyond with its propeller half buried;
- reef thick on the decks and spilling on to the sand along both sides.
Still different: the concept's water is teal and bright, the game's is deep blue (the sea's own light and post
shader, not the wreck's); the concept keeps the foremast standing with rigging (the brief asked for it fallen);
the concept has two tiers of white houses above the promenade, this has one deck of white houses on the boat deck;
the concept's staircase is seen through a hole in the side, here through the break and the skylight; no fish or
kelp come with the wreck (the game's own sea life does that).

## As built (2026-11-18, after pass 2; pass 3 changed the numbers: see its entry below)

- **Size and lie.** 60 m stem to counter as built upright (about 66 m end to end as it lies, the stern section
  5 to 7 m off); 7 m beam; keel to boat deck 9.9 m, the standing funnel's rim 17.4 m above the keel (needs 20 m of
  water or more; the map's shelf is 30 m deep). Godot axes: the bow points to -Z, starboard +X; the origin is the
  middle of the keel's resting line, y = 0 at the bed. The bow section lists 12 degrees to port, nose down 1.2
  degrees, sunk 0.45 m; the stern section is swung 20 degrees, rolled 5 degrees to starboard, pitched 2 degrees,
  sunk 1.4 m (its propeller half under the sand).
- **Triangles** 14,590 (bow 10,802, stern 3,788) of the 25,000 budget.
- **Paint**: two 2048 atlases. Bow 3,022 m2 of surface on 45% of its picture: 25 texels a metre (4 cm a texel);
  stern 1,192 m2 on 72%: 50 texels a metre (2 cm). The saloon and the bow share the bow's density. A 4096 bow atlas
  would double it (not done: the web build's size).
- **Collision**: 1,004 spheres (0.22 to 1.5 m; 41 under 0.7 m, kept off the routes), at most 376 in one of Sea's
  8 m squares; a `Sea.clear_of_rocks` call beside the wreck costs 11 to 27 us (desktop, headless). A swimmer stays
  about 0.6 m off a wall (BULGE). 127 of 18,149 surface samples are left uncovered, all at the edges of the routes'
  openings.
- **Swim routes** (`tests/wreck_view.gd -- --check`; the room is a fish's `Sea.clear_of_rocks` room, 0.3 of its
  length): tear, boiler room, up the first funnel: room 0.5 (a fish up to about 1.7 m); hatch, hold, forecastle
  hatch: 0.5; hold through the bulkhead door: 0.55; promenade colonnade, gallery, staircase, out the break: 0.5;
  down the skylight into the saloon: 0.75 (2.5 m); the gap: 1.5 (5 m); a porthole: 0.12 (a 0.4 m fish); down the
  fourth funnel through the engine room: 0.5. Every point along each is left in place.
- **Reef**: about 400 pieces of GameCommon's sea floor kit (tropical and cold: corals, fans, sponges, anemones, sea
  stars, urchins, clams) in clumps at the 40 ReefSpots and on the sand along both sides; none within a metre of a
  route; the barrel sponge only on the sand.

## Checks and passes

- Inside-out: in Blender every closed part is ray-tested (341 parts, none turned in); in Godot both halves' winding
  agrees with their normals (99.97%, 99.95%; the rest are slivers) and enclose positive volume. Interiors are thick
  walls (room cutters taken out of one solid), so both sides of every wall are outward faces of a solid. Decals
  (painted portholes and windows, brass rings) are one-sided sheets lying 1 cm off a surface.
- `sh tests/smoke.sh`: GULP SMOKE PASSED (the wreck is not in the game yet).
- Pass 1 (Blender renders and the first Godot pictures): bow too blunt (plan curve made a V); stern run too full
  (finer); the sea bed showed inside the boiler room, the hold and the engine room (their floors were below the bed
  where the hull lists: raised to 1.4, 1.7 and 2.2 m above the keel); interiors vanished in Godot when near
  (Godot's generated LODs collapse thin walls: `generate_lods=false` in `models/wreck_liner.glb.import`); the paint
  far darker than the game's sand (colours times 1.8).
- Pass 2 (beside the concept): palette to the concept's; promenade windows into the dark plate; white forecastle
  strake with portholes; glass panes on the dome; weed drips; shutters; reef thicker and on the sand; then the
  shader's `lift` (a power curve on dark paint) set to 0.3 so rooms read without washing the hull out; reef kept
  out of the routes (it filled the funnel's mouth and the foot of the stairs); barrel sponges off the decks.
- Pass 3 (the coordinator, beside the concept: "reads much plainer than the picture"):
  - Reef about tripled: 1,089 kit pieces (was about 400), 9 to 15 in each ReefSpot clump; 70 clumps on the sand,
    each of 6 to 12; 12 big coral heads (bommies) on the sand with table corals on top, given to Sea as rocks with
    the kit's own spheres. Seaweed from GameCommon's `seaweed` stands on the decks and, tall, on the sand. Pale
    pieces are tinted from a warm list (pink, orange, purple, yellow-green, gold). Reef is still kept a metre or more
    off every route.
  - The reef's colours: in a neutral white light (`tests/wreck_view.gd -- --neutral`: no fog, no water colour, no
    post shader) they come through: reds, pinks, greens, purples, golds. Under the game's water they turn blue. That
    is the sea's light (blue ambient light, a blue sun, blue fog, the post shader's tint), not the wreck's.
  - Hull: plate seams (1.4 m strakes, 3 m plates) with a fainter rivet row beside each, baked in; a band of weed
    along the old waterline; the red bottom broken by growth; rust run decals under every porthole, window and
    scupper (scuppers added along the deck edge); the starboard anchor out of its hawse and hanging low against the
    bow on a chain of links; railings bent and draped with weed and rusticles (four more runs); weed and rusticles
    off every davit; a second tier of white house on the boat deck, with windows.
  - The break: the hull's frames stand bare beyond the torn plating on both halves (some bent), torn plates peeled
    outwards; the saloon's starboard side torn open in a jagged hole with ribs at its edges, so the staircase and the
    dome read from outside. A new swim route goes in through that hole, over the stairs and out of the break (room
    0.5).
  - The foremast now stands on the forecastle, broken short at about 15 m, with its crow's nest and four stays
    (to the stem, both sides, the bridge) hung with weed; its top lies on the sand off the port bow. It clears the
    hatch route.
  - The bow atlas went to 4096: the decals had cut the picture's use to 36%. Both halves now have about 45 texels
    a metre (2.2 cm).
  - Now 17,606 triangles; 1,016 spheres of hull plus 122 of the coral heads; a `Sea.clear_of_rocks` call costs
    about 12 us beside the wreck.
  - Still different from the concept: the game's water is blue, not teal (being changed separately); the rust
    runs read as tidy tan stripes, not the concept's soft streaks; the concept's promenade windows are bigger, with
    brass frames; there are no fish or bubbles.
- Not verified: a phone or a web build; the cost of 400 reef pieces and 14,600 triangles on a phone; how it sits on
  the map's real ground (sinking 0.45 to 1.4 m allows for some unevenness); fish actually swimming the routes in
  play (only the collision is checked).

## Whose calls

The user's: a liner wreck "titanic style", the reef built into it, at the map's X.
The task's (from the session that asked for it): about 60 m, 7 m beam, 12 degrees to port, broken in two, the list
of features, the swim routes, the triangle budget, one baked atlas look.
The concept art (the user's request for it; generated): the palette, the promenade windows in the dark plate, the
glass dome, the reef spilling on to the sand.
Claude's: everything else here (the stretched heights, the layout of rooms, which funnel is which, where the
routes run, the palette's numbers, two 2048 atlases, the sphere bulge of 0.6 m, the lift curve, the reef's amount,
lit rather than unshaded drawing, the LOD switch-off).
