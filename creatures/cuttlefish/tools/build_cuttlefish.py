"""Builds the cuttlefish (creatures/cuttlefish) and exports it for Godot.

Run from the game's root:
    blender --background --factory-startup --python creatures/cuttlefish/tools/build_cuttlefish.py
    blender --background --factory-startup --python creatures/cuttlefish/tools/build_cuttlefish.py -- <folder for pictures>

Writes creatures/cuttlefish/models/cuttlefish.glb (the full model) and cuttlefish_lo.glb (far off, or many: fewer
rings), and the editable creatures/cuttlefish/tools/cuttlefish.blend (this folder has a .gdignore). Each is one static
mesh with one surface: the shader (cuttlefish.gdshader) ripples the fin, bends the mantle (`curl`), bends and
spreads the arms, shoots out the tentacles and draws the skin. It prints a WINDING line: the check that nothing is
inside out (every face is given a point it must look away from; a face that does not is counted).

A common cuttlefish (Sepia officinalis), 0.4 m from the arms' tips to the mantle's end:

- THE MANTLE: a broad oval, flattened top to bottom (its back a low dome over the cuttlebone, its belly flatter),
  widest about two fifths of the way back, rounded at its end; its back's front edge a blunt lobe over the head.
- THE FIN: a thin skirt all along each side of the mantle, from the collar nearly to its end, narrow at both ends
  (two sheets back to back, one looking up and one down, so that it is seen from both sides in one solid draw).
- THE HEAD: short, nearly as wide as the mantle, a big eye bulging from each side (its W-shaped pupil is drawn by
  the shader), the siphon under it.
- THE ARMS: eight, short, thick at the root, drawn together into a pointed bunch ahead of the head.
- THE TENTACLES: two, kept hidden; built at full stretch (0.2 m, a thin stalk and a flattened club) so that the
  shader can shoot them out (`strike`) or fold them away inside the bunch of arms.

Godot space until it is written out (metres, Y up): it swims ARMS FIRST, towards -Z; its mantle's end is towards
+Z; its back is +Y. The origin is on its middle line half way along its length (the arms' tips 0.2 m ahead).

What a point is, for the shader: vertex colour red the part (0 the mantle, 0.2 the fin, 0.4 the head and siphon,
0.6 an eye, 0.8 an arm, 1 a tentacle); green, on the fin, 0 the sheet that looks up and 1 the one that looks down;
blue, on an arm or a tentacle, which ((n + 0.5) / 16: arms 0 to 7, tentacles 8 and 9). UV.x round it (an arm or a
tentacle: 0.5 down the middle of its inner face; the fin: 0 where it joins the mantle to 1 at its edge; the mantle:
0 on its +X side, going round over its back), UV.y along it (the mantle and the fin: 0 at the collar to 1 at the
mantle's end; an arm or a tentacle: root 0 to tip 1). UV2.x an arm's or tentacle's length, UV2.y an arm's rest
angle (radians, towards its middle line: the bunch). (The glTF writer flips V: what is written here is 1 - v, so
that Godot reads v.)
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
TAU = math.tau
NAME = "cuttlefish"

# Kept in step with cuttlefish.gd and the shader.
MANTLE_FROM = -0.06
MANTLE_LONG = 0.26
FIN_FROM = 0.03
FIN_TO = 0.95
FIN_WIDE = 0.014
ARMS = 8
ARM_RX = 0.019
ARM_RY = 0.014
ARM_Z = -0.126
ARM_LONG = 0.075
TENTACLE_LONG = 0.2
TENTACLE_X = 0.005
TENTACLE_Y = -0.004
TENTACLE_Z = -0.12
EYE = Vector((0.042, 0.014, -0.09))
EYE_R = 0.0165
EYE_OUT = Vector((1.0, 0.32, 0.0)).normalized()


def to_b(p):
    return Vector((p.x, -p.z, p.y))


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.data = []
        self.wound = {}

    def add(self, p, uv, uv2, colour):
        self.verts.append(p)
        self.data.append(((uv[0], 1.0 - uv[1]), (uv2[0], 1.0 - uv2[1]), colour))
        return len(self.verts) - 1

    def face(self, points, kind, away):
        """A face; `away` is a point it must look away from (None: any way will do)."""
        self.faces.append(tuple(points))
        tally = self.wound.setdefault(kind, [0, 0])
        if away is not None:
            ps = [self.verts[i] for i in points]
            normal = Vector()
            for i in range(len(ps)):
                normal += ps[i].cross(ps[(i + 1) % len(ps)])
            if normal.length > 1e-16:
                tally[1] += 1
                middle = sum(ps, Vector()) / len(ps)
                if normal.dot(middle - away) <= 0.0:
                    tally[0] += 1


def mantle_wide(t):
    """Half the mantle's width, `t` from the collar (0) to its end (1): an oval, widest two fifths back."""
    c = 0.42
    f = (t - c) / (0.62 if t < c else 0.58)
    return 0.064 * max(1.0 - abs(f) ** 2.6, 0.0) ** (1.0 / 2.6)


def mantle_point(t, a, shrink=1.0):
    """A point of the mantle: `a` round it from its +X side over its back."""
    w = mantle_wide(t) * shrink
    s = math.sin(a)
    # (a low dome above, flatter below)
    y = s * w * (0.5 if s > 0.0 else 0.36)
    # (the back's front edge reaches forward over the head as a blunt lobe)
    z = MANTLE_FROM + t * MANTLE_LONG - 0.014 * max(s, 0.0) ** 2 * (1.0 - smooth(0.0, 0.12, t))
    return Vector((math.cos(a) * w, y, z))


def mantle(m, low):
    around = 14 if low else 48
    rings_n = 8 if low else 40
    colour = (0.0, 0.0, 0.0, 1.0)
    rings = []
    # (the lip of the collar: turned in, so that its edge has a thickness and the head's neck goes inside it)
    for shrink, deep in ((0.8, 0.012), (0.9, 0.0)):
        rings.append([m.add(mantle_point(0.0, c / around * TAU, shrink) + Vector((0.0, 0.0, deep)), (c / around, 0.0), (0.0, 0.0), colour) for c in range(around)])
    for r in range(rings_n):
        # (closer rings at both ends, where it rounds)
        t = 0.5 - 0.5 * math.cos(math.pi * r / rings_n)
        rings.append([m.add(mantle_point(t, c / around * TAU), (c / around, t), (0.0, 0.0), colour) for c in range(around)])
    for a, b in zip(rings[2:], rings[3:]):
        middle = (sum((m.verts[i] for i in a), Vector()) + sum((m.verts[i] for i in b), Vector())) / (2 * around)
        for c in range(around):
            d = (c + 1) % around
            m.face((a[c], a[d], b[d], b[c]), "mantle", middle)
    end = m.add(Vector((0.0, 0.0, MANTLE_FROM + MANTLE_LONG)), (0.0, 1.0), (0.0, 0.0), colour)
    last = rings[-1]
    for c in range(around):
        m.face((last[c], last[(c + 1) % around], end), "mantle", Vector((0.0, 0.0, MANTLE_FROM + MANTLE_LONG - 0.05)))
    # the lip: its inside looks in, towards the neck
    for a, b in ((rings[0], rings[1]), (rings[1], rings[2])):
        for c in range(around):
            d = (c + 1) % around
            mid = (m.verts[a[c]] + m.verts[b[d]]) * 0.5
            away = Vector((mid.x * 3.0, mid.y * 3.0, mid.z)) if a is rings[0] else mid + Vector((0.0, 0.0, 1.0))
            m.face((a[c], a[d], b[d], b[c]), "lip", away)


def fin(m, low):
    along_n = 10 if low else 56
    across_n = 1 if low else 6
    for side in (1.0, -1.0):
        for sheet in (0.0, 1.0):
            rows = []
            for i in range(along_n + 1):
                t = FIN_FROM + (FIN_TO - FIN_FROM) * i / along_n
                u = i / along_n
                wide = FIN_WIDE * math.sin(math.pi * u) ** 0.45 * (1.0 - 0.35 * u)
                root = mantle_point(t, 0.0 if side > 0.0 else math.pi, 0.96)
                row = []
                for j in range(across_n + 1):
                    w = j / across_n
                    p = root + Vector((side * (mantle_wide(t) * 0.04 + wide) * w, -0.0025 * w * w, 0.0))
                    row.append(m.add(p, (w, t), (0.0, 0.0), (0.2, sheet, 0.0, 1.0)))
                rows.append(row)
            for i in range(along_n):
                for j in range(across_n):
                    quad = (rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j])
                    if (side > 0.0) != (sheet > 0.5):
                        quad = quad[::-1]
                    middle = sum((m.verts[v] for v in quad), Vector()) / 4.0
                    # (the upper sheet looks up: away from a point below it; the lower one down)
                    m.face(quad, "fin", middle + Vector((0.0, -1.0 if sheet < 0.5 else 1.0, 0.0)))


# (z, half width, half height): the neck inside the mantle, the head at the eyes, the front the arms leave
HEAD = [(-0.03, 0.04, 0.021), (-0.05, 0.046, 0.026), (-0.07, 0.049, 0.029), (-0.09, 0.05, 0.03), (-0.106, 0.046, 0.028),
        (-0.118, 0.038, 0.025), (-0.128, 0.028, 0.02), (-0.135, 0.015, 0.012)]


def head(m, low):
    around = 10 if low else 32
    colour = (0.4, 0.0, 0.0, 1.0)
    rings = []
    for z, rx, ry in HEAD:
        rings.append([m.add(Vector((math.cos(c / around * TAU) * rx, math.sin(c / around * TAU) * ry, z)), (c / around, 0.0), (0.0, 0.0), colour) for c in range(around)])
    for a, b in zip(rings, rings[1:]):
        middle = Vector((0.0, 0.0, (m.verts[a[0]].z + m.verts[b[0]].z) * 0.5))
        for c in range(around):
            d = (c + 1) % around
            m.face((a[c], b[c], b[d], a[d]), "head", middle)
    front = m.add(Vector((0.0, 0.0, -0.138)), (0.0, 0.0), (0.0, 0.0), colour)
    for c in range(around):
        m.face((rings[-1][c], front, rings[-1][(c + 1) % around]), "head", Vector((0.0, 0.0, -0.12)))
    # The siphon: a short funnel under the head, out from under the collar, its mouth open forwards.
    n = 8 if low else 14
    rings = []
    for z, r, y in ((-0.035, 0.012, -0.022), (-0.06, 0.009, -0.029), (-0.078, 0.0065, -0.031), (-0.078, 0.0045, -0.031), (-0.066, 0.004, -0.03)):
        rings.append([m.add(Vector((math.cos(c / n * TAU) * r, y + math.sin(c / n * TAU) * r * 0.8, z)), (0.0, 0.0), (0.0, 0.0), colour) for c in range(n)])
    for i, (a, b) in enumerate(zip(rings, rings[1:])):
        middle = (sum((m.verts[j] for j in a), Vector()) + sum((m.verts[j] for j in b), Vector())) / (2 * n)
        for c in range(n):
            d = (c + 1) % n
            away = middle if i < 2 else (middle + Vector((0.0, 0.0, 1.0)) if i == 2 else None)
            m.face((a[c], b[c], b[d], a[d]), "siphon", away)


def eyes(m, low):
    around = 8 if low else 24
    rings_n = 3 if low else 10
    for side in (1.0, -1.0):
        centre = Vector((EYE.x * side, EYE.y, EYE.z))
        out = Vector((EYE_OUT.x * side, EYE_OUT.y, EYE_OUT.z))
        along = Vector((0.0, 0.0, 1.0))
        up = out.cross(along).normalized()
        across = out.cross(up).normalized()
        colour = (0.6, 0.0, 0.0, 1.0)
        rings = []
        for r in range(rings_n + 1):
            polar = r / rings_n * math.pi * 0.62
            rings.append([m.add(centre + (out * math.cos(polar) + (up * math.cos(c / around * TAU) + across * math.sin(c / around * TAU)) * math.sin(polar)) * EYE_R,
                                (0.0, 0.0), (0.0, 0.0), colour) for c in range(around)])
        tip = rings[0][0]
        for a, b in zip(rings[1:], rings[2:]):
            for c in range(around):
                d = (c + 1) % around
                m.face((a[c], b[c], b[d], a[d]), "eyes", centre)
        for c in range(around):
            m.face((tip, rings[1][c], rings[1][(c + 1) % around]), "eyes", centre)


def arm(k):
    """Arm k: its root, the way out from the middle it leans (a unit), its rest angle and its length."""
    a = (k + 0.5) * TAU / ARMS
    out = Vector((math.cos(a), math.sin(a), 0.0))
    root = Vector((math.cos(a) * ARM_RX, math.sin(a) * ARM_RY, ARM_Z))
    long = ARM_LONG * (1.0 - 0.1 * math.sin(a))
    # (leaning in towards the middle line, so that the eight make a pointed bunch)
    rest = -math.atan2(0.88 * Vector((root.x, root.y)).length, long)
    return root, out, rest, long


def arm_way(k):
    _root, out, rest, _long = arm(k)
    return Vector((0.0, 0.0, -1.0)) * math.cos(rest) + out * math.sin(rest)


def arm_radius(s):
    return 0.0074 * (1.0 - s) ** 0.8 + 0.0007


def arm_point(k, s, around_at):
    root, out, rest, long = arm(k)
    way = arm_way(k)
    e_out = (out - way * out.dot(way)).normalized()
    e_side = way.cross(e_out)
    a = around_at * TAU
    r = arm_radius(s)
    # (rounded outside, a flatter inner face that the suckers are on)
    flat = 0.7 if math.cos(a) < 0.0 else 1.0
    return root + way * long * s + (e_out * math.cos(a) * flat + e_side * math.sin(a)) * r


def arms(m, low):
    steps = 5 if low else 22
    around = 5 if low else 12
    for k in range(ARMS):
        root, _out, rest, long = arm(k)
        way = arm_way(k)
        colour = (0.8, 0.0, (k + 0.5) / 16.0, 1.0)
        rings = []
        # (it starts inside the head: this ring is at s = 0, back inside)
        rings.append([m.add(arm_point(k, 0.0, c / around) - way * 0.012, (c / around, 0.0), (long, rest), colour) for c in range(around + 1)])
        for i in range(steps + 1):
            s = i / steps
            rings.append([m.add(arm_point(k, s, c / around), (c / around, s), (long, rest), colour) for c in range(around + 1)])
        for a, b in zip(rings, rings[1:]):
            middle = (sum((m.verts[i] for i in a[:around]), Vector()) + sum((m.verts[i] for i in b[:around]), Vector())) / (2 * around)
            for c in range(around):
                m.face((a[c], a[c + 1], b[c + 1], b[c]), "arms", middle)
        tip = m.add(root + way * (long + 0.0012), (0.5, 1.0), (long, rest), colour)
        last = rings[-1]
        for c in range(around):
            m.face((last[c], last[c + 1], tip), "arms", root + way * (long - 0.01))


def tentacle_radius(s):
    club = smooth(0.7, 0.8, s) * (1.0 - smooth(0.93, 1.0, s))
    return 0.0024 - 0.0006 * s + 0.0034 * club


def tentacles(m, low):
    steps = 8 if low else 40
    around = 4 if low else 10
    for k in (ARMS, ARMS + 1):
        side = 1.0 if k == ARMS else -1.0
        root = Vector((side * TENTACLE_X, TENTACLE_Y, TENTACLE_Z))
        colour = (1.0, 0.0, (k + 0.5) / 16.0, 1.0)
        rings = []
        for i in range(steps + 1):
            s = i / steps
            r = tentacle_radius(s)
            # (the club is flat: wide across, thin through; its suckered face (0.5 round) looks in, to the other)
            flat = 1.0 - 0.45 * smooth(0.7, 0.8, s)
            ring = []
            for c in range(around + 1):
                a = c / around * TAU
                p = root + Vector((0.0, 0.0, -TENTACLE_LONG * s)) + Vector((side * math.cos(a) * r * flat, math.sin(a) * r, 0.0))
                ring.append(m.add(p, (c / around, s), (TENTACLE_LONG, 0.0), colour))
            rings.append(ring)
        for a, b in zip(rings, rings[1:]):
            middle = (sum((m.verts[i] for i in a[:around]), Vector()) + sum((m.verts[i] for i in b[:around]), Vector())) / (2 * around)
            for c in range(around):
                quad = (a[c], b[c], b[c + 1], a[c + 1])
                m.face(quad if side > 0.0 else quad[::-1], "tentacles", middle)
        for end, z_in in ((rings[0], 0.01), (rings[-1], -0.01)):
            cap = m.add(sum((m.verts[i] for i in end[:around]), Vector()) / around + Vector((0.0, 0.0, -z_in * 0.1)), (0.5, 0.0 if z_in > 0 else 1.0), (TENTACLE_LONG, 0.0), colour)
            centre = m.verts[cap] + Vector((0.0, 0.0, z_in))
            for c in range(around):
                tri = (end[c], end[c + 1], cap)
                tri = tri if (side > 0.0) != (z_in > 0.0) else tri[::-1]
                m.face(tri, "tentacles", centre)


def make(name, low):
    m = Mesh()
    mantle(m, low)
    fin(m, low)
    head(m, low)
    eyes(m, low)
    arms(m, low)
    tentacles(m, low)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) for p in m.verts], [], m.faces)
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
            uv[poly.loop_start + corner].uv = d[0]
            uv2[poly.loop_start + corner].uv = d[1]
            colour[poly.loop_start + corner].color = d[2]
    mesh.color_attributes.active_color = mesh.color_attributes["Color"]
    mesh.color_attributes.render_color_index = mesh.color_attributes.find("Color")
    material = bpy.data.materials.get("cuttlefish_skin") or bpy.data.materials.new("cuttlefish_skin")
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.5, 0.4, 0.28, 1.0)
    material.diffuse_color = (0.5, 0.4, 0.28, 1.0)
    mesh.materials.append(material)
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    print("BUILT %s verts=%d tris=%d" % (name, len(mesh.vertices), tris))
    wrong = sum(t[0] for t in m.wound.values())
    print("WINDING %s: %s: %s" % (name, "ok" if wrong == 0 else "INSIDE OUT",
                                  ", ".join("%s %d/%d wrong" % (kind, t[0], t[1]) for kind, t in m.wound.items())))
    return obj


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
    scene.render.resolution_x, scene.render.resolution_y = 1600, 800
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    # (Blender: it lies along Y, its arms towards +Y, its back +Z)
    body = (0.0, 0.0, 0.0)
    views = [("side", (1, 0, 0), body, 0.5), ("other_side", (-1, 0, 0), body, 0.5), ("above", (0, 0.001, 1), body, 0.5),
             ("below", (0, 0.001, -1), body, 0.5), ("front", (0, 1, 0.0), body, 0.25), ("back", (0, -1, 0.0), body, 0.25),
             ("head", (0.7, 0.6, 0.4), (0, 0.11, 0), 0.18), ("quarter", (-0.6, -0.5, 0.5), body, 0.5)]
    for low, obj in ((False, made[0]), (True, made[1])):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if low and view not in ("side", "above", "head"):
                continue
            offset = Vector(direction).normalized() * 10.0
            camera.data.ortho_scale = frame
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "X" if view in ("above", "below") else "Y").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % ("lo_" if low else "", view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    full = make(NAME, False)
    low = make(NAME + "_lo", True)
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, NAME + ".glb"))
    export_one(low, os.path.join(OUT, NAME + "_lo.glb"))
    low.location.x = 0.3
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, NAME + ".blend"))
    low.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low])


if __name__ == "__main__":
    main()
