"""Builds the butterflyfish (creatures/butterflyfish), one model for each type, and exports them for Godot.

Run from the game's root:
    blender --background --python creatures/butterflyfish/tools/build_butterflyfish.py
    blender --background --python creatures/butterflyfish/tools/build_butterflyfish.py -- <preview folder>   # with pictures
    blender --background --python creatures/butterflyfish/tools/build_butterflyfish.py -- <preview folder> raccoon   # only these

One shape for each type (TYPES: threadfin, raccoon, copperband, longnose, bannerfish). For each it writes
creatures/butterflyfish/models/butterflyfish_<type>.glb (the full model) and butterflyfish_<type>_lo.glb (far off,
phones, many at once), and the editable creatures/butterflyfish/tools/butterflyfish_<type>.blend (this folder has
a .gdignore). Each model is one still mesh with one surface: the shader (butterflyfish.gdshader) rows its pectoral
fins, bends it, works its jaw and draws every marking. It prints a WINDING line for each model (the check that
nothing is inside out), and a SHAPE line: the numbers Butterflyfish.TYPES gives the shader for that type (copy
them across by hand when a shape changes).

Every type is built to the same length, 0.18 m from snout to tail tip, nose towards -Z, belly down, its origin at
the middle of its length. A butterflyfish is a thin upright disc:

- THE BODY: one skin from the tip of the snout to the root of the tail, very flat-sided, sharp along its back and
  belly; the snout a small beak that sticks out (short in the threadfin, raccoon and bannerfish, a long tube in the
  copperband, a very long thin one in the longnose).
- THE MOUTH: the upper snout is the front of the body's skin, flat underneath (the roof of the mouth); the LOWER
  JAW is a part of its own, which fits up inside the upper lip and runs back into the throat (the shader swings
  it about its hinge).
- THE FINS: thin closed solids: one continuous DORSAL fin, spines in front (each a point, the skin dipping
  between) and soft rays behind; the ANAL fin; a small square TAIL; a pair each of pointed PELVIC fins and of
  PECTORAL fins, the ones it rows with; and on the threadfin a trailing FILAMENT from the soft dorsal, on the
  bannerfish the long banner.

What a point is, for the shader: vertex colour red the part, as a tenth (0 body, 0.1 lower jaw, 0.2 eye,
0.4 dorsal, 0.5 filament, 0.6 tail, 0.7 anal, 0.8 pelvic, 0.9 pectoral). On the body and jaw: UV.x how far
along the fish (0 snout to 1 tail tip), UV.y how high on it (0 belly line to 1 back line; on the jaw 0 keel to 1
lip); blue how much it is inside the mouth. On an eye: UV where a point is on its round face seen straight on (its
middle at 0.5, 0.5). On a fin: UV.x along its rays (0 root to 1 edge), UV.y across it counted in rays (0 its
leading edge); UV2 and blue the way its flat side faces (x, y, and z as z / 2 + 0.5), which is the way the shader
waves it. (The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.) The markings are drawn
from where a point is in the fish's side view (its still place: z and y), so they run across body and fins alike.

Everything here is worked out in body lengths in Godot space (Y up, nose towards -Z) and written out in metres.
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

# Kept in step with butterflyfish.gd and butterflyfish.gdshader.
FAMILY = "butterflyfish"
LENGTH = 0.18
TAU = math.tau
BODY, JAW, EYE, SPINE, DORSAL, FILAMENT, TAIL, ANAL, PELVIC, PECTORAL = 0, 1, 2, 3, 4, 5, 6, 7, 8, 9
# The gill arches (added 2026-11-18). The throat's lining is of the BODY part, marked by vertex colour green 1.
GILL = 10

# The wrist of the tail and the root of the tail fin, the same in every type: (s, y) of the top line and the
# bottom line, and (s, half width).
END_TOP = [(0.80, 0.052), (0.83, 0.045), (0.86, 0.048), (0.885, 0.044), (0.895, 0.028)]
END_BOT = [(0.80, -0.050), (0.83, -0.045), (0.86, -0.048), (0.885, -0.044), (0.895, -0.028)]
END_HW = [(0.75, 0.018), (0.82, 0.011), (0.86, 0.005), (0.885, 0.0015), (0.895, 0.0)]
# Half the height of the root of the tail fin.
PED = 0.046

# Each type. `top`, `bot`: the fish's outline seen from the side, (s, y) from the snout's tip to where the wrist
# of the tail begins; `hw`: its half width. `mouth`: how high the line of the mouth is at the snout's tip;
# `hinge`: where the lower jaw hinges (s, y); `gill`: how far along the gill cover's rear edge reaches; `eye`:
# where (s, y), then the eyeball's radius, how far it stands out of the head, and how much of the dome's width
# shows. `dorsal` and `anal`: from s0 to s1 along the back (the belly), so many rays of which the first `spines`
# are spines with the skin dipping `notch` between their points; `len` (t, length) and `ang` (t, degrees up from
# straight back) across the fin, t 0 its leading edge to 1 its trailing edge. `tail`: (root s, length is to s = 1,
# spread in degrees, how rounded). `pelvic`: (s, length). `pectoral`: (y of its root's top, length). `filament`:
# (s0, s1, length, degrees, how pointed), or None.
TYPES = {
    "threadfin": {
        "top": [(0.0, -0.026), (0.02, -0.014), (0.05, 0.002), (0.08, 0.035), (0.12, 0.095), (0.17, 0.16),
                (0.24, 0.222), (0.32, 0.258), (0.42, 0.27), (0.52, 0.258), (0.62, 0.215), (0.70, 0.15), (0.76, 0.085)],
        "bot": [(0.0, -0.034), (0.02, -0.046), (0.045, -0.058), (0.07, -0.078), (0.11, -0.118), (0.17, -0.168),
                (0.25, -0.212), (0.34, -0.236), (0.44, -0.238), (0.54, -0.218), (0.63, -0.17), (0.71, -0.105),
                (0.77, -0.062)],
        "hw": [(0.0, 0.0), (0.008, 0.008), (0.02, 0.013), (0.045, 0.02), (0.08, 0.03), (0.13, 0.043), (0.2, 0.054),
               (0.3, 0.058), (0.42, 0.054), (0.55, 0.043), (0.66, 0.03)],
        "mouth": -0.03, "hinge": (0.045, -0.033), "gill": 0.25, "eye": (0.132, 0.04, 0.045, 0.008, 0.7),
        "dorsal": {"s0": 0.28, "s1": 0.80, "rays": 24, "spines": 12, "notch": 0.16,
                   "len": [(0.0, 0.03), (0.15, 0.07), (0.5, 0.088), (0.75, 0.125), (0.9, 0.115), (1.0, 0.075)],
                   "ang": [(0.0, 72.0), (0.5, 56.0), (0.75, 36.0), (1.0, 8.0)]},
        "anal": {"s0": 0.56, "s1": 0.80, "rays": 16, "spines": 3, "notch": 0.12,
                 "len": [(0.0, 0.05), (0.2, 0.098), (0.6, 0.115), (1.0, 0.07)],
                 "ang": [(0.0, 66.0), (0.5, 46.0), (1.0, 8.0)]},
        "tail": (0.85, 16.0, 0.03), "pelvic": (0.31, 0.14), "pectoral": (-0.05, 0.17),
        "filament": (0.672, 0.694, 0.34, 34.0, 0.0),
    },
    "raccoon": {
        "top": [(0.0, -0.024), (0.02, -0.008), (0.045, 0.018), (0.08, 0.062), (0.12, 0.118), (0.17, 0.172),
                (0.24, 0.226), (0.32, 0.258), (0.42, 0.268), (0.52, 0.256), (0.62, 0.214), (0.70, 0.15), (0.76, 0.085)],
        "bot": [(0.0, -0.032), (0.02, -0.046), (0.045, -0.062), (0.07, -0.084), (0.11, -0.124), (0.17, -0.172),
                (0.25, -0.214), (0.34, -0.238), (0.44, -0.24), (0.54, -0.22), (0.63, -0.172), (0.71, -0.106),
                (0.77, -0.062)],
        "hw": [(0.0, 0.0), (0.008, 0.009), (0.02, 0.015), (0.045, 0.023), (0.08, 0.033), (0.13, 0.045), (0.2, 0.056),
               (0.3, 0.06), (0.42, 0.056), (0.55, 0.044), (0.66, 0.031)],
        "mouth": -0.028, "hinge": (0.04, -0.031), "gill": 0.245, "eye": (0.125, 0.05, 0.045, 0.008, 0.7),
        "dorsal": {"s0": 0.27, "s1": 0.80, "rays": 24, "spines": 12, "notch": 0.14,
                   "len": [(0.0, 0.028), (0.15, 0.062), (0.5, 0.082), (0.78, 0.104), (0.92, 0.098), (1.0, 0.07)],
                   "ang": [(0.0, 72.0), (0.5, 56.0), (0.75, 36.0), (1.0, 8.0)]},
        "anal": {"s0": 0.56, "s1": 0.80, "rays": 16, "spines": 3, "notch": 0.12,
                 "len": [(0.0, 0.05), (0.2, 0.095), (0.6, 0.108), (1.0, 0.07)],
                 "ang": [(0.0, 66.0), (0.5, 46.0), (1.0, 8.0)]},
        "tail": (0.85, 16.0, 0.05), "pelvic": (0.31, 0.135), "pectoral": (-0.05, 0.17),
        "filament": None,
    },
    "copperband": {
        "top": [(0.0, -0.021), (0.03, -0.014), (0.07, -0.004), (0.11, 0.014), (0.14, 0.045), (0.18, 0.105),
                (0.24, 0.178), (0.32, 0.236), (0.42, 0.265), (0.52, 0.262), (0.62, 0.225), (0.70, 0.155), (0.76, 0.088)],
        "bot": [(0.0, -0.03), (0.03, -0.037), (0.07, -0.047), (0.11, -0.062), (0.14, -0.088), (0.19, -0.142),
                (0.26, -0.2), (0.35, -0.236), (0.45, -0.24), (0.55, -0.218), (0.64, -0.165), (0.71, -0.105),
                (0.77, -0.062)],
        "hw": [(0.0, 0.0), (0.008, 0.006), (0.03, 0.009), (0.07, 0.012), (0.11, 0.018), (0.15, 0.031), (0.2, 0.045),
               (0.27, 0.055), (0.35, 0.058), (0.45, 0.053), (0.57, 0.041), (0.67, 0.029)],
        "mouth": -0.0255, "hinge": (0.034, -0.0275), "gill": 0.295, "eye": (0.185, 0.042, 0.042, 0.0075, 0.7),
        "dorsal": {"s0": 0.33, "s1": 0.80, "rays": 22, "spines": 9, "notch": 0.18,
                   "len": [(0.0, 0.03), (0.15, 0.065), (0.45, 0.095), (0.72, 0.155), (0.88, 0.14), (1.0, 0.08)],
                   "ang": [(0.0, 72.0), (0.45, 60.0), (0.72, 46.0), (1.0, 6.0)]},
        "anal": {"s0": 0.56, "s1": 0.80, "rays": 16, "spines": 3, "notch": 0.12,
                 "len": [(0.0, 0.055), (0.2, 0.11), (0.6, 0.135), (1.0, 0.075)],
                 "ang": [(0.0, 70.0), (0.5, 52.0), (1.0, 6.0)]},
        "tail": (0.85, 15.0, 0.0), "pelvic": (0.34, 0.14), "pectoral": (-0.05, 0.16),
        "filament": None,
    },
    "longnose": {
        "top": [(0.0, -0.0195), (0.05, -0.016), (0.1, -0.011), (0.15, -0.002), (0.19, 0.022), (0.23, 0.078),
                (0.28, 0.152), (0.35, 0.215), (0.44, 0.245), (0.53, 0.24), (0.62, 0.205), (0.70, 0.145), (0.76, 0.085)],
        "bot": [(0.0, -0.0275), (0.05, -0.0305), (0.1, -0.0345), (0.15, -0.043), (0.19, -0.066), (0.24, -0.125),
                (0.3, -0.185), (0.38, -0.22), (0.47, -0.225), (0.56, -0.205), (0.64, -0.16), (0.71, -0.105),
                (0.77, -0.062)],
        "hw": [(0.0, 0.0), (0.006, 0.005), (0.05, 0.007), (0.1, 0.0095), (0.15, 0.014), (0.2, 0.027), (0.25, 0.042),
               (0.32, 0.053), (0.4, 0.055), (0.5, 0.049), (0.6, 0.038), (0.68, 0.028)],
        "mouth": -0.0235, "hinge": (0.032, -0.025), "gill": 0.335, "eye": (0.238, 0.034, 0.04, 0.0072, 0.7),
        "dorsal": {"s0": 0.37, "s1": 0.80, "rays": 22, "spines": 12, "notch": 0.3,
                   "len": [(0.0, 0.05), (0.12, 0.1), (0.45, 0.1), (0.75, 0.115), (0.9, 0.105), (1.0, 0.07)],
                   "ang": [(0.0, 70.0), (0.5, 56.0), (0.75, 36.0), (1.0, 8.0)]},
        "anal": {"s0": 0.57, "s1": 0.80, "rays": 16, "spines": 3, "notch": 0.14,
                 "len": [(0.0, 0.05), (0.2, 0.1), (0.6, 0.118), (1.0, 0.07)],
                 "ang": [(0.0, 66.0), (0.5, 46.0), (1.0, 8.0)]},
        "tail": (0.85, 15.0, -0.04), "pelvic": (0.37, 0.135), "pectoral": (-0.045, 0.16),
        "filament": None,
    },
    "bannerfish": {
        "top": [(0.0, -0.03), (0.02, -0.016), (0.045, 0.006), (0.08, 0.052), (0.12, 0.118), (0.17, 0.188),
                (0.24, 0.258), (0.31, 0.296), (0.4, 0.296), (0.5, 0.266), (0.6, 0.216), (0.69, 0.15), (0.76, 0.085)],
        "bot": [(0.0, -0.038), (0.02, -0.051), (0.045, -0.064), (0.07, -0.084), (0.11, -0.127), (0.17, -0.182),
                (0.25, -0.232), (0.34, -0.262), (0.44, -0.264), (0.54, -0.236), (0.63, -0.18), (0.71, -0.11),
                (0.77, -0.064)],
        "hw": [(0.0, 0.0), (0.008, 0.008), (0.02, 0.013), (0.045, 0.02), (0.08, 0.03), (0.13, 0.043), (0.2, 0.054),
               (0.3, 0.058), (0.42, 0.054), (0.55, 0.043), (0.66, 0.03)],
        "mouth": -0.034, "hinge": (0.04, -0.037), "gill": 0.245, "eye": (0.128, 0.034, 0.043, 0.0078, 0.7),
        "dorsal": {"s0": 0.36, "s1": 0.80, "rays": 22, "spines": 7, "notch": 0.12,
                   "len": [(0.0, 0.06), (0.2, 0.085), (0.5, 0.11), (0.75, 0.13), (0.9, 0.115), (1.0, 0.07)],
                   "ang": [(0.0, 66.0), (0.5, 52.0), (0.75, 34.0), (1.0, 8.0)]},
        "anal": {"s0": 0.56, "s1": 0.80, "rays": 16, "spines": 3, "notch": 0.12,
                 "len": [(0.0, 0.06), (0.2, 0.115), (0.55, 0.135), (1.0, 0.07)],
                 "ang": [(0.0, 72.0), (0.5, 50.0), (1.0, 8.0)]},
        "tail": (0.85, 16.0, 0.0), "pelvic": (0.31, 0.15), "pectoral": (-0.05, 0.17),
        "filament": (0.285, 0.372, 0.52, 66.0, 1.0),
    },
}
NAMES = list(TYPES)
WANTED = [name for name in ARGS[1:] if name in NAMES] or NAMES
# The game model's numbers: rings along the body and points down each side of a ring; places across the soft
# rays of the dorsal and anal fins (the spines keep a place at each point and dip); places across the tail.
GAME_BODY_RINGS = 24
GAME_HALF = 6
GAME_SOFT = (7, 5)
GAME_TAIL = 8
# The throat and the gills (added 2026-11-18): the throat is a short tunnel from just ahead of the jaw's hinge back
# to just ahead of the gill cover's edge, an oval at each of THROAT_KNOTS places (s, the height of its middle, its
# half height, its half width; body lengths, straight lines between them). The shader is told the same numbers
# (TYPES "throat" in the node script) and, while the mouth is open, cuts away whatever of the body and the jaw lies
# inside it (they made the dark wall at the back of the mouth), so that the tunnel and the gills in it show. Each
# model's throat has this many strips between two knots and this many points round; its gill arches this many
# steps from the throat's floor up its side.
THROAT_KNOTS = 5
THROAT_STRIPS = {"full": 3, "game": 1, "low": 1}
THROAT_ROUND = {"full": 16, "game": 6, "low": 6}
GILL_STEPS = {"full": 10, "game": 2, "low": 1}


# True while the GAME model is being built (see `make`): fewer points, put where they shape the outline.
GAME = False


def to_b(p):
    return Vector((p.x, -p.z, p.y))


def spread(lines_at, a, b, n, forced=(), even=0.35):
    """n + 1 places from a to b (a and b among them) for the game model, closer together where the lines
    `lines_at(t)` gives (a list of (x, y) points, one on each line) bend: each stretch of a line is worth
    sqrt(how far it turns x how long it is) (so that a chord strays about as far from the curve everywhere),
    and `even` of the whole is spread evenly. Each place in `forced` replaces the nearest place."""
    m = 800
    ts = [a + (b - a) * i / m for i in range(m + 1)]
    pts = [lines_at(t) for t in ts]
    w = [0.0] * m
    for k in range(len(pts[0])):
        seg = [(pts[i + 1][k][0] - pts[i][k][0], pts[i + 1][k][1] - pts[i][k][1]) for i in range(m)]
        lens = [math.hypot(*d) for d in seg]
        for i in range(1, m):
            if lens[i] > 1e-12 and lens[i - 1] > 1e-12:
                c = (seg[i][0] * seg[i - 1][0] + seg[i][1] * seg[i - 1][1]) / (lens[i] * lens[i - 1])
                turn = math.acos(max(-1.0, min(1.0, c)))
                w[i] += math.sqrt(turn * 0.5 * (lens[i] + lens[i - 1]))
    total = sum(w)
    share = (even * total / m) if total > 0.0 else 1.0
    w = [x + share for x in w]
    acc = [0.0]
    for x in w:
        acc.append(acc[-1] + x)
    out = [a]
    for j in range(1, n):
        want = acc[-1] * j / n
        i = min(bisect.bisect_right(acc, want) - 1, m - 1)
        f = (want - acc[i]) / max(acc[i + 1] - acc[i], 1e-12)
        out.append(ts[i] + (ts[i + 1] - ts[i]) * f)
    out.append(b)
    fixed = {0, len(out) - 1}
    for f in forced:
        if not a < f < b:
            continue
        free = [j for j in range(len(out)) if j not in fixed]
        if free:
            j = min(free, key=lambda j: abs(out[j] - f))
            out[j] = f
            fixed.add(j)
        else:
            out.append(f)
        out.sort()
        fixed = {j for j, x in enumerate(out) if x in forced or j in (0, len(out) - 1)}
    return sorted(set(out))


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
    ellipse, more is squarer, less is sharper). All in body lengths; each a function of s."""

    def __init__(self, first, last, top, bot, hw, ycf, nt, nb):
        self.first = first
        self.last = last
        self.f = [top, bot, hw, ycf, nt, nb]

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
        if GAME:
            # (the game model: the points closer together where the ring bends, at the sharp back and belly,
            # fewer down the flat side; each still told its true distance round from the top)
            worth = [0.0]
            for i in range(steps):
                turn = 0.0
                if 0 < i:
                    ax, ay = dense[i][0] - dense[i - 1][0], dense[i][1] - dense[i - 1][1]
                    bx, by = dense[i + 1][0] - dense[i][0], dense[i + 1][1] - dense[i][1]
                    la, lb = math.hypot(ax, ay), math.hypot(bx, by)
                    if la > 1e-12 and lb > 1e-12:
                        turn = math.acos(max(-1.0, min(1.0, (ax * bx + ay * by) / (la * lb))))
                worth.append(math.sqrt(turn * (acc[i + 1] - acc[i])))
            bend = sum(worth)
            total = [0.0]
            for i in range(steps):
                total.append(total[-1] + worth[i + 1] + 0.5 * bend * (acc[i + 1] - acc[i]) / max(whole, 1e-12))
            for j in range(half + 1):
                want = total[-1] * j / half
                i = min(bisect.bisect_right(total, want) - 1, steps - 1)
                span = total[i + 1] - total[i]
                t = (want - total[i]) / span if span > 1e-12 else 0.0
                out.append((lerp(dense[i][0], dense[i + 1][0], t), lerp(dense[i][1], dense[i + 1][1], t),
                            lerp(acc[i], acc[i + 1], t)))
            return out, whole
        for j in range(half + 1):
            want = whole * j / half
            i = min(bisect.bisect_right(acc, want) - 1, steps - 1)
            span = acc[i + 1] - acc[i]
            t = (want - acc[i]) / span if span > 1e-12 else 0.0
            out.append((lerp(dense[i][0], dense[i + 1][0], t), lerp(dense[i][1], dense[i + 1][1], t), want))
        return out, whole


# The type being built (set by `use`): its numbers, its skins, and the places the shader shares.
P = {}
BODY_SKIN = None
JAW_SKIN = None
HINGE_S = 0.0
HINGE_Y = 0.0
GILL_S = 0.0
EYE_AT = (0.0, 0.0)
PEC_ROOT = Vector((0.0, 0.0, 0.0))
EYE_SKIN = Vector((0.0, 0.0, 0.0))


def use(name):
    """Makes `name` the shape being built."""
    global P, BODY_SKIN, JAW_SKIN, HINGE_S, HINGE_Y, GILL_S, EYE_AT
    P = dict(TYPES[name])
    P["name"] = name
    top = curve(P["top"] + END_TOP)
    bot = curve(P["bot"] + END_BOT)
    hw = curve(P["hw"] + END_HW)
    P["sil_top"], P["sil_bot"], P["sil_hw"] = top, bot, hw
    HINGE_S, HINGE_Y = P["hinge"]
    GILL_S = P["gill"]
    EYE_AT = (P["eye"][0], P["eye"][1])
    hs, hy, ym = HINGE_S, HINGE_Y, P["mouth"]

    def roof(s):
        """The line of the mouth: the flat underside of the upper snout."""
        return lerp(ym, hy, min(s / hs, 1.0))

    def body_bot(s):
        return lerp(roof(s), bot(s), smooth(hs - 0.004, hs + 0.022, s))
    BODY_SKIN = Section(
        0.0, 0.895, top, body_bot, hw,
        lambda s: lerp(0.3, 0.5, smooth(hs, hs + 0.08, s)),
        lambda s: lerp(2.0, P.get("sharp", 1.75), smooth(GILL_S * 0.5, GILL_S * 1.2, s)),
        lambda s: lerp(3.2, P.get("sharp", 1.75) + 0.15, smooth(hs, hs + 0.06, s)))
    first = min(0.004, hs * 0.1)
    last = hs + 0.05

    def jaw_bot(s):
        return bot(s) + 0.006 * smooth(hs + 0.004, hs + 0.03, s)

    def jaw_top(s):
        if s <= hs:
            return max(roof(s) + 0.002, jaw_bot(s) + 0.003)
        return lerp(roof(hs) + 0.002, jaw_bot(s) + 0.001, smooth(hs, last, s))

    def jaw_hw(s):
        return 0.92 * hw(s) * min(1.0, max(s - first, 0.0) / 0.004) ** 0.5 * (1.0 - smooth(hs + 0.012, last, s))
    JAW_SKIN = Section(first, last, jaw_top, jaw_bot, jaw_hw, lambda s: 0.75, lambda s: 3.5, lambda s: 2.0)
    depth = max(top(i / 200.0) - bot(i / 200.0) for i in range(40, 140))
    width = 2.0 * max(hw(i / 200.0) for i in range(20, 140))
    P["told"] = "hinge_s=%.4f hinge_y=%.4f gill_s=%.4f eye=(%.4f, %.4f) depth=%.4f m width=%.4f m" % (
        HINGE_S, HINGE_Y, GILL_S, EYE_AT[0], EYE_AT[1], depth * LENGTH, width * LENGTH)
    P["throat"] = throat_knots()


def gill_edge(h):
    """Where the gill cover's rear edge is (s) at a height on the body (0 belly to 1 back): a crescent."""
    return GILL_S - 0.22 * (h - 0.45) ** 2


def gill_plate(s, h):
    """How far the gill cover stands out from the skin behind it (body lengths)."""
    edge = gill_edge(h)
    band = smooth(0.1, 0.22, h) * (1.0 - smooth(0.66, 0.8, h))
    behind = 1.0 - smooth(edge - 0.004, edge + 0.008, s)
    return 0.0035 * smooth(GILL_S - 0.08, GILL_S - 0.018, s) * behind * band


def body_x(s, y):
    """How far out the body's skin is at height y, gill cover and all."""
    top, bot = BODY_SKIN.top(s), BODY_SKIN.bot(s)
    h = (y - bot) / max(top - bot, 1e-9)
    return BODY_SKIN.x_at(s, y) + gill_plate(s, h)


def body_frame(s, y):
    """A place on the body's right side: the point, the way out of the skin there, and the way up along it."""
    e = 0.002
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
        # (a lining, seen from inside, as the throat is: not a closed solid; its faces are wound by hand to face
        # `lining(point)`, a point on the tunnel's middle line, and `done` checks that instead)
        self.lining = None

    def add(self, p, uv, uv2, colour):
        self.verts.append(Vector(p))
        self.data.append((uv, uv2, colour))
        return len(self.verts) - 1

    def loft(self, rings):
        for a, b in zip(rings, rings[1:]):
            n = len(a)
            for j in range(n):
                self.faces.append((a[j], a[(j + 1) % n], b[(j + 1) % n], b[j]))

    def mirrored(self, name, flip):
        other = Part(name)
        for p, d in zip(self.verts, self.data):
            other.add((-p.x, p.y, p.z), *flip(d))
        other.faces = list(self.faces)
        return other

    def face_towards(self, face, target):
        """Adds a face wound so that it faces the point `target` (for a lining)."""
        a, b, c = (self.verts[i] for i in face[:3])
        n = (b - a).cross(c - a)
        if n.length < 1e-14 and len(face) > 3:
            n = (c - a).cross(self.verts[face[3]] - a)
        middle = sum((self.verts[i] for i in face), Vector()) / len(face)
        self.faces.append(tuple(face) if n.dot(target - middle) > 0.0 else tuple(reversed(face)))

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
                    # (a line that grazes an edge counts it twice: ask again along two lines a little aside, out of
                    # the same face, and go by the most of the three; added 2026-11-18 for the small gill arches)
                    odd = 1
                    for lean in (Vector((0.13, 0.07, 0.0)), Vector((-0.05, 0.11, 0.09))):
                        way = (f.normal + lean - f.normal * f.normal.dot(lean)).normalized()
                        if way.dot(f.normal) <= 0.0:
                            continue
                        at = f.calc_center_median() + f.normal * 2e-6
                        n = 0
                        while n < 40:
                            hit = tree.ray_cast(at, way)
                            if hit[0] is None:
                                break
                            n += 1
                            at = hit[0] + way * 2e-6
                        odd += n % 2
                    if odd >= 2:
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
            # (a face that closes to a point at the end of a skin has corners in one place: the weld below
            # makes a triangle of it or drops it)
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
        if self.lining is not None:
            # (a lining: every face must face the tunnel's middle line, as it was wound)
            bm.normal_update()
            wrong = 0
            for f in bm.faces:
                c = f.calc_center_median()
                g = Vector((c.x, c.z, -c.y)) / LENGTH
                axis = self.lining(g)
                towards = to_b(axis - g)
                if f.normal.dot(towards) <= 0.0:
                    wrong += 1
            out = []
            for f in bm.faces:
                out.append([(loop.vert.co.copy(), tuple(loop[uv].uv), tuple(loop[uv2].uv), tuple(loop[colour]))
                            for loop in f.loops])
            counted = len(bm.faces)
            bm.free()
            return out, wrong, counted
        # (where a skin closes to a line on the middle plane, or a fin on that plane thins to nothing at its
        # leading tip, a four-cornered face has three corners in that plane: cut it from its fourth corner, or
        # whoever cuts it in two later may leave a triangle lying flat in the plane, back to back with its twin)
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


def flip_side(d):
    return d[0], (-d[1][0], d[1][1]), d[2]


def skin(part, section, places, half, kind):
    """Lofts a Section into a Part. `kind` is BODY or JAW."""
    rings = []
    for s in places:
        side, whole = section.outline(s, half)
        top, bot = section.top(s), section.bot(s)
        ring = []
        ends = s <= section.first or s >= section.last
        # (down the right side and back up the left; the belly line is there twice, once for each side)
        for j in list(range(half + 1)) + list(range(half, 0, -1)):
            x, y, arc = side[j]
            sign = 1.0 if len(ring) <= half else -1.0
            h = (y - bot) / max(top - bot, 1e-9)
            yc = bot + section.at(s)[3] * (top - bot)
            if kind == BODY:
                x += gill_plate(s, h) * (0.0 if ends else 1.0)
                # the roof of the mouth: the flat underside of the upper snout, ahead of the jaw's hinge
                roof = smooth(0.4, 0.12, (y - bot) / max(yc - bot, 1e-9)) * smooth(HINGE_S + 0.014, HINGE_S - 0.006, s)
                ring.append(part.add((sign * x, y, s - 0.5), (s, 1.0 - h),
                                     (sign * arc * LENGTH, 1.0 - whole * LENGTH), (0.0, 0.0, roof)))
            else:
                inside = smooth(0.55, 0.92, (y - yc) / max(top - yc, 1e-9)) if y > yc else 0.0
                inside *= smooth(HINGE_S + 0.02, HINGE_S - 0.002, s)
                ring.append(part.add((sign * x, y, s - 0.5), (s, 1.0 - h),
                                     (sign * x * LENGTH, 1.0), (JAW / 10.0, 0.0, inside)))
        rings.append(ring)
    part.loft(rings)


def body_places(low):
    if GAME:
        # (rings where the outline bends, seen from the side and from above; and at the mouth's hinge, the eye
        # and the gill cover's edge)
        hs, gs, es = HINGE_S, GILL_S, EYE_AT[0]
        ball = P["eye"][2]
        return spread(lambda s: [(s, BODY_SKIN.top(s)), (s, BODY_SKIN.bot(s)), (s, P["sil_hw"](s))],
                      0.0, BODY_SKIN.last, GAME_BODY_RINGS,
                      (hs - 0.006, hs + 0.008, hs + 0.022, es - ball * 0.6, es + ball * 0.6,
                       gs - 0.03, gs - 0.012, gs + 0.004))
    head = 6 if low else 24
    rest = 10 if low else 44
    behind = GILL_S + 0.014
    places = [behind * (i / head) ** 1.35 for i in range(head)]
    places += [lerp(behind, BODY_SKIN.last, i / rest) for i in range(rest + 1)]
    return places


def eye(low):
    """The right eye: a dome set in the side of the head."""
    global EYE_SKIN
    part = Part("eye")
    at, out, up = body_frame(*EYE_AT)
    # (where the eye sits on the skin: the shader grows a cartoon eye about this point)
    EYE_SKIN = at.copy()
    along = up.cross(out).normalized()
    ball, stands, shown = P["eye"][2:]
    # (the dome goes on under the skin: what shows is `shown` of how far across it is made)
    seen = math.sqrt(1.0 - (1.0 - stands / ball) ** 2)
    reach = math.asin(min(seen / shown, 0.999))
    centre = at - out * (ball - stands)
    rows = 2 if (low or GAME) else 6
    around = 24 if GAME else (6 if low else 18)
    rings = []
    for i in range(rows + 1):
        a = reach * i / rows
        ring = []
        for k in range(around):
            q = TAU * k / around
            p = centre + out * (ball * math.cos(a)) + (up * math.cos(q) + along * math.sin(q)) * (ball * math.sin(a))
            # (UV: where it is on the eye's round face, seen straight on: its middle at (0.5, 0.5); where the
            # eye meets the skin is 0.644 of the way out)
            across = 0.5 * 0.644 * math.sin(a) / seen
            ring.append(part.add(p, (0.5 + across * math.cos(q), 1.0 - (0.5 + across * math.sin(q))), (0.0, 1.0),
                                 (EYE / 10.0, 0.0, 0.0)))
        rings.append(ring)
    # (closed behind, inside the head)
    back = centre + out * (ball * math.cos(reach) - 0.003)
    rings.append([part.add(back, (0.5 + 0.5 * math.cos(TAU * k / around), 0.5 - 0.5 * math.sin(TAU * k / around)),
                           (0.0, 1.0), (EYE / 10.0, 0.0, 0.0)) for k in range(around)])
    part.loft(rings)
    return part


def cheek_spine(low):
    """The spine at the lower corner of the cheek (the angelfishes' mark), lying back along the gill cover."""
    part = Part("spine")
    s0, y0, long = P["spine"]
    stations = 3 if low else (4 if GAME else 8)
    around = 4 if low else (6 if GAME else 8)
    rings = []
    for i in range(stations + 1):
        u = i / stations
        s = s0 + long * u
        y = y0 - 0.22 * long * u
        at, out, up = body_frame(s, y)
        back = Vector((0.0, -0.22, 1.0)).normalized()
        up = out.cross(back).normalized()
        thick = 0.0085 * (1.0 - u) ** 0.8 * min(1.0, u / 0.12 + 0.35)
        ring = []
        for k in range(around):
            q = TAU * k / around
            p = at + out * (0.0015 + 0.004 * u) + up * (thick * math.cos(q)) + out * (thick * 0.8 * math.sin(q))
            ring.append(part.add(p, (u, 1.0 - 0.5), (0.0, 1.0), (SPINE / 10.0, 0.0, 0.0)))
        rings.append(ring)
    part.loft(rings)
    # (closed at its root)
    middle = sum((part.verts[i] for i in rings[0]), Vector()) / around
    hub = part.add(middle, (0.0, 0.5), (0.0, 1.0), (SPINE / 10.0, 0.0, 0.0))
    for k in range(around):
        part.faces.append((rings[0][(k + 1) % around], rings[0][k], hub))
    return part


def reach_x(s, y):
    """How far out the fish is at (s, y): the body's skin or the jaw's, whichever is further (0 outside both)."""
    out = 0.0
    if BODY_SKIN.bot(s) < y < BODY_SKIN.top(s):
        out = body_x(s, y)
    if JAW_SKIN.first <= s <= JAW_SKIN.last and JAW_SKIN.bot(s) < y < JAW_SKIN.top(s):
        out = max(out, JAW_SKIN.x_at(s, y))
    return out


def throat_at(s):
    """The throat's oval at s (between its knots, straight lines): (height of its middle, half height, half width)."""
    knots = P["throat"]
    if s <= knots[0][0]:
        return knots[0][1:]
    for a, b in zip(knots, knots[1:]):
        if s <= b[0]:
            t = (s - a[0]) / (b[0] - a[0])
            return tuple(lerp(a[i], b[i], t) for i in (1, 2, 3))
    return knots[-1][1:]


def throat_margin(s, yc, h, w):
    """The least gap (body lengths) between the throat's oval at s and the outside of the fish or an eyeball."""
    at, out, _ = body_frame(*EYE_AT)
    ball, stands = P["eye"][2], P["eye"][3]
    centre = at - out * (ball - stands)
    least = 1e9
    for k in range(32):
        a = TAU * k / 32
        x, y = w * math.sin(a), yc + h * math.cos(a)
        least = min(least, reach_x(s, y) - x)
        if k == 0 or k == 16:
            # (the oval's top and bottom must be inside the fish's outline at that place too)
            least = min(least, (BODY_SKIN.top(s) - y) if k == 0 else (y - P["sil_bot"](s)))
        least = min(least, (Vector((abs(x), y, s - 0.5)) - centre).length - ball)
    return least


def throat_knots():
    """The throat's ovals: from inside the mouth a little ahead of the hinge, where its top is the closed mouth's
    line and it reaches down into the jaw, back to just ahead of the gill cover's edge, sloping gently down: a
    tube not much wider than the open mouth (so that the gills in it are in sight through the mouth), below the
    eyes, made smaller where it would come near the outside."""
    hs, hy = HINGE_S, HINGE_Y
    s0, s1 = hs - 0.015, GILL_S - 0.01
    top, bot = P["sil_top"], P["sil_bot"]
    eye_lim = EYE_AT[1] - P["eye"][2] - 0.008
    hi0 = hy + 0.003
    lo0 = bot(s0) + 0.3 * (hi0 - bot(s0))
    yc0, h0 = 0.5 * (hi0 + lo0), 0.5 * (hi0 - lo0)
    w0 = 0.5 * reach_x(s0, yc0)
    knots = []
    for k in range(THROAT_KNOTS):
        s = s0 + (s1 - s0) * (k / (THROAT_KNOTS - 1)) ** 1.6
        depth = top(s) - bot(s)
        hi_lim = min(top(s) - 0.3 * depth, eye_lim)
        lo_lim = bot(s) + 0.25 * max(hi_lim - bot(s), 0.0)
        h = min(1.8 * h0, 0.5 * (hi_lim - lo_lim))
        yc = min(max(yc0 - 0.12 * (s - s0), lo_lim + h), hi_lim - h)
        w = min(0.5 * reach_x(s, yc), 1.8 * w0)
        for _ in range(60):
            if throat_margin(s, yc, h, w) > 0.0025:
                break
            w *= 0.92
            h *= 0.96
        knots.append((s, yc, h, w))
    # (and between the knots, where the straight lines run: the two knots either side of a place too close to the
    # outside made smaller)
    P["throat"] = knots
    for _ in range(60):
        tight = [s for s in (lerp(s0, s1, i / 60.0) for i in range(61)) if throat_margin(s, *throat_at(s)) < 0.0015]
        if not tight:
            break
        for s in tight:
            for i in range(THROAT_KNOTS - 1):
                if knots[i][0] <= s <= knots[i + 1][0]:
                    for j in (i, i + 1):
                        k0, yc, h, w = knots[j]
                        knots[j] = (k0, yc, h * 0.97, w * 0.94)
        P["throat"] = knots
    return knots


def throat(level):
    """The throat's lining: the tunnel's wall seen from inside (dark, `inside` 1, of the body's part, vertex
    colour green 1), open at the front, closed at the back by a shallow dome."""
    part = Part("throat")
    knots = P["throat"]
    strips = THROAT_STRIPS[level]
    places = [knots[0][0]]
    for a, b in zip(knots, knots[1:]):
        places += [lerp(a[0], b[0], (i + 1) / strips) for i in range(strips)]
    n = THROAT_ROUND[level]
    rings = []
    for s in places:
        yc, h, w = throat_at(s)
        rings.append([part.add((w * math.sin(TAU * j / n), yc + h * math.cos(TAU * j / n), s - 0.5), (s, 0.5),
                               (0.0, 1.0), (BODY / 10.0, 1.0, 1.0)) for j in range(n)])
    for i in range(len(rings) - 1):
        yc = throat_at(0.5 * (places[i] + places[i + 1]))[0]
        for j in range(n):
            q = (rings[i][j], rings[i][(j + 1) % n], rings[i + 1][(j + 1) % n], rings[i + 1][j])
            middle = sum((part.verts[x] for x in q), Vector()) / 4
            part.face_towards(q, Vector((0.0, yc, middle.z)))
    s1 = places[-1]
    yc, h, w = throat_at(s1)
    end = part.add((0.0, yc, s1 + 0.4 * min(h, w) - 0.5), (s1, 0.5), (0.0, 1.0), (BODY / 10.0, 1.0, 1.0))
    for j in range(n):
        part.face_towards((rings[-1][j], rings[-1][(j + 1) % n], end), Vector((0.0, yc, s1 - 0.5 - 1.0)))

    def axis(g):
        s = g.z + 0.5
        if s > s1 - 1e-6:
            return Vector((0.0, yc, g.z - 1.0))
        return Vector((0.0, throat_at(s)[0], g.z))
    part.lining = axis
    return part


def gills(level):
    """Four gill arches a side in the throat, each a closed bar (part GILL) that follows the throat's wall from
    low on its floor round its side and up towards its roof, its top leaning back: a bar, pale gill rakers on its
    front, a fringe of deep red filaments behind it out to the wall (the full model's toothed, in bunches). UV.x:
    0 the rakers along its inner edge, 0.3 the bar against the wall, 1 the filaments' tips; UV.y: the arch's number (0 the front one) plus
    how far up it (0 to 1). Nothing of them is outside the throat."""
    part = Part("gills")
    knots = P["throat"]
    s0, s1 = knots[0][0], knots[-1][0]
    first, last = s0 + 0.35 * (s1 - s0), s1 - 0.12 * (s1 - s0)
    gap = (last - first) / 3.0
    steps = GILL_STEPS[level]
    for k in range(4):
        sa = first + gap * k
        yc, h, w = throat_at(sa)
        rings = []
        for i in range(steps + 1):
            t = i / steps
            theta = math.pi * (0.85 - 0.65 * t)
            z = sa + 0.25 * gap * t
            yc, h, w = throat_at(z)
            wall = Vector((w * math.sin(theta), yc + h * math.cos(theta), z - 0.5))
            inward = Vector((-wall.x, yc - wall.y, 0.0)).normalized()
            back = Vector((0.0, 0.0, 1.0))
            # (each point: how far in from the wall, in halves of the throat's narrower size there; how far
            # back, in gaps between two arches; and its UV.x)
            if level == "full":
                tip = 0.45 if i % 2 == 0 else 0.33
                outline = [(0.08, -0.12, 0.3)]
                outline += [(1.1 + 0.2 * math.cos(math.radians(a)), 0.12 * math.sin(math.radians(a)), u)
                            for a, u in ((-120.0, 0.06), (-60.0, 0.0), (0.0, 0.1), (60.0, 0.3), (120.0, 0.4))]
                outline.append((0.25, tip, 1.0))
            else:
                outline = [(0.08, -0.12, 0.3), (1.3, 0.0, 0.0), (0.25, 0.45, 1.0)]
            reach = 0.5 * min(w, h)
            rings.append([part.add(wall + inward * (a * reach) + back * (b * gap), (u, k + 0.98 * t), (0.0, 1.0),
                                   (GILL / 10.0, 0.0, 0.0)) for a, b, u in outline])
        part.loft(rings)
        for ring, flip in ((rings[0], True), (rings[-1], False)):
            middle = sum((part.verts[x] for x in ring), Vector()) / len(ring)
            hub = part.add(middle, (0.3, k + (0.0 if flip else 0.98)), (0.0, 1.0), (GILL / 10.0, 0.0, 0.0))
            for j in range(len(ring)):
                face = (ring[j], ring[(j + 1) % len(ring)], hub)
                part.faces.append(tuple(reversed(face)) if flip else face)
    return part


def fin(name, kind, rays, base, direction, length, normal, thick, cols, rows, ridges, ts=None):
    """A fin: `rays` rays fanned from the line `base(t)` (t 0 its leading edge to 1 its trailing edge), each
    going the way `direction(t)` for `length(t)`; flat, facing `normal`; `thick` at its root; `cols` strips
    across it and `rows` along its rays (or, for the game model, strips between the places `ts`)."""
    part = Part(name)
    normal = normal.normalized()
    left, right = [], []
    if ts is not None:
        cols = len(ts) - 1
    for i in range(cols + 1):
        t = ts[i] if ts is not None else i / cols
        b, d, long = base(t), direction(t).normalized(), length(t)
        ridge = 0.5 + 0.5 * math.cos(TAU * (t * rays - 0.5)) if (rays > 1 and ridges) else 0.0
        edge = min(1.0, t / 0.06) ** 0.5 * min(1.0, (1.0 - t) / 0.1) ** 0.5
        a, c = [], []
        for j in range(rows + 1):
            r = j / rows
            taper = 1.0 - r
            th = edge * (taper ** 0.5) * (thick * (0.1 + 0.9 * taper ** 1.6) + 0.0009 * ridge * smooth(0.0, 0.14, r))
            mid = b + d * (long * r)
            data = ((r, 1.0 - t * rays), (normal.x, 1.0 - normal.y), (kind / 10.0, 0.0, normal.z * 0.5 + 0.5))
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


def turn(d0, d1, t):
    """From one direction round to another."""
    d0, d1 = d0.normalized(), d1.normalized()
    angle = d0.angle(d1)
    return (d0 * math.sin((1.0 - t) * angle) + d1 * math.sin(t * angle)) / math.sin(angle)


def clearance(part, root, swing):
    """The least gap (mm) between a pectoral fin and the body's side at the inward end of its stroke: every
    point of the fin from a third of the way out, turned `swing` radians in towards the body about the upright
    line through `root` (as the shader rows it), against the body's skin at its height."""
    least = 1e9
    c, sn = math.cos(-swing), math.sin(-swing)
    for p, d in zip(part.verts, part.data):
        r = d[0][0]
        if r < 0.35:
            continue
        dx, dz = p.x - root.x, p.z - root.z
        q = Vector((root.x + dx * c + dz * sn, p.y, root.z - dx * sn + dz * c))
        s = q.z + 0.5
        if s < BODY_SKIN.last and BODY_SKIN.bot(s) < q.y < BODY_SKIN.top(s):
            least = min(least, (q.x - body_x(s, q.y)) * LENGTH * 1000.0)
    return least if least < 1e8 else float("inf")


def edge_places(base, direction, length, a, b, n, forced=()):
    """The game model's places across a fin, from t = a to b: closer where its edge bends, seen from the side."""
    def tip(t):
        p = base(t) + direction(t).normalized() * length(t)
        return [(p.z, p.y)]
    return spread(tip, a, b, n, forced)


def middle_fin(name, kind, spec, up, low, low_cols):
    """The dorsal fin (up 1) or the anal fin (up -1)."""
    s0, s1, rays, spines, notch = spec["s0"], spec["s1"], spec["rays"], spec["spines"], spec["notch"]
    long = curve(spec["len"])
    angle = curve(spec["ang"])
    line = BODY_SKIN.top if up > 0 else BODY_SKIN.bot

    def length(t):
        k = t * rays
        out = long(t)
        if not low and k < spines:
            # (each spine a point, the skin dipping between)
            out *= 1.0 - notch * (0.5 - 0.5 * math.cos(TAU * k))
        return out

    def base(t):
        return Vector((0.0, line(lerp(s0, s1, t)) - up * 0.01, lerp(s0, s1, t) - 0.5))

    def direction(t):
        return Vector((0.0, up * math.sin(math.radians(angle(t))), math.cos(math.radians(angle(t)))))
    if GAME:
        # (the spines as the full model has them, a place at each point and each dip; the soft rays fewer, closer
        # where the edge bends)
        ts = [k / (2.0 * rays) for k in range(2 * spines)]
        ts += edge_places(base, direction, length, spines / rays, 1.0,
                          GAME_SOFT[0 if up > 0 else 1])
        return fin(name, kind, rays, base, direction, length, Vector((1.0, 0.0, 0.0)), 0.009, 0, 2, False, ts)
    return fin(
        name, kind, rays, base, direction,
        length, Vector((1.0, 0.0, 0.0)), 0.009, low_cols if low else rays * 2, 2 if low else 6, not low)


def fins(low):
    global PEC_ROOT
    made = []
    made.append(middle_fin("dorsal", DORSAL, P["dorsal"], 1.0, low, 9))
    made.append(middle_fin("anal", ANAL, P["anal"], -1.0, low, 5))
    if P.get("filament"):
        # The threadfin's thread, trailing from the soft dorsal fin (how pointed 0: a strip); the bannerfish's
        # banner, a long pennant (how pointed 1).
        f0, f1, f_long, f_angle, pointed = P["filament"]
        way = Vector((0.0, math.sin(math.radians(f_angle)), math.cos(math.radians(f_angle))))

        def f_length(t):
            a = abs(2.0 * t - 1.0)
            return f_long * lerp(1.0 - 0.12 * a * a, 0.22 + 0.78 * (1.0 - a) ** 0.8, pointed)
        made.append(fin(
            "filament", FILAMENT, 3,
            lambda t: Vector((0.0, BODY_SKIN.top(lerp(f0, f1, t)) - 0.01, lerp(f0, f1, t) - 0.5)),
            lambda t: way, f_length, Vector((1.0, 0.0, 0.0)), 0.014 if pointed < 0.5 else 0.011,
            (2 if pointed < 0.5 else 4) if GAME else (2 if low else 6), 5 if GAME else (3 if low else 12), False))
    # The tail: small, square-ended or a little rounded.
    t_s, t_spread, t_round = P["tail"]

    def tail_base(t):
        return Vector((0.0, lerp(PED, -PED, t), t_s + 0.012 - 0.02 * (2.0 * t - 1.0) ** 2 - 0.5))

    def tail_long(t):
        a = abs(2.0 * t - 1.0)
        reach = (0.5 - tail_base(t).z) / math.cos(math.radians(t_spread * a))
        return reach * (1.0 - t_round * a * a - 0.05 * smooth(0.8, 1.0, a) - max(-t_round, 0.0) * 2.0 * (1.0 - a * a))
    def tail_way(t):
        return Vector((0.0, math.sin(math.radians(t_spread * (1.0 - 2.0 * t))), math.cos(math.radians(t_spread * (1.0 - 2.0 * t)))))
    if GAME:
        made.append(fin("tail", TAIL, 17, tail_base, tail_way, tail_long, Vector((1.0, 0.0, 0.0)), 0.016, 0, 3, False,
                        edge_places(tail_base, tail_way, tail_long, 0.0, 1.0, GAME_TAIL)))
    else:
        made.append(fin(
            "tail", TAIL, 17, tail_base, tail_way,
            tail_long, Vector((1.0, 0.0, 0.0)), 0.016, 6 if low else 34, 2 if low else 6, not low))

    # The paired fins, the right one of each (the left is its mirror picture).
    def on_body(s, y, sunk=0.003):
        return Vector((max(body_x(s, y) - sunk, 0.0), y, s - 0.5))
    pv, pv_long = P["pelvic"]
    belly = BODY_SKIN.bot(pv)
    p0, p1 = on_body(pv, belly + 0.016), on_body(pv + 0.04, BODY_SKIN.bot(pv + 0.04) + 0.012)
    d0, d1 = Vector((0.16, -0.82, 0.55)), Vector((0.1, -0.3, 0.95))
    pelvic = fin(
        "pelvic", PELVIC, 6, lambda t: p0.lerp(p1, t), lambda t: turn(d0, d1, t),
        lambda t: pv_long * (1.0 - 0.6 * t ** 0.9) * (0.9 + 0.1 * smooth(0.0, 0.16, t)),
        d0.cross(d1), 0.008, 3 if GAME else (2 if low else 12), 2 if (low or GAME) else 5, not (low or GAME))
    made += [pelvic, pelvic.mirrored("pelvic_left", flip_side)]
    # The pectoral fins: what it rows with. Rounded paddles, held out from the body.
    pc_y, pc_long = P["pectoral"]
    q0, q1 = on_body(GILL_S + 0.012, pc_y), on_body(GILL_S + 0.018, pc_y - 0.045)
    e0, e1 = Vector((0.56, 0.3, 0.77)), Vector((0.5, -0.52, 0.7))
    pectoral = fin(
        "pectoral", PECTORAL, 14, lambda t: q0.lerp(q1, t), lambda t: turn(e0, e1, t),
        lambda t: pc_long * (0.62 + 0.38 * math.sin(math.pi * (0.12 + 0.6 * t)) ** 0.8) * (1.0 - 0.3 * t ** 2),
        e0.cross(e1), 0.007, 6 if GAME else (3 if low else 28), 2 if (low or GAME) else 6, not (low or GAME))
    made += [pectoral, pectoral.mirrored("pectoral_left", flip_side)]
    PEC_ROOT = (q0 + q1) * 0.5
    if not low:
        print("CLEARANCE %s pectoral fin to body, at the inward end of its stroke: %.1f mm" % (
            P["name"] + (" (game)" if GAME else ""), clearance(pectoral, PEC_ROOT, 0.3)))
    return made


def make(name, low, game=False):
    """One model: the full one, the low one, or (`game`) the game model, of Twilight Princess weight: the points
    spent where they shape the outline, the eye, the mouth and the fins' edges, few across the flat sides."""
    global GAME
    GAME = game
    parts = []
    body = Part("body")
    skin(body, BODY_SKIN, body_places(low), GAME_HALF if game else (4 if low else 13), BODY)
    parts.append(body)
    jaw = Part("jaw")
    if game:
        # (rings at the jaw's tip, either side of its hinge and where it runs back into the throat, which is
        # where the shader bends it)
        hs, first, last = HINGE_S, JAW_SKIN.first, JAW_SKIN.last
        jaw_places = [first, lerp(first, hs - 0.008, 0.45), hs - 0.008, hs, hs + 0.012, hs + 0.03, last]
        skin(jaw, JAW_SKIN, [s for s in jaw_places if first <= s <= last], 4, JAW)
    else:
        jaw_rings = 4 if low else 12
        skin(jaw, JAW_SKIN, [lerp(JAW_SKIN.first, JAW_SKIN.last, (i / jaw_rings) ** 1.25) for i in range(jaw_rings + 1)],
             2 if low else 6, JAW)
    parts.append(jaw)
    ball = eye(low)
    parts += [ball, ball.mirrored("eye_left", lambda d: d)]
    if P.get("spine"):
        spine = cheek_spine(low)
        parts += [spine, spine.mirrored("spine_left", lambda d: d)]
    parts += fins(low)
    # The throat and the gills (2026-11-18): last, and on the full model in a second surface, so that the first
    # (everything it had before) is exactly as it was.
    level = "game" if game else ("low" if low else "full")
    inner = [throat(level)]
    arches = gills(level)
    inner += [arches, arches.mirrored("gills_left", lambda d: d)]

    verts, faces, corners = [], [], []
    told = []
    wrong_all = 0
    second = 0
    for part in parts + inner:
        out, wrong, counted = part.done()
        told.append("%s %d/%d %s" % (part.name, wrong, counted,
                                     "facing away from the middle" if part.lining else "wrong"))
        wrong_all += wrong
        for face in out:
            first = len(verts)
            for co, uv, uv2, colour in face:
                verts.append(co)
                corners.append((uv, uv2, colour))
            faces.append(list(range(first, first + len(face))))
        if part in inner:
            second += len(out)
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
    material = bpy.data.materials.get(FAMILY) or bpy.data.materials.new(FAMILY)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.8, 0.72, 0.4, 1.0)
    material.diffuse_color = (0.8, 0.72, 0.4, 1.0)
    mesh.materials.append(material)
    if level == "full":
        inside = bpy.data.materials.get(FAMILY + "_throat") or bpy.data.materials.new(FAMILY + "_throat")
        inside.diffuse_color = (0.5, 0.05, 0.06, 1.0)
        mesh.materials.append(inside)
        for poly in mesh.polygons[len(mesh.polygons) - second:]:
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
    # (all but the gill arches: theirs stay apart at every face, so that each face of those small sharp-edged
    # bars has its own normals, none against it)
    for v in mesh.vertices:
        v.select = corners[v.index][2][0] < 0.95
    for e in mesh.edges:
        e.select = all(mesh.vertices[i].select for i in e.vertices)
    for poly in mesh.polygons:
        poly.select = all(mesh.vertices[i].select for i in poly.vertices)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.remove_doubles(threshold=1e-7)
    bpy.ops.object.mode_set(mode="OBJECT")
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    low_x = min(v.co.x for v in mesh.vertices), max(v.co.x for v in mesh.vertices)
    low_z = min(v.co.z for v in mesh.vertices), max(v.co.z for v in mesh.vertices)
    low_y = min(-v.co.y for v in mesh.vertices), max(-v.co.y for v in mesh.vertices)
    print("BUILT %s verts=%d tris=%d reach (m): x %.4f..%.4f, up %.4f..%.4f, along %.4f..%.4f" % (
        name, len(mesh.vertices), tris, low_x[0], low_x[1], low_z[0], low_z[1], low_y[0], low_y[1]))
    print("WINDING %s: %s: %s" % (name, "ok" if wrong_all == 0 else "INSIDE OUT", ", ".join(told)))
    print("THROAT %s: %d triangles of throat and gills; least gap to the outside or an eye %.2f mm" % (
        name, sum(len(p.vertices) - 2 for p in mesh.polygons[len(mesh.polygons) - second:]),
        1000.0 * LENGTH * min(throat_margin(s, *throat_at(s)) for s in
                              [lerp(P["throat"][0][0], P["throat"][-1][0], i / 40.0) for i in range(41)])))
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
    scene.render.resolution_x, scene.render.resolution_y = 1000, 800
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 100.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    # (Blender space: the nose is towards +Y, up is +Z; frames and targets in body lengths)
    views = [("right", (1, 0, 0), (0, 0, 0.03), 1.3), ("left", (-1, 0, 0), (0, 0, 0.03), 1.3),
             ("top", (0, -0.001, 1), (0, 0, 0), 1.2), ("under", (0, 0.001, -1), (0, 0, 0), 1.2),
             ("front", (0, 1, 0), (0, 0, 0.03), 0.9), ("back", (0, -1, 0), (0, 0, 0.03), 0.9),
             ("quarter", (0.7, 0.6, 0.35), (0, 0, 0.03), 1.2),
             ("head", (1, 0.15, 0.05), (0, 0.36, 0), 0.4), ("head_under", (0.5, 0.5, -0.7), (0, 0.4, -0.03), 0.3)]
    for low, obj in ((False, made[0]), (True, made[1])):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if low and view not in ("right", "quarter"):
                continue
            offset = Vector(direction).normalized() * 10.0
            camera.data.ortho_scale = frame * LENGTH
            camera.location = Vector(target) * LENGTH + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "X" if view in ("top", "under") else "Y").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % ("lo_" if low else "", view))
            bpy.ops.render.render(write_still=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    for kind in WANTED:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version = 0
        use(kind)
        name = "%s_%s" % (FAMILY, kind)
        full = make(name, False)
        low = make(name + "_lo", True)
        game = make(name + "_game", False, True)
        print("SHAPE %s: %s pec_root=(%.4f, %.4f, %.4f) eye_skin=(%.4f, %.4f, %.4f)" % (
            kind, P["told"], PEC_ROOT.x, PEC_ROOT.y, PEC_ROOT.z + 0.5, EYE_SKIN.x, EYE_SKIN.y, EYE_SKIN.z + 0.5))
        print("THROAT_KNOTS %s: %s" % (kind, ", ".join(
            "Vector4(%.4f, %.4f, %.4f, %.4f)" % k for k in P["throat"])))
        if "--game-only" not in ARGS:
            export_one(full, os.path.join(OUT, name + ".glb"))
            export_one(low, os.path.join(OUT, name + "_lo.glb"))
        export_one(game, os.path.join(OUT, name + "_game.glb"))
        # (in the .blend: the full model, the low one beside it, the game model on its other side)
        low.location.x = LENGTH
        game.location.x = -LENGTH
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, name + ".blend"))
        low.location.x = 0.0
        game.location.x = 0.0
        if PREVIEW:
            folder = os.path.join(PREVIEW, kind)
            os.makedirs(folder, exist_ok=True)
            render(folder, [full, low])


if __name__ == "__main__":
    main()
