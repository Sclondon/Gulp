"""Builds the dumbo octopus (creatures/dumbo_octopus) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/dumbo_octopus/tools/build_dumbo_octopus.py
    blender --background --python creatures/dumbo_octopus/tools/build_dumbo_octopus.py -- <preview folder>   # with pictures

Writes creatures/dumbo_octopus/models/dumbo_octopus.glb (the full model, for one seen close), dumbo_octopus_game.glb
(the game model: the triangles spent on the outline, the eyes and the web's edge) and dumbo_octopus_lo.glb (far off,
phones), and the editable creatures/dumbo_octopus/tools/dumbo_octopus.blend (this folder has a .gdignore). Each is
one still mesh with one surface: the shader (dumbo_octopus.gdshader) draws every marking, flaps its fins, opens and
closes its web, bends it and makes it glow. It prints a WINDING line for each: the check that nothing is inside out.

A dumbo octopus (Grimpoteuthis), 0.3 m from the top of its mantle to the tips of its arms, built from the genus as
it is described (no picture was traced or copied):

- THE BODY: soft and rounded, a bell: the mantle a dome on top, running down without a neck into the head, widest
  about the eyes; no siphon to speak of.
- THE FINS: two big paddles, one each side of the mantle high up, like ears: a narrow root widening into a rounded
  blade. They flap (the shader turns them about their roots).
- THE ARMS AND WEB: eight short arms joined by a web almost to their tips, like an umbrella hanging from the head:
  one closed thin shell, its outer skin the web's outside, its inner skin the web's underside with the arms standing
  out of it as ridges (suckers and cirri drawn by the shader), the tips of the arms just free of the web's edge, the
  web's edge sagging between them. The shader bends it open and shut along its length (a pulse).
- THE EYES: big, a dome each side of the head, turned a little forward.

IT FLOATS UPRIGHT, FACING -Z: its mantle's top is up (+Y), its face (between the eyes) looks along -Z (Godot's
forward), its fins stand out to the sides (+X its left). Its origin is on its middle line half way along its length:
the top of the mantle 0.15 m above it, the arms' tips 0.15 m below (at rest: the web half open, as built).

What a point is, for the shader: UV2.y the part (0 the body, 1 the web's outside, 2 the web's underside and the
underside of the body, 3 a fin, 4 an eye). UV2.x on the web: how far along it from its root (metres; 0 on the body,
which is never bent). UV on the body and web: x how far along the web (0 at its root and on the body .. 1 at its
edge), y down the outline (0 the top of the mantle .. 1 the mouth); on a fin: x root (0) to tip (1), y leading edge (0) to trailing
edge (1); on an eye: its own plane, x towards the front (-Z side), y up, 1 at its rim. (The glTF writer flips V:
what is written here is 1 - v, so that Godot reads v.)

The numbers marked "as the shader has it" are in dumbo_octopus.gdshader too: change one, change the other.
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

LENGTH = 0.3
TAU = math.tau
BODY, OUTER, INNER, FIN, EYE = range(5)

# The body's outline: (radius, height) from the top of the mantle down to the web's root (the last point, which is
# as the shader has it: R0, Y0).
OUTLINE = [
    (0.0, 0.15), (0.017, 0.1482), (0.032, 0.1425), (0.0445, 0.1325), (0.0545, 0.118), (0.0612, 0.100),
    (0.0652, 0.080), (0.0672, 0.058), (0.0678, 0.036), (0.0676, 0.016), (0.0680, 0.002), (0.0695, -0.010),
]
# As the shader has it: the web's root ring, the angle it leaves it at (radians from straight down, outward), how
# fast it curls outward along its length (radians a metre).
R0, Y0 = 0.0695, -0.010
THETA0 = 0.2
KAPPA = 5.0
# How far the arms reach along the web from its root, and how far the web reaches between them (metres).
ARM_LONG = 0.18
WEB_LONG = 0.128
# The web's thickness, and how much the arms stand out of its underside at their roots.
T_WEB = 0.0018
T_ARM = 0.0085
# Where the arms are round it: radians from the front, the first by the left side.
ARM_ANGLES = [math.pi / 8.0 + k * math.pi / 4.0 for k in range(8)]
# The fins (as the shader has it: their roots): height, how far out the root is, span, chord, lift.
FIN_Y = 0.092
FIN_ROOT_X = 0.043
FIN_SPAN = 0.07
FIN_CHORD = 0.027
FIN_LIFT = math.radians(24.0)
# (and how far its leading edge is tipped up: the fin faces forward a little, as an ear)
FIN_PITCH_S, FIN_PITCH_C = math.sin(math.radians(35.0)), math.cos(math.radians(35.0))
# The eyes (as the shader has it): height, angle round from the front, radius, and how high the dome stands.
EYE_Y = 0.034
EYE_A = 0.62
EYE_R = 0.0165
EYE_H = 0.0055

GAME = "game"


def pick(low, full, game, lo):
    """How finely a part is cut: `low` is False for the full model, True for the low one, GAME for the game model."""
    return game if low is GAME else (lo if low else full)


def to_b(p):
    return Vector((p.x, -p.z, p.y))


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


# --- the body's outline, a curve through OUTLINE, measured along its length ---------------------------------------

def _catmull(points, per):
    out = []
    n = len(points)
    for i in range(n - 1):
        p0 = points[max(i - 1, 0)]
        p1 = points[i]
        p2 = points[i + 1]
        p3 = points[min(i + 2, n - 1)]
        for k in range(per):
            t = k / per
            t2 = t * t
            t3 = t2 * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    out.append(points[-1])
    return out


_DENSE = _catmull(OUTLINE, 60)
_ALONG = [0.0]
for _i in range(1, len(_DENSE)):
    _ALONG.append(_ALONG[-1] + math.dist(_DENSE[_i], _DENSE[_i - 1]))


def outline_at(f):
    """(radius, height) of the body's outline at `f` (0 the top of the mantle .. 1 the web's root), by length."""
    want = max(0.0, min(1.0, f)) * _ALONG[-1]
    i = 1
    while i < len(_ALONG) - 1 and _ALONG[i] < want:
        i += 1
    t = (want - _ALONG[i - 1]) / max(_ALONG[i] - _ALONG[i - 1], 1e-12)
    a = _DENSE[i - 1]
    b = _DENSE[i]
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def radius_at_y(y):
    for i in range(1, len(_DENSE)):
        a = _DENSE[i - 1]
        b = _DENSE[i]
        if (a[1] - y) * (b[1] - y) <= 0.0 and a[1] != b[1]:
            t = (y - a[1]) / (b[1] - a[1])
            return a[0] + (b[0] - a[0]) * t
    return _DENSE[-1][0]


def way_out(a):
    """The way out from the middle line at angle `a` round it (0 the front, -Z; a quarter turn the left, +X)."""
    return Vector((math.sin(a), 0.0, -math.cos(a)))


def widen(a, y):
    """The head is a little wider across (at the eyes) than front to back."""
    return 1.0 + 0.05 * abs(math.sin(a)) * math.exp(-((y - 0.03) / 0.04) ** 2) * smooth(Y0, Y0 + 0.025, y)


def surf(a, y):
    """The point of the body's skin at angle `a` and height `y`."""
    return way_out(a) * (radius_at_y(y) * widen(a, y)) + Vector((0.0, y, 0.0))


# --- the web ------------------------------------------------------------------------------------------------------

def arm_off(a):
    """Radians from `a` to the nearest arm."""
    best = 10.0
    for k in ARM_ANGLES:
        d = (a - k + math.pi) % TAU - math.pi
        if abs(d) < abs(best):
            best = d
    return best


def web_long(a):
    """How far the web reaches from its root at angle `a`: the arms' tips at the arms, the edge sagging between."""
    q = min(abs(arm_off(a)) / (math.pi / 8.0), 1.0)
    edge = WEB_LONG + (0.86 * ARM_LONG - WEB_LONG) * (1.0 - q * q) ** 1.5
    tip = 0.14 * ARM_LONG * math.exp(-(q / 0.16) ** 2)
    return max(edge, edge + tip)


def centre(d):
    """The web's outer skin along its length at `d` metres from its root: (radius, height), and its angle."""
    th = THETA0 + KAPPA * d
    rho = R0 + (math.cos(THETA0) - math.cos(th)) / KAPPA
    y = Y0 - (math.sin(th) - math.sin(THETA0)) / KAPPA
    return rho, y, th


def armness(a, d):
    rho = centre(d)[0]
    width = 0.0085 * (1.0 - 0.5 * d / ARM_LONG)
    return math.exp(-((rho * arm_off(a)) / width) ** 2)


def thickness(a, d):
    s = d / ARM_LONG
    return T_WEB + armness(a, d) * T_ARM * (1.0 - 0.62 * s) + 0.0012 * armness(a, d) * smooth(0.6, 1.0, s)


def web_point(a, d, inner):
    """A point of the web's outside (inner False) or its underside (inner True), and the way it faces."""
    rho, y, th = centre(d)
    e = way_out(a)
    n = e * math.cos(th) + Vector((0.0, math.sin(th), 0.0))
    p = e * rho + Vector((0.0, y, 0.0))
    if inner:
        return p - n * thickness(a, d), -n
    # (the arms show a little as ribs on the outside too)
    return p + n * (0.0012 * armness(a, d) * smooth(0.0, 0.03, d)), n


def tangent(d):
    th = centre(d)[2]
    return th


# --- the mesh -----------------------------------------------------------------------------------------------------

class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.data = []
        self.hint = []
        self.out = []
        self.count = {}
        self.tris = {}

    def add(self, p, uv, part, along=0.0, hint=None):
        self.verts.append(p)
        self.data.append(((uv[0], 1.0 - uv[1]), (along, 1.0 - part)))
        self.hint.append(hint if hint is not None else Vector((0.0, 0.0, 0.0)))
        return len(self.verts) - 1

    def face(self, points, out, name):
        """A face wound so that its front (the side its points go round anticlockwise) is towards `out`."""
        ps = [self.verts[i] for i in points]
        n = Vector((0.0, 0.0, 0.0))
        for i in range(len(ps)):
            n += ps[i].cross(ps[(i + 1) % len(ps)])
        if n.length < 1e-16:
            return
        if out is None:
            out = sum((self.hint[i] for i in points), Vector())
        if n.dot(out) < 0.0:
            points = tuple(reversed(points))
        self.faces.append(tuple(points))
        self.out.append((Vector(out), name))
        self.count[name] = self.count.get(name, 0) + 1
        self.tris[name] = self.tris.get(name, 0) + len(points) - 2


def columns(around):
    """The angles round it: `around` of them, eight sectors (one an arm) each spread from its valley to its valley,
    crowded towards the arm in the middle (where the web's edge turns and the arm's ridge is)."""
    per = around // 8
    out = []
    for k in range(8):
        for i in range(per):
            q = -1.0 + 2.0 * i / per
            w = math.copysign(abs(q) ** 1.45, q)
            out.append(ARM_ANGLES[k] + w * math.pi / 8.0)
    return out


def body_rows(low):
    n = pick(low, 34, 8, 4)
    # (crowded towards the top, where the dome turns in the outline seen from the side and the front)
    return [((i / n) ** 1.15) for i in range(n + 1)]


def web_rows(low):
    n = pick(low, 34, 6, 3)
    return [(i / n) ** 0.85 for i in range(n + 1)]


def inner_rows(low):
    n = pick(low, 26, 4, 2)
    return [(i / n) ** 0.9 for i in range(n + 1)]


def under_rows(low):
    n = pick(low, 8, 2, 1)
    return [i / n for i in range(n + 1)]


def body_and_web(m, low):
    angles = columns(pick(low, 96, 32, 16))
    around = len(angles)
    grid = []
    rows_b = body_rows(low)
    rows_w = web_rows(low)
    rows_i = inner_rows(low)
    rows_u = under_rows(low)
    total = len(rows_b) + len(rows_w) + len(rows_i) + len(rows_u) + 1
    # the top of the mantle: one point
    top = m.add(Vector((0.0, OUTLINE[0][1], 0.0)), (0.0, 0.0), BODY, 0.0, Vector((0.0, 1.0, 0.0)))
    for c, a in enumerate(angles):
        col = []
        row = 0
        u = c / around
        # the body, from just under the top down to the web's root
        for f in rows_b[1:-1]:
            r, y = outline_at(f)
            p = way_out(a) * (r * widen(a, y)) + Vector((0.0, y, 0.0))
            row += 1
            col.append(m.add(p, (0.0, row / total), BODY, 0.0, p - Vector((0.0, 0.05, 0.0))))
        # the web's outside, from its root to its edge
        long = web_long(a)
        for f in rows_w:
            d = f * long
            p, n = web_point(a, d, False)
            row += 1
            col.append(m.add(p, (f, row / total), OUTER if d > 0.0 else BODY, d, n))
        # its edge: rounded over from the outside to the underside
        rho, y, th = centre(long)
        t = thickness(a, long)
        e = way_out(a)
        n = e * math.cos(th) + Vector((0.0, math.sin(th), 0.0))
        along = e * math.sin(th) - Vector((0.0, math.cos(th), 0.0))
        p = e * rho + Vector((0.0, y, 0.0)) - n * (0.5 * t) + along * (0.55 * t)
        row += 1
        col.append(m.add(p, (1.0, row / total), INNER, long, along))
        # the underside, from the edge back to the root
        for f in rows_i:
            d = (1.0 - f) * long
            p, n = web_point(a, d, True)
            row += 1
            col.append(m.add(p, (1.0 - f, row / total), INNER, d, n))
        # the underside of the body, from the root in to the mouth
        root, _ = web_point(a, 0.0, True)
        for f in rows_u[1:]:
            k = f
            mid = Vector((root.x * 0.45, Y0 + 0.022, root.z * 0.45))
            end = Vector((0.0, Y0 + 0.017, 0.0))
            p = root * (1 - k) ** 2 + mid * (2 * k * (1 - k)) + end * (k * k)
            p = Vector((p.x * (1.0 - 0.02 * k), p.y, p.z))
            if f >= 1.0:
                break
            row += 1
            col.append(m.add(p, (0.0, row / total), INNER, 0.0, Vector((-e.x * 0.4, -1.0, -e.z * 0.4))))
        grid.append(col)
    mouth = m.add(Vector((0.0, Y0 + 0.017, 0.0)), (0.0, 1.0), INNER, 0.0, Vector((0.0, -1.0, 0.0)))
    rows = len(grid[0])
    names = {}
    for c in range(around):
        n = (c + 1) % around
        m.face((top, grid[c][0], grid[n][0]), None, "body")
        for r in range(rows - 1):
            quad = (grid[c][r], grid[n][r], grid[n][r + 1], grid[c][r + 1])
            part = round(1.0 - m.data[grid[c][r + 1]][1][1])
            name = ("body", "web outside", "web underside")[min(part, 2)]
            m.face(quad, None, name)
        m.face((mouth, grid[c][-1], grid[n][-1]), None, "web underside")
    return names


def dome(m, part, a0, y0, radius, height, sx, spokes, steps, group):
    """A dome lying on the skin: an eye. Its UV is its own plane: x towards the front, y up, 1 at its rim."""
    a0 = sx * a0
    here = surf(a0, y0)
    r0 = radius_at_y(y0) * widen(a0, y0)
    e = 0.0004
    out = (surf(a0 + e / r0, y0) - surf(a0 - e / r0, y0)).cross(surf(a0, y0 + e) - surf(a0, y0 - e))
    out.normalize()
    if out.dot(way_out(a0)) < 0.0:
        out = -out
    middle = m.add(here + out * height, (0.0, 0.0), part, 0.0, out)
    last = None
    for k in range(1, steps + 1):
        r = k / steps
        row = []
        for s in range(spokes):
            ang = s / spokes * TAU
            # (x towards the front: on the left eye (sx 1) that is round towards a smaller angle)
            qx = math.cos(ang) * r
            qy = math.sin(ang) * r
            da = -sx * qx * radius
            p = surf(a0 + da / r0, y0 + qy * radius)
            lift = height * (1.0 - r * r) + 0.00004 * (1.0 - r)
            row.append(m.add(p + out * lift, (qx, qy), part, 0.0, out))
        for s in range(spokes):
            n = (s + 1) % spokes
            if last is None:
                m.face((middle, row[s], row[n]), out, group)
            else:
                m.face((last[s], row[s], row[n], last[n]), out, group)
        last = row


def eyes(m, low):
    for sx in (1.0, -1.0):
        dome(m, EYE, EYE_A, EYE_Y, EYE_R, EYE_H, sx, pick(low, 40, 32, 10), pick(low, 10, 2, 1), "eyes")


def fin_root(sx):
    p = surf(sx * math.pi / 2.0, FIN_Y)
    return Vector((p.x - sx * 0.003, p.y, p.z))


def fins(m, low):
    nt = pick(low, 16, 4, 2)
    nu = pick(low, 12, 5, 2)
    for sx in (1.0, -1.0):
        root = fin_root(sx)
        span = Vector((sx * math.cos(FIN_LIFT), math.sin(FIN_LIFT), 0.0))
        chord = Vector((0.0, -FIN_PITCH_S, FIN_PITCH_C))
        facing = span.cross(chord).normalized()
        if facing.y < 0.0:
            facing = -facing
        for side in (1.0, -1.0):
            grid = []
            for ti in range(nt + 1):
                t = (ti / nt) ** 0.8 * 0.999
                h = FIN_CHORD * math.sqrt(max(1.0 - t ** 4, 0.0)) * (0.45 + 0.75 * math.sin(math.pi * t * 0.75))
                mid = 0.004 * t + 0.003 * t * t
                row = []
                for ui in range(nu + 1):
                    u = ui / nu
                    w = 0.5 - 0.5 * math.cos(math.pi * u)
                    z = mid + (w * 2.0 - 1.0) * h
                    foil = 2.6 * math.sqrt(w) * (1.0 - w)
                    swell = 0.0032 * math.sqrt(max(1.0 - t * t, 0.0)) * foil * (1.0 - 0.6 * t)
                    p = root + span * (FIN_SPAN * t) + chord * z + facing * (side * swell * 0.5)
                    row.append(m.add(p, (t, w), FIN, 0.0, facing * side))
                grid.append(row)
            for ti in range(nt):
                for ui in range(nu):
                    m.face((grid[ti][ui], grid[ti][ui + 1], grid[ti + 1][ui + 1], grid[ti + 1][ui]), facing * side, "fins")
            # the tip: every point of the last row is one place (the fin closes there); the root is inside the body


def material_of(name, colour):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = colour
    material.diffuse_color = colour
    return material


def make(name, low):
    m = Mesh()
    body_and_web(m, low)
    eyes(m, low)
    fins(m, low)
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
    mesh.materials.append(material_of("dumbo_octopus", (0.95, 0.66, 0.55, 1.0)))
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


def winding(name, mesh, m):
    """Nothing inside out: each face looks the way it was meant to (the body's skin and the web's outside away from
    the inside, the web's underside down and in, a fin's two skins away from its own flat, an eye out from the body)
    (Blender's front is the side a face's normal is on)."""
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
    scene.render.resolution_x, scene.render.resolution_y = 1000, 1000
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    # (Blender space: -Y is its front, Z up)
    views = [("front", (0, 1, 0), 0.42), ("left", (1, 0, 0), 0.42), ("back", (0, -1, 0), 0.42),
             ("top", (0.001, 0, 1), 0.42), ("under", (0.001, 0, -1), 0.42), ("quarter", (0.7, 0.7, 0.35), 0.42),
             ("head", (0.35, 1, 0.15), 0.2)]
    for prefix, obj in (("", made[0]), ("game_", made[1]), ("lo_", made[2])):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, frame in views:
            offset = Vector(direction).normalized() * 40.0
            target = Vector((0.0, 0.0, 0.0)) if view != "head" else Vector((0.0, 0.03, 0.05))
            camera.data.ortho_scale = frame
            camera.location = target + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % (prefix, view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    full = make("dumbo_octopus", False)
    game = make("dumbo_octopus_game", GAME)
    low = make("dumbo_octopus_lo", True)
    root = fin_root(1.0)
    print("FIN root (%.5f, %.5f, %.5f)" % (root.x, root.y, root.z))
    base = surf(EYE_A, EYE_Y)
    print("EYE base (%.5f, %.5f, %.5f)" % (base.x, base.y, base.z))
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, "dumbo_octopus.glb"))
    export_one(game, os.path.join(OUT, "dumbo_octopus_game.glb"))
    export_one(low, os.path.join(OUT, "dumbo_octopus_lo.glb"))
    game.location.x = 0.45
    low.location.x = 0.9
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "dumbo_octopus.blend"))
    game.location.x = 0.0
    low.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, game, low])


if __name__ == "__main__":
    main()
