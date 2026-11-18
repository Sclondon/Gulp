"""Shared by the sea's own kit builders (tools/build_<piece>.py; tools/BIOMES.md section 8).

Each builder makes its pieces with GameCommon's sea floor kit machinery (scenery/sea_floor_props/
tools/build_sea_floor_props.py, imported, not copied: its Kit of tubes, lathes and balls with a colour
and a sway at every point, its rock(), its inside-out checks and its json notes), then calls ship():

    import kit_build as kb
    K = kb.K
    K.life("sea_pen", "kit", "soft", sea_pen, tints=[...])
    kb.ship("sea_pen", ["sea_pen"], pictures)

ship() writes models/kit/<piece>.glb (the full mesh and <piece>_lo in one file), models/kit/<piece>.json
(as GameCommon's json: group, material, size, triangle counts, tints, spheres), tools/blend/kit_<file>.blend
(editable), and, given a folder, pictures of each piece from the front, back, both sides and above.
The game reads them through scripts/kit.gd (Kit), which draws them with the kit's own two shaders
(the alpha of a point's colour is how far it sways), so they add no shader program.

Everything is in Godot's space (metres, +Y up, base at y = 0).
"""

import json
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "scenery", "sea_floor_props", "tools"))
import build_sea_floor_props as K  # noqa: E402

OUT = os.path.join(ROOT, "models", "kit")
BLENDS = os.path.join(HERE, "blend")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def start():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    K.INFO.clear()
    K.FULL.clear()
    K.LOW.clear()


def sheet(kit, rows, col, sway):
    """A two-sided sheet through rows of points (each row the same count): its front faces and,
    on points of their own, its back faces (the kit's shaders cull back faces). col(i, j), sway(i, j)."""
    for side in (0, 1):
        idx = []
        for i, row in enumerate(rows):
            idx.append([kit.v(p, col(i, j), sway(i, j)) for j, p in enumerate(row)])
        for i in range(len(rows) - 1):
            for j in range(len(rows[0]) - 1):
                a, b, c, d = idx[i][j], idx[i][j + 1], idx[i + 1][j + 1], idx[i + 1][j]
                # (as triangles, so the back's split is the front's)
                if side == 0:
                    kit.faces.extend([(a, b, c), (a, c, d)])
                else:
                    kit.faces.extend([(a, c, b), (a, d, c)])


def blade(kit, base, along, across, length, width, segs, col, sway0, sway1, droop=Vector((0, 0, 0)), twist=0.0):
    """A strap blade from `base` along `along`, `width` wide across `across`, bending by `droop`
    (added times the square of the share along it), two-sided, its sway rising from sway0 to sway1."""
    along = along.normalized()
    across = across.normalized()
    rows = []
    for i in range(segs + 1):
        t = i / segs
        w = width * (0.3 + 0.7 * math.sin(math.pi * (0.18 + 0.82 * t))) * (1.0 - 0.35 * t * t) if t < 0.999 else width * 0.18
        mid = base + along * (length * t) + droop * (t * t)
        a = across * math.cos(twist * t) + along.cross(across) * math.sin(twist * t)
        rows.append([mid - a * w * 0.5, mid + a * w * 0.5])
    sheet(kit, rows, lambda i, j: col(i / segs), lambda i, j: sway0 + (sway1 - sway0) * i / segs)


def ship(file, names, pictures=None):
    """Exports the named pieces (built with K.life or K.rock), notes them, saves the .blend."""
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(BLENDS, exist_ok=True)
    full = {o.name: o for o in K.FULL}
    low = {o.name: o for o in K.LOW}
    for obj in [full[n] for n in names] + [low[n + "_lo"] for n in names]:
        print("WINDING %s: %s" % (obj.name, winding(obj)))
    for name in names:
        bpy.ops.object.select_all(action="DESELECT")
        full[name].select_set(True)
        low[name + "_lo"].select_set(True)
        bpy.ops.export_scene.gltf(
            filepath=os.path.join(OUT, name + ".glb"), export_format="GLB", export_yup=True, use_selection=True,
            export_animations=False, export_texcoords=False, export_materials="NONE",
            export_vertex_color="ACTIVE", export_active_vertex_color_when_no_material=True, export_all_vertex_colors=False)
        info = dict(K.INFO[name])
        info["group"] = "kit"
        with open(os.path.join(OUT, name + ".json"), "w") as out:
            json.dump(info, out, indent=1)
        print("BUILT %s material=%s size=%s tris=%d lo=%d spheres=%d" % (
            name, info["material"], info["size"], info["tris"], info["tris_lo"], len(info["spheres"])))
    x = 0.0
    for name in names:
        wide = K.INFO[name]["size"][0]
        x += wide * 0.5 + 0.5
        full[name].location = (x, 0, 0)
        low[name + "_lo"].location = (x, max(6.0, wide * 2.0), 0)
        x += wide * 0.5 + 0.5
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(BLENDS, "kit_%s.blend" % file))
    if pictures:
        look(pictures, [full[n] for n in names] + [low[n + "_lo"] for n in names])


def winding(obj):
    """Each closed part (every edge shared by two faces) must enclose a positive volume; each open
    part is a sheet, which the builders make two-sided (every face has a twin facing the other way
    on the same points: counted)."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    closed = inside = sheets = lone = 0
    twins = {}
    for f in bm.faces:
        key = tuple(sorted(tuple(round(c, 5) for c in v.co) for v in f.verts))
        twins.setdefault(key, []).append(f.normal.copy())
    for part in K.islands(bm):
        if all(len(e.link_faces) == 2 for f in part for e in f.edges):
            closed += 1
            if K.volume_of(part) <= 0.0:
                inside += 1
        else:
            sheets += 1
            for f in part:
                key = tuple(sorted(tuple(round(c, 5) for c in v.co) for v in f.verts))
                ns = twins[key]
                if not any(n.dot(f.normal) < -0.5 for n in ns):
                    lone += 1
    bm.free()
    ok = inside == 0 and lone == 0
    return "%s (%d closed parts, %d inside out; %d sheets, %d faces without a back)" % (
        "ok" if ok else "INSIDE OUT", closed, inside, sheets, lone)


def look(folder, objects):
    """Front, back, both sides and above (and below for the full ones), in the colours painted on
    the points, back faces culled (so a face turned inside out shows as a hole)."""
    os.makedirs(folder, exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "VERTEX"
    scene.display.shading.show_backface_culling = True
    scene.render.resolution_x, scene.render.resolution_y = 300, 300
    camera = bpy.data.objects.new("Look", bpy.data.cameras.new("Look"))
    camera.data.type = "ORTHO"
    scene.collection.objects.link(camera)
    scene.camera = camera
    shots = []
    for obj in objects:
        for other in objects:
            other.hide_render = other is not obj
        m = obj.matrix_world
        pts = [m @ v.co for v in obj.data.vertices]
        lo = Vector([min(p[i] for p in pts) for i in range(3)])
        hi = Vector([max(p[i] for p in pts) for i in range(3)])
        middle = (lo + hi) * 0.5
        size = max((hi - lo).length, 0.01)
        camera.data.ortho_scale = size * 1.05
        camera.data.clip_end = size * 20
        views = (("front", (0, -1, 0.25)), ("back", (0, 1, 0.25)), ("left", (-1, 0, 0.25)), ("right", (1, 0, 0.25)),
                 ("top", (0.01, 0.01, 1)), ("below", (0.01, 0.2, -1)))
        for view, direction in views:
            offset = Vector(direction).normalized() * size * 4
            camera.location = middle + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y").to_euler()
            path = os.path.join(folder, "%s_%s.png" % (obj.name, view))
            scene.render.filepath = path
            bpy.ops.render.render(write_still=True)
            shots.append(path)
    for other in objects:
        other.hide_render = False
    print("PICTURES", folder, len(shots))
