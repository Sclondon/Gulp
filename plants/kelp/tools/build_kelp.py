"""Builds the giant kelp's pieces (Macrocystis pyrifera) and saves them:

    blender --background --python plants/kelp/tools/build_kelp.py

run from a game's root (or GameCommon's godot/kelp/files). It writes, beside this file's folder:

    ../models/kelp_a.glb, kelp_b.glb, kelp_c.glb   one metre of a frond bundle each (three variants)
    ../models/kelp_lo.glb                           the same metre, very light, for far off
    ../models/kelp_holdfast.glb                     the holdfast (the root-like mound on the rock)
    kelp.blend                                      all five, side by side, to edit

and prints a WINDING line for each (the check that nothing is inside out).

WHAT A PIECE IS. Giant kelp is a holdfast, a bundle of rope-like stipes rising from it, and blades all the way
up each stipe, each blade on a small gas float (a pneumatocyst). A piece here is ONE METRE of that bundle:

- THREE STIPES, thin three-sided tubes open at both ends. Each begins and ends at the same three points (0.06 m
  from the middle line, a third of a turn apart) and wanders between, so that pieces stacked on each other,
  turned by any number of thirds of a turn, join stipe to stipe.
- TWELVE BLADES up the metre, four on each stipe, each on a float: the float a small three-sided pear (four
  triangles), pointed at the stipe; the blade a long narrow leaf (0.5 to 0.8 m long, 0.12 to 0.17 m wide),
  widest near the middle, running to a point, held out and up from the stipe and drooping towards its tip,
  its edges ruffled. Each is ONE SHEET (no thickness): kelp.gdshader draws both of its sides, cuts its
  toothed edge and draws its crinkles.

The low piece has the same twelve blades as two triangles each, the stipes as flat ribbons, no floats.

In Godot: +Y is up the frond, the piece stands on y = 0 and reaches y = 1 (blades reach a little past both), its
middle line is the Y axis.

WHAT EACH POINT TELLS THE SHADER:
    UV   on a blade: x across it (0 one edge, 1 the other), y along it (0 at the float, 1 at its tip)
    UV2  x: what it is (0 stipe or holdfast, 1 float, 2 blade); y: a number of its own for each blade (0 to 1)
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

STIPE_AT = 0.06       # how far the stipes' ends are from the middle line
STIPE_RADIUS = 0.011
BLADES = 12
UP = Vector((0.0, 1.0, 0.0))
STIPE, FLOAT, BLADE = 0.0, 1.0, 2.0


class Mesh:
    """Points in Godot's axes (+Y up), faces wound to face the way they are told to."""

    def __init__(self):
        self.verts = []
        self.faces = []      # (indices, uvs, uv2)
        self.told = []       # the way each face was told to face
        self.closed = []     # whether it is part of a closed skin (must face outward)

    def dab(self, p):
        self.verts.append(Vector(p))
        return len(self.verts) - 1

    def face(self, idx, out, uvs, uv2, closed):
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
        self.closed.append(closed)


def stipe_path(k, rng, straight=False):
    """Where stipe k (0..2) is at each height: its ends fixed, its middle wandering."""
    angle = TAU * (0.25 + k / 3.0)
    end = Vector((math.cos(angle) * STIPE_AT, 0.0, math.sin(angle) * STIPE_AT))
    wander = Vector((rng.uniform(-0.025, 0.025), 0.0, rng.uniform(-0.025, 0.025)))
    if straight:
        wander = Vector((0.0, 0.0, 0.0))

    def at(y):
        bow = math.sin(max(0.0, min(1.0, y)) * math.pi)
        return Vector((end.x + wander.x * bow, y, end.z + wander.z * bow))
    return at


def make_stipe(m, at):
    rings = []
    for y in (0.0, 0.5, 1.0):
        here = at(y)
        along = (at(y + 0.05) - at(y - 0.05)).normalized()
        side = along.cross(Vector((1.0, 0.0, 0.0))).normalized()
        other = along.cross(side).normalized()
        ring = []
        for c in range(3):
            a = TAU * c / 3.0
            ring.append(m.dab(here + (side * math.cos(a) + other * math.sin(a)) * STIPE_RADIUS))
        rings.append((here, ring))
    for r in range(2):
        for c in range(3):
            n = (c + 1) % 3
            quad = (rings[r][1][c], rings[r][1][n], rings[r + 1][1][n], rings[r + 1][1][c])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            axis = (rings[r][0] + rings[r + 1][0]) * 0.5
            m.face(quad, middle - axis, [(0.5, 0.5)] * 4, (STIPE, 0.0), True)


def make_stipe_ribbon(m, at, k):
    """The low piece's stipe: one flat strip, facing out from the middle line."""
    angle = TAU * (0.25 + k / 3.0)
    across = Vector((-math.sin(angle), 0.0, math.cos(angle))) * STIPE_RADIUS * 1.6
    quad = [m.dab(at(0.0) - across), m.dab(at(0.0) + across), m.dab(at(1.0) + across), m.dab(at(1.0) - across)]
    m.face(quad, Vector((math.cos(angle), 0.0, math.sin(angle))), [(0.5, 0.5)] * 4, (STIPE, 0.0), False)


def blade_plan(rng, variant):
    """Where each blade grows and how it is held: the same for a variant's full and low pieces."""
    plans = []
    order = [k % 3 for k in range(BLADES)]
    rng.shuffle(order)
    for i in range(BLADES):
        k = order[i]
        plans.append({
            "stipe": k,
            "y": (i + 0.5) / BLADES + rng.uniform(-0.025, 0.025),
            "turn": TAU * (0.25 + k / 3.0) + rng.uniform(-1.1, 1.1),
            "tilt": math.radians(rng.uniform(26.0, 58.0)),     # from straight up
            "long": rng.uniform(0.5, 0.8),
            "wide": rng.uniform(0.12, 0.17),
            "droop": rng.uniform(0.5, 1.1),
            "twist": rng.uniform(-0.5, 0.5),
            "own": (i + rng.uniform(0.1, 0.9)) / BLADES,
        })
    return plans


def blade_frame(plan, stipes):
    foot = stipes[plan["stipe"]](plan["y"])
    out = Vector((math.cos(plan["turn"]), 0.0, math.sin(plan["turn"])))
    along = (out * math.sin(plan["tilt"]) + UP * math.cos(plan["tilt"])).normalized()
    return foot, out, along


def make_float(m, plan, stipes):
    foot, out, along = blade_frame(plan, stipes)
    side = along.cross(UP).normalized()
    other = side.cross(along).normalized()
    start = foot + along * 0.006
    belly = foot + along * 0.06
    end = foot + along * 0.075
    # (a three-sided pear: a point at the stipe, a flat end at the blade's foot; four triangles)
    ring = []
    for c in range(3):
        a = TAU * c / 3.0 + 0.5
        ring.append(m.dab(belly + (side * math.cos(a) + other * math.sin(a)) * 0.02))
    tip = m.dab(start)
    middle_of = foot + along * 0.045
    for c in range(3):
        n = (c + 1) % 3
        tri = (tip, ring[c], ring[n])
        middle = sum((m.verts[q] for q in tri), Vector()) / 3.0
        m.face(tri, middle - middle_of, [(0.5, 0.5)] * 3, (FLOAT, plan["own"]), True)
    m.face((ring[0], ring[1], ring[2]), along, [(0.5, 0.5)] * 3, (FLOAT, plan["own"]), True)
    return end


# How far along a blade each cross-section is, and how wide there (of its full width).
FULL_SECTIONS = ((0.0, 0.26), (0.18, 0.86), (0.45, 1.0), (0.75, 0.62))
LOW_SECTIONS = ((0.0, 0.0), (0.4, 1.0))


def make_blade(m, plan, stipes, sections, ruffle):
    foot, out, along0 = blade_frame(plan, stipes)
    start = foot + along0 * 0.07
    side0 = along0.cross(UP).normalized()

    def centre(v):
        # (it droops towards its tip: its line turns down as it goes)
        steps = 12
        p = start.copy()
        n = max(1, math.ceil(v * steps))
        for s in range(n):
            tilt = plan["tilt"] + plan["droop"] * (s + 0.5) * v / n
            d = out * math.sin(tilt) + UP * math.cos(tilt)
            p += d * plan["long"] * v / n
        tilt = plan["tilt"] + plan["droop"] * v
        return p, (out * math.sin(tilt) + UP * math.cos(tilt)).normalized()

    pairs = []
    for row, (v, w) in enumerate(sections):
        p, along = centre(v)
        twist = plan["twist"] * v
        face_up = side0.cross(along).normalized()
        if face_up.y < 0.0:
            face_up = -face_up
        across = (side0 * math.cos(twist) + face_up * math.sin(twist)).normalized()
        normal = across.cross(along).normalized()
        if normal.y < 0.0:
            normal = -normal
        half = plan["wide"] * 0.5 * w
        lift = ruffle * (1.0 if row % 2 else -1.0) * (0.4 + 0.6 * v)
        if half <= 0.0:
            left = right = m.dab(p)       # (a blade that starts at a point)
        else:
            left = m.dab(p - across * half + normal * lift)
            right = m.dab(p + across * half - normal * lift)
        pairs.append((left, right, v, normal))
    p, along = centre(1.0)
    tip = m.dab(p)
    uv2 = (BLADE, plan["own"])
    for r in range(len(pairs) - 1):
        a, b = pairs[r], pairs[r + 1]
        if a[0] == a[1]:
            m.face((a[0], b[1], b[0]), a[3] + b[3], [(0.5, a[2]), (1.0, b[2]), (0.0, b[2])], uv2, False)
            continue
        m.face((a[0], a[1], b[1], b[0]), a[3] + b[3], [(0.0, a[2]), (1.0, a[2]), (1.0, b[2]), (0.0, b[2])], uv2, False)
    last = pairs[-1]
    m.face((last[0], last[1], tip), last[3], [(0.0, last[2]), (1.0, last[2]), (0.5, 1.0)], uv2, False)


def make_piece(seed, low=False):
    rng = random.Random(seed)
    m = Mesh()
    stipes = [stipe_path(k, rng, low) for k in range(3)]
    plans = blade_plan(rng, seed)
    for k in range(3):
        if low:
            make_stipe_ribbon(m, stipes[k], k)
        else:
            make_stipe(m, stipes[k])
    for plan in plans:
        if not low:
            make_float(m, plan, stipes)
        make_blade(m, plan, stipes, LOW_SECTIONS if low else FULL_SECTIONS, 0.0 if low else 0.009)
    return m


def make_holdfast():
    """A mound of haptera: a short cone the stipes rise out of, and root-like fingers arcing out and down."""
    rng = random.Random(11)
    m = Mesh()
    tag = (STIPE, 0.0)
    levels = ((0.0, 0.15), (0.14, 0.10), (0.30, 0.045))
    rings = []
    for y, r in levels:
        rings.append([m.dab((math.cos(TAU * c / 6.0) * r, y, math.sin(TAU * c / 6.0) * r)) for c in range(6)])
    for r in range(2):
        for c in range(6):
            n = (c + 1) % 6
            quad = (rings[r][c], rings[r][n], rings[r + 1][n], rings[r + 1][c])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((middle.x, 0.25, middle.z)), [(0.5, 0.5)] * 4, tag, True)
    top = m.dab((0.0, 0.32, 0.0))
    for c in range(6):
        m.face((top, rings[2][c], rings[2][(c + 1) % 6]), UP, [(0.5, 0.5)] * 3, tag, True)
    fingers = 14
    for f in range(fingers):
        a = TAU * (f + rng.uniform(-0.35, 0.35)) / fingers
        out = Vector((math.cos(a), 0.0, math.sin(a)))
        high = rng.uniform(0.05, 0.22)
        reach = rng.uniform(0.15, 0.27)
        thick = rng.uniform(0.026, 0.04)
        # (from inside the cone, out, and down into the rock)
        points = (out * 0.04 + UP * high, out * (reach * 0.6) + UP * (high * 0.75 + 0.03), out * reach + UP * -0.02)
        side = out.cross(UP).normalized()
        ring_sets = []
        for i in range(2):
            along = (points[i + 1] - points[i]).normalized()
            other = side.cross(along).normalized()
            radius = thick * (1.0 - 0.3 * i)
            ring_sets.append([m.dab(points[i] + (side * math.cos(TAU * c / 3.0) + other * math.sin(TAU * c / 3.0)) * radius) for c in range(3)])
        for c in range(3):
            n = (c + 1) % 3
            quad = (ring_sets[0][c], ring_sets[0][n], ring_sets[1][n], ring_sets[1][c])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, middle - (points[0] + points[1]) * 0.5, [(0.5, 0.5)] * 4, tag, True)
        tip = m.dab(points[2])
        for c in range(3):
            tri = (ring_sets[1][c], ring_sets[1][(c + 1) % 3], tip)
            middle = sum((m.verts[q] for q in tri), Vector()) / 3.0
            m.face(tri, middle - (points[1] + points[2]) * 0.5, [(0.5, 0.5)] * 3, tag, True)
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
    mesh = obj.data
    wrong = 0
    triangles = 0
    for poly, told in zip(mesh.polygons, m.told):
        n = poly.normal
        back = Vector((n.x, n.z, -n.y))
        triangles += len(poly.vertices) - 2
        if back.dot(told) <= 0.0:
            wrong += 1
    sheets = sum(1 for c in m.closed if not c)
    print("WINDING %s: %s: %d of %d faces against the way they were told to face (%d of them two-sided sheets), %d triangles"
          % (name, "ok" if wrong == 0 else "INSIDE OUT", wrong, len(mesh.polygons), sheets, triangles))


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
        ("kelp_a", make_piece(1)),
        ("kelp_b", make_piece(2)),
        ("kelp_c", make_piece(3)),
        ("kelp_lo", make_piece(1, True)),
        ("kelp_holdfast", make_holdfast()),
    ]
    objects = []
    for name, m in made:
        obj = to_object(name, m)
        winding(name, m, obj)
        export_one(obj, os.path.join(MODELS, name + ".glb"))
        objects.append(obj)
    for i, obj in enumerate(objects):
        obj.location.x = i * 1.6
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "kelp.blend"))
    print("BUILT kelp")


if __name__ == "__main__":
    main()
