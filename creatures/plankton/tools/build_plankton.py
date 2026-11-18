"""Builds the plankton specks (creatures/plankton) and exports them for Godot.

Run from the game's root:
    blender --background --python creatures/plankton/tools/build_plankton.py
    blender --background --python creatures/plankton/tools/build_plankton.py -- <preview folder>   # with pictures

Writes creatures/plankton/models/plankton_specks.glb and the editable creatures/plankton/tools/plankton.blend (this
folder has a .gdignore). The .glb is ONE still mesh holding four kinds of speck, all at the same place (the
origin): a cloud draws it many times in one MultiMesh and its shader (plankton.gdshader) shows one kind in each
instance and squashes the others' points to nothing. Each speck is a handful of triangles, drawn from both sides.
It prints a WINDING line: the check that every triangle faces the way it was made to.

The specks, built from what the animals and algae look like under a lens (no picture was traced or copied), each
a few millimetres across (bigger than life: a cloud's `speck_size` scales them):

- 0 A COPEPOD: a teardrop body (the front part wide, tapering back), a thin forked tail, and two long antennae
  swept out and back to either side, longer than the body (the shader draws a red eye spot at its front).
- 1 A DIATOM CHAIN: four box-like cells in a row, joined end to end, a long fine spine out from each corner of
  each join to either side: a comb.
- 2 A RADIOLARIAN: a round glassy ball with six long spines out from it.
- 3 A CRAB LARVA (a zoea): a round carapace, a long spike up from its back, a shorter one forward and down from
  its front, two big eyes, and a thin jointed tail curled under.

What a point is, for the shader: UV2.y the kind (0 to 3, as above). UV.x what it is part of: 0 a body, 1 a spine,
antenna or tail (fine and glassy), 2 an eye. (The glTF writer flips V: what is written is 1 - v, so that Godot
reads v.)
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
TAU = math.tau
COPEPOD, DIATOM, RADIOLARIAN, ZOEA = range(4)
BODY, FINE, EYE = range(3)


def to_b(p):
    """Godot's space (Y up, front at -Z) to Blender's (Z up, front at +Y)."""
    return Vector((p.x, -p.z, p.y))


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.data = []
        self.out = []
        self.count = {}
        self.kind = 0
        self.what = BODY

    def add(self, p):
        self.verts.append(Vector(p))
        self.data.append(((float(self.what), 1.0), (0.0, 1.0 - float(self.kind))))
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

    def tri(self, a, b, c, out, name):
        self.face((self.add(a), self.add(b), self.add(c)), out, name)

    def sliver(self, a, b, wide, name, up=Vector((0.0, 1.0, 0.0))):
        """A fine spine from `a` to `b`: one thin triangle, `wide` at its root, nothing at its tip."""
        a, b = Vector(a), Vector(b)
        d = (b - a).normalized()
        side = d.cross(up)
        if side.length < 0.2:
            side = d.cross(Vector((1.0, 0.0, 0.0)))
        side.normalize()
        self.tri(a - side * wide * 0.5, a + side * wide * 0.5, b, d.cross(side), name)


def diamond(m, centre, rx, ry, rz, name, around=4):
    """A closed spindle: a ring of `around` points round its middle, a point at its front and its back."""
    centre = Vector(centre)
    ring = [m.add(centre + Vector((rx * math.cos(TAU * i / around + math.pi / around), ry * math.sin(TAU * i / around + math.pi / around), 0.0)))
            for i in range(around)]
    for tip_z in (-rz, rz):
        tip = m.add(centre + Vector((0.0, 0.0, tip_z)))
        for i in range(around):
            a, b = ring[i], ring[(i + 1) % around]
            middle = (m.verts[a] + m.verts[b] + m.verts[tip]) / 3.0
            m.face((tip, a, b), middle - centre, name)


def octahedron(m, centre, rx, ry, rz, name):
    centre = Vector(centre)
    points = [Vector((rx, 0, 0)), Vector((0, ry, 0)), Vector((-rx, 0, 0)), Vector((0, -ry, 0))]
    ring = [m.add(centre + p) for p in points]
    for tip_z in (-rz, rz):
        tip = m.add(centre + Vector((0.0, 0.0, tip_z)))
        for i in range(4):
            a, b = ring[i], ring[(i + 1) % 4]
            middle = (m.verts[a] + m.verts[b] + m.verts[tip]) / 3.0
            m.face((tip, a, b), middle - centre, name)


def copepod(m):
    m.kind = COPEPOD
    m.what = BODY
    # the body: wide at the front, tapering back (its widest ring a little ahead of the middle)
    ring_z = -0.0006
    around = 4
    ring = [m.add(Vector((0.0011 * math.cos(TAU * i / around), 0.0009 * math.sin(TAU * i / around), ring_z))) for i in range(around)]
    for tip in (Vector((0.0, 0.0, -0.0017)), Vector((0.0, 0.0, 0.0018))):
        t = m.add(tip)
        for i in range(around):
            a, b = ring[i], ring[(i + 1) % around]
            middle = (m.verts[a] + m.verts[b] + m.verts[t]) / 3.0
            m.face((t, a, b), middle - Vector((0.0, 0.0, ring_z)), "copepod")
    m.what = FINE
    # the tail: thin, forked at its end
    m.sliver((0.0, 0.0, 0.0012), (0.0, 0.0, 0.0034), 0.0005, "copepod")
    for sx in (1.0, -1.0):
        m.sliver((0.0, 0.0, 0.0031), (sx * 0.0006, 0.0, 0.0042), 0.00025, "copepod")
        # an antenna: from the front of the head, out and back, longer than the body
        m.sliver((sx * 0.0005, 0.0002, -0.0014), (sx * 0.0048, -0.0001, 0.0012), 0.0003, "copepod")


def diatom(m):
    m.kind = DIATOM
    m.what = BODY
    cells = 4
    long = 0.0012
    wide = 0.0007
    start = -cells * long * 0.5
    # the chain: a long box, its four sides (the cells' faces are drawn by the shader)
    corners = [Vector((wide, wide * 0.6, 0.0)), Vector((-wide, wide * 0.6, 0.0)), Vector((-wide, -wide * 0.6, 0.0)), Vector((wide, -wide * 0.6, 0.0))]
    ends = (start, -start)
    for i in range(4):
        a, b = corners[i], corners[(i + 1) % 4]
        quad = [m.add(a + Vector((0, 0, ends[0]))), m.add(b + Vector((0, 0, ends[0]))), m.add(b + Vector((0, 0, ends[1]))), m.add(a + Vector((0, 0, ends[1])))]
        m.face(quad, (a + b) * 0.5, "diatom")
    for z, way in ((ends[0], -1.0), (ends[1], 1.0)):
        m.face(tuple(m.add(c + Vector((0, 0, z))) for c in corners), Vector((0.0, 0.0, way)), "diatom")
    # the spines: out to either side from each join, bending away along the chain
    m.what = FINE
    for k in range(cells + 1):
        z = start + k * long
        for sx in (1.0, -1.0):
            m.sliver((sx * wide, 0.0, z), (sx * 0.0042, 0.0006 * sx, z + 0.0012 * (k - cells * 0.5)), 0.00022, "diatom")


def radiolarian(m):
    m.kind = RADIOLARIAN
    m.what = BODY
    octahedron(m, Vector((0.0, 0.0, 0.0)), 0.0013, 0.0013, 0.0013, "radiolarian")
    m.what = FINE
    for d in ((1, 0.2, 0.1), (-1, -0.1, 0.25), (0.15, 1, -0.2), (-0.2, -1, 0.1), (0.1, -0.25, 1), (-0.25, 0.2, -1)):
        d = Vector(d).normalized()
        m.sliver(d * 0.0009, d * 0.0042, 0.0003, "radiolarian", up=Vector((0.3, 0.5, 0.8)).normalized())


def zoea(m):
    m.kind = ZOEA
    m.what = BODY
    octahedron(m, Vector((0.0, 0.0, 0.0)), 0.0011, 0.0013, 0.0014, "zoea")
    m.what = FINE
    # the long spike up from its back, and the shorter one forward and down from its front
    m.sliver((0.0, 0.0011, 0.0002), (0.0, 0.0044, 0.0009), 0.0005, "zoea", up=Vector((0.0, 0.0, 1.0)))
    m.sliver((0.0, -0.0004, -0.0012), (0.0, -0.0026, -0.0036), 0.0004, "zoea", up=Vector((0.0, 0.0, 1.0)))
    # the tail, curled under: two thin pieces
    m.sliver((0.0, -0.0008, 0.0010), (0.0, -0.0024, 0.0030), 0.0005, "zoea", up=Vector((0.0, 0.0, 1.0)))
    m.sliver((0.0, -0.0024, 0.0030), (0.0, -0.0040, 0.0018), 0.0004, "zoea", up=Vector((0.0, 0.0, 1.0)))
    # the eyes: a small dark spindle each side at its front
    m.what = EYE
    for sx in (1.0, -1.0):
        diamond(m, Vector((sx * 0.0010, 0.0001, -0.0010)), 0.00045, 0.00045, 0.0005, "zoea", around=3)


def material_of(name, colour):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = colour
    material.diffuse_color = colour
    return material


def finish(name, m):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) for p in m.verts], [], m.faces)
    # (every layer made first, then each looked up by name: making one moves the others)
    mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.new(name="UV2")
    uv = mesh.uv_layers["UVMap"].data
    uv2 = mesh.uv_layers["UV2"].data
    for poly in mesh.polygons:
        for corner, vi in enumerate(poly.vertices):
            uv[poly.loop_start + corner].uv = m.data[vi][0]
            uv2[poly.loop_start + corner].uv = m.data[vi][1]
    mesh.materials.append(material_of(name, (0.9, 0.85, 0.7, 1.0)))
    # (flat: each speck is so few faces that smooth shading would turn the light across a whole speck)
    for poly in mesh.polygons:
        poly.use_smooth = False
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    print("BUILT %s verts=%d tris=%d (%s)" % (name, len(mesh.vertices), tris, ", ".join("%s %d" % kv for kv in m.count.items())))
    bad = {}
    for poly in mesh.polygons:
        out, group = m.out[poly.index]
        if poly.normal.dot(to_b(out)) <= 0.0:
            bad[group] = bad.get(group, 0) + 1
    told = ["%s %d/%d wrong" % (group, bad.get(group, 0), count) for group, count in m.count.items()]
    print("WINDING %s: %s: %s" % (name, "ok" if not bad else "INSIDE OUT", ", ".join(told)))
    return obj


def render(folder, obj):
    """Each kind alone, side by side (moved apart for the picture only)."""
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_backface_culling = False
    scene.render.resolution_x, scene.render.resolution_y = 1600, 500
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    shown = obj.copy()
    shown.data = obj.data.copy()
    bpy.context.collection.objects.link(shown)
    obj.hide_render = True
    uv2 = shown.data.uv_layers["UV2"].data
    kinds = [0] * len(shown.data.vertices)
    for poly in shown.data.polygons:
        for corner, vi in enumerate(poly.vertices):
            kinds[vi] = round(1.0 - uv2[poly.loop_start + corner].uv[1])
    for vi, v in enumerate(shown.data.vertices):
        v.co.x += (kinds[vi] - 1.5) * 0.011
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 0.046
    camera.data.clip_start = 0.001
    scene.collection.objects.link(camera)
    scene.camera = camera
    # (Blender space: the specks are spread along X for the picture, their fronts at +Y, up is Z)
    for view, direction in (("front", (0, 1, 0)), ("back", (0, -1, 0)), ("above", (0.0001, 0.0, 1.0)), ("below", (0.0001, 0.0, -1.0)), ("quarter", (0.35, 0.75, 0.55))):
        offset = Vector(direction).normalized() * 1.0
        camera.location = offset
        camera.rotation_euler = (-offset).to_track_quat("-Z", "Z" if abs(offset.normalized().z) < 0.9 else "Y").to_euler()
        scene.render.filepath = os.path.join(folder, "specks_%s.png" % view)
        bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    m = Mesh()
    copepod(m)
    diatom(m)
    radiolarian(m)
    zoea(m)
    obj = finish("plankton_specks", m)
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(OUT, "plankton_specks.glb"), export_format="GLB", export_yup=True, use_selection=True,
        export_animations=False, export_texcoords=True, export_vertex_color="NONE",
    )
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "plankton.blend"))
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, obj)


if __name__ == "__main__":
    main()
