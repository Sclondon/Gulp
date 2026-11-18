"""Builds the blue marlin (creatures/blue_marlin) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/blue_marlin/tools/build_blue_marlin.py
    blender --background --python creatures/blue_marlin/tools/build_blue_marlin.py -- <preview folder>   # pictures

Writes creatures/blue_marlin/models/blue_marlin.glb (the full model) and blue_marlin_lo.glb (far off, phones),
and the editable creatures/blue_marlin/tools/blue_marlin.blend (this folder has a .gdignore). Each model is one
still mesh with one surface: the shader (blue_marlin.gdshader) draws every marking, opens its mouth and swims
it. It prints a WINDING line: the check that nothing is inside out.

A blue marlin (Makaira nigricans), 3.6 m from the tip of its bill to the tips of its tail, built from the
species (no picture was traced or copied):

- THE BODY: heavy and deep-shouldered. The upper jaw is a stout round bill; behind the eye the nape climbs
  steeply to the shoulders, where the body is deepest (0.61 m) and widest (0.36 m); from there it tapers to a
  narrow tail wrist with two keels on each side. The underside of the head ahead of the jaw's hinge is the
  ROOF OF THE MOUTH (flattened); the LOWER JAW is a part of its own, pointed, lying shut up against that roof,
  its top a shallow trough (the floor of the mouth). The shader swings it down about its hinge under the eye.
  The gill cover is a step; the eye a low dome on each side.
- THE FINS, each a thin closed blade (two skins that meet at its edges): the first dorsal (41 rays: a high
  pointed lobe at its front, lower than the body is deep, then low all the way along the back: no sail); a
  small second dorsal far back; two anal fins, the first a pointed lobe; the wide stiff crescent tail; two long
  pectoral fins held out, back and down; two thin pelvic fins, shorter than the pectorals.

Everything here is in Godot space (metres, Y up, X to its left side, its bill at -Z) until it is written out;
the origin is on the middle line of its body, half way along (1.8 m behind the tip of the bill). `xm` below is
metres behind the tip of the bill.

What a point is, for the shader: UV2.y the part (0 body, 1 the first dorsal, 2 the small middle fins, 3 the
lower jaw, 4 the tail, 5 a pectoral fin, 6 a pelvic fin, 7 an eye). UV, on the body: x how far along (0 bill
tip to 1 tail tips), y how high on its side (1 the ridge of the back, 0.5 its widest line, 0 the keel of the
belly); on a fin: x from its root (0) to its tip (1), y from its leading edge (0) to its trailing edge (1); on
the lower jaw: x from its tip (0) to its rear end (1), y from the middle of the mouth's floor (0) round to the
chin (1); on an eye: x from its middle (0) to its rim (1). UV2.x, on the body and the lower jaw: how much the
point is inside the mouth (1 the roof and the floor, hidden while the mouth is shut; 0 skin). (The glTF writer
flips V: what is written here is 1 - v, so that Godot reads v.)

The numbers marked "as the shader has it" are in blue_marlin.gdshader too: change one, change the other.
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

NAME = "blue_marlin"
LENGTH = 3.6
HALF = 1.8
BODY, DORSAL, SMALL, JAW, TAIL, PECTORAL, PELVIC, EYE = range(8)
TAU = math.tau

# The body's outline: metres behind the tip of the bill, its top, its bottom (metres above the middle line of
# the body), half its width. Ahead of the jaw's hinge the bottom is the roof of the mouth.
PROFILE = [
    (0.0, 0.016, 0.014, 0.001),
    (0.004, 0.019, 0.011, 0.004),
    (0.06, 0.025, 0.005, 0.010),
    (0.20, 0.032, -0.002, 0.017),
    (0.34, 0.040, -0.008, 0.024),
    (0.44, 0.048, -0.012, 0.031),
    (0.55, 0.064, -0.020, 0.043),
    (0.65, 0.090, -0.029, 0.060),
    (0.72, 0.118, -0.037, 0.076),
    (0.78, 0.150, -0.045, 0.092),
    (0.81, 0.166, -0.050, 0.100),
    (0.85, 0.192, -0.122, 0.111),
    (0.92, 0.232, -0.168, 0.129),
    (1.00, 0.266, -0.212, 0.149),
    (1.12, 0.298, -0.258, 0.170),
    (1.30, 0.310, -0.292, 0.180),
    (1.50, 0.300, -0.295, 0.178),
    (1.80, 0.262, -0.262, 0.160),
    (2.10, 0.204, -0.208, 0.131),
    (2.40, 0.142, -0.146, 0.098),
    (2.70, 0.088, -0.090, 0.066),
    (2.90, 0.058, -0.058, 0.046),
    (3.05, 0.040, -0.040, 0.036),
    (3.15, 0.031, -0.031, 0.030),
    (3.22, 0.030, -0.030, 0.018),
    (3.28, 0.003, -0.003, 0.002),
]
BODY_FROM = 0.004
BODY_TO = 3.28

# As the shader has it: the lower jaw's hinge (metres behind the bill's tip, metres above the middle line), the
# edge of the gill cover, the eye.
JAW_FROM = 0.42
JAW_TO = 0.95
HINGE = (0.81, -0.05)
EYE_AT = (0.775, 0.05)
EYE_RADIUS = 0.034
# How far the shut jaw's top lies inside the roof of the mouth; how flat the roof is (1 round, less flatter).
SINK = 0.004
ROOF = 0.5
# The first dorsal: where it starts and ends along the back, its rays.
DORSAL_FROM = 0.99
DORSAL_TO = 2.62
DORSAL_RAYS = 41


def gill_x(y):
    return 1.07 - 1.5 * (y + 0.03) ** 2


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
    """(top, bottom, half width) at `xm`."""
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
    out[1] = min(out[1], out[0] - 0.001)
    out[2] = max(out[2], 0.0005)
    return out


def top(xm):
    return outline(xm)[0]


def bottom(xm):
    return outline(xm)[1]


def middle(xm):
    up, down, _ = outline(xm)
    return (up + down) * 0.5


def side_power(xm):
    # (flat-sided behind the head, round at the bill and the tail wrist)
    return 0.94 - 0.12 * smooth(0.8, 1.1, xm) * (1.0 - smooth(2.7, 3.0, xm))


def roof_power(xm):
    """How round the lower half of the body is: 1 round, less where it is the flattened roof of the mouth."""
    mouth = smooth(JAW_FROM - 0.08, JAW_FROM + 0.06, xm) * (1.0 - smooth(HINGE[0], HINGE[0] + 0.07, xm))
    return 1.0 - (1.0 - ROOF) * mouth


def roof_y(xm, x):
    """How high the underside of the body is at `xm`, `x` to one side of the middle."""
    up, down, wide = outline(xm)
    yc = (up + down) * 0.5
    e = roof_power(xm)
    s = min(abs(x) / wide, 1.0) ** (1.0 / (side_power(xm) * e))
    return yc - (yc - down) * math.sqrt(max(1.0 - s * s, 0.0)) ** e


def body_point(xm, angle):
    """A point of the skin: `angle` round the body from the ridge of the back (0) by its left side (a
    quarter turn) to the keel of the belly (half a turn)."""
    up, down, wide = outline(xm)
    yc = (up + down) * 0.5
    c = math.cos(angle)
    s = math.sin(angle)
    power = side_power(xm)
    if c >= 0.0:
        y = yc + c * (up - yc)
    else:
        e = roof_power(xm)
        y = yc - (yc - down) * (-c) ** e
        power *= e
    side = math.copysign(abs(s) ** power, s) * wide
    # the keels: two ridges along each side of the tail wrist, one above the middle line, one below
    keel = 0.011 * smooth(3.0, 3.1, xm) * (1.0 - smooth(3.2, 3.265, xm))
    side += math.copysign(keel * (math.exp(-((c - 0.45) / 0.2) ** 2) + math.exp(-((c + 0.45) / 0.2) ** 2)), s)
    # the gill cover: it stands a little proud of the body behind its edge
    behind = xm - gill_x(y)
    if behind > 0.0 and wide > 0.01:
        mask = smooth(-0.95, -0.8, c) * (1.0 - smooth(0.4, 0.6, c))
        step = 0.007 * smooth(0.0, 0.006, behind) * math.exp(-behind / 0.06) * mask
        side *= 1.0 - step / wide
    return Vector((side, y, xm - HALF))


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        # per point: (uv, uv2)
        self.data = []
        # per face: the way it should face
        self.out = []
        self.count = {}

    def add(self, p, uv, part, inside=0.0):
        self.verts.append(p)
        self.data.append(((uv[0], 1.0 - uv[1]), (inside, 1.0 - part)))
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
    for until, step in ((0.40, 0.014), (1.10, 0.009), (3.0, 0.024), (BODY_TO, 0.008)):
        if low:
            step *= 4.0
        n = max(1, round((until - x) / step))
        for i in range(n):
            xs.append(x + (until - x) * i / n)
        x = until
    xs.append(BODY_TO)
    return xs


def jaw_at(xm):
    """The shut lower jaw at `xm`: (its chin, its half width, how high its lip is at its side)."""
    s = max(0.0, (xm - JAW_FROM) / (JAW_TO - JAW_FROM))
    xr = min(xm, HINGE[0])
    wide = min(outline(xr)[2] * 0.84, 0.006 + 0.2 * (xm - JAW_FROM))
    lip = roof_y(xr, wide) + SINK
    chin = -0.026 - 0.112 * s ** 1.1
    # (behind the hinge it narrows away into the throat)
    wide *= 1.0 - 0.9 * smooth(HINGE[0] - 0.06, JAW_TO, xm)
    return min(chin, lip - 0.004), wide, lip


def jaw_top(xm, x):
    """The floor of the mouth: the shut jaw's top lies just inside the roof, and follows it."""
    xr = min(xm, HINGE[0])
    return roof_y(xr, x) + SINK


def body(m, low):
    around = 20 if low else 64
    grid = []
    for xm in rings(low):
        row = []
        for c in range(around):
            angle = c / around * TAU
            p = body_point(xm, angle)
            inside = 0.0
            if JAW_FROM <= xm <= JAW_TO and math.cos(angle) < 0.0:
                chin, wide, _ = jaw_at(xm)
                inside = smooth(wide, wide * 0.86, abs(p.x)) * smooth(chin, chin + 0.006, p.y)
            row.append(m.add(p, (xm / LENGTH, 0.5 + 0.5 * math.cos(angle)), BODY, inside))
        grid.append(row)
    all_rings = rings(low)
    for r in range(len(grid) - 1):
        yc = middle((all_rings[r] + all_rings[r + 1]) * 0.5)
        for c in range(around):
            n = (c + 1) % around
            quad = (grid[r][c], grid[r][n], grid[r + 1][n], grid[r + 1][c])
            mid = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((mid.x, mid.y - yc, 0.0)), "body")
    # the tip of the bill and the end inside the tail: a fan each
    for row, xm, way in ((grid[0], 0.0, -1.0), (grid[-1], BODY_TO + 0.002, 1.0)):
        tip = m.add(Vector((0.0, middle(xm), xm - HALF)), (xm / LENGTH, 0.5), BODY)
        for c in range(around):
            m.face((tip, row[c], row[(c + 1) % around]), Vector((0.0, 0.0, way)), "body")


def jaw(m, low):
    """The lower jaw: a pointed, closed part of its own under the head, its rear end sunk in the throat. Its
    top is the floor of the mouth, its sides and chin skin."""
    around = 12 if low else 28
    count = 8 if low else 40
    grid = []
    for k in range(count + 1):
        share = k / count
        xm = JAW_FROM + (JAW_TO - JAW_FROM) * share
        chin, wide, lip = jaw_at(xm)
        row = []
        for c in range(around):
            angle = c / around * TAU
            x = wide * math.sin(angle)
            if math.cos(angle) > 0.0:
                y = jaw_top(xm, x)
            else:
                y = lip + (lip - chin) * math.cos(angle)
            inside = smooth(0.0, 0.3, math.cos(angle))
            row.append(m.add(Vector((x, y, xm - HALF)), (share, 0.5 - 0.5 * math.cos(angle)), JAW, inside))
        grid.append(row)
    for r in range(count):
        xm = JAW_FROM + (JAW_TO - JAW_FROM) * (r + 0.5) / count
        chin, wide, lip = jaw_at(xm)
        for c in range(around):
            n = (c + 1) % around
            quad = (grid[r][c], grid[r][n], grid[r + 1][n], grid[r + 1][c])
            mid = sum((m.verts[q] for q in quad), Vector()) * 0.25
            if math.cos((c + 0.5) / around * TAU) > 0.0:
                m.face(quad, Vector((0.0, 1.0, 0.0)), "mouth floor")
            else:
                m.face(quad, Vector((mid.x, mid.y - lip, 0.0)), "jaw")
    for row, xm, share, way in ((grid[0], JAW_FROM - 0.01, 0.0, -1.0), (grid[-1], JAW_TO + 0.002, 1.0, 1.0)):
        chin, wide, lip = jaw_at(max(xm, JAW_FROM))
        tip = m.add(Vector((0.0, (lip + chin) * 0.5, xm - HALF)), (share, 0.5), JAW)
        for c in range(around):
            m.face((tip, row[c], row[(c + 1) % around]), Vector((0.0, 0.0, way)), "jaw")


def eye(m, sx, low):
    """A low dome lying on the skin of the head."""
    spokes = 12 if low else 40
    steps = 3 if low else 12
    xe, ye = EYE_AT

    def on_skin(xm, y):
        up, down, _ = outline(xm)
        yc = (up + down) * 0.5
        if y >= yc:
            c = min(1.0, (y - yc) / (up - yc))
        else:
            c = -min(1.0, (yc - y) / (yc - down)) ** (1.0 / roof_power(xm))
        return body_point(xm, sx * math.acos(c))

    here = on_skin(xe, ye)
    out = (on_skin(xe + 0.004, ye) - on_skin(xe - 0.004, ye)).cross(on_skin(xe, ye + 0.004) - on_skin(xe, ye - 0.004))
    out.normalize()
    if out.x * sx < 0.0:
        out = -out
    centre = m.add(here + out * 0.007, (0.0, 0.0), EYE)
    last = None
    for k in range(1, steps + 1):
        r = k / steps
        row = []
        for s in range(spokes):
            a = s / spokes * TAU
            p = on_skin(xe + math.cos(a) * EYE_RADIUS * r, ye + math.sin(a) * EYE_RADIUS * r)
            row.append(m.add(p + out * (0.0062 * (1.0 - r * r) + 0.0008 * (1.0 - r)), (r, 0.0), EYE))
        for s in range(spokes):
            n = (s + 1) % spokes
            if last is None:
                m.face((centre, row[s], row[n]), out, "eyes")
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
    """A place in the flat of the middle fins (metres behind the bill's tip, metres up) in the model."""
    return Vector((0.0, p[1], p[0] - HALF))


SIDE = Vector((1.0, 0.0, 0.0))


def dorsal_high(u):
    """How long the first dorsal's ray is, `u` of the way along the fin: a high pointed lobe at the front
    with a hollow rear edge, then low all the way back; its edge scalloped between the rays."""
    peak = 0.045
    if u < peak:
        lobe = 0.5 + 0.5 * (u / peak) ** 0.8
    else:
        lobe = math.exp(-((u - peak) / 0.062) ** 1.1)
    low = 0.085 * smooth(0.0, 0.03, u) * (1.0 - 0.55 * u)
    scallop = 0.97 + 0.03 * abs(math.cos(math.pi * u * DORSAL_RAYS))
    return (0.42 * lobe + low) * scallop


def dorsal_lean(u):
    return math.radians(30.0 + 28.0 * smooth(0.0, 0.3, u))


def fins(m, low):
    d = 3 if low else 1

    # The first dorsal: each ray leans back, the later ones more.
    def dorsal_point(t, u):
        xm = DORSAL_FROM + (DORSAL_TO - DORSAL_FROM) * u
        high = dorsal_high(u) * t
        return (xm + math.sin(dorsal_lean(u)) * high, top(xm) - 0.02 + math.cos(dorsal_lean(u)) * high + 0.02 * t)

    blade(m, DORSAL, "first dorsal", dorsal_point, upright, SIDE, 0.022, 4 if low else 12,
          DORSAL_RAYS if low else DORSAL_RAYS * 4)
    # The second dorsal: small, far back, swept.
    y0 = top(2.72)
    tip = (2.93, y0 + 0.075)
    blade(m, SMALL, "second dorsal", swept(((2.70, top(2.70) - 0.012), (2.75, y0 + 0.10), tip),
                                           ((2.85, top(2.85) - 0.012), (2.87, y0 + 0.02), tip)),
          upright, SIDE, 0.01, 12 // d, 8 // d)
    # The first anal fin: a pointed swept lobe; the second, small, under the second dorsal.
    y0 = bottom(2.33)
    tip = (2.60, y0 - 0.22)
    blade(m, SMALL, "first anal", swept(((2.28, bottom(2.28) + 0.015), (2.33, y0 - 0.22), tip),
                                        ((2.55, bottom(2.55) + 0.015), (2.52, y0 - 0.03), tip)),
          upright, SIDE, 0.014, 14 // d, 10 // d)
    y0 = bottom(2.72)
    tip = (2.93, y0 - 0.07)
    blade(m, SMALL, "second anal", swept(((2.70, bottom(2.70) + 0.012), (2.75, y0 - 0.095), tip),
                                         ((2.85, bottom(2.85) + 0.012), (2.87, y0 - 0.02), tip)),
          upright, SIDE, 0.01, 12 // d, 8 // d)
    # The tail: a wide, stiff crescent, two narrow lobes that meet along the middle line.
    for way in (1.0, -1.0):
        tip = (3.6, 0.56 * way)
        blade(m, TAIL, "tail", swept(((3.12, 0.0), (3.33, 0.36 * way), tip),
                                     ((3.27, 0.0), (3.44, 0.25 * way), tip)),
              upright, SIDE, 0.03, 40 // d, 14 // d)
    for sx in (1.0, -1.0):
        # The pectoral fins: long, pointed, low on the side, held out, back and down.
        root = Vector((sx * (abs(body_point(1.13, 2.2).x) - 0.06), body_point(1.13, 2.2).y, 1.11 - HALF))
        span = Vector((sx * 0.38, -0.36, 0.85)).normalized()
        chord = Vector((0.0, -1.0, 0.2)).normalized()
        facing = span.cross(chord).normalized()
        if facing.x * sx < 0.0:
            facing = -facing

        def pectoral_point(t, u):
            t *= 0.985
            lead = 0.07 * t * t
            wide_here = 0.105 * (1.0 - t) ** 0.8 * (1.0 + 0.4 * t) + 0.005
            return (0.64 * t, lead + wide_here * u)

        blade(m, PECTORAL, "pectorals", pectoral_point,
              lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.018, 40 // d, 12 // d)
        # The pelvic fins: thin, shorter than the pectorals, from under them, trailing back and down.
        root = Vector((sx * 0.03, bottom(1.17) + 0.025, 1.17 - HALF))
        span = Vector((sx * 0.08, -0.5, 1.0)).normalized()
        chord = Vector((0.0, -1.0, 0.3)).normalized()
        facing = span.cross(chord).normalized()
        if facing.x * sx < 0.0:
            facing = -facing

        def pelvic_point(t, u):
            t *= 0.985
            return (0.38 * t, (0.02 * (1.0 - t) ** 0.6 + 0.005) * u)

        blade(m, PELVIC, "pelvics", pelvic_point,
              lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.014, 18 // d, 4 if not low else 2)


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
    material = bpy.data.materials.get(NAME) or bpy.data.materials.new(NAME)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.3, 0.45, 0.8, 1.0)
    material.diffuse_color = (0.3, 0.45, 0.8, 1.0)
    mesh.materials.append(material)
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    box = [(min(p[i] for p in m.verts), max(p[i] for p in m.verts)) for i in range(3)]
    print("BUILT %s verts=%d tris=%d" % (name, len(mesh.vertices), tris))
    print("BOX %s x %.3f..%.3f y %.3f..%.3f z %.3f..%.3f" % (name, box[0][0], box[0][1], box[1][0], box[1][1], box[2][0], box[2][1]))
    reach = {}
    for p, d in zip(m.verts, m.data):
        part = round(1.0 - d[1][1])
        r = reach.setdefault(part, [9.0, -9.0, 0.0])
        r[0] = min(r[0], p.y)
        r[1] = max(r[1], p.y)
        r[2] = max(r[2], abs(p.x))
    print("REACH %s (part: lowest, highest, furthest to a side): %s" % (name, ", ".join("%d: %.3f %.3f %.3f" % (k, *v) for k, v in sorted(reach.items()))))
    winding(name, mesh, m)
    return obj


def winding(name, mesh, m):
    """Nothing inside out: the skin of the body faces away from its middle line, each skin of a fin away
    from the fin's own flat, an eye out from the head (Blender's front is the side a face's normal is on)."""
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
    # (Blender space: the fish lies along Y, its bill at +Y, up is Z)
    views = [("left", (1, 0, 0), (0, 0, 0.0), 3.9), ("right", (-1, 0, 0), (0, 0, 0.0), 3.9),
             ("front", (0, 1, 0), (0, 0, 0.0), 1.8), ("back", (0, -1, 0), (0, 0, 0.0), 1.8),
             ("top", (0.001, 0, 1), (0, 0, 0), 3.9), ("under", (0.001, 0, -1), (0, 0, 0), 3.9),
             ("head", (0.8, 0.5, 0.2), (0, 1.0, 0), 1.3), ("head_under", (0.5, 0.5, -0.7), (0, 1.1, 0), 1.0),
             ("tail", (0.7, -0.6, 0.3), (0, -1.4, 0), 1.4)]
    for low, obj in ((False, made[0]), (True, made[1])):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if low and view not in ("left", "head"):
                continue
            offset = Vector(direction).normalized() * 40.0
            camera.data.ortho_scale = frame
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % ("lo_" if low else "", view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    full = make(NAME, False)
    low = make(NAME + "_lo", True)
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, NAME + ".glb"))
    export_one(low, os.path.join(OUT, NAME + "_lo.glb"))
    low.location.x = 1.6
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, NAME + ".blend"))
    low.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low])


if __name__ == "__main__":
    main()
