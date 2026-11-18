"""Builds the northern pike (creatures/northern_pike) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/northern_pike/tools/build_northern_pike.py
    blender --background --python creatures/northern_pike/tools/build_northern_pike.py -- <preview folder>

Writes creatures/northern_pike/models/northern_pike.glb (the full model, for one seen close),
northern_pike_game.glb (the game model: Twilight Princess weight, GAME_RINGS below) and
northern_pike_lo.glb (far off, phones), and the editable creatures/northern_pike/tools/northern_pike.blend (this
folder has a .gdignore). Each is one still mesh with one surface: the shader (northern_pike.gdshader) draws every
marking and swims it. It prints a WINDING line for each: the check that nothing is inside out.

A northern pike (Esox lucius), 1.0 m from the tip of its lower jaw to the tips of its tail, built from the
species (no picture was traced or copied):

- THE BODY: a long torpedo, nearly round, a little flattened from side to side, deepest (0.145 m) and widest
  (0.094 m) a little before the middle, its back flat-topped from the head to the dorsal fin, running to a
  long, fairly deep tail wrist. A long head, a quarter of the fish, with a flat broad snout like a duck's bill;
  the lower jaw a little longer than the upper; the eyes high on the head.
- THE MOUTH: long, reaching back under the front of the eye. The head ahead of the jaw's hinge is in two closed
  pieces that meet along the line of the mouth. The upper one is part of the body: its underside is the roof of
  the mouth, and a wall behind it is the throat. The LOWER JAW is a part of its own, its top the floor of the
  mouth; the shader swings it down about its hinge (`gape`) and tips the snout up a little. The teeth stand in
  the closed mouth (so they show only when it opens): a row of fangs along each side of the lower jaw, big ones
  among smaller; small teeth at the front of the upper jaw; and a row of small backward-raked teeth along each
  side of the roof of the mouth.
- THE FINS, each a thin closed blade: the dorsal and the anal fins far back, close before the tail and opposite
  each other; a forked tail; pectoral fins low behind the gill covers; pelvic fins at the middle of the belly.

Everything here is in Godot space (metres, Y up, X to its left side, its nose at -Z) until it is written out;
the origin is on its middle line, half way along (0.5 m behind the tip of its jaw). `xm` below is metres
behind the tip of the jaw.

What a point is, for the shader: UV2.y the part (0 body, 1 the dorsal fin, 2 the anal fin, 3 the tail, 4 a
pectoral fin, 5 a pelvic fin, 6 an eye, 7 the lower jaw, 8 a tooth of the upper jaw or the roof, 9 a tooth of the
lower jaw). UV2.x: 1 inside the mouth (its roof, floor and throat), 0 elsewhere. UV, on the body and the jaw:
x how far along (0 jaw to 1 tail tips), y how high on its side (1 the ridge of the back, 0.5 its middle line,
0 the keel of the belly); on a fin: x from its root (0) to its tip (1), y from its leading edge (0) to its
trailing edge (1); on an eye: x from its middle (0) to its rim (1); on a tooth: x 0 at its root, 1 at its
point. (The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.)

The numbers marked "as the shader has it" are in northern_pike.gdshader too: change one, change the other.
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

LENGTH = 1.0
HALF = 0.5
BODY, DORSAL, ANAL, TAIL, PECTORAL, PELVIC, EYE, JAW, TEETH_UP, TEETH_LOW = range(10)
TAU = math.tau

# The body's outline: metres behind the jaw, the top of the body, the bottom of it, half its width (all
# metres; its widest is half way between top and bottom).
PROFILE = [
    (0.0, -0.0030, -0.0030, 0.0),
    (0.003, 0.0005, -0.0075, 0.0100),
    (0.012, 0.0040, -0.0120, 0.0190),
    (0.030, 0.0085, -0.0175, 0.0255),
    (0.060, 0.0160, -0.0255, 0.0310),
    (0.100, 0.0265, -0.0355, 0.0365),
    (0.150, 0.0405, -0.0475, 0.0415),
    (0.210, 0.0535, -0.0580, 0.0450),
    (0.280, 0.0625, -0.0660, 0.0470),
    (0.380, 0.0690, -0.0720, 0.0470),
    (0.480, 0.0710, -0.0730, 0.0450),
    (0.580, 0.0680, -0.0690, 0.0410),
    (0.660, 0.0605, -0.0615, 0.0355),
    (0.740, 0.0500, -0.0505, 0.0290),
    (0.800, 0.0415, -0.0420, 0.0225),
    (0.840, 0.0355, -0.0355, 0.0175),
    (0.862, 0.0310, -0.0310, 0.0130),
    (0.874, 0.0250, -0.0250, 0.0080),
    (0.880, 0.0030, -0.0030, 0.0015),
]
BODY_FROM = 0.002
BODY_TO = 0.880

# As the shader has it: the line of the mouth, the edge of the gill cover, the eye.
MOUTH_TO = 0.136
EYE_AT = (0.153, 0.0265)
EYE_RADIUS = 0.0125
# As the shader has it: how far back the lower jaw runs (its hinge is there, on the line of the mouth).
JAW_TO = 0.135
# The lower jaw is the longer: the head above the line of the mouth is set back this far at the tip, less and
# less until JUT_TO.
JUT = 0.006
JUT_TO = 0.05


def mouth_y(xm):
    return -0.0030 - 0.045 * xm


def gill_x(y):
    return 0.255 - 3.0 * (y + 0.005) ** 2


def snout(xm):
    """1 at the tip of the snout, 0 behind the eyes: how flat and broad (box-like) the head is there."""
    return 1.0 - smooth(0.03, 0.2, xm)


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


def _curve(xm):
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
    return out


def outline(xm):
    """(the height of its middle line, half depth above it, half depth below, half width) at `xm`."""
    t, b, w = _curve(xm)
    cy = 0.5 * (t + b)
    return cy, max(t - cy, 0.0002), max(cy - b, 0.0002), max(w, 0.0002)


def top(xm):
    cy, up, _, _ = outline(xm)
    return cy + up


def bottom(xm):
    cy, _, down, _ = outline(xm)
    return cy - down


def flat(xm):
    """How the height of a point follows the cosine of its angle round the body: 1 a plain ellipse, less
    than 1 a flatter top and bottom (the duck-bill snout)."""
    return 1.0 - 0.3 * snout(xm)


def height_of(xm, c):
    cy, up, down, _ = outline(xm)
    k = math.copysign(abs(c) ** flat(xm), c)
    return cy + k * (up if c >= 0.0 else down)


def cos_at(xm, y):
    """The cosine of the angle round the body at which the skin at `xm` is at height `y`."""
    cy, up, down, _ = outline(xm)
    d = y - cy
    k = max(-1.0, min(1.0, d / (up if d >= 0.0 else down)))
    return math.copysign(abs(k) ** (1.0 / flat(xm)), k)


def jut(xm, y):
    """How far back a point of the head at height `y` is set (the lower jaw is the longer)."""
    if xm >= JUT_TO:
        return 0.0
    m = mouth_y(xm)
    return JUT * smooth(m - 0.001, m + 0.004, y) * (1.0 - smooth(0.0, JUT_TO, xm))


def body_point(xm, angle):
    """A point of the skin: `angle` round the body from the ridge of the back (0) by its left side (a
    quarter turn) to the keel of the belly (half a turn)."""
    _, _, _, wide = outline(xm)
    c = math.cos(angle)
    s = math.sin(angle)
    y = height_of(xm, c)
    side = math.copysign(abs(s) ** (0.85 - 0.22 * snout(xm)), s) * wide
    z = xm
    # the mouth: a groove along its line
    if xm < MOUTH_TO + 0.01:
        groove = math.exp(-((y - mouth_y(xm)) / 0.0025) ** 2) * smooth(0.002, 0.012, xm) * (1.0 - smooth(MOUTH_TO - 0.015, MOUTH_TO + 0.003, xm))
        side *= 1.0 - 0.06 * groove
    z += jut(xm, y)
    # the gill cover: it stands a little proud of the body behind its edge
    behind = xm - gill_x(y)
    if behind > 0.0 and wide > 0.01:
        mask = smooth(-0.95, -0.75, c) * (1.0 - smooth(0.6, 0.8, c))
        step = 0.0022 * smooth(0.0, 0.004, behind) * math.exp(-behind / 0.03) * mask
        side *= 1.0 - step / wide
    return Vector((side, y, z - HALF))


def skin(xm, y, sx):
    """The point of the skin at `xm` and height `y`, on the left side (sx 1) or the right (-1)."""
    return body_point(xm, sx * math.acos(cos_at(xm, y)))


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


# Faces drawn flat (not smooth-shaded): the teeth, and the throat (a wall whose corners at the lips are
# slivers, which smooth shading would turn the wrong way).
FLAT = ("teeth", "throat")


# The game model (for Gulp, at Twilight Princess weight): its rings, placed by hand where the outline turns
# (close at the snout, the mouth, the gill cover and the tail's wrist, far apart along the flanks).
GAME_RINGS = [0.002, 0.006, 0.012, 0.020, 0.030, 0.043, 0.058, 0.075, 0.095, 0.115, JAW_TO,
              0.153, 0.175, 0.200, 0.225, 0.255, 0.290, 0.340, 0.400, 0.460, 0.520, 0.580, 0.630, 0.680, 0.730,
              0.770, 0.800, 0.825, 0.845, 0.860, 0.870, 0.876, BODY_TO]
GAME_AROUND = 20
# (set while the game model is made)
GAME = [False]
# The game model's columns round the body (radians from the ridge of the back), close at the ridge and the keel,
# far apart over the flanks, one exactly on the line of the mouth at the hinge; and that column's number.
ANGLES = [None]
LIP_COL = [0]
# The game model's fins: (rows from root to tip, columns from leading to trailing edge) of each skin. Thin
# blades: few rows where a fin is straight from root to tip, columns enough for the outline of its edge.
GAME_FINS = {"dorsal": (2, 10), "anal": (2, 8), "tail": (7, 3), "pectorals": (4, 2), "pelvics": (3, 2)}


def game_angles(around, k=0.2):
    n = around // 2
    lip = lip_angle(JAW_TO)
    base = [math.pi * (i / n - k * math.sin(TAU * i / n) / TAU) for i in range(n + 1)]
    j = min(range(1, n), key=lambda i: abs(base[i] - lip))
    side = [b * lip / base[j] if i <= j else lip + (b - base[j]) * (math.pi - lip) / (math.pi - base[j])
            for i, b in enumerate(base)]
    return side + [TAU - side[around - c] for c in range(n + 1, around)], j


def col_angle(c):
    """How far round the body from the ridge of the back column `c` is."""
    if ANGLES[0] is None:
        return c / AROUND[0] * TAU
    return ANGLES[0][c % AROUND[0]]


def lip_col():
    """The column on the line of the mouth at the hinge."""
    if ANGLES[0] is None:
        return round(lip_angle(JAW_TO) / (TAU / AROUND[0]))
    return LIP_COL[0]


def rings(low):
    if GAME[0]:
        return list(GAME_RINGS)
    xs = []
    x = BODY_FROM
    for until, step in ((JAW_TO, 0.0028), (0.30, 0.004), (0.86, 0.0068), (BODY_TO, 0.003)):
        if low:
            step *= 4.0
        n = max(1, round((until - x) / step))
        for i in range(n):
            xs.append(x + (until - x) * i / n)
        x = until
    xs.append(BODY_TO)
    return xs


def lip_angle(xm):
    """How far round the body from the ridge of the back the line of the mouth is, at `xm`."""
    return math.acos(max(-0.999, min(0.999, cos_at(xm, mouth_y(xm)))))


# How many points go round the body (set for each model as it is made).
AROUND = [72]


def lip_reach(xm):
    """lip_angle, eased over the back of the mouth onto the nearest of the body's own columns at the hinge,
    where the head and the jaw meet the whole body point for point."""
    if ANGLES[0] is not None:
        return lip_angle(xm) + (col_angle(lip_col()) - lip_angle(JAW_TO)) * smooth(0.6 * JAW_TO, JAW_TO, xm)
    step = TAU / AROUND[0]
    snap = round(lip_angle(JAW_TO) / step) * step
    return lip_angle(xm) + (snap - lip_angle(JAW_TO)) * smooth(0.6 * JAW_TO, JAW_TO, xm)


def hollow(xm, way):
    """How far the roof (`way` 1) or the floor (-1) of the mouth is arched away from its line, at its middle."""
    m = mouth_y(xm)
    room = (top(xm) - m) if way > 0 else (m - bottom(xm))
    return way * 0.45 * room * smooth(0.004, 0.04, xm)


def inside_point(xm, across, way):
    """A point of the roof (`way` 1) or the floor (`way` -1) of the mouth at `xm`: `across` 1 at the left
    lip, -1 at the right, the surface arched away from the line of the mouth between them."""
    lip = body_point(xm, lip_reach(xm))
    y = lip.y + hollow(xm, way) * (1.0 - across ** 4)
    return Vector((lip.x * across, y, xm + jut(xm, y) - HALF))


def body(m, low):
    around = AROUND[0]
    xs = rings(low)
    head = [xm for xm in xs if xm < JAW_TO - 1e-9]
    xs = xs[len(head):]
    grid = []
    for xm in xs:
        row = []
        for c in range(around):
            angle = col_angle(c)
            row.append(m.add(body_point(xm, angle), (xm / LENGTH, 0.5 + 0.5 * math.cos(angle)), BODY))
        grid.append(row)
    for r in range(len(grid) - 1):
        for c in range(around):
            n = (c + 1) % around
            quad = (grid[r][c], grid[r][n], grid[r + 1][n], grid[r + 1][c])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            cy = outline(xs[r])[0]
            m.face(quad, Vector((middle.x, middle.y - cy, 0.0)), "body")
    # the end inside the tail: a fan
    tip = m.add(Vector((0.0, 0.0, BODY_TO + 0.001 - HALF)), ((BODY_TO + 0.001) / LENGTH, 0.5), BODY)
    for c in range(around):
        m.face((tip, grid[-1][c], grid[-1][(c + 1) % around]), Vector((0.0, 0.0, 1.0)), "body")
    # The head ahead of the jaw's hinge: its skin above the line of the mouth (`half` columns each side of
    # the ridge, the last on the lip), and the roof of the mouth under it, lip to lip.
    half = lip_col()
    across = around - 2 * half
    uppers = []
    roofs = []
    for xm in head:
        reach = lip_reach(xm)
        uppers.append([m.add(body_point(xm, j / half * reach), (xm / LENGTH, 0.5 + 0.5 * math.cos(j / half * reach)), BODY)
                       for j in range(-half, half + 1)])
        roofs.append([m.add(inside_point(xm, 1.0 - 2.0 * k / across, 1.0), (xm / LENGTH, 0.5), BODY, smooth(BODY_FROM, 0.01, xm))
                      for k in range(across + 1)])
    # (the throat's top edge: points of its own along the back of the roof, so that its shading is its own)
    throat_top = [m.add(m.verts[q], (JAW_TO / LENGTH, 0.5), BODY, 1.0) for q in roofs[len(head) - 1]]
    # (where they join the whole body: its own points above the line of the mouth; below it the throat, a
    # wall across the back of the mouth, on the places of the body's points there; its outer edge is skin,
    # the throat under the jaw that shows when the jaw drops, darkening up into the mouth)
    first = grid[0]
    uppers.append([first[j % around] for j in range(-half, half + 1)])
    roofs.append([m.add(m.verts[first[(half + k) % around]], (JAW_TO / LENGTH, 0.5 + 0.5 * math.cos(col_angle(half + k))), BODY, 0.0)
                  for k in range(across + 1)])
    for r in range(len(head)):
        for j in range(2 * half):
            quad = (uppers[r][j], uppers[r][j + 1], uppers[r + 1][j + 1], uppers[r + 1][j])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((middle.x, middle.y - mouth_y(head[r]) + 0.004, 0.0)), "body")
        for k in range(across):
            quad = (roofs[r][k], roofs[r][k + 1], roofs[r + 1][k + 1], roofs[r + 1][k])
            if r < len(head) - 1:
                m.face(quad, Vector((0.0, -1.0, 0.0)), "mouth roof")
            else:
                # (as two triangles: at the corners of the mouth its quads are folded slivers)
                m.face((throat_top[k], throat_top[k + 1], roofs[r + 1][k + 1]), Vector((0.0, -0.3, -1.0)), "throat")
                m.face((throat_top[k], roofs[r + 1][k + 1], roofs[r + 1][k]), Vector((0.0, -0.3, -1.0)), "throat")
    # the tip of the snout: a fan over the end of both
    loop = uppers[0] + roofs[0][1:-1]
    middle = sum((m.verts[q] for q in loop), Vector()) / len(loop)
    tip = m.add(middle + Vector((0.0, 0.0, -0.001)), (0.0, 0.5), BODY)
    for i in range(len(loop)):
        m.face((tip, loop[i], loop[(i + 1) % len(loop)]), Vector((0.0, 0.0, -1.0)), "body")


def inset(p, xm):
    """The lower jaw is a little narrower than the body towards its end (3 per cent at the hinge), so that
    when it swings down, its back slides up into the throat inside the body's skin instead of through it."""
    p.x *= 1.0 - 0.03 * smooth(0.5 * JAW_TO, JAW_TO, xm)
    return p


def jaw(m, low):
    """The lower jaw: the body's own skin below the line of the mouth, ahead of the hinge, closed over by
    the floor of the mouth, with an end inside the head. It swings down whole about its hinge (the
    shader turns it), the hinge being the line across the head through both corners of the mouth."""
    around = AROUND[0]
    # (as many columns as the body has below the line of the mouth, so that its end meets the body point for point)
    half = lip_col()
    under = around - 2 * half
    across = 6 if GAME[0] else 4 if low else 14
    xs = [xm for xm in rings(low) if xm < JAW_TO + 1e-9]
    skins = []
    floors = []
    for xm in xs:
        reach = lip_reach(xm)
        row = []
        for i in range(under + 1):
            angle = reach + (TAU - 2.0 * reach) * i / under
            if xm > JAW_TO - 1e-9:
                angle = col_angle(half + i)
            row.append(m.add(inset(body_point(xm, angle), xm), (xm / LENGTH, 0.5 + 0.5 * math.cos(angle)), JAW))
        skins.append(row)
        floors.append([m.add(inset(inside_point(xm, 1.0 - 2.0 * k / across, -1.0), xm), (xm / LENGTH, 0.5), JAW, smooth(BODY_FROM, 0.01, xm))
                       for k in range(across + 1)])
    for r in range(len(xs) - 1):
        centre = 0.5 * (mouth_y(xs[r]) + bottom(xs[r]))
        for i in range(under):
            quad = (skins[r][i], skins[r][i + 1], skins[r + 1][i + 1], skins[r + 1][i])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((middle.x, middle.y - centre, 0.0)), "jaw")
        for k in range(across):
            m.face((floors[r][k], floors[r][k + 1], floors[r + 1][k + 1], floors[r + 1][k]), Vector((0.0, 1.0, 0.0)), "mouth floor")
    # its tip, and its end inside the head: a fan each
    for r, way, inside in ((0, -1.0, 0.0), (len(xs) - 1, 1.0, 1.0)):
        loop = skins[r] + floors[r][-2:0:-1]
        if r > 0:
            # (points of its own, so that the skin's shading does not turn towards the end)
            loop = [m.add(m.verts[q], (xs[r] / LENGTH, 0.5), JAW, 1.0) for q in loop]
        middle = sum((m.verts[q] for q in loop), Vector()) / len(loop)
        z = -HALF if r == 0 else JAW_TO - HALF
        tip = m.add(Vector((0.0, middle.y, z)), (xs[r] / LENGTH, 0.5), JAW, inside)
        for i in range(len(loop)):
            m.face((tip, loop[i], loop[(i + 1) % len(loop)]), Vector((0.0, 0.0, way)), "jaw" if r == 0 else "jaw end")


# The teeth: (which row, metres behind the tip of the lower jaw, how tall, how wide at the root). Each is a
# flat blade, raked back a little, standing in the closed mouth: "low" along the lower jaw just inside its
# lip (fangs, big ones among smaller), "up" small ones at the front of the upper jaw, "roof" small ones in a
# row along each side of the roof of the mouth, pointing down.
TEETH = []
for _k in range(14):
    _x = 0.018 + _k * 0.0074
    _big = 1.0 if _k % 3 == 1 else 0.6
    TEETH.append(("low", _x, (0.0045 + 0.0075 * smooth(0.0, 0.06, _x)) * _big, 0.0055 + 0.002 * _big))
for _k in range(5):
    TEETH.append(("up", 0.026 + _k * 0.0065, 0.0030, 0.0045))
for _k in range(10):
    TEETH.append(("roof", 0.022 + _k * 0.0095, 0.0045, 0.0045))
ACROSS = {"low": 0.93, "up": 0.93, "roof": 0.5}


def teeth(m, low):
    for n, (row, xm, high, wide) in enumerate(TEETH):
        if (low or GAME[0]) and (n % 2 or row == "roof"):
            continue
        upper = row != "low"
        part = TEETH_UP if upper else TEETH_LOW
        way = -1.0 if upper else 1.0
        for sx in (1.0, -1.0):
            base = inside_point(xm, sx * (ACROSS[row] - (0.1 if low or GAME[0] else 0.0)), -way)
            if not upper:
                base = inset(base, xm)
            # (rooted a little under the surface it stands on)
            base.y -= way * 0.25 * high
            thick = 0.35 * wide
            pts = []
            for dx, dz in ((0.5, -0.5), (0.5, 0.5), (-0.5, -0.5), (-0.5, 0.5)):
                pts.append(m.add(base + Vector((sx * dx * thick, 0.0, dz * wide)), (0.0, 0.0), part))
            tip = m.add(base + Vector((-sx * 0.15 * thick, way * 1.25 * high, 0.3 * high)), (1.0, 0.0), part)
            of, ob, inf, inb = pts
            m.face((of, ob, tip), Vector((sx, 0.0, 0.0)), "teeth")
            m.face((inf, inb, tip), Vector((-sx, 0.0, 0.0)), "teeth")
            m.face((of, inf, tip), Vector((0.0, 0.0, -1.0)), "teeth")
            m.face((ob, inb, tip), Vector((0.0, 0.0, 1.0)), "teeth")


def eye_frame(sx):
    """The middle of the eye on the skin, and the way the skin faces there."""
    xe, ye = EYE_AT
    d = EYE_RADIUS * 0.12
    here = skin(xe, ye, sx)
    out = (skin(xe + d, ye, sx) - skin(xe - d, ye, sx)).cross(skin(xe, ye + d, sx) - skin(xe, ye - d, sx))
    out.normalize()
    if out.x * sx < 0.0:
        out = -out
    return here, out


def eye_numbers():
    """As the shader has it, for the cartoon eye (grown about its middle, its rim kept on the skin): the
    left eye's middle on the skin, the way it faces, and how far the skin falls away from the plane
    there (along the normal, per metre squared, going up and going along)."""
    here, out = eye_frame(1.0)
    h = EYE_RADIUS
    xe, ye = EYE_AT
    sag_y = ((skin(xe, ye + h, 1.0) - here).dot(out) + (skin(xe, ye - h, 1.0) - here).dot(out)) / (2.0 * h * h)
    sag_z = ((skin(xe + h, ye, 1.0) - here).dot(out) + (skin(xe - h, ye, 1.0) - here).dot(out)) / (2.0 * h * h)
    print("EYE middle=(%.5f, %.5f, %.5f) out=(%.4f, %.4f, %.4f) sag=(%.3f, %.3f)" % (
        here.x, here.y, here.z, out.x, out.y, out.z, sag_y, sag_z))


def eye(m, sx, low):
    """A low dome lying on the skin of the head."""
    spokes = 28 if GAME[0] else 10 if low else 28
    steps = 3 if GAME[0] else 2 if low else 8
    xe, ye = EYE_AT
    here, out = eye_frame(sx)
    dome = EYE_RADIUS * 0.24
    middle = m.add(here + out * dome, (0.0, 0.0), EYE)
    last = None
    for k in range(1, steps + 1):
        r = k / steps
        row = []
        for s in range(spokes):
            a = s / spokes * TAU
            p = skin(xe + math.cos(a) * EYE_RADIUS * r, ye + math.sin(a) * EYE_RADIUS * r, sx)
            row.append(m.add(p + out * (dome * (0.92 * (1.0 - r * r) + 0.08 * (1.0 - r))), (r, 0.0), EYE))
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
    if GAME[0]:
        nt, nu = GAME_FINS[name]
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
    """A place in the flat of the middle fins (metres behind the jaw, metres up) in the model."""
    return Vector((0.0, p[1], p[0] - HALF))


SIDE = Vector((1.0, 0.0, 0.0))

# The middle fins.
DORSAL_FROM, DORSAL_LONG, DORSAL_HIGH = 0.652, 0.128, 0.078
ANAL_FROM, ANAL_LONG, ANAL_HIGH = 0.690, 0.104, 0.068
TAIL_TIP = (1.0, 0.088)
TAIL_NOTCH = 0.938
# As the shader has it: where the tail fin is hinged.
JOINT = 0.866


def rounded(u):
    """The height of a rounded fin along its base (0 front, 1 back): low in front, rising, the back rounded."""
    return (0.14 + 0.86 * smooth(0.0, 0.6, u)) * (1.0 - 0.35 * smooth(0.8, 1.0, u))


def fins(m, low):
    d = 3 if low else 1
    # The dorsal fin: far back, its rays rising from front to back, its back edge rounded.
    lean = math.radians(28.0)

    def dorsal_point(t, u):
        xm = DORSAL_FROM + DORSAL_LONG * u
        high = DORSAL_HIGH * rounded(u) * t
        return (xm + math.sin(lean) * high, top(xm) - 0.004 + math.cos(lean) * high + 0.004 * t)

    blade(m, DORSAL, "dorsal", dorsal_point, upright, SIDE, 0.004, 14 // d, 22 // d)
    # The anal fin: opposite the dorsal, a little behind it.
    lean_a = math.radians(30.0)

    def anal_point(t, u):
        xm = ANAL_FROM + ANAL_LONG * u
        high = ANAL_HIGH * rounded(u) * t
        return (xm + math.sin(lean_a) * high, bottom(xm) + 0.004 - math.cos(lean_a) * high - 0.004 * t)

    blade(m, ANAL, "anal", anal_point, upright, SIDE, 0.0035, 12 // d, 18 // d)
    # The tail: forked, the lobes broad and a little rounded at their tips.
    for way in (1.0, -1.0):
        tip = (TAIL_TIP[0], TAIL_TIP[1] * way)
        blade(m, TAIL, "tail", swept(((0.855, 0.0), (0.905, 0.070 * way), tip),
                                      ((TAIL_NOTCH, 0.0), (0.965, 0.030 * way), tip)),
              upright, SIDE, 0.006, 22 // d, 12 // max(d - 1, 1))
    for sx in (1.0, -1.0):
        # The pectoral fins: low behind the gill covers, lying back and a little down and out.
        root = skin(0.262, -0.052, sx)
        root.x -= sx * 0.003
        span = Vector((sx * 0.36, -0.28, 0.89)).normalized()
        chord = Vector((sx * 0.06, -0.9, 0.42)).normalized()
        facing = span.cross(chord).normalized()
        if facing.x * sx < 0.0:
            facing = -facing

        def pectoral_point(t, u):
            t *= 0.975
            wide_here = 0.028 * (0.5 + 0.5 * smooth(0.0, 0.35, t)) * (1.0 - t) ** 0.5 + 0.0012
            return (0.078 * t, 0.008 * t * t + wide_here * u)

        blade(m, PECTORAL, "pectorals", pectoral_point,
              lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.003, 12 // d, 8 // max(d - 1, 1))
        # The pelvic fins: at the middle of the belly, pointing back and down.
        root = Vector((sx * 0.014, bottom(0.50) + 0.006, 0.50 - HALF))
        span = Vector((sx * 0.3, -0.5, 0.81)).normalized()
        chord = Vector((0.0, 0.12, 1.0)).normalized()
        facing = span.cross(chord).normalized()
        if facing.x * sx < 0.0:
            facing = -facing

        def pelvic_point(t, u):
            t *= 0.97
            return (0.062 * t, 0.006 * t * t + (0.026 * (1.0 - t) ** 0.6 + 0.001) * u)

        blade(m, PELVIC, "pelvics", pelvic_point,
              lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.003, 10 // d, 6 // d)


def material_of(name, colour):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = colour
    material.diffuse_color = colour
    return material


def make(name, low, game=False):
    m = Mesh()
    AROUND[0] = 16 if low else 72
    GAME[0] = game
    ANGLES[0] = None
    if game:
        AROUND[0] = GAME_AROUND
        ANGLES[0], LIP_COL[0] = game_angles(GAME_AROUND)
    body(m, low)
    jaw(m, low)
    teeth(m, low)
    for sx in (1.0, -1.0):
        eye(m, sx, low)
    fins(m, low)
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
    mesh.materials.append(material_of("northern_pike", (0.35, 0.42, 0.22, 1.0)))
    for poly in mesh.polygons:
        poly.use_smooth = m.out[poly.index][1] not in FLAT
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    print("BUILT %s verts=%d tris=%d" % (name, len(mesh.vertices), tris))
    winding(name, mesh, m)
    GAME[0] = False
    ANGLES[0] = None
    return obj


def winding(name, mesh, m):
    """Nothing inside out: the skin of the body faces away from its middle line, each skin of a fin away
    from the fin's own flat, an eye or a tooth out from where it stands (Blender's front is the side a face's
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
        export_animations=False, export_texcoords=True, export_vertex_color="NONE",
    )


def render(folder, made):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.show_cavity = True
    scene.display.shading.show_backface_culling = True
    scene.display.shading.color_type = "MATERIAL"
    scene.render.resolution_x, scene.render.resolution_y = 1400, 800
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    k = LENGTH / 0.22
    # (Blender space: the fish lies along Y, its nose at +Y, up is Z)
    views = [("left", (1, 0, 0), (0, 0, 0), 0.25 * k), ("right", (-1, 0, 0), (0, 0, 0), 0.25 * k),
             ("front", (0, 1, 0), (0, 0, 0), 0.07 * k), ("back", (0, -1, 0), (0, 0, 0), 0.07 * k),
             ("top", (0.001, 0, 1), (0, 0, 0), 0.25 * k), ("under", (0.001, 0, -1), (0, 0, 0), 0.25 * k),
             ("head", (0.8, 0.5, 0.2), (0, 0.38, 0), 0.07 * k), ("tail", (0.7, -0.6, 0.3), (0, -0.35, 0), 0.09 * k),
             ("mouth", (0.35, 0.8, -0.45), (0, 0.42, -0.005), 0.04 * k)]
    for prefix, obj, only in (("", made[0], None), ("lo_", made[1], ("left", "head", "top"))):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if only and view not in only:
                continue
            offset = Vector(direction).normalized() * 40.0
            camera.data.ortho_scale = frame
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % (prefix, view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    full = make("northern_pike", False)
    low = make("northern_pike_lo", True)
    game = make("northern_pike_game", False, True)
    eye_numbers()
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, "northern_pike.glb"))
    export_one(low, os.path.join(OUT, "northern_pike_lo.glb"))
    export_one(game, os.path.join(OUT, "northern_pike_game.glb"))
    game.location.x = -0.3
    low.location.x = 0.3
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "northern_pike.blend"))
    game.location.x = 0.0
    low.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low])


if __name__ == "__main__":
    main()
