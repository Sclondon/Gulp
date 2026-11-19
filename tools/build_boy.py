"""The younger boy (13, blond, the one who wears the machine's helmet and plays as the fish), built from his sheets.

    blender --background --factory-startup --python tools/build_boy.py -- [--out <folder>] [--rounds N]

Writes models/boy.glb, tools/blend/boy.blend, textures/boy/ (his skin and face pictures, each with a layout picture
and a JSON of its islands, and his shorts' picture) and, in --out, the overlay pictures of every fitting round.

The user: "the younger boy 13 and eager and fresh blonde"; "the models for the other characters not just the captain".
Not in the game yet: the title still uses models/title_boy.glb.

The method is the captain's (tools/build_captain.py, "The captain's model: what failed and the method that replaces
it" in CLAUDE.md), its code copied here and changed, never his mesh:

1. THE SHEETS, MEASURED. tools/art_src/concept_boy_tpose.jpg: front, side (his right) and back of his base body at
   one scale, arms hanging about 40 degrees out. No head sheet: his head is measured off the same sheet, from crops
   of it (HEAD_TABLE, NOSE_PROFILE, EAR_*), the skull under the hair rounded inside it. The face is painted from the
   painted-face trial (concept_faces_trial.jpg, his close-up at the bottom right), which draws the same face 2.2
   times larger (measured: eyes, brows, nose, mouth and chin agree to a pixel at that scale), with eyes.
   The figure is cut from the pale ground by its colour (a flood by small steps leaked through his soft edges).
2. THE BODY, LOFTED: the torso as rings of 16 as wide as the front view and as deep as the side view; the arms out of
   holes in the torso along their drawn axes; legs split at the crotch, into feet; hands with a wedge palm, fingers
   and a thumb grown out of it; the head as rings from the table, a lofted nose, ears with a bowl.
3. FITTED to the sheet's outlines (FIT_ROUNDS), the shorts drawn in by BOXER_EASE.
4. HIS OWN SKELETON with the game's figures' bone names and hierarchy (the captain's), placed at his joints.
5. PLANNED UVS, 6. PAINT projected from the sheets (the face from the trial, toned to the body sheet's skin),
   his hair painted out (the base model is bare: hair goes on top later, drawn by the hair shader).
7. FORMS IN THE MESH: collarbones, pecs, shoulder blades, spine, waist, navel, knees, elbows, and the face's brow,
   sockets, lids, cheeks, lips and chin, checked in plain grey.

Model space: Blender's, Z up, he faces -Y (the game's +Z after export), +X is his left. Metres. He stands in the
sheet's own pose (his rest pose).
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
TEX = os.path.join(ROOT, "textures", "boy")
GLB = os.path.join(ROOT, "models", "boy.glb")
BLEND = os.path.join(HERE, "blend", "boy.blend")

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


OUT = arg("--out", "")
# (twelfth pass) --glb <path>: a trial build written elsewhere (its pictures and .blend beside it), so before/after
# pairs can be built side by side without touching models/boy.glb
if "--glb" in ARGS:
    GLB = os.path.abspath(arg("--glb", GLB))
    TEX = os.path.join(os.path.dirname(GLB), "tex")
    BLEND = os.path.join(os.path.dirname(GLB), "boy.blend")
FIT_ROUNDS = int(arg("--rounds", "6"))
HEAD_FIT_ROUNDS = int(arg("--head-rounds", "10"))

# ------------------------------------------------------------------------------------------------------------------
# The sheets
# ------------------------------------------------------------------------------------------------------------------

SHEET = os.path.join(ART, "concept_boy_tpose2.jpg")
FACE_SHEET = os.path.join(ART, "concept_faces_trial.jpg")

# FIFTH PASS (2026-11-18): the sheets redrawn (concept_boy_tpose2.jpg, concept_boy_head2.jpg) because the first ones
# drew a squat little man (head 1/5.4 of his height, crotch at 35%, painted muscles). The old sheets are retired
# (kept, unread). Every sheet row the earlier passes used is carried to the new sheets through two maps by landmarks,
# BR (body sheet rows) and HR (head sheet rows); the landmarks themselves are measured off the new sheets.


def _pl(x, pairs):
    """Piecewise linear through (old, new) pairs, carried on straight past both ends."""
    xs = np.array([a for a, _ in pairs], float)
    ys = np.array([b for _, b in pairs], float)
    x = np.asarray(x, float)
    y = np.interp(x, xs, ys)
    lo, hi = x < xs[0], x > xs[-1]
    y = np.where(lo, ys[0] + (x - xs[0]) * (ys[1] - ys[0]) / (xs[1] - xs[0]), y)
    y = np.where(hi, ys[-1] + (x - xs[-1]) * (ys[-1] - ys[-2]) / (xs[-1] - xs[-2]), y)
    return y


# old body sheet row -> new: crown, chin, the neck's base, armpit, the shorts' band, crotch, hem, knee, ankle, sole
BR_PAIRS = ((135, 73), (380, 310), (415, 378), (605, 515), (800, 692), (1000, 868), (1034, 950), (1110, 1095),
            (1352, 1375), (1462, 1495))
# old head sheet row -> new: the bald row's top, crown, brows, eyes, nose's tip, its base, mouth, chin, neck, bottom
HR_PAIRS = ((700, 840), (718, 862), (905, 1035), (948, 1103), (1012, 1170), (1046, 1195), (1082, 1223), (1165, 1305),
            (1190, 1330), (1344, 1480))


def BR(r):
    return int(round(float(_pl(r, BR_PAIRS))))


def HR(r):
    return int(round(float(_pl(r, HR_PAIRS))))


# The base-body sheet (pixels of the 2752 by 1536 picture). Measured: the soles (side view) 1495, the chin 310, the
# eyes 203 (39 pixels each side of his middle), the mouth 273; the skull's crown under the hair at row 73, from the
# head sheet's proportions at its scale (0.535 of its pixels: eye spread, eye to mouth, eye to chin). He is 6.0 heads
# tall; the shorts' band 692 at his front, 699 at his back, the crotch 868, the hem 950; knees 1095, ankles 1375.
SOLE = 1495.0
CROWN = 73.0
HEIGHT = 1.50                 # metres, soles to crown
S = HEIGHT / (SOLE - CROWN)   # metres a pixel (1.05 mm)
MID = {"front": 562.5, "side": 1381.5, "back": 2210.5}
SPAN = {"front": (90, 1150), "side": (1150, 1680), "back": (1700, 2740)}
BODY_UNLINE = ((20, 60), (1020, 1100))
# The shorts: the rows they cover (the band's top, the hem), the crotch, and how far the body sits inside them.
BOXERS = (692, 950)
CROTCH = 868
BOXER_EASE = 14               # pixels (1.5 cm)
# The side view draws his near arm over his side: those pixels are not painted from, and the back's outline there is
# the arm's: the fitting's target takes SIDE_BACK instead (rows, columns of his back drawn behind the arm, Claude's
# reading of the sheet: the shoulder blades, the small of the back, the seat of the shorts, the backs of the thighs).
SIDE_PATCH = ((1262, 392), (1412, 1012))
SIDE_BACK = ((392, 1318), (430, 1306), (480, 1302), (540, 1307), (600, 1318), (650, 1328), (690, 1330), (730, 1318),
             (780, 1305), (830, 1302), (880, 1306), (940, 1316), (1000, 1323), (1020, 1325))
# The painted-face trial: its close-up of him is this sheet's face times FACE_K, his eye line's middle at FACE_AT
# (this sheet's (674.5, 256)).
FACE_K = 2.2
FACE_AT = (2277.5, 1162.0)
FACE_REF_ROW = 256.0

# The head sheet (second pass, the user: "The heads and hands need a lot of work on all three- make sure you are
# matching pose silhouettes aggressively"): tools/art_src/concept_boy_head.jpg, 3168 by 1344, two rows of five views
# (front, 3/4, side, 3/4 back, back); the BOTTOM row, shaved bald, is the base model's head. All five share one scale
# and one row for each height (the guide lines run across them). Measured off its outlines (its rows): the crown 718,
# the brows 905, the eyes 948, the nose's tip 1012, its base 1046, the mouth 1082, the chin's bottom 1165.
# To the body: the chin at the body sheet's row 380, one head pixel HS metres (the mean of brow-to-chin, 148 body
# pixels against 260, and the brows' width, 174 body pixels against 314: 0.643 and 0.626 mm).
#
# FIFTH PASS: tools/art_src/concept_boy_head2.jpg, 2752 by 1536, the same layout; the bald row's landmarks: crown 862,
# brows 1035, eyes 1103 (75 pixels each side of his middle), nose's tip 1170, its base 1195, mouth 1223 (corners 72
# out), chin 1305, the jaw's angles 1240 (128 out), the ears 1080 to 1225. The chin at the body sheet's row 310.
HEAD_SHEET = os.path.join(ART, "concept_boy_head2.jpg")
HEAD_UNLINE = ((2700, 2745), (2652, 2662))
HS = S * 0.535
H_CHIN = 1305.0
Z_CHIN = float((SOLE - 310.0) * S)
H_CROWN = 862.0
H_BALD = (840, 1536)          # the bald row's rows
# Each view: the eye's azimuth round him (degrees: 0 his front, 90 his right, 180 his back) and the picture column of
# the head's middle line. The side's column is set so that the neck's middle below the chin (1374) is the body sheet's
# neck middle (y 0); the 3/4 views' angles and columns are found by matching their outlines (Sheets._fit_angled).
HVIEW = {"hfront": [0.0, 360.0], "hside": [90.0, 1374.0], "hback": [180.0, 2420.0],
         "hq": [45.0, 900.0], "hqb": [225.0, 1930.0]}
HSPAN = {"hfront": (60, 650), "hq": (660, 1150), "hside": (1150, 1690), "hqb": (1700, 2180), "hback": (2180, 2700)}
H_EARS = (1080, 1230)         # the ears' rows: in the front and back views the head's outline there is the ears'
H_NECK = HR(1190)             # below this the sheet's neck spreads into its cut-off shoulders: not compared


def hrow(z):
    return H_CHIN + (Z_CHIN - np.asarray(z, dtype=float)) / HS


def hz(row):
    return Z_CHIN + (H_CHIN - np.asarray(row, dtype=float)) * HS


def hcam(view):
    a = math.radians(HVIEW[view][0])
    return np.array((-math.sin(a), -math.cos(a), 0.0)), np.array((math.cos(a), -math.sin(a), 0.0))


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


def unline(pix, ground_cols=(95, 135), line_cols=(95, 135)):
    """The sheet's guide lines painted out (rows where the margin left of the figures is unlike the ground)."""
    g0, g1 = ground_cols
    l0, l1 = line_cols
    ground = np.median(pix[:, g0:g1].reshape(-1, 3), axis=0)
    rows = set(np.where(np.abs(pix[:, l0:l1] - ground).max(-1).mean(axis=1) > 0.04)[0].tolist())
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


def colour_mask(pix, thr=0.055):
    """The figure: what differs from the ground (the median of each row's two edges) by more than thr, specks out,
    holes filled. (The captain's flood by small colour steps leaked through this sheet's soft painted edges.)"""
    h, w = pix.shape[:2]
    edge = np.concatenate([pix[:, 2:60], pix[:, w - 60:w - 2]], 1)
    ground = np.median(edge, axis=1)
    fig = np.abs(pix - ground[:, None, :]).max(-1) > thr
    k = np.zeros(fig.shape, np.int32)
    for dy in range(-2, 3):
        for dx in range(-2, 3):
            k += np.roll(np.roll(fig, dy, 0), dx, 1)
    fig = k >= 13
    free = ~fig
    hok = free[:, 1:] & free[:, :-1]
    vok = free[1:] & free[:-1]
    brk = np.ones((h, w), bool)
    brk[:, 1:] = ~hok
    hid = np.cumsum(brk.ravel()) - 1
    brk = np.ones((w, h), bool)
    brk[:, 1:] = ~vok.T
    vid = (np.cumsum(brk.ravel()) - 1).reshape(w, h).T.ravel()
    reach = np.zeros((h, w), bool)
    reach[0] = reach[-1] = True
    reach[:, 0] = reach[:, -1] = True
    reach = (reach & free).ravel()
    fr = free.ravel()
    for _ in range(400):
        before = reach.sum()
        reach = (np.bincount(hid, weights=reach, minlength=hid[-1] + 1) > 0)[hid] & fr
        reach = (np.bincount(vid, weights=reach, minlength=vid.max() + 1) > 0)[vid] & fr
        if reach.sum() == before:
            break
    return ~reach.reshape(h, w)


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


def smooth01(a, b, x):
    t = np.clip((np.asarray(x, float) - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


class Sheets:
    def __init__(self):
        self.body_pix = load_picture(SHEET)
        self.body_mask = colour_mask(unline(self.body_pix, *BODY_UNLINE))
        self.head_pix = load_picture(HEAD_SHEET)
        self.head_mask = colour_mask(unline(self.head_pix, *HEAD_UNLINE))
        self.head_mask[:H_BALD[0]] = False
        self.head_target = self._head_target()
        self.hand_pix = load_picture(HAND_SHEET)
        self.hand_mask = colour_mask(unline(self.hand_pix, (15, 60), (90, 130)))
        self.body_target = self._body_target()
        self._fit_angled()

    def _head_target(self):
        """The bald head's outline without the ears in the front and back views (their outline there is the ears'):
        across the ears' rows the head's half width runs smoothly between the rows above and below them, with the
        cheekbones' slight fullness."""
        t = self.head_mask.copy()
        a_, b_ = H_EARS[0] - 4, H_EARS[1] + 6
        for view in ("hfront", "hback"):
            c0, c1 = HSPAN[view]
            mid = HVIEW[view][1]
            ra = run_near(t, a_, mid, c0, c1)
            rb = run_near(t, b_, mid, c0, c1)
            ha, hb = (ra[1] - ra[0]) / 2.0, (rb[1] - rb[0]) / 2.0
            for r in range(a_ + 1, b_):
                u = (r - a_) / (b_ - a_)
                half = ha + (hb - ha) * u + 4.0 * math.sin(math.pi * u)
                t[r, c0:c1] = False
                t[r, int(round(mid - half)):int(round(mid + half)) + 1] = True
        return t

    def _fit_angled(self):
        """The 3/4 views' angle and middle column: those of a rough head (an egg of the front, side and back views'
        measures) whose outline best covers each view's (found once; the model is then checked against them)."""
        rows = np.arange(HR(730), H_NECK, 6)
        egg = []
        for r in rows:
            fr = run_near(self.head_target, r, HVIEW["hfront"][1], *HSPAN["hfront"])
            sr = run_near(self.head_mask, r, HVIEW["hside"][1], *HSPAN["hside"])
            if not fr or not sr:
                continue
            hw = (fr[1] - fr[0]) / 2.0 * HS
            yf, yb = (HVIEW["hside"][1] - sr[1]) * HS, (HVIEW["hside"][1] - sr[0]) * HS
            for k in range(32):
                th = math.tau * k / 32
                egg.append((hw * math.sin(th), (yf + yb) / 2 - (yb - yf) / 2 * math.cos(th), float(hz(r))))
        E = np.array(egg)
        for view, guesses in (("hq", np.arange(25.0, 70.0, 2.5)), ("hqb", np.arange(200.0, 250.0, 2.5))):
            c0, c1 = HSPAN[view]
            best = None
            for a in guesses:
                HVIEW[view][0] = float(a)
                d, r = hcam(view)
                u = E @ r / HS
                # (per row: the egg's extent against the sheet's)
                err = 0.0
                shift = []
                for rr in rows[::2]:
                    sel = np.abs(E[:, 2] - float(hz(rr))) < 1e-6
                    run = run_near(self.head_mask, rr, (c0 + c1) / 2, c0, c1)
                    if not sel.any() or not run:
                        continue
                    lo, hi = u[sel].min(), u[sel].max()
                    shift.append(((run[0] - lo) + (run[1] - hi)) / 2.0)
                    err += abs((run[1] - run[0]) - (hi - lo))
                if best is None or err < best[0]:
                    best = (err, float(a), float(np.median(shift)))
            HVIEW[view][0], HVIEW[view][1] = best[1], best[2]
            print("BOY head sheet %s: azimuth %.1f degrees, middle column %.1f (width error %.0f px)" % (view, best[1], best[2], best[0]))

    def _body_target(self):
        """The base body's outline as the fitting's target: the shorts drawn in by BOXER_EASE, and from the crotch
        down to their hem his legs as they are just below it."""
        t = self.body_mask.copy()
        for view in ("front", "back"):
            c0, c1 = SPAN[view]
            mid = MID[view]
            for r in range(BOXERS[0], CROTCH + 1):
                run = run_near(t, r, mid, c0, c1)
                if run and run[0] < mid < run[1]:
                    a, b = run
                    e = int(round(BOXER_EASE * float(smooth01(BOXERS[0], BOXERS[0] + 30, r))))
                    if e > 0:
                        t[r, a:a + e] = False
                        t[r, b - e + 1:b + 1] = False
            legs = t[BOXERS[1] + 6, c0:c1].copy()
            for r in range(CROTCH + 1, BOXERS[1] + 6):
                t[r, c0:c1] = legs
        c0, c1 = SPAN["side"]
        # (fifth pass) the side view's back where the near arm hides it: SIDE_BACK, and nothing behind it
        sr = [a for a, _ in SIDE_BACK]
        sc = [b for _, b in SIDE_BACK]
        for r in range(sr[0], sr[-1] + 1):
            run = run_near(t, r, MID["side"], c0, c1)
            if run:
                back = int(round(float(np.interp(r, sr, sc))))
                t[r, c0:back] = False
                t[r, back:run[1] + 1] = True
        for r in range(BOXERS[0], BOXERS[1] + 6):
            run = run_near(t, r, MID["side"], c0, c1)
            if run:
                a, b = run
                e = int(round(BOXER_EASE * float(smooth01(BOXERS[0], BOXERS[0] + 30, r))))
                if e > 0:
                    t[r, a:a + e] = False
                    t[r, b - e + 1:b + 1] = False
        return t


# ------------------------------------------------------------------------------------------------------------------
# Views: where a point of him falls in a sheet's picture (continuous pixel coordinates: column, row) and how deep.
# "face" is the painted-face trial's close-up.
# ------------------------------------------------------------------------------------------------------------------

def project(view, P):
    """(N,3) model points -> (N,2) picture coordinates and (N,) depth (smaller is nearer the painter)."""
    P = np.asarray(P, dtype=float)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    row = body_row(z) + 0.5
    if view in HVIEW:
        d, r = hcam(view)
        return np.stack([HVIEW[view][1] + (P @ r) / HS + 0.5, hrow(z) + 0.5], 1), -(P @ d)
    if view == "face":
        return np.stack([FACE_AT[0] + x / S * FACE_K + 0.5, FACE_AT[1] + (body_row(z) - FACE_REF_ROW) * FACE_K + 0.5], 1), y
    if view == "front":
        return np.stack([MID["front"] + x / S + 0.5, row], 1), y
    if view == "back":
        return np.stack([MID["back"] - x / S + 0.5, row], 1), -y
    return np.stack([MID["side"] - y / S + 0.5, row], 1), x                  # his right side


def screen_dir(view, N):
    """Directions in the picture (column, row) of model directions, and how much they face the painter."""
    N = np.asarray(N, dtype=float)
    if view in HVIEW:
        d, r = hcam(view)
        return np.stack([N @ r, -N[:, 2]], 1), N @ d
    if view in ("front", "face"):
        return np.stack([N[:, 0], -N[:, 2]], 1), -N[:, 1]
    if view == "back":
        return np.stack([-N[:, 0], -N[:, 2]], 1), N[:, 1]
    return np.stack([-N[:, 1], -N[:, 2]], 1), -N[:, 0]


def world_dir(view, d2):
    """A direction in the picture as a model direction (in the picture's plane)."""
    z = np.zeros(len(d2))
    if view in HVIEW:
        d, r = hcam(view)
        return r[None, :] * d2[:, :1] + np.stack([z, z, -d2[:, 1]], 1)
    if view in ("front", "face"):
        return np.stack([d2[:, 0], z, -d2[:, 1]], 1)
    if view == "back":
        return np.stack([-d2[:, 0], z, -d2[:, 1]], 1)
    return np.stack([z, -d2[:, 0], -d2[:, 1]], 1)


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
# A mesh under construction
# ------------------------------------------------------------------------------------------------------------------

class Mesh:
    def __init__(self):
        self.P = []
        self.part = []
        self.faces = []
        self.fpart = []
        self.tag = {}
        self.want = {}
        self.cell = {}

    def add(self, p, part):
        self.P.append(np.array(p, dtype=float))
        self.part.append(part)
        return len(self.P) - 1

    def face(self, idx, part, want=None):
        self.faces.append(list(idx))
        self.fpart.append(part)
        if want is not None:
            self.want[len(self.faces) - 1] = want

    def bridge(self, a, b, part, closed=True):
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


# ------------------------------------------------------------------------------------------------------------------
# The body, measured off the sheet
# ------------------------------------------------------------------------------------------------------------------

TORSO_N = 16
LIMB_N = 10
# The torso's rings (sheet rows, from the crotch up to the neck's base) and which hold the arm's hole.
TORSO_ROWS_OLD = [1000, 945, 885, 855, 825, 800, 775, 750, 720, 690, 660, 630, 600, 560, 520, 480, 448, 430, 415]
# (sixth pass, the budget: 975 and 915, under the shorts, dropped)
TORSO_ROWS = [BR(r) for r in TORSO_ROWS_OLD]
_H0 = TORSO_ROWS_OLD.index(560)
HOLE = (_H0, _H0 + 1, _H0 + 2, _H0 + 3)
HOLE_COLS = (3, 4, 5)
# The torso's half width where the arms hide it in the front view (metres), by row (fifth pass, the new sheet: the
# chest 0.113 where the arm leaves it at row 515, the narrow shoulders' slope above).
TORSO_UNDER_ARMS = {BR(600): 0.112, BR(560): 0.114, BR(520): 0.117, BR(480): 0.119, BR(448): 0.115}
# Shoulder joint row, elbow row (the back view's elbow), wrist row (the narrowest, above the hand).
# (third round: the shoulder joint and the arm's root raised and widened, so the root's top is the shoulder's round cap
# under the trapezius; at row 510 a square corner stood between the torso's top rings and the arm)
# (fifth pass, the new sheet: shoulder 440, elbow 645, wrist 795; the arm leaves his side at row 520)
SHOULDER_ROW, ELBOW_ROW, WRIST_ROW = 440, 645, 795
ARM_FROM_ROW = 528
ELBOW_RING = float(arg("--elbow-ring", "0.02"))   # (ninth pass: from 0.03) the rings each side of the elbow
ARM_ROOT_R = 0.052
ARM_Y = (0.0, -0.02)
ARM_DEPTH = ((0.0, 1.05), (0.12, 1.0), (0.22, 0.9), (0.27, 0.86), (0.37, 0.95), (0.47, 1.12))
# The legs: rows of their rings (from the crotch down), the hip joint, the knee and the ankle.
LEG_ROWS = [BR(r) for r in (1020, 1045, 1092, 1110, 1128, 1190, 1230, 1270, 1345)]   # (sixth pass: 1310 dropped, the budget; ninth: 1075 and 1150 moved in to 1092 and 1128, rings close by each side of the knee so it bends round)
KNEE_ROW = LEG_ROWS[3]
HIP_ROW, ANKLE_ROW = BR(940), BR(1352)
HIP_X = 0.072
LEG_X = 0.073                     # where to look for the leg in each row (from the middle)
FOOT_YAW = math.radians(14.0)     # toes out
TOE_REACH = 1.0
# The foot's rings below the ankle: height, reach forward of the ankle, back, and to each side (the side view: heel
# at column 1365, toes' end at 1627, the ankle's middle 1428; the sheet draws him big feet, 0.29 m long).
FOOT_RINGS = ((0.096, 0.052, 0.05, 0.04), (0.066, 0.118, 0.056, 0.045), (0.036, 0.206, 0.079, 0.051),
              (0.013, 0.214, 0.077, 0.05), (0.0, 0.2, 0.064, 0.043))
# (fifth pass: the new sheet's foot is 0.23 m long, heel to toe, and slimmer)
FOOT_RINGS = tuple((z * 0.85, f * 0.8, b * 0.8, h * 0.78) for z, f, b, h in FOOT_RINGS)
# (fourth pass, the critic: "boot-like lumps ... no arch ... the heel blends straight up into the leg"): the heel
# stands 1 cm further back below the Achilles' line (above), the toes' end squarer (FOOT_TOE_P, from 0.55), the inner
# sole lifted into an arch (FOOT_ARCH metres at the ground, half that a ring up), ankle bones (ANKLE_BONE)
FOOT_TOE_P = 0.35
FOOT_ARCH = 0.008
ANKLE_BONE = 0.005


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
        yf = -(run[1] + 1 - MID["side"]) * S
        yb = -(run[0] - MID["side"]) * S
        rings.append((float(body_z(r)), a, yf, yb))
    return rings


def arm_axis(sh):
    """The drawn arm's axis in the front view (both arms, front and back views): shoulder, elbow, wrist (metres)."""
    m = sh.body_mask
    pts = []
    for r in range(ARM_FROM_ROW, WRIST_ROW, 5):
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
            cs.append(abs(centre - mid) * S)
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
    """Half the arm's width across it at a point of its axis (both arms, front and back views)."""
    m = sh.body_mask
    cosang = abs(D.z) / math.hypot(D.x, D.z)
    r = float(body_row(C.z))
    halves = []
    for view in ("front", "back"):
        c0, c1 = SPAN[view]
        mid = MID[view]
        for sign in (1, -1):
            col = mid + sign * C.x / S if view == "front" else mid - sign * C.x / S
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
    return float(np.interp(s, [a for a, _ in ARM_DEPTH], [b for _, b in ARM_DEPTH]))


def leg_ring(sh, r):
    """The left leg at a row: centre x, half width, front y, back y."""
    t = sh.body_target
    xs = []
    for view in ("front", "back"):
        c0, c1 = SPAN[view]
        mid = MID[view]
        for sign in (1, -1):
            col = mid + sign * LEG_X / S if view == "front" else mid - sign * LEG_X / S
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
    M = Mesh()
    rings = measure_torso(sh)
    T = []
    for i, (z, a, yf, yb) in enumerate(rings):
        cy = (yf + yb) / 2.0
        d = (yb - yf) / 2.0
        # (fourth round: rounder rings, a boy's round ribcage; at 0.74 to 0.8 the torso was a box with a flat front
        # and corners down its sides, and the forms on it did not read)
        p = 0.86 if TORSO_ROWS[i] > 620 else 0.9
        pts = ring_points(0.0, cy, z, a, d, d, TORSO_N, p)
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
    crotch = M.add((0.0, (yf0 + yb0) / 2.0 + 0.01, z0 - 0.012), "torso")
    M.tag["crotch"] = [crotch]
    joints = {}
    shoulder, elbow, wrist = arm_axis(sh)
    joints.update(shoulder_l=shoulder, elbow_l=elbow, wrist_l=wrist)
    print("BOY arm: shoulder %s elbow %s wrist %s" % (tuple(round(v, 3) for v in shoulder), tuple(round(v, 3) for v in elbow), tuple(round(v, 3) for v in wrist)))
    for side in (1, -1):
        arm(M, sh, T, side, shoulder, elbow, wrist, joints)
        leg(M, sh, T, rings, crotch, side, joints)
    return M, T, joints


def mirror_x(p, side):
    return np.array((p[0] * side, p[1], p[2]))


def col_of(k, side):
    return k if side > 0 else (TORSO_N - k) % TORSO_N


def arm(M, sh, T, side, J, E, W, joints):
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
    centre = J + N * 0.025
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
    stations = [0.03, 0.07, 0.115, 0.16, Lu - ELBOW_RING, Lu, Lu + ELBOW_RING, Lu + 0.08, Lu + 0.13, Lu + Lf - 0.03, Lu + Lf]
    prev = hole
    rings = [hole]
    for s in stations:
        if s <= Lu:
            C = J + Du * s
            D = Du if s < Lu - 0.04 else (Du + Df).normalized()
        else:
            C = E + Df * (s - Lu)
            D = Df if s > Lu + 0.04 else (Du + Df).normalized()
        A = (X - D * D.x).normalized()
        a = arm_width(sh, C, D)
        if s > Lu + Lf - 0.045:
            a = min(a, 0.034 if s < Lu + Lf - 0.01 else 0.03)
        b = a * depth_ratio(s)
        dl = math.exp(-((s - 0.05) / 0.045) ** 2)
        a *= 1.0 + 0.22 * dl
        b *= 1.0 + 0.16 * dl
        C = C + A * (0.008 * dl) + Vector((0, 0, 0.008 * dl))
        ring = []
        for j in range(LIMB_N):
            ph = math.tau * j / LIMB_N
            ring.append(M.add(mirror_x(C + A * (a * math.cos(ph)) + F * (b * math.sin(ph)), side), part))
        M.bridge(prev, ring, part) if side > 0 else M.bridge(ring, prev, part)
        rings.append(ring)
        prev = ring
    M.tag["arm_rings" + sfx] = rings
    M.tag["arm_stations" + sfx] = [0.0] + stations
    joints["arm_frame"] = (Du, Df)
    hand(M, prev, side, W, Df, joints)


# The hand (second pass), measured off tools/art_src/concept_boy_hands.jpg (his left hand: the back view, fingers to
# the right, 670 pixels wrist to the middle fingertip; the palm view agrees within about 10%) at the body sheet's
# size (about 0.175 m): a thin wrist, a slim wedge palm 0.082 m to the knuckles and 0.078 across them, long fingers
# of different lengths (the middle 0.09, index and ring 0.082, little 0.06) in three segments (0.44, 0.31, 0.25),
# a thumb of 0.07 from the side of the palm. Twilight Princess's way of building it (the captain's eighth round):
# four-sided finger sections with loops only at the joints, a blunt box end; about 240 triangles a hand.
# name, root quad, length, half-width, spread in the open hand of the back view (degrees toward the little finger)
FINGERS_SPEC = (("index", 0, 0.078, 0.0084, -10.0), ("middle", 1, 0.088, 0.009, -2.0),
                ("ring", 2, 0.079, 0.0082, 4.0), ("little", 3, 0.056, 0.0073, 15.0))
FINGER_SEGS = (0.44, 0.31, 0.25)
# His rest pose: the body sheet's hanging hands, relaxed: fingers gently curled and closer together, the thumb in.
# The open pose ("open") is the hands sheet's back and palm views, for checking the outline.
HAND_POSES = {"rest": {"curl": (0.3, 0.42, 0.32), "spread": 0.45, "thumb_curl": 0.12, "thumb_open": 0.0},
              "open": {"curl": (0.04, 0.06, 0.04), "spread": 1.0, "thumb_curl": 0.08, "thumb_open": 1.0}}
HAND_POSE = dict(HAND_POSES["rest"])
# (second pass, after the first outline check: the sheet's palm is broader, its knuckles 0.092 across with the
# fingers spaced apart, the thumb longer and set lower)
PALM = {"wrist": (0.012, 0.032, 0.019), "heel": (0.032, 0.043, 0.017), "knuckles": (0.08, 0.046, 0.0135)}
THUMB = {"length": 0.088, "base": (0.0135, 0.0112), "radii": (0.0118, 0.0108, 0.0098), "end": (0.0085, 0.0072)}


def hand(M, wrist_ring, side, W, L, joints):
    """A hand from the wrist ring: a boxy wedge palm of three rings (wrist, heel, knuckles with a ridge), four
    fingers grown out of the palm's end quads in four-sided sections, a thumb out of the palm's side face. Posed by
    HAND_POSE. The back faces out and a little forward (38 degrees round from straight out)."""
    first = len(M.P)
    sfx = "_l" if side > 0 else "_r"
    part = "hand" + sfx
    X = Vector((1, 0, 0))
    F = Vector((0, -1, 0))
    A = (X - L * L.x).normalized()
    tw = math.radians(38.0)
    Tb = A * math.cos(tw) + F * math.sin(tw)
    Wd = -A * math.sin(tw) + F * math.cos(tw)
    back = [3, 2, 1, 0, 9]
    palm = [4, 5, 6, 7, 8]
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
    s0, s1, s2 = PALM["wrist"], PALM["heel"], PALM["knuckles"]
    # (the heel and wrist shifted toward the thumb: the sheet's palm is broad on the thumb's side, the ball of the
    # thumb swelling from near the wrist)
    r0 = ring_at(W + L * s0[0] + Wd * 0.003, s0[1], s0[2])
    r1 = ring_at(W + L * s1[0] + Wd * 0.008, s1[1], s1[2], palm_drop=(0.004, 0.0015, 0.0, 0.0015, 0.0035))
    knuck = W + L * s2[0]
    r3 = ring_at(knuck, s2[1], s2[2], back_lift=(0.001, 0.0025, 0.0025, 0.0025, 0.001))
    bridge(wrist_ring, r0)
    bridge(r0, r1)
    bridge(r1, r3)
    # (fourth check: the thumb grows from the side of the palm between the wrist and the heel, where its long first
    # bone starts in a real hand and where the hands sheet draws it; from mid palm it stood too far out toward the
    # fingers)
    thumb_root = [r0[3], r1[3], r1[4], r0[4]]
    target = sorted(thumb_root)
    for fi in range(len(M.faces) - 1, -1, -1):
        if sorted(M.faces[fi]) == target:
            del M.faces[fi]
            del M.fpart[fi]
            break
    M.tag["hand_rings" + sfx] = [wrist_ring, r0, r1, r3]

    def grow(name, root, frames, tip_at, pname):
        a0, step = frames[0]
        rings = [list(root)]
        for at, ac, bk, hw, ht in frames[1:]:
            ring = []
            for j in range(4):
                a = math.radians(a0 + step * j)
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

    curl = HAND_POSE["curl"]
    for name, i, length, hw, spread in FINGERS_SPEC:
        root = [r3[back[i]], r3[back[i + 1]], r3[palm[i + 1]], r3[palm[i]]]
        k0 = knuck + Wd * (across[i] + across[i + 1]) / 2.0 * s2[1]
        way = Matrix.Rotation(math.radians(spread * HAND_POSE["spread"]), 3, Tb) @ L.copy()
        ac, bk = Wd.copy(), Tb.copy()
        ac = Matrix.Rotation(math.radians(spread * HAND_POSE["spread"]), 3, Tb) @ ac
        frames = [(45.0, 90.0)]
        at = k0 + way * 0.006
        frames.append((at.copy(), ac.copy(), bk.copy(), hw * 1.04, hw * 0.95))          # the knuckle
        bones = [k0.copy()]
        for si, fr in enumerate(FINGER_SEGS):
            rot = Matrix.Rotation(-curl[si], 3, ac)
            way = rot @ way
            bk = rot @ bk
            at = at + way * (length * fr)
            bones.append(at.copy())
            if si < 2:
                # (a loop at each joint, a little fuller than the segment: the knuckles read)
                frames.append((at.copy(), ac.copy(), bk.copy(), hw * (0.98, 0.92)[si], hw * (0.9, 0.84)[si]))
        frames.append((at - way * 0.003, ac.copy(), bk.copy(), hw * 0.9, hw * 0.78))
        grow(name, root, frames, at + way * 0.0025 - bk * 0.0012, part + "_" + name)
        joints["%s%s" % (name, sfx)] = [Vector(mirror_x(b, side)) for b in bones]
    rootc = sum((Vector(mirror_x(M.P[v], side)) for v in thumb_root), Vector()) / 4.0
    # the thumb: in the open hand out at about 30 degrees from the hand's line, nearly in the palm's plane (the back
    # view); at rest in front of the palm, toward the fingers
    open_ = HAND_POSE["thumb_open"]
    # (third check: at rest the thumb hangs along the fingers under the palm, as the sheet's relaxed side view and
    # the body sheet draw it; open, it stands out lower and wider)
    w_rest = (L * 0.7 + Wd * 0.3 - Tb * 0.65).normalized()
    w_open = (L * 0.74 + Wd * 0.66 - Tb * 0.1).normalized()
    way = (w_rest * (1 - open_) + w_open * open_).normalized()
    U = (L - way * L.dot(way)).normalized()
    V = way.cross(U).normalized()
    if V.dot(Tb) < 0:
        V = -V
    frames = [(135.0, -90.0)]
    at = rootc + way * 0.012
    frames.append((at.copy(), U.copy(), V.copy(), THUMB["base"][0], THUMB["base"][1]))
    bones = [rootc.copy()]
    for si, (fr, rad) in enumerate(zip((0.42, 0.32, 0.26), THUMB["radii"])):
        rot = Matrix.Rotation(-HAND_POSE["thumb_curl"], 3, U.cross(way).normalized())
        way = rot @ way
        U = rot @ U
        V = rot @ V
        at = at + way * (THUMB["length"] * fr)
        bones.append(at.copy())
        if si < 2:
            frames.append((at.copy(), U.copy(), V.copy(), rad, rad * 0.86))
    frames.append((at - way * 0.0035, U.copy(), V.copy(), THUMB["end"][0], THUMB["end"][1]))
    grow("thumb", thumb_root, frames, at + way * 0.0045, part + "_thumb")
    joints["thumb%s" % sfx] = [Vector(mirror_x(b, side)) for b in bones]
    joints["thumb_back%s" % sfx] = np.array(mirror_x(V, side))
    joints["hand_frame%s" % sfx] = tuple(np.array(mirror_x(v, side)) for v in (Tb, Wd, L))
    joints["knuckles%s" % sfx] = Vector(mirror_x(knuck, side))
    M.tag["hand_points" + sfx] = (first, len(M.P))


def hand_alone(pose):
    """A left hand alone in a given pose, built by hand() on a wrist ring of its own at the origin, pointing down:
    the same points in the same order as the body's left hand (for its outline against the hands sheet, and to paint
    the body's hand from the sheet's open views). Gives (Mesh, joints, the index its hand points start at)."""
    global HAND_POSE
    keep = HAND_POSE
    HAND_POSE = dict(HAND_POSES[pose])
    Mt = Mesh()
    L = Vector((0.0, 0.0, -1.0))
    A, F = Vector((1, 0, 0)), Vector((0, -1, 0))
    ring = [Mt.add(A * (0.031 * math.cos(math.tau * j / LIMB_N)) + F * (0.022 * math.sin(math.tau * j / LIMB_N)), "arm_l")
            for j in range(LIMB_N)]
    jt = {}
    hand(Mt, ring, 1, Vector((0.0, 0.0, 0.0)), L, jt)
    HAND_POSE = keep
    return Mt, jt


def leg(M, sh, T, rings, crotch, side, joints):
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
    joints["knee" + sfx] = Vector(mirror_x((kc[0], kc[1] - 0.004, kc[2]), side))
    joints["ankle" + sfx] = Vector(mirror_x((ax, ay + 0.005, float(body_z(ANKLE_ROW))), side))
    fwd = Vector((math.sin(FOOT_YAW), -math.cos(FOOT_YAW), 0.0))
    lat = Vector((math.cos(FOOT_YAW), math.sin(FOOT_YAW), 0.0))
    foot_part = "foot" + sfx
    if FOOT:
        # (fifth pass) the base-mesh foot under the leg's last ring, its ankle ring drawn in to the leg's size
        Lf = FOOT["P"].copy()
        ring_l = FOOT["ring"]
        Pr = np.array([M.P[i] for i in prev])
        rad_leg = float(np.mean(np.linalg.norm((Pr - Pr.mean(0))[:, :2], axis=1)))
        cr = Lf[ring_l].mean(0)
        rad_foot = float(np.mean(np.linalg.norm((Lf[ring_l] - cr)[:, :2], axis=1)))
        kr = rad_leg / max(rad_foot, 1e-6)
        tz = smooth01(0.045, FOOT_RING_Z, Lf[:, 2])
        kk = 1.0 + (kr - 1.0) * tz
        Lf[:, 0] = cr[0] + (Lf[:, 0] - cr[0]) * kk
        Lf[:, 1] = cr[1] + (Lf[:, 1] - cr[1]) * kk
        base_i = len(M.P)
        A0 = np.array((ax, ay, 0.0))
        fw, lt = np.array(fwd[:]), np.array(lat[:])
        for q in Lf:
            M.add(mirror_x(A0 + fw * q[0] + lt * q[1] + np.array((0.0, 0.0, q[2])), side), foot_part)
        for f in FOOT["faces"]:
            ff = [base_i + v for v in f]
            M.face(ff if side > 0 else ff[::-1], foot_part)
        ring = [base_i + v for v in ring_l]
        PB = np.array([M.P[i] for i in ring])
        ctr = (Pr.mean(0) + PB.mean(0)) / 2.0
        zf = zip_rings(M, list(prev), ring, Pr, PB, ctr, np.array((1.0, 0.0, 0.0)), np.array((0.0, -1.0, 0.0)), foot_part)
        M.tag["foot_zip" + sfx] = zf
        M.tag["foot_points" + sfx] = (base_i, base_i + len(Lf))
        M.tag["leg_rings" + sfx] = allr
        joints["ball" + sfx] = Vector(mirror_x(A0 + fw * FOOT["ball"][0] + np.array((0, 0, FOOT["ball"][2])), side))
        joints["toe_tip" + sfx] = Vector(mirror_x(A0 + fw * FOOT["tip"][0] + np.array((0, 0, FOOT["tip"][2])), side))
        return
    for z, front, backr, half in FOOT_RINGS:
        ring = []
        for th in angles:
            al = th - FOOT_YAW
            cu, cv = math.cos(al), math.sin(al)
            if cu > 0:
                u = sgnpow(cu, FOOT_TOE_P if z < 0.05 else 0.55) * front * TOE_REACH
                v = sgnpow(cv, 0.8) * half * (1.0 + 0.18 * cu)
            else:
                u = cu * backr
                v = cv * half * (1.0 if cu > -0.2 else 0.88)
            q = Vector((ax, ay, z)) + fwd * u + lat * v
            if z < 0.02 and cv < -0.3 and -0.45 < cu < 0.6:
                q.z += FOOT_ARCH * (1.0 - z / 0.026) * math.sin(math.pi * (cu + 0.45) / 1.05)
            ring.append(M.add(mirror_x(q, side), foot_part))
        M.bridge(prev, ring, foot_part) if side > 0 else M.bridge(ring, prev, foot_part)
        prev = ring
        allr.append(ring)
    sole = M.add(mirror_x(Vector((ax, ay, 0.0)) + fwd * 0.048, side), foot_part)
    for j in range(LIMB_N):
        k = (j + 1) % LIMB_N
        M.face([prev[j], prev[k], sole] if side > 0 else [prev[k], prev[j], sole], foot_part)
    M.tag["leg_rings" + sfx] = allr
    joints["ball" + sfx] = Vector(mirror_x(Vector((ax, ay, 0.022)) + fwd * 0.108, side))
    joints["toe_tip" + sfx] = Vector(mirror_x(Vector((ax, ay, 0.018)) + fwd * 0.168, side))


# ------------------------------------------------------------------------------------------------------------------
# The head, measured off the head sheet's bald row (second pass): the half width of each ring from the front view
# (its outline with the ears taken out), its front and back from the side view; the nose lofted down the side
# view's profile; ears from the side view's ear and the front view's reach. Then refined, given its forms, and FITTED
# to the front, side and back views' outlines (fit_head), and checked against all five (head_silhouettes).
# ------------------------------------------------------------------------------------------------------------------

# The head's rings, from the neck up to just under the crown at H_CROWN: (the row of the ring's front, the row of its
# back). (Third round, the coordinator, from the captain: "The mandible is a SLANTED edge: from the jaw angle just
# below the ear lobe, down and forward to the chin ... an under-jaw surface turning back to the throat; the neck is a
# separate thin column emerging under and behind the jaw".) Level rings made the jaw a level shelf; the lower rings
# are tilted instead, the usual loops of a modelled head: their fronts run down the chin and under it to the throat
# while their backs stay up at the jaw's angles and the nape, so each ring's sides pass along the jaw's slanted edge
# and the under-jaw surface lies between them. Above the mouth they come level.
HEAD_RINGS = [(1200, 1176), (1186, 1136), (1172, 1100), (1152, 1084), (1130, 1072), (1108, 1062), (1094, 1056),
              (1082, 1050), (1070, 1044), (1040, 1040), (1022, 1022), (1004, 1004), (986, 986), (968, 968),
              (950, 950), (932, 932), (912, 912), (890, 890), (864, 864), (836, 836), (806, 806), (778, 778),
              (754, 754), (736, 736), (726, 726)]
HEAD_ROWS = [f for f, _ in HEAD_RINGS]
# How much each ring narrows toward its front, by its front's row: the V of his jaw into a pointed chin.
JAW_TAPER = ((1040, 0.0), (1070, 0.06), (1094, 0.14), (1130, 0.3), (1152, 0.42), (1172, 0.5), (1186, 0.0), (1200, 0.0))
# The ring's shape (superellipse power), by its front's row: rounder at the mouth, a narrower V to the chin.
RING_P = ((900, 1.0), (1040, 1.0), (1100, 1.06), (1172, 1.1), (1186, 0.95), (1200, 0.92))
# How far round toward its back a tilted ring rises to its back's height (0 front, 1 back): its sides are at the
# jaw's angle.
TILT_EASE = 0.45
JAW_EDGE = (0.0826, -0.024, 1773)   # the jaw's angle (out from his middle, its depth), the chin's side-view column
# Rows where the side view's front is the nose: the face's front there is the plane behind it.
FACE_PLANE = (950, 1046)
FACE_PLANE_IN = 0.007
# The nose: rows, and its full width in the front view (head pixels); its profile is the side view's outline.
NOSE_ROWS = ((950, 28), (966, 36), (982, 44), (998, 56), (1012, 70), (1026, 76), (1038, 70), (1046, 56))
NOSE_WINGS = ((1012, 0.0), (1026, 0.12), (1038, 0.24), (1046, 0.2))
NOSE_IN = 0.008               # its back, inside the face
EAR_ROWS = (1080, 1218)        # the ear's top and bottom (the lobe's bottom: the front view's 1040 to 1045)
EAR_COLS = (1382, 1296)       # its front and back in the side view
EAR_OUT = 0.036               # how far its rim stands out (the front view: its tip 0.123 m from his middle)


def side_run(sh, r):
    return run_near(sh.head_mask, r, HVIEW["hside"][1], *HSPAN["hside"])


def side_y(col):
    return (HVIEW["hside"][1] - col) * HS


def head_rings_measured(sh):
    """Each ring: (z of its front, half width, front y, back y, taper, z of its back, shape power). The front from the
    side view's outline at the front's row (the nose's rows: the face's plane behind it), the back from the side view
    at the back's row, the half width from the front view (ears out) at the row of its sides."""
    out = []
    pa, pb = side_run(sh, FACE_PLANE[0]), side_run(sh, FACE_PLANE[1] + 4)
    for rf, rb in HEAD_RINGS:
        rs = int(round(rf + (rb - rf) * 0.7))
        fr = run_near(sh.head_target, rs, HVIEW["hfront"][1], *HSPAN["hfront"])
        hw = (fr[1] + 1 - fr[0]) / 2.0 * HS
        yf = side_y(side_run(sh, rf)[1] + 1)
        yb = side_y(side_run(sh, rb)[0])
        if FACE_PLANE[0] <= rf <= FACE_PLANE[1]:
            t = (rf - FACE_PLANE[0]) / (FACE_PLANE[1] - FACE_PLANE[0])
            yf = side_y(pa[1] + 1) * (1 - t) + side_y(pb[1] + 1) * t + FACE_PLANE_IN * math.sin(math.pi * t) + 0.002
        taper = float(np.interp(rf, [a for a, _ in JAW_TAPER], [b for _, b in JAW_TAPER]))
        p = float(np.interp(rf, [a for a, _ in RING_P], [b for _, b in RING_P]))
        out.append([float(hz(rf)), hw, yf, yb, taper, float(hz(rb)), p])
    # The profile's small forms (the lips, the groove under them, the brow) are the face's middle only: put into the
    # whole ring they ran across his cheeks as ridges. The rings' fronts are the profile smoothed, the lips' rows
    # straight between above and below them; the forms go in by sculpt_head.
    yf = np.array([o[2] for o in out])
    hwv = np.array([o[1] for o in out])
    ybv = np.array([o[3] for o in out])
    sm, smw, smb = yf.copy(), hwv.copy(), ybv.copy()
    for _ in range(2):
        a_, b_, c_ = sm.copy(), smw.copy(), smb.copy()
        for i in range(1, len(out) - 1):
            if 880 < HEAD_ROWS[i] < 1120:
                sm[i] = 0.25 * a_[i - 1] + 0.5 * a_[i] + 0.25 * a_[i + 1]
            smw[i] = 0.25 * b_[i - 1] + 0.5 * b_[i] + 0.25 * b_[i + 1]
            smb[i] = 0.25 * c_[i - 1] + 0.5 * c_[i] + 0.25 * c_[i + 1]
    j0, j1 = HEAD_ROWS.index(1040), HEAD_ROWS.index(1130)
    for i in range(j1 + 1, j0):
        t = (HEAD_ROWS[j0] - HEAD_ROWS[i]) / float(HEAD_ROWS[j0] - HEAD_ROWS[j1])
        sm[i] = yf[j0] * (1 - t) + yf[j1] * t
    for o, w_, f_, b_ in zip(out, smw, sm, smb):
        o[1], o[2], o[3] = float(w_), float(f_), float(b_)
    return [tuple(o) for o in out]


def build_head(M, sh, top_ring):
    rings = head_rings_measured(sh)
    prev = top_ring
    H = []
    for i, (zf, hw, yf, yb, taper, zb, p) in enumerate(rings):
        cy, d = (yf + yb) / 2.0, (yb - yf) / 2.0
        pts = ring_points(0.0, cy, zf, hw, d, d, TORSO_N, p)
        if taper:
            pts = [(x * (1.0 - taper * max(0.0, (cy - y) / d)), y, zz) for x, y, zz in pts]
        if abs(zb - zf) > 1e-6:
            # (tilted: each point rises from the front's height toward the back's as it goes round)
            pts = [(x, y, zf + (zb - zf) * min(max((y - yf) / (yb - yf), 0.0), 1.0) ** TILT_EASE) for x, y, _ in pts]
        ring = [M.add(q, "head") for q in pts]
        for k in range(TORSO_N):
            j = (k + 1) % TORSO_N
            M.face([prev[k], prev[j], ring[j], ring[k]], "head" if i else "neck")
            M.cell[len(M.faces) - 1] = ("head", i - 1, k)
        prev = ring
        H.append(ring)
    top = M.add((0.0, rings[-1][2] * 0.5 + rings[-1][3] * 0.5, float(hz(H_CROWN))), "head")
    for k in range(TORSO_N):
        j = (k + 1) % TORSO_N
        M.face([prev[k], prev[j], top], "head")
        M.cell[len(M.faces) - 1] = ("head", len(rings) - 1, k)
    M.tag["head_rings"] = H
    nose(M, sh, rings)
    for side in (1, -1):
        ear(M, rings, side)
    return rings


def face_front_at(rings, z):
    zs = [r[0] for r in rings]
    ys = [r[2] for r in rings]
    return float(np.interp(z, zs, ys))


def nose(M, sh, rings):
    """The nose lofted down the side view's profile (its outline there), as wide as the front view paints it."""
    loops = []
    n = 10
    for r, width in NOSE_ROWS:
        tip = side_y(side_run(sh, r)[1] + 1)
        z = float(hz(r))
        base = face_front_at(rings, z) + NOSE_IN
        half = width / 2.0 * HS
        wings = float(np.interp(r, [a for a, _ in NOSE_WINGS], [w for _, w in NOSE_WINGS]))
        cy, d = (tip + base) / 2.0, max((base - tip) / 2.0, 0.003)
        pts = ring_points(0.0, cy, z, half, d, d, n, 1.0)
        pts = [(x * (1.0 + wings * float(np.clip((y - cy) / d + 0.3, 0.0, 1.0))), y, zz) for x, y, zz in pts]
        loops.append([M.add(q, "nose") for q in pts])
    for a, b in zip(loops, loops[1:]):
        M.bridge(a, b, "nose")
    last = loops[-1]
    c = M.add((0.0, float(np.mean([M.P[i][1] for i in last])), M.P[last[0]][2] - 0.003), "nose")
    for j in range(n):
        M.face([last[j], last[(j + 1) % n], c], "nose")
    first = loops[0]
    c = M.add((0.0, float(np.mean([M.P[i][1] for i in first])) + 0.004, M.P[first[0]][2] + 0.005), "nose")
    for j in range(n):
        M.face([first[(j + 1) % n], first[j], c], "nose")


# An ear's outline (b: back from its front edge, v: up), and how far each point stands out (0..1): the helix round
# the top and back, the lobe at the bottom (a boy's ears, a bit big for his head, as the sheet draws them).
# (the coordinator: "attached along their front edge, lying back against the head": the front of the rim, by the
# face, sits nearly on the head; only the back of the helix stands out)
EAR_RIM = ((0.22, 1.0, 0.42), (0.55, 0.97, 0.85), (0.86, 0.8, 1.0), (0.98, 0.52, 0.95), (0.86, 0.24, 0.8),
           (0.6, 0.04, 0.6), (0.36, -0.03, 0.42), (0.14, 0.08, 0.18), (0.02, 0.34, 0.05), (0.04, 0.66, 0.1))


def ear(M, rings, side):
    """An ear: a rim standing out from the head, rolled over (the helix), a hollow bowl inside it, a back wall."""
    part = "ear_l" if side > 0 else "ear_r"
    zt, zb = float(hz(EAR_ROWS[0])), float(hz(EAR_ROWS[1]))
    y0, y1 = side_y(EAR_COLS[0]), side_y(EAR_COLS[1])
    zs = [r[0] for r in rings]
    zc = (zt + zb) / 2.0
    hw = float(np.interp(zc, zs, [r[1] for r in rings])) * 0.95
    hgt, wid = zt - zb, y1 - y0
    tilt = math.radians(12.0)
    rim, bowl, wall = [], [], []
    for b, v, out in EAR_RIM:
        yy = y0 + b * wid + (v - 0.5) * hgt * math.sin(tilt)
        zz = zb + v * hgt
        x = hw - 0.004 + EAR_OUT * out
        rim.append(M.add(mirror_x((x, yy, zz), side), part))
        bc = (0.42, 0.5)
        yb_ = y0 + (bc[0] + (b - bc[0]) * 0.55) * wid + (v - 0.5) * hgt * math.sin(tilt) * 0.55
        zb_ = zb + (bc[1] + (v - bc[1]) * 0.55) * hgt
        bowl.append(M.add(mirror_x((hw - 0.004 + EAR_OUT * out * 0.4, yb_, zb_), side), part))
        wall.append(M.add(mirror_x((hw - 0.012, y0 + b * wid * 0.85, zz), side), part))
    centre = M.add(mirror_x((hw - 0.002, y0 + 0.4 * wid, zb + 0.45 * hgt), side), part)
    n = len(EAR_RIM)
    out = np.array((side, 0.0, 0.0))
    mid_ = np.array(M.P[centre])

    def away(c, mid_=mid_, side=side):
        d = np.array(c) - mid_
        d[0] = 0.0
        return d + np.array((side * 0.15, 0.0, 0.0)) * np.linalg.norm(d)
    roll = []
    for r_, b_ in zip(rim, bowl):
        q = np.array(M.P[r_]) * 0.74 + np.array(M.P[b_]) * 0.26
        q[0] += side * 0.004
        roll.append(M.add(q, part))
    for j in range(n):
        k = (j + 1) % n
        M.face([rim[j], rim[k], roll[k], roll[j]], part, out)
        M.face([roll[j], roll[k], bowl[k], bowl[j]], part, out)
        M.face([bowl[j], bowl[k], centre], part, out)
        M.face([rim[k], rim[j], wall[j], wall[k]], part, away)


# ------------------------------------------------------------------------------------------------------------------
# THIRD PASS: the head (with its ears) and the hands from Blender Studio's Human Base Meshes v1.4.1 (CC0), fitted to
# his sheets, as tools/FIGURE_HEADS.md describes (the user: "The heads and hands need a lot of work on all three- make
# sure you are matching pose silhouettes aggressively"). The lofted head and hand above are retired (kept, unused).
# The bundle stays outside the repo; its meshes are appended by this script and never changed.
# ------------------------------------------------------------------------------------------------------------------

BUNDLE = os.path.join(r"C:\Projects\reference\human-base-meshes\bundle\human-base-meshes-bundle-v1.4.1",
                      "human_base_meshes_bundle.blend")
HEAD_BASE = "Head - Generic Topology"
HAND_BASE = "Hand - Stylized"
# The shape key mix: the realistic kid, a little of the anime kid (bigger eyes, smaller nose and jaw)
HEAD_MIX = {"Real_Kid": 1.0, "Toon_Anime_Kid": float(arg("--anime", "0.2"))}
ANIME_EYES = float(arg("--anime-eyes", "0.6"))
# The base head's own landmark points (its vertex numbers, the same in every shape key): the middle line's chin,
# lips, nose and brow, the top of the skull, and the ring round the left eye.
HB = {"chin": 285, "lip_low": 276, "mouth": 286, "lip_up": 279, "nose_base": 278, "nose": 288, "bridge": 274,
      "brow": 281, "crown": 291}
HB_EYE = tuple(range(57, 67))
HB_MOUTH_L, HB_JAW_L = 125, 106   # the base's left mouth corner and jaw angle (picked by their place on the Real_Kid shape)
# Heights on the bald row (head-sheet rows) the base's landmarks are moved to, before the outlines are fitted.
# (seventh pass: the chin's bottom measured again off the bald front and side views at twice size: row 1318 to 1322,
# not 1305; the model's chin sat 1.1 cm high and its under-jaw ran down the throat as a ramp)
CHIN_ROW = float(arg("--chin-row", "1318"))
HB_ROWS = (("chin", CHIN_ROW), ("mouth", 1223.0), ("nose_base", 1195.0), ("nose", 1170.0), ("eye", 1103.0),
           ("brow", 1035.0), ("crown", H_CROWN))
# The hole cut in the base head's closed underside for the neck: faces whose middles lie in this ellipse (base
# coordinates: y of its middle, half width, half depth). 30 quads; its edge is a ring of 22 points from just behind
# the chin (where the sheet's throat meets the jaw) to the skull's base at his back. (A smaller hole of 16 points, as
# many as the torso's top ring, started 11 cm behind the chin: the under-jaw came out as long as a shelf.)
NECK_HOLE = (-0.040, 0.045, 0.060)
NECK_RINGS = (0.25, 0.5, 0.75)   # (sixth pass, the budget: three rings, from four)
if "--old-head" not in ARGS:
    NECK_RINGS = (0.33, 0.67)    # (eleventh pass, the budget: the subdivided head's hole is a ring of 44, so two rings)
NECK_FULL = float(arg("--neck-full", "1.0"))    # (seventh pass: from 1.08; the neck is sized to the sheet after)
NECK_THIN = float(arg("--neck-thin", "1.0"))
HEAD_UV_M = 0.42             # metres a unit of the base head's UV map (sizes its island beside the others)


def load_base(name):
    """An object of the bundle appended into this file (the bundle itself is only read): its points (world, metres),
    faces, each face's UVs, and its shape keys' points. The appended object is removed again."""
    with bpy.data.libraries.load(BUNDLE, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n.replace(" ", "") == name.replace(" ", "")]
    ob = dst.objects[0]
    me = ob.data
    # (an appended object is in no scene, so its matrix_world is not evaluated: its own location, turn and scale)
    mw = np.array(ob.matrix_basis)

    def world(co):
        return (np.c_[co, np.ones(len(co))] @ mw.T)[:, :3]
    P = world(np.array([v.co for v in me.vertices]))
    keys = {}
    if me.shape_keys:
        for kb in me.shape_keys.key_blocks:
            keys[kb.name] = world(np.array([d.co for d in kb.data]))
    faces = [list(p.vertices) for p in me.polygons]
    uvl = me.uv_layers[0].data
    uvs = [[tuple(uvl[li].uv) for li in p.loop_indices] for p in me.polygons]
    bpy.data.objects.remove(ob, do_unlink=True)
    return P, faces, uvs, keys


def mirror_pairs(P, tol=2e-3):
    kd = kdtree.KDTree(len(P))
    for i, p in enumerate(P):
        kd.insert(Vector(p), i)
    kd.balance()
    mir = np.arange(len(P))
    for i, p in enumerate(P):
        q, j, d = kd.find(Vector((-p[0], p[1], p[2])))
        if d < tol:
            mir[i] = j
    return mir


def symmetric(P, mir, keep=None):
    Q = P[mir].copy()
    Q[:, 0] *= -1
    out = (P + Q) / 2.0
    alone = mir == np.arange(len(P))
    out[alone] = P[alone]
    out[alone & (np.abs(P[:, 0]) < 2e-3), 0] = 0.0
    if keep is not None:
        out[keep] = P[keep]
    return out


def tris_of(faces):
    return [(f[0], f[i], f[i + 1]) for f in faces for i in range(1, len(f) - 1)]


def folded(P, faces):
    """Triangles whose normal turns against the mean of their corners' normals (folded over or crossing)."""
    T = np.array(tris_of(faces))
    P = np.asarray(P)
    Nv = normals_of(P, T)
    fn = np.cross(P[T[:, 1]] - P[T[:, 0]], P[T[:, 2]] - P[T[:, 0]])
    bad = (fn * Nv[T].mean(1)).sum(1) < 0
    return int(bad.sum()), T[bad]


def view_mask(P, tris, view, shape):
    P2, dep = project(view, P)
    zb, _ = raster(P2, dep, tris, shape)
    return np.isfinite(zb)


def box_smooth(a, n=4):
    a = np.asarray(a, float)
    out = a.copy()
    for i in range(len(a)):
        out[i] = a[max(0, i - n):i + n + 1].mean()
    return out


def fill_nan(a):
    a = np.asarray(a, float)
    ok = np.isfinite(a)
    idx = np.arange(len(a))
    return np.interp(idx, idx[ok], a[ok])


def head_rows_warp(P, tris_head, tris_all, sh, rows=(H_CROWN + 22, HR(1160))):
    """Every point moved, by its height, so that the head's front-view width and side-view front and back match the
    bald row's at that height (the ears out of the front view; across the ears' rows the width's scale is carried
    smoothly from the rows above and below them, as the target's outline is)."""
    rr = np.arange(rows[0], rows[1] + 1)
    kx = np.full(len(rr), np.nan)
    m = view_mask(P, tris_head, "hfront", sh.head_mask.shape)
    mid = HVIEW["hfront"][1]
    c0, c1 = HSPAN["hfront"]
    for i, r in enumerate(rr):
        # (below the jaw's angles the sheet's front outline is his neck, not his jaw: the scale is held from there)
        if H_EARS[0] - 6 <= r <= H_EARS[1] + 8 or r > JAW_ROW:
            continue
        a = run_near(m, r, mid, c0, c1)
        b = run_near(sh.head_target, r, mid, c0, c1)
        if a and b and a[1] - a[0] > 6:
            kx[i] = (b[1] + 1 - b[0]) / float(a[1] + 1 - a[0])
    kx = box_smooth(fill_nan(kx), 6)
    m = view_mask(P, tris_all, "hside", sh.head_mask.shape)
    mid = HVIEW["hside"][1]
    c0, c1 = HSPAN["hside"]
    ys = np.full((len(rr), 4), np.nan)
    for i, r in enumerate(rr):
        a = run_near(m, r, mid, c0, c1)
        b = run_near(sh.head_mask, r, mid, c0, c1)
        if a and b:
            ys[i] = (side_y(a[1] + 1), side_y(a[0]), side_y(b[1] + 1), side_y(b[0]))
            # (below the skull's base the side view's back is the back of his neck)
            # (and the base's skull ends higher at his back than the sheet's nape: held from WARP_NAPE)
            if r > WARP_NAPE:
                ys[i, 1] = ys[i, 3] = np.nan
    for k in range(4):
        ys[:, k] = box_smooth(fill_nan(ys[:, k]), 3)
    if "--debug-warp" in ARGS:
        for i in range(0, len(rr), 20):
            print("WARP row %d kx %.3f side model %.3f %.3f target %.3f %.3f" % (rr[i], kx[i], *ys[i]))
    r = np.clip(hrow(P[:, 2]), rr[0], rr[-1])
    k = np.interp(r, rr, kx)
    fm, bm_, ft, bt = (np.interp(r, rr, ys[:, j]) for j in range(4))
    Q = P.copy()
    Q[:, 0] *= k
    Q[:, 1] = ft + (P[:, 1] - fm) * (bt - ft) / np.maximum(bm_ - fm, 1e-6)
    return Q


JAW_ROW = 1238            # the jaw's angles (head-sheet row): below, the front view's outline is his neck
NAPE_ROW = 1230           # the skull's base at his back: below, the side view's back is his neck
CHIN_HALF = 32           # the chin's half width (head-sheet pixels) at its bottom, the front view
THROAT_ROW = 1322         # below this row the side view's front is his throat (above, his chin)
JAW_REACH = 0.05          # metres: how much of his face moves with the jaw's angle (smaller dented his cheeks)
WARP_NAPE = HR(1015)         # the lowest row whose side-view back the row warp matches (the base head's nape)


def head_view_rows(view, P, rows):
    """Which points of the head may be pulled onto a view's outline: only where that outline is the head's own (the
    sheet draws his neck below the jaw and the nape). The middle of the face (lips, nose, chin) is left to the
    row-by-row warp, which already put its profile on the side view's: pulled point by point it crumpled."""
    face_mid = (np.abs(P[:, 0]) < 0.035) & (rows > HR(985)) & (rows < HR(1175)) & (P[:, 1] < -0.09)
    if view in ("hfront", "hback"):
        return rows < JAW_ROW
    if view == "hqb":
        return rows < NAPE_ROW
    front = P[:, 1] < -0.03
    if view == "hq":
        # (fourth pass: the far cheek, pulled onto the 3/4 view's outline at the model's own best angle, was dented
        # hollow: an old man's cheek. The face's front is left to the front and side views; the 3/4 view fits his
        # cranium and the back of his jaw)
        return (rows < NAPE_ROW) & ~(front & (rows > HR(925)))
    return ((rows < NAPE_ROW) | (front & (rows < HR(1172)))) & ~face_mid


def neck_view_rows(view, P, rows):
    """Which neck points may be pulled onto a view's outline: in the side views, his throat only below the chin's
    bottom (above it the sheet's outline is the chin); in the front and back, below the jaw's angles."""
    if view in ("hfront", "hback"):
        return rows > JAW_ROW
    return (P[:, 1] > -0.02) | (rows > THROAT_ROW)


def outline_fit(P, tris_draw, movable, views, sh, rounds=8, reach=24, damp=0.8, step=0.004, rows_max=H_NECK - 4,
                mir=None, edges=None, label="head", no_ears_tris=None, head=False, spread=8, neck=False):
    """Points on the model's outline in each view (head sheet) moved along their outward direction onto the sheet's
    outline, the moves spread to their neighbours, left and right kept alike. views: name -> target mask. In the
    front and back views the ears are left out of the drawing (no_ears_tris), as they are out of the target."""
    P = np.array(P, float)
    E = edges
    deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
    for rnd in range(rounds):
        N = normals_of(P, tris_draw)
        move = np.zeros_like(P)
        count = np.zeros(len(P))
        rows_p = hrow(P[:, 2])
        for view, tgt in views.items():
            tr = no_ears_tris if (view in ("hfront", "hback") and no_ears_tris is not None) else tris_draw
            h, w = tgt.shape
            P2, dep = project(view, P)
            zb, _ = raster(P2, dep, tr, tgt.shape)
            R = np.isfinite(zb)
            d2, facing = screen_dir(view, N)
            L = np.linalg.norm(d2, axis=1)
            ok = movable & (np.abs(facing) < 0.55) & (L > 0.4) & (rows_p < rows_max)
            if head:
                ok &= head_view_rows(view, P, rows_p)
            if neck:
                ok &= neck_view_rows(view, P, rows_p)
            c0, c1 = HSPAN[view]
            for v in np.where(ok)[0]:
                p = P2[v]
                if not (c0 <= p[0] < c1):
                    continue
                dirn = d2[v] / L[v]
                q = p + dirn * 3.0
                qi = (int(q[1]), int(q[0]))
                if not (0 <= qi[0] < h and 0 <= qi[1] < w) or R[qi]:
                    continue
                pi = (int(p[1]), int(p[0]))
                if not (0 <= pi[0] < h and 0 <= pi[1] < w):
                    continue
                dist = None
                if tgt[pi]:
                    for k in range(1, reach + 1):
                        qq = p + dirn * k
                        if not tgt[min(max(int(qq[1]), 0), h - 1), min(max(int(qq[0]), 0), w - 1)]:
                            dist = k - 0.5
                            break
                else:
                    for k in range(1, reach + 1):
                        qq = p - dirn * k
                        if tgt[min(max(int(qq[1]), 0), h - 1), min(max(int(qq[0]), 0), w - 1)]:
                            dist = -(k - 0.5)
                            break
                if dist is None:
                    continue
                move[v] += world_dir(view, dirn[None, :])[0] * dist * HS
                count[v] += 1
        has = count > 0
        move[has] /= count[has, None]
        ln = np.linalg.norm(move, axis=1, keepdims=True)
        move *= np.minimum(1.0, step / np.maximum(ln, 1e-9))
        D = move.copy()
        W = has.astype(float) * 4.0
        for _ in range(spread):
            acc = np.zeros_like(D)
            np.add.at(acc, E[:, 0], D[E[:, 1]])
            np.add.at(acc, E[:, 1], D[E[:, 0]])
            D = (W[:, None] * move + acc) / np.maximum(W + deg, 1e-9)[:, None]
        D[~movable] = 0.0
        P += D * damp
        if mir is not None:
            P = symmetric(P, mir, keep=~movable)
        print("BOY %s outline fit round %d: %d points on the outline moved, most %.1f mm" % (
            label, rnd + 1, int(has.sum()), 1000 * float(np.abs(move[has]).max() if has.any() else 0)))
    return P


def smooth_points(P, edges, sel, rounds=2, lam=0.5, mu=-0.53):
    P = np.array(P, float)
    E = edges
    deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
    sel = sel & (deg > 0)
    for _ in range(rounds):
        for f in (lam, mu):
            acc = np.zeros_like(P)
            np.add.at(acc, E[:, 0], P[E[:, 1]])
            np.add.at(acc, E[:, 1], P[E[:, 0]])
            avg = acc / np.maximum(deg, 1)[:, None]
            P[sel] += (avg[sel] - P[sel]) * f
    return P


def subdivide_some(P, faces, uvs, flags, sel):
    """The selected faces split once (bmesh: a grid fill, the faces round them split to meet them, n-gons made
    triangles); UVs and the per-point flags carried over. Gives (points, faces, uvs, flags, the old points' new
    numbers)."""
    bm = bmesh.new()
    # (the layers made first: adding one later frees the elements already made)
    lay = {k: bm.verts.layers.float.new(k) for k in flags}
    uvl = bm.loops.layers.uv.new("UVMap")
    vs = [bm.verts.new(Vector(p)) for p in P]
    for k, arr in flags.items():
        for v, a in zip(vs, arr):
            v[lay[k]] = float(a)
    fs = []
    for f, uv in zip(faces, uvs):
        bf = bm.faces.new([vs[i] for i in f])
        for l_, q in zip(bf.loops, uv):
            l_[uvl].uv = q
        fs.append(bf)
    bm.normal_update()
    edges = list({e for fi in sel for e in fs[fi].edges})
    bmesh.ops.subdivide_edges(bm, edges=edges, cuts=1, use_grid_fill=True, use_single_edge=True, smooth=1.0,
                              quad_corner_type="INNER_VERT")
    ngons = [f for f in bm.faces if len(f.verts) > 4]
    if ngons:
        bmesh.ops.triangulate(bm, faces=ngons)
    bm.verts.index_update()
    Pn = np.array([v.co[:] for v in bm.verts])
    Fn = [[v.index for v in f.verts] for f in bm.faces]
    Un = [[tuple(l_[uvl].uv) for l_ in f.loops] for f in bm.faces]
    Fl = {k: np.array([v[lay[k]] for v in bm.verts]) for k in flags}
    bm.free()
    kd = kdtree.KDTree(len(Pn))
    for i, p in enumerate(Pn):
        kd.insert(Vector(p), i)
    kd.balance()
    old = np.array([kd.find(Vector(p))[1] for p in P])
    return Pn, Fn, Un, Fl, old


def stage(name, P, faces):
    """(for checking) the head as it stands after a step, saved beside the overlays"""
    if OUT:
        os.makedirs(os.path.join(OUT, "stages"), exist_ok=True)
        flat = [len(f) for f in faces]
        np.savez(os.path.join(OUT, "stages", name + ".npz"), P=np.asarray(P), F=np.concatenate([np.asarray(f) for f in faces]), FS=np.array(flat))


EAR_ROUND = float(arg("--ear-round", "1.6"))
EAR_THICK = float(arg("--ear-thick", "0.0006"))   # (seventh pass: from 0.0016; "thick, flat paddles ... thin the rim")
# (sixth pass, the budget: the crown's faces are no longer split (its outline is smooth enough lit), and the face only
# where it faces forward)
SPLIT_CROWN = "--no-split-crown" not in ARGS
SPLIT_FACING = float(arg("--split-facing", "-0.5"))


def round_ears(P, ear, root, mir, faces, bins=36, win=6):
    """(sixth pass; the critic: "the upper helix drawn into a POINT ... an elf or goblin ... round the helix top into an
    arc") Each ear's outline made round in the side view (y, z) and in the front view (out, z): round the ear's middle,
    the outline's reach at each angle (the furthest point there) is replaced by its average over the angles near it
    (a corner is cut to the arc through its neighbours, a round edge kept), and each point is moved in by its share of
    that, the rim most, the root not at all."""
    P = np.array(P, float)
    if EAR_ROUND <= 0:
        return P
    most = 0.0
    for sgn in (1.0, -1.0):
        ids = np.where(ear & (np.sign(P[:, 0]) == sgn))[0]
        most = max(most, _round_ear(P, ids, root, bins, win))
        # the front view: the ear's top drawn in toward his head on an arc (its top-out corner read as an elf's point
        # from above and below), the root kept
        Q = P[ids]
        r_x = float(np.abs(Q[root[ids], 0]).mean()) if root[ids].any() else float(np.abs(Q[:, 0]).min())
        zc, zt = float(Q[:, 2].mean()), float(Q[:, 2].max())
        u = np.clip((Q[:, 2] - zc) / max(zt - zc, 1e-4), 0, 1)
        f = np.sqrt(np.clip(1.0 - (u / 1.12) ** 2, 0.0, 1.0)) * 0.55 + 0.45
        off = np.abs(Q[:, 0]) - r_x
        Q[:, 0] = np.where(root[ids] | (off <= 0), Q[:, 0], np.sign(Q[:, 0]) * (r_x + off * f))
        P[ids] = Q
    # (the critic: "thin plates") the ear's two sides pushed apart along their own normals, most at the rim
    N = normals_of(P, tris_of(faces))
    xa = np.abs(P[:, 0])
    for sgn in (1.0, -1.0):
        ids = np.where(ear & (np.sign(P[:, 0]) == sgn) & ~root)[0]
        r0 = float(np.abs(P[ear & root & (np.sign(P[:, 0]) == sgn), 0]).mean())
        w = smooth01(r0, r0 + 0.02, xa[ids])
        P[ids] += N[ids] * (EAR_THICK * (0.4 + 0.6 * w))[:, None]
    print("BOY ears rounded: most moved %.1f mm" % (most * 1000))
    return P


def _round_ear(P, ids, root, bins, win):
    most = 0.0
    r_x = float(P[ids[root[ids]], 0].mean()) if root[ids].any() else float(P[ids, 0].min())
    for plane in ((1, 2),):
        Q = P[ids]
        a, b = plane
        c = np.array((Q[:, a].mean() if a == 1 else r_x, Q[:, b].mean()))
        if a == 0:
            # the front view's middle: half way out from the root, at the ear's middle height
            c[0] = (r_x + Q[:, 0].max()) / 2.0
        d = np.stack([Q[:, a] - c[0], Q[:, b] - c[1]], 1)
        half = np.maximum(np.abs(d).max(0), 1e-4)
        d = d / half
        rho = np.linalg.norm(d, axis=1)
        th = np.arctan2(d[:, 1], d[:, 0])
        k_ = np.clip(((th + math.pi) / math.tau * bins).astype(int), 0, bins - 1)
        R = np.zeros(bins)
        for i in range(bins):
            R[i] = rho[k_ == i].max() if (k_ == i).any() else np.nan
        ok = np.isfinite(R)
        R = np.interp(np.arange(bins), np.where(ok)[0], R[ok], period=bins)
        Rs = np.array([np.mean([R[(i + j) % bins] for j in range(-win, win + 1)]) for i in range(bins)])
        Rs = np.minimum(Rs, R)
        # each point's own envelope by its angle (between bins), and the cut by its share of the reach
        tb = (th + math.pi) / math.tau * bins - 0.5
        Ri = np.interp(tb, np.arange(bins), R, period=bins)
        Rsi = np.interp(tb, np.arange(bins), Rs, period=bins)
        k = 1.0 - (1.0 - Rsi / np.maximum(Ri, 1e-6)) * np.clip(rho / np.maximum(Ri, 1e-6), 0, 1) ** 1.5 * EAR_ROUND
        k = np.where(root[ids], 1.0, k)
        Q[:, a] = c[0] + d[:, 0] * k * half[0]
        Q[:, b] = c[1] + d[:, 1] * k * half[1]
        most = max(most, float(np.max(rho * (1 - k))) * float(half.max()))
        P[ids] = Q
    return most


# (eleventh pass) The head made the way the base mesh is meant to be used: its cage (316 quads) fitted, then ONE
# Catmull-Clark subdivision of the whole of it (the bundle's own Subdivision modifier at level 1), in place of the
# earlier split of chosen faces, whose unsplit faces showed as facets and whose many smoothing and carving passes over
# the split face flattened the jaw into the neck. The base's ears (five-sided blocks) are folded flat into the skull
# and the bundle's own ear (GEO-ear_male_primitive_stylized.L: rim, bowl, closed back) is set into it instead.
# --old-head builds the tenth pass's head.
HEAD2 = "--old-head" not in ARGS
EAR_BASE = "GEO-ear_male_primitive_stylized.L"
EAR_ANGLE = float(arg("--ear-angle", "32"))      # degrees the ear's back stands off the skull, seen from above
EAR_SINK = float(arg("--ear-sink", "0.006"))     # metres its front edge is set into the skull
EAR_SIZE = float(arg("--ear-size", "1.08"))
EAR_THIN = float(arg("--ear-thin", "0.42"))     # its thickness against the base's own (the base's is a thick disc)
EAR_MIN_ANGLE = float(arg("--ear-min-angle", "22"))
EAR_BOWL = float(arg("--ear-bowl", "0.006"))     # metres the bowl is pressed in
EAR_TILT = float(arg("--ear-tilt", "12"))        # degrees its top leans back
EAR_ROUND_TOP = float(arg("--ear-round-top", "0.3"))
EAR_DOWN = float(arg("--ear-down", "0.011"))     # metres it sits below EAR_ROWS' middle (the front view's lobe is lower)
EAR_EVEN = int(arg("--ear-even", "3"))


def cc_subdivide(P, faces, uvs, flags=None):
    """One Catmull-Clark step (open edges kept as creases: the neck's hole). The old points keep their numbers; then
    one point per edge, then one per face. UVs per face corner are carried (corners, edge middles, face middles), and
    per-point flags (an edge's point is set if both ends are, a face's if all corners are). Gives (points, faces, uvs,
    flags, edge point of each edge)."""
    P = np.asarray(P, float)
    nv = len(P)
    eid, ef = {}, []
    for fi, f in enumerate(faces):
        for i in range(len(f)):
            a, b = f[i], f[(i + 1) % len(f)]
            k = (min(a, b), max(a, b))
            if k not in eid:
                eid[k] = len(ef)
                ef.append([])
            ef[eid[k]].append(fi)
    ne = len(ef)
    E = np.array(sorted(eid, key=lambda k: eid[k]))
    FP = np.array([P[f].mean(0) for f in faces])
    bnd = np.array([len(x) == 1 for x in ef])
    EP = (P[E[:, 0]] + P[E[:, 1]]) / 2.0
    inner = ~bnd
    EP[inner] = np.array([(P[a] + P[b] + FP[ef[i][0]] + FP[ef[i][1]]) / 4.0 for i, (a, b) in enumerate(E) if inner[i]])
    # the old points
    Q = np.zeros((nv, 3))
    nF = np.zeros(nv)
    for fi, f in enumerate(faces):
        for v in f:
            Q[v] += FP[fi]
            nF[v] += 1
    R = np.zeros((nv, 3))
    nE = np.zeros(nv)
    bsum = np.zeros((nv, 3))
    nb = np.zeros(nv)
    for i, (a, b) in enumerate(E):
        mid = (P[a] + P[b]) / 2.0
        R[a] += mid
        R[b] += mid
        nE[a] += 1
        nE[b] += 1
        if bnd[i]:
            bsum[a] += P[b]
            bsum[b] += P[a]
            nb[a] += 1
            nb[b] += 1
    NP = P.copy()
    for v in range(nv):
        if nb[v] >= 2:
            NP[v] = (bsum[v] + 6.0 * P[v]) / 8.0 if nb[v] == 2 else P[v]
        elif nF[v] > 0:
            n = nE[v]
            NP[v] = (Q[v] / nF[v] + 2.0 * R[v] / nE[v] + (n - 3.0) * P[v]) / n
    Pn = np.concatenate([NP, EP, FP])
    Fn, Un = [], []
    for fi, f in enumerate(faces):
        k = len(f)
        uv = np.array(uvs[fi], float)
        um = uv.mean(0)
        for i in range(k):
            a, b, c = f[i - 1], f[i], f[(i + 1) % k]
            e_prev = nv + eid[(min(a, b), max(a, b))]
            e_next = nv + eid[(min(b, c), max(b, c))]
            Fn.append([b, e_next, nv + ne + fi, e_prev])
            Un.append([tuple(uv[i]), tuple((uv[i] + uv[(i + 1) % k]) / 2.0), tuple(um), tuple((uv[i - 1] + uv[i]) / 2.0)])
    fl = {}
    for name, arr in (flags or {}).items():
        arr = np.asarray(arr, bool)
        fl[name] = np.concatenate([arr, arr[E[:, 0]] & arr[E[:, 1]], np.array([arr[f].all() for f in faces])])
    return Pn, Fn, Un, fl, {tuple(k): nv + i for k, i in eid.items()}


def membrane(P, edges, sel, rounds=300):
    """The selected points relaxed to the mean of their neighbours (the rest held): a smooth skin over a gap."""
    P = np.array(P, float)
    E = np.asarray(edges)
    deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
    for _ in range(rounds):
        acc = np.zeros_like(P)
        np.add.at(acc, E[:, 0], P[E[:, 1]])
        np.add.at(acc, E[:, 1], P[E[:, 0]])
        P[sel] = acc[sel] / np.maximum(deg[sel], 1)[:, None]
    return P


def bundle_ear():
    """The bundle's left ear in its own frame: x out of the head (its back, which lies on the skull, at x 0), y toward
    the back of the head (its front edge at y 0), z up (its middle height at 0). Gives points, faces, uvs."""
    P, faces, uvs, _ = load_base(EAR_BASE)
    c = (P.max(0) + P.min(0)) / 2.0
    ext = P.max(0) - P.min(0)
    print("BOY bundle ear: %d points, %d faces, extents %s m, middle %s" % (len(P), len(faces), np.round(ext, 4).tolist(), np.round(c, 3).tolist()))
    # its thinnest axis is the one out of the head (the base sits on the head's left, +X)
    Q = P - c
    ax = int(np.argmin(ext))
    if ax != 0:
        raise RuntimeError("the bundle ear's thin axis is %d, not x" % ax)
    Q[:, 0] -= Q[:, 0].min()
    Q[:, 1] -= Q[:, 1].min()
    return Q, faces, uvs


def place_ears(P, sh, head_tris):
    """The bundle's ear sized to the bald side view's ear (EAR_ROWS, EAR_COLS), its back set on the skull with its front
    edge sunk EAR_SINK into it, turned out about its front edge until its rim reaches the front view's stand-out (or
    EAR_ANGLE at most). Gives the left ear's points, faces, uvs (mirror for the right)."""
    Q, faces, uvs = bundle_ear()
    # (its outline is a 16-sided polygon whose uneven corners showed: evened, without shrinking it)
    Q = smooth_points(Q, edges_of(faces), np.ones(len(Q), bool), rounds=EAR_EVEN)
    zt, zb = float(hz(EAR_ROWS[0])), float(hz(EAR_ROWS[1]))
    yf, yb = side_y(EAR_COLS[0]), side_y(EAR_COLS[1])
    ext = Q.max(0) - Q.min(0)
    ky = (yb - yf) / ext[1] * EAR_SIZE
    kz = (zt - zb) / ext[2] * EAR_SIZE
    kx = 0.5 * (ky + kz) * EAR_THIN
    Q = Q * np.array((kx, ky, kz))
    # (the bowl deepened again after the thinning: the outer face's points inside the rim pressed toward the skull,
    # most at the bowl's middle, so it reads cupped from the side and the front; the rim rolled a little outward)
    tri_e = np.array(tris_of(faces))
    Ne = normals_of(Q, tri_e)
    cyz = (Q[:, 1:].max(0) + Q[:, 1:].min(0)) / 2.0
    hyz = (Q[:, 1:].max(0) - Q[:, 1:].min(0)) / 2.0
    rr = np.linalg.norm((Q[:, 1:] - cyz) / hyz, axis=1)
    vol = float(np.einsum("ij,ij->i", Q[tri_e[:, 0]], np.cross(Q[tri_e[:, 1]], Q[tri_e[:, 2]])).sum())
    if vol < 0:
        Ne = -Ne
    outer = smooth01(0.1, 0.6, Ne[:, 0])
    print("BOY ear bowl: %d points on its outer face (volume sign %+.0f)" % (int((outer > 0.5).sum()), np.sign(vol)))
    Q[:, 0] -= EAR_BOWL * outer * (1.0 - smooth01(0.35, 0.78, rr))
    Q[:, 0] += EAR_BOWL * 0.25 * outer * smooth01(0.8, 0.98, rr)
    # (the sheet's ear is a round C, broad at the top; the base's an oval pointed at both ends: its top half widened
    # front to back, most at the top, and the top's crown rounded down a little)
    u = np.clip((Q[:, 2] - cyz[1]) / hyz[1], -1.0, 1.0)
    Q[:, 1] = cyz[0] + (Q[:, 1] - cyz[0]) * (1.0 + EAR_ROUND_TOP * smooth01(-0.1, 0.75, u))
    Q[:, 2] -= hyz[1] * 0.08 * smooth01(0.6, 1.0, u) * (1.0 - np.abs((Q[:, 1] - cyz[0]) / hyz[0]).clip(0, 1))
    # (the sheet's side view leans the ear's top back) turned about its own middle across the head
    ta = math.radians(EAR_TILT)
    d1, d2 = Q[:, 1] - cyz[0], Q[:, 2] - cyz[1]
    Q[:, 1] = cyz[0] + d1 * math.cos(ta) + d2 * math.sin(ta)
    Q[:, 2] = cyz[1] - d1 * math.sin(ta) + d2 * math.cos(ta)
    Q[:, 1] -= Q[:, 1].min()
    Q[:, 1] += yf - (ky * ext[1] - (yb - yf)) / 2.0
    Q[:, 2] += (zt + zb) / 2.0 - cyz[1] - EAR_DOWN
    # the skull's surface beside the ear: the head's furthest point out near the ear's front edge's middle
    Ph = np.asarray(P)
    hv = np.unique(np.asarray(head_tris).ravel())
    near = hv[(np.abs(Ph[hv, 2] - (zt + zb) / 2) < 0.02) & (np.abs(Ph[hv, 1] - (yf + 0.01)) < 0.015) & (Ph[hv, 0] > 0)]
    x_front = float(Ph[near, 0].max())
    near = hv[(np.abs(Ph[hv, 2] - (zt + zb) / 2) < 0.02) & (np.abs(Ph[hv, 1] - yb) < 0.015) & (Ph[hv, 0] > 0)]
    x_back = float(Ph[near, 0].max()) if len(near) else x_front
    # the front view's stand-out at the ear's middle
    rmid = int((EAR_ROWS[0] + EAR_ROWS[1]) / 2)
    runs = run_near(sh.head_mask, rmid, HVIEW["hfront"][1], *HSPAN["hfront"])
    out_t = (runs[1] + 1 - runs[0]) / 2.0 * HS
    pivot = np.array((x_front - EAR_SINK, yf, 0.0))
    best = None
    for ang in np.arange(EAR_MIN_ANGLE, EAR_ANGLE + 0.1, 1.0):
        a = math.radians(ang)
        # turned about the vertical through the front edge: the back swings out
        d = Q - np.array((0.0, yf, 0.0))
        X = pivot[0] + d[:, 0] * math.cos(a) + d[:, 1] * math.sin(a)
        Y = yf - d[:, 0] * math.sin(a) + d[:, 1] * math.cos(a)
        reach = float(X.max())
        # (the ear's back must stay on the skull at its back edge too: not turned in)
        if best is None or abs(reach - out_t) < abs(best[0] - out_t):
            best = (reach, ang, np.stack([X, Y, Q[:, 2]], 1))
    reach, ang, Qp = best
    print("BOY ear (bundle): sized x%.2f y%.2f z%.2f; skull at x %.3f (front) %.3f (back); turned out %.0f degrees, "
          "its rim %.3f m from his middle (sheet %.3f)" % (kx, ky, kz, x_front, x_back, ang, reach, out_t))
    return Qp, faces, uvs


def make_head(sh):
    """The bald head with its ears, from the base mesh: mixed, cut open for the neck, moved onto his landmarks'
    heights, warped row by row to the bald row's outlines, the ears sized to the sheet's, the face and ears split once,
    then fitted to all five views' outlines. Gives a dict (points, faces, uvs, ear flags, the neck hole's ring in
    order, landmark points)."""
    B, faces, uvs, keys = load_base(HEAD_BASE)
    P = keys["Basis"].copy()
    # (the anime kid's share is larger round the eyes, ANIME_EYES: his big eyes and soft brow, without its puffy lips)
    Kd = keys["Real_Kid"]
    eye_c = Kd[list(HB_EYE)].mean(0)
    eye_c2 = eye_c * np.array((-1.0, 1.0, 1.0)) + np.array((2.0 * ((Kd[:, 0].min() + Kd[:, 0].max()) / 2.0), 0.0, 0.0))
    d = np.minimum(np.linalg.norm(Kd - eye_c, axis=1), np.linalg.norm(Kd - eye_c2, axis=1))
    w_eye = np.exp(-(d / 0.03) ** 2)
    for k, w in HEAD_MIX.items():
        ww = w + (ANIME_EYES - w) * w_eye if k == "Toon_Anime_Kid" else w
        P += (keys[k] - keys["Basis"]) * np.reshape(ww, (-1, 1))
    P[:, 0] -= (P[:, 0].min() + P[:, 0].max()) / 2.0
    mir = mirror_pairs(P)
    P = symmetric(P, mir)
    n0 = len(faces)
    # the neck's hole
    # (chosen on the plain Real_Kid shape, so the same faces whatever the mix)
    Kd = keys["Real_Kid"].copy()
    Kd[:, 0] -= (Kd[:, 0].min() + Kd[:, 0].max()) / 2.0
    F4 = np.array(faces)
    C = Kd[F4].mean(1)
    nrm = np.cross(Kd[F4[:, 2]] - Kd[F4[:, 0]], Kd[F4[:, 3]] - Kd[F4[:, 1]])
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
    cy, ax, ay = NECK_HOLE
    cut = (nrm[:, 2] < -0.2) & ((C[:, 0] / ax) ** 2 + ((C[:, 1] - cy) / ay) ** 2 < 1.0)
    faces = [f for f, c in zip(faces, cut) if not c]
    uvs = [u for u, c in zip(uvs, cut) if not c]
    ec = {}
    for f in faces:
        for i in range(len(f)):
            e = (min(f[i], f[(i + 1) % len(f)]), max(f[i], f[(i + 1) % len(f)]))
            ec[e] = ec.get(e, 0) + 1
    bnd = [e for e, c in ec.items() if c == 1]
    adj = {}
    for a, b in bnd:
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    start = min(adj, key=lambda v: (abs(P[v, 0]) > 1e-5, P[v, 1]))
    nxt = max(adj[start], key=lambda v: P[v, 0])
    hole = [start, nxt]
    while True:
        c = [v for v in adj[hole[-1]] if v != hole[-2]][0]
        if c == start:
            break
        hole.append(c)
    print("BOY head base: %d quads, %d cut for the neck, its hole a ring of %d points" % (n0, int(cut.sum()), len(hole)))
    # the ears: the points standing out at the ears' height, grown over their neighbours out there
    ear = np.zeros(len(P), bool)
    box = (np.abs(P[:, 0]) > 0.07) & (P[:, 2] > 0.015) & (P[:, 2] < 0.095) & (P[:, 1] > -0.065) & (P[:, 1] < 0.0)
    ear[box & (np.abs(P[:, 0]) > 0.085)] = True
    nb = {}
    for f in faces:
        for i in range(len(f)):
            nb.setdefault(f[i], set()).update((f[i - 1], f[(i + 1) % len(f)]))
    for _ in range(6):
        grow = ear.copy()
        for v in np.where(ear)[0]:
            for u in nb[v]:
                if box[u]:
                    grow[u] = True
        ear = grow
    print("BOY head base: %d points in the ears" % int(ear.sum()))
    stage("0_base", P, faces)
    # the base's landmarks (base coordinates) and its mouth's corners, jaw angles, ear lobes
    marks = dict(HB)
    marks["mouth_l"] = HB_MOUTH_L
    marks["jaw_l"] = HB_JAW_L
    e = np.where(ear & (P[:, 0] > 0))[0]
    marks["lobe_l"] = int(e[np.argmin(P[e, 2])])
    marks["ear_top_l"] = int(e[np.argmax(P[e, 2])])
    for k in ("mouth", "jaw", "lobe", "ear_top"):
        marks[k + "_r"] = int(mir[marks[k + "_l"]])
    # 1. heights: a scale and a lift putting chin and crown where the sheet has them, then each landmark's height
    z_ch, z_cr = P[HB["chin"], 2], P[HB["crown"], 2]
    s = (float(hz(H_CROWN)) - Z_CHIN) / (z_cr - z_ch)
    y_brow = side_y(side_run(sh, 1035)[1] + 1)
    P = np.stack([P[:, 0] * s, (P[:, 1] - P[HB["brow"], 1]) * s + y_brow, Z_CHIN + (P[:, 2] - z_ch) * s], 1)
    src = []
    for name, row in HB_ROWS:
        z = P[list(HB_EYE), 2].mean() if name == "eye" else P[HB[name], 2]
        src.append((float(z), float(hz(row))))
    src.sort()
    P[:, 2] = np.interp(P[:, 2], [a for a, _ in src], [b for _, b in src])
    tris_all = tris_of(faces)
    tris_head = [t for t in tris_all if not ear[list(t)].any()]
    stage("1_heights", P, faces)
    # 2. the outlines row by row (twice: the second corrects what the first's smoothing left)
    for _ in range(2):
        P = head_rows_warp(P, tris_head, tris_all, sh)
        P = symmetric(P, mir)
    stage("2_rows", P, faces)
    # 2a. landmarks the outlines cannot place, pulled onto the bald front and side views' (radial basis moves, each
    # with its own reach, solved so each lands exactly): the jaw's angles (the base's sit up at the ear lobes; the
    # sheet's below them, JAW_ANGLE) (the mouth's corners were tried too: pulled 2 cm
    # back to the sheet's side-view corner they dented his cheeks; the base's mouth is as wide as the sheet's)
    pulls = []
    # (fourth pass: the base's own jaw-angle point sits against the ear's lobe, so the guard that keeps the ears still
    # held it still too and the jaw's angles stayed 4 cm high. The jaw's angle is now the point of the jaw line 1.2 to
    # 3 cm from the ear nearest the sheet's angle, and the guard holds only what is within 2 cm of the ear)
    Ep0 = P[ear]
    de0 = np.array([np.linalg.norm(Ep0 - p, axis=1).min() for p in P])
    for s, sfx in ((1.0, "_l"), (-1.0, "_r")):
        tgt = np.array((s * JAW_ANGLE[1] * HS, side_y(JAW_ANGLE[2]), float(hz(JAW_ANGLE[0]))))
        cand = np.where(~ear & (np.sign(P[:, 0]) == s) & (de0 > 0.012) & (de0 < 0.03) & (P[:, 2] < P[marks["lobe" + sfx], 2]))[0]
        if len(cand):
            marks["jaw" + sfx] = int(cand[np.argmin(np.linalg.norm(P[cand] - tgt, axis=1))])
        pulls.append((marks["jaw" + sfx], tuple(tgt), JAW_REACH))
    C_ = np.array([P[i] for i, _, _ in pulls])
    Dt = np.array([t for _, t, _ in pulls]) - C_
    R_ = np.array([r for _, _, r in pulls])
    K_ = np.exp(-(np.linalg.norm(C_[:, None] - C_[None], axis=2) / R_[None, :]) ** 2)
    Wt = np.linalg.solve(K_, Dt)
    Phi = np.exp(-(np.linalg.norm(P[:, None] - C_[None], axis=2) / R_[None, :]) ** 2)
    Dm = Phi @ Wt
    # (the ears and the head round their roots kept still: moved with the jaw, the ears stretched down)
    Ep = P[ear]
    de = np.array([np.linalg.norm(Ep - p, axis=1).min() for p in P])
    Dm *= smooth01(0.002, 0.02, de)[:, None]
    P = P + Dm
    print("BOY landmarks pulled: %s cm" % [round(float(np.linalg.norm(d)) * 100, 1) for d in Dt])
    n_, _ = folded(P, faces)
    print("BOY head after the landmark pulls: %d triangles folded" % n_)
    # 2b. the jaw: below its angles the sheet's outline is his neck, so the jaw's own width is set from the bald front
    # view's landmarks instead: a narrow V from the angles (JAW_ANGLE: 130 pixels out at row 1090) to a pointed chin
    # (CHIN_HALF out at row 1165), each row's widest point of the head moved onto that line
    rows_p = hrow(P[:, 2])
    lower = ~ear & (rows_p > JAW_ANGLE[0] - 15)
    rr = np.arange(int(JAW_ANGLE[0]) - 15, int(CHIN_ROW) + 5)
    # (fifth pass: a round jaw, a U, not a V from the angles to the chin)
    # (seventh pass: the sheet's bald front view, measured at twice size: half widths 128 at row 1240, about 110 at 1280,
    # 80 at 1300, 45 at 1315 (a broad round chin), an ellipse's quarter from the jaw's angles to the chin's bottom; the
    # old V (32 at the chin) made the narrow long jaw the critic read as "a goblin or a little old man")
    tj = np.clip((rr - JAW_ANGLE[0]) / (CHIN_ROW + 2 - JAW_ANGLE[0]), 0, 1)
    want = np.maximum(JAW_ANGLE[1] * np.sqrt(np.clip(1.0 - tj ** 2.2, 0, 1)), CHIN_HALF * 0.9) * HS
    have = np.array([np.abs(P[lower & (np.abs(rows_p - r) < 6), 0]).max() if (lower & (np.abs(rows_p - r) < 6)).any() else np.nan for r in rr])
    k = np.clip(box_smooth(fill_nan(want / have), 4), 0.55, 1.25)
    t = smooth01(JAW_ANGLE[0] - 15, JAW_ANGLE[0] + 5, rows_p)
    kk = 1.0 + (np.interp(rows_p, rr, k) - 1.0) * t
    P[lower, 0] *= kk[lower]
    print("BOY jaw: rows %d to %d narrowed by %.2f to %.2f" % (rr[0], rr[-1], k.min(), k.max()))
    if HEAD2:
        # (eleventh pass) the base's ears folded flat into the skull (a smooth skin over their roots); the bundle's ear
        # is set on after the subdivision (finish_head2)
        E0 = edges_of(faces)
        root = np.zeros(len(P), bool)
        for a, b in E0:
            if ear[a] != ear[b]:
                root[a] = root[b] = True
        flat = ear & ~root
        P = membrane(P, E0, flat)
        P = symmetric(P, mir)
        tris_all = tris_of(faces)
        stage("3_ears", P, faces)
        n, _ = folded(P, faces)
        print("BOY head (cage): the base's ears folded flat (%d points); %d triangles folded" % (int(flat.sum()), n))
        eye = list(HB_EYE)
        no_ear = np.zeros(len(P), bool)
        return {"P": P, "faces": faces, "uvs": uvs, "ear": no_ear, "hole": hole, "marks": marks, "eye": eye, "mir": mir,
                "tris": tris_all, "tris_head": tris_all, "edges": edges_of(faces), "cage": True, "old_ear": flat}
    # 3. the ears, sized to the sheet's: top, lobe, front and back (side view), how far they stand out (front view)
    for sgn in (1.0, -1.0):
        e = ear & (np.sign(P[:, 0]) == sgn)
        zt, zb = float(hz(EAR_ROWS[0])), float(hz(EAR_ROWS[1]))
        yf, yb = side_y(EAR_COLS[0]), side_y(EAR_COLS[1])
        Q = P[e]
        root = np.array([any(not ear[u] for u in nb[v]) for v in np.where(e)[0]])
        kz = (zt - zb) / (Q[:, 2].max() - Q[:, 2].min())
        ky = (yb - yf) / (Q[:, 1].max() - Q[:, 1].min())
        cz, cyy = (Q[:, 2].max() + Q[:, 2].min()) / 2, (Q[:, 1].max() + Q[:, 1].min()) / 2
        tz, ty = (zt + zb) / 2, (yf + yb) / 2
        w = np.where(root, 0.5, 1.0)
        nz = cz + (Q[:, 2] - cz) * kz + (tz - cz)
        ny = cyy + (Q[:, 1] - cyy) * ky + (ty - cyy)
        Q[:, 2] = Q[:, 2] + (nz - Q[:, 2]) * w
        Q[:, 1] = Q[:, 1] + (ny - Q[:, 1]) * w
        # stand-out: the sheet's front view (with ears) against the head's outline (no ears), at the ear's middle
        rmid = int((EAR_ROWS[0] + EAR_ROWS[1]) / 2)
        runs = run_near(sh.head_mask, rmid, HVIEW["hfront"][1], *HSPAN["hfront"])
        out_t = (runs[1] + 1 - runs[0]) / 2.0 * HS
        head_half = np.abs(P[~ear & (np.abs(P[:, 2] - float(hz(rmid))) < 0.01), 0]).max()
        reach = np.abs(Q[:, 0]).max() - head_half
        want = out_t - head_half
        kx_ = want / max(reach, 1e-4)
        off = np.abs(Q[:, 0]) - head_half
        Q[:, 0] = sgn * (head_half + np.where(off > 0, off * (1 + (kx_ - 1) * w), off))
        P[e] = Q
        print("BOY ear: height x%.2f, depth x%.2f, stand-out x%.2f (to %.3f m from his middle)" % (kz, ky, kx_, out_t))
    P = symmetric(P, mir)
    n, _ = folded(P, faces)
    print("BOY head after the landmarks, rows and ears: %d triangles folded" % n)
    stage("3_ears", P, faces)
    # 4. the face (brow to under the chin, facing forward) and the ears split once
    F4 = [np.array(f) for f in faces]
    hole_set = set(hole)
    sel = []
    split_kind = [0, 0, 0]
    for fi, f in enumerate(faces):
        c = P[f].mean(0)
        nn = face_normal(P, f)
        nn = nn / max(np.linalg.norm(nn), 1e-12)
        r = float(hrow(c[2]))
        if hole_set & set(f):
            continue
        # (fourth pass: and the crown, whose few big faces showed as facets and a pinch on top)
        if ear[f].all() or (HR(870) <= r <= HR(1172) and nn[1] < SPLIT_FACING) or (SPLIT_CROWN and nn[2] > 0.5 and r < HR(860)):
            sel.append(fi)
            split_kind[0 if ear[f].all() else 1 if nn[1] < SPLIT_FACING else 2] += 1
    print("BOY head split: ears %d, face %d, crown %d faces" % tuple(split_kind))
    P, faces, uvs, fl, old = subdivide_some(P, faces, uvs, {"ear": ear.astype(float)}, sel)
    ear = fl["ear"] > 0.75
    hole = [int(old[v]) for v in hole]
    marks = {k: int(old[v]) for k, v in marks.items()}
    eye = [int(old[v]) for v in HB_EYE]
    mir = mirror_pairs(P, 1e-4)
    P = symmetric(P, mir)
    # the ears rounded (the base's are five-sided blocks): smoothed but for the ring joining them to the head
    E = edges_of(faces)
    root = np.zeros(len(P), bool)
    for a, b in E:
        if ear[a] != ear[b]:
            root[a] = root[b] = True
    P = smooth_points(P, E, ear & ~root, rounds=int(arg("--ear-smooth", "18")))
    P = symmetric(P, mir)
    P = round_ears(P, ear, root, mir, faces)
    stage("4_split", P, faces)
    print("BOY head split: %d faces split, %d points, %d triangles" % (len(sel), len(P), len(tris_of(faces))))
    tris_all = tris_of(faces)
    tris_head = [t for t in tris_all if not ear[list(t)].any()]
    edges = edges_of(faces)
    n, _ = folded(P, faces)
    print("BOY head after the split: %d triangles folded" % n)
    return {"P": P, "faces": faces, "uvs": uvs, "ear": ear, "hole": hole, "marks": marks, "eye": eye, "mir": mir,
            "tris": tris_all, "tris_head": tris_head, "edges": edges}


# (fourth pass) The face made a thirteen-year-old's: the base's closed-lid sockets filled into shallow eyes with a round
# eyeball under the lid, the brow ridge softened, round full cheeks added as forms, the lips flattened a little.
# The coordinator, of the third pass: "THE FACE READS TOO OLD AND TOO MALE ... deep closed-lid eye sockets, heavy
# brow ... flat cheeks". Each: (reach, amount) in metres; --young 0 turns it off.
YOUNG = float(arg("--young", "1.0"))
YOUNG_SOCKET = (0.017, 14)        # the socket filled: reach, rounds of smoothing
YOUNG_EYEBALL = (0.009, 0.001)   # the eyeball's bulge under the lid
YOUNG_BROW = (0.014, 14)          # the brow ridge softened
YOUNG_CHEEK = (float(arg("--cheek-reach", "0.024")), float(arg("--cheek", "0.0085")))     # the cheeks' fullness (seventh pass: from 0.021, 0.0055: "full round apple cheeks ... 5-8 mm outward")
MOUTH_NARROW = float(arg("--mouth-narrow", "0.14"))   # (seventh pass) the corners drawn in: 70 to 60 head-sheet pixels out
NOSE_WIDE = float(arg("--nose-wide", "0.3"))
SOFTEN = float(arg("--soften", "1.0"))
CHEEK_LOW = float(arg("--cheek-low", "0.005"))
YOUNG_LIPS = (0.015, float(arg("--lips-back", "0.0015")))   # (seventh pass: from 0.004, which cut a band across his mouth)      # the lips drawn back


def young_face(P, Hd, movable):
    if YOUNG <= 0:
        return P
    P = np.array(P, float)
    E = Hd["edges"]
    tris = Hd["tris"]
    mir = Hd["mir"]
    mk = Hd["marks"]
    eye_l = P[Hd["eye"]].mean(0)
    eyes = [eye_l, eye_l * np.array((-1.0, 1.0, 1.0))]
    keep = ~movable | Hd["ear"]

    def near(c, r):
        return np.exp(-(np.linalg.norm(P - c, axis=1) / r) ** 2)

    def lap(P, w, rounds, lam=0.5):
        deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
        for _ in range(rounds):
            acc = np.zeros_like(P)
            np.add.at(acc, E[:, 0], P[E[:, 1]])
            np.add.at(acc, E[:, 1], P[E[:, 0]])
            avg = acc / np.maximum(deg, 1)[:, None]
            P = P + (avg - P) * (lam * w)[:, None]
            P[keep] = P0[keep]
        return P
    P0 = P.copy()
    # sockets filled (smoothing pushes a hollow out), most at the eye's middle
    w = np.maximum(*[near(c, YOUNG_SOCKET[0]) for c in eyes]) * YOUNG
    P = lap(P, np.clip(w * 1.3, 0, 1), YOUNG_SOCKET[1])
    # the brow ridge softened (above each eye)
    w = np.maximum(*[near(c + np.array((0.0, 0.0, 0.015)), YOUNG_BROW[0]) for c in eyes]) * YOUNG
    P = lap(P, w, YOUNG_BROW[1])
    N = normals_of(P, tris)
    # the eyeball under the lid, round; the cheeks full and round (below and outside each eye, on the surface)
    w = np.maximum(*[near(c, YOUNG_EYEBALL[0]) for c in eyes])
    P = P + N * (w * YOUNG_EYEBALL[1] * YOUNG)[:, None]
    for s, c in ((1.0, eyes[0]), (-1.0, eyes[1])):
        at = c + np.array((s * 0.008, 0.0, -0.026))
        # (the surface's point nearest that, seen from the front)
        cand = np.where(~Hd["ear"] & (P[:, 1] < c[1] + 0.02))[0]
        cc = P[cand[np.argmin(np.linalg.norm((P[cand] - at)[:, [0, 2]], axis=1))]]
        P = P + N * (near(cc, YOUNG_CHEEK[0]) * YOUNG_CHEEK[1] * YOUNG)[:, None]
    # the lips back a little and smoothed
    cm = P[mk["mouth"]]
    w = near(cm, YOUNG_LIPS[0]) * YOUNG
    P[:, 1] += w * YOUNG_LIPS[1]
    P = lap(P, w * 0.6, 6)
    # (sixth pass; the critic: "a horizontal shelf below the lower lip, so the mouth sits on a boxy muzzle ... make the
    # jawline from ear to chin one continuous curve") the hollow between lower lip and chin filled forward, then the
    # mouth, chin and jaw's lower edge smoothed together
    lo, ch = P[mk["lip_low"]], P[mk["chin"]]
    mid = lo * 0.45 + ch * 0.55
    w = near(mid, 0.017) * (P[:, 1] < mid[1] + 0.012) * YOUNG
    P[:, 1] -= w * float(arg("--ledge", "0.0026"))
    w2 = np.maximum(near(mid, 0.02), near(ch, 0.03) * 0.8) * YOUNG
    P = lap(P, np.clip(w2, 0, 1) * 0.5, 4)
    # (seventh pass; the critic: "a smaller, closed, soft smile ... narrower (inside the pupils' width) ... a fuller,
    # defined, pinkish lower lip ... corners tucked in"; "a round, upturned button nose ... widen the tip and alae by
    # about 30%, round the tip into a ball and tilt it up")
    if MOUTH_NARROW > 0:
        cl = P[mk["mouth_l"]]
        xc = abs(float(cl[0]))
        zm = float(P[mk["mouth"], 2])
        front = P[:, 1] < float(P[mk["mouth"], 1]) + 0.016
        w = np.exp(-((P[:, 2] - zm) / 0.0085) ** 2) * (1.0 - smooth01(xc, xc + 0.014, np.abs(P[:, 0]))) * front
        P[:, 0] *= 1.0 - MOUTH_NARROW * w * smooth01(0.0, xc, np.abs(P[:, 0]))
        lo = P[mk["lip_low"]]
        w = near(lo + np.array((0.0, 0.0, -0.002)), 0.008) * front
        P[:, 1] -= w * 0.0011
    if NOSE_WIDE > 0:
        tip = P[mk["nose"]].copy()
        base = P[mk["nose_base"]].copy()
        w = np.exp(-(np.linalg.norm((P - (tip * 0.6 + base * 0.4)) * np.array((0.7, 1.0, 1.0)), axis=1) / 0.012) ** 2)
        w *= P[:, 1] < tip[1] + 0.02
        P[:, 0] *= 1.0 + NOSE_WIDE * w
        # the tip's underside lifted (an upturn) and the ball of the tip a little rounder forward
        under = smooth01(tip[2] + 0.002, base[2], P[:, 2])
        P[:, 2] += w * under * 0.0018
        P[:, 1] -= near(tip, 0.006) * 0.0007
    P = lap(P, np.clip(near(P[mk["mouth"]], 0.02) + near(P[mk["nose"]], 0.012), 0, 1) * 0.3, 2)
    if SOFTEN > 0:
        # (seventh pass; the critic: "painted nasolabial creases", "a visible step or crease running across the chin",
        # "the cheeks are flat, even slightly hollow under the cheekbone") the lower face softened as a whole (lips'
        # seam and the nose kept), then the cheeks filled low and outward of the mouth too, as the sheet's round face
        cm_ = P[mk["mouth"]]
        ch_ = P[mk["chin"]]
        lowf = np.maximum(near(cm_ * 0.5 + ch_ * 0.5, 0.03), np.maximum(*[near(c + np.array((s * 0.012, 0.0, -0.04)), 0.025) for s, c in ((1.0, eyes[0]), (-1.0, eyes[1]))]))
        guard = 1.0 - 0.85 * np.maximum(near(cm_, 0.006), near(P[mk["nose"]], 0.014))
        P = lap(P, np.clip(lowf * guard * SOFTEN, 0, 1) * 0.5, 10)
        N = normals_of(P, tris)
        for s, c in ((1.0, eyes[0]), (-1.0, eyes[1])):
            at = c + np.array((s * 0.016, 0.0, -0.042))
            cand = np.where(~Hd["ear"] & (P[:, 1] < c[1] + 0.02))[0]
            cc = P[cand[np.argmin(np.linalg.norm((P[cand] - at)[:, [0, 2]], axis=1))]]
            P = P + N * (near(cc, 0.02) * CHEEK_LOW)[:, None]
    P[keep] = P0[keep]
    P = symmetric(P, mir, keep=keep)
    n, _ = folded(P, Hd["faces"])
    dm = np.linalg.norm(P - P0, axis=1)
    iw = int(np.argmax(dm))
    print("BOY young face: most moved %.1f mm (at %s, from %s); %d triangles folded" % (1000 * float(dm.max()), np.round(P[iw], 3), np.round(P0[iw], 3), n))
    return P


def side_warp_final(P, Hd, sh):
    """(seventh pass) Measured against the bald side view row by row, the fitted head sat 0.6 to 0.9 cm too far
    forward (its back of the skull 16 pixels short of the sheet's, its brow 11 pixels proud), so the occiput did not
    overhang the neck (the critic: "a light-bulb shape with no occipital shelf"). Each point moved front to back by its
    height, so the skull's front (crown to brow) and back (crown to the nape) land on the sheet's; below the brow the
    face keeps its shape and moves with the brow's row, below the nape the back moves with the nape's row."""
    P = np.array(P, float)
    rr = np.arange(int(H_CROWN) + 8, NAPE_ROW + 1)
    m = view_mask(P, Hd["tris"], "hside", sh.head_mask.shape)
    mid = HVIEW["hside"][1]
    c0, c1 = HSPAN["hside"]
    ys = np.full((len(rr), 4), np.nan)
    for i, r in enumerate(rr):
        a = run_near(m, r, mid, c0, c1)
        b = run_near(sh.head_mask, r, mid, c0, c1)
        if a and b:
            ys[i] = (side_y(a[1] + 1), side_y(a[0]), side_y(b[1] + 1), side_y(b[0]))
            if r > 1050:
                ys[i, 0] = ys[i, 2] = np.nan
    for k in range(4):
        ys[:, k] = box_smooth(fill_nan(ys[:, k]), 4)
    r = np.clip(hrow(P[:, 2]), rr[0], rr[-1])
    fm, bm_, ft, bt = (np.interp(r, rr, ys[:, j]) for j in range(4))
    Q = P.copy()
    Q[:, 1] = ft + (P[:, 1] - fm) * (bt - ft) / np.maximum(bm_ - fm, 1e-6)
    # (s_curve carries all above his chest 6 mm forward afterwards: the head is set back by as much here)
    Q[:, 1] += 0.006 * S_CURVE
    d = Q[:, 1] - P[:, 1]
    print("BOY side warp (final): front %.1f mm, back %.1f mm at the widest; moved %.1f to %.1f mm" % (
        1000 * float(np.nanmean(ys[:, 2] - ys[:, 0])), 1000 * float(np.nanmean(ys[:, 3] - ys[:, 1])), 1000 * d.min(), 1000 * d.max()))
    n, _ = folded(Q, Hd["faces"])
    print("BOY head after the side warp: %d triangles folded" % n)
    return Q


def fit_made_head(Hd, sh, rounds):
    """The made head pulled onto the bald row's outlines in all five views (the 3/4 views at the angles the build
    found for them), its ears left as sized, the hole's ring kept still."""
    P = Hd["P"]
    movable = ~Hd["ear"]
    movable[Hd["hole"]] = False
    if Hd.get("cage"):
        return fit_cage_head(Hd, sh, rounds, movable)
    views = {"hfront": sh.head_target, "hside": sh.head_mask, "hback": sh.head_target}
    P = outline_fit(P, Hd["tris"], movable, views, sh, rounds=rounds, mir=Hd["mir"], edges=Hd["edges"],
                    no_ears_tris=Hd["tris_head"], label="head (front, side, back)", head=True, spread=16)
    fit_angled_model([(P, Hd["tris"], ["head"] * len(Hd["tris"]))], sh)
    views = {"hq": sh.head_mask, "hqb": sh.head_mask, "hfront": sh.head_target, "hside": sh.head_mask,
             "hback": sh.head_target}
    P = outline_fit(P, Hd["tris"], movable, views, sh, rounds=max(2, rounds // 2), mir=Hd["mir"], edges=Hd["edges"],
                    no_ears_tris=Hd["tris_head"], label="head (all five)", step=0.003, head=True, spread=16)
    sel = movable.copy()
    P = smooth_points(P, Hd["edges"], sel, rounds=2)
    P = symmetric(P, Hd["mir"], keep=~movable)
    n, _ = folded(P, Hd["faces"])
    print("BOY head after the outline fit: %d triangles folded" % n)
    P = young_face(P, Hd, movable)
    P = side_warp_final(P, Hd, sh)
    stage("5_fit", P, Hd["faces"])
    Hd["P"] = P
    return Hd


CAGE_SPREAD = int(arg("--cage-spread", "3"))


def fit_cage_head(Hd, sh, rounds, movable):
    """(eleventh pass) The cage fitted to the bald row's outlines (front, side, back, then all five), a gentle side warp,
    then subdivided once and given the bundle's ears (finish_head2). The forms are added after (head_forms)."""
    P = Hd["P"]
    views = {"hfront": sh.head_target, "hside": sh.head_mask, "hback": sh.head_target}
    P = outline_fit(P, Hd["tris"], movable, views, sh, rounds=rounds, mir=Hd["mir"], edges=Hd["edges"],
                    no_ears_tris=Hd["tris_head"], label="cage (front, side, back)", head=True, spread=CAGE_SPREAD,
                    step=0.003)
    fit_angled_model([(P, Hd["tris"], ["head"] * len(Hd["tris"]))], sh)
    views = {"hq": sh.head_mask, "hqb": sh.head_mask, "hfront": sh.head_target, "hside": sh.head_mask,
             "hback": sh.head_target}
    P = outline_fit(P, Hd["tris"], movable, views, sh, rounds=max(2, rounds // 2), mir=Hd["mir"], edges=Hd["edges"],
                    no_ears_tris=Hd["tris_head"], label="cage (all five)", step=0.002, head=True, spread=CAGE_SPREAD)
    n, _ = folded(P, Hd["faces"])
    print("BOY cage after the outline fit: %d triangles folded" % n)
    P = side_warp_final(P, Hd, sh)
    stage("5_cage", P, Hd["faces"])
    Hd["P"] = P
    Hd = finish_head2(Hd, sh)
    if "--freeze-head" in ARGS:
        save_head_base(Hd)
    return Hd


HEAD_BASE_FILE = os.path.join(HERE, "blend", "boy_head_base.npz")
HEAD_FROZEN = HEAD2 and "--refit-head" not in ARGS and "--freeze-head" not in ARGS and os.path.exists(HEAD_BASE_FILE)


def save_head_base(Hd):
    """(eleventh pass) The fitted, subdivided head saved as it stands, before its adjustments: later builds start from
    exactly this mesh (HEAD_FROZEN) instead of fitting the base mesh again. Remade only with --freeze-head."""
    F = Hd["faces"]
    np.savez_compressed(HEAD_BASE_FILE, P=np.asarray(Hd["P"], float), F=np.concatenate([np.asarray(f) for f in F]),
                        FS=np.array([len(f) for f in F]), U=np.array([q for u in Hd["uvs"] for q in u], float),
                        hole=np.array(Hd["hole"]), eye=np.array(Hd["eye"]), strip=np.array(Hd["eye_strip"]),
                        old_ear=np.asarray(Hd["old_ear"]), marks=json.dumps({k: int(v) for k, v in Hd["marks"].items()}))
    print("BOY head base saved: %s (%d points, %d faces)" % (HEAD_BASE_FILE, len(Hd["P"]), len(F)))


def load_head_base():
    d = np.load(HEAD_BASE_FILE)
    faces, uvs, k = [], [], 0
    U = d["U"]
    for n in d["FS"]:
        faces.append([int(v) for v in d["F"][k:k + n]])
        uvs.append([tuple(q) for q in U[k:k + n]])
        k += n
    Hd = {"P": d["P"].copy(), "faces": faces, "uvs": uvs, "hole": [int(v) for v in d["hole"]], "eye": [int(v) for v in d["eye"]],
          "eye_strip": [int(v) for v in d["strip"]], "old_ear": d["old_ear"], "marks": {k_: int(v) for k_, v in json.loads(str(d["marks"])).items()}}
    print("BOY head base loaded (frozen): %s, %d points, %d faces" % (HEAD_BASE_FILE, len(Hd["P"]), len(faces)))
    return Hd


FORMS = float(arg("--head-forms", "1.0"))
JAW_PLANE = float(arg("--jaw-plane", "0.8"))       # share of the way the under-jaw is lifted onto its plane
JAW_RISE = float(arg("--jaw-rise", "0.25"))         # the plane's rise toward the throat (metres a metre back)
CHEEK_APPLE = float(arg("--apple", "0.0045"))
CHIN_BALL = float(arg("--chin-ball", "0.0028"))
NOSE_BALL = float(arg("--nose-ball", "0.0022"))
LIP_FULL = (float(arg("--lip-up", "0.0")), float(arg("--lip-low", "0.0")))   # (dropped: before/after pairs showed only more lumps at the mouth, not the sheet's lips)
SMILE_CORNER = float(arg("--smile-corner", "0.0"))   # (dropped: the dents read as lumps)
FACE_ROUND = float(arg("--face-round", "0.0"))   # (dropped: no visible change in the pairs)
UNSUB_BACK = float(arg("--unsub-back", "0.0"))   # metres behind the head's middle where the skull is un-subdivided (0: off) (off: merged faces across the head's UV seams drew streaks of other paint on the scalp)


def head_forms(P, faces, Hd, hole):
    """(eleventh pass) The forms the sheet draws, added to the subdivided base head as soft fields, each on its own
    landmarks: the under-jaw lifted onto a plane from the chin's underside to the throat (so a jawline runs from the
    chin to below the ear and the neck meets it at an angle; the critic: "the jaw runs straight into the neck"); round
    cheek apples under and outside each eye; a small round chin; a ball on the nose's tip; a soft upper lip and a
    fuller lower one, the corners tucked in and up. Then two gentle Taubin rounds over the face."""
    if FORMS <= 0:
        return P
    P = np.array(P, float)
    mk = Hd["marks"]
    tris = tris_of(faces)
    N = normals_of(P, tris)
    E = edges_of(faces)
    mir = mirror_pairs(P, 1e-4)
    P0 = P.copy()

    def near(c, r, scale=(1.0, 1.0, 1.0)):
        return np.exp(-(np.linalg.norm((P - c) * np.array(scale), axis=1) / r) ** 2)
    eye_l = P[Hd["eye"]].mean(0)
    chin = P[mk["chin"]].copy()
    hole_c = P[hole].mean(0)
    # 1. the under-jaw: points facing down, in front of the neck's hole's middle and above its front, raised onto a
    # plane through the chin's underside rising JAW_RISE toward his back; the jaw's angles below the ear included
    zc = float(chin[2])
    under = (N[:, 2] < -0.25) & (P[:, 1] < hole_c[1] + 0.01) & (P[:, 2] < float(P[mk["mouth"], 2]) - 0.01)
    zp = zc + (P[:, 1] - chin[1]) * JAW_RISE
    lift = np.clip(zp - P[:, 2], 0.0, 0.03)
    soft = smooth01(-0.25, -0.6, N[:, 2])
    hold = np.zeros(len(P), bool)
    hold[hole] = True
    w = under * soft * ~hold
    P[:, 2] += lift * w * JAW_PLANE * FORMS
    n_under = int((w > 0.3).sum())
    # 2. cheek apples, on the surface's normal
    for s in (1.0, -1.0):
        e = eye_l * np.array((s, 1.0, 1.0))
        c = e + np.array((s * 0.009, -0.004, -0.026))
        P += N * (near(c, 0.017, (1.0, 1.4, 1.0)) * CHEEK_APPLE * FORMS)[:, None]
    # 3. the chin: a small ball just above its underside
    c = P0[mk["lip_low"]] * 0.35 + chin * 0.65
    P += N * (near(c, 0.011) * CHIN_BALL * FORMS)[:, None]
    # 4. the nose's ball, a little forward and up
    tip = P0[mk["nose"]]
    w = near(tip + np.array((0.0, 0.0, -0.002)), 0.0075)
    P += N * (w * NOSE_BALL * FORMS)[:, None]
    P[:, 2] += w * 0.0008 * FORMS
    # 5. the lips: the upper's soft roll, the lower fuller, the corners in and up (an upturned closed smile)
    mo = P0[mk["mouth"]]
    lu, ll = P0[mk["lip_up"]], P0[mk["lip_low"]]
    P += N * (near(lu * 0.7 + mo * 0.3, 0.008, (0.7, 1.0, 1.4)) * LIP_FULL[0] * FORMS)[:, None]
    P += N * (near(ll * 0.7 + mo * 0.3, 0.008, (0.7, 1.0, 1.4)) * LIP_FULL[1] * FORMS)[:, None]
    for s, key in ((1.0, "mouth_l"), (-1.0, "mouth_r")):
        cm = P0[mk[key]]
        w = near(cm, 0.006)
        P -= N * (w * SMILE_CORNER * FORMS)[:, None]
        P[:, 2] += w * SMILE_CORNER * 0.6 * FORMS
    # 6. (the grey front read as a narrow front plane between steep flat cheeks: the critic's "boxy lower face") the
    # lower face's cross-section rounded: each point between the face's middle and its outline brought forward by a
    # share of the arc between, most half way out, from below the eyes to the chin
    if FACE_ROUND > 0:
        z = P[:, 2]
        zt_, zb_ = float(hz(1120.0)), float(hz(1290.0))
        band = smooth01(zb_ - 0.01, zb_ + 0.02, z) * (1.0 - smooth01(zt_ - 0.015, zt_ + 0.01, z))
        cy_ = float(np.median(P[(np.abs(z - (zt_ + zb_) / 2) < 0.03), 1]))
        front = P[:, 1] < cy_
        hw = np.zeros(len(P))
        for i in np.where(front & (band > 0.01))[0]:
            m_ = (np.abs(z - z[i]) < 0.006) & front & (P[:, 1] < P[i, 1] + 0.06)
            hw[i] = np.abs(P[m_, 0]).max()
        u = np.clip(np.abs(P[:, 0]) / np.maximum(hw, 1e-4), 0, 1)
        P[:, 1] -= FACE_ROUND * FORMS * band * front * np.sin(math.pi * u) ** 1.5 * (hw > 0)
    # gentle evening over the face (not the hole's ring)
    face = (P0[:, 1] < hole_c[1] - 0.02) & ~hold
    P = smooth_points(P, E, face, rounds=2)
    P = symmetric(P, mir, keep=hold)
    n, _ = folded(P, faces)
    dm = np.linalg.norm(P - P0, axis=1)
    print("BOY head forms: under-jaw %d points lifted (most %.1f mm), most moved %.1f mm; %d folded" % (
        n_under, 1000 * float((lift * (under * soft)).max()), 1000 * float(dm.max()), n))
    return P


def finish_head2(Hd, sh):
    # the base's closed lids: the strip of quads between the lids' meeting rows, round each eye (HB_EYE and its mirror);
    # their children after the subdivision are what open_eyes2 takes out
    cf = Hd["faces"]
    el = set(HB_EYE)
    er = {int(Hd["mir"][v]) for v in HB_EYE}
    starts = np.concatenate([[0], np.cumsum([len(f) for f in cf])])
    strip = [fi for fi, f in enumerate(cf) if all(v in el for v in f) or all(v in er for v in f)]
    Hd["eye_strip"] = [int(j) for fi in strip for j in range(starts[fi], starts[fi + 1])]
    print("BOY eyes: the base's closed lids are %d quads (%d after the subdivision)" % (len(strip), len(Hd["eye_strip"])))
    P, faces, uvs, fl, ept = cc_subdivide(Hd["P"], Hd["faces"], Hd["uvs"], {"old_ear": Hd["old_ear"]})
    hole = []
    h = Hd["hole"]
    for i in range(len(h)):
        a, b = h[i], h[(i + 1) % len(h)]
        hole += [a, ept[(min(a, b), max(a, b))]]
    Hd.update({"P": P, "faces": faces, "uvs": uvs, "hole": hole})
    return Hd


def head_adjust(Hd, sh):
    """(eleventh pass; the user: "you should just be making adjustments") The frozen head (finish_head2, or the saved
    copy, HEAD_BASE_FILE) given its named adjustments in order (head_forms), then the bundle's ears."""
    P, faces, uvs, hole = np.array(Hd["P"], float), [list(f) for f in Hd["faces"]], [list(u) for u in Hd["uvs"]], list(Hd["hole"])
    nh = len(P)
    tris = tris_of(faces)
    P = head_forms(P, faces, Hd, hole)
    Qe, fe, ue = place_ears(P, sh, tris)
    ear_faces = []
    base = len(P)
    P = np.concatenate([P, Qe, Qe * np.array((-1.0, 1.0, 1.0))])
    ne = len(Qe)
    for f, u in zip(fe, ue):
        faces.append([base + v for v in f])
        uvs.append(list(u))
    for f, u in zip(fe, ue):
        faces.append([base + ne + v for v in f][::-1])
        uvs.append(list(u)[::-1])
    ear = np.zeros(len(P), bool)
    ear[nh:] = True
    mir = mirror_pairs(P, 1e-4)
    P = symmetric(P, mir)
    tris = tris_of(faces)
    tris_head = [t for t in tris if not ear[list(t)].any()]
    n, _ = folded(P, faces)
    print("BOY head subdivided: %d points, %d faces, %d triangles (ears %d); hole ring %d; %d folded" % (
        len(P), len(faces), len(tris), len(tris) - len(tris_head), len(hole), n))
    Hd.update({"P": P, "faces": faces, "uvs": uvs, "ear": ear, "hole": hole, "mir": mir, "tris": tris,
               "tris_head": tris_head, "edges": edges_of(faces), "cage": False, "ear_points": (nh, nh + ne, nh + 2 * ne)})
    return Hd


NECK_DEEP = float(arg("--neck-deep", "1.0"))
NECK_SMOOTH = int(arg("--neck-smooth", "12"))
NECK_SMOOTH_REACH = float(arg("--neck-smooth-reach", "0.02"))


def neck_ellipses(Pm, rings, sh):
    """(eleventh pass; the critic: "from behind, the neck is a wide funnel with vertical ridges (two tendon-like fins)")
    The neck's middle rings made smooth ellipses (front and back halves of their own depth) at the sheet's width,
    throat and nape for their heights, their points at the head's hole ring's angles round it (so nothing twists
    between them); the ridges were corners in the rings, left where the rings were scaled half by half."""
    top = Pm[rings[-1]]
    ct = top.mean(0)
    th = np.arctan2(top[:, 0] - ct[0], -(top[:, 1] - ct[1]))
    for ri, rg in enumerate(rings[1:-1]):
        Q = Pm[rg]
        c = Q.mean(0)
        z = float(Q[:, 2].mean())
        a = float(np.abs(Q[:, 0] - c[0]).max())
        bf = float(c[1] - Q[:, 1].min())
        bb = float(Q[:, 1].max() - c[1])
        r_ = float(hrow(z))
        run = run_near(sh.head_target, int(r_), HVIEW["hfront"][1], *HSPAN["hfront"])
        if run and r_ > JAW_ROW + 30:
            a = (run[1] + 1 - run[0]) / 2.0 * HS * NECK_THIN
        sd = run_near(sh.head_mask, int(r_), HVIEW["hside"][1], *HSPAN["hside"])
        if sd and r_ > THROAT_ROW:
            F, Bk = side_y(sd[1] + 1), side_y(sd[0])
            mid = (F + Bk) / 2.0
            half = (Bk - F) / 2.0 * NECK_DEEP
            c[1] = mid
            bf = bb = half
        x = c[0] + a * np.sin(th)
        y = c[1] - np.where(np.cos(th) > 0, bf, bb) * np.cos(th)
        Pm[rg, 0] = x
        Pm[rg, 1] = y
        Pm[rg, 2] = z + (Q[:, 2] - z) * 0.5
        print("BOY neck ring %d an ellipse: half width %.3f, front %.3f, back %.3f (row %.0f)" % (ri + 1, a, bf, bb, r_))


def build_head(M, sh, T):
    """(third pass) The base-mesh head on his neck: made and fitted (make_head, fit_made_head), added to the body's
    mesh, and a neck of rings bridging the torso's top ring to the head's hole, leaving the torso along its own
    slope and entering the head straight up, then fitted to the front, side and back views below the jaw."""
    Hd = load_head_base() if HEAD_FROZEN else fit_made_head(make_head(sh), sh, HEAD_FIT_ROUNDS)
    if HEAD2:
        Hd = head_adjust(Hd, sh)
        stage("5_fit", Hd["P"], Hd["faces"])
    P = Hd["P"]
    base = len(M.P)
    M.tag["eye_strip"] = [len(M.faces) + j for j in Hd.get("eye_strip", [])]
    for i, p in enumerate(P):
        M.add(p, ("ear_l" if p[0] > 0 else "ear_r") if Hd["ear"][i] else "head")
    uv = {}
    for f, u in zip(Hd["faces"], Hd["uvs"]):
        part = "head"
        if Hd["ear"][f].all():
            part = "ear_l" if P[f, 0].mean() > 0 else "ear_r"
        M.face([base + i for i in f], part)
        if part != "head" and HEAD2:
            # (eleventh pass) the bundle's ears in islands of their own (their UV map overlaps the head's)
            M.tag.setdefault("ear_uv", {}).setdefault(part, {})[len(M.faces) - 1] = [(a * 0.12, b * 0.12) for a, b in u]
            continue
        uv[len(M.faces) - 1] = [(a * HEAD_UV_M, b * HEAD_UV_M) for a, b in u]
    M.tag["head_uv"] = uv
    M.tag["head_points"] = (base, len(M.P))
    M.tag["head_marks"] = {k: base + v for k, v in Hd["marks"].items()}
    M.tag["head_eye"] = [base + v for v in Hd["eye"]]
    top = [base + v for v in Hd["hole"]]
    bottom = T[-1]
    below = T[-2]
    n = len(top)
    Pb16 = np.array([M.P[i] for i in bottom])
    Pl16 = np.array([M.P[i] for i in below])
    Pt = np.array([M.P[i] for i in top])

    def ring_param(Q):
        """each point's place round a ring (0 at his front middle, rising toward +X), by its angle round the ring's
        middle"""
        c = Q.mean(0)
        a = np.arctan2(Q[:, 0] - c[0], -(Q[:, 1] - c[1])) / math.tau
        return np.mod(a + 1e-9, 1.0)

    def at_param(Q, u):
        """points on a closed ring at places u (linear between its points by angle)"""
        uq = ring_param(Q)
        order = np.argsort(uq)
        us = np.concatenate([uq[order] - 1.0, uq[order], uq[order] + 1.0])
        Qs = np.concatenate([Q[order]] * 3)
        return np.stack([np.interp(u, us, Qs[:, k]) for k in range(3)], 1)
    ut = ring_param(Pt)
    Pb = at_param(Pb16, ut)
    Pl = at_param(Pl16, ut)
    d = np.linalg.norm(Pt - Pb, axis=1, keepdims=True)
    m0 = Pb - Pl
    m0 = m0 / np.linalg.norm(m0, axis=1, keepdims=True) * d * 0.9
    m1 = np.tile(np.array((0.0, 0.0, 1.0)), (n, 1)) * d * 0.9
    rings = []
    for t in (0.0,) + NECK_RINGS:
        h00, h10, h01, h11 = 2 * t ** 3 - 3 * t ** 2 + 1, t ** 3 - 2 * t ** 2 + t, -2 * t ** 3 + 3 * t ** 2, t ** 3 - t ** 2
        Q = h00 * Pb + h10 * m0 + h01 * Pt + h11 * m1
        if t == 0.0:
            # (the neck's lowest ring, a little above the torso's top ring, which it is zipped to)
            Q = Pb + (Pt - Pb) * 0.05
        rings.append([M.add(q, "head") for q in Q])
    rings.append(top)
    for a, b in zip(rings, rings[1:]):
        for k in range(n):
            j = (k + 1) % n
            M.face([a[k], a[j], b[j], b[k]], "neck")
    # the torso's top ring (16 points) zipped to the neck's lowest (24) by their places round the ring
    nb16 = len(bottom)
    ub = ring_param(Pb16)
    i = j = 0
    zip_faces = []
    while i < nb16 or j < n:
        nb_ = ub[(i + 1) % nb16] + (1.0 if i + 1 >= nb16 else 0.0)
        na_ = ut[(j + 1) % n] + (1.0 if j + 1 >= n else 0.0)
        if j < n and (i >= nb16 or na_ <= nb_):
            M.face([bottom[i % nb16], rings[0][(j + 1) % n], rings[0][j % n]], "neck")
            j += 1
        else:
            M.face([bottom[i % nb16], bottom[(i + 1) % nb16], rings[0][j % n]], "neck")
            i += 1
        zip_faces.append(len(M.faces) - 1)
    M.tag["neck_zip"] = zip_faces
    M.tag["neck_rings"] = rings
    # the neck's middle rings fitted to the outlines below the jaw (with the head drawn, so it hides them)
    Pm = np.array(M.P)
    hf = [i for i, p in enumerate(M.fpart) if part_family(p) in ("head", "ear", "neck")]
    faces = [M.faces[i] for i in hf]
    tris = tris_of(faces)
    ear_pts = np.array([part_family(p) == "ear" for p in M.part])
    no_ears = [t for t in tris if not ear_pts[list(t)].any()]
    movable = np.zeros(len(Pm), bool)
    for r in rings[1:-1]:
        movable[r] = True
    mir = mirror_map(Pm)
    views = {"hfront": sh.head_target, "hside": sh.head_mask, "hback": sh.head_target}
    Pm = outline_fit(Pm, tris, movable, views, sh, rounds=12, mir=mir, edges=edges_of(faces), no_ears_tris=no_ears,
                     rows_max=H_NECK + 30, label="neck", neck=True, reach=90, step=0.006)
    # the seam where the neck meets the head (the hole's ring) softened, with a ring of each side
    seam = np.zeros(len(Pm), bool)
    seam[top] = True
    seam[rings[-2]] = True
    E_ = edges_of(faces)
    near = seam.copy()
    for a, b in E_:
        if seam[a] or seam[b]:
            near[a] = near[b] = True
    near &= ~ear_pts
    Pm = smooth_points(Pm, E_, near, rounds=2)
    Pm = symmetric(Pm, mir, keep=~near)
    # (sixth pass; the critic: "the neck reads long and scrawny with drawn cords", "a ridge running down the nape")
    # each middle ring's reach round its middle evened out (the cords and the nape's ridge were bumps in it) and the
    # neck made a little fuller, most at its middle
    for ri, rg in enumerate(rings[1:-1]):
        Q = Pm[rg]
        c = Q.mean(0)
        d = Q[:, :2] - c[:2]
        r = np.linalg.norm(d, axis=1)
        rs = r.copy()
        for _ in range(3):
            rs = (np.roll(rs, 1) + 2 * rs + np.roll(rs, -1)) / 4.0
        t = (ri + 1) / float(len(rings) - 1)
        full = 1.0 + (NECK_FULL - 1.0) * math.sin(math.pi * t)
        Q[:, :2] = c[:2] + d / np.maximum(r, 1e-6)[:, None] * (rs * full)[:, None]
        Pm[rg] = Q
    # (seventh pass; the critic: "the neck is a long, even cylinder, as wide as the jaw ... thin it by about 15%".
    # Measured: the model's neck 186 head-sheet pixels across against the sheet's 147, 185 deep against 155, its back
    # 10 to 15 pixels proud of the sheet's nape) each middle ring set to the sheet's width at its side points' row and
    # to the sheet's throat and nape at its front and back points' rows, where those are the neck's own outline
    for ri, rg in enumerate(rings[1:-1]):
        Q = Pm[rg]
        q4, q2 = len(rg) // 4, len(rg) // 2
        c = Q.mean(0)
        rs_, rf_, rb_ = float(hrow(Q[q4, 2])), float(hrow(Q[0, 2])), float(hrow(Q[q2, 2]))
        run = run_near(sh.head_target, int(rs_), HVIEW["hfront"][1], *HSPAN["hfront"])
        if run and rs_ > JAW_ROW + 30:
            a = float(np.abs(Q[:, 0] - c[0]).max())
            kx_ = float(np.clip((run[1] + 1 - run[0]) / 2.0 * HS * NECK_THIN / max(a, 1e-4), 0.7, 1.1))
            Q[:, 0] = c[0] + (Q[:, 0] - c[0]) * kx_
        else:
            kx_ = 1.0
        ky_ = [1.0, 1.0]
        sf = run_near(sh.head_mask, int(rf_), HVIEW["hside"][1], *HSPAN["hside"])
        sb = run_near(sh.head_mask, int(rb_), HVIEW["hside"][1], *HSPAN["hside"])
        ymin, ymax = float(Q[:, 1].min()), float(Q[:, 1].max())
        if sf and rf_ > CHIN_ROW + 8:
            F = side_y(sf[1] + 1)
            ky_[0] = float(np.clip((c[1] - F) / max(c[1] - ymin, 1e-4), 0.7, 1.1))
        if sb and rb_ > NAPE_ROW + 8:
            Bk = side_y(sb[0])
            ky_[1] = float(np.clip((Bk - c[1]) / max(ymax - c[1], 1e-4), 0.7, 1.1))
        Q[:, 1] = c[1] + (Q[:, 1] - c[1]) * np.where(Q[:, 1] < c[1], ky_[0], ky_[1])
        Pm[rg] = Q
        print("BOY neck ring %d sized to the sheet: across x%.2f, front x%.2f, back x%.2f" % (ri + 1, kx_, ky_[0], ky_[1]))
    if HEAD2:
        neck_ellipses(Pm, rings, sh)
        # the neck's middle rings, the hole's ring behind the jaw and the skull's underside just above it evened
        # together (the rings' corners and the hole's slant had left ridges up the back of the neck)
        E_ = edges_of(faces)
        ct = Pm[top].mean(0)
        sel = np.zeros(len(Pm), bool)
        for r in rings[1:-1]:
            sel[r] = True
        tb = [v for v in top if Pm[v][1] > ct[1] - 0.015]
        sel[tb] = True
        hp = np.array([part_family(p) == "head" for p in M.part[:len(Pm)]] + [False] * max(0, len(Pm) - len(M.part)))
        Ptb = Pm[tb]
        dmin = np.array([np.linalg.norm(Ptb - p, axis=1).min() for p in Pm])
        sel |= hp & (dmin < NECK_SMOOTH_REACH) & (Pm[:, 1] > ct[1] - 0.01) & ~ear_pts
        Pm = smooth_points(Pm, E_, sel, rounds=NECK_SMOOTH)
        Pm = symmetric(Pm, mir, keep=~sel)
        print("BOY neck evened: %d points, %d rounds" % (int(sel.sum()), NECK_SMOOTH))
    M.P = [p for p in Pm]
    n, _ = folded(Pm, faces)
    for ri, rg in enumerate(rings):
        Q = Pm[rg]
        q4, q2 = len(rg) // 4, len(rg) // 2
        print("BOY neck ring %d: front row %.0f y %.3f, side x %.3f row %.0f, back row %.0f y %.3f" % (ri, hrow(Q[0, 2]), Q[0, 1], Q[q4, 0], hrow(Q[q4, 2]), hrow(Q[q2, 2]), Q[q2, 1]))
    print("BOY head and neck: %d triangles (%d folded)" % (len(tris), n))
    used = sorted({v for f in faces for v in f})
    remap = {v: i for i, v in enumerate(used)}
    stage("6_neck", Pm[used], [[remap[v] for v in f] for f in faces])
    M.tag["head_rings"] = None
    return Hd


# ------------------------------------------------------------------------------------------------------------------
# The hands (third pass): Blender Studio's "Hand - Stylized" (a right hand, fingers down, its back toward -Y, its
# thumb toward +X), un-subdivided once, cut at the wrist, sized and fitted to the hands sheet's back and palm views
# finger by finger (each finger's spread, length and width searched against the filled outlines), given joints and a
# relaxed rest pose, then put on each forearm's last ring. Its coordinates while fitting are the hand's own:
# a along it from the wrist's crease, t across toward the thumb, b out of its back.
# ------------------------------------------------------------------------------------------------------------------

HAND_SCALE = 1.15          # (fifth pass) the new sheet draws him big hands: 0.195 m wrist to fingertip
HAND_LEN = 0.175         # the wrist's crease to the middle fingertip (the hands sheet's 670 pixels at the body's size)
HAND_CREASE_Z = 0.365     # the base hand's wrist crease (its own height; its forearm stub runs on up to 0.403)
HAND_RING_A = 0.006       # where the hand's open ring sits past the forearm's last ring (metres along the hand)
HAND_UV_M = 0.3           # metres a unit of the base hand's UV map
HAND_THUMB_T = 0.045      # the palm's edge on the thumb's side (the hand's own t): beyond it, the thumb
HAND_WEB_A = 0.1          # past the webs between the fingers (the hand's own a): the fingers stand apart there
HAND_DEPTH = float(arg("--hand-depth", "1.2"))
HAND_REST = {"curl": (0.15, 0.21, 0.13), "spread": 0.7, "thumb_in": float(arg("--thumb-in", "-0.12")), "thumb_fwd": float(arg("--thumb-fwd", "0.05")), "thumb_curl": 0.16}   # (seventh pass: a relaxed curl, index about 12 degrees a joint to the little finger about 30; the thumb 20 degrees out of the palm)
# (sixth pass; the critic: the thumb "hangs below the hand as a separate dangling nub": turned in under the palm by
# 0.45 and forward by 0.3 it hung under the palm; now it lies beside the index, a little in front, as the sheet hangs it)
# (fourth pass) the curl grows from the index to the little finger, as a relaxed hand hangs (the critic: "the index
# finger straightest and the little finger most curled")
HAND_CASCADE = {"index": 0.75, "middle": 1.0, "ring": 1.3, "little": 1.6}
HAND_COLLAPSE = float(arg("--hand-collapse", "0.4"))   # (tenth pass) the full base hand collapsed to this share; 0: un-subdivided as before
HAND_TAUBIN = int(arg("--hand-taubin", "5"))            # (tenth pass) Taubin rounds over the fitted hand (its wrist loop kept)
HAND = {}
FRAME_ID = (np.array((0.0, 0.0, 1.0)), np.array((0.0, 1.0, 0.0)), np.array((1.0, 0.0, 0.0)))   # (back, across, along)


def rot(axis, ang):
    return np.array(Matrix.Rotation(float(ang), 3, Vector(axis)))


def pose_points(Lc, chains, angs):
    """Linear blend skinning of the hand's own points: chains[name] = (joints (3), weights (n,4: palm and three
    segments), axes per joint); angs[name] = the three joints' turns (radians)."""
    out = Lc * 0.0
    wsum = np.zeros(len(Lc))
    for name, (J, W4, axes) in chains.items():
        Rs, ts = [np.eye(3)], [np.zeros(3)]
        R, t = np.eye(3), np.zeros(3)
        for j in range(3):
            Rj = rot(axes[j], angs[name][j])
            o = np.asarray(J[j])
            t = R @ (o - Rj @ o) + t
            R = R @ Rj
            Rs.append(R.copy())
            ts.append(t.copy())
        for k in range(4):
            w = W4[:, k]
            if k == 0:
                continue
            out += w[:, None] * (Lc @ Rs[k].T + ts[k])
            wsum += w
    out += (1.0 - wsum)[:, None] * Lc
    return out


KNUCKLE_ROW = {} if "--no-knuckle-row" in ARGS else {"index": 0.002, "ring": 0.003, "little": 0.009}


def hand_chains(Lc, faces, thumb, fingers):
    """Joints (local), skinning weights and flexing axes of each finger and the thumb, from their points."""
    chains = {}
    back = np.array((0.0, 0.0, 1.0))
    todo = list(fingers.items()) + [("thumb", thumb)]
    if KNUCKLE_ROW and "middle" in fingers:
        # (ninth pass) the middle finger first, then the others' roots set on the knuckle row behind it
        todo.sort(key=lambda x: x[0] != "middle")
    for name, idx in todo:
        Q = Lc[idx]
        c = Q.mean(0)
        u = np.linalg.svd(Q - c)[2][0]
        if name == "thumb":
            if (Q[np.argmax((Q - c) @ u)] - Lc.mean(0)) @ u < (Q[np.argmin((Q - c) @ u)] - Lc.mean(0)) @ u:
                u = -u
        elif u[0] < 0:
            u = -u
        s = (Q - c) @ u
        tip = c + u * s.max()
        vis = s.max() - s.min()
        L = vis / (0.78 if name != "thumb" else 0.62)
        if KNUCKLE_ROW and name in KNUCKLE_ROW and "middle" in chains and abs(u[0]) > 0.3:
            # (ninth pass) the knuckles on a row that falls away from the middle finger's toward the little finger's,
            # as a hand's do (the little finger's root had come out the furthest forward of the four)
            want_a = float(chains["middle"][4][0][0]) - KNUCKLE_ROW[name]
            L = max(L * 0.8, float((tip[0] - want_a) / u[0]))
        segs = FINGER_SEGS if name != "thumb" else (0.42, 0.32, 0.26)
        root = tip - u * L
        J = [root, root + u * L * segs[0], root + u * L * (segs[0] + segs[1]), tip]
        ax = np.cross(u, back)
        ax /= np.linalg.norm(ax)
        if np.cross(ax, u) @ back > 0:
            ax = -ax
        sp = Lc - root
        sall = sp @ u
        lat = np.linalg.norm(sp - np.outer(sall, u), axis=1)
        W4 = np.zeros((len(Lc), 4))
        mine = np.zeros(len(Lc), bool)
        mine[idx] = True
        reach = 0.012 if name != "thumb" else 0.016
        near = mine | ((sall > -0.012) & (lat < reach))
        for v in np.where(near)[0]:
            w = chain_weights(sall[v], ["p", "1", "2", "3"], [0.006 if name != "thumb" else 0.01, L * segs[0],
                                                              L * (segs[0] + segs[1])], 0.006)
            if not mine[v]:
                k = float(smooth01(-0.012, 0.004, sall[v])) * float(1 - smooth01(reach * 0.6, reach, lat[v]))
                w = {kk: vv * k for kk, vv in w.items() if kk != "p"}
            W4[v] = [w.get("p", 0.0), w.get("1", 0.0), w.get("2", 0.0), w.get("3", 0.0)]
        chains[name] = (J[:3], W4, [ax, ax, ax], u, J, L)
    return chains


def hand_view_mask(view, Lc, tris, sh, keep):
    uv, dep = hand_uv(view, Lc, FRAME_ID)
    shape = sh.hand_mask.shape
    tgt = sh.hand_mask & keep
    if view == "back":
        col0 = HANDV["back"]["wrist"]
        band = (uv[:, 0] > 0.006 / HANDV[view]["k"]) & (uv[:, 0] < 0.03 / HANDV[view]["k"])
        rows = np.where(tgt[:, col0 + 40])[0]
        off = np.array((col0, rows.mean() - uv[band, 1].mean()))
    else:
        row0 = HANDV["palm"]["wrist"]
        band = (uv[:, 1] < -0.006 / HANDV[view]["k"]) & (uv[:, 1] > -0.03 / HANDV[view]["k"])
        cols = np.where(tgt[row0 - 40])[0]
        off = np.array((cols.mean() - uv[band, 0].mean(), row0))
    zb, _ = raster(uv + off, dep, tris, shape)
    m = np.isfinite(zb) & keep
    return m, tgt


def hand_outline_fit(Lc, faces, sh, keep, rounds=6, step=0.002, damp=0.7):
    """The open hand's outline points moved (in its own a, t plane) onto the hands sheet's back and palm outlines,
    the moves spread to their neighbours: what the finger-by-finger search could not reach."""
    tris = tris_of(faces)
    E = edges_of(faces)
    deg = np.bincount(E.ravel(), minlength=len(Lc)).astype(float)
    for rnd in range(rounds):
        move = np.zeros_like(Lc)
        cnt = np.zeros(len(Lc))
        for view in ("back", "palm"):
            kk = HANDV[view]["k"]
            m, tgt = hand_view_mask(view, Lc, tris, sh, keep[view])
            uv, _ = hand_uv(view, Lc, FRAME_ID)
            # (the placement hand_view_mask used, found again from the drawn mask's agreement)
            if view == "back":
                col0 = HANDV["back"]["wrist"]
                band = (uv[:, 0] > 0.006 / kk) & (uv[:, 0] < 0.03 / kk)
                rows = np.where(tgt[:, col0 + 40])[0]
                off = np.array((col0, rows.mean() - uv[band, 1].mean()))
            else:
                row0 = HANDV["palm"]["wrist"]
                band = (uv[:, 1] < -0.006 / kk) & (uv[:, 1] > -0.03 / kk)
                cols = np.where(tgt[row0 - 40])[0]
                off = np.array((cols.mean() - uv[band, 0].mean(), row0))
            p2 = uv + off
            N = normals_of(Lc, tris)
            # the outline's outward direction in the picture: the normal's (a, t) part, as the view draws it
            d2 = np.stack([N[:, 0], N[:, 1]], 1) if view == "back" else np.stack([N[:, 1], -N[:, 0]], 1)
            L_ = np.linalg.norm(d2, axis=1)
            ok = (np.abs(N[:, 2]) < 0.6) & (L_ > 0.3)
            h, w = tgt.shape
            for v in np.where(ok)[0]:
                p = p2[v]
                dn = d2[v] / L_[v]
                q = p + dn * 3
                if not (0 <= int(q[1]) < h and 0 <= int(q[0]) < w) or m[int(q[1]), int(q[0])]:
                    continue
                pi = (int(p[1]), int(p[0]))
                if not (0 <= pi[0] < h and 0 <= pi[1] < w) or not keep[view][pi]:
                    continue
                dist = None
                if tgt[pi]:
                    for s in range(1, 30):
                        qq = p + dn * s
                        if not tgt[min(max(int(qq[1]), 0), h - 1), min(max(int(qq[0]), 0), w - 1)]:
                            dist = s - 0.5
                            break
                else:
                    for s in range(1, 30):
                        qq = p - dn * s
                        if tgt[min(max(int(qq[1]), 0), h - 1), min(max(int(qq[0]), 0), w - 1)]:
                            dist = -(s - 0.5)
                            break
                if dist is None:
                    continue
                da = dn[0] * dist * kk if view == "back" else -dn[1] * dist * kk
                dt = dn[1] * dist * kk if view == "back" else dn[0] * dist * kk
                move[v] += (da, dt, 0.0)
                cnt[v] += 1
        has = cnt > 0
        move[has] /= cnt[has, None]
        ln = np.linalg.norm(move, axis=1, keepdims=True)
        move *= np.minimum(1.0, step / np.maximum(ln, 1e-9))
        D = move.copy()
        W = has * 4.0
        for _ in range(6):
            acc = np.zeros_like(D)
            np.add.at(acc, E[:, 0], D[E[:, 1]])
            np.add.at(acc, E[:, 1], D[E[:, 0]])
            D = (W[:, None] * move + acc) / np.maximum(W + deg, 1e-9)[:, None]
        D[Lc[:, 0] < 0.012] = 0.0
        Lc = Lc + D * damp
    return Lc


def dissolve_finger_rings(Lc, faces, uvs):
    """In each finger (the points beyond the webs, apart from the thumb, found as make_hand finds them) the ring of
    four points nearest the middle of its middle bone dissolved (bmesh: its four edges and points), UVs kept."""
    E = edges_of(faces)
    nbr = [[] for _ in range(len(Lc))]
    for a, b in E:
        nbr[a].append(b)
        nbr[b].append(a)
    Lw = Lc.copy()
    # (the wrist's open ring's middle as a = HAND_RING_A, as make_hand puts it)
    ec = {}
    for f in faces:
        for i in range(len(f)):
            e = (min(f[i], f[(i + 1) % len(f)]), max(f[i], f[(i + 1) % len(f)]))
            ec[e] = ec.get(e, 0) + 1
    rim = sorted({v for e, c in ec.items() if c == 1 for v in e})
    Lw[:, 0] += HAND_RING_A - Lw[rim, 0].mean()
    thumb_ok = Lw[:, 1] > HAND_THUMB_T

    def comp(seed, ok):
        seen, st = {seed}, [seed]
        while st:
            v = st.pop()
            for u in nbr[v]:
                if ok[u] and u not in seen:
                    seen.add(u)
                    st.append(u)
        return np.array(sorted(seen))
    thumb = comp(int(np.argmax(Lw[:, 1])), thumb_ok)
    ok = (Lw[:, 0] > HAND_WEB_A) & ~np.isin(np.arange(len(Lw)), thumb)
    left = set(np.where(ok)[0].tolist())
    rings = []
    while left:
        c = comp(left.pop(), ok)
        left -= set(c.tolist())
        if len(c) <= 6:
            continue
        Q = Lw[c]
        u = np.linalg.svd(Q - Q.mean(0))[2][0]
        if u[0] < 0:
            u = -u
        s = (Q - Q.mean(0)) @ u
        L = (s.max() - s.min()) / 0.78
        pip = s.max() - L + L * FINGER_SEGS[0]
        dip = pip + L * FINGER_SEGS[1]
        order = np.argsort(s)
        groups, cur = [], [order[0]]
        for i, j in zip(order, order[1:]):
            if s[j] - s[i] > 0.004:
                groups.append(cur)
                cur = []
            cur.append(j)
        groups.append(cur)
        best = None
        for g in groups:
            if len(g) != 4:
                continue
            m = float(s[g].mean())
            if min(abs(m - pip), abs(m - dip)) < 0.004:
                continue
            d = abs(m - (pip + dip) / 2.0)
            if best is None or d < best[0]:
                best = (d, [int(c[k]) for k in g])
        if best:
            rings.append(best[1])
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    vs = [bm.verts.new(Vector(p)) for p in Lc]
    for f, uv in zip(faces, uvs):
        bf = bm.faces.new([vs[i] for i in f])
        for l_, q in zip(bf.loops, uv):
            l_[uvl].uv = q
    bm.verts.index_update()
    gone = []
    for r in rings:
        rs = set(r)
        gone += [e for e in bm.edges if e.verts[0].index in rs and e.verts[1].index in rs]
    bmesh.ops.dissolve_edges(bm, edges=gone, use_verts=True)
    bm.verts.index_update()
    Ln = np.array([v.co[:] for v in bm.verts])
    Fn = [[v.index for v in f.verts] for f in bm.faces]
    Un = [[tuple(l_[uvl].uv) for l_ in f.loops] for f in bm.faces]
    bm.free()
    print("BOY hand: %d finger rings dissolved (%d edges): %d triangles, from %d" % (
        len(rings), len(gone), len(tris_of(Fn)), len(tris_of(faces))))
    return Ln, Fn, Un


FINGER_SPLIT = "--no-finger-split" not in ARGS
FINGER_TAPER = float(arg("--finger-taper", "0.15"))
THUMB_ROUND = (float(arg("--thumb-across", "0.8")), float(arg("--thumb-through", "1.1")))
FINGER_RATIO = {"index": 0.92, "middle": 1.0, "ring": 0.93, "little": 0.76}
KNUCKLE = (float(arg("--knuckle", "0.0022")), 0.0012)
SIX_SIDES = float(arg("--six", "0.8"))   # (ninth pass) 0: every edge round a digit cut (eight to ten sides)
FINGER_THIN = float(arg("--finger-thin", "0.85"))   # (tenth pass) the fingers made this much as thick round their own axes


def split_fingers(Lc, faces, uvs, groups):
    """(seventh pass; the critic: "fat, nearly equal-length sausages with blunt, faceted, hexagonal ends ... remodel
    each finger as a 6-sided tube tapering about 25% to a rounded, domed tip") Each finger's and the thumb's edges
    running round it cut once at their middles (rounded out with the surface), so each digit is twice as many sides
    round and no longer along it: its tubes go from four or five sides to eight or ten for about 300 triangles a
    hand. groups: name -> point numbers. Gives (Lc, faces, uvs, groups renumbered, the old points' new numbers)."""
    bm = bmesh.new()
    lay = {k: bm.verts.layers.float.new(k) for k in groups}
    uvl = bm.loops.layers.uv.new("UVMap")
    vs = [bm.verts.new(Vector(p)) for p in Lc]
    for k, idx in groups.items():
        for i in idx:
            vs[i][lay[k]] = 1.0
    for f, uv in zip(faces, uvs):
        bf = bm.faces.new([vs[i] for i in f])
        for l_, q in zip(bf.loops, uv):
            l_[uvl].uv = q
    bm.normal_update()
    cut = []
    bm.verts.index_update()
    for k, idx in groups.items():
        Q = Lc[idx]
        u = np.linalg.svd(Q - Q.mean(0))[2][0]
        s_ = set(int(i) for i in idx)
        for e in bm.edges:
            a, b = e.verts[0].index, e.verts[1].index
            if a in s_ and b in s_:
                d = Lc[b] - Lc[a]
                if abs(float(d @ u)) < 0.55 * float(np.linalg.norm(d)):
                    if SIX_SIDES:
                        # (ninth pass, the budget: only the edges across the back and the palm cut, so a four-sided
                        # tube becomes six-sided, not eight: the edge's own direction lies across the finger, its
                        # middle out from the finger's line toward the back or the palm)
                        c0 = Q.mean(0)
                        m = (Lc[a] + Lc[b]) / 2.0 - c0
                        m = m - (m @ u) * u
                        mn = float(np.linalg.norm(m))
                        if mn < 1e-9 or abs(float(m[2])) / mn < SIX_SIDES:
                            continue
                    cut.append(e)
    bmesh.ops.subdivide_edges(bm, edges=list(set(cut)), cuts=1, use_grid_fill=True, use_single_edge=False, smooth=0.0,
                              quad_corner_type="INNER_VERT")
    ngons = [f for f in bm.faces if len(f.verts) > 4]
    if ngons:
        bmesh.ops.triangulate(bm, faces=ngons)
    bm.verts.index_update()
    Pn = np.array([v.co[:] for v in bm.verts])
    Fn = [[v.index for v in f.verts] for f in bm.faces]
    Un = [[tuple(l_[uvl].uv) for l_ in f.loops] for f in bm.faces]
    G = {k: np.array([i for i, v in enumerate(bm.verts) if v[lay[k]] > 0.75]) for k in groups}
    # (the grid fill put a point in the middle of each end cap and the rounding pushed it out into a spike: each
    # digit's furthest point set back to the middle of the points round it)
    nb = {}
    for f in Fn:
        for i in range(len(f)):
            nb.setdefault(f[i], set()).update((f[i - 1], f[(i + 1) % len(f)]))
    # (the cut points put round each digit's axis at the radius of the old points beside them along it, so each
    # tube is round; a cap's middle point, whose neighbours are all new, put on the axis just past them)
    kd0 = kdtree.KDTree(len(Pn))
    for i, p in enumerate(Pn):
        kd0.insert(Vector(p), i)
    kd0.balance()
    is_old = np.zeros(len(Pn), bool)
    for p in Lc:
        is_old[kd0.find(Vector(p))[1]] = True
    for k, idx in G.items():
        oi = idx[is_old[idx]]
        Q = Pn[oi]
        c = Q.mean(0)
        u = np.linalg.svd(Q - c)[2][0]
        so = (Q - c) @ u
        ro = np.linalg.norm((Q - c) - np.outer(so, u), axis=1)
        new = idx[~is_old[idx]]
        for v in new:
            s = float((Pn[v] - c) @ u)
            if all(not is_old[w] for w in nb[v]):
                continue
            near_ = np.abs(so - s) < 0.003
            if near_.sum() < 2:
                continue
            perp = (Pn[v] - c) - s * u
            r = float(np.linalg.norm(perp))
            if r > 1e-6:
                Pn[v] = c + s * u + perp / r * float(ro[near_].mean())
        for v in new:
            if all(not is_old[w] for w in nb[v]):
                ring_ = Pn[list(nb[v])]
                m = ring_.mean(0)
                s_ = (ring_ - c) @ u
                rr = float(np.linalg.norm((ring_ - m) - np.outer((ring_ - m) @ u, u), axis=1).mean())
                out = np.sign(float(np.mean(s_) - np.median(so))) or 1.0
                Pn[v] = m + u * out * rr * 0.45
    bm.free()
    kd = kdtree.KDTree(len(Pn))
    for i, p in enumerate(Pn):
        kd.insert(Vector(p), i)
    kd.balance()
    old = np.array([kd.find(Vector(p))[1] for p in Lc])
    print("BOY hand: %d edges round the digits cut: %d triangles, from %d" % (len(set(cut)), len(tris_of(Fn)), len(tris_of(faces))))
    return Pn, Fn, Un, G, old


def shape_digits(Lc, chains, fingers, thumb, tag=""):
    """(seventh pass, after the brother's shape_fingers) On the fitted open hand (a along it, t across toward the
    thumb, b out of its back): each finger tapered toward its tip (FINGER_TAPER at the tip's root, round its own axis),
    the lengths set to a hand's (middle 1, index and ring 0.92, little 0.76: the critic) by moving each finger's points
    along its axis, knuckle bumps on the back over each finger's root and middle joints."""
    Lc = np.array(Lc, float)
    mid_len = None
    for name in ("middle", "index", "ring", "little", "thumb"):
        idx = fingers[name] if name != "thumb" else thumb
        J = chains[name][4]
        root, tip = np.asarray(J[0], float), np.asarray(J[3], float)
        u = tip - root
        L = float(np.linalg.norm(u))
        u /= L
        d = Lc[idx] - root
        s = d @ u
        perp = d - np.outer(s, u)
        t = np.clip(s / L, 0, 1)
        k = 1.0 - (FINGER_TAPER if name != "thumb" else FINGER_TAPER * 0.6) * smooth01(0.15, 0.85, t)
        if name == "middle":
            mid_len = L
            kl = 1.0
        elif name == "thumb":
            kl = 1.0
        else:
            kl = min(1.0, FINGER_RATIO[name] * mid_len / L)
        # (the length change grows along the finger from its root, so the palm's web stays put)
        s2 = s * (1.0 + (kl - 1.0) * smooth01(0.0, 0.3 * L, s))
        if name == "thumb":
            # (the base's thumb is a flat paddle in the palm's plane: narrower across, a little fuller through)
            bk = np.array((0.0, 0.0, 1.0))
            bk = bk - (bk @ u) * u
            bk /= np.linalg.norm(bk)
            pb = perp @ bk
            perp = (perp - np.outer(pb, bk)) * THUMB_ROUND[0] + np.outer(pb, bk) * THUMB_ROUND[1]
        # (tenth pass; the critic: "thin each finger about 20-25%": they were 2 cm through, a grown man's)
        k = k * (FINGER_THIN if name != "thumb" else 0.5 + 0.5 * FINGER_THIN)
        Lc[idx] = root + np.outer(s2, u) + perp * k[:, None]
        # the tip clipped to a half ellipsoid round its axis (the brother's shape_fingers): a domed fingertip, the
        # cap's corners drawn in, nothing pushed out
        js2 = np.asarray(J[2], float)
        d = u
        a = np.cross(np.array((0.0, 0.0, 1.0)), d)
        a /= np.linalg.norm(a)
        b = np.cross(d, a)
        Q = Lc[idx] - js2
        s = Q @ d
        ra, rb = Q @ a, Q @ b
        s_tip = float(s.max())
        band = (s > s_tip - 0.02) & (s < s_tip - 0.008)
        if band.sum() >= 4:
            ca, cb = float(ra[band].mean()), float(rb[band].mean())
            Ra = float(np.abs(ra[band] - ca).max())
            Rb = float(np.abs(rb[band] - cb).max())
            La = min(Ra, Rb) * 1.1
            s0 = s_tip - La
            q = np.stack([np.clip(s - s0, 0, None) / La, (ra - ca) / Ra, (rb - cb) / Rb], 1)
            r = np.linalg.norm(q, axis=1)
            kk = np.where((s > s0) & (r > 1.0), 1.0 / np.maximum(r, 1e-9), 1.0)
            s_n = np.where(s > s0, s0 + (s - s0) * kk, s)
            Lc[idx] = js2 + s_n[:, None] * d + (ca + (ra - ca) * kk)[:, None] * a + (cb + (rb - cb) * kk)[:, None] * b
    bump = np.zeros(len(Lc))
    for name in FINGERS:
        J = chains[name][4]
        for j, (h, rad) in enumerate(((KNUCKLE[0], 0.009), (KNUCKLE[1], 0.006))):
            jp = np.asarray(J[j], float)
            dist = np.linalg.norm((Lc - jp)[:, :2], axis=1)
            on_back = np.clip((Lc[:, 2] - jp[2]) / 0.003, 0, 1)
            bump = np.maximum(bump, h * np.exp(-(dist / rad) ** 2) * on_back)
    Lc[:, 2] += bump
    print("BOY hand digits shaped%s: tapered %.0f%%, lengths to the middle's %s, knuckles %.1f mm" % (
        tag, FINGER_TAPER * 100, FINGER_RATIO, 1000 * float(bump.max())))
    return Lc


TIP_CAP = float(arg("--tip-cap", "0.0075"))


def round_tips(Lc, faces, chains, fingers, thumb):
    """(sixth pass; the critic: fingertips cut flat or pointed) Each finger's last TIP_CAP of length drawn in toward
    its axis on a quarter circle, so it ends in a round pad, not a flat cut; then that cap smoothed a little."""
    Lc = np.array(Lc, float)
    sel = np.zeros(len(Lc), bool)
    for name, idx in list(fingers.items()) + [("thumb", thumb)]:
        J = chains[name][4]
        a = np.asarray(J[3]) - np.asarray(J[2])
        a /= np.linalg.norm(a)
        d = Lc[idx] - np.asarray(J[2])
        t = d @ a
        tmax = t.max()
        cap = TIP_CAP * (1.25 if name == "thumb" else 1.0)
        s = np.clip((t - (tmax - cap)) / cap, 0, 1)
        perp = d - np.outer(t, a)
        # (eighth pass: a blunter dome; the critic still saw pointed curled tips: the very end pulled back a little and
        # the cap's sides kept fuller, from 0.5 + 0.5 sqrt(1 - s^2))
        k = np.sqrt(np.clip(1.0 - s ** 2, 0.0, 1.0)) * 0.32 + 0.68
        k = np.where(s > 0, k, 1.0)
        t = t - 0.3 * cap * smooth01(0.75, 1.0, s)
        Lc[idx] = np.asarray(J[2]) + np.outer(t, a) + perp * k[:, None]
        sel[np.asarray(idx)[s > 0]] = True
    Lc = smooth_points(Lc, edges_of(faces), sel, rounds=2)
    print("BOY hand: fingertips rounded (%d points)" % int(sel.sum()))
    return Lc


def make_hand(sh):
    """The base hand made into his: un-subdivided, cut at the wrist, sized, each finger fitted, joints found, and its
    open (the hands sheet's) and rest poses kept in HAND."""
    P0, faces, uvs, _ = load_base(HAND_BASE)
    me = bpy.data.meshes.new("_hand")
    me.from_pydata([tuple(p) for p in P0], [], faces)
    uvl = me.uv_layers.new(name="UVMap")
    for poly, uv in zip(me.polygons, uvs):
        for li, q in zip(poly.loop_indices, uv):
            uvl.data[li].uv = q
    ob = bpy.data.objects.new("_hand", me)
    bpy.context.scene.collection.objects.link(ob)
    if HAND_COLLAPSE > 0:
        # (tenth pass, after the brother's ninth round; the critic: "sausage claws ... the fist shatters into prisms":
        # un-subdivided twice the fingers were four points round, square pegs that splintered when bent. The full base
        # hand collapsed instead: fingers about eight points round, the knuckle loops kept, about 450 triangles a hand)
        mod = ob.modifiers.new("c", "DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = HAND_COLLAPSE
        mod.use_collapse_triangulate = False
    else:
        mod = ob.modifiers.new("u", "DECIMATE")
        mod.decimate_type = "UNSUBDIV"
        mod.iterations = int(arg("--hand-unsub", "2"))
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    m2 = ev.to_mesh()
    P = np.array([v.co[:] for v in m2.vertices])
    faces = [list(p.vertices) for p in m2.polygons]
    u2 = m2.uv_layers[0].data
    uvs = [[tuple(u2[li].uv) for li in p.loop_indices] for p in m2.polygons]
    ev.to_mesh_clear()
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.meshes.remove(me)
    tipz = P[:, 2].min()
    stub = P[:, 2] > HAND_CREASE_Z
    xm, ym = P[stub, 0].mean(), P[stub, 1].mean()
    k = HAND_LEN / (HAND_CREASE_Z - tipz)
    Lc = np.stack([(HAND_CREASE_Z - P[:, 2]) * k, (P[:, 0] - xm) * k, -(P[:, 1] - ym) * k], 1)
    # the forearm stub cut off at the crease: faces with any point behind it go, the rest renumbered
    keepf = [i for i, f in enumerate(faces) if Lc[f, 0].min() >= -0.002]
    used = sorted({v for i in keepf for v in faces[i]})
    re = {v: j for j, v in enumerate(used)}
    faces = [[re[v] for v in faces[i]] for i in keepf]
    uvs = [uvs[i] for i in keepf]
    Lc = Lc[used]
    # (fourth pass) one ring of each finger dissolved, the one in the middle of its middle bone (no joint bends there):
    # 467 triangles to about 435, under the 450 asked for
    if "--no-dissolve" not in ARGS and HAND_COLLAPSE <= 0:
        Lc, faces, uvs = dissolve_finger_rings(Lc, faces, uvs)
    ec = {}
    for f in faces:
        for i in range(len(f)):
            e = (min(f[i], f[(i + 1) % len(f)]), max(f[i], f[(i + 1) % len(f)]))
            ec[e] = ec.get(e, 0) + 1
    adj = {}
    for (a, b), c in ec.items():
        if c == 1:
            adj.setdefault(a, []).append(b)
            adj.setdefault(b, []).append(a)
    start = next(iter(adj))
    ring = [start, adj[start][0]]
    while True:
        c = [v for v in adj[ring[-1]] if v != ring[-2]][0]
        if c == start:
            break
        ring.append(c)
    if HAND_COLLAPSE > 0:
        # (the cut through the collapsed stub leaves a saw-toothed wrist loop: its points brought to one plane)
        Lc[ring, 0] = float(np.median(Lc[ring, 0]))
    Lc[:, 0] += HAND_RING_A - Lc[ring, 0].mean()
    print("BOY hand base: %d points, %d faces (%d triangles) after un-subdividing; its wrist ring %d points (%d loops open)" % (
        len(Lc), len(faces), len(tris_of(faces)), len(ring), len(adj) - len(ring)))
    E = edges_of(faces)
    nbr = [[] for _ in range(len(Lc))]
    for a, b in E:
        nbr[a].append(b)
        nbr[b].append(a)

    def component(seed, ok):
        seen = {seed}
        stack = [seed]
        while stack:
            v = stack.pop()
            for u in nbr[v]:
                if ok[u] and u not in seen:
                    seen.add(u)
                    stack.append(u)
        return np.array(sorted(seen))
    # the thumb: the points out beyond the palm's thumb-side edge, grown from the furthest
    thumb = component(int(np.argmax(Lc[:, 1])), Lc[:, 1] > HAND_THUMB_T)
    a_web = HAND_WEB_A
    ok = (Lc[:, 0] > a_web) & ~np.isin(np.arange(len(Lc)), thumb)
    left = set(np.where(ok)[0].tolist())
    comps = []
    while left:
        c = component(left.pop(), ok)
        left -= set(c.tolist())
        if len(c) > 6:
            comps.append(c)
    comps.sort(key=lambda c: -Lc[c, 1].mean())
    print("BOY hand base: thumb %d points, fingers %s points" % (len(thumb), [len(c) for c in comps]))
    fingers = dict(zip(FINGERS, comps[:4]))
    if FINGER_SPLIT and HAND_COLLAPSE <= 0:
        groups = dict(fingers)
        groups["thumb"] = thumb
        Lc, faces, uvs, G, old = split_fingers(Lc, faces, uvs, groups)
        ring = [int(old[v]) for v in ring]
        thumb = G["thumb"]
        fingers = {n: G[n] for n in FINGERS}
    tris = tris_of(faces)
    keep = {v: hand_keep(v, sh.hand_mask.shape) for v in ("back", "palm")}

    def err(L_):
        e = 0
        for v in ("back", "palm"):
            m, t = hand_view_mask(v, L_, tris, sh, keep[v])
            e += int((m ^ t).sum())
        return e
    # sized as a whole first (the sheet's hand against the base's, by area in both views), then finger by finger
    best = (err(Lc), 1.0)
    for s in (0.94, 0.97, 1.03, 1.06):
        e = err(Lc * s)
        if e < best[0]:
            best = (e, s)
    Lc = Lc * best[1]
    Lc[:, 0] += HAND_RING_A - Lc[ring, 0].mean()
    print("BOY hand sized x%.2f: %d pixels differ" % (best[1], best[0]))
    chains = hand_chains(Lc, faces, thumb, fingers)

    def apply(L_, name, spread, length, width):
        J, W4, axes, u, Jall, Lf = chains[name]
        root = Jall[0]
        w = W4[:, 1:].sum(1)
        d = L_ - root
        s = d @ u
        perp = d - np.outer(s, u)
        q = root + np.outer(s * length, u) + perp * width
        q = (q - root) @ rot((0.0, 0.0, 1.0), spread).T + root
        return L_ + (q - L_) * w[:, None]
    e0 = err(Lc)
    for rnd in range(3):
        for name in ("thumb",) + FINGERS:
            for param, values in (("spread", np.radians(np.arange(-32, 33, 4.0))), ("length", (0.88, 0.94, 1.0, 1.06, 1.12)),
                                  ("width", (0.85, 0.92, 1.0, 1.08, 1.16))):
                trials = []
                for val in values:
                    kw = {"spread": 0.0, "length": 1.0, "width": 1.0}
                    kw[param] = val
                    L2 = apply(Lc, name, **kw)
                    trials.append((err(L2), float(val), L2))
                e, val, L2 = min(trials, key=lambda x: x[0])
                Lc = L2
        chains = hand_chains(Lc, faces, thumb, fingers)
        print("BOY hand fit round %d: %d pixels differ (from %d)" % (rnd + 1, err(Lc), e0))
    e1 = err(Lc)
    Lc = hand_outline_fit(Lc, faces, sh, keep)
    # (thicker through, back to palm: the sheet's relaxed side view draws a fuller hand than the base's; the back
    # and palm views do not see this)
    Lc[:, 2] *= HAND_DEPTH
    chains = hand_chains(Lc, faces, thumb, fingers)
    Lc = round_tips(Lc, faces, chains, fingers, thumb)
    chains = hand_chains(Lc, faces, thumb, fingers)
    Lc = shape_digits(Lc, chains, fingers, thumb)
    if HAND_TAUBIN > 0:
        # (tenth pass, as the brother's hand_taubin: the outline fit moves outline points one by one and the collapsed
        # mesh is uneven; Taubin rounds, which do not shrink, even it out; the wrist loop stays where the arm meets it)
        sel = np.ones(len(Lc), bool)
        sel[ring] = False
        before = Lc.copy()
        Lc = smooth_points(Lc, edges_of(faces), sel, rounds=HAND_TAUBIN)
        print("BOY hand evened: %d Taubin rounds, most a point moved %.1f mm" % (HAND_TAUBIN, 1000 * float(np.linalg.norm(Lc - before, axis=1).max())))
    chains = hand_chains(Lc, faces, thumb, fingers)
    print("BOY hand outline fit: %d pixels differ (from %d)" % (err(Lc), e1))
    n, _ = folded(Lc, faces)
    print("BOY hand open: %d triangles folded" % n)
    # the rest pose: fingers curled and drawn together, the thumb turned in under the palm and curled
    mid = chains["middle"][3]
    angs = {}
    pre = Lc.copy()
    for name in FINGERS:
        u = chains[name][3]
        phi = math.atan2(u[1], u[0]) - math.atan2(mid[1], mid[0])
        pre = apply(pre, name, -phi * (1.0 - HAND_REST["spread"]), 1.0, 1.0)
    rchains = hand_chains(pre, faces, thumb, fingers)
    J, W4, axes, u, Jall, Lf = rchains["thumb"]
    tw = W4[:, 1:].sum(1)
    tip0 = np.asarray(Jall[3]) - Jall[0]
    sgi = -1.0 if (tip0 @ rot((1.0, 0.0, 0.0), 0.1).T)[2] > tip0[2] else 1.0
    q = (pre - Jall[0]) @ rot((1.0, 0.0, 0.0), sgi * HAND_REST["thumb_in"]).T + Jall[0]
    pre = pre + (q - pre) * tw[:, None]
    # (and swung toward the fingers, as the sheet's relaxed side view hangs it under the palm's middle)
    tip = np.asarray(Jall[3])
    sgn = 1.0 if ((tip - Jall[0]) @ rot((0.0, 1.0, 0.0), 0.1).T)[0] > (tip - Jall[0])[0] else -1.0
    q = (pre - Jall[0]) @ rot((0.0, 1.0, 0.0), sgn * HAND_REST["thumb_fwd"]).T + Jall[0]
    pre = pre + (q - pre) * tw[:, None]
    rchains = hand_chains(pre, faces, thumb, fingers)
    for name in FINGERS:
        angs[name] = tuple(c * HAND_CASCADE[name] for c in HAND_REST["curl"])
    angs["thumb"] = (HAND_REST["thumb_curl"],) * 3
    rest = pose_points(pre, {n: rchains[n][:3] for n in rchains}, angs)
    n2, _ = folded(rest, faces)
    print("BOY hand rest: %d triangles folded" % n2)
    joints_rest = {}
    for name in FINGERS + ("thumb",):
        J, W4, axes, u, Jall, Lf = rchains[name]
        Rs, ts = [np.eye(3)], [np.zeros(3)]
        R, t = np.eye(3), np.zeros(3)
        pts = [np.asarray(Jall[0])]
        for j in range(3):
            Rj = rot(axes[j], angs[name][j])
            o = np.asarray(J[j])
            t = R @ (o - Rj @ o) + t
            R = R @ Rj
            pts.append(R @ np.asarray(Jall[j + 1]) + t)
        joints_rest[name] = pts
    joints_open = {n: [np.asarray(p) for p in chains[n][4]] for n in chains}
    part = np.array(["palm"] * len(Lc), dtype=object)
    for name, idx in fingers.items():
        part[idx] = name
    part[thumb] = "thumb"
    # (fifth pass) the ball of the thumb (thenar pad): the palm swelled out on its palm side between the thumb's root
    # and the palm's middle, so the thumb grows out of a pad, not off the palm's edge as a tab (the brief, and the
    # critic: "a separate, detached-looking tab"). Measured off the open pose, moved alike in both.
    T0 = np.asarray(joints_open["thumb"][0], float)
    pc = Lc[part == "palm"].mean(0)
    cpad = T0 * 0.55 + pc * 0.45
    near_t = (part == "palm") | ((part == "thumb") & (np.linalg.norm(Lc - T0, axis=1) < 0.018))
    d2 = ((Lc - cpad) ** 2).sum(1)
    w = np.exp(-d2 / 0.028 ** 2) * near_t * (Lc[:, 2] < cpad[2] + 0.01)
    push = np.outer(w, np.array((0.0, 0.0015, -float(arg("--thenar", "0.0085")))))
    Lc = Lc + push
    rest = rest + push
    print("BOY hand: thenar pad on %d points (most %.1f mm)" % (int((w > 0.1).sum()), 1000 * float(np.abs(push).max())))
    HAND.update({"open": Lc, "rest": rest, "faces": faces, "uvs": uvs, "ring": ring, "part": part,
                 "joints": {"open": joints_open, "rest": joints_rest}})
    print("BOY hand: %d triangles" % len(tris))
    return HAND


# ------------------------------------------------------------------------------------------------------------------
# The feet (fifth pass): Blender Studio's "Foot - Stylized" (CC0, the same bundle), as the hands were: its ankle cap
# cut off, un-subdivided once (five toes kept, the big toe apart, the others parted by grooves), sized to the sheet's
# foot (0.23 m heel to toe, the heel 4 cm behind the ankle's middle), put under each leg's last ring and zipped to it.
# The critic of the ring-lofted feet: "boot-like lumps ... no toes ... no arch".
# ------------------------------------------------------------------------------------------------------------------

FOOT_BASE = "Foot - Stylized"
FOOT_LEN = 0.23               # heel to the longest toe's tip (the side view: columns 1301 to 1519)
FOOT_HEEL = 0.034             # the heel's back behind the ankle's middle (the side view: 40 pixels)
FOOT_WIDE = 0.9               # across, against the base's own proportion (his slim feet)
FOOT_RING_Z = float((SOLE - LEG_ROWS[-1]) * S) - 0.014          # the open ankle ring's height once sized (the leg's last ring is zipped to it)
FOOT = {}


TOE_PLUMP = float(arg("--toe-plump", "1.4"))


def plump_toes(L, F):
    """(sixth pass; the critic: "toes read as flat stacked slabs") Each toe (the points forward of where the toes part,
    grouped by which separate toe they belong to) made fuller up and down about its own middle line, and its last 6 mm
    drawn in on a quarter circle so it ends round; the sole kept on the ground; then the toes smoothed a little."""
    L = np.array(L, float)
    E = edges_of(F)
    # (each toe's own front: the furthest point in strips across the foot, so the little toes, set back, count too)
    bins = np.linspace(L[:, 1].min() - 1e-6, L[:, 1].max() + 1e-6, 25)
    bi = np.clip(np.digitize(L[:, 1], bins) - 1, 0, 23)
    fr = np.array([L[bi == i, 0].max() if (bi == i).any() else -1.0 for i in range(24)])
    fr = np.maximum(fr, np.maximum(np.roll(fr, 1), np.roll(fr, -1)))
    umax = fr[bi]
    sep = L[:, 0] > umax - 0.014
    nb = [[] for _ in range(len(L))]
    for a, b in E:
        nb[a].append(b)
        nb[b].append(a)
    lab = -np.ones(len(L), int)
    n = 0
    for s in np.where(sep)[0]:
        if lab[s] >= 0:
            continue
        stack = [s]
        lab[s] = n
        while stack:
            v = stack.pop()
            for u in nb[v]:
                if sep[u] and lab[u] < 0:
                    lab[u] = n
                    stack.append(u)
        n += 1
    cv = np.array([L[lab == i, 1].mean() for i in range(n)])
    zone = (L[:, 0] > umax - 0.04) & (L[:, 0] > L[:, 0].max() - 0.075)
    ramp = smooth01(umax - 0.04, umax - 0.022, L[:, 0])
    sel = np.zeros(len(L), bool)
    for v in np.where(zone)[0]:
        t = lab[v] if lab[v] >= 0 else int(np.argmin(np.abs(cv - L[v, 1])))
        lab[v] = t
    for i in range(n):
        ids = np.where(zone & (lab == i))[0]
        if len(ids) < 4:
            continue
        Q = L[ids]
        w_mid = (Q[:, 2].max() + max(Q[:, 2].min(), 0.0)) / 2.0
        k = 1.0 + (TOE_PLUMP - 1.0) * ramp[ids]
        dw = Q[:, 2] - w_mid
        nw = w_mid + dw * np.where(dw > 0, k, 1.0 + (k - 1.0) * 0.4)
        nw = np.where(Q[:, 2] > 0.0015, np.maximum(nw, 0.0015), Q[:, 2])
        Q[:, 2] = nw
        tmax = Q[:, 0].max()
        cap = 0.006
        s = np.clip((Q[:, 0] - (tmax - cap)) / cap, 0, 1)
        f = np.where(s > 0, np.sqrt(np.clip(1 - s ** 2, 0, 1)) * 0.6 + 0.4, 1.0)
        mv = Q[:, 1].mean()
        Q[:, 1] = mv + (Q[:, 1] - mv) * f
        Q[:, 2] = w_mid + (Q[:, 2] - w_mid) * np.where(Q[:, 2] > w_mid, f, 1.0)
        L[ids] = Q
        sel[ids] = True
    L = smooth_points(L, E, sel & (L[:, 2] > 0.003), rounds=2)
    print("BOY toes plumped: %d toes, %d points" % (n, int(sel.sum())))
    return L


TOE_ROUND = "--no-toe-round" not in ARGS


def round_toes(L, F):
    """(ninth pass; the toes still read as shingles: each toe was a slab four or five points round, flat on top and
    below) The faces of each separate toe (forward of where the toes part) cut once across, so each toe is about twice as
    many points round, and every toe point then put on an ellipse round its own toe's middle line at its own place along
    it: as wide as the toe is there, and at least 0.8 of that tall (the big toe 0.85), its sole kept on the ground; the
    ends then smoothed a little. The same thing the captain's refine_toes does, on this foot's layout. Gives (L, F)."""
    L = np.array(L, float)
    E = edges_of(F)
    bins = np.linspace(L[:, 1].min() - 1e-6, L[:, 1].max() + 1e-6, 25)
    bi = np.clip(np.digitize(L[:, 1], bins) - 1, 0, 23)
    fr = np.array([L[bi == i, 0].max() if (bi == i).any() else -1.0 for i in range(24)])
    fr = np.maximum(fr, np.maximum(np.roll(fr, 1), np.roll(fr, -1)))
    sep = L[:, 0] > fr[bi] - 0.016
    bm = bmesh.new()
    vs = [bm.verts.new(tuple(p)) for p in L]
    for f in F:
        bm.faces.new([vs[i] for i in f])
    bm.verts.index_update()
    cut = [e for e in bm.edges if sep[e.verts[0].index] and sep[e.verts[1].index]
           and abs(e.verts[0].co.x - e.verts[1].co.x) < 0.6 * (e.verts[0].co - e.verts[1].co).length]
    bmesh.ops.subdivide_edges(bm, edges=cut, cuts=1, use_grid_fill=True, smooth=0.0, quad_corner_type="INNER_VERT")
    ng = [f for f in bm.faces if len(f.verts) > 4]
    if ng:
        bmesh.ops.triangulate(bm, faces=ng)
    bm.verts.index_update()
    L2 = np.array([v.co[:] for v in bm.verts])
    F2 = [[v.index for v in f.verts] for f in bm.faces]
    bm.free()
    n_old = len(L)
    E2 = edges_of(F2)
    nb = [[] for _ in range(len(L2))]
    for a, b in E2:
        nb[a].append(b)
        nb[b].append(a)
    bi2 = np.clip(np.digitize(L2[:, 1], bins) - 1, 0, 23)
    sep2 = L2[:, 0] > fr[bi2] - 0.016
    lab = -np.ones(len(L2), int)
    n = 0
    for s in np.where(sep2)[0]:
        if lab[s] >= 0:
            continue
        stack = [s]
        lab[s] = n
        while stack:
            v = stack.pop()
            for u in nb[v]:
                if sep2[u] and lab[u] < 0:
                    lab[u] = n
                    stack.append(u)
        n += 1
    vin = float(L2[:, 1].min())
    moved = 0
    for i in range(n):
        ids = np.where(lab == i)[0]
        if len(ids) < 6:
            continue
        Q = L2[ids]
        big = float(Q[:, 1].mean()) < vin + 0.3 * (float(L2[:, 1].max()) - vin)
        tip = float(Q[:, 0].max())
        root = float(Q[:, 0].min())
        for j, v in enumerate(ids):
            at = L2[v, 0]
            band = np.abs(Q[:, 0] - at) < 0.003
            if band.sum() < 3:
                continue
            B = Q[band]
            vc = (B[:, 1].max() + B[:, 1].min()) / 2.0
            rv = max((B[:, 1].max() - B[:, 1].min()) / 2.0, 1e-4)
            rw = max((B[:, 2].max() - max(B[:, 2].min(), 0.0)) / 2.0, rv * (0.85 if big else 0.8))
            wc = max(B[:, 2].min(), 0.0) + rw
            dv, dw = (L2[v, 1] - vc) / rv, (L2[v, 2] - wc) / rw
            r = math.hypot(dv, dw)
            if r < 1e-6:
                continue
            k = float(smooth01(root, root + 0.006, at))   # (full at the toe, nothing where it leaves the foot)
            nv = vc + dv / r * rv
            nw = wc + dw / r * rw
            L2[v, 1] += (nv - L2[v, 1]) * k
            L2[v, 2] += (max(nw, 0.0) - L2[v, 2]) * k
            moved += 1
    sel = sep2 & (L2[:, 2] > 0.002)
    L2 = smooth_points(L2, E2, sel, rounds=2)
    print("BOY toes rounded: %d toes, %d edges cut, %d points put round; %d points, from %d" % (n, len(cut), moved, len(L2), n_old))
    return L2, F2


FOOT_FLAT = math.radians(float(arg("--foot-flat", "15")))   # (seventh pass: 20 was tried to pay for the fingers: the foot went to a blocky wedge; ninth: 15, to pay for the rounded toes)


def flat_dissolve(L, F, ring, may):
    """(sixth pass, the budget) The foot's nearly flat stretches (the sole, the heel's back, the instep: within
    FOOT_FLAT of flat) merged into larger faces and triangulated again, the toes, the open ankle ring and the outline
    kept (dissolving by angle never moves a point). Gives (points, faces, ring), the ring renumbered."""
    if FOOT_FLAT <= 0:
        return L, F, ring
    bm = bmesh.new()
    oid = bm.verts.layers.int.new("oid")
    vs = [bm.verts.new(tuple(p)) for p in L]
    for i, v in enumerate(vs):
        v[oid] = i
    for f in F:
        try:
            bm.faces.new([vs[i] for i in f])
        except ValueError:
            pass
    bm.verts.index_update()
    bm.normal_update()
    n0 = sum(len(f) - 2 for f in F)
    ring_set = set(ring)
    faces = [f for f in bm.faces if all(may[v.index] for v in f.verts)]
    verts = [v for v in bm.verts if may[v.index] and v.index not in ring_set]
    edges = list({e for f in faces for e in f.edges if all(may[v.index] for v in e.verts) and not any(v.index in ring_set for lf in e.link_faces for v in lf.verts)})
    print("BOY foot dissolve: %d of %d faces, %d points, %d edges may go" % (len(faces), len(bm.faces), len(verts), len(edges)))
    bmesh.ops.dissolve_limit(bm, angle_limit=FOOT_FLAT, verts=verts, edges=edges, delimit=set())
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4], quad_method="BEAUTY", ngon_method="BEAUTY")
    keep = sorted({v[oid] for f in bm.faces for v in f.verts})
    re = {o: j for j, o in enumerate(keep)}
    L2 = np.array([L[o] for o in keep])
    F2 = [[re[v[oid]] for v in f.verts] for f in bm.faces]
    if any(i not in re for i in ring):
        bm.free()
        print("BOY foot: flat stretches NOT merged (the ankle ring would change)")
        return L, F, ring
    ring2 = [re[i] for i in ring]
    bm.free()
    print("BOY foot: flat stretches merged: %d triangles, from %d" % (sum(len(f) - 2 for f in F2), n0))
    return L2, F2, ring2


FOOT_ARCH_LIFT = float(arg("--arch", "0.008"))
BIG_TOE = float(arg("--big-toe", "1.18"))


def shape_foot(L, F):
    """(seventh pass; the critic: "the inner arch is missing ... a flat foot", "the big toe is barely bigger than the
    others and not split from them by a clear gap", "heel: it has a hard corner") In the foot's own frame (u forward,
    v out, w up, the big toe toward -v): the inner sole lifted over the middle of the foot into an arch, the big toe
    made fuller and set a little apart inward, the heel's back-bottom corner drawn in."""
    L = np.array(L, float)
    u, v, w = L[:, 0], L[:, 1], L[:, 2]
    u0, u1 = float(u.min()), float(u.max())
    vin = float(v.min())
    t = (u - u0) / (u1 - u0)
    arch = np.exp(-((t - 0.5) / 0.17) ** 2) * smooth01(0.0, vin * 0.8, v) * (1.0 - smooth01(0.0, 0.022, w))
    L[:, 2] += FOOT_ARCH_LIFT * arch
    # the big toe: the toes' innermost third forward of where the toes part
    toe = u > u1 - 0.045
    if toe.any():
        vt0, vt1 = float(v[toe].min()), float(v[toe].max())
        big = toe & (v < vt0 + (vt1 - vt0) * 0.3)
        if big.sum() > 3:
            c = L[big].mean(0)
            g = smooth01(u1 - 0.045, u1 - 0.03, u) * big
            L[:, 1] += ((v - c[1]) * (BIG_TOE - 1.0) - 0.0018) * g
            L[:, 2] += ((w - c[2]) * (BIG_TOE - 1.0) * 0.7) * g * (w > 0.002)
    # the heel's corner
    heel = (1.0 - smooth01(u0, u0 + 0.03, u)) * (1.0 - smooth01(0.0, 0.03, w))
    L[:, 0] += 0.004 * heel * (1.0 - smooth01(0.0, 0.012, w)) * 0.8
    L[:, 2] += 0.002 * heel * (1.0 - smooth01(0.0, 0.006, w)) * (u < u0 + 0.01)
    print("BOY foot shaped: arch %.1f mm, big toe x%.2f, heel rounded" % (1000 * FOOT_ARCH_LIFT, BIG_TOE))
    return L


def make_foot():
    """The base foot made into his (a left foot in his own frame: u forward, v out to his left, w up; the sole at
    w 0, the ankle ring's middle at u = v = 0). Kept in FOOT: points, faces, the ankle ring (in order), the ball's and
    the toes' places, the toes' front edge for the nails."""
    P0, faces, uvs, _ = load_base(FOOT_BASE)
    ztop = P0[:, 2].max()
    # the cap over the ankle: faces whose points all lie within 3 mm of the top
    # (and any flat, upward-facing face near the top: the cap is a fan of them)
    def up_flat(f):
        n = np.cross(P0[f[1]] - P0[f[0]], P0[f[2]] - P0[f[0]])
        n = n / max(np.linalg.norm(n), 1e-12)
        return abs(n[2]) > 0.92 and P0[f, 2].min() > ztop - 0.03
    keep = [i for i, f in enumerate(faces) if P0[f, 2].min() < ztop - 0.003 and not up_flat(f)]
    faces = [faces[i] for i in keep]
    me = bpy.data.meshes.new("_foot")
    me.from_pydata([tuple(p) for p in P0], [], faces)
    ob = bpy.data.objects.new("_foot", me)
    bpy.context.scene.collection.objects.link(ob)
    mod = ob.modifiers.new("u", "DECIMATE")
    mod.decimate_type = "UNSUBDIV"
    mod.iterations = int(arg("--foot-unsub", "2"))
    dg = bpy.context.evaluated_depsgraph_get()
    m2 = ob.evaluated_get(dg).to_mesh()
    P = np.array([v.co[:] for v in m2.vertices])
    F = [list(p.vertices) for p in m2.polygons]
    ob.evaluated_get(dg).to_mesh_clear()
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.meshes.remove(me)
    used = sorted({v for f in F for v in f})
    re = {v: j for j, v in enumerate(used)}
    P = P[used]
    F = [[re[v] for v in f] for f in F]
    # the open ring
    ec = {}
    for f in F:
        for i in range(len(f)):
            e = (min(f[i], f[(i + 1) % len(f)]), max(f[i], f[(i + 1) % len(f)]))
            ec[e] = ec.get(e, 0) + 1
    bnd = [e for e, c in ec.items() if c == 1]
    adj = {}
    for a, b in bnd:
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    ring = [bnd[0][0], bnd[0][1]]
    while True:
        nx = [v for v in adj[ring[-1]] if v != ring[-2]][0]
        if nx == ring[0]:
            break
        ring.append(nx)
    # his frame: forward is the base's -Y; out is +X when the big toe (the toes' tallest) lies toward -X
    rc = P[ring].mean(0)
    u = -(P[:, 1] - rc[1])
    front = u > u.max() - 0.05
    big_x = P[front][np.argmax(P[front, 2]), 0]
    out_sign = 1.0 if big_x < rc[0] else -1.0
    v = (P[:, 0] - rc[0]) * out_sign
    w = P[:, 2] - P[:, 2].min()
    k = FOOT_LEN / (u.max() - u.min())
    L = np.stack([u * k, v * k * FOOT_WIDE, w * k], 1)
    L[:, 0] += -FOOT_HEEL - L[:, 0].min()
    rz = L[ring, 2].mean()
    # (the ankle's height brought to FOOT_RING_Z by stretching above the instep only)
    t = smooth01(0.03, rz, L[:, 2])
    L[:, 2] += (FOOT_RING_Z - rz) * t * np.clip(L[:, 2] / max(rz, 1e-6), 0, 1)
    # the ring's middle at u = v = 0
    c = L[ring].mean(0)
    L[:, 0] -= c[0]
    L[:, 1] -= c[1]
    # (the base's faces wind outward; the frame mirrors y, and x too when out_sign is -1: an odd count turns them)
    if out_sign > 0:
        F = [f[::-1] for f in F]
    L = plump_toes(L, F)
    if TOE_ROUND:
        L, F = round_toes(L, F)
    L = shape_foot(L, F)
    L, F, ring = flat_dissolve(L, F, ring, ~(L[:, 0] > L[:, 0].max() - 0.045))
    toes = L[:, 0] > L[:, 0].max() - 0.075
    FOOT.update(P=L, faces=F, ring=ring, toes=toes, ball=np.array((L[:, 0].max() - 0.07, 0.0, 0.022)),
                tip=np.array((L[:, 0].max(), 0.0, 0.012)))
    nt = sum(len(f) - 2 for f in F)
    print("BOY foot base: %d points, %d faces (%d triangles), its ankle ring %d points; %.3f m long, %.3f wide, ring at %.3f m" % (
        len(L), len(F), nt, len(ring), L[:, 0].ptp(), L[:, 1].ptp(), FOOT_RING_Z))


def zip_rings(M, A, B, PA, PB, centre, e1, e2, part):
    """Two closed rings of different counts joined with triangles by their places round a common middle."""
    def par(Q):
        d = Q - centre
        return np.mod(np.arctan2(d @ e2, d @ e1) / math.tau, 1.0)
    ua, ub = par(PA), par(PB)
    oa, ob = np.argsort(ua), np.argsort(ub)
    A = [A[i] for i in oa]
    B = [B[i] for i in ob]
    ua, ub = ua[oa], ub[ob]
    i = j = 0
    out = []
    na, nb = len(A), len(B)
    while i < na or j < nb:
        nxa = ua[(i + 1) % na] + (1.0 if i + 1 >= na else 0.0)
        nxb = ub[(j + 1) % nb] + (1.0 if j + 1 >= nb else 0.0)
        if j < nb and (i >= na or nxb <= nxa):
            M.face([A[i % na], B[(j + 1) % nb], B[j % nb]], part)
            j += 1
        else:
            M.face([A[i % na], A[(i + 1) % na], B[j % nb]], part)
            i += 1
        out.append(len(M.faces) - 1)
    return out


def hand(M, wrist_ring, side, W, L, joints, pose="rest"):
    """(third pass) The fitted base hand (make_hand) put on a forearm's last ring: its own coordinates turned into
    the hand's frame (the back facing out and a little forward, 38 degrees round from straight out, as before), its
    open ring zipped to the forearm's."""
    if not HAND:
        raise RuntimeError("make_hand first")
    sfx = "_l" if side > 0 else "_r"
    part = "hand" + sfx
    X = Vector((1, 0, 0))
    F = Vector((0, -1, 0))
    A = (X - L * L.x).normalized()
    tw = math.radians(38.0)
    Tb = A * math.cos(tw) + F * math.sin(tw)
    Wd = -A * math.sin(tw) + F * math.cos(tw)
    Lv, Wv, Tv, W0 = (np.array(v[:]) for v in (L, Wd, Tb, W))

    def place(q):
        # (fifth pass) the hand made larger (HAND_SCALE) beyond the wrist, the wrist itself a little slimmer, to meet
        # his thin forearm
        k = 0.9 + (HAND_SCALE - 0.9) * float(smooth01(0.0, 0.05, q[0]))
        return mirror_x(W0 + Lv * (q[0] * HAND_SCALE) + Wv * (q[1] * k) + Tv * (q[2] * k), side)
    Lc = HAND[pose]
    first = len(M.P)
    for i, q in enumerate(Lc):
        nm = HAND["part"][i]
        M.add(place(q), part if nm == "palm" else part + "_" + nm)
    uvm = M.tag.setdefault("hand_uv", {})
    M.tag["hand_faces" + sfx] = list(range(len(M.faces), len(M.faces) + len(HAND["faces"])))
    for f, uv in zip(HAND["faces"], HAND["uvs"]):
        names = {HAND["part"][v] for v in f}
        fp = part + "_" + names.pop() if len(names) == 1 and "palm" not in names else part
        M.face([first + v for v in f], fp)
        uvm[len(M.faces) - 1] = [(a * HAND_UV_M, b * HAND_UV_M) for a, b in uv]
    ring = [first + v for v in HAND["ring"]]
    PA = np.array([M.P[i] for i in wrist_ring])
    PB = np.array([M.P[i] for i in ring])
    zf = zip_rings(M, list(wrist_ring), ring, PA, PB, PA.mean(0), mirror_x(Wv, side), mirror_x(Tv, side), part)
    # (the zip's UVs: each point takes its nearest ring point's, a narrow strip; the paint fades over the wrist)
    ring_uv = {}
    for fi, (f, uv) in enumerate(zip(HAND["faces"], HAND["uvs"])):
        for v, q in zip(f, uv):
            ring_uv.setdefault(first + v, (q[0] * HAND_UV_M, q[1] * HAND_UV_M))
    for fi in zf:
        uv = []
        for v in M.faces[fi]:
            if v in ring_uv:
                uv.append(ring_uv[v])
            else:
                near = min(ring, key=lambda r: np.linalg.norm(np.asarray(M.P[r]) - np.asarray(M.P[v])))
                uv.append(ring_uv[near])
        uvm[fi] = uv
    M.tag["hand_zip" + sfx] = zf
    for name in FINGERS + ("thumb",):
        joints["%s%s" % (name, sfx)] = [Vector(place(p)) for p in HAND["joints"][pose][name]]
    joints["thumb_back%s" % sfx] = np.array(mirror_x(Tv, side))
    joints["hand_frame%s" % sfx] = tuple(np.array(mirror_x(v, side)) for v in (Tv, Wv, Lv))
    joints["knuckles%s" % sfx] = Vector(np.mean([place(HAND["joints"][pose][n][0]) for n in FINGERS], axis=0))
    M.tag["hand_points" + sfx] = (first, first + len(Lc))


def hand_alone(pose):
    """A left hand alone in a given pose on a wrist ring of its own at the origin, pointing down: the same points in
    the same order as the body's left hand (for its outline against the hands sheet, and to paint from it)."""
    Mt = Mesh()
    L = Vector((0.0, 0.0, -1.0))
    A, F = Vector((1, 0, 0)), Vector((0, -1, 0))
    ring = [Mt.add(A * (0.031 * math.cos(math.tau * j / LIMB_N)) + F * (0.022 * math.sin(math.tau * j / LIMB_N)), "arm_l")
            for j in range(LIMB_N)]
    jt = {}
    hand(Mt, ring, 1, Vector((0.0, 0.0, 0.0)), L, jt, pose=pose)
    return Mt, jt


# ------------------------------------------------------------------------------------------------------------------
# Geometry helpers
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
    P = np.asarray(P)
    kd = kdtree.KDTree(len(P))
    for i, p in enumerate(P):
        kd.insert(Vector(p), i)
    kd.balance()
    mir = np.arange(len(P))
    for i, p in enumerate(P):
        q, j, d = kd.find(Vector((-p[0], p[1], p[2])))
        if d < 1e-5:
            mir[i] = j
    return mir


def face_normal(P, f):
    p = [np.asarray(P[i]) for i in f]
    n = np.zeros(3)
    for i in range(1, len(p) - 1):
        n += np.cross(p[i] - p[0], p[i + 1] - p[0])
    return n


def fix_winding(M):
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


def inconsistent(faces):
    """edges two faces cross the same way (their windings disagree), and edges with more than two faces"""
    seen = {}
    for f in faces:
        for i in range(len(f)):
            e = (f[i], f[(i + 1) % len(f)])
            seen[e] = seen.get(e, 0) + 1
    same = sum(1 for e, c in seen.items() if c > 1)
    cnt = {}
    for (a, b), c in seen.items():
        k = (min(a, b), max(a, b))
        cnt[k] = cnt.get(k, 0) + c
    return same, sum(1 for c in cnt.values() if c > 2)


def open_edges(faces):
    count = {}
    for f in faces:
        for i in range(len(f)):
            e = (min(f[i], f[(i + 1) % len(f)]), max(f[i], f[(i + 1) % len(f)]))
            count[e] = count.get(e, 0) + 1
    return [e for e, c in count.items() if c != 2]


def winding_check(M, label):
    """Every closed piece's faces against its volume: the signed volume must be positive (faces outward), and each
    face's normal must point away from its piece's middle more often than not (a check in code, as the user asked:
    no inside-out faces)."""
    P = np.array(M.P)
    tris = np.array(M.tris())
    fam = np.array(M.tri_fams())
    vol = float(np.einsum("ij,ij->i", P[tris[:, 0]], np.cross(P[tris[:, 1]], P[tris[:, 2]])).sum() / 6.0)
    Nv = normals_of(P, tris)
    fn = np.cross(P[tris[:, 1]] - P[tris[:, 0]], P[tris[:, 2]] - P[tris[:, 0]])
    folded = int(((fn * Nv[tris].mean(1)).sum(1) < 0).sum())
    bad = ((fn * Nv[tris].mean(1)).sum(1) < 0)
    if bad.any():
        fams_bad = {}
        for f_ in fam[bad]:
            fams_bad[f_] = fams_bad.get(f_, 0) + 1
        print("BOY folded by part %s: %s" % (label, json.dumps(fams_bad)))
    print("BOY winding %s: signed volume %.4f m3 (must be > 0); %d triangles folded against their neighbours" % (label, vol, folded))
    return vol


# ------------------------------------------------------------------------------------------------------------------
# Fitting to the sheet's outlines
# ------------------------------------------------------------------------------------------------------------------

FIT_VIEWS = {
    "front": ("torso", "shoulder", "arm", "leg", "foot"),
    "back": ("torso", "shoulder", "arm", "leg", "foot"),
    "side": ("torso", "leg", "foot"),
}
FIT_REACH = 28
FIT_DAMP = 0.75


def part_family(part):
    return part.split("_")[0]


def with_caps(M, P, tris):
    P = np.asarray(P)
    extra = []
    tris = list(tris)
    for sfx in ("_l", "_r"):
        ring = M.tag["hole" + sfx]
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
            under_arm = (fams == "torso") & (P[:, 2] > body_z(BR(612))) & (P[:, 2] < body_z(BR(436)))
            ok &= ~under_arm
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
    P2 = (P + Q) / 2.0
    # (third pass: points with no mirror image are left where they are, unless they are on the middle line; set onto
    # the middle line, the base head's few unpaired points folded his face)
    P2[alone] = P[alone]
    P2[alone & (np.abs(P[:, 0]) < 2e-3), 0] = 0.0
    M.P = [p for p in P2]


# ------------------------------------------------------------------------------------------------------------------
# The hands sheet (second pass): tools/art_src/concept_boy_hands.jpg, his left hand in six views. The back view
# (fingers to the right, the thumb below) and the palm view (fingers up; drawn as a right hand, so the model is seen
# mirrored) are the open hand; the thumb-side view (fingers to the left, the back up; also mirrored) is relaxed.
# Each: the box it lies in (rows, columns), metres a pixel (the back view: 670 pixels wrist to middle fingertip, the
# palm view 628, for a 0.175 m hand), and the part compared (the forearm the sheet draws beyond the wrist is not).
# ------------------------------------------------------------------------------------------------------------------

HAND_SHEET = os.path.join(ART, "concept_boy_hands.jpg")
HANDV = {"back": {"box": (100, 740, 150, 1080), "k": 0.000261, "keep": ("col", 375, 1), "pose": "open", "wrist": 362},
         "palm": {"box": (70, 900, 1190, 1790), "k": 0.000279, "keep": ("row", 715, -1), "pose": "open", "wrist": 722},
         "side": {"box": (230, 640, 1830, 2700), "k": 0.000262, "keep": ("col", 2470, -1), "pose": "rest", "wrist": 2478}}


def hand_uv(view, P, frame):
    """Hand-frame picture coordinates (pixels from the wrist, before placing) and depth, for points of a left hand
    whose frame (back, across toward the thumb, along) is given and whose wrist is at the origin."""
    Tb, Wd, L = (np.asarray(v, float) for v in frame)
    k = HANDV[view]["k"]
    P = np.asarray(P, float)
    if view == "back":
        return np.stack([P @ L / k, P @ Wd / k], 1), -(P @ Tb)
    if view == "palm":
        return np.stack([P @ Wd / k, -(P @ L) / k], 1), P @ Tb
    return np.stack([-(P @ L) / k, -(P @ Tb) / k], 1), -(P @ Wd)


def hand_keep(view, shape):
    r0, r1, c0, c1 = HANDV[view]["box"]
    m = np.zeros(shape, bool)
    m[r0:r1, c0:c1] = True
    kind, at, sgn = HANDV[view]["keep"]
    if kind == "col":
        cols = np.arange(shape[1])
        m &= ((cols - at) * sgn >= 0)[None, :]
    else:
        rows = np.arange(shape[0])
        m &= ((rows - at) * sgn >= 0)[:, None]
    return m


def place_hand(view, uv, depth, tris, sh):
    """The hand's filled outline placed on the sheet: its wrist held where the sheet draws the wrist, along the hand
    (slid along freely, a hand of the wrong length hid half its error under the forearm's cut), its middle across the
    hand on the sheet's, then a search of small shifts. Drawn where it is placed (drawn first and moved after, its
    fingers were cut off at the picture's edge). Gives (model mask, target, (column, row) of the wrist, gap)."""
    shape = sh.hand_mask.shape
    keep = hand_keep(view, shape)
    tgt = sh.hand_mask & keep
    r0, r1, c0, c1 = HANDV[view]["box"]
    ty, tx = np.where(tgt)
    ax = 0 if HANDV[view]["keep"][0] == "col" else 1
    at = np.array((tx.mean(), ty.mean())) - uv.mean(0)
    at[ax] = HANDV[view]["wrist"]
    best = None
    for d in range(-40, 41, 4):
        for e in (-4, 0, 4):
            off = at + ((e, d) if ax == 0 else (d, e))
            zb, _ = raster(uv + off, depth, tris, shape)
            m = np.isfinite(zb) & keep
            err = int((m ^ tgt).sum())
            if best is None or err < best[0]:
                best = (err, off, m)
    _, off, model = best
    p99, worst = silhouette_gap(model, tgt, (r0, r1))
    return model, tgt, off, (round(p99 * HANDV[view]["k"] * 100, 2), round(worst * HANDV[view]["k"] * 100, 2))


def hand_silhouettes(sh, tag):
    """His left hand against the hands sheet's back, palm and thumb-side views as filled outlines: the gap per view
    (cm: 99%, worst) and red/cyan difference pictures. Gives each view's wrist placement, for painting."""
    out, places = {}, {}
    for view in ("back", "palm", "side"):
        Mt, jt = hand_alone(HANDV[view]["pose"])
        tris = [t for t, f in zip(Mt.tris(), Mt.tri_fams()) if f == "hand"]
        uv, depth = hand_uv(view, np.array(Mt.P), jt["hand_frame_l"])
        model, tgt, at, gap = place_hand(view, uv, depth, tris, sh)
        out[view] = gap
        places[view] = at
        if OUT:
            r0, r1, c0, c1 = HANDV[view]["box"]
            diff_picture(model, tgt, sh.hand_pix, (r0, r1, c0, c1), os.path.join(OUT, "handdiff_%s_%s.png" % (tag, view)))
    print("BOY hand outline gaps %s (cm: 99%%, worst) %s" % (tag, json.dumps(out)))
    return places


def paint_hands_from_sheet(M, face_uv, rgb, sh, places, joints):
    """The hands painted from the hands sheet's open views (second pass): each texel of a hand is found on the open
    hand of the same points (hand_alone), and from there in the back view (where it faces the back of the hand) or
    the palm view (where it faces the palm); the sides between are filled from round them. The sheet's colours are
    toned to his forearm's (the median of each against the other), and faded into it over the wrist."""
    Mt, jt = hand_alone("open")
    Pt = np.array(Mt.P)
    P = np.array(M.P)
    Pf = P.copy()
    for sfx, s in (("_l", 1.0), ("_r", -1.0)):
        a, b = M.tag["hand_points" + sfx]
        q = Pt[LIMB_N:LIMB_N + (b - a)].copy()
        q[:, 0] *= s
        Pf[a:b] = q
        ring = M.tag["arm_rings" + sfx][-1]
        q = Pt[:LIMB_N].copy()
        q[:, 0] *= s
        Pf[ring] = q
    tris = M.tris()
    Nf = normals_of(Pf, tris)
    N = normals_of(P, tris)
    pos, nrm, hit, fid = texel_geometry(M, face_uv, "skin", P, N)
    fpos, fnrm, _, _ = texel_geometry(M, face_uv, "skin", Pf, Nf)
    size = ATLAS["skin"]
    fam = np.array([p.split("_")[0] for p in M.fpart] + ["none"])[fid]
    hands = hit & (fam == "hand")
    side_of = np.sign(pos[..., 0])
    Q = fpos.copy()
    Nn = fnrm.copy()
    Q[..., 0] *= side_of
    Nn[..., 0] *= side_of
    Tb = np.asarray(jt["hand_frame_l"][0], float)
    got = np.zeros((size, size, 3))
    seen = np.zeros((size, size), bool)
    mask = erode(sh.hand_mask, 3)
    h, w = mask.shape
    # (fourth pass: each texel from both views by how squarely each sees it, not cut at a threshold: the cut showed
    # as a hard line down the sides of the fingers)
    wsum = np.zeros((size, size))
    nb = Nn @ Tb
    for view, sgn in (("back", 1.0), ("palm", -1.0)):
        sel = hands & (sgn * nb > 0.05)
        uv, _ = hand_uv(view, Q[sel], jt["hand_frame_l"])
        at = places[view]
        c = np.clip((uv[:, 0] + at[0]).astype(int), 0, w - 1)
        r = np.clip((uv[:, 1] + at[1]).astype(int), 0, h - 1)
        ok = mask[r, c]
        idx = np.argwhere(sel)[ok]
        wt = np.clip(sgn * nb[sel][ok], 0, 1) ** 2
        got[idx[:, 0], idx[:, 1]] += sh.hand_pix[r[ok], c[ok]] * wt[:, None]
        wsum[idx[:, 0], idx[:, 1]] += wt
    seen = wsum > 0.04
    got[seen] /= wsum[seen][:, None]
    arm = hit & (fam == "arm")
    near = arm & (np.abs(pos[..., 2] - float(np.median(pos[hands][:, 2]))) < 0.12)
    gain = np.median(rgb[near], axis=0) / np.maximum(np.median(got[seen], axis=0), 1e-3)
    gain = np.clip(gain, 0.6, 1.4)
    print("BOY hands painted from the sheet: %d texels, toned by %s" % (int(seen.sum()), np.round(gain, 3)))
    out = rgb.copy()
    out[seen] = got[seen] * gain
    good = (hit & ~hands) | seen
    filled = fill_out(out, good, 100)
    out[hands & ~seen] = filled[hands & ~seen]
    # (faded into the forearm's own paint over the wrist, so there is no step)
    for sfx, s in (("_l", 1.0), ("_r", -1.0)):
        L_ = np.array(joints["hand_frame" + sfx][2], float)
        Wr = np.array(joints["wrist_l"], float) * np.array((s, 1.0, 1.0))
        t = smooth01(0.0, 0.03, ((pos - Wr) * L_).sum(-1))
        k = hands & (side_of == s) & (t < 1.0)
        out[k] = out[k] * t[k][:, None] + rgb[k] * (1.0 - t[k][:, None])
    return out


# ------------------------------------------------------------------------------------------------------------------
# Overlays
# ------------------------------------------------------------------------------------------------------------------

def outline_of(mask):
    return mask & ~(np.roll(mask, 1, 0) & np.roll(mask, -1, 0) & np.roll(mask, 1, 1) & np.roll(mask, -1, 1))


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


def boundary_distance(model, target):
    mo = outline_of(model)
    to = outline_of(target)
    ty, tx = np.where(to)
    kd = kdtree.KDTree(len(ty))
    for i in range(len(ty)):
        kd.insert((float(tx[i]), float(ty[i]), 0.0), i)
    kd.balance()
    my, mx = np.where(mo)
    d = np.array([kd.find((float(mx[i]), float(my[i]), 0.0))[2] for i in range(len(my))])
    return d, my, mx


def model_picture(objs_tris, view, shape, skip=()):
    P = np.concatenate([o[0] for o in objs_tris])
    tris = []
    off = 0
    for pts, tr, fam in objs_tris:
        for ti, t in enumerate(tr):
            if fam[ti] in skip:
                continue
            tris.append((t[0] + off, t[1] + off, t[2] + off))
        off += len(pts)
    P2, dep = project(view, P)
    zb, tid = raster(P2, dep, tris, shape)
    model = np.isfinite(zb)
    N = normals_of(P, tris)
    _, facing = screen_dir(view, N)
    T = np.asarray(tris)
    shade_t = 0.3 + 0.7 * np.clip(facing[T].mean(1), 0, 1)
    shade = np.where(model, shade_t[np.maximum(tid, 0)], 0.0)
    return model, shade


def overlay(objs_tris, sh, round_name, report=True):
    if not OUT:
        return {}
    os.makedirs(OUT, exist_ok=True)
    result = {}
    for view in ("front", "side", "back"):
        skip = ("arm", "hand") if view == "side" else ("sidecap",)
        model, shade = model_picture(objs_tris, view, sh.body_mask.shape, skip)
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
        line = pic.copy()
        for dy in (0, 1):
            for dx in (0, 1):
                line[np.roll(np.roll(mo, dy, 0), dx, 1)] = (0.95, 0.1, 0.1)
        save_rgb(os.path.join(OUT, "outline_%s_%s.png" % (round_name, view)), line)
        if report:
            d, my, mx = boundary_distance(model, sh.body_target)
            head = my < 400
            box = (my >= BOXERS[0]) & (my < BOXERS[1])
            rest = ~head & ~box

            def stats(sel):
                if not sel.any():
                    return (0.0, 0.0)
                return (round(float(np.percentile(d[sel], 99)) * S * 100, 2), round(float(d[sel].max()) * S * 100, 2))
            result[view] = {"body_99cm": stats(rest), "boxers_99cm": stats(box), "head_99cm": stats(head)}
            worst = np.argmax(np.where(rest, d, 0))
            result[view]["body_worst_at"] = (int(mx[worst]), int(my[worst]))
    return result


def silhouette_gap(model, target, rows):
    """How far the model's filled outline and the sheet's are apart, within rows (r0, r1): the distance from each
    outline pixel of one to the nearest of the other, both ways. Gives (99th percentile, worst) in pixels."""
    keep = np.zeros(model.shape[0], bool)
    keep[rows[0]:rows[1]] = True
    mo = outline_of(model) & keep[:, None]
    to = outline_of(target) & keep[:, None]
    out = []
    for a, b in ((mo, to), (to, mo)):
        by, bx = np.where(b)
        ay, ax = np.where(a)
        if not len(by) or not len(ay):
            return (99.0, 99.0)
        kd = kdtree.KDTree(len(by))
        for i in range(len(by)):
            kd.insert((float(bx[i]), float(by[i]), 0.0), i)
        kd.balance()
        out.append(np.array([kd.find((float(ax[i]), float(ay[i]), 0.0))[2] for i in range(len(ay))]))
    d = np.concatenate(out)
    return float(np.percentile(d, 99)), float(d.max())


def diff_picture(model, target, pic, box, path, scale=1):
    """The two filled outlines over the sheet, dimmed: red where only the model is, cyan where only the sheet is,
    grey where both."""
    r0, r1, c0, c1 = box
    m, t = model[r0:r1, c0:c1], target[r0:r1, c0:c1]
    img = pic[r0:r1, c0:c1] * 0.35 + 0.6
    img[m & t] = img[m & t] * 0.55 + np.array((0.45, 0.45, 0.47)) * 0.45
    img[m & ~t] = (0.92, 0.12, 0.12)
    img[t & ~m] = (0.1, 0.8, 0.85)
    if scale > 1:
        img = np.repeat(np.repeat(img, scale, 0), scale, 1)
    save_rgb(path, img)


HEAD_SKIP = ("arm", "hand", "sidecap", "leg", "foot", "boxers")


def head_silhouettes(objs_tris, sh, tag, pictures=True):
    """The head against the bald row's five views, as filled outlines (the ears in both): the gap per view in cm
    (above the neck's cut-off, row H_NECK), and a difference picture of each."""
    out = {}
    for view in ("hfront", "hq", "hside", "hqb", "hback"):
        model, _ = model_picture(objs_tris, view, sh.head_mask.shape, HEAD_SKIP)
        c0, c1 = HSPAN[view]
        target = np.zeros_like(sh.head_mask)
        target[:, c0:c1] = sh.head_mask[:, c0:c1]
        model[:, :c0] = False
        model[:, c1:] = False
        p99, worst = silhouette_gap(model, target, (H_BALD[0], H_NECK))
        out[view] = (round(p99 * HS * 100, 2), round(worst * HS * 100, 2))
        if pictures and OUT:
            c0, c1 = HSPAN[view]
            diff_picture(model, target, sh.head_pix, (H_BALD[0], 1320, c0, c1),
                         os.path.join(OUT, "headdiff_%s_%s.png" % (tag, view)))
    print("BOY head outline gaps %s (cm: 99%%, worst) %s" % (tag, json.dumps(out)))
    return out


def body_silhouettes(objs_tris, sh, tag):
    """The body against the base sheet's front, side and back as filled outlines, below the hair (row 400): the gap
    per view in cm, the shorts' rows apart (their cloth stands off him there by design), and difference pictures."""
    out = {}
    for view in ("front", "side", "back"):
        skip = ("arm", "hand") if view == "side" else ("sidecap",)
        model, _ = model_picture(objs_tris, view, sh.body_mask.shape, skip)
        c0, c1 = SPAN[view]
        target = np.zeros_like(sh.body_mask)
        target[:, c0:c1] = sh.body_mask[:, c0:c1]
        model[:, :c0] = False
        model[:, c1:] = False
        res = {}
        for name, rows in (("above_shorts", (BR(400), BOXERS[0])), ("shorts", BOXERS), ("legs", (BOXERS[1] + 4, BR(1470)))):
            p99, worst = silhouette_gap(model, target, rows)
            res[name] = (round(p99 * S * 100, 2), round(worst * S * 100, 2))
        out[view] = res
        if OUT:
            c0, c1 = SPAN[view]
            diff_picture(model, target, sh.body_pix, (40, 1530, c0, c1), os.path.join(OUT, "bodydiff_%s_%s.png" % (tag, view)))
    print("BOY body outline gaps %s (cm: 99%%, worst) %s" % (tag, json.dumps(out)))
    return out


def fit_angled_model(objs_tris, sh):
    """The 3/4 views' azimuth and middle column found again with the model itself (after the head is fitted to the
    front, side and back): the angle whose filled outline, slid to its best column, differs least from the sheet's."""
    for view, guesses in (("hq", np.arange(24.0, 61.0, 2.0)), ("hqb", np.arange(204.0, 247.0, 2.0))):
        c0, c1 = HSPAN[view]
        tgt = np.zeros_like(sh.head_mask)
        tgt[H_BALD[0]:H_NECK, c0:c1] = sh.head_mask[H_BALD[0]:H_NECK, c0:c1]
        tc = np.where(tgt)[1].mean()
        best = None
        for a in guesses:
            HVIEW[view][0] = float(a)
            HVIEW[view][1] = 2000.0
            model, _ = model_picture(objs_tris, view, (sh.head_mask.shape[0], 4000), HEAD_SKIP)
            model[:H_BALD[0]] = False
            model[H_NECK:] = False
            ys, xs = np.where(model)
            if not len(xs):
                continue
            for dc in np.arange(-6, 7, 2):
                shift = int(round(tc - xs.mean())) + int(dc)
                m2 = np.zeros_like(tgt)
                cc = xs + shift
                ok = (cc >= 0) & (cc < tgt.shape[1])
                m2[ys[ok], cc[ok]] = True
                err = int((m2 ^ tgt).sum())
                if best is None or err < best[0]:
                    best = (err, float(a), shift + 2000)
        HVIEW[view][0], HVIEW[view][1] = best[1], float(best[2])
        print("BOY head sheet %s (by the model): azimuth %.1f degrees, middle column %.1f, %d pixels differ" % (view, best[1], best[2], best[0]))


# Landmarks on the bald row (picture column, row), read off each view at twice size: the brow's middle, the nose's
# tip, the mouth's corners, the chin's bottom, the jaw's angles, the ear lobes' bottoms ("_r" his right).
LANDMARKS = {
    # (fifth pass: measured off concept_boy_head2.jpg's bald row; the 3/4 views not measured)
    "hfront": {"brow": (360, 1040), "nose": (360, 1172), "chin": (360, 1303), "mouth_r": (288, 1222), "mouth_l": (432, 1222),
               "eye_l": (435, 1103),
               "jaw_r": (232, 1240), "jaw_l": (488, 1240), "lobe_r": (165, 1220), "lobe_l": (555, 1220)},
    "hside": {"brow": (1578, 1040), "nose": (1621, 1167), "mouth_r": (1548, 1226), "chin": (1565, 1312),
              "jaw_r": (1386, 1240), "lobe_r": (1352, 1215)},
}
MOUTH_CORNER = (1223.0, 72.0)     # head-sheet row and columns out from his middle (the front view)
JAW_ANGLE = (1240.0, 128.0, 1386.0)   # row, columns out (front), side view column


def model_landmarks(M):
    """(third pass) The base head's own landmark points, carried through the fitting."""
    mk = M.tag["head_marks"]
    out = {k: np.array(M.P[v]) for k, v in mk.items()}
    out["eye_l"] = np.mean([M.P[v] for v in M.tag["head_eye"]], axis=0)
    return out


def model_landmarks_retired(M):
    P = np.array(M.P)
    N = normals_of(P, M.tris())
    fam = np.array([part_family(p) for p in M.part])
    head = fam == "head"
    rows = hrow(P[:, 2])
    cy = np.array([head_centre(M, z)[1] for z in P[:, 2]])
    front = head & (P[:, 1] < cy - 0.04)
    mid = front & (np.abs(P[:, 0]) < 0.005)
    out = {}
    i = np.where(mid)[0]
    out["brow"] = P[i[np.argmin(np.abs(rows[i] - HR(910)))]]
    j = np.where(fam == "nose")[0]
    out["nose"] = P[j[np.argmin(P[j, 1])]]
    k = np.where(mid & (N[:, 1] < -0.3) & (rows < HR(1180)))[0]
    out["chin"] = P[k[np.argmax(rows[k])]]
    for s, sfx in ((1, "_l"), (-1, "_r")):
        c = np.where(front & (np.sign(P[:, 0]) == s))[0]
        tgt = np.array((s * MOUTH_CORNER[1] * HS, float(hz(MOUTH_CORNER[0]))))
        out["mouth" + sfx] = P[c[np.argmin(np.linalg.norm(P[c][:, [0, 2]] - tgt, axis=1))]]
        # (the jaw's angle: the head's point nearest where the sheet puts it, seen from the front and the side)
        ang = np.array((s * JAW_ANGLE[1] * HS, side_y(JAW_ANGLE[2]), float(hz(JAW_ANGLE[0]))))
        b = np.where(head)[0]
        out["jaw" + sfx] = P[b[np.argmin(np.linalg.norm(P[b] - ang, axis=1))]]
        e = np.where(fam == "ear")[0]
        e = e[np.sign(P[e, 0]) == s]
        out["lobe" + sfx] = P[e[np.argmin(P[e, 2])]]
    return out


def landmark_report(M, tag):
    L = model_landmarks(M)
    res = {}
    for view, marks in LANDMARKS.items():
        res[view] = {}
        for name, (c, r) in marks.items():
            q, _ = project(view, np.array([L[name]]))
            res[view][name] = round(float(np.hypot(q[0, 0] - c, q[0, 1] - r)) * HS * 100, 2)
            if view == "hfront":
                print("BOY landmark %s: model at (%.0f, %.0f), sheet (%d, %d)" % (name, q[0, 0], q[0, 1], c, r))
    print("BOY head landmarks %s (cm from the sheet's): %s" % (tag, json.dumps(res)))
    return res, L


def sculpt_jaw(M, amount_edge=0.0012, amount_under=0.003, reach=0.02):
    """(second pass; the coordinator, from the captain: "why is his jaw just straight flat across?") The mandible as a
    slanted edge: a curve from each jaw angle (below the ear lobe) down and forward to the chin's bottom. Points of the
    head beside it on the face's side are lifted a little (the edge), points under and behind it are drawn in toward
    the neck's axis (the under-jaw surface turning back to the throat), so the jaw reads as a curve in the front view
    and as a line from the lobe to the chin in the side view, never a level shelf."""
    P = np.array(M.P)
    N = normals_of(P, M.tris())
    fam = np.array([part_family(p) for p in M.part])
    chin_y = side_y(LANDMARKS["hside"]["chin"][0])
    chin = np.array((0.0, chin_y + 0.004, float(hz(HR(1170)))))
    moved = 0
    for s in (1.0, -1.0):
        ang = np.array((s * JAW_ANGLE[1] * HS * 0.92, side_y(JAW_ANGLE[2]), float(hz(JAW_ANGLE[0]))))
        # the curve: from the angle, bowing out a little, to the chin
        ts = np.linspace(0.0, 1.0, 24)
        mid = (ang + chin) / 2.0 + np.array((s * 0.012, -0.006, -0.004))
        C = np.array([(1 - t) ** 2 * ang + 2 * t * (1 - t) * mid + t * t * chin for t in ts])
        sel = np.where((fam == "head") & (np.sign(P[:, 0]) * s >= -1e-6))[0]
        for v in sel:
            d = C - P[v]
            dist = np.linalg.norm(d, axis=1)
            i = int(np.argmin(dist))
            if dist[i] > reach:
                continue
            off = P[v] - C[i]
            k = (1.0 - dist[i] / reach) ** 2
            if off[2] < -0.002:
                # under the jaw: in toward the neck's middle (x to 0, y toward the throat)
                axis = np.array((0.0, -0.01, P[v][2]))
                inward = axis - P[v]
                inward[2] = 0.0
                inward /= max(np.linalg.norm(inward), 1e-9)
                P[v] += inward * amount_under * k
            else:
                P[v] += N[v] * amount_edge * k
            moved += 1
    M.P = [p for p in P]
    print("BOY jaw sculpted: %d points" % moved)


def fit_head(M, sh, frozen, rounds=8, reach=24, damp=0.8):
    """The head pulled onto the bald row's front, side and back outlines (the ears out of the front and back
    targets, and out of the drawing, so the head's own outline is what is fitted): as fit_round does for the body,
    every point on the model's outline in each view moved along its outward direction to the sheet's, the move spread
    to its neighbours, left and right kept alike. The nose is fitted to the side view's profile."""
    allowed = {"hfront": ("head",), "hside": ("head", "nose"), "hback": ("head",)}
    mir = mirror_map(M.P)
    for rnd in range(rounds):
        P = np.array(M.P)
        tris = M.tris()
        tf = M.tri_fams()
        N = normals_of(P, tris)
        fams = np.array([part_family(p) for p in M.part])
        keep_tris = [t for t, f in zip(tris, tf) if f not in HEAD_SKIP and f != "ear" and f != "torso"]
        move = np.zeros_like(P)
        count = np.zeros(len(P))
        tgt = sh.head_target
        h, w = tgt.shape
        rows_p = hrow(P[:, 2])
        for view, fam_ok in allowed.items():
            P2, dep = project(view, P)
            zb, _ = raster(P2, dep, keep_tris, tgt.shape)
            R = np.isfinite(zb)
            d2, facing = screen_dir(view, N)
            L = np.linalg.norm(d2, axis=1)
            ok = np.isin(fams, fam_ok) & (np.abs(facing) < 0.55) & (L > 0.4) & ~frozen & (rows_p < H_NECK - 4)
            if view == "hside":
                # (the face's middle is not pulled onto the profile: its lips and brow are put in by sculpt_head;
                # pulled, single points of them stood out of the face as spikes and ridges)
                cyv = np.array([head_centre(M, z)[1] for z in P[:, 2]])
                ok &= ~((rows_p > HR(890)) & (rows_p < HR(1166)) & (P[:, 1] < cyv))
            for v in np.where(ok)[0]:
                p = P2[v]
                dirn = d2[v] / L[v]
                q = p + dirn * 3.0
                qi = (int(q[1]), int(q[0]))
                if not (0 <= qi[0] < h and 0 <= qi[1] < w) or R[qi]:
                    continue
                pi = (int(p[1]), int(p[0]))
                if not (0 <= pi[0] < h and 0 <= pi[1] < w):
                    continue
                dist = None
                if tgt[pi]:
                    for k in range(1, reach + 1):
                        qq = p + dirn * k
                        if not tgt[min(max(int(qq[1]), 0), h - 1), min(max(int(qq[0]), 0), w - 1)]:
                            dist = k - 0.5
                            break
                else:
                    for k in range(1, reach + 1):
                        qq = p - dirn * k
                        if tgt[min(max(int(qq[1]), 0), h - 1), min(max(int(qq[0]), 0), w - 1)]:
                            dist = -(k - 0.5)
                            break
                if dist is None:
                    continue
                move[v] += world_dir(view, dirn[None, :])[0] * dist * HS
                count[v] += 1
        has = count > 0
        move[has] /= count[has, None]
        # (at most 4 mm a round: the surface follows in steps and stays smooth)
        ln = np.linalg.norm(move, axis=1, keepdims=True)
        move *= np.minimum(1.0, 0.004 / np.maximum(ln, 1e-9))
        E = edges_of([f for f, p in zip(M.faces, M.fpart) if part_family(p) in ("head", "neck", "nose")])
        D = move.copy()
        W = has.astype(float) * 4.0
        deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
        for _ in range(8):
            acc = np.zeros_like(D)
            np.add.at(acc, E[:, 0], D[E[:, 1]])
            np.add.at(acc, E[:, 1], D[E[:, 0]])
            D = (W[:, None] * move + acc) / np.maximum(W + deg, 1e-9)[:, None]
        D[frozen] = 0.0
        D[fams == "ear"] = 0.0
        P += D * damp
        # (left and right kept alike, the head's points only: symmetrize() sets every point with no mirror image onto
        # the middle line, and after the head's refinement that took his legs with it)
        Q = P[mir].copy()
        Q[:, 0] *= -1
        hp = ~frozen & (fams != "ear")
        paired = hp & (mir != np.arange(len(P)))
        P[paired] = (P[paired] + Q[paired]) / 2.0
        mid = hp & (mir == np.arange(len(P))) & (np.abs(P[:, 0]) < 0.004)
        P[mid, 0] = 0.0
        M.P = [p for p in P]
        print("BOY head fit round %d: %d points on the outline moved, most %.1f mm" % (rnd + 1, int(has.sum()), 1000 * float(np.abs(move[has]).max() if has.any() else 0)))


# ------------------------------------------------------------------------------------------------------------------
# His skeleton: the game's figures' bone names and parents (the captain's: the leg's bones hang from the hips side by
# side, as the rig's IK in scripts/title_figures.gd expects), every bone pointing up with no roll
# ------------------------------------------------------------------------------------------------------------------

FINGERS = ("index", "middle", "ring", "little")


def torso_centre(M, T, z):
    rings = [(M.P[r[0]][2], np.array([M.P[i] for i in r])) for r in T]
    zs = [a for a, _ in rings]
    i = int(np.clip(np.searchsorted(zs, z), 1, len(zs) - 1))
    za, pa = rings[i - 1]
    zb, pb = rings[i]
    t = float(np.clip((z - za) / max(zb - za, 1e-6), 0.0, 1.0))
    ring = pa * (1 - t) + pb * t
    yf, yb = ring[:, 1].min(), ring[:, 1].max()
    return Vector((0.0, float(yb - 0.42 * (yb - yf)), float(z)))


NECK_Z = float(body_z(BR(418)))
HEAD_Z = float(body_z(BR(345)))


def skeleton_joints(M, T, joints):
    hip_z = joints["hip_l"].z
    bones = [
        ("hips", torso_centre(M, T, hip_z + 0.03), None),
        ("spine", torso_centre(M, T, float(body_z(BR(815)))), "hips"),
        ("chest", torso_centre(M, T, float(body_z(BR(650)))), "spine"),
        ("neck", torso_centre(M, T, NECK_Z), "chest"),
    ]
    bones.append(("head", Vector((0.0, (MID["side"] - 1446.0) * S, HEAD_Z)), "neck"))
    for s, sfx in ((1, "_l"), (-1, "_r")):
        sh_ = Vector(mirror_x(joints["shoulder_l"], s))
        el = Vector(mirror_x(joints["elbow_l"], s))
        wr = Vector(mirror_x(joints["wrist_l"], s))
        bones.append(("clavicle" + sfx, Vector((s * 0.035, sh_.y - 0.01, sh_.z + 0.05)), "chest"))
        bones.append(("upper_arm" + sfx, sh_, "clavicle" + sfx))   # (eighth pass: from the chest; the clavicle lifts the shoulder)
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


def make_armature(bones, name="boy_armature"):
    data = bpy.data.armatures.new(name)
    arm_ = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(arm_)
    bpy.context.view_layer.objects.active = arm_
    bpy.ops.object.mode_set(mode="EDIT")
    for bname, at, parent in bones:
        b = data.edit_bones.new(bname)
        b.head = Vector(at)
        b.tail = Vector(at) + Vector((0.0, 0.0, 0.05))
        b.roll = 0.0
        if parent:
            b.parent = data.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    return arm_


def along(p, a, b):
    d = b - a
    return float(np.dot(p - a, d) / max(np.dot(d, d), 1e-12)) * float(np.linalg.norm(d))


def chain_weights(s, names, ends, blend):
    w = {names[0]: 1.0}
    for name, at in zip(names[1:], ends):
        t = float(smooth01(at - blend, at + blend, s))
        w = {k: v * (1 - t) for k, v in w.items()}
        w[name] = w.get(name, 0.0) + t
    return w


CLAV_SHARE = float(arg("--clav", "0.7"))
FINGER_BLEND = float(arg("--finger-blend", "0.011"))
WEB_SHARE = float(arg("--web", "0.45"))
ELBOW_BLEND = float(arg("--elbow-blend", "0.055"))   # (ninth pass: from 0.028, with rings 2 cm each side of the elbow: they take about a quarter and three quarters)
KNEE_BLEND = float(arg("--knee-blend", "0.05"))     # (ninth pass: from 0.04 at the knee and the ankle)


KNUCKLE_WEIGHTS = "--old-hand-weights" not in ARGS
KNUCKLE_BEHIND = float(arg("--knuckle-behind", "0.014"))   # metres behind the knuckle where the palm starts to follow the finger
KNUCKLE_PAST = float(arg("--knuckle-past", "0.01"))       # metres past it where the skin is the finger's alone
THENAR_SHARE = float(arg("--thenar-share", "0.35"))
JOINT_BLEND = float(arg("--joint-blend", "0.5"))   # (tenth pass) the middle and end joints blend over this share of the shorter bone each side
KNUCKLE_PALM = float(arg("--knuckle-palm", "0.004"))   # (tenth pass) metres behind the knuckle where the palm side starts to follow the finger


def knuckle_weights(p, part, sfx, at, joints):
    """(ninth pass; fists showed shards along the back of the knuckles) One rule for the palm and the four fingers: the
    skin is the hand bone's behind the knuckle row and the finger's past it, blended across the row itself (from
    KNUCKLE_BEHIND behind each knuckle to KNUCKLE_PAST past it), so the knuckle rounds as a joint does. Before, the palm
    stayed with the hand (at most 45% finger at the webs) and the fingers were wholly theirs from the webs out, so the
    turn of the first bone sheared across the one row of edges at the webs. A palm point between two fingers is shared
    by the two nearest (by its distance across the hand from each finger's line); the middle and end joints blend over
    a third of the shorter bone beside them. The ball of the thumb follows the thumb's first bone a little."""
    Fa, Wr = at["forearm" + sfx], at["hand" + sfx]
    s_w = along(p, Fa, Wr) - np.linalg.norm(Wr - Fa)
    base = chain_weights(s_w, ["forearm" + sfx, "hand" + sfx], [0.0], 0.025)
    back = np.asarray(joints["hand_frame" + sfx][0], float)
    sub = part.split("_")[2] if part.count("_") >= 2 else ""
    info = []
    side_out = {}
    across = at["finger_index_1" + sfx] - at["finger_little_1" + sfx]
    across = across - (across @ back) * back
    across /= np.linalg.norm(across)
    for f in FINGERS:
        a1, a2, a3 = (at["finger_%s_%d%s" % (f, n, sfx)] for n in (1, 2, 3))
        l1, l2 = np.linalg.norm(a2 - a1), np.linalg.norm(a3 - a2)
        u = (a2 - a1) / l1
        d = p - a1
        s = float(d @ u)
        perp = d - s * u
        perp = perp - (perp @ back) * back
        info.append((float(np.linalg.norm(perp)), f, s, l1, l2, a2, a3))
        if f in ("index", "little"):
            side_out[f] = float(perp @ across) * (1.0 if f == "index" else -1.0)
    out_k = 1.0
    if sub in FINGERS:
        shares = [(1.0, next(x for x in info if x[1] == sub))]
    else:
        info.sort(key=lambda x: x[0])
        d0, d1 = info[0][0], info[1][0]
        k = d1 / max(d0 + d1, 1e-6)
        shares = [(k, info[0]), (1.0 - k, info[1])]
        # (a palm point out beyond the index finger's side, toward the thumb's web, or beyond the little finger's
        # edge, stays with the hand: the web to the thumb folded over itself in a fist when it rode the index finger)
        if info[0][1] in side_out:
            out_k = 1.0 - float(smooth01(0.006, 0.014, side_out[info[0][1]]))
    w = {}
    hand_w = base.get("hand" + sfx, 0.0)
    for share, (lat, f, s, l1, l2, a2, a3) in shares:
        names = ["finger_%s_%d%s" % (f, n, sfx) for n in (1, 2, 3)]
        if s > l1 - 0.003:
            s = l1 + max(0.0, along(p, a2, a3))
            if s > l1 + l2 - 0.003:
                s = l1 + l2 + max(0.0, along(p, a3, a3 + (a3 - a2)))
        # (tenth pass: on the palm's side the blend is short, KNUCKLE_PALM behind the knuckle, so the palm's skin does
        # not fold in under the curling finger; the back keeps the long blend that rounds the knuckle)
        hb = float((p - at["finger_%s_1%s" % (f, sfx)]) @ back)
        behind = KNUCKLE_PALM + (KNUCKLE_BEHIND - KNUCKLE_PALM) * float(smooth01(-0.004, 0.003, hb))
        kf = float(smooth01(-behind, KNUCKLE_PAST, s)) * out_k
        c = {"hand" + sfx: 1.0 - kf, names[0]: kf}
        l3 = 0.5 * l2
        for name, at_, b in ((names[1], l1, JOINT_BLEND * min(l1, l2)), (names[2], l1 + l2, JOINT_BLEND * min(l2, l3))):
            t = float(smooth01(at_ - b, at_ + b, s))
            c = {kk: vv * (1 - t) for kk, vv in c.items()}
            c[name] = c.get(name, 0.0) + t
        for kk, vv in c.items():
            w[kk] = w.get(kk, 0.0) + vv * share * hand_w
    w["forearm" + sfx] = base.get("forearm" + sfx, 0.0)
    if sub not in FINGERS and THENAR_SHARE > 0:
        dt = float(np.linalg.norm(p - at["thumb_1" + sfx]))
        kt = THENAR_SHARE * (1 - float(smooth01(0.008, 0.03, dt)))
        if kt > 0 and w.get("hand" + sfx, 0) > 0:
            moved = w["hand" + sfx] * kt
            w["hand" + sfx] -= moved
            w["thumb_1" + sfx] = w.get("thumb_1" + sfx, 0.0) + moved
    return w


def weights_of(M, T, bones, joints):
    at = {n: np.array(p) for n, p, _ in bones}
    P = np.array(M.P)
    out = []
    zt = [float(body_z(BR(845))), float(body_z(BR(680))), NECK_Z - 0.008]
    zn0, zn1 = float(hz(HR(1198))), float(hz(HR(1180)))
    for vi, part in enumerate(M.part):
        p = P[vi]
        fam = part.split("_")[0]
        sfx = "_l" if part.endswith("_l") or "_l_" in part else ("_r" if part.endswith("_r") or "_r_" in part else ("_l" if p[0] >= 0 else "_r"))
        w = {}
        if fam in ("head", "nose", "ear"):
            w = {"head": 1.0}
            if fam == "head" and p[2] < zn1:
                t = float(smooth01(zn0, zn1, p[2]))
                w = {"head": t, "neck": 1 - t}
        elif fam == "torso":
            w = chain_weights(p[2], ["hips", "spine", "chest", "neck"], zt, 0.06)
            for s, sx in ((1, "_l"), (-1, "_r")):
                # (eighth pass) the top of the chest out toward each shoulder rides the clavicle, which lifts the
                # shoulder when the arm goes up (the shoulder cap collapsed into a hard fold with the arm overhead)
                kc = CLAV_SHARE * float(smooth01(0.035, 0.1, s * p[0])) * float(smooth01(at["upper_arm" + sx][2] - 0.09, at["upper_arm" + sx][2] - 0.02, p[2]))
                if kc > 0:
                    moved = w.get("chest", 0.0) * kc + w.get("neck", 0.0) * kc * 0.5
                    if "chest" in w:
                        w["chest"] *= 1 - kc
                    if "neck" in w:
                        w["neck"] *= 1 - kc * 0.5
                    w["clavicle" + sx] = w.get("clavicle" + sx, 0) + moved
                d = np.linalg.norm(p - at["upper_arm" + sx])
                k = 0.45 * (1 - float(smooth01(0.06, 0.14, d)))
                if k > 0:
                    w = {n: v * (1 - k) for n, v in w.items()}
                    w["upper_arm" + sx] = w.get("upper_arm" + sx, 0) + k
                if p[2] < at["hips"][2] + 0.02 and s * p[0] > 0.02:
                    k = 0.5 * (1 - float(smooth01(at["thigh" + sx][2] - 0.05, at["hips"][2] + 0.035, p[2]))) * float(smooth01(0.02, 0.08, s * p[0]))
                    w = {n: v * (1 - k) for n, v in w.items()}
                    w["thigh" + sx] = w.get("thigh" + sx, 0) + k
            if vi in M.tag["crotch"]:
                w = {"hips": 0.6, "thigh_l": 0.2, "thigh_r": 0.2}
        elif fam == "shoulder":
            w = {"chest": 0.2, "clavicle" + sfx: 0.4, "upper_arm" + sfx: 0.4}
        elif fam == "arm":
            J, E, W = at["upper_arm" + sfx], at["forearm" + sfx], at["hand" + sfx]
            Lu = np.linalg.norm(E - J)
            s = along(p, J, E)
            if s > Lu - 0.05:
                s = Lu + along(p, E, W)
            w = chain_weights(s, ["upper_arm" + sfx, "forearm" + sfx, "hand" + sfx], [Lu, Lu + np.linalg.norm(W - E) + 0.005], ELBOW_BLEND)   # (eighth pass: from 0.04 at both joints)
            k = 0.4 * (1 - float(smooth01(0.0, 0.07, s)))
            if k > 0:
                w = {n: v * (1 - k) for n, v in w.items()}
                w["chest"] = w.get("chest", 0) + k * 0.4
                w["clavicle" + sfx] = w.get("clavicle" + sfx, 0) + k * 0.6
        elif fam == "hand" and KNUCKLE_WEIGHTS and (part.split("_")[2] if part.count("_") >= 2 else "") != "thumb":
            w = knuckle_weights(p, part, sfx, at, joints)
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
                w = chain_weights(s, ["hand" + sfx] + names, [0.003, l1, l1 + np.linalg.norm(a3 - a2)], FINGER_BLEND)   # (eighth pass: from 0.007, the fist spiked at the knuckles)
            else:
                Wr = at["hand" + sfx]
                s = along(p, at["forearm" + sfx], Wr) - np.linalg.norm(Wr - at["forearm" + sfx])
                w = chain_weights(s, ["forearm" + sfx, "hand" + sfx], [0.0], 0.025)
                # (eighth pass) the webs and the knuckles' skin follow the fingers' first bones part way (in a fist the
                # webs stayed with the palm and stood out as spikes between the curled fingers)
                roots = [(np.linalg.norm(p - at["finger_%s_1%s" % (f, sfx)]), "finger_%s_1%s" % (f, sfx)) for f in FINGERS]
                roots.sort()
                hand_dir = at["finger_middle_1" + sfx] - at["hand" + sfx]
                past = along(p, at["hand" + sfx], at["finger_middle_1" + sfx]) - np.linalg.norm(hand_dir) + 0.012
                if past > 0:
                    d0, n0 = roots[0]
                    d1, n1 = roots[1]
                    k = WEB_SHARE * float(smooth01(0.0, 0.012, past)) * (1 - float(smooth01(0.008, 0.02, d0)))
                    if k > 0:
                        share = d1 / max(d0 + d1, 1e-6)
                        w = {n: v * (1 - k) for n, v in w.items()}
                        w[n0] = w.get(n0, 0) + k * share
                        w[n1] = w.get(n1, 0) + k * (1 - share)
        elif fam in ("leg", "foot"):
            H, K, A = at["thigh" + sfx], at["shin" + sfx], at["foot" + sfx]
            if fam == "leg":
                z = p[2]
                w = chain_weights(-z, ["thigh" + sfx, "shin" + sfx, "foot" + sfx], [-K[2], -A[2]], KNEE_BLEND)
                k = 0.45 * float(smooth01(H[2] - 0.09, H[2] + 0.03, z))
                if k > 0:
                    w = {n: v * (1 - k) for n, v in w.items()}
                    w["hips"] = w.get("hips", 0) + k
            else:
                fwd = np.array((math.sin(FOOT_YAW) * (1 if sfx == "_l" else -1), -math.cos(FOOT_YAW), 0.0))
                u = float(np.dot(p - A, fwd))
                w = chain_weights(u, ["foot" + sfx, "toe" + sfx], [float(FOOT["ball"][0]) if FOOT else 0.13], 0.025)
                k = 0.5 * float(smooth01(A[2] - 0.02, A[2] + 0.035, p[2]))
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
# Planned UVs: every part a grid of rings, unwrapped as one; seams down his sides, under each arm, inside each leg,
# down the sides of the head behind the ears (the face one big island, the back of the head another); hands back and
# palm; each finger its own island; the soles, nose and ears flat.
# ------------------------------------------------------------------------------------------------------------------

ISLANDS = {
    "torso_front": ("skin", 1.25), "torso_back": ("skin", 1.0), "arm_l": ("skin", 1.0), "arm_r": ("skin", 1.0),
    "hand_l_back": ("skin", 3.0), "hand_l_palm": ("skin", 2.0), "hand_r_back": ("skin", 3.0), "hand_r_palm": ("skin", 2.0),
    "leg_l": ("skin", 0.8), "leg_r": ("skin", 0.8), "sole_l": ("skin", 0.5), "sole_r": ("skin", 0.5),
    "head_front": ("face", 4.0), "head_back": ("face", 1.2), "nose": ("face", 3.0), "ear_l": ("face", 2.0),
    "ear_r": ("face", 2.0), "neck_front": ("skin", 1.5), "neck_back": ("skin", 1.0),
    "head": ("face", 4.0), "neck": ("face", 1.5),
}
ATLAS = {"skin": 1024, "face": 1024}


def grid_uvs(M, rings, faces, seam, up=False):
    P = np.array(M.P)
    where = {}
    for ri, ring in enumerate(rings):
        for j, v in enumerate(ring):
            where.setdefault(v, []).append((ri, j))
    n = len(rings[0])
    arcs = []
    for ring in rings:
        pts = P[ring]
        seg = np.linalg.norm(np.roll(pts, -1, 0) - pts, axis=1)
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
        rset = sorted({r for c in cand for r, _ in c})
        best = None
        for r in rset:
            if r + 1 in rset and all(any(rr in (r, r + 1) for rr, _ in c) for c in cand):
                best = r
                break
        if best is None:
            continue
        ks = []
        for c in cand:
            ri, j = next((rr, jj) for rr, jj in c if rr in (best, best + 1))
            ks.append((ri, (j - seam) % n))
        kk = [k for _, k in ks]
        if max(kk) - min(kk) > n // 2:
            ks = [(ri, k + n if k < n // 2 else k) for ri, k in ks]
        uv = []
        for ri, k in ks:
            a = arcs[ri]
            u = a[k] if k <= n else a[n] + (a[k - n])
            uv.append((u - a[n] / 2.0, vs[ri] if up else -vs[ri]))
        out[fi] = uv
    return out


def planar_uvs(M, faces, ax_u, ax_v, origin=(0, 0, 0)):
    P = np.array(M.P)
    return {fi: [(float(np.dot(P[v] - origin, ax_u)), float(np.dot(P[v] - origin, ax_v))) for v in M.faces[fi]] for fi in faces}


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


def fill_fans(isl, M, step=0.04):
    """Faces of an island left None (fans to a single point) laid from their neighbours' layout."""
    known = {}
    for fi, uv in isl.items():
        if uv is None:
            continue
        for v, q in zip(M.faces[fi], uv):
            known.setdefault(v, q)
    vmax = max(q[1] for q in known.values())
    for fi in [f for f, uv in isl.items() if uv is None]:
        uv = []
        for v in M.faces[fi]:
            if v in known:
                uv.append(known[v])
            else:
                us = [known[w][0] for w in M.faces[fi] if w in known]
                uv.append((float(np.mean(us)), vmax + step))
        isl[fi] = uv


def neck_uvs(M, faces, R=0.065):
    """The neck (and the zip to the torso) unrolled round its own middle line, seamed at his back."""
    P = np.array(M.P)
    rings = M.tag["neck_rings"]
    zs = np.array([P[r][:, 2].mean() for r in rings])
    cys = np.array([P[r][:, 1].mean() for r in rings])
    out = {}
    for fi in faces:
        uv = []
        for v in M.faces[fi]:
            x, y, z = P[v]
            cy = float(np.interp(z, zs, cys))
            uv.append([math.atan2(x, -(y - cy)), float(z)])
        a = [q[0] for q in uv]
        if max(a) - min(a) > math.pi:
            for q in uv:
                if q[0] < 0:
                    q[0] += math.tau
        out[fi] = [(q[0] * R, q[1]) for q in uv]
    return out


def plan_uvs(M, T, H, joints):
    islands = {}
    tf = [fi for fi, c in M.cell.items() if c[0] == "torso" and (c[2] >= 12 or c[2] < 4)]
    tb = [fi for fi, c in M.cell.items() if c[0] == "torso" and 4 <= c[2] < 12]
    islands["torso_front"] = cylinder_uvs(M, T, tf, back=False)
    islands["torso_back"] = cylinder_uvs(M, T, tb, back=True)
    # (second round: the neck, from the torso's top ring to the first head ring under the jaw, is in the skin's
    # picture with the torso, painted from the same views: the seam between the pictures was a bright line across the
    # base of his neck; under the jaw it sits in shadow)
    # (third pass) the base head's own UV map, one island (ears in it), and the neck a grid of its rings, seamed at
    # his back, both in the face's picture (painted from the head sheet, which draws the neck down to the shoulders)
    islands["head"] = dict(M.tag["head_uv"])
    for part, isl in M.tag.get("ear_uv", {}).items():
        islands[part] = dict(isl)
    nf = [fi for fi, p in enumerate(M.fpart) if p == "neck"]
    islands["neck"] = neck_uvs(M, nf)
    for sfx in ("_l", "_r"):
        rings = M.tag["arm_rings" + sfx]
        af = [fi for fi, p in enumerate(M.fpart) if p == "arm" + sfx]
        islands["arm" + sfx] = grid_uvs(M, rings, af, 5)
        lr = M.tag["leg_rings" + sfx]
        if FOOT:
            # (fifth pass) the leg its grid; the base-mesh foot in three planar islands by facing: its top seen from
            # above (with the zip to the leg), its sole from below, its heel and sides from his side
            lf = [fi for fi, p in enumerate(M.fpart) if p == "leg" + sfx and len(M.faces[fi]) == 4]
            islands["leg" + sfx] = grid_uvs(M, lr, lf, 9)
            ff = [fi for fi, p in enumerate(M.fpart) if p == "foot" + sfx]
            P_f = np.array(M.P)
            top, sole, rim = [], [], []
            for fi in ff:
                nf = face_normal(P_f, M.faces[fi])
                nf = nf / max(np.linalg.norm(nf), 1e-12)
                (sole if nf[2] < -0.5 else top if nf[2] > 0.35 or fi in M.tag["foot_zip" + sfx] else rim).append(fi)
            s_ = 1.0 if sfx == "_l" else -1.0
            fwd_ = np.array((math.sin(FOOT_YAW) * s_, -math.cos(FOOT_YAW), 0.0))
            lat_ = np.array((math.cos(FOOT_YAW) * s_, math.sin(FOOT_YAW), 0.0))
            for name, fs, au, av in (("foottop", top, lat_ * s_, fwd_), ("footsole", sole, -lat_ * s_, fwd_),
                                     ("footrim", rim, fwd_, np.array((0.0, 0.0, 1.0)))):
                ISLANDS[name + sfx] = ("skin", 1.0 if name != "footsole" else 0.6)
                if name == "footrim":
                    # (unrolled round the foot: the angle round its middle, scaled to its girth, against height)
                    c0 = P_f[[v for fi in fs for v in M.faces[fi]]].mean(0)
                    isl = {}
                    for fi in fs:
                        uv = []
                        for v in M.faces[fi]:
                            d = P_f[v] - c0
                            ang = math.atan2(float(np.dot(d, lat_)), float(np.dot(d, fwd_)))
                            uv.append((ang * 0.06, float(P_f[v][2])))
                        if max(q[0] for q in uv) - min(q[0] for q in uv) > 0.15:
                            uv = [(q[0] + (math.tau * 0.06 if q[0] < 0 else 0.0), q[1]) for q in uv]
                        isl[fi] = uv
                    islands[name + sfx] = isl
                else:
                    islands[name + sfx] = planar_uvs(M, fs, au, av)
        else:
            lf = [fi for fi, p in enumerate(M.fpart) if p in ("leg" + sfx, "foot" + sfx) and len(M.faces[fi]) == 4]
            islands["leg" + sfx] = grid_uvs(M, lr, lf, 9)
            sole = [fi for fi, p in enumerate(M.fpart) if p == "foot" + sfx and len(M.faces[fi]) == 3]
            islands["sole" + sfx] = planar_uvs(M, sole, np.array((1.0, 0, 0)), np.array((0, -1.0, 0)))
        # (fourth pass) The hands laid out as the hands sheet's back and palm views see the open hand (the base hand's
        # own UV map overlaps between back and palm, and the sheet's paint projected through it came out a mosaic):
        # each face by which way it faces in the open pose, the back's (along, across) and the palm's mirrored; the
        # thumb its own pair (open, it lies over the palm's edge); the zip to the forearm unrolled round the wrist.
        hf = M.tag["hand_faces" + sfx]
        Lo = HAND["open"]
        F0 = HAND["faces"]
        fnr = np.array([face_normal(Lo, f) for f in F0])
        cen = np.array([Lo[f].mean(0) for f in F0])
        sgn = 1.0 if float(((cen - Lo.mean(0)) * fnr).sum()) > 0 else -1.0
        isl = {"handback": {}, "handpalm": {}, "handbackthumb": {}, "handpalmthumb": {}}
        for i, (fi, f) in enumerate(zip(hf, F0)):
            thumb = all(HAND["part"][v] == "thumb" for v in f)
            back = sgn * fnr[i][2] >= 0
            uv = [(float(Lo[v][0]), float(-Lo[v][1] if back else Lo[v][1])) for v in f]
            # (the face's corners in the order the body's face has them: the winding may have been turned)
            mf = M.faces[fi]
            first = M.tag["hand_points" + sfx][0]
            order = [list(f).index(v - first) for v in mf]
            isl[("handback" if back else "handpalm") + ("thumb" if thumb else "")][fi] = [uv[k] for k in order]
        for name, share in (("handback", 2.6), ("handpalm", 2.0), ("handbackthumb", 2.6), ("handpalmthumb", 2.0)):
            ISLANDS[name + sfx] = ("skin", share)
            islands[name + sfx] = isl[name]
        Tb, Wd, L = (np.array(v, float) for v in joints["hand_frame" + sfx])
        Wr = np.array(joints["wrist_l"], float) * np.array((1.0 if sfx == "_l" else -1.0, 1.0, 1.0))
        P_ = np.array(M.P)
        zw = {}
        for fi in M.tag["hand_zip" + sfx]:
            q = P_[M.faces[fi]] - Wr
            ang = np.arctan2(q @ Wd, q @ Tb)
            if ang.max() - ang.min() > math.pi:
                ang = np.where(ang < 0, ang + math.tau, ang)
            zw[fi] = [(float(a_ * 0.025), float(b_)) for a_, b_ in zip(ang, q @ L)]
        ISLANDS["wrist" + sfx] = ("skin", 1.0)
        islands["wrist" + sfx] = zw
    missing = [fi for fi in range(len(M.faces)) if not any(fi in isl for isl in islands.values())]
    if missing:
        print("BOY UV: %d faces in no island: %s" % (len(missing), sorted({M.fpart[f] for f in missing})))
    return islands


def pack(islands, pad_px=6):
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
# Paint
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


def blur(img, n=1):
    out = img.copy()
    for _ in range(n):
        out = (out + np.roll(out, 1, 0) + np.roll(out, -1, 0) + np.roll(out, 1, 1) + np.roll(out, -1, 1)) / 5.0
    return out


def fill_out(rgb, valid, rounds=64):
    """What is not valid filled from round it: a pull-push pyramid, softened in the gaps."""
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
    out[gaps] = blur(col, 2)[gaps]
    return out


DELIGHT = float(arg("--delight", "0.75"))


def delight(rgb, hit, k, cell=16):
    """The picture's broad light and shade (each texel's brightness against a wide, island-aware average) taken out
    by the share k, its colour and small marks (freckles, nails, creases) kept."""
    if k <= 0:
        return rgb
    lum = rgb.mean(-1)
    n = rgb.shape[0] // cell
    w = hit.astype(float)
    sl = (lum * w)[:n * cell, :n * cell].reshape(n, cell, n, cell).sum((1, 3))
    sw = w[:n * cell, :n * cell].reshape(n, cell, n, cell).sum((1, 3))
    low = sl / np.maximum(sw, 1e-6)
    low3 = fill_out(np.repeat(low[..., None], 3, 2), sw > cell * 2, 32)[..., 0]
    up = np.repeat(np.repeat(low3, cell, 0), cell, 1)
    for _ in range(12):
        up = (up + np.roll(up, 1, 0) + np.roll(up, -1, 0) + np.roll(up, 1, 1) + np.roll(up, -1, 1)) / 5.0
    mean = float(np.median(lum[hit]))
    g = (mean / np.maximum(up, 1e-3)) ** k
    out = rgb.copy()
    out[hit] = np.clip(rgb[hit] * np.clip(g[hit], 0.75, 1.35)[:, None], 0, 1)
    return out


def pad_edges(rgb, hit, n=10):
    """(third round) Each island's edge colour carried out into the gutter round it, a texel a round, so that
    filtering and mipmaps at a seam blend the island with its own colour, not the gutter's blurred average (a light
    line showed along the seam round the base of his neck)."""
    out = rgb.copy()
    done = hit.copy()
    for _ in range(n):
        acc = np.zeros_like(out)
        cnt = np.zeros(done.shape)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            m = np.roll(np.roll(done, dy, 0), dx, 1)
            acc += np.roll(np.roll(out, dy, 0), dx, 1) * m[..., None]
            cnt += m
        new = ~done & (cnt > 0)
        out[new] = acc[new] / cnt[new][:, None]
        done |= new
    return out


def is_shorts(c):
    """The sheet's cream shorts: pale, low in saturation, yellowish."""
    mx, mn = c.max(-1), c.min(-1)
    return (mn > 0.62) & (mx - mn < 0.2) & (c[..., 2] < c[..., 0])


def is_hair(c):
    """His golden hair (yellower than skin: green well above blue). Skin is about (0.72, 0.58, 0.52), hair about
    (0.75, 0.6, 0.36), its shade (0.45, 0.35, 0.22)."""
    return (c[..., 1] - c[..., 2] > 0.12) & (c[..., 0] > c[..., 2] + 0.15)


def paint_skin(M, face_uv, sh, tris_all, Pc, no_arms_c, joints):
    """His body's picture: front and back views for all of him, the side view (his right; mirrored for his left)
    for the trunk and legs."""
    P = np.array(M.P)
    tris = M.tris()
    N = normals_of(P, tris)
    pos, nrm, hit, fid = texel_geometry(M, face_uv, "skin", P, N)
    size = ATLAS["skin"]
    fam_face = np.array([p.split("_")[0] for p in M.fpart] + ["none"])
    tex_fam = fam_face[fid]
    acc = np.zeros((size, size, 3))
    wsum = np.zeros((size, size))
    # (fifth pass: eroded further and grazing views weighed less, and the sheet's dark outline strokes passed over:
    # projected at a slant they lay brown streaks down his arms, legs and sides)
    mask = erode(sh.body_mask, 6)
    (pc0, pr0), (pc1, pr1) = SIDE_PATCH
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
        seen = (qd <= zb[rows, cols] + 0.012) & mask[rows, cols] & (facing > 0.2) & hit.ravel()
        if view == "side":
            seen &= ~np.isin(tex_fam.ravel(), ("arm", "hand", "shoulder"))
            seen &= ~((cols >= pc0) & (cols <= pc1) & (rows >= pr0) & (rows <= pr1))
        colour = sh.body_pix[rows, cols]
        seen &= ~is_hair(colour)
        w = np.where(seen, facing ** 3 * smooth01(0.36, 0.5, colour.mean(-1)), 0.0)
        acc += (colour * w[:, None]).reshape(size, size, 3)
        wsum += w.reshape(size, size)
    good = wsum > 0.02
    rgb = acc / np.maximum(wsum, 1e-6)[..., None]
    z = pos[..., 2]
    box = hit & np.isin(tex_fam, ("torso", "leg")) & (z < body_z(BOXERS[0] + 8)) & (z > body_z(BOXERS[1] - 6))
    box |= good & is_shorts(rgb)
    good &= ~box
    print("BOY paint skin: %d texels under the shorts filled" % int(box.sum()))
    rgb = fill_out(rgb, good, 300)
    rgb = np.where(good[..., None], rgb, blur(rgb, 4))
    if RULE_PAINT:
        rgb = rule_paint(M, face_uv, "skin", pos, nrm, hit, tex_fam, joints)
    crease_k = (0.94, 0.98) if RULE_PAINT else (0.87, 0.95)
    hands = hit & (tex_fam == "hand")
    if hands.any():
        # (second round: the hand one tone with the forearm's skin, faded into it over the wrist, so no line shows
        # there or where the fingers' islands meet the palm's; the forms painted small: nails, creases, a redder palm)
        arm_skin = np.median(rgb[good & (tex_fam == "arm")], axis=0)
        base_c = np.median(rgb[hands & good], axis=0) if (hands & good).any() else arm_skin
        base_c = base_c * 0.5 + arm_skin * 0.5
        fparts = np.array(list(M.fpart) + ["none"])[fid]
        for sfx in ("_l", "_r"):
            Tb, Wd, L = (np.array(v, float) for v in joints["hand_frame" + sfx])
            FN = np.array([face_normal(M.P, f) for f in M.faces] + [np.zeros(3)])
            fn_back = (FN[fid] * Tb).sum(-1)
            Wr = np.array(joints["wrist_l"], float) * np.array((1.0 if sfx == "_l" else -1.0, 1.0, 1.0))
            from_wrist = ((pos - Wr) * L).sum(-1)
            mine_arm = hit & np.isin(tex_fam, ("arm", "hand")) & (np.sign(pos[..., 0]) == (1.0 if sfx == "_l" else -1.0))
            t = smooth01(-0.04, 0.012, from_wrist)
            k = mine_arm & (t > 0)
            rgb[k] = rgb[k] * (1 - t[k][:, None]) + base_c * t[k][:, None]
            mine = hands & np.char.startswith(fparts.astype(str), "hand" + sfx)
            back = (nrm * Tb).sum(-1)
            # (by the face's own facing, as the layout splits back and palm: per texel, the fingers' roots took the
            # palm's tint in a band)
            palm = mine & (fn_back < 0) & ~np.char.count(fparts.astype(str), "_").__ge__(2)
            rgb[palm] *= np.array((1.02, 0.94, 0.91))
            for name in FINGERS + ("thumb",):
                f_ = mine & (fparts == "hand%s_%s" % (sfx, name))
                bones = [np.array(b, float) for b in joints[name + sfx]]
                up_ = Tb if name != "thumb" else np.array(joints["thumb_back" + sfx], float)
                bk = (nrm * up_).sum(-1)
                for j in (1, 2):
                    a_ = bones[j + 1] - bones[j - 1]
                    a_ /= max(np.linalg.norm(a_), 1e-9)
                    t_ = ((pos - bones[j]) * a_).sum(-1)
                    if RULE_PAINT:
                        # (ninth pass: the hard 2 mm lines read as thin dark cuts across the fingers in the lit
                        # close-ups: a soft rosy shade over the joint instead)
                        wk = (f_ & (bk > 0.0)) * np.exp(-(t_ / 0.0035) ** 2) * smooth01(0.0, 0.4, bk) * 0.15
                        rgb = blush(rgb, wk)
                        continue
                    rgb[f_ & (bk > 0.15) & (np.abs(t_) < 0.0009)] *= crease_k[0]
                    rgb[f_ & (bk > 0.15) & (np.abs(t_ - 0.0027) < 0.0007)] *= crease_k[1]
                a_ = bones[3] - bones[2]
                a_ /= max(np.linalg.norm(a_), 1e-9)
                t_ = ((pos - bones[3]) * a_).sum(-1)
                nail = f_ & (bk > 0.35) & (t_ > -0.011) & (t_ < 0.004)
                rgb[nail] = rgb[nail] * 0.55 + np.array((0.93, 0.8, 0.76)) * 0.45
                rim = nail & ((np.abs(t_ + 0.011) < 0.001) | (bk < 0.45))
                rgb[rim] *= 0.93 if RULE_PAINT else 0.84
                rgb[f_ & (bk < -0.2) & (t_ > -0.014)] *= np.array((1.04, 0.95, 0.93))
            for name in FINGERS:
                k0 = np.array(joints[name + sfx][0], float)
                # (ninth pass: soft, not a hard-edged disc)
                kw = (mine & (back > 0.2)) * np.exp(-(np.linalg.norm(pos - k0, axis=-1) / 0.007) ** 2) * smooth01(0.2, 0.6, back)
                rgb = rgb * (1.0 + 0.05 * kw[..., None])
    if FOOT:
        # (fifth pass) toenails on the base-mesh feet, by rule: on the toes' upper faces, behind each toe's front
        # (the front measured from the foot's own points in strips across it); the soles a little pinker
        Pm_ = np.array(M.P)
        for sfx, s_ in (("_l", 1.0), ("_r", -1.0)):
            a_, b_ = M.tag["foot_points" + sfx]
            A_ = np.array(joints["ankle" + sfx], float)
            fw_ = np.array((math.sin(FOOT_YAW) * s_, -math.cos(FOOT_YAW), 0.0))
            lt_ = np.array((math.cos(FOOT_YAW), math.sin(FOOT_YAW) * s_, 0.0))
            Q_ = Pm_[a_:b_] - A_
            qu, qv = Q_ @ fw_, Q_ @ lt_
            bins = np.linspace(qv.min(), qv.max(), 33)
            front = np.full(32, -1.0)
            for i in range(32):
                m_ = (qv >= bins[i]) & (qv < bins[i + 1])
                if m_.any():
                    front[i] = qu[m_].max()
            mine = hit & (tex_fam == "foot") & (np.sign(pos[..., 0]) == s_)
            d_ = pos - A_
            tu, tv = d_ @ fw_, d_ @ lt_
            bi = np.clip(np.digitize(tv, bins) - 1, 0, 31)
            fr_ = front[bi]
            # (the big toe's nail longer: it is the strip with the furthest front on his inner side)
            inner_side = tv * s_ * np.sign(lt_[0]) < 0
            nl = np.where(inner_side & (fr_ > qu.max() - 0.012), 0.012, 0.007)
            nail = mine & (nrm[..., 2] > 0.3) & (tu > fr_ - nl - 0.002) & (tu < fr_ - 0.0015) & (fr_ > qu.max() - 0.06)
            rgb[nail] = rgb[nail] * 0.62 + np.array((0.95, 0.8, 0.76)) * 0.38
            rgb[mine & (nrm[..., 2] < -0.5)] *= np.array((1.03, 0.95, 0.93))
    print("BOY paint skin: %.0f%% of its texels seen by a view" % (100.0 * (good & hit).sum() / max(hit.sum(), 1)))
    return pad_edges(rgb, hit), pos, hit


def paint_head(M, face_uv, sh):
    """His head's picture from the head sheet's bald row (second pass; the face trial made him a round-cheeked man):
    the front view wherever the surface faces within about 50 degrees of forward, the back view likewise behind, the
    side view (his right; mirrored for his left) between, each texel from one view but for a narrow hand-over, so no
    feature is laid down twice. The side view's eye and brow in profile are not taken (on his temple they would be a
    second eye); the nose's underside is filled from the nose round it, with two small nostrils."""
    P = np.array(M.P)
    tris = M.tris()
    tf = M.tri_fams()
    head_tris = [t for t, f in zip(tris, tf) if f in ("head", "nose", "ear", "neck")]
    N = normals_of(P, tris)
    pos, nrm, hit, fid = texel_geometry(M, face_uv, "face", P, N)
    size = ATLAS["face"]
    Nall = nrm.reshape(-1, 3)
    ff = np.clip(-Nall[:, 1], 0, 1)
    fb = np.clip(Nall[:, 1], 0, 1)
    wf = smooth01(0.58, 0.72, ff)
    wb = smooth01(0.58, 0.72, fb) * (1 - wf)
    share = {"hfront": wf, "hback": wb, "hside": (1 - wf) * (1 - wb)}
    acc = np.zeros((size * size, 3))
    wsum = np.zeros(size * size)
    side_hole = np.zeros(size * size, bool)
    mask = erode(sh.head_mask, 5)
    per = []
    for view, mirrored in (("hfront", False), ("hback", False), ("hside", False), ("hside", True)):
        Q = pos.reshape(-1, 3).copy()
        Nn = nrm.reshape(-1, 3).copy()
        Pm = P.copy()
        if mirrored:
            Q[:, 0] *= -1
            Nn[:, 0] *= -1
            Pm[:, 0] *= -1
        P2, dep = project(view, Pm)
        zb, _ = raster(P2, dep, head_tris, mask.shape)
        q2, qd = project(view, Q)
        _, facing = screen_dir(view, Nn)
        cols = np.clip(q2[:, 0].astype(int), 0, mask.shape[1] - 1)
        rows = np.clip(q2[:, 1].astype(int), 0, mask.shape[0] - 1)
        seen = (qd <= zb[rows, cols] + 0.006) & mask[rows, cols] & (facing > 0.15) & hit.ravel()
        if view == "hside":
            # (fourth pass: the profile's eye, nose, smile line and mouth are not taken at all: laid on the model's
            # cheek at a slant they drew dark streaks from the eye's corner and beside the mouth; the front view has them)
            cut = ((cols > 1533) & (rows > HR(922)) & (rows < HR(978))) | ((cols > 1498) & (rows > HR(900)) & (rows < HR(1120)))
            side_hole |= seen & cut
            seen &= ~cut
        colour = sh.head_pix[rows, cols]
        # (fifth pass: the sheet's dark outline strokes passed over, as on the body)
        seen &= (colour.mean(-1) > 0.4) | (facing > 0.6)
        w = np.where(seen, share[view] * np.clip(facing, 0, 1) + 1e-4 * np.clip(facing, 0, 1), 0.0)
        per.append((view, seen, colour, w))
    # (third pass) each view toned to the front view where they both see him (the sheet paints his sides and back
    # in shade: on the model the back of his head came out far darker than his face)
    def ratio(a, b, sel):
        if sel.sum() < 50:
            return np.ones(3)
        return np.median(a[sel], axis=0) / np.maximum(np.median(b[sel], axis=0), 1e-3)
    fr = [p for p in per if p[0] == "hfront"][0]
    sides = [p for p in per if p[0] == "hside"]
    bk = [p for p in per if p[0] == "hback"][0]
    ffv, fbv = ff, fb
    band_fs = (ffv > 0.35) & (ffv < 0.8)
    g_side = np.mean([ratio(fr[2], s[2], fr[1] & s[1] & band_fs) for s in sides], axis=0)
    band_sb = (fbv > 0.35) & (fbv < 0.8)
    g_back = g_side * np.mean([ratio(s[2], bk[2], s[1] & bk[1] & band_sb) for s in sides], axis=0)
    g_side, g_back = np.clip(g_side, 0.7, 1.6), np.clip(g_back, 0.7, 1.8)
    print("BOY face paint: the side view toned by %s, the back by %s" % (np.round(g_side, 3), np.round(g_back, 3)))
    for view, seen, colour, w in per:
        g = g_side if view == "hside" else g_back if view == "hback" else np.ones(3)
        acc += np.clip(colour * g, 0, 1) * w[:, None]
        wsum += w
    good = (wsum > 0.01).reshape(size, size)
    good &= ~(side_hole.reshape(size, size) & (wf.reshape(size, size) < 0.6))
    rgb = (acc / np.maximum(wsum, 1e-6)[:, None]).reshape(size, size, 3)
    fam_t = np.array([part_family(p) for p in M.fpart] + ["none"])[fid]
    nz = nrm[..., 2]
    nose_under = hit & (fam_t == "nose") & (nz < -0.4)
    good &= ~nose_under
    rgb = fill_out(rgb, good, 200)
    rgb[nose_under] *= 0.96
    xa = np.abs(pos[..., 0])
    ys = pos[..., 1]
    if nose_under.any():
        y0, y1 = float(ys[nose_under].min()), float(ys[nose_under].max())
        nostril = nose_under & (np.abs(xa - 0.008) < 0.004) & (ys > y0 + 0.25 * (y1 - y0)) & (ys < y0 + 0.8 * (y1 - y0))
        rgb[nostril] *= 0.7
    # (fifth pass, the critic: "cords painted on the neck") the neck below his jaw one soft tone: the sheet's drawn
    # tendons blurred away
    neck_t = hit & (fam_t == "neck")
    if neck_t.any():
        soft = blur(fill_out(np.where(neck_t[..., None], rgb, 0), neck_t, 16), 10)
        rgb[neck_t] = rgb[neck_t] * 0.3 + soft[neck_t] * 0.7
    rgb = np.where(good[..., None], rgb, blur(rgb, 2))
    print("BOY paint face: %.0f%% of its texels seen by a view" % (100.0 * (good & hit).sum() / max(hit.sum(), 1)))
    return pad_edges(rgb, hit), pos, hit


# ------------------------------------------------------------------------------------------------------------------
# Forms in the mesh
# ------------------------------------------------------------------------------------------------------------------

# (row, {column offset from the front middle: (forward, outward[, up])}) in metres; mirrored left and right. A boy's
# forms, soft: collarbones and the trapezius into the neck, small pecs with a fold under them, the breastbone, the
# ribcage narrowing into the waist, the navel, the shoulder blades and the spine's groove at his back.
# (third round: about twice as strong: in plain grey the first rounds' forms did not read)
BODY_FORMS = {
    430: {2: (0.0, 0.004, 0.01), 3: (0.0, 0.005, 0.012), 4: (0.0, 0.004, 0.01), 5: (0.0, 0.0, 0.008), 6: (0.0, 0.0, 0.005)},
    448: {0: (-0.003, 0.0), 1: (0.008, 0.0, 0.002), 2: (0.009, 0.0, 0.003), 6: (-0.004, 0.0), 7: (-0.004, 0.0)},
    # (fifth round: more contrast between neighbours: the pecs forward, the breastbone and the fold under them in;
    # the blades out, the spine and the blades' lower edge in: the same moves made evenly read as no form at all)
    480: {1: (-0.003, 0.0), 2: (-0.003, 0.0), 6: (-0.009, 0.0), 7: (-0.008, 0.0), 8: (0.006, 0.0)},
    520: {0: (-0.005, 0.0), 1: (0.010, 0.0), 2: (0.012, 0.0), 6: (-0.013, 0.0), 7: (-0.010, 0.0), 8: (0.007, 0.0)},
    560: {0: (-0.006, 0.0), 1: (0.016, 0.0), 2: (0.016, 0.0), 3: (0.006, 0.0), 6: (-0.009, 0.0), 7: (-0.006, 0.0), 8: (0.007, 0.0)},
    600: {0: (-0.003, 0.0), 1: (-0.007, 0.0), 2: (-0.008, 0.0), 3: (-0.004, 0.0), 6: (0.004, 0.0), 7: (0.003, 0.0), 8: (0.007, 0.0)},
    660: {3: (0.0, 0.004), 4: (0.0, 0.004), 8: (0.006, 0.0)},
    720: {3: (0.0, -0.004), 4: (0.0, -0.006), 5: (0.0, -0.004), 8: (0.006, 0.0)},
    750: {0: (-0.006, 0.0), 3: (0.0, -0.004), 4: (0.0, -0.006), 5: (0.0, -0.004), 8: (0.005, 0.0)},
}
# (fifth pass) keyed by the new sheet's rows; a slight boy: the forms halved (flat chest, no pecs to speak of)
BODY_FORMS = {BR(r): v for r, v in BODY_FORMS.items()}
BODY_FORM_K = float(arg("--forms", "0.8"))   # (third pass: from 1.35, the forms still faint in grey; fifth: 0.8)
KNEE_FORM = {1: 0.008, 0: 0.004, 2: 0.004}   # (ninth pass: from 0.014 and 0.007: the bent knee came to a point)
ELBOW_FORM = {7: 0.007, 8: 0.007, 6: 0.003, 9: 0.003}   # (ninth pass: from 0.017 and 0.008: a spike at the bent elbow)


def sculpt_body(M):
    T = M.tag["torso_rings"]
    P = np.array(M.P)
    holes = set(M.tag["hole_l"]) | set(M.tag["hole_r"])
    for row, moves in BODY_FORMS.items():
        ring = T[TORSO_ROWS.index(row)]
        for k, mv in moves.items():
            # (second pass: a third stronger again, soft; the coordinator: "stronger (but soft) torso forms in grey")
            # (fourth pass: only the forward moves take the full factor; outward and upward moves change his outline,
            # and at 1.7 the trapezius' lift and the waist's moves opened the front and back outline gap above the
            # shorts from 1.5 to 3.7 cm)
            fwd, out = mv[0] * BODY_FORM_K, mv[1] * min(BODY_FORM_K, 1.0)
            up = (mv[2] if len(mv) > 2 else 0.0) * min(BODY_FORM_K, 1.0)
            for kk in {k % TORSO_N, (-k) % TORSO_N}:
                v = ring[kk]
                if v in holes:
                    continue
                P[v][1] -= fwd
                P[v][0] += math.copysign(out, P[v][0]) if abs(P[v][0]) > 1e-4 else 0.0
                P[v][2] += up
    for sfx in ("_l", "_r"):
        ring = M.tag["leg_rings" + sfx][LEG_ROWS.index(KNEE_ROW) + 1]
        for j, fwd in KNEE_FORM.items():
            P[ring[j]][1] -= fwd
        # (fourth pass) the ankle bones: the outer one on the leg's last ring, the inner one a ring higher
        lr = M.tag["leg_rings" + sfx]
        for ring, js in ((lr[len(LEG_ROWS)], (3, 4)), (lr[len(LEG_ROWS) - 1], (8, 9))):
            c = P[ring].mean(0)
            for j in js:
                d = P[ring[j]] - c
                d[2] = 0.0
                P[ring[j]] += d / max(np.linalg.norm(d), 1e-9) * ANKLE_BONE
        # the elbow's point at the back of the arm (the ring at the elbow; ring points 7 and 8 face back)
        st = M.tag["arm_stations" + sfx]
        Lu = st[6]
        ring = M.tag["arm_rings" + sfx][6]
        c = P[ring].mean(0)
        for j, out in ELBOW_FORM.items():
            d = P[ring[j]] - c
            P[ring[j]] += d / max(np.linalg.norm(d), 1e-9) * out
    M.P = [p for p in P]


def unfold_head(M, tries=8):
    """(sixth pass; the critic: 49 folded triangles round the eyes, 68 in all) The head's and neck's folded triangles,
    by where they are (near an eye's middle or not), and their points with a ring round them smoothed (Taubin, which
    keeps the size) until none is left; the eyelids' own rim (the open edge round each eye) is held still."""
    fams = np.array([part_family(p) for p in M.part])
    head = np.isin(fams, ("head", "neck", "ear", "nose"))
    tf = M.faces
    ec = {}
    for f in tf:
        for i in range(len(f)):
            e = (min(f[i], f[(i + 1) % len(f)]), max(f[i], f[(i + 1) % len(f)]))
            ec[e] = ec.get(e, 0) + 1
    rim = np.zeros(len(M.P), bool)
    for (a, b), c in ec.items():
        if c == 1:
            rim[a] = rim[b] = True
    for v in M.tag.get("lid_hold", []):
        rim[v] = True
    eye = np.array(M.P)[M.tag["head_eye"]].mean(0)
    eyes = (eye, eye * np.array((-1.0, 1.0, 1.0)))
    for k in range(tries):
        P = np.array(M.P)
        n, bad = folded(P, M.faces)
        pts = np.zeros(len(P), bool)
        pts[np.unique(bad)] = True
        pts &= head
        if k == 0:
            de = np.minimum(*[np.linalg.norm(P - c, axis=1) for c in eyes])
            print("BOY head folds before unfolding: %d points, %d of them within 2.5 cm of an eye" % (int(pts.sum()), int((pts & (de < 0.025)).sum())))
        if not pts.any():
            break
        sel = pts.copy()
        for a, b in edges_of(M.faces):
            if pts[a] or pts[b]:
                sel[a] = sel[b] = True
        taubin(M, sel & head & ~rim, rounds=3)
    n, bad = folded(np.array(M.P), M.faces)
    print("BOY head unfolded: %d folded triangles left in all" % n)


def unfold_body(M, tries=6, ring=True):
    """(third pass) Triangles of the body folded against their neighbours (19 of them: at the armpits, the shoulders
    and the elbows, where the arm's rings meet the torso's and the forms push points past each other): their points
    and the ring round them smoothed until none is left (the head, hands and feet are not touched)."""
    fams = np.array([part_family(p) for p in M.part])
    body = np.isin(fams, ("torso", "shoulder", "arm", "leg"))
    for k in range(tries):
        n, bad = folded(np.array(M.P), M.faces)
        pts = np.zeros(len(M.P), bool)
        pts[np.unique(bad)] = True
        pts &= body
        if not pts.any():
            break
        E = edges_of(M.faces)
        sel = pts.copy()
        if ring:
            for a, b in E:
                if pts[a] or pts[b]:
                    sel[a] = sel[b] = True
        taubin(M, sel & body, rounds=3)
        print("BOY unfolding the body, try %d: %d folded triangles, %d points smoothed" % (k + 1, n, int((sel & body).sum())))


def smooth_hands(M, rounds=4, lam=0.45, mu=-0.47):
    P = np.array(M.P)
    E = edges_of(M.faces)
    fams = np.array([part_family(p) for p in M.part])
    sel = fams == "hand"
    # (second round: the forearm's last ring too, so the wrist runs into the hand with no hard step)
    for sfx in ("_l", "_r"):
        sel[M.tag["arm_rings" + sfx][-1]] = True
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


def taubin(M, sel, rounds=4, lam=0.5, mu=-0.53, weight=None):
    """Taubin's two-step smoothing of the selected points (keeps their volume): soft forms, no ring-by-ring bands."""
    P = np.array(M.P)
    E = edges_of(M.faces)
    deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
    sel = sel & (deg > 0)
    k = np.ones(len(P)) if weight is None else weight
    for _ in range(rounds):
        for f in (lam, mu):
            acc = np.zeros_like(P)
            np.add.at(acc, E[:, 0], P[E[:, 1]])
            np.add.at(acc, E[:, 1], P[E[:, 0]])
            avg = acc / np.maximum(deg, 1)[:, None]
            P[sel] += (avg[sel] - P[sel]) * (f * k[sel])[:, None]
    M.P = [p for p in P]


def smooth_shoulders(M):
    """(second round) The shoulders' tops came out as square corners where the arm's root ring meets the torso's
    rings (the grey render: "shoulder pads"): the torso and arm points round each arm's root smoothed, more so near it."""
    P = np.array(M.P)
    fams = np.array([part_family(p) for p in M.part])
    w = np.zeros(len(P))
    for sfx in ("_l", "_r"):
        c = P[M.tag["hole" + sfx]].mean(0)
        d = np.linalg.norm(P - c, axis=1)
        w = np.maximum(w, np.clip(1.0 - d / 0.13, 0.0, 1.0))
    sel = np.isin(fams, ("torso", "shoulder", "arm")) & (w > 0)
    taubin(M, sel, rounds=6, weight=w)


def smooth_armpits(M, reach=0.08, rounds=12):
    P = np.array(M.P)
    E = edges_of(M.faces)
    fams = np.array([part_family(p) for p in M.part])
    moved = 0
    for sfx in ("_l", "_r"):
        hole = M.tag["hole" + sfx]
        low = P[hole][np.argmin(P[hole][:, 2])]
        sel = (fams == "torso") & (np.linalg.norm(P - low, axis=1) < reach)
        sel[hole] = False
        sel &= np.bincount(E.ravel(), minlength=len(P)) > 0
        w = np.clip(1.0 - np.linalg.norm(P - low, axis=1) / reach, 0, 1)[:, None] * 0.6
        before = P[sel].copy()
        for _ in range(rounds):
            acc = np.zeros_like(P)
            np.add.at(acc, E[:, 0], P[E[:, 1]])
            np.add.at(acc, E[:, 1], P[E[:, 0]])
            deg = np.bincount(E.ravel(), minlength=len(P))[:, None]
            avg = acc / np.maximum(deg, 1)
            P[sel] += (avg[sel] - P[sel]) * w[sel]
        moved = max(moved, float(np.linalg.norm(P[sel] - before, axis=1).max()) if sel.any() else 0.0)
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
            if abs(P[b][0]) > max(abs(P[a][0]), abs(P[c][0])) + 0.012:
                P[b][0] = math.copysign(ref, P[b][0])
                spikes += 1
    M.P = [p for p in P]
    print("BOY armpits smoothed: the most a point moved %.1f cm; %d spikes put back" % (moved * 100, spikes))


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


# ------------------------------------------------------------------------------------------------------------------
# Refining the face: the head's front half split once, the face (brow to chin) once more; new points on curved edges
# placed on the cubic between the corners' normals (PN triangles), so the head stays round. UVs, weights, parts kept.
# ------------------------------------------------------------------------------------------------------------------

def refine(M, sel, face_uv, weights):
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
            w = {}
            for src in (weights[a], weights[b]):
                for k, v in src.items():
                    w[k] = w.get(k, 0.0) + v / 2.0
            W.append(w)
        return mid[key]
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


def bump(row, col, r0, c0, sr, sc):
    return np.exp(-(((row - r0) / sr) ** 2 + ((np.abs(col) - c0) / sc) ** 2))


# The face's forms (head-sheet rows, and columns out from his middle, both sides alike; head pixels of 0.635 mm),
# measured off the bald front view: brows at row 905, the eyes at 948 (74 out), the cheeks' apples at 1000 (92 out),
# the nose's base 1046, the mouth 1082 (a keen closed smile, its corners up at 1076, 50 out), the chin's ball 1145.
# A thirteen-year-old's: a soft brow, big eyes in shallow sockets, soft cheeks, modelled lips, a pointed chin.
# (row, column, row spread, column spread, metres out along the surface; negative in)
FACE_FORMS = (
    # the brow, soft, and the forehead rounding above it
    (905, 38, 9, 20, 0.003), (902, 78, 9, 24, 0.004), (906, 112, 9, 16, 0.002),
    # the eye sockets, shallow; the big eyeball's swell in them; the upper lid's crease and edge; the lower lid
    (948, 74, 16, 26, -0.007), (950, 74, 10, 19, 0.0045), (934, 74, 4.0, 22, -0.0012), (964, 74, 4.0, 20, 0.001),
    # the bridge of the nose between the eyes stays up
    (948, 0, 16, 13, 0.003),
    # the cheeks' apples, soft and round (the smile lifts them), the hollow under the cheekbone
    (1002, 92, 22, 34, 0.006), (1062, 118, 18, 18, -0.003),
    # the folds from the nose's wings toward the mouth's corners
    (1054, 50, 14, 8, -0.002), (1068, 56, 10, 6, -0.0015),
    # the upper lip and its groove, the mouth's line curving up at its corners, the lower lip, the corners' dimples
    (1064, 0, 7, 36, 0.004), (1058, 0, 7, 6, -0.0012), (1078, 0, 2.4, 50, -0.005), (1075, 44, 2.6, 16, -0.003),
    (1090, 0, 6, 30, 0.0048), (1073, 64, 5, 6, -0.003),
    # the groove under the lower lip, the chin's ball (pointed: narrow)
    (1114, 0, 5, 22, -0.003), (1146, 0, 12, 18, 0.004),
    # the temples, a little hollow; the jaw's edge
    (912, 138, 18, 16, -0.002), (1128, 84, 10, 18, 0.0015),
)


def sculpt_head(M):
    P = np.array(M.P)
    N = normals_of(P, M.tris())
    row = hrow(P[:, 2])
    col = P[:, 0] / HS
    # (third round: moved along the direction out from the head's middle at each height, not along the points'
    # own normals: those are uneven where the refined face meets the coarser head, and the forms came out as
    # horizontal streaks)
    cy = np.array([head_centre(M, z)[1] for z in P[:, 2]])
    R = np.stack([P[:, 0], P[:, 1] - cy, np.zeros(len(P))], 1)
    N = R / np.maximum(np.linalg.norm(R, axis=1, keepdims=True), 1e-9)
    facing = -N[:, 1]
    fam = np.array([part_family(p) for p in M.part])
    on = (fam == "head")
    w = np.clip((facing - 0.05) / 0.35, 0.0, 1.0) * on
    d = np.zeros(len(P))
    for r0, c0, sr, sc, amount in FACE_FORMS:
        d += amount * bump(row, col, r0, c0, sr, sc)
    P = P + N * (d * w)[:, None]
    M.P = [p for p in P]
    print("BOY face sculpted: %d points moved, most %.1f mm" % (int((np.abs(d * w) > 1e-4).sum()), 1000 * float(np.abs(d * w).max())))


def refine_head(M, face_uv, weights, under):
    """The face's front (brow to under the chin) split once, the jaw's edge with it; the eyes' and mouth's bands
    once more (triangles spent on the eyes, nose, lips and jaw, as the coordinator asked)."""
    fam = [part_family(p) for p in M.fpart]
    Pm = np.array(M.P)
    front = set()
    for fi, f in enumerate(M.faces):
        if fam[fi] not in ("head", "neck"):
            continue
        c = Pm[f].mean(0)
        r = float(hrow(c[2]))
        if HR(880) <= r <= HR(1192) and c[1] < head_centre(M, c[2])[1] + 0.012:
            front.add(fi)
    M1, uv1, W1, ch1 = refine(M, front, face_uv, weights)
    P = np.array(M1.P)
    fam1 = [part_family(p) for p in M1.fpart]
    face = set()
    for fi, f in enumerate(M1.faces):
        if fam1[fi] != "head" or len(f) != 4:
            continue
        c = P[f].mean(0)
        r = float(hrow(c[2]))
        # (third round: no second split: it cut the eyes' band into slivers a couple of millimetres tall and a
        # centimetre long, which shaded as streaks and folded over in the fitting)
        band = False
        if band and c[1] < head_centre(M1, c[2])[1] - 0.04:
            face.add(fi)
    M2, uv2, W2, ch2 = refine(M1, face, uv1, W1)
    under2 = set()
    for fi in under:
        for c1 in ch1.get(fi, []):
            under2 |= set(ch2.get(c1, []))
    print("BOY refined: head %d faces split, face %d split again; %d triangles now" % (len(front), len(face), len(M2.tris())))
    return M2, uv2, W2, under2


# ------------------------------------------------------------------------------------------------------------------
# The shorts: a garment over the body (its own grid round the body's columns, stood off the skin), plain cream
# cloth painted by rule: the band's two stitch lines, the fly, soft shade in the folds and the crotch, the hem.
# ------------------------------------------------------------------------------------------------------------------

BOXER_BAND = (699.0, 692.0)   # the band's top row at his back and at his front
BOXER_BAND_TALL = 24.0        # sheet pixels (2.1 cm)
BOXER_STAND = (0.010, 0.006, 0.012)   # metres: the cloth, the band, the hems (fourth pass: closer; the hems stood off as flared rims)
BOXER_LEG_RINGS = 2
BOXER_HEM_ROW = 948


def band_row(phi):
    f = (1.0 + math.cos(phi)) / 2.0
    return BOXER_BAND[0] + (BOXER_BAND[1] - BOXER_BAND[0]) * f ** 1.6


def boxer_faces(M, T):
    out = set()
    for fi, c in M.cell.items():
        if c[0] != "torso":
            continue
        i, k = c[1], c[2]
        phi = math.tau * (k + 0.5) / TORSO_N
        if TORSO_ROWS[i + 1] >= band_row(phi) + 6:
            out.add(fi)
    for sfx in ("_l", "_r"):
        rings = M.tag["leg_rings" + sfx][:BOXER_LEG_RINGS]
        pts = set(v for r in rings for v in r)
        out |= {fi for fi, (f, p) in enumerate(zip(M.faces, M.fpart)) if p == "leg" + sfx and all(v in pts for v in f)}
    return out


# (eighth pass) The shorts as the brother's knit shorts: a band with thickness, rows down the trunk, each leg's rings
# taken from the leg under it (so the hems follow the thighs in every pose: the hems stood off as open rings when he
# sat, their weights taken from points higher on the leg than where they sat), a turned hem with a lip and an inside
# face, the front's fullness, the fly's seam and the seat's line; painted cream with the rib, the fly and folds.
SHORTS_STAND = {"band_lip": 0.0018, "band": 0.005, "cloth": 0.0075, "leg_in": 0.0025, "leg_out": 0.0065, "hug": 0.002}
SHORTS_BULGE = 0.009
SHORTS_SEAT = 0.004
SHORTS_FLY = 0.002
SHORTS_KEEP = float(arg("--shorts-keep", "0.48"))
SHORTS_THIGH = float(arg("--shorts-thigh", "0.7"))
SHORTS_SEAT_OUT = 0.012      # metres: the seat's fullness pushed out behind (the critic: "a small but present rounded bottom")

# (eighth pass) ring_double, knit_shorts and paint_knit copied from tools/build_brother.py (2026-11-18), unchanged:
# the knit shorts that follow the legs (each point's weights blended from the body points under it).

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



def build_boxers(M, T, sh, weights, armature):
    """(eighth pass) The knit shorts (knit_shorts, the brother's), sized to the boy, their weights blended from the body
    points under each of their points."""
    T = M.tag["torso_rings"]
    P = np.array(M.P)
    N = normals_of(P, M.tris())
    crotch = M.tag["crotch"][0]

    def band_z(phi):
        return float(body_z(band_row(phi)))

    def mid_zs(zb1):
        z870 = float(body_z(BR(870)))
        return [zb1 + (z870 - zb1) * t for t in (0.33, 0.66, 1.0)]

    def side_cols(sfx):
        return list(range(0, 9)) if sfx == "_l" else [col_of(k, -1) for k in range(0, 9)]
    lower = sum(1 for r in TORSO_ROWS if r >= BR(885))
    Bx, src, islands, info = knit_shorts(P, N, T, {s: M.tag["leg_rings" + s] for s in ("_l", "_r")}, crotch, band_z,
                                         BOXER_BAND_TALL * S, mid_zs, float(body_z(BOXER_HEM_ROW)), side_cols,
                                         lower_rings=lower)
    # the seat: a small rounded bottom behind, each side of the middle line
    Q = np.array(Bx.P)
    zc = info["zc"]
    back = Q[:, 1] > info["cy"]
    ws = np.exp(-((np.abs(Q[:, 0]) - 0.045) / 0.045) ** 2 - ((Q[:, 2] - (zc + 0.035)) / 0.05) ** 2) * back
    Q[:, 1] += SHORTS_SEAT_OUT * ws
    Bx.P = [q for q in Q]
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
        ISLANDS[n_] = ("boxers", 0.5 if n_.startswith("boxers_hem") else 1.0)
    saved = dict(ATLAS)
    ATLAS.clear()
    ATLAS["boxers"] = 512
    placed, face_uv = pack(islands)
    # (a face turned for its winding has its corners' UVs turned with it: the brother's builder's fix)
    for fi in turned:
        if fi in face_uv:
            pic, uv = face_uv[fi]
            face_uv[fi] = (pic, list(uv)[::-1])
    write_layout(face_uv, placed, "boxers", os.path.join(TEX, "boy_boxers_layout.png"))
    Qb = np.array(Bx.P)
    pos, nrm, hit, fid = texel_geometry(Bx, face_uv, "boxers", Qb, normals_of(Qb, Bx.tris()))
    ATLAS.clear()
    ATLAS.update(saved)
    size = pos.shape[0]
    cream = np.array((0.91, 0.875, 0.795))
    rgb = np.ones((size, size, 3)) * cream
    yy, xx = np.mgrid[0:size, 0:size]
    rgb *= (1.0 + 0.022 * np.sin(xx * 1.9) * np.sin(yy * 0.9))[..., None]
    # (soft shade where the cloth turns under him, and between the legs)
    rgb *= (0.9 + 0.1 * np.clip(nrm[..., 2] + 0.6, 0, 1))[..., None]
    inner = np.clip(1.0 - np.abs(pos[..., 0]) / 0.07, 0, 1) * np.clip((zc + 0.02 - pos[..., 2]) / 0.06, 0, 1)
    rgb *= (1.0 - 0.12 * inner)[..., None]
    rgb = paint_knit(rgb, pos, hit, fid, Bx, info, rib=0.005)
    # the button under the band, at the fly's top
    zb_ = float(body_z(BOXER_BAND[1])) - BOXER_BAND_TALL * S
    front = pos[..., 1] < info["cy"]
    d = np.hypot(pos[..., 0] - 0.0, (zb_ - 0.01) - pos[..., 2])
    btn = hit & front & (d < 0.0045)
    rgb[btn] = rgb[btn] * 0.45 + np.array((0.95, 0.93, 0.88)) * 0.55
    rgb[hit & front & (np.abs(d - 0.0042) < 0.0007)] *= 0.75
    rgb = pad_edges(fill_out(rgb, hit, 64), hit)
    path = os.path.join(TEX, "boy_boxers.png")
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
    # (ninth pass; in a deep crouch the back of each shorts leg hung below the thigh as a flap: its points took the seat's
    # weights, which stay with the hips while the thigh swings up) the leg tubes, from just above the crotch down, follow
    # their thigh by the share SHORTS_THIGH
    Qw = np.array(Bx.P)
    for i, q in enumerate(Qw):
        k = SHORTS_THIGH * float(smooth01(zc + 0.035, zc - 0.015, q[2])) * float(smooth01(0.004, 0.022, abs(q[0])))
        if k <= 0:
            continue
        th = "thigh_l" if q[0] > 0 else "thigh_r"
        acc = {b: v * (1 - k) for b, v in w[i].items()}
        acc[th] = acc.get(th, 0.0) + k
        top4 = sorted(acc.items(), key=lambda kv: -kv[1])[:4]
        tot = sum(v for _, v in top4)
        w[i] = {b: v / tot for b, v in top4}
    ob = mesh_object("boy_boxers", Bx.P, Bx.faces, armature, w)
    mat = textured_material("boy_boxers", path)
    mat.use_backface_culling = True
    ob.data.materials.append(mat)
    uvl = ob.data.uv_layers.new(name="UVMap")
    for poly in ob.data.polygons:
        for li, q in zip(poly.loop_indices, face_uv[poly.index][1]):
            uvl.data[li].uv = q
    n_before = len(Bx.tris())
    dec = ob.modifiers.new("fewer", "DECIMATE")
    dec.decimate_type = "COLLAPSE"
    dec.ratio = SHORTS_KEEP
    dec.use_symmetry = True
    dec.symmetry_axis = "X"
    dec.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.view_layer.objects:
        o.select_set(o is ob)
    bpy.ops.object.modifier_apply(modifier=dec.name)
    n_after = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    print("BOY shorts: %d triangles (%d before the collapse), %d faces turned outward" % (n_after, n_before, flipped))
    Bx.n_tris_out = n_after
    return Bx


def build_boxers_retired(M, T, sh, weights, armature):
    P = np.array(M.P)
    N = normals_of(P, M.tris())
    Bx = Mesh()
    src = []

    def column_at(k, z):
        zs = np.array([P[r[k]][2] for r in T])
        pts = np.array([P[r[k]] for r in T])
        ns = np.array([N[r[k]] for r in T])
        q = np.array([np.interp(z, zs, pts[:, a]) for a in range(3)])
        n = np.array([np.interp(z, zs, ns[:, a]) for a in range(3)])
        i = int(np.clip(np.searchsorted(zs, z), 0, len(zs) - 1))
        return q, n / max(np.linalg.norm(n), 1e-9), T[i][k]
    lower = sorted([r for r in TORSO_ROWS if r >= BR(885)])
    rows_of = []
    for k in range(TORSO_N):
        phi = math.tau * k / TORSO_N
        b = band_row(phi)
        b1 = b + BOXER_BAND_TALL
        mids = [b1 + (BR(870) - b1) * t for t in (0.33, 0.66, 1.0)]
        rows_of.append([b, b, b1] + mids + lower)
    nrows = len(rows_of[0])
    G = []
    for j in range(nrows):
        ring = []
        for k in range(TORSO_N):
            q, n, s = column_at(k, float(body_z(rows_of[k][j])))
            stand = 0.0018 if j == 0 else BOXER_STAND[1] if j in (1, 2) else BOXER_STAND[0]
            if j == 0:
                q = q + np.array((0.0, 0.0, -0.003))
            ring.append(Bx.add(q + n * stand, "boxers"))
            src.append(s)
        G.append(ring)
    band_faces = set()
    for j in range(nrows - 1):
        for k in range(TORSO_N):
            kk = (k + 1) % TORSO_N
            Bx.face([G[j][k], G[j][kk], G[j + 1][kk], G[j + 1][k]], "boxers_torso")
            Bx.cell[len(Bx.faces) - 1] = ("trunk", j, k)
            if j < 2:
                band_faces.add(len(Bx.faces) - 1)
    crotch = M.tag["crotch"][0]
    bottom = G[-1]
    gc = Bx.add(P[crotch] + np.array((0.0, 0.0, -BOXER_STAND[0])), "boxers")
    src.append(crotch)
    legs = {}
    for sfx, side in (("_l", 1), ("_r", -1)):
        top = [bottom[k if side > 0 else col_of(k, -1)] for k in range(0, 9)] + [gc]
        rings = [top]
        body_rings = M.tag["leg_rings" + sfx][1:BOXER_LEG_RINGS + 1]
        for li, br in enumerate(body_rings):
            last = li == len(body_rings) - 1
            stand = BOXER_STAND[2] if last else (BOXER_STAND[0] + BOXER_STAND[2]) / 2.0
            ring = []
            c = P[br].mean(0)
            for v in br:
                out = P[v] - c
                out[2] = 0.0
                out /= max(np.linalg.norm(out), 1e-9)
                q = P[v] + out * stand
                if last:
                    q[2] = float(body_z(BOXER_HEM_ROW))
                ring.append(Bx.add(q, "boxers"))
                src.append(v)
            rings.append(ring)
        for a, b in zip(rings, rings[1:]):
            for j in range(LIMB_N):
                k = (j + 1) % LIMB_N
                Bx.face([a[j], a[k], b[k], b[j]], "boxers_leg" + sfx)
        legs[sfx] = rings
        # (second round) The hem turned in: a lining from the hem up inside to near the thigh, so from below the
        # cloth's inside never shows (it showed as a pale band under the hem) and the shorts can cull back faces.
        hem = rings[-1]
        br = body_rings[-1]
        c = P[br].mean(0)
        inner = []
        for v in br:
            out = P[v] - c
            out[2] = 0.0
            out /= max(np.linalg.norm(out), 1e-9)
            q = P[v] + out * 0.004
            q[2] = float(body_z(BOXER_HEM_ROW)) + 0.015
            inner.append(Bx.add(q, "boxers"))
            src.append(v)
        for j in range(LIMB_N):
            k = (j + 1) % LIMB_N
            Bx.face([hem[j], hem[k], inner[k], inner[j]], "boxers_lining", np.array((0.0, 0.0, -1.0)))
    Q = np.array(Bx.P)
    flipped = 0
    for fi, f in enumerate(Bx.faces):
        if fi in Bx.want:
            if np.dot(face_normal(Q, f), Bx.want[fi]) < 0:
                Bx.faces[fi] = f[::-1]
                flipped += 1
            continue
        n_body = np.mean([N[src[v]] for v in f], axis=0)
        if np.dot(face_normal(Q, f), n_body) < 0:
            Bx.faces[fi] = f[::-1]
            flipped += 1
    mid_ring = G[nrows // 2]
    seg = [float(np.linalg.norm(Q[mid_ring[(k + 1) % TORSO_N]] - Q[mid_ring[k]])) for k in range(TORSO_N)]
    islands = {"boxers_front": {}, "boxers_back": {}}
    for fi, c in Bx.cell.items():
        j, k = c[1], c[2]
        front = k >= 12 or k < 4
        start = 12 if front else 4
        uv = []
        for v in Bx.faces[fi]:
            kv = G[j].index(v) if v in G[j] else G[j + 1].index(v)
            kk = (kv - start) % TORSO_N
            if kk > 8:
                kk -= TORSO_N
            u = sum(seg[(start + i) % TORSO_N] for i in range(kk)) if kk >= 0 else -seg[(start - 1) % TORSO_N]
            uv.append((u if front else -u, float(Q[v][2])))
        islands["boxers_front" if front else "boxers_back"][fi] = uv
    for sfx, s in (("_l", 1.0), ("_r", -1.0)):
        ring = legs[sfx][1]
        cx, cy = Q[ring][:, 0].mean(), Q[ring][:, 1].mean()
        R = float(np.hypot(Q[ring][:, 0] - cx, Q[ring][:, 1] - cy).mean())
        isl = {}
        for fi, p in enumerate(Bx.fpart):
            if p != "boxers_leg" + sfx:
                continue
            th = [math.atan2(-(Q[v][1] - cy), s * (Q[v][0] - cx)) for v in Bx.faces[fi]]
            if max(th) - min(th) > math.pi:
                th = [t + math.tau if t < 0 else t for t in th]
            isl[fi] = [(s * t * R, float(Q[v][2])) for t, v in zip(th, Bx.faces[fi])]
        islands["boxers_leg" + sfx] = isl
    lining = [fi for fi, p in enumerate(Bx.fpart) if p == "boxers_lining"]
    islands["boxers_lining"] = planar_uvs(Bx, lining, np.array((1.0, 0, 0)), np.array((0, 1.0, 0)))
    for n in islands:
        ISLANDS[n] = ("boxers", 1.0)
    saved = dict(ATLAS)
    ATLAS.clear()
    ATLAS["boxers"] = 512
    placed, face_uv = pack(islands)
    write_layout(face_uv, placed, "boxers", os.path.join(TEX, "boy_boxers_layout.png"))
    rgb = paint_boxers(Bx, face_uv, placed, band_faces, sh)
    ATLAS.update(saved)
    path = os.path.join(TEX, "boy_boxers.png")
    save_rgb(path, rgb[::-1])
    w = [weights[s] for s in src]
    ob = mesh_object("boy_boxers", Bx.P, Bx.faces, armature, w)
    mat = textured_material("boy_boxers", path)
    ob.data.materials.append(mat)
    uvl = ob.data.uv_layers.new(name="UVMap")
    for poly in ob.data.polygons:
        for li, q in zip(poly.loop_indices, face_uv[poly.index][1]):
            uvl.data[li].uv = q
    print("BOY shorts: %d triangles, %d faces turned outward" % (len(Bx.tris()), flipped))
    return Bx


def paint_boxers(Bx, face_uv, placed, band_faces, sh):
    size = 512
    Q = np.array(Bx.P)
    Nb = normals_of(Q, Bx.tris())
    pos, nrm, hit, fid = texel_geometry(Bx, face_uv, "boxers", Q, Nb)
    # the cloth's colour: the sheet's shorts in the front view, their lit middle
    sel = sh.body_mask[760:880, 450:680] & is_shorts(sh.body_pix[760:880, 450:680])
    cloth = np.median(sh.body_pix[760:880, 450:680][sel], axis=0) if sel.any() else np.array((0.86, 0.82, 0.72))
    # (seventh pass; the critic: "a muddy olive-grey ... the concept is a warm off-white knit (about #E8DFCB)")
    cloth = np.array((0.91, 0.875, 0.795))
    print("BOY shorts' cloth %s" % np.round(cloth, 3))
    rgb = np.ones((size, size, 3)) * cloth
    band = np.isin(fid, list(band_faces))
    z = pos[..., 2]
    zt = float(body_z(BOXER_BAND[1]))
    zb_ = float(body_z(BOXER_BAND[1] + BOXER_BAND_TALL))
    rgb[band] *= 1.03
    stitch = band & ((np.abs(z - (zt - 0.004)) < 0.0012) | (np.abs(z - (zb_ + 0.004)) < 0.0012))
    rgb[stitch] *= 0.86
    fam = np.array([p for p in Bx.fpart] + ["none"])[fid]
    trunk = fam == "boxers_torso"
    under_band = trunk & ~band & (zb_ - z < 0.01) & (zb_ - z > 0)
    rgb[under_band] *= 0.9
    inner = np.clip(1.0 - np.abs(pos[..., 0]) / 0.08, 0, 1) * np.clip((body_z(BR(950)) - z) / 0.07, 0, 1)
    rgb *= (1.0 - 0.14 * inner)[..., None]
    # (soft shade where the cloth turns away under him and at its sides)
    rgb *= (0.9 + 0.1 * np.clip(nrm[..., 2] + 0.6, 0, 1))[..., None]
    front = pos[..., 1] < -0.04
    ax_ = np.abs(pos[..., 0])
    # (fifth pass, the new sheet: a button fly, one sewn placket line curving to the middle, a button under the band;
    # no box. A fine knit and soft folds over the cloth)
    xs_ = pos[..., 0]
    dz = zb_ - z
    line_x = 0.012 * np.clip(1.0 - (dz - 0.05) / 0.025, 0, 1)
    fly = trunk & front & ~band & (dz > 0.004) & (dz < 0.075) & (np.abs(xs_ - line_x) < 0.0009)
    rgb[fly] *= 0.86
    btn = trunk & front & (np.hypot(xs_ - 0.006, dz - 0.012) < 0.0045)
    rgb[btn] = rgb[btn] * 0.5 + np.array((0.93, 0.91, 0.86)) * 0.5
    rgb[btn & (np.abs(np.hypot(xs_ - 0.006, dz - 0.012) - 0.0042) < 0.0007)] *= 0.75
    yy, xx = np.mgrid[0:size, 0:size]
    knit = 1.0 + 0.025 * np.sin(xx * 1.9) * np.sin(yy * 0.9)
    folds = 1.0 - 0.05 * np.clip(np.sin(z * 90.0 + xs_ * 40.0) * np.sin(xs_ * 55.0 + 1.0), 0, 1)
    rgb *= (knit * np.where(trunk | (fam != "boxers_lining"), folds, 1.0))[..., None]
    hem_z = float(body_z(BOXER_HEM_ROW))
    # (seventh pass: the hem a soft lighter knit edge with small scallops, and the lining inside it the same cloth a
    # little shaded: the dark grey band the critic saw was the lining at 0.62)
    hem = (fam != "boxers_torso") & (fam != "boxers_lining") & hit & (z - hem_z < 0.008)
    ang = np.arctan2(pos[..., 0] - np.sign(pos[..., 0]) * 0.07, pos[..., 1])
    scal = 0.5 + 0.5 * np.cos(ang * 22.0)
    rgb[hem] *= 1.035
    rgb[hem & (z - hem_z < 0.0025 * scal + 0.0008)] *= 0.93
    rgb[fam == "boxers_lining"] *= 0.86
    return pad_edges(fill_out(rgb, hit, 64), hit)


def export_views(M, face_uv, mat_skin, places):
    """(for checking, with --out) His left hand as each hands-sheet view sees it (the back and palm open, the thumb
    side relaxed), its points laid in that picture's own plane (x = column, z = -row, y = depth, metres at the view's
    scale), painted, as <out>/hand_views.glb; and the views' numbers as <out>/views.json, so that a renderer can lay
    each picture over its sheet crop pixel for pixel."""
    if not OUT:
        return
    import json as _j
    hf = M.tag["hand_faces_l"]
    first = M.tag["hand_points_l"][0]
    obs = []
    for view in ("back", "palm", "side"):
        Mt, jt = hand_alone(HANDV[view]["pose"])
        uv, depth = hand_uv(view, np.array(Mt.P), jt["hand_frame_l"])
        k = HANDV[view]["k"]
        at = places[view]
        Q = np.stack([(uv[:, 0] + at[0]) * k, depth, -(uv[:, 1] + at[1]) * k], 1)
        fl = Mt.tag["hand_faces_l"]
        faces = [Mt.faces[i] for i in fl]
        # (a view drawn mirrored turns the faces inside out: their order reversed so the normals face out)
        fn = np.array([face_normal(Q, f) for f in faces])
        out = float(((Q[np.array([f[0] for f in faces])] - Q.mean(0)) * fn).sum())
        if out < 0:
            faces = [f[::-1] for f in faces]
        me = bpy.data.meshes.new("hand_" + view)
        me.from_pydata([tuple(map(float, q)) for q in Q], [], faces)
        uvl = me.uv_layers.new(name="UVMap")
        for poly, fi, f in zip(me.polygons, [hf[i] for i in fl], faces):
            # (each corner's UV by its point: the body's face may have been turned round by the winding fix)
            pic, u = face_uv[fi]
            by = {v - first + LIMB_N: q for v, q in zip(M.faces[fi], u)}
            for li, v in zip(poly.loop_indices, f):
                q = by[v]
                uvl.data[li].uv = q
            poly.use_smooth = True
        me.materials.append(mat_skin)
        ob = bpy.data.objects.new("hand_" + view, me)
        bpy.context.scene.collection.objects.link(ob)
        obs.append(ob)
    for o in bpy.context.scene.objects:
        o.select_set(o in obs)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "hand_views.glb"), export_format="GLB", use_selection=True,
                              export_yup=True)
    for o in obs:
        bpy.data.objects.remove(o, do_unlink=True)
    views = {"S": S, "SOLE": SOLE, "MID": MID, "HS": HS, "H_CHIN": H_CHIN, "Z_CHIN": Z_CHIN, "HVIEW": HVIEW,
             "HAND": {v: {"k": HANDV[v]["k"], "box": HANDV[v]["box"]} for v in HANDV}}
    with open(os.path.join(OUT, "views.json"), "w") as f:
        _j.dump(views, f, indent=1)
    print("BOY wrote the views for checking")


def report_counts(M):
    by = {}
    for f, p in zip(M.faces, M.fpart):
        fam = p.split("_")[0]
        if fam == "hand" and p.count("_") >= 2:
            fam = "fingers"
        by[fam] = by.get(fam, 0) + len(f) - 2
    print("BOY triangles by part: %s; all %d" % (json.dumps(by), sum(by.values())))
    return sum(by.values())


def export(armature, path):
    for o in list(bpy.data.objects):
        if o != armature and o.parent != armature:
            bpy.data.objects.remove(o, do_unlink=True)
    for o in bpy.context.scene.objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = armature
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_skins=True,
                              export_animations=False, export_apply=False, export_tangents=True,
                              export_texcoords=True, export_normals=True, export_yup=True, export_image_format="AUTO")
    print("BOY wrote %s" % path)
    os.makedirs(os.path.dirname(BLEND), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    print("BOY wrote %s" % BLEND)


# ------------------------------------------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------------------------------------------

def tone_report(M, face_uv, face_rgb, sh):
    """Unlit colours of his head's picture at the cheek, forehead, temple and nape against the head sheet's at the
    same places (front view for the first two, the side and back views for the others)."""
    P = np.array(M.P)
    fam = np.array([part_family(p) for p in M.part])
    head = np.where(fam == "head")[0]
    rows = hrow(P[:, 2])
    size = ATLAS["face"]
    vuv = {}
    for fi, (pic, uv) in face_uv.items():
        if pic != "face":
            continue
        for v, q in zip(M.faces[fi], uv):
            vuv.setdefault(v, q)

    def pick(sel, key):
        c = [v for v in head[sel[head]] if v in vuv]
        return min(c, key=key) if c else None
    marks = {
        "forehead": (pick((np.abs(rows - HR(830)) < 12) & (np.abs(P[:, 0]) < 0.012), lambda v: P[v, 1]), "hfront"),
        "cheek": (pick((np.abs(rows - HR(1015)) < 12) & (np.abs(P[:, 0] - 0.06) < 0.01), lambda v: P[v, 1]), "hfront"),
        "temple": (pick((np.abs(rows - HR(890)) < 20) & (P[:, 1] < -0.02) & (P[:, 1] > -0.09), lambda v: P[v, 0]), "hside"),
        "nape": (pick((np.abs(rows - HR(1000)) < 25) & (np.abs(P[:, 0]) < 0.03), lambda v: -P[v, 1]), "hback"),
    }
    out = {}
    for name, (v, view) in marks.items():
        if v is None:
            out[name] = "none found"
            continue
        q = vuv[v]
        x, y = int(q[0] * (size - 1)), int(q[1] * (size - 1))
        model = face_rgb[max(0, y - 2):y + 3, max(0, x - 2):x + 3].reshape(-1, 3).mean(0)
        Q = P[v].copy()
        if view == "hside":
            Q[0] = -abs(Q[0])
        p2, _ = project(view, Q[None])
        c, r = int(p2[0, 0]), int(p2[0, 1])
        sheet = sh.head_pix[r - 3:r + 4, c - 3:c + 4].reshape(-1, 3).mean(0)
        out[name] = {"model": np.round(model, 3).tolist(), "sheet": np.round(sheet, 3).tolist(),
                     "ratio": np.round(model / np.maximum(sheet, 1e-3), 2).tolist()}
    print("BOY head tone (unlit, model against sheet): %s" % json.dumps(out))
    return out


# ------------------------------------------------------------------------------------------------------------------
# Open eyes (fifth pass), the brother's way (tools/build_brother.py, open_eyes: read and copied, changed for his
# sheet): the face split once more round each eye, an almond opening cut to the bald front view's lids, lids with a
# thickness rolling into the socket, a crease over the upper lid, and an eyeball of its own (boy_eye.png: white, his
# olive-green iris, pupil) on the head bone. Measured off concept_boy_head2.jpg (columns out from his middle, rows):
# big, wide-set eyes, 3.9 cm corner to corner.
# ------------------------------------------------------------------------------------------------------------------

# (seventh pass: measured again at twice size, the opening 50 to 120 out and 1077 to 1128 down, the iris 20 to 22
# pixels round centred at 1104 so the upper lid covers its top; the critic: "about 20% larger, sunk 2 to 3 mm")
EYE_INNER = (42.0, 1104.0)
EYE_OUTER = (118.0, 1101.0)
EYE_TOP = (79.0, float(arg("--eye-top", "1082")))   # (eighth pass: from 1077; ninth: from 1080, which still showed the iris whole: the lid now over its top 3 px)
EYE_LOW = (78.0, 1128.0)
EYE_IRIS = (78.0, 1104.0, float(arg("--iris", "21.5")))   # (tenth pass: from 21; twelfth: from 27, measured again on the bald front view: the iris 40 pixels across, the upper lid on its top, white either side)
EYE_R = 0.0135
EYE_RX = 0.0215
if "--old-head" not in ARGS:
    # (eleventh pass) a rounder ball, so the lids slide over it (the face rig fits a sphere): 1.18 to 1 from 1.59
    EYE_R = float(arg("--eye-r", "0.0165"))
    EYE_RX = float(arg("--eye-rx", "0.0195"))
EYE_RAD = np.array((EYE_RX, EYE_R, EYE_R))
# (ninth pass, a note from the face rig: his eyeball is NOT a sphere but this ellipsoid, wider across (21.5 mm) than
# through (13.5 mm); the rig fits it as a 15.6 mm ball. A rounder ball would let the lids slide over it cleaner, if it
# can be had without the eye reading too round from the front.)
EYE_BACK = float(arg("--eye-back", "0.0028"))   # (seventh pass: 0.0048, the eyes sunk into their sockets; tenth: back to 0.0028, the critic: "dark pits ... bring the eyeballs forward")
EYE_LID = (float(arg("--lid-up", "0.0013")), float(arg("--lid-low", "0.0008")))   # (seventh pass: from 0.0006, 0.0004: a thick upper lid, a raised lower one)
LID_THICK = 0.0013
EYES_OPEN = "--closed-eyes" not in ARGS
LID_SKIN_UV = "--lid-lash-uv" not in ARGS
MARGIN_EVEN = "--margin-snap" not in ARGS
EYE_REFINE = (float(arg("--eye-refine-w", "45")), float(arg("--eye-refine-h", "29")))   # (sixth pass, the budget: from 52 x 34)


def ball_y(x, z, C):
    k = 1.0 - ((x - C[0]) / EYE_RAD[0]) ** 2 - ((z - C[2]) / EYE_RAD[2]) ** 2
    return C[1] - EYE_RAD[1] * math.sqrt(max(k, 0.0))


def eye_outline(n=48):
    (c0, r0), (c1, r1) = EYE_INNER, EYE_OUTER
    tu = (EYE_TOP[0] - c0) / (c1 - c0)
    tl = (EYE_LOW[0] - c0) / (c1 - c0)
    out = []
    for i in range(n):
        s = i / n * 2.0
        upper = s < 1.0
        t = s if upper else 2.0 - s
        rc = r0 + (r1 - r0) * t
        if upper:
            tt = t ** (math.log(0.5) / math.log(tu))
            row = rc - (rc - EYE_TOP[1]) * (math.sin(math.pi * tt) ** 0.85)
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
        ins ^= ((yi > y) != (yj > y)) & (x < (xj - xi) * (y - yi) / ((yj - yi) + 1e-12) + xi)
        j = i
    return ins


def head_faces_pts(M):
    a, b = M.tag["head_points"]
    pts = [i for i in range(a, b) if M.part[i] == "head"]
    ps = set(pts)
    faces = [fi for fi, f in enumerate(M.faces) if M.fpart[fi] == "head" and all(v in ps for v in f)]
    return faces, pts


def open_eyes(M, face_uv, weights, under):
    """Gives (M, face_uv, weights, under, cut faces, eyes: [(centre, side)])."""
    poly = eye_outline()
    ic, ir, irad = EYE_IRIS
    P = np.array(M.P)
    hfaces, hpts = head_faces_pts(M)
    sel = set()
    mc0 = poly.mean(0)
    for fi in hfaces:
        c = P[M.faces[fi]].mean(0)
        col, row = abs(c[0]) / HS, float(hrow(c[2]))
        if c[1] < 0 and ((col - mc0[0]) / EYE_REFINE[0]) ** 2 + ((row - mc0[1]) / EYE_REFINE[1]) ** 2 < 1.0:
            sel.add(fi)
    n_old = len(M.P)
    R, face_uv, weights, ch = refine(M, sel, face_uv, weights)
    R.tag = dict(M.tag)
    for key in ("hand_faces_l", "hand_faces_r"):
        if key in M.tag:
            R.tag[key] = [c for fi in M.tag[key] for c in ch.get(fi, [fi])]
    u2 = set()
    for fi in under:
        u2 |= set(ch.get(fi, [fi]))
    under = u2
    M = R
    a_, b_ = M.tag["head_points"]
    new_head = [i for i in range(n_old, len(M.P)) if M.part[i] == "head"]
    hpts = hpts + new_head
    hps = set(hpts)
    hfaces = [fi for fi, f in enumerate(M.faces) if M.fpart[fi] == "head" and all(v in hps for v in f)]
    P = np.array(M.P)
    cut = set()
    eyes = []
    for s in (1, -1):
        cx, cz = s * float(poly[:, 0].mean()) * HS, float(hz(ir))
        near = [i for i in hpts if s * P[i][0] > 0 and P[i][1] < 0]
        d2 = (P[near, 0] - cx) ** 2 + (P[near, 2] - cz) ** 2
        k = np.argsort(d2)[:4]
        y_s = float(P[np.array(near)[k], 1].mean())
        C = np.array((cx, y_s + EYE_BACK + EYE_R, cz))
        mine = [fi for fi in hfaces if s * P[M.faces[fi]].mean(0)[0] > 0 and P[M.faces[fi]].mean(0)[1] <= C[1]]
        big = mc0 + (poly - mc0) * np.array((1.12, 1.25))
        pts_in = {}
        for fi in mine:
            for v in M.faces[fi]:
                if v not in pts_in:
                    pts_in[v] = bool(inside_poly(np.array([[s * P[v][0] / HS, float(hrow(P[v][2]))]]), big)[0])
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
        if not hole:
            print("BOY EYES: no opening cut (%s)" % s)
            continue
        cut |= hole
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
        ang_p = np.arctan2(poly[:, 1] - mc0[1], poly[:, 0] - mc0[0])
        angs = []
        for v in loop:
            col, row = s * P[v][0] / HS, float(hrow(P[v][2]))
            angs.append(math.atan2(row - mc0[1], col - mc0[0]))
        if MARGIN_EVEN:
            # (ninth pass; close up the margin was a ring of shards: the opening's edge zigzags in and out across the
            # refined triangles, and each point snapped to the outline by its own angle came out of order, folding the
            # lid's edge and the margin over each other. The points now go round the outline in their loop's order, each
            # step forward by its share of the loop's turning, so no two cross)
            da = np.angle(np.exp(1j * np.diff(np.array(angs + [angs[0]]))))
            sg = 1.0 if da.sum() > 0 else -1.0
            stp = np.maximum(sg * da, 0.0) + 0.02
            stp = stp / stp.sum() * math.tau
            targets = angs[0] + sg * np.concatenate([[0.0], np.cumsum(stp)[:-1]])
        else:
            targets = angs
        # the outline by angle, closed, for interpolation
        o_ = np.argsort(ang_p)
        ap = np.concatenate([ang_p[o_] - math.tau, ang_p[o_], ang_p[o_] + math.tau])
        pc = np.concatenate([poly[o_, 0]] * 3)
        pr = np.concatenate([poly[o_, 1]] * 3)
        for v, a in zip(loop, targets):
            a = math.atan2(math.sin(a), math.cos(a))
            c2, r2 = float(np.interp(a, ap, pc)), float(np.interp(a, ap, pr))
            x, z = s * c2 * HS, float(hz(r2))
            P[v] = (x, ball_y(x, z, C) - LID_THICK, z)
        if MARGIN_EVEN:
            # (ninth pass) lid points left inside the outline (the cut takes only faces wholly inside a larger outline,
            # so some of the lid's points lie within the opening once its edge is snapped) moved out past the outline
            # along their own angle, so the lid does not fold back over the margin
            lpset = set(loop)
            moved_in = 0
            for fi in mine:
                if fi in hole:
                    continue
                for v in M.faces[fi]:
                    if v in lpset:
                        continue
                    col, row = s * P[v][0] / HS, float(hrow(P[v][2]))
                    a = math.atan2(row - mc0[1], col - mc0[0])
                    c2, r2 = float(np.interp(a, ap, pc)), float(np.interp(a, ap, pr))
                    rp = math.hypot(c2 - mc0[0], r2 - mc0[1])
                    rv = math.hypot(col - mc0[0], row - mc0[1])
                    if rv < rp * 1.08:
                        k_ = rp * 1.08 / max(rv, 1e-6)
                        col2, row2 = mc0[0] + (col - mc0[0]) * k_, mc0[1] + (row - mc0[1]) * k_
                        x, z = s * col2 * HS, float(hz(row2))
                        P[v] = (x, min(P[v][1], ball_y(x, z, C) - LID_THICK), z)
                        lpset.add(v)
                        moved_in += 1
            print("BOY EYES margin: %d lid points moved out of the opening" % moved_in)
        inner = set(v for fi in hole for v in M.faces[fi]) - set(loop)
        for v in inner:
            dn = (P[v] - C) / EYE_RAD
            P[v] = C + dn / max(np.linalg.norm(dn), 1e-9) * EYE_RAD * (1.0 - 0.002 / EYE_R)
        lp = set(loop)
        for i in hpts:
            if i in lp or i in inner or s * P[i][0] <= 0:
                continue
            dn = (P[i] - C) / EYE_RAD
            dd = np.linalg.norm(dn)
            if dd < 1.0 + LID_THICK / EYE_R:
                P[i] = C + dn / dd * EYE_RAD * (1.0 + LID_THICK / EYE_R)
        for i in hpts:
            if i in lp or i in inner or s * P[i][0] <= 0 or P[i][1] > C[1]:
                continue
            col, row = s * P[i][0] / HS, float(hrow(P[i][2]))
            t = (col - EYE_INNER[0]) / (EYE_OUTER[0] - EYE_INNER[0])
            if t < -0.15 or t > 1.15:
                continue
            j = int(np.clip(round(np.clip(t, 0, 1) * 24), 0, 24))
            top, low = poly[j][1], poly[(48 - j) % 48][1]
            fade = float(np.clip(1.0 - (abs(t - 0.5) - 0.5) / 0.15, 0, 1)) if (t < 0 or t > 1) else 1.0
            above, below = top - row, row - low
            push = 0.0
            if 0 < above < 14:
                push += EYE_LID[0] * math.exp(-((above - 3.5) / 3.0) ** 2)
                push -= 0.0011 * math.exp(-((above - 9.5) / 2.6) ** 2)      # the crease (softer: a boy's)
            if 0 < below < 14:
                push += EYE_LID[1] * math.exp(-((below - 5.0) / 3.5) ** 2)
            P[i] = P[i] + np.array((0.0, -1.0, 0.0)) * push * fade
        ring2 = []
        mid = np.array((C[0], C[2]))
        for v in loop:
            xz = P[v][[0, 2]]
            dvec = mid - xz
            xz2 = xz + dvec / max(np.linalg.norm(dvec), 1e-9) * 0.0012
            P = np.vstack([P, (xz2[0], ball_y(xz2[0], xz2[1], C) + 0.0008, xz2[1])])
            M.P.append(P[-1].copy())
            M.part.append("head")
            weights.append(dict(weights[v]))
            ring2.append(len(M.P) - 1)
        M.P = [p for p in P]
        uv_of = {}
        for fi, f in enumerate(M.faces):
            if fi in cut or fi not in face_uv or face_uv[fi][0] != "face":
                continue
            for v, q_ in zip(f, face_uv[fi][1]):
                if v in lp and v not in uv_of:
                    uv_of[v] = q_
        # (ninth pass, for the face rig: the margin rolling into the socket took the UVs of the lid's edge, on the painted
        # lash line, so a closing lid showed a dark streak: it takes one UV on plain lid skin instead, the head point
        # nearest the lid's middle between its crease and the brow, head-sheet row 1060)
        lid_uv = None
        best = None
        for fi, f in enumerate(M.faces):
            if fi in cut or fi not in face_uv or face_uv[fi][0] != "face" or M.fpart[fi] != "head":
                continue
            for v, q_ in zip(f, face_uv[fi][1]):
                d = (s * P[v][0] / HS - 80.0) ** 2 + (float(hrow(P[v][2])) - 1060.0) ** 2
                if P[v][1] < 0 and (best is None or d < best):
                    best, lid_uv = d, q_
        n = len(loop)
        for j in range(n):
            a, b = loop[j], loop[(j + 1) % n]
            f = [a, b, ring2[(j + 1) % n], ring2[j]]
            if np.dot(face_normal(P, f), P[f].mean(0) - C) < 0:
                f = f[::-1]
            M.face(f, "head")
            fi = len(M.faces) - 1
            face_uv[fi] = ("face", [lid_uv if LID_SKIN_UV and lid_uv is not None else uv_of.get(v if v in uv_of else loop[ring2.index(v)], (0.0, 0.0)) for v in f])
        eyes.append((C, s))
        print("BOY EYES %s: opening of %d faces, margin %d points, ball at %s" % ("left" if s > 0 else "right", len(hole), n, np.round(C, 4)))
    return M, face_uv, weights, under, cut, eyes


LID_RINGS = (float(arg("--lid-ring1", "1.16")), float(arg("--lid-ring2", "1.42")))   # the lid's next two rings out, as shares of the opening's reach
LID_SWELL = (float(arg("--lid-swell1", "0.0012")), float(arg("--lid-swell2", "0.0006")))   # metres those rings stand off the ball beyond the lid's edge
LID_EVEN = int(arg("--lid-even", "3"))
LID_ROLL = (float(arg("--lid-roll-in", "0.0012")), float(arg("--lid-roll-back", "0.0008")))   # the margin's roll into the socket: in toward the eye's middle, back


def open_eyes2(M, face_uv, weights, under):
    """(eleventh pass) The eyes opened along the base mesh's own lid loops, not cut through refined triangles (the
    cut's edge zigzagged and left a ring of shards round each eye: the critic's "ragged lid edges ... spikes"). The
    strip of quads between the base's closed lids is taken out; its edge, the lids' margin, is set on the sheet's eye
    outline over the ball; the next two loops out are laid as even rings round it (the lid's thickness, then its
    fold), every point near the eye kept outside the ball; the margin rolls into the socket by one more ring. Gives
    (M, face_uv, weights, under, cut faces, eyes)."""
    def ball_y(x, z, C):
        k = 1.0 - ((x - C[0]) / EYE_RAD[0]) ** 2 - ((z - C[2]) / EYE_RAD[2]) ** 2
        return C[1] - EYE_RAD[1] * math.sqrt(max(k, 0.25))
    poly = eye_outline()
    ic, ir, irad = EYE_IRIS
    P = np.array(M.P)
    hfaces, hpts = head_faces_pts(M)
    hps = set(hpts)
    strip = set(M.tag.get("eye_strip", []))
    mc0 = poly.mean(0)
    nbr = {}
    for fi in hfaces:
        f = M.faces[fi]
        for i in range(len(f)):
            nbr.setdefault(f[i], set()).update((f[i - 1], f[(i + 1) % len(f)]))
    ang_p = np.arctan2(poly[:, 1] - mc0[1], poly[:, 0] - mc0[0])
    o_ = np.argsort(ang_p)
    ap = np.concatenate([ang_p[o_] - math.tau, ang_p[o_], ang_p[o_] + math.tau])
    pc = np.concatenate([poly[o_, 0]] * 3)
    pr = np.concatenate([poly[o_, 1]] * 3)

    def outline_at(a, k=1.0):
        a = math.atan2(math.sin(a), math.cos(a))
        c2, r2 = float(np.interp(a, ap, pc)), float(np.interp(a, ap, pr))
        return mc0[0] + (c2 - mc0[0]) * k, mc0[1] + (r2 - mc0[1]) * k
    cut, eyes = set(), []
    for s in (1, -1):
        hole = {fi for fi in strip if s * P[M.faces[fi]].mean(0)[0] > 0}
        if not hole:
            print("BOY EYES: no lid strip found (%s)" % s)
            continue
        cnt = {}
        for fi in hole:
            f = M.faces[fi]
            for i in range(len(f)):
                e = (min(f[i], f[(i + 1) % len(f)]), max(f[i], f[(i + 1) % len(f)]))
                cnt[e] = cnt.get(e, 0) + 1
        bnd = [e for e, c in cnt.items() if c == 1]
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
        inner = set(v for fi in hole for v in M.faces[fi]) - set(loop)
        cut |= hole
        # the ball: at the sheet's eye, its front just behind the closed lid's surface there
        cx, cz = s * float(mc0[0]) * HS, float(hz(ir))
        lp_ = np.array(loop)
        y_s = float(np.median(P[lp_, 1]))
        C = np.array((cx, y_s + EYE_BACK + EYE_RAD[1], cz))
        angs = [math.atan2(float(hrow(P[v][2])) - mc0[1], s * P[v][0] / HS - mc0[0]) for v in loop]
        da = np.angle(np.exp(1j * np.diff(np.array(angs + [angs[0]]))))
        sg = 1.0 if da.sum() > 0 else -1.0
        stp = np.maximum(sg * da, 0.0) + 0.02
        stp = stp / stp.sum() * math.tau
        # (the loop's points spread evenly by angle round the outline from the inner corner, so the lid's edge is a
        # clean curve: the corner point is the loop's point nearest the sheet's inner corner)
        a_in = math.atan2(EYE_INNER[1] - mc0[1], EYE_INNER[0] - mc0[0])
        k0 = int(np.argmin([abs(math.atan2(math.sin(a - a_in), math.cos(a - a_in))) for a in angs]))
        n = len(loop)
        loop = loop[k0:] + loop[:k0]
        angs = angs[k0:] + angs[:k0]
        # (spaced evenly along the outline's length, not by angle: by angle the almond's corners got too few points
        # and the opening came out round)
        pa = np.arctan2(poly[:, 1] - mc0[1], poly[:, 0] - mc0[0])
        pdir = 1.0 if np.angle(np.exp(1j * np.diff(np.append(pa, pa[0])))).sum() > 0 else -1.0
        pl = poly if pdir == sg else np.concatenate([poly[:1], poly[1:][::-1]])
        seg_ = np.linalg.norm(np.diff(np.vstack([pl, pl[:1]]), axis=0), axis=1)
        cum = np.concatenate([[0.0], np.cumsum(seg_)])
        want = np.arange(n) / n * cum[-1]
        closed = np.vstack([pl, pl[:1]])
        spots = np.stack([np.interp(want, cum, closed[:, 0]), np.interp(want, cum, closed[:, 1])], 1)
        lpos = {}
        for v, (c2, r2) in zip(loop, spots):
            x, z = s * c2 * HS, float(hz(r2))
            P[v] = (x, ball_y(x, z, C) - LID_THICK, z)
            lpos[v] = (c2, r2)
        # the next two loops out: each point by its own angle round the eye at a fixed share beyond the outline
        done = set(loop) | inner
        prev = list(loop)
        rings = []
        for k_, sw in zip(LID_RINGS, LID_SWELL):
            ring = sorted({u for v in prev for u in nbr.get(v, ()) if u not in done and u in hps})
            for u in ring:
                col, row = s * P[u][0] / HS, float(hrow(P[u][2]))
                a = math.atan2(row - mc0[1], col - mc0[0])
                c2, r2 = outline_at(a, k_)
                x, z = s * c2 * HS, float(hz(r2))
                yb = ball_y(x, z, C)
                P[u] = (x, min(P[u][1], yb - LID_THICK - sw) * 0.5 + (yb - LID_THICK - sw) * 0.5, z)
            done |= set(ring)
            rings.append(ring)
            prev = ring
        # the lids' rest evened (a ring beyond), and every head point near the eye kept off the ball
        ring3 = sorted({u for v in prev for u in nbr.get(v, ()) if u not in done and u in hps})
        for v in inner:
            dn = (P[v] - C) / EYE_RAD
            P[v] = C + dn / max(np.linalg.norm(dn), 1e-9) * EYE_RAD * (1.0 - 0.002 / EYE_R)
        for i in hpts:
            if i in done or s * P[i][0] <= 0:
                continue
            dn = (P[i] - C) / EYE_RAD
            dd = np.linalg.norm(dn)
            if dd < 1.0 + 2.5 * LID_THICK / EYE_R:
                P[i] = C + dn / dd * EYE_RAD * (1.0 + 2.5 * LID_THICK / EYE_R)
        # (the rings placed by angle stood as flat wedges round the corners: evened with their neighbours, the lid's
        # edge held)
        for _ in range(LID_EVEN):
            for u in [w for r in rings for w in r]:
                ns = [w for w in nbr.get(u, ()) if w in hps]
                avg = np.mean([P[w] for w in ns], 0)
                P[u] = P[u] * 0.6 + avg * 0.4
        for u in [w for r in rings for w in r]:
            dn = (P[u] - C) / EYE_RAD
            dd = np.linalg.norm(dn)
            if dd < 1.0 + 1.5 * LID_THICK / EYE_R:
                P[u] = C + dn / dd * EYE_RAD * (1.0 + 1.5 * LID_THICK / EYE_R)
        for _ in range(3):
            for u in ring3:
                ns = [w for w in nbr.get(u, ()) if w in hps]
                P[u] = P[u] * 0.5 + np.mean([P[w] for w in ns], 0) * 0.5
        # the upper lid's fold: its second ring a little proud, a soft crease above it
        for u in rings[1] if len(rings) > 1 else []:
            if float(hrow(P[u][2])) < mc0[1]:
                P[u][1] -= 0.0006
        for u in ring3:
            if float(hrow(P[u][2])) < mc0[1] - 4:
                P[u][1] += 0.0005
        # the margin's roll into the socket
        ring2 = []
        mid = np.array((C[0], C[2]))
        for v in loop:
            xz = P[v][[0, 2]]
            dvec = mid - xz
            xz2 = xz + dvec / max(np.linalg.norm(dvec), 1e-9) * LID_ROLL[0]
            P = np.vstack([P, (xz2[0], ball_y(xz2[0], xz2[1], C) + LID_ROLL[1], xz2[1])])
            M.P.append(P[-1].copy())
            M.part.append("head")
            weights.append(dict(weights[v]))
            ring2.append(len(M.P) - 1)
        M.P = [p for p in P]
        lid_uv, best = None, None
        for fi, f in enumerate(M.faces):
            if fi in cut or fi not in face_uv or face_uv[fi][0] != "face" or M.fpart[fi] != "head":
                continue
            for v, q_ in zip(f, face_uv[fi][1]):
                d = (s * P[v][0] / HS - 80.0) ** 2 + (float(hrow(P[v][2])) - 1060.0) ** 2
                if P[v][1] < 0 and (best is None or d < best):
                    best, lid_uv = d, q_
        for j in range(n):
            a, b = loop[j], loop[(j + 1) % n]
            f = [a, b, ring2[(j + 1) % n], ring2[j]]
            if np.dot(face_normal(P, f), P[f].mean(0) - C) < 0:
                f = f[::-1]
            M.face(f, "head")
            face_uv[len(M.faces) - 1] = ("face", [lid_uv if lid_uv is not None else (0.0, 0.0)] * 4)
        M.tag.setdefault("lid_hold", []).extend(list(loop) + list(ring2))
        cols_ = [s * P[v][0] / HS for v in loop]
        rows_ = [float(hrow(P[v][2])) for v in loop]
        print("BOY EYES lid edge: columns %.0f to %.0f, rows %.0f to %.0f (outline %.0f to %.0f, %.0f to %.0f)" % (min(cols_), max(cols_), min(rows_), max(rows_), poly[:, 0].min(), poly[:, 0].max(), poly[:, 1].min(), poly[:, 1].max()))
        eyes.append((C, s))
        print("BOY EYES %s (lid loops): opening of %d faces, margin %d points, rings %s, ball at %s" % (
            "left" if s > 0 else "right", len(hole), n, [len(r) for r in rings], np.round(C, 4)))
    return M, face_uv, weights, under, cut, eyes


def eye_texture(path, size=256):
    """The eyeball's picture, planar from its front: white, his olive-green iris (the sheet's: lighter round the pupil,
    a darker rim), the pupil, a small light."""
    k = (np.arange(size) + 0.5) / size * 2.0 - 1.0
    X, Y = np.meshgrid(k, k)
    r = np.hypot(X * EYE_RX / EYE_R, Y)
    ri = EYE_IRIS[2] * HS / EYE_R
    rp = ri * EYE_PUPIL
    sclera = np.array((0.94, 0.92, 0.88))
    img = np.zeros((size, size, 3))
    img[:] = sclera * (1.0 - 0.16 * np.clip((r - 0.75) / 0.25, 0, 1))[..., None]
    t = np.clip(r / ri, 0, 1)
    iris_in = np.array((0.62, 0.58, 0.32))
    iris_out = np.array((0.34, 0.36, 0.18))
    ang = np.arctan2(Y, X)
    rays = 0.05 * np.sin(ang * 23.0) + 0.03 * np.sin(ang * 37.0 + 1.3)
    iris = iris_in[None, None, :] * (1 - t[..., None] ** 1.4) + iris_out * (t[..., None] ** 1.4)
    iris = iris * (1.0 + rays[..., None] * (t[..., None] > 0.45))
    ring = np.clip((t - 0.86) / 0.14, 0, 1)[..., None]
    iris = iris * (1 - ring) + np.array((0.16, 0.15, 0.1)) * ring
    inn = (r < ri)[..., None]
    soft = np.clip((ri - r) / 0.02, 0, 1)[..., None]
    img = img * (1 - soft * inn) + iris * soft * inn
    pup = np.clip((rp - r) / 0.02, 0, 1)[..., None]
    img = img * (1 - pup) + np.array((0.04, 0.04, 0.05)) * pup
    # (seventh pass) the upper lid's shadow on the ball: no white shows over the iris, the stare softened
    img = img * (1.0 - 0.5 * np.clip((Y - 0.32) / 0.4, 0, 1))[..., None]
    hl = np.clip((0.09 - np.hypot(X * EYE_RX / EYE_R - 0.12, Y - 0.14)) / 0.03, 0, 1)[..., None]
    img = img * (1 - hl) + np.array((1.0, 1.0, 0.98)) * hl
    save_rgb(path, img[::-1])


def eye_balls(eyes):
    """Two balls (16 round, 12 from front to back), their poles straight ahead; UVs planar from the front."""
    P, F = [], []
    nu, nv = (14, 8) if HEAD2 else (12, 8)
    for C, s in eyes:
        base = len(P)
        for i in range(nv + 1):
            th = math.pi * i / nv
            for j in range(nu):
                ph = math.tau * j / nu
                d = np.array((math.sin(th) * math.cos(ph), -math.cos(th), math.sin(th) * math.sin(ph)))
                if HEAD2:
                    # (eleventh pass: the poles up and down, not at the pupil, where the fan showed as a dark star)
                    d = np.array((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)))
                P.append(C + d * EYE_RAD)
        for i in range(nv):
            for j in range(nu):
                jj = (j + 1) % nu
                F.append([base + i * nu + j, base + i * nu + jj, base + (i + 1) * nu + jj, base + (i + 1) * nu + j])
    P = np.array(P)
    out = []
    for f in F:
        cen = P[f].mean(0)
        C = min(eyes, key=lambda e: np.linalg.norm(cen - e[0]))[0]
        uv = [(0.5 + 0.5 * (P[v] - C)[0] / EYE_RAD[0], 0.5 + 0.5 * (P[v] - C)[2] / EYE_RAD[2]) for v in f]
        if np.dot(face_normal(P, f), cen - C) < 0:
            f, uv = f[::-1], uv[::-1]
        out.append((f, uv))
    return P, out


# ------------------------------------------------------------------------------------------------------------------
# Paint by rule (sixth pass). The critic of round five: "grimy ... a brown wash in every crease, dark outline-like
# lines on the neck, collarbones, armpits and round the knees, streaks on the arms and legs, blotchy mottling on the
# chest and scalp ... The sheet is clean, smooth, light young skin with freckles." The cause was the sheet's drawn line
# work and painted shading laid onto him by projection. So his body, scalp, ears and neck are now painted by rule in
# his own tones (one clean base, soft rose warmth at knees, elbows, knuckles and ear rims, freckles scattered on his
# shoulders, upper chest and back and forearms, soft rose shade only in true creases from the mesh's own ambient
# occlusion, the scabbed knees as small marks); only the face keeps the sheet's painting, toned to the same base and
# faded into the rule paint round its edge. `--sheet-paint` brings back the projected paint.
# ------------------------------------------------------------------------------------------------------------------

RULE_PAINT = "--sheet-paint" not in ARGS
SKIN_BASE = np.array((0.87, 0.725, 0.635))   # unlit; the sheet's lit peach is about (0.91, 0.75, 0.65) (0.86, 0.69, 0.59 lit too orange)
ROSE = np.array((1.03, 0.85, 0.83))          # the multiplier at a full blush
SHADE = np.array((0.9, 0.8, 0.79))           # the multiplier in the deepest crease (warm, never brown-grey)
FRECKLE = np.array((0.8, 0.63, 0.55))        # the multiplier at a freckle's middle


def vertex_ao(M, rays=48, reach=0.045):
    """Each point's openness (1 open, 0 shut in), by rays over its outward half, nearer hits counting more."""
    if len(M.tag.get("ao", ())) == len(M.P):
        return M.tag["ao"]
    from mathutils.bvhtree import BVHTree
    P = np.array(M.P)
    tris = M.tris()
    bvh = BVHTree.FromPolygons([Vector(p) for p in P], [list(t) for t in tris])
    N = normals_of(P, tris)
    rng = np.random.default_rng(7)
    D = rng.normal(size=(rays, 3))
    D /= np.linalg.norm(D, axis=1, keepdims=True)
    ao = np.ones(len(P))
    for i in range(len(P)):
        n = N[i]
        d = D * np.where(D @ n < 0, -1.0, 1.0)[:, None]
        o = Vector(P[i] + n * 0.0012)
        c = d @ n
        shut = 0.0
        for dd, cc in zip(d, c):
            loc, _, _, dist = bvh.ray_cast(o, Vector(dd), reach)
            if loc is not None:
                shut += cc * (1.0 - dist / reach)
        ao[i] = 1.0 - shut / max(float(c.sum()), 1e-6)
    M.tag["ao"] = ao
    return ao


def texel_scalar(M, face_uv, picture, values):
    """A value per point carried onto a picture's texels (as texel_geometry carries the points)."""
    V = np.repeat(np.asarray(values, float)[:, None], 3, 1)
    P = np.array(M.P)
    return texel_geometry(M, face_uv, picture, V, normals_of(P, M.tris()))[0][..., 0]


def soft_noise(pos, scale, seed, n=6):
    rng = np.random.default_rng(seed)
    out = np.zeros(pos.shape[:-1])
    for _ in range(n):
        k = rng.normal(size=3)
        k *= math.tau / scale / np.linalg.norm(k)
        out += np.sin(pos @ k + rng.uniform(0, math.tau))
    return out / math.sqrt(n / 2.0)


def blush(rgb, w, tint=ROSE):
    return rgb * (1.0 + (np.asarray(tint, float) - 1.0) * np.clip(w, 0, 1)[..., None])


def nearest_texel(pos, sel, at):
    idx = np.flatnonzero(sel)
    if not len(idx):
        return None
    d = np.linalg.norm(pos.reshape(-1, 3)[idx] - at, axis=1)
    return pos.reshape(-1, 3)[idx[int(np.argmin(d))]]


def spots(rgb, pos, sel, centres, radii, strengths, tint):
    """Small round marks in 3D (so they cross seams whole): each centre's texels drawn toward the tint."""
    out = rgb.copy()
    flat = out.reshape(-1, 3)
    idx = np.flatnonzero(sel)
    if not len(idx):
        return out
    Q = pos.reshape(-1, 3)[idx]
    tint = np.asarray(tint, float)
    for c, r, s in zip(centres, radii, strengths):
        box = np.all(np.abs(Q - c) < r * 1.2, axis=1)
        if not box.any():
            continue
        d = np.linalg.norm(Q[box] - c, axis=1)
        w = s * (1.0 - smooth01(r * 0.45, r, d))
        j = idx[box]
        flat[j] = flat[j] * (1.0 - w[:, None] * (1.0 - tint))
    return out


def freckles(rgb, pos, region, count, seed, r=(0.0008, 0.0017), s=(0.22, 0.5)):
    idx = np.flatnonzero(region > 0.01)
    if not len(idx) or count <= 0:
        return rgb
    rng = np.random.default_rng(seed)
    p = region.ravel()[idx]
    pick = rng.choice(idx, count, p=p / p.sum())
    C = pos.reshape(-1, 3)[pick]
    return spots(rgb, pos, region > 0.01, C, rng.uniform(*r, count), rng.uniform(*s, count), FRECKLE)


def body_marks(rgb, pos, nrm, hit, fam, joints):
    """(seventh pass; the critic: "warm peach skin with hand-painted variation: rosy at the nose, cheeks, ears, elbows,
    knees, knuckles and toes ... painted soft shading under the jaw, armpits, the waistband and between the ribs ...
    freckles ... scattered over the shoulders, upper back, chest and forearms"; "small pink nipples", "the bottom of
    the ribcage readable as a soft curve", "a visible spine channel, and shoulder blades", nails on fingers and toes)
    Marks laid by rule in 3D on his own joints. The sheet's navel sits at row 672, 2 cm over the band (row 692): the
    band stays where the sheet draws it and the navel is painted (the critic asked the band 3 to 4 cm lower)."""
    pos = np.nan_to_num(pos)
    nrm = np.nan_to_num(nrm)
    x, y, z = pos[..., 0], pos[..., 1], pos[..., 2]
    torso = hit & np.isin(fam, ("torso", "shoulder"))
    front = smooth01(-0.2, -0.6, nrm[..., 1])
    back = smooth01(0.2, 0.6, nrm[..., 1])
    zs = float(joints["shoulder_l"][2])
    xs = abs(float(joints["shoulder_l"][0]))
    # the hands and feet warmer, the toes' and fingers' ends rosier
    # (faded toward the wrist and the ankle so no step shows at the seams there)
    for sfx in ("_l", "_r"):
        kn = np.array(joints["knuckles" + sfx], float)
        # (eleventh pass: on the back of the hand only, and less: on the palm it showed as a darker orange patch
        # ending in an edge at the wrist)
        Tb_ = np.array(joints["hand_frame" + sfx][0], float)
        rgb = blush(rgb, (hit & (fam == "hand")) * 0.16 * smooth01(-0.1, 0.5, (nrm * Tb_).sum(-1)) * np.exp(-(np.linalg.norm(pos - kn, axis=-1) / 0.04) ** 2))
    rgb = blush(rgb, (hit & (fam == "foot")) * 0.28 * (1.0 - smooth01(0.025, 0.06, z)))
    for sfx in ("_l", "_r"):
        for name in FINGERS + ("thumb",):
            J = [np.array(p, float) for p in joints[name + sfx]]
            tip, j2 = J[3], J[2]
            u = (tip - j2) / max(np.linalg.norm(tip - j2), 1e-6)
            Tb = np.array(joints["hand_frame" + sfx][0], float)
            if name == "thumb":
                Tb = np.array(joints["thumb_back" + sfx], float)
                Tb = Tb - (Tb @ u) * u
                Tb /= max(np.linalg.norm(Tb), 1e-6)
            hb = hit & (fam == "hand") & ((nrm * Tb).sum(-1) > 0.35)
            at = nearest_texel(pos, hb, tip - u * 0.0055 + Tb * 0.01)
            rgb = blush(rgb, (hit & (fam == "hand")) * 0.3 * np.exp(-(np.linalg.norm(pos - tip, axis=-1) / 0.008) ** 2))
            if at is not None:
                rgb = spots(rgb, pos, hb, [at], [0.0047 if name != "thumb" else 0.0056], [0.55], (1.06, 0.94, 0.93))
                rgb = spots(rgb, pos, hb, [at + u * 0.0035], [0.0026], [0.4], (1.08, 1.03, 1.0))
        # toenails: the top of each toe's end, found as the foot's front in strips across it
        ft = hit & (fam == "foot")
        side = np.sign(x) == (1.0 if sfx == "_l" else -1.0)
        ft &= side
        if ft.any():
            an = np.array(joints["ankle" + sfx], float)
            tt = np.array(joints["toe_tip" + sfx], float)
            fw = tt - an
            fw[2] = 0.0
            fw /= np.linalg.norm(fw)
            ac = np.array((-fw[1], fw[0], 0.0))
            pr = (pos - an) @ fw
            cr = (pos - an) @ ac
            bins = np.linspace(cr[ft].min(), cr[ft].max(), 30)
            bi = np.clip(np.digitize(cr, bins) - 1, 0, 28)
            fr = np.full(29, -1.0)
            for i in range(29):
                s_ = ft & (bi == i)
                if s_.any():
                    fr[i] = pr[s_].max()
            fmax = fr[bi]
            dd = fmax - pr
            nail = ft & (nrm[..., 2] > 0.25) & (dd > 0.002) & (dd < 0.011) & (z < 0.03)
            rgb = blush(rgb, ft * 0.45 * np.exp(-(dd / 0.012) ** 2))
            rgb[nail] = rgb[nail] * 0.75 + np.array((0.95, 0.8, 0.76)) * 0.25
    # the navel (the sheet's row 672) and a little shade round it
    zn = float(body_z(672))
    nav = np.exp(-((x / 0.0045) ** 2 + ((z - zn) / 0.006) ** 2)) * front * torso
    rgb = blush(rgb, nav * 0.8, (0.78, 0.6, 0.56))
    rgb = blush(rgb, np.exp(-((x / 0.012) ** 2 + ((z - zn - 0.004) / 0.012) ** 2)) * front * torso * 0.4, SHADE)
    # the nipples
    for s in (1.0, -1.0):
        c = np.array((s * xs * 0.42, 0.0, zs - 0.105))
        w = np.exp(-(((x - c[0]) / 0.006) ** 2 + ((z - c[2]) / 0.006) ** 2)) * front * torso
        rgb = blush(rgb, w * 0.6, (0.9, 0.7, 0.68))
    # the ribcage's lower edge: a soft shade along an arch from the breastbone's end out and down
    zr = zs - 0.2
    arch = zr - 1.1 * np.abs(x) + 6.0 * x ** 2
    rgb = blush(rgb, np.exp(-((z - (arch - 0.008)) / 0.009) ** 2) * (np.abs(x) > 0.012) * (np.abs(x) < 0.1) * front * torso * 0.45, SHADE)
    # the collarbones: a light ridge with a soft shade under it, from the notch to each shoulder's point
    zn0 = zs + 0.04
    for s in (1.0, -1.0):
        t = np.clip((s * x - 0.018) / (xs - 0.018), 0, 1)
        zc = zn0 - 0.012 * np.sin(np.pi * t * 0.8) + 0.008 * t
        on = (s * x > 0.016) & (s * x < xs + 0.01) & (front > 0) & torso
        rgb = blush(rgb, np.exp(-((z - (zc - 0.009)) / 0.009) ** 2) * on * 0.22, SHADE)
        rgb = blush(rgb, np.exp(-((z - zc) / 0.004) ** 2) * on * 0.3, (1.03, 1.0, 0.98))
    # the spine's channel and the shoulder blades' inner and lower edges, on his back
    rgb = blush(rgb, np.exp(-(x / 0.006) ** 2) * back * torso * (z < zs + 0.03) * (z > float(body_z(700))) * 0.25, SHADE)
    for s in (1.0, -1.0):
        bx, bz = s * 0.055, zs - 0.06
        d = np.hypot((x - bx) / 0.045, (z - bz) / 0.075)
        rgb = blush(rgb, np.exp(-((d - 1.0) / 0.12) ** 2) * (z < bz + 0.02) * back * torso * 0.18, SHADE)
    # more freckles: the upper back, the arms, the tops of the shoulders
    up = torso * back * smooth01(zs - 0.2, zs - 0.05, z)
    rgb = freckles(rgb, pos, up * hit, 260, 61)
    arms = (hit & (fam == "arm")) * smooth01(-0.2, 0.5, nrm[..., 2] + 0.3)
    rgb = freckles(rgb, pos, arms * 1.0, 110, 67, s=(0.15, 0.4))
    return rgb


def rule_paint(M, face_uv, picture, pos, nrm, hit, fam, joints):
    """The rule paint for one picture (see above); fam is each texel's part family."""
    ao = texel_scalar(M, face_uv, picture, vertex_ao(M))
    rgb = np.tile(SKIN_BASE, pos.shape[:-1] + (1,))
    # a faint living variation (warmer and cooler by a couple of percent over hand-sized patches)
    v = soft_noise(pos, 0.09, 11)
    rgb = rgb * (1.0 + 0.018 * v[..., None] * np.array((0.6, 1.0, 1.3)))
    # soft rose shade only where the mesh is truly shut in (armpit, under the chin, between fingers and toes, ear bowl)
    crease = np.clip((0.78 - ao) / 0.45, 0, 1) ** 1.3
    # (eighth pass) on the hands only the truly shut-in places: the vertex shade of each finger's knuckle ring, pulled
    # out a little by the knuckle bump, drew thin dark lines across the fingers in the close-up
    crease = np.where(fam == "hand", 0.22 * (1.0 - 0.8 * SKIN_ROSE) * np.clip((0.58 - ao) / 0.4, 0, 1) ** 1.3, crease)   # (eleventh pass: from 0.5, the cupped palm read as a darker orange patch; twelfth, 9. skin: less again)
    rgb = blush(rgb, crease, SHADE)
    if picture == "skin" and joints is not None:
        ny = nrm[..., 1]
        for sfx, s_ in (("_l", 1.0), ("_r", -1.0)):
            side = np.sign(pos[..., 0]) == s_
            kn = np.array(joints["knee" + sfx], float)
            d = np.linalg.norm((pos - kn) * np.array((1.0, 0.6, 1.0)), axis=-1)
            rgb = blush(rgb, (0.55 + 0.25 * SKIN_ROSE) * np.exp(-(d / 0.034) ** 2) * smooth01(0.0, 0.5, -ny) * side)
            el = np.array(mirror_x(joints["elbow_l"], s_), float)
            d = np.linalg.norm(pos - el, axis=-1)
            rgb = blush(rgb, 0.35 * np.exp(-(d / 0.03) ** 2) * side)
            kk = np.array(joints["knuckles" + sfx], float)
            Tb = np.array(joints["hand_frame" + sfx][0], float)
            d = np.linalg.norm(pos - kk, axis=-1)
            rgb = blush(rgb, (0.4 + 0.25 * SKIN_ROSE) * np.exp(-(d / 0.024) ** 2) * smooth01(0.0, 0.5, (nrm * Tb).sum(-1)) * side)
            # the scabbed knee: three small marks on the kneecap, a soft pink round them
            cap = nearest_texel(pos, hit & (fam == "leg") & side & (ny < -0.5), kn + np.array((0.0, -0.06, 0.0)))
            if cap is not None:
                rng = np.random.default_rng(23 if s_ > 0 else 29)
                C = [cap + np.array((rng.uniform(-0.01, 0.01), 0.0, rng.uniform(-0.016, 0.006))) for _ in range(3)]
                legs = hit & (fam == "leg") & side
                rgb = spots(rgb, pos, legs, [cap + np.array((0.0, 0.0, -0.004))], [0.016], [0.25], (1.0, 0.86, 0.84))
                rgb = spots(rgb, pos, legs, C, rng.uniform(0.0016, 0.0026, 3), rng.uniform(0.45, 0.65, 3), (0.74, 0.46, 0.42))
        # two small scrapes on his right hand's first knuckles (the sheet's story detail, small)
        for name, k in (("index", 0.5), ("middle", 0.4)):
            K = np.array(joints[name + "_r"][1], float)
            Tb = np.array(joints["hand_frame_r"][0], float)
            at = nearest_texel(pos, hit & (fam == "hand") & (pos[..., 0] < 0) & ((nrm * Tb).sum(-1) > 0.4), K + Tb * 0.02)
            if at is not None:
                rgb = spots(rgb, pos, hit & (fam == "hand"), [at], [0.0022], [k], (0.8, 0.55, 0.52))
        # freckles: shoulders, the top of his chest and back (most on the shoulders' tops), and the forearms
        zs = float(joints["shoulder_l"][2])
        top = smooth01(zs - 0.17, zs - 0.03, pos[..., 2]) * (1.0 - smooth01(zs + 0.04, zs + 0.07, pos[..., 2]))
        top = top * np.isin(fam, ("torso", "arm", "shoulder")) * (0.5 + 0.5 * np.clip(nrm[..., 2] + 0.3, 0, 1))
        rgb = freckles(rgb, pos, top * hit, 260, 31)
        el_z = float(joints["elbow_l"][2])
        wr_z = float(joints["wrist_l"][2])
        fore = hit & (fam == "arm") & (pos[..., 2] < el_z) & (pos[..., 2] > wr_z)
        rgb = freckles(rgb, pos, fore * 1.0, 70, 37, s=(0.15, 0.35))
        hb = hit & (fam == "hand")
        rgb = freckles(rgb, pos, hb * 1.0, 16, 41, r=(0.0007, 0.0012), s=(0.12, 0.25))
        rgb = body_marks(rgb, pos, nrm, hit, fam, joints)
    if picture == "face":
        ear = hit & (fam == "ear")
        xa = np.abs(pos[..., 0])
        rgb = blush(rgb, ear * (0.05 + 0.1 * SKIN_ROSE + (0.33 + 0.12 * SKIN_ROSE) * smooth01(0.095, 0.125, xa)))   # (seventh pass: from 0.18 + 0.4, "saturated, uniform pink-red")
    return np.clip(rgb, 0, 1)


FACE_BY_RULE = "--sheet-face" not in ARGS
BROW_ROW = float(arg("--brow-row", "1046"))      # (tenth pass: from 1042; the critic: "lower the brows ... thicken them ... darker")
BROW_THICK = float(arg("--brow-thick", "9.0"))   # (tenth pass: from 6.5)
BROW_TINT = (0.5, 0.37, 0.24)


def lip_seam(M, mk):
    """(ninth pass) The lips' meeting edge: the shortest way along the head's edges from one mouth corner through the
    mouth's middle to the other (the base head's closed mouth meets on one row of edges). Gives (x, z) sorted by x, or
    None. Printed: how far it lies from the old painted curve."""
    import heapq
    P = np.array(M.P)
    hp = set(i for i, p in enumerate(M.part) if part_family(p) == "head")
    nb = {}
    for f, fp in zip(M.faces, M.fpart):
        if part_family(fp) != "head":
            continue
        for i in range(len(f)):
            a, b = f[i], f[(i + 1) % len(f)]
            nb.setdefault(a, set()).add(b)
            nb.setdefault(b, set()).add(a)

    def path(a, b):
        dist, prev, hq = {a: 0.0}, {}, [(0.0, a)]
        while hq:
            d, v = heapq.heappop(hq)
            if v == b:
                break
            if d > dist.get(v, 1e9):
                continue
            for u in nb.get(v, ()):
                if u not in hp:
                    continue
                # (along the mouth: steps that climb or drop cost more)
                st = P[u] - P[v]
                nd = d + float(np.linalg.norm(st)) + 3.0 * abs(float(st[2]))
                if nd < dist.get(u, 1e9):
                    dist[u], prev[u] = nd, v
                    heapq.heappush(hq, (nd, u))
        if b not in dist:
            return None
        out = [b]
        while out[-1] != a:
            out.append(prev[out[-1]])
        return out[::-1]
    try:
        p1 = path(mk["mouth_l"], mk["mouth"])
        p2 = path(mk["mouth"], mk["mouth_r"])
    except (KeyError, TypeError):
        return None
    if not p1 or not p2:
        return None
    ids = p1 + p2[1:]
    Q = P[ids]
    o = np.argsort(Q[:, 0])
    x, z = Q[o, 0], Q[o, 2]
    ids = [ids[i] for i in o]
    zm = float(P[mk["mouth"], 2])
    xc = abs(float(P[mk["mouth_l"], 0]))
    old = zm + 0.0016 * (x / max(xc, 1e-4)) ** 2
    print("BOY lip seam points (x, z mm): %s" % [(round(1000 * float(a), 1), round(1000 * float(b), 1)) for a, b in zip(x, z)])
    print("BOY lip seam: %d points along the meeting edge; the old painted line lay up to %.1f mm off it" % (len(ids), 1000 * float(np.abs(old - z).max())))
    return x, z, ids


def seam_smooth(x, z):
    """The seam's heights smoothed along it (it zigzags a little between the lips' rows near the corners)."""
    zs = np.array(z, float)
    for _ in range(3):
        zz = zs.copy()
        zz[1:-1] = 0.25 * zs[:-2] + 0.5 * zs[1:-1] + 0.25 * zs[2:]
        zs = zz
    return zs


def face_features(M, rgb, pos, nrm, hit, fam):
    """(seventh pass; the critic: "the smile is almost entirely paint: a long dark line from cheek to cheek, with heavy
    dark brackets at the corners and painted nasolabial creases ... a second dark horizontal line under the lower lip
    ... a darker grey-brown patch over the jaw and chin": the sheet's painting projected onto a face of another shape)
    The face drawn by rule on his own landmarks, in head-sheet columns (out from his middle) and rows: soft sandy brows,
    a dark lash line along each upper lid thickening outward, a soft lid crease, rosy cheeks and nose tip, a small soft
    smile line between the modelled lips with a rose lower lip, freckles over the nose and cheeks. No folds, no lines
    under the lip, nothing on the jaw."""
    out = rgb.copy()
    pos = np.nan_to_num(pos)
    nrm = np.nan_to_num(nrm)
    out = np.where(np.isfinite(out), out, SKIN_BASE)
    # (the face only: the back of his head lies in the same columns and rows)
    head = hit & (fam == "head") & (pos[..., 1] < -0.02)
    col = pos[..., 0] / HS
    ac = np.abs(col)
    row = hrow(pos[..., 2])
    fwd = smooth01(0.05, 0.35, -nrm[..., 1])
    mk = M.tag["head_marks"]
    Pm = np.array(M.P)

    def tint(w, c, a=1.0):
        nonlocal out
        w = np.clip(w, 0, 1)[..., None] * a
        out = out * (1.0 - w) + np.asarray(c, float) * w

    def mult(w, m):
        nonlocal out
        out = out * (1.0 + (np.asarray(m, float) - 1.0) * np.clip(w, 0, 1)[..., None])
    # brows: an arc above each eye, the inner end lower and fuller, sandy blond (the hair's), a little stroked
    ti = np.clip((ac - 38.0) / 88.0, 0, 1)
    rb = BROW_ROW - 10.0 * np.sin(np.pi * np.clip(ti * 0.85 + 0.08, 0, 1)) ** 0.8 + 3.0 * ti
    hh = BROW_THICK - 3.0 * ti
    ends = smooth01(32.0, 42.0, ac) * (1.0 - smooth01(118.0, 128.0, ac))
    strokes = 0.85 + 0.15 * np.sin(col * 1.9 + row * 0.7)
    if BROW_WARM:
        # (twelfth pass, 4. brows) a little thicker and warmer, the arch a little higher in the middle
        hh = hh + 2.0 * BROW_WARM
        rb = rb - 2.0 * BROW_WARM * np.sin(np.pi * np.clip(ti, 0, 1))
        tint(np.exp(-((row - rb) / hh) ** 4) * ends * strokes * fwd * head,
             np.array(BROW_TINT) * (1 - BROW_WARM) + np.array((0.6, 0.41, 0.22)) * BROW_WARM, 0.74 + 0.08 * BROW_WARM)
    else:
        tint(np.exp(-((row - rb) / hh) ** 4) * ends * strokes * fwd * head, BROW_TINT, 0.74)   # (eighth pass: softer, blond-brown; from 0.64, 0.5, 0.34 at 0.72)
    # the eye: the opening's upper and lower curves in (column, row)
    poly = eye_outline()
    up = poly[:25]
    low = poly[24:][::-1]
    lt = np.interp(ac, up[:, 0], up[:, 1], left=np.nan, right=np.nan)
    lb = np.interp(ac, low[:, 0], low[:, 1], left=np.nan, right=np.nan)
    t = np.clip((ac - EYE_INNER[0]) / (EYE_OUTER[0] - EYE_INNER[0]), 0, 1)
    if LASH_ON_LID and M.tag.get("eye_margins"):
        # (twelfth pass, 2. lash_on_lid) the lid's paint laid on the opening's actual edge as the mesh has it (its upper
        # and lower curves read off the margin loop's points), not on the sheet's outline, which the edge only nears
        lp = np.array([(abs(Pm[v][0]) / HS, float(hrow(Pm[v][2]))) for v in M.tag["eye_margins"][0][0]])
        i_in, i_out = int(np.argmin(lp[:, 0])), int(np.argmax(lp[:, 0]))
        c_in, c_out = lp[i_in], lp[i_out]
        mid = c_in[1] + (lp[:, 0] - c_in[0]) / (c_out[0] - c_in[0]) * (c_out[1] - c_in[1])
        upp = np.vstack([c_in, lp[lp[:, 1] < mid - 0.5], c_out])
        low_ = np.vstack([c_in, lp[lp[:, 1] > mid + 0.5], c_out])
        upp, low_ = upp[np.argsort(upp[:, 0])], low_[np.argsort(low_[:, 0])]
        lt = np.interp(ac, upp[:, 0], upp[:, 1], left=np.nan, right=np.nan)
        lb = np.interp(ac, low_[:, 0], low_[:, 1], left=np.nan, right=np.nan)
        t = np.clip((ac - c_in[0]) / (c_out[0] - c_in[0]), 0, 1)
        flick_at = (c_out[0] + 3.0, c_out[1] - 3.0)
    else:
        flick_at = (EYE_OUTER[0] + 4.0, EYE_OUTER[1] - 4.0)
    inside = np.isfinite(lt)
    d_up = np.where(inside, lt - row, 99.0)
    d_low = np.where(inside & np.isfinite(lb), row - lb, 99.0)
    # the lash line (on the lid's margin and just above it), thickest at the outer end, with a small flick out
    # (ninth pass, for the face rig: a thin line at the margin only, no paint below it on the hidden rim; the wide band
    # stretched into brown streaks over a closing lid)
    lash = np.exp(-((d_up - 0.6) / (0.9 + 0.7 * t)) ** 2) * (0.55 + 0.45 * smooth01(0.0, 0.25, t)) * smooth01(-0.6, 0.2, d_up)   # (eighth pass: along the whole lid, over the white flecks at its margin)
    flick_c = np.array(flick_at)
    flick = np.exp(-(((ac - flick_c[0]) / 5.0) ** 2 + ((row - flick_c[1]) / 2.2) ** 2))
    if LASH_ON_LID and M.tag.get("eye_margins"):
        # (a thin line just above the edge, a little heavier outward, none on or below the edge itself)
        lash = np.exp(-((d_up - 1.6) / (1.1 + 0.7 * t)) ** 2) * (0.75 + 0.25 * smooth01(0.0, 0.3, t)) * smooth01(0.0, 0.8, d_up)
        flick = flick * 0.6
    if LASH_ON_LID and M.tag.get("eye_margins"):
        tint(np.maximum(lash, flick) * head, (0.21, 0.14, 0.11), 0.9)
    else:
        tint(np.maximum(lash, flick) * head, (0.28, 0.19, 0.14), 0.75)
    # the lid crease and a little shade under the brow
    mult(np.exp(-((d_up - 10.0) / 2.6) ** 2) * 0.55 * head, SHADE)
    # the lower lid: a faint warm line, no dark rim
    mult(np.exp(-((d_low - 1.5) / 1.8) ** 2) * 0.35 * head, (0.97, 0.86, 0.84))
    # cheeks, nose: rose
    for s in (1.0, -1.0):
        mult(np.exp(-(((col - s * 95.0) / 40.0) ** 2 + ((row - 1166.0) / 30.0) ** 2)) * (0.42 + 0.18 * SKIN_ROSE) * head, ROSE)
    nose_row = float(hrow(Pm[mk["nose"], 2]))
    mult(np.exp(-((col / 20.0) ** 2 + ((row - nose_row - 4.0) / 16.0) ** 2)) * (0.45 + 0.25 * SKIN_ROSE) * (1.0 - 0.6 * NOSE_LINE * (NOSE_BALL_TO > 0)) * head, (1.0, 0.8, 0.77))
    # the mouth: a short soft line on the lips' seam, its ends turned up; a rose lower lip; small dimples
    zm = float(Pm[mk["mouth"], 2])
    xc = abs(float(Pm[mk["mouth_l"], 0]))
    xr = pos[..., 0] / max(xc, 1e-4)
    zl = zm + 0.0016 * xr ** 2
    seam = lip_seam(M, mk)
    if seam is not None:
        # (ninth pass, for the face rig: the line laid on the lips' own meeting edge, which the rig cuts open, not on a
        # curve of its own; the ends still turn up a little past the corners)
        zl = np.interp(pos[..., 0], seam[0], seam_smooth(seam[0], seam[1])) + 0.0016 * np.clip(np.abs(xr) - 0.85, 0, None) ** 2
    near_front = (pos[..., 1] < float(Pm[mk["mouth"], 1]) + 0.012) & head
    if SMILE_PAINT:
        # (twelfth pass, 3. smile) the sheet's broad closed smile: the line out to the corners and turned up there,
        # a little curl at each end, a fuller rose lower lip, a soft dimple shade beyond each corner
        k_ = SMILE_PAINT
        ax_ = np.abs(xr)
        # (the corners lie further back than the old mask's 12 mm behind the mouth's middle: it cut the line short)
        near_front = (pos[..., 1] < float(Pm[mk["mouth"], 1]) + 0.03) & head & (nrm[..., 1] < -0.2)
        # (the line stays on the lips' meeting edge to the corners, which the face rig traces and cuts open: turned up
        # over the whole mouth it led the rig's cut off the lips, and five of its expressions folded; it turns up only
        # past the corners, into the curls)
        # (and the dark line itself ends a little inside the corners: carried past them it set the rig's corners 45 mm out
        # and its wider cut folded the upper lip in a frown; the turned-up tails beyond are lighter)
        zl = zl + k_ * 0.004 * smooth01(0.85, 1.16, ax_) ** 1.2
        line = np.exp(-((pos[..., 2] - zl) / (0.0011 - 0.0004 * smooth01(0.6, 1.1, ax_))) ** 2)
        tint(line * (1.0 - smooth01(0.8, 1.0, ax_)) * near_front, (0.47, 0.28, 0.26), 0.82)
        tint(line * smooth01(0.78, 0.95, ax_) * (1.0 - smooth01(1.08, 1.2, ax_)) * near_front, (0.6, 0.4, 0.37), 0.45)
        zc_ = zm + k_ * 0.004 + 0.0008
        for s_ in (1.0, -1.0):
            cx_ = s_ * xc * 1.1
            curl = np.exp(-(((pos[..., 0] - cx_) / 0.0011) ** 2 + ((pos[..., 2] - zc_ - 0.0012) / 0.0024) ** 2))
            tint(curl * near_front * k_, (0.62, 0.42, 0.38), 0.35)
            dim = np.exp(-(((pos[..., 0] - s_ * xc * 1.3) / 0.0045) ** 2 + ((pos[..., 2] - zc_) / 0.006) ** 2))
            mult(dim * near_front * 0.35 * k_, SHADE)
        lip = np.exp(-(((pos[..., 2] - (zm - 0.0042)) / 0.0034) ** 2 + (pos[..., 0] / (0.78 * xc)) ** 4))
        mult(lip * near_front, (1.0, 0.78, 0.76))
    else:
        line = np.exp(-((pos[..., 2] - zl) / 0.00075) ** 2) * (1.0 - smooth01(0.75, 1.02, np.abs(xr)))
        tint(line * near_front, (0.58, 0.36, 0.34), 0.6)
        lip = np.exp(-(((pos[..., 2] - (zm - 0.0042)) / 0.0032) ** 2 + (pos[..., 0] / (0.62 * xc)) ** 4))
        mult(lip * near_front * 0.9, (1.0, 0.8, 0.78))
    uplip = np.exp(-(((pos[..., 2] - (zm + 0.0025)) / 0.002) ** 2 + (pos[..., 0] / (0.7 * xc)) ** 4))
    mult(uplip * near_front * 0.35, (1.0, 0.86, 0.84))
    pos_real = pos
    if NOSE_PAINT:
        pos = nose_unscale(M, pos)   # (fifteenth pass: the nose's paint placed as before nose_scale, so it scales with it)
        # (twelfth pass, 5. nose) the nostrils as two soft dark commas under the tip, and the wings' creases faintly
        # (fourteenth pass: with nose_ball2/3 the paint follows those shapes)
        NBB, NBW = (NB2_BALL, NB2_WING) if NB_MODE > 1 else (NB_BALL, NB_WING)
        P3 = NOSE_PAINT3 if NB_MODE > 1 else 0.0
        tip = Pm[mk["nose"]]
        if NOSE_BALL_TO and "nose_ball_tip" in M.tag:
            tip = np.array(M.tag["nose_ball_tip"])   # (thirteenth pass: the paint placed on the ball as nose_ball made it)
        down = smooth01(-0.05, -0.5, nrm[..., 2])
        # (on whatever of the nose faces down, near the tip: the nostrils find themselves on the mesh)
        near_tip = np.exp(-(np.linalg.norm((pos - (tip + (np.array((0.0, NB_NOST[1], -NB_NOST[2])) if NOSE_BALL_TO else np.array((0.0, 0.004, -0.004))))) / np.array((1.0, 1.4, 1.0)), axis=-1) / 0.009) ** 2)
        # (thirteenth pass, nose_paint2: the nostrils and the wings' creases moved out with nose_wings' spread)
        wx = 1.0 + 0.7 * NOSE_SPREAD if NOSE_PAINT2 else 1.0
        for s_ in (1.0, -1.0):
            side_ = np.exp(-((pos[..., 0] - s_ * (NB_NOST[0] if NOSE_BALL_TO else 0.0055 * wx)) / (0.0028 * wx ** 0.5)) ** 2)
            mult(near_tip * side_ * down ** 1.5 * head * NOSE_PAINT * (0.0 if P3 else 1.0), (0.55, 0.4, 0.38))
            if not NOSE_PAINT2:
                c2 = tip + np.array((s_ * 0.0105, 0.007, -0.002))
                d2 = np.linalg.norm((pos - c2) / np.array((0.002, 0.004, 0.005)), axis=-1)
                mult(np.exp(-d2 ** 2) * head * 0.4 * NOSE_PAINT, SHADE)
        if NOSE_PAINT2:
            # (thirteenth pass, nose_paint2) the sheet's nose: a rosy ball, its wings outlined by a soft warm shade where
            # the nose's sides turn away (read off the mesh's own facing, so it follows the form), a light bridge and a
            # soft highlight on the tip
            c_ = tip + (np.array((0.0, NBB[3], -NBB[4])) if NOSE_BALL_TO else np.array((0.0, NOSE_WINGS_AT[0], -NOSE_WINGS_AT[1])))
            field = np.exp(-(((pos - c_) / np.array((0.016 * wx ** 0.5, 0.014, 0.012))) ** 2).sum(-1)) * head
            mult(field * 0.55 * NOSE_PAINT2, (0.97, 0.86, 0.8) if NOSE_TAN else (1.0, 0.84, 0.8))
            sides = smooth01(0.3, 0.75, np.abs(nrm[..., 0])) * smooth01(-0.2, 0.3, -nrm[..., 1])
            mult(field * sides * 0.6 * NOSE_PAINT2 * (0.35 if NOSE_PAINT4 else 1.0), (0.8, 0.62, 0.58))
            if NOSE_TAN:
                # (thirteenth pass, nose_tan) the sheet's nose is a warm tan-rose, not pink: the pink taken back toward
                # tan over the nose, and the nostrils as seen from the front: two soft dark commas on the ball's lower rim
                ball = field * smooth01(0.0, 0.5, -nrm[..., 1])
                tint(ball * head * NOSE_TAN, (0.84, 0.65, 0.57), 0.4)
                rim = smooth01(0.1, 0.5, -nrm[..., 2]) * (1.0 - smooth01(0.75, 0.95, -nrm[..., 2]))
                for s_ in (1.0, -1.0):
                    cm = np.exp(-(((pos[..., 0] - s_ * (NB_NOST[0] + 0.0003 if NOSE_BALL_TO else 0.0062 * wx)) / (0.0032 * wx ** 0.5)) ** 2 + ((pos[..., 2] - (float(tip[2]) - (NB_NOST[2] + 0.0005 if NOSE_BALL_TO else 0.006))) / 0.003) ** 2))
                    mult(cm * rim * head * 0.6 * NOSE_TAN * (0.0 if P3 else 1.0), (0.6, 0.45, 0.42))
            if NOSE_LINE and NOSE_BALL_TO:
                # (thirteenth pass, nose_line) the sheet's nose as painted: a warmer tan over the ball (less pink), and
                # each wing's outline as a soft warm-brown line along its outer edge and top, on the wing's own shape
                # (the ellipsoid nose_ball drew it onto), fading out under the nose
                tint(field * smooth01(0.0, 0.4, -nrm[..., 1]) * head * NOSE_LINE, (0.8, 0.6, 0.51), 0.5)
                for s_ in (1.0, -1.0) if not P3 else ():
                    wc = tip + np.array((s_ * NBW[3], NBW[4], -NBW[5]))
                    r_ = np.array(NBW[:3])
                    sdw = (np.linalg.norm((pos - wc) / r_, axis=-1) - 1.0) * float(r_.min())
                    band = np.exp(-((sdw - 0.0004) / 0.0011) ** 2) * (s_ * pos[..., 0] > NBW[3] * 0.5) * np.maximum(smooth01(float(wc[1]) - 0.004, float(wc[1]), pos[..., 1]), smooth01(NBW[3], NBW[3] + 0.004, s_ * pos[..., 0])) \
                        * smooth01(float(wc[2]) - 0.004, float(wc[2]) + 0.001, pos[..., 2])
                    tint(band * head * NOSE_LINE, (0.55, 0.36, 0.3), 0.55)
            if P3:
                # (fourteenth pass, nose_paint3) the sheet's nose measured against its cheek: ball (167 123 105) and wings
                # (161 117 96) on a cheek of (213 192 167), so the nose is the cheek times about (0.78 0.64 0.63); the
                # model's was (0.85 0.82 0.83). Over the nose's outline seen from the front (ball and wings) the colour is
                # taken toward that warm tan-brown; each wing's outline a soft brown C over its top, outer side and
                # bottom (none on its inner lower side, where the nostril is); under the ball a soft shade; the nostrils
                # crisp dark commas (126 84 68 on the sheet) between ball and wing, their outer ends a little higher.
                xs_, zs_ = pos[..., 0], pos[..., 2]
                # (fifteenth pass) with nose_paint4 the painted wings their own size (np4-wing), inside the scaled wings as built
                NBW_ = NBW if not NOSE_PAINT4 else (NP4_WING[0], NBW[1], NP4_WING[1], NP4_WING[2], NBW[4], NP4_WING[3])
                fwd_ = smooth01(0.1, 0.5, -nrm[..., 1])
                nose_u = np.full(xs_.shape, 9.0)
                shapes_ = [(0.0, NBB[4], NBB[0], NBB[2])] + [(s_ * NBW_[3], NBW_[5], NBW_[0], NBW_[2]) for s_ in (1.0, -1.0)]
                for cx_, cd_, rx_, rz_ in shapes_:
                    nose_u = np.minimum(nose_u, np.hypot((xs_ - cx_) / rx_, (zs_ - (float(tip[2]) - cd_)) / rz_))
                yfade = smooth01(float(tip[1]) + 0.024, float(tip[1]) + 0.014, pos[..., 1])   # (soft, no cut where the nose meets the cheek)
                over = (1.0 - smooth01(0.7, 1.25, nose_u)) * yfade * head
                mult(over * P3, (0.95, 0.88, 0.86))
                tint(over * P3, (0.7, 0.5, 0.41), 0.3)
                for s_ in (1.0, -1.0):
                    cx_, cz_ = s_ * NBW_[3], float(tip[2]) - NBW_[5]
                    u_ = np.hypot((xs_ - cx_) / NBW_[0], (zs_ - cz_) / NBW_[2])
                    inner_low = (s_ * (xs_ - cx_) < 0) & (zs_ < cz_ - 0.3 * NBW_[2])
                    c_line = np.exp(-((u_ - 1.02) / 0.12) ** 2) * ~inner_low * yfade
                    if NOSE_PAINT4:
                        # (fifteenth pass) only the wing's outer side and the outer part of its top: the sheet draws one
                        # outline round the nose, not a ring round each wing (the ring read as a separate lobe)
                        c_line = np.exp(-((u_ - 1.0) / 0.06) ** 2) * ~inner_low * yfade * smooth01(-0.35, 0.1, s_ * (xs_ - cx_) / NBW_[0]) * 1.4
                    tint(np.clip(c_line, 0, 1) * head * P3, (0.5, 0.33, 0.27), 0.65 if NOSE_PAINT4 else 0.4)
                    # the nostril: a comma lying across between ball and wing, its outer end higher and rounder
                    t_ = np.clip((s_ * xs_ - NB3_NOST[0]) / NB3_NOST[2], -1.0, 1.0)
                    zc_ = float(tip[2]) - NB3_NOST[1] + 0.0018 * t_ ** 2 * np.sign(t_) + 0.0004
                    half = NB3_NOST[3] * (0.55 + 0.45 * (t_ + 1.0) / 2.0)
                    # (an egg in the front view: round at its outer end, narrowing inward; soft-edged but small)
                    e_ = np.hypot((s_ * xs_ - NB3_NOST[0]) / NB3_NOST[2], (zs_ - zc_) / half)
                    tint(smooth01(1.0, 0.65, e_) * head * yfade * P3, (0.43, 0.28, 0.22), 0.8)
                under_ = np.exp(-((zs_ - (float(tip[2]) - NBB[4] - NBB[2] * 0.9)) / 0.0018) ** 2) * np.exp(-(xs_ / (NBB[0] * 0.8)) ** 2)
                mult(under_ * fwd_ * head * 0.5 * P3, (0.8, 0.66, 0.6))
                if NOSE_PAINT4:
                    # (fifteenth pass, nose_paint4) the sheet's front: the lower nose (the ball's lower half and both
                    # wings) one darker warm tan-brown mass (sheet: wings and lower ball the cheek times about
                    # (0.87 0.82 0.83)), the wings without a light middle; the bridge a pale stripe from between the eyes
                    # widening onto the ball's top, a soft shade either side of it
                    zb_ = float(tip[2]) - NBB[4]
                    lower_ = smooth01(zb_ + 0.003, zb_ - 0.004, zs_)
                    mass = (1.0 - smooth01(0.88, 1.0, nose_u)) * yfade * head
                    mult(mass * lower_ * NOSE_PAINT4, (0.92, 0.86, 0.85))
                    z_eye = float(tip[2]) + 0.032
                    ztop_ = float(tip[2]) - NBB[4] + NBB[2] * 0.6
                    t_ = np.clip((z_eye - zs_) / max(z_eye - ztop_, 1e-4), 0.0, 1.0)
                    hw_ = 0.0035 + 0.005 * t_ ** 1.5
                    along = smooth01(z_eye + 0.004, z_eye - 0.006, zs_) * smooth01(ztop_ - 0.006, ztop_ + 0.001, zs_)
                    tint(np.exp(-(xs_ / hw_) ** 2) * along * fwd_ * head * NOSE_PAINT4, (1.0, 0.93, 0.86), 0.3)
                    side_ = np.exp(-((np.abs(xs_) - (hw_ + 0.0055)) / 0.0035) ** 2) * along * head
                    mult(side_ * NOSE_PAINT4, (0.93, 0.89, 0.88))
            hi = np.exp(-(((pos - ((tip + np.array((0.0, NBB[3] - NBB[1], 0.002 - NBB[4]))) if NOSE_BALL_TO else (tip + np.array((0.0, 0.0, 0.0025))))) / np.array((0.0035 * wx ** 0.5, 0.004, 0.003))) ** 2).sum(-1))
            tint(hi * smooth01(0.6, 0.9, -nrm[..., 1]) * head * NOSE_PAINT2, (1.0, 0.93, 0.88), 0.4)
            br = np.exp(-(pos[..., 0] / 0.0035) ** 2) * smooth01(float(tip[2]) + 0.004, float(tip[2]) + 0.01, pos[..., 2]) \
                * (1.0 - smooth01(float(tip[2]) + 0.02, float(tip[2]) + 0.028, pos[..., 2])) * smooth01(0.6, 0.9, -nrm[..., 1])
            tint(br * head * NOSE_PAINT2, (1.0, 0.92, 0.86), 0.25)
    pos = pos_real
    # (ninth pass: the small shade marks at the mouth's corners read as dark specks; gone)
    # freckles over the bridge of the nose and the cheeks
    reg = np.exp(-((ac - 58.0) / 46.0) ** 2) * np.exp(-((row - 1148.0) / 20.0) ** 2) * fwd * head
    reg = np.maximum(reg, np.exp(-((ac / 26.0) ** 2 + ((row - 1140.0) / 14.0) ** 2)) * head)
    out = freckles(out, pos, reg * hit, 190, 53, r=(0.0007, 0.0014), s=(0.3, 0.6))   # (eleventh pass: from 110, smaller and fainter; the critic: "2-3x denser and slightly larger and darker")
    out = np.where(hit[..., None], np.nan_to_num(out), np.nan_to_num(rgb))
    return np.clip(out, 0, 1)


def rule_face(M, face_uv, face, joints):
    """The face picture: the sheet's painted face (toned to the base) kept on the front of his face, faded into
    rule paint over his scalp, the back of his head, his ears and his neck."""
    P = np.array(M.P)
    pos, nrm, hit, fid = texel_geometry(M, face_uv, "face", P, normals_of(P, M.tris()))
    # (seventh pass: some seam texels came back hit with no position (NaN), and the neck tone step turned them into
    # black lines down his head: they are left out, and the padding fills them)
    bad = ~(np.isfinite(pos).all(-1) & np.isfinite(nrm).all(-1))
    hit = hit & ~bad
    pos = np.nan_to_num(pos)
    nrm = np.nan_to_num(nrm)
    fam = np.array([part_family(p) for p in M.fpart] + ["none"])[fid]
    ff = -nrm[..., 1]
    z = pos[..., 2]
    head = hit & (fam == "head")
    core = head & (ff > 0.7) & (z < float(hz(1000))) & (z > float(hz(1160)))
    med = np.median(face[core], axis=0)
    gain = np.clip(SKIN_BASE / np.maximum(med, 1e-3), 0.8, 1.3)
    # (the face's broad tone divided out and the base put in its place, as the captain's even_tone: only the painting's
    # local marks are kept (brows, lids, freckles, the nose's tip, the smile), so the face meets the rule paint with no
    # step in colour; the cheeks keep a little of their warmth)
    cell = 32
    nn_ = face.shape[0] // cell
    w_ = head.astype(float)
    s_ = (face * w_[..., None]).reshape(nn_, cell, nn_, cell, 3).sum((1, 3))
    sw_ = w_.reshape(nn_, cell, nn_, cell).sum((1, 3))
    low = fill_out(s_ / np.maximum(sw_, 1e-6)[..., None], sw_ > cell * 2, 32)
    up = np.repeat(np.repeat(low, cell, 0), cell, 1)
    up = blur(up, 14)
    detail = np.clip(face / np.maximum(up, 1e-3), 0.4, 1.12)
    # (faint marks, the sheet's drawn wrinkles and shading lines, let go; strong ones, brows, lashes, freckles, kept)
    dd = detail - 1.0
    detail = 1.0 + dd * smooth01(0.07, 0.2, np.abs(dd).max(-1))[..., None]
    warm = np.clip(up / np.maximum(med, 1e-3), 0.9, 1.1) ** 0.5
    toned = np.clip(SKIN_BASE * detail * warm, 0, 1)
    rule = rule_paint(M, face_uv, "face", pos, nrm, hit, fam, joints)
    if FACE_BY_RULE:
        out = face_features(M, rule, pos, nrm, hit, fam)
        print("BOY rule face: painted by rule (features drawn on his own landmarks; nothing projected from the sheet)")
        return out, pos, hit
    wf = head * smooth01(0.35, 0.62, ff) * (1.0 - smooth01(float(hz(985)), float(hz(945)), z)) * smooth01(float(hz(1335)), float(hz(1300)), z)
    wf = blur(wf, 3) * head
    out = toned * wf[..., None] + rule * (1.0 - wf[..., None])
    print("BOY rule face: the sheet's face toned by %s; %d texels kept from it" % (np.round(gain, 3), int((wf > 0.5).sum())))
    return out, pos, hit


FACE_POLISH = "--no-face-polish" not in ARGS
CROWN_SMOOTH = int(arg("--crown-smooth", "14"))
BROW_RIDGE = float(arg("--brow-ridge", "0.0012"))


def face_polish(M):
    """(ninth pass; in grey the crown read faceted and a little egg-like, and the brow flat) The scalp above the brow's
    row (and behind the ears' front) smoothed by Taubin rounds, which round the facets without shrinking it, faded in over
    a band so the brow, the ears and the face below do not move; then a small brow ridge: the skin over each brow brought
    forward on a soft field, most over the middle of each brow, none between them."""
    P = np.array(M.P)
    fams = np.array([part_family(p) for p in M.part])
    head = fams == "head"
    z = P[:, 2]
    z0, z1 = float(hz(1015)), float(hz(985))
    w = head * smooth01(z0, z1, z)
    if CROWN_SMOOTH > 0:
        sel = w > 0.02
        before = P.copy()
        taubin(M, sel, rounds=CROWN_SMOOTH)
        P = np.array(M.P)
        P = before + (P - before) * w[:, None]
    col = P[:, 0] / HS
    ac = np.abs(col)
    row = hrow(P[:, 2])
    front = P[:, 1] < -0.03
    ridge = np.exp(-((row - 1047.0) / 11.0) ** 2) * np.exp(-((ac - 72.0) / 34.0) ** 2) * front * head
    P[:, 1] -= BROW_RIDGE * ridge
    # (for the face rig) the lips' meeting edge made one clean line: its points beyond the straight middle, which
    # zigzag between the lips' two rows toward the corners, drawn most of the way onto the seam's smoothed line, which
    # is where face_features paints the mouth
    mk = M.tag.get("head_marks")
    M.P = [p for p in P]
    seam = lip_seam(M, mk) if mk else None
    if seam is not None:
        x, zq, ids = seam
        zs = seam_smooth(x, zq)
        for i, v in enumerate(ids):
            if abs(x[i]) > 0.012:
                P[v][2] += (zs[i] - P[v][2]) * 0.85
    M.P = [p for p in P]
    n, _ = folded(P, M.faces)
    print("BOY face polish: crown smoothed (%d rounds over %d points), brow ridge %.1f mm; %d folded" % (
        CROWN_SMOOTH, int((w > 0.02).sum()), 1000 * BROW_RIDGE, n))


NAPE_POLISH = "--no-nape-polish" not in ARGS
NAPE_IN = float(arg("--nape-in", "0.005"))       # metres the nape is drawn forward under the skull's back
THROAT_IN = float(arg("--throat-in", "0.004"))   # metres the throat under the jaw is drawn back
NAPE_SMOOTH = int(arg("--nape-smooth", "10"))
CROWN_DOME = float(arg("--crown-dome", "0.6"))   # share of the way the cranium is drawn onto its ellipsoid
DOME_ROW = float(arg("--dome-row", "985"))         # the ellipsoid's middle (head-sheet row): between the brows and the crown
DOME_GROW = float(arg("--dome-grow", "0.025"))


def nape_polish(M):
    """(tenth pass; the critic: "from behind, the neck is a wide funnel with vertical ridges (two tendon-like fins)
    running up into the skull ... no plane under the jaw") The back of the neck and the skull's base smoothed by Taubin
    rounds (the fins were where the head's open edge met the neck's rings), the nape drawn forward under the occiput so
    the skull overhangs it, and the throat under the chin drawn back so a plane under the jaw meets the neck at an
    angle. Soft fields; the face, ears and shoulders do not move."""
    P = np.array(M.P)
    fams = np.array([part_family(p) for p in M.part])
    ok = np.isin(fams, ("head", "neck"))
    z = P[:, 2]
    zc = float(hz(1330.0))              # below the chin: the neck
    z_skull = float(hz(1215.0))         # the skull's base at his back
    z_low = NECK_Z - 0.025
    cy = float(np.median(P[ok & (z > z_skull), 1]))
    back = smooth01(cy - 0.01, cy + 0.03, P[:, 1])
    band = smooth01(z_low, z_low + 0.02, z) * (1.0 - smooth01(z_skull, z_skull + 0.025, z))
    w = ok * back * band
    if NAPE_SMOOTH > 0:
        before = P.copy()
        taubin(M, w > 0.02, rounds=NAPE_SMOOTH)
        P = np.array(M.P)
        P = before + (P - before) * w[:, None]
    # the nape forward, most just under the skull, fading down the neck
    under = np.exp(-((z - (z_skull - 0.03)) / 0.03) ** 2) * ok * back * (z < z_skull + 0.005)
    P[:, 1] -= NAPE_IN * under
    # the throat back: the front of the neck between the chin's underside and the neck's middle
    front = smooth01(0.0, -0.025, P[:, 1] - cy)
    throat = np.exp(-((z - (zc + 0.008)) / 0.022) ** 2) * ok * front * np.exp(-(P[:, 0] / 0.035) ** 2)
    P[:, 1] += THROAT_IN * throat
    # (the critic: "a tall, narrow bullet with a flattish, faceted crown"; the sheet's bald front and back draw a ball)
    # The cranium above the brows drawn toward the ellipsoid through its own extents: the flat top and the square
    # corners at the temples (which stood outside the sheet's outline) rounded; the face and the ears do not move.
    if CROWN_DOME > 0:
        cran = (fams == "head") & (z > float(hz(1010.0)))
        c = np.array((0.0, float((P[cran, 1].max() + P[cran, 1].min()) / 2), float(hz(DOME_ROW))))
        R = np.array((float(np.abs(P[cran, 0]).max()), float((P[cran, 1].max() - P[cran, 1].min()) / 2), float(P[cran, 2].max() - c[2])))
        d = (P - c) / R
        r = np.linalg.norm(d, axis=1)
        wd = (fams == "head") * smooth01(float(hz(1025.0)), float(hz(965.0)), z) * CROWN_DOME
        P = P + (c + d / np.maximum(r, 1e-6)[:, None] * R - P) * wd[:, None] * (r > 0.3)[:, None]
        if HEAD2 and DOME_GROW > 0:
            # (eleventh pass: the bald front and side views' outlines stood 6 to 8 sheet pixels beyond the crown and
            # the back of the skull) the cranium grown outward from its middle, most at the top and back, not the brow
            g = (fams == "head") * smooth01(float(hz(1040.0)), float(hz(960.0)), z) * smooth01(c[1] - 0.05, c[1] + 0.01, P[:, 1])
            P = P + (P - c) * (DOME_GROW * g)[:, None]
    M.P = [p for p in P]
    n, _ = folded(P, M.faces)
    print("BOY nape polish: %d points smoothed, nape %.1f mm in, throat %.1f mm back; %d folded" % (
        int((w > 0.02).sum()), 1000 * NAPE_IN * float(under.max()), 1000 * THROAT_IN * float(throat.max()), n))


# ------------------------------------------------------------------------------------------------------------------
# (twelfth pass) The late adjustments: small named moves on the finished head (after its eyes are opened and it is
# polished), appended in order, each with its own switch and amount (0 turns it off). Nothing before them is changed.
# Each was kept only if its before/after pair moved him toward concept_boy_head2.jpg.
# ------------------------------------------------------------------------------------------------------------------
EYE_GROW = float(arg("--eye-grow", "0.0"))      # 1. eyes_bigger: the lids' opening and the skin round it spread out from each eye's middle by this share
EYE_SEAT = float(arg("--eye-seat", "0.0015"))      # 1. eyes_bigger: the ball and its lids set back into the head (metres), the cheek and brow round them left
LASH_ON_LID = float(arg("--lash-on-lid", "1")) > 0   # 2. lash_on_lid: the lid's paint (lash, crease, lower lid) on the mesh's own opening edge
SMILE_PAINT = float(arg("--smile-paint", "0.25"))   # 3. smile: the painted mouth as the sheet's broad closed smile (its amount scales the corners' rise)
EYE_PUPIL = float(arg("--pupil", "0.5"))        # 1. the pupil's radius as a share of the iris's (the sheet's: about half)
BROW_WARM = float(arg("--brow-warm", "1"))      # 4. brows: thicker and warmer by this share
NOSE_PAINT = float(arg("--nose-paint", "1"))    # 5. nose: the nostrils' shading painted
NOSE_UP = float(arg("--nose-up", "0.0012"))          # 5. nose: the tip lifted (metres)
EAR_UP = float(arg("--ear-up", "0.008"))            # 7. ears: raised (metres)
EAR_LATE_SIZE = float(arg("--ear-late-size", "1.05"))   # 7. ears: sized about their root
EAR_LATE_SMOOTH = int(arg("--ear-late-smooth", "6"))   # 7. ears: Taubin rounds over the ear (its outline rounded)
EAR_TURN = float(arg("--ear-turn", "15"))        # 7. ears: degrees turned about the upright at the root, the bowl toward the front
NECK_RIDGE = int(arg("--neck-ridge-off", "30"))  # 8. neck_ridge_off: Taubin rounds over the back of the neck
SKIN_ROSE = float(arg("--skin-rose", "1"))      # 9. skin: rosier ears, nose tip, cheeks, knees, knuckles; the palm's crease shade less
NOSE_SPREAD = float(arg("--nose-wings", "0.0"))   # (thirteenth pass) 1. nose_wings: share the nose's lower half is spread sideways
NOSE_WINGS_AT = (float(arg("--nose-wings-back", "0.006")), float(arg("--nose-wings-down", "0.003")))   # the field's middle behind and below the tip
NOSE_WINGS_REACH = tuple(float(v) for v in arg("--nose-wings-reach", "0.013,0.012,0.010").split(","))   # its reach across, back, up
NOSE_BRIDGE_SOFT = float(arg("--nose-bridge", "0.0"))   # metres the bridge's ridge is eased back
NOSE_PAINT2 = float(arg("--nose-paint2", "1"))   # (thirteenth pass) the nose's paint for the wider nose: rosy ball, wing shade, tip highlight
SMILE_RISE = float(arg("--smile-rise", "0.0"))     # (thirteenth pass) 2. smile_form: metres the corners of the lips rise
SMILE_TUCK = float(arg("--smile-tuck", "0.0"))     # metres the corners are tucked back
SMILE_APPLE = float(arg("--smile-apple", "0.0"))   # metres the cheeks above the corners swell forward
SMILE_DIMPLE = float(arg("--smile-dimple", "0.0")) # metres the small dent at each corner goes in
SMILE_REACH = float(arg("--smile-reach", "0.009")) # metres above and below the seam the lips move whole
NOSE_SUB = int(arg("--nose-sub", "1"))          # (thirteenth pass) times the nose's faces are split in four (0: off)
NOSE_SUB_REACH = tuple(float(v) for v in arg("--nose-sub-reach", "0.032,0.026,0.024").split(","))   # the nose's box (an ellipsoid round the tip): across, back, up
NOSE_SUB_AT = tuple(float(v) for v in arg("--nose-sub-at", "0.01,0.01").split(","))   # the box's middle behind and below the tip
NOSE_BALL_TO = float(arg("--nose-ball-to", "1.0"))   # (thirteenth pass) nose_ball: share of the way onto the ball-and-wings shape
NB_BALL = tuple(float(v) for v in arg("--nb-ball", "0.013,0.009,0.0135,0.009,0.0065").split(","))   # the tip's ball: radii across, back, up; its middle behind and below the tip
NB_WING = tuple(float(v) for v in arg("--nb-wing", "0.0095,0.012,0.009,0.016,0.015,0.014").split(","))   # each wing: radii; out, behind and below the tip
NB_REGION = tuple(float(v) for v in arg("--nb-region", "0.034,0.026,0.024,0.01,0.024").split(","))   # the field: radii; its middle below the tip; where it ends below the tip
NB_CLAMP = float(arg("--nb-clamp", "0.007"))       # metres the most a point is moved
NB_NOSTRIL = float(arg("--nb-nostril", "0.002"))     # metres the nostrils are pressed up
NB_SMOOTH = int(arg("--nb-smooth", "2"))         # Taubin rounds over the nose_ball field
NB_OUT_BELOW = float(arg("--nb-out-below", "0.012"))   # metres under the tip below which nose_ball only moves points out (0: off)
NB_GROOVE = float(arg("--nb-groove", "0"))       # metres the crease round each wing is pressed in
NOSE_LINE = float(arg("--nose-line", "1"))       # (thirteenth pass) paint: tan over the ball, a warm-brown line round each wing
NB_NOST = tuple(float(v) for v in arg("--nb-nost", "0.0075,0.009,0.017").split(","))   # the nostrils: out, behind and below the tip
NOSE_TAN = float(arg("--nose-tan", "1"))         # (thirteenth pass) the nose's pink turned to the sheet's tan-rose; nostrils seen from the front
# (fourteenth pass) nose_ball2: the ball narrower, the wings their own lobes out and back of it, the underside carved to a
# floor that meets the lip at a corner; all in metres from the nose mark (the tip as built): across, behind, below
NB_MODE = int(arg("--nb-mode", "3"))             # 1: nose_ball as in the thirteenth pass; 2: nose_ball2; 3: nose_ball3 (kept)
NB2_BALL = tuple(float(v) for v in arg("--nb2-ball", "0.0105,0.009,0.0115,0.0056,0.0095").split(","))   # radii across, back, up; middle behind and below
NB2_WING = tuple(float(v) for v in arg("--nb2-wing", "0.0075,0.006,0.009,0.0155,0.008,0.0135").split(","))   # radii; middle out, behind, below
NB3_EDGE = float(arg("--nb3-edge", "0.6"))      # nose_ball3: share of the outline (seen from the front) where the height field starts to fade out
NB3_DSMOOTH = int(arg("--nb3-dsmooth", "4"))    # nose_ball3: rounds the moves are averaged with their neighbours
NOSE_PAINT3 = float(arg("--nose-paint3", "1"))   # (fourteenth pass) with nose_ball2/3: the sheet's tan-brown, wing outlines, crisp nostril commas
NB3_NOST = tuple(float(v) for v in arg("--nb3-nost", "0.0078,0.0165,0.0045,0.0015").split(","))   # the painted nostrils: out, below the mark, half length, half height
NB2_K = float(arg("--nb2-k", "0.002"))          # metres of the smooth union (the crease between ball and wing)
NB2_PLANE = tuple(float(v) for v in arg("--nb2-plane", "0.017,0.5,0.010").split(","))   # the face behind the nose: metres behind, its rise per metre out, from how far out
NB_PROBE = int(arg("--nb-probe", "0"))          # (fourteenth pass) print the nose's depth table before and after nose_ball
WING_SUB = int(arg("--wing-sub", "0"))          # (fourteenth pass) wing_sub: the wings' faces split in four once more (0: off)
WING_SUB_AT = tuple(float(v) for v in arg("--wing-sub-at", "0.015,0.012,0.011").split(","))   # each box's middle: out, behind, below the tip
WING_SUB_REACH = tuple(float(v) for v in arg("--wing-sub-reach", "0.011,0.013,0.011").split(","))   # its reach across, back, up
# (fifteenth pass) nose_scale: measured as shares of the pupils' spacing (IPD) on the sheet's shaved front and side and on a
# Godot front render: the wings 0.51 IPD across on the sheet, 0.44 on the model; the nose's base 0.64 below the pupils on
# the sheet, 0.56 on the model (the mouth 0.82 on the sheet, 0.73 on the model: the upper lip, base to mouth, 0.18 and 0.17)
NOSE_SCALE = tuple(float(v) for v in arg("--nose-scale", "1.3,1,1.35").split(","))   # across, forward, down: about the bridge between the eyes
NS_REACH = tuple(float(v) for v in arg("--ns-reach", "0.024,0.042").split(","))   # metres out from his middle where the scale starts to fade, and is gone
NS_TOP = tuple(float(v) for v in arg("--ns-top", "0.004,0.018").split(","))   # metres under the pupils where it starts and is full (the bridge's top left)
NOSE_PAINT4 = float(arg("--nose-paint4", "1"))   # (fifteenth pass) the lower nose one tan-brown mass, one outline, the bridge's pale stripe
NP4_WING = tuple(float(v) for v in arg("--np4-wing", "0.006,0.011,0.012,0.011").split(","))   # the painted wing with nose_paint4: half width, half height, out, below the mark (before nose_scale)
NS_ZPIV = arg("--ns-zpiv", "tip")   # the down scale about the pupils' row ("eyes") or about the tip's height ("tip")
LATE_ADJUST = []


def nose_scale_move(T, Q):
    """The nose_scale displacement at (pre-scale) points Q, from the tag T."""
    piv, S, zb, zm, ty = T["pivot"], np.array(T["S"]), T["z_base"], T["z_mouth"], T["tip_y"]
    ax = np.abs(Q[..., 0])
    w = (1.0 - smooth01(NS_REACH[0], NS_REACH[1], ax))
    w = w * smooth01(piv[2] - NS_TOP[0], piv[2] - NS_TOP[1], Q[..., 2])
    w = w * smooth01(zm + 0.003, zb + 0.001, Q[..., 2])
    w = w * smooth01(ty + 0.04, ty + 0.03, Q[..., 1])
    d = Q - piv
    if NS_ZPIV == "tip":
        # (the down scale about the tip's height: the tip stays where the sheet has it, the ball and its underside, the
        # wings and the nostrils below it stretched down; above the tip nothing moves down (a soft corner, 2 mm))
        dz = Q[..., 2] - T["tip_z"]
        d[..., 2] = 0.5 * (dz - np.sqrt(dz * dz + 0.002 ** 2))
    return d * (S - 1.0) * w[..., None]


def nose_unscale(M, pos):
    """Points on the scaled nose taken back to where they were before nose_scale (a few fixed-point rounds), so paint
    placed by the nose's pre-scale measures lands on the scaled forms."""
    T = M.tag.get("nose_scale")
    if not T:
        return pos
    q = np.array(pos, float)
    for _ in range(8):
        q = pos - nose_scale_move(T, q)
    return q


def nose_scale(M, eyes):
    P = np.array(M.P)
    mk = M.tag["head_marks"]
    fams = np.array([part_family(p) for p in M.part])
    head = fams == "head"
    zr = float(np.mean([C_[2] for C_, s_ in eyes]))
    tip = P[mk["nose"]]
    band = head & (np.abs(P[:, 0]) < 0.008) & (np.abs(P[:, 2] - zr) < 0.008) & (P[:, 1] < tip[1] + 0.05)
    yr = float(P[band, 1].min()) if band.any() else float(tip[1]) + 0.02
    print("BOY late nose_scale: the pupils' row z %.1f mm, tip z %.1f, %d points at the bridge" % (1000 * zr, 1000 * tip[2], int(band.sum())))
    T = {"pivot": np.array((0.0, yr, zr)), "S": NOSE_SCALE, "z_base": float(P[mk["nose_base"], 2]),
         "z_mouth": float(P[mk["mouth"], 2]), "tip_y": float(tip[1])}
    # (the tip's height: the frontmost point of his middle, not the nose mark, which sits a few mm above it)
    mid_ = head & (np.abs(P[:, 0]) < 0.004) & (P[:, 2] < zr - 0.01) & (P[:, 2] > T["z_base"])
    T["tip_z"] = float(P[mid_][np.argmin(P[mid_, 1]), 2]) if mid_.any() else float(tip[2])
    guard = np.zeros(len(P), bool)
    guard[list(M.tag.get("lid_hold", []))] = True
    D = nose_scale_move(T, P) * (head & ~guard)[:, None]
    P2 = P + D
    M.P = [p for p in P2]
    M.tag["nose_scale"] = T
    n, _ = folded(P2, M.faces)
    LATE_ADJUST.append("nose_scale %s" % (NOSE_SCALE,))
    print("BOY late nose_scale: x%.2f y%.2f z%.2f about (0, %.1f, %.1f) mm; tip moved %.1f mm, base %.1f mm, most %.1f mm; %d folded" % (
        *NOSE_SCALE, 1000 * yr, 1000 * zr, 1000 * np.linalg.norm(D[mk["nose"]]), 1000 * np.linalg.norm(D[mk["nose_base"]]),
        1000 * np.linalg.norm(D, axis=1).max(), n))


def nose_profile(P, mk, head, tag):
    """(thirteenth pass, a measure) The nose's width: at three heights (the tip, between tip and base, the base) the
    face's front-most point in 2 mm columns out from his middle, and where it stands 2 mm proud of the cheek beside it."""
    tip, base = P[mk["nose"]], P[mk["nose_base"]]
    out = []
    for nm, z in (("tip", tip[2]), ("mid", 0.5 * (tip[2] + base[2])), ("base", base[2] + 0.001)):
        band = head & (np.abs(P[:, 2] - z) < 0.0015) & (P[:, 1] < tip[1] + 0.03)
        ys = []
        for k in range(16):
            sel = band & (np.abs(np.abs(P[:, 0]) - (k * 0.002 + 0.001)) < 0.001)
            ys.append(float(P[sel, 1].min()) if sel.any() else np.nan)
        ys = np.array(ys)
        cheek = np.nanmin(ys[10:15]) if np.isfinite(ys[10:15]).any() else np.nan
        proud = np.where(np.isfinite(ys) & (ys < cheek - 0.002))[0]
        wid = 2 * (proud.max() * 0.002 + 0.002) if len(proud) else 0.0
        out.append("%s z %.1f: width %.0f mm (%s)" % (nm, 1000 * z, 1000 * wid, " ".join("%.0f" % (1000 * (v - tip[1])) if np.isfinite(v) else "-" for v in ys)))
    print("BOY nose %s: tip at (%.1f %.1f %.1f) mm, base z %.1f; %s" % (tag, *(1000 * tip), 1000 * base[2], "; ".join(out)))


def nose_table(P, faces, tip, tag):
    """(fourteenth pass, a measure, --nb-probe 1) the nose's depth from the front by ray casts, in mm from the nose mark:
    rows below the tip (every 2 mm), columns out from his middle (every 2 mm); each value mm behind the tip."""
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromPolygons([Vector(p) for p in P], [list(f) for f in faces])
    print("BOY nosetable %s: mark at (%.1f %.1f %.1f) mm; rows mm below, columns mm out" % (tag, *(1000 * tip)))
    for dz in range(-6, 26, 2):
        row = []
        for x in range(0, 28, 2):
            hit = bvh.ray_cast(Vector((x / 1000.0, tip[1] - 0.05, tip[2] - dz / 1000.0)), Vector((0, 1, 0)), 0.2)
            row.append("%5.1f" % ((hit[0].y - tip[1]) * 1000) if hit[0] else "    -")
        print("BOY nosetable %s %3d %s" % (tag, dz, " ".join(row)))


def eye_margins(M, eyes):
    """Each eye's lid margin (the opening's edge) as open_eyes2 left it: its points in order from the inner corner,
    read from the lid_hold tag (each eye's margin loop, then its roll ring, the same length)."""
    lh = list(M.tag.get("lid_hold", []))
    n = len(lh) // (2 * max(len(eyes), 1))
    return [(lh[2 * k * n:(2 * k + 1) * n], lh[(2 * k + 1) * n:(2 * k + 2) * n]) for k in range(len(eyes))]


def nose_subdivide(M, face_uv, weights, levels=1, boxes=None, name="nose_sub"):
    """(thirteenth pass, nose_sub) ONE local subdivision of the nose's faces (the frozen head had 14 points within 15 mm
    of the tip: too few for a ball, wings and nostrils). Each face whose points all lie in the nose's box is split in four
    (a quad into four quads, a triangle into four triangles); each new point on an edge sits on a curve through its two
    ends that follows their normals (cubic Hermite: rounded, not flat), so the surface keeps its shape. A face outside the
    box that shares a split edge gets the edge's new point and a middle point of its own, fanned from that middle, so
    nothing cracks; its shape does not change. Old points do not move; UVs and weights are carried (averaged)."""
    mk = M.tag["head_marks"]
    for _ in range(levels):
        P = np.array(M.P)
        N = normals_of(P, M.tris())
        tip = P[mk["nose"]]
        if boxes is None:
            c = tip + np.array((0.0, NOSE_SUB_AT[0], -NOSE_SUB_AT[1]))
            R = np.array(NOSE_SUB_REACH)
            inside = (((P - c) / R) ** 2).sum(1) < 1.0
        else:
            # (fourteenth pass, wing_sub) ellipsoids given as (offset from the tip, reach)
            inside = np.zeros(len(P), bool)
            for off_, R_ in boxes:
                inside |= (((P - (tip + np.array(off_))) / np.array(R_)) ** 2).sum(1) < 1.0
        guard = set(v for v in M.tag.get("lid_hold", []))
        sel = [fi for fi, (f, fp) in enumerate(zip(M.faces, M.fpart)) if part_family(fp) == "head" and fi in face_uv
               and all(inside[v] and v not in guard for v in f)]
        sel_set = set(sel)
        mids = {}

        def mid(a, b):
            k = (min(a, b), max(a, b))
            if k not in mids:
                pa, pb = P[a], P[b]
                d = pb - pa
                L = float(np.linalg.norm(d))
                ta = d - N[a] * float(d @ N[a])
                tb = d - N[b] * float(d @ N[b])
                ta = ta / max(np.linalg.norm(ta), 1e-9) * L
                tb = tb / max(np.linalg.norm(tb), 1e-9) * L
                q = 0.5 * (pa + pb) + (ta - tb) / 8.0
                M.P.append(q)
                M.part.append("head")
                wa, wb = weights[a], weights[b]
                weights.append({bn: 0.5 * wa.get(bn, 0.0) + 0.5 * wb.get(bn, 0.0) for bn in set(wa) | set(wb)})
                mids[k] = len(M.P) - 1
            return mids[k]

        def new_point(q, srcs):
            M.P.append(np.array(q, float))
            M.part.append("head")
            w = {}
            for s_ in srcs:
                for bn, x in weights[s_].items():
                    w[bn] = w.get(bn, 0.0) + x / len(srcs)
            weights.append(w)
            return len(M.P) - 1
        n0 = len(M.faces)
        for fi in sel:
            f = M.faces[fi]
            pic, uv = face_uv[fi]
            uv = [np.array(u_, float) for u_ in uv]
            n = len(f)
            em = [mid(f[i], f[(i + 1) % n]) for i in range(n)]
            emu = [0.5 * (uv[i] + uv[(i + 1) % n]) for i in range(n)]
            if n == 4:
                cq = 0.5 * sum(np.array(M.P[m_]) for m_ in em) - 0.25 * sum(P[v] for v in f)
                cv = new_point(cq, list(f))
                cu = sum(uv) / 4.0
                kids = [([f[i], em[i], cv, em[i - 1]], [uv[i], emu[i], cu, emu[i - 1]]) for i in range(4)]
            else:
                kids = [([f[i], em[i], em[i - 1]], [uv[i], emu[i], emu[i - 1]]) for i in range(n)] + [(em, emu)]
            for j, (kf, ku) in enumerate(kids):
                if j == 0:
                    M.faces[fi] = kf
                    face_uv[fi] = (pic, [tuple(u_) for u_ in ku])
                else:
                    M.face(kf, M.fpart[fi])
                    face_uv[len(M.faces) - 1] = (pic, [tuple(u_) for u_ in ku])
        # the faces round the box that share a split edge: the edge's point put in, fanned from a middle point
        ring = 0
        for fi in range(n0):
            if fi in sel_set or fi not in face_uv:
                continue
            f = M.faces[fi]
            n = len(f)
            hits = [mids.get((min(f[i], f[(i + 1) % n]), max(f[i], f[(i + 1) % n]))) for i in range(n)]
            if not any(h is not None for h in hits):
                continue
            ring += 1
            pic, uv = face_uv[fi]
            uv = [np.array(u_, float) for u_ in uv]
            poly, pu = [], []
            for i in range(n):
                poly.append(f[i])
                pu.append(uv[i])
                if hits[i] is not None:
                    poly.append(hits[i])
                    pu.append(0.5 * (uv[i] + uv[(i + 1) % n]))
            cv = new_point(np.mean([M.P[v] for v in f], axis=0), list(f))
            cu = sum(uv) / n
            m_ = len(poly)
            for j in range(m_):
                kf = [poly[j], poly[(j + 1) % m_], cv]
                ku = [pu[j], pu[(j + 1) % m_], cu]
                if j == 0:
                    M.faces[fi] = kf
                    face_uv[fi] = (pic, [tuple(u_) for u_ in ku])
                else:
                    M.face(kf, M.fpart[fi])
                    face_uv[len(M.faces) - 1] = (pic, [tuple(u_) for u_ in ku])
        Pn = np.array(M.P)
        n_, _ = folded(Pn, M.faces)
        print("BOY late %s: %d faces split in four, %d round them fanned, %d new points (%d within 15 mm of the tip now); %d folded" % (
            name, len(sel), ring, len(M.P) - len(P), int((np.linalg.norm(Pn - tip, axis=1) < 0.015).sum()), n_))
    LATE_ADJUST.append("%s %d" % (name, levels))


def late_adjust(M, eyes, face_uv=None, weights=None):
    if NOSE_SUB and face_uv is not None:
        nose_subdivide(M, face_uv, weights, NOSE_SUB)
    if WING_SUB and face_uv is not None:
        # (fourteenth pass, wing_sub) once more, only the wings and the faces between each wing and the cheek
        boxes = [((s_ * WING_SUB_AT[0], WING_SUB_AT[1], -WING_SUB_AT[2]), WING_SUB_REACH) for s_ in (1.0, -1.0)]
        nose_subdivide(M, face_uv, weights, 1, boxes=boxes, name="wing_sub")
    P = np.array(M.P)
    fams = np.array([part_family(p) for p in M.part])
    head = fams == "head"
    marg = eye_margins(M, eyes)
    M.tag["eye_margins"] = marg
    # 1. eyes_bigger
    if EYE_GROW or EYE_SEAT:
        T_ = M.tris()
        N = normals_of(P, T_)
        ax, az = 37.0 * HS, 23.0 * HS          # the opening's half width and half height (the sheet's, measured)
        D = np.zeros_like(P)
        for (C, s), (loop, ring2) in zip(eyes, marg):
            dx, dz = P[:, 0] - C[0], P[:, 2] - C[2]
            e = np.hypot(dx / ax, dz / az)
            front = smooth01(C[1] + 0.004, C[1] - 0.004, P[:, 1])
            w = (1.0 - smooth01(1.2, 2.7, e)) * front * head
            # spread in the face's own surface (the normal part taken out), the lids then laid back on the ball
            d = np.stack([dx, np.zeros(len(P)), dz], 1) * (EYE_GROW * w)[:, None]
            d -= N * (d * N).sum(1)[:, None] * (e > 1.3)[:, None]
            D += d
        P2 = P + D
        for (C, s), (loop, ring2) in zip(eyes, marg):
            def by(x, z):
                k = 1.0 - ((x - C[0]) / EYE_RAD[0]) ** 2 - ((z - C[2]) / EYE_RAD[2]) ** 2
                return C[1] - EYE_RAD[1] * np.sqrt(np.maximum(k, 0.25))
            e = np.hypot((P[:, 0] - C[0]) / ax, (P[:, 2] - C[2]) / az)
            near = (e < 1.3) & head & (np.sign(P[:, 0]) == s)
            P2[near, 1] += by(P2[near, 0], P2[near, 2]) - by(P[near, 0], P[near, 2])
            # the seat: the ball and everything on it back, faded out over the lids' rings to the cheek and brow
            if EYE_SEAT:
                ws = (1.0 - smooth01(1.05, 2.0, e)) * head * (np.sign(P[:, 0]) == s) * smooth01(C[1] + 0.004, C[1] - 0.004, P[:, 1])
                P2[:, 1] += EYE_SEAT * ws
        if EYE_SEAT:
            eyes[:] = [(C + np.array((0.0, EYE_SEAT, 0.0)), s) for C, s in eyes]
        P = P2
        M.P = [p for p in P]
        n, _ = folded(P, M.faces)
        cols = [abs(P[v][0]) / HS for v in marg[0][0]]
        rows = [float(hrow(P[v][2])) for v in marg[0][0]]
        LATE_ADJUST.append("eyes_bigger %.2f, seat %.1f mm" % (EYE_GROW, 1000 * EYE_SEAT))
        print("BOY late eyes_bigger: grow %.2f, seat %.1f mm; the opening now columns %.0f to %.0f, rows %.0f to %.0f (%.0f x %.0f); %d folded" % (
            EYE_GROW, 1000 * EYE_SEAT, min(cols), max(cols), min(rows), max(rows), max(cols) - min(cols), max(rows) - min(rows), n))
    # 5. nose_up: the tip and the underside of the nose lifted, the bridge and the lip below left
    if NOSE_UP:
        tip = P[M.tag["head_marks"]["nose"]].copy()
        w = np.exp(-(np.linalg.norm((P - (tip + np.array((0.0, 0.003, -0.003)))) * np.array((0.8, 1.0, 1.0)), axis=1) / 0.0075) ** 2) * head
        P[:, 2] += NOSE_UP * w
        P[:, 1] += NOSE_UP * 0.3 * w
        n, _ = folded(P, M.faces)
        LATE_ADJUST.append("nose_up %.1f mm" % (1000 * NOSE_UP))
        print("BOY late nose_up: %.1f mm; %d folded" % (1000 * NOSE_UP, n))
    # (thirteenth pass) 1. nose_wings: the sheet's nose is a soft wide ball with round wings, about as wide as the gap
    # between the eyes; his was a narrow ridge. The nose's own points spread sideways from his middle on a soft field
    # round the nose's lower half (most at the wings, none at the bridge's top or the lip), the bridge's ridge eased back;
    # nothing raised.
    mk = M.tag["head_marks"]
    nose_profile(P, mk, head, "before")
    if NOSE_SPREAD:
        tip = P[mk["nose"]].copy()
        c = tip + np.array((0.0, NOSE_WINGS_AT[0], -NOSE_WINGS_AT[1]))
        d = (P - c) / np.array(NOSE_WINGS_REACH)
        w = np.exp(-(d ** 2).sum(1)) * head * (P[:, 1] < tip[1] + 0.022)
        P[:, 0] += NOSE_SPREAD * P[:, 0] * w
        if NOSE_BRIDGE_SOFT:
            # the bridge's ridge (his middle, from the eyes' row down to just above the tip) eased back a little
            zt, ze = float(tip[2]), float(np.mean([C_[2] for C_, s_ in eyes])) if eyes else float(tip[2]) + 0.03
            band = smooth01(zt + 0.002, zt + 0.01, P[:, 2]) * (1.0 - smooth01(ze - 0.006, ze + 0.004, P[:, 2]))
            P[:, 1] += NOSE_BRIDGE_SOFT * np.exp(-(P[:, 0] / 0.005) ** 2) * band * head * (P[:, 1] < tip[1] + 0.02)
        n, _ = folded(P, M.faces)
        LATE_ADJUST.append("nose_wings %.2f, bridge %.1f mm" % (NOSE_SPREAD, 1000 * NOSE_BRIDGE_SOFT))
        print("BOY late nose_wings: %.2f, bridge eased %.1f mm; %d folded" % (NOSE_SPREAD, 1000 * NOSE_BRIDGE_SOFT, n))
        nose_profile(P, mk, head, "after")
    # (thirteenth pass) nose_ball: the nose's lower half drawn onto the sheet's shape: a soft ball for the tip and a
    # rounder lobe for each wing behind and beside it, joined smoothly (a smooth union of three ellipsoids, sizes read
    # off concept_boy_head2.jpg's front and side), each point moved along its own normal by its distance to that shape,
    # a share of the way, on a soft field round the nose (none at the bridge's top, the cheeks or the lip). Then the
    # nostrils: the underside pressed up a little either side of the middle.
    if NOSE_BALL_TO:
        tip = P[mk["nose"]].copy()
        M.tag["nose_ball_tip"] = tip.copy()
        N = normals_of(P, M.tris())
        bc = tip + np.array((0.0, NB_BALL[3], -NB_BALL[4]))
        br = np.array(NB_BALL[:3])

        def ell(c_, r_):
            q = (P - c_) / r_
            return (np.linalg.norm(q, axis=1) - 1.0) * float(r_.min())

        def smin(a, b, k):
            h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
            return b + (a - b) * h - k * h * (1 - h)
        sd = ell(bc, br)
        wing_sd = []
        for s_ in (1.0, -1.0):
            wc = tip + np.array((s_ * NB_WING[3], NB_WING[4], -NB_WING[5]))
            sw_ = ell(wc, np.array(NB_WING[:3]))
            sd = smin(sd, sw_, 0.004)
            wing_sd.append(sw_)
        rc = tip + np.array((0.0, 0.012, -NB_REGION[3]))
        rw = np.exp(-((((P - rc) / np.array(NB_REGION[:3])) ** 2).sum(1)) ** 2) * head
        rw *= smooth01(tip[2] - NB_REGION[4] - 0.005, tip[2] - NB_REGION[4], P[:, 2]) * (P[:, 1] < tip[1] + 0.03)
        mv = np.clip(-sd, -NB_CLAMP, NB_CLAMP) * rw * NOSE_BALL_TO
        if NB_MODE in (2, 3):
            # (fourteenth pass, nose_ball2) a narrower ball and two wing lobes of their own, a crease between; every point
            # inside the shape pushed out to it; a point outside it carved in only where it stands proud of the face
            # behind the nose (a plane rising to the cheeks), never past that plane, and never above the ball's middle
            # (the bridge is left to itself)
            bc = tip + np.array((0.0, NB2_BALL[3], -NB2_BALL[4]))
            sd = ell(bc, np.array(NB2_BALL[:3]))
            wing_sd = []
            for s_ in (1.0, -1.0):
                wc = tip + np.array((s_ * NB2_WING[3], NB2_WING[4], -NB2_WING[5]))
                # (an egg: its back half as long as the 7th number says, so the wing's side runs back into the cheek)
                rb_back = NB2_WING[6] if len(NB2_WING) > 6 else NB2_WING[1]
                q = (P - wc) / np.array(NB2_WING[:3])
                q[:, 1] = np.where(P[:, 1] > wc[1], (P[:, 1] - wc[1]) / rb_back, q[:, 1])
                sw_ = (np.linalg.norm(q, axis=1) - 1.0) * float(min(NB2_WING[:3]))
                sd = smin(sd, sw_, NB2_K)
                wing_sd.append(sw_)
            plane_b = tip[1] + NB2_PLANE[0] + NB2_PLANE[1] * np.maximum(np.abs(P[:, 0]) - NB2_PLANE[2], 0.0)
            room = np.maximum(plane_b - P[:, 1], 0.0)
            below = smooth01(bc[2] + 0.002, bc[2] - 0.002, P[:, 2])
            carve = np.minimum(np.maximum(sd, 0.0), room) * below
            mv = (np.maximum(-sd, 0.0) - carve)
            mv = np.clip(mv, -NB_CLAMP, NB_CLAMP) * rw * NOSE_BALL_TO
        if NB_MODE == 3:
            # (fourteenth pass, nose_ball3) the front as a height field: within the ball's and the wings' outlines seen
            # from the front, every point that does not face down is set to the shapes' front depth (a smooth union of
            # the three: a crease between ball and wing), fading out over the outline's last share (NB3_EDGE), so a
            # wing is a rounded lobe whose side runs back into the cheek instead of a wall pushed sideways. The points
            # that face down (the underside) are carved by nose_ball2's rule (to the shapes, never past the face's plane).
            shapes = [(tip + np.array((0.0, NB2_BALL[3], -NB2_BALL[4])), np.array(NB2_BALL[:3]))]
            for s_ in (1.0, -1.0):
                shapes.append((tip + np.array((s_ * NB2_WING[3], NB2_WING[4], -NB2_WING[5])), np.array(NB2_WING[:3])))
            bt = None
            edge = np.zeros(len(P))
            for c_, r_ in shapes:
                u = np.sqrt(((P[:, 0] - c_[0]) / r_[0]) ** 2 + ((P[:, 2] - c_[2]) / r_[2]) ** 2)
                b_ = c_[1] - r_[1] * np.sqrt(np.clip(1.0 - u ** 2, 0.0, 1.0))
                b_ = np.where(u < 1.0, b_, c_[1] + 0.03)
                bt = b_ if bt is None else smin(bt, b_, NB2_K)
                edge = np.maximum(edge, smooth01(1.0, NB3_EDGE, u))
            facing = smooth01(-0.7, -0.4, N[:, 2])           # 0 where the surface faces down
            front_ok = facing * edge * rw * (P[:, 1] < tip[1] + NB2_PLANE[0] + 0.004)
            dy = np.clip(bt - P[:, 1], -NB_CLAMP, NB_CLAMP)
            # the underside: nose_ball2's carve (its mv) along the normal, where the height field does not reach
            mv = mv * (1.0 - np.clip(front_ok * 2.0, 0.0, 1.0))
            D3 = N * mv[:, None]
            D3[:, 1] += dy * front_ok * NOSE_BALL_TO
            # the moves themselves smoothed over the surface (each point's move averaged with its neighbours', a few
            # rounds, inside the field only), so neighbours never move apart enough to fold
            E_ = np.array(sorted({(min(a, b), max(a, b)) for f in M.faces for a, b in zip(f, list(f[1:]) + [f[0]])}))
            live = rw > 0.01
            for _ in range(NB3_DSMOOTH):
                acc = np.zeros_like(D3)
                cnt = np.zeros(len(P))
                np.add.at(acc, E_[:, 0], D3[E_[:, 1]])
                np.add.at(acc, E_[:, 1], D3[E_[:, 0]])
                np.add.at(cnt, E_[:, 0], 1.0)
                np.add.at(cnt, E_[:, 1], 1.0)
                avg = acc / np.maximum(cnt, 1.0)[:, None]
                D3 = np.where(live[:, None], 0.5 * D3 + 0.5 * avg, D3)
            mv = np.zeros(len(P))
            M.tag["_nb_before"] = P.copy()
        if NB_OUT_BELOW and NB_MODE == 1:
            # (below this far under the tip the shape only adds: the lip and the cheeks under the wings are not drawn in)
            mv = np.where(P[:, 2] < tip[2] - NB_OUT_BELOW, np.maximum(mv, 0.0), mv)
        before = P.copy()
        P = P + N * mv[:, None]
        if NB_MODE == 3:
            P = P + D3
        if NB_GROOVE:
            # the wing's crease: a soft groove just outside each wing's lobe, where the sheet draws the wing's outline
            # (on the cheek's side of the wing and above it, not under the nose)
            for s_, sw_ in zip((1.0, -1.0), wing_sd):
                g_ = np.exp(-((sw_ - 0.0015) / 0.0015) ** 2) * (s_ * P[:, 0] > NB_WING[3] * 0.6) * head * (rw > 0.02)
                P = P - N * (NB_GROOVE * g_)[:, None]
        if NB_NOSTRIL:
            for s_ in (1.0, -1.0):
                nc = tip + np.array((s_ * NB_NOST[0], NB_NOST[1], -NB_NOST[2]))
                dn = np.linalg.norm((P - nc) / np.array((0.0045, 0.0055, 0.004)), axis=1)
                down = smooth01(0.2, 0.7, -N[:, 2])
                P[:, 2] += NB_NOSTRIL * np.exp(-dn ** 2) * down * head
        if NB_SMOOTH:
            # Taubin rounds over the field (most where it moved the nose), so the wings meet the cheek without a step
            M.P = [p for p in P]
            ws_ = np.clip(rw * 1.5, 0, 1) * (rw > 0.02)
            taubin(M, ws_ > 0, rounds=NB_SMOOTH, weight=ws_)
            P = np.array(M.P)
        n, _ = folded(P, M.faces)
        if NB_PROBE:
            nose_table(M.tag.get("_nb_before", before), M.faces, tip, "before")
            nose_table(P, M.faces, tip, "after")
        LATE_ADJUST.append("nose_ball %.2f, nostrils %.1f mm" % (NOSE_BALL_TO, 1000 * NB_NOSTRIL))
        print("BOY late nose_ball: %.2f of the way (most moved %.1f mm, %d points), nostrils %.1f mm; %d folded" % (
            NOSE_BALL_TO, 1000 * float(np.linalg.norm(P - before, axis=1).max()), int((np.abs(mv) > 1e-4).sum()), 1000 * NB_NOSTRIL, n))
    # (fifteenth pass) nose_scale: the whole lower nose (ball, wings, nostrils, the bridge's lower half) scaled about the
    # bridge between the eyes, toward the sheet's proportions measured as shares of the pupils' spacing; the paint follows
    # (face_features maps its points back through nose_unscale)
    if NOSE_SCALE != (1.0, 1.0, 1.0):
        M.P = [p for p in P]
        nose_scale(M, eyes)
        P = np.array(M.P)
    # (thirteenth pass) 2. smile_form: the sheet's broad closed smile from the form: the lips' meeting edge and both lips
    # round it raised toward the corners (none in the middle, most at the corners), the corners tucked back, the cheeks
    # above them swelled a little, a small soft dent at each corner. The painted line rides the seam, so it moves too.
    if SMILE_RISE or SMILE_TUCK or SMILE_APPLE or SMILE_DIMPLE:
        M.P = [p for p in P]
        seam = lip_seam(M, mk)
        if seam is not None:
            sx, sz, _ = seam
            xc = float(np.abs(sx).max())
            zs_ = np.interp(P[:, 0], sx, seam_smooth(sx, sz))
            ym = float(P[mk["mouth"], 1])
            front = smooth01(ym + 0.035, ym + 0.02, P[:, 1]) * head
            u = np.abs(P[:, 0]) / xc
            # across: zero in the middle, rising as the square to the corners, held a little past them, then let go
            f = np.minimum(u, 1.0) ** 2 * (1.0 - smooth01(1.05, 1.6, u))
            # up and down: the lips (about 9 mm each way) move whole, then fading out
            g = np.exp(-((P[:, 2] - zs_) / SMILE_REACH) ** 4)
            w = f * g * front
            before = P.copy()
            P[:, 2] += SMILE_RISE * w
            P[:, 1] += SMILE_TUCK * w * smooth01(0.5, 1.0, u)
            for s_ in (1.0, -1.0):
                ca = np.array((s_ * (xc + 0.004), ym + 0.008, float(np.interp(xc, sx, sz)) + SMILE_RISE + 0.013))
                da = (P - ca) / np.array((0.014, 0.02, 0.011))
                P[:, 1] -= SMILE_APPLE * np.exp(-(da ** 2).sum(1)) * front
                cd = np.array((s_ * (xc + 0.0025), 0.0, float(np.interp(xc, sx, sz)) + SMILE_RISE))
                dd = np.hypot((P[:, 0] - cd[0]) / 0.004, (P[:, 2] - cd[2]) / 0.005)
                P[:, 1] += SMILE_DIMPLE * np.exp(-dd ** 2) * front
            n, _ = folded(P, M.faces)
            LATE_ADJUST.append("smile_form rise %.1f, tuck %.1f, apple %.1f, dimple %.1f mm" % (
                1000 * SMILE_RISE, 1000 * SMILE_TUCK, 1000 * SMILE_APPLE, 1000 * SMILE_DIMPLE))
            print("BOY late smile_form: corners %.1f mm out, rise %.1f, tuck %.1f, apple %.1f, dimple %.1f mm (most moved %.1f mm); %d folded" % (
                1000 * xc, 1000 * SMILE_RISE, 1000 * SMILE_TUCK, 1000 * SMILE_APPLE, 1000 * SMILE_DIMPLE,
                1000 * float(np.linalg.norm(P - before, axis=1).max()), n))
    # 7. ears: raised to the sheet's height, sized about their root, their outline rounded by Taubin rounds (no new points)
    ear = np.isin(np.array(M.part), ("ear_l", "ear_r"))
    for nm in ("ear_l", "ear_r"):
        e_ = np.array(M.part) == nm
        Q = P[e_]
        print("BOY ear %s: rows %.0f to %.0f, out to column %.0f, back %.1f to %.1f cm" % (
            nm, float(hrow(Q[:, 2].max())), float(hrow(Q[:, 2].min())), float(np.abs(Q[:, 0]).max() / HS), 100 * Q[:, 1].min(), 100 * Q[:, 1].max()))
    if EAR_UP or EAR_LATE_SIZE != 1.0 or EAR_LATE_SMOOTH or EAR_TURN:
        for nm in ("ear_l", "ear_r"):
            e_ = np.array(M.part) == nm
            Q = P[e_]
            ax_ = np.abs(Q[:, 0])
            root = Q[ax_ < np.quantile(ax_, 0.15)].mean(0)
            s_ = 1.0 if nm == "ear_l" else -1.0
            a_ = math.radians(EAR_TURN)
            v_ = (Q - root) * EAR_LATE_SIZE
            # (turned about the upright through its root, its back edge out: the bowl faces more forward)
            v_ = np.stack([v_[:, 0] * math.cos(a_) + s_ * v_[:, 1] * math.sin(a_), -s_ * v_[:, 0] * math.sin(a_) + v_[:, 1] * math.cos(a_), v_[:, 2]], 1)
            P[e_] = root + v_ + np.array((0.0, 0.0, EAR_UP))
        M.P = [p for p in P]
        if EAR_LATE_SMOOTH:
            taubin(M, ear, rounds=EAR_LATE_SMOOTH)
            P = np.array(M.P)
        n, _ = folded(P, M.faces)
        LATE_ADJUST.append("ears up %.1f mm, x%.2f, %d rounds" % (1000 * EAR_UP, EAR_LATE_SIZE, EAR_LATE_SMOOTH))
        print("BOY late ears: up %.1f mm, size x%.2f, %d smoothing rounds; %d folded" % (1000 * EAR_UP, EAR_LATE_SIZE, EAR_LATE_SMOOTH, n))
    # 8. neck_ridge_off: the back of the neck evened by Taubin rounds (its two creases from the nape down), faded out
    # toward the skull, the shoulders and the throat
    if NECK_RIDGE:
        zt = float(np.mean([P[i][2] for i in M.tag["neck_rings"][-1]]))
        z0 = float(np.mean([P[i][2] for i in M.tag["neck_rings"][0]]))
        cy = float(np.mean([P[i][1] for i in M.tag["neck_rings"][-1]]))
        z = P[:, 2]
        wgt = np.isin(fams, ("neck", "head")) * smooth01(z0 - 0.005, z0 + 0.02, z) * (1.0 - smooth01(zt + 0.03, zt + 0.07, z)) \
            * smooth01(cy - 0.01, cy + 0.015, P[:, 1])
        before = P.copy()
        taubin(M, wgt > 0.01, rounds=NECK_RIDGE)
        P = np.array(M.P)
        P = before + (P - before) * wgt[:, None]
        M.P = [p for p in P]
        n, _ = folded(P, M.faces)
        LATE_ADJUST.append("neck_ridge_off %d rounds" % NECK_RIDGE)
        print("BOY late neck_ridge_off: %d rounds over %d points (most moved %.1f mm); %d folded" % (
            NECK_RIDGE, int((wgt > 0.01).sum()), 1000 * float(np.linalg.norm(P - before, axis=1).max()), n))
    M.P = [p for p in P]
    print("BOY late adjustments: %s" % (LATE_ADJUST or "none"))


def finish(M, T, joints, sh):
    H = None
    bones = skeleton_joints(M, T, joints)
    weights = weights_of(M, T, bones, joints)
    islands = plan_uvs(M, T, H, joints)
    placed, face_uv = pack(islands)
    under = boxer_faces(M, T)
    eye_cut, eyes = set(), []
    if EYES_OPEN and HEAD2 and M.tag.get("eye_strip"):
        M, face_uv, weights, under, eye_cut, eyes = open_eyes2(M, face_uv, weights, under)
    elif EYES_OPEN:
        M, face_uv, weights, under, eye_cut, eyes = open_eyes(M, face_uv, weights, under)
    unfold_head(M)
    if FACE_POLISH:
        face_polish(M)
    if NAPE_POLISH:
        nape_polish(M)
    late_adjust(M, eyes, face_uv, weights)
    # (third pass: the head is the fitted base mesh, made in build_head; no splitting, smoothing or sculpting here)
    hobjs = lambda: [(np.array(M.P), M.tris(), M.tri_fams())]
    fit_angled_model(hobjs(), sh)
    landmark_report(M, "final")
    os.makedirs(TEX, exist_ok=True)
    for picture in ATLAS:
        write_layout(face_uv, placed, picture, os.path.join(TEX, "boy_%s_layout.png" % picture))
    tris_all = M.tris()
    tf = M.tri_fams()
    P = np.array(M.P)
    no_arms = [t for t, f in zip(tris_all, tf) if f not in ("arm", "hand")]
    Pc, no_arms_c = with_caps(M, P, no_arms)
    skin, spos, shit = paint_skin(M, face_uv, sh, tris_all, Pc, no_arms_c, joints)
    places = hand_silhouettes(sh, "final")
    face, fpos, fhit = paint_head(M, face_uv, sh)
    face = pad_edges(delight(face, fhit, DELIGHT * 0.6), fhit)
    if RULE_PAINT:
        # (sixth pass: the hands painted by rule with the rest, not from the hands sheet; the face kept from the
        # sheet only on its front)
        face, fpos, fhit = rule_face(M, face_uv, face, joints)
        face = pad_edges(face, fhit)
    else:
        skin = pad_edges(paint_hands_from_sheet(M, face_uv, skin, sh, places, joints), shit)
        # (fourth pass) the sheet's painted light taken out of both pictures by half (the game lights him: lit, the
        # sheet's own shading of muscles read as rings and swirls across his back and belly, the critic's "contour bands")
        skin = pad_edges(delight(skin, shit, DELIGHT), shit)
    zt = float(np.mean([M.P[i][2] for i in T[-1]]))
    near_b = shit & (np.abs(spos[..., 2] - (zt - 0.008)) < 0.008)
    near_h = fhit & (np.abs(fpos[..., 2] - (zt + 0.008)) < 0.008)
    if near_b.any() and near_h.any():
        # (fourth pass: matched round the neck in twelve sectors, not as one mean: his front and back differ, and
        # one gain left a step at the base of his neck in the lit views)
        cy = float(np.mean([M.P[i][1] for i in T[-1]]))
        ang_b = np.arctan2(spos[..., 0], -(spos[..., 1] - cy))
        ang_h = np.arctan2(fpos[..., 0], -(fpos[..., 1] - cy))
        sec = np.linspace(-math.pi, math.pi, 13)
        gains = []
        for i in range(12):
            sb = near_b & (ang_b >= sec[i]) & (ang_b < sec[i + 1])
            sh_ = near_h & (ang_h >= sec[i]) & (ang_h < sec[i + 1])
            gains.append(skin[sb].mean(0) / np.maximum(face[sh_].mean(0), 1e-3) if sb.sum() > 5 and sh_.sum() > 5 else np.full(3, np.nan))
        gains = np.array(gains)
        for k in range(3):
            ok = np.isfinite(gains[:, k])
            gains[:, k] = np.interp(np.arange(12), np.where(ok)[0], gains[ok, k], period=12) if ok.any() else 1.0
        mids = (sec[:-1] + sec[1:]) / 2.0
        g = np.stack([np.interp(ang_h, mids, gains[:, k], period=math.tau) for k in range(3)], -1)
        g = np.clip(g, 0.75, 1.3)
        w = (1.0 - smooth01(zt, zt + 0.07, fpos[..., 2])) * fhit
        face = pad_edges(np.clip(face * (1 + (g - 1) * w[..., None]), 0, 1), fhit)
        print("BOY neck tone (by sector round the neck): %s" % np.round(gains.mean(1), 3).tolist())
    save_rgb(os.path.join(TEX, "boy_skin.png"), skin[::-1])
    tone_report(M, face_uv, face, sh)
    save_rgb(os.path.join(TEX, "boy_face.png"), face[::-1])
    armature = make_armature(bones)
    mat_skin = textured_material("boy_skin", os.path.join(TEX, "boy_skin.png"))
    mat_face = textured_material("boy_face", os.path.join(TEX, "boy_face.png"))
    export_views(M, face_uv, mat_skin, places)

    def skin_object(name, ids):
        ob = mesh_object(name, P, [M.faces[i] for i in ids], armature, weights)
        me = ob.data
        me.materials.append(mat_skin)
        me.materials.append(mat_face)
        uvl = me.uv_layers.new(name="UVMap")
        for poly, fi in zip(me.polygons, ids):
            pic, uv = face_uv.get(fi, ("skin", [(0.0, 0.0)] * poly.loop_total))
            poly.material_index = 0 if pic == "skin" else 1
            for li, q in zip(poly.loop_indices, uv):
                uvl.data[li].uv = q
        # (points no face of this piece uses are dropped, so each piece carries only its own)
        bm = bmesh.new()
        bm.from_mesh(me)
        if name == "boy_body" and HEAD2 and UNSUB_BACK:
            # (eleventh pass, the budget) the back of the skull, a smooth dome the subdivision had made four times as
            # fine as it needs, taken back to the cage's density there (the face, ears, eyes and the neck's seam kept)
            bm.verts.ensure_lookup_table()
            hp = [i for i in range(len(P)) if M.part[i] == "head"]
            zc_ = float(np.mean([M.P[i][2] for i in M.tag["neck_rings"][-1]]))
            yc_ = float(np.median([M.P[i][1] for i in hp]))
            sel = [bm.verts[i] for i in hp if M.P[i][1] > yc_ + UNSUB_BACK and M.P[i][2] > zc_ + 0.035 and bm.verts[i].link_faces]
            n0 = sum(len(f.verts) - 2 for f in bm.faces)
            bmesh.ops.unsubdivide(bm, verts=sel, iterations=1)
            print("BOY back of the skull un-subdivided: %d points chosen, %d triangles to %d" % (len(sel), n0, sum(len(f.verts) - 2 for f in bm.faces)))
        loose = [v for v in bm.verts if not v.link_faces]
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
        bm.to_mesh(me)
        bm.free()
        return ob
    # His body, and the skin under the shorts as its own piece (finished skin, hidden by whatever he wears).
    skin_object("boy_body", [i for i in range(len(M.faces)) if i not in under and i not in eye_cut])
    if eyes:
        # his eyes: balls of their own on the head bone, in the openings (open_eyes)
        eye_path = os.path.join(TEX, "boy_eye.png")
        eye_texture(eye_path)
        Pe, Fe = eye_balls(eyes)
        ob = mesh_object("boy_eyes", Pe, [f_ for f_, _ in Fe], armature, [{"head": 1.0}] * len(Pe))
        ob.data.materials.append(textured_material("boy_eye", eye_path))
        uvl = ob.data.uv_layers.new(name="UVMap")
        for poly, (_, uv) in zip(ob.data.polygons, Fe):
            for li, q in zip(poly.loop_indices, uv):
                uvl.data[li].uv = q
        print("BOY EYES balls: %d triangles" % (2 * len(Fe)))
    skin_object("boy_body_under", sorted(under))
    Bx = build_boxers(M, T, sh, weights, armature)
    total = report_counts(M)
    print("BOY triangles with the shorts: %d" % (total + getattr(Bx, "n_tris_out", len(Bx.tris()))))
    zs = P[:, 2]
    print("BOY height: soles %.3f to crown %.3f m (%.3f m)" % (zs.min(), zs.max(), zs.max() - zs.min()))
    print("BOY joints: %s" % json.dumps({n: [round(float(v), 3) for v in p] for n, p, _ in bones if "_" not in n or n.endswith("_l") and not n.startswith(("finger", "thumb"))}))
    objs = [(np.array(M.P), M.tris(), M.tri_fams())]
    Pc, tc = with_caps(M, np.array(M.P), [])
    objs.append((Pc, tc, ["sidecap"] * len(tc)))
    objs.append((np.array(Bx.P), Bx.tris(), ["boxers"] * len(Bx.tris())))
    stats = overlay(objs, sh, "final")
    print("BOY overlay final %s" % json.dumps(stats))
    head_silhouettes(objs[:1], sh, "final")
    body_silhouettes(objs, sh, "final")
    winding_check(M, "body")
    winding_check(Bx, "shorts (open: not a volume)")
    export(armature, GLB)


def main():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sh = Sheets()
    make_hand(sh)
    if "--ring-feet" not in ARGS:
        make_foot()
    if "--hand-only" in ARGS:
        hand_silhouettes(sh, "only")
        return
    M, T, joints = build_body(sh)
    build_head(M, sh, T)
    if "--head-only" in ARGS:
        return
    dup = [(i, f, M.fpart[i]) for i, f in enumerate(M.faces) if len(set(f)) != len(f)]
    seen_f = {}
    for i, f in enumerate(M.faces):
        seen_f.setdefault(tuple(sorted(f)), []).append(i)
    twice = [v for v in seen_f.values() if len(v) > 1]
    print("BOY faces with a point twice: %d; faces made twice: %d" % (len(dup), len(twice)))
    print("BOY windings before fixing (same-way edges, edges of 3+ faces): %s" % (inconsistent(M.faces),))
    flipped = fix_winding(M)
    print("BOY windings after fixing: %s" % (inconsistent(M.faces),))
    if "--wind-only" in ARGS:
        return
    print("BOY built: %d points, %d faces, %d triangles (%d turned outward)" % (len(M.P), len(M.faces), len(M.tris()), flipped))
    body_faces = [f for f, p in zip(M.faces, M.fpart) if part_family(p) not in ("ear", "nose")]
    print("BOY open edges of the body (should be none): %d" % len(open_edges(body_faces)))
    fams = np.array([part_family(p) for p in M.part])
    frozen = np.isin(fams, ("head", "nose", "ear", "neck", "hand") + (("foot",) if FOOT else ()))
    frozen[T[-1]] = True
    for sfx in ("_l", "_r"):
        for ring in M.tag["arm_rings" + sfx][-2:]:
            frozen[ring] = True
    mir = mirror_map(M.P)
    print("BOY mirror pairs: %d of %d points matched" % ((mir != np.arange(len(mir))).sum(), len(mir)))

    def snapshot():
        Pc, tc = with_caps(M, np.array(M.P), [])
        return [(np.array(M.P), M.tris(), M.tri_fams()), (Pc, tc, ["sidecap"] * len(tc))]
    stats = overlay(snapshot(), sh, "r0")
    print("BOY overlay r0", json.dumps(stats))
    for rnd in range(1, FIT_ROUNDS + 1):
        moved, most = fit_round(M, sh, frozen)
        symmetrize(M, mir)
        relax(M, frozen, 0.2, 1)
        stats = overlay(snapshot(), sh, "r%d" % rnd, report=(rnd == FIT_ROUNDS))
        print("BOY fit round %d: %d points moved, most %.1f cm; %s" % (rnd, moved, most * 100, json.dumps(stats)))
    smooth_armpits(M)
    smooth_shoulders(M)
    sculpt_body(M)
    unfold_body(M, tries=6, ring=False)
    # (fourth pass: the unfolding's smoothing closed the gap between each arm and his side, which opened the front and
    # back outline gap above the shorts from 1.5 to 3.7 cm: the outlines are fitted again after it, then any fold left
    # smoothed at its own points only)
    for rnd in range(2):
        fit_round(M, sh, frozen)
        symmetrize(M, mir)
    unfold_body(M, tries=4, ring=False)
    s_curve(M, T)
    shoulder_slope(M, joints)
    finish(M, T, joints, sh)


SHOULDER_DROP = (float(arg("--shoulder-drop", "0.007")), float(arg("--shoulder-in", "0.005")))


def shoulder_slope(M, joints):
    """(seventh pass; the critic: "narrow, bony, sloping shoulders ... lower and narrow the shoulder caps by about 1 cm
    each side"; "in the two grey poses the shoulder top looks boxy and square") The top of each shoulder, where the
    trapezius meets the arm's cap, drawn down and in on a soft round field (the cap's outline rounder, the slope from
    the neck longer); the arm below the cap and the neck above it barely move."""
    P = np.array(M.P)
    fams = np.array([part_family(p) for p in M.part])
    ok = np.isin(fams, ("torso", "shoulder", "arm"))
    moved = 0.0
    for sfx, s in (("_l", 1.0), ("_r", -1.0)):
        sj = np.array(joints["shoulder_l"], float) * np.array((s, 1.0, 1.0))
        c = sj + np.array((-s * 0.01, 0.0, 0.035))
        d = np.linalg.norm((P - c) * np.array((1.0, 1.3, 1.0)), axis=1)
        w = np.exp(-(d / 0.045) ** 2) * ok * (P[:, 2] > sj[2] - 0.02)
        P[:, 2] -= SHOULDER_DROP[0] * w
        P[:, 0] -= s * SHOULDER_DROP[1] * w
        moved = max(moved, float(w.max()))
    M.P = [p for p in P]
    n, _ = folded(P, M.faces)
    print("BOY shoulders sloped: %.1f mm down, %.1f mm in at most; %d folded" % (1000 * SHOULDER_DROP[0] * moved, 1000 * SHOULDER_DROP[1] * moved, n))


S_CURVE = float(arg("--s-curve", "1.0"))


def s_curve(M, T):
    """(sixth pass; the critic: "the torso is a straight tube in front and side ... a slight waist about 8% narrower than
    the ribs ... the chest slightly forward and the back curves (lumbar dip)") A child's S in profile and a slight
    waist, as smooth bumps by height: the ribcage carried forward, the small of the back drawn in, the belly a little
    round below the navel, the waist narrowed; the arms move with the chest they hang from, the hands and legs not."""
    if S_CURVE <= 0:
        return
    P = np.array(M.P)
    fams = np.array([part_family(p) for p in M.part])
    body = np.isin(fams, ("torso", "shoulder", "arm", "neck", "head", "ear", "nose"))
    zc, zw = float(body_z(BR(640))), float(body_z(BR(790)))
    z = P[:, 2]

    def bump(c, r):
        return np.exp(-((z - c) / r) ** 2)
    cy = np.array([torso_centre(M, T, float(zz))[1] for zz in np.clip(z, body_z(BR(1000)), body_z(BR(415)))])
    back = smooth01(-0.01, 0.04, P[:, 1] - cy)
    front = smooth01(0.01, -0.04, P[:, 1] - cy)
    torso = np.isin(fams, ("torso", "shoulder"))
    dy = -0.006 * smooth01(zw, zc, z)                               # the chest and all above it a little forward
    dy += -0.009 * bump(zw, 0.06) * back * torso                     # the small of the back drawn in
    dy += -0.004 * bump(zw - 0.07, 0.045) * front * torso            # the belly below the navel a little round
    dx = 1.0 - 0.06 * bump(zw, 0.06) * torso                        # the waist
    k = np.where(body, S_CURVE, 0.0)
    P[:, 1] += dy * k
    P[:, 0] *= 1.0 + (dx - 1.0) * k
    M.P = [p for p in P]
    n, _ = folded(P, M.faces)
    print("BOY S-curve and waist: chest %.1f mm forward, back %.1f mm in; %d folded" % (6 * S_CURVE, 9 * S_CURVE, n))


if __name__ == "__main__":
    main()
