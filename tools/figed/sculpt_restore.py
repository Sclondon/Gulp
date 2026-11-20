"""Take the LAST sculpt session's moves off the eyebrow area (the user: "I messed up his eyer brows"), fading at its edge."""
import json
import sys

import numpy as np

sys.path.insert(0, "tools/figed")
import figed  # noqa: E402

before_path, now_path = sys.argv[sys.argv.index("--") + 1:][:2]
base = figed.Base()
w = np.zeros(len(base.verts))
for side in "lr":
    for part in ("eye-scale-incr", "eye-scale-decr", "eye-height1-incr", "eye-height2-incr", "eye-height3-incr",
                 "eye-height1-decr", "eye-height2-decr", "eye-height3-decr", "eye-eyefold-up", "eye-eyefold-down",
                 "eye-corner1-up", "eye-corner2-up", "eye-push1-out", "eye-push2-out"):
        name = side + "-" + part
        if base.has(name):
            idx, d = base.target(name)
            size = np.linalg.norm(d, axis=1)
            w[idx] = np.maximum(w[idx], size / size.max())
brow = np.clip(w / 0.25, 0, 1)                           # 1 on the brow, fading out where the targets fade
with open(before_path) as f:
    old = json.load(f)
with open(now_path) as f:
    new = json.load(f)
was = {int(i): np.array(m) for i, m in zip(old["points"], old["moves"])}
out_p, out_m, touched = [], [], 0
for i, m in zip(new["points"], new["moves"]):
    m = np.array(m)
    k = brow[int(i)]
    if k > 0:
        m = was.get(int(i), np.zeros(3)) * k + m * (1 - k)
        touched += 1
    out_p.append(int(i))
    out_m.append([round(float(x), 6) for x in m])
new["points"], new["moves"] = out_p, out_m
with open(now_path, "w") as f:
    json.dump(new, f)
print("eyelid points put back:", touched, "of", int((brow > 0).sum()), "in the eyelid area")
