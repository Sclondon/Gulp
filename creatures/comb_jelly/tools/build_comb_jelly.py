"""Builds the comb jelly (creatures/comb_jelly) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/comb_jelly/tools/build_comb_jelly.py
    blender --background --python creatures/comb_jelly/tools/build_comb_jelly.py -- <preview folder>   # with pictures

Writes creatures/comb_jelly/models/comb_jelly.glb (the full model, for one seen close), comb_jelly_game.glb (the game
model: the triangles spent on the outline and the lobes' edges) and comb_jelly_lo.glb (far off), and the editable
creatures/comb_jelly/tools/comb_jelly.blend (this folder has a .gdignore). Each is one still mesh with one surface:
the shader (comb_jelly.gdshader) draws it clear, beats its comb plates and runs rainbow light along its comb rows.
It prints a WINDING line for each: the check that nothing is inside out.

A lobate comb jelly (a ctenophore, as Mnemiopsis or Bolinopsis), 0.1 m long, built from what these look like (no
picture was traced or copied):

- THE BODY: a clear oval, a little flattened from side to side, its round aboral end (with the statocyst, its
  balance organ, a bright dot at its tip) behind.
- THE LOBES: its front half splits into two broad oral lobes, one above and one below, like two cupped hands round
  the mouth, which lies deep in the cleft between them. One closed shell: the outer skin runs from the aboral end
  over the body and out to the lobes' edges, rounds the edges, and comes back as the inner skin of the lobes to the
  mouth.
- THE COMB ROWS: eight rows running its length, two in each quarter, raised a little: the four nearest the lobes
  run out onto them, the four at the sides stop short. Each row is a line of comb plates (drawn by the shader) that
  beat in waves and scatter running rainbow light. No tentacles (lobate comb jellies have only small ones, and none
  that sting).

IT SWIMS MOUTH FIRST, as these do: the lobes' edges are ahead (-Z), the aboral end behind (+Z), the lobes above and
below (+Y and -Y), its flatter sides to +X and -X. Its origin is on its middle line half way along its length: the
lobes' front edges 0.05 m ahead of it, the aboral end 0.05 m behind.

What a point is, for the shader: UV2.y the part (0 the outer skin, 1 the inner skin of the lobes, round their edges
to the mouth). UV2.x how much of a comb row's ridge the point is on (0..1, the full model's ridges). UV.y how far
along it is: 0 the aboral end .. 1 the lobes' edge (outer skin), then 1 .. 2 back down the inside to the mouth. UV.x
round it (0..1, the top of it 0). (The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.)

The numbers marked "as the shader has it" are in comb_jelly.gdshader too: change one, change the other.
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

LENGTH = 0.1
TAU = math.tau
OUTER, INNER = 0, 1

# As the shader has it: its half width (to the sides, X) and half height (to the lobes, Y) at its widest.
RX = 0.0185
RY = 0.0265
# The outline seen from the side: (z, how wide it is there, 1 at its widest), from the aboral end forward.
OUTLINE = [(0.05, 0.0), (0.0495, 0.2), (0.048, 0.36), (0.0445, 0.55), (0.038, 0.74), (0.028, 0.89), (0.016, 0.975),
           (0.004, 1.0), (-0.008, 0.995), (-0.02, 0.985), (-0.032, 0.96), (-0.042, 0.915), (-0.05, 0.84)]
# The lobes' edges: how far forward the edge is (z) at the lobes' middles (above and below) and in the cleft at the
# sides; the mouth (as the shader has it).
LOBE_FRONT = -0.05
CLEFT = -0.012
Z_MOUTH = -0.006
# The lobes' thickness at their edges, as a share of the radius there, and how it grows towards the mouth.
THICK = 0.13
# As the shader has it: the comb rows, two in each quarter (radians round from the top), how far along each runs.
ROWS = [math.pi / 8.0 + k * math.pi / 4.0 for k in range(8)]
ROW_FROM = 0.1
RIDGE = 0.0009
RIDGE_WIDE = 0.0011

GAME = "game"


def pick(low, full, game, lo):
    return game if low is GAME else (lo if low else full)


def to_b(p):
    return Vector((p.x, -p.z, p.y))


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def _slopes(xs, ys):
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


_ZS = [-p[0] for p in OUTLINE]
_WS = [p[1] for p in OUTLINE]
_MS = _slopes(_ZS, _WS)


def wide(z):
    """How wide it is at `z` (1 at its widest)."""
    x = max(_ZS[0], min(_ZS[-1], -z))
    i = 0
    while i < len(_ZS) - 2 and x > _ZS[i + 1]:
        i += 1
    h = _ZS[i + 1] - _ZS[i]
    t = (x - _ZS[i]) / h
    a = (2 * t ** 3 - 3 * t ** 2 + 1) * _WS[i] + (t ** 3 - 2 * t ** 2 + t) * h * _MS[i]
    b = (-2 * t ** 3 + 3 * t ** 2) * _WS[i + 1] + (t ** 3 - t ** 2) * h * _MS[i + 1]
    return max(a + b, 0.0)


def rim_z(a):
    """How far forward the lobes' edge is at angle `a` round it (0 the top)."""
    c = abs(math.cos(a))
    # (the lobes broad and round in front, falling back steeply into the cleft at the sides)
    return CLEFT + (LOBE_FRONT - CLEFT) * (1.0 - (1.0 - c) ** 4.0)


def row_off(a):
    """Radians from `a` to the nearest comb row."""
    return (a % (math.pi / 4.0)) - math.pi / 8.0


def row_reach(a):
    """How far along the row nearest `a` runs (as a share of the way to the lobes' edge)."""
    near = a - row_off(a)
    return 0.93 if abs(math.cos(near)) > 0.5 else 0.68


def ridge(a, s, z):
    w = wide(z)
    across = row_off(a) * w * 0.5 * (RX + RY)
    along = smooth(ROW_FROM - 0.04, ROW_FROM + 0.02, s) * (1.0 - smooth(row_reach(a) - 0.06, row_reach(a), s))
    return math.exp(-(across / RIDGE_WIDE) ** 2) * along


def outer_point(a, s, ridged):
    """A point of the outer skin at angle `a` round it and `s` along it (0 the aboral end, 1 the lobes' edge)."""
    z = 0.05 + (rim_z(a) - 0.05) * s
    w = wide(z)
    p = Vector((math.sin(a) * w * RX, math.cos(a) * w * RY, z))
    if ridged:
        n = Vector((math.sin(a) / RX, math.cos(a) / RY, 0.0)).normalized()
        k = ridge(a, s, z)
        p += n * (RIDGE * k)
        return p, k
    return p, 0.0


def inner_point(a, v):
    """A point of the inner skin of the lobes at `a`, `v` of the way from the lobes' edge (0) in to the mouth (1)."""
    z = rim_z(a) + (Z_MOUTH - rim_z(a)) * v
    w = wide(z) * (1.0 - THICK - 0.2 * v) * (1.0 - v ** 1.6)
    return Vector((math.sin(a) * w * RX, math.cos(a) * w * RY, z))


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.data = []
        self.hint = []
        self.out = []
        self.count = {}
        self.tris = {}

    def add(self, p, uv, part, ridge_k=0.0, hint=None):
        self.verts.append(p)
        self.data.append(((uv[0], 1.0 - uv[1]), (ridge_k, 1.0 - part)))
        self.hint.append(hint if hint is not None else Vector((0.0, 0.0, 0.0)))
        return len(self.verts) - 1

    def face(self, points, out, name):
        ps = [self.verts[i] for i in points]
        n = Vector((0.0, 0.0, 0.0))
        for i in range(len(ps)):
            n += ps[i].cross(ps[(i + 1) % len(ps)])
        if n.length < 1e-18:
            return
        if out is None:
            out = sum((self.hint[i] for i in points), Vector())
        if n.dot(out) < 0.0:
            points = tuple(reversed(points))
        self.faces.append(tuple(points))
        self.out.append((Vector(out), name))
        self.count[name] = self.count.get(name, 0) + 1
        self.tris[name] = self.tris.get(name, 0) + len(points) - 2


def columns(low):
    """The angles round it: crowded towards each comb row in the full model; in the game and low models always one
    at the top and bottom (the lobes' middles: the outline from the side) and at each side (the cleft: from above)."""
    if low is GAME:
        per = [-1.0, -1.0 / 3.0, 1.0 / 3.0]
    elif low:
        return [k * math.pi / 6.0 for k in range(12)]
    else:
        per = [-1.0 + 2.0 * i / 10.0 for i in range(10)]
    out = []
    for k in range(8):
        for q in per:
            w = math.copysign(abs(q) ** 1.5, q) if low is False else q
            out.append(ROWS[k] + w * math.pi / 8.0)
    return out


def outer_rows(low):
    n = pick(low, 56, 11, 5)
    # (closer at the aboral end, where the outline turns)
    return [(i / n) ** pick(low, 1.2, 1.6, 1.5) for i in range(n + 1)]


def inner_rows(low):
    n = pick(low, 16, 3, 2)
    return [(i / n) for i in range(n + 1)]


def body(m, low):
    angles = columns(low)
    around = len(angles)
    ridged = low is False
    top = m.add(Vector((0.0, 0.0, 0.05)), (0.0, 0.0), OUTER, 0.0, Vector((0.0, 0.0, 1.0)))
    grid = []
    for c, a in enumerate(angles):
        u = c / around
        col = []
        for s in outer_rows(low)[1:]:
            p, k = outer_point(a, s, ridged)
            col.append(m.add(p, (u, s), OUTER, k, Vector((p.x / RX ** 2, p.y / RY ** 2, (p.z - 0.0) / 0.05 ** 2))))
        # the lobes' edge, rounded over from the outer skin to the inner
        o, _ = outer_point(a, 1.0, False)
        i = inner_point(a, 0.0)
        e = 0.0002
        ahead = (outer_point(a, 1.0, False)[0] - outer_point(a, 1.0 - e, False)[0]).normalized()
        p = (o + i) * 0.5 + ahead * ((o - i).length * 0.45)
        col.append(m.add(p, (u, 1.0), INNER, 0.0, ahead))
        for v in inner_rows(low)[:-1]:
            p = inner_point(a, v)
            # (the inner skin faces into the hollow between the lobes)
            col.append(m.add(p, (u, 1.0 + v), INNER, 0.0, Vector((-p.x / RX ** 2, -p.y / RY ** 2, -0.2 / 0.05))))
        grid.append(col)
    mouth = m.add(Vector((0.0, 0.0, Z_MOUTH)), (0.0, 2.0), INNER, 0.0, Vector((0.0, 0.0, -1.0)))
    rows = len(grid[0])
    for c in range(around):
        n = (c + 1) % around
        m.face((top, grid[c][0], grid[n][0]), Vector((0.0, 0.0, 1.0)), "outer skin")
        for r in range(rows - 1):
            quad = (grid[c][r], grid[n][r], grid[n][r + 1], grid[c][r + 1])
            part = round(1.0 - m.data[grid[c][r + 1]][1][1])
            m.face(quad, None, "outer skin" if part == OUTER else "lobes' edges and inner skin")
        m.face((mouth, grid[c][-1], grid[n][-1]), Vector((0.0, 0.0, -1.0)), "lobes' edges and inner skin")


def material_of(name, colour):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = colour
    material.diffuse_color = colour
    return material


def make(name, low):
    m = Mesh()
    body(m, low)
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
    mesh.materials.append(material_of("comb_jelly", (0.75, 0.85, 0.9, 1.0)))
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
    scene.render.resolution_x, scene.render.resolution_y = 1000, 800
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    views = [("left", (1, 0, 0), 0.13), ("top", (0.001, 0, 1), 0.13), ("front", (0, 1, 0), 0.13),
             ("back", (0, -1, 0), 0.13), ("quarter", (0.7, 0.6, 0.4), 0.13)]
    for prefix, obj in (("", made[0]), ("game_", made[1]), ("lo_", made[2])):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, frame in views:
            offset = Vector(direction).normalized() * 40.0
            camera.data.ortho_scale = frame
            camera.location = offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % (prefix, view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    full = make("comb_jelly", False)
    game = make("comb_jelly_game", GAME)
    low = make("comb_jelly_lo", True)
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, "comb_jelly.glb"))
    export_one(game, os.path.join(OUT, "comb_jelly_game.glb"))
    export_one(low, os.path.join(OUT, "comb_jelly_lo.glb"))
    game.location.x = 0.06
    low.location.x = 0.12
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "comb_jelly.blend"))
    game.location.x = 0.0
    low.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, game, low])


if __name__ == "__main__":
    main()
