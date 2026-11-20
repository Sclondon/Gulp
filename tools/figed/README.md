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
    (measured, not by eye; a faint tick of the base mesh's edges remains). They are paint, later. The nipple MARK
    still works: it is a point of the skin, flat or not.
  - `elbows@side` is held to -12 or more: at -31 the forearm stuck out in front of the belly in the side view.
  Outline after: front 0.92, side 0.91, back 0.93; marks within 0.1 to 1.5% of his height.
- Still not right: the arms are thick but tube-like (no biceps or triceps bulge, no forearm swell by the elbow as the
  bible paints them); the back is smooth (no shoulder blades, spine furrow or lats as the bible paints them), the pecs
  are boxy with a hard lower edge, the shoulder cap peaks lower than drawn, the thumb's tip is pointed.
