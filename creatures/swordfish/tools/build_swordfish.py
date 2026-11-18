"""Builds the swordfish (creatures/swordfish) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/swordfish/tools/build_swordfish.py
    blender --background --python creatures/swordfish/tools/build_swordfish.py -- <preview folder>   # with pictures

Writes creatures/swordfish/models/swordfish.glb (the full model, for close pictures) and swordfish_lo.glb (far
off, phones), and the editable creatures/swordfish/tools/swordfish.blend (this folder has a .gdignore). Each
model is one still mesh with one surface: the shader (swordfish.gdshader) draws every marking and swims it.
It prints a WINDING line: the check that nothing is inside out.

An adult swordfish (Xiphias gladius), 3 m from the tip of its sword to the tips of its tail, built from the
species (no picture was given, traced or copied):

- THE SWORD: the upper jaw, 0.95 m of it ahead of the lower jaw's tip: flat and broad like a blade (at its
  middle 0.08 m across and 0.02 m deep), oval in section.
- THE LOWER JAW: short and pointed, a part of its own under the sword's root, so that the mouth is a real gap;
  behind the mouth's corner it lies flush with the head. The mouth has a real inside: the head is cut off at
  the roof of the mouth and hollowed upwards from it, the jaw's top is hollowed too, both closed skins, so that
  when the shader swings the jaw down about its hinge (`gape`) there is a dark mouth to look into.
- THE BODY: stout and round, deepest (0.44 m) and widest (0.32 m) just behind the head, tapering to a narrow
  tail wrist with ONE large keel on each side. A very large eye, a low dome on each side. The gill cover, a
  step. No scales, no pelvic fins.
- THE FINS, each a thin closed blade (two skins that meet at its edges): a tall, rigid sickle of a first
  dorsal on a short base just behind the head; a tiny second dorsal far back; a first anal fin like a smaller
  sickle and a tiny second one; long sickle pectoral fins set low and held down and out; a wide stiff
  crescent tail.

Everything here is in Godot space (metres, Y up, X to its left side, its nose at -Z) until it is written out;
the origin is on its middle line, half way along (1.5 m behind the tip of the sword). `xm` below is metres
behind the tip of the sword.

What a point is, for the shader: UV2.y the part (0 body, 1 first dorsal, 2 the small fins, 3 the lower jaw, 4
the tail, 5 a pectoral fin, 6 an eye). UV, on the body: x how far along (0 sword tip to 1 tail tips), y how
high on its side (1 the ridge of the back, 0.5 its middle line, 0 the keel of the belly); on the lower jaw: the
same as on the body; on a fin: x from its root (0) to its tip (1), y from
its leading edge (0) to its trailing edge (1); on an eye: x from its middle (0) to its rim (1). UV2.x, on the body and the lower jaw: how far inside the mouth the point is (0 the
skin and the lips, 1 the middle of the mouth's roof or floor), for its dark lining. (The glTF
writer flips V: what is written here is 1 - v, so that Godot reads v.)

The numbers marked "as the shader has it" are in swordfish.gdshader too, and the lower jaw's and the pectoral
fins' places are in the component's swordfish_check.gd: change one, change the other.
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

LENGTH = 3.0
HALF = 1.5
BODY, DORSAL, FIN, JAW, TAIL, PECTORAL, EYE = range(7)
TAU = math.tau

# The outline of the sword, head and body: metres behind the sword's tip, half its depth above its middle
# line, half its depth below, half its width. (From the lower jaw's tip back, "below" is the underside of the whole head, jaw and all:
# `mouth_roof` cuts the mouth through it.)
PROFILE = [
    (0.0, 0.0, 0.0, 0.0),
    (0.004, 0.0018, 0.0018, 0.005),
    (0.03, 0.004, 0.004, 0.015),
    (0.15, 0.007, 0.006, 0.027),
    (0.40, 0.010, 0.008, 0.036),
    (0.70, 0.014, 0.010, 0.043),
    (0.88, 0.021, 0.013, 0.048),
    (0.95, 0.029, 0.016, 0.051),
    (0.965, 0.032, 0.024, 0.053),
    (1.02, 0.048, 0.042, 0.061),
    (1.08, 0.075, 0.064, 0.073),
    (1.14, 0.105, 0.088, 0.088),
    (1.20, 0.130, 0.114, 0.104),
    (1.26, 0.150, 0.145, 0.120),
    (1.34, 0.172, 0.185, 0.137),
    (1.44, 0.192, 0.210, 0.151),
    (1.54, 0.205, 0.224, 0.158),
    (1.66, 0.210, 0.228, 0.160),
    (1.85, 0.192, 0.207, 0.149),
    (2.05, 0.158, 0.170, 0.125),
    (2.25, 0.118, 0.125, 0.096),
    (2.42, 0.080, 0.083, 0.068),
    (2.55, 0.052, 0.053, 0.048),
    (2.64, 0.036, 0.036, 0.036),
    (2.70, 0.030, 0.030, 0.030),
    (2.76, 0.028, 0.028, 0.021),
    (2.80, 0.024, 0.024, 0.011),
    (2.84, 0.003, 0.003, 0.002),
]
BODY_FROM = 0.002
BODY_TO = 2.84

# As the shader has it: where the lower jaw's tip is, the edge of the gill cover, the eye.
SWORD = 0.95
JAW_FROM = 0.955
JAW_TO = 1.338
MOUTH_CORNER = 1.19
# How far up towards the top of the head the roof of the mouth is hollowed, along its middle.
MOUTH_HOLLOW = 0.4
# As the shader has it: where the lower jaw hinges (metres behind the sword's tip, metres up): the shader
# swings the whole jaw down about it to open the mouth (`gape`).
HINGE = (1.33, -0.16)
EYE_AT = (1.205, 0.04)
EYE_RADIUS = 0.05


def gill_x(y):
    return 1.43 - 1.5 * (y + 0.02) ** 2


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
    return body_skin(xm, angle)[0]


def lining(side, chord):
    """How far inside the mouth a point of its roof or floor is: 0 at the lips, 1 along the middle (no
    slope at the lips, so the lips themselves are as they would be on a flat cut)."""
    if chord < 1e-6 or abs(side) >= chord:
        return 0.0
    return (1.0 - (side / chord) ** 2) ** 2


def body_skin(xm, angle):
    """A point of the skin: `angle` round the body from the ridge of the back (0) by its left side (a
    quarter turn) to the keel of the belly (half a turn). And how far inside the mouth it is (0: not)."""
    inside = 0.0
    up, down, wide = outline(xm)
    c = math.cos(angle)
    s = math.sin(angle)
    y = c * (up if c >= 0.0 else down)
    side = math.copysign(abs(s) ** 0.92, s) * wide
    # the mouth: the head stops at its roof (the lower jaw, a part of its own, lies under it)
    # and is hollowed upwards from there, the inside of the mouth
    if JAW_FROM < xm < 1.34:
        roof = mouth_roof(xm)
        if y < roof:
            chord = wide * max(0.0, 1.0 - (roof / down) ** 2) ** 0.46
            inside = lining(side, chord) * smooth(0.97, 1.03, xm) * (1.0 - smooth(1.3, 1.335, xm))
            y = roof + MOUTH_HOLLOW * (up - roof) * inside * (1.0 - smooth(MOUTH_CORNER, 1.32, xm))
    # the keel: one large ridge along each side of the tail wrist
    keel = 0.032 * smooth(2.44, 2.62, xm) * (1.0 - smooth(2.72, 2.82, xm))
    side += math.copysign(keel * math.exp(-(c / 0.24) ** 2), s)
    # the gill cover: it stands a little proud of the body behind its edge
    behind = xm - gill_x(y)
    if behind > 0.0 and wide > 0.05 and xm < 1.8:
        mask = smooth(-0.95, -0.8, c) * (1.0 - smooth(0.4, 0.6, c))
        step = 0.008 * smooth(0.0, 0.008, behind) * math.exp(-behind / 0.07) * mask
        side *= 1.0 - step / wide
    return Vector((side, y, xm - HALF)), inside


def mouth_roof(xm):
    """How high the roof of the mouth is at `xm`: the line of the mouth as far back as its corner, then
    down round the back edge of the lower jaw to the belly."""
    line = -0.0155 - 0.125 * (xm - JAW_FROM)
    return line + (-outline(xm)[1] - line) * smooth(MOUTH_CORNER, 1.34, xm) ** 1.5


def jaw_floor(xm):
    """How high the lower jaw's flat top is: the mouth a little open ahead of its corner; behind it the
    jaw's edge is tucked just inside the head."""
    return mouth_roof(xm) - 0.004 + 0.008 * smooth(1.15, 1.20, xm)


def jaw_under(xm):
    # (the jaw stands a hair proud of the head's own line, so that the two skins never lie in one another)
    return -outline(xm)[1] * 1.012


def jaw_point(xm, angle):
    """A point of the lower jaw: the underside of the head's own section, cut off at `jaw_floor` and
    hollowed a little from there (the floor of the mouth). And how far inside the mouth it is (0: not)."""
    inside = 0.0
    up, down, wide = outline(xm)
    down *= 1.012
    wide *= 1.012
    floor = jaw_floor(xm)
    c = math.cos(angle)
    s = math.sin(angle)
    y = c * (up if c >= 0.0 else down)
    side = math.copysign(abs(s) ** 0.92, s) * wide
    if y > floor:
        chord = wide * max(0.0, 1.0 - (floor / down) ** 2) ** 0.46
        side = math.copysign(min(abs(side), chord), s)
        inside = lining(side, chord)
        y = floor - 0.3 * (floor + down) * inside
    return Vector((side, y, xm - HALF)), inside


def high_of(p):
    """How high on the side a point of the skin is, for the shader (1 the ridge of the back, 0 the belly)."""
    up, down, _ = outline(p.z + HALF)
    return 0.5 + 0.5 * max(-1.0, min(1.0, p.y / (up if p.y >= 0.0 else down)))


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
        self.verts.append(p)
        self.data.append(((uv[0], 1.0 - uv[1]), (high, 1.0 - part)))
        return len(self.verts) - 1

    def face(self, points, out, name):
        """A face wound so that its front (the side its points go round anticlockwise) is towards `out`."""
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
    for until, step in ((0.05, 0.006), (0.92, 0.02), (1.52, 0.0075), (2.42, 0.02), (BODY_TO, 0.0075)):
        if low:
            step *= 4.0
        n = max(1, round((until - x) / step))
        for i in range(n):
            xs.append(x + (until - x) * i / n)
        x = until
    xs.append(BODY_TO)
    return xs


def body(m, low):
    around = 24 if low else 80
    grid = []
    for xm in rings(low):
        row = []
        for c in range(around):
            angle = c / around * TAU
            p, inside = body_skin(xm, angle)
            row.append(m.add(p, (xm / LENGTH, high_of(p)), BODY, inside))
        grid.append(row)
    for r in range(len(grid) - 1):
        for c in range(around):
            n = (c + 1) % around
            quad = (grid[r][c], grid[r][n], grid[r + 1][n], grid[r + 1][c])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            if max(m.data[q][1][0] for q in quad) > 0.0:
                # (the roof of the mouth faces down, into the mouth)
                m.face(quad, Vector((0.0, -1.0, 0.0)), "mouth")
            else:
                m.face(quad, Vector((middle.x, middle.y, 0.0)), "body")
    # the tip of the sword and the end inside the tail: a fan each
    for row, xm, way in ((grid[0], 0.0, -1.0), (grid[-1], BODY_TO + 0.002, 1.0)):
        tip = m.add(Vector((0.0, 0.0, xm - HALF)), (xm / LENGTH, 0.5), BODY)
        for c in range(around):
            m.face((tip, row[c], row[(c + 1) % around]), Vector((0.0, 0.0, way)), "body")


def jaw(m, low):
    """The lower jaw: short and pointed, its tip free under the root of the sword, flush with the head
    behind the mouth's corner."""
    around = 16 if low else 48
    count = 12 if low else 46
    grid = []
    xs = [JAW_FROM + 0.003 + (JAW_TO - JAW_FROM - 0.003) * (i / count) for i in range(count + 1)]
    for xm in xs:
        row = []
        for c in range(around):
            angle = c / around * TAU
            p, inside = jaw_point(xm, angle)
            row.append(m.add(p, (xm / LENGTH, high_of(p)), JAW, inside))
        grid.append(row)
    for r in range(len(grid) - 1):
        for c in range(around):
            n = (c + 1) % around
            quad = (grid[r][c], grid[r][n], grid[r + 1][n], grid[r + 1][c])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            at = middle.z + HALF
            if max(m.data[q][1][0] for q in quad) > 0.0:
                # (the floor of the mouth faces up, into the mouth)
                m.face(quad, Vector((0.0, 1.0, 0.0)), "mouth")
                continue
            m.face(quad, Vector((middle.x, middle.y - (jaw_floor(at) + jaw_under(at)) * 0.5, 0.0)), "lower jaw")
    for row, xm, way in ((grid[0], JAW_FROM, -1.0), (grid[-1], JAW_TO + 0.002, 1.0)):
        tip = m.add(Vector((0.0, (jaw_floor(xm) + jaw_under(xm)) * 0.5, xm - HALF)), (xm / LENGTH, 0.1), JAW)
        for c in range(around):
            m.face((tip, row[c], row[(c + 1) % around]), Vector((0.0, 0.0, way)), "lower jaw")


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
    middle = m.add(here + out * 0.011, (0.0, 0.0), EYE)
    last = None
    for k in range(1, steps + 1):
        r = k / steps
        row = []
        for s in range(spokes):
            a = s / spokes * TAU
            p = on_skin(xe + math.cos(a) * EYE_RADIUS * r, ye + math.sin(a) * EYE_RADIUS * r)
            row.append(m.add(p + out * (0.010 * (1.0 - r * r) + 0.001 * (1.0 - r)), (r, 0.0), EYE))
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
    """A place in the flat of the middle fins (metres behind the sword's tip, metres up) in the model."""
    return Vector((0.0, p[1], p[0] - HALF))


SIDE = Vector((1.0, 0.0, 0.0))


def pectoral_frame(sx):
    """Where a pectoral fin is rooted, the way it runs out, the way across it, and the way it faces."""
    up, down, wide = outline(1.47)
    y = -0.145
    c = y / down
    root = Vector((sx * (wide * (1.0 - c * c) ** 0.46 - 0.035), y, 1.45 - HALF))
    span = Vector((sx * 0.56, -0.62, 0.55)).normalized()
    chord = Vector((0.0, 0.14, 1.0)).normalized()
    facing = span.cross(chord).normalized()
    if facing.y < 0.0:
        facing = -facing
    return root, span, chord, facing


def fins(m, low):
    d = 3 if low else 1
    # The first dorsal: a tall rigid sickle on a short base just behind the head; its leading edge rises
    # steeply and curves back to a point, its trailing edge is deeply hollowed.
    tip = (1.76, 0.585)
    blade(m, DORSAL, "first dorsal", swept(((1.36, top(1.36) - 0.02), (1.40, 0.575), tip),
                                            ((1.69, top(1.69) - 0.02), (1.585, 0.33), tip)),
          upright, SIDE, 0.022, 45 // d, 15 // d)
    # The first anal fin: a smaller sickle, pointing down and back.
    ya = bottom(2.14)
    tip = (2.37, ya - 0.215)
    blade(m, FIN, "first anal", swept(((2.09, bottom(2.09) + 0.015), (2.12, ya - 0.28), tip),
                                       ((2.29, bottom(2.29) + 0.015), (2.235, ya - 0.1), tip)),
          upright, SIDE, 0.014, 30 // d, 12 // d)
    # The second dorsal and the second anal fin: tiny, far back.
    for way, x0 in ((1.0, 2.50), (-1.0, 2.47)):
        y0 = (top(x0) if way > 0.0 else bottom(x0)) - 0.006 * way
        y1 = (top(x0 + 0.06) if way > 0.0 else bottom(x0 + 0.06)) - 0.006 * way
        tip = (x0 + 0.105, y1 + 0.05 * way)
        blade(m, FIN, "small fins", swept(((x0, y0), (x0 + 0.03, y0 + 0.07 * way), tip),
                                           ((x0 + 0.06, y1), (x0 + 0.075, y1 + 0.02 * way), tip), 0.97),
              upright, SIDE, 0.005, 9 // d, 6 // min(d, 2))
    # The tail: a wide stiff crescent, two lobes that meet along the middle line.
    for way in (1.0, -1.0):
        tip = (3.0, 0.48 * way)
        blade(m, TAIL, "tail", swept(((2.60, 0.0), (2.74, 0.27 * way), tip),
                                      ((2.83, 0.0), (2.915, 0.17 * way), tip)),
              upright, SIDE, 0.03, 42 // d, 14 // d)
    for sx in (1.0, -1.0):
        # The pectoral fins: long sickles set low on the body, held down and out, swept back.
        root, span, chord, facing = pectoral_frame(sx)

        def pectoral_point(t, u):
            t *= 0.985
            lead = 0.15 * t * t
            wide_here = 0.125 * (1.0 - t) ** 0.8 * (1.0 + 0.35 * t) + 0.005
            return (0.46 * t, lead + wide_here * u)

        blade(m, PECTORAL, "pectorals", pectoral_point,
              lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.02, 40 // d, 12 // d)
        if sx > 0.0:
            print("PECTORAL root=(%.4f, %.4f, %.4f) facing=(%.4f, %.4f, %.4f)" % (root.x, root.y, root.z, facing.x, facing.y, facing.z))


def make(name, low):
    m = Mesh()
    body(m, low)
    jaw(m, low)
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
    material = bpy.data.materials.get("swordfish") or bpy.data.materials.new("swordfish")
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.5, 0.5, 0.56, 1.0)
    material.diffuse_color = (0.5, 0.5, 0.56, 1.0)
    mesh.materials.append(material)
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    print("BUILT %s verts=%d tris=%d" % (name, len(mesh.vertices), tris))
    winding(name, mesh, m)
    return obj


def winding(name, mesh, m):
    """Nothing inside out: the skin of the body faces away from its middle line (the roof of its mouth
    down, the floor of it, on the jaw, up), the lower jaw's away from
    its own, each skin of a fin away from the fin's own flat, an eye out from the head (Blender's front is
    the side a face's normal is on)."""
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
    views = [("left", (1, 0, 0), (0, 0, 0), 3.3), ("right", (-1, 0, 0), (0, 0, 0), 3.3),
             ("front", (0, 1, 0), (0, 0, 0), 1.8), ("back", (0, -1, 0), (0, 0, 0), 1.8),
             ("top", (0.001, 0, 1), (0, 0, 0), 3.3), ("under", (0.001, 0, -1), (0, 0, 0), 3.3),
             ("head", (0.8, 0.5, 0.2), (0, 0.3, 0), 1.2), ("head_under", (0.6, 0.5, -0.6), (0, 0.4, 0), 1.0),
             ("tail", (0.7, -0.6, 0.3), (0, -1.1, 0), 1.4)]
    for low, obj in ((False, made[0]), (True, made[1])):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if low and view not in ("left", "head"):
                continue
            offset = Vector(direction).normalized() * 40.0
            camera.data.ortho_scale = frame
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y").to_euler()
            if abs(direction[2]) > 0.9:
                # (from above and below: its nose to the right of the picture)
                camera.rotation_euler = (0.0 if direction[2] > 0.0 else math.pi, 0.0, math.pi * 0.5)
            scene.render.filepath = os.path.join(folder, "%s%s.png" % ("lo_" if low else "", view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    full = make("swordfish", False)
    low = make("swordfish_lo", True)
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, "swordfish.glb"))
    export_one(low, os.path.join(OUT, "swordfish_lo.glb"))
    low.location.x = 3.0
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "swordfish.blend"))
    low.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low])


if __name__ == "__main__":
    main()
