"""Builds the clown loach (creatures/clown_loach) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/clown_loach/tools/build_clown_loach.py
    blender --background --python creatures/clown_loach/tools/build_clown_loach.py -- <preview folder>   # with pictures

Writes creatures/clown_loach/models/clown_loach.glb (the full model, for close pictures) and
clown_loach_lo.glb (far off, phones), and the editable creatures/clown_loach/tools/clown_loach.blend (this
folder has a .gdignore). Each model is one still mesh with one surface: the shader (clown_loach.gdshader)
draws every marking and moves it. It prints a WINDING line: the check that nothing is inside out, and a
SHADER line: the numbers the shader must be given.

A clown loach (Chromobotia macracanthus), 0.2 m from the tip of its snout to the tips of its tail, built from
the species and from photographs (the component's README says which; none was traced):

- THE BODY: deep and flat-sided, the back arched, the line of the belly nearly flat; deepest (0.052 m) two
  fifths of the way back; a long pointed snout, the forehead a straight slope up to the back; a deep tail
  wrist. The gill cover, a step; small eyes high on the head, a low dome each.
- THE FINS, each a thin closed blade (two skins that meet at its edges): a dorsal at mid-body, an anal fin, a
  deeply forked tail of two pointed lobes, a pair of pectoral fins low behind the gill covers (the shader
  fans them about their roots) and a pair of pelvic fins under the dorsal.
- THE BARBELS: four pairs round the small mouth under the tip of the snout (two pairs at the snout's tip, a
  pair at the corners of the mouth, a small pair on the chin), each a tapering tube the shader twitches.

Everything here is in Godot space (metres, Y up, X to its left side, its nose at -Z) until it is written out;
the origin is on its middle line (the height of the tip of its snout), half way along (0.1 m behind the tip
of the snout). `xm` below is metres behind the tip of the snout.

What a point is, for the shader: UV2.y the part (0 body, 1 dorsal, 2 anal, 3 the tail, 4 a pectoral fin, 5 a
pelvic fin, 6 an eye, 7 a barbel). UV, on the body: x how far along (0 snout to 1 tail tips), y how high on
its side (1 the ridge of the back, 0 the keel of the belly); on a fin: x from its root (0) to its tip (1), y
from its leading edge (0) to its trailing edge (1); on an eye: x from its middle (0) to its rim (1); on a
barbel: x from its root (0) to its tip (1), y which barbel (its number over 8). (The glTF writer flips V:
what is written here is 1 - v, so that Godot reads v.)

The numbers marked "as the shader has it" are in clown_loach.gdshader too: change one, change the other.
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

LENGTH = 0.2
HALF = 0.1
BODY, DORSAL, ANAL, TAIL, PECTORAL, PELVIC, EYE, BARBEL = range(8)
TAU = math.tau

# The body's outline, in shares of its length: how far behind the snout, half its depth above its middle
# line, half its depth below, half its width.
PROFILE = [
    (0.0, 0.0, 0.0, 0.0),
    (0.004, 0.006, 0.006, 0.006),
    (0.015, 0.016, 0.013, 0.012),
    (0.04, 0.037, 0.026, 0.022),
    (0.08, 0.069, 0.044, 0.034),
    (0.13, 0.104, 0.060, 0.046),
    (0.19, 0.135, 0.072, 0.056),
    (0.26, 0.168, 0.077, 0.063),
    (0.34, 0.190, 0.078, 0.066),
    (0.42, 0.197, 0.078, 0.064),
    (0.50, 0.184, 0.077, 0.058),
    (0.58, 0.150, 0.074, 0.048),
    (0.64, 0.116, 0.069, 0.038),
    (0.69, 0.088, 0.063, 0.027),
    (0.72, 0.074, 0.058, 0.019),
    (0.75, 0.066, 0.055, 0.010),
    (0.78, 0.062, 0.054, 0.004),
    (0.80, 0.020, 0.020, 0.0012),
]
BODY_FROM = 0.0004
BODY_TO = 0.80 * LENGTH

# As the shader has it: the edge of the gill cover, the eye.
EYE_AT = (0.029, 0.0092)
EYE_RADIUS = 0.0038
# As the shader has it (it prints them: SHADER): where a pectoral fin is rooted and the line it fans about.
PECTORAL_XM = 0.049
PECTORAL_ANGLE = math.radians(108.0)


def gill_x(y):
    return 0.047 - 14.0 * (y + 0.002) ** 2


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


_XS = [p[0] * LENGTH for p in PROFILE]
_CURVES = []
for column in (1, 2, 3):
    ys = [p[column] * LENGTH for p in PROFILE]
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
        out.append(max(a + b, 0.00007))
    return out


def top(xm):
    return outline(xm)[0]


def bottom(xm):
    return -outline(xm)[1]


def body_point(xm, angle):
    """A point of the skin: `angle` round the body from the ridge of the back (0) by its left side (a
    quarter turn) to the keel of the belly (half a turn). Flat-sided, and flatter underneath than above."""
    up, down, wide = outline(xm)
    c = math.cos(angle)
    s = math.sin(angle)
    y = c * up if c >= 0.0 else -down * abs(c) ** 0.72
    side = math.copysign(abs(s) ** 0.8, s) * wide
    # the gill cover: it stands a little proud of the body behind its edge
    behind = xm - gill_x(y)
    if behind > 0.0 and wide > 0.002:
        mask = smooth(-0.97, -0.8, c) * (1.0 - smooth(0.5, 0.75, c))
        step = 0.0007 * smooth(0.0, 0.0008, behind) * math.exp(-behind / 0.006) * mask
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

    def add(self, p, uv, part):
        self.verts.append(p)
        self.data.append(((uv[0], 1.0 - uv[1]), (0.0, 1.0 - part)))
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


def rings(low):
    xs = []
    x = BODY_FROM
    for until, step in ((0.03, 0.0008), (0.07, 0.0013), (0.138, 0.002), (BODY_TO, 0.0011)):
        if low:
            step *= 4.0
        n = max(1, round((until - x) / step))
        for i in range(n):
            xs.append(x + (until - x) * i / n)
        x = until
    xs.append(BODY_TO)
    return xs


def body(m, low):
    around = 24 if low else 72
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
    for row, xm, way in ((grid[0], 0.0, -1.0), (grid[-1], BODY_TO + 0.0004, 1.0)):
        tip = m.add(Vector((0.0, 0.0, xm - HALF)), (xm / LENGTH, 0.5), BODY)
        for c in range(around):
            m.face((tip, row[c], row[(c + 1) % around]), Vector((0.0, 0.0, way)), "body")


def eye(m, sx, low):
    """A low dome lying on the skin of the head (above the middle line)."""
    spokes = 12 if low else 32
    steps = 3 if low else 10
    xe, ye = EYE_AT

    def on_skin(xm, y):
        c = max(0.0, min(1.0, y / outline(xm)[0]))
        return body_point(xm, sx * math.acos(c))

    here = on_skin(xe, ye)
    d = 0.0006
    out = (on_skin(xe + d, ye) - on_skin(xe - d, ye)).cross(on_skin(xe, ye + d) - on_skin(xe, ye - d))
    out.normalize()
    if out.x * sx < 0.0:
        out = -out
    middle = m.add(here + out * 0.0013, (0.0, 0.0), EYE)
    last = None
    for k in range(1, steps + 1):
        r = k / steps
        row = []
        for s in range(spokes):
            a = s / spokes * TAU
            p = on_skin(xe + math.cos(a) * EYE_RADIUS * r, ye + math.sin(a) * EYE_RADIUS * r)
            row.append(m.add(p + out * (0.0012 * (1.0 - r * r) + 0.0001 * (1.0 - r)), (r, 0.0), EYE))
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


def rayed(x0, x1, edge, way, high, lean, sink=0.0015):
    """A fin of rays standing on the back (way 1) or hanging from the belly (way -1) from `x0` to `x1`,
    each ray leaning back by `lean`, `high(u)` long."""
    def point(t, u):
        xm = x0 + (x1 - x0) * u
        h = high(u) * t
        return (xm + math.sin(lean) * h, edge(xm) - way * sink + way * math.cos(lean) * h)
    return point


def upright(p):
    """A place in the flat of the middle fins (metres behind the snout, metres up) in the model."""
    return Vector((0.0, p[1], p[0] - HALF))


SIDE = Vector((1.0, 0.0, 0.0))


def paired_fin(xm, angle, bury, span, chord):
    """Where a paired fin is rooted on the left side, the way it reaches and the line of its root (made
    square to its reach)."""
    root = body_point(xm, angle)
    root = Vector((root.x - bury, root.y, root.z))
    span = Vector(span).normalized()
    chord = Vector(chord)
    chord = (chord - span * chord.dot(span)).normalized()
    return root, span, chord


def pectoral_frame():
    return paired_fin(PECTORAL_XM, PECTORAL_ANGLE, 0.0016, (0.52, -0.45, 0.72), (0.1, -0.9, 0.42))


def fins(m, low):
    d = 3 if low else 1
    # The dorsal: at mid-body, its first rays the longest, leaning well back, its margin falling to a short
    # last ray.
    blade(m, DORSAL, "dorsal",
          rayed(0.091, 0.125, top, 1.0, lambda u: 0.025 * (0.25 + 0.75 * smooth(0.0, 0.2, u)) * (1.0 - 0.56 * u ** 1.3), math.radians(36.0)),
          upright, SIDE, 0.0016, 18 // d, 30 // d)
    # The anal fin: small, behind the dorsal, leaning back.
    blade(m, ANAL, "anal",
          rayed(0.121, 0.137, bottom, -1.0, lambda u: 0.019 * (0.3 + 0.7 * smooth(0.0, 0.25, u)) * (1.0 - 0.55 * u ** 1.2), math.radians(40.0)),
          upright, SIDE, 0.0014, 14 // d, 18 // d)
    # The tail: deeply forked, two pointed lobes that meet along the middle line.
    for way in (1.0, -1.0):
        tip = (0.2, 0.031 * way)
        blade(m, TAIL, "tail", swept(((0.146, 0.0), (0.165, 0.031 * way), tip),
                                      ((0.167, 0.0), (0.177, 0.008 * way), tip)),
              upright, SIDE, 0.0024, 36 // d, 14 // d)
    for sx in (1.0, -1.0):
        # The pectoral fins: rounded paddles low behind the gill covers, held out and back.
        root, span, chord = pectoral_frame()

        def pectoral_point(t, u):
            t *= 0.985
            return (0.024 * (0.62 + 0.38 * math.sin(math.pi * u) ** 0.8) * t, -0.0035 * t + (0.0045 + 0.0095 * t ** 0.8) * u)

        def mirrored(v, sx=sx):
            return Vector((v.x * sx, v.y, v.z))

        blade(m, PECTORAL, "pectorals", pectoral_point,
              lambda p, root=root, span=span, chord=chord: mirrored(root + span * p[0] + chord * p[1]),
              mirrored(span.cross(chord).normalized()), 0.0014, 22 // d, 14 // d)
        # The pelvic fins: under the front of the dorsal, pointing back, down and a little out.
        root, span, chord = paired_fin(0.092, math.radians(152.0), 0.0012, (0.32, -0.5, 0.8), (-0.6, 0.1, 0.8))

        def pelvic_point(t, u):
            t *= 0.985
            return (0.021 * (0.68 + 0.32 * math.sin(math.pi * u) ** 0.8) * t, -0.002 * t + (0.0045 + 0.009 * t ** 0.8) * u)

        blade(m, PELVIC, "pelvics", pelvic_point,
              lambda p, root=root, span=span, chord=chord: mirrored(root + span * p[0] + chord * p[1]),
              mirrored(span.cross(chord).normalized()), 0.0013, 18 // d, 12 // d)


# The barbels: where on the skin each is rooted (metres behind the snout, the angle round the body in
# degrees), the way it points on the left side, how long it is.
BARBELS = [
    (0.0010, 100.0, (0.35, -0.35, -0.85), 0.0062),
    (0.0026, 118.0, (0.75, -0.45, -0.45), 0.0070),
    (0.0075, 138.0, (0.62, -0.7, 0.12), 0.0080),
    (0.0068, 166.0, (0.2, -0.95, -0.1), 0.0035),
]


def barbels(m, low):
    sides = 4 if low else 8
    segs = 3 if low else 10
    ident = 0
    for xm, angle, way, length in BARBELS:
        for sx in (1.0, -1.0):
            root = body_point(xm, math.radians(angle))
            root = Vector((root.x * 0.7 * sx, root.y * 0.8, root.z + 0.0005))
            d = Vector((way[0] * sx, way[1], way[2])).normalized()
            a = d.cross(Vector((0.0, 1.0, 0.0))).normalized()
            b = d.cross(a).normalized()

            def middle(t, root=root, d=d, length=length):
                # (it droops towards its tip)
                return root + d * (length * t) + Vector((0.0, -1.0, 0.0)) * (length * 0.45 * t * t)

            last = None
            for k in range(segs):
                t = k / segs
                r = 0.00055 * (1.0 - 0.65 * t)
                row = [m.add(middle(t) + (a * math.cos(s / sides * TAU) + b * math.sin(s / sides * TAU)) * r,
                             (t, ident / 8.0), BARBEL) for s in range(sides)]
                if last is not None:
                    at = middle(t - 0.5 / segs)
                    for s in range(sides):
                        n = (s + 1) % sides
                        quad = (last[s], last[n], row[n], row[s])
                        mid = sum((m.verts[q] for q in quad), Vector()) * 0.25
                        m.face(quad, mid - at, "barbels")
                last = row
            tip = m.add(middle(1.0), (1.0, ident / 8.0), BARBEL)
            for s in range(sides):
                n = (s + 1) % sides
                mid = (m.verts[last[s]] + m.verts[last[n]] + m.verts[tip]) / 3.0
                m.face((last[s], last[n], tip), mid - middle(1.0 - 0.6 / segs), "barbels")
            ident += 1


def make(name, low):
    m = Mesh()
    body(m, low)
    for sx in (1.0, -1.0):
        eye(m, sx, low)
    fins(m, low)
    barbels(m, low)
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
    material = bpy.data.materials.get("loach") or bpy.data.materials.new("loach")
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.9, 0.42, 0.08, 1.0)
    material.diffuse_color = (0.9, 0.42, 0.08, 1.0)
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
    from the fin's own flat, an eye out from the head, a barbel's skin away from its middle (Blender's
    front is the side a face's normal is on)."""
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
    views = [("left", (1, 0, 0), (0, 0, 0), 0.23), ("right", (-1, 0, 0), (0, 0, 0), 0.23),
             ("front", (0, 1, 0), (0, 0, 0), 0.13), ("back", (0, -1, 0), (0, 0, 0), 0.13),
             ("top", (0.001, 0, 1), (0, 0, 0), 0.23), ("under", (0.001, 0, -1), (0, 0, 0), 0.23),
             ("head", (0.8, 0.5, 0.1), (0, 0.075, 0), 0.07), ("chin", (0.4, 0.6, -0.7), (0, 0.09, 0), 0.05)]
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
    full = make("clown_loach", False)
    low = make("clown_loach_lo", True)
    root, span, chord = pectoral_frame()
    print("SHADER PECTORAL_ROOT vec3(%.5f, %.5f, %.5f) PECTORAL_AXIS vec3(%.4f, %.4f, %.4f)" % (root.x, root.y, root.z, chord.x, chord.y, chord.z))
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, "clown_loach.glb"))
    export_one(low, os.path.join(OUT, "clown_loach_lo.glb"))
    low.location.x = 0.2
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "clown_loach.blend"))
    low.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low])


if __name__ == "__main__":
    main()
