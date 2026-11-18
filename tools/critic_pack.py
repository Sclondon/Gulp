"""The picture pack for an independent critic (the user, 2026-11-18: "after a build you should show the model in tpose
and face and hand close ups to an agent that has no context, then ask it for critiques compared to the concept art so
you can get good prompts to fix the issues").

  blender --background --factory-startup --python tools/critic_pack.py -- <figure.glb> <outdir> [hide_name ...]

Writes <outdir>/body.png (whole figure from four sides, painted over plain grey), head.png (front, three-quarter,
side, back, from below), hands.png (the left hand: back, palm, thumb side, fingertips), feet.png (front, side, top).
Objects whose names contain a hide_name (e.g. cap) are left out. Pictures only: it changes nothing.
"""
import bpy, sys, math, os
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
src, out = args[0], args[1]
hide = [h.lower() for h in args[2:]]
os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=src)
sc = bpy.context.scene
for o in list(sc.objects):
    if o.type == "MESH" and (o.name.startswith("Icosphere") or any(h in o.name.lower() for h in hide) or "under" in o.name.lower()):
        bpy.data.objects.remove(o)
meshes = [o for o in sc.objects if o.type == "MESH"]
dg = bpy.context.evaluated_depsgraph_get()
pts = []
for o in meshes:
    ev = o.evaluated_get(dg)
    me = ev.to_mesh()
    pts += [ev.matrix_world @ v.co for v in me.vertices]
    ev.to_mesh_clear()
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
tall = hi.z - lo.z
mid = (lo + hi) / 2
# the head: everything above the shoulders' level, near the middle
top = [p for p in pts if p.z > hi.z - tall * 0.125 and abs(p.x - mid.x) < tall * 0.1]
hlo = Vector((min(p.x for p in top), min(p.y for p in top), min(p.z for p in top)))
hhi = Vector((max(p.x for p in top), max(p.y for p in top), max(p.z for p in top)))
head = (hlo + hhi) / 2
# the left hand: the points furthest out on +x (the figure's left when it faces -y)
far = max(p.x for p in pts)
hand_pts = [p for p in pts if p.x > far - tall * 0.11]
hand = sum(hand_pts, Vector()) / len(hand_pts)
foot_pts = [p for p in pts if p.z < lo.z + tall * 0.07 and p.x > mid.x]
foot = sum(foot_pts, Vector()) / len(foot_pts)

sc.render.engine = "BLENDER_WORKBENCH"
# plain colour: the default AgX transform darkens and browns the paint (a critic then calls the skin muddy)
sc.view_settings.view_transform = "Standard"
sh = sc.display.shading
sh.light = "STUDIO"
sh.show_cavity = True
sh.cavity_type = "BOTH"
sh.show_object_outline = False
sc.display.render_aa = "16"
sc.world = bpy.data.worlds.new("w")
sc.world.color = (0.80, 0.82, 0.85)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
sc.collection.objects.link(cam)
sc.camera = cam
cam.data.type = "ORTHO"
tmp = os.path.join(out, "_t")
os.makedirs(tmp, exist_ok=True)


def shot(name, focus, size, ang, up, w, h):
    files = []
    for mode in ("TEXTURE", "SINGLE"):
        sh.color_type = mode
        sh.single_color = (0.72, 0.72, 0.74)
        d = Vector((math.sin(ang) * math.cos(up), -math.cos(ang) * math.cos(up), math.sin(up)))
        cam.location = focus + d * 10
        cam.rotation_euler = (focus - cam.location).to_track_quat("-Z", "Y").to_euler()
        cam.data.ortho_scale = size
        sc.render.resolution_x = w
        sc.render.resolution_y = h
        path = os.path.join(tmp, "%s_%s.png" % (name, mode))
        sc.render.filepath = path
        bpy.ops.render.render(write_still=True)
        files.append(path)
    return files


def sheet(name, tiles, w, h):
    """tiles: (tag, focus, size, angle, up). One row painted over one row grey."""
    rows = [[], []]
    for tag, focus, size, ang, up in tiles:
        a, b = shot(name + "_" + tag, focus, size, ang, up, w, h)
        rows[0].append(a)
        rows[1].append(b)
    imgs = [[bpy.data.images.load(p) for p in row] for row in rows]
    W, H = w * len(tiles), h * 2
    buf = [0.0] * (W * H * 4)
    import array
    full = array.array("f", buf)
    for r, row in enumerate(imgs):
        for c, im in enumerate(row):
            px = array.array("f", [0.0] * (w * h * 4))
            im.pixels.foreach_get(px)
            for y in range(h):
                s = y * w * 4
                dy = (1 - r) * h + y
                t = (dy * W + c * w) * 4
                full[t:t + w * 4] = px[s:s + w * 4]
    res = bpy.data.images.new(name, W, H)
    res.pixels.foreach_set(full)
    res.filepath_raw = os.path.join(out, name + ".png")
    res.file_format = "PNG"
    res.save()


Q = 0.7
P = math.pi
sheet("body", [("front", mid, tall * 1.06, 0, 0), ("q", mid, tall * 1.06, Q, 0), ("side", mid, tall * 1.06, P / 2, 0),
               ("back", mid, tall * 1.06, P, 0), ("qb", mid, tall * 1.06, P - Q, 0)], 520, 860)
hs = max(hhi.z - hlo.z, hhi.x - hlo.x) * 1.35
sheet("head", [("front", head, hs, 0, 0), ("q", head, hs, Q, 0.1), ("side", head, hs, P / 2, 0), ("back", head, hs, P, 0),
               ("below", head, hs, 0.3, -0.9), ("above", head, hs, 0.3, 0.9)], 600, 600)
ds = tall * 0.2
sheet("hands", [("front", hand, ds, 0, 0), ("back", hand, ds, P, 0), ("out", hand, ds, P / 2, 0), ("in", hand, ds, -P / 2, 0),
                ("above", hand, ds, 0.2, 1.2), ("below", hand, ds, 0.2, -1.2)], 520, 520)
fs = tall * 0.24
sheet("feet", [("front", foot, fs, 0, 0.2), ("side", foot, fs, P / 2, 0.1), ("inner", foot, fs, -P / 2, 0.1), ("top", foot, fs, 0.01, 1.3)], 520, 520)
print("CRITIC_PACK", out, "height", round(tall, 3))
