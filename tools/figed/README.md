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

## The head (2026-11-19, first round on the new head art)

The user: "Alright lets start working on the head. I made some custom updates to the head art, this is the new
biblehead pic": `tools/art_src/concept_brother_bible_face2.png` (the face with hair, front) and
`concept_brother_bible_head_bare.png` (shaved, five views; 1024 px wide as it arrived). They replace
`concept_brother_bible_face.jpg` and the head rows of `_bible_bare.jpg` for his head (kept, retired).

- All 43 face sliders from the first head pass (set by eye, many at extremes: `nose_size` 1.4, `nose_tip_width`
  1.6, `brow_forward` -1) were reset, and `brother_head.fit.json` now fits the outline to the shaved sheet's front,
  profile and back.
- **A head view's size is pinned by the chin** (`"chin"`: the row of the chin's bottom; the model's is the point
  the `chin-height` target moves most). With the size left to a `zoom` slider, the fit enlarged the model and
  compared only its top part: a high score on a head too narrow and long. `zoom` is now 0.96 to 1.04.
- **The face's fullness is held by eye** (`head-fat` 0.8, `cheek_fullness` 0.8, `head-round` 0.5, `cheekbones`
  -0.3; none moves in the fit): left free, the fit reached the same outline with a thin, hollow-cheeked face and a
  wide jaw. An outline cannot tell a full face from a bony one.
- After: front 0.97, profile 0.97, back 0.94; width to height 0.78 against the sheet's 0.80.
- Not done: the nose (long and thin with a hooked tip, where the sheet's is a broad round bulb), the eyes (the
  sheet's are small and downturned with bags), the mouth (wider, a fuller smile), bigger ears, brows. Features the
  outline cannot see are next, one at a time.
- Jaw round, begun. The user: "Make sure to line up the jaw as well- maybe color the face so you can distinguish it
  better"; "Lets do just a jaw round, then a nose round".
  - `-- look ... --tint` colours the skin that follows the head bone, so the jaw's edge shows against the neck.
  - Head views take marks now (`chin`, `jaw_l` / `jaw_r`: points of the skin found from MakeHuman's chin and jaw
    targets; `brother_jaw.fit.json` moves only jaw and chin sliders).
  - **The chin point was wrong and so was the first head fit**: the `chin-height` target peaks UNDER the jaw, 2 cm
    behind and above the chin's bottom, so the size pin drew the head about 6% too large and the fitted head was
    narrow (0.72 wide to high, not the 0.78 reported). The point is now where `chin-prominent` peaks (the chin's
    bottom front), and the head outline was fitted again: 0.97 front, 0.98 profile, 0.95 back; 0.79 wide to high
    against the sheet's 0.80. Look at where a mark sits on the model (the fit's picture draws it) before using it.
  - The `jaw` point (where `chin-bones` peaks) is mid-jaw, not the corner under the ear: fine in the front view,
    wrong in profile, so the profile has only the chin mark. The user offered to outline the jaw on the sheet
    ("Do you need me to outline the jaw?"); the jaw fit waits for that.
- Jaw round, done by eye to the user's drawing (`tools/art_src/user_brother_jaw_lines.png`: red = where the jaw's
  edge is on the sheet and should be on the model, dark green = where the model's was; and
  `user_brother_upper_lip.png`): "I think you might be reading hte shadow as teh jaw? His jaw bone is sitting crazy
  low in the model ... another issue is he has way too much upper lip- so his ears and stuff dont like up either".
  The chin's bottom was right; the jaw's CORNERS hung low and wide with a flat underside. Now `head-fat` 0.8 -> 0.3,
  `double_chin` 0, `chin-triangle` 0.5, `jaw_drop` -0.8, `jaw_width` -0.3, so the lower face is a U rising to the
  ears; and the upper lip is shorter (`mouth-trans-up` 0.6, `nose-trans-up` 0.2, `nose_length` 0.1, `chin_height`
  0.6). `mouth-trans-up` is strong: 1.5 put the mouth under the nose. All of these are held out of the head fit.
  Still softer and lower at the corner under the ear than the red line: the sliders do not reach a clear jaw corner
  on a neck this thick; a candidate for the small-corrections stage.
- The user, of that: "His jaw hinge still sits way too low look at the huge difference between thr model and art"
  (a line from the ear's lobe to the jaw's corner: short on the sheet, long on the model), and, when Claude began to
  measure the ear: "the ear is in the right spot dont move it". Two findings:
  - the edge the user traced on the tinted render is where the TINT stops (the head bone's skin), not a jaw corner;
    the generic model has no jaw corner back there at all, the cheek runs smoothly into this thick neck, and no
    slider makes one (`jaw_drop` does not move it). Say what a tint edge is when showing one.
  - **`jawline`, the second small correction** (`Figure._jawline`): the jaw's lower edge cut into the skin along a
    path read off a drawing, `[back, up]` from the chin's bottom in shares of the head's height seen from the side;
    the skin just under the line is pressed in along its normal (`depth`, cm), the skin just over it raised
    (`lip`), nothing at the chin's front. The brother's follows the user's red line: depth 1.6, lip 0.4, width
    0.07. It is a cut in the surface, not anatomy: check it in three-quarter view and with the head turned.
- The user, of the jaw cut: "nope undo that, your just messing some slider up- got for a mostly modified jaw" (read as:
  a mostly UNmodified jaw). They were right: the buried jaw was Claude's own sliders, not the generic model. With the
  jaw and chin targets back at 0 (`jaw_width`, `jaw_drop`, `chin-triangle`, `chin_width`, `chin_height`,
  `chin_forward`, `chin-prognathism`, `double_chin`, `head-square` all removed) the model's own jaw shows a jaw
  line again, and the `jawline` cut is off for him (the code stays; unused). They are also out of the head fit's move
  list, which had set `jaw_width` -0.9 and `chin_height` 0.45 chasing the outline. **Before adding a correction,
  put the sliders of that part back to 0 and look: the generic part may already be right.**
- The user: "yes start with the leaner face" (`head-fat` 0, `cheek_fullness` 0.3, `head-round` 0), and "recreate all
  5 face poses from the bible for the comparison shots to me please". **Head comparison shots are the sheet's five
  views in its order**: `-- look <spec> <out> face face_quarter_r face_side_r face_quarter face_back --posed` (the
  posed head sits upright, as the user set it; unposed, the generic neck cranes forward), stacked under the sheet's
  row (`crop=1024:320:0:130`).
- Nose round one (by eye): `nose_size` 1.0, `nose_tip_up` 0.5, `nose_tip_width` 1.2, `nose_base_width` 1.0,
  `nostril_width` 0.9, `nose-greek` 0, `nose-curve-convex` -0.2. Widths past about 1.2 with `nose_flare` tear the
  nostril rims (a snout). Still smaller and more upturned than the sheet's large, low-hanging ball of a nose.
- `head_overlay.py` + `figures/brother_head.sheet.json` (the user: "line up the center of the noses, then overlay
  them and show me"): for each of the sheet's five views the model's head is scaled to the drawing's crown-to-chin
  height, moved so the nose tips coincide, and drawn half see-through over the art; rows: art, overlay, model alone.
  First use showed what outlines and scores had hidden: with the noses together the model's crown stands far above
  the sheet's. His nose tip is about three quarters of the way down his head (the sheet's: 57%), and the lower face
  is short, since the chin sliders went back to 0. The up-and-down layout of the face (brow, eyes, nose, mouth,
  chin) is the next thing to set, by marks.
- The squish round. The user, of the overlay: "seems like you havent quite matched the quarter turn angle" (a view
  of `head_overlay.py` may give its `turn` in degrees: the sheet's are about 35 right and 45 left, not 45 and 45),
  then "I think mostly what needs to happen is his head is too tall, and needs to be \"squished\" a little, shorter
  and wider". `face_levels.py` prints where the brow, eyes, nose tip and mouth sit between crown (0) and chin (1)
  and the head's width and depth to that height; it takes `slider=value` trials. The sheet: eyes 0.45, nose tip
  0.57, mouth 0.72; wide 0.80, deep 0.86. The model was eyes 0.49, nose 0.65, mouth 0.76; wide 0.75, deep 0.89.
  Now `forehead-scale-vert` -0.5 and `head_height` 0.1 (the skull above the eyes shorter), `head.size` x1.085 to
  keep his head's height on the body, and `head.depth` 0.82: eyes 0.46, nose 0.63, mouth 0.74; wide 0.83, deep 0.86.
  **Do not shorten a head's depth with `head_depth` / `head-back-scale-depth` past about -1**: at -2 they dented the
  skull behind the ears; the bone control `head.depth` scales the whole head front to back cleanly. And
  `forehead-scale-vert` at -0.9 squared the top of the skull; -0.5 keeps it round. These are held out of the head fit.
  Left: the nose tip is still low (0.63 against 0.57), which is the nose's own shape, for its next round.
- The user: "looks like his crown is still too tall, and his jaw needss to be just a hair wider". In the overlay the
  crown's height over the sheet's is the NOSE TIP's level, not the skull: the heads are the same height and the
  noses are put together, so a nose tip that sits low pushes the whole model up. The eyes were already at the
  sheet's 0.45. So: a little more off the skull (`forehead-scale-vert` -0.7, `head_height` -0.1, with `head.size`
  x1.064, `head.width` 0.94 and `head.depth` 0.77 keeping his head's height, width and depth as they were), and the
  nose tip and mouth raised (`nose_length` -1, `nose-trans-up` 1, `mouth-trans-up` 0.75): nose tip 0.58 (sheet
  0.57), mouth 0.73 (0.72). `jaw_width` 0.5 (0.25 for the user's hair wider, the rest making up for `head.width`).
  The crown, jaw, eyes and mouth now sit on the sheet's in all five views. The nose is squeezed short by this: its
  shape (a broad low ball on the sheet) is the next round.
- Nose round two. The user: "looks like his nostrils are too scrunched nad thebottom is too flat compared the arts
  fuller nose". The scrunch was `nose_length` -1 (it squashes the nostrils with the nose). Now `nose_length` -0.3
  with `nose-trans-up` 1.7 carrying the height instead, `nose_tip_up` 0.1 (was 0.5: the upturn flattened the
  underside), `nose-base-up` -0.2, `nose_flare` 0.3, `nose_size` 1.2, `nose-nostrils-angle-up` -0.5 and
  `nose-compression-uncompress` 0.6 (the other way, +0.5 and -0.6, gave a flat wide tip). Nose tip 0.60 (sheet
  0.57). `nose-trans-up` this high crowds the bridge into the brow: watch the crease between the eyes.
- The user (green marks on the profile overlay): "Chin needs to be up and forward a bit and lower nose not bend up but
  bulge down". `chin_forward` 0.6, `chin-prognathism` 0.3, `chin_height` -0.2; `nose_tip_up` -0.1 and
  `nose-base-up` -0.5 (the base hangs lower under a level tip). `nose_tip_up` -0.5 was tried first and hooked the
  nose into a beak that dropped its tip to 0.65: small steps on that one. Nose tip 0.62 now.
- The exact profile. The user: "You didnt do the full turnaround" (a profile-only crop had been sent: head pictures
  are always all five views), then "you need to line up that side profile sillouette like, exactly, the face is
  important, and also the ear is clearly too small and high and forward", and "be sure hes turned 90 degrees to the
  right".
  - **`square_head`** (`figed_fit.py`): before a head view is drawn (fit and `head_overlay.py`) the posed head is
    turned so its eye line is level and straight across; the hand-set pose left it 0.3 degrees turned and 1.4
    tipped. A head view may also carry a nod, the `tilt` slider (the sheet's profile: -1 degree;
    `head_overlay.py --tilt -1`).
  - `figures/brother_profile.fit.json`: the profile view with its face edge weighted six times (a region) and only
    profile-shaping sliders moving (forehead, brow, nose, lips, chin, neck front, head depth); the front view rides
    along at 0.3. Profile overlap 0.98: the face edge is on the sheet's to about a pixel of this 1024-pixel sheet.
  - `ear_levels.py` prints the ear's top and bottom between crown and chin and its edges between the back of the
    head and the nose tip. The sheet's ear sits far back (0.18 to 0.37 of the way from the back of the head to the
    nose tip, 0.41 to 0.69 down); the model's was at 0.32 to 0.54. Now `ear-trans-forward` -3.0, `ear-trans-up`
    -0.1, `ear_size` 0.8, `ear_out` -0.4. The points this measures take in skin round the ear, so read its numbers
    as about a third larger than the ear looks. `ear-trans-forward` this strong sweeps the ear's shape back a
    little: a candidate for a small correction.
  - `brother_head.fit.json` no longer moves any face, ear or neck slider.
- The user, of that: "You deformed the back of his skull" (a ridge and dent running down behind the ear in the
  three-quarter and profile views). Cause, found by taking settings off in turn: `ear-trans-forward` -3. The target
  drags the skull's skin with the ear, so past about -1 it ploughs a ridge. Now -1.0: the skull is clean and the
  ear is only part of the way back (0.27 to 0.52 from the back of the head to the nose tip; the sheet's 0.18 to
  0.37). **Keep `ear-trans-forward` within about -1 to 1.** Moving the ear the rest of the way needs a correction
  that moves the ear alone, not this slider.
- **`ears`, the third small correction** (`Figure._move_ears`). The user: "No yea dont drag the skin, just cut out
  the ear and resize and move it without changing the rest of the face". `"ears": {"scale", "back", "down", "out"
  (cm), "reach" 5, "reach_front" 2}`: the ear (the points MakeHuman's `ear-wing` target swings: the flap alone) is
  scaled about its middle and moved as one rigid piece, carried to the skull's surface at its new place; the skin
  round it slides with it and every slid point is set back ONTO THE HEAD'S SURFACE AS IT WAS, fading out 5 cm
  behind the ear and 2 cm in front, so the skull and face keep their shape. All ear sliders are back at 0 for him.
  The brother's: scale 1.18, back 3.0, down -0.3, out -0.4 (ear 0.19 to 0.42 from the back of the head to the nose
  tip; the sheet's 0.18 to 0.37).
  Two tries that failed first, not to repeat: the `ear-scale` target as the mask (it takes a plate of skull, the
  same ridge as the slider), and letting the skin "settle" by smoothing six rings round the ear (the scalp's
  polygons are large, six rings reach the crown, and thirty smoothing passes collapsed the skull to a cone).
  Left: faint stretch lines in the skin just in front of the ear, and from the front his ears stand out less than
  the sheet's.
- The user, of the first `ears` version: "You're moving too much of vertexes around the ear its deformed" (creases
  at the temple and under the ear). Moving the flap with NO skin at all was tried and is worse: the ear's bowl is
  part of it only loosely, so the ear tears and a stretched plate is left where it stood. The creases came from
  how slid skin was set back on the skull (onto the tangent plane of the nearest POINT: facets on this coarse
  mesh). Now it is set onto the nearest point of the head's own TRIANGLES (mathutils BVHTree; the ear's faces left
  out and its footprint capped), so the skin round the ear keeps the skull's shape exactly and only its points'
  spacing changes. `reach` 5 behind, `reach_front` 3.5 (0 = the ear alone). `EAR_FROM` 0: the whole of what
  `ear-wing` moves is the ear; at 0.10 the bowl was left behind.
