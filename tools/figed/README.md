# figed: the figure editor

Started 2026-11-19. The user: "Lets try to build a new model from scratch and this time rather than adjust minute
details, lets take a generic model, then categorize the vertices so that we can make intelligent edits to the model-
e.g. longer shins, longer forearms, longer fingers, shorter/ wider palm width, chest hip shoulder with, brow and nose
controls etc, so we can essentially make a character editor. Then we use these functions to sculpt the body to fit the
art for the most part, and THEN we can work on tiny detail corrections".

So a figure is no longer a build script. It is **one generic human plus a table of slider values**
(`figures/<name>.json`). The order of work is: sliders first (mostly by the automatic fit), small corrections last.

## Decision (Claude's pick): MakeHuman's base mesh and targets, with our own bone controls on top

- **What:** the generic human is MakeHuman's base mesh as shipped in MPFB2 (assets CC0), kept OUTSIDE the repo at
  `C:\Projects\reference\makehuman\mpfb2` (`git clone --depth 1 https://github.com/makehumancommunity/mpfb2`; only its
  `src/mpfb/data` is read: `3dobjs/base.obj`, `targets/**.target.gz`, `rigs/standard/*.game_engine.json`,
  `mesh_metadata`). The add-on itself is not installed or run. Its vertices are already categorised twice over:
  1. **targets**: 1,258 artist-made sliders ("which vertices move, and how far" for longer shins, wider nostrils, a
     lower brow...), read here as 579 controls once left/right and less/more are paired. `ALIASES` in `figed.py`
     gives the common ones plain names (`shin_length`, `forearm_length`, `finger_length`, `shoulder_width`, `chest`,
     `hips`, `brow_height`, `nose_width`, `jaw_width`...).
  2. **bones** (ours): every vertex belongs to bones by its skin weights, and `"<bones>.<length|width|depth|girth|size>"`
     scales a bone's share of the body with no limit, carrying what hangs off it without stretching it
     (`hand.width`, `thigh.length`, `head.size`...). This is what reaches cartoon proportions the targets cannot.
  The skeleton (53 bones, MakeHuman's "game engine" rig) is placed from marker cubes that move with the sliders, so
  it always fits the body, and the skin weights come with it.
- **Why:** it is exactly the editor the user described, already made and tested by artists, free to ship, with a rig,
  weights, UVs, eyes, teeth and a tongue. Writing the categories ourselves (the first idea) would have meant guessing
  face regions on a mesh with no labels: the part that failed for a day on the old figures.
- **The practice it follows:** character creators (MakeHuman, MetaHuman, most games' editors) are a neutral mesh with
  morph targets for shape and bone scaling for proportion; fitting to references is done on the sliders, not on
  vertices.
- **Alternatives:** Blender Studio's CC0 stylised body (on this machine; good shapes, but no targets, rig or weights:
  every control would be ours to write); installing MPFB2 and driving it (a GPL add-on as a build dependency, slower,
  no gain over reading its files); image-to-3D generators (triangle soup); the old per-figure build scripts (tabled).
- **Costs to know:** the body is 13,380 vertices (about 26,700 triangles) before any reduction, against the Twilight
  Princess yardstick of about 2,500: a low model is owed before it goes in the game. The look is realistic by
  default; the stylising comes from pushing sliders past 1 and from the bone controls. Faces only reach what the face
  targets can express; what is left over is the "tiny detail corrections" stage.

## Files

- `figed.py`: the core. `Base` reads the files; `Figure(base, spec).solve()` gives points and skeleton;
  `to_blender()` turns them to metres, z up, facing -y, feet on the floor. A spec has `macro` (gender, age, muscle,
  weight, height, proportions: 0..1), `targets` (control or friendly name -> value, about -1..1, more is allowed; add
  `.l` / `.r` for one side), `bones` (factor), `raw` (a target file by name), `height` (metres).
- `figed_blender.py`: `-- controls <out.txt>` lists every control; `-- look <spec|-> <out.png> [views]` pictures in
  plain grey (front side back quarter face face_side face_quarter hand foot); `-- sliders <dir>` the demonstration
  sheets; `-- build <spec> <out.glb> [out.blend]` the mesh on its skeleton.
- `figed_fit.py -- <job.json>`: the automatic fit. The drawing is cut from its background, the model is drawn as a
  filled outline at the same size, and each slider in turn is nudged and kept when the overlap improves. A job
  (`figures/*.fit.json`) lists the views (picture, box, which way it looks) and the sliders that may move with their
  limits. It writes the spec and a picture: drawing only in red, model only in cyan, both in grey.
- `figures/brother.json`: the older brother, fitted to his character bible (`tools/art_src/concept_brother_bible_*`).

Run with `blender -b --factory-startup --python tools/figed/<file>.py -- ...` (Blender's Python has numpy; this
machine has no other Python).

## State (2026-11-19, after the second body round)

- The brother's BODY, second round (the user: "do another round on the body, giving extra care to his hips thighs and
  legs which dont look quite right"; the face was to be left alone). What was wrong, seen beside the bible: flared
  fat hips, heavy thighs tapering to thin shins, knock knees, small feet, where the drawing has narrow boxy hips over
  straight sturdy columns, broad knees, thick ankles and wide turned-out feet. Causes and what the fit learned:
  - it had fitted the boxer shorts as flesh, and all rows counted alike: views now have `bands` (shares of the height,
    floor up, each with a weight): legs below the shorts 4, the shorts 1, the trunk 1.5, the head and hair of the body
    sheet 0 (the shaved sheet scores the head and neck instead, as three more views);
  - widening the pelvis moved the legs apart: `flesh_width` / `flesh_depth` / `flesh` scale a bone's own skin and
    leave the joints that hang off it where they are (`pelvis.flesh_width`);
  - two sliders fought (`hip-scale-horiz` out against `thigh.width` in) and left a ledge at the hip: the scale
    targets for hips and legs are out of the job; bone widths do that work;
  - the sheet's side view has the arm hanging while its front view has the arms out: a pose slider may be for one
    view only (`"arms_down@side"`); `legs_apart` and `feet_out` are stance sliders; a view can line up by the feet
    (`"anchor": "feet"`) instead of the head; `zoom` on a whole-figure view lets the bald model stand under the hair.
  - `muscle` is held at 0.5 or more and `weight` at 0.75 or less (Claude's limits: an outline alone drove him to fat).
  Overlap now: front 0.93, back 0.94, side 0.89 on the body sheet; head and neck 0.95 on the shaved sheet.
  `-- look <spec> <out> legs legs_side legs_back --posed` are the pictures to judge the legs by.
- Still not right in the body: no muscle definition (quads, calves, pecs: an outline cannot see them), the thigh sits a
  little behind the drawing's in the side view, the feet are shorter than drawn, the elbow's place is a guess.
- His HEAD: outline fitted to the shaved head row (`figures/brother_head.fit.json`); nose, cheeks, eyes, brow and
  mouth set by eye once (Claude). The user, 2026-11-19: "Lets not worry about the face" for now. Before re-running the
  head fit, take the nose and chin sliders out of its `move` list or it will move them again.
- Owed: landmarks for the fit (elbow, knee), muscle definition, eyes, the small corrections, paint, hair, a low model
  (27,700 triangles as exported now), and the others (he is the tallest of the three, the user, 2026-11-19).
- `-- build` exports a .glb with the 53-bone skeleton and weights (tried; not yet opened in Godot).
- A candidate for GameCommon (it is not tied to Gulp) once it has made one finished figure.

## Marks: where the parts are (2026-11-19)

The user, of the second body round: "Dont only compare to the outline, also compare to the reference art / For where
body parts are". An outline cannot say where an elbow, a knee, the navel or a nipple sits. So a view may carry `marks`:
`{name: [x, y]}` read off the drawing (at `box_width` pixels; `_l` / `_r` are the FIGURE's own left and right), and the
fit adds the squared distance from each to the same part of the model (`marks_weight`, 150 for the brother). What each
mark is on the model is `MARKS` in `figed_fit.py`: a joint (knee, ankle, elbow, wrist, shoulder, hip), a bone's tip
(fingertip), or a point of the skin found from MakeHuman's own navel and nipple targets. The fit's picture draws each
pair (yellow = the drawing, blue = the model, a line between) and its last lines print every mark's distance as a
percentage of the figure's height.

- The brother's marks were read by Claude by eye on a 100-pixel grid over the body sheet (about half a percent of his
  height either way). Knee and ankle marks are the JOINT (the lower edge of the kneecap, the ankle bones), not the
  middle of the kneecap or the narrowest part of the shin: reading them high cost a round.
- With marks, segment lengths can move without fooling the outline: `spine_0x.length`, `pelvis.length`,
  `upperarm.length` / `lowerarm.length`, `hand.length` are in the job now.
- After this round every mark is within about 1% of his height (navel 1.2, elbows 0.7 to 1.1, knees 0.5 to 1.1,
  nipples 0.5 to 0.9, ankles 0.6 to 0.9), with the outline at 0.94 front and back, 0.89 side.
- Not marked yet: shoulder points, armpits, the crotch (hidden by the shorts), kneecaps and calf bulges as shapes,
  anything on the head.

## Pecs, shoulders and hands (2026-11-19, round four)

The user: "lets do around focusing on his pecs, shoulders and hands, he should have hand key art to compare to".

- **Hands are fitted to a hand drawing.** The bible has no hands page, so the hand key art is the earlier
  `tools/art_src/concept_brother_hands.jpg` (top row: the back and the palm of his LEFT hand; Claude's pick of sheet,
  not confirmed by the user). A view with `"look": "hand_back" | "hand_palm" | "hand_edge"`, `"hand": "l"` and a
  `"wrist"` row is compared from the wrist to the fingertips in the hand's own directions (`hand_frame`), the model's
  hand drawn to the drawing's length. So `figures/brother_hands.fit.json` sets the hand's SHAPE (`hand.width`,
  `hand.length`, `fingers.length`, `fingers.girth`, `thumb.*`, finger spread and thickness, wrist) and the body job
  sets only its size (`hand.size`, by the wrist and fingertip marks): the shape sliders are out of the body job.
  Pose sliders `thumb_out` / `thumb_flat` lay the thumb as drawn. Overlap 0.62 -> 0.89 on both views.
- A back view and a mirrored palm view have the same outline: the first overlay drew the model's hand mirrored and
  the user caught it ("Swapped left and right"). Check the thumb's side in a grey render (`hand_back_l`,
  `hand_palm_l`, `hand_edge_l` in `-- look`) before trusting a hand overlay.
- **Pecs and shoulders are set by eye**, since neither outline nor marks see them: macro `muscle` 0.85, `pecs` 1.5,
  `shoulder_muscle` 1.5 (Claude, against the bible's round shoulder caps and full chest), then the body job was run
  again with those three held. Outline after: front 0.91, back 0.91, side 0.90 (front and back lost about 0.03,
  mostly at the hands, now spread with the thumb out where the body sheet's hang closed, and at the shorts);
  marks within 0.1 to 1.7% of his height. `-- look` has `chest`, `chest_quarter`, `chest_side`, `chest_back`,
  `chest_top` for judging them.
- Round five, the user (circling the chest in the side overlay): "Dont model in the nipples, just try to get the shape
  right of the pecs, they too high up and pointy. Also do a round on his arms now". So:
  - a view may carry `regions`: boxes of the drawing ([x0, y0, x1, y1, weight] at `box_width` pixels) whose overlap is
    scored by itself. The brother's: both arms from shoulder to wrist in the front and back views (weight 2), and the
    front of the chest in the side view (weight 3), which is what shapes the pecs' profile. `pecs`, `breast-point`,
    `breast-volume-vert-up` and `upperarm-fat` move in the body job again (pecs came down from the by-eye 1.5 to
    about 0.9, lower and rounder); `muscle` and `shoulder_muscle` are still held.
  - nipples are not modelled: `nipple-point` -0.25 and `nipple-size` -1.5 leave the skin there within 2 mm of smooth
    (measured, not by eye). A tick of the base mesh's edges still showed (the user: "He still has nipples?"), so a
    spec may now carry `smooth`: patches of skin relaxed after the sliders, `[{"at": "nipples", "radius": cm,
    "passes": n}]` (`Figure._smooth`; the first of the small corrections). They are paint, later. The nipple MARK
    still works: it is a point of the skin, flat or not.
  - `elbows@side` is held to -12 or more: at -31 the forearm stuck out in front of the belly in the side view.
  Outline after: front 0.92, side 0.91, back 0.93; marks within 0.1 to 1.5% of his height.
- Round six, the user (an arrow pointing back from the nape in a side render): "His biceps are too skinny. Alos lets
  start on his head and neck. His neck and head is jutting too forward so lets just fix that first".
  - Why the fit had not seen it: the body sheet's side view ignores the head (hair), and the shaved sheet's side view
    was lined up BY the head, so a head carried forward of the body scored the same. Now `bare_side` lines up by the
    feet and scores its legs (weight 1) with its head, neck and shoulders (weight 2), and `head-trans-forward` and
    `neck-trans-forward` move. `neck-trans-forward` had been set to 1 by eye in the first head pass (Claude's
    mistake); the fit took it to 0. Side overlap 0.91 -> 0.92.
  - The upper arm seen from the side is hidden inside the body's outline, so its depth is measured instead: the
    bible's is about 10% of his height front to back at the biceps (both side views), the model's was 8.6%;
    `upperarm.depth` 1.25 makes it about 10.7% (a little over, as the user asked for more).
- Round seven, the user: "Bis calves looks a tad small, and can we make them a bit more angular / toned (not skinnier
  though)? His feet also need work, his heel looks dropped a liitle and his toes look scrunched".
  - Calves by eye, held out of the fit (it would pull them back to the outline): `lowerleg-muscle` 1.1,
    `lowerleg-fat` 0.4, `calf.girth` up 6%.
  - **`foot.length` is not to be used**: the foot bone runs down and forward from the ankle, so scaling along it
    (the fit had it at 0.8) dropped the heel and squashed the toes. The foot's length is MakeHuman's
    `foot-scale-depth`, the toes' is `toes.length` (new bone set, the `ball` bones). Set by measurement, since the
    outline fit pushed them the wrong way: the bible's foot is about 16.5% of his height heel to toe (side view); the
    model's was 18.8% at rest with short toes, and is about 16.7% with `toes.length` 1.3 and `foot-scale-depth` -0.5
    (longer toes on a shorter foot). Foot sliders do not move in the body job.
  Outline after: front 0.92, side 0.90, back 0.92.
- Round eight, the user (lines drawn on the side render): "His calves poke out way too far, reference the art, his
  butt is a little too small, and he has too much of an anterior pelvic tilt he needs better posture".
  - Calves: Claude had overdone round seven. `lowerleg-muscle` 1.1 -> 0.6 and `calf.depth` 0.95, so the back of the
    calf no longer stands behind the butt in the side view (as the bible's does not).
  - Butt: `buttocks` 1.0, held out of the fit (the shorts hide it in the bible, so the outline had shrunk it).
  - **Posture is a new spec section**: `"posture": {"pelvis_tuck": degrees}` turns the pelvis under and turns the
    trunk above and the thighs back by the same angle, so the hollow of the back flattens while he stays upright; it
    is built into the model (points and skeleton, in `to_blender`), not a pose for pictures. The brother's is 7
    (by eye). The bone-turning code (`pose_points`) moved from `figed_fit.py` into `figed.py` for it.
  Outline after: front 0.92, side 0.91, back 0.92.
- Round nine, the user: "Rest his arms down by his side straightend out- I think they might be way too long". They
  were: forearm 21.3% of his height and hand 14.4%, where the bible has about 14 and 12. **Cause: the generic model
  rests with its elbows bent forward**, towards the camera of a front view, so its forearm looked short there and the
  fit stretched it to reach the wrist and fingertip marks (the "odd on paper" forearm noted after the marks round was
  this, not deep shoulder joints). Now pose `arms_straight` 1 (held) lays each forearm in line with its upper arm for
  every comparison, `elbows_out` angles it away from the body as the bible draws it (the fit found 4 degrees), and
  the common `elbows` slider is gone. After: upper arm 15.3%, forearm 15.8%, hand 12.0%; hung straight, the wrist is
  at 51% of his height and the fingertips at 43% (they were at 47% and 37%). Marks within 0.1 to 1.6%; outline
  front 0.91, side 0.92, back 0.92. **Check any figure with its arms hung straight before trusting arm lengths**
  (the probe prints the three lengths and where the joints reach).
- Round ten. The user asked to pose him ("let me pose him for you"): `-- build` to `work/<name>.blend` (ignored by
  git), opened with `pose_session.py` (skeleton selected, Pose Mode); `-- read <out.json>` writes a saved pose out.
  Raising an arm there showed what the arms-out sheet hides: "his rib cage area is too enlarged" (the side of the
  trunk under the armpit flared, where the bible's drops nearly straight to the waist). The body job now has regions
  over the gap between each arm and the trunk (armpit to waist, front and back, weight 4) and may move
  `spine_02.flesh_width` / `spine_03.flesh_width`; the fit narrowed the upper trunk (`spine_03.width` 1.26 -> 1.14,
  `shoulder_width` -0.47 -> -0.84) and the outline rose to front 0.94, back 0.94, side 0.92. **Look at a figure with
  its arms raised as well as hung**: each pose hides something.
  Also the user: "his crotch is too small": `bulge` 2.0 (MakeHuman's smooth mound for under clothes; by eye).
- Round eleven, the full body run. The user added two sheets to his bible and a pose: "I made a version without the
  arms so you can see the body sillouhette clearly, and have updated the pose sou can accurately compare them. One
  thing to note is in the character bible his right looking pose arms are not spread like the straight on one, so I
  also made a arms sheet to compare to, and only compare his arms in the face on or back pose."
  - `tools/art_src/concept_brother_bible_armless.jpg` (front, side, back without arms, plus a view from above and one
    from below, not yet used) and `concept_brother_bible_arms.jpg` (five views of the arm; six of the hand).
  - **Armless views**: a view with `"armless": true` is compared with the model drawn without its arms
    (`armless_mask`, cut `armless_cut` of the way down the upper arm, 0.45, so a stump stays as drawn). The trunk and
    legs are fitted to these three (weight 1.5 each).
  - **Arms only front and back**: the main body sheet's front and back views stay for the arms (weight 0.6, with their
    regions and marks); its side view, where the arm hangs, is kept for its marks only (`"outline_weight": 0`).
  - **The comparison pose is the user's**, set by hand in Blender and read by `pose_session.py -- read` (a `turn`
    per bone, stored as the spec's `pose`). Pose sliders (`arms_down`, `arms_back`, `legs_apart`, `feet_out`, new
    `lean`) now lay small corrections OVER it (`turn_more`) instead of replacing a bone's turn; `arms_straight` and
    the thumb sliders are not used with it.
  - A region over the gap between the thighs (shorts' hem to the knees, armless front and back, weight 5): without
    it the thighs grew together.
  - Hands refitted to the arms sheet's palm and back views (`brother_hands.fit.json`; 0.83 and 0.82). The older
    `concept_brother_hands.jpg` is retired.
  - `arm_widths.py` + `figures/brother_arms.measure.json` measure the arm's width and depth at stations from shoulder
    to wrist on the arms sheet and on the model. **The two sheets disagree**: the arms sheet's arm is about a
    quarter thicker for its length than the body sheet's front and back views allow (model / drawing 0.71 to 0.86
    wide, 0.75 to 1.0 deep after the fit). The model follows the body sheet for now; which sheet rules is the
    user's call (asked 2026-11-19).
  After: armless front 0.93, side 0.90, back 0.93; main sheet front 0.93, back 0.93; marks within 0.3 to 2.2% (the
  elbows worst). Arms hung straight: upper arm 17.3% of his height, forearm 16.2%, hand 10.1%, fingertips at 42%.
- Round twelve, hands. The user (after round eleven: "Seems likes you're doing too much- we're kinda close", then
  "Actually mych better"; then of the hand): "his hand is all messed up now ... the thumb is deformed, and the
  fingers look a little too short, with too much space between them. The hand wrist forearm connection also looks
  blated". Cause: the hand outline fit had run its sliders to their limits (`thumb.girth` 1.8, `finger_spread` 2,
  `finger_length` -1.25, `hand.length` 0.7, `wrist` 1.19). **Hands are set by hand now and no hand slider moves in
  any automatic fit**: `thumb.girth` 1.12, `thumb.length` 1, `fingers.girth` 1.08, `fingers.length` 1,
  `hand.length` 0.95, `hand.width` 1.08, `hand.size` 1, `finger_spread` 0.4, `finger_thickness` 0, `wrist` 0.1 (the first try, girth 1.25 and spread -0.5, was "too chubby tube like now, with no space between them", the user)
  (hand 12.6% of his height). `brother_hands.fit.json` is kept for looking (`--look-only`), not for running.
- The skeleton is MakeHuman's "game engine" rig: Unreal's mannequin layout and names, 53 bones, no twist or face
  bones. It is NOT the shared boy's skeleton (GameCommon's character controller): his clips need retargeting, or
  this body moving to his skeleton. Not decided; the user's call before a figure goes into a game.
- Still not right: the toes are thin beside the bible's broad ones and the feet point straight ahead (the bible's
  turn out; `feet_out` is only a pose); the arms are thick but tube-like (no biceps or triceps bulge, no forearm swell by the elbow as the
  bible paints them); the back is smooth (no shoulder blades, spine furrow or lats as the bible paints them), the pecs
  are boxy with a hard lower edge, the shoulder cap peaks lower than drawn, the thumb's tip is pointed.

## Later small rounds (2026-11-19, after round twelve)

- The user: "now his crotch is too recessed and small, the lower belly curves too much compare to the no arms side
  profile". By eye against the armless sheet's side view: `belly` 0.375 -> 0.25 (held out of the body job now),
  `bulge` 2 -> 3.5, `hip-trans-forward` 1.2, so the front runs nearly straight down from the belly to the crotch as
  the sheet's shorts do. To judge the belly and crotch from the side, raise the arms first (a trial spec with pose
  `arms_down` -70, `-- look ... side --posed`): hung or held out, the arm or hand covers them.
- The user, of that round: "you changed his pose ... after the crotch fix". `hip-trans-forward` moves the hip JOINTS
  as well as the skin, so the pelvis stood forward of the feet and the legs slanted. It is out (0); `belly` 0.25 and
  `bulge` 3.5 stay. **Targets named `*-trans-*` move joints: they change how a figure stands, not only its shape.**
  Check the stance from the side after using one.
