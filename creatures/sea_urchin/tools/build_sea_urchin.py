"""Builds the sea urchins (creatures/sea_urchin) and exports them for Godot.

Run from the game's root:
    blender --background --factory-startup --python creatures/sea_urchin/tools/build_sea_urchin.py
    blender --background --factory-startup --python creatures/sea_urchin/tools/build_sea_urchin.py -- <preview folder>

Three kinds, each three models (one still mesh, one surface each):
    models/sea_urchin_<kind>.glb        the full model (close pictures)
    models/sea_urchin_<kind>_game.glb   the game model (Twilight Princess weight)
    models/sea_urchin_<kind>_lo.glb     the low model (far off, many of them)
and the editable tools/sea_urchin.blend with all nine (this folder has a .gdignore).

The kinds, built from what the animals look like (no picture traced):
- long_spined: a long-spined black urchin after the crowned urchin (Centrostephanus coronatus) of the California
  coast: a small dark test with long thin spines, longest above the middle.
- purple: the purple urchin (Strongylocentrotus purpuratus): a broad flattened test thick with short spines.
- slate_pencil: a slate pencil urchin (Heterocentrotus mamillatus): thirty thick blunt spines in columns, short
  flat spines between them.
Each has a few tube feet reaching out as threads along its five double rows, and five teeth at its mouth
beneath (Aristotle's lantern).

Everything here is in Godot space (metres, Y up, X its left side, -Z its front) until it is written out. The
origin is on the ground under the middle of the test (the lowest spines stand on y = 0).

The test (the shell) is a sum the shader knows too (sea_urchin.gdshader: `test_point`, `spine_way`): a point at
`theta` (0 the top, pi the bottom) and `phi` (round from +X towards +Z) is
    (A sin(theta) cos(phi), MIDDLE + (TOP if cos(theta) > 0 else BOTTOM) cos(theta), A sin(theta) sin(phi))
and a spine there stands along a way tipped out by BELOW_LEAN beneath the middle. Each spine's root is that
point less SINK of a spine's way. The shader turns each spine (and foot) about its root.

What a point is, for the shader:
    UV2.y the part: 0 the test, 1 a spine, 2 a tube foot, 3 a tooth, 4 a short spine (the slate pencil's).
    UV: (phi / tau, theta / pi) of the point (on the test) or of the root of the spine or foot it belongs to.
    UV2.x on a spine or foot: from its root (0) to its tip (1); on the test 0.
(The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.)
"""

import math
import os
import random
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "models")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = ARGS[0] if ARGS else ""
TAU = math.tau
TEST, SPINE, FOOT, TOOTH, SHORT = range(5)
WHICH = ("full", "game", "lo")

# A: the test's radius; top, bottom: how far it reaches above and below its middle; middle: how high its middle
# stands (found below so that the lowest spine tips stand on the ground); below_lean: how much a spine beneath the
# middle is tipped out; spine: (longest, base radius); count of spines (full, game, low); feet (full, game, low);
# foot length; primaries: thick spines (slate pencil) (count rows, length, radius).
KINDS = {
    "long_spined": dict(A=0.032, top=0.022, bottom=0.014, below_lean=0.45, spine=(0.105, 0.0011),
                        spines=(700, 450, 90), feet=(16, 6, 0), foot=0.03, sink=0.003, primaries=None),
    "purple": dict(A=0.04, top=0.024, bottom=0.015, below_lean=0.55, spine=(0.024, 0.0011),
                   spines=(1400, 226, 70), feet=(20, 4, 0), foot=0.032, sink=0.002, primaries=None),
    "slate_pencil": dict(A=0.034, top=0.026, bottom=0.016, below_lean=0.5, spine=(0.008, 0.0009),
                         spines=(700, 170, 0), feet=(14, 5, 0), foot=0.025, sink=0.002,
                         primaries=dict(length=0.062, radius=0.0042)),
}
# The test: rings from top to bottom and points round it (full, game, low).
TEST_RINGS = (40, 7, 5)
TEST_AROUND = (72, 12, 8)
# Spines thicker on the lighter models, to cover about as much.
SPINE_THICK = (1.0, 2.0, 2.6)


def to_b(p):
    return Vector((p.x, -p.z, p.y))


def test_point(k, theta, phi):
    c = math.cos(theta)
    rho = k["A"] * math.sin(theta)
    return Vector((rho * math.cos(phi), k["middle"] + (k["top"] if c > 0.0 else k["bottom"]) * c, rho * math.sin(phi)))


def spine_way(k, theta, phi):
    t = theta if theta < math.pi * 0.5 else math.pi * 0.5 + (theta - math.pi * 0.5) * (1.0 - k["below_lean"])
    return Vector((math.sin(t) * math.cos(phi), math.cos(t), math.sin(t) * math.sin(phi)))


def spine_root(k, theta, phi):
    return test_point(k, theta, phi) - spine_way(k, theta, phi) * k["sink"]


def spine_length(kind, k, theta, wobble):
    s = math.sin(theta)
    if kind == "long_spined":
        # (longest a little above the middle, short beneath: it stands on them)
        f = 0.72 + 0.28 * math.sin(min(theta * 1.25, math.pi * 0.5)) if theta < 1.6 else 0.25 + 0.6 * s ** 2
    elif kind == "purple":
        f = 0.75 + 0.25 * s if theta < 1.57 else 0.4 + 0.5 * s
    else:
        f = 0.8 + 0.2 * s
    return k["spine"][0] * f * wobble


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.data = []
        self.out = []
        self.count = {}

    def add(self, p, uv, part, along=0.0):
        self.verts.append(p)
        self.data.append(((uv[0], 1.0 - uv[1]), (along, 1.0 - part)))
        return len(self.verts) - 1

    def face(self, points, out, name):
        """A face wound so that its front (the side its points go round anticlockwise) is towards `out`."""
        ps = [self.verts[i] for i in points]
        n = Vector((0.0, 0.0, 0.0))
        for i in range(len(ps)):
            n += ps[i].cross(ps[(i + 1) % len(ps)])
        if n.length < 1e-20:
            return
        if n.dot(out) < 0.0:
            points = tuple(reversed(points))
        self.faces.append(tuple(points))
        self.out.append((Vector(out), name))
        self.count[name] = self.count.get(name, 0) + 1


def test(m, k, w):
    rings, around = TEST_RINGS[w], TEST_AROUND[w]
    middle = Vector((0.0, k["middle"], 0.0))
    top = m.add(test_point(k, 0.0, 0.0), (0.5, 0.0), TEST)
    bottom = m.add(test_point(k, math.pi, 0.0), (0.5, 1.0), TEST)
    grid = []
    for r in range(1, rings):
        theta = math.pi * r / rings
        # (the seam's points twice, once at each end, so that phi runs 0 to 1 without wrapping)
        grid.append([m.add(test_point(k, theta, TAU * c / around), (c / around, theta / math.pi), TEST)
                     for c in range(around + 1)])
    for c in range(around):
        m.face((top, grid[0][c], grid[0][c + 1]), Vector((0.0, 1.0, 0.0)), "test")
        m.face((bottom, grid[-1][c], grid[-1][c + 1]), Vector((0.0, -1.0, 0.0)), "test")
    for r in range(len(grid) - 1):
        for c in range(around):
            quad = (grid[r][c], grid[r][c + 1], grid[r + 1][c + 1], grid[r + 1][c])
            mid = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, mid - middle, "test")


def stick(m, part, name, theta, phi, root, way, length, radius, sides, rings, cap=0.0, tip_radius=0.0):
    """A spine or foot from `root` along `way`: `rings` rings of `sides` points (radius narrowing to
    `tip_radius`), closed by a point at its tip (set back by `cap` for a blunt rounded end). Open at its root,
    which is sunk in the test."""
    ref = Vector((0.0, 1.0, 0.0)) if abs(way.y) < 0.9 else Vector((1.0, 0.0, 0.0))
    a = way.cross(ref).normalized()
    b = way.cross(a).normalized()
    uv = (phi / TAU, theta / math.pi)
    if rings > 1:
        # (an open end stops short of the tip, which closes it as a point)
        ts = [i / (rings - 1) * ((1.0 - cap) if cap > 0.0 else 0.92) for i in range(rings)]
    else:
        ts = [0.0]
    if cap > 0.0:
        ts.append(1.0 - cap * 0.4)
    rows = []
    for i, t in enumerate(ts):
        r = radius + (tip_radius - radius) * min(1.0, t / max(1.0 - cap, 1e-6))
        if cap > 0.0 and i == len(ts) - 1:
            r = tip_radius * 0.75
        here = root + way * (length * t)
        rows.append((here, [m.add(here + (a * math.cos(TAU * s / sides) + b * math.sin(TAU * s / sides)) * r,
                                  uv, part, t) for s in range(sides)]))
    for i in range(len(rows) - 1):
        axis = (rows[i][0] + rows[i + 1][0]) * 0.5
        for s in range(sides):
            n = (s + 1) % sides
            quad = (rows[i][1][s], rows[i][1][n], rows[i + 1][1][n], rows[i + 1][1][s])
            mid = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, mid - axis, name)
    end = root + way * length
    tip = m.add(end, uv, part, 1.0)
    for s in range(sides):
        m.face((tip, rows[-1][1][s], rows[-1][1][(s + 1) % sides]), end - rows[-1][0], name)
    return end


def spread(n, lo, hi, rng, jitter=0.35, offset=0.0):
    """`n` places spread evenly over the test between `theta` lo and hi (a golden-angle spiral, jittered)."""
    out = []
    golden = math.pi * (3.0 - math.sqrt(5.0))
    c0, c1 = math.cos(lo), math.cos(hi)
    for i in range(n):
        c = c0 + (c1 - c0) * (i + 0.5 + rng.uniform(-jitter, jitter)) / n
        out.append((math.acos(max(-1.0, min(1.0, c))), (offset + i * golden + rng.uniform(-0.05, 0.05)) % TAU))
    return out


def spines(m, kind, k, w, rng):
    count = k["spines"][w]
    lowest = 1.0
    if count == 0:
        return lowest
    lo, hi = (0.12, math.pi - 0.3) if kind != "slate_pencil" else (0.05, math.pi - 0.35)
    part = SPINE if kind != "slate_pencil" else SHORT
    # (the game model's spines are the same as some of the full model's, and the low model's the same as some of
    # the game model's: each lighter model's places first, then more spread between them)
    places = []
    have = 0
    for step, n in enumerate(reversed(k["spines"])):
        n = min(n, count) - have
        if n > 0:
            places += spread(n, lo, hi, random.Random(5 + step), offset=step * 1.3)
            have += n
    for theta, phi in places:
        way = spine_way(k, theta, phi)
        root = spine_root(k, theta, phi)
        # (each spine's own length from where it stands, so that it is the same on every model)
        own = random.Random(round(theta * 1e5) * 7919 + round(phi * 1e5))
        length = spine_length(kind, k, theta, own.uniform(0.85, 1.12))
        if kind == "slate_pencil":
            # (the short spines: little ones lying close to the test, three-sided)
            length = k["spine"][0] * own.uniform(0.7, 1.2)
        end = stick(m, part, "spines", theta, phi, root, way, length, k["spine"][1] * SPINE_THICK[w], 3, 1)
        lowest = min(lowest, end.y)
    return lowest


def primaries(m, k, w, rng):
    """The slate pencil's thick blunt spines: in ten columns, three to a column, round and blunt."""
    p = k["primaries"]
    sides, rings = ((10, 7), (5, 2), (4, 1))[w]
    lowest = 1.0
    for column in range(10):
        for row, theta in enumerate((0.72, 1.18, 1.62)):
            # (ten columns evenly round it, each row turned half a column from the next)
            phi = (column + 0.5 * (row % 2)) * TAU / 10.0
            way = spine_way(k, theta, phi)
            root = spine_root(k, theta, phi)
            length = p["length"] * (0.72, 1.0, 0.8)[row] * (0.9 + 0.2 * ((column * 7 + row * 3) % 5) / 4.0)
            end = stick(m, SPINE, "pencils", theta, phi, root, way, length, p["radius"] * (1.0, 1.0, 0.9)[row],
                        sides, rings, cap=0.08 if rings > 1 else 0.0, tip_radius=p["radius"] * 0.85)
            lowest = min(lowest, end.y)
    return lowest


def feet(m, k, w, rng):
    count = k["feet"][w]
    sides, rings = ((3, 8), (3, 3), (3, 1))[w]
    for i in range(count):
        column = i % 10
        phi = (column // 2) * TAU / 5.0 + TAU / 10.0 + (0.07 if column % 2 else -0.07)
        theta = 0.55 + 0.95 * ((i // 10) * 0.5 + 0.25 * (column % 3)) + rng.uniform(-0.1, 0.1)
        theta = min(theta, 1.9)
        way = spine_way(k, theta, phi)
        root = spine_root(k, theta, phi)
        stick(m, FOOT, "feet", theta, phi, root, way, k["foot"] * rng.uniform(0.8, 1.1), 0.0006, sides, rings,
              tip_radius=0.0005)


def teeth(m, k):
    """Five white teeth meeting at the mouth, beneath."""
    mouth = test_point(k, math.pi, 0.0)
    for i in range(5):
        phi = TAU * i / 5.0
        base = mouth + Vector((math.cos(phi) * 0.004, 0.0015, math.sin(phi) * 0.004))
        tip = mouth + Vector((math.cos(phi) * 0.0007, -0.004, math.sin(phi) * 0.0007))
        way = (tip - base).normalized()
        stick(m, TOOTH, "teeth", math.pi, phi, base, way, (tip - base).length, 0.0014, 3, 1)


def make(kind, w):
    k = dict(KINDS[kind])
    # (first the shape at middle 0, to find how high the middle must stand for the lowest tips to touch the ground)
    k["middle"] = 0.0
    rng = random.Random(5)
    trial = Mesh()
    lowest = spines(trial, kind, k, 0, rng)
    if k["primaries"]:
        lowest = min(lowest, primaries(trial, k, 0, random.Random(6)))
    k["middle"] = max(-lowest, k["bottom"] + 0.006)
    m = Mesh()
    test(m, k, w)
    spines(m, kind, k, w, random.Random(5 + w))
    if k["primaries"]:
        primaries(m, k, w, random.Random(6))
    feet(m, k, w, random.Random(9))
    if w < 2:
        teeth(m, k)
    name = "sea_urchin_%s%s" % (kind, "" if w == 0 else "_" + WHICH[w])
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) for p in m.verts], [], m.faces)
    # (every layer made first, then each looked up by name: making one moves the others)
    mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.new(name="UV2")
    uv = mesh.uv_layers["UVMap"].data
    uv2 = mesh.uv_layers["UV2"].data
    for poly in mesh.polygons:
        for corner, vi in enumerate(poly.vertices):
            dd = m.data[vi]
            uv[poly.loop_start + corner].uv = dd[0]
            uv2[poly.loop_start + corner].uv = dd[1]
    material = bpy.data.materials.get("sea_urchin") or bpy.data.materials.new("sea_urchin")
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.3, 0.1, 0.35, 1.0)
    material.diffuse_color = (0.3, 0.1, 0.35, 1.0)
    mesh.materials.append(material)
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    parts = {}
    for poly, (out, group) in zip(mesh.polygons, m.out):
        parts[group] = parts.get(group, 0) + len(poly.vertices) - 2
    print("BUILT %s verts=%d tris=%d %s" % (name, len(mesh.vertices), tris, parts))
    xs = [abs(p.x) for p in m.verts] + [abs(p.z) for p in m.verts]
    print("SHAPE %s: middle %.5f, reach %.4f, height %.4f" % (name, k["middle"], max(xs), max(p.y for p in m.verts)))
    winding(name, mesh, m)
    return obj


def winding(name, mesh, m):
    """Nothing inside out: every skin faces away from its own middle (Blender's front is the side a face's
    normal is on)."""
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
        export_animations=False, export_texcoords=True, export_normals=True,
    )


def render(folder, made):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_backface_culling = True
    scene.render.resolution_x, scene.render.resolution_y = 900, 700
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    for (kind, w), obj in made.items():
        span = 0.32 if kind == "long_spined" else (0.2 if kind == "slate_pencil" else 0.15)
        for other in made.values():
            other.hide_render = other is not obj
        for view, direction in (("side", (1, 0, 0.0001)), ("top", (0.001, 0, 1)), ("under", (0.001, 0, -1))):
            if w and view == "under":
                continue
            offset = Vector(direction).normalized() * 40.0
            camera.data.ortho_scale = span
            camera.location = Vector((0, 0, 0.03)) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s_%s_%s.png" % (kind, WHICH[w], view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    os.makedirs(OUT, exist_ok=True)
    made = {}
    for kind in KINDS:
        for w in range(3):
            obj = make(kind, w)
            made[(kind, w)] = obj
            export_one(obj, os.path.join(OUT, obj.name + ".glb"))
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, made)
    # (laid out side by side in the .blend: a row per kind, full, game and low along it)
    for (kind, w), obj in made.items():
        obj.hide_render = False
        obj.location = Vector((w * 0.35, -list(KINDS).index(kind) * 0.35, 0.0))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "sea_urchin.blend"))


if __name__ == "__main__":
    main()
