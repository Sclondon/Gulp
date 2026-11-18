"""Builds the sperm whale (creatures/sperm_whale) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/sperm_whale/tools/build_sperm_whale.py
    blender --background --python creatures/sperm_whale/tools/build_sperm_whale.py -- <preview folder>

Writes creatures/sperm_whale/models/sperm_whale.glb (the full model), sperm_whale_lo.glb (far off, phones) and
sperm_whale_game.glb (the game model: Twilight Princess weight, its triangles spent on the outline, the eye, the
jaw and the fin edges; added 2026-11-18), and
the editable creatures/sperm_whale/tools/sperm_whale.blend (this folder has a .gdignore). Each model is one still
mesh with one surface: the shader (sperm_whale.gdshader) draws every marking and the wrinkles, swims it and opens
its mouth. It prints a WINDING line: the check that nothing is inside out.

A sperm whale (Physeter macrocephalus), a grown bull 15 m from the front of its head to the tips of its flukes,
built from the species (no picture was traced):

- THE HEAD: the enormous box of the spermaceti organ, a third of its length, its section a rounded square, its
  front a blunt upright face; the single blowhole at the front of the top, on its LEFT (-X) side; a small eye low on
  each side, just behind and above the corner of the mouth.
- THE MOUTH: the LOWER JAW is a long narrow rod of its own under the head, starting well behind the front of the
  head; its top sits up inside the head's underside when shut, and the shader swings it down about the corner of
  the mouth. Twenty-two big conical teeth each side stand on it (the upper jaw has none that show: the head's
  underside over the jaw is the white palate, with the sockets the lower teeth fit into, drawn by the shader).
- THE BODY behind the head: round, deepest just behind the head; a low triangular hump two thirds of the way back
  and a row of knuckles after it down the ridge of the tail stock; a keel under the tail stock; small paddle
  flippers just behind the head, low down; broad triangular flukes with a notch in the middle. (The wrinkles of its
  skin are the shader's.)

Everything here is in Godot space (metres, Y up, its nose at -Z) until it is written out; the origin is on its
middle line, half way along (7.5 m behind the front of its head). `xm` below is metres behind that front.

What a point is, for the shader: UV2.y the part (0 body, 1 lower jaw, 3 a tooth, 4 the flukes, 6 a flipper, 7 an
eye; 2 and 5 are not used, kept as the dolphin's and the orca's numbers). UV2.x, on the jaw: how much the point is
on its top (the floor of the mouth, 1) rather than its outside (0). UV, on the body and jaw: x how far along (0 the
front of the head to 1 the fluke tips), y how high on its side (1 the ridge of the back, 0 the keel of the belly);
on a fin: x from its root (0) to its tip (1), y from its leading edge (0) to its trailing edge (1); on an eye: x
from its middle (0) to its rim (1); on a tooth, x from its root (0) to its tip (1). (The glTF writer flips V: what
is written here is 1 - v, so that Godot reads v.)

The numbers marked "as the shader has it" are in sperm_whale.gdshader too: change one, change the other.
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

NAME = "sperm_whale"
LENGTH = 15.0
HALF = 7.5
BODY, JAW, TOOTH, FLUKES, FLIPPER, EYE = 0, 1, 3, 4, 6, 7
TAU = math.tau
PI = math.pi

# The body's outline: metres behind the front of the head, the height of the ridge of its back, the height of
# the keel of its belly, half its width.
PROFILE = [
    (0.0, 0.62, -0.78, 0.38),
    (0.04, 0.98, -1.02, 0.66),
    (0.14, 1.17, -1.15, 0.84),
    (0.35, 1.28, -1.22, 0.95),
    (0.8, 1.34, -1.27, 1.02),
    (2.0, 1.38, -1.31, 1.08),
    (3.4, 1.41, -1.34, 1.13),
    (4.5, 1.40, -1.38, 1.18),
    (5.2, 1.30, -1.46, 1.27),
    (6.4, 1.26, -1.54, 1.30),
    (7.8, 1.22, -1.50, 1.23),
    (9.3, 1.12, -1.30, 1.02),
    (10.8, 0.86, -0.97, 0.70),
    (12.1, 0.58, -0.64, 0.40),
    (13.1, 0.40, -0.42, 0.23),
    (13.9, 0.25, -0.26, 0.16),
    (14.4, 0.11, -0.11, 0.10),
    (14.62, 0.012, -0.012, 0.012),
]
BODY_TO = 14.62
# As the shader has it: where the head's box ends (the wrinkles begin behind it), the corner of the mouth (where
# the jaw hinges) and the hinge's height, the eye, the blowhole.
HEAD_END = 5.0
JAW_FROM = 0.75
CORNER = 4.1
EYE_AT = (4.55, -0.74)
EYE_RADIUS = 0.055
BLOWHOLE = (0.42, -0.34)
# How far the jaw's top is tucked up inside the head; how far behind the corner it runs on into the throat.
TUCK = 0.07
JAW_TAIL = 0.7
# The teeth: how many each side, from where to where along the jaw, how thick, how long, how far in from its side.
TEETH = 22
TEETH_FROM = 0.95
TEETH_TO = 3.55
TOOTH_RADIUS = 0.04
TOOTH_LONG = 0.15
TOOTH_IN = 0.055
# Where the flukes hinge (as the shader has it).
JOINT = 13.5


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
    out[2] = max(out[2], 0.002)
    return out


def top(xm):
    return outline(xm)[0]


def bottom(xm):
    return outline(xm)[1]


def squareness(xm):
    """The power of the section's rounded square: under 1 the head's box, 1 the round body."""
    return 0.42 + 0.58 * smooth(3.8, 6.2, xm)


def keel(xm):
    """How much the tail stock comes to an edge above and below."""
    return 1.0 + 0.8 * smooth(11.0, 13.6, xm)


def spow(v, p):
    return math.copysign(abs(v) ** p, v)


def section(xm, angle):
    """(x, y) of the skin: `angle` round the body from the ridge of the back (0) by one side (a quarter turn) to
    the keel of the belly (half a turn)."""
    up, down, wide = outline(xm)
    yc = 0.5 * (up + down)
    e = squareness(xm)
    c = math.cos(angle)
    s = math.sin(angle)
    y = yc + spow(c, e) * (up - yc if c >= 0.0 else yc - down)
    x = spow(s, e * keel(xm)) * wide
    return x, y


def angle_at(xm, level):
    """The angle round the body at which its skin is at the height `level`."""
    up, down, _ = outline(xm)
    if level >= up:
        return 0.0
    if level <= down:
        return PI
    yc = 0.5 * (up + down)
    r = (level - yc) / (up - yc if level >= yc else yc - down)
    return math.acos(max(-1.0, min(1.0, spow(r, 1.0 / squareness(xm)))))


def ridge(xm):
    """How far the ridge of the back is raised: the low hump, then the knuckles down the tail stock."""
    hump = 0.3 * math.exp(-((xm - 9.75) / (0.75 if xm < 9.75 else 0.42)) ** 2)
    knuckles = 0.0
    for i in range(6):
        knuckles += 0.085 * (1.0 - i / 7.0) * math.exp(-((xm - (10.75 + 0.45 * i)) / 0.13) ** 2)
    return hump + knuckles


def sculpt(xm, x, y):
    """The shapes pressed into or raised from the skin."""
    up, down, wide = outline(xm)
    yc = 0.5 * (up + down)
    if y > yc:
        # the hump and knuckles, on the ridge only
        y += ridge(xm) * math.exp(-(x / max(0.12, 0.3 * wide)) ** 2) * smooth(yc, up, y)
        # the blowhole: a slit pressed into the top, at the front, on its left
        bx, bz = BLOWHOLE[1], BLOWHOLE[0]
        y -= 0.035 * math.exp(-(((xm - bz) / 0.16) ** 2 + ((x - bx) / 0.06) ** 2))
    return Vector((x, y, xm - HALF))


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


# The game model (Twilight Princess weight): how far its rings may stray from the outline (metres: the ridge with
# its hump and knuckles, the keel, the sides, and the corners of the head's box), the longest step between two
# rings, and how many points round each ring.
GAME_TOL = 0.011
GAME_LONGEST = 0.5
GAME_AROUND = 32


def rings(low, game=False):
    if game:
        def values(xm):
            up, down, wide = outline(xm)
            corner = 0.7071 ** squareness(xm)
            return up + ridge(xm), down, wide, wide * corner, up * corner
        return pick(rings(False), values, GAME_TOL, GAME_LONGEST)
    xs = []
    x = 0.0
    for until, step in ((0.4, 0.025), (4.0, 0.1), (9.0, 0.1), (13.2, 0.045), (BODY_TO, 0.06)):
        if low:
            step *= 3.4
        n = max(1, round((until - x) / step))
        for i in range(n):
            xs.append(x + (until - x) * i / n)
        x = until
    xs.append(BODY_TO)
    return xs


def loft(m, rows, name, around_middle=True):
    """Joins rings of points into a skin, each face away from its row's middle line."""
    around = len(rows[0][0])
    for r in range(len(rows) - 1):
        a, middle = rows[r]
        b = rows[r + 1][0]
        for c in range(around):
            n = (c + 1) % around
            quad = (a[c], a[n], b[n], b[c])
            at = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((at.x, at.y - middle, 0.0)), name)


def cap(m, part, row, tip, way, name, uv_x):
    """Closes the end of a skin with a fan to `tip`."""
    point = m.add(tip, (uv_x, 0.5), part)
    for c in range(len(row)):
        m.face((point, row[c], row[(c + 1) % len(row)]), Vector((0.0, 0.0, way)), name)


def body(m, low, game=False):
    """The body's skin: a closed ring of points round it at each place along it."""
    around = 22 if low else 88
    if game:
        # (the head's rounded square gathers these at its corners by itself)
        around = GAME_AROUND
    rows = []
    for xm in rings(low, game):
        up, down, _ = outline(xm)
        row = []
        for j in range(around):
            a = j / around * TAU
            # (angle from the ridge, by its right (+X) side to the keel and up its left)
            x, y = section(xm, a if a <= PI else TAU - a)
            if a > PI:
                x = -x
            p = sculpt(xm, x, y)
            row.append(m.add(p, (xm / LENGTH, high_of(xm, p.y)), BODY))
        rows.append((row, 0.5 * (up + down)))
    loft(m, rows, "body")
    # (the front of the head: a nearly flat face, a little domed)
    first = rows[0]
    cap(m, BODY, first[0], Vector((0.0, first[1] + 0.05, -0.04 - HALF)), -1.0, "body", 0.0)
    cap(m, BODY, rows[-1][0], Vector((0.0, 0.0, BODY_TO + 0.01 - HALF)), 1.0, "body", BODY_TO / LENGTH)


def jaw_shape(xm):
    """The jaw at `xm`: (the height of its top, the height of its bottom, half its width)."""
    s = smooth(JAW_FROM, CORNER, xm)
    wide = 0.1 + 0.11 * s + 0.08 * smooth(CORNER, CORNER + JAW_TAIL, xm)
    under = bottom(xm)
    deep = 0.15 + 0.15 * s
    # (behind the corner it rises into the throat)
    deep *= 1.0 - smooth(CORNER, CORNER + JAW_TAIL, xm)
    jtop = under + TUCK + 0.08 * smooth(CORNER, CORNER + JAW_TAIL, xm)
    jbottom = under - deep + 0.04 * smooth(CORNER + 0.2, CORNER + JAW_TAIL, xm)
    # (its tip rounded off)
    tip = smooth(JAW_FROM - 0.02, JAW_FROM + 0.35, xm)
    wide *= 0.45 + 0.55 * tip ** 0.5
    jbottom = jtop - (jtop - jbottom) * (0.4 + 0.6 * tip ** 0.5)
    return jtop, jbottom, wide


def jaw(m, low, game=False):
    """The lower jaw: a closed rod, flat on top (the floor of the mouth), rounded below."""
    around = 12 if low else 28
    count = 14 if low else 70
    if game:
        around, count = 16, 22
    to = CORNER + JAW_TAIL
    rows = []
    for i in range(count + 1):
        # (the game model's rings gathered to the jaw's rounded tip)
        xm = JAW_FROM + (to - JAW_FROM) * ((i / count) ** 1.35 if game else i / count)
        jtop, jbottom, wide = jaw_shape(xm)
        mid = 0.5 * (jtop + jbottom)
        half = 0.5 * (jtop - jbottom)
        row = []
        for j in range(around):
            a = j / around * TAU
            c = math.cos(a)
            s = math.sin(a)
            # (a rounded square: flat on top and at the sides)
            x = spow(s, 0.6) * wide
            y = mid + spow(c, 0.5 if c > 0.0 else 0.85) * half
            on_top = smooth(0.55, 0.85, c)
            row.append(m.add(Vector((x, y, xm - HALF)), (xm / LENGTH, high_of(xm, y)), JAW, on_top))
        rows.append((row, mid))
    loft(m, rows, "jaw")
    jtop, jbottom, _ = jaw_shape(JAW_FROM)
    cap(m, JAW, rows[0][0], Vector((0.0, 0.5 * (jtop + jbottom), JAW_FROM - 0.03 - HALF)), -1.0, "jaw", JAW_FROM / LENGTH)
    jtop, jbottom, _ = jaw_shape(to)
    cap(m, JAW, rows[-1][0], Vector((0.0, 0.5 * (jtop + jbottom), to + 0.02 - HALF)), 1.0, "jaw", to / LENGTH)


def tooth(m, base, axis, radius, long, low, name):
    """A cone standing on `base` along `axis`, a little curved back at its tip."""
    sides = 5 if low else 8
    side = axis.cross(Vector((0.0, 0.0, 1.0))).normalized()
    other = axis.cross(side).normalized()
    levels = [(0.0, 1.0)] if low else [(0.0, 1.0), (0.35, 0.92), (0.7, 0.58)]
    last = None
    for share, thick in levels:
        row = []
        for s in range(sides):
            a = s / sides * TAU
            p = base + axis * (long * share) + (side * math.cos(a) + other * math.sin(a)) * (radius * thick)
            row.append(m.add(p, (share, 0.0), TOOTH))
        if last is not None:
            for s in range(sides):
                n = (s + 1) % sides
                at = (m.verts[row[s]] + m.verts[row[n]]) * 0.5 - (base + axis * (long * share))
                m.face((last[s], last[n], row[n], row[s]), at, name)
        last = row
    tip = m.add(base + axis * long, (1.0, 0.0), TOOTH)
    for s in range(sides):
        n = (s + 1) % sides
        at = (m.verts[last[s]] + m.verts[last[n]]) * 0.5 - (base + axis * (long * 0.5))
        m.face((last[s], last[n], tip), at, name)


def teeth(m, low, game=False):
    count = TEETH // 2 if low else TEETH
    if game:
        # (fewer and simple cones, as the low model's)
        count, low = 14, True
    pitch = (TEETH_TO - TEETH_FROM) / (count - 1)
    for i in range(count):
        xm = TEETH_FROM + pitch * i
        jtop, _, wide = jaw_shape(xm)
        grow = 0.75 + 0.25 * smooth(TEETH_FROM, TEETH_FROM + 1.0, xm)
        for sx in (1.0, -1.0):
            base = Vector((sx * (wide - TOOTH_IN), jtop - 0.02, xm - HALF))
            tooth(m, base, Vector((sx * 0.15, 1.0, 0.1)).normalized(), TOOTH_RADIUS * grow, TOOTH_LONG * grow, low, "teeth")


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
    bulge = EYE_RADIUS * 0.35
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


UP = Vector((0.0, 1.0, 0.0))


def fins(m, low, game=False):
    d = 3 if low else 1
    # (the game model: rows along each fin gathered to its tip, few across: a blade is seen by its edges)
    g = 1.35 if game else 1.0

    def n(full, game_n):
        return game_n if game else full // d

    for sx in (1.0, -1.0):
        # The flukes: broad triangles, the leading edge swept back, the trailing edge nearly straight, meeting
        # in a notch.
        tip = (15.0, 2.05)
        blade(m, FLUKES, "flukes", swept(((13.45, 0.0), (14.1, 1.15), tip), ((14.6, 0.0), (14.72, 1.05), tip)),
              lambda p, sx=sx: Vector((sx * p[1], 0.0, p[0] - HALF)), UP, 0.16, n(28, 12), n(11, 4), g)
        # The flippers: small rounded paddles, low behind the head, held out, down and back.
        up, down, wide = outline(5.4)
        root = Vector((sx * (wide - 0.2), -0.98, 5.35 - HALF))
        span = Vector((sx * 0.7, -0.55, 0.45)).normalized()
        chord = Vector((sx * 0.08, -0.06, 1.0)).normalized()
        facing = span.cross(chord).normalized()
        if facing.y < 0.0:
            facing = -facing

        def flipper_point(t, u):
            t *= 0.99
            lead = 0.18 * t * t - 0.06 * math.sin(PI * t)
            wide_here = 0.6 * (0.75 + 0.3 * math.sin(PI * t ** 0.8)) * math.sqrt(max(0.0, 1.0 - t ** 3)) + 0.01
            return (1.35 * t, lead + wide_here * u)

        blade(m, FLIPPER, "flippers", flipper_point,
              lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.12, n(22, 9), n(9, 4), g)


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
    bsdf.inputs["Base Color"].default_value = (0.12, 0.1, 0.09, 1.0)
    material.diffuse_color = (0.4, 0.37, 0.35, 1.0)
    mesh.materials.append(material)
    mesh.update()
    winding(name, mesh, m)
    # Points in the same place become one (a blade's two skins along its edges), so that the skin is shaded
    # smoothly across them; a sharp fold (a blade's edge, the jaw's flat top) is then marked sharp.
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
    """Nothing inside out: the skin of the body and the jaw faces away from its middle line, each skin of a fin
    away from the fin's own flat, a tooth away from its own middle, an eye out from the head (Blender's front is
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
    # (Blender space: it lies along Y, its nose at +Y, up is Z)
    f = LENGTH
    views = [("left", (1, 0, 0), (0, 0, 0), 1.12 * f), ("right", (-1, 0, 0), (0, 0, 0), 1.12 * f),
             ("front", (0, 1, 0), (0, 0, 0), 0.5 * f), ("back", (0, -1, 0), (0, 0, 0), 0.5 * f),
             ("top", (0.001, 0, 1), (0, 0, 0), 1.12 * f), ("under", (0.001, 0, -1), (0, 0, 0), 1.12 * f),
             ("head", (0.8, 0.5, 0.2), (0, 0.33 * f, 0), 0.4 * f), ("chin", (0.6, 0.5, -0.6), (0, 0.33 * f, 0), 0.4 * f),
             ("tail", (0.7, -0.6, 0.5), (0, -0.33 * f, 0), 0.45 * f)]
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
    print("HINGE_Y %.4f (the shader's)" % (bottom(CORNER) + 0.5 * TUCK))
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
    low.location.x = 4.0
    game.location.x = -4.0
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, NAME + ".blend"))
    low.location.x = 0.0
    game.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low, game])


if __name__ == "__main__":
    main()
