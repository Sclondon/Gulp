"""Builds the California halibut (creatures/california_halibut) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/california_halibut/tools/build_california_halibut.py
    blender --background --python creatures/california_halibut/tools/build_california_halibut.py -- <preview folder>   # with pictures

Writes creatures/california_halibut/models/california_halibut.glb (the full model) and california_halibut_lo.glb
(far off, phones), and the editable creatures/california_halibut/tools/california_halibut.blend (this folder
has a .gdignore). Each model is one still mesh with one surface: the shader (california_halibut.gdshader) draws
every marking, swims it, lays it down and works its jaw. It prints a WINDING line: the check that nothing is
inside out.

A California halibut (Paralichthys californicus), 1 m from the tip of its snout to the end of its tail, built
from what the species looks like (no picture was traced). A flatfish: it lies on its side. This one is
left-eyed (its left side is uppermost; about three in five are), so as it lies, nose to -Z:

- ITS UPPER SIDE is +Y. The edge of its back (the dorsal fin) is +X and the edge of its belly (the anal fin,
  the pelvic fin, the lower jaw) is -X.
- THE BODY: a long oval slab, 0.32 m across and 0.07 m thick, domed above and nearly flat beneath, running to
  a narrow tail wrist. Both eyes are on the upper side of the head, each a dome.
- THE MOUTH: big, at the nose, running back and towards -X to under the eyes. The LOWER JAW is a part of its
  own (everything of the head on the -X side of the mouth's line, ahead of the hinge): the shader swings it
  about the hinge. Inside are the roof of the mouth, the jaw's own inner face (teeth are drawn on both by
  the shader) and a dark web between them half way up, so that the open mouth is dark seen from above.
- THE FINS, each a thin closed blade lying flat: the dorsal fin fringing the +X edge from over the eyes to the
  tail wrist, the anal fin the -X edge from behind the belly; the tail, a fan; one pectoral fin on the upper
  side pointing back; one small pelvic fin at the -X edge.

Everything here is in Godot space (metres, Y up, nose at -Z) until it is written out; the origin is on its
middle line, half way along (0.5 m behind the tip of its snout) and half way up its thickness (its underside is
0.0355 m below the origin). `xm` below is metres behind the tip of the snout, `x` metres across.

What a point is, for the shader: UV2.y the part (0 body, 1 lower jaw, 2 the dorsal and anal fins, 3 the tail,
4 the pectoral and pelvic fins, 5 an eye). UV2.x, on the body and jaw: 1 inside the mouth. UV, on the body: x
how far along (0 snout to 1 tail end), y how far across; inside the mouth: x from the nose (0) to the hinge
(1), y from the under lip (0) to the upper lip (1); on a fin: x from its root (0) to its edge (1), y from its
leading end (0) to its trailing end (1); on an eye: x from its middle (0) to its rim (1). (The glTF writer
flips V: what is written here is 1 - v, so that Godot reads v.)

The numbers marked "as the shader has it" are in california_halibut.gdshader too: change one, change the other.
"""

NAME = "california_halibut"
LENGTH = 1.0
HALF = 0.5
BODY, JAW, FRINGE, TAIL, PAIRED, EYE = range(6)


import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "models")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = ARGS[0] if ARGS else ""
TAU = math.tau
UP = Vector((0.0, 1.0, 0.0))
DOWN = Vector((0.0, -1.0, 0.0))
SIDE = Vector((1.0, 0.0, 0.0))


def to_b(p):
    return Vector((p.x, -p.z, p.y))


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def lerp(a, b, t):
    return a + (b - a) * t


class Curve:
    """A curve through (x, y) points that never overshoots them (Fritsch and Carlson)."""

    def __init__(self, points):
        self.xs = [p[0] for p in points]
        self.ys = [p[1] for p in points]
        xs, ys = self.xs, self.ys
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
        self.m = m

    def __call__(self, x):
        xs, ys, m = self.xs, self.ys, self.m
        x = max(xs[0], min(xs[-1], x))
        i = 0
        while i < len(xs) - 2 and x > xs[i + 1]:
            i += 1
        h = xs[i + 1] - xs[i]
        t = (x - xs[i]) / h
        a = (2 * t ** 3 - 3 * t ** 2 + 1) * ys[i] + (t ** 3 - 2 * t ** 2 + t) * h * m[i]
        b = (-2 * t ** 3 + 3 * t ** 2) * ys[i + 1] + (t ** 3 - t ** 2) * h * m[i + 1]
        return a + b


def steps(start, pieces, low, coarser=4.0):
    """Places along the animal: from `start`, then for each (until, step) piece, evenly to `until`."""
    xs = []
    x = start
    for until, step in pieces:
        if low:
            step *= coarser
        n = max(1, round((until - x) / step))
        for i in range(n):
            xs.append(x + (until - x) * i / n)
        x = until
    xs.append(x)
    return xs


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        # per point: (uv, uv2)
        self.data = []
        # per face: the way it should face
        self.out = []
        self.count = {}

    def add(self, p, uv, part, extra=0.0):
        self.verts.append(p)
        self.data.append(((uv[0], 1.0 - uv[1]), (extra, 1.0 - part)))
        return len(self.verts) - 1

    def face(self, points, out, name):
        """A face wound so that its front (the side its points go round anticlockwise) is towards `out`."""
        ps = [self.verts[i] for i in points]
        n = Vector((0.0, 0.0, 0.0))
        for i in range(len(ps)):
            n += ps[i].cross(ps[(i + 1) % len(ps)])
        if n.length < 1e-13:
            return
        if n.dot(out) < 0.0:
            points = tuple(reversed(points))
        self.faces.append(tuple(points))
        self.out.append((Vector(out), name))
        self.count[name] = self.count.get(name, 0) + 1


def slab_rows(m, xs, columns, top, bot, data, lo=0, hi=None, edges=(True, True), reuse=None):
    """Rows of a flat body's skin: at each place along it (`xs`, metres behind the nose) a row of points across
    its upper side and a row across its under side, at `columns(xm)[lo..hi]` (metres to the side, from its +X
    edge to its -X edge). Where an end of the row is the body's own edge (`edges`), the two sides share that
    point. `data(xm, x, upper)` gives a point's (uv, part, extra). `reuse` is a row to begin from in place of
    the first."""
    rows = []
    for k, xm in enumerate(xs):
        if k == 0 and reuse is not None:
            rows.append(reuse)
            continue
        cols = columns(xm)
        last = len(cols) - 1 if hi is None else hi
        t = []
        b = []
        for i in range(lo, last + 1):
            x = cols[i]
            uv, part, extra = data(xm, x, True)
            ti = m.add(Vector((x, top(xm, x), xm - HALF)), uv, part, extra)
            t.append(ti)
            if (i == lo and edges[0]) or (i == last and edges[1]):
                b.append(ti)
            else:
                uv, part, extra = data(xm, x, False)
                b.append(m.add(Vector((x, bot(xm, x), xm - HALF)), uv, part, extra))
        rows.append((t, b))
    return rows


def slab_faces(m, rows, name):
    for r in range(len(rows) - 1):
        for which, out in ((0, UP), (1, DOWN)):
            a = rows[r][which]
            b = rows[r + 1][which]
            for i in range(len(a) - 1):
                m.face((a[i], a[i + 1], b[i + 1], b[i]), out, name)


def slab_cap(m, row, tip, name):
    """Closes an end of a flat body: a fan from the point `tip` to each side of a row."""
    for which, out in ((0, UP), (1, DOWN)):
        a = row[which]
        for i in range(len(a) - 1):
            m.face((tip, a[i], a[i + 1]), out, name)


def blade(m, part, name, point, place, facing, thick, nt, nu, extra=None):
    """A fin: a thin closed blade. `point(t, u)` is a place in the fin's own flat (t 0 at its root to 1 at
    its edge, u 0 at its leading end to 1 at its trailing end), `place` puts that in the model, `facing`
    is the way one of its two skins faces. It is `thick` at its root, a foil across (nothing at either
    end), thinning to nothing at its edge."""
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
                row.append(m.add(p, (t, u), part, extra(t, u) if extra else 0.0))
            grid.append(row)
        for ti in range(nt):
            for ui in range(nu):
                m.face((grid[ti][ui], grid[ti][ui + 1], grid[ti + 1][ui + 1], grid[ti + 1][ui]), facing * side, name)


def dome(m, part, name, skin, at, radius, height, toward, low):
    """An eye: a dome lying on the skin. `skin(a, b)` is a place on the skin by two coordinates (metres)."""
    spokes = 10 if low else 32
    rings = 3 if low else 10
    a0, b0 = at
    e = 0.003
    out = (skin(a0 + e, b0) - skin(a0 - e, b0)).cross(skin(a0, b0 + e) - skin(a0, b0 - e))
    out.normalize()
    if out.dot(toward) < 0.0:
        out = -out
    middle = m.add(skin(a0, b0) + out * height, (0.0, 0.0), part)
    last = None
    for k in range(1, rings + 1):
        r = k / rings
        row = []
        for s in range(spokes):
            a = s / spokes * TAU
            p = skin(a0 + math.cos(a) * radius * r, b0 + math.sin(a) * radius * r)
            # (its rim is sunk a little into the skin, so that no gap shows under it)
            row.append(m.add(p + out * (height * (1.0 - r * r) ** 0.7 - 0.0012 * r ** 4), (r, 0.0), part))
        for s in range(spokes):
            n = (s + 1) % spokes
            if last is None:
                m.face((middle, row[s], row[n]), out, name)
            else:
                m.face((last[s], row[s], row[n], last[n]), out, name)
        last = row
    return out


def tube(m, part, name, centre, radii, nt, na):
    """A round tail or spine lying along the animal: `centre(t)` its middle and `radii(t)` its half width and
    half height, t 0 at its front to 1 at its end. Closed at both ends."""
    rows = []
    for i in range(nt + 1):
        t = i / nt
        c = centre(t)
        rx, ry = radii(t)
        rows.append([m.add(c + Vector((math.cos(k / na * TAU) * rx, math.sin(k / na * TAU) * ry, 0.0)), (t, k / na), part)
                     for k in range(na)])
    for i in range(nt):
        for k in range(na):
            n = (k + 1) % na
            a = (k + 0.5) / na * TAU
            m.face((rows[i][k], rows[i][n], rows[i + 1][n], rows[i + 1][k]), Vector((math.cos(a), math.sin(a), 0.0)), name)
    for row, t, way in ((rows[0], 0.0, -1.0), (rows[-1], 1.0, 1.0)):
        tip = m.add(centre(t) + Vector((0.0, 0.0, way * 0.0005)), (t, 0.0), part)
        for k in range(na):
            m.face((tip, row[k], row[(k + 1) % na]), Vector((0.0, 0.0, way)), name)


def make_object(name, m, colour):
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
    material = bpy.data.materials.get(NAME) or bpy.data.materials.new(NAME)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = colour
    material.diffuse_color = colour
    mesh.materials.append(material)
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    lo = [min(p[i] for p in m.verts) for i in range(3)]
    hi = [max(p[i] for p in m.verts) for i in range(3)]
    print("BUILT %s verts=%d tris=%d from (%.4f, %.4f, %.4f) to (%.4f, %.4f, %.4f)" % ((name, len(mesh.vertices), tris) + tuple(lo) + tuple(hi)))
    winding(name, mesh, m)
    return obj


def winding(name, mesh, m):
    """Nothing inside out: each face is looked at against the way it was built to face: the upper skin up,
    the under skin down, each skin of a fin away from the fin's own flat, an eye out from the head, a tail out
    from its middle (Blender's front is the side a face's normal is on)."""
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


def render(folder, made, frame, head_at):
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
    # (Blender space: the animal lies along Y, its nose at +Y, up is Z)
    views = [("left", (1, 0, 0), (0, 0, 0), frame), ("right", (-1, 0, 0), (0, 0, 0), frame),
             ("front", (0, 1, 0), (0, 0, 0), frame * 0.8), ("back", (0, -1, 0), (0, 0, 0), frame * 0.8),
             ("top", (0.001, 0, 1), (0, 0, 0), frame * 1.8), ("under", (0.001, 0, -1), (0, 0, 0), frame * 1.8),
             ("head", (0.6, 0.6, 0.5), (0, head_at, 0), frame * 0.3),
             ("head_under", (0.5, 0.6, -0.6), (0, head_at, 0), frame * 0.3),
             ("tail", (0.7, -0.6, 0.4), (0, -head_at, 0), frame * 0.45)]
    for low, obj in ((False, made[0]), (True, made[1])):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, size in views:
            if low and view not in ("top", "head"):
                continue
            offset = Vector(direction).normalized() * 40.0
            camera.data.ortho_scale = size
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % ("lo_" if low else "", view))
            bpy.ops.render.render(write_still=True)


def build_all(make, colour, frame, head_at):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    full = make_object(NAME, make(False), colour)
    low = make_object(NAME + "_lo", make(True), colour)
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, NAME + ".glb"))
    export_one(low, os.path.join(OUT, NAME + "_lo.glb"))
    low.location.x = frame
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, NAME + ".blend"))
    low.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low], frame, head_at)


# The body's outline: metres behind the snout, how far its edge is to +X (its back) and to -X (its belly), how
# thick it is above its seam (the flat its fins lie in) and below.
PROFILE = [
    (0.0, 0.0, 0.0, 0.0, 0.0),
    (0.004, 0.006, 0.007, 0.006, 0.004),
    (0.02, 0.020, 0.026, 0.014, 0.008),
    (0.05, 0.040, 0.052, 0.024, 0.012),
    (0.10, 0.072, 0.085, 0.036, 0.016),
    (0.16, 0.105, 0.115, 0.045, 0.019),
    (0.24, 0.135, 0.140, 0.050, 0.021),
    (0.34, 0.155, 0.155, 0.050, 0.021),
    (0.45, 0.160, 0.160, 0.047, 0.020),
    (0.56, 0.145, 0.145, 0.041, 0.018),
    (0.66, 0.115, 0.115, 0.034, 0.015),
    (0.74, 0.080, 0.080, 0.027, 0.012),
    (0.80, 0.050, 0.050, 0.021, 0.010),
    (0.84, 0.038, 0.038, 0.017, 0.008),
    (0.87, 0.036, 0.036, 0.012, 0.006),
    (0.895, 0.030, 0.030, 0.003, 0.002),
]
BODY_TO = 0.895
_CURVES = [Curve([(p[0], p[c]) for p in PROFILE]) for c in (1, 2, 3, 4)]

# As the shader has it: the flat the fins lie in; where the jaw hinges; the line of the mouth.
SEAM = -0.0145
HINGE = 0.125
MOUTH_K = 0.42


def outline(xm):
    """(edge to +X, edge to -X, thickness above the seam, thickness below it) at `xm`."""
    return [max(c(xm), 0.0004) for c in _CURVES]


def mouth_x(xm):
    return -MOUTH_K * xm


def cut_x(xm):
    """Where the skin's points are split across: the line of the mouth, then back to the middle line."""
    a, b, _, _ = outline(xm)
    x = mouth_x(xm) if xm <= HINGE else mouth_x(HINGE) * (1.0 - smooth(HINGE, 0.36, xm))
    return max(-0.8 * b, min(0.8 * a, x))


def top(xm, x):
    a, b, t, _ = outline(xm)
    u = min(1.0, abs(x) / (a if x >= 0.0 else b))
    return SEAM + t * (1.0 - u * u) ** 0.7


def bot(xm, x):
    a, b, _, t = outline(xm)
    u = min(1.0, abs(x) / (a if x >= 0.0 else b))
    return SEAM - t * (1.0 - u * u) ** 0.45


def skin(xm, x):
    return Vector((x, top(xm, x), xm - HALF))


def body(m, low):
    n = 7 if low else 24

    def columns(xm):
        a, b, _, _ = outline(xm)
        cx = cut_x(xm)
        return ([cx + (a - cx) * math.cos(i / n * math.pi / 2.0) for i in range(n + 1)]
                + [cx - (b + cx) * math.sin(j / n * math.pi / 2.0) for j in range(1, n + 1)])

    def data(xm, x, upper):
        return (xm / LENGTH, 0.5 + x / 0.34), BODY, 0.0

    def jaw_data(xm, x, upper):
        return (xm / LENGTH, 0.5 + x / 0.34), JAW, 0.0

    front = list(reversed(steps(0.0012, [(0.012, 0.0012), (HINGE, 0.003)], low, 3.0)))
    back = steps(HINGE, [(0.30, 0.005), (0.84, 0.0075), (BODY_TO, 0.004)], low)
    rows = slab_rows(m, back, columns, top, bot, data)
    slab_faces(m, rows, "body")
    slab_cap(m, rows[-1], m.add(Vector((0.0, SEAM, BODY_TO + 0.003 - HALF)), (BODY_TO / LENGTH, 0.5), BODY), "body")
    hinge = rows[0]
    # ahead of the hinge the head is two: its upper part (to +X of the mouth's line) and the lower jaw
    upper = slab_rows(m, front, columns, top, bot, data, 0, n, (True, False), (hinge[0][:n + 1], hinge[1][:n + 1]))
    slab_faces(m, upper, "body")
    slab_cap(m, upper[-1], m.add(Vector((0.0, SEAM, -HALF)), (0.0, 0.5), BODY), "body")
    jaw = slab_rows(m, front, columns, top, bot, jaw_data, n, 2 * n, (False, True), (hinge[0][n:], hinge[1][n:]))
    slab_faces(m, jaw, "jaw")
    slab_cap(m, jaw[-1], m.add(Vector((0.0, SEAM, -HALF)), (0.0, 0.5), JAW), "jaw")
    # Inside the mouth: the roof (the upper part's wall along the mouth's line, hollowed a little), the jaw's
    # own wall, and a web between the two half way up.
    for part, name, deep, out in ((BODY, "mouth roof", 0.010, Vector((-1.0, 0.0, 0.0))), (JAW, "jaw inside", -0.008, Vector((1.0, 0.0, 0.0)))):
        walls = []
        webs = ([], [])
        for xm in front:
            cx = columns(xm)[n]
            hollow = deep * math.sin(math.pi * xm / HINGE) ** 0.6
            yt, yb = top(xm, cx), bot(xm, cx)
            s = xm / HINGE
            walls.append((m.add(Vector((cx, yt, xm - HALF)), (s, 1.0), part, 1.0),
                          m.add(Vector((cx + hollow, (yt + yb) * 0.5, xm - HALF)), (s, 0.5), part, 1.0),
                          m.add(Vector((cx, yb, xm - HALF)), (s, 0.0), part, 1.0)))
            for web in webs:
                web.append(m.add(Vector((cx + hollow, (yt + yb) * 0.5, xm - HALF)), (s, 0.5), part, 1.0))
        tip = m.add(Vector((0.0, SEAM, -HALF)), (0.0, 0.5), part, 1.0)
        for k in range(len(walls) - 1):
            for i in (0, 1):
                m.face((walls[k][i], walls[k + 1][i], walls[k + 1][i + 1], walls[k][i + 1]), out, name)
        for i in (0, 1):
            m.face((tip, walls[-1][i], walls[-1][i + 1]), out, name)
        if part == BODY:
            roof_webs = webs
        else:
            for which, way in ((0, UP), (1, DOWN)):
                a, b = roof_webs[which], webs[which]
                for k in range(len(a) - 1):
                    m.face((a[k], a[k + 1], b[k + 1], b[k]), way, "mouth web")


def fins(m, low):
    d = 4 if low else 1
    lean = 0.5

    def high(u):
        return 0.004 + 0.055 * (4.0 * u * (1.0 - u)) ** 0.45 * (0.6 + 0.4 * smooth(0.0, 0.55, u))

    def flat(p):
        return Vector((p[1], SEAM, p[0] - HALF))

    # The dorsal fin (the +X edge, from over the eyes to the tail wrist) and the anal fin (the -X edge): low
    # fringes, tallest behind the middle, their rays leaning back.
    for name, x0, x1, column, way in (("dorsal", 0.075, 0.84, 0, 1.0), ("anal", 0.27, 0.84, 1, -1.0)):
        def point(t, u, x0=x0, x1=x1, column=column, way=way):
            xr = lerp(x0, x1, u)
            h = high(u)
            return (xr + math.sin(lean) * h * t, way * (outline(xr)[column] - 0.008 + (h * math.cos(lean) + 0.008) * t))

        blade(m, FRINGE, name, point, flat, UP, 0.005, max(2, 6 // d), 140 // d)

    # The tail: a fan, its middle rays the longest and its edge a little hollowed either side of them.
    def tail_point(t, u):
        angle = lerp(-0.62, 0.62, u)
        reach = 0.1535 - 0.01 * math.sin(math.pi * u) ** 2 * math.cos(TAU * (u - 0.5)) - 0.018 * abs(2.0 * u - 1.0) ** 2
        return (0.855 + t * reach * math.cos(angle), (u - 0.5) * 0.066 + t * reach * math.sin(angle))

    blade(m, TAIL, "tail", tail_point, flat, UP, 0.007, 16 // d, 32 // d)

    # The pectoral fin of the upper side: behind the gill cover, pointing back, lying just over the skin.
    def paddle(length, wide):
        def point(t, u):
            t *= 0.98
            return (length * t, (u - 0.5) * (0.35 * wide * (1.0 - t) + 2.3 * wide * t ** 0.7 * (1.0 - t) ** 0.6))
        return point

    root = Vector((-0.012, top(0.265, -0.012) - 0.004, 0.265 - HALF))
    span = Vector((-0.08, 0.14, 1.0)).normalized()
    chord = Vector((1.0, 0.0, 0.08)).normalized()
    blade(m, PAIRED, "pectoral", paddle(0.125, 0.05), lambda p: root + span * p[0] + chord * p[1],
          span.cross(chord).normalized() * (1.0 if span.cross(chord).y > 0.0 else -1.0), 0.005, 16 // d, 12 // d)
    # The pelvic fin: small, at the -X edge ahead of the anal fin.
    proot = Vector((-(outline(0.2)[1] - 0.012), SEAM, 0.2 - HALF))
    pspan = Vector((-0.55, 0.0, 0.83)).normalized()
    pchord = Vector((0.83, 0.0, 0.55)).normalized()
    blade(m, PAIRED, "pelvic", paddle(0.06, 0.03), lambda p: proot + pspan * p[0] + pchord * p[1], UP, 0.004, 10 // d, 8 // d)


def make(low):
    m = Mesh()
    body(m, low)
    # Both eyes on the upper side: the lower one near the mouth, the one that came round nearer the back's edge.
    dome(m, EYE, "eyes", skin, (0.088, -0.004), 0.0125, 0.009, UP, low)
    dome(m, EYE, "eyes", skin, (0.098, 0.036), 0.0125, 0.009, UP, low)
    fins(m, low)
    return m


if __name__ == "__main__":
    build_all(make, (0.5, 0.4, 0.26, 1.0), 1.15, 0.4)
