"""Builds the bigeye tuna (creatures/bigeye_tuna) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/bigeye_tuna/tools/build_bigeye_tuna.py
    blender --background --python creatures/bigeye_tuna/tools/build_bigeye_tuna.py -- <preview folder>   # with pictures

Writes creatures/bigeye_tuna/models/bigeye_tuna.glb (the full model), bigeye_tuna_game.glb (the game
model) and bigeye_tuna_lo.glb (far off, phones), and the editable creatures/bigeye_tuna/tools/bigeye_tuna.blend
(this folder has a .gdignore; it holds all three). Each model is one still mesh: the full and the low model
of two surfaces (the body as it always was, then the throat and the gills, added 2026-11-18 and written into
the .glb by `merge_glb`), the game model of one. The shader
(bigeye_tuna.gdshader) draws every marking, swims it and works its jaw. It prints a WINDING line for each
(the check that nothing is inside out), a SHAPE line and an EYE line (the numbers the shader shares).

THE GAME MODEL (added 2026-11-18; the user, after looking at Twilight Princess's Link beside these: "We should
have a twilight princess model to compare to so we can make low poly versions while maintaining high quality
looks and silhouettes"). Built here from the same curves as the full model, not thinned from it, with its
triangles spent where they show: its rings are as few as follow the skin to within GAME_TOL (so they crowd at
the snout, the head and the tail wrist and spread out along the flanks), a ring at the jaw's hinge and enough
ahead of it for the mouth to open cleanly; fewer points round the body; each fin with few rows across (its
thickness hardly shows) but enough along its edges for their curves and tips; the first dorsal's scallops a
point at each spine's tip and one between; a round eye of 28 spokes; fewer, simpler teeth. Every UV and UV2
means what it does on the full model.

This script began as GameCommon's yellowfin tuna's (godot/yellowfin-tuna) and is shared, but for the SPEC
block below, by the bluefin tuna, the bigeye tuna and the Pacific bonito: a fix to the code under SPEC in one
belongs in all three.

A bigeye tuna (Thunnus obesus), 1.8 m from the tip of its snout to the tips of its tail, built from what the
species looks like (no picture was traced): plump, with a big rounded head, deepest early (under the front of
its first dorsal); a VERY BIG eye; LONG pectoral fins that reach back past the start of the second dorsal; a
second dorsal and anal fin of moderate height, swept back but not the yellowfin's long sickles; nine finlets
above and eight below; a tall crescent tail on a narrow keeled wrist.

THE MOUTH works. Ahead of the jaw's hinge the skin of the head is cut along the line of the lips: the points
below it are the LOWER JAW (the shader swings them down about the hinge), and the head has a ROOF to its
mouth, the jaw a FLOOR, a wall at the back (the throat), and a web of skin across each corner of the mouth
that stretches as it opens.

Everything here is drawn as a fish 1.5 long ("units": the yellowfin's own numbers) with its nose at -Z, Y up
and X to its left side, and scaled to LENGTH as it is written out; the origin is on its middle line, half way
along. `xm` below is units behind the tip of the snout.

What a point is, for the shader: UV2.y the part (0 body, 1 first dorsal, 2 the second dorsal and the anal fin,
3 a finlet, 4 the tail, 5 a pectoral fin, 6 a pelvic fin, 7 an eye, 8 a gill: see `throat`). UV, on the body: x how far along (0 snout
to 1 tail tips), y how high on its side (1 the ridge of the back, 0.5 its middle line, 0 the keel of the
belly); on a fin: x from its root (0) to its tip (1), y from its leading edge (0) to its trailing edge (1); on
an eye: x from its middle (0) to its rim (1). UV2.x, on the first dorsal, how far the point stands above the
fin's root (metres), for folding it; on the body, what it is of the mouth: 0 skin, 1 the lower jaw's skin,
2 the roof of the mouth, 3 its floor (odd numbers swing with the jaw), 4 a tooth of the upper jaw, 5 of the
lower. (The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.)

The numbers marked "as the shader has it" are in the .gdshader too: change one, change the other.
"""

import json
import math
import os
import struct
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "models")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = ARGS[0] if ARGS else ""

# ---------------------------------------------------------------------------------------------------------
# SPEC: this species. Lengths are in units (the fish drawn 1.5 long).
NAME = "bigeye_tuna"
# As the shader has it: metres from the tip of the snout to the tips of the tail.
LENGTH = 1.8
# The body's outline: units behind the snout, half its depth above its middle line, half its depth below,
# half its width.
PROFILE = [
    (0.0, 0.0, 0.0, 0.0),
    (0.003, 0.008, 0.009, 0.007),
    (0.012, 0.022, 0.025, 0.018),
    (0.04, 0.050, 0.058, 0.041),
    (0.10, 0.095, 0.110, 0.075),
    (0.18, 0.140, 0.156, 0.107),
    (0.28, 0.174, 0.192, 0.134),
    (0.40, 0.192, 0.211, 0.149),
    (0.50, 0.190, 0.208, 0.148),
    (0.62, 0.174, 0.190, 0.137),
    (0.76, 0.145, 0.158, 0.116),
    (0.90, 0.110, 0.118, 0.090),
    (1.02, 0.077, 0.082, 0.064),
    (1.12, 0.052, 0.055, 0.045),
    (1.20, 0.036, 0.037, 0.033),
    (1.27, 0.025, 0.025, 0.026),
    (1.31, 0.020, 0.020, 0.022),
    (1.345, 0.021, 0.021, 0.012),
    (1.385, 0.003, 0.003, 0.002),
]
# As the shader has it: where the lower jaw hinges (units behind the snout), and the gill cover's rearmost
# reach.
HINGE = 0.145
GILL = 0.4
# The line of the lips, as a share of the head's depth below its middle line: at the tip of the snout, at the
# hinge, and how it bows between them.
LIP_TIP = -0.12
LIP_HINGE = -0.44
LIP_POWER = 0.8
# As the shader has it: the eye (units behind the snout, units above the middle line), and its radius.
EYE_AT = (0.158, 0.03)
EYE_RADIUS = 0.038
# Points round the body, and how much coarser than the yellowfin's its rings are.
AROUND = 88
COARSER = 1.2
# The low model: points round its body, how much coarser than the yellowfin's its rings are, how much
# coarser its fins.
LOW_AROUND = 26
LOW_RINGS = 4.2
LOW_FINS = 3
# Teeth along each side of each jaw (0 for none), and how long the longest is.
TEETH = 0
TOOTH = 0.0
# The first dorsal: where it starts, how long its root is, how tall its first spine is, how many spines, how
# its edge falls away behind (more, steeper), and the least it falls to (a share of its height).
DORSAL = {"x0": 0.42, "long": 0.35, "high": 0.155, "spines": 14, "fall": 2.2, "least": 0.1}
# The second dorsal and the anal fin: the root (from, to), the middle of each edge (how far along, how far
# out from the body) and the tip (how far along, how far out).
SECOND = {"x0": 0.8, "x1": 0.87, "lead": (0.82, 0.2), "trail": (0.9, 0.12), "tip": (1.0, 0.18)}
ANAL = {"x0": 0.88, "x1": 0.95, "lead": (0.9, 0.19), "trail": (0.975, 0.11), "tip": (1.075, 0.165)}
# The finlets: (where the first is, how many) above and below, and how big the first is.
FINLETS = ((0.94, 9), (1.02, 8))
FINLET_SIZE = (0.03, 0.032)
# The tail: how far each tip is from the middle line.
TAIL_TIP = 0.235
# The pectoral fins: where the root is, how long, how wide at the root, how far swept back (degrees).
PECTORAL_FIN = {"x": 0.41, "long": 0.47, "wide": 0.075, "sweep": 30.0, "droop": -0.2}
PELVIC_FIN = {"x": 0.47, "long": 0.11, "wide": 0.042}
COLOUR = (0.25, 0.35, 0.55, 1.0)
# The game model (added 2026-11-18): points round its body, how closely its rings must follow the skin
# (units), the longest step from one ring to the next (units), how closely they must follow the step of the
# gill cover, and a share of the fins' divisions.
GAME_AROUND = 28
GAME_TOL = 0.0012
GAME_STEP = 0.1
GAME_GILL_TOL = 0.004
GAME_FINS = 1.0
# ---------------------------------------------------------------------------------------------------------

U = LENGTH / 1.5
HALF = 0.75
BODY, DORSAL_PART, SICKLE, FINLET, TAIL, PECTORAL, PELVIC, EYE, GILLS = range(9)
SKIN, JAW, ROOF, FLOOR, TOOTH_UP, TOOTH_DOWN = range(6)
TAU = math.tau
BODY_FROM = 0.002
BODY_TO = 1.385
# The share of the columns round half the body that lie above the lips.
LIP_COLUMN = 0.62
# How far below the upper lip the lower one lies with the mouth shut (the line of the mouth).
TUCK = 0.0022
# How much of the mouth's length, from its corner, the web of skin there covers.
WEB = 0.5


def gill_x(y):
    return GILL - 3.0 * (y + 0.015) ** 2


def to_b(p):
    return Vector((p.x, -p.z, p.y))


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def _slopes(xs, ys):
    """Tangents for a curve through the points that never overshoots them (Fritsch and Carlson)."""
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
    return m


_XS = [p[0] for p in PROFILE]
_CURVES = []
for column in (1, 2, 3):
    ys = [p[column] for p in PROFILE]
    _CURVES.append((ys, _slopes(_XS, ys)))


def outline(xm):
    """(half depth above, half depth below, half width) at `xm`."""
    xm = max(_XS[0], min(_XS[-1], xm))
    i = 0
    while i < len(_XS) - 2 and xm > _XS[i + 1]:
        i += 1
    h = _XS[i + 1] - _XS[i]
    t = (xm - _XS[i]) / h
    out = []
    for ys, m in _CURVES:
        a = (2 * t ** 3 - 3 * t ** 2 + 1) * ys[i] + (t ** 3 - 2 * t ** 2 + t) * h * m[i]
        b = (-2 * t ** 3 + 3 * t ** 2) * ys[i + 1] + (t ** 3 - t ** 2) * h * m[i + 1]
        out.append(max(a + b, 0.0005))
    return out


def top(xm):
    return outline(xm)[0]


def bottom(xm):
    return -outline(xm)[1]


def body_point(xm, angle, gill=True):
    """A point of the skin: `angle` round the body from the ridge of the back (0) by its left side (a
    quarter turn) to the keel of the belly (half a turn); without the step of the gill cover if not `gill`."""
    up, down, wide = outline(xm)
    c = math.cos(angle)
    s = math.sin(angle)
    y = c * (up if c >= 0.0 else down)
    side = math.copysign(abs(s) ** 0.92, s) * wide
    # the keels: a ridge along each side of the tail wrist
    keel = 0.009 * smooth(1.15, 1.27, xm) * (1.0 - smooth(1.32, 1.37, xm))
    side += math.copysign(keel * math.exp(-(c / 0.3) ** 2), s)
    # the gill cover: it stands a little proud of the body behind its edge
    behind = xm - gill_x(y)
    if gill and behind > 0.0 and wide > 0.01:
        mask = smooth(-0.95, -0.8, c) * (1.0 - smooth(0.4, 0.6, c))
        step = 0.0045 * smooth(0.0, 0.004, behind) * math.exp(-behind / 0.035) * mask
        side *= 1.0 - step / wide
    return Vector((side, y, xm - HALF))


def lip_c(xm):
    """The line of the lips, as the cosine of how far round the body it is."""
    t = max(0.0, min(1.0, xm / HINGE))
    return LIP_TIP + (LIP_HINGE - LIP_TIP) * t ** LIP_POWER


def tuck(xm):
    # (less near the tip of the snout, where the head is too thin for it to lie under the lip)
    return min(TUCK * smooth(HINGE, HINGE * 0.75, xm), 0.15 * outline(xm)[1])


def lip_point(xm, sx, lower):
    """A point of the upper lip, or of the lower (which lies a little inside and below it), ahead of the
    hinge. `sx` 1 its left side, -1 its right."""
    p = body_point(xm, sx * math.acos(lip_c(xm)))
    if lower:
        t = tuck(xm)
        p.y -= t
        # (never across the middle line, where the snout is thinner than the tuck)
        p.x -= sx * min(t * 0.7, 0.5 * abs(p.x))
    return p


def mouth_y(xm, x, roof):
    """How high the roof of the mouth is (or its floor), `x` to one side of the middle."""
    up, down, _ = outline(xm)
    lip = lip_point(xm, 1.0, not roof)
    u = max(-1.0, min(1.0, x / max(lip.x, 1e-6)))
    room = (up - lip.y) if roof else (down + lip.y)
    deep = 0.5 * room * (0.3 + 0.7 * smooth(0.0, HINGE * 0.4, xm))
    return lip.y + (deep if roof else -deep) * (1.0 - u * u)


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        # per point: (uv, uv2)
        self.data = []
        # per face: the way it should face
        self.out = []
        self.count = {}
        # per face: 0 the body's surface, 1 the throat's and the gills' (a second surface on the full model)
        self.layers = []
        self.layer = 0

    def copy(self, i):
        self.verts.append(self.verts[i].copy())
        self.data.append(self.data[i])
        return len(self.verts) - 1

    def add(self, p, uv, part, high=0.0):
        self.verts.append(Vector(p))
        self.data.append(((uv[0], 1.0 - uv[1]), (high, 1.0 - part)))
        return len(self.verts) - 1

    def face(self, points, out, name):
        """A face wound so that its front (the side its points go round anticlockwise) is towards `out`."""
        kept = []
        for i in points:
            if all((self.verts[i] - self.verts[k]).length > 1e-9 for k in kept):
                kept.append(i)
        points = kept
        if len(points) < 3:
            return
        ps = [self.verts[i] for i in points]
        n = Vector((0.0, 0.0, 0.0))
        for i in range(len(ps)):
            n += ps[i].cross(ps[(i + 1) % len(ps)])
        if n.length < 1e-12:
            return
        if n.dot(out) < 0.0:
            points = tuple(reversed(points))
        self.faces.append(tuple(points))
        self.out.append((Vector(out), name))
        self.layers.append(self.layer)
        self.count[name] = self.count.get(name, 0) + 1


# Which model is being built: "full", "low" or "game" (set by `make`).
LEVEL = "full"


def rings(low):
    if LEVEL == "game":
        return game_rings()
    return even_rings(low)


def game_rings():
    """The game model's rings: from the full model's, as few as keep every point of the skin (sampled round
    it) within GAME_TOL of the straight line between the rings either side of it, never more than
    GAME_STEP apart (so the swimming bends smoothly), and at least six from the snout to the hinge."""
    fine = even_rings(False)
    angles = [k / 32 * TAU for k in range(17)]
    # (the step of the gill cover, a small edge, is held to a looser test: it is drawn by the shader too)
    smooth_skin = [[body_point(x, a, False) for a in angles] for x in fine]
    skin = [[body_point(x, a) for a in angles] for x in fine]

    def straight(i, k):
        for m in range(i + 1, k):
            t = (fine[m] - fine[i]) / (fine[k] - fine[i])
            for a in range(len(angles)):
                if (smooth_skin[m][a] - smooth_skin[i][a].lerp(smooth_skin[k][a], t)).length > GAME_TOL:
                    return False
                if (skin[m][a] - skin[i][a].lerp(skin[k][a], t)).length > GAME_GILL_TOL:
                    return False
        return True

    keep = [0]
    i = 0
    while i < len(fine) - 1:
        j = i + 1
        while j + 1 < len(fine):
            k = j + 1
            longest = HINGE / 6.0 if fine[i] < HINGE - 1e-6 else GAME_STEP
            if fine[k] - fine[i] > longest + 1e-9 or not straight(i, k):
                break
            j = k
        keep.append(j)
        i = j
    xs = [fine[k] for k in keep]
    if not any(abs(x - HINGE) < 1e-9 for x in xs):
        xs.append(HINGE)
    return sorted(xs)


def even_rings(low):
    xs = []
    x = BODY_FROM
    for until, step in ((0.20, 0.0035), (0.46, 0.0045), (1.18, 0.011), (BODY_TO, 0.0045)):
        step *= LOW_RINGS if low else COARSER
        n = max(1, round((until - x) / step))
        for i in range(n):
            xs.append(x + (until - x) * i / n)
        x = until
    xs.append(BODY_TO)
    # (one ring is at the jaw's hinge)
    nearest = min(range(1, len(xs) - 1), key=lambda i: abs(xs[i] - HINGE))
    xs[nearest] = HINGE
    return xs


def body(m, low):
    around = GAME_AROUND if LEVEL == "game" else LOW_AROUND if low else AROUND
    half = around // 2
    lip = round(half * LIP_COLUMN)
    xs = rings(low)

    def k_of(c):
        return c if c <= half else around - c

    def angle_of(xm, c):
        # the columns are spread so that one of them runs along the lips, and evenly again behind the head
        k = k_of(c)
        at_lip = math.acos(lip_c(xm))
        if xm > HINGE:
            at_lip += (lip / half * math.pi - at_lip) * smooth(HINGE, HINGE * 1.9, xm)
        a = at_lip * k / lip if k <= lip else at_lip + (math.pi - at_lip) * (k - lip) / (half - lip)
        return a if c <= half else TAU - a

    upper = []
    lower = []
    for xm in xs:
        split = xm < HINGE - 1e-6
        up_row = {}
        low_row = {}
        for c in range(around):
            angle = angle_of(xm, c)
            k = k_of(c)
            uv = (xm / 1.5, 0.5 + 0.5 * math.cos(angle))
            if not split:
                up_row[c] = low_row[c] = m.add(body_point(xm, angle), uv, BODY, SKIN)
                continue
            if k <= lip:
                up_row[c] = m.add(body_point(xm, angle), uv, BODY, SKIN)
            if k == lip:
                low_row[c] = m.add(lip_point(xm, 1.0 if c <= half else -1.0, True), uv, BODY, JAW)
            elif k > lip:
                low_row[c] = m.add(body_point(xm, angle), uv, BODY, JAW)
        upper.append(up_row)
        lower.append(low_row)
    for r in range(len(xs) - 1):
        for c in range(around):
            n = (c + 1) % around
            rows = upper if max(k_of(c), k_of(n)) <= lip else lower
            quad = (rows[r][c], rows[r][n], rows[r + 1][n], rows[r + 1][c])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((middle.x, middle.y, 0.0)), "body")
    # the tip of the snout (the upper jaw's and the lower's) and the end inside the tail: a fan each
    tips = ((upper, Vector((0.0, 0.0, -HALF)), SKIN, -1.0), (lower, Vector((0.0, -tuck(0.0), -HALF)), JAW, -1.0))
    for rows, at, what, way in tips:
        tip = m.add(at, (0.0, 0.5), BODY, what)
        for c in range(around):
            n = (c + 1) % around
            if c in rows[0] and n in rows[0] and (max(k_of(c), k_of(n)) <= lip) == (rows is upper):
                m.face((tip, rows[0][c], rows[0][n]), Vector((0.0, 0.0, way)), "body")
    tip = m.add(Vector((0.0, 0.0, BODY_TO + 0.002 - HALF)), ((BODY_TO + 0.002) / 1.5, 0.5), BODY, SKIN)
    for c in range(around):
        m.face((tip, upper[-1][c], upper[-1][(c + 1) % around]), Vector((0.0, 0.0, 1.0)), "body")
    mouth(m, [x for x in xs if x <= HINGE + 1e-6], low)


def mouth(m, xs, low):
    """The inside of the mouth: its roof (under the upper head), its floor (on the lower jaw), the wall at the
    back, a web of skin across each corner, and teeth."""
    across = 6 if LEVEL == "game" else 4 if low else 12
    sheets = []
    for roof in (True, False):
        what = ROOF if roof else FLOOR
        out = Vector((0.0, -1.0 if roof else 1.0, 0.0))
        rows = []
        for xm in xs:
            edge = lip_point(xm, 1.0, not roof)
            row = []
            for j in range(across + 1):
                x = edge.x * (1.0 - 2.0 * j / across)
                row.append(m.add(Vector((x, mouth_y(xm, x, roof), edge.z)), (xm / 1.5, 0.5), BODY, what))
            rows.append(row)
        for r in range(len(rows) - 1):
            for j in range(across):
                m.face((rows[r][j], rows[r][j + 1], rows[r + 1][j + 1], rows[r + 1][j]), out, "mouth")
        tip = m.add(Vector((0.0, 0.0 if roof else -tuck(0.0), -HALF)), (0.0, 0.5), BODY, what)
        for j in range(across):
            m.face((tip, rows[0][j], rows[0][j + 1]), out, "mouth")
        sheets.append(rows)
    # (the throat, back from the hinge where the back of the mouth was a wall, and the gills in it, are built
    # last, by `throat`, so that every point before them is numbered as it always was)
    m.sheets = sheets
    # the wall at the back (the full and low models' body surface is kept as it always was, so the wall is still
    # there; the shader leaves it out, opening the mouth onto the throat)
    roof_row = sheets[0][-1]
    floor_row = sheets[1][-1]
    for j in range(across):
        m.face((roof_row[j], roof_row[j + 1], floor_row[j + 1], floor_row[j]), Vector((0.0, 0.0, -1.0)), "mouth")
    # the webs: two skins each, a hair apart, from the upper lip to the lower
    for sx in (1.0, -1.0):
        for skin, inset in ((1.0, 0.0), (-1.0, 0.0012)):
            last = None
            for xm in xs:
                if xm < HINGE * (1.0 - WEB):
                    continue
                shift = Vector((-sx * inset, 0.0, 0.0))
                pair = (m.add(lip_point(xm, sx, False) + shift, (xm / 1.5, 0.5), BODY, ROOF),
                        m.add(lip_point(xm, sx, True) + shift, (xm / 1.5, 0.5), BODY, FLOOR))
                if last:
                    m.face((last[0], pair[0], pair[1], last[1]), Vector((sx * skin, 0.0, 0.0)), "mouth")
                last = pair
    if low or TEETH == 0:
        return
    # the teeth: thin cones rooted in the roof and the floor just inside the lips; shut, each jaw's are hidden
    # inside the other (the game model: half as many, each of four sides)
    game = LEVEL == "game"
    count = max(1, TEETH // 2) if game else TEETH
    sides = 4 if game else 5
    for sx in (1.0, -1.0):
        for upper in (True, False):
            for i in range(count):
                share = (i + (0.0 if upper else 0.5)) / count
                xm = HINGE * (0.05 + 0.75 * share)
                edge = lip_point(xm, sx, not upper)
                x = edge.x - sx * (0.005 if upper else 0.0036)
                long = TOOTH * (1.0 - 0.45 * share)
                root = Vector((x, mouth_y(xm, x, upper), edge.z))
                way = -1.0 if upper else 1.0
                point = Vector((x, edge.y + way * long, edge.z + 0.25 * long))
                ring = []
                thick = TOOTH * 0.24
                for q in range(sides):
                    a = q / sides * TAU
                    spot = root + Vector((math.cos(a) * thick, -way * thick * 0.6, math.sin(a) * thick))
                    ring.append(m.add(spot, (xm / 1.5, 0.5), BODY, TOOTH_UP if upper else TOOTH_DOWN))
                end = m.add(point, (xm / 1.5, 0.5), BODY, TOOTH_UP if upper else TOOTH_DOWN)
                for q in range(sides):
                    a = (q + 0.5) / sides * TAU
                    m.face((end, ring[q], ring[(q + 1) % sides]), Vector((math.cos(a), 0.0, math.sin(a))), "teeth")


# The throat and the gills (added 2026-11-18; the user: "The fish need modeled gills as well, well for relevant fish,
# so like when it opens its mouth wide you can see them"). How far back from the hinge the throat runs (units), how
# much it narrows by its end, where along it the four gill arches stand (shares of its length), how far in from its
# wall they are (a share), where on the roof and the floor each arch ends (a share of the way out to the lips), and
# the arches' bars, filaments and rakers (units, for a throat 0.07 units wide each side of its middle: they are
# scaled to the throat this fish has).
THROAT = 0.13
THROAT_NARROW = 0.3
ARCHES = (0.22, 0.4, 0.58, 0.76)
ARCH_IN = 0.84
ARCH_FROM = 0.3
BAR = 0.0042
FILAMENT = 0.02
RAKER = 0.008


def throat(m, sheets, low):
    """A short tunnel back from the hinge, carrying on the roof and the floor of the mouth from where their last
    rows meet (the mouth's back was a wall there), closed at its end; in it, on each side, four gill arches: a
    curved bar from the roof round the corner of the throat to its floor, a fringe of filaments behind it, pale
    rakers before it. All of it in the throat's layer (the full model's second surface), out of sight with the
    mouth shut: it lies behind the hinge, inside the head. A gill's UV.x is how far along its arch it is (0 at the
    roof, 1 the floor), UV.y what it is (0 the bar, 0.4 to 0.6 the filaments from their roots to their tips, 1 a
    raker)."""
    m.layer = 1
    game = LEVEL == "game"
    stations = 2 if low else 3 if game else 6
    segments = 2 if low else 4 if game else 12
    sides = 3 if low or game else 6
    teeth = 1 if low else 2
    roof_row, floor_row = sheets[0][-1], sheets[1][-1]
    loop = list(roof_row) + list(reversed(floor_row[1:-1]))
    half = len(roof_row)
    centre_y = (mouth_y(HINGE, 0.0, True) + mouth_y(HINGE, 0.0, False)) * 0.5
    flat_middle = Vector((0.0, centre_y, 0.0))
    along = Vector((0.0, 0.0, 1.0))

    def shrink(t):
        return 1.0 - THROAT_NARROW * t

    def inward(p):
        return Vector((-p.x, centre_y - p.y, 0.0)).normalized()

    # (the throat's first ring a copy of the mouth's last points, so that the throat is a mesh of its own)
    rings = [[m.copy(i) for i in loop]]
    for k in range(1, stations + 1):
        t = k / stations
        xm = HINGE + THROAT * t
        ring = []
        for n, i in enumerate(loop):
            p = m.verts[i]
            q = flat_middle + (Vector((p.x, p.y, 0.0)) - flat_middle) * shrink(t)
            ring.append(m.add(Vector((q.x, q.y, xm - HALF)), (xm / 1.5, 0.5), BODY, ROOF if n < half else FLOOR))
        rings.append(ring)
    for r in range(stations):
        for n in range(len(loop)):
            quad = (rings[r][n], rings[r][(n + 1) % len(loop)], rings[r + 1][(n + 1) % len(loop)], rings[r + 1][n])
            centre = sum((m.verts[i] for i in quad), Vector()) * 0.25
            m.face(quad, inward(centre), "throat")
    end = m.add(Vector((0.0, centre_y, HINGE + THROAT - HALF)), ((HINGE + THROAT) / 1.5, 0.5), BODY, ROOF)
    for n in range(len(loop)):
        m.face((end, rings[-1][n], rings[-1][(n + 1) % len(loop)]), Vector((0.0, 0.0, -1.0)), "throat")
    # the gill arches
    edge = lip_point(HINGE, 1.0, False)
    size = edge.x / 0.07
    bar, filament, raker = BAR * size, FILAMENT * size, RAKER * size
    for sx in (1.0, -1.0):
        for share in ARCHES:
            z = HINGE + THROAT * share - HALF
            scale = shrink(share) * ARCH_IN

            def arch(v, sx=sx, z=z, scale=scale):
                # (an even C, half an ellipse as wide as the throat and as deep, from the roof round its side to
                # its floor: no bend tighter than the bar is thick)
                a = math.asin(ARCH_FROM) + (math.pi - 2.0 * math.asin(ARCH_FROM)) * v
                deep = mouth_y(HINGE, 0.0, True) - centre_y
                q = Vector((sx * edge.x * math.sin(a), centre_y + deep * math.cos(a), 0.0))
                q = flat_middle + (q - flat_middle) * scale
                return Vector((q.x, q.y, z))

            vs = [k / segments for k in range(segments + 1)]
            curve = [arch(v) for v in vs]

            def tangent(k, curve=curve):
                return (curve[min(k + 1, segments)] - curve[max(k - 1, 0)]).normalized()

            # the bar: a tube along the arch, closed at its ends
            tube = []
            for k, p in enumerate(curve):
                side = tangent(k).cross(along).normalized()
                tube.append([m.add(p + (side * math.cos(a) + along * math.sin(a)) * bar, (vs[k], 0.0), GILLS)
                             for a in (q / sides * TAU for q in range(sides))])
            for k in range(segments):
                for q in range(sides):
                    w = (q + 1) % sides
                    quad = (tube[k][q], tube[k][w], tube[k + 1][w], tube[k + 1][q])
                    centre = sum((m.verts[i] for i in quad), Vector()) * 0.25
                    m.face(quad, centre - (curve[k] + curve[k + 1]) * 0.5, "gills")
            for k, way in ((0, -tangent(0)), (segments, tangent(segments))):
                cap = m.add(curve[k], (vs[k], 0.0), GILLS)
                for q in range(sides):
                    m.face((cap, tube[k][q], tube[k][(q + 1) % sides]), way, "gills")
            # the filaments: a thin closed blade behind the bar, its edge a comb of long and short tips; the rakers:
            # a pale tooth before the bar between each two points of it (each two skins back to back)
            fine = [k / (segments * teeth) for k in range(segments * teeth + 1)]
            base = [arch(v) for v in fine]
            tips = []
            for j, v in enumerate(fine):
                long = filament * (1.0 if j % teeth == 0 else 0.55) * (0.6 + 0.4 * math.sin(math.pi * v))
                tips.append(base[j] + (along + inward(base[j]) * 0.6).normalized() * long)
            for skin in (1.0, -1.0):
                roots, ends = [], []
                for j, v in enumerate(fine):
                    t_dir = (base[min(j + 1, len(fine) - 1)] - base[max(j - 1, 0)]).normalized()
                    normal = t_dir.cross(tips[j] - base[j]).normalized()
                    roots.append(m.add(base[j] + along * bar * 0.6 + normal * skin * bar * 0.35, (v, 0.4), GILLS))
                    ends.append(m.add(tips[j], (v, 0.6), GILLS))
                for j in range(len(fine) - 1):
                    normal = (base[j + 1] - base[j]).cross(tips[j] - base[j]).normalized()
                    m.face((roots[j], roots[j + 1], ends[j + 1], ends[j]), normal * skin, "gills")
                for k in range(segments):
                    a, b = curve[k], curve[k + 1]
                    middle = (a + b) * 0.5
                    tip = middle + (-along + inward(middle)).normalized() * raker
                    normal = (b - a).cross(tip - a).normalized()
                    lift = normal * skin * bar * 0.3
                    tooth = (m.add(a - along * bar * 0.5 + lift, (vs[k], 1.0), GILLS),
                             m.add(b - along * bar * 0.5 + lift, (vs[k + 1], 1.0), GILLS),
                             m.add(tip, ((vs[k] + vs[k + 1]) * 0.5, 1.0), GILLS))
                    m.face(tooth, normal * skin, "gills")
    m.layer = 0


def eye_skin(sx):
    """A point of the skin `xm` behind the snout and `y` up, on the side `sx`."""
    def on_skin(xm, y):
        up, down, _ = outline(xm)
        c = max(-1.0, min(1.0, y / (up if y >= 0.0 else down)))
        return body_point(xm, sx * math.acos(c))
    return on_skin


def eye_frame(sx):
    """Where the middle of the eye lies on the skin, and the way the skin faces there (as the shader has it:
    the EYE line)."""
    on_skin = eye_skin(sx)
    xe, ye = EYE_AT
    here = on_skin(xe, ye)
    out = (on_skin(xe + 0.004, ye) - on_skin(xe - 0.004, ye)).cross(on_skin(xe, ye + 0.004) - on_skin(xe, ye - 0.004))
    out.normalize()
    if out.x * sx < 0.0:
        out = -out
    return here, out


def eye(m, sx, low):
    """A low dome lying on the skin of the head."""
    spokes = 28 if LEVEL == "game" else 12 if low else 40
    steps = 3 if low or LEVEL == "game" else 12
    xe, ye = EYE_AT
    on_skin = eye_skin(sx)
    here, out = eye_frame(sx)
    bulge = EYE_RADIUS / 0.03
    middle = m.add(here + out * 0.0066 * bulge, (0.0, 0.0), EYE)
    last = None
    for k in range(1, steps + 1):
        r = k / steps
        row = []
        for s in range(spokes):
            a = s / spokes * TAU
            p = on_skin(xe + math.cos(a) * EYE_RADIUS * r, ye + math.sin(a) * EYE_RADIUS * r)
            row.append(m.add(p + out * (0.006 * (1.0 - r * r) + 0.0006 * (1.0 - r)) * bulge, (r, 0.0), EYE))
        for s in range(spokes):
            n = (s + 1) % spokes
            if last is None:
                m.face((middle, row[s], row[n]), out, "eyes")
            else:
                m.face((last[s], row[s], row[n], last[n]), out, "eyes")
        last = row


def blade(m, part, name, point, place, facing, thick, nt, nu, high=None):
    """A fin: a thin closed blade. `point(t, u)` is a place in the fin's own flat (t 0 at its root to 1 at
    its tip, u 0 at its leading edge to 1 at its trailing edge), `place` puts that in the model, `facing`
    is the way one of its two skins faces. It is `thick` at its root, a foil across (nothing at either
    edge), thinning to nothing at its tip."""
    nt = max(nt, 1 if LEVEL == "game" else 2)
    nu = max(nu, 2)
    for side in (1.0, -1.0):
        grid = []
        for ti in range(nt + 1):
            t = ti / nt
            row = []
            for ui in range(nu + 1):
                u = ui / nu
                foil = 2.6 * math.sqrt(u) * (1.0 - u)
                swell = thick * (1.0 - t) ** 0.7 * foil
                p = place(point(t, u)) + facing * (side * swell * 0.5)
                row.append(m.add(p, (t, u), part, high(t, u) if high else 0.0))
            grid.append(row)
        for ti in range(nt):
            for ui in range(nu):
                m.face((grid[ti][ui], grid[ti][ui + 1], grid[ti + 1][ui + 1], grid[ti + 1][ui]), facing * side, name)


def bezier(p0, p1, p2, t):
    a = 1.0 - t
    return (a * a * p0[0] + 2 * a * t * p1[0] + t * t * p2[0], a * a * p0[1] + 2 * a * t * p1[1] + t * t * p2[1])


def swept(lead, trail, reach=0.985):
    """A fin drawn by its leading and trailing edges (three points each, root to tip; they meet at the tip)."""
    def point(t, u):
        a = bezier(*lead, t * reach)
        b = bezier(*trail, t * reach)
        return (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)
    return point


def upright(p):
    """A place in the flat of the middle fins (units behind the snout, units up) in the model."""
    return Vector((0.0, p[1], p[0] - HALF))


SIDE = Vector((1.0, 0.0, 0.0))


def cut(full, d, game, exact=False):
    """How many rows a fin is cut into: the full model's `full`, the low one's `full // d`, the game model's
    `game` (scaled by GAME_FINS unless `exact`)."""
    if LEVEL == "game":
        return game if exact else max(1, round(game * GAME_FINS))
    return full // d


def fins(m, low):
    d = LOW_FINS if low else 1
    # The first dorsal: its spines lean back, the first the tallest, the edge falling away behind and
    # scalloped between the spines.
    spines = DORSAL["spines"]
    lean = math.radians(24.0)

    def dorsal_high(u):
        fall = DORSAL["least"] + (1.0 - DORSAL["least"]) * (1.0 - u) ** DORSAL["fall"]
        scallop = 0.9 + 0.1 * abs(math.cos(math.pi * u * spines))
        return DORSAL["high"] * fall * scallop * (0.7 + 0.3 * smooth(0.0, 0.05, u))

    def dorsal_point(t, u):
        xm = DORSAL["x0"] + DORSAL["long"] * u
        high = dorsal_high(u) * t
        return (xm + math.sin(lean) * high, top(xm) - 0.012 + math.cos(lean) * high + 0.012 * t)

    blade(m, DORSAL_PART, "first dorsal", dorsal_point, upright, SIDE, 0.007, cut(12, d, 1, exact=True), cut(spines * 6, d, spines * 2, exact=True),
          high=lambda t, u: (dorsal_high(u) * math.cos(lean) + 0.012) * t * U)
    # The second dorsal and the anal fin.
    for fin, edge, way, name in ((SECOND, top, 1.0, "second dorsal"), (ANAL, bottom, -1.0, "anal")):
        base = edge((fin["x0"] + fin["x1"]) * 0.5)
        tip = (fin["tip"][0], base + way * fin["tip"][1])
        blade(m, SICKLE, name,
              swept(((fin["x0"], edge(fin["x0"]) - way * 0.014), (fin["lead"][0], base + way * fin["lead"][1]), tip),
                    ((fin["x1"], edge(fin["x1"]) - way * 0.014), (fin["trail"][0], base + way * fin["trail"][1]), tip)),
              upright, SIDE, 0.011, cut(36, d, 10), cut(12, d, 2))
    # The finlets, smaller towards the tail.
    for way, (first, count) in zip((1.0, -1.0), FINLETS):
        for k in range(count):
            share = k / (count - 1)
            x0 = first + (1.272 - first) * share
            chord = FINLET_SIZE[0] * (1.0 - 0.33 * share)
            high = FINLET_SIZE[1] * (1.07 - 0.47 * share) * way
            y0 = (top(x0) if way > 0.0 else bottom(x0)) - 0.004 * way
            y1 = (top(x0 + chord) if way > 0.0 else bottom(x0 + chord)) - 0.004 * way
            tip = (x0 + chord * 1.55, y1 + high)
            blade(m, FINLET, "finlets", swept(((x0, y0), (x0 + chord * 0.6, y0 + high * 0.7), tip),
                                               ((x0 + chord, y1), (x0 + chord * 1.3, y1 + high * 0.25), tip), 0.97),
                  upright, SIDE, 0.0022, cut(8, min(d, 2), 2, exact=True), cut(5, min(d, 2), 2, exact=True))
    # The tail: a tall stiff crescent, two lobes that meet along the middle line.
    for way in (1.0, -1.0):
        tip = (1.5, TAIL_TIP * way)
        blade(m, TAIL, "tail", swept(((1.28, 0.0), (1.36, TAIL_TIP * 0.54 * way), tip),
                                      ((1.395, 0.0), (1.458, TAIL_TIP * 0.353 * way), tip)),
              upright, SIDE, 0.017, cut(40, d, 12), cut(14, d, 3, exact=True))
    for sx in (1.0, -1.0):
        # The pectoral fins: held out like wings, swept back and a little down.
        fin = PECTORAL_FIN
        up, down, wide = outline(fin["x"] + 0.015)
        root = Vector((sx * (wide - 0.034), -0.03, fin["x"] - HALF))
        sweep = math.radians(fin["sweep"])
        span = Vector((sx * math.sin(sweep), fin["droop"], math.cos(sweep))).normalized()
        chord = Vector((0.0, -0.8, 1.0)).normalized()
        facing = span.cross(chord).normalized()
        if facing.y < 0.0:
            facing = -facing

        def pectoral_point(t, u, fin=fin):
            t *= 0.985
            lead = 0.17 * fin["long"] * t * t
            wide_here = fin["wide"] * (1.0 - t) ** 0.75 * (1.0 + 0.5 * t) + 0.004
            return (fin["long"] * t, lead + wide_here * u)

        blade(m, PECTORAL, "pectorals", pectoral_point,
              lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.012, cut(40, d, 10), cut(12, d, 2, exact=True))
        # The pelvic fins: small, under the pectorals, pointing back and down.
        fin = PELVIC_FIN
        root = Vector((sx * 0.032, bottom(fin["x"]) + 0.014, fin["x"] - HALF))
        span = Vector((sx * 0.3, -0.5, 0.82)).normalized()
        chord = Vector((0.0, 0.12, 1.0)).normalized()
        facing = span.cross(chord).normalized()
        if facing.x * sx < 0.0:
            facing = -facing

        def pelvic_point(t, u, fin=fin):
            t *= 0.97
            return (fin["long"] * t, 0.17 * fin["long"] * t * t + (fin["wide"] * (1.0 - t) ** 0.8 + 0.003) * u)

        blade(m, PELVIC, "pelvics", pelvic_point,
              lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.007, cut(14, d, 4), cut(8, d, 2, exact=True))


def make(name, low, level=None):
    """Builds one model. The full and the low model come out as two objects: the body as it always was, and its
    throat and gills (`name`_throat), which are written into the same .glb as a second surface (`export`); the
    game model is one object."""
    global LEVEL
    LEVEL = level or ("low" if low else "full")
    m = Mesh()
    body(m, low)
    for sx in (1.0, -1.0):
        eye(m, sx, low)
    fins(m, low)
    m.split = len(m.verts)
    throat(m, m.sheets, low)
    if LEVEL == "game":
        return mesh_object(name, m, list(range(len(m.faces))), 0, len(m.verts), NAME, COLOUR), None
    first = mesh_object(name, m, [i for i, layer in enumerate(m.layers) if layer == 0], 0, m.split, NAME, COLOUR)
    inner = mesh_object(name + "_throat", m, [i for i, layer in enumerate(m.layers) if layer == 1], m.split,
                        len(m.verts), NAME + "_throat", (0.4, 0.05, 0.06, 1.0))
    return first, inner


def mesh_object(name, m, faces, lo, hi, material_name, colour):
    """A Blender object of the faces `faces` of `m`, whose points are `lo` to `hi`."""
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) * U for p in m.verts[lo:hi]], [], [tuple(i - lo for i in m.faces[f]) for f in faces])
    # (every layer made first, then each looked up by name: making one moves the others)
    mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.new(name="UV2")
    uv = mesh.uv_layers["UVMap"].data
    uv2 = mesh.uv_layers["UV2"].data
    for poly in mesh.polygons:
        for corner, vi in enumerate(poly.vertices):
            d = m.data[vi + lo]
            uv[poly.loop_start + corner].uv = d[0]
            uv2[poly.loop_start + corner].uv = d[1]
    material = bpy.data.materials.get(material_name) or bpy.data.materials.new(material_name)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = colour
    material.diffuse_color = colour
    mesh.materials.append(material)
    # (smooth, but for the gills' filaments and rakers: thin folded blades, flat so that each face keeps its own
    # facing)
    for poly in mesh.polygons:
        poly.use_smooth = not (m.out[faces[poly.index]][1] == "gills" and m.data[m.faces[faces[poly.index]][0]][0][1] < 0.9)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    box = [max(abs(v.co[i]) for v in mesh.vertices) for i in range(3)]
    print("BUILT %s verts=%d tris=%d reach side=%.3f along=%.3f up/down=%.3f" % (name, len(mesh.vertices), tris, box[0], box[1], box[2]))
    winding(name, mesh, m, faces)
    return obj


def winding(name, mesh, m, faces):
    """Nothing inside out: the skin of the body faces away from its middle line, each skin of a fin away
    from the fin's own flat, an eye out from the head, the roof of the mouth down and its floor up, the throat in
    towards its middle, each part of a gill out of itself (Blender's front is the side a face's normal is on)."""
    bad = {}
    count = {}
    for poly in mesh.polygons:
        out, group = m.out[faces[poly.index]]
        count[group] = count.get(group, 0) + 1
        if poly.normal.dot(to_b(out)) <= 0.0:
            bad[group] = bad.get(group, 0) + 1
            if os.environ.get("WHY"):
                print("  wrong %s area=%.3g at %s" % (group, poly.area, tuple(round(v, 4) for v in poly.center)))
    told = ["%s %d/%d wrong" % (group, bad.get(group, 0), n) for group, n in count.items()]
    print("WINDING %s: %s: %s" % (name, "ok" if not bad else "INSIDE OUT", ", ".join(told)))


def export(obj, inner, path):
    """Writes `obj` to `path`, and `inner` (if any) into the same .glb as a second primitive of its mesh, so that
    Godot reads one mesh of two surfaces whose first is exactly what `obj` alone would have been."""
    export_one(obj, path)
    if inner is None:
        return
    extra = os.path.join(HERE, "_throat.glb")
    export_one(inner, extra)
    merge_glb(path, extra)
    os.remove(extra)


def _read_glb(path):
    with open(path, "rb") as f:
        data = f.read()
    json_length = struct.unpack_from("<I", data, 12)[0]
    gltf = json.loads(data[20:20 + json_length])
    at = 20 + json_length
    bin_length = struct.unpack_from("<I", data, at)[0]
    return gltf, bytearray(data[at + 8:at + 8 + bin_length])


def merge_glb(path, extra):
    """Adds the first mesh of the .glb `extra` to the first mesh of the .glb `path` as more primitives (its
    accessors, buffer views, materials and binary data appended after `path`'s own, which are left as they were)."""
    base, data = _read_glb(path)
    more, more_data = _read_glb(extra)
    data += b"\0" * (-len(data) % 4)
    shift = len(data)
    views = len(base["bufferViews"])
    accessors = len(base["accessors"])
    materials = len(base.setdefault("materials", []))
    for view in more["bufferViews"]:
        view = dict(view)
        view["buffer"] = 0
        view["byteOffset"] = view.get("byteOffset", 0) + shift
        base["bufferViews"].append(view)
    for accessor in more["accessors"]:
        accessor = dict(accessor)
        accessor["bufferView"] += views
        base["accessors"].append(accessor)
    base["materials"] += more.get("materials", [])
    for primitive in more["meshes"][0]["primitives"]:
        primitive = dict(primitive)
        primitive["attributes"] = {k: v + accessors for k, v in primitive["attributes"].items()}
        if "indices" in primitive:
            primitive["indices"] += accessors
        if "material" in primitive:
            primitive["material"] += materials
        base["meshes"][0]["primitives"].append(primitive)
    data += more_data
    data += b"\0" * (-len(data) % 4)
    base["buffers"][0]["byteLength"] = len(data)
    text = json.dumps(base, separators=(",", ":")).encode("utf-8")
    text += b" " * (-len(text) % 4)
    total = 12 + 8 + len(text) + 8 + len(data)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(text), 0x4E4F534A))
        f.write(text)
        f.write(struct.pack("<II", len(data), 0x004E4942))
        f.write(data)


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
    views = [("left", (1, 0, 0), (0, 0, 0), 1.7), ("right", (-1, 0, 0), (0, 0, 0), 1.7),
             ("front", (0, 1, 0), (0, 0, 0), 1.1), ("back", (0, -1, 0), (0, 0, 0), 1.1),
             ("top", (0.001, 0, 1), (0, 0, 0), 1.7), ("under", (0.001, 0, -1), (0, 0, 0), 1.7),
             ("head", (0.8, 0.5, 0.2), (0, 0.5, 0), 0.6), ("tail", (0.7, -0.6, 0.3), (0, -0.55, 0), 0.7)]
    for low, obj in ((False, made[0]), (True, made[1])):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if low and view not in ("left", "head"):
                continue
            offset = Vector(direction).normalized() * 40.0
            camera.data.ortho_scale = frame * U
            camera.location = Vector(target) * U + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % ("lo_" if low else "", view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    up, down, wide = outline(HINGE)
    deep = max(a + b for _, a, b, _ in PROFILE) * U
    print("SHAPE %s: LENGTH=%.3f HINGE=%.4f HINGE_Y=%.4f GILL=%.3f EYE_AT=(%.3f, %.3f) depth=%.3f width=%.3f" % (
        NAME, LENGTH, HINGE, lip_c(HINGE) * down, GILL, EYE_AT[0], EYE_AT[1], deep, 2.0 * max(p[3] for p in PROFILE) * U))
    full, full_inner = make(NAME, False)
    low, low_inner = make(NAME + "_lo", True)
    os.makedirs(OUT, exist_ok=True)
    export(full, full_inner, os.path.join(OUT, NAME + ".glb"))
    export(low, low_inner, os.path.join(OUT, NAME + "_lo.glb"))
    # (the game model, built after the others are written out, so that they come out as they always did)
    game, _ = make(NAME + "_game", False, "game")
    export(game, None, os.path.join(OUT, NAME + "_game.glb"))
    here, out = eye_frame(1.0)
    print("EYE %s: EYE_MID=vec3(%.5f, %.5f, %.5f) EYE_OUT=vec3(%.5f, %.5f, %.5f) EYE_RADIUS=%.4f" % ((NAME,) + tuple(here) + tuple(out) + (EYE_RADIUS,)))
    # (in the .blend, each model's throat and gills ride with it)
    for owner, inner in ((full, full_inner), (low, low_inner)):
        inner.parent = owner
    low.location.x = LENGTH
    game.location.x = -LENGTH
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, NAME + ".blend"))
    low.location.x = 0.0
    game.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low])


if __name__ == "__main__":
    main()
