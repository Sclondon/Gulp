"""Builds the Portuguese man o' war (creatures/man_o_war) and exports it for Godot.

    blender --background --python creatures/man_o_war/tools/build_man_o_war.py

Writes creatures/man_o_war/models/man_o_war.glb (the full model), man_o_war_game.glb (the game model, at Twilight
Princess weight) and man_o_war_lo.glb (far off, crowds, phones: its tentacles are not laid along ropes), and the
editable creatures/man_o_war/tools/man_o_war.blend (all three; this folder has a .gdignore). Each is one static
mesh in two surfaces; the shaders rock the float and lay the tentacles along their ropes. It prints a BUILT line
(triangles) and a WINDING line (nothing inside out) for each.

A Portuguese man o' war (Physalia physalis): it floats AT the surface. A gas float 0.25 m long, clear blue low
down going pink and violet higher up, its front end narrower and turned up a little, its back end round; along
its top a pleated crest (its sail) standing up, edged in pink; under its back half a cluster of short dark blue
polyps, and from them long dark blue tentacles hanging 4 m down, coiled tight near the float and looser below,
beaded with stinging cells.

Everything here is in Godot space (metres, Y up) until it is written out. **The origin is on the waterline**, in
the middle of the float's length and width: the waterline is y = 0. The float's bottom is 0.011 m under the
water, its top 0.061 m above it, the crest's top 0.13 m above it; the tentacles hang from 0.012 m down. Its
narrow front end points to -Z.

What a point is, for the shaders:
- vertex colour red: the part. 0 the float, 0.5 the crest (in the float's surface, rocked with it), 0.75 a
  tentacle (a line), 0.875 a polyp (a short line).
- green: on a line, half its width / LINE_SCALE (the shader draws it that wide, turned to face the camera).
- blue: on a line, which rope it follows ((rope + 0.5) / 32).
- alpha: on a line, how far along its rope it reaches.
- UV.x: on the float round it (0..1, 0 the top); on the crest along it (0..1); on a line across it (0..1).
  UV.y: on the float along it (0 the front, 1 the back); on the crest up it (0 its foot, 1 its edge); on a line
  how far along its rope.
- UV2.x: a line's rope's length (metres); UV2.y: a number of its own (0..1).
(The glTF writer flips V: what is written is 1 - v, so that Godot reads v.)

The ropes' roots, lengths and phases are in ManOWar.strands() too: change one, change the other.
Surfaces: "man_o_war_strands" (drawn first) and "man_o_war_float" (crest, then float: ManOWar sorts its
triangles into that order when it loads it).
"""

import math
import os

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "models")

# Kept in step with man_o_war.gd and the shaders.
FLOAT_LONG = 0.25
ROPES = 6
TENTACLE_LONG = 4.0
ROOT_Y = -0.012
LINE_SCALE = 0.02

SURFACES = ["man_o_war_strands", "man_o_war_float"]
STRANDS, FLOAT = 0, 1
BODY, CREST, TENTACLE, POLYP = 0.0, 0.5, 0.75, 0.875
TAU = math.tau


def to_b(p):
    return Vector((p.x, -p.z, p.y))


def fract(x):
    return x - math.floor(x)


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def hash1(n):
    return fract(math.sin(n * 12.9898 + 4.1) * 43758.5453)


def rope_strand(k):
    """Rope k: where it hangs from under the float's back half, how long, its phase."""
    t = 0.38 + 0.09 * k
    x = 0.009 * (1 if k % 2 == 0 else -1)
    root = Vector((x, ROOT_Y, -FLOAT_LONG * 0.5 + FLOAT_LONG * t))
    return root, TENTACLE_LONG * (1.0 + 0.06 * math.sin(k * 2.3 + 1.0)), fract(k * 0.618)


class Mesh:
    def __init__(self):
        self.verts = []
        self.data = []
        self.faces = []
        self.surface = []
        self.want = []

    def add(self, p, uv, uv2, colour):
        self.verts.append(p)
        self.data.append((uv, uv2, colour))
        return len(self.verts) - 1

    def face(self, ids, surface, want=None):
        ids = tuple(ids)
        if want is not None:
            n = Vector((0.0, 0.0, 0.0))
            for i in range(len(ids)):
                n += self.verts[ids[i]].cross(self.verts[ids[(i + 1) % len(ids)]])
            if n.dot(want) < 0.0:
                ids = tuple(reversed(ids))
        self.faces.append(ids)
        self.surface.append(surface)
        self.want.append(want)


def float_section(t):
    """The float at `t` (0 its front, 1 its back): its middle (y), half its height, half its width."""
    half = 0.04 * max(0.0, math.sin(math.pi * t)) ** 0.55 * (0.82 + 0.25 * smooth(0.2, 0.9, t))
    centre = 0.024 + 0.022 * (1.0 - t) ** 3.0
    return centre, half, half * 0.82


def float_body(m, rows, around):
    middles = []
    grid = []
    for r in range(rows + 1):
        # (rows closer at the two ends, where it rounds off)
        t = 0.5 - 0.5 * math.cos(math.pi * r / rows)
        centre, hy, hx = float_section(t)
        z = -FLOAT_LONG * 0.5 + FLOAT_LONG * t
        middles.append(Vector((0.0, centre, z)))
        row = []
        for c in range(around + 1):
            th = c / around * TAU
            p = Vector((math.sin(th) * hx, centre + math.cos(th) * hy, z))
            row.append(m.add(p, (c / around, t), (0.0, 0.0), (BODY, 0.0, 0.0, 1.0)))
        grid.append(row)
    for r in range(rows):
        for c in range(around):
            ids = (grid[r][c], grid[r][c + 1], grid[r + 1][c + 1], grid[r + 1][c])
            p = sum((m.verts[i] for i in ids), Vector()) * 0.25
            if r == 0:
                ids = (grid[0][c], grid[1][c + 1], grid[1][c])
            elif r == rows - 1:
                ids = (grid[r][c], grid[r][c + 1], grid[r + 1][c])
            m.face(ids, FLOAT, p - (middles[r] + middles[r + 1]) * 0.5)


def crest(m, rows, ups, pleats):
    """The crest along the float's top, from a sixth of the way back to near its back end: a thin sheet standing
    up, arched, pleated across (a fold every so often), its edge a little scalloped. Two-sided."""
    grid = []
    t0, t1 = 0.14, 0.9
    for r in range(rows + 1):
        t = t0 + (t1 - t0) * r / rows
        centre, hy, hx = float_section(t)
        z = -FLOAT_LONG * 0.5 + FLOAT_LONG * t
        foot = centre + hy * 0.9
        x01 = (t - t0) / (t1 - t0)
        tall = 0.058 * max(0.0, math.sin(math.pi * x01)) ** 0.6 * (0.85 + 0.3 * x01) + 0.006
        row = []
        for u in range(ups + 1):
            up = u / ups
            fold = 0.007 * math.sin(x01 * pleats * math.pi) * smooth(0.0, 0.6, up)
            edge = 1.0 + 0.06 * abs(math.sin(x01 * pleats * math.pi)) * up
            p = Vector((fold, foot + tall * up * edge, z))
            row.append(m.add(p, (x01, up), (0.0, 0.0), (CREST, 0.0, 0.0, 1.0)))
        grid.append(row)
    for r in range(rows):
        for u in range(ups):
            m.face((grid[r][u], grid[r + 1][u], grid[r + 1][u + 1], grid[r][u + 1]), FLOAT)


def line(m, k, start, reach, steps, half, code, curl, seed):
    """One line following rope `k`, from `start` (an offset from the rope's root) down to `reach` of the rope,
    in a slow wave. `curl` (how many coils in its first 0.6 m) is not built in: it goes in its part code (0.75 +
    curl / 100) and the shader coils it round its line, so that the strip it is drawn as turns with the coil."""
    root, long, phase = rope_strand(k)
    row_code = (k + 0.5) / 32.0
    ll = long * reach
    for i in range(steps + 1):
        ts = (i / steps) ** (1.7 if curl > 0 else 1.0)
        s = ts * reach
        metres = ts * ll
        wave = Vector((math.sin(metres * 2.1 + seed * 5.0), 0.0, math.cos(metres * 1.7 + seed * 3.0))) * 0.03 * smooth(0.3, 1.5, metres)
        centre = root + start + Vector((0.0, -metres, 0.0)) + wave
        centre.y = root.y + start.y - metres
        w = half * (1.0 - 0.5 * ts)
        part = code + curl * 0.01 if code == TENTACLE else code
        for side in (0, 1):
            m.add(centre + Vector(((side * 2 - 1) * w, 0.0, 0.0)), (float(side), s), (long, fract(seed + phase)), (part, w / LINE_SCALE, row_code, reach))
        if i > 0:
            b = len(m.verts) - 4
            m.face((b, b + 1, b + 3, b + 2), STRANDS)


def rope_lines(m, k, kind):
    root, long, phase = rope_strand(k)
    if kind == "full":
        line(m, k, Vector(), 1.0, 80, 0.004, TENTACLE, 3.0, hash1(k))
        for j in range(2):
            line(m, k, Vector(((j * 2 - 1) * 0.006, 0.0, 0.004)), 0.45 + 0.25 * hash1(k * 5 + j), 40, 0.0024, TENTACLE, 3.0, hash1(k * 7 + j + 0.5))
        polyps = 6
    elif kind == "game":
        line(m, k, Vector(), 1.0, 40, 0.0048, TENTACLE, 3.0, hash1(k))
        polyps = 3
    else:
        line(m, k, Vector(), 1.0, 8, 0.006, TENTACLE, 0.0, hash1(k))
        polyps = 1
    for j in range(polyps):
        n = k * 13.0 + j * 3.1
        h1, h2, h3 = hash1(n), hash1(n + 1.3), hash1(n + 2.9)
        start = Vector((math.cos(h2 * TAU) * 0.014, 0.0, math.sin(h2 * TAU) * 0.014))
        line(m, k, start, (0.025 + 0.025 * h1) * 4.0 / long, 4 if kind == "full" else 2, 0.003 if kind != "low" else 0.0045, POLYP, 0.0, h3)


def make(name, kind):
    m = Mesh()
    for k in range(ROPES):
        rope_lines(m, k, kind)
    if kind == "full":
        crest(m, 96, 5, 12)
        float_body(m, 56, 40)
    elif kind == "game":
        crest(m, 36, 2, 12)
        float_body(m, 22, 18)
    else:
        crest(m, 12, 1, 4)
        float_body(m, 10, 8)
    return finish(name, m)


def finish(name, m):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) for p in m.verts], [], list(m.faces))
    mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.new(name="UV2")
    mesh.color_attributes.new(name="Color", type="FLOAT_COLOR", domain="CORNER")
    uv = mesh.uv_layers["UVMap"].data
    uv2 = mesh.uv_layers["UV2"].data
    colour = mesh.color_attributes["Color"].data
    for poly in mesh.polygons:
        for corner, vi in enumerate(poly.vertices):
            d = m.data[vi]
            uv[poly.loop_start + corner].uv = (d[0][0], 1.0 - d[0][1])
            uv2[poly.loop_start + corner].uv = (d[1][0], 1.0 - d[1][1])
            colour[poly.loop_start + corner].color = d[2]
    mesh.color_attributes.active_color = mesh.color_attributes["Color"]
    mesh.color_attributes.render_color_index = mesh.color_attributes.find("Color")
    tints = {SURFACES[0]: (0.15, 0.25, 0.6, 1.0), SURFACES[1]: (0.6, 0.6, 1.0, 1.0)}
    for surface in SURFACES:
        material = bpy.data.materials.get(surface) or bpy.data.materials.new(surface)
        material.use_nodes = True
        bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Base Color"].default_value = tints[surface]
        material.diffuse_color = tints[surface]
        mesh.materials.append(material)
    for poly in mesh.polygons:
        poly.use_smooth = True
        poly.material_index = m.surface[poly.index]
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    print("BUILT %s verts=%d tris=%d" % (name, len(mesh.vertices), tris))
    wrong = 0
    sided = 0
    for poly in mesh.polygons:
        want = m.want[poly.index]
        if want is None:
            continue
        sided += 1
        if poly.normal.dot(to_b(want)) <= 0.0:
            wrong += 1
    print("WINDING %s: %s: %d of %d one-sided faces wrong, %d two-sided" % (name, "ok" if wrong == 0 else "INSIDE OUT", wrong, sided, len(mesh.polygons) - sided))
    return obj


def export_one(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", export_yup=True, use_selection=True,
        export_animations=False, export_vertex_color="ACTIVE", export_texcoords=True,
    )


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    os.makedirs(OUT, exist_ok=True)
    made = []
    for suffix, kind in (("", "full"), ("_game", "game"), ("_lo", "low")):
        obj = make("man_o_war" + suffix, kind)
        export_one(obj, os.path.join(OUT, "man_o_war%s.glb" % suffix))
        made.append(obj)
    made[1].location.x = 0.5
    made[2].location.x = 1.0
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "man_o_war.blend"))


if __name__ == "__main__":
    main()
