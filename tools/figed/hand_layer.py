"""The user's hand paint as a layer of its own: where their saved skin differs from the projection it was painted
on, kept (RGBA, alpha = how much it differs, feathered) so a later projection can lay it back on top."""
import sys
import bpy
import numpy as np
user_p, proj_p, out_p = sys.argv[sys.argv.index("--") + 1:][:3]
def load(p):
    im = bpy.data.images.load(p)
    a = np.array(im.pixels[:]).reshape(im.size[1], im.size[0], 4)
    return a
u, pr = load(user_p), load(proj_p)
d = np.abs(u[:, :, :3] - pr[:, :, :3]).max(axis=2)
m = (d > 0.012).astype(float)
for _ in range(3):                                   # feather the edge
    m = (m + np.roll(m, 1, 0) + np.roll(m, -1, 0) + np.roll(m, 1, 1) + np.roll(m, -1, 1)) / 5
out = u.copy()
out[:, :, 3] = np.clip(m * 1.5, 0, 1)
im = bpy.data.images.new("hand", u.shape[1], u.shape[0], alpha=True)
im.pixels.foreach_set(out.astype(np.float32).ravel())
im.filepath_raw = out_p
im.file_format = "PNG"
im.save()
print("hand paint: %d texels changed (%.1f%% of the picture)" % (int((d > 0.012).sum()), 100 * (d > 0.012).mean()))
