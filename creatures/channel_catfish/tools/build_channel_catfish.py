"""Builds the channel catfish (creatures/channel_catfish) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/channel_catfish/tools/build_channel_catfish.py
    blender --background --python creatures/channel_catfish/tools/build_channel_catfish.py -- <preview folder>   # with pictures

Writes creatures/channel_catfish/models/channel_catfish.glb (the full model, for close pictures) and
channel_catfish_lo.glb (far off, phones), and the editable creatures/channel_catfish/tools/channel_catfish.blend
(this folder has a .gdignore). Each model is one still mesh with one surface: the shader
(channel_catfish.gdshader) draws every marking, swims it and lays its eight barbels along their ropes. It
prints a WINDING line (the check that nothing is inside out), a BARBEL line for each barbel and an OUTLINE
line for each row of the front of the body's outline (what channel_catfish.gd has in its BARBELS and its
OUTLINE: change one, change the other).

A channel catfish (Ictalurus punctatus), 0.6 m from the tip of its snout to the tips of its tail, built from
the species (the component's README says which photographs were looked at; none was traced):

- THE BODY: long and scaleless; a broad head flattened into a wedge, flat underneath, widest low down; the
  back rising from the snout to the dorsal fin; deepest (0.1 m) and widest (0.09 m) a quarter to a third of
  the way back; narrowing, and flattening from side to side, to the tail wrist. The wide mouth under the
  overhanging snout (a groove; the lower jaw set back); the gill cover, a step; small eyes low on the sides
  of the head (a low dome each).
- THE FINS, each a thin closed blade (two skins that meet at its edges): the dorsal (short at the root, tall,
  its leading edge a spine, leaning back); the fleshy adipose fin (a small lobe on the back before the tail,
  free at its rear); the deeply forked tail; the long round-edged anal fin; a pectoral fin low on each side
  behind the gill cover (its leading edge a spine); a pelvic fin on each side of the belly.
- THE BARBELS, eight tapering whiskers: one long one at each corner of the mouth, four across the chin (the
  outer two longer), one short one at each rear nostril. Built here lying at rest; in Godot the shader lays
  each along its rope (channel_catfish.gd simulates them).

Everything here is in Godot space (metres, Y up, X to its left side, its nose at -Z) until it is written out;
the origin is on the line through the middle of its tail wrist, half way along (0.3 m behind the tip of its
snout). `xm` below is metres behind the tip of the snout.

What a point is, for the shader: UV2.y the part (0 body, 1 dorsal, 2 adipose, 3 anal, 4 the tail, 5 a pectoral
fin, 6 a pelvic fin, 7 an eye, 8 a barbel). UV, on the body: x how far along (0 snout to 1 tail tips), y how
high on its side (1 the ridge of the back, 0 the keel of the belly); on a fin: x from its root (0) to its tip
(1), y from its leading edge (0) to its trailing edge (1); on an eye: x from its middle (0) to its rim (1); on
a barbel: x from its root (0) to its tip (1), y how far round it (0..1). UV2.x, on a barbel: which one (0 to
7, the whole part) and how thick it is at its root (the fraction: metres times 100). (The glTF writer flips V:
what is written here is 1 - v, so that Godot reads v.)

The numbers marked "as the shader has it" are in channel_catfish.gdshader too: change one, change the other.
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

LENGTH = 0.6
HALF = 0.3
BODY, DORSAL, ADIPOSE, ANAL, TAIL, PECTORAL, PELVIC, EYE, BARBEL = range(9)
TAU = math.tau

# The body's outline: metres behind the snout, the height of its back, of its belly, half its width, and the
# height at which it is widest (heights from the line through the middle of the tail wrist).
PROFILE = [
    (0.0, -0.0200, -0.0200, 0.0, -0.0200),
    (0.0015, -0.0145, -0.0250, 0.0125, -0.0205),
    (0.005, -0.0112, -0.0285, 0.0205, -0.0210),
    (0.012, -0.0070, -0.0320, 0.0282, -0.0215),
    (0.024, -0.0015, -0.0365, 0.0342, -0.0220),
    (0.042, 0.0050, -0.0415, 0.0388, -0.0220),
    (0.066, 0.0135, -0.0465, 0.0430, -0.0210),
    (0.090, 0.0215, -0.0505, 0.0456, -0.0190),
    (0.132, 0.0340, -0.0555, 0.0470, -0.0140),
    (0.180, 0.0455, -0.0595, 0.0442, -0.0080),
    (0.240, 0.0508, -0.0600, 0.0398, -0.0035),
    (0.300, 0.0502, -0.0545, 0.0348, 0.0),
    (0.360, 0.0470, -0.0420, 0.0290, 0.0020),
    (0.420, 0.0400, -0.0290, 0.0225, 0.0030),
    (0.468, 0.0290, -0.0210, 0.0160, 0.0020),
    (0.495, 0.0215, -0.0185, 0.0120, 0.0),
    (0.515, 0.0200, -0.0185, 0.0085, 0.0),
    (0.535, 0.0140, -0.0135, 0.0042, 0.0),
    (0.548, 0.0020, -0.0020, 0.0010, 0.0),
]
BODY_FROM = 0.0012
BODY_TO = 0.548

# As the shader has it: the line of the mouth, the edge of the gill cover, the eye.
MOUTH_TO = 0.031
EYE_AT = (0.050, -0.0115)
EYE_RADIUS = 0.0062


def mouth_y(xm):
    return -0.0236 - 0.14 * xm


def gill_x(y):
    return 0.138 - 13.0 * (y + 0.012) ** 2


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
for column in (1, 2, 3, 4):
    ys = [p[column] for p in PROFILE]
    _CURVES.append((ys, _slopes(_XS, ys)))


def outline(xm):
    """(the height of the back, of the belly, half the width, the height it is widest at) at `xm`."""
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
    out[2] = max(out[2], 0.0004)
    out[3] = min(max(out[3], out[1] + 0.0002), out[0] - 0.0002)
    return out


def top(xm):
    return outline(xm)[0]


def bottom(xm):
    return outline(xm)[1]


def body_point(xm, angle):
    """A point of the skin: `angle` round the body from the ridge of the back (0) by its left side (a
    quarter turn) to the keel of the belly (half a turn)."""
    up, down, wide, mid = outline(xm)
    c = math.cos(angle)
    s = math.sin(angle)
    # The head is a flattened wedge, squarer across (and flat underneath); the body an egg; the tail a blade.
    square = smooth(0.05, 0.22, xm)
    above = 0.80 + 0.16 * square
    below = 0.62 + 0.30 * square
    if c >= 0.0:
        y = mid + (c ** above) * (up - mid)
        side = (abs(s) ** above) * wide
    else:
        y = mid - ((-c) ** below) * (mid - down)
        side = (abs(s) ** below) * wide
    side = math.copysign(side, s)
    z = xm
    if xm < MOUTH_TO + 0.012:
        fade = 1.0 - smooth(MOUTH_TO - 0.008, MOUTH_TO + 0.006, xm)
        line = mouth_y(xm)
        # the mouth: a groove from under the tip of the snout back to its corners
        groove = math.exp(-((y - line) / 0.0016) ** 2) * fade * smooth(0.0, 0.004, xm)
        side *= 1.0 - 0.1 * groove
        # the lower jaw is set back under the snout, and a little narrower
        under = (1.0 - smooth(line - 0.0022, line + 0.0004, y)) * fade
        z += 0.0034 * under
        side *= 1.0 - 0.05 * under
    # the gill cover: it stands a little proud of the body behind its edge
    behind = xm - gill_x(y)
    if behind > 0.0 and wide > 0.01:
        mask = smooth(-0.97, -0.8, c) * (1.0 - smooth(0.55, 0.8, c))
        step = 0.0013 * smooth(0.0, 0.004, behind) * math.exp(-behind / 0.02) * mask
        side *= 1.0 - step / wide
    return Vector((side, y, z - HALF))


def skin_at(xm, y, sx):
    """The point of the skin at `xm` and height `y`, on the side `sx` (1 its left, -1 its right)."""
    lo, hi = 0.0, math.pi
    for _ in range(40):
        middle = 0.5 * (lo + hi)
        if body_point(xm, middle).y > y:
            lo = middle
        else:
            hi = middle
    return body_point(xm, sx * 0.5 * (lo + hi))


def skin_out(xm, wide, sx, upper):
    """The point of the skin at `xm`, `wide` out from the middle to the side `sx`, on the back (`upper`) or
    the belly."""
    lo, hi = (0.0, 0.5 * math.pi) if upper else (math.pi, 0.5 * math.pi)
    for _ in range(40):
        middle = 0.5 * (lo + hi)
        if abs(body_point(xm, middle).x) < wide:
            lo = middle
        else:
            hi = middle
    return body_point(xm, sx * 0.5 * (lo + hi))


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
        if n.length < 1e-14:
            return
        if n.dot(out) < 0.0:
            points = tuple(reversed(points))
        self.faces.append(tuple(points))
        self.out.append((Vector(out), name))
        self.count[name] = self.count.get(name, 0) + 1


def rings(low):
    xs = []
    x = BODY_FROM
    for until, step in ((0.012, 0.0009), (0.06, 0.0016), (0.16, 0.0024), (0.47, 0.0042), (BODY_TO, 0.0028)):
        if low:
            step *= 4.0
        n = max(1, round((until - x) / step))
        for i in range(n):
            xs.append(x + (until - x) * i / n)
        x = until
    xs.append(BODY_TO)
    return xs


def body(m, low):
    around = 24 if low else 88
    grid = []
    for xm in rings(low):
        up, down, _, _ = outline(xm)
        row = []
        for c in range(around):
            p = body_point(xm, c / around * TAU)
            row.append(m.add(p, (xm / LENGTH, (p.y - down) / (up - down)), BODY))
        grid.append(row)
    for r in range(len(grid) - 1):
        xm = 0.5 * (m.verts[grid[r][0]].z + m.verts[grid[r + 1][0]].z) + HALF
        mid = outline(xm)[3]
        for c in range(around):
            n = (c + 1) % around
            quad = (grid[r][c], grid[r][n], grid[r + 1][n], grid[r + 1][c])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((middle.x, middle.y - mid, 0.0)), "body")
    # the tip of the snout and the end inside the tail: a fan each
    for row, xm, way in ((grid[0], 0.0, -1.0), (grid[-1], BODY_TO + 0.001, 1.0)):
        y = outline(xm)[3]
        tip = m.add(Vector((0.0, y, xm - HALF)), (xm / LENGTH, 0.5), BODY)
        for c in range(around):
            m.face((tip, row[c], row[(c + 1) % around]), Vector((0.0, 0.0, way)), "body")


def eye(m, sx, low):
    """A low dome lying on the skin of the head."""
    spokes = 10 if low else 32
    steps = 3 if low else 10
    xe, ye = EYE_AT

    def on_skin(xm, y):
        return skin_at(xm, y, sx)

    here = on_skin(xe, ye)
    out = (on_skin(xe + 0.002, ye) - on_skin(xe - 0.002, ye)).cross(on_skin(xe, ye + 0.002) - on_skin(xe, ye - 0.002))
    out.normalize()
    if out.x * sx < 0.0:
        out = -out
    middle = m.add(here + out * 0.0024, (0.0, 0.0), EYE)
    last = None
    for k in range(1, steps + 1):
        r = k / steps
        row = []
        for s in range(spokes):
            a = s / spokes * TAU
            p = on_skin(xe + math.cos(a) * EYE_RADIUS * r, ye + math.sin(a) * EYE_RADIUS * r)
            row.append(m.add(p + out * (0.0022 * (1.0 - r * r) + 0.0002 * (1.0 - r)), (r, 0.0), EYE))
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


def swept(lead, trail, reach=0.985, round_from=1.0):
    """A fin drawn by its leading and trailing edges (three points each, root to tip). From `round_from`
    along it the two edges draw together in a round end."""
    def point(t, u):
        a = bezier(*lead, t * reach)
        b = bezier(*trail, t * reach)
        if t > round_from:
            close = math.sqrt(max(0.0, 1.0 - ((t - round_from) / (1.0 - round_from)) ** 2))
            u = 0.5 + (u - 0.5) * max(close, 0.02)
        return (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)
    return point


def upright(p):
    """A place in the flat of the middle fins (metres behind the snout, metres up) in the model."""
    return Vector((0.0, p[1], p[0] - HALF))


SIDE = Vector((1.0, 0.0, 0.0))


def fins(m, low):
    d = 3 if low else 1

    # The dorsal: short at the root, tall, its leading edge a stiff spine leaning back, its top edge falling
    # away to a short rear edge that overhangs the root.
    def dorsal_point(t, u):
        xm = 0.170 + 0.046 * u
        # (the top edge is rounded off at the spine's tip)
        high = 0.066 * (1.0 - 0.6 * u ** 1.3) * (0.86 + 0.14 * smooth(0.0, 0.1, u))
        return (xm + (0.34 + 0.3 * u) * high * t, top(xm) - 0.004 + (high + 0.004) * t)

    blade(m, DORSAL, "dorsal", dorsal_point, upright, SIDE, 0.006, 22 // d, 24 // d)

    # The adipose fin: a small fleshy lobe on the back before the tail, free at its rear.
    blade(m, ADIPOSE, "adipose", swept(((0.396, top(0.396) - 0.004), (0.426, top(0.41) + 0.023), (0.464, top(0.44) + 0.019)),
                                         ((0.433, top(0.433) - 0.004), (0.446, top(0.44) + 0.002), (0.464, top(0.44) + 0.008)), 1.0, 0.72),
          upright, SIDE, 0.009, 14 // d, 10 // d)

    # The anal fin: long, its edge rounded, deepest a third of the way along it.
    def anal_point(t, u):
        xm = 0.322 + 0.136 * u
        deep = 0.049 * (0.3 + 0.7 * smooth(0.0, 0.36, u)) * (1.0 - 0.62 * u ** 2.4)
        return (xm + 0.4 * deep * t, bottom(xm) + 0.005 - (deep + 0.005) * t)

    blade(m, ANAL, "anal", anal_point, upright, SIDE, 0.006, 18 // d, 48 // d)

    # The tail: deeply forked, two lobes that meet along the middle line.
    for way in (1.0, -1.0):
        blade(m, TAIL, "tail", swept(((0.488, 0.0), (0.522, 0.066 * way), (0.6, 0.078 * way)),
                                      ((0.553, 0.0), (0.562, 0.022 * way), (0.6, 0.052 * way)), 1.0, 0.8),
              upright, SIDE, 0.016, 36 // d, 16 // d)

    for sx in (1.0, -1.0):
        # The pectoral fins: low on the sides behind the gill cover, held out and back, a little down; a
        # fan, its leading edge a spine.
        root = skin_at(0.143, -0.036, sx)
        root.x -= sx * 0.005
        span = Vector((sx * 0.78, -0.3, 0.55)).normalized()
        chord = Vector((0.0, 0.42, 1.0))
        chord = (chord - span * chord.dot(span)).normalized()
        facing = span.cross(chord).normalized()
        if facing.y < 0.0:
            facing = -facing

        def pectoral_point(t, u):
            wide_here = 0.014 + 0.03 * smooth(0.0, 0.7, t) - 0.016 * smooth(0.72, 1.0, t)
            return (0.07 * t * (1.0 - 0.16 * u * u), 0.004 * t * t + wide_here * u)

        blade(m, PECTORAL, "pectorals", pectoral_point,
              lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.006, 20 // d, 16 // d)
        # The pelvic fins: on the belly, half way along, fanned back and out.
        root = skin_out(0.270, 0.016, sx, False)
        root.y += 0.004
        span = Vector((sx * 0.32, -0.42, 0.85)).normalized()
        chord = Vector((sx * 0.85, 0.3, 0.3))
        chord = (chord - span * chord.dot(span)).normalized()
        facing = span.cross(chord).normalized()
        if facing.y > 0.0:
            facing = -facing

        def pelvic_point(t, u):
            wide_here = 0.010 + 0.024 * smooth(0.0, 0.75, t) - 0.008 * smooth(0.75, 1.0, t)
            return (0.047 * t * (1.0 - 0.2 * (u - 0.4) ** 2), wide_here * (u - 0.3))

        blade(m, PELVIC, "pelvics", pelvic_point,
              lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.005, 14 // d, 12 // d)


def barbel_radius(thick, s):
    """As the shader has it: how thick a barbel is `s` along it (0 root .. 1 tip)."""
    return thick * (1.0 - 0.72 * s) * math.sqrt(min(1.0, (1.0 - s) * 30.0))


def barbels():
    """The eight barbels: (name, root, the way it leaves the head, the way it runs further out, how long,
    how thick at its root), all in the model's own space. The same list is BARBELS in channel_catfish.gd."""
    all_of = []
    for sx in (1.0, -1.0):
        # at each corner of the mouth: the long one
        root = skin_at(MOUTH_TO - 0.001, mouth_y(MOUTH_TO), sx)
        root.x -= sx * 0.0012
        all_of.append(("mouth", root, Vector((sx * 0.80, -0.30, 0.52)), Vector((sx * 0.38, -0.62, 0.68)), 0.115, 0.0021))
    for sx in (1.0, -1.0):
        # across the chin: the outer two
        root = skin_out(0.021, 0.0135, sx, False)
        root.y += 0.001
        all_of.append(("chin outer", root, Vector((sx * 0.32, -0.85, 0.42)), Vector((sx * 0.16, -0.6, 0.8)), 0.052, 0.0013))
    for sx in (1.0, -1.0):
        # and the inner two
        root = skin_out(0.018, 0.0048, sx, False)
        root.y += 0.001
        all_of.append(("chin inner", root, Vector((sx * 0.1, -0.9, 0.42)), Vector((sx * 0.05, -0.6, 0.8)), 0.036, 0.0011))
    for sx in (1.0, -1.0):
        # at each rear nostril: a short one
        root = skin_out(0.027, 0.0125, sx, True)
        root.y -= 0.0008
        all_of.append(("nostril", root, Vector((sx * 0.4, 0.85, -0.25)), Vector((sx * 0.5, 0.6, 0.6)), 0.024, 0.0010))
    return [(n, r, a.normalized(), b.normalized(), long, thick) for n, r, a, b, long, thick in all_of]


def barbel(m, which, root, way, way_on, long, thick, low):
    """A barbel: a tapering tube lying at rest (as channel_catfish.gd lays its rope at rest). The shader
    lays it again along the rope, from what its points say: how far along, how far round, how thick."""
    around = 5 if low else 9
    along = (8 if low else 30) if long > 0.08 else (5 if low else 16)
    fine = 96
    # the rest line, and a frame carried along it with the least turning
    line = [root.copy()]
    ways = []
    for i in range(fine):
        w = way.lerp(way_on, smooth(0.0, 0.6, (i + 0.5) / fine)).normalized()
        ways.append(w)
        line.append(line[-1] + w * (long / fine))
    ways.append(ways[-1])
    e1 = way.cross(Vector((0.0, 0.0, 1.0)) if abs(way.z) < 0.9 else Vector((1.0, 0.0, 0.0))).normalized()
    frames = []
    for w in ways:
        e1 = (e1 - w * e1.dot(w)).normalized()
        frames.append((e1.copy(), w.cross(e1)))
    last = None
    for i in range(along + 1):
        s = i / along
        f = round(s * fine)
        r = barbel_radius(thick, s)
        e1, e2 = frames[f]
        if i == along:
            tip = m.add(line[f], (1.0, 0.0), BARBEL, which + thick * 100.0)
            for c in range(around):
                m.face((last[c], last[(c + 1) % around], tip), ways[f], "barbels")
            break
        row = []
        for c in range(around):
            a = c / around * TAU
            row.append(m.add(line[f] + (e1 * math.cos(a) + e2 * math.sin(a)) * r, (s, c / around), BARBEL, which + thick * 100.0))
        if last is not None:
            for c in range(around):
                n = (c + 1) % around
                middle = sum((m.verts[q] for q in (last[c], last[n], row[n], row[c])), Vector()) * 0.25
                m.face((last[c], last[n], row[n], row[c]), middle - line[f], "barbels")
        last = row


def make(name, low):
    m = Mesh()
    body(m, low)
    for sx in (1.0, -1.0):
        eye(m, sx, low)
    fins(m, low)
    for which, (_, root, way, way_on, long, thick) in enumerate(barbels()):
        barbel(m, which, root, way, way_on, long, thick, low)
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
    material = bpy.data.materials.get("catfish") or bpy.data.materials.new("catfish")
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.3, 0.36, 0.4, 1.0)
    material.diffuse_color = (0.3, 0.36, 0.4, 1.0)
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
    """Nothing inside out: the skin of the body faces away from its middle, each skin of a fin away from
    the fin's own flat, an eye out from the head, a barbel's skin away from its own line (Blender's front
    is the side a face's normal is on)."""
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
    views = [("left", (1, 0, 0), (0, 0, 0), 0.72), ("right", (-1, 0, 0), (0, 0, 0), 0.72),
             ("front", (0, 1, 0), (0, 0, 0), 0.3), ("back", (0, -1, 0), (0, 0, 0), 0.3),
             ("top", (0.001, 0, 1), (0, 0, 0), 1.25), ("under", (0.001, 0, -1), (0, 0, 0), 1.25),
             ("head", (0.8, 0.6, 0.15), (0, 0.24, -0.01), 0.24), ("chin", (0.5, 0.7, -0.6), (0, 0.26, -0.02), 0.2),
             ("tail", (0.7, -0.6, 0.3), (0, -0.2, 0), 0.34)]
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
    for which, (named, root, way, way_on, long, thick) in enumerate(barbels()):
        print("BARBEL %d %s: [Vector3(%.5f, %.5f, %.5f), Vector3(%.3f, %.3f, %.3f), Vector3(%.3f, %.3f, %.3f), %.3f, %.4f]," % (
            which, named, root.x, root.y, root.z, way.x, way.y, way.z, way_on.x, way_on.y, way_on.z, long, thick))
    for row in PROFILE:
        if row[0] <= 0.2401:
            print("OUTLINE [%s]," % ", ".join("%g" % v for v in row))
    full = make("channel_catfish", False)
    low = make("channel_catfish_lo", True)
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, "channel_catfish.glb"))
    export_one(low, os.path.join(OUT, "channel_catfish_lo.glb"))
    low.location.x = 0.6
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "channel_catfish.blend"))
    low.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low])


if __name__ == "__main__":
    main()
