"""figed fit: move the sliders until the figure's outline matches a drawing's.

    blender -b --factory-startup --python tools/figed/figed_fit.py -- <job.json> [--sweeps N] [--look-only]

A job names the spec to start from and to write, the views (a picture, a box in it, which way it looks, an
optional window of the figure it covers) and the sliders that may move. See figures/brother_body.fit.json.

How: the drawing's figure is cut from its flat background (flood fill from the box's edge); the model is drawn
as a filled outline at the same size; the score is how much the two overlap (IoU) over all views; each slider in
turn is nudged up and down and a nudge is kept when the score improves (coordinate descent, steps halving).
"""
import json
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figed  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))


def path_of(p):
    return p if os.path.isabs(p) else os.path.join(ROOT, p)


def load_image(path):
    img = bpy.data.images.load(path_of(path))
    w, h = img.size
    a = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1, :, :3]
    bpy.data.images.remove(img)
    return a


def grow(mask, n=1):
    for _ in range(n):
        m = mask.copy()
        m[1:] |= mask[:-1]
        m[:-1] |= mask[1:]
        m[:, 1:] |= mask[:, :-1]
        m[:, :-1] |= mask[:, 1:]
        mask = m
    return mask


def shrink(mask, n=1):
    return ~grow(~mask, n)


def cut_out(img, box, tolerance=0.07):
    """The figure in `box` (x0, y0, x1, y1) as a mask: everything the background colour cannot reach from the
    box's edge. Thin guide lines are taken as background (they are within the tolerance, or opened away)."""
    x0, y0, x1, y1 = box
    a = img[y0:y1, x0:x1]
    edge = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    bg = np.median(edge, axis=0)
    like = np.abs(a - bg).max(axis=2) < tolerance
    # a thin level guide line with background just above and just below it is background too
    for n in (2, 3, 4):
        up = np.zeros_like(like)
        down = np.zeros_like(like)
        up[n:] = like[:-n]
        down[:-n] = like[n:]
        like = like | (up & down)
    reach = np.zeros(like.shape, dtype=bool)
    reach[0], reach[-1], reach[:, 0], reach[:, -1] = like[0], like[-1], like[:, 0], like[:, -1]
    while True:
        new = grow(reach) & like
        if new.sum() == reach.sum():
            break
        reach = new
    mask = ~reach
    mask = grow(shrink(mask, 2), 2)          # opens away specks
    # keep only the piece under the box's middle (labels and neighbours go)
    h, w = mask.shape
    ys, xs = np.nonzero(mask)
    near = np.argmin((ys - h / 2.0) ** 2 + (xs - w / 2.0) ** 2)
    piece = np.zeros_like(mask)
    piece[ys[near], xs[near]] = True
    while True:
        new = grow(piece, 3) & mask
        if new.sum() == piece.sum():
            break
        piece = new
    return piece


class Sampler:
    """Points spread over the body's skin, as fixed mixes of its vertices: quick outlines without a renderer."""

    def __init__(self, base, count=260000, seed=3, bones=None):
        near = None
        if bones:                                     # only the skin that belongs to these bones
            near = base.weights[:, [base.bones.index(b) for b in bones]].sum(axis=1) > 0.05
        tris = []
        for group, vi, _ti in base.faces:
            if group == "body" and (near is None or near[vi].any()):
                for k in range(1, len(vi) - 1):
                    tris.append((vi[0], vi[k], vi[k + 1]))
        t = np.array(tris)
        p = base.verts
        area = np.linalg.norm(np.cross(p[t[:, 1]] - p[t[:, 0]], p[t[:, 2]] - p[t[:, 0]]), axis=1)
        rng = np.random.default_rng(seed)
        pick = rng.choice(len(t), size=count, p=area / area.sum())
        u, v = rng.random(count), rng.random(count)
        flip = u + v > 1
        u[flip], v[flip] = 1 - u[flip], 1 - v[flip]
        self.tri = t[pick]
        self.w = np.stack([1 - u - v, u, v], axis=1)

    def points(self, P):
        return (P[self.tri] * self.w[:, :, None]).sum(axis=1)


def pose_points(fig, P, H, pose):
    """Turn bones (degrees about Blender's x, y, z at each bone's head; children follow)."""
    if not pose:
        return P, H
    base = fig.base
    mats = {}
    for b in base.bones:
        parent = base.rig[b]["parent"]
        M = mats[parent] if parent else np.eye(4)
        if b in pose:
            rx, ry, rz = np.radians(pose[b])
            cx, sx, cy, sy, cz, sz = np.cos(rx), np.sin(rx), np.cos(ry), np.sin(ry), np.cos(rz), np.sin(rz)
            R = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
            R = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]]).dot(R)
            R = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]]).dot(R)
            L = np.eye(4)
            L[:3, :3] = R
            L[:3, 3] = H[b] - R.dot(H[b])
            M = M.dot(L)
        mats[b] = M
    out = np.zeros_like(P)
    for i, b in enumerate(base.bones):
        w = base.weights[:, i]
        idx = np.nonzero(w)[0]
        if len(idx):
            M = mats[b]
            out[idx] += w[idx, None] * (P[idx].dot(M[:3, :3].T) + M[:3, 3])
    return out, H


def full_pose(spec_pose, bones):
    """The pose sliders of a spec as turns of bones."""
    pose = {b: v for b, v in spec_pose.items() if b in bones}
    if "arms_down" in spec_pose:
        a = spec_pose["arms_down"]
        pose["upperarm_l"] = (0, a, 0)
        pose["upperarm_r"] = (0, -a, 0)
    if "arms_back" in spec_pose:
        a = spec_pose["arms_back"]
        l = pose.get("upperarm_l", (0, 0, 0))
        r = pose.get("upperarm_r", (0, 0, 0))
        pose["upperarm_l"] = (l[0], l[1], a)
        pose["upperarm_r"] = (r[0], r[1], -a)
    if "elbows" in spec_pose:
        a = spec_pose["elbows"]
        pose["lowerarm_l"] = (a, 0, 0)
        pose["lowerarm_r"] = (a, 0, 0)
    if "legs_apart" in spec_pose:                  # the stance; the feet stay flat
        a = spec_pose["legs_apart"]
        pose["thigh_l"] = (0, -a, 0)
        pose["thigh_r"] = (0, a, 0)
        pose["foot_l"] = (0, a, 0)
        pose["foot_r"] = (0, -a, 0)
    if "feet_out" in spec_pose:                    # toes turned out
        a = spec_pose["feet_out"]
        l = pose.get("foot_l", (0, 0, 0))
        r = pose.get("foot_r", (0, 0, 0))
        pose["foot_l"] = (l[0], l[1], a)
        pose["foot_r"] = (r[0], r[1], -a)
    return pose


class View:
    def __init__(self, spec):
        self.spec = spec
        img = load_image(spec["picture"])
        k = img.shape[1] / float(spec.get("box_width", img.shape[1]))   # boxes are given at this picture width
        box = [int(round(c * k)) for c in spec["box"]]
        want = spec.get("tall")                       # work at about this many pixels tall
        if want and (box[3] - box[1]) > want * 1.5:
            n = int((box[3] - box[1]) // want)
            img = img[::n, ::n]
            box = [c // n for c in box]
        print("picture", spec["picture"], img.shape[1], "x", img.shape[0], "box", box)
        self.mask = cut_out(img, box, spec.get("tolerance", 0.07))
        ys, xs = np.nonzero(self.mask)
        self.top, self.bottom = ys.min(), ys.max()
        self.left, self.right = xs.min(), xs.max()
        self.h, self.w = self.mask.shape
        self.look = spec["look"]                      # front, back, side (nose to the right), side_left
        self.window = spec.get("window")              # [lo, hi] share of the figure's height shown, or None
        self.weight = spec.get("weight", 1.0)
        rows = slice(self.top, self.top + max(2, (self.bottom - self.top) // 12))
        cols = np.nonzero(self.mask[rows].any(axis=0))[0]
        self.head_x = (cols.min() + cols.max()) / 2.0
        self.anchor = spec.get("anchor", "head")      # "feet": line the view up by the feet, not the head
        if self.anchor == "feet":
            rows = slice(self.bottom - max(2, (self.bottom - self.top) // 12), self.bottom + 1)
            cols = np.nonzero(self.mask[rows].any(axis=0))[0]
            self.head_x = (cols.min() + cols.max()) / 2.0
        # a close-up of the head: the picture's row to compare down to ("cut", in box_width pixels, e.g. just
        # under the chin); its size against the model is not known, so it is a slider too ("zoom")
        self.cut = None
        if "cut" in spec:
            self.cut = int(round(spec["cut"] * k)) - box[1]
            self.mask = self.mask.copy()
            self.mask[self.cut:] = False
            self.k0 = (self.cut - self.top) / float(spec.get("span", 0.27))

    def draw_head(self, pts, dx=0.0, dy=0.0, zoom=1.0):
        if self.look == "front":
            u = pts[:, 0]
        elif self.look == "back":
            u = -pts[:, 0]
        elif self.look == "side":
            u = -pts[:, 1]
        else:
            u = pts[:, 1]
        v = pts[:, 2]
        crown = v.max()
        k = self.k0 * zoom
        keep = v > crown - (self.cut - self.top + 12) / k
        u, v = u[keep], v[keep]
        skull = v > crown - 0.06
        mid = (u[skull].min() + u[skull].max()) / 2.0
        ix = np.round(self.head_x + (u - mid) * k + dx).astype(int)
        iy = np.round(self.top + (crown - v) * k + dy).astype(int)
        ok = (ix >= 0) & (ix < self.w) & (iy >= 0) & (iy < self.cut)
        m = np.zeros((self.h, self.w), dtype=bool)
        m[iy[ok], ix[ok]] = True
        m = shrink(grow(m, 3), 2)
        m[self.cut:] = False
        return m

    def draw(self, pts, height, dx=0.0, zoom=1.0):
        """The model's outline in this view's pixels. pts: Blender metres."""
        if self.look == "front":
            u = pts[:, 0]
        elif self.look == "back":
            u = -pts[:, 0]
        elif self.look == "side":
            u = -pts[:, 1]
        else:
            u = pts[:, 1]
        v = pts[:, 2]
        if self.window:
            lo, hi = self.window[0] * height, self.window[1] * height
        else:
            lo, hi = 0.0, height
        k = (self.bottom - self.top) / (hi - lo) * zoom
        keep = (v >= lo - 0.02) & (v <= hi + 0.02)
        u, v = u[keep], v[keep]
        top_rows = (v < lo + (hi - lo) / 12.0) if self.anchor == "feet" else (v > hi - (hi - lo) / 12.0)
        mid = (u[top_rows].min() + u[top_rows].max()) / 2.0 if top_rows.any() else 0.0
        ix = np.round(self.head_x + (u - mid) * k + dx).astype(int)
        iy = np.round(self.bottom - (v - lo) * k).astype(int)
        ok = (ix >= 0) & (ix < self.w) & (iy >= 0) & (iy < self.h)
        m = np.zeros((self.h, self.w), dtype=bool)
        m[iy[ok], ix[ok]] = True
        return shrink(grow(m, 2), 1)

    def score(self, model):
        a, b = self.mask, model
        if self.window:
            b = b.copy()
            b[:self.top] = False
            b[self.bottom + 1:] = False
        bands = self.spec.get("bands")
        if not bands:
            return (a & b).sum() / float((a | b).sum())
        total, weight = 0.0, 0.0                      # bands: [from, to, weight] in shares of the height, floor up
        span = self.bottom - self.top
        for lo, hi, w in bands:
            if w <= 0:
                continue
            r0, r1 = int(self.bottom - hi * span), int(self.bottom - lo * span) + 1
            union = (a[r0:r1] | b[r0:r1]).sum()
            total += w * ((a[r0:r1] & b[r0:r1]).sum() / float(max(1, union)))
            weight += w
        return total / weight


class Job:
    def __init__(self, job):
        self.job = job
        self.base = figed.Base()
        self.sampler = Sampler(self.base)
        self.head_sampler = Sampler(self.base, 400000, 5, ["head", "neck_01", "spine_03", "clavicle_l", "clavicle_r"])
        self.views = [View(v) for v in job["views"]]
        start = job.get("start")
        self.spec = figed.load_spec(path_of(start)) if start and os.path.exists(path_of(start)) else {}
        for k in ("macro", "targets", "bones", "pose", "shift", "zoom", "drop"):
            self.spec.setdefault(k, {})
        self.params = []                              # (section, name, lo, hi, step)
        for section, table in job["move"].items():
            for name, (lo, hi, step) in table.items():
                self.params.append((section, name, lo, hi, step))
                if name not in self.spec[section]:
                    self.spec[section][name] = job.get("defaults", {}).get(section, {}).get(
                        name, {"macro": 0.5, "bones": 1.0, "zoom": 1.0}.get(section, 0.0))
        self.evals = 0

    def figure(self):
        return figed.Figure(self.base, self.spec)

    def outlines(self):
        fig = self.figure()
        P, H, _T = fig.to_blender()
        P0, H0 = P, H
        common = {k: v for k, v in self.spec["pose"].items() if "@" not in k}
        P, H = pose_points(fig, P0, H0, full_pose(common, self.base.bones))
        pts = self.sampler.points(P)
        height = pts[:, 2].max()
        own = {}                                      # a view drawn in a pose of its own: "arms_down@side"
        for v in self.views:
            n = v.spec["name"]
            extra = {k.split("@")[0]: x for k, x in self.spec["pose"].items() if k.endswith("@" + n)}
            if extra:
                Pv, _ = pose_points(fig, P0, H0, full_pose(dict(common, **extra), self.base.bones))
                own[n] = self.sampler.points(Pv)
        head_pts = self.head_sampler.points(P) if any(v.cut is not None for v in self.views) else None
        out = []
        for v in self.views:
            n = v.spec["name"]
            if v.cut is not None:
                out.append(v.draw_head(head_pts, self.spec["shift"].get(n, 0.0), self.spec["drop"].get(n, 0.0),
                                       self.spec["zoom"].get(n, 1.0)))
            else:
                out.append(v.draw(own.get(n, pts), height, self.spec["shift"].get(n, 0.0), self.spec["zoom"].get(n, 1.0)))
        return out

    def loss(self):
        self.evals += 1
        total, weight = 0.0, 0.0
        for v, m in zip(self.views, self.outlines()):
            total += (1 - v.score(m)) * v.weight
            weight += v.weight
        reg = sum(x * x for x in self.spec["targets"].values()) * self.job.get("stiffness", 0.0015)
        reg += sum((x - 1) ** 2 for x in self.spec["bones"].values()) * self.job.get("stiffness", 0.0015) * 4
        return total / weight + reg

    def run(self, sweeps=8):
        steps = {(p[0], p[1]): p[4] for p in self.params}
        for section, name, lo, hi, _ in self.params:      # the size of a close-up: look over its whole range first
            if section == "zoom":
                tries = []
                for z in np.linspace(lo, hi, 25):
                    self.spec[section][name] = float(z)
                    tries.append((self.loss(), float(z)))
                self.spec[section][name] = min(tries)[1]
        best = self.loss()
        print("start %.4f" % best)
        for sweep in range(sweeps):
            moved = 0
            for section, name, lo, hi, _ in self.params:
                step = steps[(section, name)]
                here = self.spec[section][name]
                for trial in (here + step, here - step):
                    trial = min(hi, max(lo, trial))
                    if trial == here:
                        continue
                    self.spec[section][name] = trial
                    try:
                        l = self.loss()
                    except Exception as e:           # a slider the base does not have
                        print("skip", name, e)
                        l = 9.0
                    if l < best - 1e-5:
                        best, here, moved = l, trial, moved + 1
                    else:
                        self.spec[section][name] = here
            print("sweep %d: %.4f (%d moved, %d tries)" % (sweep, best, moved, self.evals))
            sys.stdout.flush()
            if moved < 3:
                for k in steps:
                    steps[k] *= 0.5
        return best

    def save(self, out):
        clean = {k: v for k, v in self.spec.items()}
        for section in ("targets",):
            clean[section] = {k: round(v, 4) for k, v in clean[section].items() if abs(v) > 1e-6}
        clean["bones"] = {k: round(v, 4) for k, v in clean["bones"].items() if abs(v - 1) > 1e-6}
        with open(path_of(out), "w") as f:
            json.dump(clean, f, indent=1, sort_keys=True)

    def picture(self, out):
        """Drawing in red, model in cyan, both grey: one tile a view."""
        tiles = []
        height = max(v.h for v in self.views)
        for v, m in zip(self.views, self.outlines()):
            t = np.ones((height, v.w + 8, 4), dtype=np.float32)
            a, b = v.mask, m
            rgb = np.ones((v.h, v.w, 3), dtype=np.float32)
            rgb[a & b] = (0.55, 0.55, 0.55)
            rgb[a & ~b] = (0.95, 0.2, 0.2)
            rgb[~a & b] = (0.1, 0.75, 0.85)
            t[:v.h, :v.w, :3] = rgb
            tiles.append(t[::-1])
        a = np.concatenate(tiles, axis=1)
        img = bpy.data.images.new("fit", a.shape[1], a.shape[0], alpha=True)
        img.pixels.foreach_set(a.ravel())
        img.filepath_raw = out
        img.file_format = "PNG"
        img.save()


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    with open(path_of(argv[0]), "r") as f:
        job = json.load(f)
    sweeps = int(argv[argv.index("--sweeps") + 1]) if "--sweeps" in argv else job.get("sweeps", 10)
    j = Job(job)
    for v in j.views:
        print("view %s: figure %dx%d px in a %dx%d box" % (v.spec["name"], v.right - v.left, v.bottom - v.top,
                                                           v.w, v.h))
    out_pic = path_of(job["picture"]) if not os.path.isabs(job["picture"]) else job["picture"]
    if "--pic" in argv:
        out_pic = argv[argv.index("--pic") + 1]
    if "--look-only" not in argv:
        j.run(sweeps)
        j.save(job["out"])
    print("scores:", {v.spec["name"]: round(v.score(m), 4) for v, m in zip(j.views, j.outlines())})
    j.picture(out_pic)


if __name__ == "__main__":
    main()
