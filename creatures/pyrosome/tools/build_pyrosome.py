"""Builds the pyrosome (creatures/pyrosome) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/pyrosome/tools/build_pyrosome.py
    blender --background --python creatures/pyrosome/tools/build_pyrosome.py -- <preview folder>   # with pictures

Writes creatures/pyrosome/models/pyrosome.glb (the full model, for one seen close), pyrosome_game.glb (the game model:
the triangles spent on the outline, the closed end and the open mouth) and pyrosome_lo.glb (far off), and the
editable creatures/pyrosome/tools/pyrosome.blend (this folder has a .gdignore). Each is one still mesh with one
surface: the shader (pyrosome.gdshader) draws its thousands of members and their lights, sways it like a windsock and
runs waves of light along it. It prints a WINDING line for each: the check that nothing is inside out.

A pyrosome (a colony of thousands of tiny tunicates in one tube; the giant kind, as Pyrostremma spinosum), 2 m long,
built from what these look like (no picture was traced or copied):

- THE TUBE: hollow, closed at one end (rounded) and open at the other, a little wider towards the open end; its
  wall about 25 mm thick. At the open end a diaphragm, a ring of tunic, narrows the opening.
- THE MEMBERS: each a tiny zooid set in the wall, its feeding end a bump on the outside. In the full model the
  tunic stands up in low rounded lumps (1,400 of them); the thousands of zooids themselves, each with its opening
  and its pair of light organs, are drawn by the shader on all three models.

IT SWIMS CLOSED END FIRST, as pyrosomes do (water is drawn in through the wall and jetted out of the open end): the
closed end is ahead (-Z), the open end behind (+Z). Its origin is on its middle line half way along its length: the
closed end 1 m ahead, the open end's lip 1 m behind.

What a point is, for the shader: UV2.y the part (0 the outer wall, 1 the open end's lip and diaphragm, 2 the inner
wall). UV.y how far along it is (0 the closed end .. 1 the open end), UV.x round it (0..1). (The glTF writer flips V:
what is written here is 1 - v, so that Godot reads v.)
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

LENGTH = 2.0
TAU = math.tau
OUTER, LIP, INNER = 0, 1, 2

# The tube's path seen in a cut along its length: (z, radius, part), from the tip of the closed end along the outer
# wall to the open end, round the lip and the diaphragm, and back down the inside to the inner tip.
PATH = [
    (-1.0, 0.0, OUTER), (-0.996, 0.03, OUTER), (-0.984, 0.058, OUTER), (-0.962, 0.083, OUTER), (-0.93, 0.103, OUTER),
    (-0.88, 0.118, OUTER), (-0.75, 0.13, OUTER), (-0.4, 0.142, OUTER), (0.0, 0.152, OUTER), (0.4, 0.161, OUTER),
    (0.75, 0.168, OUTER), (0.94, 0.171, OUTER),
    (0.985, 0.17, LIP), (1.0, 0.163, LIP), (1.003, 0.15, LIP), (0.998, 0.13, LIP), (0.99, 0.118, LIP),
    (0.978, 0.116, LIP), (0.97, 0.124, LIP), (0.958, 0.142, INNER),
    (0.9, 0.146, INNER), (0.6, 0.142, INNER), (0.2, 0.133, INNER), (-0.3, 0.12, INNER), (-0.7, 0.106, INNER),
    (-0.86, 0.093, INNER), (-0.92, 0.076, INNER), (-0.952, 0.05, INNER), (-0.966, 0.022, INNER), (-0.97, 0.0, INNER),
]
# The full model's lumps of tunic: how many round it and along it, how high.
LUMPS_AROUND = 32
LUMPS_ALONG = 44
LUMP_HIGH = 0.005

GAME = "game"


def pick(low, full, game, lo):
    return game if low is GAME else (lo if low else full)


def to_b(p):
    return Vector((p.x, -p.z, p.y))


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


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
            q = tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                             + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1))
            # (the part: the nearer end's)
            out.append((q[0], max(q[1], 0.0), p1[2] if t < 0.5 else p2[2]))
    out.append(points[-1])
    return out


_DENSE = _catmull(PATH, 40)
_ALONG = [0.0]
for _i in range(1, len(_DENSE)):
    _ALONG.append(_ALONG[-1] + math.dist(_DENSE[_i][:2], _DENSE[_i - 1][:2]))


def _turning(i):
    """How sharply the path turns at dense point `i` (radians a metre)."""
    if i == 0 or i == len(_DENSE) - 1:
        return 0.0
    a = _DENSE[i - 1]
    b = _DENSE[i]
    c = _DENSE[i + 1]
    t1 = math.atan2(b[1] - a[1], b[0] - a[0])
    t2 = math.atan2(c[1] - b[1], c[0] - b[0])
    d = (t2 - t1 + math.pi) % TAU - math.pi
    return abs(d) / max(0.5 * (math.dist(a[:2], b[:2]) + math.dist(b[:2], c[:2])), 1e-9)


def path_samples(low):
    """Where the rings go along the path: by length, crowded where the path turns (the closed end, the lip) in the
    game and low models; evenly in the full one (and closer at the ends)."""
    n = pick(low, 260, 66, 18)
    bend = pick(low, 0.08, 0.2, 0.3)
    # (the inside is seen only through the open end: fewer rings down it)
    inside = pick(low, 0.6, 0.35, 0.4)
    measure = [0.0]
    for i in range(1, len(_DENSE)):
        step = _ALONG[i] - _ALONG[i - 1]
        weight = inside if _DENSE[i][2] == INNER and _DENSE[i][0] < 0.9 else 1.0
        measure.append(measure[-1] + step * weight * (1.0 + bend * _turning(i)))
    out = []
    j = 0
    for k in range(n + 1):
        want = measure[-1] * k / n
        while j < len(measure) - 2 and measure[j + 1] < want:
            j += 1
        t = (want - measure[j]) / max(measure[j + 1] - measure[j], 1e-12)
        a = _DENSE[j]
        b = _DENSE[j + 1]
        out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] if t < 0.5 else b[2]))
    # (the part changes where the path's parts meet: keep the lip's points as the lip)
    return out


def lump(a, z):
    """How high the tunic stands at angle `a` round it and `z` along it (0..1), in staggered rows of round lumps."""
    s = (z + 1.0) / 2.0
    row = s * LUMPS_ALONG
    r = math.floor(row)
    col = a / TAU * LUMPS_AROUND + 0.5 * (r % 2)
    fa = col - math.floor(col) - 0.5
    fz = row - r - 0.5
    d = math.sqrt(fa * fa + fz * fz) / 0.5
    return max(0.0, 1.0 - d * d) ** 1.5


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.data = []
        self.hint = []
        self.out = []
        self.count = {}
        self.tris = {}

    def add(self, p, uv, part, hint):
        self.verts.append(p)
        self.data.append(((uv[0], 1.0 - uv[1]), (0.0, 1.0 - part)))
        self.hint.append(hint)
        return len(self.verts) - 1

    def face(self, points, out, name):
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


def tube(m, low):
    samples = path_samples(low)
    # (the inside is seen only through the open end: fewer columns there)
    around = pick(low, 128, 32, 12)
    inner_around = pick(low, 64, 16, 6)
    lumped = low is False
    # (the game and low models stand a little proud, so that their fewer-sided skin straddles the full one's lumps)
    proud = pick(low, 0.0, 0.0022, 0.0035)
    rings = []
    for i, (z, r, part) in enumerate(samples[1:-1]):
        n = around if part != INNER else inner_around
        ring = []
        for c in range(n):
            a = c / n * TAU
            way = Vector((math.sin(a), math.cos(a), 0.0))
            rr = r
            if part == OUTER:
                rr += proud
                if lumped:
                    rr += LUMP_HIGH * lump(a, z) * smooth(-0.97, -0.9, z) * (1.0 - smooth(0.9, 0.95, z))
            elif part == LIP:
                rr += proud * 0.5
            p = Vector((way.x * rr, way.y * rr, z))
            hint = way if part == OUTER else (-way if part == INNER else None)
            if part == LIP:
                # (the lip and diaphragm face along the path's own outward side)
                k = i + 1
                z0, r0, _ = samples[k - 1]
                z1, r1, _ = samples[k + 1]
                hint = way * (z1 - z0) - Vector((0.0, 0.0, 1.0)) * (r1 - r0)
            ring.append(m.add(p, (c / n, (z + 1.0) / 2.0), part, hint))
        rings.append((ring, part))
    tip = m.add(Vector((0.0, 0.0, samples[0][0])), (0.0, 0.0), OUTER, Vector((0.0, 0.0, -1.0)))
    inside_tip = m.add(Vector((0.0, 0.0, samples[-1][0])), (0.0, (samples[-1][0] + 1.0) / 2.0), INNER, Vector((0.0, 0.0, 1.0)))
    names = {OUTER: "outer wall", LIP: "lip and diaphragm", INNER: "inner wall"}
    first = rings[0][0]
    for c in range(len(first)):
        m.face((tip, first[c], first[(c + 1) % len(first)]), Vector((0.0, 0.0, -1.0)), names[OUTER])
    for k in range(len(rings) - 1):
        a, pa = rings[k]
        b, pb = rings[k + 1]
        name = names[pb if pb != OUTER else pa]
        if len(a) == len(b):
            for c in range(len(a)):
                n = (c + 1) % len(a)
                m.face((a[c], a[n], b[n], b[c]), None, name)
        else:
            # (from a ring of many to a ring of fewer: each of the fewer takes a fan of the many)
            many, few = (a, b) if len(a) > len(b) else (b, a)
            per = len(many) // len(few)
            for c in range(len(few)):
                n = (c + 1) % len(few)
                for j in range(per):
                    i0 = c * per + j
                    i1 = (i0 + 1) % len(many)
                    m.face((many[i0], many[i1], few[c]), None, name)
                m.face((many[(c + 1) * per % len(many)], few[n], few[c]), None, name)
    last = rings[-1][0]
    for c in range(len(last)):
        m.face((inside_tip, last[c], last[(c + 1) % len(last)]), Vector((0.0, 0.0, 1.0)), names[INNER])


def material_of(name, colour):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = colour
    material.diffuse_color = colour
    return material


def make(name, low):
    m = Mesh()
    tube(m, low)
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
    mesh.materials.append(material_of("pyrosome", (0.6, 0.8, 0.78, 1.0)))
    for poly in mesh.polygons:
        # (the low model's lip turns in a few sharp steps: flat there, so that no point's normal is the average of
        # faces turned more than a right angle apart)
        poly.use_smooth = not (low is True and m.out[poly.index][1] == "lip and diaphragm")
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
    scene.render.resolution_x, scene.render.resolution_y = 1400, 600
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    views = [("left", (1, 0, 0), (0, 0, 0), 2.2), ("open", (0.25, -1, 0.2), (0, -0.95, 0), 0.5),
             ("closed", (0.25, 1, 0.2), (0, 0.95, 0), 0.5), ("quarter", (0.7, -0.5, 0.4), (0, 0, 0), 2.2)]
    for prefix, obj in (("", made[0]), ("game_", made[1]), ("lo_", made[2])):
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
    full = make("pyrosome", False)
    game = make("pyrosome_game", GAME)
    low = make("pyrosome_lo", True)
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, "pyrosome.glb"))
    export_one(game, os.path.join(OUT, "pyrosome_game.glb"))
    export_one(low, os.path.join(OUT, "pyrosome_lo.glb"))
    game.location.x = 0.5
    low.location.x = 1.0
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "pyrosome.blend"))
    game.location.x = 0.0
    low.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, game, low])


if __name__ == "__main__":
    main()
