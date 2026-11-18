"""Builds the ghost fish (creatures/ghost_fish) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/ghost_fish/tools/build_ghost_fish.py
    blender --background --python creatures/ghost_fish/tools/build_ghost_fish.py -- <preview folder>   # with pictures

Writes creatures/ghost_fish/models/ghost_fish.glb (the fish with its halo, for the ghost shader) and
ghost_fish_bare.glb (the same bones without the halo cards, for drawing a school with GameCommon's Flock and its
own shader), and the editable creatures/ghost_fish/tools/ghost_fish.blend (this folder has a .gdignore). Each is
one still mesh with one surface, light enough (about 100 triangles) to draw hundreds in one MultiMesh. It prints a
WINDING line (the check that nothing is inside out; the cards are two-sided and are named as such).

A little glowing fish skeleton, 0.4 m long (Claude's design from the concept sheet's fourth panel): a skull with a
big round eye socket through it and a jaw, a spine of vertebrae, five pairs of ribs curving down, a forked tail
fin, and a faint halo round it. Its nose points to -Z, up is +Y; its origin is on its middle line half way along.

What a point is, for the shader (creatures/ghost_whale/ghost.gdshader, shared with the ghost whale): UV2.y the
part (0 a bone, 5 a halo card); UV.x how far along (0 the snout, 1 the tail's tips); UV.y along a bone (0..1), or
across a halo card (with UV.x: 0..1 each way). The vertex colour is the bones' pale colour (for the Flock's shader).
(The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.)
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

NAME = "ghost_fish"
LENGTH = 0.4
HALF = 0.2
BONE, HALO = 0, 5
TAU = math.tau
PI = math.pi
PALE = (0.8, 0.92, 1.0, 1.0)


def to_b(p):
    return Vector((p.x, -p.z, p.y))


def W(xm, y, x=0.0):
    return Vector((x, y, xm - HALF))


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
        """A face wound so that its front is towards `out` (for a two-sided card, the side named its front)."""
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


# The skull's outline seen from the side (metres behind the tip, metres up): from the snout over the
# brow to the back of the head, down to the angle of the jaw and forward along the jaw; and its eye.
SKULL = [(0.0, 0.004), (0.045, 0.038), (0.1, 0.042), (0.112, -0.004), (0.094, -0.034), (0.03, -0.022)]
EYE = (0.058, 0.012, 0.017)
THICK = 0.011


def skull(m):
    """The skull: its outline as a thin plate, the eye socket a round hole right through it."""
    n = len(SKULL)
    outer = []
    inner = []
    for side in (1.0, -1.0):
        o = [m.add(W(xm, y, side * THICK), (xm / LENGTH, 0.5), BONE) for xm, y in SKULL]
        hole = []
        for k in range(n):
            # (each point of the hole across from a point of the outline, so the plate is one ring of quads)
            xm, y = SKULL[k]
            a = math.atan2(y - EYE[1], xm - EYE[0])
            hole.append(m.add(W(EYE[0] + math.cos(a) * EYE[2], EYE[1] + math.sin(a) * EYE[2], side * THICK * 0.8),
                              (EYE[0] / LENGTH, 0.5), BONE))
        outer.append(o)
        inner.append(hole)
        for k in range(n):
            j = (k + 1) % n
            m.face((o[k], o[j], hole[j], hole[k]), Vector((side, 0.0, 0.0)), "skull")
    # the walls round the outline (facing out) and round the eye socket (facing in to the hole's middle)
    for k in range(n):
        j = (k + 1) % n
        a, b = outer[0], outer[1]
        mid = (m.verts[a[k]] + m.verts[a[j]]) * 0.5
        m.face((a[k], a[j], b[j], b[k]), Vector((0.0, mid.y - EYE[1], mid.z + HALF - EYE[0])), "skull")
        a, b = inner[0], inner[1]
        mid = (m.verts[a[k]] + m.verts[a[j]]) * 0.5
        m.face((a[k], a[j], b[j], b[k]), -Vector((0.0, mid.y - EYE[1], mid.z + HALF - EYE[0])), "skull")


def spine(m):
    """The backbone: a thin three-sided rod from the back of the skull to the tail, a little knobbly."""
    pts = [W(0.1 + 0.25 * i / 3, 0.006 - 0.004 * i / 3) for i in range(4)]
    rows = []
    for i, p in enumerate(pts):
        r = 0.0055 * (1.0 - 0.3 * i / 3)
        row = []
        for s in range(3):
            a = s / 3 * TAU
            row.append(m.add(p + Vector((math.sin(a) * r, math.cos(a) * r, 0.0)), ((p.z + HALF) / LENGTH, i / 3), BONE))
        rows.append((row, p))
    for i in range(len(rows) - 1):
        a, pa = rows[i]
        b, pb = rows[i + 1]
        for s in range(3):
            n = (s + 1) % 3
            at = (m.verts[a[s]] + m.verts[a[n]] + m.verts[b[n]] + m.verts[b[s]]) * 0.25
            m.face((a[s], a[n], b[n], b[s]), Vector((at.x, at.y - pa.y, 0.0)), "spine")
    for end, way in ((0, -1.0), (-1, 1.0)):
        row, p = rows[end]
        m.face(tuple(row), Vector((0.0, 0.0, way)), "spine")


def ribs(m):
    """Five pairs of ribs: thin cards curving out and down from the spine (two-sided)."""
    for i in range(5):
        xm = 0.135 + 0.038 * i
        long = 0.052 * (1.0 - 0.13 * i)
        for sx in (1.0, -1.0):
            root = W(xm, 0.004, sx * 0.004)
            tip = W(xm + 0.02, -long, sx * 0.018)
            w = Vector((0.0, 0.0, 0.0036))
            ids = [m.add(p + d, ((p.z + HALF) / LENGTH, t), BONE) for p, t in ((root, 0.0), (tip, 1.0)) for d in (-w, w)]
            m.face((ids[0], ids[1], ids[3], ids[2]), Vector((sx, -0.2, 0.0)), "ribs (two-sided cards)")


def tail(m):
    """The forked tail fin: a two-sided card."""
    root = m.add(W(0.345, 0.003), (0.86, 0.0), BONE)
    up = m.add(W(0.4, 0.05), (1.0, 1.0), BONE)
    notch = m.add(W(0.382, 0.002), (0.95, 0.6), BONE)
    down = m.add(W(0.4, -0.046), (1.0, 1.0), BONE)
    m.face((root, up, notch), Vector((1.0, 0.0, 0.0)), "tail fin (a two-sided card)")
    m.face((root, notch, down), Vector((1.0, 0.0, 0.0)), "tail fin (a two-sided card)")


def halo(m):
    """A faint halo: two crossed cards, one upright along the fish, one flat (two-sided; the shader draws a soft
    round glow on each)."""
    for upright in (True, False):
        corners = []
        for u, v in ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)):
            xm = -0.06 + 0.52 * u
            off = -0.11 + 0.22 * v
            p = W(xm, off, 0.0) if upright else W(xm, 0.0, off)
            corners.append(m.add(p, (u, v), HALO))
        m.face(tuple(corners), Vector((1.0, 0.0, 0.0)) if upright else Vector((0.0, 1.0, 0.0)), "halo (two-sided cards)")


def make(name, with_halo):
    m = Mesh()
    skull(m)
    spine(m)
    ribs(m)
    tail(m)
    if with_halo:
        halo(m)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) for p in m.verts], [], m.faces)
    mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.new(name="UV2")
    colours = mesh.color_attributes.new(name="Col", type="BYTE_COLOR", domain="CORNER")
    uv = mesh.uv_layers["UVMap"].data
    uv2 = mesh.uv_layers["UV2"].data
    for poly in mesh.polygons:
        for corner, vi in enumerate(poly.vertices):
            d = m.data[vi]
            uv[poly.loop_start + corner].uv = d[0]
            uv2[poly.loop_start + corner].uv = d[1]
            colours.data[poly.loop_start + corner].color = PALE
    material = bpy.data.materials.get(NAME) or bpy.data.materials.new(NAME)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = PALE
    material.diffuse_color = PALE
    mesh.materials.append(material)
    mesh.update()
    winding(name, mesh, m)
    for poly in mesh.polygons:
        poly.use_smooth = False
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    print("BUILT %s verts=%d tris=%d" % (name, len(mesh.vertices), tris))
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
        export_animations=False, export_texcoords=True, export_vertex_color="ACTIVE",
    )


def render(folder, made):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_backface_culling = False
    scene.render.resolution_x, scene.render.resolution_y = 1000, 700
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 100.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    views = [("left", (1, 0, 0)), ("front", (0, 1, 0)), ("top", (0.001, 0, 1)), ("quarter", (0.7, 0.5, 0.4))]
    for prefix, obj in zip(("bare_", ""), made):
        for other in made:
            other.hide_render = other is not obj
        for view, direction in views:
            offset = Vector(direction).normalized() * 10.0
            camera.data.ortho_scale = 0.5
            camera.location = offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % (prefix, view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    bare = make(NAME + "_bare", False)
    full = make(NAME, True)
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, NAME + ".glb"))
    export_one(bare, os.path.join(OUT, NAME + "_bare.glb"))
    bare.location.x = 0.3
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, NAME + ".blend"))
    bare.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [bare, full])


if __name__ == "__main__":
    main()
