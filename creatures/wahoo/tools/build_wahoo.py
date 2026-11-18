"""Builds the wahoo (creatures/wahoo) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/wahoo/tools/build_wahoo.py
    blender --background --python creatures/wahoo/tools/build_wahoo.py -- <preview folder>   # with pictures

Writes creatures/wahoo/models/wahoo.glb (the full model) and wahoo_lo.glb (far off, phones), and the editable
tools/wahoo.blend (this folder has a .gdignore). Each is one still mesh with one surface: the shader
(wahoo.gdshader) draws every marking, swims it and works its jaw. It prints a WINDING line for each: the check
that nothing is inside out.

It also writes models/wahoo_game.glb, the game model (a third, at about Twilight Princess weight: the GAME table
below says how its triangles are spent), kept in the .blend beside the others.

A wahoo (Acanthocybium solandri), 1.8 m from the tip of its lower jaw to the tips of its tail, built from the
species (no picture was traced or copied):

- THE BODY: very long and slim, a little flattened from side to side, deepest (0.205 m) and widest (0.133 m)
  well back, running to a slim tail wrist. A long head whose jaws are a long pointed beak, the lower a little
  ahead of the upper.
- THE HEAD IS TWO PIECES ahead of the jaw's hinge (under the eye): the upper head, closed underneath by the roof
  of the mouth, and the LOWER JAW, closed on top by the floor of the mouth. They meet along the line of the mouth
  and at the hinge; the shader swings the jaw down about the hinge (`gape`). A row of small close-set TEETH (a
  cone each) stands in from each lip: hidden inside the other jaw while the mouth is shut.
- THE FINS, each a thin closed blade: a long low first dorsal fin, a small second one close behind it, an anal
  fin under that, nine finlets behind each of those two, a small stiff crescent tail, small pectoral and pelvic
  fins.

Everything here is in body lengths (s: 0 the tip of the jaw, 1 the tips of the tail; heights and widths in body
lengths too) and in Godot space (Y up, X to its left side, its nose at -Z) until it is written out, in metres;
the origin is on its middle line, half way along.

What a point is, for the shader: UV2.y the part (0 body, 1 the first dorsal fin, 2 the second, 3 the anal fin, 4
the tail, 5 a pectoral fin, 6 a pelvic fin, 7 an eye, 8 the inside of the mouth, 9 a tooth, 10 a finlet); UV2.x
how much of the jaw's swing it takes (above 0, a point of the lower jaw; below 0, a point of the upper head,
which lifts a little). UV, on the body: x how far along (0 to 1), y how high on its side (1 the ridge of the
back, 0.5 its middle line, 0 the keel of the belly); in the mouth: x how far inside (0 at the lips); on a tooth:
x from its root (0) to its point (1); on a fin: x from its root (0) to its tip (1), y from its leading edge (0)
to its trailing edge (1); on an eye: x from its middle (0) to its rim (1). (The glTF writer flips V: what is
written here is 1 - v, so that Godot reads v.)

The numbers marked "as the shader has it" are in wahoo.gdshader too: change one, change the other (the script
prints HINGE_Y for it).
"""

NAME = "wahoo"
LENGTH = 1.8
COLOUR = (0.4, 0.55, 0.75, 1.0)

# The body's outline: how far along, half its depth above its middle line, half its depth below, half its width.
PROFILE = [
    (0.0, 0.0, 0.0, 0.0),
    (0.004, 0.003, 0.003, 0.003),
    (0.02, 0.007, 0.007, 0.007),
    (0.045, 0.013, 0.013, 0.011),
    (0.075, 0.020, 0.020, 0.016),
    (0.11, 0.029, 0.029, 0.022),
    (0.15, 0.038, 0.039, 0.028),
    (0.20, 0.046, 0.048, 0.032),
    (0.27, 0.052, 0.055, 0.035),
    (0.36, 0.055, 0.059, 0.037),
    (0.46, 0.054, 0.058, 0.036),
    (0.56, 0.048, 0.052, 0.033),
    (0.65, 0.040, 0.042, 0.028),
    (0.73, 0.032, 0.034, 0.024),
    (0.80, 0.022, 0.023, 0.017),
    (0.85, 0.015, 0.015, 0.012),
    (0.885, 0.011, 0.011, 0.009),
    (0.905, 0.010, 0.010, 0.006),
    (0.915, 0.008, 0.008, 0.003),
    (0.92, 0.002, 0.002, 0.001),
]
BODY_FROM = 0.0015
BODY_TO = 0.92
# As the shader has it: where the lower jaw hinges (the corner of the mouth), how far round from the ridge of the
# back the line of the mouth is at the jaw's tip and at the hinge (degrees), where the tail fin is hinged.
HINGE_S = 0.118
SEAM_A0 = 92.0
SEAM_A1 = 110.0
JOINT_S = 0.91
# How long before the hinge the jaw's swing fades in (the skin of the throat stretches over it).
BLEND = 0.03
# Where the upper head and the lower jaw begin (0: at the very tip), and over how long a late one swells.
UP_FROM = 0.004
LOW_FROM = 0.0
TAPER = 0.014
# How square the top of the head is (1 round), and where along the body that ends.
FLAT = 1.0
FLAT_TO = 0.3
# How much sharper the belly is than the back.
KEEL = 0.05
# As the shader has it: the edge of the gill cover.
GILL_S = 0.228
GILL_K = 10.0
GILL_Y0 = -0.004
GILL_STEP = 0.003
# As the shader has it: the eye.
EYE_AT = (0.13, 0.014)
EYE_R = 0.012
EYE_DOME = 0.003
# How high the roof of the mouth is arched (and its floor dished), in lip half-widths; how deep the lips' groove.
ARCH = 0.45
INSET = 0.06
# The grid: points over the back and under the belly on each ring, and how far apart the rings are up to each place.
NU, NL = 58, 38
NU_LOW, NL_LOW = 12, 8
RING_STEPS = ((HINGE_S, 0.003), (0.25, 0.004), (0.88, 0.007), (BODY_TO, 0.004))
LOW_RINGS = 5.0

MIDDLE_FINS = [
    # the first dorsal fin: long and low
    {"part": 1, "name": "first dorsal", "shape": "long", "top": True, "from": 0.228, "long": 0.37, "high": 0.04, "lean": 15.0, "thick": 0.003, "nt": 8, "nu": 60},
    # the second, close behind it, and the anal fin under that
    {"part": 2, "name": "second dorsal", "shape": "sickle", "top": True, "from": 0.615, "long": 0.06, "high": 0.05, "lean": 35.0, "thick": 0.004, "nt": 8, "nu": 10},
    {"part": 3, "name": "anal", "shape": "sickle", "top": False, "from": 0.635, "long": 0.055, "high": 0.045, "lean": 35.0, "thick": 0.004, "nt": 8, "nu": 10},
]
FINLETS = [
    {"top": True, "count": 9, "from": 0.685, "to": 0.885, "long": 0.018, "high": 0.014, "high_end": 0.009},
    {"top": False, "count": 9, "from": 0.70, "to": 0.885, "long": 0.018, "high": 0.014, "high_end": 0.009},
]
TAIL = {"root": 0.895, "lead": (0.945, 0.07), "tip": (1.0, 0.115), "notch": 0.94, "trail": (0.962, 0.04), "thick": 0.006}
PECTORAL = {"s": 0.24, "angle": 100.0, "long": 0.075, "wide": 0.03, "span": (0.28, -0.2, 0.93), "chord": (0.08, -0.86, 0.45), "point": 0.65, "sweep": 0.12}
PELVIC = {"s": 0.27, "out": 0.008, "long": 0.045, "wide": 0.018}
# The teeth: (of the upper jaw?, how far along, how long, how far out towards the lip): a close-set row in each jaw.
TEETH = [(upper, 0.012 + 0.0045 * i, 0.0045, 0.78) for upper in (True, False) for i in range(21)]
# (the low model keeps one tooth in this many)
LOW_TEETH = 3
# The game model (a third, at about Twilight Princess weight, built from the same outline with its triangles
# where the eye sees them): points over the back and under the belly on each ring; how far the outline between
# two rings may stray from the true curve, from above, the side and below (body lengths), and the longest gap
# between rings (for the swimming bend); the rows across the inside of the mouth; the eye's spokes and its rings
# (as fractions of its radius); the rows of the tail, the pectoral and the pelvic fins from root to tip.
GAME = {"nu": 18, "nl": 12, "tol": 0.0004, "step": 0.04, "mouth": 2, "spokes": 28, "eye": (0.3, 0.56, 0.8, 1.0),
        "tail": 8, "pectoral": 6, "pelvic": 4}


import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "models")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = ARGS[0] if ARGS else ""

P_BODY, P_DORSAL1, P_DORSAL2, P_ANAL, P_TAIL, P_PECTORAL, P_PELVIC, P_EYE, P_MOUTH, P_TEETH, P_FINLET = range(11)
TAU = math.tau
SIDE = Vector((1.0, 0.0, 0.0))
# Which model is being built: `low` is False for the full one, True for the low one, GAME_MODEL for the game one.
GAME_MODEL = 2


def pick(low, full, lo, game):
    """The full model's number, the low one's, or the game one's."""
    return game if low == GAME_MODEL else (lo if low else full)


def to_b(p):
    return Vector((p.x, -p.z, p.y))


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def lerp(a, b, t):
    return a + (b - a) * t


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


def outline(s):
    """(half depth above, half depth below, half width) at `s`, all in body lengths."""
    s = max(_XS[0], min(_XS[-1], s))
    i = 0
    while i < len(_XS) - 2 and s > _XS[i + 1]:
        i += 1
    h = _XS[i + 1] - _XS[i]
    t = (s - _XS[i]) / h
    out = []
    for ys, m in _CURVES:
        a = (2 * t ** 3 - 3 * t ** 2 + 1) * ys[i] + (t ** 3 - 2 * t ** 2 + t) * h * m[i]
        b = (-2 * t ** 3 + 3 * t ** 2) * ys[i + 1] + (t ** 3 - t ** 2) * h * m[i + 1]
        out.append(max(a + b, 0.0005))
    return out


def seam_angle(s):
    """How far round from the ridge of the back the line of the mouth is, at `s` (as the shader has it);
    behind the jaw's hinge it is only where the grid's upper and lower halves meet."""
    return math.radians(lerp(SEAM_A0, SEAM_A1, max(0.0, min(1.0, s / HINGE_S))))


def gill_s(y):
    return GILL_S - GILL_K * (y - GILL_Y0) ** 2


def raw_point(s, angle):
    """A point of the skin as if the mouth were not cut: `angle` round the body from the ridge of the back
    (0) by its left side (a quarter turn) to the keel of the belly (half a turn)."""
    up, down, wide = outline(s)
    c = math.cos(angle)
    sn = math.sin(angle)
    # (a flat-topped head: the upper half of the section is squarer there)
    power = lerp(FLAT, 1.0, smooth(FLAT_TO * 0.6, FLAT_TO, s))
    y = (c ** power) * up if c >= 0.0 else c * down
    side = math.copysign(abs(sn) ** 0.9, sn) * wide
    side *= 1.0 - KEEL * smooth(0.1, 1.0, -c) * smooth(0.12, 0.25, s)
    # the gill cover: it stands a little proud of the body behind its edge
    behind = s - gill_s(y)
    if behind > 0.0 and wide > 0.005:
        mask = smooth(-0.97, -0.8, c) * (1.0 - smooth(0.5, 0.7, c))
        step = GILL_STEP * smooth(0.0, 0.004, behind) * math.exp(-behind / 0.03) * mask
        side *= 1.0 - step / wide
    return Vector((side, y, s - 0.5))


def body_point(s, angle, lower=False):
    """A point of the skin. Ahead of the jaw's hinge the head is two pieces, the upper head and the lower
    jaw (`lower`), which meet along the line of the mouth; each may begin behind the other's tip."""
    p = raw_point(s, angle)
    if s < HINGE_S:
        a = seam_angle(s)
        fade = 1.0 - smooth(HINGE_S - BLEND, HINGE_S, s)
        fold = abs(math.atan2(math.sin(angle), math.cos(angle)))
        # the lips: a shallow groove along the line of the mouth
        p.x *= 1.0 - INSET * math.exp(-((fold - a) / 0.14) ** 2) * fade
        start = LOW_FROM if lower else UP_FROM
        if start > 0.0:
            f = max(0.0, min(1.0, (s - start) / TAPER)) ** 0.55
            cy = raw_point(s, a).y
            p.x *= f
            p.y = cy + (p.y - cy) * f
    return p


def top(s):
    return raw_point(s, 0.0).y


def bottom(s):
    return -outline(s)[1]


def skin(s, y, sx):
    """The point of the skin (of the upper head and the body) at `s` and height `y`, on the left side
    (sx 1) or the right (-1)."""
    lo, hi = 0.0, math.pi
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if body_point(s, mid).y > y:
            lo = mid
        else:
            hi = mid
    return body_point(s, sx * 0.5 * (lo + hi))


def jaw_weight(s):
    """How much of the lower jaw's swing a point of it at `s` takes (the throat behind the hinge, none)."""
    return 1.0 - smooth(HINGE_S - BLEND, HINGE_S, s)


def upper_weight(s):
    """The same for the upper head's small lift, as a negative number (the shader tells them apart by it)."""
    return -(1.0 - smooth(0.4 * HINGE_S, 0.95 * HINGE_S, s))


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        # per point: (uv, uv2), or a colour (the school model)
        self.data = []
        # per face: the way it should face
        self.out = []
        self.count = {}

    def add(self, p, uv, part, weight=0.0):
        self.verts.append(p)
        self.data.append(((uv[0], 1.0 - uv[1]), (weight, 1.0 - part)))
        return len(self.verts) - 1

    def dab(self, p, colour):
        self.verts.append(p)
        self.data.append(colour)
        return len(self.verts) - 1

    def face(self, points, out, name):
        """A face wound so that its front (the side its points go round anticlockwise) is towards `out`."""
        ps = [self.verts[i] for i in points]
        n = Vector((0.0, 0.0, 0.0))
        for i in range(len(ps)):
            n += ps[i].cross(ps[(i + 1) % len(ps)])
        if n.length < 1e-16:
            return
        if n.dot(out) < 0.0:
            points = tuple(reversed(points))
        self.faces.append(tuple(points))
        self.out.append((Vector(out), name))
        self.count[name] = self.count.get(name, 0) + 1


def game_rings():
    """The game model's rings: as few as keep the outline from the side and from above within GAME["tol"] of the
    true curve (so they crowd where it bends, at the snout, the jaws' tips, the gill cover and the tail's wrist,
    and spread over the long straight flanks), never further apart than GAME["step"] (half as far again at the front); one on the jaw's hinge."""
    def shape(s):
        return (body_point(s, 0.0).y, body_point(s, math.pi, True).y, body_point(s, 0.5 * math.pi).x,
                body_point(s, 0.5 * math.pi, True).x if s < HINGE_S else body_point(s, 0.5 * math.pi).x)

    def fits(a, b):
        fa, fb = shape(a), shape(b)
        for i in range(1, 8):
            t = i / 8
            f = shape(lerp(a, b, t))
            if max(abs(f[k] - lerp(fa[k], fb[k], t)) for k in range(4)) > GAME["tol"]:
                return False
        return True

    def longest(s):
        """The longest gap between rings at `s`: longer at the front, which hardly bends as it swims."""
        return GAME["step"] * (1.6 - 0.6 * smooth(0.25, 0.55, s))

    def march(a, b):
        """From `a` to `b`: each next ring as far on as the outline allows."""
        xs = [a]
        fine = 0.0005
        while b - xs[-1] > 1e-9:
            at = xs[-1]
            n = 1
            while at + (n + 1) * fine < b and (n + 1) * fine <= longest(at) and fits(at, at + (n + 1) * fine):
                n += 1
            nxt = at + n * fine
            # (the last gap split evenly with the one before it, rather than left a sliver)
            if b - nxt < 1e-9 or not fits(at, b) or b - at > longest(at):
                xs.append(min(nxt, b) if b - nxt > 0.25 * n * fine else b)
            else:
                xs.append(b)
        return xs[:-1]

    stations = sorted({BODY_FROM, HINGE_S, BODY_TO} | ({UP_FROM + 0.0012} if UP_FROM > 0.0 else set()))
    xs = []
    for a, b in zip(stations, stations[1:]):
        xs += march(a, b)
    return xs + [BODY_TO]


def rings(low):
    if low == GAME_MODEL:
        return game_rings()
    xs = []
    x = BODY_FROM
    for until, step in RING_STEPS:
        if low:
            step *= LOW_RINGS
        n = max(1, round((until - x) / step))
        for i in range(n):
            xs.append(x + (until - x) * i / n)
        x = until
    xs.append(BODY_TO)
    return xs


def mouth_row(m, s, lower, k, shared=False):
    """A row of points across the inside of the mouth at `s`: of its roof (the underside of the upper
    head), or of its floor (the top of the lower jaw). UV.x says how far inside the mouth a point is (0 at
    the lips, and on top of a lower jaw's tip where it juts past the upper)."""
    a = seam_angle(s)
    lp = body_point(s, a, lower)
    fade = 1.0 - smooth(HINGE_S - BLEND, HINGE_S, s)
    weight = 0.0 if shared else (jaw_weight(s) if lower else upper_weight(s))
    jut = smooth(UP_FROM, UP_FROM + TAPER, s) if UP_FROM > 0.0 else 1.0
    row = []
    for i in range(k + 1):
        u = i / k
        across = 1.0 - 2.0 * u
        arch = ARCH * abs(lp.x) * (1.0 - across * across) * fade
        inside = smooth(0.0, 0.3, 1.0 - abs(across))
        if lower:
            y = lp.y - arch * (2.0 * jut - 1.0)
            inside *= jut
        else:
            y = lp.y + arch
        if shared:
            inside = 1.0
        row.append(m.add(Vector((lp.x * across, y, lp.z)), (inside, 0.0), P_MOUTH, weight))
    return row


def fr(i, n, low, a=None):
    """How far across a half ring (seam to seam) its `i`th point of `n` is. Even, but for the game model, whose
    points crowd where the outline is seen: at the ridge of the back and the keel of the belly (from the side
    and the front) and, on the upper half (`a`, the seam's angle, given), at the widest point of each side, a
    quarter turn round from the ridge (from above), which always has a point; they spread over the flanks
    between."""
    if low != GAME_MODEL:
        return i / n
    half = n // 2
    if a is None:
        # (the lower half: seam, keel, seam)
        knots = [0.0, 0.5]
        steps = [half]
    else:
        # (the upper half: seam, the widest point, ridge; its share of the points from the hinge's seam, so that
        # every ring has the same)
        side = max(0.0, (math.radians(SEAM_A1) - 0.5 * math.pi) / (2.0 * math.radians(SEAM_A1)))
        first = max(1, min(half - 1, round(half * side / 0.5)))
        knots = [0.0, max((a - 0.5 * math.pi) / (2.0 * a), 0.25 * first / n), 0.5]
        steps = [first, half - first]
    j = i if i <= half else n - i
    for k, count in enumerate(steps):
        if j <= count:
            t = j / count
            t -= GAME.get("crowd", 0.6) * math.sin(2.0 * math.pi * t) / (2.0 * math.pi)
            u = lerp(knots[k], knots[k + 1], t)
            break
        j -= count
    return u if i <= half else 1.0 - u


def body(m, low):
    nu = pick(low, NU, NU_LOW, GAME["nu"])
    nl = pick(low, NL, NL_LOW, GAME["nl"])
    k = pick(low, 8, 2, GAME["mouth"])
    before = {}
    for s in rings(low):
        a = seam_angle(s)
        now = {"s": s}
        if s >= HINGE_S - 1e-9:
            upper = []
            for i in range(nu + 1):
                angle = lerp(-a, a, fr(i, nu, low, a))
                upper.append(m.add(body_point(s, angle), (s, 0.5 + 0.5 * math.cos(angle)), P_BODY))
            lower = [upper[nu]]
            for i in range(1, nl):
                angle = lerp(a, TAU - a, fr(i, nl, low))
                lower.append(m.add(body_point(s, angle), (s, 0.5 + 0.5 * math.cos(angle)), P_BODY))
            lower.append(upper[0])
            now["upper"] = upper
            now["lower"] = lower
            if abs(s - HINGE_S) < 1e-9:
                # the corner of the mouth: its roof and its floor are one row here
                now["roof"] = now["floor"] = mouth_row(m, s, False, k, True)
        else:
            if s > UP_FROM + 0.0009:
                now["upper"] = [m.add(body_point(s, lerp(-a, a, fr(i, nu, low, a))), (s, 0.5 + 0.5 * math.cos(lerp(-a, a, fr(i, nu, low, a)))), P_BODY, upper_weight(s))
                                for i in range(nu + 1)]
                now["roof"] = mouth_row(m, s, False, k)
            if s > LOW_FROM + 0.0009:
                now["lower"] = [m.add(body_point(s, lerp(a, TAU - a, fr(i, nl, low)), True), (s, 0.5 + 0.5 * math.cos(lerp(a, TAU - a, fr(i, nl, low)))), P_BODY, jaw_weight(s))
                                for i in range(nl + 1)]
                now["floor"] = mouth_row(m, s, True, k)
        whole = s >= HINGE_S - 1e-9
        ym = raw_point(s, a).y
        up, down, _ = outline(s)
        for key, name, lean in (("upper", "body", 1.0), ("lower", "body", -1.0), ("roof", "mouth", -1.0), ("floor", "mouth", 1.0)):
            if key not in now:
                continue
            row = now[key]
            skin_row = key in ("upper", "lower")
            if skin_row:
                centre = 0.0 if whole else (ym + 0.3 * (top(s) - ym) if key == "upper" else ym - 0.3 * (ym + down))
            if key not in before:
                if s > HINGE_S:
                    continue
                # the tip of this jaw: a fan
                start = UP_FROM if key in ("upper", "roof") else LOW_FROM
                tip_at = Vector((0.0, raw_point(max(start, 0.0), seam_angle(start)).y if start > 0.0 else 0.0, start - 0.5))
                if skin_row:
                    tip = m.add(tip_at, (start, 0.5), P_BODY, upper_weight(start) if key == "upper" else jaw_weight(start))
                    for i in range(len(row) - 1):
                        m.face((tip, row[i], row[i + 1]), Vector((0.0, 0.3 * lean, -1.0)), name)
                else:
                    tip = m.add(tip_at, (0.0, 0.0), P_MOUTH, upper_weight(start) if key == "roof" else jaw_weight(start))
                    for i in range(len(row) - 1):
                        m.face((tip, row[i], row[i + 1]), Vector((0.0, lean, 0.0)), name)
                continue
            last = before[key]
            for i in range(len(row) - 1):
                quad = (last[i], last[i + 1], row[i + 1], row[i])
                if skin_row:
                    middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
                    m.face(quad, Vector((middle.x, middle.y - centre, 0.0)), name)
                else:
                    m.face(quad, Vector((0.0, lean, 0.0)), name)
        before = now
    # the end inside the tail: a fan
    loop = before["upper"] + before["lower"][1:-1]
    tip = m.add(Vector((0.0, 0.0, BODY_TO + 0.002 - 0.5)), (BODY_TO, 0.5), P_BODY)
    for i in range(len(loop)):
        m.face((tip, loop[i], loop[(i + 1) % len(loop)]), Vector((0.0, 0.0, 1.0)), "body")


def teeth(m, low):
    """Each tooth a small cone standing in from a lip: hidden inside the other jaw while the mouth is shut."""
    # (the game model's teeth are the low model's: three-sided, one in LOW_TEETH)
    sides = pick(low, 6, 3, 3)
    for n, (upper, s, high, lat) in enumerate(TEETH):
        if low and n % LOW_TEETH:
            continue
        a = seam_angle(s)
        lp = body_point(s, a, not upper)
        up, down, _ = outline(s)
        room = (lp.y + down) if upper else (top(s) - lp.y)
        high = min(high, 0.5 * room)
        if high < 0.0008:
            continue
        weight = upper_weight(s) if upper else jaw_weight(s)
        way = -1.0 if upper else 1.0
        for sx in (1.0, -1.0):
            base = Vector((sx * lat * abs(lp.x), lp.y - way * (ARCH * abs(lp.x) * (1.0 - lat * lat) + 0.15 * high), lp.z))
            tip = base + Vector((-sx * 0.12 * high, way * 1.15 * high, 0.12 * high))
            r = 0.2 * high
            ring = []
            for i in range(sides):
                t = i / sides * TAU
                ring.append(m.add(base + Vector((math.cos(t) * r, 0.0, math.sin(t) * r * 1.4)), (0.0, 0.0), P_TEETH, weight))
            point = m.add(tip, (1.0, 0.0), P_TEETH, weight)
            for i in range(sides):
                p0 = m.verts[ring[i]]
                p1 = m.verts[ring[(i + 1) % sides]]
                m.face((ring[i], ring[(i + 1) % sides], point), (p0 + p1) * 0.5 - base, "teeth")
            if sx * lat == 0.0:
                break


def eye(m, sx, low):
    """A low dome lying on the skin of the head."""
    spokes = pick(low, 28, 10, GAME["spokes"])
    steps = pick(low, 8, 2, 0)
    radii = GAME["eye"] if low == GAME_MODEL else [k / steps for k in range(1, steps + 1)]
    xe, ye = EYE_AT
    d = EYE_R * 0.12
    here = skin(xe, ye, sx)
    out = (skin(xe + d, ye, sx) - skin(xe - d, ye, sx)).cross(skin(xe, ye + d, sx) - skin(xe, ye - d, sx))
    out.normalize()
    if out.x * sx < 0.0:
        out = -out
    middle = m.add(here + out * EYE_DOME, (0.0, 0.0), P_EYE, upper_weight(xe))
    last = None
    for r in radii:
        row = []
        for sp in range(spokes):
            a = sp / spokes * TAU
            s = xe + math.cos(a) * EYE_R * r
            p = skin(s, ye + math.sin(a) * EYE_R * r, sx)
            row.append(m.add(p + out * (EYE_DOME * (0.92 * (1.0 - r * r) + 0.08 * (1.0 - r))), (r, 0.0), P_EYE, upper_weight(s)))
        for sp in range(spokes):
            n = (sp + 1) % spokes
            if last is None:
                m.face((middle, row[sp], row[n]), out, "eyes")
            else:
                m.face((last[sp], row[sp], row[n], last[n]), out, "eyes")
        last = row


def blade(m, part, name, point, place, facing, thick, nt, nu):
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
    """A place in the flat of the middle fins (body lengths behind the jaw, body lengths up) in the model."""
    return Vector((0.0, p[1], p[0] - 0.5))


def fin_high(f, u):
    """How tall a middle fin is, `u` of the way along its base."""
    shape = f["shape"]
    if shape == "spiny":
        # tallest near its front, its rear edge running down to the back
        return f["high"] * (0.06 + 0.94 * (1.0 - u) ** 1.25) * (0.4 + 0.6 * smooth(0.0, 0.16, u))
    if shape == "sickle":
        # a tall front lobe, low behind it
        return f["high"] * (0.16 + 0.84 * (1.0 - u) ** 2.4) * (0.4 + 0.6 * smooth(0.0, 0.2, u))
    if shape == "long":
        # long and low, a little taller a third of the way back, running down at its end
        return f["high"] * (0.72 + 0.28 * math.sin(math.pi * min(u * 1.5, 1.0))) * (0.45 + 0.55 * smooth(0.0, 0.05, u)) * (1.0 - 0.8 * smooth(0.6, 1.0, u))
    # a finlet
    return f["high"] * (0.1 + 0.9 * (1.0 - u) ** 0.9) * (0.5 + 0.5 * smooth(0.0, 0.25, u))


def middle_fin(m, f, low):
    lean = math.radians(f["lean"])
    way = 1.0 if f["top"] else -1.0
    sink = f.get("sink", 0.004)

    def point(t, u):
        s = f["from"] + f["long"] * u
        high = fin_high(f, u) * t
        edge = top(s) - sink if f["top"] else bottom(s) + sink
        return (s + math.sin(lean) * high, edge + way * (math.cos(lean) * high + sink * t))

    if low == GAME_MODEL:
        # (the game model: its outline is its top edge, along its base, so the rows go there; root to edge
        # it is straight)
        blade(m, f["part"], f["name"], point, upright, SIDE, f["thick"], 2, f.get("game_nu", max(4, round(0.6 * f["nu"]))))
        return
    d = 3 if low else 1
    blade(m, f["part"], f["name"], point, upright, SIDE, f["thick"], f["nt"] // d, f["nu"] // d)


def fins(m, low):
    d = 3 if low else 1
    game = low == GAME_MODEL
    for f in MIDDLE_FINS:
        middle_fin(m, f, low)
    for row in FINLETS:
        for i in range(row["count"]):
            at = lerp(row["from"], row["to"], i / max(row["count"] - 1, 1))
            size = lerp(row["high"], row["high_end"], i / max(row["count"] - 1, 1))
            middle_fin(m, {"part": P_FINLET, "name": "finlets", "shape": "finlet", "top": row["top"], "from": at,
                           "long": row["long"], "high": size, "lean": 58.0, "thick": 0.0022, "nt": 2 if low else 4, "nu": 2 if low else 5,
                           "sink": 0.002, "game_nu": 3}, low if game else False)
    # The tail: two lobes that meet along the middle line. (The game model's rows run root to tip, where its
    # edges curve; across, a lobe is straight.)
    t = TAIL
    for way in (1.0, -1.0):
        tip = (t["tip"][0], t["tip"][1] * way)
        blade(m, P_TAIL, "tail", swept(((t["root"], 0.0), (t["lead"][0], t["lead"][1] * way), tip),
                                      ((t["notch"], 0.0), (t["trail"][0], t["trail"][1] * way), tip)),
              upright, SIDE, t["thick"], GAME["tail"] if game else 20 // d, 2 if game else 8 // max(d - 1, 1))
    for sx in (1.0, -1.0):
        # The pectoral fins: behind the gill covers, lying back and a little down and out.
        f = PECTORAL
        root = body_point(f["s"], sx * math.radians(f["angle"]))
        root.x -= sx * 0.003
        span = Vector((sx * f["span"][0], f["span"][1], f["span"][2])).normalized()
        chord = Vector((sx * f["chord"][0], f["chord"][1], f["chord"][2])).normalized()
        facing = span.cross(chord).normalized()
        if facing.x * sx < 0.0:
            facing = -facing

        def pectoral_point(t, u, f=f):
            t *= 0.975
            wide_here = f["wide"] * (0.4 + 0.6 * smooth(0.0, 0.4, t)) * (1.0 - t) ** f["point"] + 0.0015
            return (f["long"] * t, f["sweep"] * f["long"] * t * t + wide_here * u)

        blade(m, P_PECTORAL, "pectorals", pectoral_point,
              lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.004, GAME["pectoral"] if game else 12 // d, 2 if game else 8 // max(d - 1, 1))
        # The pelvic fins: under the body, pointing back and down.
        f = PELVIC
        root = Vector((sx * f["out"], bottom(f["s"]) + 0.005, f["s"] - 0.5))
        span = Vector((sx * 0.26, -0.5, 0.83)).normalized()
        chord = Vector((0.0, 0.14, 1.0)).normalized()
        facing = span.cross(chord).normalized()
        if facing.x * sx < 0.0:
            facing = -facing

        def pelvic_point(t, u, f=f):
            t *= 0.97
            return (f["long"] * t, 0.16 * f["long"] * t * t + (f["wide"] * (1.0 - t) ** 0.8 + 0.0012) * u)

        blade(m, P_PELVIC, "pelvics", pelvic_point,
              lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.003, GAME["pelvic"] if game else 8 // d, 2 if game else 6 // d)


def material_of(name, colour):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = colour
    material.diffuse_color = colour
    return material


def make(name, low):
    m = Mesh()
    body(m, low)
    teeth(m, low)
    for sx in (1.0, -1.0):
        eye(m, sx, low)
    fins(m, low)
    mesh = bpy.data.meshes.new(name)
    # (everything above is in body lengths: here it becomes metres)
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
    mesh.materials.append(material_of(NAME, COLOUR))
    return finish(name, mesh, m)


def finish(name, mesh, m):
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
    """Nothing inside out: the skin of the body faces away from its middle line, the roof of the mouth
    down and its floor up, each skin of a fin away from the fin's own flat, an eye out from the head, a
    tooth's sides away from its middle (Blender's front is the side a face's normal is on)."""
    bad = {}
    for poly in mesh.polygons:
        out, group = m.out[poly.index]
        if poly.normal.dot(to_b(out)) <= 0.0:
            bad[group] = bad.get(group, 0) + 1
    told = ["%s %d/%d wrong" % (group, bad.get(group, 0), count) for group, count in m.count.items()]
    print("WINDING %s: %s: %s" % (name, "ok" if not bad else "INSIDE OUT", ", ".join(told)))


def export_one(obj, path, colours=False):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", export_yup=True, use_selection=True,
        export_animations=False, export_texcoords=not colours,
        export_vertex_color="ACTIVE" if colours else "NONE", export_all_vertex_colors=False,
    )


def render(folder, made):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.show_cavity = True
    scene.render.resolution_x, scene.render.resolution_y = 1400, 800
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    # (Blender space: the fish lies along Y, its nose at +Y, up is Z)
    views = [("left", (1, 0, 0), (0, 0, 0), 1.12), ("right", (-1, 0, 0), (0, 0, 0), 1.12),
             ("front", (0, 1, 0), (0, 0, 0), 0.45), ("back", (0, -1, 0), (0, 0, 0), 0.45),
             ("top", (0.001, 0, 1), (0, 0, 0), 1.9), ("under", (0.001, 0, -1), (0, 0, 0), 1.9),
             ("head", (0.8, 0.5, 0.2), (0, 0.36, 0), 0.42), ("tail", (0.7, -0.6, 0.3), (0, -0.36, 0), 0.5)]
    for index, obj in enumerate(made):
        prefix = ("", "lo_", "school_")[index]
        only = (None, ("left", "head", "top"), ("left", "right", "top", "under", "front", "head"))[index]
        scene.display.shading.color_type = "VERTEX" if index == 2 else "MATERIAL"
        # (the school model's sheets are drawn from both sides)
        scene.display.shading.show_backface_culling = index != 2
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if only and view not in only:
                continue
            offset = Vector(direction).normalized() * 40.0
            camera.data.ortho_scale = frame * LENGTH
            camera.location = Vector(target) * LENGTH + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % (prefix, view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    a = seam_angle(HINGE_S)
    print("SHAPE %s: HINGE_S=%.4f HINGE_Y=%.5f (body lengths: the shader has both)" % (NAME, HINGE_S, raw_point(HINGE_S, a).y))
    made = [make(NAME, False), make(NAME + "_lo", True)]
    if "make_school" in globals():
        made.append(globals()["make_school"](NAME + "_school"))
    game = make(NAME + "_game", GAME_MODEL)
    os.makedirs(OUT, exist_ok=True)
    export_one(made[0], os.path.join(OUT, NAME + ".glb"))
    export_one(made[1], os.path.join(OUT, NAME + "_lo.glb"))
    if len(made) > 2:
        export_one(made[2], os.path.join(OUT, NAME + "_school.glb"), True)
    export_one(game, os.path.join(OUT, NAME + "_game.glb"))
    for index, obj in enumerate(made + [game]):
        obj.location.x = 0.4 * LENGTH * index
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, NAME + ".blend"))
    for obj in made + [game]:
        obj.location.x = 0.0
    game.hide_render = True
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, made)


if __name__ == "__main__":
    main()
