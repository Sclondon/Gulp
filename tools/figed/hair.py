"""Hair for a figure: pieces of their own that sit on the bare head (the base model stays bald and shaven).

    blender -b --factory-startup --python tools/figed/hair.py -- <spec.json> <out.png> [--wear hair,moustache]

- `hair`: a mop of curls. The scalp's own faces inside a hairline rule (written from the eyes, the crown and the
  angle round the head, so it follows the sliders), pushed out to the mop's thickness, divided once, then raised
  into curl clumps (round lumps with creases between, seeded evenly over it) and closed underneath round the rim.
  Its picture is painted from the same clumps: strands spiralling round each one, dark in the creases, light on top.
- `moustache`: the skin between the nose and the upper lip, out past the corners of the mouth, pushed out and
  painted with strands fanning down and out from under the nose.
Each has UVs of its own (the hair's wrap round the head, the moustache's lie flat from the front) and a picture
`<stem>_hair.png` / `<stem>_moustache.png`. The numbers at the top are the first pass's, Claude's picks.
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
import garments as G  # noqa: E402

SIZE = 1024
# the hairline: degrees round the head from the front -> height over the eye line (shares of eye-to-crown where
# under 1 in size and marked "s", else metres)
LINE_A = [0, 35, 55, 72, 95, 125, 180]
LINE_S = [0.60, 0.56, 0.30, 0.0, 0.0, 0.0, 0.0]            # share of eye-to-crown
LINE_M = [0.0, 0.0, 0.0, -0.035, -0.015, -0.075, -0.085]   # plus metres
THICK = (0.012, 0.036)                                     # the mop's thickness at the hairline, and further in
CLUMP = 0.042                                              # distance between curl clumps
RISE = 0.016                                               # how far a clump stands up
SAG_A = [0, 50, 80, 120, 180]                              # degrees round from the front -> how far the mop's edge
SAG_M = [0.06, 0.042, 0.026, 0.014, 0.02]                 # hangs down over the hairline there (metres)
HAIR = ((0.20, 0.105, 0.06), (0.34, 0.185, 0.10), (0.52, 0.30, 0.16))   # crease, strand, light (amber)
TACHE = ((0.40, 0.17, 0.07), (0.60, 0.29, 0.13), (0.74, 0.42, 0.20))    # ginger: redder than his hair


INFO = {}


def _biggest(mesh):
    """Only the largest joined piece of a mesh is kept (stray flecks cut off by a fold of skin go)."""
    bm = bmesh.new()
    bm.from_mesh(mesh)
    left, best = set(bm.verts), []
    while left:
        grp, todo = set(), [next(iter(left))]
        while todo:
            v = todo.pop()
            if v in grp:
                continue
            grp.add(v)
            todo.extend(e.other_vert(v) for e in v.link_edges)
        left -= grp
        if len(grp) > len(best):
            best = grp
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v not in best], context="VERTS")
    bm.to_mesh(mesh)
    bm.free()


def landmarks(fig, P):
    base = fig.base
    z = P[:, 2]
    headw = G._w(base, ("head",))
    eye = (P[base.indices("helper-l-eye")].mean(axis=0) + P[base.indices("helper-r-eye")].mean(axis=0)) / 2
    crown = float(z[headw > 0.8].max())
    idx, d = base.target("mouth-scale-horiz-incr")
    size = np.linalg.norm(d, axis=1)
    corner = P[int(idx[np.argmax(np.where(P[idx, 0] > 0, size, -1))])]
    idx, d = base.target("mouth-philtrum-volume-incr")
    mid = idx[np.abs(P[idx, 0]) < 0.006]
    L = {"eye": eye, "crown": crown, "corner": corner, "nose_base": float(P[mid, 2].max()),
         "lip_top": float(P[mid, 2].min())}
    print("landmarks: eye z %.3f crown %.3f mouth corner x %.3f z %.3f nose base %.3f lip top %.3f"
          % (eye[2], crown, corner[0], corner[2], L["nose_base"], L["lip_top"]))
    return L


def rules(fig, P, H):
    base = fig.base
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    L = landmarks(fig, P)
    headw = G._w(base, ("head",))
    ears = np.zeros(len(P), dtype=bool)
    for _side, masks in fig._ear_masks().items():
        ears[np.asarray(masks[0], dtype=int)] = True
    eye = L["eye"]
    span = L["crown"] - eye[2]
    yc = H["head"][1]
    a = np.degrees(np.abs(np.arctan2(x, -(y - yc))))
    line = eye[2] + np.interp(a, LINE_A, LINE_S) * span + np.interp(a, LINE_A, LINE_M)
    f = z - line
    thick = THICK[0] + THICK[1] * np.clip(f / 0.04, 0, 1) ** 0.6
    out = {"hair": (f, (headw > 0.5) & ~ears, thick)}
    xe = abs(L["corner"][0]) + 0.02
    zc = L["corner"][2]
    t = np.clip(np.abs(x) / xe, 0, 1)
    top = L["nose_base"] - 0.002
    top = top - (top - (zc + 0.006)) * t ** 2.2
    bot = L["lip_top"] - 0.006
    bot = bot + ((zc - 0.009) - bot) * t ** 1.5
    fm = np.minimum(np.minimum(top - z, z - bot), (xe - np.abs(x)) * 0.5)
    out["moustache"] = (fm, (headw > 0.5) & (y < eye[1] + 0.03), 0.004 + 0.008 * np.clip(fm / 0.006, 0, 1))
    INFO.update(top=top, bot=bot, yc=yc)
    return out, L


def _spread(V, gap, seed=7):
    """Points of V at least gap apart, spread evenly."""
    rng = np.random.RandomState(seed)
    kept = []
    for i in rng.permutation(len(V)):
        if not kept or np.linalg.norm(V[kept] - V[i], axis=1).min() > gap:
            kept.append(i)
    return V[kept]


def _two_nearest(Q, S):
    d1, d2, i1 = np.zeros(len(Q)), np.zeros(len(Q)), np.zeros(len(Q), dtype=int)
    for a in range(0, len(Q), 40000):
        d = np.linalg.norm(Q[a:a + 40000, None, :] - S[None, :, :], axis=2)
        order = np.argsort(d, axis=1)[:, :2]
        rows = np.arange(len(order))
        i1[a:a + 40000] = order[:, 0]
        d1[a:a + 40000], d2[a:a + 40000] = d[rows, order[:, 0]], d[rows, order[:, 1]]
    return d1, d2, i1


def curls(mesh, skin):
    """The cut scalp made a mop: divided, raised into clumps, closed underneath. Returns the clumps' middles."""
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=2, use_grid_fill=True, smooth=0.6)
    bm.normal_update()
    bm.verts.ensure_lookup_table()
    V = np.array([v.co[:] for v in bm.verts])
    N = np.array([v.normal[:] for v in bm.verts])
    S = _spread(V, CLUMP)
    d1, d2, i1 = _two_nearest(V, S)
    tall = 0.7 + 0.6 * np.random.RandomState(3).rand(len(S))
    lump = np.clip((d2 - d1) / 0.028, 0, 1) ** 0.6
    V2 = V + N * (RISE * lump * tall[i1] - 0.004)[:, None]
    # the edge of the mop hangs over the hairline in locks, each clump by its own amount: onto the forehead most
    lf = bm.verts.layers.float.get("f")
    fv = np.array([v[lf] for v in bm.verts])
    c = V.mean(axis=0)
    ang = np.degrees(np.abs(np.arctan2(V[:, 0] - c[0], -(V[:, 1] - c[1]))))
    hang = 0.2 + 0.8 * np.random.RandomState(9).rand(len(S))
    sag = np.interp(ang, SAG_A, SAG_M) * np.clip(1 - fv / 0.04, 0, 1) ** 1.5 * hang[i1] * (0.3 + 0.7 * lump)   # each lock's middle hangs lowest
    V2[:, 2] -= sag
    # ... and stays outside the head as it hangs (the forehead comes forward under the hairline): each hanging
    # point is kept its lock's thickness out from the skin nearest it
    for i in np.nonzero(sag > 0.002)[0]:
        q = skin[np.argmin(np.linalg.norm(skin - V2[i], axis=1))]
        r = q - c
        r[2] *= 0.3
        r /= np.linalg.norm(r)
        out = (V2[i] - q).dot(r)
        need = 0.009 + 0.008 * lump[i]
        if out < need:
            V2[i] += r * (need - out)
    for v, q in zip(bm.verts, V2):
        v.co = q
    for v, q in zip(bm.verts, V2):
        v.co = q
    for _ in range(2):                                    # the edge's corners rounded (along the edge only)
        new = {}
        for v in bm.verts:
            if v.is_boundary:
                nb = [e.other_vert(v).co for e in v.link_edges if e.is_boundary]
                if len(nb) == 2:
                    new[v] = v.co * 0.5 + (nb[0] + nb[1]) * 0.25
        for v, q in new.items():
            v.co = q
    rim = [e for e in bm.edges if e.is_boundary]
    made = bmesh.ops.extrude_edge_only(bm, edges=rim)["geom"]
    for v in [g for g in made if isinstance(g, bmesh.types.BMVert)]:
        q = np.array(v.co[:])
        v.co = skin[np.argmin(np.linalg.norm(skin - q, axis=1))]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for face in bm.faces:
        face.smooth = True
    bm.to_mesh(mesh)
    bm.free()
    return S


def _raster(mesh, uv_of):
    """Each texel's place on the mesh: (SIZE, SIZE, 3) and which texels are covered. uv_of(points) -> (n, 2);
    writes the UVs too (a face across the wrap-round seam is laid over the edge and wraps)."""
    layer = mesh.uv_layers.get("hair") or mesh.uv_layers.new(name="hair")
    V = np.array([v.co[:] for v in mesh.vertices])
    U = uv_of(V)
    for poly in mesh.polygons:
        us = U[list(poly.vertices)].copy()
        if us[:, 0].max() - us[:, 0].min() > 0.5:
            us[us[:, 0] < 0.5, 0] += 1.0
        for li, uv in zip(poly.loop_indices, us):
            layer.data[li].uv = tuple(uv)
    mesh.uv_layers.active = layer
    layer.active_render = True
    pos = np.zeros((SIZE, SIZE, 3))
    hit = np.zeros((SIZE, SIZE), dtype=bool)
    mesh.calc_loop_triangles()
    for tri in mesh.loop_triangles:
        uv = np.array([layer.data[li].uv[:] for li in tri.loops]) * SIZE
        pp = V[list(tri.vertices)]
        x0, x1 = int(math.floor(uv[:, 0].min())) - 1, int(math.ceil(uv[:, 0].max())) + 1
        y0, y1 = max(0, int(math.floor(uv[:, 1].min())) - 1), min(SIZE - 1, int(math.ceil(uv[:, 1].max())) + 1)
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
        px, py = gx + 0.5, gy + 0.5
        den = (uv[1, 1] - uv[2, 1]) * (uv[0, 0] - uv[2, 0]) + (uv[2, 0] - uv[1, 0]) * (uv[0, 1] - uv[2, 1])
        if abs(den) < 1e-9:
            continue
        b0 = ((uv[1, 1] - uv[2, 1]) * (px - uv[2, 0]) + (uv[2, 0] - uv[1, 0]) * (py - uv[2, 1])) / den
        b1 = ((uv[2, 1] - uv[0, 1]) * (px - uv[2, 0]) + (uv[0, 0] - uv[2, 0]) * (py - uv[2, 1])) / den
        b2 = 1 - b0 - b1
        ins = (b0 > -0.15) & (b1 > -0.15) & (b2 > -0.15)
        yy, xx = gy[ins], gx[ins] % SIZE
        pos[yy, xx] = b0[ins][:, None] * pp[0] + b1[ins][:, None] * pp[1] + b2[ins][:, None] * pp[2]
        hit[yy, xx] = True
    return pos, hit


def _save(tex, path, name):
    im = bpy.data.images.new(name, SIZE, SIZE, alpha=False)
    rgba = np.ones((SIZE, SIZE, 4), dtype=np.float32)
    rgba[:, :, :3] = np.clip(tex, 0, 1)
    im.pixels.foreach_set(rgba.ravel())
    im.filepath_raw = os.path.abspath(path)
    im.file_format = "PNG"
    im.save()
    print("painted", path)


def paint_hair(mesh, S, path):
    c = np.array([v.co[:] for v in mesh.vertices]).mean(axis=0)

    def uv_of(V):
        d = V - c
        r = np.linalg.norm(d, axis=1)
        return np.stack([np.arctan2(d[:, 0], -d[:, 1]) / (2 * math.pi) + 0.5,
                         np.arcsin(np.clip(d[:, 2] / r, -1, 1)) / math.pi + 0.5], axis=1)

    pos, hit = _raster(mesh, uv_of)
    Q = pos[hit]
    d1, d2, i1 = _two_nearest(Q, S)
    n = S - c
    n /= np.linalg.norm(n, axis=1, keepdims=True)
    t1 = np.cross(n, np.array([0.0, 0.0, 1.0]))
    t1 /= np.maximum(np.linalg.norm(t1, axis=1, keepdims=True), 1e-6)
    t2 = np.cross(n, t1)
    rel = Q - S[i1]
    th = np.arctan2((rel * t2[i1]).sum(axis=1), (rel * t1[i1]).sum(axis=1))
    rng = np.random.RandomState(11)
    turn = np.where(rng.rand(len(S)) > 0.5, 1.0, -1.0)[i1]
    ph = rng.rand(len(S))[i1] * 6.28
    # each clump is a lock of waves: strands run one way across it (its own way, mostly downhill) and wave
    way = rng.rand(len(S))[i1] * 2.4 - 1.2 + math.pi / 2
    u = np.cos(way) * (rel * t1[i1]).sum(axis=1) + np.sin(way) * (rel * t2[i1]).sum(axis=1)
    w = -np.sin(way) * (rel * t1[i1]).sum(axis=1) + np.cos(way) * (rel * t2[i1]).sum(axis=1)
    bend = 2.4 * np.sin(u * 95 * turn + ph)
    lock = 0.5 + 0.5 * np.sin(w * 260 + bend)                             # broad waves
    fine = 0.5 + 0.5 * np.sin(w * 900 + bend * 3.4 + ph)                  # strands within them
    _ = th
    crease = np.clip((d2 - d1) / 0.014, 0, 1)
    top = np.clip(rel[:, 2] / 0.02 * 0.5 + 0.5, 0, 1) * np.clip(1 - d1 / 0.03, 0, 1)   # the upper side of each clump
    k = np.clip(0.15 + 0.55 * lock + 0.2 * fine, 0, 1) * (0.35 + 0.65 * crease)
    dark, mid, light = (np.array(v) for v in HAIR)
    col = dark + (mid - dark) * k[:, None]
    col = col + (light - mid) * (top * lock * 0.9)[:, None]
    tex = np.tile(np.array(HAIR[0]), (SIZE, SIZE, 1))
    tex[hit] = col
    _save(tex, path, "hair")


def paint_moustache(mesh, L, path):
    V = np.array([v.co[:] for v in mesh.vertices])
    lo, hi = V.min(axis=0), V.max(axis=0)
    pad = 0.004

    def uv_of(W):
        return np.stack([(W[:, 0] - lo[0] + pad) / (hi[0] - lo[0] + 2 * pad),
                         (W[:, 2] - lo[2] + pad) / (hi[2] - lo[2] + 2 * pad)], axis=1)

    pos, hit = _raster(mesh, uv_of)
    Q = pos[hit]
    mid_x = (lo[0] + hi[0]) / 2
    # strands combed out from the middle along each half, drooping to the ends
    rng = np.random.RandomState(5)
    ax = np.abs(Q[:, 0] - mid_x)
    half = (hi[0] - lo[0]) / 2
    droop = (hi[2] - lo[2]) * 0.75 * (ax / half) ** 2
    w = Q[:, 2] + droop + 0.35 * ax
    wob = np.sin(ax * 500 + w * 300) * 0.6
    strand = 0.5 + 0.5 * np.sin(w * 2600 + wob)
    broad = 0.5 + 0.5 * np.sin(w * 800 + 1.3 + wob * 0.5)
    k = np.clip(0.2 + 0.5 * strand + 0.3 * broad, 0, 1)
    low = np.clip((Q[:, 2] - lo[2]) / (hi[2] - lo[2]), 0, 1)             # lighter on the upper side, darker below
    dark, midc, light = (np.array(v) for v in TACHE)
    col = dark + (midc - dark) * k[:, None]
    col = col + (light - midc) * (k * low ** 1.5 * 0.8)[:, None]
    tex = np.tile(np.array(TACHE[0]), (SIZE, SIZE, 1))
    tex[hit] = col
    _save(tex, path, "moustache")
    _ = rng


def make(fig, wear, stem):
    base = fig.base
    P, H, T = fig.to_blender()
    Pp = figed_fit.pose_points(fig, P, H, figed_fit.full_pose(fig.pose, base.bones, H, T), T)[0]
    R, L = rules(fig, P, H)
    G.SMOOTH.update(hair=2, moustache=1)
    skin = Pp[G._w(base, ("head",)) > 0.5]
    objs = {}
    for name in wear:
        f, may, off = R[name]
        mesh = G.cut(fig, P, Pp, f, may, off, name)
        for v, d in zip(mesh.vertices, mesh.attributes["posed"].data):
            v.co = d.vector
        path = "%s_%s.png" % (stem, name)
        if name == "hair":
            _biggest(mesh)
            S = curls(mesh, skin)
            paint_hair(mesh, S, path)
        else:
            _biggest(mesh)
            paint_moustache(mesh, L, path)
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.scene.collection.objects.link(obj)
        mesh.materials.append(G.material(name, path))
        objs[name] = obj
        print("%-10s %5d triangles" % (name, sum(len(p.vertices) - 2 for p in mesh.polygons)))
    return objs


if __name__ == "__main__":
    import figed_blender as fb  # noqa: E402

    argv = sys.argv[sys.argv.index("--") + 1:]
    spec_path, out = argv[:2]
    wear = argv[argv.index("--wear") + 1].split(",") if "--wear" in argv else ["hair", "moustache"]
    fig = figed.Figure(figed.Base(), figed.load_spec(spec_path))
    stem = os.path.splitext(spec_path)[0]
    fb.reset()
    objs, _arm = fb.build(fig, rig=False, posed=True)
    objs["body"].data.materials.append(G.material("skin", stem + "_skin.png"))
    if "eyes" in objs and os.path.exists(stem + "_eyes.png"):
        objs["eyes"].data.materials.append(G.material("eyes", stem + "_eyes.png"))
    make(fig, wear, stem)
    boxes = fb.view_boxes(fig)
    cam = fb._camera()
    strips = []
    for view in ("face", "face_quarter_r", "face_side_r", "face_quarter", "face_back"):
        centre, direction, seen, aspect = boxes[view][:4]
        seen = seen * 1.12                                # room for the hair
        w = int(900 * aspect) // 2 * 2
        s = fb._scene((w, 900))
        s.display.shading.color_type = "TEXTURE"
        s.display.shading.light = "FLAT" if "--lit" not in argv else "STUDIO"
        s.display.shading.show_cavity = False
        fb._aim(cam, centre, direction, seen)
        cam.data.sensor_fit = "VERTICAL"
        cam.data.ortho_scale = seen
        s.render.filepath = os.path.join(os.path.dirname(os.path.abspath(out)), "_hair_%s.png" % view)
        bpy.ops.render.render(write_still=True)
        shot = bpy.data.images.load(s.render.filepath)
        strips.append(np.array(shot.pixels[:]).reshape(900, w, 4))
    fb.save_pixels(np.concatenate(strips, axis=1), os.path.abspath(out))
    print("shots", out)
