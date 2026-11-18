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
- No hollow tube: the lip leans over, but the surface is a height field moved sideways and cannot roll a barrel; a
  breaker sheet along the breaking line would be the next step. No spray off the lips.
- The surf's foam is flat painted pieces like the rest; far off it is a white band pulsing with the sets. The shallow
  water is clear enough that the sand's caustics show through between waves.
- Under water the churn is subtle (the fog flattens it); the bubbles are only round the eye.
- Every shore gets surf, cliffs and rocky points too (the same breaking, not a crash against rock).
- The fishers' bobs and skiffs, animals and plants still use the flat surface: under a rogue wave they sit under it.
- Not in GameCommon: it is tied to this water shader and Bay's baked shore. Worth a component (a shore map from any
  height function, the include, `Surf`) if another game wants surf.
