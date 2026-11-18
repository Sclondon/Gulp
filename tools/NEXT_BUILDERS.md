# Builders still to start (20 run at once; these wait for a free slot)

The user, 2026-11-18: "Lets also add plesiasours, ichtyosaurs, mosasuars, anomlaocaris, starfish, urchins, sea slugs,
crinoids, anemones, smalle bio luminescent animals, dumbo squid, cameroceras, trilobytes, sea horses, clams, oysters,
shrimps, walrus, sea lion, narwhal, several sea turtle types, pufferfish, sea weed, and a few more types of jellyfish".
(The sea lion is already built: `sea-lion`.)

Every prompt below starts with this paragraph:

> Read C:\Projects\FrontRangeInstituteGames\Gulp\tools\CREATURE_BRIEF.md (how a creature component is built, laid
> out and checked) and then C:\Projects\FrontRangeInstituteGames\Gulp\tools\GAME_MODEL_BRIEF.md (the game model at
> Twilight Princess weight, and the cartoon eyes at its end), and follow both: you are building NEW components, so
> build all three models from the start (full, game and low) with `game`, `game_mesh()`, `cartoon_eyes`, `eye_look`
> and `blink` in place, the full model never loaded when `game` is true. Your scratch folder is
> `...\scratchpad\new-<group>`. The user's words for these animals: (the line above).

## Left over from the game-model round (existing components: GAME_MODEL_BRIEF only)

- **aquarium-a**: `neon-tetra`, `guppy`, `betta`.
- **aquarium-b**: `goldfish`, `zebra-danio`, `corydoras`, `platy`.
- **odd**: `nudibranch`, `garden-eels` (the single eel `GardenEel`; the colony's mesh is light already), `ammonite`.

## New animals

- **reptiles**: `plesiosaur` (an elasmosaur: a small head on a very long neck, a barrel body, four long flippers
  that row in a figure of eight, a short tail; LENGTH 9; class Plesiosaur; `curl` bends the neck and body, plus `neck`
  a Vector2 that swings the neck on its own), `ichthyosaur` (dolphin-shaped reptile, a long toothed beak, a huge eye
  with a ring of bone, a crescent tail whose backbone runs into the LOWER lobe, four flippers; LENGTH 4; it swims like a
  tuna, side to side), `mosasaur` (a giant sea lizard: a long crocodile-like head with a double row of teeth, a
  barrel chest, four paddle flippers, a long tail with a downturned fluke; LENGTH 12; the apex hunter; `gape` very
  wide). Dark above, pale beneath, countershaded with faint bands. Working jaws on all three.
- **paleozoic**: `anomalocaris` (a segmented flattened body with a row of swimming lobes down each side that ripple in
  a wave, a fan tail, two big compound eyes on stalks, two spiny grasping arms curled under the head that reach and
  curl (`grasp` 0..1), a round plated mouth beneath; LENGTH 0.8), `cameroceras` (a giant straight-shelled nautiloid:
  a long tapering cone of a shell with growth bands, a squid-like head with big eyes, a hood and a crown of arms out of
  its wide end; it jets shell-first; LENGTH 6; as GameCommon's `ammonite` is, straightened: read it), `trilobite`
  (several types in one component as `sockeye-salmon` does stages: a smooth one, a spiny one, one with long cheek
  spines; a head shield with crescent compound eyes, a ribbed three-lobed body, a tail shield, many small legs and
  feathery gills beneath that walk in a wave on `phase`, antennae; it crawls on the bottom and can `enroll` 0..1 into a
  ball; LENGTH 0.12 to 0.3; origin on the ground).
- **turtles**: `sea-turtle` with types as `sockeye-salmon` does stages: green, hawksbill (a beak, overlapping shell
  plates with a serrated rim), loggerhead (a big head), leatherback (no plates: a ridged leathery back, the biggest,
  LENGTH 1.8). Front flippers that fly like wings on `phase`, hind flippers that steer, a beak that opens (`gape`),
  the shell's plates modelled as shallow steps and drawn in the shader. LENGTH about 1.0. Class SeaTurtle.
- **arctic**: `walrus` (a huge wrinkled bulk, a broad muzzle of stiff whiskers, two long tusks, small eyes, fore and
  hind flippers; it swims with its hind flippers side to side and rows with the fore ones; LENGTH 3; class Walrus;
  `gape`), `narwhal` (a mottled grey small whale with no dorsal fin, a rounded head, and the long spiral tusk straight
  ahead from the upper lip, about half the body's length again; flukes up and down as `dolphin` does: read it; LENGTH 4.5
  without the tusk, say how far the tusk reaches; class Narwhal).
- **puffer-horse**: `pufferfish` (a blunt boxy fish with a beak of four teeth, big round eyes, tiny fins that buzz; and
  `puff` 0..1 blows it up into a ball with every spine standing out; spotted; LENGTH 0.3; class Pufferfish; `gape`),
  `seahorse` (types: a common yellow one, a spiny one, a pygmy; it hangs upright: a horse's head with a tube snout and a
  coronet, a ridged ringed body, a belly, a prehensile tail that curls (`grip` 0..1), a small dorsal fin that buzzes
  and tiny ear-like pectorals; it drifts upright and bobs; LENGTH 0.15 tall; say which way is up and forward; class
  Seahorse; the snout's tip opens for `gape`).
- **echinoderms**: `starfish` (living ones that crawl: types: a five-armed sea star, a many-armed sunflower star, a
  brittle star whose thin arms writhe; arms that bend over the ground and curl at the tips on `phase`, tube feet
  beneath, colour types; origin on the ground; class Starfish; no gape), `sea-urchin` (a round test thick with spines
  that each sway and turn towards `threat` (a direction), tube feet; types: long-spined black, short purple, a pencil
  urchin; the spines as few triangles each as will do; class SeaUrchin), `crinoid` (a feather star: ten or twenty
  feathery arms round a small cup, cirri gripping beneath; arms that sway, curl up (`furl` 0..1) and, swimming, beat
  down in turn; and a stalked sea lily type on a long stem; class Crinoid). Eyes: none of these has any; leave the
  cartoon eyes out.
- **slugs-shells**: `sea-slug` (types beyond GameCommon's `nudibranch`, which you may read: a sea hare with its
  ear-like rhinophores and wing flaps, a blue dragon (Glaucus) floating upside down with its finger fans, a Spanish
  dancer that swims by rippling its red skirt; class SeaSlug; little eyespots only), `clam` (types: a giant clam with a
  fluted shell and a bright mantle, a scallop with a row of tiny blue eyes that SWIMS by clapping its shell, a razor
  clam; `open` 0..1 swings the shell about its hinge, the mantle and siphons showing; class Clam), `oyster` (a rough
  layered shell that opens a little (`open`), pearly inside, and a clump of several grown together as one piece; a
  pearl that shows when it is open (`pearl` true); class Oyster).
- **anemone-shrimp**: `anemone` (living sea anemones, types: a giant green, a tube anemone with long thin tentacles, a
  plumose anemone like a white feather duster on a column; tentacles that sway (the global `water_clock`, as
  `kelp` declares it) and `retract` 0..1 that pulls them in and closes the column to a blob; class Anemone; base at
  y 0. GameCommon's `clownfish` has a host anemone already: read it, do not change it), `shrimps` (types: a cleaner
  shrimp, red and white with long white antennae; a peacock mantis shrimp, vivid, with its two club arms that punch
  (`strike` 0..1) and its stalked turning eyes; a pistol shrimp with one huge claw; they walk and swim as
  `spot-prawn` does: read it and build on its approach; class Shrimp).
- **jellies**: more kinds of jellyfish, each its own component built on the way GameCommon's `sea-nettle` and
  `moon-jelly` are (read both: a bell that beats, strands that are simulated ropes or, where they are short and many,
  bent in the shader): `lions-mane-jelly` (a broad lobed bell with a great shaggy mass of fine tentacles, rust and
  gold, big: bell 1.5 m), `box-jelly` (a clear cube of a bell with four corners of long thin tentacles, fast and
  deadly, faint blue), `fried-egg-jelly` (a pale flat bell with a yolk-yellow dome in the middle, short frilly arms),
  `man-o-war` (it floats AT the surface: a blue-pink gas float with a crest above the water, long dark blue
  tentacles hanging far beneath; say where the waterline is). Each with `beat`, `phase`, `glow`, `step`, `low`, a
  game model and a low one; no eyes.
- **glow** (the user: "smalle bio luminescent animals", "dumbo squid"): `dumbo-octopus` (Grimpoteuthis: a soft
  bell-shaped body with two ear-like fins that flap, short webbed arms, big eyes; pink-orange; it hovers and flaps;
  LENGTH 0.3; class DumboOctopus; cartoon eyes suit it), `firefly-squid` (a small squid, LENGTH 0.07, covered in
  blue light organs that flash in patterns on `colour_phase`, with a school mesh as `sardine` has), `comb-jelly` (a
  clear lobed ctenophore with eight rows of beating combs that run with rainbow light, no stinging strands; LENGTH
  0.1), `pyrosome` (a long hollow glowing tube of a colony, open at one end, pale blue-green, that pulses with waves of
  light along it; LENGTH 2), and `sea-sparkle` (class SeaSparkle: a cloud of tiny glowing specks in one MultiMesh that
  flash brighter where something moves through them: `stir(at, radius)`; as `plankton`'s cloud is built: read it). All
  emissive (`glow` 0..2), made for the dark of the trench.
- **seaweed** (plants, as GameCommon's `kelp` and `sea-grass` are built: read both; MultiMesh, sway in the shader on
  the global `water_clock`, Blender-built pieces, near and far detail): one component `seaweed` (class SeaweedBed)
  with kinds: sea lettuce (bright green ruffled sheets), rockweed (olive, forked, with little air bladders), red
  algae (feathery crimson tufts), feather boa kelp (a long strap with a fringe), sea palm (a small palm on a stalk),
  and sargassum that FLOATS at the surface in golden mats with berry-like floats (say where the waterline is).
  `bed.plant(places, sizes, kinds)`. No game-model round needed: build them light from the start.
