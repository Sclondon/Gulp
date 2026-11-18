"""Builds the bottlenose dolphin (creatures/dolphin) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/dolphin/tools/build_dolphin.py
    blender --background --python creatures/dolphin/tools/build_dolphin.py -- <preview folder>   # with pictures

Writes creatures/dolphin/models/dolphin_game.glb (the game model: Twilight Princess weight, its triangles spent
on the outline, the eye, the lips and the fin edges; added 2026-11-18), creatures/dolphin/models/dolphin.glb (the full model, for close pictures) and dolphin_lo.glb (far off,
phones), and the editable creatures/dolphin/tools/dolphin.blend (this folder has a .gdignore). Each model is one
still mesh with one surface: the shader (dolphin.gdshader) draws every marking, swims it and opens its mouth. It
prints a WINDING line: the check that nothing is inside out.

A common bottlenose dolphin (Tursiops truncatus), 2.8 m from the tip of its lower jaw to the tips of its flukes,
built from the species (no picture was traced):

- THE BODY: a stout smooth spindle, deepest (0.51 m) and widest (0.46 m) a little ahead of the middle, running
  back to a tail stock that is thin from side to side and keeled above and below. A short stubby beak, the lower
  jaw a little the longer; the melon (forehead) rising steeply from a crease at the root of the beak; a blowhole
  on top of the head (a dimple); a small eye on each side behind the corner of the mouth.
- THE MOUTH: the body's skin ahead of the corner of the mouth is only the upper head, closed underneath by the
  roof of the mouth; the LOWER JAW is its own closed part, flat on top (the floor of the mouth), which the shader
  swings down about the corner of the mouth. Twenty small conical teeth each side of each jaw, the upper ones
  hidden inside the lower jaw when the mouth is shut and the lower ones inside the upper.
- THE FINS, each a thin closed blade (two skins that meet at its edges): one curved dorsal fin in the middle of
  the back; two pointed flippers; the flukes, a flat horizontal blade with a notch in the middle.

Everything here is in Godot space (metres, Y up, its nose at -Z) until it is written out; the origin is on its
middle line, half way along (1.4 m behind the tip of its lower jaw). `xm` below is metres behind that tip.

What a point is, for the shader: UV2.y the part (0 body, 1 lower jaw, 2 an upper tooth, 3 a lower tooth, 4 the
flukes, 5 the dorsal fin, 6 a flipper, 7 an eye). UV2.x, on the body and the jaw: how much the point is inside
the mouth (0 skin, 1 the roof or the floor of the mouth). UV, on the body and jaw: x how far along (0 the tip to
1 the fluke tips), y how high on its side (1 the ridge of the back, 0 the keel of the belly); on a fin: x from
its root (0) to its tip (1), y from its leading edge (0) to its trailing edge (1); on an eye: x from its middle
(0) to its rim (1). (The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.)

The numbers marked "as the shader has it" are in dolphin.gdshader too: change one, change the other.
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

NAME = "dolphin"
LENGTH = 2.8
HALF = 1.4
BODY, JAW, TOOTH_UP, TOOTH_LOW, FLUKES, DORSAL, FLIPPER, EYE = range(8)
TAU = math.tau
PI = math.pi

# The whole outline, lower jaw and all: metres behind the tip, the height of the ridge of its back, the height
# of the keel of its belly, half its width.
PROFILE = [
    (0.0, -0.040, -0.058, 0.010),
    (0.012, -0.022, -0.076, 0.030),
    (0.05, -0.010, -0.090, 0.046),
    (0.10, -0.003, -0.101, 0.055),
    (0.125, 0.004, -0.106, 0.060),
    (0.16, 0.062, -0.115, 0.080),
    (0.21, 0.112, -0.130, 0.106),
    (0.29, 0.155, -0.152, 0.140),
    (0.42, 0.190, -0.180, 0.175),
    (0.60, 0.218, -0.212, 0.205),
    (0.90, 0.243, -0.246, 0.228),
    (1.20, 0.252, -0.258, 0.230),
    (1.50, 0.240, -0.248, 0.212),
    (1.80, 0.202, -0.212, 0.165),
    (2.10, 0.156, -0.164, 0.105),
    (2.35, 0.116, -0.120, 0.058),
    (2.55, 0.076, -0.078, 0.036),
    (2.68, 0.036, -0.036, 0.026),
    (2.745, 0.004, -0.004, 0.004),
]
# Where the upper head begins (the lower jaw is a little the longer) and where the body ends, in the notch of
# the flukes.
BODY_FROM = 0.012
BODY_TO = 2.745
JAW_FROM = 0.002

# As the shader has it: the corner of the mouth (where the lower jaw hinges), how far behind it the jaw's bend
# is spread, the eye, the blowhole.
CORNER = 0.30
WALL = 0.05
EYE_AT = (0.368, -0.004)
EYE_RADIUS = 0.016
BLOWHOLE = 0.41
# The lips' gap, how far the roof of the mouth is arched (of half its width), and how far behind the corner of
# the mouth the jaw runs on inside the body.
GAP = 0.0015
VAULT = 0.3
JAW_TAIL = 0.065
# The teeth: how many each side of each jaw, from where to where, how thick, how long, how far in from the lip.
TEETH = 20
TEETH_FROM = 0.03
TEETH_TO = 0.262
TOOTH_RADIUS = 0.0034
TOOTH_LONG = 0.011
TOOTH_IN = 0.0075
# Where the flukes hinge (as the shader has it).
JOINT = 2.5


def mouth_y(xm):
    """The line of the mouth: back along the beak, falling a little, and turned up at its corner (the 'smile')."""
    return -0.049 - 0.06 * xm + 0.036 * smooth(0.19, 0.31, xm)


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
    out[0] = max(out[0], out[1] + 0.001)
    out[2] = max(out[2], 0.0005)
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
    px = 1.0 + 0.7 * smooth(1.7, 2.4, xm)
    y = yc + c * (up - yc if c >= 0.0 else yc - down)
    x = math.copysign(abs(s) ** px, s) * wide
    return x, y


def sculpt(xm, x, y):
    """The small shapes pressed into the skin."""
    # the blowhole: a dimple on top of the head
    if abs(xm - BLOWHOLE) < 0.05 and y > 0.0:
        y -= 0.005 * math.exp(-((xm - BLOWHOLE) ** 2 + x * x) / 0.012 ** 2)
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
    return mouth_y(CORNER) + (bottom(xm) - 0.01 - mouth_y(CORNER)) * smooth(CORNER, CORNER + WALL, xm)


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


def pick(xs, values, tol, longest, keep=()):
    """For the game model: the fewest of the stations `xs` (in order) such that, between two kept ones, a
    straight line through `values` at them stays within `tol` (metres) of `values` at every station left out
    between them, and no two kept ones are more than `longest` apart (so that the shader's bends stay smooth);
    the stations in `keep` are always kept. So rings gather where the outline curves and stand far apart down
    the smooth flanks."""
    vals = [values(x) for x in xs]
    fixed = {i for i, x in enumerate(xs) if any(abs(x - k) < 1e-9 for k in keep)}
    kept = [0]
    i = 0
    while i < len(xs) - 1:
        j = i + 1
        while j + 1 < len(xs) and j not in fixed:
            c = j + 1
            reach = longest(xs[i]) if callable(longest) else longest
            # (and no step more than twice and a half the one before: faces that change size suddenly
            # show as a line in the shine)
            if len(kept) > 1:
                reach = min(reach, 2.5 * (xs[i] - xs[kept[-2]]))
            if xs[c] - xs[i] > reach:
                break
            ok = True
            for k in range(i + 1, c):
                f = (xs[k] - xs[i]) / (xs[c] - xs[i])
                if any(abs(a + (b - a) * f - v) > tol for a, b, v in zip(vals[i], vals[c], vals[k])):
                    ok = False
                    break
            if not ok:
                break
            j = c
        kept.append(j)
        i = j
    return [xs[i] for i in kept]


# The game model (Twilight Princess weight): how far its rings may stray from the outline (metres), the longest
# step between two rings, how many columns down each side to the lip and across the roof of the mouth.
GAME_TOL = 0.0016
GAME_LONGEST = 0.1
GAME_K = 12
GAME_R = 2


def game_angle(j, k, lip):
    """The angle round the body of column `j` of the game model's body: gathered a little towards the ridge of
    the back, the widest of the side and the lip, where the outline is seen, and spread over the flanks."""
    s = j / k

    def gather(t):
        return t - 0.35 * math.sin(TAU * t) / TAU

    return lip * (0.5 * gather(2.0 * s) if s <= 0.5 else 0.5 + 0.5 * gather(2.0 * s - 1.0))


def rings(low, game=False):
    if game:
        return pick(rings(False), lambda xm: (*outline(xm), clip_y(xm)), GAME_TOL, GAME_LONGEST)
    xs = []
    x = BODY_FROM
    for until, step in ((0.5, 0.008), (2.3, 0.024), (BODY_TO, 0.014)):
        if low:
            step *= 3.6
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


def body(m, low, game=False):
    """The body's skin, with the roof of the mouth: columns 0 (the ridge of the back) to K (the lip) down each
    side, then R more across the roof to its middle."""
    k = 9 if low else 36
    r = 2 if low else 5
    if game:
        k, r = GAME_K, GAME_R
    rows = []
    for xm in rings(low, game):
        up, down, _ = outline(xm)
        level = clip_y(xm)
        lip = angle_at(xm, level)
        half = []
        for j in range(k + 1):
            x, y = section(xm, game_angle(j, k, lip) if game else lip * j / k)
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
    first = rings(low, game)[0]
    cap(m, BODY, rows[0][0], Vector((0.0, 0.5 * (top(first) + mouth_y(first)), first - 0.006 - HALF)), 0.0, -1.0, "body")
    cap(m, BODY, rows[-1][0], Vector((0.0, 0.0, BODY_TO + 0.002 - HALF)), 0.0, 1.0, "body")


def jaw(m, low, game=False):
    """The lower jaw: columns 0 (the middle of the floor of the mouth) to R (the lip), then K more down the
    outside to the keel of the chin."""
    k = 5 if low else 16
    r = 2 if low else 5
    count = 9 if low else 40
    if game:
        k, r, count = 7, 2, 14
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
            f = 1.0 - (1.0 - shrink) * smooth(edge, edge + 0.012, p.y)
            q = Vector((p.x * f, ly + (p.y - ly) * f, p.z))
            row.append(m.add(q, (xm / LENGTH, high_of(xm, p.y)), JAW, inside))
        for p, inside in reversed(half[1:-1]):
            f = 1.0 - (1.0 - shrink) * smooth(edge, edge + 0.012, p.y)
            q = Vector((-p.x * f, ly + (p.y - ly) * f, p.z))
            row.append(m.add(q, (xm / LENGTH, high_of(xm, p.y)), JAW, inside))
        rows.append((row, 0.5 * (up + down)))
    around = len(rows[0][0])
    # (the floor: the columns either side of column 0)
    flat = []
    for row, middle in rows:
        flat.append((row[around - r:] + row[:around - r], middle))
    loft(m, JAW, flat, 0, 2 * r, Vector((0.0, 1.0, 0.0)), "jaw", "floor of the mouth")
    cap(m, JAW, rows[0][0], Vector((0.0, mouth_y(0.0) - GAP - 0.004, -HALF)), 0.0, -1.0, "jaw")
    cap(m, JAW, rows[-1][0], Vector((0.0, 0.5 * (mouth_y(CORNER) + bottom(to)), to + 0.002 - HALF)), 0.0, 1.0, "jaw")


def tooth(m, part, base, axis, radius, long, low, name):
    """A cone standing on `base` along `axis`."""
    sides = 4 if low else 6
    side = axis.cross(Vector((0.0, 0.0, 1.0))).normalized()
    other = axis.cross(side).normalized()
    levels = [(0.0, 1.0)] if low else [(0.0, 1.0), (0.5, 0.68)]
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


def teeth(m, low, game=False):
    count = TEETH // 2 if low else TEETH
    if game:
        # (fewer and simple cones, as the low model's)
        count, low = 11, True
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
                tooth(m, TOOTH_UP, base, Vector((sx * 0.12, -1.0, 0.0)).normalized(), TOOTH_RADIUS, TOOTH_LONG * 1.15, low, "upper teeth")
            # the lower jaw's: standing on the floor of the mouth, between the upper ones
            xm = TEETH_FROM + pitch * (i + 0.5)
            lx, ly = section(xm, angle_at(xm, mouth_y(xm) - GAP))
            x = lx - TOOTH_IN
            if x > TOOTH_RADIUS:
                base = Vector((sx * x, ly - TOOTH_LONG * 0.15, xm - HALF))
                tooth(m, TOOTH_LOW, base, Vector((sx * 0.12, 1.0, 0.0)).normalized(), TOOTH_RADIUS, TOOTH_LONG * 1.15, low, "lower teeth")


def on_skin(xm, y, sx):
    x, yy = section(xm, angle_at(xm, y))
    return sculpt(xm, sx * x, yy)


def eye(m, sx, low, game=False):
    """A low dome lying on the skin of the head."""
    spokes = 10 if low else 28
    steps = 2 if low else 7
    if game:
        # (round enough to stay round when the shader makes it a cartoon eye, twice the size)
        spokes, steps = 32, 3
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


def eye_frame():
    """Prints where the right eye sits, for the shader's cartoon eye (the left is its mirror): its middle on
    the skin, the way out of the head, the way to the nose and the way up in the eye's own plane, and how the
    skin falls away from the eye's plane round it (`EYE_SAG`: metres per square metre out from its middle)."""
    xe, ye = EYE_AT
    here = on_skin(xe, ye, 1.0)
    d = EYE_RADIUS * 0.3
    out = (on_skin(xe + d, ye, 1.0) - on_skin(xe - d, ye, 1.0)).cross(on_skin(xe, ye + d, 1.0) - on_skin(xe, ye - d, 1.0))
    out.normalize()
    if out.x < 0.0:
        out = -out
    fwd = Vector((0.0, 0.0, -1.0))
    fwd = (fwd - out * fwd.dot(out)).normalized()
    up = out.cross(fwd).normalized()
    if up.y < 0.0:
        up = -up
    sag = 0.0
    rho = EYE_RADIUS * 1.6
    for s in range(16):
        a = s / 16 * TAU
        p = on_skin(xe + math.cos(a) * rho, ye + math.sin(a) * rho, 1.0) - here
        flat = p - out * p.dot(out)
        sag += -p.dot(out) / max(1e-9, flat.length_squared)
    print("EYE_FRAME centre vec3(%.5f, %.5f, %.5f) out vec3(%.4f, %.4f, %.4f) fwd vec3(%.4f, %.4f, %.4f) up vec3(%.4f, %.4f, %.4f) EYE_SAG %.4f"
          % (here.x, here.y, here.z, out.x, out.y, out.z, fwd.x, fwd.y, fwd.z, up.x, up.y, up.z, sag / 16))


def blade(m, part, name, point, place, facing, thick, nt, nu, tip_gather=1.0):
    """A fin: a thin closed blade. `point(t, u)` is a place in the fin's own flat (t 0 at its root to 1 at
    its tip, u 0 at its leading edge to 1 at its trailing edge), `place` puts that in the model, `facing`
    is the way one of its two skins faces. It is `thick` at its root, a foil across (nothing at either
    edge), thinning to nothing at its tip."""
    for side in (1.0, -1.0):
        grid = []
        for ti in range(nt + 1):
            # (tip_gather over 1: the rows gather towards the tip, where the edges curve most)
            t = ti / nt if tip_gather == 1.0 else 1.0 - (1.0 - ti / nt) ** tip_gather
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


def fins(m, low, game=False):
    d = 3 if low else 1
    # (the game model: rows along each fin gathered to its tip, few across: a blade is seen by its edges)
    g = 1.35 if game else 1.0

    def n(full, game_n):
        return game_n if game else full // d

    # The dorsal fin: in the middle of the back, curved back like a sickle.
    yd = top(1.3)
    tip = (1.56, yd + 0.265)
    blade(m, DORSAL, "dorsal", swept(((1.09, top(1.09) - 0.012), (1.33, yd + 0.30), tip),
                                     ((1.50, top(1.50) - 0.012), (1.45, yd + 0.10), tip)),
          upright, SIDE, 0.03, n(26, 12), n(10, 4), g)
    for sx in (1.0, -1.0):
        # The flukes: a flat blade each side, swept back to a point, their trailing edges meeting in a notch.
        tip = (2.8, 0.355)
        blade(m, FLUKES, "flukes", swept(((2.47, 0.0), (2.6, 0.27), tip), ((2.735, 0.0), (2.725, 0.2), tip)),
              lambda p, sx=sx: Vector((sx * p[1], 0.0, p[0] - HALF)), UP, 0.028, n(26, 12), n(10, 4), g)
        # The flippers: pointed, swept back, held out and down.
        up, down, wide = outline(0.7)
        root = Vector((sx * (wide - 0.05), -0.125, 0.65 - HALF))
        span = Vector((sx * 0.62, -0.52, 0.58)).normalized()
        chord = Vector((sx * 0.1, -0.08, 1.0)).normalized()
        facing = span.cross(chord).normalized()
        if facing.y < 0.0:
            facing = -facing

        def flipper_point(t, u):
            t *= 0.985
            lead = 0.11 * t * t
            wide_here = 0.15 * (1.0 - t) ** 0.8 * (1.0 + 0.45 * t) + 0.004
            return (0.43 * t, lead + wide_here * u)

        blade(m, FLIPPER, "flippers", flipper_point,
              lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.026, n(22, 10), n(9, 4), g)


def make(name, low, game=False):
    m = Mesh()
    body(m, low, game)
    jaw(m, low, game)
    teeth(m, low, game)
    for sx in (1.0, -1.0):
        eye(m, sx, low, game)
    fins(m, low, game)
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
    bsdf.inputs["Base Color"].default_value = (0.45, 0.5, 0.56, 1.0)
    material.diffuse_color = (0.45, 0.5, 0.56, 1.0)
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
    for prefix, obj in zip(("", "lo_", "game_"), made):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if prefix == "lo_" and view not in ("left", "head"):
                continue
            offset = Vector(direction).normalized() * 100.0
            camera.data.ortho_scale = frame
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % (prefix, view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    full = make(NAME, False)
    low = make(NAME + "_lo", True)
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, NAME + ".glb"))
    export_one(low, os.path.join(OUT, NAME + "_lo.glb"))
    # The game model (added 2026-11-18): built after the other two are written, so that they come out as
    # they always have.
    game = make(NAME + "_game", False, True)
    export_one(game, os.path.join(OUT, NAME + "_game.glb"))
    eye_frame()
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
