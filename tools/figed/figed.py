"""figed: the figure editor's core (see tools/figed/README.md).

A figure is ONE generic human (MakeHuman's CC0 base mesh, kept outside the repo) plus a table of control values.
Nothing here models anything by hand: every vertex of the base already belongs to named controls, of two kinds:

  targets   MakeHuman's own artist-made sliders (about 600 once left/right and less/more are paired): which
            vertices move and how far for "longer shin", "wider nostrils", "brow down" ...
  bones     ours: every vertex is sorted to the bones of the skeleton by its skin weights, and a bone can be made
            longer, wider or deeper without limit; what hangs off it is carried along, not stretched.

Run inside Blender's Python (it has numpy). Units here are MakeHuman's (decimetres, y up, z towards the viewer);
`to_blender` turns points into metres, z up, facing -y, feet on the floor.
"""
import gzip
import json
import os
import re

import numpy as np

MH = os.environ.get("FIGED_MH", r"C:\Projects\reference\makehuman\mpfb2\src\mpfb\data")
RIG = "game_engine"

# Pairs of opposite target endings: (the -1 end, the +1 end). decr/incr controls take the bare name.
PAIRS = [("decr", "incr"), ("down", "up"), ("in", "out"), ("backward", "forward"), ("compress", "uncompress"),
         ("concave", "convex")]

# Friendly names for the controls most used when fitting a body to a drawing: name -> control or controls.
ALIASES = {
    "shin_length": ["measure-lowerleg-height"], "thigh_length": ["measure-upperleg-height"],
    "forearm_length": ["measure-lowerarm-length"], "upper_arm_length": ["measure-upperarm-length"],
    "finger_length": ["hand-fingers-length"], "finger_thickness": ["hand-fingers-diameter"],
    "finger_spread": ["hand-fingers-distance"], "hand_size": ["hand-scale"], "foot_size": ["foot-scale"],
    "shoulder_width": ["measure-shoulder-dist"], "chest": ["measure-bust-circ"],
    "ribs": ["measure-underbust-circ"], "waist": ["measure-waist-circ"], "hips": ["measure-hips-circ"],
    "torso_length": ["measure-napetowaist-dist"], "waist_to_hip": ["measure-waisttohip-dist"],
    "neck_thickness": ["measure-neck-circ"], "neck_length": ["measure-neck-height"],
    "upper_arm_thickness": ["measure-upperarm-circ"], "wrist": ["measure-wrist-circ"],
    "thigh_thickness": ["measure-thigh-circ"], "knee": ["measure-knee-circ"], "calf": ["measure-calf-circ"],
    "ankle": ["measure-ankle-circ"], "pecs": ["torso-muscle-pectoral"], "lats": ["torso-muscle-dorsi"],
    "v_shape": ["torso-vshape"], "belly": ["stomach-pregnant"], "belly_tone": ["stomach-tone"],
    "buttocks": ["buttocks-volume"], "shoulder_muscle": ["upperarm-shoulder-muscle"],
    "brow_height": ["eyebrows-trans-up"], "brow_forward": ["eyebrows-trans-forward"],
    "brow_angle": ["eyebrows-angle-up"],
    "nose_size": ["nose-volume"], "nose_width": ["nose-scale-horiz"], "nose_length": ["nose-scale-vert"],
    "nose_out": ["nose-scale-depth"], "nose_tip_up": ["nose-point-up"], "nose_tip_width": ["nose-point-width"],
    "nostril_width": ["nose-nostrils-width"], "nose_flare": ["nose-flaring"], "nose_hump": ["nose-hump"],
    "nose_bridge_width": ["nose-width1"], "nose_mid_width": ["nose-width2"], "nose_base_width": ["nose-width3"],
    "jaw_width": ["chin-bones"], "chin_width": ["chin-width"], "chin_height": ["chin-height"],
    "chin_forward": ["chin-prominent"], "jaw_drop": ["chin-jaw-drop"], "double_chin": ["neck-double"],
    "cheek_fullness": ["cheek-volume"], "cheekbones": ["cheek-bones"],
    "head_width": ["head-scale-horiz"], "head_height": ["head-scale-vert"], "head_depth": ["head-scale-depth"],
    "head_fat": ["head-fat"], "head_age": ["head-age"],
    "eye_size": ["eye-scale"], "eye_bags": ["eye-bag"], "eye_outer_corner_up": ["eye-corner2-up"],
    "eye_inner_corner_up": ["eye-corner1-up"], "eye_apart": ["eye-trans-out"], "eye_height": ["eye-trans-up"],
    "ear_size": ["ear-scale"], "ear_out": ["ear-wing"],
}

# Bone groups for the "bones" kind of control: name -> (bones, what it scales). A value is a factor (1 = as is).
# "length" stretches along the bone, "width" across it side to side, "depth" front to back, "girth" both across,
# "size" all three.
BONE_SETS = {
    "thigh": ["thigh_l", "thigh_r"], "calf": ["calf_l", "calf_r"], "foot": ["foot_l", "foot_r", "ball_l", "ball_r"],
    "upperarm": ["upperarm_l", "upperarm_r"], "lowerarm": ["lowerarm_l", "lowerarm_r"],
    "hand": ["hand_l", "hand_r"], "clavicle": ["clavicle_l", "clavicle_r"],
    "fingers": ["%s_0%d_%s" % (f, i, s) for f in ("index", "middle", "ring", "pinky") for i in (1, 2, 3)
                for s in "lr"],
    "thumb": ["thumb_0%d_%s" % (i, s) for i in (1, 2, 3) for s in "lr"],
    "toes": ["ball_l", "ball_r"],
    "pelvis": ["pelvis"], "spine_01": ["spine_01"], "spine_02": ["spine_02"], "spine_03": ["spine_03"],
    "torso": ["pelvis", "spine_01", "spine_02", "spine_03"], "chest_bone": ["spine_03"],
    "neck": ["neck_01"], "head": ["head"],
}
WHAT = {"length": (0, 1, 0), "width": (1, 0, 0), "depth": (0, 0, 1), "girth": (1, 0, 1), "size": (1, 1, 1)}
# "flesh_*" scales only the bone's own skin: the joints that hang off it stay where they are (wider hips without
# moving the legs apart).
FLESH = {"flesh_width": (1, 0, 0), "flesh_depth": (0, 0, 1), "flesh": (1, 0, 1)}
EAR_FROM = 0.0                                      # share of the ear-wing target's most that counts as ear

MACRO_DEFAULT = {"gender": 1.0, "age": 0.5, "muscle": 0.5, "weight": 0.5, "height": 0.5, "proportions": 0.5,
                 "race": {"caucasian": 1.0}}

_cache = {}


def _json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class Base:
    """The generic human as read from MakeHuman's files: points, faces by group, UVs, skeleton and weights."""

    def __init__(self):
        verts, uvs, faces = [], [], []
        group = "body"
        with open(os.path.join(MH, "3dobjs", "base.obj"), "r") as f:
            for line in f:
                if line.startswith("v "):
                    verts.append([float(x) for x in line.split()[1:4]])
                elif line.startswith("vt "):
                    uvs.append([float(x) for x in line.split()[1:3]])
                elif line.startswith("g "):
                    group = line.split()[1]
                elif line.startswith("f "):
                    vi, ti = [], []
                    for corner in line.split()[1:]:
                        p = corner.split("/")
                        vi.append(int(p[0]) - 1)
                        ti.append(int(p[1]) - 1 if len(p) > 1 and p[1] else -1)
                    faces.append((group, vi, ti))
        self.verts = np.array(verts)
        self.uvs = np.array(uvs)
        self.faces = faces
        self.ranges = _json(os.path.join(MH, "mesh_metadata", "basemesh_vertex_groups.json"))
        self.rig = _json(os.path.join(MH, "rigs", "standard", "rig.%s.json" % RIG))
        raw = _json(os.path.join(MH, "rigs", "standard", "weights.%s.json" % RIG))["weights"]
        self.bones = self._order(self.rig)
        n = len(self.verts)
        w = np.zeros((n, len(self.bones)))
        for b, pairs in raw.items():
            if pairs and b in self.bones:
                a = np.array(pairs)
                w[a[:, 0].astype(int), self.bones.index(b)] = a[:, 1]
        total = w.sum(axis=1, keepdims=True)
        total[total == 0] = 1.0
        self.weights = w / total
        # targets by name
        self.paths = {}
        for root, _dirs, files in os.walk(os.path.join(MH, "targets")):
            for name in files:
                if name.endswith(".target.gz"):
                    key = name[:-len(".target.gz")]
                    folder = os.path.relpath(root, os.path.join(MH, "targets")).replace("\\", "/")
                    self.paths[(folder + "/" + key) if folder.startswith("macrodetails") else key] = \
                        os.path.join(root, name)
                    self.paths.setdefault("folder:" + key, folder)
        self.controls = self._controls()

    @staticmethod
    def _order(rig):
        done, left = [], dict(rig)
        while left:
            for b in sorted(left):
                if not rig[b]["parent"] or rig[b]["parent"] in done:
                    done.append(b)
                    del left[b]
                    break
        return done

    def indices(self, group):
        out = []
        for a, b in self.ranges[group]:
            out.extend(range(a, b + 1))
        return np.array(out)

    def target(self, name):
        """(indices, offsets) of one target file."""
        if name not in _cache:
            path = self.paths[name]
            with gzip.open(path, "rt") as f:
                rows = [l.split() for l in f if l.strip() and not l.startswith("#")]
            a = np.array(rows, dtype=float) if rows else np.zeros((0, 4))
            _cache[name] = (a[:, 0].astype(int), a[:, 1:4])
        return _cache[name]

    def has(self, name):
        return name in self.paths

    def _controls(self):
        """Every slider: name -> {"neg": [targets], "pos": [targets], "sides": bool, "folder": str}.
        l-/r- targets are one control (ask for one side with ".l" / ".r" after the name)."""
        names = [k for k in self.paths if not k.startswith("folder:") and not k.startswith("macrodetails")]
        names = [k for k in names if self.paths["folder:" + k] not in ("expression",)
                 and not self.paths["folder:" + k].startswith("expression")]
        table = {}

        def entry(stem, sided, folder):
            e = table.setdefault(stem, {"neg": {}, "pos": {}, "sides": sided, "folder": folder})
            return e

        for k in names:
            side, stem = "", k
            m = re.match(r"^([lr])-(.*)$", k)
            if m:
                side, stem = m.group(1), m.group(2)
            folder = self.paths["folder:" + k]
            hit = False
            for neg, pos in PAIRS:
                for word, end in ((neg, "neg"), (pos, "pos")):
                    if stem.endswith("-" + word):
                        root = stem[:-len(word) - 1]
                        name = root if (neg, pos) == PAIRS[0] else root + "-" + pos
                        entry(name, bool(side), folder)[end][side] = k
                        hit = True
                if hit:
                    break
            if not hit:
                entry(stem, bool(side), folder)["pos"][side] = k
        return table

    def control_names(self):
        return sorted(self.controls)


def macro_parts(macro):
    m = dict(MACRO_DEFAULT)
    m.update(macro or {})
    g, a, mu, we, h, p = (float(m[k]) for k in ("gender", "age", "muscle", "weight", "height", "proportions"))
    gender = {"female": 1 - g, "male": g}
    if a < 0.1875:
        t = a / 0.1875
        age = {"baby": 1 - t, "child": t}
    elif a < 0.5:
        t = (a - 0.1875) / (0.5 - 0.1875)
        age = {"child": 1 - t, "young": t}
    else:
        t = (a - 0.5) / 0.5
        age = {"young": 1 - t, "old": t}

    def three(v, lo, mid, hi):
        if v < 0.5:
            return {lo: 1 - v * 2, mid: v * 2}
        return {mid: 1 - (v - 0.5) * 2, hi: (v - 0.5) * 2}

    muscle = three(mu, "minmuscle", "averagemuscle", "maxmuscle")
    weight = three(we, "minweight", "averageweight", "maxweight")
    height = {"minheight": max(0.0, 1 - h * 2), "maxheight": max(0.0, h * 2 - 1)}
    prop = {"uncommonproportions": max(0.0, 1 - p * 2), "idealproportions": max(0.0, p * 2 - 1)}
    return m["race"], gender, age, muscle, weight, height, prop


def pose_points(fig, P, H, pose, T=None):
    """Turn bones (degrees about Blender's x, y, z at each bone's head; children follow)."""
    base = fig.base
    mats = {}
    for b in base.bones:
        parent = base.rig[b]["parent"]
        M = mats[parent] if parent else np.eye(4)
        if b in pose:
            if np.shape(pose[b]) == (3, 3):               # a turn given whole
                R = np.asarray(pose[b])
            else:
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
    posed = {}                                        # where each joint is once posed; a bone tip as "tail:<bone>"
    for b in base.bones:
        M = mats[b]
        posed[b] = M[:3, :3].dot(H[b]) + M[:3, 3]
        if T is not None:
            posed["tail:" + b] = M[:3, :3].dot(T[b]) + M[:3, 3]
    return out, posed


class Figure:
    """One figure: the base plus a table of values. `solve()` gives its points and skeleton."""

    def __init__(self, base, spec=None):
        self.base = base
        spec = spec or {}
        self.macro = dict(spec.get("macro", {}))
        self.targets = dict(spec.get("targets", {}))     # control or alias -> value (-1..1, may go beyond)
        self.bones = dict(spec.get("bones", {}))         # "<set>.<what>" or "<bone>.<what>" -> factor
        self.raw = dict(spec.get("raw", {}))             # a target file by its own name -> weight
        self.pose = dict(spec.get("pose", {}))           # for pictures and the fit: how the drawing stands
        self.height = spec.get("height")                 # metres, crown to floor; None keeps what comes out
        # small corrections after the sliders: patches of skin relaxed smooth,
        # [{"at": "nipples", "radius": cm, "passes": n}]
        self.smooth = list(spec.get("smooth", []))
        # how he stands, built into the model itself (not a pose for pictures): {"pelvis_tuck": degrees} turns the
        # pelvis under (less hollow back) while the legs and the trunk above stay upright
        self.posture = dict(spec.get("posture", {}))
        # a small correction: the jaw's lower edge cut into the skin where a drawing has it. {"path": [[back, up],
        # ...] from the chin's bottom to under the ear, in shares of the head's height (crown to chin) seen from the
        # side; "depth": cm the skin just under the line is pressed in; "lip": cm the skin just over it is raised;
        # "width": how far under the line the cut reaches, same shares}
        self.jawline = dict(spec.get("jawline", {}))
        # a small correction: the ears alone, cut out, resized and moved, the skull and face untouched.
        # {"scale": factor, "back": cm, "down": cm, "out": cm}
        self.ears = dict(spec.get("ears", {}))

    def _adjacent(self):
        b = self.base
        if not hasattr(b, "_near"):                      # which points share an edge, once
            near = {}
            for _group, vi, _ti in b.faces:
                for i in range(len(vi)):
                    x, y = vi[i], vi[(i + 1) % len(vi)]
                    near.setdefault(x, set()).add(y)
                    near.setdefault(y, set()).add(x)
            b._near = {k: np.array(sorted(v)) for k, v in near.items()}
        return b._near

    def _ear_masks(self):
        """The ear each side: (its points, the ones where it joins the head). The ear is what MakeHuman's "ear-wing"
        target swings out from the head: the flap itself and nothing of the skull (its scale and trans targets take
        a plate of skull along, which ploughs a ridge when moved far)."""
        b = self.base
        if not hasattr(b, "_ears"):
            near = self._adjacent()
            b._ears = {}
            for side in "lr":
                size = np.zeros(len(b.verts))
                for way in ("incr", "decr"):
                    idx, d = b.target(side + "-ear-wing-" + way)
                    size[idx] = np.maximum(size[idx], np.linalg.norm(d, axis=1))
                ear = np.nonzero(size > size.max() * EAR_FROM)[0]     # the flap, not the skin it grows from
                inside = set(ear.tolist())
                root = np.array([i for i in ear if any(int(n) not in inside for n in near.get(int(i), ()))])
                b._ears[side] = (ear, root)
        return b._ears

    def _normals(self, P):
        b = self.base
        if not hasattr(b, "_tris"):
            tris = []
            for group, vi, _ti in b.faces:
                if group == "body":
                    for k in range(1, len(vi) - 1):
                        tris.append((vi[0], vi[k], vi[k + 1]))
            b._tris = np.array(tris)
        t = b._tris
        n = np.zeros_like(P)
        face = np.cross(P[t[:, 1]] - P[t[:, 0]], P[t[:, 2]] - P[t[:, 0]])
        for k in range(3):
            np.add.at(n, t[:, k], face)
        return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)

    def _move_ears(self, P0):
        """The ears cut out, resized and moved as rigid pieces. The skin round each slides with it ALONG the head's
        surface as it was (every moved point is set back onto that surface), fading out a few centimetres away,
        sooner in front of the ear than behind: the skull and face keep their shape."""
        P = P0.copy()
        e = self.ears
        n0 = self._normals(P0)
        body = self.base.indices("body")
        for side, (ear, root) in self._ear_masks().items():
            out = 1.0 if side == "l" else -1.0
            shift = np.array([out * e.get("out", 0.0), e.get("back", 0.0), -e.get("down", 0.0)]) * 0.01
            slide = np.array([0.0, shift[1], shift[2]])
            c = P0[root].mean(axis=0)
            skin = np.setdiff1d(body[np.linalg.norm(P0[body] - c, axis=1) < 0.12], ear)   # the head's side, no ear

            # the head's surface as it was, without the ear and with the ear's footprint capped: what slid skin and
            # the ear's join are set back onto, exactly (the nearest point of its triangles, not of its points)
            from mathutils.bvhtree import BVHTree
            in_ear = np.zeros(len(P0), dtype=bool)
            in_ear[ear] = True
            is_root = np.zeros(len(P0), dtype=bool)
            is_root[root] = True
            keep = in_ear[self.base._tris].sum(axis=1) == 0
            near_c = np.linalg.norm(P0[self.base._tris[:, 0]] - c, axis=1) < 0.14
            verts = [tuple(v) for v in P0] + [tuple(c)]
            polys = [tuple(int(i) for i in t) for t in self.base._tris[keep & near_c]]
            for t in self.base._tris[in_ear[self.base._tris].any(axis=1)]:      # the cap over the footprint
                rim = [int(i) for i in t if is_root[i] or not in_ear[i]]
                if len(rim) >= 2:
                    polys.append((rim[0], rim[1], len(P0)))
            tree = BVHTree.FromPolygons(verts, polys)

            def onto(q):
                return np.array([tuple(tree.find_nearest(tuple(x))[0]) for x in q])

            dist = np.sqrt(((P0[skin][:, None, :] - P0[root][None, :, :]) ** 2).sum(axis=2)).min(axis=1)
            away = P0[skin] - c
            ahead = (away * slide).sum(axis=1) / np.maximum(np.linalg.norm(away, axis=1) * np.linalg.norm(slide), 1e-9)
            if e.get("reach", 0.0) > 0:                    # optional: skin sliding with the ear (0 = the ear alone)
                reach = (e.get("reach_front", 0.0) + (e["reach"] - e.get("reach_front", 0.0)) * (ahead + 1) / 2) * 0.01
                t = np.clip(dist / np.maximum(reach, 1e-6), 0, 1)
                f = 1 - t * t * (3 - 2 * t)
                P[skin] = onto(P0[skin] + slide * f[:, None])
            where = onto(P0[root] + slide)                 # the join carried to its new place on the skull
            carry = (where - P0[root]).mean(axis=0)
            mid = P0[ear].mean(axis=0)
            P[ear] = mid + (P0[ear] - mid) * e.get("scale", 1.0) + carry + np.array([shift[0], 0.0, 0.0])
        return P

    def _jawline(self, P):
        b = self.base
        if not hasattr(b, "_tris"):
            tris = []
            for group, vi, _ti in b.faces:
                if group == "body":
                    for k in range(1, len(vi) - 1):
                        tris.append((vi[0], vi[k], vi[k + 1]))
            b._tris = np.array(tris)
            idx, d = b.target("chin-prominent-incr")
            b._chin = int(idx[np.argmax(np.linalg.norm(d, axis=1) - 100 * np.abs(b.verts[idx, 0]))])
        t = b._tris
        n = np.zeros_like(P)
        face = np.cross(P[t[:, 1]] - P[t[:, 0]], P[t[:, 2]] - P[t[:, 0]])
        for k in range(3):
            np.add.at(n, t[:, k], face)
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        if n[b._chin][1] > 0:                             # out of the skin: the chin's own points away from the head
            n = -n
        body = b.indices("body")
        chin = P[b._chin]
        high = P[body][:, 2].max() - chin[2]
        path = np.array(self.jawline["path"], dtype=float)
        back = (P[body][:, 1] - chin[1]) / high
        up = (P[body][:, 2] - chin[2]) / high
        line = np.interp(back, path[:, 0], path[:, 1])     # the edge's height at each point's distance back
        under = line - up                                  # > 0 just under the edge
        width = self.jawline.get("width", 0.05)
        along = np.clip((back - 0.03) / 0.10, 0, 1) * (back <= path[-1, 0] + 0.02)   # nothing at the chin's front
        cut = np.exp(-((under - width * 0.8) / width) ** 2) * along * (under > -width * 0.3)
        lip = np.exp(-((under + width * 0.5) / (width * 0.6)) ** 2) * along
        move = (lip * self.jawline.get("lip", 0.0) - cut * self.jawline.get("depth", 0.6)) * 0.01
        P = P.copy()
        P[body] += n[body] * move[:, None]
        return P

    def _smooth(self, pts):
        b = self.base
        if not hasattr(b, "_near"):                      # which points share an edge, once
            near = {}
            for _group, vi, _ti in b.faces:
                for i in range(len(vi)):
                    a, c = vi[i], vi[(i + 1) % len(vi)]
                    near.setdefault(a, set()).add(c)
                    near.setdefault(c, set()).add(a)
            b._near = {k: np.array(sorted(v)) for k, v in near.items()}
        for patch in self.smooth:
            centres = []
            if patch["at"] == "nipples":
                idx, d = b.target("nipple-point-incr")
                size = np.linalg.norm(d, axis=1)
                x = b.verts[idx, 0]
                centres = [int(idx[np.argmax(np.where(x > 0, size, -1))]), int(idx[np.argmax(np.where(x < 0, size, -1))])]
            radius = patch.get("radius", 2.5) * 0.1      # decimetres here
            body = b.indices("body")
            for c in centres:
                dist = np.linalg.norm(pts[body] - pts[c], axis=1)
                ring = body[dist < radius]
                w = np.cos(dist[dist < radius] / radius * np.pi / 2) ** 2       # full at the middle, none at the rim
                for _ in range(int(patch.get("passes", 20))):
                    mean = np.array([pts[b._near[i]].mean(axis=0) for i in ring])
                    pts[ring] += (mean - pts[ring]) * w[:, None]

    # --- targets -----------------------------------------------------------------------------------------
    def _macro(self, pts):
        race, gender, age, muscle, weight, height, prop = macro_parts(self.macro)
        b = self.base

        def add(name, w):
            if w > 1e-6 and b.has(name):
                idx, d = b.target(name)
                pts[idx] += d * w

        for r, rw in race.items():
            for g, gw in gender.items():
                for a, aw in age.items():
                    add("macrodetails/%s-%s-%s" % (r, g, a), rw * gw * aw)
        for g, gw in gender.items():
            for a, aw in age.items():
                for m, mw in muscle.items():
                    for w, ww in weight.items():
                        k = gw * aw * mw * ww
                        add("macrodetails/universal-%s-%s-%s-%s" % (g, a, m, w), k)
                        for h, hw in height.items():
                            add("macrodetails/height/%s-%s-%s-%s-%s" % (g, a, m, w, h), k * hw)
                        for p, pw in prop.items():
                            add("macrodetails/proportions/%s-%s-%s-%s-%s" % (g, a, m, w, p), k * pw)

    def _expand(self):
        """The values as {target file: weight}."""
        b = self.base
        out = {}
        for name, value in self.targets.items():
            side = ""
            m = re.match(r"^(.*)\.([lr])$", name)
            if m:
                name, side = m.group(1), m.group(2)
            for control in ALIASES.get(name, [name]):
                if control not in b.controls:
                    raise KeyError("no such control: %s" % control)
                c = b.controls[control]
                end = c["pos"] if value >= 0 else c["neg"]
                if not end and value < 0:      # a one-way slider pushed backwards: the same target, negative
                    end, mag = c["pos"], value
                else:
                    mag = abs(value)
                for s, target in end.items():
                    if side and s and s != side:
                        continue
                    out[target] = out.get(target, 0.0) + mag
        for name, value in self.raw.items():
            out[name] = out.get(name, 0.0) + value
        return out

    # --- skeleton ----------------------------------------------------------------------------------------
    def _joints(self, pts):
        b = self.base
        heads, tails = {}, {}
        for bone in b.bones:
            for end, store in (("head", heads), ("tail", tails)):
                e = b.rig[bone][end]
                if e["strategy"] == "CUBE":
                    store[bone] = pts[b.indices(e["cube_name"])].mean(axis=0)
                else:
                    store[bone] = pts[np.array(e["vertex_indices"])].mean(axis=0)
        return heads, tails

    @staticmethod
    def _frame(head, tail):
        y = tail - head
        n = np.linalg.norm(y)
        y = y / n if n > 1e-9 else np.array([0.0, 1.0, 0.0])
        front = np.array([0.0, 0.0, 1.0])
        z = front - y * front.dot(y)
        if np.linalg.norm(z) < 0.2:           # a bone pointing at the viewer (the foot): depth is up-down
            up = np.array([0.0, 1.0, 0.0])
            z = up - y * up.dot(y)
        z /= np.linalg.norm(z)
        x = np.cross(y, z)
        return np.stack([x, y, z], axis=1)     # columns: across, along, depth

    def _bone_scales(self):
        scales = {b: np.ones(3) for b in self.base.bones}
        flesh = {b: np.ones(3) for b in self.base.bones}
        for key, factor in self.bones.items():
            name, what = key.rsplit(".", 1)
            into = flesh if what in FLESH else scales
            mask = np.array(FLESH[what] if what in FLESH else WHAT[what], dtype=float)
            for bone in BONE_SETS.get(name, [name]):
                if bone not in scales:
                    raise KeyError("no such bone: %s" % bone)
                into[bone] *= np.where(mask > 0, factor, 1.0)
        return scales, flesh

    def solve(self):
        b = self.base
        pts = b.verts.copy()
        self._macro(pts)
        for name, w in self._expand().items():
            idx, d = b.target(name)
            pts[idx] += d * w
        heads, tails = self._joints(pts)
        scales, flesh = self._bone_scales()
        if any(np.any(np.abs(s - 1) > 1e-9) for s in list(scales.values()) + list(flesh.values())):
            out = np.zeros_like(pts)
            new_heads, new_tails, mats, skins = {}, {}, {}, {}
            for bone in b.bones:
                parent = b.rig[bone]["parent"]
                h = heads[bone]
                if parent:
                    hp, Sp, Hp = mats[parent]
                    H = Hp + Sp.dot(h - hp)
                else:
                    H = h.copy()
                R = self._frame(h, tails[bone])
                S = R.dot(np.diag(scales[bone])).dot(R.T)
                mats[bone] = (h, S, H)
                skins[bone] = R.dot(np.diag(scales[bone] * flesh[bone])).dot(R.T)
                new_heads[bone] = H
                new_tails[bone] = H + S.dot(tails[bone] - h)
            for i, bone in enumerate(b.bones):
                w = b.weights[:, i]
                idx = np.nonzero(w)[0]
                if len(idx):
                    h, _S, H = mats[bone]
                    out[idx] += w[idx, None] * (H + (pts[idx] - h).dot(skins[bone].T))
            none = b.weights.sum(axis=1) == 0
            out[none] = pts[none]
            pts, heads, tails = out, new_heads, new_tails
        if self.smooth:
            self._smooth(pts)
        self.points, self.heads, self.tails = pts, heads, tails
        return pts

    # --- out ---------------------------------------------------------------------------------------------
    def to_blender(self):
        """(points, heads, tails) in metres, z up, facing -y, standing on z = 0, scaled to `height` if set."""
        if not hasattr(self, "points"):
            self.solve()
        body = self.points[self.base.indices("body")]
        floor = body[:, 1].min()
        k = 0.1
        if self.height:
            k = self.height / (body[:, 1].max() - floor)

        def turn(p):
            p = np.atleast_2d(p)
            return np.stack([p[:, 0], -p[:, 2], p[:, 1] - floor], axis=1) * k

        P, H, T = turn(self.points), {b: turn(v)[0] for b, v in self.heads.items()}, \
            {b: turn(v)[0] for b, v in self.tails.items()}
        if self.jawline:
            P = self._jawline(P)
        if self.ears:
            P = self._move_ears(P)
        tuck = self.posture.get("pelvis_tuck", 0.0)
        if tuck:
            turns = {"pelvis": (-tuck, 0, 0), "spine_01": (tuck, 0, 0), "thigh_l": (tuck, 0, 0), "thigh_r": (tuck, 0, 0)}
            P, posed = pose_points(self, P, H, turns, T)
            H = {b: posed[b] for b in H}
            T = {b: posed["tail:" + b] for b in T}
            lift = np.array([0.0, 0.0, P[self.base.indices("body")][:, 2].min()])
            P, H, T = P - lift, {b: v - lift for b, v in H.items()}, {b: v - lift for b, v in T.items()}
        return P, H, T

    def measures(self):
        """A few lengths of the solved figure in head-heights and metres (for fitting to a drawing)."""
        P, H, T = self.to_blender()
        body = P[self.base.indices("body")]
        out = {"height": float(body[:, 2].max())}
        for name, a, bb in (("thigh", "thigh_l", "calf_l"), ("shin", "calf_l", "foot_l"),
                            ("upper_arm", "upperarm_l", "lowerarm_l"), ("forearm", "lowerarm_l", "hand_l")):
            out[name] = float(np.linalg.norm(H[a] - H[bb]))
        out["shoulders"] = float(abs(H["upperarm_l"][0] - H["upperarm_r"][0]))
        out["hip_joints"] = float(abs(H["thigh_l"][0] - H["thigh_r"][0]))
        out["crotch"] = float((H["thigh_l"][2] + H["thigh_r"][2]) / 2)
        out["chin"] = float(H["head"][2])
        return out


def load_spec(path):
    return _json(path)
