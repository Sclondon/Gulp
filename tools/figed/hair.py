"""Hair for a figure: pieces of their own that sit on the bare head (the base model stays bald and shaven).

    blender -b --factory-startup --python tools/figed/hair.py -- <spec.json> <out.png> [--wear hair,moustache]
            [--glb <head_with_hair.glb>] [--style <style.json>]

THE HAIR IS DRAWN BY A HAIR SHADER, NOT MODELLED (the user, 2026-11-18: "Dont try to model the beard it should be made
with a hair shader"; 2026-11-20, of a first pass here that modelled curl clumps and painted locks on them: "Why did
you do if you know I said not to for the hair?"; then of a smooth dome with a curl pattern drawn on it: "His mustache
and hair doesn't even look remotely like the art"). So this makes only plain CARRIERS, all by rule from a table of
numbers (a "style": STYLES below), never shaped by hand, and `shaders/hair_stylised.gdshader` draws the hair on them
(`tests/figed_hair_view.gd` shows it in Godot). The pictures this script renders itself are plain colour: shape only.

What it makes (tools/figed/README.md, "Hair as locks", has the decision record and how to make a new style):
- `hair_cap`: the scalp's own faces inside the hairline rule, pushed out to most of the mop's thickness: the dark
  inside of the hair, seen only between the locks.
- `hair_locks`: about a hundred identical plain strips ("lock carriers"), each rooted on the scalp and laid along a
  flow over the head (away from the crown's whorl, down with gravity, swept to one side on top, each wandering and
  waving its own way), floating at the style's thickness over the skin, arched across. The shader cuts each strip to a
  lock's outline, draws it as a few waving ribbons with pointed ends, and can wave and lift it further.
  UV = (along the lock 0 root .. 1 tip, across 0..1); UV2 = (metres along, a number 0..1 of the lock's own);
  vertex colour rgb = the sideways direction across the lock (0.5 + 0.5 * unit vector, model space), a = how deep the
  lock lies (1 outermost).
- `moustache`: the skin between the nose and the upper lip, out past the corners of the mouth, pushed out a little: a
  thin dark shape under `moustache_locks`, three broad strips a side from under the nose out along the lip and down
  past the corner of the mouth, standing off the skin (the moustache's body).
- `stubble` (only when asked for in `wear`): the skin of the jaw, chin, upper lip and in front of the ears, a hair's
  breadth off it; the shader draws only short hairs of it. UV.x = how thick it grows there; UV2 = metres over the skin.
Everything is worked out on the figure at rest and carried into the pose by the head's own turn and move.
Every number is Claude's pick.
"""
import json
import math
import os
import sys

import bpy
import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import figed  # noqa: E402
import figed_fit  # noqa: E402
import garments as G  # noqa: E402

SIZE = 1024
# the hairline: degrees round the head from the front -> height over the eye line (shares of eye-to-crown where
# under 1 in size and marked "s", else metres)
LINE_A = [0, 35, 55, 72, 95, 125, 180]
LINE_S = [0.60, 0.52, 0.22, 0.0, 0.0, 0.0, 0.0]            # share of eye-to-crown
LINE_M = [0.0, 0.0, 0.0, -0.035, -0.015, -0.075, -0.085]   # plus metres
HAIR = ((0.20, 0.105, 0.06), (0.34, 0.185, 0.10), (0.52, 0.30, 0.16))   # crease, strand, light (amber)
TACHE = ((0.40, 0.17, 0.07), (0.60, 0.29, 0.13), (0.74, 0.42, 0.20))    # ginger: redder than his hair

# A STYLE: everything that makes one head of hair, as numbers. Angles round the head ("a") run 0 at the front to 180
# at the back; heights ("e") are shares of eye-to-crown over the eye line (1 the crown, 0 the eyes, under 0 below).
STYLES = {
    "mop": {                                              # the older brother's tousled mop of curls
        "seed": 7,
        "spacing": 0.018,                                 # metres between lock roots (fewer, bigger locks: raise it)
        "width": (0.056, 0.076),                          # a lock carrier's width, narrowest and widest
        "arch": 0.26,                                     # how far a carrier's edges tuck in, as a share of its width
        "segments": 10,                                    # pieces along a carrier
        "across": 4,                                      # pieces across it
        # how thick the hair stands off the skin (metres): rows by height e, columns by angle a
        "volume_e": [-0.7, -0.3, 0.1, 0.5, 1.0],
        "volume_a": [0, 45, 90, 135, 180],
        "volume": [[0.008, 0.010, 0.018, 0.018, 0.018],
                   [0.012, 0.020, 0.036, 0.034, 0.030],
                   [0.018, 0.034, 0.050, 0.048, 0.044],
                   [0.032, 0.052, 0.058, 0.054, 0.052],
                   [0.062, 0.062, 0.060, 0.056, 0.054]],
        "cap": 0.72,                                      # the dark cap under the locks, as a share of that
        # how long a lock is by its root's height e (metres), shorter at the front by `front_length`, each its own
        # by `length_vary`
        "length_e": [-0.4, 0.0, 0.4, 0.8],
        "length": [0.06, 0.09, 0.115, 0.13],
        "front_length": 1.0,
        "length_vary": (0.8, 1.15),
        # where the hair stops (a lock is cut off below this): angle a -> height e, plus metres
        "floor_a": [0, 30, 55, 75, 100, 180],
        "floor_e": [0.17, 0.15, 0.05, 0.0, 0.0, 0.0],
        "floor_m": [0.0, 0.0, 0.0, -0.012, -0.06, -0.095],
        "floor_vary": 0.014,
        "round": 0.55,                                     # how round a lock is lit across (0 flat, 1 a tube)
        # the flow the locks lie along
        "crown": (0.012, 0.045),                          # the whorl: metres to his left of the middle, and behind it
        "swirl": 80.0,                                    # degrees the flow is turned at the whorl (fading by 6 cm)
        "gravity": 0.7,                                   # how much the flow falls rather than runs from the whorl
        "sweep": 0.8,                                     # the top front swept to his left (+) or right (-)
        "part": (-0.012, 0.5),                            # the fringe parts here (metres to his left of the middle) and
                                                          # falls away to each side this strongly (0: straight down)
        "wander": 9.0,                                   # degrees each lock leaves the flow, its own way
        "curl": 26.0,                                     # degrees a lock swings either side as it runs (its S)
        "wavelength": 0.10,
        "together": 0.88,                                 # how far neighbouring locks wave in step (0 each its own, 1 all)                              # metres to one whole S
        "hook": 110.0,                                     # degrees the tip turns in the last third
        # how a lock rides: its root sunk in the cap, lifting over its middle, its tip flicked out
        "root_sink": 0.8,
        "smooth": 2,
        "shortest": 0.04,                                 # no lock shorter than this (metres)
        "lift": 0.014,
        "flick": 0.02,
        "stand": 0.022,                                   # the most a lock may stand off the mass (metres)
        "layers": 0.011,                                  # locks stand at slightly different heights (no two flat together)
    },
}
TACHE_STYLE = {
    "thick": (0.002, 0.004),                              # the dark under-shape's thickness at its edge, and in its middle
    "past": 0.017,                                        # how far its ends run past the corners of the mouth
    "droop": 0.013,                                       # how far below the corner of the mouth its ends hang
    "over_lip": 0.014,                                    # how far its lower edge comes down over the upper lip
    # the carriers on each side: (starts, ends: shares of the way from the middle to the end; how far down the shape
    # it lies, 0 its top .. 1 its lower edge; its width as a share of the shape's height there; how far it stands off
    # the skin, metres)
    "strips": [(0.0, 1.0, 0.5, 1.3, 0.0075), (0.0, 0.62, 0.34, 0.8, 0.0105), (0.12, 0.86, 0.66, 0.7, 0.0095)],
    "segments": 9,
    "arch": 0.3,
}

STUBBLE = {
    # the beard line: degrees round from the front -> its top, as metres over the corner of the mouth (the last two
    # are the sideburn in front of the ear, up to the hair)
    "top_a": [0, 22, 42, 56, 64, 80],
    "top_m": [0.026, 0.012, 0.022, 0.036, 0.085, 0.085],
    # ... and its lower edge under the jaw
    "low_a": [0, 45, 70, 80],
    "low_m": [-0.068, -0.062, -0.04, -0.02],
    "ends": 80.0,                                         # degrees round: it stops in front of the ear
    "fade": 0.012,                                        # metres over which it thins out at its edges
    "sideburn": 2.0,                                      # how much thicker it grows in front of the ear
    "off": 0.0012,                                        # metres off the skin
}

INFO = {}


def _biggest(mesh):
    """Only the largest joined piece of a mesh is kept (stray flecks cut off by a fold of skin go)."""
    bm = bmesh.new()
    bm.from_mesh(mesh)
    left, best = set(bm.verts), []
    while left:
        grp, todo = set(), [next(iter(left))]
        while todo:
            v = todo.pop()
            if v in grp:
                continue
            grp.add(v)
            todo.extend(e.other_vert(v) for e in v.link_edges)
        left -= grp
        if len(grp) > len(best):
            best = grp
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if v not in best], context="VERTS")
    bm.to_mesh(mesh)
    bm.free()


def landmarks(fig, P):
    base = fig.base
    z = P[:, 2]
    headw = G._w(base, ("head",))
    eye = (P[base.indices("helper-l-eye")].mean(axis=0) + P[base.indices("helper-r-eye")].mean(axis=0)) / 2
    crown = float(z[headw > 0.8].max())
    idx, d = base.target("mouth-scale-horiz-incr")
    size = np.linalg.norm(d, axis=1)
    corner = P[int(idx[np.argmax(np.where(P[idx, 0] > 0, size, -1))])]
    idx, d = base.target("mouth-philtrum-volume-incr")
    mid = idx[np.abs(P[idx, 0]) < 0.006]
    L = {"eye": eye, "crown": crown, "corner": corner, "nose_base": float(P[mid, 2].max()),
         "lip_top": float(P[mid, 2].min())}
    print("landmarks: eye z %.3f crown %.3f mouth corner x %.3f z %.3f nose base %.3f lip top %.3f"
          % (eye[2], crown, corner[0], corner[2], L["nose_base"], L["lip_top"]))
    return L


class Head:
    """Where things are on this head: the angle round it and the height up it of any point, the skin to lie on."""

    def __init__(self, fig, P, Pp, H):
        # (everything is worked out on the figure at rest, where the rules are written, and carried into the pose
        # by the head's own turn and move at the end: self.move, self.turn)
        base = fig.base
        self.L = landmarks(fig, P)
        self.eye = self.L["eye"]
        self.span = self.L["crown"] - self.eye[2]
        headw = G._w(base, ("head",))
        self.headw = headw
        self.yc = H["head"][1]
        self.xc = float(self.eye[0])
        hard = headw > 0.95
        ca, cb = P[hard].mean(axis=0), Pp[hard].mean(axis=0)
        U, _S, Vt = np.linalg.svd((P[hard] - ca).T.dot(Pp[hard] - cb))
        d = np.sign(np.linalg.det(Vt.T.dot(U.T)))
        R = Vt.T.dot(np.diag([1.0, 1.0, d])).dot(U.T)
        self.move = lambda q: (np.asarray(q) - ca).dot(R.T) + cb
        self.turn = lambda q: np.asarray(q).dot(R.T)
        Pp = P
        ears = np.zeros(len(P), dtype=bool)
        for _side, masks in fig._ear_masks().items():
            ears[np.asarray(masks[0], dtype=int)] = True
        self.ears = ears
        near = Pp[:, 2] > self.eye[2] - 0.22
        polys = [vi for group, vi, _ti in base.faces
                 if group == "body" and all(near[v] for v in vi) and not any(ears[v] for v in vi)]
        self.polys = polys
        self.bvh = BVHTree.FromPolygons([tuple(q) for q in Pp], polys, all_triangles=False)
        self.Pp = Pp

    def a(self, p):
        return math.degrees(abs(math.atan2(p[0] - self.xc, -(p[1] - self.yc))))

    def e(self, p):
        return (p[2] - self.eye[2]) / self.span

    def near(self, p):
        """(the skin's nearest point, the direction out from it to p, the distance)."""
        q, n, _i, d = self.bvh.find_nearest(Vector(p))
        q, n = np.array(q), np.array(n)
        if d > 1e-5:
            out = (np.array(p) - q) / d
            if out.dot(n) < -0.2:                         # (p got inside the skin)
                out, d = n, -d
        else:
            out = n
        return q, out, d


def _table(S, name, a, e):
    A, E, T = S[name + "_a"], S[name + "_e"], np.array(S[name])
    return float(np.interp(a, A, [np.interp(e, E, T[:, j]) for j in range(len(A))]))


def rules(fig, P, H):
    base = fig.base
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    L = landmarks(fig, P)
    headw = G._w(base, ("head",))
    ears = np.zeros(len(P), dtype=bool)
    for _side, masks in fig._ear_masks().items():
        ears[np.asarray(masks[0], dtype=int)] = True
    eye = L["eye"]
    span = L["crown"] - eye[2]
    yc = H["head"][1]
    a = np.degrees(np.abs(np.arctan2(x, -(y - yc))))
    line = eye[2] + np.interp(a, LINE_A, LINE_S) * span + np.interp(a, LINE_A, LINE_M)
    f = z - line
    out = {"hair": (f, (headw > 0.5) & ~ears, None)}
    T = TACHE_STYLE
    top, bot, xe = tache_edges(L, x)
    fm = np.minimum(np.minimum(top - z, z - bot), (xe - np.abs(x)) * 0.6) - 0.0015
    out["moustache"] = (fm, (headw > 0.5) & (y < eye[1] + 0.03),
                        T["thick"][0] + (T["thick"][1] - T["thick"][0]) * np.clip(fm / 0.007, 0, 1) ** 0.7)
    # the stubble: jaw, chin, upper lip and the sideburns, never the lips themselves
    B = STUBBLE
    zc = L["corner"][2]
    fs = np.minimum(zc + np.interp(a, B["top_a"], B["top_m"]) - z, z - (zc + np.interp(a, B["low_a"], B["low_m"])))
    fs = np.minimum(fs, (B["ends"] - a) * 0.0012)
    lips = np.minimum(np.minimum(abs(L["corner"][0]) + 0.004 - np.abs(x), (L["lip_top"] + 0.001) - z), z - (zc - 0.02))
    fs = np.minimum(fs, -lips)
    out["stubble"] = (fs, (headw > 0.3) & ~ears & (y < yc + 0.02), np.full(len(P), B["off"]))
    INFO.update(top=top, bot=bot, yc=yc, xe=xe)
    return out, L


def _uv_layers(bm):
    """(UV, UV2, colour) of a bmesh: all made first, then looked up (making one moves the others)."""
    if bm.loops.layers.uv.get("UVMap") is None:
        bm.loops.layers.uv.new("UVMap")
    if bm.loops.layers.uv.get("UV2") is None:
        bm.loops.layers.uv.new("UV2")
    if bm.loops.layers.color.get("Col") is None:
        bm.loops.layers.color.new("Col")
    return bm.loops.layers.uv.get("UVMap"), bm.loops.layers.uv.get("UV2"), bm.loops.layers.color.get("Col")


def carrier_material(name, col):
    """A plain colour for Blender's own pictures, with the vertex colour wired in so that the glTF exporter keeps it
    (it only writes a colour attribute the material uses)."""
    mat = G.plain_material(name, col)
    tree = mat.node_tree
    bsdf = next(n for n in tree.nodes if n.type == "BSDF_PRINCIPLED")
    tex = tree.nodes.active
    attr = tree.nodes.new("ShaderNodeVertexColor")
    attr.layer_name = "Col"
    mix = tree.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = 1.0
    tree.links.new(tex.outputs["Color"], mix.inputs[6])
    tree.links.new(attr.outputs["Color"], mix.inputs[7])
    tree.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    tree.links.new(attr.outputs["Alpha"], bsdf.inputs["Alpha"])
    tree.nodes.active = tex
    return mat


def cap(mesh, head, S):
    """The cut scalp made the hair's dark inside: closed down to the skin at its edge, with coordinates."""
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.normal_update()
    B = np.array([v.co[:] for v in bm.verts if v.is_boundary])
    edge_d = {v: float(np.linalg.norm(B - np.array(v.co[:]), axis=1).min()) for v in bm.verts}
    rim = [e for e in bm.edges if e.is_boundary]
    made = bmesh.ops.extrude_edge_only(bm, edges=rim)["geom"]
    for v in [g for g in made if isinstance(g, bmesh.types.BMVert)]:
        q, n, _d = head.near(np.array(v.co[:]))
        v.co = q - n * 0.002
        edge_d[v] = 0.0
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    uv, uv2, col = _uv_layers(bm)
    for face in bm.faces:
        face.smooth = True
        for loop in face.loops:
            d = edge_d[loop.vert]
            p = loop.vert.co
            a = math.atan2(p.x - head.xc, -(p.y - head.yc))
            loop[uv].uv = (max(0.02, 1.0 - min(1.0, d / 0.14)), a / (2 * math.pi) + 0.5)
            loop[uv2].uv = (d, 0.5)
            loop[col] = (0.5, 0.5, 1.0, 1.0)
    bm.to_mesh(mesh)
    bm.free()


def _unit(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


def _turn(v, axis, deg):
    """v turned about a unit axis."""
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return v * c + np.cross(axis, v) * s + axis * axis.dot(v) * (1 - c)


def _strip(bm, layers, pts, outs, s_at, width, arch, across, number, depth, taper=None, lit_round=0.4, flip=False):
    """One carrier: a strip along `pts` (its middle line), `outs` the way out of the head at each, arched across."""
    uv, uv2, col = layers
    n = len(pts)
    length = s_at[-1]
    rows = []
    normals = []
    for i in range(n):
        tan = _unit(pts[min(n - 1, i + 1)] - pts[max(0, i - 1)])
        side = _unit(np.cross(outs[i], tan))
        out = _unit(np.cross(tan, side))
        side = side * (-1.0 if flip else 1.0)             # (a mirrored strip keeps UV.y 0 on the same edge as its twin)
        w = width if taper is None else width * taper(s_at[i] / length)
        row = []
        for j in range(across + 1):
            u = j / float(across) * 2.0 - 1.0
            p = pts[i] + side * (u * w / 2) - out * (u * u * arch * w)
            row.append(bm.verts.new(tuple(p)))
            normals.append(_unit(out + side * u * lit_round))
        rows.append((row, side))
    for i in range(n - 1):
        for j in range(across):
            order = ((i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j))
            order = order if flip else order[::-1]          # (wound so the outside is the front face)
            face = bm.faces.new([rows[ii][0][jj] for ii, jj in order])
            face.smooth = True
            for loop, (ii, jj) in zip(face.loops, order):
                side = rows[ii][1]
                loop[uv].uv = (min(1.0, max(0.004, s_at[ii] / length)), jj / float(across))
                loop[uv2].uv = (s_at[ii], number)
                loop[col] = (0.5 + 0.5 * side[0], 0.5 + 0.5 * side[1], 0.5 + 0.5 * side[2], depth)
    return normals


def locks(head, roots, S, rng):
    """The lock carriers of a style, as one mesh."""
    bm = bmesh.new()
    layers = _uv_layers(bm)
    crown_q, _n, _d = head.near((head.xc + S["crown"][0], head.yc + S["crown"][1], head.eye[2] + head.span + 0.1))
    N = S["segments"]
    normals = []
    count = 0
    for root in roots:
        number = float(rng.random())
        a0, e0 = head.a(root), head.e(root)
        length = float(np.interp(e0, S["length_e"], S["length"])) * rng.uniform(*S["length_vary"])
        if a0 < 50:
            length *= S["front_length"] + (1 - S["front_length"]) * a0 / 50.0
        width = rng.uniform(*S["width"])
        wander = rng.normal(0, S["wander"])
        phase = rng.uniform(0, 2 * math.pi) * (1 - S["together"]) + S["together"] * (
            3.0 * math.sin(root[0] * 40.0) + 3.0 * math.cos(root[2] * 35.0 + root[1] * 30.0))
        hook = S["hook"] * rng.choice((-1.0, 1.0)) * rng.uniform(0.4, 1.0)
        lift = S["lift"] * rng.uniform(0.4, 1.3)
        flick = S["flick"] * rng.uniform(-0.2, 1.3)
        layer = S["layers"] * rng.uniform(-1, 1)
        floor_vary = S["floor_vary"] * rng.uniform(-1, 1)

        def run(length, to_floor):
            """One middle line of this lock, `length` long; cut off at the floor of the hair if to_floor."""
            ds = length / N

            def height(p, t):
                vol = _table(S, "volume", head.a(p), head.e(p))
                rise = min(1.0, t / 0.22)
                rise = rise * rise * (3 - 2 * rise)
                # (what a lock adds of its own is held to `stand`: a tip never floats far off the mass)
                own = layer * rise + lift * math.sin(math.pi * min(1.0, t * 1.15)) + flick * t ** 3
                return max(0.004, vol * (S["root_sink"] + (1 - S["root_sink"]) * rise) + min(S["stand"], own))

            q, n, _d = head.near(root)
            p = q + n * height(q, 0.0)
            pts, outs, s_at = [], [], []
            s = 0.0
            prev_d = None
            for i in range(N + 1):
                q, n, _d = head.near(p)
                pts.append(p)
                outs.append(n)
                s_at.append(s)
                if i == N:
                    break
                t = s / length
                rad = p - crown_q
                dist = np.linalg.norm(rad)
                rad = rad - n * rad.dot(n)
                if np.linalg.norm(rad) < 1e-4:
                    rad = np.array([math.cos(phase), math.sin(phase), 0.0])
                rad = _turn(_unit(rad), n, S["swirl"] * math.exp(-dist / 0.06))
                grav = np.array([0.0, 0.0, -1.0])
                grav = grav - n * grav.dot(n)
                a, e = head.a(p), head.e(p)
                sw = S["sweep"] * min(1.0, max(0.0, (e - 0.72) / 0.2)) * min(1.0, max(0.0, (100 - a) / 50.0))
                side = np.array([1.0, 0.0, 0.0])
                side = side - n * side.dot(n)
                fr = S["part"][1] * min(1.0, max(0.0, (32 - a) / 20.0)) * min(1.0, max(0.0, (0.8 - e) / 0.2))
                fr *= 1.0 if p[0] - head.xc > S["part"][0] else -1.0
                d = _unit(rad + grav * S["gravity"] + side * (sw + fr))
                d = _turn(d, n, wander + S["curl"] * math.sin(2 * math.pi * s / S["wavelength"] + phase)
                          + hook * max(0.0, (t - 0.55) / 0.45) ** 2)
                if prev_d is not None and d.dot(prev_d) < 0.0:   # (never doubling back on itself)
                    d = _unit(d + prev_d * 1.2)
                prev_d = d
                p2 = p + d * ds
                q2, n2, _d2 = head.near(p2)
                p2 = q2 + n2 * height(p2, (s + ds) / length)
                floor = head.eye[2] + np.interp(head.a(p2), S["floor_a"], S["floor_e"]) * head.span \
                    + np.interp(head.a(p2), S["floor_a"], S["floor_m"]) + floor_vary
                if to_floor and p2[2] < floor:
                    break
                s += float(np.linalg.norm(p2 - p))
                p = p2
            return pts, outs, s_at, len(pts) < N + 1

        pts, outs, s_at, cut = run(length, True)
        if cut:
            # a lock that would cross the floor of the hair is made again only as long as the way there, so it
            # ends in its own curl and point instead of being chopped off straight
            pts, outs, s_at, cut = run(max(S["shortest"], s_at[-1]), False)
        if len(pts) < 4:
            continue
        for _ in range(S["smooth"]):                     # (the middle line eased: no corners where the skin turns)
            pts = [pts[0]] + [(pts[i - 1] + 2 * pts[i] + pts[i + 1]) / 4 for i in range(1, len(pts) - 1)] + [pts[-1]]
        depth = min(1.0, max(0.0, 0.5 + layer / (2 * S["layers"]) if S["layers"] > 0 else 1.0))
        normals += _strip(bm, layers, [head.move(q) for q in pts], [head.turn(q) for q in outs], s_at, width,
                          S["arch"], S["across"], number, depth, lit_round=S["round"])
        count += 1
    mesh = bpy.data.meshes.new("hair_locks")
    bm.to_mesh(mesh)
    bm.free()
    mesh.normals_split_custom_set_from_vertices([tuple(n) for n in normals])
    INFO["locks"] = count
    return mesh


def roots_on(head, f, may, spacing, rng, inside=0.004):
    """Points on the skin inside a rule, no two nearer than `spacing` (darts thrown until none fits)."""
    P = head.Pp
    tris = []
    for vi in head.polys:
        if all(may[v] and f[v] > inside for v in vi):
            for k in range(1, len(vi) - 1):
                tris.append((vi[0], vi[k], vi[k + 1]))
    T = np.array(tris)
    A, B, C = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    area = np.linalg.norm(np.cross(B - A, C - A), axis=1) / 2
    want = int(area.sum() / (spacing * spacing) * 6)
    pick = rng.choice(len(T), size=want, p=area / area.sum())
    u, v = rng.random(want), rng.random(want)
    flip = u + v > 1
    u[flip], v[flip] = 1 - u[flip], 1 - v[flip]
    cand = A[pick] + (B[pick] - A[pick]) * u[:, None] + (C[pick] - A[pick]) * v[:, None]
    kept = []
    for c in cand:
        if not kept or np.linalg.norm(np.array(kept) - c, axis=1).min() >= spacing:
            kept.append(c)
    return kept


def stubble_uv(mesh, head):
    """The stubble's coordinates: UV.x how thick it grows (0 at its edges), UV2 metres round the face and up it."""
    B = STUBBLE
    bm = bmesh.new()
    bm.from_mesh(mesh)
    lf = bm.verts.layers.float.get("f")
    uv, uv2, col = _uv_layers(bm)
    for face in bm.faces:
        face.smooth = True
        for loop in face.loops:
            p = loop.vert.co
            a = math.atan2(p.x - head.xc, -(p.y - head.yc))
            thick = min(1.0, max(0.0, loop.vert[lf] / B["fade"]))
            burn = min(1.0, max(0.0, (abs(math.degrees(a)) - 58.0) / 8.0))
            loop[uv].uv = (max(0.004, thick * (1.0 + (B["sideburn"] - 1.0) * burn) / B["sideburn"]), 0.5)
            loop[uv2].uv = (a * 0.085, p.z)
            loop[col] = (0.5, 0.5, 1.0, 1.0)
    bm.to_mesh(mesh)
    bm.free()


def moustache_uv(mesh):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    V = np.array([v.co[:] for v in bm.verts])
    lo, hi = V.min(axis=0), V.max(axis=0)
    mid, half = (lo[0] + hi[0]) / 2, (hi[0] - lo[0]) / 2
    uv, uv2, col = _uv_layers(bm)
    for face in bm.faces:
        face.smooth = True
        for loop in face.loops:
            ax = abs(loop.vert.co.x - mid)
            # (strands run out from the middle and droop to the ends: "across" is measured from that drooping line)
            w = loop.vert.co.z + (hi[2] - lo[2]) * 0.75 * (ax / half) ** 2
            loop[uv].uv = (max(0.02, ax / half), min(1.0, max(0.0, (w - lo[2]) / (hi[2] - lo[2]) * 0.8)))
            loop[uv2].uv = (ax, w - lo[2])
            loop[col] = (0.5, 0.5, 1.0, 0.0)
    bm.to_mesh(mesh)
    bm.free()


def tache_edges(L, ax):
    """(top, bottom) heights of the moustache's full shape at |x| = ax, and how far out it ends."""
    T = TACHE_STYLE
    xe = abs(L["corner"][0]) + T["past"]
    zc = L["corner"][2]
    t = np.clip(np.abs(ax) / xe, 0, 1)
    top = L["nose_base"] - 0.001
    top = top - (top - (zc + 0.004)) * t ** 2.4
    bot = L["lip_top"] - T["over_lip"]
    bot = bot + ((zc - T["droop"]) - bot) * t ** 1.6
    return top, bot, xe


def moustache_locks(head, rng):
    """The moustache's carriers: on each side, broad strips from under the nose out along the lip and down past the
    corner of the mouth, standing off the skin, the widest first and narrower ones over it."""
    T = TACHE_STYLE
    L = head.L
    front = float(head.eye[1]) - 0.2
    bm = bmesh.new()
    layers = _uv_layers(bm)
    normals = []
    for sx in (1.0, -1.0):
        for k, (x0, x1, level, wide, stand) in enumerate(T["strips"]):
            n = T["segments"]
            pts, outs, s_at = [], [], []
            widths = []
            xe = tache_edges(L, 0.0)[2]
            jit = rng.uniform(-0.04, 0.04) if k else 0.0
            for i in range(n + 1):
                t = i / float(n)
                ax = (x0 + (x1 - x0) * t) * xe
                top, bot, _xe = tache_edges(L, ax)
                z = top + (bot - top) * min(0.95, max(0.05, level + jit))
                hit = head.bvh.ray_cast(Vector((head.xc + sx * ax, front, z)), Vector((0, 1, 0)))
                if hit[0] is None:
                    hit = head.bvh.find_nearest(Vector((head.xc + sx * ax, front + 0.1, z)))
                q, nrm = np.array(hit[0]), np.array(hit[1])
                # (the way out: mostly forward, a little with the skin, so the strip does not follow every fold)
                out = _unit(nrm * 0.5 + np.array([sx * 0.5 * (ax / xe), -1.0, 0.0]))
                pts.append(q + out * stand * (1.0 - 0.55 * t * t))
                outs.append(out)
                widths.append(max(0.004, (top - bot) * wide))
            for _ in range(2):                            # (smoothed: the lip's folds are not the moustache's)
                pts = [pts[0]] + [(pts[i - 1] + 2 * pts[i] + pts[i + 1]) / 4 for i in range(1, n)] + [pts[-1]]
            s_at = [0.0]
            for i in range(1, n + 1):
                s_at.append(s_at[-1] + float(np.linalg.norm(pts[i] - pts[i - 1])))
            normals += _strip(bm, layers, [head.move(q) for q in pts], [head.turn(q) for q in outs], s_at,
                              max(widths), T["arch"], 4, float(rng.random()), 1.0 if k else 0.5,
                              taper=lambda tt, w=widths: float(np.interp(tt * (len(w) - 1), range(len(w)), w)) / max(w),
                              lit_round=0.7, flip=sx < 0)
    mesh = bpy.data.meshes.new("moustache_locks")
    bm.to_mesh(mesh)
    bm.free()
    mesh.normals_split_custom_set_from_vertices([tuple(n) for n in normals])
    return mesh


def _object(name, mesh, col, arm):
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.vertex_groups.new(name="head").add(list(range(len(mesh.vertices))), 1.0, "REPLACE")
    if arm is not None:                                   # on the skeleton (an export): it rides the head
        obj.parent = arm
        obj.modifiers.new("rig", "ARMATURE").object = arm
    if mesh.color_attributes.find("Col") >= 0:
        mesh.color_attributes.render_color_index = mesh.color_attributes.find("Col")
        mesh.color_attributes.active_color = mesh.color_attributes["Col"]
    mesh.materials.append(carrier_material(name, col))
    print("%-16s %5d triangles" % (name, sum(len(p.vertices) - 2 for p in mesh.polygons)))
    return obj


def make(fig, wear, stem, posed=True, arm=None, style=None):
    base = fig.base
    P, H, T = fig.to_blender()
    Pp = figed_fit.pose_points(fig, P, H, figed_fit.full_pose(fig.pose, base.bones, H, T), T)[0] if posed else P
    R, L = rules(fig, P, H)
    S = style if isinstance(style, dict) else STYLES[style or "mop"]
    head = Head(fig, P, Pp, H)
    rng = np.random.default_rng(S["seed"])
    G.SMOOTH.update(hair=2, moustache=1, stubble=0)
    objs = {}
    for name in wear:
        f, may, off = R[name]
        if name == "hair":
            # (the cap's thickness: the style's own, thinning to nothing at the hairline)
            vol = np.array([_table(S, "volume", head.a(q), head.e(q)) if m and fv > -0.02 else 0.0
                            for q, m, fv in zip(P, may, f)])
            off = 0.004 + (vol * S["cap"] - 0.004) * np.clip(f / 0.035, 0, 1) ** 0.7
        mesh = G.cut(fig, P, P, f, may, off, name)
        _biggest(mesh)
        if name == "hair":
            cap(mesh, head, S)
            mesh.name = "hair_cap"
            objs["hair_cap"] = _object("hair_cap", mesh, HAIR[0], arm)
            roots = roots_on(head, f, may, S["spacing"], rng)
            objs["hair_locks"] = _object("hair_locks", locks(head, roots, S, rng), HAIR[1], arm)
            print("hair: %d locks" % INFO["locks"])
        elif name == "stubble":
            stubble_uv(mesh, head)
            objs[name] = _object(name, mesh, TACHE[0], arm)
        else:
            moustache_uv(mesh)
            objs[name] = _object(name, mesh, TACHE[1], arm)
            objs["moustache_locks"] = _object("moustache_locks", moustache_locks(head, rng), TACHE[2], arm)
    for name in ("hair_cap", "moustache", "stubble"):                # the pieces cut from the skin, carried into the pose
        if name in objs:
            for v in objs[name].data.vertices:
                v.co = head.move(np.array(v.co[:]))
    return objs


if __name__ == "__main__":
    import figed_blender as fb  # noqa: E402

    argv = sys.argv[sys.argv.index("--") + 1:]
    spec_path, out = argv[:2]
    wear = argv[argv.index("--wear") + 1].split(",") if "--wear" in argv else ["hair", "moustache", "stubble"]
    style = None
    if "--style" in argv:                                 # a style tried from a file: a table of the numbers to change
        with open(argv[argv.index("--style") + 1], "r") as fh:
            style = dict(STYLES["mop"], **json.load(fh))
    fig = figed.Figure(figed.Base(), figed.load_spec(spec_path))
    stem = os.path.splitext(spec_path)[0]
    fb.reset()
    objs, _arm = fb.build(fig, rig=False, posed=True)
    objs["body"].data.materials.append(G.material("skin", stem + "_skin.png"))
    if "eyes" in objs and os.path.exists(stem + "_eyes.png"):
        objs["eyes"].data.materials.append(G.material("eyes", stem + "_eyes.png"))
    make(fig, wear, stem, style=style)
    if "--glb" in argv:                                   # the head with its hair, for Godot (tests/figed_hair_view.gd)
        bpy.ops.export_scene.gltf(filepath=os.path.abspath(argv[argv.index("--glb") + 1]), export_format="GLB",
                                  export_yup=True, export_animations=False)
    boxes = fb.view_boxes(fig)
    cam = fb._camera()
    strips = []
    for view in ("face", "face_quarter_r", "face_side_r", "face_quarter", "face_back"):
        centre, direction, seen, aspect = boxes[view][:4]
        seen = seen * 1.12                                # room for the hair
        w = int(900 * aspect) // 2 * 2
        s = fb._scene((w, 900))
        s.display.shading.color_type = "TEXTURE"
        s.display.shading.light = "FLAT" if "--lit" not in argv else "STUDIO"
        s.display.shading.show_cavity = False
        fb._aim(cam, centre, direction, seen)
        cam.data.sensor_fit = "VERTICAL"
        cam.data.ortho_scale = seen
        s.render.filepath = os.path.join(os.path.dirname(os.path.abspath(out)), "_hair_%s.png" % view)
        bpy.ops.render.render(write_still=True)
        shot = bpy.data.images.load(s.render.filepath)
        strips.append(np.array(shot.pixels[:]).reshape(900, w, 4))
    fb.save_pixels(np.concatenate(strips, axis=1), os.path.abspath(out))
    print("shots", out)
