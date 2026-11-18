"""Builds the humpback anglerfish (creatures/deep_anglerfish) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/deep_anglerfish/tools/build_deep_anglerfish.py
    blender --background --python creatures/deep_anglerfish/tools/build_deep_anglerfish.py -- <preview folder>

Writes creatures/deep_anglerfish/models/deep_anglerfish.glb (the full model) and deep_anglerfish_lo.glb (far off,
phones), and the editable creatures/deep_anglerfish/tools/deep_anglerfish.blend (this folder has a .gdignore). Each
is one still mesh with one surface: the shader (deep_anglerfish.gdshader) draws every marking, swims it, opens its
mouth, sways its rod and lights its lure. It prints a WINDING line for each: the check that nothing is inside out.

A female humpback anglerfish, or black seadevil (Melanocetus johnsonii), 0.30 m from the tip of its lower jaw to
the edge of its tail, built from the species (no picture was traced or copied):

- THE BODY: a black globe, a little flattened from side to side, deepest (0.167 m) and widest (0.124 m) a little
  under a third of the way back, running quickly down to a short tail wrist. The body's middle line rises towards
  the front, so that the tip of the lower jaw is high on the front of the head and the mouth opens upward.
- THE MOUTH: enormous and oblique, its line running from the tip of the jaw (the foremost point) back and steeply
  down to its hinge low behind the eye. The head ahead of the hinge is in two closed pieces that meet along the
  line of the mouth. The upper one is part of the body: its underside is the roof of the mouth, and a wall behind
  it is the throat. The LOWER JAW is a part of its own (the whole lower front of the head), its top the floor of the
  mouth; the shader swings it down about its hinge (`gape`). Shut, the two lie lip to lip.
- THE TEETH: long, slender, glassy needles, each a thin cone curved back a little: a row along each side of the
  lower jaw (the longest at the front, standing up outside the upper lip when the mouth is shut, as they do in
  life) and a shorter row along each side of the roof, pointing down into the mouth.
- THE ROD (illicium): a thin stalk from the top of the snout, arching up and forward over the mouth, ending in the
  LURE (esca), a bulb with a dark collar at its base and a small crest on top. The shader sways the rod, flicks it
  and lights the bulb.
- TINY EYES, low domes high on the sides of the head behind the rod's root.
- THE FINS, each a thin closed blade: a small rounded dorsal fin and a smaller anal fin far back near the tail; a
  rounded tail fin; small rounded pectoral fins on short stalks low on the sides. No pelvic fins (anglerfish of
  the deep have none).

Everything here is in Godot space (metres, Y up, X to its left side, its nose at -Z) until it is written out; the
origin is on its middle line at the height of the tail, half way along (0.15 m behind the tip of its jaw). `xm`
below is metres behind the tip of the jaw.

It also writes models/deep_anglerfish_game.glb, the GAME MODEL (2026-11-18): a few triangles, spent unevenly as a Twilight
Princess model spends them, on the outline, the eye, the mouth and the lights, from the same curves (see
GAME_CUTS, fitted() and pick(): `low` is False, True or GAME for the full, low and game models). The full and
low models are built exactly as before.

What a point is, for the shader: UV2.y the part (0 body, 1 the dorsal fin, 2 the anal fin, 3 the tail, 4 a
pectoral fin, 5 the rod, 6 an eye, 7 the lower jaw, 8 a tooth of the roof, 9 a tooth of the lower jaw, 10 the
lure's bulb). UV2.x: 1 inside the mouth (its roof, floor and throat), 0 elsewhere. UV, on the body and the jaw: x
how far along (0 jaw to 1 tail), y how high on its side (1 the ridge of the back, 0 the keel of the belly); on a
fin: x from its root (0) to its tip (1), y from its leading edge (0) to its trailing edge (1); on an eye: x from its
middle (0) to its rim (1); on the rod and a tooth: x from its root (0) to its tip (1); on the bulb: x from its base
(0) to its top (1). (The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.)

The numbers marked "as the shader has it" are in deep_anglerfish.gdshader too: change one, change the other.
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

NAME = "deep_anglerfish"
LENGTH = 0.30
HALF = 0.15
BODY, DORSAL, ANAL, TAIL, PECTORAL, ROD, EYE, JAW, TEETH, JAW_TEETH, ESCA = range(11)
# (the gill arches, added 2026-11-18)
GILL = 11
TAU = math.tau

# The body's outline: metres behind the jaw, half its depth above its middle line, half its depth below, half
# its width. (Its middle line is at `mid(xm)`, higher towards the front.)
PROFILE = [
    (0.0, 0.0, 0.0, 0.0),
    (0.0015, 0.007, 0.020, 0.018),
    (0.005, 0.014, 0.042, 0.034),
    (0.012, 0.024, 0.060, 0.045),
    (0.022, 0.036, 0.072, 0.053),
    (0.035, 0.049, 0.080, 0.058),
    (0.050, 0.060, 0.085, 0.061),
    (0.070, 0.070, 0.088, 0.063),
    (0.090, 0.076, 0.088, 0.064),
    (0.110, 0.076, 0.085, 0.061),
    (0.130, 0.070, 0.074, 0.055),
    (0.150, 0.060, 0.061, 0.044),
    (0.170, 0.042, 0.042, 0.030),
    (0.190, 0.026, 0.026, 0.018),
    (0.210, 0.018, 0.018, 0.011),
    (0.225, 0.016, 0.016, 0.008),
    (0.232, 0.012, 0.012, 0.005),
    (0.236, 0.002, 0.002, 0.0015),
]
BODY_FROM = 0.0006
BODY_TO = 0.236

# As the shader has it: how far back the lower jaw runs (its hinge is there, on the line of the mouth).
JAW_TO = 0.095
# As the shader has it: how far back the throat and its gills reach (metres behind the snout's tip).
GILL_TO = 0.135
# How far the snout above the mouth is set back behind the jaw's tip.
SET_BACK = 0.011
EYE_AT = (0.058, 0.033)
EYE_RADIUS = 0.003
# As the shader has it: where the rod rises from the top of the snout (metres behind the jaw).
ROD_FROM = 0.02
# The game model: rings wherever the outline bends more than GAME_TOL metres off a straight line, at most
# GAME_MOST apart, and always at GAME_CUTS (the jaw's hinge among them).
GAME_CUTS = [BODY_FROM, JAW_TO, 0.20, BODY_TO]
GAME_TOL = 0.001
GAME_MOST = 0.025


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def mid(xm):
    """The height of the body's middle line: it rises towards the front, so that the jaw's tip is high."""
    return 0.042 * (1.0 - smooth(0.0, 0.12, xm))


SLOPE = 0.6


def mouth_y(xm):
    """As the shader has it: the line of the mouth, steeply down from the jaw's tip to its hinge."""
    return 0.046 - SLOPE * xm


def to_b(p):
    return Vector((p.x, -p.z, p.y))


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
    """(half depth above, half depth below, half width) at `xm`."""
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
        out.append(max(a + b, 0.0002))
    return out


def top(xm):
    return mid(xm) + outline(xm)[0]


def bottom(xm):
    return mid(xm) - outline(xm)[1]


def body_point(xm, angle):
    """A point of the skin: `angle` round the body from the ridge of the back (0) by its left side (a quarter
    turn) to the keel of the belly (half a turn)."""
    up, down, wide = outline(xm)
    c = math.cos(angle)
    s = math.sin(angle)
    y = mid(xm) + c * (up if c >= 0.0 else down)
    side = s * wide
    # (a little fuller low on the flanks: the belly hangs)
    side *= 1.0 + 0.06 * smooth(-0.2, -0.7, c) * smooth(0.06, 0.12, xm) * (1.0 - smooth(0.15, 0.2, xm))
    z = xm
    # the snout above the mouth is set back: the lower jaw juts out ahead of it
    if xm < 0.04:
        z += SET_BACK * smooth(mouth_y(xm) - 0.0005, mouth_y(xm) + 0.01, y) * (1.0 - smooth(0.0, 0.04, xm))
    return Vector((side, y, z - HALF))


def skin(xm, y, sx):
    """The point of the skin at `xm` and height `y`, on the left side (sx 1) or the right (-1)."""
    up, down, _ = outline(xm)
    m = mid(xm)
    c = max(-1.0, min(1.0, (y - m) / (up if y >= m else down)))
    return body_point(xm, sx * math.acos(c))


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.data = []
        self.out = []
        self.count = {}
        self.surface = []
        self.tris = {}

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
        self.surface.append(SURFACE[0])
        self.tris[name] = self.tris.get(name, 0) + len(points) - 2


GAME = "game"


def pick(low, full, game, lo):
    """How finely a part is cut: `low` is False for the full model, True for the low one, GAME for the game model."""
    return game if low is GAME else (lo if low else full)


def fitted(cuts, tol, most, curves):
    """The game model's rings: as few as keep each of `curves` (functions of xm) within `tol` metres of a straight
    line between rings, never more than `most` apart, with a ring at each of `cuts`. Where the outline bends
    (the snout, the jaw, the tail's wrist) they crowd; along the smooth flanks they spread."""
    xs = []
    for a, b in zip(cuts, cuts[1:]):
        x = a
        while x < b - 1e-9:
            best = min(b, x + 0.0004)
            e = best
            while e < b - 1e-9 and e - x < most:
                e = min(b, e + 0.0004)
                ok = True
                for f in curves:
                    fa = f(x)
                    fb = f(e)
                    for i in range(1, 12):
                        t = i / 12.0
                        if abs(f(x + (e - x) * t) - (fa + (fb - fa) * t)) > tol:
                            ok = False
                            break
                    if not ok:
                        break
                if not ok:
                    break
                best = e
            xs.append(x)
            x = best if b - best > 0.25 * (best - x) else b
    xs.append(cuts[-1])
    return xs


def rings(low):
    if low is GAME:
        return fitted(GAME_CUTS, GAME_TOL, GAME_MOST, [top, bottom, lambda x: outline(x)[2], lambda x: 0.04 * lip_angle(x)])
    xs = []
    x = BODY_FROM
    for until, step in ((JAW_TO, 0.0016), (0.20, 0.0028), (BODY_TO, 0.0018)):
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
    up, down, _ = outline(xm)
    y = mouth_y(xm) - mid(xm)
    return math.acos(max(-0.999, min(0.999, y / (up if y >= 0.0 else down))))


def inside_point(xm, across, hollow):
    """A point of the roof (`hollow` up) or the floor (`hollow` down) of the mouth at `xm`: `across` 1 at the left
    lip, -1 at the right, the surface arched away from the line of the mouth between them."""
    lip = body_point(xm, lip_angle(xm))
    y = lip.y + hollow * (1.0 - across * across) * smooth(0.002, 0.012, xm)
    return Vector((lip.x * across * (1.0 - 0.08 * (1.0 - across * across)), y, lip.z))


def col_angle(c, around):
    """The angle of column `c` of `around` round the body: evenly spread, but warped a little so that the line of
    the mouth at the jaw's hinge falls exactly on a column (the jaw and the head meet the body there)."""
    step = TAU / around
    half = round(lip_angle(JAW_TO) / step)
    lip = lip_angle(JAW_TO)
    a = c * step
    way = 1.0
    if a > math.pi:
        a = TAU - a
        way = -1.0
    if a <= half * step:
        a = a * lip / (half * step)
    else:
        a = lip + (a - half * step) * (math.pi - lip) / (math.pi - half * step)
    return a if way > 0.0 else TAU - a


def body(m, low):
    around = pick(low, 48, 16, 12)
    xs = rings(low)
    head = [xm for xm in xs if xm < JAW_TO - 1e-9]
    xs = xs[len(head):]
    grid = []
    for xm in xs:
        row = []
        for c in range(around):
            angle = col_angle(c, around)
            row.append(m.add(body_point(xm, angle), (xm / LENGTH, 0.5 + 0.5 * math.cos(angle)), BODY))
        grid.append(row)
    for r in range(len(grid) - 1):
        centre = mid(xs[r])
        for c in range(around):
            n = (c + 1) % around
            quad = (grid[r][c], grid[r][n], grid[r + 1][n], grid[r + 1][c])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((middle.x, middle.y - centre, 0.0)), "body")
    tip = m.add(Vector((0.0, mid(BODY_TO), BODY_TO + 0.0004 - HALF)), ((BODY_TO + 0.0004) / LENGTH, 0.5), BODY)
    for c in range(around):
        m.face((tip, grid[-1][c], grid[-1][(c + 1) % around]), Vector((0.0, 0.0, 1.0)), "body")
    # The head ahead of the jaw's hinge: its skin above the line of the mouth, and the roof of the mouth under it.
    half = round(lip_angle(JAW_TO) / (TAU / around))
    across = around - 2 * half
    uppers = []
    roofs = []
    for xm in head:
        reach = lip_angle(xm)
        up = outline(xm)[0]
        uppers.append([m.add(body_point(xm, j / half * reach), (xm / LENGTH, 0.5 + 0.5 * math.cos(j / half * reach)), BODY)
                       for j in range(-half, half + 1)])
        roofs.append([m.add(inside_point(xm, 1.0 - 2.0 * k / across, 0.5 * up), (xm / LENGTH, 0.5), BODY, smooth(BODY_FROM, 0.003, xm))
                      for k in range(across + 1)])
    first = grid[0]
    uppers.append([first[j % around] for j in range(-half, half + 1)])
    roofs.append([m.add(m.verts[first[(half + k) % around]], (JAW_TO / LENGTH, 0.5), BODY, 1.0) for k in range(across + 1)])
    for r in range(len(head)):
        centre = mid(head[r])
        for j in range(2 * half):
            quad = (uppers[r][j], uppers[r][j + 1], uppers[r + 1][j + 1], uppers[r + 1][j])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((middle.x, middle.y - centre + 0.004, 0.0)), "body")
        for k in range(across):
            quad = (roofs[r][k], roofs[r][k + 1], roofs[r + 1][k + 1], roofs[r + 1][k])
            if r < len(head) - 1:
                m.face(quad, Vector((0.0, -1.0, 0.0)), "mouth roof")
            else:
                # The wall across the back of the mouth that every model always had: kept, so that shut the fish
                # looks exactly as it did (the shader lifts it out of the way as the mouth opens, onto the throat).
                m.face(quad, Vector((0.0, -0.3, -1.0)), "throat wall")
    # behind the mouth, the throat (made last, by throat_and_gills): the opening it starts from
    THROAT[:] = [list(roofs[len(head) - 1]), list(roofs[-1])]
    loop = uppers[0] + roofs[0][1:-1]
    middle = sum((m.verts[q] for q in loop), Vector()) / len(loop)
    tip = m.add(middle + Vector((0.0, 0.0, -0.0003)), (0.0, 0.5), BODY)
    for i in range(len(loop)):
        m.face((tip, loop[i], loop[(i + 1) % len(loop)]), Vector((0.0, 0.0, -1.0)), "body")


def jaw(m, low):
    """The lower jaw: the body's own skin below the line of the mouth, ahead of the hinge, closed over by the floor
    of the mouth, with an end inside the head."""
    around = pick(low, 48, 16, 12)
    half = round(lip_angle(JAW_TO) / (TAU / around))
    under = around - 2 * half
    across = pick(low, 12, 4, 4)
    xs = [xm for xm in rings(low) if xm < JAW_TO + 1e-9]
    skins = []
    floors = []
    for xm in xs:
        reach = lip_angle(xm)
        down = outline(xm)[1]
        row = []
        for i in range(under + 1):
            angle = reach + (TAU - 2.0 * reach) * i / under
            if xm > JAW_TO - 1e-9:
                angle = col_angle(half + i, around)
            row.append(m.add(body_point(xm, angle), (xm / LENGTH, 0.5 + 0.5 * math.cos(angle)), JAW))
        skins.append(row)
        floors.append([m.add(inside_point(xm, 1.0 - 2.0 * k / across, -0.45 * down), (xm / LENGTH, 0.5), JAW, smooth(BODY_FROM, 0.003, xm))
                       for k in range(across + 1)])
    for r in range(len(xs) - 1):
        centre = 0.5 * (mouth_y(xs[r]) + bottom(xs[r]))
        for i in range(under):
            quad = (skins[r][i], skins[r][i + 1], skins[r + 1][i + 1], skins[r + 1][i])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((middle.x, middle.y - centre, 0.0)), "jaw")
        for k in range(across):
            m.face((floors[r][k], floors[r][k + 1], floors[r + 1][k + 1], floors[r + 1][k]), Vector((0.0, 1.0, 0.0)), "mouth floor")
    for r, way, inside in ((0, -1.0, 0.0), (len(xs) - 1, 1.0, 1.0)):
        loop = skins[r] + floors[r][-2:0:-1]
        if r > 0:
            loop = [m.add(m.verts[q], (xs[r] / LENGTH, 0.5), JAW, 1.0) for q in loop]
        middle = sum((m.verts[q] for q in loop), Vector()) / len(loop)
        z = -HALF if r == 0 else JAW_TO - HALF
        tip = m.add(Vector((0.0, middle.y, z)), (xs[r] / LENGTH, 0.5), JAW, inside)
        for i in range(len(loop)):
            m.face((tip, loop[i], loop[(i + 1) % len(loop)]), Vector((0.0, 0.0, way)), "jaw" if r == 0 else "jaw end")


def dome(m, part, xe, ye, radius, height, sx, low, group):
    """A low dome lying on the skin: an eye."""
    spokes = pick(low, 20, 12, 8)
    steps = pick(low, 5, 2, 2)
    here = skin(xe, ye, sx)
    out = (skin(xe + 0.0007, ye, sx) - skin(xe - 0.0007, ye, sx)).cross(skin(xe, ye + 0.0007, sx) - skin(xe, ye - 0.0007, sx))
    out.normalize()
    if out.x * sx < 0.0:
        out = -out
    middle = m.add(here + out * height, (0.0, 0.0), part)
    last = None
    for k in range(1, steps + 1):
        r = k / steps
        row = []
        for s in range(spokes):
            a = s / spokes * TAU
            p = skin(xe + math.cos(a) * radius * r, ye + math.sin(a) * radius * r, sx)
            row.append(m.add(p + out * (height * (1.0 - r * r) + 0.0001 * (1.0 - r)), (r, 0.0), part))
        for s in range(spokes):
            n = (s + 1) % spokes
            if last is None:
                m.face((middle, row[s], row[n]), out, group)
            else:
                m.face((last[s], row[s], row[n], last[n]), out, group)
        last = row


def frame_of(direction):
    d = direction.normalized()
    ref = Vector((1.0, 0.0, 0.0)) if abs(d.x) < 0.9 else Vector((0.0, 1.0, 0.0))
    a = d.cross(ref).normalized()
    return a, d.cross(a).normalized()


def tube(m, part, path, radius, sides, segs, group, inside=0.0):
    """A closed tube along `path(t)` (t 0 to 1) of radius `radius(t)`, capped at both ends."""
    rows = []
    centres = []
    for i in range(segs + 1):
        t = i / segs
        p = path(t)
        d = path(min(1.0, t + 0.01)) - path(max(0.0, t - 0.01))
        a, b = frame_of(d)
        rows.append([m.add(p + (a * math.cos(k / sides * TAU) + b * math.sin(k / sides * TAU)) * radius(t), (t, k / sides), part, inside)
                     for k in range(sides)])
        centres.append(p)
    for i in range(segs):
        for k in range(sides):
            n = (k + 1) % sides
            quad = (rows[i][k], rows[i][n], rows[i + 1][n], rows[i + 1][k])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, middle - (centres[i] + centres[i + 1]) * 0.5, group)
    for i, t, way in ((0, 0.0, -1.0), (segs, 1.0, 1.0)):
        d = (path(min(1.0, t + 0.01)) - path(max(0.0, t - 0.01))).normalized() * way
        tip = m.add(centres[i] + d * radius(t) * 0.3, (t, 0.0), part, inside)
        for k in range(sides):
            m.face((tip, rows[i][k], rows[i][(k + 1) % sides]), d, group)


def tooth(m, part, root, direction, back, length, r0, low):
    """A long thin needle: a cone from `root` along `direction`, curved towards `back` along its length."""
    sides = pick(low, 6, 3, 4)
    segs = pick(low, 5, 2, 2)
    a, b = frame_of(direction)
    centres = []
    rows = []
    for i in range(segs):
        t = i / segs
        p = root + direction * (length * t) + back * (length * 0.18 * t * t)
        centres.append(p)
        r = r0 * (1.0 - t) ** 0.8
        rows.append([m.add(p + (a * math.cos(k / sides * TAU) + b * math.sin(k / sides * TAU)) * r, (t, k / sides), part)
                     for k in range(sides)])
    tip_at = root + direction * length + back * (length * 0.18)
    for i in range(segs - 1):
        for k in range(sides):
            n = (k + 1) % sides
            quad = (rows[i][k], rows[i][n], rows[i + 1][n], rows[i + 1][k])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, middle - (centres[i] + centres[i + 1]) * 0.5, "teeth")
    tip = m.add(tip_at, (1.0, 0.0), part)
    for k in range(sides):
        p = (m.verts[rows[-1][k]] + m.verts[rows[-1][(k + 1) % sides]]) * 0.5
        m.face((tip, rows[-1][k], rows[-1][(k + 1) % sides]), p - centres[-1], "teeth")
    if low is GAME:
        # (the game model's root, buried in the gum: one face)
        m.face(tuple(rows[0]), -direction, "teeth")
        return
    base = m.add(root - direction * r0, (0.0, 0.0), part)
    for k in range(sides):
        m.face((base, rows[0][k], rows[0][(k + 1) % sides]), -direction, "teeth")


def teeth(m, low):
    step = pick(low, 1, 2, 2)
    for sx in (1.0, -1.0):
        # the lower jaw's: long needles standing up and a little out from its lip, the longest at the front
        count = 12
        for k in range(0, count, step):
            f = k / (count - 1)
            xm = 0.004 + f * (JAW_TO - 0.022)
            lip = body_point(xm, sx * lip_angle(xm))
            line = Vector((0.0, -SLOPE, 1.0)).normalized()
            across = Vector((0.0, line.z, -line.y))
            if across.y < 0.0:
                across = -across
            direction = (across * 0.5 + Vector((0.0, 1.0, 0.0)) * 0.3 + Vector((sx * 0.5 * smooth(0.0, 0.25, f), 0.0, -0.25 * (1.0 - f)))).normalized()
            root = lip + Vector((-sx * 0.0012, -0.0015, 0.0))
            length = 0.026 * (1.0 - 0.6 * f) * (0.85 + 0.3 * ((k * 7) % 5) / 4.0)
            tooth(m, JAW_TEETH, root, direction, Vector((-sx * 0.4, 0.0, 1.0)).normalized(), length, 0.0011 * (1.0 - 0.3 * f), low)
        # the roof's: shorter, pointing down into the mouth
        count = 8
        for k in range(0, count, step):
            f = k / (count - 1)
            xm = 0.012 + f * (JAW_TO - 0.024)
            lip = body_point(xm, sx * lip_angle(xm))
            direction = Vector((-sx * 0.35, -1.0, 0.25)).normalized()
            root = lip + Vector((-sx * 0.0035, 0.0025, 0.0))
            length = 0.012 * (1.0 - 0.45 * f)
            tooth(m, TEETH, root, direction, Vector((0.0, 0.0, 1.0)), length, 0.0009, low)


# The rod and its lure, as the shader has them: where the rod rises (y, z of its root), and where the lure's
# bulb is at rest.
def rod_path(t):
    root = Vector((0.0, top(ROD_FROM) - 0.002, ROD_FROM - HALF))
    bend = root + Vector((0.0, 0.062, -0.004))
    tip = root + Vector((0.0, 0.046, -0.056))
    a = 1.0 - t
    return root * (a * a) + bend * (2.0 * a * t) + tip * (t * t)


def rod(m, low):
    tube(m, ROD, rod_path, lambda t: 0.0017 - 0.0007 * t, pick(low, 8, 4, 5), pick(low, 24, 8, 5), "rod")
    # the bulb: an egg on the end of the rod, its base along the rod's last stretch
    end = rod_path(1.0)
    d = (rod_path(1.0) - rod_path(0.97)).normalized()
    centre = end + d * 0.0072
    print("LURE centre %s" % (tuple(round(v, 4) for v in centre),))
    a, b = frame_of(d)
    lats = pick(low, 12, 5, 4)
    lons = pick(low, 20, 8, 8)
    rows = []
    for i in range(1, lats):
        u = i / lats
        theta = math.pi * u
        along = -math.cos(theta) * 0.0085
        r = math.sin(theta) * 0.0072
        rows.append([m.add(centre + d * along + (a * math.cos(k / lons * TAU) + b * math.sin(k / lons * TAU)) * r, (u, k / lons), ESCA)
                     for k in range(lons)])
    for i in range(len(rows) - 1):
        for k in range(lons):
            n = (k + 1) % lons
            quad = (rows[i][k], rows[i][n], rows[i + 1][n], rows[i + 1][k])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, middle - centre, "lure")
    for row, u, way in ((rows[0], 0.0, -1.0), (rows[-1], 1.0, 1.0)):
        pole = m.add(centre + d * (way * 0.0085), (u, 0.0), ESCA)
        for k in range(lons):
            m.face((pole, row[k], row[(k + 1) % lons]), d * way, "lure")
    # a small crest along the top of the bulb (a thin closed blade)
    up = Vector((0.0, 1.0, 0.0))
    side = d.cross(up).normalized()
    up = side.cross(d).normalized()
    if up.y < 0.0:
        up = -up
    def crest(t, u):
        return (u, t)
    def place(p):
        along = (p[0] - 0.5) * 0.01
        high = 0.005 * (1.0 - (2.0 * p[0] - 1.0) ** 2) * p[1] + 0.0
        base = centre + d * along + up * (math.sqrt(max(0.0, 1.0 - (along / 0.0085) ** 2)) * 0.0070 - 0.0008)
        return base + up * high
    blade(m, ESCA, "lure", crest, place, side, 0.0007, pick(low, 6, 1, 3), pick(low, 10, 3, 4), uv_part=lambda t, u: (1.0, 0.0))


def blade(m, part, name, point, place, facing, thick, nt, nu, round_foil=False, uv_part=None):
    """A fin: a thin closed blade. `point(t, u)` is a place in the fin's own flat (t 0 at its root to 1 at its
    tip, u 0 at its leading edge to 1 at its trailing edge), `place` puts that in the model, `facing` is the way one
    of its two skins faces. It is `thick` at its root, a foil across (nothing at either edge), thinning to nothing
    at its tip."""
    for side in (1.0, -1.0):
        grid = []
        for ti in range(nt + 1):
            t = ti / nt
            row = []
            for ui in range(nu + 1):
                u = ui / nu
                foil = 4.0 * u * (1.0 - u) if round_foil else 2.6 * math.sqrt(u) * (1.0 - u)
                swell = thick * (1.0 - t) ** 0.7 * foil + thick * 0.15 * foil
                p = place(point(t, u)) + facing * (side * swell * 0.5)
                row.append(m.add(p, uv_part(t, u) if uv_part else (t, u), part))
            grid.append(row)
        for ti in range(nt):
            for ui in range(nu):
                m.face((grid[ti][ui], grid[ti][ui + 1], grid[ti + 1][ui + 1], grid[ti + 1][ui]), facing * side, name)


def upright(p):
    """A place in the flat of the middle fins (metres behind the jaw, metres up) in the model."""
    return Vector((0.0, p[1], p[0] - HALF))


SIDE = Vector((1.0, 0.0, 0.0))
# As the shader has it: where the tail fin is hinged.
JOINT = 0.228


def fins(m, low):
    d = 3 if low is True else 1
    # (the game model's fins: few rows from root to tip, more along their rounded edges)
    g = low is GAME
    # The dorsal fin: small and rounded, far back on the back.
    def dorsal_point(t, u):
        xm = 0.168 + 0.036 * u
        high = 0.024 * math.sin(math.pi * (0.15 + 0.85 * u)) ** 0.8 * t
        return (xm + 0.012 * t * t, top(xm) - 0.002 + high + 0.002 * t)
    blade(m, DORSAL, "dorsal", dorsal_point, upright, SIDE, 0.0016, 2 if g else 8 // d, 6 if g else 14 // d, True)
    # The anal fin: smaller, under the dorsal's rear half.
    def anal_point(t, u):
        xm = 0.182 + 0.026 * u
        high = 0.018 * math.sin(math.pi * (0.15 + 0.85 * u)) ** 0.8 * t
        return (xm + 0.01 * t * t, bottom(xm) + 0.002 - high - 0.002 * t)
    blade(m, ANAL, "anal", anal_point, upright, SIDE, 0.0014, 2 if g else 6 // d, 5 if g else 10 // d, True)
    # The tail: one rounded fan.
    def tail_point(t, u):
        w = 2.0 * u - 1.0
        reach = 0.072 * (1.0 - 0.2 * w * w)
        return (0.224 + reach * t, w * (0.012 + 0.03 * smooth(0.0, 0.8, t)) * (1.0 - 0.25 * t ** 6) + mid(0.23))
    blade(m, TAIL, "tail", tail_point, upright, SIDE, 0.003, 4 if g else 16 // d, 8 if g else 14 // d, True)
    for sx in (1.0, -1.0):
        # The pectoral fins: small and rounded on short stalks low on the sides, lying back and out.
        root = skin(0.135, -0.006, sx)
        root.x -= sx * 0.002
        span = Vector((sx * 0.55, -0.1, 0.83)).normalized()
        chord = Vector((sx * 0.05, -1.0, 0.1)).normalized()
        facing = span.cross(chord).normalized()
        if facing.x * sx < 0.0:
            facing = -facing

        def pectoral_point(t, u):
            w = 2.0 * u - 1.0
            reach = 0.032 * (1.0 - 0.3 * w * w)
            wide = 0.006 + 0.016 * smooth(0.0, 0.6, t)
            return (reach * t, w * wide)

        blade(m, PECTORAL, "pectorals", pectoral_point,
              lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.0025, 2 if g else 10 // d, 4 if g else 10 // d, True)


def material_of(name, colour):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = colour
    material.diffuse_color = colour
    return material


# --- the throat and the gills (2026-11-18) ---------------------------------------------------------
# Which surface the faces being made go in. The full model keeps its first surface exactly as it was before the
# gills were added (so that Godot's importer makes the same thinned LOD meshes of it, and it looks the same at
# every distance): its throat and gills are a second surface. The low and the game models are one surface each.
SURFACE = [0]
# (the opening the throat starts from, kept by body(): the roof's last arch, and the body's points under the line
# of the mouth at the hinge, both from the left lip to the right)
THROAT = []
# As the shader has it: the gills stand from GILL_FROM back to GILL_TO (metres behind the snout's tip); WALL_UP is
# how high the full model's old wall across the back of the mouth is lifted as it opens.
GILL_FROM = JAW_TO + 0.3 * (GILL_TO - JAW_TO)
_mid = globals().get("mid", lambda xm: 0.0)


def tunnel_section(xm):
    """The throat at `xm`: (its top, its floor, its half width), well inside the body's skin."""
    up, down, wide = outline(xm)
    return _mid(xm) + 0.5 * up, _mid(xm) - 0.7 * down, 0.68 * wide


WALL_UP = _mid(JAW_TO) + 0.75 * outline(JAW_TO)[0]


def throat(m, low, top_row, bottom_row):
    """The throat: a short tunnel from the back of the mouth (its opening is `top_row`, the roof's last arch, and
    `bottom_row`, the body's points under the line of the mouth at the hinge) back past the gill arches, closed by
    a dark wall behind them. All of it is inside the mouth (UV2.x 1), so the shader colours it as the inside of the
    mouth; shut, the head hides it. Its points' UV y is 0 (the full model's old wall's are 0.5)."""
    loop = list(top_row) + list(reversed(bottom_row))
    ps = [Vector(m.verts[q]) for q in loop]
    low_y = min(p.y for p in ps)
    high_y = max(p.y for p in ps)
    wide_x = max(abs(p.x) for p in ps)
    shape = [(p.x / wide_x, (p.y - 0.5 * (low_y + high_y)) / (0.5 * (high_y - low_y))) for p in ps]
    middles = [Vector((0.0, 0.5 * (low_y + high_y), JAW_TO - HALF))]
    # (where its mouth would lie in the body's skin, under the line of the mouth, it is a hair inside it and
    # behind the hinge: lying in the skin, it changed the edge of the body's outline by a pixel; its top, along
    # the roof's edge, and its two corners on the lips are exactly where they meet)
    lift = Vector((0.0, 0.0, 0.005 * (GILL_TO - JAW_TO)))
    tops = len(top_row)
    rows = [[m.add(p if (i <= tops or i == len(ps) - 1) else middles[0].lerp(p, 0.99) + lift, (JAW_TO / LENGTH, 0.0), BODY, 1.0)
             for i, p in enumerate(ps)]]
    for f in pick(low, (0.35, 1.0), (1.0,), (1.0,)):
        xm = JAW_TO + f * (GILL_TO - JAW_TO)
        high, low_, half_w = tunnel_section(xm)
        centre = 0.5 * (high + low_)
        reach = 0.5 * (high - low_)
        rows.append([m.add(Vector((half_w * s[0], centre + reach * s[1], xm - HALF)), (xm / LENGTH, 0.0), BODY, 1.0) for s in shape])
        middles.append(Vector((0.0, centre, xm - HALF)))
    n = len(loop)
    for r in range(len(rows) - 1):
        axis = middles[r].lerp(middles[r + 1], 0.5)
        for k in range(n):
            j = (k + 1) % n
            a, b, c, d = rows[r][k], rows[r][j], rows[r + 1][j], rows[r + 1][k]
            # (as two triangles, each turned to face the tunnel's middle line)
            for tri in ((a, b, c), (a, c, d)):
                middle = sum((m.verts[q] for q in tri), Vector()) / 3.0
                m.face(tri, Vector((axis.x - middle.x, axis.y - middle.y, 0.0)), "throat")
    # the wall behind the gills: a fan, facing the mouth
    end = m.add(middles[-1] + Vector((0.0, 0.0, 0.05 * (GILL_TO - JAW_TO))), (GILL_TO / LENGTH, 0.0), BODY, 1.0)
    for k in range(n):
        m.face((end, rows[-1][k], rows[-1][(k + 1) % n]), Vector((0.0, 0.0, -1.0)), "throat end")


def gills(m, low):
    """Four gill arches a side, standing in the throat: each a curved bar from the top of the throat to its floor,
    bent back in the middle (a "<" opening forward), as a thin closed blade: its inner, front edge the pale gill
    rakers, then the bar, then the fringe of red filaments reaching back and out to the throat's wall. UV x from
    its top (0) to its foot (1), y from the rakers (0) to the filaments' tips (1). Inside the head: only seen
    through the open mouth."""
    nt = pick(low, 10, 2, 2)
    nu = pick(low, 3, 1, 1)
    span = GILL_TO - JAW_TO
    for sx in (1.0, -1.0):
        for k in range(4):
            at = GILL_FROM + 0.15 * span * k
            high, low_, half_w = tunnel_section(at)
            centre = 0.5 * (high + low_)
            reach = 0.5 * (high - low_)

            def place(t, u, at=at, centre=centre, reach=reach, half_w=half_w, sx=sx):
                y = centre + reach * 0.88 * (1.0 - 2.0 * t)
                wall = half_w * 0.95 * math.sqrt(max(0.05, 1.0 - ((y - centre) / reach) ** 2))
                xm = at + 0.12 * span * (1.0 - (2.0 * t - 1.0) ** 2)
                return Vector((sx * wall * (0.38 + 0.62 * u), y, xm - HALF + 0.25 * span * u - 0.04 * span))

            d_t = place(0.6, 0.5) - place(0.4, 0.5)
            d_u = place(0.5, 0.6) - place(0.5, 0.4)
            facing = d_t.cross(d_u).normalized()
            for side in (1.0, -1.0):
                grid = []
                for ti in range(nt + 1):
                    t = ti / nt
                    row = []
                    for ui in range(nu + 1):
                        u = ui / nu
                        # (on the full model the filaments' edge is a fringe: every other point short of it)
                        reach_u = u * (0.8 if (low is False and ui == nu and ti % 2 == 1) else 1.0)
                        foil = 2.6 * math.sqrt(reach_u) * (1.0 - reach_u) if ui < nu else 0.0
                        swell = 0.06 * span * foil * math.sin(math.pi * t) ** 0.6
                        row.append(m.add(place(t, reach_u) + facing * (side * swell * 0.5), (t, reach_u), GILL))
                    grid.append(row)
                for ti in range(nt):
                    for ui in range(nu):
                        m.face((grid[ti][ui], grid[ti][ui + 1], grid[ti + 1][ui + 1], grid[ti + 1][ui]), facing * side, "gills")


def throat_and_gills(m, low):
    """Made after everything else: on the full model, in its second surface."""
    if low is False:
        SURFACE[0] = 1
    throat(m, low, *THROAT)
    gills(m, low)
    SURFACE[0] = 0
    print("GILLS from %.4f to %.4f wall_up %.5f part %d" % (GILL_FROM, GILL_TO, WALL_UP, GILL))



def make(name, low):
    m = Mesh()
    body(m, low)
    jaw(m, low)
    for sx in (1.0, -1.0):
        dome(m, EYE, EYE_AT[0], EYE_AT[1], EYE_RADIUS, 0.0016, sx, low, "eyes")
    teeth(m, low)
    rod(m, low)
    fins(m, low)
    throat_and_gills(m, low)
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
    mesh.materials.append(material_of(NAME, (0.2, 0.18, 0.2, 1.0)))
    if 1 in m.surface:
        # (the full model's throat and gills: a second surface)
        mesh.materials.append(material_of(NAME + "_throat", (0.5, 0.1, 0.1, 1.0)))
        for poly in mesh.polygons:
            poly.material_index = m.surface[poly.index]
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    print("BUILT %s verts=%d tris=%d" % (name, len(mesh.vertices), tris))
    print("TRIS %s: %s" % (name, ", ".join("%s %d" % (k, v) for k, v in m.tris.items())))
    winding(name, mesh, m)
    return obj


def winding(name, mesh, m):
    """Nothing inside out: every face's normal (Blender's front) on the side it was meant to face."""
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
    scene.display.shading.color_type = "SINGLE"
    scene.display.shading.single_color = (0.55, 0.5, 0.5)
    scene.render.resolution_x, scene.render.resolution_y = 1000, 800
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    # (Blender space: the fish lies along Y, its nose at +Y, up is Z)
    views = [("left", (1, 0, 0), (0, 0, 0.02), 0.36), ("right", (-1, 0, 0), (0, 0, 0.02), 0.36),
             ("front", (0, 1, 0), (0, 0, 0.02), 0.26), ("back", (0, -1, 0), (0, 0, 0.02), 0.26),
             ("top", (0.001, 0, 1), (0, 0, 0), 0.36), ("under", (0.001, 0, -1), (0, 0, 0), 0.36),
             ("head", (0.8, 0.6, 0.3), (0, 0.1, 0.03), 0.16), ("headlow", (0.7, 0.6, -0.4), (0, 0.1, 0.0), 0.16)]
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
    full = make(NAME, False)
    low = make(NAME + "_lo", True)
    game = make(NAME + "_game", GAME)
    print("EYE base %s" % (tuple(round(v, 5) for v in skin(EYE_AT[0], EYE_AT[1], 1.0)),))
    print("ROD root y=%.5f z=%.5f  lure at %s" % (rod_path(0.0).y, rod_path(0.0).z, tuple(round(v, 4) for v in rod_path(1.0))))
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, NAME + ".glb"))
    export_one(game, os.path.join(OUT, NAME + "_game.glb"))
    export_one(low, os.path.join(OUT, NAME + "_lo.glb"))
    low.location.x = 0.2
    game.location.x = 0.4
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, NAME + ".blend"))
    low.location.x = 0.0
    game.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low, game])


if __name__ == "__main__":
    main()
