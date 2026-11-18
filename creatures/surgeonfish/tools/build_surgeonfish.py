"""Builds the surgeonfish (creatures/surgeonfish) and exports them for Godot.

Run from the game's root:
    blender --background --python creatures/surgeonfish/tools/build_surgeonfish.py
    blender --background --python creatures/surgeonfish/tools/build_surgeonfish.py -- <preview folder>   # with pictures
    blender --background --python creatures/surgeonfish/tools/build_surgeonfish.py -- <preview folder> convict   # only these

One shape for each kind (KINDS: yellow_tang, powder_blue, convict). For each it writes
creatures/surgeonfish/models/surgeonfish_<kind>.glb (the full model) and surgeonfish_<kind>_lo.glb (far off, phones,
many), and the editable creatures/surgeonfish/tools/surgeonfish_<kind>.blend (this folder has a .gdignore). Each
model is one still mesh with one surface: the shader (surgeonfish.gdshader) bends it to swim, opens its mouth, rows
its pectoral fins and draws every marking. It prints a WINDING line for each model: the check that nothing is
inside out (a ray out of every triangle of every closed part must leave that part an even number of times).

Every kind is built 0.25 m long from snout to tail tip (Surgeonfish.LENGTH), nose towards -Z, belly down, its
origin on the line through snout and tail half way along. The parts, each a closed solid:

- THE BODY: a tall oval disc, flattened from side to side, from the end of the snout to the root of the tail; the
  upper head and snout ahead of the jaw's hinge are its front, flat underneath (the roof of the mouth).
- THE LOWER JAW: a small part of its own under the snout's tip, which the shader swings down about its hinge at the
  corner of the mouth; its top is the floor of the mouth, and behind the hinge it runs back into the throat.
- EYES: domes set high in the sides of the head.
- THE SPINE: the "scalpel" on each side of the tail's wrist, a blade lying in a groove, its point forward.
- THE FINS: thin closed blades, thick at the root and fine at the edge: the long dorsal and anal fins (tall and
  sail-like in the yellow tang), the tail, and a pair each of pelvic and pectoral fins.

What a point is, for the shader: vertex colour red the part, as a tenth (0 body, 0.1 lower jaw, 0.2 eye, 0.3 spine,
0.4 dorsal, 0.6 tail, 0.7 anal, 0.8 pelvic, 0.9 pectoral). On the body and the jaw: UV.x how far along the fish (0
snout to 1 tail tip), UV.y how high on the head and body (0 the lowest line there, chin or belly, to 1 the back
line); UV2.x how far round the skin from the back line (metres, + on +X, - on -X), UV2.y the whole way round from
back line to belly line there (metres); blue how much it is the inside of the mouth. On an eye: UV where a point is
on its round face seen straight on (its middle at 0.5, 0.5; its rim 0.5 away). On the spine: UV.x along it (0 its
point). On a fin: UV.x along its rays (0 root to 1 edge), UV.y across it counted in rays (0 its leading edge),
green how far across it (0 leading edge to 1 trailing edge); UV2 and blue the way its flat side faces (x, y, and z
as z / 2 + 0.5), which is the way the shader waves it. (The glTF writer flips V: what is written here is 1 - v,
so that Godot reads v.)

Everything here is worked out in body lengths in Godot space (Y up, nose towards -Z) and written out in metres.
The numbers the shader and the script share (LENGTH, the jaw's hinge, the gill cover's edge) are printed by
`use` (a SHAPE line) and kept in step with surgeonfish.gd by hand.
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
NAME = "surgeonfish"

# Kept in step with surgeonfish.gd and surgeonfish.gdshader.
LENGTH = 0.25
TAU = math.tau
BODY, JAW, EYE, SPINE, DORSAL, TAIL, ANAL, PELVIC, PECTORAL = 0, 1, 2, 3, 4, 6, 7, 8, 9


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

    def outline(self, s, half, bend=0.0):
        """half + 1 points down its +X side from the top line to the bottom line, evenly spaced along the
        skin: (x, y, how far round from the top). With `bend` (0..1, the game model) they are spaced partly by
        how much the skin turns, so that more of them go round the tight curves of the back and belly."""
        if bend > 0.0:
            return self.outline_bent(s, half, bend)
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

    def outline_bent(self, s, half, bend):
        """`outline` for the game model: the points spaced by a mix of the length of skin and how far it turns
        between them; each still says its true distance round from the top."""
        top, bot, hw, ycf, nt, nb = self.at(s)
        yc = bot + ycf * (top - bot)
        steps = 400
        dense = []
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
        turned = [0.0]
        heading = None
        for i in range(steps):
            dx, dy = dense[i + 1][0] - dense[i][0], dense[i + 1][1] - dense[i][1]
            acc.append(acc[-1] + math.hypot(dx, dy))
            now = math.atan2(dy, dx)
            # (from the middle line, the skin first heads straight out)
            was = heading if heading is not None else 0.0
            turned.append(turned[-1] + abs(math.atan2(math.sin(now - was), math.cos(now - was))))
            heading = now
        whole = acc[-1]
        if whole < 1e-9:
            return [(0.0, lerp(top, bot, j / half), 0.0) for j in range(half + 1)], whole
        measure = [(1.0 - bend) * a / whole + bend * t / max(turned[-1], 1e-9) for a, t in zip(acc, turned)]
        out = []
        for j in range(half + 1):
            want = j / half
            i = min(bisect.bisect_right(measure, want) - 1, steps - 1)
            span = measure[i + 1] - measure[i]
            t = (want - measure[i]) / span if span > 1e-12 else 0.0
            out.append((lerp(dense[i][0], dense[i + 1][0], t), lerp(dense[i][1], dense[i + 1][1], t),
                        lerp(acc[i], acc[i + 1], t)))
        out[0] = (0.0, top, 0.0)
        out[-1] = (0.0, bot, whole)
        # (the point nearest the widest place is moved onto it, so that the width seen from above and the
        # front is kept)
        middle = steps // 2
        j = min(range(1, half), key=lambda k: abs(k / half - measure[middle]))
        out[j] = (dense[middle][0], dense[middle][1], acc[middle])
        return out, whole


def adaptive(f, n, lo, hi, fixed=(), most=None):
    """n + 1 places from lo to hi (the game model's rings, a fin's rays) where straight lines between them follow
    f(place), a tuple of lengths, most closely: each one added where the line is furthest off, and between any two
    more than `most` apart first."""
    steps = 400
    grid = [lerp(lo, hi, i / steps) for i in range(steps + 1)]
    values = [f(x) for x in grid]
    chosen = sorted(set([0, steps] + [max(0, min(steps, round((x - lo) / (hi - lo) * steps))) for x in fixed]))
    while len(chosen) < n + 1:
        best, at = -1.0, None
        for a, b in zip(chosen, chosen[1:]):
            if b - a < 2:
                continue
            if most and grid[b] - grid[a] > most:
                score, k_at = 10.0 + grid[b] - grid[a], (a + b) // 2
            else:
                score, k_at = -1.0, None
                for k in range(a + 1, b):
                    t = (k - a) / (b - a)
                    off = max(abs(values[k][c] - lerp(values[a][c], values[b][c], t)) for c in range(len(values[k])))
                    if off > score:
                        score, k_at = off, k
            if score > best:
                best, at = score, k_at
        if at is None:
            break
        chosen.append(at)
        chosen.sort()
    return [grid[k] for k in chosen]


LIP = None

# The yellow tang (Zebrasoma flavescens): a tall disc, the forehead sloping steeply down to a long pointed snout
# with a small mouth at its end; very tall, sail-like dorsal and anal fins; a short tail wrist with its spine.
# Rows: s, top, bottom, half width, widest at (0 bottom .. 1 top), boxiness above, below.
ZEBRASOMA_BODY = [
    (0.000, 0.006, -0.002, 0.000, 0.50, 2.0, 2.0),
    (0.006, 0.014, -0.004, 0.0075, 0.50, 2.0, 2.2),
    (0.018, 0.022, -0.005, 0.0115, 0.48, 2.0, 2.6),
    (0.034, 0.033, -0.006, 0.0145, 0.45, 2.0, 2.9),
    (0.050, 0.047, -0.008, 0.0175, 0.42, 2.0, 3.0),
    (0.068, 0.068, -0.034, 0.022, 0.45, 2.1, 2.4),
    (0.095, 0.109, -0.068, 0.028, 0.48, 2.1, 2.2),
    (0.135, 0.159, -0.106, 0.034, 0.50, 2.1, 2.1),
    (0.185, 0.205, -0.143, 0.039, 0.52, 2.1, 2.1),
    (0.250, 0.240, -0.176, 0.042, 0.52, 2.15, 2.15),
    (0.330, 0.254, -0.195, 0.043, 0.52, 2.15, 2.15),
    (0.420, 0.247, -0.196, 0.041, 0.52, 2.15, 2.15),
    (0.510, 0.217, -0.176, 0.037, 0.52, 2.15, 2.15),
    (0.600, 0.170, -0.140, 0.031, 0.52, 2.1, 2.1),
    (0.680, 0.117, -0.098, 0.024, 0.52, 2.0, 2.0),
    (0.750, 0.068, -0.058, 0.0165, 0.52, 2.0, 2.0),
    (0.795, 0.049, -0.043, 0.0125, 0.52, 2.0, 2.0),
    (0.818, 0.049, -0.045, 0.0085, 0.50, 2.0, 2.0),
    (0.836, 0.055, -0.052, 0.0040, 0.50, 2.0, 2.0),
    (0.846, 0.044, -0.042, 0.0012, 0.50, 2.0, 2.0),
    (0.850, 0.030, -0.029, 0.000, 0.50, 2.0, 2.0),
]
ZEBRASOMA_JAW = [
    (0.003, -0.002, -0.006, 0.000, 0.75, 3.5, 2.0),
    (0.007, LIP, -0.010, 0.0065, 0.75, 3.5, 2.0),
    (0.018, LIP, -0.014, 0.0095, 0.78, 3.5, 2.0),
    (0.032, LIP, -0.018, 0.0120, 0.80, 3.5, 2.0),
    (0.048, LIP, -0.024, 0.0145, 0.80, 3.0, 2.0),
    (0.062, -0.022, -0.033, 0.0130, 0.70, 2.4, 2.1),
    (0.073, -0.032, -0.039, 0.0085, 0.60, 2.2, 2.1),
    (0.080, -0.0385, -0.0415, 0.0035, 0.50, 2.0, 2.0),
    (0.083, -0.0400, -0.0408, 0.000, 0.50, 2.0, 2.0),
]
# The powder blue and the convict surgeonfish (Acanthurus): an oval, a little less deep, the forehead rounder and
# the snout shorter and blunter; their dorsal and anal fins low and long.
ACANTHURUS_BODY = [
    (0.000, 0.008, -0.002, 0.000, 0.50, 2.0, 2.0),
    (0.006, 0.019, -0.004, 0.009, 0.50, 2.0, 2.2),
    (0.016, 0.030, -0.005, 0.0135, 0.48, 2.0, 2.6),
    (0.028, 0.043, -0.006, 0.017, 0.45, 2.0, 2.9),
    (0.040, 0.057, -0.008, 0.0195, 0.42, 2.0, 3.0),
    (0.058, 0.080, -0.038, 0.024, 0.45, 2.1, 2.4),
    (0.085, 0.112, -0.070, 0.030, 0.48, 2.1, 2.2),
    (0.125, 0.150, -0.104, 0.036, 0.50, 2.1, 2.1),
    (0.180, 0.184, -0.134, 0.041, 0.52, 2.15, 2.15),
    (0.250, 0.205, -0.158, 0.044, 0.52, 2.15, 2.15),
    (0.330, 0.212, -0.168, 0.044, 0.52, 2.15, 2.15),
    (0.420, 0.204, -0.164, 0.042, 0.52, 2.15, 2.15),
    (0.510, 0.180, -0.146, 0.038, 0.52, 2.15, 2.15),
    (0.600, 0.143, -0.117, 0.032, 0.52, 2.1, 2.1),
    (0.680, 0.100, -0.083, 0.025, 0.52, 2.0, 2.0),
    (0.750, 0.060, -0.051, 0.017, 0.52, 2.0, 2.0),
    (0.795, 0.044, -0.039, 0.0128, 0.52, 2.0, 2.0),
    (0.818, 0.048, -0.044, 0.0088, 0.50, 2.0, 2.0),
    (0.836, 0.055, -0.051, 0.0040, 0.50, 2.0, 2.0),
    (0.846, 0.044, -0.041, 0.0012, 0.50, 2.0, 2.0),
    (0.850, 0.030, -0.028, 0.000, 0.50, 2.0, 2.0),
]
ACANTHURUS_JAW = [
    (0.003, -0.002, -0.007, 0.000, 0.75, 3.5, 2.0),
    (0.007, LIP, -0.011, 0.0075, 0.75, 3.5, 2.0),
    (0.016, LIP, -0.016, 0.011, 0.78, 3.5, 2.0),
    (0.027, LIP, -0.021, 0.014, 0.80, 3.5, 2.0),
    (0.040, LIP, -0.027, 0.0165, 0.80, 3.0, 2.0),
    (0.053, -0.024, -0.036, 0.0150, 0.70, 2.4, 2.1),
    (0.064, -0.035, -0.043, 0.0095, 0.60, 2.2, 2.1),
    (0.071, -0.0415, -0.0455, 0.004, 0.50, 2.0, 2.0),
    (0.074, -0.0432, -0.0442, 0.000, 0.50, 2.0, 2.0),
]

# Each kind. The jaw's hinge (how far along, how high); the gill cover's rear edge (how far along, drawn by the
# shader); the eye (along, up, the eyeball's radius, how far it stands out of the head, how much of the dome's
# width shows); the fins: dorsal and anal (from, to along the fish, their height at points across them, the rake
# of their rays in degrees from straight back, the rays drawn), the tail (where its root is, how far up and down
# its root reaches, its middle rays, its longest, how sharp its corners, how far its rays spread in degrees), the
# pectorals (along, the top and bottom of their root, their longest ray, their shortest), the pelvics (along,
# longest ray), the spine (along, up, long).
KINDS = {
    "yellow_tang": {
        "body": ZEBRASOMA_BODY, "jaw": ZEBRASOMA_JAW, "hinge": (0.05, -0.007), "gill_s": 0.245,
        "eye": (0.150, 0.072, 0.030, 0.0105, 0.75),
        "dorsal": (0.175, 0.815, [(0.0, 0.04), (0.1, 0.1), (0.35, 0.17), (0.62, 0.19), (0.84, 0.145), (1.0, 0.035)],
                   [(0.0, 80.0), (0.5, 62.0), (1.0, 22.0)], 28),
        "anal": (0.40, 0.815, [(0.0, 0.035), (0.15, 0.1), (0.45, 0.16), (0.75, 0.145), (1.0, 0.03)],
                 [(0.0, 76.0), (0.5, 58.0), (1.0, 22.0)], 22),
        "tail": (0.832, 0.052, 0.155, 0.168, 2.0, 30.0),
        "pectoral": (0.262, -0.002, -0.05, 0.165, 0.085), "pelvic": (0.27, 0.07),
        "spine": (0.772, 0.004, 0.032),
    },
    "powder_blue": {
        "body": ACANTHURUS_BODY, "jaw": ACANTHURUS_JAW, "hinge": (0.04, -0.007), "gill_s": 0.235,
        "eye": (0.135, 0.072, 0.027, 0.0095, 0.75),
        "dorsal": (0.175, 0.815, [(0.0, 0.03), (0.1, 0.06), (0.5, 0.075), (0.85, 0.078), (1.0, 0.03)],
                   [(0.0, 78.0), (0.5, 55.0), (1.0, 22.0)], 37),
        "anal": (0.42, 0.815, [(0.0, 0.03), (0.15, 0.06), (0.6, 0.072), (0.88, 0.07), (1.0, 0.03)],
                 [(0.0, 74.0), (0.5, 52.0), (1.0, 22.0)], 31),
        "tail": (0.832, 0.05, 0.13, 0.175, 1.6, 31.0),
        "pectoral": (0.255, -0.004, -0.05, 0.155, 0.08), "pelvic": (0.27, 0.07),
        "spine": (0.772, 0.003, 0.03),
    },
    "convict": {
        "body": ACANTHURUS_BODY, "jaw": ACANTHURUS_JAW, "hinge": (0.04, -0.007), "gill_s": 0.235,
        "eye": (0.135, 0.072, 0.028, 0.0098, 0.75),
        "dorsal": (0.175, 0.815, [(0.0, 0.03), (0.1, 0.055), (0.5, 0.07), (0.85, 0.072), (1.0, 0.03)],
                   [(0.0, 78.0), (0.5, 55.0), (1.0, 22.0)], 31),
        "anal": (0.42, 0.815, [(0.0, 0.03), (0.15, 0.055), (0.6, 0.068), (0.88, 0.066), (1.0, 0.03)],
                 [(0.0, 74.0), (0.5, 52.0), (1.0, 22.0)], 25),
        "tail": (0.832, 0.05, 0.145, 0.165, 2.0, 30.0),
        "pectoral": (0.255, -0.004, -0.05, 0.15, 0.08), "pelvic": (0.27, 0.07),
        "spine": (0.774, 0.003, 0.022),
    },
}
WANTED = [name for name in ARGS[1:] if name in KINDS] or list(KINDS)

# The kind being built (set by `use`).
P = {}
BODY_SKIN = None
JAW_SKIN = None
HINGE_S = 0.0
HINGE_Y = 0.0
# What the game model is made of (set while it is built; None for the full and low models, which are built
# exactly as they were before it).
GAME = None


def use(kind):
    global P, BODY_SKIN, JAW_SKIN, HINGE_S, HINGE_Y
    P = dict(KINDS[kind])
    P["kind"] = kind
    BODY_SKIN = Section(P["body"])
    HINGE_S, HINGE_Y = P["hinge"]
    rows = []
    for r in P["jaw"]:
        top = lip(r[0]) if r[1] is LIP else r[1]
        rows.append((r[0], top) + tuple(r[2:]))
    JAW_SKIN = Section(rows)
    depth = max(BODY_SKIN.top(i / 400.0) - BODY_SKIN.bot(i / 400.0) for i in range(400))
    width = 2.0 * max(BODY_SKIN.at(i / 400.0)[2] for i in range(400))
    print("SHAPE %s: hinge_s=%.4f hinge_y=%.4f gill_s=%.4f depth=%.4f m width=%.4f m" % (
        kind, HINGE_S, HINGE_Y, P["gill_s"], depth * LENGTH, width * LENGTH))
    middle, out = eye_middle()
    print("EYE %s: eye_centre=Vector3(%.5f, %.5f, %.5f) m (the middle of the +X eye's rim; the shader's)" % (
        kind, middle.x * LENGTH, middle.y * LENGTH, middle.z * LENGTH))


def eye_middle():
    """The middle of the +X eye's rim, where it meets the head (body lengths), and the way it looks out: what the
    shader grows the cartoon eye about."""
    es, ey, ball, stands, shown = P["eye"]
    at, out, up = body_frame(es, ey)
    seen = math.sqrt(1.0 - (1.0 - stands / ball) ** 2)
    reach = math.asin(min(seen / shown, 0.999))
    centre = at - out * (ball - stands)
    return centre + out * (ball * math.cos(reach)), out


def lip(s):
    """The lower jaw's lip line: just up inside the upper lip."""
    return BODY_SKIN.bot(s) + 0.0012


def low_line(s):
    """The lowest line of the head and body at s: the chin where the jaw is lower than the body."""
    b = BODY_SKIN.bot(s)
    if JAW_SKIN.first <= s <= JAW_SKIN.last:
        b = min(b, JAW_SKIN.bot(s))
    return b


def body_x(s, y):
    return BODY_SKIN.x_at(s, y)


def body_frame(s, y):
    """A place on the body's +X side: the point, the way out of the skin there, and the way up along it."""
    e = 0.001
    x = body_x(s, y)
    dy = (body_x(s, y + e) - body_x(s, y - e)) / (2 * e)
    ds = (body_x(s + e, y) - body_x(s - e, y)) / (2 * e)
    return Vector((x, y, s - 0.5)), Vector((1.0, -dy, -ds)).normalized(), Vector((dy, 1.0, 0.0)).normalized()


class Part:
    """One closed piece of the fish: points (body lengths), what each is for the shader, and four-cornered
    faces. `done` welds it, turns every face outward and checks that."""

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
        the way the face faces, comes out through the solid's skin an even number of times."""
        cut = bm.copy()
        bmesh.ops.triangulate(cut, faces=cut.faces)
        cut.normal_update()
        tree = BVHTree.FromBMesh(cut)
        wrong = 0
        counted = 0
        for f in cut.faces:
            if f.calc_area() > 1e-12:
                counted += 1
                at = f.calc_center_median() + f.normal * 1e-6
                hits = 0
                while hits < 40:
                    hit = tree.ray_cast(at, f.normal)
                    if hit[0] is None:
                        break
                    hits += 1
                    at = hit[0] + f.normal * 1e-6
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
            try:
                f = bm.faces.new([made[i] for i in face])
            except ValueError:
                continue
            for loop, i in zip(f.loops, face):
                d = self.data[i]
                loop[uv].uv = d[0]
                loop[uv2].uv = d[1]
                loop[colour] = (d[2][0], d[2][1], d[2][2], 1.0)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        # (a four-cornered face with three corners on the middle plane is cut from its fourth corner, so that no
        # triangle lies flat in that plane back to back with its twin)
        for f in list(bm.faces):
            if len(f.verts) == 4:
                off = [loop for loop in f.loops if abs(loop.vert.co.x) > 1e-8]
                if len(off) == 1:
                    bmesh.ops.connect_verts(bm, verts=[off[0].vert, off[0].link_loop_next.link_loop_next.vert])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.normal_update()
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


def skin(part, section, places, half, kind):
    """Lofts a Section into a Part. `kind` is BODY or JAW."""
    rings = []
    for s in places:
        side, whole = section.outline(s, half, GAME["bend"] if GAME else 0.0)
        top, bot = section.top(s), section.bot(s)
        whole_top, lowest = BODY_SKIN.top(s), low_line(s)
        yc = bot + section.at(s)[3] * (top - bot)
        ring = []
        for j in list(range(half + 1)) + list(range(half, 0, -1)):
            x, y, arc = side[j]
            sign = 1.0 if len(ring) <= half else -1.0
            h = max(0.0, min(1.0, (y - lowest) / max(whole_top - lowest, 1e-9)))
            if kind == BODY:
                # the roof of the mouth: the flat underside of the snout, ahead of the jaw's hinge
                # (on the game model, whose points round the skin are further apart, the roof of the mouth is
                # kept to the faces along the bottom line, or the dark of it would spread up the snout's side)
                inside = (smooth(*((0.2, 0.04) if GAME else (0.45, 0.1)), (y - bot) / max(yc - bot, 1e-9))
                          * smooth(HINGE_S + 0.012, HINGE_S - 0.006, s))
                ring.append(part.add((sign * x, y, s - 0.5), (s, 1.0 - h),
                                     (sign * arc * LENGTH, 1.0 - whole * LENGTH), (BODY / 10.0, 0.0, inside)))
            else:
                inside = smooth(0.5, 0.9, (y - yc) / max(top - yc, 1e-9)) if y > yc else 0.0
                inside *= smooth(HINGE_S + 0.02, HINGE_S - 0.002, s)
                ring.append(part.add((sign * x, y, s - 0.5), (s, 1.0 - h),
                                     (sign * arc * LENGTH, 1.0 - whole * LENGTH), (JAW / 10.0, 0.0, inside)))
        rings.append(ring)
    part.loft(rings)


def body_places(low):
    if GAME:
        return game_places()
    head = 7 if low else 34
    rest = 12 if low else 66
    behind = 0.11
    places = [behind * (i / head) ** 1.4 for i in range(head)]
    places += [lerp(behind, BODY_SKIN.last, i / rest) for i in range(rest + 1)]
    return places


def eye(low):
    """The +X eye: a dome set in the side of the head."""
    part = Part("eye")
    es, ey, ball, stands, shown = P["eye"]
    at, out, up = body_frame(es, ey)
    along = up.cross(out).normalized()
    seen = math.sqrt(1.0 - (1.0 - stands / ball) ** 2)
    reach = math.asin(min(seen / shown, 0.999))
    centre = at - out * (ball - stands)
    rows = GAME["eye_rows"] if GAME else (3 if low else 8)
    around = GAME["eye_around"] if GAME else (8 if low else 24)
    rings = []
    for i in range(rows + 1):
        a = reach * i / rows
        ring = []
        for k in range(around):
            q = TAU * k / around
            p = centre + out * (ball * math.cos(a)) + (up * math.cos(q) + along * math.sin(q)) * (ball * math.sin(a))
            across = 0.5 * 0.644 * math.sin(a) / seen
            ring.append(part.add(p, (0.5 + across * math.cos(q), 1.0 - (0.5 + across * math.sin(q))), (0.0, 1.0),
                                 (EYE / 10.0, 0.0, 0.0)))
        rings.append(ring)
    back = centre + out * (ball * math.cos(reach) - 0.002)
    rings.append([part.add(back, (0.5 + 0.5 * math.cos(TAU * k / around), 0.5 - 0.5 * math.sin(TAU * k / around)),
                           (0.0, 1.0), (EYE / 10.0, 0.0, 0.0)) for k in range(around)])
    part.loft(rings)
    return part


def spine(low):
    """The +X side's scalpel: a narrow blade lying along the tail's wrist in its groove, its point forward."""
    part = Part("spine")
    ss, sy, long = P["spine"]
    stations = GAME["spine_stations"] if GAME else (3 if low else 12)
    around = GAME["spine_around"] if GAME else (4 if low else 10)
    rings = []
    for i in range(stations + 1):
        u = i / stations
        s = ss + long * u
        at, out, up = body_frame(s, sy)
        # (pointed in front, rounded behind where it sits in its sheath)
        size = (u ** 0.7) * (1.0 - smooth(0.82, 1.0, u)) ** 0.5 if 0.0 < u < 1.0 else 0.0
        high = 0.0058 * size
        thick = 0.0028 * size
        ring = []
        for k in range(around):
            q = TAU * k / around
            p = at - out * 0.0006 + up * (high * math.cos(q)) + out * (thick * max(math.sin(q), -0.3))
            ring.append(part.add(p, (u, 0.5), (0.0, 1.0), (SPINE / 10.0, 0.0, 0.0)))
        rings.append(ring)
    part.loft(rings)
    return part


def fin(name, kind, rays, cols, rows, base, direction, length, normal, thick):
    """A fin: `cols` + 1 rays fanned from the line `base(t)` (t 0 its leading edge to 1 its trailing edge),
    each going the way `direction(t)` for `length(t)`; flat, facing `normal`; `thick` at its root. `rays` is
    how many rays the shader draws across it. For the game model its rays are placed where its edge bends most
    (`adaptive`), not evenly."""
    part = Part(name)
    normal = normal.normalized()
    left, right = [], []
    ts = [i / cols for i in range(cols + 1)]
    if GAME:
        ts = adaptive(lambda t: tuple(base(t) + direction(t).normalized() * length(t)), cols, 0.0, 1.0)
    for i in range(cols + 1):
        t = ts[i]
        b, d, long = base(t), direction(t).normalized(), length(t)
        edge = min(1.0, t / 0.06) ** 0.5 * min(1.0, (1.0 - t) / 0.08) ** 0.5
        a, c = [], []
        for j in range(rows + 1):
            r = (j / rows) ** 0.85
            taper = 1.0 - r
            th = edge * (taper ** 0.5) * thick * (0.12 + 0.88 * taper ** 1.6)
            mid = b + d * (long * r)
            data = ((r, 1.0 - t * rays), (normal.x, 1.0 - normal.y), (kind / 10.0, t, normal.z * 0.5 + 0.5))
            a.append(part.add(mid + normal * (th * 0.5), *data))
            c.append(part.add(mid - normal * (th * 0.5), *data))
        left.append(a)
        right.append(c)
    for i in range(cols):
        for j in range(rows):
            for sheet in (left, right):
                a, b, c, d = sheet[i][j], sheet[i + 1][j], sheet[i + 1][j + 1], sheet[i][j + 1]
                if j == rows - 1 and i == 0:
                    part.faces += [(a, b, d), (b, c, d)]
                elif j == rows - 1 and i == cols - 1:
                    part.faces += [(a, b, c), (a, c, d)]
                else:
                    part.faces.append((a, b, c, d))
        part.faces.append((left[i][0], right[i][0], right[i + 1][0], left[i + 1][0]))
    # (closed at the leading and trailing edges, which have no thickness: their two sheets weld into one)
    return part


def turn(d0, d1, t):
    """From one direction round to another."""
    d0, d1 = d0.normalized(), d1.normalized()
    angle = d0.angle(d1)
    if angle < 1e-6:
        return d0
    return (d0 * math.sin((1.0 - t) * angle) + d1 * math.sin(t * angle)) / math.sin(angle)


def clearance(part, normal, reach):
    """The least gap (mm) between a paired fin and the body's side as the shader rows it: every point of the fin
    from a third of the way out, pushed as far in towards the body as the shader takes it (`reach(r)`, body lengths), against the
    body's skin at its height."""
    normal = normal.normalized()
    least = 1e9
    for p, d in zip(part.verts, part.data):
        r = d[0][0]
        if r < 0.35:
            continue
        q = p - normal * reach(r)
        s = q.z + 0.5
        if BODY_SKIN.bot(s) < q.y < BODY_SKIN.top(s):
            least = min(least, (abs(q.x) - body_x(s, q.y)) * LENGTH * 1000.0)
    return least if least < 1e8 else float("inf")


def fins(low):
    made = []
    rows = 2 if low else 7
    # (the game model: how many rays and rows each fin has)
    g = GAME["fins"] if GAME else {}

    def long_fin(name, kind, spec, up):
        s0, s1, heights, rakes, rays = spec
        height = curve(heights)
        rake = curve(rakes)
        sign = 1.0 if up else -1.0
        edge = BODY_SKIN.top if up else BODY_SKIN.bot
        cols = 6 if low else max(rays, 16)
        if g:
            cols = g[name][0]
        return fin(
            name, kind, rays, cols, g[name][1] if g else rows,
            lambda t: Vector((0.0, edge(lerp(s0, s1, t)) - sign * 0.006, lerp(s0, s1, t) - 0.5)),
            lambda t: Vector((0.0, sign * math.sin(math.radians(rake(t))), math.cos(math.radians(rake(t))))),
            lambda t: height(t) + 0.006, Vector((1.0, 0.0, 0.0)), 0.0045)
    made.append(long_fin("dorsal", DORSAL, P["dorsal"], True))
    made.append(long_fin("anal", ANAL, P["anal"], False))
    ts, th, t_mid, t_long, t_power, t_spread = P["tail"]

    def tail_long(t):
        a = abs(2.0 * t - 1.0)
        long = lerp(t_mid, t_long, a ** t_power)
        if a > 0.88:
            long *= 1.0 - 0.18 * ((a - 0.88) / 0.12) ** 2
        return long
    made.append(fin(
        "tail", TAIL, 16, g["tail"][0] if g else (5 if low else 20), g["tail"][1] if g else rows,
        lambda t: Vector((0.0, lerp(th, -th, t), ts - 0.012 * (2.0 * t - 1.0) ** 2 - 0.5)),
        lambda t: Vector((0.0, math.sin(math.radians(t_spread * (1.0 - 2.0 * t))), math.cos(math.radians(t_spread * (1.0 - 2.0 * t))))),
        tail_long, Vector((1.0, 0.0, 0.0)), 0.009))

    # The paired fins, the +X one of each (the -X is its mirror picture).
    def on_body(s, y, sunk=0.003):
        return Vector((body_x(s, y) - sunk, y, s - 0.5))
    ps, py0, py1, p_long, p_short = P["pectoral"]
    q0, q1 = on_body(ps, py0), on_body(ps + 0.012, py1)
    e0, e1 = Vector((0.32, 0.38, 0.87)), Vector((0.3, -0.42, 0.86))
    pectoral_normal = e0.cross(e1)
    pectoral = fin(
        "pectoral", PECTORAL, 15, g["pectoral"][0] if g else (4 if low else 16), g["pectoral"][1] if g else rows, lambda t: q0.lerp(q1, t), lambda t: turn(e0, e1, t),
        lambda t: lerp(p_long, p_short, t ** 1.1) * (0.8 + 0.2 * smooth(0.0, 0.2, t)), pectoral_normal, 0.004)
    made += [pectoral, pectoral.mirrored("pectoral_left")]
    print("CLEARANCE pectoral fin to body, rowing: %.1f mm" % clearance(pectoral, pectoral_normal, lambda r: ROW_REACH * ROW_IN * r))
    vs, v_long = P["pelvic"]
    v0, v1 = on_body(vs, BODY_SKIN.bot(vs) + 0.012, 0.002), on_body(vs + 0.022, BODY_SKIN.bot(vs + 0.022) + 0.008, 0.002)
    f0, f1 = Vector((0.2, -0.85, 0.5)), Vector((0.15, -0.45, 0.88))
    pelvic = fin(
        "pelvic", PELVIC, 6, g["pelvic"][0] if g else (3 if low else 8), g["pelvic"][1] if g else rows, lambda t: v0.lerp(v1, t), lambda t: turn(f0, f1, t),
        lambda t: lerp(v_long, v_long * 0.45, t), f0.cross(f1), 0.004)
    made += [pelvic, pelvic.mirrored("pelvic_left")]
    return made


# How far the shader moves a pectoral fin's edge out and in as it rows (body lengths), for the clearance check.
ROW_REACH = 0.035
# (the shader rows it out by up to 1.5 of that and in by up to ROW_IN of it)
ROW_IN = 0.5


# The game model (Claude's numbers, 2026-11-18): about 1,500 triangles, against the Twilight Princess yardstick
# of 900 to 1,800 for an animal 0.15 to 0.5 m long. Its rings along the body are placed where the back, belly and
# width bend most (the snout, the forehead, the tail's wrist), with three at the jaw's hinge so the mouth opens as
# on the full model; its points round each ring crowd round the tight curves of the back and the belly; a round
# eye; each fin's rays placed where its edge bends most. Rows across a fin: two where the shader bends them (the
# dorsal, anal and tail ripple as r squared), one where it only swings them.
GAME_MODEL = {
    "rings": 26, "half": 7, "bend": 0.4, "jaw_half": 4,
    "eye_rows": 3, "eye_around": 24, "spine_stations": 4, "spine_around": 5,
    "fins": {"dorsal": (14, 2), "anal": (11, 2), "tail": (10, 2), "pectoral": (6, 1), "pelvic": (4, 2)},
}


def game_places():
    """The game model's rings along the body: at the ends, about the jaw's hinge, and where a straight line
    between rings would stray furthest from the back line, the belly line or the width."""
    fixed = [HINGE_S - 0.02, HINGE_S - 0.006, HINGE_S + 0.012]
    return adaptive(lambda s: (BODY_SKIN.top(s), low_line(s), BODY_SKIN.at(s)[2] * 2.0), GAME["rings"] - 1,
                    BODY_SKIN.first, BODY_SKIN.last, fixed, most=0.07)


def make(name, low):
    parts = []
    body = Part("body")
    skin(body, BODY_SKIN, body_places(low), GAME["half"] if GAME else (5 if low else 20), BODY)
    parts.append(body)
    jaw = Part("jaw")
    jaw_rings = 4 if low else 18
    places = [lerp(JAW_SKIN.first, JAW_SKIN.last, (i / jaw_rings) ** 1.1) for i in range(jaw_rings + 1)]
    if GAME:
        # (the jaw's rings where the body's are, so that its lip runs inside the upper lip all the way)
        inner = [s for s in body_places(low) if JAW_SKIN.first + 0.004 < s < JAW_SKIN.last - 0.004]
        places = [JAW_SKIN.first] + inner + [JAW_SKIN.last]
    skin(jaw, JAW_SKIN, places, GAME["jaw_half"] if GAME else (3 if low else 10), JAW)
    parts.append(jaw)
    ball = eye(low)
    parts += [ball, ball.mirrored("eye_left")]
    blade = spine(low)
    parts += [blade, blade.mirrored("spine_left")]
    parts += fins(low)
    return assemble(name, parts)


def assemble(name, parts):
    verts, faces, corners = [], [], []
    told = []
    wrong_all = 0
    for part in parts:
        out, wrong, counted = part.done()
        told.append("%s %d/%d wrong" % (part.name, wrong, counted))
        wrong_all += wrong
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
            colour[poly.loop_start + corner].color = d[2]
    mesh.color_attributes.active_color = mesh.color_attributes["Color"]
    mesh.color_attributes.render_color_index = mesh.color_attributes.find("Color")
    material = bpy.data.materials.get(NAME) or bpy.data.materials.new(NAME)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.8, 0.7, 0.3, 1.0)
    material.diffuse_color = (0.8, 0.7, 0.3, 1.0)
    mesh.materials.append(material)
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-8)
    bpy.ops.object.mode_set(mode="OBJECT")
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    box = [min(v.co[k] for v in mesh.vertices) for k in range(3)], [max(v.co[k] for v in mesh.vertices) for k in range(3)]
    print("BUILT %s verts=%d tris=%d box x %.4f..%.4f along %.4f..%.4f up %.4f..%.4f" % (
        name, len(mesh.vertices), tris, box[0][0], box[1][0], box[0][1], box[1][1], box[0][2], box[1][2]))
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
    scene.display.shading.show_backface_culling = True
    scene.render.resolution_x, scene.render.resolution_y = 1200, 900
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 100.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    L = LENGTH
    # (Blender space: the nose is towards +Y, up is +Z)
    views = [("right", (1, 0, 0), (0, 0, 0), 1.3), ("left", (-1, 0, 0), (0, 0, 0), 1.3),
             ("top", (0, -0.001, 1), (0, 0, 0), 1.3), ("under", (0, 0.001, -1), (0, 0, 0), 1.3),
             ("front", (0, 1, 0), (0, 0, 0), 0.9), ("back", (0, -1, 0), (0, 0, 0), 0.9),
             ("quarter", (0.7, 0.6, 0.35), (0, 0, 0), 1.3), ("low_quarter", (0.6, 0.6, -0.5), (0, 0, 0), 1.3),
             ("head", (1, 0.3, 0.1), (0, 0.38, 0), 0.4), ("head_under", (0.5, 0.6, -0.7), (0, 0.4, -0.01), 0.4),
             ("tail", (1, -0.3, 0.15), (0, -0.33, 0), 0.5)]
    for low, obj in ((False, made[0]), (True, made[1])):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if low and view not in ("right", "quarter"):
                continue
            offset = Vector(direction).normalized() * 10.0
            camera.data.ortho_scale = frame * L
            camera.location = Vector(target) * L + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "X" if view in ("top", "under") else "Y").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % ("lo_" if low else "", view))
            bpy.ops.render.render(write_still=True)


def make_game(name):
    global GAME
    GAME = GAME_MODEL
    try:
        return make(name, False)
    finally:
        GAME = None


def main():
    os.makedirs(OUT, exist_ok=True)
    for kind in WANTED:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version = 0
        use(kind)
        name = "%s_%s" % (NAME, kind)
        full = make(name, False)
        low = make(name + "_lo", True)
        game = make_game(name + "_game")
        export_one(full, os.path.join(OUT, name + ".glb"))
        export_one(low, os.path.join(OUT, name + "_lo.glb"))
        export_one(game, os.path.join(OUT, name + "_game.glb"))
        low.location.x = 0.15
        game.location.x = 0.3
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, name + ".blend"))
        low.location.x = 0.0
        game.location.x = 0.0
        if PREVIEW:
            folder = os.path.join(PREVIEW, kind)
            os.makedirs(folder, exist_ok=True)
            render(folder, [full, low, game])


if __name__ == "__main__":
    main()
