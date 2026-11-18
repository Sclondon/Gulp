"""Builds the red-bellied piranha (creatures/piranha) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/piranha/tools/build_piranha.py
    blender --background --python creatures/piranha/tools/build_piranha.py -- <preview folder>   # with pictures

Writes creatures/piranha/models/piranha.glb (the full model, for one seen close), piranha_game.glb (the game model:
Twilight Princess weight, GAME_RINGS below), piranha_lo.glb (far off,
phones) and piranha_school.glb (a very light one whose look is in its vertex colours, for many drawn by one
MultiMesh), and the editable creatures/piranha/tools/piranha.blend (this folder has a .gdignore). The full and
the low model are one still mesh with one surface each: the shader (piranha.gdshader) draws every marking and
swims it. It prints a WINDING line for each: the check that nothing is inside out.

A red-bellied piranha (Pygocentrus nattereri), 0.30 m from the tip of its lower jaw to the tips of its tail,
built from the species (no picture was traced or copied):

- THE BODY: deep and flattened from side to side, deepest (0.13 m) a third of the way back, about half as deep
  as it is long without its tail; a sharp keel along the belly; a short tail wrist. A blunt bulldog head: a steep
  forehead, a short snout, a deep heavy lower jaw that reaches past the upper (an underbite).
- THE MOUTH: the head ahead of the jaw's hinge is in two closed pieces that meet along the line of the mouth.
  The upper one is part of the body: its underside is the roof of the mouth, and a wall behind it is the
  throat. The LOWER JAW is a part of its own, its top the floor of the mouth; the shader swings it down about
  its hinge (`gape`). Each jaw has a row of triangular blade teeth standing just inside its lip, in the closed
  mouth (so they show only when it opens).
- THE FINS, each a thin closed blade: a rounded dorsal fin in the middle of the back; a small fleshy adipose fin
  before the tail; a long anal fin; a broad, shallowly forked tail; pectoral fins low behind the gill covers;
  small pelvic fins under the belly.

Everything here is in Godot space (metres, Y up, X to its left side, its nose at -Z) until it is written out;
the origin is on its middle line, half way along (0.15 m behind the tip of its jaw). `xm` below is metres
behind the tip of the jaw.

What a point is, for the shader: UV2.y the part (0 body, 1 the dorsal fin, 2 the anal fin, 3 the tail, 4 a
pectoral fin, 5 a pelvic fin, 6 an eye, 7 the lower jaw, 8 an upper tooth, 9 a lower tooth, 10 the adipose fin).
UV2.x: 1 inside the mouth (its roof, floor and throat), 0 elsewhere. UV, on the body and the jaw: x how far along
(0 jaw to 1 tail tips), y how high on its side (1 the ridge of the back, 0.5 its middle line, 0 the keel of the
belly); on a fin: x from its root (0) to its tip (1), y from its leading edge (0) to its trailing edge (1); on an
eye: x from its middle (0) to its rim (1); on a tooth: x 0 at its root, 1 at its point. (The glTF writer flips
V: what is written here is 1 - v, so that Godot reads v.)

The school model has no UVs: only places, normals and a colour at each point (COLOR_0: grey back, silver flank,
orange-red belly and chin, an eye each side, grey and red fins). Its fins are single sheets, drawn from both
sides by whatever draws it (GameCommon's flock.gdshader does).

The numbers marked "as the shader has it" are in piranha.gdshader too: change one, change the other.
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

LENGTH = 0.30
HALF = 0.15
BODY, DORSAL, ANAL, TAIL, PECTORAL, PELVIC, EYE, JAW, TEETH_UP, TEETH_LOW, ADIPOSE = range(11)
TAU = math.tau

# The body's outline: metres behind the jaw, the top of the body, the bottom of it, half its width (all
# metres; its widest is half way between top and bottom).
PROFILE = [
    (0.0, -0.0120, -0.0120, 0.0),
    (0.0015, -0.0060, -0.0200, 0.0045),
    (0.005, 0.0000, -0.0290, 0.0085),
    (0.012, 0.0110, -0.0380, 0.0125),
    (0.022, 0.0240, -0.0450, 0.0158),
    (0.035, 0.0380, -0.0510, 0.0186),
    (0.050, 0.0490, -0.0560, 0.0205),
    (0.070, 0.0580, -0.0610, 0.0220),
    (0.095, 0.0630, -0.0640, 0.0224),
    (0.120, 0.0620, -0.0625, 0.0212),
    (0.145, 0.0550, -0.0560, 0.0188),
    (0.170, 0.0455, -0.0460, 0.0156),
    (0.195, 0.0350, -0.0355, 0.0124),
    (0.215, 0.0265, -0.0265, 0.0096),
    (0.228, 0.0205, -0.0205, 0.0074),
    (0.238, 0.0180, -0.0180, 0.0052),
    (0.245, 0.0130, -0.0130, 0.0025),
    (0.249, 0.0015, -0.0015, 0.0008),
]
BODY_FROM = 0.0006
BODY_TO = 0.249

# As the shader has it: the line of the mouth, the edge of the gill cover, the eye.
MOUTH_TO = 0.031
EYE_AT = (0.042, 0.0205)
EYE_RADIUS = 0.0086
# As the shader has it: how far back the lower jaw runs (its hinge is there, on the line of the mouth).
JAW_TO = 0.030
# The underbite: the head above the line of the mouth is set back this far at the tip, less and less
# until JUT_TO.
JUT = 0.0030
JUT_TO = 0.022


def mouth_y(xm):
    return -0.0120 - 0.12 * xm


def gill_x(y):
    return 0.074 - 7.0 * (y - 0.004) ** 2


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


def jut(xm, y):
    """How far back a point of the head at height `y` is set (the underbite)."""
    if xm >= JUT_TO:
        return 0.0
    m = mouth_y(xm)
    return JUT * smooth(m - 0.0004, m + 0.0016, y) * (1.0 - smooth(0.0, JUT_TO, xm))


def body_point(xm, angle):
    """A point of the skin: `angle` round the body from the ridge of the back (0) by its left side (a
    quarter turn) to the keel of the belly (half a turn)."""
    cy, up, down, wide = outline(xm)
    c = math.cos(angle)
    s = math.sin(angle)
    y = cy + c * (up if c >= 0.0 else down)
    side = math.copysign(abs(s) ** 0.85, s) * wide
    # the keel along the belly (a piranha's belly is a sharp edge of scutes)
    side *= 1.0 - 0.34 * smooth(0.2, 1.0, -c) * smooth(0.04, 0.08, xm) * (1.0 - smooth(0.2, 0.235, xm))
    z = xm
    # the mouth: a groove along its line
    if xm < MOUTH_TO + 0.003:
        groove = math.exp(-((y - mouth_y(xm)) / 0.0008) ** 2) * smooth(0.0006, 0.004, xm) * (1.0 - smooth(MOUTH_TO - 0.004, MOUTH_TO + 0.0008, xm))
        side *= 1.0 - 0.10 * groove
    z += jut(xm, y)
    # the gill cover: it stands a little proud of the body behind its edge
    behind = xm - gill_x(y)
    if behind > 0.0 and wide > 0.003:
        mask = smooth(-0.95, -0.75, c) * (1.0 - smooth(0.55, 0.75, c))
        step = 0.0008 * smooth(0.0, 0.0015, behind) * math.exp(-behind / 0.008) * mask
        side *= 1.0 - step / wide
    return Vector((side, y, z - HALF))


def skin(xm, y, sx):
    """The point of the skin at `xm` and height `y`, on the left side (sx 1) or the right (-1)."""
    cy, up, down, _ = outline(xm)
    d = y - cy
    c = max(-1.0, min(1.0, d / (up if d >= 0.0 else down)))
    return body_point(xm, sx * math.acos(c))


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        # per point: (uv, uv2), or a colour (the school model)
        self.data = []
        # per face: the way it should face
        self.out = []
        self.count = {}

    def add(self, p, uv, part, inside=0.0):
        self.verts.append(p)
        self.data.append(((uv[0], 1.0 - uv[1]), (inside, 1.0 - part)))
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
GAME_RINGS = [0.0006, 0.002, 0.0045, 0.008, 0.012, 0.017, 0.023, JAW_TO,
              0.036, 0.044, 0.053, 0.063, 0.074, 0.085, 0.100, 0.115, 0.130, 0.145, 0.160, 0.175, 0.190, 0.205,
              0.218, 0.228, 0.240, 0.246, BODY_TO]
GAME_AROUND = 18
# (set while the game model is made)
GAME = [False]
# The game model's columns round the body (radians from the ridge of the back): evenly spaced for this deep, round
# body (k 0; closer at the ridge and keel made the back pointed from the front, closer on the flanks the keel), one
# exactly on the line of the mouth at the hinge; and that column's number.
ANGLES = [None]
LIP_COL = [0]
# The game model's fins: (rows from root to tip, columns from leading to trailing edge) of each skin. Thin
# blades: few rows where a fin is straight from root to tip, columns enough for the outline of its edge.
GAME_FINS = {"dorsal": (3, 6), "adipose": (2, 3), "anal": (2, 8), "tail": (6, 3), "pectorals": (4, 2), "pelvics": (3, 2)}


def game_angles(around, k=0.0):
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
    for until, step in ((JAW_TO, 0.0008), (0.085, 0.0012), (0.234, 0.0026), (BODY_TO, 0.0012)):
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
    cy, up, down, _ = outline(xm)
    d = mouth_y(xm) - cy
    return math.acos(max(-0.999, min(0.999, d / (up if d >= 0.0 else down))))


# How many points go round the body (set for each model as it is made).
AROUND = [56]


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
    return way * 0.45 * room * smooth(0.0015, 0.012, xm)


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
    tip = m.add(Vector((0.0, 0.0, BODY_TO + 0.0004 - HALF)), ((BODY_TO + 0.0004) / LENGTH, 0.5), BODY)
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
        roofs.append([m.add(inside_point(xm, 1.0 - 2.0 * k / across, 1.0), (xm / LENGTH, 0.5), BODY, smooth(BODY_FROM, 0.003, xm))
                      for k in range(across + 1)])
    # (the throat's top edge: points of its own along the back of the roof, so that its shading is its own)
    throat_top = [m.add(m.verts[q], (JAW_TO / LENGTH, 0.5), BODY, 1.0) for q in roofs[len(head) - 1]]
    # (where they join the whole body: its own points above the line of the mouth; below it the throat, a
    # wall across the back of the mouth, on the places of the body's points there)
    first = grid[0]
    uppers.append([first[j % around] for j in range(-half, half + 1)])
    # (its outer edge is skin, the throat under the jaw that shows when the jaw drops; it darkens up into
    # the mouth)
    roofs.append([m.add(m.verts[first[(half + k) % around]], (JAW_TO / LENGTH, 0.5 + 0.5 * math.cos(col_angle(half + k))), BODY, 0.0)
                  for k in range(across + 1)])
    for r in range(len(head)):
        cy = outline(head[r])[0]
        for j in range(2 * half):
            quad = (uppers[r][j], uppers[r][j + 1], uppers[r + 1][j + 1], uppers[r + 1][j])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((middle.x, middle.y - mouth_y(head[r]) + 0.002, 0.0)), "body")
        for k in range(across):
            quad = (roofs[r][k], roofs[r][k + 1], roofs[r + 1][k + 1], roofs[r + 1][k])
            if r < len(head) - 1:
                m.face(quad, Vector((0.0, -1.0, 0.0)), "mouth roof")
            else:
                # (as two triangles: at the corners of the mouth its quads are folded slivers)
                m.face((throat_top[k], throat_top[k + 1], roofs[r + 1][k + 1]), Vector((0.0, -0.3, -1.0)), "throat")
                m.face((throat_top[k], roofs[r + 1][k + 1], roofs[r + 1][k]), Vector((0.0, -0.3, -1.0)), "throat")
    # (where the old wall across the back of the mouth is: its top edge, the back of the roof, and its bottom
    # edge, the body's points under the line of the mouth; the throat behind it is added by throat_and_gills)
    THROAT[0] = ([m.verts[q].copy() for q in throat_top], [m.verts[q].copy() for q in roofs[-1]])
    # the tip of the snout: a fan over the end of both
    loop = uppers[0] + roofs[0][1:-1]
    middle = sum((m.verts[q] for q in loop), Vector()) / len(loop)
    tip = m.add(middle + Vector((0.0, 0.0, -0.0003)), (0.0, 0.5), BODY)
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
    across = 4 if GAME[0] else 4 if low else 12
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
        floors.append([m.add(inset(inside_point(xm, 1.0 - 2.0 * k / across, -1.0), xm), (xm / LENGTH, 0.5), JAW, smooth(BODY_FROM, 0.003, xm))
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


# The teeth: (upper jaw?, metres behind the tip of the lower jaw, how tall, how wide at the root). Each is a
# flat triangular blade standing just inside its lip, the upper ones pointing down, the lower ones up; the
# two rows interlock.
TEETH = []
for _k in range(7):
    TEETH.append((False, 0.0088 + _k * 0.0026, 0.0044 - 0.0003 * _k, 0.0034 - 0.0001 * _k))
for _k in range(7):
    TEETH.append((True, 0.0094 + _k * 0.0026, 0.0038 - 0.00028 * _k, 0.0030 - 0.0001 * _k))
TEETH_ACROSS = 0.93


def teeth(m, low):
    for n, (upper, xm, high, wide) in enumerate(TEETH):
        if (low or GAME[0]) and n % 2:
            continue
        part = TEETH_UP if upper else TEETH_LOW
        way = -1.0 if upper else 1.0
        for sx in (1.0, -1.0):
            base = inside_point(xm, sx * (TEETH_ACROSS - (0.1 if low or GAME[0] else 0.0)), -way)
            if not upper:
                base = inset(base, xm)
            # (rooted a little under the surface it stands on)
            base.y -= way * 0.25 * high
            thick = 0.35 * wide
            pts = []
            for dx, dz in ((0.5, -0.5), (0.5, 0.5), (-0.5, -0.5), (-0.5, 0.5)):
                pts.append(m.add(base + Vector((sx * dx * thick, 0.0, dz * wide)), (0.0, 0.0), part))
            tip = m.add(base + Vector((-sx * 0.12 * thick, way * 1.25 * high, 0.05 * high)), (1.0, 0.0), part)
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
    spokes = 24 if GAME[0] else 10 if low else 28
    steps = 2 if GAME[0] else 2 if low else 8
    xe, ye = EYE_AT
    here, out = eye_frame(sx)
    dome = EYE_RADIUS * 0.22
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

# The middle fins, as the school model has them too.
DORSAL_FROM, DORSAL_LONG, DORSAL_HIGH = 0.104, 0.038, 0.034
ADIPOSE_FROM, ADIPOSE_LONG, ADIPOSE_HIGH = 0.196, 0.020, 0.0095
ANAL_FROM, ANAL_LONG, ANAL_HIGH = 0.150, 0.070, 0.024
TAIL_TIP = (0.30, 0.037)
TAIL_NOTCH = 0.276
# As the shader has it: where the tail fin is hinged.
JOINT = 0.242


def dorsal_high(u):
    return DORSAL_HIGH * (0.25 + 0.75 * (1.0 - u) ** 0.8) * (0.55 + 0.45 * smooth(0.0, 0.22, u))


def anal_high(u):
    return ANAL_HIGH * (0.35 + 0.65 * (1.0 - u) ** 1.1) * (0.5 + 0.5 * smooth(0.0, 0.12, u))


def fins(m, low):
    d = 3 if low else 1
    # The dorsal fin: rounded, in the middle of the back, leaning back.
    lean = math.radians(24.0)

    def dorsal_point(t, u):
        xm = DORSAL_FROM + DORSAL_LONG * u
        high = dorsal_high(u) * t
        return (xm + math.sin(lean) * high, top(xm) - 0.0015 + math.cos(lean) * high + 0.0015 * t)

    blade(m, DORSAL, "dorsal", dorsal_point, upright, SIDE, 0.0016, 12 // d, 16 // d)
    # The adipose fin: a small fleshy flap before the tail.
    lean_ad = math.radians(30.0)

    def adipose_point(t, u):
        xm = ADIPOSE_FROM + ADIPOSE_LONG * u
        high = ADIPOSE_HIGH * math.sin(math.pi * min(1.0, 0.12 + u)) ** 0.7 * t
        return (xm + math.sin(lean_ad) * high, top(xm) - 0.0012 + math.cos(lean_ad) * high + 0.0012 * t)

    blade(m, ADIPOSE, "adipose", adipose_point, upright, SIDE, 0.0026, 5 // max(d - 1, 1), 8 // max(d - 1, 1))
    # The anal fin: long, tallest at its front.
    lean_a = math.radians(30.0)

    def anal_point(t, u):
        xm = ANAL_FROM + ANAL_LONG * u
        high = anal_high(u) * t
        return (xm + math.sin(lean_a) * high, bottom(xm) + 0.0012 - math.cos(lean_a) * high - 0.0012 * t)

    blade(m, ANAL, "anal", anal_point, upright, SIDE, 0.0014, 8 // d, 20 // d)
    # The tail: broad, shallowly forked, the lobes a little rounded.
    for way in (1.0, -1.0):
        tip = (TAIL_TIP[0], TAIL_TIP[1] * way)
        blade(m, TAIL, "tail", swept(((0.235, 0.0), (0.252, 0.026 * way), tip),
                                      ((TAIL_NOTCH, 0.0), (0.287, 0.010 * way), tip)),
              upright, SIDE, 0.0022, 18 // d, 10 // max(d - 1, 1))
    for sx in (1.0, -1.0):
        # The pectoral fins: low behind the gill covers, lying back and a little down and out.
        root = skin(0.078, -0.044, sx)
        root.x -= sx * 0.001
        span = Vector((sx * 0.32, -0.30, 0.90)).normalized()
        chord = Vector((sx * 0.06, -0.88, 0.42)).normalized()
        facing = span.cross(chord).normalized()
        if facing.x * sx < 0.0:
            facing = -facing

        def pectoral_point(t, u):
            t *= 0.975
            wide_here = 0.0125 * (0.45 + 0.55 * smooth(0.0, 0.35, t)) * (1.0 - t) ** 0.55 + 0.0005
            return (0.032 * t, 0.004 * t * t + wide_here * u)

        blade(m, PECTORAL, "pectorals", pectoral_point,
              lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.0012, 12 // d, 8 // max(d - 1, 1))
        # The pelvic fins: small, under the belly, pointing back and down.
        root = Vector((sx * 0.0035, bottom(0.112) + 0.0025, 0.112 - HALF))
        span = Vector((sx * 0.28, -0.55, 0.79)).normalized()
        chord = Vector((0.0, 0.18, 1.0)).normalized()
        facing = span.cross(chord).normalized()
        if facing.x * sx < 0.0:
            facing = -facing

        def pelvic_point(t, u):
            t *= 0.97
            return (0.017 * t, 0.002 * t * t + (0.0075 * (1.0 - t) ** 0.7 + 0.0004) * u)

        blade(m, PELVIC, "pelvics", pelvic_point,
              lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.0009, 8 // d, 6 // d)


# --- the throat and the gills (added 2026-11-18) ---------------------------------------------------------
# The user: "The fish need modeled gills as well, well for relevant fish, so like when it opens its mouth wide you
# can see them". The old wall across the back of the mouth stays in the model as it was (the full model's first
# surface is untouched, so it looks exactly as before); the shader moves that wall's top edge back to THROAT_Q, so
# the wall becomes the floor of a short tunnel, a cone from the mouth's back edge to that point. Its roof is made
# here, from the back of the roof of the mouth to the same point, and four gill arches stand on each side inside
# it, where they are seen through the wide-open mouth. With the mouth shut none of it can be seen.
#
# A gill arch is part GILLS: UV.x along the arch (0 its top, 1 its bottom), UV.y across it (0 the pale rakers at
# its front, 1 the tips of the red filaments behind it), UV2.x how deep in the throat it stands (0..1).
GILLS = 11
THROAT = [None]


def throat_q():
    """As the shader has it (THROAT_Q): the point at the back of the throat where the tunnel closes."""
    my = mouth_y(JAW_TO)
    deep = 0.6 * (gill_x(my) - JAW_TO)
    return Vector((0.0, my - 0.3 * (my - bottom(JAW_TO)), JAW_TO + deep - HALF))


def throat_and_gills(m, low):
    tops, bottoms = THROAT[0]
    q = throat_q()
    deep = q.z + HALF - JAW_TO
    # The roof of the throat: the back edge of the roof of the mouth drawn back and in to Q (a fan at its end).
    rings = 3 if GAME[0] else 2 if low else 6
    end = m.add(q, ((JAW_TO + deep) / LENGTH, 0.5), BODY, 1.0)
    rows = []
    for r in range(rings):
        f = r / rings
        rows.append([m.add(p.lerp(q, f), ((JAW_TO + 0.0005 + f * deep) / LENGTH, 0.5), BODY, 1.0) for p in tops])
    for r in range(rings):
        for k in range(len(tops) - 1):
            if r < rings - 1:
                points = (rows[r][k], rows[r][k + 1], rows[r + 1][k + 1], rows[r + 1][k])
            else:
                points = (rows[r][k], rows[r][k + 1], end)
            m.face(points, Vector((0.0, -1.0, -0.5)), "throat roof")
    # (at each corner of the mouth, the gap between the back of the roof, the lip and the end of the throat)
    for p, u in ((tops[0], bottoms[0]), (tops[-1], bottoms[-1])):
        corner = [m.add(v, ((JAW_TO + 0.0005) / LENGTH, 0.5), BODY, 1.0) for v in (p, u)]
        m.face((corner[0], corner[1], end), Vector((-p.x, 0.0, -0.3)), "throat roof")
    # The gill arches: on each side a curve from the middle of the roof round by the lip to the middle of the
    # floor, following the tunnel's wall a little inside it, at four depths.
    # (the game model has the low one's simple arches: it is a small fish, and its budget is 1,800; it is over it by the gills all the same)
    if low or GAME[0]:
        profile = [(1.0, 0.0), (0.0, 0.5), (-2.4, 0.0), (0.0, -0.5)]
        along = 2
    else:
        profile = [(1.0, 0.0), (0.6, 0.5), (0.0, 0.55), (-1.2, 0.35), (-2.4, 0.0), (-1.2, -0.35), (0.0, -0.55), (0.6, -0.5)]
        along = 12
    middle_top = len(tops) // 2
    middle_low = len(bottoms) // 2
    for sx in (1.0, -1.0):
        if sx > 0:
            line = tops[middle_top::-1] + bottoms[1:middle_low + 1]
        else:
            line = tops[middle_top:] + bottoms[-2:middle_low - 1:-1]
        lengths = [0.0]
        for a, b in zip(line, line[1:]):
            lengths.append(lengths[-1] + (b - a).length)

        def at(s, line=line, lengths=lengths):
            d = s * lengths[-1]
            i = 0
            while i < len(lengths) - 2 and lengths[i + 1] < d:
                i += 1
            t = (d - lengths[i]) / max(lengths[i + 1] - lengths[i], 1e-9)
            return line[i].lerp(line[i + 1], t)

        centre_y = sum((p.y for p in line), 0.0) / len(line)
        for n, f in enumerate((0.3, 0.45, 0.6, 0.75)):
            # (as thick as the tunnel is narrow there: the deep ones thinner, or they fold over at the tight bend
            # by the corner of the mouth)
            wide = 0.1 * deep * (1.0 - f)
            sections = []
            for i in range(along + 1):
                s = 0.1 + 0.8 * i / along
                p = at(s).lerp(q, f)
                axis = Vector((0.0, centre_y + (q.y - centre_y) * f, p.z))
                p = p + (axis - p) * 0.14
                ahead = at(min(s + 0.02, 1.0)).lerp(q, f) - at(max(s - 0.02, 0.0)).lerp(q, f)
                ahead.normalize()
                front = Vector((0.0, 0.0, -1.0))
                front = (front - ahead * front.dot(ahead)).normalized()
                across = ahead.cross(front).normalized()
                ring = [m.add(p + (front * a + across * b) * wide, (i / along, (1.0 - a) / 3.4), GILLS, f) for a, b in profile]
                sections.append((p, ring))
            k = len(profile)
            for i in range(along):
                (p0, r0), (p1, r1) = sections[i], sections[i + 1]
                for j in range(k):
                    quad = (r0[j], r0[(j + 1) % k], r1[(j + 1) % k], r1[j])
                    mid = sum((m.verts[v] for v in quad), Vector()) * 0.25
                    m.face(quad, mid - (p0 + p1) * 0.5, "gills")
            # (each end closed by a fan facing the way the arch runs there)
            for (p, ring), way, ahead in ((sections[0], -1.0, sections[1][0] - sections[0][0]),
                                          (sections[-1], 1.0, sections[-1][0] - sections[-2][0])):
                cap = m.add(p, (0.0 if way < 0 else 1.0, 0.3), GILLS, f)
                for j in range(k):
                    m.face((cap, ring[j], ring[(j + 1) % k]), ahead * way, "gills")


def material_of(name, colour):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = colour
    material.diffuse_color = colour
    return material


def make(name, low, game=False):
    m = Mesh()
    AROUND[0] = 14 if low else 56
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
    throat_from = len(m.faces)
    throat_and_gills(m, low)
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
    mesh.materials.append(material_of("piranha", (0.55, 0.55, 0.55, 1.0)))
    if not GAME[0]:
        # (the full and the low models: the throat and the gills in a second surface, so that the first is
        # exactly as it was, and is thinned for far off by the importer exactly as it was)
        mesh.materials.append(material_of("piranha_throat", (0.5, 0.1, 0.1, 1.0)))
        for poly in mesh.polygons:
            if poly.index >= throat_from:
                poly.material_index = 1
    return finish(name, mesh, m)


def finish(name, mesh, m):
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


# --- the school model -------------------------------------------------------------------------

# Its colours, as they are written into the points (what a shader reads as COLOR).
C_RIDGE = (0.16, 0.18, 0.18)
C_BACK = (0.30, 0.33, 0.33)
C_SILVER = (0.62, 0.65, 0.66)
C_LOW = (0.70, 0.52, 0.36)
C_BELLY = (0.80, 0.20, 0.07)
C_EYE = (0.04, 0.02, 0.02)
C_IRIS = (0.62, 0.35, 0.12)
C_FIN = (0.26, 0.28, 0.28)
C_RED_FIN = (0.65, 0.16, 0.06)
C_TAIL_EDGE = (0.05, 0.05, 0.06)
# Round the body (degrees from the ridge of the back): the ridge, the back, the silver, low on the flank,
# the keel; then the same up the other side.
SCHOOL_ANGLES = (0.0, 45.0, 75.0, 118.0, 180.0, 242.0, 285.0, 315.0)
SCHOOL_COLOURS = (C_RIDGE, C_BACK, C_SILVER, C_LOW, C_BELLY, C_LOW, C_SILVER, C_BACK)
SCHOOL_RINGS = (0.002, 0.010, 0.025, 0.050, 0.085, 0.125, 0.165, 0.205, 0.235, 0.247)


def make_school(name):
    m = Mesh()
    grid = []
    for xm in SCHOOL_RINGS:
        row = []
        for angle, colour in zip(SCHOOL_ANGLES, SCHOOL_COLOURS):
            # (the chin and the throat are red right up to the mouth)
            if xm < 0.04 and angle in (118.0, 242.0):
                colour = C_BELLY
            row.append(m.dab(body_point(xm, math.radians(angle)), colour))
        grid.append(row)
    around = len(SCHOOL_ANGLES)
    for r in range(len(grid) - 1):
        cy = outline(SCHOOL_RINGS[r])[0]
        for c in range(around):
            n = (c + 1) % around
            quad = (grid[r][c], grid[r][n], grid[r + 1][n], grid[r + 1][c])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((middle.x, middle.y - cy, 0.0)), "body")
    for row, xm, way, colour in ((grid[0], 0.0, -1.0, C_BELLY), (grid[-1], BODY_TO, 1.0, C_SILVER)):
        y = mouth_y(0.0) if xm == 0.0 else 0.0
        tip = m.dab(Vector((0.0, y, xm - HALF)), colour)
        for c in range(around):
            m.face((tip, row[c], row[(c + 1) % around]), Vector((0.0, 0.0, way)), "body")

    def facet(xm, angle):
        """The point of this model's own flat-sided skin at `xm` and `angle` (degrees, 0 to 360)."""
        r = 0
        while r < len(SCHOOL_RINGS) - 2 and xm > SCHOOL_RINGS[r + 1]:
            r += 1
        t = (xm - SCHOOL_RINGS[r]) / (SCHOOL_RINGS[r + 1] - SCHOOL_RINGS[r])
        angles = list(SCHOOL_ANGLES) + [360.0]
        c = 0
        while c < around - 1 and angle > angles[c + 1]:
            c += 1
        u = (angle - angles[c]) / (angles[c + 1] - angles[c])
        n = (c + 1) % around
        a = m.verts[grid[r][c]].lerp(m.verts[grid[r][n]], u)
        b = m.verts[grid[r + 1][c]].lerp(m.verts[grid[r + 1][n]], u)
        return a.lerp(b, t)

    def plate(xm, angle, radius, corners, lift, colour, group):
        """A small flat plate lying on the skin: an eye."""
        here = facet(xm, angle)
        out = (facet(xm + 0.001, angle) - facet(xm - 0.001, angle)).cross(facet(xm, angle + 2.0) - facet(xm, angle - 2.0))
        out.normalize()
        if out.dot(Vector((here.x, 0.0, 0.0))) < 0.0:
            out = -out
        degrees = radius / max((facet(xm, angle + 5.0) - here).length, 1e-6) * 5.0
        ring = []
        for k in range(corners):
            a = k / corners * TAU
            p = facet(xm + math.cos(a) * radius, angle + math.sin(a) * degrees)
            ring.append(m.dab(p + out * lift, colour))
        for k in range(1, corners - 1):
            m.face((ring[0], ring[k], ring[k + 1]), out, group)

    for mirror in (False, True):
        def turned(angle):
            return 360.0 - angle if mirror else angle
        plate(EYE_AT[0], turned(58.0), EYE_RADIUS, 8, 0.0008, C_IRIS, "eyes")
        plate(EYE_AT[0], turned(58.0), EYE_RADIUS * 0.6, 6, 0.0013, C_EYE, "eyes")

    # The fins: single sheets (drawn from both sides).
    def sheet(points, colours, out=SIDE):
        m.face(tuple(m.dab(p, c) for p, c in zip(points, colours)), out, "fins (two-sided sheets)")

    x0, x1 = DORSAL_FROM, DORSAL_FROM + DORSAL_LONG
    sheet((upright((x0, top(x0) - 0.0015)), upright((x0 + 0.020, top(x0) + DORSAL_HIGH * 0.85)),
           upright((x1 + 0.006, top(x1) + 0.010)), upright((x1, top(x1) - 0.0015))),
          (C_BACK, C_FIN, C_FIN, C_BACK))
    x0, x1 = ADIPOSE_FROM, ADIPOSE_FROM + ADIPOSE_LONG
    sheet((upright((x0, top(x0) - 0.001)), upright((x0 + 0.012, top(x0) + ADIPOSE_HIGH)), upright((x1, top(x1) - 0.001))),
          (C_BACK, C_TAIL_EDGE, C_BACK))
    x0, x1 = ANAL_FROM, ANAL_FROM + ANAL_LONG
    sheet((upright((x0, bottom(x0) + 0.0012)), upright((x0 + 0.012, bottom(x0) - ANAL_HIGH)),
           upright((x1 + 0.004, bottom(x1) - 0.008)), upright((x1, bottom(x1) + 0.0012))),
          (C_BELLY, C_RED_FIN, C_TAIL_EDGE, C_SILVER))
    for way in (1.0, -1.0):
        sheet((upright((0.236, 0.010 * way)), upright((TAIL_TIP[0], TAIL_TIP[1] * way)), upright((TAIL_NOTCH, 0.0)), upright((0.236, 0.0))),
              (C_FIN, C_TAIL_EDGE, C_TAIL_EDGE, C_SILVER))
    for sx in (1.0, -1.0):
        root = facet(0.078, 125.0 if sx > 0.0 else 235.0)
        span = Vector((sx * 0.32, -0.30, 0.90)).normalized()
        chord = Vector((sx * 0.06, -0.88, 0.42)).normalized()
        out = span.cross(chord)
        if out.x * sx < 0.0:
            out = -out
        sheet((root, root + span * 0.03 + chord * 0.005, root + span * 0.01 + chord * 0.012), (C_LOW, C_RED_FIN, C_RED_FIN), out)

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) for p in m.verts], [], m.faces)
    mesh.color_attributes.new(name="Col", type="FLOAT_COLOR", domain="POINT")
    colours = mesh.color_attributes["Col"]
    for i, colour in enumerate(m.data):
        colours.data[i].color = (colour[0], colour[1], colour[2], 1.0)
    # (the glTF writer only writes the colour that is marked for rendering)
    mesh.color_attributes.active_color = colours
    mesh.color_attributes.render_color_index = 0
    material = material_of("piranha_school", (1.0, 1.0, 1.0, 1.0))
    mesh.materials.append(material)
    return finish(name, mesh, m)


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
    k = LENGTH / 0.22
    # (Blender space: the fish lies along Y, its nose at +Y, up is Z)
    views = [("left", (1, 0, 0), (0, 0, 0), 0.25 * k), ("right", (-1, 0, 0), (0, 0, 0), 0.25 * k),
             ("front", (0, 1, 0), (0, 0, 0), 0.12 * k), ("back", (0, -1, 0), (0, 0, 0), 0.12 * k),
             ("top", (0.001, 0, 1), (0, 0, 0), 0.42 * k), ("under", (0.001, 0, -1), (0, 0, 0), 0.42 * k),
             ("head", (0.8, 0.5, 0.2), (0, 0.11, -0.005), 0.09 * k), ("tail", (0.7, -0.6, 0.3), (0, -0.1, 0), 0.11 * k),
             ("mouth", (0.35, 0.8, -0.45), (0, 0.13, -0.01), 0.06 * k)]
    for prefix, obj, only in (("", made[0], None), ("lo_", made[1], ("left", "head", "top")),
                              ("school_", made[2], ("left", "right", "top", "under", "front", "head"))):
        scene.display.shading.color_type = "VERTEX" if prefix == "school_" else "MATERIAL"
        # (the school model's sheets are drawn from both sides)
        scene.display.shading.show_backface_culling = prefix != "school_"
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
    full = make("piranha", False)
    low = make("piranha_lo", True)
    game = make("piranha_game", False, True)
    eye_numbers()
    print("THROAT_Q %.5f, %.5f, %.5f" % tuple(throat_q()))
    school = make_school("piranha_school")
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, "piranha.glb"))
    export_one(low, os.path.join(OUT, "piranha_lo.glb"))
    export_one(game, os.path.join(OUT, "piranha_game.glb"))
    game.location.x = -0.12
    export_one(school, os.path.join(OUT, "piranha_school.glb"), True)
    low.location.x = 0.12
    school.location.x = 0.24
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "piranha.blend"))
    game.location.x = 0.0
    low.location.x = 0.0
    school.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low, school])


if __name__ == "__main__":
    main()
