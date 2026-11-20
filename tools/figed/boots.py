"""Boots for a figure, modelled and painted from a turnaround sheet (the user, 2026-11-20: "His boots look terrible-
generate turnaround concept art for them and make them Properly textured and modeled").

    blender -b --factory-startup --python tools/figed/boots.py -- <spec.json> <rubber|leather> <out.png> [--blend f]

The sheet (`tools/art_src/concept_brother_boots_turn.jpg`: front, three-quarter, outer side, back and sole of each
pair) is read as outlines, so the model's shape IS the drawing's:
- the side view gives, at every height, how far the boot reaches forward and back, and the line of its underside
  (heel, arch, the toe's spring);
- the front view gives its half-width at every height; the sole view the outline of the foot seen from below.
The boot is rings stacked from the ground to the rim (the low ones shaped like the sole, the high ones oval), closed
underneath along the underside's line, turned in at the rim, with pull tabs. It is scaled only as far as the figure's
own foot needs. Its picture is the sheet's views laid side by side (side, front, back, sole), each face painted from
the view it faces, so nothing is invented. The lower part rides the foot bone, the shaft the calf.
"""
import math
import os
import sys

import bpy
import bmesh
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figed  # noqa: E402
import figed_fit  # noqa: E402

SHEET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "art_src", "concept_brother_boots_turn.jpg")
# where each view is in the sheet (pixels of the 2752 x 1536 picture: x0, y0, x1, y1; Claude, by eye), the row of
# the rim (the pull tabs stand above it), the boot's height from the ground to the rim (metres) and its tabs
KINDS = {
    "rubber": {"side": (1190, 40, 1790, 770), "front": (90, 40, 345, 770), "back": (1830, 40, 2130, 770),
               "sole": (2290, 40, 2610, 770), "rim": 135, "height": 0.33, "tabs": "back"},
    "leather": {"side": (1200, 830, 1800, 1536), "front": (90, 830, 345, 1536), "back": (1820, 830, 2130, 1536),
                "sole": (2290, 830, 2610, 1536), "rim": 908, "height": 0.28, "tabs": "sides"},
    # the diver's lead boots, read off the diving dress's own sheet (its side, front and back figures); that sheet
    # has no view from below, so the sole is the rubber boot's
    "diving": {"sheet": "concept_brother_diving_turn.jpg", "side": (1556, 1240, 1830, 1500), "front": (340, 1240, 545, 1500),
               "back": (2070, 1240, 2262, 1500), "sole": "rubber", "rim": 1262, "height": 0.25, "tabs": "none"},
}
AROUND = 20                                               # points round each ring
LEVELS = [0.0, 0.03, 0.065, 0.11, 0.16, 0.21, 0.27, 0.34, 0.42, 0.52, 0.64, 0.76, 0.88, 1.0]   # rings, 0 ground .. 1 rim
RECTS = {"side": (0.0, 0.40), "front": (0.40, 0.60), "back": (0.60, 0.80), "sole": (0.80, 0.97)}  # the picture's columns
SIZE = 1024
_sheet = {}


def _smooth(a, n=5):
    k = np.ones(n) / n
    return np.convolve(np.pad(a, n // 2, mode="edge"), k, mode="valid")


def _view(kind, name):
    """One view of the sheet: (pixels, boot mask, bbox rows r0 r1, bbox cols c0 c1, the rim's row) in its crop."""
    if isinstance(KINDS[kind][name], str):                # this view borrowed from another kind
        return _view(KINDS[kind][name], name)
    sheet = os.path.join(os.path.dirname(SHEET), KINDS[kind].get("sheet", os.path.basename(SHEET)))
    if sheet not in _sheet:
        _sheet[sheet] = figed_fit.load_image(sheet)
    x0, y0, x1, y1 = KINDS[kind][name]
    px = _sheet[sheet][y0:y1, x0:x1]
    edge = np.concatenate([px[0], px[-1], px[:, 0], px[:, -1]])
    bg = np.median(edge, axis=0)
    mask = np.abs(px - bg).max(axis=2) > 0.13
    mask = figed_fit.grow(figed_fit.shrink(mask, 2), 2)     # the sheet's thin guide lines go
    rows, cols = np.nonzero(mask.any(axis=1))[0], np.nonzero(mask.any(axis=0))[0]
    return px, mask, rows[0], rows[-1], cols[0], cols[-1], KINDS[kind]["rim"] - y0


def outline(kind):
    """The boot's measures off the sheet, as functions of height u (0 ground .. 1 rim), all in metres."""
    H = KINDS[kind]["height"]
    px, mask, r0, r1, c0, c1, rim = _view(kind, "side")
    s = H / float(r1 - rim)                               # metres a pixel (side view)
    us, back, front = [], [], []
    for r in range(rim, r1 + 1):
        cols = np.nonzero(mask[r])[0]
        if len(cols):
            us.append((r1 - r) / float(r1 - rim))
            back.append(cols[0])
            front.append(cols[-1])
    us, back, front = np.array(us[::-1]), _smooth(np.array(back[::-1], float)), _smooth(np.array(front[::-1], float))
    low = us < 0.3
    cmin, cmax = back[low].min(), front[low].max()
    under = []                                            # the underside's height along the foot
    for c in range(int(cmin), int(cmax) + 1):
        rr = np.nonzero(mask[:, c])[0]
        under.append((r1 - rr[-1]) * s if len(rr) else 0.0)
    under = np.clip(_smooth(np.array(under), 7), 0, 0.03)
    fpx, fmask, fr0, fr1, fc0, fc1, frim = _view(kind, "front")
    sf = H / float(fr1 - frim)
    fu, fw = [], []
    for r in range(frim, fr1 + 1):
        cols = np.nonzero(fmask[r])[0]
        if len(cols):
            fu.append((fr1 - r) / float(fr1 - frim))
            fw.append((cols[-1] - cols[0]) / 2.0 * sf)
    fu, fw = np.array(fu[::-1]), _smooth(np.array(fw[::-1]))
    spx, smask, sr0, sr1, sc0, sc1, _ = _view(kind, "sole")
    st, sw = [], []
    for r in range(sr0, sr1 + 1):                         # the toe is at the top of the sole view
        cols = np.nonzero(smask[r])[0]
        if len(cols):
            st.append((sr1 - r) / float(sr1 - sr0))
            sw.append(float(cols[-1] - cols[0]))
    st, sw = np.array(st[::-1]), _smooth(np.array(sw[::-1]))
    sw = sw / sw.max()
    sw[0] = sw[-1] = 0.0
    return {
        "H": H, "s": s, "sf": sf, "cmin": cmin, "length": (cmax - cmin) * s,
        "back": lambda u: (np.interp(u, us, back) - cmin) * s,
        "front": lambda u: (np.interp(u, us, front) - cmin) * s,
        "wide": lambda u: np.interp(u, fu, fw),
        "under": lambda t: np.interp(t, np.linspace(0, 1, len(under)), under),
        "sole": lambda t: np.interp(t, st, sw),
    }


def shape(kind, long=0.0, wide=0.0):
    """The boot in its own space (x across, y from the heel's back toward the toe, z up from the ground): points,
    faces (lists of point numbers), and each face's view. Stretched so it is at least `long` and `wide` (metres)."""
    o = outline(kind)
    H = o["H"]
    ky = max(1.0, long / o["length"])
    kx = max(1.0, wide / (2 * o["wide"](0.12)))
    tl = np.linspace(0, 1, 101)
    pts, faces = [], []
    ang = [2 * math.pi * k / AROUND for k in range(AROUND)]
    for u in LEVELS:
        b, f, w = o["back"](u), o["front"](u), o["wide"](u)
        mix = float(np.clip((0.40 - u) / 0.22, 0, 1))                      # sole-shaped low down, oval higher up
        prof = mix * o["sole"](tl) + (1 - mix) * 2 * np.sqrt(tl * (1 - tl))
        prof = prof / prof.max()
        for a in ang:
            t = (1 + math.cos(a)) / 2
            y = b + (f - b) * t
            x = math.copysign(w * float(np.interp(t, tl, prof)), math.sin(a)) if abs(math.sin(a)) > 1e-6 else 0.0
            zb = float(o["under"](y / o["length"]))
            z = max(u * H, zb + (0.0 if u == 0 else 0.004))
            pts.append((x * kx, y * ky, z))
    n = AROUND
    for i in range(len(LEVELS) - 1):
        for k in range(n):
            a, b = i * n + k, i * n + (k + 1) % n
            faces.append([a, b, b + n, a + n])
    for k in range(1, n // 2 - 1):                        # underneath: strips across between the two sides
        faces.append([k, n - k, n - k - 1, k + 1])
    faces.append([0, n - 1, 1])
    faces.append([n // 2 - 1, n // 2 + 1, n // 2])
    top = (len(LEVELS) - 1) * n                           # the rim turned in, and the dark inside
    c = np.array(pts[top:top + n]).mean(axis=0)
    for scale, drop in ((0.88, 0.0), (0.84, 0.05)):
        base = len(pts)
        for k in range(n):
            q = np.array(pts[top + k])
            pts.append(tuple(c + (q - c) * scale - np.array([0, 0, drop])))
        prev = base - n if drop else top
        for k in range(n):
            faces.append([prev + k, prev + (k + 1) % n, base + (k + 1) % n, base + k])
    base = len(pts) - n
    faces.append([base + k for k in range(n)][::-1])
    tabs = []                                             # pull tabs: thin boxes standing above the rim
    rim_pts = np.array(pts[top:top + n])
    spots = {"back": [rim_pts[n // 2]], "sides": [rim_pts[n // 4], rim_pts[3 * n // 4]]}.get(KINDS[kind]["tabs"], [])
    for q in spots:
        d = q - c
        d[2] = 0
        d /= np.linalg.norm(d)
        side = np.array([-d[1], d[0], 0.0])
        b0 = len(pts)
        for dz in (-0.022, 0.026):
            for sa, sb in ((-1, 0), (1, 0), (1, 1), (-1, 1)):
                pts.append(tuple(q + side * sa * 0.011 + d * (sb * 0.006 - 0.001) + np.array([0, 0, dz])))
        for k in range(4):
            faces.append([b0 + k, b0 + (k + 1) % 4, b0 + 4 + (k + 1) % 4, b0 + 4 + k])
        faces.append([b0 + 7, b0 + 6, b0 + 5, b0 + 4])
        tabs.extend(range(b0, b0 + 8))
    return np.array(pts), faces, {"o": o, "kx": kx, "ky": ky, "inside": base - n, "tabs": set(tabs)}


def texture(kind, path):
    """The sheet's four views side by side as the boot's picture; where a view is paper, the boot's colour beside
    it is carried out, so an edge never shows paper."""
    tex = np.zeros((SIZE, SIZE, 3), dtype=np.float32)
    for name, (u0, u1) in RECTS.items():
        px, mask, r0, r1, c0, c1, _rim = _view(kind, name)
        px, mask = px[r0:r1 + 1, c0:c1 + 1].copy(), mask[r0:r1 + 1, c0:c1 + 1].copy()
        mask = figed_fit.shrink(mask, 2)
        for _ in range(60):
            if mask.all():
                break
            tot = np.zeros_like(px)
            cnt = np.zeros(mask.shape)
            for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                m = np.roll(mask, (dy, dx), axis=(0, 1))
                tot += np.roll(px, (dy, dx), axis=(0, 1)) * m[:, :, None]
                cnt += m
            new = ~mask & (cnt > 0)
            px[new] = tot[new] / cnt[new][:, None]
            mask |= new
        w = int(round((u1 - u0) * SIZE))
        yy = (np.arange(SIZE) * px.shape[0] / float(SIZE)).astype(int)
        xx = (np.arange(w) * px.shape[1] / float(w)).astype(int)
        tex[:, int(u0 * SIZE):int(u0 * SIZE) + w] = px[yy][:, xx][::-1]
    dark = tex[:, :int(0.4 * SIZE)].reshape(-1, 3)
    tex[:, int(0.97 * SIZE):] = np.percentile(dark, 5, axis=0) * 0.6
    im = bpy.data.images.new("boots_" + kind, SIZE, SIZE, alpha=False)
    rgba = np.ones((SIZE, SIZE, 4), dtype=np.float32)
    rgba[:, :, :3] = tex
    im.pixels.foreach_set(rgba.ravel())
    im.filepath_raw = os.path.abspath(path)
    im.file_format = "PNG"
    im.save()
    print("painted", path)


def _uv(kind, info, q, normal, face_pts):
    """Where a point of a face is in the picture: by the view the face is turned to."""
    o = info["o"]
    H = o["H"]
    x, y, z = q[0] / info["kx"], q[1] / info["ky"], q[2]

    def place(name, col, row_up, scale):
        px, mask, r0, r1, c0, c1, rim = _view(kind, name)
        u0, u1 = RECTS[name]
        u = (col - c0) / float(c1 - c0)
        v = row_up / float(r1 - r0)
        return (u0 + (u1 - u0) * min(0.995, max(0.005, u)), min(0.997, max(0.003, v)))

    if normal[2] < -0.6:                                  # underneath: the sole view (its toe at the top)
        px, mask, r0, r1, c0, c1, _ = _view(kind, "sole")
        half = max(1e-6, o["wide"](0.03)) * 1.02
        return place("sole", (c0 + c1) / 2.0 + x / half * (c1 - c0) / 2.0, y / o["length"] * (r1 - r0), 0)
    h = math.hypot(normal[0], normal[1])
    zz = z
    if normal[2] > 0.55 and z < 0.5 * H:
        # the top of the toe and instep: no view looks down on it, so it takes the side view's colours just under
        # the outline's upper edge at that place along the foot (the lit top of the vamp, as the side view paints it)
        zz = max(0.0, z - 0.014)
        name = "side"
    elif abs(normal[0]) >= 0.42 * h:
        name = "side"
    else:
        name = "front" if normal[1] > 0 else "back"
    px, mask, r0, r1, c0, c1, rim = _view(kind, name)
    s = H / float(r1 - rim)
    if name == "side":
        col = o["cmin"] + y / o["s"]
    else:
        col = (c0 + c1) / 2.0 + x / s
    return place(name, col, zz / s, s)


def mesh_for(kind, name, long=0.0, wide=0.0):
    """One boot as a Blender mesh in its own space, with UVs."""
    pts, faces, info = shape(kind, long, wide)
    bm = bmesh.new()
    vs = [bm.verts.new(tuple(p)) for p in pts]
    for f in faces:
        try:
            bm.faces.new([vs[i] for i in f])
        except ValueError:
            pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.normal_update()
    probe = max(bm.faces, key=lambda f: f.calc_center_median().x)          # (outward check: the face furthest +x)
    if probe.normal.x < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.normal_update()
    uv = bm.loops.layers.uv.new("UVMap")
    inside = info["inside"]
    for face in bm.faces:
        face.smooth = True
        idx = [v.index for v in face.verts]
        if min(idx) >= inside and not (set(idx) & info["tabs"]):
            for loop in face.loops:
                loop[uv].uv = (0.985, 0.5)                # the dark inside
            continue
        nrm = np.array(face.normal[:])
        if set(idx) & info["tabs"]:
            nrm = np.array([1.0, 0.0, 0.0]) if KINDS[kind]["tabs"] == "back" else np.array([0.0, 1.0, 0.0])
        for loop in face.loops:
            loop[uv].uv = _uv(kind, info, np.array(loop.vert.co[:]), nrm, None)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    return mesh, info


def make_pair(fig, P, Pp, H, kind, tex_path, weights_of):
    """Both boots on the figure, posed. weights_of(names) -> each body point's weight on those bones."""
    if not os.path.exists(tex_path):
        texture(kind, tex_path)
    mat = bpy.data.materials.new("boots_" + kind)
    mat.use_nodes = True
    node = mat.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = bpy.data.images.load(os.path.abspath(tex_path), check_existing=True)
    mat.node_tree.nodes.active = node
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    mat.node_tree.links.new(node.outputs["Color"], bsdf.inputs["Base Color"])
    footw, calfw = weights_of(("foot", "ball")), weights_of(("calf",))
    objs = []
    for side in ("l", "r"):
        mine = P[:, 0] * H["foot_" + side][0] > 0
        foot = P[mine & (footw > 0.5)]
        heel, toe = foot[:, 1].max(), foot[:, 1].min()    # the figure faces -y
        cx = (foot[:, 0].min() + foot[:, 0].max()) / 2
        z0 = foot[:, 2].min()
        long = (heel - toe) + 0.035
        wide = (foot[:, 0].max() - foot[:, 0].min()) + 0.02
        mesh, info = mesh_for(kind, "boot_" + side, long, wide)
        ankle = H["foot_" + side][2] - z0
        to_foot = _rigid(P[mine & (footw > 0.6)], Pp[mine & (footw > 0.6)])
        to_calf = _rigid(P[mine & (calfw > 0.8)], Pp[mine & (calfw > 0.8)])
        obj = bpy.data.objects.new("boot_" + side, mesh)
        gf, gc = obj.vertex_groups.new(name="foot_" + side), obj.vertex_groups.new(name="calf_" + side)
        flip = -1.0 if side == "r" else 1.0
        for v in mesh.vertices:
            q = np.array([cx + v.co.x * flip, heel + 0.014 - v.co.y, z0 + v.co.z])
            k = float(np.clip((v.co.z - (ankle - 0.02)) / 0.06, 0, 1))      # 0 with the foot, 1 with the calf
            v.co = to_foot(q[None])[0] * (1 - k) + to_calf(q[None])[0] * k
            gf.add([v.index], 1 - k, "REPLACE")
            gc.add([v.index], k, "REPLACE")
        if side == "r":
            mesh.flip_normals()
        mesh.materials.append(mat)
        bpy.context.scene.collection.objects.link(obj)
        objs.append(obj)
        print("boot %s: %d triangles, foot %.3f long, boot %.3f x %.3f" % (
            side, sum(len(p.vertices) - 2 for p in mesh.polygons), heel - toe, info["o"]["length"] * info["ky"],
            2 * info["o"]["wide"](0.12) * info["kx"]))
    return objs


def _rigid(A, B):
    ca, cb = A.mean(axis=0), B.mean(axis=0)
    U, _S, Vt = np.linalg.svd((A - ca).T.dot(B - cb))
    d = np.sign(np.linalg.det(Vt.T.dot(U.T)))
    R = Vt.T.dot(np.diag([1.0, 1.0, d])).dot(U.T)
    return lambda q: (q - ca).dot(R.T) + cb


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:]
    kind, out = argv[1], argv[2]
    stem = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures", "boots_" + kind)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    texture(kind, stem + ".png")
    mesh, info = mesh_for(kind, "boot_" + kind)
    obj = bpy.data.objects.new("boot_" + kind, mesh)
    bpy.context.scene.collection.objects.link(obj)
    mat = bpy.data.materials.new("boots_" + kind)
    mat.use_nodes = True
    node = mat.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = bpy.data.images.load(stem + ".png", check_existing=True)
    mat.node_tree.nodes.active = node
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    mat.node_tree.links.new(node.outputs["Color"], bsdf.inputs["Base Color"])
    mesh.materials.append(mat)
    print("boot: %d triangles, %.3f long" % (sum(len(p.vertices) - 2 for p in mesh.polygons), info["o"]["length"]))
    if "--blend" in argv:
        node.image.pack()
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(argv[argv.index("--blend") + 1]))
    import figed_blender as fb  # noqa: E402
    cam = fb._camera()
    H = KINDS[kind]["height"]
    L = info["o"]["length"]
    centre = np.array([0.0, L / 2, H / 2])
    q = math.sqrt(0.5)
    strips = []
    for name, d, up in (("front", (0, -1, 0), None), ("quarter", (-q, -q, 0), None), ("side", (-1, 0, 0), None),
                        ("back", (0, 1, 0), None), ("under", (0, 0, 1), (0, 1, 0)), ("top", (-0.4, -0.5, -0.76), None)):
        s = fb._scene((520, 640))
        s.display.shading.color_type = "TEXTURE"
        s.display.shading.light = "FLAT"
        s.display.shading.show_cavity = False
        fb._aim(cam, centre, d, 0.46, up)
        cam.data.sensor_fit = "VERTICAL"
        cam.data.ortho_scale = 0.46
        s.render.filepath = os.path.join(os.path.dirname(os.path.abspath(out)), "_boot_%s.png" % name)
        bpy.ops.render.render(write_still=True)
        shot = bpy.data.images.load(s.render.filepath)
        strips.append(np.array(shot.pixels[:]).reshape(640, 520, 4))
    fb.save_pixels(np.concatenate(strips, axis=1), os.path.abspath(out))
    print("shots", out)
