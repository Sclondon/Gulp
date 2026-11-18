"""Builds the moray eel (creatures/moray_eel) and exports it for Godot.

Run from anywhere:
    blender --background --python creatures/moray_eel/tools/build_moray_eel.py
    blender --background --python creatures/moray_eel/tools/build_moray_eel.py -- <preview folder>   # with pictures

Writes creatures/moray_eel/models/moray_eel.glb (the full model, near), moray_eel_game.glb (the game model, near
in a game: about 3,700 triangles, spent as a Twilight Princess figure spends them) and moray_eel_lo.glb (far off),
and the editable creatures/moray_eel/tools/moray_eel.blend (this folder has a .gdignore). Each model is one still mesh,
lying straight: MorayEel simulates its spine and the shader (moray_eel.gdshader) lays the mesh along it, opens
its jaw and draws its skin. It prints a WINDING line: the check that nothing is inside out.

A green moray (Gymnothorax funebris), 1.8 m long, after photographs on Wikimedia Commons (named in the
component's README):

- THE BODY: a long deep ribbon, taller than it is wide (0.15 m by 0.1 m at its thickest, behind the head),
  flattening to a blade at the tail. No paired fins at all.
- THE FIN: one tall fleshy membrane: it rises on the nape (well before the gill opening), runs the whole back
  about 5 cm high, goes round the tail tip and comes forward under the body as the anal fin to the vent, a
  little before the middle. Skin and fin are one surface.
- THE HEAD: a blunt snout, low at the front and rising steeply to a swollen nape; the mouth cut far back
  behind the eye (the eye sits over its middle); a heavy lower jaw, which is hinged (the shader swings it); a
  hollow mouth with needle teeth round both jaws (longest at the front) and three long ones down the middle
  of the palate; small round eyes high on the sides; two tube nostrils at the tip of the snout and two low
  rimmed ones over the eyes.

What a point is, for the shader: vertex colour red the part (0 skin, 0.2 inside the mouth, 0.4 a tooth, 0.6
an eye, 0.8 a hole: the inside of a nostril); green how much it swings with the lower jaw (0..1); blue how far
out on the fin it is (0 the body, 1 the fin's edge). UV.x round the body (0 at the right corner of the mouth,
over the back to 0.5 at the left, under the belly to 1), UV.y how far along (0 snout, 1 tail tip); on an eye
UV.y is 0 at the middle of the pupil to 1 at its rim under the skin, on a tooth 0 its root to 1 its point.
(The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.)

Everything here is in Godot space (metres, Y up, the snout at the origin, the tail towards +Z, so that it
faces -Z) until it is written out. LENGTH, MOUTH and HINGE are in moray_eel.gd and the shader too: change
one, change the others.
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

LENGTH = 1.8
# How far back the corner of the mouth is (the jaw's hinge), and how high.
MOUTH = 0.115
HINGE_Y = -0.007
EYE_AT = 0.055
GILL_AT = 0.26

SKIN, MOUTH_IN, TOOTH, EYE, HOLE = 0.0, 0.2, 0.4, 0.6, 0.8


def to_b(p):
    return Vector((p.x, -p.z, p.y))


# Which model is being built: FULL (close pictures), LOW (far off) or GAME (the game model: a Twilight Princess
# weight, spent on the head, the mouth and the eye, and on the fin's outline; few across the long flanks).
FULL, LOW, GAME = 0, 1, 2


def pick(lod, full, low, game):
    """The number for this model. (`lod` may be False or True, for FULL and LOW.)"""
    return (full, low, game)[int(lod)]


def smooth(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


class Curve:
    """A smooth line through points that never overshoots them (monotone cubic)."""

    def __init__(self, points):
        self.x = [p[0] for p in points]
        self.y = [p[1] for p in points]
        n = len(points)
        d = [(self.y[i + 1] - self.y[i]) / (self.x[i + 1] - self.x[i]) for i in range(n - 1)]
        m = [d[0]] + [0.0 if d[i - 1] * d[i] <= 0.0 else 0.5 * (d[i - 1] + d[i]) for i in range(1, n - 1)] + [d[-1]]
        for i in range(n - 1):
            if d[i] == 0.0:
                m[i] = m[i + 1] = 0.0
            else:
                a, b = m[i] / d[i], m[i + 1] / d[i]
                if a * a + b * b > 9.0:
                    t = 3.0 / math.sqrt(a * a + b * b)
                    m[i], m[i + 1] = t * a * d[i], t * b * d[i]
        self.m = m

    def __call__(self, x):
        x = min(max(x, self.x[0]), self.x[-1])
        i = 0
        while i < len(self.x) - 2 and x > self.x[i + 1]:
            i += 1
        h = self.x[i + 1] - self.x[i]
        t = (x - self.x[i]) / h
        return ((2 * t ** 3 - 3 * t ** 2 + 1) * self.y[i] + (t ** 3 - 2 * t ** 2 + t) * h * self.m[i]
                + (-2 * t ** 3 + 3 * t ** 2) * self.y[i + 1] + (t ** 3 - t ** 2) * h * self.m[i + 1])


# The body without its fin, along its length: how far its back is over its middle line, how far its belly
# under it, and half its width.
TOP = Curve([(0, 0), (0.004, 0.016), (0.012, 0.024), (0.03, 0.031), (0.055, 0.038), (0.085, 0.047), (0.115, 0.057),
             (0.16, 0.068), (0.22, 0.074), (0.30, 0.076), (0.45, 0.076), (0.9, 0.072), (1.3, 0.060), (1.6, 0.040),
             (1.72, 0.02), (1.77, 0.008), (1.8, 0.0)])
BOT = Curve([(0, 0), (0.004, 0.014), (0.012, 0.022), (0.03, 0.029), (0.055, 0.035), (0.085, 0.043), (0.115, 0.052),
             (0.16, 0.062), (0.22, 0.069), (0.30, 0.072), (0.45, 0.072), (0.9, 0.068), (1.3, 0.056), (1.6, 0.036),
             (1.72, 0.018), (1.77, 0.007), (1.8, 0.0)])
WIDE = Curve([(0, 0), (0.004, 0.014), (0.012, 0.021), (0.03, 0.027), (0.055, 0.031), (0.085, 0.035), (0.115, 0.039),
              (0.16, 0.044), (0.22, 0.047), (0.30, 0.048), (0.45, 0.048), (0.9, 0.042), (1.3, 0.030), (1.6, 0.015),
              (1.72, 0.007), (1.77, 0.004), (1.8, 0.002)])
# The fin's height: over the back, and under the belly behind the vent.
FIN_BACK = Curve([(0, 0), (0.12, 0), (0.17, 0.012), (0.30, 0.04), (0.5, 0.05), (1.3, 0.05), (1.6, 0.046), (1.72, 0.04),
                  (1.77, 0.03), (1.79, 0.018), (1.8, 0.0)])
FIN_BELLY = Curve([(0, 0), (0.84, 0), (0.9, 0.01), (1.0, 0.028), (1.3, 0.032), (1.6, 0.034), (1.72, 0.033), (1.77, 0.026),
                   (1.79, 0.016), (1.8, 0.0)])
# The line of the mouth, carried on behind its corner as the seam between the upper and lower halves.
SEAM = Curve([(0, 0), (0.02, -0.002), (0.06, -0.004), (MOUTH, HINGE_Y), (0.17, HINGE_Y), (0.36, 0.0), (1.8, 0.0)])


def body_point(s, phi):
    """The body's outline at `s`: `phi` round from the top (0) by the right side to the bottom (pi)."""
    c = math.cos(phi)
    return WIDE(s) * math.sin(phi), (TOP(s) if c >= 0.0 else BOT(s)) * c


def seam_angle(s):
    y = SEAM(s)
    return math.acos(min(max(y / (TOP(s) if y >= 0.0 else BOT(s)), -1.0), 1.0))


def half_side(s, upper, nb, nf):
    """The right side of the upper (or lower) half at `s`, from the seam to the middle of the back (or
    belly): [x, y, how far out on the fin]. The body's arc, then the fin: a membrane thick at its foot and
    thin at its edge; where there is no fin those points lie on the body."""
    wide = WIDE(s)
    fin = FIN_BACK(s) if upper else FIN_BELLY(s)
    foot = min(0.0055, 0.6 * wide)
    foot_angle = math.asin(min(foot / max(wide, 1e-6), 1.0))
    start = seam_angle(s)
    end = foot_angle if upper else math.pi - foot_angle
    middle = 0.0 if upper else math.pi
    sign = 1.0 if upper else -1.0
    points = []
    for k in range(nb + 1):
        x, y = body_point(s, start + (end - start) * k / nb)
        points.append((x, y, 0.0))
    foot_y = body_point(s, end)[1]
    blend = smooth(0.0, 0.012, fin)
    for j in range(1, nf + 1):
        q = j / nf
        ex, ey = body_point(s, end + (middle - end) * q)
        fx = (0.0012 + (foot - 0.0012) * (1.0 - q) ** 2) if j < nf else 0.0
        fy = foot_y + sign * (fin * q + (0.0012 if j == nf else 0.0))
        points.append((ex + (fx - ex) * blend, ey + (fy - ey) * blend, q * blend))
    return points


class Mesh:
    def __init__(self):
        self.verts = []
        self.uv = []
        self.colour = []
        self.faces = []
        self.group = []

    def v(self, x, y, z, u=0.0, v=0.0, part=SKIN, jaw=0.0, fin=0.0):
        self.verts.append(Vector((x, y, z)))
        self.uv.append((u, 1.0 - v))
        self.colour.append((part, jaw, fin, 1.0))
        return len(self.verts) - 1

    def face(self, corners, group, hint=None, flip=False):
        """A face. With `hint`, it is wound to face that way; otherwise as given (turned over by `flip`)."""
        corners = [c for i, c in enumerate(corners) if (self.verts[c] - self.verts[corners[i - 1]]).length > 1e-7]
        if len(corners) < 3:
            return
        normal = Vector((0.0, 0.0, 0.0))
        for i in range(1, len(corners) - 1):
            normal += (self.verts[corners[i]] - self.verts[corners[0]]).cross(self.verts[corners[i + 1]] - self.verts[corners[0]])
        if normal.length < 1e-12:
            return
        if (hint is not None and normal.dot(hint) < 0.0) or (hint is None and flip):
            corners = corners[::-1]
        self.faces.append(corners)
        self.group.append(group)

    def strip(self, a, b, group, hint=None, flip=False):
        """Faces between two rows of points of the same length."""
        for k in range(len(a) - 1):
            self.face([a[k], a[k + 1], b[k + 1], b[k]], group, hint, flip)

    def fan(self, pole, row, group, hint):
        for k in range(len(row) - 1):
            self.face([pole, row[k], row[k + 1]], group, hint)


def jaw_weight(s, y):
    """How much a point of the lower half swings with the jaw: all of it before the hinge, fading behind
    it, and not at all at the seam."""
    if s < MOUTH:
        return 1.0
    return smooth(0.0, 0.03, SEAM(s) - y) * (1.0 - smooth(MOUTH, MOUTH + 0.10, s))


def stations(low):
    """Where the rings are, snout to tail, and which is the one at the corner of the mouth."""
    first = 0.0012
    n_mouth = pick(low, 26, 8, 12)
    out = [first + (MOUTH - first) * (j / n_mouth) ** 1.5 for j in range(n_mouth + 1)]
    # (the game model: close rings over the head, where the nape rises and the fin begins; far apart along the
    # body, whose outline runs straight; close again where the tail and its fin round off)
    for to, step in ((0.34, pick(low, 0.0075, 0.03, 0.025)), (1.72, pick(low, 0.0125, 0.046, 0.06)),
                     (1.797, pick(low, 0.0097, 0.026, 0.016))):
        n = max(1, round((to - out[-1]) / step))
        from_s = out[-1]
        out += [from_s + (to - from_s) * (i + 1) / n for i in range(n)]
    return out, n_mouth


def inner_lip(s):
    """How far in and up the inner edge of the lip is from the seam."""
    k = smooth(0.0, 0.02, MOUTH - s) * smooth(0.0, 0.008, s)
    return 0.004 * k, 0.0025 * k


def body(m, low):
    nb, nf, n_in = pick(low, (14, 7, 9), (4, 2, 3), (5, 2, 3))
    rings, at_mouth = stations(low)
    upper = []
    lower = []
    lips = []   # for each ring of the mouth: [upper right, upper left, lower right, lower left] inner lip points
    palate = []
    floor = []
    for j, s in enumerate(rings):
        v = s / LENGTH
        up_side = half_side(s, True, nb, nf)
        lo_side = half_side(s, False, nb, nf)
        count = 2 * (nb + nf)
        up = []
        for k, (x, y, fin) in enumerate(up_side + [(-x, y, fin) for x, y, fin in reversed(up_side[:-1])]):
            up.append(m.v(x, y, s, 0.5 * k / count, v, SKIN, 0.0, fin))
        lo_points = [(-x, y, fin) for x, y, fin in lo_side] + list(reversed(lo_side[:-1]))
        lo = []
        for k, (x, y, fin) in enumerate(lo_points):
            if j >= at_mouth and k == 0:
                lo.append(up[-1])
            elif j >= at_mouth and k == count:
                lo.append(up[0])
            else:
                lo.append(m.v(x, y, s, 0.5 + 0.5 * k / count, v, SKIN, jaw_weight(s, y), fin))
        upper.append(up)
        lower.append(lo)
        if j <= at_mouth:
            # the lips and the hollow of the mouth
            sx, sy = up_side[0][0], up_side[0][1]
            dx, dy = inner_lip(s)
            dx = min(dx, 0.4 * sx)
            ix = sx - dx
            lips.append([m.v(ix, sy + dy, s, 0.0, v), m.v(-ix, sy + dy, s, 0.5, v),
                         m.v(ix, sy - dy, s, 1.0, v, SKIN, 1.0), m.v(-ix, sy - dy, s, 0.5, v, SKIN, 1.0)])
            fade = smooth(0.0, 0.035, MOUTH - s)
            high = min(0.45 * TOP(s), 0.016) * fade
            deep = min(0.45 * BOT(s), 0.014) * fade
            row_up = []
            row_lo = []
            for i in range(n_in + 1):
                across = 1.0 - 2.0 * i / n_in
                row_up.append(m.v(ix * across, sy + dy + high * (1.0 - across * across), s, 0.5 * i / n_in, v, MOUTH_IN))
                row_lo.append(m.v(ix * across, sy - dy - deep * (1.0 - across * across), s, 0.5 * i / n_in, v, MOUTH_IN, 1.0))
            palate.append(row_up)
            floor.append(row_lo)
    for j in range(len(rings) - 1):
        m.strip(upper[j], upper[j + 1], "skin")
        m.strip(lower[j], lower[j + 1], "skin")
    down = Vector((0.0, -1.0, 0.0))
    for j in range(at_mouth):
        a, b = lips[j], lips[j + 1]
        m.face([upper[j][0], a[0], b[0], upper[j + 1][0]], "lip_upper", down)
        m.face([upper[j][-1], a[1], b[1], upper[j + 1][-1]], "lip_upper", down)
        m.face([lower[j][-1], a[2], b[2], lower[j + 1][-1]], "lip_lower", -down)
        m.face([lower[j][0], a[3], b[3], lower[j + 1][0]], "lip_lower", -down)
        m.strip(palate[j], palate[j + 1], "palate", down)
        m.strip(floor[j], floor[j + 1], "floor", -down)
    # the tips of the jaws, closed to a point each
    s = rings[0]
    front = Vector((0.0, 0.0, -1.0))
    for sign, half, lip, inside, jaw in ((1.0, upper[0], (lips[0][0], lips[0][1]), palate[0], 0.0),
                                         (-1.0, lower[0], (lips[0][2], lips[0][3]), floor[0], 1.0)):
        y = SEAM(0.0) + sign * 0.0004
        pole = m.v(0.0, y, 0.0, 0.25, 0.0, SKIN, jaw)
        m.fan(pole, half, "skin_tip", front)
        ends = (half[0], half[-1]) if sign > 0.0 else (half[-1], half[0])
        m.face([pole, ends[0], lip[0]], "lip_tip", down * sign)
        m.face([pole, ends[1], lip[1]], "lip_tip", down * sign)
        pole_in = m.v(0.0, y, 0.0, 0.25, 0.0, MOUTH_IN, jaw)
        m.fan(pole_in, inside, "mouth_tip", down * sign)
    # the tail's tip
    last = len(rings) - 1
    y = 0.5 * (m.verts[upper[last][nb + nf]].y + m.verts[lower[last][nb + nf]].y)
    pole = m.v(0.0, y, LENGTH, 0.25, 1.0, SKIN, 0.0, 1.0)
    m.fan(pole, upper[last] + lower[last][1:], "skin_tail", -front)
    return rings, lips, palate


def cone(m, base, way, long, radius, sides, jaw):
    """A tooth: a needle from `base` along `way`."""
    way = way.normalized()
    side = way.cross(Vector((1.0, 0.0, 0.0)))
    if side.length < 0.1:
        side = way.cross(Vector((0.0, 0.0, 1.0)))
    side.normalize()
    other = way.cross(side)
    tip = base + way * long
    ring = []
    for k in range(sides):
        a = math.tau * k / sides
        p = base + (side * math.cos(a) + other * math.sin(a)) * radius
        ring.append(m.v(p.x, p.y, p.z, k / sides, 0.0, TOOTH, jaw))
    top = m.v(tip.x, tip.y, tip.z, 0.5, 1.0, TOOTH, jaw)
    for k in range(sides):
        a, b = ring[k], ring[(k + 1) % sides]
        mid = (m.verts[a] + m.verts[b]) * 0.5
        m.face([a, b, top], "teeth", mid - (base + way * way.dot(mid - base)))


def teeth(m, low):
    sides = pick(low, 6, 4, 3)
    n_up = pick(low, 17, 8, 10)
    n_lo = pick(low, 15, 7, 9)
    for count, upper in ((n_up, True), (n_lo, False)):
        sign = -1.0 if upper else 1.0
        for i in range(count):
            s = 0.007 + (MOUTH - 0.022) * ((i + (0.0 if upper else 0.5)) / count) ** 1.15
            x = WIDE(s) * math.sin(seam_angle(s))
            dx, dy = inner_lip(s)
            x -= min(dx, 0.4 * x) + 0.0012
            # longest at the front; every third a little longer
            long = 0.0042 + 0.0062 * (1.0 - smooth(0.0, 0.05, s)) + (0.0015 if i % 3 == 0 else 0.0)
            if not upper:
                long *= 0.85
            for side in (1.0, -1.0):
                base = Vector((side * x, SEAM(s) - sign * (dy + 0.0006), s))
                cone(m, base, Vector((-0.12 * side, sign, 0.3)), long, 0.0011 + 0.08 * long, sides, 0.0 if upper else 1.0)
    # the long teeth down the middle of the palate
    for s in (0.022, 0.034, 0.047):
        fade = smooth(0.0, 0.035, MOUTH - s)
        dy = inner_lip(s)[1]
        high = SEAM(s) + dy + min(0.45 * TOP(s), 0.016) * fade
        cone(m, Vector((0.0, high + 0.001, s)), Vector((0.0, -1.0, 0.4)), 0.0115, 0.002, sides, 0.0)


def skin_at(s, phi):
    """A point on the head's skin and the way it faces."""
    x, y = body_point(s, phi)
    c = math.cos(phi)
    high = TOP(s) if c >= 0.0 else BOT(s)
    normal = Vector((math.sin(phi) / max(WIDE(s), 1e-6), c / max(high, 1e-6), 0.0))
    ahead = Vector(body_point(s + 0.002, phi) + (0.002,)) - Vector((x, y, 0.0))
    normal -= ahead.normalized() * normal.dot(ahead.normalized())
    return Vector((x, y, s)), normal.normalized()


def eye(m, side, low):
    """A small round eye, high on the side over the middle of the mouth, sunk a little into the head."""
    at, out = skin_at(EYE_AT, math.radians(54.0))
    out = (out + Vector((0.0, 0.0, -0.18))).normalized()
    at.x *= side
    out.x *= side
    radius = 0.0086
    middle = at - out * 0.006
    a = out.cross(Vector((0.0, 1.0, 0.0))).normalized()
    b = out.cross(a)
    n_lat, n_lon = pick(low, (9, 20), (4, 8), (5, 24))
    reach = math.radians(112.0)
    pole = m.v(*(middle + out * radius), 0.0, 0.0, EYE)
    rows = []
    # (the game model's rows close together over the part that shows, out of the skin, and then one wide step
    # down under it)
    polars = [reach * i / n_lat for i in range(1, n_lat + 1)]
    if low == GAME:
        polars = [math.radians(d) for d in (14.0, 28.0, 40.0, 54.0, 112.0)]
    for i, polar in enumerate(polars, 1):
        row = []
        for k in range(n_lon + 1):
            around = math.tau * k / n_lon
            p = middle + (out * math.cos(polar) + (a * math.cos(around) + b * math.sin(around)) * math.sin(polar)) * radius
            row.append(m.v(p.x, p.y, p.z, k / n_lon, i / n_lat if low != GAME else polar / reach, EYE))
        rows.append(row)
    for k in range(n_lon):
        m.face([pole, rows[0][k], rows[0][k + 1]], "eyes", m.verts[rows[0][k]] - middle)
    for i in range(n_lat - 1):
        for k in range(n_lon):
            quad = [rows[i][k], rows[i][k + 1], rows[i + 1][k + 1], rows[i + 1][k]]
            m.face(quad, "eyes", m.verts[quad[0]] + m.verts[quad[2]] - middle * 2.0)


def nostril(m, base, way, long, wide, low):
    """A tube nostril: its wall, a rim, and the dark hole in its end."""
    way = way.normalized()
    a = way.cross(Vector((0.0, 1.0, 0.0)))
    if a.length < 0.1:
        a = way.cross(Vector((1.0, 0.0, 0.0)))
    a.normalize()
    b = way.cross(a)
    sides = pick(low, 12, 6, 6)
    v = base.z / LENGTH
    # [how far along, how wide, the part]
    shape = [(-0.003, wide * 1.15, SKIN), (long * 0.6, wide * 0.92, SKIN), (long, wide, SKIN),
             (long, wide * 0.62, HOLE), (long - wide * 1.2, wide * 0.4, HOLE)]
    rows = []
    for along, radius, part in shape:
        row = []
        for k in range(sides + 1):
            around = math.tau * k / sides
            p = base + way * along + (a * math.cos(around) + b * math.sin(around)) * radius
            row.append(m.v(p.x, p.y, p.z, 0.2, v, part))
        rows.append(row)
    for i in range(len(rows) - 1):
        for k in range(sides):
            quad = [rows[i][k], rows[i][k + 1], rows[i + 1][k + 1], rows[i + 1][k]]
            mid = (m.verts[quad[0]] + m.verts[quad[2]]) * 0.5
            out = mid - (base + way * way.dot(mid - base))
            # (the wall faces out from the tube, its end the way the tube points, the hole in towards its middle)
            hint = out if i < 2 else (way if i == 2 else way * 0.5 - out)
            m.face(quad, "nostrils", hint)
    end = base + way * (long - wide * 1.2)
    pole = m.v(end.x, end.y, end.z, 0.2, v, HOLE)
    m.fan(pole, rows[-1], "nostrils", way)


def make(name, low):
    m = Mesh()
    body(m, low)
    teeth(m, low)
    for side in (1.0, -1.0):
        eye(m, side, low)
        at, out = skin_at(0.007, math.radians(50.0))
        nostril(m, Vector((side * at.x, at.y, at.z)), Vector((side * 0.45, 0.3, -1.0)), 0.011, 0.0027, low)
        at, out = skin_at(0.043, math.radians(24.0))
        nostril(m, Vector((side * at.x, at.y, at.z)), Vector((side * out.x, out.y, -0.2)), 0.002, 0.0026, low)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) for p in m.verts], [], m.faces)
    # (every layer made first, then each looked up by name: making one moves the others)
    mesh.uv_layers.new(name="UVMap")
    mesh.color_attributes.new(name="Color", type="FLOAT_COLOR", domain="CORNER")
    uv = mesh.uv_layers["UVMap"].data
    colour = mesh.color_attributes["Color"].data
    for poly in mesh.polygons:
        for corner, vi in enumerate(poly.vertices):
            uv[poly.loop_start + corner].uv = m.uv[vi]
            colour[poly.loop_start + corner].color = m.colour[vi]
    mesh.color_attributes.active_color = mesh.color_attributes["Color"]
    mesh.color_attributes.render_color_index = mesh.color_attributes.find("Color")
    material = bpy.data.materials.get("moray") or bpy.data.materials.new("moray")
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.36, 0.45, 0.1, 1.0)
    material.diffuse_color = (0.36, 0.45, 0.1, 1.0)
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
    """Nothing inside out (Blender's front is the side a face's normal is on): the skin faces away from
    the body's middle line (a face of the fin, away from the plane down the middle of the eel); the tips
    of the snout and tail face forward and back; the lips and the hollow of the mouth face into the mouth.
    Teeth, eyes and nostrils are wound from their own middles as they are built."""
    counts = {}
    for f, poly in enumerate(mesh.polygons):
        group = m.group[f]
        normal = Vector((poly.normal.x, poly.normal.z, -poly.normal.y))
        middle = Vector((poly.center.x, poly.center.z, -poly.center.y))
        if group == "skin":
            fin = sum(m.colour[v][2] for v in poly.vertices) / len(poly.vertices)
            s = min(max(middle.z, 0.0), LENGTH)
            if fin > 0.15:
                side = normal.x * middle.x
            else:
                side = normal.dot(Vector((middle.x, middle.y - 0.5 * (TOP(s) - BOT(s)), 0.0)))
        elif group == "skin_tip":
            side = -normal.z
        elif group == "skin_tail":
            side = normal.z
        elif group in ("lip_upper", "palate"):
            side = -normal.y
        elif group in ("lip_lower", "floor"):
            side = normal.y
        else:
            continue
        bad, all_ = counts.get(group, (0, 0))
        counts[group] = (bad + (1 if side <= 0.0 else 0), all_ + 1)
    wrong = sum(bad for bad, _ in counts.values())
    told = ", ".join("%s %d/%d wrong" % (group, bad, all_) for group, (bad, all_) in sorted(counts.items()))
    print("WINDING %s: %s: %s" % (name, "ok" if wrong == 0 else "INSIDE OUT", told))


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
    scene.render.resolution_x, scene.render.resolution_y = 1400, 700
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.05, 0.1, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    # (Blender space: the eel lies along -Y from its snout at the origin, Z up)
    whole = (0, -0.9, 0)
    head = (0, -0.1, 0)
    views = [("right", (1, 0, 0), whole, 2.0), ("left", (-1, 0, 0), whole, 2.0), ("top", (0, -0.001, 1), whole, 2.0),
             ("under", (0, -0.001, -1), whole, 2.0), ("front", (0, 1, 0.0), (0, 0, 0), 0.5), ("back", (0, -1, 0), (0, 0, 0), 0.5),
             ("head_right", (1, 0.0, 0.0), head, 0.42), ("head_front", (0.6, 1, 0.3), head, 0.42),
             ("head_top", (0, -0.001, 1), head, 0.42), ("head_under", (0.3, 0.5, -1), head, 0.42),
             ("tail", (1, 0, 0.2), (0, -1.6, 0), 0.6)]
    for low, obj in ((FULL, made[0]), (LOW, made[1]), (GAME, made[2])):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if low == LOW and view not in ("right", "head_front"):
                continue
            offset = Vector(direction).normalized() * 40.0
            camera.data.ortho_scale = frame
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % (("", "lo_", "game_")[low], view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    at, out = skin_at(EYE_AT, math.radians(54.0))
    out = (out + Vector((0.0, 0.0, -0.18))).normalized()
    middle = at - out * 0.006
    print("EYE moray_eel (the right eye, Godot metres, for the shader's cartoon eye): centre=(%.5f, %.5f, %.5f) out=(%.4f, %.4f, %.4f)" % (
        middle.x, middle.y, middle.z, out.x, out.y, out.z))
    full = make("moray_eel", FULL)
    low = make("moray_eel_lo", LOW)
    game = make("moray_eel_game", GAME)
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, "moray_eel.glb"))
    export_one(low, os.path.join(OUT, "moray_eel_lo.glb"))
    export_one(game, os.path.join(OUT, "moray_eel_game.glb"))
    low.location.x = 0.6
    game.location.x = 1.2
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "moray_eel.blend"))
    low.location.x = 0.0
    game.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low, game])


if __name__ == "__main__":
    main()
