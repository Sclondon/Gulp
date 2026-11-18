"""Builds the sea sparkle's specks (creatures/sea_sparkle) and exports them for Godot.

Run from the game's root:
    blender --background --python creatures/sea_sparkle/tools/build_sea_sparkle.py
    blender --background --python creatures/sea_sparkle/tools/build_sea_sparkle.py -- <preview folder>   # with pictures

Writes creatures/sea_sparkle/models/sea_sparkle_speck.glb (one speck, for a cloud of thousands drawn by one MultiMesh)
and sea_sparkle_speck_lo.glb (a lighter speck, for a cloud far off or a very big one), and the editable
creatures/sea_sparkle/tools/sea_sparkle.blend (this folder has a .gdignore). The shader (sea_sparkle.gdshader) tumbles
and drifts each speck and makes it glow and flash. It prints a WINDING line for each: the check that nothing is
inside out.

Sea sparkle is Noctiluca scintillans, a dinoflagellate: one cell, a clear round balloon about a millimetre across
with a short tentacle, that flashes blue when the water round it is disturbed. Each speck here is one, built bigger
than life (0.004 m across as built; `speck_size` scales it), from what it looks like under a lens (no picture was
traced or copied): a ball, a little squashed, with a groove down one side where the tentacle grows from it.

What a point is, for the shader: UV2.y the part (0 the cell, 1 the tentacle). UV.x how far from the cell's middle
seen face on (0 the middle, 1 its rim), for its glow. (The glTF writer flips V: what is written here is 1 - v, so
that Godot reads v.)
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

# As the cloud has it (SPECK in sea_sparkle.gd): how wide a speck is as built.
RADIUS = 0.002
CELL, TENTACLE = 0, 1


def to_b(p):
    return Vector((p.x, -p.z, p.y))


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
        ps = [self.verts[i] for i in points]
        n = (ps[1] - ps[0]).cross(ps[2] - ps[0])
        if n.length < 1e-18:
            return
        if n.dot(out) < 0.0:
            points = tuple(reversed(points))
        self.faces.append(tuple(points))
        self.out.append((Vector(out), name))
        self.count[name] = self.count.get(name, 0) + 1


def ball(m, subdivide):
    """An icosahedron (subdivided once for the speck, not for the low one), squashed a little, a groove down one side."""
    t = (1.0 + math.sqrt(5.0)) / 2.0
    corners = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
               (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    points = [Vector(c).normalized() for c in corners]
    tris = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6),
            (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10),
            (8, 6, 7), (9, 8, 1)]
    if subdivide:
        middles = {}

        def middle(a, b):
            key = (min(a, b), max(a, b))
            if key not in middles:
                points.append((points[a] + points[b]).normalized())
                middles[key] = len(points) - 1
            return middles[key]
        finer = []
        for a, b, c in tris:
            ab = middle(a, b)
            bc = middle(b, c)
            ca = middle(c, a)
            finer += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        tris = finer
    index = []
    for p in points:
        q = Vector((p.x, p.y * 0.88, p.z))
        # (the groove: a shallow dent down the side the tentacle grows from, +Z)
        q *= 1.0 - 0.08 * math.exp(-(p.x / 0.3) ** 2) * max(p.z, 0.0)
        index.append(m.add(q * RADIUS, (math.sqrt(p.x * p.x + p.y * p.y), 0.0), CELL))
    for a, b, c in tris:
        middle = (m.verts[index[a]] + m.verts[index[b]] + m.verts[index[c]]) / 3.0
        m.face((index[a], index[b], index[c]), middle, "cell")


def tentacle(m):
    """A short tapering tentacle, three-sided, from the groove, curling down."""
    root = Vector((0.0, -0.0002, RADIUS * 0.9))
    tip = Vector((0.0, -0.0016, RADIUS * 1.75))
    sides = []
    for k in range(3):
        a = k / 3.0 * math.tau
        sides.append(m.add(root + Vector((math.cos(a), math.sin(a) * 0.5, 0.0)) * 0.00028, (1.0, 0.0), TENTACLE))
    end = m.add(tip, (1.0, 0.0), TENTACLE)
    axis = (tip - root).normalized()
    for k in range(3):
        a = m.verts[sides[k]]
        b = m.verts[sides[(k + 1) % 3]]
        mid = (a + b) * 0.5
        out = mid - root
        out = out - axis * out.dot(axis)
        m.face((sides[k], sides[(k + 1) % 3], end), out, "tentacle")


def material_of(name, colour):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = colour
    material.diffuse_color = colour
    return material


def make(name, low):
    m = Mesh()
    ball(m, not low)
    if not low:
        tentacle(m)
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
    mesh.materials.append(material_of("sea_sparkle", (0.7, 0.85, 0.9, 1.0)))
    for poly in mesh.polygons:
        poly.use_smooth = m.out[poly.index][1] == "cell"
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    print("BUILT %s verts=%d tris=%d" % (name, len(mesh.vertices), tris))
    bad = {}
    for poly in mesh.polygons:
        out, group = m.out[poly.index]
        if poly.normal.dot(to_b(out)) <= 0.0:
            bad[group] = bad.get(group, 0) + 1
    told = ["%s %d/%d wrong" % (group, bad.get(group, 0), count) for group, count in m.count.items()]
    print("WINDING %s: %s: %s" % (name, "ok" if not bad else "INSIDE OUT", ", ".join(told)))
    return obj


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
    scene.display.shading.show_backface_culling = True
    scene.render.resolution_x, scene.render.resolution_y = 600, 600
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    views = [("side", (1, 0, 0)), ("front", (0, 1, 0)), ("back", (0, -1, 0)), ("top", (0.001, 0, 1))]
    for prefix, obj in (("", made[0]), ("lo_", made[1])):
        for other in made:
            other.hide_render = other is not obj
        for view, direction in views:
            offset = Vector(direction).normalized() * 10.0
            camera.data.ortho_scale = 0.0075
            camera.location = offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % (prefix, view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    speck = make("sea_sparkle_speck", False)
    low = make("sea_sparkle_speck_lo", True)
    os.makedirs(OUT, exist_ok=True)
    export_one(speck, os.path.join(OUT, "sea_sparkle_speck.glb"))
    export_one(low, os.path.join(OUT, "sea_sparkle_speck_lo.glb"))
    low.location.x = 0.008
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "sea_sparkle.blend"))
    low.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [speck, low])


if __name__ == "__main__":
    main()
