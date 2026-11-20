"""The arm's thickness along its length, drawing against model: how wide (seen from the front or back) and how
deep (seen from the side) it is at stations from the top of the shoulder (0) to the wrist (1), each as a share of
that length. An arm hidden inside the body's outline, or held another way in the body sheets, is checked like this.

    blender -b --factory-startup --python tools/figed/arm_widths.py -- <spec.json> <job.json>

The job: {"picture": ..., "box_width": px, "views": [{"name", "box": [x0, y0, x1, y1], "wrist": row,
"kind": "wide" | "deep"}], "stations": [0.3, ...]}.
"""
import json
import sys

import numpy as np

sys.path.insert(0, "tools/figed")
import figed  # noqa: E402
import figed_fit  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
base = figed.Base()
spec = figed.load_spec(argv[0])
with open(argv[1]) as f:
    job = json.load(f)
stations = job["stations"]

# the drawing
img = figed_fit.load_image(job["picture"])
k = img.shape[1] / float(job["box_width"])
art = {"wide": [], "deep": []}
for v in job["views"]:
    box = [int(round(c * k)) for c in v["box"]]
    mask = figed_fit.cut_out(img, box, 0.07)
    ys = np.nonzero(mask.any(axis=1))[0]
    top, wrist = ys.min(), int(round(v["wrist"] * k)) - box[1]
    row = []
    for t in stations:
        y = int(top + (wrist - top) * t)
        band = mask[y - 2:y + 3].any(axis=0)
        xs = np.nonzero(band)[0]
        row.append((xs.max() - xs.min()) / float(wrist - top))
    art[v["kind"]].append(row)
    print("drawing %-10s %s" % (v["name"], " ".join("%.3f" % x for x in row)))

# the model: the left arm as it rests, measured in its own directions
fig = figed.Figure(base, spec)
P, H, T = fig.to_blender()
body = base.indices("body")
chain = [i for i, b in enumerate(base.bones) if b.endswith("_l") and b.split("_")[0] in (
    "upperarm", "lowerarm", "hand", "thumb", "index", "middle", "ring", "pinky")]
own = body[base.weights[body][:, chain].sum(axis=1) > 0.5]
pose = {}
straight = figed_fit.full_pose({"arms_straight": 1}, base.bones, H, T)
Pp, posed = figed.pose_points(fig, P, H, straight, T)
W, S = posed["hand_l"], posed["upperarm_l"]
f = (S - W) / np.linalg.norm(S - W)
a = np.cross([0, 1.0, 0], f)
a /= np.linalg.norm(a)
d = np.cross(f, a)
q = Pp[own] - W
v = q.dot(f)
length = v.max()
out = {"wide": [], "deep": []}
for t in stations:
    at = length * (1 - t)
    near = np.abs(v - at) < length * 0.04
    out["wide"].append((q[near].dot(a).max() - q[near].dot(a).min()) / length)
    out["deep"].append((q[near].dot(d).max() - q[near].dot(d).min()) / length)
print("stations          %s" % " ".join("%.2f " % t for t in stations))
for kind in ("wide", "deep"):
    mean = np.mean(art[kind], axis=0)
    print("drawing %-5s      %s" % (kind, " ".join("%.3f" % x for x in mean)))
    print("model   %-5s      %s" % (kind, " ".join("%.3f" % x for x in out[kind])))
    print("model / drawing   %s" % " ".join("%.2f " % (m / x) for m, x in zip(out[kind], mean)))
print("arm length, shoulder top to wrist: %.3f m" % length)
