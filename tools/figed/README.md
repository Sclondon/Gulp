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
- The user, with the temple, the skin round the ear and the skull behind it circled: "Yes its clearly still not
  moving smoothly". Tried and rejected again: the whole `ear-wing` set moved with no skin (`reach` 0): the set is
  not the complete ear (bits of the bowl stay) and the faces behind fold; it tears. What changed: slid skin is now
  set onto the head as a CURVED surface (Phong tessellation in `onto`: the nearest triangle point lifted towards
  the tangent planes at the triangle's corners, 0.75), not onto flat triangles, whose facets were the dents. A
  little smoother; NOT confirmed by the user. If it is still not good enough, the honest fallback is the ear by
  sliders only (`ear-trans-forward` within -1: clean, but about 1.5 cm forward of the sheet's) and the move done by
  hand in Blender's sculpt tools at the small-corrections stage: relocating an ear 3 cm across a mesh this coarse
  by arithmetic has now failed four ways.
- **The ears are cut off and reattached** (the user, after two more tries at moving skin: "Cut the ears off, smooth
  over the hole, then reattach in at the right spot size and angle"). This replaces every earlier `ears` version.
  `"ears": {"cut": true, "scale", "back", "down", "out" (cm), "tilt", "flare" (degrees)}`:
  - `Figure._move_ears`: the head's skin does not move. The ear's own points (and the floor of its bowl) are drawn
    tight like a skin across where the ear stood, held by the skin round them (150 passes of plain averaging,
    `settle`): the head is left whole, no ear and no hole. The ear's flap is kept aside as `fig.ear_pieces` (side ->
    points, where each now stands): scaled about its middle, turned (`tilt` leans the top back, `flare` swings the
    back edge out), carried `back` / `down`, and seated on the outer skin at the new place by the foot of the flap
    (the inner 30% of it); `out` negative sinks its cut edge under the skin.
  - `figed_blender.cut_ears`: adds each piece to the body mesh as a copy of every face that is wholly flap, with
    its UVs, weighted to the head. In a posed build the pieces are posed with the head (`ear_pieces_posed`).
  - What is ear: the flap = what `ear-wing` moves by more than `EAR_PIECE` (8%) of its most; what is smoothed over =
    all of what `ear-wing` moves, plus skin cut off from the head without it, plus the skin inside the outline of
    the flap's join seen from the side (the bowl's floor: the flap curls round it in a C).
  - The brother's: scale 1.18, back 3.0, down -0.3, out -0.4, tilt 8, flare 8.
  - Failed on the way, not to repeat: cutting the joining faces and capping the hole by hand (the hole is a C, not a
    loop; several loops on one side); a sphere fitted to the skull as the cap (bulged); seating the piece by the
    middle of the join (the join's points include the ear canal, far inside: the ear floated 2 cm off the head);
    forgetting to pose the pieces with the head.
  - **The outline fits do not see the ear pieces** (the Sampler draws the base's faces: the head with no ears).
    Head and body fit jobs score slightly differently for it; ears are set by `ear_levels.py` and by eye.
- **The overlay's light matches the sheet** (the user: "adjust he lighting in the reference scene until the ahdows
  match up with the bible art as well"). The sheet paints every view with the same soft lamp above and a little to
  the left of the viewer (the crown is brightest in all five, the back view as light as the front), so the lamp goes
  with the camera: `head_overlay.py` turns on Workbench shadows with `light_direction` (-0.25, 0.85, 0.45) and
  `shade` 0.3 (a sheet may give its own `light` / `shade`). A lamp fixed to the head was tried first: the back view
  went black, which the sheet's is not.
- The user (a line down the back of the jaw in the three-quarter view): "The ears are way too far back they should
  like up with the jaw like in the art". `ears.back` 3.0 -> 1.6: the ear's front edge meets the back of the jaw.
  **Place an ear by the jaw, not by the back of the skull**: measured from the back of the head the 3.0 matched the
  sheet's profile, but his jaw ends further forward on his head than the sheet's does, so an ear put there stood
  behind a gap. In the profile overlay the ear is now about half its width forward of the sheet's: the real
  difference is the jaw's (and skull's) depth, not the ear, and is not fixed.
- The user: "A little more forward and a little lower": `ears.back` 1.6 -> 1.0, `ears.down` -0.3 -> 0.4.
- The user: "his jaw should be little bit wider as well": `jaw_width` 0.5 -> 0.85.
- The user: "jaw just a bit wider still, and ear just a bit more forward": `jaw_width` 0.85 -> 1.15, `ears.back`
  1.0 -> 0.5.
- The user (red lines: straight down from the ear, a corner, then a diagonal to the chin): "Can we raise the corners
  of his jaws up so he has a sharper jawline?". `head-square` 0.5 gives a clear jaw corner and a sharp edge under
  the jaw. `jaw_drop` -1.5 was tried and only lumped the chin. Two costs of `head-square`: it also flattens the top
  of the skull a little, and its corner sits LOW (about level with the chin), where the user drew it about level
  with the mouth. Raising the corner itself is not something a slider does: a small correction, still owed.
- The user, of `head-square`: "You lowered it instead of raising it". It is out (0). **`jaw_corner`, a small
  correction** (`Figure._jaw_corner`): `{"lift": cm, "radius": cm, "below_ear": cm, "forward": cm}` raises the skin
  within `radius` of a point under where the ear grows from the head, fading smoothly to nothing at the radius. The
  brother's: lift 2.0, radius 4.5, below_ear 6.5, forward 0.5. The effect is modest; where the point sits against
  his real jaw corner has not been checked with a marker.
- The user: "Mark where you placed it how am I supposed to lnow what 6.5 cm looks like on a screen".
  `head_overlay.py` now draws every `jaw_corner` on the overlay and model rows: a red cross at its centre and a red
  ring at its radius, carried with the posed head. **Show where a correction acts on the picture; never describe a
  place to the user in centimetres.**
- The user marked the jaw corners with blue crosses on the sheet row and the model row
  (`tools/art_src/user_brother_jaw_corners.png`): the sheet's are just under the ear lobes at mouth level, the
  model's about 4 cm lower, near chin level, and further in. `jaw_corner` gained `inward` (cm towards the middle)
  and leaves the neck behind the ear alone; the brother's is now centred on the user's marks: lift 2.2, radius 4.5,
  below_ear 8.9, forward -0.2, inward 2.5. First tried at lift 3.5 / radius 5.5: it pinched the back of the neck
  and cut a notch under the ear. At 2.2 the jaw's underside rises towards the ear, but a hard crease is left behind
  the jaw in profile: a radial lift is a blunt tool for this. NOT confirmed by the user.
- The user: "Mark the reference jaw corner on the overlay as well, then align them". A sheet view may carry `"jaw"`:
  the jaw's corner as marked on the drawing; `head_overlay.py` draws it as a BLUE cross on the art and overlay rows,
  and the model's corner (where `jaw_corner` carries it) as a RED cross with its reach as a ring. `jaw_corner` now
  moves the corner three ways (`lift` up, `back`, `out`, cm), not only up. From the user's marks the model's corner
  was about 3.7 cm low, 1.7 cm forward and 2.2 cm in of the sheet's; after one look at the crosses: lift 2.9, back
  0.9, out 2.2, radius 6.5. Red sits on blue in the front and profile views; in the three-quarter views red is
  about half a centimetre behind blue (the marks in the different views do not agree exactly). This gave the
  clear jaw edge rising to the ear that sliders and the earlier lift did not.
  **Method that worked: mark the same landmark on drawing and model, draw both on the overlay, move one onto the
  other.** Use it for other landmarks (ear, eye corners, mouth corners, nose wings).
- The user: "the ears are actually a little too far forward" and "theres a gap at their seam with the head, the are
  floating". `ears.back` 0.5 -> 1.0; `ears.out` -0.4 -> -0.65 and `flare` 8 -> 7 (the cut edge sunk further under
  the skin). At `out` -1.0 the ears were half buried. Check the seam in the back view after any ear change.
- Sculpting by hand (the user: "You're saying its easy to shape the jaw by hand? Direct me in blender").
  `sculpt_session.py`: `-- make <spec> <work.blend>` (headless) builds the figure at rest with its points remembered
  (`figed_rest`), opening that file with the script switches to Sculpt Mode (side view, mirror on, Grab brush), and
  `-- read <out.sculpt.json>` writes how far each base point was moved. NOT YET DONE: `Figure` applying a
  `"sculpt"` file. Two traps hit: building the figure INSIDE an open window (`read_factory_settings` there)
  crashed Blender at the user's first `F` (build headless, open the file); and in 4.3 brushes are assets,
  `wm.tool_set_by_id("builtin_brush.Grab")` does nothing (use `brush.asset_activate`; untested in a window: the
  user can press `G`).
- **`sculpt`, the hand correction, works end to end.** A spec's `"sculpt": "<file>"` names a `.sculpt.json` and
  `Figure.to_blender` adds its moves last. The user's first sculpt of the brother's jaw is
  `figures/brother.sculpt.json` (832 points, up to 24 mm, read from `work/brother_sculpt4.blend`). The moves are
  differences from the figure AS IT STOOD when the sculpt file was made: change the head's sliders much afterwards
  and the sculpt no longer fits (re-sculpt, or sculpt again on top: a new `make` starts from the figure with the
  old sculpt in it, and `read` then gives only the new strokes, which must be ADDED to the old file, not put in
  its place. Not built yet).
  More traps of the session, all hit: entering Sculpt Mode in the window is an undo step (the user's first Ctrl+Z
  left the mode, and G then moved the whole object): `make` saves the file already in Sculpt Mode; the Grab brush
  only takes if activated a few seconds after the window opens (a second timer); both checked in a test window
  that reports and quits. Reference pictures: the shaved sheet as two image empties (`bible_front`,
  `bible_profile`) placed by the nose and sized by crown-to-chin, shown only in straight-on orthographic views, put
  into the user's live window through the Blender MCP (worth moving into `sculpt_session.py make`).
- Second sculpt session (`work/brother_sculpt5.blend`, with the reference pictures): 297 more points, read with
  `--add` onto the first: `figures/brother.sculpt.json` is now 924 points. The user, with lines on a screenshot of
  the profile with the bible over it: "his ear is too far forward and needs to be angled backwards a bit":
  `ears.back` 1.0 -> 3.0, `ears.tilt` 8 -> 16; in the profile overlay the ear now lies over the sheet's.
  What the session taught (all hit by the user): the user has NO NUMPAD (the session turns on Blender's numpad
  emulation; views are top-row `1` and `Ctrl+3`); before emulation was on, top-row `Ctrl+3` in Sculpt Mode added a
  MULTIRES modifier at level 3 and the body stopped drawing (only eyes and teeth showed) until it was removed;
  reference pictures at 45% hid the model, 22% is right; a plain middle-drag tilts the view and the pictures (shown
  only straight on) vanish: say so up front; open windows on the main monitor (`--window-geometry`), the user's
  words: "stop using monitor 3".
- The user, of the ear in the sculpt window (the sheet's ear outlined in blue, much wider): "the ear looks
  scrunched? and it has an open seam on the backside and his not conncted to the head". `ears.wide` (new: the ear
  broader front to back before it is turned) 1.4, `out` -0.65 -> -0.35 (sunk less: sinking hid its front),
  `flare` 7 -> 4; and `cut_ears` now carries the piece's cut edge 1.8 cm INTO the head as a skirt, so no open rim
  shows behind the ear. Better, not finished: from behind the skirt still reads as a hollow shell. The honest fix
  is to weld the ear's rim to the head's skin (bridge the two loops), which the smoothed-over patch makes hard to
  do by rule; a candidate for doing once by hand.
- Texturing: the user, same message: "We should also start figuring out his texturing". Not started; options put
  to the user (a far-reaching choice).
- Eyes and lips (the user, marks on the profile in the sculpt window): "his eyes need to be bigger and sit back a
  little further, and his lips need to be softly rounded not flat. Also, his eyes need the downturn soft slant and
  epticanthal tilt". By sliders, by eye: `eye_size` -0.2 -> 1.5, `eye-push1-out` and `eye-push2-out` -0.5 (negative
  sets the eye back; positive opens it wide and forward), `eye_outer_corner_up` -0.6 -> -1.0,
  `eye-epicanthus-out` -0.7 (which sign is the fold was a guess: check close up), `mouth-upperlip-volume` 0.9,
  `mouth-lowerlip-volume` -0.2 -> 0.9, `mouth-scale-depth` -0.4 -> 0.6 (positive rounds the lips forward in
  profile; negative was the flat mouth).

## Paint (2026-11-20, first try)

The user: "We should also start figuring out his texturing", then, of three ways offered (project the bible and touch
up; a ready-made skin tinted; hand painting): "do the texture projection as a first try".

- `paint_project.py <spec> <sheet> <out.png> [shots.png]`: for every texel of the head's skin (MakeHuman's own UV
  layout: no new unwrap), the point of the posed, squared model it belongs to is looked up in each view of the head
  sheet (placed as `head_overlay.py` places them) and the views are mixed by how squarely each sees that skin
  (facing cubed), only where the drawing has figure (its cut-out); texels no view sees and everything below the
  neck get the sheet's median skin colour. The cut-off ears are painted where they stand. Output
  `figures/brother_skin.png` (2048); `shots.png` draws the painted model flat lit from the five angles.
- First result: recognisably him (brows, eye bags, nose, smile, cheek shading land on the right forms). Wrong, in
  order of how much they show: the eyeballs are a separate mesh and are blank white; the drawing's dark OUTLINE is
  projected as lines (over the crown, round the neck's edge, where a view's silhouette falls on skin another view
  also sees); the ears are doubled (the sheet's ear is not where the model's is in every view, so ear paint lands
  on the head beside the ear); the mouth line is doubled where front and three-quarter views disagree; no occlusion
  test (the nose's far side takes cheek paint); the drawing's light and shade is still in the paint (to be taken
  out so the game's light is not doubled); the sheet is only 1024 px wide, so the paint is soft.
- Next, in order: erode each view's cut-out a few pixels (kills the outline lines); weight views more sharply and
  drop a view's vote where its colour disagrees with the better-facing view (kills doubles); paint the eyes;
  a depth test per view; then de-light.
- The user (the model's front beside the sheet's): "his eye shape and nostril shape is wrong, and his nose needs to
  go lower he has too much upper lip". Eyes narrowed to the sheet's smiling squint: `eye-height1` -0.4,
  `eye-height2` -0.7, `eye-height3` -1.0 (the lid opening, inner to outer), `eye-eyefold-angle-up` -0.8,
  `eye_size` 1.5 -> 1.2. Nose lower and nostrils rounder: `nose-trans-up` 2.0 -> 1.4 (the profile fit had raised
  it to 2), `nose-base-up` -0.5, `nostril_width` 1.2, `nose_base_width` 1.2, `nose_flare` 0.45,
  `nose-nostrils-angle-up` 0.2. `nose-trans-up` at 1.0 with `nose-base-up` -0.9 hung the nose over the mouth.
  Nose tip level 0.63 now (the sheet 0.57 by Claude's earlier reading: the user's eye says lower is right, and the
  user's eye rules). The paint (`brother_skin.png`) was projected before this and should be projected again.
- Second projection. The user: "just project the fotnad back views, and the ears shouold come from the side view".
  `paint_project.py` now uses only `face` and `face_back` for the head (which one by whether the skin faces forward
  or back, a narrow blend where it faces sideways) and `face_side_r` for the ears (his left ear by mirror); the
  three-quarter views are not used. Each view's cut-out is shrunk 4 px (no outline lines), and skin outside a view's
  outline on a row takes that row's edge colour (so the side of the head, edge on to both views, is not bare).
  Result: front and back are clean and read as him; no doubled mouth, no outline lines. Wrong: the side of the head
  and the shoulders are STREAKED (one edge pixel dragged across: the side has no view of its own by the user's
  rule); a pale patch round each ear (the smoothed-over head under the ear shares the ear's texels, and the ear's
  paint spills past its outline); eyeballs still blank; the drawing's light still in the paint.
  Made before the user's eye and nose changes settle: project again when the face is agreed.
- Third projection. The user: "okay just use his front facing one for the head texture at first".
  `paint_project.py ... --front`: the front view alone for the head (ears still from the side view, Claude's
  reading); skin that faces away from the front is left the plain skin colour (not painted through to the back),
  with the same edge-colour streaks where the head turns sideways. `brother_skin.png` is this version.
- Painting by hand: `sculpt_session.py -- make <spec> <work.blend> <sheet> --paint <skin.png>` builds a file in
  Texture Paint mode with the skin PACKED in it (so Ctrl+S keeps the paint), opened flat lit with the texture
  showing and the reference pictures hidden; `-- read-paint <out.png>` writes the painted skin back. Opening in the
  right mode is checked in a window; that painted strokes survive a save is NOT yet checked.
- Fourth projection, head and body. The user: "and do his body as well", then "actually the back projection looked
  good, just smoothly blend them with the skin tone together". `paint_project.py ... --body <fit job>`: the body
  below the chin from the body job's `front` and `back` views of the main body sheet, using the fit's own mapping
  (`View.project`) with the model standing as the job stands it. Head and body alike: each view paints skin that
  faces it, fading to the plain skin tone as the skin turns side on (`SIDE_FROM` 0.12 .. `SIDE_TO` 0.6 of the
  normal) and towards each view's outline (`feather`); no edge colour is pulled round the side any more (that made
  the streaks). `brother_skin.png` is this version: his chest hair, tattoos and drawers land where the sheet has
  them. Known: the DRAWERS are painted on the skin (see the shorts question); tattoos are in the paint, where the
  agreed design has them as separate movable overlays; flanks, inner arms and legs and the top of the shoulders are
  plain skin tone; eyeballs blank; the drawings' light is still in the paint; a pale patch behind each ear.
- The ear's skirt is now a cone to one point inside the head (the user: "the back of his ears have some strange
  geomtery": the straight skirt showed as a hollow tube).
- Fifth projection. The user (blue marks on the painted model: the eye openings above the painted eyes, the nose's
  base above the painted nostrils; and a side view): "the eyes and nose are misalinged you can see from the
  projection they arent shaped quite right, and theres sa seam in the texture down his side"; then "I guess you
  can try filling in with a side propction as well but it needs to blend well".
  - **The paint is a measure of the model**: where a painted feature and the model's feature disagree, the model is
    off. But only if the paint hangs from something that does not move: the head's views are now placed across by
    the nose and UP AND DOWN BY THE CROWN (crown and chin both on the sheet's), not by the nose tip, which every nose
    edit moved. With that, the nose sits on its paint as it was (the nose changes tried were undone) and the eye
    openings were about a centimetre low: `eye_height` 1.8.
    A mistake on the way, not to repeat: the anchor and the eye slider were changed in one step, and the two errors
    added up (eyes far below the paint). One change, one look.
  - The body's side: skin that faces sideways on the trunk, neck and legs is painted from the ARMLESS sheet's side
    view (`armless_side` of the body job; the main sheet's side view has the arm over the flank), blended into
    front and back by the skin's facing; arms keep front and back only, each pulled in at most `PULL` (10) pixels
    from outside its outline. No band of plain skin and no long streaks down the side.
  - Left: a smudge on the outer upper arm (front and back disagree there), eyeballs blank, the pale patch behind
    each ear, dark lines under the jaw from the sheet's outline, the drawings' light still in the paint.
- Sixth projection, from the user's notes on the paint window (2026-11-20): "the eyes dont have the downards tilt"
  (`eye_outer_corner_up` -2.5, `eye_inner_corner_up` 0.6); "the ear projection is very messed up" (the ear is now
  painted BOX TO BOX, the model's ear onto the sheet's `"ear"` box in the side view, and the flattened head under a
  cut-off ear has its UVs sent to a corner of plain skin, so it no longer shows ear paint); "the under side seems
  to have gotten messed up" (white: samples had been pulled in along a row and landed on the paper between arm and
  body; now each body view's colours are carried `PULL` pixels out from the figure's true edge, `spread`); "double
  nipples and shoulder smearing- and he should have no tattoos- those should be positionable separate textures"
  (the side view is used only squarely side on, 0.75..0.95; skin facing neither front nor back fades to skin tone;
  TATTOO INK IS PAINTED OUT of the body views: dark, red minus blue under `INK` 0.17, grown 7 px, filled from the
  skin round it, the drawers' pale cloth and its shading left alone); "his lip line is misaligned" and "his
  modeled mouth isnt wide enough" (`mouth-trans-up` 0.9 -> 1.6, `mouth-scale-horiz` 0.7 -> 1.5).
  Owed from this: the tattoos as separate movable pictures (cut from the sheet before the ink is painted out); the
  drawers as a garment ("his wastband isnt a clean line anymore": front, back and side views disagree where they
  meet, and the ink pass smudges the cloth's shading a little); eyeballs.
- `session_keys.py`: F5 texture on/off, F6 Sculpt <-> Texture Paint, in every figed window (the user: "is there a
  way for me to toggle on and off the texture? and to get to sculpt mode?"). A paint file has `figed_rest`, so
  sculpting in it is read by `-- read` as usual.
- The user: "you did the eyse backwards, the tilt down inwards" (blue lines: the openings sloped down to the nose).
  **In this base `eye-corner1` is the OUTER corner and `eye-corner2` the INNER** (the aliases `eye_inner_corner_up`
  = corner1 and `eye_outer_corner_up` = corner2 in `figed.py` are named the wrong way round: to be swapped).
  Now `eye_inner_corner_up` -1.3 (outer corner down), `eye_outer_corner_up` 0.4.
- "f5 doenst turn off texture": Texture Paint mode always draws the texture whatever the shading says, so F5 from
  paint mode now goes to Sculpt Mode in grey (F5 again: the texture in Sculpt Mode; F6: back to paint).
- The user, of the grey face: "his eyes are getting worse, he looks asain now whats going on". Eleven eye sliders
  had been stacked over four rounds (size, two push, two corners, epicanthus, three lid heights, fold angle, bags),
  each a by-eye answer to one note; together they made a narrow slanted eye that is not his. ALL are cleared: the
  eye is MakeHuman's own again, with only `eye_height` 1.8 (its place, set from the paint). The same lesson as the
  jaw: **when a part has taken more than three or four sliders and looks worse, put them all back to 0 and look.**
  His eye's character (heavy lid, soft bags, slight downturn) is mostly in the PAINT; the opening only has to be the
  right size and place. Shape changes to the eye from here: one at a time, or by the user's hand in Sculpt Mode.
- The user sculpted in the paint window (F5/F6) and saved: 2,341 more points (up to 22 mm; nose and lower face),
  added to the sculpt: `figures/brother.sculpt.json` is now 2,987 points. It was sculpted on the face with the old
  eye sliders and applied to the face with the eyes reset: looked at together and it holds. The skin picture in
  that window (possibly hand painted) is kept as `work/brother_paint4_user_skin.png`, NOT merged: the skin has
  been re-projected since. Merging hand paint with a new projection is not solved (a hand-paint layer over the
  projection is the likely way).
- The user (red lines on the profile in the window, bible on): "his eye is in the wrong spot, and his head is
  shaped slightly odd". The eye: `eye_height` 1.8 -> -1.0. It had been RAISED to meet the paint while the paint
  was hung from the crown; the window's bible is hung from the nose tip, and by that the eye was a centimetre high.
  **Everything the user sees is aligned ONE way: by the nose tip** (`head_overlay.py`, the sculpt window's
  pictures, and `paint_project.py` again). With that, the model's eyes lie on the sheet's in front and profile.
  The skull: `head-back-scale-depth` 0.9 was tried on a reading of the user's line and taken out again: the overlay
  shows the model's skull already standing ABOVE and BEHIND the sheet's (crown about 1.5 cm high with the noses
  together), not short of it. What the user meant by the line is not settled: asked.
- The skull (the user, with the bible over the un-posed profile, `tools/art_src/user_brother_skull_profile.png`):
  "the skull isnt fitting the shape- too tall, and missing at the back".
  - **Check a head against its sheet UN-POSED** (`head_overlay.py` without `--posed`): the pose the user set for the
    body sheets pitches the head, and a posed overlay showed the back of the skull beyond the sheet while the user's
    window (rest pose) showed it short. The window is what the user judges by.
  - **`pushes`, a small correction** (`Figure._push`): broad smooth pushes of the skull, like one stroke of a grab
    brush: `{"anchor": "crown" | "skull_back", "up", "move": [out, back, up] cm, "radius": cm}`.
  - What was tried, all judged in the overlay (which scales the model's crown-to-chin to the sheet's, so lowering
    the crown makes everything else read bigger): `forehead-scale-vert` -1.2 with `head-back-scale-depth` 0.9
    (a lump at the nape); crown down 2 cm (a flat top, and the back then overshoots); crown down 1 and back 1 to
    1.6 (back overshoots). Applied: crown `move` [0, 0.5, -0.8], radius 13: a part of the way. The crown still
    stands a little over the sheet's. One stroke of the user's Grab brush with the bible on would do this better
    than more arithmetic.
- The user, of the crown push: "no its worse, just undo that". `pushes` removed from the brother (the code stays,
  unused). His skull is as it was before that round; the skull's shape is left for the user's hand.
- Fourth sculpt (in `work/brother_paint8.blend`, bible on): 4,490 more points; `brother.sculpt.json` is 5,073
  points. The user: "his mouth needs to be a little wider and I messed up his eyer brows", then "no I meant I messed
  up his eye lids not his eyebrows". `sculpt_restore.py -- <before.sculpt.json> <now.sculpt.json>` puts ONE AREA
  of a sculpt back to what an earlier file had, fading at the area's edge (the area = where MakeHuman's own targets
  for that part move the skin; it is written for the eyelids, the list of targets at its top is the thing to
  change). 1,124 eyelid points put back. `mouth-scale-horiz` 1.5 -> 2.1. Paint re-projected.
  Not certain: an earlier run of the same script on the EYEBROW area was stopped by the user as it started; the
  mouth value shows part of that command had run, so the last session's brow strokes may have been put back too.
  The window's skin is kept as `work/brother_paint8_user_skin.png`.
- Features moved onto the sculpt (the user: "could you separate out his eye nose eye mouth etc part of the texture,
  and then position them better ontou our sculpt?"). The sheet may give `"features"` in its FRONT view (iris centres,
  nostril wings; `_l`/`_r` his own sides); `paint_project.py` finds the same feature on the model and shifts the
  paint's lookup so each drawn feature lands on the model's, the shift fading with distance (`feature_reach`, 13
  sheet px) so the skin between follows smoothly. Used: `eye_l`, `eye_r`, `nostril_l`, `nostril_r` (shifts of 1 to
  4 px). NOT usable as tried: `nose_base`, `mouth`, `mouth_l`, `mouth_r`. The model points taken for them (where
  the `nose-base-up`, `mouth-trans-up`, `mouth-scale-horiz` targets move the skin most) are not on those features
  (15 px off) and carrying paint to them bent the mouth into a moustache shape. Mouth corners need proper points
  (the lip line's end vertices) before they can be used.
- **Eyes** (the user: "finish the head"). MakeHuman's eyeballs have a speck of UV space inside the body's texture,
  so `figed_blender.build` now gives the `eyes` mesh UVs of its own (each ball seen from straight ahead fills the
  square) and `paint_project.py` writes `figures/<name>_eyes.png` (256): white, a hazel iris (amber-brown at the
  pupil to olive green, a dark ring), drawn by rule round the middle; not from the sheet, where an iris is six
  pixels. Paint windows and the shots load it. Two tries failed first: painting through the old UVs (a few texels)
  and assuming the two eyes share UVs (they do not).
- Head still owed: the ears welded to the head (pieces pushed in, with a cone behind); the sheet's smiling squint
  (the lids are the generic open eye); the drawing's light taken out of the paint; the hair, moustache and stubble;
  the paint is soft because the shaved sheet is 1024 px wide.
- **Hand paint is kept as a layer** (the user: "i cleaned up his torso paint"). `figures/brother_skin_hand.png`:
  the user's painted skin, its alpha where it differs from the projection it was painted on
  (`hand_layer.py -- <painted.png> <projection it was painted on.png> <out_hand.png>`); `paint_project.py` lays it
  back over every new projection (`--no-hand` leaves it off). First layer: 24% of the picture, the torso, arms,
  drawers and feet cleaned of smears and leftover ink. A LATER hand session must be differenced against the skin
  that window started from (which already has the first layer in it) and its result laid over the old layer, not
  put in its place: not built yet.
  **A trap hit: Ctrl+S did not save the paint.** A painted image that is packed in the .blend stays as it was
  packed unless it is packed again; the saved file had the untouched projection. Recovered from the still-open
  window through the Blender MCP (`image.save(filepath=...)`). `session_keys.py` now packs dirty `figed_` images
  in a `save_pre` handler, so Ctrl+S keeps paint (added to the live window too; not yet checked in a fresh one).
- The user saved again in the same window: the saved file's skin now equals the live window's exactly (the
  `save_pre` pack works: Ctrl+S keeps paint). 15,627 more texels painted and 158 points nudged (up to 2.5 mm);
  the hand layer was made again from this save against the same starting projection, and the sculpt added.
- Third paint save (the user: "I think the texture and model look pretty good now, might need to add clothes"):
  246,000 more texels painted (the legs and feet cleaned); the hand layer is now 28% of the picture. No new sculpt.
  **The user's verdict on the bare figure: pretty good.** Next asked for: clothes. Not started; the drawers are
  still paint on the skin. Still owed on the head: ears welded, the squint, de-lighting, hair.

## Clothes (2026-11-20, first pass)

The user: "lets do the shorts and this outfit" (a front view of him in a cream vest and olive trousers with rolled
cuffs and braces hanging at the hips: `tools/art_src/concept_brother_bible_outfit.png`, 345 px wide as it arrived).

- `garments.py -- <spec> <outfit.json> <out.png> --wear tank,trousers | drawers`: a garment is the body's own faces
  where a rule f(point) > 0, CUT EXACTLY along f = 0 (every edge crossing it is split at the crossing with
  `bmesh.utils.edge_split`, the faces cut along the line with `connect_verts`, so hems and necklines are clean
  curves, not face edges), pushed out along the normals (vest 6 mm, drawers 4 mm, trousers 11 mm growing to 23 mm
  below the knee). Rules (`rules()`) are written from the joints in the rest pose, so they follow the sliders:
  trousers from 2.5 cm under the navel to 7.5 cm over the ankle, with `cuffs` and `waistband` as further bands
  over them; the vest with a scoop neck (deeper in front) and armholes as ellipses; the drawers wherever the skin
  picture is painted as pale cloth. Garments keep the body's UVs and weights (bone groups are set; the cut
  interpolates them) and carry a `posed` attribute so pictures can show them in the comparison pose.
- Paint: vest and trousers get pictures of their own (`figures/brother_tank.png`, `_trousers.png`, 1024), the
  drawing's cloth carried over BOX TO BOX from the front view (`figures/brother_outfit.json`: each garment's box
  and whether its cloth is pale or dark; other pixels in the box take the nearest cloth colour). The back takes
  the front's colours seen through: no back view exists. The drawers use the skin picture, where they were
  already painted.
- First result: reads as the drawing from the front (vest with neckline and armholes, baggy trousers, rolled cuffs,
  waistband). Known: the braces are only PAINT on the trousers (and so appear on the back too; their hanging loops
  are not modelled); the vest's back neckline and the trousers' back are guesses; cloth edges have no thickness;
  the body is whole under the clothes (may poke through in strong poses: hide covered skin when worn); the skin
  under the drawers is still painted as drawers; not wired into `-- build` (export) yet.
- The user: "the tank top needs to be more a frame shirt type, and the texture needs to frame his pecs". The vest is
  now an A-shirt: narrower straps, the scoop down to the top of the chest (front depth 0.20, back 0.11), big
  armholes cut in beside the pecs (radii 0.118 x 0.21), tighter (4 mm). Its picture is no longer taken from the
  drawing: `"paint": "shade"` in the outfit file paints a plain off-white (`colour`) lightened and darkened by the
  BODY's own painted shading under it (the skin picture's brightness, blurred 4 px over blurred 45 px, so hair and
  marks do not show), with fine ribs every 6 mm across. So the shadow under and between the pecs is exactly where
  his are. First try was clipped to pure white; the range is held to 0.7..1.06 now.
- The user: "It needs to cover up his nips, have border stitching". Armholes narrower (radii 0.095 x 0.175; the
  build prints the armhole rule's value at the nipple: 0.78, well clear). A bound edge is painted wherever the
  cloth is within `BIND` (13 mm) of the garment's edge (the rule f, interpolated per texel, is the distance in): a
  plain band without ribs, a dark seam where it meets the cloth, and a row of stitches at mid-band. It shows at
  the neck and armholes; the hem is under the trousers' waistband.
- The user: "The straps on his pants should be modeled separately not part of the art". `braces()` in `garments.py`
  builds, with the trousers, a strap each side: from the waistband's front, out and down round the hip (25 cm) and
  up to the waistband's back, 28 x 4 mm in section, with a slider on the front run; meshes of their own (`braces`,
  `brace_sliders`), plain colours, carried by the pelvis bone only (they do not swing or follow the thighs yet).
  The painted ones are taken out of the trousers' picture: the outfit file's `paint_out` boxes, inside which only
  pixels of the cloth's usual brightness and warmth are kept and the rest filled from the cloth round them.
  Traces of the painted straps still show near the waistband (the buckles' shadows).
- The user: "Its a little to skin tight, the straps are too wide, and neck too deel". The shirt: neck wider and
  shallower (half-width 0.098, depth 0.135 front, 0.09 back); armholes wider at the shoulder and ending higher
  (0.112 x 0.16, centred 2 cm above the shoulder joint), so the straps are narrow and the nipple is still covered
  (rule value 0.64); looser, 11 mm off the body on the chest, tapering to 4 mm at the waist (11 mm all the way down
  came through the trousers' waistband); the body-shading on it softened (power 0.9). Claude read "the straps" as
  the shirt's shoulder straps, not the braces.
- The user, with a photograph of a square-necked vest on a model as the CUT to follow (described here, not kept in
  the repo: a real person's photo): "the shirt fit needs to be like big straps and straight across like this
  more". The neck is now a square: `max(|x| - 0.072, line - z)`, the line 1.2 cm above the shoulder joints in
  front and 4.5 cm above behind (4 cm below was tried first and bared half the chest); the armholes back to
  0.092 x 0.175 so the straps are broad (about 7 cm) with straight inner edges; the edge band 20 mm wide and a
  shade darker (`bind`, `bind_shade` in the outfit file). Nipple rule 1.02.
- The user: "the stiching border should make up the straps", then "and not quite so square". Above the neckline
  (`INFO["strap_from"]`, set by `rules()` for `paint()`) all of the shirt is band: plain, a shade darker, stitched
  along both edges, joined to the ribbed body by a seam straight across. The neck opening's corners are rounded
  3.5 cm and its line dips 1 cm in the middle (a rounded-box rule in place of the hard square); half-width 0.078.
- The user, with red lines drawn on the render (`tools/art_src/user_brother_shirt_band_lines.jpg`: from each
  strap's inner edge straight down, then curving out under the armhole to the side): "It should run all the way
  round the arm whole, and now its not square enough". The band is now everything within the strap's width of the
  ARMHOLE's edge (`INFO["hole_d"]`: each point's distance from the armhole ellipse along the line from its middle;
  `INFO["band_wide"]`: the strap's width at the shoulder, about 7 cm), so the straps are the top of one broad band
  that carries on round under the arm, front and back, with a seam and a row of stitches along its inner edge.
  The neck's corners are back to 1.5 cm and its dip to 3 mm.
- The user: "the straps are too thick"; "his pants need to be more burlap sacky colored"; "his capri a little bit
  higher". Shirt: the neck's half-width 0.09 and the armhole's 0.104, so the straps and the band round the
  armholes are about 4.5 cm (nipple rule 0.64). Trousers: `"tint"` in the outfit file replaces the drawing's
  colour and keeps its light and dark (a dull tan, 0.60 0.51 0.38; a brighter 0.66 0.54 0.36 read as mustard),
  `"weave"` adds a sacking crosshatch every 5 mm (it shows moire in small renders). The cuff's lower edge is
  14.5 cm above the ankle joint (was 7.5), so they end at mid-calf.
- The user, with a second picture of him in the outfit (`tools/art_src/concept_brother_bible_outfit2.png`: looking
  up, a loose cream vest, dull olive-tan trousers rolled at the calf, braces hanging): "sthe straps still a little
  too thick, pants too bright, and his nips and mulsces show too much on the tank texture, it should just sublty
  frame his pecs then the rest be a lttle more loose like so". Straps and armhole band about 3 cm (neck half-width
  0.097, armhole 0.111; nipple rule 0.47); a narrow strap has two stitch rows of its own, not the edge rows.
  Trousers tint 0.47 0.44 0.35. The shirt's shade is now broad and soft (skin brightness blurred 14 px over
  60 px, range 0.8..1.04, power 0.9) and fades to none from 5 cm under the nipples down, so no nipples or stomach
  muscles show; it stands 19 mm off the body over the belly, 4 mm at the waist, and lies on the shoulders (19 mm
  everywhere made the straps float). A thin red sliver shows at the corner of his right strap: not yet found.

### The two work outfits (2026-11-20, first pass)

The user, with a sheet of two (`tools/art_src/concept_brother_bible_outfits_work.png`): "letys make these next".
Left: cream cable roll-neck jumper, yellow oilskin bib overalls on black straps with clips, black rubber boots.
Right: grey work shirt with sleeves rolled above the elbow and an open collar, dark green-black bib overalls with
brass buckles and a chest pocket, brown boots, a flat cap; forearm tattoos.

- Outfit files: `figures/brother_outfit_oilskin.json`, `figures/brother_outfit_work.json` (`prefix` names their
  pictures, `figures/brother_<prefix><garment>.png`; `wear` lists the garments to pass to `--wear`).
- New garments in `rules()`: `jumper` (to the wrists by the hand's weights, a roll up the neck to just under the
  head joint; `neck_01` is the neck's BASE, 7 cm above it is only the shoulders), `shirt` (to above the elbow, a
  collar band), `bib` (legs to 20 cm over the ankle, a bib in front to 6 cm under the shoulder joints, a lower
  panel behind), `bib_straps` (bands over the shoulders), `boots` (shafts to 27 cm over the ankle), `cap`.
- `SMOOTH` (set in `rules()`): heavy cloth is smoothed after it is pushed out, so overalls do not show the navel
  or crotch. Smoothing pulled cloth inside the thighs and seat, so THE BODY UNDER CLOTHES IS NOT DRAWN: the render
  deletes body faces whose points are all well inside a worn garment (f > 0.015). The export must do the same.
- `extras()`: hard parts no body surface gives, as convex hulls riding one bone (`_rigid` carries them into the
  pose): a boot foot round each foot (the body has toes), the cap's peak.
- `"paint": "plain"`: no drawing needed. A colour lit as if painted (the body's rest normals against a lamp from
  above, in front, his right), soft blotches, a turned edge, and `knit` (cables and stitch rows), `weave`, `gloss`.
- Rough, all of it Claude's first guess: flat colours with none of the sheet's painted folds; the jumper's
  cables run round the sleeves (they follow x) and it has no ribbed cuffs or hem; the roll neck is thin; the bib
  still follows his belly, has no pocket, clips or buckles, and its straps are plain bands; the boot feet are
  slipper-shaped hulls with no heel or sole; the shirt has no collar points, placket, buttons or rolled cuff; the
  cap is a dome with a peak, not a flat cap's forward-leaning crown; hair, moustache and tattoos are not on him.
