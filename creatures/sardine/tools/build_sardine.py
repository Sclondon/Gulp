"""Builds the Pacific sardine (creatures/sardine) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/sardine/tools/build_sardine.py
    blender --background --python creatures/sardine/tools/build_sardine.py -- <preview folder>   # with pictures

Writes creatures/sardine/models/sardine.glb (the full model, for one seen close), sardine_lo.glb (far off,
phones) and sardine_school.glb (a very light one whose look is in its vertex colours, for hundreds drawn by
one MultiMesh), and the editable creatures/sardine/tools/sardine.blend (this folder has a .gdignore). The full
and the low model are one still mesh with one surface each: the shader (sardine.gdshader) draws every marking
and swims it. It prints a WINDING line for each: the check that nothing is inside out.

A Pacific sardine (Sardinops sagax), 0.22 m from the tip of its lower jaw to the tips of its tail, built from
the species (no picture was traced or copied):

- THE BODY: a slender spindle, a little flattened from side to side, deepest (0.042 m) and widest (0.024 m)
  two fifths of the way back, its belly a little sharper than its back, running to a tail wrist about a third
  as deep. A pointed head, the lower jaw a little ahead of the upper; the line of the mouth, a groove; the
  gill cover, a step; a big eye, a low dome on each side.
- THE FINS, each a thin closed blade (two skins that meet at its edges): one small triangular dorsal fin at
  the middle of the body; a low anal fin far back; a deeply forked tail; two pectoral fins set low behind the
  gill covers, lying back; two small pelvic fins under the dorsal.

Everything here is in Godot space (metres, Y up, X to its left side, its nose at -Z) until it is written out;
the origin is on its middle line, half way along (0.11 m behind the tip of its jaw). `xm` below is metres
behind the tip of the jaw.

What a point is, for the shader: UV2.y the part (0 body, 1 the dorsal fin, 2 the anal fin, 3 the tail, 4 a
pectoral fin, 5 a pelvic fin, 6 an eye). UV, on the body: x how far along (0 jaw to 1 tail tips), y how high
on its side (1 the ridge of the back, 0.5 its middle line, 0 the keel of the belly); on a fin: x from its root
(0) to its tip (1), y from its leading edge (0) to its trailing edge (1); on an eye: x from its middle (0) to
its rim (1). (The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.)

The school model has no UVs: only places, normals and a colour at each point (COLOR_0: blue-green back, silver
flank, white belly, seven dark spots and an eye on each side as small plates lying on the skin, grey fins). Its
fins are single sheets, drawn from both sides by whatever draws it (GameCommon's flock.gdshader does).

The numbers marked "as the shader has it" are in sardine.gdshader too: change one, change the other.
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

LENGTH = 0.22
HALF = 0.11
BODY, DORSAL, ANAL, TAIL, PECTORAL, PELVIC, EYE = range(7)
TAU = math.tau

# The body's outline: metres behind the jaw, half its depth above its middle line, half its depth below,
# half its width.
PROFILE = [
    (0.0, 0.0, 0.0, 0.0),
    (0.0008, 0.0012, 0.0016, 0.0011),
    (0.003, 0.0030, 0.0038, 0.0026),
    (0.008, 0.0058, 0.0070, 0.0046),
    (0.016, 0.0093, 0.0108, 0.0068),
    (0.026, 0.0126, 0.0145, 0.0088),
    (0.038, 0.0153, 0.0176, 0.0103),
    (0.052, 0.0174, 0.0203, 0.0114),
    (0.068, 0.0189, 0.0221, 0.0120),
    (0.084, 0.0195, 0.0225, 0.0120),
    (0.100, 0.0189, 0.0215, 0.0115),
    (0.118, 0.0170, 0.0190, 0.0104),
    (0.136, 0.0142, 0.0155, 0.0087),
    (0.152, 0.0112, 0.0120, 0.0068),
    (0.166, 0.0086, 0.0090, 0.0050),
    (0.176, 0.0070, 0.0072, 0.0038),
    (0.182, 0.0064, 0.0065, 0.0028),
    (0.186, 0.0052, 0.0052, 0.0015),
    (0.189, 0.0008, 0.0008, 0.0005),
]
BODY_FROM = 0.0006
BODY_TO = 0.189

# As the shader has it: the line of the mouth, the edge of the gill cover, the eye.
MOUTH_TO = 0.018
EYE_AT = (0.021, 0.0042)
EYE_RADIUS = 0.0056


def mouth_y(xm):
    return 0.0008 - 0.30 * xm


def gill_x(y):
    return 0.050 - 26.0 * (y + 0.002) ** 2


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
        out.append(max(a + b, 0.0002))
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
    side = math.copysign(abs(s) ** 0.9, s) * wide
    # the belly is sharper than the back (a sardine's belly has a keel of scutes)
    side *= 1.0 - 0.24 * smooth(0.1, 1.0, -c) * smooth(0.03, 0.06, xm)
    # the mouth: a groove from the tip of the jaw back and down to under the front of the eye
    z = xm
    if xm < MOUTH_TO + 0.002:
        groove = math.exp(-((y - mouth_y(xm)) / 0.0006) ** 2) * smooth(0.0006, 0.003, xm) * (1.0 - smooth(MOUTH_TO - 0.003, MOUTH_TO + 0.0006, xm))
        side *= 1.0 - 0.12 * groove
    # the lower jaw is a little ahead: what is above the mouth's line is set back
    if xm < 0.012:
        z += 0.0013 * smooth(mouth_y(xm) - 0.0003, mouth_y(xm) + 0.0012, y) * (1.0 - smooth(0.0, 0.012, xm))
    # the gill cover: it stands a little proud of the body behind its edge
    behind = xm - gill_x(y)
    if behind > 0.0 and wide > 0.002:
        mask = smooth(-0.97, -0.82, c) * (1.0 - smooth(0.45, 0.65, c))
        step = 0.0006 * smooth(0.0, 0.0012, behind) * math.exp(-behind / 0.007) * mask
        side *= 1.0 - step / wide
    return Vector((side, y, z - HALF))


def skin(xm, y, sx):
    """The point of the skin at `xm` and height `y`, on the left side (sx 1) or the right (-1)."""
    up, down, _ = outline(xm)
    c = max(-1.0, min(1.0, y / (up if y >= 0.0 else down)))
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

    def add(self, p, uv, part):
        self.verts.append(p)
        self.data.append(((uv[0], 1.0 - uv[1]), (0.0, 1.0 - part)))
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
    for until, step in ((0.058, 0.0009), (0.170, 0.0025), (BODY_TO, 0.001)):
        if low:
            step *= 4.0
        n = max(1, round((until - x) / step))
        for i in range(n):
            xs.append(x + (until - x) * i / n)
        x = until
    xs.append(BODY_TO)
    return xs


def body(m, low):
    around = 16 if low else 64
    grid = []
    for xm in rings(low):
        row = []
        for c in range(around):
            angle = c / around * TAU
            row.append(m.add(body_point(xm, angle), (xm / LENGTH, 0.5 + 0.5 * math.cos(angle)), BODY))
        grid.append(row)
    for r in range(len(grid) - 1):
        for c in range(around):
            n = (c + 1) % around
            quad = (grid[r][c], grid[r][n], grid[r + 1][n], grid[r + 1][c])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((middle.x, middle.y, 0.0)), "body")
    # the tip of the jaw and the end inside the tail: a fan each
    for row, xm, way in ((grid[0], 0.0, -1.0), (grid[-1], BODY_TO + 0.0004, 1.0)):
        tip = m.add(Vector((0.0, 0.0, xm - HALF)), (xm / LENGTH, 0.5), BODY)
        for c in range(around):
            m.face((tip, row[c], row[(c + 1) % around]), Vector((0.0, 0.0, way)), "body")


def eye(m, sx, low):
    """A low dome lying on the skin of the head."""
    spokes = 10 if low else 28
    steps = 2 if low else 8
    xe, ye = EYE_AT
    here = skin(xe, ye, sx)
    out = (skin(xe + 0.0007, ye, sx) - skin(xe - 0.0007, ye, sx)).cross(skin(xe, ye + 0.0007, sx) - skin(xe, ye - 0.0007, sx))
    out.normalize()
    if out.x * sx < 0.0:
        out = -out
    middle = m.add(here + out * 0.0012, (0.0, 0.0), EYE)
    last = None
    for k in range(1, steps + 1):
        r = k / steps
        row = []
        for s in range(spokes):
            a = s / spokes * TAU
            p = skin(xe + math.cos(a) * EYE_RADIUS * r, ye + math.sin(a) * EYE_RADIUS * r, sx)
            row.append(m.add(p + out * (0.0011 * (1.0 - r * r) + 0.0001 * (1.0 - r)), (r, 0.0), EYE))
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
    """A place in the flat of the middle fins (metres behind the jaw, metres up) in the model."""
    return Vector((0.0, p[1], p[0] - HALF))


SIDE = Vector((1.0, 0.0, 0.0))

# The middle fins, as the school model has them too.
DORSAL_FROM, DORSAL_LONG, DORSAL_HIGH = 0.083, 0.025, 0.021
ANAL_FROM, ANAL_LONG, ANAL_HIGH = 0.140, 0.021, 0.0065
TAIL_TIP = (0.22, 0.0275)
TAIL_NOTCH = 0.1935
# As the shader has it: where the tail fin is hinged.
JOINT = 0.183


def dorsal_high(u):
    return DORSAL_HIGH * (0.2 + 0.8 * (1.0 - u) ** 1.5) * (0.5 + 0.5 * smooth(0.0, 0.14, u))


def anal_high(u):
    return ANAL_HIGH * (0.3 + 0.7 * (1.0 - u) ** 1.3) * (0.55 + 0.45 * smooth(0.0, 0.15, u))


def fins(m, low):
    d = 3 if low else 1
    # The dorsal fin: one small triangle at the middle of the body, tallest at its front, leaning back.
    lean = math.radians(28.0)

    def dorsal_point(t, u):
        xm = DORSAL_FROM + DORSAL_LONG * u
        high = dorsal_high(u) * t
        return (xm + math.sin(lean) * high, top(xm) - 0.001 + math.cos(lean) * high + 0.001 * t)

    blade(m, DORSAL, "dorsal", dorsal_point, upright, SIDE, 0.0009, 10 // d, 14 // d)
    # The anal fin: low, far back.
    lean_a = math.radians(38.0)

    def anal_point(t, u):
        xm = ANAL_FROM + ANAL_LONG * u
        high = anal_high(u) * t
        return (xm + math.sin(lean_a) * high, bottom(xm) + 0.0008 - math.cos(lean_a) * high - 0.0008 * t)

    blade(m, ANAL, "anal", anal_point, upright, SIDE, 0.0007, 6 // d, 10 // d)
    # The tail: deeply forked, two pointed lobes that meet along the middle line.
    for way in (1.0, -1.0):
        tip = (TAIL_TIP[0], TAIL_TIP[1] * way)
        blade(m, TAIL, "tail", swept(((0.176, 0.0), (0.190, 0.0195 * way), tip),
                                      ((TAIL_NOTCH, 0.0), (0.1995, 0.0085 * way), tip)),
              upright, SIDE, 0.0014, 18 // d, 8 // max(d - 1, 1))
    for sx in (1.0, -1.0):
        # The pectoral fins: set low behind the gill covers, lying back and a little down and out.
        root = skin(0.0545, -0.0128, sx)
        root.x -= sx * 0.0008
        span = Vector((sx * 0.30, -0.26, 0.92)).normalized()
        chord = Vector((sx * 0.08, -0.86, 0.45)).normalized()
        facing = span.cross(chord).normalized()
        if facing.x * sx < 0.0:
            facing = -facing

        def pectoral_point(t, u):
            t *= 0.975
            wide_here = 0.0098 * (0.4 + 0.6 * smooth(0.0, 0.4, t)) * (1.0 - t) ** 0.65 + 0.0004
            return (0.029 * t, 0.0035 * t * t + wide_here * u)

        blade(m, PECTORAL, "pectorals", pectoral_point,
              lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.0009, 12 // d, 8 // max(d - 1, 1))
        # The pelvic fins: small, under the dorsal, pointing back and down.
        root = Vector((sx * 0.0028, bottom(0.097) + 0.0012, 0.097 - HALF))
        span = Vector((sx * 0.26, -0.5, 0.83)).normalized()
        chord = Vector((0.0, 0.14, 1.0)).normalized()
        facing = span.cross(chord).normalized()
        if facing.x * sx < 0.0:
            facing = -facing

        def pelvic_point(t, u):
            t *= 0.97
            return (0.0125 * t, 0.002 * t * t + (0.0052 * (1.0 - t) ** 0.8 + 0.0003) * u)

        blade(m, PELVIC, "pelvics", pelvic_point,
              lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.0007, 8 // d, 6 // d)


def material_of(name, colour):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = colour
    material.diffuse_color = colour
    return material


def make(name, low):
    m = Mesh()
    body(m, low)
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
    mesh.materials.append(material_of("sardine", (0.55, 0.62, 0.68, 1.0)))
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


# --- the school model -------------------------------------------------------------------------

# Its colours, as they are written into the points (what a shader reads as COLOR).
C_BACK = (0.035, 0.16, 0.21)
C_RIDGE = (0.025, 0.11, 0.16)
C_SILVER = (0.74, 0.78, 0.80)
C_LOW = (0.86, 0.88, 0.88)
C_BELLY = (0.95, 0.95, 0.93)
C_SPOT = (0.03, 0.05, 0.07)
C_EYE = (0.01, 0.01, 0.015)
C_FIN = (0.42, 0.48, 0.50)
C_TAIL = (0.24, 0.31, 0.33)
# Round the body (degrees from the ridge of the back): the ridge, the back's edge, the top of the silver,
# low on the flank, the keel; then the same up the other side.
SCHOOL_ANGLES = (0.0, 48.0, 66.0, 115.0, 180.0, 245.0, 294.0, 312.0)
SCHOOL_COLOURS = (C_RIDGE, C_BACK, C_SILVER, C_LOW, C_BELLY, C_LOW, C_SILVER, C_BACK)
SCHOOL_RINGS = (0.002, 0.012, 0.030, 0.055, 0.085, 0.115, 0.145, 0.170, 0.186)


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
    for row, xm, way, colour in ((grid[0], 0.0, -1.0, C_BACK), (grid[-1], BODY_TO, 1.0, C_SILVER)):
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

    def plate(xm, angle, radius, corners, lift, colour, group):
        """A small flat plate lying on the skin: a spot or an eye."""
        here = facet(xm, angle)
        out = (facet(xm + 0.001, angle) - facet(xm - 0.001, angle)).cross(facet(xm, angle + 2.0) - facet(xm, angle - 2.0))
        out.normalize()
        if out.dot(Vector((here.x, here.y, 0.0))) < 0.0:
            out = -out
        # (how many degrees round the body `radius` is, here)
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
        # the row of spots along the top of the silver, smaller towards the tail
        for k in range(7):
            plate(0.058 + k * 0.0135, turned(77.0), 0.0029 - 0.00012 * k, 6, 0.0005, C_SPOT, "spots")
        plate(EYE_AT[0], turned(74.0), 0.0054, 6, 0.0008, C_EYE, "eyes")

    # The fins: single sheets (drawn from both sides).
    def sheet(points, colours, out=SIDE):
        m.face(tuple(m.dab(p, c) for p, c in zip(points, colours)), out, "fins (two-sided sheets)")

    x0, x1 = DORSAL_FROM, DORSAL_FROM + DORSAL_LONG
    sheet((upright((x0, top(x0) - 0.001)), upright((x0 + 0.011, top(x0) + DORSAL_HIGH * 0.9)), upright((x1, top(x1) - 0.001))),
          (C_BACK, C_FIN, C_BACK))
    x0, x1 = ANAL_FROM, ANAL_FROM + ANAL_LONG
    sheet((upright((x0, bottom(x0) + 0.0008)), upright((x0 + 0.007, bottom(x0) - ANAL_HIGH)), upright((x1, bottom(x1) + 0.0008))),
          (C_BELLY, C_FIN, C_BELLY))
    x0 = 0.097
    sheet((upright((x0 - 0.002, bottom(x0) + 0.001)), upright((x0 + 0.011, bottom(x0) - 0.005)), upright((x0 + 0.005, bottom(x0) + 0.001))),
          (C_BELLY, C_FIN, C_BELLY))
    for way in (1.0, -1.0):
        sheet((upright((0.178, 0.0065 * way)), upright((TAIL_TIP[0], TAIL_TIP[1] * way)), upright((TAIL_NOTCH, 0.0)), upright((0.178, 0.0))),
              (C_TAIL, C_TAIL, C_FIN, C_SILVER))
    for sx in (1.0, -1.0):
        root = facet(0.055, 132.0 if sx > 0.0 else 228.0)
        span = Vector((sx * 0.30, -0.26, 0.92)).normalized()
        chord = Vector((sx * 0.08, -0.86, 0.45)).normalized()
        out = span.cross(chord)
        if out.x * sx < 0.0:
            out = -out
        sheet((root, root + span * 0.027 + chord * 0.004, root + span * 0.009 + chord * 0.009), (C_LOW, C_FIN, C_FIN), out)

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) for p in m.verts], [], m.faces)
    mesh.color_attributes.new(name="Col", type="FLOAT_COLOR", domain="POINT")
    colours = mesh.color_attributes["Col"]
    for i, colour in enumerate(m.data):
        colours.data[i].color = (colour[0], colour[1], colour[2], 1.0)
    # (the glTF writer only writes the colour that is marked for rendering)
    mesh.color_attributes.active_color = colours
    mesh.color_attributes.render_color_index = 0
    material = material_of("sardine_school", (1.0, 1.0, 1.0, 1.0))
    mesh.materials.append(material)
    return finish(name, mesh, m)


def winding(name, mesh, m):
    """Nothing inside out: the skin of the body faces away from its middle line, each skin of a fin away
    from the fin's own flat, an eye or a spot out from the body (Blender's front is the side a face's
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
    scene.display.shading.show_backface_culling = True
    scene.render.resolution_x, scene.render.resolution_y = 1400, 800
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    # (Blender space: the fish lies along Y, its nose at +Y, up is Z)
    views = [("left", (1, 0, 0), (0, 0, 0), 0.25), ("right", (-1, 0, 0), (0, 0, 0), 0.25),
             ("front", (0, 1, 0), (0, 0, 0), 0.1), ("back", (0, -1, 0), (0, 0, 0), 0.1),
             ("top", (0.001, 0, 1), (0, 0, 0), 0.42), ("under", (0.001, 0, -1), (0, 0, 0), 0.42),
             ("head", (0.8, 0.5, 0.2), (0, 0.075, 0), 0.09), ("tail", (0.7, -0.6, 0.3), (0, -0.08, 0), 0.11)]
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
    full = make("sardine", False)
    low = make("sardine_lo", True)
    school = make_school("sardine_school")
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, "sardine.glb"))
    export_one(low, os.path.join(OUT, "sardine_lo.glb"))
    export_one(school, os.path.join(OUT, "sardine_school.glb"), True)
    low.location.x = 0.08
    school.location.x = 0.16
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "sardine.blend"))
    low.location.x = 0.0
    school.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low, school])


if __name__ == "__main__":
    main()
