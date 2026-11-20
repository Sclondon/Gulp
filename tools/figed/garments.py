"""Clothes for a figure: each garment is a piece of its own, cut from the body's own surface and pushed out a little,
on the same skeleton and the same UVs, with a picture of its own.

    blender -b --factory-startup --python tools/figed/garments.py -- <spec.json> <outfit.json> <out.png> --wear a,b

A garment is the body's faces where a rule f(point) > 0 (hems and necklines are cut exactly along f = 0: edges are
split where they cross and the faces cut along the line), offset along the normals. Rules are written in the
figure's REST pose from its joints, so they follow the sliders. `make()` gives Blender objects (posed for pictures,
or at rest with weights for an export). The outfit file names the drawing and where each garment is in it; cloth
colours are carried over box to box from the drawing's front view (the back takes the front's, seen through).
"""
import json
import math
import os
import sys

import bpy
import bmesh
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figed  # noqa: E402
import figed_fit  # noqa: E402

SIZE = 1024
ARM = ("lowerarm", "hand", "thumb", "index", "middle", "ring", "pinky")
LEG = ("pelvis", "thigh", "calf", "foot", "ball", "spine_01")


def _w(base, names):
    idx = [i for i, b in enumerate(base.bones) if b.split("_")[0] in names or b in names]
    return base.weights[:, idx].sum(axis=1)


def rules(fig, P, H, skin_px=None):
    """name -> (f per point, which points may belong, offset per point in metres, colour for plain renders)."""
    base = fig.base
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    arm, leg, head = _w(base, ARM), _w(base, LEG), _w(base, ("head",))
    up = _w(base, ("upperarm",))
    navel = P[figed_fit.mark_vertices(base)["navel"]]
    sx, zs = abs(H["upperarm_l"][0]), H["upperarm_l"][2]
    zn, yn = H["neck_01"][2], H["neck_01"][1]
    waist = navel[2] - 0.025
    cuff = H["foot_l"][2] + 0.075
    knee = H["calf_l"][2]
    out = {}
    lower = (arm < 0.3) & (up < 0.3) & (leg > 0.5)
    baggy = 0.011 + 0.012 * np.clip((knee + 0.1 - z) / 0.25, 0, 1)
    baggy = baggy * np.clip(np.abs(x) / 0.035, 0.4, 1)
    out["trousers"] = (np.minimum(waist - z, z - cuff), lower, baggy, (0.30, 0.29, 0.22))
    out["cuffs"] = (np.minimum(cuff + 0.05 - z, z - cuff), lower, baggy + 0.007, (0.27, 0.26, 0.20))
    out["waistband"] = (np.minimum(waist - z, z - (waist - 0.035)), lower, baggy + 0.004, (0.25, 0.24, 0.19))
    # the vest: scoop neck (deeper in front), armholes, tucked into the trousers
    depth = np.where(y < yn, 0.14, 0.08)
    neck = (x / 0.088) ** 2 + ((z - (zn + 0.03)) / depth) ** 2 - 1
    hole = ((np.abs(x) - (sx + 0.035)) / 0.085) ** 2 + ((z - zs) / 0.15) ** 2 - 1
    torso = (arm < 0.3) & (up < 0.75) & (head < 0.3) & (z > waist - 0.1) & (_w(base, ("thigh", "calf")) < 0.3)
    f = np.minimum(np.minimum(neck, hole) * 0.05, np.minimum(z - (waist - 0.06), zn + 0.06 - z))
    out["tank"] = (f, torso, np.full(len(P), 0.006), (0.88, 0.86, 0.80))
    if skin_px is not None:                              # the drawers: where the skin picture is painted as cloth
        cloth = skin_px & lower
        if cloth.sum() > 50:
            top, hem = np.percentile(z[cloth], 98), np.percentile(z[cloth], 2)
            out["drawers"] = (np.minimum(top - z, z - hem), lower, np.full(len(P), 0.004), (0.90, 0.87, 0.78))
    return out


def cut(fig, P, posed, f, may, offset, name):
    """The garment as a Blender mesh: the body's faces where f > 0, cut along f = 0, pushed out."""
    base = fig.base
    bm = bmesh.new()
    lf = bm.verts.layers.float.new("f")
    lp = bm.verts.layers.float_vector.new("posed")
    lo = bm.verts.layers.float.new("off")
    ld = bm.verts.layers.deform.verify()
    uv = bm.loops.layers.uv.new("UVMap")
    verts = {}
    for group, vi, ti in base.faces:
        if group != "body" or min(ti) < 0 or not all(may[v] for v in vi) or max(f[v] for v in vi) <= 0:
            continue
        vs = []
        for v in vi:
            if v not in verts:
                bv = bm.verts.new(tuple(P[v]))
                bv[lf], bv[lp], bv[lo] = float(f[v]), tuple(posed[v]), float(offset[v])
                for i in np.nonzero(base.weights[v] > 1e-4)[0]:
                    bv[ld][int(i)] = float(base.weights[v, i])
                verts[v] = bv
            vs.append(verts[v])
        try:
            face = bm.faces.new(vs)
        except ValueError:
            continue
        for loop, t in zip(face.loops, ti):
            loop[uv].uv = tuple(base.uvs[t])
        face.smooth = True
    new = []
    for e in list(bm.edges):                              # split every edge that crosses f = 0, at the crossing
        a, b = e.verts
        fa, fb = a[lf], b[lf]
        if fa * fb < 0:
            _e, nv = bmesh.utils.edge_split(e, a, fa / (fa - fb))
            nv[lf] = 0.0
            new.append(nv)
    if new:
        bmesh.ops.connect_verts(bm, verts=new, check_degenerate=True)
    gone = [face for face in bm.faces if sum(v[lf] for v in face.verts) / len(face.verts) < 1e-9]
    bmesh.ops.delete(bm, geom=gone, context="FACES")
    bm.normal_update()
    for v in bm.verts:
        push = v.normal * v[lo]
        v.co += push
        v[lp] = tuple(np.array(v[lp]) + np.array(push))
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    return mesh


def make(fig, wear, posed=True, arm=None, skin_path=None):
    base = fig.base
    P, H, T = fig.to_blender()
    Pp = figed_fit.pose_points(fig, P, H, figed_fit.full_pose(fig.pose, base.bones, H, T), T)[0] if posed else P
    skin_px = None
    if "drawers" in wear and skin_path:
        px = figed_fit.load_image(skin_path)[::-1, :, :3]             # row 0 = v 0
        cloth = np.zeros(len(P), dtype=bool)
        uvs = np.array(base.uvs)
        for group, vi, ti in base.faces:
            if group == "body" and min(ti) >= 0:
                for v, t in zip(vi, ti):
                    c = px[min(px.shape[0] - 1, int(uvs[t][1] * px.shape[0])), min(px.shape[1] - 1, int(uvs[t][0] * px.shape[1]))]
                    cloth[v] = c.min() > 0.6 and (c[0] - c[2]) < 0.22
        skin_px = cloth
    R = rules(fig, P, H, skin_px)
    parts = []
    for name in wear:
        for piece in ([name] if name != "trousers" else ["trousers", "cuffs", "waistband"]):
            if piece not in R:
                print("no such garment here:", piece)
                continue
            f, may, off, col = R[piece]
            mesh = cut(fig, P, Pp, f, may, off, piece)
            if posed:
                for v, d in zip(mesh.vertices, mesh.attributes["posed"].data):
                    v.co = d.vector
            obj = bpy.data.objects.new(piece, mesh)
            bpy.context.scene.collection.objects.link(obj)
            for b in base.bones:
                obj.vertex_groups.new(name=b)
            if arm is not None:
                obj.parent = arm
                obj.modifiers.new("rig", "ARMATURE").object = arm
            obj["plain"] = col
            parts.append((piece, name, obj))
            print("garment %-10s %5d faces" % (piece, len(mesh.polygons)))
    return parts, R, P


def paint(fig, outfit, name, R, P, path):
    """A garment's picture: the drawing's cloth, box to box from the front view, onto the body's UVs."""
    base = fig.base
    art = figed_fit.load_image(outfit["picture"])[:, :, :3]
    x0, y0, x1, y1 = outfit[name]["box"]
    sub = art[y0:y1, x0:x1]
    if outfit[name]["cloth"] == "pale":
        cloth = sub.min(axis=2) > 0.55
    else:
        cloth = sub.max(axis=2) < 0.52
    cloth = figed_fit.shrink(cloth, 1)
    # the cloth's colours carried over everything else in the box (skin, paper), so every lookup finds cloth
    img, known = sub.copy(), cloth.copy()
    for _ in range(max(sub.shape[:2])):
        if known.all():
            break
        tot, cnt = np.zeros_like(img), np.zeros(known.shape)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            s_ = (slice(max(0, -dy), img.shape[0] - max(0, dy)), slice(max(0, -dx), img.shape[1] - max(0, dx)))
            d_ = (slice(max(0, dy), img.shape[0] - max(0, -dy)), slice(max(0, dx), img.shape[1] - max(0, -dx)))
            tot[d_] += img[s_] * known[s_][:, :, None]
            cnt[d_] += known[s_]
        fresh = (~known) & (cnt > 0)
        img[fresh] = tot[fresh] / cnt[fresh][:, None]
        known |= fresh
    f, may, _off, _col = R[name]
    keep = may & (f > 0)
    bx0, bx1, bz0, bz1 = P[keep][:, 0].min(), P[keep][:, 0].max(), P[keep][:, 2].min(), P[keep][:, 2].max()
    tex = np.zeros((SIZE, SIZE, 3))
    tex[:] = img[known].mean(axis=0)
    uvs = np.array(base.uvs)
    for group, vi, ti in base.faces:
        if group != "body" or min(ti) < 0 or not all(may[v] for v in vi) or max(f[v] for v in vi) <= -0.03:
            continue
        for a in range(1, len(vi) - 1):
            tri = [vi[0], vi[a], vi[a + 1]]
            uv = uvs[[ti[0], ti[a], ti[a + 1]]] * SIZE
            u0, u1 = int(max(0, math.floor(uv[:, 0].min()))), int(min(SIZE - 1, math.ceil(uv[:, 0].max())))
            v0, v1 = int(max(0, math.floor(uv[:, 1].min()))), int(min(SIZE - 1, math.ceil(uv[:, 1].max())))
            if u1 < u0 or v1 < v0:
                continue
            gx, gy = np.meshgrid(np.arange(u0, u1 + 1) + 0.5, np.arange(v0, v1 + 1) + 0.5)
            e0, e1 = uv[1] - uv[0], uv[2] - uv[0]
            den = e0[0] * e1[1] - e0[1] * e1[0]
            if abs(den) < 1e-9:
                continue
            b1 = ((gx - uv[0, 0]) * e1[1] - (gy - uv[0, 1]) * e1[0]) / den
            b2 = ((gy - uv[0, 1]) * e0[0] - (gx - uv[0, 0]) * e0[1]) / den
            b0 = 1 - b1 - b2
            ins = (b0 >= -0.05) & (b1 >= -0.05) & (b2 >= -0.05)
            if not ins.any():
                continue
            pos = np.stack([b0[ins], b1[ins], b2[ins]], axis=1).dot(P[tri])
            ix = np.clip(((pos[:, 0] - bx0) / (bx1 - bx0) * (img.shape[1] - 1)).astype(int), 0, img.shape[1] - 1)
            iy = np.clip(((bz1 - pos[:, 2]) / (bz1 - bz0) * (img.shape[0] - 1)).astype(int), 0, img.shape[0] - 1)
            tex[gy[ins].astype(int), gx[ins].astype(int)] = img[iy, ix]
    im = bpy.data.images.new(name, SIZE, SIZE, alpha=False)
    rgba = np.ones((SIZE, SIZE, 4), dtype=np.float32)
    rgba[:, :, :3] = tex
    im.pixels.foreach_set(rgba.ravel())
    im.filepath_raw = os.path.abspath(path)
    im.file_format = "PNG"
    im.save()
    print("painted", path)


def material(name, path):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    node = mat.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = bpy.data.images.load(os.path.abspath(path), check_existing=True)
    mat.node_tree.nodes.active = node
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    mat.node_tree.links.new(node.outputs["Color"], bsdf.inputs["Base Color"])
    return mat


if __name__ == "__main__":
    import figed_blender as fb  # noqa: E402

    argv = sys.argv[sys.argv.index("--") + 1:]
    spec_path, outfit_path, out = argv[:3]
    wear = argv[argv.index("--wear") + 1].split(",")
    fig = figed.Figure(figed.Base(), figed.load_spec(spec_path))
    with open(outfit_path) as fh:
        outfit = json.load(fh)
    stem = os.path.splitext(spec_path)[0]
    fb.reset()
    objs, _arm = fb.build(fig, rig=False, posed=True)
    objs["body"].data.materials.append(material("skin", stem + "_skin.png"))
    if "eyes" in objs and os.path.exists(stem + "_eyes.png"):
        objs["eyes"].data.materials.append(material("eyes", stem + "_eyes.png"))
    parts, R, P = make(fig, wear, posed=True, skin_path=stem + "_skin.png")
    done = {}
    for piece, name, obj in parts:
        if name == "drawers":
            obj.data.materials.append(material("skin", stem + "_skin.png"))
            continue
        if name not in done:
            done[name] = "%s_%s.png" % (stem, name)
            paint(fig, outfit, name, R, P, done[name])
        obj.data.materials.append(material(name, done[name]))
    boxes = fb.view_boxes(fig)
    cam = fb._camera()
    strips = []
    for view in ("front", "quarter", "side", "back"):
        centre, direction, seen, aspect = boxes[view][:4]
        w = int(900 * aspect) // 2 * 2
        s = fb._scene((w, 900))
        s.display.shading.color_type = "TEXTURE"
        s.display.shading.light = "FLAT"
        s.display.shading.show_cavity = False
        fb._aim(cam, centre, direction, seen)
        cam.data.sensor_fit = "VERTICAL"
        cam.data.ortho_scale = seen
        s.render.filepath = os.path.join(os.path.dirname(os.path.abspath(out)), "_wear_%s.png" % view)
        bpy.ops.render.render(write_still=True)
        shot = bpy.data.images.load(s.render.filepath)
        strips.append(np.array(shot.pixels[:]).reshape(900, w, 4))
    fb.save_pixels(np.concatenate(strips, axis=1), os.path.abspath(out))
    print("shots", out)
