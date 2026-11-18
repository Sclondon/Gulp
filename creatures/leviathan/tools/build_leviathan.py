"""Builds the leviathan (creatures/leviathan) and exports it for Godot.

Run from the game's root (or from anywhere: paths are taken from this file's own folder):
    blender --background --python creatures/leviathan/tools/build_leviathan.py
    blender --background --python creatures/leviathan/tools/build_leviathan.py -- <preview folder>   # with pictures

Writes creatures/leviathan/models/leviathan.glb (the full model, for close pictures), leviathan_game.glb (the game
model: Twilight Princess boss weight, its triangles spent on the head, the jaw, the teeth, the eye and the ragged
edges of the fins, big triangles over the flat armoured flanks) and leviathan_lo.glb (far off), and the editable
creatures/leviathan/tools/leviathan.blend (this folder has a .gdignore). Each model is one still mesh with one
surface: the shared shader (creatures/sea_monster/sea_monster.gdshader) draws every marking, swims it, opens its
mouth, sways its ropes. It prints a WINDING line for each model (the check that nothing is inside out) and an
EYE_FRAME line (where the eye sits, for the shader's cartoon eye: copy it into leviathan.gd).

An original sea monster, 40 m from the tip of its snout to the tip of its tail fin: an immense armoured
serpent-whale, built to the concept picture Gulp's session made for it (tools/art_src/concept_monsters.jpg, top
left), nothing traced:

- THE HEAD: a third of its length, deep and long, a blunt overhanging snout; a huge lower jaw; a small pale eye
  high over the corner of the mouth; armoured plates and gill ridges drawn by the shader.
- THE BODY: deepest just behind the head, then a long tapering tail ending in a tall ragged tail fin; a row of
  serrated fringe along the top and the bottom of the tail; a tattered sail of a dorsal fin.
- THE MOUTH: the upper head is closed underneath by the roof of the mouth; the LOWER JAW is its own closed part,
  which the shader swings down about the corner of the mouth, very wide (60 degrees: it swallows things), the skull
  lifting too. Big conical teeth: the upper ones overlap outside the lower jaw (they show with the mouth shut), the
  lower ones stand inside the upper jaw, between them (they interlock).
- THE FINS: tattered (ragged trailing edges): two great pectorals, two small pelvics, the dorsal, the tail fin.
- WHAT IT CARRIES: clusters of barnacles on its back and head, three old harpoons stuck in its back (one with its
  barbed iron showing) with ropes trailing from them.

Everything here is in Godot space (metres, Y up, its nose at -Z) until it is written out; the origin is on its
middle line, half way along (20 m behind the tip of its snout). `xm` below is metres behind that tip.

What a point is, for the shader (the parts are the same for every creature that wears sea_monster.gdshader): UV2.y
the part (0 body, 1 lower jaw, 2 an upper tooth, 3 a lower tooth, 4 a fin, 5 weed, 6 a pectoral fin, 7 an eye, 8 a
barnacle, 9 a harpoon, 10 a rope). UV2.x: on the body and the jaw, how much the point is inside the mouth (0 skin, 1
the roof or the floor of the mouth); on a harpoon, 1 on its iron. UV, on the body and jaw: x how far along (0 the tip
to 1 the tail), y how high on its side (1 the ridge of the back, 0 the keel of the belly); on a fin: x root (0) to tip
(1), y leading (0) to trailing edge (1); on an eye: x middle (0) to rim (1); on a rope or weed: x from where it is tied
(0) to its free end (1). (The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.)

The numbers marked "as the shader has it" are sent to the shader by leviathan.gd: change one, change the other.
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

NAME = "leviathan"
LENGTH = 40.0
HALF = 20.0
BODY, JAW, TOOTH_UP, TOOTH_LOW, FIN, WEED, PECTORAL, EYE, BARNACLE, HARPOON, ROPE = range(11)
TAU = math.tau
PI = math.pi

# The whole outline, lower jaw and all: metres behind the tip, the height of the ridge of its back, the height
# of the keel of its belly, half its width.
PROFILE = [
    (0.0, -0.25, -0.85, 0.35),
    (0.3, 0.15, -1.50, 0.85),
    (1.0, 0.55, -2.20, 1.35),
    (2.2, 1.00, -2.85, 1.85),
    (3.8, 1.50, -3.40, 2.30),
    (5.8, 2.05, -3.85, 2.70),
    (7.8, 2.62, -4.15, 3.00),
    (9.6, 3.20, -4.30, 3.15),
    (11.4, 4.05, -4.60, 3.35),
    (14.0, 5.10, -5.10, 3.55),
    (17.0, 5.30, -5.00, 3.45),
    (20.5, 4.80, -4.30, 3.05),
    (24.5, 3.80, -3.20, 2.40),
    (28.5, 2.80, -2.35, 1.85),
    (32.0, 2.00, -1.65, 1.30),
    (35.0, 1.40, -1.10, 0.85),
    (37.0, 0.90, -0.70, 0.48),
    (38.3, 0.50, -0.38, 0.20),
    (38.8, 0.25, -0.18, 0.06),
]
BODY_FROM = 0.0
BODY_TO = 38.8
# (the snout overhangs the lower jaw: the lower jaw starts here)
JAW_FROM = 0.55

# As the shader has it: the corner of the mouth (where the lower jaw hinges), how far behind it the jaw's bend is
# spread, the eye (metres behind the tip, metres up) and its radius; where the tail fin is hinged.
CORNER = 10.2
WALL = 1.3
EYE_AT = (7.0, 1.2)
EYE_RADIUS = 0.36
JOINT = 37.2
# The lips' gap, how far the roof of the mouth is arched (of half its width), how far behind the corner of the
# mouth the jaw runs on inside the body.
GAP = 0.02
VAULT = 0.3
JAW_TAIL = 1.2
# The teeth along the lips: how many each side of each jaw, from where to where, how thick, how long; the upper
# ones stand this far out from the lip (over the outside of the lower jaw), the lower ones this far in.
TEETH = 10
TEETH_FROM = 0.75
TEETH_TO = 9.2
TOOTH_RADIUS = 0.3
TOOTH_LONG = 1.05
TOOTH_IN = 0.3


def mouth_y(xm):
    """The line of the mouth, as the shader has it: falling back along the head, below its middle."""
    return -0.42 - 0.105 * xm


def to_b(p):
    return Vector((p.x, -p.z, p.y))


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def hash1(i):
    """A steady pseudo-random number in 0..1 for a whole number."""
    x = math.sin(i * 127.1 + 311.7) * 43758.5453
    return x - math.floor(x)


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
    # The armour: overlapping bands round the trunk and the tail, each swelling at its front edge and sloping in
    # to the groove before the next (so the outline is stepped, as the concept's plated body).
    swell = PLATE_SWELL * plate_bump(xm)
    if swell > 0.0:
        yc = 0.5 * (out[0] + out[1])
        out[0] = yc + (out[0] - yc) * (1.0 + swell)
        out[1] = yc + (out[1] - yc) * (1.0 + swell)
        out[2] *= 1.0 + swell
    return out


# As the shader has it: where the armour bands begin, how long the first is, how much shorter they grow towards
# the tail (see plate_phase), how far a band swells (of the body's size), and where they end.
PLATE_FROM = 11.6
PLATE_LONG = 2.6
PLATE_GROW = 0.3
PLATE_SWELL = 0.04
PLATE_TO = 36.0


def plate_phase(xm):
    """How many armour bands from PLATE_FROM to `xm` (a band begins at each whole number)."""
    d = (xm - PLATE_FROM) / PLATE_LONG
    return d * (1.0 + PLATE_GROW * d / 10.0)


def plate_bump(xm):
    if xm <= PLATE_FROM or xm >= PLATE_TO:
        return 0.0
    f = plate_phase(xm)
    fr = f - math.floor(f)
    fade = smooth(PLATE_FROM, PLATE_FROM + 0.8, xm) * (1.0 - smooth(PLATE_TO - 3.0, PLATE_TO, xm))
    return fade * smooth(0.0, 0.14, fr) * (1.0 - 0.75 * fr)


def top(xm):
    return outline(xm)[0]


def bottom(xm):
    return outline(xm)[1]


def _shape(xm):
    """The exponents of the section: (sides, top and bottom): under 1 fuller, boxier (the armoured trunk), over
    1 to an edge (the tail stock)."""
    px = 0.78 + 0.7 * smooth(28.0, 37.0, xm)
    py = 0.9 - 0.1 * (1.0 - smooth(0.5, 4.0, xm))
    return px, py


def section(xm, angle):
    """(x, y) of the skin: `angle` round the body from the ridge of the back (0) by one side (a quarter turn) to
    the keel of the belly (half a turn)."""
    up, down, wide = outline(xm)
    yc = 0.5 * (up + down)
    c = math.cos(angle)
    s = math.sin(angle)
    px, py = _shape(xm)
    y = yc + math.copysign(abs(c) ** py, c) * (up - yc if c >= 0.0 else yc - down)
    x = math.copysign(abs(s) ** px, s) * wide
    return x, y


def angle_at(xm, level):
    """The angle round the body at which its skin is at the height `level`."""
    up, down, _ = outline(xm)
    if level >= up:
        return 0.0
    if level <= down:
        return PI
    yc = 0.5 * (up + down)
    c = (level - yc) / (up - yc if level >= yc else yc - down)
    c = max(-1.0, min(1.0, c))
    _, py = _shape(xm)
    c = math.copysign(abs(c) ** (1.0 / py), c)
    return math.acos(c)


def sculpt(xm, x, y):
    return Vector((x, y, xm - HALF))


def clip_y(xm):
    """Under this the body's skin is cut away for the mouth: the line of the mouth as far as its corner, then a
    wall falling to the belly (the back of the mouth, the throat)."""
    if xm <= CORNER:
        return mouth_y(xm)
    return mouth_y(CORNER) + (bottom(xm) - 0.03 - mouth_y(CORNER)) * smooth(CORNER, CORNER + WALL, xm)


def high_of(xm, y):
    up, down, _ = outline(xm)
    return max(0.0, min(1.0, (y - down) / (up - down)))


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.data = []
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
    """For the game model: the fewest of the stations `xs` such that between two kept ones a straight line through
    `values` stays within `tol` (metres) of `values` at every station left out, and no two kept ones are more than
    `longest(x)` apart; the stations in `keep` are always kept. So rings gather where the outline curves and stand
    far apart down the flat flanks."""
    vals = [values(x) for x in xs]
    fixed = {i for i, x in enumerate(xs) if any(abs(x - k) < 1e-9 for k in keep)}
    kept = [0]
    i = 0
    while i < len(xs) - 1:
        j = i + 1
        while j + 1 < len(xs) and j not in fixed:
            c = j + 1
            reach = longest(xs[i])
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


# The game model: how far its rings may stray from the outline (metres), the longest step between rings (short at
# the head, longer down the trunk, shorter again down the tail, which bends most), columns down each side to the lip
# and across the roof of the mouth.
GAME_TOL = 0.04
GAME_K = 10
GAME_R = 2


def game_longest(xm):
    if xm < CORNER + 1.0:
        return 1.3
    if xm < 24.0:
        return 2.6
    return 1.6


def game_angle(j, k, lip):
    """The angle round the body of column `j` of the game model's body: gathered towards the ridge of the back,
    the widest of the side and the lip, where the outline is seen, and spread over the flanks."""
    s = j / k

    def gather(t):
        return t - 0.35 * math.sin(TAU * t) / TAU

    return lip * (0.5 * gather(2.0 * s) if s <= 0.5 else 0.5 + 0.5 * gather(2.0 * s - 1.0))


def band_x(f):
    """Where the armour's phase reaches `f` (the inverse of plate_phase)."""
    g = PLATE_GROW / 10.0
    d = (-1.0 + math.sqrt(1.0 + 4.0 * g * f)) / (2.0 * g)
    return PLATE_FROM + d * PLATE_LONG


def band_marks(shares):
    """The places along the armour at these shares of each band (0 its groove, 0.14 the crest of its front)."""
    xs = []
    f = 0
    while True:
        for s in shares:
            x = band_x(f + s)
            if PLATE_FROM < x < PLATE_TO:
                xs.append(x)
        if band_x(f) > PLATE_TO:
            return xs
        f += 1


def rings(lod):
    if lod == "game":
        return pick(rings("full"), lambda xm: (*outline(xm), clip_y(xm)), GAME_TOL, game_longest,
                    keep=(CORNER, CORNER + WALL, *band_marks((0.0, 0.14))))
    xs = []
    x = BODY_FROM
    trunk = (PLATE_FROM + 0.8, PLATE_TO - 0.5)
    for until, step in ((1.2, 0.12), (CORNER + WALL + 0.4, 0.46), (30.0, 0.36), (BODY_TO, 0.36)):
        if lod == "low":
            step *= 3.2
        n = max(1, round((until - x) / step))
        for i in range(n):
            here = x + (until - x) * i / n
            if lod == "low" and trunk[0] < here < trunk[1]:
                continue
            xs.append(here)
        x = until
    xs.append(BODY_TO)
    musts = [CORNER, CORNER + 0.35 * WALL, CORNER + 0.7 * WALL, CORNER + 0.88 * WALL, CORNER + WALL]
    if lod == "low":
        musts += [b for b in band_marks((0.0, 0.14, 0.6)) if trunk[0] < b < trunk[1]]
    else:
        musts += band_marks((0.0, 0.07, 0.14))
    for must in musts:
        xs = [x for x in xs if abs(x - must) > 0.08 or x == must]
        if not any(abs(x - must) < 1e-9 for x in xs):
            xs.append(must)
    xs.sort()
    return xs



def loft(m, rows, flat_from, flat_to, flat_out, name, flat_name):
    """Joins rings of points into a skin. Each row is (list of point numbers, the row's middle); the faces between
    columns `flat_from` and `flat_to` are the flat of the mouth and face `flat_out`, the others face away from the
    row's middle."""
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


def body(m, lod):
    """The body's skin, with the roof of the mouth: columns 0 (the ridge of the back) to K (the lip) down each
    side, then R more across the roof to its middle."""
    k, r = {"full": (18, 4), "low": (8, 2), "game": (GAME_K, GAME_R)}[lod]
    rows = []
    xs = rings(lod)
    for xm in xs:
        up, down, _ = outline(xm)
        level = clip_y(xm)
        lip = angle_at(xm, level)
        half = []
        for j in range(k + 1):
            x, y = section(xm, game_angle(j, k, lip))
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
    loft(m, rows, k, k + 2 * r, Vector((0.0, -1.0, 0.0)), "body", "roof of the mouth")
    first = xs[0]
    cap(m, BODY, rows[0][0], Vector((0.0, 0.5 * (top(first) + mouth_y(first)), first - 0.01 - HALF)), 0.0, -1.0, "body")
    last = xs[-1]
    cap(m, BODY, rows[-1][0], Vector((0.0, 0.5 * (top(last) + bottom(last)), last + 0.01 - HALF)), 0.0, 1.0, "body")


def jaw(m, lod):
    """The lower jaw: columns 0 (the middle of the floor of the mouth) to R (the lip), then K more down the outside
    to the keel of the chin."""
    k, r, count = {"full": (14, 4, 44), "low": (5, 2, 12), "game": (8, 2, 20)}[lod]
    rows = []
    to = CORNER + JAW_TAIL
    for i in range(count + 1):
        xm = JAW_FROM + (to - JAW_FROM) * (i / count) ** 1.1
        up, down, _ = outline(xm)
        level = mouth_y(min(xm, CORNER)) - GAP
        lip = angle_at(xm, level)
        lx, ly = section(xm, lip)
        # (behind the corner of the mouth it runs on inside the body, a little smaller than the skin over it)
        shrink = 1.0 - (0.012 + 0.05 * smooth(CORNER, to, xm)) * (1.0 if xm > CORNER else 0.0)
        # (and its chin is a little narrower than the snout over it: the upper teeth close outside it)
        narrow = 0.97
        half = []
        for j in range(r):
            half.append((Vector((lx * narrow * j / r, ly, xm - HALF)), 1.0))
        for j in range(k + 1):
            x, y = section(xm, lip + (PI - lip) * j / k)
            half.append((Vector((x * narrow, y, xm - HALF)), 0.0))
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
    flat = []
    for row, middle in rows:
        flat.append((row[around - r:] + row[:around - r], middle))
    loft(m, flat, 0, 2 * r, Vector((0.0, 1.0, 0.0)), "jaw", "floor of the mouth")
    cap(m, JAW, rows[0][0], Vector((0.0, 0.5 * (mouth_y(JAW_FROM) - GAP + bottom(JAW_FROM)), JAW_FROM - 0.01 - HALF)), 0.0, -1.0, "jaw")
    cap(m, JAW, rows[-1][0], Vector((0.0, 0.5 * (mouth_y(CORNER) + bottom(to)), to + 0.01 - HALF)), 0.0, 1.0, "jaw")


def cone(m, part, base, axis, radius, long, sides, levels, name, extra=0.0, hook=0.0):
    """A cone standing on `base` along `axis` (a tooth), bent back by `hook` (metres, towards +Z) at its tip."""
    side = axis.cross(Vector((0.0, 0.0, 1.0)))
    if side.length < 1e-6:
        side = axis.cross(Vector((1.0, 0.0, 0.0)))
    side.normalize()
    other = axis.cross(side).normalized()
    last = None
    for share, thick in levels:
        centre = base + axis * (long * share) + Vector((0.0, 0.0, hook * share * share))
        row = []
        for s in range(sides):
            a = s / sides * TAU
            p = centre + (side * math.cos(a) + other * math.sin(a)) * (radius * thick)
            row.append(m.add(p, (share, 0.0), part, extra))
        if last is not None:
            for s in range(sides):
                n = (s + 1) % sides
                at = (m.verts[row[s]] + m.verts[row[n]]) * 0.5 - centre
                m.face((last[s], last[n], row[n], row[s]), at, name)
        last = row
    tip_at = base + axis * long + Vector((0.0, 0.0, hook))
    tip = m.add(tip_at, (1.0, 0.0), part, extra)
    for s in range(sides):
        n = (s + 1) % sides
        at = (m.verts[last[s]] + m.verts[last[n]]) * 0.5 - (base + axis * (long * 0.6))
        m.face((last[s], last[n], tip), at, name)


def teeth(m, lod):
    count = {"full": TEETH, "low": 7, "game": 9}[lod]
    sides = 6 if lod == "full" else 4
    levels = [(0.0, 1.0), (0.45, 0.72)] if lod == "full" else [(0.0, 1.0)]
    pitch = (TEETH_TO - TEETH_FROM) / count
    for i in range(count):
        f = i / max(1, count - 1)
        # (a great fang third from the front, big along the middle of the jaw, smaller at the back)
        size = 0.75 + 0.35 * math.exp(-((f - 0.18) / 0.1) ** 2) + 0.25 * smooth(0.0, 0.4, f) - 0.45 * smooth(0.65, 1.0, f)
        for sx in (1.0, -1.0):
            # the upper jaw's: rooted in the lip, hanging down and a little out, over the outside of the
            # lower jaw (they show with the mouth shut)
            xm = TEETH_FROM + pitch * (i + 0.25)
            lx, ly = section(xm, angle_at(xm, mouth_y(xm)))
            base = Vector((sx * (lx - TOOTH_RADIUS * size * 0.6), ly + TOOTH_LONG * 0.25 * size, xm - HALF))
            cone(m, TOOTH_UP, base, Vector((sx * 0.22, -1.0, 0.08)).normalized(), TOOTH_RADIUS * size,
                 TOOTH_LONG * size * 1.35, sides, levels, "upper teeth", hook=0.12 * size)
            # the lower jaw's: standing on the floor of the mouth just in from the lip, between the upper ones
            # (inside the upper jaw with the mouth shut)
            xm = TEETH_FROM + pitch * (i + 0.75)
            if xm < JAW_FROM + 0.3:
                continue
            lx, ly = section(xm, angle_at(xm, mouth_y(xm) - GAP))
            x = lx * 0.97 - TOOTH_IN * size
            if x > TOOTH_RADIUS:
                base = Vector((sx * x, ly - TOOTH_LONG * 0.2, xm - HALF))
                cone(m, TOOTH_LOW, base, Vector((sx * 0.08, 1.0, -0.05)).normalized(), TOOTH_RADIUS * size * 0.95,
                     min(TOOTH_LONG * size * 1.55, 0.55 * (top(xm) - ly)), sides, levels, "lower teeth", hook=-0.1 * size)


def on_skin(xm, y, sx):
    x, yy = section(xm, angle_at(xm, y))
    return sculpt(xm, sx * x, yy)


def skin_frame(xm, angle, sx):
    """A point on the skin `angle` round from the ridge, and the way out of the skin there."""
    x, y = section(xm, angle)
    here = sculpt(xm, sx * x, y)
    d = 0.05
    xa, ya = section(xm, angle + d)
    xb, yb = section(xm, angle - d)
    around = sculpt(xm, sx * xa, ya) - sculpt(xm, sx * xb, yb)
    x2, y2 = section(xm + d * 4, angle)
    x1, y1 = section(xm - d * 4, angle)
    along = sculpt(xm + d * 4, sx * x2, y2) - sculpt(xm - d * 4, sx * x1, y1)
    out = around.cross(along).normalized()
    centre = Vector((0.0, 0.5 * (top(xm) + bottom(xm)), xm - HALF))
    if out.dot(here - centre) < 0.0:
        out = -out
    return here, out


def eye(m, sx, lod):
    """A low dome lying on the skin of the head."""
    spokes, steps = {"full": (32, 6), "low": (12, 2), "game": (28, 3)}[lod]
    xe, ye = EYE_AT
    here = on_skin(xe, ye, sx)
    d = EYE_RADIUS * 0.3
    out = (on_skin(xe + d, ye, sx) - on_skin(xe - d, ye, sx)).cross(on_skin(xe, ye + d, sx) - on_skin(xe, ye - d, sx))
    out.normalize()
    if out.x * sx < 0.0:
        out = -out
    bulge = EYE_RADIUS * 0.28
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
    """Prints where the right eye sits, for the shader's cartoon eye (the left is its mirror)."""
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
    rho = EYE_RADIUS * 1.4
    for s in range(16):
        a = s / 16 * TAU
        p = on_skin(xe + math.cos(a) * rho, ye + math.sin(a) * rho, 1.0) - here
        flat = p - out * p.dot(out)
        sag += -p.dot(out) / max(1e-9, flat.length_squared)
    print("EYE_FRAME centre Vector3(%.5f, %.5f, %.5f) out Vector3(%.4f, %.4f, %.4f) fwd Vector3(%.4f, %.4f, %.4f) up Vector3(%.4f, %.4f, %.4f) EYE_SAG %.4f"
          % (here.x, here.y, here.z, out.x, out.y, out.z, fwd.x, fwd.y, fwd.z, up.x, up.y, up.z, sag / 16))


def ragged(depth, seed, keep_tip=True):
    """How far a tattered fin's trailing edge reaches at row `ti` of `nt` (1 whole): torn back by up to `depth`
    of its chord, row by row, the root and the tip whole."""
    def f(t, ti, nt):
        if ti == 0 or (keep_tip and ti == nt):
            return 1.0
        h = hash1(ti * 7 + seed)
        # (every other row torn deeper: a frayed, saw-toothed edge; now and then a deep rent)
        tear = depth * (0.25 + 0.75 * h) * (1.0 if ti % 2 else 0.35)
        if h > 0.82:
            tear = depth * 1.6
        return max(0.25, 1.0 - tear)
    return f


def blade(m, part, name, point, place, facing, thick, nt, nu, tip_gather=1.0, extra=0.0, rag=None):
    """A fin: a thin closed blade. `point(t, u)` is a place in the fin's own flat (t 0 at its root to 1 at its tip,
    u 0 at its leading edge to 1 at its trailing edge), `place` puts that in the model, `facing` is the way one of
    its two skins faces. It is `thick` at its root, a foil across, thinning to nothing at its tip. `rag(t, ti, nt)`
    tears its trailing edge back."""
    for side in (1.0, -1.0):
        grid = []
        for ti in range(nt + 1):
            t = ti / nt if tip_gather == 1.0 else 1.0 - (1.0 - ti / nt) ** tip_gather
            reach = rag(t, ti, nt) if rag else 1.0
            row = []
            for ui in range(nu + 1):
                u = ui / nu
                foil = 2.6 * math.sqrt(u) * (1.0 - u)
                swell = thick * (1.0 - t) ** 0.7 * foil
                p = place(point(t, u * reach)) + facing * (side * swell * 0.5)
                row.append(m.add(p, (t, u * reach), part, extra))
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
    """A place in the flat of an upright fin (metres behind the tip, metres up) in the model."""
    return Vector((0.0, p[1], p[0] - HALF))


SIDE = Vector((1.0, 0.0, 0.0))
UP = Vector((0.0, 1.0, 0.0))


def flipper(m, part, name, sx, at, level, length, chord, sweep, out_down, thick, nt, nu, g, rag):
    """A side fin: broad, swept back, held out and down. Its root is at `at` metres behind the tip, `level` up, a
    little inside the skin."""
    x, y = section(at, angle_at(at, level))
    root = Vector((sx * x * 0.93, y, at - HALF))
    span = Vector((sx * 1.0, -out_down, 0.5)).normalized()
    chord_way = Vector((sx * 0.08, -0.04, 1.0)).normalized()
    facing = span.cross(chord_way).normalized()
    if facing.y < 0.0:
        facing = -facing

    def point(t, u):
        t *= 0.985
        lead = sweep * t * t
        wide = chord * (1.0 - t ** 1.6) ** 0.55 * (1.0 + 0.35 * t) + 0.02
        return (length * t, lead + wide * u - 0.3 * chord * (1.0 - t))

    blade(m, part, name, point, lambda p: root + span * p[0] + chord_way * p[1], facing, thick, nt, nu, g, rag=rag)


def ridge(m, name, x0, x1, base, height, inset, lean, nu, nt, spikes, way):
    """A serrated fringe along the top (`way` 1) or the bottom (-1) of the tail: a thin closed blade standing out
    of the ridge from `x0` to `x1`, `height` high (a function of how far along, 0..1), leaning back by `lean`, its
    free edge cut into `spikes` points."""
    def point(t, u):
        xm = x0 + (x1 - x0) * u
        # (a saw: tall at each spike, low between)
        k = u * spikes
        saw = 1.0 - 0.75 * abs(k - math.floor(k) - 0.5) * 2.0
        tall = height(u) * (0.35 + 0.65 * saw)
        return (xm + lean * t * tall, base(xm) - way * inset + way * tall * t)

    # (the blade's own t runs root to edge; u along the body; its points, column by column, are wound so its two
    # skins face out to either side)
    def column_point(t, u):
        return point(t, u)

    for side in (1.0, -1.0):
        grid = []
        for ti in range(nt + 1):
            t = ti / nt
            row = []
            for ui in range(nu + 1):
                u = ui / nu
                foil = 1.0 if 0 < ui < nu else 0.0
                p = column_point(t, u)
                swell = 0.22 * (1.0 - t) * foil
                row.append(m.add(Vector((side * swell * 0.5, p[1], p[0] - HALF)), (t, u), FIN))
            grid.append(row)
        for ti in range(nt):
            for ui in range(nu):
                m.face((grid[ti][ui], grid[ti][ui + 1], grid[ti + 1][ui + 1], grid[ti + 1][ui]), SIDE * side, name)


def fins(m, lod):
    full = lod == "full"
    low = lod == "low"

    def n(full_n, game_n, low_n):
        return full_n if full else (low_n if low else game_n)

    g = 1.3 if lod == "game" else 1.0
    # The tail fin: a tall ragged upper lobe and a smaller lower one, upright.
    up_tip = (40.0, 4.6)
    blade(m, FIN, "tail fin", swept(((35.6, top(35.6) - 0.15), (37.6, 2.6), up_tip),
                                    ((38.2, top(38.2) - 0.1), (38.9, 1.2), up_tip)),
          upright, SIDE, 0.4, n(18, 9, 5), n(8, 4, 2), g, rag=ragged(0.5, 3) if not low else None)
    lo_tip = (39.5, -2.9)
    blade(m, FIN, "tail fin", swept(((36.2, bottom(36.2) + 0.15), (37.8, -1.9), lo_tip),
                                    ((38.4, bottom(38.4) + 0.08), (38.9, -1.0), lo_tip)),
          upright, SIDE, 0.35, n(12, 7, 4), n(6, 3, 2), g, rag=ragged(0.45, 11) if not low else None)
    # The dorsal: a tattered sail on the hump of the back, raked back.
    blade(m, FIN, "dorsal fin", swept(((13.2, top(13.2) - 0.3), (15.2, 7.0), (18.8, 9.3)),
                                      ((20.6, top(20.6) - 0.3), (20.4, 6.6), (18.8, 9.3))),
          upright, SIDE, 0.35, n(16, 8, 4), n(10, 5, 2), g, rag=ragged(0.4, 21) if not low else None)
    # The fringes along the top and the bottom of the tail.
    ridge(m, "tail ridge", 23.0, 36.0, top, lambda u: 1.3 - 0.5 * u, 0.25, 0.35,
          n(26, 16, 6), 1, n(13, 8, 3), 1.0)
    ridge(m, "keel ridge", 27.0, 36.4, bottom, lambda u: 0.9 - 0.3 * u, 0.25, 0.3,
          n(18, 12, 4), 1, n(9, 6, 2), -1.0)
    # (the shoulders' row of armoured spines, ahead of the dorsal)
    ridge(m, "back spines", 9.6, 13.4, top, lambda u: 0.55, 0.15, 0.2, n(10, 6, 2), 1, n(5, 3, 1), 1.0)
    for sx in (1.0, -1.0):
        # The pectorals: great tattered fins swept back and down behind the jaw; the pelvics, small, under the trunk.
        flipper(m, PECTORAL, "pectoral fins", sx, 13.0, -2.3, 7.4, 3.6, 3.4, 0.75, 0.35, n(16, 9, 4), n(8, 4, 2), g,
                ragged(0.55, 31 if sx > 0 else 47) if not low else None)
        flipper(m, FIN, "pelvic fins", sx, 23.5, -1.8, 3.4, 1.7, 1.4, 1.1, 0.25, n(10, 5, 3), n(5, 3, 2), g,
                ragged(0.4, 53 if sx > 0 else 59) if not low else None)


# Barnacles: (metres behind the tip, the angle round the body from the ridge, which side, radius).
BARNACLES = [
    (15.2, 0.12, 1, 0.6), (15.9, 0.26, 1, 0.5), (16.5, 0.08, -1, 0.58), (15.0, 0.3, -1, 0.42),
    (16.9, 0.36, 1, 0.42), (17.4, 0.18, -1, 0.5), (14.4, 0.2, 1, 0.4), (17.9, 0.05, 1, 0.38),
    (16.2, 0.45, 1, 0.34), (14.8, 0.46, -1, 0.36),
    (5.4, 0.2, 1, 0.34), (5.9, 0.32, 1, 0.26), (6.2, 0.15, -1, 0.3),
    (21.5, 0.6, 1, 0.38), (22.2, 0.7, 1, 0.3), (24.0, 0.55, -1, 0.36), (11.8, 0.9, -1, 0.3),
]


def barnacle(m, xm, angle, sx, radius, sides, lod):
    """An acorn barnacle: a short cone of plates standing out of the skin, a crater in its top."""
    here, out = skin_frame(xm, angle, sx)
    side = out.cross(Vector((0.0, 0.0, 1.0)))
    if side.length < 1e-6:
        side = Vector((1.0, 0.0, 0.0))
    side.normalize()
    other = out.cross(side).normalized()
    tall = radius * 1.0
    levels = [(-0.25 * radius, radius * 1.05), (tall, radius * 0.62), (tall * 0.72, radius * 0.36)]
    rows = []
    for k, (h, r) in enumerate(levels):
        row = []
        for s in range(sides):
            a = s / sides * TAU + 0.3 * k
            wob = 1.0 + 0.12 * math.sin(a * 3.0 + xm)
            p = here + out * h + (side * math.cos(a) + other * math.sin(a)) * r * wob
            row.append(m.add(p, (k / 2.0, 0.0), BARNACLE))
        rows.append(row)
    for s in range(sides):
        nx = (s + 1) % sides
        a = rows[0]
        b = rows[1]
        mid = (m.verts[a[s]] + m.verts[b[nx]]) * 0.5
        m.face((a[s], a[nx], b[nx], b[s]), mid - (here + out * (mid - here).dot(out)), "barnacles")
        c = rows[2]
        m.face((b[s], b[nx], c[nx], c[s]), out, "barnacles")
    centre = m.add(here + out * (tall * 0.45), (1.0, 0.0), BARNACLE, 1.0)
    for s in range(sides):
        nx = (s + 1) % sides
        m.face((rows[2][s], rows[2][nx], centre), out, "barnacles")


def tube(m, part, points, radius, sides, name, extra=0.0, cap_end=True, along=None):
    """A thin tube through `points` (a rope, a shaft); UV.x from 0 at the first point to 1 at the last."""
    rows = []
    n = len(points)
    for i, p in enumerate(points):
        a = points[max(0, i - 1)]
        b = points[min(n - 1, i + 1)]
        way = (b - a).normalized()
        ref = Vector((0.0, 1.0, 0.0)) if abs(way.y) < 0.9 else Vector((1.0, 0.0, 0.0))
        side = way.cross(ref).normalized()
        other = way.cross(side).normalized()
        u = i / (n - 1) if along is None else along[i]
        r = radius(u) if callable(radius) else radius
        row = []
        for s in range(sides):
            ang = s / sides * TAU
            row.append(m.add(p + (side * math.cos(ang) + other * math.sin(ang)) * r, (u, s / sides), part, extra))
        rows.append((row, p))
    for i in range(n - 1):
        a, pa = rows[i]
        b, pb = rows[i + 1]
        for s in range(sides):
            nx = (s + 1) % sides
            mid = (m.verts[a[s]] + m.verts[b[nx]]) * 0.5
            axis = (pb - pa).normalized()
            centre = pa + axis * (mid - pa).dot(axis)
            m.face((a[s], a[nx], b[nx], b[s]), mid - centre, name)
    first, p0 = rows[0]
    way0 = (points[1] - points[0]).normalized()
    c0 = m.add(p0 - way0 * 0.001, (0.0, 0.0), part, extra)
    for s in range(sides):
        m.face((first[s], first[(s + 1) % sides], c0), -way0, name)
    if cap_end:
        last, p1 = rows[-1]
        way1 = (points[-1] - points[-2]).normalized()
        c1 = m.add(p1 + way1 * 0.001, (1.0, 0.0), part, extra)
        for s in range(sides):
            m.face((last[s], last[(s + 1) % sides], c1), way1, name)


# Harpoons: (metres behind the tip, angle round from the ridge, side, how far it leans back, length out of the
# skin, iron showing, rope length).
HARPOONS = [
    (16.6, 0.22, 1, 0.12, 5.0, True, 0.0),
    (21.0, 0.45, 1, 0.75, 3.6, False, 9.0),
    (25.6, 0.18, -1, 0.6, 3.4, False, 7.0),
    (12.2, 0.55, -1, 0.5, 3.0, False, 6.0),
]


def harpoon(m, xm, angle, sx, lean, long, iron, rope_long, lod):
    here, out = skin_frame(xm, angle, sx)
    way = (out + Vector((0.0, 0.0, lean))).normalized()
    sides = 6 if lod == "full" else 4
    start = here - way * 0.8
    end = here + way * long
    r_shaft = 0.12
    tube(m, HARPOON, [start, here, end], r_shaft, sides, "harpoons")
    if iron:
        # The barbed iron out at the end (as if it had gone in by its butt: sailors' harpoons from the concept):
        # a socket, two barbs and a point.
        side = way.cross(Vector((0.0, 0.0, 1.0)))
        if side.length < 1e-6:
            side = Vector((1.0, 0.0, 0.0))
        side.normalize()
        other = way.cross(side).normalized()
        socket = end
        tip = end + way * 1.5
        barb_at = end + way * 0.55
        ring = []
        for s in range(4):
            a = s / 4 * TAU + TAU / 8
            wide = 0.55 if s % 2 == 0 else 0.12
            ring.append(m.add(barb_at + (side * math.cos(a) * wide + other * math.sin(a) * 0.12) - way * (0.35 if s % 2 == 0 else 0.0), (0.5, 0.0), HARPOON, 1.0))
        base_ring = []
        for s in range(4):
            a = s / 4 * TAU + TAU / 8
            base_ring.append(m.add(socket + (side * math.cos(a) + other * math.sin(a)) * 0.15, (0.0, 0.0), HARPOON, 1.0))
        t = m.add(tip, (1.0, 0.0), HARPOON, 1.0)
        for s in range(4):
            nx = (s + 1) % 4
            mid = (m.verts[ring[s]] + m.verts[ring[nx]]) * 0.5
            axis_pt = socket + way * (mid - socket).dot(way)
            m.face((base_ring[s], base_ring[nx], ring[nx], ring[s]), mid - axis_pt, "harpoons")
            m.face((ring[s], ring[nx], t), mid - axis_pt, "harpoons")
    if rope_long > 0.0:
        # A rope tied near the butt, trailing back along the body, sagging and drifting out to the side.
        segs = 12 if lod == "full" else (8 if lod == "game" else 4)
        pts = []
        tie = end - way * 0.3
        for i in range(segs + 1):
            u = i / segs
            p = tie + Vector((sx * (0.3 + 2.4 * u) * u, -rope_long * 0.75 * u ** 1.2, rope_long * 0.55 * u))
            pts.append(p)
        tube(m, ROPE, pts, lambda u: 0.11 * (1.0 - 0.3 * u), 4 if lod != "full" else 5, "ropes")
        # (and a loose loop of it round the shaft)


def make(name, lod):
    m = Mesh()
    body(m, lod)
    jaw(m, lod)
    teeth(m, lod)
    for sx in (1.0, -1.0):
        eye(m, sx, lod)
    fins(m, lod)
    sides = {"full": 7, "game": 5, "low": 4}[lod]
    for i, (xm, angle, sx, radius) in enumerate(BARNACLES):
        if (lod == "low" and i % 2) or (lod == "game" and radius < 0.31):
            continue
        barnacle(m, xm, angle, sx, radius, sides, lod)
    for xm, angle, sx, lean, long, iron, rope in HARPOONS:
        harpoon(m, xm, angle, sx, lean, long, iron, rope, lod)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) for p in m.verts], [], m.faces)
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
    bsdf.inputs["Base Color"].default_value = (0.3, 0.42, 0.42, 1.0)
    material.diffuse_color = (0.3, 0.42, 0.42, 1.0)
    mesh.materials.append(material)
    mesh.update()
    winding(name, mesh, m)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.set_sharp_from_angle(angle=math.radians(50.0))
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    parts = {}
    for name_, count in m.count.items():
        parts[name_] = count
    print("BUILT %s verts=%d tris=%d" % (name, len(mesh.vertices), tris))
    return obj


def winding(name, mesh, m):
    """Nothing inside out: every face's front is the side it was meant to face (Blender's front is the side a
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
    f = LENGTH
    views = [("left", (1, 0, 0), (0, 0, 0), 1.12 * f), ("right", (-1, 0, 0), (0, 0, 0), 1.12 * f),
             ("front", (0, 1, 0), (0, 0, 0), 0.5 * f), ("back", (0, -1, 0), (0, 0, 0), 0.5 * f),
             ("top", (0.001, 0, 1), (0, 0, 0), 1.12 * f), ("under", (0.001, 0, -1), (0, 0, 0), 1.12 * f),
             ("head", (0.8, 0.5, 0.2), (0, HALF - 6.0, 0), 2.0 * CORNER)]
    for prefix, obj in zip(("", "lo_", "game_"), made):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if prefix == "lo_" and view not in ("left", "head"):
                continue
            offset = Vector(direction).normalized() * 200.0
            camera.data.ortho_scale = frame
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % (prefix, view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    full = make(NAME, "full")
    low = make(NAME + "_lo", "low")
    game = make(NAME + "_game", "game")
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, NAME + ".glb"))
    export_one(low, os.path.join(OUT, NAME + "_lo.glb"))
    export_one(game, os.path.join(OUT, NAME + "_game.glb"))
    eye_frame()
    low.location.x = LENGTH * 0.4
    game.location.x = -LENGTH * 0.4
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, NAME + ".blend"))
    low.location.x = 0.0
    game.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low, game])


if __name__ == "__main__":
    main()
