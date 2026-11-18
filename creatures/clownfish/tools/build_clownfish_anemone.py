"""Builds the clownfish's host anemone (creatures/clownfish, ClownfishAnemone) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/clownfish/tools/build_clownfish_anemone.py
    blender --background --python creatures/clownfish/tools/build_clownfish_anemone.py -- <preview folder>

A magnificent sea anemone (Heteractis magnifica), the ocellaris clownfish's usual host: a short stout column
standing on its foot, a broad oral disc on top whose margin rises and falls in folds, a mouth in the middle of
the disc, and a few hundred finger-like tentacles with blunt tips crowded over the disc, upright in the middle and
leaning out and down at the margin. About 0.52 m across the tentacles, 0.17 m high; its base at y = 0, its middle
on the Y axis.

It writes creatures/clownfish/models/clownfish_anemone.glb (250 tentacles), clownfish_anemone_game.glb (for
games: 165 four-sided tentacles of two rings, a little thicker, about 2,650 triangles) and clownfish_anemone_lo.glb (50
fewer, thicker, coarser tentacles), and the editable creatures/clownfish/tools/clownfish_anemone.blend (this folder has a
.gdignore). Each is one still mesh with one surface; the shader (clownfish_anemone.gdshader) sways the tentacles
and draws the colours. Every part (the column with its disc, each tentacle) is a closed solid, and the script
prints a WINDING line: a ray out of every triangle of a part must leave that part an even number of times.

What a point is, for the shader: vertex colour red the part, as a tenth (0 the column and its foot, 0.1 the oral
disc, 0.2 a tentacle). On the column and the disc: UV.x how far out from the middle (0 the middle, 1 the disc's
margin; on the column 1 at its top, more down its side to the foot), UV.y how far round (0..1). On a tentacle: UV.x
how far along it (0 its root, 1 its tip), UV.y how far round it (0..1); UV2 where its root is (x, z in metres, the
anemone's own space), green a number of its own (0..1), blue how far out on the disc it stands (0 the middle, 1
the margin). (The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.)

Everything here is in metres in Godot space (Y up), written out in Blender space.
"""

import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "models")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = ARGS[0] if ARGS else ""
NAME = "clownfish_anemone"
TAU = math.tau
COLUMN, DISC, TENTACLE = 0, 1, 2

# Kept in step with clownfish_anemone.gd.
DISC_RADIUS = 0.2      # the oral disc's margin, at its widest fold
FOOT_RADIUS = 0.14     # the column's foot, on the ground
DISC_HEIGHT = 0.1      # how high the disc's margin stands
FOLDS = 5              # how many times the margin rises and falls round the disc
MOUTH = 0.035          # the mouth's lips, how far out from the middle

# The game model (Claude's numbers, 2026-11-18): about 2,650 triangles against the full model's 13,824 (the
# Twilight Princess yardstick: 1,800 to 3,000 for something 0.5 to 1.5 m across). The mass of tentacles is the
# look, so most of them go there: 165 tentacles (the full model's 250 at 48 triangles each) of four sides and
# two rings and a blunt tip (14 triangles each), 1.15 times as thick so that they cover the disc as the 250 do,
# spread over the disc as the full model's are (`spread` 1; more than 1 would crowd them to the middle, less to
# the margin); the column and disc with 24 points
# round and fewer rings (most of the disc is under the tentacles). Set while it is built; None for the full and
# low models, which are built exactly as they were before it.
GAME_MODEL = {
    "count": 165, "thick": 1.15, "sides": 4, "stations": [0.0, 0.88], "radii": [1.0, 0.88],
    "spread": 1.0,
    "around": 24, "foot": [0.0, 1.0], "up": 3, "across": 4,
}
GAME = None


def to_b(p):
    return Vector((p.x, -p.z, p.y))


def margin(angle):
    """How far out the disc's margin is at an angle round it."""
    return DISC_RADIUS * (1.0 + 0.045 * math.sin(FOLDS * angle))


def disc_y(r, angle):
    """How high the disc is at `r` out from the middle and `angle` round: a low dome, its margin folded up and
    down, the mouth's lips raised a little in the middle."""
    k = min(r / margin(angle), 1.0)
    lips = 0.006 * math.exp(-((r - MOUTH) / 0.012) ** 2)
    return DISC_HEIGHT + 0.01 * (1.0 - k * k) + 0.018 * math.sin(FOLDS * angle + 0.4) * k ** 3 + lips


class Part:
    """One closed piece: points (metres), what each is for the shader, and faces. `done` welds it, turns every
    face outward and checks that."""

    def __init__(self, name):
        self.name = name
        self.verts = []
        self.data = []
        self.faces = []

    def add(self, p, uv, uv2, colour):
        self.verts.append(Vector(p))
        self.data.append((uv, uv2, colour))
        return len(self.verts) - 1

    @staticmethod
    def inside_out(bm):
        cut = bm.copy()
        bmesh.ops.triangulate(cut, faces=cut.faces)
        cut.normal_update()
        tree = BVHTree.FromBMesh(cut)
        wrong = 0
        counted = 0
        for f in cut.faces:
            if f.calc_area() > 1e-12:
                counted += 1
                at = f.calc_center_median() + f.normal * 1e-6
                hits = 0
                while hits < 40:
                    hit = tree.ray_cast(at, f.normal)
                    if hit[0] is None:
                        break
                    hits += 1
                    at = hit[0] + f.normal * 1e-6
                if hits % 2:
                    wrong += 1
        cut.free()
        return wrong, counted

    def done(self):
        bm = bmesh.new()
        uv = bm.loops.layers.uv.new("uv")
        uv2 = bm.loops.layers.uv.new("uv2")
        colour = bm.loops.layers.float_color.new("colour")
        made = [bm.verts.new(to_b(p)) for p in self.verts]
        for face in self.faces:
            try:
                f = bm.faces.new([made[i] for i in face])
            except ValueError:
                continue
            for loop, i in zip(f.loops, face):
                d = self.data[i]
                loop[uv].uv = d[0]
                loop[uv2].uv = d[1]
                loop[colour] = (d[2][0], d[2][1], d[2][2], 1.0)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.normal_update()
        wrong, counted = self.inside_out(bm)
        if wrong * 2 > counted:
            bmesh.ops.reverse_faces(bm, faces=bm.faces)
            bm.normal_update()
            wrong, counted = self.inside_out(bm)
        out = []
        for f in bm.faces:
            out.append([(loop.vert.co.copy(), tuple(loop[uv].uv), tuple(loop[uv2].uv), tuple(loop[colour]))
                        for loop in f.loops])
        bm.free()
        return out, wrong, counted


def column_and_disc(low):
    """The column from its foot up to the disc's margin, and the disc over it, as one closed solid: rings round
    the Y axis, from the middle of the foot out and up the column, over the margin and in across the disc to the
    mouth."""
    part = Part("column")
    around = GAME["around"] if GAME else (16 if low else 48)
    rings = []
    # (the foot, from its middle out: flat on the ground)
    centre = part.add((0.0, 0.0, 0.0), (1.6, 0.0), (0.0, 0.0), (COLUMN / 10.0, 0.0, 0.0))
    foot = GAME["foot"] if GAME else ([0.0, 1.0] if low else [0.0, 0.5, 1.0])
    up = GAME["up"] if GAME else (2 if low else 7)
    across = GAME["across"] if GAME else (3 if low else 11)
    profile = []
    for t in foot[1:]:
        profile.append(("foot", t))
    for i in range(1, up + 1):
        profile.append(("column", i / up))
    for i in range(1, across + 1):
        profile.append(("disc", i / across))
    for kind, t in profile:
        ring = []
        for k in range(around + 1):
            angle = TAU * k / around
            c, s = math.cos(angle), math.sin(angle)
            if kind == "foot":
                r = FOOT_RADIUS * t
                y = 0.0
                uvx = 1.6
                code = COLUMN
            elif kind == "column":
                # (a stout column flaring out under the disc's margin)
                top = disc_y(margin(angle), angle)
                y = top * t
                r = FOOT_RADIUS + (margin(angle) - FOOT_RADIUS) * (t ** 2.2) + 0.012 * math.sin(math.pi * t)
                uvx = 1.0 + 0.6 * (1.0 - t)
                code = COLUMN
            else:
                # (in across the disc to the mouth's middle: finer near the margin)
                k_in = 1.0 - t
                r = margin(angle) * k_in
                y = disc_y(r, angle)
                uvx = k_in
                code = DISC
            ring.append(part.add((r * c, y, r * s), (uvx, 1.0 - k / around), (0.0, 0.0), (code / 10.0, 0.0, 0.0)))
        rings.append(ring)
    first = rings[0]
    for k in range(around):
        part.faces.append((centre, first[k + 1], first[k]))
    for a, b in zip(rings, rings[1:]):
        for k in range(around):
            part.faces.append((a[k], a[k + 1], b[k + 1], b[k]))
    # (the seam where the rings meet themselves is welded by `done`: the first and last points are one place)
    return part


def tentacle(index, count, rng, low):
    """One tentacle: a finger with a blunt rounded tip, its root sunk a little into the disc."""
    part = Part("tentacle")
    golden = math.pi * (3.0 - math.sqrt(5.0))
    angle = index * golden + rng.uniform(-0.08, 0.08)
    inner = MOUTH + 0.022
    reach = (index + 0.5) / count
    r = inner + (margin(angle) - 0.012 - inner) * (reach ** (0.5 * GAME["spread"]) if GAME else math.sqrt(reach))
    out_k = r / margin(angle)
    root = Vector((r * math.cos(angle), disc_y(r, angle) - 0.004, r * math.sin(angle)))
    outward = Vector((math.cos(angle), 0.0, math.sin(angle)))
    lean = Vector((0.0, 1.0 - 0.55 * out_k ** 2, 0.0)) + outward * (0.18 + 0.95 * out_k ** 2)
    lean += Vector((rng.uniform(-0.15, 0.15), 0.0, rng.uniform(-0.15, 0.15)))
    lean.normalize()
    long = rng.uniform(0.06, 0.082) * (0.85 + 0.2 * out_k)
    # (the low model has fewer, thicker ones, to cover the disc as well)
    thick = rng.uniform(0.0068, 0.0082) * (GAME["thick"] if GAME else (1.5 if low else 1.0))
    droop = 0.5 * out_k ** 1.5 + rng.uniform(0.0, 0.15)
    wander = Vector((rng.uniform(-1.0, 1.0), rng.uniform(-0.3, 0.3), rng.uniform(-1.0, 1.0))) * 0.18
    seed = rng.random()

    def line(u):
        return root + lean * (long * u) + Vector((0.0, -1.0, 0.0)) * (long * droop * u * u) + outward * (long * 0.12 * out_k * u * u) + wander * (long * u * u)

    sides = GAME["sides"] if GAME else (3 if low else 6)
    stations = GAME["stations"] if GAME else ([0.0, 0.85] if low else [0.0, 0.35, 0.68, 0.9])
    radii = GAME["radii"] if GAME else ([1.0, 0.8] if low else [1.0, 0.92, 0.86, 0.72])
    rings = []
    for u, k in zip(stations, radii):
        at = line(u)
        ahead = (line(min(u + 0.02, 1.0)) - line(max(u - 0.02, 0.0))).normalized()
        # (the same way round at every ring: the way round the disc, square to the tentacle there; a frame
        # from "up" turns over between rings of an upright tentacle and twists it inside out)
        round_way = Vector((-math.sin(angle), 0.0, math.cos(angle)))
        side = (round_way - ahead * round_way.dot(ahead)).normalized()
        other = side.cross(ahead).normalized()
        ring = []
        for j in range(sides):
            q = TAU * j / sides
            p = at + (side * math.cos(q) + other * math.sin(q)) * (thick * k)
            ring.append(part.add(p, (u, 1.0 - j / sides), (root.x, 1.0 - root.z), (TENTACLE / 10.0, seed, out_k)))
        rings.append(ring)
    tip = part.add(line(1.0), (1.0, 0.5), (root.x, 1.0 - root.z), (TENTACLE / 10.0, seed, out_k))
    base = part.add(root - lean * 0.002, (0.0, 0.5), (root.x, 1.0 - root.z), (TENTACLE / 10.0, seed, out_k))
    for a, b in zip(rings, rings[1:]):
        for j in range(sides):
            n = (j + 1) % sides
            part.faces.append((a[j], a[n], b[n], b[j]))
    last = rings[-1]
    for j in range(sides):
        part.faces.append((last[j], last[(j + 1) % sides], tip))
        if not GAME:
            part.faces.append((rings[0][(j + 1) % sides], rings[0][j], base))
    if GAME:
        # (the game model's root, sunk in the disc where nothing sees it, is closed flat)
        part.faces.append(tuple(reversed(rings[0])))
    return part


def make(name, low):
    rng = random.Random(11)
    parts = [column_and_disc(low)]
    count = GAME["count"] if GAME else (50 if low else 250)
    for i in range(count):
        parts.append(tentacle(i, count, rng, low))
    verts, faces, corners = [], [], []
    wrong_by = {"column": 0, "tentacle": 0}
    counted_by = {"column": 0, "tentacle": 0}
    for part in parts:
        out, wrong, counted = part.done()
        wrong_by[part.name] += wrong
        counted_by[part.name] += counted
        for face in out:
            first = len(verts)
            for co, uv, uv2, colour in face:
                verts.append(co)
                corners.append((uv, uv2, colour))
            faces.append(list(range(first, first + len(face))))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    # (every layer made first, then each looked up by name: making one moves the others)
    mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.new(name="UV2")
    mesh.color_attributes.new(name="Color", type="FLOAT_COLOR", domain="CORNER")
    uv = mesh.uv_layers["UVMap"].data
    uv2 = mesh.uv_layers["UV2"].data
    colour = mesh.color_attributes["Color"].data
    for poly in mesh.polygons:
        for corner, vi in enumerate(poly.vertices):
            d = corners[vi]
            uv[poly.loop_start + corner].uv = d[0]
            uv2[poly.loop_start + corner].uv = d[1]
            colour[poly.loop_start + corner].color = d[2]
    mesh.color_attributes.active_color = mesh.color_attributes["Color"]
    mesh.color_attributes.render_color_index = mesh.color_attributes.find("Color")
    material = bpy.data.materials.get(NAME) or bpy.data.materials.new(NAME)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.55, 0.5, 0.3, 1.0)
    material.diffuse_color = (0.55, 0.5, 0.3, 1.0)
    mesh.materials.append(material)
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    # (every face was made with corners of its own: the same point is one point again)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-8)
    bpy.ops.object.mode_set(mode="OBJECT")
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    box = [min(v.co[k] for v in mesh.vertices) for k in range(3)], [max(v.co[k] for v in mesh.vertices) for k in range(3)]
    print("BUILT %s verts=%d tris=%d tentacles=%d box x %.3f..%.3f z(godot) %.3f..%.3f up %.3f..%.3f" % (
        name, len(mesh.vertices), tris, count, box[0][0], box[1][0], -box[1][1], -box[0][1], box[0][2], box[1][2]))
    bad = wrong_by["column"] + wrong_by["tentacle"]
    print("WINDING %s: %s: column %d/%d wrong, tentacles %d/%d wrong" % (
        name, "ok" if bad == 0 else "INSIDE OUT", wrong_by["column"], counted_by["column"],
        wrong_by["tentacle"], counted_by["tentacle"]))
    return obj


def make_game(name):
    global GAME
    GAME = GAME_MODEL
    try:
        return make(name, False)
    finally:
        GAME = None


def export_one(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", export_yup=True, use_selection=True,
        export_animations=False, export_vertex_color="ACTIVE", export_texcoords=True,
    )


def render(folder, made):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_cavity = True
    scene.display.shading.show_backface_culling = True
    scene.render.resolution_x, scene.render.resolution_y = 1200, 900
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 100.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    views = [("side", (1, 0, 0.0001), (0, 0, 0.09), 0.7), ("side2", (0, 1, 0.0001), (0, 0, 0.09), 0.7),
             ("top", (0.0001, 0, 1), (0, 0, 0), 0.7), ("under", (0.0001, 0, -1), (0, 0, 0), 0.7),
             ("quarter", (0.7, 0.6, 0.6), (0, 0, 0.08), 0.75), ("close", (0.7, 0.3, 0.5), (0.1, 0.05, 0.12), 0.25)]
    for low, obj in ((False, made[0]), (True, made[1])):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if low and view not in ("side", "quarter"):
                continue
            offset = Vector(direction).normalized() * 10.0
            camera.data.ortho_scale = frame
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "X" if view in ("top", "under") else "Y").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % ("lo_" if low else "", view))
            bpy.ops.render.render(write_still=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    full = make(NAME, False)
    low = make(NAME + "_lo", True)
    game = make_game(NAME + "_game")
    export_one(full, os.path.join(OUT, NAME + ".glb"))
    export_one(low, os.path.join(OUT, NAME + "_lo.glb"))
    export_one(game, os.path.join(OUT, NAME + "_game.glb"))
    low.location.x = 0.7
    game.location.x = 1.4
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, NAME + ".blend"))
    low.location.x = 0.0
    game.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low, game])


if __name__ == "__main__":
    main()
