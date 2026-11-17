"""Builds the moon jelly (models/moon_jelly.glb) for Godot.

Run from the project's root:
    blender --background --python tools/build_moon_jelly.py
    blender --background --python tools/build_moon_jelly.py -- <preview folder>   # with pictures from six sides

Writes models/moon_jelly.glb (one static mesh) and tools/blend/moon_jelly.blend (editable).

A moon jelly (Aurelia aurita), after the user's own aquarium photographs (2026-11-17): a shallow
translucent saucer, thick in the middle and thin at the rim; a bright rim line cut into eight shallow
lobes; fine canals running out to the rim; four horseshoe gonads round the middle, seen through the
bell; a fringe of hundreds of short hair-fine tentacles; and four frilled oral arms that lie out from the middle along the
underside of the bell, one to each quarter, with loose ends near the rim (the user, 2026-11-17,
with a picture: "its not a long center tail but 4 ridges with loose ends along the dome").

The bell is 1 unit in radius (the game scales it); the origin is the middle of the rim's plane, Y up.

The model is still: shaders/moon_jelly.gdshader beats the bell, sways the fringe, and lays each
oral arm along a chain of points simulated like a rope in scripts/moon_jelly.gd. What each point is:

- vertex colour red, the part: 0 the top of the bell, 0.25 its underside and the stalk the arms hang
  from, 0.5 a gonad, 0.75 an oral arm, 1 a fringe tentacle
- vertex colour green: which oral arm (k / 4 + 0.125)
- UV.x across (round the bell 0..1; across an arm 0..1), UV.y along (bell: 0 the crown to 1 the rim;
  an arm or a tentacle: 0 its root to 1 its tip)
- UV2.x a tentacle's length, UV2.y its phase (0..1)
(The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.)

An arm hangs straight down from its root at rest: the shader takes each point's offset from that
line. ARM_* are kept in step with scripts/moon_jelly.gd.
"""

import math
import os
import random
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "models")
BLEND = os.path.join(HERE, "blend")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = ARGS[0] if ARGS else ""

HEIGHT = 0.42
INNER_HEIGHT = 0.2
LOBES = 8
# Kept in step with scripts/moon_jelly.gd and the shader.
ARMS = 4
ARM_ROOT = 0.07
ARM_Y = 0.08
ARM_LONG = 0.85

PART_TOP = 0.0
PART_UNDER = 0.25
PART_GONAD = 0.5
PART_ARM = 0.75
PART_FRINGE = 1.0


def to_b(p):
    return Vector((p.x, -p.z, p.y))


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.data = {}

    def add(self, p, uv, uv2, part, green=0.0):
        self.verts.append(p)
        i = len(self.verts) - 1
        self.data[i] = ((uv[0], 1.0 - uv[1]), (uv2[0], 1.0 - uv2[1]), (part, green, 0.0, 1.0))
        return i

    def quad(self, a, b, c, d):
        self.faces.append((a, b, c, d))


def bell_point(v, a, inner):
    """A point of the bell: v 0 at the crown to 1 at the rim, a round it."""
    # (past the widest point the rim turns in and down a little: a lip)
    phi = v * (math.pi * 0.5 + 0.22)
    rad = math.sin(phi) ** 0.8
    y = HEIGHT * math.cos(phi) if phi < math.pi * 0.5 else 0.5 * math.cos(phi)
    rim = smooth(0.82, 1.0, v)
    # eight shallow lobes: a notch between each pair
    notch = abs(math.cos(a * LOBES * 0.5)) ** 10
    rad -= 0.035 * rim * notch
    y += 0.03 * rim * notch
    if inner:
        # the underside: the jelly is thick in the middle and thins to nothing at the rim
        y = mix(INNER_HEIGHT * math.cos(min(phi, math.pi * 0.5)) ** 0.8, y, smooth(0.8, 1.0, v))
        rad *= mix(0.97, 1.0, smooth(0.8, 1.0, v))
    return Vector((math.cos(a) * rad, y, math.sin(a) * rad))


def mix(a, b, t):
    return a + (b - a) * t


def bell(m):
    around = 128
    rings = 36
    for inner in (False, True):
        rows = []
        for r in range(rings + 1):
            # (rings gathered towards the rim, where it bends most)
            v = (r / rings) ** 0.8
            row = []
            for c in range(around + 1):
                a = c / around * math.tau
                p = bell_point(v, a, inner)
                row.append(m.add(p, (c / around, v), (0.0, 0.0), PART_UNDER if inner else PART_TOP))
            rows.append(row)
        for r in range(rings):
            for c in range(around):
                a, b = rows[r][c], rows[r][c + 1]
                d, e = rows[r + 1][c], rows[r + 1][c + 1]
                if inner:
                    m.quad(a, d, e, b)
                else:
                    m.quad(a, b, e, d)


def stalk(m):
    """The short stalk under the middle of the bell that the four arms hang from: four-cornered."""
    around = 32
    rows = []
    for r in range(7):
        t = r / 6
        y = mix(INNER_HEIGHT, ARM_Y - 0.02, t)
        row = []
        for c in range(around + 1):
            a = c / around * math.tau
            # (a cross in section, its corners towards the arms)
            rad = (0.2 * (1.0 - t) ** 2 + 0.075) * (1.0 + 0.3 * math.cos((a - math.pi * 0.25) * 4.0) * t)
            row.append(m.add(Vector((math.cos(a) * rad, y, math.sin(a) * rad)), (c / around, 0.2), (0.0, 0.0), PART_UNDER))
        rows.append(row)
    for r in range(6):
        for c in range(around):
            m.quad(rows[r][c], rows[r][c + 1], rows[r + 1][c + 1], rows[r + 1][c])


def gonads(m):
    """Four horseshoes round the middle, in the jelly between the top and the underside, each
    open towards the middle."""
    rng = random.Random(7)
    steps = 56
    sides = 10
    for k in range(4):
        a = math.pi * 0.25 + k * math.pi * 0.5
        out = Vector((math.cos(a), 0.0, math.sin(a)))
        side = Vector((-math.sin(a), 0.0, math.cos(a)))
        middle = out * 0.3
        rows = []
        for s_i in range(steps + 1):
            s = s_i / steps
            # (from one side of the gap round to the other; the gap faces the middle)
            t = math.pi + 0.5 + s * (math.tau - 1.0)
            loop_r = 0.155 * (1.0 + 0.06 * math.sin(s * 19.0 + k))
            centre = middle + out * math.cos(t) * loop_r * 1.12 + side * math.sin(t) * loop_r
            reach = math.hypot(centre.x, centre.z)
            # (it lies in the jelly: nearer the underside than the top)
            phi = math.asin(min(reach, 0.99) ** 1.25)
            centre.y = mix(INNER_HEIGHT * math.cos(phi) ** 0.8, HEIGHT * math.cos(phi), 0.3)
            along = (out * -math.sin(t) * 1.12 + side * math.cos(t)).normalized()
            across = along.cross(Vector((0.0, 1.0, 0.0))).normalized()
            # (thick and lumpy in its middle, thin at its ends)
            thick = 0.036 * (0.35 + 0.65 * math.sin(s * math.pi) ** 0.5) * (1.0 + 0.25 * rng.uniform(-1.0, 1.0))
            row = []
            for c in range(sides):
                b = c / sides * math.tau
                p = centre + across * math.cos(b) * thick * 1.25 + Vector((0.0, 1.0, 0.0)) * math.sin(b) * thick * 0.6
                row.append(m.add(p, (c / sides, s), (0.0, 0.0), PART_GONAD))
            rows.append(row)
        for s_i in range(steps):
            for c in range(sides):
                n = (c + 1) % sides
                m.quad(rows[s_i][c], rows[s_i][n], rows[s_i + 1][n], rows[s_i + 1][c])


def oral_arm(m, k):
    """A frilled ribbon folded along its middle into a V, hanging straight down from its root."""
    a = math.pi * 0.25 + k * math.pi * 0.5
    root = Vector((math.cos(a) * ARM_ROOT, ARM_Y, math.sin(a) * ARM_ROOT))
    out = Vector((math.cos(a), 0.0, math.sin(a)))
    side = Vector((-math.sin(a), 0.0, math.cos(a)))
    steps = 64
    across = 12
    rows = []
    for s_i in range(steps + 1):
        s = s_i / steps
        # (broad below the root, narrowing to a blunt tip)
        width = (0.06 + 0.07 * smooth(0.0, 0.3, s)) * (1.0 - 0.35 * s * s) + 0.01
        row = []
        for w_i in range(across + 1):
            u = w_i / across * 2.0 - 1.0
            edge = abs(u)
            # the fold opens outwards; its edges are ruffled, more the nearer the edge
            fold = edge * width * 0.75
            ruffle = math.sin(s * 38.0 + k * 1.7 + u * 1.5) * 0.04 * edge ** 2.5 * (1.0 - 0.5 * s)
            ruffle += math.sin(s * 95.0 + k * 0.9) * 0.018 * edge ** 4
            # (the fold opens away from `out`: once the shader has laid the arm out along the underside
            # of the bell, that is downwards, so its frilled edges hang)
            p = root + Vector((0.0, -s * ARM_LONG, 0.0)) + side * u * width - out * (fold + ruffle)
            p.y += math.cos(s * 38.0 + k * 1.7) * 0.016 * edge ** 3
            row.append(m.add(p, ((u + 1.0) * 0.5, s), (0.0, 0.0), PART_ARM, k / 4.0 + 0.125))
        rows.append(row)
    for s_i in range(steps):
        for w_i in range(across):
            m.quad(rows[s_i][w_i], rows[s_i][w_i + 1], rows[s_i + 1][w_i + 1], rows[s_i + 1][w_i])


def fringe(m):
    """Hundreds of hair-fine tentacles round the rim: each a thin tapering strip hanging down."""
    rng = random.Random(3)
    count = 420
    steps = 8
    for i in range(count):
        a = (i + rng.uniform(-0.3, 0.3)) / count * math.tau
        root = bell_point(1.0, a, False)
        root.y += 0.01
        long = rng.uniform(0.26, 0.58) * (1.0 if i % 3 else 1.25)
        phase = rng.random()
        side = Vector((-math.sin(a), 0.0, math.cos(a)))
        rows = []
        for s_i in range(steps + 1):
            s = s_i / steps
            half = 0.0045 * (1.0 - 0.8 * s)
            p = root + Vector((0.0, -s * long, 0.0))
            rows.append((m.add(p - side * half, (0.0, s), (long, phase), PART_FRINGE),
                         m.add(p + side * half, (1.0, s), (long, phase), PART_FRINGE)))
        for s_i in range(steps):
            m.quad(rows[s_i][0], rows[s_i][1], rows[s_i + 1][1], rows[s_i + 1][0])


def make(name):
    m = Mesh()
    bell(m)
    stalk(m)
    gonads(m)
    for k in range(ARMS):
        oral_arm(m, k)
    fringe(m)
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
        poly.use_smooth = True
    mesh.color_attributes.active_color = mesh.color_attributes["Color"]
    mesh.color_attributes.render_color_index = mesh.color_attributes.find("Color")
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    material = bpy.data.materials.new("jelly")
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.75, 0.85, 1.0, 1.0)
    mesh.materials.append(material)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    print("BUILT %s verts=%d tris=%d" % (name, len(mesh.vertices), tris))
    # Inside-out check: the top of the bell must face out and up, its underside in and down.
    wrong = 0
    for poly in mesh.polygons:
        part = m.data[poly.vertices[0]][2][0]
        if part > 0.1:
            continue
        c = poly.center
        outward = Vector((c.x, c.y, c.z + 0.3))
        if poly.normal.dot(outward) < 0.0:
            wrong += 1
    print("WINDING top-of-bell faces pointing in: %d" % wrong)
    return obj


def render(folder, obj):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_xray = True
    scene.display.shading.xray_alpha = 0.6
    scene.render.resolution_x, scene.render.resolution_y = 1000, 1000
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.03, 0.12)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    views = [("front", (0, -1, 0.0), (0, 0, -0.5), 3.2), ("side", (1, 0, 0.0), (0, 0, -0.5), 3.2),
             ("back", (0, 1, 0.0), (0, 0, -0.5), 3.2), ("left", (-1, 0, 0.0), (0, 0, -0.5), 3.2),
             ("top", (0.0, -0.01, 1.0), (0, 0, 0), 2.4), ("under", (0.1, -0.3, -1.0), (0, 0, 0), 2.4),
             ("close", (0.6, -0.8, 0.25), (0, 0, 0.1), 1.6)]
    for view, direction, target, frame in views:
        offset = Vector(direction).normalized() * 40.0
        camera.data.ortho_scale = frame
        camera.location = Vector(target) + offset
        camera.rotation_euler = (-offset).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = os.path.join(folder, "%s.png" % view)
        bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    obj = make("moon_jelly")
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(BLEND, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(OUT, "moon_jelly.glb"), export_format="GLB", export_yup=True, use_selection=True,
        export_animations=False, export_vertex_color="ACTIVE", export_texcoords=True,
    )
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(BLEND, "moon_jelly.blend"))
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, obj)


if __name__ == "__main__":
    main()
