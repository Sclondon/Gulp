"""Builds the whale shark (creatures/whale_shark) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/whale_shark/tools/build_whale_shark.py
    blender --background --python creatures/whale_shark/tools/build_whale_shark.py -- <preview folder>   # with pictures

It writes creatures/whale_shark/models/whale_shark.glb (the full model) and whale_shark_lo.glb (far off, phones,
many at once), and the editable creatures/whale_shark/tools/whale_shark.blend (this folder has a .gdignore). Each
model is one still mesh with one surface: the shader (whale_shark.gdshader) bends it to swim, works its jaws and
draws every marking. It prints a WINDING line for each model: the check that nothing is inside out. It also writes
creatures/whale_shark/models/whale_shark_game.glb, the game model (2026-11-18: GAME_MESH below; the same curves and
outlines sampled where they show, at about the weight of a Twilight Princess model).
The whale shark (Rhincodon typus), 10 m from the front of its mouth to the tip of its tail, nose towards -Z, belly
down, its origin at the middle of its length on the line through the front of its head. Built from the species'
anatomy; nothing traced or copied:

- THE BODY: one skin, deepest (0.18 of its length) and widest (0.16) a quarter to a third of the way back, with a
  broad, flat head whose front is square across, and three ridges along each flank (the lowest running on into
  the keel of the tail's wrist). The underside of the head from its front back to the corners of the mouth is
  the roof of the mouth: the mouth is right at the front, as wide as the head.
- THE LOWER JAW: a part of its own under the head, flush with its front, which fits up against that roof and runs
  back into the throat (the shader drops it about its hinge at the corners of the mouth, bows its lip down and
  lifts the upper lip in the middle, so that the open mouth is a great oval).
- NO TEETH worth building (a whale shark's are tiny); the inside of the mouth is drawn by the shader.
- EYES: small domes on the sides of the head, just behind the corners of the mouth.
- THE FINS: thick closed foils with no rays: a tall first dorsal a little behind the middle, a small second
  dorsal and anal fin, big sickle pectoral fins, pelvic fins, and a tall crescent tail whose upper lobe is the
  longer.
- The five very long gill slits each side are drawn by the shader (GILLS here says where; the shader has the same numbers).

What a point is, for the shader: vertex colour red the part, as a twentieth (0 body, 1 lower jaw, 2 eye, 3 upper
tooth, 4 lower tooth, 5 first dorsal, 6 second dorsal, 7 tail, 8 anal, 9 pelvic, 10 pectoral, 11 cheek: UV.x 0 at
its top edge to 1 at its lower edge, which goes with the jaw; green as the body's). On the body and the
jaw: UV.x how far along the fish (0 snout to 1 tail tip), UV.y how high on it (0 the line under the belly and
chin to 1 the back line); UV2.x how far round the skin from the back line (metres, + on its right side, - on its
left; on the jaw, how far to the side), UV2.y on the body the whole way from back line to belly line there
(metres); green how much a point goes with the upper jaw when it pushes out, blue how much it is inside the
mouth. On an eye: UV where a point is on its round face seen straight on (its middle at 0.5, 0.5; its rim 0.5
away). On a tooth: UV.x root (0) to tip (1); green as the body's. On a fin: UV.x from its root (0) to its edge
(1), UV.y along its outline from its leading root (0) to its trailing root (1). (The glTF writer flips V: what is
written here is 1 - v, so that Godot reads v.)

Everything here is worked out in body lengths in Godot space (Y up, nose towards -Z) and written out in metres.
The numbers the shader and the script share (LENGTH, the jaw's hinge, the gill slits) are kept in step by hand:
change one, change the others.
"""

import bisect
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "models")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = ARGS[0] if ARGS else ""
TAU = math.tau
BODY, JAW, EYE, UPPER, LOWER, DORSAL, DORSAL2, TAIL, ANAL, PELVIC, PECTORAL, CHEEK = range(12)
# (added 2026-11-18: the gill arches in the throat, and the flaps of the gill slits)
GILL, SLIT = 12, 13
LIP = None

# ---------------------------------------------------------------------------------------------------------------
# The species. Kept in step with whale_shark.gd and whale_shark.gdshader.
NAME = "whale_shark"
LENGTH = 10.0
# The body and upper head: s, top, bottom, half width, widest at (0 bottom to 1 top), boxiness above, below.
BODY_ROWS = [
    # (the broad, flat head; its front is the upper lip, square across, the mouth right at the front)
    (0.000, 0.008, -0.010, 0.030, 0.45, 2.4, 3.0),
    (0.003, 0.018, -0.011, 0.045, 0.40, 2.6, 4.0),
    (0.010, 0.029, -0.012, 0.057, 0.35, 2.6, 4.0),
    (0.025, 0.040, -0.013, 0.066, 0.30, 2.5, 4.0),
    (0.045, 0.050, -0.014, 0.072, 0.30, 2.4, 4.0),
    (0.060, 0.056, -0.015, 0.076, 0.30, 2.4, 3.6),
    (0.080, 0.063, -0.045, 0.078, 0.38, 2.3, 2.6),
    (0.130, 0.076, -0.068, 0.080, 0.44, 2.3, 2.3),
    (0.220, 0.090, -0.079, 0.080, 0.48, 2.3, 2.2),
    (0.320, 0.097, -0.080, 0.077, 0.50, 2.2, 2.2),
    (0.420, 0.095, -0.074, 0.070, 0.50, 2.2, 2.2),
    (0.520, 0.083, -0.062, 0.058, 0.50, 2.1, 2.1),
    (0.620, 0.061, -0.046, 0.042, 0.50, 2.0, 2.0),
    (0.700, 0.040, -0.032, 0.031, 0.50, 1.8, 1.8),
    # (the wrist of the tail: wider than deep, the lowest ridge become a keel each side)
    (0.750, 0.027, -0.022, 0.029, 0.50, 1.5, 1.5),
    (0.780, 0.022, -0.018, 0.026, 0.50, 1.5, 1.5),
    (0.810, 0.018, -0.015, 0.016, 0.50, 1.7, 1.7),
    (0.830, 0.012, -0.010, 0.005, 0.50, 2.0, 2.0),
    (0.840, 0.006, -0.005, 0.000, 0.50, 2.0, 2.0),
]
# The lower jaw and throat, as the body's rows. LIP for a top: the lip line, just up inside the roof of the mouth.
# (Its front is flush with the head's: the mouth is at the very front, as wide as the head.)
JAW_ROWS = [
    (0.000, LIP, -0.018, 0.028, 0.80, 3.5, 2.4),
    (0.003, LIP, -0.022, 0.043, 0.80, 3.5, 2.4),
    (0.010, LIP, -0.026, 0.055, 0.80, 3.5, 2.4),
    (0.025, LIP, -0.030, 0.063, 0.80, 3.5, 2.4),
    (0.045, LIP, -0.036, 0.066, 0.80, 3.2, 2.2),
    (0.060, LIP, -0.042, 0.066, 0.80, 3.0, 2.2),
    (0.075, -0.035, -0.050, 0.058, 0.70, 2.4, 2.1),
    (0.095, -0.050, -0.057, 0.040, 0.60, 2.2, 2.1),
    (0.110, -0.056, -0.059, 0.018, 0.50, 2.0, 2.0),
    (0.118, -0.0565, -0.0630, 0.000, 0.50, 2.0, 2.0),
]
# Where the lower jaw hinges (how far along, how high).
HINGE_S = 0.058
HINGE_Y = -0.030
# The cheeks: a fold of skin each side that closes the side of the open mouth from this far between the front of
# the mouth (0) and the hinge (1) back to the hinge; ahead of it the mouth is open.
CHEEK_FROM = 0.35
# The upper lip lifts most in the middle (so that the open mouth is an oval), not as one piece.
UPPER_ARC = True
# The eye: how far along, how high, the ball's radius, how far it stands out of the head. (Small, just behind the
# corners of the mouth.)
EYE_AT = (0.062, 0.006, 0.0036, 0.0012)
# The gill slits (for the docs: the shader draws them): where each is along the fish, and from how high to how high.
GILLS = ((0.135, 0.152, 0.169, 0.186, 0.203), 0.15, 0.82)
# The same slits as the shader draws them, for their flaps (2026-11-18): the first's place, the step to the next, the
# first's top (and how much lower each next one's is, times i squared over 4), how it leans (as h - 0.5) and bows
# (as (h - 0.48) squared), the lowest h, and how much higher each next one starts.
SLIT_LINE = (0.135, 0.017, 0.82, 0.03, 0.01, 0.02, 0.165, 0.02)
# Ridges along the flank: (how high, how far they stand out, from, to). Three each side; the lowest runs on into
# the keel of the tail's wrist.
RIDGES = [(0.84, 0.0040, 0.14, 0.72), (0.67, 0.0036, 0.22, 0.70), (0.51, 0.0042, 0.28, 0.83)]
# Rings of points round the body (each side) and along it (head, the rest), full and low. (More round it than the
# other sharks, for the ridges.)
BODY_MESH = {"half": (48, 10), "head": (40, 10), "rest": (150, 26)}
# The teeth: none worth building (a whale shark's are tiny, in bands of hundreds).
TEETH = {}
# The game model (added 2026-11-18): how many rings along the body (placed where its outline bends most), how
# many points round each side above and below its widest line, the jaw's the same, the fins' longest step along
# their outlines (body lengths; every point of the outlines above is kept), where their rows are from root (0) to
# edge (1), the tail's step, the eye's rows and points round, the share of the teeth kept, the cheeks' columns and
# rows.
GAME_MESH = {"rings": 36, "up": 6, "down": 6, "jaw": (3, 4), "fin_step": 0.022, "fin_rows": (0.0, 0.6, 0.93, 1.0),
             "tail_step": 0.018, "eye": (4, 24), "teeth": 0.7, "cheek": (8, 2)}


def median_fins():
    """The fins on the middle plane: (name, part, root at s0, root at s1, +1 on the back or -1 under the belly,
    the outline between the roots as (s, height from the body's line at s0), thickness at the root)."""
    return [
        ("dorsal", DORSAL, 0.460, 0.560, 1, [(0.480, 0.035), (0.505, 0.070), (0.530, 0.094), (0.545, 0.101),
                                               (0.553, 0.094), (0.553, 0.060), (0.557, 0.030), (0.575, 0.008)], 0.016),
        ("dorsal2", DORSAL2, 0.735, 0.757, 1, [(0.742, 0.012), (0.750, 0.022), (0.756, 0.024), (0.759, 0.017),
                                               (0.762, 0.008), (0.772, 0.002)], 0.005),
        ("anal", ANAL, 0.745, 0.765, -1, [(0.751, 0.010), (0.758, 0.019), (0.764, 0.021), (0.766, 0.014),
                                          (0.769, 0.007), (0.778, 0.002)], 0.005),
    ]


# The tail: its outline from the root on the back, round the upper lobe, the fork and the lower lobe, to the root
# under the wrist, as (s, y); and its thickness at the root. A tall crescent, its upper lobe the longer.
TAIL_OUTLINE = [(0.795, 0.016), (0.835, 0.040), (0.880, 0.085), (0.930, 0.135), (0.975, 0.172), (1.000, 0.186),
                (0.993, 0.170), (0.950, 0.110), (0.915, 0.055), (0.897, 0.018), (0.892, 0.000),
                (0.897, -0.025), (0.915, -0.060), (0.940, -0.095), (0.957, -0.113), (0.946, -0.111),
                (0.905, -0.080), (0.855, -0.040), (0.805, -0.013)]
TAIL_THICK = 0.030
# The paired fins, the right one of each: (name, part, root from s0 to s1, how high on the body the root is
# (0 belly to 1 back) at each end, the way out of the body the fin goes, its outline between the roots as (how far
# back along the root line, how far out), thickness at the root).
PAIRED = [
    ("pectoral", PECTORAL, 0.200, 0.270, 0.22, 0.19, (0.82, -0.57, 0.0),
     [(0.030, 0.045), (0.065, 0.095), (0.100, 0.140), (0.125, 0.170), (0.135, 0.178), (0.136, 0.165),
      (0.124, 0.125), (0.108, 0.075), (0.098, 0.035), (0.100, 0.010)], 0.018),
    ("pelvic", PELVIC, 0.530, 0.575, 0.10, 0.10, (0.55, -0.83, 0.0),
     [(0.012, 0.016), (0.030, 0.030), (0.044, 0.038), (0.050, 0.034), (0.051, 0.018), (0.058, 0.006)], 0.009),
]
# ---------------------------------------------------------------------------------------------------------------


def to_b(p):
    return Vector((p.x, -p.z, p.y))


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def curve(points):
    """A smooth line through (x, y) points that never overshoots them."""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] > 0.0:
            w1 = 2.0 * h[i] + h[i - 1]
            w2 = h[i] + 2.0 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def f(x):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = bisect.bisect_right(xs, x) - 1
        t = (x - xs[i]) / h[i]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])
    return f


class Section:
    """A lofted skin: at each place along the fish (s, 0 snout to 1 tail tip) its top line, bottom line, half
    width, how far up from the bottom it is widest (0..1), and how boxy its upper and lower halves are (2 an
    ellipse, more is squarer). All in body lengths."""

    def __init__(self, rows):
        self.first = rows[0][0]
        self.last = rows[-1][0]
        self.f = [curve([(r[0], r[k]) for r in rows]) for k in range(1, 7)]

    def at(self, s):
        return [f(s) for f in self.f]

    def top(self, s):
        return self.f[0](s)

    def bot(self, s):
        return self.f[1](s)

    def x_at(self, s, y):
        """How far out the skin is at height y."""
        top, bot, hw, ycf, nt, nb = self.at(s)
        yc = bot + ycf * (top - bot)
        if y >= yc:
            u, n = (y - yc) / max(top - yc, 1e-9), nt
        else:
            u, n = (yc - y) / max(yc - bot, 1e-9), nb
        u = max(0.0, min(1.0, u))
        return hw * (1.0 - u ** n) ** (1.0 / n)

    def y_at(self, s, x, upper):
        """How high the skin's upper (or lower) half is, `x` out from the middle."""
        top, bot, hw, ycf, nt, nb = self.at(s)
        yc = bot + ycf * (top - bot)
        q = max(0.0, min(1.0, x / max(hw, 1e-9)))
        if upper:
            return yc + (top - yc) * (1.0 - q ** nt) ** (1.0 / nt)
        return yc - (yc - bot) * (1.0 - q ** nb) ** (1.0 / nb)

    def outline(self, s, half):
        """half + 1 points down its right side from the top line to the bottom line, evenly spaced along the
        skin: (x, y, how far round from the top)."""
        top, bot, hw, ycf, nt, nb = self.at(s)
        yc = bot + ycf * (top - bot)
        dense = []
        steps = 200
        for i in range(steps + 1):
            phi = math.pi * i / steps
            c, sn = math.cos(phi), max(math.sin(phi), 0.0)
            if c >= 0.0:
                dense.append((hw * sn ** (2.0 / nt), yc + (top - yc) * c ** (2.0 / nt)))
            else:
                dense.append((hw * sn ** (2.0 / nb), yc - (yc - bot) * (-c) ** (2.0 / nb)))
        dense[0] = (0.0, top)
        dense[-1] = (0.0, bot)
        acc = [0.0]
        for i in range(steps):
            acc.append(acc[-1] + math.hypot(dense[i + 1][0] - dense[i][0], dense[i + 1][1] - dense[i][1]))
        whole = acc[-1]
        out = []
        for j in range(half + 1):
            want = whole * j / half
            i = min(bisect.bisect_right(acc, want) - 1, steps - 1)
            span = acc[i + 1] - acc[i]
            t = (want - acc[i]) / span if span > 1e-12 else 0.0
            out.append((lerp(dense[i][0], dense[i + 1][0], t), lerp(dense[i][1], dense[i + 1][1], t), want))
        return out, whole

    def outline_at(self, s, marks, between):
        """For the game model: points down its right side from the top line to the bottom line: at each of
        `marks` (0 the top, 1 the bottom, or ("widest",) its widest point, or ("h", h) a height on the fish, 0
        its lowest line to 1 its back), and between each mark and the next `between[k]` more, evenly spaced along
        the skin: (x, y, how far round from the top), and the whole way."""
        top, bot, hw, ycf, nt, nb = self.at(s)
        yc = bot + ycf * (top - bot)
        dense = []
        steps = 200
        for i in range(steps + 1):
            phi = math.pi * i / steps
            c, sn = math.cos(phi), max(math.sin(phi), 0.0)
            if c >= 0.0:
                dense.append((hw * sn ** (2.0 / nt), yc + (top - yc) * c ** (2.0 / nt)))
            else:
                dense.append((hw * sn ** (2.0 / nb), yc - (yc - bot) * (-c) ** (2.0 / nb)))
        dense[0] = (0.0, top)
        dense[-1] = (0.0, bot)
        acc = [0.0]
        for i in range(steps):
            acc.append(acc[-1] + math.hypot(dense[i + 1][0] - dense[i][0], dense[i + 1][1] - dense[i][1]))
        whole = acc[-1]
        at = []
        for mark in marks:
            if isinstance(mark, tuple) and mark[0] == "widest":
                want = acc[steps // 2]
            elif isinstance(mark, tuple):
                low = low_line(s)
                y = low + mark[1] * (BODY_SKIN.top(s) - low)
                want = acc[-1]
                for i in range(steps):
                    if dense[i][1] >= y >= dense[i + 1][1]:
                        span = dense[i][1] - dense[i + 1][1]
                        want = lerp(acc[i], acc[i + 1], (dense[i][1] - y) / span if span > 1e-12 else 0.0)
                        break
                want = max(0.02 * whole, min(0.98 * whole, want))
            else:
                want = whole * mark
            at.append(want)
        wants = []
        for k in range(len(at) - 1):
            a, b = at[k], max(at[k + 1], at[k])
            n = between[k] + 1
            wants += [lerp(a, b, j / n) for j in range(n)]
        wants.append(at[-1])
        out = []
        for want in wants:
            i = min(bisect.bisect_right(acc, want) - 1, steps - 1)
            span = acc[i + 1] - acc[i]
            t = (want - acc[i]) / span if span > 1e-12 else 0.0
            out.append((lerp(dense[i][0], dense[i + 1][0], t), lerp(dense[i][1], dense[i + 1][1], t), want))
        return out, whole


BODY_SKIN = Section(BODY_ROWS)


def lip(s):
    """The lower jaw's lip line: just up inside the roof of the mouth."""
    return BODY_SKIN.bot(s) + 0.002


JAW_SKIN = Section([(r[0], lip(r[0]) if r[1] is LIP else r[1]) + tuple(r[2:]) for r in JAW_ROWS])
# Where the mouth begins.
MOUTH_S = JAW_SKIN.first


def low_line(s):
    """The fish's lowest line: under the chin where the jaw is, under the belly behind it."""
    b = BODY_SKIN.bot(s)
    if JAW_SKIN.first <= s <= JAW_SKIN.last:
        b = min(b, JAW_SKIN.bot(s))
    return b


def height(s, y):
    low = low_line(s)
    return (y - low) / max(BODY_SKIN.top(s) - low, 1e-9)


def ridge(s, h):
    """How far the flank's ridges stand out at a place."""
    out = 0.0
    for at, stands, s0, s1 in RIDGES:
        out += stands * math.exp(-((h - at) / 0.035) ** 2) * smooth(s0, s0 + 0.08, s) * (1.0 - smooth(s1 - 0.1, s1, s))
    return out


def body_x(s, y):
    """How far out the body's skin is at height y."""
    return BODY_SKIN.x_at(s, y) + ridge(s, height(s, y))


def body_frame(s, y, plain=False):
    """A place on the body's right side: the point, the way out of the skin there, and the way up along it.
    (`plain`: on the skin without its ridges, smoother, under them.)"""
    e = 0.002
    side = BODY_SKIN.x_at if plain else body_x
    x = side(s, y)
    dy = (side(s, y + e) - side(s, y - e)) / (2 * e)
    ds = (side(s + e, y) - side(s - e, y)) / (2 * e)
    return Vector((x, y, s - 0.5)), Vector((1.0, -dy, -ds)).normalized(), Vector((dy, 1.0, 0.0)).normalized()


class Part:
    """One closed piece of the fish: points (body lengths), what each is for the shader, and faces. `done`
    welds it, turns every face outward and checks that."""

    def __init__(self, name):
        self.name = name
        self.verts = []
        self.data = []
        self.faces = []

    def add(self, p, uv, uv2, colour):
        self.verts.append(Vector(p))
        self.data.append((uv, uv2, colour))
        return len(self.verts) - 1

    def loft(self, rings):
        for a, b in zip(rings, rings[1:]):
            n = len(a)
            for j in range(n):
                self.faces.append((a[j], a[(j + 1) % n], b[(j + 1) % n], b[j]))

    def mirrored(self, name):
        other = Part(name)
        for p, d in zip(self.verts, self.data):
            other.add((-p.x, p.y, p.z), d[0], (-d[1][0], d[1][1]), d[2])
        other.faces = list(self.faces)
        return other

    @staticmethod
    def inside_out(bm):
        """How many of a closed solid's faces face inwards, and how many were looked at: a line out of a face,
        the way the face faces, comes out through the solid's skin an even number of times (none, for most)."""
        cut = bm.copy()
        bmesh.ops.triangulate(cut, faces=cut.faces)
        cut.normal_update()
        tree = BVHTree.FromBMesh(cut)
        wrong = 0
        counted = 0
        for f in cut.faces:
            if f.calc_area() > 1e-11:
                counted += 1
                at = f.calc_center_median() + f.normal * 2e-6
                hits = 0
                while hits < 40:
                    hit = tree.ray_cast(at, f.normal)
                    if hit[0] is None:
                        break
                    hits += 1
                    at = hit[0] + f.normal * 2e-6
                if hits % 2:
                    wrong += 1
        cut.free()
        return wrong, counted

    def done(self):
        """Returns (faces as lists of (point in Blender metres, uv, uv2, colour), faces wound wrongly, faces)."""
        bm = bmesh.new()
        uv = bm.loops.layers.uv.new("uv")
        uv2 = bm.loops.layers.uv.new("uv2")
        colour = bm.loops.layers.float_color.new("colour")
        made = [bm.verts.new(to_b(p * LENGTH)) for p in self.verts]
        for face in self.faces:
            # (a face that closes to a point has corners in one place: the weld below makes a triangle of it
            # or drops it)
            try:
                f = bm.faces.new([made[i] for i in face])
            except ValueError:
                continue
            for loop, i in zip(f.loops, face):
                d = self.data[i]
                loop[uv].uv = d[0]
                loop[uv2].uv = d[1]
                loop[colour] = (d[2][0], d[2][1], d[2][2], 1.0)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-6 * LENGTH)
        # (where a skin closes to a line on the middle plane, or a fin on that plane thins to nothing, a
        # four-cornered face has three corners in that plane: cut it from its fourth corner, or whoever cuts it
        # in two later may leave a triangle lying flat in the plane, back to back with its twin)
        for f in list(bm.faces):
            if len(f.verts) == 4:
                off = [loop for loop in f.loops if abs(loop.vert.co.x) > 1e-8]
                if len(off) == 1:
                    bmesh.ops.connect_verts(bm, verts=[off[0].vert, off[0].link_loop_next.link_loop_next.vert])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.normal_update()
        # The check, which does not trust the line above (it has turned a whole fin inside out before now).
        wrong, counted = self.inside_out(bm)
        if wrong * 2 > counted:
            bmesh.ops.reverse_faces(bm, faces=bm.faces)
            bm.normal_update()
            wrong, counted = self.inside_out(bm)
        out = []
        for f in bm.faces:
            out.append([(loop.vert.co.copy(), tuple(loop[uv].uv), tuple(loop[uv2].uv), tuple(loop[colour]))
                        for loop in f.loops])
        bm.free()
        return out, wrong, counted


def upper_goes(s):
    """How much of a point under the head goes with the upper jaw when it moves."""
    return smooth(MOUTH_S - 0.03, MOUTH_S + 0.002, s) * smooth(HINGE_S + 0.008, HINGE_S - 0.03, s)


def upper_arc(s, x):
    """How much of that a point `x` out from the middle takes (UPPER_ARC: most in the middle, none at the corners
    of the mouth)."""
    if not UPPER_ARC:
        return 1.0
    wide = JAW_SKIN.at(max(JAW_SKIN.first, min(s, JAW_SKIN.last)))[2]
    return max(0.0, 1.0 - (x / max(wide, 1e-6)) ** 2)


def skin(part, section, places, half, kind, side_of=None):
    """Lofts a Section into a Part. `kind` is BODY or JAW. `side_of(s)`, for the game model, gives each ring's
    points down the right side (as Section.outline does) in place of `half` evenly spaced ones."""
    rings = []
    for s in places:
        if side_of:
            side, whole = side_of(s)
            half = len(side) - 1
        else:
            side, whole = section.outline(s, half)
        top, bot, hw, ycf = section.at(s)[:4]
        yc = bot + ycf * (top - bot)
        ring = []
        # (down the right side and back up the left; the belly line is there twice, once for each side, so that
        # how far round the skin a point is does not run from one side's number to the other's across one face)
        for j in list(range(half + 1)) + list(range(half, 0, -1)):
            x, y, arc = side[j]
            sign = 1.0 if len(ring) <= half else -1.0
            h = height(s, y)
            if kind == BODY:
                if 0 < j < half:
                    x += ridge(s, h)
                under = max(0.0, (yc - y) / max(yc - bot, 1e-9))
                mouth_here = smooth(MOUTH_S - 0.003, MOUTH_S + 0.004, s) * smooth(HINGE_S + 0.012, HINGE_S - 0.012, s)
                jaw_wide = JAW_SKIN.at(s)[2]
                # the roof of the mouth: the flat underside of the head over the lower jaw
                roof = smooth(0.55, 0.9, under) * mouth_here * smooth(1.04 * jaw_wide + 1e-5, 0.88 * jaw_wide, x)
                # what goes with the upper jaw as it pushes out: the underside of the head round the mouth
                upper = smooth(0.1, 0.75, under) * upper_goes(s) * upper_arc(s, x)
                ring.append(part.add((sign * x, y, s - 0.5), (s, 1.0 - h),
                                     (sign * arc * LENGTH, 1.0 - whole * LENGTH), (0.0, upper, roof)))
            else:
                inside = smooth(0.5, 0.9, (y - yc) / max(top - yc, 1e-9)) if y > yc else 0.0
                inside *= smooth(HINGE_S + 0.025, HINGE_S - 0.002, s)
                ring.append(part.add((sign * x, y, s - 0.5), (s, 1.0 - h),
                                     (sign * x * LENGTH, 1.0), (JAW / 20.0, 0.0, inside)))
        rings.append(ring)
    part.loft(rings)
    # (a skin that begins blunt, not at a point, is closed across its front)
    if section.at(places[0])[2] > 1e-6:
        ring = rings[0]
        n = len(ring)
        for j in range(half):
            if j == 0:
                part.faces.append((ring[0], ring[1], ring[n - 1]))
            else:
                part.faces.append((ring[j], ring[j + 1], ring[n - j - 1], ring[n - j]))


def body_places(low):
    head = BODY_MESH["head"][1 if low else 0]
    rest = BODY_MESH["rest"][1 if low else 0]
    behind = HINGE_S + 0.03
    first = BODY_SKIN.first
    places = [first + (behind - first) * (i / head) ** 1.3 for i in range(head)]
    places += [lerp(behind, BODY_SKIN.last, i / rest) for i in range(rest + 1)]
    return places


def game_places():
    """The game model's rings along the body: a few where the mouth and its markings need them, then one at a
    time into whichever gap's straight lines miss the outline most (the back line, the lowest line, the half
    width, and the jaw's where it is), or is longest for the swimming to bend smoothly, until there are
    GAME_MESH["rings"]."""
    must = {BODY_SKIN.first, BODY_SKIN.last, MOUTH_S, MOUTH_S + 0.004, HINGE_S - 0.012, HINGE_S, HINGE_S + 0.012,
            HINGE_S + 0.03, JAW_SKIN.last, lerp(MOUTH_S, HINGE_S, CHEEK_FROM)}
    places = sorted(p for p in must if BODY_SKIN.first <= p <= BODY_SKIN.last)
    lines = [BODY_SKIN.top, low_line, lambda s: BODY_SKIN.at(s)[2]]
    jaw_lines = [JAW_SKIN.bot, lambda s: JAW_SKIN.at(s)[2]]

    def miss(a, b):
        if b - a < 0.002:
            return 0.0
        # (each line taken just inside the gap at its ends: the lowest line jumps where the mouth begins)
        a1, b1 = a + 1e-7, b - 1e-7
        worst = 0.0
        for k in range(1, 8):
            s = lerp(a, b, k / 8.0)
            for f in lines:
                worst = max(worst, abs(f(s) - lerp(f(a1), f(b1), k / 8.0)))
            if JAW_SKIN.first <= a and b <= JAW_SKIN.last:
                for f in jaw_lines:
                    worst = max(worst, abs(f(s) - lerp(f(a1), f(b1), k / 8.0)))
        return max(worst / 0.0004, (b - a) / 0.045)

    while len(places) < GAME_MESH["rings"]:
        k = max(range(len(places) - 1), key=lambda i: miss(places[i], places[i + 1]))
        places.insert(k + 1, 0.5 * (places[k] + places[k + 1]))
    return places


_GAME_SPLIT = {}


def game_side(section, kind):
    """For the game model: a function giving a ring's points down the right side: one on the back line, one on
    the widest line (or, with RIDGES, one on each ridge and either side of it), one on the lowest line, and
    GAME_MESH's counts spread evenly between them."""
    if kind == JAW:
        marks = [0.0, ("widest",), 1.0]
        between = [GAME_MESH["jaw"][0] - 1, GAME_MESH["jaw"][1] - 1]
    elif not RIDGES:
        marks = [0.0, ("widest",), 1.0]
        between = [GAME_MESH["up"] - 1, GAME_MESH["down"] - 1]
    else:
        marks = [0.0]
        for at, stands, s0, s1 in sorted(RIDGES, reverse=True):
            marks += [("h", at + 0.045), ("h", at), ("h", at - 0.045)]
        marks.append(1.0)
        if "ridges" not in _GAME_SPLIT:
            # (how many go in each gap, shared out once by the gaps' lengths where the body is widest, so that
            # every ring has the same in each)
            s = max((i / 200.0 for i in range(1, 200)), key=lambda q: BODY_SKIN.at(q)[2])
            free = GAME_MESH["up"] + GAME_MESH["down"] - (len(marks) - 1)
            side, whole = section.outline_at(s, marks, [0] * (len(marks) - 1))
            gaps = [side[k + 1][2] - side[k][2] for k in range(len(side) - 1)]
            # (the ridges' own gaps, a ridge's two sides, get nothing more)
            open_gaps = [k for k in range(len(gaps)) if k % 3 == 0]
            share = [0] * len(gaps)
            room = sum(gaps[k] for k in open_gaps)
            for _ in range(max(free, 0)):
                k = max(open_gaps, key=lambda q: gaps[q] / room / (share[q] + 1))
                share[k] += 1
            _GAME_SPLIT["ridges"] = share
        between = _GAME_SPLIT["ridges"]
    return lambda s: section.outline_at(s, marks, between)


def eye_middle():
    """Where the right eye's dome meets the skin, in metres (Godot axes): the shader's EYE_MID, about which it
    grows the cartoon eye."""
    s, y, ball, stands = EYE_AT
    return body_frame(s, y)[0] * LENGTH


def eye(low, game=False):
    """The right eye: a dome set in the side of the head."""
    part = Part("eye")
    s, y, ball, stands = EYE_AT
    at, out, up = body_frame(s, y)
    along = up.cross(out).normalized()
    seen = math.acos(1.0 - stands / ball)
    reach = min(seen * 1.3, 0.5 * math.pi)
    centre = at - out * (ball - stands)
    rows = 4 if low else 10
    around = 10 if low else 28
    if game:
        rows, around = GAME_MESH["eye"]
    rings = []
    colour = (EYE / 20.0, 0.0, 0.0)
    for i in range(rows + 1):
        a = reach * i / rows
        ring = []
        for k in range(around):
            q = TAU * k / around
            p = centre + out * (ball * math.cos(a)) + (up * math.cos(q) + along * math.sin(q)) * (ball * math.sin(a))
            # (UV: where it is on the eye's round face, seen straight on: its middle at (0.5, 0.5), up towards +x;
            # 0.5 away is where the eye meets the skin)
            across = 0.5 * math.sin(a) / math.sin(seen)
            ring.append(part.add(p, (0.5 + across * math.cos(q), 1.0 - (0.5 + across * math.sin(q))), (0.0, 1.0), colour))
        rings.append(ring)
    # (closed behind, inside the head)
    back = centre + out * (ball * math.cos(reach) - 0.4 * ball)
    rings.append([part.add(back, (0.5, 0.5), (0.0, 1.0), colour) for k in range(around)])
    part.loft(rings)
    return part


def outline_marks(points):
    """How far along outline_curve(points) (0..1) each of the points is."""
    pts = [Vector(p) for p in points]
    n = len(pts)
    dense = []
    for i in range(n - 1):
        p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, n - 1)]
        for k in range(20):
            t = k / 20.0
            dense.append(0.5 * ((2.0 * p1) + (p2 - p0) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t * t
                                + (3.0 * p1 - p0 - 3.0 * p2 + p3) * t ** 3))
    dense.append(pts[-1])
    acc = [0.0]
    for a, b in zip(dense, dense[1:]):
        acc.append(acc[-1] + (b - a).length)
    return [acc[20 * i] / acc[-1] for i in range(n)], acc[-1]


def game_columns(points, step):
    """The game model's columns along a fin's outline (0..1): one at every point of the outline, and more
    between where two points are further apart than `step` (body lengths)."""
    marks, whole = outline_marks(points)
    ts = [0.0]
    for a, b in zip(marks, marks[1:]):
        n = max(1, math.ceil((b - a) * whole / step - 0.25))
        ts += [lerp(a, b, k / n) for k in range(1, n + 1)]
    return ts


def outline_curve(points):
    """A smooth closed-ended line through points (Vectors), as a function of how far along it (0..1)."""
    pts = [Vector(p) for p in points]
    n = len(pts)
    dense = []
    for i in range(n - 1):
        p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, n - 1)]
        for k in range(20):
            t = k / 20.0
            dense.append(0.5 * ((2.0 * p1) + (p2 - p0) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t * t
                                + (3.0 * p1 - p0 - 3.0 * p2 + p3) * t ** 3))
    dense.append(pts[-1])
    acc = [0.0]
    for a, b in zip(dense, dense[1:]):
        acc.append(acc[-1] + (b - a).length)

    def f(t):
        want = acc[-1] * max(0.0, min(1.0, t))
        i = min(bisect.bisect_right(acc, want) - 1, len(dense) - 2)
        span = acc[i + 1] - acc[i]
        return dense[i].lerp(dense[i + 1], (want - acc[i]) / span if span > 1e-12 else 0.0)
    return f


def fin(name, kind, base0, base1, outline, normal, thick, low, tail=False, game=False):
    """A fin, a thick foil with no rays: its skin runs from its root line (base0 to base1, inside the body) out
    to its outline (a line from base0 round to base1); flat, facing `normal`; `thick` at its root, thinning to
    nothing at its edge. (The game model's columns: game_columns.)"""
    part = Part(name)
    cols = (14 if tail else 10) if low else (72 if tail else 44)
    rows = 2 if low else 9
    ts = [i / cols for i in range(cols + 1)]
    if game:
        ts = game_columns(outline, GAME_MESH["tail_step" if tail else "fin_step"])
        cols = len(ts) - 1
        rows = len(GAME_MESH["fin_rows"]) - 1
    normal = normal.normalized()
    edge = outline_curve(outline)
    left, right = [], []
    for i in range(cols + 1):
        t = ts[i]
        b, tip = base0.lerp(base1, t), edge(t)
        # (thickest a third of the way from its leading edge, as a wing is; the tail's root the same all along)
        foil = math.sin(math.pi * t) ** 0.5 if tail else min(1.0, 1.9 * t ** 0.5 * (1.0 - t) ** 0.8) ** 0.8
        if i in (0, cols):
            foil = 0.0
        a, c = [], []
        for j in range(rows + 1):
            r = (j / rows) ** 0.85
            if game:
                # (a row close to the edge, so that the edge's rounding stays a thin rim and does not shade
                # half the fin)
                r = GAME_MESH["fin_rows"][j]
            th = thick * foil * (1.0 - r) ** 0.75
            mid = b.lerp(tip, r)
            data = ((r, 1.0 - t), (0.0, 1.0), (kind / 20.0, 0.0, 0.0))
            a.append(part.add(mid + normal * (th * 0.5), *data))
            c.append(part.add(mid - normal * (th * 0.5), *data))
        left.append(a)
        right.append(c)
    for i in range(cols):
        for j in range(rows):
            for sheet in (left, right):
                a, b, c, d = sheet[i][j], sheet[i + 1][j], sheet[i + 1][j + 1], sheet[i][j + 1]
                # (at the two corners of its edge three of a face's corners have no thickness: cut it from
                # the fourth, so that no triangle lies flat between the fin's two sides)
                if j == rows - 1 and i == 0:
                    part.faces += [(a, b, d), (b, c, d)]
                elif j == rows - 1 and i == cols - 1:
                    part.faces += [(a, b, c), (a, c, d)]
                else:
                    part.faces.append((a, b, c, d))
        # (closed at the root, inside the body)
        part.faces.append((left[i][0], right[i][0], right[i + 1][0], left[i + 1][0]))
    return part


def fins(low, game=False):
    made = []
    side = Vector((1.0, 0.0, 0.0))
    for name, kind, s0, s1, way, points, thick in median_fins():
        line = BODY_SKIN.top if way > 0 else BODY_SKIN.bot
        sunk = 0.5 * min(abs(line(s0)), abs(line(s1)), 0.02)
        b0 = Vector((0.0, line(s0) - way * sunk, s0 - 0.5))
        b1 = Vector((0.0, line(s1) - way * sunk, s1 - 0.5))
        outline = [b0] + [Vector((0.0, line(s0) + way * v, s - 0.5)) for s, v in points] + [b1]
        made.append(fin(name, kind, b0, b1, outline, side, thick, low, game=game))
    outline = [Vector((0.0, y, s - 0.5)) for s, y in TAIL_OUTLINE]
    made.append(fin("tail", TAIL, outline[0], outline[-1], outline, side, TAIL_THICK, low, True, game=game))
    for name, kind, s0, s1, h0, h1, out, points, thick in PAIRED:
        def on_body(s, h):
            y = lerp(low_line(s), BODY_SKIN.top(s), h)
            return Vector((body_x(s, y) - 0.2 * thick - 0.004, y, s - 0.5))
        b0, b1 = on_body(s0, h0), on_body(s1, h1)
        along = (b1 - b0).normalized()
        out = Vector(out)
        out = (out - along * out.dot(along)).normalized()
        outline = [b0] + [b0 + along * u + out * v for u, v in points] + [b1]
        one = fin(name, kind, b0, b1, outline, along.cross(out), thick, low, game=game)
        made += [one, one.mirrored(name + "_left")]
    return made


def teeth(low, game=False):
    """The teeth: a row along the upper jaw (in the roof of the mouth) and a row along the lower jaw's lip, each
    a flattened point. With the mouth shut the upper ones are inside the lower jaw and the lower ones inside
    the head."""
    made = []
    if not TEETH:
        return made
    for kind, name, way in ((UPPER, "upper", -1.0), (LOWER, "lower", 1.0)):
        spec = TEETH[name]
        part = Part(name + "_teeth")
        s0 = MOUTH_S
        s1 = lerp(MOUTH_S, HINGE_S, spec["back"])
        line = []
        for i in range(201):
            s = s0 + (s1 - s0) * (i / 200.0) ** 2
            line.append((s, spec["inset"] * JAW_SKIN.at(s)[2]))
        acc = [0.0]
        for a, b in zip(line, line[1:]):
            acc.append(acc[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
        count = max(3, spec["count"] // 3) if low else spec["count"]
        grow = 3.0 if low else 1.0
        if game:
            count = max(3, round(spec["count"] * GAME_MESH["teeth"]))
            grow = 1.3
        for k in range(count):
            want = acc[-1] * (k + 0.5) / count
            i = min(bisect.bisect_right(acc, want) - 1, 199)
            s, x = line[i]
            ds, dx = line[i + 1][0] - s, line[i + 1][1] - x
            # (smaller towards the corners of the mouth)
            size = 1.0 - 0.55 * (want / acc[-1]) ** 1.6
            long = spec["long"] * size
            wide = min(spec["wide"] * size * (grow if low or game else 1.0), 0.96 * acc[-1] / count)
            goes = smooth(MOUTH_S - 0.03, MOUTH_S + 0.002, s) * smooth(HINGE_S + 0.008, HINGE_S - 0.03, s) if kind == UPPER else 0.0
            for sign in (1.0, -1.0):
                along = Vector((sign * dx, 0.0, ds)).normalized()
                outward = Vector((along.z, 0.0, -along.x)) * sign
                if kind == UPPER:
                    root = Vector((sign * x, BODY_SKIN.y_at(s, x, False) + 0.15 * long, s - 0.5))
                else:
                    root = Vector((sign * x, JAW_SKIN.y_at(s, x, True) - 0.15 * long, s - 0.5))
                # (leaning back into the mouth a little)
                tip = root + Vector((0.0, way * long * 1.15, 0.0)) - outward * (0.12 * long) + Vector((0.0, 0.0, 0.1 * long))
                colour = (kind / 20.0, goes, 0.0)
                corners = [root + along * (0.5 * wide), root + outward * (0.17 * wide), root - along * (0.5 * wide),
                           root - outward * (0.17 * wide)]
                if low or game:
                    corners = [corners[0], corners[1], corners[2]]
                base = [part.add(p, (0.0, 1.0), (0.0, 1.0), colour) for p in corners]
                top = part.add(tip, (1.0, 1.0), (0.0, 1.0), colour)
                for j in range(len(base)):
                    part.faces.append((base[j], base[(j + 1) % len(base)], top))
                part.faces.append(tuple(base))
        made.append(part)
    return made





def cheeks(low, game=False):
    """The cheeks: a thin fold each side between the roof of the mouth and the lower jaw's edge, from CHEEK_FROM
    back to the hinge. Shut, it is folded away inside the head and the jaw; the shader swings its lower edge down
    with the jaw (UV.x: 0 its top edge, which stays with the head, 1 its lower edge, which goes with the jaw), so
    that an open mouth is closed at its sides as a real one is and only open at the front."""
    part = Part("cheek")
    s0 = lerp(MOUTH_S, HINGE_S, CHEEK_FROM)
    s1 = HINGE_S + 0.003
    cols = 5 if low else 22
    rows = 1 if low else 5
    if game:
        cols, rows = GAME_MESH["cheek"]
    thick = 0.0012
    outer, inner = [], []
    for i in range(cols + 1):
        s = lerp(s0, s1, i / cols)
        x = 0.9 * JAW_SKIN.at(min(s, JAW_SKIN.last))[2]
        top = BODY_SKIN.y_at(s, x, False) + 0.003
        bottom = min(JAW_SKIN.y_at(s, x, True) - 0.003, top - 0.002)
        a, b = [], []
        for j in range(rows + 1):
            w = j / rows
            y = lerp(top, bottom, w)
            colour = (CHEEK / 20.0, upper_goes(s) * upper_arc(s, x) * (1.0 - w), 0.0)
            data = ((w, 1.0 - (i / cols)), (0.0, 1.0), colour)
            a.append(part.add((x, y, s - 0.5), *data))
            b.append(part.add((x - thick, y, s - 0.5), *data))
        outer.append(a)
        inner.append(b)
    for i in range(cols):
        for j in range(rows):
            part.faces.append((outer[i][j], outer[i + 1][j], outer[i + 1][j + 1], outer[i][j + 1]))
            part.faces.append((inner[i][j], inner[i][j + 1], inner[i + 1][j + 1], inner[i + 1][j]))
        part.faces.append((outer[i][0], inner[i][0], inner[i + 1][0], outer[i + 1][0]))
        part.faces.append((outer[i][rows], outer[i + 1][rows], inner[i + 1][rows], inner[i][rows]))
    for j in range(rows):
        part.faces.append((outer[0][j], outer[0][j + 1], inner[0][j + 1], inner[0][j]))
        part.faces.append((outer[cols][j], inner[cols][j], inner[cols][j + 1], outer[cols][j + 1]))
    return [part, part.mirrored("cheek_left")]


# ---------------------------------------------------------------------------------------------------------------
# The gills (added 2026-11-18). The user: "The fish need modeled gills as well, well for relevant fish, so like when
# it opens its mouth wide you can see them".
# How many: (points along an arch, sides round its bar, rakers on it; points up a slit's flap, across it).
GILL_MESH = {"full": (10, 6, 5, 8, 3), "game": (4, 3, 2, 3, 1), "low": (3, 3, 0, 2, 1)}
# The arches: how many a side, from how far and to how far between the front of the mouth (0) and the hinge (1), the
# bar's radius, how deep the fringe of filaments behind it is, how long a raker (body lengths).
GILL_ARCHES = (4, 0.58, 0.86, 0.0012, 0.0030, 0.0022)
# The slits' flaps: how far under the skin they lie with the mouth shut, how thick, how far back from the slit line
# (as a share of the step between slits).
SLIT_FLAP = (0.0045, 0.0006, 0.55)


def blade(part, grid, thick):
    """A thin closed blade over a grid of places: grid[i][j] = (middle, the way its faces face, data); its two sheets
    `thick` apart, closed round its edge."""
    ni, nj = len(grid), len(grid[0])
    a = [[part.add(m + n * (0.5 * thick), *d) for m, n, d in row] for row in grid]
    b = [[part.add(m - n * (0.5 * thick), *d) for m, n, d in row] for row in grid]
    for i in range(ni - 1):
        for j in range(nj - 1):
            part.faces.append((a[i][j], a[i + 1][j], a[i + 1][j + 1], a[i][j + 1]))
            part.faces.append((b[i][j], b[i][j + 1], b[i + 1][j + 1], b[i + 1][j]))
    ring = [(i, 0) for i in range(ni)] + [(ni - 1, j) for j in range(1, nj)] \
        + [(i, nj - 1) for i in range(ni - 2, -1, -1)] + [(0, j) for j in range(nj - 2, 0, -1)]
    for k in range(len(ring)):
        p, q = ring[k], ring[(k + 1) % len(ring)]
        part.faces.append((a[p[0]][p[1]], b[p[0]][p[1]], b[q[0]][q[1]], a[q[0]][q[1]]))


def gills(level):
    """The gill arches, right side and left: GILL_ARCHES[0] a side across the back of the mouth, each a curved bar
    from the roof of the mouth down the side of the throat to the floor, a fringe of filaments behind it and pale
    rakers in front. With the mouth shut each is folded flat inside the head and the jaw, between the roof of the mouth
    and the jaw's lip; the shader swings its lower end down with the jaw as it does a cheek's (UV.x: 0 its top, which
    stays with the head, 1 its foot, which goes with the jaw), so that the open mouth shows them standing across the
    throat. What a point is: UV.y which arch (0 the front one, 1 the back one); COLOR.g as a cheek's; COLOR.b what
    of it (1 filaments, 0.5 the bar, 0 a raker); UV2.x along the arch (0 top, 1 foot)."""
    along, sides, rakers = GILL_MESH[level][:3]
    count, f0, f1, radius, fringe, raker = GILL_ARCHES
    bars, fringes, combs = Part("gill_bars"), Part("gill_filaments"), Part("gill_rakers")
    for k in range(count):
        s = lerp(lerp(MOUTH_S, HINGE_S, f0), lerp(MOUTH_S, HINGE_S, f1), k / max(count - 1, 1))
        wide = JAW_SKIN.at(s)[2]
        # (thinner where the jaw is shallow, so that the folded arch's two legs do not run into each other)
        x_end = wide * 0.36
        thick = min(radius, 0.12 * (BODY_SKIN.y_at(s, x_end, False) + 0.004 - lerp(BODY_SKIN.y_at(s, x_end, False), JAW_SKIN.y_at(s, x_end, False), 0.75)))

        def place(w):
            x = wide * (0.36 + 0.32 * math.sin(math.pi * w))
            roof = BODY_SKIN.y_at(s, x, False)
            # (from just up inside the head to well down inside the jaw: the arch's two ends are hidden in them
            # whether the mouth is open or shut)
            floor = roof - 0.75 * (roof - JAW_SKIN.y_at(s, x, False))
            return Vector((x, lerp(roof + 0.004, floor, w), s - 0.5))

        def data(w, kind):
            # (the upper lip lifts most in the middle: the arch's top goes with it as the roof there does)
            return ((w, 1.0 - k / max(count - 1, 1)), (w, 1.0),
                    (GILL / 20.0, upper_goes(s) * upper_arc(s, place(w).x) * (1.0 - w), kind))

        line = [(i / along, place(i / along)) for i in range(along + 1)]
        back = Vector((0.0, 0.0, 1.0))
        rings = []
        grid = []
        for i, (w, p) in enumerate(line):
            ahead = line[min(i + 1, along)][1] - line[max(i - 1, 0)][1]
            ahead.normalize()
            n1 = (back - ahead * back.dot(ahead)).normalized()
            n2 = ahead.cross(n1).normalized()
            rings.append([bars.add(p + (n1 * math.cos(TAU * q / sides) + n2 * math.sin(TAU * q / sides)) * thick,
                                   *data(w, 0.5)) for q in range(sides)])
            # (the filaments: a thin fringe behind the bar, shorter at the arch's ends; the shader stripes it)
            deep = fringe * (0.55 + 0.45 * math.sin(math.pi * w))
            grid.append([(p + n1 * (thick * 0.6 + deep * t), n2, data(w, 1.0)) for t in (0.0, 1.0)])
        bars.loft(rings)
        # (closed at each end)
        for ring_ in (rings[0], rings[-1]):
            middle = bars.add(sum((bars.verts[v] for v in ring_), Vector()) / sides, *bars.data[ring_[0]])
            for q in range(sides):
                bars.faces.append((ring_[q], ring_[(q + 1) % sides], middle))
        blade(fringes, grid, 0.0008)
        # (the rakers: short pale points on the bar's front, pointing forward into the mouth)
        for r in range(rakers):
            w = (r + 0.5) / rakers
            p = place(w)
            ahead = (place(min(w + 0.01, 1.0)) - place(max(w - 0.01, 0.0))).normalized()
            n1 = (back - ahead * back.dot(ahead)).normalized()
            n2 = ahead.cross(n1).normalized()
            root = p - n1 * (thick * 0.7)
            base = [combs.add(root + n2 * (thick * 0.6), *data(w, 0.0)),
                    combs.add(root + ahead * (thick * 0.7), *data(w, 0.0)),
                    combs.add(root - ahead * (thick * 0.7), *data(w, 0.0))]
            tip = combs.add(root - n1 * raker, *data(w, 0.0))
            for j in range(3):
                combs.faces.append((base[j], base[(j + 1) % 3], tip))
            combs.faces.append(tuple(base))
    made = [bars, fringes] + ([combs] if rakers else [])
    return made + [p.mirrored(p.name + "_left") for p in made]


def slits(level):
    """The five gill slits' flaps, right side and left: a thin blade behind each slit line the shader draws, lying
    SLIT_FLAP[0] under the skin with the mouth shut (unseen); the shader lifts its front edge out through the skin as
    the mouth opens, so that each slit stands open a little with red showing in it. A point has the body's UV and UV2
    (so the shader draws the skin on it as on the body there), and COLOR.b how far it lifts (1 its front edge, which
    is red, 0 its back edge, which stays under the skin)."""
    up, across = GILL_MESH[level][3:]
    at0, step, top0, top_drop, lean_k, bow_k, h0, h_step = SLIT_LINE
    under, thick, wide = SLIT_FLAP
    made = []
    for i in range(5):
        # (each a part of its own, checked by itself)
        part = Part("slit%d" % (i + 1))
        at = at0 + step * i
        top = top0 - top_drop * i * i / 4.0 - 0.015
        low = h0 + h_step * i

        def lean(h):
            return at + lean_k * (h - 0.5) - bow_k * (h - 0.48) ** 2

        grid = []
        for j in range(up + 1):
            h = lerp(low, top, j / up)
            row = []
            for u in range(across + 1):
                f = u / across
                s = lean(h) - 0.0008 + (wide * step + 0.0008) * f
                low_s = low_line(s)
                y = low_s + h * (BODY_SKIN.top(s) - low_s)
                # (on the skin without its ridges, which lies under them: a flap bent over a ridge folds)
                p, n, _ = body_frame(s, y, True)
                side, whole = BODY_SKIN.outline_at(s, [0.0, ("h", h), 1.0], [0, 0])
                data = ((s, 1.0 - h), (side[1][2] * LENGTH, 1.0 - whole * LENGTH), (SLIT / 20.0, 0.0, 1.0 - f))
                row.append((p - n * under, n, data))
            grid.append(row)
        # (its two sheets apart along one way, the slit's mean way out: apart along each point's own way out, the
        # sheets of a flap bent round the body cross each other where its rows are few)
        way = sum((n for row in grid for _, n, _ in row), Vector()).normalized()
        grid = [[(m, way, d) for m, _, d in row] for row in grid]
        blade(part, grid, thick)
        made += [part, part.mirrored(part.name + "_left")]
    return made


def make(name, low, game=False):
    parts = []
    body = Part("body")
    if game:
        places = game_places()
        skin(body, BODY_SKIN, places, 0, BODY, game_side(BODY_SKIN, BODY))
    else:
        skin(body, BODY_SKIN, body_places(low), BODY_MESH["half"][1 if low else 0], BODY)
    parts.append(body)
    jaw = Part("jaw")
    jaw_rings = 12 if low else 40
    if game:
        # (the jaw's rings where the body's are, so that the lip and the roof of the mouth run together)
        skin(jaw, JAW_SKIN, [JAW_SKIN.first] + [p for p in places if JAW_SKIN.first < p < JAW_SKIN.last]
             + [JAW_SKIN.last], 0, JAW, game_side(JAW_SKIN, JAW))
    else:
        skin(jaw, JAW_SKIN, [lerp(JAW_SKIN.first, JAW_SKIN.last, (i / jaw_rings) ** 1.25) for i in range(jaw_rings + 1)],
             5 if low else 14, JAW)
    parts.append(jaw)
    ball = eye(low, game)
    parts += [ball, ball.mirrored("eye_left")]
    parts += teeth(low, game)
    parts += cheeks(low, game)
    parts += fins(low, game)
    # (the gills last: on the full model they are a second surface, so that the first is as it was)
    level = "game" if game else ("low" if low else "full")
    gill_parts = gills(level) + slits(level)
    parts += gill_parts

    verts, faces, corners = [], [], []
    told = []
    wrong_all = 0
    for part in parts:
        out, wrong, counted = part.done()
        told.append("%s %d/%d wrong" % (part.name, wrong, counted))
        wrong_all += wrong
        if part is gill_parts[0]:
            gill_from = len(faces)
        for face in out:
            first = len(verts)
            for co, uv, uv2, colour in face:
                verts.append(co)
                corners.append((uv, uv2, colour))
            faces.append(list(range(first, first + len(face))))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    # (every layer made first, then each looked up by name: making one moves the others)
    mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.new(name="UV2")
    mesh.color_attributes.new(name="Color", type="FLOAT_COLOR", domain="CORNER")
    uv = mesh.uv_layers["UVMap"].data
    uv2 = mesh.uv_layers["UV2"].data
    colour = mesh.color_attributes["Color"].data
    for poly in mesh.polygons:
        for corner, vi in enumerate(poly.vertices):
            d = corners[vi]
            uv[poly.loop_start + corner].uv = d[0]
            uv2[poly.loop_start + corner].uv = d[1]
            colour[poly.loop_start + corner].color = (d[2][0], d[2][1], d[2][2], 1.0)
    mesh.color_attributes.active_color = mesh.color_attributes["Color"]
    mesh.color_attributes.render_color_index = mesh.color_attributes.find("Color")
    material = bpy.data.materials.get("shark") or bpy.data.materials.new("shark")
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.55, 0.6, 0.66, 1.0)
    material.diffuse_color = (0.55, 0.6, 0.66, 1.0)
    mesh.materials.append(material)
    if level == "full":
        second = bpy.data.materials.get("shark_gills") or bpy.data.materials.new("shark_gills")
        second.diffuse_color = (0.6, 0.1, 0.1, 1.0)
        mesh.materials.append(second)
        for poly in mesh.polygons[gill_from:]:
            poly.material_index = 1
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.update()
    # (every face was made with corners of its own; the same point with the same data is one point again)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-7)
    bpy.ops.object.mode_set(mode="OBJECT")
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    xs = [v.co.x for v in mesh.vertices]
    ys = [v.co.y for v in mesh.vertices]
    zs = [v.co.z for v in mesh.vertices]
    print("BUILT %s verts=%d tris=%d" % (name, len(mesh.vertices), tris))
    print("BOX %s (Godot axes): x %.3f..%.3f  y %.3f..%.3f  z %.3f..%.3f" % (
        name, min(xs), max(xs), min(zs), max(zs), -max(ys), -min(ys)))
    print("WINDING %s: %s: %s" % (name, "ok" if wrong_all == 0 else "INSIDE OUT", ", ".join(told)))
    return obj


def export_one(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", export_yup=True, use_selection=True,
        export_animations=False, export_vertex_color="ACTIVE", export_texcoords=True,
    )


def render(folder, made):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_cavity = True
    scene.render.resolution_x, scene.render.resolution_y = 1400, 800
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    # (Blender space: the nose is towards +Y, up is +Z; the views are laid out for a fish 1 long)
    views = [("right", (1, 0, 0), (0, 0, 0), 1.15), ("left", (-1, 0, 0), (0, 0, 0), 1.15),
             ("top", (0, -0.001, 1), (0, 0, 0), 1.15), ("under", (0, 0.001, -1), (0, 0, 0), 1.15),
             ("front", (0, 1, 0), (0, 0, 0), 0.6), ("back", (0, -1, 0), (0, 0, 0), 0.6),
             ("quarter", (0.7, 0.6, 0.35), (0, 0, 0), 1.1), ("low_quarter", (0.6, 0.6, -0.5), (0, 0, 0), 1.1),
             ("head", (1, 0.15, 0.05), (0, 0.36, 0), 0.4), ("head_under", (0.5, 0.5, -0.7), (0, 0.38, -0.02), 0.4),
             ("tail", (1, -0.2, 0.1), (0, -0.36, 0), 0.5)]
    for prefix, obj in zip(("", "lo_", "game_"), made):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if prefix == "lo_" and view not in ("right", "quarter"):
                continue
            offset = Vector(direction).normalized() * 10.0 * LENGTH
            camera.data.ortho_scale = frame * LENGTH
            camera.location = Vector(target) * LENGTH + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "X" if view in ("top", "under") else "Y").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % (prefix, view))
            bpy.ops.render.render(write_still=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    depth = max(BODY_SKIN.top(i / 400.0) - low_line(i / 400.0) for i in range(400))
    width = 2.0 * max(BODY_SKIN.at(i / 400.0)[2] for i in range(400))
    print("SHAPE %s: length=%.2f depth=%.3f width=%.3f hinge_s=%.4f hinge_y=%.4f mouth_s=%.4f" % (
        NAME, LENGTH, depth * LENGTH, width * LENGTH, HINGE_S, HINGE_Y, MOUTH_S))
    full = make(NAME, False)
    low = make(NAME + "_lo", True)
    game = make(NAME + "_game", False, True)
    mid = eye_middle()
    print("EYE_MID %s: vec3(%.4f, %.4f, %.4f)" % (NAME, mid.x, mid.y, mid.z))
    export_one(full, os.path.join(OUT, NAME + ".glb"))
    export_one(low, os.path.join(OUT, NAME + "_lo.glb"))
    export_one(game, os.path.join(OUT, NAME + "_game.glb"))
    low.location.x = LENGTH * 0.8
    game.location.x = -LENGTH * 0.8
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, NAME + ".blend"))
    low.location.x = 0.0
    game.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low, game])


if __name__ == "__main__":
    main()
