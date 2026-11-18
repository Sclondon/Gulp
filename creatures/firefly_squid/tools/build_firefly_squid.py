"""Builds the firefly squid (creatures/firefly_squid) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/firefly_squid/tools/build_firefly_squid.py
    blender --background --python creatures/firefly_squid/tools/build_firefly_squid.py -- <preview folder>   # with pictures

Writes creatures/firefly_squid/models/firefly_squid.glb (the full model, for one seen close), firefly_squid_game.glb
(the game model: the triangles spent on the outline, the eyes and the lights), firefly_squid_lo.glb (far off) and
firefly_squid_school.glb (a very light one whose look is in its vertex colours, for hundreds drawn by one
MultiMesh), and the editable creatures/firefly_squid/tools/firefly_squid.blend (this folder has a .gdignore). The
first three are one still mesh with one surface each: the shader (firefly_squid.gdshader) draws every marking and
every tiny light, bends the arms, ripples the fins and flashes the lights. It prints a WINDING line for each: the
check that nothing is inside out. Its school model is made as GameCommon's sardine's and lanternfish's are.

A firefly squid (Watasenia scintillans), 0.07 m from the tips of its arms to the end of its mantle, built from the
species as it is described (no picture was traced or copied):

- THE MANTLE: a slender torpedo, round in section, widest just behind its collar, running to a point; its collar a
  low step over the back of the head.
- THE FINS: at the end of the mantle, one each side, together a broad arrowhead (rhombic), thin blades.
- THE HEAD: short, with a big eye each side.
- THE ARMS: eight, short, drawn together ahead of the head, the lowest (ventral) pair the longest; two slender
  tentacles between the third and fourth pairs. Each a tapered tube built straight; the shader bends them.
- THE LIGHTS: the many tiny photophores over its skin are drawn by the shader; the big ones are built: three beads
  at the tip of each of the ventral arms, and five small domes along the lower rim of each eye.

Everything here is in Godot space (metres, Y up, X to its left side, its arms' tips at -Z) until it is written out;
the origin is on its middle line, half way along (0.035 m behind the tips of its arms). `xm` below is metres behind
the tips of its arms.

What a point is, for the shader: UV2.y the part (0 the body: mantle and head, 1 a fin, 2 an eye, 3 an arm or
tentacle, 4 a big light). UV2.x: on an arm, or a light on an arm, which (1 to 10: arms 1 to 8, tentacles 9 and 10);
0 elsewhere. UV on the body: x how far along (xm / LENGTH), y how high round it (1 the ridge of its back, 0 its
belly); on a fin: x out from its root (0) to its edge (1), y from its front (0) to its back (1); on an arm: x round it
(0.5 its inner face), y from its root (0) to its tip (1); on an eye: its own plane (x towards the arms, y up, 1 at
its rim); on a light: x from its middle (0) to its rim (1), y 1 on the lights round the eyes. (The glTF writer flips
V: what is written here is 1 - v, so that Godot reads v.)

The school model has no UVs: only places, normals and a colour at each point (COLOR_0, RGBA): a dusky red-violet
back, a paler belly, a dark eye with a silver ring each side, the arms a bunch of thin sheets, the fins one sheet,
and its lights small bright blue plates (rows along the belly and flanks, the three on each ventral arm's tip as one
plate, the eyes' rims). Its ALPHA is a glow mask: 1 on the lights, 0 everywhere else, so that a shader can make just
them glow (EMISSION = COLOR.rgb * COLOR.a). Its fins and arms are single sheets, drawn from both sides by whatever
draws it (GameCommon's flock.gdshader does).

The numbers marked "as the shader has it" are in firefly_squid.gdshader too: change one, change the other.
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

LENGTH = 0.07
HALF = 0.035
BODY, FIN, EYE, ARM, LIGHT = range(5)
TAU = math.tau

# The body's outline: metres behind the arms' tips, and its radius there (round in section).
PROFILE = [
    (0.0150, 0.0), (0.0154, 0.0016), (0.0163, 0.0028), (0.0178, 0.0037), (0.0205, 0.0044), (0.0235, 0.0044),
    (0.0252, 0.0040), (0.0262, 0.0048), (0.0300, 0.0055), (0.0360, 0.0057), (0.0450, 0.0053), (0.0540, 0.0044),
    (0.0610, 0.0031), (0.0665, 0.0015), (0.0700, 0.0),
]
BODY_FROM = 0.0150
BODY_TO = 0.0700
# As the shader has it: where the mantle starts (its collar), behind which `curl` bends it.
COLLAR = 0.0257
# As the shader has it: the arms' roots on a ring round the front of the head, how far each leans out at rest
# (radians from straight ahead), how long each is; the tentacles' roots (between the third and fourth pairs).
ARM_RX = 0.0021
ARM_RY = 0.0019
ARM_XM = 0.0162
ARM_ANGLES = [(k + 0.5) * math.pi / 4.0 for k in range(8)] + [math.radians(235.0), math.radians(305.0)]
ARM_RING = [1.0] * 8 + [0.55, 0.55]
ARM_LONG = [0.0118, 0.0102, 0.0102, 0.0118, 0.0130, 0.0158, 0.0158, 0.0130, 0.0166, 0.0166]
ARM_REST = [0.16] * 8 + [0.06, 0.06]
ARM_THICK = [0.00105, 0.00095, 0.00095, 0.00105, 0.0011, 0.0012, 0.0012, 0.0011, 0.0005, 0.0005]
VENTRAL = (5, 6)
# As the shader has it: the eye.
EYE_AT = (0.0212, 0.0005)
EYE_RADIUS = 0.0034
EYE_HEIGHT = 0.0011
# The fins: from, to, how far out at most, and where along that is.
FIN_FROM = 0.0505
FIN_TO = 0.0695
FIN_OUT = 0.0068
FIN_PEAK = 0.42

GAME = "game"


def pick(low, full, game, lo):
    return game if low is GAME else (lo if low else full)


def to_b(p):
    return Vector((p.x, -p.z, p.y))


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def _slopes(xs, ys):
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
_YS = [p[1] for p in PROFILE]
_MS = _slopes(_XS, _YS)


def radius(xm):
    xm = max(_XS[0], min(_XS[-1], xm))
    i = 0
    while i < len(_XS) - 2 and xm > _XS[i + 1]:
        i += 1
    h = _XS[i + 1] - _XS[i]
    t = (xm - _XS[i]) / h
    a = (2 * t ** 3 - 3 * t ** 2 + 1) * _YS[i] + (t ** 3 - 2 * t ** 2 + t) * h * _MS[i]
    b = (-2 * t ** 3 + 3 * t ** 2) * _YS[i + 1] + (t ** 3 - t ** 2) * h * _MS[i + 1]
    return max(a + b, 0.0)


def body_point(xm, angle, bias=1.0):
    """A point of the skin: `angle` round from the ridge of the back (0) by its left side (a quarter turn). `bias`
    stands the game model's fewer-sided skin a little proud, so that it straddles the round one."""
    r = radius(xm) * bias
    # (a little deeper than wide on the mantle, the head a little wider at the eyes)
    wide = 1.0 + 0.06 * math.exp(-((xm - 0.021) / 0.003) ** 2)
    deep = 1.0 + 0.04 * smooth(0.027, 0.034, xm)
    return Vector((math.sin(angle) * r * wide, math.cos(angle) * r * deep, xm - HALF))


def skin(xm, y, sx):
    r = radius(xm) * (1.0 + 0.04 * smooth(0.027, 0.034, xm))
    c = max(-1.0, min(1.0, y / max(r, 1e-6)))
    return body_point(xm, sx * math.acos(c))


def skin_normal(xm, y, sx):
    e = 0.0001
    out = (skin(xm + e, y, sx) - skin(xm - e, y, sx)).cross(skin(xm, y + e, sx) - skin(xm, y - e, sx))
    out.normalize()
    if out.x * sx < 0.0:
        out = -out
    return out


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.data = []
        self.out = []
        self.count = {}
        self.tris = {}

    def add(self, p, uv, part, arm=0.0):
        self.verts.append(p)
        self.data.append(((uv[0], 1.0 - uv[1]), (arm, 1.0 - part)))
        return len(self.verts) - 1

    def dab(self, p, colour):
        self.verts.append(p)
        self.data.append(colour)
        return len(self.verts) - 1

    def face(self, points, out, name):
        ps = [self.verts[i] for i in points]
        n = Vector((0.0, 0.0, 0.0))
        for i in range(len(ps)):
            n += ps[i].cross(ps[(i + 1) % len(ps)])
        if n.length < 1e-18:
            return
        if n.dot(out) < 0.0:
            points = tuple(reversed(points))
        self.faces.append(tuple(points))
        self.out.append((Vector(out), name))
        self.count[name] = self.count.get(name, 0) + 1
        self.tris[name] = self.tris.get(name, 0) + len(points) - 2


def body_rings(low):
    if low is GAME:
        # (crowded at the round front of the head, the eyes, the collar's step and the mantle's point)
        return [BODY_FROM, 0.0154, 0.0163, 0.0178, 0.0205, 0.0237, 0.0254, 0.0262, 0.0315, 0.0430, 0.0540,
                0.0625, 0.0688]
    step = 0.0045 if low else 0.0008
    xs = []
    x = BODY_FROM
    n = max(3, round((BODY_TO - BODY_FROM) / step))
    for i in range(n):
        t = i / n
        # (closer at both ends, where the outline turns)
        u = t - 0.12 * math.sin(TAU * t) / TAU
        xs.append(BODY_FROM + (BODY_TO - BODY_FROM) * u)
    return xs[:]


def body(m, low):
    # (a multiple of four, so that a column runs along each side and the back and the belly: the outline seen from
    # above and from the side)
    around = pick(low, 32, 12, 8)
    xs = [x for x in body_rings(low) if x > BODY_FROM + 1e-6]
    grid = []
    for xm in xs:
        row = []
        for c in range(around):
            angle = c / around * TAU
            row.append(m.add(body_point(xm, angle, 1.016 if low is GAME else 1.0), (xm / LENGTH, 0.5 + 0.5 * math.cos(angle)), BODY))
        grid.append(row)
    for r in range(len(grid) - 1):
        for c in range(around):
            n = (c + 1) % around
            quad = (grid[r][c], grid[r][n], grid[r + 1][n], grid[r + 1][c])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((middle.x, middle.y, 0.0)), "body")
    front = m.add(Vector((0.0, 0.0, BODY_FROM - HALF)), (BODY_FROM / LENGTH, 0.5), BODY)
    back = m.add(Vector((0.0, 0.0, BODY_TO - HALF)), (1.0, 0.5), BODY)
    for c in range(around):
        n = (c + 1) % around
        m.face((front, grid[0][c], grid[0][n]), Vector((0.0, 0.0, -1.0)), "body")
        m.face((back, grid[-1][c], grid[-1][n]), Vector((0.0, 0.0, 1.0)), "body")


def arm_frame(k):
    """The way arm `k` points at rest, and the two ways across it (out from the middle line, and round)."""
    a = ARM_ANGLES[k]
    lean = Vector((math.cos(a), math.sin(a), 0.0))
    ahead = Vector((0.0, 0.0, -1.0))
    way = ahead * math.cos(ARM_REST[k]) + lean * math.sin(ARM_REST[k])
    out = (lean - way * lean.dot(way)).normalized()
    side = way.cross(out).normalized()
    root = Vector((math.cos(a) * ARM_RX * ARM_RING[k], math.sin(a) * ARM_RY * ARM_RING[k], ARM_XM - HALF))
    return root, way, out, side


def arm_radius(k, s):
    if k >= 8:
        # (the tentacle: a slender stalk, a club at its end)
        return ARM_THICK[k] * (1.0 - 0.35 * s + 0.55 * math.exp(-((s - 0.84) / 0.08) ** 2)) * (1.0 - smooth(0.93, 1.0, s) * 0.85)
    return ARM_THICK[k] * (1.0 - 0.72 * s) * (1.0 - smooth(0.9, 1.0, s) * 0.7)


def arms(m, low):
    for k in range(10):
        root, way, out, side = arm_frame(k)
        long = ARM_LONG[k]
        around = pick(low, 8, 4, 3)
        steps = pick(low, 24, 3, 2)
        grid = []
        for i in range(steps + 1):
            s = i / steps
            # (the root sunk into the head)
            centre = root + way * (long * s - 0.0006 * (1.0 - s) ** 4)
            r = arm_radius(k, s)
            row = []
            for j in range(around):
                phi = j / around * TAU + (math.pi / around if around < 8 else 0.0)
                # (a few-sided arm stands a little proud, so that it looks as thick as the round one)
                p = centre + (out * math.cos(phi) + side * math.sin(phi)) * (r * (1.1 if around < 8 else 1.0))
                row.append(m.add(p, (j / around, s), ARM, k + 1.0))
            grid.append((row, centre))
        for i in range(steps):
            a, ca = grid[i]
            b, cb = grid[i + 1]
            for j in range(around):
                n = (j + 1) % around
                quad = (a[j], a[n], b[n], b[j])
                middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
                axis = (ca + cb) * 0.5
                m.face(quad, middle - axis, "arms")
        tip = m.add(root + way * (long + 0.0002), (0.5, 1.0), ARM, k + 1.0)
        last = grid[-1][0]
        for j in range(around):
            m.face((tip, last[j], last[(j + 1) % around]), way, "arms")
        if k in VENTRAL:
            for s in (0.8, 0.885, 0.965):
                bead(m, root + way * (long * s), way, out, side, 0.00052, low, k + 1.0, s)


def bead(m, centre, way, out, side, r, low, arm, s):
    """A big light on an ventral arm's tip: a small ball round the arm (UV.y its place along the arm, so that the
    shader bends it with the arm)."""
    rings = pick(low, 4, 2, 0)
    around = pick(low, 8, 4, 0)
    if rings == 0:
        return
    top = m.add(centre + way * r, (0.0, s), LIGHT, arm)
    bottom = m.add(centre - way * r, (0.0, s), LIGHT, arm)
    rows = []
    for i in range(1, rings):
        a = math.pi * i / rings
        row = []
        for j in range(around):
            phi = j / around * TAU
            p = centre + way * (r * math.cos(a)) + (out * math.cos(phi) + side * math.sin(phi)) * (r * math.sin(a))
            row.append(m.add(p, (0.0, s), LIGHT, arm))
        rows.append(row)
    for j in range(around):
        n = (j + 1) % around
        m.face((top, rows[0][j], rows[0][n]), (m.verts[rows[0][j]] + m.verts[rows[0][n]]) * 0.5 - centre, "lights")
        m.face((bottom, rows[-1][j], rows[-1][n]), (m.verts[rows[-1][j]] + m.verts[rows[-1][n]]) * 0.5 - centre, "lights")
        for i in range(len(rows) - 1):
            quad = (rows[i][j], rows[i][n], rows[i + 1][n], rows[i + 1][j])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, middle - centre, "lights")


def dome(m, part, xe, ye, radius, height, sx, spokes, steps, group, plane=True, tag=0.0):
    """A low dome lying on the skin: an eye (its UV its own plane), or a light (UV x from its middle to its rim)."""
    here = skin(xe, ye, sx)
    out = skin_normal(xe, ye, sx)
    middle = m.add(here + out * height, (0.0, 0.0) if plane else (0.0, tag), part)
    last = None
    for k in range(1, steps + 1):
        r = k / steps
        row = []
        for s in range(spokes):
            a = s / spokes * TAU
            qx = math.cos(a) * r
            qy = math.sin(a) * r
            # (x towards the arms: that is towards a smaller xm)
            p = skin(xe - qx * radius, ye + qy * radius, sx)
            lift = height * (1.0 - r * r) + 0.00001 * (1.0 - r)
            row.append(m.add(p + out * lift, (qx, qy) if plane else (r, tag), part))
        for s in range(spokes):
            n = (s + 1) % spokes
            if last is None:
                m.face((middle, row[s], row[n]), out, group)
            else:
                m.face((last[s], row[s], row[n], last[n]), out, group)
        last = row


def eyes(m, low):
    for sx in (1.0, -1.0):
        dome(m, EYE, EYE_AT[0], EYE_AT[1], EYE_RADIUS, EYE_HEIGHT, sx, pick(low, 36, 24, 8), pick(low, 8, 2, 1), "eyes")


def eye_light_places():
    """The five lights along the lower rim of each eye (left side; metres behind the arms' tips, metres up)."""
    out = []
    for k in range(5):
        a = math.radians(-155.0 + k * 32.5)
        out.append((EYE_AT[0] - math.cos(a) * EYE_RADIUS * 1.18, EYE_AT[1] + math.sin(a) * EYE_RADIUS * 1.18))
    return out


def eye_lights(m, low):
    if low is True:
        return
    for sx in (1.0, -1.0):
        for xm, y in eye_light_places():
            if low is GAME:
                plate(m, xm, y, 0.00042, sx)
            else:
                dome(m, LIGHT, xm, y, 0.00042, 0.00016, sx, 8, 2, "lights", False, 1.0)


def plate(m, xe, ye, radius, sx):
    """The game model's eye light: one six-cornered plate just off the skin (its corners marked a little in from
    its rim, so that the shader lights the whole of it)."""
    out = skin_normal(xe, ye, sx)
    corners = []
    for s in range(6):
        a = s / 6.0 * TAU
        p = skin(xe + math.cos(a) * radius, ye + math.sin(a) * radius, sx)
        corners.append(m.add(p + out * 0.00009, (0.4, 1.0), LIGHT))
    for s in range(1, 5):
        m.face((corners[0], corners[s], corners[s + 1]), out, "lights")


def fins(m, low):
    # (always a row at the fin's widest: FIN_PEAK)
    us = pick(low, [i / 14.0 for i in range(15)], [0.0, 0.2, FIN_PEAK, 0.7, 1.0], [0.0, FIN_PEAK, 1.0])
    if low is False:
        us = sorted(set(us + [FIN_PEAK]))
    nu = len(us) - 1
    nt = pick(low, 6, 3, 1)
    for sx in (1.0, -1.0):
        for side in (1.0, -1.0):
            grid = []
            for ui in range(nu + 1):
                u = us[ui]
                xm = FIN_FROM + (FIN_TO - FIN_FROM) * u
                # (a rhombus: out to its widest at FIN_PEAK, its outer corners a little rounded)
                reach = FIN_OUT * (u / FIN_PEAK if u < FIN_PEAK else (1.0 - u) / (1.0 - FIN_PEAK))
                reach = FIN_OUT * (reach / FIN_OUT) ** 0.92
                r = radius(xm) * (1.0 + 0.04 * smooth(0.027, 0.034, xm)) - 0.0002
                row = []
                for ti in range(nt + 1):
                    t = ti / nt
                    swell = 0.0005 * (1.0 - t) ** 1.2 * math.sin(math.pi * u) ** 0.5
                    # (the edge swept back a little)
                    p = Vector((sx * (r + reach * t), side * swell * 0.5, xm - HALF + 0.0018 * t * t * reach / FIN_OUT))
                    row.append(m.add(p, (t, u), FIN))
                grid.append(row)
            for ui in range(nu):
                for ti in range(nt):
                    m.face((grid[ui][ti], grid[ui][ti + 1], grid[ui + 1][ti + 1], grid[ui + 1][ti]), Vector((0.0, side, 0.0)), "fins")


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
    eyes(m, low)
    eye_lights(m, low)
    fins(m, low)
    arms(m, low)
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
    mesh.materials.append(material_of("firefly_squid", (0.4, 0.2, 0.25, 1.0)))
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
    xs = [p.x for p in m.verts]
    ys = [p.y for p in m.verts]
    zs = [p.z for p in m.verts]
    print("BOX %s: x %.4f..%.4f y %.4f..%.4f z %.4f..%.4f" % (name, min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)))
    return obj


# --- the school model -------------------------------------------------------------------------

C_BACK = (0.34, 0.14, 0.2, 0.0)
C_FLANK = (0.42, 0.22, 0.28, 0.0)
C_BELLY = (0.55, 0.38, 0.44, 0.0)
C_EYE = (0.03, 0.03, 0.05, 0.0)
C_RING = (0.6, 0.66, 0.75, 0.0)
C_FIN = (0.4, 0.2, 0.26, 0.0)
C_ARM = (0.38, 0.17, 0.22, 0.0)
C_LIGHT = (0.3, 0.68, 1.0, 1.0)
SCHOOL_ANGLES = (0.0, 60.0, 120.0, 180.0, 240.0, 300.0)
SCHOOL_COLOURS = (C_BACK, C_FLANK, C_BELLY, C_BELLY, C_BELLY, C_FLANK)
SCHOOL_RINGS = (0.0163, 0.0205, 0.0255, 0.0262, 0.034, 0.045, 0.056, 0.0655)


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
    for row, xm, way, colour in ((grid[0], BODY_FROM, -1.0, C_ARM), (grid[-1], BODY_TO, 1.0, C_FLANK)):
        tip = m.dab(Vector((0.0, 0.0, xm - HALF)), colour)
        for c in range(around):
            m.face((tip, row[c], row[(c + 1) % around]), Vector((0.0, 0.0, way)), "body")

    def facet(xm, angle):
        r = 0
        while r < len(SCHOOL_RINGS) - 2 and xm > SCHOOL_RINGS[r + 1]:
            r += 1
        t = max(0.0, min(1.0, (xm - SCHOOL_RINGS[r]) / (SCHOOL_RINGS[r + 1] - SCHOOL_RINGS[r])))
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
        plate(EYE_AT[0], turned(82.0), EYE_RADIUS, 8, 0.00028, C_RING, "eyes")
        plate(EYE_AT[0], turned(82.0), EYE_RADIUS * 0.62, 6, 0.0004, C_EYE, "eyes")
        plate(EYE_AT[0] + 0.0001, turned(130.0), 0.0008, 4, 0.0003, C_LIGHT, "lights")
        # the lights: rows along the belly and the lower flanks
        for xm in (0.029, 0.034, 0.039, 0.044, 0.049, 0.054, 0.059):
            for angle in (150.0, 118.0):
                plate(xm + (0.0025 if angle < 120.0 else 0.0), turned(angle), 0.0008, 4, 0.00015, C_LIGHT, "lights")

    def sheet(points, colours, out, group):
        m.face(tuple(m.dab(p, c) for p, c in zip(points, colours)), out, group)

    # the fins: one sheet across the end of the mantle
    z0, z1 = FIN_FROM - HALF, FIN_TO - HALF
    zp = FIN_FROM + (FIN_TO - FIN_FROM) * FIN_PEAK - HALF
    sheet((Vector((0.0, 0.0, z0)), Vector((radius(FIN_FROM + 0.008) + FIN_OUT, 0.0, zp + 0.001)), Vector((0.0, 0.0, z1)),
           Vector((-radius(FIN_FROM + 0.008) - FIN_OUT, 0.0, zp + 0.001))),
          (C_FIN, C_FIN, C_FIN, C_FIN), Vector((0.0, 1.0, 0.0)), "fins (two-sided sheets)")
    # the arms: four thin sheets in a bunch, the ventral ones longest, their tips lit
    for k, (a, long, lit) in enumerate(((math.radians(90.0), 0.0102, False), (math.radians(0.0), 0.0118, False),
                                        (math.radians(180.0), 0.0118, False), (math.radians(270.0), 0.0158, True))):
        lean = Vector((math.cos(a), math.sin(a), 0.0))
        across = Vector((-math.sin(a), math.cos(a), 0.0))
        root = Vector((0.0, 0.0, ARM_XM - HALF + 0.0015))
        tip = root + Vector((0.0, 0.0, -long - 0.0015)) + lean * 0.0018
        w = 0.0018
        sheet((root + across * w, root - across * w, tip), (C_ARM, C_ARM, C_LIGHT if lit else C_ARM), lean.cross(Vector((0.0, 0.0, -1.0))) if False else lean, "arms (two-sided sheets)")
        if lit:
            centre = root.lerp(tip, 0.88)
            sheet((centre + across * 0.0016 + Vector((0.0, 0.0, 0.0016)), centre - across * 0.0016 + Vector((0.0, 0.0, 0.0016)), tip + Vector((0.0, 0.0, -0.0003))),
                  (C_LIGHT, C_LIGHT, C_LIGHT), lean, "lights")

    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) for p in m.verts], [], m.faces)
    mesh.color_attributes.new(name="Col", type="FLOAT_COLOR", domain="POINT")
    colours = mesh.color_attributes["Col"]
    for i, colour in enumerate(m.data):
        colours.data[i].color = colour
    mesh.color_attributes.active_color = colours
    mesh.color_attributes.render_color_index = 0
    mesh.materials.append(material_of("firefly_squid_school", (1.0, 1.0, 1.0, 1.0)))
    return finish(name, mesh, m)


def winding(name, mesh, m):
    """Nothing inside out: each face looks the way it was meant to (Blender's front is the side a face's normal is
    on)."""
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
    scene.render.resolution_x, scene.render.resolution_y = 1400, 700
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    views = [("left", (1, 0, 0), (0, 0, 0), 0.08), ("top", (0.001, 0, 1), (0, 0, 0), 0.08),
             ("under", (0.001, 0, -1), (0, 0, 0), 0.08), ("front", (0, 1, 0), (0, 0, 0), 0.03),
             ("quarter", (0.8, 0.5, 0.35), (0, 0, 0), 0.08), ("head", (0.8, 0.6, 0.2), (0, 0.012, 0), 0.03)]
    for prefix, obj in (("", made[0]), ("game_", made[1]), ("lo_", made[2]), ("school_", made[3])):
        scene.display.shading.color_type = "VERTEX" if prefix == "school_" else "MATERIAL"
        scene.display.shading.show_backface_culling = prefix != "school_"
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            offset = Vector(direction).normalized() * 40.0
            camera.data.ortho_scale = frame
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % (prefix, view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    full = make("firefly_squid", False)
    game = make("firefly_squid_game", GAME)
    low = make("firefly_squid_lo", True)
    school = make_school("firefly_squid_school")
    base = skin(EYE_AT[0], EYE_AT[1], 1.0)
    print("EYE base (%.5f, %.5f, %.5f)" % (base.x, base.y, base.z))
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, "firefly_squid.glb"))
    export_one(game, os.path.join(OUT, "firefly_squid_game.glb"))
    export_one(low, os.path.join(OUT, "firefly_squid_lo.glb"))
    export_one(school, os.path.join(OUT, "firefly_squid_school.glb"), True)
    game.location.x = 0.03
    low.location.x = 0.06
    school.location.x = 0.09
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "firefly_squid.blend"))
    game.location.x = 0.0
    low.location.x = 0.0
    school.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, game, low, school])


if __name__ == "__main__":
    main()
