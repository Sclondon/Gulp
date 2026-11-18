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
TEX = os.path.join(ROOT, "textures", "brother")
TATTOO_DIR = os.path.join(ROOT, "textures", "tattoos")
GLB = os.path.join(ROOT, "models", "brother.glb")
BLEND = os.path.join(HERE, "blend", "brother.blend")
WHO = "BROTHER"

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


OUT = arg("--out", "")
FIT_ROUNDS = int(arg("--rounds", "6"))

# ------------------------------------------------------------------------------------------------------------------
# The sheets
# ------------------------------------------------------------------------------------------------------------------

BODY_SHEET = os.path.join(ART, "concept_brother_tpose6.jpg")
HEAD_SHEET = os.path.join(ART, "concept_brother_head2.jpg")
HANDS_SHEET = os.path.join(ART, "concept_brother_hands.jpg")

# The body sheet (pixels of the 2752 by 1536 picture): the soles' row, the chin's row, each view's middle column (the
# front's and back's from the torso and the legs; the side's between the ankle and the torso's middle) and the
# columns each spans. Its guide lines are found in the columns between the front and the side figures.
SOLE = 1458.0
CHIN = 308.0
CHIN_Z = 1.673                # metres: the crown 0.257 m above (1/7.5 of 1.93 m)
CROWN_Z = 1.93
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


class Sheets:
    def __init__(self):
        # (the guide lines painted out of the pictures that are painted from as well: they crossed his eyes and neck)
        self.body_pix = unline(load_picture(BODY_SHEET), GROUND_COLS)
        self.body_mask = flood_mask(self.body_pix)
        raw = load_picture(HEAD_SHEET)
        self.head_pix = unline_rows(raw, guide_rows(raw))
        self.head_mask = figure_mask(self.head_pix)
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
ARM_ROOT_Z = 1.475
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
        yf = -(run[1] + 1 - MID["side"]) * S
        back = SIDE_BACK.get(r, run[0])
        yb = -(back - MID["side"]) * S
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
HAND_UNSUBDIV = 2
# The base head's own landmarks on its middle line (the bundle's coordinates, y and z, at HEAD_MIX), read off it.
HEAD_BASE_MARKS = {"chin_bottom": (-0.141, -0.039), "chin": (-0.148, -0.027), "mouth": (-0.149, 0.006),
                   "tip": (-0.166, 0.035), "nasion": (-0.143, 0.073), "brow": (-0.148, 0.094)}
HEAD_FIT_PASSES = int(arg("--headrounds", "10"))


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
    cb, rb = fwd(975, 1015)
    ct, rt = fwd(1050, 1115)
    cn, rn = min(((front_col(r), r) for r in range(rb + 3, rt - 15)))
    out["brow"] = (y_of(cb), float(head_z(rb)))
    out["tip"] = (y_of(ct), float(head_z(rt)))
    out["nasion"] = (y_of(cn), float(head_z(rn)))
    out["mouth"] = (y_of(front_col(int(SMILE[0]))), float(head_z(SMILE[0])))
    cc, rc = fwd(1185, 1238)
    out["chin"] = (y_of(cc), float(head_z(rc)))
    out["chin_bottom"] = (y_of(CHIN_BOTTOM[0]), float(head_z(CHIN_BOTTOM[1])))
    back = min(int(np.where(side[r])[0].min()) for r in range(880, 1060))
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
    for _ in range(25):
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


def base_head(M, sh, top_ring):
    """The base head put on him: placed, warped by landmarks, fitted to the bald row's outlines, bridged to the
    torso's top ring. Its points and faces go into M (part "head"; the bridge "neck"); its own UVs are kept per face
    corner (M.base_uv) for the face picture's layout."""
    P, faces, uvs, loc = load_base("head")
    P[:, 0] -= (P[:, 0].max() + P[:, 0].min()) / 2.0
    # (the base is symmetrical to a fraction of a millimetre: made exact)
    mid = np.where(np.abs(P[:, 0]) < 1e-3)[0]
    P[mid, 0] = 0.0
    B = {}
    for k, v in HEAD_BASE_MARKS.items():
        yz = np.array(v) - loc[1:]
        i = mid[np.argmin(np.linalg.norm(P[mid][:, 1:] - yz, axis=1))]
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
        P[ids, 0] += s * out
    # Into M
    base = len(M.P)
    idx = [M.add(p, "head") for p in P]
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
    kept = []
    for k, f in enumerate(faces):
        if k in hole:
            continue
        M.face([idx[v] for v in f], "head")
        M.base_uv[len(M.faces) - 1] = {idx[v]: uv for v, uv in zip(f, uvs[k])}
        kept.append(len(M.faces) - 1)
    M.tag["base_head_faces"] = kept
    M.tag["base_head_pts"] = idx
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
            gain[k] = 1.0 + (float(np.clip(want / have, 0.8, 2.2)) - 1.0) * wnose[k]
    Pm[hp, 0] *= gain
    M.P = [p for p in Pm]
    print("BROTHER nose widened: %d points, most times %.2f" % (int((gain > 1.001).sum()), float(gain.max())))
    # 7. the outline fit, five views, kept symmetrical; the angled views' own angle and middle found first
    N0 = {fi: face_normal(M.P, M.faces[fi]) for fi in kept}
    mir = head_mirror(M)
    head_silhouettes(M, sh, "placed")
    align_head_views(M, sh, spread=10.0, step=2.0)
    for rnd in range(HEAD_FIT_PASSES):
        views = ("front", "side", "back") if rnd < 3 else ("front", "q", "side", "qb", "back")
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
HAND_POSE_RELAXED = {"curl": (0.1, 0.2, 0.14), "together": 0.75, "thumb_in": 0.55, "thumb_fwd": 0.4, "thumb_curl": 0.2}
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
    print("BROTHER base hand: %d points, %d faces, %d triangles after the stub; wrist loop %d" % (len(C), len(faces), sum(len(f) - 2 for f in faces), len(loop)))
    # labels: the four fingers (beyond the webs), the thumb, the palm
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
    axes["thumb"] = digit_axis(C, np.where((label == "thumb") & (C[:, 2] > 0.06))[0])
    print("BROTHER base hand labels: %s" % {n: int((label == n).sum()) for n in names + ("thumb", "")})
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
    sa = palm_s / float(C[band, 0].max() - C[band, 0].min())
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
    HB["flat"] = HB["C"].copy()
    hand_silhouettes(sh)


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
            curls = pose["curl"]
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


def head_target(sh, view):
    """The sheet's head in one view: its figure within the view's columns and the compared rows."""
    _, mid, (c0, c1) = HEAD_VIEWS[view]
    t = np.zeros_like(sh.head_mask)
    r0, r1 = HEAD_ROWS_SEEN
    t[r0:r1, c0:c1] = sh.head_mask[r0:r1, c0:c1]
    return t


def head_silhouette(M, view, P=None):
    P = np.array(M.P) if P is None else P
    P2, dep = project("head_" + view, P)
    zb, _ = raster(P2, dep, head_tris(M), (1536, 2752))
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
NECK_HALF = 0.079             # metres: as wide as the jaw (the front view draws a thick neck straight down from it)


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
        out.append(np.array([kd.find((float(ax[i]), float(ay[i]), 0.0))[2] for i in range(len(ay))]))
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
        m = head_silhouette(M, v)
        t = head_target(sh, v)
        r = gaps(m, t, HEAD_ROWS_SEEN, HEAD_SX)
        res[v] = (round(r[0], 2), round(r[1], 2))
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

    for name, rows in (("nose tip", (1050, 1115)), ("brow", (975, 1015)), ("lips", (1130, 1165)), ("chin", (1185, 1238))):
        a, b = forward(side_s, rows), forward(side_m, rows)
        out[name] = round(math.hypot(a[0] - b[0], a[1] - b[1]) * HEAD_SX * 100, 2)

    def width(mask, r):
        cols = np.where(mask[r])[0]
        return cols.min(), cols.max()
    for name, r in (("ears' width", 1060), ("jaw at its angle", 1176), ("jaw by the chin", 1225)):
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
    head_at.z = 1.735
    head_at.y += 0.012
    bones.append(("head", head_at, "neck"))
    for s, sfx in ((1, "_l"), (-1, "_r")):
        sh_ = Vector(mirror_x(joints["shoulder_l"], s))
        el = Vector(mirror_x(joints["elbow_l"], s))
        wr = Vector(mirror_x(joints["wrist_l"], s))
        bones.append(("clavicle" + sfx, Vector((s * 0.04, sh_.y - 0.01, sh_.z + 0.07)), "chest"))
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
            w = {"head": 1.0}
            if fam in ("head", "neck") and p[2] < 1.672:
                t = float(smooth01(1.638, 1.672, p[2]))
                w = {"head": t, "neck": 1 - t}
        elif fam == "torso":
            w = chain_weights(p[2], ["hips", "spine", "chest", "neck"], [zt["hips_spine"], zt["spine_chest"], zt["chest_neck"]], 0.07)
            # near the shoulder: some of the upper arm
            for s, sx in ((1, "_l"), (-1, "_r")):
                d = np.linalg.norm(p - at["upper_arm" + sx])
                k = 0.45 * (1 - float(smooth01(0.085, 0.2, d)))
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
            w = chain_weights(s, ["upper_arm" + sfx, "forearm" + sfx, "hand" + sfx], [Lu, Lu + np.linalg.norm(W - E) + 0.005], 0.055)
            k = 0.4 * (1 - float(smooth01(0.0, 0.1, s)))
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
                w = chain_weights(-z, ["thigh" + sfx, "shin" + sfx, "foot" + sfx], [-K[2], -A[2]], 0.055)
                k = 0.3 * float(smooth01(H[2] - 0.04, H[2] + 0.05, z))
                if k > 0:
                    w = {n: v * (1 - k) for n, v in w.items()}
                    w["hips"] = w.get("hips", 0) + k
            else:
                fwd = np.array((math.sin(FOOT_YAW) * (1 if sfx == "_l" else -1), -math.cos(FOOT_YAW), 0.0))
                u = float(np.dot(p - A, fwd))
                w = chain_weights(u, ["foot" + sfx, "toe" + sfx], [0.15], 0.03)
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
    368: {2: (0.0, 0.004, 0.008), 3: (0.0, 0.008, 0.014), 4: (0.0, 0.008, 0.016), 5: (0.0, 0.006, 0.014), 6: (0.0, 0.004, 0.01)},
    345: {2: (0.0, 0.004, 0.006), 3: (0.0, 0.008, 0.012), 4: (0.0, 0.01, 0.014), 5: (0.0, 0.008, 0.012), 6: (0.0, 0.005, 0.008)},
    318: {3: (0.0, 0.004, 0.004), 4: (0.0, 0.006, 0.006), 5: (0.0, 0.004, 0.004)},
}
# The kneecaps (forward, metres) on the leg ring at the knee's row, by point (point 1 is the front), and the calves
# (back, metres) on the rings below it (point 6 is the back).
KNEE_FORM = {1: 0.012, 0: 0.006, 2: 0.006}
CALF_FORM = {1190: {6: 0.012, 5: 0.009, 7: 0.009}, 1235: {6: 0.008, 5: 0.006, 7: 0.006}}
# The belly's rows smoothed down each front column after the forms (from, to, rounds): no ring stands out of the curve.
BELLY_SMOOTH = (600, 720, 3)


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
    sel = np.isin(fams, ("torso", "shoulder", "arm", "leg", "foot"))
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
    d += depth * np.exp(-((row - line) / 3.0) ** 2) * np.clip((half + 6 - np.abs(col)) / 10.0, 0, 1)
    P = P + N * (d * w)[:, None]
    M.P = [p for p in P]
    print("BROTHER face forms: most %.1f mm" % (1000 * float(np.abs(d * w).max())))


def refine_base_head(M, face_uv, weights, under, sh):
    """Third build: the base head's face (brow to chin, the faces turned forward) split once, the new points placed
    on the curved surface (refine); then two more outline rounds on the denser face."""
    P = np.array(M.P)
    # (the whole head but the ears: the cage alone showed its facets along the skull's outline)
    ears = set(M.tag["ear_l"]) | set(M.tag["ear_r"])
    sel = {fi for fi in M.tag["base_head_faces"] if len(M.faces[fi]) == 4 and not (set(M.faces[fi]) & ears)}
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
    mir = head_mirror(R)
    N0 = {fi: face_normal(R.P, R.faces[fi]) for fi in R.tag["base_head_faces"]}
    neck = [v for ring in R.tag["neck_rings"] for v in ring]
    for rnd in range(4):
        # (the neck too, and the opening's loop: the head sheet's nape and throat)
        base_head_round(R, sh, ("front", "q", "side", "qb", "back"), step=0.8 if rnd < 2 else 0.5, reach=70,
                        more=neck, hold_loop=False)
        symmetrize(R, mir)
    head_smooth(R, 1, lam=0.3, mu=-0.32)
    symmetrize(R, mir)
    base_face_forms(R)
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
    near[hp[(rows_h > 1135) & (np.abs(Pn[hp, 0]) > 0.035)]] = True
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
    print("BROTHER refined: face %d faces split; %d triangles now; folded after the refit %d" % (len(sel), len(R.tris()), folded_faces(R, R.tag["base_head_faces"], N0)))
    return R, uv1, W1, under2


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

def main():
    # (an empty scene: the factory start-up's cube, camera and light removed)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
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
    frozen = np.isin(fams, ("head", "nose", "ear", "neck", "hand"))
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
    finish(M, T, joints, sh)


def finish(M, T, joints, sh):
    H = M.tag["head_rings"]
    bones = skeleton_joints(M, T, joints)
    weights = weights_of(M, T, bones, joints)
    islands = plan_uvs(M, T, H, joints)
    placed, face_uv = pack(islands)
    under = boxer_faces(M, T)
    M, face_uv, weights, under = refine_base_head(M, face_uv, weights, under, sh)
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
    face, fpos, fhit, fskin = paint_head(M, face_uv, sh)
    # The two sheets paint his skin differently (the head sheet a little cooler than the body sheet): the whole face picture
    # is brought to the body's tone (the median of its plain skin to the median of the body's chest and neck), then
    # the neck is matched where the two pictures meet (the torso's top ring), so no step shows.
    zt = float(np.mean([M.P[i][2] for i in T[-1]]))
    body_ref = np.median(skin[shit & (spos[..., 2] > zt - 0.25) & (spos[..., 2] < zt - 0.03)], axis=0)
    gain0 = body_ref / np.maximum(fskin, 1e-3)
    # (only on skin: the eyes' blue and whites keep their colour)
    skinw = np.clip((face[..., 0] - face[..., 2] - 0.03) * 12.0, 0, 1)[..., None]
    face = np.clip(face * (1 + (gain0 - 1) * skinw), 0, 1)
    near_b = shit & (np.abs(spos[..., 2] - (zt - 0.02)) < 0.02)
    near_h = fhit & (np.abs(fpos[..., 2] - (zt + 0.01)) < 0.012)
    if near_b.any() and near_h.any():
        gain = skin[near_b].mean(0) / np.maximum(face[near_h].mean(0), 1e-3)
        gain = np.clip(gain, 0.85, 1.2)
        w = (1.0 - smooth01(zt, zt + 0.06, fpos[..., 2])) * fhit
        face = face * (1 + (gain - 1) * w[..., None])
        print("BROTHER face tone: times %s, then the neck times %s" % (np.round(gain0, 3), np.round(gain, 3)))
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
    skin_object("brother_body", [i for i in range(len(M.faces)) if i not in under])
    skin_object("brother_body_under", sorted(under))
    Bx = build_boxers(M, T, sh, weights, under, armature)
    # His tattoos: lifted from the sheet, placed by the table, drawn as a see-through layer over his arms.
    ink_faces = lay_tattoos(M, face_uv, placed, sh)
    if ink_faces:
        mat_ink = ink_material()
        ob = skin_object("brother_ink", ink_faces, (mat_ink,))
        for v in ob.data.vertices:
            v.co += v.normal * 0.0007
    report_counts(M, face_uv)
    print("BROTHER triangles shorts: %d" % len(Bx.tris()))
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


def build_boxers(M, T, sh, weights, under, armature):
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

    lower = sorted(r for r in TORSO_ROWS if r >= 835)
    rows_of = []
    for k in range(TORSO_N):
        phi = math.tau * k / TORSO_N
        b = band_row(phi)
        b1 = b + BOXER_BAND_TALL
        mids = [b1 + (822.0 - b1) * t for t in (0.33, 0.66, 1.0)]
        rows_of.append([b, b, b1] + mids + lower)
    nrows = len(rows_of[0])
    G = []
    band_rows = (0, 1, 2)
    for j in range(nrows):
        ring = []
        for k in range(TORSO_N):
            r = rows_of[k][j]
            q, n, s = column_at(k, float(body_z(r)))
            stand = 0.002 if j == 0 else BOXER_STAND[1] if j in band_rows else BOXER_STAND[0]
            if j == 0:
                q = q + np.array((0.0, 0.0, -0.003))
            ring.append(Bx.add(q + n * stand, "boxers"))
            src.append(s)
        G.append(ring)
    for j in range(nrows - 1):
        for k in range(TORSO_N):
            kk = (k + 1) % TORSO_N
            Bx.face([G[j][k], G[j][kk], G[j + 1][kk], G[j + 1][k]], "boxers_torso")
            Bx.cell[len(Bx.faces) - 1] = ("trunk", j, k)
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
                    q[2] = float(body_z(BOXER_HEM))
                ring.append(Bx.add(q, "boxers"))
                src.append(v)
            rings.append(ring)
        for a, b in zip(rings, rings[1:]):
            for j in range(LIMB_N):
                k = (j + 1) % LIMB_N
                Bx.face([a[j], a[k], b[k], b[j]], "boxers_leg" + sfx)
        # (the hem turned up inside a centimetre and a half: the cloth has a thickness at its edge, not a hard rim)
        hem = rings[-1]
        hc = np.array([Bx.P[v] for v in hem]).mean(0)
        fold = []
        for v in hem:
            q = np.array(Bx.P[v], float)
            dd = q - hc
            dd[2] = 0.0
            dd /= max(np.linalg.norm(dd), 1e-9)
            fold.append(Bx.add(q - dd * 0.008 + np.array((0.0, 0.0, 0.015)), "boxers"))
            src.append(src[v])
        for j in range(LIMB_N):
            k = (j + 1) % LIMB_N
            Bx.face([hem[j], hem[k], fold[k], fold[j]], "boxers_leg" + sfx)
        legs[sfx] = rings
    Q = np.array(Bx.P)
    flipped = 0
    for fi, f in enumerate(Bx.faces):
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
    for n in islands:
        ISLANDS[n] = ("shorts", 1.0)
    ATLAS["shorts"] = 512
    placed, face_uv = pack(islands)
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
    path = os.path.join(TEX, "brother_shorts.png")
    save_rgb(path, rgb[::-1])
    w = [weights[s] for s in src]
    ob = mesh_object("brother_shorts", Bx.P, Bx.faces, armature, w)
    mat = textured_material("brother_shorts", path)
    mat.use_backface_culling = False
    ob.data.materials.append(mat)
    uvl = ob.data.uv_layers.new(name="UVMap")
    for poly in ob.data.polygons:
        for li, q in zip(poly.loop_indices, face_uv[poly.index][1]):
            uvl.data[li].uv = q
    print("BROTHER shorts: %d triangles, %d faces turned outward" % (len(Bx.tris()), flipped))
    return Bx


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
    a = np.clip((skin_rb - rb - 0.04) / 0.1, 0, 1) * np.clip((skin_lum - lum + 0.06) / 0.1, 0.3, 1)
    a[~sh.body_mask[r0:r1, c0:c1]] = 0.0
    ink = np.clip(pix * 0.85, 0, 1)
    # (where there is no ink the picture is clear and its colour the ink's own, so no skin rides along at its edges)
    mean_ink = ink[a > 0.5].mean(0) if (a > 0.5).any() else np.array((0.25, 0.28, 0.32))
    ink = np.where((a > 0.25)[..., None], ink, mean_ink)
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
                     "y": round(float((uv[1] - b0) / (h * sc)), 4), "size": round((c1 - c0) * S, 4),
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
        rgb[hands] = flat[hands] * 0.75 + blur(rgb, 6)[hands] * 0.25
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
    if hands.any():
        rgb, _ = paint_hands(M, face_uv, rgb, hit, fid, sh, base_c)
    print("BROTHER paint skin: %.0f%% of its texels seen by a view" % (100.0 * (good & hit).sum() / max(hit.sum(), 1)))
    return rgb, pos, hit
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
