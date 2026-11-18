"""Builds the yellowfin tuna (creatures/yellowfin_tuna) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/yellowfin_tuna/tools/build_yellowfin_tuna.py
    blender --background --python creatures/yellowfin_tuna/tools/build_yellowfin_tuna.py -- <preview folder>   # with pictures

Writes creatures/yellowfin_tuna/models/yellowfin_tuna.glb (the full model, for close pictures) and
yellowfin_tuna_lo.glb (far off, phones), and the editable creatures/yellowfin_tuna/tools/yellowfin_tuna.blend
(this folder has a .gdignore). Each model is one still mesh with one surface: the shader
(yellowfin_tuna.gdshader) draws every marking and swims it. It prints a WINDING line: the check that nothing
is inside out.

A yellowfin tuna (Thunnus albacares), 1.5 m from the tip of its snout to the tips of its tail, built from the
species (the component's README says which pictures were looked at; none was traced):

- THE BODY: a deep, round, rigid torpedo, deepest (0.39 m) and widest (0.28 m) a third of the way back, running
  to a very narrow tail wrist with a keel on each side. A pointed head; the line of the mouth, a groove; the
  gill cover, a step; a big eye, a low dome on each side.
- THE FINS, each a thin closed blade (two skins that meet at its edges): the first dorsal (thirteen spines, its
  edge scalloped between them; the shader folds it down); the long sickle second dorsal and anal fins; nine
  finlets above and eight below, from those back to the tail; the tall stiff crescent tail; two long pectoral
  fins held out like wings; two small pelvic fins.

Everything here is in Godot space (metres, Y up, X to its left side, its nose at -Z) until it is written out;
the origin is on its middle line, half way along (0.75 m behind the tip of its snout). `xm` below is metres
behind the tip of the snout.

What a point is, for the shader: UV2.y the part (0 body, 1 first dorsal, 2 the sickle fins, 3 a finlet, 4 the
tail, 5 a pectoral fin, 6 a pelvic fin, 7 an eye). UV, on the body: x how far along (0 snout to 1 tail tips),
y how high on its side (1 the ridge of the back, 0.5 its middle line, 0 the keel of the belly); on a fin: x
from its root (0) to its tip (1), y from its leading edge (0) to its trailing edge (1); on an eye: x from its
middle (0) to its rim (1). UV2.x, on the first dorsal, how far the point stands above the fin's root (metres),
for folding it. (The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.)

The numbers marked "as the shader has it" are in yellowfin_tuna.gdshader too: change one, change the other.
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

LENGTH = 1.5
HALF = 0.75
BODY, DORSAL, SICKLE, FINLET, TAIL, PECTORAL, PELVIC, EYE = range(8)
TAU = math.tau

# The body's outline: metres behind the snout, half its depth above its middle line, half its depth below,
# half its width.
PROFILE = [
    (0.0, 0.0, 0.0, 0.0),
    (0.003, 0.0065, 0.0075, 0.0055),
    (0.012, 0.016, 0.019, 0.0135),
    (0.04, 0.037, 0.046, 0.031),
    (0.10, 0.071, 0.085, 0.057),
    (0.18, 0.108, 0.122, 0.085),
    (0.28, 0.146, 0.157, 0.112),
    (0.40, 0.175, 0.184, 0.133),
    (0.52, 0.189, 0.197, 0.142),
    (0.64, 0.186, 0.192, 0.140),
    (0.78, 0.162, 0.171, 0.123),
    (0.90, 0.127, 0.136, 0.100),
    (1.02, 0.089, 0.095, 0.072),
    (1.12, 0.058, 0.062, 0.049),
    (1.20, 0.038, 0.039, 0.034),
    (1.27, 0.024, 0.024, 0.025),
    (1.31, 0.019, 0.019, 0.021),
    (1.345, 0.020, 0.020, 0.012),
    (1.385, 0.003, 0.003, 0.002),
]
BODY_FROM = 0.002
BODY_TO = 1.385

# As the shader has it: the line of the mouth, the edge of the gill cover, the eye.
MOUTH_TO = 0.132
EYE_AT = (0.145, 0.024)
EYE_RADIUS = 0.03


def mouth_y(xm):
    return -0.004 - 0.34 * xm + 0.55 * xm * xm


def gill_x(y):
    return 0.36 - 3.0 * (y + 0.015) ** 2


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
        out.append(max(a + b, 0.0005))
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
    side = math.copysign(abs(s) ** 0.92, s) * wide
    # the keels: a ridge along each side of the tail wrist
    keel = 0.009 * smooth(1.15, 1.27, xm) * (1.0 - smooth(1.32, 1.37, xm))
    side += math.copysign(keel * math.exp(-(c / 0.3) ** 2), s)
    # the mouth: a groove from the tip of the snout back and down to under the eye
    if xm < MOUTH_TO + 0.01:
        groove = math.exp(-((y - mouth_y(xm)) / 0.0035) ** 2) * smooth(0.004, 0.02, xm) * (1.0 - smooth(MOUTH_TO - 0.012, MOUTH_TO + 0.004, xm))
        side *= 1.0 - 0.08 * groove
    # the gill cover: it stands a little proud of the body behind its edge
    behind = xm - gill_x(y)
    if behind > 0.0 and wide > 0.01:
        mask = smooth(-0.95, -0.8, c) * (1.0 - smooth(0.4, 0.6, c))
        step = 0.0045 * smooth(0.0, 0.004, behind) * math.exp(-behind / 0.035) * mask
        side *= 1.0 - step / wide
    return Vector((side, y, xm - HALF))


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        # per point: (uv, uv2)
        self.data = []
        # per face: the way it should face
        self.out = []
        self.count = {}

    def add(self, p, uv, part, high=0.0):
        self.verts.append(p)
        self.data.append(((uv[0], 1.0 - uv[1]), (high, 1.0 - part)))
        return len(self.verts) - 1

    def face(self, points, out, name):
        """A face wound so that its front (the side its points go round anticlockwise) is towards `out`."""
        ps = [self.verts[i] for i in points]
        n = Vector((0.0, 0.0, 0.0))
        for i in range(len(ps)):
            n += ps[i].cross(ps[(i + 1) % len(ps)])
        if n.length < 1e-12:
            return
        if n.dot(out) < 0.0:
            points = tuple(reversed(points))
        self.faces.append(tuple(points))
        self.out.append((Vector(out), name))
        self.count[name] = self.count.get(name, 0) + 1


def rings(low):
    xs = []
    x = BODY_FROM
    for until, step in ((0.20, 0.0035), (0.46, 0.0045), (1.18, 0.011), (BODY_TO, 0.0045)):
        if low:
            step *= 4.0
        n = max(1, round((until - x) / step))
        for i in range(n):
            xs.append(x + (until - x) * i / n)
        x = until
    xs.append(BODY_TO)
    return xs


def body(m, low):
    around = 28 if low else 96
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
    # the tip of the snout and the end inside the tail: a fan each
    for row, xm, way in ((grid[0], 0.0, -1.0), (grid[-1], BODY_TO + 0.002, 1.0)):
        tip = m.add(Vector((0.0, 0.0, xm - HALF)), (xm / LENGTH, 0.5), BODY)
        for c in range(around):
            m.face((tip, row[c], row[(c + 1) % around]), Vector((0.0, 0.0, way)), "body")


def eye(m, sx, low):
    """A low dome lying on the skin of the head."""
    spokes = 12 if low else 40
    steps = 3 if low else 12
    xe, ye = EYE_AT

    def on_skin(xm, y):
        up, down, _ = outline(xm)
        c = max(-1.0, min(1.0, y / (up if y >= 0.0 else down)))
        return body_point(xm, sx * math.acos(c))

    here = on_skin(xe, ye)
    out = (on_skin(xe + 0.004, ye) - on_skin(xe - 0.004, ye)).cross(on_skin(xe, ye + 0.004) - on_skin(xe, ye - 0.004))
    out.normalize()
    if out.x * sx < 0.0:
        out = -out
    middle = m.add(here + out * 0.0066, (0.0, 0.0), EYE)
    last = None
    for k in range(1, steps + 1):
        r = k / steps
        row = []
        for s in range(spokes):
            a = s / spokes * TAU
            p = on_skin(xe + math.cos(a) * EYE_RADIUS * r, ye + math.sin(a) * EYE_RADIUS * r)
            row.append(m.add(p + out * (0.006 * (1.0 - r * r) + 0.0006 * (1.0 - r)), (r, 0.0), EYE))
        for s in range(spokes):
            n = (s + 1) % spokes
            if last is None:
                m.face((middle, row[s], row[n]), out, "eyes")
            else:
                m.face((last[s], row[s], row[n], last[n]), out, "eyes")
        last = row


def blade(m, part, name, point, place, facing, thick, nt, nu, high=None):
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
                row.append(m.add(p, (t, u), part, high(t, u) if high else 0.0))
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


def fins(m, low):
    d = 3 if low else 1
    # The first dorsal: thirteen spines, the first the tallest, the edge falling away steeply behind and
    # scalloped between the spines; each leans back.
    spines = 13
    lean = math.radians(24.0)

    def dorsal_high(u):
        fall = 0.14 + 0.86 * (1.0 - u) ** 2.3
        scallop = 0.9 + 0.1 * abs(math.cos(math.pi * u * spines))
        return 0.14 * fall * scallop * (0.7 + 0.3 * smooth(0.0, 0.05, u))

    def dorsal_point(t, u):
        xm = 0.47 + 0.325 * u
        high = dorsal_high(u) * t
        return (xm + math.sin(lean) * high, top(xm) - 0.012 + math.cos(lean) * high * 1.0 + 0.012 * t)

    blade(m, DORSAL, "first dorsal", dorsal_point, upright, SIDE, 0.007, 12 // d, (spines * 6) // d,
          high=lambda t, u: (dorsal_high(u) * math.cos(lean) + 0.012) * t)
    # The second dorsal and the anal fin: long sickles, narrow at the root and strongly arched: up and then far
    # back in a curve (the user, 2026-11-17: "The tunas yellow fins should be skinnier abd more arched").
    yd = top(0.85)
    tip = (1.21, yd + 0.33)
    blade(m, SICKLE, "second dorsal", swept(((0.80, top(0.80) - 0.014), (0.83, yd + 0.4), tip),
                                              ((0.862, top(0.862) - 0.014), (0.9, yd + 0.29), tip)),
          upright, SIDE, 0.011, 42 // d, 12 // d)
    ya = bottom(0.93)
    tip = (1.29, ya - 0.32)
    blade(m, SICKLE, "anal", swept(((0.885, bottom(0.885) + 0.014), (0.915, ya - 0.4), tip),
                                    ((0.947, bottom(0.947) + 0.014), (0.985, ya - 0.29), tip)),
          upright, SIDE, 0.011, 42 // d, 12 // d)
    # The finlets: nine above, eight below, smaller towards the tail.
    for way, first, count in ((1.0, 0.927, 9), (-1.0, 1.008, 8)):
        for k in range(count):
            share = k / (count - 1)
            x0 = first + (1.272 - first) * share
            chord = 0.03 - 0.01 * share
            high = (0.032 - 0.014 * share) * way
            y0 = (top(x0) if way > 0.0 else bottom(x0)) - 0.004 * way
            y1 = (top(x0 + chord) if way > 0.0 else bottom(x0 + chord)) - 0.004 * way
            tip = (x0 + chord * 1.55, y1 + high)
            blade(m, FINLET, "finlets", swept(((x0, y0), (x0 + chord * 0.6, y0 + high * 0.7), tip),
                                               ((x0 + chord, y1), (x0 + chord * 1.3, y1 + high * 0.25), tip), 0.97),
                  upright, SIDE, 0.0022, 8 // min(d, 2), 5 // min(d, 2))
    # The tail: a tall stiff crescent, two lobes that meet along the middle line.
    for way in (1.0, -1.0):
        tip = (1.5, 0.232 * way)
        blade(m, TAIL, "tail", swept(((1.28, 0.0), (1.36, 0.125 * way), tip),
                                      ((1.395, 0.0), (1.458, 0.082 * way), tip)),
              upright, SIDE, 0.017, 40 // d, 14 // d)
    for sx in (1.0, -1.0):
        # The pectoral fins: long scythes held out like wings, swept back and a little down.
        up, down, wide = outline(0.40)
        root = Vector((sx * (wide - 0.034), -0.03, 0.385 - HALF))
        sweep = math.radians(34.0)
        span = Vector((sx * math.sin(sweep), -0.2, math.cos(sweep))).normalized()
        chord = Vector((0.0, -0.8, 1.0)).normalized()
        facing = span.cross(chord).normalized()
        if facing.y < 0.0:
            facing = -facing

        def pectoral_point(t, u):
            t *= 0.985
            lead = 0.07 * t * t
            wide_here = 0.072 * (1.0 - t) ** 0.75 * (1.0 + 0.5 * t) + 0.004
            return (0.41 * t, lead + wide_here * u)

        blade(m, PECTORAL, "pectorals", pectoral_point,
              lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.012, 40 // d, 12 // d)
        # The pelvic fins: small, under the pectorals, pointing back and down.
        root = Vector((sx * 0.032, bottom(0.455) + 0.014, 0.455 - HALF))
        span = Vector((sx * 0.3, -0.5, 0.82)).normalized()
        chord = Vector((0.0, 0.12, 1.0)).normalized()
        facing = span.cross(chord).normalized()
        if facing.x * sx < 0.0:
            facing = -facing

        def pelvic_point(t, u):
            t *= 0.97
            return (0.115 * t, 0.02 * t * t + (0.042 * (1.0 - t) ** 0.8 + 0.003) * u)

        blade(m, PELVIC, "pelvics", pelvic_point,
              lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.007, 14 // d, 8 // d)


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
    material = bpy.data.materials.get("tuna") or bpy.data.materials.new("tuna")
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.45, 0.55, 0.7, 1.0)
    material.diffuse_color = (0.45, 0.55, 0.7, 1.0)
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
    """Nothing inside out: the skin of the body faces away from its middle line, each skin of a fin away
    from the fin's own flat, an eye out from the head (Blender's front is the side a face's normal is on)."""
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
    # (Blender space: the fish lies along Y, its nose at +Y, up is Z)
    views = [("left", (1, 0, 0), (0, 0, 0), 1.7), ("right", (-1, 0, 0), (0, 0, 0), 1.7),
             ("front", (0, 1, 0), (0, 0, 0), 1.1), ("back", (0, -1, 0), (0, 0, 0), 1.1),
             ("top", (0.001, 0, 1), (0, 0, 0), 1.7), ("under", (0.001, 0, -1), (0, 0, 0), 1.7),
             ("head", (0.8, 0.5, 0.2), (0, 0.5, 0), 0.6), ("tail", (0.7, -0.6, 0.3), (0, -0.55, 0), 0.7)]
    for low, obj in ((False, made[0]), (True, made[1])):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if low and view not in ("left", "head"):
                continue
            offset = Vector(direction).normalized() * 40.0
            camera.data.ortho_scale = frame
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % ("lo_" if low else "", view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    full = make("yellowfin_tuna", False)
    low = make("yellowfin_tuna_lo", True)
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, "yellowfin_tuna.glb"))
    export_one(low, os.path.join(OUT, "yellowfin_tuna_lo.glb"))
    low.location.x = 1.5
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "yellowfin_tuna.blend"))
    low.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low])


if __name__ == "__main__":
    main()
