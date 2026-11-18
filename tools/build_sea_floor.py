"""Builds the rocks of the sea floor (models/sea_floor.glb) for Godot.

RETIRED (2026-11-18): nothing loads sea_floor.glb or sea_rocks.json any more, and its `ground` is the old coast's;
the sea is now Monterey Bay, whose floor is scripts/bay.gd (tools/MONTEREY.md). Kept, unused.

Gulp: this is Moon Jellies' tools/build_sea_floor.py (as of its 642f9bd) with the outcrops spread
over a sea 44 m in radius, Gulp's own ground, lighter rocks (320 triangles each), and a list of
each rock as a sphere (models/sea_rocks.json) for the fish to swim round.

Run from the project's root:
    blender --background --python tools/build_sea_floor.py
    blender --background --python tools/build_sea_floor.py -- <preview folder>   # with pictures from four sides

Writes models/sea_floor.glb (one mesh, `rocks`) and tools/blend/sea_floor.blend (editable).

Outcrops of rounded, lumpy rock standing in the sand. The sand itself is not a model: it is
GameCommon's sand (a SandGround, in scripts/sea.gd), whose height is Sea.ground(x, z). `ground` here
is the same sum, so the rocks sit in the sand: change one, change the other.

Godot space until written out: metres, Y up, the middle of the stage at the origin, the camera
mostly to +Z looking -Z.
"""

import json
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector, noise

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "models")
BLEND = os.path.join(HERE, "blend")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = ARGS[0] if ARGS else ""

# Outcrops: (x, z, how big, how many rocks), scattered over the sea with the middle left open
# (where a run starts).
def outcrops():
    rng = random.Random(7)
    made = []
    while len(made) < 26:
        turn = rng.uniform(0.0, math.tau)
        reach = 7.0 + 35.0 * math.sqrt(rng.random())
        x, z = math.cos(turn) * reach, math.sin(turn) * reach
        size = rng.uniform(0.7, 3.2)
        if all(math.hypot(x - o[0], z - o[1]) > (size + o[2]) * 1.8 for o in made):
            made.append((x, z, size, rng.randint(3, 8)))
    return made


OUTCROPS = outcrops()
SPHERES = []


def to_b(p):
    return Vector((p.x, -p.z, p.y))


def ground(x, z):
    """The height of the sand at a point: the same sum as Sea.ground in scripts/sea.gd."""
    h = 0.6 * math.sin(x * 0.07 + 1.3) * math.cos(z * 0.06) + 0.2 * math.sin(x * 0.21 + z * 0.17)
    far = math.hypot(x, z)
    # (banks rising all round the edge of the sea)
    return h + max(0.0, far - 34.0) ** 1.5 * 0.09


def rocks():
    rng = random.Random(11)
    bm = bmesh.new()
    for ox, oz, size, count in OUTCROPS:
        for i in range(count):
            # (the biggest in the middle, smaller ones gathered round it)
            share = 1.0 if i == 0 else rng.uniform(0.25, 0.6)
            reach = 0.0 if i == 0 else rng.uniform(0.6, 1.5) * size
            turn = rng.uniform(0.0, math.tau)
            x = ox + math.cos(turn) * reach
            z = oz + math.sin(turn) * reach
            r = size * share
            squash = Vector((rng.uniform(0.8, 1.3), rng.uniform(0.45, 0.8), rng.uniform(0.8, 1.3)))
            seed = Vector((rng.uniform(0, 50), rng.uniform(0, 50), rng.uniform(0, 50)))
            base = Vector((x, ground(x, z) + r * squash.y * 0.25, z))
            SPHERES.append([round(base.x, 3), round(base.y, 3), round(base.z, 3),
                            round(r * 0.5 * (squash.x + squash.z) * 0.95, 3)])
            made = bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
            for v in made["verts"]:
                d = v.co.normalized()
                # lumps, and flat facets where the rock has split
                lump = 1.0 + 0.3 * noise.noise(d * 1.4 + seed) + 0.1 * noise.noise(d * 4.5 + seed)
                facet = noise.noise(d * 0.9 + seed * 1.7)
                lump -= 0.18 * max(0.0, facet) ** 0.5
                # (a turn, not a mirror image: a mirror image would turn the rock inside out)
                p = Vector((d.x * squash.x, d.z * squash.y, -d.y * squash.z)) * r * lump
                v.co = to_b(base + p)
            for face in {f for v in made["verts"] for f in v.link_faces}:
                face.smooth = True
    mesh = bpy.data.meshes.new("rocks")
    bm.normal_update()
    # Inside-out check: a closed mesh wound outwards has a positive volume.
    print("WINDING rocks volume (must be positive): %.1f" % bm.calc_volume(signed=True))
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("rocks", mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    print("BUILT rocks tris=%d" % tris)
    return obj


def render(folder):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.render.resolution_x, scene.render.resolution_y = 1000, 700
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    for view, direction in (("front", (0, -1, 0.35)), ("right", (1, 0, 0.35)), ("back", (0, 1, 0.35)),
                            ("left", (-1, 0, 0.35)), ("top", (0, -0.01, 1))):
        offset = Vector(direction).normalized() * 105.0
        camera.location = offset
        camera.rotation_euler = (-offset).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = os.path.join(folder, "floor_%s.png" % view)
        bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    made = rocks()
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(BLEND, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    made.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(OUT, "sea_floor.glb"), export_format="GLB", export_yup=True, use_selection=True,
        export_animations=False, export_texcoords=False,
    )
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(BLEND, "sea_floor.blend"))
    with open(os.path.join(OUT, "sea_rocks.json"), "w") as out:
        json.dump(SPHERES, out)
    print("SPHERES %d" % len(SPHERES))
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW)


if __name__ == "__main__":
    main()
