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
GLB = arg("--glb", GLB)
REVERT = set(v for v in arg("--revert", "").split(",") if v)   # (bisecting: last round's face edits taken back by name)
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
    """The height of an old head-sheet row on him (ninth round: carried onto the bare head sheet by its landmarks,
    which sets his head now; the cap and the face's forms are still measured in these rows)."""
    return bare_z(_interp_x(row, OLD_LM, BARE_LM))


def head_row(z):
    return _interp_x(bare_row(z), BARE_LM, OLD_LM)


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
        self.bare_pix = load_picture(BARE_SHEET)
        self.bare_mask = bare_mask_of(self.bare_pix)
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
    if view.startswith("bare_"):
        row = bare_row(z) + 0.5
        v = view[5:]
        if v == "front":
            return np.stack([BARE_MID["front"] + x / BS + 0.5, row], 1), y
        if v == "back":
            return np.stack([BARE_MID["back"] - x / (BS * BARE_BACK_W) + 0.5, row], 1), -y
        return np.stack([BARE_MID["side"] + y / BS + 0.5, row], 1), -x   # his left side
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
    v = view[5:] if view.startswith(("head_", "bare_")) else view
    if v == "front":
        return np.stack([N[:, 0], -N[:, 2]], 1), -N[:, 1]
    if v == "back":
        return np.stack([-N[:, 0], -N[:, 2]], 1), N[:, 1]
    if view.startswith(("head_", "bare_")):
        return np.stack([N[:, 1], -N[:, 2]], 1), N[:, 0]
    return np.stack([-N[:, 1], -N[:, 2]], 1), -N[:, 0]


def world_dir(view, d2):
    """A direction in the picture as a model direction (in the picture's plane)."""
    v = view[5:] if view.startswith(("head_", "bare_")) else view
    z = np.zeros(len(d2))
    if v == "front":
        return np.stack([d2[:, 0], z, -d2[:, 1]], 1)
    if v == "back":
        return np.stack([-d2[:, 0], z, -d2[:, 1]], 1)
    if view.startswith(("head_", "bare_")):
        return np.stack([z, d2[:, 0], -d2[:, 1]], 1)
    return np.stack([z, -d2[:, 0], -d2[:, 1]], 1)


def view_scale(view):
    return BS if view.startswith("bare_") else HEAD_SX if view.startswith("head_") else S


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
# (eighth round, the user: "Seems like hes missing a chin/jaw/neck": the torso's top two rings are his neck now, a
# short thick column under the jaw: 405 the throat, 425 the neck's base flaring into the trapezius)
CHEST_UNDER_BEARD = {445: -0.138, 425: -0.098, 405: -0.074}
# The torso's half width where the arms hide it in the front view (metres), by row.
TORSO_UNDER_ARMS = {642: 0.262, 615: 0.262, 566: 0.258, 525: 0.25, 485: 0.24, 445: 0.225, 425: 0.122, 405: 0.088}
# Shoulder joint row, elbow row, wrist row (the arm's axis is fitted through the drawn arm in the front view).
SHOULDER_ROW, ELBOW_ROW, WRIST_ROW = 505, 700, 846   # (eighteenth round: 862; the sheet's wrist, its narrowest, is at 840)
ARM_ROOT_R = 0.094            # the radius of the arm's root ring (where it comes out of the torso)
ARM_Y = (0.0, -0.035)         # the arm's axis front to back, at the shoulder and at the wrist (the side view has none)
# How deep each arm ring is for how wide it is, along the arm (deltoid, upper arm, elbow, forearm, wrist).
ARM_DEPTH = ((0.0, 1.05), (0.12, 1.0), (0.24, 0.9), (0.3, 0.88), (0.4, 1.0), (0.52, 1.15))
ARM_SWELL = (0.06, 0.2, 0.1, 0.22)   # (fourteenth round) the upper arm across, in depth; the forearm across, in depth
ARM_ELBOW = 0.012                # the elbow's point behind
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
            # (seventeenth round, the user: "why are his forearms and wrists such different sizes": the sheet's wrist
            # measured 11.8 cm across at its narrowest (four views; 80% of the palm's 14.8), the model's 6.8: these
            # caps were half widths of 4.7 and 4 cm; now a thick sailor's wrist, the hand's wrist loop widened to meet it)
            a = WRIST_HALF[0] if s < Lu + Lf - 0.01 else WRIST_HALF[1]
        b = a * depth_ratio(s)
        # (seventh round, the user: "his shoulders need a little work": a heavy round deltoid over the top of the arm,
        # fuller out and a little forward; the upper arm's bulk under it)
        dl = math.exp(-((s - 0.06) / 0.05) ** 2)
        a *= 1.0 + 0.2 * dl
        b *= 1.0 + 0.16 * dl
        C = C + A * (0.009 * dl) + F * (0.002 * dl) + Vector((0, 0, 0.006 * dl))
        # (fourteenth round, the critic: "arms too thin and tubular ... swell the upper arm, the forearm just below
        # the elbow, keep the wrist thick; one bony point at the back of the elbow"): the front view's width is the
        # sheet's (the fit holds it), so the swell is mostly in depth, which no fitted view sees: the biceps and triceps
        # round the upper arm's middle, the forearm's muscles bulging just below the elbow.
        bi = math.exp(-((s - Lu * 0.55) / (Lu * 0.28)) ** 2)
        fo = math.exp(-((s - (Lu + 0.065)) / 0.055) ** 2)
        a *= 1.0 + ARM_SWELL[0] * bi + ARM_SWELL[2] * fo
        b *= 1.0 + ARM_SWELL[1] * bi + ARM_SWELL[3] * fo
        elbow = abs(s - Lu) < 1e-6
        ring = []
        for j in range(LIMB_N):
            ph = math.tau * j / LIMB_N
            q = C + A * (a * math.cos(ph)) + F * (b * math.sin(ph))
            if elbow and math.sin(ph) < -0.6:
                q = q - F * ARM_ELBOW * (-math.sin(ph) - 0.6) / 0.4
            ring.append(M.add(mirror_x(q, side), part))
        M.bridge(prev, ring, part) if side > 0 else M.bridge(ring, prev, part)
        rings.append(ring)
        prev = ring
    M.tag["arm_rings" + sfx] = rings
    M.tag["arm_stations" + sfx] = [0.0] + stations
    joints["arm_frame"] = (Du, Df)
    hand(M, prev, side, W, Df, joints)


# Tenth round: the hands rebuilt from tools/art_src/concept_captain_hands.jpg (the user: "his hands still seem poor
# quality compared to like twilight princess hands", "Captains current hands also seem too small"; "make sure you are
# matching pose silhouettes aggressively"). Built in the hand's own frame (u along it from the wrist's crease, v across
# toward the thumb, w out of its back), in the hand sheet's pixels (HAND_PX metres each: the sheet's wrist, 282 px
# across, made as wide as his forearm's last ring, 9.2 cm; his hand is then 20.3 cm from the wrist's crease to the
# middle fingertip, as the base-body sheet's front view draws it). Measured on the sheet's palm view (fingers up, his
# left hand): the palm's edges row by row, each finger's axis, width and tip, the webs; on its thumb-side view the
# thickness. Rings of 20 round the palm (wrist, heel, the thenar's swell, below the knuckles, the knuckles), so each
# finger and the thumb leave it from six points and are hexagons in section; four rings and a rounded tip a finger.
# Posed by angles (spread at the knuckle, curl at each joint), so the same hand is laid over each sheet view in that
# view's pose (HAND_POSES) and hangs relaxed on him.
HAND_PX = 0.000326
# The palm's rings: (u, v at the little finger's edge, v at the thumb's edge, w of the back, w of the palm), pixels.
HAND_RINGS = ((0, -143, 143, 121, -121), (60, -155, 182, 117, -137), (135, -175, 238, 120, -158),
              (245, -194, 166, 128, -112))
# The knuckles' ring: the fingers' boundaries and middles across (thumb side to little side: index outer edge,
# index|middle, middle|ring, ring|little, little outer edge), where the back meets them (the knuckles) and where the
# palm does (the webs), and how high the back and low the palm stand there.
KNUCKLE_V = (160, 111, 57, 5, -45, -94, -151, -203, -243)
KNUCKLE_U_BACK = (296, 313, 316, 322, 316, 313, 300, 282, 266)
KNUCKLE_U_PALM = (346, 368, 368, 368, 368, 368, 356, 335, 322)
KNUCKLE_W_BACK = (100, 122, 110, 126, 110, 120, 102, 106, 88)
KNUCKLE_W_PALM = (-40, -52, -46, -54, -46, -52, -44, -48, -36)
KNUCKLE_SIDES = ((172, 326, 36), (-252, 292, 30))   # (v, u, w) of the thumb's side point and the little finger's
# Each finger: (name, knuckle u, middle v, middle w, length from the knuckle to the tip, widths at the first ring, the
# middle joint, the end joint, near the tip), pixels; measured on the palm view (the back view draws them 8% wider: the
# widths here lie between).
HAND_FINGERS = (("index", 313, 111, 22, 270, (97, 90, 85, 75)), ("middle", 322, 5, 40, 303, (97, 93, 89, 79)),
                ("ring", 313, -94, 32, 262, (92, 87, 83, 73)), ("little", 282, -203, 10, 199, (82, 75, 71, 63)))
FINGER_SEGS = (0.45, 0.30, 0.25)
# The thumb (metres): its segments from its root on the palm's side (the free part of its long bone, the first and
# end joints) and its widths (root, first joint, end joint, near the tip).
THUMB_SEGS = (0.018, 0.028, 0.026)
THUMB_W = (0.038, 0.035, 0.0355, 0.031)
# Poses: spread (degrees toward the thumb) and curl (knuckle, middle joint, end joint) a finger; the thumb's yaw (from
# along the hand toward its side), pitch (toward the palm), and its two joints' curl.
HAND_POSES = {
    "relaxed": {"spread": (2, 0, -4, -8), "curl": ((14, 24, 12), (18, 30, 14), (22, 34, 16), (26, 38, 18)),
                "thumb": (20, 30, 10, 16)},
    "palm": {"spread": (5, -3, -11, -16.5), "curl": ((0, 2, 2), (0, 2, 2), (0, 2, 2), (0, 2, 2)), "thumb": (29, 40, 0, 6)},
    "back": {"spread": (7, -1, -4.5, -3), "curl": ((0, 2, 2), (0, 2, 2), (0, 2, 2), (0, 2, 2)), "thumb": (44, 19, 0, 8)},
    "thumb": {"spread": (2, 0, -3, -6), "curl": ((10, 4, 3), (10, 4, 3), (10, 4, 3), (10, 4, 3)), "thumb": (10, 14, 4, 8)},
}


def _rot(vec, axis, deg):
    return np.asarray(Matrix.Rotation(math.radians(deg), 3, Vector(axis)) @ Vector(vec))


def loft_hand_local(pose):
    """(Twelfth round: no longer his hand, see hand_local; kept as the pose reference: its joints and their frames are
    where the base hand is fitted.) The hand in its own frame (metres): points, faces [(index list, piece)], rings and joints."""
    P, F = [], []
    k_ = HAND_PX

    def add(q):
        P.append(np.asarray(q, float))
        return len(P) - 1

    def palm_ring(u, vL, vR, wT, wB, pads=0.0):
        """20 points: back (thumb edge to little edge, 9), the little side, palm (little to thumb, 9), the thumb side."""
        span = KNUCKLE_V[0] - KNUCKLE_V[-1]
        e = 0.08 * (vR - vL) / 2.0
        back, palm = [], []
        for v0 in KNUCKLE_V:
            f = (v0 - KNUCKLE_V[-1]) / span
            v = vL + e + f * (vR - vL - 2 * e)
            x = 2 * f - 1
            wb = wT * (1 - 0.3 * x * x)
            wp = wB * (1 - 0.25 * x * x)
            # (the pads at the heel: the thenar under the thumb, the hypothenar on the little finger's side)
            wp -= pads * (0.9 * float(smooth01(0.2, 0.8, x)) + 0.6 * float(smooth01(-0.2, -0.8, x)))
            back.append(add((u * k_, v * k_, wb * k_)))
            palm.append(add((u * k_, v * k_, wp * k_)))
        sl = add((u * k_, vL * k_, (0.7 * wT + 0.75 * wB) / 2 * k_))
        st = add((u * k_, vR * k_, (0.7 * wT + 0.75 * wB) / 2 * k_))
        return back + [sl] + palm[::-1] + [st]
    rings = []
    for i, (u, vL, vR, wT, wB) in enumerate(HAND_RINGS):
        rings.append(palm_ring(u, vL, vR, wT, wB, pads=(0, 16, 20, 0)[i]))
    # the knuckles' ring
    back = [add((ub * k_, v * k_, w * k_)) for v, ub, w in zip(KNUCKLE_V, KNUCKLE_U_BACK, KNUCKLE_W_BACK)]
    palm = [add((up * k_, v * k_, w * k_)) for v, up, w in zip(KNUCKLE_V, KNUCKLE_U_PALM, KNUCKLE_W_PALM)]
    (tv, tu, tw), (lv, lu, lw) = KNUCKLE_SIDES
    sl = add((lu * k_, lv * k_, lw * k_))
    st = add((tu * k_, tv * k_, tw * k_))
    rings.append(back + [sl] + palm[::-1] + [st])
    N = 20
    B = lambda r, i: rings[r][i]                 # noqa: E731  back point i (0 thumb edge .. 8 little edge)
    Pm = lambda r, i: rings[r][18 - i]           # noqa: E731  palm point i
    ST, SL = 19, 9
    skip = {(2, 18 - 1), (2, 18 - 0)}            # (ring 2 to 3: the quads from palm 1 to palm 0 and palm 0 to the side)
    for r in range(len(rings) - 1):
        for j in range(N):
            if (r, j) in skip:
                continue
            k = (j + 1) % N
            F.append(([rings[r][j], rings[r][k], rings[r + 1][k], rings[r + 1][j]], ""))
    kr = len(rings) - 1
    F.append(([Pm(kr, 0), rings[kr][ST], B(kr, 0)], ""))
    F.append(([B(kr, 8), rings[kr][SL], Pm(kr, 8)], ""))
    spread = pose["spread"]
    curls = pose["curl"]
    info = {"rings": rings, "fingers": {}, "joints": {}}

    def hexring(c, a, kk, W):
        hw = W / 2.0 / 0.866
        ht = 0.46 * W
        out = []
        for th in (30, 90, 150, 210, 270, 330):
            s, co = math.sin(math.radians(th)), math.cos(math.radians(th))
            out.append(add(c + a * co * hw + kk * s * ht * (1.0 if s > 0 else 0.9)))
        return out
    U, V, Wv = np.array((1.0, 0, 0)), np.array((0, 1.0, 0)), np.array((0, 0, 1.0))
    for fi, (name, ku, vc, wc, length, widths) in enumerate(HAND_FINGERS):
        root = [B(kr, 2 * fi), B(kr, 2 * fi + 1), B(kr, 2 * fi + 2), Pm(kr, 2 * fi + 2), Pm(kr, 2 * fi + 1), Pm(kr, 2 * fi)]
        J0 = np.array((ku, vc, wc)) * k_
        L_ = length * k_
        d = _rot(U, Wv, spread[fi])
        a = _rot(V, Wv, spread[fi])
        kk = Wv.copy()

        def bend(d, kk, deg, a):
            return _rot(d, a, deg), _rot(kk, a, deg)      # (about v: + turns the finger toward the palm)
        c1, c2, c3 = curls[fi]
        d1, k1 = bend(d, kk, c1, a)
        d2, k2 = bend(d1, k1, c2, a)
        d3, k3 = bend(d2, k2, c3, a)
        prox, mid, dist = (L_ * f for f in FINGER_SEGS)
        pip = J0 + d1 * prox
        dip = pip + d2 * mid
        tipw = widths[3] * k_
        half = lambda x, y: (x + y) / np.linalg.norm(x + y)   # noqa: E731
        frs = [hexring(J0 + d1 * prox * 0.45, a, k1, widths[0] * k_),
               hexring(pip, a, half(k1, k2), widths[1] * k_),
               hexring(dip, a, half(k2, k3), widths[2] * k_),
               hexring(dip + d3 * (dist - 0.42 * tipw), a, k3, widths[3] * k_)]
        info.setdefault("frames", {})[name] = [(J0 + d1 * prox * 0.45, a, k1, widths[0] * k_), (pip, a, half(k1, k2), widths[1] * k_), (dip, a, half(k2, k3), widths[2] * k_), (dip + d3 * dist, a, k3, widths[3] * k_ * 0.8)]
        allr = [root] + frs
        for r0, r1 in zip(allr, allr[1:]):
            for j in range(6):
                F.append(([r0[j], r0[(j + 1) % 6], r1[(j + 1) % 6], r1[j]], name))
        tip = add(dip + d3 * dist - k3 * 0.12 * tipw)
        for j in range(6):
            F.append(([frs[-1][j], frs[-1][(j + 1) % 6], tip], name))
        info["fingers"][name] = (allr, tip)
        info["joints"][name] = [J0, pip, dip, dip + d3 * dist]
    # the thumb, from the palm's side between the thenar's ring and the ring below the knuckles
    root = [Pm(2, 1), Pm(2, 0), rings[2][ST], rings[3][ST], Pm(3, 0), Pm(3, 1)]
    R0 = np.mean([P[i] for i in root], axis=0)
    yaw, pitch, t1, t2 = pose["thumb"]
    dT = math.cos(math.radians(pitch)) * (math.cos(math.radians(yaw)) * U + math.sin(math.radians(yaw)) * V) - math.sin(math.radians(pitch)) * Wv
    kT = V * 0.6 + Wv * 0.8
    kT = kT - dT * np.dot(kT, dT)
    kT /= np.linalg.norm(kT)
    aT = np.cross(dT, kT)
    m1, mid_, dist_ = THUMB_SEGS
    base = R0 + dT * 0.012
    mcp = R0 + dT * m1
    d2, k2 = _rot(dT, aT, -t1), _rot(kT, aT, -t1)
    ip = mcp + d2 * mid_
    d3, k3 = _rot(d2, aT, -t2), _rot(k2, aT, -t2)
    trs = []
    prev = [P[i] for i in root]
    for c, kk, W, dv in ((base, kT, THUMB_W[0], dT), (mcp, (kT + k2) / 2, THUMB_W[1], (dT + d2) / 2),
                         (ip, (k2 + k3) / 2, THUMB_W[2], (d2 + d3) / 2), (ip + d3 * (dist_ - 0.42 * THUMB_W[3]), k3, THUMB_W[3], d3)):
        kk = kk / np.linalg.norm(kk)
        ac = np.cross(kk, dv)
        ring = hexring(c, ac / np.linalg.norm(ac), kk, W)
        info.setdefault("frames", {}).setdefault("thumb", []).append((c, ac / np.linalg.norm(ac), kk, W))
        ordered = aligned(prev, [P[i] for i in ring])
        idx = [ring[[tuple(P[i]) for i in ring].index(tuple(q))] for q in ordered]
        trs.append(idx)
        prev = [P[i] for i in idx]
    allr = [root] + trs
    for r0, r1 in zip(allr, allr[1:]):
        for j in range(6):
            F.append(([r0[j], r0[(j + 1) % 6], r1[(j + 1) % 6], r1[j]], "thumb"))
    tip = add(ip + d3 * dist_ - k3 * 0.004)
    for j in range(6):
        F.append(([trs[-1][j], trs[-1][(j + 1) % 6], tip], "thumb"))
    info["fingers"]["thumb"] = (allr, tip)
    info["joints"]["thumb"] = [R0, mcp, ip, ip + d3 * dist_]
    info["thumb_back"] = k2
    return np.array(P), F, info


# Twelfth round (FIGURE_HEADS.md): his hand is Blender Studio's `Hand - Stylized` (CC0) un-subdivided twice, fitted to
# the lofted hand's measured joints (the hands sheet's palm, back and thumb views, as hand_local was): for each finger
# its knuckle and four sections (the base finger's own, at the same shares of its length) laid on the lofted finger's
# rings, middle and four sides (so the fingers come out as thick as the sheet's sausage fingers); the thumb likewise;
# the palm by its wrist, middle and knuckle rows' four extremes. A thin plate carries every other point. Posed the same
# way: the targets are the lofted hand's in that pose.
_HAND_BASE = {}


def hand_base():
    """The base hand in the lofted hand's frame (u along from the wrist, v across toward the thumb, w out of its back):
    its points, faces, per-face {point: uv}, the sections used as landmarks, the wrist's open edge."""
    if _HAND_BASE:
        return _HAND_BASE
    ob = base_object("Hand - Stylized")
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    for _ in range(2):
        bmesh.ops.unsubdivide(bm, verts=bm.verts)
    bm.verts.index_update()
    bm.verts.ensure_lookup_table()
    uvl = bm.loops.layers.uv.active
    P0 = np.array([v.co for v in bm.verts], float)
    F = [[v.index for v in f.verts] for f in bm.faces]
    U = [{l.vert.index: tuple(l[uvl].uv) for l in f.loops} for f in bm.faces]
    bm.free()
    drop_object(ob)
    # (the bundle's hand: fingers down -Z, back of the hand toward -Y, thumb toward +X: a right hand, as the lofted)
    L = np.stack([-P0[:, 2], P0[:, 0], -P0[:, 1]], 1)
    L[:, 0] -= L[:, 0].min()
    # the wrist's cap taken off: its open edge is where the forearm joins
    keep = [i for i, f in enumerate(F) if not all(L[v, 0] < 0.002 for v in f)]
    F = [F[i] for i in keep]
    U = [U[i] for i in keep]
    wrist = max(loops_of(F), key=len)
    # the fingers: the parts below the webs (connected through faces wholly past u = 0.15), ordered across
    u_split = 0.15
    fin = L[:, 0] > u_split
    parent = list(range(len(L)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for f in F:
        if all(fin[v] for v in f):
            for v in f[1:]:
                parent[find(v)] = find(f[0])
    comps = {}
    for v in np.where(fin)[0]:
        comps.setdefault(find(v), []).append(v)
    comps = sorted((c for c in comps.values() if len(c) >= 6), key=lambda c: L[c, 1].mean())
    # (little, ring, middle, index from his little finger's side across to the thumb's)
    fingers = {}
    for name, c in zip(("little", "ring", "middle", "index"), comps[-4:]):
        c = np.array(c)
        v_mid = L[c, 1].mean()
        half_v = max(L[c, 1].max() - L[c, 1].min(), 0.01) / 2.0 + 0.004
        # the whole finger: its points past the knuckles' row within its own column
        col = np.where((np.abs(L[:, 1] - v_mid) < half_v) & (L[:, 0] > 0.125) & (L[:, 1] < 0.06))[0]
        fingers[name] = col
    thumb = np.where((L[:, 1] > 0.052) & (L[:, 0] > 0.02))[0]
    fingers["thumb"] = thumb
    _HAND_BASE.update(P=L, F=F, U=U, wrist=wrist, fingers=fingers)
    print("CAPTAIN base hand: %d points, %d faces (%d triangles), fingers %s" % (len(L), len(F), sum(len(f) - 2 for f in F),
          {k: len(v) for k, v in fingers.items()}))
    return _HAND_BASE


def _section(P, ids, axis, origin, at, width):
    """The base finger's section at distance `at` along its axis: (middle, across extent, back extent)."""
    d = (P[ids] - origin) @ axis
    sel = ids[np.abs(d - at) < width]
    if len(sel) < 3:
        sel = ids[np.argsort(np.abs(d - at))[:4]]
    return P[sel].mean(0), sel


def hand_local(pose):
    """The hand in its own frame (metres): the base hand fitted to the lofted hand's joints in this pose. Gives what
    loft_hand_local gives (points, faces [(index list, piece)], info with rings, fingers, joints, thumb_back) and the
    base mesh's UVs per face (info["uv"]: {point: uv})."""
    hb = hand_base()
    Pb = hb["P"]
    _, _, ref = loft_hand_local(pose)
    src, dst = [], []
    U_, V_, W_ = np.array((1.0, 0, 0)), np.array((0, 1.0, 0)), np.array((0, 0, 1.0))
    for name in FINGERS:
        ids = hb["fingers"][name]
        fr = ref["frames"][name]
        J = ref["joints"][name]
        u0 = 0.135
        tip_u = Pb[ids, 0].max()
        Lb = tip_u - u0
        origin = np.array((u0, Pb[ids, 1].mean(), Pb[ids, 2].mean()))
        Lr = sum(np.linalg.norm(J[i + 1] - J[i]) for i in range(3))
        # the knuckle
        c, _ = _section(Pb, ids, U_, origin, 0.0, 0.006)
        src.append(c)
        dst.append(J[0])
        for (cc, a, kk, Wd), share in zip(fr, (0.45 * FINGER_SEGS[0], FINGER_SEGS[0], FINGER_SEGS[0] + FINGER_SEGS[1], 0.97)):
            c, sel = _section(Pb, ids, U_, origin, share * Lb, 0.006)
            hv = max((Pb[sel, 1].max() - Pb[sel, 1].min()) / 2.0, 0.003)
            hw = max((Pb[sel, 2].max() - Pb[sel, 2].min()) / 2.0, 0.003)
            ht = 0.46 * Wd
            for s_src, s_dst in ((c, cc), (c + V_ * hv, cc + a * Wd / 2.0), (c - V_ * hv, cc - a * Wd / 2.0),
                                 (c + W_ * hw, cc + kk * ht), (c - W_ * hw, cc - kk * ht * 0.9)):
                src.append(s_src)
                dst.append(s_dst)
    # the thumb: its axis through its points (root nearest the palm's middle), sections at the lofted thumb's shares
    ids = hb["fingers"]["thumb"]
    Q = Pb[ids]
    cen = Q.mean(0)
    ax = np.linalg.svd(Q - cen)[2][0]
    t = (Q - cen) @ ax
    if t[np.argmax(Q[:, 0])] < 0:
        ax, t = -ax, -t
    root = cen + ax * t.min()
    Lb = t.max() - t.min()
    fr = ref["frames"]["thumb"]
    J = ref["joints"]["thumb"]
    chain = [J[0]] + [f[0] for f in fr] + [J[3]]
    seg = np.cumsum([0.0] + [np.linalg.norm(chain[i + 1] - chain[i]) for i in range(len(chain) - 1)])
    across = np.cross(ax, W_)
    across /= np.linalg.norm(across)
    back = np.cross(across, ax)
    for (cc, a, kk, Wd), s in zip(fr, seg[1:-1] / seg[-1]):
        c, sel = _section(Pb, ids, ax, root, s * Lb, 0.006)
        ha = max(float(np.ptp((Pb[sel] - c) @ across)) / 2.0, 0.003)
        hk = max(float(np.ptp((Pb[sel] - c) @ back)) / 2.0, 0.003)
        for s_src, s_dst in ((c, cc), (c + across * ha, cc + a * Wd / 2.0), (c - across * ha, cc - a * Wd / 2.0),
                             (c + back * hk, cc + kk * 0.46 * Wd), (c - back * hk, cc - kk * 0.42 * Wd)):
            src.append(s_src)
            dst.append(s_dst)
    tip_i = ids[np.argmax(t)]
    src.append(Pb[tip_i])
    dst.append(J[3])
    # the palm: the wrist's, the middle's and the knuckles' rows, their four extremes (the thumb's points left out)
    k_ = HAND_PX
    for ub, (ur, vL, vR, wT, wB) in ((0.0, HAND_RINGS[0]), (0.065, HAND_RINGS[2]), (0.118, HAND_RINGS[3])):
        band = np.where((np.abs(Pb[:, 0] - ub) < 0.008) & (Pb[:, 1] < 0.05))[0]
        mid_v = (Pb[band, 1].max() + Pb[band, 1].min()) / 2.0
        mid_w = (Pb[band, 2].max() + Pb[band, 2].min()) / 2.0
        for b_pt, r_pt in (((ub, Pb[band, 1].min(), mid_w), (ur, vL, (wT + wB) / 2.0)),
                           ((ub, Pb[band, 1].max(), mid_w), (ur, vR, (wT + wB) / 2.0)),
                           ((ub, mid_v, Pb[band, 2].max()), (ur, (vL + vR) / 2.0, wT)),
                           ((ub, mid_v, Pb[band, 2].min()), (ur, (vL + vR) / 2.0, wB))):
            src.append(np.array(b_pt))
            dst.append(np.array(r_pt) * k_)
    P = tps_warp(Pb, np.array(src), np.array(dst), smooth=1e-6)
    # faces, named by the finger they lie on
    sets = {n: set(v.tolist()) for n, v in hb["fingers"].items()}
    F = []
    for f in hb["F"]:
        piece = next((n for n in ("thumb",) + FINGERS if all(v in sets[n] for v in f)), "")
        F.append((list(f), piece))
    info = {"rings": [list(hb["wrist"]), []], "fingers": {}, "joints": ref["joints"], "thumb_back": ref["thumb_back"],
            "uv": hb["U"]}
    for n in FINGERS + ("thumb",):
        ids = np.array(sorted(sets[n]))
        far = int(ids[np.argmax(np.linalg.norm(P[ids] - ref["joints"][n][0], axis=1))])
        info["fingers"][n] = ([[], [int(i) for i in ids if i != far]], far)
        # (the tip rounded: the base finger's end is a point, stretched into a claw by the fit; drawn back toward the
        # end joint so the end is a round pad)
        J = ref["joints"][n]
        ax = J[3] - J[2]
        ax /= max(np.linalg.norm(ax), 1e-9)
        t = (P[ids] - J[3]) @ ax
        pull = np.clip((t + 0.012) / 0.012, 0.0, 1.0) * 0.45 * np.maximum(t + 0.012, 0.0)
        P[ids] -= ax[None, :] * pull[:, None]
    # (the knuckles' row: the fingers' points nearest their knuckles)
    kn = []
    for n in FINGERS:
        ids = np.array(sorted(sets[n]))
        kn += [int(i) for i in ids[np.argsort(np.linalg.norm(P[ids] - ref["joints"][n][0], axis=1))[:2]]]
    info["rings"][1] = kn + kn[:1]
    return P, F, info


def bridge_uneven(M, a, b, part, axis):
    """Triangles between two closed rings of different counts (a zipper by angle round `axis`)."""
    Pa = np.array([M.P[i] for i in a])
    Pb = np.array([M.P[i] for i in b])
    ax = np.asarray(axis, float) / np.linalg.norm(axis)
    e1 = np.cross(ax, (1.0, 0, 0) if abs(ax[0]) < 0.9 else (0, 1.0, 0))
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(ax, e1)

    def ang(Pr):
        c = Pr.mean(0)
        return np.arctan2((Pr - c) @ e2, (Pr - c) @ e1)

    def sense(t):
        return np.sign(np.sum(np.angle(np.exp(1j * (np.roll(t, -1) - t)))))
    ta, tb = ang(Pa), ang(Pb)
    a, b = list(a), list(b)
    if sense(ta) < 0:
        a, ta = a[::-1], ta[::-1]
    if sense(tb) < 0:
        b, tb = b[::-1], tb[::-1]
    s = int(np.argmin(ta))
    a, ta = a[s:] + a[:s], np.concatenate([ta[s:], ta[:s]])
    ta = np.unwrap(ta)
    j0 = int(np.argmin(np.abs(np.angle(np.exp(1j * (tb - ta[0]))))))
    b, tb = b[j0:] + b[:j0], np.concatenate([tb[j0:], tb[:j0]])
    # (fourteenth round: the first difference wrapped into a half turn either way; raw, it could be nearly a whole
    # turn when ta[0] and tb[0] lay either side of the half-turn line, and the zipper then folded over itself)
    tb = ta[0] + np.unwrap(np.angle(np.exp(1j * (tb - ta[0]))))
    n, m = len(a), len(b)
    ta = np.append(ta, ta[0] + math.tau)
    tb = np.append(tb, tb[0] + math.tau)
    i = j = 0
    while i < n or j < m:
        if j >= m or (i < n and ta[i + 1] <= tb[j + 1]):
            M.face([a[i], a[(i + 1) % n], b[j % m]], part)
            i += 1
        else:
            M.face([a[i % n], b[(j + 1) % m], b[j]], part)
            j += 1


def hand(M, wrist_ring, side, W, L, joints, pose="relaxed"):
    """His hand on the wrist ring: hand_local's hand, its back facing out and a little forward (36 degrees round from
    straight out), joined to the forearm's last ring by a zipper of triangles."""
    if HAND_FIT:
        return place_base_hand(M, wrist_ring, side, W, L, joints)
    sfx = "_l" if side > 0 else "_r"
    part = "hand" + sfx
    X = Vector((1, 0, 0))
    F_ = Vector((0, -1, 0))
    A = (X - L * L.x).normalized()
    tw = math.radians(36.0)
    Tb = A * math.cos(tw) + F_ * math.sin(tw)          # the back of the hand
    Wd = -A * math.sin(tw) + F_ * math.cos(tw)         # across, toward the thumb
    O = np.array(W + L * 0.012)
    Lv, Wv, Tv = np.array(L), np.array(Wd), np.array(Tb)
    Pl, Fl, info = hand_local(HAND_POSES[pose])

    def world(q):
        return mirror_x(O + Lv * q[0] + Wv * q[1] + Tv * q[2], side)
    ids = [M.add(world(q), part) for q in Pl]
    huv = M.tag.setdefault("hand_uv", {})
    for k, (f, piece) in enumerate(Fl):
        M.face([ids[i] for i in f], part + ("_" + piece if piece else ""))
        if "uv" in info:
            # (twelfth round: the base hand's own UVs, by point, so a face turned over keeps them)
            huv[len(M.faces) - 1] = {ids[v]: q for v, q in info["uv"][k].items()}
    for fname, (rings, tip) in info["fingers"].items():
        for r in rings[1:]:
            for i in r:
                M.part[ids[i]] = part + "_" + fname
        M.part[ids[tip]] = part + "_" + fname
        M.tag["finger_rings%s_%s" % (sfx, fname)] = [[ids[i] for i in r] for r in rings]
        M.tag["finger_ends%s_%s" % (sfx, fname)] = [ids[tip], -1]
        joints["%s%s" % (fname, sfx)] = [Vector(world(q)) for q in info["joints"][fname]]
    hr = [[ids[i] for i in r] for r in info["rings"]]
    bridge_uneven(M, wrist_ring, hr[0], part, np.array(mirror_x(Lv, side)))
    M.tag["hand_rings" + sfx] = [wrist_ring] + hr
    joints["thumb_back%s" % sfx] = np.array(mirror_x(Wv * info["thumb_back"][1] + Tv * info["thumb_back"][2] + Lv * info["thumb_back"][0], side))
    joints["hand_frame%s" % sfx] = tuple(np.array(mirror_x(v, side)) for v in (Tv, Wv, Lv))
    joints["knuckles%s" % sfx] = Vector(world(np.mean([Pl[i] for i in info["rings"][-1][:9]], axis=0)))


# ------------------------------------------------------------------------------------------------------------------
# Thirteenth round (the user: "his hands still seem poor quality compared to like twilight princess hands", "Captains
# current hands also seem too small"): his hand is Blender Studio's `Hand - Stylized` (CC0) fitted STRAIGHT to the hands
# sheet, not to the lofted hand, by the method that worked for the older brother (tools/build_brother.py: base_hand_fit,
# pose_hand, place_base_hand; ported here, that file left alone). The sheet's back, palm and thumb-side views are first
# stood upright side by side in one working picture (fingers up; the back view with the thumb to the right; the palm
# view mirrored, so one projection serves both; the thumb-side view with the back of the hand to the right). The hand
# is worked on in its own frame: a across toward the thumb, b out of its back, l along from the wrist; on him (a, b, l)
# is hand()'s (Wd, Tb, L). Fitted flat in the sheet's own pose, painted from the sheet in that pose, then posed by
# turning the digits about their joints.
HAND_FIT = "--loft-hand" not in ARGS
HANDS_SHEET = os.path.join(ART, "concept_captain_hands.jpg")
# (nineteenth round, the fourth critic: "too small for the arms, about 75% of the concept's size against the forearm";
# the user: "Captains current hands also seem too small". Measured on the body sheet's front view over the built model:
# the sheet's fingertips hang 2.5 to 3 cm below the model's and its thumb further out, about 15% more hand, not the
# critic's 25 to 30%: the sheet wins. The hands sheet's own scale is grown by HAND_GROW, so every fit to it grows too.)
HAND_GROW = 1.15
HAND_SX = HAND_PX * HAND_GROW      # metres a pixel of the hands sheet (its wrist to middle fingertip, 20.3 cm before the grow)
HAND_LEN = 0.203 * HAND_GROW
HAND_LOOP_L = 0.012                # the hand's open loop stands this far beyond the wrist ring
HAND_UNSUBDIV = int(arg("--hand-unsub", "0"))   # (twentieth round: 2 with bevel_fingers, about 1,000 triangles a hand)
HAND_COLLAPSE = float(arg("--hand-collapse", "0.36"))   # (twenty-first round: the full base hand collapsed to this share)
HAND_TOP = 80                      # each view's top row in the working picture
# each view: its box in the sheet (columns, rows), quarter turns (numpy's rot90: + counter-clockwise), mirrored, and the
# column it is put at in the working picture
HAND_VIEW_BOX = {"back": ((150, 110, 1060, 780), 1, False, 50), "palm": ((1150, 70, 1820, 860), 0, True, 800),
                 "thumb": ((1850, 230, 2700, 620), -1, False, 1550)}
HAND_COLS = {"back": (50, 720), "palm": (800, 1470), "thumb": (1550, 1940)}
HAND_ROWS = (70, 650)              # rows fitted and compared (the wrist's crease is about row 700)
HAND_DROP_MORE = 0          # (tried 5: the count stayed 992 for the two hands, only moved between palm and fingers)
# (fifteenth round, the second critic: "fused C-shaped claws": the brother's gentler hang, each finger curled a little
# more than the one before it from the index to the little finger, the fingers a little apart, the thumb less tucked)
# (seventeenth round, the third critic: "fingers clumped together, partly fused at the base ... relax the curl ...
# rotate the thumb out about 30 degrees": the fingers no longer drawn together, the thumb swung out off the palm)
HAND_POSE_RELAXED = {"curl": {"index": (0.0, 0.05, 0.03), "middle": (0.03, 0.08, 0.05), "ring": (0.06, 0.11, 0.06),
                              "little": (0.09, 0.14, 0.08)}, "together": 0.35, "thumb_in": 0.3, "thumb_fwd": 0.55, "thumb_curl": 0.12}
HAND_POSE_THUMBVIEW = {"curl": (0.12, 0.08, 0.06), "together": 0.0, "thumb_in": 0.0, "thumb_fwd": 0.0, "thumb_curl": 0.1}
HAND_THUMB_FAT = (1.12, 1.3)       # the thumb fuller round its line: its back half, its palm half
HAND_WRIST_EASE = (0.75, 0.35)    # how far the forearm's last ring and the one before it are drawn to the hand's wrist
HB = {}


def _grow(mk, n):
    for _ in range(n):
        mk = mk | np.roll(mk, 1, 0) | np.roll(mk, -1, 0) | np.roll(mk, 1, 1) | np.roll(mk, -1, 1)
    return mk


def _shrink(mk, n):
    for _ in range(n):
        mk = mk & np.roll(mk, 1, 0) & np.roll(mk, -1, 0) & np.roll(mk, 1, 1) & np.roll(mk, -1, 1)
    return mk


def _fill_holes(mk):
    reach = np.zeros_like(mk)
    reach[0], reach[-1], reach[:, 0], reach[:, -1] = ~mk[0], ~mk[-1], ~mk[:, 0], ~mk[:, -1]
    free = ~mk
    for _ in range(4000):
        n = reach | ((np.roll(reach, 1, 0) | np.roll(reach, -1, 0) | np.roll(reach, 1, 1) | np.roll(reach, -1, 1)) & free)
        if (n == reach).all():
            break
        reach = n
    return ~reach


def hand_sheet():
    """The working picture (HB["pix"], HB["mask"]): the hands sheet's back, palm and thumb-side views stood upright;
    HB["tip"] the back view's middle fingertip; HB["ink"] the anchor tattoo's pixels (left out of the paint: tattoos
    are a separate movable overlay)."""
    if "pix" in HB:
        return
    raw = load_picture(HANDS_SHEET)
    bg = np.median(np.concatenate([raw[:40, :40].reshape(-1, 3), raw[-40:, -40:].reshape(-1, 3)]), 0)
    d = np.abs(raw - bg).max(-1)
    m = d > 0.07
    lines = np.where((np.abs(raw[:, 20:80] - bg).max(-1) > 0.025).mean(1) > 0.7)[0]
    for r in lines:
        m[max(r - 2, 0):r + 3] = d[max(r - 2, 0):r + 3] > 0.16
    H, W = 1040, 2000
    pix = np.ones((H, W, 3), np.float32) * bg
    mask = np.zeros((H, W), bool)
    for name, ((x0, y0, x1, y1), k, flip, c0) in HAND_VIEW_BOX.items():
        sub = _fill_holes(_grow(_shrink(m[y0:y1, x0:x1], 2), 2))
        p = raw[y0:y1, x0:x1]
        if flip:
            sub, p = sub[:, ::-1], p[:, ::-1]
        sub, p = np.rot90(sub, k), np.rot90(p, k)
        top = int(np.where(sub.any(1))[0][0])
        r0 = HAND_TOP - top
        h_, w_ = sub.shape
        rs, re_ = max(r0, 0), min(r0 + h_, H)
        pix[rs:re_, c0:c0 + w_] = p[rs - r0:re_ - r0]
        mask[rs:re_, c0:c0 + w_] = sub[rs - r0:re_ - r0]
    lum = pix.mean(-1)
    ink = mask & ((pix[..., 0] - pix[..., 2]) < 0.035) & (lum < 0.5)
    ink = _grow(ink, 5) & mask
    c0, c1 = HAND_COLS["back"]
    rows = np.where(mask[:, c0:c1].any(1))[0]
    cols = np.where(mask[rows[0]:rows[0] + 4, c0:c1].any(0))[0]
    HB.update(pix=pix, mask=mask, ink=ink, tip=(float(cols.mean() + c0), float(rows[0])))
    if OUT:
        os.makedirs(OUT, exist_ok=True)
        show = pix * 0.6
        show[mask] = show[mask] * 0.6 + np.array((0.4, 0.05, 0.05))
        show[ink] = (0.1, 0.9, 0.2)
        save_rgb(os.path.join(OUT, "hand_sheet.png"), show)
    print("CAPTAIN hands sheet stood upright: tip %s, ink %d px" % (HB["tip"], int(ink.sum())))


def load_base_hand():
    """`Hand - Stylized` from the bundle, un-subdivided HAND_UNSUBDIV times: its points (the bundle's frame) and faces."""
    want = "Hand-Stylized"
    with bpy.data.libraries.load(BUNDLE, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n.replace(" ", "") == want]
    o = dst.objects[0]
    bpy.context.scene.collection.objects.link(o)
    o.modifiers.clear()
    if o.data.shape_keys:
        for k in o.data.shape_keys.key_blocks:
            k.value = 0.0
    if HAND_UNSUBDIV:
        m = o.modifiers.new("un", "DECIMATE")
        m.decimate_type = "UNSUBDIV"
        m.iterations = HAND_UNSUBDIV
    if HAND_COLLAPSE:
        # (twenty-first round, as the brother's builder: the FULL base hand collapsed, so each finger keeps about eight
        # points round and its rings stay even; un-subdividing made four-sided fingers or a diamond lattice)
        m2 = o.modifiers.new("co", "DECIMATE")
        m2.decimate_type = "COLLAPSE"
        m2.ratio = HAND_COLLAPSE
        m2.use_symmetry = False
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = o.evaluated_get(dg)
    me = ev.to_mesh()
    P = np.array([tuple(v.co) for v in me.vertices], float)
    faces = [list(p.vertices) for p in me.polygons]
    ev.to_mesh_clear()
    bpy.data.objects.remove(o, do_unlink=True)
    return P, faces


def sheet_fingers():
    """The back view's digits as chains of runs followed down from their tips: each one's tip (column, row), its
    middle line's direction toward the tip (in the picture), its median width (pixels) and the row it joins the palm.
    In order little, ring, middle, index, thumb."""
    m = HB["mask"]
    c0, c1 = HAND_COLS["back"]
    chains = []
    for r in range(70, 570):
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
    chains = [c for c in chains if len(c["pts"]) > 37]
    out = []
    for c in chains:
        pts = np.array(c["pts"])
        use = pts[15:-8] if len(pts) > 37 else pts
        k, _ = np.polyfit(use[:, 1], use[:, 0], 1)
        d = np.array((-k, -1.0))
        d /= np.linalg.norm(d)
        out.append({"tip": (float(pts[0, 0]), float(c["top"])), "dir": d, "width": float(np.median(use[:, 2])),
                    "join": int(c["end"] or 570), "col": float(pts[:, 0].mean())})
    fingers = sorted([c for c in out if c["tip"][1] < 300], key=lambda c: c["col"])
    thumb = [c for c in out if c["tip"][1] >= 300]
    print("CAPTAIN sheet digits: %s" % json.dumps([(round(c["tip"][0]), round(c["tip"][1]), round(c["width"]), c["join"], [round(v, 2) for v in c["dir"]]) for c in fingers + thumb]))
    if len(fingers) != 4 or not thumb:
        raise RuntimeError("the hands sheet's back view did not give four fingers and a thumb")
    return fingers + [max(thumb, key=lambda c: c["col"])]


def to_back_view(C):
    t = HB["tip_mid"]
    return np.stack([HB["tip"][0] + (C[:, 0] - t[0]) / HAND_SX, HB["tip"][1] - (C[:, 2] - t[2]) / HAND_SX], 1)


def from_back_view(c, r):
    t = HB["tip_mid"]
    return np.array((t[0] + (c - HB["tip"][0]) * HAND_SX, 0.0, t[2] - (r - HB["tip"][1]) * HAND_SX))


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


# Twentieth round (the fifth critic: "jagged shards" on the fingers). Un-subdivided ONCE the base hand's fingers came
# out as a diamond lattice (each ring's points alternately 8 mm ahead and behind), a saw-tooth outline whatever was
# smoothed after; un-subdivided twice they are clean square rings, four corners round. So: twice, and every edge running
# along a digit is bevelled (a share HAND_BEVEL of its faces either side), which makes each digit eight-sided with the
# same clean rings. About 480 triangles a hand.
HAND_BEVEL = float(arg("--hand-bevel", "0.3"))


def bevel_fingers(C, faces, label, loop, names):
    import bmesh
    bm = bmesh.new()
    vs = [bm.verts.new(tuple(map(float, p))) for p in C]
    for f in faces:
        bm.faces.new([vs[i] for i in f])
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    bm.edges.ensure_lookup_table()
    axes = {n: digit_axis(C, np.where(label == n)[0])[1] for n in names}
    pick = []
    for e in bm.edges:
        a, b = e.verts[0].index, e.verts[1].index
        if label[a] != label[b] or label[a] not in axes:
            continue
        d = C[b] - C[a]
        if abs(float(d @ axes[label[a]])) > 0.7 * float(np.linalg.norm(d)):
            pick.append(e)
    bmesh.ops.bevel(bm, geom=pick, offset=HAND_BEVEL * 100.0, offset_type="PERCENT", segments=1, profile=0.5,
                    affect="EDGES", clamp_overlap=True)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4], quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.verts.index_update()
    bm.verts.ensure_lookup_table()
    P = np.array([tuple(v.co) for v in bm.verts], float)
    nf = [[v.index for v in f.verts] for f in bm.faces]
    bm.free()
    near = np.array([int(np.argmin(np.linalg.norm(C - p, axis=1))) for p in P])
    new_loop = [int(np.argmin(np.linalg.norm(P - C[v], axis=1))) for v in loop]
    print("CAPTAIN fingers bevelled: %d edges along them, %d -> %d triangles" % (
        len(pick), sum(len(f) - 2 for f in faces), sum(len(f) - 2 for f in nf)))
    return P, nf, label[near], new_loop


def base_hand_fit():
    """The base hand in its own frame fitted to the sheet's back view in the sheet's pose (HB: C, flat, faces,
    label, J, loop); then its back, palm and thumb-side silhouettes compared."""
    if "flat" in HB:
        return
    hand_sheet()
    P, faces = load_base_hand()
    C = np.stack([P[:, 0], -P[:, 1], -P[:, 2]], 1)
    keep = [k for k, f in enumerate(faces) if C[f, 2].min() > 0.006]
    used = sorted({v for k in keep for v in faces[k]})
    remap = {v: i for i, v in enumerate(used)}
    C = C[used]
    faces = [[remap[v] for v in faces[k]] for k in keep]
    loop = max(loops_of(faces), key=len)
    if HAND_COLLAPSE:
        # (the collapsed stub's cut leaves a saw-toothed loop: its points brought to one height)
        C[loop, 2] = float(np.median(C[loop, 2]))
    print("CAPTAIN base hand: %d points, %d faces, %d triangles; wrist loop %d" % (len(C), len(faces), sum(len(f) - 2 for f in faces), len(loop)))
    adj = {}
    for f in faces:
        for i in range(len(f)):
            a, b = f[i], f[(i + 1) % len(f)]
            adj.setdefault(a, set()).add(b)
            adj.setdefault(b, set()).add(a)
    far = set(np.where(C[:, 2] > 0.145)[0].tolist())
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
    # (the triangle budget, 300 to 450 a hand: one ring of each finger taken out, the one between its middle and end
    # joints' rings, third from the tip; each of its points merged into its neighbour toward the palm)
    if HAND_UNSUBDIV >= 2:
        C, faces, label, loop = drop_finger_rings(C, faces, label, loop, names)
        C, faces, label, loop = drop_finger_rings(C, faces, label, loop, ("thumb",), nth=2)
    if HAND_BEVEL and HAND_UNSUBDIV >= 2:
        C, faces, label, loop = bevel_fingers(C, faces, label, loop, names + ("thumb",))
    for nth_ in [int(v) for v in arg("--hand-drop", "").split(",") if v]:
        # (twentieth round: rings taken out of the un-subdivided-once hand along each finger, regular quads kept)
        C, faces, label, loop = drop_finger_rings(C, faces, label, loop, names, nth=nth_)
        print("CAPTAIN hand ring %d dropped: %d triangles" % (nth_, sum(len(f) - 2 for f in faces)))
    if HAND_DROP_MORE:
        # (fourteenth round: under 450 a hand; a second ring of each finger out, the one over the knuckle's first
        # bone, between the middle joint and the knuckle)
        C, faces, label, loop = drop_finger_rings(C, faces, label, loop, names, nth=HAND_DROP_MORE)
    axes = {n: digit_axis(C, np.where(label == n)[0]) for n in names}
    axes["thumb"] = digit_axis(C, np.where((label == "thumb") & (C[:, 2] > 0.06))[0])
    print("CAPTAIN base hand labels: %s; %d triangles" % ({n: int((label == n).sum()) for n in names + ("thumb", "")}, sum(len(f) - 2 for f in faces)))
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
    digits = sheet_fingers()
    l_loop = float(C[loop, 2].mean())
    sl = (HAND_LEN - HAND_LOOP_L) / (J["middle"][3][2] - l_loop)
    webs = sorted(d["join"] for d in digits[:4])
    r_k = webs[1] + 27
    run = run_near(HB["mask"], r_k, HB["tip"][0], *HAND_COLS["back"])
    palm_s = (run[1] + 1 - run[0]) * HAND_SX
    band = (np.abs(C[:, 2] - J["middle"][0][2]) < 0.008) & (label != "thumb")
    sa = palm_s / float(C[band, 0].max() - C[band, 0].min())
    tc0, tc1 = HAND_COLS["thumb"]
    rr = run_near(HB["mask"], 636, (tc0 + tc1) / 2, tc0, tc1)
    wrist_s = (rr[1] + 1 - rr[0]) * HAND_SX if rr else 0.05
    sb = wrist_s / float(C[loop, 1].max() - C[loop, 1].min())
    sb = float(np.clip(sb, 0.8 * min(sa, sl), 1.25 * max(sa, sl)))
    o = np.array((0.0, 0.0, l_loop))
    S3 = np.array((sa, sb, sl))
    C = (C - o) * S3 + np.array((0.0, 0.0, HAND_LOOP_L))
    J = {n: [(p - o) * S3 + np.array((0.0, 0.0, HAND_LOOP_L)) for p in js] for n, js in J.items()}
    print("CAPTAIN hand scaled: across %.3f, back %.3f, along %.3f (sheet palm %.1f cm at row %d, wrist %.1f cm)" % (sa, sb, sl, palm_s * 100, r_k, wrist_s * 100))
    HB["tip_mid"] = J["middle"][3].copy()
    # 2. each digit turned (in the hand's plane) at its drawn tip and sized to its drawn width
    for n, dg in zip(names + ("thumb",), digits):
        ids = np.where(label == n)[0]
        piv = J[n][0]
        dm = J[n][3] - piv
        dm_len = float(np.linalg.norm(dm))
        dm /= dm_len
        tip_s = from_back_view(*dg["tip"])
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
        k = want / dm_len
        s = (C - piv) @ ds
        grow = np.where(s > 0, s * (k - 1.0), 0.0) * w
        C = C + ds[None, :] * grow[:, None]
        J[n] = [J[n][0]] + [p + ds * max(float(np.dot(p - piv, ds)), 0) * (k - 1.0) for p in J[n][1:]]
        across = np.array((ds[2], 0.0, -ds[0]))
        near = ids[np.abs(((C[ids] - piv) @ ds) - 0.5 * want) < 0.012]
        have = float(((C[near] - piv) @ across).max() - ((C[near] - piv) @ across).min()) if len(near) > 2 else 0.0
        want_w = dg["width"] * HAND_SX * abs(float(dg["dir"][1]))
        if have > 0.005:
            g = float(np.clip(want_w / have, 0.75, 1.5))
            ax_c = (C - piv) @ across
            cen = float(((C[near] - piv) @ across).mean())
            C = C + across[None, :] * ((ax_c - cen) * (g - 1.0) * w)[:, None]
            # (and as thick as wide by the same share: his fingers are round sausages, not flat)
            bb = C[:, 1] - float(C[near, 1].mean())
            C[:, 1] = C[:, 1] + bb * (g - 1.0) * w * 0.8
        if n == "thumb":
            # (his thumb a heavy one, the thenar's pad with it: fuller round its own line, most toward the palm)
            c_, d_ = digit_axis(C, ids)
            r_ = (C[ids] - c_) - np.outer((C[ids] - c_) @ d_, d_)
            fat = np.where(r_[:, 1] < 0, HAND_THUMB_FAT[1], HAND_THUMB_FAT[0])
            C[ids] = C[ids] + r_ * (fat - 1.0)[:, None] * w[ids][:, None]
        print("CAPTAIN hand %s: turned %.1f degrees, length times %.2f" % (n, math.degrees(a1 - a0), k))
    HB.update(C=C, faces=faces, label=label, J=J, loop=loop)
    # 3. the back view's outline: outline points moved onto the sheet's, the rest following
    for _ in range(12):
        hand_outline_round()
    shape_fingers()
    HB["flat"] = HB["C"].copy()
    # 4. (the brother's hand was 5 cm off in its thumb-side view) the thumb-side view's pose found by trying, then the
    # hand's thickness pulled onto that view's outline (the back of the hand and the palm, front to back only)
    hand_thumb_fit()
    round_fingertips()
    hand_silhouettes()
    if HAND_KEEP_TRIS or HAND_PLANAR:
        thin_hand(HAND_KEEP_TRIS)
    taubin_hand(HAND_TAUBIN)


# Nineteenth round (the fourth critic: "short, curled sausages ... no knuckles and no nails ... seen from the end, the
# fingers come out of a jagged slab"). Un-subdivided twice and a ring dropped from each finger, the base hand had four
# corners round a finger and three rings along it: square sausages with pointed ends whatever was done to them after.
# Now the base hand is un-subdivided ONCE (eight corners round a finger, a ring at each joint and between), fitted as
# before at that density, and only then collapsed (Blender's decimate, which keeps the triangles where the surface
# curves: the knuckles, the tips, the thumb's root, and gives up the flat back and palm) to HAND_KEEP_TRIS, its wrist
# loop held for the zip to the forearm. The practice: model or fit dense, reduce by quadric collapse (as game LODs are
# made). Alternative kept: --hand-unsub 2 and --hand-keep 0 build the eighteenth round's hand.
# Twentieth round (the fifth critic: "polygon shards on the outer edge of the palm and at fingertips"): the collapse
# left slivers that shaded as shards. Now the fitted hand keeps its regular quads (eight corners round each finger) and
# only its near-flat stretches (back of the hand, palm) are merged by a planar dissolve of HAND_PLANAR degrees, then
# triangulated; --hand-keep N (with --hand-planar 0) brings back the nineteenth round's collapse.
HAND_KEEP_TRIS = int(arg("--hand-keep", "0"))
HAND_PLANAR = float(arg("--hand-planar", "0"))


# (twentieth round, of the hand in grey: each finger a string of beads, every ring bulging a little out of line, which the
# fifth critic read as "jagged shards". Taubin smoothing (a shrink step then an inflate step, so the hand keeps its
# size) over the fitted hand, its wrist loop held: rounds)
HAND_TAUBIN = int(arg("--hand-taubin", "2"))


def taubin_hand(rounds, lam=0.5, mu=-0.53):
    if rounds <= 0:
        return
    P = HB["flat"].copy()
    E = edges_of(HB["faces"])
    deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
    held = np.zeros(len(P), bool)
    held[HB["loop"]] = True
    P0 = P.copy()
    for _ in range(rounds):
        for k in (lam, mu):
            acc = np.zeros_like(P)
            np.add.at(acc, E[:, 0], P[E[:, 1]])
            np.add.at(acc, E[:, 1], P[E[:, 0]])
            lap = acc / np.maximum(deg, 1)[:, None] - P
            lap[held] = 0.0
            P += k * lap
    print("CAPTAIN hand smoothed (Taubin, %d rounds): most a point moved %.1f mm" % (rounds, 1000 * float(np.linalg.norm(P - P0, axis=1).max())))
    HB["flat"] = P
    HB["C"] = P.copy()


def thin_hand(keep):
    """The fitted flat hand (HB) collapsed to about `keep` triangles, its wrist loop and the ring of faces on it held;
    labels, loop and the flat copy carried over by the nearest new point."""
    C, faces, label, loop = HB["flat"], HB["faces"], HB["label"], HB["loop"]
    n_before = sum(len(f) - 2 for f in faces)
    me = bpy.data.meshes.new("hand_thin")
    me.from_pydata([tuple(map(float, p)) for p in C], [], faces)
    me.update()
    ob = bpy.data.objects.new("hand_thin", me)
    bpy.context.scene.collection.objects.link(ob)
    held = set(loop)
    for f in faces:
        if held & set(f):
            held |= set(f)
    g = ob.vertex_groups.new(name="free")
    g.add([i for i in range(len(C)) if i not in held], 1.0, "REPLACE")
    dec = ob.modifiers.new("fewer", "DECIMATE")
    if HAND_PLANAR:
        dec.decimate_type = "DISSOLVE"
        dec.angle_limit = math.radians(HAND_PLANAR)
        dec.use_dissolve_boundaries = False
        dec.delimit = {"NORMAL"}
    else:
        dec.decimate_type = "COLLAPSE"
        dec.ratio = min(1.0, keep / max(n_before, 1))
        dec.vertex_group = "free"
        dec.use_collapse_triangulate = False
    bpy.context.view_layer.update()
    ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    m2 = ev.to_mesh()
    if HAND_PLANAR:
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(m2)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4], quad_method="BEAUTY", ngon_method="BEAUTY")
        bm.to_mesh(m2)
        bm.free()
    P = np.array([tuple(v.co) for v in m2.vertices], float)
    nf = [list(p.vertices) for p in m2.polygons]
    ev.to_mesh_clear()
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.meshes.remove(me)
    near = np.array([int(np.argmin(np.linalg.norm(C - p, axis=1))) for p in P])
    new_loop = [int(np.argmin(np.linalg.norm(P - C[v], axis=1))) for v in loop]
    # (spikes the collapse left, chiefly at the webs and the fingertips: a point standing further from its neighbours'
    # middle than 2.5 times the hand's median is drawn most of the way to it; the wrist loop held)
    E = edges_of(nf)
    deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
    fixed = np.zeros(len(P), bool)
    fixed[new_loop] = True
    spikes = 0
    for _ in range(4):
        acc = np.zeros_like(P)
        np.add.at(acc, E[:, 0], P[E[:, 1]])
        np.add.at(acc, E[:, 1], P[E[:, 0]])
        lap = acc / np.maximum(deg, 1)[:, None] - P
        m = np.linalg.norm(lap, axis=1)
        bad = (m > 2.5 * np.median(m)) & ~fixed
        spikes += int(bad.sum())
        P[bad] += 0.7 * lap[bad]
    print("CAPTAIN hand: %d spike moves after the collapse" % spikes)
    HB.update(flat=P, C=P.copy(), faces=nf, label=label[near], loop=new_loop)
    print("CAPTAIN hand thinned: %d -> %d triangles, wrist loop %d (worst %.1f mm)" % (
        n_before, sum(len(f) - 2 for f in nf), len(new_loop),
        1000 * max(float(np.linalg.norm(P[n] - C[v])) for n, v in zip(new_loop, loop))))


# Seventeenth round (the third critic: "claw mittens ... separate the fingers, round the tips, swing the thumb out from
# a real thenar pad, knuckles, the wrist step blended"): the brother's shape_fingers (tools/build_brother.py,
# 2026-11-18), copied unchanged in what it does, with the captain's numbers: round fingertips, flatter-backed fingers,
# knuckle bumps, a thenar pad, and the wrist loop widened to the forearm so no cuff step shows.
FINGER_THIN = 0.12
THENAR = 0.011   # (twentieth round: 0.007; the critic: "a large thumb with a fat thenar pad")
WRIST_WIDEN = (1.08, 1.04)   # (nineteenth round: was 1.25, 1.15; with the hand grown 15% the heel stood 2 to 3 cm out of the sheet inside the wrist)
WRIST_FADE = 0.03                # metres up the hand over which the widening fades out (the palm keeps the sheet's width)
WRIST_HALF = (0.061, 0.058)      # the forearm's last two rings' half widths at most (metres)


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
    f = 1.0 - smooth01(float(lc[2]), float(lc[2]) + WRIST_FADE, C[:, 2])
    C[:, 0] = lc[0] + (C[:, 0] - lc[0]) * (1.0 + (WRIST_WIDEN[0] - 1.0) * f)
    C[:, 1] = lc[1] + (C[:, 1] - lc[1]) * (1.0 + (WRIST_WIDEN[1] - 1.0) * f)
    print("%s HAND shaped: round tips, fingers %.0f%% thinner back to palm, knuckles %.1f mm, thenar %.1f mm" % (
        WHO, FINGER_THIN * 100, 1000 * float(bump.max()), THENAR * 1000))
    HB["C"] = C


TIP_DOME = (0.62, 0.0)    # the share of the last bone from which each tip is domed; how far the very tip is drawn back
                          # (in shares of the finger's radius) (twentieth round: 0.5; the dome later, so the tips stay
                          # thick and blunt)
TIP_POW = float(arg("--tip-pow", "3.0"))   # (twenty-first round; 0: the old quarter circle)
NAIL = (0.3, 0.86)        # the nail's plate: from this share of the last bone; flattened to this share of the back's height


def round_fingertips():
    """Fifteenth round (the second critic: "shard-like spiky fingertips"; un-subdivided twice and a ring dropped, each
    tip came to a point): the last bone of each digit, from TIP_DOME[0] of its length on, is made a round cap. Round
    its axis, the finger's own cross-section at the start of the dome (radius by angle) is kept, scaled by a quarter
    circle's height to nothing at the tip, so the end is a blunt round dome; the tip drawn back a little."""
    C = HB["flat"]
    lab = HB["label"]
    J = HB["J"]
    moved = 0.0
    for n in ("index", "middle", "ring", "little", "thumb"):
        ids = np.where(lab == n)[0]
        a, b = J[n][2], J[n][3]
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
            continue
        o = np.argsort(phi[ref])
        ph, rr = phi[ref][o], r[ref][o]
        R0 = np.interp(phi, np.concatenate([ph - math.tau, ph, ph + math.tau]), np.concatenate([rr, rr, rr]))
        smax = float(s.max())
        tip_s = smax - TIP_DOME[1] * float(np.median(rr)) / ln
        t = np.clip((s - s0) / max(tip_s - s0, 1e-3), 0.0, 1.0)
        if TIP_POW:
            # (twenty-first round, as the brother's: a superellipse of power TIP_POW keeps the last ring broad, a blunt
            # round end, and the cap's own points keep their distance from the axis, so no faces of no size)
            want_r = R0 * np.clip(1.0 - np.minimum(t, 0.95) ** TIP_POW, 0.0, 1.0) ** (1.0 / TIP_POW)
            want_r = np.minimum(want_r, np.maximum(r, 0.35 * want_r))
        else:
            want_r = R0 * np.sqrt(np.clip(1.0 - t ** 2, 0.0, 1.0))
        dome = s > s0
        # along the axis: the points past the new tip brought back onto it
        new_s = np.minimum(s, tip_s)
        unit = rel / np.maximum(r, 1e-9)[:, None]
        Q = a + np.outer(new_s * ln, d) + unit * want_r[:, None]
        old = C[ids].copy()
        C[ids[dome]] = Q[dome]
        moved = max(moved, float(np.linalg.norm(C[ids] - old, axis=1).max()))
        # (twentieth round, the fifth critic: "fingers that keep their thickness to blunt rounded tips ... short square
        # nails": the back of the last bone, from NAIL[0] of its length to the tip, flattened to a plate at NAIL[1] of the
        # finger's back height there, so a nail reads as a modelled flat plate)
        up_ = np.array((0.0, 1.0, 0.0)) - d * d[1]
        up_ /= np.linalg.norm(up_)
        rel2 = C[ids] - a
        s2 = rel2 @ d / ln
        hb = rel2 @ up_
        band = (s2 > NAIL[0]) & (hb > 0)
        if band.sum() > 2:
            top = float(np.percentile(hb[band], 90)) * NAIL[1]
            k_ = band & (hb > top)
            C[ids[k_]] -= np.outer(hb[k_] - top, up_)
    HB["flat"] = C
    HB["C"] = C.copy()
    print("CAPTAIN fingertips domed: most a point moved %.1f mm" % (moved * 1000))


def thumb_view_points(C, shift=(0.0, 0.0)):
    c0, c1 = HAND_COLS["thumb"]
    t = HB["tip_mid"]
    b0 = float(HB["flat"][HB["loop"], 1].mean())
    return np.stack([(c0 + c1) / 2.0 + (C[:, 1] - b0) / HAND_SX + shift[0], HB["tip"][1] - (C[:, 2] - t[2]) / HAND_SX + shift[1]], 1)


def thumb_target():
    c0, c1 = HAND_COLS["thumb"]
    r0, r1 = HAND_ROWS
    T = np.zeros_like(HB["mask"])
    T[r0:r1, c0:c1] = HB["mask"][r0:r1, c0:c1]
    return T


def _iou(P2, tris, T):
    zb, _ = raster(P2, np.zeros(len(P2)), tris, T.shape)
    m = np.isfinite(zb)
    r0, r1 = HAND_ROWS
    m[:r0] = False
    m[r1:] = False
    return float((m & T).sum()) / max(float((m | T).sum()), 1.0)


def hand_thumb_fit():
    """The thumb-side view: its shift and pose (finger curl, the thumb's swing and curl) by trying, kept as
    HAND_POSE_THUMBVIEW; then the back and palm surfaces moved front to back onto its outline."""
    tris = hand_tris_of(HB["faces"])
    T = thumb_target()
    C0, _ = pose_hand(HB["flat"], HB["J"], HB["label"], HAND_POSE_THUMBVIEW)
    best = (-1, (0, 0))
    for dx in range(-120, 121, 8):
        for dy in range(-30, 31, 10):
            s = _iou(thumb_view_points(C0, (dx, dy)), tris, T)
            if s > best[0]:
                best = (s, (dx, dy))
    shift = best[1]
    pose = dict(HAND_POSE_THUMBVIEW)
    for it in range(2):
        for key, vals in (("thumb_fwd", (-0.3, 0.0, 0.3, 0.6, 0.9, 1.2)), ("thumb_in", (-0.9, -0.7, -0.5, -0.3, -0.1, 0.1, 0.3)),
                          ("thumb_curl", (0.0, 0.15, 0.3, 0.5)), ("curl", ((-0.1, 0, 0), (0, 0, 0), (0.12, 0.08, 0.06), (0.25, 0.12, 0.08)))):
            scores = []
            for v_ in vals:
                p = dict(pose)
                p[key] = v_
                C, _ = pose_hand(HB["flat"], HB["J"], HB["label"], p)
                scores.append(_iou(thumb_view_points(C, shift), tris, T))
            pose[key] = vals[int(np.argmax(scores))]
        C, _ = pose_hand(HB["flat"], HB["J"], HB["label"], pose)
        best = (-1, shift)
        for dx in range(shift[0] - 16, shift[0] + 17, 4):
            for dy in range(shift[1] - 12, shift[1] + 13, 4):
                s = _iou(thumb_view_points(C, (dx, dy)), tris, T)
                if s > best[0]:
                    best = (s, (dx, dy))
        shift = best[1]
    HAND_POSE_THUMBVIEW.update(pose)
    print("CAPTAIN thumb-side view: pose %s, shift %s, overlap %.3f" % (json.dumps(pose), shift, best[0]))
    # the thickness: points facing front or back (not the thumb's) moved along b onto the view's outline
    lab = HB["label"]
    E = edges_of(HB["faces"])
    deg = np.bincount(E.ravel(), minlength=len(lab)).astype(float)
    loopset = list(HB["loop"])
    h, w = T.shape
    for rnd in range(8):
        C, _ = pose_hand(HB["flat"], HB["J"], HB["label"], HAND_POSE_THUMBVIEW)
        P2 = thumb_view_points(C, shift)
        zb, _ = raster(P2, -C[:, 0], tris, T.shape)
        R = np.isfinite(zb)
        N = normals_of(C, tris)
        move = np.zeros(len(C))
        has = np.zeros(len(C), bool)
        for v in range(len(C)):
            if abs(N[v, 1]) < 0.55 or not (HAND_ROWS[0] + 15 < P2[v, 1] < HAND_ROWS[1] - 5):
                continue
            sgn = 1.0 if N[v, 1] > 0 else -1.0
            p = P2[v]
            q = p + np.array((sgn * 2.0, 0.0))
            if not (0 <= int(q[0]) < w) or R[int(q[1]), int(q[0])]:
                continue
            inside = T[int(p[1]), int(p[0])]
            dist = None
            for k in range(1, 60):
                cc = int(p[0] + sgn * k) if inside else int(p[0] - sgn * k)
                hit = T[int(p[1]), min(max(cc, 0), w - 1)]
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


def drop_finger_rings(C, faces, label, loop, names, nth=3):
    """Each finger's ring `nth` from its tip collapsed onto the next ring toward the palm (rings walked from the tip's
    cap by neighbours); gives the compacted points, faces, labels and wrist loop."""
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
            print("CAPTAIN finger %s: rings %s, none taken out" % (n, [len(r) for r in rings]))
            continue
        for v in a:
            w = [u for u in adj[v] if u in b]
            if len(w) == 1:
                merge[v] = w[0]
    out = []
    for f in faces:
        g = [merge.get(v, v) for v in f]
        h = []
        for v in g:
            if v not in h:
                h.append(v)
        if len(h) >= 3:
            out.append(h)
    used = sorted({v for f in out for v in f})
    remap = {v: i for i, v in enumerate(used)}
    return (C[used], [[remap[v] for v in f] for f in out], label[used], [remap[merge.get(v, v)] for v in loop])


def hand_tris_of(faces):
    out = []
    for f in faces:
        for i in range(1, len(f) - 1):
            out.append((f[0], f[i], f[i + 1]))
    return out


def hand_outline_round():
    C, faces = HB["C"], HB["faces"]
    tris = hand_tris_of(faces)
    P2 = to_back_view(C)
    T = np.zeros_like(HB["mask"])
    c0, c1 = HAND_COLS["back"]
    r0, r1 = HAND_ROWS
    T[r0:r1, c0:c1] = HB["mask"][r0:r1, c0:c1]
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
        if v in loopset or L[v] < 0.5 or not (r0 + 15 < P2[v, 1] < r1 - 5):
            continue
        p = P2[v]
        dirn = d2[v] / L[v]
        q = p + dirn * 2.0
        if not (0 <= int(q[1]) < h and 0 <= int(q[0]) < w) or R[int(q[1]), int(q[0])]:
            continue
        dist = None
        inside = T[int(p[1]), int(p[0])]
        for k in range(1, 87):
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
    """The hand in a pose: the fingers drawn together toward the middle finger and curled at each joint toward the
    palm; the thumb swung in front of the palm and curled. Each digit turned about its joints with smooth weights
    (no warping). Gives (points, joints)."""
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
            for ax, ang in ((up, -pose["thumb_in"]), (mid_d, pose["thumb_fwd"])):
                k_ = 1 if ax is mid_d else 0
                test = rot_about(np.array([js[3]]), js[0], ax, 0.1, np.ones(1))[0]
                ang = -abs(ang) if (test[k_] - js[3][k_]) > 0 else abs(ang)
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
            test = rot_about(np.array([js[3]]), js[k], ax, 0.1, np.ones(1))[0]
            if test[1] > js[3][1]:
                ax = -ax
            s = (C[ids] - js[k]) @ d
            w = smooth01(-0.004, 0.004, s) if k else smooth01(-0.012, 0.004, s)
            C[ids] = rot_about(C[ids], js[k], ax, ang, w)
            js = js[:k + 1] + [rot_about(np.array([p]), js[k], ax, ang, np.ones(1))[0] for p in js[k + 1:]]
        J[n] = js
    return C, J


def hand_gaps(model, target, rows, scale):
    """The worst and the 99th-percentile distance (cm) between the two outlines, both ways, over the rows given."""
    keep = np.zeros(model.shape[0], bool)
    keep[rows[0] + 3:rows[1] - 3] = True
    mo = outline_of(model) & keep[:, None]
    to = outline_of(target) & keep[:, None]
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
        out.append(np.array([kd.find((float(ax[i]), float(ay[i]), 0.0))[2] for i in range(len(ay))]))
    d = np.concatenate(out)
    return float(d.max()) * scale * 100, float(np.percentile(d, 99)) * scale * 100


def hand_silhouettes():
    """The fitted hand's back, palm and thumb-side silhouettes against the sheet's (the thumb side in the sheet's own
    bend): difference pictures (to --out) and the worst gaps; also keeps where each view lands (HB["views"])."""
    res = {}
    HB["views"] = {}
    tris = hand_tris_of(HB["faces"])
    r0, r1 = HAND_ROWS
    for v, pose in (("back", None), ("palm", None), ("thumb", HAND_POSE_THUMBVIEW)):
        c0, c1 = HAND_COLS[v]
        C = HB["flat"]
        if pose:
            C, _ = pose_hand(C, HB["J"], HB["label"], pose)
        u = {"back": C[:, 0], "palm": -C[:, 0], "thumb": C[:, 1]}[v]
        dep = {"back": -C[:, 1], "palm": C[:, 1], "thumb": -C[:, 0]}[v]
        t = HB["tip_mid"]
        if v == "back":
            P2 = to_back_view(C)
        else:
            P2 = np.stack([(c0 + c1) / 2.0 + (u - u[np.argmax(C[:, 2])]) / HAND_SX, HB["tip"][1] - (C[:, 2] - t[2]) / HAND_SX], 1)
        target = np.zeros_like(HB["mask"])
        target[r0:r1, c0:c1] = HB["mask"][r0:r1, c0:c1]
        zb, _ = raster(P2, dep, tris, target.shape)
        full = np.isfinite(zb)
        mc, tc_ = full[r0:r1, c0:c1], target[r0:r1, c0:c1]

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
        sm = np.roll(np.roll(mc, best[2], 0), best[1], 1)
        if best[2] > 0:
            sm[:best[2]] = False          # (rows rolled round from the bottom)
        elif best[2] < 0:
            sm[best[2]:] = False
        mm[r0:r1, c0:c1] = sm
        HB["views"][v] = (float(P2[0, 0] + best[1] - u[0] / HAND_SX), float(P2[0, 1] + best[2] + C[0, 2] / HAND_SX))
        g = hand_gaps(mm, target, HAND_ROWS, HAND_SX)
        res[v] = (round(g[0], 2), round(g[1], 2), round(best[0], 3))
        if OUT:
            os.makedirs(OUT, exist_ok=True)
            box = (c0, r0 - 10, c1, r1 + 10)
            m_, t_ = mm[box[1]:box[3], box[0]:box[2]], target[box[1]:box[3], box[0]:box[2]]
            img = np.ones(m_.shape + (3,)) * 0.97 * 0.75 + HB["pix"][box[1]:box[3], box[0]:box[2]] * 0.25
            img[m_ & t_] = (0.62, 0.62, 0.64)
            img[m_ & ~t_] = (0.92, 0.15, 0.12)
            img[t_ & ~m_] = (0.05, 0.75, 0.9)
            save_rgb(os.path.join(OUT, "handdiff_%s.png" % v), img)
    print("CAPTAIN hand silhouettes (worst cm, 99%% cm, overlap): %s" % json.dumps(res))
    return res


# (eighteenth round, the critic: "in the side view the fingers still curl like a claw: a natural relaxed hang (fingers
# nearly straight, slightly apart, a gentle curl growing toward the little finger)". HAND_POSE_RELAXED's curls are
# added to whatever bend the fitted hand already has, and the fitted hand (the base mesh fitted to the sheet's views)
# is itself bent some 20 to 40 degrees a joint. So the bends are measured on it and the curls set to reach these, in
# radians at the knuckle, the middle joint and the last (index first): about 5 to 10 degrees, more toward the little
# finger.)
# (twentieth round, the fifth critic: "clawed": about two thirds of the eighteenth round's bends)
HAND_RELAXED_BENDS = {"index": (0.04, 0.07, 0.04), "middle": (0.05, 0.08, 0.05), "ring": (0.07, 0.10, 0.06),
                      "little": (0.10, 0.13, 0.08)}


def finger_bends(J):
    """Each finger's bends (radians, toward the palm, which is -y in the flat hand) at its three joints."""
    up = np.array((0.0, 1.0, 0.0))
    out = {}
    for n in FINGERS:
        js = [np.array(p) for p in J[n]]
        d = js[3] - js[0]
        ref = d - up * (d @ up)
        ref /= np.linalg.norm(ref)
        segs = [js[k + 1] - js[k] for k in range(3)]
        bs = []
        for k in range(3):
            nh = ref if k == 0 else segs[k - 1] / np.linalg.norm(segs[k - 1])
            pw = -up - nh * float(-up @ nh)
            pw /= max(np.linalg.norm(pw), 1e-9)
            bs.append(math.atan2(float(segs[k] @ pw), float(segs[k] @ nh)))
        out[n] = tuple(bs)
    return out


def straighten_fingers(C, J, label, bins=7):
    """The fitted hand's fingers bow toward the palm in the mesh itself (their joints J lie on straight lines: the
    measured bends were 0 at the middle and last joints), so curls about J never took the bow out. Each finger's middle
    line is measured (its points' middle in bins along it) and its bow away from the straight line from its knuckle
    to its tip taken off every point of it (fading in over the first centimetre)."""
    C = C.copy()
    for n in FINGERS:
        ids = np.where(label == n)[0]
        js = [np.array(p) for p in J[n]]
        d = js[3] - js[0]
        Ln = float(np.linalg.norm(d))
        d /= Ln
        s = (C[ids] - js[0]) @ d
        edges = np.linspace(0.0, Ln, bins + 1)
        mids, offs = [0.0], [np.zeros(3)]
        for a, b in zip(edges[:-1], edges[1:]):
            m = (s >= a) & (s < b)
            if m.sum() < 3:
                continue
            c = C[ids[m]].mean(0)
            rel = c - js[0]
            off = rel - d * float(rel @ d)
            mids.append(float((a + b) / 2.0))
            offs.append(off)
        offs = np.array(offs)
        # the knuckle's own offset (the first bin) is kept: only the bow beyond it is taken off
        base = offs[1] if len(offs) > 1 else np.zeros(3)
        offs = offs - base
        offs[0] = 0.0
        # (twentieth round: the bins' middles, each of a part of a ring, swing from bin to bin, and followed point by
        # point they corrugated every finger into a row of ridges; the bow is now a smooth curve, a quadratic through
        # the knuckle fitted to them)
        mids_ = np.array(mids)
        if len(mids_) >= 4:
            A_ = np.stack([mids_, mids_ ** 2], 1)
            coef = np.linalg.lstsq(A_, offs, rcond=None)[0]
            sq = np.clip(s, 0.0, None)
            sh = np.outer(sq, coef[0]) + np.outer(sq ** 2, coef[1])
        else:
            sh = np.stack([np.interp(s, mids, offs[:, k]) for k in range(3)], 1)
        w = smooth01(0.0, 0.012, s)
        C[ids] -= sh * w[:, None]
    return C


def relaxed_pose():
    have = finger_bends(HB["J"])
    pose = dict(HAND_POSE_RELAXED)
    pose["curl"] = {n: tuple(t - h for t, h in zip(HAND_RELAXED_BENDS[n], have[n])) for n in FINGERS}
    print("CAPTAIN fingers: the fitted hand's bends (degrees) %s; curled to %s" % (
        {n: [round(math.degrees(b)) for b in v] for n, v in have.items()},
        {n: [round(math.degrees(b)) for b in v] for n, v in HAND_RELAXED_BENDS.items()}))
    return pose


def place_base_hand(M, wrist_ring, side, W, L, joints):
    """The fitted hand, relaxed, on the arm's end (its frame as hand()'s), its open loop joined to the wrist ring."""
    base_hand_fit()
    sfx = "_l" if side > 0 else "_r"
    X = Vector((1, 0, 0))
    F = Vector((0, -1, 0))
    A = (X - L * L.x).normalized()
    tw = math.radians(36.0)
    Tb = A * math.cos(tw) + F * math.sin(tw)
    Wd = -A * math.sin(tw) + F * math.cos(tw)
    C, J = pose_hand(straighten_fingers(HB["flat"], HB["J"], HB["label"]), HB["J"], HB["label"], relaxed_pose())
    Wv, Tv, Lv, Ov = np.array(Wd), np.array(Tb), np.array(L), np.array(W)

    def body(Q):
        Q = np.atleast_2d(Q)
        R = Ov + Q[:, :1] * Wv + Q[:, 1:2] * Tv + Q[:, 2:3] * Lv
        R[:, 0] *= side
        return R
    B = body(C)
    lab = HB["label"]
    base = len(M.P)
    ids = [M.add(p, "hand" + sfx + ("_" + lab[k] if lab[k] else "")) for k, p in enumerate(B)]
    hf = []
    for f in HB["faces"]:
        labs = [lab[v] for v in f]
        fl = max(set(labs), key=labs.count)
        M.face([ids[v] for v in f], "hand" + sfx + ("_" + fl if fl else ""))
        hf.append(len(M.faces) - 1)
    f0 = len(M.faces)
    # (the zipper to the forearm: both loops in order of their angle round the wrist, merged)
    Wm = np.array(mirror_x(W, side))
    Wd_m, Tb_m = np.array(mirror_x(Wd, side)), np.array(mirror_x(Tb, side))
    Pm_ = np.array(M.P)
    # (the forearm's last two rings drawn toward the hand's loop, so no cuff stands round the wrist: each point's
    # distance from the wrist's middle, round the arm, eased toward the loop's at the same angle)
    hl = [ids[v] for v in HB["loop"]]
    hc = Pm_[hl].mean(0)
    ha = np.arctan2((Pm_[hl] - hc) @ Wd_m, (Pm_[hl] - hc) @ Tb_m)
    hr_ = np.linalg.norm((Pm_[hl] - hc) - np.outer((Pm_[hl] - hc) @ np.array(mirror_x(Lv, side)), np.array(mirror_x(Lv, side))), axis=1)
    o_ = np.argsort(ha)
    ha, hr_ = ha[o_], hr_[o_]
    rings_ = M.tag["arm_rings" + sfx]
    for ring, share in ((rings_[-1], HAND_WRIST_EASE[0]), (rings_[-2], HAND_WRIST_EASE[1])):
        rc = Pm_[ring].mean(0)
        for v in ring:
            d = Pm_[v] - rc
            th = math.atan2(float(d @ Wd_m), float(d @ Tb_m))
            want = float(np.interp(th, np.concatenate([ha - math.tau, ha, ha + math.tau]), np.concatenate([hr_, hr_, hr_])))
            have = float(np.linalg.norm(d))
            k = 1.0 + share * (want / max(have, 1e-6) - 1.0)
            M.P[v] = rc + d * k
            Pm_[v] = M.P[v]
    seqs = []
    for lp in (list(wrist_ring), [ids[v] for v in HB["loop"]]):
        a_ = np.mod(np.arctan2((Pm_[lp] - Wm) @ Wd_m, (Pm_[lp] - Wm) @ Tb_m), math.tau)
        o_ = np.argsort(a_)
        seqs.append(([lp[i] for i in o_], a_[o_]))
    (A_, a_), (B_, b_) = seqs
    na, nb_ = len(A_), len(B_)
    ae = np.append(a_, a_[0] + math.tau)
    be = np.append(b_, b_[0] + math.tau)
    i = j = 0
    while i < na or j < nb_:
        if j >= nb_ or (i < na and ae[i + 1] <= be[j + 1]):
            M.face([A_[i % na], A_[(i + 1) % na], B_[j % nb_]], "hand" + sfx)
            i += 1
        else:
            M.face([A_[i % na], B_[(j + 1) % nb_], B_[j % nb_]], "hand" + sfx)
            j += 1
    M.tag["wrist_faces" + sfx] = list(range(f0, len(M.faces)))
    M.tag["hand_faces" + sfx] = hf
    M.tag["hand_range" + sfx] = (base, len(M.P))
    M.tag["hand_flat" + sfx] = {ids[k]: HB["flat"][k] for k in range(len(ids))}
    for n in ("little", "ring", "middle", "index", "thumb"):
        joints[n + sfx] = [Vector(p) for p in body(np.array(J[n]))]
    tb_thumb = np.cross(J["thumb"][3] - J["thumb"][0], np.array((0.0, 0.0, 1.0)))
    joints["thumb_back" + sfx] = body(np.array([tb_thumb]))[0] - body(np.zeros((1, 3)))[0]
    joints["hand_frame" + sfx] = tuple(np.array(mirror_x(v, side)) for v in (Tb, Wd, L))
    joints["knuckles" + sfx] = Vector(body(np.array([J["middle"][0]]))[0])


def paint_hands(M, face_uv, rgb, hit, fid, pos, good, tex_fam, joints):
    """The hands painted from their own sheet's back and palm views (the brother's method): each hand texel found on
    the hand as fitted flat in the sheet's pose (M.tag["hand_flat_*"]) takes the sheet's colour where that view sees
    it squarely; the anchor tattoo's pixels are left out and filled from round them (tattoos are a movable overlay);
    then brought to the forearm's tone, fading into it over the first few centimetres from the wrist."""
    P = np.array(M.P)
    Palt = P.copy()
    inflat = np.zeros(len(P), bool)
    for sfx in ("_l", "_r"):
        flat = M.tag["hand_flat" + sfx]
        ids = np.array(list(flat))
        Palt[ids] = np.array([flat[i] for i in ids])
        inflat[ids] = True
    Nalt = normals_of(Palt, M.tris())
    sign = {}
    for sfx in ("_l", "_r"):
        ids = np.array(list(M.tag["hand_flat" + sfx]))
        c = Palt[ids].mean(0)
        sign[sfx] = 1.0 if float(((Palt[ids] - c) * Nalt[ids]).sum()) > 0 else -1.0
    posf, nrmf, _, _ = texel_geometry(M, face_uv, "skin", Palt, Nalt)
    parts = np.array(list(M.fpart) + ["none"])[fid].astype(str)
    wristf = np.array([p.startswith("hand") and not all(inflat[v] for v in f) for f, p in zip(M.faces, M.fpart)] + [False])
    wrist = hit & wristf[fid]
    hands = hit & np.char.startswith(parts, "hand") & ~wrist
    nb = nrmf[..., 1] * np.where(np.char.startswith(parts, "hand_l"), sign["_l"], sign["_r"])
    mask = _shrink(HB["mask"], 3) & ~HB["ink"]
    acc = np.zeros_like(rgb)
    wsum = np.zeros(rgb.shape[:2])
    for v, s_ in (("back", 1.0), ("palm", -1.0)):
        col0, row0 = HB["views"][v]
        col = col0 + posf[..., 0] * s_ / HAND_SX
        row = row0 - posf[..., 2] / HAND_SX
        c = np.clip(col.astype(int), 0, mask.shape[1] - 1)
        r = np.clip(row.astype(int), 0, mask.shape[0] - 1)
        ok = hands & mask[r, c] & (row < HAND_ROWS[1] + 45) & (row > 60)
        w = np.where(ok, np.clip(s_ * nb, 0, 1) ** 2 + 1e-3, 0.0)
        acc += HB["pix"][r, c] * w[..., None]
        wsum += w
    seen = hands & (wsum > 0.02)
    col_ = acc / np.maximum(wsum, 1e-6)[..., None]
    filled = fill_out(np.where(seen[..., None], col_, rgb), seen | ~hands, 60)
    soft = blur(filled, 2)
    filled = np.where(seen[..., None], filled, soft)
    # the forearm's tone just above the wrist
    W_ = np.array(joints["wrist_l"], float)
    L_ = np.array(joints["hand_frame_l"][2], float)
    near_w = np.zeros(hit.shape, bool)
    for s in (1.0, -1.0):
        Wm = W_ * np.array((s, 1.0, 1.0))
        Lm = L_ * np.array((s, 1.0, 1.0))
        near_w |= hit & good & (tex_fam == "arm") & (np.linalg.norm(pos - (Wm - Lm * 0.05), axis=-1) < 0.05)
    base_c = np.median(rgb[near_w], axis=0) if near_w.any() else np.median(rgb[hit & (tex_fam == "arm")], axis=0)
    near = seen & (posf[..., 2] < 0.07) & (nb > 0.3)
    ref = np.median(filled[near], axis=0) if near.any() else np.median(filled[seen], axis=0)
    gain = np.clip(base_c / np.maximum(ref, 1e-3), 0.7, 1.4)
    out = rgb.copy()
    k = smooth01(HAND_LOOP_L, HAND_LOOP_L + 0.035, posf[..., 2])[..., None]
    out[hands] = np.clip((filled * gain * k + base_c * (1 - k))[hands], 0, 1)
    out[wrist] = base_c
    print("CAPTAIN hands painted from their sheet: %d texels (%d seen), tone times %s" % (int(hands.sum()), int(seen.sum()), np.round(gain, 3)))
    return out


def round_uvs(M, faces, centre, across, back, along):
    """UVs round an axis: u the angle times the mean radius, v along it."""
    P = np.array(M.P)
    ids = sorted({v for fi in faces for v in M.faces[fi]})
    rad = float(np.mean([np.linalg.norm((P[v] - centre) - along * np.dot(P[v] - centre, along)) for v in ids]))
    out = {}
    for fi in faces:
        Q = P[M.faces[fi]] - centre
        th = np.arctan2(Q @ across, Q @ back)
        if th.max() - th.min() > math.pi:
            th = np.where(th < 0, th + math.tau, th)
        out[fi] = [(float(t) * rad, float(np.dot(q, along))) for t, q in zip(th, Q)]
    return out


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
            HB["foot"] = refine_toes(shape_foot(fit_base_foot(load_base_foot(unsub=FOOT_UNSUB), foot_profile(sh, ax, ay), FOOT_HEIGHT_K, toe_plump=FOOT_TOE_PLUMP)))
        base = HB["foot"]
        o = np.array(mirror_x(Vector((ax, ay, 0.0)), side))
        f_m = np.array(mirror_x(fwd, side))
        l_m = np.array(mirror_x(lat, side))
        ids, bf, zf = place_base_foot(M, base, prev, o, f_m, l_m, side, foot_part)
        M.tag["foot_faces" + sfx] = bf + zf
        M.tag["foot_frame" + sfx] = (o, f_m, l_m)
        Pn = np.array(M.P)
        tips = [Pn[ids[t]] for t in base["tips"]]
        M.tag["foot_toes" + sfx] = [(tips[0], 0.0095)] + [(t, 0.0058 - 0.0004 * i) for i, t in enumerate(tips[1:])]
        tip_u = min(float(np.dot(t - o, f_m)) for t in tips)
        M.tag["foot_toe_u" + sfx] = tip_u
        joints["ball" + sfx] = Vector(o + f_m * (tip_u - 0.06) + np.array((0.0, 0.0, 0.028)))
        joints["toe_tip" + sfx] = Vector(o + f_m * (tip_u + 0.01) + np.array((0.0, 0.0, 0.02)))
        return
    if FOOT_TOES:
        foot_rings(M, prev, ax, ay, fwd, lat, side, sfx, joints)
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
    joints["ball" + sfx] = Vector(mirror_x(Vector((ax, ay, 0.025)) + fwd * 0.12, side))
    joints["toe_tip" + sfx] = Vector(mirror_x(Vector((ax, ay, 0.02)) + fwd * 0.2, side))


# Fourteenth round (the critic: "feet are toeless mittens ... no toes, no arch, a step at the heel, faceted"; the
# brother's foot, tools/build_brother.py foot_shape, taken over and pushed further): the foot's rings have 24 points,
# 15 of them across the front half so the toes have points of their own; the big toe parts from the rest by a deep
# groove, the small toes' tips scalloped, the toe line slopes back to the little toe, the inner side lifts into an
# arch, the heel is round and the ankle bones stand out. The ankle's 10-point ring is zipped to the first.
FOOT_TOES = "--old-feet" not in ARGS
FOOT_AL = [math.radians(-80.0 + 160.0 * i / 14.0) for i in range(15)] + [math.radians(80.0 + 20.0 * k) for k in range(1, 10)]
# (height, reach forward of the ankle, back, half width)
FOOT_RINGS2 = ((0.118, 0.07, 0.066, 0.06), (0.088, 0.118, 0.076, 0.064), (0.06, 0.175, 0.082, 0.072),
               (0.036, 0.212, 0.083, 0.076), (0.016, 0.218, 0.080, 0.073), (0.003, 0.208, 0.072, 0.066))
TOE_GROOVES = ((-0.2, 0.034), (0.2, 0.018), (0.56, 0.016))     # (across: inside < 0, depth in metres at the sole)


def foot_shape(al, z, front, backr, half):
    """(forward, across toward his outside, height) of a foot point at angle al round the ring (from his toes'
    direction)."""
    cu, cv = math.cos(al), math.sin(al)
    if cu > 0:
        u = sgnpow(cu, 0.5) * front * TOE_REACH
        v = sgnpow(cv, 0.8) * half * (1.0 + 0.16 * cu)
    else:
        u = -sgnpow(-cu, 0.85) * backr
        v = cv * half * (0.98 if cu > -0.2 else 0.84)
    zz = z
    if cu > 0.3 and z < 0.06:
        low = 1.0 if z < 0.045 else (0.7 if z < 0.06 else 0.3)
        # the toe line slopes back toward the little toe (cv > 0 is his outside)
        u -= 0.03 * max(cv + 0.1, 0.0) * low
        # the big toe's tip round and furthest forward, the grooves between toes
        u += 0.006 * math.exp(-((cv + 0.42) / 0.16) ** 2) * low
        for c, d in TOE_GROOVES:
            u -= d * low * math.exp(-((cv - c) / 0.09) ** 2)
        # the toes thinner than the ball: their tops dip toward the tips
        if z > 0.02:
            zz -= 0.006 * max(cu - 0.55, 0.0) / 0.45
            # (and between the toes their tops part too)
            for c, d in TOE_GROOVES:
                zz -= 0.25 * d * math.exp(-((cv - c) / 0.09) ** 2) * max(cu - 0.5, 0.0) / 0.5
    # the arch: the inner side's sole lifted between the heel and the ball
    if z < 0.02 and cv < -0.2 and -0.55 < cu < 0.6:
        lift = (1.0 - (cu / 0.6) ** 2) * min((-cv - 0.2) / 0.5, 1.0)
        zz += 0.02 * lift * (1.0 if z < 0.008 else 0.5)
        v *= 1.0 - 0.14 * lift
    # the heel rounded under: the lowest ring drawn in at the back
    if cu < -0.3 and z < 0.01:
        u *= 0.9
    # the ankle bones: the inner one higher and further forward, the outer one lower and further back
    if z > 0.075:
        inner = math.exp(-((cv + 0.95) / 0.25) ** 2 - ((cu - 0.1) / 0.45) ** 2)
        outer = math.exp(-((cv - 0.95) / 0.25) ** 2 - ((cu + 0.15) / 0.45) ** 2)
        k_in = 0.008 if z > 0.1 else 0.003
        k_out = 0.004 if z > 0.1 else 0.007
        v += -k_in * inner + k_out * outer
    # the Achilles tendon's notch behind the ankle
    if z > 0.075 and cu < -0.8:
        u += 0.007 * (-cu - 0.8) / 0.2
    return u, v, zz


def foot_rings(M, ankle_ring, ax, ay, fwd, lat, side, sfx, joints):
    part = "foot" + sfx
    rings = []
    for z, front, backr, half in FOOT_RINGS2:
        ring = []
        for al in FOOT_AL:
            u, v, zz = foot_shape(al, z, front, backr, half)
            q = Vector((ax, ay, zz)) + fwd * u + lat * v
            ring.append(M.add(mirror_x(q, side), part))
        rings.append(ring)
    # (the first ring as wide as the ankle's ring over it, so no ledge shows where they meet)
    A = np.array([M.P[v] for v in ankle_ring])
    r0 = np.array([M.P[v] for v in rings[0]])
    c0 = np.array((r0[:, 0].mean(), r0[:, 1].mean()))
    ca = A[:, :2].mean(0)
    k = float(np.linalg.norm(A[:, :2] - ca, axis=1).mean() / max(np.linalg.norm(r0[:, :2] - c0, axis=1).mean(), 1e-6))
    k = float(np.clip(k, 0.85, 1.25))
    for i, v in enumerate(rings[0]):
        p = np.array(M.P[v], float)
        p[:2] = ca + (p[:2] - c0) * k * 0.97 + (c0 - ca) * 0.5
        M.P[v] = p
    print("CAPTAIN foot%s: the first ring made %.2f times as wide, to the ankle's" % (sfx, k))
    n0 = len(M.faces)
    bridge_uneven(M, ankle_ring, rings[0], part, np.array((0.0, 0.0, 1.0)))
    M.tag["foot_zip" + sfx] = list(range(n0, len(M.faces)))
    n1 = len(M.faces)
    for a, b in zip(rings, rings[1:]):
        M.bridge(a, b, part) if side > 0 else M.bridge(b, a, part)
    M.tag["foot_quads" + sfx] = list(range(n1, len(M.faces)))
    # the sole: a fan from a point under the ball's back
    sole = M.add(mirror_x(Vector((ax, ay, 0.0)) + fwd * 0.07, side), part)
    last = rings[-1]
    n2 = len(M.faces)
    nn = len(last)
    for j in range(nn):
        k = (j + 1) % nn
        M.face([last[j], last[k], sole] if side > 0 else [last[k], last[j], sole], part)
    M.tag["foot_sole" + sfx] = list(range(n2, len(M.faces)))
    M.tag["foot_rings" + sfx] = rings
    M.tag["foot_frame" + sfx] = (np.array(mirror_x(Vector((ax, ay, 0.0)), side), float),
                                 np.array(mirror_x(fwd, side), float) * np.array((1.0, 1.0, 1.0)))
    joints["ball" + sfx] = Vector(mirror_x(Vector((ax, ay, 0.025)) + fwd * 0.15, side))
    joints["toe_tip" + sfx] = Vector(mirror_x(Vector((ax, ay, 0.02)) + fwd * 0.24, side))


def foot_uvs(M, sfx):
    """The foot's island: round the foot by angle about the ankle's upright (u, the mean radius times the angle,
    the seam at the heel), and down its rings (v, distance); the zipper's points on the ankle ring at v = 0."""
    P = np.array(M.P)
    c = M.tag["foot_frame" + sfx][0]
    fw = M.tag["foot_frame" + sfx][1]
    fw = fw / np.linalg.norm(fw)
    rings = M.tag["foot_rings" + sfx]
    ankle = M.tag["leg_rings" + sfx][-1]
    vpos = {v: 0.0 for v in ankle}
    acc = 0.0
    prev = P[ankle].mean(0)
    for ring in rings:
        m = P[ring].mean(0)
        acc += float(np.linalg.norm(m - prev)) + 0.012
        prev = m
        for v in ring:
            vpos[v] = acc
    R = 0.075
    lat = np.cross(fw, (0, 0, 1.0))

    def ang(v):
        d = P[v] - c
        # (0 at the toes, so the seam (at plus and minus a half turn) is behind the heel)
        return math.atan2(float(np.dot(d, lat)), float(np.dot(d, fw)))
    out = {}
    for fi in M.tag["foot_zip" + sfx] + M.tag["foot_quads" + sfx]:
        f = M.faces[fi]
        a = np.array([ang(v) for v in f])
        if a.max() - a.min() > math.pi:
            a = np.where(a < 0, a + math.tau, a)
        out[fi] = [(float(a[i] * R), -vpos[v]) for i, v in enumerate(f)]
    return out


# ------------------------------------------------------------------------------------------------------------------
# Fifteenth round (the second critic: "split hooves with a sawtooth toe edge, a flat sole and a ledge at the ankle"):
# the feet are no longer lofted rings. Each is Blender Studio's `Foot - Stylized` from the CC0 human base meshes
# bundle (five real toes), un-subdivided twice, warped height by height to the body sheet's side view (heel, instep,
# toes) and front view (the ankle), its top blended into the shin's last ring (no ledge), unwrapped into a sole and
# an upper island and painted from the shin's tone with toenails. The functions load_base_foot, fit_base_foot,
# place_base_foot, foot_islands, unwrap_conformal and paint_feet are the brother's (tools/build_brother.py), copied
# as they are (they take every figure-specific number as an argument); foot_profile reads this figure's sheet.
# ------------------------------------------------------------------------------------------------------------------
BASE_FEET = "--ring-feet" not in ARGS
FOOT_PROFILE_ROWS = (1355, 1459)   # the body sheet's rows the foot is fitted over (just under the ankle ring to the sole)
FOOT_HEIGHT_K = 1.12               # the base foot's height times this
FOOT_BALL_K = 1.12                 # the ball's width over the sheet's measure (the critic: "broad, flat, wide bare feet")
FOOT_LEN_K = 1.12                  # (eighteenth round: 1.24 tried for the instep, 4 to 5 cm short of the sheet: the toes came out as flat teeth; seventeenth round: the side view of the built foot measured 27.6 cm against the sheet's 33.1;
                                   # the refine and the thinning shorten it, so it is made this much over the sheet's length)
FOOT_TOE_PLUMP = (1.3, 1.6)         # the toes thickened about their own axes (across, up): short, thick toes
FOOT_BLEND = 0.045                 # metres down from the foot's top over which it is drawn to the shin's last ring
WHO = "CAPTAIN"


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
        if z > 0.07:
            f0, f1 = SPAN["front"]
            rf = run_near(sh.body_mask, r, MID["front"] + ax / S, f0, f1)
            if rf and not (rf[0] < MID["front"] < rf[1]):
                half = (rf[1] + 1 - rf[0]) / 2.0 * S
        zs.append(z)
        fr.append(ay - yf)
        bk.append(yb - ay)
        hf.append(half)
    f0, f1 = SPAN["front"]
    wide = 0.0
    for r in range(FOOT_PROFILE_ROWS[1], FOOT_PROFILE_ROWS[1] - 40, -2):
        rf = run_near(sh.body_mask, r, MID["front"] + (ax + 0.04) / S, f0, f1)
        if rf and not (rf[0] < MID["front"] < rf[1]):
            wide = max(wide, (rf[1] + 1 - rf[0]) * S)
    # (the side view sees L cos + W sin of a foot turned out, the front view L sin + W cos: solved for L and W)
    Ls = max(a + b for a, b in zip(fr, bk))
    cy_, sy_ = math.cos(FOOT_YAW), math.sin(FOOT_YAW)
    c2 = cy_ * cy_ - sy_ * sy_
    L = (Ls * cy_ - wide * sy_) / c2
    W = (wide * cy_ - Ls * sy_) / c2
    k = L * FOOT_LEN_K / Ls
    fr = [a * k for a in fr]
    bk = [b * k for b in bk]
    ball = W / 2.0 * FOOT_BALL_K
    print("%s foot from the sheet: %.1f cm long, %.1f cm wide (side view %.1f, front view %.1f); made %.1f long" % (WHO, L * 100, W * 100, Ls * 100, wide * 100, L * FOOT_LEN_K * 100))
    print("%s foot profile: %s" % (WHO, ", ".join("z %.3f f %.3f b %.3f w %.3f" % q for q in zip(zs[::4], fr[::4], bk[::4], hf[::4]))))
    print("%s foot ball: front view %.1f cm wide, so the ball %.1f cm" % (WHO, wide * 100, ball * 200))
    return {"z": zs, "front": fr, "back": bk, "half": hf, "ball_half": ball}


def load_base_foot(bundle=None, unsub=2):
    """The bundle's `Foot - Stylized` (a left foot), un-subdivided, its ankle cap taken off. Gives a dict: F (points as
    (u forward, v toward the little toe's side, z up from the sole), the ankle cap's middle at u = v = 0), faces,
    loop (the open ankle loop, in order), toes (five lists of point indices, the big toe first) and tips (the
    point of each toe furthest forward)."""
    bundle = bundle or BUNDLE
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
    loop = max(open_loops(faces), key=len)
    hub_xy = P[loop, :2].mean(0)
    F = np.stack([-(P[:, 1] - hub_xy[1]), P[:, 0] - hub_xy[0], P[:, 2] - P[:, 2].min()], 1)
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
    for k in (0.0, 0.2, 0.35, 0.5, 0.7, 0.9):
        g = F[:, 0] + k * F[:, 1]
        found = None
        for t in np.linspace(g.max() - 0.004, g.max() - 0.09, 120):
            comps = [c for c in pieces(t, k) if len(c) >= 2]
            if len(comps) == 5:
                found = comps
            elif found is not None and len(comps) < 5:
                break
        if found is not None:
            best = found
            break
    if best is None:
        raise RuntimeError("base foot: five toes not found")
    toes = sorted(best, key=lambda c: F[c, 1].mean())
    tips = [int(c[int(np.argmax(F[c, 0]))]) for c in toes]
    print("%s base foot: %d points, %d faces, %d triangles, ankle loop %d, toes %s" % (
        WHO, len(F), len(faces), sum(len(f) - 2 for f in faces), len(loop), [len(c) for c in toes]))
    return {"F": F, "faces": faces, "loop": loop, "toes": toes, "tips": tips}


def fit_base_foot(base, prof, height_k=1.0, bumps=True, toe_plump=(1.12, 1.4)):
    """The foot warped to a profile (see the brother's builder): scaled whole to the sheet's length, then height by
    height its front to `front`, its heel to `back`, its width to `half`; the toes plumped; the ankle bones and the
    Achilles tendon's notch. Changes base["F"]."""
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
    z = F[:, 2]
    F[:, 0] *= np.where(F[:, 0] > 0, np.interp(z, zs, kf), np.interp(z, zs, kb))
    F[:, 1] *= np.interp(z, zs, kw)
    for comp in base["toes"]:
        c = np.array(comp)
        Q = F[c]
        root = Q[:, 0].min()
        mean = Q.mean(0)
        _, _, vt = np.linalg.svd(Q - mean)
        ax_ = np.array((1.0, 0.0, 0.0))   # (nineteenth round: the foot's forward line, as the brother's shape_foot found: the small toes are wider than long, so their spread's axis ran across the foot and the plumping flattened them into a lip)
        rel = Q - mean
        along_ = rel @ ax_
        perp = rel - along_[:, None] * ax_[None, :]
        w = np.clip((Q[:, 0] - root) / 0.012, 0, 1)[:, None]
        grow = np.array((1.0, toe_plump[0], toe_plump[1]))
        F[c] = Q + perp * (grow - 1.0) * w
    # (seventeenth round, the third critic: "toes graded from a proper broad big toe down to a small little toe, not a
    # row of same-size teeth"): each toe scaled about its root across and up (TOE_GRADE), the big toe set a little
    # apart toward the inside and the small ones drawn a little back
    for i, comp in enumerate(base["toes"]):
        c = np.array(comp)
        Q = F[c]
        root = Q[:, 0].min()
        w = np.clip((Q[:, 0] - root) / 0.012, 0, 1)
        g, back = TOE_GRADE[i]
        m = Q.mean(0)
        Q[:, 1] = m[1] + (Q[:, 1] - m[1]) * (1.0 + (g - 1.0) * w)
        Q[:, 2] = np.maximum(m[2] + (Q[:, 2] - m[2]) * (1.0 + (g - 1.0) * w), 0.0)
        Q[:, 0] -= back * w
        if i == 0:
            Q[:, 1] -= 0.003 * w
        F[c] = Q
    F[:, 2] = np.maximum(F[:, 2], 0.0)
    if bumps:
        L = L_sheet
        for side_v, zc, uc, amt in ((-1.0, 0.09 * height_k, 0.01, FOOT_KNOB[0]), (1.0, 0.075 * height_k, -0.008, FOOT_KNOB[1])):
            w = np.exp(-((F[:, 2] - zc) / 0.018) ** 2 - ((F[:, 0] - uc) / 0.022) ** 2) * (np.sign(F[:, 1]) == side_v)
            F[:, 1] += side_v * amt * w
        w = np.exp(-((F[:, 2] - 0.095 * height_k) / 0.022) ** 2) * np.clip(-F[:, 0] / (0.2 * L), 0, 1) * np.exp(-(F[:, 1] / 0.02) ** 2)
        F[:, 0] += 0.006 * w
    base["F"] = F
    print("%s foot fitted: length %.1f cm (scale %.2f), height %.1f cm; front x %.2f..%.2f, heel x %.2f..%.2f, width x %.2f..%.2f" % (
        WHO, L_sheet * 100, s, F[:, 2].max() * 100, kf.min(), kf.max(), kb.min(), kb.max(), kw.min(), kw.max()))
    return base


TOE_GRADE = ((1.3, 0.0), (1.0, 0.002), (0.9, 0.006), (0.82, 0.010), (0.74, 0.015))   # (big toe first: size, metres back)
# (nineteenth round, the fourth critic: "the toes are a row of jagged triangular teeth". The bundle's foot un-subdivided
# twice leaves each toe a little pyramid that no smoothing rounds. Now it is un-subdivided once (each toe a round
# tube with a domed end), shaped (the brother's shape_foot: round tips, a broad big toe, the arch, the heel) and then
# collapsed by Blender's decimate (which keeps curvature where it is and spends few triangles on the flat sole and
# instep) down to FOOT_KEEP_TRIS.)
FOOT_UNSUB = 1
FOOT_PLANAR = float(arg("--foot-planar", "0"))   # degrees: thin_foot merges faces flatter than this (0: collapse to FOOT_KEEP_TRIS)
FOOT_KNOB = (0.010, 0.011)         # the inner and outer ankle bones, metres out (the inner higher; the critic: "add the ankle bones")
TOE_BIG = 0.35                     # shape_foot: the big toe this much broader across
ARCH = 0.008                       # shape_foot: metres the inner arch is lifted
HEEL_OUT = 0.006                   # shape_foot: metres the heel is rounded out behind


def shape_foot(base):
    """The brother's shape_foot (tools/build_brother.py), copied: on the fitted foot (u forward, v outward, z up) each
    toe's end clipped to a half ellipsoid round the foot's forward line (a round tip), the big toe broader, the inner
    arch lifted, the heel rounded out. Changes base["F"]."""
    F = base["F"].copy()
    for i, comp in enumerate(base["toes"]):
        c = np.array(comp)
        Q = F[c]
        mean = Q.mean(0)
        d = np.array((1.0, 0.0, 0.0))
        b = np.array((0.0, 0.0, 1.0))
        a = np.cross(b, d)
        rel = Q - mean
        s, ra, rb = rel @ d, rel @ a, rel @ b
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
    t = (u - heel) / L
    arch = np.clip(np.sin(np.clip((t - 0.2) / 0.45, 0, 1) * math.pi), 0, 1) * np.clip(-v / 0.03, 0, 1) * (1.0 - smooth01(0.01, 0.035, z))
    F[:, 2] += ARCH * arch
    hw = np.exp(-((z - 0.03) / 0.025) ** 2) * np.clip((heel + 0.05 - u) / 0.05, 0, 1)
    F[:, 0] -= HEEL_OUT * hw
    F[:, 2] = np.maximum(F[:, 2], 0.0)
    print("%s FOOT shaped: round toe tips, the big toe %d%% broader, arch %.0f mm, heel %.0f mm out" % (
        WHO, int(TOE_BIG * 100), ARCH * 1000, HEEL_OUT * 1000))
    base["F"] = F
    return base
TOE_REFINE = (0.034, 2, 0.25)    # the toes' zone (metres behind the tips), smoothing rounds, strength


def refine_toes(base):
    """This figure's addition (the critic: "a sawtooth of polygon spikes" at the toes; un-subdivided twice, each toe
    is a little pyramid): the faces of the toes' zone split once on a smooth surface (bmesh's subdivide with smooth),
    then that zone relaxed (Taubin, which keeps its size), the soles kept on the ground; the tips found again. Changes
    base in place."""
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
    if FOOT_UNSUB >= 2:
        bmesh.ops.subdivide_edges(bm, edges=list(edges), cuts=1, smooth=1.0, use_grid_fill=True, use_smooth_even=True)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4], quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.verts.index_update()
    P = np.array([tuple(v.co) for v in bm.verts], float)
    nf = [[v.index for v in f.verts] for f in bm.faces]
    # (the faces round the split ones came out with five or more corners: fans of triangles, for the exporter)
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
    tips = [int(np.argmin(np.linalg.norm(P - t, axis=1) - 2.0 * P[:, 0])) for t in tips0]
    tips = []
    for t in tips0:
        near = np.where(np.linalg.norm(P - t, axis=1) < 0.012)[0]
        tips.append(int(near[np.argmax(P[near, 0])]) if len(near) else int(np.argmin(np.linalg.norm(P - t, axis=1))))
    print("%s toes refined: %d faces split, %d triangles a foot now" % (WHO, len(nf) - len(faces), sum(len(f) - 2 for f in nf)))
    base["F"], base["faces"], base["tips"] = P, nf, tips
    if FOOT_KEEP_TRIS:
        base = thin_foot(base, FOOT_KEEP_TRIS)
        # (twenty-first round: the collapse left the toes' tops faceted, ridges catching the light as shards: the toes'
        # zone evened again after it, Taubin, so it keeps its size; the soles on the ground)
        P, nf = base["F"], base["faces"]
        E = set()
        for f in nf:
            for i in range(len(f)):
                a, b = f[i], f[(i + 1) % len(f)]
                E.add((min(a, b), max(a, b)))
        E = np.array(sorted(E))
        deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
        w = np.clip((P[:, 0] - zone) / 0.015, 0, 1) * TOE_AFTER[1]
        for _ in range(TOE_AFTER[0]):
            for k in (1.0, -1.04):
                acc = np.zeros_like(P)
                np.add.at(acc, E[:, 0], P[E[:, 1]])
                np.add.at(acc, E[:, 1], P[E[:, 0]])
                P += (acc / np.maximum(deg, 1)[:, None] - P) * (w * k)[:, None]
            P[:, 2] = np.maximum(P[:, 2], 0.0)
        base["F"] = P
    return base


TOE_AFTER = (int(arg("--toe-after", "3")), 0.5)   # (twenty-first round) Taubin rounds and strength over the toes after the collapse
FOOT_TOE_HOLD = float(arg("--toe-hold", "0.022"))   # (twenty-first round: metres behind the tips held from the collapse; was 0.045, which held about 600 triangles a foot)
FOOT_KEEP_TRIS = int(arg("--foot-keep", "430"))   # (twenty-first round: 650 before)    # (sixteenth round: the refined foot was 784 triangles; collapsed back to about this many, the
                         # rounded toes kept: the flat sole and instep give most of them up. 0 keeps all.)


def thin_foot(base, keep):
    """The refined foot's triangles collapsed (Blender's decimate, Collapse) down to `keep`, its ankle loop and the
    ring of points next to it held (they are zipped to the shin), the rest renumbered: the loop by position, the toes
    and tips by the nearest new point to the old ones."""
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
    tip_u = float(F[base["tips"], 0].min())
    toe_zone = {v for c in base["toes"] for v in c} | set(np.where(F[:, 0] > tip_u - FOOT_TOE_HOLD)[0].tolist())
    g.add([i for i in range(len(F)) if i not in held and i not in toe_zone], 1.0, "REPLACE")   # (nineteenth round: the toes held too: collapsed, they came out as teeth)
    dec = ob.modifiers.new("fewer", "DECIMATE")
    if FOOT_PLANAR:
        # (nineteenth round: collapsed with the toes held, the sole and instep folded into dark shards; only the near
        # flat stretches merged instead (planar dissolve, never across the open ankle loop), then triangulated)
        dec.decimate_type = "DISSOLVE"
        dec.angle_limit = math.radians(FOOT_PLANAR)
        dec.use_dissolve_boundaries = False
    else:
        dec.decimate_type = "COLLAPSE"
        dec.ratio = min(1.0, keep / max(n_before, 1))
        dec.vertex_group = "free"
        dec.use_collapse_triangulate = False
    bpy.context.view_layer.update()
    ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get())
    m2 = ev.to_mesh()
    if FOOT_PLANAR:
        import bmesh
        bm = bmesh.new()
        bm.from_mesh(m2)
        bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4], quad_method="BEAUTY", ngon_method="BEAUTY")
        bm.to_mesh(m2)
        bm.free()
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
    """The fitted foot put into the Mesh, its ankle loop zipped to the shin's last ring. Before the zip (this figure's
    addition) the foot's top is drawn toward the ring over FOOT_BLEND, its middle and its size, so the shin runs into
    the foot with no ledge. Gives (point ids, base face ids, zip face ids)."""
    F = base["F"].copy()
    o, f_, l_ = (np.array(v, float) for v in (origin, fwd, lat))
    up = np.array((0.0, 0.0, 1.0))
    A = np.array([M.P[v] for v in ankle_ring])
    a_uv = np.stack([(A - o) @ f_, (A - o) @ l_], 1)
    a_c = a_uv.mean(0)
    a_r = float(np.linalg.norm(a_uv - a_c, axis=1).mean())
    loop = base["loop"]
    l_c = F[loop, :2].mean(0)
    l_r = float(np.linalg.norm(F[loop, :2] - l_c, axis=1).mean())
    zt = float(F[loop, 2].mean())
    k_top = a_r / max(l_r, 1e-4)
    w = np.clip((F[:, 2] - (zt - FOOT_BLEND)) / FOOT_BLEND, 0.0, 1.0) ** 1.5
    for i in range(len(F)):
        if w[i] <= 0:
            continue
        rel = F[i, :2] - l_c
        F[i, :2] = l_c + (a_c - l_c) * w[i] + rel * (1.0 + (k_top * 0.96 - 1.0) * w[i])
    print("%s foot top drawn to the ankle ring: ring %.1f cm round, foot's top %.1f cm (times %.2f), centres %.1f cm apart; gap up %.1f cm" % (
        WHO, a_r * 100, l_r * 100, k_top, float(np.linalg.norm(a_c - l_c)) * 100, (float(A[:, 2].mean()) - o[2] - zt) * 100))
    ids = [M.add(o + f_ * u + l_ * v + up * z, part) for u, v, z in F]
    f0 = len(M.faces)
    for f in base["faces"]:
        M.face([ids[v] for v in f], part)
    f1 = len(M.faces)

    def ang(Q):
        return np.arctan2((Q - o) @ l_, (Q - o) @ f_)
    zipper(M, [ids[v] for v in loop], list(ankle_ring), ang, part)
    return ids, list(range(f0, f1)), list(range(f1, len(M.faces)))


def unwrap_conformal(P, faces, seams):
    """Blender's conformal unwrap of a piece of surface with the given seam edges. Gives the UV of each face corner."""
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
    """Two UV islands for a foot (its base faces and the zip to the shin): the sole, and the rest cut once up the back
    of the heel to the shin's ring. Gives {"sole": {face: uvs}, "upper": {...}} in metres."""
    import heapq
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
        c = P[M.faces[fi]].mean(0)
        if c[2] - o[2] < 0.022 and abs(n[2]) > 0.55:
            sole.add(k)
    owner = {}
    for k, f in enumerate(lf):
        for i in range(len(f)):
            e = tuple(sorted((f[i], f[(i + 1) % len(f)])))
            owner.setdefault(e, []).append(k)
    seams = {e for e, ks in owner.items() if len(ks) == 2 and ((ks[0] in sole) != (ks[1] in sole))}
    graph = {}
    for e in owner:
        a, b = e
        w = float(np.linalg.norm(Q[a] - Q[b])) * (1.0 + 60.0 * abs(vv[a] + vv[b]) / 2.0) * (1.0 + 4.0 * float(u[a] + u[b] > 0))
        graph.setdefault(a, []).append((w, b))
        graph.setdefault(b, []).append((w, a))
    edge_pts = {v for e in seams for v in e}
    start = min(edge_pts, key=lambda v: u[v])
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
    """A foot's skin (the brother's): the shin's tone (base_c) with `keep` of what was projected, the gaps between
    the toes and their undersides in soft shade, the toe tips and heel a little rosier, a pale toenail with a darker
    rim on each toe. frame = (origin, fwd, lat); toes = [(tip point, nail radius)], big toe first."""
    o, f_, l_ = (np.array(v, float) for v in frame)
    up = np.array((0.0, 0.0, 1.0))
    soft = blur(rgb, 4)
    d = pos - o
    u = (d * f_).sum(-1)
    h = d[..., 2]
    # (the brother's later version: the shin's last `fade` metres above the ring where the two islands meet go over to
    # the foot's tone by degrees, so the seam has one colour on both sides)
    k_ = keep + (1.0 - keep) * smooth01(ring_z, ring_z + fade, h)
    both = mine | ((shin if shin is not None else np.zeros_like(mine)) & (h < ring_z + fade))
    rgb[both] = base_c * (1 - k_[both])[:, None] + soft[both] * k_[both][:, None]
    nu = (nrm * f_).sum(-1)
    nl = np.abs((nrm * l_).sum(-1))
    nz = nrm[..., 2]
    tip_u = min(float(np.dot(np.array(t, float) - o, f_)) for t, _ in toes)
    root_u = tip_u - 0.05
    r_ = np.maximum(smooth01(root_u - 0.02, root_u + 0.02, u), smooth01(-0.02, -0.06, u))[mine][:, None]
    rgb[mine] *= 1.0 + r_ * (np.array((1.04, 0.96, 0.94)) - 1.0)
    sole = mine & (nz < -0.5) & (h < 0.02)
    rgb[sole] *= np.array((1.04, 1.0, 0.94))
    gap = mine & (u > root_u) & (nl > 0.5) & (h < 0.035)
    rgb[gap] *= 0.84
    under = mine & (u > root_u) & (nz < -0.2) & (h > 0.004)
    rgb[under] *= 0.9
    # (seventeenth round, the third critic: "a hard, lighter outline runs across the top of each foot ... white specks
    # at the toe tips": the line drawn across the foot at the toes' root is gone, and the nails are soft pale shapes,
    # faded in from their edge, with no rim)
    for i, (t, r) in enumerate(toes):
        t = np.array(t, float)
        c = t - f_ * (r * 0.9) + up * (r * 0.55)
        dd = pos - c
        along_ = (dd * f_).sum(-1)
        across = (dd * l_).sum(-1)
        e = (along_ / (r * 1.15)) ** 2 + (across / r) ** 2
        nail = mine & (e < 1.0) & ((nz > 0.25) | (nu > 0.5)) & (dd[..., 2] > -r * 0.6)
        k = (0.4 * smooth01(1.0, 0.45, e))[nail][:, None]
        rgb[nail] = rgb[nail] * (1 - k) + np.array((0.80, 0.70, 0.64)) * k
    # (and every shade laid on above had a hard edge where its mask ended, the critic's "seam outline" across the top
    # of the foot: the foot's texels blurred among themselves only, so the shades fade into each other)
    m = mine.astype(float)[..., None]
    num = box_blur(rgb * m, 6)
    den = box_blur(m, 6)
    soft2 = num / np.maximum(den, 1e-4)
    rgb[mine] = soft2[mine]
    return rgb


# ------------------------------------------------------------------------------------------------------------------
# The head, measured off the head sheet
# ------------------------------------------------------------------------------------------------------------------

# The head's rings (head-sheet rows, from the chin up to the cap's band), then the bare skull above it (seventh round,
# the user: "We should make the captain model without a hat as well"): the cap and its peak are their own piece
# (build_cap), sitting on a finished cranium.
# (eighth round: the bare lower face its true length, nose's base to chin about as far as nose's base to brow: the
# lips, under the lip, the chin's pad jutting to the lips' line, the chin's and jaw's underside, the throat under the
# jaw where the neck begins)
HEAD_RING_ROWS = [768, 750, 722, 690, 645, 605, 565, 525, 488, 455, 425]
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
SKULL_HALF = {455: 194.0, 488: 201.0, 525: 205.0, 565: 202.0, 605: 195.0, 645: 186.0, 690: 178.0, 722: 168.0, 750: 150.0, 768: 128.0}
# The bare face's front below the nose (seventh round; the sheet's beard hides it): the head sheet's side-view column
# of his face's front by row: the upper lip, the lips, the chin (a strong one), under the chin into the throat.
BARE_FRONT = {605: 1479.0, 645: 1483.0, 690: 1491.0, 722: 1481.0, 750: 1528.0, 768: 1618.0}
JAW_TAPER = {645: 0.08, 690: 0.16, 722: 0.34, 750: 0.32, 768: 0.04}
# (the jaw's rings squarer than the rest, so the jawline reads as an edge from the chin back to a square angle)
JAW_SQUARE = {690: 0.86, 722: 0.8, 750: 0.82}
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
EAR_OUT = 0.027               # how far its rim stands out from the head


def head_measure(sh, rows=None, zf=None):
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
        rings.append((float((zf or head_z)(r)), hw, yf, yb, JAW_TAPER.get(r, 0.0)))
    return rings


def skull_measure(band):
    """The skull's rings above the band: an egg rounding from the band's ring (drawn in by SKULL_IN) to the crown,
    the back fuller than the front (an old man's cranium), its middle a little back as it rises."""
    z0, hw0, yf0, yb0, _ = band
    # (eighth round: the skull at the band no wider than his temples below it, so the bare head rounds in, not a box)
    hw0, yf0, yb0 = min(hw0 - SKULL_IN, SKULL_HALF[455] * HEAD_SX + 0.004), yf0 + SKULL_IN, yb0 - SKULL_IN
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


# ------------------------------------------------------------------------------------------------------------------
# Ninth round: the bare head from its own sheet, tools/art_src/concept_captain_head_bare.jpg (six views of him bald and
# clean-shaven: front, three-quarter, side, three-quarter back, back, from below). The user: "The heads and hands need
# a lot of work on all three- make sure you are matching pose silhouettes aggressively". Its figures are cut from the
# flat ground by colour; the head's rings are built from the front and side silhouettes together, the back checked,
# and the model laid over each view as a silhouette difference (bare_diff). The old head sheet's rows (which the face's
# forms, the refining and the cap are measured in) are carried onto this sheet by shared landmarks (BARE_LM).
# ------------------------------------------------------------------------------------------------------------------

BARE_SHEET = os.path.join(ART, "concept_captain_head_bare.jpg")
BARE_BACK_W = 1.12            # the back view is drawn this much narrower than the front (its dome: 328 px to 373)
# Tenth round (the user, of the side view beside the base-body sheet: "See how the head connection is totally messed up
# and doesn't match reference"): the head's size and place re-derived from concept_captain_tpose.jpg, nothing invented.
# Measured there: the ear's middle at side column 1435 (6 mm in front of his middle) and row 300, the nose's tip at
# column 1607 (171 px, 21.2 cm, ahead of the ear), the eyes at row 280, the ears' outer width 29 cm in the front view.
# On the bare sheet the ear's middle is at side column 1766, the nose's tip at 1358 (408 px), the eyes at row 525, the
# ears 555 px across: both say 0.52 mm a bare-sheet pixel (0.43 before: the head was a fifth too small), and the head
# sits with its ear over the front of his chest, the face carried forward (it stood upright, set back, on a stalk).
# (The ninth round's 2 cm "raise so a short neck shows" is gone: the sheet shows almost no neck.)
FORM_COL_SCALE = 1.05         # the old head sheet's eyes 5.4 cm out from his middle, the bare sheet's 5.1 (at 0.52 mm)
BS = 0.00052                  # metres a pixel of the bare sheet (measured against the body sheet, above)
BARE_EYE = 525.0              # the bare sheet's eye row (the slits; 499 was the brows' underside)
Z_EYE = float((SOLE - 280.0) * S)
BARE_SPAN = {"front": (60, 700), "q": (705, 1350), "side": (1350, 1960), "qback": (1960, 2580), "back": (2580, 3100)}
# (the side view's middle: the ear's middle, 1766, carried 6 mm back so it stands over the body sheet's ear)
BARE_MID = {"front": 377.5, "side": 1778.0, "back": 2831.0}
# old head-sheet rows -> bare-sheet rows: crown, the cap's band, brow, eyes, nose's base, mouth, chin, throat
# (tenth round, read again off the bare sheet: brows 482, eyes 525, the nose's base 665, the mouth's line 742, the chin's
# lowest point 928, the throat's corner 950)
OLD_LM = np.array([252.0, 425.0, 446.0, 485.0, 595.0, 638.0, 716.0, 768.0])
BARE_LM = np.array([186.0, 452.0, 482.0, 525.0, 665.0, 742.0, 928.0, 950.0])
# The skull's width in the front view where the sheet's hair tufts and ears stand out of it (bare rows: pixels across):
# the dome rounding into narrower temples, then the cheekbones, the jaw measured below.
BARE_SKULL_W = {326: 411.0, 346: 424.0, 366: 432.0, 386: 436.0, 406: 437.0, 426: 436.0, 446: 433.0, 466: 432.0,
                486: 436.0, 526: 444.0, 566: 450.0, 606: 452.0, 646: 451.0, 662: 446.0}
BARE_NOSE = (552, 668)        # the nose's rows: the face's front taken straight under it (side view)
# the nose's width in the front view by row (pixels): the bridge, widening into the bulb, the nostrils' wings
BARE_NOSE_W = ((552, 46), (572, 58), (592, 84), (606, 122), (620, 148), (636, 158), (652, 152), (668, 128))
# the ear's top, lobe's bottom rows, front (where it joins), back columns (side view; tenth round, read again: it was
# placed 3 cm too far back)
BARE_EAR = (485.0, 645.0, 1720.0, 1812.0)
# The head's rings (bare rows) from the crown down to under the chin; below them the torso's two top rings are his neck
BARE_ROWS = [196, 212, 232, 256, 282, 310, 340, 372, 404, 434, 462, 490, 520, 550, 580, 610, 640, 670, 700, 730, 760,
             790, 818, 845, 868, 888]


def _interp_x(x, xs, ys):
    """Piecewise linear, carried on straight past both ends."""
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    x = np.asarray(x, float)
    lo = ys[0] + (x - xs[0]) * (ys[1] - ys[0]) / (xs[1] - xs[0])
    hi = ys[-1] + (x - xs[-1]) * (ys[-1] - ys[-2]) / (xs[-1] - xs[-2])
    return np.where(x < xs[0], lo, np.where(x > xs[-1], hi, np.interp(x, xs, ys)))


def bare_z(brow):
    return Z_EYE - (np.asarray(brow, float) - BARE_EYE) * BS


def bare_row(z):
    return BARE_EYE + (Z_EYE - np.asarray(z, float)) / BS


def bare_mask_of(pix):
    """The figures: unlike the flat ground (the guide lines painted out first)."""
    bg = np.median(np.concatenate([pix[:60, :60].reshape(-1, 3), pix[-60:, :60].reshape(-1, 3), pix[:60, -60:].reshape(-1, 3)]), 0)
    d = np.abs(pix - bg).max(-1)
    lines = np.where((np.abs(pix[:, 70:110] - bg).max(-1) > 0.02).mean(1) > 0.8)[0]
    m = d > 0.08
    for r in lines:
        m[max(r - 2, 0):r + 3] = d[max(r - 2, 0):r + 3] > 0.14
    return m


def bare_edges(sh, view, row):
    c0, c1 = BARE_SPAN[view]
    cs = np.where(sh.bare_mask[int(row), c0:c1])[0]
    return (cs.min() + c0, cs.max() + c0 + 1) if len(cs) else None


def bare_ring(sh, row):
    """(z, half-width, front y, back y) of his head at a bare-sheet row."""
    f = bare_edges(sh, "front", row)
    keys = sorted(BARE_SKULL_W)
    if row >= keys[0] and row <= keys[-1]:
        w = float(np.interp(row, keys, [BARE_SKULL_W[k] for k in keys]))
    else:
        w = float(f[1] - f[0])
    s = bare_edges(sh, "side", row)
    front = float(s[0])
    if BARE_NOSE[0] <= row <= BARE_NOSE[1]:
        a = bare_edges(sh, "side", BARE_NOSE[0] - 6)[0]
        b = bare_edges(sh, "side", BARE_NOSE[1] + 4)[0]
        t = (row - BARE_NOSE[0]) / (BARE_NOSE[1] - BARE_NOSE[0])
        front = a + (b - a) * t + 10.0
    back = float(s[1]) if row <= 760 else float(bare_edges(sh, "side", 760)[1]) - (row - 760) * 0.4
    return (float(bare_z(row)), w / 2.0 * BS, (front - BARE_MID["side"]) * BS, (back - BARE_MID["side"]) * BS, 0.0)


def build_head(M, sh, T):
    """Ninth round: his head's rings from the bare sheet's front and side silhouettes, from the crown down to under
    his chin, bridged onto the torso's top ring; the torso's two top rings set as his neck (a short thick column under
    the jaw, as the sheet's views have it); then the nose and ears as shells of their own. (The cap: build_cap.)"""
    top_ring = T[-1]
    # Tenth round: the neck is short, thick and leans forward under the head carried ahead of him; the torso's top two
    # rings are set from tables (NECK_RINGS: half-width, forward position and the body sheet's row of each column, his
    # front middle round to his back): low at the front, under his chin, high at the nape, wide at the back where the
    # trapezius rises into the nape. And the upper chest under the chin (the front of the ring below them).
    for ring, table in ((T[-1], NECK_RINGS[0]), (T[-2], NECK_RINGS[1])):
        for k in range(TORSO_N):
            kk = k if k <= 8 else TORSO_N - k
            x, y, row = table[kk]
            M.P[ring[k]] = np.array((x if k <= 8 else -x, y, float(body_z(row))), float)
    for k, (x, y, row) in CHEST_TOP.items():
        for kk, sx in ((k, 1.0), ((TORSO_N - k) % TORSO_N, -1.0)):
            M.P[T[-3][kk]] = np.array((x * sx, y, float(body_z(row))), float)
    upper = [r for r in BARE_ROWS if r <= 730]
    rings = [bare_ring(sh, r) for r in reversed(upper)]
    up_pts = []
    for (z, hw, yf, yb, taper), row in zip(rings, reversed(upper)):
        cy, d = (yf + yb) / 2.0, (yb - yf) / 2.0
        up_pts.append(ring_points(0.0, cy, z, hw, d, d, TORSO_N, 0.9 if row > 640 else 0.95))
    # The lower face (the user: "why is his jaw just straight flat across?"): loops that follow the jaw, not level rings.
    # Each loop's front five columns (his front middle to his side) are placed from the sheet: on the face's surface at
    # their own rows (the jowls, the chin's pad), or as measured points (the jawline: from the chin's lowest point in
    # the middle, along the U the front view draws and down the slant the side view draws, up to the jaw's angle below
    # and in front of the ear; the under-jaw turning back from it to the throat, set back from the chin, as the view from
    # below shows). The columns round the back lie between the ring at row 730 and the neck, a little full (a fat nape).
    low = []
    n_low = len(JAW_LOOPS)
    neck_top = np.array([M.P[v] for v in top_ring])
    last_up = np.array(up_pts[0])          # (the level ring at row 730, the lowest)
    for li, (name, kind, cols) in enumerate(JAW_LOOPS):
        pts = []
        f = (li + 1.0) / (n_low + 1.0)
        for k in range(TORSO_N):
            kk = k if k <= 8 else TORSO_N - k
            sx = 1.0 if k <= 8 else -1.0
            if kk <= 4:
                if kind == "s":
                    z, hw, yf, yb, _ = bare_ring(sh, cols[kk])
                    cy, d = (yf + yb) / 2.0, (yb - yf) / 2.0
                    q = np.array(ring_points(0.0, cy, z, hw, d, d, TORSO_N, 0.9)[k], float)
                else:
                    dx, col, row = cols[kk]
                    q = np.array((sx * dx * BS, (col - BARE_MID["side"]) * BS, float(bare_z(row))), float)
            else:
                q = last_up[k] * (1 - f) + neck_top[k] * f
                c = (last_up[:, :2].mean(0) * (1 - f) + neck_top[:, :2].mean(0) * f)
                out = q[:2] - c
                q[:2] += out / max(np.linalg.norm(out), 1e-9) * 0.012 * math.sin(math.pi * f)
            pts.append(q)
        low.append((name, pts))
    # bottom to top: the neck's ring, the lower loops (throat first), the level rings, the crown
    seq = [(name, pts) for name, pts in reversed(low)] + [("upper", p) for p in up_pts]
    prev = top_ring
    H = []
    share = {}
    for i, (name, pts) in enumerate(seq):
        ring = [M.add(q, "head") for q in pts]
        for k in range(TORSO_N):
            j = (k + 1) % TORSO_N
            M.face([prev[k], prev[j], ring[j], ring[k]], "head" if i else "neck")
            M.cell[len(M.faces) - 1] = ("head", i - 1, k)
        hs = HEAD_SHARE.get(name, 1.0)
        # (round the back, by how far down toward the neck the loop lies)
        fb = ([n for n, _ in low].index(name) + 1.0) / (n_low + 1.0) if name in HEAD_SHARE else 0.0
        for k, v in enumerate(ring):
            kk = k if k <= 8 else TORSO_N - k
            share[v] = hs if kk <= 4 else 1.0 - 0.55 * fb
        prev = ring
        H.append(ring)
    s = bare_edges(sh, "side", 188)
    top = M.add((0.0, ((s[0] + s[1]) / 2.0 - BARE_MID["side"]) * BS, float(bare_z(186))), "head")
    for k in range(TORSO_N):
        j = (k + 1) % TORSO_N
        M.face([prev[k], prev[j], top], "head")
        M.cell[len(M.faces) - 1] = ("head", len(seq) - 1, k)
    M.tag["head_rings"] = H
    M.tag["head_share"] = share
    M.tag["jaw_loop"] = H[len(low) - 1 - [n for n, _ in low].index("jaw")]
    bare_nose(M, sh, rings)
    for side in (1, -1):
        ear(M, sh, rings, side)
    return rings


# The lower face's loops (bare sheet), top to bottom. "s": on the face's surface at the given row, for columns 0..4
# (front middle to his side); "p": measured points (pixels out from the front view's middle, the side view's column,
# the row). Read off concept_captain_head_bare.jpg: the chin's lowest point (row 928) in the middle; the jaw's U in the
# front view (62 px out at row 925, 122 at 900, 182 at 850, the angle 228 out at about 815); the jawline's slant in the
# side view (column 1412 at the chin, 1478, 1572, 1640, the angle at 1692, just below and in front of the lobe); the
# under-jaw's line from the chin back to the throat's corner (column 1585, row 950); the view from below for how far in.
JAW_LOOPS = (
    ("jowl", "s", (774, 773, 771, 767, 762)),
    ("pad", "s", (850, 846, 835, 812, 792)),
    ("jaw", "p", ((0, 1412, 928), (62, 1478, 925), (122, 1572, 905), (182, 1640, 862), (228, 1692, 812))),
    ("under", "p", ((0, 1500, 941), (52, 1522, 939), (106, 1582, 928), (160, 1645, 880), (202, 1702, 822))),
    ("throat", "p", ((0, 1578, 952), (60, 1586, 950), (116, 1610, 938), (166, 1655, 892), (196, 1712, 832))),
)
# How much of each loop the head's bone carries (the rest the neck's): the jaw all of it, the under-jaw and throat less.
HEAD_SHARE = {"jowl": 1.0, "pad": 1.0, "jaw": 1.0, "under": 0.85, "throat": 0.65}
# The neck's two rings (the torso's top two): (half-width m, forward y m, body-sheet row) for columns 0..8, his front
# middle round his left side to his back middle (mirrored). Under the chin the throat's front at the body sheet's row
# 456, behind the chin; the nape and the trapezius's rise at the back follow the side view's back line (column 1325 at
# row 392, 1313 at 405); at his sides the trapezius widens toward the shoulders' top ring.
NECK_RINGS = (
    # (fourteenth round, the critic: "the head meets the body at a hard horizontal ledge like a turtleneck"; "cut a
    # nape groove under the occiput": the throat drawn back and down under the chin, the nape in under the skull;
    # the head's forward carriage, which the body sheet's side view draws, is kept)
    # (sixteenth round: the bare sheet's side view puts the back of his neck 3 cm further in than this ring stood, just
    # under the head; the body sheet's back line there is the trapezius beside the spine, so only the middle columns
    # are drawn in: the nape a groove between the two ridges of the trapezius, which keep the body sheet's outline)
    ((0.0, -0.088, 470), (0.046, -0.086, 468), (0.083, -0.068, 461), (0.107, -0.034, 440), (0.119, 0.008, 413),
     (0.113, 0.054, 403), (0.089, 0.080, 399), (0.050, 0.084, 397), (0.0, 0.082, 396)),
    ((0.0, -0.140, 476), (0.062, -0.134, 474), (0.112, -0.100, 466), (0.152, -0.050, 443), (0.176, 0.010, 424),
     (0.166, 0.070, 414), (0.132, 0.114, 409), (0.072, 0.132, 406), (0.0, 0.130, 405)),
)
# The upper chest under the chin (the shoulders' ring's front columns 0 and 1): (x, y, body-sheet row).
CHEST_TOP = {0: (0.0, -0.175, 484), 1: (0.078, -0.168, 481)}   # (eighteenth round: 474, 471, at the neck rings' height: a ledge)


def bare_nose(M, sh, rings):
    """The nose lofted down the bare side view's profile, as wide as the front view paints its red at each row."""
    rows = list(range(BARE_NOSE[0], BARE_NOSE[1] + 1, 10))
    pix = sh.bare_pix
    loops = []
    n = 12
    c0 = int(BARE_MID["front"] - 110)
    for r in rows:
        tip = (bare_edges(sh, "side", r)[0] - BARE_MID["side"]) * BS
        z = float(bare_z(r))
        base = face_front_at(rings, z) + 0.012
        # (tenth round: the width read off the front view by row, a narrow bridge into a big round bulb; measured by
        # its red, the rosy cheeks beside it were counted in and made the nose a box from the front)
        width = float(np.interp(r, [a for a, _ in BARE_NOSE_W], [b for _, b in BARE_NOSE_W]))
        half = width / 2.0 * BS
        wings = 0.25 * float(smooth01(625.0, 660.0, r))
        cy, d = (tip + base) / 2.0, max((base - tip) / 2.0, 0.003)
        pts = ring_points(0.0, cy, z, half, d, d, n, 1.0)
        pts = [(x * (1.0 + wings * float(np.clip((y - cy) / d + 0.3, 0.0, 1.0))), y, zz) for x, y, zz in pts]
        loops.append([M.add(q, "nose") for q in pts])
    # (the bulb rounded under: a last loop drawn in toward the nostrils' middle, a little lower)
    last = loops[-1]
    cen = np.mean([M.P[i] for i in last], axis=0)
    loops.append([M.add(cen + (np.array(M.P[i]) - cen) * np.array((0.72, 0.6, 1.0)) - np.array((0.0, 0.0, 0.006)), "nose") for i in last])
    for a, b in zip(loops, loops[1:]):
        M.bridge(a, b, "nose")
    last = loops[-1]
    c = M.add((0.0, float(np.mean([M.P[i][1] for i in last])), M.P[last[0]][2] - 0.003), "nose")
    for j in range(n):
        M.face([last[j], last[(j + 1) % n], c], "nose")
    first = loops[0]
    c = M.add((0.0, float(np.mean([M.P[i][1] for i in first])) + 0.004, M.P[first[0]][2] + 0.006), "nose")
    for j in range(n):
        M.face([first[(j + 1) % n], first[j], c], "nose")


def bare_diff(objs_tris, sh):
    """The model's silhouette laid over the bare sheet's front, side and back views: white both, red the model only,
    cyan the sheet only; the worst gap between the two outlines (cm, and the 99th percentile), down to the neck."""
    if not OUT:
        return {}
    out = {}
    # (the side view below 870 is his trapezius sloping to the shoulders, the back view below 470 his neck, which it
    # draws narrower than his jaw: the sheet's own views disagree there)
    for view, last_row in (("bare_front", 900), ("bare_side", 870), ("bare_back", 470)):
        P = np.concatenate([o[0] for o in objs_tris])
        tris, off = [], 0
        for pts, tr, fam in objs_tris:
            for ti, t in enumerate(tr):
                if fam[ti] in ("arm", "hand", "sidecap", "leg", "foot", "torso", "boxers", "cap"):
                    continue
                tris.append((t[0] + off, t[1] + off, t[2] + off))
            off += len(pts)
        P2, dep = project(view, P)
        zb, _ = raster(P2, dep, tris, sh.bare_mask.shape)
        model = np.isfinite(zb)
        c0, c1 = BARE_SPAN[view[5:]]
        sheet = np.zeros_like(model)
        sheet[:, c0:c1] = sh.bare_mask[:, c0:c1]
        keep = np.zeros(model.shape[0], bool)
        keep[150:last_row] = True
        model &= keep[:, None]
        sheet &= keep[:, None]
        model[:, :c0] = False
        model[:, c1:] = False
        pic = np.ones(model.shape + (3,)) * 0.12
        pic[model & sheet] = (0.92, 0.92, 0.92)
        pic[model & ~sheet] = (0.95, 0.15, 0.15)
        pic[~model & sheet] = (0.1, 0.85, 0.9)
        save_rgb(os.path.join(OUT, "diff_%s.png" % view), pic[100:last_row + 20, c0:c1])
        d, my, mx = boundary_distance(model, sheet)
        out[view] = (round(float(d.max()) * BS * 100, 2), round(float(np.percentile(d, 99)) * BS * 100, 2))
    print("CAPTAIN bare silhouette gaps (cm: worst, 99%%): %s" % out)
    return out


# Landmarks read off the bare sheet (column, row) by view, to check the model's own points against (tenth round: the
# outline can agree while the forms inside it are wrong). The mouth's corners are painted, not modelled.
BARE_MARKS = {
    "bare_front": {"chin": (377.5, 930), "jaw angle (his right)": (159, 820), "jaw angle (his left)": (596, 820),
                   "lobe (his right)": (135, 645), "nose tip": (382, 625)},
    "bare_side": {"nose tip": (1358, 625), "chin": (1412, 928), "jaw angle": (1692, 812), "ear top": (1765, 485),
                  "lobe": (1748, 645), "throat": (1585, 950), "crown": (None, 186)},
}


def bare_landmarks(M):
    P = np.array(M.P)
    if "base_marks" in M.tag:
        # (twelfth round: the base head's own points)
        b = M.tag["base_marks"]
        b0 = M.tag["base_head"][0]
        mir = None
        ids = sorted(b.values())
        pts = {"chin": P[b0 + 284], "nose tip": P[b0 + 288], "crown": P[b0 + 291], "jaw angle": P[b0 + 52],
               "jaw angle (his left)": P[b0 + 52], "ear top": P[b0 + BH_EAR_TOP], "lobe": P[M.tag["earlobe_l"][0]],
               "lobe (his right)": P[M.tag["earlobe_r"][0]], "throat": P[M.tag["base_throat"]]}
        pts["jaw angle (his right)"] = pts["jaw angle"] * np.array((-1.0, 1.0, 1.0))
        out = {}
        for view, marks in BARE_MARKS.items():
            for name, (c, r) in marks.items():
                q, _ = project(view, pts[name][None, :])
                dc = 0.0 if c is None else float(q[0, 0] - c)
                dr = float(q[0, 1] - r)
                out["%s %s" % (view[5:], name)] = round(math.hypot(dc, dr) * BS * 100, 2)
        print("CAPTAIN landmarks (cm off the sheet): %s" % json.dumps(out))
        return out
    fam = np.array([part_family(p) for p in M.part])
    jaw = M.tag["jaw_loop"]
    nose = np.where(fam == "nose")[0]
    earl = np.where(np.array(M.part) == "ear_l")[0]
    earr = np.where(np.array(M.part) == "ear_r")[0]
    head = np.where(fam == "head")[0]
    pts = {"chin": P[jaw[0]], "jaw angle (his right)": P[jaw[12]], "jaw angle (his left)": P[jaw[4]], "jaw angle": P[jaw[4]],
           "lobe (his right)": P[M.tag["earlobe_r"][0]], "lobe": P[M.tag["earlobe_l"][0]],
           "nose tip": P[nose[np.argmin(P[nose, 1])]], "ear top": P[earl[np.argmax(P[earl, 2])]],
           "throat": P[M.tag["head_rings"][0][0]], "crown": P[head[np.argmax(P[head, 2])]]}
    out = {}
    for view, marks in BARE_MARKS.items():
        for name, (c, r) in marks.items():
            q, _ = project(view, pts[name][None, :])
            dc = 0.0 if c is None else float(q[0, 0] - c)
            dr = float(q[0, 1] - r)
            out["%s %s" % (view[5:], name)] = round(math.hypot(dc, dr) * BS * 100, 2)
    print("CAPTAIN landmarks (cm off the sheet): %s" % json.dumps(out))
    return out


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


# Tenth round (the user: "The captains jaw and ears are very wrong"; they were flat square plates standing straight out
# at mid-head): the ear's outline read off the bare sheet's side view (b back from its front edge, where it joins the
# head, 0..1 over 4.8 cm; v up from the lobe's bottom, 0..1 over 8.3 cm), round from the top of the front edge over the
# helix, down the back, round the hanging lobe and up the front (the tragus).
EAR_OUTLINE = ((0.27, 0.94), (0.49, 1.0), (0.72, 0.96), (0.92, 0.84), (1.0, 0.6), (0.94, 0.42), (0.82, 0.28),
               (0.66, 0.16), (0.54, 0.07), (0.30, 0.0), (0.11, 0.1), (0.04, 0.3), (0.02, 0.5), (0.1, 0.78))
EAR_LOBE = 9                  # the outline's point at the lobe's bottom (the earring hangs there)
EAR_BACK = math.radians(33.0)  # how far the ear lies back from the head's side, hinged at its front edge
# Its loops from the rim in: (share of the way to the bowl's middle, how far proud of the ear's plane, metres). The rim
# rolled forward, the groove inside it, the ridge inside that, the deep bowl.
EAR_LOOPS = ((0.0, 0.0), (0.12, 0.004), (0.27, -0.001), (0.43, 0.002), (0.66, -0.007))
EAR_MID = (0.36, 0.5)


def skin_x(rings, y, z):
    """The head's surface on his left at (y, z), from the level rings (z, half-width, front, back): x."""
    zs = [r[0] for r in rings]
    order = np.argsort(zs)
    zs = np.array(zs)[order]
    a = float(np.interp(z, zs, np.array([r[1] for r in rings])[order]))
    yf = float(np.interp(z, zs, np.array([r[2] for r in rings])[order]))
    yb = float(np.interp(z, zs, np.array([r[3] for r in rings])[order]))
    cy, d = (yf + yb) / 2.0, (yb - yf) / 2.0
    c = float(np.clip((cy - y) / d, -0.999, 0.999))
    c = math.copysign(abs(c) ** (1 / 0.95), c)
    return a * math.sqrt(max(1.0 - c * c, 0.0)) ** 0.95


def ear(M, sh, rings, side):
    """A real ear: a thick shell joined along its front edge, lying back, its rim rolled, a groove, a ridge and a deep
    bowl on its face, a fleshy hanging lobe, and its back running in to the skull."""
    part = "ear_l" if side > 0 else "ear_r"
    zt, zb = float(bare_z(BARE_EAR[0])), float(bare_z(BARE_EAR[1]))
    y0 = (BARE_EAR[2] - BARE_MID["side"]) * BS
    y1 = (BARE_EAR[3] - BARE_MID["side"]) * BS
    hgt, wid = zt - zb, y1 - y0
    tb, cb = math.tan(EAR_BACK), math.cos(EAR_BACK)

    def place(b, v, proud):
        """A point of the ear's face at (b, v), `proud` metres off its plane, which is hinged at the front edge on
        the skin and lies back by EAR_BACK."""
        # (the side view draws the ear's width as seen, already foreshortened by its lying back)
        y = y0 + b * wid
        z = zb + v * hgt
        x0 = skin_x(rings, y0 + 0.002, z)
        lobe = 1.0 - 0.35 * float(smooth01(0.3, 0.0, v))   # (the lobe lies closer)
        x = x0 + b * wid * tb * lobe + 0.003 + proud
        return (x, y, z)
    loops = []
    for share, proud in EAR_LOOPS:
        loop = []
        for i, (b, v) in enumerate(EAR_OUTLINE):
            bb = b + (EAR_MID[0] - b) * share
            vv = v + (EAR_MID[1] - v) * share
            # (the lobe is solid flesh: no groove or ridge in it)
            pr = proud if v > 0.22 else min(proud, 0.0) * 0.3 + 0.002 * (share > 0)
            loop.append(M.add(mirror_x(place(bb, vv, pr), side), part))
        loops.append(loop)
    centre = M.add(mirror_x(place(EAR_MID[0] - 0.08, EAR_MID[1] - 0.05, -0.012), side), part)
    # the back: behind the rim, then in to the skin a little inside the outline
    back1, back2 = [], []
    for b, v in EAR_OUTLINE:
        x, y, z = place(b, v, -0.006)
        back1.append(M.add(mirror_x((x - 0.001, y + 0.002, z), side), part))
        x2, y2, z2 = place(b * 0.7, 0.5 + (v - 0.5) * 0.8, 0.0)
        back2.append(M.add(mirror_x((skin_x(rings, y2, z2) - 0.004, y2, z2), side), part))
    n = len(EAR_OUTLINE)
    face_out = np.array((side, -0.25, 0.0))
    mid_ = np.array(mirror_x(place(EAR_MID[0], EAR_MID[1], 0.0), side))

    def behind(c, mid_=mid_, side=side):
        d = np.array(c) - mid_
        d[0] = 0.0
        return d - np.array((side * 0.5, 0.0, 0.0)) * np.linalg.norm(d)
    for a, b in zip(loops, loops[1:]):
        for j in range(n):
            k = (j + 1) % n
            M.face([a[j], a[k], b[k], b[j]], part, face_out)
    for j in range(n):
        k = (j + 1) % n
        M.face([loops[-1][j], loops[-1][k], centre], part, face_out)
        M.face([loops[0][k], loops[0][j], back1[j], back1[k]], part, behind)
        M.face([back1[k], back1[j], back2[j], back2[k]], part, behind)
    M.tag["earlobe" + ("_l" if side > 0 else "_r")] = [loops[0][EAR_LOBE]]


def peak(M, sh, rings, zf=None):
    head_z = zf or globals()["head_z"]
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


# The cap's heights (tenth round): from the band's bottom on the head sheet (row 425), set on him at the bare sheet's band
# (452, 1.6 cm over the brows), up to its top at the base-body sheet's cap top (row 106); carried through the face's
# landmarks it stood 5 cm too tall on the taller bare dome.
def cap_z(row):
    return float(_interp_x(row, [135.0, 425.0], [float(body_z(106.0)), float(bare_z(452.0))]))


CAP_CROWN_X = 1.0             # the crown's size across against the head sheet's (the band's is drawn to his skull)
CAP_CROWN_Y = 1.0


def build_cap(sh, M=None):
    """The cap (seventh round: its own piece, `captain_cap`, so the game can take it off): the band and the puffed
    crown measured off the head sheet as before, stood CAP_OUT outside it, with a lining turned in under the band's
    edge (into the head, so no gap shows from below) and the peak. Gives the Mesh and its outer rings."""
    Cm = Mesh()
    meas = head_measure(sh, CAP_ROWS, cap_z)
    rings = []
    for i, (z, hw, yf, yb, _) in enumerate([(float(cap_z(427)),) + meas[0][1:]] + meas[1:]):
        hw, yf, yb = hw + CAP_OUT, yf - CAP_OUT, yb + CAP_OUT
        cy, d = (yf + yb) / 2.0, (yb - yf) / 2.0
        rings.append([Cm.add(q, "cap") for q in ring_points(0.0, cy, z, hw, d, d, TORSO_N, 0.78)])
    for i in range(len(rings) - 1):
        for k in range(TORSO_N):
            j = (k + 1) % TORSO_N
            Cm.face([rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]], "cap")
            Cm.cell[len(Cm.faces) - 1] = ("cap", i, k)
    last = rings[-1]
    zt = float(cap_z(137))
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
    peak(Cm, sh, meas, cap_z)
    flipped = fix_winding(Cm)
    Cm.P0 = [np.array(p, float).copy() for p in Cm.P]
    if M is not None:
        refit_cap(Cm, M, rings)
    print("CAPTAIN cap: %d triangles (%d turned outward), open edges %d" % (len(Cm.tris()), flipped,
          len(open_edges([f for f, p in zip(Cm.faces, Cm.fpart) if p != "peak"]))))
    Cm.tag["rings"] = rings
    return Cm


# Sixteenth round (the critic: "the crown is a hard, flat disc ... a soft, puffy crown that overhangs the band on all
# sides and droops a little to the back"; concept_captain_tpose.jpg and concept_captain_head.jpg agree): the crown's
# rings stood out round their own middle (metres, by ring from the band's bottom), the top's middle raised, the back of
# the upper rings let down. The sheets keep the gold badge on the front (the critic asked for it gone; the sheets win).
CAP_PUFF = (0.0, 0.0, 0.002, 0.008, 0.016, 0.015, 0.008, -0.002)
CAP_DOME = 0.008
CAP_DROOP = 0.009


def cap_puff(Cm):
    P = np.array(Cm.P, float)
    rings = Cm.tag["rings"]
    zs = [float(np.mean([P[v][2] for v in r])) for r in rings]
    order = np.argsort(zs)
    for n, k in enumerate(order):
        r = rings[k]
        c = np.mean([P[v] for v in r], axis=0)
        amt = CAP_PUFF[min(n, len(CAP_PUFF) - 1)]
        for v in r:
            d = P[v][:2] - c[:2]
            d /= max(np.linalg.norm(d), 1e-9)
            P[v][:2] += d * amt
            if n >= 4:
                back = max(0.0, (P[v][1] - c[1]) / max(np.ptp([P[u][1] for u in r]) / 2.0, 1e-6))
                P[v][2] -= CAP_DROOP * back * (n - 3) / (len(rings) - 3)
    top_ring = rings[order[-1]]
    tops = set()
    for f in Cm.faces:
        if len(f) == 3 and sum(1 for v in f if v in top_ring) == 2:
            tops |= set(v for v in f if v not in top_ring)
    for v in tops:
        P[v][2] += CAP_DOME
    Cm.P = [p for p in P]
    print("CAPTAIN cap puffed: crown out %.1f cm, top up %.1f cm" % (100 * max(CAP_PUFF), 100 * CAP_DOME))


def refit_cap(Cm, M, rings):
    """Ninth round: the cap (measured on the old head sheet, a much wider head) refitted to the bare skull: drawn in
    about its band's middle so the band sits CAP_OUT outside his head there, lowered a little in its crown's height,
    then every ring of it pushed out where his dome would come through it."""
    P = np.array(Cm.P, float)
    band = np.array([P[v] for v in rings[0]])
    zb = float(band[:, 2].mean())
    cy = float(band[:, 1].mean())
    H = M.tag["head_rings"]
    Z = np.array([np.mean([M.P[i][2] for i in r]) for r in H])
    def skull_at(z):
        i = int(np.clip(np.searchsorted(Z, z), 1, len(H) - 1))
        t = float(np.clip((z - Z[i - 1]) / max(Z[i] - Z[i - 1], 1e-6), 0, 1))
        return np.array([M.P[v] for v in H[i - 1]]) * (1 - t) + np.array([M.P[v] for v in H[i]]) * t
    sk = skull_at(zb)
    fx = (np.abs(sk[:, 0]).max() + CAP_OUT) / np.abs(band[:, 0]).max()
    fy = ((sk[:, 1].max() - sk[:, 1].min()) / 2.0 + CAP_OUT) / ((band[:, 1].max() - band[:, 1].min()) / 2.0)
    # (tenth round, the user's brief: "band low on the brow, crown puffed wide and flopping, peak thick": only the band
    # is drawn to his skull; the crown keeps the head sheet's size above it (it was all shrunk with the band, small and
    # tall), and the cap is moved to sit centred on his skull front to back)
    sky = (sk[:, 1].max() + sk[:, 1].min()) / 2.0
    t = np.clip((P[:, 2] - zb) / 0.035, 0.0, 1.0)
    kx = fx + (CAP_CROWN_X - fx) * t
    ky = fy + (CAP_CROWN_Y - fy) * t
    P[:, 0] *= kx
    P[:, 1] = sky + (P[:, 1] - cy) * ky
    pushed = 0
    # every point of the cap's outside kept 6 mm clear of his skull's section at its height, along the way out from
    # the skull's middle (his dome is tall: it came through the cap's back)
    for ring in rings:
        for v in ring:
            z = float(P[v][2])
            if z > Z.max():
                continue
            s = skull_at(z)[:, :2]
            sc = s.mean(0)
            d = P[v][:2] - sc
            r_ = float(np.linalg.norm(d))
            if r_ < 1e-6:
                continue
            u = d / r_
            # the skull's reach along u: the furthest of its section's points projected on u, near that way
            proj = (s - sc) @ u
            side = np.abs((s - sc) @ np.array((-u[1], u[0])))
            near = side < 0.03
            reach = float(proj[near].max()) if near.any() else float(proj.max())
            if r_ < reach + 0.014:
                P[v][:2] = sc + u * (reach + 0.014)
                pushed += 1
    Cm.P = [p for p in P]
    print("CAPTAIN cap refitted: across x%.2f, front to back x%.2f; %d points pushed out over his dome" % (fx, fy, pushed))


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
    # (painted on the cap as the head sheet measured it, before it was refitted to his bare skull)
    Cp = Mesh()
    Cp.P, Cp.faces, Cp.fpart = getattr(Cm, "P0", Cm.P), Cm.faces, Cm.fpart
    rgb, hit = paint(Cp, face_uv, "cap", sh, views, Cp.tris())
    P = np.array(Cp.P)
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
NECK_JOINT = (0.0, 0.02, 1.27)
HEAD_JOINT = (0.0, -0.012, 1.37)


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
        # (tenth round: the neck leans forward under the head carried ahead of him: its root behind the throat at
        # the trapezius, the head's pivot behind the jaw's angle and below the ear)
        ("neck", Vector(NECK_JOINT), "chest"),
    ]
    bones.append(("head", Vector(HEAD_JOINT), "neck"))
    for s, sfx in ((1, "_l"), (-1, "_r")):
        sh_ = Vector(mirror_x(joints["shoulder_l"], s))
        el = Vector(mirror_x(joints["elbow_l"], s))
        wr = Vector(mirror_x(joints["wrist_l"], s))
        bones.append(("clavicle" + sfx, Vector((s * 0.04, sh_.y - 0.01, sh_.z + 0.06)), "chest"))
        # (twentieth round: under the clavicle, as the boy's builder has it: the viewer raises the clavicle with the
        # arm, so the shoulder's top lifts instead of folding over the raised arm)
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


# (twentieth round) the clavicle's share of the chest's top toward each shoulder, and the elbow's blend (metres each side)
CLAV_SHARE = float(arg("--clav", "0.7"))
ELBOW_BLEND = float(arg("--elbow-blend", "0.12"))   # (twenty-first round: 0.06; at 0.12 the 120-degree elbow folded 12 edges, not 23)


# Twenty-first round (the brief: a 70-degree grip folded about 140 faces, nearly all fingers): the younger boy's
# knuckle_weights (tools/build_boy.py, 2026-11-18), copied unchanged in what it does: the palm blended into each
# finger across the knuckle row, each joint blended over half the shorter bone beside it, the thumb's ball following it.
KNUCKLE_BEHIND = float(arg("--knuckle-behind", "0.014"))   # metres behind the knuckle where the palm starts to follow the finger
KNUCKLE_PAST = float(arg("--knuckle-past", "0.01"))       # metres past it where the skin is the finger's alone
THENAR_SHARE = float(arg("--thenar-share", "0.35"))
JOINT_BLEND = float(arg("--joint-blend", "0.8"))   # (twenty-first round: 0.5, the boy's; at 0.8 the 75-degree grip folded 68 edges, not 86)   # (tenth pass) the middle and end joints blend over this share of the shorter bone each side
KNUCKLE_PALM = float(arg("--knuckle-palm", "0.004"))   # (tenth pass) metres behind the knuckle where the palm side starts to follow the finger
KNUCKLE_WEIGHTS = "--old-finger-weights" not in ARGS


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
    zt = {"hips_spine": 0.74, "spine_chest": 0.93, "chest_neck": 1.29}
    NECK_SET = (set(T[-1]), set(T[-2]))
    for vi, part in enumerate(M.part):
        p = P[vi]
        fam = part.split("_")[0]
        sfx = "_l" if part.endswith("_l") or "_l_" in part else ("_r" if part.endswith("_r") or "_r_" in part else ("_l" if p[0] >= 0 else "_r"))
        w = {}
        if fam in ("head", "cap", "nose", "ear", "peak"):
            w = {"head": 1.0}
            # (tenth round: the lower face's loops carry their own share, the jaw all head, the throat less)
            t = M.tag["head_share"].get(vi, 1.0) if fam == "head" else 1.0
            if t < 1.0:
                w = {"head": t, "neck": 1 - t}
        elif fam == "torso":
            w = chain_weights(p[2], ["hips", "spine", "chest", "neck"], [zt["hips_spine"], zt["spine_chest"], zt["chest_neck"]], 0.07)
            # near the shoulder: some of the upper arm
            for s, sx in ((1, "_l"), (-1, "_r")):
                # (twentieth round, the boy's way) the top of the chest out toward each shoulder, and the trapezius's outer
                # slope, ride the clavicle
                kc = CLAV_SHARE * float(smooth01(0.04, 0.12, s * p[0])) * float(smooth01(at["upper_arm" + sx][2] - 0.1, at["upper_arm" + sx][2] - 0.02, p[2]))
                if kc > 0:
                    moved = w.get("chest", 0.0) * kc + w.get("neck", 0.0) * kc * 0.5
                    if "chest" in w:
                        w["chest"] *= 1 - kc
                    if "neck" in w:
                        w["neck"] *= 1 - kc * 0.5
                    w["clavicle" + sx] = w.get("clavicle" + sx, 0) + moved
                d = np.linalg.norm(p - at["upper_arm" + sx])
                k = 0.45 * (1 - float(smooth01(0.07, 0.17, d)))
                # (eighteenth round, the pose test: with an arm raised the trapezius's slope by the neck rose with it as a
                # fin; only the points out over the shoulder follow the arm)
                k *= float(smooth01(at["upper_arm" + sx][0] * s - 0.13, at["upper_arm" + sx][0] * s - 0.05, s * p[0]))
                if k > 0:
                    w = {n: v * (1 - k) for n, v in w.items()}
                    w["upper_arm" + sx] = w.get("upper_arm" + sx, 0) + k
                # near the hip: some of the thigh
                if p[2] < at["hips"][2] + 0.02 and s * p[0] > 0.02:
                    k = 0.5 * (1 - float(smooth01(at["thigh" + sx][2] - 0.06, at["hips"][2] + 0.04, p[2]))) * float(smooth01(0.02, 0.09, s * p[0]))
                    w = {n: v * (1 - k) for n, v in w.items()}
                    w["thigh" + sx] = w.get("thigh" + sx, 0) + k
            if vi in NECK_SET[0]:
                w = {"neck": 0.85, "chest": 0.15}
            elif vi in NECK_SET[1]:
                w = {"neck": 0.45, "chest": 0.55}
            if vi in M.tag["crotch"]:
                w = {"hips": 0.6, "thigh_l": 0.2, "thigh_r": 0.2}
        elif fam == "shoulder":
            w = {"chest": 0.2, "clavicle" + sfx: 0.4, "upper_arm" + sfx: 0.4}
        elif fam == "arm":
            J, E, W = at["upper_arm" + sfx], at["forearm" + sfx], at["hand" + sfx]
            Lu = np.linalg.norm(E - J)
            s = along(p, J, E)
            if s > Lu - 0.06:
                s = Lu + along(p, E, W)
            w = chain_weights(s, ["upper_arm" + sfx, "forearm" + sfx, "hand" + sfx], [Lu, Lu + np.linalg.norm(W - E) + 0.005], ELBOW_BLEND)
            k = 0.4 * (1 - float(smooth01(0.0, 0.08, s)))
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
                w = chain_weights(u, ["foot" + sfx, "toe" + sfx], [float(np.dot(at["toe" + sfx] - A, fwd)) if BASE_FEET else 0.135], 0.025 if BASE_FEET else 0.03)
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
        if BASE_FEET:
            # (fifteenth round: the base foot, a sole and an upper island, the brother's way)
            lf = [fi for fi, p in enumerate(M.fpart) if p == "leg" + sfx and len(M.faces[fi]) == 4]
            o, f_, l_ = M.tag["foot_frame" + sfx]
            fi_ = foot_islands(M, M.tag["foot_faces" + sfx], o, f_, l_, lr[-1])
            for g, share in (("upper", 1.4), ("sole", 0.7)):
                ISLANDS["foot_%s%s" % (g, sfx)] = ("skin", share)
                islands["foot_%s%s" % (g, sfx)] = fi_[g]
            islands["leg" + sfx] = grid_uvs(M, lr, lf, 9)
            sole = []
        elif "foot_rings" + sfx in M.tag:
            # (fourteenth round: the foot with toes, its own island)
            lf = [fi for fi, p in enumerate(M.fpart) if p == "leg" + sfx and len(M.faces[fi]) == 4]
            islands["foot" + sfx] = foot_uvs(M, sfx)
            ISLANDS["foot" + sfx] = ("skin", 1.2)
            sole = M.tag["foot_sole" + sfx]
        else:
            lf = [fi for fi, p in enumerate(M.fpart) if p in ("leg" + sfx, "foot" + sfx) and len(M.faces[fi]) == 4]
            sole = [fi for fi, p in enumerate(M.fpart) if p == "foot" + sfx and len(M.faces[fi]) == 3]
        islands["leg" + sfx] = grid_uvs(M, lr, lf, 9)
        islands["sole" + sfx] = planar_uvs(M, sole, np.array((1.0, 0, 0)), np.array((0, -1.0, 0)))
        hand_faces = [fi for fi, p in enumerate(M.fpart) if p == "hand" + sfx]
        if M.tag.get("hand_flat" + sfx):
            # (thirteenth round, as the brother's: laid out as the hands sheet's back and palm views see the hand flat,
            # each face by which way it faces in the flat pose; the bundle's own hand UVs overlap between back and
            # palm, and a projection painted through them came out scrambled; the thumb its own pair of islands)
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
            ef = [fi for fi, p in enumerate(M.fpart) if p == "ear" + sfx]
            s = 1.0 if sfx == "_l" else -1.0
            islands["ear" + sfx] = planar_uvs(M, ef, np.array((0, s, 0.0)), np.array((0, 0, 1.0)))
            continue
        if M.tag.get("hand_uv"):
            # (twelfth round: the base hand keeps its own UV map, one island a hand; the zipper to the forearm takes
            # its wrist's UVs)
            huv = M.tag["hand_uv"]
            allf = [fi for fi, p in enumerate(M.fpart) if p.startswith("hand" + sfx)]
            known = {}
            for fi in allf:
                if fi in huv:
                    known.update(huv[fi])
            isl = {}
            for fi in allf:
                f = M.faces[fi]
                if fi in huv:
                    isl[fi] = [tuple(huv[fi][v]) for v in f]
                else:
                    kn = [known[v] for v in f if v in known]
                    c = np.mean(kn, axis=0) if kn else np.zeros(2)
                    isl[fi] = [tuple(known.get(v, c)) for v in f]
            # (the base UVs are 0..1 of the base hand, about 25 cm: to metres so the packing shares texels fairly)
            isl = {fi: [(u * 0.25, v * 0.25) for u, v in uv] for fi, uv in isl.items()}
            ISLANDS["hand" + sfx] = ("skin", 3.0)
            islands["hand" + sfx] = isl
            ef = [fi for fi, p in enumerate(M.fpart) if p == "ear" + sfx]
            s = 1.0 if sfx == "_l" else -1.0
            islands["ear" + sfx] = planar_uvs(M, ef, np.array((0, s, 0.0)), np.array((0, 0, 1.0)))
            continue
        # each finger and the thumb its own island: round its rings (seam under it, on the palm side) and along it
        for f in FINGERS + ("thumb",):
            rings = M.tag["finger_rings%s_%s" % (sfx, f)]
            tip, root = M.tag["finger_ends%s_%s" % (sfx, f)]
            ff = [fi for fi, p in enumerate(M.fpart) if p == "hand%s_%s" % (sfx, f)]
            isl = grid_uvs(M, rings, [fi for fi in ff if len(M.faces[fi]) == 4], 2)
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
    CHIN = 750.0          # head-sheet row of the chin's underside (eighth round: the bare jaw's)
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

# ==================================================================================================================
# Twelfth round (tools/FIGURE_HEADS.md, "fit a base mesh, do not loft"): his head with its ears and his hands are
# Blender Studio's Human Base Meshes v1.4.1 (CC0), appended from the bundle (kept outside the repo), fitted to his
# own sheets. The lofted head above is still built first (the cap is fitted on it, and the --hair locks), then taken
# off and this one put on in its place, bridged to the torso's top ring (his neck); the lofted hands are no longer
# built (hand_local gives the base hand).
# ==================================================================================================================

BUNDLE = "C:/Projects/reference/human-base-meshes/bundle/human-base-meshes-bundle-v1.4.1/human_base_meshes_bundle.blend"
# The head's shape keys mixed (the Ork's heavy jaw and brow half way to the Real male): the start of the fitting.
HEAD_MIX = {"Ork": 0.5, "Real_MALE": 0.5}


def base_object(name):
    """One object appended from the bundle (matched with spaces taken out: its names have odd spacing)."""
    want = name.replace(" ", "")
    with bpy.data.libraries.load(BUNDLE, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n.replace(" ", "") == want]
    if not dst.objects:
        raise RuntimeError("not in the bundle: %s" % name)
    return dst.objects[0]


def drop_object(ob):
    me = ob.data
    bpy.data.objects.remove(ob, do_unlink=True)
    if me is not None and me.users == 0:
        bpy.data.meshes.remove(me)


def mirror_pairs(P, tol=1e-3):
    """For each point the point at its mirror across x = 0 (itself on the middle line), within tol."""
    P = np.asarray(P)
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


def mirror_even(P, mir):
    P = np.array(P, float)
    Q = P[mir].copy()
    Q[:, 0] *= -1
    P = (P + Q) / 2.0
    P[mir == np.arange(len(P)), 0] = 0.0
    return P


def tps_warp(P, src, dst, smooth=0.0):
    """Thin-plate (3D biharmonic, kernel r) interpolation of the landmark moves src -> dst, with its affine part,
    applied to the points P: the usual smooth landmark warp."""
    src, dst, P = np.asarray(src, float), np.asarray(dst, float), np.asarray(P, float)
    n = len(src)
    K = np.linalg.norm(src[:, None] - src[None], axis=-1)
    A = np.zeros((n + 4, n + 4))
    A[:n, :n] = K + smooth * np.eye(n)
    A[:n, n] = 1.0
    A[:n, n + 1:] = src
    A[n, :n] = 1.0
    A[n + 1:, :n] = src.T
    b = np.zeros((n + 4, 3))
    b[:n] = dst
    sol = np.linalg.solve(A, b)
    Kp = np.linalg.norm(P[:, None] - src[None], axis=-1)
    return Kp @ sol[:n] + sol[n] + P @ sol[n + 1:]


def loops_of(faces):
    """The open edges of a set of faces as closed loops of points, each in order."""
    cnt = {}
    nxt = {}
    for f in faces:
        for k in range(len(f)):
            a, b = f[k], f[(k + 1) % len(f)]
            e = (min(a, b), max(a, b))
            cnt[e] = cnt.get(e, 0) + 1
            nxt[(a, b)] = True
    bnd = [e for e, c in cnt.items() if c == 1]
    adj = {}
    for a, b in bnd:
        # (the open edge's direction as its face runs it)
        if (a, b) in nxt:
            adj[a] = b
        else:
            adj[b] = a
    loops, seen = [], set()
    for s in adj:
        if s in seen:
            continue
        loop, v = [], s
        while v not in seen:
            seen.add(v)
            loop.append(v)
            v = adj.get(v)
            if v is None:
                break
        loops.append(loop)
    return loops


# Landmarks: base-head point (its index in the cage) -> where it goes on him, read off concept_captain_head_bare.jpg.
# ("edge", row, inward px): on his middle line, at the side view's front outline at that row; ("back", row): at its back
# outline; ("top", row): the crown; ("pt", px out from the middle in the front view, side-view column, row). His left
# side is given; the right is its mirror. Read off the sheet (tenth-round measures kept: eyes 525, nose tip 1358 at
# 625, chin 1412 at 928, jaw angle 159/596 at 820 and 1692 at 812, throat 1585 at 950, ear 485..645 and 1720..1812) and
# off crops of it: the slit eyes 46 to 142 px out (inner and outer corners), set under the brow at side column about
# 1500; the mouth's corners 115 px out at 756, drooping, at 1505; the nose's wings 77 px out at 640, back at 1440.
HEAD_MARKS = {
    291: ("top", 186), 290: ("edge", 222, 0), 282: ("edge", 300, 0), 289: ("edge", 405, 0),
    281: ("edge", 485, 0), 274: ("edge", 527, 0), 283: ("edge", 575, 0), 288: ("edge", 625, 0),
    277: ("edge", 652, 0), 287: ("pt", 0, 1440, 672), 278: ("edge", 692, 0), 279: ("edge", 720, 0),
    286: ("edge", 731, 6), 276: ("edge", 762, 0), 275: ("edge", 815, 0), 280: ("edge", 880, 0),
    284: ("pt", 0, 1418, 926), 285: ("pt", 0, 1455, 934), 298: ("pt", 0, 1500, 941), 314: ("pt", 0, 1540, 946),
    292: ("back", 290), 293: ("back", 440), 294: ("back", 580),
    66: ("pt", 96, 1500, 515), 58: ("pt", 104, 1506, 535), 60: ("pt", 46, 1488, 527), 62: ("pt", 142, 1540, 527),
    10: ("pt", 112, 1500, 754), 52: ("pt", 218, 1692, 816), 44: ("pt", 77, 1440, 640), 43: ("pt", 72, 1450, 655),
    # the ear: top, lobe, back, the rim's outermost, its root in front
    108: ("pt", 262, 1772, 486), 106: ("pt", 238, 1748, 642), 110: ("pt", 240, 1795, 560), 138: ("pt", 277, 1790, 525),
    104: ("pt", 270, 1745, 490), 111: ("pt", 277, 1800, 515), 136: ("pt", 272, 1810, 560), 137: ("pt", 258, 1795, 605),
    109: ("pt", 250, 1785, 625), 130: ("pt", 250, 1760, 630), 129: ("pt", 240, 1782, 530), 112: ("pt", 236, 1770, 585),
    33: ("pt", 222, 1722, 560),
    # the big ball nose: the bulb's sides either side of the tip, the bridge's sides, the wings' tops and bottoms
    42: ("pt", 52, 1372, 615), 15: ("pt", 50, 1384, 648), 14: ("pt", 28, 1405, 585), 13: ("pt", 68, 1468, 612),
    16: ("pt", 62, 1462, 664),
    # the heavy frowning brow shelf, 2 to 3 cm ahead of the slit eyes; the fold under it
    6: ("pt", 66, 1440, 486), 28: ("pt", 146, 1500, 494), 74: ("pt", 86, 1468, 505), 75: ("pt", 134, 1495, 507),
    # the puffy cheeks: the apple, the bag under the eye, the top of the fold beside the nose
    81: ("pt", 150, 1488, 585), 72: ("pt", 88, 1462, 556), 27: ("pt", 96, 1462, 608),
    # the lips' sides, the broad chin
    18: ("pt", 58, 1405, 722), 11: ("pt", 62, 1402, 770), 7: ("pt", 84, 1398, 880), 36: ("pt", 92, 1440, 926),
    # the jawline from the chin to the angle (front view's U, side view's slant), and the under-jaw behind it
    37: ("pt", 122, 1572, 905), 120: ("pt", 182, 1640, 862), 119: ("pt", 52, 1522, 939),
}
BH_EAR_TOP, BH_EAR_LOBE = 108, 106
NECK_CUT = (0.018, -0.070, 0.44, 0.010)    # the cage's bottom taken off: below z = b + k (y - a) + lift, behind the chin


def head_mark_targets(sh, mir):
    src, dst = [], []
    out = {}
    for i, spec in HEAD_MARKS.items():
        kind = spec[0]
        if kind == "top":
            s = bare_edges(sh, "side", spec[1] + 6)
            q = (0.0, ((s[0] + s[1]) / 2.0 - BARE_MID["side"]) * BS, float(bare_z(spec[1])))
        elif kind == "edge":
            q = (0.0, (bare_edges(sh, "side", spec[1])[0] + spec[2] - BARE_MID["side"]) * BS, float(bare_z(spec[1])))
        elif kind == "back":
            q = (0.0, (bare_edges(sh, "side", spec[1])[1] - BARE_MID["side"]) * BS, float(bare_z(spec[1])))
        else:
            q = (spec[1] * BS, (spec[2] - BARE_MID["side"]) * BS, float(bare_z(spec[3])))
        out[i] = np.array(q, float)
        if mir[i] != i:
            out[int(mir[i])] = np.array((-q[0], q[1], q[2]), float)
    return out


def head_cage():
    ob = base_object("Head - Generic Topology")
    me = ob.data
    kb = me.shape_keys.key_blocks
    basis = np.array([v.co for v in kb["Basis"].data], float)
    P = basis.copy()
    for k, w in HEAD_MIX.items():
        P += w * (np.array([v.co for v in kb[k].data], float) - basis)
    faces = [list(p.vertices) for p in me.polygons]
    uvl = me.uv_layers[0].data
    fuv = [[tuple(uvl[li].uv) for li in p.loop_indices] for p in me.polygons]
    drop_object(ob)
    return P, faces, fuv


def folds(P, faces, ref=None):
    """Faces turned over against the reference shape's, and neighbouring faces folded sharper than 120 degrees."""
    P = np.asarray(P)
    n = np.array([face_normal(P, f) for f in faces])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    flipped = 0
    if ref is not None:
        r = np.array([face_normal(ref, f) for f in faces])
        r /= np.maximum(np.linalg.norm(r, axis=1, keepdims=True), 1e-12)
        flipped = int(((n * r).sum(1) < 0.0).sum())
    by_edge = {}
    for fi, f in enumerate(faces):
        for k in range(len(f)):
            e = (min(f[k], f[(k + 1) % len(f)]), max(f[k], f[(k + 1) % len(f)]))
            by_edge.setdefault(e, []).append(fi)
    sharp = sum(1 for fs in by_edge.values() if len(fs) == 2 and np.dot(n[fs[0]], n[fs[1]]) < -0.5)
    return flipped, sharp


HEAD_FIT_VIEWS = (("bare_front", 905), ("bare_side", 885), ("bare_back", 690))


def head_fit_round(Hm, sh, frozen, reach=28, damp=0.7, views=HEAD_FIT_VIEWS):
    """One round of pulling the head's outline onto the bare sheet's, view by view (as fit_round does the body)."""
    P = np.array(Hm.P)
    tris = Hm.tris()
    N = normals_of(P, tris)
    move = np.zeros_like(P)
    count = np.zeros(len(P))
    h, w = sh.bare_mask.shape
    for view, last in views:
        c0, c1 = BARE_SPAN[view[5:]]
        T_ = np.zeros_like(sh.bare_mask)
        T_[:, c0:c1] = sh.bare_mask[:, c0:c1]
        P2, dep = project(view, P)
        zb, _ = raster(P2, dep, tris, (h, w))
        R = np.isfinite(zb)
        d2, facing = screen_dir(view, N)
        L = np.linalg.norm(d2, axis=1)
        ok = (np.abs(facing) < 0.6) & (L > 0.35) & ~frozen & (P2[:, 1] < last)
        sc = BS * (BARE_BACK_W if view == "bare_back" else 1.0)
        for v in np.where(ok)[0]:
            p = P2[v]
            dirn = d2[v] / L[v]
            q = p + dirn * 3.0
            if not (0 <= int(q[1]) < h and 0 <= int(q[0]) < w) or R[int(q[1]), int(q[0])]:
                continue
            if not (0 <= int(p[1]) < h and 0 <= int(p[0]) < w):
                continue
            dist = None
            inside = T_[int(p[1]), int(p[0])]
            for k in range(1, reach + 1):
                qq = p + dirn * (k if inside else -k)
                cell = T_[min(max(int(qq[1]), 0), h - 1), min(max(int(qq[0]), 0), w - 1)]
                if cell != inside:
                    dist = (k - 0.5) * (1 if inside else -1)
                    break
            if dist is None:
                continue
            wd = world_dir(view, dirn[None, :])[0]
            if view == "bare_back":
                wd = wd * np.array((BARE_BACK_W, 1.0, 1.0))
            move[v] += wd * dist * BS
            count[v] += 1
    has = count > 0
    move[has] /= count[has, None]
    E = edges_of(Hm.faces)
    D = move.copy()
    W = has.astype(float) * 4.0
    deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
    for _ in range(30):
        acc = np.zeros_like(D)
        np.add.at(acc, E[:, 0], D[E[:, 1]])
        np.add.at(acc, E[:, 1], D[E[:, 0]])
        D = (W[:, None] * move + acc) / np.maximum(W + deg, 1e-9)[:, None]
    D[frozen] = 0.0
    P += D * damp
    Hm.P = [p for p in P]
    return int(has.sum()), float(np.linalg.norm(move[has], axis=1).max() if has.any() else 0.0)


# Nineteenth round (the face-rig builder, tools/FACE_RIG.md "Integration": "a lips' meeting line that IS an edge loop";
# the rig cuts the mouth open along the painted line, and where that line is not an edge it slices every triangle it
# crosses). The base head's lips meet along 286 (the middle) - 40 - 128 on each side, but from 128 to the corner (10)
# the line runs across a quad's diagonal (128, 25 above, 10, 9 below). That quad, and its mirror, is cut along that
# diagonal into two triangles, so the meeting line is edges from corner to corner: LIP_LOOP (one side, the corner
# first; the middle 286 shared), kept through the face's split (a split triangle keeps the midpoint of each edge).
LIP_LOOP = (10, 128, 40, 286)


def lip_line(faces, fuv, mir):
    out_f, out_uv = [], []
    cut = 0
    pairs = [(LIP_LOOP[0], LIP_LOOP[1]), (int(mir[LIP_LOOP[0]]), int(mir[LIP_LOOP[1]]))]
    for f, uv in zip(faces, fuv):
        done = False
        if len(f) == 4:
            for a, b in pairs:
                if a in f and b in f:
                    i, j = f.index(a), f.index(b)
                    if (j - i) % 4 == 2:
                        out_f += [[f[i], f[(i + 1) % 4], f[j]], [f[j], f[(j + 1) % 4], f[i]]]
                        out_uv += [[uv[i], uv[(i + 1) % 4], uv[j]], [uv[j], uv[(j + 1) % 4], uv[i]]]
                        done = True
                        cut += 1
                        break
        if not done:
            out_f.append(f)
            out_uv.append(uv)
    print("CAPTAIN lips' meeting line: %d corner quads cut along it; the line %s and its mirror %s" % (
        cut, list(LIP_LOOP), [int(mir[v]) for v in LIP_LOOP]))
    return out_f, out_uv


def build_base_head(sh, M, T):
    """The base head fitted to him. Gives the head as a Mesh (parts "head", "ear_l", "ear_r"), its UVs
    ({face: ("face", [uv])}, in the face picture), its open neck loop (in order) and its landmarks (index -> target)."""
    P, faces, fuv = head_cage()
    mir = mirror_pairs(P)
    P = mirror_even(P, mir)
    print("CAPTAIN base head: %d points, %d quads, %d on the middle line" % (len(P), len(faces), int((mir == np.arange(len(P))).sum())))
    # the cage's bottom (where a neck would leave it) taken off
    a, b, k, lift = NECK_CUT
    C = np.array([P[f].mean(0) for f in faces])
    rm = (C[:, 2] < b + k * (C[:, 1] - a) + lift) & (C[:, 1] > -0.005)
    faces = [f for f, r in zip(faces, rm) if not r]
    fuv = [u for u, r in zip(fuv, rm) if not r]
    faces, fuv = lip_line(faces, fuv, mir)
    loops = loops_of(faces)
    print("CAPTAIN base head: %d faces taken off its bottom; open loops %s" % (int(rm.sum()), [len(l) for l in loops]))
    loop = max(loops, key=len)
    # landmarks -> his sheet (thin plate)
    marks = head_mark_targets(sh, mir)
    ids = sorted(marks)
    P = tps_warp(P, P[ids], np.array([marks[i] for i in ids]))
    P = mirror_even(P, mir)
    Hm = Mesh()
    Hm.P = [p for p in P]
    Hm.part = ["head"] * len(P)
    for f in faces:
        Hm.face(f, "head")
    ref = P.copy()
    print("CAPTAIN base head warped to %d landmarks; folds %s" % (len(ids), folds(P, faces, ref)))
    face_uv = {fi: ("face", [(0.01 + 0.98 * (u - 0.0), 0.01 + 0.98 * v) for u, v in uv]) for fi, uv in enumerate(fuv)}
    Hm.tag["loop"] = loop
    Hm.tag["marks"] = marks
    Hm.tag["mir"] = mir
    return Hm, face_uv


def repin(Hm, marks, frozen=None, share=1.0):
    """The landmarks moved back onto their targets, the rest carried smoothly (a thin plate of the residuals)."""
    P = np.array(Hm.P)
    ids = sorted(marks)
    src = P[ids]
    dst = src + (np.array([marks[i] for i in ids]) - src) * share
    Q = tps_warp(P, src, dst, smooth=0.0)
    if frozen is not None:
        Q[frozen] = P[frozen]
    Hm.P = [p for p in Q]


def head_fit_stage(Hm, sh, frozen, rounds, reach, mir):
    ref = np.array(Hm.P)
    for r in range(rounds):
        moved, most = head_fit_round(Hm, sh, frozen, reach=reach)
        Hm.P = [p for p in mirror_even(Hm.P, mir)]
        relax(Hm, frozen, 0.15, 1)
        print("CAPTAIN base head fit round %d: %d outline points, most %.1f cm; folds %s" % (r + 1, moved, most * 100, folds(Hm.P, Hm.faces, ref)))


def neck_ring_points():
    """The torso's top ring (his neck's top) as build_head sets it from NECK_RINGS[0]: 16 points round."""
    out = []
    for k in range(TORSO_N):
        kk = k if k <= 8 else TORSO_N - k
        x, y, row = NECK_RINGS[0][kk]
        out.append((x if k <= 8 else -x, y, float(body_z(row))))
    return np.array(out, float)


NECK_LIFT = 0.014      # the head's open edge stands this far above the neck's ring (one row of faces between them)


def snap_neck(Hm, ring):
    """The head's open edge laid on the neck's ring (raised NECK_LIFT), each point at its own angle round it; the
    faces near it eased after it."""
    P = np.array(Hm.P)
    loop = Hm.tag["loop"]
    c = ring[:, :2].mean(0)
    ang_r = np.unwrap(np.arctan2(ring[:, 0] - c[0], -(ring[:, 1] - c[1])))
    for v in loop:
        a = math.atan2(P[v, 0] - c[0], -(P[v, 1] - c[1]))
        # the ring as a closed polyline: find the segment the ray at angle a crosses
        best = None
        for k in range(len(ring)):
            p0, p1 = ring[k], ring[(k + 1) % len(ring)]
            for t in np.linspace(0, 1, 21):
                q = p0 + (p1 - p0) * t
                aq = math.atan2(q[0] - c[0], -(q[1] - c[1]))
                d = abs(math.atan2(math.sin(aq - a), math.cos(aq - a)))
                if best is None or d < best[0]:
                    best = (d, q)
        P[v] = best[1] + np.array((0.0, 0.0, NECK_LIFT))
    Hm.P = [p for p in P]
    # ease the three rows of faces above it (their points drawn toward the average of their neighbours)
    E = edges_of(Hm.faces)
    near = np.zeros(len(P), bool)
    near[loop] = True
    for _ in range(3):
        nb = near.copy()
        nb[E[near[E[:, 0]], 1]] = True
        nb[E[near[E[:, 1]], 0]] = True
        near = nb
    frozen = ~near
    frozen[loop] = True
    for _ in range(6):
        relax_full(Hm, frozen, 0.5)


def relax_full(Hm, frozen, amount):
    """Each free point moved toward its neighbours' average (in every direction: smooths, unlike relax)."""
    P = np.array(Hm.P)
    E = edges_of(Hm.faces)
    acc = np.zeros_like(P)
    deg = np.zeros(len(P))
    np.add.at(acc, E[:, 0], P[E[:, 1]])
    np.add.at(acc, E[:, 1], P[E[:, 0]])
    np.add.at(deg, E[:, 0], 1)
    np.add.at(deg, E[:, 1], 1)
    avg = acc / np.maximum(deg, 1)[:, None]
    d = (avg - P) * amount
    d[frozen | (deg == 0)] = 0.0
    Hm.P = [p for p in P + d]


def nose_width(Hm, sh, mir):
    """The nose's width in the front view brought to the sheet's (BARE_NOSE_W; it is inside the outline, so the
    outline fitting cannot reach it): the nose's points (ahead of his cheeks between its rows) spread across, by row."""
    P = np.array(Hm.P)
    row = bare_row(P[:, 2])
    lo, hi = BARE_NOSE[0] - 10, BARE_NOSE[1] + 6
    face_y = -0.150
    nose = (row > lo) & (row < hi) & (P[:, 1] < face_y) & (np.abs(P[:, 0]) < 0.07)
    rows = np.array([r for r, _ in BARE_NOSE_W], float)
    want = np.array([w for _, w in BARE_NOSE_W], float) / 2.0 * BS
    for _ in range(3):
        P = np.array(Hm.P)
        for r0 in range(lo, hi, 8):
            band = nose & (row >= r0 - 6) & (row < r0 + 6)
            if band.sum() < 2:
                continue
            have = float(np.abs(P[band, 0]).max())
            target = float(np.interp(r0, rows, want))
            if have < 1e-4:
                continue
            k = np.clip(target / have, 0.7, 1.6)
            # (more toward the front of the nose: its root on the face stays)
            depth = np.clip((face_y - P[band, 1]) / 0.03, 0.0, 1.0)
            P[band, 0] *= 1.0 + (k - 1.0) * 0.5 * depth
        Hm.P = [p for p in mirror_even(P, mir)]
    print("CAPTAIN nose width: %d points" % int(nose.sum()))


NOSE_BACK = -0.160      # where the nose's ball meets his cheeks (y)


def nose_round(Hm, sh, mir):
    """The nose made a ball: each row's points laid round a half-ellipse as wide as the front view paints it and as
    deep as the side view's outline reaches there (the cage's nose is a wedge: square in section, flat in front)."""
    P = np.array(Hm.P)
    row = bare_row(P[:, 2])
    rows = np.array([r for r, _ in BARE_NOSE_W], float)
    want = np.array([w for _, w in BARE_NOSE_W], float) / 2.0 * BS
    # (the nose's points: ahead of the cheeks and within its own painted width and a little more, so the puffy cheeks
    # under the eyes, as far forward, are not taken for it)
    reach = (np.interp(row, rows, want) + 25 * BS)
    nose = (row > BARE_NOSE[0] - 4) & (row < BARE_NOSE[1] + 4) & (P[:, 1] < NOSE_BACK) & (np.abs(P[:, 0]) < reach)
    moved = 0
    for i in np.where(nose)[0]:
        r = float(row[i])
        band = nose & (np.abs(row - r) < 7)
        xm = max(float(np.abs(P[band, 0]).max()), 1e-4)
        ymin = float(P[band, 1].min())
        e = bare_edges(sh, "side", int(round(min(max(r, BARE_NOSE[0]), BARE_NOSE[1]))))
        y_front = (e[0] - BARE_MID["side"]) * BS
        hw = float(np.interp(r, rows, want))
        xn = P[i, 0] / xm
        yn = (NOSE_BACK - P[i, 1]) / max(NOSE_BACK - ymin, 1e-4)
        rho = min(math.hypot(xn, yn), 1.0)
        th = math.atan2(xn, yn)
        q = np.array((hw * math.sin(th) * rho, NOSE_BACK - (NOSE_BACK - y_front) * math.cos(th) * rho))
        # (fading out toward the face, so the ball's root joins the cheeks smoothly)
        t = float(smooth01(0.0, 0.35, yn))
        P[i, :2] = P[i, :2] * (1 - 0.85 * t) + q * 0.85 * t
        moved += 1
    Hm.P = [p for p in mirror_even(P, mir)]
    frozen = ~nose
    for _ in range(2):
        relax_full(Hm, frozen, 0.3)
    print("CAPTAIN nose rounded: %d points" % moved)


# Seventeenth round (the third critic: "a long, straight, narrow wedge with a drooping beak tip ... a big round bulb (a
# ball about the size of the mouth's width) with flared round nostril wings and visible nostrils from below"): the
# nose's front end laid round a ball (its radius, how far its middle sits behind the tip, its height on the bare sheet),
# the bridge shortened by drawing the ball's top back toward the face, and two nostrils pressed into its underside.
NOSE_BULB = (0.035, 0.031, 646.0)   # (nineteenth round: was 3.0 cm and row 640; the sheet's ball is about 7 cm across, its tip lower)
NOSE_GROW = (1.26, 1.04, 1.08)   # (twentieth round: 1.28, 1.18, 1.12; the fifth critic: "projects too far and droops below the nostril line"; the side outline's tip still sits on the sheet's within a centimetre, so only the ball's forward swell and its hang are taken back)     # the nose grown about the ball's middle: across, forward, up
NOSE_LIFT = 0.004    # (twentieth round: the tip lifted, metres; was 3 mm lowered)
NOSE_RGB = (0.89, 0.53, 0.46)   # (twentieth round) the nose's coral, as the sheet's (about #E58A7A, a little deeper for the lit render)
NOSTRILS = (0.015, 0.008, 0.011)   # (twentieth round: 5 mm deep, 1 cm wide)   # (out from the middle, metres in, radius)
if "nose" in REVERT or "all" in REVERT:
    NOSE_GROW, NOSE_LIFT = (1.28, 1.18, 1.12), -0.003


def nose_bulb(Hm, mir):
    P = np.array(Hm.P)
    row = bare_row(P[:, 2])
    R, back, brow_ = NOSE_BULB
    zc = float(bare_z(brow_))
    near_mid = (np.abs(P[:, 0]) < 0.02) & (np.abs(P[:, 2] - zc) < 0.03)
    tip_y = float(P[near_mid, 1].min())
    c = np.array((0.0, tip_y + back, zc))
    d = P - c
    r = np.linalg.norm(d, axis=1)
    # (the nose's own points: in front of the cheeks, near the ball)
    w = np.clip((1.7 * R - r) / (0.7 * R), 0.0, 1.0) * np.clip((NOSE_BACK + 0.012 - P[:, 1]) / 0.02, 0.0, 1.0)
    w *= (row > 560) & (row < 700)
    unit = d / np.maximum(r, 1e-9)[:, None]
    want = c + unit * R
    # (only outward toward the ball's surface where it lies inside it, inward where it stands out past it; the back half
    # facing the face is left)
    front = np.clip((-unit[:, 1] + 0.2) / 0.5, 0.0, 1.0)
    k = (w * front)[:, None]
    P = P * (1 - k) + want * k
    # nostrils: pressed up into the ball's underside either side of the middle
    N = normals_of(P, Hm.tris())
    for s_ in (1.0, -1.0):
        nc = c + np.array((s_ * NOSTRILS[0], -0.004, -R * 0.82))
        g = np.exp(-np.sum((P - nc) ** 2, 1) / NOSTRILS[2] ** 2) * np.clip(-N[:, 2], 0, 1)
        P[:, 2] += NOSTRILS[1] * g
    # (nineteenth round, the fourth critic: "in grey the nose is a small, narrow knob; the red paint is painted larger
    # than the form": the whole nose, wings with it, grown about the ball's middle, most at the ball and fading out by
    # 1.9 of its radius, so it fills the sheet's red ball, the tip a little lower)
    d = P - c
    r = np.linalg.norm(d * np.array((1.0, 0.6, 1.0)), axis=1)
    g = np.clip((1.9 * R - r) / (0.9 * R), 0.0, 1.0) * (P[:, 1] < NOSE_BACK + 0.01)
    P = P + d * (np.array(NOSE_GROW) - 1.0)[None, :] * g[:, None]
    P[:, 2] += NOSE_LIFT * g * np.clip(-d[:, 1] / R, 0, 1)
    Hm.P = [p for p in mirror_even(P, mir)]
    print("CAPTAIN nose bulb: %d points onto a ball of %.1f cm radius" % (int((k[:, 0] > 0.05).sum()), R * 100))


# The face's forms the outline cannot carry, carved along lines in the bare sheet's front view (px out from the
# middle, row), both sides alike: (points, metres along the normal (negative in), width px). Read off the sheet: the deep
# folds from the nose's wings round the mouth's corners, the slit eyes under puffy lids with bags below, the frown's
# creases between the brows, the down-turned mouth's line over a full lower lip, the groove over the chin, the folds
# hanging from the mouth's corners into the jowls.
HEAD_CARVES = (
    (((78, 652), (96, 700), (114, 748), (126, 800)), -0.008, 12),
    (((120, 575), (150, 615), (162, 660)), 0.008, 26),            # the cheeks' fullness outside the folds
    (((112, 770), (130, 830), (140, 880)), 0.008, 20),            # the jowls hanging outside the mouth's folds
    (((46, 527), (100, 523), (142, 530)), -0.004, 7),             # the eye's slit
    (((50, 511), (100, 506), (140, 514)), 0.005, 9),              # the puffy upper lid
    (((56, 546), (100, 552), (140, 548)), 0.006, 10),             # the bag under it
    (((14, 468), (16, 500)), -0.006, 7),
    (((26, 474), (28, 502)), -0.004, 6),                          # the frown's crease
    (((0, 730), (60, 736), (116, 754)), -0.006, 7),               # the mouth's line (nineteenth round: on the sheet's line, 730 in the middle, the corners 24 px lower)
    (((0, 754), (50, 760), (86, 766)), 0.005, 12),                           # the full lower lip, pouting
    (((0, 784), (50, 782)), -0.004, 10),                          # the groove over the chin
    (((0, 830), (40, 826), (70, 830)), 0.006, 26),                           # the ball of the chin (nineteenth round)
    (((120, 765), (128, 820), (134, 870)), -0.004, 12),           # the folds into the jowls
    # (sixteenth round, the critic: "a heavy, overhanging brow shelf that knots down over the nose ... lids that are
    # folded creases following the curve of the eyeball"; the user: "his eyes should just be wrinkly slits")
    (((24, 504), (70, 490), (120, 484), (156, 490)), 0.010, 11),  # the brow's shelf over each eye
    (((30, 508), (80, 512), (130, 516)), -0.004, 6),              # the fold under the shelf, over the lid
    (((52, 532), (100, 536), (140, 546)), -0.003, 6),             # the slit's outer end lower, along the eyeball
    (((150, 520), (172, 512)), -0.003, 5),                        # crow's feet: the deepest fold at the eye's corner
    (((150, 536), (174, 540)), -0.003, 5),
)
_OLD_CARVES = {"jowl": (2, (((112, 770), (130, 830), (140, 880)), 0.006, 20)),
               "lid": (4, (((50, 511), (100, 506), (140, 514)), 0.003, 9)),
               "lip": (9, (((0, 752), (50, 758)), 0.004, 10)),
               "chin": (11, (((0, 830), (40, 826)), 0.004, 22)),
               "brow": (14, (((24, 492), (70, 484), (120, 488), (156, 500)), 0.009, 11))}
if REVERT:
    HEAD_CARVES = list(HEAD_CARVES)
    for _k, (_i, _v) in _OLD_CARVES.items():
        if _k in REVERT or "all" in REVERT:
            HEAD_CARVES[_i] = _v
    HEAD_CARVES = tuple(HEAD_CARVES)


def carve_face(Hm):
    P = np.array(Hm.P)
    N = normals_of(P, Hm.tris())
    col = np.abs(P[:, 0]) / BS
    row = bare_row(P[:, 2])
    facing = np.clip((-N[:, 1] - 0.15) / 0.4, 0.0, 1.0)
    d = np.zeros(len(P))
    for pts, depth, width in HEAD_CARVES:
        best = np.full(len(P), np.inf)
        for (c0, r0), (c1, r1) in zip(pts, pts[1:]):
            a = np.array((c0, r0), float)
            b = np.array((c1, r1), float)
            ab = b - a
            t = np.clip(((col - a[0]) * ab[0] + (row - a[1]) * ab[1]) / max(ab @ ab, 1e-9), 0, 1)
            dist = np.hypot(col - (a[0] + ab[0] * t), row - (a[1] + ab[1] * t))
            best = np.minimum(best, dist)
        d += depth * np.exp(-(best / width) ** 2)
    d = np.clip(d, -0.008, 0.011)
    P += N * (d * facing)[:, None]
    Hm.P = [p for p in P]
    print("CAPTAIN face carved: most %.1f mm" % (1000 * float(np.abs(d * facing).max())))


def finish_base_head(Hm, face_uv, sh):
    """The head's outline fitted to the bare sheet's front, side and back views, the face and ears split once,
    fitted again, the landmarks pinned."""
    mir = Hm.tag["mir"]
    marks = Hm.tag["marks"]
    loop = Hm.tag["loop"]
    frozen = np.zeros(len(Hm.P), bool)
    frozen[loop] = True
    snap_neck(Hm, neck_ring_points())
    Hm.P = [p for p in mirror_even(Hm.P, mir)]
    print("CAPTAIN base head: its open edge laid on the neck; folds %s" % (folds(Hm.P, Hm.faces),))
    head_fit_stage(Hm, sh, frozen, 4, 28, mir)
    repin(Hm, marks, frozen, 0.7)
    # the face's front, the jaw and the ears split once (the dome under his cap and the back of his head kept coarse)
    P = np.array(Hm.P)
    cy = float(np.median(P[:, 1]))
    sel = set()
    for fi, f in enumerate(Hm.faces):
        c = P[f].mean(0)
        row = float(bare_row(c[2]))
        # (sixteenth round: the back of the head too, from the occiput to the neck: between row 580 and the open edge at
        # 780 it had no point down his middle at all, one slope of big faces that no nape could be drawn into)
        if (row > 430 and c[1] < cy + 0.01) or (abs(c[0]) > 0.11 and 460 < row < 670) or (DOME_SPLIT and row < DOME_SPLIT) \
                or (NAPE_SPLIT and c[1] > cy + 0.02 and row >= DOME_SPLIT):
            sel.add(fi)
    weights = [{} for _ in Hm.P]
    H2, uv2, _, _ = refine(Hm, sel, face_uv, weights)
    H2.tag = dict(Hm.tag)
    mir2 = mirror_pairs(H2.P, 2e-3)
    H2.tag["mir"] = mir2
    # (the open edge again: splitting put new points on it)
    loop = max(loops_of(H2.faces), key=len)
    H2.tag["loop"] = loop
    frozen2 = np.zeros(len(H2.P), bool)
    frozen2[loop] = True
    print("CAPTAIN base head split: %d faces, %d triangles; %d points unpaired" % (len(sel), len(H2.tris()), int(((mir2 == np.arange(len(mir2))) & (np.abs(np.array(H2.P)[:, 0]) > 1e-4)).sum())))
    head_fit_stage(H2, sh, frozen2, 4, 16, mir2)
    repin(H2, marks, frozen2, 1.0)
    nose_width(H2, sh, mir2)
    nose_round(H2, sh, mir2)
    nose_bulb(H2, mir2)
    carve_face(H2)
    jowls_and_chin(H2)
    # (the eyes' lids eased: pinched into slits, a quad there folded over and showed as a hole)
    P = np.array(H2.P)
    rw = bare_row(P[:, 2])
    eyes = (rw > 495) & (rw < 560) & (np.abs(P[:, 0]) > 0.015) & (np.abs(P[:, 0]) < 0.085) & (P[:, 1] < -0.12)
    for _ in range(3):
        relax_full(H2, ~eyes, 0.35)
    H2.P = [p for p in mirror_even(H2.P, mir2)]
    tr = H2.tris()
    Pn = np.array(H2.P)
    away = 0
    for a, b, c in tr:
        n = np.cross(Pn[b] - Pn[a], Pn[c] - Pn[a])
        m = (Pn[a] + Pn[b] + Pn[c]) / 3.0
        if 495 < bare_row(m[2]) < 560 and 0.015 < abs(m[0]) < 0.085 and m[1] < -0.12 and n[1] > 0.3 * np.linalg.norm(n):
            away += 1
    print("CAPTAIN eyes eased; triangles there facing backward: %d" % away)
    relax(H2, frozen2, 0.1, 1)
    head_fit_stage(H2, sh, frozen2, 2, 10, mir2)
    H2.P = [p for p in mirror_even(H2.P, mir2)]
    dome_fill(H2, sh, frozen2, mir2)
    occiput(H2, frozen2, mir2)
    ears_out(H2, mir2)
    unfold(H2, frozen2, mir2)
    return H2, uv2


# (twentieth round, the fifth critic: "ears flat against the head". Measured on the bare sheet: the ears are already its
# size (top to lobe 0.31 of the head's height on him, 0.28 on the sheet: the critic's "30% bigger" is overruled), but
# from the front they stand out 11% of the head's width on the sheet, 8% on him: each ear turned out about its front
# edge, its back moved out EAR_FLARE of its depth)
EAR_FLARE = float(arg("--ear-flare", "0.05"))   # (0.16 added 5 folded edges to the face rig's jaw test)   (twentieth round: 0.12)
EAR_SHIFT = float(arg("--ear-shift", "0.007"))   # (twenty-first round) metres the whole ear stands further out
EAR_MOVE = (float(arg("--ear-fwd", "0.014")), float(arg("--ear-down", "0.010")))   # (twenty-first round) metres forward, down
EAR_LONG = float(arg("--ear-long", "1.35"))   # the ear drawn out at its front, about its back edge
if "ears" in REVERT or "all" in REVERT:
    EAR_FLARE = 0.0


def ears_out(Hm, mir):
    P = np.array(Hm.P)
    rw = bare_row(P[:, 2])
    w = np.clip((np.abs(P[:, 0]) - 0.108) / 0.014, 0.0, 1.0) * ((rw > 450) & (rw < 680))
    ear = w > 0
    if ear.sum() < 4:
        return
    y0 = float(P[ear, 1].min())
    # (twenty-first round: the ear also stood out as a whole by EAR_SHIFT, with less of a turn: turned only, its back rim
    # alone was the widest part of the head, so the face rig took the ear, and the jaw's hinge with it, 1 cm high and
    # 1 cm back of the sheet's ear (bare sheet: rows 485 to 645, the middle 2 cm under the eye), and the jaw opened about
    # a hinge too high: its long ramus swung back into the neck, 50 folded faces down the side of the neck)
    P[:, 0] += np.sign(P[:, 0]) * (EAR_SHIFT + EAR_FLARE * np.clip(P[:, 1] - y0, 0.0, None)) * w
    # (and the ear itself, not the jowl before it, moved toward the sheet's ear and drawn out at its front to the sheet's
    # width front to back: the side view's ear spans 4.8 cm, from 3.0 cm before the head's middle to 1.8 behind; the
    # base ear stood 3 cm long, centred on the middle)
    gate = np.clip((P[:, 1] + 0.03) / 0.01, 0.0, 1.0) * w
    if gate.sum() > 4:
        yb = float(P[gate > 0.5, 1].max())
        P[:, 1] += (EAR_LONG - 1.0) * (P[:, 1] - yb) * gate - EAR_MOVE[0] * gate
        P[:, 2] -= EAR_MOVE[1] * gate
    Hm.P = [p for p in mirror_even(P, mir)]
    print("CAPTAIN ears turned out: %d points, the back edge out %.1f cm" % (int(ear.sum()), 100 * EAR_FLARE * float(P[ear, 1].max() - y0)))


DOME_ROWS = (190, 325)       # bare-sheet rows of the skull filled out to the side view's back outline (fourteenth round: only
                             # above the grey fringe, which stands 5 to 11 cm off his skull from row 340 down: that
                             # was the "frame" disagreement of the last round, the hair's outline, not the skull's)
DOME_TAPER = 400             # the back's stretch fades to nothing by this row
DOME_WIDE = True
DOME_WIDE_ROWS = (200, 300, 420)   # front-view rows widened to the sheet (above its side hair), and where it fades out
DOME_SMOOTH = 470            # above this row the dome's facets smoothed (Taubin: keeps its size)
DOME_STRETCH = 1.0
# Fifteenth round (the second critic: "the crown comes to a faceted point"; "no bulge at the back of the skull";
# "a narrow, pointed jaw where the bare sheet has a broad, jowly double chin"):
DOME_SPLIT = 440             # the skull's faces above this bare-sheet row split once too (they were the cage's own, 16 round)
OCCIPUT = (450.0, 85.0, 0.008, 680.0, 65.0, 0.036)   # the back of the skull pushed back (row, spread, metres), the nape
                                                     # under it drawn in (row, spread, metres)
# (sixteenth round: the side view's back outline measured against the bare sheet's: the skull from row 250 to 580 within
# 7 mm of the sheet's (whose outline there is the grey fringe, standing off the skull: the skull is not pushed further
# back than the hair's outline, the sheet wins over the critic's "8% of head depth"); from row 600 down the model went
# straight down and out where the sheet steps in under the skull, 2 cm at row 640, 3.3 cm at 670, 3.5 cm at 700: the
# nape drawn in by that much, a groove under the occiput, rolling back out to the neck's ring)
JOWLS = (865.0, 45.0, 0.009)     # the jowls out along their normals (row, spread, metres) where |x| > 5 cm
CHIN_FILL = (930.0, 990.0, 0.004)  # the underside of the chin and jaw filled out (rows, metres): a double chin
# Sixteenth round: the jaw's mass (jowls_and_chin): metres forward at most, centred this far out (m), spread (m); the
# rows it rises over (r0 to r1) and falls off over (r2 to r3)
JAW_MASS = (0.045, 0.08, 0.022, 760.0, 830.0, 950.0, 990.0)
JOWL_HANG = 0.013             # metres the jowls are lowered over the jaw's line
NAPE_SPLIT = True             # the back of the head's faces below the dome split once (finish_base_head)


def jowls_and_chin(Hm):
    P = np.array(Hm.P)
    N = normals_of(P, Hm.tris())
    row = bare_row(P[:, 2])
    cy = float(np.median(P[:, 1]))
    ax = np.abs(P[:, 0])
    j = JOWLS[2] * np.exp(-((row - JOWLS[0]) / JOWLS[1]) ** 2) * np.clip((ax - 0.04) / 0.03, 0, 1) * (P[:, 1] < cy + 0.02)
    lo, hi, amt = CHIN_FILL
    down = np.clip((-N[:, 2] - 0.2) / 0.4, 0, 1)
    c = amt * down * smooth01(lo - 50, lo, row) * (1.0 - smooth01(hi, hi + 30, row)) * (P[:, 1] < cy) * np.clip((0.11 - ax) / 0.04, 0, 1)
    d = j + c
    loop = Hm.tag.get("loop", [])
    d[loop] = 0.0
    P += N * d[:, None]
    # Sixteenth round (the user: "Seems like hes missing a chin/jaw/neck", "why is his jaw just straight flat across?";
    # the critic: "a narrow, pointed jaw where the bare sheet has a broad, jowly double chin"). The front and side
    # outlines already sat on the sheet's; what was wrong is the jaw's cross-section: measured at rows 860 to 940 its
    # front fell back 8 cm between 5 and 8 cm out from his middle (a V, a pointed chin from below), where the sheet's
    # three-quarter and from-below views draw a broad squared U whose front stays within 2 to 4 cm of the chin's out to
    # the jowls. So the lower face's front is carried forward (pure -y: neither outline moves) by a band peaking 8 cm
    # out, never past a curve just behind the chin's own front, and the jowls hung over the jaw's line (down).
    if JAW_MASS:
        amt, cx, sx, r0, r1, r2, r3 = JAW_MASS
        ay = np.abs(P[:, 0])
        row = bare_row(P[:, 2])
        wr = smooth01(r0, r1, row) * (1.0 - smooth01(r2, r3, row))
        wf = np.clip((-P[:, 1] - 0.025) / 0.04, 0.0, 1.0)
        dy = amt * np.exp(-((ay - cx) / sx) ** 2) * wr * wf
        # the chin's front, row by row (its middle's foremost point), and the curve the jaw may not pass
        chin = np.full(len(P), -np.inf)
        mid_ = ay < 0.018
        for r in range(int(r0) - 20, int(r3) + 20, 10):
            band = mid_ & (np.abs(row - r) < 12)
            if band.any():
                sel_ = np.abs(row - r) < 5
                chin[sel_] = float(P[band, 1].min())
        limit = chin + 0.006 + 0.32 * np.clip(ay - 0.035, 0, None) + 1.4 * np.clip(ay - 0.07, 0, None) ** 2
        newy = np.where(np.isfinite(chin), np.maximum(P[:, 1] - dy, np.minimum(limit, P[:, 1])), P[:, 1])
        newy[loop] = P[loop, 1]
        moved = P[:, 1] - newy
        P[:, 1] = newy
        # the jowls hang: the jaw's outer front, between the mouth's corner and the jaw's angle, lowered a little
        hang = JOWL_HANG * np.exp(-((ay - 0.075) / 0.025) ** 2) * np.exp(-((row - 900.0) / 40.0) ** 2) * wf
        hang[loop] = 0.0
        P[:, 2] -= hang
        print("CAPTAIN jaw's mass forward: most %.1f cm (%d points over 5 mm); jowls hung %.1f mm"
              % (100 * float(moved.max()), int((moved > 0.005).sum()), 1000 * float(hang.max())))
        Hm.P = [p for p in mirror_even(P, Hm.tag["mir"])]
        # (the moved band smoothed into its neighbours so no step shows at its edges)
        sel = np.zeros(len(P), bool)
        sel[moved > 0.001] = True
        E = edges_of(Hm.faces)
        for _ in range(2):
            nb = sel.copy()
            nb[E[sel[E[:, 0]], 1]] = True
            nb[E[sel[E[:, 1]], 0]] = True
            sel = nb
        sel[loop] = False
        for _ in range(3):
            relax_full(Hm, ~sel, 0.3)
        P = np.array(Hm.P)
    Hm.P = [p for p in mirror_even(P, Hm.tag["mir"])]
    print("CAPTAIN jowls out %.1f mm, chin's underside out %.1f mm" % (1000 * float(j.max()), 1000 * float(c.max())))


def occiput(Hm, frozen, mir):
    P = np.array(Hm.P)
    row = bare_row(P[:, 2])
    cy = float(np.median(P[:, 1]))
    ymax = float(P[:, 1].max())
    share = np.clip((P[:, 1] - cy) / max(ymax - cy, 1e-6), 0.0, 1.0) ** 1.5
    r0, s0, a0, r1, s1, a1 = OCCIPUT
    dy = a0 * np.exp(-((row - r0) / s0) ** 2) - a1 * np.exp(-((row - r1) / s1) ** 2)
    dy = dy * share
    dy[frozen] = 0.0
    P[:, 1] += dy
    # (and the dome smoothed once more: the new rows of the split skull rounded off)
    sel = (row < DOME_SMOOTH) & ~frozen
    E = edges_of(Hm.faces)
    deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
    for _ in range(4):
        for lam in (0.5, -0.53):
            acc = np.zeros_like(P)
            np.add.at(acc, E[:, 0], P[E[:, 1]])
            np.add.at(acc, E[:, 1], P[E[:, 0]])
            avg = acc / np.maximum(deg, 1)[:, None]
            P[sel] += lam * (avg[sel] - P[sel])
    Hm.P = [p for p in mirror_even(P, mir)]
    print("CAPTAIN occiput out %.1f mm, nape in %.1f mm" % (1000 * float(dy.max()), -1000 * float(dy.min())))


def dome_fill(Hm, sh, frozen, mir):
    """Thirteenth round (the back of his skull stood about 3 cm short at the top-back in the side view, and the dome
    showed flat facets): row by row, the back half of the head stretched back until its back-most point stands on the
    side view's back outline (the stretch growing from nothing at the head's middle to all of it at the back); then
    the dome's points smoothed."""
    P = np.array(Hm.P)
    c0, c1 = BARE_SPAN["side"]
    P2, _ = project("bare_side", P)
    back_w = world_dir("bare_side", np.array([[1.0, 0.0]]))[0]
    s_ = 1.0 if float(back_w @ np.array((0.0, 1.0, 0.0))) > 0 else -1.0
    back_w = back_w * s_
    yc = float(np.median(P[:, 1]))
    moved = []
    for r in range(DOME_ROWS[0], DOME_ROWS[1], 10):
        band = (np.abs(P2[:, 1] - r) < 8) & (P[:, 1] > yc)
        if band.sum() < 3:
            continue
        run = run_near(sh.bare_mask, r, BARE_MID["side"], c0, c1)
        if not run:
            continue
        want = float(run[1] + 1 if s_ > 0 else run[0])
        have = float(P2[band, 0].max() if s_ > 0 else P2[band, 0].min())
        moved.append((r, (want - have) * s_))
    if not moved:
        return
    rr = np.array([m[0] for m in moved], float)
    dd = np.clip(np.array([m[1] for m in moved], float), -10.0, 45.0)
    rr, dd = np.append(rr, DOME_TAPER), np.append(dd, 0.0)
    d_px = np.interp(P2[:, 1], rr, dd, left=0.0, right=0.0)
    ymax = float(P[:, 1].max())
    share = np.clip((P[:, 1] - yc) / max(ymax - yc, 1e-6), 0.0, 1.0) ** 1.3
    share[frozen] = 0.0
    P += np.outer(d_px * share * BS * DOME_STRETCH, back_w)
    # (fourteenth round, the critic: "widen the upper cranium about 10% at the temples and above the ears": the front
    # view's outline above its side hair (rows to DOME_WIDE_ROWS[1]), each row's half width brought to the sheet's,
    # the move fading out down to DOME_WIDE_ROWS[2])
    if DOME_WIDE:
        f0, f1 = BARE_SPAN["front"]
        P2f, _ = project("bare_front", P)
        mid = BARE_MID["front"]
        wide = []
        for r in range(DOME_WIDE_ROWS[0], DOME_WIDE_ROWS[1] + 1, 10):
            band = np.abs(P2f[:, 1] - r) < 8
            if band.sum() < 3:
                continue
            run = run_near(sh.bare_mask, r, mid, f0, f1)
            if not run:
                continue
            want = (run[1] + 1 - run[0]) / 2.0
            have = float(np.abs(P2f[band, 0] - mid).max())
            wide.append((r, float(np.clip(want / max(have, 1.0), 0.9, 1.12))))
        if wide:
            rr2 = np.array([w_[0] for w_ in wide] + [DOME_WIDE_ROWS[2]], float)
            kk2 = np.array([w_[1] for w_ in wide] + [1.0], float)
            k_ = np.interp(P2f[:, 1], rr2, kk2, left=kk2[0], right=1.0)
            xm = float(np.abs(P[:, 0]).max())
            sh_ = np.clip(np.abs(P[:, 0]) / max(xm, 1e-6), 0, 1) ** 0.7
            sh_[frozen] = 0.0
            P[:, 0] *= 1.0 + (k_ - 1.0) * sh_
            print("CAPTAIN dome widened (row, times): %s" % [(int(r), round(k, 3)) for r, k in wide])
    # the dome smoothed (Taubin's two steps)
    rw = bare_row(P[:, 2])
    sel = (rw < DOME_SMOOTH) & ~frozen
    E = edges_of(Hm.faces)
    for _ in range(4):
        for lam in (0.5, -0.53):
            acc = np.zeros_like(P)
            np.add.at(acc, E[:, 0], P[E[:, 1]])
            np.add.at(acc, E[:, 1], P[E[:, 0]])
            deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
            avg = acc / np.maximum(deg, 1)[:, None]
            P[sel] += lam * (avg[sel] - P[sel])
    Hm.P = [p for p in mirror_even(P, mir)]
    print("CAPTAIN dome filled: back outline gaps (row, px) %s" % [(int(r), round(float(d), 1)) for r, d in moved])


def unfold(Hm, frozen, mir, rounds=12):
    """Folded places eased away: the points of neighbouring faces folded sharper than 120 degrees, and of faces on his
    face's front turned to face backward, drawn toward their neighbours, until none are left (the lips' meeting line
    and the ears' rims are folds by design: left alone)."""
    for it in range(rounds):
        P = np.array(Hm.P)
        F = Hm.faces
        n = np.array([face_normal(P, f) for f in F])
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        bad = set()
        by = {}
        for fi, f in enumerate(F):
            for k in range(len(f)):
                e = (min(f[k], f[(k + 1) % len(f)]), max(f[k], f[(k + 1) % len(f)]))
                by.setdefault(e, []).append(fi)
        for e, fs in by.items():
            if len(fs) == 2 and np.dot(n[fs[0]], n[fs[1]]) < -0.5:
                bad.update(e)
        for fi, f in enumerate(F):
            m = P[f].mean(0)
            if m[1] < -0.12 and 440 < bare_row(m[2]) < 900 and n[fi, 1] > 0.3:
                bad.update(f)
        row = bare_row(P[:, 2])
        lips = (row > 735) & (row < 762) & (np.abs(P[:, 0]) < 0.07)
        ears = (np.abs(P[:, 0]) > 0.105) & (row > 460) & (row < 670)
        sel = np.zeros(len(P), bool)
        sel[list(bad)] = True
        sel &= ~lips & ~ears & ~frozen
        if not sel.any():
            break
        relax_full(Hm, ~sel, 0.45)
        Hm.P = [p for p in mirror_even(Hm.P, mir)]
    print("CAPTAIN unfolded in %d rounds; folds left %s" % (it + 1, folds(Hm.P, Hm.faces)))


def transplant_head(M, T, face_uv, weights, under, sh):
    """The lofted head (head, nose, ears, the neck's faces) taken off his body and the fitted base head put on, its open
    edge bridged to the torso's top ring by a zipper of triangles. The old head's points stay in the list (unused; the
    cap's fitting and the --hair locks still read them) so every other index and tag holds. Gives the new Mesh, UVs,
    weights and the faces under the boxers renumbered."""
    Hm, huv = build_base_head(sh, M, T)
    Hm, huv = finish_base_head(Hm, huv, sh)
    old = {fi for fi, p in enumerate(M.fpart) if part_family(p) in ("head", "nose", "ear", "neck")}
    R = Mesh()
    R.P = [np.array(p, float) for p in M.P]
    R.part = list(M.part)
    R.tag = M.tag
    W = list(weights)
    new_uv, fmap = {}, {}
    for fi, f in enumerate(M.faces):
        if fi in old:
            continue
        fmap[fi] = len(R.faces)
        R.faces.append(list(f))
        R.fpart.append(M.fpart[fi])
        if fi in M.cell:
            R.cell[fmap[fi]] = M.cell[fi]
        if fi in face_uv:
            new_uv[fmap[fi]] = face_uv[fi]
    base = len(R.P)
    Ph = np.array(Hm.P)
    for p in Ph:
        R.add(p, "head")
    vuv = {}
    vuvs = {}       # (fourteenth round: every UV a point has; on the islands' seams it has two)
    for k, f in enumerate(Hm.faces):
        R.face([v + base for v in f], "head")
        new_uv[len(R.faces) - 1] = huv[k]
        for v, q in zip(f, huv[k][1]):
            vuv.setdefault(v, q)
            vuvs.setdefault(v, [])
            if not any(np.allclose(q, o, atol=1e-5) for o in vuvs[v]):
                vuvs[v].append(tuple(q))
    loop = [v + base for v in Hm.tag["loop"]]
    # (the body's open edge at the neck: the torso's top ring with the points the face's splitting put on it)
    ring = next(l for l in loops_of([f for f, p in zip(R.faces, R.fpart) if part_family(p) != "peak"]) if T[-1][0] in l)
    n0 = len(R.faces)
    bridge_uneven(R, loop, ring, "neck", np.array((0.0, 0.0, 1.0)))
    # (the zipper's UVs: the head's own on its edge; each ring point's carried on past the edge, as far again as the
    # ring lies below it, from the head's point above, so the zipper has real texels, painted like the rest)
    Eh = edges_of(Hm.faces)
    lset = set(Hm.tag["loop"])
    up = {}
    for a, b in Eh:
        for x, y in ((a, b), (b, a)):
            if x in lset and y not in lset and (x not in up or Ph[y, 2] > Ph[up[x], 2]):
                up[x] = y
    ring_uv = {}
    for v in ring:
        j = Hm.tag["loop"][int(np.argmin(np.linalg.norm(Ph[Hm.tag["loop"]] - R.P[v], axis=1)))]
        q = np.array(vuv[j])
        if j in up:
            k = up[j]
            s = float(np.linalg.norm(R.P[v] - Ph[j])) / max(float(np.linalg.norm(Ph[j] - Ph[k])), 1e-6)
            q = q + (q - np.array(vuv[k])) * min(s, 1.5)
        ring_uv[v] = tuple(np.clip(q, 0.002, 0.998))
    # (fourteenth round: a point on the head's island seam has two UVs, and the zipper's faces there took one from
    # each island: long slivers across the face's picture, painted with whatever lay between. Each zipper face now
    # takes every UV from the one island of its first head point)
    def near_uv(v, ref):
        c = vuvs.get(v, [vuv[v]])
        return np.array(min(c, key=lambda q: (q[0] - ref[0]) ** 2 + (q[1] - ref[1]) ** 2))

    def ring_uv_near(v, ref):
        j = Hm.tag["loop"][int(np.argmin(np.linalg.norm(Ph[Hm.tag["loop"]] - R.P[v], axis=1)))]
        q = near_uv(j, ref)
        if j in up:
            k = up[j]
            s = float(np.linalg.norm(R.P[v] - Ph[j])) / max(float(np.linalg.norm(Ph[j] - Ph[k])), 1e-6)
            q = q + (q - near_uv(k, q)) * min(s, 1.5)
        return tuple(np.clip(q, 0.002, 0.998))
    fixed = 0
    for fi in range(n0, len(R.faces)):
        f = R.faces[fi]
        uvs = [vuv[v - base] if v >= base else ring_uv[v] for v in f]
        if np.ptp(np.array(uvs), axis=0).max() > 0.06:
            hv = [v for v in f if v >= base]
            ref = vuv[hv[0] - base] if hv else uvs[0]
            uvs = [tuple(near_uv(v - base, ref)) if v >= base else ring_uv_near(v, ref) for v in f]
            fixed += 1
            if np.ptp(np.array(uvs), axis=0).max() > 0.06:
                # (sixteenth round, "the thin seam line on the crown" and on the back of the head: a few zipper faces
                # still spanned the picture as long slivers, and the texels under them, inside the back of the head's
                # island, were painted as the neck: light lines across it. Those faces take the UV of the head's
                # point nearest each corner, unextended: a sliver no wider than the head's edge)
                uvs = []
                for v in f:
                    if v >= base:
                        uvs.append(tuple(near_uv(v - base, ref)))
                    else:
                        j = Hm.tag["loop"][int(np.argmin(np.linalg.norm(Ph[Hm.tag["loop"]] - R.P[v], axis=1)))]
                        uvs.append(tuple(near_uv(j, ref)))
                print("CAPTAIN zipper face %d still a sliver across the picture: its UVs drawn to the head's edge" % fi)
        new_uv[fi] = ("face", uvs)
    print("CAPTAIN zipper faces given one island's UVs: %d" % fixed)
    # weights: the head's bone, shared with the neck's over the rows next to the open edge
    E = edges_of(Hm.faces)
    step = np.full(len(Ph), 99)
    step[Hm.tag["loop"]] = 0
    for s in range(1, 4):
        a = step[E[:, 0]] == s - 1
        b = step[E[:, 1]] == s - 1
        step[E[a, 1]] = np.minimum(step[E[a, 1]], s)
        step[E[b, 0]] = np.minimum(step[E[b, 0]], s)
    # (seventeenth round, the user: "stop his chin and jaw phasing into his neck": the under-jaw rows fully the head's,
    # only the open edge itself (the throat) shared, mostly the neck's)
    share = {0: 0.4, 1: 0.92, 2: 1.0}
    for s in step:
        t = share.get(int(s), 1.0)
        W.append({"head": t, "neck": 1.0 - t} if t < 1.0 else {"head": 1.0})
    # the ears' points named, for the landmarks and the earring
    mir = Hm.tag["mir"]
    R.tag["earlobe_l"] = [base + BH_EAR_LOBE]
    R.tag["earlobe_r"] = [base + int(mir[BH_EAR_LOBE])]
    R.tag["base_head"] = (base, len(Ph))
    R.tag["base_marks"] = {k: base + k for k in (284, 288, 291, 52, int(mir[52]), BH_EAR_TOP, BH_EAR_LOBE, int(mir[BH_EAR_LOBE]))}
    R.tag["base_throat"] = loop[int(np.argmin(Ph[Hm.tag["loop"], 2] + 10 * np.abs(Ph[Hm.tag["loop"], 0])))]
    flipped = fix_winding(R)
    oe = open_edges([f for f, p in zip(R.faces, R.fpart) if part_family(p) != "peak"])
    if oe:
        print("CAPTAIN open edges after the transplant: %s" % [(a, b, "head" if a >= base else R.part[a], np.round(R.P[a], 3).tolist()) for a, b in oe[:8]])
    under2 = {fmap[fi] for fi in under if fi in fmap}
    print("CAPTAIN head transplanted: %d old faces off, %d new (%d triangles with the neck's zipper), %d turned outward; "
          "open edges of the body %d" % (len(old), len(Hm.faces), len(Hm.tris()) + len(R.faces) - n0, flipped,
                                         len(open_edges([f for f, p in zip(R.faces, R.fpart) if part_family(p) not in ("peak",)]))))
    return R, new_uv, W, under2


CAP_DROP = (0.016, 0.008)     # metres the band's bottom ring and the next are lowered at the back (none at the front)
CAP_SNUG = 0.004               # metres the band's bottom stands off his head


def cap_clear(Cm, R):
    """The cap's outside kept clear of the new head (it was fitted to the lofted one): every point of its rings pushed
    out along the way from the head's middle at its height until it stands 6 mm off the head's surface there."""
    b0, n = R.tag["base_head"]
    H = np.array(R.P[b0:b0 + n])
    P = np.array(Cm.P, float)
    # (thirteenth round: the band's bottom edge cut straight across his head; a cap sits lower at the back and the
    # sides than over the brow: the band's two bottom rings dropped by angle round the head, none at the front)
    rings_ = Cm.tag["rings"]
    zs = [float(np.mean([P[v][2] for v in r])) for r in rings_]
    order = np.argsort(zs)
    cen = np.mean([P[v] for v in rings_[order[0]]], axis=0)
    for k, drop in zip(order[:2], CAP_DROP):
        for v in rings_[k]:
            th = math.atan2(P[v][0] - cen[0], -(P[v][1] - cen[1]))
            P[v][2] -= drop * (1.0 - math.cos(th)) / 2.0
    pushed = 0
    # (seventeenth round, the third critic: "a large dark gap between the inner band and the scalp ... lower the cap so
    # the band touches the skull all the way round": the band's bottom ring is drawn IN as well as out, to
    # CAP_SNUG off the head (both bottom rings folded the band); the rings above are only pushed out)
    snug = set(v for k in order[:1] for v in rings_[k])
    for ring in Cm.tag["rings"]:
        for v in ring:
            z = float(P[v][2])
            near = np.abs(H[:, 2] - z) < 0.008
            if near.sum() < 6:
                continue
            s = H[near, :2]
            sc = s.mean(0)
            d = P[v][:2] - sc
            r_ = float(np.linalg.norm(d))
            if r_ < 1e-6:
                continue
            u = d / r_
            proj = (s - sc) @ u
            side = np.abs((s - sc) @ np.array((-u[1], u[0])))
            ok = side < 0.02
            reach = float(proj[ok].max()) if ok.any() else float(proj.max())
            if v in snug:
                P[v][:2] = sc + u * (reach + CAP_SNUG)
                pushed += 1
            elif r_ < reach + 0.006:
                P[v][:2] = sc + u * (reach + 0.006)
                pushed += 1
    Cm.P = [p for p in P]
    print("CAPTAIN cap cleared of the new head: %d points pushed out" % pushed)


def main():
    # (an empty scene: the factory start-up's cube, camera and light removed; read_factory_settings from inside a
    # running script crashed Blender later on)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sh = Sheets()
    M, T, joints = build_body(sh)
    head_rings = build_head(M, sh, T)
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
    for e in open_edges(body_faces)[:4]:
        print("CAPTAIN open edge %s: faces %s" % (e, [(fi, M.faces[fi], M.fpart[fi]) for fi, f in enumerate(M.faces) if e[0] in f and e[1] in f]))
    fams = np.array([part_family(p) for p in M.part])
    # (the hands too, fifth round: they are built to the hands sheet, and the base body's outline pulled the fingers
    # and the thumb out of shape: the thumb came out a flat twisted sliver)
    frozen = np.isin(fams, ("head", "cap", "nose", "ear", "peak", "neck", "hand"))
    if FOOT_TOES or BASE_FEET:
        frozen |= fams == "foot"     # (fourteenth round: the toed foot is shaped by rule; the fit pulled its toes about)
        for sfx_ in ("_l", "_r"):
            frozen[M.tag["leg_rings" + sfx_][-1]] = True    # (and the ankle ring it is matched to)
    # (the torso's two top rings are under the beard in the front view: kept as built)
    for i in (len(T) - 1, len(T) - 2):
        frozen[T[i]] = True
    # (and the front of the ring below them: the sheet's outline there is the beard's)
    for k in (0, 1, 2, 14, 15):
        frozen[T[-3][k]] = True
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
    if not HAND_FIT:
        smooth_hands(M, rounds=1)
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
    # (eighth round: hanging further over the band, as far as the sheet's: fuller low down, then rolling under)
    826: {0: (0.017, 0.0), 1: (0.016, 0.0), 2: (0.011, 0.0), 3: (0.003, 0.0)},
    842: {0: (0.018, 0.0), 1: (0.017, 0.0), 2: (0.011, 0.0), 3: (0.002, 0.0)},
    855: {0: (0.008, 0.0), 1: (0.008, 0.0), 2: (0.005, 0.0)},
    868: {0: (-0.008, 0.0), 1: (-0.007, 0.0), 2: (-0.004, 0.0)},
    # the pecs (the nipples' row 610) with a fold under them, the breastbone between, and the armpit's folds (the pec's
    # edge in front of the arm, the back's behind it)
    # (fourteenth round, the critic: "heavy old pecs with a clear lower edge (an underfold over the belly) ... a dip
    # between the pecs"; "shoulder blades, a spine groove ... traps rising to the neck": stronger pecs and fold, the
    # breastbone sunk, the shoulder blades out behind (columns 6, 7) over a groove down the spine (column 8))
    615: {0: (-0.010, 0.0), 1: (0.018, 0.0), 2: (0.028, 0.0), 3: (0.018, 0.0), 5: (-0.008, 0.0), 6: (-0.010, 0.0), 7: (-0.008, 0.0), 8: (0.006, 0.0)},
    642: {0: (-0.005, 0.0), 1: (-0.008, 0.0), 2: (-0.018, 0.0), 3: (-0.006, 0.0), 5: (-0.005, 0.0), 6: (-0.004, 0.0), 8: (0.005, 0.0)},
    566: {0: (-0.007, 0.0), 1: (0.008, 0.0), 2: (0.012, 0.0), 3: (0.008, 0.0), 6: (-0.013, 0.0), 7: (-0.010, 0.0), 8: (0.006, 0.0)},
    668: {6: (-0.003, 0.0), 8: (0.005, 0.0)},
    715: {8: (0.004, 0.0)},
    525: {1: (0.006, 0.0, 0.002), 2: (0.006, 0.0, 0.003), 6: (-0.006, 0.0), 7: (-0.005, 0.0), 8: (0.003, 0.0)},
    485: {1: (-0.002, 0.0), 2: (0.004, 0.0, 0.004), 6: (-0.002, 0.0, 0.008), 7: (0.0, 0.0, 0.006)},
    # the collarbone's hint, then the shoulder's top rounded and the trapezius rising into the neck
    # (fifteenth round, the second critic: "raise the trapezius higher toward the ears": the top of the shoulder's slope up more)
    445: {1: (0.004, 0.0, 0.003), 2: (0.004, 0.0, 0.014), 6: (0.0, 0.0, 0.02), 7: (0.0, 0.0, 0.014)},
    # (eighth round: 425 and 405 are his neck now; the trapezius is the slope from it out to the shoulder's top)
}
# The kneecaps (forward, metres) on the leg ring at the knee's row, by point (point 1 is the front).
KNEE_FORM = {1: 0.012, 0: 0.006, 2: 0.006}
# The belly's rows smoothed down each front column after the forms (from, to, rounds): no ring stands out of the curve.
BELLY_SMOOTH = (755, 900, 2)
TORSO_SMOOTH = 6     # (fifteenth round, the second critic: "faint horizontal banding" across chest and back: 3 rounds were not enough)


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
    smooth_torso(M, rounds=TORSO_SMOOTH)
    torso_forms(M)


# Sixteenth round (the second critic: "a smooth balloon with no pecs, deltoids, shoulder blades or spine"; the
# coordinator: "add a few well-placed loops", not the brother's refine_forms). The ring moves above are smoothed away by
# the six rounds that take out the banding, so the forms are laid on AFTER the smoothing, as smooth fields along each
# point's normal (no ring can stand out of them): (centre x, body-sheet row, forward-or-back side, spread across, spread
# up above the centre, spread below it, metres along the normal). Side: -1 front, 1 back, 0 either.
TORSO_FORMS = (
    (0.085, 600.0, -1, 0.065, 0.075, 0.03, 0.030),     # the heavy pecs, sagging: soft above, their lower fold sharp
    (0.085, 655.0, -1, 0.07, 0.018, 0.03, -0.018),     # the fold under each pec, onto the belly (nineteenth round: -0.012)
    (0.0, 600.0, -1, 0.022, 0.07, 0.05, -0.006),       # the breastbone's dip between them
    (0.095, 545.0, 1, 0.06, 0.06, 0.07, 0.028),        # the shoulder blades under the fat (seventeenth round: 0.022)
    (0.0, 640.0, 1, 0.025, 0.2, 0.18, -0.018),         # the spine's groove, neck to waist (seventeenth round: -0.014)
    (0.19, 640.0, 1, 0.05, 0.08, 0.06, 0.008),         # (seventeenth round, the third critic: "lat flare") the lats
    (0.13, 800.0, 0, 0.05, 0.04, 0.04, 0.016),         # the love handles over the band, at his sides (nineteenth round: 0.010)
    (0.0, 790.0, -1, 0.016, 0.012, 0.012, -0.012),     # (nineteenth round, the fourth critic: "no navel") the navel
)
DELTOID = (0.024, 0.065)      # the deltoid's cap: metres out along the normal, spread round the shoulder's top


def torso_forms(M):
    P = np.array(M.P)
    N = normals_of(P, M.tris())
    fams = np.array([part_family(p) for p in M.part])
    T = M.tag["torso_rings"]
    keep = set(T[0]) | set(T[-1]) | set(T[-2]) | set(M.tag["crotch"])
    cy = float(np.median(P[fams == "torso", 1]))
    row = body_row(P[:, 2])
    d = np.zeros(len(P))
    torso = fams == "torso"
    for cx, r, side, sx, su, sd, amt in TORSO_FORMS:
        dz_px = row - r
        s_up = su / S
        s_dn = sd / S
        gz = np.where(dz_px < 0, np.exp(-(dz_px / s_up) ** 2), np.exp(-(dz_px / s_dn) ** 2))
        gx = np.exp(-((np.abs(P[:, 0]) - cx) / sx) ** 2)
        if side < 0:
            gs = np.clip((cy - P[:, 1]) / 0.05, 0, 1)
        elif side > 0:
            gs = np.clip((P[:, 1] - cy) / 0.05, 0, 1)
        else:
            gs = 1.0
        d += amt * gz * gx * gs * torso
    # the deltoids: round caps at each shoulder's top, on the torso's and the arm's points about the arm's root
    for sfx in ("_l", "_r"):
        hole = np.array([P[v] for v in M.tag["hole" + sfx]])
        top = hole[np.argmax(hole[:, 2])]
        c = hole.mean(0) * 0.4 + top * 0.6
        c[0] += np.sign(c[0]) * 0.03
        r2 = np.sum((P - c) ** 2, 1)
        near = np.isin(fams, ("torso", "arm"))
        d += DELTOID[0] * np.exp(-r2 / DELTOID[1] ** 2) * near
    for v in keep:
        d[v] = 0.0
    P += N * d[:, None]
    M.P = [p for p in P]
    print("CAPTAIN torso forms laid on: out %.1f mm, in %.1f mm" % (1000 * float(d.max()), -1000 * float(d.min())))


def smooth_torso(M, rounds=3, lam=0.5, mu=-0.52):
    """Eighth round (the coordinator, of the grey render: "faint horizontal ring banding"): the torso's points
    smoothed together (Taubin's two steps, which keep the size), so no ring stands as a band; the arms' holes, the
    neck's ring and the crotch's ring are held."""
    P = np.array(M.P)
    E = edges_of(M.faces)
    T = M.tag["torso_rings"]
    fams = np.array([part_family(p) for p in M.part])
    sel = fams == "torso"
    for v in set(M.tag["hole_l"]) | set(M.tag["hole_r"]) | set(T[0]) | set(T[-1]) | set(M.tag["crotch"]):
        sel[v] = False
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
    # (ninth round: the forms' columns were measured on the old head sheet, whose face is wider by this much)
    col = P[:, 0] / HEAD_SX * FORM_COL_SCALE
    return P, N, row, col, -N[:, 1]


def bump(row, col, r0, c0, sr, sc):
    return np.exp(-(((row - r0) / sr) ** 2 + ((np.abs(col) - c0) / sc) ** 2))


# The face's forms in the head sheet's front view (rows, and columns out from the middle, both sides alike; pixels of
# 0.62 mm): measured off concept_captain_head.jpg (brows knit low over squinting eyes at row 487, 85 px out; puffy
# round cheeks at 545; the mouth at 638 under the moustache). Each: (row, column, row spread, column spread, metres
# out along the surface; negative in).
FACE_FORMS = (
    # the brow ridge, heavy, lower toward the middle (he frowns), and the frown's crease between the brows
    (452, 40, 10, 22, 0.007), (446, 80, 11, 30, 0.009), (444, 118, 12, 22, 0.006),
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
    (666, 0, 5, 26, -0.005),
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
    # (ninth round: the bare sheet's head has many more rings; only his face's front half is split, then its middle)
    head = set()
    for fi, f in enumerate(fam):
        if f not in ("head", "neck"):
            continue
        c = Pm[M.faces[fi]].mean(0)
        if 430 <= float(head_row(c[2])) <= 780 and c[1] < head_centre(M, c[2])[1]:
            head.add(fi)
    M1, uv1, W1, ch1 = refine(M, head, face_uv, weights)
    P = np.array(M1.P)
    fam1 = [part_family(p) for p in M1.fpart]
    face = set()
    for fi, f in enumerate(M1.faces):
        if fam1[fi] != "head" or len(f) != 4:
            continue
        c = P[f].mean(0)
        r = float(head_row(c[2]))
        if 438 <= r <= 700 and c[1] < head_centre(M1, c[2])[1] - 0.03 and abs(c[0]) < 0.075:
            face.add(fi)
    M2, uv2, W2, ch2 = refine(M1, face, uv1, W1)
    under2 = set()
    for fi in under:
        for c1 in ch1.get(fi, []):
            under2 |= set(ch2.get(c1, []))
    print("CAPTAIN refined: head %d faces split, face %d split again; %d triangles now" % (len(head), len(face), len(M2.tris())))
    return M2, uv2, W2, under2


# Seventeenth round (the third critic: "the upper body has no muscle ... huge traps from the skull to the shoulder points,
# big deltoids, Popeye forearms; the model has narrow sloping shoulders, a column of a neck and tube arms"). Measured
# first (the final .glb's front and back silhouettes over the body sheet, rows 380 to 900): from the deltoid down the
# outer outline was already within 1 cm of the sheet (so the shoulders are NOT widened: the sheet wins over the
# critic's "12 to 15 percent"), but from row 400 to 440 (the trapezius) he was 2 to 3.5 cm a side inside the sheet, the
# forearm just below the elbow 2 cm narrower than drawn, and the lower forearm 1 to 3 cm narrower. So: the trapezius
# filled out to the sheet from under the skull to the shoulder's top (the neck's rings and the head's lowest rows at
# his sides and back), the forearm widened below the elbow and less tapered to the wrist, and the bulk the front view
# cannot see put in depth: the deltoid's front and back heads, the biceps and triceps, the forearm's muscles below the
# elbow; the wrist made shallower so the forearm is no longer thickest there.
# (nineteenth round, the fourth critic: "the trapezius and neck form one slab that rises from the shoulders to
# mid-ear height ... like a turtleneck". Measured on the front overlay: the model's outline stood out of the sheet's
# beside the neck from row 330 to 400, and the sheet's trapezius leaves the neck at about row 413, some 4 to 5 cm under
# the earlobe (row 374). So the fill starts lower, at row 405, and is not lifted toward the skull.)
TRAP_FILL = ((400.0, 0.0), (410.0, 0.010), (420.0, 0.022), (434.0, 0.022), (450.0, 0.012),
             (467.0, 0.0))                                       # (body-sheet row, metres out at his sides)
TRAP_UP = 0.0              # the trapezius's slope lifted a little toward the skull at its outer part (metres)
ARM_ACROSS = ((0.0, 0.0), (0.45, 0.0), (0.92, 0.04), (1.08, 0.08), (1.3, 0.04), (1.55, 0.03), (1.75, 0.03),
              (1.9, 0.02), (2.0, 0.0))   # (along the arm: 0 shoulder, 1 elbow, 2 wrist; the share wider across)
ARM_DEEP = ((0.0, 0.10), (0.2, 0.18), (0.5, 0.26), (0.8, 0.14), (1.0, 0.04), (1.1, 0.10), (1.3, 0.07), (1.65, 0.0),
            (1.9, 0.0), (2.0, 0.0))   # (the same, the share deeper front to back)
DELT_DEEP = (0.016, 0.065)  # the deltoid's front and back heads: metres out in depth, spread round the arm's root
JAW_CREASE = (0.005, 0.003, 0.005, 0.004)   # metres: the throat back, up; the double chin down, forward
WRIST_SMOOTH = (0.05, 10)       # the wrist's smoothing: reach from the joint (metres), rounds
WRIST_FILL = (0.7, 0.0, 0.034)   # the wrist filled back out: share, metres along the arm past the joint, spread
WRIST_RUN = (0.045, 0.09, 0.85, 0.02)  # (twentieth round) the wrist's run: the joint's stretch either side, the reach fitted, the share drawn


def upper_mass(M, joints):
    P = np.array(M.P)
    fams = np.array([part_family(p) for p in M.part])
    row = body_row(P[:, 2])
    ax = np.abs(P[:, 0])
    # the trapezius: the torso's (neck's) points and the head's lowest, at his sides and back
    gain = np.interp(row, [r for r, _ in TRAP_FILL], [g for _, g in TRAP_FILL])
    side = smooth01(0.03, 0.10, ax)
    behind = np.clip((P[:, 1] + 0.02) / 0.04, 0.0, 1.0)            # (the head's points only behind the jaw's angle)
    who = np.isin(fams, ("torso", "neck")) | ((fams == "head") & (row > 388.0))
    w = gain * side * who * np.where(fams == "head", behind, 1.0)
    P[:, 0] += np.sign(P[:, 0]) * w
    P[:, 2] += TRAP_UP * (w / 0.03) * smooth01(0.08, 0.16, ax) * (1.0 - smooth01(440.0, 470.0, row))
    # the arms
    moved = 0.0
    for s_ in (1.0, -1.0):
        sfx = "_l" if s_ > 0 else "_r"
        J = mirror_x(np.array(joints["shoulder_l"]), s_)
        E = mirror_x(np.array(joints["elbow_l"]), s_)
        W = mirror_x(np.array(joints["wrist_l"]), s_)
        sel = np.where(np.isin(np.array(M.part), ("arm" + sfx, "shoulder" + sfx)))[0]
        Lu, Lf = np.linalg.norm(E - J), np.linalg.norm(W - E)
        Du, Df = (E - J) / Lu, (W - E) / Lf
        for v in sel:
            p = P[v]
            su = float(np.dot(p - J, Du)) / Lu
            if su <= 1.0:
                t = su
                c = J + Du * (np.clip(su, 0.0, 1.0) * Lu)
                d = Du
            else:
                sf = float(np.dot(p - E, Df)) / Lf
                t = 1.0 + sf
                c = E + Df * (np.clip(sf, 0.0, 1.0) * Lf)
                d = Df
            if t > 1.995:
                continue                     # (the wrist's last ring: the hand is zipped to it)
            rel = p - c
            rel = rel - d * np.dot(rel, d)
            fwd = np.array((0.0, -1.0, 0.0))
            fwd = fwd - d * np.dot(fwd, d)
            fwd /= np.linalg.norm(fwd)
            across = np.cross(d, fwd)
            ka = float(np.interp(t, [a for a, _ in ARM_ACROSS], [b for _, b in ARM_ACROSS]))
            kd = float(np.interp(t, [a for a, _ in ARM_DEEP], [b for _, b in ARM_DEEP]))
            new = p + across * np.dot(rel, across) * ka + fwd * np.dot(rel, fwd) * kd
            moved = max(moved, float(np.linalg.norm(new - p)))
            P[v] = new
        # the deltoid's heads, in depth only, round the arm's root
        hole = np.array([P[v] for v in M.tag["hole" + sfx]])
        c = hole.mean(0)
        c[0] += s_ * 0.02
        r2 = np.sum((P - c) ** 2, 1)
        near = np.isin(fams, ("torso", "arm", "shoulder")) & (np.sign(P[:, 0]) == s_)
        g = DELT_DEEP[0] * np.exp(-r2 / DELT_DEEP[1] ** 2) * near
        P[:, 1] += np.sign(P[:, 1] - c[1]) * g * np.clip(np.abs(P[:, 1] - c[1]) / 0.03, 0, 1)
    # The wrist: the forearm's last ring, the zipper and the hand's widened loop smoothed together round the wrist's
    # joint (plain Laplacian, strongest at the joint), so no step, ring or spike is left where the hand meets the arm
    E0 = edges_of(M.faces)
    deg = np.bincount(E0.ravel(), minlength=len(P)).astype(float)
    for s_ in (1.0, -1.0):
        Wj = mirror_x(np.array(joints["wrist_l"]), s_)
        dist = np.linalg.norm(P - Wj, axis=1)
        wgt = np.clip(1.0 - dist / WRIST_SMOOTH[0], 0, 1) * np.isin(fams, ("arm", "hand", "shoulder", "wrist")) * (deg > 0)
        for _ in range(WRIST_SMOOTH[1]):
            acc = np.zeros_like(P)
            np.add.at(acc, E0[:, 0], P[E0[:, 1]])
            np.add.at(acc, E0[:, 1], P[E0[:, 0]])
            avg = acc / np.maximum(deg, 1)[:, None]
            P += (avg - P) * (wgt * 0.5)[:, None]
        # (the smoothing shrinks the waist it leaves: filled back out round the arm's line to the sheet's thick wrist)
        Ej = mirror_x(np.array(joints["elbow_l"]), s_)
        Df_ = (Wj - Ej) / np.linalg.norm(Wj - Ej)
        rel = P - Wj
        al = rel @ Df_
        perp = rel - np.outer(al, Df_)
        g = WRIST_FILL[0] * np.exp(-((al - WRIST_FILL[1]) / WRIST_FILL[2]) ** 2) * (np.linalg.norm(perp, axis=1) < 0.09)
        g *= np.isin(fams, ("arm", "hand", "shoulder", "wrist"))
        P += perp * g[:, None]
        # (and the flanges: a few corners of the base hand's heel stood out past the wrist as sharp fins, in every round
        # since the base hand came in. A hand point near the wrist further from the arm's line than 1.2 times its
        # neighbours' middle at that place along the arm is drawn in to that)
        rel = P - Wj
        al = rel @ Df_
        perp = rel - np.outer(al, Df_)
        pr = np.linalg.norm(perp, axis=1)
        mine = np.isin(np.array(M.part), ("hand" + ("_l" if s_ > 0 else "_r"), "arm" + ("_l" if s_ > 0 else "_r"))) & (np.abs(al) < 0.06) & (pr < 0.2)
        idx = np.where(mine)[0]
        pulled = 0
        for i in idx:
            if abs(al[i]) > 0.035:
                continue
            nb = idx[np.abs(al[idx] - al[i]) < 0.008]
            lim = 1.2 * float(np.median(pr[nb]))
            if pr[i] > lim:
                P[i] = P[i] - perp[i] * (1.0 - lim / pr[i])
                pulled += 1
        print("CAPTAIN wrist%s: %d fin points drawn in" % ("_l" if s_ > 0 else "_r", pulled))
        pr = np.linalg.norm(P - Wj - np.outer((P - Wj) @ Df_, Df_), axis=1)
        odd = np.where((np.abs(al) < 0.05) & (pr > 0.072) & (pr < 0.2))[0]
        print("CAPTAIN wrist%s: points standing out over 7.2 cm from the arm's line: %d %s" % (
            "_l" if s_ > 0 else "_r", len(odd), sorted({M.part[i] for i in odd})))
    # (twentieth round, the fifth critic: "a hard seam ring where the hand meets the forearm, with jagged triangles";
    # "the wrist pinches then the hand flares") The wrist's outline made one smooth run: round the arm's line, in 16
    # sectors, the radius over WRIST_RUN of arm and hand either side of the joint is taken as a straight run between
    # the medians either side of the joint's own stretch (each point moved 1.5 cm at most), and the points within it are drawn most of the way onto it
    for s_ in (1.0, -1.0):
        sfx_ = "_l" if s_ > 0 else "_r"
        Wj = mirror_x(np.array(joints["wrist_l"]), s_)
        Ej = mirror_x(np.array(joints["elbow_l"]), s_)
        Df_ = (Wj - Ej) / np.linalg.norm(Wj - Ej)
        e1 = np.cross(Df_, (0.0, 0.0, 1.0))
        e1 /= np.linalg.norm(e1)
        e2 = np.cross(Df_, e1)
        parts_ = np.array(M.part)
        mine = np.isin(parts_, ("hand" + sfx_, "arm" + sfx_))
        rel = P - Wj
        al = rel @ Df_
        perp = rel - np.outer(al, Df_)
        pr = np.linalg.norm(perp, axis=1)
        th = np.arctan2(perp @ e2, perp @ e1)
        zone = mine & (np.abs(al) < WRIST_RUN[1]) & (pr < 0.12)
        fit_ = zone & (np.abs(al) > WRIST_RUN[0])
        sec = ((th + math.pi) / math.tau * 16).astype(int) % 16
        moved_ = 0.0
        for k in range(16):
            near_k = (np.abs(((sec - k + 8) % 16) - 8) <= 1)
            f_ = fit_ & near_k
            if f_.sum() < 4:
                continue
            lo_, hi_ = f_ & (al < 0), f_ & (al > 0)
            if lo_.sum() < 2 or hi_.sum() < 2:
                continue
            a0, r0 = float(np.median(al[lo_])), float(np.median(pr[lo_]))
            a1, r1 = float(np.median(al[hi_])), float(np.median(pr[hi_]))
            j_ = zone & (sec == k) & (np.abs(al) <= WRIST_RUN[0])
            for i in np.where(j_)[0]:
                want = r0 + (r1 - r0) * float(np.clip((al[i] - a0) / max(a1 - a0, 1e-6), 0.0, 1.0))
                want = float(np.clip(want, pr[i] - WRIST_RUN[3], pr[i] + WRIST_RUN[3]))
                t_ = WRIST_RUN[2] * (1.0 - smooth01(WRIST_RUN[0] * 0.6, WRIST_RUN[0], abs(al[i])))
                new_r = pr[i] + (want - pr[i]) * t_
                q = Wj + Df_ * al[i] + perp[i] / max(pr[i], 1e-9) * new_r
                moved_ = max(moved_, float(np.linalg.norm(q - P[i])))
                P[i] = q
        print("CAPTAIN wrist%s run: drawn onto one smooth outline, most a point moved %.1f mm" % (sfx_, moved_ * 1000))
    # The under-jaw's crease (the user: "stop his chin and jaw phasing into his neck- have a pose where he is looking up
    # to see what I mean"). In section the midline ran chin (y -0.189) -> head's open edge (-0.166) -> throat (-0.088)
    # -> neck's base (-0.140) -> chest (-0.182) within 5 cm of height: a fold existed, but the under-jaw's last row and
    # the throat met as one smooth surface, so tilted back the chin read as part of the neck. The head's open edge (the
    # throat side of the zipper) is tucked back up into the fold and the row above it (the double chin) hung down over
    # it, under the chin and the jaw only (in front of the ears).
    b0, nh = M.tag["base_head"]
    zip_pts = {v for f, p in zip(M.faces, M.fpart) if p == "neck" for v in f if v >= b0}
    E = edges_of([f for f in M.faces])
    ring1 = set()
    for a_, b_ in E:
        if a_ in zip_pts and b_ >= b0 and b_ not in zip_pts:
            ring1.add(b_)
        if b_ in zip_pts and a_ >= b0 and a_ not in zip_pts:
            ring1.add(a_)
    cyh = float(np.median(P[b0:b0 + nh, 1]))
    for v in zip_pts:
        f_ = float(np.clip((cyh - 0.02 - P[v][1]) / 0.04, 0, 1))
        P[v][1] += JAW_CREASE[0] * f_
        P[v][2] += JAW_CREASE[1] * f_
    for v in ring1:
        f_ = float(np.clip((cyh - 0.02 - P[v][1]) / 0.04, 0, 1))
        P[v][2] -= JAW_CREASE[2] * f_
        P[v][1] -= JAW_CREASE[3] * f_
    M.P = [p for p in P]
    print("CAPTAIN upper mass: the under-jaw's crease: %d throat points tucked, %d double-chin points hung over" % (len(zip_pts), len(ring1)))
    print("CAPTAIN upper mass: trapezius out %.1f cm at most, arms moved %.1f cm at most" % (100 * float(w.max()), 100 * moved))
    return M


# (eighteenth round, the neck's base: "a ragged collar ring at the base of the neck when the head looks up, down or
# turns". Measured: at his side the head's open edge (z 1.308), the neck's top ring (1.303) and the next (1.285) stood
# within 2.3 cm of height, weighted head 0.92 -> 0.4 -> neck 0.85 -> 0.45 -> chest: a turn of 45 degrees sheared the
# skin 15 degrees over 1 cm and folded it; at the front the throat is a pocket 8 cm deep under the chin with the same
# steps. The practice for short thick necks: the neck's influence spread down into the trapezius and the top of the
# chest, the weights smooth across head / neck / chest. Here: a harmonic field (Laplace, edge-length weighted) solved
# over the neck's zone, 1 on the head (all but its two lowest rows), 0 on the body beyond NECK_ZONE of the head's
# open edge; the neck's and head's shares taken from it (NECK_SHARE), the rest the body's own weights.)
NECK_ZONE = 0.13           # metres from the head's open edge over which the body's points are blended
NECK_SHARE = (0.04, 0.62, 1.0)   # the field's values where the neck starts, where it is whole, where the head is whole
NECK_FREE_ROWS = (2, 5, 70.0)   # the head's lowest rows blended too: under the jaw (its open edge and the row
                                # above), at his sides and back (beyond this many degrees from his front)


def wrist_tone(M, face_uv, skin, spos, shit, reach=0.035):
    """(eighteenth round, "a faint tone change and a thin dark line at the wrist", and a pale band once the wrist moved
    up): the wrist's zipper faces and the texels of the hand's and the forearm's faces within `reach` of the wrist's
    joint take a blend of the forearm's tone just above and the hand's just below, by height along the arm, so the two
    pictures meet with no band."""
    Pp = np.array(M.P)
    _, _, _, fid = texel_geometry(M, face_uv, "skin", Pp, normals_of(Pp, M.tris()))
    fpart = np.array(list(M.fpart) + ["none"])[fid]
    out = skin.copy()
    n = 0
    for sfx in ("_l", "_r"):
        wf = np.zeros(len(M.faces) + 1, bool)
        # (the zipper: the hand's faces that hold forearm points; the tag's face numbers went stale with the transplant)
        wf[[fi for fi, (f, p) in enumerate(zip(M.faces, M.fpart)) if p == "hand" + sfx and any(M.part[v] == "arm" + sfx for v in f)]] = True
        ring = Pp[M.tag["arm_rings" + sfx][-1]]
        c = ring.mean(0)
        hand_c = Pp[[v for v in range(len(Pp)) if M.part[v] == "hand" + sfx]].mean(0)
        ax = hand_c - c
        ax /= np.linalg.norm(ax)
        s = (spos - c) @ ax
        zone = shit & (np.abs(s) < reach) & (np.char.startswith(fpart.astype(str), "arm" + sfx) | np.char.startswith(fpart.astype(str), "hand" + sfx))
        above = shit & np.char.startswith(fpart.astype(str), "arm" + sfx) & (s < -reach) & (s > -reach - 0.03)
        below = shit & (fpart == "hand" + sfx) & ~wf[fid] & (s > reach * 0.4) & (s < reach + 0.03)
        if not above.any() or not below.any():
            continue
        ta = np.median(skin[above], 0)
        tb = np.median(skin[below], 0)
        t = smooth01(-reach, reach, s)[..., None]
        want = ta * (1 - t) + tb * t
        # keep the paint's own detail (its ratio to a wide blur) on the blended tone, but not over the zipper itself
        soft = box_blur(skin, 6)
        detail = np.clip(skin / np.maximum(soft, 1e-3), 0.85, 1.15)
        detail = np.where(wf[fid][..., None], 1.0, detail)
        w = (1.0 - smooth01(reach * 0.6, reach, np.abs(s)))[..., None] * zone[..., None]
        out = out * (1 - w) + (want * detail) * w
        n += int(zone.sum())
    print("CAPTAIN wrist tone: %d texels blended" % n)
    return out


UNDER_JAW = (0.15, 0.5, 1.345, 14)  # (eighteenth round) the face's paint where it faces down (-nz from, to), below
                                     # this height, replaced by its own wide blur (texels): no smeared projection


def clean_under_jaw(M, face_uv, face, fpos, fhit):
    """The under-jaw and throat took the front and side views' paint at a grazing angle: vertical smears, seen when he
    looks up. There the picture is replaced by a wide blur of itself (only texels facing down below the mouth are
    averaged), which keeps the stubble's tone and its gentle change and drops the streaks."""
    Pp = np.array(M.P)
    _, nrm, _, _ = texel_geometry(M, face_uv, "face", Pp, normals_of(Pp, M.tris()))
    down = -nrm[..., 2]
    low = fpos[..., 2] < UNDER_JAW[2]
    w = (smooth01(UNDER_JAW[0], UNDER_JAW[1], down) * low * fhit).astype(np.float32)
    m = (fhit & low & (down > 0.0)).astype(np.float32)
    r = UNDER_JAW[3]
    num = box_blur(face * m[..., None], r)
    den = box_blur(m, r)
    soft = num / np.maximum(den, 1e-6)[..., None]
    out = face * (1.0 - w[..., None]) + soft * w[..., None]
    print("CAPTAIN under-jaw paint smoothed over %d texels" % int((w > 0.5).sum()))
    return out


NECK_SLOPE = (55.0, 85.0, 0.6, 1)  # (nineteenth round: from the head's first row, not its third: from the third the
                                     # slope rose to mid-ear, the critic's "turtleneck") degrees from his front where the fill starts, where it is whole; its strength;
                                     # the head's row (from its open edge) the slope starts from
NECK_SPLIT = 0.16                    # metres from the head's open edge within which the torso's faces are split once
NECK_SPLIT_FROM = 50.0               # degrees from his front: only his sides and back split (the throat crumpled split)
NECK_SLOPE_MAX = 0.03              # metres a point is pushed out at most
NECK_ZIP_SMOOTH = (0.035, 6)          # metres from the zipper the smoothing reaches, Taubin rounds
NECK_SLOPE_SMOOTH = 8                # Taubin rounds over the pushed points afterwards


def neck_slope(M, T):
    """(eighteenth round) At his sides and back the neck stood as a wall on a near-level trapezius shelf (a right angle
    at its foot that folded when the head moved; the sheet's back view draws the trapezius as one straight slope from
    under the skull to the shoulders). The head's lowest rows, the zipper and the neck's two rings are pushed out (never
    in) onto the straight line from the head's row NECK_SLOPE[3] to the shoulders' ring, column by column round him."""
    P = np.array(M.P)
    b0, nh = M.tag["base_head"]
    E = edges_of(M.faces)
    zip_pts = sorted({v for f, p in zip(M.faces, M.fpart) if p == "neck" for v in f if b0 <= v < b0 + nh})
    top = NECK_SLOPE[3]
    step = np.full(len(P), 99)
    step[zip_pts] = 0
    inh = lambda i: (i >= b0) & (i < b0 + nh)
    for s in range(1, top + 1):
        a = (step[E[:, 0]] == s - 1) & inh(E[:, 1])
        b = (step[E[:, 1]] == s - 1) & inh(E[:, 0])
        step[E[a, 1]] = np.minimum(step[E[a, 1]], s)
        step[E[b, 0]] = np.minimum(step[E[b, 0]], s)
    cy = 0.01
    ang = np.degrees(np.arctan2(P[:, 0], -(P[:, 1] - cy)))
    rad = np.hypot(P[:, 0], P[:, 1] - cy)
    up = np.where(step == top)[0]
    low = np.array(T[-3])
    fams = np.array([part_family(p) for p in M.part])
    dz = np.min(np.linalg.norm(P[:, None, :] - P[zip_pts][None, :, :], axis=2), axis=1)
    body = np.isin(fams, ("torso", "shoulder")) & (dz < NECK_SPLIT) & np.isin(np.arange(len(P)), np.unique(E))
    cand = sorted(set(np.where(step < top)[0].tolist()) | set(T[-1]) | set(T[-2]) | set(np.where(body)[0].tolist()))
    moved = []
    for v in cand:
        a = abs(ang[v])
        g = float(smooth01(NECK_SLOPE[0], NECK_SLOPE[1], a)) * (1.0 - 0.6 * float(smooth01(150.0, 175.0, a)))
        if g <= 0.0:
            continue
        da = np.abs((ang[up] - ang[v] + 180.0) % 360.0 - 180.0)
        nb = up[da < 12.0]
        if len(nb) == 0:
            continue
        rA, zA = float(rad[nb].mean()), float(P[nb, 2].mean())
        dl = (ang[low] - ang[v] + 180.0) % 360.0 - 180.0
        k = np.argsort(np.abs(dl))[:2]
        wk = 1.0 / np.maximum(np.abs(dl[k]), 1e-3)
        rB = float((rad[low[k]] * wk).sum() / wk.sum())
        zB = float((P[low[k], 2] * wk).sum() / wk.sum())
        z = P[v, 2]
        if not (zB < z < zA):
            continue
        rl = rB + (rA - rB) * (z - zB) / (zA - zB)
        if rl > rad[v]:
            dr = g * NECK_SLOPE[2] * (rl - rad[v])
            d2 = np.array((P[v, 0], P[v, 1] - cy)) / max(rad[v], 1e-6)
            dr = min(dr, NECK_SLOPE_MAX)
            P[v, 0] += d2[0] * dr
            P[v, 1] += d2[1] * dr
            moved.append(dr)
    # the pushed points smoothed among themselves (Taubin, so the slope keeps its size): the head's rows, the zipper and
    # the rings were moved by different amounts and stood as facets
    cs = np.zeros(len(P), bool)
    cs[cand] = True
    gs = np.array([float(smooth01(NECK_SLOPE[0] - 15.0, NECK_SLOPE[1], abs(ang[v]))) for v in range(len(P))]) * cs
    deg = np.zeros(len(P))
    np.add.at(deg, E[:, 0], 1.0)
    np.add.at(deg, E[:, 1], 1.0)
    for _ in range(NECK_SLOPE_SMOOTH):
        for lam in (0.5, -0.52):
            acc = np.zeros_like(P)
            np.add.at(acc, E[:, 0], P[E[:, 1]])
            np.add.at(acc, E[:, 1], P[E[:, 0]])
            avg = acc / np.maximum(deg, 1)[:, None]
            P += (avg - P) * (lam * gs)[:, None]
    # (nineteenth round, the fourth critic: "a hard horizontal crease runs where the jaw meets the neck", and from below
    # a saw edge at the neck's sides: the zipper between the head's open edge and the neck's ring smoothed all the way
    # round, fading out by NECK_ZIP_SMOOTH[0] from it)
    dz2 = np.min(np.linalg.norm(P[:, None, :] - P[zip_pts][None, :, :], axis=2), axis=1)
    gz = np.clip(1.0 - dz2 / NECK_ZIP_SMOOTH[0], 0.0, 1.0) * np.isin(np.arange(len(P)), np.unique(E))
    for _ in range(NECK_ZIP_SMOOTH[1]):
        for lam in (0.5, -0.52):
            acc = np.zeros_like(P)
            np.add.at(acc, E[:, 0], P[E[:, 1]])
            np.add.at(acc, E[:, 1], P[E[:, 0]])
            avg = acc / np.maximum(deg, 1)[:, None]
            P += (avg - P) * (lam * gz)[:, None]
    M.P = [p for p in P]
    print("CAPTAIN neck slope: %d points pushed out onto the trapezius's line, %.1f cm at most" % (
        len(moved), 100 * max(moved) if moved else 0.0))


def unfold_body(M, rounds=40, limit=100.0):
    """(eighteenth round) Edges whose two triangles turn more than `limit` degrees against each other (folds left where
    the neck's slope meets the jaw, and in the armpits) found among the torso's, neck's, shoulders' and arms' points and
    the head's below its ears; their points drawn to their neighbours' middle, round after round, until none is left."""
    P = np.array(M.P)
    tris = np.array(M.tris())
    fams = np.array([part_family(p) for p in M.part])
    ok = np.isin(fams, ("torso", "neck", "shoulder", "arm")) | ((fams == "head") & (P[:, 2] < 1.33))
    # (twentieth round: and the palm, whose heel folded into shards at the wrist)
    ok |= np.isin(np.array(M.part), ("hand_l", "hand_r"))
    E = edges_of(M.faces)
    deg = np.zeros(len(P))
    np.add.at(deg, E[:, 0], 1.0)
    np.add.at(deg, E[:, 1], 1.0)
    ef = {}
    for ti, t in enumerate(tris):
        for k in range(3):
            a, b = int(t[k]), int(t[(k + 1) % 3])
            ef.setdefault((min(a, b), max(a, b)), []).append(ti)
    pairs = [(k, v) for k, v in ef.items() if len(v) == 2 and ok[k[0]] and ok[k[1]]]
    first = None
    for r in range(rounds):
        n = np.cross(P[tris[:, 1]] - P[tris[:, 0]], P[tris[:, 2]] - P[tris[:, 0]])
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        bad = np.zeros(len(P), bool)
        cnt = 0
        for (a, b), (t1, t2) in pairs:
            if float(np.dot(n[t1], n[t2])) < math.cos(math.radians(limit)):
                bad[list(tris[t1]) + list(tris[t2])] = True
                cnt += 1
        if first is None:
            first = cnt
        if cnt == 0:
            break
        bad &= ok
        acc = np.zeros_like(P)
        np.add.at(acc, E[:, 0], P[E[:, 1]])
        np.add.at(acc, E[:, 1], P[E[:, 0]])
        avg = acc / np.maximum(deg, 1)[:, None]
        P[bad] += (avg[bad] - P[bad]) * 0.5
    M.P = [p for p in P]
    print("CAPTAIN body unfolded: %d folded edges at first, %d after %d rounds" % (first, cnt, r + 1))


def neck_blend(M, weights):
    P = np.array(M.P)
    b0, nh = M.tag["base_head"]
    fams = np.array([part_family(p) for p in M.part])
    E = edges_of(M.faces)
    used = np.zeros(len(P), bool)
    used[E.ravel()] = True
    zip_pts = sorted({v for f, p in zip(M.faces, M.fpart) if p == "neck" for v in f if b0 <= v < b0 + nh})
    step = np.full(len(P), 99)
    step[zip_pts] = 0
    for s in range(1, NECK_FREE_ROWS[1]):
        a = (step[E[:, 0]] == s - 1) & (E[:, 1] >= b0) & (E[:, 1] < b0 + nh)
        b = (step[E[:, 1]] == s - 1) & (E[:, 0] >= b0) & (E[:, 0] < b0 + nh)
        step[E[a, 1]] = np.minimum(step[E[a, 1]], s)
        step[E[b, 0]] = np.minimum(step[E[b, 0]], s)
    loop = P[zip_pts]
    d = np.min(np.linalg.norm(P[:, None, :] - loop[None, :, :], axis=2), axis=1)
    head = np.zeros(len(P), bool)
    head[b0:b0 + nh] = True
    angf = np.abs(np.degrees(np.arctan2(P[:, 0], -(P[:, 1] - 0.01))))
    rows_ok = step < np.where(angf > NECK_FREE_ROWS[2], NECK_FREE_ROWS[1], NECK_FREE_ROWS[0])
    rows_ok &= P[:, 2] < P[M.tag["earlobe_l"][0], 2] - 0.015      # (the ears and the earring stay the head's)
    free = used & ((head & rows_ok) | (~head & np.isin(fams, ("torso", "neck", "shoulder")) & (d < NECK_ZONE)))
    u = np.where(head & ~free, 1.0, 0.0)
    L = np.linalg.norm(P[E[:, 0]] - P[E[:, 1]], axis=1)
    wE = 1.0 / np.maximum(L, 1e-4)
    den = np.zeros(len(P))
    np.add.at(den, E[:, 0], wE)
    np.add.at(den, E[:, 1], wE)
    for _ in range(600):
        acc = np.zeros(len(P))
        np.add.at(acc, E[:, 0], wE * u[E[:, 1]])
        np.add.at(acc, E[:, 1], wE * u[E[:, 0]])
        u = np.where(free, acc / np.maximum(den, 1e-9), u)
    out = list(weights)
    n0, n1, n2 = NECK_SHARE
    for v in np.where(free)[0]:
        rest = {k: x for k, x in weights[v].items() if k not in ("head", "neck")}
        tot = sum(rest.values())
        rest = {k: x / tot for k, x in rest.items()} if tot > 1e-6 else {"chest": 1.0}
        whole = float(smooth01(n0, n1, u[v]))
        hd = float(smooth01(n1, n2, u[v]))
        w = {k: x * (1.0 - whole) for k, x in rest.items()}
        w["neck"] = w.get("neck", 0.0) + whole - hd
        w["head"] = w.get("head", 0.0) + hd
        w = {k: x for k, x in w.items() if x > 0.01}
        t = sum(w.values())
        out[v] = {k: x / t for k, x in sorted(w.items(), key=lambda kv: -kv[1])[:4]}
    print("CAPTAIN neck blend: %d points blended (%d of the head's), field %.2f .. %.2f" % (
        int(free.sum()), int((free & head).sum()), float(u[free].min()), float(u[free].max())))
    return out


def bare_scalp(M, face, fpos, fhit):
    """(nineteenth round, the fourth critic: "grey tufts above the ears are painted on as blotches where the sheet's
    side hair is; the base model should be bare, so they read as dirt") The bare sheet's grey side and back hair taken
    out of the head's paint: pale, unsaturated texels above the earlobe and behind the brows (the brows are kept) are
    refilled from the skin round them."""
    P = np.array(M.P)
    b0, nh = M.tag["base_head"]
    yc = float(np.median(P[b0:b0 + nh, 1]))
    z_lobe = float(P[M.tag["earlobe_l"][0]][2])
    lum = face.mean(-1)
    sat = face.max(-1) - face.min(-1)
    hair = fhit & (sat < 0.15) & (lum > 0.34) & (fpos[..., 2] > z_lobe - 0.01) & (fpos[..., 1] > yc - 0.06)
    hair = _grow(hair, 4) & fhit
    clean = fill_out(face, fhit & ~hair, 96)
    out = np.where(hair[..., None], blur(clean, 3), face)
    print("CAPTAIN bare scalp: %d texels of painted side hair refilled" % int(hair.sum()))
    return out


# Twenty-second round. The user: "Are you rebuilding the whole head each revision? I'm not seeing improvement, you
# should just be making adjustments". So the mesh as the twenty-first round left it (every step up to the neck's
# blend: the fitted body, the base head with its carves, nose and ears, the fitted hands and feet) is FROZEN in
# BASE_MESH (point positions; the faces are made the same way every build, and the count is checked), and the build
# loads it unless --rebuild-base is given (--save-base writes it again from a rebuild). Changes from here are an ordered
# list of small named ADJUSTMENTS laid on the frozen mesh, each a local move with smooth falloff, each with its own
# amount (ADJUSTMENTS; --adj name=amount,name=0 sets amounts; --adj-upto name applies only those before it, for
# before-and-after pictures). Each was kept only when its before-and-after pair moved toward the sheet.
BASE_MESH = os.path.join(HERE, "blend", "captain_base_mesh.npz")


SKIN_GAIN = tuple(float(v) for v in arg("--skin-gain", "0.81,0.85,0.90").split(","))


def frozen_base(M):
    if "--save-base" in ARGS:
        np.savez_compressed(BASE_MESH, P=np.array(M.P, float), nfaces=len(M.faces), npoints=len(M.P))
        print("CAPTAIN base mesh saved: %d points" % len(M.P))
        return
    if "--rebuild-base" in ARGS or not os.path.exists(BASE_MESH):
        print("CAPTAIN base mesh: rebuilt, not loaded")
        return
    z = np.load(BASE_MESH)
    if int(z["npoints"]) != len(M.P) or int(z["nfaces"]) != len(M.faces):
        raise RuntimeError("frozen base mesh does not match the build (%d/%d points, %d/%d faces)" % (
            int(z["npoints"]), len(M.P), int(z["nfaces"]), len(M.faces)))
    moved = float(np.abs(z["P"] - np.array(M.P)).max())
    M.P = [p for p in z["P"]]
    print("CAPTAIN base mesh loaded (%d points; the rebuild differed by %.2f mm at most)" % (len(M.P), 1000 * moved))


ADJ_SET = {kv.split("=")[0]: float(kv.split("=")[1]) for kv in arg("--adj", "").split(",") if "=" in kv}
ADJ_UPTO = arg("--adj-upto", "")


def _gauss(d, r):
    return np.exp(-(d / r) ** 2)


def adj_knuckle_bumps(M, P, N, ctx, amt):
    """The hands sheet's swollen knuckles on the back of the hand and fingers: a bump over each finger's MCP (amt
    metres), PIP (0.6 of it) and DIP (0.3), toward the hand's back."""
    move = np.zeros_like(P)
    parts = ctx["parts"]
    for sfx in ("_l", "_r"):
        back0 = np.array(ctx["joints"]["hand_frame" + sfx][0], float)
        hand = np.array([p.startswith("hand" + sfx) for p in parts])
        for n in ("little", "ring", "middle", "index"):
            js = [np.array(v, float) for v in ctx["joints"][n + sfx]]
            mine = np.array([p == "hand%s_%s" % (sfx, n) for p in parts])
            for k, (share, rad) in enumerate(((1.0, 0.0105), (0.6, 0.0075), (0.3, 0.0055))):
                jp = js[k]
                d = (js[k + 1] - js[k - 1]) if k else (js[1] - js[0])
                d /= np.linalg.norm(d)
                back = back0 - d * (back0 @ d)
                back /= np.linalg.norm(back)
                across = np.cross(d, back)
                q = P - jp
                s, a, b = q @ d, q @ across, q @ back
                on_back = np.clip(b / 0.005, 0, 1)
                w = _gauss(s, rad) * _gauss(a, rad * (1.1 if k == 0 else 0.9)) * on_back * (hand if k == 0 else mine)
                move += back[None, :] * (amt * share * w)[:, None]
    return move


def adj_finger_joints(M, P, N, ctx, amt):
    """Knobbly finger joints: each finger's ring swollen by `amt` (share) round its PIP and DIP, and a shallow crease
    across the palm side under them."""
    move = np.zeros_like(P)
    parts = ctx["parts"]
    for sfx in ("_l", "_r"):
        back0 = np.array(ctx["joints"]["hand_frame" + sfx][0], float)
        for n in ("little", "ring", "middle", "index"):
            js = [np.array(v, float) for v in ctx["joints"][n + sfx]]
            mine = np.array([p == "hand%s_%s" % (sfx, n) for p in parts])
            for k in (1, 2):
                jp = js[k]
                d = js[k + 1] - js[k - 1]
                d /= np.linalg.norm(d)
                back = back0 - d * (back0 @ d)
                back /= np.linalg.norm(back)
                q = P - jp
                s = q @ d
                r = q - np.outer(s, d)
                g = _gauss(s, 0.0055) * mine
                move += r * (amt * g)[:, None]
                on_palm = np.clip(-(q @ back) / 0.004, 0, 1)
                move += back[None, :] * (0.0012 * _gauss(s, 0.0028) * on_palm * mine)[:, None]
    return move


def adj_palm_pads(M, P, N, ctx, amt):
    """A fat thenar pad under the thumb's root (amt metres out of the palm) and a smaller hypothenar on the little
    finger's side."""
    move = np.zeros_like(P)
    parts = ctx["parts"]
    for sfx in ("_l", "_r"):
        back = np.array(ctx["joints"]["hand_frame" + sfx][0], float)
        hand = np.array([p.startswith("hand" + sfx) for p in parts])
        t0, t1 = (np.array(v, float) for v in ctx["joints"]["thumb" + sfx][:2])
        l0 = np.array(ctx["joints"]["little" + sfx][0], float)
        wr = np.array(ctx["bones"]["hand" + sfx], float)
        for c, a, r in ((t0 * 0.6 + t1 * 0.4, amt, 0.02), (l0 * 0.5 + wr * 0.5, amt * 0.65, 0.016)):
            q = P - c
            plane = q - np.outer(q @ back, back)
            on_palm = np.clip(-(q @ back) / 0.004, 0, 1)
            w = _gauss(np.linalg.norm(plane, axis=1), r) * on_palm * hand
            move -= back[None, :] * (a * w)[:, None]
    return move


# The face's landmarks as the face rig finds them on the frozen head (its self-test log): the lips' line in the middle
# at z 1.3607 (y -0.1858), the corners 4.3 to 4.6 cm out, the nose's tip (0, -0.2205, 1.3984), the chin's front
# (0, -0.2057, 1.2962), the menton (where the profile falls back) at z 1.2527.
MOUTH_Z, MOUTH_X = 1.3607, 0.044
CHIN = np.array((0.0, -0.2057, 1.2962))


def _face_pts(ctx, P):
    fam = np.array([part_family(p) for p in ctx["parts"]])
    return np.isin(fam, ("head", "neck")) & (P[:, 2] > 1.15)


def adj_frown(M, P, N, ctx, amt):
    """The sheet's upside-down-U frown: the lips' line drawn down toward its corners (amt metres at the corner, as
    the square of the way out), the corners' flesh with it, fading out by 2 cm round them."""
    face = _face_pts(ctx, P) & (P[:, 1] < -0.12)
    ax = np.abs(P[:, 0])
    t = np.clip(ax / MOUTH_X, 0, 1.25)
    down = amt * t ** 2 * _gauss(P[:, 2] - (MOUTH_Z - 0.4 * amt * t ** 2), 0.016) * np.clip((0.075 - ax) / 0.02, 0, 1)
    mv = np.zeros_like(P)
    mv[:, 2] = -down * face
    return mv


def adj_mouth_crease(M, P, N, ctx, amt):
    """The lips' meeting line and the corners cut in (amt metres) along the frowned line, so it reads in grey."""
    face = _face_pts(ctx, P) & (P[:, 1] < -0.12)
    ax = np.abs(P[:, 0])
    zl = MOUTH_Z - ctx.get("frown", 0.0) * np.clip(ax / MOUTH_X, 0, 1.25) ** 2
    w = _gauss(P[:, 2] - zl, 0.0028) * np.clip((MOUTH_X + 0.006 - ax) / 0.006, 0, 1) * face
    return -N * (amt * w)[:, None]


def _segment_dist(P, a, b):
    ab = b - a
    t = np.clip(((P - a) @ ab) / float(ab @ ab), 0, 1)
    return np.linalg.norm(P - (a + np.outer(t, ab)), axis=1), t


def adj_nasolabial(M, P, N, ctx, amt):
    """The deep folds from the nose's wings down past the mouth's corners (amt metres in), the cheek above each
    swelling a little over it."""
    face = _face_pts(ctx, P) & (P[:, 1] < -0.1)
    mv = np.zeros_like(P)
    for s in (1.0, -1.0):
        a = np.array((s * 0.034, -0.19, 1.392))
        b = np.array((s * 0.062, -0.165, 1.322))
        XZ = np.array((1.0, 0.0, 1.0))
        d, t = _segment_dist(P * XZ, a * XZ, b * XZ)
        fade = np.clip(t * 4, 0, 1) * np.clip((1 - t) * 3 + 0.3, 0, 1)
        mv -= N * (amt * _gauss(d, 0.0035) * fade * face)[:, None]
        # the cheek's fullness on the outer side of the fold
        out = a + np.array((s * 0.012, 0.004, -0.008))
        d2, t2 = _segment_dist(P * XZ, out * XZ, (b + np.array((s * 0.012, 0.004, 0.004))) * XZ)
        mv += N * (0.5 * amt * _gauss(d2, 0.008) * face)[:, None]
    return mv


def adj_jowls(M, P, N, ctx, amt):
    """Heavy jowls beside the chin: flesh below the mouth's corners lowered (amt metres) and filled out (0.6 of it)."""
    face = _face_pts(ctx, P)
    mv = np.zeros_like(P)
    for s in (1.0, -1.0):
        c = np.array((s * 0.062, -0.165, 1.305))
        w = _gauss(np.linalg.norm((P - c) * np.array((1.0, 0.8, 1.2)), axis=1), 0.024) * face
        mv[:, 2] -= amt * w
        mv += N * (0.6 * amt * w)[:, None]
    return mv


def adj_chin_ball(M, P, N, ctx, amt):
    """A round solid chin: its ball pushed out (amt metres) and the crease above it under the lower lip cut in."""
    face = _face_pts(ctx, P) & (P[:, 1] < -0.13)
    c = CHIN + np.array((0.0, 0.006, -0.004))
    w = _gauss(np.linalg.norm((P - c) * np.array((0.9, 1.0, 1.0)), axis=1), 0.02) * face
    crease = _gauss(P[:, 2] - (MOUTH_Z - 0.03), 0.004) * _gauss(P[:, 0], 0.02) * face
    return N * (amt * w - 0.4 * amt * crease)[:, None]


def adj_throat_round(M, P, N, ctx, amt):
    """The flat shelf under the jaw rounded: points that face down between the chin and the throat pushed out along
    their normals, most halfway (amt metres), so chin to throat is one convex curve with a soft double chin."""
    face = _face_pts(ctx, P)
    down = np.clip((-N[:, 2] - 0.25) / 0.4, 0, 1)
    y0, y1 = -0.205, -0.075
    t = np.clip((P[:, 1] - y0) / (y1 - y0), 0, 1)
    band = (P[:, 2] > 1.17) & (P[:, 2] < 1.29)
    w = np.sin(np.pi * t) * down * band * face * np.clip((0.09 - np.abs(P[:, 0])) / 0.03, 0, 1)
    return N * (amt * w)[:, None]


ADJUSTMENTS = [
    # (name, function, amount)
    ("knuckle_bumps", adj_knuckle_bumps, 0.009),
    ("finger_joints", adj_finger_joints, 0.16),
    ("palm_pads", adj_palm_pads, 0.005),
    ("frown", adj_frown, 0.006),
    ("mouth_crease", adj_mouth_crease, 0.0015),
    ("nasolabial", adj_nasolabial, 0.003),
    ("jowls", adj_jowls, 0.009),
    ("chin_ball", adj_chin_ball, 0.004),
    ("throat_round", adj_throat_round, 0.004),   # (0.008 folded two faces at the temple in every face shape)
    ("deltoid_mass", None, 0.04),
    ("heel_fin_off", None, 0),   # (off: 4 rounds moved 7.7 mm but the heel from behind did not change)
    ("toe_clefts", None, 0.002),
    ("wrist_seam", None, 3),
]


def _local_smooth(M, P, w, rounds, lam=0.5, mu=-0.53):
    """Taubin smoothing (keeps the size) weighted by w (0 holds a point)."""
    E = edges_of(M.faces)
    deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
    Q = P.copy()
    for _ in range(rounds):
        for k in (lam, mu):
            acc = np.zeros_like(Q)
            np.add.at(acc, E[:, 0], Q[E[:, 1]])
            np.add.at(acc, E[:, 1], Q[E[:, 0]])
            lap = acc / np.maximum(deg, 1)[:, None] - Q
            lap[deg == 0] = 0.0      # (points on no face: they would be drawn to the origin)
            Q = Q + k * lap * w[:, None]
    return Q - P


def adj_deltoid_mass(M, P, N, ctx, amt):
    """Each deltoid a round mass of its own at the shoulder's cap, out along the normals (amt metres), its front and
    back heads a little lower, on the arm and the torso's points round the arm's root."""
    fam = np.array([part_family(p) for p in ctx["parts"]])
    near = np.isin(fam, ("torso", "arm", "shoulder"))
    w = np.zeros(len(P))
    for sfx in ("_l", "_r"):
        sh_ = np.array(ctx["bones"]["upper_arm" + sfx], float)
        el = np.array(ctx["bones"]["forearm" + sfx], float)
        d = (el - sh_) / np.linalg.norm(el - sh_)
        c = sh_ + d * 0.045
        for off, r, k in ((0.0, 0.05, 1.0), (-0.03, 0.04, 0.6), (0.03, 0.04, 0.6)):
            cc = c + np.array((0.0, off, -0.015 * abs(off) / 0.03))
            w = np.maximum(w, k * _gauss(np.linalg.norm(P - cc, axis=1), r))
    return N * (amt * w * near)[:, None]


def adj_heel_fin_off(M, P, N, ctx, amt):
    """The fin at the back of each heel smoothed away (amt rounds of Taubin smoothing over the heel), so the heel is
    a round half dome."""
    w = np.zeros(len(P))
    parts = ctx["parts"]
    for sfx in ("_l", "_r"):
        o, f_, l_ = M.tag["foot_frame" + sfx]
        mine = np.array([p.startswith("foot" + sfx) for p in parts])
        back = -((P - o) @ f_)
        w = np.maximum(w, mine * np.clip((back + 0.005) / 0.025, 0, 1) * np.clip((0.11 - P[:, 2]) / 0.03, 0, 1))
    # (the first try, Taubin over the whole heel, sharpened the fin: only the spiky points, those standing far from
    # their neighbours' middle, are drawn to it, a few rounds; the rest of the heel is left as it is)
    E = edges_of(M.faces)
    deg = np.bincount(E.ravel(), minlength=len(P)).astype(float)
    Q = P.copy()
    zone = w > 0.05
    for _ in range(int(amt)):
        acc = np.zeros_like(Q)
        np.add.at(acc, E[:, 0], Q[E[:, 1]])
        np.add.at(acc, E[:, 1], Q[E[:, 0]])
        lap = acc / np.maximum(deg, 1)[:, None] - Q
        lap[deg == 0] = 0.0
        m = np.linalg.norm(lap, axis=1)
        bad = zone & (m > 1.6 * np.median(m[zone])) & (m < 0.012)
        Q[bad] += 0.7 * lap[bad] * w[bad, None]
    return Q - P


def adj_toe_clefts(M, P, N, ctx, amt):
    """Clefts between the toes (amt metres in), deepest at the tips' line, running 2.2 cm back: separate toes, the
    big toe's cleft the deepest."""
    mv = np.zeros_like(P)
    parts = ctx["parts"]
    for sfx in ("_l", "_r"):
        o, f_, l_ = M.tag["foot_frame" + sfx]
        mine = np.array([p.startswith("foot" + sfx) for p in parts])
        tips = [np.array(t, float) for t, _ in M.tag["foot_toes" + sfx]]
        for i in range(len(tips) - 1):
            a = (tips[i] + tips[i + 1]) / 2
            b = a - f_ * 0.022
            d, t = _segment_dist(P * np.array((1, 1, 0)), a * np.array((1, 1, 0)), b * np.array((1, 1, 0)))
            k = 1.3 if i == 0 else 1.0
            mv -= N * (amt * k * _gauss(d, 0.0035) * (1 - 0.6 * t) * mine * (P[:, 2] > 0.004))[:, None]
    return mv


def adj_wrist_seam(M, P, N, ctx, amt):
    """The step where the hand meets the forearm smoothed (amt rounds) within 2.5 cm of the wrist joint."""
    fam = np.array([part_family(p) for p in ctx["parts"]])
    w = np.zeros(len(P))
    for sfx in ("_l", "_r"):
        wr = np.array(ctx["bones"]["hand" + sfx], float)
        el = np.array(ctx["bones"]["forearm" + sfx], float)
        d = (wr - el) / np.linalg.norm(wr - el)
        q = P - wr
        s = q @ d
        rad = np.linalg.norm(q - np.outer(s, d), axis=1)
        w = np.maximum(w, _gauss(s, 0.025) * (rad < 0.09))
    near_ = w > 0.3
    print("CAPTAIN wrist seam: %d points near, families %s" % (int(near_.sum()), sorted(set(fam[near_].tolist()))))
    w *= np.isin(fam, ("arm", "hand"))
    return _local_smooth(M, P, w, int(amt))


ADJ_FN = {"deltoid_mass": adj_deltoid_mass, "heel_fin_off": adj_heel_fin_off, "toe_clefts": adj_toe_clefts,
          "wrist_seam": adj_wrist_seam}
ADJUSTMENTS = [(n, f or ADJ_FN[n], a) for n, f, a in ADJUSTMENTS]


def adjust(M, bones, joints):
    ctx = {"parts": list(M.part), "joints": joints, "bones": {n: p for n, p, _ in bones}}
    done = []
    for name, fn, amt in ADJUSTMENTS:
        if ADJ_UPTO and name == ADJ_UPTO:
            break
        amt = ADJ_SET.get(name, amt)
        if not amt:
            continue
        P = np.array(M.P, float)
        N = normals_of(P, M.tris())
        mv = fn(M, P, N, ctx, amt)
        ctx[name] = amt
        M.P = [p for p in P + mv]
        done.append("%s %.4g (%.1f mm most)" % (name, amt, 1000 * float(np.linalg.norm(mv, axis=1).max())))
    print("CAPTAIN adjustments: %s" % ("; ".join(done) or "none"))


def finish(M, T, joints, sh):
    H = M.tag["head_rings"]
    bones = skeleton_joints(M, T, joints)
    weights = weights_of(M, T, bones, joints)
    islands = plan_uvs(M, T, H, joints)
    placed, face_uv = pack(islands)
    under = boxer_faces(M, T)
    M, face_uv, weights, under = refine_head(M, face_uv, weights, under)
    sculpt_head(M)
    # (twelfth round: the lofted head off, the base head on; FIGURE_HEADS.md)
    M, face_uv, weights, under = transplant_head(M, T, face_uv, weights, under, sh)
    M = upper_mass(M, joints)
    # (eighteenth round: the torso's faces round the neck's foot split once, so the slope and the neck's twist bend
    # over smaller faces than the torso's 16 columns: long slivers there folded when the head turned)
    b0, nh = M.tag["base_head"]
    zp = np.array(sorted({v for f, p in zip(M.faces, M.fpart) if p == "neck" for v in f if b0 <= v < b0 + nh}))
    Pz = np.array(M.P)
    near = lambda v: float(np.min(np.linalg.norm(Pz[zp] - Pz[v], axis=1))) < NECK_SPLIT
    sel = {fi for fi, (f, p) in enumerate(zip(M.faces, M.fpart))
           if part_family(p) in ("torso", "shoulder") and all(near(v) for v in f)
           and abs(math.degrees(math.atan2(Pz[f, 0].mean(), -(Pz[f, 1].mean() - 0.01)))) > NECK_SPLIT_FROM}
    M, face_uv, weights, children = refine(M, sel, face_uv, weights)
    under = {c for fi in under for c in children.get(fi, [fi])}
    print("CAPTAIN neck's foot: %d torso faces split" % len(sel))
    neck_slope(M, T)
    unfold_body(M)
    weights = neck_blend(M, weights)
    frozen_base(M)
    adjust(M, bones, joints)
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
    # (fourteenth round: one warm light tan for body and head, the body's painted-in shadow divided out)
    raw_skin = skin.copy()
    skin = even_tone(skin, shit)
    skin = body_hair(skin, raw_skin, shit, spos)
    skin = hair_strokes(skin, shit, spos, joints)
    skin = red_accents(M, skin, shit, spos, joints)
    if BASE_FEET:
        Pp = np.array(M.P)
        _, snrm, _, sfid = texel_geometry(M, face_uv, "skin", Pp, normals_of(Pp, M.tris()))
        fparts = np.array(list(M.fpart) + ["none"])[sfid]
        for sfx in ("_l", "_r"):
            o, f_, l_ = M.tag["foot_frame" + sfx]
            mine = shit & (fparts == "foot" + sfx)
            shin = shit & (fparts == "leg" + sfx) & (spos[..., 2] > 0.17) & (spos[..., 2] < 0.26)
            lum = skin[shin].mean(1)
            base_c = np.median(skin[shin][lum >= np.median(lum)], axis=0) * 0.97
            legs = shit & (fparts == "leg" + sfx)
            skin = paint_feet(skin, spos, snrm, shit, mine, (o, f_, l_), M.tag["foot_toes" + sfx], base_c, shin=legs,
                              ring_z=float(body_z(LEG_ROWS[-1])))
            print("CAPTAIN FEET painted%s: %d texels, the shin's tone %s" % (sfx, int(mine.sum()), np.round(base_c, 3)))
    fsat = face.max(-1) - face.min(-1)
    face, fmed = match_tone(face, fhit & (fsat > 0.1) & (face.mean(-1) > 0.35))
    face = clean_under_jaw(M, face_uv, face, fpos, fhit)
    face = bare_scalp(M, face, fpos, fhit)
    face = red_accents(M, face, fhit, fpos, joints, ears=True)
    skin = heal_seams(M, face_uv, "skin", skin, spos, shit)
    face = heal_seams(M, face_uv, "face", face, fpos, fhit)
    # (the texels round the islands taken again from the new edges: they held the old tone, a light line at seams)
    skin = fill_out(skin, shit, 64)
    skin = wrist_tone(M, face_uv, skin, spos, shit)
    face = fill_out(face, fhit, 64)
    print("CAPTAIN skin tone: body evened to %s; the head's middle %s brought to it" % (SKIN_TONE, np.round(fmed, 3)))
    # The two sheets paint his skin in slightly different tones: the head's neck is brought to the body's tone where
    # they meet (the torso's top ring), fading out up to the jaw, so no line shows at the seam.
    # (tenth round: the seam is the neck's top ring, which slopes from under the chin to the nape, so the match is made
    # along it: round the ring, the body's tone just below it and the head's just above, compared, and the head's
    # picture brought to the body's at the seam, fading out over 8 cm up; one tone for all of it left a step)
    ring = np.array([M.P[i] for i in T[-1]])
    seam = np.array([ring[k] + (ring[(k + 1) % len(ring)] - ring[k]) * t for k in range(len(ring))
                     for t in np.linspace(0, 1, 8, endpoint=False)])
    kd_s = kdtree.KDTree(len(seam))
    for i, p in enumerate(seam):
        kd_s.insert(Vector([float(v) for v in p]), i)
    kd_s.balance()

    def near_seam(pos, hit, reach):
        sel = hit & (pos[..., 2] > seam[:, 2].min() - reach) & (pos[..., 2] < seam[:, 2].max() + reach)
        rr, cc = np.where(sel)
        idx = np.zeros(len(rr), int)
        dist = np.zeros(len(rr))
        for n, (r_, c_) in enumerate(zip(rr, cc)):
            _, j, d_ = kd_s.find(Vector([float(v) for v in pos[r_, c_]]))
            idx[n], dist[n] = j, d_
        return rr, cc, idx, dist
    rb, cb_, ib, db = near_seam(spos, shit, 0.03)
    rh, ch, ih, dh = near_seam(fpos, fhit, 0.09)

    def tone(img, rr, cc, idx, dist):
        acc = np.zeros((len(seam), 3))
        cnt = np.zeros(len(seam))
        ok = dist < 0.025
        np.add.at(acc, idx[ok], img[rr[ok], cc[ok]])
        np.add.at(cnt, idx[ok], 1)
        k = np.ones(15)
        acc = np.stack([np.convolve(np.concatenate([acc[-7:, c], acc[:, c], acc[:7, c]]), k, "valid") for c in range(3)], 1)
        cnt = np.convolve(np.concatenate([cnt[-7:], cnt, cnt[:7]]), k, "valid")
        return acc / np.maximum(cnt, 1)[:, None], cnt
    body_t, nb = tone(skin, rb, cb_, ib, db)
    head_t, nh = tone(face, rh, ch, ih, dh)
    gain = np.clip(body_t / np.maximum(head_t, 1e-3), 0.6, 1.7)
    gain[(nb < 5) | (nh < 5)] = 1.0
    w = (1.0 - smooth01(0.0, 0.08, dh))[:, None]
    face[rh, ch] = face[rh, ch] * (1.0 + (gain[ih] - 1.0) * w)
    print("CAPTAIN neck tone: the head's picture brought to the body's along the seam, gain %s .. %s"
          % (np.round(gain.min(0), 2), np.round(gain.max(0), 2)))
    # His tattoos placed first, and the skin under them refilled from round them: what the sheet's ink left in the
    # skin's paint (the critic saw the ship faintly on his back with the layer hidden) is taken out, so the layer is
    # the only ink and can be moved.
    ink_faces, ink_rgba = lay_tattoos(M, face_uv, placed, sh)
    under_ink = ink_rgba[..., 3] > 0.08
    if under_ink.shape != shit.shape:      # (the overlay at TATTOO_RES times the skin picture: brought down to it)
        k_ = under_ink.shape[0] // shit.shape[0]
        under_ink = under_ink.reshape(shit.shape[0], k_, shit.shape[1], k_).any(axis=(1, 3))
    for _ in range(3):
        under_ink = under_ink | np.roll(under_ink, 1, 0) | np.roll(under_ink, -1, 0) | np.roll(under_ink, 1, 1) | np.roll(under_ink, -1, 1)
    clean = fill_out(skin, shit & ~under_ink, 64)
    skin = np.where(under_ink[..., None], blur(clean, 2), skin)
    print("CAPTAIN skin under the tattoos refilled: %d texels" % int((under_ink & shit).sum()))
    # (twenty-second round, a paint adjustment: the Godot lit render of his chest measured (205, 170, 145) against
    # the body sheet's (166, 144, 130): the skin and the face brought down by those ratios, so the game's render matches
    # the sheet's warm greyed tan)
    skin = np.clip(skin * np.array(SKIN_GAIN), 0, 1)
    face = np.clip(face * np.array(SKIN_GAIN), 0, 1)
    save_rgb(os.path.join(TEX, "captain_skin.png"), skin[::-1])
    face = fill_out(face, fhit, 64)
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
    # his tattoos: lifted from the sheet, placed by the table, a see-through layer over the clean skin
    # (laid out before the skin was saved: see above)
    if ink_faces:
        ob = mesh_object("captain_ink", P, [M.faces[i] for i in ink_faces], armature, weights)
        ob.data.materials.append(ink_material())
        uvl = ob.data.uv_layers.new(name="UVMap")
        for poly, fi in zip(ob.data.polygons, ink_faces):
            for li, q in zip(poly.loop_indices, face_uv[fi][1]):
                uvl.data[li].uv = q
        for v in ob.data.vertices:
            v.co += v.normal * 0.0007
    # the cap: its own piece on the head's bone (the game can hide it: he has a whole bare head under it)
    Cap = build_cap(sh, M)
    cap_clear(Cap, M)
    cap_puff(Cap)
    cap_object(Cap, sh, armature)
    # the earring in his left ear's lobe
    lobe = np.array(M.P[M.tag["earlobe_l"][0]])
    # (tenth round: the sheet's chunky hoop, about 2.6 cm across)
    ring_pts, ring_faces = torus(lobe + np.array((0.005, 0.0, -0.011)), 0.0115, 0.0036, 14, 6)
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
    bare_diff(objs, sh)
    bare_landmarks(M)
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
BOXER_BAND_TALL = 19.0        # sheet pixels (3.7 cm; fourteenth round, the critic: "make the waistband thicker")
BOXER_STAND = (0.018, 0.016, 0.036)   # metres: the cloth, the band, the hems (the legs flare); fifteenth round, the second
                                      # critic: "a skin-tight shell ... loose cotton standing a little off the thigh, a thick
                                      # ribbed waistband": looser (the body under them is BOXER_EASE in from the sheet's outline,
                                      # so the cloth now stands about half a centimetre past it), the band proud of the skin
BOXER_HEM = (1064.0, 1034.0)  # the hem's row at the leg's outside and at its inside (it rises to the crotch)
BOXER_FOLDS = (5, 0.004)      # loose folds round each leg: how many, how deep at the hem (metres)
BOXER_TURN = (0.014, 0.006)   # the hem turned in: how far up, how far off the skin (no paper edge)
BOXER_LEG_RINGS = 2           # the leg rings down to LEG_ROWS[1] = row 1065
BOXER_CLOTH = (0.82, 0.81, 0.78)   # (twenty-first round: was 0.7, 0.69, 0.665, which rendered grey in the lit views)
BOXER_BAND_RGB = (0.92, 0.92, 0.93)    # (fifteenth round: warm off-white, not paper white)
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
        rings = M.tag["leg_rings" + sfx][:BOXER_LEG_RINGS]     # (fourteenth round: the thigh above the hem kept, the hem rises inside)
        pts = set(v for r in rings for v in r)
        out |= {fi for fi, (f, p) in enumerate(zip(M.faces, M.fpart)) if p == "leg" + sfx and all(v in pts for v in f)}
    return out


def heart_cover(x, y):
    """How much of a unit heart (about 2.3 across, point down, y up) covers (x, y): 1 inside, 0 out."""
    y = y * 1.08 + 0.12
    f = (x * x + y * y - 1.0) ** 3 - x * x * y ** 3
    return f <= 0.0


# Sixteenth round (the critic: "a tight paper shell with a ragged hem ... loose cotton boxers with a thick waistband";
# the coordinator: port the brother's knit shorts for the structure, as loose cotton): the garment's structure is the
# brother's `knit_shorts` (tools/build_brother.py, 2026-11-18), copied here unchanged in what it does (two legs that
# read from the front, a band with a rolled lip, the hem turned under with a lip and an inside face), driven with the
# captain's own numbers: the cloth stands well off him, the legs flare loose, the band is tall and stands proud, a few
# soft folds hang round each leg and down the trunk. The old grid garment is kept as build_boxers_grid (--grid-boxers).
GRID_BOXERS = "--grid-boxers" in ARGS
BOXER_LOOSE = {"band_lip": 0.004, "band": 0.013, "cloth": 0.026, "leg_in": 0.014, "leg_out": 0.042, "hug": 0.0025}   # (nineteenth round: legs looser, the critic: "flare each leg tube out from the thigh"; cloth 0.024, leg_in 0.010, leg_out 0.036)
BOXER_LOOSE_HEM = 1060.0          # body-sheet row of the hem (the sheet's 1064 outside, 1034 at the crotch)
BOXER_LOOSE_BULGE = 0.02          # the gentle fullness at the fly (the user: "a tasteful bulge")
BOXER_LOOSE_FOLDS = (7, 0.006, 5, 0.007)   # soft folds: round the trunk below the band (how many, metres at the bottom),
                                           # round each leg (how many, metres at the hem)
BOXER_LOOSE_KEEP = 0.6            # the share of the garment's triangles kept by the collapse (976 -> about 590)


def ring_double(pts):
    """A closed ring of points with a new point between each two (the four-point subdivision rule: a smooth curve
    through the old points). Gives 2n points, the old ones at even places. (build_brother.py's)"""
    pts = np.asarray(pts, float)
    n = len(pts)
    out = np.zeros((2 * n,) + pts.shape[1:])
    for i in range(n):
        p0, p1, p2, p3 = pts[(i - 1) % n], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        out[2 * i] = p1
        out[2 * i + 1] = (-p0 + 9.0 * p1 + 9.0 * p2 - p3) / 16.0
    return out


def knit_shorts(P, N, T, leg_rings, crotch, band_z, band_tall, mid_zs, hem_z, side_cols, stand,
                bulge=0.017, seat=0.005, fly=0.0025, lower_rings=3):
    """Shorts over a lofted body (build_brother.py's, 2026-11-18; see its docstring there).
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
    z_low = [float(z) for z in zs[:lower_rings]][::-1]
    rows = []
    for k in range(nT):
        phi = math.tau * k / nT
        zb = band_z(phi)
        zb1 = zb - band_tall
        rows.append([zb, zb, zb1] + list(mid_zs(zb1)) + z_low)
    nrows = len(rows[0])
    G = []
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
        cols = side_cols(sfx)
        top = []
        for a, b in zip(cols[:-1], cols[1:]):
            top.append(bottom[2 * a])
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
        z1 = bz[1]
        targets = [z1, (z1 + hem_z) / 2.0, hem_z]
        for ti, z in enumerate(targets):
            i = int(np.clip(np.searchsorted(-bz, -z), 1, len(bz) - 1))
            t = float(np.clip((bz[i - 1] - z) / max(bz[i - 1] - bz[i], 1e-9), 0, 1))
            A, B = body[i - 1], body[i]
            pts = P[A] * (1 - t) + P[B] * t
            c = pts.mean(0)
            q10 = []
            for p in pts:
                out = p - c
                out[2] = 0.0
                out /= max(np.linalg.norm(out), 1e-9)
                inner = max(0.0, -side * out[0])
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
        hem = rings[-1]
        hc = np.array([Bx.P[v] for v in hem]).mean(0)
        lip, inside = [], []
        for v in hem:
            q = np.array(Bx.P[v], float)
            dd = q - hc
            dd[2] = 0.0
            dd /= max(np.linalg.norm(dd), 1e-9)
            lip.append(add(q - dd * 0.005 - up * 0.005, src[v]))
        for v in hem:
            q = np.array(Bx.P[v], float)
            dd = q - hc
            dd[2] = 0.0
            dd /= max(np.linalg.norm(dd), 1e-9)
            inside.append(add(q - dd * 0.012 + up * 0.016, src[v]))
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
    for sfx in ("_l", "_r"):
        hem, lip, inside, _ = rolls[sfx]
        for m, v in enumerate(hem):
            Q[v, 2] += 0.0025 * math.sin(m * math.tau * 3 / len(hem) + (0.7 if sfx == "_l" else 2.1))
            Q[lip[m], 2] += 0.0025 * math.sin(m * math.tau * 3 / len(hem) + (0.7 if sfx == "_l" else 2.1))
    Bx.P = [q for q in Q]
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
            vpos[v] = -0.007
        for v in inside:
            vpos[v] = -0.026
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
    return Bx, src, islands, {"zc": zc, "cy": cy, "rows": nrows, "G": G, "legs": legs, "rolls": rolls}


def loose_folds(Bx, info, P, T):
    """Soft folds in the loose cotton (the captain's own, not the brother's knit): the trunk's cloth below the band
    waved in and out round him, growing toward the crotch; each leg's cloth waved round the leg, most at the hem."""
    Q = np.array(Bx.P)
    G = info["G"]
    nt, at, nl, al = BOXER_LOOSE_FOLDS
    cy = info["cy"]
    nrows = len(G)
    for j in range(3, nrows):
        grow = (j - 2) / max(nrows - 3, 1)
        for i, v in enumerate(G[j]):
            phi = math.tau * i / len(G[j])
            d = Q[v] - np.array((0.0, cy, Q[v][2]))
            d[2] = 0.0
            d /= max(np.linalg.norm(d), 1e-9)
            Q[v] += d * at * grow * math.cos(nt * phi + 0.4)
    for sfx in ("_l", "_r"):
        rings = info["legs"][sfx]
        hem, lip, inside, _ = info["rolls"][sfx]
        for ri, ring in enumerate(rings[1:], 1):
            grow = ri / (len(rings) - 1)
            c = Q[ring].mean(0)
            for m, v in enumerate(ring):
                d = Q[v] - c
                d[2] = 0.0
                d /= max(np.linalg.norm(d), 1e-9)
                off = d * al * grow * math.cos(nl * math.tau * m / len(ring) + 1.1)
                Q[v] += off
                if ring is hem:
                    Q[lip[m]] += off
                    Q[inside[m]] += off * 0.5
    Bx.P = [q for q in Q]


FLY = (0.02, 0.11, 0.0028, 0.0045)   # (twenty-first round) the fly's placket: half its width, its length down from the
                                     # band, how far it stands proud, the stitched edge's ridge beside it (metres)


def fly_placket(Bx, info):
    """(twenty-first round, the critic: "fly placket visible") The fly modelled, not only painted: on his front middle,
    from the band's bottom down FLY[1], the placket stands FLY[2] proud with a soft ridge along its edge, where the paint
    draws its outline (paint_boxers)."""
    Q = np.array(Bx.P)
    N = normals_of(Q, Bx.tris())
    zb = float(body_z(BOXER_BAND[1] + BOXER_BAND_TALL))
    front = Q[:, 1] < info["cy"] - 0.05
    ax_ = np.abs(Q[:, 0])
    down = np.clip((zb - Q[:, 2]) / 0.01, 0.0, 1.0) * np.clip((Q[:, 2] - (zb - FLY[1])) / 0.015 + 1.0, 0.0, 1.0)
    plate = np.clip((FLY[0] + 0.004 - ax_) / 0.006, 0.0, 1.0)
    ridge = np.exp(-((ax_ - FLY[0]) / 0.003) ** 2)
    d = (FLY[2] * plate + FLY[3] * ridge) * down * front
    band = np.zeros(len(Q), bool)
    for fi, p in enumerate(Bx.fpart):
        if p == "boxers_band":
            band[Bx.faces[fi]] = True
    d[band] = 0.0
    Q += N * d[:, None]
    Bx.P = [q for q in Q]
    print("CAPTAIN fly modelled: %d points, most %.1f mm" % (int((d > 1e-4).sum()), 1000 * float(d.max())))


def build_boxers(M, T, sh, weights, under, armature):
    if GRID_BOXERS:
        return build_boxers_grid(M, T, sh, weights, under, armature)
    P = np.array(M.P)
    N = normals_of(P, M.tris())
    crotch = M.tag["crotch"][0]

    def band_z(phi):
        return float(body_z(band_row(phi)))

    def mid_zs(zb1):
        z905 = float(body_z(905.0))
        zb1 = max(zb1, z905 + 0.012)
        return [zb1 + (z905 - zb1) * t for t in (0.33, 0.66, 1.0)]

    def side_cols(sfx):
        return list(range(0, 9)) if sfx == "_l" else [col_of(k, -1) for k in range(0, 9)]
    lower = sum(1 for r in TORSO_ROWS if r >= 915)
    Tl = M.tag["torso_rings"][:12]
    Bx, src, islands, info = knit_shorts(P, N, Tl, {s: M.tag["leg_rings" + s] for s in ("_l", "_r")}, crotch, band_z,
                                         BOXER_BAND_TALL * S, mid_zs, float(body_z(BOXER_LOOSE_HEM)), side_cols,
                                         BOXER_LOOSE, bulge=BOXER_LOOSE_BULGE, lower_rings=lower)
    loose_folds(Bx, info, P, Tl)
    fly_placket(Bx, info)
    Q = np.array(Bx.P)
    flipped = 0
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
            flipped += 1
            # (the face's UVs turned with it: they are listed in its corners' order; left as they were, every turned
            # face took its neighbours' corners' UVs and the hearts came out as torn halves; the brother's plain knit
            # hides the same slip)
            for isl_ in islands.values():
                if fi in isl_:
                    isl_[fi] = isl_[fi][::-1]
    for n_ in islands:
        ISLANDS[n_] = ("boxers", 0.5 if n_.startswith("boxers_hem") else 1.0)
    ATLAS["boxers"] = 1024
    placed, face_uv = pack(islands)
    write_layout(face_uv, placed, "boxers", os.path.join(TEX, "captain_boxers_layout.png"))
    band_faces = {fi for fi, p in enumerate(Bx.fpart) if p == "boxers_band"}
    rgb = paint_boxers(Bx, face_uv, placed, band_faces, info["G"], info)
    path = os.path.join(TEX, "captain_boxers.png")
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
    ob = mesh_object("captain_boxers", Bx.P, Bx.faces, armature, w)
    mat = textured_material("captain_boxers", path)
    mat.use_backface_culling = True
    ob.data.materials.append(mat)
    uvl = ob.data.uv_layers.new(name="UVMap")
    for poly in ob.data.polygons:
        for li, q in zip(poly.loop_indices, face_uv[poly.index][1]):
            uvl.data[li].uv = q
    n_before = len(Bx.tris())
    if BOXER_LOOSE_KEEP >= 1.0:
        print("CAPTAIN boxers (loose, the brother's structure): %d triangles, %d islands, %d faces turned" % (n_before, len(islands), flipped))
        return Bx
    dec = ob.modifiers.new("fewer", "DECIMATE")
    dec.decimate_type = "COLLAPSE"
    dec.ratio = BOXER_LOOSE_KEEP
    dec.use_symmetry = True
    dec.symmetry_axis = "X"
    dec.use_collapse_triangulate = True
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.view_layer.objects:
        o.select_set(o is ob)
    ob.modifiers.move(ob.modifiers.find(dec.name), 0)
    bpy.ops.object.modifier_apply(modifier=dec.name)
    n_after = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    print("CAPTAIN boxers (loose, the brother's structure): %d triangles (%d before the collapse), %d islands, %d faces turned"
          % (n_after, n_before, len(islands), flipped))
    return Bx


def build_boxers_grid(M, T, sh, weights, under, armature):
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
            stand = 0.005 if j == 0 else BOXER_STAND[1] if j in band_rows else (0.75 * BOXER_STAND[0] if j == 3 else BOXER_STAND[0])
            if j == 0:
                q = q + np.array((0.0, 0.0, -0.003))
            ring.append(Bx.add(q + n * stand, "boxers"))
            src.append(s)
        G.append(ring)
    # A soft fullness at the fly (eighth round; the user: "the captain should have a tasteful bulge"): the front of the
    # cloth's lowest rings stood forward, most at the middle and lowest, so it rounds out gently and the cloth falls
    # from it to the legs. (rows 955, 990, the crotch's 1020; forward metres by column from the front middle)
    BULGE = {955: (0.006, 0.004, 0.0), 990: (0.016, 0.011, 0.003), 1020: (0.02, 0.014, 0.005)}
    for row, amounts in BULGE.items():
        j = rows_of[0].index(row)
        for k_off, amt in enumerate(amounts):
            for k in {k_off % TORSO_N, (-k_off) % TORSO_N}:
                Bx.P[G[j][k]] = Bx.P[G[j][k]] - np.array((0.0, amt, 0.0))
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
    # (the bulge carried down to the crotch: the cloth there stands forward too)
    gc = Bx.add(P[crotch] + np.array((0.0, -0.012, -BOXER_STAND[0])), "boxers")
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
            # (fourteenth round, the critic: "the hem is one straight line across both legs, so the shorts read as a
            # skirt ... paper-thin"): the hem rises toward the crotch on each leg's inside and hangs a little lower
            # outside, the cloth lies closer on the inside, loose folds stand round each leg, most at the hem, and the
            # hem is turned in to the skin below (BOXER_TURN), so it has a thickness and no gap shows under it.
            hem_in = []
            for jv, v in enumerate(br):
                out = P[v] - c
                out[2] = 0.0
                out /= max(np.linalg.norm(out), 1e-9)
                t = (1.0 - out[0] * side) / 2.0           # 1 on the leg's inside, toward the crotch
                fold = math.cos(BOXER_FOLDS[0] * math.atan2(out[1], out[0] * side) + 0.6)
                st = stand * (1.0 - 0.5 * t * t) + BOXER_FOLDS[1] * fold * (1.0 if last else 0.4)
                q = P[v] + out * st
                if last:
                    q[2] = float(body_z(BOXER_HEM[0] + (BOXER_HEM[1] - BOXER_HEM[0]) * t * t))
                    hem_in.append((P[v] + out * BOXER_TURN[1], q[2] + BOXER_TURN[0], v))
                ring.append(Bx.add(q, "boxers"))
                src.append(v)
            rings.append(ring)
        ring = []
        for p, zz, v in hem_in:
            ring.append(Bx.add(np.array((p[0], p[1], zz)), "boxers"))
            src.append(v)
        nlegs = len(rings)
        rings.append(ring)
        for ri, (a, b) in enumerate(zip(rings, rings[1:])):
            for j in range(LIMB_N):
                k = (j + 1) % LIMB_N
                Bx.face([a[j], a[k], b[k], b[j]], "boxers_leg" + sfx if ri < nlegs - 1 else "boxers_hem" + sfx)
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
        hem_ring = set(legs[sfx][-1])
        for fi, p in enumerate(Bx.fpart):
            if p not in ("boxers_leg" + sfx, "boxers_hem" + sfx):
                continue
            th = [math.atan2(-(Q[v][1] - cy), s * (Q[v][0] - cx)) for v in Bx.faces[fi]]
            if max(th) - min(th) > math.pi:
                th = [t + math.tau if t < 0 else t for t in th]
            if p == "boxers_hem" + sfx:
                # (the turned-in hem laid below the leg's own island, not over it)
                isl[fi] = [(s * t * R, float(body_z(1080)) - (BOXER_TURN[0] if v in hem_ring else 0.0)) for t, v in zip(th, Bx.faces[fi])]
            else:
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


def paint_boxers(Bx, face_uv, placed, band_faces, G, info=None):
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
    band = np.isin(fid, list(band_faces))
    fam0 = np.array([p for p in Bx.fpart] + ["none"])[fid]
    hem_t = np.char.startswith(fam0.astype(str), "boxers_hem")
    # (seventeenth round, the third critic: "hearts cut in half, sheared into triangles and red shards at the side
    # seams, the hem and the crotch ... no heart may be cut by a seam": each heart of the staggered lattice is drawn
    # whole or not at all. It is drawn only where all of it, with a margin, lies on texels of one island that are cloth:
    # not over an island's edge (a seam), the band, the turned hem or the fly's placket)
    zfly = float(body_z(BOXER_BAND[1] + BOXER_BAND_TALL))
    cloth = hit & ~band & ~hem_t
    flyzone = hit & (pos[..., 1] < -0.04) & (np.abs(pos[..., 0]) < 0.04) & (pos[..., 2] < zfly + 0.01) & (pos[..., 2] > zfly - 0.125)
    cloth &= ~flyzone
    cloth = erode(cloth, 1)
    hem_line = float(body_z(BOXER_LOOSE_HEM)) + 0.012   # (no heart reaches the hem's last 1.2 cm, where the cloth turns)
    cover = np.zeros((size, size))
    half = int(math.ceil(wd * 0.75)) + 2
    # (each island its own lattice: of sixteen shifts of the lattice the one that fits the most whole hearts in it)
    lab = np.where(hit, np.arange(size * size).reshape(size, size), size * size)
    for _ in range(2000):
        prev = lab
        m = lab.copy()
        for sh_, axis in ((1, 0), (-1, 0), (1, 1), (-1, 1)):
            m = np.minimum(m, np.where(hit, np.roll(lab, sh_, axis), size * size))
        m = np.where(hit, m, size * size)
        flat = np.append(m.ravel(), size * size)
        lab = np.where(hit, flat[np.minimum(m, size * size)], size * size)
        if np.array_equal(lab, prev):
            break

    def fits(cyc, cxc):
        r0, r1 = int(cyc) - half, int(cyc) + half + 1
        c0, c1 = int(cxc) - half, int(cxc) + half + 1
        if r0 < 0 or c0 < 0 or r1 > size or c1 > size:
            return None
        Y, X = np.mgrid[r0:r1, c0:c1].astype(float) + 0.5
        big = heart_cover((X - cxc) / (wd / 2.3 * 1.25), (Y - cyc) / (wd / 2.3 * 1.25))
        if not cloth[r0:r1, c0:c1][big].all():
            return None
        # (and only where the picture is not stretched on him: across and down the heart, its 3D size within a third
        # of the drawn size; at the crotch the cloth's UVs shear and a whole heart came out a sliver)
        h2 = int(wd * 0.5)
        ci, ri = int(cxc), int(cyc)
        a_, b_ = pos[ri, ci - h2], pos[ri, ci + h2]
        c_, d_ = pos[ri - h2, ci], pos[ri + h2, ci]
        want = 2 * h2 / ppm
        sx_ = float(np.linalg.norm(a_ - b_)) / want
        sy_ = float(np.linalg.norm(c_ - d_)) / want
        if not (0.75 < sx_ < 1.33 and 0.75 < sy_ < 1.33 and 0.8 < sx_ / sy_ < 1.25):
            return None
        ext = np.ptp(pos[r0:r1, c0:c1][big], axis=0)
        if float(ext.max()) > 1.45 * (wd * 1.25 / ppm) or float(pos[r0:r1, c0:c1][big][:, 2].min()) < hem_line:
            return None
        return r0, r1, c0, c1, X, Y
    drawn = skipped = 0
    for isl in np.unique(lab[hit]):
        rs, cs = np.where(lab == isl)
        if len(rs) < wd * wd:
            continue
        best = []
        for oy in (0.0, 0.25, 0.5, 0.75):
            for ox in (0.0, 0.25, 0.5, 0.75):
                got = []
                for rr in range(int((rs.min() - ay) / ay) - 1, int(rs.max() / ay) + 2):
                    shift = (rr % 2) * 0.5
                    cyc = (rr + 0.5 + oy) * ay
                    if cyc < rs.min() or cyc > rs.max():
                        continue
                    for cc in range(int(cs.min() / ax) - 2, int(cs.max() / ax) + 2):
                        cxc = (cc + 0.5 + shift + ox) * ax
                        if cxc < cs.min() or cxc > cs.max():
                            continue
                        f = fits(cyc, cxc)
                        if f is not None and lab[int(cyc), int(cxc)] == isl:
                            got.append((cyc, cxc, f))
                if len(got) > len(best):
                    best = got
        for cyc, cxc, (r0, r1, c0, c1, X, Y) in best:
            acc = np.zeros(X.shape)
            for ox_, oy_ in ((-0.25, -0.25), (0.25, -0.25), (-0.25, 0.25), (0.25, 0.25)):
                acc += heart_cover((X + ox_ - cxc) / (wd / 2.3), (Y + oy_ - cyc) / (wd / 2.3)) * 0.25
            cover[r0:r1, c0:c1] = np.maximum(cover[r0:r1, c0:c1], acc)
            drawn += 1
    print("CAPTAIN boxer hearts: %d drawn whole, %d left out (they would cross a seam, the band, the hem or the fly)" % (drawn, skipped))
    rgb = rgb * (1 - cover[..., None]) + np.array(BOXER_RED) * cover[..., None]
    # the band: gathered elastic, fine upright gathers
    gathers = 0.94 + 0.06 * np.cos(xs * math.tau / max(0.006 * ppm, 2.0)) ** 2
    rgb[band] = gathers[band][:, None] * np.array((0.75, 0.75, 0.765))     # (fourteenth round: white, not grey)
    if info is not None:
        # (sixteenth round: a thick ribbed elastic, its ribs every 7 mm round him, a slight grey cast; the hem's roll a
        # little darker, the crotch's folds as shade fanning from it: the brother's paint_knit, at the captain's sizes)
        ang = np.arctan2(pos[..., 0], -(pos[..., 1] - info["cy"]))
        Rr = np.hypot(pos[..., 0], pos[..., 1] - info["cy"])
        stripes = 0.5 + 0.5 * np.cos(ang * Rr / 0.007 * math.tau)
        rgb[band] = (0.93 + 0.07 * stripes[band])[:, None] * np.array(BOXER_BAND_RGB)   # (twenty-first round: a thin clean white band, the critic: "thinner white band"; it rendered grey)
        rgb[hem_t] *= 0.9
        zc = info["zc"]
        zb_ = pos[..., 2]
        frontb = pos[..., 1] < info["cy"]
        for s in (1.0, -1.0):
            x = s * pos[..., 0]
            for a in (0.35, 0.75, 1.1):
                d = (zb_ - (zc - 0.035)) * math.cos(a) - x * math.sin(a)
                fold = hit & frontb & (x > 0.01) & (x < 0.15) & (zb_ > zc - 0.07) & (zb_ < zc + 0.07)
                g = np.exp(-(d / 0.009) ** 2)[fold]
                rgb[fold] *= (1.0 - 0.09 * g)[:, None]
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
    # The hands, painted by rule as the Twilight Princess figures' hands are (their method only, looked at and not
    # copied: one even skin tone with the forms painted in small and soft). Eighth round: the tone is his forearm's
    # (sampled just above the wrist; the sheet's few hand pixels had made them pink-grey, another man's hands); the
    # palm a little warmer; soft shade over each joint on the back (no drawn lines); the fingers' sides toward their
    # neighbours darker, most near the palm; a clean pale nail on each fingertip's back; the knuckles' tops lighter.
    hands = hit & (tex_fam == "hand")
    if HAND_FIT and "views" in HB:
        rgb = paint_hands(M, face_uv, rgb, hit, fid, pos, good, tex_fam, joints)
    elif hands.any() and joints is not None:
        fparts = np.array(list(M.fpart) + ["none"])[fid].astype(str)
        for sfx in ("_l", "_r"):
            Tb, Wd, L = (np.array(v, float) for v in joints["hand_frame" + sfx])
            W_ = np.array(joints["wrist_l"], float) * np.array((1.0 if sfx == "_l" else -1.0, 1.0, 1.0))
            mine = hands & np.char.startswith(fparts, "hand" + sfx)
            near_wrist = hit & good & (tex_fam == "arm") & (np.linalg.norm(pos - (W_ - L * 0.05), axis=-1) < 0.05)
            base_c = np.median(rgb[near_wrist], axis=0) if near_wrist.any() else np.median(rgb[hit & (tex_fam == "arm")], axis=0)
            back = (nrm * Tb).sum(-1)
            side_ = np.abs((nrm * Wd).sum(-1))
            shade = np.ones(rgb.shape[:2])
            colour = np.ones_like(rgb) * base_c
            # the palm warmer and a touch darker, the back's middle a little lighter
            warm = np.clip(-back, 0, 1)
            colour *= (1.0 + warm[..., None] * (np.array((1.03, 0.95, 0.92)) - 1.0))
            shade *= 1.0 + 0.04 * np.clip(back, 0, 1)
            for name in FINGERS + ("thumb",):
                f_ = mine & (fparts == "hand%s_%s" % (sfx, name))
                bones = [np.array(b, float) for b in joints[name + sfx]]
                up_ = Tb if name != "thumb" else np.array(joints["thumb_back" + sfx], float)
                bk = (nrm * up_).sum(-1)
                near_root = np.clip(1.0 - np.linalg.norm(pos - bones[0], axis=-1) / 0.035, 0, 1)
                gap = f_ & (side_ > 0.5)
                shade[gap] *= (0.9 - 0.08 * near_root[gap])
                for j in (1, 2):
                    a_ = bones[j + 1] - bones[j - 1]
                    a_ /= max(np.linalg.norm(a_), 1e-9)
                    t_ = ((pos - bones[j]) * a_).sum(-1)
                    soft_ = f_ & (bk > 0.0)
                    shade[soft_] *= 1.0 - 0.07 * np.exp(-(t_[soft_] / 0.003) ** 2)
                a_ = bones[3] - bones[2]
                a_ /= max(np.linalg.norm(a_), 1e-9)
                t_ = ((pos - bones[3]) * a_).sum(-1)
                nail = f_ & (bk > 0.4) & (t_ > -0.012) & (t_ < 0.003)
                colour[nail] = colour[nail] * 0.45 + np.array((0.84, 0.74, 0.69)) * 0.55
                edge_ = nail & ((np.abs(t_ + 0.012) < 0.001) | (bk < 0.5))
                shade[edge_] *= 0.9
                pad = f_ & (bk < -0.2) & (t_ > -0.015)
                colour[pad] *= np.array((1.03, 0.97, 0.95))
            for name in FINGERS:
                k0 = np.array(joints[name + sfx][0], float)
                top = mine & (back > 0.4)
                d_ = np.linalg.norm(pos - k0, axis=-1)
                shade[top] *= 1.0 + 0.05 * np.exp(-(d_[top] / 0.008) ** 2)
            rgb[mine] = colour[mine] * shade[mine][:, None]
    print("CAPTAIN paint skin: %.0f%% of its texels seen by a view" % (100.0 * (good & hit).sum() / max(hit.sum(), 1)))
    return rgb, pos, hit


def paint_head(M, face_uv, sh):
    """His head's picture (ninth round) from the bare head sheet, the true bare face: its front view wherever the
    surface faces within about 50 degrees of forward, the back view likewise behind, the side view (mirrored for his
    other side) between; the hand-over narrow, so no feature is laid down twice. The sheet's fringe of grey hair round
    his back and sides is toned down to a short grey stubble over skin (the hair itself is added on top later)."""
    P = np.array(M.P)
    tris = M.tris()
    tf = M.tri_fams()
    head_tris = [t for t, f in zip(tris, tf) if f in ("head", "nose", "ear", "neck")]
    N = normals_of(P, tris)
    pos, nrm, hit, fid = texel_geometry(M, face_uv, "face", P, N)
    size = ATLAS["face"]
    acc = np.zeros((size, size, 3))
    wsum = np.zeros((size, size))
    pix = sh.bare_pix
    mask = erode(sh.bare_mask, 2)
    gold = (pix[..., 0] - pix[..., 2] > 0.25) & (pix[..., 1] > 0.35) & (pix[..., 0] > 0.55)
    Nall = nrm.reshape(-1, 3)
    ff = np.clip(-Nall[:, 1], 0, 1)
    fb = np.clip(Nall[:, 1], 0, 1)
    wf = smooth01(0.42, 0.64, ff)
    wb = smooth01(0.42, 0.64, fb) * (1 - wf)
    share = {"bare_front": wf, "bare_back": wb, "bare_side": (1 - wf) * (1 - wb)}
    for view, mirrored in (("bare_front", False), ("bare_back", False), ("bare_side", False), ("bare_side", True)):
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
        seen = (qd <= zb[rows, cols] + 0.008) & mask[rows, cols] & (facing > 0.05) & hit.ravel() & ~gold[rows, cols]
        # (thirteenth round: the under-jaw, which faces down, is seen by no view squarely; it smeared the front view's
        # chin down into the neck: left to be filled from round it)
        seen &= ~((Nn[:, 2] < -0.55) & (Q[:, 2] < bare_z(880)))
        if view == "bare_back":
            # (tenth round: the back view ends at row 700; below it in the same columns is the from-below view, whose
            # face had been painted onto the back of his neck)
            seen &= rows < 690
        if view == "bare_side":
            # (twelfth round: the side view paints his eye open, its white showing; the front view's squint is his)
            seen &= ~((cols > 1470) & (cols < 1565) & (rows > 498) & (rows < 548))
        if view in ("bare_front", "bare_back"):
            # (their ears stand out past his head's sides: not laid on his temples; his own are painted from the side)
            seen &= ~((np.abs(cols - BARE_MID[view[5:]]) > 205) & (rows > 468) & (rows < 668))
        colour = pix[rows, cols]
        w = np.where(seen, share[view] * np.clip(facing, 0, 1) + 1e-4 * np.clip(facing, 0, 1), 0.0)
        acc += (colour * w[:, None]).reshape(size, size, 3)
        wsum += w.reshape(size, size)
    good = wsum > 0.01
    rgb = acc / np.maximum(wsum, 1e-6)[..., None]
    fam_t = np.array([part_family(p) for p in M.fpart] + ["none"])[fid]
    headish = hit & np.isin(fam_t, ("head", "neck"))
    lum, sat = rgb.mean(-1), rgb.max(-1) - rgb.min(-1)
    skin_ref = np.median(rgb[good & headish & (sat > 0.12) & (lum > 0.4)], axis=0)
    rb = bare_row(pos[..., 2])
    hairish = good & headish & (sat < 0.09) & (lum > 0.46) & (rb < 720) & (nrm[..., 1] > -0.35)
    # (sixteenth round, "the dark band across the back of the head": the back view's fringe in its own shadow, under the
    # lit tips, is darker than 0.46 and was kept as skin: a grey-green band. Behind his ears, low-saturation texels down to
    # a darker grey count as fringe too, and the mask is grown by a few texels so its soft edge goes with it)
    back_hair = good & headish & (sat < 0.115) & (lum > 0.26) & (rb > 360) & (rb < 740) & (nrm[..., 1] > 0.15)
    for _ in range(4):
        back_hair = back_hair | (np.roll(back_hair, 1, 0) | np.roll(back_hair, -1, 0) | np.roll(back_hair, 1, 1) | np.roll(back_hair, -1, 1)) & good & headish & (nrm[..., 1] > 0.1) & (rb > 340) & (rb < 760)
    hairish |= back_hair
    rs = np.random.default_rng(5)
    speck = rs.random(rgb.shape[:2])
    # (thirteenth round: the fringe toned by mixing smeared into grey streaks across the back of his head: now left
    # out and filled from the skin round it, with a faint stubble on top)
    good &= ~hairish
    rgb = fill_out(rgb, good, 200)
    rgb[hairish] = rgb[hairish] * 0.85 + skin_ref * 0.15
    rgb[hairish & (speck > 0.7)] *= 0.95
    good |= hairish
    print("CAPTAIN paint face (bare sheet): %d texels of fringe toned to stubble; skin %s" % (int(hairish.sum()), np.round(skin_ref, 3)))
    rgb = fill_out(rgb, good, 200)
    soft = blur(rgb, 3)
    rgb = np.where(good[..., None], rgb, soft)
    gb = box_blur(box_blur(good.astype(float)[..., None], 10), 10)[..., 0]
    w = np.clip(np.abs(2.0 * gb - 1.0) * 1.4, 0, 1)[..., None]
    rgb = box_blur(box_blur(rgb, 6), 6) * (1 - w) + rgb * w
    # Fourteenth round (the critic: "a light diagonal stripe runs across the back of the head ... a dark brow-like stroke
    # is projected onto the top of the scalp ... the scalp from above should be one plain skin tone"; "a white/grey
    # goatee and moustache painted round the mouth ... the bare head sheet shows only an even fine grey stubble"):
    # (1) the scalp above the forehead's wrinkles and the back of the head above the nape: the painting's own broad
    # tone only (a wide blur of itself), no strokes; (2) the beard's zone one even stipple of grey over skin.
    z = pos[..., 2]
    ny, nz = nrm[..., 1], nrm[..., 2]
    zone = lambda a, b, x: smooth01(a, b, x)
    scalp = (zone(bare_z(330), bare_z(290), z) * zone(0.45, 0.75, 1.0 - np.clip(-ny, 0, 1))
             + zone(0.1, 0.4, ny) * zone(bare_z(790), bare_z(720), z)     # (sixteenth round: down to the nape, was 700)
             + zone(bare_z(300), bare_z(272), z))
    scalp = np.clip(scalp, 0, 1) * headish
    wv = (headish & ~(scalp > 0.5)).astype(float)[..., None] + (headish & (scalp > 0.5)).astype(float)[..., None]
    acc, ws = rgb * wv, wv
    for _ in range(3):
        acc, ws = box_blur(acc, 12), box_blur(ws, 12)
    plain = acc / np.maximum(ws, 1e-6)
    sm = box_blur(box_blur(scalp[..., None], 4), 4)
    # (sixteenth round, "the thin seam line on the crown": at an island's edge the blur of the scalp's mask took in the
    # empty texels outside it and fell to half, so the edge's texels kept the unevened paint, a light line along the
    # seam between the face's island and the back's: the mask's blur divided by the blur of where the head is painted)
    hm = box_blur(box_blur(headish.astype(float)[..., None], 4), 4)
    sm = np.clip(sm / np.maximum(hm, 1e-3), 0, 1) * headish[..., None]
    rgb = rgb * (1 - sm) + plain * sm
    sat = rgb.max(-1) - rgb.min(-1)
    # (fifteenth round, the second critic: "a dark, smeared horizontal band across the back of the head and neck": the
    # beard's zone reached round the back of his neck at its rows; now the face's front and sides only)
    # (seventeenth round, the third critic: "with the dark stubble paint it reads as a goatee ... recolour the stubble
    # to a light, cool grey tint, even and short, not dark streaks": the darker texels in the shadow under his chin
    # were left out of the zone by its lightness test and stayed dark streaks; now every texel of the zone that is not
    # lip or nose red is evened, and the tint is lighter)
    beard = headish & (z < bare_z(640)) & (z > bare_z(1000)) & (sat < 0.16) & (nz < 0.6) & (ny < 0.2)
    for _ in range(3):      # (closed: the stubble's gaps and the lip's edge in)
        beard = beard | (np.roll(beard, 1, 0) & np.roll(beard, -1, 0)) | (np.roll(beard, 1, 1) & np.roll(beard, -1, 1))
    bm = box_blur(box_blur(beard.astype(float)[..., None], 3), 3)[..., 0] * headish
    skin_c = np.median(rgb[headish & ~beard & (sat > 0.12) & (z < bare_z(560)) & (z > bare_z(760))], axis=0)
    rs2 = np.random.default_rng(11)
    speck = box_blur(rs2.random(rgb.shape[:2])[..., None], 1)[..., 0]
    stub = skin_c * 0.6 + np.array((0.66, 0.66, 0.67)) * 0.4
    stub = stub[None, None, :] * (0.96 + 0.08 * speck[..., None])
    rgb = rgb * (1 - bm[..., None] * 0.9) + stub * (bm[..., None] * 0.9)
    # the brows: the sheet's are bushy white-grey; projected they came out a blue-green grey smear. The low-saturation
    # texels over each eye are made a warm white-grey, by how grey they are
    x_ = np.abs(pos[..., 0])
    browz = headish & (z < bare_z(452)) & (z > bare_z(515)) & (x_ > 0.012) & (x_ < 0.092) & (ny < -0.3)
    grey = np.clip((0.16 - sat) / 0.08, 0, 1) * browz
    grey = box_blur(grey[..., None], 1)[..., 0] * browz
    rgb = rgb * (1 - grey[..., None] * 0.8) + np.array((0.74, 0.72, 0.69)) * (grey[..., None] * 0.8)
    # (twentieth round, the fifth critic: "painted dark maroon-brown ... colour salmon/coral pink, lighter than the
    # cheeks' red"; the sheet's ball is a clear coral with a light tip). The nose's ball (in front of his cheeks' line,
    # between the brows' and the mouth's rows) recoloured to NOSE_RGB, keeping half its light and shade, soft at the edge
    nz_ = headish & (z < bare_z(545)) & (z > bare_z(668)) & (x_ < 0.05) & (pos[..., 1] < NOSE_BACK + 0.004)
    nose_k = box_blur(box_blur(nz_.astype(float)[..., None], 3), 3)[..., 0] * headish
    lum_ = rgb.mean(-1)
    shade = np.clip(lum_ / max(float(np.median(lum_[nz_])) if nz_.any() else 0.5, 1e-3), 0.75, 1.2) ** 0.5
    coral = np.array(NOSE_RGB)[None, None, :] * shade[..., None]
    rgb = rgb * (1 - nose_k[..., None] * 0.85) + coral * (nose_k[..., None] * 0.85)
    print("CAPTAIN paint face: nose recoloured coral over %d texels" % int(nz_.sum()))
    print("CAPTAIN paint face: scalp plain over %d texels; beard zone evened over %d (stubble %s)"
          % (int((scalp > 0.5).sum()), int(beard.sum()), np.round(stub.mean((0, 1)), 3)))
    print("CAPTAIN paint face: %.0f%% of its texels seen by a view" % (100.0 * (good & hit).sum() / max(hit.sum(), 1)))
    return rgb, pos, hit


# ------------------------------------------------------------------------------------------------------------------
# One skin tone (fourteenth round; the critic: "skin far too dark, grey ... match the head's tone to the body"). The
# body sheet paints its light and shade into the skin (his chest about (0.66, 0.56, 0.50), his back in shadow (0.45,
# 0.36, 0.33)) and the bare head sheet is lit brighter still (forehead (0.78, 0.65, 0.57)); laid on a lit model the
# body's picture came out shaded twice and the head a different man's colour. So the body's broad light and shade is
# divided out (what is left is the painting's detail: hair, nipples, creases, knuckles), and both pictures are brought
# to one tone, the sheets' warm light tan on his lit chest, keeping a quarter of the broad shading as painted form.
# ------------------------------------------------------------------------------------------------------------------

SKIN_TONE = (0.60, 0.49, 0.405)   # (twenty-first round: warmer and a little brighter, the brief; was 0.56, 0.465, 0.39)  # (fifteenth round: the lit render of 0.6, 0.475, 0.395 measured 0.78, 0.61, 0.51 on his chest against the sheet's 0.60, 0.56, 0.51: brought down by those ratios, a little warmer)
#    # (tried 0.70 and 0.665: rendered 0.89 on his lit chest in tests/captain_beauty.gd, far paler than the sheet)
TONE_KEEP = 0.3          # how much of the broad light and shade is kept (as a power of its ratio to the middle)


def even_tone(rgb, hit, keep=TONE_KEEP, r=14, rounds=3, target=SKIN_TONE):
    w = hit.astype(float)[..., None]
    acc, ws = rgb * w, w
    for _ in range(rounds):
        acc, ws = box_blur(acc, r), box_blur(ws, r)
    low = acc / np.maximum(ws, 1e-6)
    low = np.where(ws > 1e-3, low, rgb)
    detail = rgb / np.maximum(low, 1e-3)
    lum = low.mean(-1)
    mid = float(np.median(lum[hit]))
    form = (np.clip(lum / mid, 0.3, 2.0) ** keep)[..., None]
    out = np.clip(detail * np.array(target) * form, 0, 1)
    return np.where(hit[..., None], out, rgb)


def heal_seams(M, face_uv, picture, rgb, pos, hit, reach=0.02, cell=0.012):
    """Where a UV island's edge meets another's (the critic: "a light diagonal stripe runs across the back of the
    head"), the two sides were painted apart and their edges differ. Near every seam (within `reach` on him, in 3D)
    each texel is drawn toward one colour field made in 3D from both sides at once (the mean colour of small cubes,
    each with its 26 neighbours), so both sides of the seam agree."""
    P = np.array(M.P)
    first = {}
    seam = []
    for fi, f in enumerate(M.faces):
        if fi not in face_uv or face_uv[fi][0] != picture:
            continue
        uvs = face_uv[fi][1]
        for i in range(len(f)):
            a, b = f[i], f[(i + 1) % len(f)]
            ua, ub = np.array(uvs[i]), np.array(uvs[(i + 1) % len(f)])
            key = (min(a, b), max(a, b))
            here = (ua, ub) if a < b else (ub, ua)
            if key in first:
                o = first[key]
                if np.abs(o[0] - here[0]).max() > 1e-4 or np.abs(o[1] - here[1]).max() > 1e-4:
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
    # the colour field: every painted texel near the seams, by cube
    allr, allc = np.where(cand)
    q = np.floor(pos[allr, allc] / cell).astype(np.int64) + (1 << 18)
    code = q[:, 0] + (q[:, 1] << 20) + (q[:, 2] << 40)
    uniq, inv = np.unique(code, return_inverse=True)
    sums = np.zeros((len(uniq), 3))
    cnt = np.zeros(len(uniq))
    np.add.at(sums, inv, rgb[allr, allc])
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
    pos_code = {}
    qn = np.floor(pos[rr, cc] / cell).astype(np.int64) + (1 << 18)
    cn = qn[:, 0] + (qn[:, 1] << 20) + (qn[:, 2] << 40)
    j = np.clip(np.searchsorted(uniq, cn), 0, len(uniq) - 1)
    w = (1.0 - smooth01(reach * 0.35, reach, dist))[:, None]
    out = rgb.copy()
    out[rr, cc] = rgb[rr, cc] * (1 - w) + field[j] * w
    print("CAPTAIN seams healed (%s): %d seam edges, %d texels drawn together" % (picture, len(seam), len(rr)))
    return out


# Sixteenth round (the critic: "the chest hair is a thin, brownish-grey wisp ... the concept has a dense silver-grey mat
# ... the same goes for the back pelt, the forearms and the leg hair"). even_tone divides each texel by the broad tone
# round it, and where the sheet's hair covers a whole chest the broad tone is the hair's own, so it came out faint and
# tan. The hair is found in the picture as painted (before the toning: greyer than the skin round it, not darker by
# much, so not ink) and laid back over the toned skin as silver-grey strokes, keeping the painting's own light and
# dark within them (roots darker).
BODY_HAIR = (0.03, 0.035, 0.62)            # how much greyer than the skin round it (start, full); the most it covers
# (seventeenth round, the third critic: "a chalk-white plume ... an ash grey-brown mat ... softer": darker ash grey, laid
# on thinner, and its strokes softened by a light blur of the cover)
HAIR_SILVER = (0.55, 0.53, 0.50)


def body_hair(rgb, raw, hit, pos=None):
    rb = raw[..., 0] - raw[..., 2]
    lum = raw.mean(-1)
    w = hit.astype(float)[..., None]
    acc, ws = raw * w, w
    for _ in range(2):
        acc, ws = box_blur(acc, 10), box_blur(ws, 10)
    local = acc / np.maximum(ws, 1e-6)
    lrb = local[..., 0] - local[..., 2]
    llum = local.mean(-1)
    # (the broad tone of a hairy chest is itself greyish: the skin's own red taken from the picture's skin as a whole)
    skin_rb = float(np.percentile(rb[hit], 70))
    grey = np.maximum(lrb - rb, skin_rb - rb - 0.02)
    a = np.clip((grey - BODY_HAIR[0]) / BODY_HAIR[1], 0, 1) * np.clip((lum - llum + 0.06) / 0.06, 0, 1) * hit
    a = np.clip(a, 0, 1)
    a = box_blur(a[..., None], 1)[..., 0] * hit * BODY_HAIR[2]
    if pos is not None:
        # (not on the belly just over the band: the sheet's grey waistband lay there and came out as a white patch)
        a = a * (1.0 - smooth01(float(body_z(836.0)), float(body_z(852.0)), pos[..., 2]) * (pos[..., 1] < 0.0) * (pos[..., 2] > float(body_z(900.0))))
    shade = np.clip(0.8 + 1.6 * (lum - llum), 0.6, 1.15)[..., None]
    hair = np.array(HAIR_SILVER) * shade
    out = rgb * (1 - a[..., None]) + hair * a[..., None]
    print("CAPTAIN body hair laid back: %d texels over a half" % int((a > 0.42).sum()))
    return np.where(hit[..., None], out, rgb)


# Twenty-first round (the user: "captian should have bushy chest hair"; the critic: "chest/back hair as directional strokes
# following the growth (down the sternum, fanning on the pecs)"): over the smeared grey taken from the sheet, strokes are
# drawn in the picture: seeds over the chest, belly and forearms, each a short curved line stepped along a growth field
# given in world directions (down the sternum's middle, out and down across the pecs, down the belly toward the navel,
# along the forearm toward the hand), turned into the picture's own directions through each texel's world position.
HAIR_STROKES = (int(arg("--hair-strokes", "5200")), 0.011, 0.55)   # how many, metres long, how much they cover
HAIR_DARK = (0.30, 0.29, 0.28)     # the darker strokes among the silver (a mix of grey and dark, as the sheet draws)


def hair_strokes(rgb, hit, pos, joints=None, seed=7):
    H, W = hit.shape
    rng = np.random.default_rng(seed)
    x, y, z = pos[..., 0], pos[..., 1], pos[..., 2]
    zc0, zc1 = float(body_z(470.0)), float(body_z(835.0))   # the chest's top (under the collar bones) to the band
    chest = hit & (y < -0.02) & (z < zc0) & (z > zc1 + 0.02)
    dens = chest * (1.0 - 0.6 * smooth01(0.05, 0.13, np.abs(x)))
    # the forearms (back of the forearm, toward the hand)
    fore = np.zeros_like(hit)
    if joints is not None:
        for sfx in ("_l", "_r"):
            sg_ = 1.0 if sfx == "_l" else -1.0
            E_ = np.array(joints["elbow_l"], float) * np.array((sg_, 1.0, 1.0))
            W_ = np.array(joints["wrist_l"], float) * np.array((sg_, 1.0, 1.0))
            a_ = W_ - E_
            L_ = float(np.linalg.norm(a_))
            a_ /= L_
            t_ = ((pos - E_) * a_).sum(-1)
            r_ = np.linalg.norm((pos - E_) - t_[..., None] * a_, axis=-1)
            fore |= hit & (t_ > 0.15 * L_) & (t_ < 0.95 * L_) & (r_ < 0.08)
    dens = np.maximum(dens, 0.7 * fore)

    def field(p):
        px, py, pz = p
        if abs(px) > 0.2 or pz < 1.0:     # an arm: along it, toward the hand
            if joints is not None:
                d = (np.array(joints["wrist_l"], float) - np.array(joints["elbow_l"], float)) * np.array((1.0 if px > 0 else -1.0, 1.0, 1.0))
                return d / np.linalg.norm(d)
        out_ = np.sign(px) * np.clip(abs(px) / 0.09, 0, 1)
        high = smooth01(zc0 - 0.16, zc0 - 0.04, pz)          # the pecs: out and down; lower: down toward the middle
        d = np.array((out_ * 0.8 * high - 0.35 * np.sign(px) * (1 - high) * np.clip(abs(px) / 0.06, 0, 1), 0.0, -1.0))
        return d / np.linalg.norm(d)

    # world position's derivatives in the picture (per texel), for turning a world direction into a picture direction
    gu = np.zeros_like(pos); gv = np.zeros_like(pos)
    gu[:, 1:-1] = (pos[:, 2:] - pos[:, :-2]) * 0.5
    gv[1:-1, :] = (pos[2:, :] - pos[:-2, :]) * 0.5
    ok = hit.copy()
    ok[:, 1:-1] &= hit[:, 2:] & hit[:, :-2]
    ok[1:-1, :] &= hit[2:, :] & hit[:-2, :]
    cand = np.argwhere((dens > 0) & ok)
    if len(cand) == 0:
        return rgb
    pick = cand[rng.choice(len(cand), size=min(HAIR_STROKES[0], len(cand) * 4), p=None)]
    pick = pick[rng.random(len(pick)) < dens[pick[:, 0], pick[:, 1]]]
    cover = np.zeros((H, W))
    dark = np.zeros((H, W))
    drawn = 0
    for r0, c0 in pick:
        r, c = float(r0), float(c0)
        isdark = rng.random() < 0.35
        steps = 0
        left = HAIR_STROKES[1] * (0.6 + 0.8 * rng.random())
        wob = rng.normal(0, 0.35)
        while left > 0 and steps < 40:
            ri, ci = int(round(r)), int(round(c))
            if ri < 1 or ci < 1 or ri >= H - 1 or ci >= W - 1 or not ok[ri, ci]:
                break
            d = field(pos[ri, ci])
            A = np.stack([gu[ri, ci], gv[ri, ci]], 1)          # world metres a texel step along columns, rows
            AtA = A.T @ A
            if abs(np.linalg.det(AtA)) < 1e-18:
                break
            t = np.linalg.solve(AtA, A.T @ d)
            n_ = float(np.hypot(*t))
            if n_ < 1e-9:
                break
            tc, tr = t[0] / n_, t[1] / n_
            tc, tr = tc - wob * tr * 0.3, tr + wob * tc * 0.3
            a_ = 1.0 - steps / 40.0
            cover[ri, ci] = max(cover[ri, ci], a_)
            if isdark:
                dark[ri, ci] = 1.0
            step_m = float(np.linalg.norm(A @ np.array((tc, tr))))
            left -= max(step_m, 1e-4)
            c += tc
            r += tr
            steps += 1
        drawn += 1
    a = np.clip(box_blur(cover[..., None], 1)[..., 0] * 1.6, 0, 1) * HAIR_STROKES[2] * hit
    col = np.where(dark[..., None] > 0, np.array(HAIR_DARK), np.array(HAIR_SILVER))
    out = rgb * (1 - a[..., None]) + col * a[..., None]
    print("CAPTAIN hair strokes: %d drawn over %d texels" % (drawn, int((a > 0.2).sum())))
    return np.where(hit[..., None], out, rgb)


RED_ACCENT = (0.80, 0.42, 0.36)   # (twenty-first round, the critic: "warm red to ears, knuckles and knees", as the sheet)


def red_accents(M, rgb, hit, pos, joints, ears=False):
    """Soft warm red where the sheet's skin flushes: knees, knuckles, elbows (the skin), the ears (the face)."""
    spots = []
    if ears:
        k = hit & (np.abs(pos[..., 0]) > 0.13) & (pos[..., 2] > Z_EYE - 0.075) & (pos[..., 2] < Z_EYE + 0.03) & (pos[..., 1] > -0.045) & (pos[..., 1] < 0.03)
        a = k * 0.45
    else:
        a = np.zeros(hit.shape)
        for sfx, sg in (("_l", 1.0), ("_r", -1.0)):
            kn = np.array(joints["knee" + sfx], float) + np.array((0.0, -0.05, 0.0))
            spots.append((kn, 0.05, 0.35))
            spots.append((np.array(joints["knuckles" + sfx], float), 0.035, 0.4))
            spots.append((np.array(joints["elbow_l"], float) * np.array((sg, 1.0, 1.0)) + np.array((0.0, 0.04, 0.0)), 0.04, 0.25))
        for c, r, s in spots:
            d = np.linalg.norm(pos - c, axis=-1)
            a = np.maximum(a, s * np.exp(-(d / r) ** 2))
        a = a * hit
    lum = rgb.mean(-1, keepdims=True)
    red = np.array(RED_ACCENT) * lum / max(float(np.mean(RED_ACCENT)), 1e-3)
    out = rgb * (1 - a[..., None]) + red * a[..., None]
    print("CAPTAIN red accents%s: %d texels" % (" (ears)" if ears else "", int((a > 0.1).sum())))
    return out


def match_tone(rgb, sel, target=SKIN_TONE):
    """The whole picture scaled channel by channel so its skin's middle tone is the target's."""
    med = np.median(rgb[sel], axis=0)
    return np.clip(rgb * (np.array(target) / np.maximum(med, 1e-3)), 0, 1), med


# ------------------------------------------------------------------------------------------------------------------
# His tattoos, movable (the user: "the tattoos need to be moveable so we can postion them eventually"; the brother's
# scheme, tools/build_brother.py): each lifted from the body sheet into its own picture (ink only, on a clear ground:
# textures/tattoos/captain_<name>.png); a table (textures/captain/captain_tattoos.json) of where each sits (the skin
# layout's island, the middle's place in it from 0 to 1, its width on him in metres, its turn and mirror); the overlay
# (textures/captain/captain_tattoo_overlay.png) composited from the table and drawn as a see-through layer,
# `captain_ink`, over the skin, which is painted clean under them. "keep": true in the table keeps it as it is.
# The boxes are measured on the body sheet (2752 x 1536), each in the view that sees it most squarely; the back view's
# ship is on the viewer's left there, his right shoulder blade.
# ------------------------------------------------------------------------------------------------------------------

TATTOO_DIR = os.path.join(ROOT, "textures", "tattoos")
TATTOOS = (
    ("rose_shoulder", "front", (380, 442), (458, 532)),
    ("arm_badge", "front", (328, 402), (566, 644)),
    ("anchor_forearm", "front", (212, 282), (688, 802)),
    ("swallow_forearm", "front", (280, 352), (716, 802)),
    ("chest_anchor", "front", (712, 822), (478, 568)),
    ("ship_shoulder", "front", (886, 962), (438, 542)),
    ("anchor_arm", "front", (902, 992), (566, 662)),
    ("swallows_forearm", "front", (976, 1082), (698, 802)),
    ("ship_wrist", "front", (1066, 1132), (758, 822)),
    ("ship_back", "back", (2030, 2172), (462, 598)),
    ("swallow_heart", "back", (2272, 2402), (452, 608)),
    ("compass", "back", (2452, 2528), (466, 562)),
    ("squid_back", "back", (2096, 2184), (656, 724)),
    ("arm_back_l", "back", (1866, 1962), (556, 662)),
    ("forearm_back_r", "back", (1776, 1862), (716, 818)),     # (seventeenth round: to 818, was 852: the box took the wrist's shade as a dark band)
    ("forearm_back_l", "back", (2548, 2642), (726, 818)),
)
INK = (0.22, 0.28, 0.27)      # (seventeenth round, the third critic: "thin, crisp, grey-green-blue as on the sheet": the sheet's faded green-grey)
TATTOO_LINE = (0.022, 0.06)   # how much darker than the skin round it a texel must be to count as a line (start, full)
TATTOO_STRENGTH = 0.74        # the lines' opacity over the skin (faded into it; sixteenth round, was 0.72)
TATTOO_RES = 2                 # (twenty-first round) the overlay picture this many times the skin picture's size
TATTOO_CRISP = (0.3, 0.55)     # (twenty-first round) the lifted cover made crisp: from this to this is the edge
TATTOO_FILL = 0.25           # the designs' fills against their lines (sixteenth round)
TATTOO_GROW = 0               # pixels the lines are thickened by (sixteenth round)


# (eighteenth round, the coordinator: "TATTOOS REGRESSED: they are thin scratchy scribbles again ... The user must be
# able to READ each design at game distance ... a faithful, legible copy of the sheet's design: clean lines of the
# sheet's weight, the sheet's fills, faded blue-grey-green ink; fix the dark smudge bands"). The last rounds took only
# the lines (darker than the skin round them) and a weak share of the fill: the sheet's designs are slate FILLS inside
# darker outlines, so what came out was the outlines' broken edges. Now the design is UNMIXED from the sheet: each
# pixel's step from the skin toward the sheet's own darkest ink (TATTOO_SHEET_INK, measured: (0.35..0.40) grey-slate
# in the anchor, swallows and ship boxes against skin (0.67, 0.59, 0.53)) is its ink's cover, so fills come out as the
# sheet paints them and lines darker; only where the pixel is also cooler than the skin (the ink is grey-blue, the
# sheet's shading is warm brown: that is what drew the dark bands along the forearm's edge and across the wrist); the
# skin taken as a wide local median of the box's warm pixels, so the arm's shading is not counted. Drawn in one ink,
# TATTOO_INK (the sheet's ink brought down by the game skin's tone against the sheet's), with a soft clean edge.
TATTOO_SHEET_INK = (0.33, 0.36, 0.36)
TATTOO_INK = (0.20, 0.25, 0.26)      # in the game's darker skin (SKIN_TONE against the sheet's 0.67, 0.59, 0.53)
TATTOO_COVER = (0.12, 0.62)          # the unmixed share that starts to show, that is whole
TATTOO_COOL = (0.045, 0.085)         # red less blue: at or under the first all ink may be, over the second none


def lift_tattoo(sh, c0, c1, r0, r1, pix_all=None, mask_all=None):
    """The ink in a box of the sheet as an RGBA picture (rows top down), unmixed from the skin round it."""
    pix_all = sh.body_pix if pix_all is None else pix_all
    pix = pix_all[r0:r1, c0:c1].copy()
    mask = (sh.body_mask if mask_all is None else mask_all)[r0:r1, c0:c1]
    rb = pix[..., 0] - pix[..., 2]
    lum = pix.mean(-1)
    warm = mask & (rb > np.percentile(rb[mask], 55) - 0.01)
    # the skin under each pixel: the warm pixels' wide local mean (the arm's light and shade kept out of the ink)
    wf = warm.astype(np.float32)
    S = box_blur(pix * wf[..., None], 9) / np.maximum(box_blur(wf[..., None], 9), 1e-6)
    S = np.where((box_blur(wf[..., None], 9) > 0.05), S, np.median(pix[warm], 0))
    K = np.array(TATTOO_SHEET_INK, np.float32)
    d = S - K
    cover = ((S - pix) * d).sum(-1) / np.maximum((d * d).sum(-1), 1e-6)
    # (measured: the ink's red less blue is 0.03 or under, lit skin's 0.13 to 0.16, the arm's shade 0.08 to 0.11)
    a = smooth01(TATTOO_COVER[0], TATTOO_COVER[1], cover) * (1.0 - smooth01(TATTOO_COOL[0], TATTOO_COOL[1], rb))
    a = box_blur(a[..., None].astype(np.float32), 1)[..., 0]
    a = smooth01(0.15, 0.5, a) * np.clip(a * 1.3, 0, 1)
    # specks (ink with almost no ink round it) dropped; outside him nothing
    near = box_blur((a > 0.3).astype(np.float32)[..., None], 3)[..., 0]
    a[near < 0.1] = 0.0
    a[~mask] = 0.0
    a = np.clip(a, 0, 1) * TATTOO_STRENGTH
    ink = np.broadcast_to(np.array(TATTOO_INK, np.float32), pix.shape).copy()
    # (the darkest parts, the outlines, a little darker than the fills)
    ink *= (1.0 - 0.25 * smooth01(0.7, 1.0, cover))[..., None]
    return np.concatenate([ink, a[..., None]], 2).astype(np.float32)


# (eighteenth round, the critic: "the concept has an anchor on the back of his left hand. It is missing"): lifted from
# the hands sheet's back view (its box, pixels), placed on the back of his left hand HAND_ANCHOR_AT metres up from the
# hand's lowest knuckles toward the wrist, HAND_ANCHOR_SIZE tall, its crown toward the wrist (as the sheet draws it)
HAND_ANCHOR_BOX = ((418, 580), (440, 572))
HAND_ANCHOR_AT = 0.55              # share of the way from the wrist's ring down to the knuckles
HAND_ANCHOR_SIZE = 0.034           # metres tall


def hand_anchor(M, face_uv, face_island, pictures):
    pix = load_picture(HANDS_SHEET)
    (c0, c1), (r0, r1) = HAND_ANCHOR_BOX
    mask = np.zeros(pix.shape[:2], bool)
    lum = pix.mean(-1)
    mask[r0:r1, c0:c1] = (pix[r0:r1, c0:c1, 0] - pix[r0:r1, c0:c1, 2] > 0.02) | (lum[r0:r1, c0:c1] < 0.6)
    rgba = lift_tattoo(None, c0, c1, r0, r1, pix, mask)
    # the sheet draws it leaning; the box as is (the turn below sets its crown toward the wrist)
    pictures["hand_anchor"] = rgba
    save_rgba(os.path.join(TATTOO_DIR, "captain_hand_anchor.png"), rgba)
    P = np.array(M.P)
    parts = np.array(M.part)
    arm = P[parts == "arm_l"]
    hand_ids = np.where(parts == "hand_l")[0]
    if len(arm) == 0 or len(hand_ids) == 0:
        return None
    wz = float(arm[:, 2].min())
    kz = float(np.percentile(P[np.char.startswith(parts.astype(str), "hand_l_")][:, 2], 85)) if any(np.char.startswith(parts.astype(str), "hand_l_")) else wz - 0.1
    tz = wz + (kz - wz) * HAND_ANCHOR_AT
    tris = M.tris()
    tface = tri_faces(M)
    out = np.array((0.85, -0.25, 0.0))
    out /= np.linalg.norm(out)
    best = None
    for ti, t in enumerate(tris):
        fi = tface[ti]
        if M.fpart[fi] != "hand_l" or fi not in face_uv or face_uv[fi][0] != "skin":
            continue
        a, b, c = P[list(t)]
        n = np.cross(b - a, c - a)
        n /= max(np.linalg.norm(n), 1e-12)
        cen = (a + b + c) / 3.0
        score = abs(cen[2] - tz) * 20.0 - float(np.dot(n, out))
        if best is None or score < best[0]:
            best = (score, ti, fi, cen)
    if best is None:
        return None
    _, ti, fi, cen = best
    t = tris[ti]
    f = M.faces[fi]
    pic, uvs = face_uv[fi]
    U = np.array([uvs[f.index(v)] for v in t], float)
    X = P[list(t)]
    # the face's map from its plane to the picture: uv = U0 + A (p - X0)
    e1, e2 = X[1] - X[0], X[2] - X[0]
    G = np.array([[e1 @ e1, e1 @ e2], [e1 @ e2, e2 @ e2]])
    def to_uv(p):
        r = p - X[0]
        s, w = np.linalg.solve(G, np.array([r @ e1, r @ e2]))
        return U[0] + s * (U[1] - U[0]) + w * (U[2] - U[0])
    uv = to_uv(cen)
    upd = np.array((0.0, 0.0, 1.0))         # toward the wrist
    uv_up = to_uv(cen + upd * 0.01)
    isl = [n_ for n_, (p_, a0, b0, sc, w, h) in face_island.items()
           if p_ == pic and a0 - 1e-6 <= uv[0] <= a0 + w * sc + 1e-6 and b0 - 1e-6 <= uv[1] <= b0 + h * sc + 1e-6]
    if not isl:
        print("CAPTAIN hand anchor: no island")
        return None
    _, a0, b0, sc, w, h = face_island[isl[0]]
    au = (uv_up - uv) / 0.01                # atlas units a metre, toward the wrist
    per_m = float(np.linalg.norm(au))
    ph, pw = rgba.shape[:2]
    width_m = HAND_ANCHOR_SIZE * pw / ph
    turn = math.degrees(math.atan2(au[1], au[0])) - 90.0
    print("CAPTAIN hand anchor: on %s at z %.3f (wrist %.3f), %.1f cm wide" % (isl[0], cen[2], wz, 100 * width_m))
    return {"picture": "captain_hand_anchor", "part": isl[0], "x": round(float((uv[0] - a0) / (w * sc)), 4),
            "y": round(float((uv[1] - b0) / (h * sc)), 4), "size": round(float(width_m * per_m / sc), 4),
            "turn": round(turn, 1), "mirror": False, "strength": 1.0}


def tri_faces(M):
    out = []
    for fi, f in enumerate(M.faces):
        out += [fi] * (len(f) - 2)
    return out


def uv_at(M, face_uv, view, col, row):
    """The skin picture's place (face, picture name, uv) of his surface that the sheet's pixel shows in a view."""
    P = np.array(M.P)
    tris = M.tris()
    tfam = M.tri_fams()
    tface = tri_faces(M)
    keep = [i for i, f in enumerate(tfam) if f in ("arm", "hand", "torso", "shoulder")]
    P2, dep = project(view, P)
    best = None
    for i in keep:
        t = tris[i]
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
            best = (d, i, (w0, w1, w2))
    if best is None:
        return None
    _, ti, (w0, w1, w2) = best
    fi = tface[ti]
    f = M.faces[fi]
    if fi not in face_uv:
        return None
    pic, uvs = face_uv[fi]
    uv = sum(np.array(uvs[f.index(v)]) * wt for v, wt in zip(tris[ti], (w0, w1, w2)))
    return fi, pic, uv


def save_rgba(path, rgba):
    rgba = np.clip(np.asarray(rgba, dtype=np.float32), 0, 1)
    h, w = rgba.shape[:2]
    img = bpy.data.images.new(os.path.basename(path), w, h, alpha=True)
    img.pixels.foreach_set(rgba[::-1].ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


# Twenty-second round (the sixth critic: "the tattoos are solid, dark navy, blurry silhouettes (the swallows and anchor
# are blobs) ... draw them as line art with outlines"). The simple sailor designs are DRAWN by rule (a paint
# adjustment): each design's picture, lifted from the sheet as before, is replaced by line art of the same size, so
# its place, size and turn in the movable table are the sheet's. Slate blue-black lines with a lighter see-through
# fill. The others (rose, badge, squid, the back sleeves) stay lifted. --lifted-tattoos takes the drawn ones back.
TATTOO_DRAWN = "--lifted-tattoos" not in ARGS
TATTOO_LINE_RGB = (0.17, 0.21, 0.27)
TATTOO_FILL_RGB = (0.36, 0.43, 0.52)
TATTOO_LINE_A = (0.82, 0.32)         # the lines' opacity, the fills'
TATTOO_LINE_W = 0.045                # half the line's width, in the design's units (its box is -1..1)


def _arc(cx, cy, r, a0, a1, n=24, ry=None):
    t = np.radians(np.linspace(a0, a1, n))
    return [(cx + r * math.cos(v), cy + (ry or r) * math.sin(v)) for v in t]


def _heart(cx, cy, s, n=40):
    t = np.linspace(0, 2 * math.pi, n)
    x = 16 * np.sin(t) ** 3
    y = -(13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t))
    return [(cx + s * a / 17.0, cy + s * b / 17.0) for a, b in zip(x, y)]


def _swallow(cx, cy, s, flip=False):
    """A swallow flying right (left if flip), as polygons: wings, tail, body."""
    f = -1.0 if flip else 1.0
    P_ = lambda pts: [(cx + f * s * x, cy + s * y) for x, y in pts]
    body = P_([(0.55, -0.08), (0.4, -0.2), (0.0, -0.15), (-0.35, -0.02), (-0.95, -0.38), (-0.62, 0.02),
               (-0.95, 0.32), (-0.3, 0.12), (0.1, 0.16), (0.42, 0.06)])
    wing = P_([(0.2, -0.14), (0.0, -0.55), (-0.3, -0.85), (-0.55, -0.98), (-0.2, -0.55), (-0.08, -0.14)])
    wing2 = P_([(0.15, 0.12), (-0.05, 0.45), (-0.4, 0.78), (-0.12, 0.42), (-0.05, 0.12)])
    beak = P_([(0.55, -0.08), (0.72, -0.04), (0.53, 0.0)])
    return [("fill", body), ("fill", wing), ("fill", wing2), ("line", beak + [beak[0]]),
            ("dot", P_([(0.38, -0.08)])[0], 0.06 * s)]


def _anchor(cx, cy, s):
    sh_ = [(cx, cy - 0.62 * s), (cx, cy + 0.72 * s)]
    ring = _arc(cx, cy - 0.78 * s, 0.15 * s, 0, 360)
    stock = [(cx - 0.38 * s, cy - 0.5 * s), (cx + 0.38 * s, cy - 0.5 * s)]
    arms = _arc(cx, cy + 0.1 * s, 0.62 * s, 15, 165)
    l, r = arms[-1], arms[0]
    fl = [(l[0] - 0.14 * s, l[1] - 0.02 * s), (l[0] + 0.02 * s, l[1] - 0.22 * s), (l[0] + 0.1 * s, l[1] + 0.02 * s)]
    fr = [(r[0] + 0.14 * s, r[1] - 0.02 * s), (r[0] - 0.02 * s, r[1] - 0.22 * s), (r[0] - 0.1 * s, r[1] + 0.02 * s)]
    rope = [(cx + 0.22 * s * math.sin(t * 2.6), cy + (-0.55 + t * 0.35) * s) for t in np.linspace(0, 3, 30)]
    return [("line", sh_), ("line", ring), ("line", stock), ("line", arms), ("fill", fl), ("fill", fr),
            ("thin", rope)]


def _ship(cx, cy, s):
    hull = [(cx - 0.85 * s, cy + 0.25 * s), (cx + 0.9 * s, cy + 0.25 * s), (cx + 0.62 * s, cy + 0.55 * s),
            (cx - 0.6 * s, cy + 0.55 * s)]
    out = [("fill", hull)]
    for mx, top, w in ((-0.35, -0.8, 0.32), (0.25, -0.95, 0.36)):
        x = cx + mx * s
        out.append(("line", [(x, cy + 0.25 * s), (x, cy + top * s)]))
        y0, y1 = top + 0.15, top + 0.85
        # one square sail a mast, its foot bellied
        sail = [(x - w * s, cy + y0 * s), (x + w * s, cy + y0 * s)] + \
               [(x + w * 1.1 * s * (1 - 2 * t), cy + (y1 + 0.08 * math.sin(math.pi * t)) * s) for t in np.linspace(0, 1, 8)]
        out.append(("fill", sail))
    out.append(("line", [(cx + 0.9 * s, cy + 0.25 * s), (cx + 0.25 * s, cy - 0.95 * s)]))
    out.append(("thin", [(cx + (-1.0 + 2.0 * t) * s, cy + (0.68 + 0.06 * math.sin(t * 25)) * s) for t in np.linspace(0, 1, 40)]))
    return out


def _compass(cx, cy, s):
    out = [("line", _arc(cx, cy, 0.9 * s, 0, 360, 48)), ("thin", _arc(cx, cy, 0.72 * s, 0, 360, 40))]
    for k in range(8):
        a = math.radians(k * 45 - 90)
        L = (0.85 if k % 2 == 0 else 0.5) * s
        tip = (cx + L * math.cos(a), cy + L * math.sin(a))
        sa, ca = math.sin(a), math.cos(a)
        w = 0.13 * s
        out.append(("fill", [(cx - sa * w, cy + ca * w), tip, (cx + sa * w, cy - ca * w)]))
    out.append(("dot", (cx, cy), 0.07 * s))
    return out


TATTOO_DESIGNS = {
    "chest_anchor": [("anchor", 0.0, 0.0, 0.95)],
    "anchor_forearm": [("anchor", 0.0, 0.0, 0.95)],
    "anchor_arm": [("anchor", 0.0, 0.0, 0.95)],
    "hand_anchor": [("anchor", 0.0, 0.0, 0.95)],
    "swallow_forearm": [("swallow", 0.0, 0.0, 0.9, False)],
    "swallows_forearm": [("swallow", -0.25, -0.35, 0.6, False), ("swallow", 0.3, 0.4, 0.55, True)],
    "swallow_heart": [("heart", -0.1, 0.15, 0.62), ("swallow", 0.35, -0.55, 0.45, True), ("swallow", -0.45, -0.55, 0.42, False)],
    "compass": [("compass", 0.0, 0.0, 0.95)],
    "ship_shoulder": [("ship", 0.0, 0.0, 0.92)],
    "ship_back": [("ship", 0.0, 0.0, 0.92)],
    "ship_wrist": [("ship", 0.0, 0.0, 0.92)],
}


def _seg_dist(X, Y, pts):
    d = np.full(X.shape, 1e9)
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        dx, dy = x1 - x0, y1 - y0
        L = dx * dx + dy * dy
        t = np.clip(((X - x0) * dx + (Y - y0) * dy) / L, 0, 1) if L > 0 else 0.0
        d = np.minimum(d, np.hypot(X - (x0 + t * dx), Y - (y0 + t * dy)))
    return d


def _inside(X, Y, poly):
    ins = np.zeros(X.shape, bool)
    n = len(poly)
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        c = ((y0 > Y) != (y1 > Y)) & (X < (x1 - x0) * (Y - y0) / ((y1 - y0) if y1 != y0 else 1e-9) + x0)
        ins ^= c
    return ins


def draw_tattoo(design, shape):
    """An RGBA picture (rows top down) of the given shape: the design drawn as line art in a -1..1 box fitted to it."""
    h, w = shape
    k = 4                                   # drawn at 4x and brought down: smooth edges
    H, W = h * k, w * k
    sc = min(W, H) / 2.0
    Y, X = np.mgrid[0:H, 0:W].astype(np.float32)
    X = (X + 0.5 - W / 2.0) / sc
    Y = (Y + 0.5 - H / 2.0) / sc
    line = np.zeros((H, W), np.float32)
    fill = np.zeros((H, W), np.float32)
    hw = TATTOO_LINE_W
    aa = 1.0 / sc
    for item in design:
        kind, cx, cy, s = item[:4]
        if kind == "anchor":
            parts = _anchor(cx, cy, s)
        elif kind == "swallow":
            parts = _swallow(cx, cy, s, item[4])
        elif kind == "heart":
            parts = [("fill", _heart(cx, cy, s))]
        elif kind == "compass":
            parts = _compass(cx, cy, s)
        else:
            parts = _ship(cx, cy, s)
        for p in parts:
            if p[0] == "dot":
                (px, py), r = p[1], p[2]
                line = np.maximum(line, np.clip((r - np.hypot(X - px, Y - py)) / aa + 0.5, 0, 1))
                continue
            pts = p[1]
            closed = p[0] == "fill"
            ring = pts + [pts[0]] if closed else pts
            d = _seg_dist(X, Y, ring)
            width = hw * (0.55 if p[0] == "thin" else 1.0) * (0.85 if s < 0.7 else 1.0)
            line = np.maximum(line, np.clip((width - d) / aa + 0.5, 0, 1))
            if closed:
                fill = np.maximum(fill, _inside(X, Y, pts).astype(np.float32))
    line = line.reshape(h, k, w, k).mean(axis=(1, 3))
    fill = fill.reshape(h, k, w, k).mean(axis=(1, 3))
    a = np.maximum(line * TATTOO_LINE_A[0], fill * TATTOO_LINE_A[1])
    rgb = np.array(TATTOO_FILL_RGB, np.float32) * (1 - line[..., None]) + np.array(TATTOO_LINE_RGB, np.float32) * line[..., None]
    return np.concatenate([rgb, a[..., None]], 2).astype(np.float32)


def lay_tattoos(M, face_uv, placed, sh):
    os.makedirs(TATTOO_DIR, exist_ok=True)
    table = os.path.join(TEX, "captain_tattoos.json")
    old = None
    if os.path.exists(table):
        with open(table) as f:
            old = json.load(f)
    pictures = {}
    rows = []
    face_island = {name: (pic, u0, v0, sc, w, h) for name, (pic, u0, v0, sc, (w, h)) in placed.items()}
    for name, view, (c0, c1), (r0, r1) in TATTOOS:
        rgba = lift_tattoo(sh, c0, c1, r0, r1)
        pictures[name] = rgba
        save_rgba(os.path.join(TATTOO_DIR, "captain_%s.png" % name), rgba)
        cx, cy = (c0 + c1) / 2.0, (r0 + r1) / 2.0
        here = uv_at(M, face_uv, view, cx, cy)
        right = uv_at(M, face_uv, view, cx + 6, cy)
        up = uv_at(M, face_uv, view, cx, cy - 6)
        if not here or not right or not up or here[1] != "skin":
            print("CAPTAIN tattoo %s: not on him" % name)
            continue
        fi, pic, uv = here
        isl = [n for n, (p_, a0, b0, sc, w, h) in face_island.items()
               if p_ == pic and a0 - 1e-6 <= uv[0] <= a0 + w * sc + 1e-6 and b0 - 1e-6 <= uv[1] <= b0 + h * sc + 1e-6]
        if not isl:
            print("CAPTAIN tattoo %s: no island" % name)
            continue
        _, a0, b0, sc, w, h = face_island[isl[0]]
        ar, au = right[2] - uv, up[2] - uv
        # (a view's few pixels across are this many metres on him: the size from the picture's span on him)
        # (eighteenth round: the smaller of the two: near an arm's edge the sheet sees the skin at a slant, and 6 pixels
        # across were far more skin than 6 pixels; the ship at the wrist was stamped 1.6 times too big)
        span = min(np.linalg.norm(ar), np.linalg.norm(au)) / 6.0      # atlas units a sheet pixel
        mirror = float(ar[0] * au[1] - ar[1] * au[0]) < 0
        turn = math.degrees(math.atan2(au[1], au[0])) - 90.0
        rows.append({"picture": "captain_" + name, "part": isl[0], "x": round(float((uv[0] - a0) / (w * sc)), 4),
                     "y": round(float((uv[1] - b0) / (h * sc)), 4), "size": round(float((c1 - c0) * span / sc), 4),
                     "turn": round(turn, 1), "mirror": bool(mirror), "strength": 1.0})
    row = hand_anchor(M, face_uv, face_island, pictures)
    if row:
        rows.append(row)
    if TATTOO_DRAWN:
        for name in list(pictures):
            if name in TATTOO_DESIGNS:
                pictures[name] = draw_tattoo(TATTOO_DESIGNS[name], pictures[name].shape[:2])
                save_rgba(os.path.join(TATTOO_DIR, "captain_%s.png" % name), pictures[name])
        print("CAPTAIN tattoos drawn as line art: %s" % ", ".join(n for n in pictures if n in TATTOO_DESIGNS))
    if old and old.get("keep"):
        rows = old["rows"]
        print("CAPTAIN tattoos: the table says keep; placed as it says")
    else:
        with open(table, "w") as f:
            json.dump({"keep": False, "skin": "captain_skin_layout.json", "pictures": "res://textures/tattoos/",
                       "note": "size: the picture's width in the island's own units (the layout's scale divided out)",
                       "rows": rows}, f, indent=1)
    size = ATLAS["skin"] * TATTOO_RES   # (twenty-first round: twice the skin's picture, the critic: "re-raster the tattoo pictures at 2x")
    out = np.zeros((size, size, 4), np.float32)
    rects = []
    for row in rows:
        if row["part"] not in face_island:
            continue
        pic, a0, b0, sc, w, h = face_island[row["part"]]
        img = pictures.get(row["picture"].replace("captain_", "", 1))
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
        # (eighteenth round: a stamp near its island's edge ran over into the next island: the "fragments at the
        # collar" were the left forearm's stamps landing on the torso's top edge. Each stamp is kept in its island)
        inside &= (xs >= a0 * size) & (xs < (a0 + w * sc) * size) & (ys >= b0 * size) & (ys < (b0 + h * sc) * size)
        # (twenty-first round: sampled smoothly, then the cover made crisp: a clean edge a texel wide, not a soft blot)
        fy_ = (1.0 - py[inside]) * ph - 0.5
        fx_ = px[inside] * pw - 0.5
        y0_ = np.floor(fy_).astype(int); x0_ = np.floor(fx_).astype(int)
        ty_ = (fy_ - y0_)[:, None]; tx_ = (fx_ - x0_)[:, None]
        def _at(yi, xi):
            return img[yi.clip(0, ph - 1), xi.clip(0, pw - 1)]
        src = (_at(y0_, x0_) * (1 - tx_) + _at(y0_, x0_ + 1) * tx_) * (1 - ty_) + (_at(y0_ + 1, x0_) * (1 - tx_) + _at(y0_ + 1, x0_ + 1) * tx_) * ty_
        yy, xx = ys[inside], xs[inside]
        a = smooth01(TATTOO_CRISP[0], TATTOO_CRISP[1], src[:, 3]) * row.get("strength", 1.0)
        rects.append((cx - reach, cy - reach, cx + reach, cy + reach))
        put = a > out[yy, xx, 3]
        out[yy[put], xx[put], :3] = src[put, :3]
        out[yy[put], xx[put], 3] = a[put]
    # (the clear texels round the ink take the ink's colour, so the texture's filtering does not draw a pale fringe)
    has = out[..., 3] > 0.3
    if has.any():
        out[..., :3] = np.where(has[..., None], out[..., :3], fill_out(out[..., :3], has, 64))
    save_rgba(os.path.join(TEX, "captain_tattoo_overlay.png"), out[::-1])
    print("CAPTAIN tattoos: %d placed: %s" % (len(rows), [(r["picture"][8:], r["part"]) for r in rows]))
    ink = []
    for fi, (pic, uv) in face_uv.items():
        if pic != "skin":
            continue
        q = np.array(uv) * size
        lo, hi = q.min(0), q.max(0)
        if any(lo[0] <= r[2] and hi[0] >= r[0] and lo[1] <= r[3] and hi[1] >= r[1] for r in rects):
            ink.append(fi)
    return ink, out


def ink_material():
    mat = bpy.data.materials.new("captain_ink")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tex = nt.nodes.new("ShaderNodeTexImage")
    img = bpy.data.images.load(os.path.join(TEX, "captain_tattoo_overlay.png"))
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
