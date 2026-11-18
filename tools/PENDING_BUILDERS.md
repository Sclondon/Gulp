# Model builders still to start (the limit of 20 at once was reached)

Each prompt starts: "Read <scratchpad>\CREATURE_BRIEF.md first and follow it exactly. The user has since also asked
for tropical reef fish: 'butterflyfish, lionfish, parrotfish, wrasse, surgeon fish, clownfish, blue tang, multiple
buttflyshi types, angelfish' and 'cuttlefish'."

1. `cuttlefish` (class Cuttlefish, 0.4): broad flat mantle, fin skirt all round rippling, W pupils, eight short arms
   bunched ahead, swims ARMS FIRST (arms at -Z), `strike` tentacles, skin patterns `zebra`, `cloud`, `blanch`,
   `flash()`, `spread`; example: humboldt-squid. No ropes.
2. `butterflyfish` (class Butterflyfish, 0.18, enum Type: threadfin, raccoon, copperband, longnose, +bannerfish) and
   `angelfish` (class Angelfish, 0.35, Type: emperor, queen, French). Types as sockeye-salmon does stages. Pectoral
   rowers. gape + curl. 8-15k triangles, low 800.
3. `lionfish` (class Lionfish, 0.35, `spread`, spine reach const), `parrotfish` (class Parrotfish, 0.5, the beak,
   gape bites), `wrasse` (class Wrasse, 0.25, Type: cleaner, moon/bird). gape + curl.
4. `surgeonfish` (class Surgeonfish, 0.25, Type: yellow tang, powder blue/convict), `blue-tang` (class BlueTang,
   0.25, + school mesh as sardine), `clownfish` (class Clownfish, 0.09) with its host anemone in the same component
   (class ClownfishAnemone, 0.5 m, sway from world position and global `water_clock`). gape + curl.

(2 is started.) The user then: "there should also be a mangrove / river entrance area for fresh water fish as well,
arowana, pirahna, cat fish, trout, pike, perch, walleye, carp, koi, gar, lampray":

5. `arowana` (class Arowana, 0.9: silver/Asian arowana, big scales, upturned trapdoor mouth with chin barbels, long
   dorsal and anal fins set far back, it leaps), `piranha` (class Piranha, 0.3: red-bellied, deep body, underbite
   with triangular teeth showing on gape; + school mesh), `northern-pike` (class NorthernPike, 1.0: duck-bill snout,
   olive with pale bean spots, dorsal far back).
6. `yellow-perch` (class YellowPerch, 0.3: gold with dark bars, orange fins, two dorsals), `walleye` (class Walleye,
   0.7: glassy eye, olive-gold, white tail tip, fangs), `gar` (class Gar, longnose/alligator gar 1.4: long toothed
   snout, armoured diamond scales, fins far back).
7. `carp` (class Carp, 0.7, enum Type: common carp, and koi kohaku / sanke / showa / ogon as colour types; barbels,
   big scales, long dorsal), `lamprey` (class Lamprey, 0.7: eel body, seven gill holes, the round sucker mouth of
   teeth: `gape` opens the disc; rope or shader body).
8. Scenery: `mangrove` (prop roots arching into the water, trunks and canopy above the surface, pneumatophores,
   fallen leaves, a river mouth's muddy banks; MultiMesh-able pieces, spheres/capsules for roots) — in
   `files/plants/mangrove`.

(1 cuttlefish is started.) The user then: "tetras, guppys, bettas, and other commmon small aquarium fish as well":

9. `neon-tetra` (class NeonTetra, 0.035, + school mesh; cardinal as a type), `guppy` (class Guppy, 0.04, male fan
   tail types + plain female), `betta` (class Betta, 0.065, long flowing fins that trail and ripple, colour types,
   `flare` 0..1 gill covers and fins).
10. `goldfish` (class Goldfish, 0.15, common + fantail types), `zebra-danio` (class ZebraDanio, 0.045, + school
    mesh), `corydoras` (class Corydoras, 0.06, bottom, barbels), `freshwater-angelfish` (class FreshwaterAngelfish,
    0.12 tall triangle), `molly-platy` (class Platy, 0.05, colour types).

The user then: "plankton, and krill also", "ammonites":

11. `krill` (class Krill, 0.05: Pacific krill, clear pink-red, big black eyes, beating swimmerets, + a very light
    school mesh for swarms of hundreds), `plankton` (class PlanktonCloud: a drifting cloud of copepods, diatoms and
    larvae drawn as many tiny instances/particles from a few Blender-built specks, glittering; API to place clouds and
    take a bite out of one), `ammonite` (class Ammonite, 0.5: a ribbed coiled spiral shell with a pearly sheen and
    iridescent bands, a squid-like head with eyes, a hood and about ten short tentacles out of the opening; it bobs
    and jets shell-first backwards; `withdraw` 0..1 pulls it into its shell).

Started already: tunas; mackerel/wahoo/barracuda; marlin/mahi; sea bass/grouper/kelp bass;
snapper/rockfish/surfperch/garibaldi; sharks (+whale shark); halibut/bat ray/stingray; anchovy/prawn/lobster/crab;
nudibranch/garden eels; octopus; baleen whales (+fin whale); sperm whale/orca/dolphin; seal/sea lion/otter;
kelp/sea grass; sea-floor-props (+coral); jaws for tuna/loach/catfish; jaws for sardine, sailfish, swordfish;
manta/devil ray/eagle ray.

12. `horseshoe-crab` (class HorseshoeCrab, 0.5: the domed horseshoe shell, the spiked tail, ten legs under it; walks on the bottom on `phase`).
13. Trench fish (the user: "with trench fish, angler fish, and other types"): `deep-anglerfish` (lure that glows), `gulper-eel`, `viperfish`, `lanternfish` (+ school mesh, light organs), `dumbo-octopus`, `vampire-squid`.
14. Not models: the online arena with a high score.
