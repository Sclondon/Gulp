"""The model's head laid over a head sheet, view by view: scaled so crown-to-chin matches the drawing, moved so
the nose tips sit on the same point, drawn half see-through over the art (the back view lines up by the crown).

    blender -b --factory-startup --python tools/figed/head_overlay.py -- <spec.json> <sheet.json> <out.png> [--posed]

The sheet: {"picture", "box_width", "views": [{"view": a figed_blender view name, "box": [x0, y0, x1, y1],
"nose": [x, y] (the nose's tip in the drawing; none for the back), "crown": y, "chin": y, "turn": degrees the
head is turned (+ = facing the picture's right), for a three-quarter view}]}.
Rows of the picture: the art, the overlay, the model alone.
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
base = figed.Base()
spec = figed.load_spec(argv[0])
with open(argv[1]) as f:
    sheet = json.load(f)
out = argv[2]
posed = "--posed" in argv
UP = 4                                                  # the art is drawn this many times its own size

fig = figed.Figure(base, spec)
P, H, T = fig.to_blender()
if posed and fig.pose:
    P, _ = figed.pose_points(fig, P, H, figed_fit.full_pose(fig.pose, base.bones, H, T), T)
turn, pivot = figed_fit.square_head(P, base)            # the head set square: full face, and exactly side on
if "--tilt" in argv:                                    # and nodded as the profile fit found the drawing to be
    turn = figed_fit.about(np.array([1.0, 0, 0]), float(argv[argv.index("--tilt") + 1])).dot(turn)
P = (P - pivot).dot(turn.T) + pivot
body = base.indices("body")
head = body[base.weights[body, base.bones.index("head")] > 0.6]
mid = head[np.abs(P[head][:, 0] - np.median(P[head][:, 0])) < 0.012]
nose = P[mid[np.argmin(P[mid][:, 1])]]                  # the point of the face furthest forward: the nose's tip
crown = P[head[np.argmax(P[head][:, 2])]]
chin = P[figed_fit.mark_vertices(base)["chin"]]

fb.reset()
objs, _arm = fb.build(fig, rig=False, posed=posed)
from mathutils import Matrix  # noqa: E402
M = Matrix.Translation(pivot) @ Matrix(turn.tolist()).to_4x4() @ Matrix.Translation(-pivot)
for o in objs.values():
    o.matrix_world = M
fb.paint_plain(objs)
boxes = fb.view_boxes(fig)
cam = fb._camera()
art = figed_fit.load_image(sheet["picture"])            # rows top to bottom, 0..1
k = art.shape[1] / float(sheet["box_width"])
RES = 900
tiles = []
for v in sheet["views"]:
    centre, direction, seen, aspect = boxes[v["view"]][:4]
    if "turn" in v:                                      # the head turned this many degrees (+ = facing the picture's
        t = math.radians(v["turn"])                      # right), read off the drawing: sheets are seldom at 45
        direction = (math.sin(t), math.cos(t), 0.0)
    centre = np.array(centre, dtype=float)
    centre[2] = (crown[2] + chin[2]) / 2                # look at the middle of the head
    seen = (crown[2] - chin[2]) * 1.9
    w = int(RES * aspect) // 2 * 2
    s = fb._scene((w, RES))
    s.render.film_transparent = True
    fb._aim(cam, centre, direction, seen)
    cam.data.sensor_fit = "VERTICAL"
    cam.data.ortho_scale = seen
    path = os.path.join(os.path.dirname(out), "_overlay_%s.png" % v["view"])
    s.render.filepath = path
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(path)
    shot = np.array(img.pixels[:]).reshape(RES, w, 4)[::-1]          # rows top to bottom
    bpy.data.images.remove(img)

    d = np.array(direction, dtype=float)
    d /= np.linalg.norm(d)
    right = np.cross(d, [0, 0, 1.0])
    right /= np.linalg.norm(right)
    up = np.cross(right, d)

    def pixel(p):                                        # a point of the model in the render's pixels
        r = np.asarray(p) - centre
        return w / 2 + r.dot(right) / seen * RES, RES / 2 - r.dot(up) / seen * RES

    x0, y0, x1, y1 = [int(round(c * k)) for c in v["box"]]
    tile = art[y0:y1, x0:x1, :3]
    tile = np.repeat(np.repeat(tile, UP, axis=0), UP, axis=1)
    th, tw = tile.shape[:2]
    scale = (v["chin"] - v["crown"]) * k * UP / (pixel(chin)[1] - pixel(crown)[1])     # tile pixels per render pixel
    if "nose" in v:
        ax, ay = (v["nose"][0] * k - x0) * UP, (v["nose"][1] * k - y0) * UP
        mx, my = pixel(nose)
    else:                                                # the back of the head: by the crown, centred
        ax, ay = (v["centre"] * k - x0) * UP, (v["crown"] * k - y0) * UP
        mx, my = pixel(crown)
    yy, xx = np.mgrid[0:th, 0:tw]
    sx = np.round((xx - ax) / scale + mx).astype(int)
    sy = np.round((yy - ay) / scale + my).astype(int)
    ok = (sx >= 0) & (sx < w) & (sy >= 0) & (sy < RES)
    model = np.zeros((th, tw, 4), dtype=np.float32)
    model[ok] = shot[sy[ok], sx[ok]]
    a = model[:, :, 3:4]
    over = tile * (1 - a * 0.55) + model[:, :, :3] * a * 0.55
    alone = np.ones_like(tile) * 0.86 * (1 - a) + model[:, :, :3] * a
    for pic in (over, alone):                            # a small cross where the nose tips were put together
        if "nose" in v:
            cx, cy = int(ax), int(ay)
            pic[max(0, cy - 1):cy + 2, max(0, cx - 14):cx + 15] = (0.1, 0.8, 0.2)
            pic[max(0, cy - 14):cy + 15, max(0, cx - 1):cx + 2] = (0.1, 0.8, 0.2)
    tiles.append((tile, over, alone))

height = max(t[0].shape[0] for t in tiles)


def row(i):
    parts = []
    for t in tiles:
        p = np.ones((height, t[i].shape[1] + 12, 4), dtype=np.float32)
        p[:t[i].shape[0], :t[i].shape[1], :3] = t[i]
        parts.append(p)
    return np.concatenate(parts, axis=1)


sheet_img = np.concatenate([row(0), row(1), row(2)], axis=0)[::-1]
fb.save_pixels(sheet_img, out)
print("overlay", out, sheet_img.shape)
