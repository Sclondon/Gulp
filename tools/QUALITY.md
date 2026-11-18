# Gulp: the quality pass on clipping, hit boxes and textures (2026-11-18)

The user: "also do a quality pass on clipping adn hit boxes" and "and make sure things have textures that fit our art
style". Done by an agent and three helpers after the first push. Every number and choice below is Claude's unless it
quotes the user. Pictures are in the session's scratchpad
(`C:\Users\stewa\AppData\Local\Temp\claude\be065d617517d416\9790e32c-36f1-4aaf-8ece-7f095c2906fe\scratchpad\quality\`,
called `quality\` below); they are for checking, not kept in the repo.

## The checks (all headless, silent)

| | |
| --- | --- |
| `godot --headless --path . --audio-driver Dummy -s res://tests/hitboxes.gd` | Every kind's drawn model against the length, nose and mouth the game uses (`-- --kind=a,b`, `-- --slices` for a girth profile) |
| `... --fixed-fps 60 -s res://tests/giants_solid.gd` | The player steered into nine big kinds as a sardine and a tuna, and put inside the reef-back: how deep it gets into a body |
| `... -s res://tests/camera_clear.gd` | The eye at five places round the rocks, at three fish sizes: in a rock or the floor, sight line blocked, old place against new |
| `... --fixed-fps 60 -s res://tests/floor_clip.gd` | Every animal that keeps to the floor, after 8 s about its business: sunk into the floor or hovering over it |
| `... -s res://tests/setpiece_hits.gd -- --only=liner,pirate,ruins` | The set pieces' spheres against their drawn surfaces: open surface ("clip" over 0.15 m, "hole" over 0.4 m) and spheres standing proud. `--only=kit` for the kit's pieces; `--only=docks` needs a window. `--fit-ruins --no-ruins-extra` rewrites `models/ruins_extra.json` |
| `tests/contact_sheet.gd`, `material_scan.gd`, `panel_overlap.gd`, `title_clip.gd` | The art-style sheets (window), the list of flat-coloured surfaces (headless), the panel housings' overlaps (window, `-- --calm --shot=60`), the helmet cables against the computer (headless, `--title`) |

## Part one: hit boxes

### Eating: the mouth and the reach (fixed)

`tests/hitboxes.gd` dresses a Fish of every kind (155) as the game does and measures its drawn model in its own space.
The body is taken as the slices of at least 15% of the greatest girth (so a bill, a tusk, feelers, a whip tail or
trailing arms are outside it), the mouth at the body's front.

- **Lengths agree.** For every swimmer the drawn nose-to-tail is the game's length within 2% (the components' LENGTH is
  right), and the nose is where the game puts it. What is drawn beyond the length is appendages, by design: the
  narwhal's tusk (+0.56 of a length ahead), the lobster's, prawn's and shrimps' feelers (+0.3 to +1.1), the eagle,
  devil and manta rays' whip tails (drawn 1.35 to 3.35 times the disc), the giant squid's tentacles (1.34), the
  anglerfish's lure (+0.17), the cuttlefish's arms (+0.3), the turtles' flippers (1.15 to 1.24). Upright kinds
  (seahorses, sea lily) are measured by height. The submarine's lamp beams are not body.
- One real slip: the **female guppy** was drawn 13% long (its component is 0.045 m, the game took 0.04): `long` 0.045.
- **The mouth was in the wrong place on five kinds**: the game put every mouth 0.08 of a length behind the nose. The
  billfish's mouths are at the root of the bill and the squids swim mantle first with the beak among the arms behind:

  | kind | mouth behind the nose (share of length), before | now |
  | --- | --- | --- |
  | swordfish (player kind) | 0.08: on the bill, 1.1 m ahead of the mouth | 0.35 |
  | sailfish (player kind) | 0.08 | 0.26 |
  | marlin (player kind) | 0.08 | 0.21 |
  | Humboldt squid (pack hunter) | 0.08: it bit with the tip of its mantle | 0.62 |
  | giant squid | 0.08 | 0.46 |

  New Species field `mouth`; `Fish.mouth()` reads it (`Fish.MOUTH` 0.08 otherwise).
- The test still flags 51 kinds; read with the girth profile, the rest are the heuristic, not faults: slender heads
  under 15% of a tall tail or sail (barracuda, wahoo, spinosaurus, hippocampus, kelpie), big fins (flying fish, blue
  shark), feelers and tails (above), flat radial bodies (stars), shells (ammonite, razor clam). The player's 23 kinds
  and the new kinds (leviathan, sea serpent, submarine, remora, mermaid, deep spawn, ghost whale, river beast) all have
  drawn length = game length within 2%.
- **The reach was measured from middles**, so it did not match what is drawn:
  - Being eaten: a hunter's mouth within 0.22 of its length + 0.3 of the player's of the player's MIDDLE. A 4.8 m
    white shark took a 0.25 m sardine with its mouth 1.1 m from the sardine's skin (4 sardine lengths). Now: the
    hunter's mouth within `Life.JAWS` (0.1) of its own length of the player's body (`Fish.gap_to`: the line nose to
    tail, less a half-thickness of 0.1 of the length): 0.48 m for that shark, about its head's half-width.
  - Eating: the prey's middle within 0.3 of the player's length + 0.35 of the prey's of the mouth. An 8 m orca ate a
    1 m fish 2.7 m from its mouth; a fish crossing ahead was eaten by its middle. Now: the mouth within `Life.TAKES`
    (0.2) of the player's length + 0.03 m of the prey's body. Head-on it is about as forgiving as before (a little
    suction is kept on purpose: never fail to eat what is in your mouth); side-on, a fish half a length off is no
    longer taken.
  - The arena's claims, the hook's bite and sea life taking a bait use the same reach.
  - The boat's net sold a fish with its mouth 0.9 m from the hoop's middle (the hoop is 0.8 m across: half a metre
    outside it; an orca 3.2 m off). Now within 0.55 m, or 0.15 of a big fish's length.
  - Play: the bot ate and grew the same under both rules (two 300 s runs each: 272 to 277 meals, stage 1, no deaths),
    and every smoke check passes.

### Giants: solid (fixed)

Before, the player swam straight through every animal it could not eat: the whales, the leviathan, the submarine,
the whale shark, the reef-back (no spheres at all); the old one had three spheres for a body 50 m across. Now anything
1.5 times the player's length or more (`Life.SOLID`) is a rounded rod down its middle `Life.BODY` (0.11) of its length
thick, and the player is pushed out of it each frame (`Life.push_off`), keeping its way along the body. A hunter that
could eat the player is left out (it would be pushed off its own bite). The reef-back's trunk is the same rod in
`Life.solids` (Main fills it: 4 to 13 m up, nose to tail root). `tests/giants_solid.gd`: steered at the middle of nine
big kinds for 2 s, as a sardine and as a tuna, the player never got into a body (0.00 m); put inside the reef-back it
came out at 4.86 m from its middle. Cost: a few multiplications for the animals in sight. Decision in CLAUDE.md.
Not done: the old one (its spheres are in `scenery.gd`, another builder's: see below); bodies bent into a turn are
treated straight.

### Rocks and set pieces (liner, pirate ship, Atlantis fixed; the rest measured)

`tests/setpiece_hits.gd`. Clip % / hole % / spheres / spheres standing proud:

| piece | before | after |
| --- | --- | --- |
| liner | 4.4 / 3.0 / 1138 / 30.6% (up to 1.5 m off the hull) | 6.7 / 4.3 / 2832 / 5.2% (at most 0.4 m) |
| pirate ship | 5.2 / 2.9 / 713 / 57.5% (up to 1.4 m) | 6.4 / 3.0 / 1130 / 26.1% (nearly all 0.3 to 0.6 m) |
| Atlantis | 33.8 / 10.4 / 940 / 0.6% | 6.8 / 0.0 / 2547 / 4.6% |

- Liner (`tools/build_wreck.py`, `STANDOFF` 0.4): each sphere no more than 0.4 m beyond the nearest surface; small fish
  now come within 0.4 m of the hull instead of stopping up to 1.5 m short of nothing. Its remaining holes are walls
  along its swim routes, which spheres may not enter (worst about 5 m² round the break, (-25.5, 17.3, 135.1)).
- Pirate ship (`tools/build_pirate_wreck.py`, `BULGE` 1.2 -> 0.45, `SAND_DOWN` -1.5): spheres stood up to 1.3 m off
  masts, yards and hull; the hull's ends below her sand line had none (8 m² holes). Worst left: sails about
  (-77, 28.9, -23), the stern cabin walls (-81, 19.3, 5.3).
- Atlantis: thin paving slabs over a falling floor had no spheres (fish passed through them). `models/ruins_extra.json`
  (1,607 spheres up to 0.45 m, 0.2 m in from every surface open more than 0.3 m, kept out of every route), read by
  `scripts/ruins.gd` (`Ruins.EXTRA`).
- Route checks: `WRECK CHECK PASSED` (every route 0 points pushed, 12 fish spots clear), `PIRATE VIEW PASSED` (985
  route points, 0 blocked), `RUINS CHECK PASSED` (12 routes open). The glbs and blends are unchanged (md5).
- Cost: 6,215 -> 10,114 spheres in the sea; `Sea.clear_of_rocks` liner 1.1 -> 1.2 us, pirate 1.5 -> 1.5, ruins 1.2 ->
  1.2, kelp 1.0 -> 0.9 to 1.5, open water 0.36 -> 0.37 to 0.65 (a busy machine): within 1.5 times.
- Retired, unused: `models/wreck_liner_old.json`, `models/pirate_wreck_old.json` (left out of the web pack by
  `tools/web_excludes.sh`).

**Not fixed (another builder's: `scripts/scenery.gd`, `biomes.gd`, the kit), measured:**
- The kit's cliffs: 42 to 45% of their surface open more than 0.4 m (ledges, crack, overhang, buttress), 17 to 33% of
  their spheres proud. Rocks: ledge 34%, arch 18%, slab 18%, pinnacle 9%, bommies 7 to 8%. **The biggest open area left:
  fish swim into the cliffs and ledges.**
- The old one: 3 spheres (5, 8.5, 11 m) for a 50 m body: 57% open, spheres up to 4.4 m proud at (-42.4, -32.6, 29.2).
- Moored trawler at Monterey: 5 spheres up to 2.4 m proud at (58.7, 39.4, 69.4). Outcrop island: a 3.6 m sphere 1.7 m
  proud at (-98, 39.1, -24); 0.6 to 1.1 m proud round (-106 to -113, 17 to 32, -26 to -33). Dock islets 18% open,
  shards 30%, pillars 6.6%. Sailboats: re-run `--only=docks` (the first run took their hulls for sails).
- Fine: pilings and floats (0%), mangroves under water (0.3 to 3.7%), the skiff (1.5%).
- The pirate build reports 3 hull faces inside out at (±2.63, 15.06, 6.4), (4.72, 6.28, 3.08) (were there before).

### The camera (fixed)

`Main._camera_place`, every line added:
- `var pivot := player.global_position + Vector3.UP * long * 0.3`: the camera's way is tried from just over the fish.
- `var eye := _camera_clear(pivot, behind, long * 0.7 + 0.2)`: along the way to its old place, 8 points; it stops at
  the last one clear of the rock spheres (0.3 m) and the floor, never nearer than 0.7 of the fish's length + 0.2 m
  (outside its body), then is pushed clear of any rock it is in and kept 0.3 m over the floor.
- `if eye.distance_squared_to(behind) > 0.0025:` when that brought it in, `over` (higher over the fish, 1.8 lengths
  up, 0.7 back) is tried the same way, and taken if it sees further.
- The easing (`lerp` at 5 a second in `_process`) is unchanged, so it slides in and out smoothly. In a leap the eye is
  placed as before. `tests/camera_clear.gd`, eye in a rock or the floor, old -> new: liner 33% -> 3% (sardine), 16% ->
  2% (tuna), 2% -> 0% (orca); pirate 32% -> 1%, 21% -> 2%, 5% -> 0%; ruins 21% -> 1%, 11% -> 3%, 2% -> 0%; kelp 15% ->
  0%; docks 20% -> 0%, 10% -> 0%. Sight line blocked: liner 37% -> 4% (sardine), 41% -> 16% (tuna), 27% -> 15% (orca);
  the rest are the eye at its nearest (it does not go inside the fish) or a rock between the fish's middle and the
  pivot. It never came nearer than its fish's body. Not done: animals and giants do not stop the eye.

### Hooks, nets, the boat's net

Hooks and baits now use the eating reach (above). Gill nets are crossed by side (the drawn panel itself), trawls by
their own frame: both match what is drawn (smoke checks). The boat's net: above.

## Part two: clipping

- **Animals that keep to the floor (fixed).** They were held 0.1 m up whatever their size (`keep_in`'s room) and
  steered towards 0.03 m over the floor, slowly, so shrimps, nudibranchs and stars hovered, walkers off a ledge hung in
  the water (a prawn 5 m over the trench floor), and anything on a slope stood level with one side in the sand. Now:
  how far each kind's drawn body reaches below its middle is measured when it is first dressed (`Creature._belows`),
  it stands that high (`_stands()`); walking, it stays on the floor (unless a rock holds it up, it hops or it hunts);
  resting, it lies along the slope (`_lie_on_floor`). `tests/floor_clip.gd`, 29 floor kinds, 8 s: before, 24 kinds had
  some sunk or hovering (worst: prawn 5.0 m over, octopus 1.7 m in, halibut 0.8 m over); after, 0 hovering and only the
  octopus (its arms' box on a slope: the box overstates it) and one cheeked trilobite (0.06 m) sunk.
- **The title** (helper's pictures, `quality\ui1\title_*.png`): the helmet's cables go INTO the wall monitor: about 30%
  of each cable's points inside its box, up to 0.11 m deep (`tests/title_clip.gd`); their ends are set in
  `Title._process` (`top * Vector3((k - 0.5) * 0.5, -0.2, -0.25)`): not fixed (they need a socket on the computer's
  model to end at; next pass). Clear of the housings, bench and stool. The figures were not measured in code (posed
  meshes). The fish logo is 6 m in front of the eye, so it passes through nothing; at 1280x720 its letters sit over
  the mast, booms and net so the word is hard to read (framing in `Title`, `TitleLogo.hold`): not fixed.
- **The control panel**: housings' boxes overlap helm/gauges 30 px and engine/gauges 32 px at 390x844 (about 8% of the
  gauges' width; the gauges' side pipes tuck behind the side housings), 16 to 20 px at 844x390 and 1280x720. It reads
  as one panel and no control is hidden: left. At 720x720, 844x390 and 1280x720 the panel covers about the bottom half
  of the screen (a sizing choice).
- **The sale and shop screens**: no overlaps at any size. Fixed: the choice card's fish (`Hud.ChoiceCard`) spilled past
  its ring broadside (a tuna's tail cut off at the square edge): its camera is further back (0, 0.31, 1.8).
- Not checked: plants through hulls (another builder's placement), schools through each other, animals through rocks
  other than the floor test (they are pushed out of rock spheres as the player is).

## Part three: art style

The settled look: the brass control panel (low-poly, procedural paint baked to one atlas, drawn unlit:
`tools/art_src/panel_concept_1.png`), the set pieces' baked atlases, the creatures' painted shaders with cartoon eyes,
a half-size dithered picture.

### The boat (done)

`tools/build_shrimp_boat.py` now bakes: every material is a procedural paint (white paint chipped to primer with
dirt runs; wood grain along the deck planks and trim, upright on the cabin and doors; mottled red bottom paint; rust;
brass gone green; broad tone unevenness), times the old "Col" vertex colours (plank tints, seams, scupper rust), with
an ambient-occlusion grime mask in corners; all five meshes in one atlas, baked by Cycles under an even sky brighter
above (contact shadow and occlusion, no sun direction). 2048 square, embedded as a JPEG (quality 90), imported lossy with
mipmaps: about 0.40 MB in the pack (the glb 1.18 -> 1.97 MB). Bake 72 s; `-- --no-bake` gives the old plain build.
Every node, marker, name and origin is unchanged (a dump of the imported tree compared). Winding: 21,639 triangles, 0
inward. `scripts/title.gd` no longer turns on vertex colour as albedo. **Claude's call, against the brief's "drawn
unlit"**: the paint is lit by the game's sun (a StandardMaterial with the atlas), because the boat turns on its circle
(a baked sun would be wrong half the time) and lives through day and night above water (unlit it would glow at night).
No shader programs added.

Before and after: `quality\boat\before_close.png` / `after_close.png`, `before_title_1280x720.png` /
`after_title_1280x720.png`, `before_title_390x844.png` / `after_title_390x844.png`, and four sides
(`before_side_port.png`, `before_bow.png`, `before_stern.png`, `before_above.png` and their `after_`). Verdict: no
longer flat and clean (grain, chipped and streaked paint, grime and shadow in corners and under the roof); lighter
and less weathered than the panel's rusted brass, which suits a white working boat. The hull's rust weeps are fainter
than the old vertex-coloured ones, and the winch and mast stay fairly plain: a second pass could strengthen both.

### The fishing gear (done)

`tools/build_fishing_gear.py` the same way, a 1024 atlas (about 0.09 MB): the skiff a worn white hull, grained wooden
inside, red-brown bottom; the otter doors grained and grimy; floats and buoys plain with grime. Not baked: the net
panel, the line and the trawl's net (its UVs are metres for `net.gdshader`); the trawl's rope, chain and floats keep
plain copies of their materials (`chain_plain`, `float_orange_plain`, `rope_plain`). Pictures:
`quality\boat\gear_after_*.png`, before `quality\boat\gear_before_blender\`.

### Verdicts by group (helper's sheets, every one read)

Sheets: `quality\sheets\gear.png`, `docks.png`, `kit.png`, `creatures.png`, `title.png`, `effects.png`;
`quality\sheets2\kit.png` (sea-floor pieces); the places from the game's own `--perf-shots`: `quality\places\*.png`;
the 2D screens `quality\ui1\sell_*`, `shop_*`, `over_*`, `play_*`. (The gear sheet is from before its bake.)

| group | item | verdict |
| --- | --- | --- |
| gear | hooks, worm, sinker, red-and-white float, bait fish, marker buoys and flags, trawl doors, skiffs | did not fit (flat colours, clean): skiff, doors, floats and buoys now baked; hooks, worm, sinker, bait, flags still flat |
| gear | an unnamed pale-blue box (0.78, 0.88, 0.92), two a rig | does not fit: a plain block |
| gear | trawl net, net panels (`net.gdshader`) | fits |
| docks | decks, piles, floats, sailboats, tyre, crab pot, chain, anchor | does not fit: flat colours, no grain or grime (`tools/build_docks.py`: not reached) |
| docks | mussels on the piles | does not fit: chunky blue lumps |
| outcrop | islet, pillar, shard | **does not fit: plain grey cones and cylinders, the worst rocks in the sea** |
| plants | kelp, sea grass, mangroves, seaweeds | fit |
| plants | sea lettuce, red algae | too clean: flat saturated colour |
| floor | rocks (split, boulder, ledge, stack, slab, arch), brain coral | fit (the pink coralline blotches a little noisy in plain light) |
| floor | cliffs | mismatched resolution: a stretched, smeary low-resolution texture |
| floor | bommies, giant clam | too noisy (rainbow confetti; the clam a smeared rainbow, looks generated) |
| floor | urchins, hydrocoral, puffball sponges, strawberry anemones, soft coral, sea fans, green anemone, mussel clump, scallop | too clean: one flat saturated colour each |
| floor | vase sponge, bat and ochre stars, staghorn, table and pillar coral, garden eel | plain white or grey alone (tinted per piece in play) |
| floor | at the liner: pure-blue staghorn and a big pure-blue mound | wrong palette: clash with the rest |
| set pieces | the liner | fits |
| set pieces | the pirate ship | fits from outside; inside the hold grey-green and smeary close up (the lossy atlas), one beam flat dark |
| set pieces | Atlantis | the plaza fits; the columns read as plain light blue (the tint swallows the paint) |
| set pieces | the docks' floor (the floor types, another builder's) | a hard-edged cracked-mud pattern |
| creatures | sardine, salmon, shark, orca, clownfish, leviathan, sea serpent, hippocampus, kelpie, deep spawn, ghost whale, river beast, reef-back, old one, submarine, mermaid | fit |
| creatures | remora | does not fit: dark and featureless, looks unfinished |
| creatures | anglerfish | pure black in plain light (check in the trench's light) |
| creatures | green turtle | glossy, plastic-looking shell |
| creatures | octopus | one arm straight out as a stick (alone; check in the sea) |
| creatures | spinosaurus; tuna | thin and flat-looking; the tuna's sickle fins drawn huge |
| title | helmet, computer | fit (baked atlas) |
| title | the boat | now baked (above) |
| title | the three figures | flat vertex colours (another builder's, report only) |
| title | the boat net | flat rope and steel (the bag is the net shader) |
| title | the fish logo | fits |
| 2D | sale, shop, run-over, choice cards, HUD | do not fit the brass panel: dark panels, the system font, flat mint and amber icons (planned for stage 2) |
| effects | static | fits |
| effects | bubbles | do not fit: big thin outline rings, flat, read as vector art |
| effects | splash meshes | plain white |
| effects | the leap, the red edge, the bubbles on eating | not caught in the pictures (rerun `--feed`: other sessions' half-written edits broke that run) |

Flat surfaces in a built sea and the title (`tests/material_scan.gd`): 470. Mostly the boat (now baked), the fishers'
gear (partly baked), the docks (deck, beams, piles, barnacles, mussels, floats, rubber, rust, pot wire, sailboats),
the outcrops (rock, rock dark, rock top), the boat net's rope and steel, the figures' every part, the splash meshes.

**Worst for the next art pass, in order**: 1. the docks (decks, piles, floats, sailboats); 2. the outcrop islet,
pillar and shard; 3. the reef props in flat saturated colours and the pure-blue staghorn and mound at the liner; 4.
the bommies and giant clam (noisy) and the cliffs (low resolution); 5. the small gear still flat (hooks, sinker,
bait, flags, the pale-blue box) and the boat net's rope and hoop; 6. the 2D screens (planned); 7. the figures
(another builder's); 8. the bubble rings; 9. the remora, the turtle's gloss, the octopus's arm; 10. the pirate hold
close up.

Shader programs added by this pass: none.

## Files changed by this pass

Scripts: `scripts/fish.gd` (`MOUTH`, `THICK`, `mouth()` by kind, `gap_to`), `scripts/species.gd` (`mouth` on five
kinds and its note; `long` on the female guppy), `scripts/creature.gd` (mouth by kind; floor kinds stand, walk and lie
on the floor), `scripts/life.gd` (`TAKES`, `JAWS`, `SOLID`, `BODY`, the two rules, `push_off`, `solids`), `scripts/arena.gd`
(the eating reach), `scripts/fishers.gd` (the hook's and bait's reach), `scripts/main.gd` (the reef-back's body,
`NET_REACH`, `_camera_place`, `_camera_clear`), `scripts/hud.gd` (the choice card's camera), `scripts/ruins.gd`
(`EXTRA`), `scripts/title.gd` (no vertex colour on the boat). Data and builds: `models/wreck_liner.json`,
`models/pirate_wreck.json`, `models/ruins_extra.json` (new), `tools/build_wreck.py`, `tools/build_pirate_wreck.py`,
`tools/build_shrimp_boat.py`, `models/shrimp_boat.glb` and its atlas, `tools/build_fishing_gear.py`,
`models/fishing_gear.glb` and its atlas, the two blends, `tools/web_excludes.sh`. Tests: the seven above.

## What changes how the game plays

- Eating: a fish crossing ahead must pass the mouth, not the middle of the head; big players eat from closer (an orca
  from about 1.6 m of the prey's body, not 2.7 m of its middle).
- Being eaten: a hunter's mouth must be on the player as drawn (0.1 of its length), not a metre off.
- Billfish players eat with the mouth, not the bill's tip; the Humboldt and giant squid bite with their arms' end.
- The giants, the submarine and the reef-back are solid; so is anything 1.5 times the player's length that is not
  hunting it.
- Small fish can come within 0.4 m of the liner and the pirate ship (up to 1.5 m before); Atlantis' paving stops them.
- The boat's net takes a fish only with its mouth at the hoop.
- The camera pulls in or rises at rocks and the floor.
- Floor animals stay on the floor (they used to hang over ledges).
