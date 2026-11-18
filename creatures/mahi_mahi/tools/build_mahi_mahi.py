"""Builds the mahi-mahi (creatures/mahi_mahi) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/mahi_mahi/tools/build_mahi_mahi.py
    blender --background --python creatures/mahi_mahi/tools/build_mahi_mahi.py -- <preview folder>   # pictures

Writes creatures/mahi_mahi/models/mahi_mahi.glb (the full model) and mahi_mahi_lo.glb (far off, phones), and
the editable creatures/mahi_mahi/tools/mahi_mahi.blend (this folder has a .gdignore). Each model is one still
mesh with one surface: the shader (mahi_mahi.gdshader) draws every marking, opens its mouth and swims it. It
prints a WINDING line: the check that nothing is inside out.
It also writes models/mahi_mahi_game.glb, the game model (about a tenth to a fifteenth of the full
model, at the weight of a Twilight Princess figure: see "The game model" further down), and the .blend holds
all three.

A mahi-mahi or dorado (Coryphaena hippurus), a bull, 1.2 m from the front of its forehead to the tips of its
tail, built from the species (no picture was traced or copied):

- THE BODY: long, tapering and flat-sided (compressed: about a third as wide as it is deep). The bull's
  forehead rises almost straight up from the upper lip to a high blunt crest; the body is deepest just behind
  the head and tapers evenly to a slim tail wrist (no keels, no finlets). The mouth is at the front, below the
  forehead; the underside of the head ahead of the jaw's hinge is the ROOF OF THE MOUTH (flattened); the LOWER
  JAW is a part of its own lying shut up against it, its top a shallow trough (the floor of the mouth). The
  shader swings it down about its hinge under the eye. The eye is low on the head, just above the corner of the
  mouth. The gill cover is a step.
- THE FINS, each a thin closed blade (two skins that meet at its edges): one long dorsal (60 rays) from over the
  eye nearly to the tail, tallest at its front; a long anal fin from the middle of the body nearly to the tail;
  a deeply forked tail of two long narrow lobes; two sickle-shaped pectoral fins; two pelvic fins under them.

Everything here is in Godot space (metres, Y up, X to its left side, its nose at -Z) until it is written out;
the origin is on the middle line of its body, half way along (0.6 m behind the front of the forehead). `xm`
below is metres behind the front of the upper lip.

What a point is, for the shader: UV2.y the part (0 body, 1 the dorsal fin, 2 the anal fin, 3 the lower jaw, 4
the tail, 5 a pectoral fin, 6 a pelvic fin, 7 an eye). UV, on the body: x how far along (0 nose to 1 tail
tips), y how high on its side (1 the ridge of the back, 0.5 its widest line, 0 the keel of the belly); on a fin:
x from its root (0) to its tip (1), y from its leading edge (0) to its trailing edge (1) (on the dorsal and the
anal fin, y is how far along the fin's length, front 0 to back 1); on the lower jaw: x from its tip (0) to its
rear end (1), y from the middle of the mouth's floor (0) round to the chin (1); on an eye: x from its middle (0)
to its rim (1). UV2.x, on the body and the lower jaw: how much the point is inside the mouth (1 the roof and
the floor, hidden while the mouth is shut; 0 skin). (The glTF writer flips V: what is written here is 1 - v, so
that Godot reads v.)

The numbers marked "as the shader has it" are in mahi_mahi.gdshader too: change one, change the other.
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

NAME = "mahi_mahi"
LENGTH = 1.2
HALF = 0.6
BODY, DORSAL, ANAL, JAW, TAIL, PECTORAL, PELVIC, EYE = range(8)
TAU = math.tau

# The body's outline: metres behind the front of the upper lip, its top, its bottom (metres above the middle
# line of the body), half its width. Ahead of the jaw's hinge the bottom is the roof of the mouth.
PROFILE = [
    (0.0, 0.004, -0.004, 0.002),
    (0.004, 0.016, -0.007, 0.008),
    (0.015, 0.046, -0.011, 0.015),
    (0.03, 0.080, -0.015, 0.021),
    (0.05, 0.110, -0.019, 0.027),
    (0.07, 0.129, -0.023, 0.032),
    (0.085, 0.138, -0.027, 0.035),
    (0.105, 0.144, -0.066, 0.038),
    (0.14, 0.149, -0.097, 0.041),
    (0.20, 0.151, -0.112, 0.043),
    (0.28, 0.146, -0.116, 0.043),
    (0.40, 0.130, -0.110, 0.040),
    (0.55, 0.103, -0.092, 0.035),
    (0.70, 0.074, -0.068, 0.028),
    (0.83, 0.048, -0.045, 0.020),
    (0.93, 0.030, -0.029, 0.014),
    (0.99, 0.022, -0.021, 0.011),
    (1.03, 0.019, -0.019, 0.009),
    (1.047, 0.012, -0.012, 0.006),
    (1.058, 0.002, -0.002, 0.002),
]
BODY_FROM = 0.004
BODY_TO = 1.058

# As the shader has it: the lower jaw's hinge (metres behind the lip, metres above the middle line), the eye.
JAW_FROM = 0.003
JAW_TO = 0.13
HINGE = (0.085, -0.024)
EYE_AT = (0.068, 0.024)
EYE_RADIUS = 0.017
# How far the shut jaw's top lies inside the roof of the mouth; how flat the roof is (1 round, less flatter).
SINK = 0.0015
ROOF = 0.5
# The dorsal fin: where it starts and ends along the back, its rays. The anal fin's the same.
DORSAL_FROM = 0.062
DORSAL_TO = 1.0
DORSAL_RAYS = 60
ANAL_FROM = 0.52
ANAL_TO = 1.0
ANAL_RAYS = 27


def gill_x(y):
    """The edge of the gill cover (as the shader has it)."""
    return 0.168 - 2.2 * (y - 0.02) ** 2


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
    # (flat-sided along the body, rounder at the lips and the tail wrist)
    return 0.92 - 0.14 * smooth(0.06, 0.2, xm) * (1.0 - smooth(0.9, 1.02, xm))


def roof_power(xm):
    """How round the lower half of the body is: 1 round, less where it is the flattened roof of the mouth."""
    mouth = smooth(JAW_FROM - 0.01, JAW_FROM + 0.02, xm) * (1.0 - smooth(HINGE[0], HINGE[0] + 0.015, xm))
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
    # the gill cover: it stands a little proud of the body behind its edge
    behind = xm - gill_x(y)
    if behind > 0.0 and wide > 0.01:
        mask = smooth(-0.95, -0.8, c) * (1.0 - smooth(0.5, 0.7, c))
        step = 0.0025 * smooth(0.0, 0.003, behind) * math.exp(-behind / 0.025) * mask
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
    for until, step in ((0.16, 0.004), (0.95, 0.008), (BODY_TO, 0.004)):
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
    wide = min(outline(xr)[2] * 0.88, 0.003 + 0.45 * (xm - JAW_FROM))
    chin = -0.009 - 0.062 * s
    # (behind the hinge it narrows away into the throat)
    wide *= 1.0 - 0.9 * smooth(HINGE[0] - 0.01, JAW_TO, xm)
    lip = roof_y(xr, wide) + SINK
    return min(chin, lip - 0.003), wide, lip


def jaw_top(xm, x):
    """The floor of the mouth: the shut jaw's top lies just inside the roof, and follows it."""
    xr = min(xm, HINGE[0])
    return roof_y(xr, x) + SINK


def body(m, low):
    around = 16 if low else 48
    angles = [c / around * TAU for c in range(around)]
    all_rings = rings(low)
    if GAME:
        angles = game_angles()
        around = len(angles)
        all_rings = game_rings()
    grid = []
    for xm in all_rings:
        row = []
        for angle in angles:
            p = body_point(xm, angle)
            inside = 0.0
            if JAW_FROM <= xm <= JAW_TO and math.cos(angle) < 0.0:
                chin, wide, _ = jaw_at(xm)
                inside = smooth(wide, wide * 0.86, abs(p.x)) * smooth(chin, chin + 0.002, p.y)
                # (the roof of the mouth ends at the hinge: the throat behind it is skin)
                inside *= 1.0 - smooth(HINGE[0] - 0.004, HINGE[0] + 0.008, xm)
            row.append(m.add(p, (xm / LENGTH, 0.5 + 0.5 * math.cos(angle)), BODY, inside))
        grid.append(row)
    for r in range(len(grid) - 1):
        yc = middle((all_rings[r] + all_rings[r + 1]) * 0.5)
        for c in range(around):
            n = (c + 1) % around
            quad = (grid[r][c], grid[r][n], grid[r + 1][n], grid[r + 1][c])
            mid = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((mid.x, mid.y - yc, 0.0)), "body")
    # the tip of the lips and the end inside the tail: a fan each
    for row, xm, way in ((grid[0], 0.0, -1.0), (grid[-1], BODY_TO + 0.001, 1.0)):
        tip = m.add(Vector((0.0, middle(xm), xm - HALF)), (xm / LENGTH, 0.5), BODY)
        for c in range(around):
            m.face((tip, row[c], row[(c + 1) % around]), Vector((0.0, 0.0, way)), "body")


def jaw(m, low):
    """The lower jaw: a pointed, closed part of its own under the head, its rear end sunk in the throat. Its
    top is the floor of the mouth, its sides and chin skin."""
    # (a multiple of four, so that no face straddles the edge of the floor of the mouth)
    around = 12 if low else 24
    count = 6 if low else 28
    if GAME:
        around, count = GAME_JAW
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
    for row, xm, share, way in ((grid[0], JAW_FROM - 0.003, 0.0, -1.0), (grid[-1], JAW_TO + 0.001, 1.0, 1.0)):
        chin, wide, lip = jaw_at(max(xm, JAW_FROM))
        tip = m.add(Vector((0.0, (lip + chin) * 0.5, xm - HALF)), (share, 0.5), JAW)
        for c in range(around):
            m.face((tip, row[c], row[(c + 1) % around]), Vector((0.0, 0.0, way)), "jaw")


def eye(m, sx, low):
    """A low dome lying on the skin of the head."""
    spokes = 10 if low else 32
    steps = 2 if low else 8
    if GAME:
        spokes, steps = GAME_EYE
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
    if sx > 0.0:
        # (as the shader has it, for the cartoon eye: where the middle of the eye lies on the skin)
        print("EYE_MIDDLE (%.4f, %.4f, %.4f)" % (here.x, here.y, here.z))
    out =(on_skin(xe + 0.002, ye) - on_skin(xe - 0.002, ye)).cross(on_skin(xe, ye + 0.002) - on_skin(xe, ye - 0.002))
    out.normalize()
    if out.x * sx < 0.0:
        out = -out
    centre = m.add(here + out * 0.0035, (0.0, 0.0), EYE)
    last = None
    for k in range(1, steps + 1):
        r = k / steps
        row = []
        for s in range(spokes):
            a = s / spokes * TAU
            p = on_skin(xe + math.cos(a) * EYE_RADIUS * r, ye + math.sin(a) * EYE_RADIUS * r)
            row.append(m.add(p + out * (0.003 * (1.0 - r * r) + 0.0004 * (1.0 - r)), (r, 0.0), EYE))
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
    edge), thinning to nothing at its tip. (For the game model, `blade_game` places its points instead.)"""
    if GAME:
        blade_game(m, part, name, point, place, facing, thick)
        return
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
    """A place in the flat of the middle fins (metres behind the lip, metres up) in the model."""
    return Vector((0.0, p[1], p[0] - HALF))


SIDE = Vector((1.0, 0.0, 0.0))


def dorsal_high(u):
    """How long the dorsal's ray is, `u` of the way along the fin: tallest at its front over the head, then
    lower and even all the way back, dropping away at its end (the rays are drawn by the shader)."""
    high = (0.05 + 0.036 * math.exp(-u / 0.12)) * (1.0 - 0.35 * u)
    high *= (0.35 + 0.65 * smooth(0.0, 0.03, u)) * (1.0 - 0.75 * smooth(0.95, 1.0, u))
    return high


def anal_high(u):
    """The anal fin's ray: a pointed lobe at its front with a hollow behind it, then low and even."""
    high = 0.03 + 0.03 * math.exp(-u / 0.13)
    high *= (0.3 + 0.7 * smooth(0.0, 0.05, u)) * (1.0 - 0.75 * smooth(0.94, 1.0, u))
    return high


def fins(m, low):
    d = 3 if low else 1

    # The dorsal: each ray leans back, the later ones more. (Its root sinks a little into the back.)
    def dorsal_point(t, u):
        xm = DORSAL_FROM + (DORSAL_TO - DORSAL_FROM) * u
        lean = math.radians(22.0 + 26.0 * smooth(0.0, 0.5, u))
        high = dorsal_high(u) * t
        return (xm + math.sin(lean) * high, top(xm) - 0.004 + math.cos(lean) * high + 0.004 * t)

    blade(m, DORSAL, "dorsal", dorsal_point, upright, SIDE, 0.006, 3 if low else 8,
          DORSAL_RAYS // 2 if low else DORSAL_RAYS * 2)

    def anal_point(t, u):
        xm = ANAL_FROM + (ANAL_TO - ANAL_FROM) * u
        lean = math.radians(30.0 + 20.0 * smooth(0.0, 0.5, u))
        high = anal_high(u) * t
        return (xm + math.sin(lean) * high, bottom(xm) + 0.004 - math.cos(lean) * high - 0.004 * t)

    blade(m, ANAL, "anal", anal_point, upright, SIDE, 0.005, 3 if low else 8,
          ANAL_RAYS // 2 if low else ANAL_RAYS * 2)
    # The tail: deeply forked, two long narrow lobes that meet along the middle line.
    for way in (1.0, -1.0):
        tip = (1.2, 0.195 * way)
        blade(m, TAIL, "tail", swept(((1.022, 0.0), (1.09, 0.125 * way), tip),
                                     ((1.066, 0.0), (1.12, 0.088 * way), tip)),
              upright, SIDE, 0.008, 30 // d, 10 // d)
    for sx in (1.0, -1.0):
        # The pectoral fins: sickle-shaped, low on the side behind the gill cover, held out and back.
        p0 = body_point(0.178, sx * 2.05)
        root = Vector((sx * (abs(p0.x) - 0.006), p0.y, p0.z))
        span = Vector((sx * 0.32, -0.18, 1.0)).normalized()
        chord = Vector((0.0, -1.0, 0.25)).normalized()
        facing = span.cross(chord).normalized()
        if facing.x * sx < 0.0:
            facing = -facing

        def pectoral_point(t, u):
            t *= 0.985
            lead = -0.012 * math.sin(math.pi * t) + 0.018 * t * t
            wide_here = 0.034 * (1.0 - t) ** 0.9 + 0.003
            return (0.135 * t, lead + wide_here * u)

        blade(m, PECTORAL, "pectorals", pectoral_point,
              lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.005, 20 // d, 8 // d)
        # The pelvic fins: under the pectorals, swept back and down.
        root = Vector((sx * 0.008, bottom(0.19) + 0.006, 0.19 - HALF))
        span = Vector((sx * 0.25, -0.5, 1.0)).normalized()
        chord = Vector((0.0, -1.0, 0.35)).normalized()
        facing = span.cross(chord).normalized()
        if facing.x * sx < 0.0:
            facing = -facing

        def pelvic_point(t, u):
            t *= 0.985
            return (0.085 * t, (0.024 * (1.0 - t) ** 0.8 + 0.003) * u)

        blade(m, PELVIC, "pelvics", pelvic_point,
              lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.004, 14 // d, 6 // d)


# The game model's settings: how far an edge may stray from its curve (metres), along the body and round it;
# inside a fin, how many times GAME_TOL; the longest step between a fin's rows (t); rings always kept (the
# jaw's hinge, its rear end, the gill cover); the lower jaw's points round it (a multiple of four) and its
# rings; the eye's spokes and rings (24 or more, so that it stays round). GAME_GAP: the longest step between
# rings along the body (shorter where it bends).
GAME_TOL = 0.0026
GAME_TOL_AROUND = 0.0016
GAME_FLANK = 5.0
GAME_FIN_GAP = 0.34
GAME_KEEP_RINGS = (HINGE[0], JAW_TO, 0.168)
GAME_JAW = (16, 10)
GAME_EYE = (28, 3)


def GAME_GAP(x):
    return 0.035 if x > 0.75 else 0.06


# ---- The game model (added 2026-11-18) ------------------------------------------------------------------------
# A third model at the weight of a Twilight Princess figure (the user, 2026-11-18: "We should have a twilight
# princess model to compare to so we can make low poly versions while maintaining high quality looks and
# silhouettes"). It is built from the same curves and profiles as the full model, not thinned from it: each
# outline (the body's rings, its cross-section, every fin's edges, the sail's scalloped top) keeps only the
# points it needs to stay within GAME_TOL of the curve it stands for, so the points crowd where the shape turns
# (the bill, the head, the tail wrist, the fins' tips, the scallops) and spread out across smooth flanks and
# inside the fins. While it is built GAME is true; the full and low models come out exactly as before.
GAME = False


def dp_keep(n, err, tol, keep=()):
    """Of points 0..n-1 (in order along a curve), the ones to keep so that `err(i, j, k)` (how far point k strays
    from the straight edge between kept points i and j) stays under `tol`: the first, the last, `keep`, and as
    few more as that takes (Douglas and Peucker)."""
    kept = sorted({0, n - 1, *keep})
    out = set(kept)
    stack = list(zip(kept, kept[1:]))
    while stack:
        i, j = stack.pop()
        if j - i < 2:
            continue
        worst, at = 0.0, -1
        for k in range(i + 1, j):
            e = err(i, j, k)
            if e > worst:
                worst, at = e, k
        if worst > tol:
            out.add(at)
            stack += [(i, at), (at, j)]
    return sorted(out)


def _seg_dist(p, a, b):
    ab = b - a
    length = ab.length_squared
    if length < 1e-18:
        return (p - a).length
    t = max(0.0, min(1.0, (p - a).dot(ab) / length))
    return (p - (a + ab * t)).length


def curves_err(curves):
    """`err` for dp_keep over several curves sampled at the same parameters: the worst of them."""
    return lambda i, j, k: max(_seg_dist(c[k], c[i], c[j]) for c in curves)


def fill_gaps(xs, longest):
    """`xs` with points put in wherever two are further apart than `longest(x)`."""
    out = [xs[0]]
    for b in xs[1:]:
        a = out[-1]
        n = math.ceil((b - a) / longest((a + b) * 0.5) - 1e-9)
        for i in range(1, n):
            out.append(a + (b - a) * i / n)
        out.append(b)
    return out


def game_rings():
    """Where the game model's rings stand along the body: of the full model's, those that keep the skin (at nine
    angles round it: the ridge of the back, the belly, the widest line and between) within GAME_TOL, and no two
    further apart than GAME_GAP allows (the body must still bend smoothly when it swims)."""
    xs = rings(False)
    angles = [math.pi * k / 8 for k in range(9)]
    curves = [[body_point(x, a) for x in xs] for a in angles]
    keep = [min(range(len(xs)), key=lambda i: abs(xs[i] - x)) for x in GAME_KEEP_RINGS]
    picked = [xs[i] for i in dp_keep(len(xs), curves_err(curves), GAME_TOL, keep)]
    out = fill_gaps(picked, GAME_GAP)
    print("GAME rings %d" % len(out))
    return out


def game_angles():
    """The game model's points round the body (radians from the ridge of the back by its left side, then back
    by its right): those of 96 a half turn that keep the cross-section within GAME_TOL at every station along
    the body, the quarter turns always kept, the two sides the same."""
    fine = [math.pi * k / 96 for k in range(97)]
    stations = [BODY_FROM + (BODY_TO - BODY_FROM) * (k + 0.5) / 40 for k in range(40)]
    curves = [[body_point(x, a) for a in fine] for x in stations]
    half = [fine[i] for i in dp_keep(len(fine), curves_err(curves), GAME_TOL_AROUND, (48,))]
    print("GAME round %d" % (2 * len(half) - 2))
    return half + [TAU - a for a in reversed(half[1:-1])]


def _zip_rows(m, a, ua, b, ub, out, name):
    """Triangles between two rows of a fin that need not have as many points (each row's `u` rising 0 to 1)."""
    i = j = 0
    while i < len(a) - 1 or j < len(b) - 1:
        if j == len(b) - 1 or (i < len(a) - 1 and ua[i + 1] <= ub[j + 1]):
            m.face((a[i], a[i + 1], b[j]), out, name)
            i += 1
        else:
            m.face((a[i], b[j + 1], b[j]), out, name)
            j += 1


def blade_game(m, part, name, point, place, facing, thick, high=None):
    """`blade` for the game model: the same fin, a thin closed blade, with its rows (t) where its leading and
    trailing edges need them and each row's points (u) where that row's curve needs them: the outer row (the
    fin's free edge: a sail's scallops) to GAME_TOL, the rows inside it to GAME_FLANK times that. The middle of
    each row is always kept, so the blade keeps a little thickness."""
    fine_t = [k / 96 for k in range(97)]
    edges = [[place(point(t, u)) for t in fine_t] for u in (0.0, 1.0)]
    ts = [fine_t[i] for i in dp_keep(len(fine_t), curves_err(edges), GAME_TOL)]
    ts = fill_gaps(ts, lambda t: GAME_FIN_GAP)
    fine_u = [k / 480 for k in range(481)]
    rows = []
    for t in ts:
        tol = GAME_TOL if t == ts[-1] else GAME_TOL * GAME_FLANK
        curve = [place(point(t, u)) for u in fine_u]
        rows.append([fine_u[i] for i in dp_keep(len(fine_u), curves_err([curve]), tol, (240,))])
    for side in (1.0, -1.0):
        grid = []
        for t, us in zip(ts, rows):
            row = []
            for u in us:
                foil = 2.6 * math.sqrt(u) * (1.0 - u)
                swell = thick * (1.0 - t) ** 0.7 * foil
                p = place(point(t, u)) + facing * (side * swell * 0.5)
                if high:
                    row.append(m.add(p, (t, u), part, high(t, u)))
                else:
                    row.append(m.add(p, (t, u), part))
            grid.append(row)
        for r in range(len(ts) - 1):
            _zip_rows(m, grid[r], rows[r], grid[r + 1], rows[r + 1], facing * side, name)


# The gills' settings (metres behind the snout's tip, metres): the throat from THROAT_FROM to THROAT_TO, at most
# THROAT_W wide (half) and THROAT_H high, its floor THROAT_MARGIN above the roof of the mouth (level behind THROAT_LEVEL); where the four arches
# stand along it, how far back their tops lean, the bars' radius, how long the filaments and the rakers are.
GILL = 8
THROAT_FROM, THROAT_TO, THROAT_W, THROAT_H, THROAT_MARGIN = 0.035, 0.155, 0.012, 0.03, 0.001
THROAT_LEVEL = 0.082
THROAT_REACH = 0.008
ARCHES = (0.09, 0.105, 0.12, 0.135)
ARCH_LEAN, ARCH_R, FILAMENT, RAKER = 0.01, 0.0013, 0.012, 0.004


def outline_top(xm):
    return top(xm)


def jaw_top_at(xm, x):
    """The top of the shut lower jaw at `xm`, `x` to one side (None where there is none)."""
    if JAW_FROM <= xm <= JAW_TO:
        chin, wide, lip = jaw_at(xm)
        if abs(x) < wide:
            return jaw_top(xm, x)
    return None


# ---- The gills (added 2026-11-18) ------------------------------------------------------------------------------
# The user: "The fish need modeled gills as well, well for relevant fish, so like when it opens its mouth wide you
# can see them". A short THROAT, a closed tunnel whose faces look inwards, runs back inside the head from above the
# rear of the roof of the mouth; its floor lies just above the roof (and above the shut lower jaw), so that when the
# shader opens a hole in the roof (only while the mouth is open: see THROAT_* in the shader) the tunnel is seen
# through it. Four GILL ARCHES a side line its walls: each a curved bar, a fringe of filaments behind it and a comb
# of rakers in front, every piece a closed mesh. All of it is part GILL and lies wholly inside the head, so with the
# mouth shut nothing of it is seen. What a point of it is, for the shader: UV.x the kind (0 the throat's wall, 1 an
# arch's bar, 2 its filaments, 3 its rakers) plus a tenth of the arch's number (0 to 3, front to back); UV.y how
# deep in the throat (0 its front, 1 its back); UV2.x how far along the arch (0 the floor, 1 the top).


def _under_y(xm, x):
    """How high the underside of the body's skin (the roof of the mouth, ahead of the hinge) is `x` to one side."""
    lo, hi = math.pi * 0.5, math.pi
    for _ in range(30):
        mid = (lo + hi) * 0.5
        if abs(body_point(xm, mid).x) > abs(x):
            lo = mid
        else:
            hi = mid
    return body_point(xm, (lo + hi) * 0.5).y


def _half_width_at(xm, y):
    """How wide (half) the body's skin is at height `y`."""
    lo, hi = 0.0, math.pi
    for _ in range(30):
        mid = (lo + hi) * 0.5
        if body_point(xm, mid).y > y:
            lo = mid
        else:
            hi = mid
    return abs(body_point(xm, (lo + hi) * 0.5).x)


def throat_floor(xm, x):
    """The throat's floor: just above the roof of the mouth and above whatever of the shut lower jaw is there. Behind
    THROAT_LEVEL it stays level, where the underside of the head drops away to the throat. It takes the highest of
    the roof a little ahead and behind as well (THROAT_REACH): the bars and their combs reach that far, and the low
    and game models' coarser skins lie a little inside the true one."""
    xm = min(xm, THROAT_LEVEL)
    y = max(_under_y(min(xm + d, THROAT_LEVEL), x) for d in (-THROAT_REACH, 0.0, THROAT_REACH))
    jaw = jaw_top_at(xm, x)
    if jaw is not None:
        y = max(y, jaw)
    return y + THROAT_MARGIN


def throat_size(xm):
    """The throat's half width and its height above the floor at `xm` (kept well inside the head)."""
    floor = throat_floor(xm, 0.0)
    high = min(THROAT_H, 0.45 * (outline_top(xm) - floor))
    wide = min(THROAT_W, 0.7 * _half_width_at(xm, floor + high * 0.5), 0.7 * _half_width_at(xm, floor + THROAT_MARGIN))
    return wide, high


def throat_wall(xm, a):
    """A point of the throat's wall at `xm`, `a` round it (0 the top, a half turn the middle of the floor)."""
    wide, high = throat_size(xm)
    s = math.sin(a)
    c = math.cos(a)
    x = wide * math.copysign(abs(s) ** 0.55, s)
    floor = throat_floor(xm, x)
    y = floor + (high * c ** 0.7 if c > 0.0 else 0.0)
    return Vector((x, y, xm - HALF))


def _closed_sheet(m, name, root, edge, rows, thick, kind_uv, along):
    """A thin closed sheet between two lines of points (`root`, `edge`), `rows` rows across, thickest between
    them and nothing at either line, its two skins facing either way."""
    n = len(root)
    across = [edge[i] - root[i] for i in range(n)]
    for side in (1.0, -1.0):
        grid = []
        for j in range(rows + 1):
            f = j / rows
            row = []
            for i in range(n):
                tang = (root[min(i + 1, n - 1)] - root[max(i - 1, 0)])
                face = tang.cross(across[i])
                if face.length < 1e-12:
                    face = Vector((0.0, 0.0, 1.0))
                face.normalize()
                p = root[i] + across[i] * f + face * (side * thick * 4.0 * f * (1.0 - f) * 0.5)
                row.append((m.add(p, (kind_uv, along[i][1]), GILL, along[i][0]), face * side))
            grid.append(row)
        for j in range(rows):
            for i in range(n - 1):
                quad = (grid[j][i][0], grid[j][i + 1][0], grid[j + 1][i + 1][0], grid[j + 1][i][0])
                m.face(quad, grid[j][i][1] + grid[j][i + 1][1], name)


def gills(m, low):
    """The throat and four gill arches a side (see above). Fewer points on the game model, fewest on the low one."""
    detail = "game" if GAME else ("low" if low else "full")
    rings_n, around, seg, sides, teeth, rows = {
        "full": (10, 16, 10, 8, 12, 2), "game": (5, 10, 3, 3, 3, 1), "low": (3, 6, 2, 3, 2, 1)}[detail]
    length = THROAT_TO - THROAT_FROM
    # the throat: a tunnel facing inwards, closed at both ends
    grid = []
    xs = [THROAT_FROM + length * k / rings_n for k in range(rings_n + 1)]
    for xm in xs:
        depth = (xm - THROAT_FROM) / length
        grid.append([m.add(throat_wall(xm, TAU * c / around), (0.0, depth), GILL, 0.0) for c in range(around)])
    for r in range(rings_n):
        xm = (xs[r] + xs[r + 1]) * 0.5
        wide, high = throat_size(xm)
        middle = Vector((0.0, throat_floor(xm, 0.0) + high * 0.4, xm - HALF))
        for c in range(around):
            n = (c + 1) % around
            quad = (grid[r][c], grid[r][n], grid[r + 1][n], grid[r + 1][c])
            centre = sum((m.verts[q] for q in quad), Vector()) * 0.25
            inward = middle - centre
            inward.z = 0.0
            m.face(quad, inward, "throat")
    for row, xm, way in ((grid[0], THROAT_FROM, 1.0), (grid[-1], THROAT_TO, -1.0)):
        wide, high = throat_size(xm)
        tip = m.add(Vector((0.0, throat_floor(xm, 0.0) + high * 0.4, xm - HALF)), (0.0, 0.0 if way > 0 else 1.0), GILL, 0.0)
        # (the end has points of its own, so that smoothing does not bend the walls' normals into it)
        own = [m.add(m.verts[q].copy(), (0.0, 0.0 if way > 0 else 1.0), GILL, 0.0) for q in row]
        for c in range(around):
            m.face((tip, own[c], own[(c + 1) % around]), Vector((0.0, 0.0, way)), "throat")
    # the arches, four a side, each lining the wall from the floor to near the top, leaning back
    for k, xk in enumerate(ARCHES):
        for sx in (1.0, -1.0):
            path = []
            for i in range(seg + 1):
                t = i / seg
                # (round an ellipse inside the throat, from low beside the middle of the floor up the side to near
                # the top: no sharp turns, so the bar never folds on itself)
                phi = (0.3 + 0.55 * t) * math.pi
                xm = xk + ARCH_LEAN * t
                wide, high = throat_size(xm)
                centre = Vector((0.0, throat_floor(xm, 0.0) + high * 0.4, xm - HALF))
                p = centre + Vector((sx * (wide - ARCH_R * 2.5) * math.sin(phi), -(high * 0.4 - ARCH_R * 2.5) * math.cos(phi), 0.0))
                inward = centre - p
                inward.z = 0.0
                inward.normalize()
                path.append((p, inward, t))
            depth = (xk - THROAT_FROM) / length
            code = 0.1 * k
            # the bar: a round tube along the path, closed at both ends
            back = Vector((0.0, 0.0, 1.0))
            ring_ids = []
            for i, (p, inward, t) in enumerate(path):
                ring = []
                # (a frame square to the bar that does not twist along it: 'back' kept as square to it as it can be)
                tangent = (path[min(i + 1, seg)][0] - path[max(i - 1, 0)][0]).normalized()
                up = (back - tangent * back.dot(tangent)).normalized()
                across = tangent.cross(up).normalized()
                for s in range(sides):
                    ang = TAU * s / sides
                    q = p + (across * math.cos(ang) + up * math.sin(ang)) * ARCH_R
                    ring.append(m.add(q, (1.0 + code, depth), GILL, t))
                ring_ids.append((ring, p))
            for i in range(seg):
                for s in range(sides):
                    n = (s + 1) % sides
                    a0, a1 = ring_ids[i][0], ring_ids[i + 1][0]
                    quad = (a0[s], a0[n], a1[n], a1[s])
                    centre = sum((m.verts[q] for q in quad), Vector()) * 0.25
                    axis = (ring_ids[i][1] + ring_ids[i + 1][1]) * 0.5
                    m.face(quad, centre - axis, "gill arches")
            for (ring, p), other in ((ring_ids[0], ring_ids[1][1]), (ring_ids[-1], ring_ids[-2][1])):
                tip = m.add(p, (1.0 + code, depth), GILL, 0.0)
                # (the end has points of its own, so that smoothing does not bend the sides' normals into it)
                own = [m.add(m.verts[q].copy(), (1.0 + code, depth), GILL, m.data[q][1][0]) for q in ring]
                for s in range(sides):
                    m.face((tip, own[s], own[(s + 1) % sides]), p - other, "gill arch ends")
            # the filaments behind the bar and the rakers in front: a toothed sheet each
            # (one way for the whole sheet: back, square to the bar on the whole, never down into the floor, so that
            # the sheet never folds along a leaning bar)
            square = Vector((0.0, 0.0, 0.0))
            for i in range(seg):
                tangent = (path[i + 1][0] - path[i][0]).normalized()
                square += back - tangent * back.dot(tangent)
            square.y = max(square.y, 0.0)
            square.normalize()
            for kind, way, reach, name in ((2.0, 1.0, FILAMENT, "gill filaments"), (3.0, -1.0, RAKER, "gill rakers")):
                count = teeth if kind == 2.0 else max(1, teeth // 2)
                n_pts = 2 * count + 1
                root, edge, along = [], [], []
                for i in range(n_pts):
                    t = i / (n_pts - 1)
                    # (a point of the path at t, by straight steps between its points)
                    f = t * seg
                    i0 = min(int(f), seg - 1)
                    u = f - i0
                    p = path[i0][0].lerp(path[i0 + 1][0], u)
                    inward = path[i0][1].lerp(path[i0 + 1][1], u).normalized()
                    long = reach * (1.0 if i % 2 == 1 else 0.45)
                    r0 = p + square * (way * ARCH_R * 0.7)
                    root.append(r0)
                    edge.append(r0 + square * (way * long) + inward * (long * (0.15 if kind == 2.0 else 0.3)))
                    along.append((t, depth))
                _closed_sheet(m, name, root, edge, rows, ARCH_R * 0.5, kind + code, along)


def gills_inside_mesh(m, first):
    """How many of the gills' points lie outside this model's own body (its faceted skin, part BODY, not the
    curves it was built from): a ray from each must cross that skin an odd number of times."""
    from mathutils.bvhtree import BVHTree
    body_faces = [f for f, d in zip(m.faces, m.out) if round(1.0 - m.data[f[0]][1][1]) == BODY]
    tris = []
    for f in body_faces:
        for k in range(1, len(f) - 1):
            tris.append((f[0], f[k], f[k + 1]))
    tree = BVHTree.FromPolygons(m.verts, tris)
    way = Vector((0.0123, 0.0071, 0.9999)).normalized()
    outside = 0
    for i in range(first, len(m.verts)):
        start = Vector(m.verts[i])
        crossings = 0
        while True:
            hit = tree.ray_cast(start, way)
            if hit[0] is None:
                break
            crossings += 1
            start = hit[0] + way * 1e-6
        if crossings % 2 == 0:
            outside += 1
    return outside


def gills_inside(m, first):
    """How far (metres) the point of the gills that is furthest outside the head's skin is outside it (0: none)."""
    worst = 0.0
    for i in range(first, len(m.verts)):
        p = m.verts[i]
        xm = p.z + HALF
        up = outline_top(xm)
        down = _under_y(xm, p.x)
        out = max(p.y - up, down - p.y, 0.0)
        if down < p.y < up:
            out = max(out, abs(p.x) - _half_width_at(xm, p.y))
        worst = max(worst, out)
    return worst


def make(name, low, game=False):
    global GAME
    GAME = game
    m = Mesh()
    body(m, low)
    jaw(m, low)
    for sx in (1.0, -1.0):
        eye(m, sx, low)
    fins(m, low)
    first = len(m.verts)
    gills(m, low)
    print("GILLS %s: %d points, the furthest outside the head's skin by %.4f m" % (name, len(m.verts) - first, gills_inside(m, first)))
    print("GILLS %s: %d of them outside the model's own faceted skin" % (name, gills_inside_mesh(m, first)))
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
    bsdf.inputs["Base Color"].default_value = (0.75, 0.65, 0.2, 1.0)
    material.diffuse_color = (0.75, 0.65, 0.2, 1.0)
    mesh.materials.append(material)
    if not GAME:
        # (on the full and the low model the throat and gills are a second surface, so that the body's surface
        # stays as it was: one changed, Godot's importer thins it into different LODs and it looks different far off)
        throat = bpy.data.materials.get(mesh.name + "_gills") or bpy.data.materials.new(mesh.name + "_gills")
        throat.diffuse_color = (0.5, 0.05, 0.06, 1.0)
        mesh.materials.append(throat)
        names = ("throat", "gill arches", "gill arch ends", "gill filaments", "gill rakers")
        for poly in mesh.polygons:
            if m.out[poly.index][1] in names:
                poly.material_index = 1
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
    GAME = False
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
    # (Blender space: the fish lies along Y, its nose at +Y, up is Z)
    views = [("left", (1, 0, 0), (0, 0, 0.0), 1.3), ("right", (-1, 0, 0), (0, 0, 0.0), 1.3),
             ("front", (0, 1, 0), (0, 0, 0.0), 0.5), ("back", (0, -1, 0), (0, 0, 0.0), 0.5),
             ("top", (0.001, 0, 1), (0, 0, 0), 1.3), ("under", (0.001, 0, -1), (0, 0, 0), 1.3),
             ("head", (0.8, 0.5, 0.2), (0, 0.45, 0), 0.4), ("head_under", (0.5, 0.5, -0.7), (0, 0.48, 0), 0.3),
             ("tail", (0.7, -0.6, 0.3), (0, -0.45, 0), 0.5)]
    for low, obj in ((False, made[0]), (True, made[1])):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if low and view not in ("left", "head"):
                continue
            offset = Vector(direction).normalized() * 20.0
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
    game = make(NAME + "_game", False, True)
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, NAME + ".glb"))
    export_one(low, os.path.join(OUT, NAME + "_lo.glb"))
    export_one(game, os.path.join(OUT, NAME + "_game.glb"))
    low.location.x = 0.6
    game.location.x = -0.6
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, NAME + ".blend"))
    low.location.x = 0.0
    game.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low])


if __name__ == "__main__":
    main()
