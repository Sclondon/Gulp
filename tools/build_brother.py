"""The older brother, built from his modelling sheets (second build, 2026-11-18).

    blender --background --factory-startup --python tools/build_brother.py -- [--out <folder>] [--rounds N]

Writes models/brother.glb, tools/blend/brother.blend, textures/brother/ (his skin, face and shorts pictures, each with a
layout picture and a JSON of its islands), his tattoos (textures/tattoos/brother_*.png, the table
textures/brother/brother_tattoos.json and the overlay textures/brother/brother_tattoo_overlay.png) and, in --out, the
overlays of every fitting round and the silhouette differences (red: only the model; cyan: only the sheet) of the
head's five views, the body's three and the hand's three, with their worst gaps printed.

Who he is (the user): "the older brother is a budding handsom curly dark haired sailor about 19"; "The older brother
should be the tallest of the 3, a little taller and rugby built, with a less pointy more rugged square face"; "Older
brother needs body hair as well"; "He shouldn't be too ripped- needs a stocky build"; of the first build: "The heads
and hands need a lot of work on all three- make sure you are matching pose silhouettes aggressively".

Three sheets:
- THE BODY: tools/art_src/concept_brother_tpose6.jpg (front, side, back, arms about 45 degrees out, off-white knit
  shorts; stocky: barrel chest, soft belly, very hairy). Everything from the chin down is measured on it, its soles to
  its chin 1.673 m.
- THE HEAD: tools/art_src/concept_brother_head2.jpg, its bottom row (bald, clean-shaven: front, three-quarter, his
  right side, three-quarter back, back), scaled so crown to chin is 0.257 m (1/7.5 of 1.93 m), set on the body's chin.
  Third build (tools/FIGURE_HEADS.md): the head and ears are Blender Studio's Human Base Meshes `Head - Generic
  Topology` (CC0, appended from the bundle outside the repo) at HEAD_MIX, placed by landmarks, its face's heights warped
  to the bald side view's, ears and nose fitted, pulled to all five bald views' outlines (base_head), split once but
  the ears and refitted (refine_base_head); checked by silhouettes and landmarks (head_silhouettes, head_landmarks).
  Its open neck is bridged to the torso's top ring.
- THE HANDS: tools/art_src/concept_brother_hands.jpg: the hand is sized and shaped to its back, palm and thumb-side
  views. Third build: `Hand - Stylized` un-subdivided twice, each digit turned and sized to its drawn digit, pulled to
  the back view's outline (base_hand_fit), posed relaxed (pose_hand), bridged to the forearm (place_base_hand) and
  painted from the back and palm views through a layout made from those views (paint_hands).

He is the BARE person (the user: hair is added on top later): no head hair, no moustache. His body hair (chest, belly,
forearms, thighs, shins) is the sheet's own paint on the skin. His tattoos are lifted from the body sheet into pictures
of their own, placed by a table and drawn as a see-through layer (`brother_ink`) over a clean skin; the wrist's rope is
one of them. The knit shorts are their own garment (`brother_shorts`) over finished skin (`brother_body_under`, hidden).

The method is the captain's (tools/build_captain.py, copied and changed here, never imported): the body lofted as
rings measured row by row and fitted to the outlines; forms moved into the mesh by rule; his own skeleton with the
game's bone names; planned UVs; the sheets projected into that layout.

Model space: Blender's, Z up, he faces -Y (the game's +Z after export), +X is his left. Metres. He stands in the
sheet's own pose (arms hanging about 40 degrees out), which is his rest pose.
"""
import bpy
import builtins
import time
_T0 = time.time()


def print(*a, **k):
    k.setdefault("flush", True)
    builtins.print("[%5.1fs]" % (time.time() - _T0), *a, **k)

import bmesh
import json
import math
import os
import sys

import numpy as np
from mathutils import Matrix, Vector, kdtree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ART = os.path.join(HERE, "art_src")
TATTOO_DIR = os.path.join(ROOT, "textures", "tattoos")
# (TEX, GLB and BLEND are the figure's, set below the figure table)
WHO = "BROTHER"

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


OUT = arg("--out", "")
FIT_ROUNDS = int(arg("--rounds", "6"))

# ------------------------------------------------------------------------------------------------------------------
# Figures (2026-11-18, the user: "The older brothers is a bit too bulky a big gutted, though I like how it works so
# make it a different grown man model"; then of tpose7: "Not stocky enough now and he lost thair, though make a body on
# that one"). One build, a small table per figure, chosen by `-- --figure <name>`:
# - brother (the default): the older brother. Built on the tpose6 fit until his own sheet (concept_brother_tpose8.jpg)
#   arrives; then his entry gets that sheet, its warp and its own rows;
# - man_big: a grown townsman, the bulky big-bellied body fitted to concept_brother_tpose6.jpg;
# - man_trim: a grown townsman, tall and broad-shouldered with a nearly flat stomach, concept_brother_tpose7.jpg.
# The townsmen keep the brother's head, hands, feet and shorts for now (faces of their own later) and carry no
# tattoos. Every row and column in this file is in tpose6's frame (the sheet it was first written for). A figure on
# another sheet gives that sheet's chin and sole rows and its views' middle columns ("warp"): its picture is resampled
# into tpose6's frame, one uniform scale (chin to sole onto tpose6's chin to sole, so he keeps 1.93 m and the head's
# share measured before) and each view's middle onto tpose6's; widths, depths and the torso/leg split come from his
# own sheet. Measured (scratchpad landmarks.py): tpose7's chin row 332 (the end of the narrow run under the jaw, as
# tpose6's 308), its soles row 1500 (the side view's last row), its middles 579, 1393 (the side view's neck and
# ankle), 2210.
# Each figure: sheet, warp (None, or chin, sole, middles and the guide lines' ground columns), outputs (glb, textures,
# blend), tattoos (None keeps the TATTOOS table; () none; boxes in the sheet's own pixels), the side view's hand box
# (tpose6's frame; None keeps SIDE_HAND), the share of the bulky belly's forms (BODY_FORMS rows 610 to 690) laid on,
# and the nose's red kept (1 the sheet's; the brother's is pulled back to a mild flush: the user, "a bit too red button
# nosed").
FIGURES = {
    # (eighth round: his own settled sheets. The BODY is concept_brother_tpose8.jpg, warped as man_trim's: measured
    # (scratchpad brother8/rows.py, chin.py) its chin row 330 (10 px above the end of the jaw's underside in the side
    # view, as tpose6's 308 is), its soles row 1501 (the side view's last row), its middles 578 (front), 1402 (side:
    # 28 px of tpose6 in front of the ankle's middle, as tpose6's 1440 is) and 2210 (back): times 0.982, so its own
    # widths, depths and the trunk/leg split are kept almost pixel for pixel. Its waistband, crotch, hem, knee and
    # ankle then fall within 7 px (1 cm) of tpose6's rows, so the row tables written for tpose6 hold. The HEAD is the
    # bottom row of concept_brother_head3_bare.jpg (shaved, clean), warped into head2's bottom-row frame (crown row
    # 862, chin row 1332, its views' middles at the same share of each skull as head2's); its face's own landmarks are
    # the "marks" below, read off that warped picture.)
    "brother": {"sheet": "concept_brother_tpose8.jpg",
                "warp": {"chin": 330.0, "sole": 1501.0, "mid": {"front": 578.0, "side": 1402.0, "back": 2210.0},
                         "ground_cols": (1010, 1240)},
                "head": {"sheet": "concept_brother_head3_bare.jpg", "crown": 862.0, "chin": 1332.0, "rows": (800, 1536),
                         "spans": {"front": (0, 640), "q": (640, 1170), "side": (1170, 1720), "qb": (1720, 2180),
                                   "back": (2180, 2752)},
                         "mid": {"front": 359.0, "q": 813.0, "side": 1285.0, "qb": 1852.0, "back": 2419.0},
                         # (read off the warped picture, scratchpad brother8/hw_front.png and hw_side.png: head2-frame
                         # rows; front columns out from the middle; side columns)
                         "marks": {
                             "HEAD_PROFILE_ROWS": {"brow": (985, 1025), "tip": (1085, 1130), "chin": (1195, 1240),
                                                   "back": (880, 1060), "lips": (1145, 1172)},
                             "HEAD_WIDTH_ROWS": (1078, 1196, 1235),
                             "EAR_ROWS": (1020, 1137), "EAR_COLS": (1415, 1342), "EAR_LOBE": (1390.0, 1137.0),
                             "EAR_HIDES": (1025, 1150), "FACE_PLANE": (1035, 1135),
                             "NOSE": ((1042, 28.0), (1058, 30.0), (1074, 33.0), (1090, 38.0), (1100, 46.0), (1108, 62.0),
                                      (1116, 76.0), (1124, 76.0), (1131, 66.0), (1137, 46.0), (1141, 30.0)),
                             "NOSE_WINGS": ((1105, 0.0), (1115, 0.12), (1124, 0.2), (1133, 0.15)),
                             "JAW_ANGLE": (1408.0, 1158.0), "CHIN_BOTTOM": (1560.0, 1250.0), "NECK_ROW": 1270,
                             "SMILE": (1168.0, 6.0, 62.0, -0.0025),
                             # (tenth round: fuller cheeks, no fold from the nose's wings, temples full, not hollow:
                             # all three read as age, the critic)
                             "BASE_FACE_FORMS": ((1100, 84, 22, 28, 0.011), (1140, 52, 9, 7, 0.0),
                                                 (985, 125, 18, 14, 0.001), (1010, 62, 6, 22, 0.0012),
                                                 (1158, 0, 5, 24, 0.0016), (1180, 0, 4, 20, 0.0022),
                                                 (1163, 60, 4, 4, -0.0016), (1132, 15, 3, 6, -0.0025)),
                             "JAW_FIRM": (1162.0, 0.0012, (1162.0, 1255.0), (0.03, 0.095)),
                             "EYE_INNER": (35.0, 1047.0), "EYE_OUTER": (96.0, 1053.0), "EYE_TOP": (58.0, 1035.0),
                             "EYE_LOW": (60.0, 1060.0), "EYE_IRIS": (64.0, 1048.0, 13.0), "EYE_ZONE": (40.0, 24.0)}},
                "glb": ("models", "brother.glb"), "tex": ("textures", "brother"), "blend": ("blend", "brother.blend"),
                "tattoos": (("anchor", "front", (786, 864), (430, 594)),
                            ("forearm_l", "front", (860, 932), (652, 754)),
                            ("forearm_r", "front", (238, 292), (652, 748))),
                # (tpose8's arm, read off the warped sheet (scratchpad brother8/sw_arm.png): the elbow higher and the
                # wrist 33 px lower than tpose6's, a forearm of 23 cm, not 16)
                "consts": {"SHOULDER_ROW": 400, "ELBOW_ROW": 630, "WRIST_ROW": 790, "ARM_SAMPLE": (560, 786),
                           "HAND_LEN": 0.236, "TATTOO_CLOSE": 2,   # (tpose8 draws a 24 to 25 cm hand (its side view, wrist crease to fingertip), the hands sheet 21: ninth round, toward the body sheet)
                           # (the side view: the arm hangs further back, its deltoid's middle 5.5 cm and its wrist 2 cm
                           # behind the side view's middle; the back behind it read 10 px further back than tpose6's)
                           "ARM_Y": (0.07, 0.02), "TRAPS": 0.012, "TOP_DROP": {368: 0.02, 345: 0.04, 318: 0.012}, "HEAD_BACK": 0.022, "EAR_SHAPE": (0.93, -18.0, 0.0035, 0.0045), "JAW_WIDEN": 0.007, "CHIN_BROAD": (0.18, 0.003),
                           # (his neck: tpose8 draws it 14 cm across under the jaw: the torso's top ring and the
                           # jaw's neck column widened to it, from 0.088 and 0.092 m half widths)
                           "TORSO_UNDER_ARMS": {538: 0.272, 490: 0.284, 442: 0.268, 398: 0.226, 368: 0.2, 345: 0.162,
                                                318: 0.098},
                           "NECK_HALF": 0.097,
                           # (tenth round: his face younger and broader, as tpose8 draws it; see youth_head)
                           "HEAD_WIDEN": ((1.62, 1.0), (1.665, 1.1), (1.69, 1.14), (1.73, 1.19), (1.765, 1.17), (1.79, 1.13),
                                          (1.83, 1.09), (1.89, 1.07), (1.95, 1.05)),
                           "CROWN_ROUND": (3, 1.86), "NOSE_SHORT": 0.15, "PEC_PROUD": 0.02,
                           # (tenth round: a broader palm; a bigger big toe, a higher arch, the feet lighter; the shorts'
                           # band halved and their hems nearer the thighs)
                           "HAND_WIDE": 1.14, "HAND_TAUBIN": 5, "HAND_DESPIKE": 0.006, "TOE_BIG": 0.8, "ARCH": 0.012,
                           "BOXER_BAND_TALL": 15.0,
                           "SHORTS_STAND": {"band_lip": 0.0015, "band": 0.004, "cloth": 0.01, "leg_in": 0.003,
                                            "leg_out": 0.005, "hug": 0.0025}, "DOME_FROM": 1.83, "DOME_DROP": 0.004, "NECK_EASE": 6,
                           "SIDE_BACK": {368: 1342, 398: 1332, 442: 1328, 490: 1327, 538: 1329, 580: 1331, 610: 1334,
                                         640: 1337, 665: 1340}},
                "side_hand": ((1385, 775), (1530, 962)), "belly": 0.5, "nose_red": 0.35,
                # (the side view's hand and wrist as the skin's paint must skip them: its fingertips reach row 995 on
                # the warped sheet, scratchpad brother9/sidehand.png)
                "side_hand_skin": ((1378, 760), (1535, 1008)),
                # (his eyes, the user: "a bit down turned eyes and more prominent world weary bags": the outer corners
                # 6 px (about 4 mm) lower, a pouch of 1.8 mm under each; the townsmen keep the plain eyes)
                # (tenth round: lid_drop 6 -> 0: on head3's top row the upper lid just meets the iris's top (the
                # sheet's EYE_TOP is the iris's top, row 1035): the opening 25 px high against 19, a third taller;
                # the bags softer, a form without the crease under them)
                "eye_down": 4.0, "fresh": {"EYE_R": 0.016, "EYE_RX": 0.0285, "LID_TUCK": (0.0018, 0.0025), "EYE_ZONE": (31.0, 19.0), "LID_EVEN": 10, "LID_RINGS": 3, "EYE_INNER": (33.0, 1047.0), "EYE_OUTER": (99.0, 1053.0), "EYE_TOP": (60.0, 1033.0), "EYE_LOW": (63.0, 1063.0), "EYE_IRIS": (65.0, 1048.0, 16.0), "CHIN_BROAD": (0.18, 0.0), "JAW_WIDEN": 0.006, "SMILE": (1168.0, 9.0, 70.0, -0.0009), "MOUTH_WIDEN": 70.0 / 62.0, "JAW_LINE": 0.004, "EAR_SHAPE": (1.0, -12.0, 0.0035, 0.0045), "FACE_ROSE": (0.7, 0.75), "LASH": 1.6, "BROW_ROW": (16.0, 7.5, 9.0), "EYE_SPLIT": False}, "lid_drop": 0.0, "bags": 0.0025, "bag_crease": 0.0, "iris": "hazel",
                # (tenth round: his face and body painted by rule on clean young skin (rule_face, young_skin); his tone
                # warm peach, red up and a little more saturated than the ninth round's 0.9, 0.755, 0.635)
                "rule_paint": True, "skin_tone": (0.92, 0.745, 0.6), "iris_k": 1.15,
                # (eleventh round: the head built afresh, see HEAD_MIX_FRESH; `-- --head-route old` for the tenth round's)
                "head_route": "r7",
                # (eleventh round: the chest hair a fan by rule, limb hair as fine strokes, plain hands in the
                # forearm's tone, the shorts cream)
                "hair_fan": 1.0, "plain_hands": True, "cream_k": 0.85, "cream": (0.93, 0.885, 0.775)},
    "man_big": {"sheet": "concept_brother_tpose6.jpg", "warp": None,
                "glb": ("models", "npc", "man_big.glb"), "tex": ("textures", "npc", "man_big"),
                "blend": ("blend", "npc", "man_big.blend"),
                "tattoos": (), "side_hand": None, "belly": 1.0, "nose_red": 1.0,
                # (tenth round: their own tone, the SKIN_TONE they had before the ninth round lightened the brother)
                "skin_tone": (0.665, 0.5, 0.39)},
    "man_trim": {"sheet": "concept_brother_tpose7.jpg",
                 "warp": {"chin": 332.0, "sole": 1500.0, "mid": {"front": 579.0, "side": 1393.0, "back": 2210.0},
                          "ground_cols": (1040, 1260)},
                 "glb": ("models", "npc", "man_trim.glb"), "tex": ("textures", "npc", "man_trim"),
                 "blend": ("blend", "npc", "man_trim.blend"),
                 "tattoos": (), "side_hand": ((1400, 790), (1540, 1000)), "belly": 0.0, "nose_red": 1.0,
                 "skin_tone": (0.665, 0.5, 0.39),
                 # (eighth round: its silhouette gap of 12.5 cm was its hands: tpose7 hangs the forearm as long as tpose8
                 # does, so the brother's tpose8 arm rows and hand length)
                 "consts": {"SHOULDER_ROW": 400, "ELBOW_ROW": 630, "WRIST_ROW": 790, "ARM_SAMPLE": (560, 786),
                            "HAND_LEN": 0.224}},
}
FIGURE_NAME = arg("--figure", "brother")
FIGURE = FIGURES[FIGURE_NAME]

# ------------------------------------------------------------------------------------------------------------------
# The sheets
# ------------------------------------------------------------------------------------------------------------------

TEX = os.path.join(ROOT, *FIGURE["tex"])
GLB = os.path.join(ROOT, *FIGURE["glb"])
BLEND = os.path.join(HERE, *FIGURE["blend"])
BODY_SHEET = os.path.join(ART, FIGURE["sheet"])
HEAD_SHEET = os.path.join(ART, "concept_brother_head2.jpg")
HANDS_SHEET = os.path.join(ART, "concept_brother_hands.jpg")

# The body sheet (pixels of the 2752 by 1536 picture): the soles' row, the chin's row, each view's middle column (the
# front's and back's from the torso and the legs; the side's between the ankle and the torso's middle) and the
# columns each spans. Its guide lines are found in the columns between the front and the side figures.
SOLE = 1458.0
CHIN = 308.0
# Sixth round: the head's size from the BODY sheet, not a 1/7.5 rule. On concept_brother_tpose6.jpg the curls' top is
# row 74 and the chin row 308 (234 px); on concept_brother_head2.jpg the curls stand about 11% above the shaved crown
# (the eye line set level between its two rows), so the shaved crown is about row 98: crown to chin 210 px of 1360 px
# crown to sole, 1/6.48 of his height (the old build had 1/7.5, a head 14% too small). He stays 1.93 m tall: the chin
# comes down to 1.632 m and the body below it is 2.5% smaller than before (S below).
SHEET_CROWN = 98.0
CROWN_Z = 1.93
CHIN_Z = CROWN_Z * (1458.0 - 308.0) / (1458.0 - SHEET_CROWN)
K_BODY = CHIN_Z / 1.673      # the body against the old build
K_HEAD = (CROWN_Z - CHIN_Z) / 0.257   # the head against the old build
S = CHIN_Z / (SOLE - CHIN)    # metres a pixel
MID = {"front": 573.0, "side": 1440.0, "back": 2238.0}
SPAN = {"front": (40, 1110), "side": (1290, 1700), "back": (1720, 2752)}
GROUND_COLS = (1090, 1300)
# The shorts: the rows they cover (waistband's top to hem), the crotch, how far they stand off him.
BOXERS = (698, 937)
CROTCH = 880
BOXER_EASE = 10               # pixels (1.5 cm): the body under them is this much inside their outline
# The side view's back from the shoulder to the waist is his right arm (it hangs over his side): the back's column
# there, read off the sheet by eye (the lats and the upper back behind the arm), by row.
SIDE_BACK = {368: 1352, 398: 1342, 442: 1338, 490: 1337, 538: 1339, 580: 1341, 610: 1344, 640: 1347, 665: 1350}

# The head sheet (concept_brother_head2.jpg, 2752 by 1536): two rows of five views (front, three-quarter, his right
# side, three-quarter back, back); the BOTTOM row, shaved bald and clean-shaven, is his base head. Scaled alike every
# way (HEAD_SX metres a pixel) so its crown to chin (the sheet's own guide lines, rows 846 and 1244) is 0.257 m, its
# chin's row on CHIN_Z. Each view: (degrees round from his front toward his right side, its middle column (the
# angled views' are found by fitting, see align_head_views), the columns it spans). The side view's middle column
# puts his throat under the chin where the body sheet's is.
HEAD_SX = (CROWN_Z - CHIN_Z) / (1244.0 - 846.0)
HEAD_CHIN = 1244.0
HEAD_CROWN = 846.0
HEAD_VIEWS = {"front": [0.0, 459.0, (150, 720)], "q": [31.0, 906.0, (700, 1185)], "side": [90.0, 1343.0, (1185, 1700)],
              "qb": [141.0, 1845.0, (1660, 2140)], "back": [180.0, 2380.0, (2080, 2720)]}
HEAD_ROWS_SEEN = (840, 1240)  # the rows the head's views are compared over (below, the five views' shoulders meet)


def head_z(row):
    return CHIN_Z + (HEAD_CHIN - np.asarray(row, dtype=float)) * HEAD_SX


def head_row(z):
    return HEAD_CHIN - (np.asarray(z, dtype=float) - CHIN_Z) / HEAD_SX


def body_z(row):
    return (SOLE - np.asarray(row, dtype=float)) * S


def body_row(z):
    return SOLE - np.asarray(z) / S


def load_picture(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    pix = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1, :, :3].copy()
    bpy.data.images.remove(img)
    return pix


def unline(pix, cols):
    """The sheet's guide lines painted out (rows where the ground between the figures is unlike the ground)."""
    ground = np.median(pix[:, cols[0]:cols[1]].reshape(-1, 3), axis=0)
    rows = set(np.where(np.abs(pix[:, cols[0]:cols[1]] - ground).max(-1).mean(axis=1) > 0.04)[0].tolist())
    out = pix.copy()
    for r in sorted(rows):
        a = r - 1
        while a in rows:
            a -= 1
        b = r + 1
        while b in rows:
            b += 1
        b = min(b, pix.shape[0] - 1)
        t = (r - a) / (b - a)
        out[r] = pix[a] * (1 - t) + pix[b] * t
    return out


def flood_mask(pix, tol=0.03):
    """The figure: everything a flood from the picture's edges cannot reach through small steps of colour."""
    h, w = pix.shape[:2]
    hok = np.abs(pix[:, 1:] - pix[:, :-1]).max(-1) < tol
    vok = np.abs(pix[1:] - pix[:-1]).max(-1) < tol
    brk = np.ones((h, w), bool)
    brk[:, 1:] = ~hok
    hid = np.cumsum(brk.ravel()) - 1
    brk = np.ones((w, h), bool)
    brk[:, 1:] = ~vok.T
    vid = (np.cumsum(brk.ravel()) - 1).reshape(w, h).T.ravel()
    reach = np.zeros((h, w), bool)
    reach[0] = reach[-1] = True
    reach[:, 0] = reach[:, -1] = True
    reach = reach.ravel()
    for _ in range(400):
        before = reach.sum()
        reach = (np.bincount(hid, weights=reach, minlength=hid[-1] + 1) > 0)[hid]
        reach = (np.bincount(vid, weights=reach, minlength=vid.max() + 1) > 0)[vid]
        if reach.sum() == before:
            break
    return ~reach.reshape(h, w)


def colour_mask(pix, cols, thr=0.055):
    """The figure where the flood leaks (a soft-edged sheet): every pixel unlike the ground by more than thr, with
    the holes inside it filled."""
    ground = np.median(pix[:, cols[0]:cols[1]].reshape(-1, 3), axis=0)
    fig = np.abs(pix - ground).max(-1) > thr
    for _ in range(2):
        fig = fig | np.roll(fig, 1, 0) | np.roll(fig, -1, 0) | np.roll(fig, 1, 1) | np.roll(fig, -1, 1)
    for _ in range(2):
        fig = fig & np.roll(fig, 1, 0) & np.roll(fig, -1, 0) & np.roll(fig, 1, 1) & np.roll(fig, -1, 1)
    b = np.repeat(fig[..., None].astype(np.float32), 3, 2)
    return flood_mask(b, 0.5)


def runs_of(row, c0, c1, least=3):
    out = []
    c = c0
    while c < c1:
        if row[c]:
            s = c
            while c < c1 and row[c]:
                c += 1
            if c - s >= least:
                out.append((s, c - 1))
        c += 1
    return out


def run_near(mask, row, col, c0, c1):
    """The run of figure in a row that holds the column, or the nearest one."""
    rs = runs_of(mask[int(round(row))], c0, c1)
    if not rs:
        return None
    for a, b in rs:
        if a <= col <= b:
            return (a, b)
    return min(rs, key=lambda r: min(abs(r[0] - col), abs(r[1] - col)))


def guide_rows(pix):
    """The guide lines' rows of a sheet whose figures fill its middle: rows where a fifth of the picture is the lines'
    neutral grey."""
    mx, mn = pix.max(-1), pix.min(-1)
    lum = pix.mean(-1)
    neutral = (mx - mn < 0.045) & (lum < 0.84) & (lum > 0.5)
    rows = set(np.where(neutral[:, 160:2620].mean(1) > 0.2)[0].tolist())
    return rows | {r + 1 for r in rows} | {r - 1 for r in rows}


def unline_rows(pix, rows):
    out = pix.copy()
    for r in sorted(rows):
        a = r - 1
        while a in rows:
            a -= 1
        b = r + 1
        while b in rows:
            b += 1
        b = min(b, pix.shape[0] - 1)
        t = (r - a) / (b - a)
        out[r] = pix[a] * (1 - t) + pix[b] * t
    return out


def figure_mask(pix, thr=0.06):
    """The figures of a sheet on its flat pale ground: unlike the ground (its left margin) by more than thr, holes
    filled."""
    ground = np.median(pix[:, 20:150].reshape(-1, 3), axis=0)
    fig = np.abs(pix - ground).max(-1) > thr
    for _ in range(2):
        fig = fig | np.roll(fig, 1, 0) | np.roll(fig, -1, 0) | np.roll(fig, 1, 1) | np.roll(fig, -1, 1)
    for _ in range(2):
        fig = fig & np.roll(fig, 1, 0) & np.roll(fig, -1, 0) & np.roll(fig, 1, 1) & np.roll(fig, -1, 1)
    return flood_mask(np.repeat(fig[..., None].astype(np.float32), 3, 2), 0.5)


def warp_k(w):
    return (SOLE - CHIN) / (w["sole"] - w["chin"])


def warp_point(w, view, col, row):
    """A point of the figure's own sheet in tpose6's frame (see FIGURES)."""
    k = warp_k(w)
    return MID[view] + (col - w["mid"][view]) * k, CHIN + (row - w["chin"]) * k


def warp_sheet(pix, w, fill=None):
    """The figure's sheet resampled into tpose6's frame, view by view (bilinear); the ground (or `fill`) elsewhere."""
    h, wd, _ = pix.shape
    bg = np.median(pix[5:30, 5:200].reshape(-1, 3), 0) if fill is None else np.full(3, fill, np.float32)
    out = np.broadcast_to(bg, pix.shape).copy()
    k = warp_k(w)
    rows = np.arange(h, dtype=np.float32)
    r_src = w["chin"] + (rows - CHIN) / k
    for view, (c0, c1) in SPAN.items():
        cols = np.arange(c0, min(c1, wd), dtype=np.float32)
        c_src = w["mid"][view] + (cols - MID[view]) / k
        R, C = np.meshgrid(r_src, c_src, indexing="ij")
        ok = (R >= 0) & (R < h - 1) & (C >= 0) & (C < wd - 1)
        R0, C0 = np.clip(np.floor(R).astype(int), 0, h - 2), np.clip(np.floor(C).astype(int), 0, wd - 2)
        fr, fc = (R - R0)[..., None], (C - C0)[..., None]
        v = (pix[R0, C0] * (1 - fr) * (1 - fc) + pix[R0 + 1, C0] * fr * (1 - fc) + pix[R0, C0 + 1] * (1 - fr) * fc
             + pix[R0 + 1, C0 + 1] * fr * fc)
        out[:, c0:c0 + len(cols)] = np.where(ok[..., None], v, bg)
    if fill is None:
        print("%s body sheet %s warped into tpose6's frame: times %.4f" % (WHO, FIGURE["sheet"], k))
    return out


def warp_head_sheet(pix, hw):
    """A figure's own bald head row resampled into head2's bottom-row frame (see FIGURES "head"): one uniform scale
    per sheet (its crown to chin onto HEAD_CROWN to HEAD_CHIN), each view's middle onto HEAD_VIEWS' middle; source
    rows outside the bald row (`rows`) are the ground."""
    h, wd, _ = pix.shape
    bg = np.median(pix[5:30, 5:200].reshape(-1, 3), 0)
    out = np.broadcast_to(bg, pix.shape).copy()
    k = (HEAD_CHIN - HEAD_CROWN) / (hw["chin"] - hw["crown"])
    rows = np.arange(h, dtype=np.float32)
    r_src = hw["crown"] + (rows - HEAD_CROWN) / k
    done = np.zeros(wd, bool)
    for view in ("front", "q", "side", "qb", "back"):
        _, mid, (c0, c1) = HEAD_VIEWS[view]
        c0 = max(c0, int(np.where(~done)[0].min())) if not done.all() else c1
        cols = np.arange(c0, min(c1, wd), dtype=np.float32)
        if not len(cols):
            continue
        c_src = hw["mid"][view] + (cols - mid) / k
        R, C = np.meshgrid(r_src, c_src, indexing="ij")
        s0, s1 = hw["spans"][view]
        ok = (R >= hw["rows"][0]) & (R < min(hw["rows"][1], h - 1)) & (C >= max(0, s0)) & (C < min(wd - 1, s1))
        R0, C0 = np.clip(np.floor(R).astype(int), 0, h - 2), np.clip(np.floor(C).astype(int), 0, wd - 2)
        fr, fc = (R - R0)[..., None], (C - C0)[..., None]
        v = (pix[R0, C0] * (1 - fr) * (1 - fc) + pix[R0 + 1, C0] * fr * (1 - fc) + pix[R0, C0 + 1] * (1 - fr) * fc
             + pix[R0 + 1, C0 + 1] * fr * fc)
        out[:, c0:c0 + len(cols)] = np.where(ok[..., None], v, bg)
        done[c0:c0 + len(cols)] = True
    print("%s head sheet %s warped into head2's frame: times %.4f" % (WHO, hw["sheet"], k))
    return out


class Sheets:
    def __init__(self):
        # (the guide lines painted out of the pictures that are painted from as well: they crossed his eyes and neck)
        if FIGURE["warp"]:
            # (the figure found on the sheet as drawn, then both warped: the resampling softens the figure's outline
            # into small colour steps that the flood leaks through)
            raw = unline(load_picture(BODY_SHEET), FIGURE["warp"]["ground_cols"])
            m = figure_mask(raw).astype(np.float32)   # (a flood leaked into the side figure along a painted-out guide row)
            self.body_pix = warp_sheet(raw, FIGURE["warp"])
            self.body_mask = warp_sheet(np.repeat(m[..., None], 3, 2), FIGURE["warp"], fill=0.0)[..., 0] > 0.5
        else:
            self.body_pix = unline(load_picture(BODY_SHEET), GROUND_COLS)
            self.body_mask = flood_mask(self.body_pix)
        if OUT and FIGURE["warp"]:
            save_rgb(os.path.join(OUT, "sheet_warped.png"), self.body_pix * (0.5 + 0.5 * self.body_mask[..., None]))
            save_rgb(os.path.join(OUT, "sheet_warped_plain.png"), self.body_pix)
        hw = FIGURE.get("head")
        raw = load_picture(os.path.join(ART, hw["sheet"]) if hw else HEAD_SHEET)
        self.head_pix = unline_rows(raw, guide_rows(raw))
        if hw:
            self.head_pix = warp_head_sheet(self.head_pix, hw)
        self.head_mask = figure_mask(self.head_pix)
        if OUT and hw:
            save_rgb(os.path.join(OUT, "head_warped.png"), self.head_pix * (0.5 + 0.5 * self.head_mask[..., None]))
            save_rgb(os.path.join(OUT, "head_warped_plain.png"), self.head_pix)
            if "--sheets" in ARGS:
                raise SystemExit("BROTHER --sheets: the warped head sheet written")
        raw = load_picture(HANDS_SHEET)
        self.hands_pix = unline_rows(raw, guide_rows(raw))
        self.hands_mask = figure_mask(self.hands_pix)
        self.body_target = self._body_target()

    def _body_target(self):
        """The base body's outline as the fitting's target: the shorts drawn in by BOXER_EASE, and under them, from
        the crotch down to their hem, his legs as they are just below it."""
        t = self.body_mask.copy()
        for view in ("front", "back"):
            c0, c1 = SPAN[view]
            mid = MID[view]
            for r in range(BOXERS[0] + 6, CROTCH + 1):
                run = run_near(t, r, mid, c0, c1)
                if run and run[0] < mid < run[1]:
                    a, b = run
                    t[r, a:a + BOXER_EASE] = False
                    t[r, b - BOXER_EASE + 1:b + 1] = False
            legs = t[BOXERS[1] + 6, c0:c1].copy()
            for r in range(CROTCH + 1, BOXERS[1] + 6):
                t[r, c0:c1] = legs
        c0, c1 = SPAN["side"]
        for r in range(BOXERS[0] + 10, BOXERS[1] + 6):
            run = run_near(t, r, MID["side"], c0, c1)
            if run:
                a, b = run
                t[r, a:a + BOXER_EASE] = False
                # (the front of the shorts stands further off him over the fly: drawn in more there)
                e = BOXER_EASE + (8 if r > 760 else 0)
                t[r, b - e + 1:b + 1] = False
        return t


# ------------------------------------------------------------------------------------------------------------------
# Views: where a point of him falls in a sheet's picture (continuous pixel coordinates: column, row) and how deep
# ------------------------------------------------------------------------------------------------------------------

def head_angle(view):
    return math.radians(HEAD_VIEWS[view[5:]][0])


def project(view, P):
    """(N,3) model points -> (N,2) picture coordinates and (N,) depth (smaller is nearer the painter). A head view
    looks at him from `angle` degrees round from his front toward his right side: across the picture runs
    x cos(angle) - y sin(angle), the depth is x sin(angle) + y cos(angle)."""
    P = np.asarray(P, dtype=float)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    if view.startswith("head_"):
        a = head_angle(view)
        u = x * math.cos(a) - y * math.sin(a)
        mid = HEAD_VIEWS[view[5:]][1]
        return np.stack([mid + u / HEAD_SX + 0.5, head_row(z) + 0.5], 1), x * math.sin(a) + y * math.cos(a)
    row = body_row(z) + 0.5
    if view == "front":
        return np.stack([MID["front"] + x / S + 0.5, row], 1), y
    if view == "back":
        return np.stack([MID["back"] - x / S + 0.5, row], 1), -y
    return np.stack([MID["side"] - y / S + 0.5, row], 1), x                  # his right side


def screen_dir(view, N):
    """Directions in the picture (column, row) of model directions, and how much they face the painter."""
    N = np.asarray(N, dtype=float)
    if view.startswith("head_"):
        a = head_angle(view)
        return np.stack([N[:, 0] * math.cos(a) - N[:, 1] * math.sin(a), -N[:, 2]], 1), -(N[:, 0] * math.sin(a) + N[:, 1] * math.cos(a))
    if view == "front":
        return np.stack([N[:, 0], -N[:, 2]], 1), -N[:, 1]
    if view == "back":
        return np.stack([-N[:, 0], -N[:, 2]], 1), N[:, 1]
    return np.stack([-N[:, 1], -N[:, 2]], 1), -N[:, 0]


def world_dir(view, d2):
    """A direction in the picture as a model direction (in the picture's plane)."""
    z = np.zeros(len(d2))
    if view.startswith("head_"):
        a = head_angle(view)
        return np.stack([d2[:, 0] * math.cos(a), -d2[:, 0] * math.sin(a), -d2[:, 1]], 1)
    if view == "front":
        return np.stack([d2[:, 0], z, -d2[:, 1]], 1)
    if view == "back":
        return np.stack([-d2[:, 0], z, -d2[:, 1]], 1)
    return np.stack([z, -d2[:, 0], -d2[:, 1]], 1)


def view_scale(view):
    return HEAD_SX if view.startswith("head_") else S

def raster(P2, depth, tris, shape):
    """Draws triangles (in picture coordinates) into a depth buffer: gives (depth, which triangle) per pixel."""
    h, w = shape
    zb = np.full((h, w), np.inf, np.float32)
    tid = np.full((h, w), -1, np.int32)
    T = np.asarray(tris)
    A, B, C = P2[T[:, 0]], P2[T[:, 1]], P2[T[:, 2]]
    lo = np.floor(np.minimum(np.minimum(A, B), C)).astype(int)
    hi = np.ceil(np.maximum(np.maximum(A, B), C)).astype(int)
    for t in range(len(T)):
        x0, y0 = max(lo[t, 0], 0), max(lo[t, 1], 0)
        x1, y1 = min(hi[t, 0], w - 1), min(hi[t, 1], h - 1)
        if x1 < x0 or y1 < y0:
            continue
        a, b, c = A[t], B[t], C[t]
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-9:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        w0 = ((b[1] - c[1]) * (xs - c[0]) + (c[0] - b[0]) * (ys - c[1])) / den
        w1 = ((c[1] - a[1]) * (xs - c[0]) + (a[0] - c[0]) * (ys - c[1])) / den
        w2 = 1.0 - w0 - w1
        inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if not inside.any():
            continue
        i0, i1, i2 = T[t]
        d = w0 * depth[i0] + w1 * depth[i1] + w2 * depth[i2]
        sub = zb[y0:y1 + 1, x0:x1 + 1]
        upd = inside & (d < sub)
        sub[upd] = d[upd]
        tid[y0:y1 + 1, x0:x1 + 1][upd] = t
    return zb, tid


# ------------------------------------------------------------------------------------------------------------------
# A mesh under construction: points, faces (quads and triangles), and for each point which part it is
# ------------------------------------------------------------------------------------------------------------------

class Mesh:
    def __init__(self):
        self.P = []
        self.part = []
        self.faces = []
        self.fpart = []
        self.tag = {}      # name -> list of point indices (rings, joints' neighbourhoods)
        self.want = {}     # face index -> the way it must face (open shells)
        self.cell = {}     # face index -> (grid, ring, column) for the torso and the head

    def add(self, p, part):
        self.P.append(np.array(p, dtype=float))
        self.part.append(part)
        return len(self.P) - 1

    def face(self, idx, part, want=None):
        """want: for a face of an open shell (an ear, the peak), the way it must face (a vector, or a function of
        its middle giving one); such faces are turned to it, the closed body by Blender's own recalculation."""
        self.faces.append(list(idx))
        self.fpart.append(part)
        if want is not None:
            self.want[len(self.faces) - 1] = want

    def bridge(self, a, b, part, closed=True):
        """Quads between two rings of the same count (a above or before b)."""
        n = len(a)
        for j in range(n if closed else n - 1):
            k = (j + 1) % n
            self.face([a[j], a[k], b[k], b[j]], part)

    def tris(self):
        out = []
        for f in self.faces:
            for i in range(1, len(f) - 1):
                out.append((f[0], f[i], f[i + 1]))
        return out

    def tri_fams(self):
        out = []
        for f, p in zip(self.faces, self.fpart):
            out += [p.split("_")[0]] * (len(f) - 2)
        return out


def aligned(prev_pts, new_pts):
    """The new ring's points reordered to run the same way round as the previous ring's (the cyclic shift and
    direction whose offsets from each ring's middle agree best)."""
    a = np.array(prev_pts, float)
    b = np.array(new_pts, float)
    ua = a - a.mean(0)
    ub = b - b.mean(0)
    ua /= np.maximum(np.linalg.norm(ua, axis=1, keepdims=True), 1e-9)
    ub /= np.maximum(np.linalg.norm(ub, axis=1, keepdims=True), 1e-9)
    n = len(b)
    best, order = -1e9, list(range(n))
    for flip in (False, True):
        base = list(range(n))[::-1] if flip else list(range(n))
        for s in range(n):
            o = base[s:] + base[:s]
            score = float((ua * ub[o]).sum())
            if score > best:
                best, order = score, o
    return [new_pts[i] for i in order]


def sgnpow(v, p):
    return np.sign(v) * np.abs(v) ** p


def ring_points(cx, cy, z, a, b_front, b_back, n, p=0.8, start=0.0):
    """A horizontal ring: half-width a, from cy-b_front (front) to cy+b_back (back); point 0 at the front middle,
    going round toward +X."""
    out = []
    for k in range(n):
        th = start + math.tau * k / n
        s, c = math.sin(th), math.cos(th)
        y = cy - b_front * sgnpow(c, p) if c > 0 else cy - b_back * sgnpow(c, p)
        out.append((cx + a * sgnpow(s, p), y, z))
    return out

def mirror_x(p, side):
    return np.array((p[0] * side, p[1], p[2]))


def col_of(k, side):
    return k if side > 0 else (TORSO_N - k) % TORSO_N




# ------------------------------------------------------------------------------------------------------------------
# The body, measured off the body sheet (tpose6)
# ------------------------------------------------------------------------------------------------------------------

TORSO_N = 16
LIMB_N = 10
# The torso's rings (body-sheet rows, from the crotch up) and which of them hold the arm's hole (4 rings: armpit to
# top). Above the hole: the trapezius sloping into the neck, the neck's base.
TORSO_ROWS = [880, 860, 835, 810, 785, 760, 735, 712, 690, 665, 640, 610, 580, 560, 538, 490, 442, 398, 368, 345, 318]
_H0 = TORSO_ROWS.index(538)
HOLE = (_H0, _H0 + 1, _H0 + 2, _H0 + 3)
HOLE_COLS = (3, 4, 5)
# The torso's half width where the arms hide it in the front view (metres), by row: the lats under the armpit, the
# chest, the shoulder's top inside the deltoid, the trapezius and the neck's base.
TORSO_UNDER_ARMS = {538: 0.272, 490: 0.284, 442: 0.268, 398: 0.222, 368: 0.192, 345: 0.15, 318: 0.088}
# How much thinner front to back each top ring is at its sides than at its middle (the trapezius as a ridge).
TOP_THIN = {398: 0.15, 368: 0.35, 345: 0.5, 318: 0.2}
# How much lower each top ring is at its sides than at its middle (metres at its full width): the shoulders slope.
TOP_DROP = {368: 0.012, 345: 0.026, 318: 0.01}
# Shoulder joint row, elbow row, wrist row (the arm's axis is fitted through the drawn arm in the front view, sampled
# between ARM_SAMPLE's rows, split at the elbow).
SHOULDER_ROW, ELBOW_ROW, WRIST_ROW = 404, 642, 757
ARM_SAMPLE = (560, 752)
ARM_ROOT_R = 0.112            # the radius of the arm's root ring (where it comes out of the torso)
# The root ring's middle's height: between the hole's bottom and top rings, so its top stays under the trapezius's rings
# (at the shoulder joint's height it stood above them and folded the shoulder into a box's corner).
ARM_ROOT_Z = 1.475 * K_BODY
ARM_Y = (0.036, -0.03)        # the arm's axis front to back, at the shoulder and at the wrist (from the side view)
# How deep each arm ring is for how wide it is, along the arm (metres from the shoulder: deltoid, biceps, elbow,
# forearm's swell, wrist).
ARM_DEPTH = ((0.0, 1.05), (0.16, 1.02), (0.3, 0.92), (0.37, 0.88), (0.48, 1.0), (0.58, 1.2), (0.66, 1.5))
HAND_K = 1.0                  # his hands against the captain's hand plan: big, thick hands (the sheet: 21 cm long)
# The legs: rows of their rings (from the crotch down), the hip joint, the knee and the ankle.
LEG_ROWS = [900, 937, 975, 1020, 1065, 1110, 1150, 1190, 1235, 1280, 1318, 1348]
HIP_ROW, KNEE_ROW, ANKLE_ROW = 820, 1150, 1348
LEG_PROBE = 0.15              # metres out from the middle where each leg's run is looked for
HIP_X = 0.105
FOOT_YAW = math.radians(14.0)     # toes out
TOE_REACH = 1.04
# The foot's rings below the ankle: height, how far it reaches forward of the ankle, back, and to each side.
FOOT_RINGS = ((0.11, 0.065, 0.064, 0.054), (0.075, 0.13, 0.078, 0.06), (0.04, 0.235, 0.083, 0.07),
              (0.014, 0.232, 0.079, 0.066), (0.0, 0.22, 0.066, 0.056))


def measure_torso(sh):
    """Each torso ring: (z, half-width, front y, back y)."""
    rings = []
    for r in TORSO_ROWS:
        widths = []
        for view in ("front", "back"):
            c0, c1 = SPAN[view]
            run = run_near(sh.body_target, r, MID[view], c0, c1)
            if r in TORSO_UNDER_ARMS:
                widths.append(TORSO_UNDER_ARMS[r] / S)
            else:
                widths.append((run[1] - run[0] + 1) / 2.0)
        a = float(np.mean(widths)) * S
        c0, c1 = SPAN["side"]
        run = run_near(sh.body_target, r, MID["side"], c0, c1)
        if run is None:
            # (another figure's sheet (man_trim) can leave the side view's middle column off the figure at a row: its
            # run nearest that column then)
            rs = runs_of(sh.body_target[r], c0, c1, 3)
            run = min(rs, key=lambda q: min(abs(q[0] - MID["side"]), abs(q[1] - MID["side"])))
            print("%s torso row %d: the side view's run nearest its middle, %s" % (WHO, r, run))
        yf = -(run[1] + 1 - MID["side"]) * S
        back = SIDE_BACK.get(r, run[0])
        yb = -(back - MID["side"]) * S
        # (ninth round, the critic's "armpit fins": the ring just under the arm's hole (row 560) took the front view's
        # run with the arm lying against his side in it, 0.36 m half wide where the ring under it is 0.24: its side
        # points stood out of his ribs as a flap. It is no wider than the ring below it)
        if r == TORSO_ROWS[_H0 - 1] and rings:
            a = min(a, rings[-1][1])
        rings.append((float(body_z(r)), a, yf, yb))
    return rings


def arm_axis(sh):
    """The drawn arm's axis in the front view (his left arm, the right mirrored onto it, and the back view's too):
    shoulder, elbow and wrist points (metres)."""
    m = sh.body_mask
    pts = []
    for r in range(ARM_SAMPLE[0], ARM_SAMPLE[1], 6):
        cs = []
        for view, sign in (("front", 1), ("front", -1), ("back", 1), ("back", -1)):
            c0, c1 = SPAN[view]
            mid = MID[view]
            rs = runs_of(m[r], c0, c1)
            outward = sign * (1 if view == "front" else -1) > 0
            side = [x for x in rs if (x[0] > mid if outward else x[1] < mid)]
            if not side:
                continue
            run = max(side, key=lambda x: x[1]) if outward else min(side, key=lambda x: x[0])
            centre = (run[0] + run[1] + 1) / 2.0
            x = (centre - mid) * S if view == "front" else -(centre - mid) * S
            cs.append(abs(x))
        if cs:
            pts.append((r, float(np.median(cs))))
    rows = np.array([p[0] for p in pts], float)
    xs = np.array([p[1] for p in pts])
    up = rows < ELBOW_ROW
    ku = np.polyfit(rows[up], xs[up], 1)
    kf = np.polyfit(rows[~up], xs[~up], 1)
    shoulder = Vector((float(np.polyval(ku, SHOULDER_ROW)), ARM_Y[0], float(body_z(SHOULDER_ROW))))
    ex = 0.5 * (np.polyval(ku, ELBOW_ROW) + np.polyval(kf, ELBOW_ROW))
    elbow = Vector((float(ex), ARM_Y[0] + (ARM_Y[1] - ARM_Y[0]) * 0.55, float(body_z(ELBOW_ROW))))
    wrist = Vector((float(np.polyval(kf, WRIST_ROW)), ARM_Y[1], float(body_z(WRIST_ROW))))
    return shoulder, elbow, wrist


def arm_width(sh, C, D):
    """Half the arm's width across it at a point of its axis (his left arm; the right and back views averaged)."""
    m = sh.body_mask
    cosang = abs(D.z) / math.hypot(D.x, D.z)
    r = float(body_row(C.z))
    halves = []
    for view in ("front", "back"):
        c0, c1 = SPAN[view]
        mid = MID[view]
        for sign in (1, -1):
            if view == "front":
                col = mid + sign * C.x / S
            else:
                col = mid - sign * C.x / S
            run = run_near(m, r, col, c0, c1)
            if not run:
                continue
            outward = (sign > 0) == (view == "front")
            if run[0] < mid < run[1]:
                edge = run[1] + 1 if outward else run[0]
                halves.append(abs(edge - col))
            else:
                halves.append((run[1] + 1 - run[0]) / 2.0)
    return float(np.median(halves)) * S * cosang


def depth_ratio(s):
    xs = [a for a, _ in ARM_DEPTH]
    return float(np.interp(s, xs, [b for _, b in ARM_DEPTH]))


def leg_ring(sh, r):
    """The left leg at a row: centre x, half width, front y, back y."""
    t = sh.body_target
    xs = []
    for view in ("front", "back"):
        c0, c1 = SPAN[view]
        mid = MID[view]
        for sign in (1, -1):
            col = mid + sign * LEG_PROBE / S if view == "front" else mid - sign * LEG_PROBE / S
            run = run_near(t, r, col, c0, c1)
            if not run:
                continue
            a, b = (run[0] - mid) * S, (run[1] + 1 - mid) * S
            if view == "back":
                a, b = -b, -a
            if sign < 0:
                a, b = -b, -a
            xs.append((max(a, 0.004), b))
    lo = float(np.median([x[0] for x in xs]))
    hi = float(np.median([x[1] for x in xs]))
    c0, c1 = SPAN["side"]
    run = run_near(t, r, MID["side"], c0, c1)
    yf = -(run[1] + 1 - MID["side"]) * S
    yb = -(run[0] - MID["side"]) * S
    return (lo + hi) / 2.0, (hi - lo) / 2.0, yf, yb


def build_body(sh):
    """The body without the head: torso, arms with hands, legs with feet. Gives the Mesh and its joints."""
    M = Mesh()
    rings = measure_torso(sh)
    T = []
    for i, (z, a, yf, yb) in enumerate(rings):
        cy = (yf + yb) / 2.0
        d = (yb - yf) / 2.0
        p = 0.84 if TORSO_ROWS[i] > 560 else 0.86 if TORSO_ROWS[i] > 380 else 0.9
        pts = ring_points(0.0, cy, z, a, d, d, TORSO_N, p)
        # (the top rings are the trapezius: thin front to back out toward the shoulders, a ridge, not a shelf)
        k = TOP_THIN.get(TORSO_ROWS[i], 0.0)
        if k:
            pts = [(x, cy + (y - cy) * (1.0 - k * (abs(x) / a) ** 2), zz) for x, y, zz in pts]
        dz = TOP_DROP.get(TORSO_ROWS[i], 0.0)
        if dz:
            pts = [(x, y, zz - dz * (abs(x) / a) ** 2) for x, y, zz in pts]
        T.append([M.add(q, "torso") for q in pts])
    M.tag["torso_rings"] = T
    for i in range(len(T) - 1):
        lower, upper = T[i], T[i + 1]
        for k in range(TORSO_N):
            j = (k + 1) % TORSO_N
            if i in (HOLE[0], HOLE[1], HOLE[2]) and (k in (3, 4) or k in (11, 12)):
                continue
            M.face([lower[k], lower[j], upper[j], upper[k]], "torso")
            M.cell[len(M.faces) - 1] = ("torso", i, k)
    z0, a0, yf0, yb0 = rings[0]
    crotch = M.add((0.0, (yf0 + yb0) / 2.0 + 0.01, z0 - 0.014), "torso")
    M.tag["crotch"] = [crotch]

    joints = {}
    shoulder, elbow, wrist = arm_axis(sh)
    joints.update(shoulder_l=shoulder, elbow_l=elbow, wrist_l=wrist)
    print("BROTHER arm: shoulder %s elbow %s wrist %s" % (tuple(round(v, 3) for v in shoulder), tuple(round(v, 3) for v in elbow), tuple(round(v, 3) for v in wrist)))

    for side in (1, -1):
        arm(M, sh, T, side, shoulder, elbow, wrist, joints)
        leg(M, sh, T, rings, crotch, side, joints)
    return M, T, joints


def col_of(k, side):
    return k if side > 0 else (TORSO_N - k) % TORSO_N


def arm(M, sh, T, side, J, E, W, joints):
    """An arm out of the torso's hole, along the drawn axis, ending in a hand. Built as his left and mirrored."""
    sfx = "_l" if side > 0 else "_r"
    part = "arm" + sfx
    X = Vector((1, 0, 0))
    F = Vector((0, -1, 0))
    Du = (E - J).normalized()
    Df = (W - E).normalized()
    N = (Du + X).normalized()
    U = (Vector((0, 0, 1)) - N * N.z).normalized()
    Fh = F - N * N.dot(F)
    Fh.normalize()
    centre = J + N * 0.035
    centre.z = ARM_ROOT_Z
    (ra, rb, rc, rd) = [T[i] for i in HOLE]
    c3, c4, c5 = (col_of(k, side) for k in HOLE_COLS)
    hole = [rd[c4], rd[c3], rc[c3], rb[c3], ra[c3], ra[c4], ra[c5], rb[c5], rc[c5], rd[c5]]
    M.tag["hole" + sfx] = hole
    for j, v in enumerate(hole):
        ph = math.tau * j / LIMB_N
        q = centre + (U * math.cos(ph) + Fh * math.sin(ph)) * ARM_ROOT_R
        M.P[v] = mirror_x(q, side)
        M.part[v] = "shoulder" + sfx
    Lu, Lf = (E - J).length, (W - E).length
    stations = [0.04, 0.1, 0.165, 0.23, 0.29, Lu - 0.035, Lu, Lu + 0.04, Lu + 0.1, Lu + 0.17, Lu + Lf - 0.045, Lu + Lf]
    stations = sorted(set(round(s, 4) for s in stations if s <= Lu + Lf))
    prev = hole
    rings = [hole]
    for s in stations:
        if s <= Lu:
            C = J + Du * s
            D = Du if s < Lu - 0.05 else (Du + Df).normalized()
        else:
            C = E + Df * (s - Lu)
            D = Df if s > Lu + 0.05 else (Du + Df).normalized()
        A = (X - D * D.x).normalized()
        a = arm_width(sh, C, D)
        if s > Lu + Lf - 0.06:
            a = min(a, 0.042 if s < Lu + Lf - 0.01 else 0.036)
        b = a * depth_ratio(s)
        # a heavy round deltoid over the top of the arm, fuller out and a little forward
        dl = math.exp(-((s - 0.075) / 0.065) ** 2)
        a *= 1.0 + 0.16 * dl
        b *= 1.0 + 0.16 * dl
        C = C + A * (0.01 * dl) + F * (0.003 * dl) + Vector((0, 0, 0.008 * dl))
        # the biceps' and the forearm's swell toward the front (rugby arms)
        bi = math.exp(-((s - 0.2) / 0.07) ** 2)
        fo = math.exp(-((s - (Lu + 0.08)) / 0.06) ** 2)
        ring = []
        for j in range(LIMB_N):
            ph = math.tau * j / LIMB_N
            fs = math.sin(ph)
            swell = 1.0 + (0.08 * bi + 0.05 * fo) * max(fs, 0.0)
            ring.append(M.add(mirror_x(C + A * (a * math.cos(ph)) + F * (b * fs * swell), side), part))
        M.bridge(prev, ring, part) if side > 0 else M.bridge(ring, prev, part)
        rings.append(ring)
        prev = ring
    M.tag["arm_rings" + sfx] = rings
    M.tag["arm_stations" + sfx] = [0.0] + stations
    joints["arm_frame"] = (Du, Df)
    first = len(M.P)
    place_base_hand(M, prev, side, W, Df, joints)
    M.tag["hand_range" + sfx] = (first, len(M.P))
    M.tag["wrist_ring" + sfx] = list(prev)
    # (the hand is planned at the captain's size and grown about the wrist to his: HAND_K)
    Wm = np.array(mirror_x(W, side))
    for v in range(first, len(M.P)):
        M.P[v] = Wm + (M.P[v] - Wm) * HAND_K
    for key in list(joints):
        if key.endswith(sfx) and (key.split("_")[0] in FINGERS + ("thumb", "knuckles")):
            val = joints[key]
            if isinstance(val, list):
                joints[key] = [Vector(Wm + (np.array(b) - Wm) * HAND_K) for b in val]
            elif isinstance(val, Vector):
                joints[key] = Vector(Wm + (np.array(val) - Wm) * HAND_K)

# His hands, from their own sheet (concept_brother_hands.jpg: his left hand's back, palm and thumb side, fingers up
# and spread; and below, lying flat, from the fingertips, and hanging relaxed). Measured on its back view at 0.404 mm a
# pixel (the hand from the wrist to the middle fingertip 0.208 m, the body sheet's): the palm from the wrist to the
# knuckles 10 cm, 13 cm wide at the knuckles, the wrist 8.7 cm wide; the fingers from their knuckles 7.7 (little) to
# 10.4 cm (middle), the ring finger longer than the index; a heavy thumb. Metres, built directly (no scaling).
HAND = {
    "wrist": (0.010, 0.0435, 0.031),            # along, half width, half thickness
    "heel": (0.042, 0.058, 0.037),
    "knuckles": (0.100, 0.07, 0.022),
    # name, root quad (0 the thumb's side), length from its knuckle, half width
    "fingers": (("index", 0, 0.090, 0.0152), ("middle", 1, 0.102, 0.0158), ("ring", 2, 0.096, 0.015),
                ("little", 3, 0.076, 0.0134)),
    "segments": (0.45, 0.31, 0.24),
    "thumb": (0.074, 0.023),                    # length beyond its base, base half width
}
# The poses: the sheet's (fingers straight and spread, the thumb out: for checking against the sheet) and the hang (the
# sheet's "hanging relaxed": fingers together, gently curled, the thumb in front of the index).
HAND_POSES = {
    "sheet": {"spread": (-2.0, 0.0, -2.0, -5.0), "curl": (0.02, 0.02, 0.02), "thumb": (0.75, 0.6, -0.1), "thumb_curl": 0.05},
    # (the sheet'"'"'s thumb-side view: the fingers bent forward a little at their knuckles, the thumb up and forward)
    "thumbview": {"spread": (-2.0, 0.0, -2.0, -5.0), "curl": (0.6, 0.25, 0.1), "thumb": (0.3, 0.6, -0.8), "thumb_curl": 0.1},
    "relaxed": {"spread": (-2.0, 0.0, 2.0, 4.0), "curl": (0.26, 0.38, 0.3), "thumb": (0.78, 0.5, -0.38), "thumb_curl": 0.22},
}


def hand(M, wrist_ring, side, W, L, joints, pose="relaxed"):
    """A hand from the wrist ring, in the captain's low-poly way (as Twilight Princess's figures: a boxy palm, four
    fingers of four-sided sections in three segments with loops at the joints, a separate thumb, the rest painted),
    sized and shaped to his hands sheet:
    - the palm a wedge of three rings of 10: the wrist, narrower than the forearm; the heel, thickest, with the thenar
      pad (the thumb's) and the hypothenar pad (the little finger's) standing off the palm; the knuckles, widest, their
      ridge standing off the back;
    - each finger out of one of the four quads across the palm's end: a ring of four at its knuckle and at each joint
      and one short of its tip, closed by a point; different lengths (middle, ring, index, little);
    - the thumb out of the palm's side face between the heel and the knuckles, from a fat base.
    Its back faces out and a little forward (36 degrees round from straight out)."""
    po = HAND_POSES[pose]
    sfx = "_l" if side > 0 else "_r"
    part = "hand" + sfx
    X = Vector((1, 0, 0))
    F = Vector((0, -1, 0))
    A = (X - L * L.x).normalized()
    tw = math.radians(36.0)
    Tb = A * math.cos(tw) + F * math.sin(tw)          # the back of the hand
    Wd = -A * math.sin(tw) + F * math.cos(tw)         # across, toward the thumb
    back = [3, 2, 1, 0, 9]                            # ring points on the back, thumb side first
    palm = [4, 5, 6, 7, 8]                            # on the palm, thumb side first
    across = [1.0, 0.5, 0.0, -0.5, -1.0]

    def ring_at(at, hw, ht, back_lift=(0, 0, 0, 0, 0), palm_drop=(0, 0, 0, 0, 0)):
        pts = [None] * LIMB_N
        for j, w, lb in zip(back, across, back_lift):
            edge = abs(w) == 1.0
            pts[j] = at + Wd * (w * hw * (0.9 if edge else 1.0)) + Tb * (ht * (0.7 if edge else 1.0) + lb)
        for j, w, pd in zip(palm, across, palm_drop):
            edge = abs(w) == 1.0
            pts[j] = at + Wd * (w * hw * (0.9 if edge else 1.0)) - Tb * (ht * (0.7 if edge else 1.0) + pd)
        return [M.add(mirror_x(q, side), part) for q in pts]

    def bridge(a, b, pt=part):
        M.bridge(a, b, pt) if side > 0 else M.bridge(b, a, pt)
    a0, w0, t0 = HAND["wrist"]
    a1, w1, t1 = HAND["heel"]
    a3, w3, t3 = HAND["knuckles"]
    r0 = ring_at(W + L * a0, w0, t0)
    # (the heel a little toward the thumb: the thenar pad's fullness; the knuckles' row a little toward the little
    # finger, so the middle finger sits over the wrist as the sheet draws it)
    r1 = ring_at(W + L * a1 + Wd * 0.006, w1, t1, palm_drop=(0.012, 0.004, 0.0, 0.003, 0.008))
    knuck = W + L * a3 + Wd * 0.004
    r3 = ring_at(knuck, w3, t3, back_lift=(0.002, 0.004, 0.004, 0.004, 0.002))
    bridge(wrist_ring, r0)
    bridge(r0, r1)
    bridge(r1, r3)
    thumb_root = [r1[3], r3[3], r3[4], r1[4]]
    target = sorted(thumb_root)
    for fi in range(len(M.faces) - 1, -1, -1):
        if sorted(M.faces[fi]) == target:
            del M.faces[fi]
            del M.fpart[fi]
            break
    M.tag["hand_rings" + sfx] = [wrist_ring, r0, r1, r3]

    def grow(name, root, frames, tip_at, pname):
        a0_, step = frames[0]
        rings = [list(root)]
        for at, ac, bk, hw, ht in frames[1:]:
            ring = []
            for j in range(4):
                a = math.radians(a0_ + step * j)
                q = at + ac * (math.cos(a) * hw * 1.414) + bk * (math.sin(a) * ht * 1.414)
                ring.append(M.add(mirror_x(q, side), pname))
            rings.append(ring)
        for a, b in zip(rings, rings[1:]):
            M.bridge(a, b, pname)
        tip = M.add(mirror_x(tip_at, side), pname)
        last = rings[-1]
        for j in range(4):
            M.face([last[j], last[(j + 1) % 4], tip], pname)
        M.tag["finger_rings%s_%s" % (sfx, name)] = rings
        M.tag["finger_ends%s_%s" % (sfx, name)] = [tip, -1]

    curl = po["curl"]
    segs = HAND["segments"]
    for (name, i, length, hw), spread in zip(HAND["fingers"], po["spread"]):
        root = [r3[back[i]], r3[back[i + 1]], r3[palm[i + 1]], r3[palm[i]]]
        k0 = knuck + Wd * (across[i] + across[i + 1]) / 2.0 * w3
        way = Matrix.Rotation(math.radians(spread), 3, Tb) @ L.copy()
        ac, bk = (Matrix.Rotation(math.radians(spread), 3, Tb) @ Wd.copy()), Tb.copy()
        frames = [(45.0, 90.0)]
        at = k0 + way * 0.009
        frames.append((at.copy(), ac.copy(), bk.copy(), hw * 1.04, hw * 0.94))         # the knuckle
        bones = [k0.copy()]
        for si, f in enumerate(segs):
            rot = Matrix.Rotation(-curl[si], 3, ac)
            way = rot @ way
            bk = rot @ bk
            at = at + way * (length * f)
            bones.append(at.copy())
            if si < 2:
                # (each joint a little fuller than the finger between: the knuckles' bumps)
                frames.append((at - way * (length * f * 0.5), ac.copy(), bk.copy(), hw * (0.95, 0.9)[si], hw * (0.84, 0.78)[si]))
                frames.append((at.copy(), ac.copy(), bk.copy(), hw * (0.98, 0.92)[si], hw * (0.88, 0.8)[si]))
        frames.append((at - way * 0.005, ac.copy(), bk.copy(), hw * 0.86, hw * 0.72))
        grow(name, root, frames, at + way * 0.006 - bk * 0.002, part + "_" + name)
        joints["%s%s" % (name, sfx)] = [Vector(mirror_x(b, side)) for b in bones]
    # the thumb: its frame U along the palm, V toward the back
    rootc = sum((Vector(mirror_x(M.P[v], side)) for v in thumb_root), Vector()) / 4.0
    tw_, tl_, tb_ = po["thumb"]
    way = (Wd * tw_ + L * tl_ + Tb * tb_).normalized()
    U = (L - way * L.dot(way)).normalized()
    V = way.cross(U).normalized()
    if V.dot(Tb) < 0:
        V = -V
    tlen, tr = HAND["thumb"]
    frames = [(135.0, -90.0)]
    at = rootc + way * 0.018
    frames.append((at.copy(), U.copy(), V.copy(), tr, tr * 0.85))                        # the fat base
    bones = [rootc.copy()]
    for si, (f, rad) in enumerate(((0.42, tr * 0.86), (0.32, tr * 0.78), (0.26, tr * 0.7))):
        rot = Matrix.Rotation(-po["thumb_curl"], 3, U.cross(way).normalized())
        way = rot @ way
        U = rot @ U
        V = rot @ V
        at = at + way * (tlen * f)
        bones.append(at.copy())
        if si < 2:
            frames.append((at.copy(), U.copy(), V.copy(), rad, rad * 0.86))
    frames.append((at - way * 0.005, U.copy(), V.copy(), tr * 0.6, tr * 0.5))
    grow("thumb", thumb_root, frames, at + way * 0.006, part + "_thumb")
    joints["thumb%s" % sfx] = [Vector(mirror_x(b, side)) for b in bones]
    joints["thumb_back%s" % sfx] = np.array(mirror_x(V, side))
    joints["hand_frame%s" % sfx] = tuple(np.array(mirror_x(v, side)) for v in (Tb, Wd, L))
    joints["knuckles%s" % sfx] = Vector(mirror_x(knuck, side))


# The hands sheet's views of his left hand, for checking the hand built in the sheet's own pose: (where it is: the
# columns and the rows above its wrist that are compared (the sheet cuts the forearm off below: not a feature), which
# way across the picture runs: the hand's own "across toward the thumb" (+1), back (+2) or their reverse, the middle
# fingertip's place (column, row) to put the model's on).
HAND_SHEET_VIEWS = {
    "back": ((400, 940), (80, 560), 1, (612.0, 92.0), "sheet"),
    "palm": ((1120, 1700), (80, 560), -1, None, "sheet"),
    "thumb": ((1980, 2420), (80, 560), 2, None, "thumbview"),
}
HAND_SX = 0.208 / 515.0
HAND_ALIGN = {}


def hand_check(sh):
    """The hand built alone in the sheet's pose (fingers up) and drawn as a filled shape from the sheet's back, palm and
    thumb side, against the sheet's: the difference pictures (to --out) and the worst gaps."""
    Mh = Mesh()
    # (fingers along -Z, as on the body: with them along +Z the hand came out as its own mirror image, a right hand)
    L = Vector((0.0, 0.0, -1.0))
    W = Vector((0.0, 0.0, 0.0))
    # (a wrist ring for it to grow from, as the forearm's would be)
    tw = math.radians(36.0)
    A = Vector((1.0, 0.0, 0.0))
    F = Vector((0.0, -1.0, 0.0))
    Tb = A * math.cos(tw) + F * math.sin(tw)
    Wd = -A * math.sin(tw) + F * math.cos(tw)
    ring = []
    for j in range(LIMB_N):
        ph = math.tau * j / LIMB_N
        ring.append(Mh.add(np.array(W - L * 0.02 + A * (0.034 * math.cos(ph)) + F * (0.05 * math.sin(ph))), "arm_l"))
    res = {}
    base_n = len(Mh.P)
    base_f = len(Mh.faces)
    for v, ((c0, c1), (r0, r1), axis, tip, pose) in HAND_SHEET_VIEWS.items():
        del Mh.P[base_n:], Mh.part[base_n:], Mh.faces[base_f:], Mh.fpart[base_f:]
        Mh.want = {}
        joints = {}
        hand(Mh, ring, 1, W, L, joints, pose=pose)
        fix_winding(Mh)
        P = np.array(Mh.P)
        tris = Mh.tris()
        ax = {1: Wd, -1: -Wd, 2: Tb, -2: -Tb}[axis]
        depth_dir = ax.cross(L)
        u = P @ np.array(ax)
        w_ = P @ np.array(L)
        dep = P @ np.array(depth_dir)
        target = np.zeros_like(sh.hands_mask)
        target[r0:r1, c0:c1] = sh.hands_mask[r0:r1, c0:c1]
        # the model's middle fingertip on the sheet's (back view), else the best overlap of the two shapes
        tipv = Mh.tag["finger_ends_l_middle"][0]
        tc, tr = tip if tip else ((c0 + c1) / 2.0, r0 + 40.0)
        P2 = np.stack([tc + (u - u[tipv]) / HAND_SX, tr - (w_ - w_[tipv]) / HAND_SX], 1)
        zb, _ = raster(P2, dep, tris, target.shape)
        full = np.isfinite(zb)
        mc = full[r0:r1, c0:c1]
        tc_ = target[r0:r1, c0:c1]

        def score(dx, dy):
            s = np.roll(np.roll(mc, dy, 0), dx, 1)
            return float((s & tc_).sum()) / max(float((s | tc_).sum()), 1.0)
        best = (score(0, 0), 0, 0)
        if not tip:
            for dx in range(-240, 241, 8):
                for dy in range(-40, 41, 8):
                    sc_ = score(dx, dy)
                    if sc_ > best[0]:
                        best = (sc_, dx, dy)
            b0 = best
            for dx in range(b0[1] - 8, b0[1] + 9, 2):
                for dy in range(b0[2] - 8, b0[2] + 9, 2):
                    sc_ = score(dx, dy)
                    if sc_ > best[0]:
                        best = (sc_, dx, dy)
        iou = best[0]
        m = np.zeros_like(full)
        m[r0:r1, c0:c1] = np.roll(np.roll(mc, best[2], 0), best[1], 1)
        # (kept for painting the hands from the sheet: where the hand's points fall in this view)
        HAND_ALIGN[v] = (np.array(ax), np.array(L), u[tipv], w_[tipv], tc + best[1], tr + best[2], pose, P.copy())
        r = gaps(m, target, (r0, r1), HAND_SX)
        res[v] = (round(r[0], 2), round(r[1], 2), round(iou, 3))
        if OUT:
            os.makedirs(OUT, exist_ok=True)
            diff_picture(m, target, (c0, r0 - 10, c1, r1 + 10), os.path.join(OUT, "handdiff_%s.png" % v), sh.hands_pix)
    print("BROTHER hand silhouettes (worst cm, 99%% cm, overlap): %s" % json.dumps(res))
    return res


def leg(M, sh, T, rings, crotch, side, joints):
    """A leg from the torso's bottom ring and the crotch down to the ankle, then the foot as rings round its
    footprint, closed underneath."""
    sfx = "_l" if side > 0 else "_r"
    part = "leg" + sfx
    bottom = T[0]
    if side > 0:
        top = [bottom[k] for k in range(0, 9)] + [crotch]
    else:
        top = [bottom[col_of(k, -1)] for k in range(0, 9)] + [crotch]
    prev = top
    allr = [top]
    angles = [math.radians(-36.0 + 36.0 * j) for j in range(LIMB_N)]
    centre_xy = []
    for r in LEG_ROWS:
        cx, a, yf, yb = leg_ring(sh, r)
        cy, b = (yf + yb) / 2.0, (yb - yf) / 2.0
        z = float(body_z(r))
        ring = []
        for th in angles:
            s_, c_ = math.sin(th), math.cos(th)
            ring.append(M.add(mirror_x((cx + a * sgnpow(s_, 0.85), cy - b * sgnpow(c_, 0.85), z), side), part))
        M.bridge(prev, ring, part) if side > 0 else M.bridge(ring, prev, part)
        prev = ring
        allr.append(ring)
        centre_xy.append((cx, cy, z))
    ax, ay, az = centre_xy[-1]
    joints["hip" + sfx] = Vector(mirror_x((HIP_X, (rings[0][2] + rings[0][3]) / 2.0 + 0.005, float(body_z(HIP_ROW))), side))
    kc = [c for c, r in zip(centre_xy, LEG_ROWS) if r == KNEE_ROW][0]
    joints["knee" + sfx] = Vector(mirror_x((kc[0], kc[1] - 0.005, kc[2]), side))
    joints["ankle" + sfx] = Vector(mirror_x((ax, ay + 0.005, float(body_z(ANKLE_ROW))), side))
    # The foot: rings round its footprint at each height, the toes out by FOOT_YAW.
    fwd = Vector((math.sin(FOOT_YAW), -math.cos(FOOT_YAW), 0.0))
    lat = Vector((math.cos(FOOT_YAW), math.sin(FOOT_YAW), 0.0))
    foot_part = "foot" + sfx
    M.tag["leg_rings" + sfx] = list(allr)
    if BASE_FEET:
        if "foot" not in HB:
            HB["foot"] = refine_toes(shape_foot(fit_base_foot(load_base_foot(unsub=FOOT_UNSUBDIV), foot_profile(sh, ax, ay), FOOT_HEIGHT_K)))
        base = HB["foot"]
        o = np.array(mirror_x(Vector((ax, ay, 0.0)), side))
        f_m = np.array(mirror_x(fwd, side))
        l_m = np.array(mirror_x(lat, side))
        ids, bf, zf = place_base_foot(M, base, prev, o, f_m, l_m, side, foot_part)
        M.tag["foot_faces" + sfx] = bf + zf
        M.tag["foot_frame" + sfx] = (o, f_m, l_m)
        Pn = np.array(M.P)
        tips = [Pn[ids[t]] for t in base["tips"]]
        M.tag["foot_toes" + sfx] = [(tips[0], 0.0085)] + [(t, 0.0052 - 0.0004 * i) for i, t in enumerate(tips[1:])]
        tip_u = min(float(np.dot(t - o, f_m)) for t in tips)
        joints["ball" + sfx] = Vector(o + f_m * (tip_u - 0.06) + np.array((0.0, 0.0, 0.028)))
        joints["toe_tip" + sfx] = Vector(o + f_m * (tip_u + 0.01) + np.array((0.0, 0.0, 0.02)))
        return
    if FOOT_N:
        foot_rings(M, prev, angles, ax, ay, fwd, lat, side, sfx, joints)
        return
    for z, front, backr, half in FOOT_RINGS:
        ring = []
        for th in angles:
            # the footprint as an egg: forward `front`, back `backr`, across `half` (a little narrower at the heel);
            # each point at its own angle round the egg, turned with the foot, so the toes get the front points
            al = th - FOOT_YAW
            cu, cv = math.cos(al), math.sin(al)
            # (the toes' end squarer and wider than an egg, and reaching further, as the sheet's long splayed toes;
            # stage one's egg front made them blunt)
            if cu > 0:
                u = sgnpow(cu, 0.55) * front * TOE_REACH
                v = sgnpow(cv, 0.8) * half * (1.0 + 0.18 * cu)
            else:
                u = cu * backr
                v = cv * half * (1.0 if cu > -0.2 else 0.88)
            q = Vector((ax, ay, z)) + fwd * u + lat * v
            ring.append(M.add(mirror_x(q, side), foot_part))
        M.bridge(prev, ring, foot_part) if side > 0 else M.bridge(ring, prev, foot_part)
        prev = ring
        allr.append(ring)
    sole = M.add(mirror_x(Vector((ax, ay, 0.0)) + fwd * 0.06, side), foot_part)
    for j in range(LIMB_N):
        k = (j + 1) % LIMB_N
        M.face([prev[j], prev[k], sole] if side > 0 else [prev[k], prev[j], sole], foot_part)
    M.tag["leg_rings" + sfx] = allr
    joints["ball" + sfx] = Vector(mirror_x(Vector((ax, ay, 0.025)) + fwd * 0.135, side))
    joints["toe_tip" + sfx] = Vector(mirror_x(Vector((ax, ay, 0.02)) + fwd * 0.22, side))


# Polish pass (the critic: "boot-shaped blocks with no toes, arch, heel or ankle bones"): the foot's rings have 24
# points (the ankle's 10 zipped to them), so the big toe parts from the rest by a groove, the small toes' tips are
# scalloped, the inner side lifts into an arch, the heel is round and the ankle bones stand out. Its rings:
# (height, reach forward of the ankle, back, half width), as FOOT_RINGS, two more toward the toes.
FOOT_N = 24
FOOT_RINGS2 = ((0.105, 0.07, 0.062, 0.052), (0.078, 0.12, 0.074, 0.058), (0.052, 0.19, 0.08, 0.066),
               (0.032, 0.232, 0.081, 0.07), (0.014, 0.236, 0.078, 0.067), (0.003, 0.226, 0.07, 0.06))


def foot_shape(th, z, front, backr, half):
    """(forward, across toward his outside, height) of a foot point at angle th round the ring (FOOT_YAW taken)."""
    al = th - FOOT_YAW
    cu, cv = math.cos(al), math.sin(al)
    if cu > 0:
        u = sgnpow(cu, 0.55) * front * TOE_REACH
        v = sgnpow(cv, 0.8) * half * (1.0 + 0.18 * cu)
    else:
        # (the heel round, a little narrower than the ball)
        u = -sgnpow(-cu, 0.85) * backr
        v = cv * half * (0.98 if cu > -0.2 else 0.84)
    zz = z
    toes = z < 0.045
    if cu > 0.35 and toes:
        # the toe line slopes back toward the little toe (v > 0 is his outside)
        u -= 0.022 * max(cv + 0.2, 0.0) * (1.0 if z < 0.03 else 0.6)
        # the big toe's tip round, the groove between it and the second toe
        g = math.exp(-((cv + 0.3) / 0.11) ** 2)
        u -= (0.02 if z < 0.03 else 0.011) * g
        if z > 0.02:
            zz -= 0.005 * g * max(cu - 0.5, 0.0) / 0.5
        # the small toes' tips scalloped
        for c in (0.0, 0.3, 0.58):
            u -= (0.008 if z < 0.03 else 0.004) * math.exp(-((cv - c) / 0.07) ** 2)
        # the toes thinner than the ball: their tops dip toward the tips
        if z > 0.02:
            zz -= 0.008 * max(cu - 0.6, 0.0) / 0.4
    # the arch: the inner side's sole lifted between the heel and the ball
    if z < 0.02 and cv < -0.2 and -0.55 < cu < 0.55:
        lift = (1.0 - (cu / 0.55) ** 2) * min((-cv - 0.2) / 0.5, 1.0)
        zz += 0.016 * lift * (1.0 if z < 0.008 else 0.5)
        v *= 1.0 - 0.12 * lift
    # the ankle bones: the inner one higher and further forward, the outer one lower and further back
    if z > 0.07:
        inner = math.exp(-((cv + 0.95) / 0.25) ** 2 - ((cu - 0.1) / 0.45) ** 2)
        outer = math.exp(-((cv - 0.95) / 0.25) ** 2 - ((cu + 0.15) / 0.45) ** 2)
        k_in = 0.006 if z > 0.09 else 0.002
        k_out = 0.003 if z > 0.09 else 0.006
        v += -k_in * inner + k_out * outer
    # the Achilles tendon's notch behind the ankle
    if z > 0.07 and cu < -0.8:
        u += 0.006 * (-cu - 0.8) / 0.2
    return u, v, zz


def foot_rings(M, ankle_ring, angles, ax, ay, fwd, lat, side, sfx, joints):
    part = "foot" + sfx
    th_f = [angles[0] + math.tau * j / FOOT_N for j in range(FOOT_N)]
    rings = []
    for z, front, backr, half in FOOT_RINGS2:
        ring = []
        for th in th_f:
            u, v, zz = foot_shape(th, z, front, backr, half)
            q = Vector((ax, ay, zz)) + fwd * u + lat * v
            ring.append(M.add(mirror_x(q, side), part))
        rings.append(ring)
    zipper(M, ankle_ring, rings[0], None, part,
           order=(np.array(angles) - angles[0], np.array(th_f) - angles[0]))
    for a, b in zip(rings, rings[1:]):
        M.bridge(a, b, part) if side > 0 else M.bridge(b, a, part)
    # the sole: a fan from a point under the ball's back (the arch's lift is on its ring)
    sole = M.add(mirror_x(Vector((ax, ay, 0.0)) + fwd * 0.07, side), part)
    last = rings[-1]
    for j in range(FOOT_N):
        k = (j + 1) % FOOT_N
        M.face([last[j], last[k], sole] if side > 0 else [last[k], last[j], sole], part)
    M.tag["foot_rings" + sfx] = rings
    joints["ball" + sfx] = Vector(mirror_x(Vector((ax, ay, 0.025)) + fwd * 0.15, side))
    joints["toe_tip" + sfx] = Vector(mirror_x(Vector((ax, ay, 0.02)) + fwd * 0.23, side))


# ------------------------------------------------------------------------------------------------------------------
# The feet, fifth round (the critic: "smooth mittens; toes exist only as paint"): no longer lofted rings. Each foot is
# Blender Studio's `Foot - Stylized` (the same CC0 bundle as the head and hands; 798 quads with five real toes),
# un-subdivided twice (about 450 triangles a foot, the toes kept), warped height by height to the body sheet's side
# view (heel, instep, toes) and front view (the ankle), given ankle bones, joined to the shin's last ring, unwrapped
# into two islands (sole; the rest cut up the back of the heel) and painted from the shin's tone with toenails.
#
# FOR OTHER FIGURES: these functions take every figure-specific number as an argument and can be copied as they are:
#   load_base_foot(bundle, unsub)            -> the foot in its own frame (u forward, v outward, z up from the sole)
#   fit_base_foot(base, prof, ...)           -> warped to a profile of target extents by height
#   place_base_foot(M, base, ankle_ring, origin, fwd, lat, side, part) -> added to a Mesh and zipped to the shin
#   foot_islands(M, faces, origin, fwd, lat, top_loop)  -> its UV islands (conformal unwrap with planned seams)
#   paint_feet(rgb, pos, nrm, hit, mine, frame, toes, base_c) -> skin tone, grooves, toenails
# Only foot_profile() reads this figure's sheet (its rows, columns and scale).
# ------------------------------------------------------------------------------------------------------------------

def foot_profile(sh, ax, ay):
    """This figure's sheet read for fit_base_foot: at each row from just under the ankle ring to the sole, the side
    view's reach forward of and behind the ankle's axis (divided by the cosine of the toes' turn out, which the side
    view foreshortens), and above the instep the front view's half width of his left ankle."""
    zs, fr, bk, hf = [], [], [], []
    c0, c1 = SPAN["side"]
    col = MID["side"] - ay / S
    for r in range(FOOT_PROFILE_ROWS[1], FOOT_PROFILE_ROWS[0] - 1, -3):
        run = run_near(sh.body_mask, r, col, c0, c1)
        if not run:
            continue
        yf = -(run[1] + 1 - MID["side"]) * S
        yb = -(run[0] - MID["side"]) * S
        z = float(body_z(r))
        half = np.nan
        if z > 0.105:
            f0, f1 = SPAN["front"]
            rf = run_near(sh.body_mask, r, MID["front"] + ax / S, f0, f1)
            if rf and not (rf[0] < MID["front"] < rf[1]):
                half = (rf[1] + 1 - rf[0]) / 2.0 * S
        zs.append(z)
        fr.append((ay - yf) / math.cos(FOOT_YAW))
        bk.append((yb - ay) / math.cos(FOOT_YAW))
        hf.append(half)
    # the ball's width: the front view's widest run low on the foot is the width times the cosine of the turn out plus
    # the length times its sine
    f0, f1 = SPAN["front"]
    wide = 0.0
    for r in range(FOOT_PROFILE_ROWS[1], FOOT_PROFILE_ROWS[1] - 40, -2):
        rf = run_near(sh.body_mask, r, MID["front"] + (ax + 0.04) / S, f0, f1)
        if rf and not (rf[0] < MID["front"] < rf[1]):
            wide = max(wide, (rf[1] + 1 - rf[0]) * S)
    L = max(a + b for a, b in zip(fr, bk)) * math.cos(FOOT_YAW)
    ball = (wide - L * math.sin(FOOT_YAW)) / math.cos(FOOT_YAW) / 2.0 * 1.1
    print("%s foot profile: %s" % (WHO, ", ".join("z %.3f f %.3f b %.3f w %.3f" % q for q in zip(zs[::4], fr[::4], bk[::4], hf[::4]))))
    print("%s foot ball: front view %.1f cm wide, so the ball %.1f cm" % (WHO, wide * 100, ball * 200))
    return {"z": zs, "front": fr, "back": bk, "half": hf, "ball_half": ball}


BASE_FEET = True
FOOT_UNSUBDIV = int(arg("--footunsub", "1"))   # (ninth round: once, not twice: twice left toes four points round, "jagged triangular spikes"; the result is collapsed back to FOOT_KEEP_TRIS)
FOOT_PROFILE_ROWS = (1352, 1449)   # the sheet rows the foot is fitted over (just under the ankle ring to the sole)
FOOT_HEIGHT_K = 1.06               # the base foot's height times this (its ankle cap 10 cm up: the sheet's ankle bone ~10.6 cm)
TOE_BIG = 0.55                     # shape_foot: the big toe this much broader across
ARCH = 0.009                       # shape_foot: metres the inner arch is lifted
HEEL_OUT = 0.006                   # shape_foot: metres the heel is rounded out behind


def load_base_foot(bundle=None, unsub=2):
    """The bundle's `Foot - Stylized` (a left foot), un-subdivided, its ankle cap taken off. Gives a dict: F (points as
    (u forward, v toward the little toe's side, z up from the sole), the ankle cap's middle at u = v = 0), faces,
    loop (the open ankle loop, in order), toes (five lists of point indices, the big toe first) and tips (the
    point of each toe furthest forward)."""
    bundle = bundle or BASE_BUNDLE
    with bpy.data.libraries.load(bundle, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n.replace(" ", "") == "Foot-Stylized"]
    o = dst.objects[0]
    bpy.context.scene.collection.objects.link(o)
    o.modifiers.clear()
    if unsub:
        m = o.modifiers.new("un", "DECIMATE")
        m.decimate_type = "UNSUBDIV"
        m.iterations = unsub
    bpy.context.view_layer.update()
    ev = o.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    P = np.array([tuple(v.co) for v in me.vertices], float)
    faces = [list(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    bpy.data.objects.remove(o, do_unlink=True)
    # (the cap: a fan round its highest point of most faces)
    val = np.zeros(len(P), int)
    for f in faces:
        val[f] += 1
    top = P[:, 2] > P[:, 2].max() - 0.004
    hub = int(np.argmax(np.where(top, val, -1)))
    keep = [f for f in faces if hub not in f]
    used = sorted({v for f in keep for v in f})
    remap = {v: i for i, v in enumerate(used)}
    P = P[used]
    faces = [[remap[v] for v in f] for f in keep]
    hub_xy = np.array(P[:, :2].mean(0))
    loop = max(open_loops(faces), key=len)
    hub_xy = P[loop, :2].mean(0)
    F = np.stack([-(P[:, 1] - hub_xy[1]), P[:, 0] - hub_xy[0], P[:, 2] - P[:, 2].min()], 1)
    # the toes: the points beyond a line across the foot, as separate pieces; the line as far back as still gives five
    adj = {}
    for f in faces:
        for i in range(len(f)):
            a, b = f[i], f[(i + 1) % len(f)]
            adj.setdefault(a, set()).add(b)
            adj.setdefault(b, set()).add(a)

    def pieces(t, k=0.0):
        far = set(np.where(F[:, 0] + k * F[:, 1] > t)[0].tolist())
        out = []
        while far:
            s = far.pop()
            st, comp = [s], [s]
            while st:
                v = st.pop()
                for w in adj.get(v, ()):
                    if w in far:
                        far.remove(w)
                        st.append(w)
                        comp.append(w)
            out.append(comp)
        return out
    best = None
    counts = {}
    for k in (0.0, 0.2, 0.35, 0.5, 0.7, 0.9):
        g = F[:, 0] + k * F[:, 1]
        found = None
        cs = []
        for t in np.linspace(g.max() - 0.004, g.max() - 0.09, 120):
            comps = [c for c in pieces(t, k) if len(c) >= 2]
            cs.append(len(comps))
            if len(comps) == 5:
                found = comps
            elif found is not None and len(comps) < 5:
                break
        counts[k] = max(cs)
        if found is not None:
            best = found
            break
    print("%s base foot toe search: most pieces by slope %s" % (WHO, counts))
    if best is None:
        raise RuntimeError("base foot: five toes not found")
    toes = sorted(best, key=lambda c: F[c, 1].mean())
    tips = [int(c[int(np.argmax(F[c, 0]))]) for c in toes]
    print("%s base foot: %d points, %d faces, %d triangles, ankle loop %d, toes %s" % (
        WHO, len(F), len(faces), sum(len(f) - 2 for f in faces), len(loop), [len(c) for c in toes]))
    return {"F": F, "faces": faces, "loop": loop, "toes": toes, "tips": tips}


def fit_base_foot(base, prof, height_k=1.0, bumps=True, toe_plump=(1.12, 1.75)):
    """The foot warped to a profile: prof = {"z": heights (m, rising), "front": how far the foot reaches forward of the
    ankle's axis at each height, "back": behind it, "half": its half width at each height or None (then the length's
    scale)}. First scaled whole to the length at its longest; then, height by height (smoothly), its front part to
    `front`, its heel to `back`, its width to `half`. Then the ankle bones (the inner higher and further forward) and
    a little more depth to the Achilles tendon's notch. toe_plump: the toes thickened (across, up) about their own axes. Changes base["F"]."""
    F = base["F"].copy()
    zs = np.asarray(prof["z"], float)
    fr = np.asarray(prof["front"], float)
    bk = np.asarray(prof["back"], float)
    L_sheet = float((fr + bk).max())
    L_base = float(F[:, 0].max() - F[:, 0].min())
    s = L_sheet / L_base
    F[:, :2] *= s
    if prof.get("ball_half"):
        low = F[:, 2] < 0.05
        F[:, 1] *= prof["ball_half"] / max((F[low, 1].max() - F[low, 1].min()) / 2.0, 1e-3)
    F[:, 2] *= height_k
    zt = F[:, 2].max()

    def model_ext(z, band=0.006):
        sel = np.abs(F[:, 2] - z) < band
        if sel.sum() < 3:
            return None
        return F[sel, 0].max(), -F[sel, 0].min(), (F[sel, 1].max() - F[sel, 1].min()) / 2.0
    kf, kb, kw = [], [], []
    for i, z in enumerate(zs):
        e = model_ext(min(z, zt - 0.004))
        if e is None:
            kf.append(np.nan); kb.append(np.nan); kw.append(np.nan)
            continue
        kf.append(fr[i] / max(e[0], 1e-3))
        kb.append(bk[i] / max(e[1], 1e-3))
        kw.append(prof["half"][i] / max(e[2], 1e-3) if prof.get("half") is not None and not np.isnan(prof["half"][i]) else 1.0)

    def clean(k):
        k = np.array(k, float)
        good = ~np.isnan(k)
        k = np.interp(np.arange(len(k)), np.where(good)[0], k[good])
        k = np.clip(k, 0.72, 1.4)
        for _ in range(4):
            k = np.convolve(np.pad(k, 2, mode="edge"), np.ones(5) / 5.0, mode="valid")
        return k
    kf, kb, kw = clean(kf), clean(kb), clean(kw)
    # (the forefoot is not stretched past its scale: drawn forward at the instep's height it became a slab over the
    # toes; the sheet's reach there is its thick toes, which toe_plump makes)
    kf = np.clip(kf, 0.8, 1.1)
    z = F[:, 2]
    F[:, 0] *= np.where(F[:, 0] > 0, np.interp(z, zs, kf), np.interp(z, zs, kb))
    F[:, 1] *= np.interp(z, zs, kw)
    # the toes plumped round their own axes (the length's stretch thinned them into wedges): thicker up and down
    # than across, so their gaps stay open, from nothing at the toe's root to full beyond a centimetre
    for comp in base["toes"]:
        c = np.array(comp)
        Q = F[c]
        root = Q[:, 0].min()
        mean = Q.mean(0)
        _, _, vt = np.linalg.svd(Q - mean)
        ax_ = vt[0] if vt[0][0] > 0 else -vt[0]
        rel = Q - mean
        along_ = rel @ ax_
        perp = rel - along_[:, None] * ax_[None, :]
        w = np.clip((Q[:, 0] - root) / 0.012, 0, 1)[:, None]
        grow = np.array((1.0, toe_plump[0], toe_plump[1]))
        F[c] = Q + perp * (grow - 1.0) * w
    # (the forefoot's top sloped down into the toes: the base foot steps down to them, which read as a row of teeth
    # under a slab from the front)
    root = min(F[c, 0].min() for c in base["toes"])
    ramp = smooth01(root - 0.05, root + 0.005, F[:, 0]) * smooth01(0.012, 0.03, F[:, 2])
    F[:, 2] -= (F[:, 2] - 0.012) * 0.16 * ramp
    # (the toes' undersides kept on the ground)
    F[:, 2] = np.maximum(F[:, 2], 0.0)
    if bumps:
        L = L_sheet
        # the ankle bones: the inner (v < 0) about 9 cm up and a centimetre forward, the outer lower and further back
        for side_v, zc, uc, amt in ((-1.0, 0.09 * height_k, 0.01, 0.006), (1.0, 0.075 * height_k, -0.008, 0.007)):
            w = np.exp(-((F[:, 2] - zc) / 0.018) ** 2 - ((F[:, 0] - uc) / 0.022) ** 2) * (np.sign(F[:, 1]) == side_v)
            F[:, 1] += side_v * amt * w
        # the Achilles tendon's notch: the back above the heel drawn in, the heel's round left
        w = np.exp(-((F[:, 2] - 0.095 * height_k) / 0.022) ** 2) * np.clip(-F[:, 0] / (0.2 * L), 0, 1) * np.exp(-(F[:, 1] / 0.02) ** 2)
        F[:, 0] += 0.006 * w
    base["F"] = F
    print("%s foot fitted: length %.1f cm (scale %.2f), height %.1f cm; front x %.2f..%.2f, heel x %.2f..%.2f, width x %.2f..%.2f" % (
        WHO, L_sheet * 100, s, F[:, 2].max() * 100, kf.min(), kf.max(), kb.min(), kb.max(), kw.min(), kw.max()))
    return base


def shape_foot(base):
    """Sixth round (the critic: "a sawtooth row of boxes with pinched points, the big toe barely separate, a flat slab
    with no arch or heel"). On the fitted foot (u forward, v outward, z up):
    - each toe's end clipped to a half ellipsoid round its own axis (its square cap's corners pulled in: a round tip);
    - the big toe broader across, the others a little narrower so the gaps between them stay open;
    - the inner arch: the sole's inner half lifted between the heel and the ball;
    - the heel rounded out behind the ankle. Changes base["F"]."""
    F = base["F"].copy()
    toes = base["toes"]
    for i, comp in enumerate(toes):
        c = np.array(comp)
        Q = F[c]
        mean = Q.mean(0)
        # (the toe's axis is the foot's forward line, not the toe's longest spread: the small toes are wider than long,
        # so their principal axis ran across the foot and the tips were never rounded)
        d = np.array((1.0, 0.0, 0.0))
        b = np.array((0.0, 0.0, 1.0)) - d * d[2]
        b /= np.linalg.norm(b)
        a = np.cross(b, d)
        rel = Q - mean
        s, ra, rb = rel @ d, rel @ a, rel @ b
        # across: the big toe broader, the small ones a little narrower, from their roots on
        root = s.min()
        w = smooth01(root, root + 0.012, s)
        ra = ra * (1.0 + (TOE_BIG if i == 0 else -0.06) * w)
        s_tip = float(s.max())
        band = (s > s_tip - 0.016) & (s < s_tip - 0.006)
        if band.sum() >= 4:
            ca, cb = float(ra[band].mean()), float(rb[band].mean())
            Ra = max(float(np.abs(ra[band] - ca).max()), 1e-3)
            Rb = max(float(np.abs(rb[band] - cb).max()), 1e-3)
            La = min(Ra, Rb) * 1.1
            s0 = s_tip - La
            q = np.stack([np.clip(s - s0, 0, None) / La, (ra - ca) / Ra, (rb - cb) / Rb], 1)
            r = np.linalg.norm(q, axis=1)
            k = np.where((s > s0) & (r > 1.0), 1.0 / np.maximum(r, 1e-9), 1.0)
            s = np.where(s > s0, s0 + (s - s0) * k, s)
            ra = np.where(s > s0, ca + (ra - ca) * k, ra)
            rb = np.where(s > s0, cb + (rb - cb) * k, rb)
        F[c] = mean + s[:, None] * d + ra[:, None] * a + rb[:, None] * b
    u, v, z = F[:, 0], F[:, 1], F[:, 2]
    L = float(u.max() - u.min())
    heel = u.min()
    # the arch: under the inner half, from behind the ball to the heel's front
    t = (u - heel) / L
    arch = np.clip(np.sin(np.clip((t - 0.2) / 0.45, 0, 1) * math.pi), 0, 1) * np.clip(-v / 0.03, 0, 1) * (1.0 - smooth01(0.01, 0.035, z))
    F[:, 2] += ARCH * arch
    # the heel: round, out behind the ankle, most at a third of the heel's height
    hw = np.exp(-((z - 0.03) / 0.025) ** 2) * np.clip((heel + 0.05 - u) / 0.05, 0, 1)
    F[:, 0] -= HEEL_OUT * hw
    F[:, 2] = np.maximum(F[:, 2], 0.0)
    print("%s FOOT shaped: round toe tips, the big toe %d%% broader, arch %.0f mm, heel %.0f mm out" % (
        WHO, int(TOE_BIG * 100), ARCH * 1000, HEEL_OUT * 1000))
    base["F"] = F
    return base


TOE_REFINE = (0.034, 3, 0.5)     # refine_toes: the toes' zone (metres behind the tips), smoothing rounds, strength
FOOT_KEEP_TRIS = 400             # refine_toes: the refined foot collapsed back to about this many triangles
FOOT_BLEND = 0.045               # place_base_foot: metres down from the foot's top drawn to the shin's last ring


def refine_toes(base):
    """Seventh round, from the captain's build (the critic: "a sawtooth row of boxes"; shape_foot's rounding found
    too few points in its band on toes of 4 to 10 points, so it did nothing): the faces touching the toes split once
    on a smooth surface (bmesh subdivide, smooth), that zone relaxed (Taubin), the soles kept on the ground, the
    tips found again; then the whole foot collapsed back to FOOT_KEEP_TRIS. Changes base in place."""
    import bmesh
    F, faces = base["F"], base["faces"]
    tips0 = F[base["tips"]].copy()
    tip_u = float(F[base["tips"], 0].min())
    bm = bmesh.new()
    vs = [bm.verts.new(tuple(map(float, p))) for p in F]
    for f in faces:
        bm.faces.new([vs[i] for i in f])
    bm.verts.index_update()
    bm.verts.ensure_lookup_table()
    zone = tip_u - TOE_REFINE[0]
    toe_set = {v for c in base["toes"] for v in c}
    edges = {e for f in bm.faces if any(v.index in toe_set for v in f.verts) for e in f.edges}
    bmesh.ops.subdivide_edges(bm, edges=list(edges), cuts=1, smooth=1.0, use_grid_fill=True, use_smooth_even=True)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4], quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.verts.index_update()
    P = np.array([tuple(v.co) for v in bm.verts], float)
    nf = [[v.index for v in f.verts] for f in bm.faces]
    nf = [g for f in nf for g in ([f] if len(f) <= 4 else [[f[0], f[i], f[i + 1]] for i in range(1, len(f) - 1)])]
    bm.free()
    E = set()
    for f in nf:
        for i in range(len(f)):
            a, b = f[i], f[(i + 1) % len(f)]
            E.add((min(a, b), max(a, b)))
    E = np.array(sorted(E))
    deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
    w = np.clip((P[:, 0] - zone) / 0.015, 0, 1) * TOE_REFINE[2]
    for _ in range(TOE_REFINE[1]):
        for k in (1.0, -1.04):
            acc = np.zeros_like(P)
            np.add.at(acc, E[:, 0], P[E[:, 1]])
            np.add.at(acc, E[:, 1], P[E[:, 0]])
            avg = acc / np.maximum(deg, 1)[:, None]
            P += (avg - P) * (w * k)[:, None]
        P[:, 2] = np.maximum(P[:, 2], 0.0)
    tips = []
    for t in tips0:
        near = np.where(np.linalg.norm(P - t, axis=1) < 0.012)[0]
        tips.append(int(near[np.argmax(P[near, 0])]) if len(near) else int(np.argmin(np.linalg.norm(P - t, axis=1))))
    print("%s toes refined: %d faces split, %d triangles a foot now" % (WHO, len(nf) - len(faces), sum(len(f) - 2 for f in nf)))
    base["F"], base["faces"], base["tips"] = P, nf, tips
    # (the toes' point lists kept for later steps: the nearest new points within each old toe's reach)
    base["toes"] = [sorted(set(np.where(np.min(np.linalg.norm(P[:, None, :] - F[c][None, :, :], axis=2), axis=1) < 0.004)[0].tolist()))
                    for c in (np.array(c) for c in base["toes"])]
    if FOOT_KEEP_TRIS:
        base = thin_foot(base, FOOT_KEEP_TRIS)
    return base


def thin_foot(base, keep):
    """(From the captain's build.) The refined foot collapsed (Blender's decimate) to about `keep` triangles, its ankle
    loop and the ring next to it held; the loop, toes and tips renumbered by the nearest new points."""
    F, faces = base["F"], base["faces"]
    n_before = sum(len(f) - 2 for f in faces)
    me = bpy.data.meshes.new("foot_thin")
    me.from_pydata([tuple(map(float, p)) for p in F], [], faces)
    me.update()
    ob = bpy.data.objects.new("foot_thin", me)
    bpy.context.scene.collection.objects.link(ob)
    held = set(base["loop"])
    for f in faces:
        if held & set(f):
            held |= set(f)
    g = ob.vertex_groups.new(name="free")
    g.add([i for i in range(len(F)) if i not in held], 1.0, "REPLACE")
    dec = ob.modifiers.new("fewer", "DECIMATE")
    dec.decimate_type = "COLLAPSE"
    dec.ratio = min(1.0, keep / max(n_before, 1))
    dec.vertex_group = "free"
    dec.use_collapse_triangulate = False
    bpy.context.view_layer.update()
    ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    m2 = ev.to_mesh()
    P = np.array([tuple(v.co) for v in m2.vertices], float)
    nf = [list(p.vertices) for p in m2.polygons]
    ev.to_mesh_clear()
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.meshes.remove(me)

    def nearest(q):
        return int(np.argmin(np.linalg.norm(P - q, axis=1)))
    loop = [nearest(F[v]) for v in base["loop"]]
    toes = [sorted({nearest(F[v]) for v in c}) for c in base["toes"]]
    tips = [nearest(F[t]) for t in base["tips"]]
    worst = max(float(np.linalg.norm(P[n] - F[v])) for n, v in zip(loop, base["loop"]))
    print("%s foot thinned: %d -> %d triangles; ankle loop held (worst %.1f mm), %d open loops" % (
        WHO, n_before, sum(len(f) - 2 for f in nf), worst * 1000, len(open_loops(nf))))
    base["F"], base["faces"], base["loop"], base["toes"], base["tips"] = P, nf, loop, toes, tips
    return base


def place_base_foot(M, base, ankle_ring, origin, fwd, lat, side, part):
    """The fitted foot put into the Mesh: origin (the ankle's axis on the ground), fwd and lat (the foot's forward
    and outward directions, already mirrored for the right foot), its ankle loop zipped to the shin's last ring.
    Before the zip (seventh round, from the captain's build) the foot's top is drawn toward the ring over FOOT_BLEND,
    to its middle and its size, so the shin runs into the foot with no ledge. Gives (point ids, base face ids, zip
    face ids)."""
    F = base["F"].copy()
    o, f_, l_ = (np.array(v, float) for v in (origin, fwd, lat))
    up = np.array((0.0, 0.0, 1.0))
    A = np.array([M.P[v] for v in ankle_ring])
    a_uv = np.stack([(A - o) @ f_, (A - o) @ l_], 1)
    a_c = a_uv.mean(0)
    a_r = float(np.linalg.norm(a_uv - a_c, axis=1).mean())
    l_c = F[base["loop"], :2].mean(0)
    l_r = float(np.linalg.norm(F[base["loop"], :2] - l_c, axis=1).mean())
    zt = float(F[base["loop"], 2].mean())
    k_top = a_r / max(l_r, 1e-4)
    wt = np.clip((F[:, 2] - (zt - FOOT_BLEND)) / FOOT_BLEND, 0.0, 1.0) ** 1.5
    for i in np.where(wt > 0)[0]:
        rel = F[i, :2] - l_c
        F[i, :2] = l_c + (a_c - l_c) * wt[i] + rel * (1.0 + (k_top * 0.96 - 1.0) * wt[i])
    print("%s foot top drawn to the ankle ring: ring %.1f cm round, foot's top %.1f cm (times %.2f)" % (WHO, a_r * 100, l_r * 100, k_top))
    ids = [M.add(o + f_ * u + l_ * v + up * z, part) for u, v, z in F]
    f0 = len(M.faces)
    for f in base["faces"]:
        M.face([ids[v] for v in f], part)
    f1 = len(M.faces)

    def ang(Q):
        return np.arctan2((Q - o) @ l_, (Q - o) @ f_)
    zipper(M, [ids[v] for v in base["loop"]], list(ankle_ring), ang, part)
    return ids, list(range(f0, f1)), list(range(f1, len(M.faces)))


def unwrap_conformal(P, faces, seams):
    """Blender's conformal unwrap of a piece of surface with the given seam edges (pairs of indices into P). Gives
    the UV of each face corner (Blender's 0..1 packing; islands are scaled to metres by the caller)."""
    me = bpy.data.meshes.new("_unwrap")
    me.from_pydata([tuple(map(float, p)) for p in P], [], [list(f) for f in faces])
    me.update()
    ob = bpy.data.objects.new("_unwrap", me)
    bpy.context.scene.collection.objects.link(ob)
    for e in me.edges:
        e.use_seam = tuple(sorted(e.vertices)) in seams
    me.uv_layers.new(name="UVMap")
    for o in list(bpy.data.objects):
        try:
            o.select_set(False)
        except Exception:
            pass
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.unwrap(method="CONFORMAL", margin=0.0)
    bpy.ops.object.mode_set(mode="OBJECT")
    uvl = me.uv_layers[0].data
    out = [[tuple(uvl[li].uv) for li in p.loop_indices] for p in me.polygons]
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.meshes.remove(me)
    return out


def foot_islands(M, faces, origin, fwd, lat, top_loop):
    """Two UV islands for a foot (its base faces and the zip to the shin): the sole (faces looking down, low), and
    the rest cut once up the back of the heel to the shin's ring (a seam where the eye seldom is). Gives {"sole":
    {face: uvs}, "upper": {...}} in metres."""
    P = np.array(M.P)
    o, f_, l_ = (np.array(v, float) for v in (origin, fwd, lat))
    used = sorted({v for fi in faces for v in M.faces[fi]})
    loc = {v: i for i, v in enumerate(used)}
    lf = [[loc[v] for v in M.faces[fi]] for fi in faces]
    Q = P[used]
    u = (Q - o) @ f_
    vv = (Q - o) @ l_
    sole = set()
    for k, fi in enumerate(faces):
        n = face_normal(P, M.faces[fi])
        n = n / max(np.linalg.norm(n), 1e-12)
        # (which way is out: the closed body's winding is set later, so judge by the face's place against the foot's
        # middle line at its height)
        c = P[M.faces[fi]].mean(0)
        if c[2] - o[2] < 0.022 and abs(n[2]) > 0.55:
            sole.add(k)
    # the sole's edge
    owner = {}
    for k, f in enumerate(lf):
        for i in range(len(f)):
            e = tuple(sorted((f[i], f[(i + 1) % len(f)])))
            owner.setdefault(e, []).append(k)
    seams = {e for e, ks in owner.items() if len(ks) == 2 and ((ks[0] in sole) != (ks[1] in sole))}
    # up the back of the heel: the cheapest path from the sole's edge to the shin's ring, kept near the middle line
    import heapq
    graph = {}
    for e in owner:
        a, b = e
        w = float(np.linalg.norm(Q[a] - Q[b])) * (1.0 + 60.0 * abs(vv[a] + vv[b]) / 2.0) * (1.0 + 4.0 * float(u[a] + u[b] > 0))
        graph.setdefault(a, []).append((w, b))
        graph.setdefault(b, []).append((w, a))
    edge_pts = {v for e in seams for v in e}
    start = min(edge_pts, key=lambda v: u[v] - 0.0 * abs(vv[v]))
    goal = {loc[v] for v in top_loop if v in loc}
    dist, prev, pq = {start: 0.0}, {}, [(0.0, start)]
    end = None
    while pq:
        d, a = heapq.heappop(pq)
        if a in goal:
            end = a
            break
        if d > dist.get(a, 1e9):
            continue
        for w, b in graph[a]:
            if d + w < dist.get(b, 1e9):
                dist[b] = d + w
                prev[b] = a
                heapq.heappush(pq, (d + w, b))
    v = end
    while v is not None and v in prev:
        seams.add(tuple(sorted((v, prev[v]))))
        v = prev[v]
    uvs = unwrap_conformal(Q, lf, seams)
    out = {"sole": {}, "upper": {}}
    for k, fi in enumerate(faces):
        out["sole" if k in sole else "upper"][fi] = uvs[k]
    for name, isl in out.items():
        a3 = auv = 0.0
        for fi, uv in isl.items():
            a3 += float(np.linalg.norm(face_normal(P, M.faces[fi]))) / 2.0
            q = np.array(uv)
            auv += abs(float(np.sum(q[:, 0] * np.roll(q[:, 1], -1) - np.roll(q[:, 0], -1) * q[:, 1]))) / 2.0
        k = math.sqrt(a3 / max(auv, 1e-12))
        out[name] = {fi: [(a * k, b * k) for a, b in uv] for fi, uv in isl.items()}
    return out


def paint_feet(rgb, pos, nrm, hit, mine, frame, toes, base_c, keep=0.25, shin=None, ring_z=0.16, fade=0.08):
    """A foot's skin: the shin's tone (base_c) with `keep` of what the sheet projected (its small changes), the gaps
    between the toes and the toes' undersides in soft shade, the toe tips and heel a little rosier, a pale toenail on
    each toe's last joint with a darker rim. frame = (origin, fwd, lat); toes = [(tip point, nail radius)], big toe
    first."""
    o, f_, l_ = (np.array(v, float) for v in frame)
    up = np.array((0.0, 0.0, 1.0))
    soft = blur(rgb, 4)
    d = pos - o
    u = (d * f_).sum(-1)
    h = d[..., 2]
    # (up toward the shin the sheet's own paint (its hair, its tone) is kept more and more, so no edge shows where the
    # foot's island meets the leg's)
    # (the foot takes the tone whole; the shin's last `fade` metres above the ring where the two islands meet (shin: its
    # texels) go over to it by degrees, so the seam has the same colour on both sides and the hair thins out)
    k_ = keep + (1.0 - keep) * smooth01(ring_z, ring_z + fade, h)
    both = mine | (shin if shin is not None else np.zeros_like(mine)) & (h < ring_z + fade)
    rgb[both] = base_c * (1 - k_[both])[:, None] + soft[both] * k_[both][:, None]
    nu = (nrm * f_).sum(-1)
    nl = np.abs((nrm * l_).sum(-1))
    nz = nrm[..., 2]
    tip_u = min(float(np.dot(np.array(t, float) - o, f_)) for t, _ in toes)
    root_u = tip_u - 0.05
    # rosier, by soft degrees: the toes' ends, the heel's back
    r_ = np.maximum(smooth01(root_u - 0.02, root_u + 0.02, u), smooth01(-0.02, -0.06, u))[mine][:, None]
    rgb[mine] *= 1.0 + r_ * (np.array((1.03, 0.965, 0.95)) - 1.0)
    # the sole a little paler and yellower
    sole = mine & (nz < -0.5) & (h < 0.02)
    rgb[sole] *= np.array((1.04, 1.0, 0.94))
    # the gaps between the toes, and under them, in shade
    # (soft: by how far past the toes' roots and how sideways the surface looks; a hard mask drew square patches)
    gw = (smooth01(root_u, root_u + 0.015, u) * smooth01(0.45, 0.8, nl) * (1.0 - smooth01(0.025, 0.04, h)))[mine]
    rgb[mine] *= (1.0 - 0.15 * gw)[:, None]
    under = mine & (u > root_u) & (nz < -0.2) & (h > 0.004)
    rgb[under] *= 0.9
    # the toe creases on top, where each toe leaves the foot
    for i, (t, r) in enumerate(toes):
        t = np.array(t, float)
        c = t - f_ * (r * 0.9) + up * (r * 0.55)
        dd = pos - c
        along_ = (dd * f_).sum(-1)
        across = (dd * l_).sum(-1)
        e = (along_ / (r * 1.15)) ** 2 + (across / r) ** 2
        nail = mine & (e < 1.0) & ((nz > 0.25) | (nu > 0.5)) & (dd[..., 2] > -r * 0.6)
        rgb[nail] = rgb[nail] * 0.45 + np.array((0.9, 0.74, 0.68)) * 0.55
        rim = nail & (e > 0.62)
        rgb[rim] *= 0.84
    return rgb



# ------------------------------------------------------------------------------------------------------------------
# The head, measured off the head sheet's bald row (concept_brother_head2.jpg): each ring's width from the front
# view's outline (where the ears hide the skull's side, between the rows above and below them) and its front and back
# from the side view's (where the nose stands out, the face's front taken straight under it: the nose is its own
# shell). Then fitted to all five views' outlines (fit_head_round), the angled views' own angle and middle found by
# fitting (align_head_views).
# ------------------------------------------------------------------------------------------------------------------

# The head's rings (head-sheet rows), from the chin's underside up over the bald skull; the crown's point at
# HEAD_CROWN. Closer together where the face has its forms.
HEAD_RING_ROWS = [1244, 1228, 1212, 1196, 1180, 1166, 1152, 1140, 1128, 1116, 1102, 1088, 1074, 1060, 1046, 1033,
                  1020, 1006, 992, 978, 962, 944, 924, 904, 884, 868, 857, 850]
EAR_ROWS = (1016, 1124)       # the ear's top and bottom (the side view)
EAR_COLS = (1411, 1345)       # its front and back in the side view
EAR_OUT = 0.021               # how far its rim stands out from the head (it lies close)
EAR_LOBE = (1385.0, 1124.0)   # the lobe's lowest point in the side view (column, row)
EAR_HIDES = (1008, 1142)      # rows where the front view's outline is the ears, not the skull
FACE_PLANE = (1040, 1124)     # rows where the side view's front is the nose
# The nose (the user's "big round ball nose"): its width in the front view (pixels) by row: a narrow bridge from
# between the eyes, the ball, the wings flaring at its base.
NOSE = ((1042, 34.0), (1056, 38.0), (1068, 52.0), (1080, 70.0), (1092, 82.0), (1102, 86.0), (1110, 84.0),
        (1117, 74.0), (1122, 60.0), (1126, 38.0))
NOSE_WINGS = ((1090, 0.0), (1102, 0.12), (1112, 0.2), (1122, 0.15))


def head_measure(sh, rows=None):
    m = sh.head_mask
    _, fmid, (f0, f1) = HEAD_VIEWS["front"]
    _, smid, (s0, s1) = HEAD_VIEWS["side"]

    def half(r):
        run = run_near(m, r, fmid, f0, f1)
        return (run[1] + 1 - run[0]) / 2.0
    ha, hb = half(EAR_HIDES[0]), half(EAR_HIDES[1])
    ra = run_near(m, FACE_PLANE[0], smid, s0, s1)
    rb = run_near(m, FACE_PLANE[1] + 2, smid, s0, s1)
    fa = -(ra[1] + 1 - smid) * HEAD_SX
    fb = -(rb[1] + 1 - smid) * HEAD_SX + 0.004
    rings = []
    for r in (rows or HEAD_RING_ROWS):
        if EAR_HIDES[0] < r < EAR_HIDES[1]:
            t = (r - EAR_HIDES[0]) / (EAR_HIDES[1] - EAR_HIDES[0])
            hw = ha + (hb - ha) * t + 3.0 * math.sin(math.pi * t)      # (the cheeks' fullness under the ears)
        else:
            hw = half(r)
        run = run_near(m, r, smid, s0, s1)
        yf = -(run[1] + 1 - smid) * HEAD_SX
        yb = -(run[0] - smid) * HEAD_SX
        if FACE_PLANE[0] <= r <= FACE_PLANE[1]:
            t = (r - FACE_PLANE[0]) / (FACE_PLANE[1] - FACE_PLANE[0])
            yf = fa + (fb - fa) * t
        rings.append((float(head_z(r)), hw * HEAD_SX, yf, yb, 0.0))
    return rings


def build_head(M, sh, top_ring):
    """The head's rings bridged onto the torso's top ring, up the face and over the skull to the crown; then the nose
    and ears as shells of their own."""
    rings = head_measure(sh)
    prev = top_ring
    H = []
    for i, (z, hw, yf, yb, taper) in enumerate(rings):
        # (each ring's middle where the head is widest front to back: about 45% of its depth from the back)
        cy = yb - (yb - yf) * 0.55
        pts = ring_points(0.0, cy, z, hw, cy - yf, yb - cy, TORSO_N, 0.9)
        ring = [M.add(q, "head") for q in pts]
        for k in range(TORSO_N):
            j = (k + 1) % TORSO_N
            M.face([prev[k], prev[j], ring[j], ring[k]], "head" if i else "neck")
            M.cell[len(M.faces) - 1] = ("head", i - 1, k)
        prev = ring
        H.append(ring)
    crown_y = float(np.mean([M.P[v][1] for v in prev]))
    top = M.add((0.0, crown_y, float(head_z(HEAD_CROWN - 3.0))), "head")
    for k in range(TORSO_N):
        j = (k + 1) % TORSO_N
        M.face([prev[k], prev[j], top], "head")
        M.cell[len(M.faces) - 1] = ("head", len(rings) - 1, k)
    M.tag["head_rings"] = H
    return rings


def head_features(M, sh):
    """The nose and the ears, built after the head is fitted, on the head as it stands."""
    H = M.tag["head_rings"]
    rings = []
    for ring in H:
        P = np.array([M.P[v] for v in ring])
        rings.append((float(P[:, 2].mean()), float(np.abs(P[:, 0]).max()), float(P[0, 1]), float(P[:, 1].max()), 0.0))
    nose(M, sh, rings)
    for side in (1, -1):
        ear(M, sh, rings, side)


def face_front_at(rings, z):
    zs = [r[0] for r in rings]
    ys = [r[2] for r in rings]
    return float(np.interp(z, zs, ys))


def nose(M, sh, rings):
    """The ball nose: lofted down the side view's profile, as wide as the front view paints it at each row, each
    loop an egg from the face to the tip, closed under the nostrils."""
    m = sh.head_mask
    _, smid, (c0, c1) = HEAD_VIEWS["side"]
    rows = list(range(NOSE[0][0], NOSE[-1][0] + 1, 4))
    if rows[-1] != NOSE[-1][0]:
        rows.append(NOSE[-1][0])
    loops = []
    n = 12
    for r in rows:
        run = run_near(m, r, smid, c0, c1)
        tip = -(run[1] + 1 - smid) * HEAD_SX
        z = float(head_z(r))
        base = face_front_at(rings, z) + 0.012
        half = float(np.interp(r, [a for a, _ in NOSE], [w for _, w in NOSE])) / 2.0 * HEAD_SX
        wings = float(np.interp(r, [a for a, _ in NOSE_WINGS], [w for _, w in NOSE_WINGS]))
        cy, d = (tip + base) / 2.0, max((base - tip) / 2.0, 0.003)
        pts = ring_points(0.0, cy, z, half, d, d, n, 1.0)
        pts = [(x * (1.0 + wings * float(np.clip((y - cy) / d + 0.3, 0.0, 1.0))), y, zz) for x, y, zz in pts]
        loops.append([M.add(q, "nose") for q in pts])
    for a, b in zip(loops, loops[1:]):
        M.bridge(a, b, "nose")
    last = loops[-1]
    zc = M.P[last[0]][2] - 0.003
    c = M.add((0.0, float(np.mean([M.P[i][1] for i in last])), zc), "nose")
    for j in range(n):
        k = (j + 1) % n
        M.face([last[j], last[k], c], "nose")
    first = loops[0]
    c = M.add((0.0, float(np.mean([M.P[i][1] for i in first])) + 0.004, M.P[first[0]][2] + 0.005), "nose")
    for j in range(n):
        k = (j + 1) % n
        M.face([first[k], first[j], c], "nose")


# An ear's outline as the side view draws it (b: back from where it joins the head, v: up), how far each point stands
# out (0..1): the helix round the top and back, the lobe at the bottom, the tragus at the front.
EAR_RIM = ((0.18, 0.97, 0.55), (0.42, 1.0, 0.85), (0.66, 0.93, 1.0), (0.86, 0.78, 1.0), (0.96, 0.58, 0.95),
           (0.92, 0.38, 0.85), (0.78, 0.2, 0.7), (0.6, 0.06, 0.6), (0.4, -0.02, 0.5), (0.22, 0.04, 0.35),
           (0.08, 0.22, 0.15), (0.02, 0.45, 0.1), (0.04, 0.7, 0.2), (0.08, 0.88, 0.35))


def ear(M, sh, rings, side):
    """An ear lying close to the head: the helix as a rolled rim (an outer and an inner edge), the bowl (concha)
    inside it, a back wall into the skull."""
    part = "ear_l" if side > 0 else "ear_r"
    zt, zb = float(head_z(EAR_ROWS[0])), float(head_z(EAR_ROWS[1]))
    y0 = -(EAR_COLS[0] - HEAD_VIEWS["side"][1]) * HEAD_SX
    y1 = -(EAR_COLS[1] - HEAD_VIEWS["side"][1]) * HEAD_SX
    zc = (zt + zb) / 2.0
    zs = [r[0] for r in rings]
    hw = float(np.interp(zc, zs, [r[1] for r in rings]))
    hgt, wid = zt - zb, y1 - y0
    tilt = math.radians(12.0)
    rim, lip, bowl, wall = [], [], [], []
    ctr = (0.45, 0.5)
    for b, v, out in EAR_RIM:
        yy = y0 + b * wid + (v - 0.5) * hgt * math.sin(tilt)
        zz = zb + v * hgt
        x = hw - 0.006 + EAR_OUT * out
        rim.append(M.add(mirror_x((x, yy, zz), side), part))
        # the helix's inner edge: a little in from the rim toward the bowl's middle, and standing a little less
        bi, vi = ctr[0] + (b - ctr[0]) * 0.8, ctr[1] + (v - ctr[1]) * 0.8
        lip.append(M.add(mirror_x((x - 0.002, y0 + bi * wid + (vi - 0.5) * hgt * math.sin(tilt), zb + vi * hgt), side), part))
        bb, vb = ctr[0] + (b - ctr[0]) * 0.5, ctr[1] + (v - ctr[1]) * 0.5
        bowl.append(M.add(mirror_x((hw - 0.006 + EAR_OUT * out * 0.3, y0 + bb * wid + (vb - 0.5) * hgt * math.sin(tilt) * 0.5, zb + vb * hgt), side), part))
        wall.append(M.add(mirror_x((hw - 0.02, y0 + b * wid * 0.8, zb + (0.5 + (v - 0.5) * 0.9) * hgt), side), part))
    centre = M.add(mirror_x((hw - 0.004, y0 + ctr[0] * wid, zb + 0.42 * hgt), side), part)
    n = len(EAR_RIM)
    out = np.array((side, 0.0, 0.0))
    mid_ = np.array(M.P[centre])

    def away(c, mid_=mid_, side=side):
        d = np.array(c) - mid_
        d[0] = 0.0
        return d + np.array((side * 0.15, 0.0, 0.0)) * np.linalg.norm(d)
    for j in range(n):
        k = (j + 1) % n
        M.face([rim[j], rim[k], lip[k], lip[j]], part, out)
        M.face([lip[j], lip[k], bowl[k], bowl[j]], part, out)
        M.face([bowl[j], bowl[k], centre], part, out)
        M.face([rim[k], rim[j], wall[j], wall[k]], part, away)


# ------------------------------------------------------------------------------------------------------------------
# Third build (2026-11-18, tools/FIGURE_HEADS.md; the user: "The heads and hands need a lot of work on all three- make
# sure you are matching pose silhouettes aggressively"): his head (with its ears) and his hands are no longer lofted
# (build_head, nose, ear and hand above are kept, unused). Each starts from Blender Studio's Human Base Meshes v1.4.1
# (CC0; the bundle stays outside the repo, appended from by script, never edited): the head from `Head - Generic
# Topology` at a mix of its Real_MALE and Toon_MALE shape keys, the hand from `Hand - Stylized` un-subdivided twice.
# The head is placed and scaled by landmarks, its face's heights warped to the bald side view's (chin, mouth, nose
# tip, the bridge's dip, brow), its ears moved to where the side view has them, its nose widened to the front view's
# ball, then pulled to the five bald views' outlines round by round (outline points moved, the rest following
# smoothly, kept symmetrical, folded faces counted after every step); its open neck bridged to the torso's top ring.
# ------------------------------------------------------------------------------------------------------------------

BASE_BUNDLE = (r"C:\Projects\reference\human-base-meshes\bundle\human-base-meshes-bundle-v1.4.1"
               r"\human_base_meshes_bundle.blend")
HEAD_MIX = {"Real_MALE": 0.3, "Toon_MALE": 0.7}
HAND_UNSUBDIV = int(arg("--unsub", "0"))
# (ninth round: un-subdivided twice the fingers are four points round, square pegs with a four-point cap that the
# tip domes pulled to a spike; un-subdivided once the result is irregular (saw-toothed fingers). So the full base hand
# is collapsed (Decimate COLLAPSE) to 40%: about 650 triangles a hand, fingers round and smooth)
HAND_COLLAPSE = float(arg("--collapse", "0.34"))   # (tenth round: 0.4 -> 0.34, the brief's budget of about 1,150 for both hands)
# The base head's own landmarks on its middle line (the bundle's coordinates, y and z, at HEAD_MIX), read off it.
HEAD_BASE_MARKS = {"chin_bottom": (-0.141, -0.039), "chin": (-0.148, -0.027), "mouth": (-0.149, 0.006),
                   "tip": (-0.166, 0.035), "nasion": (-0.143, 0.073), "brow": (-0.148, 0.094)}
HEAD_FIT_PASSES = int(arg("--headrounds", "10"))
HEAD_SPLIT_BACK = float(arg("--splitback", "0.05"))   # metres in front of the head's middle (front to back) where the refine stops (a figure's "consts" may set it)


# Eleventh round (2026-11-18): THE FRESH HEAD (the figure's "head_route": "fresh"; `-- --head-route old` brings back
# the tenth round's). Ten rounds of nudging a cage-density head left a faceted crown, fin ears, slot eyes and a cut
# mouth. Now the base head is mixed for a broad young face (HEAD_MIX_FRESH, picked from grey renders of six mixes,
# scratchpad brother11/mixes.png), Catmull-Clark subdivided ONCE before anything else (316 quads -> about 1,260: the
# whole head, crown and back included, at one even density that can carry eyes and a nose; the cage's points keep
# their numbers, so the mouth loop and the marks hold), then placed and fitted to the shaved sheet as before; the
# later steps that bent a thin head wide (youth_head's widening, square_jaw, the nose shortened) are off for it.
HEAD_MIX_FRESH = {"Toon_MALE": 0.5, "Real_Kid": 0.3, "Real_MALE": 0.2}
HEAD_ROUTE = "old"
BASE_REF = {}
HEAD_DIFFUSE = 25      # base_head_round: rounds the outline's moves are spread over the head (more on a denser head)
NOSE_GAIN_MAX = 2.2    # base_head 6: the most the nose is widened by
FACE_EASE = None       # fresh_face_ease: (rows, |columns|, Taubin rounds) of the lower face evened (None: none)
FACE_ROSE = (0.55, 0.45)   # rule_face: the cheeks' and the nose's flush
LASH = 1.0             # rule_face: the lash line's thickness
BROW_ROW = (21.0, 6.5, 6.0)   # rule_face: the brows' middle line: px over the eye's top, the arch, the outer end's fall
MOUTH_WIDEN = 1.0      # snap_mouth_line: the mouth's corners moved out this much (its loop and the skin round it)
JAW_LINE = 0.0         # fresh_jaw_line: metres the jaw's underside is drawn up under its edge
BROW_PAINT = (5.0, 3.0, 0.72, (0.32, 0.21, 0.14))   # rule_face: the brows' half thickness inside and outside (px), cover, colour
HEAD_FIT_VIEWS = ("front", "q", "side", "qb", "back")   # the views the outline fit pulls to after its first rounds
# The fresh route's own values over the figure's (apply_figure). The face's forms in head2-frame rows (EYE_TOP 1035,
# the iris's middle 1048, the nose's wings 1124, the mouth 1168, the chin 1250) and columns out from the middle:
# (row, column, spread up/down, spread across, metres along the normal).
FRESH_CONSTS = {
    "HEAD_WIDEN": (), "JAW_WIDEN": 0.0, "CHIN_BROAD": (0.0, 0.0), "NOSE_SHORT": 0.0, "DOME_FROM": 0.0,
    "CROWN_ROUND": (0, 1.86), "HEAD_DIFFUSE": 60, "HEAD_FIT_VIEWS": ("front", "side", "back"), "NOSE_GAIN_MAX": 1.6,
    "FACE_EASE": ((1092.0, 1236.0), (34.0, 130.0), 8), "LID_CREASE": 0.0007,
    "BROW_PAINT": (8.5, 4.0, 0.85, (0.25, 0.16, 0.1)),
    "BASE_FACE_FORMS": (
        (1100, 84, 22, 28, 0.008),     # the cheeks' apples, full and round
        (985, 125, 18, 14, 0.001),     # the temples full
        (1012, 52, 7, 24, 0.0035),     # the brow's ridge, under the brows
        (1012, 0, 8, 10, 0.0012),      # between the brows (the ridge carried across, a little less)
        (1158, 0, 5, 24, 0.0014),      # the upper lip's volume
        (1179, 0, 5, 22, 0.0030),      # the soft full lower lip
        (1196, 0, 4, 20, -0.0012),     # the dip under the lower lip
        (1224, 0, 12, 30, 0.0022),     # the chin's broad pad
        (1110, 0, 9, 15, 0.0030),      # the nose's heavy round tip
    ),
    "SMILE_DEPTH": -0.0009,
}


def catmull_clark(P, faces, uvs):
    """One Catmull-Clark step (open edges by the boundary rules). The old points keep their numbers; then one point a
    face, then one an edge. UVs per face corner are carried by the same rules without smoothing (bilinear)."""
    P = np.asarray(P, float)
    n = len(P)
    nf = len(faces)
    fp = np.array([P[f].mean(0) for f in faces])
    edges = {}
    for fi, f in enumerate(faces):
        for i in range(len(f)):
            e = (min(f[i], f[(i + 1) % len(f)]), max(f[i], f[(i + 1) % len(f)]))
            edges.setdefault(e, []).append(fi)
    elist = list(edges)
    eidx = {e: n + nf + k for k, e in enumerate(elist)}
    ep = np.zeros((len(elist), 3))
    bnd_nb = {}
    for k, e in enumerate(elist):
        fs = edges[e]
        if len(fs) == 2:
            ep[k] = (P[e[0]] + P[e[1]] + fp[fs[0]] + fp[fs[1]]) / 4.0
        else:
            ep[k] = (P[e[0]] + P[e[1]]) / 2.0
            bnd_nb.setdefault(e[0], []).append(e[1])
            bnd_nb.setdefault(e[1], []).append(e[0])
    vf = [[] for _ in range(n)]
    for fi, f in enumerate(faces):
        for v in f:
            vf[v].append(fi)
    ve = [[] for _ in range(n)]
    for e in elist:
        ve[e[0]].append(e)
        ve[e[1]].append(e)
    V = P.copy()
    for v in range(n):
        if v in bnd_nb:
            a, b = bnd_nb[v][0], bnd_nb[v][-1]
            V[v] = (6 * P[v] + P[a] + P[b]) / 8.0
        elif vf[v]:
            k = len(vf[v])
            F = fp[vf[v]].mean(0)
            R = np.mean([(P[e[0]] + P[e[1]]) / 2.0 for e in ve[v]], axis=0)
            V[v] = (F + 2 * R + (k - 3) * P[v]) / k
    out_P = np.concatenate([V, fp, ep])
    out_f, out_uv = [], []
    for fi, f in enumerate(faces):
        m = len(f)
        uv = [np.array(q, float) for q in uvs[fi]]
        cuv = sum(uv) / m
        for i in range(m):
            a, b, c = f[(i - 1) % m], f[i], f[(i + 1) % m]
            e1 = eidx[(min(a, b), max(a, b))]
            e2 = eidx[(min(b, c), max(b, c))]
            out_f.append([b, e2, n + fi, e1])
            out_uv.append([tuple(uv[i]), tuple((uv[i] + uv[(i + 1) % m]) / 2), tuple(cuv), tuple((uv[(i - 1) % m] + uv[i]) / 2)])
    return out_P, out_f, out_uv


def load_base(kind):
    """A base mesh appended from the bundle: (points in its own frame, faces, UVs per face corner, its place)."""
    key = {"head": "Head-GenericTopology", "hand": "Hand-Stylized"}[kind]
    with bpy.data.libraries.load(BASE_BUNDLE, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n.replace(" ", "") == key]
    o = dst.objects[0]
    bpy.context.scene.collection.objects.link(o)
    o.modifiers.clear()
    if o.data.shape_keys:
        for k in o.data.shape_keys.key_blocks:
            k.value = float(HEAD_MIX.get(k.name, 0.0)) if kind == "head" else 0.0
    if kind == "hand":
        m = o.modifiers.new("un", "DECIMATE")
        m.decimate_type = "UNSUBDIV"
        m.iterations = HAND_UNSUBDIV
        if HAND_COLLAPSE:
            m2 = o.modifiers.new("co", "DECIMATE")
            m2.decimate_type = "COLLAPSE"
            m2.ratio = HAND_COLLAPSE
            m2.use_symmetry = False
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = o.evaluated_get(dg)
    me = ev.to_mesh()
    loc = np.array(o.location, float)
    P = np.array([tuple(v.co) for v in me.vertices], float)
    if kind == "head":
        # (the shape keys mixed by sum from their own points: the evaluated mesh did not take the values set above,
        # the bundle shows its active key alone)
        kb = o.data.shape_keys.key_blocks
        base_k = np.array([tuple(p.co) for p in kb["Basis"].data], float)
        P = base_k.copy()
        for name, wgt in HEAD_MIX.items():
            P += wgt * (np.array([tuple(p.co) for p in kb[name].data], float) - base_k)
        if HEAD_ROUTE == "fresh":
            # (the marks are found on the old mix by place (HEAD_BASE_MARKS were read off it), then read by number
            # on the fresh mix)
            BASE_REF["P"] = P.copy()
            P = base_k.copy()
            for name, wgt in HEAD_MIX_FRESH.items():
                P += wgt * (np.array([tuple(p.co) for p in kb[name].data], float) - base_k)
    faces = [list(p.vertices) for p in me.polygons]
    uvl = me.uv_layers[0].data
    uvs = [[tuple(uvl[li].uv) for li in p.loop_indices] for p in me.polygons]
    ev.to_mesh_clear()
    bpy.data.objects.remove(o, do_unlink=True)
    print("BROTHER base %s: %d points, %d faces, %d triangles" % (kind, len(P), len(faces), sum(len(f) - 2 for f in faces)))
    return P, faces, uvs, loc


def open_loops(faces):
    """The open edges of a surface as loops of point indices, in order."""
    nxt = {}
    for a, b in open_edges(faces):
        nxt.setdefault(a, []).append(b)
        nxt.setdefault(b, []).append(a)
    loops, seen = [], set()
    for s in nxt:
        if s in seen:
            continue
        loop, prev, cur = [s], None, s
        seen.add(s)
        while True:
            cand = [w for w in nxt[cur] if w != prev and w not in seen]
            if not cand:
                break
            prev, cur = cur, cand[0]
            loop.append(cur)
            seen.add(cur)
        loops.append(loop)
    return loops


def zipper(M, A, B, angle, part, order=None):
    """Triangles between two closed loops of different counts: both put in order of `angle` (a function of points
    giving angles round a common axis) and merged. Their winding is set later with the rest of the body."""
    P = np.array(M.P)
    if order is not None:
        # (the loops already in order, with their own increasing parameters round)
        a, b = np.asarray(order[0], float), np.asarray(order[1], float)
    else:
        out = []
        for loop in (A, B):
            a = np.mod(angle(P[loop]), math.tau)
            o = np.argsort(a)
            out.append(([loop[i] for i in o], a[o]))
        (A, a), (B, b) = out
    na, nb = len(A), len(B)
    ae = np.append(a, a[0] + math.tau)
    be = np.append(b, b[0] + math.tau)
    i = j = 0
    while i < na or j < nb:
        if j >= nb or (i < na and ae[i + 1] <= be[j + 1]):
            M.face([A[i % na], A[(i + 1) % na], B[j % nb]], part)
            i += 1
        else:
            M.face([A[i % na], B[(j + 1) % nb], B[j % nb]], part)
            j += 1


def loop_at_angles(P, loop, angle, targets):
    """Points on a closed loop (by straight pieces) at given angles round an axis."""
    Q = P[loop]
    a = np.mod(angle(Q), math.tau)
    o = np.argsort(a)
    Q, a = Q[o], a[o]
    Qe = np.concatenate([Q[-1:], Q, Q[:1]])
    ae = np.concatenate([[a[-1] - math.tau], a, [a[0] + math.tau]])
    t = np.mod(targets, math.tau)
    t = np.where(t < ae[0], t + math.tau, t)
    return np.stack([np.interp(t, ae, Qe[:, k]) for k in range(3)], 1)


# The rows of the bald side view searched for the brow's, the nose tip's and the chin's most forward points and the
# skull's back (a figure's own head sheet overrides them: FIGURES "head" "marks").
HEAD_PROFILE_ROWS = {"brow": (975, 1015), "tip": (1050, 1115), "chin": (1185, 1238), "back": (880, 1060),
                     "lips": (1130, 1165)}
# head_landmarks' front-view width rows: the ears, the jaw at its angle, the jaw by the chin
HEAD_WIDTH_ROWS = (1060, 1176, 1225)


def sheet_head_marks(sh):
    """The bald row's landmarks as model (y, z): the side view's profile (brow, the bridge's dip, nose tip, mouth,
    chin, chin's underside, the back of the skull) and the front view's skull half width above the ears."""
    side = head_target(sh, "side")
    _, smid, _ = HEAD_VIEWS["side"]

    def y_of(c):
        return float(-(c - smid) * HEAD_SX)

    def front_col(r):
        cols = np.where(side[r])[0]
        return int(cols.max()) + 1 if len(cols) else None

    def fwd(r0, r1):
        best = max(((front_col(r), r) for r in range(r0, r1) if front_col(r) is not None))
        return best
    out = {}
    top = int(np.where(side.any(1))[0].min())
    out["crown"] = (None, float(head_z(top)))
    cb, rb = fwd(*HEAD_PROFILE_ROWS["brow"])
    ct, rt = fwd(*HEAD_PROFILE_ROWS["tip"])
    cn, rn = min(((front_col(r), r) for r in range(rb + 3, rt - 15)))
    out["brow"] = (y_of(cb), float(head_z(rb)))
    out["tip"] = (y_of(ct), float(head_z(rt)))
    out["nasion"] = (y_of(cn), float(head_z(rn)))
    out["mouth"] = (y_of(front_col(int(SMILE[0]))), float(head_z(SMILE[0])))
    cc, rc = fwd(*HEAD_PROFILE_ROWS["chin"])
    out["chin"] = (y_of(cc), float(head_z(rc)))
    out["chin_bottom"] = (y_of(CHIN_BOTTOM[0]), float(head_z(CHIN_BOTTOM[1])))
    back = min(int(np.where(side[r])[0].min()) for r in range(*HEAD_PROFILE_ROWS["back"]))
    out["back"] = (y_of(back), None)
    fr = head_target(sh, "front")
    _, fmid, (f0, f1) = HEAD_VIEWS["front"]
    run = run_near(fr, 950, fmid, f0, f1)
    out["half_950"] = (run[1] + 1 - run[0]) / 2.0 * HEAD_SX
    print("BROTHER bald row landmarks (y, z): %s" % json.dumps({k: [None if v is None else round(v, 4) for v in vv] if isinstance(vv, tuple) else round(vv, 4) for k, vv in out.items()}))
    return out


def head_points(M):
    return np.array(M.tag["base_head_pts"])


def head_mirror(M):
    """For the head's points, each one's mirror image (itself on the middle line); every other point its own."""
    idx = np.concatenate([head_points(M)] + [np.array(r) for r in M.tag.get("neck_rings", [])])
    P = np.array(M.P)
    kd = kdtree.KDTree(len(idx))
    for k, i in enumerate(idx):
        kd.insert(Vector(P[i]), k)
    kd.balance()
    mir = np.arange(len(P))
    for i in idx:
        q, k, d = kd.find(Vector((-P[i][0], P[i][1], P[i][2])))
        if d < 2e-3:
            mir[i] = idx[k]
    return mir


def folded_faces(M, fids, N0):
    """Faces whose normal has turned more than 90 degrees from where they began (a fold or a crossing)."""
    n = 0
    for fi in fids:
        if np.dot(face_normal(M.P, M.faces[fi]), N0[fi]) < 0:
            n += 1
    return n


def base_head_round(M, sh, views, step=0.8, reach=40, sel_extra=None, more=(), hold_loop=True):
    """One round of the outline fit: every head point on a view's outline (squarely side-on to that view) moved to
    the sheet's outline along its outward direction; the moves spread to the rest of the head (each point to its
    neighbours' mean, weighted), the open neck's points held."""
    P = np.array(M.P)
    tris = head_tris(M)
    N = normals_of(P, M.tris())
    move = np.zeros_like(P)
    count = np.zeros(len(P))
    sel = np.zeros(len(P), bool)
    sel[head_points(M)] = True
    if hold_loop:
        sel[M.tag["neck_loop"]] = False
    if sel_extra is not None:
        sel &= sel_extra
    sel[list(more)] = True
    for view in views:
        T = head_target(sh, view)
        P2, dep = project("head_" + view, P)
        zb, _ = raster(P2, dep, tris, T.shape)
        R = np.isfinite(zb)
        d2, facing = screen_dir("head_" + view, N)
        L = np.linalg.norm(d2, axis=1)
        rows = P2[:, 1]
        ok = sel & (np.abs(facing) < (0.55 if view in ("front", "side", "back") else 0.3)) & (L > 0.4)
        ok &= (rows > HEAD_ROWS_SEEN[0]) & (rows < HEAD_ROWS_SEEN[1] - 6)
        h, w = T.shape
        for v in np.where(ok)[0]:
            p = P2[v]
            dirn = d2[v] / L[v]
            q = p + dirn * 2.0
            qi = (int(q[1]), int(q[0]))
            if not (0 <= qi[0] < h and 0 <= qi[1] < w) or R[qi]:
                continue
            pi = (int(p[1]), int(p[0]))
            dist = None
            if T[pi]:
                for k in range(1, reach):
                    qq = p + dirn * k
                    if not T[min(max(int(qq[1]), 0), h - 1), min(max(int(qq[0]), 0), w - 1)]:
                        dist = k - 0.5
                        break
            else:
                for k in range(1, reach):
                    qq = p - dirn * k
                    if T[min(max(int(qq[1]), 0), h - 1), min(max(int(qq[0]), 0), w - 1)]:
                        dist = -(k - 0.5)
                        break
            if dist is None:
                continue
            move[v] += world_dir("head_" + view, dirn[None, :])[0] * dist * HEAD_SX
            count[v] += 1
    has = count > 0
    move[has] /= count[has, None]
    E = edges_of([M.faces[i] for i in M.tag["base_head_faces"]])
    D = move.copy()
    Wt = has.astype(float) * 3.0
    deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
    hold = np.zeros(len(P), bool)
    if hold_loop:
        hold[M.tag["neck_loop"]] = True
    for _ in range(HEAD_DIFFUSE):
        acc = np.zeros_like(D)
        np.add.at(acc, E[:, 0], D[E[:, 1]])
        np.add.at(acc, E[:, 1], D[E[:, 0]])
        D = (Wt[:, None] * move + acc) / np.maximum(Wt + deg, 1e-9)[:, None]
        D[hold] = 0.0
    keep = np.zeros(len(P), bool)
    keep[head_points(M)] = True
    keep[list(more)] = True
    D[~keep | hold] = 0.0
    P += D * step
    M.P = [p for p in P]
    return int(has.sum()), float(np.linalg.norm(move[has], axis=1).max() if has.any() else 0.0)


def head_smooth(M, rounds=2, lam=0.5, mu=-0.53, only=None):
    """Taubin smoothing of the head's points (keeps size), the neck's loop held."""
    P = np.array(M.P)
    E = edges_of([M.faces[i] for i in M.tag["base_head_faces"]])
    deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
    sel = np.zeros(len(P), bool)
    sel[head_points(M)] = True
    sel[M.tag["neck_loop"]] = False
    if only is not None:
        sel &= only
    for _ in range(rounds):
        for f in (lam, mu):
            acc = np.zeros_like(P)
            np.add.at(acc, E[:, 0], P[E[:, 1]])
            np.add.at(acc, E[:, 1], P[E[:, 0]])
            avg = acc / np.maximum(deg, 1)[:, None]
            P[sel] += (avg[sel] - P[sel]) * f
    M.P = [p for p in P]


# The lips' meeting line of the base head (its own vertex numbers, his right corner to his left: the corners, then
# through the upper corner quad to the middle line): kept as one edge loop and laid on the painted lip line
# (snap_mouth_line), where the face rig cuts the mouth open (tools/FACE_RIG.md, "Integration").
MOUTH_LINE_BASE = (268, 153, 168, 271, 183, 286, 40, 128, 25, 10, 125)
MOUTH_DRAG = 0.006            # snap_mouth_line: metres round the loop over which its neighbours follow it up or down


def snap_mouth_line(M):
    """The lips' meeting loop (MOUTH_LINE_BASE, with every point the refines put on its edges) moved up or down onto
    the painted lip line (SMILE's curve in the head sheet, where the face picture paints the mouth), its neighbours
    within MOUTH_DRAG following; the SMILE groove lies on the same curve, so the mouth has one modelled crease."""
    line = M.tag.get("mouth_line")
    if not line:
        return
    P = np.array(M.P)
    nb = {}
    for f in M.faces:
        for a, b in zip(f, list(f[1:]) + [f[0]]):
            nb.setdefault(a, set()).add(b)
            nb.setdefault(b, set()).add(a)
    path = [line[0]]
    for a, b in zip(line[:-1], line[1:]):
        prev = {a: None}
        todo = [a]
        while todo and b not in prev:
            nxt = []
            for v in todo:
                for w_ in nb.get(v, ()):
                    if w_ not in prev:
                        prev[w_] = v
                        nxt.append(w_)
            todo = nxt
        seg = []
        v = b
        while v is not None and v != a:
            seg.append(v)
            v = prev.get(v)
        path += seg[::-1]
    col = np.abs(P[:, 0]) / HEAD_SX
    r0, rise, half, _ = SMILE
    want = head_z(r0 - rise * np.clip(col / half, 0, 1.2) ** 2)
    dz = np.zeros(len(P))
    dz[path] = np.clip(want[path] - P[path, 2], -MOUTH_SNAP_MAX, MOUTH_SNAP_MAX)
    hp = np.array(M.tag["base_head_pts"])
    on = np.zeros(len(P), bool)
    on[hp] = True
    on[path] = False
    kd = kdtree.KDTree(len(path))
    for k, v in enumerate(path):
        kd.insert(Vector(P[v]), k)
    kd.balance()
    for v in np.where(on)[0]:
        _, k, d = kd.find(Vector(P[v]))
        if d < MOUTH_DRAG:
            dz[v] = dz[path[k]] * (1.0 - float(smooth01(0.0, MOUTH_DRAG, d)))
    P[:, 2] += dz
    M.P = [p for p in P]
    M.tag["mouth_loop"] = path
    zs = P[path, 2]
    print("%s MOUTH loop: %d points (an edge path, his right corner to his left), z %.4f at the middle, %.4f / %.4f at the corners, x %.4f to %.4f; moved at most %.1f mm" % (
        WHO, len(path), float(P[path[len(path) // 2], 2]), float(zs[0]), float(zs[-1]), float(P[path, 0].min()),
        float(P[path, 0].max()), 1000 * float(np.abs(dz[path]).max())))


def base_head(M, sh, top_ring):
    """The base head put on him: placed, warped by landmarks, fitted to the bald row's outlines, bridged to the
    torso's top ring. Its points and faces go into M (part "head"; the bridge "neck"); its own UVs are kept per face
    corner (M.base_uv) for the face picture's layout."""
    P, faces, uvs, loc = load_base("head")
    P[:, 0] -= (P[:, 0].max() + P[:, 0].min()) / 2.0
    # (the base is symmetrical to a fraction of a millimetre: made exact)
    mid = np.where(np.abs(P[:, 0]) < 1e-3)[0]
    P[mid, 0] = 0.0
    ref = BASE_REF.get("P", P)
    B = {}
    mark_i = {}
    for k, v in HEAD_BASE_MARKS.items():
        yz = np.array(v) - loc[1:]
        mark_i[k] = mid[np.argmin(np.linalg.norm(ref[mid][:, 1:] - yz, axis=1))]
    if HEAD_ROUTE == "fresh":
        n_cage = len(P)
        P, faces, uvs = catmull_clark(P, faces, uvs)
        mid = np.where(np.abs(P[:, 0]) < 1e-3)[0]
        P[mid, 0] = 0.0
        print("%s FRESH head: mix %s, subdivided once: %d cage points -> %d points, %d faces" % (
            WHO, HEAD_MIX_FRESH, n_cage, len(P), len(faces)))
    for k, i in mark_i.items():
        B[k] = P[i, 1:].copy()
    B["crown"] = np.array((0.0, P[:, 2].max()))
    S_ = sheet_head_marks(sh)
    # The ears (as the base has them): the points standing out at the sides behind the cheeks.
    ear = (np.abs(P[:, 0]) > 0.073) & (P[:, 1] > 0.02) & (P[:, 2] > -0.025) & (P[:, 2] < 0.065)
    ear_b = {s: np.where(ear & (np.sign(P[:, 0]) == s))[0] for s in (1, -1)}
    # 1. heights: the face's front warped by its landmarks (piecewise straight between them); the back of the head
    # scaled evenly from the chin's underside to the crown; between them blended by how far forward a point is.
    names = ["chin_bottom", "chin", "mouth", "tip", "nasion", "brow", "crown"]
    zb = np.array([B[n][1] for n in names])
    zs = np.array([S_[n][1] for n in names])
    print("BROTHER head heights base %s -> sheet %s" % (np.round(zb, 3).tolist(), np.round(zs, 3).tolist()))
    zf = np.interp(P[:, 2], zb, zs, left=None, right=None)
    lo = P[:, 2] < zb[0]
    zf[lo] = zs[0] + (P[lo, 2] - zb[0]) * (zs[-1] - zs[0]) / (zb[-1] - zb[0])
    zl = zs[0] + (P[:, 2] - zb[0]) * (zs[-1] - zs[0]) / (zb[-1] - zb[0])
    y_ear = float(P[ear_b[1], 1].mean())
    wf = smooth01(y_ear - 0.01, y_ear - 0.07, P[:, 1])
    Z = zf * wf + zl * (1 - wf)
    # 2. depth: the back of the skull to the brow as the side view has it
    yb_back = float(P[:, 1].max())
    sy = (S_["back"][0] - S_["brow"][0]) / (yb_back - B["brow"][0])
    Y = S_["back"][0] + (P[:, 1] - yb_back) * sy
    # 3. width: the skull's half width above the ears (front view, row 950)
    z950 = float(head_z(950))
    band = np.abs(Z - z950) < 0.01
    sx = S_["half_950"] / float(np.abs(P[band, 0]).max())
    X = P[:, 0] * sx
    print("BROTHER head scales: depth %.3f, width %.3f, height %.3f" % (sy, sx, (zs[-1] - zs[0]) / (zb[-1] - zb[0])))
    P = np.stack([X, Y, Z], 1)
    # 4. the ears where the side view has them (EAR_ROWS, EAR_COLS): each ear's points moved and scaled in (y, z) from
    # their own box to the sheet's, fully on the ear, fading out over 1.5 cm round it
    ys0, ys1 = sorted((-(EAR_COLS[0] - HEAD_VIEWS["side"][1]) * HEAD_SX, -(EAR_COLS[1] - HEAD_VIEWS["side"][1]) * HEAD_SX))
    zs0, zs1 = float(head_z(EAR_ROWS[1])), float(head_z(EAR_ROWS[0]))
    for s, ids in ear_b.items():
        e = P[ids]
        y0, y1, z0, z1 = e[:, 1].min(), e[:, 1].max(), e[:, 2].min(), e[:, 2].max()
        d = np.full(len(P), 1.0)
        kd = kdtree.KDTree(len(ids))
        for k, i in enumerate(ids):
            kd.insert(Vector(P[i]), k)
        kd.balance()
        d = np.array([kd.find(Vector(p))[2] for p in P])
        w = 1.0 - smooth01(0.0, 0.03, d)
        w[np.sign(P[:, 0]) != s] = 0.0
        ny = ys0 + (P[:, 1] - y0) * (ys1 - ys0) / (y1 - y0)
        nz = zs0 + (P[:, 2] - z0) * (zs1 - zs0) / (z1 - z0)
        P[:, 1] = P[:, 1] * (1 - w) + ny * w
        P[:, 2] = P[:, 2] * (1 - w) + nz * w
        # (squeezed into the sheet's box the base ear read as a flat plate from the side: its bowl pressed in toward
        # the head and its rim (the helix) rolled out, by how far each point is from the ear's middle)
        e = P[ids]
        cyz = np.array(((e[:, 1].min() + e[:, 1].max()) / 2, (e[:, 2].min() + e[:, 2].max()) / 2))
        half = np.array(((e[:, 1].max() - e[:, 1].min()) / 2, (e[:, 2].max() - e[:, 2].min()) / 2))
        rr = np.linalg.norm((e[:, 1:] - cyz) / half, axis=1)
        out = np.where(rr > 0.72, 0.0025 * smooth01(0.72, 0.95, rr), -0.005 * (1 - smooth01(0.25, 0.65, rr)))
        # (polish pass, the critic: "thin flat paddles ... thicken the rim, add a concha bowl, angle the ear out":
        # the rim rolled further, an antihelix ridge inside it, and the ear turned out 6 degrees from its front edge)
        out = out + 0.0015 * smooth01(0.72, 0.95, rr) + 0.0015 * np.exp(-((rr - 0.58) / 0.1) ** 2)
        # (the turn-out fades over the ear's top third, which otherwise flared into an elf's point seen from above)
        nz = (e[:, 2] - cyz[1]) / half[1]
        out = out + (e[:, 1] - e[:, 1].min()) * math.tan(math.radians(6.0)) * (1.0 - 0.75 * smooth01(0.2, 0.8, nz))
        out = out - 0.002 * smooth01(0.5, 1.0, nz) * smooth01(0.72, 0.95, rr)
        P[ids, 0] += s * out
    # Into M
    base = len(M.P)
    idx = [M.add(p, "head") for p in P]
    M.tag["n_cage"] = len(idx)
    f0 = len(M.faces)
    M.base_uv = getattr(M, "base_uv", {})
    # 5. the neck's opening: the underside behind the chin (faces facing down, behind the throat), taken out
    Pn = P
    hole = set()
    zc = S_["chin_bottom"][1]
    for k, f in enumerate(faces):
        n = face_normal(Pn, f)
        n = n / max(np.linalg.norm(n), 1e-12)
        c = Pn[f].mean(0)
        if n[2] < -0.3 and c[1] > S_["chin_bottom"][0] + 0.05 and abs(c[0]) < 0.07 and c[2] < zc + 0.09:
            hole.add(k)
    if HEAD_ROUTE == "r7":
        hole = set(r7_load()["hole"])     # (round seven's own opening for the neck)
    kept = []
    for k, f in enumerate(faces):
        if k in hole:
            continue
        M.face([idx[v] for v in f], "head")
        M.base_uv[len(M.faces) - 1] = {idx[v]: uv for v, uv in zip(f, uvs[k])}
        kept.append(len(M.faces) - 1)
    M.tag["base_head_faces"] = kept
    M.tag["base_head_pts"] = idx
    M.tag["mouth_line"] = [idx[i] for i in MOUTH_LINE_BASE]
    M.tag["ear_l"] = [idx[i] for i in ear_b[1]]
    M.tag["ear_r"] = [idx[i] for i in ear_b[-1]]
    loops = open_loops([M.faces[i] for i in kept])
    print("BROTHER head: %d faces taken out for the neck; open loops %s" % (len(hole), [len(l) for l in loops]))
    M.tag["neck_loop"] = max(loops, key=len)
    M.tag["head_rings"] = []
    # 6. the nose: as wide as the front view's ball (NOSE), row by row, over the points standing forward of the cheeks
    Pm = np.array(M.P)
    hp = np.array(idx)
    nz0, nz1 = float(head_z(NOSE[-1][0] + 2)), float(head_z(NOSE[0][0]))
    rows_ = head_row(Pm[hp, 2])
    cheek_y = {}
    gain = np.ones(len(hp))
    wnose = np.zeros(len(hp))
    for k, i in enumerate(hp):
        x, y, z = Pm[i]
        if not (nz0 <= z <= nz1) or abs(x) > 0.045:
            continue
        band = (np.abs(Pm[hp, 2] - z) < 0.006) & (np.abs(Pm[hp, 0]) > 0.035) & (np.abs(Pm[hp, 0]) < 0.05) & (Pm[hp, 1] < 0)
        if not band.any():
            continue
        yc = float(Pm[hp[band], 1].min())
        wnose[k] = float(np.clip((yc - y) / 0.008, 0, 1))
    for k, i in enumerate(hp):
        if wnose[k] <= 0:
            continue
        z = Pm[i][2]
        band = (np.abs(Pm[hp, 2] - z) < 0.004) & (wnose > 0.5)
        have = float(np.abs(Pm[hp[band], 0]).max()) if band.any() else 0.0
        want = float(np.interp(rows_[k], [a for a, _ in NOSE], [w_ for _, w_ in NOSE])) / 2.0 * HEAD_SX
        if have > 0.004:
            gain[k] = 1.0 + (float(np.clip(want / have, 0.8, NOSE_GAIN_MAX)) - 1.0) * wnose[k]
    Pm[hp, 0] *= gain
    M.P = [p for p in Pm]
    print("BROTHER nose widened: %d points, most times %.2f" % (int((gain > 1.001).sum()), float(gain.max())))
    # 7. the outline fit, five views, kept symmetrical; the angled views' own angle and middle found first
    N0 = {fi: face_normal(M.P, M.faces[fi]) for fi in kept}
    mir = head_mirror(M)
    head_silhouettes(M, sh, "placed")
    align_head_views(M, sh, spread=10.0, step=2.0)
    for rnd in range(HEAD_FIT_PASSES):
        views = ("front", "side", "back") if rnd < 3 else HEAD_FIT_VIEWS
        moved, most = base_head_round(M, sh, views, step=0.8)
        symmetrize(M, mir)
        if rnd % 3 == 2:
            head_smooth(M, 1)
            symmetrize(M, mir)
        if rnd == 4:
            align_head_views(M, sh, spread=4.0, step=1.0)
        print("BROTHER head fit %d: %d outline points, most %.1f mm; folded faces %d" % (rnd, moved, most * 1000, folded_faces(M, kept, N0)))
    head_silhouettes(M, sh, "fitted")
    # 8. the neck: the opening's loop bridged to the torso's top ring through two rings between (the zipper takes the
    # opening's count to the ring's 16)
    Pm = np.array(M.P)
    cy = float(np.mean([Pm[v][1] for v in top_ring]))

    def ang(Q):
        return np.arctan2(Q[:, 0], -(Q[:, 1] - cy))
    # (the opening's loop is steeply slanted, throat to nape, so its points' angles round the neck's axis need not run
    # in order: it is walked by its own length instead, from the throat, the way the torso's ring runs (toward +X),
    # and each ring point takes the loop's point at its own share of the way round)
    loop = list(M.tag["neck_loop"])
    a0 = np.abs(np.angle(np.exp(1j * ang(Pm[loop]))))
    s0 = int(np.argmin(a0))
    loop = loop[s0:] + loop[:s0]
    if Pm[loop[1]][0] < Pm[loop[-1]][0]:
        loop = [loop[0]] + loop[1:][::-1]
    M.tag["neck_loop"] = loop
    seg = np.linalg.norm(Pm[loop] - Pm[loop[1:] + loop[:1]], axis=1)
    uL = np.concatenate([[0.0], np.cumsum(seg)[:-1]]) / seg.sum()
    n_t = len(top_ring)
    uT = np.arange(n_t) / float(n_t)
    Qe = np.concatenate([Pm[loop], Pm[loop[:1]]])
    ue = np.append(uL, 1.0)
    Lr = np.stack([np.interp(uT, ue, Qe[:, k]) for k in range(3)], 1)
    Tr = Pm[top_ring]
    rings = []
    for t in (0.3, 0.65):
        R = Lr * (1 - t) + Tr * t
        # (the neck's sides full, not a waist between head and shoulders)
        c = R.mean(0)
        R[:, :2] = c[:2] + (R[:, :2] - c[:2]) * (1.0 + 0.04 * math.sin(math.pi * t))
        rings.append([M.add(q, "neck") for q in R])
    zipper(M, loop, rings[0], None, "neck", order=(uL * math.tau, uT * math.tau))
    M.bridge(rings[0], rings[1], "neck")
    M.bridge(rings[1], list(top_ring), "neck")
    M.tag["neck_rings"] = rings
    return S_


# The hand, from `Hand - Stylized` (a right hand in the bundle: fingers down -Z, palm toward +Y, thumb at +X). It is
# worked on in its own frame: a across toward the thumb, b out of the back of the hand, l along the fingers from the
# wrist; on him that frame is the arm's (Wd, Tb, L) of hand() above, which is mirror-handed, so it becomes his left
# hand there (and is mirrored again for his right). The forearm's stub and cap are cut off; its open loop sits
# HAND_LOOP_L beyond the wrist ring. Fitted in the sheet's pose (fingers up, spread, the thumb out), then posed.
HAND_LOOP_L = 0.012
HAND_LEN = 0.208               # the wrist to the middle fingertip (the hands sheet, at HAND_SX)
HAND_TIP = (612.0, 92.0)       # the back view's middle fingertip (column, row)
HAND_BACK_COLS = (400, 960)
HAND_THUMB_COLS = (1980, 2420)
FINGER_THIN = 0.14              # the fingers this much thinner from back to palm beyond the knuckle (shape_fingers)
THENAR = 0.006                 # metres: the thumb's pad pushed out of the palm
WRIST_WIDEN = (1.3, 1.12)      # shape_fingers: the hand's wrist loop widened across and back to palm (to the sheet's 9 cm wrist)
# (polish pass: a gentler hang, as the body sheet draws it: each finger curled a little more than the one before it
# from the index to the little finger, and the fingers a little apart; the thumb less tucked)
# (sixth round, the critic: "the curl as a gradient: index about 15 degrees a joint, little finger about 35", the
# fingers together with no gap between middle and ring, the thumb lower and turned about 45 degrees off the palm)
# (seventh round, the brief: a relaxed hang, the fingers nearly straight: about 8, 12, 10 degrees at the index's three
# joints rising to about 15, 22, 15 at the little finger; slightly apart)
HAND_POSE_RELAXED = {"curl": {"index": (0.14, 0.21, 0.17), "middle": (0.17, 0.26, 0.19), "ring": (0.21, 0.31, 0.21),
                              "little": (0.26, 0.38, 0.26)}, "together": 0.3, "thumb_in": 0.6, "thumb_fwd": 0.5, "thumb_curl": 0.25,
                     "thumb_aim": (0.014, 0.012)}
for _k in ("thumb_in", "thumb_fwd", "thumb_curl"):
    if "--" + _k in ARGS:
        HAND_POSE_RELAXED[_k] = float(arg("--" + _k, "0"))
HAND_POSE_THUMBVIEW = {"curl": (0.7, 0.2, 0.1), "together": 0.0, "thumb_in": 0.0, "thumb_fwd": 0.45, "thumb_curl": 0.1}
HB = {}


def sheet_fingers(sh):
    """The back view's digits as chains of runs followed down from their tips: each digit's tip (column, row), its
    middle line's direction (toward the tip, in the picture), its median width (pixels) and the row it joins the
    palm. Gives them in order little, ring, middle, index, thumb."""
    m = sh.hands_mask
    c0, c1 = HAND_BACK_COLS
    chains = []
    for r in range(70, 470):
        runs = runs_of(m[r], c0, c1, 4)
        claimed = {}
        for ci, ch in enumerate(chains):
            if ch["end"] is not None:
                continue
            last = ch["pts"][-1]
            hit = [k for k, (a, b) in enumerate(runs) if a - 3 <= last[0] <= b + 3]
            if not hit:
                ch["end"] = r
                continue
            claimed.setdefault(hit[0], []).append(ci)
        for k, (a, b) in enumerate(runs):
            owners = claimed.get(k, [])
            if len(owners) > 1:
                for ci in owners:
                    chains[ci]["end"] = r
            elif len(owners) == 1:
                chains[owners[0]]["pts"].append(((a + b + 1) / 2.0, r, b + 1 - a))
            else:
                chains.append({"top": r, "pts": [((a + b + 1) / 2.0, r, b + 1 - a)], "end": None})
    chains = [c for c in chains if len(c["pts"]) > 30]
    out = []
    for c in chains:
        pts = np.array(c["pts"])
        use = pts[12:-6] if len(pts) > 30 else pts
        k, c_ = np.polyfit(use[:, 1], use[:, 0], 1)
        d = np.array((-k, -1.0))
        d /= np.linalg.norm(d)
        out.append({"tip": (float(pts[0, 0]), float(c["top"])), "dir": d, "width": float(np.median(use[:, 2])),
                    "join": int(c["end"] or 470), "col": float(pts[:, 0].mean())})
    fingers = sorted([c for c in out if c["tip"][1] < 260], key=lambda c: c["col"])
    thumb = [c for c in out if c["tip"][1] >= 260]
    print("BROTHER sheet digits: %s" % json.dumps([(round(c["tip"][0]), round(c["tip"][1]), round(c["width"]), c["join"], [round(v, 2) for v in c["dir"]]) for c in fingers + thumb]))
    if len(fingers) != 4 or not thumb:
        raise RuntimeError("the hands sheet's back view did not give four fingers and a thumb")
    return fingers + [max(thumb, key=lambda c: c["col"])]


def drop_finger_rings(C, faces, uvs, label, loop, names, nth=3):
    """(From the captain's build, with the faces' UVs carried.) Each finger's ring `nth` from its tip collapsed onto
    the next ring toward the palm (rings walked from the tip's cap by neighbours); gives the compacted points, faces,
    UVs, labels and wrist loop."""
    adj = {}
    for f in faces:
        for i in range(len(f)):
            a, b = f[i], f[(i + 1) % len(f)]
            adj.setdefault(a, set()).add(b)
            adj.setdefault(b, set()).add(a)
    merge = {}
    for n in names:
        ids = set(np.where(label == n)[0].tolist())
        cap = max((f for f in faces if all(v in ids for v in f)), key=lambda f: C[f, 2].mean())
        rings = [set(cap)]
        prev = set()
        while len(rings) <= nth + 1:
            nxt = set()
            for v in rings[-1]:
                nxt |= adj[v]
            nxt -= rings[-1] | prev
            prev = rings[-1]
            rings.append(nxt)
        a, b = rings[nth], rings[nth + 1]
        if len(a) != len(b) or len(a) < 3:
            print("%s finger %s: rings %s, none taken out" % (WHO, n, [len(r) for r in rings]))
            continue
        for v in a:
            w = [u for u in adj[v] if u in b]
            if len(w) == 1:
                merge[v] = w[0]
    out, out_uv = [], []
    for f, uv in zip(faces, uvs):
        h, hu = [], []
        for v, q in zip(f, uv):
            v = merge.get(v, v)
            if v not in h:
                h.append(v)
                hu.append(q)
        if len(h) >= 3:
            out.append(h)
            out_uv.append(hu)
    used = sorted({v for f in out for v in f})
    remap = {v: i for i, v in enumerate(used)}
    return (C[used], [[remap[v] for v in f] for f in out], out_uv, label[used], [remap[merge.get(v, v)] for v in loop])


def to_back_view(C):
    """Canonical hand points -> the back view's (column, row), its middle fingertip on HAND_TIP."""
    t = HB["tip_mid"]
    return np.stack([HAND_TIP[0] + (C[:, 0] - t[0]) / HAND_SX, HAND_TIP[1] - (C[:, 2] - t[2]) / HAND_SX], 1)


def from_back_view(c, r):
    t = HB["tip_mid"]
    return np.array((t[0] + (c - HAND_TIP[0]) * HAND_SX, 0.0, t[2] - (r - HAND_TIP[1]) * HAND_SX))


def rot_about(points, pivot, axis, angle, weight):
    R = np.array(Matrix.Rotation(angle, 3, Vector(axis)))
    Q = (points - pivot) @ R.T + pivot
    return points * (1 - weight[:, None]) + Q * weight[:, None]


def digit_axis(C, ids):
    Q = C[ids]
    c = Q.mean(0)
    _, _, vt = np.linalg.svd(Q - c)
    d = vt[0]
    if d[2] < 0:
        d = -d
    return c, d


def finger_parts(C, adj, z_web):
    """The hand's points beyond z_web split into connected parts (more than 8 points each)."""
    far = set(np.where(C[:, 2] > z_web)[0].tolist())
    comps = []
    while far:
        s = far.pop()
        st, comp = [s], [s]
        while st:
            v = st.pop()
            for w in adj.get(v, ()):
                if w in far:
                    far.remove(w)
                    st.append(w)
                    comp.append(w)
        comps.append(comp)
    return [c for c in comps if len(c) > 8]


def base_hand_fit(sh):
    """The base hand in its own frame, fitted to the hands sheet's back view in the sheet's pose; kept in HB; the
    back, palm and thumb-side silhouettes compared."""
    P, faces, uvs, loc = load_base("hand")
    C = np.stack([P[:, 0], -P[:, 1], -P[:, 2]], 1)
    # (the forearm's stub and its cap off: the faces reaching within 6 mm of the stub's top)
    keep = [k for k, f in enumerate(faces) if C[f, 2].min() > 0.006]
    used = sorted({v for k in keep for v in faces[k]})
    remap = {v: i for i, v in enumerate(used)}
    C = C[used]
    faces = [[remap[v] for v in faces[k]] for k in keep]
    uvs = [uvs[k] for k in keep]
    loops = open_loops(faces)
    loop = max(loops, key=len)
    # (un-subdivided once, the stub's cut leaves a saw-toothed loop: its points brought to one height)
    C[loop, 2] = float(np.median(C[loop, 2]))
    print("BROTHER base hand: %d points, %d faces, %d triangles after the stub; wrist loop %d" % (len(C), len(faces), sum(len(f) - 2 for f in faces), len(loop)))
    # labels: the four fingers (beyond the webs), the thumb, the palm
    adj = {}
    for f in faces:
        for i in range(len(f)):
            a, b = f[i], f[(i + 1) % len(f)]
            adj.setdefault(a, set()).add(b)
            adj.setdefault(b, set()).add(a)
    # (tenth round: collapsed harder, an edge can cross a web at 0.145: the line is raised until four fingers part)
    for z_web in (0.145, 0.15, 0.155, 0.16, 0.165):
        comps = finger_parts(C, adj, z_web)
        if len(comps) == 4:
            break
    if z_web != 0.145:
        print("BROTHER base hand: fingers parted at %.3f" % z_web)
    comps = sorted([c for c in comps if len(c) > 8], key=lambda c: C[c, 0].mean())
    if len(comps) != 4:
        raise RuntimeError("base hand: %d fingers found" % len(comps))
    label = np.array([""] * len(C), dtype=object)
    names = ("little", "ring", "middle", "index")
    axes = {}
    for n, comp in zip(names, comps):
        label[comp] = n
        axes[n] = digit_axis(C, comp)
    thumb = ((C[:, 0] > 0.05) | ((C[:, 0] > 0.04) & (C[:, 1] < -0.012))) & (C[:, 2] > 0.03) & (C[:, 2] < 0.15) & (label == "")
    label[thumb] = "thumb"
    for v in np.where((label == "") & (C[:, 2] > 0.112))[0]:
        best = None
        for n in names:
            c, d = axes[n]
            t = (C[v, 2] - c[2]) / d[2]
            a = c[0] + d[0] * t
            if best is None or abs(C[v, 0] - a) < best[0]:
                best = (abs(C[v, 0] - a), n)
        label[v] = best[1]
    # (seventh round, the budget: under 450 triangles a hand; from the captain's build: one ring of each finger taken
    # out, third from the tip, between its middle and end joints, and the thumb's second from its tip)
    # (NOT used: the base hand's UVs are per corner, and a merged point's corners keep the UVs of the point that was
    # merged away, so the hand's painting tore into shards (seventh round, r4); left off until the UVs are carried
    # from the kept point)
    if HAND_DROP:
        C, faces, uvs, label, loop = drop_finger_rings(C, faces, uvs, label, loop, names)
        C, faces, uvs, label, loop = drop_finger_rings(C, faces, uvs, label, loop, ("thumb",), nth=2)
    if HAND_DROP and HAND_DROP_MORE:
        C, faces, uvs, label, loop = drop_finger_rings(C, faces, uvs, label, loop, names, nth=HAND_DROP_MORE)
        C, faces, uvs, label, loop = drop_finger_rings(C, faces, uvs, label, loop, ("thumb",), nth=2)
    axes = {n: digit_axis(C, np.where(label == n)[0]) for n in names}
    axes["thumb"] = digit_axis(C, np.where((label == "thumb") & (C[:, 2] > 0.06))[0])
    print("BROTHER base hand labels: %s; %d triangles" % ({n: int((label == n).sum()) for n in names + ("thumb", "")}, sum(len(f) - 2 for f in faces)))
    # joints (knuckle/root, two joints, tip) along each digit's axis
    J = {}
    for n in names + ("thumb",):
        ids = np.where(label == n)[0]
        c, d = axes[n]
        s = (C[ids] - c) @ d
        tip = c + d * s.max()
        if n == "thumb":
            root = c + d * s.min()
            ln = s.max() - s.min()
            J[n] = [root, root + d * ln * 0.42, root + d * ln * 0.74, tip]
        else:
            t = (0.122 - c[2]) / d[2]
            k = c + d * t
            ln = float(np.dot(tip - k, d))
            J[n] = [k, k + d * ln * 0.45, k + d * ln * 0.76, tip]
    # 1. scaled to the sheet: l from the loop to the middle tip, a by the palm's width at the knuckles, b by the wrist
    digits = sheet_fingers(sh)
    l_loop = float(C[loop, 2].mean())
    sl = (HAND_LEN - HAND_LOOP_L) / (J["middle"][3][2] - l_loop)
    webs = sorted(d["join"] for d in digits[:4])
    r_k = webs[1] + 22
    run = run_near(sh.hands_mask, r_k, HAND_TIP[0], *HAND_BACK_COLS)
    palm_s = (run[1] + 1 - run[0]) * HAND_SX
    band = (np.abs(C[:, 2] - J["middle"][0][2]) < 0.008) & (label != "thumb")
    sa = palm_s / float(C[band, 0].max() - C[band, 0].min()) * HAND_WIDE
    m = sh.hands_mask
    rr = run_near(m, 540, (HAND_THUMB_COLS[0] + HAND_THUMB_COLS[1]) / 2, *HAND_THUMB_COLS)
    wrist_s = (rr[1] + 1 - rr[0]) * HAND_SX if rr else 0.05
    sb = wrist_s / float(C[loop, 1].max() - C[loop, 1].min())
    sb = float(np.clip(sb, 0.8 * min(sa, sl), 1.25 * max(sa, sl)))
    o = np.array((0.0, 0.0, l_loop))
    S3 = np.array((sa, sb, sl))
    C = (C - o) * S3 + np.array((0.0, 0.0, HAND_LOOP_L))
    J = {n: [(p - o) * S3 + np.array((0.0, 0.0, HAND_LOOP_L)) for p in js] for n, js in J.items()}
    print("BROTHER hand scaled: across %.3f, back %.3f, along %.3f (sheet palm %.1f cm at row %d, wrist %.1f cm)" % (sa, sb, sl, palm_s * 100, r_k, wrist_s * 100))
    HB["tip_mid"] = J["middle"][3].copy()
    # 2. each digit turned (in the hand's plane) and sized to its drawn digit
    for n, dg in zip(names + ("thumb",), digits):
        ids = np.where(label == n)[0]
        piv = J[n][0]
        dm = J[n][3] - piv
        dm_len = float(np.linalg.norm(dm))
        dm /= dm_len
        tip_s = from_back_view(*dg["tip"])
        ds = np.array((dg["dir"][0], 0.0, -dg["dir"][1]))
        ds /= np.linalg.norm(ds)
        # (the drawn digit's own line toward its tip, through the model's knuckle: its length to where the drawn tip
        # stands along it)
        want = float(np.dot(tip_s - piv, ds))
        if True:
            # (each digit pointed from its knuckle (the thumb from its root) at the drawn tip, so each tip lands where
            # it is drawn)
            ds = (tip_s - piv) * np.array((1.0, 0.0, 1.0))
            want = float(np.linalg.norm(ds))
            ds /= want
        a0 = math.atan2(dm[0], dm[2])
        a1 = math.atan2(ds[0], ds[2])
        s_all = (C - piv) @ dm
        w = np.zeros(len(C))
        w[ids] = smooth01(-0.014, 0.006, s_all[ids])
        C = rot_about(C, piv, (0.0, 1.0, 0.0), a1 - a0, w)
        J[n] = [J[n][0]] + [rot_about(np.array([p]), piv, (0.0, 1.0, 0.0), a1 - a0, np.ones(1))[0] for p in J[n][1:]]
        # lengthen along it, beyond the knuckle only
        k = want / dm_len
        s = (C - piv) @ ds
        grow = np.where(s > 0, s * (k - 1.0), 0.0) * w
        C = C + ds[None, :] * grow[:, None]
        J[n] = [J[n][0]] + [p + ds * max(float(np.dot(p - piv, ds)), 0) * (k - 1.0) for p in J[n][1:]]
        # its width across, to the drawn width (a run across a slanted digit is wider than the digit by 1 / cos)
        if True:
            across = np.array((ds[2], 0.0, -ds[0]))
            mid_s = 0.5 * want
            near = ids[np.abs(((C[ids] - piv) @ ds) - mid_s) < 0.012]
            have = float(((C[near] - piv) @ across).max() - ((C[near] - piv) @ across).min()) if len(near) > 2 else 0.0
            want_w = dg["width"] * HAND_SX * abs(float(dg["dir"][1]))
            if have > 0.005:
                g = float(np.clip(want_w / have, 0.75, 1.5))
                ax_c = (C - piv) @ across
                cen = float(((C[near] - piv) @ across).mean())
                C = C + across[None, :] * ((ax_c - cen) * (g - 1.0) * w)[:, None]
        print("BROTHER hand %s: turned %.1f degrees, length times %.2f" % (n, math.degrees(a1 - a0), k))
    HB.update(C=C, faces=faces, uvs=uvs, label=label, J=J, loop=loop)
    # 3. the back view's outline: outline points moved onto the sheet's, the rest following
    for rnd in range(12):
        hand_outline_round(sh)
    shape_fingers()
    HB["flat"] = HB["C"].copy()
    if HAND_THUMB_FIT:
        hand_thumb_fit(sh)
    round_fingertips()
    hand_taubin()
    hand_silhouettes(sh)


HAND_THUMB_FIT = True
HAND_DROP = False              # drop_finger_rings on the base hand (see base_hand_fit)
HAND_DROP_MORE = 0             # a second ring of each finger taken out (this many from its tip; 0: none)
HAND_THUMB_FAT = (1.12, 1.3)   # the thumb thickened round its own line (across, toward the palm): a heavy thumb
TIP_POW = float(arg("--tippow", "3.0"))
HAND_WIDE = 1.08               # (ninth round, the critic: "big, square, practical hands ... the palm width 15%" more: the palm
                               # 8% wider than the hands sheet, as the body sheet draws it beside his thigh)
HAND_THUMB_SURFACE = "--thumbsurf" in ARGS   # hand_thumb_fit's front-to-back moves onto the thumb view's outline
TIP_DOME = (0.42, 0.12)        # round_fingertips: the share of the last bone from which each tip is domed; how far
                               # the very tip is drawn back (in shares of the finger's radius)


HAND_TAUBIN = int(arg("--handtaubin", "3"))


def hand_taubin():
    """Ninth round: the outline fit moves each outline point on its own, and on the once-un-subdivided hand (eight
    points round a finger) neighbours were pushed in and out alternately: the fingers' edges came out saw-toothed.
    Taubin rounds (no shrinking) over the whole hand but its wrist loop even them out."""
    C = HB["flat"].copy()
    E = edges_of(HB["faces"])
    deg = np.bincount(E.ravel(), minlength=len(C)).astype(float)[:, None]
    loop = list(HB["loop"])
    before = C.copy()
    for _ in range(HAND_TAUBIN):
        for lam in (0.5, -0.53):
            acc = np.zeros_like(C)
            np.add.at(acc, E[:, 0], C[E[:, 1]])
            np.add.at(acc, E[:, 1], C[E[:, 0]])
            d = acc / np.maximum(deg, 1) - C
            d[loop] = 0.0
            C += lam * d
    HB["flat"] = C
    HB["C"] = C.copy()
    print("%s HAND evened: %d Taubin rounds, most a point moved %.1f mm" % (
        WHO, HAND_TAUBIN, 1000 * float(np.linalg.norm(C - before, axis=1).max())))


def round_fingertips():
    """Seventh round, from the captain's build (the critic: "spiky tips"): the last bone of each digit, from
    TIP_DOME[0] of its length on, made a round cap: round its axis the finger's own cross-section at the start of the
    dome is kept, scaled by a quarter circle's height to nothing at the tip; the tip drawn back a little."""
    C = HB["flat"]
    lab = HB["label"]
    J = HB["J"]
    moved = 0.0
    for n in ("index", "middle", "ring", "little", "thumb"):
        ids = np.where(lab == n)[0]
        a, b = np.array(J[n][2], float), np.array(J[n][3], float)
        d = b - a
        ln = float(np.linalg.norm(d))
        d = d / ln
        s = (C[ids] - a) @ d / ln
        rel = (C[ids] - a) - np.outer((C[ids] - a) @ d, d)
        e1 = np.cross(d, (0.0, 1.0, 0.0))
        e1 /= np.linalg.norm(e1)
        e2 = np.cross(d, e1)
        phi = np.arctan2(rel @ e2, rel @ e1)
        r = np.linalg.norm(rel, axis=1)
        s0 = TIP_DOME[0]
        ref = (s > s0 - 0.3) & (s < s0 + 0.05)
        if ref.sum() < 4:
            # (with a second ring of each finger taken out the last bone has fewer rings: the nearest ring below)
            ref = (s > s0 - 0.9) & (s < s0 + 0.2)
        if ref.sum() < 4:
            print("%s fingertip %s: too few points to dome (%d)" % (WHO, n, int(ref.sum())))
            continue
        o = np.argsort(phi[ref])
        ph, rr = phi[ref][o], r[ref][o]
        R0 = np.interp(phi, np.concatenate([ph - math.tau, ph, ph + math.tau]), np.concatenate([rr, rr, rr]))
        smax = float(s.max())
        tip_s = smax - TIP_DOME[1] * float(np.median(rr)) / ln
        t = np.clip((s - s0) / max(tip_s - s0, 1e-3), 0.0, 1.0)
        # (ninth round, the critic: "spiky jagged tips": a quarter circle took the last ring nearly to the axis and the
        # cap stood on it as a point; a superellipse of power TIP_POW keeps the last ring broad, a blunt round end)
        want_r = R0 * np.clip(1.0 - np.minimum(t, 0.95) ** TIP_POW, 0.0, 1.0) ** (1.0 / TIP_POW)
        # (and the cap's own points, near the axis already, keep their distance from it: brought all to the axis they
        # made faces of no size, the torn tips)
        want_r = np.minimum(want_r, np.maximum(r, 0.35 * want_r))
        dome = s > s0
        new_s = np.minimum(s, tip_s)
        unit = rel / np.maximum(r, 1e-9)[:, None]
        Q = a + np.outer(new_s * ln, d) + unit * want_r[:, None]
        old = C[ids].copy()
        if os.environ.get("TIPDBG"):
            o_ = np.argsort(-s)
            print("TIPDBG %s ln %.4f s0 %.2f tip_s %.2f: %s" % (n, ln, s0, tip_s, " ".join(
                "%.2f/%.1f>%.1f" % (s[i], r[i] * 1000, want_r[i] * 1000 if dome[i] else r[i] * 1000) for i in o_[:22])))
        C[ids[dome]] = Q[dome]
        moved = max(moved, float(np.linalg.norm(C[ids] - old, axis=1).max()))
    HB["flat"] = C
    HB["C"] = C.copy()
    print("%s fingertips domed: most a point moved %.1f mm" % (WHO, moved * 1000))


def thumb_view_points(C, shift=(0.0, 0.0)):
    c0, c1 = HAND_THUMB_COLS
    t = HB["tip_mid"]
    b0 = float(HB["flat"][HB["loop"], 1].mean())
    return np.stack([(c0 + c1) / 2.0 + (C[:, 1] - b0) / HAND_SX + shift[0], HAND_TIP[1] - (C[:, 2] - t[2]) / HAND_SX + shift[1]], 1)


def _thumb_iou(P2, tris, T):
    zb, _ = raster(P2, np.zeros(len(P2)), tris, T.shape)
    m = np.isfinite(zb)
    m[:80] = False
    m[560:] = False
    return float((m & T).sum()) / max(float((m | T).sum()), 1.0)


def hand_thumb_fit(sh):
    """Seventh round, from the captain's build (the thumb-side view was 5.3 cm off, 62% overlap): first the thumb made
    heavy round its own line (HAND_THUMB_FAT); then the thumb-side view's shift and pose (finger curl, the thumb's
    swing and curl) found by trying and kept as HAND_POSE_THUMBVIEW; then the back and palm surfaces moved front to
    back onto that view's outline."""
    C = HB["flat"]
    lab = HB["label"]
    ids = np.where(lab == "thumb")[0]
    c_, d_ = digit_axis(C, ids)
    r_ = (C[ids] - c_) - np.outer((C[ids] - c_) @ d_, d_)
    s_ = (C[ids] - np.array(HB["J"]["thumb"][0])) @ d_
    w = smooth01(-0.005, 0.015, s_)
    fat = np.where(r_[:, 1] < 0, HAND_THUMB_FAT[1], HAND_THUMB_FAT[0])
    C[ids] = C[ids] + r_ * (fat - 1.0)[:, None] * w[:, None]
    HB["flat"] = C
    tris = hand_tris_of(HB["faces"])
    c0, c1 = HAND_THUMB_COLS
    T = np.zeros_like(sh.hands_mask)
    T[80:560, c0:c1] = sh.hands_mask[80:560, c0:c1]
    C0, _ = pose_hand(HB["flat"], HB["J"], HB["label"], HAND_POSE_THUMBVIEW)
    best = (-1, (0, 0))
    for dx in range(-120, 121, 8):
        for dy in range(-30, 31, 10):
            s = _thumb_iou(thumb_view_points(C0, (dx, dy)), tris, T)
            if s > best[0]:
                best = (s, (dx, dy))
    shift = best[1]
    pose = dict(HAND_POSE_THUMBVIEW)
    for it in range(2):
        for key, vals in (("thumb_fwd", (-0.3, 0.0, 0.3, 0.6, 0.9, 1.2)), ("thumb_in", (-0.9, -0.7, -0.5, -0.3, -0.1, 0.1, 0.3)),
                          ("thumb_curl", (0.0, 0.15, 0.3, 0.5)), ("curl", ((-0.1, 0, 0), (0, 0, 0), (0.12, 0.08, 0.06), (0.25, 0.12, 0.08), (0.7, 0.2, 0.1)))):
            scores = []
            for v_ in vals:
                p = dict(pose)
                p[key] = v_
                Cp, _ = pose_hand(HB["flat"], HB["J"], HB["label"], p)
                scores.append(_thumb_iou(thumb_view_points(Cp, shift), tris, T))
            pose[key] = vals[int(np.argmax(scores))]
        Cp, _ = pose_hand(HB["flat"], HB["J"], HB["label"], pose)
        best = (-1, shift)
        for dx in range(shift[0] - 16, shift[0] + 17, 4):
            for dy in range(shift[1] - 12, shift[1] + 13, 4):
                s = _thumb_iou(thumb_view_points(Cp, (dx, dy)), tris, T)
                if s > best[0]:
                    best = (s, (dx, dy))
        shift = best[1]
    HAND_POSE_THUMBVIEW.update(pose)
    print("%s thumb-side view: pose %s, shift %s, overlap %.3f" % (WHO, json.dumps(pose), shift, best[0]))
    E = edges_of(HB["faces"])
    deg = np.bincount(E.ravel(), minlength=len(lab)).astype(float)
    loopset = list(HB["loop"])
    h, w_ = T.shape
    for rnd in range(8 if HAND_THUMB_SURFACE else 0):
        Cp, _ = pose_hand(HB["flat"], HB["J"], HB["label"], HAND_POSE_THUMBVIEW)
        P2 = thumb_view_points(Cp, shift)
        zb, _ = raster(P2, -Cp[:, 0], tris, T.shape)
        R = np.isfinite(zb)
        N = normals_of(Cp, tris)
        move = np.zeros(len(Cp))
        has = np.zeros(len(Cp), bool)
        for v in range(len(Cp)):
            if abs(N[v, 1]) < 0.55 or not (95 < P2[v, 1] < 555):
                continue
            sgn = 1.0 if N[v, 1] > 0 else -1.0
            p = P2[v]
            q = p + np.array((sgn * 2.0, 0.0))
            if not (0 <= int(q[0]) < w_) or not (0 <= int(p[1]) < h) or R[int(q[1]), int(q[0])]:
                continue
            inside = T[int(p[1]), min(max(int(p[0]), 0), w_ - 1)]
            dist = None
            for k in range(1, 60):
                cc = int(p[0] + sgn * k) if inside else int(p[0] - sgn * k)
                hit = T[int(p[1]), min(max(cc, 0), w_ - 1)]
                if (inside and not hit) or (not inside and hit):
                    dist = (k - 0.5) if inside else -(k - 0.5)
                    break
            if dist is None:
                continue
            move[v] = sgn * dist * HAND_SX
            has[v] = True
        D = move.copy()
        Wt = has * 3.0
        for _ in range(20):
            acc = np.zeros_like(D)
            np.add.at(acc, E[:, 0], D[E[:, 1]])
            np.add.at(acc, E[:, 1], D[E[:, 0]])
            D = (Wt * move + acc) / np.maximum(Wt + deg, 1e-9)
            D[loopset] = 0.0
        HB["flat"][:, 1] += D * 0.6
    HB["C"] = HB["flat"].copy()


def shape_fingers():
    """Sixth round (the critic: "stubby sausage fingers ... jagged spiky tips, no modelled knuckles, the thumb a tiny
    nub"). On the fitted flat hand (x across toward the thumb, +y its back, z along the fingers):
    - each digit's last stretch clipped to a half ellipsoid round its axis, so the base mesh's square end cap becomes a
      round fingertip (the cap's corners pulled in, nothing pushed out);
    - the fingers a little thinner from back to palm beyond their knuckles (the sheet's side views: flat-backed
      fingers, not round sausages);
    - knuckle bumps on the back over each finger's root and middle joint;
    - a thenar pad: the palm's side under the thumb's root pushed out."""
    C = HB["C"].copy()
    J, label = HB["J"], HB["label"]
    ydir = np.array((0.0, 1.0, 0.0))
    for n in ("little", "ring", "middle", "index", "thumb"):
        ids = np.where(label == n)[0]
        js = [np.array(p, float) for p in J[n]]
        d = js[3] - js[2]
        d /= np.linalg.norm(d)
        a = np.cross(ydir, d)
        a /= np.linalg.norm(a)
        b = np.cross(d, a)
        Q = C[ids] - js[3]
        s = Q @ d                                      # along, 0 at the tip joint's mark, negative toward the hand
        ra, rb = Q @ a, Q @ b
        s_tip = float(s.max())
        # the finger's half widths a little behind the tip
        band = (s > s_tip - 0.022) & (s < s_tip - 0.012)
        if band.sum() < 4:
            continue
        Ra = float(np.abs(ra[band] - ra[band].mean()).max())
        Rb = float(np.abs(rb[band] - rb[band].mean()).max())
        ca, cb = float(ra[band].mean()), float(rb[band].mean())
        La = min(Ra, Rb) * 1.05
        s0 = s_tip - La
        q = np.stack([np.clip(s - s0, 0, None) / La, (ra - ca) / Ra, (rb - cb) / Rb], 1)
        r = np.linalg.norm(q, axis=1)
        out = (s > s0) & (r > 1.0)
        k = np.where(out, 1.0 / np.maximum(r, 1e-9), 1.0)
        s_n = np.where(s > s0, s0 + (s - s0) * k, s)
        ra_n = np.where(s > s0, ca + (ra - ca) * k, ra)
        rb_n = np.where(s > s0, cb + (rb - cb) * k, rb)
        C[ids] = js[3] + s_n[:, None] * d + ra_n[:, None] * a + rb_n[:, None] * b
        if n != "thumb":
            # thinner back to palm beyond the knuckle (fading in over the first centimetre)
            Q = C[ids] - js[0]
            dd = js[3] - js[0]
            dd /= np.linalg.norm(dd)
            t = smooth01(0.0, 0.012, Q @ dd)
            yb = Q @ b
            mid_b = np.median(yb)
            C[ids] -= ((yb - mid_b) * FINGER_THIN * t)[:, None] * b
    # knuckle bumps over the back (+y) and the thenar pad on the palm (-y)
    bump = np.zeros(len(C))
    for n in ("little", "ring", "middle", "index"):
        for k, (h, rad) in enumerate(((0.0028, 0.011), (0.0014, 0.007))):
            jp = np.array(J[n][k], float)
            dist = np.linalg.norm((C - jp) * np.array((1.0, 0.0, 1.0)), axis=1)
            on_back = np.clip((C[:, 1] - jp[1]) / 0.004, 0, 1)
            bump = np.maximum(bump, h * np.exp(-(dist / rad) ** 2) * on_back)
    C[:, 1] += bump
    t0, t1 = np.array(J["thumb"][0], float), np.array(J["thumb"][1], float)
    pad_c = t0 * 0.55 + t1 * 0.45 + np.array((-0.008, 0.0, -0.004))
    dist = np.linalg.norm((C - pad_c) * np.array((1.0, 0.0, 1.0)), axis=1)
    palm_side = np.clip((pad_c[1] - C[:, 1]) / 0.004, 0, 1)
    C[:, 1] -= THENAR * np.exp(-(dist / 0.022) ** 2) * palm_side
    # the wrist: the outline fit holds the base's wrist loop still, so it stayed the base hand's thin wrist (about
    # 6.6 cm across against the sheet's 9 cm at the knot band) and the forearm met it as a cuff: the loop and the hand's
    # heel widened, fading out by the palm's middle
    loop = np.array(HB["loop"])
    lc = C[loop].mean(0)
    f = 1.0 - smooth01(float(lc[2]), float(lc[2]) + 0.05, C[:, 2])
    C[:, 0] = lc[0] + (C[:, 0] - lc[0]) * (1.0 + (WRIST_WIDEN[0] - 1.0) * f)
    C[:, 1] = lc[1] + (C[:, 1] - lc[1]) * (1.0 + (WRIST_WIDEN[1] - 1.0) * f)
    print("%s HAND shaped: round tips, fingers %.0f%% thinner back to palm, knuckles %.1f mm, thenar %.1f mm" % (
        WHO, FINGER_THIN * 100, 1000 * float(bump.max()), THENAR * 1000))
    HB["C"] = C


def hand_tris_of(faces):
    out = []
    for f in faces:
        for i in range(1, len(f) - 1):
            out.append((f[0], f[i], f[i + 1]))
    return out


def hand_outline_round(sh):
    C, faces = HB["C"], HB["faces"]
    tris = hand_tris_of(faces)
    P2 = to_back_view(C)
    T = np.zeros_like(sh.hands_mask)
    c0, c1 = HAND_BACK_COLS
    T[80:560, c0:c1] = sh.hands_mask[80:560, c0:c1]
    zb, _ = raster(P2, -C[:, 1], tris, T.shape)
    R = np.isfinite(zb)
    N = normals_of(C, tris)
    d2 = np.stack([N[:, 0], -N[:, 2]], 1)
    L = np.linalg.norm(d2, axis=1)
    move = np.zeros_like(C)
    has = np.zeros(len(C), bool)
    h, w = T.shape
    loopset = set(HB["loop"])
    for v in range(len(C)):
        if v in loopset or L[v] < 0.5 or not (85 < P2[v, 1] < 555):
            continue
        p = P2[v]
        dirn = d2[v] / L[v]
        q = p + dirn * 2.0
        if not (0 <= int(q[1]) < h and 0 <= int(q[0]) < w) or R[int(q[1]), int(q[0])]:
            continue
        dist = None
        inside = T[int(p[1]), int(p[0])]
        for k in range(1, 70):
            qq = p + dirn * k if inside else p - dirn * k
            hit = T[min(max(int(qq[1]), 0), h - 1), min(max(int(qq[0]), 0), w - 1)]
            if (inside and not hit) or (not inside and hit):
                dist = (k - 0.5) if inside else -(k - 0.5)
                break
        if dist is None:
            continue
        move[v] = np.array((dirn[0], 0.0, -dirn[1])) * dist * HAND_SX
        has[v] = True
    E = edges_of(faces)
    D = move.copy()
    Wt = has * 3.0
    deg = np.bincount(E.ravel(), minlength=len(C)).astype(float)
    for _ in range(20):
        acc = np.zeros_like(D)
        np.add.at(acc, E[:, 0], D[E[:, 1]])
        np.add.at(acc, E[:, 1], D[E[:, 0]])
        D = (Wt[:, None] * move + acc) / np.maximum(Wt + deg, 1e-9)[:, None]
        D[list(loopset)] = 0.0
    HB["C"] = C + D * 0.7
    return int(has.sum())


def pose_hand(C, J, label, pose):
    """The hand in a pose: the fingers drawn together toward the middle finger, curled at each joint toward the palm;
    the thumb swung in front of the palm and curled. Gives (points, joints)."""
    C = C.copy()
    J = {n: [p.copy() for p in js] for n, js in J.items()}
    up = np.array((0.0, 1.0, 0.0))
    mid_d = J["middle"][3] - J["middle"][0]
    mid_d /= np.linalg.norm(mid_d)
    for n in ("little", "ring", "middle", "index", "thumb"):
        ids = np.where(label == n)[0]
        js = J[n]
        d = js[3] - js[0]
        d /= np.linalg.norm(d)
        if n == "thumb":
            s = (C[ids] - js[0]) @ d
            w = smooth01(-0.01, 0.01, s)
            # swung in toward the fingers and forward of the palm, about its root
            for ax, ang in ((up, -pose["thumb_in"]), (mid_d, pose["thumb_fwd"])):
                # (each turn the way that takes the tip toward the palm's side, -b, or toward the fingers, -a)
                k_ = 1 if ax is mid_d else 0
                test = rot_about(np.array([js[3]]), js[0], ax, 0.1, np.ones(1))[0]
                if (test[k_] - js[3][k_]) * (1 if k_ else 1) > 0:
                    ang = -abs(ang)
                else:
                    ang = abs(ang)
                C[ids] = rot_about(C[ids], js[0], ax, ang, w)
                js = [js[0]] + [rot_about(np.array([p]), js[0], ax, ang, np.ones(1))[0] for p in js[1:]]
            curls = (pose["thumb_curl"],) * 2
            joints_k = (1, 2)
        else:
            if pose["together"]:
                ang = -math.atan2(np.cross(d, mid_d)[1], np.dot(d, mid_d)) * pose["together"]
                s = (C[ids] - js[0]) @ d
                w = smooth01(-0.012, 0.004, s)
                C[ids] = rot_about(C[ids], js[0], up, -ang, w)
                js = [js[0]] + [rot_about(np.array([p]), js[0], up, -ang, np.ones(1))[0] for p in js[1:]]
            curls = pose["curl"][n] if isinstance(pose["curl"], dict) else pose["curl"]
            joints_k = (0, 1, 2)
        for k, ang in reversed(list(zip(joints_k, curls))):
            d = js[3] - js[k]
            d /= np.linalg.norm(d)
            ax = np.cross(d, up)
            ax /= max(np.linalg.norm(ax), 1e-9)
            # (the way that brings the tip toward the palm, -b)
            test = rot_about(np.array([js[3]]), js[k], ax, 0.1, np.ones(1))[0]
            if test[1] > js[3][1]:
                ax = -ax
            s = (C[ids] - js[k]) @ d
            w = smooth01(-0.004, 0.004, s) if k else smooth01(-0.012, 0.004, s)
            C[ids] = rot_about(C[ids], js[k], ax, ang, w)
            js = js[:k + 1] + [rot_about(np.array([p]), js[k], ax, ang, np.ones(1))[0] for p in js[k + 1:]]
        J[n] = js
    if pose.get("thumb_aim"):
        # (seventh round: the relaxed thumb aimed, whatever its swing left it, at a point beside the index finger's
        # first joint, in front of it and on its thumb side, so it lies along the index as a resting hand's does: the
        # swings above only ever turn it by their size, and from the sheet's splayed thumb they left it hanging 6 cm
        # off the index, a pincer)
        ids = np.where(label == "thumb")[0]
        js = J["thumb"]
        fwd_, side_ = pose["thumb_aim"]
        # the index's own frame there: across toward the thumb (+x), out of the palm (-y)
        tgt = J["index"][1] + np.array((side_, -fwd_, 0.0))
        d0 = js[3] - js[0]
        d1 = tgt - js[0]
        d0n, d1n = d0 / np.linalg.norm(d0), d1 / np.linalg.norm(d1)
        axis = np.cross(d0n, d1n)
        sn = float(np.linalg.norm(axis))
        if sn > 1e-6:
            ang = math.atan2(sn, float(np.dot(d0n, d1n)))
            s = (C[ids] - js[0]) @ d0n
            w = smooth01(-0.025, 0.02, s)
            C[ids] = rot_about(C[ids], js[0], axis / sn, ang, w)
            J["thumb"] = [js[0]] + [rot_about(np.array([p]), js[0], axis / sn, ang, np.ones(1))[0] for p in js[1:]]
    return C, J


def hand_silhouettes(sh):
    """The fitted hand's back, palm and thumb-side silhouettes against the sheet's (the thumb side in the sheet's own
    bend): difference pictures and the worst gaps; also keeps where each view lands, for painting (HB["views"])."""
    res = {}
    HB["views"] = {}
    tris = hand_tris_of(HB["faces"])
    for v, (c0, c1), pose in (("back", HAND_BACK_COLS, None), ("palm", (1120, 1700), None), ("thumb", HAND_THUMB_COLS, HAND_POSE_THUMBVIEW)):
        C = HB["flat"]
        if pose:
            C, _ = pose_hand(C, HB["J"], HB["label"], pose)
        u = {"back": C[:, 0], "palm": -C[:, 0], "thumb": C[:, 1]}[v]
        dep = {"back": -C[:, 1], "palm": C[:, 1], "thumb": -C[:, 0]}[v]
        t = HB["tip_mid"]
        if v == "back":
            P2 = to_back_view(C)
        else:
            P2 = np.stack([(c0 + c1) / 2.0 + (u - u[np.argmax(C[:, 2])]) / HAND_SX, HAND_TIP[1] - (C[:, 2] - t[2]) / HAND_SX], 1)
        target = np.zeros_like(sh.hands_mask)
        target[80:560, c0:c1] = sh.hands_mask[80:560, c0:c1]
        zb, _ = raster(P2, dep, tris, target.shape)
        full = np.isfinite(zb)
        mc, tc_ = full[80:560, c0:c1], target[80:560, c0:c1]

        def score(dx, dy):
            s = np.roll(np.roll(mc, dy, 0), dx, 1)
            return float((s & tc_).sum()) / max(float((s | tc_).sum()), 1.0)
        best = (score(0, 0), 0, 0)
        if v != "back":
            for dx in range(-200, 201, 6):
                for dy in range(-30, 31, 6):
                    sc_ = score(dx, dy)
                    if sc_ > best[0]:
                        best = (sc_, dx, dy)
            b0 = best
            for dx in range(b0[1] - 6, b0[1] + 7, 2):
                for dy in range(b0[2] - 6, b0[2] + 7, 2):
                    sc_ = score(dx, dy)
                    if sc_ > best[0]:
                        best = (sc_, dx, dy)
        mm = np.zeros_like(full)
        mm[80:560, c0:c1] = np.roll(np.roll(mc, best[2], 0), best[1], 1)
        # (where a flat point (u across, l along) lands: column = col0 + u / HAND_SX, row = row0 - l / HAND_SX)
        HB["views"][v] = (float(P2[0, 0] + best[1] - u[0] / HAND_SX), float(P2[0, 1] + best[2] + C[0, 2] / HAND_SX))
        r = gaps(mm, target, (80, 560), HAND_SX)
        res[v] = (round(r[0], 2), round(r[1], 2), round(best[0], 3))
        if OUT:
            os.makedirs(OUT, exist_ok=True)
            diff_picture(mm, target, (c0, 70, c1, 570), os.path.join(OUT, "handdiff_%s.png" % v), sh.hands_pix)
    print("BROTHER hand silhouettes (worst cm, 99%% cm, overlap): %s" % json.dumps(res))
    return res


def place_base_hand(M, wrist_ring, side, W, L, joints):
    """The fitted hand, relaxed, put on the arm's end (its frame as hand()'s), its loop bridged to the wrist ring."""
    sfx = "_l" if side > 0 else "_r"
    X = Vector((1, 0, 0))
    F = Vector((0, -1, 0))
    A = (X - L * L.x).normalized()
    tw = math.radians(36.0)
    Tb = A * math.cos(tw) + F * math.sin(tw)
    Wd = -A * math.sin(tw) + F * math.cos(tw)
    C, J = pose_hand(HB["flat"], HB["J"], HB["label"], HAND_POSE_RELAXED)
    Wv, Tv, Lv, Ov = np.array(Wd), np.array(Tb), np.array(L), np.array(W)

    def body(Q):
        Q = np.atleast_2d(Q)
        R = Ov + Q[:, :1] * Wv + Q[:, 1:2] * Tv + Q[:, 2:3] * Lv
        R[:, 0] *= side
        return R
    B = body(C)
    lab = HB["label"]
    base = len(M.P)
    ids = []
    for k, p in enumerate(B):
        ids.append(M.add(p, "hand" + sfx + ("_" + lab[k] if lab[k] else "")))
    M.base_uv = getattr(M, "base_uv", {})
    hf = []
    for f, uv in zip(HB["faces"], HB["uvs"]):
        labs = [lab[v] for v in f]
        fl = max(set(labs), key=labs.count)
        part = "hand" + sfx + ("_" + fl if fl else "")
        M.face([ids[v] for v in f], part)
        M.base_uv[len(M.faces) - 1] = {ids[v]: q for v, q in zip(f, uv)}
        hf.append(len(M.faces) - 1)
    # the bridge to the forearm's last ring
    Wm = np.array(mirror_x(W, side))
    Wd_m, Tb_m = np.array(mirror_x(Wd, side)), np.array(mirror_x(Tb, side))

    def ang(Q):
        return np.arctan2((Q - Wm) @ Wd_m, (Q - Wm) @ Tb_m)
    f0 = len(M.faces)
    zipper(M, [ids[v] for v in HB["loop"]], list(wrist_ring), ang, "hand" + sfx)
    M.tag["wrist_faces" + sfx] = list(range(f0, len(M.faces)))
    M.tag["hand_faces" + sfx] = hf
    M.tag["hand_range" + sfx] = (base, len(M.P))
    M.tag["hand_flat" + sfx] = {ids[k]: HB["flat"][k] for k in range(len(ids))}
    for n in ("little", "ring", "middle", "index", "thumb"):
        joints[n + sfx] = [Vector(p) for p in body(np.array(J[n]))]
    if side > 0:
        th, ix = body(np.array(J["thumb"])), body(np.array(J["index"]))
        print("%s HAND relaxed: thumb tip %s, index joints %s; thumb tip to the index's first joint %.1f cm" % (
            WHO, np.round(th[3], 3), np.round(ix[:3], 3).tolist(), 100 * float(np.linalg.norm(th[3] - ix[1]))))
    tb_thumb = np.cross(J["thumb"][3] - J["thumb"][0], np.array((0.0, 0.0, 1.0)))
    joints["thumb_back" + sfx] = body(np.array([tb_thumb]))[0] - body(np.zeros((1, 3)))[0]
    joints["hand_frame" + sfx] = tuple(np.array(mirror_x(v, side)) for v in (Tb, Wd, L))
    joints["knuckles" + sfx] = Vector(body(np.array([J["middle"][0]]))[0])


# ------------------------------------------------------------------------------------------------------------------
# Geometry helpers on the Mesh
# ------------------------------------------------------------------------------------------------------------------

def normals_of(P, tris):
    P = np.asarray(P)
    T = np.asarray(tris)
    fn = np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]])
    N = np.zeros_like(P)
    for i in range(3):
        np.add.at(N, T[:, i], fn)
    n = np.linalg.norm(N, axis=1, keepdims=True)
    return N / np.maximum(n, 1e-12)


def edges_of(faces):
    e = set()
    for f in faces:
        for i in range(len(f)):
            a, b = f[i], f[(i + 1) % len(f)]
            e.add((min(a, b), max(a, b)))
    return np.array(sorted(e))


def mirror_map(P):
    """For each point, the point at its mirror image across x = 0 (itself on the middle line)."""
    P = np.asarray(P)
    kd = kdtree.KDTree(len(P))
    for i, p in enumerate(P):
        kd.insert(Vector(p), i)
    kd.balance()
    mir = np.arange(len(P))
    for i, p in enumerate(P):
        q, j, d = kd.find(Vector((-p[0], p[1], p[2])))
        if d < 1e-4:
            mir[i] = j
    return mir


def face_normal(P, f):
    p = [np.asarray(P[i]) for i in f]
    n = np.zeros(3)
    for i in range(1, len(p) - 1):
        n += np.cross(p[i] - p[0], p[i + 1] - p[0])
    return n


def fix_winding(M):
    """Turns faces to face outward: the open shells' faces to the way each was given, the closed body's by
    Blender's own normal recalculation (which needs a closed surface)."""
    flipped = 0
    for i, want in M.want.items():
        f = M.faces[i]
        c = np.mean([M.P[j] for j in f], axis=0)
        w = want(c) if callable(want) else want
        if np.dot(face_normal(M.P, f), w) < 0:
            M.faces[i] = f[::-1]
            flipped += 1
    rest = [i for i in range(len(M.faces)) if i not in M.want]
    me = bpy.data.meshes.new("_wind")
    me.from_pydata([tuple(p) for p in M.P], [], [M.faces[i] for i in rest])
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.faces.ensure_lookup_table()
    for f, i in zip(bm.faces, rest):
        vs = [v.index for v in f.verts]
        if vs != M.faces[i]:
            flipped += 1
            M.faces[i] = vs
    bm.free()
    bpy.data.meshes.remove(me)
    return flipped


def open_edges(faces):
    count = {}
    for f in faces:
        for i in range(len(f)):
            e = (min(f[i], f[(i + 1) % len(f)]), max(f[i], f[(i + 1) % len(f)]))
            count[e] = count.get(e, 0) + 1
    return [e for e, c in count.items() if c != 2]

# ------------------------------------------------------------------------------------------------------------------
# Fitting to the sheet's outlines
# ------------------------------------------------------------------------------------------------------------------

FIT_VIEWS = {
    "front": ("torso", "shoulder", "arm", "hand", "leg", "foot"),
    "back": ("torso", "shoulder", "arm", "hand", "leg", "foot"),
    "side": ("torso", "leg", "foot"),
}
FIT_REACH = 32          # pixels a point may be moved in one round
FIT_DAMP = 0.75


def part_family(part):
    return part.split("_")[0]


def with_caps(M, P, tris):
    """The arms' holes closed (a fan from each hole's middle), for drawing him without his arms (the sheet's side
    view has none)."""
    P = np.asarray(P)
    extra = []
    tris = list(tris)
    # (the hole as it is now: the open loop of the faces that are not arm or hand nearest the hole's first ring; once
    # refine_forms has split the torso's faces, the first ring alone leaves slivers open round the cap, and those
    # slivers' outlines were counted as side-view gaps of 9 to 13 cm)
    loops = []
    if len(P) == len(M.P):
        body = [f for f, p in zip(M.faces, M.fpart) if part_family(p) not in ("arm", "hand", "ear")]
        loops = [lp for lp in open_loops(body) if len(lp) >= 6]
    for sfx in ("_l", "_r"):
        ring = M.tag["hole" + sfx]
        if loops:
            c0 = P[ring].mean(0)
            best = min(loops, key=lambda lp: np.linalg.norm(P[lp].mean(0) - c0))
            if np.linalg.norm(P[best].mean(0) - c0) < 0.05:
                ring = best
        c = len(P) + len(extra)
        extra.append(P[ring].mean(0))
        for j in range(len(ring)):
            tris.append((ring[j], ring[(j + 1) % len(ring)], c))
    return np.concatenate([P, np.array(extra)]), tris


def fit_round(M, sh, frozen):
    P = np.array(M.P)
    tris = M.tris()
    N = normals_of(P, tris)
    fams = np.array([part_family(p) for p in M.part])
    move = np.zeros_like(P)
    count = np.zeros(len(P))
    T_body = sh.body_target
    for view, allowed in FIT_VIEWS.items():
        keep_tris = tris
        Pr = P
        if view == "side":
            tf = M.tri_fams()
            keep_tris = [t for t, f in zip(tris, tf) if f not in ("arm", "hand")]
            Pr, keep_tris = with_caps(M, P, keep_tris)
        P2, dep = project(view, Pr)
        zb, _ = raster(P2, dep, keep_tris, T_body.shape)
        P2, dep = P2[:len(P)], dep[:len(P)]
        R = np.isfinite(zb)
        d2, facing = screen_dir(view, N)
        L = np.linalg.norm(d2, axis=1)
        ok = np.isin(fams, allowed) & (np.abs(facing) < 0.55) & (L > 0.4) & ~frozen
        if view != "side":
            # (where the arm lies against him the sheet shows no side of the torso: not fitted there)
            under_arm = (fams == "torso") & (P[:, 2] > body_z(565)) & (P[:, 2] < body_z(355))
            ok &= ~under_arm
        else:
            # (the side view's back from the shoulder to the waist is his arm: the torso there keeps SIDE_BACK)
            behind_arm = (fams == "torso") & (P[:, 2] > body_z(690)) & (P[:, 2] < body_z(360)) & (N[:, 1] > 0.2)
            ok &= ~behind_arm
        idx = np.where(ok)[0]
        d2n = d2[idx] / L[idx, None]
        h, w = T_body.shape
        for ii, v in enumerate(idx):
            p = P2[v]
            dirn = d2n[ii]
            q = p + dirn * 3.0
            qi = (int(q[1]), int(q[0]))
            if not (0 <= qi[0] < h and 0 <= qi[1] < w) or R[qi]:
                continue
            pi = (int(p[1]), int(p[0]))
            if not (0 <= pi[0] < h and 0 <= pi[1] < w):
                continue
            dist = None
            if T_body[pi]:
                for k in range(1, FIT_REACH + 1):
                    qq = p + dirn * k
                    if not T_body[min(max(int(qq[1]), 0), h - 1), min(max(int(qq[0]), 0), w - 1)]:
                        dist = k - 0.5
                        break
            else:
                for k in range(1, FIT_REACH + 1):
                    qq = p - dirn * k
                    if T_body[min(max(int(qq[1]), 0), h - 1), min(max(int(qq[0]), 0), w - 1)]:
                        dist = -(k - 0.5)
                        break
            if dist is None:
                continue
            wd = world_dir(view, dirn[None, :])[0]
            move[v] += wd * dist * S
            count[v] += 1
    has = count > 0
    move[has] /= count[has, None]
    # spread the moves to the neighbours: a smooth field that keeps the moved points' moves
    E = edges_of(M.faces)
    D = move.copy()
    W = has.astype(float) * 4.0
    deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
    for _ in range(40):
        acc = np.zeros_like(D)
        np.add.at(acc, E[:, 0], D[E[:, 1]])
        np.add.at(acc, E[:, 1], D[E[:, 0]])
        D = (W[:, None] * move + acc) / np.maximum(W + deg, 1e-9)[:, None]
    D[frozen] = 0.0
    P += D * FIT_DAMP
    M.P = [p for p in P]
    return int(has.sum()), float(np.abs(move[has]).max() if has.any() else 0.0)


def relax(M, frozen, amount=0.25, rounds=2):
    """Evens the points out along the surface (the change across the surface taken out), keeping the shape."""
    P = np.array(M.P)
    E = edges_of(M.faces)
    deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
    for _ in range(rounds):
        N = normals_of(P, M.tris())
        acc = np.zeros_like(P)
        np.add.at(acc, E[:, 0], P[E[:, 1]])
        np.add.at(acc, E[:, 1], P[E[:, 0]])
        avg = acc / np.maximum(deg, 1)[:, None]
        d = avg - P
        d[deg == 0] = 0.0
        d -= N * (d * N).sum(1, keepdims=True)
        d[frozen] = 0.0
        P += d * amount
    M.P = [p for p in P]


def symmetrize(M, mir):
    P = np.array(M.P)
    Q = P[mir].copy()
    Q[:, 0] *= -1
    alone = mir == np.arange(len(P))
    P = np.where(alone[:, None], P, (P + Q) / 2.0)
    # (a point with no mirror image is left as it is, unless it lies on the middle line: averaging it with its own
    # reflection put it on the middle line, which pinched the head into bands)
    P[alone & (np.abs(P[:, 0]) < 2e-3), 0] = 0.0
    M.P = [p for p in P]

# ------------------------------------------------------------------------------------------------------------------
# Overlays: the model drawn half-clear and as an outline over each view of the sheet, and how far apart they are
# ------------------------------------------------------------------------------------------------------------------

def outline_of(mask):
    e = mask & ~(np.roll(mask, 1, 0) & np.roll(mask, -1, 0) & np.roll(mask, 1, 1) & np.roll(mask, -1, 1))
    return e


def save_rgb(path, rgb):
    rgb = np.clip(np.asarray(rgb, dtype=np.float32), 0, 1)
    h, w = rgb.shape[:2]
    if rgb.shape[2] == 3:
        rgb = np.concatenate([rgb, np.ones((h, w, 1), np.float32)], 2)
    img = bpy.data.images.new(os.path.basename(path), w, h, alpha=True)
    img.pixels.foreach_set(rgb[::-1].ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def boundary_distance(model, target, rows=None):
    """For each pixel of the model's outline, how far (pixels) to the target's outline; gives the distances and the
    outline pixels."""
    mo = outline_of(model)
    to = outline_of(target)
    if rows is not None:
        keep = np.zeros(model.shape[0], bool)
        keep[rows[0]:rows[1]] = True
        mo &= keep[:, None]
    ty, tx = np.where(to)
    kd = kdtree.KDTree(len(ty))
    for i in range(len(ty)):
        kd.insert((float(tx[i]), float(ty[i]), 0.0), i)
    kd.balance()
    my, mx = np.where(mo)
    d = np.array([kd.find((float(mx[i]), float(my[i]), 0.0))[2] for i in range(len(my))])
    return d, my, mx


def overlay(objs_tris, sh, round_name, report=True):
    """objs_tris: list of (points, triangles, family per point). Draws each body view and the head views."""
    if not OUT:
        return {}
    os.makedirs(OUT, exist_ok=True)
    result = {}
    for view in ("front", "side", "back"):
        P = np.concatenate([o[0] for o in objs_tris])
        tris = []
        off = 0
        for pts, tr, fam in objs_tris:
            for ti, t in enumerate(tr):
                if view == "side" and fam[ti] in ("arm", "hand"):
                    continue
                if view != "side" and fam[ti] == "sidecap":
                    continue
                tris.append((t[0] + off, t[1] + off, t[2] + off))
            off += len(pts)
        P2, dep = project(view, P)
        zb, tid = raster(P2, dep, tris, sh.body_mask.shape)
        model = np.isfinite(zb)
        # shade it as lit from the front
        N = normals_of(P, tris)
        _, facing = screen_dir(view, N)
        T = np.asarray(tris)
        shade_t = 0.3 + 0.7 * np.clip(facing[T].mean(1), 0, 1)
        shade = np.where(model, shade_t[np.maximum(tid, 0)], 0.0)
        c0, c1 = SPAN[view]
        r0, r1 = 60, 1500
        pic = sh.body_pix[r0:r1, c0:c1].copy()
        mm = model[r0:r1, c0:c1]
        tint = np.stack([shade * 0.75, shade * 0.85, shade * 1.0], -1)[r0:r1, c0:c1]
        half = np.where(mm[..., None], pic * 0.5 + tint * 0.5, pic)
        mo = outline_of(model)[r0:r1, c0:c1]
        to = outline_of(sh.body_target)[r0:r1, c0:c1]
        half[to] = (0.1, 0.75, 0.2)
        half[mo] = (0.95, 0.1, 0.1)
        save_rgb(os.path.join(OUT, "overlay_%s_%s.png" % (round_name, view)), half)
        # the outline alone over the sheet
        line = pic.copy()
        for dy in (0, 1):
            for dx in (0, 1):
                line[np.roll(np.roll(mo, dy, 0), dx, 1)] = (0.95, 0.1, 0.1)
        save_rgb(os.path.join(OUT, "outline_%s_%s.png" % (round_name, view)), line)
        if report:
            d, my, mx = boundary_distance(model, sh.body_target)
            # where on him: head (above the beard's bottom), boxers, the rest
            head = my < CHIN
            box = (my >= BOXERS[0]) & (my < BOXERS[1])
            rest = ~head & ~box
            def stats(sel):
                if not sel.any():
                    return (0.0, 0.0)
                return (float(np.percentile(d[sel], 99)) * S * 100, float(d[sel].max()) * S * 100)
            result[view] = {"body_99cm": stats(rest), "boxers_99cm": stats(box), "head_99cm": stats(head)}
            worst = np.argmax(np.where(rest, d, 0))
            result[view]["body_worst_at"] = (int(mx[worst]), int(my[worst]))
    return result


def head_overlay(objs_tris, sh):
    """The head with its hair over the head sheet's front, side and back views: half-clear, his outline red, the
    sheet's green (fifth round: the beard's width and profile are checked against these)."""
    if not OUT:
        return
    for view in ("head_front", "head_side", "head_back"):
        P = np.concatenate([o[0] for o in objs_tris])
        tris, off = [], 0
        for pts, tr, fam in objs_tris:
            for ti, t in enumerate(tr):
                if fam[ti] in ("arm", "hand", "sidecap", "leg", "foot"):
                    continue
                tris.append((t[0] + off, t[1] + off, t[2] + off))
            off += len(pts)
        P2, dep = project(view, P)
        zb, tid = raster(P2, dep, tris, sh.head_mask.shape)
        model = np.isfinite(zb)
        c0, c1 = HEAD_SPAN[view[5:]]
        r0, r1 = 90, 430
        pic = sh.head_pix[r0:r1, c0:c1].copy()
        mm = model[r0:r1, c0:c1]
        half = np.where(mm[..., None], pic * 0.55 + np.array((0.2, 0.25, 0.45)) * 0.45, pic)
        half[outline_of(sh.head_mask)[r0:r1, c0:c1]] = (0.1, 0.75, 0.2)
        half[outline_of(model)[r0:r1, c0:c1]] = (0.95, 0.1, 0.1)
        save_rgb(os.path.join(OUT, "overlay_%s.png" % view), half)

# ------------------------------------------------------------------------------------------------------------------
# The head fitted to the bald row's five views, and the silhouettes compared (the user: "make sure you are matching
# pose silhouettes aggressively"). Each view: the model's head drawn as a filled shape from that view's angle against
# the sheet's head, the outline points of the model moved onto the sheet's outline (as the body's are), five views at
# once, kept symmetrical; then the difference pictures and the worst gaps.
# ------------------------------------------------------------------------------------------------------------------

HEAD_FIT_ROUNDS = 8


def head_tris(M, fams=("head", "nose", "ear", "neck")):
    return [t for t, f in zip(M.tris(), M.tri_fams()) if f in fams]


def fill_holes(mask):
    """The mask with every background region that does not reach the picture's edge filled; and how many pixels."""
    ys, xs = np.where(mask)
    if not len(ys):
        return mask, 0
    r0, r1, c0, c1 = max(ys.min() - 2, 0), ys.max() + 3, max(xs.min() - 2, 0), xs.max() + 3
    sub = mask[r0:r1, c0:c1]
    out = np.zeros_like(sub)
    out[0, :] = ~sub[0, :]
    out[-1, :] = ~sub[-1, :]
    out[:, 0] = ~sub[:, 0]
    out[:, -1] = ~sub[:, -1]
    while True:
        g = out.copy()
        g[1:] |= out[:-1]
        g[:-1] |= out[1:]
        g[:, 1:] |= out[:, :-1]
        g[:, :-1] |= out[:, 1:]
        g &= ~sub
        if (g == out).all():
            break
        out = g
    filled = mask.copy()
    filled[r0:r1, c0:c1] = ~out
    return filled, int((filled & ~mask).sum())


def head_target(sh, view):
    """The sheet's head in one view: its figure within the view's columns and the compared rows."""
    _, mid, (c0, c1) = HEAD_VIEWS[view]
    t = np.zeros_like(sh.head_mask)
    r0, r1 = HEAD_ROWS_SEEN
    t[r0:r1, c0:c1] = sh.head_mask[r0:r1, c0:c1]
    return t


def head_silhouette(M, view, P=None, fams=("head", "nose", "ear", "neck")):
    P = np.array(M.P) if P is None else P
    P2, dep = project("head_" + view, P)
    zb, _ = raster(P2, dep, head_tris(M, fams), (1536, 2752))
    m = np.isfinite(zb)
    r0, r1 = HEAD_ROWS_SEEN
    m[:r0] = False
    m[r1:] = False
    return m


def align_head_views(M, sh, views=("q", "qb"), spread=12.0, step=3.0):
    """The angled views' own angle and middle column: the angle (within `spread` degrees of the given one) and the
    shift whose model silhouette overlaps the sheet's best (its share of the two together)."""
    for v in views:
        target = head_target(sh, v)
        a0 = HEAD_VIEWS[v][0]
        best = None
        for a in np.arange(a0 - spread, a0 + spread + 0.1, step):
            HEAD_VIEWS[v][0] = float(a)
            m = head_silhouette(M, v)
            for dx in range(-60, 61, 2):
                s = np.roll(m, dx, 1)
                both = float((s & target).sum())
                iou = both / max(float((s | target).sum()), 1.0)
                if best is None or iou > best[0]:
                    best = (iou, float(a), dx)
        HEAD_VIEWS[v][0] = best[1]
        HEAD_VIEWS[v][1] += best[2]
        print("BROTHER head view %s: %.0f degrees, middle %.0f, overlap %.3f" % (v, best[1], HEAD_VIEWS[v][1], best[0]))


def fit_head_round(M, sh, frozen, views=("front", "q", "side", "qb", "back")):
    P = np.array(M.P)
    tris = head_tris(M)
    N = normals_of(P, M.tris())
    fams = np.array([part_family(p) for p in M.part])
    move = np.zeros_like(P)
    count = np.zeros(len(P))
    for view in views:
        T = head_target(sh, view)
        P2, dep = project("head_" + view, P)
        zb, _ = raster(P2, dep, tris, T.shape)
        R = np.isfinite(zb)
        d2, facing = screen_dir("head_" + view, N)
        L = np.linalg.norm(d2, axis=1)
        rows = P2[:, 1]
        # (the angled views move only the points on their own outline, not the face turned toward them: their outline
        # crosses the face, and pulling the face to it laid ripples across it ring by ring)
        ok = (fams == "head") & (np.abs(facing) < (0.55 if view in ("front", "side", "back") else 0.25)) & (L > 0.4) & ~frozen
        ok &= (rows > HEAD_ROWS_SEEN[0]) & (rows < HEAD_ROWS_SEEN[1] - 6)
        # (the face under the nose is not pulled out to the nose's outline: the nose is its own shell)
        ok &= ~((rows > FACE_PLANE[0] - 6) & (rows < FACE_PLANE[1] + 6) & (np.abs(P[:, 0]) < 0.04) & (P[:, 1] < -0.04))
        # (nor the skull's sides to the ears' outline, where the ears stand out of it)
        if view != "side":
            ok &= ~((rows > EAR_ROWS[0] - 8) & (rows < EAR_ROWS[1] + 8) & (np.abs(P[:, 0]) > 0.045))
        idx = np.where(ok)[0]
        h, w = T.shape
        for v in idx:
            p = P2[v]
            dirn = d2[v] / L[v]
            q = p + dirn * 3.0
            qi = (int(q[1]), int(q[0]))
            if not (0 <= qi[0] < h and 0 <= qi[1] < w) or R[qi]:
                continue
            pi = (int(p[1]), int(p[0]))
            dist = None
            if T[pi]:
                for k in range(1, 40):
                    qq = p + dirn * k
                    if not T[min(max(int(qq[1]), 0), h - 1), min(max(int(qq[0]), 0), w - 1)]:
                        dist = k - 0.5
                        break
            else:
                for k in range(1, 40):
                    qq = p - dirn * k
                    if T[min(max(int(qq[1]), 0), h - 1), min(max(int(qq[0]), 0), w - 1)]:
                        dist = -(k - 0.5)
                        break
            if dist is None:
                continue
            move[v] += world_dir("head_" + view, dirn[None, :])[0] * dist * HEAD_SX
            count[v] += 1
    has = count > 0
    move[has] /= count[has, None]
    E = edges_of(M.faces)
    D = move.copy()
    Wt = has.astype(float) * 4.0
    deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
    for _ in range(30):
        acc = np.zeros_like(D)
        np.add.at(acc, E[:, 0], D[E[:, 1]])
        np.add.at(acc, E[:, 1], D[E[:, 0]])
        D = (Wt[:, None] * move + acc) / np.maximum(Wt + deg, 1e-9)[:, None]
    D[frozen | (fams != "head")] = 0.0
    P += D * 0.8
    M.P = [p for p in P]
    return int(has.sum()), float(np.abs(move[has]).max() if has.any() else 0.0)


def cut_edge(mask, view, rows, side):
    """The view's outline on one side (side -1 its left, +1 its right) taken straight between two rows (where the
    nose or an ear stands out of the head's own outline): the figure beyond that line, in those rows, cleared."""
    _, mid, (c0, c1) = HEAD_VIEWS[view]
    r0, r1 = rows

    def edge(r):
        run = run_near(mask, r, mid, c0, c1)
        return run[1] + 1 if side > 0 else run[0]
    e0, e1 = edge(r0), edge(r1)
    for r in range(r0 + 1, r1):
        e = e0 + (e1 - e0) * (r - r0) / float(r1 - r0)
        if side > 0:
            mask[r, int(math.ceil(e)):c1] = False
        else:
            mask[r, c0:int(math.floor(e))] = False


def envelope_edge(mask, view, rows, side, win=25, soft=9):
    """The view's outline on one side, over some rows, filled out to its outer envelope (the most outward edge within
    `win` rows, then softened): so the profile's hollows (between the brows and the nose, under the nose, under the
    lower lip) are not carved across the whole width of the face. Those hollows are the face's forms, sculpted where
    they are (FACE_FORMS)."""
    _, mid, (c0, c1) = HEAD_VIEWS[view]
    r0, r1 = rows
    edges = []
    for r in range(r0, r1):
        run = run_near(mask, r, mid, c0, c1)
        edges.append(run[1] + 1 if side > 0 else run[0])
    e = np.array(edges, float)
    h = win // 2
    if side > 0:
        env = np.array([e[max(0, i - h):i + h + 1].max() for i in range(len(e))])
    else:
        env = np.array([e[max(0, i - h):i + h + 1].min() for i in range(len(e))])
    k = np.ones(soft) / soft
    env = np.convolve(np.pad(env, soft // 2, mode="edge"), k, "valid")
    env = np.maximum(env, e) if side > 0 else np.minimum(env, e)
    for i, r in enumerate(range(r0, r1)):
        run = run_near(mask, r, mid, c0, c1)
        if side > 0:
            mask[r, run[0]:int(round(env[i]))] = True
        else:
            mask[r, int(round(env[i])):run[1] + 1] = True


def hull_masks(sh):
    """Each head view's figure with the nose and the ears taken out of its outline (they are shells of their own),
    for carving the head."""
    out = {}
    for v in HEAD_VIEWS:
        m = head_target(sh, v)
        if v in ("front", "back"):
            cut_edge(m, v, EAR_HIDES, -1)
            cut_edge(m, v, EAR_HIDES, 1)
        if v == "side":
            cut_edge(m, v, (FACE_PLANE[0] - 2, FACE_PLANE[1] + 2), 1)
            envelope_edge(m, v, (975, HEAD_ROWS_SEEN[1]), 1)
        if v == "q":
            cut_edge(m, v, (FACE_PLANE[0] - 2, FACE_PLANE[1] + 2), 1)
            envelope_edge(m, v, (975, HEAD_ROWS_SEEN[1]), 1)
            cut_edge(m, v, EAR_HIDES, -1)
        if v == "qb":
            cut_edge(m, v, EAR_HIDES, 1)
        out[v] = m
    return out


def inside_hull(masks, P):
    """Whether each point (and its mirror image across the middle: the head is symmetrical, and the angled views see
    his right side only) falls within every view's figure."""
    ok = np.ones(len(P), bool)
    for v, m in masks.items():
        for s in (1.0, -1.0):
            Q = P.copy()
            Q[:, 0] *= s
            q2, _ = project("head_" + v, Q)
            c = np.clip(q2[:, 0].astype(int), 0, m.shape[1] - 1)
            # (below the compared rows, the five views' shoulders meet: a point there is held to the lowest row's
            # figure, the jaw's)
            r = np.clip(q2[:, 1].astype(int), 0, HEAD_ROWS_SEEN[1] - 3)
            ok &= m[r, c]
    return ok


def carve_head(M, sh):
    """Every head ring's points set where the five views' figures, taken together, end along that point's direction
    from the ring's middle (the head's visual hull, sampled on the rings): the chin narrows in front of the jaw's
    angles, the jaw runs down and forward, the skull rounds to the crown as the views draw them."""
    masks = hull_masks(sh)
    H = M.tag["head_rings"]
    for ring in H:
        Pr = np.array([M.P[v] for v in ring])
        z = float(Pr[:, 2].mean())
        cy = float(Pr[:, 1].min() + (Pr[:, 1].max() - Pr[:, 1].min()) * 0.45)
        n = len(ring)
        th = np.array([math.tau * k / n for k in range(n)])
        d = np.stack([np.sin(th), -np.cos(th), np.zeros(n)], 1)
        c = np.array((0.0, cy, z))
        lo, hi = np.zeros(n), np.full(n, 0.2)
        for _ in range(22):
            midr = (lo + hi) / 2.0
            ok = inside_hull(masks, c + d * midr[:, None])
            lo = np.where(ok, midr, lo)
            hi = np.where(ok, hi, midr)
        for k, v in enumerate(ring):
            M.P[v] = c + d[k] * lo[k]


# The jaw (the coordinator, from the user's word on the captain: "why is his jaw just straight flat across?"): the
# mandible's lower edge is a slanted line, from its angle under the ear lobe down and forward to the chin's bottom;
# under it the surface turns back to the throat, and the neck is a column of its own under and behind the jaw. Read
# off the bald side view: the jaw's angle and the chin's bottom (columns, rows), and the neck's column just under the
# jaw (its front and back, side view, and its half width, front view).
JAW_ANGLE = (1418.0, 1190.0)
CHIN_BOTTOM = (1572.0, 1244.0)
NECK_ROW = 1268
NECK_HALF = 0.079 * K_HEAD             # metres: as wide as the jaw (the front view draws a thick neck straight down from it)


def sculpt_jaw(M, sh):
    """The head's points under the mandible's line drawn into the neck's column (an ellipse round the neck's axis),
    fully from 1.2 cm under the line: the jaw's edge as a crease, the under-jaw turning back to the throat."""
    m = sh.head_mask
    _, smid, (s0, s1) = HEAD_VIEWS["side"]
    run = run_near(m, NECK_ROW, smid, s0, s1)
    yf = -(run[1] + 1 - smid) * HEAD_SX
    yb = -(run[0] - smid) * HEAD_SX
    cy, dy = (yf + yb) / 2.0, (yb - yf) / 2.0
    ya, za = -(JAW_ANGLE[0] - smid) * HEAD_SX, float(head_z(JAW_ANGLE[1]))
    yc, zc = -(CHIN_BOTTOM[0] - smid) * HEAD_SX, float(head_z(CHIN_BOTTOM[1]))
    fams = np.array([part_family(p) for p in M.part])
    P = np.array(M.P)
    moved = 0
    for i in np.where(fams == "head")[0]:
        x, y, z = P[i]
        # (the line's height at this point's depth; behind the angle it carries on level, in front of the chin too)
        t = float(np.clip((y - yc) / (ya - yc), 0.0, 1.0))
        zl = zc + (za - zc) * t
        under = zl - z
        if under <= 0.0:
            continue
        k = float(smooth01(0.0, 0.012, under))
        ex, ey = x / NECK_HALF, (y - cy) / dy
        r = math.hypot(ex, ey)
        if r <= 1.0:
            continue
        P[i] = (x / r * k + x * (1 - k), (cy + (y - cy) / r) * k + y * (1 - k), z)
        moved += 1
    M.P = [p for p in P]
    print("BROTHER jaw: %d points drawn into the neck under the mandible's line" % moved)


def fit_head(M, sh):
    """The head carved to the five views together (carve_head), the angled views' own angle and middle found against
    it and the head carved again; evened out, kept symmetrical."""
    head_silhouettes(M, sh, "h0")
    mir = mirror_map(M.P)
    for rnd in range(3):
        carve_head(M, sh)
        symmetrize(M, mir)
        if rnd < 2:
            align_head_views(M, sh, spread=12.0 if rnd == 0 else 4.0, step=3.0 if rnd == 0 else 1.0)
    # (the carved rings evened out: the figures' pixel steps are not forms)
    smooth_head(M, rounds=3)
    sculpt_jaw(M, sh)
    smooth_head(M, rounds=1)
    symmetrize(M, mir)
    head_silhouettes(M, sh, "carved")


GAP_AT = []


def gaps(model, target, rows, scale, skip=None):
    """The worst and the 99th-percentile distance (cm) between the two outlines, both ways, over the rows given;
    `skip` a mask of outline pixels left out (a cut edge, a part not modelled)."""
    keep = np.zeros(model.shape[0], bool)
    keep[rows[0] + 3:rows[1] - 3] = True
    mo = outline_of(model) & keep[:, None]
    to = outline_of(target) & keep[:, None]
    if skip is not None:
        mo &= ~skip
        to &= ~skip
    out = []
    for a, b in ((mo, to), (to, mo)):
        by, bx = np.where(b)
        if not len(by):
            return 0.0, 0.0
        kd = kdtree.KDTree(len(by))
        for i in range(len(by)):
            kd.insert((float(bx[i]), float(by[i]), 0.0), i)
        kd.balance()
        ay, ax = np.where(a)
        dd = np.array([kd.find((float(ax[i]), float(ay[i]), 0.0))[2] for i in range(len(ay))])
        out.append(dd)
        # (where each way's worst gap is: (column, row) on the outline it is measured from)
        GAP_AT.append((int(ax[int(np.argmax(dd))]), int(ay[int(np.argmax(dd))]), round(float(dd.max()) * scale * 100, 2)))
    d = np.concatenate(out)
    return float(d.max()) * scale * 100, float(np.percentile(d, 99)) * scale * 100


def diff_picture(model, target, box, path, back=None):
    """Red where only the model is, cyan where only the sheet is, grey where both; over `back` faintly."""
    c0, r0, c1, r1 = box
    m, t = model[r0:r1, c0:c1], target[r0:r1, c0:c1]
    img = np.ones(m.shape + (3,)) * 0.97
    if back is not None:
        img = img * 0.75 + back[r0:r1, c0:c1] * 0.25
    img[m & t] = (0.62, 0.62, 0.64)
    img[m & ~t] = (0.92, 0.15, 0.12)
    img[t & ~m] = (0.05, 0.75, 0.9)
    save_rgb(path, img)


def head_silhouettes(M, sh, tag):
    """Every head view's difference picture (to --out) and its worst gaps; gives {view: (worst cm, 99% cm)}."""
    res = {}
    for v in HEAD_VIEWS:
        # (seventh round: the torso's top is drawn too. Since the head was scaled up and sunk into the shoulders
        # (K_HEAD), the torso's top ring stands above the compared rows' bottom at the throat, so the head and neck
        # alone left a notch there 6 cm behind the sheet's throat, which the side view's worst gap measured: 5.8 cm
        # was that notch, not the head's outline)
        m = head_silhouette(M, v, fams=("head", "nose", "ear", "neck", "torso"))
        t = head_target(sh, v)
        # (seventh round: holes in either figure (a dark line drawn inside the sheet's neck, a gap in the model's
        # raster) filled before measuring, so only the outlines are compared; how many pixels each filled is printed)
        t, th = fill_holes(t)
        m, mh = fill_holes(m)
        if th or mh:
            print("%s head %s: holes filled before measuring, sheet %d px, model %d px" % (WHO, v, th, mh))
        del GAP_AT[:]
        # (seventh round: the side view's 5.8 cm was found at (1502, 1236): the model's chin underside, 8 px above the
        # sheet's (row 1244, below the compared rows), measured against the sheet's throat 98 px off, because the cut
        # at row 1240 fell between the two undersides. The compared rows now stop 14 px above the chin (HEAD_CHIN), so
        # both undersides are out of them alike; the chin itself is measured as a landmark (head_landmarks))
        r = gaps(m, t, (HEAD_ROWS_SEEN[0], int(HEAD_CHIN) - 14), HEAD_SX)
        res[v] = (round(r[0], 2), round(r[1], 2))
        if tag == "final":
            print("%s head %s: worst gaps at (column, row, cm), model to sheet and sheet to model: %s" % (WHO, v, GAP_AT))
        if OUT:
            os.makedirs(OUT, exist_ok=True)
            _, mid, (c0, c1) = HEAD_VIEWS[v]
            diff_picture(m, t, (c0, HEAD_ROWS_SEEN[0] - 10, c1, HEAD_ROWS_SEEN[1] + 10),
                         os.path.join(OUT, "headdiff_%s_%s.png" % (tag, v)), sh.head_pix)
    print("BROTHER head silhouettes %s (worst cm, 99%% cm): %s" % (tag, json.dumps(res)))
    return res


def head_landmarks(M, sh):
    """Landmarks on the bald row against the model's (cm apart): in the side view the nose's tip, the brow's front,
    the lips' front and the chin's front (the outline's furthest point forward in their rows), the ear's lobe (the
    ear's lowest point); in the front view the ears' outer edge and the jaw's width at its angle and at the chin."""
    out = {}
    side_s = head_target(sh, "side")
    side_m = head_silhouette(M, "side")
    front_s = head_target(sh, "front")
    front_m = head_silhouette(M, "front")

    def forward(mask, rows):
        best = None
        for r in range(*rows):
            cols = np.where(mask[r])[0]
            if len(cols) and (best is None or cols.max() > best[0]):
                best = (cols.max(), r)
        return best

    for name, rows in (("nose tip", HEAD_PROFILE_ROWS["tip"]), ("brow", HEAD_PROFILE_ROWS["brow"]),
                       ("lips", HEAD_PROFILE_ROWS["lips"]), ("chin", HEAD_PROFILE_ROWS["chin"])):
        a, b = forward(side_s, rows), forward(side_m, rows)
        out[name] = round(math.hypot(a[0] - b[0], a[1] - b[1]) * HEAD_SX * 100, 2)

    def width(mask, r):
        cols = np.where(mask[r])[0]
        return cols.min(), cols.max()
    for name, r in zip(("ears' width", "jaw at its angle", "jaw by the chin"), HEAD_WIDTH_ROWS):
        a, b = width(front_s, r), width(front_m, r)
        out[name] = round(max(abs(a[0] - b[0]), abs(a[1] - b[1])) * HEAD_SX * 100, 2)
    # the ear's lobe: the sheet's (side view: the lowest ear pixel, read off the sheet) against the model's ear's lowest
    # point projected into the side view
    ear_r = M.tag.get("ear_r") or [i for i, p in enumerate(M.part) if p == "ear_r"]
    P = np.array(M.P)
    q2, _ = project("head_side", P[ear_r])
    lo = q2[np.argmax(q2[:, 1])]
    out["ear lobe"] = round(math.hypot(lo[0] - EAR_LOBE[0], lo[1] - EAR_LOBE[1]) * HEAD_SX * 100, 2)
    print("BROTHER head landmarks, sheet to model (cm): %s" % json.dumps(out))
    return out


def body_silhouettes(objs_tris, sh, tag):
    """The body's front, side and back against the body sheet (its shorts eased in, as the fitting's target), below
    the chin; the side view's back from the shoulder to the waist is his arm there and is left out of the gaps."""
    res = {}
    for view in ("front", "side", "back"):
        P = np.concatenate([o[0] for o in objs_tris])
        tris, off = [], 0
        for pts, tr, fam in objs_tris:
            for ti, t in enumerate(tr):
                if view == "side" and fam[ti] in ("arm", "hand"):
                    continue
                if view != "side" and fam[ti] == "sidecap":
                    continue
                if fam[ti] in ("head", "nose", "ear"):
                    continue
                tris.append((t[0] + off, t[1] + off, t[2] + off))
            off += len(pts)
        P2, dep = project(view, P)
        zb, _ = raster(P2, dep, tris, sh.body_mask.shape)
        model = np.isfinite(zb)
        c0, c1 = SPAN[view]
        target = np.zeros_like(sh.body_target)
        # (the sheet as drawn, the shorts included: the model'"'"'s shorts are in its outline)
        target[:, c0:c1] = sh.body_mask[:, c0:c1]
        rows = (int(CHIN) + 12, int(SOLE) + 4)
        model[:rows[0]] = False
        target[:rows[0]] = False
        skip = None
        if view == "side":
            skip = np.zeros_like(model)
            skip[360:700, :int(MID["side"])] = True
        r = gaps(model, target, rows, S, skip)
        res[view] = (round(r[0], 2), round(r[1], 2))
        if OUT:
            diff_picture(model, target, (c0, rows[0] - 20, c1, rows[1] + 10), os.path.join(OUT, "bodydiff_%s_%s.png" % (tag, view)), sh.body_pix)
    print("BROTHER body silhouettes %s (worst cm, 99%% cm): %s" % (tag, json.dumps(res)))
    return res


# ------------------------------------------------------------------------------------------------------------------
# His skeleton: the game's figures' bone names and parents (scripts/title_figures.gd poses them by name), every bone
# pointing up with no roll (so each rests unturned in Godot, as the man's do), placed at this body's own joints
# ------------------------------------------------------------------------------------------------------------------

FINGERS = ("index", "middle", "ring", "little")


def torso_centre(M, T, z):
    """The middle of the torso at a height, a little toward the back (where a spine is)."""
    rings = [(M.P[r[0]][2], np.array([M.P[i] for i in r])) for r in T]
    zs = [a for a, _ in rings]
    i = int(np.clip(np.searchsorted(zs, z), 1, len(zs) - 1))
    za, pa = rings[i - 1]
    zb, pb = rings[i]
    t = (z - za) / max(zb - za, 1e-6)
    ring = pa * (1 - t) + pb * t
    yf, yb = ring[:, 1].min(), ring[:, 1].max()
    return Vector((0.0, float(yb - 0.42 * (yb - yf)), float(z)))


def skeleton_joints(M, T, joints):
    """(name, head point, parent) for every bone, in model space."""
    hip_z = joints["hip_l"].z
    bones = [
        ("hips", torso_centre(M, T, hip_z + 0.03), None),
        ("spine", torso_centre(M, T, 1.12), "hips"),
        ("chest", torso_centre(M, T, 1.37), "spine"),
        ("neck", torso_centre(M, T, 1.615), "chest"),
    ]
    head_at = torso_centre(M, T, 1.615)
    head_at.z = HEAD_PIVOT_Z
    head_at.y += 0.012
    bones.append(("head", head_at, "neck"))
    for s, sfx in ((1, "_l"), (-1, "_r")):
        sh_ = Vector(mirror_x(joints["shoulder_l"], s))
        el = Vector(mirror_x(joints["elbow_l"], s))
        wr = Vector(mirror_x(joints["wrist_l"], s))
        bones.append(("clavicle" + sfx, Vector((s * 0.04, sh_.y - 0.01, sh_.z + 0.07)), "chest"))
        # (ninth round, as the boy's build: the upper arm hangs from the clavicle in the rig itself, so a clavicle raised
        # by a pose carries the shoulder joint up with it in the game as in the pose test; bone names kept)
        bones.append(("upper_arm" + sfx, sh_, "clavicle" + sfx))
        bones.append(("forearm" + sfx, el, "upper_arm" + sfx))
        bones.append(("hand" + sfx, wr, "forearm" + sfx))
        for f in FINGERS:
            pts = joints[f + sfx]
            for n in range(3):
                bones.append(("finger_%s_%d%s" % (f, n + 1, sfx), pts[n], "hand" + sfx if n == 0 else "finger_%s_%d%s" % (f, n, sfx)))
        pts = joints["thumb" + sfx]
        for n in range(3):
            bones.append(("thumb_%d%s" % (n + 1, sfx), pts[n], "hand" + sfx if n == 0 else "thumb_%d%s" % (n, sfx)))
        bones.append(("thigh" + sfx, joints["hip" + sfx], "hips"))
        bones.append(("shin" + sfx, joints["knee" + sfx], "hips"))
        bones.append(("foot" + sfx, joints["ankle" + sfx], "hips"))
        bones.append(("toe" + sfx, joints["ball" + sfx], "foot" + sfx))
    return bones


def make_armature(bones, name="brother_armature"):
    data = bpy.data.armatures.new(name)
    arm_ = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(arm_)
    bpy.context.view_layer.objects.active = arm_
    bpy.ops.object.mode_set(mode="EDIT")
    for bname, at, parent in bones:
        b = data.edit_bones.new(bname)
        b.head = Vector(at)
        b.tail = Vector(at) + Vector((0.0, 0.0, 0.06))
        b.roll = 0.0
        if parent:
            b.parent = data.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm_


# ------------------------------------------------------------------------------------------------------------------
# Skin weights: along each limb by where a point lies along it, blended across each joint; the trunk by height;
# the shoulders and hips shared between trunk and limb near the joint
# ------------------------------------------------------------------------------------------------------------------

def smooth01(a, b, x):
    t = np.clip((np.asarray(x, float) - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def along(p, a, b):
    d = b - a
    return float(np.dot(p - a, d) / max(np.dot(d, d), 1e-12)) * float(np.linalg.norm(d))


def chain_weights(s, names, ends, blend):
    """Weights along a chain: `ends` are the distances where each bone after the first takes over."""
    w = {names[0]: 1.0}
    for name, at in zip(names[1:], ends):
        t = float(smooth01(at - blend, at + blend, s))
        w = {k: v * (1 - t) for k, v in w.items()}
        w[name] = w.get(name, 0.0) + t
    return w


# The skin's blends (eighth round, the pose test; the seventh round's numbers in brackets): the torso's share of
# the upper arm near the shoulder (most, from, to: 0.45, 0.085, 0.2 m), the arm's share of the chest at its root (most,
# over: 0.4, 0.1 m), the head's nape band (1.638 to 1.672 by height alone before) and the neck bridge's most of the head.
SHOULDER_BLEND = (0.5, 0.07, 0.26)
ARM_ROOT_BLEND = (0.45, 0.15)
HEAD_NAPE = (1.64, 1.71)
HEAD_NECK_SHARE = 0.55
HEAD_PIVOT_Z = 1.70           # the head bone's joint (1.735 before: half way up the ears, so a turned head swung its chin)
CLAVICLE_SHARE = 0.45        # the most of the clavicle in the shoulder's top (none before: the bone carried no skin)


def weights_of(M, T, bones, joints):
    at = {n: np.array(p) for n, p, _ in bones}
    P = np.array(M.P)
    out = []
    zt = {"hips_spine": 1.02, "spine_chest": 1.25, "chest_neck": 1.6}
    for vi, part in enumerate(M.part):
        p = P[vi]
        fam = part.split("_")[0]
        sfx = "_l" if part.endswith("_l") or "_l_" in part else ("_r" if part.endswith("_r") or "_r_" in part else ("_l" if p[0] >= 0 else "_r"))
        w = {}
        if fam in ("head", "nose", "ear", "neck"):
            # (eighth round, the pose test: the chin's underside and the jaw went with the NECK while the face went
            # with the head (a band by height alone, 1.638 to 1.672 m, under the chin at 1.63), so a head thrown back
            # sheared the jaw into a shelf. Now the whole head as the base mesh has it goes with the head bone but the
            # nape low at its back; the neck's bridge blends from the neck at the torso to about half head at the jaw,
            # its throat side more)
            front = float(smooth01(-0.01, -0.07, p[1]))
            if fam in ("nose", "ear"):
                t = 1.0
            elif fam == "head":
                t = max(front, float(smooth01(HEAD_NAPE[0], HEAD_NAPE[1], p[2])))
            else:
                t = HEAD_NECK_SHARE * float(smooth01(HEAD_NAPE[0] - 0.08, HEAD_NAPE[1] - 0.03, p[2])) * (0.75 + 0.25 * front)
            w = {"head": t, "neck": 1 - t}
        elif fam == "torso":
            w = chain_weights(p[2], ["hips", "spine", "chest", "neck"], [zt["hips_spine"], zt["spine_chest"], zt["chest_neck"]], 0.07)
            # near the shoulder: some of the upper arm
            for s, sx in ((1, "_l"), (-1, "_r")):
                d = np.linalg.norm(p - at["upper_arm" + sx])
                k = SHOULDER_BLEND[0] * (1 - float(smooth01(SHOULDER_BLEND[1], SHOULDER_BLEND[2], d)))
                if k > 0:
                    w = {n: v * (1 - k) for n, v in w.items()}
                    w["upper_arm" + sx] = w.get("upper_arm" + sx, 0) + k
                # (eighth round: the shoulder's top and the trapezius over it partly on the clavicle, which the poses
                # raise with an arm lifted past the horizontal, as a shoulder blade and collarbone do)
                ua = at["upper_arm" + sx]
                kc = CLAVICLE_SHARE * float(smooth01(ua[2] - 0.05, ua[2] + 0.03, p[2])) * (1 - float(smooth01(0.06, 0.2, d))) * float(smooth01(0.04, 0.1, s * p[0]))
                if kc > 0.01:
                    w = {n: v * (1 - kc) for n, v in w.items()}
                    w["clavicle" + sx] = w.get("clavicle" + sx, 0) + kc
                # near the hip: some of the thigh
                if p[2] < at["hips"][2] + 0.02 and s * p[0] > 0.02:
                    k = 0.62 * (1 - float(smooth01(at["thigh" + sx][2] - 0.06, at["hips"][2] + 0.05, p[2]))) * float(smooth01(0.0, 0.08, s * p[0]))
                    w = {n: v * (1 - k) for n, v in w.items()}
                    w["thigh" + sx] = w.get("thigh" + sx, 0) + k
            if vi in M.tag["crotch"]:
                w = {"hips": 0.6, "thigh_l": 0.2, "thigh_r": 0.2}
        elif fam == "shoulder":
            w = {"chest": 0.3, "clavicle" + sfx: 0.3, "upper_arm" + sfx: 0.4}
        elif fam == "arm":
            J, E, W = at["upper_arm" + sfx], at["forearm" + sfx], at["hand" + sfx]
            Lu = np.linalg.norm(E - J)
            s = along(p, J, E)
            if s > Lu - 0.06:
                s = Lu + along(p, E, W)
            w = chain_weights(s, ["upper_arm" + sfx, "forearm" + sfx, "hand" + sfx], [Lu, Lu + np.linalg.norm(W - E) + 0.005], 0.055)
            k = ARM_ROOT_BLEND[0] * (1 - float(smooth01(0.0, ARM_ROOT_BLEND[1], s)))
            if k > 0:
                # (ninth round, as the boy's: the arm's root shared between the chest and the clavicle it now hangs from)
                w = {n: v * (1 - k) for n, v in w.items()}
                w["chest"] = w.get("chest", 0) + k * 0.4
                w["clavicle" + sfx] = w.get("clavicle" + sfx, 0) + k * 0.6
        elif fam == "hand":
            sub = part.split("_")[2] if part.count("_") >= 2 else ""
            if sub in FINGERS or sub == "thumb":
                names = ["finger_%s_%d%s" % (sub, n, sfx) for n in (1, 2, 3)] if sub != "thumb" else ["thumb_%d%s" % (n, sfx) for n in (1, 2, 3)]
                a1, a2, a3 = at[names[0]], at[names[1]], at[names[2]]
                s = along(p, a1, a2)
                l1 = np.linalg.norm(a2 - a1)
                if s > l1 - 0.004:
                    s = l1 + max(0.0, along(p, a2, a3))
                    l2 = l1 + np.linalg.norm(a3 - a2)
                    if s > l2 - 0.004:
                        s = l2 + max(0.0, along(p, a3, a3 + (a3 - a2)))
                w = chain_weights(s, ["hand" + sfx] + names, [0.004, l1, l1 + np.linalg.norm(a3 - a2)], 0.008)
            else:
                Wr = at["hand" + sfx]
                s = along(p, at["forearm" + sfx], Wr) - np.linalg.norm(Wr - at["forearm" + sfx])
                w = chain_weights(s, ["forearm" + sfx, "hand" + sfx], [0.0], 0.03)
        elif fam in ("leg", "foot"):
            H, K, A = at["thigh" + sfx], at["shin" + sfx], at["foot" + sfx]
            if fam == "leg":
                z = p[2]
                w = chain_weights(-z, ["thigh" + sfx, "shin" + sfx, "foot" + sfx], [-K[2], -A[2]], 0.055)
                k = 0.42 * float(smooth01(H[2] - 0.1, H[2] + 0.04, z))  # (polish pass: a wider blend, so a lifted or seated thigh stretches the seat instead of shearing it)
                if k > 0:
                    w = {n: v * (1 - k) for n, v in w.items()}
                    w["hips"] = w.get("hips", 0) + k
            else:
                fwd = np.array((math.sin(FOOT_YAW) * (1 if sfx == "_l" else -1), -math.cos(FOOT_YAW), 0.0))
                u = float(np.dot(p - A, fwd))
                w = chain_weights(u, ["foot" + sfx, "toe" + sfx], [float(np.dot(at["toe" + sfx] - A, fwd)) if BASE_FEET else 0.15],  0.025 if BASE_FEET else 0.03)
                k = 0.5 * float(smooth01(A[2] - 0.02, A[2] + 0.04, p[2]))
                if k > 0:
                    w = {n: v * (1 - k) for n, v in w.items()}
                    w["shin" + sfx] = w.get("shin" + sfx, 0) + k
        else:
            w = {"hips": 1.0}
        w = {n: v for n, v in w.items() if v > 0.01}
        tot = sum(w.values())
        out.append({n: v / tot for n, v in sorted(w.items(), key=lambda kv: -kv[1])[:4]})
    return out
# ------------------------------------------------------------------------------------------------------------------
# Planned UVs (the user: "instead of projecting hte concept art onto it we should make proper uvs no?"). Every part
# is a grid of rings: unwrapped as one, the distance round each ring from its seam across, the distance down the
# rings along. Seams: down his sides (torso front and back), under each arm, inside each leg, down the sides of the
# head behind the ears (the face and the front of the cap one big island, the back of the head another); the hands
# front and back of the palm; the soles flat; the nose, the ears and the peak flat.
# ------------------------------------------------------------------------------------------------------------------

# Each island's share of texels (on top of its size) and which picture it goes in.
ISLANDS = {
    "torso_front": ("skin", 1.25), "torso_back": ("skin", 1.0), "arm_l": ("skin", 1.0), "arm_r": ("skin", 1.0),
    "hand_l_back": ("skin", 3.0), "hand_l_palm": ("skin", 2.0), "hand_r_back": ("skin", 3.0), "hand_r_palm": ("skin", 2.0),
    "leg_l": ("skin", 0.8), "leg_r": ("skin", 0.8), "sole_l": ("skin", 0.5), "sole_r": ("skin", 0.5),
    "head_front": ("face", 4.0), "head_back": ("face", 0.8), "nose": ("face", 2.2), "ear_l": ("face", 0.8),
    "ear_r": ("face", 0.8),
}
ATLAS = {"skin": 1024, "face": 1024}


def grid_uvs(M, rings, faces, seam, up=False):
    """UVs for faces between consecutive rings of one grid: u the distance round the ring from point `seam` (going
    the rings' own way round), v the distance down the rings (the mean over the ring's points). Gives
    {face index: [uv per corner]}."""
    P = np.array(M.P)
    where = {}
    for ri, ring in enumerate(rings):
        for j, v in enumerate(ring):
            where.setdefault(v, []).append((ri, j))
    n = len(rings[0])
    arcs = []
    for ring in rings:
        pts = P[ring]
        seg = np.linalg.norm(np.roll(pts, -1, 0) - pts, axis=1)    # j -> j+1
        a = np.zeros(n + 1)
        for k in range(n):
            j = (seam + k) % n
            a[k + 1] = a[k] + seg[j]
        arcs.append(a)
    vs = [0.0]
    for ri in range(1, len(rings)):
        vs.append(vs[-1] + float(np.linalg.norm(P[rings[ri]] - P[rings[ri - 1]], axis=1).mean()))
    out = {}
    for fi in faces:
        f = M.faces[fi]
        cand = [where[v] for v in f]
        # the face's rings: the two consecutive rings shared by its points
        rset = sorted({r for c in cand for r, _ in c})
        best = None
        for r in rset:
            if r + 1 in rset and all(any(rr in (r, r + 1) for rr, _ in c) for c in cand):
                best = r
                break
        if best is None:
            continue
        uv = []
        ks = []
        for c in cand:
            ri, j = next((rr, jj) for rr, jj in c if rr in (best, best + 1))
            k = (j - seam) % n
            ks.append((ri, k))
        kk = [k for _, k in ks]
        if max(kk) - min(kk) > n // 2:          # (crosses the seam: the low side goes to the far end)
            ks = [(ri, k + n if k < n // 2 else k) for ri, k in ks]
        for ri, k in ks:
            a = arcs[ri]
            u = a[k] if k <= n else a[n] + (a[k - n])
            # centred: each ring's middle at u = 0, so the island is upright
            uv.append((u - a[n] / 2.0, vs[ri] if up else -vs[ri]))
        out[fi] = uv
    return out


def planar_uvs(M, faces, ax_u, ax_v, origin=(0, 0, 0)):
    P = np.array(M.P)
    out = {}
    for fi in faces:
        out[fi] = [(float(np.dot(P[v] - origin, ax_u)), float(np.dot(P[v] - origin, ax_v))) for v in M.faces[fi]]
    return out


def cylinder_uvs(M, T, faces, back):
    P = np.array(M.P)
    zs = np.array([P[r][:, 2].mean() for r in T])
    cys = np.array([P[r][:, 1].mean() for r in T])
    Rs = np.array([np.hypot(P[r][:, 0], P[r][:, 1] - P[r][:, 1].mean()).mean() for r in T])
    out = {}
    for fi in faces:
        uv = []
        for v in M.faces[fi]:
            x, y, z = P[v]
            cy = float(np.interp(z, zs, cys))
            R = float(np.interp(z, zs, Rs))
            th = math.atan2(-x, y - cy) if back else math.atan2(x, -(y - cy))
            uv.append((th * R, float(z)))
        out[fi] = uv
    return out


def base_island(M, faces):
    """A base mesh's own UVs for these faces, in metres (its UV units times the root of the surface's area over the
    UVs' area)."""
    P = np.array(M.P)
    a3 = auv = 0.0
    for fi in faces:
        a3 += float(np.linalg.norm(face_normal(P, M.faces[fi]))) / 2.0
        q = np.array([M.base_uv[fi][v] for v in M.faces[fi]])
        auv += abs(float(np.sum(q[:, 0] * np.roll(q[:, 1], -1) - np.roll(q[:, 0], -1) * q[:, 1]))) / 2.0
    k = math.sqrt(a3 / max(auv, 1e-12))
    return {fi: [(M.base_uv[fi][v][0] * k, M.base_uv[fi][v][1] * k) for v in M.faces[fi]] for fi in faces}


def round_uvs(M, faces, centre, across, back, along, front_half=None):
    """UVs round an axis: u the angle (from `across`'s side through `back`'s) times the mean radius, v along it.
    front_half: True/False splits the faces by which half they face (each half its own island, its seam behind)."""
    P = np.array(M.P)
    ids = sorted({v for fi in faces for v in M.faces[fi]})
    rad = float(np.mean([np.linalg.norm((P[v] - centre) - along * np.dot(P[v] - centre, along)) for v in ids]))
    out = {}
    for fi in faces:
        Q = P[M.faces[fi]] - centre
        th = np.arctan2(Q @ across, Q @ back)
        if front_half is not None:
            c = float(np.arctan2(np.mean(np.sin(th)), np.mean(np.cos(th))))
            if (abs(c) > math.pi / 2) != front_half:
                continue
            th = np.arctan2(-(Q @ across), -(Q @ back)) if front_half else th
        if th.max() - th.min() > math.pi:
            th = np.where(th < 0, th + math.tau, th)
        out[fi] = [(float(t) * rad, float(np.dot(q, along))) for t, q in zip(th, Q)]
    return out


def plan_uvs(M, T, H, joints):
    """Gives {island: {face index: [uv per corner, metres]}}. Third build: the head and the hands keep their base
    meshes' own UVs (packed into the face and skin pictures); the neck and the wrists' bridges are unrolled round."""
    islands = {}
    # torso: front (columns 12..3, seam at column 4 and 12) and back
    tf = [fi for fi, c in M.cell.items() if c[0] == "torso" and (c[2] >= 12 or c[2] < 4)]
    tb = [fi for fi, c in M.cell.items() if c[0] == "torso" and 4 <= c[2] < 12]
    # (the torso's front and back by angle round his middle at each height times that height's mean radius, so the
    # arm holes, whose points stand round the shoulder, do not shear the islands as distance round a ring did)
    islands["torso_front"] = cylinder_uvs(M, T, tf, back=False)
    islands["torso_back"] = cylinder_uvs(M, T, tb, back=True)
    # the head (its base mesh's UVs) and the neck (round it, front and back halves)
    islands["head_base"] = base_island(M, M.tag["base_head_faces"])
    ISLANDS["head_base"] = ("face", 4.0)
    nk = [fi for fi, p in enumerate(M.fpart) if p == "neck"]
    P = np.array(M.P)
    c = P[T[-1]].mean(0)
    c[0] = 0.0
    up = np.array((0.0, 0.0, 1.0))
    # (front half: angle from his front; back half: from his back; u across his left as +)
    islands["neck_front"] = round_uvs(M, nk, c, np.array((1.0, 0.0, 0.0)), np.array((0.0, 1.0, 0.0)), up, front_half=True)
    islands["neck_back"] = round_uvs(M, nk, c, np.array((1.0, 0.0, 0.0)), np.array((0.0, 1.0, 0.0)), up, front_half=False)
    ISLANDS["neck_front"] = ("face", 1.0)
    ISLANDS["neck_back"] = ("face", 0.8)
    # limbs
    for sfx in ("_l", "_r"):
        rings = M.tag["arm_rings" + sfx]
        af = [fi for fi, p in enumerate(M.fpart) if p == "arm" + sfx]
        islands["arm" + sfx] = grid_uvs(M, rings, af, 5)
        lr = M.tag["leg_rings" + sfx]
        if BASE_FEET:
            lf = [fi for fi, p in enumerate(M.fpart) if p == "leg" + sfx and len(M.faces[fi]) == 4]
            islands["leg" + sfx] = grid_uvs(M, lr, lf, 9)
            o, f_, l_ = M.tag["foot_frame" + sfx]
            fi_ = foot_islands(M, M.tag["foot_faces" + sfx], o, f_, l_, lr[-1])
            for g, share in (("upper", 1.4), ("sole", 0.7)):
                ISLANDS["foot_%s%s" % (g, sfx)] = ("skin", share)
                islands["foot_%s%s" % (g, sfx)] = fi_[g]
        elif FOOT_N:
            # (polish pass: the foot has rings of its own count; the leg's grid stops at the ankle, the foot is laid
            # out as five flat islands by which way each face looks: its top, its sole, its inside, outside and heel)
            lf = [fi for fi, p in enumerate(M.fpart) if p == "leg" + sfx and len(M.faces[fi]) == 4]
            islands["leg" + sfx] = grid_uvs(M, lr, lf, 9)
            s_ = 1.0 if sfx == "_l" else -1.0
            fw = np.array((s_ * math.sin(FOOT_YAW), -math.cos(FOOT_YAW), 0.0))
            lt = np.array((s_ * math.cos(FOOT_YAW), s_ * math.sin(FOOT_YAW), 0.0))
            Pn = np.array(M.P)
            groups = {"top": [], "sole": [], "in": [], "out": [], "heel": []}
            for fi, p in enumerate(M.fpart):
                if p != "foot" + sfx:
                    continue
                n = face_normal(Pn, M.faces[fi])
                n = n / max(np.linalg.norm(n), 1e-12)
                if n[2] < -0.55:
                    groups["sole"].append(fi)
                elif n[2] > 0.45 or np.dot(n, fw) > 0.6:
                    groups["top"].append(fi)
                elif np.dot(n, fw) < -0.55:
                    groups["heel"].append(fi)
                elif np.dot(n, lt) > 0:
                    groups["out"].append(fi)
                else:
                    groups["in"].append(fi)
            up = np.array((0.0, 0.0, 1.0))
            axes = {"top": (lt, fw), "sole": (lt, -fw), "in": (-fw, up), "out": (fw, up), "heel": (-lt, up)}
            for g, fs in groups.items():
                ISLANDS["foot_%s%s" % (g, sfx)] = ("skin", 1.0)
                islands["foot_%s%s" % (g, sfx)] = planar_uvs(M, fs, axes[g][0], axes[g][1])
        else:
            lf = [fi for fi, p in enumerate(M.fpart) if p in ("leg" + sfx, "foot" + sfx) and len(M.faces[fi]) == 4]
            islands["leg" + sfx] = grid_uvs(M, lr, lf, 9)
            sole = [fi for fi, p in enumerate(M.fpart) if p == "foot" + sfx and len(M.faces[fi]) == 3]
            islands["sole" + sfx] = planar_uvs(M, sole, np.array((1.0, 0, 0)), np.array((0, -1.0, 0)))
        # The hands: laid out as the hands sheet's back and palm views see the hand flat (the bundle's hand UVs overlap
        # between back and palm, and a projection painted through them came out scrambled): each face by which way it
        # faces in the flat pose, its back across and along, its palm the same, mirrored.
        flat = M.tag["hand_flat" + sfx]
        hf = M.tag["hand_faces" + sfx]
        ids = np.array(list(flat))
        Fp = np.zeros((len(M.P), 3))
        Fp[ids] = np.array([flat[i] for i in ids])
        cen = Fp[ids].mean(0)
        out = sum(float(np.dot(face_normal(Fp, M.faces[fi]), Fp[M.faces[fi]].mean(0) - cen)) for fi in hf)
        sgn = 1.0 if out > 0 else -1.0
        back = {fi: [(float(Fp[v][0]), float(Fp[v][2])) for v in M.faces[fi]] for fi in hf if sgn * face_normal(Fp, M.faces[fi])[1] >= 0}
        palm = {fi: [(-float(Fp[v][0]), float(Fp[v][2])) for v in M.faces[fi]] for fi in hf if fi not in back}
        # (the thumb its own pair: in the flat pose it stands in front of the palm's edge, so its faces would lie over
        # the palm's in one picture)
        th = {fi for fi in hf if M.fpart[fi].endswith("_thumb")}
        for name, isl, share in (("handback", back, 2.6), ("handpalm", palm, 2.0)):
            islands[name + sfx] = {fi: uv for fi, uv in isl.items() if fi not in th}
            islands[name + "thumb" + sfx] = {fi: uv for fi, uv in isl.items() if fi in th}
            ISLANDS[name + sfx] = ("skin", share)
            ISLANDS[name + "thumb" + sfx] = ("skin", share)
        Tb, Wd, L = (np.array(v, float) for v in joints["hand_frame" + sfx])
        Wj = np.array(mirror_x(joints["wrist_l"], 1 if sfx == "_l" else -1), float)
        islands["wrist" + sfx] = round_uvs(M, M.tag["wrist_faces" + sfx], Wj, Wd, Tb, L)
        ISLANDS["wrist" + sfx] = ("skin", 1.0)
    missing = [fi for fi in range(len(M.faces)) if not any(fi in isl for isl in islands.values())]
    if missing:
        print("BROTHER UV: %d faces in no island: %s" % (len(missing), sorted({M.fpart[f] for f in missing})))
    return islands


def pack(islands, pad_px=6):
    """Shelf-packs each picture's islands, each at its true size times the square root of its share: gives
    {island: (picture, u0, v0, scale, (w, h) metres)} and {face: (picture, [uv per corner in 0..1])}."""
    placed, face_uv = {}, {}
    for picture, size in ATLAS.items():
        names = [n for n in islands if ISLANDS[n][0] == picture and islands[n]]
        boxes = {}
        for n in names:
            pts = np.array([q for uv in islands[n].values() for q in uv])
            lo, hi = pts.min(0), pts.max(0)
            k = math.sqrt(ISLANDS[n][1])
            boxes[n] = (lo, hi, k, (hi - lo) * k)
        for n in names:
            if not np.all(np.isfinite(boxes[n][3])) or boxes[n][3].min() <= 0:
                raise ValueError("island %s has a bad size %s" % (n, boxes[n][3]))
        order = sorted(names, key=lambda n: -boxes[n][3][1])
        total = sum(b[3][0] * b[3][1] for b in boxes.values())
        width = max(math.sqrt(total) * 0.95, max(b[3][0] for b in boxes.values()) * 1.02) if boxes else 1.0
        while True:
            pad = width * pad_px / size
            x = y = shelf = 0.0
            spots = {}
            for n in order:
                w, h = boxes[n][3]
                if x + w > width and x > 0:
                    x, y, shelf = 0.0, y + shelf + pad, 0.0
                spots[n] = (x, y)
                x += w + pad
                shelf = max(shelf, h)
            if y + shelf <= width:
                break
            width *= 1.03
        for n in order:
            lo, hi, k, (w, h) = boxes[n]
            ox, oy = spots[n]
            sc = k / width
            placed[n] = (picture, ox / width, oy / width, sc, tuple(hi - lo))
            for fi, uv in islands[n].items():
                face_uv[fi] = (picture, [((q[0] - lo[0]) * sc + ox / width, (q[1] - lo[1]) * sc + oy / width) for q in uv])
    return placed, face_uv


_FONT = {
    "A": "010101111101101", "B": "110101110101110", "C": "011100100100011", "D": "110101101101110", "E": "111100110100111",
    "F": "111100110100100", "G": "011100101101011", "H": "101101111101101", "I": "111010010010111", "K": "101101110101101",
    "L": "100100100100111", "M": "101111111101101", "N": "110101101101101", "O": "010101101101010", "P": "110101110100100",
    "R": "110101110101101", "S": "011100010001110", "T": "111010010010010", "U": "101101101101111", "W": "101101111111101",
    "Y": "101101010010010", "_": "000000000000111", " ": "000000000000000",
}


def write_layout(face_uv, placed, picture, path):
    size = ATLAS[picture]
    img = np.ones((size, size, 3)) * 0.12
    for fi, (pic, uv) in face_uv.items():
        if pic != picture:
            continue
        for a, b in zip(uv, uv[1:] + uv[:1]):
            steps = int(max(abs(b[0] - a[0]), abs(b[1] - a[1])) * size) + 2
            for t in np.linspace(0, 1, steps):
                x = int((a[0] + (b[0] - a[0]) * t) * (size - 1))
                y = int((a[1] + (b[1] - a[1]) * t) * (size - 1))
                img[size - 1 - y, x] = (0.55, 0.75, 0.95)
    for n, (pic, u0, v0, sc, (w, h)) in placed.items():
        if pic != picture:
            continue
        x, y = int(u0 * size) + 3, size - 1 - int(v0 * size) - 4
        for ch in n.upper():
            g = _FONT.get(ch, _FONT[" "])
            for gy in range(5):
                for gx in range(3):
                    if g[gy * 3 + gx] == "1":
                        img[max(0, y - (4 - gy) * 2 - 1):max(0, y - (4 - gy) * 2 + 1), x + gx * 2:x + gx * 2 + 2] = (1.0, 0.85, 0.2)
            x += 8
    save_rgb(path, img)
    with open(path.replace(".png", ".json"), "w") as f:
        json.dump({"size": size, "islands": {n: {"rect": [round(u0, 5), round(v0, 5), round(u0 + w * sc, 5), round(v0 + h * sc, 5)],
                                                 "metres": [round(w, 4), round(h, 4)]}
                                             for n, (pic, u0, v0, sc, (w, h)) in placed.items() if pic == picture}}, f, indent=1)


# ------------------------------------------------------------------------------------------------------------------
# Paint: the sheets projected into the layout. Each texel takes the views that see it (a depth test against the
# model drawn from that view, and only where the sheet shows him, kept off his outline's edge), weighted by how
# squarely each sees it; what none sees is filled from round it. Skin: the tattoos are painted out (they are laid
# over it from a table, stage two) and the boxers' white is never taken.
# ------------------------------------------------------------------------------------------------------------------

def erode(mask, n):
    m = mask.copy()
    for _ in range(n):
        m = m & np.roll(m, 1, 0) & np.roll(m, -1, 0) & np.roll(m, 1, 1) & np.roll(m, -1, 1)
    return m


def texel_geometry(M, face_uv, picture, P, N):
    size = ATLAS[picture]
    pos = np.zeros((size, size, 3), np.float32)
    nrm = np.zeros((size, size, 3), np.float32)
    hit = np.zeros((size, size), bool)
    fid = np.full((size, size), -1, np.int32)
    for fi, (pic, uv) in face_uv.items():
        if pic != picture:
            continue
        f = M.faces[fi]
        for i in range(1, len(f) - 1):
            ids = (0, i, i + 1)
            uvs = np.array([uv[k] for k in ids]) * size
            ps = P[[f[k] for k in ids]]
            ns = N[[f[k] for k in ids]]
            lo = np.clip(np.floor(uvs.min(0)).astype(int) - 1, 0, size - 1)
            hi = np.clip(np.ceil(uvs.max(0)).astype(int) + 1, 0, size - 1)
            xs, ys = np.meshgrid(np.arange(lo[0], hi[0] + 1) + 0.5, np.arange(lo[1], hi[1] + 1) + 0.5)
            a, b, c = uvs
            den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
            if abs(den) < 1e-12:
                continue
            w0 = ((b[1] - c[1]) * (xs - c[0]) + (c[0] - b[0]) * (ys - c[1])) / den
            w1 = ((c[1] - a[1]) * (xs - c[0]) + (a[0] - c[0]) * (ys - c[1])) / den
            w2 = 1 - w0 - w1
            inside = (w0 >= -0.01) & (w1 >= -0.01) & (w2 >= -0.01)
            if not inside.any():
                continue
            wv = np.stack([w0, w1, w2], -1)[inside]
            rows = (ys[inside] - 0.5).astype(int)
            cols = (xs[inside] - 0.5).astype(int)
            pos[rows, cols] = wv @ ps
            nrm[rows, cols] = wv @ ns
            hit[rows, cols] = True
            fid[rows, cols] = fi
    nrm /= np.maximum(np.linalg.norm(nrm, axis=-1, keepdims=True), 1e-6)
    return pos, nrm, hit, fid


def fill_out(rgb, valid, rounds=64):
    """What is not valid filled from round it: a pull-push pyramid (each coarser level the mean of the valid texels
    under it; going back up, the gaps take the coarser level's colour), then softened in the gaps."""
    levels = [(rgb * valid[..., None], valid.astype(float))]
    while levels[-1][1].shape[0] > 1:
        c, w = levels[-1]
        h2, w2 = c.shape[0] // 2, c.shape[1] // 2
        cs = c[:h2 * 2, :w2 * 2].reshape(h2, 2, w2, 2, 3).sum((1, 3))
        ws = w[:h2 * 2, :w2 * 2].reshape(h2, 2, w2, 2).sum((1, 3))
        levels.append((cs, ws))
    col = levels[-1][0] / np.maximum(levels[-1][1], 1e-9)[..., None]
    for c, w in reversed(levels[:-1]):
        up = np.repeat(np.repeat(col, 2, 0), 2, 1)
        up = np.pad(up, ((0, c.shape[0] - up.shape[0]), (0, c.shape[1] - up.shape[1]), (0, 0)), mode="edge")
        up = blur(up, 2)
        own = c / np.maximum(w, 1e-9)[..., None]
        k = np.clip(w, 0, 1)[..., None]
        col = own * k + up * (1 - k)
    out = rgb.copy()
    gaps = ~valid
    soft = blur(col, 2)
    out[gaps] = soft[gaps]
    return out


def fill_out_slow(rgb, valid, rounds=64):
    filled = valid.copy()
    rgb = rgb.copy()
    for _ in range(rounds):
        grow = np.zeros_like(rgb)
        count = np.zeros(filled.shape)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            m = np.roll(np.roll(filled, dy, 0), dx, 1)
            grow += np.roll(np.roll(rgb, dy, 0), dx, 1) * m[..., None]
            count += m
        new = ~filled & (count > 0)
        if not new.any():
            break
        rgb[new] = grow[new] / count[new][..., None]
        filled |= new
    return rgb


def blur(img, n=1):
    out = img.copy()
    for _ in range(n):
        out = (out + np.roll(out, 1, 0) + np.roll(out, -1, 0) + np.roll(out, 1, 1) + np.roll(out, -1, 1)) / 5.0
    return out


def is_ink(c, local):
    """Tattoo ink, measured on the sheet: blue-grey, its red no higher than its green and hardly above its blue
    (skin there is about (0.47, 0.37, 0.33), ink about (0.5, 0.51, 0.49), the grey chest hair (0.49, 0.46, 0.42))."""
    r, g, b = c[..., 0], c[..., 1], c[..., 2]
    return (r - b < 0.045) & (g - r > -0.022) & (c.mean(-1) < 0.7)


def is_boxers(c):
    mx, mn = c.max(-1), c.min(-1)
    return (mn > 0.66) & (mx - mn < 0.17)


def paint(M, face_uv, picture, sh, views, tris_for_depth, clean_skin=False, extra_reject=None, extend_up=None):
    """views: list of (view name, picture array, mask, mirrored) to paint from."""
    P = np.array(M.P)
    tris = M.tris()
    N = normals_of(P, tris)
    pos, nrm, hit, fid = texel_geometry(M, face_uv, picture, P, N)
    size = ATLAS[picture]
    acc = np.zeros((size, size, 3))
    wsum = np.zeros((size, size))
    for view, pix, mask, mirrored in views:
        Q = pos.reshape(-1, 3).copy()
        Nn = nrm.reshape(-1, 3).copy()
        if mirrored:
            Q[:, 0] *= -1
            Nn[:, 0] *= -1
        Pm = P.copy()
        if mirrored:
            Pm[:, 0] *= -1
        P2, dep = project(view, Pm)
        zb, _ = raster(P2, dep, tris_for_depth, mask.shape)
        q2, qd = project(view, Q)
        _, facing = screen_dir(view, Nn)
        cols = np.clip(q2[:, 0].astype(int), 0, mask.shape[1] - 1)
        rows = np.clip(q2[:, 1].astype(int), 0, mask.shape[0] - 1)
        seen = (qd <= zb[rows, cols] + 0.012) & erode(mask, 2)[rows, cols] & (facing > 0.08) & hit.ravel()
        colour = pix[rows, cols]
        if extra_reject is not None:
            seen &= ~extra_reject(view, colour, rows, cols)
        w = np.where(seen, facing ** 2, 0.0)
        acc += (colour * w[:, None]).reshape(size, size, 3)
        wsum += w.reshape(size, size)
    good = wsum > 0.02
    rgb = acc / np.maximum(wsum, 1e-6)[..., None]
    if clean_skin:
        local = blur(fill_out(rgb, good & ~is_boxers(rgb), 16), 12)
        ink = good & is_ink(rgb, local)
        ink = ink | np.roll(ink, 1, 0) | np.roll(ink, -1, 0) | np.roll(ink, 1, 1) | np.roll(ink, -1, 1)
        good &= ~ink & ~is_boxers(rgb)
        print("BROTHER paint %s: %d texels of ink painted out" % (picture, int(ink.sum())))
    if extend_up is not None:
        # The cloth above the highest texel painted in each column (the garment reaches higher than the sheet's drawn
        # waistband) takes that column's waistband colour, instead of the pull-push fill's grey average of the whole
        # garment, which showed as a grey-brown strip over the waistband.
        z = pos[..., 2]
        n = 0
        cols, wants, colours = [], [], []
        for c in range(size):
            ok = good[:, c] & hit[:, c]
            if not ok.any():
                continue
            zmax = z[ok, c].max()
            if zmax < extend_up:
                continue
            near = ok & (z[:, c] >= zmax - 0.008)
            cols.append(c)
            wants.append(hit[:, c] & ~good[:, c] & (z[:, c] > zmax - 0.002))
            colours.append(rgb[near, c].mean(0))
        # (smoothed across the columns, so the waistband's ribs are not drawn up the strip as streaks)
        colours = np.array(colours)
        for k, (c, want) in enumerate(zip(cols, wants)):
            near_k = [i for i in range(max(0, k - 12), min(len(cols), k + 13)) if abs(cols[i] - c) <= 12]
            rgb[want, c] = colours[near_k].mean(0)
            good[want, c] = True
            n += int(want.sum())
        print("BROTHER paint %s: %d texels above the waistband given its colour" % (picture, n))
    rgb = fill_out(rgb, good, 200)
    # a soft pass where texels were filled, so filled patches carry no streaks
    soft = blur(rgb, 3)
    rgb = np.where(good[..., None], rgb, soft)
    print("BROTHER paint %s: %.0f%% of its texels seen by a view" % (picture, 100.0 * (good & hit).sum() / max(hit.sum(), 1)))
    return rgb, hit
# Forms the plain grey model lacked (the coordinator, from a render of him untextured, 2026-11-18: "the torso is a
# smooth tube: no pecs, no belly roll over the waistband, no love handles, no navel ... the knees and calves are
# tubes"). Moves of the fitted rings, by row and by how far round from his front each point is, in metres: forward is
# -Y. (row, {column offset from the front middle: (forward, outward[, up])}).
# Seventh round (the user, of the belly in profile: "His belly has an issue its sharp"; "his shoulders need a little
# work"): the belly is one full round curve (out from under the chest, fullest a little below the navel, rolling
# smoothly under and back in to the band, no crease ring), then smoothed down each front column (BELLY_SMOOTH); the
# shoulders get a rounded top and the trapezius rising into the neck, a hint of the collarbone, and the armpit's folds.
BODY_FORMS = {
    # a solid belly, a little forward between the navel and the band (he is built, not fat)
    610: {0: (0.003, 0.0), 1: (0.003, 0.0), 2: (0.002, 0.0)},
    640: {0: (0.006, 0.0), 1: (0.005, 0.0), 2: (0.003, 0.0)},
    665: {0: (0.006, 0.0), 1: (0.005, 0.0), 2: (0.003, 0.0)},
    690: {0: (0.003, 0.0), 1: (0.003, 0.0), 2: (0.002, 0.0)},
    # the pecs (the nipples' row about 500) over a fold under them, the breastbone's groove between; the armpit's
    # folds (the pec's edge in front of the arm, the lats behind it); the spine's groove down the back
    442: {0: (-0.002, 0.0), 1: (0.014, 0.0), 2: (0.018, 0.0), 3: (0.010, 0.0), 6: (0.0, 0.004), 7: (0.0, 0.004), 8: (0.004, 0.0)},
    490: {0: (-0.005, 0.0), 1: (0.022, 0.0), 2: (0.027, 0.0), 3: (0.017, 0.0), 6: (0.0, 0.006), 7: (0.0, 0.004), 8: (0.006, 0.0)},
    538: {0: (-0.004, 0.0), 1: (-0.006, 0.0), 2: (-0.008, 0.0), 3: (-0.003, 0.0), 8: (0.006, 0.0)},
    560: {8: (0.005, 0.0)},
    580: {8: (0.004, 0.0)},
    # the trapezius rising from the shoulders into a thick neck, the collarbone's hint in front
    398: {1: (0.004, 0.0, 0.002), 2: (0.004, 0.0, 0.004)},
    # (fifth round, the critic: "the traps run straight up into the jaw, so the head looks sunk": the trapezius no
    # longer raised at its sides, and the nape drawn in and down behind the neck)
    368: {2: (0.0, 0.004, 0.0), 3: (0.0, 0.008, 0.002), 4: (0.0, 0.008, 0.002), 5: (0.0, 0.006, 0.002), 6: (0.0, 0.004, 0.0)},
    345: {2: (0.0, 0.002, -0.004), 3: (0.0, 0.004, -0.006), 4: (0.0, 0.004, -0.006), 5: (0.0, 0.004, -0.006), 6: (0.0, 0.003, -0.006), 7: (0.006, 0.0, -0.008), 8: (0.007, 0.0, -0.008)},
    318: {3: (0.0, 0.0, -0.002), 4: (0.0, 0.0, -0.003), 5: (0.0, 0.0, -0.002), 7: (0.008, 0.0, -0.004), 8: (0.01, 0.0, -0.005)},
}
# The kneecaps (forward, metres) on the leg ring at the knee's row, by point (point 1 is the front), and the calves
# (back, metres) on the rings below it (point 6 is the back).
KNEE_FORM = {1: 0.012, 0: 0.006, 2: 0.006}
CALF_FORM = {1190: {6: 0.012, 5: 0.009, 7: 0.009}, 1235: {6: 0.008, 5: 0.006, 7: 0.006}}
# The belly's rows smoothed down each front column after the forms (from, to, rounds): no ring stands out of the curve.
BELLY_SMOOTH = (600, 720, 3)
FORMS_SPLIT_ROW = 545               # the body sheet's row above which the torso's faces are split for the forms (was 735)
TRAPS = 0.022                       # refine_forms: metres the trapezius slope is raised
TORSO_ALONG_ROUNDS = 6              # smooth_along's rounds
FOREARM_WIDEST = 0.33               # taper_forearms: the share of the way elbow to wrist where the forearm is widest
WRIST_EASE = 1.04                   # taper_forearms: the last ring this much bigger round than the hand's wrist loop
ANKLE_THIN = 0.12                   # smooth_ankles: the shin's last ring drawn in this share


def sculpt_body(M):
    T = M.tag["torso_rings"]
    P = np.array(M.P)
    holes = set(M.tag["hole_l"]) | set(M.tag["hole_r"])
    for row, moves in BODY_FORMS.items():
        ring = T[TORSO_ROWS.index(row)]
        for k, mv in moves.items():
            fwd, out = mv[0], mv[1]
            up = mv[2] if len(mv) > 2 else 0.0
            for kk in {k % TORSO_N, (-k) % TORSO_N}:
                v = ring[kk]
                if v in holes:
                    continue
                P[v][1] -= fwd
                P[v][0] += math.copysign(out, P[v][0]) if abs(P[v][0]) > 1e-4 else 0.0
                P[v][2] += up
    # the belly's front columns smoothed downward (each point toward the middle of its neighbours above and below)
    lo, hi, rounds = BELLY_SMOOTH
    idx = [i for i, r in enumerate(TORSO_ROWS) if lo <= r <= hi]
    for _ in range(rounds):
        Q = P.copy()
        for i in idx:
            if i == 0 or i == len(T) - 1:
                continue
            for k in list(range(0, 4)) + list(range(13, 16)):
                a, b, c = T[i - 1][k], T[i][k], T[i + 1][k]
                Q[b][1] = P[b][1] * 0.6 + (P[a][1] + P[c][1]) * 0.2
                Q[b][0] = P[b][0] * 0.6 + (P[a][0] + P[c][0]) * 0.2
        P = Q
    for sfx in ("_l", "_r"):
        ring = M.tag["leg_rings" + sfx][LEG_ROWS.index(KNEE_ROW) + 1]
        for j, fwd in KNEE_FORM.items():
            P[ring[j]][1] -= fwd
        for row, moves in CALF_FORM.items():
            ring = M.tag["leg_rings" + sfx][LEG_ROWS.index(row) + 1]
            for j, back in moves.items():
                P[ring[j]][1] += back
    M.P = [p for p in P]


def smooth_body(M, rounds=3, lam=0.45, mu=-0.47):
    """The fitted body smoothed (Taubin's two steps, which keep its size): the rings' creases and the fitting's small
    dents softened, so every form reads as a smooth round surface. The head, the hands, the torso's top ring (the
    neck's seam) and the wrists are held."""
    P = np.array(M.P)
    E = edges_of(M.faces)
    fams = np.array([part_family(p) for p in M.part])
    sel = np.isin(fams, ("torso", "shoulder", "arm", "leg") + (() if FOOT_N else ("foot",)))
    sel[M.tag["torso_rings"][-1]] = False
    for sfx in ("_l", "_r"):
        for ring in M.tag["arm_rings" + sfx][-2:]:
            sel[ring] = False
    deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
    sel &= deg > 0
    for _ in range(rounds):
        for f in (lam, mu):
            acc = np.zeros_like(P)
            np.add.at(acc, E[:, 0], P[E[:, 1]])
            np.add.at(acc, E[:, 1], P[E[:, 0]])
            avg = acc / np.maximum(deg, 1)[:, None]
            P[sel] += (avg[sel] - P[sel]) * f
    M.P = [p for p in P]


def smooth_along(M, rounds=TORSO_ALONG_ROUNDS, lam=0.5, mu=-0.53):
    """Sixth round (the critic: "horizontal rings showing as a hard shelf under the pecs and stacked lumps down the
    back and flanks"): the torso's points smoothed along the body's length only (Taubin over the edges that run up and
    down, never round), so each ring's own bulge or dent, left by fitting each ring to the outlines on its own, is
    shared with its neighbours above and below; the cross-sections' shapes are kept. The neck's seam is held."""
    P = np.array(M.P)
    E = edges_of(M.faces)
    d = P[E[:, 1]] - P[E[:, 0]]
    vert = np.abs(d[:, 2]) > 0.75 * np.linalg.norm(d, axis=1)
    fams = np.array([part_family(p) for p in M.part])
    sel = fams == "torso"
    sel[M.tag["torso_rings"][-1]] = False
    sel[M.tag["torso_rings"][0]] = False
    E = E[vert & sel[E[:, 0]] & sel[E[:, 1]]]
    deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
    on = sel & (deg >= 2)
    P0 = P.copy()
    for _ in range(rounds):
        for f in (lam, mu):
            acc = np.zeros_like(P)
            np.add.at(acc, E[:, 0], P[E[:, 1]])
            np.add.at(acc, E[:, 1], P[E[:, 0]])
            avg = acc / np.maximum(deg, 1)[:, None]
            P[on] += (avg[on] - P[on]) * f
    print("%s TORSO smoothed along its length: %d points, most moved %.1f mm" % (WHO, int(on.sum()), 1000 * float(np.linalg.norm(P - P0, axis=1).max())))
    M.P = [p for p in P]


def taper_forearms(M, joints):
    """Sixth round (the critic: "the forearms are puffy and do not taper", "a hard cuff at the wrist: the forearm ends
    in a ledge and the hand starts narrower"): each forearm ring below its widest third drawn in about its own middle,
    more toward the wrist, so the last ring is as big round as the hand's own wrist loop and the forearm reads as a cone
    widest a third of the way down from the elbow."""
    P = np.array(M.P)
    for sfx, s in (("_l", 1), ("_r", -1)):
        E_ = np.array(mirror_x(joints["elbow_l"], s), float)
        W_ = np.array(mirror_x(joints["wrist_l"], s), float)
        ax = W_ - E_
        L = float(np.linalg.norm(ax))
        ax /= L
        a, b = M.tag["hand_range" + sfx]
        loop = [a + v for v in HB["loop"]]
        lc = P[loop].mean(0)
        r_loop = float(np.mean(np.linalg.norm((P[loop] - lc) - np.outer((P[loop] - lc) @ ax, ax), axis=1)))
        rings = M.tag["arm_rings" + sfx]
        last = rings[-1]
        c_last = P[last].mean(0)
        r_last = float(np.mean(np.linalg.norm((P[last] - c_last) - np.outer((P[last] - c_last) @ ax, ax), axis=1)))
        k_last = min(1.0, r_loop * WRIST_EASE / max(r_last, 1e-6))
        for ring in rings:
            c = P[ring].mean(0)
            t = float((c - E_) @ ax) / L
            if t <= FOREARM_WIDEST:
                continue
            u = min(1.0, (t - FOREARM_WIDEST) / (1.0 - FOREARM_WIDEST))
            k = 1.0 + (k_last - 1.0) * u ** 1.3
            off = P[ring] - c
            along = np.outer(off @ ax, ax)
            P[ring] = c + along + (off - along) * k
        print("%s ARM forearm%s tapered: the wrist ring times %.2f (its radius %.1f cm, the hand's loop %.1f cm)" % (
            WHO, sfx, k_last, r_last * 100, r_loop * 100))
    M.P = [p for p in P]


def smooth_shoulders(M, joints, reach=0.19, rounds=6, lam=0.5, mu=0.0):
    """Where the arm's tube meets the torso's rings the two loops meet at an angle and left a box's corner over the
    shoulder and folds at the armpits: the points within `reach` of each shoulder joint smoothed (Taubin), most at the
    joint and fading out, so the deltoid rounds into the trapezius and the armpit."""
    P = np.array(M.P)
    E = edges_of(M.faces)
    fams = np.array([part_family(p) for p in M.part])
    deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
    w = np.zeros(len(P))
    for s in (1, -1):
        J = np.array(mirror_x(joints["shoulder_l"], s))
        d = np.linalg.norm(P - J, axis=1)
        w = np.maximum(w, np.clip(1.0 - d / reach, 0, 1) ** 0.7)
    w *= np.isin(fams, ("torso", "shoulder", "arm")) & (deg > 0)
    w[M.tag["torso_rings"][-1]] = 0.0
    for _ in range(rounds):
        for f in ((lam, mu) if mu else (lam,)):
            acc = np.zeros_like(P)
            np.add.at(acc, E[:, 0], P[E[:, 1]])
            np.add.at(acc, E[:, 1], P[E[:, 0]])
            avg = acc / np.maximum(deg, 1)[:, None]
            P += (avg - P) * (f * w)[:, None]
    print("BROTHER shoulders smoothed: most moved %.1f cm" % (100 * float(np.linalg.norm(P - np.array(M.P), axis=1).max())))
    M.P = [p for p in P]


def round_shoulders(M, joints):
    """Third build (the coordinator: "an armpit/lat notch and boxy deltoid caps"): after the last outline fit the
    shoulders are smoothed again (Taubin, which keeps their size) so the arm's tube rounds into the trapezius, the
    armpits' notch is folded out, and a heavy round deltoid is laid over each shoulder's outer top (pushed out along
    the surface, most at its middle)."""
    smooth_shoulders(M, joints, reach=0.16, rounds=10, lam=0.5, mu=-0.53)
    smooth_armpits(M, reach=0.09, rounds=8)
    P = np.array(M.P)
    N = normals_of(P, M.tris())
    fams = np.array([part_family(p) for p in M.part])
    on = np.isin(fams, ("torso", "shoulder", "arm"))
    on[M.tag["torso_rings"][-1]] = False
    d = np.zeros(len(P))
    for s in (1, -1):
        J = np.array(mirror_x(joints["shoulder_l"], s))
        c = J + np.array((s * 0.03, 0.0, 0.012))
        d = np.maximum(d, np.exp(-(np.linalg.norm(P - c, axis=1) / 0.065) ** 2))
    P += N * (0.012 * d * on)[:, None]
    M.P = [p for p in P]


def smooth_head(M, rounds=8, lam=0.5, mu=-0.53):
    """The refined head smoothed (Taubin) before its forms are sculpted: splitting the rings' faces on curves left
    ripples between the rings, which read as bands across the face. The nose and the ears are held, as is the neck's
    seam to the torso."""
    P = np.array(M.P)
    E = edges_of(M.faces)
    fams = np.array([part_family(p) for p in M.part])
    deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
    sel = (fams == "head") & (deg > 0)
    # (the points the nose and the ears share with the head are not on them: the nose and ears are separate shells)
    for _ in range(rounds):
        for f in (lam, mu):
            acc = np.zeros_like(P)
            np.add.at(acc, E[:, 0], P[E[:, 1]])
            np.add.at(acc, E[:, 1], P[E[:, 0]])
            avg = acc / np.maximum(deg, 1)[:, None]
            P[sel] += (avg[sel] - P[sel]) * f
    M.P = [p for p in P]


def smooth_hands(M, rounds=2, lam=0.45, mu=-0.47):
    """Seventh round (the user: "his hands still seem poor quality"): the hands' points smoothed together (Taubin's
    two-step smoothing, which keeps their size), so the palm, the knuckles and where each finger leaves the palm read
    as one soft form, not facets and creases. The wrist (the arm's last ring) is held."""
    P = np.array(M.P)
    E = edges_of(M.faces)
    fams = np.array([part_family(p) for p in M.part])
    sel = fams == "hand"
    deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
    sel &= deg > 0
    for _ in range(rounds):
        for f in (lam, mu):
            acc = np.zeros_like(P)
            np.add.at(acc, E[:, 0], P[E[:, 1]])
            np.add.at(acc, E[:, 1], P[E[:, 0]])
            avg = acc / np.maximum(deg, 1)[:, None]
            P[sel] += (avg[sel] - P[sel]) * f
    M.P = [p for p in P]


def smooth_wrists(M, joints, reach=0.045, rounds=6):
    """Polish pass (the critic: "a hard ring/ledge at the wrist, like a glove joined onto a sleeve"): the points within
    `reach` of each wrist (the forearm's end, the bridge and the back of the hand, not the fingers) smoothed together,
    full at the wrist and fading out, Taubin's steps so the wrist keeps its thickness."""
    P = np.array(M.P)
    E = edges_of(M.faces)
    deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
    parts = np.array(M.part)
    fingers = np.array([p.count("_") >= 2 and p.startswith("hand") for p in parts])
    w = np.zeros(len(P))
    for s in (1, -1):
        Wj = np.array(mirror_x(joints["wrist_l"], s), float)
        d = np.linalg.norm(P - Wj, axis=1)
        w = np.maximum(w, 1.0 - smooth01(reach * 0.4, reach, d))
    w[fingers | (deg == 0)] = 0.0
    for _ in range(rounds):
        for f in (0.5, -0.52):
            acc = np.zeros_like(P)
            np.add.at(acc, E[:, 0], P[E[:, 1]])
            np.add.at(acc, E[:, 1], P[E[:, 0]])
            avg = acc / np.maximum(deg, 1)[:, None]
            P += (avg - P) * (f * w)[:, None]
    M.P = [p for p in P]
    print("BROTHER HAND wrists smoothed: %d points" % int((w > 0.01).sum()))


def smooth_ankles(M, joints, rounds=6):
    """Sixth round (the critic: "a hard horizontal ring seam in both geometry (a step) and paint" at the ankle, "the
    ankles are thick posts"): the shin's last rings drawn in toward the leg's axis (ANKLE_THIN at the ankle, fading
    out 12 cm up), then the points within 5 cm of the shin-to-foot seam smoothed together (Taubin), toes held."""
    P = np.array(M.P)
    parts = np.array(M.part)
    E = edges_of(M.faces)
    deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
    w = np.zeros(len(P))
    for sfx, s in (("_l", 1), ("_r", -1)):
        rings = M.tag["leg_rings" + sfx]
        z_a = float(P[rings[-1]][:, 2].mean())
        last = np.array(rings[-1])
        c = P[last].mean(0)
        # (the shin's points and the foot's top together, about the last ring's middle, so no step opens at the seam)
        mine = np.array([(p.startswith("leg" + sfx) or p.startswith("foot" + sfx)) for p in parts])
        z = P[:, 2]
        k = ANKLE_THIN * (1.0 - smooth01(z_a, z_a + 0.12, z)) * smooth01(z_a - 0.05, z_a - 0.015, z) * mine
        P[:, :2] = P[:, :2] - (P[:, :2] - c[:2]) * k[:, None]
        seam_z = z_a
        w = np.maximum(w, (1.0 - smooth01(0.012, 0.04, np.abs(z - z_a))) * mine)
    toes = np.array(["toe" in p for p in parts])
    w[toes | (deg == 0)] = 0.0
    for _ in range(rounds):
        for f in (0.5, -0.52):
            acc = np.zeros_like(P)
            np.add.at(acc, E[:, 0], P[E[:, 1]])
            np.add.at(acc, E[:, 1], P[E[:, 0]])
            avg = acc / np.maximum(deg, 1)[:, None]
            P += (avg - P) * (f * w)[:, None]
    M.P = [p for p in P]
    print("%s ANKLES thinned %.0f%% and smoothed: %d points" % (WHO, ANKLE_THIN * 100, int((w > 0.01).sum())))


def smooth_armpits(M, reach=0.1, rounds=12):
    """Stage one left a flap at each armpit: the torso's points under the arm's hole stood out past the hole's bottom
    (the front view hides that part of him, so the fitting never drew them in). The torso's points near each hole's
    bottom are smoothed (plain Laplacian, the hole's own points held), which folds the flap back into the side."""
    P = np.array(M.P)
    E = edges_of(M.faces)
    fams = np.array([part_family(p) for p in M.part])
    if os.environ.get("FINDBG"):
        T = M.tag["torso_rings"]
        for i in range(10, 18):
            print("FINDBG ring %d row %d: %s" % (i, TORSO_ROWS[i], " ".join(
                "%d:(%.3f,%.3f,%.3f)" % (k, *P[T[i][k]]) for k in range(1, 8))))
        print("FINDBG hole_l", np.round(P[M.tag["hole_l"]], 3).tolist())
    moved = 0
    for sfx in ("_l", "_r"):
        hole = M.tag["hole" + sfx]
        low = P[hole][np.argmin(P[hole][:, 2])]
        sel = (fams == "torso") & (np.linalg.norm(P - low, axis=1) < reach)
        sel[hole] = False
        sel &= np.bincount(E.ravel(), minlength=len(P)) > 0     # (the hole's inner points are in no face)
        w = np.clip(1.0 - np.linalg.norm(P - low, axis=1) / reach, 0, 1)[:, None] * 0.6
        before = P[sel].copy()
        for _ in range(rounds):
            acc = np.zeros_like(P)
            np.add.at(acc, E[:, 0], P[E[:, 1]])
            np.add.at(acc, E[:, 1], P[E[:, 0]])
            deg = np.bincount(E.ravel(), minlength=len(P))[:, None]
            avg = acc / np.maximum(deg, 1)
            P[sel] += (avg[sel] - P[sel]) * w[sel]
        if sel.any():
            moved = max(moved, float(np.linalg.norm(P[sel] - before, axis=1).max()))
    # A spike: a torso point standing out sideways past both its neighbours up and down the same column by more than
    # 1.5 cm (the sheet's front view, where the arm meets his side, measured him too wide on one ring) is put back
    # between them.
    T = M.tag["torso_rings"]
    spikes = 0
    deg0 = np.bincount(E.ravel(), minlength=len(P)) == 0
    holes = set(M.tag["hole_l"]) | set(M.tag["hole_r"]) | set(np.where(deg0)[0].tolist())
    for i in range(1, len(T) - 1):
        for k in range(TORSO_N):
            a, b, c = T[i - 1][k], T[i][k], T[i + 1][k]
            if {a, b, c} & holes:
                continue
            ref = (abs(P[a][0]) + abs(P[c][0])) / 2.0
            if abs(P[b][0]) > max(abs(P[a][0]), abs(P[c][0])) + 0.015:
                P[b][0] = math.copysign(ref, P[b][0])
                spikes += 1
    M.P = [p for p in P]
    print("BROTHER armpits smoothed: the most a point moved %.1f cm; %d spikes put back" % (moved * 100, spikes))


def textured_material(name, path):
    mat = bpy.data.materials.new(name)
    mat.use_backface_culling = True
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tex = nt.nodes.new("ShaderNodeTexImage")
    img = bpy.data.images.load(path)
    img.pack()
    tex.image = img
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 1.0
    for key in ("Specular IOR Level", "Specular"):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = 0.0
    return mat


def plain_material(name, rgb, metallic=0.0, rough=0.6):
    mat = bpy.data.materials.new(name)
    mat.use_backface_culling = True
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = rough
    return mat


def mesh_object(name, P, faces, armature, weights=None, rigid=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, p)) for p in P], [], faces)
    me.update()
    for poly in me.polygons:
        poly.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = armature
    mod = ob.modifiers.new("armature", "ARMATURE")
    mod.object = armature
    if weights is not None:
        groups = {}
        for vi, w in enumerate(weights):
            for bn, v in w.items():
                if bn not in groups:
                    groups[bn] = ob.vertex_groups.new(name=bn)
                groups[bn].add([vi], v, "REPLACE")
    if rigid:
        g = ob.vertex_groups.new(name=rigid)
        g.add(list(range(len(P))), 1.0, "REPLACE")
    return ob

def head_centre(M, z):
    H = M.tag["head_rings"]
    zs = [M.P[r[0]][2] for r in H]
    cs = [np.mean([M.P[i] for i in r], axis=0) for r in H]
    i = int(np.clip(np.searchsorted(zs, z), 1, len(zs) - 1))
    t = (z - zs[i - 1]) / max(zs[i] - zs[i - 1], 1e-6)
    c = cs[i - 1] * (1 - t) + cs[i] * t
    c[2] = z
    c[0] = 0.0
    return c


# ------------------------------------------------------------------------------------------------------------------
# Refining the face (fifth round). The rings give the head 16 points round: too few for a brow, eyes, cheeks or a
# mouth (the coordinator's grey render: "a flat sunken band where the eyes and brow should be"). After the UVs are
# planned, the head's faces are split once and the face's front twice (each quad into four; the new points on curved
# edges placed on the cubic between the corners' normals, as PN triangles do, so the split head stays round); faces
# next to a split one take the new edge points and are cut into triangles. UVs, weights and parts are carried over
# (old points keep their numbers, so the rings and tags still hold). Then the forms are moved into the face by sum.
# ------------------------------------------------------------------------------------------------------------------

# (2026-11-18, the round-seven head restored: every point refine() adds is recorded with its parents, so a head point
# can be named by how it was made from the base head's cage (head_sigs), the same in any build whatever its shape)
PARENTS = {}


def head_sigs(M, pts):
    """For each of `pts`, a name by its making: "c<k>" the cage's k-th point, "e(..)" an edge's middle, "f(..)" a face's
    middle, with their parents' names inside (sorted); None for a point not made from the cage."""
    loc = {v: k for k, v in enumerate(M.tag["base_head_pts"][:M.tag["n_cage"]])}
    memo = {}

    def sig(v):
        if v in memo:
            return memo[v]
        s = None
        if v in loc:
            s = "c%d" % loc[v]
        elif v in PARENTS:
            kind, par = PARENTS[v]
            subs = [sig(p) for p in par]
            if all(x is not None for x in subs):
                s = kind + "(" + ",".join(sorted(subs)) + ")"
        memo[v] = s
        return s
    return {int(v): sig(int(v)) for v in pts}


def refine(M, sel, face_uv, weights):
    """Splits the faces in `sel` (a set of face indices) once. Gives (new Mesh, new face_uv, new weights, children:
    {old face: [new faces]})."""
    P = np.array(M.P)
    N = normals_of(P, M.tris())
    R = Mesh()
    R.P = [p.copy() for p in P]
    R.part = list(M.part)
    R.tag = M.tag
    W = list(weights)
    mid = {}

    def edge_point(a, b):
        key = (min(a, b), max(a, b))
        if key not in mid:
            d = P[b] - P[a]
            ta = d - N[a] * np.dot(d, N[a])
            tb = d - N[b] * np.dot(d, N[b])
            q = (P[a] + P[b]) / 2.0 + (ta - tb) / 8.0
            mid[key] = R.add(q, M.part[a])
            PARENTS[mid[key]] = ("e", (a, b))
            w = {}
            for src in (weights[a], weights[b]):
                for k, v in src.items():
                    w[k] = w.get(k, 0.0) + v / 2.0
            W.append(w)
        return mid[key]
    # (every edge of a split face gets its point first, so the faces round them know)
    for fi in sel:
        f = M.faces[fi]
        for i in range(len(f)):
            edge_point(f[i], f[(i + 1) % len(f)])
    new_uv, children = {}, {}

    def put(fi, idx, uvs):
        R.faces.append(list(idx))
        R.fpart.append(M.fpart[fi])
        if fi in M.cell:
            R.cell[len(R.faces) - 1] = M.cell[fi]
        if fi in M.want:
            R.want[len(R.faces) - 1] = M.want[fi]
        if uvs is not None:
            new_uv[len(R.faces) - 1] = (face_uv[fi][0], uvs)
        children.setdefault(fi, []).append(len(R.faces) - 1)
    for fi, f in enumerate(M.faces):
        has_uv = fi in face_uv
        uv = [np.array(q) for q in face_uv[fi][1]] if has_uv else None
        n = len(f)
        if fi in sel:
            ms = [mid[(min(f[i], f[(i + 1) % n]), max(f[i], f[(i + 1) % n]))] for i in range(n)]
            muv = [(uv[i] + uv[(i + 1) % n]) / 2.0 for i in range(n)] if has_uv else None
            if n == 4:
                corners = [P[v] for v in f]
                cq = sum(R.P[m] for m in ms) / 2.0 - sum(corners) / 4.0
                c = R.add(cq, M.part[f[0]])
                PARENTS[c] = ("f", tuple(f))
                w = {}
                for v in f:
                    for k, x in weights[v].items():
                        w[k] = w.get(k, 0.0) + x / 4.0
                W.append(w)
                cuv = sum(uv) / 4.0 if has_uv else None
                for i in range(4):
                    j = (i - 1) % 4
                    put(fi, [f[i], ms[i], c, ms[j]], [uv[i], muv[i], cuv, muv[j]] if has_uv else None)
            else:
                for i in range(n):
                    j = (i - 1) % n
                    put(fi, [f[i], ms[i], ms[j]], [uv[i], muv[i], muv[j]] if has_uv else None)
                put(fi, list(ms), list(muv) if has_uv else None)
            continue
        # a face beside split ones: the edge points put into it, then cut into triangles from an edge point
        pts, puv = [], []
        for i in range(n):
            a, b = f[i], f[(i + 1) % n]
            pts.append(a)
            if has_uv:
                puv.append(uv[i])
            key = (min(a, b), max(a, b))
            if key in mid:
                pts.append(mid[key])
                if has_uv:
                    puv.append((uv[i] + uv[(i + 1) % n]) / 2.0)
        if len(pts) == n:
            put(fi, f, [uv[i] for i in range(n)] if has_uv else None)
            continue
        s = next(i for i, v in enumerate(pts) if v >= len(P))
        pts = pts[s:] + pts[:s]
        if has_uv:
            puv = puv[s:] + puv[:s]
        for i in range(1, len(pts) - 1):
            put(fi, [pts[0], pts[i], pts[i + 1]], [puv[0], puv[i], puv[i + 1]] if has_uv else None)
    new_uv = {k: (pic, [tuple(map(float, q)) for q in uvs]) for k, (pic, uvs) in new_uv.items()}
    return R, new_uv, W, children


def head_frame(M):
    """For the head's points: the head sheet's row, the column across the front view (pixels from the middle), and
    how squarely each faces forward."""
    P = np.array(M.P)
    N = normals_of(P, M.tris())
    row = head_row(P[:, 2])
    col = P[:, 0] / HEAD_SX
    return P, N, row, col, -N[:, 1]


def bump(row, col, r0, c0, sr, sc):
    return np.exp(-(((row - r0) / sr) ** 2 + ((np.abs(col) - c0) / sc) ** 2))


# The face's forms in the head sheet's front view (head2's bald front view: rows, and columns out from the middle, both sides alike;
# pixels of 1.06 mm): brows at 226, eyes at 248 (37 px out), round cheeks at 284, the mouth at 317. Each: (row,
# column, row spread, column spread, metres out along the surface; negative in).
FACE_FORMS = (
    # the brow ridge over the eyes and the glabella between them
    (992, 62, 6, 20, 0.002),
    # the eye sockets, the lids standing over the eyes, the soft bags under them
    (1034, 60, 8, 13, -0.004), (1031, 60, 4, 11, 0.0015),
    # the cheeks: full and round
    (1094, 96, 22, 28, 0.007),
    # the folds from the nose's wings toward the mouth's corners
    (1122, 64, 10, 8, -0.003),
    # the upper lip, the lower lip, the groove under it
    (1128, 0, 4, 10, -0.002), (1172, 0, 4, 20, -0.003),
    # a round chin with its small dimple
    (1218, 0, 5, 4, -0.002),
    # the temples, a little hollow
    (985, 125, 18, 14, -0.003),
)
# The smile: a groove along the mouth's line, its corners up (the sheet's soft smile): (middle row, rise at the
# corners, half width in pixels, depth in metres).
SMILE = (1146.0, 12.0, 76.0, -0.0025)


def sculpt_head(M):
    if "--noforms" in ARGS:
        return
    P, N, row, col, facing = head_frame(M)
    fam = np.array([part_family(p) for p in M.part])
    on = (fam == "head")
    w = np.clip((facing - 0.05) / 0.35, 0.0, 1.0) * on
    d = np.zeros(len(P))
    for r0, c0, sr, sc, amount in FACE_FORMS:
        d += amount * bump(row, col, r0, c0, sr, sc)
    r0, rise, half, depth = SMILE
    line = r0 - rise * np.clip(np.abs(col) / half, 0, 1.2) ** 2
    d += depth * np.exp(-((row - line) / 3.0) ** 2) * np.clip((half + 6 - np.abs(col)) / 10.0, 0, 1)
    P = P + N * (d * w)[:, None]
    M.P = [p for p in P]
    print("BROTHER face sculpted: %d points moved, most %.1f mm" % (int((np.abs(d * w) > 1e-4).sum()), 1000 * float(np.abs(d * w).max())))


# The forms the bald sheet paints that the base head lacks (the user's "boyish" square face: full round cheeks, the
# soft smile), moved into it along its normals where it faces forward. (row, column out from the middle, row spread,
# column spread, metres out; as FACE_FORMS.)
BASE_FACE_FORMS = (
    (1094, 92, 20, 26, 0.006),       # the cheeks, full and round
    (1122, 62, 9, 7, -0.002),        # the folds from the nose's wings toward the mouth's corners
    (985, 125, 18, 14, -0.002),      # the temples, a little hollow
    (994, 58, 6, 20, 0.0015),        # the brow's ridge
    # fifth round (the critic: "no lip forms: just a groove and a flat upper lip"; nostrils): the upper lip's volume, the
    # lower lip's roll, small dents at the mouth's corners, the nostrils under the ball of the nose
    (1138, 0, 5, 24, 0.0016),
    (1155, 0, 4, 20, 0.0022),
    (1147, 50, 4, 4, -0.0016),
    (1116, 15, 3, 6, -0.0025),
)


def base_face_forms(M):
    P, N, row, col, facing = head_frame(M)
    on = np.zeros(len(P), bool)
    on[M.tag["base_head_pts"]] = True
    w = np.clip((facing - 0.05) / 0.35, 0.0, 1.0) * on
    d = np.zeros(len(P))
    for r0, c0, sr, sc, amount in BASE_FACE_FORMS:
        d += amount * bump(row, col, r0, c0, sr, sc)
    r0, rise, half, depth = SMILE
    line = r0 - rise * np.clip(np.abs(col) / half, 0, 1.2) ** 2
    # (seventh round: the groove ends short of the mouth's corner and fades over 14 px, so it does not run on as a
    # crease toward the jaw)
    end = half * SMILE_HALF
    d += depth * np.exp(-((row - line) / 3.0) ** 2) * np.clip((end - np.abs(col)) / 14.0, 0, 1)
    P = P + N * (d * w)[:, None]
    M.P = [p for p in P]
    print("BROTHER face forms: most %.1f mm" % (1000 * float(np.abs(d * w).max())))


# Seventh round (the critic: "the lower jaw bulges out as a pouch, like a jowl bag, below a hard fold from the mouth
# corner"; "from below, the chin is a separate round knob"). Horizontal sections through the jaw (scratchpad jaw.py)
# showed the cross-section fault: 4.5 to 6 cm out from the middle the lower face stood up to 0.9 cm FURTHER forward
# at z 1.64 to 1.66 than at the mouth's corner (z 1.69), a pouch, where the shaved sheet's jaw falls back evenly
# from the mouth to its lower edge; neither outline (front, side) shows it, so the silhouettes passed.
# JAW_FIRM: (the mouth-corner row the reference section is taken at, how far back (m) each centimetre lower the jaw
# must at least fall back, the rows it works over (from, to), the |x| range (m) it works over).
JAW_FIRM = (1150.0, 0.0012, (1150.0, 1250.0), (0.03, 0.095))
SMILE_HALF = 0.78              # the smile's groove ends this share of SMILE's half width out (it ran on as a crease)
CHIN_ROUND = (0.03, 6)         # firm_jaw: (metres round the opening's front, Taubin rounds); None: none


# Seventh round (the critic: "ears small, flat and pinned to the head ... little inner-ear detail"): EAR_SHAPE =
# (grown in the side plane about the front of its root, turned out at the back (degrees), the rim raised (m), the bowl
# sunk (m)). The sheet's front-view ear width was within 2 mm, so the growth is kept small: the sheet wins over the
# critic's "20%".
EAR_SHAPE = (1.1, 9.0, 0.0022, 0.0035)


def shape_ears(R):
    """Each ear (a plate of rings round its middle): grown a little about the front of its root, its back turned out
    from the head, a rim raised round its edge and a bowl sunk inside it, the root (nearest the skull) held."""
    grow, turn, rim, bowl = EAR_SHAPE
    P = np.array(R.P)
    for key, s_ in (("ear_l", 1.0), ("ear_r", -1.0)):
        ids = np.array(R.tag[key])
        Q = P[ids].copy()
        out = s_ * Q[:, 0]
        x0, x1 = float(out.min()), float(out.max())
        held = np.clip((out - x0) / max(x1 - x0, 1e-4) / 0.35, 0, 1)
        y_f = float(Q[:, 1].min())
        z_c = float(Q[:, 2].mean())
        c = Q.mean(0)
        # grown in the side plane (y, z) about the front of the root
        Q[:, 1] = y_f + (Q[:, 1] - y_f) * (1 + (grow - 1) * held)
        Q[:, 2] = z_c + (Q[:, 2] - z_c) * (1 + (grow - 1) * held)
        # turned out: further from the head toward its back
        Q[:, 0] += s_ * math.tan(math.radians(turn)) * (Q[:, 1] - y_f) * held
        # rim and bowl by the elliptical radius round its middle
        ry = max(float(np.abs(Q[:, 1] - c[1]).max()), 1e-3)
        rz = max(float(np.abs(Q[:, 2] - c[2]).max()), 1e-3)
        r = np.sqrt(((Q[:, 1] - c[1]) / ry) ** 2 + ((Q[:, 2] - c[2]) / rz) ** 2)
        dx = rim * np.exp(-((r - 0.85) / 0.14) ** 2) - bowl * np.exp(-((r - 0.3) / 0.25) ** 2)
        Q[:, 0] += s_ * dx * held
        P[ids] = Q
    R.P = [p for p in P]
    print("%s EARS shaped: grown %.0f%%, turned out %.0f degrees, rim %.1f mm, bowl %.1f mm" % (
        WHO, (grow - 1) * 100, turn, rim * 1000, bowl * 1000))


def firm_jaw(R):
    """The lower face pulled back where it stands forward of its own section at the mouth's corner (less a steady
    fall-back per centimetre down), only toward the back (pure +y: the front outline and the chin's middle stay),
    then the jaw's lower face and the chin's underside evened out (Taubin) so no fold remains."""
    P = np.array(R.P)
    hp = np.array(R.tag["base_head_pts"])
    r_m, fall, (r0, r1), (x0, x1) = JAW_FIRM
    z_m = float(head_z(r_m))
    ax = np.abs(P[:, 0])
    ref_band = hp[(np.abs(P[hp, 2] - z_m) < 0.006) & (P[hp, 1] < 0.0)]
    bins = np.arange(0.0, 0.11, 0.005)
    ref = []
    for b in bins:
        sel = ref_band[np.abs(ax[ref_band] - b) < 0.006]
        ref.append(float(P[sel, 1].min()) if len(sel) else np.nan)
    ref = np.array(ref)
    good = ~np.isnan(ref)
    ref = np.interp(bins, bins[good], ref[good])
    rows = head_row(P[:, 2])
    on = np.zeros(len(P), bool)
    on[hp] = True
    on &= (rows > r0) & (rows < r1) & (P[:, 1] < -0.04)
    wx = smooth01(x0 - 0.01, x0 + 0.01, ax) * (1.0 - smooth01(x1 - 0.01, x1 + 0.01, ax))
    wr = smooth01(r0, r0 + 15, rows) * (1.0 - smooth01(r1 - 20, r1, rows))
    limit = np.interp(ax, bins, ref) + fall * np.clip((z_m - P[:, 2]) * 100.0, 0, None)
    push = np.clip(limit - P[:, 1], 0, None) * wx * wr * on
    P[:, 1] += push
    # (then the band and the chin's underside evened: the points moved, their neighbours, and the head's points under
    # the chin's lower edge forward of the neck)
    E = edges_of(R.faces)
    sel = push > 0.0005
    sel |= on & (rows > 1220) & (ax < 0.09)
    for _ in range(2):
        nb = sel.copy()
        nb[E[sel[E[:, 0]], 1]] = True
        nb[E[sel[E[:, 1]], 0]] = True
        sel = nb & np.isin(np.arange(len(P)), hp)
    sel[R.tag["neck_loop"]] = False
    deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
    for _ in range(4):
        for f in (0.5, -0.53):
            acc = np.zeros_like(P)
            np.add.at(acc, E[:, 0], P[E[:, 1]])
            np.add.at(acc, E[:, 1], P[E[:, 0]])
            avg = acc / np.maximum(deg, 1)[:, None]
            P[sel] += (avg[sel] - P[sel]) * f
    if CHIN_ROUND:
        # (eighth round, the critic: "the chin as a shelf with a hard undercut from below": the head's opening loop
        # under the chin, its two head rings and the neck bridge's first ring there rounded together (the loop
        # moved too), so the jaw's underside turns into the throat instead of meeting it at an edge)
        loop = np.array(R.tag["neck_loop"])
        front = loop[P[loop, 1] < -0.03]
        near = np.zeros(len(P), bool)
        if len(front):
            d = np.min(np.linalg.norm(P[:, None, :] - P[front][None, :, :], axis=2), axis=1)
            near = (d < CHIN_ROUND[0]) & (P[:, 1] < -0.02)
        rings = R.tag.get("neck_rings", [])
        allowed = np.isin(np.arange(len(P)), np.concatenate([hp, loop] + [np.array(r) for r in rings[:1]]))
        sel2 = near & allowed
        for _ in range(CHIN_ROUND[1]):
            for f in (0.5, -0.53):
                acc = np.zeros_like(P)
                np.add.at(acc, E[:, 0], P[E[:, 1]])
                np.add.at(acc, E[:, 1], P[E[:, 0]])
                avg = acc / np.maximum(deg, 1)[:, None]
                P[sel2] += (avg[sel2] - P[sel2]) * f
        print("%s CHIN rounded into the throat: %d points" % (WHO, int(sel2.sum())))
    R.P = [p for p in P]
    print("%s JAW firmed: the pouch pulled back up to %.1f mm on %d points; %d points evened" % (
        WHO, 1000 * float(push.max()), int((push > 0.0005).sum()), int(sel.sum())))


JAW_WIDEN = 0.0      # square_jaw: metres each jaw corner is pushed out sideways (a figure's "consts" sets it)
CHIN_BROAD = (0.0, 0.0)   # square_jaw: the chin's pad widened this share, and brought forward this many metres


def square_jaw(R):
    """Ninth round (the critic: "the jaw angle is weak, so cheek to neck is nearly one line"; "the chin is small and
    recedes ... from below it is pointed"). Measured on the shaved sheet's front view the jaw below the ears is up to a
    centimetre wider than the model (headdiff_final_front: the sheet's outline outside his there), so each jaw corner
    is pushed out sideways round the side view's jaw angle, and the chin's pad is widened and brought a little
    forward: a squarer lower face, as tpose8 and the head sheet draw it."""
    P = np.array(R.P)
    hp = np.array(R.tag["base_head_pts"])
    Q = P[hp]
    smid = HEAD_VIEWS["side"][1]
    ya, za = -(JAW_ANGLE[0] - smid) * HEAD_SX, float(head_z(JAW_ANGLE[1]))
    zc = float(head_z(CHIN_BOTTOM[1]))
    ax = np.abs(Q[:, 0])
    # the jaw's corner: round the angle's height, behind the mouth, out at the sides
    w = (np.exp(-((Q[:, 2] - za) / 0.024) ** 2) * np.exp(-((Q[:, 1] - ya) / 0.04) ** 2)
         * np.clip((ax - 0.025) / 0.03, 0, 1))
    Q[:, 0] += np.sign(Q[:, 0]) * JAW_WIDEN * w
    # the chin's pad: its front between the chin's underside and the lower lip
    band = (Q[:, 2] > zc - 0.005) & (Q[:, 2] < zc + 0.045) & (ax < 0.05)
    yfront = float(Q[band, 1].min()) if band.any() else 0.0
    wc = (np.exp(-((Q[:, 2] - (zc + 0.016)) / 0.02) ** 2) * np.clip((yfront + 0.035 - Q[:, 1]) / 0.02, 0, 1)
          * np.clip((0.06 - ax) / 0.02, 0, 1))
    Q[:, 0] *= 1.0 + CHIN_BROAD[0] * wc
    Q[:, 1] -= CHIN_BROAD[1] * wc
    P[hp] = Q
    R.P = [p for p in P]
    print("%s JAW squared: corners out %.1f mm on %d points, chin %.0f%% wider and %.1f mm forward on %d" % (
        WHO, JAW_WIDEN * 1000, int((w > 0.3).sum()), CHIN_BROAD[0] * 100, CHIN_BROAD[1] * 1000, int((wc > 0.3).sum())))


# Tenth round (the critic: "he reads 35 to 45, not 19 ... a long, narrow, egg-shaped face"; "seen front-on, the head is
# barely wider than the neck"). Measured on tpose8's front view (scratchpad brother10/ratios.py, 1.39 mm a pixel, chin
# row 330): the face 0.229 m across at the mouth's height (z 1.69), the neck 0.195 under the jaw, the shoulders 0.62;
# the ninth model 0.171 at the mouth, 0.165 under the jaw, 0.61 at the shoulders. So his shoulders and his head's
# height were right (1/6.5 of him) and his FACE was too narrow: the head is widened across only (x, about its middle
# line), most at the jaw and mouth, less at the cheeks and temples, a little at the crown, none at the neck's base;
# the ears are moved out with the skull at their roots but not grown; then the crown evened (Taubin) so the egg's
# point and facets round off. The shaved sheet's front outline is narrower than this (its painting also reads older):
# tpose8, his own body sheet, wins. HEAD_WIDEN: ((z, factor), ...); CROWN_ROUND: (rounds, from z).
HEAD_WIDEN = ()
CROWN_ROUND = (0, 1.84)
NOSE_SHORT = 0.0
DOME_FROM = 0.0       # youth_head: the level (z, m) the skull's dome stands on (0: none), and how far the crown comes down
DOME_DROP = 0.0
NECK_EASE = 0         # youth_head: Taubin rounds over the neck's two joins


def youth_head(R):
    global EYE_INNER, EYE_OUTER, EYE_TOP, EYE_LOW, EYE_IRIS, EYE_ZONE, EYE_RX, EYE_RAD, SMILE
    P = np.array(R.P)
    zs, ks = (np.array(v, float) for v in zip(*(HEAD_WIDEN or ((0.0, 1.0), (9.0, 1.0)))))
    kz = lambda z: np.interp(z, zs, ks)
    ears = set(R.tag["ear_l"]) | set(R.tag["ear_r"])
    ids = [v for v in R.tag["base_head_pts"] if v not in ears]
    ids += [v for ring in R.tag.get("neck_rings", []) for v in ring if v not in ears]
    ids = np.array(sorted(set(ids)))
    P[ids, 0] *= kz(P[ids, 2])
    for key in ("ear_l", "ear_r"):
        e = np.array(R.tag[key])
        ax = np.abs(P[e, 0])
        root = e[ax <= np.quantile(ax, 0.3)]
        x_r = float(P[root, 0].mean())
        P[e, 0] += x_r * (float(kz(P[root, 2].mean())) - 1.0)
    # (the nose, the critic: "shorten the projection by about 15%": every point of the nose's zone standing forward of
    # the cheeks beside it is brought back by NOSE_SHORT of that, most on the middle line)
    if NOSE_SHORT:
        hpa = np.array([v for v in R.tag["base_head_pts"] if v not in ears])
        z_lo, z_hi = float(head_z(NOSE[-1][0] + 6)), float(head_z(NOSE[0][0]))
        side = hpa[(np.abs(P[hpa, 0]) > 0.03) & (np.abs(P[hpa, 0]) < 0.04) & (P[hpa, 1] < -0.05)]
        moved = 0.0
        for v in hpa:
            x, y, z = P[v]
            if abs(x) > 0.032 or z < z_lo - 0.004 or z > z_hi or y > -0.05:
                continue
            near = side[np.abs(P[side, 2] - z) < 0.006]
            if not len(near):
                continue
            d = float(P[near, 1].min()) - y
            if d > 0:
                dd = NOSE_SHORT * d * (1.0 - float(smooth01(0.012, 0.032, abs(x)))) * float(smooth01(z_lo - 0.004, z_lo + 0.004, z))
                P[v, 1] += dd
                moved = max(moved, dd)
        print("%s NOSE shortened: at most %.1f mm back" % (WHO, moved * 1000))
    R.P = [p for p in P]
    # (the dome: the head's points above DOME_FROM laid onto a half ellipsoid standing on that level (as wide and deep
    # as the head is there, as high as the crown), faded in over 2.5 cm: an even round skull, no egg point, no flat top
    # with corners. The sheets (both rows of head3) draw one smooth arc from temple to temple.)
    if DOME_FROM:
        hpa = np.array([v for v in R.tag["base_head_pts"] if v not in ears])
        Q = P[hpa]
        band = np.abs(Q[:, 2] - DOME_FROM) < 0.006
        a_ = float(np.abs(Q[band, 0]).max())
        y0, y1 = float(Q[band, 1].min()), float(Q[band, 1].max())
        top = float(Q[:, 2].max()) - DOME_DROP
        C_ = np.array((0.0, (y0 + y1) / 2.0, DOME_FROM))
        rad = np.array((a_, (y1 - y0) / 2.0, top - DOME_FROM))
        up = Q[:, 2] > DOME_FROM - 0.03
        d = (Q - C_) / rad
        n_ = np.linalg.norm(d, axis=1, keepdims=True)
        on_ = C_ + d / np.maximum(n_, 1e-9) * rad
        w = (smooth01(DOME_FROM - 0.005, DOME_FROM + 0.025, Q[:, 2]) * up)[:, None]
        P[hpa] = Q * (1 - w) + on_ * w
        print("%s DOME: from z %.3f, half width %.3f, half depth %.3f, height %.3f (crown down %.1f mm)" % (
            WHO, DOME_FROM, rad[0], rad[1], rad[2], DOME_DROP * 1000))
        R.P = [p for p in P]
    # (the crown: Taubin rounds over the head's points above CROWN_ROUND's z, faded in over 3 cm)
    n_r, z0 = CROWN_ROUND
    if n_r:
        hp = np.zeros(len(P), bool)
        hp[[v for v in R.tag["base_head_pts"] if v not in ears]] = True
        w = hp * smooth01(z0 - 0.03, z0, P[:, 2])
        sel = w > 0.02
        E = edges_of(R.faces)
        deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
        before = P.copy()
        for _ in range(n_r):
            for f in (0.5, -0.53):
                acc = np.zeros_like(P)
                np.add.at(acc, E[:, 0], P[E[:, 1]])
                np.add.at(acc, E[:, 1], P[E[:, 0]])
                avg = acc / np.maximum(deg, 1)[:, None]
                P[sel] += (avg[sel] - P[sel]) * f
        P = before + (P - before) * w[:, None]
        R.P = [p for p in P]
    # (the neck's two joins evened, the critic: "a dark line circles the neck at the base of the head" (a lit ridge
    # where the neck's bridge meets the torso's top ring: Blender close-up, scratchpad brother10/a2/neck.png) and "a
    # sharp concave notch where the jaw meets the throat": Taubin rounds over the points near the torso's top ring and
    # near the head's opening loop, the loops themselves included)
    if NECK_EASE:
        P = np.array(R.P)
        topr = np.array(R.tag["torso_rings"][-1])
        loop = np.array(R.tag["neck_loop"])
        fams = np.array([part_family(p) for p in R.part])
        d1 = np.min(np.linalg.norm(P[:, None, :] - P[topr][None, :, :], axis=2), axis=1)
        d2 = np.min(np.linalg.norm(P[:, None, :] - P[loop][None, :, :], axis=2), axis=1)
        sel = ((d1 < 0.03) | (d2 < 0.018)) & np.isin(fams, ("torso", "neck", "head", "shoulder"))
        E = edges_of(R.faces)
        deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
        for _ in range(NECK_EASE):
            for f in (0.5, -0.53):
                acc = np.zeros_like(P)
                np.add.at(acc, E[:, 0], P[E[:, 1]])
                np.add.at(acc, E[:, 1], P[E[:, 0]])
                avg = acc / np.maximum(deg, 1)[:, None]
                P[sel] += (avg[sel] - P[sel]) * f
        R.P = [p for p in P]
        print("%s NECK eased: %d points, %d rounds" % (WHO, int(sel.sum()), NECK_EASE))
    # the face's sheet columns (eyes, smile) widened with it, so the eyes are cut and painted where the face now is
    ke = float(kz(head_z(EYE_IRIS[1])))
    km = float(kz(head_z(SMILE[0])))
    EYE_INNER = (EYE_INNER[0] * ke, EYE_INNER[1])
    EYE_OUTER = (EYE_OUTER[0] * ke, EYE_OUTER[1])
    EYE_TOP = (EYE_TOP[0] * ke, EYE_TOP[1])
    EYE_LOW = (EYE_LOW[0] * ke, EYE_LOW[1])
    EYE_IRIS = (EYE_IRIS[0] * ke, EYE_IRIS[1], EYE_IRIS[2])
    EYE_ZONE = (EYE_ZONE[0] * ke, EYE_ZONE[1])
    EYE_RX = EYE_RX * ke
    EYE_RAD = np.array((EYE_RX, EYE_R, EYE_R))
    SMILE = (SMILE[0], SMILE[1], SMILE[2] * km, SMILE[3])
    print("%s HEAD widened (youth): x times %s at z %s; eyes' columns times %.3f, mouth's %.3f; crown %d rounds above %.2f m" % (
        WHO, list(ks), list(zs), ke, km, n_r, z0))


def fresh_face_ease(R):
    """(eleventh round) The lower face between the nose's wings and the jaw evened (Taubin, faded in at the zone's
    edges), the mouth's loop and its near points held: the base's nasolabial loop, drawn into a hard crease by the
    outline fit and the widened nose, read as a fold from the nose to the jaw (age)."""
    (r0, r1), (c0, c1), n = FACE_EASE
    P = np.array(R.P)
    hp = np.zeros(len(P), bool)
    hp[R.tag["base_head_pts"]] = True
    row = head_row(P[:, 2])
    col = np.abs(P[:, 0]) / HEAD_SX
    w = (smooth01(r0, r0 + 12, row) * (1 - smooth01(r1 - 12, r1, row)) * smooth01(c0, c0 + 10, col)
         * (1 - smooth01(c1 - 12, c1, col)) * (P[:, 1] < -0.04) * hp)
    loop = R.tag.get("mouth_line") or []
    if loop:
        d = np.min(np.linalg.norm(P[:, None, :] - P[loop][None, :, :], axis=2), axis=1)
        w = w * smooth01(0.004, 0.012, d)
    sel = w > 0.01
    E = edges_of(R.faces)
    deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
    before = P.copy()
    for _ in range(n):
        for f in (0.5, -0.53):
            acc = np.zeros_like(P)
            np.add.at(acc, E[:, 0], P[E[:, 1]])
            np.add.at(acc, E[:, 1], P[E[:, 0]])
            avg = acc / np.maximum(deg, 1)[:, None]
            P[sel] += (avg[sel] - P[sel]) * f
    P = before + (P - before) * w[:, None]
    R.P = [p for p in P]
    print("%s FACE eased: %d points, %d rounds, most moved %.1f mm" % (
        WHO, int(sel.sum()), n, 1000 * float(np.linalg.norm(P - before, axis=1).max())))


# ------------------------------------------------------------------------------------------------------------------
# The FROZEN head and its adjustments (2026-11-18, the user: "Are you rebuilding the whole head each revision? I'm not
# seeing improvement, you should just be making adjustments"). The fresh head as refine_base_head leaves it (the
# head's points and the neck's rings, before the eyes are cut) is saved once to HEAD_FROZEN (`-- --refreeze`) and every
# later build loads exactly those points in place of what the earlier steps made (`-- --no-frozen` regenerates
# instead). The earlier head steps are not to be edited any more: changes to his head are the named adjustments below,
# applied in order on the frozen points, each a local move with a smooth falloff, each with its own switch and amount;
# each was kept only if a before/after pair beside the sheet showed it moving toward the sheet (scratchpad
# brother11/adjustments.png).
# ------------------------------------------------------------------------------------------------------------------
HEAD_FROZEN = os.path.join(HERE, "blend", "brother_head_base.npz")
# (name, on, amount in metres); the kinds are in adjust_head
HEAD_ADJUST = []
if "--adj" in ARGS:     # (trying adjustments: `-- --adj name=metres,name=metres` in place of the list)
    HEAD_ADJUST = [(k, True, float(v)) for k, v in (s.split("=") for s in arg("--adj", "").split(",") if s)]


def frozen_ids(R):
    return np.array(sorted(set(R.tag["base_head_pts"]) | {v for ring in R.tag.get("neck_rings", []) for v in ring}))


def freeze_or_load_head(R):
    if HEAD_ROUTE != "fresh" or FIGURE_NAME != "brother" or "--no-frozen" in ARGS:
        return
    ids = frozen_ids(R)
    P = np.array(R.P)
    if "--refreeze" in ARGS or not os.path.exists(HEAD_FROZEN):
        np.savez(HEAD_FROZEN, ids=ids, P=P[ids], n=len(P))
        print("%s HEAD frozen: %d points saved to %s" % (WHO, len(ids), HEAD_FROZEN))
        return
    z = np.load(HEAD_FROZEN)
    if int(z["n"]) != len(P) or not np.array_equal(z["ids"], ids):
        raise RuntimeError("the frozen head does not fit this build's mesh (%d points, file %d): `-- --no-frozen` or "
                           "`-- --refreeze`" % (len(P), int(z["n"])))
    moved = float(np.abs(P[ids] - z["P"]).max())
    P[ids] = z["P"]
    R.P = [p for p in P]
    print("%s HEAD loaded frozen: %d points (the regenerated head differed by at most %.2f mm)" % (WHO, len(ids), moved * 1000))


def adjust_head(R):
    """The named adjustments on the frozen head, in HEAD_ADJUST's order."""
    if HEAD_ROUTE != "fresh" or FIGURE_NAME != "brother":
        return
    P = np.array(R.P)
    hp = np.zeros(len(P), bool)
    hp[R.tag["base_head_pts"]] = True
    ears = np.zeros(len(P), bool)
    ears[list(R.tag["ear_l"]) + list(R.tag["ear_r"])] = True
    N = normals_of(P, R.tris())
    row = head_row(P[:, 2])
    col = np.abs(P[:, 0]) / HEAD_SX
    sx = np.sign(P[:, 0])
    smid = HEAD_VIEWS["side"][1]
    face = hp & ~ears & (P[:, 1] < -0.02)
    g = lambda r0, c0, sr, sc: np.exp(-(((row - r0) / sr) ** 2 + ((col - c0) / sc) ** 2))
    for name, on, amt in HEAD_ADJUST:
        if not on:
            continue
        d = np.zeros_like(P)
        if name == "jaw_corners_wider":
            # out sideways round the jaw's angle (the side view's), behind the mouth
            ya, za = -(JAW_ANGLE[0] - smid) * HEAD_SX, float(head_z(JAW_ANGLE[1]))
            w = (np.exp(-((P[:, 2] - za) / 0.03) ** 2) * np.exp(-((P[:, 1] - ya) / 0.05) ** 2)
                 * np.clip((col - 30.0) / 40.0, 0, 1)) * hp * ~ears
            d[:, 0] = sx * amt * w
        elif name == "nose_tip_bigger":
            w = g(1112.0, 0.0, 10.0, 17.0) * face
            d = N * (amt * w)[:, None]
        elif name == "nose_wings_wider":
            w = g(1124.0, 30.0, 8.0, 12.0) * face
            d[:, 0] = sx * amt * w
        elif name == "chin_forward":
            w = g(1228.0, 0.0, 14.0, 34.0) * face
            d[:, 1] = -amt * w
        elif name == "cheeks_fuller":
            w = g(1098.0, 82.0, 20.0, 26.0) * face
            d = N * (amt * w)[:, None]
        elif name == "brow_ridge":
            w = g(1014.0, 50.0, 6.0, 26.0) * face
            d = N * (amt * w)[:, None]
        else:
            raise RuntimeError("no such head adjustment: %s" % name)
        P += d
        print("%s HEAD adjust %s: %.1f mm, most moved %.1f mm on %d points" % (
            WHO, name, amt * 1000, 1000 * float(np.linalg.norm(d, axis=1).max()), int((np.linalg.norm(d, axis=1) > 0.0003).sum())))
    R.P = [p for p in P]


# ------------------------------------------------------------------------------------------------------------------
# THE ROUND-SEVEN HEAD (2026-11-18, the user: "The brother had a much better earlier head unless I'm mistaken": the
# head of commit 61a8380, built to concept_brother_head2.jpg, broad skull, strong brows, big nose, full cheeks, kind
# closed smile; rounds 8 to 10 refitted it to the shaved head3 sheet and lost him). Frozen as the brother's base head
# (the figure's "head_route": "r7"): tools/blend/brother_head_r7.json holds every head point of that build by how it
# was made from the base mesh's cage (head_sigs: the same names in any build), the cage faces taken out for the neck,
# the faces it split, and its eye and mouth landmarks; tools/blend/brother_head_r7_face.npz holds its painted face
# picture as coloured points on that surface. Made once by running 61a8380's build with a dump added (scratchpad
# brother11/build_brother_r7.py); this build lays those points on the current body (moved back R7_BACK, the ninth
# round's HEAD_BACK, so the face stands over tpose8's), bridges the neck to the current torso again, cuts the eyes
# with round seven's landmarks, and carries the painted face over by nearest point, its skin brought to the current
# peach tone. The head steps before this are not used for it; changes to it are the named adjustments (adjust_r7).
# ------------------------------------------------------------------------------------------------------------------
R7_JSON = os.path.join(HERE, "blend", "brother_head_r7.json")
R7_FACE = os.path.join(HERE, "blend", "brother_head_r7_face.npz")
R7_CENTRE = np.array((0.0, -0.02, 1.78))
R7_BACK = 0.022
R7 = {}
# The adjustments, in order: (name, on, amount). Each kept only if its before/after pair beside the sheet showed it
# moving toward the sheet (scratchpad brother11/adjustments.png).
R7_ADJUST = [("nose_less_red", True, 0.6),          # kept: the nose no redder than the cheeks (pair_n1)
             ("nose_bridge_straight", False, 0.004),  # dropped: no visible change at game distance (pair_n4)
             ("nose_tip_planes", False, 0.0015),      # dropped: moved two points only
             ("eyes_downturn", False, 3.0),           # dropped: the cut no longer met round seven's painted lids (e1)
             ("eye_bags", False, 0.0008)]             # dropped with it
if "--r7adj" in ARGS:     # (trying adjustments: `-- --r7adj name=amount,name=amount` in place of the list)
    R7_ADJUST = [(k, True, float(v)) for k, v in (s.split("=") for s in arg("--r7adj", "").split(",") if s)]
MOUTH_SNAP_MAX = 1.0      # snap_mouth_line: the most (m) the lips' loop is moved (the r7 head: a few millimetres)


def r7_load():
    if not R7:
        R7.update(json.load(open(R7_JSON)))
    return R7


def r7_place(R):
    """The round-seven head's points laid on R (after refine_base_head's split, which took round seven's own faces),
    then the neck's two bridge rings remade between its opening and the torso's top ring."""
    d = r7_load()
    pts = d["pts"]
    sig = head_sigs(R, R.tag["base_head_pts"])
    P = np.array(R.P)
    miss = 0
    for v, s in sig.items():
        if s in pts:
            P[v] = np.array(pts[s]) + np.array((0.0, R7_BACK, 0.0))
        else:
            miss += 1
    # the neck's bridge again (as base_head step 8 makes it), from the laid head's opening to the torso's top ring
    loop = list(R.tag["neck_loop"])
    top = list(R.tag["torso_rings"][-1])
    seg = np.linalg.norm(P[loop] - P[loop[1:] + loop[:1]], axis=1)
    uL = np.concatenate([[0.0], np.cumsum(seg)[:-1]]) / seg.sum()
    uT = np.arange(len(top)) / float(len(top))
    Qe = np.concatenate([P[loop], P[loop[:1]]])
    Lr = np.stack([np.interp(uT, np.append(uL, 1.0), Qe[:, k]) for k in range(3)], 1)
    Tr = P[top]
    for t, ring in zip((0.3, 0.65), R.tag["neck_rings"]):
        Q = Lr * (1 - t) + Tr * t
        c = Q.mean(0)
        Q[:, :2] = c[:2] + (Q[:, :2] - c[:2]) * (1.0 + 0.04 * math.sin(math.pi * t))
        P[ring] = Q
    R.P = [p for p in P]
    print("%s R7 head laid: %d points, %d not named in the file (kept as made)" % (WHO, len(sig) - miss, miss))


def r7_face(M, face_uv, tone):
    """The round-seven painted face carried onto this build's face picture by nearest point (the same surface), its
    skin brought to `tone` (the hue and lightness of its own plain skin moved onto the current peach; reds, browns and
    whites keep their difference from it)."""
    z = np.load(R7_FACE)
    cpos = z["pos"].astype(float) + R7_CENTRE + np.array((0.0, R7_BACK, 0.0))
    crgb = z["rgb"].astype(float) / 255.0
    P = np.array(M.P)
    pos, nrm, hit, fid = texel_geometry(M, face_uv, "face", P, normals_of(P, M.tris()))
    bad = ~(np.isfinite(pos).all(-1))
    hit = hit & ~bad
    kd = kdtree.KDTree(len(cpos))
    for i, p in enumerate(cpos):
        kd.insert(Vector(p), i)
    kd.balance()
    out = np.zeros(pos.shape)
    dist = np.zeros(pos.shape[:2])
    ii = np.argwhere(hit)
    for r_, c_ in ii:
        _, k, dd = kd.find(Vector(pos[r_, c_]))
        out[r_, c_] = crgb[k]
        dist[r_, c_] = dd
    far = int((dist > 0.004).sum())
    skin = np.median(crgb, 0)
    lum = lambda x: x.mean(-1, keepdims=True)
    # (the colour's ratio to the old plain skin, laid on the new one: a texel as red as the old cheeks stays as red
    # against the new skin)
    out = np.where(hit[..., None], np.clip(out / np.maximum(skin, 1e-3) * tone, 0, 1), 0.0)
    # (where this surface is not the old one (the neck's bridge to the new body, the lids' cut), plain skin)
    wf = smooth01(0.003, 0.01, dist)[..., None]
    out = np.where(hit[..., None], out * (1 - wf) + np.asarray(tone) * wf, 0.0)
    print("%s R7 face carried: %d texels (%d more than 4 mm from the old surface), old skin %s -> %s" % (
        WHO, len(ii), far, np.round(skin, 3), np.round(tone, 3)))
    return out, pos, hit, np.array(tone, float)


def adjust_r7(R):
    """The named adjustments on the laid round-seven head (geometry); the paint ones are in r7_paint_adjust."""
    if HEAD_ROUTE != "r7":
        return
    P = np.array(R.P)
    hp = np.zeros(len(P), bool)
    hp[R.tag["base_head_pts"]] = True
    N = normals_of(P, R.tris())
    row = head_row(P[:, 2] - 0.0)
    col = np.abs(P[:, 0]) / HEAD_SX
    face = hp & (P[:, 1] < -0.02)
    g = lambda r0, c0, sr, sc: np.exp(-(((row - r0) / sr) ** 2 + ((col - c0) / sc) ** 2))
    for name, on, amt in R7_ADJUST:
        if not on or name in R7_PAINT_ADJ or name in R7_EYE_ADJ:
            continue
        d = np.zeros_like(P)
        if name == "nose_bridge_straight":
            # (the user: "a tad angular": the bridge's dip filled toward a straight line from the brow to the tip, the
            # bridge's middle only)
            w = g(1062.0, 0.0, 22.0, 13.0) * face
            d[:, 1] = -amt * w
        elif name == "nose_tip_planes":
            # (the tip less of a round button: its front pressed flatter, its sides kept)
            w = g(1100.0, 0.0, 10.0, 11.0) * face
            d = -N * (amt * w)[:, None]
        else:
            raise RuntimeError("no such head adjustment: %s" % name)
        P += d
        print("%s R7 adjust %s: %.1f mm, %d points moved" % (WHO, name, amt * 1000, int((np.linalg.norm(d, axis=1) > 0.0003).sum())))
    R.P = [p for p in P]


R7_PAINT_ADJ = ("nose_less_red",)
R7_EYE_ADJ = ("eyes_downturn", "eye_bags")


def r7_eye_adjust():
    for name, on, amt in R7_ADJUST:
        if on and name == "eyes_downturn":
            FIGURE["eye_down"] = FIGURE.get("eye_down", 0.0) + amt
        elif on and name == "eye_bags":
            FIGURE["bags"] = FIGURE.get("bags", 0.0) + amt
        else:
            continue
        print("%s R7 adjust %s: %+.4f (eye_down %.1f px, bags %.1f mm)" % (WHO, name, amt, FIGURE.get("eye_down", 0.0), 1000 * FIGURE.get("bags", 0.0)))


def r7_paint_adjust(face, fpos, fhit, M):
    for name, on, amt in R7_ADJUST:
        if not (on and name == "nose_less_red"):
            continue
        # (the user: "a bit too red button nosed": the nose's flush taken toward the cheeks' level: within 2 cm of the
        # tip, the red's excess over the skin's own red/green balance cut by `amt`)
        P = np.array(M.P)
        hp = np.array(M.tag["base_head_pts"])
        nz = hp[np.abs(P[hp, 0]) < 0.006]
        tip = P[nz[np.argmin(P[nz, 1])]]
        w = np.exp(-(np.linalg.norm(fpos - tip, axis=-1) / 0.02) ** 2) * fhit
        skin = np.median(face[fhit], 0)
        ratio = skin[1] / skin[0]
        g_ = face[..., 0] * ratio
        excess = np.clip(g_ - face[..., 1], 0, None)
        face = face.copy()
        face[..., 1] += excess * amt * w
        face[..., 2] += excess * amt * w * (skin[2] / skin[1])
        print("%s R7 adjust nose_less_red: %.2f of the nose's extra red taken out" % (WHO, amt))
    return np.clip(face, 0, 1)


def fresh_mouth_widen(R):
    """(eleventh round) The mouth's corners moved out by MOUTH_WIDEN (head3's top row draws a mouth well over half the
    face's width, the base's is narrower): every head point forward of the cheeks within the mouth's rows is moved out
    in proportion to how far out it is, most at the corners, fading to nothing beyond them and above and below."""
    P = np.array(R.P)
    hp = np.zeros(len(P), bool)
    hp[R.tag["base_head_pts"]] = True
    line = R.tag["mouth_line"]
    xc = float(np.abs(P[line, 0]).max())
    zm = float(np.mean(P[line, 2]))
    ax = np.abs(P[:, 0])
    t = np.clip(ax / xc, 0, None)
    w = np.where(t <= 1.0, t, np.exp(-((t - 1.0) / 0.45) ** 2)) * np.exp(-((P[:, 2] - zm) / 0.016) ** 2) * hp * (P[:, 1] < -0.06)
    P[:, 0] += np.sign(P[:, 0]) * xc * (MOUTH_WIDEN - 1.0) * w
    R.P = [p for p in P]
    print("%s MOUTH widened: corners %.1f -> %.1f mm out" % (WHO, xc * 1000, xc * MOUTH_WIDEN * 1000))


def fresh_jaw_line(R):
    """(eleventh round, the critic: "under the chin the jaw melts into the neck") The jaw's underside, from the chin back
    toward the angle, drawn up along its normal under the jaw's edge, and the neck's first ring there drawn in, so the
    jaw has an edge from ear to chin that holds when the head tilts back."""
    P = np.array(R.P)
    N = normals_of(P, R.tris())
    fams = np.array([part_family(p) for p in R.part])
    zc = float(head_z(CHIN_BOTTOM[1]))
    za = float(head_z(JAW_ANGLE[1]))
    down = np.clip((-N[:, 2] - 0.25) / 0.4, 0, 1)
    band = np.exp(-((P[:, 2] - (zc + 0.008)) / 0.022) ** 2)
    front = smooth01(0.03, -0.05, P[:, 1])
    on = np.isin(fams, ("head", "neck"))
    d = JAW_LINE * down * band * front * on
    loop = R.tag["neck_loop"]
    d[loop] *= 1.0
    P -= N * d[:, None]
    R.P = [p for p in P]
    print("%s JAW line: underside drawn up, most %.1f mm on %d points" % (WHO, 1000 * float(d.max()), int((d > 0.0005).sum())))


def refine_base_head(M, face_uv, weights, under, sh):
    """Third build: the base head's face (brow to chin, the faces turned forward) split once, the new points placed
    on the curved surface (refine); then two more outline rounds on the denser face."""
    P = np.array(M.P)
    # (the whole head but the ears: the cage alone showed its facets along the skull's outline)
    ears = set(M.tag["ear_l"]) | set(M.tag["ear_r"])
    sel = {fi for fi in M.tag["base_head_faces"] if len(M.faces[fi]) == 4 and not (set(M.faces[fi]) & ears)}
    # (sixth round, the triangle budget: only the face and the sides forward of the ears are split; the skull's back
    # and crown keep the cage's loops, which hold its round outline once smoothed)
    yc = float(np.mean([P[v][1] for v in M.tag["base_head_pts"]]))
    sel = {fi for fi in sel if P[M.faces[fi]].mean(0)[1] < yc - HEAD_SPLIT_BACK}
    if HEAD_ROUTE == "fresh":
        sel = set()     # (the fresh head is subdivided whole already: base_head)
    if HEAD_ROUTE == "r7":
        # (round seven's own split faces, by their cage corners)
        loc = {v: k for k, v in enumerate(M.tag["base_head_pts"][:M.tag["n_cage"]])}
        want = {tuple(s) for s in r7_load()["sel"]}
        sel = {fi for fi in M.tag["base_head_faces"]
               if all(v in loc for v in M.faces[fi]) and tuple(sorted(loc[v] for v in M.faces[fi])) in want}
        print("%s R7 split: %d of round seven's %d faces found" % (WHO, len(sel), len(want)))
    n_old = len(M.P)
    R, uv1, W1, ch = refine(M, sel, face_uv, weights)
    R.base_uv = {}
    R.tag = dict(M.tag)
    R.tag["base_head_faces"] = [c for fi in M.tag["base_head_faces"] for c in ch.get(fi, [])]
    for key in ("hand_faces_l", "hand_faces_r", "wrist_faces_l", "wrist_faces_r"):
        R.tag[key] = [c for fi in M.tag[key] for c in ch.get(fi, [])]
    R.tag["base_head_pts"] = list(M.tag["base_head_pts"]) + [i for i in range(n_old, len(R.P)) if R.part[i] == "head"]
    under2 = set()
    for fi in under:
        under2 |= set(ch.get(fi, []))
    if HEAD_ROUTE == "r7":
        r7_place(R)
        adjust_r7(R)
        return R, uv1, W1, under2
    mir = head_mirror(R)
    N0 = {fi: face_normal(R.P, R.faces[fi]) for fi in R.tag["base_head_faces"]}
    neck = [v for ring in R.tag["neck_rings"] for v in ring]
    for rnd in range(4):
        # (the neck too, and the opening's loop: the head sheet's nape and throat)
        base_head_round(R, sh, HEAD_FIT_VIEWS, step=0.8 if rnd < 2 else 0.5, reach=70,
                        more=neck, hold_loop=False)
        symmetrize(R, mir)
    head_smooth(R, 1, lam=0.3, mu=-0.32)
    symmetrize(R, mir)
    if MOUTH_WIDEN != 1.0:
        fresh_mouth_widen(R)
        symmetrize(R, mir)
    base_face_forms(R)
    symmetrize(R, mir)
    if FACE_EASE:
        fresh_face_ease(R)
        symmetrize(R, mir)
    # (where the neck's bridge meets the jaw's underside the two met at an angle, a crease from the ear to the chin:
    # the points of the opening's loop, the neck's rings and the head within 2 cm of the loop smoothed together)
    Pn = np.array(R.P)
    loop = R.tag["neck_loop"]
    near = np.zeros(len(Pn), bool)
    hp = np.array(R.tag["base_head_pts"])
    dl = np.min(np.linalg.norm(Pn[hp][:, None, :] - Pn[loop][None, :, :], axis=2), axis=1)
    near[hp[dl < 0.02]] = True
    near[neck] = True
    # (and the jaw's sides below the mouth's corners, where the base's jaw loop was drawn into a crease from the lobe
    # to the chin)
    rows_h = head_row(Pn[hp, 2])
    near[hp[(rows_h > SMILE[0] - SMILE[1] + 1) & (np.abs(Pn[hp, 0]) > 0.035)]] = True
    E = edges_of(R.faces)
    deg = np.bincount(E.ravel(), minlength=len(Pn)).astype(float)
    for _ in range(4):
        for f in (0.5, -0.53):
            acc = np.zeros_like(Pn)
            np.add.at(acc, E[:, 0], Pn[E[:, 1]])
            np.add.at(acc, E[:, 1], Pn[E[:, 0]])
            avg = acc / np.maximum(deg, 1)[:, None]
            Pn[near] += (avg[near] - Pn[near]) * f
    R.P = [p for p in Pn]
    symmetrize(R, mir)
    firm_jaw(R)
    symmetrize(R, mir)
    if JAW_LINE:
        fresh_jaw_line(R)
        symmetrize(R, mir)
    shape_ears(R)
    symmetrize(R, mir)
    if JAW_WIDEN or CHIN_BROAD:
        square_jaw(R)
        symmetrize(R, mir)
    if HEAD_WIDEN or NECK_EASE:
        youth_head(R)
        symmetrize(R, mir)
    freeze_or_load_head(R)
    adjust_head(R)
    print("BROTHER refined: face %d faces split; %d triangles now; folded after the refit %d" % (len(sel), len(R.tris()), folded_faces(R, R.tag["base_head_faces"], N0)))
    return R, uv1, W1, under2


# ------------------------------------------------------------------------------------------------------------------
# Open eyes (polish pass, 2026-11-18). The base head's cage has one quad where each eye is, so the eyes were closed
# almond slits painted on a shallow dent. Now: the face is split once more round each eye, an almond opening cut to
# the bald front view's lids, the lids given a thickness that rolls into the socket, the skin round the opening kept
# outside a ball, a crease over the upper lid; and an eyeball of its own (brother_eyes, its own small picture: sclera,
# iris, pupil) set in, on the head bone. The usual way game figures have eyes (Twilight Princess's included).
# ------------------------------------------------------------------------------------------------------------------

# The bald front view's left eye (his left, the viewer's right), measured off the sheet: (columns out from the middle,
# rows). The inner and outer corners, the upper lid's peak, the lower lid's lowest point, the iris's middle and radius.
EYE_INNER = (35.0, 1033.0)
EYE_OUTER = (89.0, 1034.0)
EYE_TOP = (58.0, 1021.0)
EYE_LOW = (55.0, 1042.0)
EYE_IRIS = (60.0, 1031.0, 9.5)
EYE_ZONE = (36.0, 20.0)           # open_eyes: the half width and height (px) round the iris where the face is split again
EYE_R = 0.0125 * K_HEAD               # the eyeball's depth and height radius (metres)
EYE_RX = 0.0205 * K_HEAD              # its half width: an ellipsoid, wide enough to fill the almond's corners (the sheet's eye is 3.5 cm long)
EYE_RAD = np.array((EYE_RX, EYE_R, EYE_R))
EYE_BACK = 0.0015            # the ball's front this far behind where the closed lids were
LID_THICK = 0.0013           # the lids' margins stand this far in front of the ball
LID_EVEN = 6                 # open_eyes 5b: Taubin rounds over the two skin rings round each margin (0: none)
EYE_SPLIT = "--no-eye-split" not in ARGS           # open_eyes 1: the faces round each eye split once more first
LID_CREASE = 0.0014          # open_eyes 5: metres the crease over the upper lid is sunk
LID_RINGS = 2                # open_eyes 5b: how many rings of skin round each margin are evened
LID_TUCK = (0.0012, 0.0008)  # open_eyes 6: the lids' inner edge this far in from the margin and this far behind the ball's front (m)


def ball_y(x, z, C):
    """The eyeball's front surface (its y) at (x, z)."""
    k = 1.0 - ((x - C[0]) / EYE_RAD[0]) ** 2 - ((z - C[2]) / EYE_RAD[2]) ** 2
    return C[1] - EYE_RAD[1] * math.sqrt(max(k, 0.0))


def eye_outline(n=48):
    """The almond as (column out, row) points round it, from the inner corner over the top and back under."""
    (c0, r0), (c1, r1) = EYE_INNER, EYE_OUTER
    # (the user, 2026-11-18: "a bit down turned eyes ... soft gentle kind eyes": the outer corner lowered by the
    # figure's "eye_down" (head sheet pixels, about 0.65 mm each); the upper lid's outer half comes down with it)
    r1 = r1 + FIGURE.get("eye_down", 0.0)
    tu = (EYE_TOP[0] - c0) / (c1 - c0)
    tl = (EYE_LOW[0] - c0) / (c1 - c0)
    out = []
    for i in range(n):
        s = i / n * 2.0
        upper = s < 1.0
        t = s if upper else 2.0 - s
        rc = r0 + (r1 - r0) * t
        if upper:
            # (peak at tu: the curve's parameter skewed so its top lies there)
            tt = t ** (math.log(0.5) / math.log(tu))
            # (ninth round, the critic: "staring ... white showing round the iris"; the brief: the upper lid over the top
            # quarter of the iris: the lid's peak lowered by the figure's "lid_drop" (head sheet pixels))
            row = rc - (rc - EYE_TOP[1] - FIGURE.get("lid_drop", 0.0)) * (math.sin(math.pi * tt) ** 0.85)
        else:
            tt = t ** (math.log(0.5) / math.log(tl))
            row = rc + (EYE_LOW[1] - rc) * (math.sin(math.pi * tt) ** 0.9)
        out.append((c0 + (c1 - c0) * t, row))
    return np.array(out)


def inside_poly(pts, poly):
    x, y = pts[:, 0], pts[:, 1]
    ins = np.zeros(len(pts), bool)
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        cross = ((yi > y) != (yj > y)) & (x < (xj - xi) * (y - yi) / ((yj - yi) + 1e-12) + xi)
        ins ^= cross
        j = i
    return ins


PEC_PROUD = 0.010   # refine_forms: metres the pecs stand proud (the brother's "consts" set 0.02, tenth round)


def refine_forms(M, face_uv, weights, under, joints):
    """Fifth round (the critic: no deltoid caps or collarbones, flat pecs with a hard crease under them, a banded
    cylinder of a back with no spine groove, shoulder blades or lats). The torso's 16 columns cannot hold those forms,
    so its faces that are seen (not under the shorts) and the arms' tops are split once (refine), and the forms are
    laid on as smooth fields along the surface's normals: two pec masses with a soft fold under each and the
    breastbone's dip between, small nipples, the collarbones with the hollow under them, the deltoids' caps, the spine's
    groove, the shoulder blades and the lats. No abs: he is stocky and padded. Gives (M, face_uv, weights, under)."""
    fams = [part_family(p) for p in M.fpart]
    P0 = np.array(M.P)
    sh_l = np.array(joints["shoulder_l"], float)
    sel = set()
    for fi, f in enumerate(M.faces):
        if fi in under:
            continue
        c = P0[f].mean(0)
        # (sixth round, the triangle budget: the chest, upper back and shoulders only, from the pecs' lower edge up;
        # the belly, flanks and lower back keep the rings, which hold their round forms once smoothed along the body)
        if fams[fi] in ("torso", "shoulder") and c[2] > body_z(FORMS_SPLIT_ROW):
            sel.add(fi)
        elif fams[fi] == "arm" and min(np.linalg.norm(c - np.array(mirror_x(sh_l, s))) for s in (1, -1)) < 0.12:
            sel.add(fi)
    R, face_uv, weights, ch = refine(M, sel, face_uv, weights)
    under = remap_tags(R, M, ch, under)
    R.base_uv = getattr(M, "base_uv", {})
    M = R
    P = np.array(M.P)
    N = normals_of(P, M.tris())
    fam_p = np.array([part_family(p) for p in M.part])
    on = np.isin(fam_p, ("torso", "shoulder", "arm"))
    on[M.tag["torso_rings"][-1]] = False
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    ax_ = np.abs(x)
    front = np.clip((-N[:, 1] - 0.15) / 0.35, 0, 1)
    back = np.clip((N[:, 1] - 0.15) / 0.35, 0, 1)
    Z = lambda r: float(body_z(r))
    g = lambda d, s: np.exp(-(d / s) ** 2)
    d = np.zeros(len(P))
    # the pecs: two masses, fullest over the nipples' row, their lower edges a soft fold, the breastbone between
    # (tenth round, the critic: "the chest is a flat slab with no pectoral mass"; tpose8 draws heavy soft pecs: 2 cm
    # proud, fuller toward their lower edge, which falls off faster than the top rises)
    zp = z - Z(480)
    d += PEC_PROUD * g(ax_ - 0.1, 0.06) * np.where(zp < 0, g(zp, 0.03), g(zp, 0.055)) * front
    # (sixth round: the fold under the pecs is gone, the critic read it as a hard shelf across the whole torso; the
    # pecs' lower edge is their own mass fading)
    zf = Z(522) + 0.018 * ((ax_ - 0.1) / 0.08) ** 2
    d -= 0.0 * g(z - zf, 0.009) * (ax_ > 0.03) * (ax_ < 0.19) * front
    d -= 0.006 * g(ax_, 0.017) * (z < Z(395)) * (z > Z(540)) * front
    d += 0.003 * g(np.hypot(ax_ - 0.12, z - Z(500)), 0.008) * front
    # the collarbones from the breastbone's notch out to the shoulder, the hollow under each
    a, b = np.array((0.025, Z(352))), np.array((0.165, Z(364)))
    q = np.stack([ax_, z], 1)
    t = np.clip(((q - a) @ (b - a)) / float((b - a) @ (b - a)), 0, 1)
    dist = np.linalg.norm(q - (a + t[:, None] * (b - a)), axis=1)
    d += 0.005 * g(dist, 0.009) * front
    q2 = q + np.array((0.0, 0.024))
    t2 = np.clip(((q2 - a) @ (b - a)) / float((b - a) @ (b - a)), 0, 1)
    d -= 0.003 * g(np.linalg.norm(q2 - (a + t2[:, None] * (b - a)), axis=1), 0.012) * front
    # the deltoids' caps over the shoulder's outer top, a little forward
    for s in (1, -1):
        J = np.array(mirror_x(joints["shoulder_l"], s), float)
        c = J + np.array((s * 0.035, -0.008, -0.01))
        d += 0.012 * g(np.linalg.norm(P - c, axis=1), 0.06)
    # the back: the spine's groove, the shoulder blades, the lats' flare below the armpits
    # (the groove made by raising the long muscles either side of the spine, not by cutting the middle in: the middle
    # line is the side view's outline, which the sheet sets)
    d += 0.007 * g(ax_ - 0.035, 0.018) * (z < Z(385)) * (z > Z(720)) * back
    d += 0.004 * g(ax_ - 0.085, 0.045) * g(z - Z(452), 0.05) * back    # (tenth round: 0.007 -> 0.004, "a hump behind each shoulder")
    d -= 0.003 * g(ax_ - 0.05, 0.012) * g(z - Z(470), 0.06) * back
    # the trapezius (sixth round; the critic: "the neck a straight column ... no trapezius slopes"; the sheet's front
    # view is 0.33 m wide at row 330, between the 0.2 m neck and the shoulders): the top of each shoulder raised into
    # a slope from the neck out to the shoulder's top
    upw = np.clip((N[:, 2] - 0.2) / 0.5, 0, 1)
    d += TRAPS * g(ax_ - 0.13, 0.055) * g(z - Z(352), 0.03) * upw
    side = np.clip((np.abs(N[:, 0]) - 0.4) / 0.4, 0, 1)
    d += 0.005 * g(z - Z(560), 0.05) * side * (fam_p == "torso")
    P += N * (d * on)[:, None]
    M.P = [p for p in P]
    print("%s FORMS: %d faces split, %d triangles now; most moved %.1f mm" % (WHO, len(sel), len(M.tris()), 1000 * float(np.abs(d * on).max())))
    return M, face_uv, weights, under


def remap_tags(R, M, ch, under):
    R.tag = dict(M.tag)
    for key in ("base_head_faces", "hand_faces_l", "hand_faces_r", "wrist_faces_l", "wrist_faces_r", "foot_faces_l", "foot_faces_r"):
        if key in M.tag:
            R.tag[key] = [c for fi in M.tag[key] for c in ch.get(fi, [])]
    u2 = set()
    for fi in under:
        u2 |= set(ch.get(fi, []))
    return u2


def open_eyes(M, face_uv, weights, under):
    """Gives (M, face_uv, weights, under, cut faces, eyes: [(centre, side)])."""
    poly = eye_outline()
    ic, ir, irad = EYE_IRIS
    # 1. the faces round each eye split once more (the sides alike)
    P = np.array(M.P)
    hp = set(M.tag["base_head_pts"])
    sel = set()
    for fi in M.tag["base_head_faces"]:
        f = M.faces[fi]
        c = P[f].mean(0)
        col, row = abs(c[0]) / HEAD_SX, float(head_row(c[2]))
        if EYE_SPLIT and c[1] < 0 and ((col - EYE_IRIS[0] - 2.0) / EYE_ZONE[0]) ** 2 + ((row - EYE_IRIS[1]) / EYE_ZONE[1]) ** 2 < 1.0:
            sel.add(fi)
    n_old = len(M.P)
    R, face_uv, weights, ch = refine(M, sel, face_uv, weights)
    under = remap_tags(R, M, ch, under)
    R.base_uv = {}
    R.tag["base_head_pts"] = list(M.tag["base_head_pts"]) + [i for i in range(n_old, len(R.P)) if R.part[i] == "head"]
    M = R
    P = np.array(M.P)
    tris = M.tris()
    N = normals_of(P, tris)
    cut = set()
    eyes = []
    for s in (1, -1):
        # where the closed lids were, at the iris's middle
        # (the ball centred on the almond, which lies 2 px outside the iris's middle)
        cx, cz = s * float(poly[:, 0].mean()) * HEAD_SX, float(head_z(ir))
        near = [i for i in M.tag["base_head_pts"] if s * P[i][0] > 0 and P[i][1] < 0]
        d2 = (P[near, 0] - cx) ** 2 + (P[near, 2] - cz) ** 2
        k = np.argsort(d2)[:4]
        y_s = float(P[np.array(near)[k], 1].mean())
        C = np.array((cx, y_s + EYE_BACK + EYE_R, cz))
        # 2. the opening: faces whose middle lies inside the almond, facing forward
        mine = []
        for fi in M.tag["base_head_faces"]:
            f = M.faces[fi]
            c = P[f].mean(0)
            if s * c[0] <= 0 or c[1] > C[1]:
                continue
            mine.append(fi)
        # (a face is cut when all its corners lie inside the almond grown a little; then any corner where the cut's
        # edge would pinch (a point met by the cut at two places) has its faces cut too, so the edge is one clean loop)
        mc0 = poly.mean(0)
        big = mc0 + (poly - mc0) * np.array((1.12, 1.25))
        pts_in = {}
        for fi in mine:
            for v in M.faces[fi]:
                if v not in pts_in:
                    pts_in[v] = bool(inside_poly(np.array([[s * P[v][0] / HEAD_SX, float(head_row(P[v][2]))]]), big)[0])
        hole = {fi for fi in mine if all(pts_in[v] for v in M.faces[fi])}
        for _ in range(6):
            cnt = {}
            for fi in hole:
                f = M.faces[fi]
                for i in range(len(f)):
                    e = (min(f[i], f[(i + 1) % len(f)]), max(f[i], f[(i + 1) % len(f)]))
                    cnt[e] = cnt.get(e, 0) + 1
            bnd = [e for e, c in cnt.items() if c == 1]
            deg = {}
            for a, b in bnd:
                deg[a] = deg.get(a, 0) + 1
                deg[b] = deg.get(b, 0) + 1
            pinch = {v for v, d in deg.items() if d > 2}
            if not pinch:
                break
            hole |= {fi for fi in mine if set(M.faces[fi]) & pinch}
        cut |= hole
        # the loop: the cut's edge walked in order
        nxt = {}
        for a, b in bnd:
            nxt.setdefault(a, []).append(b)
            nxt.setdefault(b, []).append(a)
        start = bnd[0][0]
        loop, prev_v, cur = [start], None, start
        while True:
            nb_ = [w for w in nxt[cur] if w != prev_v]
            if not nb_ or nb_[0] == start:
                break
            prev_v, cur = cur, nb_[0]
            loop.append(cur)
            if len(loop) > len(bnd) + 2:
                break
        # 3. the margin onto the almond (each point to the curve's point at its own angle round the eye's middle)
        mc = poly.mean(0)
        ang_p = np.arctan2(poly[:, 1] - mc[1], poly[:, 0] - mc[0])
        order = np.argsort(ang_p)
        for v in loop:
            col, row = s * P[v][0] / HEAD_SX, float(head_row(P[v][2]))
            a = math.atan2(row - mc[1], col - mc[0])
            j = int(np.argmin(np.abs(np.angle(np.exp(1j * (ang_p - a))))))
            c2, r2 = poly[j]
            x, z = s * c2 * HEAD_SX, float(head_z(r2))
            y = ball_y(x, z, C) - LID_THICK
            P[v] = (x, y, z)
        # 4. the points inside the opening tucked into the ball (they are not drawn); the skin round it kept outside
        # the ball, the lids wrapping it
        inner = set(v for fi in hole for v in M.faces[fi]) - set(loop)
        for v in inner:
            dvec = P[v] - C
            dn = dvec / EYE_RAD
            P[v] = C + dn / max(np.linalg.norm(dn), 1e-9) * EYE_RAD * (1.0 - 0.002 / EYE_R)
        lp = set(loop)
        for i in M.tag["base_head_pts"]:
            if i in lp or i in inner or s * P[i][0] <= 0:
                continue
            dvec = P[i] - C
            dn = dvec / EYE_RAD
            dd = np.linalg.norm(dn)
            if dd < 1.0 + LID_THICK / EYE_R:
                P[i] = C + dn / dd * EYE_RAD * (1.0 + LID_THICK / EYE_R)
        # 5. the crease over the upper lid, and the lid between full; a soft bag under the lower lid
        for i in M.tag["base_head_pts"]:
            if i in lp or i in inner or s * P[i][0] <= 0 or P[i][1] > C[1]:
                continue
            col, row = s * P[i][0] / HEAD_SX, float(head_row(P[i][2]))
            t = (col - EYE_INNER[0]) / (EYE_OUTER[0] - EYE_INNER[0])
            if t < -0.15 or t > 1.15:
                continue
            j = int(np.clip(round(np.clip(t, 0, 1) * 24), 0, 24))
            top = poly[j][1]
            low = poly[(48 - j) % 48][1]
            fade = float(np.clip(1.0 - (abs(t - 0.5) - 0.5) / 0.15, 0, 1)) if (t < 0 or t > 1) else 1.0
            above = top - row
            below = row - low
            n_ = np.array((0.0, -1.0, 0.0))
            push = 0.0
            if 0 < above < 12:
                push += 0.0006 * math.exp(-((above - 3.0) / 2.5) ** 2)       # the lid's own fullness
                push -= LID_CREASE * math.exp(-((above - 8.0) / 2.2) ** 2)       # the crease
            if 0 < below < 14:
                push += 0.0006 * math.exp(-((below - 7.0) / 3.0) ** 2)       # the soft bag
            bags = FIGURE.get("bags", 0.0)
            if bags and 0 < below < 26:
                # (the user: "more prominent world weary bags": a soft pouch under the lower lid, most toward the
                # outer half, and a crease under it)
                outer = 0.6 + 0.4 * float(np.clip(t, 0, 1))
                push += bags * outer * math.exp(-((below - 9.0) / 4.0) ** 2)
                push -= bags * FIGURE.get("bag_crease", 0.7) * outer * math.exp(-((below - 16.5) / 2.2) ** 2)
            P[i] = P[i] + n_ * push * fade
        # 5b. (seventh round, the critic: "the eye sockets are holes ringed by jagged, spiky lid geometry") the two rings
        # of skin round the margin evened out (Taubin), the margin held, then kept outside the ball again
        if LID_EVEN:
            kept = [fi for fi in range(len(M.faces)) if fi not in hole]
            Ek = edges_of([M.faces[fi] for fi in kept])
            ring_pts = set(loop)
            for _ in range(LID_RINGS):
                grow = set(ring_pts)
                for a_, b_ in Ek:
                    if a_ in ring_pts:
                        grow.add(int(b_))
                    if b_ in ring_pts:
                        grow.add(int(a_))
                ring_pts = grow
            sm = np.zeros(len(P), bool)
            sm[list(ring_pts - lp - inner)] = True
            sm &= np.array([s * p[0] > 0 for p in P])
            degk = np.bincount(Ek.ravel(), minlength=len(P)).astype(float)
            for _ in range(LID_EVEN):
                for f_ in (0.5, -0.53):
                    acc = np.zeros_like(P)
                    np.add.at(acc, Ek[:, 0], P[Ek[:, 1]])
                    np.add.at(acc, Ek[:, 1], P[Ek[:, 0]])
                    avg = acc / np.maximum(degk, 1)[:, None]
                    P[sm] += (avg[sm] - P[sm]) * f_
            for i in np.where(sm)[0]:
                dn = (P[i] - C) / EYE_RAD
                dd = np.linalg.norm(dn)
                if dd < 1.0 + LID_THICK / EYE_R:
                    P[i] = C + dn / dd * EYE_RAD * (1.0 + LID_THICK / EYE_R)
            # (the margin itself evened along its own line: each point a little toward its neighbours' middle, then
            # back onto the ball's front)
            Lq = P[loop].copy()
            for _ in range(2):
                Lq = Lq * 0.5 + (np.roll(Lq, 1, 0) + np.roll(Lq, -1, 0)) * 0.25
            for k_, v in enumerate(loop):
                x, z = Lq[k_, 0], Lq[k_, 2]
                P[v] = (x, ball_y(x, z, C) - LID_THICK, z)
        # 6. the lids' thickness: a strip from the margin into the ball, 1.2 mm in
        Lp = P[loop]
        mid = np.array((C[0], C[2]))
        ring2 = []
        for v in loop:
            xz = P[v][[0, 2]]
            dvec = mid - xz
            xz2 = xz + dvec / max(np.linalg.norm(dvec), 1e-9) * LID_TUCK[0]
            y2 = ball_y(xz2[0], xz2[1], C) + LID_TUCK[1]
            P = np.vstack([P, (xz2[0], y2, xz2[1])])
            M.P.append(P[-1].copy())
            M.part.append("head")
            weights.append(dict(weights[v]))
            ring2.append(len(M.P) - 1)
        M.P = [p for p in P]
        # (each margin point's place in the face picture, from a kept face that has it)
        uv_of = {}
        for fi, f in enumerate(M.faces):
            if fi in cut or fi not in face_uv or face_uv[fi][0] != "face":
                continue
            for v, q_ in zip(f, face_uv[fi][1]):
                if v in lp and v not in uv_of:
                    uv_of[v] = q_
        n = len(loop)
        for j in range(n):
            a, b = loop[j], loop[(j + 1) % n]
            f = [a, b, ring2[(j + 1) % n], ring2[j]]
            nrm_ = face_normal(P, f)
            cen = P[f].mean(0)
            if np.dot(nrm_, cen - C) < 0:
                f = f[::-1]
            M.face(f, "head")
            fi = len(M.faces) - 1
            face_uv[fi] = ("face", [uv_of.get(v if v in uv_of else loop[ring2.index(v)], (0.0, 0.0)) for v in f])
        eyes.append((C, s))
        print("BROTHER EYES %s: opening of %d faces, margin %d points, ball at %s" % ("left" if s > 0 else "right", len(hole), n, np.round(C, 4)))
    return M, face_uv, weights, under, cut, eyes


def eye_texture(path, size=256):
    """The eyeball's picture, planar from its front: sclera, the iris (the sheet's blue-grey, darker at its rim, lighter
    rays inside), the pupil. The iris's radius on the picture is its angle on the ball."""
    k = (np.arange(size) + 0.5) / size * 2.0 - 1.0
    X, Y = np.meshgrid(k, k)
    r = np.hypot(X * EYE_RX / EYE_R, Y)    # (the ball is wider than tall: the iris round on it, an ellipse here)
    ri = EYE_IRIS[2] * HEAD_SX / EYE_R * FIGURE.get("iris_k", 1.0)   # the iris's radius over the ball's height radius
    rp = ri * 0.36
    img = np.zeros((size, size, 3))
    sclera = np.array((0.93, 0.9, 0.86))
    img[:] = sclera * (1.0 - 0.18 * np.clip((r - 0.75) / 0.25, 0, 1))[..., None]
    img[:] = img * (1.0 - 0.05 * np.clip((r - ri) / 0.4, 0, 1))[..., None] + np.array((0.03, -0.01, -0.02)) * np.clip((r - 0.7) / 0.3, 0, 1)[..., None]
    t = np.clip(r / ri, 0, 1)
    ang = np.arctan2(Y, X)
    rays = 0.04 * np.sin(ang * 23.0) + 0.03 * np.sin(ang * 37.0 + 1.3)
    if FIGURE.get("iris") == "hazel":
        # (the user, 2026-11-18, of the brother's eyes: "amber brown green": hazel, an amber-brown ring round the
        # pupil shading to a soft green toward the rim, a darker limbal edge; the highlight below)
        # (ninth round, the critic: "bright green with an orange ring"; the brief: amber-brown at the pupil to green at
        # the rim, about 15% darker: the amber now holds to 0.6 of the radius, an olive green only in the outer band)
        # (tenth round, the brief: "reading hazel-green overall, not orange": the amber a ring round the pupil only,
        # out to 0.42 of the radius, browner; green from there out)
        amber, green = np.array((0.45, 0.32, 0.15)), np.array((0.4, 0.4, 0.22))
        g = np.clip((t - 0.4) / 0.3, 0, 1)[..., None] ** 1.1
        iris = amber * (1 - g) + green * g
        iris = iris * (1.0 - 0.18 * np.clip((0.5 - t) / 0.5, 0, 1))[..., None]
        iris = iris * (1.0 + rays[..., None] * (t[..., None] > 0.3))
        ring = np.clip((t - 0.84) / 0.16, 0, 1)[..., None]
        iris = iris * (1 - ring) + np.array((0.17, 0.15, 0.1)) * ring
    else:
        iris_in = np.array((0.58, 0.64, 0.70))
        iris_out = np.array((0.34, 0.39, 0.47))
        iris = iris_in[None, None, :] * (1 - t[..., None] ** 1.6) + iris_out * (t[..., None] ** 1.6)
        iris = iris * (1.0 + rays[..., None] * (t[..., None] > 0.4))
        ring = np.clip((t - 0.86) / 0.14, 0, 1)[..., None]
        iris = iris * (1 - ring) + np.array((0.2, 0.22, 0.27)) * ring
    inn = (r < ri)[..., None]
    soft = np.clip((ri - r) / 0.02, 0, 1)[..., None]
    img = img * (1 - soft * inn) + iris * soft * inn
    pup = np.clip((rp - r) / 0.02, 0, 1)[..., None]
    img = img * (1 - pup) + np.array((0.05, 0.05, 0.07)) * pup
    if FIGURE.get("iris") == "hazel":
        # a small highlight, up and to one side of the pupil
        hl = np.clip(1.0 - np.hypot(X * EYE_RX / EYE_R + ri * 0.35, Y + ri * 0.35) / (ri * 0.16), 0, 1)[..., None]
        img = img * (1 - hl * 0.85) + np.array((0.97, 0.96, 0.92)) * hl * 0.85
    save_rgb(path, img[::-1])


def eye_balls(eyes):
    """Two balls' front caps (12 round, 6 rows out to 100 degrees from the pole: the rest is always behind the lids;
    the whole ball was 768 triangles for the pair), their poles straight ahead; UVs planar from the front."""
    P, F, UV = [], [], []
    nu, nv = 12, 6
    for C, s in eyes:
        base = len(P)
        for i in range(nv + 1):
            th = math.radians(100.0) * i / nv
            for j in range(nu):
                ph = math.tau * j / nu
                d = np.array((math.sin(th) * math.cos(ph), -math.cos(th), math.sin(th) * math.sin(ph)))
                P.append(C + d * EYE_RAD)
        for i in range(nv):
            for j in range(nu):
                jj = (j + 1) % nu
                a, b, c, d = base + i * nu + j, base + i * nu + jj, base + (i + 1) * nu + jj, base + (i + 1) * nu + j
                F.append([a, c, d] if i == 0 else [a, b, c, d])
    P = np.array(P)
    for f in F:
        uv = []
        for v in f:
            d = (P[v] - np.array(min(eyes, key=lambda e: np.linalg.norm(P[v] - e[0]))[0])) / EYE_RAD
            k_ = 1.0 if d[1] < 0 else 1.0
            uv.append((0.5 + 0.5 * d[0] * k_, 0.5 + 0.5 * d[2] * k_))
        UV.append(uv)
    # (each face turned outward)
    out = []
    for f, uv in zip(F, UV):
        cen = P[f].mean(0)
        C = min(eyes, key=lambda e: np.linalg.norm(cen - e[0]))[0]
        if np.dot(face_normal(P, f), cen - C) < 0:
            f, uv = f[::-1], uv[::-1]
        out.append((f, uv))
    return P, out


def refine_head(M, face_uv, weights, under):
    """The head (skin, not the cap) split once, the face's front (brow to mouth) twice."""
    fam = [part_family(p) for p in M.fpart]
    # (not the bare skull above the band: smooth enough at 16 round, and under the cap)
    Pm = np.array(M.P)
    # (second build: the rings are close enough that only the face is split, once; the first build split the whole
    # head first and spent 5,000 triangles on it)
    head = set()
    M1, uv1, W1, ch1 = refine(M, head, face_uv, weights)
    P = np.array(M1.P)
    fam1 = [part_family(p) for p in M1.fpart]
    face = set()
    for fi, f in enumerate(M1.faces):
        if fam1[fi] != "head" or len(f) != 4:
            continue
        c = P[f].mean(0)
        r = float(head_row(c[2]))
        if 972 <= r <= 1238 and c[1] < head_centre(M1, c[2])[1] - 0.02 and abs(c[0]) < 0.09:
            face.add(fi)
    M2, uv2, W2, ch2 = refine(M1, face, uv1, W1)
    under2 = set()
    for fi in under:
        for c1 in ch1.get(fi, []):
            under2 |= set(ch2.get(c1, []))
    print("BROTHER refined: head %d faces split, face %d split again; %d triangles now" % (len(head), len(face), len(M2.tris())))
    return M2, uv2, W2, under2



# ------------------------------------------------------------------------------------------------------------------
# The build
# ------------------------------------------------------------------------------------------------------------------

def apply_figure():
    """The chosen figure's own tables over the module's (see FIGURES)."""
    global TATTOOS, SIDE_HAND, SIDE_HAND_SKIN
    for d in (TEX, os.path.dirname(GLB), os.path.dirname(BLEND)):
        os.makedirs(d, exist_ok=True)
    if FIGURE["tattoos"] is not None:
        w = FIGURE["warp"]
        tt = []
        for name, view, (c0, c1), (r0, r1) in FIGURE["tattoos"]:
            if w:
                a0, b0 = warp_point(w, view, c0, r0)
                a1, b1 = warp_point(w, view, c1, r1)
                c0, c1, r0, r1 = int(round(a0)), int(round(a1)), int(round(b0)), int(round(b1))
            tt.append((name, view, (c0, c1), (r0, r1)))
        TATTOOS = tuple(tt)
    if FIGURE["side_hand"]:
        SIDE_HAND = FIGURE["side_hand"]
    (c0, r0), (c1, r1) = SIDE_HAND
    SIDE_HAND_SKIN = FIGURE.get("side_hand_skin", ((c0, r0), (c1, r1 + 50)))
    if FIGURE.get("head"):
        globals().update(FIGURE["head"]["marks"])
    globals().update(FIGURE.get("consts", {}))
    global HEAD_ROUTE, SMILE
    HEAD_ROUTE = arg("--head-route", FIGURE.get("head_route", "old"))
    if HEAD_ROUTE == "fresh":
        fc = dict(FRESH_CONSTS)
        sd = fc.pop("SMILE_DEPTH")
        globals().update(fc)
        SMILE = (SMILE[0], SMILE[1], SMILE[2], sd)
        globals().update(FIGURE.get("fresh", {}))
        globals()["EYE_RAD"] = np.array((EYE_RX, EYE_R, EYE_R))
    if HEAD_ROUTE == "r7":
        # (round seven's own eye and mouth landmarks (concept_brother_head2.jpg's frame), eye settings and iris)
        d = r7_load()
        for k, v in d["glob"].items():
            globals()[k] = tuple(tuple(x) if isinstance(x, list) else x for x in v) if isinstance(v, list) else v
        for k, v in d["fig"].items():
            if v is not None:
                FIGURE[k] = v
        globals()["EYE_RAD"] = np.array((EYE_RX, EYE_R, EYE_R))
        globals()["EYE_ZONE"] = (36.0, 20.0)
        globals()["MOUTH_SNAP_MAX"] = 0.003
        globals()["HEAD_WIDEN"] = ()
        globals()["NECK_EASE"] = 0
        r7_eye_adjust()
    print("%s HEAD route: %s" % (WHO, HEAD_ROUTE))
    # (ninth round: the head moved back on the body by HEAD_BACK metres (the critic: "the neck ... leans forward like
    # a vulture's"; laid over tpose8's side view his face stood 1.4 cm in front of the drawn face, scratchpad
    # brother9/ov_side_top.png). The head sheet's side view is resampled with its middle that much further forward, so
    # everything fitted to it lands further back; the side view's own columns read off the old resampling follow.)
    hb = FIGURE.get("consts", {}).get("HEAD_BACK", 0.0)
    if hb and FIGURE.get("head"):
        hw = FIGURE["head"]
        d = hb / HEAD_SX
        k = (HEAD_CHIN - HEAD_CROWN) / (hw["chin"] - hw["crown"])
        hw["mid"]["side"] += d / k
        g = globals()
        g["EAR_COLS"] = tuple(c - d for c in EAR_COLS)
        g["EAR_LOBE"] = (EAR_LOBE[0] - d, EAR_LOBE[1])
        g["JAW_ANGLE"] = (JAW_ANGLE[0] - d, JAW_ANGLE[1])
        g["CHIN_BOTTOM"] = (CHIN_BOTTOM[0] - d, CHIN_BOTTOM[1])
        print("%s head moved back %.1f cm: the side view's middle %+.1f px of its own sheet" % (WHO, hb * 100, d / k))
    for r in (610, 640, 665, 690):
        if r in BODY_FORMS:
            BODY_FORMS[r] = {j: tuple(v * FIGURE["belly"] for v in vals) for j, vals in BODY_FORMS[r].items()}
    print("%s FIGURE %s: sheet %s, %d tattoos, out %s" % (WHO, FIGURE_NAME, FIGURE["sheet"], len(TATTOOS), GLB))


HAND_DESPIKE = 0.0    # despike_hands: metres a hand point may stand off its neighbours' middle (0: off)


def despike_hands(M, rounds=3):
    """(tenth round, the critic: "a sharp triangular flap sticks out at the heel of the palm on the thumb side") Every
    hand point standing more than HAND_DESPIKE off the middle of its neighbours (a flap or a shard: smooth skin there
    stands a millimetre or two off) is drawn onto that middle, round by round."""
    P = np.array(M.P)
    fams = np.array([part_family(p) for p in M.part])
    # (the palm and the back of the hand only: fingers and the thumb are thin, their points stand well off by nature)
    on = np.isin(np.array(M.part), ("hand_l", "hand_r"))
    E = edges_of(M.faces)
    deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
    total = 0
    for _ in range(rounds):
        acc = np.zeros_like(P)
        np.add.at(acc, E[:, 0], P[E[:, 1]])
        np.add.at(acc, E[:, 1], P[E[:, 0]])
        avg = acc / np.maximum(deg, 1)[:, None]
        off = np.linalg.norm(P - avg, axis=1)
        bad = on & (off > HAND_DESPIKE)
        if not bad.any():
            break
        total += int(bad.sum())
        P[bad] = avg[bad] * 0.8 + P[bad] * 0.2
    M.P = [p for p in P]
    print("%s HAND despiked: %d moves of points more than %.1f mm off their neighbours" % (WHO, total, HAND_DESPIKE * 1000))


def main():
    # (an empty scene: the factory start-up's cube, camera and light removed)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    apply_figure()
    sh = Sheets()
    base_hand_fit(sh)
    M, T, joints = build_body(sh)
    base_head(M, sh, T[-1])
    seen_f = {}
    for i, f in enumerate(M.faces):
        seen_f.setdefault(tuple(sorted(f)), []).append(i)
    twice = [v for v in seen_f.values() if len(v) > 1]
    dup = [i for i, f in enumerate(M.faces) if len(set(f)) != len(f)]
    print("BROTHER faces with a point twice: %d; faces made twice: %d" % (len(dup), len(twice)))
    flipped = fix_winding(M)
    print("BROTHER built: %d points, %d faces, %d triangles (%d turned outward)" % (len(M.P), len(M.faces), len(M.tris()), flipped))
    body_faces = [f for f, p in zip(M.faces, M.fpart) if part_family(p) not in ("ear",)]
    print("BROTHER open edges of the body (should be none): %d" % len(open_edges(body_faces)))
    fams = np.array([part_family(p) for p in M.part])
    frozen = np.isin(fams, ("head", "nose", "ear", "neck", "hand") + (("foot",) if BASE_FEET else ()))
    frozen[T[-1]] = True
    for sfx in ("_l", "_r"):
        for ring in M.tag["arm_rings" + sfx][-2:]:
            frozen[ring] = True
    mir = mirror_map(M.P)
    print("BROTHER mirror pairs: %d of %d points matched" % ((mir != np.arange(len(mir))).sum(), len(mir)))

    def snapshot():
        Pc, tc = with_caps(M, np.array(M.P), [])
        return [(np.array(M.P), M.tris(), M.tri_fams()), (Pc, tc, ["sidecap"] * len(tc))]

    stats = overlay(snapshot(), sh, "r0")
    print("BROTHER overlay r0", json.dumps(stats))
    for rnd in range(1, FIT_ROUNDS + 1):
        moved, most = fit_round(M, sh, frozen)
        symmetrize(M, mir)
        relax(M, frozen, 0.2, 1)
        stats = overlay(snapshot(), sh, "r%d" % rnd, report=(rnd == FIT_ROUNDS))
        print("BROTHER fit round %d: %d points on the outline moved, most %.1f cm; %s" % (rnd, moved, most * 100, json.dumps(stats)))
    smooth_armpits(M)
    smooth_body(M, 3)
    smooth_shoulders(M, joints)
    # (the smoothing drew the shoulders and the lats in from the sheet's outline: fitted again)
    for rnd in range(3):
        fit_round(M, sh, frozen)
        symmetrize(M, mir)
        relax(M, frozen, 0.2, 1)
    smooth_body(M, 1)
    sculpt_body(M)
    smooth_body(M, 1)
    round_shoulders(M, joints)
    smooth_along(M)
    taper_forearms(M, joints)
    smooth_ankles(M, joints)
    smooth_wrists(M, joints)
    if HAND_DESPIKE:
        despike_hands(M)
    back_forms(M)
    finish(M, T, joints, sh)


# Seventh round (the critic: "a broad back with clear lats, shoulder blades, a spine groove ... round glutes filling the
# shorts"; the back had gone plain once its banding was smoothed out). From the captain's build: the forms laid on
# after the smoothing as smooth fields along each point's normal, so no ring can stand out of them and no loop or
# triangle is added: (centre |x| m, body-sheet row, side (-1 front, 1 back, 0 either), spread across, spread up above
# the centre, spread below it (m), metres along the normal).
BACK_FORMS = (
    (0.10, 470.0, 1, 0.055, 0.06, 0.07, 0.005),     # the shoulder blades under the padding (tenth round: 0.010 -> 0.005, the hump)
    (0.0, 560.0, 1, 0.02, 0.17, 0.17, -0.009),      # the spine's soft groove, shoulders to waist
    (0.17, 540.0, 1, 0.05, 0.07, 0.06, 0.006),      # the lats' flare under the arms
    (0.075, 845.0, 1, 0.06, 0.06, 0.04, 0.018),     # the glutes, rounding the seat (the shorts follow the body)
)


def back_forms(M):
    P = np.array(M.P)
    N = normals_of(P, M.tris())
    fams = np.array([part_family(p) for p in M.part])
    T = M.tag["torso_rings"]
    keep = set(T[0]) | set(T[-1])
    torso = fams == "torso"
    cy = float(np.median(P[torso, 1]))
    row = body_row(P[:, 2])
    d = np.zeros(len(P))
    for cx, r, side, sx, su, sd, amt in BACK_FORMS:
        dz = row - r
        gz = np.where(dz < 0, np.exp(-(dz / (su / S)) ** 2), np.exp(-(dz / (sd / S)) ** 2))
        gx = np.exp(-((np.abs(P[:, 0]) - cx) / sx) ** 2)
        gs = np.clip(side * (P[:, 1] - cy) / 0.05, 0, 1) if side else 1.0
        d += amt * gz * gx * gs * torso
    for v in keep:
        d[v] = 0.0
    P += N * d[:, None]
    M.P = [p for p in P]
    print("%s BACK forms laid on: out %.1f mm, in %.1f mm" % (WHO, 1000 * float(d.max()), -1000 * float(d.min())))


# ------------------------------------------------------------------------------------------------------------------
# Tenth round: paint for youth (the critic: "he reads 35 to 45, not 19": "deep painted nasolabial folds plus crow's-feet
# and under-eye lines drawn as hard dark strokes", "hands and legs covered in brown vein and scratch strokes", "dark
# anatomy-chart contour lines", hair "drawn as dark scratch strokes"; the user twice: boyish). The sheets' painting
# carries their line work and shading, which projected onto him read as age and dirt. So, as the younger boy's build
# does (tools/build_boy.py, RULE_PAINT; read, not imported):
# - the FACE is painted by rule on clean skin in his own tone (FACE_BY_RULE): soft brown brows, a lash line, a soft
#   lid crease, soft bags as a light rose shade (no line), rosy cheeks, a nose flush no stronger than the cheeks,
#   the lips on the modelled mouth line, nostrils, rosy ear rims, a faint cool stubble shadow on the jaw. No folds,
#   no crow's-feet, no forehead lines. `--sheet-face` brings back the projected face.
# - the BODY keeps only the sheet's broad tone (a 3D low pass) brought to his tone, and its hair where the sheet's
#   dark strokes are DENSE (the hair's places: chest, belly line, forearms, legs), redrawn as soft clumps with a few
#   strands; thin isolated strokes (contours, veins, scratches) are dropped. The hands are plain skin with the
#   rule's knuckles, creases and nails (no projection from the hands sheet: its streaks read as veins).
# ------------------------------------------------------------------------------------------------------------------

FACE_BY_RULE = "--sheet-face" not in ARGS
YOUNG_SKIN = "--sheet-skin" not in ARGS
ROSE = np.array((1.03, 0.84, 0.81))
SOFT_SHADE = np.array((0.93, 0.83, 0.81))
HAIR_BROWN = np.array((0.30, 0.2, 0.14))


PAD = 6


def grown_by(valid, n=PAD):
    g = valid.copy()
    for _ in range(n):
        g = g | np.roll(g, 1, 0) | np.roll(g, -1, 0) | np.roll(g, 1, 1) | np.roll(g, -1, 1)
    return g


def pad_edges(rgb, valid, n=PAD):
    """(tenth round, the critic: "a dark line circles the neck"; in a close-up a thin light-and-dark line along the
    island edge: the margins were filled from a coarse average of the atlas round them, other islands included, and
    bilinear sampling drew it in) Each island's edge colour carried out n texels, ring by ring, from its own texels."""
    out = rgb.copy()
    v = valid.copy()
    for _ in range(n):
        acc = np.zeros_like(out)
        cnt = np.zeros(v.shape)
        for ax, sh_ in ((0, 1), (0, -1), (1, 1), (1, -1)):
            acc += np.roll(out * v[..., None], sh_, ax)
            cnt += np.roll(v.astype(float), sh_, ax)
        new = ~v & (cnt > 0)
        out[new] = acc[new] / cnt[new][:, None]
        v = v | new
    return out


def lowpass3d(rgb, pos, hit, cell=0.05, spread=2):
    lo_ = pos[hit].min(0) - cell * 4
    idx = np.floor((pos - lo_) / cell).astype(int)
    shape = tuple(idx[hit].max(0) + 5)
    s = np.zeros(shape + (3,))
    n = np.zeros(shape)
    ih = idx[hit]
    np.add.at(s, (ih[:, 0], ih[:, 1], ih[:, 2]), rgb[hit])
    np.add.at(n, (ih[:, 0], ih[:, 1], ih[:, 2]), 1.0)
    for _ in range(spread):
        for ax in range(3):
            s = s + np.roll(s, 1, ax) + np.roll(s, -1, ax)
            n = n + np.roll(n, 1, ax) + np.roll(n, -1, ax)
    out = rgb.copy()
    out[hit] = (s / np.maximum(n, 1e-6)[..., None])[ih[:, 0], ih[:, 1], ih[:, 2]]
    return out


def young_skin(M, face_uv, skin, spos, shit, tone):
    """The body's picture rebuilt (see above). Gives the new picture."""
    P = np.array(M.P)
    _, nrm, _, fid = texel_geometry(M, face_uv, "skin", P, normals_of(P, M.tris()))
    fam = np.array([part_family(p) for p in M.fpart] + ["none"])[fid]
    hands = shit & (fam == "hand")
    body = shit & ~hands
    low = lowpass3d(skin, spos, body, 0.06, 2)
    med = np.median(low[body], 0)
    broad = np.clip((low / np.maximum(med, 1e-3)) ** 0.35, 0.92, 1.06)
    out = np.where(body[..., None], tone * broad, skin)
    # the sheet's dark strokes: darker than a soft local mean
    soft = blur(fill_out(skin, shit, 8), 3)
    dev = (skin - soft).mean(-1)
    dark = np.clip((-dev - 0.015) / 0.06, 0, 1) * body
    # their density over about 2.5 cm of skin: hair lies in dense fields, contours and veins are thin lines
    dens = blur(dark, 6)
    clump = smooth01(0.1, 0.26, dens) * body
    # (no hair on his back, the backs of his upper arms, his face side of the neck: the sheet paints none; its
    # back's muscle shading counted as dense there)
    clump *= 1.0 - smooth01(0.2, 0.5, nrm[..., 1]) * np.isin(fam, ("torso", "shoulder"))
    clump = blur(clump, 5)
    # soft clumps: an under-layer of soft brown, broken by a slow noise so it lies in tufts, then strands over it
    rng = np.random.default_rng(5)
    noise = blur(rng.random(clump.shape), 3)
    noise = (noise - noise.mean()) / max(float(noise.std()), 1e-6)
    fan = FIGURE.get("hair_fan")
    if fan:
        # (eleventh round, the critic: the chest hair "a dark branching tree up the middle ... a stain"; limb hair
        # "smudges that read as mud". The torso's hair by rule: a fan over both pecs, a thin trail down the belly to the
        # navel, fuller again below it; the limbs keep the sheet's places. Both drawn as fine strokes that run down the
        # body (3D noise stretched along z), warm brown, over a faint under-layer)
        x_, y_, z_ = spos[..., 0], spos[..., 1], spos[..., 2]
        Zb = lambda r: float(body_z(r))
        front_t = smooth01(0.1, 0.45, -nrm[..., 1]) * np.isin(fam, ("torso",)) * body
        pecs = np.exp(-((np.abs(x_) - 0.075) / 0.075) ** 2 - ((z_ - Zb(470)) / 0.07) ** 2)
        mid_ = np.exp(-((z_ - Zb(470)) / 0.05) ** 2 - (x_ / 0.05) ** 2) * 0.8
        trail = np.exp(-(x_ / 0.016) ** 2) * smooth01(Zb(660), Zb(520), z_) * 0.75
        below = np.exp(-(x_ / 0.03) ** 2) * smooth01(Zb(640), Zb(700), z_) * 0.85
        field = np.clip(pecs + mid_ + trail + below, 0, 1) * front_t
        clump = clump * (1.0 - front_t) + field * fan
        streak = np.zeros(clump.shape)
        for i in range(5):
            d = rng.normal(size=3)
            d[2] *= 0.08     # (high frequency across, low along z: streaks that run up and down)
            d /= np.linalg.norm(d)
            streak += np.sin(spos @ (d * math.tau / 0.0035) + rng.uniform(0, math.tau))
        strands_f = smooth01(0.5, 1.9, streak) * clump * (0.6 + 0.4 * smooth01(-0.5, 1.0, noise))
        hair_c = np.array(FIGURE.get("hair_warm", (0.40, 0.27, 0.17)))
        tufts = np.clip(clump * (0.85 + 0.15 * noise), 0, 1)
        out = out * (1 - 0.2 * tufts[..., None]) + hair_c * 0.2 * tufts[..., None]
        out = out * (1 - 0.7 * strands_f[..., None]) + hair_c * 0.7 * strands_f[..., None]
        strands = strands_f
    else:
        tufts = np.clip(clump * (0.85 + 0.15 * noise), 0, 1)
        out = out * (1 - 0.2 * tufts[..., None]) + HAIR_BROWN * 0.2 * tufts[..., None]
        strands = dark * clump
        out = out * (1 - 0.3 * strands[..., None]) + HAIR_BROWN * 0.3 * strands[..., None]
    # the hands: their rule paint (creases, nails, knuckles: ratios against their flat colour) on his tone
    if hands.any():
        hb = np.median(skin[hands], 0)
        rel = np.clip(skin / np.maximum(hb, 1e-3), 0.6, 1.25)
        if FIGURE.get("plain_hands"):
            # (eleventh round: the hands the forearm's own tone, the rule paint's ratios softened to nails and
            # knuckles only: no lines across the fingers)
            arm_t = np.median(out[body & (fam == "arm")], 0)
            rel = np.clip(blur(np.where(hands[..., None], rel, 1.0), 2), 0.94, 1.04)
            out[hands] = arm_t * rel[hands]
        else:
            out[hands] = tone * rel[hands] * np.array((1.02, 0.98, 0.97))
    print("%s SKIN young: tone %s, hair clumps on %d texels, strands %d; dropped thin strokes on %d" % (
        WHO, np.round(tone, 3), int((tufts > 0.3).sum()), int((strands > 0.3).sum()),
        int(((dark > 0.3) & (clump < 0.2)).sum())))
    return np.clip(out, 0, 1)


def rule_face(M, face_uv, tone):
    """The face picture painted by rule on his own landmarks (see above). Gives (rgb, pos, hit, skin tone)."""
    P = np.array(M.P)
    pos, nrm, hit, fid = texel_geometry(M, face_uv, "face", P, normals_of(P, M.tris()))
    bad = ~(np.isfinite(pos).all(-1) & np.isfinite(nrm).all(-1))
    hit = hit & ~bad
    pos = np.nan_to_num(pos)
    nrm = np.nan_to_num(nrm)
    fam = np.array([part_family(p) for p in M.fpart] + ["none"])[fid]
    x, y, z = pos[..., 0], pos[..., 1], pos[..., 2]
    ax = np.abs(x)
    col = ax / HEAD_SX
    row = head_row(z)
    rgb = np.tile(tone, pos.shape[:-1] + (1,)).astype(float)
    rng = np.random.default_rng(11)
    v = np.zeros(pos.shape[:-1])
    for _ in range(6):
        k = rng.normal(size=3)
        k *= math.tau / 0.08 / np.linalg.norm(k)
        v += np.sin(pos @ k + rng.uniform(0, math.tau))
    rgb = rgb * (1.0 + 0.012 * v[..., None] * np.array((0.6, 1.0, 1.3)))
    face = hit & np.isin(fam, ("head", "nose")) & (y < -0.03)
    fwd = smooth01(0.05, 0.4, -nrm[..., 1])
    eyes_on = face & (fwd > 0.3) & (col < EYE_OUTER[0] * 1.4)

    def tint(w, c, a=1.0):
        nonlocal rgb
        w = np.clip(w, 0, 1)[..., None] * a
        rgb = rgb * (1.0 - w) + np.asarray(c, float) * w

    def mult(w, m):
        nonlocal rgb
        rgb = rgb * (1.0 + (np.asarray(m, float) - 1.0) * np.clip(w, 0, 1)[..., None])
    poly = eye_outline()
    up = poly[:25]
    low = poly[24:][::-1]
    lt = np.interp(col, up[:, 0], up[:, 1], left=np.nan, right=np.nan)
    lb = np.interp(col, low[:, 0], low[:, 1], left=np.nan, right=np.nan)
    inside = np.isfinite(lt)
    t = np.clip((col - EYE_INNER[0]) / (EYE_OUTER[0] - EYE_INNER[0]), 0, 1)
    d_up = np.where(inside, lt - row, 99.0)
    d_low = np.where(inside & np.isfinite(lb), row - lb, 99.0)
    span = EYE_OUTER[0] - EYE_INNER[0]
    # the stubble: a faint cool shadow over the jaw, chin and upper lip (head3's top row: light stubble), never a line
    r_m = float(SMILE[0])
    stub = (smooth01(r_m - 30.0, r_m - 18.0, row) * (1.0 - smooth01(r_m - 6.0, r_m + 4.0, row)) * (col < SMILE[2] * 0.9)
            + smooth01(r_m + 8.0, r_m + 24.0, row) * (1.0 - smooth01(float(HEAD_CHIN) + 10.0, float(HEAD_CHIN) + 30.0, row)))
    stub = np.clip(stub, 0, 1) * (1.0 - smooth01(EYE_OUTER[0] * 1.5, EYE_OUTER[0] * 1.9, col)) * face
    mult(blur(stub, 3) * 0.55, (0.94, 0.94, 0.97))
    # cheeks: rose, soft, high under the outer eye (as head3's top row)
    for s in (1.0, -1.0):
        cx = s * (EYE_IRIS[0] + 0.25 * span)
        w = np.exp(-(((x / HEAD_SX - cx) / (0.55 * span)) ** 2 + ((row - (EYE_LOW[1] + 42.0)) / 26.0) ** 2))
        mult(w * FACE_ROSE[0] * face, ROSE)
    # the nose: a flush on its tip no stronger than the cheeks
    hp = np.array(M.tag["base_head_pts"])
    nz = hp[(np.abs(P[hp, 0]) < 0.006)]
    tip = P[nz[np.argmin(P[nz, 1])]]
    w = np.exp(-(np.linalg.norm(pos - tip, axis=-1) / 0.014) ** 2)
    mult(w * FACE_ROSE[1] * face, ROSE)
    # nostrils: the underside of the nose's base, either side
    for s in (1.0, -1.0):
        c_ = tip + np.array((s * 0.0085, 0.012, -0.012))
        w = np.exp(-(np.linalg.norm((pos - c_) * np.array((1.0, 0.7, 1.4)), axis=-1) / 0.0035) ** 2)
        mult(w * smooth01(-0.1, 0.4, -nrm[..., 2]) * face, (0.62, 0.45, 0.42))
    # brows: soft brown arcs over each eye, fuller inside, a little higher than the eye's top and tapering down outward
    tb = np.clip((col - (EYE_INNER[0] - 6.0)) / (span + 16.0), 0, 1)
    brow_row = EYE_TOP[1] - BROW_ROW[0] - BROW_ROW[1] * np.sin(np.pi * np.clip(tb * 0.9 + 0.05, 0, 1)) + BROW_ROW[2] * tb ** 2
    half = BROW_PAINT[0] - (BROW_PAINT[0] - BROW_PAINT[1]) * tb
    ends = smooth01(EYE_INNER[0] - 8.0, EYE_INNER[0] - 2.0, col) * (1.0 - smooth01(EYE_OUTER[0] + 4.0, EYE_OUTER[0] + 12.0, col))
    strokes = 1.0
    tint(np.exp(-((row - brow_row) / half) ** 4) * ends * strokes * fwd * face, BROW_PAINT[3], BROW_PAINT[2])
    # the lash line, thin, thickest at the outer end, on the margin only
    lash = np.exp(-((d_up - 0.5 * LASH) / ((0.9 + 0.6 * t) * LASH)) ** 2) * (0.6 + 0.4 * t) * smooth01(-0.6, 0.2, d_up)
    tint(lash * eyes_on, (0.22, 0.14, 0.11), 0.75)
    # the lid crease, soft, and a soft heavy outer lid
    mult(np.exp(-((d_up - 9.0) / 2.6) ** 2) * (0.35 + 0.25 * t) * eyes_on, SOFT_SHADE)
    # the lower lid: a faint warm line; the bags: a soft rose shade under it (no line), toward the outer half
    mult(np.exp(-((d_low - 1.5) / 1.8) ** 2) * 0.3 * eyes_on, (0.98, 0.88, 0.86))
    mult(np.exp(-((d_low - 9.0) / 5.0) ** 2) * (0.35 + 0.25 * t) * eyes_on, (0.98, 0.88, 0.88))
    # the mouth: a soft line on the modelled lips' meeting loop, a rose lower lip, the upper lip a little rose
    loop = M.tag.get("mouth_loop")
    if loop:
        L = P[loop]
        o = np.argsort(L[:, 0])
        lx, lz = L[o, 0], L[o, 2]
        xc = float(np.abs(lx).max())
        zl = np.interp(x, lx, lz)
        zm = float(np.interp(0.0, lx, lz))
        ym = float(L[:, 1].min())
        near = face & (y < ym + 0.012)
        xr = x / max(xc, 1e-4)
        line = np.exp(-((z - zl) / 0.0008) ** 2) * (1.0 - smooth01(0.65, 0.92, np.abs(xr)))
        tint(line * near, (0.58, 0.37, 0.36), 0.5)
        lip = np.exp(-(((z - (zl - 0.0045)) / 0.0035) ** 2 + (x / (0.7 * xc)) ** 4))
        mult(lip * near * 0.7, (1.0, 0.83, 0.81))
        ulip = np.exp(-(((z - (zl + 0.003)) / 0.0022) ** 2 + (x / (0.75 * xc)) ** 4))
        mult(ulip * near * 0.45, (1.0, 0.85, 0.83))
        for s in (1.0, -1.0):
            c_ = np.array((s * xc * 0.98, ym + 0.006, float(np.interp(s * xc, lx, lz))))
            w = np.exp(-(np.linalg.norm(pos - c_, axis=-1) / 0.0025) ** 2)
            mult(w * near * 0.35, SOFT_SHADE)
    # the ears: rosy toward the rim
    ear = hit & (fam == "ear")
    mult(ear * (0.15 + 0.35 * smooth01(0.08, 0.12, ax)), ROSE)
    # (no shade anywhere else: the game's light models his forms)
    print("%s FACE painted by rule: tone %s, nose tip at %s" % (WHO, np.round(tone, 3), np.round(tip, 3)))
    return np.clip(rgb, 0, 1), pos, hit, np.array(tone, float)


def finish(M, T, joints, sh):
    H = M.tag["head_rings"]
    bones = skeleton_joints(M, T, joints)
    weights = weights_of(M, T, bones, joints)
    islands = plan_uvs(M, T, H, joints)
    placed, face_uv = pack(islands)
    under = boxer_faces(M, T)
    M, face_uv, weights, under = refine_forms(M, face_uv, weights, under, joints)
    M, face_uv, weights, under = refine_base_head(M, face_uv, weights, under, sh)
    M, face_uv, weights, under, eye_cut, eyes = open_eyes(M, face_uv, weights, under)
    snap_mouth_line(M)
    os.makedirs(TEX, exist_ok=True)
    for picture in ("skin", "face"):
        write_layout(face_uv, placed, picture, os.path.join(TEX, "brother_%s_layout.png" % picture))
    tris_all = M.tris()
    tf = M.tri_fams()
    P = np.array(M.P)
    no_arms = [t for t, f in zip(tris_all, tf) if f not in ("arm", "hand")]
    Pc, no_arms_c = with_caps(M, P, no_arms)

    def reject_skin(view, colour, rows, cols):
        return np.zeros(len(rows), bool)

    skin, spos, shit = paint_skin(M, face_uv, sh, tris_all, Pc, no_arms_c, reject_skin, joints)
    tone = np.array(FIGURE.get("skin_tone", SKIN_TONE), float)
    skin = delight(skin, spos, shit, target=tone)
    rule = FIGURE.get("rule_paint", False)
    if rule and YOUNG_SKIN:
        skin = young_skin(M, face_uv, skin, spos, shit, tone)
    else:
        # (ninth round, the critic: "the chest hair ... drawn as black scratches", "muscle definition ... painted as hard
        # dark lines", "dark stains": the fine detail's contrast taken down to SKIN_DETAIL of itself round a soft local
        # mean, and what stays darker than that mean turned from near black toward the hair's dark brown)
        soft = blur(fill_out(skin, shit, 8), 3)
        dev = skin - soft
        skin = np.where(shit[..., None], soft + dev * SKIN_DETAIL, skin)
        dark = np.clip(-dev.mean(-1) / 0.12, 0, 1)[..., None] * shit[..., None]
        skin = skin * (1 - 0.35 * dark) + (soft * np.array((0.62, 0.48, 0.36))) * 0.35 * dark
    if BASE_FEET:
        Pp = np.array(M.P)
        _, snrm, _, sfid = texel_geometry(M, face_uv, "skin", Pp, normals_of(Pp, M.tris()))
        fparts = np.array(list(M.fpart) + ["none"])[sfid]
        for sfx in ("_l", "_r"):
            o, f_, l_ = M.tag["foot_frame" + sfx]
            mine = shit & (fparts == "foot" + sfx)
            shin = shit & (fparts == "leg" + sfx) & (spos[..., 2] > 0.15) & (spos[..., 2] < 0.24)
            # (the skin between the hairs: the lighter half of the shin's texels, then its median darkened a little to
            # the hair's share, so the foot is neither paler nor darker than the shin looks)
            lum = skin[shin].mean(1)
            base_c = np.median(skin[shin][lum >= np.median(lum)], axis=0) * 0.9
            ring_z = float(np.array(M.P)[M.tag["leg_rings" + sfx][-1]][:, 2].mean())
            legs = shit & (fparts == "leg" + sfx)
            skin = paint_feet(skin, spos, snrm, shit, mine, (o, f_, l_), M.tag["foot_toes" + sfx], base_c, shin=legs, ring_z=ring_z)
            print("%s FEET painted%s: %d texels, the shin's tone %s" % (WHO, sfx, int(mine.sum()), np.round(base_c, 3)))
    if HEAD_ROUTE == "r7":
        face, fpos, fhit, fskin = r7_face(M, face_uv, tone)
        face = r7_paint_adjust(face, fpos, fhit, M)
    elif rule and FACE_BY_RULE:
        face, fpos, fhit, fskin = rule_face(M, face_uv, tone)
    else:
        face, fpos, fhit, fskin = paint_head(M, face_uv, sh)
        face0 = face
        face = delight(face, fpos, fhit, target=tone, k=0.55, cell=0.012, spread=3, lum_only=True)
        fskin = fskin * np.median(face[fhit], 0) / np.maximum(np.median(face0[fhit], 0), 1e-3)
    # The two sheets paint his skin differently (the head sheet a little cooler than the body sheet): the whole face picture
    # is brought to the body's tone (the median of its plain skin to the median of the body's chest and neck), then
    # the neck is matched where the two pictures meet (the torso's top ring), so no step shows.
    zt = float(np.mean([M.P[i][2] for i in T[-1]]))
    body_ref = np.median(skin[shit & (spos[..., 2] > zt - 0.25) & (spos[..., 2] < zt - 0.03)], axis=0)
    gain0 = body_ref / np.maximum(fskin, 1e-3)
    if rule and FACE_BY_RULE:
        gain0 = np.ones(3)    # (both pictures are painted in the one tone; the chest's hair would darken the face)
    # (only on skin: the eyes' blue and whites keep their colour)
    skinw = np.clip((face[..., 0] - face[..., 2] - 0.03) * 12.0, 0, 1)[..., None]
    face = np.clip(face * (1 + (gain0 - 1) * skinw), 0, 1)
    near_b = shit & (np.abs(spos[..., 2] - (zt - 0.02)) < 0.02)
    near_h = fhit & (np.abs(fpos[..., 2] - (zt + 0.01)) < 0.012)
    if near_b.any() and near_h.any():
        gain = skin[near_b].mean(0) / np.maximum(face[near_h].mean(0), 1e-3)
        # (ninth round, the critic: "the colour lines at the base of the neck": the gain had hit its 1.2 cap, so a step
        # stayed; now allowed to 1.5 and faded over 10 cm up the neck)
        gain = np.clip(gain, 0.8, 1.5)
        w = (1.0 - smooth01(zt, zt + 0.1, fpos[..., 2])) * fhit
        face = face * (1 + (gain - 1) * w[..., None])
        print("BROTHER face tone: times %s, then the neck times %s" % (np.round(gain0, 3), np.round(gain, 3)))
    if not (rule and FACE_BY_RULE):
        face = calm_nose(face, fpos, fhit)
    if not (rule and FACE_BY_RULE):   # (tenth round: the rule face is one tone; healing drew the body's broad tone into it as blotches)
        face = heal_seams(M, face_uv, "face", face, fpos, fhit, others=((skin, spos, shit, "skin"),))
    # (the islands' margins filled again from their healed edges: the old margins drew a thin line along each seam)
    face = fill_out(pad_edges(face, fhit), fhit | grown_by(fhit), 8)
    save_rgb(os.path.join(TEX, "brother_skin.png"), skin[::-1])
    save_rgb(os.path.join(TEX, "brother_face.png"), face[::-1])
    armature = make_armature(bones)
    mat_skin = textured_material("brother_skin", os.path.join(TEX, "brother_skin.png"))
    mat_face = textured_material("brother_face", os.path.join(TEX, "brother_face.png"))

    def skin_object(name, ids, materials=(mat_skin, mat_face)):
        ob = mesh_object(name, P, [M.faces[i] for i in ids], armature, weights)
        me = ob.data
        for m in materials:
            me.materials.append(m)
        uvl = me.uv_layers.new(name="UVMap")
        for poly, fi in zip(me.polygons, ids):
            pic, uv = face_uv.get(fi, ("skin", [(0.0, 0.0)] * poly.loop_total))
            poly.material_index = 0 if (pic == "skin" or len(materials) == 1) else 1
            for li, q in zip(poly.loop_indices, uv):
                uvl.data[li].uv = q
        return ob
    # His body, and the skin under the shorts as its own piece (never seen: whatever he wears covers it; hidden, not
    # deleted).
    skin_object("brother_body", [i for i in range(len(M.faces)) if i not in under and i not in eye_cut])
    # His eyes: balls of their own on the head bone, in the openings (open_eyes)
    eye_path = os.path.join(TEX, "brother_eye.png")
    eye_texture(eye_path)
    Pe, Fe = eye_balls(eyes)
    ob = mesh_object("brother_eyes", Pe, [f for f, _ in Fe], armature, [{"head": 1.0}] * len(Pe))
    ob.data.materials.append(textured_material("brother_eye", eye_path))
    uvl = ob.data.uv_layers.new(name="UVMap")
    for poly, (_, uv) in zip(ob.data.polygons, Fe):
        for li, q in zip(poly.loop_indices, uv):
            uvl.data[li].uv = q
    print("BROTHER EYES balls: %d triangles" % sum(len(f) - 2 for f, _ in Fe))
    skin_object("brother_body_under", sorted(under))
    Bx = build_boxers(M, T, sh, weights, under, armature)
    # His tattoos: lifted from the sheet, placed by the table, drawn as a see-through layer over his arms.
    ink_faces = lay_tattoos(M, face_uv, placed, sh)
    # Sixth round (the critic: "purple bruise smears" on the forearms, flanks and back; "the forearm hair paint runs
    # over and muddies" the tattoos): the sheet's purple shading turned to the skin's own hue at the same lightness
    # (where blue is up at or above green: skin, hair and the red blush all keep green over blue); then under each
    # tattoo (and 2 texels round it) the dark hair strokes lifted to the skin round them. Saved again over the first.
    med = np.median(skin[shit], 0)
    lum = skin.mean(-1, keepdims=True)
    tone = med[None, None, :] * lum / max(float(med.mean()), 1e-3)
    pw = np.clip((skin[..., 2] - skin[..., 1] + 0.06) / 0.05, 0, 1)[..., None] * shit[..., None]
    skin = skin * (1 - pw) + tone * pw
    ta = HB.get("tattoo_alpha")
    if ta is not None and ta.shape == skin.shape[:2]:
        m = (ta > 0.1).astype(float)
        for _ in range(2):
            m = np.maximum(m, blur(m, 1))
        m = np.clip(blur(m, 1) * 1.5, 0, 1)[..., None] * shit[..., None]
        soft = blur(skin, 6)
        skin = skin * (1 - m) + np.maximum(skin, soft) * m
    print("%s SKIN purple turned on %d texels; hair lifted under the tattoos on %d" % (
        WHO, int((pw[..., 0] > 0.5).sum()), int((m[..., 0] > 0.5).sum()) if ta is not None else 0))
    if not (rule and YOUNG_SKIN):   # (tenth round: the young skin is a 3D field already, alike either side of a seam)
        skin = heal_seams(M, face_uv, "skin", skin, spos, shit, others=((face, fpos, fhit, "face"),))
    skin = fill_out(pad_edges(skin, shit), shit | grown_by(shit), 8)
    save_rgb(os.path.join(TEX, "brother_skin.png"), skin[::-1])
    for im in bpy.data.images:
        if os.path.normcase(bpy.path.abspath(im.filepath)) == os.path.normcase(os.path.join(TEX, "brother_skin.png")):
            if im.packed_file:
                im.unpack(method="REMOVE")
            im.filepath = os.path.join(TEX, "brother_skin.png")
            im.reload()
            im.pack()
    if ink_faces:
        mat_ink = ink_material()
        ob = skin_object("brother_ink", ink_faces, (mat_ink,))
        for v in ob.data.vertices:
            v.co += v.normal * 0.0007
    report_counts(M, face_uv)
    print("BROTHER triangles shorts: %d" % getattr(Bx, "n_tris_out", len(Bx.tris())))
    objs = [(np.array(M.P), M.tris(), M.tri_fams())]
    Pc, tc = with_caps(M, np.array(M.P), [])
    objs.append((Pc, tc, ["sidecap"] * len(tc)))
    objs.append((np.array(Bx.P), Bx.tris(), ["shorts"] * len(Bx.tris())))
    stats = overlay(objs, sh, "final")
    print("BROTHER overlay final (with shorts) %s" % json.dumps(stats))
    head_silhouettes(M, sh, "final")
    head_landmarks(M, sh)
    body_silhouettes(objs, sh, "final")
    if OUT:
        export_checks(M, face_uv, mat_skin)
    export(armature, GLB)


def export_checks(M, face_uv, mat_skin):
    """For the comparison pictures (to --out only, never the game): his left hand flat as fitted to the sheet (its
    frame laid out as the back view sees it: x across toward the thumb, -y out of its back, z along the fingers) and
    in the thumb view's bend, painted, as hand_flat.glb; and where each sheet view lands (views.json)."""
    C2, _ = pose_hand(HB["flat"], HB["J"], HB["label"], HAND_POSE_THUMBVIEW)
    a, b = M.tag["hand_range_l"]
    faces = [M.faces[fi] for fi in M.tag["hand_faces_l"]]
    objs = []
    for name, C in (("hand_flat", HB["flat"]), ("hand_bent", C2)):
        P = np.zeros((len(M.P), 3))
        P[a:b] = np.stack([C[:, 0], -C[:, 1], C[:, 2]], 1)
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(map(float, p)) for p in P], [], faces)
        me.update()
        for poly in me.polygons:
            poly.use_smooth = True
        me.materials.append(mat_skin)
        uvl = me.uv_layers.new(name="UVMap")
        for poly, fi in zip(me.polygons, M.tag["hand_faces_l"]):
            for li, q in zip(poly.loop_indices, face_uv[fi][1]):
                uvl.data[li].uv = q
        ob = bpy.data.objects.new(name, me)
        bpy.context.scene.collection.objects.link(ob)
        objs.append(ob)
    for o in bpy.context.scene.objects:
        o.select_set(o in objs)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "hand_flat.glb"), export_format="GLB", use_selection=True,
                              export_yup=True, export_image_format="AUTO")
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    views = {"head": {v: HEAD_VIEWS[v][:2] for v in HEAD_VIEWS}, "head_sx": HEAD_SX, "head_chin": HEAD_CHIN,
             "chin_z": CHIN_Z, "body_s": S, "sole": SOLE, "mid": MID, "hand_sx": HAND_SX,
             "hand": {v: list(HB["views"][v]) for v in HB["views"]}}
    with open(os.path.join(OUT, "views.json"), "w") as f:
        json.dump(views, f, indent=1)


# ------------------------------------------------------------------------------------------------------------------
# The knit shorts: a garment over the body (its own grid down the torso's 16 columns from a waistband that is about
# level, round each thigh to a loose hem), painted by projecting the sheet's own shorts into its layout (front, back
# and his right side, mirrored for his left), the hand's place in the side view left out and filled.
# ------------------------------------------------------------------------------------------------------------------

BOXER_BAND = (703.0, 724.0)   # the waistband's top row at his back and at his front
BOXER_BAND_TALL = 26.0        # sheet pixels (3.8 cm): the ribbed knit band
BOXER_STAND = (0.012, 0.007, 0.03)   # metres: the cloth, the band, the hems (the legs are loose)
BOXER_LEG_RINGS = 2           # the leg rings down to LEG_ROWS[1] = row 937
BOXER_HEM = 934.0
SIDE_HAND = ((1360, 752), (1560, 912))   # the side view's hand over the shorts (columns, rows): not painted from


def band_row(phi):
    f = (1.0 + math.cos(phi)) / 2.0
    return BOXER_BAND[0] + (BOXER_BAND[1] - BOXER_BAND[0]) * f ** 1.6


def boxer_faces(M, T):
    """The body's faces the shorts cover wholly: torso faces whose top ring lies at or below the band's line in their
    column, and the thighs to the hem."""
    out = set()
    for fi, c in M.cell.items():
        if c[0] != "torso":
            continue
        i, k = c[1], c[2]
        phi = math.tau * (k + 0.5) / TORSO_N
        if TORSO_ROWS[i + 1] >= band_row(phi) + 8:
            out.add(fi)
    for sfx in ("_l", "_r"):
        rings = M.tag["leg_rings" + sfx][:BOXER_LEG_RINGS + 1]
        pts = set(v for r in rings for v in r)
        out |= {fi for fi, (f, p) in enumerate(zip(M.faces, M.fpart)) if p == "leg" + sfx and all(v in pts for v in f)}
    return out


# Fifth round (the critic: "a straight tube or skirt with no separate leg openings", "a hard bright white line all
# round the hem", "a flat shelf" of a waistband, "muddy grey-khaki"). The sheet itself parts the legs only about 5 cm
# above the hem (its shorts' crotch near row 903, the hem near 940: measured), so the legs are not made to part higher
# than the sheet; they read as two by hugging each thigh closely on the inside (a gap of air between them at the hem),
# a crotch that the cloth follows in, a front fullness and a seat with its middle line. Built at twice the body's
# density round (32 columns, 20 round each leg, by a four-point spline through the body's own rings), with a knit
# band of thickness, a turned hem (outer, a rolled lip, an inner face against the thigh: no rim stands off), and drawn
# with back faces culled.
#
# FOR OTHER FIGURES: knit_shorts() takes everything figure-specific as arguments (the body's points and normals, its
# torso rings and leg rings, the crotch point, the band's height round the waist, the hem's height, the stand-offs)
# and gives the garment's Mesh, each point's weights as a blend of body points, and its UV islands; paint and
# material stay with the figure (build_boxers below).

SHORTS_HEM = 943.0                 # the sheet's hem (front 940, back 942) and a little under
# (seventh round, the critic: "hems too wide and stand off the thighs": leg_out 0.016 -> 0.009, leg_in 0.005 -> 0.003)
SHORTS_STAND = {"band_lip": 0.002, "band": 0.006, "cloth": 0.011, "leg_in": 0.003, "leg_out": 0.009, "hug": 0.0025}
SHORTS_BULGE = 0.017               # metres: the front's fullness between the legs
SHORTS_SEAT = 0.005                # metres: the seat's middle line drawn in
SHORTS_FLY = 0.0025                # metres: the fly's seam drawn in
SHORTS_KEEP = 0.56                 # the share of the shorts' triangles kept by the collapse (912 -> about 510)


def ring_double(pts):
    """A closed ring of points with a new point between each two (the four-point subdivision rule: a smooth curve
    through the old points). Gives 2n points, the old ones at even places."""
    pts = np.asarray(pts, float)
    n = len(pts)
    out = np.zeros((2 * n,) + pts.shape[1:])
    for i in range(n):
        p0, p1, p2, p3 = pts[(i - 1) % n], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        out[2 * i] = p1
        out[2 * i + 1] = (-p0 + 9.0 * p1 + 9.0 * p2 - p3) / 16.0
    return out


def knit_shorts(P, N, T, leg_rings, crotch, band_z, band_tall, mid_zs, hem_z, side_cols, stand=SHORTS_STAND,
                bulge=SHORTS_BULGE, seat=SHORTS_SEAT, fly=SHORTS_FLY, lower_rings=3):
    """Knit shorts over a lofted body.
    P, N: the body's points and normals. T: the torso's rings (lists of point indices, the crotch's ring first, each
    starting at his front middle and going round toward +X). leg_rings: {"_l": rings, "_r": rings} from the leg's top
    (the torso's first ring's half and the crotch point) down, LIMB_N points each. crotch: the crotch point's index.
    band_z(phi): the waistband's top height at the angle phi round him (0 = his front). band_tall: the band's height
    (metres). mid_zs(z_band_bottom): the heights of the rows between the band and the torso rings kept. hem_z: the hem's
    height. side_cols(sfx): the torso columns (0..n/2) that the leg's top takes, in its own order.
    Gives (Mesh, src: [{body point: weight}] per point, islands: {name: {face: uvs in metres}}, info)."""
    nT = len(T[0])
    Bx = Mesh()
    src = []
    zs = np.array([P[r].mean(0)[2] for r in T])
    up = np.array((0.0, 0.0, 1.0))

    def column_at(k, z):
        ks = np.array([P[r[k]][2] for r in T])
        q = np.array([np.interp(z, ks, P[[r[k] for r in T]][:, a]) for a in range(3)])
        n = np.array([np.interp(z, ks, N[[r[k] for r in T]][:, a]) for a in range(3)])
        i = int(np.clip(np.searchsorted(ks, z), 1, len(ks) - 1))
        t = float(np.clip((z - ks[i - 1]) / max(ks[i] - ks[i - 1], 1e-9), 0, 1))
        return q, n / max(np.linalg.norm(n), 1e-9), {T[i - 1][k]: 1.0 - t, T[i][k]: t}

    def add(q, s, part="boxers"):
        src.append(s)
        return Bx.add(q, part)

    def blend(a, b, t=0.5):
        out = {}
        for d, w in ((a, 1.0 - t), (b, t)):
            for k, v in d.items():
                out[k] = out.get(k, 0.0) + v * w
        return out
    # the trunk: per column its band top, band bottom, rows between, then the torso's last rings
    z_low = [float(z) for z in zs[:lower_rings]][::-1]
    rows = []
    for k in range(nT):
        phi = math.tau * k / nT
        zb = band_z(phi)
        zb1 = zb - band_tall
        rows.append([zb, zb, zb1] + list(mid_zs(zb1)) + z_low)
    nrows = len(rows[0])
    G, grow = [], []
    for j in range(nrows):
        qs, ns, ss = [], [], []
        for k in range(nT):
            q, n, s = column_at(k, rows[k][j])
            qs.append(q)
            ns.append(n)
            ss.append(s)
        Q2 = ring_double(qs)
        N2 = ring_double(ns)
        N2 /= np.maximum(np.linalg.norm(N2, axis=1, keepdims=True), 1e-9)
        st = stand["band_lip"] if j == 0 else stand["band"] if j in (1, 2) else stand["cloth"]
        ring = []
        for i in range(2 * nT):
            s = ss[i // 2] if i % 2 == 0 else blend(ss[i // 2], ss[(i // 2 + 1) % nT])
            q = Q2[i] + N2[i] * st
            if j == 0:
                q = q - up * 0.003
            ring.append(add(q, s))
        G.append(ring)
    nc = 2 * nT
    for j in range(nrows - 1):
        for i in range(nc):
            ii = (i + 1) % nc
            Bx.face([G[j][i], G[j][ii], G[j + 1][ii], G[j + 1][i]], "boxers_band" if j < 2 else "boxers_torso")
            Bx.cell[len(Bx.faces) - 1] = ("trunk", j, i)
    bottom = G[-1]
    gc = add(P[crotch] - up * stand["cloth"], {crotch: 1.0})
    legs, rolls = {}, {}
    for sfx in ("_l", "_r"):
        side = 1.0 if sfx == "_l" else -1.0
        cols = side_cols(sfx)                     # torso columns 0..n/2 in the leg's own order
        # the top ring, doubled: the trunk's bottom row at whole and half columns, then the two points by the crotch
        top = []
        for a, b in zip(cols[:-1], cols[1:]):
            top.append(bottom[2 * a])
            # (the half column between two whole ones: the one the trunk made, between a and b going round)
            top.append(bottom[(2 * a + 1) % nc] if (b - a) % nT == 1 else bottom[(2 * a - 1) % nc])
        top.append(bottom[2 * cols[-1]])
        ten = [Bx.P[bottom[2 * c]] for c in cols] + [Bx.P[gc]]
        d10 = ring_double(ten)
        m1 = add(d10[2 * len(cols) - 1], blend(src[bottom[2 * cols[-1]]], src[gc]))
        m2 = add(d10[-1], blend(src[gc], src[bottom[2 * cols[0]]]))
        top += [m1, gc, m2]
        rings = [top]
        body = leg_rings[sfx]
        bz = np.array([P[r].mean(0)[2] for r in body])
        # the rings below: the body's first ring under the crotch, one between, and the hem
        z1 = bz[1]
        targets = [z1, (z1 + hem_z) / 2.0, hem_z]
        for ti, z in enumerate(targets):
            i = int(np.clip(np.searchsorted(-bz, -z), 1, len(bz) - 1))
            t = float(np.clip((bz[i - 1] - z) / max(bz[i - 1] - bz[i], 1e-9), 0, 1))
            A, B = body[i - 1], body[i]
            pts = P[A] * (1 - t) + P[B] * t
            c = pts.mean(0)
            hem = ti == len(targets) - 1
            q10 = []
            for p in pts:
                out = p - c
                out[2] = 0.0
                out /= max(np.linalg.norm(out), 1e-9)
                inner = max(0.0, -side * out[0])          # 1 facing the other leg
                st = stand["leg_in"] + (stand["leg_out"] - stand["leg_in"]) * (1.0 - inner) ** 1.5
                st = stand["cloth"] * (1 - (ti + 1) / len(targets)) + st * ((ti + 1) / len(targets))
                q = p + out * st
                q[2] = z
                q10.append(q)
            q20 = ring_double(q10)
            ring = []
            for m in range(len(q20)):
                k0, k1 = A[(m // 2) % len(A)], A[((m + 1) // 2) % len(A)]
                l0, l1 = B[(m // 2) % len(B)], B[((m + 1) // 2) % len(B)]
                s = blend(blend({k0: 1.0}, {k1: 1.0}), blend({l0: 1.0}, {l1: 1.0}), t)
                ring.append(add(q20[m], s))
            rings.append(ring)
        for a, b in zip(rings, rings[1:]):
            n = len(a)
            for j in range(n):
                k = (j + 1) % n
                Bx.face([a[j], a[k], b[k], b[j]], "boxers_leg" + sfx)
        # the turned hem: a lip a few millimetres under the hem, rolled in toward the thigh, and the inside face
        # against the thigh, a centimetre and a half up
        hem = rings[-1]
        hc = np.array([Bx.P[v] for v in hem]).mean(0)
        lip, inside = [], []
        for v in hem:
            q = np.array(Bx.P[v], float)
            dd = q - hc
            dd[2] = 0.0
            dd /= max(np.linalg.norm(dd), 1e-9)
            lip.append(add(q - dd * 0.004 - up * 0.004, src[v]))
        for v in hem:
            q = np.array(Bx.P[v], float)
            dd = q - hc
            dd[2] = 0.0
            dd /= max(np.linalg.norm(dd), 1e-9)
            # (the skin under it: the hem's own stand taken back to the hug)
            skin = q - dd * 0.0
            # find how far this hem point stands from the body: the body ring at the hem's height
            inside.append(add(q - dd * 0.009 + up * 0.014, src[v]))
        n = len(hem)
        roll = []
        for j in range(n):
            k = (j + 1) % n
            Bx.face([hem[j], hem[k], lip[k], lip[j]], "boxers_hem" + sfx)
            Bx.want[len(Bx.faces) - 1] = ("down", None)
            roll.append(len(Bx.faces) - 1)
            Bx.face([lip[j], lip[k], inside[k], inside[j]], "boxers_hem" + sfx)
            Bx.want[len(Bx.faces) - 1] = ("in", hc)
            roll.append(len(Bx.faces) - 1)
        legs[sfx] = rings
        rolls[sfx] = (hem, lip, inside, roll)
    # the forms: the front's fullness between the legs, the fly's seam, the seat's middle line
    Q = np.array(Bx.P)
    zc = float(P[crotch][2]) + 0.035
    cy = float(np.mean([P[r].mean(0)[1] for r in T[:2]]))
    front = Q[:, 1] < cy
    w = np.exp(-(Q[:, 0] / 0.055) ** 2 - ((Q[:, 2] - zc) / 0.05) ** 2) * front
    Q[:, 1] -= bulge * w
    zf0 = min(band_z(0.0) - band_tall, zc + 0.11)
    wf = np.exp(-(Q[:, 0] / 0.008) ** 2) * front * smooth01(zc + 0.02, zc + 0.05, Q[:, 2]) * (1.0 - smooth01(zf0 - 0.02, zf0, Q[:, 2]))
    Q[:, 1] += fly * wf
    ws = np.exp(-(Q[:, 0] / 0.02) ** 2) * (~front) * smooth01(zc - 0.03, zc + 0.04, Q[:, 2]) * (1.0 - smooth01(zc + 0.14, zc + 0.2, Q[:, 2]))
    Q[:, 1] -= seat * ws
    # the hem's soft wave (cloth, not a pipe)
    for sfx in ("_l", "_r"):
        hem, lip, inside, _ = rolls[sfx]
        for m, v in enumerate(hem):
            Q[v, 2] += 0.0025 * math.sin(m * math.tau * 3 / len(hem) + (0.7 if sfx == "_l" else 2.1))
            Q[lip[m], 2] += 0.0025 * math.sin(m * math.tau * 3 / len(hem) + (0.7 if sfx == "_l" else 2.1))
    Bx.P = [q for q in Q]
    # UVs: the trunk's front and back halves unrolled by distance round its middle row; each leg round its axis;
    # each hem's roll its own strip
    mid = G[nrows // 2]
    seg = [float(np.linalg.norm(Q[mid[(i + 1) % nc]] - Q[mid[i]])) for i in range(nc)]
    islands = {"boxers_front": {}, "boxers_back": {}}
    q0, q1 = nc * 3 // 4, nc // 4
    for fi, c in Bx.cell.items():
        j, i = c[1], c[2]
        is_front = i >= q0 or i < q1
        start = q0 if is_front else q1
        uv = []
        for v in Bx.faces[fi]:
            kv = G[j].index(v) if v in G[j] else G[j + 1].index(v)
            kk = (kv - start) % nc
            if kk > nc // 2:
                kk -= nc
            u = sum(seg[(start + m) % nc] for m in range(kk)) if kk >= 0 else -seg[(start - 1) % nc]
            uv.append((u if is_front else -u, float(Q[v][2])))
        islands["boxers_front" if is_front else "boxers_back"][fi] = uv
    for sfx, s in (("_l", 1.0), ("_r", -1.0)):
        ring = legs[sfx][1]
        cx, cy_ = Q[ring][:, 0].mean(), Q[ring][:, 1].mean()
        R = float(np.hypot(Q[ring][:, 0] - cx, Q[ring][:, 1] - cy_).mean())
        isl, hisl = {}, {}
        hem, lip, inside, roll = rolls[sfx]
        vpos = {}
        for v in hem:
            vpos[v] = 0.0
        for v in lip:
            vpos[v] = -0.006
        for v in inside:
            vpos[v] = -0.022
        for fi, p in enumerate(Bx.fpart):
            if p not in ("boxers_leg" + sfx, "boxers_hem" + sfx):
                continue
            th = [math.atan2(-(Q[v][1] - cy_), s * (Q[v][0] - cx)) for v in Bx.faces[fi]]
            if max(th) - min(th) > math.pi:
                th = [t + math.tau if t < 0 else t for t in th]
            if p.startswith("boxers_hem"):
                hisl[fi] = [(s * t * R, vpos[v]) for t, v in zip(th, Bx.faces[fi])]
            else:
                isl[fi] = [(s * t * R, float(Q[v][2])) for t, v in zip(th, Bx.faces[fi])]
        islands["boxers_leg" + sfx] = isl
        islands["boxers_hem" + sfx] = hisl
    return Bx, src, islands, {"zc": zc, "cy": cy, "rows": nrows}


def build_boxers(M, T, sh, weights, under, armature):
    P = np.array(M.P)
    N = normals_of(P, M.tris())
    crotch = M.tag["crotch"][0]

    def band_z(phi):
        return float(body_z(band_row(phi)))

    def mid_zs(zb1):
        z822 = float(body_z(822.0))
        return [zb1 + (z822 - zb1) * t for t in (0.33, 0.66, 1.0)]

    def side_cols(sfx):
        return list(range(0, 9)) if sfx == "_l" else [col_of(k, -1) for k in range(0, 9)]
    lower = sum(1 for r in TORSO_ROWS if r >= 835)
    Bx, src, islands, info = knit_shorts(P, N, M.tag["torso_rings"][:12], {s: M.tag["leg_rings" + s] for s in ("_l", "_r")},
                                         crotch, band_z, BOXER_BAND_TALL * S, mid_zs, float(body_z(SHORTS_HEM)),
                                         side_cols, stand=SHORTS_STAND, lower_rings=lower)
    # every face turned the way it must look: out from the body, the hem's lip down, its inside in
    Q = np.array(Bx.P)
    flipped = 0
    turned = set()
    for fi, f in enumerate(Bx.faces):
        n = face_normal(Q, f)
        want = Bx.want.get(fi)
        if want is None:
            nb = np.zeros(3)
            for v in f:
                for b, w in src[v].items():
                    nb += N[b] * w
            ok = np.dot(n, nb) >= 0
        elif want[0] == "down":
            ok = n[2] <= 0
        else:
            c = Q[f].mean(0) - want[1]
            c[2] = 0.0
            ok = np.dot(n, c) <= 0
        if not ok:
            Bx.faces[fi] = f[::-1]
            turned.add(fi)
            flipped += 1
    for n_ in islands:
        ISLANDS[n_] = ("shorts", 0.5 if n_.startswith("boxers_hem") else 1.0)
    ATLAS["shorts"] = 1024
    placed, face_uv = pack(islands)
    # (seventh round, the captain's builder found it: a face turned for its winding must have its corners' UVs turned
    # with it, or a printed pattern tears into shards and the rib and fly paint smear at those faces)
    for fi in turned:
        if fi in face_uv:
            pic, uv = face_uv[fi]
            face_uv[fi] = (pic, list(uv)[::-1])
    write_layout(face_uv, placed, "shorts", os.path.join(TEX, "brother_shorts_layout.png"))

    def reject(view, colour, rows, cols):
        (c0, r0), (c1, r1) = SIDE_HAND
        bad = ~is_boxers(colour)
        if view == "side":
            bad |= (cols >= c0) & (cols <= c1) & (rows >= r0) & (rows <= r1)
        return bad
    views = [("front", sh.body_pix, sh.body_mask, False), ("back", sh.body_pix, sh.body_mask, False),
             ("side", sh.body_pix, sh.body_mask, False), ("side", sh.body_pix, sh.body_mask, True)]
    rgb, hit = paint(Bx, face_uv, "shorts", sh, views, Bx.tris(), extra_reject=reject)
    Qb = np.array(Bx.P)
    pos_b, nrm_b, hit_b, fid_b = texel_geometry(Bx, face_uv, "shorts", Qb, normals_of(Qb, Bx.tris()))
    # the sheet's painted shade mostly taken out, to clean cream cotton; its folds' small changes kept (sixth round:
    # #E6DAC0, warmer than the #E9E2CF before, which read white or grey under the lights: the sheet's lit cloth measures
    # 213,200,177 and the critic asked for about #E8DFC8)
    rgb = delight(rgb, pos_b, hit_b & hit, target=np.array((0.94, 0.905, 0.82)), k=0.85, cell=0.025, spread=3)
    # (and most of the way to the plain cream: the sheet's cloth is clean, its smudges and grey were not wanted)
    cream = np.array(FIGURE.get("cream", (0.902, 0.855, 0.753)))
    ck = FIGURE.get("cream_k", 0.55)
    rgb[hit_b] = cream * ck + rgb[hit_b] * (1.0 - ck)
    rgb = paint_knit(rgb, pos_b, hit_b, fid_b, Bx, info)
    path = os.path.join(TEX, "brother_shorts.png")
    save_rgb(path, rgb[::-1])
    w = []
    for s in src:
        acc = {}
        for b, k in s.items():
            for bone, v in weights[b].items():
                acc[bone] = acc.get(bone, 0.0) + v * k
        top4 = sorted(acc.items(), key=lambda kv: -kv[1])[:4]
        tot = sum(v for _, v in top4)
        w.append({b: v / tot for b, v in top4})
    ob = mesh_object("brother_shorts", Bx.P, Bx.faces, armature, w)
    mat = textured_material("brother_shorts", path)
    mat.use_backface_culling = True
    ob.data.materials.append(mat)
    uvl = ob.data.uv_layers.new(name="UVMap")
    for poly in ob.data.polygons:
        for li, q in zip(poly.loop_indices, face_uv[poly.index][1]):
            uvl.data[li].uv = q
    # (sixth round, the triangle budget: the grid was 912 triangles, most of them flat cloth over the belly and seat;
    # collapsed to about 500, mirrored, the UV seams and the hems' outline kept: the rib and the fly are paint)
    dec = ob.modifiers.new("fewer", "DECIMATE")
    dec.decimate_type = "COLLAPSE"
    dec.ratio = SHORTS_KEEP
    dec.use_symmetry = True
    dec.symmetry_axis = "X"
    dec.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.view_layer.objects:
        o.select_set(o is ob)
    mods = [m for m in ob.modifiers if m.type == "DECIMATE"]
    for m in mods:
        ob.modifiers.move(ob.modifiers.find(m.name), 0)
        bpy.ops.object.modifier_apply(modifier=m.name)
    n_after = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    print("BROTHER shorts: %d triangles (%d before the collapse), %d faces turned" % (n_after, len(Bx.tris()), flipped))
    Bx.n_tris_out = n_after
    return Bx


def paint_knit(rgb, pos, hit, fid, Bx, info, rib=0.006):
    """The knit's details over the cleaned paint: the band ribbed (soft upright stripes every `rib` metres round) with
    a shadow line under it, the fly's seam (a double stitch line down his front middle), the crotch's soft folds as
    shade fanning from it, the hem's lip a little darker."""
    parts = np.array(list(Bx.fpart) + ["none"])[fid]
    band = hit & (parts == "boxers_band")
    ang = np.arctan2(pos[..., 0], -(pos[..., 1] - info["cy"]))
    R = np.hypot(pos[..., 0], pos[..., 1] - info["cy"])
    stripes = 0.5 + 0.5 * np.cos(ang * R / rib * math.tau)
    rgb[band] *= (0.93 + 0.07 * stripes[band])[:, None]
    zb = pos[..., 2]
    # the line under the band: the lowest band texels of each column and the cloth just under
    torso = hit & (parts == "boxers_torso")
    under = np.zeros_like(torso)
    if band.any():
        bins = np.round(ang * 16).astype(int)
        for b in np.unique(bins[band]):
            zmin = zb[band & (bins == b)].min()
            sel = torso & (bins == b) & (zb > zmin - 0.008) & (zb < zmin)
            under |= sel
    rgb[under] *= 0.92
    front = pos[..., 1] < info["cy"]
    zc = info["zc"]
    for dx in (-0.004, 0.004):
        st = hit & front & (np.abs(pos[..., 0] - dx) < 0.0011) & (zb > zc + 0.03) & (zb < zc + 0.12)
        rgb[st] *= 0.88
    # the crotch's folds: soft shade lines fanning up and out from it, on the front of each leg
    for s in (1.0, -1.0):
        x = s * pos[..., 0]
        for k, a in enumerate((0.35, 0.75)):
            d = (zb - (zc - 0.035)) * math.cos(a) - x * math.sin(a)
            fold = hit & front & (x > 0.01) & (x < 0.13) & (zb > zc - 0.06) & (zb < zc + 0.06)
            g = np.exp(-(d / 0.006) ** 2)[fold]
            rgb[fold] *= (1.0 - 0.07 * g)[:, None]
    lip = hit & np.char.startswith(parts.astype(str), "boxers_hem")
    rgb[lip] *= 0.94
    return rgb


# ------------------------------------------------------------------------------------------------------------------
# The head's picture, from the head sheet (tpose3): front, back, his right side (mirrored for his left). He is bare:
# the hair, the moustache and most of the stubble are painted out to skin; the brows, eyes, lids, the rosy nose and
# the lips are kept.
# ------------------------------------------------------------------------------------------------------------------

def paint_head(M, face_uv, sh):
    """His head's picture from the bald row: the front view where the surface faces within about 50 degrees of his
    front, the side view (his right; mirrored for his left) for his sides, the back view behind, handed over across
    narrow bands (so no feature is laid down twice), each texel only where its view sees it (a depth test); what no
    view sees filled from round it."""
    P = np.array(M.P)
    tris = M.tris()
    head_tris_ = head_tris(M)
    N = normals_of(P, tris)
    pos, nrm, hit, fid = texel_geometry(M, face_uv, "face", P, N)
    size = ATLAS["face"]
    acc = np.zeros((size, size, 3))
    wsum = np.zeros((size, size))
    mask = erode(sh.head_mask, 2)
    Nall = nrm.reshape(-1, 3)
    phi = np.degrees(np.abs(np.arctan2(-Nall[:, 0], -Nall[:, 1])))
    wf = 1.0 - smooth01(46.0, 60.0, phi)
    wb = smooth01(120.0, 134.0, phi)
    share = {"head_front": wf, "head_back": wb, "head_side": np.clip(1.0 - wf - wb, 0, 1)}
    left = Nall[:, 0] > 0           # (his left side: painted from the right side's view, mirrored)
    for view in ("head_front", "head_back", "head_side"):
        for mirrored in ((False, True) if view == "head_side" else (False,)):
            Q = pos.reshape(-1, 3).copy()
            Nn = Nall.copy()
            Pm = P.copy()
            if mirrored:
                Q[:, 0] *= -1
                Nn[:, 0] *= -1
                Pm[:, 0] *= -1
            P2, dep = project(view, Pm)
            zb, _ = raster(P2, dep, head_tris_, sh.head_mask.shape)
            q2, qd = project(view, Q)
            _, facing = screen_dir(view, Nn)
            cols = np.clip(q2[:, 0].astype(int), 0, mask.shape[1] - 1)
            rows = np.clip(q2[:, 1].astype(int), 0, mask.shape[0] - 1)
            seen = (qd <= zb[rows, cols] + 0.006) & mask[rows, cols] & (facing > 0.05) & hit.ravel()
            # (not the jaw's underside, which every view sees only aslant: it took the chin's own shadow line from the
            # front view and read as a second chin; filled from round it)
            seen &= Nall[:, 2] > -0.4
            # (nor the top of the scalp, which every view sees only aslant, at the sheet's dark outline: it painted a
            # brown smear on his crown (the critic); filled from round it)
            seen &= (Nall[:, 2] < 0.6) & (facing > 0.25)
            # (and the jaw's edge and the neck under it, which each view sees near its outline, where the sheet
            # draws its jaw line and shadow: they painted red-brown smears along the jaw and a second chin line)
            rq = head_row(Q[:, 2])
            seen &= ~((rq > SMILE[0] + 19) & (facing < 0.6))
            if view == "head_side":
                seen &= (left if mirrored else ~left)
            colour = sh.head_pix[rows, cols]
            w = np.where(seen, share[view] * (0.2 + 0.8 * np.clip(facing, 0, 1)), 0.0)
            acc += (colour * w[:, None]).reshape(size, size, 3)
            wsum += w.reshape(size, size)
    good = wsum > 0.02
    rgb = acc / np.maximum(wsum, 1e-6)[..., None]
    fam_t = np.array([part_family(p) for p in M.fpart] + ["none"])[fid]
    rows_t = head_row(pos[..., 2])
    # (the chest hair the sheet paints below his collarbones is not his neck's: none reaches the head's picture, but
    # the sheet's line under the jaw and its shadow are softened where the neck meets the body)
    rgb = fill_out(rgb, good, 200)
    soft = blur(rgb, 3)
    rgb = np.where(good[..., None], rgb, soft)
    print("BROTHER paint face: %.0f%% of its texels seen by a view" % (100.0 * (good & hit).sum() / max(hit.sum(), 1)))
    front = hit & (nrm[..., 1] < -0.5) & np.isin(fam_t, ("head",)) & (rows_t > 950) & (rows_t < 990)
    fskin = np.median(rgb[front], axis=0) if front.any() else np.median(rgb[hit], axis=0)
    return rgb, pos, hit, fskin


# ------------------------------------------------------------------------------------------------------------------
# His tattoos, movable (the user: "the tattoos need to be moveable so we can postion them eventually"): each lifted from
# the body sheet into its own picture (its ink only, on a clear ground: textures/tattoos/brother_<name>.png); a table
# (textures/brother/brother_tattoos.json) of where each sits: the island of his skin's layout, the middle's place in it
# (x, y from 0 to 1, as the layout's JSON gives the island's rectangle; y up), its width on him in metres, its turn
# (degrees, anticlockwise in the layout) and whether it is mirrored; the overlay picture composited from the table
# (textures/brother/brother_tattoo_overlay.png) and drawn as a see-through layer, `brother_ink`, over his arms. The skin
# under them is clean. The build places them where the sheet has them and writes the table, unless the table says
# "keep": true (then it is left as it is: the place to move them by hand).
# ------------------------------------------------------------------------------------------------------------------

# (name, view, columns, rows) on the body sheet: the box round each tattoo in the view that sees it most squarely.
TATTOO_GROW = 1.4      # each tattoo this much bigger than its box on the sheet (the critic: "scale each tattoo up about 1.5 times")
TATTOO_INK = (0.2, 0.25, 0.33)   # (seventh round: one blue-black, darker, as old sailor work reads)
TATTOO_LINE = (0.022, 0.06)      # lift_tattoo: how much darker than the skin round it a line is (start, full)
TATTOO_FILL = 0.45               # lift_tattoo: the designs' fills against their lines
TATTOO_CLOSE = 0                  # lift_tattoo: pixels the lines are closed over (a figure's "consts" sets it)
TATTOOS = (
    ("anchor", "side", (1384, 1456), (622, 716)),
    ("banner_anchor", "front", (786, 866), (436, 556)),
    ("swallow", "front", (828, 912), (596, 684)),
    ("rope_knot", "front", (890, 968), (650, 726)),
)


def lift_tattoo(sh, c0, c1, r0, r1):
    """The ink in a box of the sheet as an RGBA picture (rows top down): ink is bluer and darker than the skin round
    it; brown body hair is not ink."""
    pix = sh.body_pix[r0:r1, c0:c1].copy()
    rb = pix[..., 0] - pix[..., 2]
    lum = pix.mean(-1)
    skin = rb > np.percentile(rb, 60) - 0.02
    skin_rb = float(np.median(rb[skin]))
    skin_lum = float(np.median(lum[skin]))
    # (seventh round, from the captain's build: clean old-sailor line work that reads at game distance. The LINES are
    # what is markedly darker than the skin just round it (a local mean, so the soft painted fill drops out) and bluer;
    # the FILL (bluer and darker than the skin) kept at TATTOO_FILL of the lines' strength; the lines thickened a pixel;
    # the edges crisp; specks with no ink round them dropped; one blue-black ink, no skin colour riding along)
    local = blur(lum[..., None], 6)[..., 0]
    a = np.clip((local - lum - TATTOO_LINE[0]) / TATTOO_LINE[1], 0, 1) * np.clip((skin_rb - rb - 0.015) / 0.05, 0, 1)
    a *= np.clip((skin_lum - lum) / 0.08, 0, 1)
    fill = np.clip((skin_rb - rb - 0.03) / 0.05, 0, 1) * np.clip((skin_lum - lum - 0.03) / 0.07, 0, 1)
    line = np.clip((a - 0.15) / 0.5, 0, 1)
    line = np.maximum(line, np.maximum.reduce([np.roll(line, 1, 0), np.roll(line, -1, 0), np.roll(line, 1, 1), np.roll(line, -1, 1)]) * 0.85)
    a = np.maximum(line, fill * TATTOO_FILL)
    a = blur(a[..., None], 1)[..., 0]
    a = smooth01(0.28, 0.55, a) * np.maximum(a, 0.7)
    near = blur((a > 0.3).astype(float)[..., None], 3)[..., 0]
    a[near < 0.12] = 0.0
    a[~sh.body_mask[r0:r1, c0:c1]] = 0.0
    if TATTOO_CLOSE:
        # (eighth round: tpose8 paints his forearm designs under thick hair, and the hairs cut the lines into lace: the
        # lines closed (grown then shrunk TATTOO_CLOSE pixels), and the arm's own dark outline, which ran along the
        # anchor's box, left out (the figure shrunk 4 pixels))
        def grow(x, n, op):
            for _ in range(n):
                x = op.reduce([x, np.roll(x, 1, 0), np.roll(x, -1, 0), np.roll(x, 1, 1), np.roll(x, -1, 1)])
            return x
        a = grow(grow(a, TATTOO_CLOSE, np.maximum), TATTOO_CLOSE, np.minimum)
        a[~erode(sh.body_mask, 4)[r0:r1, c0:c1]] = 0.0
    a = np.clip(a, 0, 1) * 0.9
    ink = np.broadcast_to(np.array(TATTOO_INK, np.float32), pix.shape).copy()
    return np.concatenate([ink, a[..., None]], 2).astype(np.float32)


def tri_faces(M):
    out = []
    for fi, f in enumerate(M.faces):
        out += [fi] * (len(f) - 2)
    return out


def uv_at(M, face_uv, view, col, row):
    """The skin picture's place (island name, uv) of his surface that the sheet's pixel shows in a view."""
    P = np.array(M.P)
    tris = M.tris()
    tfam = M.tri_fams()
    tface = tri_faces(M)
    keep = [i for i, f in enumerate(tfam) if not (view == "side" and f in ("head",)) and f in ("arm", "hand", "torso", "shoulder")]
    T = [tris[i] for i in keep]
    Pm = P.copy()
    P2, dep = project(view, Pm)
    best = None
    for k, t in enumerate(T):
        a, b, c = P2[t[0]], P2[t[1]], P2[t[2]]
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-9:
            continue
        w0 = ((b[1] - c[1]) * (col - c[0]) + (c[0] - b[0]) * (row - c[1])) / den
        w1 = ((c[1] - a[1]) * (col - c[0]) + (a[0] - c[0]) * (row - c[1])) / den
        w2 = 1 - w0 - w1
        if min(w0, w1, w2) < -1e-6:
            continue
        d = w0 * dep[t[0]] + w1 * dep[t[1]] + w2 * dep[t[2]]
        if best is None or d < best[0]:
            best = (d, keep[k], (w0, w1, w2))
    if best is None:
        return None
    _, ti, (w0, w1, w2) = best
    fi = tface[ti]
    f = M.faces[fi]
    tri = tris[ti]
    pic, uvs = face_uv[fi]
    uv = sum(np.array(uvs[f.index(v)]) * wt for v, wt in zip(tri, (w0, w1, w2)))
    return fi, pic, uv


def lay_tattoos(M, face_uv, placed, sh):
    os.makedirs(TATTOO_DIR, exist_ok=True)
    table = os.path.join(TEX, "brother_tattoos.json")
    old = None
    if os.path.exists(table):
        with open(table) as f:
            old = json.load(f)
    pictures = {}
    rows = []
    face_island = {}
    for name, (pic, u0, v0, sc, (w, h)) in placed.items():
        face_island[name] = (pic, u0, v0, sc, w, h)
    for name, view, (c0, c1), (r0, r1) in TATTOOS:
        rgba = lift_tattoo(sh, c0, c1, r0, r1)
        pictures[name] = rgba
        save_rgba(os.path.join(TATTOO_DIR, "brother_%s.png" % name), rgba)
        cx, cy = (c0 + c1) / 2.0, (r0 + r1) / 2.0
        here = uv_at(M, face_uv, view, cx, cy)
        right = uv_at(M, face_uv, view, cx + 6, cy)
        up = uv_at(M, face_uv, view, cx, cy - 6)
        if not here or not right or not up:
            print("BROTHER tattoo %s: not on him" % name)
            continue
        fi, pic, uv = here
        isl = next(n for n, (p_, a0, b0, sc, w, h) in face_island.items() if p_ == pic and a0 - 1e-6 <= uv[0] <= a0 + w * sc + 1e-6 and b0 - 1e-6 <= uv[1] <= b0 + h * sc + 1e-6)
        _, a0, b0, sc, w, h = face_island[isl]
        ar, au = right[2] - uv, up[2] - uv
        mirror = float(ar[0] * au[1] - ar[1] * au[0]) < 0
        turn = math.degrees(math.atan2(au[1], au[0])) - 90.0
        rows.append({"picture": "brother_" + name, "part": isl, "x": round(float((uv[0] - a0) / (w * sc)), 4),
                     "y": round(float((uv[1] - b0) / (h * sc)), 4), "size": round((c1 - c0) * S * TATTOO_GROW, 4),
                     "turn": round(turn, 1), "mirror": bool(mirror), "strength": 1.0})
    if old and old.get("keep"):
        rows = old["rows"]
        print("BROTHER tattoos: the table says keep; placed as it says")
    else:
        with open(table, "w") as f:
            json.dump({"keep": False, "skin": "brother_skin_layout.json", "pictures": "res://textures/tattoos/",
                       "rows": rows}, f, indent=1)
    size = ATLAS["skin"]
    out = np.zeros((size, size, 4), np.float32)
    rects = []
    for row in rows:
        if row["part"] not in face_island:
            continue
        pic, a0, b0, sc, w, h = face_island[row["part"]]
        img = pictures.get(row["picture"].replace("brother_", ""))
        if img is None:
            continue
        ph, pw = img.shape[:2]
        wd = row["size"] * sc * size
        ht = wd * ph / pw
        cx = (a0 + row["x"] * w * sc) * size
        cy = (b0 + row["y"] * h * sc) * size
        reach = int(max(wd, ht) * 0.75) + 2
        ys, xs = np.mgrid[int(cy) - reach:int(cy) + reach, int(cx) - reach:int(cx) + reach]
        ok = (xs >= 0) & (xs < size) & (ys >= 0) & (ys < size)
        dx, dy = xs + 0.5 - cx, ys + 0.5 - cy
        t = math.radians(row.get("turn", 0.0))
        qx = dx * math.cos(t) + dy * math.sin(t)
        qy = -dx * math.sin(t) + dy * math.cos(t)
        if row.get("mirror"):
            qx = -qx
        px = qx / wd + 0.5
        py = qy / ht + 0.5
        inside = ok & (px >= 0) & (px < 1) & (py >= 0) & (py < 1)
        src = img[((1.0 - py[inside]) * ph).astype(int).clip(0, ph - 1), (px[inside] * pw).astype(int).clip(0, pw - 1)]
        yy, xx = ys[inside], xs[inside]
        a = src[:, 3] * row.get("strength", 1.0)
        rects.append((cx - reach, cy - reach, cx + reach, cy + reach))
        put = a > out[yy, xx, 3]
        out[yy[put], xx[put], :3] = src[put, :3]
        out[yy[put], xx[put], 3] = a[put]
    HB["tattoo_alpha"] = out[..., 3].copy()
    path = os.path.join(TEX, "brother_tattoo_overlay.png")
    save_rgba(path, out[::-1])
    print("BROTHER tattoos: %d placed: %s" % (len(rows), [(r["picture"], r["part"], r["turn"], r["mirror"]) for r in rows]))
    parts = {r["part"] for r in rows}
    fams = {p.split("_")[0] + ("_" + p.split("_")[1] if p.startswith(("arm", "hand")) else "") for p in parts}
    ink = []
    for fi, (pic, uv) in face_uv.items():
        if pic != "skin":
            continue
        q = np.array(uv) * size
        lo, hi = q.min(0), q.max(0)
        if any(lo[0] <= r[2] and hi[0] >= r[0] and lo[1] <= r[3] and hi[1] >= r[1] for r in rects):
            ink.append(fi)
    return ink


def save_rgba(path, rgba):
    rgba = np.clip(np.asarray(rgba, dtype=np.float32), 0, 1)
    h, w = rgba.shape[:2]
    img = bpy.data.images.new(os.path.basename(path), w, h, alpha=True)
    img.pixels.foreach_set(rgba[::-1].ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def ink_material():
    mat = bpy.data.materials.new("brother_ink")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tex = nt.nodes.new("ShaderNodeTexImage")
    img = bpy.data.images.load(os.path.join(TEX, "brother_tattoo_overlay.png"))
    img.pack()
    tex.image = img
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    bsdf.inputs["Roughness"].default_value = 1.0
    for key in ("Specular IOR Level", "Specular"):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = 0.0
    mat.blend_method = "BLEND"
    mat.use_backface_culling = True
    return mat

def paint_hands(M, face_uv, rgb, hit, fid, sh, base_c):
    """Third build: the hands painted from their own sheet's back and palm views. Each hand texel is found on the hand
    as fitted in the sheet's pose (M.tag["hand_flat_*"]: the same points, flat, in the hand's own frame) and takes the
    sheet's colour where that view sees it squarely (the back view for the back, the palm view for the palm); then
    brought to the forearm's tone, fading into it over the first few centimetres from the wrist, so no band shows."""
    if "views" not in HB:
        return rgb, np.zeros(hit.shape, bool)
    P = np.array(M.P)
    Palt = P.copy()
    sign = {}
    for sfx in ("_l", "_r"):
        flat = M.tag["hand_flat" + sfx]
        ids = np.array(list(flat))
        Palt[ids] = np.array([flat[i] for i in ids])
    Nalt = normals_of(Palt, M.tris())
    for sfx in ("_l", "_r"):
        ids = np.array(list(M.tag["hand_flat" + sfx]))
        c = Palt[ids].mean(0)
        sign[sfx] = 1.0 if float(((Palt[ids] - c) * Nalt[ids]).sum()) > 0 else -1.0
    pos, nrm, _, _ = texel_geometry(M, face_uv, "skin", Palt, Nalt)
    parts = np.array(list(M.fpart) + ["none"])[fid]
    wrist = np.zeros(hit.shape, bool)
    for sfx in ("_l", "_r"):
        wf = np.zeros(len(M.faces) + 1, bool)
        wf[M.tag["wrist_faces" + sfx]] = True
        wrist |= hit & wf[fid]
    hands = hit & np.char.startswith(parts.astype(str), "hand") & ~wrist
    nb = nrm[..., 1] * np.where(np.char.startswith(parts.astype(str), "hand_l"), sign["_l"], sign["_r"])
    mask = erode(sh.hands_mask, 3)
    acc = np.zeros_like(rgb)
    wsum = np.zeros(rgb.shape[:2])
    for v, s_ in (("back", 1.0), ("palm", -1.0)):
        col0, row0 = HB["views"][v]
        u = pos[..., 0] * s_
        col = col0 + u / HAND_SX
        row = row0 - pos[..., 2] / HAND_SX
        c = np.clip(col.astype(int), 0, mask.shape[1] - 1)
        r = np.clip(row.astype(int), 0, mask.shape[0] - 1)
        ok = hands & mask[r, c] & (row < 560) & (row > 60)
        w = np.where(ok, np.clip(s_ * nb, 0, 1) ** 2 + 1e-3, 0.0)
        acc += sh.hands_pix[r, c] * w[..., None]
        wsum += w
    good = hands & (wsum > 0.02)
    col_ = acc / np.maximum(wsum, 1e-6)[..., None]
    filled = fill_out(np.where(good[..., None], col_, rgb), good | ~hands, 60)
    soft = blur(filled, 2)
    filled = np.where(good[..., None], filled, soft)
    # the sheet's hand to the forearm's tone: the median of its back near the wrist against the forearm's
    near = good & (pos[..., 2] < 0.06)
    ref = np.median(filled[near], axis=0) if near.any() else np.median(filled[good], axis=0)
    gain = np.clip(base_c / np.maximum(ref, 1e-3), 0.7, 1.4)
    out = rgb.copy()
    k = smooth01(HAND_LOOP_L, HAND_LOOP_L + 0.035, pos[..., 2])[..., None]
    out[hands] = np.clip((filled * gain * k + base_c * (1 - k))[hands], 0, 1)
    out[wrist] = base_c
    print("BROTHER hands painted from their sheet: %d texels (%d seen), tone times %s" % (int(hands.sum()), int(good.sum()), np.round(gain, 3)))
    return out, hands


def paint_skin(M, face_uv, sh, tris_all, Pc, no_arms_c, reject, joints=None):
    """His body's picture: front and back views for all of him, the side view (his right; mirrored for his left)
    for the trunk and legs, which the side view shows."""
    P = np.array(M.P)
    tris = M.tris()
    N = normals_of(P, tris)
    pos, nrm, hit, fid = texel_geometry(M, face_uv, "skin", P, N)
    size = ATLAS["skin"]
    fam_face = np.array([p.split("_")[0] for p in M.fpart] + ["none"])
    tex_fam = fam_face[fid]
    acc = np.zeros((size, size, 3))
    wsum = np.zeros((size, size))
    mask = erode(sh.body_mask, 2)
    for view, mirrored in (("front", False), ("back", False), ("side", False), ("side", True)):
        Q = pos.reshape(-1, 3).copy()
        Nn = nrm.reshape(-1, 3).copy()
        Pm = (Pc if view == "side" else P).copy()
        if mirrored:
            Q[:, 0] *= -1
            Nn[:, 0] *= -1
            Pm[:, 0] *= -1
        P2, dep = project(view, Pm)
        zb, _ = raster(P2, dep, no_arms_c if view == "side" else tris, sh.body_mask.shape)
        q2, qd = project(view, Q)
        _, facing = screen_dir(view, Nn)
        cols = np.clip(q2[:, 0].astype(int), 0, mask.shape[1] - 1)
        rows = np.clip(q2[:, 1].astype(int), 0, mask.shape[0] - 1)
        seen = (qd <= zb[rows, cols] + 0.012) & mask[rows, cols] & (facing > 0.08) & hit.ravel()
        # (the torso seen aslant took the sheet's dark outline and the shadow under the arm along his flanks: only
        # where a view sees it fairly squarely; the rest is filled from round it)
        seen &= ~(np.isin(tex_fam.ravel(), ("torso", "shoulder")) & (facing < np.where(Q[:, 2] > body_z(420), 0.45, 0.3)))
        # (the arms likewise, more loosely: their outer sides took the sheet's outline as dark smudges)
        seen &= ~(np.isin(tex_fam.ravel(), ("arm",)) & (facing < np.where(Q[:, 2] > joints["elbow_l"].z, 0.38, 0.22)))
        # (and the legs' insides, which the front and back views see only aslant, in the crotch's shadow)
        seen &= ~(np.isin(tex_fam.ravel(), ("leg",)) & (facing < 0.25) & (view != "side"))
        if view == "side":
            seen &= ~np.isin(tex_fam.ravel(), ("arm", "hand", "shoulder"))
            # (his right arm hangs over his side there: the torso above the hem is not painted from the side view)
            seen &= ~(np.isin(tex_fam.ravel(), ("torso",)) & (Q[:, 2] > body_z(BOXERS[1] - 30)))
            # (ninth round, the critic: "the concept's hanging hand has been painted onto his thighs": the side view's
            # hand hangs over his thigh below the hem; nothing is painted from the sheet's pixels inside it, the thigh
            # there is filled from the skin round it)
            (hc0, hr0), (hc1, hr1) = SIDE_HAND_SKIN
            seen &= ~((cols >= hc0) & (cols <= hc1) & (rows >= hr0) & (rows <= hr1))
        colour = sh.body_pix[rows, cols]
        seen &= ~reject(view, colour, rows, cols)
        w = np.where(seen, facing ** 2, 0.0)
        acc += (colour * w[:, None]).reshape(size, size, 3)
        wsum += w.reshape(size, size)
    good = wsum > 0.02
    rgb = acc / np.maximum(wsum, 1e-6)[..., None]
    # (under the boxers: by where the texel is on him, from their waistband to their hem, the trunk and thighs)
    z = pos[..., 2]
    # (the band filled plain lies inside the boxers garment, which reaches row BOXER_TOP_ROW to BOXER_HEM_ROW, so
    # its edge is never seen)
    # (the band's line slopes: low under the belly at his front, higher at his back; the belly above it is skin)
    phi_t = np.arctan2(pos[..., 0], -(pos[..., 1] - 0.03))
    band_t = BOXER_BAND[0] + (BOXER_BAND[1] - BOXER_BAND[0]) * ((1.0 + np.cos(phi_t)) / 2.0) ** 1.6
    box = hit & np.isin(tex_fam, ("torso", "leg")) & (z < body_z(band_t + 6)) & (z > body_z(BOXERS[1] - 14))
    # (eighth round: only near the shorts' own rows: tpose8 paints his lit skin pale enough to pass for the cream, and
    # whole arms and thighs were painted out)
    box |= (good & is_boxers(rgb) & np.isin(tex_fam, ("torso", "leg")) & (z < body_z(BOXERS[0] - 25))
            & (z > body_z(BOXERS[1] + 25)))
    # (the beard hangs over his upper chest in the body sheet: its grey is not skin)
    mx, mn = rgb.max(-1), rgb.min(-1)
    beard = np.zeros_like(good)
    # Tattoo ink, judged against the skin round it (stage one judged by colour alone and took a fifth of his skin,
    # the shaded chest and belly with it): bluer than the skin near it by a margin (measured on the sheet: ink about (0.53, 0.55, 0.55), no darker
    # than the skin round it, red minus blue under 0.04; skin 0.08 to 0.14; the grey chest hair about 0.07).
    skinlike = (rgb[..., 0] - rgb[..., 2]) > 0.06      # (the skin round a tattoo, not the tattoo)
    local = blur(fill_out(rgb, good & ~box & ~beard & skinlike, 16), 10)
    rb, lrb = rgb[..., 0] - rgb[..., 2], local[..., 0] - local[..., 2]
    ink = good & (rb < lrb - 0.06) & (rb < 0.05)
    # (on the arms the tattoos' soft painted edges are only a little bluer than the skin and were left as faint traces;
    # there, where no grey chest hair can be mistaken for ink, the margin is looser and the cut wider)
    arms = np.isin(tex_fam, ("arm", "hand"))
    ink |= good & arms & (((rb < lrb - 0.02) & (rb < 0.12)) | (rgb[..., 2] > rgb[..., 0] - 0.02))
    for _ in range(2):
        ink = ink | np.roll(ink, 1, 0) | np.roll(ink, -1, 0) | np.roll(ink, 1, 1) | np.roll(ink, -1, 1)
    for _ in range(5):
        ink = ink | (arms & (np.roll(ink, 1, 0) | np.roll(ink, -1, 0) | np.roll(ink, 1, 1) | np.roll(ink, -1, 1)))
    good &= ~ink & ~box & ~beard
    print("BROTHER paint skin: %d texels of tattoo ink painted out, %d of boxers" % (int(ink.sum()), int(box.sum())))
    rgb = fill_out(rgb, good, 300)
    soft = blur(rgb, 4)
    rgb = np.where(good[..., None], rgb, soft)
    # The hands (sixth round): the base sheet paints them a few pixels across, so taken from it they came out in dark
    # smudges. They take the sheet's hand colour (the median of what it paints them) with a quarter of its variation,
    # a little redder toward the fingertips and on the palm, as the hands sheet paints them.
    hands = hit & (tex_fam == "hand")
    if hands.any():
        # (the hands take the colour of the forearm just above the wrist, so no step shows there)
        near_wrist = np.zeros_like(hands)
        if joints is not None:
            for sfx in ("_l", "_r"):
                Wj = np.array(joints["wrist" + sfx] if "wrist" + sfx in joints else mirror_x(joints["wrist_l"], -1), float)
                near_wrist |= hit & (tex_fam == "arm") & (np.linalg.norm(pos - Wj, axis=-1) < 0.07)
        base_c = np.median(rgb[near_wrist], axis=0) if near_wrist.any() else np.median(rgb[hands & good], axis=0)
        print("BROTHER hands: %d texels of forearm by the wrists, colour %s" % (int(near_wrist.sum()), np.round(base_c, 3)))
        fid_parts = np.array(list(M.fpart) + ["none"])[fid]
        finger = hands & np.char.count(fid_parts.astype(str), "_") >= 2
        flat = np.ones_like(rgb) * base_c
        hk = 1.0 if (YOUNG_SKIN and FIGURE.get("rule_paint")) else 0.75   # (tenth round: plain, no sheet streaks)
        rgb[hands] = flat[hands] * hk + blur(rgb, 6)[hands] * (1.0 - hk)
        # (the forearm's last few centimetres fade into the hands' colour: no edge at the wrist)
        if joints is not None:
            for sfx in ("_l", "_r"):
                Wj = np.array(mirror_x(joints["wrist_l"], 1 if sfx == "_l" else -1), float)
                d = np.linalg.norm(pos - Wj, axis=-1)
                fade = hit & (tex_fam == "arm") & (d < 0.08)
                k = np.clip(1.0 - d / 0.08, 0, 1)[fade][:, None] ** 0.8
                rgb[fade] = rgb[fade] * (1 - k) + (base_c * 0.8 + rgb[fade] * 0.2) * k
        rgb[finger] = rgb[finger] * np.array((1.04, 0.97, 0.95))
        # Seventh round (the user: "his hands still seem poor quality compared to like twilight princess hands"):
        # painted as the Twilight Princess figures' hands are (looked at, not copied: their skin is one tone with the
        # forms painted in small: pale nails on the fingertips' backs, thin dark creases over the knuckles, the
        # fingers' sides and the gaps between them darker, the palm a little redder and darker than the back).
        if joints is not None:
            fparts = np.array(list(M.fpart) + ["none"])[fid]
            for sfx in ("_l", "_r"):
                Tb, Wd, L = (np.array(v, float) for v in joints["hand_frame" + sfx])
                mine = hands & np.char.startswith(fparts.astype(str), "hand" + sfx)
                back = (nrm * Tb).sum(-1)
                side_ = np.abs((nrm * Wd).sum(-1))
                palm = mine & (back < -0.25)
                rgb[palm] *= np.array((1.0, 0.9, 0.87))
                for name in FINGERS + ("thumb",):
                    f_ = mine & (fparts == "hand%s_%s" % (sfx, name))
                    bones = [np.array(b, float) for b in joints[name + sfx]]
                    up_ = Tb if name != "thumb" else np.array(joints["thumb_back" + sfx], float)
                    bk = (nrm * up_).sum(-1)
                    # the sides of each finger, toward its neighbours, in shadow; more so near the palm
                    near_root = np.clip(1.0 - np.linalg.norm(pos - bones[0], axis=-1) / 0.03, 0, 1)
                    gap = f_ & (side_ > 0.55) & (bk < 0.6)
                    rgb[gap] *= (0.88 - 0.1 * near_root[gap])[:, None]
                    # creases over the joints, on the back: a line and a fainter one beside it
                    for j in (1, 2):
                        a_ = bones[j + 1] - bones[j - 1]
                        a_ /= max(np.linalg.norm(a_), 1e-9)
                        t_ = ((pos - bones[j]) * a_).sum(-1)
                        crease = f_ & (bk > 0.15) & (np.abs(t_) < 0.0011)
                        rgb[crease] *= 0.86
                        faint = f_ & (bk > 0.15) & (np.abs(t_ - 0.0032) < 0.0008)
                        rgb[faint] *= 0.94
                    # the nail: on the last joint's back, pale, its edge darker; the fingertip below it pinker
                    a_ = bones[3] - bones[2]
                    a_ /= max(np.linalg.norm(a_), 1e-9)
                    t_ = ((pos - bones[3]) * a_).sum(-1)
                    nail = f_ & (bk > 0.35) & (t_ > -0.013) & (t_ < 0.004)
                    rgb[nail] = rgb[nail] * 0.35 + np.array((0.86, 0.74, 0.7)) * 0.65
                    rim = nail & ((np.abs(t_ + 0.013) < 0.0012) | (bk < 0.45))
                    rgb[rim] *= 0.82
                    pad = f_ & (bk < -0.2) & (t_ > -0.016)
                    rgb[pad] *= np.array((1.04, 0.95, 0.93))
                # the knuckles' tops a touch lighter, the back of the hand's middle a little darker between them
                for name in FINGERS:
                    k0 = np.array(joints[name + sfx][0], float)
                    top = mine & (back > 0.5) & (np.linalg.norm(pos - k0, axis=-1) < 0.011)
                    rgb[top] *= 1.06
    if hands.any() and not (YOUNG_SKIN and FIGURE.get("rule_paint")):
        rgb, _ = paint_hands(M, face_uv, rgb, hit, fid, sh, base_c)
    print("BROTHER paint skin: %.0f%% of its texels seen by a view" % (100.0 * (good & hit).sum() / max(hit.sum(), 1)))
    return rgb, pos, hit
# (seventh round: measured in the viewer's light (sun 0.25, ambient 0.8) the 0.84, 0.645, 0.505 albedo rendered his lit
# chest 240, 192, 155 against the sheet's 166..189, 128..139, 102..108: the albedo brought to about the sheet's own
# painted tone, so the lit front lands on it and the shaded back a little under it)
# (ninth round, the critic: "a muddy, dark red-brown"; measured in the viewer (brother9/a1/view/p_front.png) his lit
# belly rendered 132, 100, 80 against the sheet's 192, 161, 136: about 0.69 of it and redder (green over red 0.76 against
# 0.84, blue 0.61 against 0.71). The albedo lifted by that and turned to the sheet's own balance)
SKIN_TONE = np.array((0.9, 0.755, 0.635))
SKIN_DETAIL = 0.7                                # finish: the share of the skin picture's fine detail kept
SKIN_TONE_OLD = np.array((0.84, 0.645, 0.505))   # the sheet's lit skin (between its thighs' #C59674 and lights' #F0C8A6)
DELIGHT = 0.85                                 # how much of the sheet's painted light and shade is taken out


def delight(rgb, pos, hit, target=SKIN_TONE, k=DELIGHT, cell=0.02, spread=3, lum_only=False):
    """Polish pass (the critic: "far too dark and red-brown ... heavy baked dark shading in the flanks, armpits and
    back of the legs"). The sheets paint light and shade into the skin, and the game lights him again: the shade came
    twice. The picture's slow changes of colour are measured IN 3D (texels binned into `cell` cubes on the body,
    averaged, blurred over `spread` cubes, so islands that sit side by side in the picture never mix) and divided out
    toward `target`, `k` of the way; what changes fast (hair, tattoos, nails, creases, blush edges) is kept."""
    lo_ = pos[hit].min(0) - cell * 4
    idx = np.floor((pos - lo_) / cell).astype(int)
    shape = tuple(idx[hit].max(0) + 5)
    s = np.zeros(shape + (3,))
    n = np.zeros(shape)
    ih = idx[hit]
    np.add.at(s, (ih[:, 0], ih[:, 1], ih[:, 2]), rgb[hit])
    np.add.at(n, (ih[:, 0], ih[:, 1], ih[:, 2]), 1.0)
    for _ in range(spread):
        for ax in range(3):
            s = s + np.roll(s, 1, ax) + np.roll(s, -1, ax)
            n = n + np.roll(n, 1, ax) + np.roll(n, -1, ax)
    low = s / np.maximum(n, 1e-6)[..., None]
    L = low[ih[:, 0], ih[:, 1], ih[:, 2]]
    out = rgb.copy()
    if lum_only:
        # (the face: only its light taken out, its colours (the blush, the red nose) kept)
        gain = ((target.mean() / np.maximum(L.mean(1), 0.05)) ** k)[:, None]
    else:
        gain = (target[None, :] / np.maximum(L, 0.05)) ** k
    out[hit] = np.clip(rgb[hit] * gain, 0, 1)
    print("BROTHER SKIN delit: low tone median %s -> %s" % (np.round(np.median(L, 0), 3), np.round(np.median(out[hit], 0), 3)))
    return out


SEAM_REACH = 0.02     # heal_seams: metres either side of a seam over which both sides are drawn to one colour


NOSE_AT = (0.0, -0.205, 1.748)   # calm_nose: about the middle of his nose's ball (m), and its reach (below)
NOSE_REACH = 0.03


def calm_nose(rgb, pos, hit):
    """The user (2026-11-18): "hes a bit too red button nosed". The nose's red pulled back toward a mild warm flush:
    within NOSE_REACH of its ball (softly), only on the face's front, each texel's colour moved toward the face's own
    skin tone with a touch of warmth, keeping its light and shade (its brightness against the skin's); FIGURE
    "nose_red" is how much of the sheet's red stays (the cheeks are not touched)."""
    keep = FIGURE.get("nose_red", 1.0)
    if keep >= 1.0:
        return rgb
    d = np.linalg.norm(pos - np.array(NOSE_AT), axis=-1)
    w = (1.0 - smooth01(NOSE_REACH * 0.55, NOSE_REACH, d)) * hit * (pos[..., 1] < NOSE_AT[1] + 0.035)
    plain = hit & (d > 0.05) & (d < 0.09) & (pos[..., 1] < -0.1)
    skin = np.median(rgb[plain], 0) if plain.any() else np.array((0.75, 0.57, 0.45))
    # (red: redder than the face's own skin, red over green)
    redness = ((rgb[..., 0] - rgb[..., 1]) - (skin[0] - skin[1]) - 0.02) / 0.1
    w = w * np.clip(redness, 0, 1) * (1.0 - keep)
    flush = skin * np.array((1.05, 0.96, 0.94))
    lum = rgb.mean(-1, keepdims=True) / max(float(skin.mean()), 1e-3)
    calm = np.clip(flush * lum, 0, 1)
    out = rgb * (1 - w[..., None]) + calm * w[..., None]
    print("%s NOSE calmed: %d texels, the sheet's red kept %.0f%%" % (WHO, int((w > 0.3).sum()), keep * 100))
    return out


def heal_seams(M, face_uv, picture, rgb, pos, hit, others=(), reach=SEAM_REACH, cell=0.012):
    """Seventh round, from the captain's build (the critic: seams at the neck's base, the crown, the wrists, the ankles,
    under the shorts' hems). Where a UV island's edge meets another's, the two sides were painted apart. Near every
    seam (within `reach` on him, in 3D) each texel is drawn toward one colour field made in 3D from both sides at once
    (the mean colour of small cubes, each with its 26 neighbours). This figure's addition: `others`, a list of (rgb,
    pos, hit, picture) of his other pictures, so the seam where the face picture meets the skin picture (the neck's
    "necklace") is healed from both pictures' colours."""
    P = np.array(M.P)
    first = {}
    seam = []
    other_pics = {o[3] for o in others}
    for fi, f in enumerate(M.faces):
        if fi not in face_uv:
            continue
        pic = face_uv[fi][0]
        if pic != picture and pic not in other_pics:
            continue
        uvs = face_uv[fi][1]
        for i in range(len(f)):
            a, b = f[i], f[(i + 1) % len(f)]
            ua, ub = np.array(uvs[i]), np.array(uvs[(i + 1) % len(f)])
            key = (min(a, b), max(a, b))
            here = (pic, ua, ub) if a < b else (pic, ub, ua)
            if key in first:
                o = first[key]
                if picture not in (o[0], here[0]):
                    continue
                if o[0] != here[0] or np.abs(o[1] - here[1]).max() > 1e-4 or np.abs(o[2] - here[2]).max() > 1e-4:
                    seam.append(key)
            else:
                first[key] = here
    if not seam:
        return rgb
    pts = np.array([P[a] + (P[b] - P[a]) * t for a, b in seam for t in np.linspace(0, 1, 6)])
    kd = kdtree.KDTree(len(pts))
    for i, p in enumerate(pts):
        kd.insert(Vector([float(v) for v in p]), i)
    kd.balance()
    lo, hi = pts.min(0) - reach, pts.max(0) + reach
    cand = hit & np.all((pos >= lo) & (pos <= hi), axis=-1)
    rr, cc = np.where(cand)
    dist = np.array([kd.find(Vector([float(v) for v in pos[r, c]]))[2] for r, c in zip(rr, cc)])
    near = dist < reach
    rr, cc, dist = rr[near], cc[near], dist[near]
    srcs = [(rgb, pos, cand)]
    for o_rgb, o_pos, o_hit, _ in others:
        srcs.append((o_rgb, o_pos, o_hit & np.all((o_pos >= lo) & (o_pos <= hi), axis=-1)))
    allp = np.concatenate([sp[sc] for _, sp, sc in srcs])
    allc = np.concatenate([sr[sc] for sr, _, sc in srcs])
    q = np.floor(allp / cell).astype(np.int64) + (1 << 18)
    code = q[:, 0] + (q[:, 1] << 20) + (q[:, 2] << 40)
    uniq, inv = np.unique(code, return_inverse=True)
    sums = np.zeros((len(uniq), 3))
    cnt = np.zeros(len(uniq))
    np.add.at(sums, inv, allc)
    np.add.at(cnt, inv, 1)
    ssum, scnt = np.zeros_like(sums), np.zeros_like(cnt)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                k = uniq + dx + (dy << 20) + (dz << 40)
                j = np.clip(np.searchsorted(uniq, k), 0, len(uniq) - 1)
                ok = uniq[j] == k
                ssum[ok] += sums[j[ok]]
                scnt[ok] += cnt[j[ok]]
    field = ssum / np.maximum(scnt, 1)[:, None]
    qn = np.floor(pos[rr, cc] / cell).astype(np.int64) + (1 << 18)
    cn = qn[:, 0] + (qn[:, 1] << 20) + (qn[:, 2] << 40)
    j = np.clip(np.searchsorted(uniq, cn), 0, len(uniq) - 1)
    w = (1.0 - smooth01(reach * 0.35, reach, dist))[:, None]
    out = rgb.copy()
    # (the field is broad colour only: each texel keeps its own small detail, its ratio to the blurred picture)
    soft = blur(rgb, 3)
    detail = rgb[rr, cc] / np.maximum(soft[rr, cc], 1e-3)
    out[rr, cc] = rgb[rr, cc] * (1 - w) + np.clip(field[j] * detail, 0, 1) * w
    print("%s SEAMS healed (%s): %d seam edges, %d texels drawn together" % (WHO, picture, len(seam), len(rr)))
    return out


def report_counts(M, face_uv):
    by = {}
    for f, p in zip(M.faces, M.fpart):
        fam = p.split("_")[0]
        if fam == "hand" and p.count("_") >= 2:
            fam = "fingers"
        by[fam] = by.get(fam, 0) + len(f) - 2
    print("BROTHER triangles by part: %s; all %d" % (json.dumps(by), sum(by.values())))


def export(armature, path, skip=(), keep=None, blend=True):
    """Writes the armature and its meshes to a .glb: all but those named in skip, or only those named in keep."""
    # (nothing but him goes out: a run without --factory-startup once exported the start-up file's Icosphere)
    for o in list(bpy.data.objects):
        if o != armature and o.parent != armature:
            print("BROTHER not exported, removed: %s" % o.name)
            bpy.data.objects.remove(o, do_unlink=True)

    def wanted(o):
        if o == armature:
            return True
        if o.parent != armature:
            return False
        name = o.name.split(".")[0]
        return name in keep if keep is not None else name not in skip
    for o in bpy.context.scene.objects:
        o.select_set(wanted(o))
    bpy.context.view_layer.objects.active = armature
    os.makedirs(os.path.dirname(path), exist_ok=True)
    kw = dict(filepath=path, export_format="GLB", use_selection=True, export_skins=True, export_animations=False,
              export_apply=False, export_tangents=True, export_texcoords=True, export_normals=True,
              export_yup=True, export_image_format="AUTO")
    try:
        bpy.ops.export_scene.gltf(export_vertex_color="ACTIVE", **kw)
    except TypeError:
        bpy.ops.export_scene.gltf(**kw)
    print("BROTHER wrote %s" % path)
    if blend:
        os.makedirs(os.path.dirname(BLEND), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=BLEND)
        print("BROTHER wrote %s" % BLEND)


if __name__ == "__main__":
    main()
