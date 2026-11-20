"""The diver's helmet, modelled and painted from the diving dress's turnaround sheet
(`tools/art_src/concept_brother_diving_turn.jpg`: the helmet drawn apart, from the front and from the side).

    blender -b --factory-startup --python tools/figed/helmet.py -- <out.png> [--blend <file>]

As the boots: the SHAPE is the drawing's. The helmet is a turned shape (a dome on a neck), so its outline at every
height is read off the two views (the smaller of the front view's half-width and the side view's reach to the
back: the side windows show in one and the valves in the other, the bare dome in the smaller of the two), from the
narrowest row of the neck up. The windows are short drums set on it (front, both sides, one above the front), each
capped with its own drawn face. The picture is the two views side by side: what faces forward takes the front view,
the rest the side view. `make()` stands it on the neck ring of the figure's corselet; it rides the chest, not the
head (a diver's helmet is bolted to the corselet: he turns his head inside it).
"""
import math
import os
import sys

import bpy
import bmesh
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figed_fit  # noqa: E402

SHEET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "art_src", "concept_brother_diving_turn.jpg")
BOX = {"front": (2463, 55, 2740, 425), "side": (2490, 940, 2748, 1262)}      # pixels of the sheet (Claude, by eye)
# the windows: which view draws their face, its middle and radius there (pixels), where they sit on the helmet
# (height as a share from neck to crown, degrees round from the front, degrees tipped up), radius as a share of the
# dome's
PORTS = [
    {"face": ("front", 2597, 206, 52), "u": 0.47, "round": 0, "up": 0, "r": 0.36},
    {"face": ("side", 2610, 1066, 41), "u": 0.5, "round": 90, "up": 0, "r": 0.29},
    {"face": ("side", 2610, 1066, 41), "u": 0.5, "round": -90, "up": 0, "r": 0.29},
    {"face": ("side", 2610, 1066, 41), "u": 0.80, "round": 0, "up": 52, "r": 0.2},
]
RADIUS = 0.155                                            # the dome's greatest radius, metres
AROUND, RINGS = 24, 14
SIZE = 1024
_cache = {}


def _view(name):
    if "px" not in _cache:
        _cache["px"] = figed_fit.load_image(SHEET)
    if name not in _cache:
        x0, y0, x1, y1 = BOX[name]
        px = _cache["px"][y0:y1, x0:x1]
        edge = np.concatenate([px[0], px[:, 0], px[:, -1]])
        bg = np.median(edge, axis=0)
        mask = np.abs(px - bg).max(axis=2) > 0.12
        mask = figed_fit.grow(figed_fit.shrink(mask, 2), 2)
        rows, cols = np.nonzero(mask.any(axis=1))[0], np.nonzero(mask.any(axis=0))[0]
        _cache[name] = (px, mask, rows[0], rows[-1], cols[0], cols[-1])
    return _cache[name]


def _sm(a, n=7):
    return np.convolve(np.pad(a, n // 2, mode="edge"), np.ones(n) / n, mode="valid")


def outline():
    """radius (pixels of the front view) at each height u (0 neck .. 1 crown), and how each view lines up."""
    if "out" in _cache:
        return _cache["out"]
    info = {}
    prof = {}
    for name in ("front", "side"):
        px, mask, r0, r1, c0, c1 = _view(name)
        top = mask[r0:r0 + max(3, (r1 - r0) // 8)]
        axis = float(np.mean(np.nonzero(top.any(axis=0))[0]))               # the dome's own middle
        half = []
        for r in range(r0, r1 + 1):
            cols = np.nonzero(mask[r])[0]
            if name == "front":
                half.append((cols[-1] - cols[0]) / 2.0 if len(cols) else 0.0)
            else:
                half.append(axis - cols[0] if len(cols) else 0.0)           # reach to the back (the left)
        half = _sm(np.array(half))
        n = len(half)
        neck = int(n * 0.5) + int(np.argmin(half[int(n * 0.5):int(n * 0.92)]))   # the narrowest row low down
        info[name] = {"axis": axis, "top": r0, "neck": r0 + neck, "rows": neck}
        prof[name] = half[:neck + 1][::-1] / float(neck)                    # from the neck up, in heights
    u = np.linspace(0, 1, 60)
    pf = np.interp(u, np.linspace(0, 1, len(prof["front"])), prof["front"])
    ps = np.interp(u, np.linspace(0, 1, len(prof["side"])), prof["side"])
    r = _sm(np.minimum(pf, ps), 5)
    r[-1] = 0.0
    _cache["out"] = (u, r, info)
    return _cache["out"]


def texture(path):
    tex = np.zeros((SIZE, SIZE, 3), dtype=np.float32)
    for i, name in enumerate(("front", "side")):
        px, mask, r0, r1, c0, c1 = _view(name)
        px, mask = px[r0:r1 + 1, c0:c1 + 1].copy(), figed_fit.shrink(mask[r0:r1 + 1, c0:c1 + 1].copy(), 2)
        for _ in range(60):
            if mask.all():
                break
            tot, cnt = np.zeros_like(px), np.zeros(mask.shape)
            for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                m = np.roll(mask, (dy, dx), axis=(0, 1))
                tot += np.roll(px, (dy, dx), axis=(0, 1)) * m[:, :, None]
                cnt += m
            new = ~mask & (cnt > 0)
            px[new] = tot[new] / cnt[new][:, None]
            mask |= new
        yy = (np.arange(SIZE) * px.shape[0] / float(SIZE)).astype(int)
        xx = (np.arange(SIZE // 2) * px.shape[1] / float(SIZE // 2)).astype(int)
        tex[:, i * SIZE // 2:(i + 1) * SIZE // 2] = px[yy][:, xx][::-1]
    im = bpy.data.images.new("helmet", SIZE, SIZE, alpha=False)
    rgba = np.ones((SIZE, SIZE, 4), dtype=np.float32)
    rgba[:, :, :3] = tex
    im.pixels.foreach_set(rgba.ravel())
    im.filepath_raw = os.path.abspath(path)
    im.file_format = "PNG"
    im.save()
    print("painted", path)


def _uv_of(name, col, row):
    """A pixel of a view's crop -> the picture's (u, v)."""
    px, mask, r0, r1, c0, c1 = _view(name)
    u = min(0.995, max(0.005, (col - c0) / float(c1 - c0)))
    v = min(0.995, max(0.005, (r1 - row) / float(r1 - r0)))
    return ((0.0 if name == "front" else 0.5) + 0.5 * u, v)


def mesh_for(name="helmet"):
    """The helmet in its own space: x across, y back (the front is -y, as the figure), z up from the neck's foot."""
    u, r, info = outline()
    rmax = r.max()
    k = RADIUS / rmax                                     # metres for one height-unit of radius
    height = k                                            # (radius was measured in heights: 1 height = k metres)
    levels = np.sin(np.linspace(0, 1, RINGS) * math.pi / 2) ** 1.15     # closer together toward the crown: a round top
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new("UVMap")
    rings = []
    for lv in levels[:-1]:
        rr = float(np.interp(lv, u, r)) * k
        rings.append([bm.verts.new((rr * math.sin(a), -rr * math.cos(a), lv * height))
                      for a in np.linspace(0, 2 * math.pi, AROUND, endpoint=False)])
    crown = bm.verts.new((0, 0, height))
    for i in range(len(rings) - 1):
        for j in range(AROUND):
            bm.faces.new((rings[i][j], rings[i][(j + 1) % AROUND], rings[i + 1][(j + 1) % AROUND], rings[i + 1][j]))
    for j in range(AROUND):
        bm.faces.new((rings[-1][j], rings[-1][(j + 1) % AROUND], crown))
    bm.faces.new(rings[0][::-1])
    shell = set(bm.faces)
    caps = {}
    for port in PORTS:                                    # the windows: a drum each, capped with its drawn face
        ru = float(np.interp(port["u"], u, r)) * k
        a, e = math.radians(port["round"]), math.radians(port["up"])
        d = np.array([math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)])
        c = np.array([0, 0, port["u"] * height])          # the drum's axis starts on the helmet's own axis
        if port["up"]:                                    # a window tipped up looks out from the dome's middle
            c = np.array([0, 0, 0.5 * height])
        side = np.cross(d, (0, 0, 1.0))
        side /= np.linalg.norm(side)
        upv = np.cross(side, d)
        pr = port["r"] * RADIUS
        reach = RADIUS * 0.97 if port["up"] else ru
        ring0, ring1 = [], []
        for t in np.linspace(0, 2 * math.pi, 12, endpoint=False):
            off = side * math.cos(t) * pr + upv * math.sin(t) * pr
            ring0.append(bm.verts.new(tuple(c + d * reach * 0.7 + off)))
            ring1.append(bm.verts.new(tuple(c + d * (reach + 0.02) + off * 0.92)))
        for j in range(12):
            bm.faces.new((ring0[j], ring0[(j + 1) % 12], ring1[(j + 1) % 12], ring1[j]))
        cap = bm.faces.new(ring1)
        caps[cap] = (port, c + d * (reach + 0.02), side, upv, pr * 0.92)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    if max(bm.faces, key=lambda f: f.calc_center_median().x).normal.x < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.normal_update()
    fi, si = info["front"], info["side"]
    for face in bm.faces:
        face.smooth = face not in caps
        if face in caps:
            port, mid, side, upv, pr = caps[face]
            vname, cx, cy, rpx = port["face"]
            x0, y0 = BOX[vname][:2]
            for loop in face.loops:
                q = np.array(loop.vert.co[:]) - mid
                loop[uv].uv = _uv_of(vname, cx - x0 + q.dot(side) / pr * rpx, cy - y0 - q.dot(upv) / pr * rpx)
            continue
        n = face.normal
        drum = face not in shell
        for loop in face.loops:
            x, y, z = loop.vert.co[:]
            if drum:                                      # the drums' sides: the brass of a window's rim
                vname, cx, cy, rpx = PORTS[0]["face"]
                loop[uv].uv = _uv_of(vname, cx - BOX[vname][0] + rpx * 0.93, cy - BOX[vname][1])
            elif -n.y > 0.55:
                loop[uv].uv = _uv_of("front", fi["axis"] + x / k * fi["rows"], fi["neck"] - z / k * fi["rows"])
            else:
                loop[uv].uv = _uv_of("side", si["axis"] - y / k * si["rows"], si["neck"] - z / k * si["rows"])
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    return mesh, {"height": height, "neck": float(r[0]) * k}


def material(tex_path):
    if not os.path.exists(tex_path):
        texture(tex_path)
    mat = bpy.data.materials.new("helmet")
    mat.use_nodes = True
    node = mat.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = bpy.data.images.load(os.path.abspath(tex_path), check_existing=True)
    mat.node_tree.nodes.active = node
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    mat.node_tree.links.new(node.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


def make(at, ride, crown_z, tex_path, arm=None):
    """The helmet on a figure: its neck's foot at `at` (rest space), carried into the pose by ride(points)."""
    mesh, info = mesh_for()
    lift = max(1.0, (crown_z + 0.035 - at[2]) / info["height"])              # tall enough to clear his crown
    pts = np.array([(at[0] + v.co.x, at[1] + v.co.y, at[2] + v.co.z * lift) for v in mesh.vertices])
    for v, q in zip(mesh.vertices, ride(pts)):
        v.co = q
    obj = bpy.data.objects.new("helmet", mesh)
    obj.vertex_groups.new(name="spine_03").add(list(range(len(mesh.vertices))), 1.0, "REPLACE")
    if arm is not None:
        obj.parent = arm
        obj.modifiers.new("rig", "ARMATURE").object = arm
    mesh.materials.append(material(tex_path))
    bpy.context.scene.collection.objects.link(obj)
    print("helmet: %d triangles, %.3f tall, neck %.3f" % (
        sum(len(p.vertices) - 2 for p in mesh.polygons), info["height"] * lift, info["neck"]))
    return obj, info


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:]
    out = argv[0]
    tex = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures", "helmet_diving.png")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    texture(tex)
    mesh, info = mesh_for()
    obj = bpy.data.objects.new("helmet", mesh)
    bpy.context.scene.collection.objects.link(obj)
    mat = material(tex)
    mesh.materials.append(mat)
    print("helmet: %d triangles, %.3f tall" % (sum(len(p.vertices) - 2 for p in mesh.polygons), info["height"]))
    if "--blend" in argv:
        for im in bpy.data.images:
            if im.filepath:
                im.pack()
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(argv[argv.index("--blend") + 1]))
    import figed_blender as fb  # noqa: E402
    cam = fb._camera()
    centre = np.array([0.0, 0.0, info["height"] / 2])
    q = math.sqrt(0.5)
    strips = []
    for name, d in (("front", (0, 1, 0)), ("quarter", (-q, q, 0)), ("side", (-1, 0, 0)), ("back", (0, -1, 0)),
                    ("top", (-0.3, 0.5, -0.8))):
        s = fb._scene((520, 520))
        s.display.shading.color_type = "TEXTURE"
        s.display.shading.light = "FLAT"
        s.display.shading.show_cavity = False
        fb._aim(cam, centre, d, 0.5)
        cam.data.sensor_fit = "VERTICAL"
        cam.data.ortho_scale = 0.5
        s.render.filepath = os.path.join(os.path.dirname(os.path.abspath(out)), "_helmet_%s.png" % name)
        bpy.ops.render.render(write_still=True)
        shot = bpy.data.images.load(s.render.filepath)
        strips.append(np.array(shot.pixels[:]).reshape(520, 520, 4))
    fb.save_pixels(np.concatenate(strips, axis=1), os.path.abspath(out))
    print("shots", out)
