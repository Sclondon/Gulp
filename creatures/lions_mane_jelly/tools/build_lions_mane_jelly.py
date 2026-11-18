"""Builds the lion's mane jelly (creatures/lions_mane_jelly) and exports it for Godot.

Run from the game's root (or anywhere: paths are from this file):
    blender --background --python creatures/lions_mane_jelly/tools/build_lions_mane_jelly.py

Writes creatures/lions_mane_jelly/models/lions_mane_jelly.glb (the full model), lions_mane_jelly_game.glb (the
game model, at Twilight Princess weight) and lions_mane_jelly_lo.glb (far off, crowds, phones: its strands are
not laid along ropes), and the editable creatures/lions_mane_jelly/tools/lions_mane_jelly.blend (all three; this
folder has a .gdignore). Each is one static mesh in two surfaces; the shaders beat the bell and lay the strands
along their ropes. It prints a BUILT line (triangles) and a WINDING line (nothing inside out) for each.

A lion's mane jelly (Cyanea capillata), not life size for the biggest (they reach 2 m) but big: the bell 1.5 m
across and 0.3 m high, broad and flattish, cut into eight lobes, each lobe's rim scalloped in four, rust at the
crown and deep gold out to the lobes. Under it eight clusters of very many fine tentacles (the mane), each cluster
rooted in a horseshoe under its lobe and drawn as many thin lines that follow one rope; in the middle four big
folded, frilly curtains of oral arms.

Everything here is in Godot space (metres, Y up) until it is written out. The origin is the middle of the bell's
rim (the rim at rest lies in y = 0); up is +Y. A jelly has no front: -Z is only where the build starts.

What a point is, for the shaders:
- vertex colour red: the part. 0 the top of the bell, 0.25 its underside (and the lip and the stalk under it),
  0.5 an oral arm (a sheet), 0.75 a tentacle of the mane (a line).
- green: on a line, half its width / LINE_SCALE (the shader draws it that wide, turned to face the camera).
- blue: on a strand, which rope it follows ((row + 0.5) / 32: the arms 0 to 3, the clusters 4 to 11, as
  LionsManeJelly.strands() lists them).
- alpha: on a strand, how far along its rope it reaches (1 the whole rope; a shorter tentacle less).
- UV.x: across a sheet or line (0..1); on the bell, round it (0..1). UV.y: on a strand, how far along its ROPE
  (0 root .. alpha); on the bell, 0 the crown to 1 the rim.
- UV2.x: the length of the strand's rope (metres); UV2.y: a number of its own (0..1) for sway and colour.
(The glTF writer flips V: what is written is 1 - v, so that Godot reads v.)

The ropes' roots, lengths and phases are in LionsManeJelly.strands() too: change one, change the other.
Each strand's points are laid in the model hanging straight down from its rope's root at rest; the shader takes
each point's offset from that line and lays it along the rope.

Surfaces: "lions_mane_strands" (drawn first: arms and tentacles) and "lions_mane_bell" (the underside, then the
top; LionsManeJelly puts its triangles in that order when it loads it).
"""

import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "models")

# Kept in step with lions_mane_jelly.gd and the shaders.
RADIUS = 0.75
HEIGHT = 0.22
LOBES = 8
ARMS = 4
CLUSTERS = 8
ARM_LONG = 1.4
TENTACLE_LONG = 3.0
ARM_ROOT = Vector((0.0, 0.07, 0.0))
ARM_SPREAD = 0.07
CLUSTER_AT = 0.5
CLUSTER_Y = 0.11
LINE_SCALE = 0.02
# How many tentacles a cluster has in the full model (the game and low models take some of the same).
HAIRS_FULL = 56

SURFACES = ["lions_mane_strands", "lions_mane_bell"]
STRANDS, BELL = 0, 1
TOP, UNDER, ARM, HAIR = 0.0, 0.25, 0.5, 0.75
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


def arm_strand(k):
    a = math.pi * 0.25 + k * math.pi * 0.5
    root = ARM_ROOT + Vector((math.cos(a) * ARM_SPREAD, 0.0, math.sin(a) * ARM_SPREAD))
    return root, ARM_LONG * (1.0 + 0.08 * math.sin(k * 2.1 + 0.4)), fract(k * 0.37 + 0.11), a


def cluster_strand(k):
    a = (k + 0.5) * TAU / CLUSTERS
    root = Vector((math.cos(a) * RADIUS * CLUSTER_AT, CLUSTER_Y, math.sin(a) * RADIUS * CLUSTER_AT))
    return root, TENTACLE_LONG * (1.0 + 0.08 * math.sin(k * 2.3 + 1.0)), fract(k * 0.618), a


class Mesh:
    def __init__(self):
        self.verts = []
        self.data = []
        self.faces = []
        self.surface = []
        # per face: the way it should face (Godot space), or None for a two-sided sheet or line
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
                a = self.verts[ids[i]]
                b = self.verts[ids[(i + 1) % len(ids)]]
                n += a.cross(b)
            if n.dot(want) < 0.0:
                ids = tuple(reversed(ids))
        self.faces.append(ids)
        self.surface.append(surface)
        self.want.append(want)


def lobe_of(a):
    """Where `a` (round the bell) is across its lobe: 0 at one cleft, 0.5 the lobe's middle, 1 the next cleft."""
    return fract(a * LOBES / TAU)


def bell_point(v, a, inner):
    """A point of the bell: `v` 0 at the crown to 1 at the rim, `a` the angle round it."""
    phi = v * math.pi * 0.5
    rad = RADIUS * math.sin(phi) ** 0.8
    y = HEIGHT * math.cos(phi) ** 1.1
    x = lobe_of(a)
    # 1 in a cleft between two lobes, 0 across the lobe
    cleft = smooth(0.36, 0.5, abs(x - 0.5))
    # four scallops on each lobe's rim
    scallop = abs(math.sin(x * math.pi * 4.0))
    rim = smooth(0.7, 1.0, v)
    rad *= 1.0 - 0.11 * cleft * rim
    rad += RADIUS * 0.016 * (scallop - 0.6) * smooth(0.92, 1.0, v) * (1.0 - cleft)
    # each lobe swells a little and droops at its rim
    y += 0.018 * math.sin(x * math.pi) * smooth(0.45, 0.85, v) * (1.0 - rim)
    y -= 0.05 * rim * rim * (1.0 - cleft)
    y -= 0.012 * (1.0 - scallop) * smooth(0.92, 1.0, v)
    if inner:
        rad *= 0.955
        y = y * 0.5 - 0.01 * (1.0 - rim)
    return Vector((math.cos(a) * rad, y, math.sin(a) * rad))


def under_y(r, a):
    """How high the underside is `r` from the middle, at angle `a` (found by halving)."""
    lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = (lo + hi) * 0.5
        p = bell_point(mid, a, True)
        if math.hypot(p.x, p.z) < r:
            lo = mid
        else:
            hi = mid
    return bell_point(lo, a, True).y


def bell(m, around, rings_top, rings_under, under_around):
    middle = Vector((0.0, -0.4, 0.0))
    grids = {}
    for name, inner, rings, code, count in (("top", False, rings_top, TOP, around), ("under", True, rings_under, UNDER, under_around)):
        grid = []
        for r in range(rings + 1):
            # (more rings towards the rim, where the lobes are cut)
            v = (r / rings) ** 0.75
            row = []
            for c in range(count + 1):
                a = c / count * TAU
                row.append(m.add(bell_point(v, a, inner), (c / count, v), (0.0, 0.0), (code, 0.0, 0.0, 1.0)))
            grid.append(row)
        grids[name] = (grid, rings, count)
    # the underside first (it is drawn first), then the lip, then the top
    for name, sign in (("under", -1.0), ("top", 1.0)):
        grid, rings, count = grids[name]
        if name == "top":
            # the lip: the top's edge joined to the underside's (taken at the top's angles)
            lip = []
            for inner in (False, True):
                row = []
                for c in range(around + 1):
                    p = bell_point(1.0, c / around * TAU, inner)
                    row.append(m.add(p, (c / around, 1.0), (0.0, 0.0), (UNDER, 0.0, 0.0, 1.0)))
                lip.append(row)
            for c in range(around):
                p = m.verts[lip[0][c]]
                m.face((lip[0][c], lip[1][c], lip[1][c + 1], lip[0][c + 1]), BELL, Vector((p.x, -0.3, p.z)))
        for r in range(rings):
            for c in range(count):
                ids = (grid[r][c], grid[r][c + 1], grid[r + 1][c + 1], grid[r + 1][c])
                p = sum((m.verts[i] for i in ids), Vector()) * 0.25
                if r == 0:
                    ids = (grid[0][c], grid[1][c + 1], grid[1][c])
                m.face(ids, BELL, (p - middle) * sign)
    # the stalk under the middle, down to where the arms hang from
    stalk = []
    for k, (y, rad) in enumerate(((under_y(0.0, 0.0) + 0.01, 0.1), (0.1, 0.085), (ARM_ROOT.y, ARM_SPREAD + 0.01))):
        row = []
        for c in range(13):
            a = c / 12 * TAU
            row.append(m.add(Vector((math.cos(a) * rad, y, math.sin(a) * rad)), (c / 12, 0.0), (0.0, 0.0), (UNDER, 0.0, 0.0, 1.0)))
        stalk.append(row)
    for r in range(2):
        for c in range(12):
            ids = (stalk[r][c], stalk[r][c + 1], stalk[r + 1][c + 1], stalk[r + 1][c])
            p = sum((m.verts[i] for i in ids), Vector()) * 0.25
            m.face(ids, BELL, Vector((p.x, 0.0, p.z)))


def arm_sheet(m, k, turned, wide, seed, steps, across):
    """One folded, frilled curtain of oral arm `k`, through the arm's middle line, turned `turned` round it."""
    root, long, phase, a = arm_strand(k)
    colour = (ARM, 0.0, (k + 0.5) / 32.0, 1.0)
    rows = []
    for s_i in range(steps + 1):
        t = s_i / steps
        s = t ** 1.2
        arc = s * long
        twist = a + turned + arc * 0.9 + 0.4 * math.sin(arc * 1.3 + seed)
        width = wide * (0.07 + 0.28 * smooth(0.0, 0.2, s) * (1.0 - 0.5 * smooth(0.45, 1.0, s))) * (1.0 + 0.2 * math.sin(arc * 3.1 + seed))
        across_way = Vector((math.cos(twist), 0.0, math.sin(twist)))
        facing = Vector((-math.sin(twist), 0.0, math.cos(twist)))
        row = []
        for w_i in range(across + 1):
            u = w_i / across * 2.0 - 1.0
            e = abs(u)
            side = 1.9 if u > 0.0 else 0.0
            # deep folds like a curtain, finer frills at the edges
            fold = math.sin(arc / 0.22 * TAU + seed + side + u * 1.5)
            frill = math.sin(arc / 0.08 * TAU + seed * 1.7 + side * 1.3)
            out = width * (0.35 * e ** 1.2 * fold + 0.14 * e ** 2.0 * frill) * smooth(0.0, 0.05, s)
            p = root + Vector((0.0, -arc, 0.0)) + across_way * u * width + facing * out
            row.append(m.add(p, ((u + 1.0) * 0.5, s), (long, fract(phase + seed * 0.1)), colour))
        rows.append(row)
    # the top of the sheet runs up into the stalk
    for r in range(len(rows) - 1):
        for w_i in range(across):
            m.face((rows[r][w_i], rows[r][w_i + 1], rows[r + 1][w_i + 1], rows[r + 1][w_i]), STRANDS)


def hairs(m, k, count, steps, thicker):
    """Cluster `k` of the mane: `count` fine tentacles rooted along a horseshoe under its lobe, hanging as one
    shaggy bundle that follows the cluster's rope and spreads out towards its tips."""
    root, long, phase, a = cluster_strand(k)
    row_code = (ARMS + k + 0.5) / 32.0
    for j in range(count):
        t = (j + 0.5) / count
        # (each takes its randomness from the full model's tentacle nearest it, so the models agree)
        jf = min(int(t * HAIRS_FULL), HAIRS_FULL - 1)
        n = k * 97.0 + jf * 13.1
        h1, h2, h3, h4 = hash1(n), hash1(n + 1.7), hash1(n + 3.3), hash1(n + 5.9)
        u = t * 2.0 - 1.0
        ang = a + u * 0.32
        rr = RADIUS * (0.36 + 0.24 * (1.0 - u * u))
        hr = Vector((math.cos(ang) * rr, under_y(rr, ang) - 0.004, math.sin(ang) * rr))
        reach = 0.5 + 0.5 * h1
        hl = long * reach
        # (spread out from the cluster, more outwards than in)
        out = Vector((math.cos(ang), 0.0, math.sin(ang)))
        drift = (Vector((math.cos(h2 * TAU), 0.0, math.sin(h2 * TAU))) + out * 0.6).normalized() * (0.08 + 0.3 * h3)
        base = Vector((hr.x - root.x, 0.0, hr.z - root.z))
        half = (0.0045 + 0.003 * h4) * thicker
        for i in range(steps + 1):
            hs = (i / steps) ** 1.15
            s = hs * reach
            lateral = base * (1.0 - 0.25 * smooth(0.0, 0.45, hs)) + drift * smooth(0.0, 1.0, hs) ** 0.7
            # (shaggy: each waves its own way)
            lateral += Vector((math.sin(hs * hl * 3.1 + h1 * TAU), 0.0, math.cos(hs * hl * 2.7 + h2 * TAU))) * 0.045 * smooth(0.0, 0.25, hs)
            centre = Vector((root.x + lateral.x, hr.y - hs * hl, root.z + lateral.z))
            w = half * (1.0 - 0.55 * hs)
            for side in (0, 1):
                p = centre + Vector(((side * 2 - 1) * w, 0.0, 0.0))
                m.add(p, (float(side), s), (long, fract(h4 + phase)), (HAIR, w / LINE_SCALE, row_code, reach))
            if i > 0:
                b = len(m.verts) - 4
                m.face((b, b + 1, b + 3, b + 2), STRANDS)


def make(name, kind):
    m = Mesh()
    full, game = kind == "full", kind == "game"
    for k in range(ARMS):
        if full:
            arm_sheet(m, k, 0.0, 1.0, k * 1.3, 40, 10)
            arm_sheet(m, k, math.pi * 0.5, 0.85, k * 1.3 + 4.0, 34, 10)
        elif game:
            arm_sheet(m, k, 0.0, 1.0, k * 1.3, 14, 3)
            arm_sheet(m, k, math.pi * 0.5, 0.85, k * 1.3 + 4.0, 12, 3)
        else:
            arm_sheet(m, k, 0.0, 1.0, k * 1.3, 6, 2)
    for k in range(CLUSTERS):
        if full:
            hairs(m, k, HAIRS_FULL, 24, 1.0)
        elif game:
            hairs(m, k, 16, 7, 1.25)
        else:
            hairs(m, k, 7, 5, 1.7)
    if full:
        bell(m, 192, 22, 12, 96)
    elif game:
        bell(m, 96, 7, 4, 48)
    else:
        bell(m, 48, 5, 2, 24)
    return finish(name, m)


def finish(name, m):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) for p in m.verts], [], list(m.faces))
    # (every layer made first, then each looked up by name: making one moves the others)
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
    tints = {SURFACES[0]: (0.85, 0.45, 0.2, 1.0), SURFACES[1]: (0.9, 0.6, 0.2, 1.0)}
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
    winding(name, mesh, m)
    return obj


def winding(name, mesh, m):
    """Every face that has a way to face (the bell's top out, its underside in) faces it, as Blender sees it;
    the rest are two-sided sheets and lines."""
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
        obj = make("lions_mane_jelly" + suffix, kind)
        export_one(obj, os.path.join(OUT, "lions_mane_jelly%s.glb" % suffix))
        made.append(obj)
    made[1].location.x = 2.0
    made[2].location.x = 4.0
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "lions_mane_jelly.blend"))


if __name__ == "__main__":
    main()
