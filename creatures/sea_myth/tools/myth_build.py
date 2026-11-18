"""Helpers shared by the build scripts of the sea's mythical creatures (creatures/mermaid, creatures/hippocampus,
creatures/deep_spawn), which all wear one shader, creatures/sea_myth/sea_myth.gdshader. Not run by itself: each
build script puts this folder on its path and imports it.

The same file is in each of those three GameCommon components (godot/mermaid, godot/hippocampus, godot/deep-spawn),
at the same path: change one, copy it to the others (kit.sh install reports a difference if they drift).

Everything here is in Godot space (metres, Y up, X its right, its nose at -Z) until a mesh is written out.

What a point tells the shader (sea_myth.gdshader reads exactly these):
- UV2.y the part: BODY 0 (skin: only the body's wave moves it), JAW 1 (turns down about the jaw's hinge with
  `gape`), LIMB 2 (an arm or a foreleg: swings about its shoulder and bends at its elbow or knee; which side by
  the sign of x), STRAND 3 (hair, a mane, weed: sways, more towards its tip), TENTACLE 4 (writhes, and spreads out
  from the mouth with `gape`), FIN_V 5 (an upright fin: ripples from side to side), FIN_H 6 (a flat fin: ripples
  up and down), EYE 7 (glossy), KELPIE 8 (weed drawn only in the kelpie's look: otherwise folded away to nothing).
- UV2.x how far out along its part (0 its root, 1 its tip), on limbs, strands, tentacles and fins.
- UV: a pattern place, by part: on a body's skin (x metres along, y round it: 0 the ridge of the back, 0.25 its
  right side, 0.5 its belly, 0.75 its left side); on a fin (x from its leading edge 0 to its trailing edge 1,
  y from its root 0 to its edge 1); on a strand or tentacle (x along it, y a number of its own, 0..1).
- COLOR.rgb its colour (linear), COLOR.a where the shader draws its pattern (scales, or lights: each creature's
  settings say which).
(The glTF writer flips V: what is stored here is 1 - v, so that Godot reads v.)
"""

import math
import os

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector

TAU = math.tau
PI = math.pi
BODY, JAW, LIMB, STRAND, TENTACLE, FIN_V, FIN_H, EYE, KELPIE = range(9)


def V(x, y, z):
    return Vector((x, y, z))


def to_b(p):
    return Vector((p.x, -p.z, p.y))


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def smooth(a, b, x):
    t = clamp((x - a) / (b - a))
    return t * t * (3.0 - 2.0 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def lin(c):
    """An sRGB colour (0..1) as linear, which is what a vertex colour holds."""
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c)


def mixc(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def hash1(x):
    s = math.sin(x * 127.1 + 311.7) * 43758.5453
    return s - math.floor(s)


def spread(n, gather=None):
    """n + 1 values from 0 to 1, gathered where `gather` (a function of t, more is denser) asks."""
    if n <= 0:
        return [0.0]
    if gather is None:
        return [i / n for i in range(n + 1)]
    steps = 400
    acc = [0.0]
    for i in range(steps):
        t = (i + 0.5) / steps
        acc.append(acc[-1] + gather(t))
    total = acc[-1]
    out = []
    j = 0
    for k in range(n + 1):
        goal = total * k / n
        while j < steps and acc[j + 1] < goal:
            j += 1
        if j >= steps:
            out.append(1.0)
            continue
        f = (goal - acc[j]) / max(acc[j + 1] - acc[j], 1e-12)
        out.append((j + f) / steps)
    out[0] = 0.0
    out[-1] = 1.0
    return out


class Mesh:
    """Points, faces and what each point tells the shader; every face wound to face the way it is told."""

    def __init__(self):
        self.verts = []
        self.data = []
        self.faces = []
        self.out = []
        self.count = {}

    def add(self, p, uv=(0.0, 0.0), w=0.0, part=BODY, col=(1.0, 1.0, 1.0), mask=0.0):
        self.verts.append(Vector(p))
        self.data.append(((uv[0], 1.0 - uv[1]), (w, 1.0 - part), (col[0], col[1], col[2], mask)))
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

    def centre(self, points):
        c = Vector((0.0, 0.0, 0.0))
        for i in points:
            c += self.verts[i]
        return c / len(points)


# ---------------------------------------------------------------------------------------------------------------
# Curves and frames


def catmull(ctrl, t):
    """A point on a Catmull-Rom curve through `ctrl` (Vectors), t 0..1 over all of it (by span, not length)."""
    n = len(ctrl) - 1
    x = clamp(t) * n
    i = min(int(x), n - 1)
    f = x - i
    p0 = ctrl[max(i - 1, 0)]
    p1 = ctrl[i]
    p2 = ctrl[i + 1]
    p3 = ctrl[min(i + 2, n)]
    f2 = f * f
    f3 = f2 * f
    return 0.5 * ((2.0 * p1) + (-p0 + p2) * f + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * f2
                  + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * f3)


class Curve:
    """A smooth curve through control points, walked by the fraction of its length."""

    def __init__(self, ctrl, samples=600):
        self.ctrl = [Vector(c) for c in ctrl]
        self.pts = [catmull(self.ctrl, i / samples) for i in range(samples + 1)]
        self.acc = [0.0]
        for i in range(samples):
            self.acc.append(self.acc[-1] + (self.pts[i + 1] - self.pts[i]).length)
        self.length = self.acc[-1]

    def at(self, s):
        goal = clamp(s) * self.length
        lo, hi = 0, len(self.acc) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if self.acc[mid] < goal:
                lo = mid
            else:
                hi = mid
        seg = max(self.acc[hi] - self.acc[lo], 1e-12)
        return self.pts[lo].lerp(self.pts[hi], (goal - self.acc[lo]) / seg)

    def param(self, s):
        """Which control point (a float: 1.5 half way from the second to the third) the fraction s of the
        curve's length is at."""
        goal = clamp(s) * self.length
        lo, hi = 0, len(self.acc) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if self.acc[mid] < goal:
                lo = mid
            else:
                hi = mid
        seg = max(self.acc[hi] - self.acc[lo], 1e-12)
        f = (lo + (goal - self.acc[lo]) / seg) / (len(self.acc) - 1)
        return f * (len(self.ctrl) - 1)

    def tangent(self, s):
        e = 0.002
        d = self.at(min(s + e, 1.0)) - self.at(max(s - e, 0.0))
        return d.normalized()


def frames(points, up_hint):
    """Parallel-transported frames along a polyline: (tangent, side, up) at each point."""
    out = []
    n = len(points)
    tangents = []
    for i in range(n):
        a = points[max(i - 1, 0)]
        b = points[min(i + 1, n - 1)]
        tangents.append((b - a).normalized())
    t0 = tangents[0]
    up = (up_hint - t0 * up_hint.dot(t0))
    if up.length < 1e-6:
        up = Vector((1.0, 0.0, 0.0)) - t0 * t0.x
    up.normalize()
    for i in range(n):
        t = tangents[i]
        if i > 0:
            q = tangents[i - 1].rotation_difference(t)
            up = q @ up
            up = (up - t * up.dot(t)).normalized()
        side = t.cross(up).normalized()
        out.append((t, side, up))
    return out


# ---------------------------------------------------------------------------------------------------------------
# Shapes


def section_point(c, ex, ey, a, bu, bd, n, theta, bump=1.0):
    """A point round a cross-section: theta 0 at +ey (its top), TAU/4 at +ex; a superellipse of half-width a,
    half-heights bu above and bd below, exponent n (2 an ellipse, more squarer), its radius times `bump`."""
    s = math.sin(theta)
    co = math.cos(theta)
    x = a * math.copysign(abs(s) ** (2.0 / n), s)
    b = bu if co >= 0.0 else bd
    y = b * math.copysign(abs(co) ** (2.0 / n), co)
    return c + (ex * x + ey * y) * bump


def loft(m, rings, name, close=True, cap0=None, cap1=None, centres=None, axes=None):
    """Faces between rings of point indices (each the same count; closed round unless `close` is False).
    `centres`: each ring's middle (for which way is out; worked out if left out). cap0/cap1: (tip index, which
    way is out) to close an end with a fan to that point."""
    if centres is None:
        centres = [m.centre(r) for r in rings]
    cols = len(rings[0])
    span = cols if close else cols - 1
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        mid = (centres[i] + centres[i + 1]) * 0.5
        for j in range(span):
            k = (j + 1) % cols
            quad = (a[j], a[k], b[k], b[j])
            out = m.centre(quad) - mid
            m.face(quad, out, name)
    for cap, ring, centre in ((cap0, rings[0], centres[0]), (cap1, rings[-1], centres[-1])):
        if cap is None:
            continue
        tip, way = cap
        for j in range(span):
            k = (j + 1) % cols
            tri = (ring[j], ring[k], tip)
            out = (m.centre(tri) - centre) + way * 0.05
            m.face(tri, out, name)


def tube(m, pts, size, sides, attr, name, up_hint=Vector((0.0, 1.0, 0.0)), cap_end=True, cap_start=False,
         theta0=0.0, ex_scale=None):
    """A tube along a polyline `pts`. size(t) -> (half-width, half-height) across it (t 0..1 along, by point),
    attr(t, theta) -> keyword arguments for Mesh.add. Ends closed to a point if asked. Returns its rings."""
    fr = frames(pts, up_hint)
    rings = []
    n = len(pts)
    for i, p in enumerate(pts):
        t = i / (n - 1)
        tan, side, up = fr[i]
        a, b = size(t)
        ring = []
        for j in range(sides):
            th = theta0 + TAU * j / sides
            q = section_point(p, side, up, a, b, b, 2.0, th)
            ring.append(m.add(q, **attr(t, th / TAU)))
        rings.append(ring)
    cap0 = cap1 = None
    if cap_end:
        tip = pts[-1] + fr[-1][0] * size(1.0)[0] * 0.6
        cap1 = (m.add(tip, **attr(1.0, 0.0)), fr[-1][0])
    if cap_start:
        tip = pts[0] - fr[0][0] * size(0.0)[0] * 0.6
        cap0 = (m.add(tip, **attr(0.0, 0.0)), -fr[0][0])
    loft(m, rings, name, cap0=cap0, cap1=cap1, centres=list(pts))
    return rings


def blade(m, point, normal, thick, ts, us, attr, name):
    """A thin closed blade (a fin, a web, a leaf): its middle surface point(t, u), the way its top skin faces
    normal(t, u), half its thickness thick(t, u) (0 at its edges: the two skins meet there and are joined).
    attr(t, u) -> keyword arguments for Mesh.add. t and u are lists of values 0..1."""
    def true_normal(t, u):
        # (the middle surface's own normal, turned to agree with the one asked for; that one where the
        # surface has no width to tell)
        e = 1e-3
        dt = point(min(t + e, 1.0), u) - point(max(t - e, 0.0), u)
        du = point(t, min(u + e, 1.0)) - point(t, max(u - e, 0.0))
        n = dt.cross(du)
        hint = normal(t, u)
        if n.length < 1e-9:
            return hint
        n.normalize()
        return n if n.dot(hint) >= 0.0 else -n

    for sign in (1.0, -1.0):
        grid = []
        for t in ts:
            row = []
            for u in us:
                n = true_normal(t, u)
                row.append(m.add(point(t, u) + n * thick(t, u) * sign, **attr(t, u)))
            grid.append(row)
        for i in range(len(ts) - 1):
            for j in range(len(us) - 1):
                quad = (grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j])
                tm = (ts[i] + ts[i + 1]) * 0.5
                um = (us[j] + us[j + 1]) * 0.5
                m.face(quad, true_normal(tm, um) * sign, name)


def dome(m, centre, normal, radius, height, spokes, rings, attr, name, squash=1.0, up=Vector((0.0, 1.0, 0.0))):
    """A dome standing out of a skin (an eye, a shell): rim on the skin at `centre`, rising `height` along
    `normal`. attr(r) -> keyword arguments for Mesh.add, r 0 the middle to 1 the rim."""
    nz = normal.normalized()
    ex = up.cross(nz)
    if ex.length < 1e-6:
        ex = Vector((1.0, 0.0, 0.0)).cross(nz)
    ex.normalize()
    ey = nz.cross(ex).normalized()
    top = m.add(centre + nz * height, **attr(0.0))
    prev = None
    for k in range(1, rings + 1):
        r = k / rings
        ang = r * PI * 0.5
        ring = []
        for j in range(spokes):
            a = TAU * j / spokes
            off = (ex * math.cos(a) + ey * math.sin(a) * squash) * radius * math.sin(ang)
            ring.append(m.add(centre + off + nz * height * math.cos(ang), **attr(r)))
        if prev is None:
            for j in range(spokes):
                tri = (top, ring[j], ring[(j + 1) % spokes])
                m.face(tri, nz + (m.centre(tri) - centre).normalized() * 0.2, name)
        else:
            for j in range(spokes):
                quad = (prev[j], prev[(j + 1) % spokes], ring[(j + 1) % spokes], ring[j])
                m.face(quad, (m.centre(quad) - (centre - nz * radius)), name)
        prev = ring
    return prev


def blob(m, centre, basis, radius, lats, lons, attr, name):
    """A closed rounded shape (a head): basis is a Matrix whose columns are its own x, y (up) and z (back);
    radius(d) its radius along its own unit direction d; lats from +1 (its top) to -1 (its bottom) as sines,
    lons round it (radians; 0 its back, PI its front at its -z). attr(d) -> keyword arguments for Mesh.add."""
    rows = []
    for s in lats[1:-1]:
        c = math.sqrt(max(1.0 - s * s, 0.0))
        row = []
        for lo in lons:
            d = Vector((c * math.sin(lo), s, c * math.cos(lo)))
            row.append(m.add(centre + basis @ (d * radius(d)), **attr(d)))
        rows.append(row)
    top_d = Vector((0.0, 1.0, 0.0))
    bot_d = Vector((0.0, -1.0, 0.0))
    top = m.add(centre + basis @ (top_d * radius(top_d)), **attr(top_d))
    bot = m.add(centre + basis @ (bot_d * radius(bot_d)), **attr(bot_d))
    centres = [centre] * len(rows)
    loft(m, rows, name, cap0=(top, basis @ top_d), cap1=(bot, basis @ bot_d), centres=centres)
    return rows


# ---------------------------------------------------------------------------------------------------------------
# Writing it out, checking it, pictures


def make(m, name, material_rgb=(0.5, 0.55, 0.5)):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) for p in m.verts], [], m.faces)
    mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.new(name="UV2")
    mesh.color_attributes.new(name="Col", type="FLOAT_COLOR", domain="CORNER")
    uv = mesh.uv_layers["UVMap"].data
    uv2 = mesh.uv_layers["UV2"].data
    col = mesh.color_attributes["Col"].data
    for poly in mesh.polygons:
        for corner, vi in enumerate(poly.vertices):
            d = m.data[vi]
            li = poly.loop_start + corner
            uv[li].uv = d[0]
            uv2[li].uv = d[1]
            col[li].color = d[2]
    mesh.color_attributes.active_color = mesh.color_attributes["Col"]
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.diffuse_color = (*material_rgb, 1.0)
    mesh.materials.append(material)
    mesh.update()
    winding(name, mesh, m)
    # Points in the same place become one (a blade's two skins along its edges), so the skin shades smoothly
    # across them; a sharp fold is then marked sharp.
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.set_sharp_from_angle(angle=math.radians(60.0))
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    print("BUILT %s verts=%d tris=%d" % (name, len(mesh.vertices), tris))
    return obj


def winding(name, mesh, m):
    """Nothing inside out: every face's normal on the side it was told to face (Blender's front is the side a
    face's normal is on; glTF and Godot keep that side the front)."""
    bad = {}
    for poly in mesh.polygons:
        out, group = m.out[poly.index]
        if poly.normal.dot(to_b(out)) <= 0.0:
            bad[group] = bad.get(group, 0) + 1
    told = ["%s %d/%d wrong" % (group, bad.get(group, 0), count) for group, count in sorted(m.count.items())]
    print("WINDING %s: %s: %s" % (name, "ok" if not bad else "INSIDE OUT", ", ".join(told)))


def export_one(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    kw = dict(filepath=path, export_format="GLB", export_yup=True, use_selection=True, export_animations=False,
              export_texcoords=True, export_normals=True, export_materials="NONE")
    try:
        bpy.ops.export_scene.gltf(export_vertex_color="ACTIVE", **kw)
    except TypeError:
        bpy.ops.export_scene.gltf(export_colors=True, **kw)


def render(folder, made, views, size=(1200, 900)):
    """Pictures of each model (workbench, its vertex colours, back faces culled: an inside-out face shows as a
    hole). views: (name, direction from the target, target, frame width), in Godot space."""
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "VERTEX"
    scene.display.shading.show_cavity = True
    scene.display.shading.show_backface_culling = True
    scene.render.resolution_x, scene.render.resolution_y = size
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.06, 0.08)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    for prefix, obj in made:
        for _, other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            d = to_b(Vector(direction)).normalized()
            offset = d * 100.0
            camera.data.ortho_scale = frame
            camera.location = to_b(Vector(target)) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(d.z) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % (prefix, view))
            bpy.ops.render.render(write_still=True)
