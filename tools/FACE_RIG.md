# Faces that move: research and the decision

Written 2026-11-18 by Claude, at the user's "We should start working on facial movements as well" and "Make sure it
does research". The code is `tools/face_rig.py`; the viewer `tests/face_view.gd`. Nothing of it is in the game yet.

## What the research found

Each line: the source, and what it said that mattered here. "Unverified" marks what could not be confirmed.

### Godot 4 blend shapes (the engine this ships on)

- Godot's own Compatibility (GLES3) renderer source, `drivers/gles3/storage/mesh_storage.cpp`
  (https://raw.githubusercontent.com/godotengine/godot/master/drivers/gles3/storage/mesh_storage.cpp): blend shapes run
  on the GPU by transform feedback, **per surface, one pass per shape with a non-zero weight, over every vertex of the
  surface** (`glDrawArrays(GL_POINTS, 0, vertex_count)`); zero-weight shapes are skipped (`is_zero_approx(weight)`),
  except the last, which shares the final pass with skinning. Normals are blended; tangents are not in the blend
  passes' format. The shape count belongs to the whole mesh (`mesh_set_blend_shape_count`), so every surface of a mesh
  with shapes carries them. No cap on the number of shapes.
  => The cost is (shapes in use) x (vertices of the mesh that holds them), every frame the face moves. A head kept in
  the body mesh would push the whole body (about 3,900 vertices) through every pass; a head of its own costs only its
  own vertices.
- Godot's glTF importer, `modules/gltf/gltf_document.cpp` (raw source on GitHub): morph targets import as blend shapes
  in `BLEND_SHAPE_MODE_NORMALIZED`, positions as offsets added to the base, NORMAL and TANGENT targets imported; shape
  names come from the mesh's `targetNames` extra (Blender writes it). Driven with
  `MeshInstance3D.set_blend_shape_value(find_blend_shape_by_name(name), v)` (class reference,
  https://docs.godotengine.org/en/4.6/classes/class_meshinstance3d.html).
- Godot forum, "Extreme VRAM use for meshes with blendshapes" (https://forum.godotengine.org/t/extreme-vram-use-for-meshes-with-blendshapes/128808):
  Godot stores a shape for every vertex of the mesh, moved or not (97 MB against Unity's 11 MB for 237 shapes); the
  advice given there: few shapes, bones where bones do, and **split the face into its own mesh** so shapes cover
  fewer vertices. (No engine developer replied; the numbers are one user's.)
- Godot forum, "Blend shapes mess up normal maps" (https://forum.godotengine.org/t/blend-shapes-mess-up-normal-maps/96695):
  in Compatibility (4.3) normal-mapped materials shade wrongly on blend shapes (tangents; issue #61685). Our figures
  have no normal maps, so it does not bite; do not add one to a face that moves.
- Godot's renderer overview and GPU optimisation pages list skinning and morphs as per-vertex work; there are no
  published numbers for blend shape cost on phones (unverified: measure on a phone when one is tried).

### How games and riggers move faces

- Roblox's dynamic head specification (https://create.roblox.com/docs/avatar/facial-animation/creating-basic-heads):
  a head that animates needs a **mouth bag** inside the head holding **upper teeth, lower teeth and a tongue**, and the
  **lip vertices separated** so the mouth opens; a root face joint under the head joint. Roblox drives faces by joints
  mapped to FACS names (17 of 50 poses required for sale; a robot needs only JawDrop and two eye-closes).
- Tutsplus "Game character creation, Kila" chapters 7 and 8 (joints, then blend shapes) and 80.lv articles on stylised
  and realistic face rigs: joints for what rotates (the jaw), blend shapes for what bones do badly (lip shapes, brows,
  lids) and as **correctives over the jaw** (the mouth shape while the jaw opens). This hybrid is the usual set-up.
- Disney Research, "An Empirical Rig for Jaw Animation" (https://la.disneyresearch.com/wp-content/uploads/An-Empirical-Rig-for-Jaw-Animation-Paper.pdf)
  and a Maya jaw tutorial (courses.cs.washington.edu, "Advanced Rigging: mouth"): the jaw's pivot sets where the skin and
  the lower teeth go; the **mouth corners follow the jaw by about half**. The pivot itself (the temporomandibular joint,
  in front of the ear canal) is anatomy, not from these sources.
- Wind Waker and Twilight Princess: a fan reading of Wind Waker's data (Medium, "Link's Expressions", gordonnl:
  403 when fetched, known only from its search summary) counts 7 eye, 6 brow and 9 mouth **textures** swapped on the
  face, eyes and brows as floating planes over the hair (polycount thread). For Twilight Princess the eyes are reported
  as textured planes too (Zelda Dungeon on ClassicGameJunkie's video); how its mouths moved could not be found
  (unverified). So that era moved faces mostly by **texture swaps**, very cheap, but the user asked that the topology
  itself be poseable.
- Shape sets: Apple's ARKit has 52 shapes (`jawOpen`, `mouthSmileLeft`, `eyeBlinkLeft`, `browInnerUp`, `cheekPuff`...;
  Apple's ARFaceAnchor.BlendShapeLocation docs, Unity's ARKit enum); Meta's OVR lip sync uses 15 visemes (sil PP FF TH
  DD kk CH SS nn RR aa E ih oh ou; developers.meta.com OVRLipSync viseme reference; the plugin is end-of-life); Rhubarb
  Lip Sync (https://github.com/DanielSWolf/rhubarb-lip-sync) needs only six mouths A to F (closed MBP, slightly open
  clenched, open, wide open AA, slightly rounded, puckered) plus optional G (F/V), H (L), X (rest). Godot has Rhubarb
  add-ons (AniMesuro's "Rhubarb Lip Sync T.P.I.", "Baked Lipsync" in the asset library).
- Lids against eyeballs: "emg2face" (https://arxiv.org/pdf/2610.09304) fits a sphere to the eyeball and **remaps each
  lid vertex's distance from its centre** so none can sit inside a shell just outside the ball; Reallusion forum
  threads: a straight-line blink shape cuts through the ball on the way down (one slider cannot follow the curve).
- Mouth interiors: Roblox (above); stock low-poly "teeth and tongue rigged" kits (CGTrader) are separate strips and a
  tongue on the jaw bone; the arXiv paper 2606.08043 notes templated teeth often fail on stylised faces (so size them
  from the face's own measurements).

## Decision (Claude's pick, from the research above)

**What:** faces move by **one `jaw` bone plus 17 morph targets on a head mesh of its own**, with a mouth inside.
(Second pass: 20 shapes, adding `eyes_happy` and the blink correctives `blink_arc_L`/`_R`, and two eye bones; see below.)

- `jaw`: child of `head`, pivot at the jaw hinge found from the head (in front of and below the ear's middle, at the
  height of the cheekbone's underside). Lower lip, chin, under-jaw, lower teeth and tongue follow it; the lip corners at
  half (sealed), cheeks blended, the throat fading to `neck`, the skull and upper lip on `head`. Opening: rotate about
  the bone's sideways axis (the viewer shows how).
- Shapes, the same names on every figure: `smile`, `frown`, `mouth_o`, `mouth_wide`, `lips_press`, `cheeks_puff`,
  `brows_up`, `brows_down`, `brows_sad`, `eyes_closed`, `eyes_wide`, `squint`, `sneer`, plus halves `eyes_closed_L`,
  `eyes_closed_R`, `smile_L`, `smile_R` (wink and lopsided grin). L and R are the figure's own left and right.
- Mouth: the lips cut open along their meeting line, an inner lip roll, a dark mouth bag, upper teeth (on `head`) and
  lower teeth and a tongue (on `jaw`), one small palette picture, one material.
- Lids: moved by rotating about the fitted eyeball centre (so they slide over the ball), then pushed out to a shell just
  outside it (the emg2face remap). The eyeballs are never deformed. The captain's slits are cut open the same way as
  the lips and get eyeballs, so `eyes_wide` can pop them open; at rest they are closed slits as before.
- The head (the face material's faces, which already end at the neck in a seam the glTF splits anyway) becomes its own
  mesh `<figure>_head` on the same skeleton; the mouth parts `<figure>_mouth`. Normals at the seam are kept from the
  joined mesh, and normal changes are zeroed wherever a shape moves nothing (so no seam shows when shapes play).

**Why:** a jaw is a rotation, which a bone does exactly and for free (it rides the skinning pass); lip shapes, brows and
lids are what bones do badly at this density, and Godot runs a shape only while its weight is not zero, over only the
mesh that holds it. Laughing, shock and anger need the jaw and shapes together (`mouth_wide` and `mouth_o` are
correctives on the open jaw).

**The practice it follows:** the hybrid joint plus blend shape face of game rigs (Tutsplus Kila, 80.lv, Roblox's
mouth bag and separated lips), the Disney half-follow of the corners, a sphere-guarded blink (emg2face).

**Alternatives rejected:** bones only (Roblox's way: about 20 to 50 face joints weighted by hand per figure, harder to
keep shared across 13 figures whose heads are warped differently, and lids still clip without correctives); ARKit's
52 (a capture standard: far more shapes than hand-keyed expressions need, every one stored for every head vertex);
visemes as shapes (talking is covered by the jaw plus `mouth_o`, `mouth_wide`, `lips_press`, `smile`: Rhubarb's A =
`lips_press`, B = jaw 4 degrees, C = jaw 10 + `mouth_wide` 0.3, D = jaw 22 + `mouth_wide` 0.6, E = jaw 8 + `mouth_o` 0.5,
F = `mouth_o` 1, X = rest; add `mouth_f` for G later if speech ever wants it); texture-swap faces (cheapest, kept in mind
for far LODs and blinks, but the user asked for poseable topology); the head as a second surface of the body mesh (Godot
gives every surface of the mesh the shapes: no saving).

**Mapping to ARKit names** (for a capture tool, if ever): smile ~ mouthSmileLeft+Right, frown ~ mouthFrown, mouth_o ~
mouthFunnel+mouthPucker, mouth_wide ~ mouthStretch+mouthUpperUp+mouthLowerDown, lips_press ~ mouthPress+mouthRollLower,
cheeks_puff = cheekPuff, brows_up ~ browInnerUp+browOuterUp, brows_down = browDown, brows_sad ~ browInnerUp-browOuterUp,
eyes_closed = eyeBlink, eyes_wide = eyeWide, squint = eyeSquint+cheekSquint, sneer = noseSneer, jaw bone = jawOpen.

**Did the research change the plan in FIGURE_HEADS.md?** No: it confirmed the jaw bone plus a few shared shapes and
a mouth inside. It added three things: the head must be its own MESH, not a second surface (Godot's GLES3 code gives
every surface of a mesh all its shapes); lids must slide over the ball on a shell (a straight-line shape cuts through
it); the mouth bag is best hung from the lips themselves (a separate ellipsoid left gaps where the head showed through).

## What was built (first pass, 2026-11-18, Claude)

- `tools/face_rig.py` runs as a post-process on a figure's glb (or inside a build, see its docstring) and writes
  `models/face/<figure>_face.glb`. `tests/face_view.gd` renders the expression sheet, a talk strip, close-ups and beauty
  shots. Nothing is in the game.
- Landmarks are found from geometry, with the face picture as a fallback: the mouth line is the deepest crease under the
  nose, or, where the lips are modelled flat (the boy), the darkest painted line; the corners where the crease fades
  (clamped to 0.68 to 1.05 of the eyes' half-spacing); eyes from the eyeball meshes (a sphere fit, plus the cornea's
  reach) or, for closed slits (the captain), the deepest crease between brow and cheek; the chin's underside from the
  profile of head and body together; ears as the widest points between nose base and brow.
- The jaw takes its share from head AND neck (the builds weight the chin's underside partly to the neck: that was what
  pulled the chin into the neck when the head tilts back); the whole chin is rigid, and the share fades down the throat
  over about 1.6 eye-spacings so the skin under the jaw stretches instead of folding. The same field is laid on the body
  mesh's under-jaw, so weights agree across the neck seam (checked: 0 mismatches).
- Lids: each lid's band is remapped in height (linear, so it cannot fold) and put back on a shell just off the eyeball
  and cornea (`lid_remap`). The captain's slits are cut open like the lips, get eyeballs pushed back until none shows
  through at rest, and `eyes_wide` opens them.
- Skeleton and inverse bind matrices are unchanged by the round trip (checked by comparing the glbs); the new bone
  `jaw` is inserted after `head`, so bone INDICES after it shift by one (names are unchanged).

## Second pass (2026-11-18, evening, Claude): what changed and why

More research for this pass: FACS (Ekman and Friesen's Facial Action Coding System) prototype combinations: joy =
AU6 cheek raiser + AU12 lip corner puller (+ AU25/26 for a laugh); surprise = AU1 + 2 + 5 + 26; anger = AU4 + 5 + 7 +
23/24, or with AU10 + 27 shouting; sadness = AU1 + 4 + 15. The viewer's expressions are now these recipes
(`EXPRESSIONS` in face_rig.py, written to `models/face/face_expressions.json`, read by tests/face_view.gd). Eye aiming:
a bone per eyeball under the head, turned by look-at code, is the usual game answer (Roblox's dynamic heads and the
usual Unity/Unreal character rigs aim eyes by joints; UV-scrolling irises suit flat painted eyes, and ours are balls).

- **Mouth**: the palette is now a 64 x 16 picture whose left half is a row of eight painted teeth (gaps, a warmer
  neck); teeth are curved arches with thickness (gum, front, biting edge, back); a shaped tongue with a groove rests
  behind the lower teeth; the inside is warm dark red (`bag`), darker deep in (`bag_deep`), never black; the inner lip
  is pink. Pouch three rows (was four), the deep rows thinned to seven points.
- **Where the mouth is cut**: the painted line between the lips now decides which modelled crease is the mouth (the
  brother's cut had taken the crease UNDER his lower lip; the captain's was too narrow); with no crease at the painted
  line the cut follows the paint. The cut's region reaches back as far as the corners (the captain's now spans 98% of
  his mouth, was 69%).
- **Joy**: `smile` is now AU12 + AU6 (corners up, back and out 0.24/0.13/0.11 u; the cheeks' apples up and forward; the
  nasolabial fold deepened; the lower lids pushed up by half a squint). New `eyes_happy` (AU6 + AU43): closed lids meeting
  in an upward arch, the skin under them bunched. The laugh is smile + eyes_happy + some mouth_wide + jaw 17 with the head
  back. The corners now follow the jaw 0.4 (was 0.5: Disney's "about half"), so a smile holds them up as the jaw drops.
- **Lids**: `lid_remap` turns lid points about the eye's long axis (angle remap, radius kept), so the lid keeps its
  thickness and slides round the ball; the old version rebuilt points from their distance to the centre with a square
  root and threw corner points inward (the boy's spiky lids). The lids' pivot is set back until the margin spans about
  +-35 degrees (the boy's eye is a flattened shape: its sphere fit sat 13 mm too far forward and his lids swung 95
  degrees). The guard is the real eyeball mesh (a BVH per side), not a sphere. Rim points below a lid's edge are carried
  with it (were squashed onto it).
- **Blink in-betweens**: `blink_arc_L`/`_R`, correctives a driver sets to 4c(1-c) (c = that eye's closure). Without
  them a half blink puts 52 of the boy's lid points inside his eyeball; with them none.
- **Eyes**: bones `eye_l` (the figure's own left, +x) and `eye_r`, children of `head`, at each ball's centre; the
  eyeball mesh is weighted wholly to them. Yaw + turns to the figure's left, pitch + up (tests/face_view.gd `aim_eyes`).
- **Lid UVs**: `fix_lid_uvs` gives hidden lid faces (the lid's inner rim, which comes into view as it closes) a skin
  texel when their UVs land on painted eye (29 faces on the boy, 6 on the brother).
- **Checks and self-test**: `rig_face` checks its inputs and what it measured and raises `FaceRigError` with what to
  change; `--selftest` prints landmarks, folds (and how many are over 1 mm2), lid-through-eyeball counts for every shape
  and every recipe, and exits 1 on any failure. `--bind a.glb,b.glb` binds hair pieces for a test copy.

## Integration (checklist for the figure builders)

1. Build the figure as now (armature with `head` and `neck`; body mesh `<figure>_body` with the head's faces on a
   material named `*_face`, UV mapped, Armature modifier; eyeball mesh `<figure>_eyes` with an Armature modifier, or none
   for slit eyes). No shape keys on the body, no `jaw`/`eye_l`/`eye_r` bones yet.
2. Just before export: `rig = face_rig.rig_face(arm, body, eyes, figure=..., tex_dir=<textures/face>, hair=[...])` in a
   try/except `face_rig.FaceRigError` that stops the build with the message.
3. Export with `export_morph=True, export_morph_normal=True, export_morph_tangent=False, export_try_sparse_sk=False`,
   then `face_rig.zero_still_normals(out_glb)`; write `face_rig.write_expressions(<models/face/face_expressions.json>)`
   if the recipes changed.
4. Bone indices: `jaw`, `eye_l`, `eye_r` come right after `head` (head 4, jaw 5, eye_l 6, eye_r 7 on all three now);
   every bone index after `head` shifts by three. Anything that stores bone INDICES (baked clips by index, attachment
   tables) must be re-baked or switched to names; names are unchanged.
5. Run `blender ... tools/face_rig.py -- models/<figure>.glb --selftest` after every rebuild; then
   `tests/face_view.gd -- --figure=<figure> --out=<dir>` and look at the sheet.
6. In Godot: the head is its own MeshInstance3D (`<figure>_head`) with the blend shapes; a face driver sets the
   recipe's weights plus the blink correctives (`drive_correctives` in tests/face_view.gd), turns `jaw` about the
   world's sideways axis (`bone_turn`) and the eye bones (`aim_eyes`). Keep normal maps off the head (Compatibility
   shades blend-shaped normal maps wrongly).

## Costs (second pass)

| | head (shapes) | triangles added to the head | mouth parts | added in all | shapes |
| --- | --- | --- | --- | --- | --- |
| brother | 1,167 v, 2,226 t | 306 (a cut along paint crosses many triangles) | 132 v, 188 t | 494 | 20 |
| boy | 1,262 v, 2,422 t | 194 | 132 v, 188 t | 382 | 20 |
| captain | 1,419 v, 2,754 t (+ eyeballs 216 v) | 392 (lips and both slits' rolls) | 132 v, 188 t | 580 | 20 |

The target was 150 to 300 added. Mouth parts are 188 (teeth 128, tongue 60); the overrun is the cut: where the lips'
meeting line is not an edge loop of the mesh, cutting it slices every triangle it crosses (the brother's 35 cut
vertices against the boy's 23). The fix belongs in the builds: a lips' meeting line that IS an edge loop (the base mesh
has one) brings the brother and captain to about 250.

Phones: a recipe drives 1 to 5 shapes (smile 2, laugh 4, shock 3, shout 4, sad 3 + 2 correctives, blink 1, a half
blink 1 + 2 correctives); each is one transform-feedback pass over the head's 1,170 to 1,420 vertices while its weight
is not zero, nothing while the face is still. Memory: 20 shapes x about 1,300 vertices x (position + normal), about
0.6 MB a figure. The L/R halves (4 shapes) cost memory only (about 0.12 MB) until a wink or a lopsided grin uses them:
worth keeping.

## Costs (first pass, glTF, as exported)

| | head mesh (has the shapes) | mouth parts | shapes | file |
| --- | --- | --- | --- | --- |
| brother | 1,510 vertices, 2,318 triangles (was 2,028 face faces: +290 for the cut lips, roll and pouch) | 104 v, 112 t | 17 | 3.46 MB (2.76 in) |
| boy | 1,634 v, 2,577 t | 104 v, 112 t | 17 | 1.86 MB (1.23 in) |
| captain | 1,784 v, 2,762 t, plus eyeballs 216 v, 384 t | 104 v, 112 t | 17 | 3.48 MB (2.79 in) |

Per frame in Compatibility, each shape with a weight above zero is one transform-feedback pass over the head's 1,500
to 1,800 vertices only; the body (2,200 to 2,600 vertices) runs no shape passes. Memory: about 17 x head vertices x
(position + normal) per figure, a few hundred KB. Morph tangents are not exported (no normal maps on faces).
