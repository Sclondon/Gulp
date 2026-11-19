# The water's effects: the leap, splashes, bubbles, burst, light shafts, caustics, the day

Done 2026-11-18 by an agent, while the user was play-testing the web build.

## The user's words (2026-11-18)

- "and the splahs and jump mechanics are not working correctly"
- "and you shloud leave a bubble trail / distortion in the water, moras you swim and boost, boost should change fov
  and speed lines, the god rays need to be in 3d space on just on the screen overlay, and there should be caustics
  effects on the floor (in some areas) ... Ther should be a day and night cycle (dont make night too dark)"
- Earlier: "And you should be able to jump above the waters surface ala salmon run", "The bubble and particle and
  splash effects should be based on the salmon run ones in game common".

## What was wrong with the leap and the splash (found by pictures from the game's camera, tests/fx_strip.gd)

1. **Without the burst it never leapt.** The leap needed 0.9 of the fish's pace; at the speed lever's starting
   place (0.7) it swims at 0.3 + 0.85 x 0.7 = 0.895 of it. Swimming up it only stuck under the surface.
2. **The camera came out of the water whenever the fish swam near the top** (`_camera_place` returned any point
   above the surface as it was). It then looked down through the surface at a fish it could hardly see (a sardine
   at the top was invisible, the picture was a blue wall).
3. **Big fish never got clear of the water.** Thrown out only by their own speed (slow for their size), an orca rose
   1.6 m, under a third of its length; a sardine rose three lengths.
4. **The camera in a leap shot up**: it went behind the fish along its nose (which swings from up to down) and then
   above the higher of that and the fish, plus more: 15 m over an orca's leap, still above the water seconds after
   the orca had gone back in, looking down at the waves.
5. **The splash was the wrong size at both ends.** Its size was (length / 1.8)^2, and Salmon Run 2's splash makes
   its width go by the root of that and its height by it whole: for a sardine a speck nobody could see; for an
   orca a column of water 40 m high, 4 m wide, its drops flung at 40 m/s as low-poly chunks the size of boulders
   hanging in the sky.
6. **The fish could be invisible for the whole leap**: the blink while it is safe (first 3 s of a run, after
   growing) was only updated under water, so a fish that went up hidden stayed hidden until it was back in.
7. Back in from a leap it went on diving at the angle it came in, straight to the floor.
8. No bubbles under the water where it went in.

## What was changed

- `Player` (leap code only): `LEAP_PACE` 0.75. A leap now goes at least `LEAP_LEAST + LEAP_PER_LENGTH x length`
  (0.25 m + 0.9 lengths) high on a burst, three quarters of that without (a sardine about 0.4 m, a tuna 1.5 m, an
  orca 3.8 m over the water at the top). The blink is kept up in the air. For 0.9 s after going back in it eases
  out of a steep dive to -0.3 rad unless the stick is pushed up or down.
- `main.gd` (marked "water fx"): under water the eye stays at least 0.5 m under the surface (below the waves, which
  are about ±0.3 m). In a leap it is behind the fish along its way over the water (not along its nose), turned
  0.45 rad to one side so that the arc is seen, `0.6 + 1.9 lengths` back, `0.35 + 0.5 lengths` over the water and
  rising with the fish by 0.55 of its height; it aims a little under the fish, so the fish flies in the top half of
  the picture above the control panel (checked at 1280x720 and 390x844). It follows at 8/s in the air and while
  getting back under, 5/s otherwise (it was 12 in the air).
- `Splash.start(at, size, water, foam, how_hard)`: everything in proportion to `size` (width, height, ripple rings,
  where its drops start), its drops thrown by the root of size x strength (so they rise in proportion), drops
  growing only by size^0.6 (more of them, not boulders), its time slowed by the root of size. `Effects.splash`
  gives size = clamp(length / 1.8, 0.14, 4)^0.9 (a sardine's can be seen; an orca's is about 7 m across), strength
  0.55 going out (as Salmon Run 2's take-off), 0.7 to 1.6 coming in, by how fast it was falling for its size.
- A gush of bubbles under the water where it goes in (fewer where it comes out).

## Each effect, how it is drawn, and what it costs

| Effect | How | Draws | New shader programs |
| --- | --- | --- | --- |
| Bubble trail | `Effects._trail` (26 bubbles, 1.7 s) from the tail while swimming; `_stream` (60, 1.3 s, bigger) while bursting. CPUParticles3D, rising (gravity +1.2, damping), swelling then shrinking. Size 0.02 to 0.17 m by length | 1, 2 in a burst | `shaders/bubble.gdshader` (Salmon Run 2's ring-and-glint bubble, unused until now; given `ceiling`: none above the surface, and `near_cut`: none within 0.45 m of the eye) |
| Bubbles of a meal, of a plunge | the same shader (the meal's were white spheres) | 1 each, while they last | - |
| Churned water behind the fish | `Effects._churn` keeps where the tail was every 1/16 s (8 places, 0.5 s), with how hard it was going (nothing idling, most in a burst); each frame the live ones are put on the screen and passed to the post shader (`haze`, 8 x vec4), which wobbles the picture round each by a little (0.0022 of the screen). The panel is its own Control over the picture, so it is not touched | 0 | 0 (in `post.gdshader`) |
| Burst: wider view | `Effects.fov_kick`, eased to 10 degrees in a burst (in at 5/s, out at 2.5/s); main adds it to its fov | 0 | 0 |
| Burst: speed lines | `post.gdshader` `streaks`: pale dashed spokes running outwards towards the corners (110 spokes, a third lit), by how far over cruising speed it is, eased; only under water | 0 | 0 |
| Light shafts | `scripts/light_shafts.gd` (`LightShafts`, made by Sea): one MultiMesh of 49 long strips, one per 5 m square of the world round the eye (a quarter of the squares have none), each in its own place in its square so they stand still as the eye moves (parallax checked in two pictures a second apart). They hang from the surface along the light bent by the water (Snell, 1.33), reach the floor, turn about their length to face the eye (`shaders/light_shaft.gdshader`, added light, soft sides, fade with depth (13 m), near the eye (1 to 5 m) and far (18 to 40 m), each breathing and swaying). Laid out again only when the eye crosses into another square. Fainter as the eye goes from 14 to 34 m deep, none deeper (so none in the trench or deep open water), none above water. The old flat shafts in the post shader are gone (its `shafts` uniform is left, unused) | 1 | `light_shaft.gdshader` (drawn from the first frame, at strength 0 above water, so a browser makes it behind the title) |
| Caustics | one pass over the picture (2026-11-18, the user: "The caustics need to appear on fish and props etc"): `scripts/caustics.gd` (`Caustics`, made by `Sea._caustics`) is a full-screen quad drawn first among the see-through things with `shaders/caustics.gdshader`, which reads the depth buffer, rebuilds each pixel's place in the world and its facing (from neighbouring pixels), and lays the net (two panning copies of `Sea.caustic_texture`, the sand's old pattern, scale, drift and `water_clock`) over the floor, rocks, plants, wrecks, piles and every animal: brighter lines and darker cells on what faces up, full in the shallows, 0.3 at 30 m, none below 45 m or above the surface, fading 25 to 40 m from the eye, the fog's share of a pixel left alone. Strength by the hour from `Sea._look` (a third at night: the moon's). `-- --no-caustics` leaves it out (pictures, costs). Pictures: `tests/caustics_view.gd`. CLAUDE.md, "Decision: caustics as one pass over the picture" | 1 | 1 program (plus a copy of the depth and colour buffers after the solid pass) |
| Day and night | `scripts/day.gd` (`Day`, static): `Day.now()` 0..1 (0 midnight), `Day.hour()`, `Day.light()` 0..1, `Day.glow()` (dawn/dusk), `Day.sun_direction()`, `Day.light_colour()`, `Day.sky_colour()`, `Day.hold(hour)`; `--hour=<0..24>` holds it. Sea moves it on and relights 4 times a second (`Sea._look`): the sun or moon's direction, colour and strength, the sky and air fog above water, the water's fog and ambient light under it, the surface's colours, the shafts' slant, colour and strength, the caustics' strength | 0 | 0 |

Frame cost (60 s bot, `--disable-vsync`, 1280x720, RTX 4080): 7.4 ms before; 6.6 and 6.9 ms after. Other sessions
changed the flocks and fishers between the runs (flocks went from 0.81 ms to 0.00), so this says only that the
effects did not add a measurable amount; their own script work is a few dozen sums a frame (8 projections, one
lay-out of 49 shafts when the eye crosses 5 m, the light 4 times a second). Draws added: 2 steady (trail, shafts),
up to 2 more in a burst or a splash.

## The day's numbers

- A whole day is `Day.LENGTH` = 540 s (9 minutes). A game starts at 9:30. Sunrise 6:00, sunset 19:00; dawn and
  dusk light over about an hour and a half round each.
- Midday: the sun 62 degrees up, colour (0.62, 0.82, 1.0), energy 1.5; under water ambient (0.3, 0.5, 0.8) x 0.95,
  fog (0.012, 0.07, 0.17). (As the game was.)
- Midnight: the moon, at least 20 degrees up, colour (0.5, 0.62, 0.95), energy 0.6; under water ambient
  (0.22, 0.34, 0.62) (about 70 % of midday's brightness), fog (0.008, 0.042, 0.11); the surface's colours at half.
  Glowing animals stand out by themselves. Above water the sky is (0.1, 0.15, 0.3).
- Dawn and dusk: the light and sky go warm (sky to (1.0, 0.56, 0.32)), the sun's energy is held up a little.
- The light never comes from lower than 20 degrees, so nothing is lit side-on.
- For the panel later: `Day.hour()`.

## Checked

- Pictures from the game's own camera (`tests/fx_strip.gd`, kept: a strip of pictures at given times, with
  `--leap --hold-up --burst=<from> --side --floor --hour=`): the leap of a sardine, salmon, tuna and orca, out, at
  the top and back in, at 1280x720 and a tuna at 390x844; cruising and bursting from behind and from the side;
  shafts from the side a second apart; caustics in the sea grass (4 m) and on the sand flats (10 m, faint), none in
  the open ocean (66 m); under water and above at 6:36, 12:00, 18:36 and midnight; the title at noon, 19:00 and
  midnight; one leap with `--rendering-driver opengl3_angle` (the splash, bubbles, streaks and shafts draw).
- `sh tests/smoke.sh` GULP SMOKE PASSED, `sh tests/touch.sh` GULP TOUCH PASSED.

## Not checked

- Nobody has played it by hand: how the leap and the burst feel, whether the speed lines or the shimmer are too
  much.
- Phones and a real browser build (only ANGLE on the desktop): the cost of the shafts' added light over the
  screen, and of the longer sand shader, on a phone GPU; whether `light_shaft.gdshader` is really made behind the
  title in a browser.
- Caustics: their facing comes from neighbouring pixels, so on thin, busy plants it speckles; not tried in a browser or on a phone. The plankton specks do not stretch in a burst.
- Sunrise and sunset were looked at once each; dusk is a bit grey.

## Whose calls

The user's: a bubble trail and distortion, more on a burst; a burst changes the fov and shows speed lines; shafts in
3D; caustics in some areas; a day and night, night not too dark; the leap as in Salmon Run.

Claude's (change freely): everything in the numbers above; 9-minute day from 9:30; the moon as the night's light;
the leap's least height in lengths; the eye's place in a leap (to one side, low over the water); the eye kept under
the surface while swimming; the shafts' grid, look and depth fade; caustics only in the sand's shader, by depth;
streaks as pale dashes; the bubble shader for every bubble.

## Surf and rogue waves (2026-11-18)

The user: "Can we work on simulating crashing waves by the shoreline, and also rogue waves? Looking up solutions for
actual wave cresting etc so we can enhance our water / ocean system". Built by an agent. Concept first:
`tools/art_src/concept_waves_shore.png` (a green plunging breaker, a white bore behind it, lacy foam, swash on wet sand)
and `concept_waves_rogue.png` (one dark wall far over a rolling sea, a white breaking lip, streaks down its face, fish
tumbled in the surge under it), both made in the set-pieces Gemini conversation in the art-style brief.

### What was found (research)

- **Gerstner (trochoidal) waves** are the usual real-time wave: each point moves in an orbit, so the water bunches at
  the crests (sharp) and spreads in the troughs (round); steepness Q sets how far; at Q·A·k = 1 the crest becomes a
  cusp, past it the surface loops. GPU Gems 1, ch. 1 (Finch, "Effective Water Simulation from Physical Models"):
  https://developer.nvidia.com/gpugems/gpugems/part-i-natural-effects/chapter-1-effective-water-simulation-physical-models
- **Shoaling**: in shallow water waves slow (c = sqrt(g h)), so they shorten and their fronts swing round parallel to
  the depth lines; their height grows as h^-1/4 (Green's law); they break when the height reaches about 0.78 of the
  depth (McCowan's limit, most reliable on gentle slopes), then go on as broken water whose height stays about in
  proportion to depth (the saturated surf zone). Steep beaches give plunging breakers (a curling lip), gentle ones
  spilling. Sources: https://arxiv.org/pdf/1601.06822 (solitary wave shoaling and breaking),
  https://journals.flvc.org/jcr/article/download/77840/75280/81548 (McCowan's criterion tested on a beach).
- **Breaking in graphics**: Fournier and Reeves, "A Simple Model of Ocean Waves" (SIGGRAPH 1986): Gerstner orbits
  squashed by depth and tilted forward as the wave shoals, so the crest leans over its face and breaks:
  https://ohiostate.pressbooks.pub/app/uploads/sites/45/2017/09/fournier-reeves.pdf
- **Foam from folding**: Tessendorf, "Simulating Ocean Water": where the Jacobian of the sideways displacement falls to
  0 the surface folds over itself, and that is where crest foam and spray go:
  https://jtessen.people.clemson.edu/reports/papers_files/coursenotes2004.pdf
- **Games**: Crest (Unity) makes shoreline foam from shallow water and lays its ocean as LOD rings round the eye
  (SIGGRAPH 2017/2019 talks): https://crest.readthedocs.io/en/4.20/user/water-appearance.html. Shore waves in games are
  usually driven by a baked map of the shore: Assassin's Creed III by a 512x512 shoreline mask (a forum report,
  https://forums.unrealengine.com/t/shore-detection-for-water-surfaces/64505/29), a hobbyist ocean by a distance field
  to the shore that picks skewed wave shapes and foam (https://www.gamedev.net/blogs/entry/2249487-ocean-rendering).
  Naughty Dog's water talks (https://gdcvault.com/play/1015517/contactUs) are summaries only: no details of breaker
  sheet meshes were found to follow, so none are used.
- **Rogue waves**: a single crest far over the sea round it, mostly from wave groups focusing (longer, faster waves
  catch shorter ones and add up at one place and time, then spread again), also from modulational instability and
  currents. Kharif et al. 2008: https://data-ww3.ifremer.fr/BIB/Kharif_etal_JFM2008.pdf ; Pelinovsky et al. 2011:
  https://nhess.copernicus.org/articles/11/127/2011/nhess-11-127-2011.pdf . In games: a scripted bigger swell.

### Decision: shore-distance surf on rings round the eye, a scripted rogue swell (Claude's pick)

- **What**: (1) the shores are baked once at start into a small picture (`Surf.bake`: a texel every 2 m, 143x161,
  half floats: shore distance, depth, how open to the sea; about 90 ms); (2) one train of Gerstner waves runs in to
  every shore at once, its phase the distance to the shore, squeezed as the water shoals (2 sqrt(d x 14) within the
  14 m beach strip: the travel time of a wave over an even slope), its height by Green's law, breaking at McCowan's 0.78
  of the depth and capped there after, steeper as it shoals, its crest thrown forward as it breaks (Fournier-Reeves);
  foam from the fold (the Jacobian), the bore of broken water and its trail, lace, a white line along each standing
  crest; it runs up the sand and back (the swash) because the water mesh lies over the land too and the sand hides
  what is under it; (3) the water mesh follows the eye as five rings of squares, 0.5 m within 16 m, doubling out to
  256 m (`Sea._rings`, about 33,000 triangles, moved in 8 m steps so nothing swims; the seams are fans, no cracks);
  (4) a rogue wave is one travelling hump (sech squared) with a trough before it, 30 m across, growing and fading over
  its 30 s life (a focusing group), breaking at its top. `Surf` (scripts/surf.gd) is the CPU copy of the same sums:
  `Sea.surface_height`, `Sea.surge`, `Sea.rogue_wave`.
- **Why**: GL Compatibility on phones has no compute shaders, so no FFT ocean and no simulated shallow water; a
  vertex-shader sum is a few dozen operations a vertex; the bay's real shore is already baked (Bay), so a shore map is
  nearly free; rings put the fine mesh only where the eye can see a wave break (the old fixed sheet of 4 m squares
  could not draw a wave 4 m long).
- **The practice it follows**: Gerstner waves (GPU Gems), depth-driven shoaling and breaking (Fournier-Reeves,
  McCowan), Jacobian foam (Tessendorf), a baked shore distance or mask (AC III, Crest's depth cache), LOD rings round
  the eye (Crest, geometry clipmaps), rogue waves as a scripted swell.
- **Alternatives**: FFT waves (compute or many render passes: too heavy for phones, and blind to depth); a
  shallow-water simulation on a grid (compute, memory); breaker sheet or rolling curl meshes along the shore (art-heavy,
  and must follow every winding of the real coast; could be laid over the breaking line later); a finer fixed mesh
  everywhere (over 100,000 triangles); a shore strip mesh (cracks where it meets the coarse sheet, and no help for a
  rogue wave in open water).

### The numbers (Claude's picks, change freely)

`Surf`: HEIGHT 0.85 m (amplitude at the beach strip's 5 m depth), LENGTH 14 m, PERIOD 7 s, REACH 28 m from the shore,
BREAK 0.78, SWASH 0.3 m; sets of bigger waves every few (0.5 to 1.1 times). The surf starts to break about 2.5 m deep
(6 to 7 m out on the eased beach) and is broken water inside 5 m. Rogue: 4.5 m high, 30 s, 5.5 m/s, 6.5 m long, 30 m
wide; one comes by itself every 240 to 480 s, passing near the eye at its highest, over water at least 8 m deep and
clear of the surf (none in `--check` runs; `-- --rogue` sends one across the fish, highest 15 s later). Its push: up to
1.6 m/s along, 1.8 m/s up its front, fading over 4 m of depth; the water under it darkens by up to 45%. The shader's
numbers come from `Surf.dress`; `shaders/surf.gdshaderinc` repeats the sums: keep the two alike.

### What uses the surface as drawn now

`Sea.surface_height(x, z)` (about 12 us a call): the player (leaping out, landing, kept under the surface, which may now
be higher under a crest or lower in a trough), the camera (kept under it, over it in a leap, `set_above`), the effects
(spray, splashes, plunge bubbles, the speed streaks and shimmer), the title boat (rides it: pitch and roll from four
points, eased). The rogue wave's `Sea.surge` pushes the player and the awake animals within 8 m of the top (`Main`,
`Life`). Still on the flat `Sea.SURFACE`: animals' own ceiling, the fishers' bobs and skiffs, the bubbles' ceiling, the
light shafts, Biomes and scenery placement.

### Other changes

- `water.gdshader` writes depth (`depth_draw_always`): without it a tall wave's far side, drawn in the same mesh in no
  particular order, showed its underside through the near face. Seen from above, transparent things under the water
  behind the surface may now be hidden by it.
- With the eye above the water, a back face is drawn as water (an overhang), not as the bright ceiling.
- Whitecaps and drifting patches are left out of the surf, which has its own foam; the small ripples give way there.
- Under water: the surf's foam is a brighter roof, the troughs darker bands; bubbles churn round an eye under breaking
  surf (`Sea._surf_bubbles`, 70, the bubble shader); a rogue wave overhead darkens the water.
- `surf_debug` (1 the baked shores as colours, 2 the surf's weight, shoaling and phase, 3 front and back faces);
  `tests/surf_shot.gd --debug[2|3]` sets it.

### Checked

- `sh tests/smoke.sh` passes with six new checks (`checks.gd` `_waves`): a gentle swell out at sea, a larger rise and
  fall at a beach, the surf only near the shore, a leap clear of the waves and back in, a rogue wave 4 m over the sea
  pushing near the top and not 30 m down, gone after its life.
- Pictures (`tests/surf_shot.gd`: a fixed eye out from a shore or anywhere, a forced rogue wave, strips over time): the
  surf rolling in and breaking at Santa Cruz's beach, a rogue wave coming at the eye from 18 m, under the surf, the
  title boat riding the swell, a salmon's leap. Faces checked by colour (the rings wind as Godot's front faces, up).
- Cost (`-- --perf=beach,start,title`, 390x844, desktop, other sessions' Godot runs going at the same time both times,
  so the frame times are not comparable): the water 20,000 triangles before, 36,000 after; GPU 1.09 / 1.14 / 2.08 ms
  before, 0.93 / 0.81 / 1.24 ms after; no measurable cost added. Not tried on a phone.

### Rough

- The surf zone is narrow: the bake eases the beach to 5 m deep 14 m out, a steep beach, so real breaking happens in
  the last 6 m; the waves are bigger than real so that the surf reads.
- (Fixed by "Barrels" below, at two breaks and on the rogue wave: elsewhere still true.) No hollow tube: the lip leans
  over, but the surface is a height field moved sideways and cannot roll a barrel. No spray off the lips.
- The surf's foam is flat painted pieces like the rest; far off it is a white band pulsing with the sets. The shallow
  water is clear enough that the sand's caustics show through between waves.
- Under water the churn is subtle (the fog flattens it); the bubbles are only round the eye.
- Every shore gets surf, cliffs and rocky points too (the same breaking, not a crash against rock).
- The fishers' bobs and skiffs, animals and plants still use the flat surface: under a rogue wave they sit under it.
- Not in GameCommon: it is tied to this water shader and Bay's baked shore. Worth a component (a shore map from any
  height function, the include, `Surf`) if another game wants surf.

## Barrels (2026-11-18, second round)

The user, after the first build (crests that only leaned forward): "The whole point of the wave agent was for real
curling barrels on the waves, so research that". Built by an agent. Concept: `tools/art_src/concept_waves_shore.png`.

### What was found (research)

- **A heightfield cannot curl.** One height per x, z; moving it sideways (Gerstner, "choppy" displacement) folds it
  only into a cusp and then a self-crossing loop, never an open tube. Every curl in the work below adds geometry that
  folds back on itself.
- **Games: a breaking-wave shape carried along the wavefront.** Horizon Forbidden West (Malan, "Rendering Water in
  Horizon Forbidden West", SIGGRAPH 2022 Advances,
  https://advances.realtimerendering.com/s2022/SIGGRAPH2022-Advances-Water-Malan.pdf; the Decima Real-Time Live,
  https://history.siggraph.org/?p=89215; the art director on waves that "actually break and collapse",
  https://gamesradar.com/horizon-forbidden-west-dev-explains-why-its-water-looks-so-unbelievably-good): the curl
  treated as a fixed cross-section moving along the wavefront, laid out by artists as quads and deformed at run time.
  Lopatin, "Simulation and Representation of Topology-changing Rolling Waves for Massive Open Ocean Games" (SIGGRAPH
  2024 talk, https://history.siggraph.org/?p=160711): a simulated rolling wave captured as a few approximation curves
  that keep its overhang, for an open-world game. (The Horizon PDF could not be read here; the summaries are from the
  talk pages. No technical write-ups were found for Uncharted 4, Black Flag, Sea of Thieves or the surfing games.)
- **Film: a profile curve swept along the crest.** Moana's crashing waves (Byun and Stomakhin, SIGGRAPH 2017,
  https://history.siggraph.org/wp-content/uploads/2022/09/2017-Talks-Byun_Moana-Crashing-Waves.pdf): a profile-curve
  wave deformer for art-directed shape and motion, simulation only on top. Surf's Up (Sony Imageworks, SIGGRAPH 2007
  course, https://history.siggraph.org/animation-video-pod/surfs-up-a-practical-guide-to-making-waves-by-sony-pictures-imageworks/):
  the wave rigged and animated "as if it was just another character".
- **Real time, simulated**: Thuerey et al., "Real-time Breaking Waves for Shallow Water Simulations"
  (https://matthias-research.github.io/pages/publications/breakingWaves.pdf): a heightfield plus particle sheets that
  break off it (needs a simulation; no compute shaders here).
- **Which beaches plunge**: the Iribarren number, slope / sqrt(wave steepness) (https://en.wikipedia.org/wiki/Iribarren_number):
  spilling under about 0.5, plunging 0.5 to 3.3. A STEEP beach plunges; a gentle one spills. The baked beach (5 m deep
  at 14 m, about 0.36) with these waves (about 2 m high, 14 m long) gives about 1: plunging. So the floor was NOT made
  gentler and data/monterey.bin was not re-baked: a gentler slope would have made spilling surf, the opposite of
  barrels. What was short was room, which the sheets give (they break 6 to 11 m out, in 3 to 6 m of water).
- **Vertex animation textures** (a Houdini FLIP breaker baked to a picture of positions): considered; a parametric
  profile drawn into a small picture is the same idea without a simulation, and stays art-directable.

### Decision: a breaker sheet along each break, its profile from a baked picture (Claude's pick)

- **What**: `scripts/breakers.gd` (Breakers). Each break is a strip of sections (one every 0.6 m) along the line 8 m
  from the shore; each section has 64 points running in to the shore. A section carries one wave at a time (the one
  that has come in past 12 m and not yet been replaced a wavelength later). Behind and ahead of that wave's crest it
  is the water's own sums (the same `surface_at` as the water mesh); round the crest it takes a breaking PROFILE, 18
  key points per stage (a steep face; the lip pitching; thrown out about one and a half heights; the open tube about
  as high as it is deep; the lip landing; a collapsing mound), drawn into a 64 x 48 picture (`Breakers.profile`:
  columns along the profile, rows of stages; x, y, how thin the lip is, how far inside the tube). The profile is
  blended in by HEIGHT ONLY, where the water is not pushed sideways, so the shape can never fold through itself
  (each vertical line keeps its order). Each section breaks at its own time (`tb`), so the break peels along the
  strip (about 9 to 11 m/s): at any moment white water at one end, an open tube in the middle, a standing face at the
  other. Wave height follows the surf's sets (the barrels come in sets too). The water mesh is cut away (discarded)
  where the shore map's fourth channel (`Breakers.zone`, baked by `Surf.bake`) is over 0.5, and the sheet everywhere
  else: both draw with the water's own material and sums, so they meet along one line of one surface. The sideways
  push is taken out on both sides of that line (`Surf.zone_at` on the CPU).
- **The rogue wave** gets a sheet of its own across its width, moving with its crest: the same profile, its stage from
  its age (it pitches at 42% of its life, a stage every 22%), its height from its own. It curls over and collapses.
- **The look** (water.gdshader, the breaker path): the body deep green-blue at the foot of the face rising to green;
  the thin lip lit through in a yellow-green (`breaker_lip`), brighter looking towards the sun (`breaker_sun`, set by
  `Sea._look`); the tube's inside darker (`breaker_tube`) with pale streaks up its face; foam feathering along the
  lip's edge as it pitches, a white curtain where it lands, then white water with holes; the water round a breaking
  crest glassy (the last wave's foam left further in), and clearer from below. Spray: drops thrown off each pitching
  lip, blown back off the crest, and burst up where a lip lands (one CPUParticles3D a break, fed every 0.1 s from the
  CPU copy of the sums, `Breakers.point`). Which side of the sheet is seen comes from the shape (`v_air`), not the
  winding.
- **Why**: GL Compatibility on phones and the web: no compute, so no simulation; a vertex shader that reads a small
  picture and the shore map is cheap, and sheets exist only at the breaks. It actually curls (an open tube you can
  look into), which no heightfield trick does.
- **The practice**: a breaking cross-section swept along the wavefront (Horizon Forbidden West; Moana's profile-curve
  deformer; Lopatin's curves), the profile baked into a texture as vertex animation textures are, laid on a baked
  shore line as games drive surf (Crest, AC III).
- **Alternatives**: a FLIP simulation baked to a vertex animation texture in Houdini (no Houdini here; the profile
  picture is the same thing, art-directed); "curling Gerstner" displacement (folds into a self-crossing loop, never a
  tube); lip-only meshes over the heightfield (the heightfield's own crest fills the tube); a gentler beach (makes
  spilling surf, see Iribarren); particles for the lip (no smooth glassy face).

### Where the barrels break (Claude's pick)

- **Steamer Lane**: the point west of Santa Cruz's wharf, `from` (-58, -126.5) to (-20, -123) (second pass; was
  (-50, -125.5) to (-22, -123)), waves to 3.0 m at a full set (was 2.6), peeling west to east (a right, as there). Stops short of the wharf's harbour.
- **Marina**: the long straight beach on the east shore south of the river mouth, (88.8, -18) to (86.3, 28) (was
  (88.5, -10) to (86.5, 24)), to 2.9 m (was 2.3),
  peeling north to south (a beach break).
- Everywhere else the surf is as before (spilling and broken water, rocky points and cliffs included). More breaks:
  add a line to `Breakers.SITES` on a straight, smooth coast (a concave cove makes the sections fan; Pleasure Point
  was looked at and left out for that). Nothing placed by the shore moved: the floor is unchanged.

### The numbers (Claude's picks, change freely)

`Breakers`: STEP 0.6 m, POINTS 96 (12 behind, 72 in the profile, 12 ahead; 64 and 40 before the second pass),
DEPTH_LINE 8 m, ENTRY 12 m, WINDOW 1.7 wavelengths, BREAK_TIME 2.0 s (face to landing; 2.2 before), LAST_STAGE 1.5,
BACK 1.6 and FRONT 2.6 wave heights, SEEN 110 m (drawn within it; the water mesh beyond), the peel `tb` 0.4 to 3.9 s
along each strip (0.5 to 3.1 before), the ends' fade 0.8 to 3.5 m and the shoulders' taper (SHOULDER_LOW 0.4 over
SHOULDER 14 and 7 m; before, a fade over 2.5 to 8 m), the sets' share 0.67 to 1.
The shader repeats the sums (`breaker_point`, `breaker_crest`, `surface_at`): keep them alike with `Breakers.point`.
`-- --no-breakers` leaves the breakers out (costs, comparisons).

### Checked

- `sh tests/smoke.sh` passes with three new checks (`checks.gd` `_breakers`): the profile never crosses itself at any
  of its 48 stages, opens a tube and closes it; every face of the sheets, bent as the shader bends it, faces the air
  (Godot's front faces wind clockwise), at 10 times through a period (0 wrong of about 20,000 where the shape shows;
  at the strips' ends, where it is faint, about 180 thin twisted slivers, which the shader shows from the right side
  anyway); the water gives way only at a break.
- Pictures (`tests/barrel_shot.gd`: holds the clock where a chosen section is at a chosen stage and puts the eye at
  `--view=side|inside|under|beach|sea|top|high`; `--debug=4` shows which mesh draws each pixel, `--debug=5` the foam
  and weights): from the shoulder into the tube, from inside the tube out to its open end, from under the water, a
  strip from the beach of one wave from swell to curl to collapse, both breaks, and the rogue wave's curl from the
  side (`tests/surf_shot.gd --rogue=46,<age> --across`). Two quality passes against the concept and barrel
  photographs: colours moved from teal to the concept's lit green lip and dark tube; foam and the pale wandering lines
  taken off the barrel's glassy face; spray thickened. Also drawn under ANGLE (as a browser draws).
- Cost (`-- --perf=beach,start,title`, 390x844, desktop): frame 5.32 / 5.15 / 5.57 ms before, 5.39 / 4.51 / 4.56 after;
  GPU 1.04 / 1.03 / 1.16 before, 1.01 / 1.04 / 1.15 after; one more draw and about 11,000 more triangles where a break
  is in sight. At a barrel (`--perf=barrel`, new), with and without `--no-breakers`: GPU 0.19 to 0.33 ms either way,
  within the noise. Not tried on a phone.

### Second pass (2026-11-18, the user after GIFs from six angles: "Definitely needs another round")

What the GIFs showed: only the close side view read as a tube; from above a moving foam line; from under the water a
foam roof; the Marina from the beach a low green band; the "inside" camera dipping under the water. What changed
(Claude's picks, after barrel photographs and the concept; a "round" tube is 1 to 2 times as wide as it is high,
Pipeline's is round, Teahupo'o's lip is half the wave's height thick: Surferpedia "Wave shape", Swellnet's anatomy of
Teahupo'o):

- **Shape**: new profile keys (`Breakers.KEYS`): the crest 1.2 heights up (was 0.95), the lip thrown 1.6 to 1.85
  heights (was 1.45 to 1.7) with a quarter to a third of a height of thickness, the tube about 1.4 times as wide as
  high (about 1.5 x 1.05 heights inside, was about 1.3 x 0.8). The tip still never meets the water below (the profile
  must not cross itself). 96 points down a section (72 in the curl, was 40) and a 128-column profile picture, so the
  tip is round and the edge smooth. `tools/` has no profile viewer: the sheet of stages was drawn with a throwaway
  script; `checks.gd` still counts crossings.
- **Size and peel**: waves taller (Steamer Lane 3.0 m at a full set, was 2.6; the Marina 2.9, was 2.3, the same
  profile, so as round) and the sets' share of it 0.67 to 1 (`Breakers.sets`, was 0.45 to 1: a small set's barrel
  was too small to read). Strips longer (Steamer Lane 38 m from x -58, the Marina 46 m from z -18 to 28), BREAK_TIME
  2.0 s and the peel 0.4 to 3.9 s along each (11 and 13 m/s), so a tube spins along the beach for longer. (A section
  carries its wave one period, 7 s: the last section's peel time plus 1.5 breaks must fit in it.) The Marina's strip
  walk now stops at the line's point nearest `to` (it ran on to 400 sections when `to` was off the line).
- **Shoulders**: the breaking shape fades only in the last 0.8 to 3.5 m; before that the wave itself is lower towards
  each end (to 0.4 of its height over 14 m on the shoulder still to break, 7 m on the white water side;
  `SHOULDER`, each section's height in `heights` and CUSTOM0.z), so a tube tapers away instead of flattening.
- **Look** (water.gdshader's breaker path): foam in two painted tones (a pale lit aqua band and white strokes, broken
  along the lip by a big slow blotch) instead of a hard white line; a curtain of white streaks only on the falling tip;
  white water only from the landing forward and over the collapsing crest (the back stays green), in heaps and holes,
  shaded by the sun on its own shape (`breaker_foam_shade` the shaded side); painted streaks up the wave's back and its
  top lit through, for the view from out at sea; the glassy water (no surf lace) over the whole section while it
  carries a barrel, from well before the face stands up (the shoulder ahead was covered in the last wave's lace) and
  further ahead of the crest. From under the water: the breaking section's foam roof mostly taken away, the wave's
  body lit water a little darker than the surface round it, the lip brightest, the tube's floor clear so the dark
  inside of the tube shows through, white where the lip lands.
- **Spray** (`Breakers._make_stream`, `_feed_spray`): the drops are gone; three streams a break of billboards cut from
  one painted puff made in code (`Breakers.puff`: five lobes, a noise-cut edge, three flat tones): a PLUME feathering
  up and back off the crest (twice from a big one) and thrown off the pitching lip; a BURST of big puffs up and back
  where the lip lands; and a CURTAIN of bubbles driven down under the landing. Only the side the eye is on is fed (the
  surface hides each from the other), puffs fade out within 0.6 to 5 m of the eye, dimmed with the hour.
- **The surface knows the lip**: `Sea.surface_height(x, z, y)` (new optional height) asks `Breakers.surface`, which reads
  the nearest section's profile row: in the tube (between the floor and the lip's underside) the surface is the floor,
  so a fish there is in the air and the camera above water; without `y` it is the lip's top. The camera's above/below,
  the wet-lens streaks, the haze, the player's leap and landing pass their height (a fish left in the tube's air as a lip goes by falls to the floor, not put under it). About 12 to 17 us a call near a
  break (5.5 for `Surf.height`), nothing elsewhere. New check: `in a barrel's tube the surface is the tube's floor`.
- **Pictures** (`tests/barrel_shot.gd`): "inside" and "under" ride with the tube (put again each stage), the rest are
  placed at stage 0.7 so the frame holds the curl; "inside" sinks as the tube closes; "under" is under the back of the
  wave, where it is deep enough to swim (under the tube itself the water is too shallow for an eye: a barrel breaks in
  water little deeper than it is high); "beach" is further along so it sees into the tube's open end; "sea" is behind
  and above, as from a deck or the bluff; "high" a drone's view over the shoulder. Each saved line says whether the eye
  is above or under the water.

### Rough

- From straight out to sea at the water a barrel is only its back and the plume (as a real one is); the "sea" picture
  is from higher up.
- The white water is painted heaps on the sheet plus the burst; it does not roll on as a moving foam ball after the
  section's last stage (the water's own bore takes over).
- Inside the tube as it closes (stage 1.2 on) the eye is in a jumble of foam faces; the trough under the tube shows
  faint vertical bands where the sections meet at a grazing angle.
- The rest of the surf's foam (the swash's flat white shapes, the lace on the plain surf) is as it was.
- At the strips' ends a few thin twisted slivers remain where the shape is faint (307 counted, shown from the right
  side by `v_air`).
- Only two breaks. Nobody has swum one by hand; a fish in the tube now leaps there (the surface is the floor), which
  is untried in play.
