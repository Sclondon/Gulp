"""The sea captain, built from his modelling sheets (the fourth attempt, 2026-11-18).

    blender --background --factory-startup --python tools/build_captain.py -- [--out <folder>] [--rounds N]

Writes models/captain.glb, tools/blend/captain.blend, textures/captain/ (his skin and face pictures, each with a layout
picture and a JSON of its islands) and, in --out, the overlay pictures of every fitting round.

The user, of the earlier attempts: "the captain model does not match the conept art", "its deformted". Those were the
shared tall man's mesh squashed by a bone table. This one is built from nothing, the way his head was the one time it
worked:

1. THE SHEETS, MEASURED. tools/art_src/concept_captain_tpose.jpg (front, side, back of his base body at one scale) and
   concept_captain_head.jpg (his head from the front, side and back). Each sheet's figure is cut from its pale ground
   by a flood fill from the edges (the guide lines painted out first); the masks are what everything is measured on.
2. THE BODY, LOFTED. Rings round him, row by row: the torso as one tube of 16 points a ring, as wide as the front view
   and as deep as the side view at that height; each arm a tube of 10 along its own drawn axis (the axis fitted
   through the drawn arm), coming out of a hole in the torso's side; each leg a tube of 10 split from the torso's
   bottom ring at the crotch, going down into the foot as rings round the footprint; hands with a palm, four fingers
   and a thumb; the head as rings from the head sheet, nose lofted down its profile, real ear shapes, the cap's peak.
3. FITTED TO THE SHEET. The body is then pulled onto the sheet's outlines: in each view, every point on the model's
   own outline is moved along its outward direction to the sheet's outline, the move spread smoothly to its
   neighbours, left and right kept alike; repeated (FIT_ROUNDS). Overlays of every round go to --out.
4. HIS OWN SKELETON, with the game's figures' bone names (scripts/title_figures.gd), joints placed in this body;
   weights by where each point lies along its limb, blended across each joint, smoothed.
5. PLANNED UVS: every part is a grid of rings, unwrapped as one (arc length round each ring, distance down the
   rings), seams inside the limbs, under the arms and down the sides; the face its own big island.
6. PAINT: the sheets projected into that layout (each texel from the view that sees it most squarely, and only where
   that view really sees it: a depth test), the tattoos painted out of the skin, unseen places filled from round them.
7. HAIR: beard, moustache, the grey hair under his cap and his chest hair are locks for the hair shader
   (shaders/ink/hair_ink.gdshader): long tapered locks in three layers from the skin out, darker underneath.

Fifth round (the user: "his face and waist need work", "his hands / fingers also seemed scuffed"; a plain grey render
showed the paint carrying every form): forms moved into the mesh (BODY_FORMS: belly roll over the band, navel, love
handles, pecs, knees; FACE_FORMS on a refined head: brow, slit eyes, lids, cheeks, lips; a bigger nose), the head's
skin split once and the face twice after the UVs are planned (refine), the boxers their own garment with a sloping
band and painted hearts (build_boxers, paint_boxers), the hands rebuilt with round fingers as closed tubes, the head's
paint taken from one view at a time (no doubled features), the peak painted the cap's black, head overlays saved.
Sixth round: the hand welded (wrist, wedge palm with heel pads and a knuckle ridge, short fanned fingers and the thumb
grown out of the palm's own faces), the hands painted one even colour, the beard's bottom in five soft points and its
sideburns up to the cap, a deeper belly overhang and stronger pecs, flared boxer legs with a level hem and a side
notch, a fuller nose, deeper eyes and brow.
Seventh round (the user: "The captain model shouldnt have a beard- we will add that on top"; "We should make the
captain model without a hat as well"): he is bare-faced and bare-headed: a modelled jaw, chin, jowls and lips painted
as skin, a bald cranium under the cap; the cap and peak are their own object, `captain_cap`; the beard, moustache and
hair under the cap only with `--hair`, into models/captain_hair.glb. The belly one smooth curve; heavier shoulders
(deltoid, trapezius); the hands smoothed and painted with nails, creases and shaded gaps.

    blender --background --factory-startup --python tools/build_captain.py -- [--out <folder>] [--rounds N] [--hair]

Model space: Blender's, Z up, he faces -Y (the game's +Z after export), +X is his left. Metres. He stands in the
sheet's own pose (arms hanging about 30 degrees out), which is his rest pose.
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
TEX = os.path.join(ROOT, "textures", "captain")
GLB = os.path.join(ROOT, "models", "captain.glb")
HAIR_GLB = os.path.join(ROOT, "models", "captain_hair.glb")
BLEND = os.path.join(HERE, "blend", "captain.blend")

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


OUT = arg("--out", "")
FIT_ROUNDS = int(arg("--rounds", "6"))
HAIR = "--hair" in ARGS          # the beard, moustache and hair under the cap, into HAIR_GLB (off: he is built bare)

# ------------------------------------------------------------------------------------------------------------------
# The sheets
# ------------------------------------------------------------------------------------------------------------------

BODY_SHEET = os.path.join(ART, "concept_captain_tpose.jpg")
HEAD_SHEET = os.path.join(ART, "concept_captain_head.jpg")

# The base-body sheet (pixels of the 2752 by 1536 picture): the soles' row, his cap's top row, and each view's middle
# column (the front's and back's from the torso and the legs, the side's at the ankle) and the columns it spans.
SOLE = 1462.0
CAP_TOP = 106.0
HEIGHT_TO_CAP = 1.68          # metres, soles to the cap's top: he stands about 1.62 m to the crown under it
S = HEIGHT_TO_CAP / (SOLE - CAP_TOP)   # metres a pixel
MID = {"front": 663.0, "side": 1430.0, "back": 2214.0}
SPAN = {"front": (140, 1200), "side": (1250, 1720), "back": (1720, 2740)}
# The boxers (the sheet's base body wears them): the rows they cover, the crotch, and how far they stand off him.
BOXERS = (815, 1060)
CROTCH = 1020
BOXER_EASE = 12               # pixels (1.5 cm): the body under them is this much inside their outline
# The side view has no arm (the painter left a round patch where it would be): those pixels are not painted from.
SIDE_PATCH = ((1318, 455), (1465, 610))

# The head sheet: his head from the front, his left side and the back, at a larger scale. Across and front to back it
# is scaled to the base-body sheet by the cap (its width there, its depth with the peak); up and down by the landmarks
# both sheets show (cap top, band, eyes, nose, mouth, beard's bottom), since the two paintings differ there (the head
# sheet's beard is half again as long).
HEAD_SX = (255.0 * S) / 507.0
HEAD_MID = {"front": 404.0, "side": 1807.5, "back": 2373.0}
HEAD_SPAN = {"front": (100, 720), "side": (1380, 2080), "back": (2080, 2680)}
#                  cap top  band   eyes   nose   mouth  beard  (beyond)
HEAD_ROWS = np.array([135.0, 420.0, 485.0, 595.0, 635.0, 835.0, 1000.0])
BODY_ROWS = np.array([106.0, 240.0, 280.0, 335.0, 358.0, 425.0, 425.0 + 165.0 * HEAD_SX / S])


def head_z(row):
    return (SOLE - np.interp(row, HEAD_ROWS, BODY_ROWS)) * S


def head_row(z):
    return np.interp(SOLE - np.asarray(z) / S, BODY_ROWS, HEAD_ROWS)


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


class Sheets:
    def __init__(self):
        self.body_pix = load_picture(BODY_SHEET)
        self.body_mask = flood_mask(unline(self.body_pix))
        self.head_pix = load_picture(HEAD_SHEET)
        self.head_mask = flood_mask(unline(self.head_pix))
        self.body_target = self._body_target()

    def _body_target(self):
        """The base body's outline as the fitting's target: the boxers drawn in by BOXER_EASE, and under them, from the
        crotch down to their hem, his legs as they are just below it."""
        t = self.body_mask.copy()
        for view in ("front", "back"):
            c0, c1 = SPAN[view]
            mid = MID[view]
            for r in range(BOXERS[0], CROTCH + 1):
                run = run_near(t, r, mid, c0, c1)
                if run and run[0] < mid < run[1]:
                    a, b = run
                    t[r, a:a + BOXER_EASE] = False
                    t[r, b - BOXER_EASE + 1:b + 1] = False
            legs = t[BOXERS[1] + 4, c0:c1].copy()
            for r in range(CROTCH + 1, BOXERS[1] + 4):
                t[r, c0:c1] = legs
        c0, c1 = SPAN["side"]
        # (the side view's waistband slopes: about row 800 at his back, 866 under the belly at his front, where the
        # belly hangs over it; the body is drawn in only under the cloth)
        for r in range(800, BOXERS[1] + 4):
            run = run_near(t, r, MID["side"], c0, c1)
            if run:
                a, b = run
                t[r, a:a + BOXER_EASE] = False
                # (seventh round: drawn in gradually from 850 to 885, not all at once at 866, which cut a shelf
                # under the belly)
                e = int(round(BOXER_EASE * float(smooth01(850.0, 885.0, r))))
                if e > 0:
                    t[r, b - e + 1:b + 1] = False
        return t


# ------------------------------------------------------------------------------------------------------------------
# Views: where a point of him falls in a sheet's picture (continuous pixel coordinates: column, row) and how deep
# ------------------------------------------------------------------------------------------------------------------

def project(view, P):
    """(N,3) model points -> (N,2) picture coordinates and (N,) depth (smaller is nearer the painter)."""
    P = np.asarray(P, dtype=float)
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    if view.startswith("head_"):
        row = head_row(z) + 0.5
        v = view[5:]
        if v == "front":
            return np.stack([HEAD_MID["front"] + x / HEAD_SX + 0.5, row], 1), y
        if v == "back":
            return np.stack([HEAD_MID["back"] - x / HEAD_SX + 0.5, row], 1), -y
        return np.stack([HEAD_MID["side"] + y / HEAD_SX + 0.5, row], 1), -x   # his left side
    row = body_row(z) + 0.5
    if view == "front":
        return np.stack([MID["front"] + x / S + 0.5, row], 1), y
    if view == "back":
        return np.stack([MID["back"] - x / S + 0.5, row], 1), -y
    return np.stack([MID["side"] - y / S + 0.5, row], 1), x                  # his right side


def screen_dir(view, N):
    """Directions in the picture (column, row) of model directions, and how much they face the painter."""
    N = np.asarray(N, dtype=float)
    v = view[5:] if view.startswith("head_") else view
    if v == "front":
        return np.stack([N[:, 0], -N[:, 2]], 1), -N[:, 1]
    if v == "back":
        return np.stack([-N[:, 0], -N[:, 2]], 1), N[:, 1]
    if view.startswith("head_"):
        return np.stack([N[:, 1], -N[:, 2]], 1), N[:, 0]
    return np.stack([-N[:, 1], -N[:, 2]], 1), -N[:, 0]


def world_dir(view, d2):
    """A direction in the picture as a model direction (in the picture's plane)."""
    v = view[5:] if view.startswith("head_") else view
    z = np.zeros(len(d2))
    if v == "front":
        return np.stack([d2[:, 0], z, -d2[:, 1]], 1)
    if v == "back":
        return np.stack([-d2[:, 0], z, -d2[:, 1]], 1)
    if view.startswith("head_"):
        return np.stack([z, d2[:, 0], -d2[:, 1]], 1)
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


# ------------------------------------------------------------------------------------------------------------------
# The body, measured off the sheet
# ------------------------------------------------------------------------------------------------------------------

TORSO_N = 16
LIMB_N = 10
# The torso's rings (sheet rows, from the crotch up) and which of them hold the arm's hole (4 rings: armpit to top).
# (fifth round: more rings round the belly's overhang over the waistband and under the pecs, for the forms the user
# found missing in a plain grey render: "the texture has been carrying everything")
TORSO_ROWS = [1020, 990, 955, 915, 885, 868, 855, 842, 826, 808, 790, 772, 755, 715, 668, 642, 615, 566, 525, 485, 445, 425, 405]
_H0 = TORSO_ROWS.index(566)
HOLE = (_H0, _H0 + 1, _H0 + 2, _H0 + 3)
HOLE_COLS = (3, 4, 5)
# Where the side view's front is the beard (rows above it): the chest's front there (metres, y), up to the neck.
CHEST_UNDER_BEARD = {445: -0.138, 425: -0.118, 405: -0.092}
# The torso's half width where the arms hide it in the front view (metres), by row.
TORSO_UNDER_ARMS = {642: 0.262, 615: 0.262, 566: 0.258, 525: 0.25, 485: 0.24, 445: 0.225, 425: 0.2, 405: 0.158}
# Shoulder joint row, elbow row, wrist row (the arm's axis is fitted through the drawn arm in the front view).
SHOULDER_ROW, ELBOW_ROW, WRIST_ROW = 505, 700, 862
ARM_ROOT_R = 0.094            # the radius of the arm's root ring (where it comes out of the torso)
ARM_Y = (0.0, -0.035)         # the arm's axis front to back, at the shoulder and at the wrist (the side view has none)
# How deep each arm ring is for how wide it is, along the arm (deltoid, upper arm, elbow, forearm, wrist).
ARM_DEPTH = ((0.0, 1.05), (0.12, 1.0), (0.24, 0.9), (0.3, 0.88), (0.4, 1.0), (0.52, 1.15))
# The legs: rows of their rings (from the crotch down), the hip joint, the knee and the ankle.
LEG_ROWS = [1040, 1065, 1100, 1140, 1180, 1215, 1250, 1290, 1322, 1350]
HIP_ROW, KNEE_ROW, ANKLE_ROW = 978, 1215, 1352
HIP_X = 0.118
FOOT_YAW = math.radians(24.0)     # toes out
TOE_REACH = 1.06                  # the toes' end a little further forward than stage one's
# The foot's rings below the ankle: height, how far it reaches forward of the ankle, back, and to each side.
FOOT_RINGS = ((0.100, 0.060, 0.058, 0.050), (0.068, 0.125, 0.072, 0.056), (0.036, 0.25, 0.08, 0.068),
              (0.013, 0.246, 0.076, 0.064), (0.0, 0.232, 0.064, 0.054))


def measure_torso(sh):
    """Each torso ring: (z, half-width, front y, back y)."""
    m = sh.body_mask
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
        if r in CHEST_UNDER_BEARD:
            yf = CHEST_UNDER_BEARD[r]
        rings.append((float(body_z(r)), a, yf, yb))
    return rings


def arm_axis(sh):
    """The drawn arm's axis in the front view (his left arm, the right mirrored onto it, and the back view's too):
    shoulder, elbow and wrist points (metres)."""
    m = sh.body_mask
    pts = []
    for r in range(680, 870, 6):
        cs = []
        for view, sign in (("front", 1), ("front", -1), ("back", 1), ("back", -1)):
            c0, c1 = SPAN[view]
            mid = MID[view]
            rs = runs_of(m[r], c0, c1)
            # the arm: the outermost run on that side
            side = [x for x in rs if (x[0] > mid if sign * (1 if view == "front" else -1) > 0 else x[1] < mid)]
            if not side:
                continue
            run = max(side, key=lambda x: x[1]) if (sign * (1 if view == "front" else -1)) > 0 else min(side, key=lambda x: x[0])
            centre = (run[0] + run[1] + 1) / 2.0
            x = (centre - mid) * S if view == "front" else -(centre - mid) * S
            cs.append(abs(x))
        if cs:
            pts.append((r, float(np.median(cs))))
    rows = np.array([p[0] for p in pts], float)
    xs = np.array([p[1] for p in pts])
    up = rows < 765
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
                # (merged with the torso: from the axis out to the outer edge)
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
            col = mid + sign * 0.155 / S if view == "front" else mid - sign * 0.155 / S
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
        p = 0.72 if TORSO_ROWS[i] > 668 else 0.78
        pts = ring_points(0.0, cy, z, a, d, d, TORSO_N, p)
        T.append([M.add(q, "torso") for q in pts])
    M.tag["torso_rings"] = T
    for i in range(len(T) - 1):
        lower, upper = T[i], T[i + 1]
        for k in range(TORSO_N):
            j = (k + 1) % TORSO_N
            # (the arm's holes: two columns by three rings on each side, left out)
            if i in (HOLE[0], HOLE[1], HOLE[2]) and (k in (3, 4) or k in (11, 12)):
                continue
            M.face([lower[k], lower[j], upper[j], upper[k]], "torso")
            M.cell[len(M.faces) - 1] = ("torso", i, k)
    # The crotch: one point between the legs, under the bottom ring's middle.
    z0, a0, yf0, yb0 = rings[0]
    crotch = M.add((0.0, (yf0 + yb0) / 2.0 + 0.01, z0 - 0.012), "torso")
    M.tag["crotch"] = [crotch]

    joints = {}
    shoulder, elbow, wrist = arm_axis(sh)
    joints.update(shoulder_l=shoulder, elbow_l=elbow, wrist_l=wrist)
    print("CAPTAIN arm: shoulder %s elbow %s wrist %s" % (tuple(round(v, 3) for v in shoulder), tuple(round(v, 3) for v in elbow), tuple(round(v, 3) for v in wrist)))

    for side in (1, -1):
        arm(M, sh, T, side, shoulder, elbow, wrist, joints)
        leg(M, sh, T, rings, crotch, side, joints)
    return M, T, joints


def mirror_x(p, side):
    return np.array((p[0] * side, p[1], p[2]))


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
    # The hole's ring: a circle round the shoulder, in a plane half way between the arm's way and straight out.
    N = (Du + X).normalized()
    U = (Vector((0, 0, 1)) - N * N.z).normalized()
    Fh = F - N * N.dot(F)
    Fh.normalize()
    centre = J + N * 0.03
    (ra, rb, rc, rd) = [T[i] for i in HOLE]
    c3, c4, c5 = (col_of(k, side) for k in HOLE_COLS)
    hole = [rd[c4], rd[c3], rc[c3], rb[c3], ra[c3], ra[c4], ra[c5], rb[c5], rc[c5], rd[c5]]
    M.tag["hole" + sfx] = hole
    for j, v in enumerate(hole):
        ph = math.tau * j / LIMB_N
        q = centre + (U * math.cos(ph) + Fh * math.sin(ph)) * ARM_ROOT_R
        M.P[v] = mirror_x(q, side)
        M.part[v] = "shoulder" + sfx
    # The arm's rings along its axis (distance s from the shoulder).
    Lu, Lf = (E - J).length, (W - E).length
    stations = [0.035, 0.08, 0.13, 0.18, Lu - 0.03, Lu, Lu + 0.035, Lu + 0.09, Lu + 0.15, Lu + Lf - 0.035, Lu + Lf]
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
        # (sixth round: the forearm narrows into the wrist; measured off the sheet, its last rings took the hand's
        # width and stood as a square cuff over the palm)
        if s > Lu + Lf - 0.05:
            a = min(a, 0.047 if s < Lu + Lf - 0.01 else 0.04)
        b = a * depth_ratio(s)
        # (seventh round, the user: "his shoulders need a little work": a heavy round deltoid over the top of the arm,
        # fuller out and a little forward; the upper arm's bulk under it)
        dl = math.exp(-((s - 0.06) / 0.05) ** 2)
        a *= 1.0 + 0.2 * dl
        b *= 1.0 + 0.16 * dl
        C = C + A * (0.009 * dl) + F * (0.002 * dl) + Vector((0, 0, 0.006 * dl))
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


def hand(M, wrist_ring, side, W, L, joints):
    """A hand hanging from the wrist ring, after the hands sheet (concept_captain_hands_wheel.jpg) and the base body's
    hands. Sixth round (the coordinator, of the grey render: "four sausages and a thumb poking out of a square forearm
    stump: no palm, no wrist, a hard rectangular cuff, fingers parallel and too long, tips pointed"), one welded
    surface the usual low-poly way, every ring of 10 points (the arm's):
    - the wrist: a ring narrower than the forearm's end;
    - the palm, a wedge: thick at the heel (with the pads at the thumb's and the little finger's side), wider and
      thinner at the knuckles, with a ridge across the back there;
    - the palm's end is four quads across (its ring's five back points against its five palm points); each finger
      grows out of one of them (4 points to a ring of 8, then rings of 8), short and thick, different lengths (the
      middle longest, the little shortest), a little fanned, gently curled, ending blunt with a flat nail on the back;
    - the thumb grows the same way out of the palm's side face between the heel and the middle of the palm, from a fat
      base pad, forward and in.
    Its back faces out and a little forward (36 degrees round from straight out), as the sheet has his hands hang."""
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
        for j, w, lb, pd in zip(back, across, back_lift, palm_drop):
            edge = abs(w) == 1.0
            pts[j] = at + Wd * (w * hw * (0.9 if edge else 1.0)) + Tb * (ht * (0.72 if edge else 1.0) + lb)
        for j, w, pd in zip(palm, across, palm_drop):
            edge = abs(w) == 1.0
            pts[j] = at + Wd * (w * hw * (0.9 if edge else 1.0)) - Tb * (ht * (0.72 if edge else 1.0) + pd)
        return [M.add(mirror_x(q, side), part) for q in pts]

    def bridge(a, b, pt=part):
        M.bridge(a, b, pt) if side > 0 else M.bridge(b, a, pt)
    # wrist, heel (pads), mid palm, knuckles (the ridge)
    r0 = ring_at(W + L * 0.012, 0.036, 0.023)
    r1 = ring_at(W + L * 0.04, 0.045, 0.027, palm_drop=(0.006, 0.003, 0.0, 0.003, 0.005))
    r2 = ring_at(W + L * 0.075, 0.05, 0.024, palm_drop=(0.002, 0.0, 0.0, 0.0, 0.002))
    knuck = W + L * 0.103
    r3 = ring_at(knuck, 0.053, 0.019, back_lift=(0.002, 0.004, 0.004, 0.004, 0.002))
    bridge(wrist_ring, r0)
    bridge(r0, r1)
    bridge(r1, r2)
    bridge(r2, r3)
    # the thumb's root: the palm's side face between the heel and the middle, on the thumb's side (taken out)
    thumb_root = [r1[3], r2[3], r2[4], r1[4]]
    target = sorted(thumb_root)
    for fi in range(len(M.faces) - 1, -1, -1):
        if sorted(M.faces[fi]) == target:
            del M.faces[fi]
            del M.fpart[fi]
            break
    M.tag["hand_rings" + sfx] = [wrist_ring, r0, r1, r2, r3]

    def grow(name, root, frames, tip_at, pname):
        """A finger out of a root quad (4 points: the corners at angles a0, a0 -/+ 90...) into rings of 8: frames is
        a list of (centre, across, back, half-width, half-height, back lift); ring point j at angle a0 + step * j.
        The quad's corners are the ring's points 0, 2, 4, 6."""
        a0, step = frames[0]
        rings = []
        for at, ac, bk, hw, ht, lift in frames[1:]:
            ring = []
            for j in range(8):
                a = math.radians(a0 + step * j)
                s_, c_ = math.sin(a), math.cos(a)
                q = at + ac * (c_ * hw) + bk * (s_ * ht + (lift if s_ > 0.9 else 0.0))
                ring.append(M.add(mirror_x(q, side), pname))
            rings.append(ring)
        # root quad -> first ring of 8: three triangles an edge
        R, Q = root, rings[0]
        for i in range(4):
            a, b = R[i], R[(i + 1) % 4]
            q0, q1, q2 = Q[2 * i], Q[2 * i + 1], Q[(2 * i + 2) % 8]
            M.face([a, b, q1], pname)
            M.face([a, q1, q0], pname)
            M.face([b, q2, q1], pname)
        for a, b in zip(rings, rings[1:]):
            M.bridge(a, b, pname)
        tip = M.add(mirror_x(tip_at, side), pname)
        last = rings[-1]
        for j in range(8):
            M.face([last[j], last[(j + 1) % 8], tip], pname)
        M.tag["finger_rings%s_%s" % (sfx, name)] = rings
        M.tag["finger_ends%s_%s" % (sfx, name)] = [tip, -1]

    # name, which root quad (0 the thumb's side), length, half-width, spread (degrees toward the little finger)
    fingers = (("index", 0, 0.058, 0.0122, -6.0), ("middle", 1, 0.064, 0.0128, -1.5),
               ("ring", 2, 0.06, 0.0122, 3.0), ("little", 3, 0.049, 0.0108, 8.0))
    curl = (0.16, 0.26, 0.2)
    segs = (0.45, 0.3, 0.25)
    for name, i, length, hw, spread in fingers:
        root = [r3[back[i]], r3[back[i + 1]], r3[palm[i + 1]], r3[palm[i]]]
        k0 = knuck + Wd * (across[i] + across[i + 1]) / 2.0 * 0.053
        way = Matrix.Rotation(math.radians(spread), 3, Tb) @ L.copy()
        ac, bk = Wd.copy(), Tb.copy()
        # corners: thumb-side back (45), little-side back (135), little-side palm (225), thumb-side palm (315)
        frames = [(45.0, 45.0)]
        at = k0 + way * 0.006
        frames.append((at.copy(), ac.copy(), bk.copy(), hw * 1.06, hw * 0.98, 0.003))      # the knuckle
        bones = [k0.copy()]
        for si, f in enumerate(segs):
            rot = Matrix.Rotation(-curl[si], 3, ac)
            way = rot @ way
            bk = rot @ bk
            at = at + way * (length * f)
            bones.append(at.copy())
            if si < 2:
                taper = (0.98, 0.93)[si]
                frames.append((at.copy(), ac.copy(), bk.copy(), hw * taper * 1.04, hw * taper * 0.9, 0.0015))
                frames.append((at + way * (length * segs[si + 1] * 0.5), ac.copy(), bk.copy(), hw * taper * 0.97, hw * taper * 0.84, 0.0))
        # the end: blunt, its back flat (the nail), then closed round the fingertip's pad
        frames.append((at - way * 0.006, ac.copy(), bk.copy(), hw * 0.9, hw * 0.74, -0.001))
        frames.append((at + way * 0.0005, ac.copy(), bk.copy(), hw * 0.68, hw * 0.5, -0.0015))
        grow(name, root, frames, at + way * 0.0032 - bk * 0.0015, part + "_" + name)
        joints["%s%s" % (name, sfx)] = [Vector(mirror_x(b, side)) for b in bones]
    # The thumb, out of the side face. Its frame: U along the palm (heel to knuckles), V toward the back of the hand;
    # the root quad's corners r1[3] (U-, V+) 135, r2[3] (U+, V+) 45, r2[4] (U+, V-) 315, r1[4] (U-, V-) 225: the ring
    # runs 135, 90, 45 ... downward.
    rootc = sum((Vector(mirror_x(M.P[v], side)) for v in thumb_root), Vector()) / 4.0
    way = (Wd * 0.78 + L * 0.5 - Tb * 0.38).normalized()
    U = (L - way * L.dot(way)).normalized()
    V = way.cross(U).normalized()
    if V.dot(Tb) < 0:
        V = -V
    frames = [(135.0, -45.0)]
    at = rootc + way * 0.014
    frames.append((at.copy(), U.copy(), V.copy(), 0.022, 0.019, 0.0))                # the fat base pad
    bones = [rootc.copy()]
    for si, (f, rad) in enumerate(((0.42, 0.0185), (0.32, 0.0165), (0.26, 0.015))):
        rot = Matrix.Rotation(-0.18, 3, U.cross(way).normalized())
        way = rot @ way
        U = rot @ U
        V = rot @ V
        at = at + way * (0.072 * f)
        bones.append(at.copy())
        if si < 2:
            frames.append((at.copy(), U.copy(), V.copy(), rad, rad * 0.88, 0.0012))
    frames.append((at - way * 0.006, U.copy(), V.copy(), 0.0135, 0.011, -0.001))
    frames.append((at + way * 0.0005, U.copy(), V.copy(), 0.0098, 0.0075, -0.0015))
    grow("thumb", thumb_root, frames, at + way * 0.0035, part + "_thumb")
    joints["thumb%s" % sfx] = [Vector(mirror_x(b, side)) for b in bones]
    joints["thumb_back%s" % sfx] = np.array(mirror_x(V, side))
    joints["hand_frame%s" % sfx] = tuple(np.array(mirror_x(v, side)) for v in (Tb, Wd, L))
    joints["knuckles%s" % sfx] = Vector(mirror_x(knuck, side))


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
    joints["ball" + sfx] = Vector(mirror_x(Vector((ax, ay, 0.025)) + fwd * 0.12, side))
    joints["toe_tip" + sfx] = Vector(mirror_x(Vector((ax, ay, 0.02)) + fwd * 0.2, side))


# ------------------------------------------------------------------------------------------------------------------
# The head, measured off the head sheet
# ------------------------------------------------------------------------------------------------------------------

# The head's rings (head-sheet rows, from the chin up to the cap's band), then the bare skull above it (seventh round,
# the user: "We should make the captain model without a hat as well"): the cap and its peak are their own piece
# (build_cap), sitting on a finished cranium.
HEAD_RING_ROWS = [730, 690, 645, 605, 565, 525, 488, 455, 425]
# The skull's rings above the band (head-sheet rows; the crown's point at SKULL_TOP). An old man's head: the eyes about
# half way between chin and crown, so the crown is about as far above the eyes as the chin is below them; it rises
# inside the cap's puffed crown.
SKULL_ROWS = [402, 378, 350, 320, 292, 270]
SKULL_TOP = 252.0
SKULL_IN = 0.002              # metres: the skull at the band is this far inside the band's outline (the cap's cloth)
# The cap's rings (its band's bottom, the band, the crown's sides up to its top), measured off the head sheet.
CAP_ROWS = [425, 395, 355, 315, 270, 225, 185, 155]
CAP_OUT = 0.002               # the cap stands this far outside the band's outline (it sits on him)
# The head's half width behind the ears and the jaw (head-sheet pixels), by row. (seventh round: the true jaw, bare,
# heavy jowls into a thick neck; the beard's narrowing is undone)
SKULL_HALF = {455: 205.0, 488: 207.0, 525: 208.0, 565: 204.0, 605: 198.0, 645: 188.0, 690: 168.0, 730: 130.0}
# The bare face's front below the nose (seventh round; the sheet's beard hides it): the head sheet's side-view column
# of his face's front by row: the upper lip, the lips, the chin (a strong one), under the chin into the throat.
BARE_FRONT = {605: 1479.0, 645: 1483.0, 690: 1492.0, 730: 1580.0}
JAW_TAPER = {645: 0.1, 690: 0.26, 730: 0.4}
FACE_PLANE = (468, 600)       # rows where the side view's front is the nose: the face's front taken straight between
PEAK_ROWS = (318, 420)        # rows where the side view's front is the cap's peak
PEAK_FRONT_COL = 1512.0       # the cap's band's front there
HAIR_BACK = 0.008             # the grey hair at the back of his head stands this far off the skin (it is hair)
# (fifth round: wider, a big round bulb and flared wings, as the head sheet's front view paints it: the grey render
# showed "a small pinched cone")
NOSE = ((470, 58.0), (490, 78.0), (510, 100.0), (530, 122.0), (548, 134.0), (564, 138.0), (580, 130.0), (594, 104.0))
NOSE_WINGS = ((540, 0.0), (560, 0.2), (578, 0.32), (594, 0.26))   # extra width toward the face, by row (share)
EAR_ROWS = (452, 612)         # the ear's top and bottom in the head sheet
EAR_COLS = (1790, 1866)       # its front and back in the side view
EAR_OUT = 0.026               # how far its rim stands out from the head


def head_measure(sh, rows=None):
    m = sh.head_mask
    rings = []
    for r in (rows or HEAD_RING_ROWS):
        if r in SKULL_HALF:
            hw = SKULL_HALF[r] * HEAD_SX
        else:
            ws = []
            for view in ("front", "back"):
                c0, c1 = HEAD_SPAN[view]
                run = run_near(m, r, HEAD_MID[view], c0, c1)
                ws.append((run[1] + 1 - run[0]) / 2.0)
            hw = float(np.mean(ws)) * HEAD_SX
        c0, c1 = HEAD_SPAN["side"]
        run = run_near(m, r, HEAD_MID["side"], c0, c1)
        front, back = float(run[0]), float(run[1] + 1)
        if PEAK_ROWS[0] <= r <= PEAK_ROWS[1]:
            front = max(front, PEAK_FRONT_COL)
        yf = (front - HEAD_MID["side"]) * HEAD_SX
        yb = (back - HEAD_MID["side"]) * HEAD_SX
        if FACE_PLANE[0] <= r <= FACE_PLANE[1]:
            ra = run_near(m, FACE_PLANE[0] - 2, HEAD_MID["side"], c0, c1)
            rb = run_near(m, FACE_PLANE[1] + 4, HEAD_MID["side"], c0, c1)
            fa = (ra[0] - HEAD_MID["side"]) * HEAD_SX
            fb = (rb[0] - HEAD_MID["side"]) * HEAD_SX + 0.012
            t = (r - FACE_PLANE[0]) / (FACE_PLANE[1] - FACE_PLANE[0])
            yf = fa + (fb - fa) * t
        if r in BARE_FRONT:
            yf = (BARE_FRONT[r] - HEAD_MID["side"]) * HEAD_SX
        if 420 <= r <= 730:
            yb -= HAIR_BACK
        rings.append((float(head_z(r)), hw, yf, yb, JAW_TAPER.get(r, 0.0)))
    return rings


def skull_measure(band):
    """The skull's rings above the band: an egg rounding from the band's ring (drawn in by SKULL_IN) to the crown,
    the back fuller than the front (an old man's cranium), its middle a little back as it rises."""
    z0, hw0, yf0, yb0, _ = band
    hw0, yf0, yb0 = hw0 - SKULL_IN, yf0 + SKULL_IN, yb0 - SKULL_IN
    cy0, d0 = (yf0 + yb0) / 2.0, (yb0 - yf0) / 2.0
    zt = float(head_z(SKULL_TOP))
    out = []
    for r in SKULL_ROWS:
        z = float(head_z(r))
        t = (z - z0) / (zt - z0)
        k = (1.0 - t ** 2.3) ** (1.0 / 2.3)
        cy = cy0 + 0.018 * t ** 1.5
        out.append((z, hw0 * k, cy - d0 * k * (1.0 - 0.06 * t), cy + d0 * k, 0.0))
    return out, (hw0, yf0, yb0)


def build_head(M, sh, top_ring):
    """The head's rings bridged onto the torso's top ring, up the face to the band, the bare skull above it to the
    crown; then the nose and ears as shells of their own. (The cap and its peak: build_cap.)"""
    rings = head_measure(sh)
    skull, band_in = skull_measure(rings[-1])
    prev = top_ring
    H = []
    allr = rings[:-1] + [(rings[-1][0], band_in[0], band_in[1], band_in[2], 0.0)] + skull
    for i, (z, hw, yf, yb, taper) in enumerate(allr):
        cy, d = (yf + yb) / 2.0, (yb - yf) / 2.0
        p = 0.82 if i < len(rings) else 0.85
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
    top = M.add((0.0, allr[-1][2] * 0.5 + allr[-1][3] * 0.5 + 0.004, float(head_z(SKULL_TOP))), "head")
    for k in range(TORSO_N):
        j = (k + 1) % TORSO_N
        M.face([prev[k], prev[j], top], "head")
        M.cell[len(M.faces) - 1] = ("head", len(allr) - 1, k)
    M.tag["head_rings"] = H
    M.tag["band_ring"] = [H[len(rings) - 1]]
    nose(M, sh, rings)
    for side in (1, -1):
        ear(M, sh, rings, side)
    return rings


def face_front_at(rings, z):
    zs = [r[0] for r in rings]
    ys = [r[2] for r in rings]
    return float(np.interp(z, zs, ys))


def nose(M, sh, rings):
    """The nose lofted down the side view's profile, as wide as the front view paints it at each row."""
    m = sh.head_mask
    c0, c1 = HEAD_SPAN["side"]
    rows = list(range(NOSE[0][0], NOSE[-1][0] + 1, 10))
    if rows[-1] != NOSE[-1][0]:
        rows.append(NOSE[-1][0])
    loops = []
    n = 12
    for r in rows:
        run = run_near(m, r, HEAD_MID["side"], c0, c1)
        tip = (run[0] - HEAD_MID["side"]) * HEAD_SX
        z = float(head_z(r))
        base = face_front_at(rings, z) + 0.014
        half = float(np.interp(r, [a for a, _ in NOSE], [w for _, w in NOSE])) / 2.0 * HEAD_SX
        wings = float(np.interp(r, [a for a, _ in NOSE_WINGS], [w for _, w in NOSE_WINGS]))
        cy, d = (tip + base) / 2.0, max((base - tip) / 2.0, 0.003)
        pts = ring_points(0.0, cy, z, half, d, d, n, 1.0)
        # (the wings: wider toward the face, where the nostrils flare)
        pts = [(x * (1.0 + wings * float(np.clip((y - cy) / d + 0.3, 0.0, 1.0))), y, zz) for x, y, zz in pts]
        loop = [M.add(q, "nose") for q in pts]
        loops.append(loop)
    for a, b in zip(loops, loops[1:]):
        M.bridge(a, b, "nose")
    # (closed underneath: the nostrils' floor)
    last = loops[-1]
    zc = M.P[last[0]][2] - 0.004
    c = M.add((0.0, float(np.mean([M.P[i][1] for i in last])), zc), "nose")
    for j in range(n):
        k = (j + 1) % n
        M.face([last[j], last[k], c], "nose")
    first = loops[0]
    c = M.add((0.0, float(np.mean([M.P[i][1] for i in first])) + 0.004, M.P[first[0]][2] + 0.006), "nose")
    for j in range(n):
        k = (j + 1) % n
        M.face([first[k], first[j], c], "nose")
    M.tag["nose_tip_z"] = [float(head_z(min(range(NOSE[0][0], NOSE[-1][0]), key=lambda r: run_near(m, r, HEAD_MID["side"], c0, c1)[0])))]


# An ear's outline (b: back from where it joins the head, v: up), and how far each point stands out (0..1).
EAR_RIM = ((0.25, 1.0, 0.7), (0.62, 0.92, 1.0), (0.9, 0.66, 1.0), (0.86, 0.38, 0.9), (0.62, 0.12, 0.7),
           (0.38, -0.02, 0.55), (0.12, 0.05, 0.35), (0.0, 0.3, 0.1), (0.02, 0.62, 0.15), (0.08, 0.88, 0.4))


def ear(M, sh, rings, side):
    """A real ear: a rim standing out from the head, a hollow bowl inside it, a back wall to the skull."""
    part = "ear_l" if side > 0 else "ear_r"
    zt, zb = float(head_z(EAR_ROWS[0])), float(head_z(EAR_ROWS[1]))
    y0 = (EAR_COLS[0] - HEAD_MID["side"]) * HEAD_SX
    y1 = (EAR_COLS[1] - HEAD_MID["side"]) * HEAD_SX
    zc = (zt + zb) / 2.0
    # the skull's side there
    zs = [r[0] for r in rings]
    hw = float(np.interp(zc, zs, [r[1] for r in rings]))
    hgt, wid = zt - zb, y1 - y0
    tilt = math.radians(14.0)       # the top leans back
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
    for j in range(n):
        k = (j + 1) % n
        M.face([rim[j], rim[k], bowl[k], bowl[j]], part, out)
        M.face([bowl[j], bowl[k], centre], part, out)
        M.face([rim[k], rim[j], wall[j], wall[k]], part, away)
    M.tag["earlobe" + ("_l" if side > 0 else "_r")] = [rim[5]]


def peak(M, sh, rings):
    """The cap's peak: a curved slab from the band's front out to the side view's tip, sloping down."""
    m = sh.head_mask
    c0, c1 = HEAD_SPAN["side"]
    tip_row = min(range(330, 410), key=lambda r: run_near(m, r, HEAD_MID["side"], c0, c1)[0])
    tip_y = (run_near(m, tip_row, HEAD_MID["side"], c0, c1)[0] - HEAD_MID["side"]) * HEAD_SX
    root_y = (PEAK_FRONT_COL - HEAD_MID["side"]) * HEAD_SX + 0.03
    z_root = float(head_z(398))
    z_tip = float(head_z(tip_row + 10))
    hw = float(np.interp(z_root, [r[0] for r in rings], [r[1] for r in rings])) * 0.98
    n = 9
    top, bot = [], []
    for j in range(n):
        a = math.pi * j / (n - 1)           # round the front, from his right to his left
        x = -math.cos(a) * hw
        reach = (root_y - tip_y) * math.sin(a) ** 0.8
        y = root_y - reach - 0.02 * (1 - math.sin(a))
        f = reach / max(root_y - tip_y, 1e-6)
        z = z_root + (z_tip - z_root) * f - 0.004 * math.sin(a)
        top.append(M.add((x, y, z + 0.006), "peak"))
        bot.append(M.add((x, y + 0.008, z - 0.008), "peak"))
    back_t, back_b = [], []
    for j in range(n):
        a = math.pi * j / (n - 1)
        x = -math.cos(a) * hw * 0.97
        y = root_y + 0.045 * math.sin(a) ** 0.5
        back_t.append(M.add((x, y, z_root + 0.008), "peak"))
        back_b.append(M.add((x, y, z_root - 0.011), "peak"))
    root = np.array((0.0, root_y + 0.03, z_root))

    def outward(c, root=root):
        d = np.array(c) - root
        d[2] = 0.0
        return d
    for j in range(n - 1):
        M.face([back_t[j], back_t[j + 1], top[j + 1], top[j]], "peak", np.array((0.0, -0.3, 1.0)))
        M.face([bot[j], bot[j + 1], back_b[j + 1], back_b[j]], "peak", np.array((0.0, 0.3, -1.0)))
        M.face([top[j], top[j + 1], bot[j + 1], bot[j]], "peak", outward)
    M.face([back_t[0], top[0], bot[0], back_b[0]], "peak", np.array((-1.0, 0.0, 0.0)))
    M.face([top[-1], back_t[-1], back_b[-1], bot[-1]], "peak", np.array((1.0, 0.0, 0.0)))


def build_cap(sh):
    """The cap (seventh round: its own piece, `captain_cap`, so the game can take it off): the band and the puffed
    crown measured off the head sheet as before, stood CAP_OUT outside it, with a lining turned in under the band's
    edge (into the head, so no gap shows from below) and the peak. Gives the Mesh and its outer rings."""
    Cm = Mesh()
    meas = head_measure(sh, CAP_ROWS)
    rings = []
    for i, (z, hw, yf, yb, _) in enumerate([(float(head_z(427)),) + meas[0][1:]] + meas[1:]):
        hw, yf, yb = hw + CAP_OUT, yf - CAP_OUT, yb + CAP_OUT
        cy, d = (yf + yb) / 2.0, (yb - yf) / 2.0
        rings.append([Cm.add(q, "cap") for q in ring_points(0.0, cy, z, hw, d, d, TORSO_N, 0.78)])
    for i in range(len(rings) - 1):
        for k in range(TORSO_N):
            j = (k + 1) % TORSO_N
            Cm.face([rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]], "cap")
            Cm.cell[len(Cm.faces) - 1] = ("cap", i, k)
    last = rings[-1]
    zt = float(head_z(137))
    top = Cm.add((0.0, float(np.mean([Cm.P[v][1] for v in last])), zt), "cap")
    for k in range(TORSO_N):
        Cm.face([last[k], last[(k + 1) % TORSO_N], top], "cap")
        Cm.cell[len(Cm.faces) - 1] = ("cap", len(rings) - 1, k)
    # the lining: in under the band's edge and up inside him
    b0 = np.array([Cm.P[v] for v in rings[0]])
    c0 = b0.mean(0)
    inner = []
    for p in b0:
        q = c0 + (p - c0) * np.array((1.0, 1.0, 0.0)) * 0.9
        inner.append(Cm.add((q[0], q[1], p[2] + 0.004), "cap_lining"))
    hidden = Cm.add((c0[0], c0[1], c0[2] + 0.06), "cap_lining")
    for k in range(TORSO_N):
        j = (k + 1) % TORSO_N
        Cm.face([rings[0][j], rings[0][k], inner[k], inner[j]], "cap_lining")
        Cm.face([inner[j], inner[k], hidden], "cap_lining")
    peak(Cm, sh, meas)
    flipped = fix_winding(Cm)
    print("CAPTAIN cap: %d triangles (%d turned outward), open edges %d" % (len(Cm.tris()), flipped,
          len(open_edges([f for f, p in zip(Cm.faces, Cm.fpart) if p != "peak"]))))
    Cm.tag["rings"] = rings
    return Cm


def cap_object(Cm, sh, armature):
    """The cap's UVs (its side front and back as grids, the crown into them, the lining and peak flat), its picture
    painted from the head sheet's views (the peak and lining their own black), and its Blender object, all on the
    head's bone."""
    rings = Cm.tag["rings"]
    front = [fi for fi, c in Cm.cell.items() if (c[2] >= 12 or c[2] < 4)]
    back = [fi for fi, c in Cm.cell.items() if 4 <= c[2] < 12]
    side_front = [fi for fi in front if Cm.cell[fi][1] < len(rings) - 1]
    side_back = [fi for fi in back if Cm.cell[fi][1] < len(rings) - 1]
    islands = {"cap_front": grid_uvs(Cm, rings, side_front, 12, up=True),
               "cap_back": {fi: [(-u, v) for u, v in uv] for fi, uv in grid_uvs(Cm, rings, side_back, 4, up=True).items()}}
    for key, fan in (("cap_front", [fi for fi in front if fi not in side_front]),
                     ("cap_back", [fi for fi in back if fi not in side_back])):
        known = {}
        for fi, uv in islands[key].items():
            for v, q in zip(Cm.faces[fi], uv):
                known.setdefault(v, q)
        vmax = max(q[1] for q in known.values())
        for fi in fan:
            us = [known[w][0] for w in Cm.faces[fi] if w in known]
            islands[key][fi] = [known[w] if w in known else (float(np.mean(us)), vmax + 0.04) for w in Cm.faces[fi]]
    lining = [fi for fi, p in enumerate(Cm.fpart) if p == "cap_lining"]
    islands["cap_lining"] = planar_uvs(Cm, lining, np.array((1.0, 0, 0)), np.array((0, 1.0, 0)))
    pf = [fi for fi, p in enumerate(Cm.fpart) if p == "peak"]
    islands["cap_peak"] = planar_uvs(Cm, pf, np.array((1.0, 0, 0)), np.array((0, -1.0, 0)))
    for n, share in (("cap_front", 1.0), ("cap_back", 0.8), ("cap_lining", 0.1), ("cap_peak", 0.4)):
        ISLANDS[n] = ("cap", share)
    ATLAS["cap"] = 512
    placed, face_uv = pack(islands)
    write_layout(face_uv, placed, "cap", os.path.join(TEX, "captain_cap_layout.png"))
    views = [("head_front", sh.head_pix, sh.head_mask, False), ("head_back", sh.head_pix, sh.head_mask, False),
             ("head_side", sh.head_pix, sh.head_mask, False), ("head_side", sh.head_pix, sh.head_mask, True)]
    rgb, hit = paint(Cm, face_uv, "cap", sh, views, Cm.tris())
    P = np.array(Cm.P)
    N = normals_of(P, Cm.tris())
    pos, nrm, hit, fid = texel_geometry(Cm, face_uv, "cap", P, N)
    fam_t = np.array(list(Cm.fpart) + ["none"])[fid]
    lift = np.clip(nrm[..., 2], 0, 1)
    pk = hit & (fam_t == "peak")
    rgb[pk] = np.array((0.11, 0.12, 0.14)) + np.array((0.06, 0.065, 0.07)) * lift[pk][:, None]
    rgb[hit & (fam_t == "cap_lining")] = (0.08, 0.08, 0.09)
    path = os.path.join(TEX, "captain_cap.png")
    save_rgb(path, rgb[::-1])
    ob = mesh_object("captain_cap", Cm.P, Cm.faces, armature, rigid="head")
    ob.data.materials.append(textured_material("captain_cap", path))
    uvl = ob.data.uv_layers.new(name="UVMap")
    for poly in ob.data.polygons:
        for li, q in zip(poly.loop_indices, face_uv[poly.index][1]):
            uvl.data[li].uv = q
    return ob


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
            # (where the arm lies against him the sheet shows no side of the torso: not fitted there)
            under_arm = (fams == "torso") & (P[:, 2] > body_z(672)) & (P[:, 2] < body_z(440))
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
    P = (P + Q) / 2.0
    centre = mir == np.arange(len(P))
    P[centre, 0] = 0.0
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
            head = my < 430
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
        r0, r1 = 80, 1000
        pic = sh.head_pix[r0:r1, c0:c1].copy()
        mm = model[r0:r1, c0:c1]
        half = np.where(mm[..., None], pic * 0.55 + np.array((0.2, 0.25, 0.45)) * 0.45, pic)
        half[outline_of(sh.head_mask)[r0:r1, c0:c1]] = (0.1, 0.75, 0.2)
        half[outline_of(model)[r0:r1, c0:c1]] = (0.95, 0.1, 0.1)
        save_rgb(os.path.join(OUT, "overlay_%s.png" % view), half)


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
        ("spine", torso_centre(M, T, 0.82), "hips"),
        ("chest", torso_centre(M, T, 1.02), "spine"),
        ("neck", torso_centre(M, T, 1.30), "chest"),
    ]
    head_at = torso_centre(M, T, 1.30)
    head_at.z = 1.385
    head_at.y += 0.012
    bones.append(("head", head_at, "neck"))
    for s, sfx in ((1, "_l"), (-1, "_r")):
        sh_ = Vector(mirror_x(joints["shoulder_l"], s))
        el = Vector(mirror_x(joints["elbow_l"], s))
        wr = Vector(mirror_x(joints["wrist_l"], s))
        bones.append(("clavicle" + sfx, Vector((s * 0.04, sh_.y - 0.01, sh_.z + 0.06)), "chest"))
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


def make_armature(bones, name="captain_armature"):
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


def weights_of(M, T, bones, joints):
    at = {n: np.array(p) for n, p, _ in bones}
    P = np.array(M.P)
    out = []
    zt = {"hips_spine": 0.74, "spine_chest": 0.93, "chest_neck": 1.29}
    for vi, part in enumerate(M.part):
        p = P[vi]
        fam = part.split("_")[0]
        sfx = "_l" if part.endswith("_l") or "_l_" in part else ("_r" if part.endswith("_r") or "_r_" in part else ("_l" if p[0] >= 0 else "_r"))
        w = {}
        if fam in ("head", "cap", "nose", "ear", "peak"):
            w = {"head": 1.0}
            if fam == "head" and p[2] < 1.345:
                t = float(smooth01(1.305, 1.345, p[2]))
                w = {"head": t, "neck": 1 - t}
        elif fam == "torso":
            w = chain_weights(p[2], ["hips", "spine", "chest", "neck"], [zt["hips_spine"], zt["spine_chest"], zt["chest_neck"]], 0.07)
            # near the shoulder: some of the upper arm
            for s, sx in ((1, "_l"), (-1, "_r")):
                d = np.linalg.norm(p - at["upper_arm" + sx])
                k = 0.45 * (1 - float(smooth01(0.07, 0.17, d)))
                if k > 0:
                    w = {n: v * (1 - k) for n, v in w.items()}
                    w["upper_arm" + sx] = w.get("upper_arm" + sx, 0) + k
                # near the hip: some of the thigh
                if p[2] < at["hips"][2] + 0.02 and s * p[0] > 0.02:
                    k = 0.5 * (1 - float(smooth01(at["thigh" + sx][2] - 0.06, at["hips"][2] + 0.04, p[2]))) * float(smooth01(0.02, 0.09, s * p[0]))
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
            if s > Lu - 0.06:
                s = Lu + along(p, E, W)
            w = chain_weights(s, ["upper_arm" + sfx, "forearm" + sfx, "hand" + sfx], [Lu, Lu + np.linalg.norm(W - E) + 0.005], 0.045)
            k = 0.4 * (1 - float(smooth01(0.0, 0.08, s)))
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
                w = chain_weights(s, ["hand" + sfx] + names, [0.004, l1, l1 + np.linalg.norm(a3 - a2)], 0.008)
            else:
                Wr = at["hand" + sfx]
                s = along(p, at["forearm" + sfx], Wr) - np.linalg.norm(Wr - at["forearm" + sfx])
                w = chain_weights(s, ["forearm" + sfx, "hand" + sfx], [0.0], 0.03)
        elif fam in ("leg", "foot"):
            H, K, A = at["thigh" + sfx], at["shin" + sfx], at["foot" + sfx]
            if fam == "leg":
                z = p[2]
                w = chain_weights(-z, ["thigh" + sfx, "shin" + sfx, "foot" + sfx], [-K[2], -A[2]], 0.045)
                k = 0.45 * float(smooth01(H[2] - 0.1, H[2] + 0.03, z))
                if k > 0:
                    w = {n: v * (1 - k) for n, v in w.items()}
                    w["hips"] = w.get("hips", 0) + k
            else:
                fwd = np.array((math.sin(FOOT_YAW) * (1 if sfx == "_l" else -1), -math.cos(FOOT_YAW), 0.0))
                u = float(np.dot(p - A, fwd))
                w = chain_weights(u, ["foot" + sfx, "toe" + sfx], [0.135], 0.03)
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
    "ear_r": ("face", 0.8), "peak": ("face", 0.35),
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


def plan_uvs(M, T, H, joints):
    """Gives {island: {face index: [uv per corner, metres]}}."""
    fam = [p.split("_")[0] for p in M.fpart]
    islands = {}
    # torso: front (columns 12..3, seam at column 4 and 12) and back
    tf = [fi for fi, c in M.cell.items() if c[0] == "torso" and (c[2] >= 12 or c[2] < 4)]
    tb = [fi for fi, c in M.cell.items() if c[0] == "torso" and 4 <= c[2] < 12]
    # (the torso's front and back by angle round his middle at each height times that height's mean radius, so the
    # arm holes, whose points stand round the shoulder, do not shear the islands as distance round a ring did)
    islands["torso_front"] = cylinder_uvs(M, T, tf, back=False)
    islands["torso_back"] = cylinder_uvs(M, T, tb, back=True)
    # the head and neck (the torso's top ring, the head's rings): front and back
    HR = [T[-1]] + H
    hf = [fi for fi, c in M.cell.items() if c[0] == "head" and (c[2] >= 12 or c[2] < 4) and c[1] < len(H) - 1]
    hb = [fi for fi, c in M.cell.items() if c[0] == "head" and 4 <= c[2] < 12 and c[1] < len(H) - 1]
    islands["head_front"] = grid_uvs(M, HR, hf, 12, up=True)
    islands["head_back"] = {fi: [(-u, v) for u, v in uv] for fi, uv in grid_uvs(M, HR, hb, 4, up=True).items()}
    # the cap's crown (the fan at the top): flat from above, into the island of its side
    P = np.array(M.P)
    for fi, c in M.cell.items():
        if c[0] == "head" and c[1] == len(H) - 1:
            # (continue the grid upward: the top point's v one ring step on, u the ring's)
            pass
    top = [fi for fi, c in M.cell.items() if c[0] == "head" and c[1] == len(H) - 1]
    for fi in top:
        f = M.faces[fi]
        key = "head_front" if (M.cell[fi][2] >= 12 or M.cell[fi][2] < 4) else "head_back"
        islands[key][fi] = None   # filled below from its neighbours' layout
    # limbs
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
        # each finger and the thumb its own island: round its rings (seam under it, on the palm side) and along it
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
    pf = [fi for fi, p in enumerate(M.fpart) if p == "peak"]
    islands["peak"] = planar_uvs(M, pf, np.array((1.0, 0, 0)), np.array((0, -1.0, 0)))
    # the crown's fan: its outer points take their ring's place, the top point one ring's step above the middle
    for key in ("head_front", "head_back"):
        isl = islands[key]
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
                    uv.append((float(np.mean(us)), vmax + 0.04))
            isl[fi] = uv
    missing = [fi for fi in range(len(M.faces)) if not any(fi in isl for isl in islands.values())]
    if missing:
        print("CAPTAIN UV: %d faces in no island: %s" % (len(missing), sorted({M.fpart[f] for f in missing})))
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


def box_blur(img, r):
    """A box blur of radius r texels (by running sums), for wide soft edges."""
    out = img.astype(float)
    for axis in (0, 1):
        n = out.shape[axis]
        c = np.cumsum(np.concatenate([np.zeros_like(np.take(out, [0], axis)), out], axis), axis)
        lo = np.clip(np.arange(n) - r, 0, n)
        hi = np.clip(np.arange(n) + r + 1, 0, n)
        out = (np.take(c, hi, axis) - np.take(c, lo, axis)) / np.expand_dims((hi - lo).astype(float), [i for i in range(out.ndim) if i != axis])
    return out


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
    white = (mn > 0.72) & (mx - mn < 0.1)
    red = (c[..., 0] > 0.6) & (c[..., 0] - c[..., 1] > 0.25)
    return white | red


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
        print("CAPTAIN paint %s: %d texels of ink painted out" % (picture, int(ink.sum())))
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
        print("CAPTAIN paint %s: %d texels above the waistband given its colour" % (picture, n))
    rgb = fill_out(rgb, good, 200)
    # a soft pass where texels were filled, so filled patches carry no streaks
    soft = blur(rgb, 3)
    rgb = np.where(good[..., None], rgb, soft)
    print("CAPTAIN paint %s: %.0f%% of its texels seen by a view" % (picture, 100.0 * (good & hit).sum() / max(hit.sum(), 1)))
    return rgb, hit


# ------------------------------------------------------------------------------------------------------------------
# Hair (the user: "Dont try to model the beard it should be made with a hair shader"). How stylised game beards and
# hair are built (looked up: hair cards and clumps for games, e.g. the Polycount and 80.lv breakdowns of stylised
# beards; Scheuermann's hair notes): clumps that follow the growth, laid in overlapping layers from underneath
# outward, each tapering to a point, of varied length, width and direction, darker at the roots and in the under-
# layers, with strands breaking up the ends (an alpha tip; here hair_ink's `tip_ragged`). So: long locks from root
# to tip (not short tiles: those were the "shingles"), each a flattened tube (closed, so no back faces are needed),
# three layers from the skin out to the outline the head sheet draws, the under layers darker (vertex colour), the
# moustache two sweeps of thick locks over the mouth; the grey hair under the cap the same in two layers; the chest
# hair short tufts. UV along each lock (0 root, 1 tip) and round it; UV2 the same in metres (the shader's strands).
# ------------------------------------------------------------------------------------------------------------------

class Locks:
    def __init__(self):
        self.P, self.F, self.UV, self.UV2, self.C = [], [], [], [], []
        self.count = 0

    def lock(self, path, outs, widths, thick=0.35, shade=1.0, under=0.6, sides=4):
        """A lock along `path` (points), lying with its face toward `outs` (directions), `widths` half-widths.
        sides 4: a flat diamond; 6 or more: a lens-shaped clump (round on top, flatter underneath), soft in light."""
        if sides != 4:
            return self.clump(path, outs, widths, thick, shade, under, sides)
        path = [np.asarray(p, float) for p in path]
        n = len(path)
        seg = [np.linalg.norm(path[i + 1] - path[i]) for i in range(n - 1)]
        total = max(sum(seg), 1e-6)
        dist = np.concatenate([[0.0], np.cumsum(seg)])
        rings = []
        for i in range(n):
            t = path[min(i + 1, n - 1)] - path[max(i - 1, 0)]
            t /= max(np.linalg.norm(t), 1e-9)
            o = np.asarray(outs[i], float)
            o = o - t * np.dot(o, t)
            o /= max(np.linalg.norm(o), 1e-9)
            s = np.cross(t, o)
            w = widths[i]
            h = w * thick
            base = len(self.P)
            pts = [path[i] - s * w, path[i] + o * h, path[i] + s * w, path[i] - o * h * under, path[i] - s * w]
            across = [0.0, w * 1.1, w * 2.2, w * 3.3, w * 4.4]
            for k, q in enumerate(pts):
                self.P.append(q)
                self.UV.append((dist[i] / total, k / 4.0))
                self.UV2.append((dist[i], across[k]))
                self.C.append(shade)
            rings.append(base)
        for a, b in zip(rings, rings[1:]):
            for k in range(4):
                self.F.append([a + k, b + k, b + k + 1, a + k + 1])
        self.count += 1

    def clump(self, path, outs, widths, thick, shade, under, sides):
        """A closed tapered clump: rings of `sides` points round a lens (half-width w across, w * thick out on top,
        w * thick * under below), the first point repeated so UV round it runs 0..1. UV.x along it (root 0, tip 1)."""
        path = [np.asarray(p, float) for p in path]
        n = len(path)
        seg = [np.linalg.norm(path[i + 1] - path[i]) for i in range(n - 1)]
        total = max(sum(seg), 1e-6)
        dist = np.concatenate([[0.0], np.cumsum(seg)])
        rings = []
        for i in range(n):
            t = path[min(i + 1, n - 1)] - path[max(i - 1, 0)]
            t /= max(np.linalg.norm(t), 1e-9)
            o = np.asarray(outs[i], float)
            o = o - t * np.dot(o, t)
            o /= max(np.linalg.norm(o), 1e-9)
            s = np.cross(t, o)
            w = widths[i]
            base = len(self.P)
            for k in range(sides + 1):
                a = math.tau * k / sides
                ca, sa = math.cos(a), math.sin(a)
                h = w * thick * (1.0 if sa >= 0 else under)
                q = path[i] - s * (w * ca) + o * (h * sa)
                self.P.append(q)
                self.UV.append((dist[i] / total, k / float(sides)))
                self.UV2.append((dist[i], w * math.tau * k / sides))
                self.C.append(shade)
            rings.append(base)
        for a, b in zip(rings, rings[1:]):
            for k in range(sides):
                # (wound outward: round the ring, then along it)
                self.F.append([a + k, a + k + 1, b + k + 1, b + k])
        # the root closed by a fan, so each clump is a closed shape
        c = len(self.P)
        self.P.append(path[0])
        self.UV.append((0.0, 0.5))
        self.UV2.append((0.0, 0.0))
        self.C.append(shade)
        for k in range(sides):
            self.F.append([c, rings[0] + k + 1, rings[0] + k])
        self.count += 1

    def grid(self, G, A, A2, X, X2, shade):
        """A smooth shell as one grid of points G[i][j] (i along the hair, root to tip and on round the fold, j
        across), quads between them; A, A2: UV.x and UV2.x (along, 0..1 and metres) per point; X, X2: UV.y and UV2.y
        (across) per column; shade: the vertex colour per point. Gives the first face's index (for orient)."""
        n, m = len(G), len(G[0])
        base = len(self.P)
        f0 = len(self.F)
        for i in range(n):
            for j in range(m):
                self.P.append(np.asarray(G[i][j], float))
                self.UV.append((A[i][j], X[j]))
                self.UV2.append((A2[i][j], X2[j]))
                self.C.append(shade[i][j])
        for i in range(n - 1):
            for j in range(m - 1):
                a = base + i * m + j
                self.F.append([a, a + 1, a + m + 1, a + m])
        self.count += 1
        return f0

    def orient(self, f0, probe, outward):
        """Turns every face from f0 on if the face `probe` (an index from f0) does not face `outward`."""
        f = self.F[f0 + probe]
        p = [self.P[k] for k in f]
        nrm = np.cross(p[1] - p[0], p[2] - p[0])
        if np.dot(nrm, outward) < 0:
            for k in range(f0, len(self.F)):
                self.F[k] = self.F[k][::-1]
            return True
        return False

    def tris(self):
        return sum(len(f) - 2 for f in self.F)


def beard_masks(sh):
    """The beard and grey hair as the head sheet paints them: pale, grey pixels inside his outline."""
    p = sh.head_pix
    mx, mn = p.max(-1), p.min(-1)
    grey = (mx - mn < 0.12) & (mx > 0.42)
    return sh.head_mask & grey


def span_in_row(mask, row, mid, c0, c1, gap=6):
    """The run of mask round `mid` in a row, bridging small gaps (strands drawn apart)."""
    r = mask[int(row), c0:c1]
    cols = np.where(r)[0] + c0
    if not len(cols):
        return None
    # group into runs with small gaps bridged
    groups = np.split(cols, np.where(np.diff(cols) > gap)[0] + 1)
    best = min(groups, key=lambda g: 0 if g[0] <= mid <= g[-1] else min(abs(g[0] - mid), abs(g[-1] - mid)))
    return best[0], best[-1] + 1


def build_hair(M, sh, rng):
    from mathutils.bvhtree import BVHTree
    P = np.array(M.P)
    head_faces = [f for f, p in zip(M.faces, M.fpart) if p.split("_")[0] in ("head", "neck", "cap")]
    trunk_faces = [f for f, p in zip(M.faces, M.fpart) if p.split("_")[0] == "torso"]
    verts = [Vector(p) for p in P]
    bvh = BVHTree.FromPolygons(verts, head_faces)
    bvh_trunk = BVHTree.FromPolygons(verts, trunk_faces)
    beard = beard_masks(sh)
    # (closed: the painted strands leave gaps of darker grey between them)
    for _ in range(5):
        beard = beard | np.roll(beard, 1, 0) | np.roll(beard, -1, 0) | np.roll(beard, 1, 1) | np.roll(beard, -1, 1)
    for _ in range(5):
        beard = beard & np.roll(beard, 1, 0) & np.roll(beard, -1, 0) & np.roll(beard, 1, 1) & np.roll(beard, -1, 1)
    beard &= sh.head_mask
    outline = sh.head_mask
    out = {}

    def skin_hit(origin, d, reach=0.4):
        hit = bvh.ray_cast(Vector(origin), Vector(d), reach)
        return None if hit[0] is None else np.array(hit[0])

    # The beard's outline in the head sheet: front view (half-width per row), side view (front and back per row).
    fc0, fc1 = HEAD_SPAN["front"]
    sc0, sc1 = HEAD_SPAN["side"]

    # Measured once for every row and smoothed over 15 rows, so the locks run smoothly (the painted strands make the
    # raw outline ragged).
    env_rows = np.arange(540, 900)
    raw = []
    for row in env_rows:
        f = span_in_row(outline if 648 <= row <= 760 else beard, row, HEAD_MID["front"], fc0, fc1, gap=20)
        s = span_in_row(beard, row, 1500, sc0, sc1, gap=30)
        if f is None or s is None or (f[1] - f[0]) < 6:
            raw.append((np.nan,) * 3)
        else:
            raw.append(((f[1] - f[0]) / 2.0 * HEAD_SX, (s[0] - HEAD_MID["side"]) * HEAD_SX, (s[1] - HEAD_MID["side"]) * HEAD_SX))
    raw = np.array(raw)
    ok = ~np.isnan(raw[:, 0])
    last_row = env_rows[ok].max()
    for c in range(3):
        raw[:, c] = np.interp(env_rows, env_rows[ok], raw[ok, c])
    k = np.ones(15) / 15.0
    smooth_env = np.stack([np.convolve(np.pad(raw[:, c], 7, mode="edge"), k, "valid") for c in range(3)], 1)
    # the head's cross-section at a height, from its rings (the torso's top ring and the head's)
    HR = [M.tag["torso_rings"][-1]] + M.tag["head_rings"]
    ring_z = np.array([np.mean([M.P[i][2] for i in r]) for r in HR])
    ring_xy = [np.array([M.P[i][:2] for i in r]) for r in HR]

    def section(z):
        i = int(np.clip(np.searchsorted(ring_z, z), 1, len(HR) - 1))
        t = float(np.clip((z - ring_z[i - 1]) / max(ring_z[i] - ring_z[i - 1], 1e-6), 0, 1))
        return ring_xy[i - 1] * (1 - t) + ring_xy[i] * t

    def ray_out(poly, o, d):
        """Where a ray from o along d (2D) leaves the polygon, or None."""
        best = None
        n = len(poly)
        for j in range(n):
            a, b = poly[j], poly[(j + 1) % n]
            e = b - a
            den = d[0] * e[1] - d[1] * e[0]
            if abs(den) < 1e-12:
                continue
            w = a - o
            t = (w[0] * e[1] - w[1] * e[0]) / den
            u = (w[0] * d[1] - w[1] * d[0]) / den
            if t > 0 and 0 <= u <= 1 and (best is None or t > best):
                best = t
        return best

    def envelope(row):
        if row > last_row + 4:
            return None
        i = int(np.clip(round(row) - env_rows[0], 0, len(env_rows) - 1))
        xw, yf, yb = smooth_env[i]
        return 0.0, xw, yf, yb

    B = Locks()
    # Root rows (head sheet) round the face by angle from the front: chin under the mouth, the cheeks lower down,
    # the sideburns from the temples.
    def root_row(phi):
        a = abs(math.degrees(phi))
        # (high up the cheeks and the whole sideburn, so none of the sheet's beard painted on his face is left showing)
        # (sixth round: the sideburns carried up to the cap over the temples, as the sheet's three-quarter view has them;
        # below the cap's band only the front view's painted sideburn stood there, a grey stripe read as a second brow)
        return float(np.interp(a, [0, 18, 30, 45, 58, 66, 74, 84, 98], [655, 638, 612, 585, 548, 500, 462, 452, 448]))

    bottom = 845

    # The beard's outline, read straight off the head sheet's silhouettes (which, below the cheeks, are the beard):
    # the front view's half width and the side view's front, by row, smoothed.
    rows_all = np.arange(440, 900)
    half_w, front_y = [], []
    for row in rows_all:
        f = span_in_row(outline if row <= 760 else beard, row, HEAD_MID["front"], fc0, fc1, gap=20)
        s = span_in_row(outline, row, 1500, sc0, sc1, gap=20)
        half_w.append((f[1] - f[0]) / 2.0 * HEAD_SX if f else np.nan)
        front_y.append((s[0] - HEAD_MID["side"]) * HEAD_SX if s else np.nan)
    half_w, front_y = np.array(half_w), np.array(front_y)
    for arr in (half_w, front_y):
        good_ = ~np.isnan(arr)
        arr[:] = np.convolve(np.pad(np.interp(rows_all, rows_all[good_], arr[good_]), 7, mode="edge"), np.ones(15) / 15, "valid")
    CHIN = 735.0          # head-sheet row of the chin's skin (the head's lowest ring)
    hcentre = lambda z: head_centre(M, z)  # noqa: E731

    def thickness(row, phi):
        """How far the beard stands off the skin: the silhouettes' distance from the skin, front (side view) and
        sides (front view), blended round; nothing behind the jaw."""
        z = float(head_z(row))
        c = hcentre(z)
        sec = section(z)
        i = int(np.clip(row - rows_all[0], 0, len(rows_all) - 1))
        t_front = ray_out(sec, c[:2], np.array((0.0, -1.0)))
        t_side = ray_out(sec, c[:2], np.array((1.0, 0.0)))
        tf = max(0.004, (c[1] - front_y[i]) - (t_front or 0.0))
        ts = max(0.004, half_w[i] - (t_side or 0.0))
        a = abs(phi)
        fade = 1.0 - float(smooth01(math.radians(92), math.radians(120), a))
        th = (tf * math.cos(min(a, math.pi / 2)) ** 2 + ts * math.sin(min(a, math.pi / 2)) ** 2) * fade
        # (sixth round: the sideburns up by the temples lie close, short hair; carried up there at the sheet's width they
        # stood out from his head under the cap as two flaps)
        return min(th, 0.004 + 0.02 * float(smooth01(540.0, 620.0, row)))

    def beard_point(row, phi, f):
        """A point of the beard at a row, an angle round (0 the front, toward his left positive) and a depth f (0 the
        skin, 1 the outline). Below the chin the beard hangs: the chin's section carried down, drawn in to the front
        view's narrowing and moved with the side view's front."""
        d = np.array((math.sin(phi), -math.cos(phi), 0.0))
        r = min(row, CHIN)
        z = float(head_z(r))
        c = hcentre(z)
        t = ray_out(section(z), c[:2], d[:2])
        if t is None:
            return None, None
        p = c + d * (t + f * thickness(r, phi))
        if row > CHIN:
            i0 = int(CHIN - rows_all[0])
            i1 = int(np.clip(row - rows_all[0], 0, len(rows_all) - 1))
            sx = half_w[i1] / max(half_w[i0], 1e-4)
            hang = float(smooth01(CHIN, CHIN + 60, row))
            p = np.array((p[0] * sx, p[1] + (front_y[i1] - front_y[i0]) * (0.4 + 0.6 * f), float(head_z(row))))
            # (the inner layers hang closer in toward the throat)
            p[1] += (1 - f) * 0.02 * hang
        return p, d

    # The beard as ONE SMOOTH SHELL (the fourth way; clumps, strands and cards all read as shingles from the side and
    # below). A grid of columns round the face (PHI: from the right sideburn round the chin to the left one) by points
    # down each column: the root just inside the skin on the cheek or jaw, down the outline the head sheet draws (the
    # front view's width, the side view's forward wedge) to the beard's rounded bottom, round the fold there, and back up
    # its underside to the throat, where it goes into the neck. The hair is the shader's: UV.x along the growth (0 at
    # the roots, 1 at the tips, back to 0 at the throat's roots underneath), UV.y across; UV2 the same in metres.
    BEARD_PHI = 92.0              # degrees round from the front to each sideburn's back edge
    BEARD_COLS = 15
    BEARD_OUT = 9                 # points down the outside
    BEARD_UNDER = 4               # points back up the underside

    def end_row(phi):
        a = abs(math.degrees(phi))
        # (a rounded bottom, as the front view draws it: no corners at the jaw)
        # (and at the sides down the jaw to the neck, the back edge falling straight from the ear lobe as the side view
        # draws it)
        return float(np.interp(a, [0, 20, 40, 55, 70, 82, 92], [bottom + 6, 851, 846, 838, 820, 796, 760]))

    cols_phi = [math.radians(BEARD_PHI) * (2.0 * j / (BEARD_COLS - 1) - 1.0) for j in range(BEARD_COLS)]
    G, A, A2, SH = [], [], [], []
    for j, phi in enumerate(cols_phi):
        r0, r1 = root_row(phi), end_row(phi)
        # (sixth round: the bottom edge drawn down into a few big soft points, as the sheet's locks end, not a smooth
        # curve and not many thin teeth: five points, every third column. Moved straight down (metres) at the end of
        # each column only: lengthening the whole column instead drew the point's end back toward his throat, and the
        # faces beside it folded inward)
        drop = 0.00062 * max(h * max(0.0, 1.0 - abs(j - p) / 1.6) for p, h in ((1, 8.0), (4, 13.0), (7, 15.0), (10, 13.0), (13, 8.0)))
        # (every other column a little longer round the bottom and lower sides: a soft scalloped edge, the locks'
        # ends suggested in the silhouette itself, with no separate pieces to show as shards from below)
        # (tried: every other column a little longer, a scalloped edge; it twisted the fold and opened a notch at the
        # middle of the bottom from below, so the edge is left smooth)
        col, shade = [], []
        for i in range(BEARD_OUT):
            t = i / (BEARD_OUT - 1)
            row = r0 + (r1 - r0) * t ** 0.9
            # (rising off the skin quickly from the root, so the beard's top edge on the cheek is soft, not a step)
            # (and thinning to the skin at the sideburns' back edge, the grid's open side, so no cut edge shows there)
            f = float(smooth01(0.0, 0.45, t)) * (1.0 - 0.5 * float(smooth01(86.0, 92.0, abs(math.degrees(phi))))) if i else 0.0
            q, d = beard_point(row, phi, f)
            # (never closer to the skin than 2.5 mm, where the sideburns are thin: closer, the skin showed through in
            # a saw-tooth)
            q = q - d * 0.004 if i == 0 else q + d * 0.0025 * float(smooth01(0.0, 0.15, t))
            col.append(q)
            # (sixth round: shadowed under the moustache, and darker round toward his neck and lower down there)
            under_m = (1.0 - float(smooth01(25.0, 50.0, abs(math.degrees(phi))))) * (1.0 - float(smooth01(0.05, 0.4, t)))
            neck = float(smooth01(60.0, 92.0, abs(math.degrees(phi)))) * (0.4 + 0.6 * t)
            shade.append((0.82 + 0.18 * float(smooth01(0.0, 0.35, t))) * (1.0 - 0.32 * under_m) * (1.0 - 0.3 * neck))
        # the fold: round under the bottom, between the outside's last point and the underside's first
        q_out, d = beard_point(r1, phi, 1.0)
        q_in, _ = beard_point(r1, phi, 0.0)
        hang = float(smooth01(CHIN - 10, CHIN + 40, r1))
        tip = (q_out * 0.6 + q_in * 0.4) + np.array((0.0, 0.0, -0.013 * hang))
        col[-2] = col[-2] - np.array((0.0, 0.0, drop * 0.45))
        col[-1] = col[-1] - np.array((0.0, 0.0, drop * 0.85))
        tip = tip - np.array((0.0, 0.0, drop))
        col.append(tip)
        shade.append(0.86)
        # the underside, from the bottom back up to the throat (where the beard hangs below the chin), or back up
        # under the skin to the root (on the cheeks, where it lies on him)
        rb = r0 + (CHIN - r0) * hang
        for k in range(BEARD_UNDER):
            u = (k + 1) / BEARD_UNDER
            row = r1 + (rb - r1) * u
            q, d = beard_point(row, phi, 0.0)
            inset = 0.004 * (1.0 - float(smooth01(CHIN - 5, CHIN + 25, row)))
            if k == BEARD_UNDER - 1:
                inset = 0.008
            q = q - np.array((0.0, 0.0, drop * 0.6)) if k == 0 else q
            col.append(q - d * inset)
            shade.append(0.68 + 0.12 * (1.0 - u))
        G.append(col)
        SH.append(shade)
    # along: the outside's length 0..1 to the tip, the underside's back down to 0 at its roots; metres the same
    for col in G:
        seg = [float(np.linalg.norm(col[i + 1] - col[i])) for i in range(len(col) - 1)]
        out_len = sum(seg[:BEARD_OUT])
        under_len = max(sum(seg[BEARD_OUT:]), 1e-6)
        a, a2, run = [0.0], [0.0], 0.0
        for i, s_ in enumerate(seg):
            run += s_
            if i < BEARD_OUT:
                a.append(run / out_len)
                a2.append(run)
            else:
                left = out_len + under_len - run
                a.append(0.55 + 0.45 * left / under_len)      # (the underside never back to its roots: no ragged roots under him)
                a2.append((0.55 + 0.45 * left / under_len) * out_len)
        A.append(a)
        A2.append(a2)
    # (to grid order: along, then across)
    T_ = lambda arr: [[arr[j][i] for j in range(len(arr))] for i in range(len(arr[0]))]  # noqa: E731
    X = [j / (BEARD_COLS - 1) for j in range(BEARD_COLS)]
    X2 = [phi * 0.1 for phi in cols_phi]
    B = Locks()
    f0 = B.grid(T_(G), T_(A), T_(A2), X, X2, T_(SH))
    # (the face halfway down the middle column must face forward, -Y)
    B.orient(f0, (BEARD_OUT // 2) * (BEARD_COLS - 1) + BEARD_COLS // 2, np.array((0.0, -1.0, 0.0)))
    shell_tris = B.tris()

    # The moustache: two smooth drooping lobes from under the nose, out over the mouth's corners and down into the
    # beard, overlapping in the middle; each a closed tube, rounder on top, flatter underneath.
    # (their own mesh with the tips below, captain_tips_beard, so the shader can break their ends into strands, which
    # it cannot do on the shell without opening a hole into it)
    Tp = Locks()
    nose_row, mouth_row = 598.0, 640.0
    for s in (1, -1):
        pts, outs = [], []
        for t in np.linspace(0, 1, 7):
            row = nose_row + 6 + (mouth_row + 36 - nose_row - 6) * (t ** 1.3)
            phi = s * math.radians(-3 + 36 * t ** 0.85)
            q, d = beard_point(row, phi, 1.0)
            pts.append(q + d * (0.006 + 0.008 * math.sin(math.pi * min(t * 1.2, 1.0))))
            outs.append(d * 0.7 + np.array((0, 0, 0.7)))
        m = len(pts)
        widths = [0.029 * (0.8 + 0.4 * math.sin(math.pi * min(i / (m - 1) * 1.5, 1.0))) * (1.0 - 0.8 * (i / (m - 1)) ** 2.0)
                  for i in range(m)]
        widths[-1] = 0.003
        Tp.clump(pts, outs, widths, 0.9, 1.0, 0.55, 8)
    moustache_tris = Tp.tris()

    # Tips past the beard's edge (BEARD_TIPS of them, none now): tried in round four as a row of small tapered pieces
    # rooted in the shell and running past its bottom edge. From the front they broke the outline well; from below
    # they read as a crown of flat shards, which is the fault this round set out to remove. The edge is scalloped in the
    # shell instead (above) and the moustache's ends are broken by the shader.
    tips = 0
    NT = BEARD_TIPS = 0
    for k in range(NT):
        phi = math.radians(-74 + 148 * (k + 0.5) / NT + rng.uniform(-3, 3))
        r0, r1 = root_row(phi), end_row(phi)
        p0, d = beard_point(r0 + (r1 - r0) * 0.8, phi, 0.6)
        p1, _ = beard_point(r0 + (r1 - r0) * 0.93, phi, 1.0)
        q_out, _ = beard_point(r1, phi, 1.0)
        q_in, _ = beard_point(r1, phi, 0.0)
        hang = float(smooth01(CHIN - 10, CHIN + 40, r1))
        p2 = (q_out * 0.75 + q_in * 0.25) + np.array((0.0, 0.0, -0.006 * hang))
        flow = p2 - p1
        flow /= max(np.linalg.norm(flow), 1e-9)
        flow = flow + np.array((-0.3 * math.sin(phi), 0.0, -0.5))
        flow /= np.linalg.norm(flow)
        L = rng.uniform(0.014, 0.022) * (0.75 + 0.25 * math.cos(phi))
        path = [p0, p1 + d * 0.0015, p2, p2 + flow * L * 0.5, p2 + flow * L]
        w = rng.uniform(0.012, 0.015)
        # (Locks.clump, wound outward; Locks.lock's flat cards are wound the other way)
        Tp.clump(path, [d] * 5, [w * 0.7, w, w * 0.95, w * 0.6, 0.002], 0.4, 0.92, 0.5, 6)
        tips += 1
    out["captain_beard"] = B
    out["captain_tips_beard"] = Tp

    def shell_winding(L, f0, rows, cols, name):
        """The shells are open (their edges lie inside him), so the winding test's volume means nothing for them: here
        every face of the outside (rows above the fold) must face away from the head's middle at its height."""
        good = 0
        for i in range(rows):
            for j in range(cols):
                f = L.F[f0 + i * cols + j]
                p = [L.P[k] for k in f]
                nrm = np.cross(p[1] - p[0], p[2] - p[0])
                c = np.mean(p, axis=0)
                axis = head_centre(M, float(c[2]))
                ok_ = np.dot(nrm[:2], (c - axis)[:2]) > 0
                good += ok_
                if not ok_:
                    print("CAPTAIN WINDING %s: face row %d column %d faces inward" % (name, i, j))
        print("CAPTAIN WINDING %s: %d of %d outside faces face outward" % (name, good, rows * cols))
    shell_winding(B, f0, BEARD_OUT - 1, BEARD_COLS - 1, "beard shell")
    print("CAPTAIN hair: beard shell %d triangles, moustache %d, %d tips %d; all %d"
          % (shell_tris, moustache_tris, tips, Tp.tris() - moustache_tris, B.tris() + Tp.tris()))

    # The grey hair under his cap: one thin smooth shell hugging the skull from temple to temple round the back, from
    # inside the cap's band down to the nape's top (longest at the back, short over the ears), with a small swell over
    # each ear; its lower edge folds back under into the skull, so it has a soft thick edge and no gap. UV.x from the
    # band (0) down to the edge (1).
    Hh = Locks()
    band_row = 420.0
    HAIR_COLS = 17
    HAIR_DOWN = 6

    def nape_row(phi):
        a = abs(math.degrees(phi))
        # (low enough to cover all the grey the head sheet's back view paints onto his skin there)
        # (and behind the ears falling to the neck's top, as the back and side views draw it)
        # (short over the ear, which stands clear of it: the ear runs from about 90 to 112 degrees round)
        return float(np.interp(a, [82, 96, 110, 124, 140, 160, 180], [466, 470, 478, 525, 565, 588, 598]))

    def on_skull(row, phi, lift):
        z = float(head_z(row))
        c = head_centre(M, z)
        d = np.array((math.sin(phi), -math.cos(phi), 0.0))
        hit = skin_hit(c, d, 0.3)
        if hit is None:
            t = ray_out(section(z), c[:2], d[:2]) or 0.08
            hit = c + d * t
        return hit + d * lift, d

    G, A, A2, SH = [], [], [], []
    # (from 82 degrees, where the beard's sideburns come up to meet it: further forward its front edge stood as a
    # pale plate on the temple)
    hcols = [math.radians(82.0 + (360.0 - 164.0) * j / (HAIR_COLS - 1)) for j in range(HAIR_COLS)]
    for phi in hcols:
        a = abs(math.degrees(math.atan2(math.sin(phi), math.cos(phi))))
        r1 = nape_row(math.atan2(math.sin(phi), math.cos(phi)))
        col, shade = [], []
        for i in range(HAIR_DOWN):
            t = i / (HAIR_DOWN - 1)
            row = band_row - 8 + (r1 - band_row + 8) * t
            # (inside the band at the top; then out to its thickness; over each ear a swell)
            ear_ = float(smooth01(80, 92, a) * (1 - smooth01(108, 122, a))) * math.sin(math.pi * min(t * 1.25, 1.0))
            # (thinning to almost nothing at its lower edge, so the edge melts into the grey painted under it rather
            # than standing as a slab's cut)
            # (and to the skin at its two ends by the temples, the grid's open sides, so no cut edge shows there)
            ends_ = 0.2 + 0.8 * float(smooth01(82.0, 96.0, a))
            lift = -0.003 if i == 0 else (0.0026 + 0.0075 * math.sin(math.pi * min(0.2 + 0.8 * t, 1.0)) ** 0.8) * ends_ + 0.0045 * ear_
            q, d = on_skull(row, phi, lift)
            col.append(q)
            shade.append((0.85 + 0.15 * float(smooth01(0.0, 0.4, t))) * (1.0 - 0.22 * float(smooth01(0.6, 1.0, t))))
        q, d = on_skull(r1 + 3, phi, 0.0016)
        col.append(q)
        shade.append(0.7)
        q, d = on_skull(r1 - 10, phi, -0.004)
        col.append(q)
        shade.append(0.6)
        seg = [float(np.linalg.norm(col[i + 1] - col[i])) for i in range(len(col) - 1)]
        tot = sum(seg[:HAIR_DOWN])
        a_, a2, run = [0.0], [0.0], 0.0
        for s_ in seg:
            run += s_
            a_.append(min(run / tot, 1.0))
            a2.append(min(run, tot))
        G.append(col)
        SH.append(shade)
        A.append(a_)
        A2.append(a2)
    X = [j / (HAIR_COLS - 1) for j in range(HAIR_COLS)]
    X2 = [phi * 0.1 for phi in hcols]
    f0 = Hh.grid(T_(G), T_(A), T_(A2), X, X2, T_(SH))
    # (the face halfway down the middle column, at the back of his head, must face backward, +Y)
    Hh.orient(f0, (HAIR_DOWN // 2) * (HAIR_COLS - 1) + HAIR_COLS // 2, np.array((0.0, 1.0, 0.0)))
    out["captain_headhair"] = Hh
    shell_winding(Hh, f0, HAIR_DOWN - 1, HAIR_COLS - 1, "hair under the cap")
    print("CAPTAIN hair: under the cap one shell, %d triangles" % Hh.tris())

    # Chest and body hair (Claude's pick, fourth round): no raised tufts (they read as a column of chips). The sheet's
    # painted bush stays on the skin, in his skin picture, as the sheet paints it.
    return out


def face_normal_at(bvh, p):
    hit = bvh.find_nearest(Vector(p))
    n = np.array(hit[1])
    return n / max(np.linalg.norm(n), 1e-9)


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


def hair_object(name, L, armature, material, bone="head"):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(map(float, p)) for p in L.P], [], L.F)
    me.update()
    for poly in me.polygons:
        poly.use_smooth = True
    # (made first and then looked up again: adding a layer moves the others, and an older reference to one then
    # points at freed memory, which crashed Blender)
    me.uv_layers.new(name="UVMap")
    me.uv_layers.new(name="UV2")
    me.color_attributes.new("Color", "BYTE_COLOR", "CORNER")
    uv0 = me.uv_layers["UVMap"]
    uv1 = me.uv_layers["UV2"]
    col = me.color_attributes["Color"]
    for poly in me.polygons:
        for li in poly.loop_indices:
            v = me.loops[li].vertex_index
            uv0.data[li].uv = L.UV[v]
            uv1.data[li].uv = L.UV2[v]
            c = L.C[v]
            col.data[li].color = (c, c, c, 1.0)
    me.uv_layers.active = uv0
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = armature
    mod = ob.modifiers.new("armature", "ARMATURE")
    mod.object = armature
    if isinstance(bone, str):
        g = ob.vertex_groups.new(name=bone)
        g.add(list(range(len(L.P))), 1.0, "REPLACE")
    else:
        groups = {}
        for vi, w in enumerate(bone):
            for bn, v in w.items():
                if bn not in groups:
                    groups[bn] = ob.vertex_groups.new(name=bn)
                groups[bn].add([vi], v, "REPLACE")
    me.materials.append(material)
    return ob


# ------------------------------------------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------------------------------------------

def main():
    # (an empty scene: the factory start-up's cube, camera and light removed; read_factory_settings from inside a
    # running script crashed Blender later on)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sh = Sheets()
    M, T, joints = build_body(sh)
    head_rings = build_head(M, sh, T[-1])
    dup = [(i, f, M.fpart[i]) for i, f in enumerate(M.faces) if len(set(f)) != len(f)]
    seen_f = {}
    for i, f in enumerate(M.faces):
        seen_f.setdefault(tuple(sorted(f)), []).append(i)
    twice = [v for v in seen_f.values() if len(v) > 1]
    print("CAPTAIN faces with a point twice: %d %s; faces made twice: %d %s" % (len(dup), dup[:4], len(twice), [[M.fpart[i] for i in v] for v in twice[:4]]))
    flipped = fix_winding(M)
    print("CAPTAIN built: %d points, %d faces, %d triangles (%d turned outward)" % (len(M.P), len(M.faces), len(M.tris()), flipped))
    body_faces = [f for f, p in zip(M.faces, M.fpart) if part_family(p) not in ("ear", "peak")]
    print("CAPTAIN open edges of the body (should be none): %d" % len(open_edges(body_faces)))
    fams = np.array([part_family(p) for p in M.part])
    # (the hands too, fifth round: they are built to the hands sheet, and the base body's outline pulled the fingers
    # and the thumb out of shape: the thumb came out a flat twisted sliver)
    frozen = np.isin(fams, ("head", "cap", "nose", "ear", "peak", "neck", "hand"))
    # (the torso's two top rings are under the beard in the front view: kept as built)
    for i in (len(T) - 1,):
        frozen[T[i]] = True
    # (and the wrist's two rings, sixth round: the sheet's outline there is the hand's, and pulled them out to a cuff)
    for sfx in ("_l", "_r"):
        for ring in M.tag["arm_rings" + sfx][-2:]:
            frozen[ring] = True
    mir = mirror_map(M.P)
    print("CAPTAIN mirror pairs: %d of %d points matched" % ((mir != np.arange(len(mir))).sum(), len(mir)))

    def snapshot():
        Pc, tc = with_caps(M, np.array(M.P), [])
        return [(np.array(M.P), M.tris(), M.tri_fams()), (Pc, tc, ["sidecap"] * len(tc))]

    stats = overlay(snapshot(), sh, "r0")
    print("CAPTAIN overlay r0", json.dumps(stats))
    for rnd in range(1, FIT_ROUNDS + 1):
        moved, most = fit_round(M, sh, frozen)
        symmetrize(M, mir)
        relax(M, frozen, 0.2, 1)
        stats = overlay(snapshot(), sh, "r%d" % rnd, report=True)
        print("CAPTAIN fit round %d: %d points on the outline moved, most %.1f cm; %s" % (rnd, moved, most * 100, json.dumps(stats)))
    smooth_armpits(M)
    sculpt_body(M)
    smooth_hands(M)
    finish(M, T, joints, sh)


# Forms the plain grey model lacked (the coordinator, from a render of him untextured, 2026-11-18: "the torso is a
# smooth tube: no pecs, no belly roll over the waistband, no love handles, no navel ... the knees and calves are
# tubes"). Moves of the fitted rings, by row and by how far round from his front each point is, in metres: forward is
# -Y. (row, {column offset from the front middle: (forward, outward[, up])}).
# Seventh round (the user, of the belly in profile: "His belly has an issue its sharp"; "his shoulders need a little
# work"): the belly is one full round curve (out from under the chest, fullest a little below the navel, rolling
# smoothly under and back in to the band, no crease ring), then smoothed down each front column (BELLY_SMOOTH); the
# shoulders get a rounded top and the trapezius rising into the neck, a hint of the collarbone, and the armpit's folds.
BODY_FORMS = {
    # the belly: one round curve, fullest a little below the navel
    772: {0: (0.004, 0.0), 1: (0.004, 0.0), 2: (0.003, 0.0)},
    790: {0: (-0.002, 0.0), 1: (0.007, 0.0), 2: (0.005, 0.0), 3: (0.0, 0.006), 4: (0.0, 0.010), 5: (0.0, 0.006)},
    808: {0: (0.011, 0.0), 1: (0.010, 0.0), 2: (0.007, 0.0), 3: (0.002, 0.004), 4: (0.0, 0.008), 5: (0.0, 0.005)},
    826: {0: (0.013, 0.0), 1: (0.012, 0.0), 2: (0.008, 0.0), 3: (0.002, 0.0)},
    842: {0: (0.010, 0.0), 1: (0.009, 0.0), 2: (0.006, 0.0)},
    855: {0: (0.003, 0.0), 1: (0.003, 0.0), 2: (0.002, 0.0)},
    868: {0: (-0.004, 0.0), 1: (-0.004, 0.0), 2: (-0.002, 0.0)},
    # the pecs (the nipples' row 610) with a fold under them, the breastbone between, and the armpit's folds (the pec's
    # edge in front of the arm, the back's behind it)
    615: {0: (-0.008, 0.0), 1: (0.010, 0.0), 2: (0.017, 0.0), 3: (0.012, 0.0), 5: (-0.008, 0.0)},
    642: {0: (-0.004, 0.0), 1: (-0.004, 0.0), 2: (-0.009, 0.0), 3: (-0.002, 0.0), 5: (-0.005, 0.0)},
    566: {0: (-0.004, 0.0), 1: (0.003, 0.0), 2: (0.005, 0.0)},
    # the collarbone's hint, then the shoulder's top rounded and the trapezius rising into the neck
    445: {1: (0.004, 0.0, 0.003), 2: (0.004, 0.0, 0.006)},
    425: {2: (0.0, 0.004, 0.012), 3: (0.0, 0.008, 0.016), 4: (0.0, 0.006, 0.014), 5: (0.0, 0.004, 0.012), 6: (0.0, 0.0, 0.008)},
    405: {2: (0.0, 0.0, 0.006), 3: (0.0, 0.002, 0.009), 4: (0.0, 0.002, 0.009), 5: (0.0, 0.0, 0.007), 6: (0.0, 0.0, 0.004)},
}
# The kneecaps (forward, metres) on the leg ring at the knee's row, by point (point 1 is the front).
KNEE_FORM = {1: 0.012, 0: 0.006, 2: 0.006}
# The belly's rows smoothed down each front column after the forms (from, to, rounds): no ring stands out of the curve.
BELLY_SMOOTH = (755, 900, 4)


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
    M.P = [p for p in P]


def smooth_hands(M, rounds=4, lam=0.45, mu=-0.47):
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


def smooth_armpits(M, reach=0.1, rounds=12):
    """Stage one left a flap at each armpit: the torso's points under the arm's hole stood out past the hole's bottom
    (the front view hides that part of him, so the fitting never drew them in). The torso's points near each hole's
    bottom are smoothed (plain Laplacian, the hole's own points held), which folds the flap back into the side."""
    P = np.array(M.P)
    E = edges_of(M.faces)
    fams = np.array([part_family(p) for p in M.part])
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
    print("CAPTAIN armpits smoothed: the most a point moved %.1f cm; %d spikes put back" % (moved * 100, spikes))


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


# ------------------------------------------------------------------------------------------------------------------
# Refining the face (fifth round). The rings give the head 16 points round: too few for a brow, eyes, cheeks or a
# mouth (the coordinator's grey render: "a flat sunken band where the eyes and brow should be"). After the UVs are
# planned, the head's faces are split once and the face's front twice (each quad into four; the new points on curved
# edges placed on the cubic between the corners' normals, as PN triangles do, so the split head stays round); faces
# next to a split one take the new edge points and are cut into triangles. UVs, weights and parts are carried over
# (old points keep their numbers, so the rings and tags still hold). Then the forms are moved into the face by sum.
# ------------------------------------------------------------------------------------------------------------------

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


# The face's forms in the head sheet's front view (rows, and columns out from the middle, both sides alike; pixels of
# 0.62 mm): measured off concept_captain_head.jpg (brows knit low over squinting eyes at row 487, 85 px out; puffy
# round cheeks at 545; the mouth at 638 under the moustache). Each: (row, column, row spread, column spread, metres
# out along the surface; negative in).
FACE_FORMS = (
    # the brow ridge, heavy, lower toward the middle (he frowns), and the frown's crease between the brows
    (452, 40, 10, 22, 0.013), (446, 80, 11, 30, 0.017), (444, 118, 12, 22, 0.011),
    (458, 0, 16, 10, -0.005),
    # the eye sockets under the brow, the squinting slit, the puffy lid over it and the bag under it
    (486, 86, 16, 42, -0.010), (488, 86, 4, 34, -0.012),
    (476, 86, 5, 34, 0.004), (500, 88, 6, 34, 0.005),
    # crow's feet: a crease out from each eye's corner
    (492, 132, 4, 10, -0.002),
    # the cheeks: round, high and full, the sheet's rosy apples
    (540, 108, 26, 42, 0.015), (565, 128, 24, 30, 0.007),
    # the upper lip under the nose, the mouth's line, the lower lip
    (612, 0, 10, 40, 0.004), (638, 0, 4, 34, -0.004), (650, 0, 8, 30, 0.006),
    # the bare lower face (seventh round, no beard): the folds from the nose's wings to the mouth's corners, the corners,
    # the groove under the lower lip, a strong round chin, heavy jowls
    (602, 64, 10, 9, -0.003), (622, 76, 10, 9, -0.004), (642, 84, 10, 9, -0.003), (640, 50, 6, 8, -0.004),
    (664, 0, 5, 26, -0.004), (690, 0, 15, 30, 0.008), (668, 150, 26, 34, 0.009), (700, 120, 20, 30, 0.005),
    # the temples, a little hollow
    (455, 170, 20, 18, -0.004),
)


def sculpt_head(M):
    P, N, row, col, facing = head_frame(M)
    fam = np.array([part_family(p) for p in M.part])
    on = (fam == "head")
    w = np.clip((facing - 0.05) / 0.35, 0.0, 1.0) * on
    d = np.zeros(len(P))
    for r0, c0, sr, sc, amount in FACE_FORMS:
        d += amount * bump(row, col, r0, c0, sr, sc)
    P = P + N * (d * w)[:, None]
    M.P = [p for p in P]
    print("CAPTAIN face sculpted: %d points moved, most %.1f mm" % (int((np.abs(d * w) > 1e-4).sum()), 1000 * float(np.abs(d * w).max())))


def refine_head(M, face_uv, weights, under):
    """The head (skin, not the cap) split once, the face's front (brow to mouth) twice."""
    fam = [part_family(p) for p in M.fpart]
    # (not the bare skull above the band: smooth enough at 16 round, and under the cap)
    Pm = np.array(M.P)
    head = {fi for fi, f in enumerate(fam) if f in ("head", "neck") and Pm[M.faces[fi]].mean(0)[2] < float(head_z(418))}
    M1, uv1, W1, ch1 = refine(M, head, face_uv, weights)
    P = np.array(M1.P)
    fam1 = [part_family(p) for p in M1.fpart]
    face = set()
    for fi, f in enumerate(M1.faces):
        if fam1[fi] != "head" or len(f) != 4:
            continue
        c = P[f].mean(0)
        r = float(head_row(c[2]))
        if 428 <= r <= 712 and c[1] < head_centre(M1, c[2])[1] - 0.02 and abs(c[0]) < 0.105:
            face.add(fi)
    M2, uv2, W2, ch2 = refine(M1, face, uv1, W1)
    under2 = set()
    for fi in under:
        for c1 in ch1.get(fi, []):
            under2 |= set(ch2.get(c1, []))
    print("CAPTAIN refined: head %d faces split, face %d split again; %d triangles now" % (len(head), len(face), len(M2.tris())))
    return M2, uv2, W2, under2


def finish(M, T, joints, sh):
    H = M.tag["head_rings"]
    bones = skeleton_joints(M, T, joints)
    weights = weights_of(M, T, bones, joints)
    islands = plan_uvs(M, T, H, joints)
    placed, face_uv = pack(islands)
    under = boxer_faces(M, T)
    M, face_uv, weights, under = refine_head(M, face_uv, weights, under)
    sculpt_head(M)
    print("CAPTAIN island shares: %s" % ", ".join("%s %.0f%%" % (n, 100 * w * h * sc * sc) for n, (pic, u0, v0, sc, (w, h)) in sorted(placed.items())))
    os.makedirs(TEX, exist_ok=True)
    for picture in ATLAS:
        write_layout(face_uv, placed, picture, os.path.join(TEX, "captain_%s_layout.png" % picture))
    # --- paint ---
    fam_of_face = [p.split("_")[0] for p in M.fpart]
    tris_all = M.tris()
    tf = M.tri_fams()
    P = np.array(M.P)
    no_arms = [t for t, f in zip(tris_all, tf) if f not in ("arm", "hand")]
    Pc, no_arms_c = with_caps(M, P, no_arms)
    body_pix = sh.body_pix
    hp = sh.head_pix

    def reject_skin(view, colour, rows, cols):
        bad = np.zeros(len(rows), bool)
        if view == "side":
            (c0, r0), (c1, r1) = SIDE_PATCH
            bad |= (cols >= c0) & (cols <= c1) & (rows >= r0) & (rows <= r1)
        return bad

    skin, spos, shit = paint_skin(M, face_uv, sh, tris_all, Pc, no_arms_c, reject_skin, joints)
    face, fpos, fhit = paint_head(M, face_uv, sh)
    # The two sheets paint his skin in slightly different tones: the head's neck is brought to the body's tone where
    # they meet (the torso's top ring), fading out up to the jaw, so no line shows at the seam.
    zt = float(np.mean([M.P[i][2] for i in T[-1]]))
    near_b = shit & (np.abs(spos[..., 2] - (zt - 0.02)) < 0.02)
    near_h = fhit & (np.abs(fpos[..., 2] - (zt + 0.01)) < 0.012)
    if near_b.any() and near_h.any():
        gain = skin[near_b].mean(0) / np.maximum(face[near_h].mean(0), 1e-3)
        w = (1.0 - smooth01(zt, zt + 0.07, fpos[..., 2])) * fhit
        face = face * (1 + (gain - 1) * w[..., None])
        print("CAPTAIN neck tone: the head's neck times %s" % np.round(gain, 3))
    save_rgb(os.path.join(TEX, "captain_skin.png"), skin[::-1])
    save_rgb(os.path.join(TEX, "captain_face.png"), face[::-1])
    # --- Blender objects ---
    armature = make_armature(bones)
    # (the faces under the boxers: found before the head was refined, carried through it)
    mat_skin = textured_material("captain_skin", os.path.join(TEX, "captain_skin.png"))
    mat_face = textured_material("captain_face", os.path.join(TEX, "captain_face.png"))

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
        return ob
    # His body, and the skin under the boxers as its own piece (plain paint, never seen: whatever he wears covers it;
    # hidden, not deleted, as every look's covered skin is to be).
    skin_object("captain_body", [i for i in range(len(M.faces)) if i not in under])
    skin_object("captain_body_under", sorted(under))
    build_boxers(M, T, sh, weights, under, armature)
    # the cap: its own piece on the head's bone (the game can hide it: he has a whole bare head under it)
    Cap = build_cap(sh)
    cap_object(Cap, sh, armature)
    # the earring in his left ear's lobe
    lobe = np.array(M.P[M.tag["earlobe_l"][0]])
    ring_pts, ring_faces = torus(lobe + np.array((0.004, 0.0, -0.008)), 0.009, 0.0022, 12, 5)
    earring = mesh_object("captain_earring", ring_pts, ring_faces, armature, rigid="head")
    earring.data.materials.append(plain_material("captain_gold", (0.85, 0.62, 0.2), 0.8, 0.35))
    # hair
    # (seventh round, the user: "The captain model shouldnt have a beard- we will add that on top". He is built bare;
    # the beard, moustache and the hair under the cap are kept, made only with --hair, into models/captain_hair.glb on
    # the same skeleton)
    hair = build_hair(M, sh, np.random.default_rng(7)) if HAIR else {}
    print("CAPTAIN hair built: %s" % (sorted(hair) or "none (no --hair)"))
    kd = kdtree.KDTree(len(P))
    for i, p in enumerate(P):
        kd.insert(Vector(p), i)
    kd.balance()
    for name, L in hair.items():
        mat = plain_material(name, (0.8, 0.79, 0.76) if name != "captain_chesthair" else (0.5, 0.48, 0.45), 0.0, 1.0)
        if name == "captain_chesthair":
            bone = [weights[kd.find(Vector(p))[1]] for p in L.P]
        else:
            bone = "head"
        Pn = np.array(L.P)
        print("CAPTAIN making %s: %d points, nan %d, faces %d, max index %d" % (name, len(Pn), int(np.isnan(Pn).sum()), len(L.F), max(max(f) for f in L.F)))
        hair_object(name, L, armature, mat, bone)
    report_counts(M, face_uv)
    for name, L in hair.items():
        print("CAPTAIN triangles %s: %d" % (name, L.tris()))
    # the overlay with his hair, the last round's measure
    objs = [(np.array(M.P), M.tris(), M.tri_fams())]
    Pc, tc = with_caps(M, np.array(M.P), [])
    objs.append((Pc, tc, ["sidecap"] * len(tc)))
    objs.append((np.array(Cap.P), Cap.tris(), ["cap"] * len(Cap.tris())))
    for name, L in hair.items():
        tr = []
        for f in L.F:
            tr += [(f[0], f[i], f[i + 1]) for i in range(1, len(f) - 1)]
        objs.append((np.array(L.P), tr, ["hair"] * len(tr)))
    stats = overlay(objs, sh, "final")
    print("CAPTAIN overlay final (with hair) %s" % json.dumps(stats))
    head_overlay(objs, sh)
    export(armature, GLB, skip=tuple(hair))
    if HAIR:
        export(armature, HAIR_GLB, keep=tuple(hair), blend=False)


# The boxers (the user: "he should have hear shaped boxers pose so you can add clothes on top"): a garment over the
# body, not paint on it. Fifth round (the user circled the waist: "his face and waist need work"): the garment is its
# own grid now, not a copy of the body's faces, so its top can follow the sheet's waistband, which is not level: a thin
# gathered elastic about row 806 at his back, sloping down round his sides to row 864 at his front, where it sits in
# the crease under his belly and the belly rolls over it. Each column of the garment runs down the body's own column of
# rings (the torso's 16), its rows placed by the band's line in that column, stood off the skin by BOXER_STAND; the
# legs carry on round each thigh to the hem (row 1065, the sheet's 1060), flaring a little. The picture is painted, not
# taken from the sheet (whose cloth carried grey smudges): white cloth, evenly spaced crisp red hearts (measured on the
# sheet: about 9.5 cm apart across, 5.5 cm down, every other row half a step over, each 3.3 cm wide), the band's
# gathers, a fly, and a little shade in the folds.
BOXER_BAND = (798.0, 858.0)   # the band's top row at his back and at his front
BOXER_BAND_TALL = 22.0        # sheet pixels (2.7 cm)
BOXER_STAND = (0.012, 0.006, 0.028)   # metres: the cloth, the band, the hems (the legs flare)
BOXER_LEG_RINGS = 2           # the leg rings down to LEG_ROWS[1] = row 1065
BOXER_CLOTH = (0.93, 0.93, 0.94)
BOXER_RED = (0.80, 0.18, 0.20)
HEARTS = (0.14, 0.06, 0.037)   # metres: across, down, a heart's width


def band_row(phi):
    """The band's top row at an angle round him (0 his front)."""
    f = (1.0 + math.cos(phi)) / 2.0
    return BOXER_BAND[0] + (BOXER_BAND[1] - BOXER_BAND[0]) * f ** 1.6


def boxer_faces(M, T):
    """The body's faces the boxers cover wholly (indices into M.faces): torso faces whose top ring lies at or below
    the band's line in their column, and the thighs to the hem."""
    out = set()
    for fi, c in M.cell.items():
        if c[0] != "torso":
            continue
        i, k = c[1], c[2]
        phi = math.tau * (k + 0.5) / TORSO_N
        if TORSO_ROWS[i + 1] >= band_row(phi) + 6:
            out.add(fi)
    for sfx in ("_l", "_r"):
        rings = M.tag["leg_rings" + sfx][:BOXER_LEG_RINGS + 1]
        pts = set(v for r in rings for v in r)
        out |= {fi for fi, (f, p) in enumerate(zip(M.faces, M.fpart)) if p == "leg" + sfx and all(v in pts for v in f)}
    return out


def heart_cover(x, y):
    """How much of a unit heart (about 2.3 across, point down, y up) covers (x, y): 1 inside, 0 out."""
    y = y * 1.08 + 0.12
    f = (x * x + y * y - 1.0) ** 3 - x * x * y ** 3
    return f <= 0.0


def build_boxers(M, T, sh, weights, under, armature):
    P = np.array(M.P)
    N = normals_of(P, M.tris())
    Bx = Mesh()
    src = []                  # for each garment point, the body point it stands off (for its weights)

    def column_at(k, z):
        """The body's surface point and normal in torso column k at height z (between its rings)."""
        zs = np.array([P[r[k]][2] for r in T])
        pts = np.array([P[r[k]] for r in T])
        ns = np.array([N[r[k]] for r in T])
        q = np.array([np.interp(z, zs, pts[:, a]) for a in range(3)])
        n = np.array([np.interp(z, zs, ns[:, a]) for a in range(3)])
        i = int(np.clip(np.searchsorted(zs, z), 0, len(zs) - 1))
        return q, n / max(np.linalg.norm(n), 1e-9), T[i][k]

    # The trunk's rows in each column: the band's rolled top (lip), its top, its bottom, then down to the crotch's ring.
    lower = [r for r in TORSO_ROWS if r >= 915]          # 915, 955, 990, 1020 (crotch ring last)
    lower = sorted(lower)
    rows_of = []
    for k in range(TORSO_N):
        phi = math.tau * k / TORSO_N
        b = band_row(phi)
        b1 = b + BOXER_BAND_TALL
        mids = [b1 + (905.0 - b1) * t for t in (0.25, 0.5, 0.75, 1.0)]
        rows_of.append([b, b, b1] + mids + lower)
    nrows = len(rows_of[0])
    G = []
    band_rows = (0, 1, 2)
    for j in range(nrows):
        ring = []
        for k in range(TORSO_N):
            r = rows_of[k][j]
            q, n, s = column_at(k, float(body_z(r)))
            stand = 0.0018 if j == 0 else BOXER_STAND[1] if j in band_rows else BOXER_STAND[0]
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
    # The crotch and the legs, as the body splits its bottom ring.
    crotch = M.tag["crotch"][0]
    bottom = G[-1]
    zc = P[crotch][2]
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
            # (sixth round: stood straight out from the thigh's middle, and the hem level at the sheet's row 1060; off
            # the skin's normals it came out jagged in the front view, and hardly flared)
            c = P[br].mean(0)
            for v in br:
                out = P[v] - c
                out[2] = 0.0
                out /= max(np.linalg.norm(out), 1e-9)
                q = P[v] + out * stand
                if last:
                    q[2] = float(body_z(1058))
                ring.append(Bx.add(q, "boxers"))
                src.append(v)
            rings.append(ring)
        for a, b in zip(rings, rings[1:]):
            for j in range(LIMB_N):
                k = (j + 1) % LIMB_N
                Bx.face([a[j], a[k], b[k], b[j]], "boxers_leg" + sfx)
        legs[sfx] = rings
    # every face turned to face away from the body under it
    Q = np.array(Bx.P)
    flipped = 0
    for fi, f in enumerate(Bx.faces):
        n_body = np.mean([N[src[v]] for v in f], axis=0)
        if np.dot(face_normal(Q, f), n_body) < 0:
            Bx.faces[fi] = f[::-1]
            flipped += 1
    # UVs: the trunk's front (columns 12 round to 4) and back (4 to 12) by distance round the garment at its middle
    # height and height; each leg by angle round it (seam inside the thigh) and height.
    mid_ring = G[nrows // 2]
    seg = [float(np.linalg.norm(Q[mid_ring[(k + 1) % TORSO_N]] - Q[mid_ring[k]])) for k in range(TORSO_N)]
    islands = {"boxers_front": {}, "boxers_back": {}}
    for fi, c in Bx.cell.items():
        j, k = c[1], c[2]
        front = k >= 12 or k < 4
        start = 12 if front else 4
        uv = []
        f = Bx.faces[fi]
        for v in f:
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
    for n in islands:
        ISLANDS[n] = ("boxers", 1.0)
    ATLAS["boxers"] = 1024
    placed, face_uv = pack(islands)
    write_layout(face_uv, placed, "boxers", os.path.join(TEX, "captain_boxers_layout.png"))
    rgb = paint_boxers(Bx, face_uv, placed, band_faces, G)
    path = os.path.join(TEX, "captain_boxers.png")
    save_rgb(path, rgb[::-1])
    # weights: each garment point takes its body point's
    w = [weights[s] for s in src]
    ob = mesh_object("captain_boxers", Bx.P, Bx.faces, armature, w)
    mat = textured_material("captain_boxers", path)
    mat.use_backface_culling = False
    ob.data.materials.append(mat)
    uvl = ob.data.uv_layers.new(name="UVMap")
    for poly in ob.data.polygons:
        for li, q in zip(poly.loop_indices, face_uv[poly.index][1]):
            uvl.data[li].uv = q
    print("CAPTAIN boxers: %d triangles, %d islands, %d faces turned outward" % (len(Bx.tris()), len(islands), flipped))
    return Bx


def paint_boxers(Bx, face_uv, placed, band_faces, G):
    """The boxers' picture, painted by rule from where each texel lies on him."""
    size = ATLAS["boxers"]
    Q = np.array(Bx.P)
    Nb = normals_of(Q, Bx.tris())
    pos, nrm, hit, fid = texel_geometry(Bx, face_uv, "boxers", Q, Nb)
    sc = next(v[3] for n, v in placed.items() if v[0] == "boxers")
    ppm = sc * size                                    # texels a metre
    ys, xs = np.mgrid[0:size, 0:size].astype(float) + 0.5
    rgb = np.ones((size, size, 3)) * np.array(BOXER_CLOTH)
    # hearts: a staggered lattice in each island's own metres (the islands are all at one scale)
    ax, ay, wd = HEARTS[0] * ppm, HEARTS[1] * ppm, HEARTS[2] * ppm
    cover = np.zeros((size, size))
    for ox, oy in ((0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)):
        X = xs + ox - 0.5
        Y = ys + oy - 0.5
        row = np.floor(Y / ay)
        shift = (row % 2) * 0.5
        cx = (np.floor(X / ax - shift) + 0.5 + shift) * ax
        cy = (row + 0.5) * ay
        u = (X - cx) / (wd / 2.3)
        v = (Y - cy) / (wd / 2.3)
        cover += heart_cover(u, v) * 0.25
    band = np.isin(fid, list(band_faces))
    cover[band] = 0.0
    rgb = rgb * (1 - cover[..., None]) + np.array(BOXER_RED) * cover[..., None]
    # the band: gathered elastic, fine upright gathers
    gathers = 0.9 + 0.1 * np.cos(xs * math.tau / max(0.006 * ppm, 2.0)) ** 2
    rgb[band] *= gathers[band][:, None] * np.array((0.98, 0.98, 1.0))
    z = pos[..., 2]
    # (shade under the band and in the crotch and inner thighs; the hem's edge)
    fam = np.array([p for p in Bx.fpart] + ["none"])[fid]
    trunk = fam == "boxers_torso"
    phi = np.arctan2(pos[..., 0], -pos[..., 1])
    ff = ((1.0 + np.cos(phi)) / 2.0) ** 1.6
    top = body_z(BOXER_BAND[0] + (BOXER_BAND[1] - BOXER_BAND[0]) * ff + BOXER_BAND_TALL)
    under_band = trunk & ~band & (top - z < 0.012) & (top - z > 0)
    rgb[under_band] *= 0.88
    inner = np.clip(1.0 - np.abs(pos[..., 0]) / 0.1, 0, 1) * np.clip((body_z(960) - z) / 0.08, 0, 1)
    rgb *= (1.0 - 0.12 * inner)[..., None]
    # the fly: a placket's outline down his front middle from the band
    front = pos[..., 1] < -0.05
    zb = float(body_z(BOXER_BAND[1] + BOXER_BAND_TALL))
    ax_ = np.abs(pos[..., 0])
    fly = trunk & front & ~band & (z < zb) & (z > zb - 0.11) & (np.abs(ax_ - 0.02) < 0.0011)
    fly |= trunk & front & (np.abs(z - (zb - 0.11)) < 0.0011) & (ax_ < 0.02)
    rgb[fly] *= 0.9
    # the side notch: each leg's side seam open a little way up from the hem, drawn as the dark of the slit
    hem_z = float(body_z(1058))
    for s_ in (1.0, -1.0):
        leg = (fam == ("boxers_leg_l" if s_ > 0 else "boxers_leg_r")) & hit
        if not leg.any():
            continue
        xs_ = pos[..., 0] * s_
        outer = xs_ > np.percentile(xs_[leg], 92)
        cy_ = float(np.median(pos[..., 1][leg & outer]))
        up = z - hem_z
        slit = leg & outer & (up < 0.028) & (np.abs(pos[..., 1] - cy_) < 0.0012 + 0.004 * np.clip(1.0 - up / 0.028, 0, 1))
        rgb[slit] *= 0.6
    out = fill_out(rgb, hit, 64)
    print("CAPTAIN boxers painted: %d texels of hearts" % int((cover > 0.5).sum()))
    return out


def torus(centre, R, r, n, m):
    """A ring in the side plane (the YZ plane), as an earring hangs."""
    pts, faces = [], []
    for i in range(n):
        a = math.tau * i / n
        c = np.array((0.0, math.cos(a), math.sin(a)))
        for j in range(m):
            b = math.tau * j / m
            pts.append(centre + c * (R + r * math.cos(b)) + np.array((1.0, 0, 0)) * r * math.sin(b))
    for i in range(n):
        for j in range(m):
            a, b = i * m + j, i * m + (j + 1) % m
            c, d = ((i + 1) % n) * m + (j + 1) % m, ((i + 1) % n) * m + j
            faces.append([d, c, b, a])      # (outward: the other way round was inside out)
    return pts, faces


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
        if view == "side":
            seen &= ~np.isin(tex_fam.ravel(), ("arm", "hand", "shoulder"))
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
    box |= good & is_boxers(rgb)
    # (the beard hangs over his upper chest in the body sheet: its grey is not skin)
    mx, mn = rgb.max(-1), rgb.min(-1)
    beard = good & (z > body_z(452)) & (mx - mn < 0.1) & (mx > 0.4)
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
    ink |= good & arms & (rb < lrb - 0.03) & (rb < 0.075)
    for _ in range(2):
        ink = ink | np.roll(ink, 1, 0) | np.roll(ink, -1, 0) | np.roll(ink, 1, 1) | np.roll(ink, -1, 1)
    for _ in range(2):
        ink = ink | (arms & (np.roll(ink, 1, 0) | np.roll(ink, -1, 0) | np.roll(ink, 1, 1) | np.roll(ink, -1, 1)))
    good &= ~ink & ~box & ~beard
    print("CAPTAIN paint skin: %d texels of tattoo ink painted out, %d of boxers" % (int(ink.sum()), int(box.sum())))
    rgb = fill_out(rgb, good, 300)
    soft = blur(rgb, 4)
    rgb = np.where(good[..., None], rgb, soft)
    # The hands (sixth round): the base sheet paints them a few pixels across, so taken from it they came out in dark
    # smudges. They take the sheet's hand colour (the median of what it paints them) with a quarter of its variation,
    # a little redder toward the fingertips and on the palm, as the hands sheet paints them.
    hands = hit & (tex_fam == "hand")
    if hands.any():
        base_c = np.median(rgb[hands & good], axis=0) if (hands & good).any() else np.array((0.62, 0.5, 0.44))
        fid_parts = np.array(list(M.fpart) + ["none"])[fid]
        finger = hands & np.char.count(fid_parts.astype(str), "_") >= 2
        flat = np.ones_like(rgb) * base_c
        rgb[hands] = flat[hands] * 0.75 + blur(rgb, 6)[hands] * 0.25
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
    print("CAPTAIN paint skin: %.0f%% of its texels seen by a view" % (100.0 * (good & hit).sum() / max(hit.sum(), 1)))
    return rgb, pos, hit


def paint_head(M, face_uv, sh):
    """His head's picture from the head sheet: front, back, his left side (mirrored for his right)."""
    P = np.array(M.P)
    tris = M.tris()
    tf = M.tri_fams()
    head_tris = [t for t, f in zip(tris, tf) if f in ("head", "cap", "nose", "ear", "peak", "neck")]
    N = normals_of(P, tris)
    pos, nrm, hit, fid = texel_geometry(M, face_uv, "face", P, N)
    size = ATLAS["face"]
    acc = np.zeros((size, size, 3))
    side_hole = np.zeros(size * size, bool)
    wsum = np.zeros((size, size))
    mask = erode(sh.head_mask, 2)
    # (the earring is its own model: its gold is not painted onto the ear)
    gold = (sh.head_pix[..., 0] - sh.head_pix[..., 2] > 0.25) & (sh.head_pix[..., 1] > 0.35)
    # Which view paints each texel (fifth round: blending the views by facing alone painted the cheeks' red twice,
    # once from the front and once from the side, as rings): the front view wherever the surface faces within about
    # 55 degrees of forward, the back view likewise behind, the side views only between; the hand-over is narrow
    # (about 15 degrees), so no feature is laid down by two views at once.
    Nall = nrm.reshape(-1, 3)
    ff = np.clip(-Nall[:, 1], 0, 1)
    fb = np.clip(Nall[:, 1], 0, 1)
    wf = smooth01(0.3, 0.55, ff)
    wb = smooth01(0.3, 0.55, fb) * (1 - wf)
    share = {"head_front": wf, "head_back": wb, "head_side": (1 - wf) * (1 - wb)}
    for view, mirrored in (("head_front", False), ("head_back", False), ("head_side", False), ("head_side", True)):
        Q = pos.reshape(-1, 3).copy()
        Nn = nrm.reshape(-1, 3).copy()
        Pm = P.copy()
        if mirrored:
            Q[:, 0] *= -1
            Nn[:, 0] *= -1
            Pm[:, 0] *= -1
        P2, dep = project(view, Pm)
        zb, _ = raster(P2, dep, head_tris, sh.head_mask.shape)
        q2, qd = project(view, Q)
        _, facing = screen_dir(view, Nn)
        cols = np.clip(q2[:, 0].astype(int), 0, mask.shape[1] - 1)
        rows = np.clip(q2[:, 1].astype(int), 0, mask.shape[0] - 1)
        seen = (qd <= zb[rows, cols] + 0.008) & mask[rows, cols] & (facing > 0.05) & hit.ravel() & ~gold[rows, cols]
        if view == "head_side":
            # (the side view's brow, eye and crow's feet are not taken: on his temple, where the side view sees, they
            # made a second eye, a grey smudge beside the front view's)
            cut = (cols < 1640) & (rows > 412) & (rows < 530)
            side_hole |= seen & cut
            seen &= ~cut
        if view in ("head_front", "head_back"):
            # (seventh round: nor the front and back views' ears, which stand out past his head's sides there and were laid
            # on his temples as a second ear; his own ears are painted from the side)
            mid_ = HEAD_MID[view[5:]]
            seen &= ~((np.abs(cols - mid_) > 182) & (rows > 430) & (rows < 625))
        colour = sh.head_pix[rows, cols]
        w = np.where(seen, share[view] * np.clip(facing, 0, 1) + 1e-4 * np.clip(facing, 0, 1), 0.0)
        acc += (colour * w[:, None]).reshape(size, size, 3)
        wsum += w.reshape(size, size)
    good = wsum > 0.01
    # (where the side view's eye was left out and the front view sees only aslant, nothing is taken: filled from round it;
    # the front view's ear had been laid on his temple there)
    good &= ~(side_hole.reshape(size, size) & (wf.reshape(size, size) < 0.6))
    rgb = acc / np.maximum(wsum, 1e-6)[..., None]
    # The peak is the cap's own black, a little lighter on top toward its edge (the sheet's front view put the band and
    # the forehead on it: a pink streak along the cap's lower edge).
    fam_t = np.array([part_family(p) for p in M.fpart] + ["none"])[fid]
    peak = hit & (fam_t == "peak")
    lift = np.clip(nrm[..., 2], 0, 1)
    rgb[peak] = np.array((0.11, 0.12, 0.14)) + np.array((0.06, 0.065, 0.07)) * lift[peak][:, None]
    good |= peak
    # Seventh round: he is bare-faced and bare-headed (the beard and the cap are pieces of their own). What the sheet
    # paints as beard and moustache (all below his nose's base on the face and neck, and the grey of the sideburns
    # down his cheeks) and what it paints as cap (his skull above the band) are not taken; they are filled from the
    # skin round them, then given a clean-shaven weathered jaw (shade under the chin and jowls, a faint grey of
    # stubble, lips, the mouth's line) and a bald crown (his skin, a little lighter on top).
    rows_t = head_row(pos[..., 2])
    headish = hit & np.isin(fam_t, ("head", "neck"))
    not_back = nrm[..., 1] < 0.45
    lum, sat = rgb.mean(-1), rgb.max(-1) - rgb.min(-1)
    beard = headish & not_back & (rows_t > 590)
    beard |= headish & not_back & (rows_t > 540) & (sat < 0.1) & (lum > 0.42)
    # (and the sideburns' grey down the sides of his face: the hair is added on top later)
    beard |= headish & not_back & (rows_t > 436) & (np.abs(nrm[..., 0]) > 0.45) & (sat < 0.12) & (lum > 0.28)
    # (the crown, and the cap band's dark the sheet paints just above the hair at his back)
    scalp = headish & ((rows_t < 438) | ((rows_t < 448) & (nrm[..., 1] > 0.3)) | ((rows_t < 470) & ((lum < 0.3) | ((rgb[..., 2] > rgb[..., 0]) & (lum < 0.42)))))
    skin_ref = np.median(rgb[good & headish & ~beard & ~scalp & (sat > 0.12) & (lum > 0.4)], axis=0)
    good &= ~beard & ~scalp
    print("CAPTAIN paint face: bare jaw %d texels, bare crown %d; skin %s" % (int(beard.sum()), int(scalp.sum()), np.round(skin_ref, 3)))
    rgb = fill_out(rgb, good, 200)
    nz = nrm[..., 2]
    rgb[beard] = rgb[beard] * 0.5 + skin_ref * 0.5
    rgb[beard] *= (0.8 + 0.2 * np.clip((nz[beard] + 0.7) / 1.0, 0, 1))[:, None]
    stub = beard & (rows_t > 600)
    rgb[stub] = rgb[stub] * 0.93 + np.array((0.42, 0.42, 0.45)) * 0.07
    xa = np.abs(pos[..., 0])
    lips = beard & (rows_t > 626) & (rows_t < 660) & (xa < 0.032) & (nrm[..., 1] < -0.4)
    k = np.clip(1.0 - xa / 0.032, 0, 1) ** 0.5
    rgb[lips] = rgb[lips] * (1 - 0.5 * k[lips][:, None]) + np.array((0.72, 0.42, 0.4)) * 0.5 * k[lips][:, None]
    mouth = beard & (np.abs(rows_t - 638) < 2.2) & (xa < 0.028) & (nrm[..., 1] < -0.4)
    rgb[mouth] *= 0.68
    rgb[scalp] = skin_ref * (0.96 + 0.1 * np.clip(nz[scalp], 0, 1))[:, None]
    # (the short grey hair the sheet paints round his back below the cap thins out upward into the bald crown, no line)
    fringe = headish & ~scalp & ~beard & (rows_t < 478) & (nrm[..., 1] > -0.3)
    k = np.clip((rows_t - 438.0) / 40.0, 0, 1)[fringe][:, None] ** 1.5
    rgb[fringe] = rgb[fringe] * k + skin_ref * (1 - k)
    soft = blur(rgb, 3)
    rgb = np.where(good[..., None], rgb, soft)
    # (the edges between what the sheet paints and the bare skin laid in round it feathered over about ten texels:
    # unfeathered they showed as straight lines across his forehead and under his nose)
    gb = box_blur(box_blur(good.astype(float)[..., None], 14), 14)[..., 0]
    w = np.clip(np.abs(2.0 * gb - 1.0) * 1.4, 0, 1)[..., None]
    rgb = box_blur(box_blur(rgb, 10), 10) * (1 - w) + rgb * w
    print("CAPTAIN paint face: %.0f%% of its texels seen by a view" % (100.0 * (good & hit).sum() / max(hit.sum(), 1)))
    return rgb, pos, hit


def report_counts(M, face_uv):
    by = {}
    for f, p in zip(M.faces, M.fpart):
        fam = p.split("_")[0]
        if fam == "hand" and p.count("_") >= 2:
            fam = "fingers"
        by[fam] = by.get(fam, 0) + len(f) - 2
    print("CAPTAIN triangles by part: %s; all %d" % (json.dumps(by), sum(by.values())))


def export(armature, path, skip=(), keep=None, blend=True):
    """Writes the armature and its meshes to a .glb: all but those named in skip, or only those named in keep."""
    # (nothing but him goes out: a run without --factory-startup once exported the start-up file's Icosphere)
    for o in list(bpy.data.objects):
        if o != armature and o.parent != armature:
            print("CAPTAIN not exported, removed: %s" % o.name)
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
    print("CAPTAIN wrote %s" % path)
    if blend:
        os.makedirs(os.path.dirname(BLEND), exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=BLEND)
        print("CAPTAIN wrote %s" % BLEND)


if __name__ == "__main__":
    main()
