"""Builds the net that hangs beside the shrimp boat, where the fish is sold (DESIGN.md, the loop).

    "C:/Program Files/Blender Foundation/Blender 4.3/blender.exe" --background --factory-startup --python tools/build_boat_net.py [-- <folder for pictures>]

Writes models/boat_net.glb and tools/blend/boat_net.blend (editable). Swimming into its hoop ends a run as a sale
(scripts/main.gd). The helpers (Build, tube, lathe, the inside-out check, the pictures) and the materials are
tools/build_fishing_gear.py's own: its top part is run here, not copied.

Written in Godot's axes (metres, Y up, -Z ahead). One object, BoatNet, its origin at the middle of the hoop:
  hoop      a steel ring 0.8 m round (HOOP), upright, its opening facing -Z
  bag       a tapering bag of net behind it (+Z), 2.4 m long, closed at its end; material "net" (two-sided, drawn
            by shaders/net.gdshader from its UVs, in metres round and along, as the trawl's)
  bridle    three ropes from the top and the sides of the hoop up to a ring 1.1 m over its middle
  line      the rope from that ring straight up LINE metres (to the boat's starboard outrigger end)
"""

import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
source = open(os.path.join(HERE, "build_fishing_gear.py")).read()
# (everything but its last line, which builds the fishing gear)
exec(compile(source[:source.rstrip().rfind("main()")], "build_fishing_gear.py", "exec"))

GLB = os.path.join(ROOT, "models", "boat_net.glb")
BLEND = os.path.join(HERE, "blend", "boat_net.blend")
HOOP = 0.8
BAG = 2.4
LINE = 12.0
RING = 1.1


def bag_radius(z):
    s = z / BAG
    return HOOP * (1.0 - 0.78 * s ** 0.9) + 0.03 * math.sin(s * math.pi)


def boat_net(line=True):
    b = Build("BoatNet" if line else "BoatNetClose")
    sides = 14
    loop = [(HOOP * math.cos(math.tau * k / 20), HOOP * math.sin(math.tau * k / 20), 0.0) for k in range(20)]
    tube(b, "hoop", loop, 0.025, 6, "steel", loop=True)
    zs = [0.02, 0.4, 0.85, 1.3, 1.75, 2.1, 2.3]
    verts, faces, uvs = [], [], []
    for z in zs:
        r = bag_radius(z)
        for j in range(sides + 1):
            t = math.tau * j / sides
            verts.append((r * math.cos(t), r * math.sin(t), z))
    tip = len(verts)
    verts.append((0.0, -0.08, BAG))
    per = sides + 1

    def round_m(k, j):
        return j / sides * math.tau * bag_radius(zs[k])

    for k in range(len(zs) - 1):
        for j in range(sides):
            p, q = k * per + j, (k + 1) * per + j
            faces.append([p, q, q + 1, p + 1])
            uvs.append([(round_m(k, j), zs[k]), (round_m(k + 1, j), zs[k + 1]), (round_m(k + 1, j + 1), zs[k + 1]), (round_m(k, j + 1), zs[k])])
    k = len(zs) - 1
    for j in range(sides):
        p = k * per + j
        faces.append([p, tip, p + 1])
        uvs.append([(round_m(k, j), zs[k]), (round_m(k, j) + 0.1, BAG), (round_m(k, j + 1), zs[k])])
    # (outwards: one face against its place; all flipped if wrong. Drawn two-sided anyway.)
    v0 = [Vector(verts[i]) for i in faces[0]]
    n = (v0[1] - v0[0]).cross(v0[2] - v0[0])
    centre = sum(v0, Vector()) / 4
    if n.dot(Vector((centre.x, centre.y, 0.0))) < 0:
        faces = [list(reversed(f)) for f in faces]
        uvs = [list(reversed(u)) for u in uvs]
    b.part("bag", verts, faces, "net", closed=False, uvs=uvs)
    top = (0.0, RING, 0.0)
    for a in (math.pi * 0.5, math.pi * 0.5 + 1.0, math.pi * 0.5 - 1.0):
        rod(b, "bridle", (HOOP * math.cos(a), HOOP * math.sin(a), 0.0), top, 0.012, 0.012, 4, "rope")
    lathe(b, "ring", [(0.0, -0.05), (0.045, -0.03), (0.05, 0.0), (0.045, 0.03), (0.0, 0.05)], 6, "steel", at=top)
    if line:
        rod(b, "line", top, (0.0, LINE, 0.0), 0.014, 0.014, 5, "rope")
    return b


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    b = boat_net()
    wrong, bad = b.inside_out()
    print("NET %s: %d triangles, %d facing inwards" % (b.name, b.tris(), wrong))
    for label, count, of, where in bad:
        print("   bad part %s: %d of %d at %s" % (label, count, of, where))
    print("INSIDE-OUT %s" % ("PASSED" if wrong == 0 else "FAILED (%d)" % wrong))
    obj = b.make()
    os.makedirs(os.path.dirname(BLEND), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.export_scene.gltf(filepath=GLB, export_format="GLB", export_apply=True, export_yup=True, export_cameras=False,
                              export_lights=False, export_animations=False)
    print("WROTE", GLB)
    if ARGS:
        os.makedirs(ARGS[0], exist_ok=True)
        # (and the net without its long line, close enough to see; made after the export, so not in the model)
        render(ARGS[0], [obj, boat_net(False).make()])


build()
