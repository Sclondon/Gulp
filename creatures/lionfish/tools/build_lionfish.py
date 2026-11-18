"""Builds the red lionfish (creatures/lionfish) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/lionfish/tools/build_lionfish.py
    blender --background --python creatures/lionfish/tools/build_lionfish.py -- <preview folder>   # with pictures

Writes creatures/lionfish/models/lionfish.glb (the full model) and lionfish_lo.glb (far off, phones), and the
editable creatures/lionfish/tools/lionfish.blend (this folder has a .gdignore). Each model is one still mesh with
one surface: the shader (lionfish.gdshader) draws every marking, fans and folds its fins and spines, waves its
pectoral fins and soft fins and swings its lower jaw. It prints a WINDING line: the check that nothing is inside
out.

A red lionfish (Pterois volitans), 0.35 m from the tip of its snout to the edge of its tail, built from the species
(no picture was traced): a big head (more than a third of its length) with a large, upturned mouth and big eyes
set high; a body deep at the shoulder and narrowing to a slim tail wrist; a rounded tail. Thirteen long, separate
DORSAL SPINES, each a banded rod standing far above the back with its own flag of membrane down its back edge
(the membrane between them is cut almost to the root); a rounded soft dorsal fin behind them; an anal fin of three
spines and soft rays. Huge PECTORAL FINS spread to either side like wings, reaching back to the tail, their long
rays running on free beyond the membrane (feathery); long pelvic fins. Fleshy TABS: a leaf-like tentacle standing
over each eye and two small tabs on each side of the lower jaw.

THE MOUTH WORKS: ahead of the jaw's hinge the underside of the head is cut away up to the line of the mouth and
arched (the roof of the mouth), and the LOWER JAW (with its tabs) is a part of its own, a hollow scoop that shuts up
inside the upper lip and runs back into the throat; the shader turns it down about its hinge.

Everything below is in BODY LENGTHS (the whole fish is 1 long: `s` is how far along, 0 the tip of the snout, 1
the edge of the tail; heights are from its middle line), and is multiplied by LENGTH as it is written out. In
Godot: metres, Y up, X to its left side, its nose at -Z, its origin on its middle line half way along.

What a point is, for the shader: UV2.y the part (0 body, 1 lower jaw, 2 a dorsal spine with its flag, 3 the soft
dorsal and anal fins, 4 tail, 5 a pectoral fin, 6 a pelvic fin, 7 an eye, 8 a tab over an eye, 9 a tab on the
lower jaw). UV, on the body and jaw: x how far along (s), y how high on its side (1 the ridge of the back, 0 the
keel of the belly); on a fin or a tab: x from its root (0) to its edge or tip (1), y from its leading edge (0) to
its trailing edge (1); on a dorsal spine: x from its root (0) to its tip (1), y its number (0 the first to 12 the
last) plus 0.9 times how far across its flag (0 on the spine); on an eye: x from its middle (0) to its rim (1).
UV2.x, on the body and jaw: how much the point is inside the mouth (0 skin, 1 inside). (The glTF writer flips V:
what is written here is 1 - v, so that Godot reads v.)

The numbers marked "as the shader has it" are in lionfish.gdshader too: change one, change the other. The build
prints them (SHADER and SPINE ROOTS lines).

The way of building the body, jaw, eyes and soft fins (everything under the line below) is GameCommon's
parrotfish's (godot/parrotfish), itself from the snapper's; copied, not kept in step. The spines, their flags,
the tabs and the cut edges of the pectoral fins are this fish's own (`extras`, and `cut` on the paired fins).
"""

NAME = "lionfish"
LENGTH = 0.35
COLOUR = (0.7, 0.25, 0.2, 1.0)

# The body's outline: how far along, its top, its bottom, half its width, the height of its widest line.
PROFILE = [
    (0.0, -0.02, -0.02, 0.0, -0.02),
    (0.004, -0.008, -0.032, 0.012, -0.02),
    (0.012, 0.004, -0.044, 0.022, -0.02),
    (0.04, 0.036, -0.07, 0.038, -0.017),
    (0.08, 0.07, -0.098, 0.052, -0.013),
    (0.13, 0.1, -0.12, 0.062, -0.008),
    (0.2, 0.125, -0.136, 0.068, -0.003),
    (0.28, 0.14, -0.142, 0.068, 0.0),
    (0.37, 0.142, -0.136, 0.064, 0.0),
    (0.47, 0.128, -0.12, 0.056, 0.0),
    (0.57, 0.104, -0.098, 0.046, 0.0),
    (0.65, 0.078, -0.074, 0.036, 0.0),
    (0.71, 0.06, -0.057, 0.026, 0.0),
    (0.75, 0.055, -0.053, 0.018, 0.0),
    (0.78, 0.057, -0.055, 0.009, 0.0),
    (0.795, 0.004, -0.004, 0.001, 0.0),
]
# How round its cross-section is (1 an ellipse, less than 1 boxier).
POWER = 1.0

# As the shader has it: the jaw's hinge (how far along, how high), how the line of the mouth bows, the eye
# (how far along, how high, its radius), the gill cover's edge (its rearmost reach, at what height, how it curves).
HINGE = (0.1, -0.062)
MOUTH_BOW = 1.0
EYE_AT = (0.122, 0.05, 0.027)
EYE_BULGE = 0.3
GILL = (0.29, 0.0, 2.2)
GILL_STEP = 0.004
# The lips: how much they swell, and how wide the swelling is. Where the jaw's tip is, and how far it juts.
LIP = 0.08
LIP_WIDE = 0.008
JAW_FROM = 0.004
JAW_JUT = 0.0

# The dorsal spines: how many, the first's and the last's roots (how far along), how long each is (by its number,
# 0 the first to 1 the last; body lengths along the spine), how far each leans back (degrees from upright), how
# far up its spine its flag runs, and how far back the flag reaches at its root (a share of the gap to the next).
SPINES = {
    "count": 13, "from": 0.2, "to": 0.555,
    "long": [(0.0, 0.2), (0.2, 0.29), (0.45, 0.3), (0.7, 0.24), (1.0, 0.13)],
    "lean": [(0.0, 12.0), (1.0, 38.0)],
    "flag": 0.62, "flag_wide": 0.9, "radius": 0.0042, "sink": 0.012,
}
# The soft dorsal fin (behind the spines) and the anal fin: rounded.
DORSAL_FIN = {
    "from": 0.565, "to": 0.75, "spines": 0, "share": 0.0, "scallop": 0.0,
    "high": [(0.0, 0.05), (0.25, 0.1), (0.6, 0.105), (0.9, 0.07), (1.0, 0.03)],
    "lean": [(0.0, 30.0), (1.0, 60.0)],
    "thick": 0.006, "nt": 8, "nu": 24,
}
ANAL_FIN = {
    "from": 0.55, "to": 0.735, "spines": 3, "share": 0.25, "scallop": 0.12,
    "high": [(0.0, 0.05), (0.3, 0.11), (0.65, 0.105), (0.9, 0.07), (1.0, 0.03)],
    "lean": [(0.0, 30.0), (1.0, 60.0)],
    "thick": 0.006, "nt": 8, "nu": 24,
}
# (the tail's hinge, `root`, is as the shader has it)
TAIL_FIN = {
    "root": 0.78, "half": 0.036, "spread": 32.0,
    "reach": [(0.0, 0.16), (0.25, 0.198), (0.5, 0.215), (0.75, 0.198), (1.0, 0.16)],
    "thick": 0.01, "nt": 10, "nu": 20,
}
# `on`: where its root is (how far along, how high); `span`: the way its middle rays point (out, up, back);
# `chord`: the way its root runs; `fan`: the angles of its first and last rays from `span`, degrees.
# `rays` and `cut`: how many rays, and how deep its edge is cut back between them (the rays run on free).
PECTORAL_FIN = {
    "on": (0.285, -0.035), "span": (0.6, -0.1, 0.8), "chord": (0.0, -1.0, 0.15), "base": 0.06,
    "fan": (-58.0, 52.0),
    "reach": [(0.0, 0.33), (0.25, 0.49), (0.55, 0.5), (0.8, 0.41), (1.0, 0.27)],
    "rays": 15, "cut": 0.4,
    "thick": 0.008, "nt": 9, "nu": 0,
}
PELVIC_FIN = {
    "on": 0.3, "apart": 0.026, "span": (0.3, -0.6, 0.75), "chord": (0.0, 0.15, 1.0), "base": 0.035,
    "fan": (-5.0, 30.0),
    "reach": [(0.0, 0.17), (0.3, 0.19), (0.7, 0.15), (1.0, 0.1)],
    "rays": 6, "cut": 0.0,
    "thick": 0.006, "nt": 8, "nu": 8,
}
# The tabs: over each eye (how long, how wide, which way it stands: out, up, back) and on the lower jaw (where
# along, how far under the line of the mouth, how long, how wide).
BROW_TAB = {"long": 0.09, "wide": 0.026, "way": (0.3, 0.92, 0.25)}
CHIN_TABS = [(0.045, 0.013, 0.03, 0.013), (0.075, 0.016, 0.026, 0.011)]

# How finely each model is cut: points round the body, how much longer than the finest rings' steps its rings'
# steps are, how much of the fins' points, the jaw (rings, points round its keel, points across its hollow), the
# eye, the spines (sides round each, none for no rod, points along it, points across its flag), and on a fin whose
# edge is cut, where its points are between two rays (shares of the gap) and how many of its rays it has (a share).
FULL = {"around": 40, "step": 1.6, "fin": 1.0, "jaw": (20, 22, 9), "eye": (22, 6), "spine": (5, 12, 4), "per": (0.0, 0.07, 0.3, 0.5, 0.7, 0.93), "rays": 1.0}
LOW = {"around": 12, "step": 5.0, "fin": 0.25, "jaw": (6, 8, 3), "eye": (8, 2), "spine": (0, 4, 1), "per": (0.0, 0.5), "rays": 0.5}

SPINE, SOFT, TAB, CHIN_TAB = 2, 3, 8, 9


def spine_line(i):
    """Spine `i`: its root, the way it stands, how long it is."""
    count = SPINES["count"]
    k = i / (count - 1)
    s = SPINES["from"] + (SPINES["to"] - SPINES["from"]) * k
    root = Vector((0.0, TOP(s) - SPINES["sink"], s - 0.5))
    a = math.radians(Curve(SPINES["lean"])(k))
    return root, Vector((0.0, math.cos(a), math.sin(a))), Curve(SPINES["long"])(k)


def spine_point(i, t):
    root, way, long = spine_line(i)
    # (each spine bows back a little towards its tip)
    return root + way * (t * long) + Vector((0.0, 0.0, 0.05 * long * t * t))


def tube(m, part, name, centre, radius, ts, sides, uv):
    """A thin round rod along `centre(t)`, `radius(t)` thick, closed at its far end (its root is inside the body)."""
    rows = []
    for t in ts:
        c = centre(t)
        ahead = centre(min(1.0, t + 0.01)) - centre(max(0.0, t - 0.01))
        ahead.normalize()
        a = Vector((1.0, 0.0, 0.0))
        b = ahead.cross(a).normalized()
        row = []
        for k in range(sides):
            ang = k / sides * TAU
            p = c + (a * math.cos(ang) + b * math.sin(ang)) * radius(t)
            row.append((m.add(p, uv(t, k / sides), part), c))
        rows.append(row)
    for r in range(len(rows) - 1):
        for k in range(sides):
            n = (k + 1) % sides
            quad = (rows[r][k][0], rows[r][n][0], rows[r + 1][n][0], rows[r + 1][k][0])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, middle - (rows[r][k][1] + rows[r + 1][k][1]) * 0.5, name)
    tip = m.add(centre(1.0) + (centre(1.0) - centre(0.97)).normalized() * radius(1.0), uv(1.0, 0.0), part)
    last = rows[-1]
    for k in range(sides):
        n = (k + 1) % sides
        m.face((tip, last[k][0], last[n][0]), m.verts[tip] - last[k][1], name)


def spines(m, detail):
    """The thirteen dorsal spines, each a rod with a flag of membrane down its back edge."""
    sides, along, across = detail["spine"]
    count = SPINES["count"]
    gap = (SPINES["to"] - SPINES["from"]) / (count - 1)
    top = SPINES["flag"]
    for i in range(count):
        _, way, long = spine_line(i)
        back = Vector((0.0, -way.z, way.y))
        ts = lin(along)
        if sides:
            tube(m, SPINE, "spines", lambda t, i=i: spine_point(i, t),
                 lambda t: SPINES["radius"] * (1.0 - 0.8 * t), ts, sides, lambda t, u, i=i: (t, float(i)))
        # (with no rod, the flag's edge stands for the spine all the way up)
        least = 0.0005 if sides else 0.003
        if i == count - 1:
            wide = 0.5 * gap * SPINES["flag_wide"]
        else:
            wide = gap * SPINES["flag_wide"]

        def flag(t, u, i=i, back=back, wide=wide, least=least):
            # (the flag runs up the spine's back edge, broad at its root, narrowing to a point part way up; it
            # leans back and down from the spine; with no rod it runs on up the spine as a strip)
            f = t * (top if least < 0.001 else 1.0)
            reach = wide * max(0.0, 1.0 - f / top) ** 0.7 * (0.55 + 0.45 * math.sin(math.pi * min(1.0, f / top * 1.4)))
            return spine_point(i, f) + back * (u * max(reach, least)) - Vector((0.0, u * reach * 0.25, 0.0))

        blade(m, SPINE, "flags", flag, lambda p: p, SIDE, 0.003, lin(along * 0.8), lin(across),
              uv=lambda t, u, i=i: (t * (top if sides else 1.0), i + 0.9 * u))


def leaf(m, part, name, root, way, flat, long, wide, ts, us):
    """A fleshy tab: a thin leaf from `root` along `way`, broad in the plane of `way` and `flat`."""
    way = way.normalized()
    flat = (flat - way * flat.dot(way)).normalized()

    def point(t, u):
        w = wide * math.sin(math.pi * (0.12 + 0.88 * t)) ** 0.6 * (1.0 - 0.6 * t)
        return root + way * (t * long) + flat * ((u - 0.5) * w)

    blade(m, part, name, point, lambda p: p, way.cross(flat).normalized(), wide * 0.3, ts, us)


def extras(m, detail):
    """The spines and their flags, the tabs over the eyes and on the lower jaw."""
    spines(m, detail)
    f = detail["fin"]
    xe, ye, radius = EYE_AT
    for sx in (1.0, -1.0):
        w = BROW_TAB["way"]
        root = on_skin(xe + 0.006, ye + radius * 0.85, sx) - skin_normal(xe, ye + radius, sx) * 0.004
        leaf(m, TAB, "tabs", root, Vector((sx * w[0], w[1], w[2])), Vector((0.0, 0.0, 1.0)), BROW_TAB["long"],
             BROW_TAB["wide"], lin(10 * f), lin(4 * f))
        for s, under, long, wide in CHIN_TABS:
            y = mouth_y(s) - under
            p = on_skin(s, y, sx)
            root = Vector((p.x * JAW_FIT * 0.9, y, s - 0.5))
            leaf(m, CHIN_TAB, "chin tabs", root, Vector((sx * 0.6, -0.8, 0.15)), Vector((0.0, 0.0, 1.0)), long, wide,
                 lin(6 * f), lin(3 * f))


def report():
    """The numbers the shader needs: the spines' roots, how far they reach."""
    roots = []
    reach = 0.0
    for i in range(SPINES["count"]):
        root, _, _ = spine_line(i)
        roots.append("vec2(%.4f, %.4f)" % (root.z + 0.5, root.y))
        reach = max(reach, spine_point(i, 1.0).y)
    print("SPINE ROOTS (s, y): " + ", ".join(roots))
    print("SPINE REACH: tips up to %.4f body lengths (%.3f m) above the middle line" % (reach, reach * LENGTH))


# ---------------------------------------------------------------------------------------------------------------
# From here down: the way of building a reef fish (from GameCommon's parrotfish's; see the top).
# ---------------------------------------------------------------------------------------------------------------

import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "models")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = ARGS[0] if ARGS else ""

BODY, JAW, DORSAL, ANAL, TAIL, PECTORAL, PELVIC, EYE = range(8)
TAU = math.tau
# How far before and behind the jaw's hinge the corner of the mouth runs (as the shader has it).
CORNER_B = 0.012
CORNER_C = 0.035
# How much narrower than the head the lower jaw is: it shuts up inside the upper lip.
JAW_FIT = 0.97


def to_b(p):
    return Vector((p.x, -p.z, p.y))


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


class Curve:
    """A curve through points (x, y) that never overshoots them (Fritsch and Carlson); flat beyond its ends."""

    def __init__(self, points):
        self.xs = [p[0] for p in points]
        self.ys = [p[1] for p in points]
        xs, ys = self.xs, self.ys
        d = [(ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]) for i in range(len(xs) - 1)]
        m = [d[0]]
        for i in range(1, len(xs) - 1):
            if d[i - 1] * d[i] <= 0.0:
                m.append(0.0)
            else:
                w1 = 2.0 * (xs[i + 1] - xs[i]) + (xs[i] - xs[i - 1])
                w2 = (xs[i + 1] - xs[i]) + 2.0 * (xs[i] - xs[i - 1])
                m.append((w1 + w2) / (w1 / d[i - 1] + w2 / d[i]))
        m.append(d[-1])
        self.m = m

    def __call__(self, x):
        xs, ys, m = self.xs, self.ys, self.m
        x = max(xs[0], min(xs[-1], x))
        i = 0
        while i < len(xs) - 2 and x > xs[i + 1]:
            i += 1
        h = xs[i + 1] - xs[i]
        t = (x - xs[i]) / h
        a = (2 * t ** 3 - 3 * t ** 2 + 1) * ys[i] + (t ** 3 - 2 * t ** 2 + t) * h * m[i]
        b = (-2 * t ** 3 + 3 * t ** 2) * ys[i + 1] + (t ** 3 - t ** 2) * h * m[i + 1]
        return a + b


TOP = BOT = WIDE = MID = None
BODY_FROM = 0.0015
BODY_TO = 0.0


def prepare():
    """Makes the outline's curves from PROFILE (again, after a variant has changed it)."""
    global TOP, BOT, WIDE, MID, BODY_TO
    TOP = Curve([(p[0], p[1]) for p in PROFILE])
    BOT = Curve([(p[0], p[2]) for p in PROFILE])
    WIDE = Curve([(p[0], p[3]) for p in PROFILE])
    MID = Curve([(p[0], p[4]) for p in PROFILE])
    BODY_TO = PROFILE[-1][0]


def outline(s):
    """(top, bottom, half width, the height of its widest line) at `s`."""
    mid = MID(s)
    return max(TOP(s), mid + 0.0004), min(BOT(s), mid - 0.0004), max(WIDE(s), 0.0004), mid


def mouth_y(s):
    """The line of the mouth: from the tip of the snout back and down to the jaw's hinge, and on."""
    y0 = MID(0.0)
    hs, hy = HINGE
    if s <= hs:
        return y0 + (hy - y0) * (s / hs) ** MOUTH_BOW
    return hy + (hy - y0) * MOUTH_BOW / hs * (s - hs)


def gill_s(y):
    return GILL[0] - GILL[2] * (y - GILL[1]) ** 2


def angle_of(s, y):
    """The angle round the body (0 the ridge of the back, half a turn the keel) at which its skin is `y` high."""
    top, bot, _, mid = outline(s)
    c = (y - mid) / ((top - mid) if y >= mid else (mid - bot))
    return math.acos(max(-1.0, min(1.0, c)))


def full_point(s, angle, gill=True):
    """(how far to the side, how high) the skin is, as if the mouth were not cut into it."""
    top, bot, wide, mid = outline(s)
    c = math.cos(angle)
    sn = math.sin(angle)
    y = mid + c * ((top - mid) if c >= 0.0 else (mid - bot))
    side = math.copysign(abs(sn) ** POWER, sn) * wide
    # the lips: a swelling along the line of the mouth
    hs = HINGE[0]
    if LIP > 0.0 and s < hs * 1.2:
        swell = math.exp(-((y - mouth_y(s)) / LIP_WIDE) ** 2) * smooth(0.0, 0.012, s) * (1.0 - smooth(hs * 0.75, hs * 1.15, s))
        side *= 1.0 + LIP * swell
    # the gill cover: it stands a little proud of the body behind its edge
    if gill:
        behind = s - gill_s(y)
        if behind > 0.0 and wide > 0.006:
            mask = smooth(-0.97, -0.75, c) * (1.0 - smooth(0.35, 0.6, c))
            step = GILL_STEP * smooth(0.0, 0.004, behind) * math.exp(-behind / 0.035) * mask
            side *= 1.0 - step / wide
    return side, y


def roof_dome(s):
    top, bot, _, _ = outline(s)
    ym = mouth_y(s)
    return max(0.0, min(0.4 * (ym - bot), 0.45 * (top - ym)))


def body_point(s, angle):
    """A point of the skin and how much it is inside the mouth (0 skin, 1 the roof of the mouth). Ahead of the
    jaw's hinge the underside of the head is cut away up to the line of the mouth and arched: the roof."""
    side, y = full_point(s, angle)
    inside = 0.0
    hs = HINGE[0]
    if s < hs + CORNER_C:
        ym = mouth_y(s)
        wm = abs(full_point(s, angle_of(s, ym))[0]) + 1e-6
        # (the swollen lips stand wider than the mouth: what is cut away is kept within the mouth's width)
        cs = math.copysign(min(abs(side), wm), side)
        roof = ym + min(roof_dome(s), 0.8 * wm) * (1.0 - min(1.0, (cs / wm) ** 2))
        if y < roof:
            _, bot, _, _ = outline(s)
            blend = smooth(hs - CORNER_B, hs + CORNER_C, s)
            side = cs + (side - cs) * blend
            inside = (1.0 - blend) * smooth(0.0, 0.25 * (ym - bot) + 1e-5, ym - y)
            y = roof + (y - roof) * blend
    return Vector((side, y, s - 0.5)), inside


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        # per point: (uv, uv2)
        self.data = []
        # per face: the way it should face
        self.out = []
        self.count = {}

    def add(self, p, uv, part, extra=0.0):
        self.verts.append(p)
        self.data.append(((uv[0], 1.0 - uv[1]), (extra, 1.0 - part)))
        return len(self.verts) - 1

    def face(self, points, out, name):
        """A face wound so that its front (the side its points go round anticlockwise) is towards `out`."""
        ps = [self.verts[i] for i in points]
        n = Vector((0.0, 0.0, 0.0))
        for i in range(len(ps)):
            n += ps[i].cross(ps[(i + 1) % len(ps)])
        if n.length < 1e-14:
            return
        if n.dot(out) < 0.0:
            points = tuple(reversed(points))
        self.faces.append(tuple(points))
        self.out.append((Vector(out), name))
        self.count[name] = self.count.get(name, 0) + 1


def rings(detail):
    xs = []
    x = BODY_FROM
    for until, step in ((HINGE[0] + 0.04, 0.0035), (0.3, 0.006), (0.74, 0.013), (BODY_TO, 0.006)):
        step *= detail["step"]
        n = max(1, round((until - x) / step))
        for i in range(n):
            xs.append(x + (until - x) * i / n)
        x = until
    xs.append(BODY_TO)
    return xs


def body(m, detail):
    around = detail["around"]
    grid = []
    for s in rings(detail):
        row = []
        for c in range(around):
            angle = c / around * TAU
            p, inside = body_point(s, angle)
            row.append(m.add(p, (s, 0.5 + 0.5 * math.cos(angle)), BODY, inside))
        grid.append(row)
    for r in range(len(grid) - 1):
        # (faces look away from the middle of their own ring: the roof of the mouth looks down)
        centre = sum((m.verts[q].y for q in grid[r] + grid[r + 1])) / (2 * around)
        for c in range(around):
            n = (c + 1) % around
            quad = (grid[r][c], grid[r][n], grid[r + 1][n], grid[r + 1][c])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            if sum(m.data[q][1][0] for q in quad) > 1.0:
                # (the roof of the mouth: it looks down, however steeply it is arched)
                m.face(quad, Vector((0.0, -1.0, 0.0)), "roof")
            else:
                m.face(quad, Vector((middle.x, middle.y - centre, 0.0)), "body")
    # the tip of the snout and the end inside the tail: a fan each
    for row, s, way in ((grid[0], -0.002, -1.0), (grid[-1], BODY_TO + 0.002, 1.0)):
        y = sum(m.verts[q].y for q in row) / around
        tip = m.add(Vector((0.0, y, s - 0.5)), (s, 0.5), BODY)
        for c in range(around):
            m.face((tip, row[c], row[(c + 1) % around]), Vector((0.0, 0.0, way)), "body")


def jaw(m, detail):
    """The lower jaw: a part of its own, a scoop that shuts up inside the upper lip and runs back into the
    throat. The shader swings it down about its hinge."""
    hs = HINGE[0]
    s0 = JAW_FROM
    s1 = hs + CORNER_C + 0.03
    nr = detail["jaw"][0]
    nb = detail["jaw"][1]
    nt = detail["jaw"][2]
    grid = []
    for i in range(nr + 1):
        s = s0 + (s1 - s0) * (i / nr) ** 1.2
        top, bot, _, _ = outline(s)
        ym = mouth_y(s)
        ymj = min(ym + 0.15 * roof_dome(s) + 0.002, top - 0.0005)
        k = 1.0 - 0.14 * smooth(hs - CORNER_B, hs + CORNER_C, s)
        z = s - JAW_JUT * (1.0 - smooth(0.0, hs, s)) - 0.5
        a0 = angle_of(s, ymj)
        row = []
        low = ymj
        for j in range(nb + 1):
            angle = a0 + (TAU - 2.0 * a0) * j / nb
            side, y = full_point(s, angle, gill=False)
            y = ymj + (min(y, ymj) - ymj) * k
            low = min(low, y)
            row.append(m.add(Vector((side * JAW_FIT * k, y, z)), (s, 0.5 + 0.5 * math.cos(angle)), JAW, 0.0))
        xr = m.verts[row[0]].x
        hollow = 0.5 * (ymj - low)
        for j in range(1, nt):
            x = -xr + 2.0 * xr * j / nt
            y = ymj - hollow * (1.0 - (x / xr) ** 2)
            row.append(m.add(Vector((x, y, z)), (s, 0.5 + 0.5 * math.cos(a0)), JAW, 1.0))
        grid.append((row, ymj))
    count = nb + nt
    for r in range(len(grid) - 1):
        ra, ya = grid[r]
        rb, yb = grid[r + 1]
        for c in range(count):
            n = (c + 1) % count
            quad = (ra[c], ra[n], rb[n], rb[c])
            name = "jaw"
            if c >= nb:
                out = Vector((0.0, 1.0, 0.0))
                name = "jaw hollow"
            else:
                middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
                out = Vector((middle.x, middle.y - 0.5 * (ya + yb), 0.0))
                if out.length < 1e-9:
                    out = Vector((0.0, -1.0, 0.0))
            m.face(quad, out, name)
    for (row, _), way in ((grid[0], -1.0), (grid[-1], 1.0)):
        middle = sum((m.verts[q] for q in row), Vector()) / count
        tip = m.add(middle + Vector((0.0, 0.0, 0.005 * way)), (m.verts[row[0]].z + 0.5, 0.3), JAW, 0.0)
        for c in range(count):
            m.face((tip, row[c], row[(c + 1) % count]), Vector((0.0, 0.0, way)), "jaw")


def on_skin(s, y, sx=1.0):
    side, y2 = full_point(s, sx * angle_of(s, y), gill=False)
    return Vector((side, y2, s - 0.5))


def skin_normal(s, y, sx=1.0):
    out = (on_skin(s + 0.004, y, sx) - on_skin(s - 0.004, y, sx)).cross(on_skin(s, y + 0.004, sx) - on_skin(s, y - 0.004, sx))
    out.normalize()
    if out.x * sx < 0.0:
        out = -out
    return out


def eye(m, sx, detail):
    """A low dome lying on the skin of the head."""
    spokes, steps = detail["eye"]
    xe, ye, radius = EYE_AT
    here = on_skin(xe, ye, sx)
    out = skin_normal(xe, ye, sx)
    middle = m.add(here + out * (EYE_BULGE * radius * 1.1), (0.0, 0.0), EYE)
    last = None
    for k in range(1, steps + 1):
        r = k / steps
        row = []
        for sp in range(spokes):
            a = sp / spokes * TAU
            p = on_skin(xe + math.cos(a) * radius * r, ye + math.sin(a) * radius * r, sx)
            row.append(m.add(p + out * radius * (EYE_BULGE * (1.0 - r * r) + 0.02 * (1.0 - r)), (r, 0.0), EYE))
        for sp in range(spokes):
            n = (sp + 1) % spokes
            if last is None:
                m.face((middle, row[sp], row[n]), out, "eyes")
            else:
                m.face((last[sp], row[sp], row[n], last[n]), out, "eyes")
        last = row


def blade(m, part, name, point, place, facing, thick, ts, us, high=None, uv=None):
    """A fin: a thin closed blade. `point(t, u)` is a place in the fin's own flat (t 0 at its root to 1 at
    its edge, u 0 at its leading edge to 1 at its trailing edge), `place` puts that in the model, `facing`
    is the way one of its two skins faces. It is `thick` at its root, a foil across (nothing at either
    edge), thinning to nothing at its outer edge. `ts` and `us` are where its points are. `high(t, u)` is
    what goes in UV2.x, `uv(t, u)` what goes in UV (t, u if not given)."""
    for side in (1.0, -1.0):
        grid = []
        for t in ts:
            row = []
            for u in us:
                foil = 2.6 * math.sqrt(u) * (1.0 - u)
                swell = thick * (1.0 - t) ** 0.7 * foil
                p = place(point(t, u)) + facing * (side * swell * 0.5)
                row.append(m.add(p, uv(t, u) if uv else (t, u), part, high(t, u) if high else 0.0))
            grid.append(row)
        for ti in range(len(ts) - 1):
            for ui in range(len(us) - 1):
                m.face((grid[ti][ui], grid[ti][ui + 1], grid[ti + 1][ui + 1], grid[ti + 1][ui]), facing * side, name)


def lin(n, a=0.0, b=1.0):
    n = max(1, int(round(n)))
    return [a + (b - a) * i / n for i in range(n + 1)]


def upright(p):
    """A place in the flat of the middle fins (how far along, how high) in the model."""
    return Vector((0.0, p[1], p[0] - 0.5))


SIDE = Vector((1.0, 0.0, 0.0))


def median_fin(m, part, name, fin, way, detail):
    """The dorsal fin (way 1) or the anal fin (way -1): rays standing along the body's edge from `from` to `to`,
    as long as `high` says (by how far along the fin's root, 0 to 1), leaning back by `lean` degrees. Its first
    `share` is `spines` spines: the edge is cut in between them."""
    s0, s1 = fin["from"], fin["to"]
    tall = Curve(fin["high"])
    lean = Curve(fin["lean"])
    spines = fin.get("spines", 0)
    share = fin.get("share", 0.0)
    scallop = fin.get("scallop", 0.0)
    sink = 0.012
    edge = TOP if way > 0.0 else BOT

    def high(u):
        h = tall(u)
        if spines and u < share:
            h *= 1.0 - scallop * abs(math.sin(math.pi * u / share * spines)) ** 0.8
        return h

    def point(t, u):
        s = s0 + (s1 - s0) * u
        a = math.radians(lean(u))
        h = high(u) * t
        return (s + math.sin(a) * h, edge(s) + way * (-sink + (sink + math.cos(a) * high(u)) * t))

    def fold(t, u):
        return (sink + math.cos(math.radians(lean(u))) * high(u)) * t

    f = detail["fin"]
    if spines:
        per = 6 if f >= 0.99 else (3 if f > 0.4 else 2)
        us = lin(spines * per, 0.0, share)[:-1] + lin(fin["nu"] * f * (1.0 - share), share, 1.0)
    else:
        us = lin(fin["nu"] * f)
    blade(m, part, name, point, upright, SIDE, fin["thick"], lin(fin["nt"] * f), us,
          high=fold if way > 0.0 else None)


def tail_fin(m, detail):
    """The tail: rays fanning from the end of the tail wrist, each as long as `reach` says (0 the top ray to 1
    the bottom one)."""
    reach = Curve(TAIL_FIN["reach"])
    root, half = TAIL_FIN["root"], TAIL_FIN["half"]
    spread = math.radians(TAIL_FIN["spread"])

    def point(t, u):
        a = spread * (1.0 - 2.0 * u)
        length = reach(u) * t
        return (root + math.cos(a) * length, half * (1.0 - 2.0 * u) + math.sin(a) * length)

    f = detail["fin"]
    blade(m, TAIL, "tail", point, upright, SIDE, TAIL_FIN["thick"], lin(TAIL_FIN["nt"] * f), lin(TAIL_FIN["nu"] * f))


def paired_fin(m, part, name, fin, sx, detail):
    """A pectoral or a pelvic fin: rays fanning from a short root on the body; its edge cut back by `cut`
    between its `rays`."""
    root = Vector((sx * fin["at"][0], fin["at"][1], fin["at"][2] - 0.5))
    e1 = Vector((sx * fin["span"][0], fin["span"][1], fin["span"][2])).normalized()
    e2 = Vector((sx * fin["chord"][0], fin["chord"][1], fin["chord"][2]))
    e2 = (e2 - e1 * e2.dot(e1)).normalized()
    reach = Curve(fin["reach"])
    a0, a1 = math.radians(fin["fan"][0]), math.radians(fin["fan"][1])
    rays = fin.get("rays", 1)
    rays = max(2, round((rays - 1) * detail.get("rays", 1.0))) + 1
    per = detail.get("per", (0.0, 0.5))
    cut = fin.get("cut", 0.0)

    def point(t, u):
        a = a0 + (a1 - a0) * u
        length = reach(u) * t
        if cut > 0.0:
            # (between each two rays the edge is cut back; the rays run on free)
            between = abs((u * (rays - 1) + 0.5) % 1.0 - 0.5)
            length *= 1.0 - cut * smooth(0.04, 0.24 if len(per) > 2 else 0.5, between) * smooth(0.3, 1.0, t)
        return (math.cos(a) * length, fin["base"] * u + math.sin(a) * length)

    f = detail["fin"]
    if cut <= 0.0:
        us = lin(fin["nu"] * f)
    else:
        # (points close each side of every ray, so that the rays run on as thin free tips)
        us = [(k + q) / (rays - 1) for k in range(rays - 1) for q in per] + [1.0]
    blade(m, part, name, point, lambda p: root + e1 * p[0] + e2 * p[1], e1.cross(e2).normalized(), fin["thick"],
          lin(fin["nt"] * f), us)


def skin_side(s, y):
    return abs(full_point(s, angle_of(s, y))[0])


def make(name, detail):
    prepare()
    m = Mesh()
    body(m, detail)
    jaw(m, detail)
    for sx in (1.0, -1.0):
        eye(m, sx, detail)
    median_fin(m, SOFT, "soft dorsal", DORSAL_FIN, 1.0, detail)
    median_fin(m, SOFT, "anal", ANAL_FIN, -1.0, detail)
    tail_fin(m, detail)
    ps, py = PECTORAL_FIN["on"]
    pectoral = dict(PECTORAL_FIN, at=(skin_side(ps, py) - 0.004, py, ps))
    vs = PELVIC_FIN["on"]
    pelvic = dict(PELVIC_FIN, at=(PELVIC_FIN["apart"], BOT(vs) + 0.01, vs))
    for sx in (1.0, -1.0):
        paired_fin(m, PECTORAL, "pectorals", pectoral, sx, detail)
        paired_fin(m, PELVIC, "pelvics", pelvic, sx, detail)
    extras(m, detail)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p * LENGTH) for p in m.verts], [], m.faces)
    # (every layer made first, then each looked up by name: making one moves the others)
    mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.new(name="UV2")
    uv = mesh.uv_layers["UVMap"].data
    uv2 = mesh.uv_layers["UV2"].data
    for poly in mesh.polygons:
        for corner, vi in enumerate(poly.vertices):
            d = m.data[vi]
            uv[poly.loop_start + corner].uv = d[0]
            uv2[poly.loop_start + corner].uv = d[1]
    material = bpy.data.materials.get(NAME) or bpy.data.materials.new(NAME)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = COLOUR
    material.diffuse_color = COLOUR
    mesh.materials.append(material)
    for poly in mesh.polygons:
        poly.use_smooth = True
    sharp_creases(mesh, m)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    print("BUILT %s verts=%d tris=%d" % (name, len(mesh.vertices), tris))
    winding(name, mesh, m)
    if not name.endswith("_lo"):
        box = [(min(v[i] for v in m.verts) * LENGTH, max(v[i] for v in m.verts) * LENGTH) for i in range(3)]
        print("REACH %s (m): x %.3f..%.3f  y %.3f..%.3f  z %.3f..%.3f" % ((name,) + box[0] + box[1] + box[2]))
        print("SHADER %s: pectoral root (x, y, s) = (%.4f, %.4f, %.4f); hinge (s, y) = (%.4f, %.4f); mouth y0 %.4f" % (
            name, pectoral["at"][0], pectoral["at"][1], pectoral["at"][2], HINGE[0], HINGE[1], MID(0.0)))
        e1 = Vector(PECTORAL_FIN["span"]).normalized()
        e2 = Vector(PECTORAL_FIN["chord"])
        e2 = (e2 - e1 * e2.dot(e1)).normalized()
        print("SHADER %s: pectoral (left side) facing %s, middle ray %s, fan %.4f radians" % (
            name, tuple(round(v, 4) for v in e1.cross(e2).normalized()), tuple(round(v, 4) for v in e1),
            math.radians(PECTORAL_FIN["fan"][1] - PECTORAL_FIN["fan"][0])))
        report()
        print("SIZE %s (m): depth %.3f width %.3f" % (
            name, max(outline(x / 200.0)[0] - outline(x / 200.0)[1] for x in range(170)) * LENGTH,
            2.0 * max(outline(x / 200.0)[2] for x in range(170)) * LENGTH))
    return obj


def sharp_creases(mesh, m):
    """The edges where the roof of the mouth meets the lips, and the jaw's hollow its skin, are sharp: their
    points are split, so that each side keeps its own normal (one smooth normal across such a fold points
    the wrong way for some of the faces beside it)."""
    creases = (("roof", "body"), ("jaw hollow", "jaw"))
    owner = {}
    for poly in mesh.polygons:
        for key in poly.edge_keys:
            owner.setdefault(key, []).append(m.out[poly.index][1])
    sharp = mesh.attributes.get("sharp_edge") or mesh.attributes.new("sharp_edge", "BOOLEAN", "EDGE")
    for edge in mesh.edges:
        groups = set(owner.get(edge.key, []))
        sharp.data[edge.index].value = any(a in groups and b in groups for a, b in creases)


def winding(name, mesh, m):
    """Nothing inside out: the skin of the body faces away from the middle of its ring (the roof of the mouth
    down), the jaw's skin away from its own middle and its hollow up, each skin of a fin away from the fin's
    own flat, an eye out from the head (Blender's front is the side a face's normal is on)."""
    bad = {}
    for poly in mesh.polygons:
        out, group = m.out[poly.index]
        if poly.normal.dot(to_b(out)) <= 0.0:
            bad[group] = bad.get(group, 0) + 1
    told = ["%s %d/%d wrong" % (group, bad.get(group, 0), count) for group, count in m.count.items()]
    print("WINDING %s: %s: %s" % (name, "ok" if not bad else "INSIDE OUT", ", ".join(told)))


def export_one(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", export_yup=True, use_selection=True,
        export_animations=False, export_texcoords=True,
    )


def render(folder, made):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_cavity = True
    scene.display.shading.show_backface_culling = True
    scene.render.resolution_x, scene.render.resolution_y = 1000, 640
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    # (Blender space: the fish lies along Y, its nose at +Y, up is Z)
    g = LENGTH
    views = [("left", (1, 0, 0), (0, 0, 0), 1.2), ("right", (-1, 0, 0), (0, 0, 0), 1.2),
             ("front", (0, 1, 0), (0, 0, 0), 0.8), ("back", (0, -1, 0), (0, 0, 0), 0.8),
             ("top", (0.001, 0, 1), (0, 0, 0), 1.9), ("under", (0.001, 0, -1), (0, 0, 0), 1.9),
             ("head", (0.8, 0.5, 0.2), (0, 0.38, 0), 0.4), ("tail", (0.7, -0.6, 0.3), (0, -0.36, 0), 0.5)]
    for low, obj in ((False, made[0]), (True, made[1])):
        for other in bpy.data.objects:
            if other.type == "MESH":
                other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if low and view not in ("left", "head"):
                continue
            offset = Vector(direction).normalized() * 40.0
            camera.data.ortho_scale = frame * g
            camera.location = Vector(target) * g + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % ("lo_" if low else "", view))
            bpy.ops.render.render(write_still=True)


def build(name, folder):
    full = make(name, FULL)
    low = make(name + "_lo", LOW)
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, name + ".glb"))
    export_one(low, os.path.join(OUT, name + "_lo.glb"))
    low.location.x = LENGTH
    return full, low


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    full, low = build(NAME, PREVIEW)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, NAME + ".blend"))
    low.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low])


if __name__ == "__main__":
    main()
