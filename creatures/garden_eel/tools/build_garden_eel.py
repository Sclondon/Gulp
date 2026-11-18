"""Builds the garden eel (creatures/garden_eel) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/garden_eel/tools/build_garden_eel.py
    blender --background --python creatures/garden_eel/tools/build_garden_eel.py -- <preview folder>   # with pictures

Writes creatures/garden_eel/models/garden_eel.glb (the full model, for close looks), garden_eel_lo.glb (far
off) and garden_eel_colony.glb (about 230 triangles: the one GardenEelColony draws hundreds of), and the
editable creatures/garden_eel/tools/garden_eel.blend (this folder has a .gdignore). Each model is one still
mesh with one surface. It prints a WINDING line: the check that nothing is inside out.

A spotted garden eel, 0.4 m long and 1.2 cm thick. THE MODEL STANDS STRAIGHT UP, as if drawn out of its
burrow like a pencil: the shader (garden_eel.gdshaderinc) curls it into its question mark, sways it and slides
it down into the sand. In Godot space (metres, Y up): the tip of its snout at y = 0.3, its tail's tip at
y = -0.1 (a quarter of it never leaves the burrow), its back to +Z and its belly to -Z (so that, bowed
forward, it faces -Z with its back up), the origin at the mouth of its burrow, on the sand. `s` below is
metres from the tip of the snout, along the body.

- THE BODY: a thin round rod, a short blunt head a little thicker than the rest, the lower jaw reaching
  past the upper (the mouth is a groove that climbs towards the front), a tail drawn out to a point.
- A BIG EYE on each side of the head (a low dome); a tiny pectoral fin on each side behind the head.
- The colony model has no tail (it stops just under the sand), no eyes and no fins of its own: the shader
  draws its eyes.

What a point is, for the shader: UV2.y the part (0 body, 1 an eye, 2 a pectoral fin). UV, on the body: x how
far along (0 snout to 1 tail); on an eye: x from its middle (0) to its rim (1); on a fin: x root to tip.
(The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.) The shader finds where a
point of the body is from its place in the still model.

The numbers marked "as the shader has it" are in garden_eel.gdshaderinc too: change one, change the other.
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

LENGTH = 0.4
# As the shader has it: how high the tip of the snout stands in the still model.
TOP = 0.3
BODY, EYE, FIN = range(3)
TAU = math.tau

# The body's outline: metres from the tip of the snout, half its width, how far its back and its belly are
# from its middle line, and how far that middle line is pushed towards the back (+) or the belly (-).
PROFILE = [
    (0.0003, 0.0010, 0.0008, 0.0010, -0.0018),
    (0.002, 0.0030, 0.0024, 0.0028, -0.0010),
    (0.005, 0.0048, 0.0042, 0.0042, -0.0004),
    (0.009, 0.0060, 0.0055, 0.0052, 0.0),
    (0.014, 0.0066, 0.0062, 0.0058, 0.0),
    (0.022, 0.0064, 0.0062, 0.0060, 0.0),
    (0.035, 0.0060, 0.0060, 0.0060, 0.0),
    (0.30, 0.0060, 0.0060, 0.0060, 0.0),
    (0.36, 0.0048, 0.0048, 0.0048, 0.0),
    (0.39, 0.0028, 0.0028, 0.0028, 0.0),
    (0.3995, 0.0006, 0.0006, 0.0006, 0.0),
]
BODY_FROM = PROFILE[0][0]
BODY_TO = PROFILE[-1][0]

# As the shader has it: the line of the mouth, the eye.
MOUTH_TO = 0.0072
EYE_AT = (0.0088, 0.0012)
EYE_RADIUS = 0.0031


def mouth_d(s):
    return -0.0004 - 0.45 * s


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
for column in (1, 2, 3, 4):
    ys = [p[column] for p in PROFILE]
    _CURVES.append((ys, _slopes(_XS, ys)))


def outline(s):
    """(half width, back, belly, middle) at `s`."""
    s = max(_XS[0], min(_XS[-1], s))
    i = 0
    while i < len(_XS) - 2 and s > _XS[i + 1]:
        i += 1
    h = _XS[i + 1] - _XS[i]
    t = (s - _XS[i]) / h
    out = []
    for ys, m in _CURVES:
        a = (2 * t ** 3 - 3 * t ** 2 + 1) * ys[i] + (t ** 3 - 2 * t ** 2 + t) * h * m[i]
        b = (-2 * t ** 3 + 3 * t ** 2) * ys[i + 1] + (t ** 3 - t ** 2) * h * m[i + 1]
        out.append(a + b)
    return out


def body_point(s, angle):
    """A point of the skin: `angle` round the body from the ridge of its back (0) by its left side (a
    quarter turn) to the middle of its belly (half a turn)."""
    wide, back, belly, middle = outline(s)
    c = math.cos(angle)
    sn = math.sin(angle)
    d = middle + c * (back if c >= 0.0 else belly)
    side = sn * wide
    # the mouth: a groove on each side of the head, climbing towards the front
    if s < MOUTH_TO + 0.001:
        groove = math.exp(-((d - mouth_d(s)) / 0.0005) ** 2) * smooth(0.0002, 0.001, s) * (1.0 - smooth(MOUTH_TO - 0.001, MOUTH_TO + 0.0005, s))
        side *= 1.0 - 0.1 * groove
    return Vector((side, TOP - s, d))


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.data = []
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


def rings(kind):
    if kind == "colony":
        # (close together where it curls, and stopping just under the sand)
        return [0.0016, 0.006, 0.014, 0.027, 0.042, 0.058, 0.074, 0.09, 0.108, 0.13, 0.156, 0.188, 0.224, 0.262, 0.304]
    xs = []
    x = BODY_FROM
    for until, step in ((0.012, 0.0005), (0.04, 0.0015), (0.30, 0.003), (BODY_TO, 0.004)):
        if kind == "lo":
            step *= 4.0
        n = max(1, round((until - x) / step))
        for i in range(n):
            xs.append(x + (until - x) * i / n)
        x = until
    xs.append(BODY_TO)
    return xs


def body(m, kind):
    around = {"full": 28, "lo": 10, "colony": 8}[kind]
    grid = []
    ss = rings(kind)
    for s in ss:
        grid.append([m.add(body_point(s, c / around * TAU), (s / LENGTH, c / around), BODY) for c in range(around)])
    for r in range(len(grid) - 1):
        middle_d = outline(0.5 * (ss[r] + ss[r + 1]))[3]
        for c in range(around):
            n = (c + 1) % around
            quad = (grid[r][c], grid[r][n], grid[r + 1][n], grid[r + 1][c])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((middle.x, 0.0, middle.z - middle_d)), "body")
    ends = [(grid[0], 0.0, 1.0)]
    if kind != "colony":
        ends.append((grid[-1], LENGTH, -1.0))
    for row, s, way in ends:
        tip = m.add(Vector((0.0, TOP - s, outline(s)[3])), (s / LENGTH, 0.5), BODY)
        for c in range(around):
            m.face((tip, row[c], row[(c + 1) % around]), Vector((0.0, way, 0.0)), "body")


def on_skin(s, d, sx):
    _, back, belly, middle = outline(s)
    c = max(-1.0, min(1.0, (d - middle) / (back if d >= middle else belly)))
    return body_point(s, sx * math.acos(c))


def eye(m, sx, low):
    """A low dome lying on the skin of the head."""
    spokes = 10 if low else 28
    steps = 2 if low else 8
    se, de = EYE_AT
    here = on_skin(se, de, sx)
    out = Vector((sx, 0.0, 0.12)).normalized()
    middle = m.add(here + out * 0.0011, (0.0, 0.0), EYE)
    last = None
    for k in range(1, steps + 1):
        r = k / steps
        row = []
        for sp in range(spokes):
            a = sp / spokes * TAU
            p = on_skin(se + math.cos(a) * EYE_RADIUS * r, de + math.sin(a) * EYE_RADIUS * r, sx)
            row.append(m.add(p + out * (0.001 * (1.0 - r * r) + 0.0001 * (1.0 - r)), (r, 0.0), EYE))
        for sp in range(spokes):
            n = (sp + 1) % spokes
            if last is None:
                m.face((middle, row[sp], row[n]), out, "eyes")
            else:
                m.face((last[sp], row[sp], row[n], last[n]), out, "eyes")
        last = row


def fin(m, sx, low):
    """A pectoral fin: a tiny thin closed blade (two skins that meet at its edges), held out and back."""
    nt = 2 if low else 6
    nu = 2 if low else 5
    root = Vector((sx * 0.0052, TOP - 0.036, -0.001))
    span = Vector((sx * 0.75, -0.6, -0.1)).normalized()
    chord = Vector((0.0, -0.3, -1.0)).normalized()
    facing = span.cross(chord).normalized()
    for side in (1.0, -1.0):
        grid = []
        for ti in range(nt + 1):
            t = ti / nt * 0.97
            row = []
            for ui in range(nu + 1):
                u = ui / nu
                wide = 0.0034 * (1.0 - t) ** 0.6 * (0.6 + 0.4 * math.sin(math.pi * min(1.0, t + 0.5)))
                foil = 2.6 * math.sqrt(u) * (1.0 - u)
                p = root + span * (0.0065 * t) + chord * (wide * (u - 0.5)) + facing * (side * 0.0005 * (1.0 - t) * foil)
                row.append(m.add(p, (t, u), FIN))
            grid.append(row)
        for ti in range(nt):
            for ui in range(nu):
                m.face((grid[ti][ui], grid[ti][ui + 1], grid[ti + 1][ui + 1], grid[ti + 1][ui]), facing * side, "fins")


def make(name, kind):
    m = Mesh()
    body(m, kind)
    if kind != "colony":
        for sx in (1.0, -1.0):
            eye(m, sx, kind == "lo")
            fin(m, sx, kind == "lo")
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
    material = bpy.data.materials.get("garden_eel") or bpy.data.materials.new("garden_eel")
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.8, 0.78, 0.7, 1.0)
    material.diffuse_color = (0.8, 0.78, 0.7, 1.0)
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
    # (Blender space: it stands along Z, its back to -Y, its belly to +Y)
    top = (0, 0, 0.285)
    views = [("head_left", (1, 0, 0), top, 0.06), ("head_right", (-1, 0, 0), top, 0.06),
             ("head_belly", (0, 1, 0), top, 0.06), ("head_back", (0, -1, 0), top, 0.06),
             ("head_above", (0.001, 0, 1), top, 0.04), ("head_quarter", (0.7, 0.6, 0.3), top, 0.05),
             ("whole_left", (1, 0, 0), (0, 0, 0.1), 0.75)]
    for kind, obj in zip(("", "lo_", "colony_"), made):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if kind and view not in ("head_left", "whole_left"):
                continue
            offset = Vector(direction).normalized() * 40.0
            camera.data.ortho_scale = frame
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Z" if abs(direction[2]) < 0.9 else "Y").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % (kind, view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    made = [make("garden_eel", "full"), make("garden_eel_lo", "lo"), make("garden_eel_colony", "colony")]
    os.makedirs(OUT, exist_ok=True)
    for obj in made:
        export_one(obj, os.path.join(OUT, obj.name + ".glb"))
    made[1].location.x = 0.05
    made[2].location.x = 0.1
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "garden_eel.blend"))
    made[1].location.x = 0.0
    made[2].location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, made)


if __name__ == "__main__":
    main()
