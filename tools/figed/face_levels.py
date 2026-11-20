"""Where the face's features sit between the crown (0) and the chin's bottom (1), and how wide the head is to that
height: the model's, to set beside a drawing's.

    blender -b --factory-startup --python tools/figed/face_levels.py -- <spec.json> [slider=value ...]
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
    section = "bones" if "." in k else "targets"
    spec.setdefault(section, {})[k] = float(v)
fig = figed.Figure(base, spec)
P, H, T = fig.to_blender()
body = base.indices("body")
head = body[base.weights[body, base.bones.index("head")] > 0.6]
chin = P[figed_fit.mark_vertices(base)["chin"]]
crown = P[head][:, 2].max()
high = crown - chin[2]


def peak(target, centre=True):
    idx, d = base.target(target)
    size = np.linalg.norm(d, axis=1)
    if centre:
        size = size - 100 * np.abs(base.verts[idx, 0])
    return P[int(idx[np.argmax(size)])]


mid = head[np.abs(P[head][:, 0]) < 0.012]
nose = P[mid[np.argmin(P[mid][:, 1])]]
eye = P[base.indices("helper-l-eye")].mean(axis=0)
level = lambda p: (crown - p[2]) / high
above = head[P[head][:, 2] > chin[2]]
skull = above[np.abs(P[above][:, 1] - H["head"][1]) < 0.05]          # across the skull, not the ears
print("levels (crown 0, chin 1): brow %.2f, eyes %.2f, nose tip %.2f, mouth %.2f" % (
    level(peak("eyebrows-trans-up")), level(eye), level(nose), level(peak("mouth-trans-up"))))
print("head: %.3f m crown to chin; widest %.3f (%.2f of the height); deep %.3f (%.2f)" % (
    high, P[above][:, 0].max() - P[above][:, 0].min(), (P[above][:, 0].max() - P[above][:, 0].min()) / high,
    P[above][:, 1].max() - P[above][:, 1].min(), (P[above][:, 1].max() - P[above][:, 1].min()) / high))
