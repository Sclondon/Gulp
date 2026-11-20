"""A first paint for a figure's head: the views of its head sheet projected onto the model's own UV layout.

    blender -b --factory-startup --python tools/figed/paint_project.py -- <spec.json> <sheet.json> <out.png> [shots.png] [--front]

For every texel of the head's skin the script finds the point of the (posed, squared) model it belongs to and which
way that skin faces, looks that point up in each view of the sheet (placed as head_overlay.py places them: scaled
crown to chin, noses together), and mixes the views by how squarely each sees the skin. Texels no view sees, and the
body below the neck, get the sheet's average skin colour. Nothing is hand painted and the drawing's own light and
shade is NOT taken out yet: it is a first try to look at. With `shots.png` the painted model is drawn from the
sheet's five angles, flat lit.
"""
import json
import math
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figed  # noqa: E402
import figed_blender as fb  # noqa: E402
import figed_fit  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
SIZE = 2048
base = figed.Base()
fig = figed.Figure(base, figed.load_spec(argv[0]))
with open(argv[1]) as f:
    sheet = json.load(f)

# the model as the sheet shows it: posed, the ears standing where they were set, the head squared
P, H, T = fig.to_blender()
for _side, (ear, piece) in getattr(fig, "ear_pieces", {}).items():
    P = P.copy()
    P[ear] = piece
turns = figed_fit.full_pose(fig.pose, base.bones, H, T)
P = figed.pose_points(fig, P, H, turns, T)[0]
turn, pivot = figed_fit.square_head(P, base)
P = (P - pivot).dot(turn.T) + pivot
N = fig._normals(P)
body = base.indices("body")
head = body[base.weights[body, base.bones.index("head")] > 0.6]
if ((P[head] - P[head].mean(axis=0)) * N[head]).sum() < 0:      # normals out of the skin
    N = -N
chin = P[figed_fit.mark_vertices(base)["chin"]]
mid = head[np.abs(P[head][:, 0] - np.median(P[head][:, 0])) < 0.012]
nose = P[mid[np.argmin(P[mid][:, 1])]]
crown = P[head[np.argmax(P[head][:, 2])]]
high = crown[2] - chin[2]

# the sheet's views
art = figed_fit.load_image(sheet["picture"])[:, :, :3]
k = art.shape[1] / float(sheet["box_width"])
DIRS = {"face": (0, 1, 0), "face_side_r": (1, 0, 0), "face_side": (-1, 0, 0), "face_back": (0, -1, 0)}
views = []
for v in sheet["views"]:
    if "turn" in v:
        t = math.radians(v["turn"])
        d = np.array([math.sin(t), math.cos(t), 0.0])
    else:
        d = np.array(DIRS[v["view"]], dtype=float)
    right = np.cross(d, [0, 0, 1.0])
    right /= np.linalg.norm(right)
    up = np.cross(right, d)
    box = [int(round(c * k)) for c in v["box"]]
    mask = figed_fit.shrink(figed_fit.cut_out(art, box, 0.07), 4)     # in from the drawn outline: no dark lines
    px = (v["chin"] - v["crown"]) * k / high                 # sheet pixels a metre
    if "nose" in v:
        anchor, at = nose, (v["nose"][0] * k, v["nose"][1] * k)
    else:
        anchor, at = crown, (v["centre"] * k, v["crown"] * k)
    # each row's figure: where it starts and ends, so skin just outside a view's outline (the side of the head, seen
    # edge on from front and back) takes the colour of the outline's edge and is not left bare
    rows = mask.any(axis=1)
    lo = np.where(rows, mask.argmax(axis=1), 0)
    hi = np.where(rows, mask.shape[1] - 1 - mask[:, ::-1].argmax(axis=1), -1)
    views.append((d, right, up, box, (mask, rows, lo, hi), px, anchor, at, v["view"]))
skin = np.median(art[views[0][4][0].nonzero()[0] + views[0][3][1], views[0][4][0].nonzero()[1] + views[0][3][0]], axis=0)
# The user, 2026-11-20: "just project the fotnad back views, and the ears shouold come from the side view". The
# three-quarter views are not used: where two views disagree the paint doubled (mouth, ears).
by_name = {v[8]: v for v in views}
FRONT, BACK, SIDE = by_name["face"], by_name["face_back"], by_name["face_side_r"]
ear_of = np.zeros(len(P), dtype=int)                          # 1 = an ear on his left (+x), 2 = on his right
for side, (ear, _root, flap) in fig._ear_masks().items():
    ear_of[ear] = 1 if side == "l" else 2
print("skin colour", skin.round(3), "views", len(views))

# texels of the head's faces: where each is on the model, and which way it faces
tex = np.zeros((SIZE, SIZE, 3))
wsum = np.zeros((SIZE, SIZE))
cover = np.zeros((SIZE, SIZE), dtype=bool)
low = chin[2] - 0.14                                         # paint down to the base of the neck
uvs = np.array(base.uvs)
done = 0
for group, vi, ti in base.faces:
    if group != "body" or min(ti) < 0:
        continue
    for a in range(1, len(vi) - 1):
        tri = [vi[0], vi[a], vi[a + 1]]
        uv = uvs[[ti[0], ti[a], ti[a + 1]]] * SIZE
        x0, x1 = int(max(0, math.floor(uv[:, 0].min()))), int(min(SIZE - 1, math.ceil(uv[:, 0].max())))
        y0, y1 = int(max(0, math.floor(uv[:, 1].min()))), int(min(SIZE - 1, math.ceil(uv[:, 1].max())))
        if x1 < x0 or y1 < y0:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        e0, e1 = uv[1] - uv[0], uv[2] - uv[0]
        den = e0[0] * e1[1] - e0[1] * e1[0]
        if abs(den) < 1e-9:
            continue
        b1 = ((gx - uv[0, 0]) * e1[1] - (gy - uv[0, 1]) * e1[0]) / den
        b2 = ((gy - uv[0, 1]) * e0[0] - (gx - uv[0, 0]) * e0[1]) / den
        b0 = 1 - b1 - b2
        inside = (b0 >= -0.02) & (b1 >= -0.02) & (b2 >= -0.02)
        if not inside.any():
            continue
        ys, xs = gy[inside].astype(int), gx[inside].astype(int)
        cover[ys, xs] = True
        if P[tri][:, 2].max() < low:
            continue
        w3 = np.stack([b0[inside], b1[inside], b2[inside]], axis=1)
        pos = w3.dot(P[tri])
        nrm = w3.dot(N[tri])
        nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)
        fade = np.clip((pos[:, 2] - low) / 0.05, 0, 1)        # the paint fades out down the neck
        which = ear_of[tri]
        if which.min() > 0:                                   # an ear: from the side view (his left ear mirrored)
            if which[0] == 1:
                pos = pos * np.array([-1.0, 1, 1])
            use = [(SIDE, np.ones(len(pos)))]
        else:                                                 # the head: front or back, a narrow blend at the side
            t = np.clip((0.12 - nrm[:, 1]) / 0.24, 0, 1)
            front = t * t * (3 - 2 * t)
            # --front (the user, 2026-11-20: "just use his front facing one for the head texture at first"): the front
            # view alone; skin that faces away from it is left the plain skin colour, not painted through
            use = [(FRONT, front)] if "--front" in argv else [(FRONT, front), (BACK, 1 - front)]
        for (d, right, up, box, (mask, rows, lo, hi), px, anchor, at, _name), share in use:
            sx = at[0] + (pos - anchor).dot(right) * px
            sy = at[1] - (pos - anchor).dot(up) * px
            ix, iy = np.round(sx).astype(int), np.round(sy).astype(int)
            ry = np.clip(iy - box[1], 0, mask.shape[0] - 1)
            on = rows[ry] & (iy >= box[1]) & (iy < box[3])
            ix = np.clip(ix - box[0], lo[ry], np.maximum(hi[ry], lo[ry])) + box[0]     # pulled in to the figure
            wgt = share * on * fade
            col = art[np.clip(iy, 0, art.shape[0] - 1), np.clip(ix, 0, art.shape[1] - 1)]
            tex[ys, xs] += col * wgt[:, None]
            wsum[ys, xs] += wgt
        done += 1
print("triangles painted", done)
seen = np.clip(wsum / 0.25, 0, 1)[:, :, None]                 # weakly seen texels lean on the plain skin colour
out = np.where(wsum[:, :, None] > 1e-6, tex / np.maximum(wsum, 1e-6)[:, :, None], skin) * seen + skin * (1 - seen)
out[~cover] = skin
img = bpy.data.images.new("skin", SIZE, SIZE, alpha=False)
rgba = np.ones((SIZE, SIZE, 4), dtype=np.float32)
rgba[:, :, :3] = out                                          # row 0 is v = 0: Blender's own order
img.pixels.foreach_set(rgba.ravel())
img.filepath_raw = os.path.abspath(argv[2])
img.file_format = "PNG"
img.save()
print("painted", argv[2], "texels seen", int((wsum > 1e-6).sum()))

if len(argv) > 3 and not argv[3].startswith("--"):            # the painted model from the sheet's angles
    fb.reset()
    img = bpy.data.images.load(os.path.abspath(argv[2]))
    objs, _arm = fb.build(fig, rig=False, posed=True)
    mat = bpy.data.materials.new("skin")
    mat.use_nodes = True
    node = mat.node_tree.nodes.new("ShaderNodeTexImage")
    node.image = img
    mat.node_tree.nodes.active = node
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    mat.node_tree.links.new(node.outputs["Color"], bsdf.inputs["Base Color"])
    objs["body"].data.materials.append(mat)
    boxes = fb.view_boxes(fig)
    cam = fb._camera()
    Pp = figed.pose_points(fig, *fig.to_blender()[:2], turns, fig.to_blender()[2])[0]
    top, bottom = Pp[head][:, 2].max(), Pp[figed_fit.mark_vertices(base)["chin"]][2]
    strips = []
    for v in sheet["views"]:
        centre, direction, _seen, _aspect = boxes[v["view"]][:4]
        if "turn" in v:
            t = math.radians(v["turn"])
            direction = (math.sin(t), math.cos(t), 0.0)
        centre = np.array(centre, dtype=float)
        centre[2] = (top + bottom) / 2 - 0.02
        seen_m = (top - bottom) * 1.75
        s = fb._scene((720, 900))
        s.display.shading.color_type = "TEXTURE"
        s.display.shading.light = "FLAT"
        s.display.shading.show_cavity = False
        fb._aim(cam, centre, direction, seen_m)
        cam.data.sensor_fit = "VERTICAL"
        cam.data.ortho_scale = seen_m
        s.render.filepath = os.path.join(os.path.dirname(os.path.abspath(argv[3])), "_paint_%s.png" % v["view"])
        bpy.ops.render.render(write_still=True)
        shot = bpy.data.images.load(s.render.filepath)
        strips.append(np.array(shot.pixels[:]).reshape(900, 720, 4))
    fb.save_pixels(np.concatenate(strips, axis=1), os.path.abspath(argv[3]))
    print("shots", argv[3])
