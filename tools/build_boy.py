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
FIT_ROUNDS = int(arg("--rounds", "6"))

# ------------------------------------------------------------------------------------------------------------------
# The sheets
# ------------------------------------------------------------------------------------------------------------------

SHEET = os.path.join(ART, "concept_boy_tpose.jpg")
FACE_SHEET = os.path.join(ART, "concept_faces_trial.jpg")

# The base-body sheet (pixels of the 2752 by 1536 picture). His crown (the skull, under the hair: the hair's top is
# row 88) is placed at row 135 from the head's proportions (eyes 256, chin 380: the eyes a little below the middle).
SOLE = 1462.0
CROWN = 135.0
HEIGHT = 1.50                 # metres, soles to crown
S = HEIGHT / (SOLE - CROWN)   # metres a pixel (1.13 mm)
MID = {"front": 674.5, "side": 1430.0, "back": 2202.5}
SPAN = {"front": (100, 1240), "side": (1250, 1690), "back": (1690, 2740)}
# The shorts: the rows they cover (the band's top, the hem), the crotch, and how far the body sits inside them.
BOXERS = (800, 1034)
CROTCH = 1000
BOXER_EASE = 14               # pixels (1.6 cm)
# The side view has no arm (a round patch where it would be): those pixels are not painted from.
SIDE_PATCH = ((1338, 430), (1482, 574))
# The painted-face trial: its close-up of him is this sheet's face times FACE_K, his eye line's middle at FACE_AT
# (this sheet's (674.5, 256)).
FACE_K = 2.2
FACE_AT = (2277.5, 1162.0)
FACE_REF_ROW = 256.0


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


def unline(pix):
    """The sheet's guide lines painted out (rows where the margin left of the figures is unlike the ground)."""
    ground = np.median(pix[:, 95:135].reshape(-1, 3), axis=0)
    rows = set(np.where(np.abs(pix[:, 95:135] - ground).max(-1).mean(axis=1) > 0.04)[0].tolist())
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
        self.body_mask = colour_mask(unline(self.body_pix))
        self.face_pix = load_picture(FACE_SHEET)
        self.face_mask = colour_mask(self.face_pix)
        self.body_target = self._body_target()

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
    if view in ("front", "face"):
        return np.stack([N[:, 0], -N[:, 2]], 1), -N[:, 1]
    if view == "back":
        return np.stack([-N[:, 0], -N[:, 2]], 1), N[:, 1]
    return np.stack([-N[:, 1], -N[:, 2]], 1), -N[:, 0]


def world_dir(view, d2):
    """A direction in the picture as a model direction (in the picture's plane)."""
    z = np.zeros(len(d2))
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
TORSO_ROWS = [1000, 975, 945, 915, 885, 855, 825, 800, 775, 750, 720, 690, 660, 630, 600, 560, 520, 480, 448, 430, 415]
_H0 = TORSO_ROWS.index(560)
HOLE = (_H0, _H0 + 1, _H0 + 2, _H0 + 3)
HOLE_COLS = (3, 4, 5)
# The torso's half width where the arms hide it in the front view (metres), by row (the chest under the armpit is
# 0.183 where the arm leaves it, row 605; the shoulders' top slope into the trapezius above).
TORSO_UNDER_ARMS = {600: 0.184, 560: 0.186, 520: 0.186, 480: 0.181, 448: 0.17}
# Shoulder joint row, elbow row (the back view's elbow), wrist row (the narrowest, above the hand).
# (third round: the shoulder joint and the arm's root raised and widened, so the root's top is the shoulder's round cap
# under the trapezius; at row 510 a square corner stood between the torso's top rings and the arm)
SHOULDER_ROW, ELBOW_ROW, WRIST_ROW = 495, 695, 862
ARM_ROOT_R = 0.08
ARM_Y = (0.0, -0.02)
ARM_DEPTH = ((0.0, 1.05), (0.12, 1.0), (0.22, 0.9), (0.27, 0.86), (0.37, 0.95), (0.47, 1.12))
# The legs: rows of their rings (from the crotch down), the hip joint, the knee and the ankle.
LEG_ROWS = [1020, 1045, 1075, 1110, 1150, 1190, 1230, 1270, 1310, 1345]
HIP_ROW, KNEE_ROW, ANKLE_ROW = 940, 1110, 1352
HIP_X = 0.09
LEG_X = 0.11                      # where to look for the leg in each row (from the middle)
FOOT_YAW = math.radians(14.0)     # toes out
TOE_REACH = 1.0
# The foot's rings below the ankle: height, reach forward of the ankle, back, and to each side (the side view: heel
# at column 1365, toes' end at 1627, the ankle's middle 1428; the sheet draws him big feet, 0.29 m long).
FOOT_RINGS = ((0.096, 0.052, 0.05, 0.04), (0.066, 0.118, 0.062, 0.045), (0.036, 0.206, 0.069, 0.051),
              (0.013, 0.214, 0.066, 0.05), (0.0, 0.2, 0.056, 0.043))


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
    for r in range(615, WRIST_ROW, 5):
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
    stations = [0.03, 0.07, 0.115, 0.16, Lu - 0.03, Lu, Lu + 0.03, Lu + 0.08, Lu + 0.13, Lu + Lf - 0.03, Lu + Lf]
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


# The hand (a boy's big hand, as the sheet draws it: about 0.18 m wrist to fingertip): name, root quad, length,
# half-width, spread (degrees toward the little finger).
# (second round: thicker, shorter and more curled, as the sheet's chunky hanging hands; the first round's were long
# thin straight sticks)
FINGERS_SPEC = (("index", 0, 0.06, 0.0102, -1.5), ("middle", 1, 0.067, 0.0107, 0.0),
                ("ring", 2, 0.063, 0.0102, 1.5), ("little", 3, 0.05, 0.0092, 3.0))
FINGER_CURL = (0.26, 0.38, 0.3)
FINGER_SEGS = (0.44, 0.31, 0.25)


def hand(M, wrist_ring, side, W, L, joints):
    """A hand from the wrist ring (the captain's welded hand, the usual low-poly way, in a boy's size): a wrist ring,
    a wedge palm thick at the heel with pads at the thumb's and little finger's side, a knuckle ridge; each finger
    grown out of one of the palm's end quads in four-sided sections, different lengths, a little fanned and curled,
    blunt; the thumb grown out of the palm's side face. The back faces out and a little forward."""
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
            pts[j] = at + Wd * (w * hw * (0.9 if edge else 1.0)) + Tb * (ht * (0.72 if edge else 1.0) + lb)
        for j, w, pd in zip(palm, across, palm_drop):
            edge = abs(w) == 1.0
            pts[j] = at + Wd * (w * hw * (0.9 if edge else 1.0)) - Tb * (ht * (0.72 if edge else 1.0) + pd)
        return [M.add(mirror_x(q, side), part) for q in pts]

    def bridge(a, b, pt=part):
        M.bridge(a, b, pt) if side > 0 else M.bridge(b, a, pt)
    # (sixth round: the captain's eighth-round hand, borrowed: Twilight Princess's hands, measured on Telma and Shad,
    # are about 130 to 150 triangles: a boxy palm of three rings, four separate fingers of four-sided sections with
    # loops only at the joints, a blunt box end, a separate thumb, the rest painted. In the boy's sizes.)
    r0 = ring_at(W + L * 0.012, 0.03, 0.019)
    r1 = ring_at(W + L * 0.04, 0.038, 0.022, palm_drop=(0.005, 0.002, 0.0, 0.002, 0.004))
    knuck = W + L * 0.09
    r3 = ring_at(knuck, 0.042, 0.015, back_lift=(0.001, 0.0028, 0.0028, 0.0028, 0.001))
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
        """A finger out of a root quad through rings of four (point j over the root's corner j), closed by a point."""
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

    for name, i, length, hw, spread in FINGERS_SPEC:
        root = [r3[back[i]], r3[back[i + 1]], r3[palm[i + 1]], r3[palm[i]]]
        k0 = knuck + Wd * (across[i] + across[i + 1]) / 2.0 * 0.042
        way = Matrix.Rotation(math.radians(spread), 3, Tb) @ L.copy()
        ac, bk = Wd.copy(), Tb.copy()
        frames = [(45.0, 90.0)]
        at = k0 + way * 0.007
        frames.append((at.copy(), ac.copy(), bk.copy(), hw * 1.02, hw * 0.92))          # the knuckle
        bones = [k0.copy()]
        for si, fr in enumerate(FINGER_SEGS):
            rot = Matrix.Rotation(-FINGER_CURL[si], 3, ac)
            way = rot @ way
            bk = rot @ bk
            at = at + way * (length * fr)
            bones.append(at.copy())
            if si < 2:
                frames.append((at.copy(), ac.copy(), bk.copy(), hw * (0.97, 0.92)[si], hw * (0.86, 0.8)[si]))
        frames.append((at - way * 0.0035, ac.copy(), bk.copy(), hw * 0.84, hw * 0.7))
        grow(name, root, frames, at + way * 0.0045 - bk * 0.0018, part + "_" + name)
        joints["%s%s" % (name, sfx)] = [Vector(mirror_x(b, side)) for b in bones]
    rootc = sum((Vector(mirror_x(M.P[v], side)) for v in thumb_root), Vector()) / 4.0
    way = (Wd * 0.8 + L * 0.48 - Tb * 0.36).normalized()
    U = (L - way * L.dot(way)).normalized()
    V = way.cross(U).normalized()
    if V.dot(Tb) < 0:
        V = -V
    frames = [(135.0, -90.0)]
    at = rootc + way * 0.014
    frames.append((at.copy(), U.copy(), V.copy(), 0.017, 0.0145))                   # the fat base
    bones = [rootc.copy()]
    for si, (fr, rad) in enumerate(((0.42, 0.0148), (0.32, 0.0135), (0.26, 0.0122))):
        rot = Matrix.Rotation(-0.22, 3, U.cross(way).normalized())
        way = rot @ way
        U = rot @ U
        V = rot @ V
        at = at + way * (0.062 * fr)
        bones.append(at.copy())
        if si < 2:
            frames.append((at.copy(), U.copy(), V.copy(), rad, rad * 0.86))
    frames.append((at - way * 0.0035, U.copy(), V.copy(), 0.0106, 0.0088))
    grow("thumb", thumb_root, frames, at + way * 0.0045, part + "_thumb")
    joints["thumb%s" % sfx] = [Vector(mirror_x(b, side)) for b in bones]
    joints["thumb_back%s" % sfx] = np.array(mirror_x(V, side))
    joints["hand_frame%s" % sfx] = tuple(np.array(mirror_x(v, side)) for v in (Tb, Wd, L))
    joints["knuckles%s" % sfx] = Vector(mirror_x(knuck, side))


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
    for z, front, backr, half in FOOT_RINGS:
        ring = []
        for th in angles:
            al = th - FOOT_YAW
            cu, cv = math.cos(al), math.sin(al)
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
    joints["toe_tip" + sfx] = Vector(mirror_x(Vector((ax, ay, 0.02)) + fwd * 0.21, side))


# ------------------------------------------------------------------------------------------------------------------
# The head, measured off crops of the same sheet (front: middle column 674.5; side: the face's front and the skull's
# back, columns; the hair hides the skull, so its back and top are rounded inside the hair's outline)
# ------------------------------------------------------------------------------------------------------------------

# (row, half width in px (front view, cheeks and jaw without the ears), the face's front column in the side view,
# the skull's or neck's back column, how much the ring narrows toward its front (the jaw to the chin))
HEAD_TABLE = (
    # (second round: the back column measured where the hair ends at his nape (rows 350 to 370: the neck at 1381 to
    # 1385), and kept inside the hair's thin bottom edge above it (1361 at row 310, 1365 at 330))
    (398, 61, 1506, 1377, 0.0),     # the neck
    (390, 57, 1532, 1381, 0.55),    # under the chin, into the throat (sixth round: the chin 3 rows lower; smoothed it sat high)
    (381, 54, 1557, 1383, 0.5),     # the chin's bottom
    (366, 56, 1570, 1382, 0.48),    # the chin
    (349, 63, 1568, 1376, 0.38),    # the groove under the lower lip (fifth round: the jaw narrowed more to the chin, as the sheet's V)
    (337, 69, 1574, 1369, 0.26),    # the lips
    (324, 75, 1575, 1363, 0.15),    # the upper lip
    (311, 80, 1571, 1357, 0.05),    # under the nose
    (293, 86, 1567, 1350, 0.0),     # the cheeks (the nose is its own shell)
    (275, 88, 1565, 1346, 0.0),
    (258, 88, 1568, 1345, 0.0),     # the eyes
    (241, 87, 1573, 1347, 0.0),     # the brow
    (221, 84, 1570, 1352, 0.0),     # the forehead
    (201, 80, 1562, 1360, 0.0),
)
SKULL_ROWS = [186, 170, 156, 144]
# The nose (row, the side view's tip column, full width px in the front view) and the flare of its wings by row.
# (second round: a narrow bridge, then the ball of the tip and the round wings, as the trial paints it: the first
# round's widths grew evenly into a wedge)
NOSE_PROFILE = ((262, 1569, 15), (270, 1576, 17), (280, 1584, 20), (288, 1590, 27), (295, 1594, 35),
                (300, 1593, 40), (305, 1588, 47), (309, 1577, 42))
NOSE_WINGS = ((295, 0.0), (300, 0.12), (305, 0.28), (309, 0.24))
EAR_ROWS = (257, 316)         # the ear's top and bottom
EAR_COLS = (1460, 1414)       # its front and back in the side view
EAR_OUT = 0.022


def head_rings_measured():
    out = []
    for r, hw, fc, bc, taper in HEAD_TABLE:
        yf = (MID["side"] - fc) * S
        yb = (MID["side"] - bc) * S
        out.append((float(body_z(r)), hw * S, yf, yb, taper))
    return out


def skull_measure(band):
    """The skull's rings above the forehead's ring: an egg rounding up to the crown, its middle a little back as it
    rises (a boy's round cranium)."""
    z0, hw0, yf0, yb0, _ = band
    cy0, d0 = (yf0 + yb0) / 2.0, (yb0 - yf0) / 2.0
    zt = float(body_z(CROWN))
    out = []
    for r in SKULL_ROWS:
        z = float(body_z(r))
        t = (z - z0) / (zt - z0)
        k = (1.0 - t ** 2.1) ** (1.0 / 2.1)
        cy = cy0 + 0.014 * t ** 1.4
        out.append((z, hw0 * k, cy - d0 * k * (1.0 - 0.05 * t), cy + d0 * k, 0.0))
    return out


def build_head(M, sh, top_ring):
    rings = head_rings_measured()
    skull = skull_measure(rings[-1])
    prev = top_ring
    H = []
    allr = rings + skull
    for i, (z, hw, yf, yb, taper) in enumerate(allr):
        cy, d = (yf + yb) / 2.0, (yb - yf) / 2.0
        p = 0.82 if i < len(rings) else 0.86
        pts = ring_points(0.0, cy, z, hw, d, d, TORSO_N, p)
        if taper:
            pts = [(x * (1.0 - taper * max(0.0, (cy - y) / d)), y, zz) for x, y, zz in pts]
        ring = [M.add(q, "head") for q in pts]
        for k in range(TORSO_N):
            j = (k + 1) % TORSO_N
            M.face([prev[k], prev[j], ring[j], ring[k]], "head" if i else "neck")
            M.cell[len(M.faces) - 1] = ("head", i - 1, k)
        prev = ring
        H.append(ring)
    top = M.add((0.0, allr[-1][2] * 0.5 + allr[-1][3] * 0.5, float(body_z(CROWN))), "head")
    for k in range(TORSO_N):
        j = (k + 1) % TORSO_N
        M.face([prev[k], prev[j], top], "head")
        M.cell[len(M.faces) - 1] = ("head", len(allr) - 1, k)
    M.tag["head_rings"] = H
    nose(M, rings)
    for side in (1, -1):
        ear(M, rings, side)
    return rings


def face_front_at(rings, z):
    zs = [r[0] for r in rings]
    ys = [r[2] for r in rings]
    return float(np.interp(z, zs, ys))


def nose(M, rings):
    """The nose lofted down the side view's profile, as wide as the front view paints it at each row."""
    loops = []
    n = 10
    for r, tipc, width in NOSE_PROFILE:
        tip = (MID["side"] - tipc) * S
        z = float(body_z(r))
        base = face_front_at(rings, z) + 0.01
        half = width / 2.0 * S
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


# (second round: the front of the rim stands out too, so the ear reads as a whole shell from the side, as the sheet
# draws it; the first round's lay flat at the front and read as a thin C)
EAR_RIM = ((0.25, 1.0, 0.75), (0.62, 0.92, 1.0), (0.9, 0.66, 1.0), (0.86, 0.38, 0.9), (0.62, 0.12, 0.75),
           (0.38, -0.02, 0.6), (0.12, 0.05, 0.45), (0.0, 0.3, 0.35), (0.02, 0.62, 0.4), (0.08, 0.88, 0.55))


def ear(M, rings, side):
    """An ear: a rim standing out from the head, a hollow bowl inside it, a back wall to the skull."""
    part = "ear_l" if side > 0 else "ear_r"
    zt, zb = float(body_z(EAR_ROWS[0])), float(body_z(EAR_ROWS[1]))
    y0 = (MID["side"] - EAR_COLS[0]) * S
    y1 = (MID["side"] - EAR_COLS[1]) * S
    zs = [r[0] for r in rings]
    zc = (zt + zb) / 2.0
    hw = float(np.interp(zc, zs, [r[1] for r in rings]))
    # (the ring's side is narrower behind its middle: the ear sits there)
    hw *= 0.94
    hgt, wid = zt - zb, y1 - y0
    tilt = math.radians(14.0)
    rim, bowl, wall = [], [], []
    for b, v, out in EAR_RIM:
        yy = y0 + b * wid + (v - 0.5) * hgt * math.sin(tilt)
        zz = zb + v * hgt
        x = hw - 0.004 + EAR_OUT * out
        rim.append(M.add(mirror_x((x, yy, zz), side), part))
        bc = (0.42, 0.5)
        yb_ = y0 + (bc[0] + (b - bc[0]) * 0.55) * wid + (v - 0.5) * hgt * math.sin(tilt) * 0.55
        zb_ = zb + (bc[1] + (v - bc[1]) * 0.55) * hgt
        bowl.append(M.add(mirror_x((hw - 0.004 + EAR_OUT * out * 0.45, yb_, zb_), side), part))
        wall.append(M.add(mirror_x((hw - 0.012, y0 + b * wid * 0.85, zz), side), part))
    centre = M.add(mirror_x((hw - 0.001, y0 + 0.4 * wid, zb + 0.45 * hgt), side), part)
    n = len(EAR_RIM)
    out = np.array((side, 0.0, 0.0))
    mid_ = np.array(M.P[centre])

    def away(c, mid_=mid_, side=side):
        d = np.array(c) - mid_
        d[0] = 0.0
        return d + np.array((side * 0.15, 0.0, 0.0)) * np.linalg.norm(d)
    # (second round) the rim rolled over: a ring a little in from the rim and standing proud of it (the helix), so
    # the ear's edge has thickness
    roll = []
    for r_, b_ in zip(rim, bowl):
        q = np.array(M.P[r_]) * 0.72 + np.array(M.P[b_]) * 0.28
        q[0] += side * 0.003
        roll.append(M.add(q, part))
    for j in range(n):
        k = (j + 1) % n
        M.face([rim[j], rim[k], roll[k], roll[j]], part, out)
        M.face([roll[j], roll[k], bowl[k], bowl[j]], part, out)
        M.face([bowl[j], bowl[k], centre], part, out)
        M.face([rim[k], rim[j], wall[j], wall[k]], part, away)


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
    print("BOY winding %s: signed volume %.4f m3 (must be > 0)" % (label, vol))
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
            under_arm = (fams == "torso") & (P[:, 2] > body_z(612)) & (P[:, 2] < body_z(436))
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
    P = (P + Q) / 2.0
    centre = mir == np.arange(len(P))
    P[centre, 0] = 0.0
    M.P = [p for p in P]


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


def head_overlay(objs_tris, sh):
    """The head over the sheet's front, side and back (twice the size) and over the painted-face trial's close-up."""
    if not OUT:
        return
    for view in ("front", "side", "back", "face"):
        skip = ("arm", "hand", "sidecap", "leg", "foot")
        pix = sh.face_pix if view == "face" else sh.body_pix
        model, shade = model_picture(objs_tris, view, pix.shape[:2], skip)
        if view == "face":
            r0, r1, c0, c1 = 940, 1536, 1960, 2600
        else:
            mid = MID[view] if view != "side" else 1460
            r0, r1, c0, c1 = 80, 440, int(mid - 170), int(mid + 170)
        pic = pix[r0:r1, c0:c1].copy()
        mm = model[r0:r1, c0:c1]
        half = np.where(mm[..., None], pic * 0.55 + np.array((0.2, 0.25, 0.45)) * 0.45, pic)
        half[outline_of(model)[r0:r1, c0:c1]] = (0.95, 0.1, 0.1)
        if view != "face":
            half = np.repeat(np.repeat(half, 2, 0), 2, 1)
        save_rgb(os.path.join(OUT, "overlay_head_%s.png" % view), half)


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


NECK_Z = float(body_z(418))
HEAD_Z = float(body_z(345))


def skeleton_joints(M, T, joints):
    hip_z = joints["hip_l"].z
    bones = [
        ("hips", torso_centre(M, T, hip_z + 0.03), None),
        ("spine", torso_centre(M, T, float(body_z(815))), "hips"),
        ("chest", torso_centre(M, T, float(body_z(650))), "spine"),
        ("neck", torso_centre(M, T, NECK_Z), "chest"),
    ]
    bones.append(("head", Vector((0.0, (MID["side"] - 1446.0) * S, HEAD_Z)), "neck"))
    for s, sfx in ((1, "_l"), (-1, "_r")):
        sh_ = Vector(mirror_x(joints["shoulder_l"], s))
        el = Vector(mirror_x(joints["elbow_l"], s))
        wr = Vector(mirror_x(joints["wrist_l"], s))
        bones.append(("clavicle" + sfx, Vector((s * 0.035, sh_.y - 0.01, sh_.z + 0.05)), "chest"))
        bones.append(("upper_arm" + sfx, sh_, "chest"))
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


def weights_of(M, T, bones, joints):
    at = {n: np.array(p) for n, p, _ in bones}
    P = np.array(M.P)
    out = []
    zt = [float(body_z(845)), float(body_z(680)), NECK_Z - 0.008]
    zn0, zn1 = float(body_z(400)), float(body_z(374))
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
            w = {"chest": 0.55, "upper_arm" + sfx: 0.45}
        elif fam == "arm":
            J, E, W = at["upper_arm" + sfx], at["forearm" + sfx], at["hand" + sfx]
            Lu = np.linalg.norm(E - J)
            s = along(p, J, E)
            if s > Lu - 0.05:
                s = Lu + along(p, E, W)
            w = chain_weights(s, ["upper_arm" + sfx, "forearm" + sfx, "hand" + sfx], [Lu, Lu + np.linalg.norm(W - E) + 0.005], 0.04)
            k = 0.4 * (1 - float(smooth01(0.0, 0.07, s)))
            if k > 0:
                w = {n: v * (1 - k) for n, v in w.items()}
                w["chest"] = w.get("chest", 0) + k
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
                w = chain_weights(s, ["hand" + sfx] + names, [0.004, l1, l1 + np.linalg.norm(a3 - a2)], 0.007)
            else:
                Wr = at["hand" + sfx]
                s = along(p, at["forearm" + sfx], Wr) - np.linalg.norm(Wr - at["forearm" + sfx])
                w = chain_weights(s, ["forearm" + sfx, "hand" + sfx], [0.0], 0.025)
        elif fam in ("leg", "foot"):
            H, K, A = at["thigh" + sfx], at["shin" + sfx], at["foot" + sfx]
            if fam == "leg":
                z = p[2]
                w = chain_weights(-z, ["thigh" + sfx, "shin" + sfx, "foot" + sfx], [-K[2], -A[2]], 0.04)
                k = 0.45 * float(smooth01(H[2] - 0.09, H[2] + 0.03, z))
                if k > 0:
                    w = {n: v * (1 - k) for n, v in w.items()}
                    w["hips"] = w.get("hips", 0) + k
            else:
                fwd = np.array((math.sin(FOOT_YAW) * (1 if sfx == "_l" else -1), -math.cos(FOOT_YAW), 0.0))
                u = float(np.dot(p - A, fwd))
                w = chain_weights(u, ["foot" + sfx, "toe" + sfx], [0.13], 0.025)
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


def plan_uvs(M, T, H, joints):
    islands = {}
    tf = [fi for fi, c in M.cell.items() if c[0] == "torso" and (c[2] >= 12 or c[2] < 4)]
    tb = [fi for fi, c in M.cell.items() if c[0] == "torso" and 4 <= c[2] < 12]
    islands["torso_front"] = cylinder_uvs(M, T, tf, back=False)
    islands["torso_back"] = cylinder_uvs(M, T, tb, back=True)
    # (second round: the neck, from the torso's top ring to the first head ring under the jaw, is in the skin's
    # picture with the torso, painted from the same views: the seam between the pictures was a bright line across the
    # base of his neck; under the jaw it sits in shadow)
    HR = H
    hf = [fi for fi, c in M.cell.items() if c[0] == "head" and (c[2] >= 12 or c[2] < 4) and 0 <= c[1] < len(H) - 1]
    hb = [fi for fi, c in M.cell.items() if c[0] == "head" and 4 <= c[2] < 12 and 0 <= c[1] < len(H) - 1]
    islands["head_front"] = grid_uvs(M, HR, hf, 12, up=True)
    islands["head_back"] = {fi: [(-u, v) for u, v in uv] for fi, uv in grid_uvs(M, HR, hb, 4, up=True).items()}
    nf = [fi for fi, c in M.cell.items() if c[0] == "head" and c[1] == -1 and (c[2] >= 12 or c[2] < 4)]
    nb = [fi for fi, c in M.cell.items() if c[0] == "head" and c[1] == -1 and 4 <= c[2] < 12]
    islands["neck_front"] = grid_uvs(M, [T[-1], H[0]], nf, 12, up=True)
    islands["neck_back"] = {fi: [(-u, v) for u, v in uv] for fi, uv in grid_uvs(M, [T[-1], H[0]], nb, 4, up=True).items()}
    for fi, c in M.cell.items():
        if c[0] == "head" and c[1] == len(H) - 1:
            key = "head_front" if (c[2] >= 12 or c[2] < 4) else "head_back"
            islands[key][fi] = None
    for sfx in ("_l", "_r"):
        rings = M.tag["arm_rings" + sfx]
        af = [fi for fi, p in enumerate(M.fpart) if p == "arm" + sfx]
        islands["arm" + sfx] = grid_uvs(M, rings, af, 5)
        lr = M.tag["leg_rings" + sfx]
        lf = [fi for fi, p in enumerate(M.fpart) if p in ("leg" + sfx, "foot" + sfx) and len(M.faces[fi]) == 4]
        islands["leg" + sfx] = grid_uvs(M, lr, lf, 9)
        sole = [fi for fi, p in enumerate(M.fpart) if p == "foot" + sfx and len(M.faces[fi]) == 3]
        islands["sole" + sfx] = planar_uvs(M, sole, np.array((1.0, 0, 0)), np.array((0, -1.0, 0)))
        hand_faces = [fi for fi, p in enumerate(M.fpart) if p == "hand" + sfx]
        for f in FINGERS + ("thumb",):
            rings = M.tag["finger_rings%s_%s" % (sfx, f)]
            tip, root = M.tag["finger_ends%s_%s" % (sfx, f)]
            ff = [fi for fi, p in enumerate(M.fpart) if p == "hand%s_%s" % (sfx, f)]
            isl = grid_uvs(M, rings, [fi for fi in ff if len(M.faces[fi]) == 4], 4)
            known = {}
            for fi, uv in isl.items():
                for v, q in zip(M.faces[fi], uv):
                    known.setdefault(v, q)
            vs = [q[1] for q in known.values()]
            for fi in ff:
                if fi in isl:
                    continue
                uv = []
                for v in M.faces[fi]:
                    if v in known:
                        uv.append(known[v])
                    else:
                        us = [known[w][0] for w in M.faces[fi] if w in known]
                        uv.append((float(np.mean(us)), (min(vs) - 0.006) if v == tip else (max(vs) + 0.006)))
                isl[fi] = uv
            name = "fing%s_%s" % (sfx, f)
            ISLANDS[name] = ("skin", 3.0)
            islands[name] = isl
        Tb, Wd, L = joints["hand_frame" + sfx]
        backs, palms = [], []
        for fi in hand_faces:
            n = face_normal(M.P, M.faces[fi])
            (backs if np.dot(n, Tb) >= 0 else palms).append(fi)
        islands["hand%s_back" % sfx] = planar_uvs(M, backs, Wd, -L)
        islands["hand%s_palm" % sfx] = planar_uvs(M, palms, -Wd, -L)
        ef = [fi for fi, p in enumerate(M.fpart) if p == "ear" + sfx]
        s = 1.0 if sfx == "_l" else -1.0
        islands["ear" + sfx] = planar_uvs(M, ef, np.array((0, s, 0.0)), np.array((0, 0, 1.0)))
    nf = [fi for fi, p in enumerate(M.fpart) if p == "nose"]
    ymin = min(M.P[v][1] for fi in nf for v in M.faces[fi])
    islands["nose"] = {fi: [(float(M.P[v][0]), float(M.P[v][2] - 0.8 * (M.P[v][1] - ymin))) for v in M.faces[fi]] for fi in nf}
    for key in ("head_front", "head_back"):
        fill_fans(islands[key], M)
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
    mask = erode(sh.body_mask, 2)
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
        seen = (qd <= zb[rows, cols] + 0.012) & mask[rows, cols] & (facing > 0.08) & hit.ravel()
        if view == "side":
            seen &= ~np.isin(tex_fam.ravel(), ("arm", "hand", "shoulder"))
            seen &= ~((cols >= pc0) & (cols <= pc1) & (rows >= pr0) & (rows <= pr1))
        colour = sh.body_pix[rows, cols]
        seen &= ~is_hair(colour)
        w = np.where(seen, facing ** 2, 0.0)
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
                    rgb[f_ & (bk > 0.15) & (np.abs(t_) < 0.0009)] *= 0.87
                    rgb[f_ & (bk > 0.15) & (np.abs(t_ - 0.0027) < 0.0007)] *= 0.95
                a_ = bones[3] - bones[2]
                a_ /= max(np.linalg.norm(a_), 1e-9)
                t_ = ((pos - bones[3]) * a_).sum(-1)
                nail = f_ & (bk > 0.35) & (t_ > -0.011) & (t_ < 0.004)
                rgb[nail] = rgb[nail] * 0.35 + np.array((0.88, 0.76, 0.72)) * 0.65
                rim = nail & ((np.abs(t_ + 0.011) < 0.001) | (bk < 0.45))
                rgb[rim] *= 0.84
                rgb[f_ & (bk < -0.2) & (t_ > -0.014)] *= np.array((1.04, 0.95, 0.93))
            for name in FINGERS:
                k0 = np.array(joints[name + sfx][0], float)
                rgb[mine & (back > 0.5) & (np.linalg.norm(pos - k0, axis=-1) < 0.009)] *= 1.06
    print("BOY paint skin: %.0f%% of its texels seen by a view" % (100.0 * (good & hit).sum() / max(hit.sum(), 1)))
    return pad_edges(rgb, hit), pos, hit


def paint_head(M, face_uv, sh):
    """His head's picture. The face (front-facing texels above the chin) from the painted-face trial, toned to the body
    sheet's skin; his sides from the body sheet's side view (his right; mirrored for his left), the brow and blank eye
    of its profile left out; the neck's front and the back from the body sheet. His hair is not taken: it is painted
    out to skin (hair goes on top later); the scalp is skin, a touch lighter on top."""
    P = np.array(M.P)
    tris = M.tris()
    tf = M.tri_fams()
    head_tris = [t for t, f in zip(tris, tf) if f in ("head", "nose", "ear", "neck")]
    N = normals_of(P, tris)
    pos, nrm, hit, fid = texel_geometry(M, face_uv, "face", P, N)
    size = ATLAS["face"]
    rows_t = body_row(pos[..., 2])
    Nall = nrm.reshape(-1, 3)
    ff = np.clip(-Nall[:, 1], 0, 1)
    fb = np.clip(Nall[:, 1], 0, 1)
    wf = smooth01(0.3, 0.55, ff)
    wb = smooth01(0.3, 0.55, fb) * (1 - wf)
    low = rows_t.ravel() > 378
    share = {"face": wf * ~low, "front": wf * low, "back": wb, "side": (1 - wf) * (1 - wb), "front_ref": wf}
    accs = {k: np.zeros((size * size, 3)) for k in ("face", "body", "front_ref")}
    wsums = {k: np.zeros(size * size) for k in accs}
    side_hole = np.zeros(size * size, bool)
    xs_t = pos[..., 0].ravel()
    for view, mirrored in (("face", False), ("front", False), ("back", False), ("side", False), ("side", True), ("front_ref", False)):
        pview = "front" if view == "front_ref" else view
        pix = sh.face_pix if view == "face" else sh.body_pix
        mask = erode(sh.face_mask if view == "face" else sh.body_mask, 2)
        Q = pos.reshape(-1, 3).copy()
        Nn = nrm.reshape(-1, 3).copy()
        Pm = P.copy()
        if mirrored:
            Q[:, 0] *= -1
            Nn[:, 0] *= -1
            Pm[:, 0] *= -1
        P2, dep = project(pview, Pm)
        zb, _ = raster(P2, dep, head_tris, mask.shape)
        q2, qd = project(pview, Q)
        _, facing = screen_dir(pview, Nn)
        cols = np.clip(q2[:, 0].astype(int), 0, mask.shape[1] - 1)
        rows = np.clip(q2[:, 1].astype(int), 0, mask.shape[0] - 1)
        tol = 0.008 * (1.0 if view != "face" else 1.0)
        seen = (qd <= zb[rows, cols] + tol) & mask[rows, cols] & (facing > 0.05) & hit.ravel()
        colour = pix[rows, cols]
        hair = is_hair(colour)
        if view == "face":
            # (his brows are golden too: kept; above them, and out at the sides, golden is hair)
            hair &= (rows_t.ravel() < 222) | (np.abs(xs_t) > 0.072)
        seen &= ~hair
        if view == "side":
            # (the profile's blank eye and its brow: on his temple they would make a second eye)
            cut = (cols > 1522) & (rows > 236) & (rows < 272)
            side_hole |= seen & cut
            seen &= ~cut
        w = np.where(seen, share[view] * np.clip(facing, 0, 1) + 1e-4 * np.clip(facing, 0, 1), 0.0)
        key = "face" if view == "face" else "front_ref" if view == "front_ref" else "body"
        accs[key] += colour * w[:, None]
        wsums[key] += w
    # The trial paints him lighter and pinker than the body sheet: its colours are toned to the body sheet's, measured
    # on the cheeks (where both see him squarely), so the face meets the sides with no line.
    cheeks = (wsums["face"] > 0.3) & (wsums["front_ref"] > 0.3) & (rows_t.ravel() > 268) & (rows_t.ravel() < 300) & \
             (np.abs(xs_t) > 0.025) & (np.abs(xs_t) < 0.075)
    fa = accs["face"][cheeks] / wsums["face"][cheeks, None]
    fr = accs["front_ref"][cheeks] / wsums["front_ref"][cheeks, None]
    gain = np.median(fr, axis=0) / np.maximum(np.median(fa, axis=0), 1e-3)
    gain = 1.0 + (gain - 1.0) * 0.85
    print("BOY paint face: the trial's colours times %s (%d cheek texels)" % (np.round(gain, 3), int(cheeks.sum())))
    acc = accs["face"] * gain + accs["body"]
    wsum = wsums["face"] + wsums["body"]
    good = (wsum > 0.01).reshape(size, size)
    good &= ~(side_hole.reshape(size, size) & (wf.reshape(size, size) < 0.6))
    rgb = (acc / np.maximum(wsum, 1e-6)[:, None]).reshape(size, size, 3)
    fam_t = np.array([part_family(p) for p in M.fpart] + ["none"])[fid]
    headish = hit & np.isin(fam_t, ("head", "neck"))
    skin_ref = np.median(rgb[good & headish & (rows_t > 268) & (rows_t < 300) & (np.abs(pos[..., 0]) > 0.03)], axis=0)
    # (second round) Where the sheets paint hair, his skin is not taken at all, whatever its colour: the hair's shaded
    # locks and dark edges are no more golden than skin and were left on his scalp as brown streaks. The hairline, by
    # angle round his head from the front (degrees) and sheet row: the bangs' line at the forehead, the temples, the
    # sideburn in front of the ear, over the ear, behind it down to the nape.
    hl_phi = (0.0, 35.0, 55.0, 72.0, 82.0, 95.0, 115.0, 140.0, 180.0)
    hl_row = (221.0, 222.0, 236.0, 262.0, 298.0, 254.0, 300.0, 345.0, 357.0)
    cy = np.interp(pos[..., 2], [M.P[r[0]][2] for r in M.tag["head_rings"]],
                   [float(np.mean([M.P[i][1] for i in r])) for r in M.tag["head_rings"]])
    phi = np.degrees(np.arctan2(np.abs(pos[..., 0]), -(pos[..., 1] - cy)))
    hairline = np.interp(phi, hl_phi, hl_row)
    under_hair = headish & (rows_t < hairline + 3)
    good &= ~under_hair
    # The nose's underside: the trial paints its nostrils seen from the front, and laid on the underside they
    # stretched into a dark band. It is filled from the nose round it, with two small dark nostrils.
    nz = nrm[..., 2]
    nose_under = hit & (fam_t == "nose") & (nz < -0.4)
    good &= ~nose_under
    print("BOY paint face: %d texels under the hair painted as skin; skin %s" % (int(under_hair.sum()), np.round(skin_ref, 3)))
    rgb = fill_out(rgb, good, 200)
    scalp_col = skin_ref[None, :] * (0.98 + 0.05 * np.clip(nz, 0, 1)).reshape(-1)[:, None]
    t = smooth01(hairline - 10.0, hairline + 2.0, rows_t)
    k = (headish & (t < 1.0))
    rgb[k] = rgb[k] * t[k][:, None] + scalp_col.reshape(size, size, 3)[k] * (1.0 - t[k][:, None])
    rgb[nose_under] *= 0.97
    nostril = nose_under & (np.abs(np.abs(pos[..., 0]) - 0.0095) < 0.0045) & (pos[..., 1] > -0.162) & (pos[..., 1] < -0.151)
    rgb[nostril] *= 0.72
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
KNEE_FORM = {1: 0.014, 0: 0.007, 2: 0.007}
ELBOW_FORM = {7: 0.008, 8: 0.008}


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
    for sfx in ("_l", "_r"):
        ring = M.tag["leg_rings" + sfx][LEG_ROWS.index(KNEE_ROW) + 1]
        for j, fwd in KNEE_FORM.items():
            P[ring[j]][1] -= fwd
        # the elbow's point at the back of the arm (the ring at the elbow; ring points 7 and 8 face back)
        st = M.tag["arm_stations" + sfx]
        Lu = st[6]
        ring = M.tag["arm_rings" + sfx][6]
        c = P[ring].mean(0)
        for j, out in ELBOW_FORM.items():
            d = P[ring[j]] - c
            P[ring[j]] += d / max(np.linalg.norm(d), 1e-9) * out
    M.P = [p for p in P]


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


# The face's forms (body-sheet rows, and columns out from the middle, both sides alike; pixels of 1.13 mm): brows
# at row 232, eyes at 256 (42 out), cheeks' apples at 283, the nose's base 309, mouth 330 (a keen closed grin, its
# corners up at 327), chin 362. (row, column, row spread, column spread, metres out along the surface).
FACE_FORMS = (
    # (second round: deeper and firmer, the grey render read as a smooth blob)
    # the brow ridge, soft (a boy's), and the forehead's roundness above it
    (234, 22, 5, 12, 0.006), (232, 46, 5, 14, 0.008), (234, 66, 5, 10, 0.004),
    # the eye sockets under the brow, the eyeball's swell in them, the upper lid's crease and the lower lid
    (256, 43, 9, 19, -0.014), (257, 43, 4.5, 12, 0.0065), (250, 43, 1.6, 13, -0.002), (262, 43, 2.0, 12, 0.0018),
    # the bridge of the nose between the eyes stays up
    (256, 0, 8, 7, 0.004),
    # the cheeks' apples, high and round (the grin lifts them), and the hollow under the cheekbone
    (283, 52, 11, 18, 0.009), (312, 66, 9, 10, -0.004),
    # the nose's wings into the cheeks: the fold to the mouth's corners
    (312, 30, 8, 5, -0.003), (322, 33, 6, 4, -0.0025),
    # the upper lip, the mouth's line (curving up at its corners), the lower lip, the corners' dimples
    (320, 0, 5, 20, 0.005), (331, 0, 1.6, 22, -0.006), (329, 18, 1.6, 7, -0.003), (338, 0, 4, 16, 0.006),
    (327, 27, 3, 4, -0.0035),
    # the groove under the lower lip, the chin's round ball
    (347, 0, 3, 14, -0.004), (362, 0, 7, 16, 0.006),
    # the temples, a little hollow; the jaw's line
    (238, 80, 10, 9, -0.003), (352, 58, 8, 10, 0.002),
)


def sculpt_head(M):
    P = np.array(M.P)
    N = normals_of(P, M.tris())
    row = body_row(P[:, 2])
    col = P[:, 0] / S
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
    fam = [part_family(p) for p in M.fpart]
    Pm = np.array(M.P)
    front = set()
    for fi, f in enumerate(M.faces):
        if fam[fi] not in ("head", "neck"):
            continue
        c = Pm[f].mean(0)
        r = float(body_row(c[2]))
        if 190 <= r <= 400 and c[1] < head_centre(M, c[2])[1] + 0.01:
            front.add(fi)
        # (second round: the skull's top all round too: at 16 points round it came to a peak)
        elif r < 212 and fam[fi] == "head":
            front.add(fi)
    M1, uv1, W1, ch1 = refine(M, front, face_uv, weights)
    P = np.array(M1.P)
    fam1 = [part_family(p) for p in M1.fpart]
    face = set()
    for fi, f in enumerate(M1.faces):
        if fam1[fi] != "head" or len(f) != 4:
            continue
        c = P[f].mean(0)
        r = float(body_row(c[2]))
        # (third round: only the eyes' and the mouth's bands are split a second time; the brow, cheeks and chin are broad
        # forms and the whole figure must stay within about 5,500 triangles)
        band = (238 <= r <= 272 and abs(c[0]) < 0.07) or (314 <= r <= 346 and abs(c[0]) < 0.05)
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

BOXER_BAND = (796.0, 802.0)   # the band's top row at his back and at his front
BOXER_BAND_TALL = 19.0        # sheet pixels (2.1 cm)
BOXER_STAND = (0.013, 0.007, 0.024)   # metres: the cloth, the band, the hems
BOXER_LEG_RINGS = 2
BOXER_HEM_ROW = 1032


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


def build_boxers(M, T, sh, weights, armature):
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
    lower = sorted([r for r in TORSO_ROWS if r >= 885])
    rows_of = []
    for k in range(TORSO_N):
        phi = math.tau * k / TORSO_N
        b = band_row(phi)
        b1 = b + BOXER_BAND_TALL
        mids = [b1 + (870.0 - b1) * t for t in (0.33, 0.66, 1.0)]
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
    sel = sh.body_mask[880:990, 560:790] & is_shorts(sh.body_pix[880:990, 560:790])
    cloth = np.median(sh.body_pix[880:990, 560:790][sel], axis=0) if sel.any() else np.array((0.86, 0.82, 0.72))
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
    inner = np.clip(1.0 - np.abs(pos[..., 0]) / 0.08, 0, 1) * np.clip((body_z(950) - z) / 0.07, 0, 1)
    rgb *= (1.0 - 0.14 * inner)[..., None]
    # (soft shade where the cloth turns away under him and at its sides)
    rgb *= (0.9 + 0.1 * np.clip(nrm[..., 2] + 0.6, 0, 1))[..., None]
    front = pos[..., 1] < -0.04
    ax_ = np.abs(pos[..., 0])
    fly = trunk & front & ~band & (z < zb_) & (z > zb_ - 0.09) & (np.abs(ax_ - 0.018) < 0.0011)
    fly |= trunk & front & (np.abs(z - (zb_ - 0.09)) < 0.0011) & (ax_ < 0.018)
    rgb[fly] *= 0.88
    hem_z = float(body_z(BOXER_HEM_ROW))
    rgb[(fam != "boxers_torso") & hit & (z - hem_z < 0.007)] *= 0.93
    rgb[fam == "boxers_lining"] *= 0.62
    return pad_edges(fill_out(rgb, hit, 64), hit)


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

def finish(M, T, joints, sh):
    H = M.tag["head_rings"]
    bones = skeleton_joints(M, T, joints)
    weights = weights_of(M, T, bones, joints)
    islands = plan_uvs(M, T, H, joints)
    placed, face_uv = pack(islands)
    under = boxer_faces(M, T)
    M, face_uv, weights, under = refine_head(M, face_uv, weights, under)
    # (second round: the refined head smoothed before its forms go in: the rings of the lower face stood as bands)
    hsel = np.array([part_family(p) == "head" for p in M.part])
    hsel[M.tag["head_rings"][0]] = False
    taubin(M, hsel, rounds=3)
    sculpt_head(M)
    os.makedirs(TEX, exist_ok=True)
    for picture in ATLAS:
        write_layout(face_uv, placed, picture, os.path.join(TEX, "boy_%s_layout.png" % picture))
    tris_all = M.tris()
    tf = M.tri_fams()
    P = np.array(M.P)
    no_arms = [t for t, f in zip(tris_all, tf) if f not in ("arm", "hand")]
    Pc, no_arms_c = with_caps(M, P, no_arms)
    skin, spos, shit = paint_skin(M, face_uv, sh, tris_all, Pc, no_arms_c, joints)
    face, fpos, fhit = paint_head(M, face_uv, sh)
    zt = float(np.mean([M.P[i][2] for i in M.tag["head_rings"][0]]))
    near_b = shit & (np.abs(spos[..., 2] - (zt - 0.008)) < 0.008)
    near_h = fhit & (np.abs(fpos[..., 2] - (zt + 0.008)) < 0.008)
    if near_b.any() and near_h.any():
        gain = skin[near_b].mean(0) / np.maximum(face[near_h].mean(0), 1e-3)
        w = (1.0 - smooth01(zt, zt + 0.07, fpos[..., 2])) * fhit
        face = face * (1 + (gain - 1) * w[..., None])
        print("BOY neck tone: the head's neck times %s" % np.round(gain, 3))
    save_rgb(os.path.join(TEX, "boy_skin.png"), skin[::-1])
    save_rgb(os.path.join(TEX, "boy_face.png"), face[::-1])
    armature = make_armature(bones)
    mat_skin = textured_material("boy_skin", os.path.join(TEX, "boy_skin.png"))
    mat_face = textured_material("boy_face", os.path.join(TEX, "boy_face.png"))

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
        loose = [v for v in bm.verts if not v.link_faces]
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
        bm.to_mesh(me)
        bm.free()
        return ob
    # His body, and the skin under the shorts as its own piece (finished skin, hidden by whatever he wears).
    skin_object("boy_body", [i for i in range(len(M.faces)) if i not in under])
    skin_object("boy_body_under", sorted(under))
    Bx = build_boxers(M, T, sh, weights, armature)
    total = report_counts(M)
    print("BOY triangles with the shorts: %d" % (total + len(Bx.tris())))
    zs = P[:, 2]
    print("BOY height: soles %.3f to crown %.3f m (%.3f m)" % (zs.min(), zs.max(), zs.max() - zs.min()))
    print("BOY joints: %s" % json.dumps({n: [round(float(v), 3) for v in p] for n, p, _ in bones if "_" not in n or n.endswith("_l") and not n.startswith(("finger", "thumb"))}))
    objs = [(np.array(M.P), M.tris(), M.tri_fams())]
    Pc, tc = with_caps(M, np.array(M.P), [])
    objs.append((Pc, tc, ["sidecap"] * len(tc)))
    objs.append((np.array(Bx.P), Bx.tris(), ["boxers"] * len(Bx.tris())))
    stats = overlay(objs, sh, "final")
    print("BOY overlay final %s" % json.dumps(stats))
    head_overlay(objs[:1], sh)
    winding_check(M, "body")
    winding_check(Bx, "shorts (open: not a volume)")
    export(armature, GLB)


def main():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sh = Sheets()
    M, T, joints = build_body(sh)
    build_head(M, sh, T[-1])
    dup = [(i, f, M.fpart[i]) for i, f in enumerate(M.faces) if len(set(f)) != len(f)]
    seen_f = {}
    for i, f in enumerate(M.faces):
        seen_f.setdefault(tuple(sorted(f)), []).append(i)
    twice = [v for v in seen_f.values() if len(v) > 1]
    print("BOY faces with a point twice: %d; faces made twice: %d" % (len(dup), len(twice)))
    flipped = fix_winding(M)
    print("BOY built: %d points, %d faces, %d triangles (%d turned outward)" % (len(M.P), len(M.faces), len(M.tris()), flipped))
    body_faces = [f for f, p in zip(M.faces, M.fpart) if part_family(p) not in ("ear", "nose")]
    print("BOY open edges of the body (should be none): %d" % len(open_edges(body_faces)))
    fams = np.array([part_family(p) for p in M.part])
    frozen = np.isin(fams, ("head", "nose", "ear", "neck", "hand"))
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
    smooth_hands(M)
    finish(M, T, joints, sh)


if __name__ == "__main__":
    main()
