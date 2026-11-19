"""Faces that move: a jaw bone, a mouth inside, and shared blend shapes for Gulp's figures.

Run (a post-process on a copy; the figure's own glb is never written):
    blender --background --factory-startup --python tools/face_rig.py -- <in.glb> <out.glb> [--figure captain|brother|boy]
    [--report <file.json>] [--keep-blend <file.blend>]

DECISION (Claude's pick; research and sources in tools/FACE_RIG.md)
    One `jaw` bone (child of `head`, pivot at the jaw hinge in front of and below the ear) for the open mouth, plus 17
    morph targets with the same names on every figure:
        smile frown mouth_o mouth_wide lips_press cheeks_puff brows_up brows_down brows_sad
        eyes_closed eyes_wide squint sneer   eyes_closed_L eyes_closed_R smile_L smile_R   (L/R = the figure's own)
    and a mouth inside (lips cut open, an inner lip roll, a dark bag, upper teeth on `head`, lower teeth and tongue on
    `jaw`, one palette picture). Why: the hybrid of a jaw joint for the rotation and blend shapes for what bones do badly
    (lips, brows, lids) is the usual set-up for game faces; Godot's Compatibility renderer runs a blend shape only while
    its weight is not zero, but over EVERY vertex of the mesh that holds it, so the head is split off into a mesh of its
    own (`<figure>_head`) on the same skeleton: the shapes cost head vertices only. Lids are moved by rotating about the
    fitted eyeball centre, so they slide over the ball (a sphere-guarded blink). Alternatives (bones only, ARKit's 52,
    visemes, texture-swap faces, a second surface of the body mesh) and why not: tools/FACE_RIG.md.

HOW TO INTEGRATE into a build script (build_brother.py, build_boy.py, build_captain.py, build_npc.py)
    Just before the glTF export, with the armature, the body mesh (head joined into it, the face's faces on the material
    whose name ends in `_face`) and the eyeball mesh (or None) as Blender objects:

        import importlib.util, os
        spec = importlib.util.spec_from_file_location("face_rig", os.path.join(os.path.dirname(__file__), "face_rig.py"))
        face_rig = importlib.util.module_from_spec(spec); spec.loader.exec_module(face_rig)
        rig = face_rig.rig_face(armature_obj, body_obj, eyes_obj, figure="brother")   # or "boy", "captain", "npc"
        # rig["head"] is the new <figure>_head mesh, rig["mouth"] the teeth/tongue/bag mesh, rig["report"] the costs
        ... export as before, with export_morph=True, export_morph_normal=True, export_try_sparse_sk=False, then:
        face_rig.zero_still_normals(out_glb)    # no shading change where a shape moves nothing (the neck seam)

    Or step by step: split_head, find_face_landmarks, cut_mouth, add_lip_roll, add_jaw, weight_jaw, add_mouth,
    add_shapes, (captain) cut_slits + add_eyeballs, finish_normals. Hair, beards and moustaches made later are bound to
    the face with bind_to_face(hair_obj, head_obj): it copies jaw/head weights and every shape's movement from the
    nearest point of the head, so a beard follows the jaw and a moustache follows `smile` and `mouth_o`.

Godot: MeshInstance3D.set_blend_shape_value(mesh.find_blend_shape_by_name("smile"), 0..1); the jaw opens by rotating
the `jaw` bone about the world's sideways axis expressed in the bone's rest frame (see tests/face_view.gd, `bone_turn`).
"""
import bpy, bmesh, sys, os, math, json, struct
import numpy as np
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

SHAPES = ["smile", "frown", "mouth_o", "mouth_wide", "lips_press", "cheeks_puff", "brows_up", "brows_down",
          "brows_sad", "eyes_closed", "eyes_wide", "squint", "sneer",
          "eyes_closed_L", "eyes_closed_R", "smile_L", "smile_R"]

# per-figure tuning: multipliers on the shared amounts (Claude's picks, change freely)
FIGURES = {
    "brother": dict(smile=1.4, brows=1.3, lids=1.0, slits=False),
    "boy": dict(smile=1.45, brows=1.4, lids=1.0, slits=False),
    "captain": dict(smile=1.25, brows=1.1, lids=1.0, slits=True),
    "npc": dict(smile=1.4, brows=1.3, lids=1.0, slits=False),
}

# the mouth palette: cells of an 8x1 strip (u at a cell's middle)
PALETTE = [("bag", (0.10, 0.025, 0.03)), ("teeth", (0.90, 0.86, 0.76)), ("gums", (0.70, 0.30, 0.31)),
           ("tongue", (0.66, 0.26, 0.31)), ("lip_in", (0.52, 0.20, 0.21)), ("sclera", (0.93, 0.91, 0.86)),
           ("lid_in", (0.45, 0.22, 0.20)), ("spare", (0.5, 0.5, 0.5))]


def cell_uv(name, v=0.5):
    i = [p[0] for p in PALETTE].index(name)
    return ((i + 0.5) / len(PALETTE), v)


def log(*a):
    sys.stdout.write("FACE " + " ".join(str(x) for x in a) + "\n")
    sys.stdout.flush()


def smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x, dtype=float) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def bump(P, c, r):
    """Gaussian bump on |x| (mirrored): P (N,3), c (3,), r (3,)."""
    Q = P.copy(); Q[:, 0] = np.abs(Q[:, 0])
    d = (Q - np.asarray(c)) / np.asarray(r)
    return np.exp(-np.sum(d * d, axis=1))


# ---------------------------------------------------------------------------------------------------- reading
def mesh_arrays(obj):
    me = obj.data
    P = np.array([obj.matrix_world @ v.co for v in me.vertices])
    return P


def vgroup_weights(obj, name):
    g = obj.vertex_groups.get(name)
    out = np.zeros(len(obj.data.vertices))
    if g is None:
        return out
    for v in obj.data.vertices:
        for e in v.groups:
            if e.group == g.index:
                out[v.index] = e.weight
    return out


def corner_normal_table(obj):
    """{(rounded vertex pos, rounded face centre): normal} and {rounded vertex pos: mean normal}."""
    me = obj.data
    cn = me.corner_normals
    by_face, by_vert = {}, {}
    for p in me.polygons:
        c = tuple(np.round(np.array(p.center), 5))
        for li in p.loop_indices:
            vi = me.loops[li].vertex_index
            k = tuple(np.round(np.array(me.vertices[vi].co), 5))
            n = Vector(cn[li].vector)
            by_face[(k, c)] = n
            by_vert.setdefault(k, Vector()).__iadd__(n)
    for k in by_vert:
        by_vert[k] = by_vert[k].normalized()
    return by_face, by_vert


def apply_normals(obj, by_face=None, by_vert=None, only_verts=None, avg_pairs=None):
    """Set custom normals: from the tables where a corner is found (by face, then by vertex), otherwise the mesh's own
    smooth normal. only_verts: a set of rounded positions to take from the tables (others smooth)."""
    me = obj.data
    # plain smooth normals first
    if me.has_custom_normals:
        with bpy.context.temp_override(object=obj, active_object=obj, selected_objects=[obj]):
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
    me.shade_smooth()
    auto = [Vector(c.vector) for c in me.corner_normals]
    out = list(auto)
    pos = [tuple(np.round(np.array(v.co), 5)) for v in me.vertices]
    # average across the cut chains so a closed cut does not show (pairs of rounded positions share a normal)
    vmean = {}
    for p in me.polygons:
        for li in p.loop_indices:
            k = pos[me.loops[li].vertex_index]
            vmean.setdefault(k, Vector()).__iadd__(auto[li])
    for p in me.polygons:
        c = tuple(np.round(np.array(p.center), 5))
        for li in p.loop_indices:
            k = pos[me.loops[li].vertex_index]
            if only_verts is not None and k in only_verts:
                if by_face is not None and (k, c) in by_face:
                    out[li] = by_face[(k, c)]
                elif by_vert is not None and k in by_vert:
                    out[li] = by_vert[k]
            elif avg_pairs is not None and k in avg_pairs:
                out[li] = vmean[k].normalized()
    me.normals_split_custom_set([tuple(n) for n in out])


# ---------------------------------------------------------------------------------------------------- the split
def split_head(body, armature, figure_name):
    """Move the face material's faces (the head) out of the body into <figure>_head. Normals on both sides of the neck
    seam are kept as they were in the joined mesh. Returns (head_obj, seam positions set)."""
    me = body.data
    face_mi = [i for i, m in enumerate(me.materials) if m and m.name.endswith("_face")]
    if not face_mi:
        # fall back to the head bone's faces
        w = vgroup_weights(body, "head")
        sel = [p.index for p in me.polygons if all(w[v] > 0.5 for v in p.vertices)]
    else:
        sel = [p.index for p in me.polygons if p.material_index in face_mi]
    by_face, by_vert = corner_normal_table(body)
    selset = set(sel)
    head = body.copy(); head.data = me.copy(); head.name = figure_name + "_head"; head.data.name = figure_name + "_head"
    for c in body.users_collection:
        c.objects.link(head)
    for obj, keep in ((head, True), (body, False)):
        bm = bmesh.new(); bm.from_mesh(obj.data)
        bm.faces.ensure_lookup_table()
        kill = [f for f in bm.faces if (f.index in selset) != keep]
        bmesh.ops.delete(bm, geom=kill, context="FACES")
        loose = [v for v in bm.verts if not v.link_faces]
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
        bm.to_mesh(obj.data); bm.free()
    # seam = vertices of the head that are also in the body
    bpos = {tuple(np.round(np.array(v.co), 5)) for v in body.data.vertices}
    seam = {tuple(np.round(np.array(v.co), 5)) for v in head.data.vertices} & bpos
    allb = {tuple(np.round(np.array(v.co), 5)) for v in body.data.vertices}
    apply_normals(body, by_face, by_vert, only_verts=allb)
    apply_normals(head, by_face, by_vert, only_verts=seam)
    # drop unused materials from each (keeps the glTF primitives honest)
    log("split: head %d verts %d faces, body %d verts, seam %d" % (len(head.data.vertices), len(head.data.polygons),
                                                                   len(body.data.vertices), len(seam)))
    return head, seam, (by_face, by_vert)


# ---------------------------------------------------------------------------------------------------- landmarks
class Face:
    pass


def _tex_sampler(obj, bvh):
    """(x, z) -> darkness (1 - luminance) of the face picture where a ray from the front meets the head, or None."""
    me = obj.data
    img = None
    for m in me.materials:
        if m and m.name.endswith("_face") and m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == "TEX_IMAGE" and n.image is not None:
                    img = n.image
                    break
    if img is None or not me.uv_layers:
        return None
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(h, w, 4)
    lum = 0.3 * px[:, :, 0] + 0.59 * px[:, :, 1] + 0.11 * px[:, :, 2]
    uv = me.uv_layers.active.data
    P = mesh_arrays(obj)
    y0 = P[:, 1].min() - 0.2

    def f(x, z):
        hit = bvh.ray_cast(Vector((x, y0, z)), Vector((0, 1, 0)), 1.0)
        if hit[0] is None:
            return np.nan
        poly = me.polygons[hit[2]]
        li = list(poly.loop_indices)
        vs = [P[me.loops[l].vertex_index] for l in li[:3]]
        a, b, c = vs
        pnt = np.array(hit[0])
        v0, v1, v2 = b - a, c - a, pnt - a
        d00, d01, d11, d20, d21 = v0 @ v0, v0 @ v1, v1 @ v1, v2 @ v0, v2 @ v1
        den = d00 * d11 - d01 * d01
        if abs(den) < 1e-18:
            return np.nan
        bv = (d11 * d20 - d01 * d21) / den; cw = (d00 * d21 - d01 * d20) / den; aw = 1 - bv - cw
        t = aw * np.array(uv[li[0]].uv) + bv * np.array(uv[li[1]].uv) + cw * np.array(uv[li[2]].uv)
        i = int(np.clip(t[1] % 1.0 * h, 0, h - 1)); j = int(np.clip(t[0] % 1.0 * w, 0, w - 1))
        return 1.0 - float(lum[i, j])
    return f


def _bvh_multi(objs):
    V, polys = [], []
    for o in objs:
        base = len(V)
        V += [Vector(p) for p in mesh_arrays(o)]
        polys += [[base + i for i in p.vertices] for p in o.data.polygons]
    return BVHTree.FromPolygons(V, polys)


def _bvh(obj):
    P = mesh_arrays(obj)
    polys = [list(p.vertices) for p in obj.data.polygons]
    return BVHTree.FromPolygons([Vector(p) for p in P], polys)


def _front(bvh, x, z, y0):
    hit = bvh.ray_cast(Vector((x, y0, z)), Vector((0, 1, 0)), 1.0)
    if hit[0] is None:
        return None, None
    return hit[0].y, hit[1]


def _profile(bvh, x, z0, z1, y0, step=0.0005):
    zs = np.arange(z0, z1, -step)
    ys = np.full(len(zs), np.nan)
    for i, z in enumerate(zs):
        y, n = _front(bvh, x, z, y0)
        if y is not None:
            ys[i] = y
    return zs, ys


def _smooth(a, k=3):
    if len(a) < k:
        return a
    b = a.copy()
    good = ~np.isnan(a)
    for i in range(len(a)):
        lo, hi = max(0, i - k // 2), min(len(a), i + k // 2 + 1)
        seg = a[lo:hi][good[lo:hi]]
        if len(seg):
            b[i] = seg.mean()
    return b


def _valleys(zs, ys, win):
    """Local maxima of y (deepest points) with prominence against the shallowest point within `win` metres above and
    below. Returns [(index, prominence)]."""
    out = []
    n = len(ys)
    step = abs(zs[1] - zs[0]) if n > 1 else 0.0005
    w = max(2, int(win / step))
    for i in range(1, n - 1):
        if np.isnan(ys[i]) or np.isnan(ys[i - 1]) or np.isnan(ys[i + 1]):
            continue
        if ys[i] >= ys[i - 1] and ys[i] > ys[i + 1]:
            up = ys[max(0, i - w):i]; dn = ys[i + 1:i + 1 + w]
            up = up[~np.isnan(up)]; dn = dn[~np.isnan(dn)]
            if len(up) == 0 or len(dn) == 0:
                continue
            out.append((i, ys[i] - max(up.min(), dn.min())))
    return out


def _sphere_fit(P):
    A = np.c_[2 * P, np.ones(len(P))]
    b = np.sum(P * P, axis=1)
    s = np.linalg.lstsq(A, b, rcond=None)[0]
    c = s[:3]
    return c, math.sqrt(max(1e-12, s[3] + c @ c))


def _boundary_loops(obj):
    bm = bmesh.new(); bm.from_mesh(obj.data)
    adj = {}
    for e in bm.edges:
        if e.is_boundary:
            a, b = e.verts[0].index, e.verts[1].index
            adj.setdefault(a, []).append(b); adj.setdefault(b, []).append(a)
    bm.free()
    loops, seen = [], set()
    for s in adj:
        if s in seen:
            continue
        comp, st = [], [s]
        while st:
            x = st.pop()
            if x in seen:
                continue
            seen.add(x); comp.append(x); st += adj[x]
        loops.append(comp)
    return loops


def find_face_landmarks(head, eyes=None, seam=None, body=None):
    """Measure the face: eyes (centre, radius, lid margins), nose tip, nasion, the mouth's meeting line and corners,
    the jaw hinge, chin, brows, cheeks. Everything is found from geometry, so it survives re-builds."""
    F = Face()
    P = mesh_arrays(head)
    F.P = P
    bvh = _bvh(head)
    F.bvh = bvh
    F.bvh_all = _bvh_multi([head, body]) if body is not None else bvh
    y0 = P[:, 1].min() - 0.2
    F.y0 = y0
    zmax, zmin = P[:, 2].max(), P[:, 2].min()
    H = zmax - zmin
    u0 = H / 6.0
    # nose tip: the most forward point near the middle
    mid = np.abs(P[:, 0]) < 0.25 * u0
    i = np.argmin(np.where(mid, P[:, 1], 9))
    F.nose_tip = P[i].copy()
    # nasion: deepest point on the middle line between the nose tip and 1.6 u0 above it
    zs, ys = _profile(bvh, 0.0, F.nose_tip[2] + 1.6 * u0, F.nose_tip[2] + 0.2 * u0, y0)
    ys = _smooth(ys, 5)
    j = np.nanargmax(ys)
    F.nasion = np.array([0.0, ys[j], zs[j]])
    # eyes
    F.slits = False
    if eyes is not None:
        E = mesh_arrays(eyes)
        F.eyes = []
        for sgn in (1, -1):
            Q = E[E[:, 0] * sgn > 0]
            c, r = _sphere_fit(Q)
            F.eyes.append(dict(c=c, r=r, side=sgn, r_out=float(np.linalg.norm(Q - c, axis=1).max())))   # r_out: the cornea's bulge
        F.u = float(np.mean([abs(e["c"][0]) for e in F.eyes]))
        # lid margins: the head's boundary loops nearest each eye
        loops = _boundary_loops(head)
        for e in F.eyes:
            best = min(loops, key=lambda L: np.linalg.norm(P[L].mean(axis=0) - e["c"]))
            e["margin"] = best
    else:
        F.eyes = None
        F.u = u0
    u = F.u
    # the mouth's meeting line on the middle: the most prominent valley below the nose
    # Two signals: the surface's depth (a modelled crease), or the face picture's darkness (a painted mouth line,
    # when the lips are modelled flat, as the boy's are). Larger = more of a valley.
    tex = _tex_sampler(head, bvh)

    def geo_sig(x, z0, z1, step=0.0005):
        zz, yy = _profile(bvh, x, z0, z1, y0, step)
        return zz, _smooth(yy, 3)

    def tex_sig(x, z0, z1, step=0.0005):
        zz = np.arange(z0, z1, -step)
        vals = np.array([tex(x, z) for z in zz])
        return zz, _smooth(vals, 3)
    sig, thr = geo_sig, 0.001
    zs, ys = sig(0.0, F.nose_tip[2] - 0.25 * u, F.nose_tip[2] - 1.6 * u)
    vs = [v for v in _valleys(zs, ys, 0.3 * u) if zs[v[0]] < F.nose_tip[2] - 0.45 * u]
    if (not vs or max(v[1] for v in vs) < thr) and tex is not None:
        sig, thr = tex_sig, 0.04
        zs, ys = sig(0.0, F.nose_tip[2] - 0.25 * u, F.nose_tip[2] - 1.6 * u)
        vs = [v for v in _valleys(zs, ys, 0.3 * u) if zs[v[0]] < F.nose_tip[2] - 0.45 * u]
        log("mouth: no modelled crease; using the painted mouth line")
    if not vs:
        raise RuntimeError("no mouth line found")
    i, prom0 = max(vs, key=lambda v: v[1])
    yfront, _n = _front(bvh, 0.0, zs[i], y0)
    F.mouth_mid = np.array([0.0, yfront, zs[i]])
    # follow it outward to the corners
    xs, zc, prom = [0.0], [zs[i]], [prom0]
    x = 0.0
    while x < 1.4 * u:
        x += 0.0015
        z0 = zc[-1]
        zz, yy = sig(x, z0 + 0.25 * u, z0 - 0.25 * u, 0.0004)
        vv = _valleys(zz, yy, 0.2 * u)
        vv = [v for v in vv if abs(zz[v[0]] - z0) < 0.09 * u]
        if not vv:
            break
        k, p = max(vv, key=lambda v: v[1] - 3 * abs(zz[v[0]] - z0) * (1 if sig is geo_sig else 30))
        if p < max(thr * 0.4, 0.22 * prom0):
            break
        xs.append(x); zc.append(zz[k]); prom.append(p)
    cx = float(np.clip(xs[-1], 0.68 * u, 1.05 * u))
    if xs[-1] < 0.68 * u:
        log("mouth corners: found only %.4f, using %.4f" % (xs[-1], cx))
    xs = np.array(xs); zc = _smooth(np.array(zc), 5)
    F.mouth_x, F.mouth_z = xs, zc
    F.corner_x = cx
    F.mouth_curve = lambda x: float(np.interp(min(abs(x), cx), xs, zc, right=zc[-1]))
    yc_c, nc = _front(bvh, cx, F.mouth_curve(cx), y0)
    F.corner = np.array([cx, yc_c if yc_c is not None else F.mouth_mid[1] + 0.3 * u, F.mouth_curve(cx)])
    F.mouth_prom = prom0
    # chin: below the mouth, the most forward point, then where the front ray falls back (the underside)
    # (on the head and body together: the face's material often ends just under the chin, the neck is the body's)
    ball = F.bvh_all
    zs, ys = _profile(ball, 0.0, F.mouth_mid[2] - 0.35 * u, F.mouth_mid[2] - 2.6 * u, y0)
    good = ~np.isnan(ys)
    jump = np.where(np.diff(ys) > 0.12 * u)[0]
    if len(jump):
        k = jump[0]
    else:   # a chin that rolls into a heavy neck with no step: where the profile has fallen back 0.3 u from the chin
        j0 = int(np.nanargmin(ys))
        back = np.where((np.arange(len(ys)) > j0) & (ys > ys[j0] + 0.3 * u))[0]
        k = int(back[0]) if len(back) else int(np.argmin(np.abs(zs - (F.mouth_mid[2] - 1.1 * u))))
        log("chin: no step under the chin; menton where the profile falls back (z %.4f)" % zs[k])
    F.chin_bottom = np.array([0.0, ys[k], zs[k]])          # the menton: the chin's lowest front point
    F.throat = np.array([0.0, ys[min(k + 1, len(ys) - 1)], zs[min(k + 1, len(ys) - 1)]])
    seg = ys[:k + 1]
    j = int(np.nanargmin(seg))
    F.chin = np.array([0.0, ys[j], zs[j]])
    # captain-style closed slits: find them now that u is a first guess
    if F.eyes is None:
        find_slits(F)
    else:
        F.u = u
    u = F.u
    # ears: the head's widest points between the nose's base and the brow (a heavy jowl or neck can be wider lower down)
    ez = float(np.mean([e["c"][2] for e in F.eyes]))
    side = (P[:, 0] > 0) & (P[:, 2] > F.nose_tip[2] - 0.3 * u) & (P[:, 2] < ez + 0.4 * u)
    xm = P[side, 0].max()
    ear = P[side & (P[:, 0] > xm - 0.25 * u)]
    F.ear = ear.mean(axis=0)
    # jaw hinge (anatomy: the joint is just in front of the ear canal; the jaw turns about a point a little below it)
    F.hinge = np.array([0.0, F.ear[1] - 0.28 * u, F.ear[2] - 0.22 * u])
    # the jaw's lower border (side view): from the menton back to the angle below the ear
    F.gonion = np.array([0.0, F.ear[1] - 0.15 * u, F.chin_bottom[2] + 0.4 * (F.hinge[2] - F.chin_bottom[2])])
    for e in F.eyes:
        ec = e["c"]
        # brow: the most forward point above the eye in its column
        zz, yy = _profile(bvh, abs(ec[0]) * e["side"], ec[2] + 1.4 * u, ec[2] + 0.25 * u, y0)
        yy = _smooth(yy, 5)
        j = int(np.nanargmin(yy)) if not np.all(np.isnan(yy)) else 0
        e["brow"] = np.array([ec[0], yy[j], zz[j]])
    F.brow_z = float(np.mean([e["brow"][2] for e in F.eyes]))
    F.eye_z = float(np.mean([e["c"][2] for e in F.eyes]))
    F.eye_x = float(np.mean([abs(e["c"][0]) for e in F.eyes]))
    F.eye_r = float(np.mean([e["r"] for e in F.eyes]))
    # cheek apples: below the eyes, out a little
    F.cheek = np.array([F.eye_x * 1.05, 0.0, F.eye_z - 0.8 * u])
    yy, n = _front(bvh, F.cheek[0], F.cheek[2], y0)
    F.cheek[1] = yy if yy is not None else F.mouth_mid[1] + 0.4 * u
    # nose wings
    F.ala = np.array([0.42 * u, 0.0, F.nose_tip[2] - 0.12 * u])
    yy, n = _front(bvh, F.ala[0], F.ala[2], y0)
    F.ala[1] = yy if yy is not None else F.nose_tip[1] + 0.3 * u
    # seam distance (for masking everything that moves)
    if seam:
        kd = KDTree(len(seam))
        for i, s in enumerate(seam):
            kd.insert(Vector(s), i)
        kd.balance()
        F.seam_kd = kd
    else:
        F.seam_kd = None
    log("landmarks u=%.4f eye_x=%.4f eye_z=%.4f eye_r=%.4f nose=%s mouth=%s corner_x=%.4f prom=%.4f chin=%s "
        "chin_bottom=%s ear=%s hinge=%s brow_z=%.4f" % (
            F.u, F.eye_x, F.eye_z, F.eye_r, np.round(F.nose_tip, 4), np.round(F.mouth_mid, 4), F.corner_x, F.mouth_prom,
            np.round(F.chin, 4), np.round(F.chin_bottom, 4), np.round(F.ear, 4), np.round(F.hinge, 4), F.brow_z))
    return F


def find_slits(F):
    """Closed eyes (the captain's squint): the eye is the deepest crease beside the nasion. Per column, the most
    prominent valley within reach of the nasion's height; the eye spans the columns where it is clear."""
    bvh, y0, u0 = F.bvh, F.y0, F.u
    zn = F.nasion[2]
    cols = []
    for x in np.arange(0.25 * u0, 1.9 * u0, 0.0015):
        zz, yy = _profile(bvh, x, F.nose_tip[2] + 1.5 * u0, F.nose_tip[2] + 0.15 * u0, y0, 0.0004)
        yy = _smooth(yy, 3)
        vv = _valleys(zz, yy, 0.18 * u0)
        if not vv:
            cols.append((x, None, None, 0.0)); continue
        k, p = max(vv, key=lambda v: v[1])
        cols.append((x, zz[k], yy[k], p))
    pm = max(c[3] for c in cols)
    good = [c for c in cols if c[3] > 0.35 * pm]
    # the longest run of neighbouring good columns
    runs, cur = [], []
    for c in cols:
        if c[3] > 0.35 * pm:
            cur.append(c)
        else:
            if cur:
                runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    run = max(runs, key=len)
    x0, x1 = run[0][0], run[-1][0]
    xs = np.array([c[0] for c in run]); zs = _smooth(np.array([c[1] for c in run]), 5); ys = np.array([c[2] for c in run])
    xm = 0.5 * (x0 + x1)
    half = 0.5 * (x1 - x0)
    r = float(np.clip(0.62 * half, 0.009, 0.016))
    zm = float(np.interp(xm, xs, zs)); ym = float(np.interp(xm, xs, ys))
    F.u = xm
    F.eyes = []
    for sgn in (1, -1):
        c = np.array([sgn * xm, ym + r + 0.0012, zm + 0.08 * r])
        F.eyes.append(dict(c=c, r=r, side=sgn, slit=(xs, zs), x0=x0, x1=x1, margin=None))
    F.slits = True
    log("slits: x %.4f..%.4f z %.4f depth %.4f r %.4f prom %.4f" % (x0, x1, zm, ym, r, pm))


# ---------------------------------------------------------------------------------------------------- cutting
def cut_open(obj, curve, x0, x1, zband, ymax, mirror=False):
    """Cut the mesh open along z = curve(x) for x in [x0, x1] (and its mirror if asked), on front faces only. Returns
    the list of (upper chain, lower chain, corner vertices) as vertex indices, chains ordered by x."""
    bm = bmesh.new(); bm.from_mesh(obj.data)
    ranges = [(x0, x1)] + ([(-x1, -x0)] if mirror else [])
    results = []
    for (a, b) in ranges:
        def cz(x):
            return curve(min(max(x, a), b))
        bm.verts.ensure_lookup_table()
        region = [f for f in bm.faces if all(a - 0.004 <= v.co.x <= b + 0.004 and abs(v.co.z - cz(v.co.x)) < zband
                                             and v.co.y < ymax for v in f.verts)]
        rverts = {v for f in region for v in f.verts}
        # snap near points onto the curve (no slivers), then warp, cut, unwarp
        for v in rverts:
            d = v.co.z - cz(v.co.x)
            if abs(d) < 0.00035 and a - 1e-4 <= v.co.x <= b + 1e-4:
                v.co.z = cz(v.co.x)
        for v in rverts:
            v.co.z -= cz(v.co.x)
        edges = list({e for f in region for e in f.edges})
        res = bmesh.ops.bisect_plane(bm, geom=region + edges + list(rverts), dist=1e-6, plane_co=(0, 0, 0),
                                     plane_no=(0, 0, 1))
        moved = set(rverts) | {g for g in res["geom_cut"] if isinstance(g, bmesh.types.BMVert)}
        on = {v for v in moved if abs(v.co.z) < 1e-6 and a - 1e-5 <= v.co.x <= b + 1e-5}
        for v in moved:
            v.co.z += cz(v.co.x)
        cut_edges = [e for e in bm.edges if e.verts[0] in on and e.verts[1] in on and len(e.link_faces) == 2]
        # keep the one path from a to b: walk from the vertex nearest a
        adj = {}
        for e in cut_edges:
            adj.setdefault(e.verts[0], []).append((e.verts[1], e)); adj.setdefault(e.verts[1], []).append((e.verts[0], e))
        start = min(adj, key=lambda v: v.co.x)
        chain, path_e, cur, prev = [start], [], start, None
        while True:
            nxt = [(w, e) for (w, e) in adj[cur] if w is not prev and w.co.x > cur.co.x - 1e-6 and w not in chain]
            if not nxt:
                break
            w, e = min(nxt, key=lambda t: t[0].co.x)
            chain.append(w); path_e.append(e); prev, cur = cur, w
        log("cut x %.4f..%.4f: %d edges on the line, chain %d verts from %.4f to %.4f" % (
            a, b, len(cut_edges), len(chain), chain[0].co.x, chain[-1].co.x))
        ends = (chain[0], chain[-1])
        keys = {tuple(round(c, 6) for c in v.co) for v in chain[1:-1]}
        bmesh.ops.split_edges(bm, edges=path_e)
        # after the split, the chain's inner verts are doubled: sort each by the side of its faces
        up, lo = [], []
        cand = [v for v in bm.verts if tuple(round(c, 6) for c in v.co) in keys]
        for v in cand:
            if v in ends or not v.link_faces:
                continue
            fz = np.mean([f.calc_center_median().z for f in v.link_faces]) - cz(v.co.x)
            (up if fz > 0 else lo).append(v)
        up.sort(key=lambda v: v.co.x); lo.sort(key=lambda v: v.co.x)
        bm.verts.index_update()
        results.append(dict(upper=[ends[0].index] + [v.index for v in up] + [ends[1].index],
                            lower=[ends[0].index] + [v.index for v in lo] + [ends[1].index],
                            range=(a, b)))
    bm.to_mesh(obj.data); bm.free()
    obj.data.update()
    # indices may shift with to_mesh? bmesh keeps order on to_mesh, so the saved indices hold.
    return results


def cut_mouth(head, F):
    r = cut_open(head, F.mouth_curve, -F.corner_x, F.corner_x, 0.3 * F.u, F.mouth_mid[1] + 0.35 * F.u)[0]
    F.lip = r
    me = head.data
    ends = max(abs(me.vertices[r["upper"][0]].co.x), abs(me.vertices[r["upper"][-1]].co.x))
    if ends < F.corner_x:
        log("mouth corners: the cut ends at %.4f (asked %.4f): the corners are there" % (ends, F.corner_x))
        F.corner_x = float(ends)
        F.corner = np.array([F.corner_x, F.corner[1], F.mouth_curve(F.corner_x)])
    F.m = F.corner_x / 0.68     # the mouth's own scale for its insides (u on a mouth of usual width)
    log("lips: upper %d, lower %d verts" % (len(r["upper"]), len(r["lower"])))
    return r


def cut_slits(head, F):
    F.slit_cuts = []
    for e in F.eyes:
        xs, zs = e["slit"]
        sgn = e["side"]
        curve = (lambda x, xs=xs, zs=zs: float(np.interp(abs(x), xs, zs)))
        a, b = (e["x0"], e["x1"]) if sgn > 0 else (-e["x1"], -e["x0"])
        r = cut_open(head, curve, a, b, 0.25 * F.u, e["c"][1] + 0.5 * F.u)[0]
        e["cut"] = r
        F.slit_cuts.append(r)


# ---------------------------------------------------------------------------------------------------- rolls
def add_roll(obj, chain, side, depth_fn, mat_index, uvname, into=None, rows_n=2, face_to=None, last=None):
    """Extrude a cut chain inward as rows (an inner lip, a lid's inside, or a whole mouth pouch). side +1 = rolls
    upward (an upper lip), -1 = downward. depth_fn(k) gives (back, along, taper power) offsets for row k. uvname: a
    palette cell, or a function of k. into: a point the rows head toward instead of straight back (an eye's centre).
    face_to: faces are wound to face this point (else by side). last: a list that receives the last row's indices.
    Returns {new vertex index: source vertex index}."""
    bm = bmesh.new(); bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    dl = bm.verts.layers.deform.active
    uvl = bm.loops.layers.uv.active
    C = [bm.verts[i] for i in chain]
    n = len(C)
    xs = np.array([v.co.x for v in C])
    xa, xb = xs[0], xs[-1]
    rows = [C]
    src = {}
    for k in range(1, rows_n + 1):
        row = [C[0]]
        dk = depth_fn(k)
        back, along = dk[0], dk[1]
        pw = dk[2] if len(dk) > 2 else 0.6
        for i in range(1, n - 1):
            v = C[i]
            t = (v.co.x - xa) / max(1e-9, (xb - xa))
            taper = math.sin(math.pi * t) ** pw
            if into is None:
                off = Vector((0, back * taper, side * along * taper))
            else:
                d = (Vector(into) - v.co)
                dist = d.length
                d.normalize()
                off = d * min(back * taper, dist - 0.0006) + Vector((0, 0, side * along * taper))
            nv = bm.verts.new(v.co + off)
            if dl is not None:
                nv[dl] = v[dl]
            src[nv] = v
            row.append(nv)
        row.append(C[-1])
        rows.append(row)
    bm.verts.index_update()
    faces = []
    for k in range(rows_n):
        A, B = rows[k], rows[k + 1]
        for i in range(n - 1):
            q = [A[i], A[i + 1], B[i + 1], B[i]]
            uq = []
            for v in q:
                if v not in uq:
                    uq.append(v)
            if len(uq) < 3:
                continue
            try:
                f = bm.faces.new(uq)
            except ValueError:
                continue
            faces.append((f, k + 1))
    # wind: toward face_to, else an upper roll faces down into the mouth (side +1 -> normal z < 0), a lower one up
    for f, k in faces:
        f.normal_update()
        if face_to is not None:
            if f.normal.dot(Vector(face_to) - f.calc_center_median()) < 0:
                f.normal_flip()
        elif f.normal.z * (-side) < 0:
            f.normal_flip()
        f.material_index = mat_index
        cell = uvname(k) if callable(uvname) else uvname
        for l in f.loops:
            l[uvl].uv = cell_uv(cell)
    bm.verts.index_update()
    out = {nv.index: s.index for nv, s in src.items()}
    if last is not None:
        last[:] = [v.index for v in rows[-1]]
    bm.to_mesh(obj.data); bm.free()
    return out


def add_lip_roll(head, F, mat_index):
    u = F.m
    # the inner lip (rows 1, 2) runs on into the mouth's roof and floor (rows 3, 4), and the two are joined at the
    # back: a closed pouch hung from the lips, so an open mouth never shows through the head (the 'mouth bag')
    rows = {1: (0.06 * u, 0.035 * u, 0.6), 2: (0.14 * u, 0.13 * u, 0.6), 3: (0.30 * u, 0.36 * u, 0.35),
            4: (0.62 * u, 0.30 * u, 0.3)}
    depth = lambda k: rows[k]
    cell = lambda k: "lip_in" if k <= 2 else "bag"
    inner = (0.0, F.mouth_mid[1] + 0.35 * u, F.mouth_mid[2])
    F.roll_src = {}
    lu, ll = [], []
    F.roll_src.update(add_roll(head, F.lip["upper"], +1, depth, mat_index, cell, rows_n=4, face_to=inner, last=lu))
    F.roll_src.update(add_roll(head, F.lip["lower"], -1, depth, mat_index, cell, rows_n=4, face_to=inner, last=ll))
    # keep the deep rows inside the head (at the corners the cheek turns back, and a roof row could poke out)
    me = head.data
    pulled = 0
    for nv, s in F.roll_src.items():
        p = Vector(me.vertices[nv].co); q = Vector(me.vertices[s].co)
        if (p - q).length < 0.001:
            continue
        for _ in range(20):
            loc, nrm, idx, d = F.bvh_all.find_nearest(p)
            need = 0.0025 if (p - q).length > 0.25 * u else 0.0006
            if loc is None or ((p - loc).dot(nrm) < 0 and d > need):
                break
            p = Vector(inner) + (p - Vector(inner)) * 0.88
            pulled += 1
        me.vertices[nv].co = p
    # the back wall
    bm = bmesh.new(); bm.from_mesh(head.data); bm.verts.ensure_lookup_table()
    uvl = bm.loops.layers.uv.active
    U = [bm.verts[i] for i in lu]; L = [bm.verts[i] for i in ll]
    nf = 0
    for i in range(len(U) - 1):
        q = []
        for v in (U[i], U[i + 1], L[i + 1], L[i]):
            if v not in q:
                q.append(v)
        if len(q) < 3:
            continue
        try:
            f = bm.faces.new(q)
        except ValueError:
            continue
        f.normal_update()
        if f.normal.dot(Vector(inner) - f.calc_center_median()) < 0:
            f.normal_flip()
        f.material_index = mat_index
        for l in f.loops:
            l[uvl].uv = cell_uv("bag")
        nf += 1
    bm.to_mesh(head.data); bm.free()
    F.pouch_back = (lu, ll)
    log("lip roll and pouch: %d verts, back wall %d faces" % (len(F.roll_src), nf))


def add_slit_rolls(head, F, mat_index):
    F.lid_roll_src = {}
    for e in F.eyes:
        r = e["r"]
        depth = lambda k, r=r: ((0.004, 0.0) if k == 1 else (0.012, 0.0))
        F.lid_roll_src.update(add_roll(head, e["cut"]["upper"], +1, depth, mat_index, "lid_in", into=e["c"]))
        F.lid_roll_src.update(add_roll(head, e["cut"]["lower"], -1, depth, mat_index, "lid_in", into=e["c"]))


# ---------------------------------------------------------------------------------------------------- the jaw
def add_jaw(armature, F):
    bpy.context.view_layer.objects.active = armature
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    armature.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = armature.data.edit_bones
    if "jaw" in eb:
        jb = eb["jaw"]
    else:
        jb = eb.new("jaw")
    inv = armature.matrix_world.inverted()
    h = inv @ Vector(F.hinge)
    jb.head = h
    jb.tail = inv @ Vector((0.0, F.chin[1], F.chin[2]))
    jb.parent = eb["head"]
    jb.use_connect = False
    jb.align_roll(Vector((0, 0, 1)))
    jb.use_deform = True
    bpy.ops.object.mode_set(mode="OBJECT")
    log("jaw bone: head %s tail %s" % (np.round(F.hinge, 4), np.round(F.chin, 4)))


def jaw_field(F, P, side_of=None):
    """How much each point follows the jaw (0..1), before the head weight and seam fade."""
    u = F.u
    cx = F.corner_x
    ax = np.abs(P[:, 0])
    zc = np.array([F.mouth_curve(x) for x in P[:, 0]])
    # outside the mouth: below the line from the corner back to the hinge
    yC, zC = F.corner[1], F.corner[2]
    # the line ends below the hinge (the cheekbone and the cheek above the jaw's ramus stay with the skull)
    yH, zH = F.hinge[1], F.hinge[2] - 0.4 * u
    t = np.clip((P[:, 1] - yC) / (yH - yC), 0, 1)
    zline = np.where(ax <= cx, zc, zC + (zH - zC) * t)
    # beyond the corner the line runs from the corner's height to the hinge's
    zline = np.where(ax > cx, zC + (zH - zC) * np.maximum(t, np.clip((ax - cx) / max(1e-6, F.ear[0] - cx), 0, 1)), zline)
    dz = P[:, 2] - zline
    outside = 1.0 - smoothstep(-0.25 * u, 0.25 * u, dz)
    front = 1.0 - smoothstep(yH - 0.45 * u, yH - 0.05 * u, P[:, 1])   # nothing at the ear
    outside *= front
    # in the mouth: by side, sealed at the corners (half), the lip's height fading
    # an oval opening: the lower lip's share falls from 1 in the middle to a half at the corner along an ellipse
    taper = np.sqrt(np.clip(1.0 - (ax / cx) ** 2, 0.0, 1.0))
    if side_of is None:
        side_of = np.sign(dz)
    lower = np.maximum(0.5 + 0.5 * taper, smoothstep(0.0, -0.45 * u, dz))
    upper = (0.5 - 0.5 * taper) * np.exp(-(dz / (0.22 * u)) ** 2)
    inside = np.where(side_of < 0, lower, upper)
    inside = np.where(dz < -0.5 * u, outside, inside)
    blend = smoothstep(cx, 1.25 * cx, ax)
    J = inside * (1 - blend) + outside * blend
    # under the jaw: full on the jaw's lower border (menton to gonion), fading to nothing down the throat, so the
    # skin between chin and throat stretches over a hand's width instead of folding
    M, G = F.chin_bottom, F.gonion
    dy, dzl = G[1] - M[1], G[2] - M[2]
    n = np.array([dzl, -dy]); n /= np.linalg.norm(n)
    if n[1] > 0:
        n = -n
    below = (P[:, 1] - M[1]) * n[0] + (P[:, 2] - M[2]) * n[1]
    J = J * (1.0 - smoothstep(0.15 * u, 1.6 * u, below))   # the whole chin rigid; a long fade down the throat
    return np.clip(J, 0, 1)


def weight_jaw(head, F, extra_side=None, seam=None, others=()):
    """Weights: jaw = J * head, head = (1 - J) * head; neck untouched. The same field is laid on `others` (the body:
    its under-jaw and throat), so the weights agree on both sides of the neck seam."""
    me = head.data
    P = mesh_arrays(head)
    side = side_flags(head, F, P)
    J = jaw_field(F, P, side)
    # smooth a little over the mesh (cuts keep the lips apart; the neck seam is held so both sides agree)
    nb = [[] for _ in range(len(me.vertices))]
    for e in me.edges:
        a, b = e.vertices
        nb[a].append(b); nb[b].append(a)
    lipset = set(F.lip["upper"]) | set(F.lip["lower"]) | set(F.roll_src.keys())
    if seam:
        lipset |= {i for i, p in enumerate(P) if tuple(np.round(np.array(me.vertices[i].co), 5)) in seam}
    for o in others:
        Po = mesh_arrays(o)
        Jo = jaw_field(F, Po, None)
        k = _lay_jaw(o, Jo)
        log("jaw weights on %s: %d verts" % (o.name, k))
    for _ in range(2):
        J2 = J.copy()
        for i in range(len(J)):
            if i in lipset or not nb[i]:
                continue
            J2[i] = 0.5 * J[i] + 0.5 * np.mean(J[nb[i]])
        J = J2
    # roll rows copy their lip vertex
    for nv, s in F.roll_src.items():
        J[nv] = J[s]
    k = _lay_jaw(head, J)
    F.J = J
    log("jaw weights: %d head verts on jaw" % k)


def _lay_jaw(o, J):
    """jaw = J x (head + neck), taken from head first, then from neck. (The builds weight the chin's underside partly
    to the neck; taking that share onto the jaw, which rides the head, also keeps the chin out of the neck when the
    head tilts back. The throat keeps its neck weight: J fades to 0 below the jaw's border.)"""
    wh = vgroup_weights(o, "head"); wn = vgroup_weights(o, "neck")
    gj = o.vertex_groups.get("jaw") or o.vertex_groups.new(name="jaw")
    gh = o.vertex_groups["head"]; gn = o.vertex_groups.get("neck")
    k = 0
    for i in range(len(J)):
        j = float(J[i] * (wh[i] + wn[i]))
        if j <= 1e-4:
            continue
        fh = min(j, wh[i]); fn = j - fh
        gj.add([i], j, "REPLACE")
        gh.add([i], float(wh[i] - fh), "REPLACE")
        if gn is not None and fn > 0:
            gn.add([i], float(wn[i] - fn), "REPLACE")
        k += 1
    return k


def side_flags(head, F, P):
    """+1 above the mouth line, -1 below; lip chain vertices by the chain they are in."""
    zc = np.array([F.mouth_curve(x) for x in P[:, 0]])
    s = np.sign(P[:, 2] - zc + 1e-9)
    for i in F.lip["upper"][1:-1]:
        s[i] = 1
    for i in F.lip["lower"][1:-1]:
        s[i] = -1
    for i in (F.lip["upper"][0], F.lip["upper"][-1]):
        s[i] = 0
    for nv, src in getattr(F, "roll_src", {}).items():
        s[nv] = s[src]
    return s


# ---------------------------------------------------------------------------------------------------- mouth parts
def palette_image(path):
    img = bpy.data.images.get("face_palette") or bpy.data.images.new("face_palette", len(PALETTE) * 4, 4)
    px = []
    for row in range(4):
        for name, c in PALETTE:
            for _ in range(4):
                px += [c[0], c[1], c[2], 1.0]
    img.pixels = px
    img.filepath_raw = path
    img.file_format = "PNG"
    try:
        img.save()
    except Exception as ex:
        log("palette not saved:", ex)
    return img


def palette_material(name, img):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    m.use_backface_culling = False
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img; tex.interpolation = "Closest"
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.9
    bsdf.inputs["Specular IOR Level"].default_value = 0.15
    return m


def _ellipsoid(cx, cy, cz, rx, ry, rz, nu=10, nv=6, vmin=0.0, vmax=math.pi):
    verts, faces = [], []
    for j in range(nv + 1):
        th = vmin + (vmax - vmin) * j / nv
        for i in range(nu):
            ph = 2 * math.pi * i / nu
            verts.append((cx + rx * math.sin(th) * math.cos(ph), cy + ry * math.sin(th) * math.sin(ph), cz + rz * math.cos(th)))
    for j in range(nv):
        for i in range(nu):
            a = j * nu + i; b = j * nu + (i + 1) % nu
            faces.append((a, b, b + nu, a + nu))
    return verts, faces


def add_mouth(armature, head, F, figure_name, img):
    """The dark bag, the teeth, the tongue: one mesh on head and jaw, one palette material, about 250 triangles."""
    u = F.m
    cx = F.corner_x
    ym, zm = F.mouth_mid[1], F.mouth_mid[2]
    V, Fc, UV, W = [], [], [], []   # W: jaw share per vertex

    def add(verts, faces, cell, jaw_of):
        base = len(V)
        for p in verts:
            V.append(p); W.append(jaw_of(p))
        for f in faces:
            Fc.append(tuple(base + i for i in f)); UV.append(cell)

    # (the bag itself is the pouch hung from the lips in the head mesh: add_lip_roll)
    # teeth: an arch strip each, teeth row and gum row (separate verts so each has its own colour)
    def arch(z_top, z_bot, y_front, width, cell_top, cell_bot, jaw, n=8):
        rowsz = [(z_top, cell_top), (z_bot, cell_bot)]
        out = []
        for (za, zb), cell in (((z_top[0], z_top[1]), cell_top), ((z_bot[0], z_bot[1]), cell_bot)):
            verts, faces = [], []
            for i in range(n + 1):
                s = -1 + 2 * i / n
                x = s * width
                y = y_front + 0.38 * u * s * s
                verts += [(x, y, za), (x, y, zb)]
            for i in range(n):
                a = 2 * i
                faces.append((a, a + 2, a + 3, a + 1))
            add(verts, faces, cell, lambda p, jaw=jaw: jaw)

    # upper: edge just below the line, gum above
    arch((zm - 0.05 * u, zm + 0.16 * u), (zm + 0.16 * u, zm + 0.27 * u), ym + 0.15 * u, cx * 0.8, "teeth", "gums", 0.0)
    # lower: behind the upper (overbite)
    arch((zm - 0.04 * u, zm - 0.19 * u), (zm - 0.19 * u, zm - 0.28 * u), ym + 0.19 * u, cx * 0.74, "teeth", "gums", 1.0)
    # the tongue: a low dome on the mouth's floor
    tv, tf = _ellipsoid(0.0, ym + 0.5 * u, zm - 0.24 * u, cx * 0.62, 0.3 * u, 0.11 * u, 8, 3, 0.0, math.pi / 2)
    add(tv, tf, "tongue", lambda p: 1.0)

    # teeth and tongue stay inside the head (a wide arch would poke out through the cheeks)
    inner = Vector((0.0, ym + 0.35 * u, zm))
    for i, p in enumerate(V):
        q = Vector(p)
        for _ in range(25):
            loc, nrm, idx, d = F.bvh_all.find_nearest(q)
            if loc is None or ((q - loc).dot(nrm) < 0 and d > 0.0012):
                break
            q = inner + (q - inner) * 0.9
        V[i] = tuple(q)
    me = bpy.data.meshes.new(figure_name + "_mouth")
    me.from_pydata(V, [], Fc)
    me.update()
    uvl = me.uv_layers.new(name="UVMap")
    for p, cell in zip(me.polygons, UV):
        for li in p.loop_indices:
            uvl.data[li].uv = cell_uv(cell)
    mat = bpy.data.materials.get(figure_name + "_mouth_in") or palette_material(figure_name + "_mouth", img)   # one material for all the insides
    me.materials.append(mat)
    ob = bpy.data.objects.new(figure_name + "_mouth", me)
    for c in head.users_collection:
        c.objects.link(ob)
    ob.parent = armature
    ob.matrix_world = Matrix.Identity(4)
    ob.matrix_parent_inverse = armature.matrix_world.inverted()
    gh = ob.vertex_groups.new(name="head"); gj = ob.vertex_groups.new(name="jaw")
    for i, w in enumerate(W):
        if w < 1:
            gh.add([i], 1 - w, "REPLACE")
        if w > 0:
            gj.add([i], w, "REPLACE")
    mod = ob.modifiers.new("Armature", "ARMATURE"); mod.object = armature
    me.shade_smooth()
    log("mouth parts: %d verts, %d triangles" % (len(me.vertices), sum(len(p.vertices) - 2 for p in me.polygons)))
    return ob


def settle_eyeballs(F):
    """Push each slit eye's ball back until no part of it shows through the skin at rest."""
    dirs = []
    for j in range(1, 7):
        th = math.pi / 2 * j / 6
        for i in range(12):
            ph = 2 * math.pi * i / 12
            dirs.append(Vector((math.sin(th) * math.cos(ph), -math.cos(th), math.sin(th) * math.sin(ph))))
    dirs.append(Vector((0, -1, 0)))
    for e in F.eyes:
        c = Vector(e["c"]); r = e["r"]
        for k in range(60):
            bad = 0
            for d in dirs:
                p = c + d * r
                # inside the head if a ray forward from it leaves through skin facing forward, at least 0.4 mm on
                hit = F.bvh.ray_cast(p, Vector((0, -1, 0)), 0.5)
                if hit[0] is None or hit[1].dot(Vector((0, -1, 0))) < 0 or hit[3] < 0.0004:
                    bad += 1
            if bad == 0:
                break
            c.y += 0.0005
        e["c"] = np.array(c)
        log("eyeball settled %d mm back" % round(k * 0.5))


def add_eyeballs(armature, head, F, figure_name):
    """Eyeballs for closed slits (the captain), so his eyes can pop open: a sphere each with a painted iris."""
    img = bpy.data.images.new(figure_name + "_eyeball", 64, 64)
    px = np.zeros((64, 64, 4))
    yy, xx = np.mgrid[0:64, 0:64]
    d = np.hypot(xx - 31.5, yy - 31.5) / 32.0
    sclera = np.array([0.92, 0.90, 0.84, 1]); iris = np.array([0.26, 0.36, 0.42, 1]); pupil = np.array([0.03, 0.03, 0.04, 1])
    px[:] = sclera
    px[d < 0.42] = iris
    px[d < 0.18] = pupil
    img.pixels = px.ravel()
    V, Fc, UVs = [], [], []
    for e in F.eyes:
        c, r = e["c"], e["r"]
        nu, nv = 12, 8
        base = len(V)
        for j in range(nv + 1):
            th = math.pi * j / nv
            for i in range(nu):
                ph = 2 * math.pi * i / nu
                # pole forward (-y)
                d3 = Vector((math.sin(th) * math.cos(ph), -math.cos(th), math.sin(th) * math.sin(ph)))
                V.append(tuple(Vector(c) + d3 * r))
                UVs.append((0.5 + 0.5 * d3.x * 1.0, 0.5 + 0.5 * d3.z))
        for j in range(nv):
            for i in range(nu):
                a = base + j * nu + i; b = base + j * nu + (i + 1) % nu
                Fc.append((a, a + nu, b + nu, b))
    me = bpy.data.meshes.new(figure_name + "_eyes")
    me.from_pydata(V, [], Fc); me.update()
    # outward winding
    bm = bmesh.new(); bm.from_mesh(me)
    for f in bm.faces:
        cc = Vector(F.eyes[0]["c"]) if f.calc_center_median().x > 0 == (F.eyes[0]["c"][0] > 0) else Vector(F.eyes[1]["c"])
        cc = min((Vector(e["c"]) for e in F.eyes), key=lambda q: (q - f.calc_center_median()).length)
        if f.normal.dot(f.calc_center_median() - cc) < 0:
            f.normal_flip()
    bm.to_mesh(me); bm.free()
    uvl = me.uv_layers.new(name="UVMap")
    for p in me.polygons:
        for li in p.loop_indices:
            uvl.data[li].uv = UVs[me.loops[li].vertex_index]
    m = bpy.data.materials.new(figure_name + "_eye"); m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    tex = m.node_tree.nodes.new("ShaderNodeTexImage"); tex.image = img
    m.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.25
    me.materials.append(m)
    me.shade_smooth()
    ob = bpy.data.objects.new(figure_name + "_eyes", me)
    for c in head.users_collection:
        c.objects.link(ob)
    ob.parent = armature
    g = ob.vertex_groups.new(name="head"); g.add(list(range(len(V))), 1.0, "REPLACE")
    mod = ob.modifiers.new("Armature", "ARMATURE"); mod.object = armature
    log("eyeballs for the slits: %d verts" % len(V))
    return ob


# ---------------------------------------------------------------------------------------------------- shapes
def _rot_about(P, c, axis, ang):
    """Rotate points P about the line through c along unit axis by per-point angles ang (Rodrigues)."""
    k = np.asarray(axis, float)
    V = P - c
    ca, sa = np.cos(ang)[:, None], np.sin(ang)[:, None]
    kv = np.cross(np.broadcast_to(k, V.shape), V)
    kd = (V @ k)[:, None]
    return c + V * ca + kv * sa + k * kd * (1 - ca)


def eye_frame(e, P):
    """Axis along the eye (inner to outer corner), forward, up; and per-point (s along, phi elevation, rho)."""
    c = e["c"]
    if e.get("margin"):
        M = P[e["margin"]]
        a = M[np.argmax(M[:, 0] * e["side"])] - M[np.argmin(M[:, 0] * e["side"])]
    else:
        a = np.array([e["side"], 0, 0.0])
    a = a / np.linalg.norm(a)
    a = a * np.sign(a[0]) if a[0] != 0 else a     # always +x-ish so 'up' is up on both eyes
    f = np.array([0, -1.0, 0]); f = f - a * (f @ a); f /= np.linalg.norm(f)
    up = np.cross(f, a)
    if up[2] < 0:
        up = -up
    V = P - c
    s = V @ a
    phi = np.arctan2(V @ up, V @ f)
    return a, f, up, s, phi


def lid_rotation(F, e, P, close_up, close_lo, band_up=None, band_lo=None):
    """Per-point rotation angle about the eye's axis: upper lid points turned by close_up(s) (radians, negative closes),
    lower by close_lo(s); with falloffs so nothing folds."""
    a, f, up, s, phi = eye_frame(e, P)
    r = e["r"]
    c = e["c"]
    if e.get("margin"):
        M = e["margin"]
        sm, pm = s[M], phi[M]
        # corners: extremes along s; upper margin = above the chord
        i0, i1 = np.argmin(sm), np.argmax(sm)
        chord = pm[i0] + (pm[i1] - pm[i0]) * (sm - sm[i0]) / max(1e-9, sm[i1] - sm[i0])
        hh = ((P[M] - c) @ up)
        hchord = hh[i0] + (hh[i1] - hh[i0]) * (sm - sm[i0]) / max(1e-9, sm[i1] - sm[i0])
        upm = hh >= hchord
        # the margin's angle as seen from the front: the angle on the ball that has the margin's height (the hole's
        # edge may lie well behind the lid's front edge; front edge and hole edge share a height, not an angle)
        Rb = max(1.06 * r, 1.02 * np.abs(hh).max())
        pm = np.arcsin(np.clip(hh / Rb, -1, 1))
        su, pu = sm[upm], pm[upm]; sl, pl = sm[~upm], pm[~upm]
        ou, ol = np.argsort(su), np.argsort(sl)
        su, pu, sl, pl = su[ou], pu[ou], sl[ol], pl[ol]
        s0, s1 = sm[i0], sm[i1]
    else:
        # a slit: both margins on the cut line
        Ch = e["cut"]["upper"]
        sm, pm = s[Ch], phi[Ch]
        o = np.argsort(sm)
        su = sl = sm[o]; pu = pl = pm[o]
        s0, s1 = su[0], su[-1]
    phu = np.interp(s, su, pu); phl = np.interp(s, sl, pl)
    t = np.clip((s - s0) / max(1e-9, s1 - s0), 0, 1)
    du = close_up(t, phu, phl); dl = close_lo(t, phu, phl)
    du = np.where((s < s0) | (s > s1), 0.0, du); dl = np.where((s < s0) | (s > s1), 0.0, dl)
    mx = max(1e-3, np.abs(du).max(), np.abs(dl).max())
    bu = band_up or max(0.55, 1.7 * np.abs(du).max())
    bl = band_lo or max(0.45, 1.7 * np.abs(dl).max())
    dist = np.linalg.norm(P - c, axis=1)
    radial = 1.0 - smoothstep(1.55 * r, 2.5 * r, dist)
    outside = smoothstep(0.0, -0.45 * r, np.minimum(s - s0, s1 - s))   # fade beyond the corners
    outside = 1.0 - outside
    # which lid a point belongs to, and how far from its edge, is measured in the FRONT view (height along `up`):
    # lids have thickness, and the hole's edge (the margin found) can sit several mm behind the lid's front edge, at
    # the same height but a different angle about the ball's centre
    hgt = (P - c) @ up
    Mi = e["margin"] if e.get("margin") else e["cut"]["upper"]
    hm = hgt[Mi]; smm = s[Mi]
    if e.get("margin"):
        hu_s, hu_h = su, np.interp(su, smm[np.argsort(smm)], hm[np.argsort(smm)])
        # per margin vertex heights, split as above
        Mu = np.array(Mi)[upm]; Ml = np.array(Mi)[~upm]
        ou2, ol2 = np.argsort(s[Mu]), np.argsort(s[Ml])
        hu = np.interp(s, s[Mu][ou2], hgt[Mu][ou2]); hl = np.interp(s, s[Ml][ol2], hgt[Ml][ol2])
    else:
        o2 = np.argsort(smm)
        hu = hl = np.interp(s, smm[o2], hm[o2])
    rr = max(r, 1e-3)
    bhu = float(np.clip(1.7 * np.abs(du).max() * rr, 0.6 * rr, 1.0 * rr))   # the lid itself; the skin above stretches
    bhl = float(np.clip(1.7 * np.abs(dl).max() * rr, 0.5 * rr, 0.8 * rr))
    tol = 0.0004
    wu = (1.0 - smoothstep(0.35 * bhu, bhu, hgt - hu)) * (hgt >= hu - tol)
    wl = (1.0 - smoothstep(0.35 * bhl, bhl, hl - hgt)) * (hgt <= hl + tol)
    # the slit's margins are the same line: split by the vertex's side instead
    if not e.get("margin"):
        side = e.get("side_flags")
        if side is not None:
            wu = np.where(side > 0, 1.0 - smoothstep(0.0, bhu, np.maximum(hgt - hu, 0)), 0.0)
            wl = np.where(side < 0, 1.0 - smoothstep(0.0, bhl, np.maximum(hl - hgt, 0)), 0.0)
    ang = (du * wu + dl * wl) * radial * outside
    # the eye's own hole/inside: only points in front of the ball's centre plane
    ang = np.where((P - c) @ f > -0.3 * r, ang, 0.0)
    return a, ang


def lid_remap(F, e, P, up_to, lo_to):
    """Move the lids by sliding them over the eyeball: in the eye's frame (s along the eye, h up, depth forward), each
    point of the upper lid's band [hu, hu + B] is mapped linearly onto [hu', hu + B] (hu' = up_to(t, hu, hl), the
    edge's new height), the lower lid's band likewise, and the point is put back at its own distance from the ball's
    centre (at least a shell 1.5 mm off the ball), keeping s. Linear in h, so nothing folds; on the shell, so the lid
    never goes through the ball. Returns the moved points."""
    a, f, up, s, phi = eye_frame(e, P)
    r, c = e["r"], e["c"]
    V = P - c
    h = V @ up
    fw = V @ f
    d = np.linalg.norm(V, axis=1)
    if e.get("margin"):
        M = np.array(e["margin"])
        sm, hm = s[M], h[M]
        i0, i1 = np.argmin(sm), np.argmax(sm)
        hchord = hm[i0] + (hm[i1] - hm[i0]) * (sm - sm[i0]) / max(1e-9, sm[i1] - sm[i0])
        upm = hm >= hchord
        ou, ol = np.argsort(sm[upm]), np.argsort(sm[~upm])
        hu = np.interp(s, sm[upm][ou], hm[upm][ou]); hl = np.interp(s, sm[~upm][ol], hm[~upm][ol])
        s0, s1 = sm[i0], sm[i1]
    else:
        Ch = np.array(e["cut"]["upper"])
        o = np.argsort(s[Ch])
        hu = hl = np.interp(s, s[Ch][o], h[Ch][o])
        s0, s1 = s[Ch].min(), s[Ch].max()
    t = np.clip((s - s0) / max(1e-9, s1 - s0), 0, 1)
    inside_s = (s >= s0) & (s <= s1)
    hu2 = np.where(inside_s, up_to(t, hu, hl), hu)
    hl2 = np.where(inside_s, lo_to(t, hu, hl), hl)
    Bu, Bl = 1.1 * r, 0.8 * r
    side = e.get("side_flags")
    # the lid's front edge can sit a little below the hole's edge (thick lids): reach down to it
    tol = np.minimum(0.3 * r, 0.3 * np.maximum(hu - hl, 0.0)) + 0.0004
    is_up = (h >= hu - tol) if side is None else (side > 0)
    is_lo = (h <= hl + tol) if side is None else (side < 0)
    # fade beyond the corners and far from the eye
    fade = (1.0 - smoothstep(0.0, 0.5 * r, np.maximum(s0 - s, s - s1))) * (1.0 - smoothstep(1.7 * r, 2.6 * r, d))
    fade *= (fw > -0.2 * r)
    hn = h.copy()
    bu = is_up & (h <= hu + Bu)
    k = (h[bu] - hu[bu]) / Bu                         # 0 at the edge .. 1 at the band's top
    hn[bu] = hu2[bu] + np.clip(k, 0, 1) * (hu[bu] + Bu - hu2[bu])
    bl = is_lo & (h >= hl - Bl)
    k = (hl[bl] - h[bl]) / Bl
    hn[bl] = hl2[bl] - np.clip(k, 0, 1) * (hl2[bl] - (hl[bl] - Bl))
    hn = h + (hn - h) * fade
    moved = np.abs(hn - h) > 1e-7
    ro = max(r, e.get("r_out", r))
    shell = np.where(is_up, ro + 0.0012, ro + 0.0006)   # over the cornea; the upper lid rides just over the lower
    dn = np.where(moved, np.maximum(d, shell), d)
    f2 = dn * dn - s * s - hn * hn
    fwd_new = np.sqrt(np.maximum(f2, (0.25 * r) ** 2))
    # (a moved point always comes out in front of the ball, on or beyond the shell)
    # keep the lid's own thickness: points that were behind the front edge stay as far behind
    Q = c + np.outer(s, a) + np.outer(hn, up) + np.outer(np.where(moved, fwd_new, fw), f)
    Q[~moved] = P[~moved]
    return Q


def lids_delta(F, P, which, amount=1.0, sides=(1, -1), mask=None):
    """Delta for lid shapes. which: closed | wide | squint. (Sliding remap: lid_remap.)"""
    D = np.zeros_like(P)
    for e in F.eyes:
        if e["side"] not in sides:
            continue
        r = e["r"]
        bump_ = lambda t: np.sin(np.pi * t) ** 0.7
        if F.slits:
            if which == "closed":      # a squeeze: the folds above and below press toward the slit
                ut = lambda t, hu, hl: hu - 0.0 * t
                lt = lambda t, hu, hl: hl + 0.0 * t
            elif which == "wide":      # the slits pop open on to the eyeballs
                ut = lambda t, hu, hl: hu + 0.55 * r * bump_(t) * amount
                lt = lambda t, hu, hl: hl - 0.3 * r * bump_(t) * amount
            else:
                ut = lambda t, hu, hl: hu
                lt = lambda t, hu, hl: hl
        else:
            if which == "closed":
                ut = lambda t, hu, hl: hu + ((hl + 0.32 * (hu - hl)) - hu) * amount   # past the lower: a little overlap
                lt = lambda t, hu, hl: hl + ((hl + 0.42 * (hu - hl)) - hl) * amount
            elif which == "wide":
                ut = lambda t, hu, hl: hu + 0.22 * (hu - hl) * amount
                lt = lambda t, hu, hl: hl - 0.08 * (hu - hl) * amount
            else:  # squint
                ut = lambda t, hu, hl: hu - 0.15 * (hu - hl) * amount
                lt = lambda t, hu, hl: hl + 0.35 * (hu - hl) * amount
        Q = lid_remap(F, e, P, ut, lt)
        D += Q - P
    if F.slits and which in ("closed", "squint"):
        # closed slits: the lids are already shut; a blink or squint scrunches the skin round them instead
        for e in F.eyes:
            if e["side"] not in sides:
                continue
            c, r = e["c"], e["r"]
            above = bump(P, [abs(c[0]), c[1] - r, c[2] + 0.9 * r], [1.3 * r, 1.2 * r, 0.6 * r])
            below = bump(P, [abs(c[0]), c[1] - r, c[2] - 0.9 * r], [1.3 * r, 1.2 * r, 0.6 * r])
            sidem = (np.sign(P[:, 0]) == e["side"]).astype(float)
            k = 1.0 if which == "closed" else 0.7
            D[:, 2] += (-0.18 * r * above + 0.22 * r * below) * sidem * k * amount
            D[:, 1] -= 0.06 * r * (above + below) * sidem * k * amount
    return D


def _lids_delta_rotation(F, P, which, amount=1.0, sides=(1, -1), mask=None):
    """(Retired: lids turned about the ball's centre. Kept for reference; lids_delta slides them instead.)"""
    D = np.zeros_like(P)
    for e in F.eyes:
        if e["side"] not in sides:
            continue
        if F.slits:
            if which == "closed":
                cu = lambda t, pu, pl: -0.10 * np.sin(np.pi * t) * amount
                cl = lambda t, pu, pl: 0.08 * np.sin(np.pi * t) * amount
            elif which == "wide":
                cu = lambda t, pu, pl: 0.55 * np.sin(np.pi * t) ** 0.7 * amount
                cl = lambda t, pu, pl: -0.22 * np.sin(np.pi * t) ** 0.7 * amount
            else:
                cu = lambda t, pu, pl: -0.08 * np.sin(np.pi * t) * amount
                cl = lambda t, pu, pl: 0.12 * np.sin(np.pi * t) * amount
        else:
            if which == "closed":
                cu = lambda t, pu, pl: ((pl + 0.4 * (pu - pl)) - pu) * amount
                cl = lambda t, pu, pl: ((pl + 0.4 * (pu - pl)) - pl) * amount
            elif which == "wide":
                cu = lambda t, pu, pl: 0.55 * (pu - pl) * amount + 0 * t
                cl = lambda t, pu, pl: -0.12 * (pu - pl) * amount
            else:  # squint
                cu = lambda t, pu, pl: -0.16 * (pu - pl) * amount
                cl = lambda t, pu, pl: 0.36 * (pu - pl) * amount
        a, ang = lid_rotation(F, e, P, cu, cl)
        Q = _rot_about(P, e["c"], a, -ang)   # a + turn about a lowers phi (up = f x a)
        # lids rest with their inner rim tucked just inside the ball's sphere (on the ball, as real lids do); a lid that
        # sweeps down over the ball must ride outside it, so every point that turns is pushed out to a shell 1.2 mm
        # off the ball, in proportion to how far it turns (the emg2face sphere remap; the chord between rest and
        # full sags at most about 0.6 mm, inside the margin)
        V = Q - e["c"]; d = np.linalg.norm(V, axis=1)
        top = np.abs(ang).max()
        if top > 1e-6:
            frac = np.clip(4.0 * np.abs(ang) / top, 0, 1)
            shell = e["r"] + 0.0012
            want = d + frac * np.maximum(0.0, shell - d)
            k = np.abs(ang) > 1e-6
            Q[k] = e["c"] + V[k] / d[k, None] * want[k, None]
        D += Q - P
    return D


def add_shapes(head, F, params):
    me = head.data
    P = mesh_arrays(head)
    N = np.array([v.normal for v in me.vertices])
    u = F.u
    cx = F.corner_x
    side = side_flags(head, F, P)
    for e in F.eyes:
        e["side_flags"] = None
    if F.slits:
        for e in F.eyes:
            sf = np.zeros(len(P))
            cut = e["cut"]
            for i in cut["upper"][1:-1]:
                sf[i] = 1
            for i in cut["lower"][1:-1]:
                sf[i] = -1
            # other points: above/below the slit curve
            xs, zs = e["slit"]
            zc = np.interp(np.abs(P[:, 0]), xs, zs)
            rest = sf == 0
            sf[rest] = np.sign(P[rest, 2] - zc[rest] + 1e-9)
            for nv, s in F.lid_roll_src.items():
                sf[nv] = sf[s]
            e["side_flags"] = sf
    # mask: nothing moves at the neck seam or the back of the head
    mask = np.ones(len(P))
    if F.seam_kd is not None:
        for i, p in enumerate(P):
            co, idx, d = F.seam_kd.find(Vector(p))
            mask[i] = float(smoothstep(0.3 * u, 0.8 * u, d))
    mask *= 1.0 - smoothstep(F.hinge[1] - 0.1 * u, F.hinge[1] + 0.3 * u, P[:, 1])
    sgnx = np.sign(P[:, 0])
    corner = np.array([cx, F.corner[1], F.corner[2]])
    lipzone = bump(P, [0, F.mouth_mid[1], F.mouth_mid[2]], [cx * 1.25, 0.45 * u, 0.42 * u])
    near_line = np.exp(-((P[:, 2] - np.array([F.mouth_curve(x) for x in P[:, 0]])) / (0.2 * u)) ** 2)
    upper = (side > 0).astype(float); lower = (side < 0).astype(float)
    cheek = bump(P, F.cheek, [0.55 * u, 0.6 * u, 0.45 * u])
    brow_c = np.array([F.eye_x, 0, F.brow_z])
    sm, br, ld = params["smile"], params["brows"], params["lids"]
    D = {}

    # smile: corners up, back and out; cheeks up and forward; lower lids pushed up a little
    cb = bump(P, corner, [0.55 * u, 0.6 * u, 0.42 * u])
    d = np.zeros_like(P)
    d[:, 2] += 0.17 * u * cb * sm
    d[:, 1] += 0.10 * u * cb * sm
    d[:, 0] += sgnx * 0.07 * u * cb * sm
    d[:, 2] += 0.07 * u * cheek * sm
    d[:, 1] -= 0.035 * u * cheek * sm
    d += 0.25 * lids_delta(F, P, "squint")
    D["smile"] = d
    # frown: corners down, chin pushed up a little
    d = np.zeros_like(P)
    d[:, 2] -= 0.13 * u * cb
    d[:, 0] += sgnx * 0.02 * u * cb
    chinb = bump(P, F.chin, [0.6 * u, 0.5 * u, 0.35 * u])
    d[:, 2] += 0.04 * u * chinb
    d[:, 1] -= 0.02 * u * chinb
    D["frown"] = d
    # mouth_o: lips together inward and forward, the middle opening a little
    d = np.zeros_like(P)
    lz = lipzone
    d[:, 0] -= 0.38 * P[:, 0] * lz
    d[:, 1] -= 0.12 * u * lz
    mid_open = np.cos(np.clip(np.abs(P[:, 0]) / cx, 0, 1) * np.pi / 2)
    d[:, 2] += 0.06 * u * lz * mid_open * (upper - lower) * near_line
    D["mouth_o"] = d
    # mouth_wide: corners out and back, upper lip up, lower lip down (with the jaw: a shout or a laugh)
    d = np.zeros_like(P)
    d[:, 0] += sgnx * 0.24 * u * cb
    d[:, 1] += 0.06 * u * cb
    d[:, 2] += 0.03 * u * cb
    lipmid = lz * np.exp(-((np.abs(P[:, 0]) - 0.45 * cx) / (0.6 * cx)) ** 2)
    d[:, 2] += 0.16 * u * lipmid * upper * near_line
    d[:, 2] -= 0.09 * u * lipmid * lower * near_line
    D["mouth_wide"] = d
    # lips_press: lips thinner (pressed toward the line, never across it) and drawn back
    d = np.zeros_like(P)
    zc = np.array([F.mouth_curve(x) for x in P[:, 0]])
    dz = P[:, 2] - zc
    squeeze = np.sign(dz) * smoothstep(0.0, 0.12 * u, np.abs(dz)) * np.exp(-(np.abs(dz) / (0.32 * u)) ** 2)
    d[:, 2] -= 0.05 * u * squeeze * lz
    d[:, 1] += 0.04 * u * lz
    d[:, 2] += 0.03 * u * chinb
    D["lips_press"] = d
    # cheeks_puff: cheeks out along their normals, lips pushed forward and pressed
    d = np.zeros_like(P)
    pc = bump(P, [cx + 0.5 * u, F.corner[1] + 0.35 * u, F.corner[2] + 0.12 * u], [0.6 * u, 0.7 * u, 0.55 * u])
    d += N * (0.2 * u * pc)[:, None]
    d[:, 1] -= 0.04 * u * lz
    D["cheeks_puff"] = d
    # brows
    def brow_zone(xc, rx):
        b = bump(P, [xc, 0, F.brow_z + 0.05 * u], [rx, 9.0, 0.42 * u])
        # not the lids themselves
        above = smoothstep(F.eye_z + 0.2 * F.eye_r, F.eye_z + 1.0 * F.eye_r, P[:, 2])
        return b * above
    bz = brow_zone(F.eye_x, 0.85 * u)
    d = np.zeros_like(P); d[:, 2] += 0.11 * u * bz * br
    fore = bump(P, [F.eye_x * 0.5, 0, F.brow_z + 0.7 * u], [1.4 * u, 9.0, 0.5 * u])
    d[:, 2] += 0.04 * u * fore * br
    D["brows_up"] = d
    bi = brow_zone(F.eye_x * 0.55, 0.55 * u)
    d = np.zeros_like(P)
    d[:, 2] -= 0.15 * u * bi * br
    d[:, 0] -= sgnx * 0.07 * u * bi * br
    d[:, 1] -= 0.02 * u * bi * br
    bo = brow_zone(F.eye_x * 1.3, 0.5 * u)
    d[:, 2] -= 0.04 * u * bo * br
    D["brows_down"] = d
    d = np.zeros_like(P)
    d[:, 2] += 0.16 * u * bi * br
    d[:, 0] -= sgnx * 0.02 * u * bi * br
    d[:, 2] -= 0.05 * u * bo * br
    D["brows_sad"] = d
    # lids
    D["eyes_closed"] = lids_delta(F, P, "closed", ld)
    D["eyes_wide"] = lids_delta(F, P, "wide", ld) + 0.35 * D["brows_up"]
    d = lids_delta(F, P, "squint", ld)
    d[:, 2] += 0.05 * u * cheek; d[:, 1] -= 0.02 * u * cheek
    D["squint"] = d
    # sneer: nose wings and the upper lip beside them up
    d = np.zeros_like(P)
    al = bump(P, F.ala, [0.3 * u, 0.4 * u, 0.3 * u])
    d[:, 2] += 0.07 * u * al
    d[:, 1] -= 0.01 * u * al
    ul = bump(P, [0.45 * cx, F.mouth_mid[1], F.mouth_mid[2] + 0.12 * u], [0.45 * cx, 0.4 * u, 0.22 * u]) * upper
    d[:, 2] += 0.07 * u * ul
    bridge = bump(P, [0.15 * u, 0, F.nasion[2] - 0.25 * u], [0.3 * u, 9, 0.3 * u])
    d[:, 2] += 0.02 * u * bridge
    D["sneer"] = d
    # halves (figure's left is +x)
    left = smoothstep(-0.12 * u, 0.12 * u, P[:, 0])
    D["eyes_closed_L"] = lids_delta(F, P, "closed", ld, sides=(1,))
    D["eyes_closed_R"] = lids_delta(F, P, "closed", ld, sides=(-1,))
    D["smile_L"] = D["smile"] * left[:, None]
    D["smile_R"] = D["smile"] * (1 - left)[:, None]

    # roll rows copy their source; mask; keep the corners and the cut sealed where they should be
    rolls = dict(getattr(F, "roll_src", {})); rolls.update(getattr(F, "lid_roll_src", {}))
    for k in D:
        d = D[k] * mask[:, None]
        for nv, s in rolls.items():
            d[nv] = d[s]
        D[k] = d
    # write shape keys
    if me.shape_keys is None:
        head.shape_key_add(name="Basis", from_mix=False)
    base = P
    inv = head.matrix_world.inverted()
    for name in SHAPES:
        kb = me.shape_keys.key_blocks.get(name) or head.shape_key_add(name=name, from_mix=False)
        Q = base + D[name]
        kb.data.foreach_set("co", np.array([inv @ Vector(q) for q in Q]).ravel())
        kb.value = 0.0
    F.D = D
    moving = np.zeros(len(P), bool)
    for k in D:
        moving |= np.linalg.norm(D[k], axis=1) > 1e-6
    log("shapes: %d, head verts %d, verts any shape moves %d" % (len(SHAPES), len(P), int(moving.sum())))
    return D


# ---------------------------------------------------------------------------------------------------- checks
def check_faces(head, F):
    """Inside-out at rest (normals against the outward direction from the head's middle, for the skin), folded faces
    in every shape and in the laugh/shout mixes with the jaw open, lids inside eyeballs, teeth in front of lips."""
    me = head.data
    P = mesh_arrays(head)
    polys = [list(p.vertices) for p in me.polygons]
    tris = []
    for p in polys:
        for k in range(1, len(p) - 1):
            tris.append((p[0], p[k], p[k + 1]))
    T = np.array(tris)

    def normals(Q):
        n = np.cross(Q[T[:, 1]] - Q[T[:, 0]], Q[T[:, 2]] - Q[T[:, 0]])
        return n / np.maximum(1e-12, np.linalg.norm(n, axis=1))[:, None]
    n0 = normals(P)
    # inside-out at rest: skin faces whose normal points toward the head's middle
    mid = np.array([0, F.ear[1], F.eye_z - 0.5 * F.u])
    cen = (P[T[:, 0]] + P[T[:, 1]] + P[T[:, 2]]) / 3
    isface = [bool(m and m.name.endswith("_face")) for m in me.materials]
    skin = np.array([isface[me.polygons[i].material_index] for i, p in enumerate(polys) for _ in range(len(p) - 2)])
    out = np.einsum("ij,ij->i", n0, cen - mid) < 0
    # the face's own folds (nostrils, ear bowls, lid insides) point inward legitimately: count against the mesh's
    # stored normals instead, which the build made outward
    vn = np.array([v.normal for v in me.vertices])
    tn = vn[T[:, 0]] + vn[T[:, 1]] + vn[T[:, 2]]
    rep = {"rest_faces_against_vertex_normals": int((np.einsum("ij,ij->i", n0, tn) < 0).sum()),
           "rest_skin_faces_toward_middle": int((out & skin).sum())}
    J = getattr(F, "J", np.zeros(len(P)))
    wh = vgroup_weights(head, "head") + vgroup_weights(head, "jaw")
    Jw = vgroup_weights(head, "jaw")

    def jaw_open(Q, deg):
        R = np.array(Matrix.Rotation(math.radians(deg), 3, "X"))  # a + turn about X drops the chin (front is -y)
        Qr = (Q - F.hinge) @ R.T + F.hinge
        return Q + Jw[:, None] * (Qr - Q)
    mixes = {k: {k: 1.0} for k in SHAPES}
    mixes["laugh"] = {"mouth_wide": 1.0, "eyes_closed": 1.0, "brows_up": 0.6, "smile": 0.8, "_jaw": 25}
    mixes["shock"] = {"eyes_wide": 1.0, "brows_up": 1.0, "mouth_o": 0.8, "_jaw": 15}
    mixes["shout"] = {"brows_down": 1.0, "mouth_wide": 1.0, "sneer": 0.5, "_jaw": 20}
    mixes["jaw25"] = {"_jaw": 25}
    mixes["blink_half"] = {"eyes_closed": 0.5}
    mixes["wide_half"] = {"eyes_wide": 0.5}
    for name, mix in mixes.items():
        Q = P.copy()
        for k, v in mix.items():
            if k != "_jaw":
                Q = Q + v * F.D[k]
        if "_jaw" in mix:
            Q = jaw_open(Q, mix["_jaw"])
        n1 = normals(Q)
        fl = np.einsum("ij,ij->i", n0, n1) < 0
        flips = int(fl.sum())
        fz = cen[fl & skin]
        where_ = "" if len(fz) == 0 else "skin z %.3f..%.3f y %.3f..%.3f" % (fz[:, 2].min(), fz[:, 2].max(), fz[:, 1].min(), fz[:, 1].max())
        inside = 0
        for e in F.eyes:
            d = np.linalg.norm(Q - e["c"], axis=1)
            d0 = np.linalg.norm(P - e["c"], axis=1)
            inside += int(((d < e["r"] - 0.0003) & (d0 >= e["r"] - 0.0003)).sum())
        rep[name] = dict(flipped=flips, flipped_skin=int((fl & skin).sum()), where=where_, into_eyeball=inside, max_move_mm=round(float(np.abs(Q - P).max() * 1000), 1))
    return rep


def shape_cost(head, mouth, body):
    def tris(o):
        return sum(len(p.vertices) - 2 for p in o.data.polygons)
    return dict(head_verts=len(head.data.vertices), head_tris=tris(head), mouth_tris=tris(mouth),
                body_tris_after=tris(body), shapes=len(SHAPES))


# ---------------------------------------------------------------------------------------------------- hair
def bind_to_face(obj, head):
    """Bind a separate piece (a beard, a moustache, eyebrows) to the face: copy the head's bone weights (head, jaw,
    neck) and every shape key's movement from the nearest point on the head's surface. Call after add_shapes, before
    export. The piece then follows the jaw and every expression."""
    hm = head.data
    bvh = _bvh(head)
    keys = hm.shape_keys.key_blocks if hm.shape_keys else []
    HP = mesh_arrays(head)
    if obj.data.shape_keys is None:
        obj.shape_key_add(name="Basis", from_mix=False)
    groups = [g.name for g in head.vertex_groups]
    wt = {g: vgroup_weights(head, g) for g in groups}
    moves = {k.name: np.array([head.matrix_world @ d.co for d in k.data]) - HP for k in keys if k.name != "Basis"}
    OP = mesh_arrays(obj)
    res = {k: np.zeros_like(OP) for k in moves}
    W = {g: np.zeros(len(OP)) for g in groups}
    for i, p in enumerate(OP):
        loc, nrm, fi, dist = bvh.find_nearest(Vector(p))
        poly = hm.polygons[fi]
        vs = list(poly.vertices)
        # inverse-distance weights over the face's corners
        dd = np.array([np.linalg.norm(HP[v] - np.array(loc)) for v in vs]) + 1e-6
        b = (1 / dd) / (1 / dd).sum()
        for k in moves:
            res[k][i] = (moves[k][vs] * b[:, None]).sum(axis=0)
        for g in groups:
            W[g][i] = float((wt[g][vs] * b).sum())
    for g in groups:
        vg = obj.vertex_groups.get(g) or obj.vertex_groups.new(name=g)
        for i in range(len(OP)):
            if W[g][i] > 1e-4:
                vg.add([i], W[g][i], "REPLACE")
    inv = obj.matrix_world.inverted()
    for k, d in res.items():
        kb = obj.shape_key_add(name=k, from_mix=False)
        kb.data.foreach_set("co", np.array([inv @ Vector(q) for q in OP + d]).ravel())


# ---------------------------------------------------------------------------------------------------- normals, export
def finish_normals(head, seam, tables, F):
    by_face, by_vert = tables
    pairs = set()
    cuts = [F.lip] + list(getattr(F, "slit_cuts", []))
    for c in cuts:
        for i in c["upper"] + c["lower"]:
            pairs.add(tuple(np.round(np.array(head.data.vertices[i].co), 5)))
    apply_normals(head, by_face, by_vert, only_verts=seam, avg_pairs=pairs)


def zero_still_normals(glb_path, eps=1e-7):
    """In the written glb, zero every morph target's normal change where its position does not move (the exporter
    measures shape normals against the plain smooth ones, so the kept seam normals would otherwise jump)."""
    with open(glb_path, "rb") as fh:
        data = bytearray(fh.read())
    magic, ver, length = struct.unpack_from("<III", data, 0)
    jlen, jtype = struct.unpack_from("<II", data, 12)
    js = json.loads(data[20:20 + jlen].decode("utf8"))
    boff = 20 + jlen + 8
    acc, bvs = js["accessors"], js["bufferViews"]

    def view(ai):
        a = acc[ai]
        bv = bvs[a["bufferView"]]
        off = boff + bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        stride = bv.get("byteStride", 12)
        return off, stride, a["count"]
    fixed = 0
    for m in js["meshes"]:
        for pr in m["primitives"]:
            for t in pr.get("targets", []):
                if "NORMAL" not in t or "POSITION" not in t:
                    continue
                if "sparse" in acc[t["POSITION"]] or "sparse" in acc[t["NORMAL"]] or "bufferView" not in acc[t["NORMAL"]]:
                    continue
                po, ps, cnt = view(t["POSITION"]); no, ns, _ = view(t["NORMAL"])
                for i in range(cnt):
                    x, y, z = struct.unpack_from("<fff", data, po + i * ps)
                    if abs(x) < eps and abs(y) < eps and abs(z) < eps:
                        nx, ny, nz = struct.unpack_from("<fff", data, no + i * ns)
                        if nx or ny or nz:
                            struct.pack_into("<fff", data, no + i * ns, 0.0, 0.0, 0.0)
                            fixed += 1
    with open(glb_path, "wb") as fh:
        fh.write(data)
    log("zeroed %d still normal deltas" % fixed)


# ---------------------------------------------------------------------------------------------------- all of it
def rig_face(armature, body, eyes, figure="brother", tex_dir=None):
    params = dict(FIGURES.get(figure, FIGURES["npc"]))
    if eyes is None:
        params["slits"] = True    # no eyeball mesh: treat the eyes as closed slits (found by their crease)
    name = body.name[:-5] if body.name.endswith("_body") else figure
    head, seam, tables = split_head(body, armature, name)
    F = find_face_landmarks(head, eyes if not params["slits"] else None, seam, body=body)
    img = palette_image(os.path.join(tex_dir or bpy.app.tempdir, "face_palette.png"))
    mat = palette_material(name + "_mouth_in", img)
    head.data.materials.append(mat)
    mi = len(head.data.materials) - 1
    cut_mouth(head, F)
    add_lip_roll(head, F, mi)
    if F.slits:
        settle_eyeballs(F)
        cut_slits(head, F)
        add_slit_rolls(head, F, mi)
    add_jaw(armature, F)
    weight_jaw(head, F, seam=seam, others=[body])
    mouth = add_mouth(armature, head, F, name, img)
    eyes_new = add_eyeballs(armature, head, F, name) if F.slits else None
    add_shapes(head, F, params)
    finish_normals(head, seam, tables, F)
    rep = shape_cost(head, mouth, body)
    rep["checks"] = check_faces(head, F)
    rep["landmarks"] = dict(u=F.u, corner_x=F.corner_x, mouth=F.mouth_mid.tolist(), hinge=F.hinge.tolist(),
                            menton=F.chin_bottom.tolist(), gonion=F.gonion.tolist(), ear=F.ear.tolist(),
                            chin=F.chin.tolist(), eyes=[dict(c=e["c"].tolist(), r=e["r"]) for e in F.eyes])
    return dict(head=head, mouth=mouth, eyes=eyes_new, report=rep, face=F)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    src, dst = argv[0], argv[1]
    figure = argv[argv.index("--figure") + 1] if "--figure" in argv else os.path.basename(src).split(".")[0].split("_")[0]
    report_path = argv[argv.index("--report") + 1] if "--report" in argv else None
    keep_blend = argv[argv.index("--keep-blend") + 1] if "--keep-blend" in argv else None
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=os.path.abspath(src), merge_vertices=True)
    for o in list(bpy.data.objects):
        if o.type == "MESH" and o.parent is None and o.name.startswith("Icosphere"):
            bpy.data.objects.remove(o)       # the importer's bone shape
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    body = next(o for o in bpy.data.objects if o.type == "MESH" and o.name.endswith("_body"))
    eyes = next((o for o in bpy.data.objects if o.type == "MESH" and o.name.endswith("_eyes")), None)
    tex_dir = os.path.join(os.path.dirname(os.path.abspath(dst)), "..", "..", "textures", "face")
    os.makedirs(tex_dir, exist_ok=True)
    rig = rig_face(arm, body, eyes, figure, tex_dir)
    rep = rig["report"]
    log("REPORT " + json.dumps(rep))
    if keep_blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(keep_blend))
    for o in bpy.context.view_layer.objects:
        o.select_set(o.type in ("MESH", "ARMATURE"))
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=os.path.abspath(dst), export_format="GLB", use_selection=True,
                              export_morph=True, export_morph_normal=True, export_morph_tangent=False,
                              export_try_sparse_sk=False, export_skins=True, export_animations=False,
                              export_apply=False, export_yup=True)
    zero_still_normals(os.path.abspath(dst))
    if report_path:
        with open(report_path, "w") as fh:
            json.dump(rep, fh, indent=1)


if __name__ == "__main__":
    main()
