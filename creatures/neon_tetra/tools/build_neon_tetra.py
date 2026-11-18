"""Builds the neon tetra and the cardinal tetra (creatures/neon_tetra) and exports them for Godot.

Run from the game's root:
    blender --background --python creatures/neon_tetra/tools/build_neon_tetra.py
    blender --background --python creatures/neon_tetra/tools/build_neon_tetra.py -- <preview folder>   # with pictures

Writes, for each type (neon, cardinal), creatures/neon_tetra/models/<type>_tetra.glb (the full model),
<type>_tetra_lo.glb (far off, phones) and <type>_tetra_school.glb (a very light one whose look is in its vertex
colours, for hundreds drawn by one MultiMesh), and the editable creatures/neon_tetra/tools/neon_tetra.blend (all
six; this folder has a .gdignore). The full and the low models are one still mesh with one surface each: the
shader (neon_tetra.gdshader) draws every marking and swims it. It prints a WINDING line for each: the check that
nothing is inside out.

Two small characins of South American blackwater streams, built from the species (no picture was traced or
copied):

- THE NEON TETRA (Paracheirodon innesi), 0.035 m from the tip of its jaw to the tips of its tail: a slender
  spindle, a little flattened from side to side, a short blunt head with a big eye, a small terminal mouth.
- THE CARDINAL TETRA (Paracheirodon axelrodi), 0.042 m: the same build, a little deeper in the body.
- THE MOUTH: the head ahead of the jaw's hinge is in two closed pieces that meet along the line of the mouth.
  The upper one is part of the body: its underside is the roof of the mouth, and a wall behind it is the throat.
  The LOWER JAW is a part of its own, its top the floor of the mouth; the shader swings it down about its hinge
  (`gape`). Shut, the two lie lip to lip and the fish's outline is that of one whole body.
- THE FINS, each a thin closed blade (two skins that meet at its edges): a small dorsal fin just behind the
  middle, the small adipose fin behind it (a characin's mark), a long anal fin under the back half, a forked
  tail, small pelvic fins and pectoral fins set low behind the gill covers.

Everything here is built in BODY LENGTHS (the tip of the jaw at 0, the tips of the tail at 1), in Godot's axes
(Y up, X to its left side, its nose at -Z), with the origin on its middle line half way along; it is multiplied
by the type's length (metres) only as it is written out. `xm` below is body lengths behind the tip of the jaw.

What a point is, for the shader: UV2.y the part (0 body, 1 the dorsal fin, 2 the anal fin, 3 the tail, 4 a
pectoral fin, 5 a pelvic fin, 6 an eye, 7 the lower jaw, 8 the adipose fin). UV2.x: 1 inside the mouth (its
roof, floor and throat), 0 elsewhere. UV, on the body and the jaw: x how far along (0 jaw to 1 tail tips), y how
high on its side (1 the ridge of the back, 0.5 its middle line, 0 the keel of the belly); on a fin: x from its
root (0) to its tip (1), y from its leading edge (0) to its trailing edge (1); on an eye: x from its middle (0)
to its rim (1). (The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.)

The school models have no UVs: only places, normals and a colour at each point (COLOR_0). Their fins are single
sheets, drawn from both sides by whatever draws them (GameCommon's flock.gdshader does).

The numbers marked "as the shader has it" are in neon_tetra.gdshader too (in body lengths there as well):
change one, change the other.
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

HALF = 0.5
BODY, DORSAL, ANAL, TAIL, PECTORAL, PELVIC, EYE, JAW, ADIPOSE = range(9)
TAU = math.tau

# Each type: its length (metres, jaw to tail tips) and how much deeper its body is than the neon's.
TYPES = {
    "neon": {"length": 0.035, "deep": 1.0},
    "cardinal": {"length": 0.042, "deep": 1.07},
}

# The body's outline (the neon's): body lengths behind the jaw, half its depth above its middle line, half
# its depth below, half its width.
PROFILE = [
    (0.0, 0.0, 0.0, 0.0),
    (0.004, 0.008, 0.010, 0.007),
    (0.014, 0.022, 0.026, 0.017),
    (0.032, 0.040, 0.046, 0.029),
    (0.056, 0.057, 0.064, 0.038),
    (0.095, 0.076, 0.084, 0.047),
    (0.145, 0.092, 0.101, 0.053),
    (0.215, 0.104, 0.115, 0.057),
    (0.295, 0.110, 0.122, 0.058),
    (0.375, 0.108, 0.119, 0.056),
    (0.455, 0.100, 0.104, 0.050),
    (0.535, 0.085, 0.083, 0.043),
    (0.615, 0.068, 0.063, 0.034),
    (0.695, 0.053, 0.048, 0.026),
    (0.755, 0.043, 0.040, 0.020),
    (0.795, 0.039, 0.037, 0.014),
    (0.818, 0.030, 0.029, 0.008),
    (0.832, 0.004, 0.004, 0.002),
]
BODY_FROM = 0.003
BODY_TO = 0.832

# As the shader has it: the line of the mouth, the eye, the lower jaw (its hinge is at JAW_TO, on the line
# of the mouth), the tail fin's hinge.
MOUTH_TO = 0.05
EYE_AT = (0.085, 0.016)
EYE_RADIUS = 0.042
JAW_TO = 0.052
JOINT = 0.812


def mouth_y(xm):
    return -0.006 - 0.22 * xm


def gill_x(y):
    return 0.2 - 9.0 * (y + 0.01) ** 2


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
TYPE = {}


def use(name):
    """Makes `name` the type being built: its outline."""
    TYPE.clear()
    TYPE.update(TYPES[name])
    TYPE["name"] = name
    _CURVES.clear()
    for column, deep in ((1, TYPE["deep"]), (2, TYPE["deep"]), (3, 1.0)):
        ys = [p[column] * deep for p in PROFILE]
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
        out.append(max(a + b, 0.001))
    return out


def top(xm):
    return outline(xm)[0]


def bottom(xm):
    return -outline(xm)[1]


def body_point(xm, angle):
    """A point of the skin: `angle` round the body from the ridge of the back (0) by its left side (a
    quarter turn) to the keel of the belly (half a turn)."""
    up, down, wide = outline(xm)
    c = math.cos(angle)
    s = math.sin(angle)
    y = c * (up if c >= 0.0 else down)
    side = math.copysign(abs(s) ** 0.85, s) * wide
    # the belly a little narrower than the back
    side *= 1.0 - 0.12 * smooth(0.2, 1.0, -c)
    # the mouth: a groove from the tip of the jaw back to its corner
    if xm < MOUTH_TO + 0.01:
        groove = math.exp(-((y - mouth_y(xm)) / 0.004) ** 2) * smooth(0.003, 0.014, xm) * (1.0 - smooth(MOUTH_TO - 0.012, MOUTH_TO + 0.003, xm))
        side *= 1.0 - 0.12 * groove
    # the gill cover: it stands a little proud of the body behind its edge
    behind = xm - gill_x(y)
    if behind > 0.0 and wide > 0.01:
        mask = smooth(-0.97, -0.82, c) * (1.0 - smooth(0.45, 0.65, c))
        step = 0.003 * smooth(0.0, 0.006, behind) * math.exp(-behind / 0.03) * mask
        side *= 1.0 - step / wide
    return Vector((side, y, xm - HALF))


def skin(xm, y, sx):
    """The point of the skin at `xm` and height `y`, on the left side (sx 1) or the right (-1)."""
    up, down, _ = outline(xm)
    c = max(-1.0, min(1.0, y / (up if y >= 0.0 else down)))
    return body_point(xm, sx * math.acos(c))


def to_b(p):
    """Godot's axes to Blender's, and body lengths to metres."""
    s = TYPE["length"]
    return Vector((p.x * s, -p.z * s, p.y * s))


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


def rings(low):
    xs = []
    x = BODY_FROM
    for until, step in ((JAW_TO, 0.0065), (0.25, 0.013), (0.78, 0.026), (BODY_TO, 0.009)):
        if low:
            step *= 4.0
        n = max(1, round((until - x) / step))
        for i in range(n):
            xs.append(x + (until - x) * i / n)
        x = until
    xs.append(BODY_TO)
    return xs


AROUND = [32]


def raw_lip_angle(xm):
    up, down, _ = outline(xm)
    y = mouth_y(xm)
    return math.acos(max(-0.999, min(0.999, y / (up if y >= 0.0 else down))))


def lip_angle(xm):
    """How far round the body from the ridge of the back the line of the mouth is, at `xm` (eased, towards
    the hinge, onto the column of the body's points nearest to it, so that the lip meets that column)."""
    snap = round(raw_lip_angle(JAW_TO) / (TAU / AROUND[0])) * TAU / AROUND[0]
    return raw_lip_angle(xm) + (snap - raw_lip_angle(JAW_TO)) * smooth(0.0, JAW_TO, xm)


def inside_point(xm, across, hollow):
    """A point of the roof (`hollow` up) or the floor (`hollow` down) of the mouth at `xm`: `across` 1 at the
    left lip, -1 at the right, the surface arched away from the line of the mouth between them."""
    lip = body_point(xm, lip_angle(xm))
    y = lip.y + hollow * (1.0 - across * across) * smooth(0.16 * JAW_TO, 0.47 * JAW_TO, xm)
    return Vector((lip.x * across, y, xm - HALF))


def body(m, low):
    around = 10 if low else 32
    xs = rings(low)
    head = [xm for xm in xs if xm < JAW_TO - 1e-9]
    xs = xs[len(head):]
    grid = []
    for xm in xs:
        row = []
        for c in range(around):
            angle = c / around * TAU
            row.append(m.add(body_point(xm, angle), (xm, 0.5 + 0.5 * math.cos(angle)), BODY))
        grid.append(row)
    for r in range(len(grid) - 1):
        for c in range(around):
            n = (c + 1) % around
            quad = (grid[r][c], grid[r][n], grid[r + 1][n], grid[r + 1][c])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((middle.x, middle.y, 0.0)), "body")
    # the end inside the tail: a fan
    tip = m.add(Vector((0.0, 0.0, BODY_TO + 0.002 - HALF)), (BODY_TO + 0.002, 0.5), BODY)
    for c in range(around):
        m.face((tip, grid[-1][c], grid[-1][(c + 1) % around]), Vector((0.0, 0.0, 1.0)), "body")
    # The head ahead of the jaw's hinge: its skin above the line of the mouth (`half` columns each side of
    # the ridge, the last on the lip), and the roof of the mouth under it, lip to lip.
    half = round(lip_angle(JAW_TO) / (TAU / around))
    across = around - 2 * half
    uppers = []
    roofs = []
    for xm in head:
        reach = lip_angle(xm)
        up = outline(xm)[0]
        uppers.append([m.add(body_point(xm, j / half * reach), (xm, 0.5 + 0.5 * math.cos(j / half * reach)), BODY)
                       for j in range(-half, half + 1)])
        roofs.append([m.add(inside_point(xm, 1.0 - 2.0 * k / across, 0.4 * up), (xm, 0.5), BODY, smooth(BODY_FROM, 0.12 * JAW_TO, xm))
                      for k in range(across + 1)])
    # (where they join the whole body: its own points above the line of the mouth; below it the throat, a
    # wall across the back of the mouth, on the places of the body's points there)
    first = grid[0]
    uppers.append([first[j % around] for j in range(-half, half + 1)])
    roofs.append([m.add(m.verts[first[(half + k) % around]], (JAW_TO, 0.5), BODY, 1.0) for k in range(across + 1)])
    # (the throat has points of its own where it meets the roof, so that their shading is not shared)
    throat_top = []
    for q in roofs[len(head) - 1]:
        throat_top.append(m.add(m.verts[q], (0.0, 0.0), BODY, 1.0))
        m.data[-1] = (m.data[q][0], (1.0, 1.0 - BODY))
    for r in range(len(head)):
        for j in range(2 * half):
            quad = (uppers[r][j], uppers[r][j + 1], uppers[r + 1][j + 1], uppers[r + 1][j])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((middle.x, middle.y + 0.01, 0.0)), "body")
        for k in range(across):
            quad = (roofs[r][k], roofs[r][k + 1], roofs[r + 1][k + 1], roofs[r + 1][k])
            if r < len(head) - 1:
                m.face(quad, Vector((0.0, -1.0, 0.0)), "mouth roof")
            else:
                # (as two triangles, each turned to face the mouth: at the corners the quad is a twisted sliver)
                a, b, c, d = throat_top[k], throat_top[k + 1], roofs[r + 1][k + 1], roofs[r + 1][k]
                m.face((a, b, c), Vector((0.0, -0.3, -1.0)), "throat")
                m.face((a, c, d), Vector((0.0, -0.3, -1.0)), "throat")
    # the tip of the snout: a fan over the end of both
    loop = uppers[0] + roofs[0][1:-1]
    middle = sum((m.verts[q] for q in loop), Vector()) / len(loop)
    tip = m.add(middle + Vector((0.0, 0.0, -0.0015)), (0.0, 0.5), BODY)
    for i in range(len(loop)):
        m.face((tip, loop[i], loop[(i + 1) % len(loop)]), Vector((0.0, 0.0, -1.0)), "body")


def jaw(m, low):
    """The lower jaw: the body's own skin below the line of the mouth, ahead of the hinge, closed over by
    the floor of the mouth, with an end inside the head."""
    around = 10 if low else 32
    # (as many columns as the body has below the line of the mouth, so that its end meets the body point for point)
    half = round(lip_angle(JAW_TO) / (TAU / around))
    under = around - 2 * half
    across = 4 if low else 8
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
                angle = (half + i) / around * TAU
            row.append(m.add(body_point(xm, angle), (xm, 0.5 + 0.5 * math.cos(angle)), JAW))
        skins.append(row)
        floors.append([m.add(inside_point(xm, 1.0 - 2.0 * k / across, -0.45 * down), (xm, 0.5), JAW, smooth(BODY_FROM, 0.12 * JAW_TO, xm))
                       for k in range(across + 1)])
    for r in range(len(xs) - 1):
        centre = 0.5 * (mouth_y(xs[r]) - outline(xs[r])[1])
        for i in range(under):
            quad = (skins[r][i], skins[r][i + 1], skins[r + 1][i + 1], skins[r + 1][i])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((middle.x, middle.y - centre, 0.0)), "jaw")
        for k in range(across):
            m.face((floors[r][k], floors[r][k + 1], floors[r + 1][k + 1], floors[r + 1][k]), Vector((0.0, 1.0, 0.0)), "mouth floor")
    # its tip, and its end inside the head: a fan each
    for r, z, way, inside in ((0, -HALF, -1.0, 0.0), (len(xs) - 1, JAW_TO - HALF, 1.0, 1.0)):
        loop = skins[r] + floors[r][-2:0:-1]
        if r > 0:
            # (points of its own, so that the skin's shading does not turn towards the end)
            loop = [m.add(m.verts[q], (xs[r], 0.5), JAW, 1.0) for q in loop]
        middle = sum((m.verts[q] for q in loop), Vector()) / len(loop)
        tip = m.add(Vector((0.0, 0.0 if r == 0 else middle.y, z)), (xs[r], 0.5), JAW, inside)
        for i in range(len(loop)):
            m.face((tip, loop[i], loop[(i + 1) % len(loop)]), Vector((0.0, 0.0, way)), "jaw" if r == 0 else "jaw end")


def eye(m, sx, low):
    """A low dome lying on the skin of the head."""
    spokes = 8 if low else 20
    steps = 1 if low else 5
    xe, ye = EYE_AT
    e = 0.004
    here = skin(xe, ye, sx)
    out = (skin(xe + e, ye, sx) - skin(xe - e, ye, sx)).cross(skin(xe, ye + e, sx) - skin(xe, ye - e, sx))
    out.normalize()
    if out.x * sx < 0.0:
        out = -out
    middle = m.add(here + out * 0.24 * EYE_RADIUS, (0.0, 0.0), EYE)
    last = None
    for k in range(1, steps + 1):
        r = k / steps
        row = []
        for s in range(spokes):
            a = s / spokes * TAU
            p = skin(xe + math.cos(a) * EYE_RADIUS * r, ye + math.sin(a) * EYE_RADIUS * r, sx)
            row.append(m.add(p + out * EYE_RADIUS * (0.22 * (1.0 - r * r) + 0.02 * (1.0 - r) + 0.025), (r, 0.0), EYE))
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
    """A place in the flat of the middle fins (body lengths behind the jaw, up) in the model."""
    return Vector((0.0, p[1], p[0] - HALF))


SIDE = Vector((1.0, 0.0, 0.0))

# The middle fins, as the school model has them too.
DORSAL_FROM, DORSAL_LONG, DORSAL_HIGH = 0.465, 0.075, 0.105
ADIPOSE_FROM, ADIPOSE_LONG, ADIPOSE_HIGH = 0.675, 0.04, 0.03
ANAL_FROM, ANAL_LONG, ANAL_HIGH = 0.525, 0.215, 0.07
TAIL_TIP = (1.0, 0.108)
TAIL_NOTCH = 0.905


def dorsal_high(u):
    return DORSAL_HIGH * (0.25 + 0.75 * (1.0 - u) ** 1.3) * (0.5 + 0.5 * smooth(0.0, 0.14, u))


def anal_high(u):
    return ANAL_HIGH * (0.35 + 0.65 * (1.0 - u) ** 1.6) * (0.55 + 0.45 * smooth(0.0, 0.1, u))


def fins(m, low):
    d = 3 if low else 1
    # The dorsal fin: small, just behind the middle, tallest at its front, leaning back.
    lean = math.radians(24.0)

    def dorsal_point(t, u):
        xm = DORSAL_FROM + DORSAL_LONG * u
        high = dorsal_high(u) * t
        return (xm + math.sin(lean) * high, top(xm) - 0.004 + math.cos(lean) * high + 0.004 * t)

    blade(m, DORSAL, "dorsal", dorsal_point, upright, SIDE, 0.006, 8 // d, 8 // d)

    # The adipose fin: a small rounded lobe on the back between the dorsal and the tail.
    def adipose_point(t, u):
        xm = ADIPOSE_FROM + ADIPOSE_LONG * u
        high = ADIPOSE_HIGH * math.sin(math.pi * min(1.0, u * 1.15) ** 0.8) ** 0.7 * t
        return (xm + 0.25 * high, top(xm) - 0.003 + high + 0.003 * t)

    blade(m, ADIPOSE, "adipose", adipose_point, upright, SIDE, 0.006, max(1, 4 // d), max(2, 6 // d))
    # The anal fin: long, under the back half, tallest at its front.
    lean_a = math.radians(30.0)

    def anal_point(t, u):
        xm = ANAL_FROM + ANAL_LONG * u
        high = anal_high(u) * t
        return (xm + math.sin(lean_a) * high, bottom(xm) + 0.004 - math.cos(lean_a) * high - 0.004 * t)

    blade(m, ANAL, "anal", anal_point, upright, SIDE, 0.005, 6 // d, 14 // d)
    # The tail: forked, two pointed lobes that meet along the middle line.
    for way in (1.0, -1.0):
        tip = (TAIL_TIP[0], TAIL_TIP[1] * way)
        blade(m, TAIL, "tail", swept(((0.796, 0.0), (0.862, 0.085 * way), tip),
                                      ((TAIL_NOTCH, 0.0), (0.93, 0.04 * way), tip)),
              upright, SIDE, 0.009, 12 // d, 6 // max(d - 1, 1))
    for sx in (1.0, -1.0):
        # The pectoral fins: set low behind the gill covers, lying back and a little down and out.
        root = skin(0.17, -0.05, sx)
        root.x -= sx * 0.003
        span = Vector((sx * 0.32, -0.24, 0.92)).normalized()
        chord = Vector((sx * 0.08, -0.86, 0.45)).normalized()
        facing = span.cross(chord).normalized()
        if facing.x * sx < 0.0:
            facing = -facing

        def pectoral_point(t, u):
            t *= 0.975
            wide_here = 0.042 * (0.4 + 0.6 * smooth(0.0, 0.4, t)) * (1.0 - t) ** 0.6 + 0.002
            return (0.12 * t, 0.014 * t * t + wide_here * u)

        blade(m, PECTORAL, "pectorals", pectoral_point,
              lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.005, 6 // d, 5 // max(d - 1, 1))
        # The pelvic fins: small, a little ahead of the dorsal, pointing back and down.
        root = Vector((sx * 0.012, bottom(0.41) + 0.006, 0.41 - HALF))
        span = Vector((sx * 0.26, -0.5, 0.83)).normalized()
        chord = Vector((0.0, 0.14, 1.0)).normalized()
        facing = span.cross(chord).normalized()
        if facing.x * sx < 0.0:
            facing = -facing

        def pelvic_point(t, u):
            t *= 0.97
            return (0.06 * t, 0.008 * t * t + (0.022 * (1.0 - t) ** 0.8 + 0.0015) * u)

        blade(m, PELVIC, "pelvics", pelvic_point,
              lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.004, max(1, 5 // d), max(2, 4 // d))


def material_of(name, colour):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = colour
    material.diffuse_color = colour
    return material


def make(name, low):
    AROUND[0] = 10 if low else 32
    m = Mesh()
    body(m, low)
    jaw(m, low)
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
    mesh.materials.append(material_of("neon_tetra", (0.45, 0.55, 0.65, 1.0)))
    return finish(name, mesh, m)


def finish(name, mesh, m):
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    print("BUILT %s verts=%d tris=%d" % (name, len(mesh.vertices), tris))
    winding(name, mesh, m)
    return obj


# --- the school models ------------------------------------------------------------------------

# Their colours, as they are written into the points (what a shader reads as COLOR).
C_RIDGE = (0.10, 0.09, 0.05)
C_BACK = (0.26, 0.24, 0.14)
C_LINE = (0.07, 0.07, 0.06)
C_STRIPE = (0.10, 0.75, 0.95)
C_STRIPE_EDGE = (0.10, 0.45, 0.70)
C_RED = (0.80, 0.08, 0.06)
C_SILVER = (0.78, 0.80, 0.82)
C_BELLY = (0.93, 0.93, 0.92)
C_EYE = (0.01, 0.01, 0.015)
C_FIN = (0.62, 0.64, 0.66)
C_TAIL = (0.55, 0.50, 0.46)
# Round the body (degrees from the ridge of the back): the ridge, the back, the line above the stripe, the
# stripe's top, middle and foot, under it, low on the flank, the keel; then the same up the other side.
SCHOOL_ANGLES = (0.0, 40.0, 56.0, 64.0, 74.0, 84.0, 100.0, 135.0, 180.0)
SCHOOL_RINGS = (0.005, 0.03, 0.07, 0.13, 0.22, 0.33, 0.44, 0.54, 0.65, 0.74, 0.81)


def school_colour(xm, k):
    """The colour of the school model at `xm`, at SCHOOL_ANGLES[k]."""
    red_from = 0.05 if TYPE["name"] == "cardinal" else 0.43
    striped = 0.06 < xm < 0.72
    reddened = xm > red_from and xm < 0.8
    if k == 0:
        return C_RIDGE
    if k == 1:
        return C_BACK
    if k == 2:
        return C_LINE if striped else C_BACK
    if k in (3, 5):
        return C_STRIPE_EDGE if striped else (C_BACK if k == 3 else C_SILVER)
    if k == 4:
        return C_STRIPE if striped else C_SILVER
    if k == 6:
        return C_RED if reddened and xm > 0.12 else C_SILVER
    if k == 7:
        return C_RED if reddened else C_SILVER
    return C_RED if reddened and TYPE["name"] == "cardinal" and 0.2 < xm < 0.72 else C_BELLY


def make_school(name):
    m = Mesh()
    angles = list(SCHOOL_ANGLES) + [360.0 - a for a in reversed(SCHOOL_ANGLES[1:-1])]
    kinds = list(range(len(SCHOOL_ANGLES))) + list(reversed(range(1, len(SCHOOL_ANGLES) - 1)))
    around = len(angles)
    grid = []
    for xm in SCHOOL_RINGS:
        grid.append([m.dab(body_point(xm, math.radians(a)), school_colour(xm, k)) for a, k in zip(angles, kinds)])
    for r in range(len(grid) - 1):
        for c in range(around):
            n = (c + 1) % around
            quad = (grid[r][c], grid[r][n], grid[r + 1][n], grid[r + 1][c])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((middle.x, middle.y, 0.0)), "body")
    for row, xm, way, colour in ((grid[0], 0.0, -1.0, C_SILVER), (grid[-1], BODY_TO, 1.0, C_SILVER)):
        tip = m.dab(Vector((0.0, 0.0, xm - HALF)), colour)
        for c in range(around):
            m.face((tip, row[c], row[(c + 1) % around]), Vector((0.0, 0.0, way)), "body")

    def facet(xm, angle):
        """The point of this model's own flat-sided skin at `xm` and `angle` (degrees, 0 to 360)."""
        r = 0
        while r < len(SCHOOL_RINGS) - 2 and xm > SCHOOL_RINGS[r + 1]:
            r += 1
        t = (xm - SCHOOL_RINGS[r]) / (SCHOOL_RINGS[r + 1] - SCHOOL_RINGS[r])
        full = angles + [360.0]
        c = 0
        while c < around - 1 and angle > full[c + 1]:
            c += 1
        u = (angle - full[c]) / (full[c + 1] - full[c])
        n = (c + 1) % around
        a = m.verts[grid[r][c]].lerp(m.verts[grid[r][n]], u)
        b = m.verts[grid[r + 1][c]].lerp(m.verts[grid[r + 1][n]], u)
        return a.lerp(b, t)

    # the eyes: small flat plates lying on the skin
    for sx in (1.0, -1.0):
        angle = 76.0 if sx > 0.0 else 284.0
        here = facet(EYE_AT[0], angle)
        out = (facet(EYE_AT[0] + 0.005, angle) - facet(EYE_AT[0] - 0.005, angle)).cross(facet(EYE_AT[0], angle + 2.0) - facet(EYE_AT[0], angle - 2.0))
        out.normalize()
        if out.dot(Vector((here.x, here.y, 0.0))) < 0.0:
            out = -out
        degrees = EYE_RADIUS * 0.95 / max((facet(EYE_AT[0], angle + 5.0) - here).length, 1e-6) * 5.0
        ring = []
        for k in range(6):
            a = k / 6 * TAU
            p = facet(EYE_AT[0] + math.cos(a) * EYE_RADIUS * 0.95, angle + math.sin(a) * degrees)
            ring.append(m.dab(p + out * 0.004, C_EYE))
        for k in range(1, 5):
            m.face((ring[0], ring[k], ring[k + 1]), out, "eyes")

    # The fins: single sheets (drawn from both sides).
    def sheet(points, colours, out=SIDE):
        m.face(tuple(m.dab(p, c) for p, c in zip(points, colours)), out, "fins (two-sided sheets)")

    x0, x1 = DORSAL_FROM, DORSAL_FROM + DORSAL_LONG
    sheet((upright((x0, top(x0) - 0.004)), upright((x0 + 0.04, top(x0) + DORSAL_HIGH * 0.9)), upright((x1, top(x1) - 0.004))),
          (C_BACK, C_FIN, C_BACK))
    x0, x1 = ADIPOSE_FROM, ADIPOSE_FROM + ADIPOSE_LONG
    sheet((upright((x0, top(x0) - 0.003)), upright((x0 + 0.025, top(x0) + ADIPOSE_HIGH)), upright((x1, top(x1) - 0.003))),
          (C_BACK, C_FIN, C_BACK))
    x0, x1 = ANAL_FROM, ANAL_FROM + ANAL_LONG
    sheet((upright((x0, bottom(x0) + 0.004)), upright((x0 + 0.03, bottom(x0) - ANAL_HIGH)), upright((x1, bottom(x1) + 0.004))),
          (C_BELLY, C_FIN, C_BELLY))
    for way in (1.0, -1.0):
        sheet((upright((0.79, 0.03 * way)), upright((TAIL_TIP[0], TAIL_TIP[1] * way)), upright((TAIL_NOTCH, 0.0)), upright((0.79, 0.0))),
              (C_TAIL, C_FIN, C_FIN, C_TAIL))

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) for p in m.verts], [], m.faces)
    mesh.color_attributes.new(name="Col", type="FLOAT_COLOR", domain="POINT")
    colours = mesh.color_attributes["Col"]
    for i, colour in enumerate(m.data):
        colours.data[i].color = (colour[0], colour[1], colour[2], 1.0)
    # (the glTF writer only writes the colour that is marked for rendering)
    mesh.color_attributes.active_color = colours
    mesh.color_attributes.render_color_index = 0
    material = material_of("neon_tetra_school", (1.0, 1.0, 1.0, 1.0))
    mesh.materials.append(material)
    return finish(name, mesh, m)


def winding(name, mesh, m):
    """Nothing inside out: the skin of the body faces away from its middle line, each skin of a fin away
    from the fin's own flat, an eye out from the body (Blender's front is the side a face's normal is on)."""
    bad = {}
    for poly in mesh.polygons:
        out, group = m.out[poly.index]
        o = Vector((out.x, -out.z, out.y))
        if poly.normal.dot(o) <= 0.0:
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


def render(folder, made, length, prefix_name):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.show_cavity = True
    scene.render.resolution_x, scene.render.resolution_y = 1400, 800
    if scene.world is None:
        scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.get("Camera")
    if camera is None:
        camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
        camera.data.type = "ORTHO"
        camera.data.clip_end = 1000.0
        scene.collection.objects.link(camera)
    scene.camera = camera
    L = length
    # (Blender space: the fish lies along Y, its nose at +Y, up is Z)
    views = [("left", (1, 0, 0), (0, 0, 0), 1.15 * L), ("right", (-1, 0, 0), (0, 0, 0), 1.15 * L),
             ("front", (0, 1, 0), (0, 0, 0), 0.45 * L), ("back", (0, -1, 0), (0, 0, 0), 0.45 * L),
             ("top", (0.001, 0, 1), (0, 0, 0), 2.0 * L), ("under", (0.001, 0, -1), (0, 0, 0), 2.0 * L),
             ("head", (0.8, 0.5, 0.2), (0, 0.36 * L, 0), 0.4 * L), ("tail", (0.7, -0.6, 0.3), (0, -0.36 * L, 0), 0.5 * L)]
    everything = [o for o in bpy.data.objects if o.type == "MESH"]
    for prefix, obj, only in (("", made[0], None), ("lo_", made[1], ("left", "head", "top", "front")),
                              ("school_", made[2], ("left", "right", "top", "under", "front", "head"))):
        scene.display.shading.color_type = "VERTEX" if prefix == "school_" else "MATERIAL"
        # (the school model's sheets are drawn from both sides)
        scene.display.shading.show_backface_culling = prefix != "school_"
        for other in everything:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if only and view not in only:
                continue
            offset = Vector(direction).normalized() * 40.0
            camera.data.ortho_scale = frame
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s_%s%s.png" % (prefix_name, prefix, view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    os.makedirs(OUT, exist_ok=True)
    built = {}
    for name in TYPES:
        use(name)
        full = make("%s_tetra" % name, False)
        low = make("%s_tetra_lo" % name, True)
        school = make_school("%s_tetra_school" % name)
        export_one(full, os.path.join(OUT, "%s_tetra.glb" % name))
        export_one(low, os.path.join(OUT, "%s_tetra_lo.glb" % name))
        export_one(school, os.path.join(OUT, "%s_tetra_school.glb" % name), True)
        built[name] = (full, low, school)
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        for name, made in built.items():
            render(PREVIEW, made, TYPES[name]["length"], name)
    # (side by side in the .blend: each type a row, full, low and school along it)
    for row, made in enumerate(built.values()):
        for k, obj in enumerate(made):
            obj.location = (0.05 * k, 0.0, -0.03 * row)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "neon_tetra.blend"))


if __name__ == "__main__":
    main()
