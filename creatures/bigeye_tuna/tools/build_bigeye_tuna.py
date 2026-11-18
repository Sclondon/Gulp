"""Builds the bigeye tuna (creatures/bigeye_tuna) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/bigeye_tuna/tools/build_bigeye_tuna.py
    blender --background --python creatures/bigeye_tuna/tools/build_bigeye_tuna.py -- <preview folder>   # with pictures

Writes creatures/bigeye_tuna/models/bigeye_tuna.glb (the full model) and bigeye_tuna_lo.glb (far off,
phones), and the editable creatures/bigeye_tuna/tools/bigeye_tuna.blend (this folder has a .gdignore). Each
model is one still mesh with one surface: the shader (bigeye_tuna.gdshader) draws every marking, swims it and
works its jaw. It prints a WINDING line (the check that nothing is inside out) and a SHAPE line (the numbers
the shader shares).

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
3 a finlet, 4 the tail, 5 a pectoral fin, 6 a pelvic fin, 7 an eye). UV, on the body: x how far along (0 snout
to 1 tail tips), y how high on its side (1 the ridge of the back, 0.5 its middle line, 0 the keel of the
belly); on a fin: x from its root (0) to its tip (1), y from its leading edge (0) to its trailing edge (1); on
an eye: x from its middle (0) to its rim (1). UV2.x, on the first dorsal, how far the point stands above the
fin's root (metres), for folding it; on the body, what it is of the mouth: 0 skin, 1 the lower jaw's skin,
2 the roof of the mouth, 3 its floor (odd numbers swing with the jaw), 4 a tooth of the upper jaw, 5 of the
lower. (The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.)

The numbers marked "as the shader has it" are in the .gdshader too: change one, change the other.
"""

import math
import os
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
# ---------------------------------------------------------------------------------------------------------

U = LENGTH / 1.5
HALF = 0.75
BODY, DORSAL_PART, SICKLE, FINLET, TAIL, PECTORAL, PELVIC, EYE = range(8)
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


def body_point(xm, angle):
    """A point of the skin: `angle` round the body from the ridge of the back (0) by its left side (a
    quarter turn) to the keel of the belly (half a turn)."""
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
    if behind > 0.0 and wide > 0.01:
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
        self.count[name] = self.count.get(name, 0) + 1


def rings(low):
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
    around = LOW_AROUND if low else AROUND
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
    across = 4 if low else 12
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
    # the wall at the back
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
    # inside the other
    for sx in (1.0, -1.0):
        for upper in (True, False):
            for i in range(TEETH):
                share = (i + (0.0 if upper else 0.5)) / TEETH
                xm = HINGE * (0.05 + 0.75 * share)
                edge = lip_point(xm, sx, not upper)
                x = edge.x - sx * (0.005 if upper else 0.0036)
                long = TOOTH * (1.0 - 0.45 * share)
                root = Vector((x, mouth_y(xm, x, upper), edge.z))
                way = -1.0 if upper else 1.0
                point = Vector((x, edge.y + way * long, edge.z + 0.25 * long))
                ring = []
                thick = TOOTH * 0.24
                for q in range(5):
                    a = q / 5 * TAU
                    spot = root + Vector((math.cos(a) * thick, -way * thick * 0.6, math.sin(a) * thick))
                    ring.append(m.add(spot, (xm / 1.5, 0.5), BODY, TOOTH_UP if upper else TOOTH_DOWN))
                end = m.add(point, (xm / 1.5, 0.5), BODY, TOOTH_UP if upper else TOOTH_DOWN)
                for q in range(5):
                    a = (q + 0.5) / 5 * TAU
                    m.face((end, ring[q], ring[(q + 1) % 5]), Vector((math.cos(a), 0.0, math.sin(a))), "teeth")


def eye(m, sx, low):
    """A low dome lying on the skin of the head."""
    spokes = 12 if low else 40
    steps = 3 if low else 12
    xe, ye = EYE_AT

    def on_skin(xm, y):
        up, down, _ = outline(xm)
        c = max(-1.0, min(1.0, y / (up if y >= 0.0 else down)))
        return body_point(xm, sx * math.acos(c))

    here = on_skin(xe, ye)
    out = (on_skin(xe + 0.004, ye) - on_skin(xe - 0.004, ye)).cross(on_skin(xe, ye + 0.004) - on_skin(xe, ye - 0.004))
    out.normalize()
    if out.x * sx < 0.0:
        out = -out
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
    nt = max(nt, 2)
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

    blade(m, DORSAL_PART, "first dorsal", dorsal_point, upright, SIDE, 0.007, 12 // d, (spines * 6) // d,
          high=lambda t, u: (dorsal_high(u) * math.cos(lean) + 0.012) * t * U)
    # The second dorsal and the anal fin.
    for fin, edge, way, name in ((SECOND, top, 1.0, "second dorsal"), (ANAL, bottom, -1.0, "anal")):
        base = edge((fin["x0"] + fin["x1"]) * 0.5)
        tip = (fin["tip"][0], base + way * fin["tip"][1])
        blade(m, SICKLE, name,
              swept(((fin["x0"], edge(fin["x0"]) - way * 0.014), (fin["lead"][0], base + way * fin["lead"][1]), tip),
                    ((fin["x1"], edge(fin["x1"]) - way * 0.014), (fin["trail"][0], base + way * fin["trail"][1]), tip)),
              upright, SIDE, 0.011, 36 // d, 12 // d)
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
                  upright, SIDE, 0.0022, 8 // min(d, 2), 5 // min(d, 2))
    # The tail: a tall stiff crescent, two lobes that meet along the middle line.
    for way in (1.0, -1.0):
        tip = (1.5, TAIL_TIP * way)
        blade(m, TAIL, "tail", swept(((1.28, 0.0), (1.36, TAIL_TIP * 0.54 * way), tip),
                                      ((1.395, 0.0), (1.458, TAIL_TIP * 0.353 * way), tip)),
              upright, SIDE, 0.017, 40 // d, 14 // d)
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
              facing, 0.012, 40 // d, 12 // d)
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
              facing, 0.007, 14 // d, 8 // d)


def make(name, low):
    m = Mesh()
    body(m, low)
    for sx in (1.0, -1.0):
        eye(m, sx, low)
    fins(m, low)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) * U for p in m.verts], [], m.faces)
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
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    box = [max(abs(v.co[i]) for v in mesh.vertices) for i in range(3)]
    print("BUILT %s verts=%d tris=%d reach side=%.3f along=%.3f up/down=%.3f" % (name, len(mesh.vertices), tris, box[0], box[1], box[2]))
    winding(name, mesh, m)
    return obj


def winding(name, mesh, m):
    """Nothing inside out: the skin of the body faces away from its middle line, each skin of a fin away
    from the fin's own flat, an eye out from the head, the roof of the mouth down and its floor up (Blender's
    front is the side a face's normal is on)."""
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
    full = make(NAME, False)
    low = make(NAME + "_lo", True)
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, NAME + ".glb"))
    export_one(low, os.path.join(OUT, NAME + "_lo.glb"))
    low.location.x = LENGTH
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, NAME + ".blend"))
    low.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low])


if __name__ == "__main__":
    main()
