"""Builds the lanternfish (creatures/lanternfish) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/lanternfish/tools/build_lanternfish.py
    blender --background --python creatures/lanternfish/tools/build_lanternfish.py -- <preview folder>   # with pictures

Writes creatures/lanternfish/models/lanternfish.glb (the full model, for one seen close), lanternfish_lo.glb (far
off, phones) and lanternfish_school.glb (a very light one whose look is in its vertex colours, for hundreds drawn
by one MultiMesh), and the editable creatures/lanternfish/tools/lanternfish.blend (this folder has a .gdignore).
The full and the low model are one still mesh with one surface each: the shader (lanternfish.gdshader) draws every
marking, swims it and lights its photophores. It prints a WINDING line for each: the check that nothing is inside
out. Laid out as GameCommon's sardine (godot/sardine), whose build script this one follows.

A spotted lanternfish (Myctophum punctatum), 0.08 m from the tip of its snout to the tips of its tail, built from
the species (no picture was traced or copied):

- THE BODY: a little flattened from side to side, deepest (0.018 m) and widest (0.010 m) a quarter of the way back,
  running to a narrow tail wrist. A big blunt head with a very big eye; a large oblique mouth reaching back below
  and behind the eye; the gill cover a step.
- THE MOUTH: as the sardine's, the head ahead of the jaw's hinge is in two closed pieces that meet along the line of
  the mouth: the upper one part of the body (its underside the roof of the mouth, a wall behind it the throat), the
  LOWER JAW a part of its own (its top the floor of the mouth); the shader swings it down about its hinge (`gape`).
- THE FINS, each a thin closed blade: a dorsal fin at the middle of the back; a small adipose fin far back on it; an
  anal fin from under the dorsal's end back towards the tail; pelvic fins under the dorsal's front; pectoral fins
  behind the gill covers; a forked tail.
- THE PHOTOPHORES: small round domes lying on the skin, in the pattern of a lanternfish: a row along each side of
  the chest (five), one along the belly (four), the long anal row (seven, then three rising towards the tail), an
  oblique row of three above the belly row, one above the anal row, two at the tail wrist, two above the pectoral
  fin, and one in front of and below each eye.

Everything here is in Godot space (metres, Y up, X to its left side, its nose at -Z) until it is written out; the
origin is on its middle line, half way along (0.04 m behind the tip of its snout). `xm` below is metres behind the
tip of the snout.

It also writes models/lanternfish_game.glb, the GAME MODEL (2026-11-18): a few triangles, spent unevenly as a Twilight
Princess model spends them, on the outline, the eye, the mouth and the lights, from the same curves (see
GAME_CUTS, fitted() and pick(): `low` is False, True or GAME for the full, low and game models). The full and
low models are built exactly as before.

What a point is, for the shader: UV2.y the part (0 body, 1 the dorsal fin, 2 the anal fin, 3 the tail, 4 a pectoral
fin, 5 a pelvic fin, 6 an eye, 7 the lower jaw, 8 a photophore, 9 the adipose fin, 10 a gill arch). UV2.x: 1 inside the mouth (its
roof, floor and throat), 0 elsewhere. UV, on the body and the jaw: x how far along (0 snout to 1 tail tips), y how
high on its side (1 the ridge of the back, 0.5 its middle line, 0 the keel of the belly); on a fin: x from its root
(0) to its tip (1), y from its leading edge (0) to its trailing edge (1); on an eye or a photophore: x from its
middle (0) to its rim (1). (The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.)

The school model has no UVs: only places, normals and a colour at each point (COLOR_0, RGBA: a dark back, a silvery
flank, a paler belly, an eye on each side and the photophores, small plates lying on the skin, as small bright
blue-green plates). Its ALPHA is a glow mask: 1 on the photophores, 0 everywhere else, so that a shader can make
just them glow (EMISSION = COLOR.rgb * COLOR.a). Its fins are single sheets, drawn from both sides by whatever draws
it (GameCommon's flock.gdshader does).

The numbers marked "as the shader has it" are in lanternfish.gdshader too: change one, change the other.
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

LENGTH = 0.08
HALF = 0.04
BODY, DORSAL, ANAL, TAIL, PECTORAL, PELVIC, EYE, JAW, PHOTO, ADIPOSE = range(10)
# (the gill arches, added 2026-11-18)
GILL = 10
TAU = math.tau

# The body's outline: metres behind the snout, half its depth above its middle line, half its depth below, half
# its width.
PROFILE = [
    (0.0, 0.0, 0.0, 0.0),
    (0.0005, 0.0013, 0.0015, 0.0012),
    (0.0015, 0.0028, 0.0031, 0.0024),
    (0.003, 0.0043, 0.0046, 0.0033),
    (0.006, 0.0060, 0.0064, 0.0042),
    (0.010, 0.0074, 0.0078, 0.0048),
    (0.016, 0.0084, 0.0088, 0.0050),
    (0.024, 0.0088, 0.0090, 0.0049),
    (0.034, 0.0084, 0.0084, 0.0045),
    (0.044, 0.0072, 0.0070, 0.0038),
    (0.054, 0.0054, 0.0052, 0.0028),
    (0.060, 0.0040, 0.0038, 0.0020),
    (0.064, 0.0032, 0.0031, 0.0014),
    (0.0665, 0.0026, 0.0026, 0.0009),
    (0.0685, 0.0004, 0.0004, 0.0003),
]
BODY_FROM = 0.0002
BODY_TO = 0.0685

# As the shader has it: the line of the mouth, the edge of the gill cover, the eye.
MOUTH_TO = 0.012
EYE_AT = (0.0072, 0.0015)
EYE_RADIUS = 0.0031
# As the shader has it: how far back the lower jaw runs (its hinge is there, on the line of the mouth).
JAW_TO = 0.0125
# As the shader has it: how far back the throat and its gills reach (metres behind the snout's tip).
GILL_TO = 0.0185
SLOPE = 0.42
# The game model: rings wherever the outline bends more than GAME_TOL metres off a straight line, at most
# GAME_MOST apart, and always at GAME_CUTS (the jaw's hinge among them); GAME_AROUND points round each.
GAME_CUTS = [BODY_FROM, JAW_TO, 0.022, 0.061, BODY_TO]
GAME_TOL = 0.0005
GAME_MOST = 0.0055
GAME_AROUND = 12


def mouth_y(xm):
    return 0.0006 - SLOPE * xm


def gill_x(y):
    return 0.0195 - 60.0 * (y + 0.0005) ** 2


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
        out.append(max(a + b, 0.00006))
    return out


def top(xm):
    return outline(xm)[0]


def bottom(xm):
    return -outline(xm)[1]


def body_point(xm, angle):
    """A point of the skin: `angle` round the body from the ridge of the back (0) by its left side (a quarter
    turn) to the keel of the belly (half a turn)."""
    up, down, wide = outline(xm)
    c = math.cos(angle)
    s = math.sin(angle)
    y = c * (up if c >= 0.0 else down)
    side = math.copysign(abs(s) ** 0.85, s) * wide
    # the back and the belly a little narrower than the flanks
    side *= 1.0 - 0.15 * smooth(0.4, 1.0, abs(c)) * smooth(0.01, 0.02, xm)
    z = xm
    # the mouth: a groove from the snout's tip back and down to under the back of the eye
    if xm < MOUTH_TO + 0.001:
        groove = math.exp(-((y - mouth_y(xm)) / 0.0002) ** 2) * smooth(0.0002, 0.001, xm) * (1.0 - smooth(MOUTH_TO - 0.001, MOUTH_TO + 0.0002, xm))
        side *= 1.0 - 0.1 * groove
    # the gill cover: it stands a little proud of the body behind its edge
    behind = xm - gill_x(y)
    if behind > 0.0 and wide > 0.0008:
        mask = smooth(-0.97, -0.82, c) * (1.0 - smooth(0.6, 0.8, c))
        step = 0.00022 * smooth(0.0, 0.0005, behind) * math.exp(-behind / 0.0025) * mask
        side *= 1.0 - step / wide
    return Vector((side, y, z - HALF))


def skin(xm, y, sx):
    """The point of the skin at `xm` and height `y`, on the left side (sx 1) or the right (-1)."""
    up, down, _ = outline(xm)
    c = max(-1.0, min(1.0, y / (up if y >= 0.0 else down)))
    return body_point(xm, sx * math.acos(c))


def skin_normal(xe, ye, sx):
    e = 0.0002
    out = (skin(xe + e, ye, sx) - skin(xe - e, ye, sx)).cross(skin(xe, ye + e, sx) - skin(xe, ye - e, sx))
    out.normalize()
    if out.x * sx < 0.0:
        out = -out
    return out


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        # per point: (uv, uv2), or a colour (the school model)
        self.data = []
        self.out = []
        self.count = {}
        self.surface = []
        self.tris = {}

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
        if n.length < 1e-16:
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
    for until, step in ((JAW_TO, 0.00028), (0.022, 0.0004), (0.061, 0.0008), (BODY_TO, 0.0004)):
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
    y = mouth_y(xm)
    return math.acos(max(-0.999, min(0.999, y / (up if y >= 0.0 else down))))


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


def inside_point(xm, across, hollow):
    """A point of the roof (`hollow` up) or the floor (`hollow` down) of the mouth at `xm`: `across` 1 at the left
    lip, -1 at the right, the surface arched away from the line of the mouth between them."""
    lip = body_point(xm, lip_angle(xm))
    y = lip.y + hollow * (1.0 - across * across) * smooth(0.0005, 0.0025, xm)
    return Vector((lip.x * across * (1.0 - 0.08 * (1.0 - across * across)), y, lip.z))


def body(m, low):
    around = pick(low, 44, GAME_AROUND, 12)
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
        for c in range(around):
            n = (c + 1) % around
            quad = (grid[r][c], grid[r][n], grid[r + 1][n], grid[r + 1][c])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((middle.x, middle.y, 0.0)), "body")
    tip = m.add(Vector((0.0, 0.0, BODY_TO + 0.0001 - HALF)), ((BODY_TO + 0.0001) / LENGTH, 0.5), BODY)
    for c in range(around):
        m.face((tip, grid[-1][c], grid[-1][(c + 1) % around]), Vector((0.0, 0.0, 1.0)), "body")
    half = round(lip_angle(JAW_TO) / (TAU / around))
    across = around - 2 * half
    uppers = []
    roofs = []
    for xm in head:
        reach = lip_angle(xm)
        up = outline(xm)[0]
        uppers.append([m.add(body_point(xm, j / half * reach), (xm / LENGTH, 0.5 + 0.5 * math.cos(j / half * reach)), BODY)
                       for j in range(-half, half + 1)])
        roofs.append([m.add(inside_point(xm, 1.0 - 2.0 * k / across, 0.45 * up), (xm / LENGTH, 0.5), BODY, smooth(BODY_FROM, 0.0008, xm))
                      for k in range(across + 1)])
    first = grid[0]
    uppers.append([first[j % around] for j in range(-half, half + 1)])
    roofs.append([m.add(m.verts[first[(half + k) % around]], (JAW_TO / LENGTH, 0.5), BODY, 1.0) for k in range(across + 1)])
    for r in range(len(head)):
        for j in range(2 * half):
            quad = (uppers[r][j], uppers[r][j + 1], uppers[r + 1][j + 1], uppers[r + 1][j])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((middle.x, middle.y + 0.001, 0.0)), "body")
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
    tip = m.add(middle + Vector((0.0, 0.0, -0.0001)), (0.0, 0.5), BODY)
    for i in range(len(loop)):
        m.face((tip, loop[i], loop[(i + 1) % len(loop)]), Vector((0.0, 0.0, -1.0)), "body")


def jaw(m, low):
    """The lower jaw: the body's own skin below the line of the mouth, ahead of the hinge, closed over by the floor
    of the mouth, with an end inside the head."""
    around = pick(low, 44, GAME_AROUND, 12)
    half = round(lip_angle(JAW_TO) / (TAU / around))
    under = around - 2 * half
    across = pick(low, 10, 2, 4)
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
        floors.append([m.add(inside_point(xm, 1.0 - 2.0 * k / across, -0.4 * down), (xm / LENGTH, 0.5), JAW, smooth(BODY_FROM, 0.0008, xm))
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


def dome(m, part, xe, ye, radius, height, sx, spokes, steps, group):
    """A low dome lying on the skin: an eye, or a photophore."""
    here = skin(xe, ye, sx)
    out = skin_normal(xe, ye, sx)
    middle = m.add(here + out * height, (0.0, 0.0), part)
    last = None
    for k in range(1, steps + 1):
        r = k / steps
        row = []
        for s in range(spokes):
            a = s / spokes * TAU
            p = skin(xe + math.cos(a) * radius * r, ye + math.sin(a) * radius * r, sx)
            row.append(m.add(p + out * (height * (1.0 - r * r) + 0.00002 * (1.0 - r)), (r, 0.0), part))
        for s in range(spokes):
            n = (s + 1) % spokes
            if last is None:
                m.face((middle, row[s], row[n]), out, group)
            else:
                m.face((last[s], row[s], row[n], last[n]), out, group)
        last = row


def photophore_places():
    """Where the photophores are, on the left side (metres behind the snout, metres up; the right is the mirror),
    with their radii: in the pattern of Myctophum."""
    places = []
    for k in range(5):
        xm = 0.0165 + k * 0.0029
        places.append((xm, bottom(xm) * 0.84, 0.00056))
    for k in range(4):
        xm = 0.032 + k * 0.0031
        places.append((xm, bottom(xm) * 0.8, 0.00052))
    for k in range(7):
        xm = 0.0455 + k * 0.0021
        places.append((xm, bottom(xm) * 0.8, 0.00046))
    for k in range(3):
        xm = 0.0555 + k * 0.0019
        places.append((xm, bottom(xm) * (0.45 - 0.17 * k), 0.00042))
    for k in range(3):
        xm = 0.039 + k * 0.0014
        places.append((xm, bottom(xm) * 0.45 + k * 0.0027, 0.0005))
    places.append((0.052, top(0.052) * 0.2, 0.00045))
    places.append((0.0605, bottom(0.0605) * 0.55, 0.0004))
    places.append((0.0625, top(0.0625) * 0.1, 0.0004))
    places.append((0.0185, bottom(0.0185) * 0.25, 0.0005))
    places.append((0.0205, top(0.0205) * 0.18, 0.00048))
    places.append((0.0033, 0.0024, 0.00045))
    return places


def photophores(m, low):
    for sx in (1.0, -1.0):
        for k, (xm, y, r) in enumerate(photophore_places()):
            if low is GAME:
                plate(m, PHOTO, xm, y, r, r * 0.2, sx, "photophores")
                continue
            if low and k % 2:
                continue
            dome(m, PHOTO, xm, y, r * (1.3 if low else 1.0), r * 0.4, sx, 4 if low else 8, 1 if low else 2, "photophores")


def plate(m, part, xe, ye, radius, height, sx, group):
    """The game model's photophore: one three-cornered plate lying just off the skin, its corners marked a little
    in from its rim (UV x 0.4), so that the shader lights the whole of it."""
    out = skin_normal(xe, ye, sx)
    corners = []
    for s in range(3):
        a = s / 3.0 * TAU + 0.5 * math.pi
        p = skin(xe + math.cos(a) * radius * 1.25, ye + math.sin(a) * radius * 1.25, sx)
        corners.append(m.add(p + out * height, (0.4, 0.0), part))
    m.face(tuple(corners), out, group)


def blade(m, part, name, point, place, facing, thick, nt, nu, round_foil=False, warp=None):
    """A fin: a thin closed blade. `point(t, u)` is a place in the fin's own flat (t 0 at its root to 1 at its tip,
    u 0 at its leading edge to 1 at its trailing edge), `place` puts that in the model, `facing` is the way one of
    its two skins faces. It is `thick` at its root, a foil across (nothing at either edge), thinning towards its
    tip. `warp(u)`, if given, spaces the points across it unevenly (the game model's, close at the tall
    front of the dorsal and anal fins)."""
    for side in (1.0, -1.0):
        grid = []
        for ti in range(nt + 1):
            t = ti / nt
            row = []
            for ui in range(nu + 1):
                u = ui / nu
                if warp:
                    u = warp(u)
                foil = 4.0 * u * (1.0 - u) if round_foil else 2.6 * math.sqrt(u) * (1.0 - u)
                swell = thick * (1.0 - t) ** 0.7 * foil + thick * 0.12 * foil
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
    """A place in the flat of the middle fins (metres behind the snout, metres up) in the model."""
    return Vector((0.0, p[1], p[0] - HALF))


SIDE = Vector((1.0, 0.0, 0.0))

# The middle fins, as the school model has them too.
DORSAL_FROM, DORSAL_LONG, DORSAL_HIGH = 0.029, 0.013, 0.0072
ANAL_FROM, ANAL_LONG, ANAL_HIGH = 0.041, 0.0135, 0.0042
ADIPOSE_FROM, ADIPOSE_LONG = 0.0535, 0.004
TAIL_TIP = (0.08, 0.0088)
TAIL_NOTCH = 0.0715
# As the shader has it: where the tail fin is hinged.
JOINT = 0.0655


def side_fin(m, part, name, xm, y, sx, span, chord, size, low, d):
    root = skin(xm, y, sx)
    root.x -= sx * 0.0002
    span = Vector((sx * span[0], span[1], span[2])).normalized()
    chord = Vector((sx * chord[0], chord[1], chord[2])).normalized()
    facing = span.cross(chord).normalized()
    if facing.x * sx < 0.0:
        facing = -facing
    long, wide = size

    def point(t, u):
        t *= 0.975
        return (long * t, 0.15 * wide * t * t + (wide * (1.0 - t) ** 0.7 + 0.0001) * u)

    blade(m, part, name, point, lambda p: root + span * p[0] + chord * p[1], facing, 0.0003, pick(low, 10, 1, 10 // 3), pick(low, 6, 2, 6 // 3))


def fins(m, low):
    d = 3 if low is True else 1
    # (the game model's fins: few rows from root to tip, more along their edges)
    g = low is GAME
    lean = math.radians(30.0)

    def dorsal_point(t, u):
        xm = DORSAL_FROM + DORSAL_LONG * u
        high = DORSAL_HIGH * (0.25 + 0.75 * (1.0 - u) ** 1.2) * (0.6 + 0.4 * smooth(0.0, 0.12, u)) * t
        return (xm + math.sin(lean) * high, top(xm) - 0.0003 + math.cos(lean) * high)
    blade(m, DORSAL, "dorsal", dorsal_point, upright, SIDE, 0.00035, 1 if g else 10 // d, 5 if g else 14 // d, warp=(lambda u: u * u) if g else None)

    def anal_point(t, u):
        xm = ANAL_FROM + ANAL_LONG * u
        high = ANAL_HIGH * (0.35 + 0.65 * (1.0 - u) ** 1.2) * (0.6 + 0.4 * smooth(0.0, 0.1, u)) * t
        return (xm + math.sin(lean) * high, bottom(xm) + 0.0003 - math.cos(lean) * high)
    blade(m, ANAL, "anal", anal_point, upright, SIDE, 0.0003, 1 if g else 6 // d, 4 if g else 14 // d, warp=(lambda u: u * u) if g else None)

    def adipose_point(t, u):
        xm = ADIPOSE_FROM + ADIPOSE_LONG * u
        high = 0.0016 * (0.3 + 0.7 * math.sin(math.pi * (0.2 + 0.8 * u)) ** 0.6) * t
        return (xm + 0.0008 * t, top(xm) - 0.0003 + high)
    blade(m, ADIPOSE, "adipose", adipose_point, upright, SIDE, 0.0005, pick(low, 5, 1, 3), pick(low, 8, 3, 4), True)
    for way in (1.0, -1.0):
        tip = (TAIL_TIP[0], TAIL_TIP[1] * way)
        blade(m, TAIL, "tail", swept(((0.0635, 0.0), (0.0695, 0.0062 * way), tip),
                                      ((TAIL_NOTCH, 0.0), (0.0735, 0.0028 * way), tip)),
              upright, SIDE, 0.0005, 3 if g else 16 // d, 2 if g else 8 // max(d - 1, 1))
    for sx in (1.0, -1.0):
        side_fin(m, PECTORAL, "pectorals", 0.0195, -0.0032, sx, (0.3, -0.15, 0.94), (0.06, -0.9, 0.42), (0.0095, 0.0028), low, d)
        side_fin(m, PELVIC, "pelvics", 0.0285, bottom(0.0285) + 0.0005, sx, (0.25, -0.5, 0.83), (0.0, 0.14, 1.0), (0.0065, 0.0018), low, d)


def eyes(m, low):
    for sx in (1.0, -1.0):
        dome(m, EYE, EYE_AT[0], EYE_AT[1], EYE_RADIUS, 0.0007, sx, pick(low, 28, 12, 10), pick(low, 8, 2, 2), "eyes")


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
    eyes(m, low)
    photophores(m, low)
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
    mesh.materials.append(material_of("lanternfish", (0.3, 0.32, 0.36, 1.0)))
    if 1 in m.surface:
        # (the full model's throat and gills: a second surface)
        mesh.materials.append(material_of("lanternfish" + "_throat", (0.5, 0.1, 0.1, 1.0)))
        for poly in mesh.polygons:
            poly.material_index = m.surface[poly.index]
    return finish(name, mesh, m)


def finish(name, mesh, m):
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


# --- the school model -------------------------------------------------------------------------

# Its colours, as they are written into the points (what a shader reads as COLOR; the fourth number is the glow
# mask, 1 only on the photophores).
C_RIDGE = (0.03, 0.035, 0.05, 0.0)
C_BACK = (0.06, 0.08, 0.11, 0.0)
C_FLANK = (0.42, 0.46, 0.52, 0.0)
C_LOW = (0.55, 0.58, 0.62, 0.0)
C_BELLY = (0.3, 0.3, 0.33, 0.0)
C_EYE = (0.02, 0.02, 0.03, 0.0)
C_IRIS = (0.62, 0.66, 0.7, 0.0)
C_FIN = (0.22, 0.24, 0.27, 0.0)
C_TAIL = (0.14, 0.16, 0.19, 0.0)
C_PHOTO = (0.35, 1.0, 0.9, 1.0)
# Round the body (degrees from the ridge of the back): the ridge, the back's edge, the top of the silver, low on the
# flank, the keel; then the same up the other side.
SCHOOL_ANGLES = (0.0, 50.0, 72.0, 118.0, 180.0, 242.0, 288.0, 310.0)
SCHOOL_COLOURS = (C_RIDGE, C_BACK, C_FLANK, C_LOW, C_BELLY, C_LOW, C_FLANK, C_BACK)
SCHOOL_RINGS = (0.0006, 0.004, 0.009, 0.016, 0.026, 0.037, 0.048, 0.058, 0.0655)


def make_school(name):
    m = Mesh()
    grid = []
    for xm in SCHOOL_RINGS:
        row = []
        for angle, colour in zip(SCHOOL_ANGLES, SCHOOL_COLOURS):
            row.append(m.dab(body_point(xm, math.radians(angle)), colour))
        grid.append(row)
    around = len(SCHOOL_ANGLES)
    for r in range(len(grid) - 1):
        for c in range(around):
            n = (c + 1) % around
            quad = (grid[r][c], grid[r][n], grid[r + 1][n], grid[r + 1][c])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((middle.x, middle.y, 0.0)), "body")
    for row, xm, way, colour in ((grid[0], 0.0, -1.0, C_BACK), (grid[-1], BODY_TO, 1.0, C_FLANK)):
        tip = m.dab(Vector((0.0, 0.0, xm - HALF)), colour)
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

    def angle_at(xm, y):
        up, down, _ = outline(xm)
        return math.degrees(math.acos(max(-1.0, min(1.0, y / (up if y >= 0.0 else down)))))

    def plate(xm, angle, radius, corners, lift, colour, group):
        """A small flat plate lying on the skin: a photophore or an eye."""
        here = facet(xm, angle)
        out = (facet(xm + 0.0003, angle) - facet(xm - 0.0003, angle)).cross(facet(xm, angle + 2.0) - facet(xm, angle - 2.0))
        out.normalize()
        if out.dot(Vector((here.x, here.y, 0.0))) < 0.0:
            out = -out
        degrees = radius / max((facet(xm, angle + 5.0) - here).length, 1e-7) * 5.0
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
        # the eye: a big dark plate with a pale ring round it
        plate(EYE_AT[0], turned(angle_at(EYE_AT[0], EYE_AT[1])), EYE_RADIUS, 8, 0.00018, C_IRIS, "eyes")
        plate(EYE_AT[0], turned(angle_at(EYE_AT[0], EYE_AT[1])), EYE_RADIUS * 0.62, 6, 0.00028, C_EYE, "eyes")
        # the photophores: the chest, belly and anal rows, and the oblique row above (fewer than the full model's)
        for k, (xm, y, r) in enumerate(photophore_places()):
            if k in (1, 3, 6, 8, 10, 12, 14) or xm < 0.01:
                continue
            plate(xm, turned(angle_at(xm, y)), r * 1.25, 4, 0.00012, C_PHOTO, "photophores")

    def sheet(points, colours, out=SIDE):
        m.face(tuple(m.dab(p, c) for p, c in zip(points, colours)), out, "fins (two-sided sheets)")

    x0, x1 = DORSAL_FROM, DORSAL_FROM + DORSAL_LONG
    sheet((upright((x0, top(x0) - 0.0003)), upright((x0 + 0.004, top(x0) + DORSAL_HIGH * 0.85)), upright((x1, top(x1) - 0.0003))),
          (C_BACK, C_FIN, C_BACK))
    x0, x1 = ANAL_FROM, ANAL_FROM + ANAL_LONG
    sheet((upright((x0, bottom(x0) + 0.0003)), upright((x0 + 0.003, bottom(x0) - ANAL_HIGH)), upright((x1, bottom(x1) + 0.0003))),
          (C_BELLY, C_FIN, C_BELLY))
    for way in (1.0, -1.0):
        sheet((upright((0.064, 0.0026 * way)), upright((TAIL_TIP[0], TAIL_TIP[1] * way)), upright((TAIL_NOTCH, 0.0)), upright((0.064, 0.0))),
              (C_TAIL, C_TAIL, C_FIN, C_FLANK))
    for sx in (1.0, -1.0):
        root = facet(0.0195, 112.0 if sx > 0.0 else 248.0)
        span = Vector((sx * 0.30, -0.15, 0.94)).normalized()
        chord = Vector((sx * 0.06, -0.9, 0.42)).normalized()
        out = span.cross(chord)
        if out.x * sx < 0.0:
            out = -out
        sheet((root, root + span * 0.009 + chord * 0.0012, root + span * 0.003 + chord * 0.0028), (C_LOW, C_FIN, C_FIN), out)

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) for p in m.verts], [], m.faces)
    mesh.color_attributes.new(name="Col", type="FLOAT_COLOR", domain="POINT")
    colours = mesh.color_attributes["Col"]
    for i, colour in enumerate(m.data):
        colours.data[i].color = colour
    # (the glTF writer only writes the colour that is marked for rendering)
    mesh.color_attributes.active_color = colours
    mesh.color_attributes.render_color_index = 0
    mesh.materials.append(material_of("lanternfish_school", (1.0, 1.0, 1.0, 1.0)))
    return finish(name, mesh, m)


def winding(name, mesh, m):
    """Nothing inside out: the skin of the body faces away from its middle line, each skin of a fin away from the
    fin's own flat, an eye or a photophore out from the body (Blender's front is the side a face's normal is on)."""
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
    scene.display.shading.show_backface_culling = True
    scene.render.resolution_x, scene.render.resolution_y = 1400, 800
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    views = [("left", (1, 0, 0), (0, 0, 0), 0.09), ("right", (-1, 0, 0), (0, 0, 0), 0.09),
             ("front", (0, 1, 0), (0, 0, 0), 0.035), ("back", (0, -1, 0), (0, 0, 0), 0.035),
             ("top", (0.001, 0, 1), (0, 0, 0), 0.15), ("under", (0.001, 0, -1), (0, 0, 0), 0.15),
             ("head", (0.8, 0.5, 0.2), (0, 0.027, 0), 0.035), ("belly", (0.6, 0.1, -0.8), (0, 0.0, 0), 0.07)]
    for prefix, obj, only in (("", made[0], None), ("lo_", made[1], ("left", "head", "top")),
                              ("school_", made[2], ("left", "top", "front", "head", "belly"))):
        scene.display.shading.color_type = "VERTEX" if prefix == "school_" else "MATERIAL"
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
    full = make("lanternfish", False)
    low = make("lanternfish_lo", True)
    game = make("lanternfish_game", GAME)
    print("EYE base %s" % (tuple(round(v, 5) for v in skin(EYE_AT[0], EYE_AT[1], 1.0)),))
    school = make_school("lanternfish_school")
    print("HINGE y=%.5f" % mouth_y(JAW_TO))
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, "lanternfish.glb"))
    export_one(low, os.path.join(OUT, "lanternfish_lo.glb"))
    export_one(game, os.path.join(OUT, "lanternfish_game.glb"))
    export_one(school, os.path.join(OUT, "lanternfish_school.glb"), True)
    low.location.x = 0.03
    school.location.x = 0.06
    game.location.x = 0.09
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "lanternfish.blend"))
    low.location.x = 0.0
    school.location.x = 0.0
    game.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low, school])


if __name__ == "__main__":
    main()
