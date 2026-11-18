"""Builds the box jelly (creatures/box_jelly) and exports it for Godot.

    blender --background --python creatures/box_jelly/tools/build_box_jelly.py

Writes creatures/box_jelly/models/box_jelly.glb (the full model), box_jelly_game.glb (the game model, at Twilight
Princess weight) and box_jelly_lo.glb (far off, crowds, phones: its tentacles are not laid along ropes), and the
editable creatures/box_jelly/tools/box_jelly.blend (all three; this folder has a .gdignore). Each is one static
mesh in two surfaces; the shaders beat the bell and lay the tentacles along their ropes. It prints a BUILT line
(triangles) and a WINDING line (nothing inside out) for each.

A box jelly (a sea wasp, after Chironex and its kin): a clear, faintly blue bell shaped like a cube with rounded
edges and a domed top, 0.25 m across and 0.25 m high, open below, a shelf (the velarium) round the inside of its
mouth; a small dark eye cluster (a rhopalium) low on each of its four faces; at each of its four lower corners a
flat stalk (a pedalium) from which several long thin tentacles trail, 2 m.

Everything here is in Godot space (metres, Y up) until it is written out. The origin is the middle of the
bell's mouth (its lower rim lies in y = 0); its faces look along +X, -X, +Z and -Z, its corners and stalks are
on the diagonals. It has no front.

What a point is, for the shaders:
- vertex colour red: the part. 0 the outside of the bell, 0.25 its inside (with the lip and the velarium),
  0.5 a stalk (in the bell's surface, moved with it), 0.75 a tentacle (a line).
- green: on a tentacle, half its width / LINE_SCALE (the shader draws it that wide, turned to face the camera).
- blue: on a tentacle, which rope it follows ((corner + 0.5) / 32).
- alpha: on a tentacle, how far along its rope it reaches.
- UV.x: on the bell round it (0..1, a face's middle at 0, 0.25, 0.5, 0.75); on a tentacle across it (0..1).
  UV.y: on the bell 0 the crown to 1 the rim; on a tentacle how far along its rope.
- UV2.x: a tentacle's rope's length (metres); UV2.y: a number of its own (0..1).
(The glTF writer flips V: what is written is 1 - v, so that Godot reads v.)

The ropes' roots, lengths and phases are in BoxJelly.strands() too: change one, change the other.
Surfaces: "box_jelly_strands" (drawn first) and "box_jelly_bell" (inside, stalks, then outside: BoxJelly sorts
its triangles into that order when it loads it).
"""

import math
import os

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "models")

# Kept in step with box_jelly.gd and the shaders.
HALF = 0.125
HEIGHT = 0.25
CORNERS = 4
TENTACLE_LONG = 2.0
# Where a stalk's tip is (the rope's root): out along the diagonal and down.
STALK_OUT = 0.15
STALK_Y = -0.055
LINE_SCALE = 0.02
TENTACLES_FULL = 6

SURFACES = ["box_jelly_strands", "box_jelly_bell"]
STRANDS, BELL = 0, 1
OUTSIDE, INSIDE, STALK, TENTACLE = 0.0, 0.25, 0.5, 0.75
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


def corner_strand(k):
    a = math.pi * 0.25 + k * math.pi * 0.5
    root = Vector((math.cos(a) * STALK_OUT, STALK_Y, math.sin(a) * STALK_OUT))
    return root, TENTACLE_LONG * (1.0 + 0.05 * math.sin(k * 2.3 + 1.0)), fract(k * 0.618), a


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


def square(a):
    """How far out a rounded square reaches at angle `a`, for a face 1 from its middle."""
    return (abs(math.cos(a)) ** 4 + abs(math.sin(a)) ** 4) ** -0.25


def bell_point(v, a, inner):
    """A point of the bell: `v` 0 at the crown to 1 at the rim, `a` the angle round it (0 a face's middle)."""
    t = v * math.pi * 0.5
    # a rounded box in profile: a domed top, walls nearly straight down, a little wider at the mouth
    r = math.sin(t) ** 0.45
    y = HEIGHT * math.cos(t) ** 0.55
    half = HALF * (1.0 + 0.04 * smooth(0.5, 1.0, v))
    if inner:
        half *= 0.86
        y = y * 0.9 + 0.004
    rad = half * r * square(a)
    return Vector((math.cos(a) * rad, y, math.sin(a) * rad))


def bell(m, around, rings_out, rings_in, in_around):
    middle = Vector((0.0, HEIGHT * 0.45, 0.0))
    grids = {}
    for name, inner, rings, code, count in (("out", False, rings_out, OUTSIDE, around), ("in", True, rings_in, INSIDE, in_around)):
        grid = []
        for r in range(rings + 1):
            v = (r / rings) ** 0.8
            row = []
            for c in range(count + 1):
                a = c / count * TAU
                row.append(m.add(bell_point(v, a, inner), (c / count, v), (0.0, 0.0), (code, 0.0, 0.0, 1.0)))
            grid.append(row)
        grids[name] = (grid, rings, count)
    for name, sign in (("in", -1.0), ("out", 1.0)):
        grid, rings, count = grids[name]
        for r in range(rings):
            for c in range(count):
                ids = (grid[r][c], grid[r][c + 1], grid[r + 1][c + 1], grid[r + 1][c])
                p = sum((m.verts[i] for i in ids), Vector()) * 0.25
                if r == 0:
                    ids = (grid[0][c], grid[1][c + 1], grid[1][c])
                m.face(ids, BELL, (p - middle) * sign)
    # the lip, and the velarium: a shelf from the inside of the rim in towards the middle, its edge a little up
    rows = []
    for k, (inner, scale, lift) in enumerate(((False, 1.0, 0.0), (True, 1.0, 0.0), (True, 0.78, 0.012))):
        row = []
        for c in range(around + 1):
            a = c / around * TAU
            p = bell_point(1.0, a, inner)
            p = Vector((p.x * scale, p.y + lift, p.z * scale))
            row.append(m.add(p, (c / around, 1.0), (0.0, 0.0), (INSIDE, 0.0, 0.0, 1.0)))
        rows.append(row)
    for c in range(around):
        p = m.verts[rows[0][c]]
        m.face((rows[0][c], rows[1][c], rows[1][c + 1], rows[0][c + 1]), BELL, Vector((p.x, -1.0, p.z)))
        m.face((rows[1][c], rows[2][c], rows[2][c + 1], rows[1][c + 1]), BELL, Vector((0.0, -1.0, 0.0)))


def stalk(m, k, steps, sides):
    """The flat stalk at corner `k`: from the bell's lower corner out along the diagonal and down to where the
    tentacles leave it, a blade wider than it is thick."""
    root, long, phase, a = corner_strand(k)
    out = Vector((math.cos(a), 0.0, math.sin(a)))
    across = Vector((-math.sin(a), 0.0, math.cos(a)))
    start = bell_point(0.93, a, False)
    rows = []
    middles = []
    for i in range(steps + 1):
        t = i / steps
        # (bowed: out first, then down)
        mid = start.lerp(root, t) + out * 0.012 * math.sin(t * math.pi)
        wide = 0.011 + 0.006 * t
        thick = 0.004
        row = []
        for j in range(sides):
            th = j / sides * TAU
            p = mid + across * math.cos(th) * wide + Vector((0.0, 1.0, 0.0)).cross(across) * math.sin(th) * thick
            row.append(m.add(p, (j / sides, t), (0.0, 0.0), (STALK, 0.0, 0.0, 1.0)))
        rows.append(row)
        middles.append(mid)
    for i in range(steps):
        for j in range(sides):
            n = (j + 1) % sides
            ids = (rows[i][j], rows[i][n], rows[i + 1][n], rows[i + 1][j])
            p = sum((m.verts[q] for q in ids), Vector()) * 0.25
            m.face(ids, BELL, p - (middles[i] + middles[i + 1]) * 0.5)
    # (its tip closed)
    tip = m.add(middles[-1] + Vector((0.0, -0.003, 0.0)), (0.5, 1.0), (0.0, 0.0), (STALK, 0.0, 0.0, 1.0))
    for j in range(sides):
        n = (j + 1) % sides
        m.face((rows[-1][j], rows[-1][n], tip), BELL, Vector((0.0, -1.0, 0.0)))


def tentacles(m, k, count, steps, thicker):
    """Corner `k`'s tentacles: `count` long thin lines leaving the stalk's tip side by side, each following the
    corner's one rope and drifting a little from it."""
    root, long, phase, a = corner_strand(k)
    across = Vector((-math.sin(a), 0.0, math.cos(a)))
    row_code = (k + 0.5) / 32.0
    for j in range(count):
        t = (j + 0.5) / count
        jf = min(int(t * TENTACLES_FULL), TENTACLES_FULL - 1)
        n = k * 31.0 + jf * 7.3
        h1, h2, h3 = hash1(n), hash1(n + 1.7), hash1(n + 3.3)
        u = t * 2.0 - 1.0
        start = root + across * u * 0.014
        reach = 0.82 + 0.18 * h1
        tl = long * reach
        drift = Vector((math.cos(h2 * TAU), 0.0, math.sin(h2 * TAU))) * (0.02 + 0.05 * h3) + across * u * 0.03
        half = 0.0016 * thicker
        for i in range(steps + 1):
            ts = (i / steps) ** 1.1
            s = ts * reach
            lateral = (start - root) + drift * smooth(0.0, 1.0, ts) ** 0.8
            centre = Vector((root.x + lateral.x, root.y - ts * tl, root.z + lateral.z))
            w = half * (1.0 - 0.4 * ts)
            for side in (0, 1):
                m.add(centre + Vector(((side * 2 - 1) * w, 0.0, 0.0)), (float(side), s), (long, fract(h3 + phase)), (TENTACLE, w / LINE_SCALE, row_code, reach))
            if i > 0:
                b = len(m.verts) - 4
                m.face((b, b + 1, b + 3, b + 2), STRANDS)


def make(name, kind):
    m = Mesh()
    for k in range(CORNERS):
        if kind == "full":
            tentacles(m, k, TENTACLES_FULL, 60, 1.0)
        elif kind == "game":
            tentacles(m, k, 3, 14, 1.2)
        else:
            tentacles(m, k, 2, 6, 1.6)
    if kind == "full":
        bell(m, 128, 20, 10, 64)
    elif kind == "game":
        bell(m, 48, 7, 4, 32)
    else:
        bell(m, 24, 4, 2, 16)
    for k in range(CORNERS):
        if kind == "full":
            stalk(m, k, 12, 8)
        elif kind == "game":
            stalk(m, k, 5, 4)
        else:
            stalk(m, k, 2, 4)
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
    tints = {SURFACES[0]: (0.7, 0.85, 1.0, 1.0), SURFACES[1]: (0.75, 0.9, 1.0, 1.0)}
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
        obj = make("box_jelly" + suffix, kind)
        export_one(obj, os.path.join(OUT, "box_jelly%s.glb" % suffix))
        made.append(obj)
    made[1].location.x = 0.5
    made[2].location.x = 1.0
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "box_jelly.blend"))


if __name__ == "__main__":
    main()
