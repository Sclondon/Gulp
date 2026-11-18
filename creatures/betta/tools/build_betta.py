"""Builds the betta, the Siamese fighting fish (creatures/betta), and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/betta/tools/build_betta.py
    blender --background --python creatures/betta/tools/build_betta.py -- <preview folder>   # with pictures

Writes creatures/betta/models/betta.glb (the full model, for one seen close) and betta_lo.glb (far off, phones),
and the editable creatures/betta/tools/betta.blend (both; this folder has a .gdignore). Each is one still mesh
with one surface: the shader (betta.gdshader) draws every marking (its colours are its settings), swims it,
billows and ripples its fins, opens its mouth and flares it. It prints a WINDING line for each: the check that
nothing is inside out.

A male betta (Betta splendens) of the long-finned halfmoon kind, 0.065 m from the tip of its jaw to the end of
its tail, built from the species (no picture was traced or copied):

- THE BODY: stout and a little long, a little flattened from side to side, deepest just behind the head; a short
  blunt head, a big eye, a small upturned mouth.
- THE MOUTH: the head ahead of the jaw's hinge is in two closed pieces that meet along the line of the mouth,
  which runs from the tip of the snout steeply down and back. The upper one is part of the body: its underside is
  the roof of the mouth, and a wall behind it is the throat. The LOWER JAW is a part of its own, its top the floor
  of the mouth; the shader swings it down about its hinge (`gape`).
- THE FINS, each a thin closed blade (two skins that meet at its edges), all built standing out as when it flares
  (the shader lets them fold and droop and trail when it does not): a halfmoon tail, a fan as long as the body
  spread nearly upright above and below; a long-based dorsal fin rising behind the middle of the back and running
  back over the tail; a long, deep anal fin from behind the belly to the tail; two long thread-like pelvic fins;
  two small clear pectoral fins.
- THE GILL COVERS: a thin flap on each side of the head over the gill cover, hinged at its front: the shader
  swings them out when it flares. Under each, folded away inside the head when it is calm, THE BEARD: a dark
  ruffled membrane along the edge of the gill opening, which the shader brings out when it flares.

Everything here is built in BODY LENGTHS (the tip of the jaw at 0, the end of the tail at 1), in Godot's axes
(Y up, X to its left side, its nose at -Z), with the origin on its middle line half way along; it is multiplied
by its length (metres) only as it is written out. `xm` below is body lengths behind the tip of the jaw.

What a point is, for the shader: UV2.y the part (0 body, 1 the dorsal fin, 2 the anal fin, 3 the tail, 4 a
pectoral fin, 5 a pelvic fin, 6 an eye, 7 the lower jaw, 8 a gill cover, 9 the beard). UV2.x: 1 inside the mouth
(its roof, floor and throat), 0 elsewhere. UV, on the body and the jaw: x how far along (0 jaw to 1 tail end), y
how high on its side (1 the ridge of the back, 0.5 its middle line, 0 the keel of the belly); on a fin, a gill
cover or the beard: x from its root (0) to its tip or free edge (1), y from its leading (or upper) edge (0) to its
trailing (or lower) edge (1); on an eye: x from its middle (0) to its rim (1). (The glTF writer flips V: what is
written here is 1 - v, so that Godot reads v.)

The numbers marked "as the shader has it" are in betta.gdshader too (in body lengths there as well): change
one, change the other.
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
BODY, DORSAL, ANAL, TAIL, PECTORAL, PELVIC, EYE, JAW, COVER, BEARD = range(10)
TAU = math.tau

# Its length (metres, jaw to tail end); its outline (body lengths behind the jaw, half its depth above its
# middle line, half its depth below, half its width); where its body ends inside the tail; the line of the
# mouth (y at the tip, slope), how far back the lower jaw runs (its hinge), the eye (place, radius), the gill
# cover's edge (x at the middle, how fast it curves forward), and where the tail fin's root is. As the shader
# has it.
SHAPES = {
    "betta": {
        "length": 0.065,
        "profile": [
            (0.0, 0.0, 0.0, 0.0),
            (0.004, 0.006, 0.010, 0.007),
            (0.014, 0.013, 0.026, 0.018),
            (0.030, 0.024, 0.042, 0.030),
            (0.055, 0.038, 0.056, 0.040),
            (0.090, 0.052, 0.068, 0.048),
            (0.140, 0.063, 0.078, 0.052),
            (0.200, 0.069, 0.083, 0.054),
            (0.260, 0.071, 0.083, 0.053),
            (0.320, 0.069, 0.077, 0.049),
            (0.380, 0.064, 0.068, 0.043),
            (0.440, 0.056, 0.057, 0.036),
            (0.490, 0.050, 0.050, 0.028),
            (0.525, 0.047, 0.047, 0.018),
            (0.545, 0.035, 0.035, 0.010),
            (0.558, 0.004, 0.004, 0.002),
        ],
        "body_to": 0.558, "mouth": (0.004, -0.45), "mouth_to": 0.035, "jaw_to": 0.037,
        "eye": (0.072, 0.016), "eye_radius": 0.028, "gill": (0.165, 7.0), "joint": 0.535,
    },
}

BODY_FROM = 0.003
SHAPE = {}
_XS = []
_CURVES = []
AROUND = [32]
BODY_TO = MOUTH_TO = JAW_TO = EYE_RADIUS = JOINT = 0.0
EYE_AT = (0.0, 0.0)


def use(name):
    """Makes `name` the model being built: its outline and its numbers."""
    global BODY_TO, MOUTH_TO, JAW_TO, EYE_AT, EYE_RADIUS, JOINT
    SHAPE.clear()
    SHAPE.update(SHAPES[name])
    SHAPE["name"] = name
    BODY_TO = SHAPE["body_to"]
    MOUTH_TO = SHAPE["mouth_to"]
    JAW_TO = SHAPE["jaw_to"]
    EYE_AT = SHAPE["eye"]
    EYE_RADIUS = SHAPE["eye_radius"]
    JOINT = SHAPE["joint"]
    profile = SHAPE["profile"]
    _XS[:] = [p[0] for p in profile]
    _CURVES.clear()
    for column in (1, 2, 3):
        ys = [p[column] for p in profile]
        _CURVES.append((ys, _slopes(_XS, ys)))


def mouth_y(xm):
    a, b = SHAPE["mouth"]
    return a + b * xm


def gill_x(y):
    a, b = SHAPE["gill"]
    return a - b * (y + 0.008) ** 2


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
    side = math.copysign(abs(s) ** 0.8, s) * wide
    # the top of the head a little flattened
    side *= 1.0 + 0.08 * smooth(0.3, 0.9, c) * (1.0 - smooth(0.1, 0.25, xm))
    # the mouth: a groove from the tip of the jaw back to its corner
    if xm < MOUTH_TO + 0.01:
        groove = math.exp(-((y - mouth_y(xm)) / 0.004) ** 2) * smooth(0.003, 0.012, xm) * (1.0 - smooth(MOUTH_TO - 0.01, MOUTH_TO + 0.003, xm))
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
    s = SHAPE["length"]
    return Vector((p.x * s, -p.z * s, p.y * s))


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


def rings(low):
    xs = []
    x = BODY_FROM
    for until, step in ((JAW_TO, 0.006), (JAW_TO + 0.18, 0.012), (BODY_TO - 0.04, 0.022), (BODY_TO, 0.008)):
        if low:
            step *= 4.0
        n = max(1, round((until - x) / step))
        for i in range(n):
            xs.append(x + (until - x) * i / n)
        x = until
    xs.append(BODY_TO)
    return xs


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
    around = AROUND[0]
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
    around = AROUND[0]
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


def fan(pivot, root_half, reach, spread, rounded):
    """A tail fin spread as a fan from its root: t from the root (a short upright line about `pivot`, half
    `root_half` long) to the back edge, `reach` away, u from its top edge (spread radians above the middle
    line) to its bottom edge. `rounded` bows the back edge out in the middle."""
    def point(t, u):
        a = spread * (1.0 - 2.0 * u)
        r = reach * t * 0.995 * (1.0 + rounded * (1.0 - (2.0 * u - 1.0) ** 2))
        return (pivot + r * math.cos(a), (1.0 - t) * root_half * (1.0 - 2.0 * u) + r * math.sin(a))
    return point


def material_of(name, colour):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = colour
    material.diffuse_color = colour
    return material


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


def export_one(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", export_yup=True, use_selection=True,
        export_animations=False, export_texcoords=True, export_vertex_color="NONE", export_all_vertex_colors=False,
    )


def render(folder, made, length, prefix_name):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.show_cavity = True
    scene.display.shading.show_backface_culling = True
    scene.display.shading.color_type = "MATERIAL"
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
    views = [("left", (1, 0, 0), (0, 0, 0), 1.5 * L), ("right", (-1, 0, 0), (0, 0, 0), 1.5 * L),
             ("front", (0, 1, 0), (0, 0, 0), 1.6 * L), ("back", (0, -1, 0), (0, 0, 0), 1.6 * L),
             ("top", (0.001, 0, 1), (0, 0, 0), 2.0 * L), ("under", (0.001, 0, -1), (0, 0, 0), 2.0 * L),
             ("head", (0.8, 0.5, 0.2), (0, 0.36 * L, 0), 0.4 * L), ("tail", (0.7, -0.6, 0.3), (0, -0.25 * L, 0), 0.8 * L)]
    everything = [o for o in bpy.data.objects if o.type == "MESH"]
    for prefix, obj, only in (("", made[0], None), ("lo_", made[1], ("left", "head", "top", "front"))):
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


def skin_normal(xm, y, sx):
    """The way the skin faces at `xm` and height `y`, on the left side (sx 1) or the right (-1)."""
    e = 0.003
    n = (skin(xm + e, y, sx) - skin(xm - e, y, sx)).cross(skin(xm, y + e, sx) - skin(xm, y - e, sx))
    n.normalize()
    if n.x * sx < 0.0:
        n = -n
    return n


# As the shader has it: the tail fin's pivot; the gill covers' hinge (body lengths behind the jaw) and how far
# out from the middle line it is; the beard's reach and ruffle, and the way it reaches (on the left side).
TAIL_PIVOT = 0.525
COVER_HINGE = 0.098
BEARD_LONG = 0.08
BEARD_RUFFLE = 0.012
BEARD_WAY = Vector((0.85, -0.25, 0.45)).normalized()


def beard_across(sx):
    """The way the beard's sheet faces, on the left side (sx 1) or the right."""
    way = Vector((BEARD_WAY.x * sx, BEARD_WAY.y, BEARD_WAY.z))
    return Vector((0.0, 1.0, 0.0)).cross(way).normalized()


def fins(m, low):
    d = 3 if low else 1
    # The tail: a halfmoon, a fan as long as the body spread nearly upright above and below, its back edge
    # rounded.
    blade(m, TAIL, "tail", fan(TAIL_PIVOT, 0.035, 0.42, 1.2, 0.12), upright, SIDE, 0.007, 4 if low else 20, 6 if low else 24)
    # The dorsal fin: a long root behind the middle of the back, rising tall and running back over the tail.
    blade(m, DORSAL, "dorsal",
          swept(((0.27, top(0.27) - 0.005), (0.33, top(0.30) + 0.22), (0.62, top(0.45) + 0.29)),
                ((0.50, top(0.50) - 0.005), (0.60, top(0.50) + 0.10), (0.62, top(0.45) + 0.29))),
          upright, SIDE, 0.006, 3 if low else 14, 3 if low else 12)
    # The anal fin: long and deep, from behind the belly to the tail.
    blade(m, ANAL, "anal",
          swept(((0.22, bottom(0.22) + 0.005), (0.27, bottom(0.25) - 0.20), (0.60, bottom(0.45) - 0.28)),
                ((0.51, bottom(0.51) + 0.005), (0.59, bottom(0.50) - 0.09), (0.60, bottom(0.45) - 0.28))),
          upright, SIDE, 0.006, 3 if low else 14, 3 if low else 14)
    for sx in (1.0, -1.0):
        # The pelvic fins: long threads from under the throat, held down and a little back when it flares.
        root = Vector((sx * 0.014, bottom(0.2) + 0.006, 0.2 - HALF))
        span = Vector((sx * 0.12, -0.9, 0.42)).normalized()
        chord = Vector((0.0, 0.42, 0.9)).normalized()
        facing = span.cross(chord).normalized()
        if facing.x * sx < 0.0:
            facing = -facing

        def pelvic_point(t, u):
            t *= 0.98
            return (0.30 * t, 0.06 * t * t + (0.034 * (1.0 - t) ** 0.9 + 0.003) * u)

        blade(m, PELVIC, "pelvics", pelvic_point,
              lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.005, 10 // d, max(2, 3 // d))
        # The pectoral fins: small, rounded, clear.
        root = skin(0.17, -0.012, sx)
        root.x -= sx * 0.003
        span = Vector((sx * 0.5, -0.1, 0.86)).normalized()
        chord = Vector((sx * 0.05, -0.95, 0.3)).normalized()
        facing = span.cross(chord).normalized()
        if facing.x * sx < 0.0:
            facing = -facing

        def pectoral_point(t, u):
            t *= 0.97
            wide_here = 0.062 * math.sin(math.pi * (0.2 + 0.8 * t)) ** 0.6 + 0.003
            return (0.085 * t, wide_here * (u - 0.35))

        blade(m, PECTORAL, "pectorals", pectoral_point,
              lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.005, max(2, 6 // d), max(2, 5 // d))
        # The gill cover: a flap lying on the side of the head from its hinge (in front) to the edge of the
        # gill opening, its hinge edge sunk into the skin.
        def cover_point(t, u):
            y = 0.03 - 0.085 * u
            front = COVER_HINGE + 0.004 * (2.0 * u - 1.0) ** 2
            back = gill_x(y) + 0.003
            return (front + (back - front) * t, y, t)

        def cover_place(p, sx=sx):
            lift = 0.0035 * smooth(0.0, 0.3, p[2]) - 0.0025 * (1.0 - smooth(0.0, 0.3, p[2]))
            return skin(p[0], p[1], sx) + skin_normal(p[0], p[1], sx) * lift

        blade(m, COVER, "gill covers", cover_point, cover_place, skin_normal(0.13, -0.012, sx), 0.004,
              1 if low else 6, 2 if low else 8)
        # The beard: a dark ruffled membrane along the gill opening, reaching out and back (the shader folds
        # it away inside the head when it is calm).
        across = beard_across(sx)
        way = Vector((BEARD_WAY.x * sx, BEARD_WAY.y, BEARD_WAY.z))

        def beard_place(p, sx=sx, across=across, way=way):
            t, u = p
            y = 0.025 - 0.085 * u
            xm = gill_x(y) - 0.014
            root = skin(xm, y, sx) - skin_normal(xm, y, sx) * 0.003
            reach = BEARD_LONG * (0.6 + 0.4 * math.sin(math.pi * u))
            return root + way * (t * reach) + across * (BEARD_RUFFLE * t * math.sin(u * 6.0 * math.pi))

        blade(m, BEARD, "beard", lambda t, u: (t, u), beard_place, across, 0.003, 1 if low else 5, 3 if low else 14)


def make(name, low):
    AROUND[0] = 10 if low else 36
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
    mesh.materials.append(material_of("betta", (0.15, 0.25, 0.65, 1.0)))
    return finish(name, mesh, m)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    os.makedirs(OUT, exist_ok=True)
    use("betta")
    full = make("betta", False)
    low = make("betta_lo", True)
    export_one(full, os.path.join(OUT, "betta.glb"))
    export_one(low, os.path.join(OUT, "betta_lo.glb"))
    print("SHADER betta: jaw_to %.4f hinge_y %.5f eye_at (%.3f, %.3f) eye_radius %.3f joint %.3f body_to %.3f half width at the cover's hinge %.4f" % (
        JAW_TO, mouth_y(JAW_TO), EYE_AT[0], EYE_AT[1], EYE_RADIUS, JOINT, BODY_TO, skin(COVER_HINGE, -0.01, 1.0).x))
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, (full, low), SHAPES["betta"]["length"], "betta")
    low.location = (0.08, 0.0, 0.0)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "betta.blend"))


if __name__ == "__main__":
    main()
