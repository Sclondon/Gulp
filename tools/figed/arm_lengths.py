"""Arms hung straight down: how far up his height the shoulder, elbow, wrist and fingertip sit, and each part's length."""
import json
import sys

import numpy as np

sys.path.insert(0, "tools/figed")
import figed  # noqa: E402
import figed_fit  # noqa: E402

base = figed.Base()
spec = figed.load_spec(sys.argv[sys.argv.index("--") + 1])
fig = figed.Figure(base, spec)
P, H, T = fig.to_blender()
body = base.indices("body")
top = P[body][:, 2].max()
d = H["hand_l"] - H["upperarm_l"]
rest = np.degrees(np.arctan2(d[0], -d[2]))          # degrees out from straight down, seen from the front
print("height %.3f m; arm at rest is %.1f degrees out from straight down" % (top, rest))
n = lambda a, b: np.linalg.norm(a - b) / top * 100
print("lengths, %% of height: upper arm %.1f, forearm %.1f, hand %.1f (wrist to middle fingertip)" % (
    n(H["upperarm_l"], H["lowerarm_l"]), n(H["lowerarm_l"], H["hand_l"]), n(H["hand_l"], T["middle_03_l"])))
pose = {"arms_down": rest, "arms_back": 0, "elbows": 0}
Pp, posed = figed.pose_points(fig, P, H, figed_fit.full_pose(pose, base.bones, H, T), T)
for name, key in (("shoulder", "upperarm_l"), ("elbow", "lowerarm_l"), ("wrist", "hand_l"), ("fingertip", "tail:middle_03_l")):
    print("%s at %.1f%% of height, x %.3f" % (name, posed[key][2] / top * 100, posed[key][0]))
out = dict(spec)
out["pose"] = pose
with open(sys.argv[sys.argv.index("--") + 2], "w") as f:
    json.dump(out, f)
