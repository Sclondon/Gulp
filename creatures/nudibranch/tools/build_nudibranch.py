"""Builds the nudibranch (creatures/nudibranch) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/nudibranch/tools/build_nudibranch.py
    blender --background --python creatures/nudibranch/tools/build_nudibranch.py -- <preview folder>   # with pictures

Writes creatures/nudibranch/models/nudibranch.glb (the full model, for close pictures) and nudibranch_lo.glb
(far off, phones), and the editable creatures/nudibranch/tools/nudibranch.blend (this folder has a .gdignore).
Each model is one still mesh with one surface: the shader (nudibranch.gdshader) colours it, ripples it as it
crawls, flexes it as it swims and waves what stands on its back. It prints a WINDING line: the check that
nothing is inside out.

A Spanish shawl (Flabellinopsis iodinea), 0.07 m long, built from the species (no picture was traced):

- THE BODY: a slim slug, flat underneath (its foot), rounded on top, a blunt head, widest a third of the way
  back, drawn out to a pointed tail.
- THE CERATA: a mane of finger-like stalks standing on the back in eleven rows, four each side of the middle
  line, leaning out and back, the longest over the middle of the body.
- TWO RHINOPHORES on the head: short ringed clubs. TWO ORAL TENTACLES from the front of the head, long and
  tapering, reaching forward and out.

Everything here is in Godot space (metres, Y up, X to its left side, its head at -Z) until it is written out;
the origin is on the ground under its middle (0.035 m behind the front of its head). `xm` below is metres
behind the front of the head.

What a point is, for the shader: UV2.y the part (0 body, 1 a ceras, 2 a rhinophore, 3 an oral tentacle).
UV, on the body: x how far along (0 head to 1 tail), y how high (0 the foot to 1 the top of the back); on
anything else: x from its root (0) to its tip (1), y round it. UV2.x, on anything but the body, a number of
its own from 0 to 1 (so that no two wave quite together). (The glTF writer flips V: what is written here is
1 - v, so that Godot reads v.)
"""

import math
import os
import random
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "models")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = ARGS[0] if ARGS else ""

LENGTH = 0.07
HALF = 0.035
BODY, CERAS, RHINOPHORE, ORAL = range(4)
TAU = math.tau

# The body's outline: metres behind the front of the head, half its width, its height.
PROFILE = [
    (0.0005, 0.0020, 0.0024),
    (0.002, 0.0033, 0.0042),
    (0.006, 0.0040, 0.0056),
    (0.012, 0.0046, 0.0070),
    (0.020, 0.0050, 0.0078),
    (0.030, 0.0050, 0.0080),
    (0.042, 0.0044, 0.0072),
    (0.054, 0.0032, 0.0052),
    (0.063, 0.0019, 0.0030),
    (0.068, 0.0009, 0.0014),
    (0.0698, 0.0003, 0.0004),
]
BODY_FROM = PROFILE[0][0]
BODY_TO = PROFILE[-1][0]


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
for column in (1, 2):
    ys = [p[column] for p in PROFILE]
    _CURVES.append((ys, _slopes(_XS, ys)))


def outline(xm):
    """(half width, height) at `xm`."""
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


def body_point(xm, angle):
    """A point of the skin: `angle` round the body from the top of the back (0) by its left side to the
    middle of the foot (half a turn). The foot is flat on the ground."""
    wide, high = outline(xm)
    c = math.cos(angle)
    s = math.sin(angle)
    y = high * max(0.0, min(1.0, (c + 0.72) / 1.72))
    return Vector((math.copysign(abs(s) ** 0.85, s) * wide, y, xm - HALF))


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.data = []
        self.out = []
        self.count = {}

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


def body(m, low):
    around = 12 if low else 40
    step = 0.0035 if low else 0.0008
    n = round((BODY_TO - BODY_FROM) / step)
    xs = [BODY_FROM + (BODY_TO - BODY_FROM) * i / n for i in range(n + 1)]
    grid = []
    for xm in xs:
        high = outline(xm)[1]
        row = []
        for c in range(around):
            p = body_point(xm, c / around * TAU)
            row.append(m.add(p, (xm / LENGTH, p.y / high), BODY))
        grid.append(row)
    for r in range(len(grid) - 1):
        high = outline(0.5 * (xs[r] + xs[r + 1]))[1]
        for c in range(around):
            k = (c + 1) % around
            quad = (grid[r][c], grid[r][k], grid[r + 1][k], grid[r + 1][c])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((middle.x, middle.y - 0.35 * high, 0.0)), "body")
    for row, xm, way in ((grid[0], 0.0, -1.0), (grid[-1], LENGTH, 1.0)):
        tip = m.add(Vector((0.0, 0.0003, xm - HALF)), (xm / LENGTH, 0.5), BODY)
        for c in range(around):
            m.face((tip, row[c], row[(c + 1) % around]), Vector((0.0, 0.0, way)), "body")


def finger(m, part, name, curve, radius, sides, segs, own):
    """A stalk: a tube round `curve(t)` (t 0 at its root to 1 at its tip), `radius(t)` thick, closed by a
    point at its tip and open at its root (which is sunk in the body)."""
    first = (curve(0.02) - curve(0.0)).normalized()
    ref = Vector((1.0, 0.0, 0.0))
    if abs(first.x) > abs(first.z):
        ref = Vector((0.0, 0.0, 1.0))
    rows = []
    for i in range(segs + 1):
        t = 0.97 * i / segs
        here = curve(t)
        along = (curve(min(t + 0.02, 1.0)) - curve(max(t - 0.02, 0.0))).normalized()
        a = along.cross(ref).normalized()
        b = along.cross(a).normalized()
        r = radius(t)
        row = []
        for k in range(sides):
            turn = k / sides * TAU
            row.append(m.add(here + (a * math.cos(turn) + b * math.sin(turn)) * r, (t, k / sides), part, own))
        rows.append((here, row))
    for i in range(segs):
        axis = (rows[i][0] + rows[i + 1][0]) * 0.5
        for k in range(sides):
            j = (k + 1) % sides
            quad = (rows[i][1][k], rows[i][1][j], rows[i + 1][1][j], rows[i + 1][1][k])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, middle - axis, name)
    end = curve(1.0)
    tip = m.add(end, (1.0, 0.0), part, own)
    for k in range(sides):
        m.face((tip, rows[-1][1][k], rows[-1][1][(k + 1) % sides]), end - rows[-1][0], name)


def bent(p0, p1, p2):
    def curve(t):
        a = 1.0 - t
        return p0 * (a * a) + p1 * (2.0 * a * t) + p2 * (t * t)
    return curve


def cerata(m, low):
    rng = random.Random(7)
    rows = 11
    for r in range(rows):
        for sx in (1.0, -1.0):
            for a0 in (0.22, 0.5, 0.8, 1.08):
                xm = 0.015 + (0.063 - 0.015) * r / (rows - 1) + rng.uniform(-0.0012, 0.0012)
                a = a0 + rng.uniform(-0.06, 0.06)
                env = 0.5 + 0.5 * math.sin(math.pi * max(0.0, min(1.0, (xm - 0.006) / 0.064))) ** 0.8
                length = 0.0165 * env * rng.uniform(0.85, 1.15) * (1.0 - 0.22 * a / 1.1)
                radial = Vector((sx * math.sin(a), math.cos(a), 0.0))
                root = body_point(xm, sx * a) - radial * 0.0014
                way = (radial * (0.55 + 0.5 * a) + Vector((0.0, 0.75, 0.0)) + Vector((0.0, 0.0, 0.45))).normalized()
                p1 = root + way * (length * 0.5)
                p2 = root + way * (length * 0.85) + Vector((0.0, 0.05 * length, 0.3 * length))
                thick = 0.0011 * rng.uniform(0.9, 1.1) * (0.75 + 0.25 * env)
                finger(m, CERAS, "cerata", bent(root, p1, p2),
                       lambda t, thick=thick: thick * (1.0 + 0.25 * math.sin(math.pi * min(t / 0.5, 1.0))) * (1.0 - 0.7 * t ** 1.5),
                       3 if low else 8, 2 if low else 8, rng.random())


def head(m, low):
    rng = random.Random(11)
    for sx in (1.0, -1.0):
        # A rhinophore: a short club ringed with leaves from a quarter of the way up.
        xm = 0.0085
        root = Vector((sx * 0.0021, outline(xm)[1] - 0.0012, xm - HALF))
        way = Vector((sx * 0.28, 1.0, -0.4)).normalized()
        length = 0.0105
        tip = root + way * length + Vector((0.0, 0.0, -0.0008))

        def ring(t):
            leaves = 0.0 if low else 0.5 * max(0.0, math.sin(TAU * 9.0 * t)) * min(1.0, max(0.0, (t - 0.22) / 0.1))
            return 0.0009 * (1.0 - 0.55 * t) * (1.0 + leaves)

        finger(m, RHINOPHORE, "rhinophores", bent(root, root + way * (length * 0.5), tip), ring,
               4 if low else 10, 3 if low else 54, rng.random())
        # An oral tentacle: long and tapering, from the front of the head forward and out.
        root = Vector((sx * 0.0019, 0.0022, 0.003 - HALF))
        way = Vector((sx * 0.8, 0.1, -1.0)).normalized()
        length = 0.0135
        p1 = root + way * (length * 0.5)
        p2 = root + way * length + Vector((sx * 0.0025, 0.001, 0.0015))
        finger(m, ORAL, "oral tentacles", bent(root, p1, p2), lambda t: 0.0008 * (1.0 - 0.75 * t),
               4 if low else 8, 3 if low else 12, rng.random())


# --- the game model ------------------------------------------------------------------------------------
# The user, 2026-11-18: "We should have a twilight princess model to compare to so we can make low poly versions
# while maintaining high quality looks and silhouettes", then "just rebuild all of them, and keep the high
# quality version as well". The game model is built from the same outline and the same stalks as the full one,
# with its triangles spent on what shows: eight points round the body (one on the top of the back, one on each
# side at its widest, the foot's edges), its rings close together at the head and the tail's point and no further
# apart than swimming bends it smoothly (it bends into a U); every ceras still there (the mane is its outline),
# each a bent three-sided finger of ten triangles with a blunt end, whose root is a point deep in the body, so
# no triangles are spent below the skin. Eighty-eight fingers put it over the brief's 900 for its size: about
# 1,300 triangles, the cerata 880 of them (with fewer the mane read as spikes, not fingers).

GAME_RINGS = [0.0005, 0.0018, 0.004, 0.0075, 0.0115, 0.016, 0.0205, 0.025, 0.0295, 0.034, 0.0385, 0.043,
              0.0475, 0.052, 0.056, 0.0595, 0.0628, 0.0658, 0.0683, 0.0698]
GAME_AROUND = 8


def body_game(m):
    around = GAME_AROUND
    xs = GAME_RINGS
    grid = []
    for xm in xs:
        high = outline(xm)[1]
        row = []
        for c in range(around):
            p = body_point(xm, c / around * TAU)
            row.append(m.add(p, (xm / LENGTH, p.y / high), BODY))
        grid.append(row)
    for r in range(len(grid) - 1):
        high = outline(0.5 * (xs[r] + xs[r + 1]))[1]
        for c in range(around):
            k = (c + 1) % around
            quad = (grid[r][c], grid[r][k], grid[r + 1][k], grid[r + 1][c])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((middle.x, middle.y - 0.35 * high, 0.0)), "body")
    for row, xm, way in ((grid[0], 0.0, -1.0), (grid[-1], LENGTH, 1.0)):
        tip = m.add(Vector((0.0, 0.0003, xm - HALF)), (xm / LENGTH, 0.5), BODY)
        for c in range(around):
            m.face((tip, row[c], row[(c + 1) % around]), Vector((0.0, 0.0, way)), "body")


def stalk_game(m, part, name, curve, radius, own, sides=3, at=(0.38, 0.96), sunk=0.005, wider=1.2):
    """A finger of the game model: a point sunk `sunk` metres below its root (inside the body), a ring of
    `sides` points at each of `at` along it, and a flat end on the last ring (it is blunt, as the full
    finger's end is): with three sides and two rings, ten triangles. The rings are `wider` times the full
    finger's radius there, so that the few-sided finger is about as wide as the round one from any side."""
    first = (curve(0.02) - curve(0.0)).normalized()
    ref = Vector((1.0, 0.0, 0.0))
    if abs(first.x) > abs(first.z):
        ref = Vector((0.0, 0.0, 1.0))
    rings = []
    for t in at:
        here = curve(t)
        along = (curve(min(t + 0.02, 1.0)) - curve(max(t - 0.02, 0.0))).normalized()
        a = along.cross(ref).normalized()
        b = along.cross(a).normalized()
        r = radius(t) * wider
        rings.append((here, [m.add(here + (a * math.cos(k / sides * TAU) + b * math.sin(k / sides * TAU)) * r,
                                   (t, k / sides), part, own) for k in range(sides)]))
    # (no deeper than keeps the point inside the body, which is thin towards the tail)
    deep = curve(0.0) - first * sunk
    while sunk > 0.0004:
        wide, high = outline(deep.z + HALF)
        if 0.0005 < deep.y < 0.85 * high and abs(deep.x) < 0.75 * wide:
            break
        sunk *= 0.85
        deep = curve(0.0) - first * sunk
    root = m.add(deep, (0.0, 0.0), part, own)
    here, ring = rings[0]
    for k in range(sides):
        j = (k + 1) % sides
        middle = (m.verts[ring[k]] + m.verts[ring[j]]) * 0.5
        m.face((root, ring[k], ring[j]), middle - (deep + here) * 0.5, name)
    for (h0, r0), (h1, r1) in zip(rings, rings[1:]):
        axis = (h0 + h1) * 0.5
        for k in range(sides):
            j = (k + 1) % sides
            quad = (r0[k], r0[j], r1[j], r1[k])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, middle - axis, name)
    here, ring = rings[-1]
    if sides == 3:
        m.face(tuple(ring), here - rings[-2][0], name)
    else:
        tip = m.add(curve(1.0), (1.0, 0.0), part, own)
        for k in range(sides):
            m.face((tip, ring[k], ring[(k + 1) % sides]), curve(1.0) - here, name)


def cerata_game(m):
    """The same eighty-eight cerata as the full model (the same random numbers, so each stands where it does
    there), each a finger of ten triangles."""
    rng = random.Random(7)
    rows = 11
    for r in range(rows):
        for sx in (1.0, -1.0):
            for a0 in (0.22, 0.5, 0.8, 1.08):
                xm = 0.015 + (0.063 - 0.015) * r / (rows - 1) + rng.uniform(-0.0012, 0.0012)
                a = a0 + rng.uniform(-0.06, 0.06)
                env = 0.5 + 0.5 * math.sin(math.pi * max(0.0, min(1.0, (xm - 0.006) / 0.064))) ** 0.8
                length = 0.0165 * env * rng.uniform(0.85, 1.15) * (1.0 - 0.22 * a / 1.1)
                radial = Vector((sx * math.sin(a), math.cos(a), 0.0))
                root = body_point(xm, sx * a) - radial * 0.0014
                way = (radial * (0.55 + 0.5 * a) + Vector((0.0, 0.75, 0.0)) + Vector((0.0, 0.0, 0.45))).normalized()
                p1 = root + way * (length * 0.5)
                p2 = root + way * (length * 0.85) + Vector((0.0, 0.05 * length, 0.3 * length))
                thick = 0.0011 * rng.uniform(0.9, 1.1) * (0.75 + 0.25 * env)
                stalk_game(m, CERAS, "cerata", bent(root, p1, p2),
                           lambda t, thick=thick: thick * (1.0 + 0.25 * math.sin(math.pi * min(t / 0.5, 1.0))) * (1.0 - 0.7 * t ** 1.5),
                           rng.random())


def head_game(m):
    """The rhinophores and oral tentacles of the full model (the same random numbers), lighter: a rhinophore
    a four-sided club of three rings (its leaves are not in the outline: the shader still draws its rings),
    an oral tentacle three-sided, of three rings."""
    rng = random.Random(11)
    for sx in (1.0, -1.0):
        xm = 0.0085
        root = Vector((sx * 0.0021, outline(xm)[1] - 0.0012, xm - HALF))
        way = Vector((sx * 0.28, 1.0, -0.4)).normalized()
        length = 0.0105
        tip = root + way * length + Vector((0.0, 0.0, -0.0008))

        def ring(t):
            # (the full club's leaves, averaged: its rings stand out by half its width over three fifths of it)
            leaves = 0.32 * min(1.0, max(0.0, (t - 0.22) / 0.1))
            return 0.0009 * (1.0 - 0.55 * t) * (1.0 + leaves)

        finger(m, RHINOPHORE, "rhinophores", bent(root, root + way * (length * 0.5), tip), ring, 4, 3, rng.random())
        root = Vector((sx * 0.0019, 0.0022, 0.003 - HALF))
        way = Vector((sx * 0.8, 0.1, -1.0)).normalized()
        length = 0.0135
        p1 = root + way * (length * 0.5)
        p2 = root + way * length + Vector((sx * 0.0025, 0.001, 0.0015))
        finger(m, ORAL, "oral tentacles", bent(root, p1, p2), lambda t: 0.0008 * 1.15 * (1.0 - 0.75 * t), 3, 3, rng.random())


def make(name, low, game=False):
    m = Mesh()
    if game:
        body_game(m)
        cerata_game(m)
        head_game(m)
    else:
        body(m, low)
        cerata(m, low)
        head(m, low)
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
    material = bpy.data.materials.get("nudibranch") or bpy.data.materials.new("nudibranch")
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.5, 0.2, 0.8, 1.0)
    material.diffuse_color = (0.5, 0.2, 0.8, 1.0)
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
    """Nothing inside out: the skin of the body faces away from its middle line, the skin of each stalk
    away from the stalk's own middle line (Blender's front is the side a face's normal is on)."""
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
    # (Blender space: it lies along Y, its head at +Y, up is Z)
    views = [("left", (1, 0, 0), (0, 0, 0.01), 0.1), ("right", (-1, 0, 0), (0, 0, 0.01), 0.1),
             ("front", (0, 1, 0), (0, 0, 0.01), 0.06), ("back", (0, -1, 0), (0, 0, 0.01), 0.06),
             ("top", (0.001, 0, 1), (0, 0, 0), 0.1), ("under", (0.001, 0, -1), (0, 0, 0), 0.1),
             ("head", (0.7, 0.6, 0.4), (0, 0.03, 0.006), 0.04)]
    for tag, obj in zip(("", "lo_", "game_"), made):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if tag == "lo_" and view not in ("left", "top"):
                continue
            offset = Vector(direction).normalized() * 40.0
            camera.data.ortho_scale = frame
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % (tag, view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    full = make("nudibranch", False)
    low = make("nudibranch_lo", True)
    game = make("nudibranch_game", False, True)
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, "nudibranch.glb"))
    export_one(low, os.path.join(OUT, "nudibranch_lo.glb"))
    export_one(game, os.path.join(OUT, "nudibranch_game.glb"))
    # (in the .blend all three side by side: the full, the game model, the low)
    game.location.x = 0.06
    low.location.x = 0.12
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "nudibranch.blend"))
    game.location.x = 0.0
    low.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low, game])


if __name__ == "__main__":
    main()
