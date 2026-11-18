"""Townsfolk (NPC) base bodies, one data-driven builder for all of them (2026-11-18).

    blender --background --factory-startup --python tools/build_npc.py -- <name>|all [--pics <folder>]
    blender --background --factory-startup --python tools/build_npc.py -- lineup --pics <folder>

The user: "I've like all thr older brother bodys you've sent, so we should make different models for each and generate
a lanky build and women builds and we need models for them so we can make npcs out of them".

Each entry of NPCS is one body sheet (FRONT, SIDE, BACK, arms about 45 degrees out) and becomes one bare person:
models/npc/<name>.glb, tools/blend/npc/<name>.blend, textures/npc/<name>/ (skin 1024, face 512, underwear 512, each
with a layout picture). With --pics, comparison pictures (sheet | painted | silhouette difference | plain grey | a pose
check) go to <folder>/<name>_compare.png.

How a body is made (the method of tools/build_brother.py and tools/build_captain.py, written afresh here, not imported):
- THE SHEET is cut from its flat pale background (its guide lines painted out, holes filled) into three views; every
  measure is in its pixels, scaled so that the soles to the top of the skull (under the hair) is the entry's height.
- THE BODY is lofted from cross-section rings measured row by row from the front and side outlines: a torso of 24
  points a ring with a hole on each side that IS the arm's root ring, arms of 12 a ring along each arm's own bent axis
  (measured across the arm, not across the row), legs of 14 a ring that start from the torso's bottom ring and a
  shared crotch point, feet as level rings down to a flat sole. Then rounds of outline fitting: every point on the
  model's outline in the front, side and back views is moved to the sheet's outline, the rest following smoothly,
  kept symmetrical.
- THE HEAD AND HANDS follow tools/FIGURE_HEADS.md: Blender Studio's Human Base Meshes (CC0, appended from the bundle
  outside the repo, never edited): `Head - Generic Topology` at a mix of its shape keys, subdivided once and reduced,
  fitted to the head drawn on the body sheet (chin, eye line, top of the skull, the jaw's width row by row, the face's
  profile), its underside opened and joined to the neck; `Hand - Stylized` un-subdivided once, sized to the sheet's
  hands and joined at the wrist.
- THE BARE PERSON: no hair, no hat; the scalp painted skin. The underwear (men's knit shorts; women's chemise and
  drawers) is its own mesh (`<name>_underwear`), found by where the sheet's paint is cloth, over finished skin.
- THE SKELETON has the captain's and the brother's bone names and parents (so one set of animations drives everyone),
  fitted to each body.
- UVs are planned (torso front and back, each arm and leg as an unrolled tube with the seam underneath and inside, the
  soles flat, the neck, the hands' backs and palms, the head's own UVs), and the sheet is projected into them by facing
  (front, side, back; never at a grazing angle), hair, tattoos and cloth left out of the skin and filled from round.

Model space: Blender's, Z up, the figure faces -Y (the game's +Z after export), +X is the figure's left. Metres. Each
stands in the sheet's own pose, which is the rest pose.
"""
import bpy
import builtins
import bmesh
import json
import math
import os
import sys
import time

import numpy as np
from mathutils import Matrix, Vector, kdtree

_T0 = time.time()


def print(*a, **k):
    k.setdefault("flush", True)
    builtins.print("[%5.1fs]" % (time.time() - _T0), *a, **k)


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ART = os.path.join(HERE, "art_src")
BUNDLE = os.path.join(r"C:\Projects\reference\human-base-meshes\bundle\human-base-meshes-bundle-v1.4.1",
                      "human_base_meshes_bundle.blend")

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


PICS = arg("--pics", "")
FIT_ROUNDS = int(arg("--rounds", "6"))

# ------------------------------------------------------------------------------------------------------------------
# The table. Rows are pixels of the 2752 by 1536 sheet. chin: the chin's lowest row in the front view; eye: the eye
# line; crown: the top of the skull under the hair (None: as far above the eyes as the chin is below). Heights are the
# caller's picks (soles to the top of the skull). Everything else is measured from the sheet; the optional numbers
# below change what is measured where a sheet misleads (an arm hanging over the side view, a painted-out patch).
# ------------------------------------------------------------------------------------------------------------------

MALE_HEAD = {"Real_MALE": 0.55, "Toon_MALE": 0.45}
FEMALE_HEAD = {"Real_FEMALE": 0.6, "Toon_FEMALE": 0.4}

NPCS = {
    "man_lanky": dict(sheet="concept_npc_man_lanky.jpg", height=1.91, sex="m", chin=305, eye=183, crown=78,
                      head_mix=MALE_HEAD),
    "woman_stout": dict(sheet="concept_npc_woman_stout.jpg", height=1.57, sex="f", chin=328, eye=209, crown=98,
                        head_mix=FEMALE_HEAD, thigh_k=0.8),
    "man_short_lean": dict(sheet="concept_brother_tpose2.jpg", height=1.70, sex="m", chin=359, eye=250, crown=None,
                           head_mix=MALE_HEAD, side_reject=(1463, 482, 80)),
    "man_short_sturdy": dict(sheet="concept_brother_tpose3.jpg", height=1.72, sex="m", chin=359, eye=250,
                             crown=None, head_mix=MALE_HEAD, side_reject=(1463, 482, 80)),
    "man_tall_athletic": dict(sheet="concept_brother_tpose4.jpg", height=1.90, sex="m", chin=301, eye=189,
                              crown=None, head_mix=MALE_HEAD),
    "man_tall_solid": dict(sheet="concept_brother_tpose5.jpg", height=1.90, sex="m", chin=301, eye=189,
                           crown=None, head_mix=MALE_HEAD),
    "woman_slender": dict(sheet="concept_npc_woman_slender.jpg", height=1.65, sex="f", chin=324, eye=205,
                          crown=None, head_mix=FEMALE_HEAD),
    "woman_tall": dict(sheet="concept_npc_woman_tall.jpg", height=1.78, sex="f", chin=324, eye=207, crown=None,
                       head_mix=FEMALE_HEAD),
    "woman_old": dict(sheet="concept_npc_woman_old.jpg", height=1.52, sex="f", chin=325, eye=207, crown=None,
                      head_mix={"Real_FEMALE": 0.8, "Toon_FEMALE": 0.2}),
}
ORDER = ["man_lanky", "woman_stout", "man_short_lean", "man_short_sturdy", "man_tall_athletic", "man_tall_solid",
         "woman_slender", "woman_tall", "woman_old"]

TORSO_N = 24      # points a torso ring: 0 the front's middle, 6 the left side (+X), 12 the back, 18 the right side
ARM_N = 12
LEG_N = 14
HOLE_K = (4, 8)   # the left arm's root: torso columns 4 to 8, rings ia to ia+2 (the right's mirrored: 16 to 20)
EASE = 0.010      # metres the skin lies inside the underwear's outline
FINGERS = ("index", "middle", "ring", "little")
SKIN_PX, FACE_PX, CLOTH_PX = 1024, 512, 512


# ------------------------------------------------------------------------------------------------------------------
# Pictures
# ------------------------------------------------------------------------------------------------------------------

def load_picture(path):
    im = bpy.data.images.load(path)
    w, h = im.size
    a = np.empty(w * h * 4, np.float32)
    im.pixels.foreach_get(a)
    bpy.data.images.remove(im)
    return a.reshape(h, w, 4)[::-1, :, :3].copy()   # row 0 at the top


def save_png(path, rgb):
    rgb = np.asarray(rgb, np.float32)
    if rgb.ndim == 2:
        rgb = np.repeat(rgb[:, :, None], 3, 2)
    h, w = rgb.shape[:2]
    im = bpy.data.images.new("save", w, h, alpha=False)
    a = np.ones((h, w, 4), np.float32)
    a[:, :, :3] = np.clip(rgb[::-1], 0, 1)
    im.pixels.foreach_set(a.ravel())
    im.filepath_raw = path
    im.file_format = "PNG"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save()
    bpy.data.images.remove(im)


def resize(img, h=None, w=None):
    """Nearest-pixel resize (by box averaging when shrinking a lot)."""
    H, W = img.shape[:2]
    if h is None:
        h = int(round(H * w / W))
    if w is None:
        w = int(round(W * h / H))
    f = max(1, int(min(H / h, W / w)))
    if f > 1:
        Hc, Wc = H // f * f, W // f * f
        img = img[:Hc, :Wc].reshape(Hc // f, f, Wc // f, f, -1).mean((1, 3))
        H, W = img.shape[:2]
    ri = np.clip((np.arange(h) + 0.5) * H / h, 0, H - 1).astype(int)
    ci = np.clip((np.arange(w) + 0.5) * W / w, 0, W - 1).astype(int)
    return img[ri][:, ci]


def runs_of(row, least=3):
    """Runs of True in a 1D boolean array: [(start, end)] (end not included)."""
    d = np.diff(np.concatenate([[0], row.astype(np.int8), [0]]))
    s = np.where(d == 1)[0]
    e = np.where(d == -1)[0]
    return [(int(a), int(b)) for a, b in zip(s, e) if b - a >= least]


def run_at(row, c, least=3):
    for a, b in runs_of(row, least):
        if a <= c < b:
            return a, b
    return None


def dilate(m, n=1):
    for _ in range(n):
        o = m.copy()
        o[1:] |= m[:-1]
        o[:-1] |= m[1:]
        o[:, 1:] |= m[:, :-1]
        o[:, :-1] |= m[:, 1:]
        m = o
    return m


def erode(m, n=1):
    return ~dilate(~m, n)


# ------------------------------------------------------------------------------------------------------------------
# The sheet: the figure's mask, its three views, its landmarks
# ------------------------------------------------------------------------------------------------------------------

class Sheet:
    def __init__(self, cfg):
        self.cfg = cfg
        self.pix = load_picture(os.path.join(ART, cfg["sheet"]))
        pix = self.pix
        H, W, _ = pix.shape
        bg = np.median(pix.reshape(-1, 3)[::97], 0)
        dist = np.abs(pix - bg).max(2)
        chroma = (pix[:, :, 0] - pix[:, :, 2]) - (bg[0] - bg[2])
        m = (dist > 0.06) | (chroma > 0.035)
        # the guide lines: rows darker than the rows six above and below, across the picture
        lum = pix.mean(2)
        score = np.median((np.roll(lum, 6, 0) + np.roll(lum, -6, 0)) / 2 - lum, 1)
        rows = [r for r in range(8, H - 8) if score[r] > 0.012]
        bands = []
        for r in rows:
            if bands and r - bands[-1][1] <= 2:
                bands[-1][1] = r
            else:
                bands.append([r, r])
        for r0, r1 in bands:
            keep = m[r0 - 3] & m[r1 + 3]
            for r in range(r0 - 1, r1 + 2):
                m[r] = keep
        self.guides = [(a + b) / 2 for a, b in bands]
        # holes: background is what the border reaches (found at a quarter size: a cell is background if any of it is)
        f = 4
        Hc, Wc = H // f, W // f
        cellbg = (~m[:Hc * f, :Wc * f]).reshape(Hc, f, Wc, f).any((1, 3))
        reach = np.zeros_like(cellbg)
        reach[0, :] = cellbg[0, :]
        reach[-1, :] = cellbg[-1, :]
        reach[:, 0] = cellbg[:, 0]
        reach[:, -1] = cellbg[:, -1]
        for _ in range(3000):
            nr = dilate(reach) & cellbg
            if (nr == reach).all():
                break
            reach = nr
        outside = np.zeros((H, W), bool)
        outside[:Hc * f, :Wc * f] = np.repeat(np.repeat(reach, f, 0), f, 1)
        m = m | ~outside
        m[:, :4] = m[:, -4:] = False
        m[:4] = m[-4:] = False
        # specks: keep only pixels in runs of at least 4 both ways
        m = erode(dilate(m, 1), 1)
        m &= dilate(erode(m, 2), 2) | dilate(erode(m.T, 2).T, 2)
        self.mask = m
        self.H, self.W = H, W
        # the cloth: pale, little colour
        r_, g_, b_ = pix[:, :, 0], pix[:, :, 1], pix[:, :, 2]
        rr = np.maximum(r_, 1e-3)
        self.cloth = m & (lum > 0.45) & (g_ / rr > 0.885) & (b_ / rr > 0.77)
        self.cloth[: int(cfg["chin"]) + 10] = False
        self.cloth = erode(dilate(self.cloth, 5), 5) & m
        # for painting: the figure less its edge, the drawn lines (darker than round them), and near the cloth
        self.inner = erode(m, 4)
        k = 15
        cs = np.cumsum(np.cumsum(np.pad(lum, ((k + 1, k), (k + 1, k)), mode="edge"), 0), 1)
        box = (cs[2 * k + 1:, 2 * k + 1:] - cs[:-2 * k - 1, 2 * k + 1:] - cs[2 * k + 1:, :-2 * k - 1] + cs[:-2 * k - 1, :-2 * k - 1]) / (2 * k + 1) ** 2
        self.lines = lum < 0.8 * box
        self.near_cloth = dilate(self.cloth, 6)
        # three views by columns
        occ = m[int(H * 0.1):int(H * 0.95)].sum(0) > 2
        cr = []
        for a, b in runs_of(occ, 1):
            if cr and a - cr[-1][1] < 30:
                cr[-1] = (cr[-1][0], b)
            else:
                cr.append((a, b))
        cr = sorted(sorted(cr, key=lambda ab: ab[1] - ab[0])[-3:])
        self.span = {"front": cr[0], "side": cr[1], "back": cr[2]}
        print("SHEET", cfg["sheet"], "views", self.span, "guides", [int(g) for g in self.guides])
        self.measure_landmarks()

    def view_mask(self, view):
        a, b = self.span[view]
        out = np.zeros_like(self.mask)
        out[:, a:b] = self.mask[:, a:b]
        return out

    def measure_landmarks(self):
        cfg = self.cfg
        fm = self.view_mask("front")
        sm = self.view_mask("side")
        bm = self.view_mask("back")
        self.fm, self.sm, self.bm = fm, sm, bm
        rows_s = np.where(sm.any(1))[0]
        self.sole = float(rows_s.max())
        self.top = float(np.where(fm.any(1))[0].min())
        a, b = self.span["front"]
        # the middle columns: the torso's middle a third of the way up from the soles to the top... (the hips)
        def middle(mask, span):
            cs = []
            guess = (span[0] + span[1]) / 2
            for r in np.linspace(self.sole - 0.5 * (self.sole - self.top), self.sole - 0.62 * (self.sole - self.top), 9):
                ra = run_at(mask[int(r)], int(guess))
                if ra:
                    cs.append((ra[0] + ra[1]) / 2)
            return float(np.median(cs)) if cs else guess
        self.mid = {"front": middle(fm, self.span["front"]), "back": middle(bm, self.span["back"]),
                    "side": middle(sm, self.span["side"])}
        chin, eye, crown = cfg.get("chin"), cfg.get("eye"), cfg.get("crown")
        if chin is None or eye is None:
            raise RuntimeError("the table needs chin and eye rows for %s" % cfg["sheet"])
        if crown is None:
            crown = eye - (chin - eye)
        self.chin, self.eye, self.crown = float(chin), float(eye), float(crown)
        self.S = cfg["height"] / (self.sole - self.crown)
        print("  sole %.0f top %.0f crown %.0f chin %.0f eye %.0f  %.2f mm a pixel  middles %s" % (
            self.sole, self.top, self.crown, self.chin, self.eye, self.S * 1000,
            {k: round(v) for k, v in self.mid.items()}))

    # pixels and metres
    def z(self, row):
        return (self.sole - row) * self.S

    def row(self, z):
        return self.sole - z / self.S

    def to_px(self, view, P):
        """Model points (n,3) to (col, row, depth) in a view of the sheet."""
        P = np.asarray(P, float)
        r = self.sole - P[:, 2] / self.S
        if view == "front":
            c, d = self.mid["front"] + P[:, 0] / self.S, P[:, 1]
        elif view == "back":
            c, d = self.mid["back"] - P[:, 0] / self.S, -P[:, 1]
        elif view == "side":
            c, d = self.mid["side"] - P[:, 1] / self.S, P[:, 0]
        else:  # side_l: the right side's drawing used for the left, seen from +X
            c, d = self.mid["side"] - P[:, 1] / self.S, -P[:, 0]
        return np.stack([c, r, d], 1)

    @staticmethod
    def world_dir(view, dc, dr):
        if view == "front":
            return np.array([dc, 0.0, -dr])
        if view == "back":
            return np.array([-dc, 0.0, -dr])
        return np.array([0.0, -dc, -dr])

    VIEW_DIR = {"front": (0, -1, 0), "back": (0, 1, 0), "side": (-1, 0, 0), "side_l": (1, 0, 0)}

    def target(self, view):
        return {"front": self.fm, "back": self.bm, "side": self.sm, "side_l": self.sm}[view]


# ------------------------------------------------------------------------------------------------------------------
# A rasteriser (orthographic, for silhouettes, depth and the UV layouts)
# ------------------------------------------------------------------------------------------------------------------

def raster(P2, depth, tris, shape, want_bary=False):
    """P2 (n,2) in pixels (col, row); returns depth buffer, triangle ids (and barycentrics)."""
    H, W = shape
    zb = np.full((H, W), np.inf, np.float32)
    tid = np.full((H, W), -1, np.int32)
    bary = np.zeros((H, W, 3), np.float32) if want_bary else None
    P2 = np.asarray(P2, np.float64)
    depth = np.asarray(depth, np.float64)
    for t, (i, j, k) in enumerate(tris):
        a, b, c = P2[i], P2[j], P2[k]
        c0 = int(max(0, math.floor(min(a[0], b[0], c[0]))))
        c1 = int(min(W - 1, math.ceil(max(a[0], b[0], c[0]))))
        r0 = int(max(0, math.floor(min(a[1], b[1], c[1]))))
        r1 = int(min(H - 1, math.ceil(max(a[1], b[1], c[1]))))
        if c1 < c0 or r1 < r0:
            continue
        area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if abs(area) < 1e-12:
            continue
        xs, ys = np.meshgrid(np.arange(c0, c1 + 1) + 0.0, np.arange(r0, r1 + 1) + 0.0)
        w0 = ((b[0] - xs) * (c[1] - ys) - (b[1] - ys) * (c[0] - xs)) / area
        w1 = ((c[0] - xs) * (a[1] - ys) - (c[1] - ys) * (a[0] - xs)) / area
        w2 = 1.0 - w0 - w1
        inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not inside.any():
            continue
        z = w0 * depth[i] + w1 * depth[j] + w2 * depth[k]
        sub = zb[r0:r1 + 1, c0:c1 + 1]
        better = inside & (z < sub)
        sub[better] = z[better]
        tid[r0:r1 + 1, c0:c1 + 1][better] = t
        if want_bary:
            bb = bary[r0:r1 + 1, c0:c1 + 1]
            bb[better] = np.stack([w0[better], w1[better], w2[better]], 1)
    return zb, tid, bary


# ------------------------------------------------------------------------------------------------------------------
# The mesh being built
# ------------------------------------------------------------------------------------------------------------------

class Mesh:
    def __init__(self):
        self.P = []
        self.part = []
        self.F = []
        self.fpart = []
        self.fuv = []
        self.base = {}      # head points: their place on the base head (for the scalp)
        self.finger = {}    # hand points: which finger

    def add(self, p, part):
        self.P.append(np.array(p, float))
        self.part.append(part)
        return len(self.P) - 1

    def face(self, vs, fpart, uv=None):
        self.F.append(list(vs))
        self.fpart.append(fpart)
        self.fuv.append(uv)

    def arr(self):
        return np.array(self.P)

    def tris(self, sel=None):
        out = []
        for fi, f in enumerate(self.F):
            if sel is not None and not sel(fi):
                continue
            for k in range(1, len(f) - 1):
                out.append((f[0], f[k], f[k + 1]))
        return np.array(out, int)

    def neighbours(self):
        nb = [set() for _ in self.P]
        for f in self.F:
            for k in range(len(f)):
                a, b = f[k], f[(k + 1) % len(f)]
                nb[a].add(b)
                nb[b].add(a)
        return [list(s) for s in nb]

    def normals(self):
        P = self.arr()
        N = np.zeros_like(P)
        for f in self.F:
            for k in range(1, len(f) - 1):
                n = np.cross(P[f[k]] - P[f[0]], P[f[k + 1]] - P[f[0]])
                for v in (f[0], f[k], f[k + 1]):
                    N[v] += n
        return N / np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)


def sgnpow(v, p):
    return np.sign(v) * np.abs(v) ** p


def ring_shape(theta, a, bf, bb, p):
    """A superellipse ring round (0,0): theta 0 the front (-Y), pi/2 the left (+X)."""
    s, c = np.sin(theta), np.cos(theta)
    x = a * sgnpow(s, p)
    b = np.where(c > 0, bf, bb)
    y = -b * sgnpow(c, p)
    return x, y


def lerp(a, b, t):
    return a + (b - a) * t


def smoothstep(a, b, x):
    t = np.clip((np.asarray(x, float) - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def interp_rows(table, z):
    """table: list of (z, value) sorted by z."""
    zs = [a for a, _ in table]
    vs = [b for _, b in table]
    return float(np.interp(z, zs, vs))


# ------------------------------------------------------------------------------------------------------------------
# Measuring the body
# ------------------------------------------------------------------------------------------------------------------

class Body:
    """What the sheet says about the body, in metres."""

    def __init__(self, sh):
        self.sh = sh
        S = sh.S
        fm, sm = sh.fm, sh.sm
        mf, ms = sh.mid["front"], sh.mid["side"]
        H = sh.cfg["height"]
        self.H = H
        k = H / 1.75
        self.k = k
        # the crotch: the lowest row where the front's middle column is filled, from the knees up
        r = int(sh.row(0.30 * H))
        while r > sh.chin and not fm[r, int(mf)]:
            r -= 1
        self.crotch_row = r
        self.crotch_z = sh.z(r)
        # the arm, tracked down from the shoulder (the figure's left arm: the front view's right)
        self.track_arm()
        # the neck: the narrowest middle run between the chin and the shoulders
        best = None
        for r in range(int(sh.chin) + 4, int(self.shoulder_row)):
            ra = run_at(fm[r], int(mf))
            if ra and (best is None or ra[1] - ra[0] < best[1]):
                best = (r, ra[1] - ra[0])
        self.neck_row, neck_w = best
        self.neck_half = neck_w / 2 * S
        r = self.neck_row
        while r < self.shoulder_row:
            ra = run_at(fm[r], int(mf))
            if ra and (ra[1] - ra[0]) > 1.35 * neck_w:
                break
            r += 1
        self.neckbase_row = r
        print("  crotch %d  armpit %d  shoulder top %d  neck %d (half %.3f m)  neck base %d" % (
            self.crotch_row, self.armpit_row, self.shoulder_row, self.neck_row, self.neck_half, self.neckbase_row))

    # front-view torso run and side-view run at a row
    def front_run(self, r):
        """The torso's run at a row (runs split by a drawn line a few pixels wide joined again)."""
        rs = runs_of(self.sh.fm[int(round(r))], 1)
        mf = self.sh.mid["front"]
        hit = [i for i, (a, b) in enumerate(rs) if a <= mf < b]
        if not hit:
            near = [i for i, (a, b) in enumerate(rs) if abs((a + b) / 2 - mf) < 12 or a - 6 <= mf <= b + 6]
            if not near:
                return None
            hit = near[:1]
        i0 = i1 = hit[0]
        while i0 > 0 and rs[i0][0] - rs[i0 - 1][1] <= 6:
            i0 -= 1
        while i1 < len(rs) - 1 and rs[i1 + 1][0] - rs[i1][1] <= 6:
            i1 += 1
        return rs[i0][0], rs[i1][1]

    def side_run(self, r):
        sm = self.sh.sm[int(round(r))]
        ra = run_at(sm, int(self.sh.mid["side"]))
        if ra is None:
            rs = runs_of(sm)
            if not rs:
                return None
            ra = min(rs, key=lambda ab: abs((ab[0] + ab[1]) / 2 - self.sh.mid["side"]))
        return ra

    def track_arm(self):
        sh = self.sh
        fm = sh.fm
        mf = sh.mid["front"]
        # start at the chest's middle height: the rightmost run that does not hold the middle
        r = int(sh.row(0.62 * self.H))
        rs = runs_of(fm[r])
        arm = [ab for ab in rs if ab[0] > mf]
        arm = [ab for ab in arm if not (ab[0] <= mf < ab[1])]
        if not arm:
            raise RuntimeError("no arm at row %d" % r)
        start = arm[-1]
        track = {r: start}
        # up to the armpit
        prev = start
        rr = r - 1
        while rr > sh.chin:
            cand = [ab for ab in runs_of(fm[rr]) if ab[1] > prev[0] and ab[0] < prev[1]]
            if not cand:
                break
            ab = cand[-1]
            if ab[0] <= mf < ab[1]:   # merged with the torso
                break
            track[rr] = ab
            prev = ab
            rr -= 1
        self.armpit_row = rr + 1
        # down to the finger tips
        prev = start
        rr = r + 1
        while rr < sh.sole:
            cand = [ab for ab in runs_of(fm[rr]) if ab[1] > prev[0] and ab[0] < prev[1]]
            if not cand:
                break
            ab = cand[-1]
            if ab[0] <= mf < ab[1] or (ab[1] - ab[0]) > 2.5 * max(prev[1] - prev[0], 8):
                break
            track[rr] = ab
            prev = ab
            rr += 1
        self.tip_row = rr - 1
        self.track = track
        centres = {q: (ab[0] + ab[1]) / 2 for q, ab in track.items()}
        self.centres = centres
        # the shoulder's top: the first filled row from the top at the arm's column under the armpit
        ca = centres[self.armpit_row]
        top = np.where(fm[:, int(ca)])[0]
        self.shoulder_row = float(top.min())
        # the arm's points in pixels: J the shoulder joint, E the elbow, W the wrist, T the finger tips
        hand_len = self.sh.cfg.get("hand", 0.108 if self.sh.cfg["sex"] == "m" else 0.10) * self.H
        self.hand_len = hand_len
        T = np.array([centres[self.tip_row], self.tip_row], float)
        # the direction near the hand
        lo = self.tip_row - int(2.2 * hand_len / sh.S)
        hi = self.tip_row - int(1.1 * hand_len / sh.S)
        qs = [q for q in range(lo, hi) if q in centres]
        A = np.array([[centres[q], q] for q in qs])
        d = A[-1] - A[0]
        d /= np.linalg.norm(d)
        # the wrist: the arm's narrowest row above the hand (unless the table gives the hand's length)
        if "hand" not in self.sh.cfg:
            cs = [q for q in range(self.tip_row - int(0.14 * self.H / sh.S), self.tip_row - int(0.085 * self.H / sh.S))
                  if q in track]
            wd = np.array([track[q][1] - track[q][0] for q in cs], float)
            wd = np.convolve(wd, np.ones(9) / 9, mode="same")
            q = cs[int(np.argmin(wd[4:-4])) + 4]
            Wp = np.array([centres[q], q], float)
            hand_len = float(np.linalg.norm(T - Wp) * sh.S)
            self.hand_len = hand_len
        else:
            Wp = T - d * hand_len / sh.S
            q = int(round(Wp[1]))
            if q in centres:
                Wp = np.array([centres[q], q], float)
        print("  hand %.3f m (wrist row %d, tips %d)" % (self.hand_len, Wp[1], self.tip_row))
        w_ap = track[self.armpit_row][1] - track[self.armpit_row][0]
        Jp = np.array([ca - 0.12 * w_ap, self.shoulder_row + 0.55 * w_ap], float)
        # the elbow: on the tracked middle line, 0.53 of the way down from J to W
        L = np.linalg.norm(Wp - Jp)
        best = None
        for q, c in centres.items():
            p = np.array([c, q])
            t = np.dot(p - Jp, Wp - Jp) / L / L
            if best is None or abs(t - 0.53) < abs(best[0] - 0.53):
                best = (t, p)
        Ep = best[1]
        self.Jp, self.Ep, self.Wp, self.Tp = Jp, Ep, Wp, T

    def px_to_xz(self, p):
        return np.array([(p[0] - self.sh.mid["front"]) * self.sh.S, self.sh.z(p[1])])

    def torso_at(self, r):
        """(half width, y front, y back) at a row, from the front and side runs."""
        sh = self.sh
        fr = self.front_run(r)
        sr = self.side_run(r)
        a = (fr[1] - fr[0]) / 2 * sh.S if fr else None
        yf = -(sr[1] - sh.mid["side"]) * sh.S
        yb = -(sr[0] - sh.mid["side"]) * sh.S
        return a, yf, yb

    def leg_at(self, r):
        """The left leg at a row: (x in, x out, y front, y back)."""
        sh = self.sh
        mf = sh.mid["front"]
        r = int(round(r))
        # the leg: the widest run on the middle's right that starts near it (not the hand, not a stray line)
        rs = [ab for ab in runs_of(sh.fm[r]) if ab[1] > mf + 2 and ab[0] < mf + 0.14 * self.H / sh.S]
        ab = max(rs, key=lambda ab: ab[1] - max(ab[0], mf))
        xin = max(0.0, (ab[0] - mf) * sh.S)
        xout = (ab[1] - mf) * sh.S
        sr = self.side_run(r)
        yf = -(sr[1] - sh.mid["side"]) * sh.S
        yb = -(sr[0] - sh.mid["side"]) * sh.S
        return xin, xout, yf, yb


# ------------------------------------------------------------------------------------------------------------------
# Building the body
# ------------------------------------------------------------------------------------------------------------------

def build_body(M, B):
    sh = B.sh
    S = sh.S
    k = B.k
    H = B.H
    N = TORSO_N
    theta = np.arange(N) * math.tau / N
    J = B.px_to_xz(B.Jp)
    E = B.px_to_xz(B.Ep)
    Wr = B.px_to_xz(B.Wp)
    armpit_z = sh.z(B.armpit_row)
    shoulder_z = sh.z(B.shoulder_row)
    neckbase_z = sh.z(B.neckbase_row)
    neck_z = sh.z(B.neck_row)
    crotch_z = B.crotch_z
    # the torso's rows: crotch to armpit (measured), the arm's root (3), the shoulder line, the neck's base, the neck
    meas = []
    n_low = 11
    for i in range(n_low):
        z = lerp(crotch_z, armpit_z - 0.012 * k, i / (n_low - 1))
        a, yf, yb = B.torso_at(sh.row(z))
        meas.append((z, a, yf, yb))
    # rows where a hand hangs over the side view: the torso's depth there from the rows round them
    hand_top = sh.z(B.Wp[1]) + 0.03 * k
    hand_bot = sh.z(B.tip_row) - 0.03 * k
    good = [m_ for m_ in meas if not (hand_bot < m_[0] < hand_top)]
    if 1 < len(good) < len(meas):
        meas = [(z, a, interp_rows([(g_[0], g_[2]) for g_ in good], z), interp_rows([(g_[0], g_[3]) for g_ in good], z))
                if hand_bot < z < hand_top else (z, a, yf, yb) for z, a, yf, yb in meas]
    # smooth the side's back and front over rows where an arm may hang over the side view
    z_a, a_a, yf_a, yb_a = meas[-1]
    root_r = (B.track[B.armpit_row][1] - B.track[B.armpit_row][0]) / 2 * S
    top_z = min(J[1] + 0.75 * root_r, shoulder_z - 0.25 * root_r)
    rings = []   # (z, a, yf, yb, p)
    for z, a, yf, yb in meas:
        rings.append([z, a, yf, yb, 0.86])
    yc_a = (yf_a + yb_a) / 2
    d_a = (yb_a - yf_a) / 2
    rings.append([armpit_z + 0.004 * k, a_a * 1.0, yf_a + 0.004, yb_a, 0.84])
    rings.append([lerp(armpit_z, top_z, 0.55), lerp(a_a, J[0], 0.6), yc_a - d_a * 0.92, yc_a + d_a * 0.95, 0.8])
    rings.append([top_z, J[0] + 0.01 * k, yc_a - d_a * 0.72, yc_a + d_a * 0.8, 0.74])
    ia = n_low
    # the shoulder line (trapezius) and the neck's base
    n_a, n_yf, n_yb = B.torso_at(B.neckbase_row)
    nb_a = max(B.neck_half * 1.12, 0.0)
    trap_z = lerp(top_z, neckbase_z, 0.5)
    rings.append([trap_z, lerp(J[0], nb_a, 0.55), lerp(yc_a - d_a * 0.6, n_yf, 0.5), lerp(yc_a + d_a * 0.7, n_yb, 0.5), 0.78])
    rings.append([neckbase_z, nb_a, n_yf, n_yb, 0.9])
    _, nk_yf, nk_yb = B.torso_at(B.neck_row)
    rings.append([neck_z, B.neck_half, nk_yf, nk_yb, 0.95])
    T = []
    for ri, (z, a, yf, yb, p) in enumerate(rings):
        yc = (yf + yb) / 2
        x, y = ring_shape(theta, a, yc - yf, yb - yc, p)
        if ri >= len(rings) - 2:
            part = "neck"
        else:
            part = "torso"
        idx = [M.add((x[j], yc + y[j], z), part) for j in range(N)]
        T.append(idx)
    # women: the bust as two soft masses under the chemise
    if sh.cfg["sex"] == "f":
        P = M.arr()
        zs = [M.P[r[0]][2] for r in T[:ia]]
        # the bust's row: where the side view's front stands furthest forward in the upper half of the torso
        upper = [i for i in range(ia) if M.P[T[i][0]][2] > lerp(crotch_z, armpit_z, 0.55)]
        bi = min(upper, key=lambda i: M.P[T[i][0]][1])
        for i in range(max(0, bi - 2), min(ia + 1, bi + 3)):
            w = [0.5, 1.0, 0.5][min(2, abs(i - bi))] if abs(i - bi) <= 1 else 0.25
            for j in range(N):
                th = theta[j]
                if math.cos(th) > 0.3:
                    dip = 0.06 * w * math.exp(-(th if th < math.pi else th - math.tau) ** 2 / 0.06)
                    p = M.P[T[i][j]]
                    yc = (M.P[T[i][0]][1] + M.P[T[i][12]][1]) / 2
                    p[1] = yc + (p[1] - yc) * (1 - dip)
    # faces, leaving the arm holes (rings ia..ia+2, columns 4..8 and 16..20)
    holes = set()
    for r0 in (ia, ia + 1):
        for kk in list(range(HOLE_K[0], HOLE_K[1])) + list(range(N - HOLE_K[1], N - HOLE_K[0])):
            holes.add((r0, kk))
    for ri in range(len(T) - 1):
        for j in range(N):
            if (ri, j) in holes:
                continue
            a, b = T[ri][j], T[ri][(j + 1) % N]
            c, d = T[ri + 1][(j + 1) % N], T[ri + 1][j]
            isl = "neck" if ri >= len(T) - 3 else ("torso_front" if (j < 6 or j >= 18) else "torso_back")
            M.face([a, d, c, b], isl)
    # the points inside the holes are not used: put them on the hole's middle (they are dropped later)
    M.unused = set()
    for kk in (5, 6, 7, 17, 18, 19):
        M.unused.add(T[ia + 1][kk])
    joints = {}
    arm_rings = {}
    for side in (1, -1):
        arm_rings[side] = build_arm(M, B, T, ia, side, J, E, Wr, joints)
    leg_rings = build_legs(M, B, T, joints)
    return T, ia, arm_rings, leg_rings, joints


def hole_loop(T, ia, side):
    """The hole's boundary in order round: armpit (front to back), up the back, the top (back to front), down."""
    k0, k1 = HOLE_K
    if side == 1:
        ks = list(range(k0, k1 + 1))
    else:
        ks = [TORSO_N - kk for kk in range(k0, k1 + 1)]
    loop = [T[ia][kk] for kk in ks]
    loop.append(T[ia + 1][ks[-1]])
    loop += [T[ia + 2][kk] for kk in reversed(ks)]
    loop.append(T[ia + 1][ks[0]])
    return loop


def arm_frame(t):
    """u: across the arm in the front view's plane (outward and up), v: forward (-Y)."""
    t = t / np.linalg.norm(t)
    v = np.array([0.0, -1.0, 0.0])
    v = v - t * np.dot(v, t)
    v /= np.linalg.norm(v)
    u = np.cross(v, t)
    if u[0] * np.sign(t[0] if abs(t[0]) > 1e-6 else 1) < 0:
        u = -u
    return u, v


def measure_across(B, Pc, t, side):
    """The arm's half widths across its axis at a point (model x, z of the left arm), from the front view:
    (outer, inner) in metres, the inner limited where the arm touches the body."""
    sh = B.sh
    S = sh.S
    c0 = sh.mid["front"] + Pc[0] / S
    r0 = sh.row(Pc[1])
    # the image direction across the axis, outward (away from the body)
    tc, tr = t[0], -t[1]
    n = np.array([tr, -tc])
    if n[0] < 0:
        n = -n
    n /= np.linalg.norm(n)
    fm = sh.fm
    def walk(sgn):
        for s in range(0, 400):
            c = int(round(c0 + sgn * n[0] * s))
            r = int(round(r0 + sgn * n[1] * s))
            if r < 0 or r >= sh.H or c < 0 or c >= sh.W or not fm[r, c]:
                return s
        return 400
    eo, ei = walk(1), walk(-1)
    if ei > 1.35 * eo:
        ei = eo
    return eo * S, ei * S


def build_arm(M, B, T, ia, side, J, E, Wr, joints):
    sh = B.sh
    k = B.k
    S = sh.S
    sfx = "_l" if side == 1 else "_r"
    # the arm's axis in model space (the left arm measured, mirrored for the right)
    torso_mid_y = (M.P[T[ia][0]][1] + M.P[T[ia][12]][1]) / 2
    yJ = torso_mid_y + sh.cfg.get("arm_dy", 0.0)
    yW = yJ + sh.cfg.get("wrist_dy", -0.03 * k)
    Jw = np.array([J[0], yJ, J[1]])
    Ew = np.array([E[0], lerp(yJ, yW, 0.5) + 0.01 * k, E[1]])
    Ww = np.array([Wr[0], yW, Wr[1]])
    L1 = np.linalg.norm(Ew - Jw)
    L2 = np.linalg.norm(Ww - Ew)
    Lh = B.hand_len
    stub = 0.025 * k
    total = L1 + L2 - stub
    def at(s):
        if s <= L1:
            return Jw + (Ew - Jw) * (s / L1), (Ew - Jw) / L1
        return Ew + (Ww - Ew) * ((s - L1) / L2), (Ww - Ew) / L2
    def tangent(s):
        t1 = (Ew - Jw) / L1
        t2 = (Ww - Ew) / L2
        w = float(smoothstep(L1 - 0.05 * k, L1 + 0.05 * k, s))
        t = t1 * (1 - w) + t2 * w
        return t / np.linalg.norm(t)
    loop = hole_loop(T, ia, side)
    # the hole's points in the arm's frame at the root: their angles round the axis
    P0 = np.array([M.P[i] for i in loop])
    if side == -1:
        P0 = P0 * np.array([-1, 1, 1])
    t0 = tangent(0.0)
    u0, v0 = arm_frame(t0)
    rel = P0 - Jw
    ang0 = np.unwrap(np.arctan2(rel @ v0, rel @ u0))
    # keep them going round the same way as uniform angles
    if ang0[-1] < ang0[0]:
        dirn = -1
    else:
        dirn = 1
    uni = ang0[0] + dirn * np.arange(ARM_N) * math.tau / ARM_N
    # the arm's rings: from just out of the root to the wrist's stub
    root_r = (B.track[B.armpit_row][1] - B.track[B.armpit_row][0]) / 2 * S
    s_first = 0.55 * root_r
    ss = list(np.linspace(s_first, L1 - 0.06 * k, 6)) + [L1 - 0.025 * k, L1, L1 + 0.025 * k] + \
        list(np.linspace(L1 + 0.06 * k, total, 6))
    depth_ratio = sh.cfg.get("arm_depth", ((0.0, 1.0), (0.3, 0.98), (0.5, 0.9), (0.62, 0.95), (0.85, 0.85),
                                           (1.0, 0.7)))
    rings = [loop]
    prev_centre = None
    for i, s in enumerate(ss):
        C, _ = at(s)
        t = tangent(s)
        u, v = arm_frame(t)
        eo, ei = measure_across(B, (C[0], C[2]), (t[0], t[2]), side)
        ru = (eo + ei) / 2
        shift = (eo - ei) / 2
        uxz = np.array([u[0], 0.0, u[2]])
        uxz /= np.linalg.norm(uxz)
        C = C + uxz * shift
        f = s / (L1 + L2)
        rv = ru * interp_rows(list(depth_ratio), f)
        w = min(1.0, (i + 1) / 4.0)
        angs = ang0 * (1 - w) + uni * w
        idx = []
        for a in angs:
            ca, sa = math.cos(a), math.sin(a)
            p = C + u * ru * sgnpow(ca, 0.92) + v * rv * sgnpow(sa, 0.92)
            if side == -1:
                p = p * np.array([-1, 1, 1])
            idx.append(M.add(p, "arm" + sfx))
        rings.append(idx)
    for ri in range(len(rings) - 1):
        A, Bq = rings[ri], rings[ri + 1]
        n = len(A)
        for j in range(n):
            M.face([A[j], A[(j + 1) % n], Bq[(j + 1) % n], Bq[j]], "arm" + sfx)
    m = np.array([side, 1, 1])
    joints["shoulder" + sfx] = Jw * m
    joints["elbow" + sfx] = Ew * m
    joints["wrist" + sfx] = Ww * m
    joints["arm_t" + sfx] = (Ww - Ew) / L2 * m
    M.arm_axis = getattr(M, "arm_axis", {})
    M.arm_axis[side] = (Jw * m, Ew * m, Ww * m)
    return rings


def build_legs(M, B, T, joints):
    sh = B.sh
    k = B.k
    S = sh.S
    H = B.H
    crotch_z = B.crotch_z
    N = TORSO_N
    bottom = T[0]
    c_y = (M.P[bottom[0]][1] + M.P[bottom[12]][1]) / 2
    crotch = M.add((0.0, c_y, crotch_z - 0.012 * k), "torso")
    ankle_z = 0.052 * H
    leg_z = list(np.linspace(crotch_z - 0.035 * k, ankle_z, 14))
    foot_z = [0.04 * k, 0.026 * k, 0.012 * k, 0.0]
    out = {}
    for side in (1, -1):
        sfx = "_l" if side == 1 else "_r"
        if side == 1:
            loop = [bottom[kk] for kk in range(0, 13)] + [crotch]
        else:
            loop = [bottom[kk % N] for kk in range(N, N - 13, -1)] + [crotch]
        meas = []
        for z in leg_z:
            xin, xout, yf, yb = B.leg_at(sh.row(z))
            meas.append((z, xin, xout, yf, yb))
        # the leg's middle at its top, for the angles of the loop
        z0, xin0, xout0, yf0, yb0 = meas[0]
        P0 = np.array([M.P[i] for i in loop])
        if side == -1:
            P0 = P0 * np.array([-1, 1, 1])
        # the angles round the loop's own middle (a hand over the side view must not move it off the loop)
        c0 = P0[:, :2].mean(0)
        ang0 = np.unwrap(np.arctan2(P0[:, 0] - c0[0], -(P0[:, 1] - c0[1])))
        dirn = 1 if ang0[-1] > ang0[0] else -1
        uni = ang0[0] + dirn * np.arange(LEG_N) * math.tau / LEG_N
        # the uniform angles turned to sit as close to the loop's as they can
        off = np.mean(np.angle(np.exp(1j * (ang0 - uni))))
        uni = uni + off
        rings = [loop]
        # rows where a hand hangs over the side view: the depth there from the rows round them
        hand_top = sh.z(B.Wp[1]) + 0.03 * k
        hand_bot = sh.z(B.tip_row) - 0.03 * k
        good = [(z, yf, yb) for z, xin, xout, yf, yb in meas if not (hand_bot < z < hand_top)]
        thigh_k = sh.cfg.get("thigh_k", 1.0)
        for i, (z, xin, xout, yf, yb) in enumerate(meas):
            if hand_bot < z < hand_top and len(good) > 2:
                yf = interp_rows(sorted([(g[0], g[1]) for g in good]), z)
                yb = interp_rows(sorted([(g[0], g[2]) for g in good]), z)
            cx, cy = (xin + xout) / 2, (yf + yb) / 2
            a = (xout - xin) / 2
            bfr, bba = cy - yf, yb - cy
            w = min(1.0, (i + 1) / 3.0)
            angs = ang0 * (1 - w) + uni * w
            idx = []
            for an in angs:
                x = cx + a * sgnpow(math.sin(an), 0.9)
                cA = math.cos(an)
                y = cy - (bfr if cA > 0 else bba) * sgnpow(cA, 0.9)
                idx.append(M.add((side * x, y, z), "leg" + sfx))
            rings.append(idx)
        # the feet: level rings from the ankle down to the sole, toed out
        za, xin, xout, yf, yb = meas[-1]
        ank = np.array([(xin + xout) / 2, (yf + yb) / 2])
        yaw = math.radians(sh.cfg.get("toe_out", 18.0))
        for fi, z in enumerate(foot_z):
            r = int(round(sh.row(max(z, 0.004 * k))))
            sr = B.side_run(r)
            heel = -(sr[0] - sh.mid["side"]) * S
            toe = -(sr[1] - sh.mid["side"]) * S
            fr = [ab for ab in runs_of(sh.fm[r]) if ab[1] > sh.mid["front"] + 2 and ab[0] < sh.mid["front"] + 0.16 * H / S]
            fr = max(fr, key=lambda ab: ab[1] - max(ab[0], sh.mid["front"]))
            fw = (fr[1] - fr[0]) / 2 * S * sh.cfg.get("foot_w", 0.95)
            cy = (heel + toe) / 2
            half = (heel - toe) / 2
            cx = ank[0]
            idx = []
            for an in uni:
                s_, c_ = math.sin(an), math.cos(an)
                width = fw * (0.78 + 0.22 * max(0.0, c_))
                x = width * sgnpow(s_, 0.8)
                y = -half * sgnpow(c_, 0.7)
                # toe out about the ankle
                yy = cy + y - ank[1]
                xr = x * math.cos(yaw) - yy * math.sin(yaw)
                yr = x * math.sin(yaw) + yy * math.cos(yaw)
                idx.append(M.add((side * (cx + xr), ank[1] + yr, z), "foot" + sfx))
            rings.append(idx)
        for ri in range(len(rings) - 1):
            A, Bq = rings[ri], rings[ri + 1]
            n = len(A)
            for j in range(n):
                M.face([A[j], A[(j + 1) % n], Bq[(j + 1) % n], Bq[j]], "leg" + sfx)
        # the sole: a fan round its middle
        last = rings[-1]
        cpt = np.mean([M.P[i] for i in last], 0)
        ci = M.add(cpt, "foot" + sfx)
        for j in range(LEG_N):
            M.face([last[j], last[(j + 1) % LEG_N], ci], "sole" + sfx)
        out[side] = rings
        # joints
        hip = np.array([side * (xin0 + xout0) / 2 * 0.92, c0[1] + 0.005, crotch_z + 0.055 * k])
        kz = 0.285 * H
        kin, kout, kyf, kyb = B.leg_at(sh.row(kz))
        knee = np.array([side * (kin + kout) / 2, (kyf + kyb) / 2 - 0.01 * k, kz])
        ankle = np.array([side * ank[0], ank[1] + 0.012 * k, 0.065 * k])
        fwd = np.array([side * math.sin(yaw), -math.cos(yaw), 0.0])
        ball = ankle + fwd * 0.125 * k
        ball[2] = 0.022 * k
        joints["hip" + sfx], joints["knee" + sfx], joints["ankle" + sfx], joints["ball" + sfx] = hip, knee, ankle, ball
        joints["foot_fwd" + sfx] = fwd
    M.crotch = crotch
    return out


# ------------------------------------------------------------------------------------------------------------------
# The base meshes (tools/FIGURE_HEADS.md)
# ------------------------------------------------------------------------------------------------------------------

def load_base(name, mix=None, unsubdiv=0, subdiv=0, collapse=None):
    with bpy.data.libraries.load(BUNDLE, link=False) as (src, dst):
        dst.objects = [n for n in src.objects if n.replace(" ", "") == name.replace(" ", "")]
    o = dst.objects[0]
    bpy.context.scene.collection.objects.link(o)
    o.modifiers.clear()
    me = o.data
    if me.shape_keys:
        kb = me.shape_keys.key_blocks
        base = np.array([tuple(p.co) for p in kb["Basis"].data], float)
        P = base.copy()
        for key, wgt in (mix or {}).items():
            P += wgt * (np.array([tuple(p.co) for p in kb[key].data], float) - base)
        o.shape_key_clear()
        for v, p in zip(me.vertices, P):
            v.co = Vector(p)
    # symmetrise across x
    P = np.array([tuple(v.co) for v in me.vertices], float)
    kd = kdtree.KDTree(len(P))
    for i, p in enumerate(P):
        kd.insert(Vector(p), i)
    kd.balance()
    if name.startswith("Head"):
        Q = P.copy()
        for i, p in enumerate(P):
            _, j, d = kd.find(Vector((-p[0], p[1], p[2])))
            if d < 0.004:
                q = (p + P[j] * np.array([-1, 1, 1])) / 2
                Q[i] = q
            if abs(p[0]) < 1e-4:
                Q[i][0] = 0.0
        for v, p in zip(me.vertices, Q):
            v.co = Vector(p)
    bpy.context.view_layer.objects.active = o
    o.select_set(True)
    if unsubdiv:
        m = o.modifiers.new("un", "DECIMATE")
        m.decimate_type = "UNSUBDIV"
        m.iterations = unsubdiv
        bpy.ops.object.modifier_apply(modifier=m.name)
    if subdiv:
        m = o.modifiers.new("sub", "SUBSURF")
        m.levels = subdiv
        m.render_levels = subdiv
        m.uv_smooth = "PRESERVE_CORNERS"
        bpy.ops.object.modifier_apply(modifier=m.name)
    if collapse:
        m = o.modifiers.new("dec", "DECIMATE")
        m.decimate_type = "COLLAPSE"
        m.ratio = collapse
        m.use_symmetry = name.startswith("Head")
        m.symmetry_axis = "X"
        m.delimit = {"UV"}
        bpy.ops.object.modifier_apply(modifier=m.name)
    me = o.data
    P = np.array([tuple(v.co) for v in me.vertices], float)
    faces = [list(p.vertices) for p in me.polygons]
    uvl = me.uv_layers[0].data
    uvs = [[tuple(uvl[li].uv) for li in p.loop_indices] for p in me.polygons]
    bpy.data.objects.remove(o, do_unlink=True)
    return P, faces, uvs


def open_loops(faces):
    from collections import Counter
    c = Counter()
    for f in faces:
        for k in range(len(f)):
            a, b = f[k], f[(k + 1) % len(f)]
            c[(min(a, b), max(a, b))] += 1
    nxt = {}
    for (a, b), n in c.items():
        if n == 1:
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


def zipper(M, A, Bl, centre, axis, isl):
    """Triangles between two closed loops of different counts, merged by angle round an axis through centre."""
    axis = axis / np.linalg.norm(axis)
    ref = np.array([0.0, -1.0, 0.0]) if abs(axis[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
    e1 = ref - axis * np.dot(ref, axis)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(axis, e1)
    def order(loop):
        Q = np.array([M.P[i] for i in loop]) - centre
        a = np.mod(np.arctan2(Q @ e2, Q @ e1), math.tau)
        o = np.argsort(a)
        return [loop[i] for i in o], a[o]
    A, a = order(A)
    Bl, b = order(Bl)
    na, nb = len(A), len(Bl)
    ae = np.append(a, a[0] + math.tau)
    be = np.append(b, b[0] + math.tau)
    i = j = 0
    while i < na or j < nb:
        if j >= nb or (i < na and ae[i + 1] <= be[j + 1]):
            M.face([A[i % na], A[(i + 1) % na], Bl[j % nb]], isl)
            i += 1
        else:
            M.face([A[i % na], Bl[(j + 1) % nb], Bl[j % nb]], isl)
            j += 1


def head_marks(P):
    """The base head's landmarks (z of chin, nose tip, mouth, nasion, crown; y of the nose tip)."""
    mid = np.where(np.abs(P[:, 0]) < 1e-4)[0]
    front = [i for i in mid if P[i, 1] < -0.02]
    chin_z = P[P[:, 1] < 0.0, 2].min()
    tip = min([i for i in front if -0.03 < P[i, 2] < 0.04], key=lambda i: P[i, 1])
    zt = P[tip, 2]
    nas = max([i for i in front if zt + 0.01 < P[i, 2] < zt + 0.07], key=lambda i: P[i, 1])
    mouth = max([i for i in front if chin_z + 0.02 < P[i, 2] < zt - 0.02], key=lambda i: P[i, 1])
    return dict(chin=chin_z, tip_z=zt, tip_y=P[tip, 1], nasion=P[nas, 2], mouth=P[mouth, 2], crown=P[:, 2].max(),
                back=P[:, 1].max())


def build_head(M, B, mix, neck_ring, T):
    """The base head fitted to the sheet's head, its underside opened and joined to the neck's top ring."""
    sh = B.sh
    S = sh.S
    P, faces, uvs = load_base("Head - Generic Topology", mix=mix, subdiv=1, collapse=0.47)
    base0 = P.copy()
    mk = head_marks(P)
    # the opening under the jaw: downward faces inside an oval round the neck
    Pc = np.array([P[f].mean(0) for f in faces])
    Nf = []
    for f in faces:
        n = np.cross(P[f[1]] - P[f[0]], P[f[2]] - P[f[0]])
        Nf.append(n / max(np.linalg.norm(n), 1e-12))
    Nf = np.array(Nf)
    neck_y0 = lerp(mk["tip_y"], mk["back"], 0.52)
    ell = (Pc[:, 0] / 0.047) ** 2 + ((Pc[:, 1] - neck_y0) / 0.058) ** 2
    cut = (ell < 1.0) & (Pc[:, 2] < mk["chin"] + 0.045) & (Nf[:, 2] < -0.25)
    keep = [i for i in range(len(faces)) if not cut[i]]
    faces = [faces[i] for i in keep]
    uvs = [uvs[i] for i in keep]
    loops = open_loops(faces)
    print("  head: %d faces, %d cut, open loops %s" % (len(faces), int(cut.sum()), [len(l) for l in loops]))
    # the sheet's head: chin, eye line, crown rows; jaw widths and the profile
    z_chin, z_eye, z_crown = sh.z(sh.chin), sh.z(sh.eye), sh.z(sh.crown)
    zmap_src = [mk["chin"], mk["nasion"] - 0.004, mk["crown"]]
    zmap_dst = [z_chin, z_eye, z_crown]
    def map_z(z):
        z = np.asarray(z, float)
        lo = z < zmap_src[0]
        out = np.interp(z, zmap_src, zmap_dst)
        sl = (zmap_dst[1] - zmap_dst[0]) / (zmap_src[1] - zmap_src[0])
        out[lo] = zmap_dst[0] + (z[lo] - zmap_src[0]) * sl
        return out
    # width: the jaw's half width at the mouth's row
    mouth_row = sh.row(float(map_z(np.array([mk["mouth"]]))[0]))
    fr = run_at(sh.fm[int(mouth_row)], int(sh.mid["front"]))
    jaw_half = (fr[1] - fr[0]) / 2 * S
    near = np.abs(P[:, 2] - mk["mouth"]) < 0.012
    base_half = np.abs(P[near, 0]).max()
    sx = jaw_half / base_half * sh.cfg.get("head_wide", 1.0)
    vs = (z_eye - z_chin) / (zmap_src[1] - zmap_src[0])
    sy = (sx + vs) / 2 * sh.cfg.get("head_deep", 1.0)
    Q = np.empty_like(P)
    Q[:, 2] = map_z(P[:, 2])
    # the skull above the ears: as wide as the hair's outline at the temples less the hair
    k_ = B.k
    rc = int(sh.eye - 0.3 * (sh.chin - sh.eye))
    fr2 = run_at(sh.fm[rc], int(sh.mid["front"]))
    top_half = (fr2[1] - fr2[0]) / 2 * S - sh.cfg.get("hair_side", 0.018) * k_
    band = np.abs(Q[:, 2] - sh.z(rc)) < 0.01
    sx_top = top_half / max(np.abs(P[band, 0]).max(), 1e-3)
    sx_top = min(max(sx_top, sx * 0.95), sx * 1.2)
    z_mouth = float(map_z(np.array([mk["mouth"]]))[0])
    sxz = np.interp(Q[:, 2], [z_mouth, z_eye, sh.z(rc)], [sx, lerp(sx, sx_top, 0.6), sx_top])
    print("  head widths: jaw scale %.2f, skull scale %.2f" % (sx, sx_top))
    Q[:, 0] = P[:, 0] * sxz
    Q[:, 1] = (P[:, 1] - mk["tip_y"]) * sy
    # the nose tip's place in the side view
    tip_row = int(round(sh.row(float(map_z(np.array([mk["tip_z"]]))[0]))))
    front_cols = []
    for r in range(tip_row - 6, tip_row + 7):
        ra = runs_of(sh.sm[r])
        if ra:
            front_cols.append(max(b for a, b in ra))
    tip_y = -(np.median(front_cols) - sh.mid["side"]) * S
    Q[:, 1] += tip_y
    # the back of the skull: inside the hair's outline (at a row below a bun) by the hair's thickness
    rb = int(sh.eye + 0.4 * (sh.chin - sh.eye))
    ra_ = runs_of(sh.sm[rb])
    if ra_:
        back_t = -(min(a for a, b in ra_) - sh.mid["side"]) * S - sh.cfg.get("hair_back", 0.015) * k_
        band = np.abs(Q[:, 2] - sh.z(rb)) < 0.012
        cur = Q[band, 1].max()
        ymid = lerp(tip_y, cur, 0.45)
        f_ = (back_t - ymid) / max(cur - ymid, 1e-3)
        f_ = min(max(f_, 0.8), 1.3)
        behind = Q[:, 1] > ymid
        Q[behind, 1] = ymid + (Q[behind, 1] - ymid) * f_
        print("  head depth behind the ears scaled %.2f" % f_)
    # the profile: the face's middle pulled to the side view's front row by row (brow to chin)
    for it in range(3):
        rows = np.arange(int(sh.eye + 0.45 * (sh.chin - sh.eye)), int(sh.chin) + 1, 3)
        prof = []
        for r in rows:
            ra = runs_of(sh.sm[r])
            if ra:
                prof.append((sh.z(r), -(max(b for a, b in ra) - sh.mid["side"]) * S))
        prof = sorted(prof)
        mid = (np.abs(Q[:, 0]) < 0.004) & (Q[:, 1] < tip_y + 0.06)
        mz = Q[mid, 2]
        my = Q[mid, 1]
        o = np.argsort(mz)
        mz, my = mz[o], my[o]
        half = np.abs(Q[:, 0]).max()
        for i in range(len(Q)):
            z = Q[i, 2]
            if z < prof[0][0] - 0.01 or z > prof[-1][0] + 0.005 or Q[i, 1] > tip_y + 0.09:
                continue
            target = np.interp(z, [p[0] for p in prof], [p[1] for p in prof])
            cur = np.interp(z, mz, my)
            fall = math.exp(-(Q[i, 0] / (0.45 * half)) ** 2) * float(smoothstep(tip_y + 0.09, tip_y + 0.04, Q[i, 1]))
            Q[i, 1] += 0.45 * (target - cur) * fall
    # the jaw: widths row by row from the mouth to the chin (the front view)
    for it in range(2):
        rows = np.arange(int(mouth_row) - 10, int(sh.chin - 0.14 * (sh.chin - sh.eye)), 3)
        for r in rows:
            fr = run_at(sh.fm[r], int(sh.mid["front"]))
            if not fr:
                continue
            tw = (fr[1] - fr[0]) / 2 * S
            z = sh.z(r)
            band = np.abs(Q[:, 2] - z) < 0.006
            band &= Q[:, 1] < tip_y + 0.11
            if band.sum() < 3:
                continue
            cw = np.abs(Q[band, 0]).max()
            if cw < 1e-4:
                continue
            f = lerp(1.0, tw / cw, 0.5)
            f = min(max(f, 0.85), 1.15)
            wz = np.exp(-((Q[:, 2] - z) / 0.012) ** 2)
            Q[:, 0] *= 1 + (f - 1) * wz * (Q[:, 1] < tip_y + 0.11)
    # into the mesh
    idx = [M.add(q, "head") for q in Q]
    for i, q in zip(idx, base0):
        M.base[i] = q
    for f, uv in zip(faces, uvs):
        M.face([idx[v] for v in f], "head", uv)
    loop = max(loops, key=len)
    hole = [idx[v] for v in loop]
    # the neck's top ring joined to the opening
    centre = np.mean([M.P[i] for i in neck_ring], 0)
    centre2 = np.mean([M.P[i] for i in hole], 0)
    # the neck's top ring kept under the opening (a short neck must not rise into the jaw)
    low = min(M.P[i][2] for i in hole) - 0.012 * B.k
    top = max(M.P[i][2] for i in neck_ring)
    if top > low:
        below = np.mean([M.P[i][2] for i in T[-2]])
        for i in neck_ring:
            M.P[i][2] = max(below + 0.4 * (low - below), M.P[i][2] - (top - low))
    zipper(M, neck_ring, hole, (centre + centre2) / 2, centre2 - centre + np.array([0, 0, 0.05]), "neck")
    M.head_idx = idx
    return dict(chin=z_chin, eye=z_eye, crown=z_crown, tip_y=tip_y)


def match_wrist(M, wr, remap=None):
    """The arm's last two rings sized and centred to the hand's opening (no step at the wrist)."""
    rings, hole = wr
    Ph_ = np.array([M.P[i] for i in hole])
    hc = Ph_.mean(0)
    rh = np.linalg.norm(Ph_ - hc, axis=1).mean()
    ax = hc - np.array([M.P[i] for i in rings[0]]).mean(0)
    ax /= np.linalg.norm(ax)
    ra = np.array([M.P[i] for i in rings[0]])
    r_arm = np.linalg.norm(ra - ra.mean(0), axis=1).mean()
    r_t = max(rh, 0.5 * (rh + r_arm))
    for i in hole:
        M.P[i] = hc + (M.P[i] - hc) * (r_t / rh)
    rh = r_t
    for ring, wgt in ((rings[2], 1.0), (rings[1], 0.5)):
        Q = np.array([M.P[i] for i in ring])
        c = Q.mean(0)
        r = np.linalg.norm(Q - c, axis=1).mean()
        s = lerp(1.0, rh * 1.04 / r, wgt)
        shift = hc - c
        shift = shift - ax * np.dot(shift, ax)
        for i in ring:
            M.P[i] = c + (M.P[i] - c) * s + shift * wgt


def build_hands(M, B, joints, arm_rings):
    """The base hand sized to the sheet's hands and joined at each wrist; finger joints from its own shape."""
    P, faces, uvs = load_base("Hand - Stylized", unsubdiv=2, collapse=0.75)
    top = P[:, 2].max()
    cap = [i for i, f in enumerate(faces) if all(P[v, 2] > top - 0.004 for v in f)]
    faces = [f for i, f in enumerate(faces) if i not in cap]
    uvs = [u for i, u in enumerate(uvs) if i not in cap]
    loops = open_loops(faces)
    loop = max(loops, key=len)
    cap_c = P[loop].mean(0)
    tip_z = P[:, 2].min()
    wrist_z = cap_c[2] - 0.03
    base_len = wrist_z - tip_z
    k = B.hand_len / base_len * B.sh.cfg.get("hand_scale", 1.0)
    # fingers in the base frame: points below the knuckles, by x
    knuck = tip_z + 0.43 * (wrist_z - tip_z)
    low = np.where(P[:, 2] < knuck)[0]
    thumb_x = cap_c[0] + 0.035
    fing = [i for i in low if P[i, 0] < thumb_x]
    xs = P[fing, 0]
    cents = np.percentile(xs, [12, 38, 62, 88])
    for _ in range(10):
        lab = np.argmin(np.abs(xs[:, None] - cents[None, :]), 1)
        cents = np.array([xs[lab == q].mean() if (lab == q).any() else cents[q] for q in range(4)])
    order = np.argsort(-cents)   # +X is the thumb's side: index is the largest x
    finger_of = {}
    fjoints = {}
    for rank, q in enumerate(order):
        name = FINGERS[rank]
        pts = [fing[i] for i in range(len(fing)) if lab[i] == q]
        for i in pts:
            finger_of[i] = name
        zs = P[pts, 2]
        tip = P[pts][np.argmin(zs)]
        root = np.array([cents[q], P[pts, 1].mean(), knuck + 0.012])
        Lf = root[2] - tip[2]
        fjoints[name] = [root, root + (tip - root) * 0.46, root + (tip - root) * 0.74]
    # the thumb: points well out on +X above the knuckles
    th = [i for i in range(len(P)) if P[i, 0] > thumb_x and P[i, 2] > tip_z + 0.03]
    for i in th:
        finger_of[i] = "thumb"
    far = P[th][np.argmax(P[th, 0] - 0.5 * P[th, 2])]
    t1 = np.array([cap_c[0] + 0.022, cap_c[1] - 0.004, wrist_z - 0.025])
    fjoints["thumb"] = [t1, t1 + (far - t1) * 0.45, t1 + (far - t1) * 0.75]
    for side in (1, -1):
        sfx = "_l" if side == 1 else "_r"
        Jw, Ew, Ww = M.arm_axis[side]
        Wl = Ww * np.array([side, 1, 1])
        El = Ew * np.array([side, 1, 1])
        f = (Wl - El) / np.linalg.norm(Wl - El)   # fingers' way (left arm frame, mirrored below)
        # the palm faces the thigh: for the left hand (at +X) inward is -X
        n_in = np.array([-1.0, 0.0, 0.0])
        n_in = n_in - f * np.dot(n_in, f)
        n_in /= np.linalg.norm(n_in)
        # turned about the arm so the palm faces partly back (the sheets show the backs of the hands half on)
        tw = math.radians(B.sh.cfg.get("palm_back", 35.0))
        bk = np.array([0.0, 1.0, 0.0])
        bk = bk - f * np.dot(bk, f) - n_in * np.dot(bk, n_in)
        bk /= np.linalg.norm(bk)
        n_in = n_in * math.cos(tw) + bk * math.sin(tw)
        M.palm = getattr(M, "palm", {})
        M.palm[side] = n_in * np.array([side, 1, 1])
        # the bundle's hand is a right hand: fingers -Z, palm +Y, thumb +X; built as the right hand at -X, mirrored
        fr = f * np.array([-1, 1, 1])
        nr = n_in * np.array([-1, 1, 1])
        tr = np.cross(fr, nr)
        R = np.stack([tr, nr, -fr], 1)
        Wr = Wl * np.array([-1, 1, 1])
        def place(p):
            q = R @ ((np.asarray(p) - np.array([cap_c[0], cap_c[1], wrist_z])) * k) + Wr
            return q * np.array([-1, 1, 1]) if side == 1 else q
        idx = [M.add(place(p), "hand" + sfx) for p in P]
        for i, v in enumerate(idx):
            if i in finger_of:
                M.finger[v] = finger_of[i]
        for fc, uv in zip(faces, uvs):
            vs = [idx[v] for v in fc]
            if side == 1:
                vs = vs[::-1]
                uv = uv[::-1]
            M.face(vs, "hand" + sfx, uv)
        hole = [idx[v] for v in loop]
        last = arm_rings[side][-1]
        M.wrists = getattr(M, "wrists", [])
        M.wrists.append(([list(r) for r in arm_rings[side][-3:]], list(hole)))
        match_wrist(M, M.wrists[-1])
        Pl = np.array([M.P[i] for i in last]).mean(0)
        Ph = np.array([M.P[i] for i in hole]).mean(0)
        zipper(M, last, hole, (Pl + Ph) / 2, Ph - Pl, "arm" + sfx)
        for name, pts in fjoints.items():
            joints[name + sfx] = [place(p) for p in pts]
    return k


# ------------------------------------------------------------------------------------------------------------------
# Clean-up: winding, folded faces, symmetry, smoothing
# ------------------------------------------------------------------------------------------------------------------

def drop_unused(M):
    used = set(v for f in M.F for v in f)
    remap = {}
    P, part, base, finger = [], [], {}, {}
    for i in range(len(M.P)):
        if i in used:
            remap[i] = len(P)
            P.append(M.P[i])
            part.append(M.part[i])
            if i in M.base:
                base[remap[i]] = M.base[i]
            if i in M.finger:
                finger[remap[i]] = M.finger[i]
    M.P, M.part, M.base, M.finger = P, part, base, finger
    M.F = [[remap[v] for v in f] for f in M.F]
    return remap


def fix_winding(M):
    """Every face's winding agreed with its neighbours and pointing out (bmesh's own recalculation)."""
    bm = bmesh.new()
    vs = [bm.verts.new(Vector(p)) for p in M.P]
    bm.verts.ensure_lookup_table()
    fmap = []
    for f in M.F:
        try:
            fmap.append(bm.faces.new([vs[v] for v in f]))
        except ValueError:
            fmap.append(None)
    bm.faces.ensure_lookup_table()
    bmesh.ops.recalc_face_normals(bm, faces=[f for f in fmap if f is not None])
    flipped = 0
    for fi, bf in enumerate(fmap):
        if bf is None:
            continue
        order = [v.index for v in bf.verts]
        if order != M.F[fi]:
            # bmesh reversed it
            M.F[fi] = order
            if M.fuv[fi] is not None:
                M.fuv[fi] = M.fuv[fi][::-1]
            flipped += 1
    nonman = sum(1 for e in bm.edges if not e.is_manifold)
    bm.free()
    return flipped, nonman


def folded_faces(M):
    """Faces whose normal turns against most of their edge neighbours (folds), and faces with no area."""
    P = M.arr()
    Nf = []
    for f in M.F:
        n = np.zeros(3)
        for k in range(1, len(f) - 1):
            n += np.cross(P[f[k]] - P[f[0]], P[f[k + 1]] - P[f[0]])
        Nf.append(n)
    Nf = np.array(Nf)
    area = np.linalg.norm(Nf, axis=1)
    Nn = Nf / np.maximum(area[:, None], 1e-15)
    edge = {}
    for fi, f in enumerate(M.F):
        for k in range(len(f)):
            a, b = f[k], f[(k + 1) % len(f)]
            edge.setdefault((min(a, b), max(a, b)), []).append(fi)
    bad = 0
    for fi in range(len(M.F)):
        nb = set()
        f = M.F[fi]
        for k in range(len(f)):
            a, b = f[k], f[(k + 1) % len(f)]
            nb.update(edge[(min(a, b), max(a, b))])
        nb.discard(fi)
        if nb and np.mean([np.dot(Nn[fi], Nn[j]) for j in nb]) < -0.2:
            bad += 1
    return bad, int((area < 1e-10).sum())


def mirror_map(M):
    P = M.arr()
    kd = kdtree.KDTree(len(P))
    for i, p in enumerate(P):
        kd.insert(Vector(p), i)
    kd.balance()
    mir = np.arange(len(P))
    for i, p in enumerate(P):
        _, j, d = kd.find(Vector((-p[0], p[1], p[2])))
        mir[i] = j if d < 0.003 else i
    return mir


def symmetrize(M, mir):
    P = M.arr()
    Q = (P + P[mir] * np.array([-1, 1, 1])) / 2
    for i in range(len(P)):
        if mir[i] == i and abs(P[i][0]) < 0.003:
            Q[i][0] = 0.0
        M.P[i] = Q[i]


def smooth(M, sel, rounds=2, lam=0.4, mu=-0.42, nb=None):
    nb = nb or M.neighbours()
    sel = np.asarray(sel, bool)
    P = M.arr()
    for _ in range(rounds):
        for f in (lam, mu):
            avg = np.array([P[n].mean(0) if n else P[i] for i, n in enumerate(nb)])
            P[sel] += f * (avg[sel] - P[sel])
    for i in np.where(sel)[0]:
        M.P[i] = P[i]


# ------------------------------------------------------------------------------------------------------------------
# Silhouettes: rendering the model's, fitting it to the sheet's, the difference pictures
# ------------------------------------------------------------------------------------------------------------------

def model_view(M, sh, view, tris=None, P=None):
    P = M.arr() if P is None else P
    tris = M.tris() if tris is None else tris
    Q = sh.to_px(view, P)
    zb, tid, _ = raster(Q[:, :2], Q[:, 2], tris, (sh.H, sh.W))
    return zb, tid, Q


FIT_PARTS = ("torso", "arm", "leg", "foot", "neck")


def fit_round(M, sh, B, nb, reach=26, damp=0.8):
    P = M.arr()
    N = M.normals()
    tris = M.tris()
    disp = np.zeros_like(P)
    cnt = np.zeros(len(P))
    fam = np.array([p.split("_")[0] for p in M.part])
    can = np.isin(fam, FIT_PARTS)
    hand_top = sh.z(B.Wp[1])
    for view in ("front", "side", "back"):
        zb, tid, Q = model_view(M, sh, view, tris, P)
        inside = np.isfinite(zb)
        edge = dilate(inside, 1) & ~erode(inside, 2)
        tgt = sh.target(view)
        vd = np.array(Sheet.VIEW_DIR[view], float)
        for i in np.where(can)[0]:
            if abs(np.dot(N[i], vd)) > 0.55:
                continue
            c, r = int(round(Q[i, 0])), int(round(Q[i, 1]))
            if not (0 < r < sh.H - 1 and 0 < c < sh.W - 1) or not edge[r, c]:
                continue
            if Q[i, 2] > zb[r, c] + 0.02:
                continue
            if view == "side" and fam[i] == "torso" and sh.z(B.tip_row) < P[i, 2] < sh.z(B.armpit_row) and \
                    abs(P[i, 0]) > 0.02:
                continue  # an arm hangs over the side view there
            if view == "side" and fam[i] == "leg" and sh.z(B.tip_row) - 0.02 < P[i, 2] < hand_top:
                continue  # the hand hangs over the thigh there
            # the outward way in the picture
            if view == "front":
                d2 = np.array([N[i, 0], -N[i, 2]])
            elif view == "back":
                d2 = np.array([-N[i, 0], -N[i, 2]])
            else:
                d2 = np.array([-N[i, 1], -N[i, 2]])
            nn = np.linalg.norm(d2)
            if nn < 1e-6:
                continue
            d2 /= nn
            if tgt[r, c]:
                s = 0
                while s < reach and tgt[int(round(r + d2[1] * (s + 1))), int(round(c + d2[0] * (s + 1)))]:
                    s += 1
                dist = s
            else:
                s = 0
                while s < reach and not tgt[int(round(r - d2[1] * (s + 1))), int(round(c - d2[0] * (s + 1)))]:
                    s += 1
                dist = -s - 1 if s < reach else 0
            w3 = sh.world_dir(view, d2[0], d2[1])
            disp[i] += w3 * dist * sh.S
            cnt[i] += 1
    has = cnt > 0
    disp[has] /= cnt[has][:, None]
    # spread to the points round them (harmonic fill), then apply
    D = disp.copy()
    known = has.copy()
    for _ in range(6):
        avg = np.array([D[n].mean(0) if n else D[i] for i, n in enumerate(nb)])
        D[~known & can] = avg[~known & can] * 0.85
        D[known] = 0.8 * D[known] + 0.2 * avg[known]
    D[~can] = 0
    for i in range(len(P)):
        M.P[i] = P[i] + damp * D[i]
    return int(has.sum()), float(np.abs(disp[has]).max() if has.any() else 0)


def gap_stats(model, target, rows, S):
    """Where the masks disagree, the thickness of each disagreement (the shorter of its runs across and down): the
    worst and the 98th percentile, in centimetres."""
    diff = (model ^ target)
    diff[:int(rows[0])] = False
    diff[int(rows[1]):] = False
    if not diff.any():
        return 0.0, 0.0
    def runlen(d):
        out = np.zeros(d.shape, np.int32)
        for i, row in enumerate(d):
            for a, b in runs_of(row, 1):
                out[i, a:b] = b - a
        return out
    h = runlen(diff)
    v = runlen(diff.T).T
    t = np.minimum(h, v)[diff]
    return float(t.max() * S * 100), float(np.percentile(t, 98) * S * 100)


def silhouette_diffs(M, sh, tag=""):
    tris = M.tris()
    out = {}
    pics = {}
    for view in ("front", "side", "back"):
        zb, _, _ = model_view(M, sh, view, tris)
        mm = np.isfinite(zb)
        tg = sh.target(view).copy()
        a, b = sh.span[view]
        mm[:, :a] = False
        mm[:, b:] = False
        body = gap_stats(mm, tg, (sh.chin + 4, sh.sole + 1), sh.S)
        head = gap_stats(mm, tg, (sh.top, sh.chin + 4), sh.S)
        out[view] = (body, head)
        img = np.zeros(mm.shape + (3,), np.float32)
        img[mm & tg] = (0.85, 0.85, 0.85)
        img[mm & ~tg] = (1.0, 0.15, 0.1)
        img[~mm & tg] = (0.1, 0.85, 1.0)
        pics[view] = img[:, a:b]
    print("  silhouette gaps %s (cm, body below the chin: worst / 98%%; head: worst / 98%%, the hair counts there)" % tag)
    for v, ((bw, bp), (hw, hp)) in out.items():
        print("    %-5s body %.1f / %.1f   head %.1f / %.1f" % (v, bw, bp, hw, hp))
    return out, pics


# ------------------------------------------------------------------------------------------------------------------
# The underwear: where the sheet's paint is cloth
# ------------------------------------------------------------------------------------------------------------------

def find_cloth(M, sh, top_z=None):
    P = M.arr()
    tris_all = M.tris()
    fam = [M.part[f[0]].split("_")[0] for f in M.F]
    Nf, Cf = [], []
    for f in M.F:
        n = np.cross(P[f[1]] - P[f[0]], P[f[-1]] - P[f[0]])
        Nf.append(n / max(np.linalg.norm(n), 1e-12))
        Cf.append(P[f].mean(0))
    Nf, Cf = np.array(Nf), np.array(Cf)
    votes = np.zeros(len(M.F))
    for view in ("front", "side", "back", "side_l"):
        zb, _, _ = model_view(M, sh, view, tris_all, P)
        Q = sh.to_px(view, Cf)
        vd = np.array(Sheet.VIEW_DIR[view], float)
        for fi in range(len(M.F)):
            if fam[fi] not in ("torso", "leg", "neck", "arm"):
                continue
            face = np.dot(Nf[fi], vd)
            if face < 0.3:
                continue
            c, r = int(round(Q[fi, 0])), int(round(Q[fi, 1]))
            if not (2 < r < sh.H - 2 and 2 < c < sh.W - 2) or Q[fi, 2] > zb[r, c] + 0.02:
                continue
            frac = sh.cloth[r - 2:r + 3, c - 2:c + 3].mean()
            votes[fi] += face * (frac - 0.3)
    is_c = votes > 0
    print("  cloth votes: %d faces positive before cleaning, of %d torso/leg faces" % (int(is_c.sum()), sum(1 for f_ in fam if f_ in ("torso", "leg"))))
    # clean: majority of edge neighbours, twice
    edge = {}
    for fi, f in enumerate(M.F):
        for k in range(len(f)):
            a, b = f[k], f[(k + 1) % len(f)]
            edge.setdefault((min(a, b), max(a, b)), []).append(fi)
    nbf = [set() for _ in M.F]
    for fs in edge.values():
        for a in fs:
            nbf[a].update(fs)
    for _ in range(2):
        new = is_c.copy()
        for fi in range(len(M.F)):
            if fam[fi] not in ("torso", "leg", "neck", "arm"):
                continue
            nb = [j for j in nbf[fi] if j != fi]
            s = sum(is_c[j] for j in nb)
            if s >= len(nb) * 0.5:
                new[fi] = True
            elif s <= len(nb) * 0.25:
                new[fi] = False
        is_c = new
    for fi in range(len(M.F)):
        if fam[fi] not in ("torso", "leg"):
            is_c[fi] = False
        elif top_z is not None and max(P[v][2] for v in M.F[fi]) > top_z:
            is_c[fi] = False   # no straps: the underwear's top ends at the armpits (straps on 24 columns came out as blocks)
    return is_c


def make_underwear(M, is_c, B):
    """The underwear: a copy of the cloth faces at the outline; the skin under it moved in by EASE (more under loose
    legs, by thigh_k)."""
    sh = B.sh
    P = M.arr()
    N = M.normals()
    cv = sorted(set(v for fi in np.where(is_c)[0] for v in M.F[fi]))
    sv = set(v for fi in np.where(~is_c)[0] for v in M.F[fi])
    U = Mesh()
    remap = {}
    for v in cv:
        remap[v] = U.add(P[v], M.part[v])
    for fi in np.where(is_c)[0]:
        U.face([remap[v] for v in M.F[fi]], M.fpart[fi])
    U.src = {u: v for v, u in remap.items()}
    # the skin under it
    for v in cv:
        f = 0.5 if v in sv else 1.0
        M.P[v] = P[v] - N[v] * EASE * f
    # loose legs: each leg ring under the cloth narrowed toward the leg below the hem
    thigh_k = sh.cfg.get("thigh_k", 1.0)
    if thigh_k < 1.0:
        for side, rings in M.leg_rings.items():
            covered = [ri for ri, ring in enumerate(rings[1:], 1) if sum(v in cv for v in ring) > len(ring) // 2]
            if not covered:
                continue
            below = max(covered) + 1
            ref = np.array([M.P[v] for v in rings[below]])
            rc = ref.mean(0)
            r_ref = np.linalg.norm((ref - rc)[:, :2], axis=1).mean()
            top = np.array([M.P[v] for v in rings[1]])
            r_top = np.linalg.norm((top - top.mean(0))[:, :2], axis=1).mean() * thigh_k
            for ri in covered:
                ring = rings[ri]
                Q = np.array([M.P[v] for v in ring])
                c = Q.mean(0)
                r = np.linalg.norm((Q - c)[:, :2], axis=1).mean()
                t = (ri - 1) / max(below - 1, 1)
                want = lerp(r_top, r_ref, t)
                if want < r:
                    s = want / r
                    # (the ring's middle moved toward the line from the hip to the leg below)
                    for v in ring:
                        p = M.P[v]
                        p[0] = c[0] + (p[0] - c[0]) * s
                        p[1] = c[1] + (p[1] - c[1]) * s
    return U


# ------------------------------------------------------------------------------------------------------------------
# The skeleton and the weights (the captain's and the brother's bone names and parents)
# ------------------------------------------------------------------------------------------------------------------

def skeleton(M, B, joints, T, hd):
    sh = B.sh
    k = B.k
    def centre(z):
        rings = [(M.P[r[0]][2], np.array([M.P[i] for i in r])) for r in T]
        zs = [a for a, _ in rings]
        i = int(np.clip(np.searchsorted(zs, z), 1, len(zs) - 1))
        za, pa = rings[i - 1]
        zb_, pb = rings[i]
        t = (z - za) / max(zb_ - za, 1e-6)
        ring = pa * (1 - t) + pb * t
        yf, yb = ring[:, 1].min(), ring[:, 1].max()
        return np.array([0.0, yb - 0.42 * (yb - yf), z])
    hip_z = joints["hip_l"][2]
    chest_z = sh.z(B.armpit_row) - 0.02 * k
    neck_z = M.P[T[-3][0]][2]
    bones = [("hips", centre(hip_z + 0.03 * k), None),
             ("spine", centre(lerp(hip_z, chest_z, 0.45)), "hips"),
             ("chest", centre(chest_z), "spine"),
             ("neck", centre(neck_z), "chest")]
    head_at = centre(neck_z)
    head_at[2] = lerp(hd["chin"], hd["eye"], 0.5)
    head_at[1] += 0.01 * k
    bones.append(("head", head_at, "neck"))
    for s, sfx in ((1, "_l"), (-1, "_r")):
        J, E, W = joints["shoulder" + sfx], joints["elbow" + sfx], joints["wrist" + sfx]
        bones.append(("clavicle" + sfx, np.array([s * 0.04 * k, J[1] - 0.01, J[2] + 0.06 * k]), "chest"))
        bones.append(("upper_arm" + sfx, J, "chest"))
        bones.append(("forearm" + sfx, E, "upper_arm" + sfx))
        bones.append(("hand" + sfx, W, "forearm" + sfx))
        for f in FINGERS:
            pts = joints[f + sfx]
            for n in range(3):
                bones.append(("finger_%s_%d%s" % (f, n + 1, sfx), pts[n],
                              "hand" + sfx if n == 0 else "finger_%s_%d%s" % (f, n, sfx)))
        pts = joints["thumb" + sfx]
        for n in range(3):
            bones.append(("thumb_%d%s" % (n + 1, sfx), pts[n], "hand" + sfx if n == 0 else "thumb_%d%s" % (n, sfx)))
        bones.append(("thigh" + sfx, joints["hip" + sfx], "hips"))
        bones.append(("shin" + sfx, joints["knee" + sfx], "hips"))
        bones.append(("foot" + sfx, joints["ankle" + sfx], "hips"))
        bones.append(("toe" + sfx, joints["ball" + sfx], "foot" + sfx))
    return bones


def chain(s, names, ends, blend):
    w = {names[0]: 1.0}
    for name, at in zip(names[1:], ends):
        t = float(smoothstep(at - blend, at + blend, s))
        w = {n: v * (1 - t) for n, v in w.items()}
        w[name] = w.get(name, 0.0) + t
    return w


def along(p, a, b):
    d = b - a
    return float(np.dot(p - a, d) / max(np.linalg.norm(d), 1e-12))


def mix_in(w, name, kk):
    if kk <= 0:
        return w
    w = {n: v * (1 - kk) for n, v in w.items()}
    w[name] = w.get(name, 0.0) + kk
    return w


def weights(M, bones, joints, hd, k):
    at = {n: np.array(p) for n, p, _ in bones}
    P = M.arr()
    out = []
    zt = (lerp(at["hips"][2], at["spine"][2], 0.6), lerp(at["spine"][2], at["chest"][2], 0.5),
          lerp(at["chest"][2], at["neck"][2], 0.75))
    for vi, part in enumerate(M.part):
        p = P[vi]
        fam = part.split("_")[0]
        sfx = "_l" if part.endswith("_l") else ("_r" if part.endswith("_r") else ("_l" if p[0] >= 0 else "_r"))
        if fam == "head":
            t = float(smoothstep(hd["chin"] - 0.03 * k, hd["chin"] + 0.005, p[2]))
            w = {"head": t, "neck": 1 - t} if t < 1 else {"head": 1.0}
        elif fam == "neck":
            t = float(smoothstep(at["neck"][2] - 0.01, hd["chin"] - 0.01 * k, p[2]))
            w = {"neck": 1 - t, "head": t}
            w = mix_in(w, "chest", 0.5 * (1 - float(smoothstep(at["neck"][2] - 0.04 * k, at["neck"][2] + 0.02 * k, p[2]))))
        elif fam == "torso":
            w = chain(p[2], ["hips", "spine", "chest", "neck"], zt, 0.06 * k)
            for s, sx in ((1, "_l"), (-1, "_r")):
                d = np.linalg.norm(p - at["upper_arm" + sx])
                w = mix_in(w, "upper_arm" + sx, 0.5 * (1 - float(smoothstep(0.06 * k, 0.17 * k, d))) * (s * p[0] > 0))
                if p[2] < at["hips"][2] + 0.03 * k and s * p[0] > 0.0:
                    kk = 0.55 * (1 - float(smoothstep(at["thigh" + sx][2] - 0.07 * k, at["hips"][2] + 0.05 * k, p[2])))
                    kk *= float(smoothstep(-0.01, 0.06 * k, s * p[0]))
                    w = mix_in(w, "thigh" + sx, kk)
            if vi == M.crotch:
                w = {"hips": 0.6, "thigh_l": 0.2, "thigh_r": 0.2}
        elif fam == "arm":
            J, E, W = at["upper_arm" + sfx], at["forearm" + sfx], at["hand" + sfx]
            Lu = np.linalg.norm(E - J)
            s = along(p, J, E)
            if s > Lu - 0.05 * k:
                s = max(s, Lu + along(p, E, W))
            w = chain(s, ["upper_arm" + sfx, "forearm" + sfx, "hand" + sfx], [Lu, Lu + np.linalg.norm(W - E)], 0.045 * k)
            w = mix_in(w, "chest", 0.45 * (1 - float(smoothstep(-0.02 * k, 0.07 * k, s))))
        elif fam == "hand":
            sub = M.finger.get(vi)
            if sub:
                names = ["thumb_%d%s" % (n, sfx) for n in (1, 2, 3)] if sub == "thumb" else \
                    ["finger_%s_%d%s" % (sub, n, sfx) for n in (1, 2, 3)]
                a1, a2, a3 = at[names[0]], at[names[1]], at[names[2]]
                l1 = np.linalg.norm(a2 - a1)
                l2 = l1 + np.linalg.norm(a3 - a2)
                s = along(p, a1, a2)
                if s > l1 - 0.003:
                    s = l1 + max(0.0, along(p, a2, a3))
                    if s > l2 - 0.003:
                        s = l2 + max(0.0, along(p, a3, a3 + (a3 - a2)))
                w = chain(s, ["hand" + sfx] + names, [0.0, l1, l2], 0.007 * k)
            else:
                Wr = at["hand" + sfx]
                s = along(p, at["forearm" + sfx], Wr) - np.linalg.norm(Wr - at["forearm" + sfx])
                w = chain(s, ["forearm" + sfx, "hand" + sfx], [0.0], 0.02 * k)
        elif fam == "leg":
            Hh, K, A = at["thigh" + sfx], at["shin" + sfx], at["foot" + sfx]
            w = chain(-p[2], ["thigh" + sfx, "shin" + sfx, "foot" + sfx], [-K[2], -A[2] - 0.01 * k], 0.045 * k)
            w = mix_in(w, "hips", 0.35 * float(smoothstep(Hh[2] - 0.08 * k, Hh[2] + 0.02 * k, p[2])))
        elif fam == "foot":
            A = at["foot" + sfx]
            fwd = joints["foot_fwd" + sfx]
            u = float(np.dot(p - A, fwd))
            w = chain(u, ["foot" + sfx, "toe" + sfx], [np.dot(at["toe" + sfx] - A, fwd)], 0.025 * k)
            w = mix_in(w, "shin" + sfx, 0.45 * float(smoothstep(A[2] - 0.02 * k, A[2] + 0.03 * k, p[2])))
        else:
            w = {"hips": 1.0}
        w = {n: v for n, v in w.items() if v > 0.01}
        tot = sum(w.values())
        out.append({n: v / tot for n, v in sorted(w.items(), key=lambda kv: -kv[1])[:4]})
    return out


# ------------------------------------------------------------------------------------------------------------------
# UVs: planned islands, packed into the three pictures
# ------------------------------------------------------------------------------------------------------------------

def planar(P, ax_u, ax_v):
    return np.stack([P @ ax_u, P @ ax_v], 1)


def unroll(M, face_ids, centre_fn, seam_angle_fn, axis_fn):
    """UVs per face corner for a tube: u = angle round the tube's axis (from the seam) times the local radius,
    v = distance along the axis. centre_fn(p) -> (centre, axis) for a point."""
    P = M.arr()
    uv = {}
    for fi in face_ids:
        f = M.F[fi]
        corners = []
        for v in f:
            c, ax, e1 = centre_fn(P[v])
            rel = P[v] - c
            e2 = np.cross(ax, e1)
            a = math.atan2(np.dot(rel, e2), np.dot(rel, e1))   # 0 opposite the seam, +-pi at the seam
            r = np.linalg.norm(rel - ax * np.dot(rel, ax))
            corners.append([a, r, axis_fn(P[v])])
        A = np.array(corners)
        # faces across the seam: unwrap their angles
        if A[:, 0].max() - A[:, 0].min() > math.pi:
            A[A[:, 0] < 0, 0] += math.tau
        rm = A[:, 1].mean()
        uv[fi] = [(a * rm, s) for a, r_, s in A]
    return uv


def plan_uvs(M, B, T, joints):
    """Islands of face corner UVs (in metres, before packing): name -> {face: [(u, v)...]}"""
    P = M.arr()
    isl = {}
    for fi, name in enumerate(M.fpart):
        isl.setdefault(name, []).append(fi)
    out = {}
    tor_rings = [(M.P[r[0]][2], np.array([M.P[i] for i in r]).mean(0)) for r in T]
    zs = np.array([z for z, _ in tor_rings])
    cs = np.array([c for _, c in tor_rings])
    def torso_centre(p):
        c = np.array([0.0, np.interp(p[2], zs, cs[:, 1]), p[2]])
        return c
    for name in ("torso_front", "torso_back"):
        e1 = np.array([0.0, -1.0, 0.0]) if name == "torso_front" else np.array([0.0, 1.0, 0.0])
        out[name] = unroll(M, isl[name], lambda p, e1=e1: (torso_centre(p), np.array([0.0, 0.0, 1.0]), e1), None,
                           lambda p: p[2])
    # the neck (and its join to the head): seam at the back
    out["neck"] = unroll(M, isl["neck"], lambda p: (torso_centre(p) if p[2] < zs[-1] else
                                                    np.array([0.0, cs[-1][1], p[2]]), np.array([0.0, 0.0, 1.0]),
                                                    np.array([0.0, -1.0, 0.0])), None, lambda p: p[2])
    for side, sfx in ((1, "_l"), (-1, "_r")):
        J, E, W = M.arm_axis[side]
        def arm_c(p, J=J, E=E, W=W):
            L1 = np.linalg.norm(E - J)
            s = along(p, J, E)
            if s <= L1:
                ax = (E - J) / L1
                c = J + ax * s
            else:
                ax = (W - E) / np.linalg.norm(W - E)
                c = E + ax * along(p, E, W)
            up = np.array([0.0, 0.0, 1.0])
            e1 = up - ax * np.dot(up, ax)   # the top of the arm faces away from the seam underneath
            return c, ax, e1 / np.linalg.norm(e1)
        def arm_s(p, J=J, E=E, W=W):
            L1 = np.linalg.norm(E - J)
            s = along(p, J, E)
            return -(s if s <= L1 else L1 + along(p, E, W))
        out["arm" + sfx] = unroll(M, isl["arm" + sfx], arm_c, None, arm_s)
        hip = joints["hip" + sfx]
        ank = joints["ankle" + sfx]
        def leg_c(p, hip=hip, ank=ank, side=side):
            t = np.clip((hip[2] - p[2]) / (hip[2] - ank[2]), 0, 1)
            c = hip + (ank - hip) * t
            c[2] = p[2]
            return c, np.array([0.0, 0.0, 1.0]), np.array([float(side), 0.0, 0.0])
        out["leg" + sfx] = unroll(M, isl["leg" + sfx], leg_c, None, lambda p: p[2])
        out["sole" + sfx] = {fi: [tuple(planar(P[v][None], np.array([side * 1.0, 0, 0]), np.array([0, -1.0, 0]))[0])
                                  for v in M.F[fi]] for fi in isl["sole" + sfx]}
        # hands: back and palm, flat from the palm's way
        fwd = joints["arm_t" + sfx]
        n_in = M.palm[side] * np.array([side, 1, 1])
        thumb = np.cross(fwd, n_in)
        Pc = P
        back, palm = {}, {}
        for fi in isl["hand" + sfx]:
            f = M.F[fi]
            n = np.cross(Pc[f[1]] - Pc[f[0]], Pc[f[-1]] - Pc[f[0]])
            uvs = [(float(np.dot(Pc[v], thumb)) * (1 if side == 1 else -1), float(-np.dot(Pc[v], fwd))) for v in f]
            if np.dot(n, n_in) > 0:
                palm[fi] = [(-u, v) for u, v in uvs]
            else:
                back[fi] = uvs
        out["hand" + sfx + "_back"] = back
        out["hand" + sfx + "_palm"] = palm
    return out


def pack(islands, density, pad):
    """Shelf packing of islands (name -> {face: [(u, v)]} in metres, scaled by density name -> factor) into the unit
    square. Returns face -> [(u, v)] in 0..1 and the scale used."""
    boxes = []
    if not any(islands.values()):
        return {}, 1.0
    for name, fu in islands.items():
        if not fu:
            continue
        pts = np.array([q for c in fu.values() for q in c])
        lo, hi = pts.min(0), pts.max(0)
        boxes.append((name, lo, hi - lo, density.get(name, 1.0)))
    def attempt(scale):
        x = y = rowh = 0.0
        place = {}
        for name, lo, size, d in sorted(boxes, key=lambda b: -b[2][1] * b[3]):
            w, h = size * scale * d
            if x + w + pad > 1.0:
                x, y, rowh = 0.0, y + rowh + pad, 0.0
            if w + 2 * pad > 1.0:
                return None
            place[name] = (x + pad, y + pad)
            x += w + pad
            rowh = max(rowh, h)
        if y + rowh + 2 * pad > 1.0:
            return None
        return place
    lo_s, hi_s = 0.01, 50.0
    best = None
    for _ in range(40):
        mid = (lo_s + hi_s) / 2
        p = attempt(mid)
        if p:
            best = (mid, p)
            lo_s = mid
        else:
            hi_s = mid
    scale, place = best
    out = {}
    for name, lo, size, d in boxes:
        ox, oy = place[name]
        for fi, c in islands[name].items():
            out[fi] = [(ox + (u - lo[0]) * scale * d, oy + (v - lo[1]) * scale * d) for u, v in c]
    return out, scale


def layout_picture(face_uv, faces, px, path, labels=None):
    img = np.ones((px, px, 3), np.float32) * 0.12
    for fi, uv in face_uv.items():
        pts = [(u * px, (1 - v) * px) for u, v in uv]
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            n = int(max(abs(a[0] - b[0]), abs(a[1] - b[1]))) + 1
            for t in np.linspace(0, 1, n + 1):
                c = int(a[0] + (b[0] - a[0]) * t)
                r = int(a[1] + (b[1] - a[1]) * t)
                if 0 <= r < px and 0 <= c < px:
                    img[r, c] = (0.9, 0.85, 0.4)
    save_png(path, img)


# ------------------------------------------------------------------------------------------------------------------
# Painting: the sheet projected into the pictures by facing
# ------------------------------------------------------------------------------------------------------------------

def skin_stats(sh, B):
    """The sheet's skin colour: the chest's middle in the front view (a patch above the navel)."""
    r = int(sh.row(lerp(B.crotch_z, sh.z(B.armpit_row), 0.75)))
    c = int(sh.mid["front"])
    patch = sh.pix[r - 12:r + 12, c - 30:c + 30].reshape(-1, 3)
    if sh.cloth[r, c]:
        # covered: the upper arm instead
        q = B.armpit_row + 40
        cc = int(B.centres.get(q, c))
        patch = sh.pix[q - 8:q + 8, cc - 6:cc + 6].reshape(-1, 3)
    return np.median(patch, 0)


def is_skin(c, ref):
    """Skin-coloured pixels (not hair, ink, cloth or background), against the sheet's own skin colour."""
    c = np.asarray(c, float)
    r = np.maximum(c[..., 0], 1e-3)
    g_r, b_r = c[..., 1] / r, c[..., 2] / r
    rg, rb = ref[1] / ref[0], ref[2] / ref[0]
    lum = c.mean(-1)
    lr = ref.mean()
    return (np.abs(g_r - rg) < 0.075) & (np.abs(b_r - rb) < 0.09) & (lum > 0.42 * lr) & (lum < 1.25 * lr)


def texel_points(M, face_uv, faces, px, P, N):
    """For every texel of a picture: the model point and normal under it (or none)."""
    tris, tuv = [], []
    for fi in faces:
        if fi not in face_uv:
            continue
        f = M.F[fi]
        uv = face_uv[fi]
        for k in range(1, len(f) - 1):
            tris.append((f[0], f[k], f[k + 1]))
            tuv.append((uv[0], uv[k], uv[k + 1]))
    tris = np.array(tris)
    tuv = np.array(tuv) * px
    # rasterise in UV space (a point per corner)
    U = tuv.reshape(-1, 2).copy()
    U[:, 1] = px - U[:, 1]
    T3 = np.arange(len(U)).reshape(-1, 3)
    zb, tid, bary = raster(U - 0.5, np.zeros(len(U)), T3, (px, px), want_bary=True)
    ok = tid >= 0
    t = tid[ok]
    b = bary[ok]
    Pt = (P[tris[t, 0]] * b[:, 0:1] + P[tris[t, 1]] * b[:, 1:2] + P[tris[t, 2]] * b[:, 2:3])
    Nt = (N[tris[t, 0]] * b[:, 0:1] + N[tris[t, 1]] * b[:, 1:2] + N[tris[t, 2]] * b[:, 2:3])
    Nt /= np.maximum(np.linalg.norm(Nt, axis=1, keepdims=True), 1e-9)
    return ok, Pt, Nt, tris[t], b


def paint(sh, ok, Pt, Nt, zbufs, kind, ref, scalp=None, head=False):
    """kind: 'skin' takes skin-coloured pixels only, 'cloth' cloth only. Returns the picture and where it was set."""
    px = ok.shape[0]
    acc = np.zeros((len(Pt), 3))
    wsum = np.zeros(len(Pt))
    for view in ("front", "back", "side", "side_l"):
        zb = zbufs[view]
        vd = np.array(Sheet.VIEW_DIR[view], float)
        facing = Nt @ vd
        Q = sh.to_px(view, Pt)
        c = np.clip(np.round(Q[:, 0]).astype(int), 0, sh.W - 1)
        r = np.clip(np.round(Q[:, 1]).astype(int), 0, sh.H - 1)
        vis = Q[:, 2] <= zb[r, c] + 0.012
        col = sh.pix[r, c]
        least = 0.3 if view in ("front", "back") else (0.72 if head else 0.5)
        good = vis & (facing > least) & sh.inner[r, c] & ~sh.lines[r, c]
        if view in ("side", "side_l") and "side_reject" in sh.cfg:
            cc, rr, rad = sh.cfg["side_reject"]
            good &= (c - cc) ** 2 + (r - rr) ** 2 > rad ** 2
        if kind == "skin":
            good &= is_skin(col, ref) & ~sh.near_cloth[r, c]
        else:
            good &= sh.cloth[r, c]
        w = np.where(good, (facing - least * 0.8) ** 2 * (2.0 if (head and view == "front") else 1.0), 0.0)
        acc += col * w[:, None]
        wsum += w
    valid = wsum > 1e-6
    if scalp is not None:
        valid &= ~scalp
    col = np.zeros((len(Pt), 3))
    col[valid] = acc[valid] / wsum[valid][:, None]
    img = np.zeros((px, px, 3), np.float32)
    val = np.zeros((px, px), bool)
    img[ok] = col
    val[ok] = valid
    return img, val


def fill_out(img, valid, ok, base_colour, rounds=48):
    """Fill what has no paint: a few rounds from the painted edge, then the base colour, then softened."""
    img = img.copy()
    v = valid.copy()
    for _ in range(rounds):
        acc = np.zeros_like(img)
        n = np.zeros(v.shape)
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            acc += np.roll(np.roll(img * v[:, :, None], dr, 0), dc, 1)
            n += np.roll(np.roll(v, dr, 0), dc, 1)
        new = ~v & (n > 0)
        img[new] = acc[new] / n[new][:, None]
        v = v | new
    rest = ~v
    img[rest] = base_colour
    # soften the filled part toward its surroundings
    filled = ~valid
    for _ in range(6):
        b = img.copy()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            b += np.roll(np.roll(img, dr, 0), dc, 1)
        b /= 5
        img[filled] = b[filled]
    # bleed past the islands' edges so mip levels and seams do not show the dark ground
    v2 = ok.copy()
    for _ in range(4):
        acc = np.zeros_like(img)
        n = np.zeros(v2.shape)
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            acc += np.roll(np.roll(img * v2[:, :, None], dr, 0), dc, 1)
            n += np.roll(np.roll(v2, dr, 0), dc, 1)
        new = ~v2 & (n > 0)
        img[new] = acc[new] / n[new][:, None]
        v2 = v2 | new
    img[~v2] = base_colour
    return img


def scalp_mask(M, tris, bary, sex):
    """Head texels under the hair on the sheet (from their place on the base head): forehead above the hairline,
    above the ears, the back of the skull down to the nape."""
    B0 = np.array([M.base.get(v, (0, 0, -1)) for v in range(len(M.P))])
    has = np.array([v in M.base for v in range(len(M.P))])
    p = B0[tris[:, 0]] * bary[:, 0:1] + B0[tris[:, 1]] * bary[:, 1:2] + B0[tris[:, 2]] * bary[:, 2:3]
    inhead = has[tris[:, 0]] & has[tris[:, 1]] & has[tris[:, 2]]
    ang = np.arctan2(np.abs(p[:, 0]), -(p[:, 1] - 0.03))   # 0 at the front, pi at the back
    front_line = 0.098 if sex == "m" else 0.092
    side_line = 0.05
    back_line = -0.035 if sex == "m" else -0.06
    line = np.interp(ang, [0.0, 0.7, 1.35, 2.1, math.pi], [front_line, front_line - 0.01, side_line, back_line + 0.02,
                                                           back_line])
    return inhead & (p[:, 2] > line)


# ------------------------------------------------------------------------------------------------------------------
# Blender objects, export
# ------------------------------------------------------------------------------------------------------------------

def image_material(name, path, double=False):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(path)
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.8
    mat.use_backface_culling = not double
    return mat


def mesh_object(name, P, faces, face_uv, face_mat, mats, arm, wts):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(p) for p in P], [], faces)
    me.update()
    uvl = me.uv_layers.new(name="UVMap")
    for poly, uv in zip(me.polygons, face_uv):
        for li, q in zip(poly.loop_indices, uv):
            uvl.data[li].uv = q
    for m in mats:
        me.materials.append(m)
    for poly, mi in zip(me.polygons, face_mat):
        poly.material_index = mi
        poly.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if arm is not None:
        groups = {}
        for b in arm.data.bones:
            groups[b.name] = ob.vertex_groups.new(name=b.name)
        for vi, w in enumerate(wts):
            for bn, x in w.items():
                groups[bn].add([vi], x, "REPLACE")
        ob.parent = arm
        mod = ob.modifiers.new("arm", "ARMATURE")
        mod.object = arm
    return ob


def make_armature(name, bones):
    data = bpy.data.armatures.new(name)
    ob = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    for bname, at, parent in bones:
        b = data.edit_bones.new(bname)
        b.head = Vector(at)
        b.tail = Vector(at) + Vector((0.0, 0.0, 0.06))
        b.roll = 0.0
        if parent:
            b.parent = data.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    return ob


# ------------------------------------------------------------------------------------------------------------------
# Pictures for checking
# ------------------------------------------------------------------------------------------------------------------

def setup_render(textured):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    shd = sc.display.shading
    shd.light = "FLAT" if textured else "STUDIO"
    shd.color_type = "TEXTURE" if textured else "SINGLE"
    shd.single_color = (0.72, 0.72, 0.74)
    shd.show_cavity = not textured
    shd.cavity_type = "WORLD"
    shd.show_backface_culling = False
    sc.display.render_aa = "8"
    sc.view_settings.view_transform = "Standard"
    if sc.world is None:
        sc.world = bpy.data.worlds.new("w")
    sc.world.color = (0.86, 0.87, 0.9)
    cam = sc.camera
    if cam is None:
        cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
        sc.collection.objects.link(cam)
        sc.camera = cam
    cam.data.type = "ORTHO"
    return cam


def shoot(path, angle, focus, size, w, h, textured, up=0.0):
    cam = setup_render(textured)
    sc = bpy.context.scene
    cam.data.ortho_scale = size
    d = Vector((math.sin(angle) * math.cos(up), -math.cos(angle) * math.cos(up), math.sin(up)))
    cam.location = Vector(focus) + d * 20
    cam.data.clip_end = 60
    cam.rotation_euler = (Vector(focus) - cam.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return load_picture(path)


def pose_check(arm, H, path_dir, name):
    """A test pose: the left arm down and forward with the elbow bent, the right thigh raised with the knee bent."""
    pb = arm.pose.bones
    def rot(bone, axis, deg, pivot_bone=None):
        b = arm.data.bones[bone]
        piv = arm.data.bones[pivot_bone or bone].head_local
        R = Matrix.Translation(piv) @ Matrix.Rotation(math.radians(deg), 4, axis) @ Matrix.Translation(-piv)
        return R
    # the left arm: swing it down to the side and forward
    Ru = rot("upper_arm_l", "Y", 32) @ rot("upper_arm_l", "X", 35)
    pb["upper_arm_l"].matrix = Ru @ arm.data.bones["upper_arm_l"].matrix_local
    bpy.context.view_layer.update()
    El = Ru @ arm.data.bones["forearm_l"].head_local
    Rf = Matrix.Translation(El) @ Matrix.Rotation(math.radians(70), 4, "X") @ Matrix.Translation(-El) @ Ru
    pb["forearm_l"].matrix = Rf @ arm.data.bones["forearm_l"].matrix_local
    bpy.context.view_layer.update()
    # the right leg: hip bent 50, knee bent 70 (the shin and foot hang from the hips, so each is moved with the thigh)
    Rt = rot("thigh_r", "X", -50)
    pb["thigh_r"].matrix = Rt @ arm.data.bones["thigh_r"].matrix_local
    Kn = Rt @ arm.data.bones["shin_r"].head_local
    Rs = Matrix.Translation(Kn) @ Matrix.Rotation(math.radians(75), 4, "X") @ Matrix.Translation(-Kn) @ Rt
    pb["shin_r"].matrix = Rs @ arm.data.bones["shin_r"].matrix_local
    pb["foot_r"].matrix = Rs @ arm.data.bones["foot_r"].matrix_local
    bpy.context.view_layer.update()
    pics = []
    for a in (0.0, math.pi / 2, 0.8):
        pics.append(shoot(os.path.join(path_dir, "%s_pose_%d.png" % (name, int(a * 100))), a, (0, 0, H * 0.5),
                          H * 1.12, 420, 640, False))
    for b in pb:
        b.matrix_basis = Matrix()
    bpy.context.view_layer.update()
    return np.concatenate(pics, 1)


def label_bar(w, h=24, colour=(0.2, 0.2, 0.22)):
    return np.ones((h, w, 3), np.float32) * np.array(colour, np.float32)


def compare_picture(name, sh, diff_pics, H, out_dir):
    """sheet front/side/back | painted front/side/back | silhouette differences | grey front/side/back/three-quarter
    (+ a row of the pose check)."""
    ph = 760
    crops = []
    r0, r1 = int(max(0, sh.crown - 80)), int(min(sh.H, sh.sole + 40))
    for v in ("front", "side", "back"):
        a, b = sh.span[v]
        crops.append(resize(sh.pix[r0:r1, a:b], h=ph))
    focus = (0, 0, H * 0.5)
    span = (r1 - r0) * sh.S
    zc = (sh.z(r0) + sh.z(r1)) / 2
    painted, grey = [], []
    for v, a in (("front", 0.0), ("side", -math.pi / 2), ("back", math.pi)):
        a0, b0 = sh.span[v]
        wpx = int(ph * (b0 - a0) / (r1 - r0))
        # the camera's middle on the view's middle column
        cx = (a0 + b0) / 2
        off = (cx - sh.mid[v]) * sh.S
        if v == "front":
            f = (off, 0, zc)
        elif v == "back":
            f = (-off, 0, zc)
        else:
            f = (0, -off, zc)
        painted.append(shoot(os.path.join(out_dir, "%s_paint_%s.png" % (name, v)), a, f, max(span, (b0 - a0) * sh.S),
                             wpx, ph, True))
        grey.append(shoot(os.path.join(out_dir, "%s_grey_%s.png" % (name, v)), a, f, max(span, (b0 - a0) * sh.S),
                          wpx, ph, False))
    grey.append(shoot(os.path.join(out_dir, "%s_grey_q.png" % name), 0.7, (0, 0, zc), span, int(ph * 0.55), ph,
                      False))
    diffs = [resize(diff_pics[v][r0:r1], h=ph) for v in ("front", "side", "back")]
    gap = np.ones((ph, 12, 3), np.float32) * 0.3
    def join(lst):
        out = []
        for x in lst:
            out += [x, gap]
        return np.concatenate(out[:-1], 1)
    row1 = np.concatenate([join(crops), gap, gap, join(painted)], 1)
    row2 = np.concatenate([join(diffs), gap, gap, join(grey)], 1)
    w = max(row1.shape[1], row2.shape[1])
    def padw(x):
        return np.concatenate([x, np.ones((x.shape[0], w - x.shape[1], 3), np.float32) * 0.3], 1) if x.shape[1] < w else x
    return [padw(row1), padw(row2)], padw


# ------------------------------------------------------------------------------------------------------------------
# One figure
# ------------------------------------------------------------------------------------------------------------------

def build(name):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    cfg = dict(NPCS[name])
    print("=== %s" % name)
    sh = Sheet(cfg)
    B = Body(sh)
    M = Mesh()
    T, ia, arm_rings, leg_rings, joints = build_body(M, B)
    M.leg_rings = leg_rings
    hd = build_head(M, B, cfg["head_mix"], T[-1], T)
    hand_k = build_hands(M, B, joints, arm_rings)
    remap = drop_unused(M)
    M.crotch = remap[M.crotch]
    M.leg_rings = {s: [[remap[v] for v in r] for r in rings] for s, rings in leg_rings.items()}
    T = [[remap.get(v, v) for v in r] for r in T]
    M.head_idx = [remap[v] for v in M.head_idx if v in remap]
    M.wrists = [([[remap[v] for v in r] for r in rings], [remap[v] for v in hole]) for rings, hole in M.wrists]
    flipped, nonman = fix_winding(M)
    print("  winding: %d faces turned, %d edges not manifold" % (flipped, nonman))
    mir = mirror_map(M)
    nb = M.neighbours()
    body_sel = np.isin(np.array([p.split("_")[0] for p in M.part]), FIT_PARTS)
    silhouette_diffs(M, sh, "(lofted)")
    for rnd in range(FIT_ROUNDS):
        n, worst = fit_round(M, sh, B, nb, damp=0.8 if rnd < FIT_ROUNDS - 1 else 0.6)
        symmetrize(M, mir)
        smooth(M, body_sel, rounds=1, lam=0.3, mu=-0.32, nb=nb)
        print("  fit round %d: %d outline points, largest move %.1f cm" % (rnd + 1, n, worst * 100))
    smooth(M, body_sel, rounds=2, lam=0.35, mu=-0.37, nb=nb)
    symmetrize(M, mir)
    for wr in M.wrists:
        match_wrist(M, wr)
    is_c = find_cloth(M, sh, top_z=sh.z(B.armpit_row) + 0.01 * B.k)
    U = make_underwear(M, is_c, B)
    fold, flat = folded_faces(M)
    print("  folded faces %d, faces with no area %d; underwear %d faces" % (fold, flat, len(U.F)))
    gaps, diff_pics = silhouette_diffs(M, sh, "(fitted, skin)")
    # the silhouette with the underwear on (what is seen)
    MU = Mesh()
    MU.P = list(M.P) + list(U.P)
    MU.part = list(M.part) + list(U.part)
    MU.F = list(M.F) + [[v + len(M.P) for v in f] for f in U.F]
    gaps, diff_pics = silhouette_diffs(MU, sh, "(fitted, dressed)")
    if PICS:
        save_png(os.path.join(PICS, "%s_diff.png" % name), np.concatenate([diff_pics[v] for v in ("front", "side", "back")], 1))
        cm = np.zeros(sh.mask.shape + (3,), np.float32)
        cm[sh.mask] = 0.4
        cm[sh.cloth] = (1, 0.9, 0.3)
        save_png(os.path.join(PICS, "%s_cloth.png" % name), resize(cm, h=600))
    # the skeleton and weights
    bones = skeleton(M, B, joints, T, hd)
    W = weights(M, bones, joints, hd, B.k)
    WU = [W[U.src[i]] for i in range(len(U.P))]
    # UVs
    isl = plan_uvs(M, B, T, joints)
    skin_names = [n for n in isl if n != "head"]
    dens = {n: (1.7 if n.startswith("hand") else 1.0) for n in skin_names}
    dens["neck"] = 1.2
    skin_uv, sscale = pack({n: isl[n] for n in skin_names}, dens, 6 / SKIN_PX)
    head_faces = [fi for fi, p in enumerate(M.fpart) if p == "head"]
    hu = {fi: M.fuv[fi] for fi in head_faces}
    pts = np.array([q for c in hu.values() for q in c])
    lo, hi = pts.min(0), pts.max(0)
    sc_ = (1 - 2 * 6 / FACE_PX) / (hi - lo).max()
    face_uv = {fi: [((u - lo[0]) * sc_ + 6 / FACE_PX, (v - lo[1]) * sc_ + 6 / FACE_PX) for u, v in c] for fi, c in hu.items()}
    # the underwear's UVs: its faces' islands from the body's, packed alone
    uisl = {}
    body_face_of = {tuple(sorted(f)): fi for fi, f in enumerate(M.F)}
    U.body_face = []
    for ui, f in enumerate(U.F):
        fi = body_face_of[tuple(sorted(U.src[v] for v in f))]
        U.body_face.append(fi)
        name_ = M.fpart[fi]
        if name_ in isl and fi in isl[name_]:
            # the corners in the underwear's own order
            order = [M.F[fi].index(U.src[v]) for v in f]
            uisl.setdefault(name_, {})[ui] = [isl[name_][fi][o] for o in order]
    under_uv, _ = pack(uisl, {}, 6 / CLOTH_PX)
    # pictures
    tex_dir = os.path.join(ROOT, "textures", "npc", name)
    os.makedirs(tex_dir, exist_ok=True)
    ref = skin_stats(sh, B)
    print("  skin colour", ref.round(3))
    # depth buffers of the dressed figure
    PU = np.array(MU.P)
    trisU = MU.tris()
    zbufs = {}
    for v in ("front", "back", "side", "side_l"):
        Q = sh.to_px(v, PU)
        zbufs[v], _, _ = raster(Q[:, :2], Q[:, 2], trisU, (sh.H, sh.W))
    P = M.arr()
    N = M.normals()
    skin_faces = [fi for fi in range(len(M.F)) if fi in skin_uv]
    ok, Pt, Nt, tt, bb = texel_points(M, skin_uv, skin_faces, SKIN_PX, P, N)
    img, val = paint(sh, ok, Pt, Nt, zbufs, "skin", ref)
    skin_img = fill_out(img, val, ok, ref)
    ok, Pt, Nt, tt, bb = texel_points(M, face_uv, head_faces, FACE_PX, P, N)
    scalp = scalp_mask(M, tt, bb, cfg["sex"])
    img, val = paint(sh, ok, Pt, Nt, zbufs, "skin", ref, scalp=scalp, head=True)
    face_img = fill_out(img, val, ok, ref * 0.97)
    PUu = U.arr()
    NU = U.normals()
    ok, Pt, Nt, tt, bb = texel_points(U, under_uv, list(range(len(U.F))), CLOTH_PX, PUu, NU)
    cloth_ref = np.median(sh.pix[sh.cloth].reshape(-1, 3)[::50], 0) if sh.cloth.any() else np.array([0.85, 0.82, 0.75])
    img, val = paint(sh, ok, Pt, Nt, zbufs, "cloth", ref)
    under_img = fill_out(img, val, ok, cloth_ref)
    paths = {}
    for key, im_, px in (("skin", skin_img, SKIN_PX), ("face", face_img, FACE_PX), ("underwear", under_img, CLOTH_PX)):
        paths[key] = os.path.join(tex_dir, "%s_%s.png" % (name, key))
        save_png(paths[key], im_)
    layout_picture(skin_uv, M.F, SKIN_PX, os.path.join(tex_dir, "%s_skin_layout.png" % name))
    layout_picture(face_uv, M.F, FACE_PX, os.path.join(tex_dir, "%s_face_layout.png" % name))
    layout_picture(under_uv, U.F, CLOTH_PX, os.path.join(tex_dir, "%s_underwear_layout.png" % name))
    # Blender objects
    arm = make_armature("%s_armature" % name, bones)
    m_skin = image_material("%s_skin" % name, paths["skin"])
    m_face = image_material("%s_face" % name, paths["face"])
    m_under = image_material("%s_underwear" % name, paths["underwear"], double=True)
    fuv = [skin_uv.get(fi) or face_uv.get(fi) for fi in range(len(M.F))]
    fmat = [1 if fi in face_uv else 0 for fi in range(len(M.F))]
    body_ob = mesh_object("%s_body" % name, M.P, M.F, fuv, fmat, [m_skin, m_face], arm, W)
    under_ob = mesh_object("%s_underwear" % name, U.P, U.F, [under_uv[i] for i in range(len(U.F))], [0] * len(U.F),
                           [m_under], arm, WU)
    tri_body = sum(len(f) - 2 for f in M.F)
    per = {}
    for f in M.F:
        fam_ = M.part[f[0]].split("_")[0]
        per[fam_] = per.get(fam_, 0) + len(f) - 2
    print("  triangles by part", per)
    tri_under = sum(len(f) - 2 for f in U.F)
    zmax = max(p[2] for p in M.P)
    print("  triangles: body %d, underwear %d, together %d; height %.3f m" % (tri_body, tri_under, tri_body + tri_under,
                                                                         zmax))
    glb = os.path.join(ROOT, "models", "npc", "%s.glb" % name)
    os.makedirs(os.path.dirname(glb), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.export_scene.gltf(filepath=glb, export_format="GLB", export_skins=True, export_animations=False,
                              export_yup=True, export_apply=False)
    blend = os.path.join(HERE, "blend", "npc", "%s.blend" % name)
    os.makedirs(os.path.dirname(blend), exist_ok=True)
    stats = dict(name=name, height=zmax, tris=tri_body + tri_under, tri_body=tri_body, tri_under=tri_under,
                 gaps={v: g[0] for v, g in gaps.items()}, head_gaps={v: g[1] for v, g in gaps.items()},
                 folded=fold, nonmanifold=nonman, hand_k=hand_k)
    if PICS:
        os.makedirs(PICS, exist_ok=True)
        rows, padw = compare_picture(name, sh, diff_pics, cfg["height"], PICS)
        pose = pose_check(arm, cfg["height"], PICS, name)
        pose = resize(pose, h=rows[0].shape[0] // 2)
        # close up: the head (grey front, side, three-quarter; painted front, side) and the left hand
        hz = (hd["chin"] + hd["crown"]) / 2
        hy = hd["tip_y"] + 0.09 * B.k
        hs = (hd["crown"] - hd["chin"]) * 1.6
        cl = []
        for a, tx in ((0.0, False), (-math.pi / 2, False), (0.7, False), (0.0, True), (-math.pi / 2, True)):
            cl.append(shoot(os.path.join(PICS, "%s_head_%d%d.png" % (name, int(a * 10), tx)), a, (0, hy, hz), hs, 300, 300,
                            tx))
        Wl = joints["wrist_l"] + joints["arm_t_l"] * B.hand_len * 0.5
        for a in (0.0, 1.2):
            cl.append(shoot(os.path.join(PICS, "%s_hand_%d.png" % (name, int(a * 10))), a, tuple(Wl), B.hand_len * 1.5,
                            300, 300, False))
        close = np.concatenate(cl, 1)
        close = resize(close, h=pose.shape[0])
        last = np.concatenate([pose, np.ones((pose.shape[0], 12, 3), np.float32) * 0.3, close], 1)
        if last.shape[1] > rows[0].shape[1]:
            last = resize(last, w=rows[0].shape[1])
        rows.append(padw(last))
        bar = label_bar(rows[0].shape[1], 10)
        out = []
        for r in rows:
            out += [r, bar]
        save_png(os.path.join(PICS, "%s_compare.png" % name), np.concatenate(out[:-1], 0))
        with open(os.path.join(PICS, "%s_stats.json" % name), "w") as f:
            json.dump(stats, f, indent=1)
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    print("  wrote", glb, blend)
    return stats


def lineup():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    x = 0.0
    done = []
    for name in ORDER:
        glb = os.path.join(ROOT, "models", "npc", "%s.glb" % name)
        if not os.path.exists(glb):
            continue
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=glb)
        new = [o for o in bpy.data.objects if o not in before]
        roots = [o for o in new if o.parent is None]
        for o in roots:
            o.location.x += x
        x += 1.0
        done.append(name)
    top = 1.95
    w = int(220 * len(done))
    a = shoot(os.path.join(PICS, "lineup_grey.png"), 0.0, ((x - 1.0) / 2, 0, top / 2), max(x + 0.2, top * 1.1) * 1.0,
              w, int(w * top * 1.1 / max(x + 0.2, top * 1.1)), False)
    b = shoot(os.path.join(PICS, "lineup_paint.png"), 0.0, ((x - 1.0) / 2, 0, top / 2), max(x + 0.2, top * 1.1) * 1.0,
              w, int(w * top * 1.1 / max(x + 0.2, top * 1.1)), True)
    save_png(os.path.join(PICS, "lineup.png"), np.concatenate([a, np.ones((8, a.shape[1], 3)) * 0.3, b], 0))
    print("LINEUP", done)


def main():
    if not ARGS:
        raise SystemExit("name or all or lineup")
    what = ARGS[0]
    if what == "lineup":
        lineup()
        return
    names = ORDER if what == "all" else [what]
    allstats = []
    for n in names:
        allstats.append(build(n))
    for s in allstats:
        print("DONE %-18s %.3f m  %d triangles  gaps(cm) %s" % (s["name"], s["height"], s["tris"],
                                                             {v: round(g[0], 1) for v, g in s["gaps"].items()}))


main()
