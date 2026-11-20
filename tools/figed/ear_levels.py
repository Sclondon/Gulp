"""Where the ear sits on the head seen from the side: its top and bottom between the crown (0) and the chin (1),
its front and back edges between the back of the head (0) and the nose's tip (1), with the head set square.

    blender -b --factory-startup --python tools/figed/ear_levels.py -- <spec.json> [slider=value ...]
"""
import sys

import numpy as np

sys.path.insert(0, "tools/figed")
import figed  # noqa: E402
import figed_fit  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
base = figed.Base()
spec = figed.load_spec(argv[0])
for a in argv[1:]:
    k, v = a.split("=")
    spec.setdefault("bones" if "." in k else "targets", {})[k] = float(v)
fig = figed.Figure(base, spec)
P, H, T = fig.to_blender()
P = figed.pose_points(fig, P, H, figed_fit.full_pose(fig.pose, base.bones, H, T), T)[0]
turn, pivot = figed_fit.square_head(P, base)
P = (P - pivot).dot(turn.T) + pivot
d = P[base.indices("helper-l-eye")].mean(axis=0) - P[base.indices("helper-r-eye")].mean(axis=0)
body = base.indices("body")
head = body[base.weights[body, base.bones.index("head")] > 0.6]
chin = P[figed_fit.mark_vertices(base)["chin"]]
head = head[P[head][:, 2] > chin[2]]
fig.to_blender()
ear = fig.ear_pieces["l"][1] if getattr(fig, "ear_pieces", None) else P[fig._ear_masks()["l"][2]]
ear = (ear - pivot).dot(turn.T) + pivot if getattr(fig, "ear_pieces", None) else ear
crown = P[head][:, 2].max()
back, front = P[head][:, 1].max(), P[head][:, 1].min()
lv = lambda z: (crown - z) / (crown - chin[2])
ac = lambda y: (back - y) / (back - front)
print("ear: top %.2f bottom %.2f (crown 0, chin 1); back edge %.2f front edge %.2f (back of head 0, nose tip 1); stands out %.3f m; eye line off square %.2f %.2f" % (
    lv(ear[:, 2].max()), lv(ear[:, 2].min()), ac(ear[:, 1].max()), ac(ear[:, 1].min()),
    ear[:, 0].max() - np.percentile(np.abs(P[head][:, 0]), 90), d[1] / d[0], d[2] / d[0]))
