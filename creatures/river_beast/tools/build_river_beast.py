"""Builds the river beast (creatures/river_beast) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/river_beast/tools/build_river_beast.py
    blender --background --python creatures/river_beast/tools/build_river_beast.py -- <preview folder>   # with pictures

Writes creatures/river_beast/models/river_beast.glb (the full model, for close pictures), river_beast_lo.glb (far
off) and river_beast_game.glb (the game model: Twilight Princess weight, its triangles spent on the head, the claws
and the shaggy outline), and the editable creatures/river_beast/tools/river_beast.blend (this folder has a
.gdignore). Each model is one still mesh with one surface: the shader (river_beast.gdshader) draws every marking,
swims it, opens its mouth and stands it up (`stand`). It prints a WINDING line for each model (the check that
nothing is inside out) and an EYE_FRAME line (where the eye sits, for the shader's cartoon eye).

A creature of our own (Claude's design, from the concept sheet's sixth panel, in the spirit of a drawing the user
showed; nothing of that drawing is traced): a heavy shaggy brown-furred animal the size of a big bear, 3.93 m from
the tip of its snout to the tip of its tail, that can stand up on its hind legs (2.6 m tall then), with:

- A CAIMAN'S HEAD: a broad flat snout, nostrils raised at its tip, the eyes raised on top at the back under bony
  brows, conical teeth showing along the lips with the mouth shut; scaly, not furred.
- A BEAR'S BODY in wet matted fur: a deep chest and a shaggy ruff round the neck and shoulders, the fur in clumped
  tufts that hang back along the body (and so down, when it stands); each tuft a few big triangles, so the shaggy
  edge is in the outline itself (no fur shader).
- SCALY HANDS AND FEET with big dark claws (the fur stops at the wrists and ankles), and a BROAD FLAT SCALY TAIL,
  a paddle like a beaver's but longer, furred only at its root.

It is BUILT SWIMMING, as a beaver or an otter swims at the surface: lying along the water, its forelimbs tucked
under its chest, its hind legs trailing back beside its tail. The shader stands it up (`stand`): the body turns up
about the hips, the head comes back to level, the hind legs swing down under it, the arms hang in front of the
chest, the tail drops to the ground behind.

Everything here is in Godot space (metres, Y up, its nose at -Z) until it is written out; the origin is on its
middle line, half way along (1.965 m behind the tip of its snout). `xm` below is metres behind that tip.

What a point is, for the shader: UV2.y the part (0 body (the tail too), 1 lower jaw, 2 an upper tooth, 3 a lower
tooth, 5 an arm, 6 a hind leg, 7 an eye). UV2.x: on the body and the jaw, how much the point is inside the mouth
(0 skin, 1 the roof or floor of the mouth); on a limb, how far along it from its root (metres, in this pose).
UV, on the body and jaw: x how far along (0 the tip to 1 the tail's tip), y how high on its side (1 the ridge of
the back, 0 the keel of the belly); on a limb: x along it (0..1), y 1 on a claw, 0 elsewhere; on an eye: x from
its middle (0) to its rim (1); on a tooth x from its root to its tip. On a TUFT of fur (on the body or a limb), UV.y
is 2 + how far from its root to its tip (0..1), the rest as for what it grows on. (The glTF writer flips V: what is
written here is 1 - v, so that Godot reads v.)

The numbers marked "as the shader has it" are in river_beast.gdshader too: change one, change the other.
"""

import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "models")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = ARGS[0] if ARGS else ""

NAME = "river_beast"
LENGTH = 3.93
HALF = 1.965
BODY, JAW, TOOTH_UP, TOOTH_LOW, _UNUSED, ARM, HIND, EYE = range(8)
TAU = math.tau
PI = math.pi

# The whole outline, as it lies swimming: metres behind the tip, the height of the ridge of its back, of the keel
# of its belly, half its width.
PROFILE = [
    (0.0, 0.04, -0.07, 0.07),
    (0.05, 0.075, -0.1, 0.12),
    (0.2, 0.078, -0.11, 0.145),
    (0.36, 0.1, -0.13, 0.17),
    (0.48, 0.155, -0.155, 0.195),
    (0.6, 0.175, -0.185, 0.215),
    (0.74, 0.2, -0.23, 0.225),
    (0.86, 0.27, -0.32, 0.26),
    (1.02, 0.36, -0.42, 0.33),
    (1.25, 0.42, -0.5, 0.4),
    (1.6, 0.44, -0.54, 0.44),
    (1.98, 0.4, -0.51, 0.43),
    (2.33, 0.32, -0.38, 0.37),
    (2.53, 0.2, -0.24, 0.3),
    (2.73, 0.1, -0.12, 0.28),
    (3.03, 0.066, -0.076, 0.27),
    (3.38, 0.05, -0.06, 0.24),
    (3.68, 0.036, -0.045, 0.16),
    (3.93, 0.01, -0.02, 0.02),
]
BODY_FROM = 0.0
BODY_TO = 3.93
JAW_FROM = 0.04

# As the shader has it: the corner of the mouth, how far behind it the cut is spread, the eye (metres behind the
# tip, metres up) and its radius.
CORNER = 0.58
WALL = 0.14
EYE_AT = (0.49, 0.112)
EYE_RADIUS = 0.03
GAP = 0.003
VAULT = 0.3
JAW_TAIL = 0.11
# The teeth along the lips: how many each side of each jaw, from where to where, how thick, how long.
TEETH = 12
TEETH_FROM = 0.04
TEETH_TO = 0.53
TOOTH_RADIUS = 0.0095
TOOTH_LONG = 0.034
TOOTH_IN = 0.015
# Mesh resolutions: the body's columns down each side and across the roof of the mouth (low, full); the lower
# jaw's (columns, roof, rings) and the eye's (spokes, rings) for the low, full and game models.
LOW_KR = (6, 1)
FULL_KR = (30, 5)
JAW_LOW, JAW_FULL, JAW_GAME = (4, 1, 8), (16, 5, 48), (5, 1, 11)
EYE_LOW, EYE_FULL, EYE_GAME = (8, 2), (36, 9), (16, 3)
# Where the fur starts behind the scaly head and where it ends on the root of the scaly tail (as the shader has it).
FUR_FROM = 0.76
FUR_TO = 2.68

# The limbs, swimming, as the shader has them: (xm, y) of the root, the middle joint and the far joint, and how
# far out to the side the root is. Arm: shoulder, elbow, wrist; leg: hip, knee, ankle.
SHOULDER = (1.26, -0.26)
ELBOW = (1.58, -0.44)
WRIST = (1.9, -0.46)
ARM_X = 0.28
HIP = (2.3, -0.15)
KNEE = (2.73, -0.31)
ANKLE = (3.13, -0.29)
LEG_X = 0.2


def mouth_y(xm):
    """The line of the mouth: a little below the snout's middle, rising a touch to the corner (a croc's grin)."""
    return -0.035 - 0.012 * xm + 0.03 * smooth(0.34, 0.58, xm)


def _px(xm):
    # (the snout is a little boxy; the tail a flat paddle with sharp edges)
    return 0.85 + 0.15 * smooth(0.4, 0.7, xm)


def _py(xm):
    return 1.0 + 0.9 * smooth(2.58, 2.83, xm) - 0.12 * (1.0 - smooth(0.4, 0.8, xm))



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


def curve(points):
    xs = [p[0] for p in points]
    cols = []
    for c in range(1, len(points[0])):
        ys = [p[c] for p in points]
        cols.append((ys, _slopes(xs, ys)))

    def at(x):
        x = max(xs[0], min(xs[-1], x))
        i = 0
        while i < len(xs) - 2 and x > xs[i + 1]:
            i += 1
        h = xs[i + 1] - xs[i]
        t = (x - xs[i]) / h
        out = []
        for ys, m in cols:
            a = (2 * t ** 3 - 3 * t ** 2 + 1) * ys[i] + (t ** 3 - 2 * t ** 2 + t) * h * m[i]
            b = (-2 * t ** 3 + 3 * t ** 2) * ys[i + 1] + (t ** 3 - t ** 2) * h * m[i + 1]
            out.append(a + b)
        return out
    return at


def outline(xm):
    """(the top, the bottom, half the width) at `xm`."""
    out = _OUTLINE(xm)
    out[0] = max(out[0], out[1] + 0.001)
    out[2] = max(out[2], 0.0005)
    return out


def top(xm):
    return outline(xm)[0]


def bottom(xm):
    return outline(xm)[1]


def section(xm, angle):
    """(x, y) of the skin: `angle` round the body from the ridge of the back (0) by one side (a quarter turn)
    to the keel of the belly (half a turn)."""
    up, down, wide = outline(xm)
    yc = 0.5 * (up + down)
    c = math.cos(angle)
    s = math.sin(angle)
    py = _py(xm)
    y = yc + math.copysign(abs(c) ** py, c) * (up - yc if c >= 0.0 else yc - down)
    x = math.copysign(abs(s) ** _px(xm), s) * wide
    return x, y


def sculpt(xm, x, y):
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
    c = max(-1.0, min(1.0, c))
    c = math.copysign(abs(c) ** (1.0 / _py(xm)), c)
    return math.acos(c)


def clip_y(xm):
    """Under this the body's skin is cut away for the mouth: the line of the mouth as far as its corner, then
    a wall falling to the belly (the back of the mouth)."""
    if xm <= CORNER:
        return mouth_y(xm)
    return mouth_y(CORNER) + (bottom(xm) - 0.012 - mouth_y(CORNER)) * smooth(CORNER, CORNER + WALL, xm)


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
    """For the game model: the fewest of the stations `xs` such that a straight line between two kept ones stays
    within `tol` of `values` at every station left out, no two kept ones more than `longest` apart."""
    vals = [values(x) for x in xs]
    fixed = {i for i, x in enumerate(xs) if any(abs(x - k) < 1e-9 for k in keep)}
    kept = [0]
    i = 0
    while i < len(xs) - 1:
        j = i + 1
        while j + 1 < len(xs) and j not in fixed:
            c = j + 1
            reach = longest(xs[i]) if callable(longest) else longest
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


def game_angle(j, k, lip):
    s = j / k

    def gather(t):
        return t - 0.35 * math.sin(TAU * t) / TAU

    return lip * (0.5 * gather(2.0 * s) if s <= 0.5 else 0.5 + 0.5 * gather(2.0 * s - 1.0))


def loft(m, rows, flat_from, flat_to, flat_out, name, flat_name):
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
    xm = tip.z + HALF
    point = m.add(tip, (xm / LENGTH, high_of(xm, tip.y)), part, extra)
    for c in range(len(row)):
        m.face((point, row[c], row[(c + 1) % len(row)]), Vector((0.0, 0.0, way)), name)


def body(m, low, game=False):
    """The body's skin, with the roof of the mouth: columns 0 (the ridge of the back) to K (the lip) down each
    side, then R more across the roof to its middle."""
    k, r = LOW_KR if low else FULL_KR
    if game:
        k, r = GAME_K, GAME_R
    rows = []
    xs = rings(low, game)
    for xm in xs:
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
    loft(m, rows, k, k + 2 * r, Vector((0.0, -1.0, 0.0)), "body", "roof of the mouth")
    first = xs[0]
    cap(m, BODY, rows[0][0], Vector((0.0, 0.5 * (top(first) + mouth_y(first)), first - 0.004 - HALF)), 0.0, -1.0, "body")
    last = xs[-1]
    cap(m, BODY, rows[-1][0], Vector((0.0, 0.5 * (top(last) + bottom(last)), last + 0.004 - HALF)), 0.0, 1.0, "body")


def jaw(m, low, game=False):
    """The lower jaw: columns 0 (the middle of the floor of the mouth) to R (the lip), then K more down the
    outside to the keel of the chin."""
    k, r, count = JAW_LOW if low else JAW_FULL
    if game:
        k, r, count = JAW_GAME
    rows = []
    to = CORNER + JAW_TAIL
    for i in range(count + 1):
        xm = JAW_FROM + (to - JAW_FROM) * (i / count) ** 1.1
        up, down, _ = outline(xm)
        level = mouth_y(min(xm, CORNER)) - GAP
        lip = angle_at(xm, level)
        lx, ly = section(xm, lip)
        shrink = 1.0 - (0.012 + 0.05 * smooth(CORNER, to, xm)) * (1.0 if xm > CORNER else 0.0)
        half = []
        for j in range(r):
            half.append((Vector((lx * j / r, ly, xm - HALF)), 1.0))
        for j in range(k + 1):
            x, y = section(xm, lip + (PI - lip) * j / k)
            half.append((Vector((x, y, xm - HALF)), 0.0))
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
    flat = []
    for row, middle in rows:
        flat.append((row[around - r:] + row[:around - r], middle))
    loft(m, flat, 0, 2 * r, Vector((0.0, 1.0, 0.0)), "jaw", "floor of the mouth")
    cap(m, JAW, rows[0][0], Vector((0.0, 0.5 * (mouth_y(JAW_FROM) - GAP + bottom(JAW_FROM)), JAW_FROM - 0.004 - HALF)), 0.0, -1.0, "jaw")
    cap(m, JAW, rows[-1][0], Vector((0.0, 0.5 * (mouth_y(CORNER) + bottom(to)), to + 0.002 - HALF)), 0.0, 1.0, "jaw")


def cone(m, part, base, axis, radius, long, sides, levels, name, uvy=0.0, extra=None, bend=None):
    """A cone standing on `base` along `axis` (bent towards `bend` as it goes, for a claw). `extra` gives
    each point's UV2.x from its place (a limb's along), or 0."""
    side = axis.cross(Vector((0.0, 0.0, 1.0)))
    if side.length < 1e-6:
        side = axis.cross(Vector((1.0, 0.0, 0.0)))
    side.normalize()
    other = axis.cross(side).normalized()

    def centre(share):
        c = base + axis * (long * share)
        if bend is not None:
            c += bend * (long * 0.35 * share * share)
        return c

    def add(p, share):
        return m.add(p, (share, uvy), part, extra(p) if extra else 0.0)

    last = None
    for share, thick in levels:
        row = []
        for s in range(sides):
            a = s / sides * TAU
            p = centre(share) + (side * math.cos(a) + other * math.sin(a)) * (radius * thick)
            row.append(add(p, share))
        if last is not None:
            for s in range(sides):
                n = (s + 1) % sides
                at = (m.verts[row[s]] + m.verts[row[n]]) * 0.5 - centre(share)
                m.face((last[s], last[n], row[n], row[s]), at, name)
        last = row
    tip = add(centre(1.0), 1.0)
    for s in range(sides):
        n = (s + 1) % sides
        at = (m.verts[last[s]] + m.verts[last[n]]) * 0.5 - centre(levels[-1][0])
        m.face((last[s], last[n], tip), at, name)
    return last


def on_skin(xm, y, sx):
    x, yy = section(xm, angle_at(xm, y))
    return sculpt(xm, sx * x, yy)


def eye(m, sx, low, game=False):
    spokes, steps = EYE_LOW if low else EYE_FULL
    if game:
        spokes, steps = EYE_GAME
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
    print("EYE_FRAME centre vec3(%.5f, %.5f, %.5f) out vec3(%.4f, %.4f, %.4f) fwd vec3(%.4f, %.4f, %.4f) up vec3(%.4f, %.4f, %.4f) EYE_SAG %.4f"
          % (here.x, here.y, here.z, out.x, out.y, out.z, fwd.x, fwd.y, fwd.z, up.x, up.y, up.z, sag / 16))


def blade(m, part, name, point, place, facing, thick, nt, nu, extra=0.0, uv=None, tgather=1.0):
    """A thin closed blade. `point(t, u)` is a place in its own flat, `place` puts that in the model, `facing`
    is the way one of its two skins faces. `thick` at its root (t 0), a foil across (nothing at u 0 or 1),
    thinning to nothing at t 1."""
    for side in (1.0, -1.0):
        grid = []
        for ti in range(nt + 1):
            t = 1.0 - (1.0 - ti / nt) ** tgather
            row = []
            for ui in range(nu + 1):
                u = ui / nu
                foil = 2.6 * math.sqrt(u) * (1.0 - u)
                swell = thick * (1.0 - t) ** 0.7 * foil
                p = place(point(t, u)) + facing * (side * swell * 0.5)
                row.append(m.add(p, uv(t, u) if uv else (t, u), part, extra(p) if callable(extra) else extra))
            grid.append(row)
        for ti in range(nt):
            for ui in range(nu):
                m.face((grid[ti][ui], grid[ti][ui + 1], grid[ti + 1][ui + 1], grid[ti + 1][ui]), facing * side, name)


def along_of(points):
    """Distances from the first point along a chain of points."""
    out = [0.0]
    for i in range(1, len(points)):
        out.append(out[-1] + (points[i] - points[i - 1]).length)
    return out


def tube(m, part, name, points, radii, sides, total, from_along=0.0, flat=1.0, up=None, uvy=0.0):
    """A closed tube through `points` (each with its radius), capped at both ends: a limb. Each point's UV2.x
    is how far along the limb it is (from `from_along` at the first point); UV.x that over `total`."""
    alongs = [from_along + a for a in along_of(points)]
    rows = []
    for i, p in enumerate(points):
        if i == 0:
            axis = points[1] - points[0]
        elif i == len(points) - 1:
            axis = points[-1] - points[-2]
        else:
            axis = (points[i + 1] - points[i - 1])
        axis.normalize()
        ref = up if up is not None else Vector((0.0, 1.0, 0.0))
        side = axis.cross(ref)
        if side.length < 1e-4:
            side = axis.cross(Vector((1.0, 0.0, 0.0)))
        side.normalize()
        other = side.cross(axis).normalized()
        row = []
        for s in range(sides):
            a = s / sides * TAU + PI / sides
            q = p + (side * math.cos(a) + other * math.sin(a) * flat) * radii[i]
            row.append(m.add(q, (alongs[i] / total, uvy), part, alongs[i]))
        rows.append((row, p))
    for i in range(len(rows) - 1):
        a, pa = rows[i]
        b, pb = rows[i + 1]
        for s in range(sides):
            n = (s + 1) % sides
            quad = (a[s], a[n], b[n], b[s])
            at = sum((m.verts[q] for q in quad), Vector()) * 0.25
            axis = (pb - pa).normalized()
            mid = pa + axis * (at - pa).dot(axis)
            m.face(quad, at - mid, name)
    for end, way in ((0, points[0] - points[1]), (-1, points[-1] - points[-2])):
        row, p = rows[end]
        tip = m.add(p + way.normalized() * radii[end] * 0.5, (alongs[end] / total, uvy), part, alongs[end])
        for s in range(len(row)):
            m.face((tip, row[s], row[(s + 1) % len(row)]), way, name)


def P(xm, y, x):
    return Vector((x, y, xm - HALF))


def chain(a, b, n):
    return [a + (b - a) * (i / n) for i in range(n + 1)]


def winding(name, mesh, m):
    """Nothing inside out: every face's normal on the side it was meant to face."""
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


_OUTLINE = curve(PROFILE)

GAME_TOL = 0.006
GAME_K = 8
GAME_R = 1


def game_longest(xm):
    # (short steps over the head and down the tail, which bends; longer over the furred trunk, whose outline
    # the tufts make)
    if CORNER - 0.01 < xm < CORNER + WALL + 0.01:
        # (across the wall at the back of the mouth, where the cut falls to the belly)
        return 0.03
    if xm < 0.78:
        return 0.09
    if xm < 2.5:
        return 0.26
    return 0.15


def rings(low, game=False):
    if game:
        return pick(rings(False), lambda xm: (*outline(xm), clip_y(xm)), GAME_TOL, game_longest,
                    keep=(CORNER, FUR_FROM, HIP[0]))
    xs = []
    x = BODY_FROM
    for until, step in ((0.78, 0.008), (2.6, 0.03), (3.85, 0.025), (BODY_TO, 0.012)):
        if low:
            step *= 3.6
        n = max(1, round((until - x) / step))
        for i in range(n):
            xs.append(x + (until - x) * i / n)
        x = until
    xs.append(BODY_TO)
    for extra in (CORNER, FUR_FROM, HIP[0]):
        if not any(abs(x - extra) < 1e-9 for x in xs):
            xs.append(extra)
    xs.sort()
    return xs


def teeth(m, low, game=False):
    """A caiman's teeth: conical, a little curved back, the upper ones hanging outside the lower jaw (they show
    with the mouth shut), bigger at the front and in the middle of the row."""
    count = TEETH
    sides, levels = 6, [(0.0, 1.0), (0.5, 0.7)]
    if low:
        count, sides, levels = 4, 3, [(0.0, 1.0)]
    if game:
        count, sides, levels = 7, 4, [(0.0, 1.0)]
    pitch = (TEETH_TO - TEETH_FROM) / count
    for i in range(count):
        f = i / count
        size = 1.0 + 0.35 * math.exp(-((f - 0.08) / 0.07) ** 2) + 0.25 * math.exp(-((f - 0.45) / 0.12) ** 2) - 0.25 * smooth(0.6, 1.0, f)
        for sx in (1.0, -1.0):
            xm = TEETH_FROM + pitch * (i + 0.25)
            lx, ly = section(xm, angle_at(xm, mouth_y(xm)))
            base = Vector((sx * (lx - TOOTH_RADIUS * 0.5), ly + TOOTH_LONG * 0.3, xm - HALF))
            cone(m, TOOTH_UP, base, Vector((sx * 0.22, -1.0, 0.12)).normalized(), TOOTH_RADIUS * size,
                 TOOTH_LONG * size * 1.25, sides, levels, "upper teeth")
            xm = TEETH_FROM + pitch * (i + 0.75)
            lx, ly = section(xm, angle_at(xm, mouth_y(xm) - GAP))
            x = lx - TOOTH_IN
            if x > TOOTH_RADIUS:
                base = Vector((sx * x, ly - TOOTH_LONG * 0.2, xm - HALF))
                cone(m, TOOTH_LOW, base, Vector((sx * 0.1, 1.0, 0.1)).normalized(), TOOTH_RADIUS * size,
                     TOOTH_LONG * size * 0.95, sides, levels, "lower teeth")


def tuft(m, part, root, normal, flow, long, wide, sides, extra, uvx, full):
    """A clump of wet fur: a shard rooted a little inside the skin at `root`, lying back along `flow`, lifted off
    the skin along `normal`; `wide` across its root (flat: half that deep). The full model's clumps bend once (a
    ring half way along); the game model's are three faces to the tip."""
    n = normal.normalized()
    f = (flow - n * flow.dot(n)).normalized()
    s = n.cross(f).normalized()
    base = root - n * (wide * 0.04)
    tip = base + n * (long * 0.17) + f * long
    rings = [(base, 1.0)]
    if full:
        rings.append((base + n * (long * 0.13) + f * (long * 0.5), 0.6))
    rows = []
    for centre, scale in rings:
        row = []
        for i in range(sides):
            a = TAU * i / sides + PI / 2.0
            # (a flat clump: its ridge lifted off the skin, its two edges just under it)
            lift = 0.32 if math.sin(a) > 0.0 else -0.22
            p = centre + (s * math.cos(a) * wide * 1.15 + n * abs(math.sin(a)) * lift * wide) * scale
            row.append(m.add(p, (uvx, 2.0 + (0.0 if centre is base else 0.5)), part, extra))
        rows.append((row, centre))
    tip_i = m.add(tip, (uvx, 3.0), part, extra)
    for r in range(len(rows) - 1):
        a, ca = rows[r]
        b, cb = rows[r + 1]
        for i in range(sides):
            j = (i + 1) % sides
            quad = (a[i], a[j], b[j], b[i])
            at = sum((m.verts[q] for q in quad), Vector()) * 0.25
            axis = (cb - ca).normalized()
            m.face(quad, at - (ca + axis * (at - ca).dot(axis)), "fur")
    last, cl = rows[-1]
    axis = (tip - cl).normalized()
    for i in range(sides):
        j = (i + 1) % sides
        at = (m.verts[last[i]] + m.verts[last[j]] + tip) / 3.0
        m.face((last[i], last[j], tip_i), at - (cl + axis * (at - cl).dot(axis)), "fur")


def skin_normal(xm, angle, sx):
    d = 0.004
    p = on_skin_a(xm, angle, sx)
    a = on_skin_a(xm + d, angle, sx) - on_skin_a(xm - d, angle, sx)
    b = on_skin_a(xm, angle + d, sx) - on_skin_a(xm, angle - d, sx)
    n = a.cross(b).normalized()
    up, down, _ = outline(xm)
    if n.dot(Vector((p.x, p.y - 0.5 * (up + down), 0.0))) < 0.0:
        n = -n
    return n


def on_skin_a(xm, angle, sx):
    x, y = section(xm, angle)
    return sculpt(xm, sx * x, y)


def body_fur(m, low, game=False):
    """The coat on the trunk: rows of clumps from the back of the head to the root of the tail, thickest and
    longest in a ruff round the neck and shoulders and along the ridge of the back, a fringe along the belly."""
    rng = random.Random(11)
    if low:
        dx, per_side, sides, wide, full = 0.22, 4, 3, 0.13, False
    elif game:
        dx, per_side, sides, wide, full = 0.12, 6, 3, 0.1, False
    else:
        dx, per_side, sides, wide, full = 0.05, 15, 4, 0.05, True
    count = 0
    xm = FUR_FROM + dx * 0.3
    row = 0
    while xm < FUR_TO:
        for k in range(per_side + 1):
            for sx in ((1.0,) if k == 0 else (1.0, -1.0)):
                share = k / per_side
                # (gathered a little to the ridge, the widest of the side and the belly's edge)
                a = PI * (0.04 + 0.9 * share) + (rng.random() - 0.5) * (0.6 * PI / per_side)
                if k == 0:
                    a = 0.0
                x = xm + (rng.random() - 0.5) * dx * 0.7 + (dx * 0.5 if row % 2 else 0.0)
                if x < FUR_FROM or x > FUR_TO:
                    continue
                # (not where the arms and legs come out of the body, under them)
                if a > 0.55 * PI and (abs(x - SHOULDER[0]) < 0.12 or abs(x - HIP[0]) < 0.14):
                    continue
                root = on_skin_a(x, a, sx)
                n = skin_normal(x, a, sx)
                long = 0.17
                long *= 1.0 + 0.7 * (1.0 - smooth(0.8, 1.25, x))
                long *= 1.0 + 0.25 * (1.0 - smooth(0.0, 0.3 * PI, a))
                long *= 1.0 + 0.3 * smooth(0.7 * PI, 0.85 * PI, a)
                long *= 1.0 - 0.35 * smooth(2.38, 2.68, x)
                long *= 0.8 + 0.4 * rng.random()
                if low:
                    long *= 1.25
                flow = Vector((0.0, -0.3 * smooth(0.25 * PI, 0.6 * PI, a), 1.0))
                tuft(m, BODY, root, n, flow, long, wide * (0.85 + 0.3 * rng.random()), sides, 0.0, x / LENGTH, full)
                count += 1
        xm += dx
        row += 1
    return count


def limb_fur(m, part, points, from_along, total, until, low, game, seed):
    """Clumps of fur round a limb from its root to `until` metres along it, lying down the limb."""
    rng = random.Random(seed)
    if low:
        step, around, sides, wide, full = 0.22, 3, 3, 0.1, False
    elif game:
        step, around, sides, wide, full = 0.12, 4, 3, 0.075, False
    else:
        step, around, sides, wide, full = 0.05, 9, 4, 0.045, True
    alongs = [from_along + a for a in along_of(points)]
    d = alongs[0] + step * 0.4
    ring = 0
    while d < min(until, alongs[-1]):
        i = 0
        while i < len(points) - 2 and d > alongs[i + 1]:
            i += 1
        f = (d - alongs[i]) / max(1e-6, alongs[i + 1] - alongs[i])
        centre = points[i] + (points[i + 1] - points[i]) * f
        axis = (points[i + 1] - points[i]).normalized()
        r = LIMB_R[id(points)](d)
        side = axis.cross(Vector((0.0, 1.0, 0.0)))
        if side.length < 1e-4:
            side = axis.cross(Vector((1.0, 0.0, 0.0)))
        side.normalize()
        other = side.cross(axis).normalized()
        for k in range(around):
            a = TAU * (k + 0.5 * (ring % 2)) / around + (rng.random() - 0.5) * 0.5
            n = side * math.cos(a) + other * math.sin(a)
            root = centre + n * r
            long = (0.12 if not low else 0.15) * (0.8 + 0.4 * rng.random())
            tuft(m, part, root, n, axis, long, wide * (0.85 + 0.3 * rng.random()), sides, d, d / total, full)
        d += step
        ring += 1


LIMB_R = {}


def radius_of(points, radii, from_along):
    alongs = [from_along + a for a in along_of(points)]

    def at(d):
        i = 0
        while i < len(points) - 2 and d > alongs[i + 1]:
            i += 1
        f = max(0.0, min(1.0, (d - alongs[i]) / max(1e-6, alongs[i + 1] - alongs[i])))
        return radii[i] + (radii[i + 1] - radii[i]) * f
    return at


def furred_tube(m, part, name, points, radii, sides, total, from_along, until, low, game, seed):
    tube(m, part, name, points, radii, sides, total, from_along)
    LIMB_R[id(points)] = radius_of(points, radii, from_along)
    limb_fur(m, part, points, from_along, total, until, low, game, seed)


def claws_on(m, part, start, way, across, count, finger, reach, total, a0, sides, low, game, down, size=1.0):
    """Fingers or toes side by side across `across` from `start`, each a short scaly tube and a hooked claw."""
    for i in range(count):
        f = (i / (count - 1) - 0.5) if count > 1 else 0.0
        s = start + across * f
        spread = (way + across.normalized() * f * 0.5).normalized()
        e = s + spread * finger
        tube(m, part, "fingers", [s, e], [0.022 * size, 0.017 * size], (4 if (low or game) else 8), total, a0)
        a1 = a0 + finger
        cone(m, part, e, spread, 0.016 * size, reach * size, 4 if (low or game) else 7,
             [(0.0, 1.0)] if (low or game) else [(0.0, 1.0), (0.5, 0.6)], "claws", 1.0,
             extra=lambda p, a1=a1, e=e: a1 + (p - e).length, bend=down)


def arm(m, sx, low, game=False):
    """An arm, tucked under the chest as it swims: the furred upper arm and forearm folded back, the scaly hand
    lying back along the belly with four hooked claws."""
    sides = 6 if game else (5 if low else 12)
    sh = P(SHOULDER[0], SHOULDER[1], sx * ARM_X)
    el = P(ELBOW[0], ELBOW[1], sx * (ARM_X + 0.08))
    wr = P(WRIST[0], WRIST[1], sx * (ARM_X + 0.07))
    total = 1.0
    upper = [sh, (sh + el) * 0.5, el]
    lower = [el, (el + wr) * 0.5, wr]
    d_el = (el - sh).length
    d_wr = d_el + (wr - el).length
    furred_tube(m, ARM, "arms", upper, [0.15, 0.13, 0.095], sides, total, 0.0, 9.0, low, game, 21 if sx > 0 else 22)
    furred_tube(m, ARM, "arms", lower, [0.095, 0.08, 0.06], sides, total, d_el, d_wr - 0.06, low, game, 23 if sx > 0 else 24)
    back = Vector((0.0, -0.08, 1.0)).normalized()
    palm_end = wr + back * 0.1
    tube(m, ARM, "hands", [wr, palm_end], [0.06, 0.058], sides, total, d_wr, flat=0.55, up=Vector((0.0, 1.0, 0.0)))
    claws_on(m, ARM, palm_end, back, Vector((0.1, 0.0, 0.0)), 2 if low else 4, 0.06, 0.075, total, d_wr + 0.1,
             sides, low, game, Vector((0.0, -1.0, 0.0)), 1.15)
    return d_el, d_wr


def leg(m, sx, low, game=False):
    """A hind leg, trailing back beside the tail as it swims: the furred thigh and shin, the scaly foot sole up,
    four toes with claws."""
    sides = 6 if game else (5 if low else 12)
    hp = P(HIP[0] - 0.04, HIP[1] + 0.04, sx * LEG_X)
    kn = P(KNEE[0], KNEE[1], sx * (LEG_X + 0.17))
    an = P(ANKLE[0], ANKLE[1], sx * (LEG_X + 0.16))
    total = 1.2
    d_kn = (kn - hp).length
    d_an = d_kn + (an - kn).length
    furred_tube(m, HIND, "legs", [hp, (hp + kn) * 0.5, kn], [0.24, 0.19, 0.12], sides, total, 0.0, 9.0, low, game, 31 if sx > 0 else 32)
    furred_tube(m, HIND, "legs", [kn, (kn + an) * 0.5, an], [0.11, 0.09, 0.07], sides, total, d_kn, d_an - 0.05, low, game, 33 if sx > 0 else 34)
    back = Vector((0.0, 0.02, 1.0)).normalized()
    mid = an + back * 0.14
    tube(m, HIND, "feet", [an, mid], [0.072, 0.07], sides, total, d_an, flat=0.5, up=Vector((0.0, 1.0, 0.0)))
    claws_on(m, HIND, mid, back, Vector((0.13, 0.0, 0.0)), 2 if low else 4, 0.075, 0.06, total, d_an + 0.14,
             sides, low, game, Vector((0.0, 1.0, 0.0)), 1.2)
    return d_kn, d_an


def make(name, low, game=False):
    m = Mesh()
    body(m, low, game)
    jaw(m, low, game)
    teeth(m, low, game)
    tufts = body_fur(m, low, game)
    joints = None
    for sx in (1.0, -1.0):
        eye(m, sx, low, game)
        a = arm(m, sx, low, game)
        b = leg(m, sx, low, game)
        joints = joints or (a, b)
    print("LIMBS %s AT_ELBOW %.4f AT_WRIST %.4f AT_KNEE %.4f AT_ANKLE %.4f; %d clumps on the body"
          % (name, joints[0][0], joints[0][1], joints[1][0], joints[1][1], tufts))
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
    bsdf.inputs["Base Color"].default_value = (0.3, 0.2, 0.11, 1.0)
    material.diffuse_color = (0.3, 0.2, 0.11, 1.0)
    mesh.materials.append(material)
    mesh.update()
    winding(name, mesh, m)
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
    views = [("left", (1, 0, 0), (0, 0, 0), 1.1 * f), ("right", (-1, 0, 0), (0, 0, 0), 1.1 * f),
             ("front", (0, 1, 0), (0, 0, 0), 0.5 * f), ("back", (0, -1, 0), (0, 0, 0), 0.5 * f),
             ("top", (0.001, 0, 1), (0, 0, 0), 1.1 * f), ("under", (0.001, 0, -1), (0, 0, 0), 1.1 * f),
             ("head", (0.8, 0.5, 0.2), (0, HALF - 0.3, 0), 1.0), ("chin", (0.6, 0.5, -0.6), (0, HALF - 0.3, 0), 1.0)]
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
    game = make(NAME + "_game", False, True)
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, NAME + ".glb"))
    export_one(low, os.path.join(OUT, NAME + "_lo.glb"))
    export_one(game, os.path.join(OUT, NAME + "_game.glb"))
    eye_frame()
    low.location.x = 1.2
    game.location.x = -1.2
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, NAME + ".blend"))
    low.location.x = 0.0
    game.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low, game])


if __name__ == "__main__":
    main()
