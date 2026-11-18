"""Builds the fried egg jelly (creatures/fried_egg_jelly) and exports it for Godot.

    blender --background --python creatures/fried_egg_jelly/tools/build_fried_egg_jelly.py

Writes creatures/fried_egg_jelly/models/fried_egg_jelly.glb (the full model), fried_egg_jelly_game.glb (the game
model, at Twilight Princess weight) and fried_egg_jelly_lo.glb (far off, crowds, phones: its arms are not laid
along ropes), and the editable creatures/fried_egg_jelly/tools/fried_egg_jelly.blend (all three; this folder has a
.gdignore). Each is one static mesh in two surfaces; the shaders beat the bell and lay the arms along their ropes.
It prints a BUILT line (triangles) and a WINDING line (nothing inside out) for each.

A fried egg jelly (after Cotylorhiza tuberculata, the Mediterranean one): a pale, flat, clear bell 0.4 m across,
its rim cut in sixteen small scallops, with a raised yolk-yellow dome in its middle, a groove round the dome's
foot; under it eight short oral arms, each a frilly cream bunch with club-like stalks sticking out of it whose
tips are purple. Slow and harmless.

Everything here is in Godot space (metres, Y up) until it is written out. The origin is the middle of the bell's
rim (the rim at rest lies in y = 0); up is +Y. It has no front.

What a point is, for the shaders:
- vertex colour red: the part. 0 the top of the bell (the yolk is its middle), 0.25 its underside (with the lip
  and the stalk), 0.5 a frilly sheet of an arm, 0.75 a club (a line, wider towards its purple tip).
- green: on a club, half its width / LINE_SCALE (the shader draws it that wide, turned to face the camera).
- blue: on an arm, which rope it follows ((arm + 0.5) / 32).
- alpha: on an arm, how far along its rope it reaches.
- UV.x: on the bell round it (0..1); on an arm across it (0..1). UV.y: on the bell how far out from the middle
  (0 the middle, 1 the rim); on an arm how far along its rope.
- UV2.x: an arm's rope's length (metres); UV2.y: a number of its own (0..1).
(The glTF writer flips V: what is written is 1 - v, so that Godot reads v.)

The ropes' roots, lengths and phases are in FriedEggJelly.strands() too: change one, change the other.
Surfaces: "fried_egg_strands" (drawn first) and "fried_egg_bell" (underside, then top: FriedEggJelly sorts its
triangles into that order when it loads it).
"""

import math
import os

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "models")

# Kept in step with fried_egg_jelly.gd and the shaders.
RADIUS = 0.2
YOLK = 0.095
ARMS = 8
ARM_LONG = 0.17
ARM_AT = 0.045
ARM_Y = -0.02
SCALLOPS = 16
LINE_SCALE = 0.02
CLUBS_FULL = 10

SURFACES = ["fried_egg_strands", "fried_egg_bell"]
STRANDS, BELL = 0, 1
TOP, UNDER, SHEET, CLUB = 0.0, 0.25, 0.5, 0.75
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
    a = (k + 0.5) * TAU / ARMS
    root = Vector((math.cos(a) * ARM_AT, ARM_Y, math.sin(a) * ARM_AT))
    return root, ARM_LONG * (1.0 + 0.1 * math.sin(k * 2.1 + 0.4)), fract(k * 0.37 + 0.11), a


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


def top_y(r):
    """How high the top of the bell is `r` from the middle: a flat, gently domed disc, and the yolk standing up
    out of it, a groove round its foot."""
    x = min(r / RADIUS, 1.0)
    disc = 0.045 * (1.0 - x * x) ** 0.7
    yolk = 0.07 * max(0.0, 1.0 - (r / YOLK) ** 2) ** 0.6
    groove = -0.006 * math.exp(-((r - YOLK * 1.04) / 0.008) ** 2)
    return disc + yolk + groove


def bell_point(v, a, inner):
    """A point of the bell: `v` 0 in the middle to 1 at the rim, `a` the angle round it."""
    x = fract(a * SCALLOPS / TAU)
    scallop = abs(math.sin(x * math.pi))
    r = RADIUS * v * (1.0 + 0.025 * (scallop - 0.7) * smooth(0.85, 1.0, v))
    y = top_y(r) - 0.006 * (1.0 - scallop) * smooth(0.9, 1.0, v)
    if inner:
        r *= 0.97
        x2 = min(r / RADIUS, 1.0)
        y = 0.012 * (1.0 - x2 * x2) - 0.004 * (1.0 - smooth(0.9, 1.0, v))
    return Vector((math.cos(a) * r, y, math.sin(a) * r))


def ring_v(r, rings):
    """Where ring `r` of `rings` lies (0 the middle .. 1 the rim): closer together round the yolk's foot, where
    the shape turns."""
    t = r / rings
    return t + 0.07 * math.sin(t * TAU)


def bell(m, around, rings_top, rings_under, under_around):
    middle = Vector((0.0, -0.1, 0.0))
    grids = {}
    for name, inner, rings, code, count in (("top", False, rings_top, TOP, around), ("under", True, rings_under, UNDER, under_around)):
        grid = []
        for r in range(rings + 1):
            v = ring_v(r, rings)
            row = []
            for c in range(count + 1):
                a = c / count * TAU
                row.append(m.add(bell_point(v, a, inner), (c / count, v), (0.0, 0.0), (code, 0.0, 0.0, 1.0)))
            grid.append(row)
        grids[name] = (grid, rings, count)
    for name, sign in (("under", -1.0), ("top", 1.0)):
        grid, rings, count = grids[name]
        for r in range(rings):
            for c in range(count):
                ids = (grid[r][c], grid[r][c + 1], grid[r + 1][c + 1], grid[r + 1][c])
                p = sum((m.verts[i] for i in ids), Vector()) * 0.25
                if r == 0:
                    ids = (grid[0][c], grid[1][c + 1], grid[1][c])
                m.face(ids, BELL, Vector((0.0, sign, 0.0)) if r < rings - 1 else (p - middle) * sign)
    # the lip
    lip = []
    for inner in (False, True):
        row = []
        for c in range(around + 1):
            row.append(m.add(bell_point(1.0, c / around * TAU, inner), (c / around, 1.0), (0.0, 0.0), (UNDER, 0.0, 0.0, 1.0)))
        lip.append(row)
    for c in range(around):
        p = m.verts[lip[0][c]]
        m.face((lip[0][c], lip[1][c], lip[1][c + 1], lip[0][c + 1]), BELL, Vector((p.x, -0.02, p.z)))
    # the stalk under the middle, down to where the arms hang from
    stalk = []
    for y, rad in ((0.008, ARM_AT + 0.02), (ARM_Y, ARM_AT + 0.01)):
        row = []
        for c in range(13):
            a = c / 12 * TAU
            row.append(m.add(Vector((math.cos(a) * rad, y, math.sin(a) * rad)), (c / 12, 0.0), (0.0, 0.0), (UNDER, 0.0, 0.0, 1.0)))
        stalk.append(row)
    for c in range(12):
        ids = (stalk[0][c], stalk[0][c + 1], stalk[1][c + 1], stalk[1][c])
        p = sum((m.verts[i] for i in ids), Vector()) * 0.25
        m.face(ids, BELL, Vector((p.x, 0.0, p.z)))


def arm_sheet(m, k, turned, wide, seed, steps, across):
    """A frilly cream sheet of arm `k`, through its middle line, turned `turned` round it: wide and crinkled at
    the top (a bunch, like cauliflower), narrowing down the arm."""
    root, long, phase, a = arm_strand(k)
    reach = 0.8
    colour = (SHEET, 0.0, (k + 0.5) / 32.0, reach)
    rows = []
    for s_i in range(steps + 1):
        t = s_i / steps
        s = t * reach
        arc = s * long
        twist = a + turned + arc * 6.0 + 0.4 * math.sin(arc * 9.0 + seed)
        width = wide * (0.012 + 0.04 * smooth(0.0, 0.25, t) * (1.0 - 0.75 * smooth(0.5, 1.0, t)))
        across_way = Vector((math.cos(twist), 0.0, math.sin(twist)))
        facing = Vector((-math.sin(twist), 0.0, math.cos(twist)))
        # (the arms lean out from the middle a little)
        out = Vector((math.cos(a), 0.0, math.sin(a))) * 0.04 * math.sin(t * math.pi * 0.5)
        row = []
        for w_i in range(across + 1):
            u = w_i / across * 2.0 - 1.0
            e = abs(u)
            side = 1.9 if u > 0.0 else 0.0
            crinkle = math.sin(arc / 0.03 * TAU + seed + side + u * 2.0)
            p = root + out + Vector((0.0, -arc, 0.0)) + across_way * u * width + facing * width * 0.45 * e ** 1.3 * crinkle
            row.append(m.add(p, ((u + 1.0) * 0.5, s), (long, fract(phase + seed * 0.1)), colour))
        rows.append(row)
    for r in range(len(rows) - 1):
        for w_i in range(across):
            m.face((rows[r][w_i], rows[r][w_i + 1], rows[r + 1][w_i + 1], rows[r + 1][w_i]), STRANDS)


def clubs(m, k, count, steps, thicker):
    """Arm `k`'s clubs: `count` stalks sticking out of its bunch, each a line wider towards its purple tip."""
    root, long, phase, a = arm_strand(k)
    row_code = (k + 0.5) / 32.0
    out_way = Vector((math.cos(a), 0.0, math.sin(a)))
    for j in range(count):
        t = (j + 0.5) / count
        jf = min(int(t * CLUBS_FULL), CLUBS_FULL - 1)
        n = k * 31.0 + jf * 7.3
        h1, h2, h3 = hash1(n), hash1(n + 1.7), hash1(n + 3.3)
        # where along the arm it leaves, how long it is, which way it sticks out
        start = 0.15 + 0.5 * t
        reach = min(1.0, start + 0.25 + 0.3 * h1)
        way = (Vector((math.cos(h2 * TAU), 0.0, math.sin(h2 * TAU))) + out_way * 0.8).normalized()
        half = 0.0022 * thicker
        for i in range(steps + 1):
            ts = i / steps
            s = start + (reach - start) * ts
            arc = s * long
            stick = way * (0.012 + 0.05 * ts) * (0.6 + 0.6 * h3)
            lean = out_way * 0.04 * math.sin(min(s / 0.8, 1.0) * math.pi * 0.5)
            centre = Vector((root.x + stick.x + lean.x, root.y - arc, root.z + stick.z + lean.z))
            # (a club: thin, swelling to a knob at its tip)
            w = half * (0.6 + 1.6 * smooth(0.55, 0.95, ts)) * (1.0 - 0.5 * smooth(0.97, 1.0, ts))
            for side in (0, 1):
                m.add(centre + Vector(((side * 2 - 1) * w, 0.0, 0.0)), (float(side), s), (long, fract(h3 + phase)), (CLUB, w / LINE_SCALE, row_code, reach))
            if i > 0:
                b = len(m.verts) - 4
                m.face((b, b + 1, b + 3, b + 2), STRANDS)


def make(name, kind):
    m = Mesh()
    for k in range(ARMS):
        if kind == "full":
            arm_sheet(m, k, 0.0, 1.0, k * 1.3, 18, 8)
            arm_sheet(m, k, math.pi * 0.5, 0.85, k * 1.3 + 4.0, 16, 8)
            clubs(m, k, CLUBS_FULL, 10, 1.0)
        elif kind == "game":
            arm_sheet(m, k, 0.0, 1.0, k * 1.3, 6, 2)
            arm_sheet(m, k, math.pi * 0.5, 0.85, k * 1.3 + 4.0, 5, 2)
            clubs(m, k, 4, 4, 1.15)
        else:
            arm_sheet(m, k, 0.0, 1.0, k * 1.3, 3, 1)
            clubs(m, k, 2, 2, 1.5)
    if kind == "full":
        bell(m, 160, 24, 8, 80)
    elif kind == "game":
        bell(m, 48, 8, 3, 24)
    else:
        bell(m, 24, 4, 2, 12)
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
    tints = {SURFACES[0]: (0.95, 0.9, 0.75, 1.0), SURFACES[1]: (1.0, 0.85, 0.4, 1.0)}
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
        obj = make("fried_egg_jelly" + suffix, kind)
        export_one(obj, os.path.join(OUT, "fried_egg_jelly%s.glb" % suffix))
        made.append(obj)
    made[1].location.x = 0.6
    made[2].location.x = 1.2
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "fried_egg_jelly.blend"))


if __name__ == "__main__":
    main()
