"""Builds eelgrass tufts (Zostera marina) and saves them:

    blender --background --python plants/sea_grass/tools/build_sea_grass.py

run from a game's root (or GameCommon's godot/sea-grass/files). It writes, beside this file's folder:

    ../models/sea_grass_a.glb, sea_grass_b.glb, sea_grass_c.glb   one tuft each (three variants)
    ../models/sea_grass_lo.glb                                    tuft a, very light, for far off
    sea_grass.blend                                               all four, side by side, to edit

and prints a WINDING line for each (the check that nothing is inside out).

WHAT A TUFT IS. Eelgrass grows as shoots from a creeping root: each shoot a short sheath with three to five
long, flat, ribbon-like leaves with rounded tips. A tuft here is two to four shoots a few centimetres apart, ten
to twelve leaves in all, the tallest reaching y = 1 (the bed scales each tuft to its height). Each leaf leans out
a little from its shoot, curves gently over, and twists a little along its length, as ribbons do. Each is ONE
SHEET (no thickness): sea_grass.gdshader draws both of its sides.

In Godot: +Y is up, the tuft stands on y = 0 round the Y axis.

WHAT EACH POINT TELLS THE SHADER:
    UV   x across the leaf (0 one edge, 1 the other), y along it (0 at its foot, 1 at its tip)
    UV2  x: a number of the leaf's own (0 to 1); y: how long the leaf is, of the tallest (0 to 1)
(The glTF exporter writes a UV's y as 1 - y; this script writes 1 - y, so that Godot reads y.)
"""
import math
import os
import random

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(HERE, "..", "models")
TAU = math.tau
UP = Vector((0.0, 1.0, 0.0))


class Mesh:
    """Points in Godot's axes (+Y up), faces wound to face the way they are told to."""

    def __init__(self):
        self.verts = []
        self.faces = []      # (indices, uvs, uv2)
        self.told = []

    def dab(self, p):
        self.verts.append(Vector(p))
        return len(self.verts) - 1

    def face(self, idx, out, uvs, uv2):
        idx = list(idx)
        uvs = list(uvs)
        a, b, c = (self.verts[i] for i in idx[:3])
        n = (b - a).cross(c - a)
        if len(idx) == 4:
            n += (self.verts[idx[2]] - a).cross(self.verts[idx[3]] - a)
        if n.dot(out) < 0.0:
            idx.reverse()
            uvs.reverse()
        self.faces.append((idx, uvs, uv2))
        self.told.append(Vector(out))


# How far along a leaf each cross-section is, and how wide there (of its full width). The last ones round its tip.
FULL_ROWS = ((0.0, 0.8), (0.3, 1.0), (0.62, 1.0), (0.88, 0.94), (0.97, 0.62))
LOW_ROWS = ((0.0, 0.8), (0.9, 0.9))


def leaf_plans(seed):
    rng = random.Random(seed)
    plans = []
    shoots = rng.randint(2, 4)
    leaves = 0
    for s in range(shoots):
        a = TAU * (s + rng.uniform(-0.3, 0.3)) / shoots
        foot = Vector((math.cos(a), 0.0, math.sin(a))) * rng.uniform(0.012, 0.04) if shoots > 1 else Vector()
        n = rng.randint(3, 5)
        if leaves + n > 12:
            n = max(12 - leaves, 2)
        heading = rng.uniform(0.0, TAU)
        for k in range(n):
            # (a shoot's leaves come out of its sheath as a flat fan, the inner ones longest)
            fan = (k - (n - 1) * 0.5) / max(n - 1, 1)
            turn = heading + fan * rng.uniform(0.5, 0.9)
            plans.append({
                "foot": foot.copy(),
                "out": Vector((math.cos(turn), 0.0, math.sin(turn))),
                "lean": math.radians(rng.uniform(3.0, 14.0) + abs(fan) * 10.0),
                "bow": math.radians(rng.uniform(20.0, 55.0)),          # how far it curves over by its tip
                "long": rng.uniform(0.55, 1.0) * (1.0 - 0.25 * abs(fan)),
                "wide": rng.uniform(0.022, 0.03),
                "twist": rng.uniform(-0.8, 0.8),
                "own": rng.random(),
            })
        leaves += n
    tallest = max(p["long"] for p in plans)
    for p in plans:
        p["long"] /= tallest
    return plans


def make_leaf(m, plan, rows):
    steps = 16

    def centre(v):
        p = plan["foot"].copy()
        n = max(1, math.ceil(v * steps))
        for s in range(n):
            tilt = plan["lean"] + plan["bow"] * ((s + 0.5) * v / n) ** 1.5
            p += (plan["out"] * math.sin(tilt) + UP * math.cos(tilt)) * plan["long"] * v / n
        tilt = plan["lean"] + plan["bow"] * v ** 1.5
        return p, (plan["out"] * math.sin(tilt) + UP * math.cos(tilt)).normalized()

    side0 = plan["out"].cross(UP).normalized()
    pairs = []
    for v, w in rows:
        p, along = centre(v)
        twist = plan["twist"] * v
        flat_out = along.cross(side0).normalized()
        across = (side0 * math.cos(twist) + flat_out * math.sin(twist)).normalized()
        normal = across.cross(along).normalized()
        if normal.dot(plan["out"]) < 0.0:
            normal = -normal
        half = plan["wide"] * 0.5 * w
        pairs.append((m.dab(p - across * half), m.dab(p + across * half), v, normal))
    p, along = centre(1.0)
    tip = m.dab(p)
    uv2 = (plan["own"], plan["long"])
    for r in range(len(pairs) - 1):
        a, b = pairs[r], pairs[r + 1]
        m.face((a[0], a[1], b[1], b[0]), a[3] + b[3], [(0.0, a[2]), (1.0, a[2]), (1.0, b[2]), (0.0, b[2])], uv2)
    last = pairs[-1]
    m.face((last[0], last[1], tip), last[3], [(0.0, last[2]), (1.0, last[2]), (0.5, 1.0)], uv2)


def make_tuft(seed, low=False):
    m = Mesh()
    for plan in leaf_plans(seed):
        make_leaf(m, plan, LOW_ROWS if low else FULL_ROWS)
    return m


def to_blender(p):
    """Godot (x, y up, z) to Blender (x, y, z up): the glTF exporter turns it back."""
    return (p.x, -p.z, p.y)


def to_object(name, m):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_blender(v) for v in m.verts], [], [f[0] for f in m.faces])
    mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.new(name="UV2")
    first = mesh.uv_layers["UVMap"]
    second = mesh.uv_layers["UV2"]
    for poly, (idx, uvs, uv2) in zip(mesh.polygons, m.faces):
        for corner, loop in enumerate(poly.loop_indices):
            first.data[loop].uv = (uvs[corner][0], 1.0 - uvs[corner][1])
            second.data[loop].uv = (uv2[0], 1.0 - uv2[1])
        poly.use_smooth = True
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def winding(name, m, obj):
    """Every face as Blender holds it against the way it was told to face."""
    wrong = 0
    triangles = 0
    for poly, told in zip(obj.data.polygons, m.told):
        n = poly.normal
        back = Vector((n.x, n.z, -n.y))
        triangles += len(poly.vertices) - 2
        if back.dot(told) <= 0.0:
            wrong += 1
    print("WINDING %s: %s: %d of %d faces against the way they were told to face (all two-sided sheets), %d triangles"
          % (name, "ok" if wrong == 0 else "INSIDE OUT", wrong, len(obj.data.polygons), triangles))


def export_one(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", export_yup=True, use_selection=True,
        export_animations=False, export_texcoords=True, export_normals=True,
        export_materials="NONE", export_vertex_color="NONE",
    )


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    os.makedirs(MODELS, exist_ok=True)
    made = [
        ("sea_grass_a", make_tuft(4)),
        ("sea_grass_b", make_tuft(7)),
        ("sea_grass_c", make_tuft(12)),
        ("sea_grass_lo", make_tuft(4, True)),
    ]
    objects = []
    for name, m in made:
        obj = to_object(name, m)
        winding(name, m, obj)
        export_one(obj, os.path.join(MODELS, name + ".glb"))
        objects.append(obj)
    for i, obj in enumerate(objects):
        obj.location.x = i * 0.6
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "sea_grass.blend"))
    print("BUILT sea_grass")


if __name__ == "__main__":
    main()
