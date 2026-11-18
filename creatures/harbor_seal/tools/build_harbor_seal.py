"""Builds the harbor seal (creatures/harbor_seal) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/harbor_seal/tools/build_harbor_seal.py
    blender --background --python creatures/harbor_seal/tools/build_harbor_seal.py -- <preview folder>   # with pictures

Writes creatures/harbor_seal/models/harbor_seal.glb (the full model, for close pictures) and
harbor_seal_lo.glb (far off, phones), harbor_seal_game.glb (the game model: about a
tenth of the triangles, spent on its outline, face, eyes and flippers), and the editable creatures/harbor_seal/tools/harbor_seal.blend (this
folder has a .gdignore). Each model is one still mesh with one surface: the shader (harbor_seal.gdshader) draws
its coat and spots, swims it, fans its hind flippers and opens its jaw. It prints a WINDING line: the check
that nothing is inside out.

A harbor seal (Phoca vitulina), 1.6 m from the tip of its nose to the tips of its hind flippers, built from the
species (no picture was traced):

- THE BODY: a plump spindle, deepest (0.41 m) and widest (0.43 m) well ahead of its middle, tapering to narrow
  hips and a stub of a tail between the hind flippers. A round, cat-like head on a thick neck that is hardly
  narrower than the head; a short broad muzzle with fat whisker pads; no ear flaps.
- THE HEAD: big round eyes set forward (a dome each); the upper head is cut away below the line of the lips, so
  that its underside is the roof of the mouth; the LOWER JAW is a part of its own which the shader swings down
  about its hinge; teeth in both jaws and a tongue, hidden while the mouth is shut; whiskers on the pads and
  over the eyes.
- THE FLIPPERS: two short fore flippers held back against its sides, five claws each; two hind flippers that
  point straight back, soles together like the two halves of a fish's tail, five toes each (the outer two the
  longest).

The numbers marked "as the shader has it" are in harbor_seal.gdshader too: change one, change the other.
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

NAME = "harbor_seal"
LENGTH = 1.6
COLOUR = (0.5, 0.5, 0.48, 1.0)

# The body's outline: metres behind the nose, the height of its back line, the height it is widest at, the
# height of its belly line (of the chin, where the mouth is), half its width.
PROFILE = [
    (0.0, 0.016, 0.004, -0.008, 0.0005),
    (0.004, 0.030, 0.006, -0.024, 0.024),
    (0.015, 0.041, 0.006, -0.038, 0.038),
    (0.035, 0.050, 0.006, -0.048, 0.048),
    (0.060, 0.064, 0.010, -0.056, 0.058),
    (0.090, 0.086, 0.014, -0.066, 0.075),
    (0.125, 0.100, 0.014, -0.076, 0.087),
    (0.165, 0.103, 0.012, -0.084, 0.090),
    (0.21, 0.102, 0.008, -0.092, 0.092),
    (0.27, 0.112, 0.004, -0.108, 0.108),
    (0.36, 0.146, 0.0, -0.142, 0.152),
    (0.48, 0.186, 0.0, -0.182, 0.196),
    (0.62, 0.205, -0.005, -0.205, 0.215),
    (0.78, 0.195, -0.005, -0.200, 0.205),
    (0.94, 0.165, 0.0, -0.165, 0.170),
    (1.08, 0.125, 0.0, -0.125, 0.128),
    (1.20, 0.088, 0.0, -0.085, 0.090),
    (1.30, 0.060, 0.0, -0.055, 0.062),
    (1.37, 0.044, 0.0, -0.040, 0.048),
    (1.41, 0.028, 0.0, -0.026, 0.030),
    (1.445, 0.003, 0.0, -0.003, 0.003),
]
BODY_FROM = 0.0015
BODY_TO = 1.445
# (how closely the rings of points are spaced, as far back as each place)
RINGS = ((0.20, 0.004), (0.50, 0.012), (1.20, 0.018), (BODY_TO, 0.008))
AROUND = 84
AROUND_LO = 22
ROUND = 0.92

# The mouth. As the shader has it: the corner of the mouth and the jaw's hinge.
CORNER = 0.082
HINGE_X = 0.128
HINGE_Y = -0.032
JAW_TIP = 0.004
JAW_ROUND = 0.014
JAW_WIDE = 0.95
# (how far the roof of the mouth is arched up and its floor sunk, as shares of the head above and the jaw below)
PALATE = 0.2
TROUGH = 0.3
GAP = 0.001
OVERHANG = 0.0022
# (metres behind the nose, out to the side as a share of the lip's edge, how long, how wide at the root): four
# incisors, the canines, five cheek teeth a side
TEETH = [
    (0.02, 0.14, 0.005, 0.002), (0.022, 0.38, 0.006, 0.0022),
    (0.03, 0.62, 0.013, 0.004),
    (0.038, 0.74, 0.006, 0.0032), (0.047, 0.77, 0.007, 0.0034), (0.056, 0.79, 0.007, 0.0034),
    (0.065, 0.8, 0.006, 0.0032), (0.073, 0.81, 0.005, 0.0028),
]
TEETH_LOW = 0.012
TONGUE_AT = (0.02, 0.075, 0.007)
# (metres behind the nose, degrees round from the back line, its radius, how far it bulges)
EYE_AT = (0.088, 50.0, 0.0215, 0.0085)
# The game model (see GAME below): points round the body; how near (metres) its skin keeps to the full model's;
# how far apart its rings may be at most, along the body and over the mouth; rings in the lower jaw; places
# that must have a ring.
GAME_AROUND = 28
GAME_TOL = 0.0012
GAME_STEP = 0.09
GAME_MOUTH_STEP = 0.016
GAME_JAW = 14
GAME_KEEP = ()
# (and how many pieces each whisker is made of)
GAME_WHISKER = 3


def lip(xm):
    """The line of the lips: how high, `xm` behind the nose (a faint smile)."""
    return -0.013 - 0.2 * xm + 0.9 * (xm - 0.04) ** 2


def sculpt(xm, c):
    """How much wider the skin is at a place than the plain outline: the whisker pads."""
    pad = math.exp(-((xm - 0.03) / 0.022) ** 2) * math.exp(-((c + 0.05) / 0.5) ** 2)
    return 1.0 + 0.13 * pad


def extras(m, low):
    d = 3 if low else 1
    for sx in (1.0, -1.0):
        # The fore flippers: short paddles held back against its sides, five claws at the end of each.
        at = math.radians(118.0) * sx
        out = out_of_skin(0.47, at)
        root = skin(0.47, at) - out * 0.022
        span = (Vector((sx * 0.22, -0.42, 0.88)) + out * 0.1).normalized()
        chord = out.cross(span).normalized()
        if chord.y > 0.0:
            chord = -chord
        facing = span.cross(chord).normalized()
        if facing.dot(out) < 0.0:
            facing = -facing

        def fore_point(t, u):
            wide = 0.105 * (0.62 + 0.38 * math.sin(math.pi * min(1.0, t * 1.15) ** 0.8)) * (1.0 - 0.45 * smooth(0.7, 1.0, t))
            return (0.215 * t, (u - 0.42) * wide + 0.02 * t * t)

        place = lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1]
        m.part(SKIN, FORE_L if sx > 0.0 else FORE_R, root)
        blade(m, "fore flippers", fore_point, place, facing, 0.034, *((6, 5) if GAME else (20 // d, 10 // d)), edge=0.25, tip=0.3)
        m.part(CLAW, FORE_L if sx > 0.0 else FORE_R, root)
        for k in range(5):
            u = 0.12 + 0.19 * k
            base = place(fore_point(0.96, u))
            cone(m, base, base + span * 0.03 + facing * 0.004, 0.0045, "claws", 4 if low or GAME else 7, 1 if low or GAME else 3)
        # The hind flippers: they point straight back, soles together, each a fan of five toes with the
        # outer two the longest.
        root = Vector((sx * 0.022, 0.0, 1.355 - HALF))
        span = Vector((sx * 0.11, 0.0, 1.0)).normalized()
        facing = span.cross(Y).normalized()

        def hind_point(t, u):
            fan = math.radians(27.0) * (u * 2.0 - 1.0)
            reach = 0.268 * (1.0 - 0.24 * math.sin(math.pi * u) ** 1.5) * (0.93 + 0.07 * abs(math.cos(math.pi * u * 5.0)) ** 0.6)
            a = (0.0, (u - 0.5) * 0.06)
            b = (math.cos(fan) * reach, math.sin(fan) * reach)
            k = t ** 0.9
            return (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)

        m.part(SKIN, HIND_L if sx > 0.0 else HIND_R, root)
        blade(m, "hind flippers", hind_point, lambda p, root=root, span=span: root + span * p[0] + Y * p[1],
              facing, 0.03, *((3, 20) if GAME else (22 // d, 30 // d)), tip=0.12)
        # Whiskers: on the pads of the muzzle, and a few over each eye.
        m.part(WHISKER)
        rows = ((78.0, 0.07), (92.0, 0.095), (106.0, 0.085)) if not low else ((92.0, 0.09),)
        for degrees, length in rows:
            for k in range(2 if low else 5):
                xm = 0.014 + 0.0075 * k * (2.5 if low else 1.0)
                at = math.radians(degrees + 3.0 * (k % 2)) * sx
                out = out_of_skin(xm, at)
                way = (out + Vector((0.0, -0.1, 0.25 + 0.08 * k))).normalized()
                whisker(m, skin(xm, at) - out * 0.002, way, length * (0.6 + 0.1 * k),
                        Vector((0.0, -0.22, 0.2)), 0.0011, low)
        if not low:
            for k in range(3):
                at = math.radians(24.0 + 5.0 * k) * sx
                out = out_of_skin(0.07 + 0.006 * k, at)
                whisker(m, skin(0.07 + 0.006 * k, at) - out * 0.002, (out + Vector((0.0, 0.3, 0.2))).normalized(),
                        0.045 - 0.006 * k, Vector((0.0, -0.1, 0.3)), 0.0009, low)


# ======================================================================================================
# From here down GameCommon's three sea mammals (harbor seal, sea lion, sea otter) are built by the same
# code: change it in one, change it in the others. Everything above is this animal's own.
#
# Everything is in Godot space (metres, Y up, +X its left side, its nose at -Z) until it is written out;
# the origin is on its middle line, half way along. `xm` is metres behind the tip of its nose.
#
# What a point is, for the shader:
#   vertex colour red   what it is made of, as a tenth (0 fur, 0.1 an eye, 0.2 a tooth, 0.3 the tongue,
#                       0.4 a whisker, 0.5 bare hide, 0.6 a claw)
#   vertex colour green how far inside the mouth it is (0 outside, 0.5 the lip's edge, 1 inside)
#   vertex colour blue  on a flipper or a limb: how far along it, 0 its root to 1 its tip; on an eye, 0 its
#                       middle to 1 its rim; on the skin of the head and jaw, how much it is the lips' edge
#   UV2.y               what moves it, as an eighth (0 nothing, 1 the lower jaw, 2 and 3 the left and right
#                       fore limbs, 4 and 5 the left and right hind limbs)
#   UV.x, UV.y, UV2.x   its hinge: where the jaw or the limb it belongs to turns, as z, y and x in body
#                       lengths plus a half (so always between 0 and 1)
# (The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.)

HALF = LENGTH * 0.5
TAU = math.tau
SKIN, EYE, TOOTH, TONGUE, WHISKER, HIDE, CLAW = range(7)
STILL, JAW, FORE_L, FORE_R, HIND_L, HIND_R = range(6)
X = Vector((1.0, 0.0, 0.0))
Y = Vector((0.0, 1.0, 0.0))
Z = Vector((0.0, 0.0, 1.0))

# The game model (added 2026-11-18; the user: "We should have a twilight princess model to compare to so we can
# make low poly versions while maintaining high quality looks and silhouettes"): the same parts from the same
# curves, its rings of points where the outline bends (the nose, the mouth, round the eye, the neck, the hips)
# and few along the smooth flanks, a round eye, simpler teeth, thinner whiskers' curves, flippers with their
# points on their edges and toes. GAME is True while it is being made; the GAME_* numbers are this animal's.
GAME = False


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
for _column in (1, 2, 3, 4):
    _ys = [p[_column] for p in PROFILE]
    _CURVES.append((_ys, _slopes(_XS, _ys)))


def outline(xm):
    """(the back line's height, the height it is widest at, the belly line's height, half its width) at `xm`."""
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
    out[3] = max(out[3], 0.0003)
    return out


def full_point(xm, angle):
    """(how far to its side, how high) the skin is, as if it had no mouth: `angle` round the body from the
    back line (0) by its left side (a quarter turn) to the belly line (half a turn)."""
    top, mid, bot, wide = outline(xm)
    c = math.cos(angle)
    s = math.sin(angle)
    y = mid + c * ((top - mid) if c >= 0.0 else (mid - bot))
    side = math.copysign(abs(s) ** ROUND, s) * wide
    return side * sculpt(xm, c), y


def angle_at(xm, y):
    """The angle at which the skin is `y` high."""
    top, mid, bot, _ = outline(xm)
    if y >= mid:
        c = min(1.0, (y - mid) / max(top - mid, 1e-6))
    else:
        c = -min(1.0, (mid - y) / max(mid - bot, 1e-6))
    return math.acos(c)


def skin(xm, angle):
    side, y = full_point(xm, angle)
    return Vector((side, y, xm - HALF))


def out_of_skin(xm, angle):
    """The way the skin faces at a place (a unit vector)."""
    sx = 1.0 if angle >= 0.0 else -1.0
    along = skin(xm + 0.003, angle) - skin(xm - 0.003, angle)
    around = skin(xm, angle + 0.02) - skin(xm, angle - 0.02)
    out = around.cross(along)
    out.normalize()
    here = skin(xm, angle)
    if out.dot(Vector((here.x, here.y - outline(xm)[1], 0.0))) < 0.0:
        out = -out
    if out.length < 0.5:
        out = Vector((sx, 0.0, 0.0))
    return out


def palate_at(xm, share):
    """How far the roof of the mouth is arched up above the line of the lips: `share` is how far out from
    the middle line to the lip's edge."""
    front = smooth(JAW_TIP + JAW_ROUND * 0.5, JAW_TIP + JAW_ROUND * 1.5, xm)
    return PALATE * (outline(xm)[0] - lip(xm)) * (1.0 - min(1.0, share) ** 4) * (1.0 - wall(xm)) * front


def trough_at(xm, share):
    """How far the floor of the mouth is sunk below the lower lip."""
    return TROUGH * max(0.0, jaw_floor(xm) - outline(xm)[2]) * (1.0 - min(1.0, share) ** 2) ** 2


def jaw_grow(xm):
    return max(0.0, min(1.0, (xm - JAW_TIP) / JAW_ROUND)) ** 0.5


def wall(xm):
    """0 where the mouth is, rising to 1 at the jaw's hinge: the back of the mouth."""
    return smooth(CORNER, HINGE_X, xm)


def roof(xm):
    """Where the upper head's skin is cut away for the mouth: there is none of it below this height. As far
    back as the corner of the mouth it is the line of the lips; behind, it falls away to the throat."""
    line = lip(xm)
    if xm <= CORNER:
        # (the upper lip hangs a little way down over the lower)
        return line - OVERHANG * smooth(JAW_TIP, JAW_TIP + JAW_ROUND, xm) * (1.0 - smooth(CORNER - 0.3 * (HINGE_X - CORNER), CORNER, xm))
    bot = outline(xm)[2]
    return line - wall(xm) * (line - bot)


def jaw_floor(xm):
    """The top of the lower jaw: just under the line of the lips, and behind the corner of the mouth just
    under where the upper head's skin is cut away, so that the jaw thins to nothing at its hinge."""
    return (lip(xm) if xm <= CORNER else roof(xm)) - GAP * (1.0 - wall(xm))


def columns(xm, half, split, cut, even_share):
    """The angles of a ring's points down one side, from the back line (0) to the belly line (pi). Where
    the mouth is, point `split` lies on the edge of the cut, so that the lip is a clean line."""
    even = [math.pi * h / half for h in range(half + 1)]
    if even_share >= 1.0:
        return even
    a = min(max(angle_at(xm, cut), 0.2 * math.pi), 0.985 * math.pi)
    out = []
    for h in range(half + 1):
        mine = a * h / split if h <= split else a + (math.pi - a) * (h - split) / (half - split)
        out.append(mine + (even[h] - mine) * even_share)
    return out


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        # per point: (what it is, what moves it, its hinge, inside the mouth, along its limb)
        self.data = []
        # per face: the way it should face, and the name of its part
        self.out = []
        self.count = {}
        self.kind = SKIN
        self.group = STILL
        self.hinge = Vector((0.0, 0.0, 0.0))

    def part(self, kind, group=STILL, hinge=None):
        self.kind = kind
        self.group = group
        self.hinge = Vector(hinge) if hinge is not None else Vector((0.0, 0.0, 0.0))

    def add(self, p, inside=0.0, along=0.0):
        self.verts.append(Vector(p))
        self.data.append((self.kind, self.group, self.hinge, inside, along))
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
            n = -n
        if len(points) == 4:
            # (a twisted four-sided face: cut it the way that leaves neither half folded over)
            a, b, c, d = points
            pa, pb, pc, pd = (self.verts[i] for i in points)

            def faces_out(p, q, r):
                return (q - p).cross(r - p).dot(n) > 0.0

            first = faces_out(pa, pb, pc) and faces_out(pa, pc, pd)
            second = faces_out(pa, pb, pd) and faces_out(pb, pc, pd)
            if not (first and second):
                halves = ((a, b, d), (b, c, d)) if second and not first else ((a, b, c), (a, c, d))
                for half in halves:
                    self.face(half, out, name)
                return
        self.faces.append(tuple(points))
        self.out.append((Vector(out), name))
        self.count[name] = self.count.get(name, 0) + 1


def rings(low):
    if GAME:
        return game_rings()
    return even_rings(low)


def game_rings():
    """The game model's rings: of the full model's (and a few places that must have one: the chin, the corner
    of the mouth, the hinge, across the eye, GAME_KEEP), as few as keep the skin within GAME_TOL metres of
    the full model's, and never further apart than GAME_STEP (GAME_MOUTH_STEP as far back as the hinge)."""
    xe, _, radius, _ = EYE_AT
    must = [BODY_FROM, BODY_TO, JAW_TIP + JAW_ROUND, CORNER, HINGE_X] + [xe + radius * k for k in (-1.0, -0.5, 0.0, 0.5, 1.0)]
    must = [x for x in must + list(GAME_KEEP) if BODY_FROM <= x <= BODY_TO]
    xs = sorted(set(even_rings(False) + must))
    hard = set(must)
    angles = [math.pi * k / 16.0 for k in range(17)]

    def sample(xm):
        out = []
        for a in angles:
            side, y = full_point(xm, a)
            if xm < HINGE_X:
                y = max(y, roof(xm))
            out.append((side, y))
        return out

    points = [sample(x) for x in xs]

    def fits(i, k):
        for m in range(i + 1, k):
            t = (xs[m] - xs[i]) / (xs[k] - xs[i])
            for a in range(len(angles)):
                sx = points[i][a][0] + (points[k][a][0] - points[i][a][0]) * t
                sy = points[i][a][1] + (points[k][a][1] - points[i][a][1]) * t
                if math.hypot(sx - points[m][a][0], sy - points[m][a][1]) > GAME_TOL:
                    return False
        return True

    kept = [0]
    i = 0
    while i < len(xs) - 1:
        j = i + 1
        while j + 1 < len(xs) and xs[j] not in hard:
            k = j + 1
            if xs[k] - xs[i] > (GAME_MOUTH_STEP if xs[i] < HINGE_X else GAME_STEP) or not fits(i, k):
                break
            j = k
        kept.append(j)
        i = j
    return [xs[k] for k in kept]



def cols():
    """How wide the lip's dark edge and the change to the inside of the mouth are, in columns of points, as a
    share of the full model's (the game model's columns are wider apart)."""
    return GAME_AROUND / AROUND if GAME else 1.0

def even_rings(low):
    xs = []
    x = BODY_FROM
    for until, step in RINGS:
        if low:
            step *= 4.0
        n = max(1, round((until - x) / step))
        for i in range(n):
            xs.append(x + (until - x) * i / n)
        x = until
    xs.append(BODY_TO)
    return xs


def body(m, low):
    """The skin from the nose to the end of the body (or of the tail), the upper head cut away below the line
    of the lips: its underside there is the roof of the mouth."""
    m.part(SKIN)
    half = (GAME_AROUND if GAME else (AROUND_LO if low else AROUND)) // 2
    around = half * 2
    split = round(half * 0.62)
    grid = []
    cut_away = []
    centre = []
    for xm in rings(low):
        mouth = xm < HINGE_X
        cut = roof(xm) if mouth else -1e9
        angles = columns(xm, half, split, cut, wall(xm) if mouth else 1.0)
        front = smooth(JAW_TIP + JAW_ROUND * 0.8, JAW_TIP + JAW_ROUND * 1.8, xm)
        edge = max(abs(full_point(xm, angles[split])[0]), 1e-6)
        row = []
        flags = []
        for c in range(around):
            h = c if c <= half else around - c
            angle = angles[h] if c <= half else -angles[h]
            side, y = full_point(xm, angle)
            inside = 0.0
            lips = 0.0
            gone = False
            if mouth and xm <= CORNER:
                lips = max(0.0, 1.0 - abs(h - split) / (3.0 * cols())) * front
            if mouth and y <= cut + 1e-7:
                gone = y < cut - 1e-7 or h > split
                y = max(y, cut)
                if xm <= CORNER:
                    inside = min(1.0, max(0.0, (h - split) / (4.0 * cols())))
                    y += palate_at(xm, abs(side) / edge)
                else:
                    inside = 1.0 if gone else 0.0
                    lips = max(lips, (0.0 if gone else 1.0) * (1.0 - smooth(0.0, 0.4, wall(xm))))
                inside *= front
            row.append(m.add(Vector((side, y, xm - HALF)), inside, lips))
            flags.append(gone)
        grid.append(row)
        cut_away.append(flags)
        top, _, bot, _ = outline(xm)
        centre.append(0.5 * (top + max(bot, cut)))
    for r in range(len(grid) - 1):
        for c in range(around):
            n = (c + 1) % around
            quad = (grid[r][c], grid[r][n], grid[r + 1][n], grid[r + 1][c])
            if cut_away[r][c] and cut_away[r][n] and cut_away[r + 1][n] and cut_away[r + 1][c]:
                m.face(quad, Vector((0.0, -1.0, -1.0)), "mouth")
                continue
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((middle.x, middle.y - 0.5 * (centre[r] + centre[r + 1]), 0.0)), "body")
    # the tip of the nose and the end of the body: a fan each
    first = m.verts[grid[0][0]]
    last = m.verts[grid[-1][0]]
    for row, at, way in ((grid[0], Vector((0.0, centre[0], first.z - 0.002)), -1.0),
                         (grid[-1], Vector((0.0, centre[-1], last.z + 0.002)), 1.0)):
        tip = m.add(at)
        for c in range(around):
            m.face((tip, row[c], row[(c + 1) % around]), Vector((0.0, 0.0, way)), "body")


def jaw_point(xm, angle, clamp):
    """A point of the lower jaw: the skin as if it had no mouth, cut away above the mouth's floor, a little
    narrower than the upper lip, rounded off to the chin at its tip."""
    floor = jaw_floor(xm)
    grow = jaw_grow(xm)
    narrow = JAW_WIDE + (1.0 - JAW_WIDE) * smooth(CORNER - 0.3 * (HINGE_X - CORNER), CORNER + 0.4 * (HINGE_X - CORNER), xm)
    side, y = full_point(xm, angle)
    if clamp:
        y = floor - trough_at(xm, abs(side) / max(abs(full_point(xm, angle_at(xm, floor))[0]), 1e-6))
    y = floor - (floor - min(y, floor)) * grow
    return Vector((side * narrow * grow, y, xm - HALF))


def jaw(m, low):
    """The lower jaw and chin: a part of its own from its tip back to its hinge, where it meets the throat's
    skin; the shader swings it down. Its top is the floor of the mouth."""
    m.part(SKIN, JAW, (0.0, HINGE_Y, HINGE_X - HALF))
    half = max(6, (GAME_AROUND if GAME else (AROUND_LO if low else AROUND)) // 4)
    around = half * 2
    split = max(2, round(half * 0.3))
    n = GAME_JAW if GAME else (9 if low else 44)
    grid = []
    centre = []
    xs = [JAW_TIP + (HINGE_X - JAW_TIP) * (i / n) ** 1.35 for i in range(1, n + 1)]
    for xm in xs:
        floor = jaw_floor(xm)
        angles = columns(xm, half, split, floor, 0.0)
        row = []
        for c in range(around):
            h = c if c <= half else around - c
            angle = angles[h] if c <= half else -angles[h]
            inside = min(1.0, max(0.0, (split - h) / (4.0 * cols())))
            lips = max(0.0, 1.0 - abs(h - split) / (3.0 * cols())) * (1.0 - smooth(0.0, 0.4, wall(xm)))
            if xm > CORNER:
                inside = 1.0 if h < split else 0.0
            row.append(m.add(jaw_point(xm, angle, h <= split), inside, lips))
        grid.append(row)
        centre.append(0.5 * (floor + m.verts[row[half]].y))
    for r in range(len(grid) - 1):
        for c in range(around):
            n2 = (c + 1) % around
            hs = [q if q <= half else around - q for q in (c, n2)]
            quad = (grid[r][c], grid[r][n2], grid[r + 1][n2], grid[r + 1][c])
            if max(hs) <= split:
                m.face(quad, Y, "jaw floor")
                continue
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((middle.x, middle.y - 0.5 * (centre[r] + centre[r + 1]), 0.0)), "jaw")
    tip = m.add(Vector((0.0, lip(JAW_TIP) - GAP, JAW_TIP - HALF)), 0.0, 1.0)
    for c in range(around):
        m.face((tip, grid[0][c], grid[0][(c + 1) % around]), Vector((0.0, -0.3, -1.0)), "jaw")


def cone(m, base, tip, radius, name, sides=8, rows=3, blunt=0.0):
    """A tooth, a claw: round at `base` (left open: bury it), coming to `tip`."""
    axis = (tip - base)
    way = axis.normalized()
    a = way.orthogonal().normalized()
    b = way.cross(a)
    last = None
    for r in range(rows):
        t = r / rows
        ring = []
        for s in range(sides):
            ang = s / sides * TAU
            wide = radius * ((1.0 - t) ** 0.8 * (1.0 - blunt) + blunt * math.sqrt(max(0.0, 1.0 - t * t)))
            ring.append(m.add(base + axis * t + (a * math.cos(ang) + b * math.sin(ang)) * wide, 0.0, t))
        if last:
            for s in range(sides):
                n = (s + 1) % sides
                middle = (m.verts[last[s]] + m.verts[ring[n]]) * 0.5
                m.face((last[s], last[n], ring[n], ring[s]), middle - (base + axis * (t - 0.5 / rows)) + way * radius * 0.1, name)
        last = ring
    end = m.add(tip, 0.0, 1.0)
    for s in range(sides):
        n = (s + 1) % sides
        middle = (m.verts[last[s]] + m.verts[last[n]]) * 0.5
        m.face((last[s], last[n], end), middle - (base + axis * (1.0 - 1.0 / rows)) + way * radius * 0.3, name)


def blob(m, centre, ax, ay, az, name, around=14, rows=8, along=None):
    """A closed rounded lump: `ax`, `ay` and `az` are its three half-axes. `along(p)` gives each point how far
    along its limb it is."""
    def point(p):
        return m.add(p, 0.0, along(p) if along else 0.0)
    north = point(centre + az)
    south = point(centre - az)
    grid = []
    for r in range(1, rows):
        lat = math.pi * r / rows
        row = []
        for s in range(around):
            lon = s / around * TAU
            row.append(point(centre + az * math.cos(lat) + (ax * math.cos(lon) + ay * math.sin(lon)) * math.sin(lat)))
        grid.append(row)

    def out(points):
        middle = sum((m.verts[q] for q in points), Vector()) / len(points) - centre
        # (the way an ellipsoid faces there)
        return Vector([sum(middle.dot(axis) / axis.length_squared * axis[k] / axis.length_squared for axis in (ax, ay, az)) for k in range(3)])

    for s in range(around):
        n = (s + 1) % around
        m.face((north, grid[0][s], grid[0][n]), out((north, grid[0][s], grid[0][n])), name)
        m.face((south, grid[-1][s], grid[-1][n]), out((south, grid[-1][s], grid[-1][n])), name)
        for r in range(len(grid) - 1):
            quad = (grid[r][s], grid[r][n], grid[r + 1][n], grid[r + 1][s])
            m.face(quad, out(quad), name)


def blade(m, name, point, place, facing, thick, nt, nu, edge=0.0, tip=0.0):
    """A flipper: a closed blade. `point(t, u)` is a place in its own flat (t 0 at its root to 1 at its tip,
    u 0 at its leading edge to 1 at its trailing edge), `place` puts that in the model, `facing` is the way
    one of its two skins faces. It is `thick` at its root (left open: bury it), a foil across (thickest a
    third of the way back, `edge` of that at its edges), thinning to `tip` of that at its tip. The two skins
    share their points round the edges."""
    grids = []
    for side in (1.0, -1.0):
        grid = []
        for ti in range(nt + 1):
            t = ti / nt
            row = []
            for ui in range(nu + 1):
                u = ui / nu
                foil = edge + (1.0 - edge) * 2.6 * math.sqrt(u) * (1.0 - u)
                if edge > 0.0:
                    foil *= math.sqrt(max(0.0, 1.0 - (2.0 * u - 1.0) ** 6))
                swell = thick * (tip + (1.0 - tip) * (1.0 - t) ** 0.7) * foil * math.sqrt(max(0.0, 1.0 - t ** 10))
                if side < 0.0 and swell < 1e-9:
                    row.append(grids[0][ti][ui])
                else:
                    row.append(m.add(place(point(t, u)) + facing * (side * swell * 0.5), 0.0, t))
            grid.append(row)
        grids.append(grid)
        for ti in range(nt):
            for ui in range(nu):
                a, b, c, d = grid[ti][ui], grid[ti][ui + 1], grid[ti + 1][ui + 1], grid[ti + 1][ui]
                # (at the tip's two corners three of a face's points lie in the flipper's flat: cut it so
                # that neither half lies wholly in the flat, where the two skins would share it)
                if ti == nt - 1 and ui == 0:
                    m.face((a, b, d), facing * side, name)
                    m.face((b, c, d), facing * side, name)
                elif ti == nt - 1 and ui == nu - 1:
                    m.face((a, b, c), facing * side, name)
                    m.face((a, c, d), facing * side, name)
                else:
                    m.face((a, b, c, d), facing * side, name)


def whisker(m, root, way, length, bend, thick, low, name="whiskers"):
    """A whisker: a three-sided hair from `root` (left open: bury it) `way`, curving towards `bend`."""
    steps = GAME_WHISKER if GAME else (2 if low else 6)
    last = None
    here = Vector(root)
    a = way.orthogonal().normalized()
    for k in range(steps + 1):
        t = k / steps
        at = root + way * (length * t) + bend * (length * t * t)
        ahead = (way + bend * (2.0 * t)).normalized()
        # (the same way round all the way along: each ring's first point follows the last ring's)
        a = (a - ahead * a.dot(ahead)).normalized()
        b = ahead.cross(a)
        if k == steps:
            end = m.add(at, 0.0, 1.0)
            for s in range(3):
                n = (s + 1) % 3
                middle = (m.verts[last[s]] + m.verts[last[n]]) * 0.5
                m.face((last[s], last[n], end), middle - here, name)
            break
        ring = [m.add(at + (a * math.cos(s / 3 * TAU) + b * math.sin(s / 3 * TAU)) * thick * (1.0 - 0.75 * t), 0.0, t) for s in range(3)]
        if last:
            for s in range(3):
                n = (s + 1) % 3
                middle = (m.verts[last[s]] + m.verts[last[n]] + m.verts[ring[s]] + m.verts[ring[n]]) * 0.25
                m.face((last[s], last[n], ring[n], ring[s]), middle - (here + at) * 0.5, name)
        last = ring
        here = at


def eye(m, sx, low):
    """A dome lying on the skin of the head."""
    m.part(EYE)
    spokes = 28 if GAME else (12 if low else 36)
    steps = 3 if GAME else (3 if low else 10)
    xe, degrees, radius, bulge = EYE_AT
    angle = math.radians(degrees)
    here = skin(xe, sx * angle)
    round_here = max(0.015, Vector((here.x, here.y - outline(xe)[1])).length)

    def on_skin(dx, dy):
        return skin(xe + dx, sx * (angle - dy / round_here))

    out = out_of_skin(xe, sx * angle)
    if sx > 0.0 and not low and not GAME:
        # (the eye's place, for the shader's cartoon eye: its middle on the skin, the way it faces, the way
        # to the nose and up across it, and how far its rim lies below a flat across it)
        ahead = (-Z - out * out.dot(-Z)).normalized()
        up = out.cross(ahead) if out.cross(ahead).y > 0.0 else ahead.cross(out)
        print("EYE middle (%.4f, %.4f, %.4f) out (%.4f, %.4f, %.4f) ahead (%.4f, %.4f, %.4f) up (%.4f, %.4f, %.4f) radius %.4f sag %.5f" % (
            here.x, here.y, here.z, out.x, out.y, out.z, ahead.x, ahead.y, ahead.z, up.x, up.y, up.z, radius,
            radius * radius / (2.0 * round_here)))
    middle = m.add(here + out * (bulge + 0.0006), 0.0, 0.0)
    last = None
    for k in range(1, steps + 1):
        r = k / steps
        row = []
        for s in range(spokes):
            a = s / spokes * TAU
            p = on_skin(math.cos(a) * radius * r, math.sin(a) * radius * r)
            row.append(m.add(p + out * (bulge * (1.0 - r * r) + 0.0006 * (1.0 - r)), 0.0, r))
        for s in range(spokes):
            n = (s + 1) % spokes
            if last is None:
                m.face((middle, row[s], row[n]), out, "eyes")
            else:
                m.face((last[s], row[s], row[n], last[n]), out, "eyes")
        last = row


def lip_side(xm):
    """How far out to its side the edge of the upper lip is."""
    return abs(full_point(xm, angle_at(xm, lip(xm)))[0])


def teeth(m, low):
    """Its teeth: in the upper jaw (still) and the lower (they swing with it), hidden inside the other jaw
    while the mouth is shut. TEETH lists them: (metres behind the nose, how far out to the side as a share
    of the lip's edge there, how long, how wide at the root), each made on both sides, above and below; a
    tooth on the middle line is made once."""
    sides = 4 if GAME else (5 if low else 9)
    rows = 2 if low else 4
    for upper in (True, False):
        m.part(TOOTH, STILL if upper else JAW, (0.0, HINGE_Y, HINGE_X - HALF))
        for xm, share, length, radius in TEETH:
            if low and length < TEETH_LOW:
                continue
            if not upper:
                # (the lower ones sit a little ahead, between the upper ones, and a little further in)
                xm = xm - radius * 1.6
                share *= 0.82
                length *= 0.85
                if xm < JAW_TIP + radius * 1.2:
                    continue
            for sx in ((1.0, -1.0) if share > 0.0 else (1.0,)):
                if upper:
                    x = sx * share * lip_side(xm)
                    at = roof(xm) + palate_at(xm, share)
                    base = Vector((x, at + radius * 0.9, xm - HALF))
                    tip = Vector((x * 0.9, at - length, xm - HALF + length * 0.12))
                else:
                    grow = jaw_grow(xm)
                    x = sx * share * lip_side(xm) * JAW_WIDE * grow
                    at = lip(xm) - GAP - trough_at(xm, share) * grow
                    base = Vector((x, at - radius * 0.9, xm - HALF))
                    tip = Vector((x * 0.9, at + length, xm - HALF + length * 0.06))
                if GAME:
                    # (the game model: four-sided, and only the long ones in two rows)
                    rows = 2 if length >= TEETH_LOW else 1
                cone(m, base, tip, radius, "upper teeth" if upper else "lower teeth", sides, rows, blunt=0.35)


def tongue(m, low):
    m.part(TONGUE, JAW, (0.0, HINGE_Y, HINGE_X - HALF))
    front, back, thick = TONGUE_AT
    middle = 0.5 * (front + back)
    wide = lip_side(middle) * JAW_WIDE * 0.6
    blob(m, Vector((0.0, lip(middle) - GAP - trough_at(middle, 0.0) * 0.75, middle - HALF)),
         X * wide, Y * thick, Vector((0.0, 0.5 * (lip(front) - lip(back)), -0.5 * (back - front))), "tongue",
         10 if GAME else (8 if low else 18), 5 if GAME else (4 if low else 10))


def make(name, low):
    m = Mesh()
    body(m, low)
    jaw(m, low)
    teeth(m, low)
    tongue(m, low)
    for sx in (1.0, -1.0):
        eye(m, sx, low)
    extras(m, low)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) for p in m.verts], [], m.faces)
    # (every layer made first, then each looked up by name: making one moves the others)
    mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.new(name="UV2")
    mesh.color_attributes.new(name="Color", type="FLOAT_COLOR", domain="CORNER")
    uv = mesh.uv_layers["UVMap"].data
    uv2 = mesh.uv_layers["UV2"].data
    colour = mesh.color_attributes["Color"].data
    for poly in mesh.polygons:
        for corner, vi in enumerate(poly.vertices):
            kind, group, hinge, inside, along = m.data[vi]
            uv[poly.loop_start + corner].uv = (hinge.z / LENGTH + 0.5, 1.0 - (hinge.y / LENGTH + 0.5))
            uv2[poly.loop_start + corner].uv = (hinge.x / LENGTH + 0.5, 1.0 - group / 8.0)
            colour[poly.loop_start + corner].color = (kind / 10.0, inside, along, 1.0)
    mesh.color_attributes.active_color = mesh.color_attributes["Color"]
    mesh.color_attributes.render_color_index = mesh.color_attributes.find("Color")
    material = bpy.data.materials.get(NAME) or bpy.data.materials.new(NAME)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = COLOUR
    material.diffuse_color = COLOUR
    mesh.materials.append(material)
    for poly in mesh.polygons:
        poly.use_smooth = True
    # (a fold sharper than this is an edge: the two sides of it do not share their shading)
    mesh.set_sharp_from_angle(angle=math.radians(62.0))
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    box = [(min(p[k] for p in m.verts), max(p[k] for p in m.verts)) for k in range(3)]
    print("BUILT %s verts=%d tris=%d x %.3f..%.3f y %.3f..%.3f z %.3f..%.3f" % (
        name, len(mesh.vertices), tris, box[0][0], box[0][1], box[1][0], box[1][1], box[2][0], box[2][1]))
    winding(name, mesh, m)
    return obj


def winding(name, mesh, m):
    """Nothing inside out: the skin of the body faces away from its middle line, each skin of a flipper away
    from the flipper's own flat, a tooth away from its own middle (Blender's front is the side a face's
    normal is on)."""
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
        export_animations=False, export_vertex_color="ACTIVE", export_texcoords=True,
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
    long = LENGTH * 1.15
    views = [("left", (1, 0, 0), (0, 0, 0), long), ("right", (-1, 0, 0), (0, 0, 0), long),
             ("front", (0, 1, 0), (0, 0, 0), long * 0.6), ("back", (0, -1, 0), (0, 0, 0), long * 0.6),
             ("top", (0.001, 0, 1), (0, 0, 0), long * 1.8), ("under", (0.001, 0, -1), (0, 0, 0), long * 1.8),
             ("head", (0.8, 0.5, 0.2), (0, HALF * 0.75, 0), long * 0.35),
             ("chin", (0.5, 0.6, -0.6), (0, HALF * 0.8, 0), long * 0.3),
             ("tail", (0.7, -0.6, 0.3), (0, -HALF * 0.7, 0), long * 0.5)]
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
    global GAME
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    full = make(NAME, False)
    low = make(NAME + "_lo", True)
    GAME = True
    game = make(NAME + "_game", False)
    GAME = False
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, NAME + ".glb"))
    export_one(low, os.path.join(OUT, NAME + "_lo.glb"))
    export_one(game, os.path.join(OUT, NAME + "_game.glb"))
    low.location.x = LENGTH
    game.location.x = LENGTH * 2.0
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, NAME + ".blend"))
    low.location.x = 0.0
    game.location.x = 0.0
    game.hide_render = True
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low])


if __name__ == "__main__":
    main()
