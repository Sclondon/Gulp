"""Builds the walrus (creatures/walrus) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/walrus/tools/build_walrus.py
    blender --background --python creatures/walrus/tools/build_walrus.py -- <preview folder>   # with pictures

Writes creatures/walrus/models/walrus.glb (the full model, for close pictures), walrus_lo.glb (far off, phones)
and walrus_game.glb (the game model, at Twilight Princess weight: its triangles spent on its outline, its face,
eyes, tusks and flippers), and the editable creatures/walrus/tools/walrus.blend (this folder has a .gdignore).
Each model is one still mesh with one surface: the shader (walrus.gdshader) draws its hide and its wrinkles,
swims it, fans its hind flippers, sets the length of its tusks and opens its jaw. It prints a WINDING line for
each model (the check that nothing is inside out) and an EYE line (where the eye sits, for the shader).

A Pacific walrus (Odobenus rosmarus divergens), 3 m from the front of its whisker pad to the tips of its hind
flippers, built from the species (no picture was traced):

- THE BODY: a huge bulk, deepest (0.99 m) and widest (1.1 m) at the shoulders, a little ahead of its middle,
  tapering to narrow hips and a stub of a tail between the hind flippers. A small head on a neck as thick as the
  head is long, so that the head runs straight into the body; thick folds of hide round the neck and shoulders.
- THE HEAD: a broad, flat-fronted muzzle, the whisker pad a fat swelling on its front set with rows of short,
  stiff, pale bristles; the mouth small and under the pad; no ear flaps (an ear hole is drawn); small eyes high
  on the sides of the head. The upper head is cut away below the line of the lips (its underside is the roof of
  the mouth); the LOWER JAW is a part of its own, narrow (it sits between the tusks), which the shader swings
  down about its hinge; a few small cheek teeth and a tongue, hidden while the mouth is shut.
- THE TUSKS: the two upper canines, long, ivory, oval in section, coming down out of the upper lip at the sides
  of the mouth, a little splayed and curving a little back. The shader sets their length (`tusks`).
- THE FLIPPERS: two broad, square-ended fore flippers held back against its sides, a small claw on each digit;
  two hind flippers that point straight back, soles together, five toes each.

The numbers marked "as the shader has it" are in walrus.gdshader too: change one, change the other.
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

NAME = "walrus"
LENGTH = 3.0
COLOUR = (0.45, 0.28, 0.2, 1.0)

# The body's outline: metres behind the front of the whisker pad, the height of its back line, the height it is
# widest at, the height of its belly line (of the chin, where the mouth is), half its width.
PROFILE = [
    (0.0, 0.0, -0.045, -0.09, 0.001),
    (0.004, 0.035, -0.045, -0.118, 0.07),
    (0.012, 0.058, -0.045, -0.138, 0.118),
    (0.03, 0.078, -0.045, -0.158, 0.162),
    (0.06, 0.092, -0.045, -0.168, 0.188),
    (0.1, 0.108, -0.045, -0.174, 0.198),
    (0.15, 0.138, -0.04, -0.178, 0.2),
    (0.21, 0.175, -0.035, -0.183, 0.21),
    (0.28, 0.205, -0.032, -0.195, 0.228),
    (0.37, 0.24, -0.03, -0.225, 0.262),
    (0.49, 0.292, -0.03, -0.285, 0.322),
    (0.65, 0.368, -0.03, -0.365, 0.405),
    (0.85, 0.44, -0.03, -0.45, 0.5),
    (1.10, 0.49, -0.03, -0.50, 0.55),
    (1.40, 0.478, -0.03, -0.49, 0.532),
    (1.70, 0.43, -0.028, -0.43, 0.462),
    (2.00, 0.335, -0.02, -0.33, 0.36),
    (2.25, 0.228, -0.01, -0.218, 0.248),
    (2.42, 0.14, 0.0, -0.13, 0.158),
    (2.52, 0.09, 0.0, -0.08, 0.10),
    (2.58, 0.05, 0.0, -0.045, 0.056),
    (2.62, 0.005, 0.0, -0.005, 0.005),
]
BODY_FROM = 0.002
BODY_TO = 2.62
# (how closely the rings of points are spaced, as far back as each place)
RINGS = ((0.30, 0.0065), (1.05, 0.0125), (2.3, 0.03), (BODY_TO, 0.014))
AROUND = 84
AROUND_LO = 22
ROUND = 0.9

# The mouth. As the shader has it: the corner of the mouth and the jaw's hinge.
CORNER = 0.13
HINGE_X = 0.2
HINGE_Y = -0.118
JAW_TIP = 0.012
JAW_ROUND = 0.03
# (the lower jaw is narrow: it sits between the tusks)
JAW_WIDE = 0.6
# (how far the roof of the mouth is arched up and its floor sunk, as shares of the head above and the jaw below)
PALATE = 0.15
TROUGH = 0.3
GAP = 0.0015
OVERHANG = 0.005
# (metres behind the front, out to the side as a share of the lip's edge, how long, how wide at the root): a few
# small peg-like cheek teeth a side
TEETH = [
    (0.055, 0.42, 0.012, 0.006), (0.075, 0.44, 0.012, 0.0065), (0.095, 0.46, 0.011, 0.0065),
    (0.113, 0.47, 0.009, 0.006),
]
TEETH_LOW = 0.0115
TONGUE_AT = (0.04, 0.15, 0.012)
# (metres behind the front, degrees round from the back line, its radius, how far it bulges): small, high
EYE_AT = (0.215, 50.0, 0.017, 0.0068)
# The tusks: where each comes out of the upper lip (metres behind the front, out to the side as a share of the
# lip's edge, how far above the lip its root is buried), the way it points (out, down, back: the left one's), its
# length from its buried root to its tip at `tusks` 1, its half-thickness front to back and side to side at the
# root, how far its tip curves back (as a share of its length). As the shader has it: TUSK_WAY.
TUSK_AT = (0.068, 0.8, 0.04)
TUSK_WAY = (0.13, -1.0, 0.14)
TUSK_LONG = 0.68
TUSK_THICK = (0.03, 0.023)
TUSK_CURVE = 0.1
# The folds of hide round the neck and shoulders: (metres behind the front, how deep a share of the radius, how
# wide). As the shader has it (it darkens the creases between them).
FOLDS = [(0.40, 0.022, 0.03), (0.475, 0.03, 0.034), (0.555, 0.034, 0.036), (0.64, 0.034, 0.04),
         (0.735, 0.03, 0.042), (0.835, 0.024, 0.045), (0.95, 0.016, 0.05)]
# The game model (see GAME below): points round the body; how near (metres) its skin keeps to the full model's;
# how far apart its rings may be at most, along the body and over the mouth; rings in the lower jaw; places
# that must have a ring.
GAME_AROUND = 30
GAME_TOL = 0.0045
GAME_STEP = 0.17
GAME_MOUTH_STEP = 0.03
GAME_JAW = 10
GAME_KEEP = ()
# (and how many pieces each whisker is made of)
GAME_WHISKER = 2


def lip(xm):
    """The line of the lips: how high, `xm` behind the front (it falls a little towards the corners)."""
    return -0.104 - 0.07 * xm


def fold(xm, c):
    """How much further out the skin is at a place for the folds of the neck and shoulders (a share of the
    radius): `c` is the cosine of the angle round from the back line. The folds wander a little and are deepest
    over the back and the sides."""
    a = math.acos(max(-1.0, min(1.0, c)))
    out = 0.0
    for k, (at, deep, wide) in enumerate(FOLDS):
        shift = 0.012 * math.sin(2.0 * a + 1.7 * k)
        strength = 0.75 + 0.25 * math.sin(3.0 * a + 2.3 * k)
        out += deep * strength * math.exp(-((xm - at - shift) / wide) ** 2)
    return out * (0.55 + 0.45 * smooth(-0.9, 0.3, c))


def sculpt(xm, c):
    """How much wider the skin is at a place than the plain outline: the whisker pad."""
    pad = math.exp(-((xm - 0.045) / 0.05) ** 2) * math.exp(-((c + 0.35) / 0.55) ** 2)
    return 1.0 + 0.1 * pad


def extras(m, low):
    d = 3 if low else 1
    for sx in (1.0, -1.0):
        # The fore flippers: broad and square-ended, held back against its sides, a small claw on each digit.
        at = math.radians(122.0) * sx
        out = out_of_skin(0.86, at)
        root = skin(0.86, at) - out * 0.04
        span = (Vector((sx * 0.2, -0.45, 0.86)) + out * 0.12).normalized()
        chord = out.cross(span).normalized()
        if chord.y > 0.0:
            chord = -chord
        facing = span.cross(chord).normalized()
        if facing.dot(out) < 0.0:
            facing = -facing

        def fore_point(t, u):
            wide = 0.26 * (0.72 + 0.28 * smooth(0.0, 0.7, t)) * (1.0 - 0.12 * smooth(0.9, 1.0, t))
            # (the end is square: the trailing edge reaches as far as the leading edge)
            reach = 0.5 * (1.0 - 0.06 * (u - 0.3) ** 2)
            return (reach * t, (u - 0.4) * wide + 0.03 * t * t)

        place = lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1]
        m.part(SKIN, FORE_L if sx > 0.0 else FORE_R, root)
        blade(m, "fore flippers", fore_point, place, facing, 0.075, *((6, 6) if GAME else (20 // d, 12 // d)), edge=0.3, tip=0.35)
        m.part(CLAW, FORE_L if sx > 0.0 else FORE_R, root)
        for k in range(5):
            u = 0.1 + 0.2 * k
            base = place(fore_point(0.93, u))
            cone(m, base, base + span * 0.03 + facing * 0.006, 0.006, "claws", 4 if low or GAME else 7, 1 if low or GAME else 3)
        # The hind flippers: they point straight back, soles together, each a broad fan of five toes.
        root = Vector((sx * 0.035, 0.0, 2.5 - HALF))
        span = Vector((sx * 0.12, 0.0, 1.0)).normalized()
        facing = span.cross(Y).normalized()

        def hind_point(t, u):
            fan = math.radians(30.0) * (u * 2.0 - 1.0)
            reach = 0.565 * (1.0 - 0.2 * math.sin(math.pi * u) ** 1.5) * (0.95 + 0.05 * abs(math.cos(math.pi * u * 5.0)) ** 0.6)
            a = (0.0, (u - 0.5) * 0.12)
            b = (math.cos(fan) * reach, math.sin(fan) * reach)
            k = t ** 0.9
            return (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)

        m.part(SKIN, HIND_L if sx > 0.0 else HIND_R, root)
        blade(m, "hind flippers", hind_point, lambda p, root=root, span=span: root + span * p[0] + Y * p[1],
              facing, 0.055, *((3, 20) if GAME else (22 // d, 30 // d)), tip=0.12)
        # The whiskers: rows of short, stiff, pale bristles over the front of the pad, pointing forward and down.
        m.part(WHISKER)
        if low:
            columns_at, spread = (0.008, 0.03), (0.3, 0.75)
        elif GAME:
            columns_at, spread = (0.005, 0.016, 0.032, 0.052), (0.08, 0.36, 0.64, 0.92)
        else:
            columns_at, spread = (0.003, 0.008, 0.015, 0.024, 0.035, 0.048, 0.062), (0.04, 0.2, 0.36, 0.52, 0.68, 0.84, 1.0)
        for i, xm in enumerate(columns_at):
            # (from the lip up the pad, and from near the middle line round to the side: the pad faces forward
            # near the front, so there the roots spread across the face)
            low_at = angle_at(xm, lip(xm) + 0.012)
            high_at = angle_at(xm, outline(xm)[1] + 0.05)
            for j, share in enumerate(spread):
                at = sx * (low_at + (high_at - low_at) * share if xm > 0.02 else math.radians(168.0) - (math.radians(168.0) - high_at) * share)
                if skin(xm, at).y < lip(xm) + 0.01:
                    continue
                out = out_of_skin(xm, at)
                way = (out * 0.7 + Vector((0.0, -0.75, -0.3))).normalized()
                length = 0.042 + 0.02 * (1.0 - share) + 0.01 * math.sin(7.0 * i + 3.0 * j)
                whisker(m, skin(xm, at) - out * 0.004, way, length, Vector((0.0, -0.12, 0.04)), 0.0034, low)


def tusks(m, low):
    """The tusks: a tapering oval rod each, from inside the upper lip (left open: buried) down to a rounded tip,
    curving a little back. Every point of one carries the tusk's root as its hinge, for the shader to set its
    length."""
    xm, share, buried = TUSK_AT
    sides = 12 if GAME else (6 if low else 24)
    steps = 9 if GAME else (4 if low else 40)
    for sx in (1.0, -1.0):
        root = Vector((sx * share * lip_side(xm), lip(xm) + buried, xm - HALF))
        way = Vector((sx * TUSK_WAY[0], TUSK_WAY[1], TUSK_WAY[2])).normalized()
        back = (Z - way * way.dot(Z)).normalized()
        across = way.cross(back).normalized()
        m.part(TUSK, STILL, root)
        last = None
        for k in range(steps + 1):
            # (the rings gather towards the tip, where it rounds off)
            t = 1.0 - (1.0 - k / steps) ** 1.4
            centre = root + way * (TUSK_LONG * t) + back * (TUSK_CURVE * TUSK_LONG * t * t)
            ahead = (way + back * (2.0 * TUSK_CURVE * t)).normalized()
            b2 = (back - ahead * back.dot(ahead)).normalized()
            a2 = ahead.cross(b2).normalized()
            taper = (1.0 - 0.72 * t ** 1.6) * math.sqrt(max(0.0, 1.0 - max(0.0, (t - 0.9) / 0.1) ** 2) if t < 1.0 else 0.0)
            if k == steps:
                end = m.add(centre, 0.0, 1.0)
                for s in range(sides):
                    n = (s + 1) % sides
                    middle = (m.verts[last[s]] + m.verts[last[n]]) * 0.5
                    m.face((last[s], last[n], end), middle - centre + ahead * 0.002, "tusks")
                break
            ring = []
            for s in range(sides):
                ang = s / sides * TAU
                p = centre + (b2 * (math.cos(ang) * TUSK_THICK[0]) + a2 * (math.sin(ang) * TUSK_THICK[1])) * taper
                ring.append(m.add(p, 0.0, t))
            if last:
                for s in range(sides):
                    n = (s + 1) % sides
                    middle = (m.verts[last[s]] + m.verts[last[n]] + m.verts[ring[s]] + m.verts[ring[n]]) * 0.25
                    m.face((last[s], last[n], ring[n], ring[s]), middle - (here + centre) * 0.5, "tusks")
            last = ring
            here = centre


# ======================================================================================================
# From here down the code is GameCommon's sea mammals' (harbor seal, sea lion, sea otter), with three changes
# for the walrus: `full_point` adds the folds of the neck (`fold`) all round the body, not only to its width;
# the roof of the mouth is coloured as the inside of the mouth only over the lower jaw (the walrus's pad hangs
# out past its narrow jaw); and the tusks (TUSK, above).
#
# Everything is in Godot space (metres, Y up, +X its right side, its nose at -Z) until it is written out;
# the origin is on its middle line, half way along. `xm` is metres behind the front of its muzzle.
#
# What a point is, for the shader:
#   vertex colour red   what it is made of, as a tenth (0 hide, 0.1 an eye, 0.2 a tooth, 0.3 the tongue,
#                       0.4 a whisker, 0.5 bare hide, 0.6 a claw, 0.7 a tusk)
#   vertex colour green how far inside the mouth it is (0 outside, 0.5 the lip's edge, 1 inside)
#   vertex colour blue  on a flipper, a tusk or a whisker: how far along it, 0 its root to 1 its tip; on an
#                       eye, 0 its middle to 1 its rim; on the skin of the head and jaw, how much it is the
#                       lips' edge
#   UV2.y               what moves it, as an eighth (0 nothing, 1 the lower jaw, 2 and 3 the right and left
#                       fore limbs, 4 and 5 the right and left hind limbs)
#   UV.x, UV.y, UV2.x   its hinge: where the jaw or the limb it belongs to turns (for a tusk: its root), as z,
#                       y and x in body lengths plus a half (so always between 0 and 1)
# (The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.)

HALF = LENGTH * 0.5
TAU = math.tau
SKIN, EYE, TOOTH, TONGUE, WHISKER, HIDE, CLAW, TUSK = range(8)
STILL, JAW, FORE_L, FORE_R, HIND_L, HIND_R = range(6)
X = Vector((1.0, 0.0, 0.0))
Y = Vector((0.0, 1.0, 0.0))
Z = Vector((0.0, 0.0, 1.0))

# The game model (the user, 2026-11-18: "We should have a twilight princess model to compare to so we can make
# low poly versions while maintaining high quality looks and silhouettes"): the same parts from the same curves,
# its rings of points where the outline bends (the muzzle, the mouth, round the eye, the folds, the hips) and few
# along the smooth flanks, a round eye, simpler teeth and tusks, whiskers in two pieces, flippers with their
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
    back line (0) by its right side (a quarter turn) to the belly line (half a turn)."""
    top, mid, bot, wide = outline(xm)
    c = math.cos(angle)
    s = math.sin(angle)
    y = mid + c * ((top - mid) if c >= 0.0 else (mid - bot))
    side = math.copysign(abs(s) ** ROUND, s) * wide
    swell = 1.0 + fold(xm, c)
    return side * sculpt(xm, c) * swell, mid + (y - mid) * swell


def angle_at(xm, y):
    """The angle at which the skin is `y` high (the folds left out)."""
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
    """The skin from the front of the muzzle to the end of the body, the upper head cut away below the line
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
                    # (only over the narrow lower jaw: out past it the pad's underside is hide)
                    inside = min(1.0, max(0.0, (h - split) / (4.0 * cols()))) * min(1.0, max(0.0, (JAW_WIDE * 0.95 - abs(side) / edge) / 0.12))
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
    # the front of the muzzle and the end of the body: a fan each
    first = m.verts[grid[0][0]]
    last = m.verts[grid[-1][0]]
    for row, at, way in ((grid[0], Vector((0.0, centre[0], first.z - 0.002)), -1.0),
                         (grid[-1], Vector((0.0, centre[-1], last.z + 0.002)), 1.0)):
        tip = m.add(at)
        for c in range(around):
            m.face((tip, row[c], row[(c + 1) % around]), Vector((0.0, 0.0, way)), "body")


def jaw_point(xm, angle, clamp):
    """A point of the lower jaw: the skin as if it had no mouth, cut away above the mouth's floor, narrower
    than the upper lip, rounded off to the chin at its tip."""
    floor = jaw_floor(xm)
    grow = jaw_grow(xm)
    narrow = JAW_WIDE + (1.0 - JAW_WIDE) * smooth(CORNER - 0.3 * (HINGE_X - CORNER), CORNER + 0.4 * (HINGE_X - CORNER), xm)
    side, y = full_point(xm, angle)
    if clamp:
        # (the floor of the mouth is never wider than the lip's edge, and widens steadily out to it: near the
        # hinge, where the floor has fallen below the widest of the throat, it would stand out past its sides)
        rim = abs(full_point(xm, angle_at(xm, floor))[0])
        share = min(1.0, abs(angle) / max(angle_at(xm, floor), 1e-6))
        side = math.copysign(min(abs(side), rim * math.sin(0.5 * math.pi * share)), side)
        y = floor - trough_at(xm, abs(side) / max(rim, 1e-6))
    y = floor - (floor - min(y, floor)) * grow
    # (behind the corner of the mouth it tucks a little inside the throat's skin, so that no edge of it shows)
    tuck = 1.0 - 0.05 * smooth(CORNER, HINGE_X, xm)
    return Vector((side * narrow * grow * tuck, floor - (floor - y) * tuck, xm - HALF))


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
    # (the game model's last ring stops just short of the hinge, where the floor of its mouth has fallen to the
    # throat: with its few columns a face there would fold over)
    end = HINGE_X - (0.008 if GAME else 0.0)
    xs = [JAW_TIP + (end - JAW_TIP) * (i / n) ** 1.35 for i in range(1, n + 1)]
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
    steps = GAME_WHISKER if GAME else (2 if low else 5)
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
        ring = [m.add(at + (a * math.cos(s / 3 * TAU) + b * math.sin(s / 3 * TAU)) * thick * (1.0 - 0.45 * t), 0.0, t) for s in range(3)]
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
    while the mouth is shut. TEETH lists them: (metres behind the front, how far out to the side as a share
    of the lip's edge there, how long, how wide at the root), each made on both sides, above and below."""
    sides = 4 if GAME else (5 if low else 9)
    rows = 2 if low else 4
    for upper in (True, False):
        m.part(TOOTH, STILL if upper else JAW, (0.0, HINGE_Y, HINGE_X - HALF))
        for xm, share, length, radius in TEETH:
            if low and length < TEETH_LOW:
                continue
            if not upper:
                # (the lower ones sit a little ahead, between the upper ones)
                xm = xm - radius * 1.6
                length *= 0.85
                if xm < JAW_TIP + radius * 1.2:
                    continue
            for sx in ((1.0, -1.0) if share > 0.0 else (1.0,)):
                if upper:
                    x = sx * share * lip_side(xm)
                    at = roof(xm) + palate_at(xm, share)
                    base = Vector((x, at + radius * 0.9, xm - HALF))
                    tip = Vector((x * 0.95, at - length, xm - HALF + length * 0.12))
                else:
                    grow = jaw_grow(xm)
                    x = sx * share * lip_side(xm) * grow
                    at = lip(xm) - GAP - trough_at(xm, share / JAW_WIDE) * grow
                    base = Vector((x, at - radius * 0.9, xm - HALF))
                    tip = Vector((x * 0.95, at + length, xm - HALF + length * 0.06))
                if GAME:
                    rows = 1
                cone(m, base, tip, radius, "upper teeth" if upper else "lower teeth", sides, rows, blunt=0.6)


def tongue(m, low):
    m.part(TONGUE, JAW, (0.0, HINGE_Y, HINGE_X - HALF))
    front, back, thick = TONGUE_AT
    middle = 0.5 * (front + back)
    wide = lip_side(middle) * JAW_WIDE * 0.55
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
    tusks(m, low)
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
    from the flipper's own flat, a tooth or a tusk away from its own middle (Blender's front is the side a
    face's normal is on)."""
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
             ("top", (0.001, 0, 1), (0, 0, 0), long * 1.1), ("under", (0.001, 0, -1), (0, 0, 0), long * 1.1),
             ("head", (0.8, 0.5, 0.2), (0, HALF * 0.85, -0.1), long * 0.3),
             ("chin", (0.5, 0.6, -0.6), (0, HALF * 0.9, -0.15), long * 0.25),
             ("tail", (0.7, -0.6, 0.3), (0, -HALF * 0.7, 0), long * 0.5)]
    for prefix, obj in zip(("", "lo_", "game_"), made):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if prefix == "lo_" and view not in ("left", "head"):
                continue
            offset = Vector(direction).normalized() * 40.0
            camera.data.ortho_scale = frame
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % (prefix, view))
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
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low, game])


if __name__ == "__main__":
    main()
