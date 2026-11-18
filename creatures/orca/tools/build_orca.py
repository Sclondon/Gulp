"""Builds the orca (creatures/orca) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/orca/tools/build_orca.py
    blender --background --python creatures/orca/tools/build_orca.py -- <preview folder>   # with pictures

Writes creatures/orca/models/orca.glb (the full model, for close pictures and the player) and orca_lo.glb (far
off, phones), and the editable creatures/orca/tools/orca.blend (this folder has a .gdignore). Each model is one
still mesh with one surface: the shader (orca.gdshader) draws every marking, swims it, opens its mouth and sets
the shape of its dorsal fin. It prints a WINDING line: the check that nothing is inside out.

An orca, a killer whale (Orcinus orca), 7 m from the tip of its jaw to the tips of its flukes, built from the
species (no picture was traced). The scheme is GameCommon's bottlenose dolphin's (build_dolphin.py), made big:

- THE BODY: a robust smooth spindle, deepest (1.48 m) and widest (1.26 m) about a third of the way back, running
  back to a deep tail stock that is thin from side to side and keeled above and below. A blunt rounded head with
  no beak; the mouth a long, nearly straight line; a blowhole on top of the head; a small eye just above and behind
  the corner of the mouth.
- THE MOUTH: the body's skin ahead of the corner of the mouth is only the upper head, closed underneath by the roof
  of the mouth; the LOWER JAW is its own closed part, flat on top (the floor of the mouth), which the shader swings
  down about the corner of the mouth. Twelve big conical teeth each side of each jaw, interlocking.
- THE FINS, each a thin closed blade: the dorsal fin in the middle of the back (built as a bull's tall upright
  blade; the shader reshapes it, from the same numbers as here, to a female's shorter curved fin by `fin_tall`);
  two big rounded paddle flippers; the flukes, a broad flat horizontal blade with a notch in the middle.

Everything here is in Godot space (metres, Y up, its nose at -Z) until it is written out; the origin is on its
middle line, half way along (3.5 m behind the tip of its jaw). `xm` below is metres behind that tip.

What a point is, for the shader: UV2.y the part (0 body, 1 lower jaw, 2 an upper tooth, 3 a lower tooth, 4 the
flukes, 5 the dorsal fin, 6 a flipper, 7 an eye). UV2.x, on the body and the jaw: how much the point is inside
the mouth (0 skin, 1 the roof or the floor of the mouth). UV, on the body and jaw: x how far along (0 the tip to
1 the fluke tips), y how high on its side (1 the ridge of the back, 0 the keel of the belly); on a fin: x from
its root (0) to its tip (1), y from its leading edge (0) to its trailing edge (1); on an eye: x from its middle
(0) to its rim (1). (The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.)

The numbers marked "as the shader has it" are in orca.gdshader too: change one, change the other.
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "models")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = ARGS[0] if ARGS else ""

NAME = "orca"
LENGTH = 7.0
HALF = 3.5
BODY, JAW, TOOTH_UP, TOOTH_LOW, FLUKES, DORSAL, FLIPPER, EYE = range(8)
TAU = math.tau
PI = math.pi

# The whole outline, lower jaw and all: metres behind the tip, the height of the ridge of its back, the height
# of the keel of its belly, half its width.
PROFILE = [
    (0.0, -0.07, -0.19, 0.03),
    (0.03, 0.02, -0.25, 0.11),
    (0.10, 0.12, -0.31, 0.22),
    (0.25, 0.25, -0.40, 0.34),
    (0.45, 0.37, -0.48, 0.43),
    (0.70, 0.47, -0.55, 0.50),
    (1.00, 0.56, -0.61, 0.555),
    (1.50, 0.655, -0.68, 0.60),
    (2.20, 0.72, -0.735, 0.625),
    (2.80, 0.74, -0.74, 0.63),
    (3.50, 0.71, -0.69, 0.575),
    (4.20, 0.62, -0.58, 0.46),
    (4.90, 0.49, -0.46, 0.315),
    (5.60, 0.355, -0.34, 0.18),
    (6.10, 0.26, -0.255, 0.11),
    (6.45, 0.17, -0.165, 0.08),
    (6.70, 0.08, -0.08, 0.06),
    (6.86, 0.01, -0.01, 0.01),
]
# Where the upper head begins and where the body ends, in the notch of the flukes.
BODY_FROM = 0.02
BODY_TO = 6.86
JAW_FROM = 0.005

# As the shader has it: the corner of the mouth (where the lower jaw hinges), the eye, the blowhole.
CORNER = 0.62
WALL = 0.12
EYE_AT = (0.80, -0.04)
EYE_RADIUS = 0.032
BLOWHOLE = 1.2
# The lips' gap, how far the roof of the mouth is arched (of half its width), and how far behind the corner of
# the mouth the jaw runs on inside the body.
GAP = 0.004
VAULT = 0.3
JAW_TAIL = 0.16
# The teeth: how many each side of each jaw, from where to where, how thick, how long, how far in from the lip.
TEETH = 12
TEETH_FROM = 0.08
TEETH_TO = 0.54
TOOTH_RADIUS = 0.015
TOOTH_LONG = 0.05
TOOTH_IN = 0.035
# Where the flukes hinge (as the shader has it).
JOINT = 6.2
# The dorsal fin, as the shader has it: its leading and trailing edges, each three points (metres behind the tip,
# metres up) from root to tip; the two roots are the same for both shapes; the bull's (fin_tall 1) and the
# female's (fin_tall 0) middle points and tips. The model is built as the bull's.
DORSAL_LEAD_ROOT = (2.42, 0.69)
DORSAL_TRAIL_ROOT = (3.38, 0.675)
BULL = ((2.66, 1.65), (3.05, 1.42), (2.88, 2.56))
COW = ((2.92, 1.55), (3.28, 0.95), (3.52, 1.66))
DORSAL_REACH = 0.985


def mouth_y(xm):
    """The line of the mouth: back from the tip, nearly straight, falling a little, turned up at its corner."""
    return -0.125 - 0.05 * xm + 0.035 * smooth(0.42, 0.63, xm)


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
    """(the top, the bottom, half the width) at `xm`."""
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
        out.append(a + b)
    out[0] = max(out[0], out[1] + 0.002)
    out[2] = max(out[2], 0.001)
    return out


def top(xm):
    return outline(xm)[0]


def bottom(xm):
    return outline(xm)[1]


def section(xm, angle):
    """(x, y) of the whole outline's skin: `angle` round the body from the ridge of the back (0) by one side (a
    quarter turn) to the keel of the belly (half a turn)."""
    up, down, wide = outline(xm)
    yc = 0.5 * (up + down)
    c = math.cos(angle)
    s = math.sin(angle)
    # (the tail stock is keeled above and below: its section comes to an edge there)
    px = 1.0 + 0.7 * smooth(4.3, 6.0, xm)
    y = yc + c * (up - yc if c >= 0.0 else yc - down)
    x = math.copysign(abs(s) ** px, s) * wide
    return x, y


def sculpt(xm, x, y):
    """The small shapes pressed into the skin."""
    # the blowhole: a dimple on top of the head
    if abs(xm - BLOWHOLE) < 0.12 and y > 0.0:
        y -= 0.012 * math.exp(-((xm - BLOWHOLE) ** 2 + x * x) / 0.03 ** 2)
    return Vector((x, y, xm - HALF))


def angle_at(xm, level):
    """The angle round the body at which its skin is at the height `level`."""
    up, down, _ = outline(xm)
    if level >= up:
        return 0.0
    if level <= down:
        return PI
    yc = 0.5 * (up + down)
    c = (level - yc) / (up - yc if level >= yc else yc - down)
    return math.acos(max(-1.0, min(1.0, c)))


def clip_y(xm):
    """Under this the body's skin is cut away for the mouth: the line of the mouth as far as its corner, then
    a wall falling to the belly (the back of the mouth)."""
    if xm <= CORNER:
        return mouth_y(xm)
    return mouth_y(CORNER) + (bottom(xm) - 0.025 - mouth_y(CORNER)) * smooth(CORNER, CORNER + WALL, xm)


def high_of(xm, y):
    up, down, _ = outline(xm)
    return max(0.0, min(1.0, (y - down) / (up - down)))


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
        if n.length < 1e-13:
            return
        if n.dot(out) < 0.0:
            points = tuple(reversed(points))
        self.faces.append(tuple(points))
        self.out.append((Vector(out), name))
        self.count[name] = self.count.get(name, 0) + 1


def rings(low):
    xs = []
    x = BODY_FROM
    # (closer at the back of the mouth, where the skin's cut edge falls steeply from ring to ring)
    for until, step in ((CORNER, 0.018), (CORNER + WALL, 0.005), (1.3, 0.018), (5.8, 0.055), (BODY_TO, 0.03)):
        if low:
            step *= 3.2
        n = max(1, round((until - x) / step))
        for i in range(n):
            xs.append(x + (until - x) * i / n)
        x = until
    xs.append(BODY_TO)
    return xs


def loft(m, part, rows, flat_from, flat_to, flat_out, name, flat_name):
    """Joins rings of points into a skin. Each row is (list of point numbers, the row's middle); the faces
    between columns `flat_from` and `flat_to` are the flat of the mouth and face `flat_out`, the others face
    away from the row's middle."""
    around = len(rows[0][0])
    for r in range(len(rows) - 1):
        a, middle = rows[r]
        b = rows[r + 1][0]
        for c in range(around):
            n = (c + 1) % around
            quad = (a[c], a[n], b[n], b[c])
            if flat_from <= c < flat_to:
                m.face(quad, flat_out, flat_name)
            else:
                at = sum((m.verts[q] for q in quad), Vector()) * 0.25
                m.face(quad, Vector((at.x, at.y - middle, 0.0)), name)


def cap(m, part, row, tip, extra, way, name):
    """Closes the end of a skin with a fan to `tip`."""
    xm = tip.z + HALF
    point = m.add(tip, (xm / LENGTH, high_of(xm, tip.y)), part, extra)
    for c in range(len(row)):
        m.face((point, row[c], row[(c + 1) % len(row)]), Vector((0.0, 0.0, way)), name)


def column_angle(j, k, lip):
    """The angle round the body of column `j` of `k` down to the lip: the upper columns at the same angles in
    every ring (so that the skin over the head is not skewed where the mouth ends and the lip falls away to the
    belly), the rest spread from there to the lip."""
    upper = UPPER_SHARE * k
    if lip <= UPPER_ANGLE * 1.05:
        return lip * j / k
    if j <= upper:
        return UPPER_ANGLE * j / upper
    return UPPER_ANGLE + (lip - UPPER_ANGLE) * (j - upper) / (k - upper)


UPPER_ANGLE = 0.47 * PI
UPPER_SHARE = 0.55


def body(m, low):
    """The body's skin, with the roof of the mouth: columns 0 (the ridge of the back) to K (the lip) down each
    side, then R more across the roof to its middle."""
    k = 9 if low else 40
    r = 2 if low else 5
    rows = []
    for xm in rings(low):
        up, down, _ = outline(xm)
        level = clip_y(xm)
        lip = angle_at(xm, level)
        half = []
        for j in range(k + 1):
            x, y = section(xm, column_angle(j, k, lip))
            half.append((sculpt(xm, x, y), 0.0))
        lx, ly = section(xm, lip)
        for j in range(1, r + 1):
            f = j / r
            x = lx * (1.0 - f)
            arch = min(VAULT * lx, 0.45 * (up - ly)) * (1.0 - (1.0 - f) ** 2)
            half.append((Vector((x, ly + arch, xm - HALF)), 1.0))
        row = []
        for p, inside in half:
            row.append(m.add(p, (xm / LENGTH, high_of(xm, p.y)), BODY, inside))
        for p, inside in reversed(half[1:-1]):
            row.append(m.add(Vector((-p.x, p.y, p.z)), (xm / LENGTH, high_of(xm, p.y)), BODY, inside))
        rows.append((row, 0.5 * (up + down)))
    loft(m, BODY, rows, k, k + 2 * r, Vector((0.0, -1.0, 0.0)), "body", "roof of the mouth")
    first = rings(low)[0]
    cap(m, BODY, rows[0][0], Vector((0.0, 0.5 * (top(first) + mouth_y(first)), first - 0.012 - HALF)), 0.0, -1.0, "body")
    cap(m, BODY, rows[-1][0], Vector((0.0, 0.0, BODY_TO + 0.005 - HALF)), 0.0, 1.0, "body")


def jaw(m, low):
    """The lower jaw: columns 0 (the middle of the floor of the mouth) to R (the lip), then K more down the
    outside to the keel of the chin."""
    k = 5 if low else 18
    r = 2 if low else 5
    count = 10 if low else 46
    rows = []
    to = CORNER + JAW_TAIL
    for i in range(count + 1):
        xm = JAW_FROM + (to - JAW_FROM) * (i / count) ** 1.15
        up, down, _ = outline(xm)
        level = mouth_y(min(xm, CORNER)) - GAP
        lip = angle_at(xm, level)
        lx, ly = section(xm, lip)
        # (behind the corner of the mouth it runs on inside the body, a little smaller than the skin over it)
        shrink = 1.0 - (0.012 + 0.05 * smooth(CORNER, to, xm)) * (1.0 if xm > CORNER else 0.0)
        half = []
        for j in range(r):
            half.append((Vector((lx * j / r, ly, xm - HALF)), 1.0))
        for j in range(k + 1):
            x, y = section(xm, lip + (PI - lip) * j / k)
            half.append((Vector((x, y, xm - HALF)), 0.0))
        # (only where the body's skin is over it: below the body's cut edge, at the back of the mouth,
        # it is the skin, full size, so that no crack opens between the two)
        edge = clip_y(xm)
        row = []
        for p, inside in half:
            f = 1.0 - (1.0 - shrink) * smooth(edge, edge + 0.03, p.y)
            q = Vector((p.x * f, ly + (p.y - ly) * f, p.z))
            row.append(m.add(q, (xm / LENGTH, high_of(xm, p.y)), JAW, inside))
        for p, inside in reversed(half[1:-1]):
            f = 1.0 - (1.0 - shrink) * smooth(edge, edge + 0.03, p.y)
            q = Vector((-p.x * f, ly + (p.y - ly) * f, p.z))
            row.append(m.add(q, (xm / LENGTH, high_of(xm, p.y)), JAW, inside))
        rows.append((row, 0.5 * (up + down)))
    around = len(rows[0][0])
    # (the floor: the columns either side of column 0)
    flat = []
    for row, middle in rows:
        flat.append((row[around - r:] + row[:around - r], middle))
    loft(m, JAW, flat, 0, 2 * r, Vector((0.0, 1.0, 0.0)), "jaw", "floor of the mouth")
    cap(m, JAW, rows[0][0], Vector((0.0, mouth_y(0.0) - GAP - 0.01, -HALF)), 0.0, -1.0, "jaw")
    cap(m, JAW, rows[-1][0], Vector((0.0, 0.5 * (mouth_y(CORNER) + bottom(to)), to + 0.005 - HALF)), 0.0, 1.0, "jaw")


def tooth(m, part, base, axis, radius, long, low, name):
    """A cone standing on `base` along `axis`, bent a little back."""
    sides = 5 if low else 8
    side = axis.cross(Vector((0.0, 0.0, 1.0))).normalized()
    other = axis.cross(side).normalized()
    levels = [(0.0, 1.0)] if low else [(0.0, 1.0), (0.35, 0.9), (0.7, 0.55)]
    last = None
    for share, thick in levels:
        row = []
        for s in range(sides):
            a = s / sides * TAU
            p = base + axis * (long * share) + (side * math.cos(a) + other * math.sin(a)) * (radius * thick)
            row.append(m.add(p, (share, 0.0), part))
        if last is not None:
            for s in range(sides):
                n = (s + 1) % sides
                at = (m.verts[row[s]] + m.verts[row[n]]) * 0.5 - (base + axis * (long * share))
                m.face((last[s], last[n], row[n], row[s]), at, name)
        last = row
    tip = m.add(base + axis * long, (1.0, 0.0), part)
    for s in range(sides):
        n = (s + 1) % sides
        at = (m.verts[last[s]] + m.verts[last[n]]) * 0.5 - (base + axis * (long * 0.5))
        m.face((last[s], last[n], tip), at, name)


def teeth(m, low):
    count = TEETH // 2 if low else TEETH
    pitch = (TEETH_TO - TEETH_FROM) / count
    for i in range(count):
        for sx in (1.0, -1.0):
            # the upper jaw's: hanging from the roof of the mouth, just in from the lip
            xm = TEETH_FROM + pitch * i
            lx, ly = section(xm, angle_at(xm, mouth_y(xm)))
            x = lx - TOOTH_IN
            if x > TOOTH_RADIUS:
                up = top(xm)
                arch = min(VAULT * lx, 0.45 * (up - ly)) * (1.0 - (x / lx) ** 2)
                base = Vector((sx * x, ly + arch + TOOTH_LONG * 0.15, xm - HALF))
                tooth(m, TOOTH_UP, base, Vector((sx * 0.1, -1.0, 0.12)).normalized(), TOOTH_RADIUS, TOOTH_LONG * 1.15, low, "upper teeth")
            # the lower jaw's: standing on the floor of the mouth, between the upper ones
            xm = TEETH_FROM + pitch * (i + 0.5)
            lx, ly = section(xm, angle_at(xm, mouth_y(xm) - GAP))
            x = lx - TOOTH_IN
            if x > TOOTH_RADIUS:
                base = Vector((sx * x, ly - TOOTH_LONG * 0.15, xm - HALF))
                tooth(m, TOOTH_LOW, base, Vector((sx * 0.1, 1.0, 0.12)).normalized(), TOOTH_RADIUS, TOOTH_LONG * 1.15, low, "lower teeth")


def on_skin(xm, y, sx):
    x, yy = section(xm, angle_at(xm, y))
    return sculpt(xm, sx * x, yy)


def eye(m, sx, low):
    """A low dome lying on the skin of the head."""
    spokes = 10 if low else 28
    steps = 2 if low else 7
    xe, ye = EYE_AT
    here = on_skin(xe, ye, sx)
    d = EYE_RADIUS * 0.3
    out = (on_skin(xe + d, ye, sx) - on_skin(xe - d, ye, sx)).cross(on_skin(xe, ye + d, sx) - on_skin(xe, ye - d, sx))
    out.normalize()
    if out.x * sx < 0.0:
        out = -out
    bulge = EYE_RADIUS * 0.3
    middle = m.add(here + out * (bulge * 1.1), (0.0, 0.0), EYE)
    last = None
    for k in range(1, steps + 1):
        r = k / steps
        row = []
        for s in range(spokes):
            a = s / spokes * TAU
            p = on_skin(xe + math.cos(a) * EYE_RADIUS * r, ye + math.sin(a) * EYE_RADIUS * r, sx)
            row.append(m.add(p + out * (bulge * (1.0 - r * r) + bulge * 0.1 * (1.0 - r)), (r, 0.0), EYE))
        for s in range(spokes):
            n = (s + 1) % spokes
            if last is None:
                m.face((middle, row[s], row[n]), out, "eyes")
            else:
                m.face((last[s], row[s], row[n], last[n]), out, "eyes")
        last = row


def blade(m, part, name, point, place, facing, thick, nt, nu):
    """A fin: a thin closed blade. `point(t, u)` is a place in the fin's own flat (t 0 at its root to 1 at
    its tip, u 0 at its leading edge to 1 at its trailing edge), `place` puts that in the model, `facing`
    is the way one of its two skins faces. It is `thick` at its root, a foil across (nothing at either
    edge), thinning to nothing at its tip."""
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
                row.append(m.add(p, (t, u), part))
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
    """A place in the flat of the dorsal fin (metres behind the tip, metres up) in the model."""
    return Vector((0.0, p[1], p[0] - HALF))


SIDE = Vector((1.0, 0.0, 0.0))
UP = Vector((0.0, 1.0, 0.0))


def fins(m, low):
    d = 3 if low else 1
    # The dorsal fin: the bull's tall blade (the shader makes it a female's by `fin_tall`).
    lead_mid, trail_mid, tip = BULL
    blade(m, DORSAL, "dorsal", swept((DORSAL_LEAD_ROOT, lead_mid, tip), (DORSAL_TRAIL_ROOT, trail_mid, tip), DORSAL_REACH),
          upright, SIDE, 0.12, 30 // d, 12 // d)
    for sx in (1.0, -1.0):
        # The flukes: a broad flat blade each side, swept back to a point, their trailing edges meeting in a
        # notch.
        tip = (7.0, 1.12)
        blade(m, FLUKES, "flukes", swept(((6.1, 0.0), (6.42, 0.84), tip), ((6.84, 0.0), (6.8, 0.62), tip)),
              lambda p, sx=sx: Vector((sx * p[1], 0.0, p[0] - HALF)), UP, 0.08, 28 // d, 11 // d)
        # The flippers: big rounded paddles, held out, down and a little back.
        up, down, wide = outline(1.6)
        root = Vector((sx * (wide - 0.13), -0.36, 1.45 - HALF))
        span = Vector((sx * 0.72, -0.6, 0.36)).normalized()
        chord = Vector((sx * 0.08, -0.06, 1.0)).normalized()
        facing = span.cross(chord).normalized()
        if facing.y < 0.0:
            facing = -facing

        def flipper_point(t, u):
            t *= 0.99
            lead = 0.1 * t * t - 0.05 * math.sin(PI * t)
            wide_here = 0.52 * (0.72 + 0.4 * math.sin(PI * t ** 0.8)) * math.sqrt(max(0.0, 1.0 - t ** 3)) + 0.008
            return (1.08 * t, lead + wide_here * u)

        blade(m, FLIPPER, "flippers", flipper_point,
              lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.07, 24 // d, 10 // d)


def make(name, low):
    m = Mesh()
    body(m, low)
    jaw(m, low)
    teeth(m, low)
    for sx in (1.0, -1.0):
        eye(m, sx, low)
    fins(m, low)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) for p in m.verts], [], m.faces)
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
    bsdf.inputs["Base Color"].default_value = (0.05, 0.05, 0.06, 1.0)
    material.diffuse_color = (0.3, 0.3, 0.32, 1.0)
    mesh.materials.append(material)
    mesh.update()
    winding(name, mesh, m)
    # Points in the same place become one (the two sides of the belly behind the mouth, a blade's two skins
    # along its edges), so that the skin is shaded smoothly across them; a sharp fold (a lip, a blade's edge)
    # is then marked sharp.
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.set_sharp_from_angle(angle=math.radians(50.0))
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    print("BUILT %s verts=%d tris=%d" % (name, len(mesh.vertices), tris))
    return obj


def winding(name, mesh, m):
    """Nothing inside out: the skin of the body faces away from its middle line, the roof of the mouth down
    and its floor up, each skin of a fin away from the fin's own flat, a tooth away from its own middle, an
    eye out from the head (Blender's front is the side a face's normal is on)."""
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
    # (Blender space: it lies along Y, its nose at +Y, up is Z)
    f = LENGTH
    views = [("left", (1, 0, 0), (0, 0, 0), 1.12 * f), ("right", (-1, 0, 0), (0, 0, 0), 1.12 * f),
             ("front", (0, 1, 0), (0, 0, 0), 0.5 * f), ("back", (0, -1, 0), (0, 0, 0), 0.5 * f),
             ("top", (0.001, 0, 1), (0, 0, 0), 1.12 * f), ("under", (0.001, 0, -1), (0, 0, 0), 1.12 * f),
             ("head", (0.8, 0.5, 0.2), (0, 0.4 * f, 0), 0.3 * f), ("chin", (0.6, 0.5, -0.6), (0, 0.42 * f, 0), 0.25 * f),
             ("tail", (0.7, -0.6, 0.5), (0, -0.4 * f, 0), 0.4 * f)]
    for low, obj in ((False, made[0]), (True, made[1])):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if low and view not in ("left", "head"):
                continue
            offset = Vector(direction).normalized() * 100.0
            camera.data.ortho_scale = frame
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % ("lo_" if low else "", view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    print("HINGE_Y %.4f (the shader's)" % mouth_y(CORNER))
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
