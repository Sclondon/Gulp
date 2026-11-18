"""Builds the yellow perch (creatures/yellow_perch) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/yellow_perch/tools/build_yellow_perch.py
    blender --background --python creatures/yellow_perch/tools/build_yellow_perch.py -- <preview folder>   # with pictures

Writes creatures/yellow_perch/models/yellow_perch.glb (the full model), yellow_perch_game.glb (the game model, see GAME) and yellow_perch_lo.glb (far off, phones),
and the editable creatures/yellow_perch/tools/yellow_perch.blend (this folder has a .gdignore). Each model is one
still mesh with one surface: the shader (yellow_perch.gdshader) draws every marking, swims it, sculls its pectoral
fins and swings its lower jaw. It prints a WINDING line: the check that nothing is inside out.

A yellow perch (Perca flavescens), 0.3 m from the tip of its snout to the tips of its tail, built from the
species (no picture was traced): an oval, humped body, the back rising steeply behind the head to the first dorsal
fin; a blunt snout with the mouth at its tip reaching back under the eye; TWO SEPARATE DORSAL FINS, the first
of fourteen spines and the second soft; a short anal fin with two spines; a lightly forked tail; pectoral fins on
the side and pelvic fins under them.

THE MOUTH WORKS: ahead of the jaw's hinge the underside of the head is cut away up to the line of the mouth and
arched (the roof of the mouth), and the LOWER JAW is a part of its own, a hollow scoop that shuts up inside the
upper lip and runs back into the throat; the shader turns it down about its hinge.

Everything below is in BODY LENGTHS (the whole fish is 1 long: `s` is how far along, 0 the tip of the snout, 1
the tips of the tail; heights are from its middle line), and is multiplied by LENGTH as it is written out. In
Godot: metres, Y up, X to its left side, its nose at -Z, its origin on its middle line half way along.

What a point is, for the shader: UV2.y the part (0 body, 1 lower jaw, 2 first dorsal fin, 3 anal fin, 4 tail,
5 a pectoral fin, 6 a pelvic fin, 7 an eye, 8 the second dorsal fin, 9 a tooth). UV, on the body and jaw: x how
far along (s), y how high on its side (1 the ridge of the back, 0 the keel of the belly); on a fin: x from its
root (0) to its edge (1), y from its leading edge (0) to its trailing edge (1); on an eye: x from its middle (0)
to its rim (1); on a tooth: x root (0) to point (1). UV2.x, on the body and jaw: how much the point is inside the
mouth (0 skin, 1 inside); on the first dorsal fin: how far the point stands above the fin's root (body lengths),
for folding its spines down; on a tooth: 1 on the lower jaw. (The glTF writer flips V: what is written here is
1 - v, so that Godot reads v.)

The numbers marked "as the shader has it" are in yellow_perch.gdshader too: change one, change the other.
"""

NAME = "yellow_perch"
LENGTH = 0.3
COLOUR = (0.85, 0.72, 0.2, 1.0)

# The body's outline: how far along, its top, its bottom, half its width, the height of its widest line.
PROFILE = [
    (0.0, -0.012, -0.012, 0.0, -0.012),
    (0.004, -0.002, -0.022, 0.008, -0.012),
    (0.012, 0.008, -0.03, 0.015, -0.012),
    (0.04, 0.032, -0.045, 0.026, -0.01),
    (0.09, 0.068, -0.068, 0.038, -0.008),
    (0.15, 0.106, -0.09, 0.048, -0.006),
    (0.22, 0.134, -0.108, 0.055, -0.004),
    (0.30, 0.146, -0.12, 0.058, -0.002),
    (0.38, 0.142, -0.122, 0.057, 0.0),
    (0.48, 0.126, -0.115, 0.051, 0.0),
    (0.58, 0.1, -0.098, 0.042, 0.0),
    (0.67, 0.072, -0.072, 0.031, 0.0),
    (0.74, 0.05, -0.05, 0.021, 0.0),
    (0.79, 0.04, -0.04, 0.014, 0.0),
    (0.83, 0.041, -0.041, 0.009, 0.0),
    (0.85, 0.042, -0.042, 0.005, 0.0),
    (0.862, 0.004, -0.004, 0.001, 0.0),
]
# How round its cross-section is (1 an ellipse, less than 1 boxier).
POWER = 1.0
# Where the body's rings are: up to how far along, how far apart (body lengths, in the full model).
RINGS = ((0.135, 0.0035), (0.3, 0.006), (0.74, 0.013), (0.862, 0.006))

# As the shader has it: the jaw's hinge (how far along, how high), how the line of the mouth bows, the eye
# (how far along, how high, its radius), the gill cover's edge (its rearmost reach, at what height, how it curves).
HINGE = (0.095, -0.03)
MOUTH_BOW = 1.2
EYE_AT = (0.088, 0.03, 0.025)
EYE_BULGE = 0.22
GILL = (0.26, 0.0, 3.0)
GILL_STEP = 0.004
# The lips: how much they swell, and how wide the swelling is. Where the jaw's tip is, how far it juts, and
# how far its rim sits above the line of the mouth (in 0.002s).
LIP = 0.06
LIP_WIDE = 0.006
JAW_FROM = 0.006
JAW_JUT = 0.0
JAW_GAP = 1.0
# The teeth: (of the upper jaw?, how far along, how long, how far out towards the lip). A perch's are fine and
# bristly: none are built.
TEETH = []
TOOTH_FAT = 0.2
TOOTH_RAKE = 0.1

# The first dorsal fin: all spines (fourteen). The second: soft rays, a little gap behind the first.
DORSAL_FIN = {
    "from": 0.30, "to": 0.52, "spines": 14, "share": 1.0, "scallop": 0.25,
    "high": [(0.0, 0.05), (0.12, 0.1), (0.3, 0.105), (0.6, 0.08), (0.85, 0.045), (1.0, 0.018)],
    "lean": [(0.0, 20.0), (1.0, 45.0)],
    "thick": 0.005, "nt": 10, "nu": 40,
}
DORSAL2_FIN = {
    "from": 0.545, "to": 0.735,
    "high": [(0.0, 0.03), (0.12, 0.075), (0.4, 0.07), (0.8, 0.05), (1.0, 0.025)],
    "lean": [(0.0, 35.0), (1.0, 55.0)],
    "thick": 0.005, "nt": 10, "nu": 34,
}
ANAL_FIN = {
    "from": 0.62, "to": 0.73, "spines": 2, "share": 0.18, "scallop": 0.1,
    "high": [(0.0, 0.03), (0.2, 0.065), (0.45, 0.07), (0.8, 0.05), (1.0, 0.02)],
    "lean": [(0.0, 30.0), (1.0, 55.0)],
    "thick": 0.005, "nt": 8, "nu": 30,
}
# (the tail's hinge, `root`, is as the shader has it)
TAIL_FIN = {
    "root": 0.845, "half": 0.035, "spread": 30.0,
    "reach": [(0.0, 0.16), (0.1, 0.155), (0.3, 0.13), (0.5, 0.115), (0.7, 0.13), (0.9, 0.155), (1.0, 0.16)],
    "thick": 0.009, "nt": 16, "nu": 28,
}
# `on`: where its root is (how far along, how high); `span`: the way its middle rays point (out, up, back);
# `chord`: the way its root runs; `fan`: the angles of its first and last rays from `span`, degrees.
PECTORAL_FIN = {
    "on": (0.265, -0.03), "span": (0.5, 0.0, 0.86), "chord": (0.0, -1.0, 0.15), "base": 0.03,
    "fan": (-20.0, 22.0),
    "reach": [(0.0, 0.13), (0.15, 0.15), (0.4, 0.13), (0.7, 0.09), (1.0, 0.05)],
    "thick": 0.005, "nt": 14, "nu": 18,
}
PELVIC_FIN = {
    "on": 0.29, "apart": 0.02, "span": (0.25, -0.55, 0.8), "chord": (0.0, 0.15, 1.0), "base": 0.03,
    "fan": (0.0, 40.0),
    "reach": [(0.0, 0.12), (0.3, 0.13), (0.7, 0.1), (1.0, 0.06)],
    "thick": 0.005, "nt": 10, "nu": 8,
}

# How finely each model is cut: points round the body, how much longer than the full model's its rings' steps
# are, how much of the fins' points, the jaw (rings, points round its keel, points across its hollow), the eye,
# a tooth's sides (0 none) and one tooth in how many.
FULL = {"around": 64, "step": 1.15, "fin": 0.85, "jaw": (24, 28, 12), "eye": (24, 7), "tooth": 0, "teeth_every": 1}
LOW = {"around": 16, "step": 4.5, "fin": 0.3, "jaw": (6, 8, 3), "eye": (8, 2), "tooth": 0, "teeth_every": 1}
# The game model (Twilight Princess weight, 900 to 1,800 triangles for a fish this long): its rings put by the
# outline's bends (`tol`, body lengths; no further apart than `head` ahead of the end of the jaw, `step` behind
# it, see game_rings), the fins' points from root to edge (`fin_t`) and along it (`fin_u`), two points a spine,
# a round eye.
GAME = {"around": 16, "tol": 0.0022, "head": 0.018, "step": 0.05, "fin": 0.4, "fin_t": 0.15, "fin_u": 0.42,
        "spine_per": 2, "jaw": (6, 8, 4), "eye": (24, 2), "tooth": 0, "teeth_every": 1}
# How much of the fish's length the pictures from the front and of the head take in.
FRONT_FRAME = 0.6
HEAD_FRAME = 0.4


# ---------------------------------------------------------------------------------------------------------------
# From here down the script is the same for GameCommon's yellow perch, walleye and gar (one way of building a
# freshwater fish with a working jaw, copied into each component): only the numbers above differ. Mend one, mend
# the others. It began as a copy of the snapper's (godot/snapper), with a second dorsal fin, teeth and the rings'
# spacing added.
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

BODY, JAW, DORSAL, ANAL, TAIL, PECTORAL, PELVIC, EYE, DORSAL2, TOOTH = range(10)
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


TOP = Curve([(p[0], p[1]) for p in PROFILE])
BOT = Curve([(p[0], p[2]) for p in PROFILE])
WIDE = Curve([(p[0], p[3]) for p in PROFILE])
MID = Curve([(p[0], p[4]) for p in PROFILE])
BODY_FROM = 0.004
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
        roof = ym + min(roof_dome(s), 0.8 * wm) * (1.0 - min(1.0, (side / wm) ** 2))
        if y < roof:
            _, bot, _, _ = outline(s)
            blend = smooth(hs - CORNER_B, hs + CORNER_C, s)
            inside = (1.0 - blend) * smooth(0.0, 0.25 * (ym - bot) + 1e-5, roof - y)
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
    if "tol" in detail:
        return game_rings(detail)
    xs = []
    x = BODY_FROM
    for until, step in RINGS:
        step *= detail["step"]
        n = max(1, round((until - x) / step))
        for i in range(n):
            xs.append(x + (until - x) * i / n)
        x = until
    xs.append(BODY_TO)
    return xs


def ring_angles(s, around):
    """The angles round the body of a ring's points. (Ahead of the corner of the mouth one point of each
    ring, on each side, is on the lip exactly.)"""
    lip = round(0.29 * around)
    hs = HINGE[0]
    at_lip = lip / around * TAU
    if s < hs + CORNER_C:
        at_lip += (angle_of(s, mouth_y(s)) - at_lip) * (1.0 - smooth(hs - CORNER_B, hs + CORNER_C, s))
    angles = []
    for c in range(around):
        k = min(c, around - c)
        angle = at_lip * k / lip if k <= lip else at_lip + (math.pi - at_lip) * (k - lip) / (around / 2 - lip)
        if c > around / 2:
            angle = TAU - angle
        angles.append(angle)
    return angles


def game_rings(detail):
    """The game model's rings: few where the body runs straight, close where its outline bends. From the
    snout back, each ring is put as far on as it can go while every point of the rings it skips (sampled
    finely, with all its points round) lies within `tol` (body lengths) of the straight line between the two,
    and no further than `head` apart ahead of the end of the jaw or `step` apart behind it. The jaw's hinge,
    the corner of the mouth, the eye's front and back and the gill cover's rearmost reach always get a ring."""
    around = detail["around"]
    tol = detail["tol"]
    head_to = HINGE[0] + CORNER_C + 0.03
    must = [HINGE[0] - CORNER_B, HINGE[0], HINGE[0] + CORNER_C, EYE_AT[0] - EYE_AT[2], EYE_AT[0] + EYE_AT[2],
            GILL[0], BODY_TO]
    n = 900
    fine = sorted(set([BODY_FROM + (BODY_TO - BODY_FROM) * i / n for i in range(n + 1)] +
                      [x for x in must if BODY_FROM < x <= BODY_TO]))
    cache = {}

    def ring_at(s):
        if s not in cache:
            cache[s] = [body_point(s, a)[0] for a in ring_angles(s, around)]
        return cache[s]

    def straight(i, j):
        a, b = ring_at(fine[i]), ring_at(fine[j])
        for k in range(i + 1, j):
            t = (fine[k] - fine[i]) / (fine[j] - fine[i])
            for p, pa, pb in zip(ring_at(fine[k]), a, b):
                q = pa.lerp(pb, t)
                if math.hypot(p.x - q.x, p.y - q.y) > tol:
                    return False
        return True

    xs = [fine[0]]
    i = 0
    while i < len(fine) - 1:
        j = i + 1
        while j + 1 < len(fine):
            if any(abs(fine[j] - x) < 1e-12 for x in must):
                break
            limit = detail["head"] if fine[i] < head_to else detail["step"]
            if fine[j + 1] - fine[i] > limit or not straight(i, j + 1):
                break
            j += 1
        xs.append(fine[j])
        i = j
    return xs


def body(m, detail):
    around = detail["around"]
    grid = []
    for s in rings(detail):
        row = []
        for angle in ring_angles(s, around):
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
            out = Vector((middle.x, middle.y - centre, 0.0)).normalized()
            roof = max(m.data[q][1][0] for q in quad)
            if middle.z + 0.5 < HINGE[0] - CORNER_B:
                roof = 1.0 if roof > 1e-4 else 0.0
            roof = min(1.0, 3.0 * roof)
            m.face(quad, out * (1.0 - roof) + Vector((0.0, -1.0, 0.0)) * roof, "body")
    # the tip of the snout and the end inside the tail: a fan each
    for row, s, way in ((grid[0], 0.0, -1.0), (grid[-1], BODY_TO + 0.002, 1.0)):
        y = MID(0.0) if way < 0.0 else MID(BODY_TO)
        tip = m.add(Vector((0.0, y, s - 0.5)), (s, 0.5), BODY)
        for c in range(around):
            n = (c + 1) % around
            roof = way < 0.0 and max(m.data[row[c]][1][0], m.data[row[n]][1][0]) > 1e-4
            m.face((tip, row[c], row[n]), Vector((0.0, -1.0, 0.0)) if roof else Vector((0.0, 0.0, way)), "body")


def jaw_row(s):
    """For the lower jaw at `s`: the height of its top edge, how much narrower it is drawn, where it is along."""
    hs = HINGE[0]
    top, _, _, _ = outline(s)
    ym = mouth_y(s)
    ymj = min(ym + 0.15 * roof_dome(s) + 0.002 * JAW_GAP, top - 0.0005)
    k = 1.0 - 0.14 * smooth(hs - CORNER_B, hs + CORNER_C, s)
    z = s - JAW_JUT * (1.0 - smooth(0.0, hs, s)) - 0.5
    return ymj, k, z


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
        ymj, k, z = jaw_row(s)
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
            if c >= nb:
                out = Vector((0.0, 1.0, 0.0))
            else:
                middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
                out = Vector((middle.x, middle.y - 0.5 * (ya + yb), 0.0))
                if out.length < 1e-9:
                    out = Vector((0.0, -1.0, 0.0))
            m.face(quad, out, "jaw")
    for (row, _), way in ((grid[0], -1.0), (grid[-1], 1.0)):
        middle = (m.verts[row[nb // 2]] * 0.45 + m.verts[row[nb + nt // 2]] * 0.55) if way < 0.0 else sum((m.verts[q] for q in row), Vector()) / count
        deep = abs(m.verts[row[nb // 2]].y - m.verts[row[0]].y)
        tip = m.add(middle + Vector((0.0, 0.0, (max(0.003, 0.4 * deep) if way < 0.0 else 0.003) * way)), (m.verts[row[0]].z + 0.5, 0.3), JAW, 0.0)
        for c in range(count):
            m.face((tip, row[c], row[(c + 1) % count]), Vector((0.0, 0.0, way)), "jaw tip" if way < 0.0 else "jaw")


def teeth(m, detail):
    """Each tooth a small cone: the upper ones hang from the roof of the mouth, the lower ones stand on the
    lower jaw's rim. Shut, each is hidden inside the other jaw. UV2.x on a tooth: 1 on the lower jaw (it swings
    with it), 0 on the upper."""
    sides = detail["tooth"]
    if sides == 0:
        return
    for n, (upper, s, high, lat) in enumerate(TEETH):
        if n % detail["teeth_every"]:
            continue
        ym = mouth_y(s)
        top, bot, _, _ = outline(s)
        wm = abs(full_point(s, angle_of(s, ym))[0])
        if upper:
            x = lat * wm
            roof = ym + min(roof_dome(s), 0.8 * wm) * (1.0 - lat * lat)
            ymj, k, _ = jaw_row(s)
            high = min(high, 0.6 * (ymj - bot * k - (1.0 - k) * ymj))
            base_y = roof + 0.15 * high
            way = -1.0
            z = s - 0.5
        else:
            ymj, k, z = jaw_row(s)
            xr = wm * JAW_FIT * k
            x = lat * xr
            # (the hollow of the jaw dips by half its depth; near its rim it is close to the rim)
            jaw_low = ymj + (bot - ymj) * k
            hollow = 0.5 * (ymj - jaw_low)
            base_y = ymj - hollow * (1.0 - lat * lat) - 0.15 * high
            high = min(high, 0.6 * (top - ymj))
            way = 1.0
        if high < 0.0008:
            continue
        r = TOOTH_FAT * high
        for sx in (1.0, -1.0):
            base = Vector((sx * x, base_y, z))
            tip = base + Vector((-sx * 0.1 * high, way * 1.15 * high, TOOTH_RAKE * high))
            ring = []
            for i in range(sides):
                t = i / sides * TAU
                ring.append(m.add(base + Vector((math.cos(t) * r, 0.0, math.sin(t) * r * 1.2)), (0.0, 0.0), TOOTH, 0.0 if upper else 1.0))
            point = m.add(tip, (1.0, 0.0), TOOTH, 0.0 if upper else 1.0)
            for i in range(sides):
                p0 = m.verts[ring[i]]
                p1 = m.verts[ring[(i + 1) % sides]]
                m.face((ring[i], ring[(i + 1) % sides], point), (p0 + p1) * 0.5 - base, "teeth")


EYE_SHADER = []


def eye(m, sx, detail):
    """A low dome lying on the skin of the head."""
    spokes, steps = detail["eye"]
    xe, ye, radius = EYE_AT

    def on_skin(s, y):
        side, y2 = full_point(s, sx * angle_of(s, y), gill=False)
        return Vector((side, y2, s - 0.5))

    here = on_skin(xe, ye)
    out = (on_skin(xe + 0.004, ye) - on_skin(xe - 0.004, ye)).cross(on_skin(xe, ye + 0.004) - on_skin(xe, ye - 0.004))
    out.normalize()
    if out.x * sx < 0.0:
        out = -out
    if sx > 0.0:
        # (for the shader's cartoon eye, which grows the dome about the skin's point under its middle: that
        # point, the way the eye looks, and how far its rim lies below the flat touching the skin there)
        rim = [on_skin(xe + math.cos(a) * radius, ye + math.sin(a) * radius) for a in (i / 16 * TAU for i in range(16))]
        EYE_SHADER[:] = [here, out, sum(((here - p).dot(out) for p in rim)) / len(rim)]
    middle = m.add(here + out * (EYE_BULGE * radius * 1.1), (0.0, 0.0), EYE)
    last = None
    for k in range(1, steps + 1):
        r = k / steps
        row = []
        for sp in range(spokes):
            a = sp / spokes * TAU
            p = on_skin(xe + math.cos(a) * radius * r, ye + math.sin(a) * radius * r)
            row.append(m.add(p + out * radius * (EYE_BULGE * (1.0 - r * r) + 0.02 * (1.0 - r)), (r, 0.0), EYE))
        for sp in range(spokes):
            n = (sp + 1) % spokes
            if last is None:
                m.face((middle, row[sp], row[n]), out, "eyes")
            else:
                m.face((last[sp], row[sp], row[n], last[n]), out, "eyes")
        last = row


def blade(m, part, name, point, place, facing, thick, ts, us, high=None):
    """A fin: a thin closed blade. `point(t, u)` is a place in the fin's own flat (t 0 at its root to 1 at
    its edge, u 0 at its leading edge to 1 at its trailing edge), `place` puts that in the model, `facing`
    is the way one of its two skins faces. It is `thick` at its root, a foil across (nothing at either
    edge), thinning to nothing at its outer edge. `ts` and `us` are where its points are."""
    for side in (1.0, -1.0):
        grid = []
        for t in ts:
            row = []
            for u in us:
                foil = 2.6 * math.sqrt(u) * (1.0 - u)
                swell = thick * (1.0 - t) ** 0.7 * foil
                p = place(point(t, u)) + facing * (side * swell * 0.5)
                row.append(m.add(p, (t, u), part, high(t, u) if high else 0.0))
            grid.append(row)
        for ti in range(len(ts) - 1):
            for ui in range(len(us) - 1):
                m.face((grid[ti][ui], grid[ti][ui + 1], grid[ti + 1][ui + 1], grid[ti + 1][ui]), facing * side, name)


def lin(n, a=0.0, b=1.0):
    n = max(1, int(n))
    return [a + (b - a) * i / n for i in range(n + 1)]


def upright(p):
    """A place in the flat of the middle fins (how far along, how high) in the model."""
    return Vector((0.0, p[1], p[0] - 0.5))


SIDE = Vector((1.0, 0.0, 0.0))


def median_fin(m, part, name, fin, way, detail):
    """A dorsal fin (way 1) or the anal fin (way -1): rays standing along the body's edge from `from` to `to`,
    as long as `high` says (by how far along the fin's root, 0 to 1), leaning back by `lean` degrees. Its first
    `share` is `spines` spines: the edge is cut in between them. The first dorsal's spines fold (UV2.x)."""
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
        keep = 1.0 if share >= 1.0 else (1.0 - smooth(share - 0.08, share + 0.06, u))
        return (sink + math.cos(math.radians(lean(u))) * high(u)) * t * keep

    f = detail.get("fin_u", detail["fin"])
    if spines:
        per = detail.get("spine_per") or (6 if f >= 0.99 else (4 if f > 0.4 else 2))
        if share >= 1.0:
            us = lin(spines * per)
        else:
            us = lin(spines * per, 0.0, share)[:-1] + lin(fin["nu"] * f * (1.0 - share), share, 1.0)
    else:
        us = lin(fin["nu"] * f)
    blade(m, part, name, point, upright, SIDE, fin["thick"], lin(fin["nt"] * detail.get("fin_t", detail["fin"])), us,
          high=fold if (spines and part == DORSAL) else None)


def tail_fin(m, detail):
    """The tail: rays fanning from the end of the tail wrist, each as long as `reach` says (0 the top ray to 1
    the bottom one)."""
    reach = Curve(TAIL_FIN["reach"])
    root, half = TAIL_FIN["root"], TAIL_FIN["half"]
    spread = math.radians(TAIL_FIN["spread"])
    rise = TAIL_FIN.get("y", 0.0)
    tilt = math.radians(TAIL_FIN.get("tilt", 0.0))

    def point(t, u):
        a = spread * (1.0 - 2.0 * u) + tilt
        length = reach(u) * t
        return (root + math.cos(a) * length, rise + half * (1.0 - 2.0 * u) + math.sin(a) * length)

    f = detail["fin"]
    blade(m, TAIL, "tail", point, upright, SIDE, TAIL_FIN["thick"], lin(TAIL_FIN["nt"] * detail.get("fin_t", f)),
          lin(TAIL_FIN["nu"] * detail.get("fin_u", f)))


def paired_fin(m, part, name, fin, sx, detail):
    """A pectoral or a pelvic fin: rays fanning from a short root on the body."""
    root = Vector((sx * fin["at"][0], fin["at"][1], fin["at"][2] - 0.5))
    e1 = Vector((sx * fin["span"][0], fin["span"][1], fin["span"][2])).normalized()
    e2 = Vector((sx * fin["chord"][0], fin["chord"][1], fin["chord"][2]))
    e2 = (e2 - e1 * e2.dot(e1)).normalized()
    reach = Curve(fin["reach"])
    a0, a1 = math.radians(fin["fan"][0]), math.radians(fin["fan"][1])

    def point(t, u):
        a = a0 + (a1 - a0) * u
        length = reach(u) * t
        return (math.cos(a) * length, fin["base"] * u + math.sin(a) * length)

    f = detail["fin"]
    blade(m, part, name, point, lambda p: root + e1 * p[0] + e2 * p[1], e1.cross(e2).normalized(), fin["thick"],
          lin(fin["nt"] * detail.get("fin_t", f)), lin(fin["nu"] * detail.get("fin_u", f)))


def skin_side(s, y):
    return abs(full_point(s, angle_of(s, y))[0])


def make(name, detail):
    m = Mesh()
    body(m, detail)
    jaw(m, detail)
    teeth(m, detail)
    for sx in (1.0, -1.0):
        eye(m, sx, detail)
    median_fin(m, DORSAL, "dorsal", DORSAL_FIN, 1.0, detail)
    if DORSAL2_FIN:
        median_fin(m, DORSAL2, "dorsal2", DORSAL2_FIN, 1.0, detail)
    median_fin(m, ANAL, "anal", ANAL_FIN, -1.0, detail)
    tail_fin(m, detail)
    ps, py = PECTORAL_FIN["on"]
    pectoral = dict(PECTORAL_FIN, at=(skin_side(ps, py) - 0.004, py, ps))
    vs = PELVIC_FIN["on"]
    pelvic = dict(PELVIC_FIN, at=(PELVIC_FIN["apart"], BOT(vs) + 0.01, vs))
    for sx in (1.0, -1.0):
        paired_fin(m, PECTORAL, "pectorals", pectoral, sx, detail)
        paired_fin(m, PELVIC, "pelvics", pelvic, sx, detail)
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
        # (the jaw's tip is a fan of slivers: drawn flat, so that no point's normal leans against them)
        poly.use_smooth = m.out[poly.index][1] != "jaw tip"
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    print("BUILT %s verts=%d tris=%d" % (name, len(mesh.vertices), tris))
    winding(name, mesh, m)
    if name == NAME:
        box = [(min(v[i] for v in m.verts) * LENGTH, max(v[i] for v in m.verts) * LENGTH) for i in range(3)]
        print("REACH %s (m): x %.3f..%.3f  y %.3f..%.3f  z %.3f..%.3f" % ((name,) + box[0] + box[1] + box[2]))
        print("SHADER %s: pectoral root (x, y, s) = (%.4f, %.4f, %.4f); hinge (s, y) = (%.4f, %.4f)" % (
            name, pectoral["at"][0], pectoral["at"][1], pectoral["at"][2], HINGE[0], HINGE[1]))
        here, out, sink = EYE_SHADER
        print("SHADER %s: eye on the skin (x, y, s) = (%.4f, %.4f, %.4f); its way out = (%.4f, %.4f, %.4f); rim sink = %.5f" % (
            name, here.x, here.y, here.z + 0.5, out.x, out.y, out.z, sink))
    return obj


def winding(name, mesh, m):
    """Nothing inside out: the skin of the body faces away from the middle of its ring (the roof of the mouth
    down), the jaw's skin away from its own middle and its hollow up, each skin of a fin away from the fin's
    own flat, an eye out from the head, a tooth's sides away from its middle (Blender's front is the side a
    face's normal is on)."""
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
    scene.render.resolution_x, scene.render.resolution_y = 1400, 800
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    # (Blender space: the fish lies along Y, its nose at +Y, up is Z)
    g = LENGTH
    head_y = 0.5 - HINGE[0] * 0.8
    views = [("left", (1, 0, 0), (0, 0, 0), 1.15), ("right", (-1, 0, 0), (0, 0, 0), 1.15),
             ("front", (0, 1, 0), (0, 0, 0), FRONT_FRAME), ("back", (0, -1, 0), (0, 0, 0), FRONT_FRAME),
             ("top", (0.001, 0, 1), (0, 0, 0), 1.15), ("under", (0.001, 0, -1), (0, 0, 0), 1.15),
             ("head", (0.8, 0.5, 0.2), (0, head_y, 0), HEAD_FRAME), ("tail", (0.7, -0.6, 0.3), (0, -0.36, 0), 0.5)]
    for prefix, obj in (("", made[0]), ("lo_", made[1]), ("game_", made[2])):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if prefix and view not in ("left", "top", "head"):
                continue
            offset = Vector(direction).normalized() * 40.0
            camera.data.ortho_scale = frame * g
            camera.location = Vector(target) * g + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % (prefix, view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    full = make(NAME, FULL)
    low = make(NAME + "_lo", LOW)
    game = make(NAME + "_game", GAME)
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, NAME + ".glb"))
    export_one(low, os.path.join(OUT, NAME + "_lo.glb"))
    export_one(game, os.path.join(OUT, NAME + "_game.glb"))
    low.location.x = LENGTH
    game.location.x = -LENGTH
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, NAME + ".blend"))
    low.location.x = 0.0
    game.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low, game])


if __name__ == "__main__":
    main()
