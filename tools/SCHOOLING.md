# Schooling: how Gulp's sea life keeps together, and why

The user (2026-11-18): "fish should boid together, have mixed schooling dependet on species, some fish should have big
massive swarms like sardines (need to find performatn solution for having like hundreds), and different species need
unique behaviours (to a reasonable degree)".

Everything below the brief is Claude's design and Claude's picks; the user has not seen or played it yet.

## What is usually done (looked up first)

- **Boids** (Craig Reynolds, 1987): each animal steers by keeping clear of its neighbours, lining up with them and
  keeping together. The cost is the neighbour search: all pairs is n². The usual fixes are a **uniform grid or spatial
  hash** (each animal only looks in its own and the next cells), a **fixed most-neighbours count** (starlings heed
  their 6-7 nearest), and **thinking in turns** (only part of the flock decides each frame; all of it moves every
  frame on its last decision). GameCommon's `flock` component already does all three.
- **ABZÛ** (Giant Squid; GDC 2017 "Creating the Art of ABZÛ", Matt Nava; the programmer Brian Balamut on the fish):
  "tens of thousands" of fish, made affordable two ways: the fish are spatially sorted so each checks only near
  neighbours, and they are **not skinned**: the swimming is a few sine waves in the **vertex shader** (a skeleton per
  fish would have capped a scene at about 100). Godot's own tutorial "Animating thousands of fish with
  MultiMeshInstance" is the same idea: one MultiMesh, one draw, a per-instance phase in INSTANCE_CUSTOM so they do
  not swim in step, and a hand-set custom AABB when instances move far apart (or the MultiMesh is wrongly culled).
- **Leader + followers / level of detail for crowds**: when a swarm is far bigger than a CPU can steer, simulate a
  few dozen **guides** and let the many bodies follow them at fixed offsets with a little noise; a vector field or a
  noise texture driving the bodies on the GPU is the other way (GPU boids with compute shaders are out: the web build
  is WebGL 2, no compute).
- Real bait balls (for the look): a polarised school that tightens into a turning ball when attacked, parts round a
  predator in a "vacuole" and closes behind it, and is driven up to the surface by the hunters below; dolphins,
  sailfish, tuna, sea lions and orcas take turns rushing through it.

Sources: Godot docs, "Animating thousands of fish with MultiMeshInstance"
(docs.godotengine.org/en/stable/tutorials/performance/vertex_animation/animating_thousands_of_fish.html);
GDC Vault 1024409 "Creating the Art of ABZÛ"; the Audiokinetic "10,000 fish" ABZÛ article and the Kill Screen
interview on its fish; Reynolds 1987; Ballerini et al. 2008 (seven neighbours).

## Decision: three sizes of group, three ways

| Group | How many | How | Why |
| --- | --- | --- | --- |
| **Swarms**: krill, sardines, anchovies, lanternfish, mackerel | 160 to 1,600 each | GameCommon Flock in a new **riders** mode: 16-40 guide boids are simulated (spatial hash, 6 neighbours, a sixth of them thinking each frame); each guide carries a cloud of riders. The riders' transforms are the identity and never change; their custom data is their place in the cloud and their guide's index + a seed. The Flock's own shader (flock.gdshader, which every school already used) reads the guides' places, headings, frights and beats from two uniform arrays and puts each rider there, swimming. | The CPU pays for the few dozen guides, not the riders: a swarm of 1,600 costs what 40 boids cost. No new shader program (a new one freezes a browser for about a second), one draw per swarm. |
| **Small schools**: neon tetras, zebra danios, piranhas | 22-36 | Flock as before, one body per boid | Small enough that full boids are cheap and look best. |
| **Creatures in groups**: every single animal whose kind has `social` | 2-9 a group | Creature steers among the members of its own Group only (keep clear, line up, keep together, make for the group's shared goal); Life updates each group's middle and heading once a frame | Groups are small and fixed at stocking, so no search at all: a member looks at at most eight others. Far-off creatures are still stepped one frame in eight. |

Alternatives weighed:
- *All riders steered on the CPU* (each fish a boid, 1,600 per swarm): the Flock costs about 8-15 µs a boid in
  GDScript, so 20-25 ms a swarm. Out.
- *Riders placed on the CPU each frame* (guides simulated, each rider's transform written to the MultiMesh buffer):
  a buffer of 1,600 × 20 floats rebuilt in GDScript each frame is about 1-2 ms a swarm. Out.
- *A noise field or texture moving every fish in the shader, no guides*: cheapest of all, but the CPU would not know
  where a fish is, so it could not be eaten one by one, and the swarm could not flee a hunter or split round the
  player. Out for the bait-ball fish (the guides give exactly that), but it is close to what the rider's own drift is.
- *GPU boids (compute)*: not in GL Compatibility / WebGL 2.

## How a swarm works (flock/flock.gd, `rules.riders`)

- Guides: at most `Flock.MOST_LEADS` (48). They keep a cloud's width apart (`separation_distance` = 1.25 × the cloud
  radius), all in one body (`gather`), flee predators and pass a fright on (`alarm_spread` 0.85).
- Riders: rider *k* of guide *g* is instance *k × guides + g*, so drawing fewer (`rider_layers`; Life draws 60% past
  12 m, 35% past 22 m) thins every cloud evenly. Each rider drifts slowly round its place (`rider_drift`), its heading
  wanders a little off its guide's, each its own size (`size_variation`) and beat phase.
- A frightened guide's cloud spreads (`rider_fright`): the swarm flashes outwards where it is attacked.
- `shove`: up to two spheres the riders are pushed out of in the shader (the player's body; a hunter dashing
  through), so the swarm parts round them and closes behind.
- Eating: `nearest_rider(point, within)` looks only at the guides near the point and only at their own riders.
  `take_rider(i, seconds)` hides that one (its custom w goes negative, the shader collapses it); when its time is up it
  comes back on the guide furthest from `shove[0]` (the far side from the player), so the swarm keeps its numbers and
  nothing pops up in front of the mouth that took it.
- Culling: the MultiMesh's `custom_aabb` is the guides' box grown by a cloud each frame.
- When the swarm is hunted (a pack hunter circling it, Life's `school.hunters`), Life raises `gather`, adds an
  `orbit` round the swarm's middle and drives its centre up towards the surface: a turning bait ball.

## Groups and habits (scripts/creature.gd, species keys)

Species keys (all optional): `social` ("school" tight and lined up, "shoal" loose and milling, "pair", "harem" (the
biggest leads, the rest follow it), "pod" (and they go up for air together); left out: "solo"), `group` [from, to]
members, `mix` (kinds with the same mix are grouped together), `habit`, `breathes`, `leaps`, `visits` (goes to a
cleaning station), `nocturnal` (rises into the open water at night, if scripts/day.gd is there).

Habits: `ambush` (holds at a lair watching, mouth working; the player within reach ahead: mouth wide open for 0.6 s
(the warning, counted as a threat so the red edge and sonar show it), then a 0.55 s lunge, no chase), `stalk` (circles
the player 2.5-4 s, closing, then the usual chase), `pack` (rings a swarm it can eat, taking turns to dash through it
mouth open), `filter` (cruises through krill, plankton or a small-fish swarm mouth wide, taking what it passes),
`graze` (nose down to the floor or a rock face nibbling, then on with its group), `cleaner` (bobs at a station; tends the
client's head), `shy` (a fright of its own: pufferfish puff and cannot be eaten while puffed, clams shut, urchins point
their spines at the player, feather stars and sea lilies furl, razor clams dig in), `hop` (a scallop claps away in
jerks), `cling` (seahorses hold on, tails curled, and move house now and then), `home` (clownfish, garibaldi keep to
their spot), `drift` (comb jellies, pyrosomes, ammonites, dumbo octopus: carried along, bobbing), `sting` (lionfish face
what comes near, fins out; touching one, too big to eat, drains the player's burst and most of its speed and pushes it
off: a hurt, not a death, Claude's call), `display` (bettas flare), `strike` (mantis and pistol shrimps punch and snap
at what comes close; cuttlefish and gar strike as they close on prey), `float` (sea otters lie at the surface).
Breathers go up when their breath runs out, lie at the surface a few seconds, and dive (pods together); leapers (flying
fish (and they glide), dolphins, mahi, arowana) leap out near the surface, more often when fleeing. Anything with
`arch` arches as it pitches; anything with `eye_look` watches the player when it is near.

## Measured (2026-11-18, RTX 4080 desktop, headless, script time)

- The 1,600-sardine bait ball (40 guides): 0.10 ms a frame; a 640 swarm (32 guides): 0.09 ms; the ball with a fish
  inside it eating: 0.13 ms. Life's own school work (eating, roaming): 0.01-0.05 ms in all.
- "fish" (all the creatures, with groups and habits) in 120 s bot runs: 2.1 ms, against 1.9-2.3 ms before the change
  (the machine was shared with other sessions; repeated runs vary by 1 ms or more).
- Windowed at 390x844 beside the ball, vsync off: about 5.5-6 ms a frame in all. Not measured on a phone or in a
  browser.

## Whose calls

- The user's: the brief above.
- Claude's (change freely): the rider approach and every number in Life's `*_SWARM` constants; which kinds school,
  shoal, pair, form harems or pods, and the mixes (reef roamers: the tangs, surgeonfish, convict tangs and three
  butterflyfish together, after the real mixed foraging schools of convict tangs and surgeonfish; yellowfin and bigeye
  tuna together, as under drifting objects; carp with the koi; goldfish with fantails; guppies with platies; the two
  corydoras); garibaldi as territorial loners (true to life) though the brief's example named them a shoal; the
  lionfish sting as a hurt, not a death; ambushers lunge only, without the old chase.

## Pulling back to GameCommon

`flock/flock.gd`, `flock_rules.gd` and `flock.gdshader` gained the riders mode (and `middle()`); with `riders` 0 they
behave as before. Worth pulling back to `GameCommon/godot/flock` if it is kept (with `move_boid`, which was added
earlier). GameCommon itself was not touched.
