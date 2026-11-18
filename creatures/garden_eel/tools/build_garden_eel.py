"""Builds the garden eel (creatures/garden_eel) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/garden_eel/tools/build_garden_eel.py
    blender --background --python creatures/garden_eel/tools/build_garden_eel.py -- <preview folder>   # with pictures

Writes creatures/garden_eel/models/garden_eel.glb (the full model, for close looks), garden_eel_lo.glb (far
off) and garden_eel_colony.glb (about 230 triangles: the one GardenEelColony draws hundreds of), and the
editable creatures/garden_eel/tools/garden_eel.blend (this folder has a .gdignore). Each model is one still
mesh with one surface. It prints a WINDING line: the check that nothing is inside out.

A spotted garden eel, 0.4 m long and 1.2 cm thick. THE MODEL STANDS STRAIGHT UP, as if drawn out of its
burrow like a pencil: the shader (garden_eel.gdshaderinc) curls it into its question mark, sways it and slides
it down into the sand. In Godot space (metres, Y up): the tip of its snout at y = 0.3, its tail's tip at
y = -0.1 (a quarter of it never leaves the burrow), its back to +Z and its belly to -Z (so that, bowed
forward, it faces -Z with its back up), the origin at the mouth of its burrow, on the sand. `s` below is
metres from the tip of the snout, along the body.

- THE BODY: a thin round rod, a short blunt head a little thicker than the rest, the lower jaw reaching
  past the upper (the mouth is a groove that climbs towards the front), a tail drawn out to a point.
- A BIG EYE on each side of the head (a low dome); a tiny pectoral fin on each side behind the head.
- The colony model has no tail (it stops just under the sand), no eyes and no fins of its own: the shader
  draws its eyes.

What a point is, for the shader: UV2.y the part (0 body, 1 an eye, 2 a pectoral fin, 3 the inside of the mouth
and the throat, 4 a gill arch). UV, on the body: x how far along (0 snout to 1 tail), y 1 on the upper lip's
points along the line of the mouth; on an eye: x from its middle (0) to its rim (1), y 1 on the game model's (drawn
from the points' places); on a fin: x root to tip; on a gill arch: x which (0..1), y 0 its bar, 1 its filaments,
2 its rakers. UV2.x the jaw weight (more than 0 on the lower jaw and the floor of the mouth: how far it turns with
the jaw). COLOR (not on the colony's model): how far a lip's point slides onto the line of the mouth as it opens
(0.5 + metres / SNAP_RANGE). (The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.) The
shader finds where a point of the body is from its place in the still model.

2026-11-18: garden_eel_game.glb, the game model (Twilight Princess weight, about 1,700 triangles), and on the full,
low and game models a mouth that opens (`gape`) with the inside of the mouth, a throat and gill arches behind it;
the skin of the full and low models is left exactly as it was (see "the mouth that opens" below). The colony's
model is unchanged.

The numbers marked "as the shader has it" are in garden_eel.gdshaderinc too: change one, change the other.
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

LENGTH = 0.4
# As the shader has it: how high the tip of the snout stands in the still model.
TOP = 0.3
BODY, EYE, FIN = range(3)
TAU = math.tau

# The body's outline: metres from the tip of the snout, half its width, how far its back and its belly are
# from its middle line, and how far that middle line is pushed towards the back (+) or the belly (-).
PROFILE = [
    (0.0003, 0.0010, 0.0008, 0.0010, -0.0018),
    (0.002, 0.0030, 0.0024, 0.0028, -0.0010),
    (0.005, 0.0048, 0.0042, 0.0042, -0.0004),
    (0.009, 0.0060, 0.0055, 0.0052, 0.0),
    (0.014, 0.0066, 0.0062, 0.0058, 0.0),
    (0.022, 0.0064, 0.0062, 0.0060, 0.0),
    (0.035, 0.0060, 0.0060, 0.0060, 0.0),
    (0.30, 0.0060, 0.0060, 0.0060, 0.0),
    (0.36, 0.0048, 0.0048, 0.0048, 0.0),
    (0.39, 0.0028, 0.0028, 0.0028, 0.0),
    (0.3995, 0.0006, 0.0006, 0.0006, 0.0),
]
BODY_FROM = PROFILE[0][0]
BODY_TO = PROFILE[-1][0]

# As the shader has it: the line of the mouth, the eye.
MOUTH_TO = 0.0072
EYE_AT = (0.0088, 0.0012)
EYE_RADIUS = 0.0031


def mouth_d(s):
    return -0.0004 - 0.45 * s


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


def outline(s):
    """(half width, back, belly, middle) at `s`."""
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
        out.append(a + b)
    return out


def body_point(s, angle):
    """A point of the skin: `angle` round the body from the ridge of its back (0) by its left side (a
    quarter turn) to the middle of its belly (half a turn)."""
    wide, back, belly, middle = outline(s)
    c = math.cos(angle)
    sn = math.sin(angle)
    d = middle + c * (back if c >= 0.0 else belly)
    side = sn * wide
    # the mouth: a groove on each side of the head, climbing towards the front
    if s < MOUTH_TO + 0.001:
        groove = math.exp(-((d - mouth_d(s)) / 0.0005) ** 2) * smooth(0.0002, 0.001, s) * (1.0 - smooth(MOUTH_TO - 0.001, MOUTH_TO + 0.0005, s))
        side *= 1.0 - 0.1 * groove
    return Vector((side, TOP - s, d))


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.data = []
        self.out = []
        self.count = {}
        self.snap = {}

    def add(self, p, uv, part, own=0.0):
        self.verts.append(p)
        self.data.append(((uv[0], 1.0 - uv[1]), (own, 1.0 - part)))
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


def rings(kind):
    if kind == "colony":
        # (close together where it curls, and stopping just under the sand)
        return [0.0016, 0.006, 0.014, 0.027, 0.042, 0.058, 0.074, 0.09, 0.108, 0.13, 0.156, 0.188, 0.224, 0.262, 0.304]
    if kind == "game":
        # (close together on the head, a ring on the corner of the mouth, about a centimetre apart where it
        # curls, and few on the tail, which never leaves its burrow)
        xs = [BODY_FROM, 0.001, 0.002, 0.0032, 0.0045, 0.0058, MOUTH_TO, 0.0086, 0.0102, 0.012, 0.0145, 0.0175,
              0.021, 0.026, 0.032, 0.039, 0.047, 0.056]
        while xs[-1] < 0.29:
            xs.append(round(xs[-1] + 0.0098, 6))
        return xs + [0.3, 0.33, 0.37, BODY_TO]
    xs = []
    x = BODY_FROM
    for until, step in ((0.012, 0.0005), (0.04, 0.0015), (0.30, 0.003), (BODY_TO, 0.004)):
        if kind == "lo":
            step *= 4.0
        n = max(1, round((until - x) / step))
        for i in range(n):
            xs.append(x + (until - x) * i / n)
        x = until
    xs.append(BODY_TO)
    return xs


def line_angle(s):
    """How far round from the ridge of the back the line of the mouth is at `s` (radians; behind the corner
    of the mouth, where it is there)."""
    s = min(s, MOUTH_TO)
    _, back, belly, middle = outline(s)
    d = mouth_d(s) - middle
    return math.acos(max(-1.0, min(1.0, d / (back if d >= 0.0 else belly))))


def angle_of(kind, s, c, around):
    """How far round the body point `c` of a ring is. The game model's points are moved on the head: one
    each side on the line of the mouth and one just below it (the edge of the lower jaw), the others spread
    evenly between; behind the head they are even again."""
    if kind != "game":
        return c / around * TAU
    half = around // 2
    k = c if c <= half else around - c
    even = k / around * TAU
    line = max(0.45, min(math.pi - GAME_JAW_EDGE - 0.4, line_angle(s)))
    edge = line + GAME_JAW_EDGE
    moved = [0.0, line / 3.0, line * 2.0 / 3.0, line, edge, edge + (math.pi - edge) * 0.5, math.pi][k]
    a = even + (moved - even) * (1.0 - smooth(MOUTH_TO, MOUTH_TO + 0.007, s))
    return a if c <= half else TAU - a


def body(m, kind):
    around = {"full": 28, "lo": 10, "colony": 8, "game": 12}[kind]
    grid = []
    ss = rings(kind)
    for s in ss:
        grid.append([m.add(body_point(s, angle_of(kind, s, c, around)), (s / LENGTH, c / around), BODY) for c in range(around)])
    for r in range(len(grid) - 1):
        middle_d = outline(0.5 * (ss[r] + ss[r + 1]))[3]
        for c in range(around):
            n = (c + 1) % around
            quad = (grid[r][c], grid[r][n], grid[r + 1][n], grid[r + 1][c])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((middle.x, 0.0, middle.z - middle_d)), "body")
    ends = [(grid[0], 0.0, 1.0)]
    if kind != "colony":
        ends.append((grid[-1], LENGTH, -1.0))
    for row, s, way in ends:
        tip = m.add(Vector((0.0, TOP - s, outline(s)[3])), (s / LENGTH, 0.5), BODY)
        for c in range(around):
            m.face((tip, row[c], row[(c + 1) % around]), Vector((0.0, way, 0.0)), "body")


def on_skin(s, d, sx):
    _, back, belly, middle = outline(s)
    c = max(-1.0, min(1.0, (d - middle) / (back if d >= middle else belly)))
    return body_point(s, sx * math.acos(c))


def eye(m, sx, kind):
    """A low dome lying on the skin of the head."""
    spokes = {"full": 28, "lo": 10, "game": 12}[kind]
    steps = {"full": 8, "lo": 2, "game": 2}[kind]
    se, de = EYE_AT
    here = on_skin(se, de, sx)
    out = Vector((sx, 0.0, 0.12)).normalized()
    if kind == "full" and sx > 0.0:
        print("AS THE SHADER HAS IT: EEL_EYE_SKIN = vec3(%.6f, %.6f, %.6f); EEL_EYE_OUT = vec3(%.6f, %.6f, %.6f)"
              % (here.x, here.y, here.z, out.x, out.y, out.z))
    # (the game model's eye has few rings: its UV.y 1 tells the shader to draw it from the points' places, so
    # that its rings stay round)
    flag = 1.0 if kind == "game" else 0.0
    middle = m.add(here + out * 0.0011, (0.0, flag), EYE)
    last = None
    for k in range(1, steps + 1):
        r = k / steps
        row = []
        for sp in range(spokes):
            a = sp / spokes * TAU
            p = on_skin(se + math.cos(a) * EYE_RADIUS * r, de + math.sin(a) * EYE_RADIUS * r, sx)
            row.append(m.add(p + out * (0.001 * (1.0 - r * r) + 0.0001 * (1.0 - r)), (r, flag), EYE))
        for sp in range(spokes):
            n = (sp + 1) % spokes
            if last is None:
                m.face((middle, row[sp], row[n]), out, "eyes")
            else:
                m.face((last[sp], row[sp], row[n], last[n]), out, "eyes")
        last = row


def fin(m, sx, kind):
    """A pectoral fin: a tiny thin closed blade (two skins that meet at its edges), held out and back."""
    nt = 6 if kind == "full" else 2
    nu = 5 if kind == "full" else 2
    root = Vector((sx * 0.0052, TOP - 0.036, -0.001))
    span = Vector((sx * 0.75, -0.6, -0.1)).normalized()
    chord = Vector((0.0, -0.3, -1.0)).normalized()
    facing = span.cross(chord).normalized()
    for side in (1.0, -1.0):
        grid = []
        for ti in range(nt + 1):
            t = ti / nt * 0.97
            row = []
            for ui in range(nu + 1):
                u = ui / nu
                wide = 0.0034 * (1.0 - t) ** 0.6 * (0.6 + 0.4 * math.sin(math.pi * min(1.0, t + 0.5)))
                foil = 2.6 * math.sqrt(u) * (1.0 - u)
                p = root + span * (0.0065 * t) + chord * (wide * (u - 0.5)) + facing * (side * 0.0005 * (1.0 - t) * foil)
                row.append(m.add(p, (t, u), FIN))
            grid.append(row)
        for ti in range(nt):
            for ui in range(nu):
                m.face((grid[ti][ui], grid[ti][ui + 1], grid[ti + 1][ui + 1], grid[ti + 1][ui]), facing * side, "fins")


# --- the mouth that opens, and the gills (2026-11-18) ----------------------------------------------------------
# The user: "the fish should be able to open their mouths" (2026-11-17), then "The fish need modeled gills as
# well, well for relevant fish, so like when it opens its mouth wide you can see them" (2026-11-18). The skin of
# the full and low models is left exactly as it was (the same points, the same normals): the mouth opens in the
# shader. What a point of the body says, for that: UV2.x its jaw weight (more than 0 on the lower jaw: how far it
# turns with the jaw, 1 at the front, less towards the hinge at the corner of the mouth); UV.y 1 on the upper lip
# (the points of the skin along the line of the mouth, which stay put), 0 elsewhere. A face of the skin that has
# both (the strip of skin across the line of the mouth) is the closed mouth's seam: the shader leaves it out
# once the mouth opens, and behind it are the inside of the mouth (a roof from the upper lip, a floor from the
# lower jaw, part MOUTH), a short throat back past the gills, and four gill arches each side (part GILL).

MOUTH, GILL = 3, 4
# The roof of the mouth rises this far inside the upper lip, the floor sinks this far inside the lower jaw, and
# both keep this far inside the skin.
LIFT = 0.0012
DROP = 0.0008
MARGIN = 0.0007
# The game model's lower jaw: its edge, this far round below the line of the mouth (radians).
GAME_JAW_EDGE = 0.16
# The rims' slide onto the line of the mouth as it opens: the lower jaw's edge this far round below the line
# (radians); no slide longer than SNAP metres; written in COLOR as 0.5 + slide / SNAP_RANGE (as the shader has it).
SNAP_BELOW = 0.1
SNAP = 0.0014
SNAP_RANGE = 0.003
# How far in from the lips the cheeks are (of the way to the middle of the roof and the floor).
CHEEK = 0.3
# Where the gill arches are (metres behind the tip of the snout), and how far round the throat's wall they
# reach from its side (radians, either way).
GILLS_AT = [0.0125, 0.0153, 0.0181, 0.0209]
GILL_REACH = math.radians(40.0)
# The throat's hexagon: where its six points are round it (radians from its side, up).
THROAT_ROUND = [math.radians(a) for a in (20.0, 90.0, 160.0, 200.0, 270.0, 340.0)]


def jaw_weight(s):
    """How far a point of the lower jaw turns with it, as the shader has it (EEL_GAPE)."""
    return max(0.002, 1.0 - smooth(MOUTH_TO - 0.003, MOUTH_TO, s))


def face_safe(m, points, out, name):
    """m.face, but a quad with a point twice (two points that came out the same) is made a triangle."""
    kept = []
    for p in points:
        if p not in kept:
            kept.append(p)
    if len(kept) >= 3:
        m.face(tuple(kept), out, name)


def mouth(m, kind, nb):
    """The mouth's seam marked on the body (the first `nb` faces), the inside of the mouth and the throat.
    Returns how the throat runs, for the gills."""
    faces = m.faces[:nb]
    kinds = []
    for f in faces:
        c = sum((m.verts[i] for i in f), Vector()) / len(f)
        s = TOP - c.y
        if s < MOUTH_TO:
            kinds.append("J" if c.z < mouth_d(s) else "U")
        else:
            kinds.append("B")
    sets = {"J": set(), "U": set(), "B": set()}
    for f, k in zip(faces, kinds):
        sets[k].update(f)
    lip = (sets["J"] & sets["U"]) - sets["B"]
    corner = sets["J"] & sets["U"] & sets["B"]
    jaw = sets["J"] - sets["U"]
    weight = {i: jaw_weight(TOP - m.verts[i].y) for i in jaw}
    for i in set(i for f in faces for i in f):
        (u, _), (_, part) = m.data[i]
        m.data[i] = ((u, 0.0 if i in lip else 1.0), (weight.get(i, 0.0), part))
    seam = set(fi for fi, (f, k) in enumerate(zip(faces, kinds))
               if k == "J" and any(i in lip for i in f) and any(i in jaw for i in f))
    edges = {}
    for fi, f in enumerate(faces):
        for a, b in zip(f, f[1:] + f[:1]):
            edges.setdefault((min(a, b), max(a, b)), []).append(fi)
    lip_rim, jaw_rim = [], []
    for (a, b), fs in edges.items():
        if len(fs) != 2 or (fs[0] in seam) == (fs[1] in seam):
            continue
        # (with the seam's face beside it: a step of the roof or floor that stands across the body faces it)
        beside = fs[0] if fs[0] in seam else fs[1]
        beside = sum((m.verts[i] for i in faces[beside]), Vector()) / len(faces[beside])
        if a in jaw or b in jaw:
            jaw_rim.append((a, b, beside))
        else:
            lip_rim.append((a, b, beside))
    # The rims follow the grid of the skin, in steps. As the mouth opens the shader slides each rim point onto
    # the line of the mouth on its own ring (the upper lip's onto it, the lower jaw's a little below it), so
    # that the lips are clean lines: how far, in the point's COLOR (see SNAP).
    for rim, below in ((jaw_rim, SNAP_BELOW), (lip_rim, 0.0)):
        for i in set(i for e in rim for i in e[:2]):
            p = m.verts[i]
            s = TOP - p.y
            line = line_angle(s)
            if s >= MOUTH_TO or line < 0.35 or abs(p.x) < 1e-6:
                continue
            to = body_point(s, math.copysign(line + below, p.x))
            if (to - p).length < SNAP:
                m.snap[i] = to - p
    copies = {}

    def copy(i):
        w = weight.get(i, 0.0)
        if i not in copies:
            p = m.verts[i]
            # (a hair inside the skin's edge, so that with the mouth shut it never shows through the skin)
            _, _, _, middle = outline(TOP - p.y)
            inward = Vector((-p.x, 0.0, middle - p.z))
            q = p + inward.normalized() * 0.00006 if inward.length > 1e-9 else Vector(p)
            copies[i] = m.add(q, ((TOP - p.y) / LENGTH, 0.0), MOUTH, w)
            if i in m.snap:
                m.snap[copies[i]] = m.snap[i]
        return copies[i]

    mids = {}

    def mid(i, roof):
        p = m.verts[i]
        # (no nearer the tip of the snout than where the head is round enough to hold it)
        s = max(TOP - p.y, 0.0014)
        _, back, belly, middle = outline(s)
        # (the roof arches up to just under the top of the head, the floor sinks to just over the bottom of the
        # lower jaw: a mouth deep enough to see down into the throat)
        top, bottom = middle + back, middle - belly
        if roof:
            d = max(top - MARGIN, min(p.z + 0.0002, top - 0.0002))
        else:
            d = min(bottom + MARGIN, max(p.z - 0.0002, bottom + 0.0002))
        key = (round(s, 7), round(d, 7), roof)
        if key not in mids:
            mids[key] = m.add(Vector((0.0, TOP - s, d)), (s / LENGTH, 0.0), MOUTH, 0.0 if roof else weight.get(i, 0.0))
        return mids[key]

    def towards_axis(c):
        s = TOP - c.y
        return Vector((0.0, c.y, mouth_d(min(s, MOUTH_TO)) - 0.0002)) - c

    for rim, roof in ((lip_rim, True), (jaw_rim, False)):
        for a, b, beside in rim:
            quad = [copy(a), copy(b), mid(b, roof), mid(a, roof)]
            c = sum((m.verts[q] for q in quad), Vector()) / 4.0
            face_safe(m, quad, towards_axis(c) + Vector((0.0, (beside.y - c.y) * 3.0, 0.0)), "mouth")
    # The cheeks: each side, a strip from the roof to the floor CHEEK of the way in from the lips (on the
    # edges of their quads, so that it meets them), which stretches as the jaw turns down: from the side the
    # open mouth is dark inside, not a slit to see through; from the front it is open to the throat.
    for sx in (1.0, -1.0):
        rows = []
        for rim, roof in ((lip_rim, True), (jaw_rim, False)):
            # (on the sides of the head only: across the front the mouth stays open)
            on = sorted(set(i for e in rim for i in e[:2] if m.verts[i].x * sx > 0.6 * outline(TOP - m.verts[i].y)[0]),
                        key=lambda i: TOP - m.verts[i].y)
            row = []
            for i in on:
                a, b = m.verts[copy(i)], m.verts[mid(i, roof)]
                row.append(m.add(a + (b - a) * CHEEK, ((TOP - a.y) / LENGTH, 0.0), MOUTH, weight.get(i, 0.0)))
                if i in m.snap:
                    m.snap[row[-1]] = m.snap[i] * (1.0 - CHEEK)
            rows.append(row)
        top, low = rows
        if not top or not low:
            continue
        # (both edges from the same place to the same place along the head: no long slivers at its ends)
        start = max(TOP - m.verts[top[0]].y, TOP - m.verts[low[0]].y)
        top = [k for k in top if TOP - m.verts[k].y >= start - 1e-7]
        low = [k for k in low if TOP - m.verts[k].y >= start - 1e-7]
        if not top or not low:
            continue
        i = j = 0
        while i < len(top) - 1 or j < len(low) - 1:
            s_top = TOP - m.verts[top[i + 1]].y if i < len(top) - 1 else 1.0
            s_low = TOP - m.verts[low[j + 1]].y if j < len(low) - 1 else 1.0
            if s_top <= s_low:
                face_safe(m, [top[i], low[j], top[i + 1]], Vector((sx, 0.3, 0.0)), "mouth")
                i += 1
            else:
                face_safe(m, [top[i], low[j], low[j + 1]], Vector((sx, 0.3, 0.0)), "mouth")
                j += 1
    # The throat: from the back of the mouth (between the corners, the roof's and the floor's middles) back
    # past the gills, a hexagon that grows round, closed at its end.
    ends = []
    for rim in (lip_rim, jaw_rim):
        on = set(i for e in rim for i in e[:2])
        for sx in (1.0, -1.0):
            ends.append(max((i for i in on if m.verts[i].x * sx > 1e-6), key=lambda i: TOP - m.verts[i].y))
    l_left, l_right, j_left, j_right = ends
    ring0 = [copy(l_left), mid(l_left, True), copy(l_right), copy(j_right), mid(j_right, False), copy(j_left)]
    s0 = sum(TOP - m.verts[i].y for i in ring0) / 6.0
    d0 = sum(m.verts[i].z for i in ring0) / 6.0

    def throat(s):
        """(the middle of the throat's section, half its width, half its height) at `s`."""
        wide, back, belly, middle = outline(s)
        half = 0.18 * (back + belly)
        # (level with the back of the mouth, so that the gills are seen straight through it; but its floor
        # and roof no nearer the skin than MARGIN * 1.5)
        dc = max(min(d0, middle + back - half - MARGIN * 1.5), middle - belly + half + MARGIN * 1.5)
        return dc, 0.65 * wide, half

    steps = {"full": [0.0015, 0.004, 0.0075, 0.011, 0.015, 0.019], "lo": [0.003, 0.01, 0.019],
             "game": [0.002, 0.006, 0.011, 0.016, 0.019]}[kind]
    rows = [ring0]
    axis = [Vector((0.0, TOP - s0, d0))]
    for o in steps:
        s = s0 + o
        dc, a, b = throat(s)
        rows.append([m.add(Vector((a * math.cos(t), TOP - s, dc + b * math.sin(t))), (s / LENGTH, 0.0), MOUTH)
                     for t in THROAT_ROUND])
        axis.append(Vector((0.0, TOP - s, dc)))
    for r in range(len(rows) - 1):
        between = (axis[r] + axis[r + 1]) * 0.5
        for j in range(6):
            k = (j + 1) % 6
            quad = [rows[r][j], rows[r][k], rows[r + 1][k], rows[r + 1][j]]
            c = sum((m.verts[q] for q in quad), Vector()) / 4.0
            face_safe(m, quad, Vector((0.0, c.y, between.z)) - c, "throat")
    s_end = s0 + steps[-1] + 0.002
    dc, _, _ = throat(s_end)
    cap = m.add(Vector((0.0, TOP - s_end, dc)), (s_end / LENGTH, 0.0), MOUTH)
    for j in range(6):
        face_safe(m, [cap, rows[-1][j], rows[-1][(j + 1) % 6]], Vector((0.0, 1.0, 0.0)), "throat")
    return throat


def bar(m, path, radius, sides, uv, name):
    """A closed tube round `path` (a gill arch), capped at both ends."""
    ref = Vector((0.0, 1.0, 0.0))
    rows = []
    for i, p in enumerate(path):
        t = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
        a = t.cross(ref).normalized()
        b = t.cross(a).normalized()
        rows.append([m.add(p + (a * math.cos(k / sides * TAU) + b * math.sin(k / sides * TAU)) * radius, uv, GILL)
                     for k in range(sides)])
    for i in range(len(rows) - 1):
        axis = (path[i] + path[i + 1]) * 0.5
        for k in range(sides):
            j = (k + 1) % sides
            quad = (rows[i][k], rows[i][j], rows[i + 1][j], rows[i + 1][k])
            c = sum((m.verts[q] for q in quad), Vector()) / 4.0
            m.face(quad, c - axis, name)
    for row, end, before in ((rows[0], path[0], path[1]), (rows[-1], path[-1], path[-2])):
        tip = m.add(end + (end - before).normalized() * radius * 0.5, uv, GILL)
        for k in range(sides):
            m.face((tip, row[k], row[(k + 1) % sides]), end - before, name)


def blade(m, roots, tips, thick, uv, name):
    """A thin closed blade (two skins meeting at its edges) from `roots` to `tips` (two rows of points along
    an arch), one strip of quads a skin."""
    for side in (1.0, -1.0):
        grid = []
        for i, (r, t) in enumerate(zip(roots, tips)):
            along = (roots[min(i + 1, len(roots) - 1)] - roots[max(i - 1, 0)]).normalized()
            facing = along.cross((t - r).normalized()).normalized()
            middle = (r + t) * 0.5 + facing * (side * thick)
            grid.append((r, middle, t, facing))
        for i in range(len(grid) - 1):
            for u in range(2):
                quad = [grid[i][u], grid[i + 1][u], grid[i + 1][u + 1], grid[i][u + 1]]
                pts = [m.add(Vector(p), uv, GILL) for p in quad]
                m.face(tuple(pts), (grid[i][3] + grid[i + 1][3]) * (0.5 * side), name)


def gills(m, kind, throat):
    """Four gill arches each side of the throat, in its walls: each a curved bar (pale where it faces the
    mouth: the rakers), with a fringe of deep red filaments behind it; on the full model the rakers stand in
    front of it as a pale comb."""
    segments, sides, radius = {"full": (8, 6, 0.0003), "lo": (2, 3, 0.0004), "game": (3, 3, 0.00036)}[kind]
    for n, s in enumerate(GILLS_AT):
        dc, a, b = throat(s)
        for sx in (1.0, -1.0):
            path = []
            outs = []
            for i in range(segments + 1):
                t = -GILL_REACH + 2.0 * GILL_REACH * i / segments
                # (each arch leans back towards its top)
                path.append(Vector((sx * 0.8 * a * math.cos(t), TOP - s - 0.0006 * math.sin(t), dc + 0.8 * b * math.sin(t))))
                outs.append(Vector((sx * math.cos(t), 0.0, math.sin(t))))
            bar(m, path, radius, sides, (n / 3.0, 0.0), "gills")
            if kind == "lo":
                continue
            back = Vector((0.0, -1.0, 0.0))
            roots = [p + back * (radius * 0.6) for p in path]
            tips = []
            for i, (p, o) in enumerate(zip(path, outs)):
                # (the filaments' fringe: on the full model long and short by turns)
                long = 0.0011 if (kind == "game" or i % 2 == 0) else 0.0007
                tips.append(p + back * (radius + long) + o * 0.00025)
            blade(m, roots, tips, 0.00007, (n / 3.0, 1.0), "gills")
            if kind == "full":
                ahead = Vector((0.0, 1.0, 0.0))
                roots = [p + ahead * (radius * 0.6) for p in path]
                tips = [p + ahead * (radius + (0.00035 if i % 2 == 0 else 0.0002)) - o * 0.00015
                        for i, (p, o) in enumerate(zip(path, outs))]
                blade(m, roots, tips, 0.00005, (n / 3.0, 2.0), "gills")


def make(name, kind):
    m = Mesh()
    body(m, kind)
    nb = len(m.faces)
    if kind != "colony":
        for sx in (1.0, -1.0):
            eye(m, sx, kind)
            fin(m, sx, kind)
        throat = mouth(m, kind, nb)
        gills(m, kind, throat)
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
    if kind != "colony":
        # (the rims' slides as the mouth opens: see SNAP; everything else 0.5, no slide)
        colours = mesh.color_attributes.new(name="Col", type="FLOAT_COLOR", domain="POINT")
        for i in range(len(m.verts)):
            slide = m.snap.get(i, Vector((0.0, 0.0, 0.0))) / SNAP_RANGE
            colours.data[i].color = (0.5 + slide.x, 0.5 + slide.y, 0.5 + slide.z, 1.0)
        mesh.color_attributes.active_color = colours
        mesh.color_attributes.render_color_index = 0
    material = bpy.data.materials.get("garden_eel") or bpy.data.materials.new("garden_eel")
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.8, 0.78, 0.7, 1.0)
    material.diffuse_color = (0.8, 0.78, 0.7, 1.0)
    mesh.materials.append(material)
    for poly in mesh.polygons:
        # (the inside of the mouth and the throat flat-shaded: folded at the tip of the snout, smooth normals
        # there would point against their faces)
        poly.use_smooth = m.out[poly.index][1] not in ("mouth", "throat")
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    print("BUILT %s verts=%d tris=%d" % (name, len(mesh.vertices), tris))
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
    if obj.data.color_attributes:
        bpy.ops.export_scene.gltf(
            filepath=path, export_format="GLB", export_yup=True, use_selection=True,
            export_animations=False, export_texcoords=True,
            export_vertex_color="ACTIVE", export_all_vertex_colors=False,
        )
        return
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
    # (Blender space: it stands along Z, its back to -Y, its belly to +Y)
    top = (0, 0, 0.285)
    views = [("head_left", (1, 0, 0), top, 0.06), ("head_right", (-1, 0, 0), top, 0.06),
             ("head_belly", (0, 1, 0), top, 0.06), ("head_back", (0, -1, 0), top, 0.06),
             ("head_above", (0.001, 0, 1), top, 0.04), ("head_quarter", (0.7, 0.6, 0.3), top, 0.05),
             ("whole_left", (1, 0, 0), (0, 0, 0.1), 0.75)]
    for kind, obj in zip(("", "lo_", "colony_", "game_"), made):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if kind in ("lo_", "colony_") and view not in ("head_left", "whole_left"):
                continue
            offset = Vector(direction).normalized() * 40.0
            camera.data.ortho_scale = frame
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Z" if abs(direction[2]) < 0.9 else "Y").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % (kind, view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    made = [make("garden_eel", "full"), make("garden_eel_lo", "lo"), make("garden_eel_colony", "colony"),
            make("garden_eel_game", "game")]
    os.makedirs(OUT, exist_ok=True)
    for obj in made:
        export_one(obj, os.path.join(OUT, obj.name + ".glb"))
    # (in the .blend side by side: the full, the low, the colony's, the game model)
    for i, obj in enumerate(made):
        obj.location.x = 0.05 * i
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "garden_eel.blend"))
    for obj in made:
        obj.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, made)


if __name__ == "__main__":
    main()
