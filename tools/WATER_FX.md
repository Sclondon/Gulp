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
| Caustics | in the sand's own shader: `Sea._caustics` takes the code of GameCommon's sand shader (scripts/sand.gd, left as it is), puts in a few lines at four anchors, and draws the sand with that copy (made before anything is drawn, so still one program). Two layers of wandering lines where a smooth noise crosses its middle, warped and drifting, brighter where they cross, in patches; they brighten only the light from above (sun or moon), between 5 and 12 m of water fading out, and fade beyond 16 to 34 m from the eye. If the sand's shader changes so that an anchor is missing, there are no caustics and a warning | 0 | 0 (a copy instead of the original) |
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
- Caustics fall only on the sand, not on rocks, plants or fish. The plankton specks do not stretch in a burst.
- Sunrise and sunset were looked at once each; dusk is a bit grey.

## Whose calls

The user's: a bubble trail and distortion, more on a burst; a burst changes the fov and shows speed lines; shafts in
3D; caustics in some areas; a day and night, night not too dark; the leap as in Salmon Run.

Claude's (change freely): everything in the numbers above; 9-minute day from 9:30; the moon as the night's light;
the leap's least height in lengths; the eye's place in a leap (to one side, low over the water); the eye kept under
the surface while swimming; the shafts' grid, look and depth fade; caustics only in the sand's shader, by depth;
streaks as pale dashes; the bubble shader for every bubble.
