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
PULL = 10.0                                                   # body views: pixels a sample may be pulled in from outside
SIDE_FROM, SIDE_TO = 0.12, 0.6                                # how squarely skin must face a view: none .. full paint
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

def feather(mask, n=6):
    """A cut-out as 0..1, falling off over n pixels inside its edge: paint fades out towards the outline."""
    m = mask.astype(float)
    cur = mask
    for i in range(n):
        cur = figed_fit.shrink(cur, 1)
        m += cur
    return m / (n + 1.0)


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
    if "nose" in v:                                          # across by the nose, up and down by the crown: reshaping
        anchor = np.array([nose[0], nose[1], crown[2]])      # the nose must not slide the whole paint up or down
        at = (v["nose"][0] * k, v["crown"] * k)
    else:
        anchor, at = crown, (v["centre"] * k, v["crown"] * k)
    # each row's figure: where it starts and ends, so skin just outside a view's outline (the side of the head, seen
    # edge on from front and back) takes the colour of the outline's edge and is not left bare
    rows = mask.any(axis=1)
    lo = np.where(rows, mask.argmax(axis=1), 0)
    hi = np.where(rows, mask.shape[1] - 1 - mask[:, ::-1].argmax(axis=1), -1)
    soft = feather(mask)
    views.append((d, right, up, box, (mask, soft, lo, hi), px, anchor, at, v["view"]))
skin = np.median(art[views[0][4][0].nonzero()[0] + views[0][3][1], views[0][4][0].nonzero()[1] + views[0][3][0]], axis=0)
# The user, 2026-11-20: "just project the fotnad back views, and the ears shouold come from the side view". The
# three-quarter views are not used: where two views disagree the paint doubled (mouth, ears).
by_name = {v[8]: v for v in views}
FRONT, BACK, SIDE = by_name["face"], by_name["face_back"], by_name["face_side_r"]
ear_of = np.zeros(len(P), dtype=int)                          # 1 = an ear on his left (+x), 2 = on his right
for side, (ear, _root, flap) in fig._ear_masks().items():
    ear_of[ear] = 1 if side == "l" else 2
print("skin colour", skin.round(3), "views", len(views))

# --body <fit job>: the body below the chin from the job's "front" and "back" views of the body sheet, the model
# standing as the job stands it (the fit's own mapping from model to drawing: View.project)
ORDER = {"front": 0, "back": 1, "armless_side": 2}
body_views = []
if "--body" in argv:
    with open(argv[argv.index("--body") + 1]) as f:
        job = json.load(f)
    J = figed_fit.Job(job)
    J.outlines()                                              # sets each view's mapping
    figb = J.figure()
    P0, H0, T0 = figb.to_blender()
    common = {kk: vv for kk, vv in J.spec["pose"].items() if "@" not in kk}
    Pb = figed.pose_points(figb, P0, H0, figed_fit.full_pose(common, base.bones, H0, T0), T0)[0]
    Nb = figb._normals(Pb)
    if ((Pb[head] - Pb[head].mean(axis=0)) * Nb[head]).sum() < 0:
        Nb = -Nb
    chin_b = Pb[figed_fit.mark_vertices(base)["chin"]][2]
    for v in J.views:
        if v.spec["name"] not in ORDER:
            continue
        pic = figed_fit.load_image(v.spec["picture"])[:, :, :3]
        kb = pic.shape[1] / float(v.spec.get("box_width", pic.shape[1]))
        bx = [int(round(c * kb)) for c in v.spec["box"]]
        n = 1
        want = v.spec.get("tall")
        if want and (bx[3] - bx[1]) > want * 1.5:
            n = int((bx[3] - bx[1]) // want)
        origin = (bx[0] // n, bx[1] // n)
        m = figed_fit.shrink(v.mask, 2)
        softb = m
        rows = m.any(axis=1)
        lo = np.where(rows, m.argmax(axis=1), 0)
        hi = np.where(rows, m.shape[1] - 1 - m[:, ::-1].argmax(axis=1), -1)
        body_views.append((v, pic, n, origin, softb, lo, hi))
    body_views.sort(key=lambda b: ORDER[b[0].spec["name"]])
    print("body views", [b[0].spec["name"] for b in body_views])
    arm_bones = [i for i, b in enumerate(base.bones) if b.split("_")[0] in (
        "upperarm", "lowerarm", "hand", "thumb", "index", "middle", "ring", "pinky")]
    armw = base.weights[:, arm_bones].sum(axis=1)
texb = np.zeros((SIZE, SIZE, 3))
wb = np.zeros((SIZE, SIZE))

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
        w3 = np.stack([b0[inside], b1[inside], b2[inside]], axis=1)
        if body_views and Pb[tri][:, 2].min() < chin_b + 0.03:
            posb = w3.dot(Pb[tri])
            nb = w3.dot(Nb[tri])
            nb /= np.maximum(np.linalg.norm(nb, axis=1, keepdims=True), 1e-9)
            t = np.clip((0.3 - nb[:, 1]) / 0.6, 0, 1)
            fr = t * t * (3 - 2 * t)                          # front and back meet each other round the side
            below = np.clip((chin_b + 0.03 - posb[:, 2]) / 0.05, 0, 1)
            # skin that faces sideways on the trunk, neck and legs: the ARMLESS sheet's side view (the main sheet's
            # has the arm hanging over the flank). Arms keep front and back only.
            sw = np.zeros(len(fr))
            if len(body_views) > 2 and armw[tri].mean() < 0.5:
                q = np.clip((np.abs(nb[:, 0]) - 0.45) / 0.4, 0, 1)
                sw = q * q * (3 - 2 * q)
            for (v, pic, n, origin, rows, lo, hi), share in zip(body_views, (fr * (1 - sw), (1 - fr) * (1 - sw), sw)):
                px_, py_ = v.project(posb.T)
                iy0, ix0 = np.round(py_).astype(int), np.round(px_).astype(int)
                iy = np.clip(iy0, 0, rows.shape[0] - 1)
                has = hi[iy] >= lo[iy]
                ix = np.clip(ix0, lo[iy], np.maximum(hi[iy], lo[iy]))     # pulled in to the figure on its row ...
                pulled = np.abs(ix - ix0)
                on = has * (iy0 == iy) * np.clip(1.5 - pulled / PULL, 0, 1)   # ... a little way only (no long streaks)
                fx = np.clip((ix + origin[0]) * n + n // 2, 0, pic.shape[1] - 1)
                fy = np.clip((iy + origin[1]) * n + n // 2, 0, pic.shape[0] - 1)
                wgt = share * on * below
                texb[ys, xs] += pic[fy, fx] * wgt[:, None]
                wb[ys, xs] += wgt
        if P[tri][:, 2].max() < low:
            continue
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
            # The user, 2026-11-20: "the back projection looked good, just smoothly blend them with the skin tone
            # together". Each view paints the skin that faces it; as the skin turns side on, the paint fades
            # smoothly into the plain skin tone (no edge colour dragged round the side).
            g = np.clip((np.abs(nrm[:, 1]) - SIDE_FROM) / (SIDE_TO - SIDE_FROM), 0, 1)
            g = g * g * (3 - 2 * g)
            front, back = g * (nrm[:, 1] < 0), g * (nrm[:, 1] > 0)
            # --front (the user, 2026-11-20: "just use his front facing one for the head texture at first"): the front
            # view alone; skin that faces away from it is left the plain skin colour, not painted through
            use = [(FRONT, front)] if "--front" in argv else [(FRONT, front), (BACK, back)]
        for (d, right, up, box, (mask, soft, lo, hi), px, anchor, at, _name), share in use:
            sx = at[0] + (pos - anchor).dot(right) * px
            sy = at[1] - (pos - anchor).dot(up) * px
            ix, iy = np.round(sx).astype(int), np.round(sy).astype(int)
            ry = np.clip(iy - box[1], 0, mask.shape[0] - 1)
            rx = np.clip(ix - box[0], 0, mask.shape[1] - 1)
            on = soft[ry, rx] * ((iy >= box[1]) & (iy < box[3]) & (ix >= box[0]) & (ix < box[2]))
            # (off the drawn figure the paint fades to the skin tone: pulling the edge colour in made streaks)
            wgt = share * on * fade
            col = art[np.clip(iy, 0, art.shape[0] - 1), np.clip(ix, 0, art.shape[1] - 1)]
            tex[ys, xs] += col * wgt[:, None]
            wsum[ys, xs] += wgt
        done += 1
print("triangles painted", done)
seen = np.clip(wsum, 0, 1)[:, :, None]                        # the rest of each texel is the plain skin tone
under = np.where(wb[:, :, None] > 1e-6, texb / np.maximum(wb, 1e-6)[:, :, None], skin)          # the body, or plain skin
shown = np.clip(wb, 0, 1)[:, :, None]
under = under * shown + skin * (1 - shown)
out = np.where(wsum[:, :, None] > 1e-6, tex / np.maximum(wsum, 1e-6)[:, :, None], skin) * seen + under * (1 - seen)
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
    if body_views:                                            # and the whole figure
        strips = []
        for name in ("front", "quarter", "side", "back"):
            centre, direction, seen_m, aspect = boxes[name][:4]
            wpx = int(900 * aspect) // 2 * 2
            s = fb._scene((wpx, 900))
            s.display.shading.color_type = "TEXTURE"
            s.display.shading.light = "FLAT"
            s.display.shading.show_cavity = False
            fb._aim(cam, centre, direction, seen_m)
            cam.data.sensor_fit = "VERTICAL"
            cam.data.ortho_scale = seen_m
            s.render.filepath = os.path.join(os.path.dirname(os.path.abspath(argv[3])), "_paint_body_%s.png" % name)
            bpy.ops.render.render(write_still=True)
            shot = bpy.data.images.load(s.render.filepath)
            strips.append(np.array(shot.pixels[:]).reshape(900, wpx, 4))
        fb.save_pixels(np.concatenate(strips, axis=1), os.path.abspath(argv[3])[:-4] + "_body.png")
