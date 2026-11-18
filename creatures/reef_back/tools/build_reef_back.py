"""Builds the reef-back (creatures/reef_back) and exports it for Godot.

Run from anywhere (paths are from this file):
    blender --background --python creatures/reef_back/tools/build_reef_back.py
    blender --background --python creatures/reef_back/tools/build_reef_back.py -- <preview folder>   # with pictures
    (add --why to list any face wound against its own smoothed normals)

Writes creatures/reef_back/models/reef_back.glb (the full model, for close pictures), reef_back_game.glb (the game
model: Twilight Princess boss weight, its triangles spent on the head, eyes, claws and the outline of its back),
reef_back_lo.glb (far off) and the editable creatures/reef_back/tools/reef_back.blend (this folder has a .gdignore).
Each is one mesh with one surface, skinned to the same small skeleton (23 bones), with two clips: "walk" (one full
four-legged walking cycle, 6 s at 24 frames, in which it goes STRIDE metres) and "stand" (one slow breath, as long).
The shader (reef_back.gdshader) draws every marking, sways its weed and frills, glows its throat and bends it round
for a turn; the node (reef_back.gd) plays the clips by phase and opens the jaw by turning the jaw bone. It prints a
WINDING line for each model (each face against the way it should face) and a SHADING line (each face against its own
smoothed normals, as Godot reads them).

An original giant amphibious reptile (not any published monster): a heavy four-legged iguana-like beast, 35 m from
nose to tail, that walks slowly on the sea floor; a thick tail; a back of rock plates overgrown with coral, kelp,
barnacles and sponges; a broad blunt head with pink gill frills, a glowing green throat and clawed feet.

Everything here is in Godot space (metres, Y up, its nose at -Z) until it is written out. The origin is on the
floor under its middle; its feet stand on y 0.

What a point is, for the shader: UV2.y the part:
  0 skin (body, neck, tail, legs, the top of the head), 1 the lower jaw's skin, 2 the inside of the mouth, 3 a rock
  plate, 4 coral, 5 kelp, 6 a barnacle, 7 a sponge, 8 a gill frill, 9 a claw, 10 an eye, 11 a ridge plate on the tail.
UV2.x: on a plate a number of its own (0..1); on kelp how far along the blade (0 root .. 1 tip); on coral how far out
along its branch; inside the mouth 0 next to the lips, 1 deep inside; on a barnacle 1 inside its crater; on a sponge 1 inside its tube; on a frill how far out (0 root ..
1 edge); on a claw how far along (0 root, 1 point).
UV: on the body, neck, tail, head and jaw (along: 0 the nose .. 1 the tail tip, high: 1 the ridge of the back .. 0 the
middle of the belly); on a leg (2 + which leg (0 left fore, 1 right fore, 2 left hind, 3 right hind) + along it 0..0.99,
around 0..1); on a frill (across its fan 0..1, 0); on an eye its point in the eye's own plane in eye radii (x towards
the nose, y up). (The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.)

The numbers marked "as the shader has it" or "as the node has it" are there too: change one, change the other.
"""

import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "models")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = ARGS[0] if ARGS and not ARGS[0].startswith("--") else ""

NAME = "reef_back"
TAU = math.tau
PI = math.pi
LENGTH = 35.0
NOSE = -17.5
# The walk (as the node has it): frames in one cycle, frames a second, metres gone in one cycle.
FRAMES = 144
FPS = 24
STRIDE = 4.0
DUTY = 0.72
LIFT = 1.1


def to_b(p):
    return Vector((p.x, -p.z, p.y))


C4 = Matrix(((1, 0, 0, 0), (0, 0, -1, 0), (0, 1, 0, 0), (0, 0, 0, 1)))
C4I = C4.inverted()


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def hermite(keys, x, col):
    """Smooth interpolation of column `col` of `keys` (rows of (x, values...)) at x."""
    xs = [k[0] for k in keys]
    if x <= xs[0]:
        return keys[0][col]
    if x >= xs[-1]:
        return keys[-1][col]
    i = max(j for j in range(len(xs) - 1) if xs[j] <= x)

    def slope(j):
        a, b = max(j - 1, 0), min(j + 1, len(xs) - 1)
        return (keys[b][col] - keys[a][col]) / (xs[b] - xs[a])
    x0, x1 = xs[i], xs[i + 1]
    h = x1 - x0
    t = (x - x0) / h
    y0, y1 = keys[i][col], keys[i + 1][col]
    m0, m1 = slope(i) * h, slope(i + 1) * h
    t2, t3 = t * t, t * t * t
    return (2 * t3 - 3 * t2 + 1) * y0 + (t3 - 2 * t2 + t) * m0 + (-2 * t3 + 3 * t2) * y1 + (t3 - t2) * m1


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.data = []
        self.weights = []
        self.out = []
        self.count = {}

    def add(self, p, uv, part, extra, weights):
        self.verts.append(Vector(p))
        self.data.append(((uv[0], 1.0 - uv[1]), (extra, 1.0 - part)))
        self.weights.append(weights)
        return len(self.verts) - 1

    def face(self, points, out, name):
        kept = []
        for i in points:
            if not any((self.verts[i] - self.verts[k]).length < 1e-4 for k in kept):
                kept.append(i)
        if len(kept) < 3:
            return
        ps = [self.verts[i] for i in kept]
        n = Vector((0.0, 0.0, 0.0))
        for i in range(len(ps)):
            n += ps[i].cross(ps[(i + 1) % len(ps)])
        if n.length < 1e-6:
            return
        if n.dot(out) < 0.0:
            kept = list(reversed(kept))
        self.faces.append(tuple(kept))
        self.out.append((Vector(out), name))
        self.count[name] = self.count.get(name, 0) + 1


class Q:
    def __init__(self, kind):
        self.kind = kind
        full, game = kind == "full", kind == "game"
        self.body_round = 40 if full else (20 if game else 8)
        self.body_tol = 0.004 if full else (0.06 if game else 0.3)
        self.body_step = 0.4 if full else (2.2 if game else 5.0)
        self.head_arch = 24 if full else (12 if game else 6)
        self.head_rings = 36 if full else (10 if game else 4)
        self.leg_sides = 20 if full else (10 if game else 5)
        self.leg_rings = 6 if full else (2 if game else 1)
        self.toe_sides = 10 if full else (5 if game else 3)
        self.eye_sides = 20 if full else (10 if game else 6)
        self.plates = True
        self.dressing = 1.0 if full else (0.6 if game else 0.25)
        self.fine = full


# ---------------------------------------------------------------- the skeleton (as the node has it: bone names)

# (name, head, tail, parent, roll hint): in Godot space. Left is -X.
def limb_bones():
    out = []
    for side, sx in (("L", -1.0), ("R", 1.0)):
        out += [("upperarm." + side, Vector((4.2 * sx, 7.0, -7.4)), Vector((6.2 * sx, 4.1, -6.6)), "chest", None),
                ("forearm." + side, Vector((6.2 * sx, 4.1, -6.6)), Vector((5.4 * sx, 1.25, -7.8)), "upperarm." + side, None),
                ("hand." + side, Vector((5.4 * sx, 1.25, -7.8)), Vector((5.8 * sx, 0.5, -10.0)), "forearm." + side, Vector((0, 1, 0))),
                ("thigh." + side, Vector((4.0 * sx, 6.6, 3.8)), Vector((6.3 * sx, 4.2, 2.1)), "hips", None),
                ("shin." + side, Vector((6.3 * sx, 4.2, 2.1)), Vector((5.3 * sx, 1.25, 4.4)), "thigh." + side, None),
                ("foot." + side, Vector((5.3 * sx, 1.25, 4.4)), Vector((5.7 * sx, 0.5, 2.2)), "shin." + side, Vector((0, 1, 0)))]
    return out


BONES = [
    ("root", Vector((0, 0, 0)), Vector((0, 0, -2.0)), None, Vector((0, 1, 0))),
    ("hips", Vector((0, 8.0, 3.5)), Vector((0, 8.0, -1.0)), "root", Vector((0, 1, 0))),
    ("chest", Vector((0, 8.0, -1.0)), Vector((0, 8.0, -8.0)), "hips", Vector((0, 1, 0))),
    ("neck", Vector((0, 8.0, -8.0)), Vector((0, 8.4, -10.8)), "chest", Vector((0, 1, 0))),
    ("head", Vector((0, 8.4, -10.8)), Vector((0, 9.0, -17.0)), "neck", Vector((0, 1, 0))),
    ("jaw", Vector((0, 6.7, -11.6)), Vector((0, 5.0, -17.0)), "head", Vector((0, 1, 0))),
    ("tail1", Vector((0, 7.4, 5.0)), Vector((0, 6.2, 8.5)), "hips", Vector((0, 1, 0))),
    ("tail2", Vector((0, 6.2, 8.5)), Vector((0, 4.6, 11.5)), "tail1", Vector((0, 1, 0))),
    ("tail3", Vector((0, 4.6, 11.5)), Vector((0, 3.3, 14.0)), "tail2", Vector((0, 1, 0))),
    ("tail4", Vector((0, 3.3, 14.0)), Vector((0, 2.3, 16.0)), "tail3", Vector((0, 1, 0))),
    ("tail5", Vector((0, 2.3, 16.0)), Vector((0, 1.7, 17.6)), "tail4", Vector((0, 1, 0))),
] + limb_bones()
BONE = {b[0]: b for b in BONES}
# Where each bone of the spine holds the skin most (metres along z), in order from the head to the tail tip.
SPINE = [("head", -12.2), ("neck", -9.8), ("chest", -5.0), ("hips", 2.0), ("tail1", 6.8), ("tail2", 10.0),
         ("tail3", 12.8), ("tail4", 15.0), ("tail5", 16.8)]


def spine_weights(z):
    if z <= SPINE[0][1]:
        return {SPINE[0][0]: 1.0}
    if z >= SPINE[-1][1]:
        return {SPINE[-1][0]: 1.0}
    for (a, za), (b, zb) in zip(SPINE, SPINE[1:]):
        if za <= z <= zb:
            t = smooth(za, zb, z)
            return {a: 1.0 - t, b: t}
    return {"hips": 1.0}


def pole_of(name):
    """A limb bone's bend: the knee or elbow, out of the line from its upper joint to its lower."""
    _, h, t, parent, hint = BONE[name]
    if hint is not None:
        return hint
    side = name.split(".")[1]
    upper = "upperarm." + side if name.startswith(("upperarm", "forearm")) else "thigh." + side
    lower = "forearm." + side if upper.startswith("upperarm") else "shin." + side
    a, mid, c = BONE[upper][1], BONE[upper][2], BONE[lower][2]
    line = (c - a).normalized()
    off = (mid - a) - line * (mid - a).dot(line)
    return off.normalized()


# ---------------------------------------------------------------- the body, neck and tail

# (z, middle line's height, half width, half height)
BODY = [(-12.6, 8.0, 3.0, 3.0), (-10.8, 7.9, 3.6, 3.4), (-8.5, 8.0, 4.6, 4.3), (-5.0, 8.3, 5.2, 4.8), (0.0, 8.2, 5.4, 4.9),
        (3.5, 7.9, 5.0, 4.6), (6.0, 7.1, 3.9, 3.7), (9.0, 5.7, 2.8, 2.7), (12.0, 4.3, 1.9, 1.9), (14.5, 3.0, 1.15, 1.2),
        (16.5, 2.1, 0.58, 0.62), (17.5, 1.7, 0.1, 0.12)]
BODY_FROM, BODY_TO = -12.6, 17.5


def body_at(z, a):
    """A point on the skin of the body: `z` along it, `a` round it (0 the ridge of its back, + its right)."""
    yc = hermite(BODY, z, 1)
    w = max(hermite(BODY, z, 2), 0.02)
    h = max(hermite(BODY, z, 3), 0.02)
    c = math.cos(a)
    y = yc + (h * c if c > 0.0 else h * 0.88 * c)
    # (a little fuller along the flanks: a flat-sided barrel)
    x = w * math.sin(a) * (1.0 + 0.06 * math.sin(a) ** 2 * (1.0 - abs(c)))
    return Vector((x, y, z))


def body_normal(z, a):
    e = 1e-3
    p = body_at(z, a)
    dz = body_at(z + e, a) - body_at(z - e, a)
    da = body_at(z, a + e) - body_at(z, a - e)
    n = da.cross(dz)
    centre = Vector((0.0, hermite(BODY, z, 1), z))
    if n.dot(p - centre) < 0.0:
        n = -n
    return n.normalized()


def along(z):
    return (z - NOSE) / LENGTH


def pick_z(q):
    """The rings of the body: close where its outline curves, far apart along straight stretches."""
    zs = [BODY_FROM + (BODY_TO - BODY_FROM) * i / 600.0 for i in range(601)]
    if q.kind == "full":
        n = int((BODY_TO - BODY_FROM) / q.body_step)
        return [BODY_FROM + (BODY_TO - BODY_FROM) * i / n for i in range(n + 1)]
    vals = lambda z: (hermite(BODY, z, 1), hermite(BODY, z, 2), hermite(BODY, z, 3))
    kept = [0]
    i = 0
    while i < len(zs) - 1:
        best = i + 1
        for j in range(i + 2, len(zs)):
            if zs[j] - zs[i] > q.body_step:
                break
            ok = True
            a, b = vals(zs[i]), vals(zs[j])
            for k in range(i + 1, j):
                t = (zs[k] - zs[i]) / (zs[j] - zs[i])
                v = vals(zs[k])
                if any(abs(lerp(a[c], b[c], t) - v[c]) > q.body_tol for c in range(3)):
                    ok = False
                    break
            if not ok:
                break
            best = j
        kept.append(best)
        i = best
    out = [zs[k] for k in kept]
    # (always a ring at the shoulders and the hips, where the legs bend the skin)
    for z in (-8.5, -6.0, 2.0, 4.5, 7.0):
        if all(abs(z - o) > 0.6 for o in out):
            out.append(z)
    return sorted(out)


def body(m, q):
    zs = pick_z(q)
    n = q.body_round
    rows = []
    for i, z in enumerate(zs):
        w = spine_weights(z)
        if i == len(zs) - 1:
            idx = m.add(Vector((0.0, hermite(BODY, z, 1), z + 0.05)), (along(z), 0.5), 0, 0.0, w)
            rows.append([idx] * (n + 1))
            continue
        row = []
        for j in range(n + 1):
            a = -PI + TAU * j / n
            row.append(m.add(body_at(z, a), (along(z), (1.0 + math.cos(a)) * 0.5), 0, 0.0, w))
        rows.append(row)
    for i in range(len(rows) - 1):
        za, zb = zs[i], zs[i + 1]
        centre = Vector((0.0, hermite(BODY, (za + zb) * 0.5, 1), (za + zb) * 0.5))
        for j in range(n):
            quad = (rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j])
            mid = sum((m.verts[x] for x in quad), Vector()) / 4.0
            m.face(quad, mid - centre, "body")
    # (the front of the neck, inside the head: closed)
    c = m.add(Vector((0.0, hermite(BODY, zs[0], 1), zs[0] - 0.05)), (along(zs[0]), 0.5), 0, 0.0, spine_weights(zs[0]))
    for j in range(n):
        m.face((rows[0][j], rows[0][j + 1], c), Vector((0, 0, -1)), "body")


# ---------------------------------------------------------------- the head and the jaw

# (z, top of the head, line of the lips, half width at the lips, bottom of the chin)
HEAD = [(-17.5, 7.8, 6.6, 0.55, 6.0), (-17.3, 8.8, 6.4, 2.2, 5.3), (-16.5, 9.8, 6.4, 3.3, 4.7), (-15.0, 10.7, 6.5, 4.05, 4.3),
        (-13.4, 11.25, 6.6, 4.3, 4.2), (-12.0, 11.3, 6.7, 4.25, 4.45), (-10.4, 10.9, 6.8, 3.8, 5.1)]
HEAD_FROM, HEAD_TO = -17.5, -10.4
CORNER = -12.0
# (as the node has it: the jaw's hinge)
HINGE = Vector((0.0, 6.7, -11.6))


def head_at(z, a):
    """A point on the upper head: `a` from -pi/2 (its left lip) over its top to pi/2 (its right lip)."""
    top, lip, w = hermite(HEAD, z, 1), hermite(HEAD, z, 2), hermite(HEAD, z, 3)
    c = math.cos(a)
    y = lip + (top - lip) * (c ** 0.75 if c > 0 else 0.0)
    # (cheeks: fuller low on the sides)
    x = w * math.sin(a) * (1.0 + 0.08 * math.sin(2.0 * abs(a)))
    return Vector((x, y, z))


def jaw_at(z, a):
    """A point on the lower jaw: `a` from -pi/2 (its left lip) under its chin to pi/2."""
    lip, w, chin = hermite(HEAD, z, 2), hermite(HEAD, z, 3) * 0.96, hermite(HEAD, z, 4)
    c = math.cos(a)
    # (its lower lip rises a little inside the upper one: a closed mouth line, nothing of the mouth showing)
    y = lip + 0.15 - (lip + 0.15 - chin) * (c ** 0.8 if c > 0 else 0.0)
    return Vector((w * math.sin(a), y, z))


def head_rings(q, z0, z1, tip):
    n = q.head_rings
    zs = []
    for i in range(n + 1):
        f = i / n
        f = f * f * (3.0 - 2.0 * f) * 0.5 + f * 0.5 if tip else f
        zs.append(z0 + (z1 - z0) * f)
    return zs


def head(m, q):
    # The upper head: an arch over the top from lip to lip, closed beneath by the roof of the mouth.
    zs = head_rings(q, HEAD_FROM + 0.12, HEAD_TO, True)
    na = q.head_arch
    nr = 4 if q.kind != "lo" else 2
    w = {"head": 1.0}
    rows = []
    for z in zs:
        lip = hermite(HEAD, z, 2)
        row = []
        for j in range(na + 1):
            a = -PI / 2 + PI * j / na
            p = head_at(z, a)
            row.append((m.add(p, (along(z), 0.5 + 0.5 * math.cos(a)), 0, 0.0, w), "skin"))
        # the roof of the mouth, from the right lip back to the left, vaulted
        hw = hermite(HEAD, z, 3)
        for k in range(1, nr):
            x = hw * (1.0 - 2.0 * k / nr)
            # (the vault rises behind the snout; on the first ring, at the tip of the snout, it is skin)
            front = z == zs[0]
            y = lip + 0.05 + 0.55 * (1.0 - (x / hw) ** 2) * smooth(HEAD_FROM, HEAD_FROM + 1.6, z)
            row.append((m.add(Vector((x, y, z)), (along(z), 0.4), 0 if front else 2, 0.0 if k in (1, nr - 1) else 1.0, w), "roof"))
        rows.append(row)
    for i in range(len(rows) - 1):
        a, b = rows[i], rows[i + 1]
        cnt = len(a)
        zc = (zs[i] + zs[i + 1]) * 0.5
        centre = Vector((0.0, (hermite(HEAD, zc, 1) + hermite(HEAD, zc, 2)) * 0.5, zc))
        for j in range(cnt):
            k = (j + 1) % cnt
            quad = (a[j][0], a[k][0], b[k][0], b[j][0])
            mid = sum((m.verts[x] for x in quad), Vector()) / 4.0
            roof = a[j][1] == "roof" or a[k][1] == "roof"
            m.face(quad, Vector((0, -1, 0)) if roof and j >= na else mid - centre, "head")
    tip = m.add(Vector((0.0, (hermite(HEAD, HEAD_FROM, 1) + hermite(HEAD, HEAD_FROM, 2)) * 0.5, HEAD_FROM)), (0.0, 0.6), 0, 0.0, w)
    for j in range(len(rows[0])):
        k = (j + 1) % len(rows[0])
        m.face((rows[0][j][0], rows[0][k][0], tip), Vector((0, 0.2, -1)), "head")
    back = m.add(Vector((0.0, 8.6, HEAD_TO + 0.1)), (along(HEAD_TO), 0.6), 0, 0.0, w)
    for j in range(len(rows[-1])):
        k = (j + 1) % len(rows[-1])
        m.face((rows[-1][j][0], rows[-1][k][0], back), Vector((0, 0, 1)), "head")
    # The lower jaw: a trough under the chin from lip to lip, closed above by the floor of the mouth.
    zs = head_rings(q, HEAD_FROM + 0.12, -10.8, True)
    rows = []
    w = {"jaw": 1.0}
    for z in zs:
        lip = hermite(HEAD, z, 2)
        row = []
        for j in range(na + 1):
            a = -PI / 2 + PI * j / na
            p = jaw_at(z, a)
            row.append((m.add(p, (along(z), 0.25 * (1.0 - math.cos(a)) + 0.02), 1, 0.0, w), "skin"))
        hw = hermite(HEAD, z, 3) * 0.95
        for k in range(1, nr):
            x = hw * (1.0 - 2.0 * k / nr)
            y = lip - 0.15 - 0.45 * (1.0 - (x / hw) ** 2)
            row.append((m.add(Vector((x, y, z)), (along(z), 0.3), 1 if z == zs[0] else 2, 0.0 if k in (1, nr - 1) else 1.0, w), "floor"))
        rows.append(row)
    for i in range(len(rows) - 1):
        a, b = rows[i], rows[i + 1]
        cnt = len(a)
        zc = (zs[i] + zs[i + 1]) * 0.5
        centre = Vector((0.0, (hermite(HEAD, zc, 2) + hermite(HEAD, zc, 4)) * 0.5, zc))
        for j in range(cnt):
            k = (j + 1) % cnt
            quad = (a[j][0], a[k][0], b[k][0], b[j][0])
            mid = sum((m.verts[x] for x in quad), Vector()) / 4.0
            floor = j >= na
            m.face(quad, Vector((0, 1, 0)) if floor else mid - centre, "jaw")
    z0 = zs[0]
    tip = m.add(Vector((0.0, hermite(HEAD, z0, 2) - 0.3, z0 - 0.1)), (0.0, 0.1), 1, 0.0, w)
    for j in range(len(rows[0])):
        k = (j + 1) % len(rows[0])
        m.face((rows[0][j][0], rows[0][k][0], tip), Vector((0, -0.2, -1)), "jaw")
    back = m.add(Vector((0.0, 6.0, -10.7)), (along(-10.8), 0.2), 1, 0.0, w)
    for j in range(len(rows[-1])):
        k = (j + 1) % len(rows[-1])
        m.face((rows[-1][j][0], rows[-1][k][0], back), Vector((0, 0, 1)), "jaw")


def head_surface(z, a):
    p = head_at(z, a)
    e = 1e-3
    n = (head_at(z, a + e) - head_at(z, a - e)).cross(head_at(z + e, a) - head_at(z - e, a))
    centre = Vector((0.0, (hermite(HEAD, z, 1) + hermite(HEAD, z, 2)) * 0.5, z))
    if n.dot(p - centre) < 0.0:
        n = -n
    return p, n.normalized()


# ---------------------------------------------------------------- tubes and lumps

def frames(pts, first_n):
    ts = []
    for i in range(len(pts)):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, len(pts) - 1)]
        ts.append((b - a).normalized())
    ns = []
    n = (first_n - ts[0] * first_n.dot(ts[0]))
    if n.length < 1e-6:
        n = ts[0].orthogonal()
    n.normalize()
    ns.append(n)
    for i in range(len(pts) - 1):
        v1 = pts[i + 1] - pts[i]
        c1 = v1.dot(v1)
        if c1 < 1e-12:
            ns.append(n)
            continue
        rl = n - v1 * (2.0 / c1 * v1.dot(n))
        tl = ts[i] - v1 * (2.0 / c1 * v1.dot(ts[i]))
        v2 = ts[i + 1] - tl
        c2 = v2.dot(v2)
        n = rl - v2 * (2.0 / c2 * v2.dot(rl)) if c2 > 1e-12 else rl
        n = (n - ts[i + 1] * n.dot(ts[i + 1])).normalized()
        ns.append(n)
    return ts, ns


def tube(m, pts, radii, sides, part, name, uv_of, extra_of, weights_of, first_n, tip=True, root_cap=True, squash=1.0):
    ts, ns = frames(pts, first_n)
    rows = []
    for i, p in enumerate(pts):
        n = ns[i]
        b = ts[i].cross(n).normalized()
        row = []
        for j in range(sides + 1):
            ang = TAU * j / sides
            off = n * (math.cos(ang) * radii[i] * squash) + b * (math.sin(ang) * radii[i])
            row.append(m.add(p + off, uv_of(i, j / sides), part, extra_of(i), weights_of(i, p + off)))
        rows.append(row)
    for i in range(len(rows) - 1):
        mid_line = (pts[i] + pts[i + 1]) * 0.5
        for j in range(sides):
            quad = (rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j])
            mid = sum((m.verts[x] for x in quad), Vector()) / 4.0
            m.face(quad, mid - mid_line, name)
    last = len(pts) - 1
    if tip:
        end = pts[-1] + ts[-1] * radii[-1] * 1.2
        e = m.add(end, uv_of(last, 0.5), part, extra_of(last), weights_of(last, end))
        for j in range(sides):
            m.face((rows[-1][j], rows[-1][j + 1], e), ts[-1], name)
    if root_cap:
        s0 = pts[0] - ts[0] * radii[0] * 0.3
        s = m.add(s0, uv_of(0, 0.5), part, extra_of(0), weights_of(0, s0))
        for j in range(sides):
            m.face((rows[0][j + 1], rows[0][j], s), -ts[0], name)
    return rows


def lump(m, centre, radii, part, name, uv, extra, weights, nlon, nlat, rnd=None, rough=0.0, axes=None):
    """A closed squashed sphere (with a lumpy skin if `rough`)."""
    ax = axes or (Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))
    rows = []
    bumps = [rnd.uniform(0, TAU) for _ in range(3)] if rnd else [0, 0, 0]
    for i in range(nlat + 1):
        lat = -PI / 2 + PI * i / nlat
        row = []
        if i in (0, nlat):
            p = centre + ax[1] * (radii.y * math.sin(lat))
            idx = m.add(p, uv, part, extra, weights)
            rows.append([idx] * (nlon + 1))
            continue
        for j in range(nlon + 1):
            lon = TAU * j / nlon
            k = 1.0 + rough * (math.sin(3 * lon + bumps[0]) * math.cos(2 * lat + bumps[1]) * 0.6 + math.sin(5 * lon + bumps[2]) * 0.4)
            d = ax[0] * (radii.x * math.cos(lat) * math.cos(lon)) + ax[2] * (radii.z * math.cos(lat) * math.sin(lon)) + ax[1] * (radii.y * math.sin(lat))
            row.append(m.add(centre + d * k, uv, part, extra, weights))
        rows.append(row)
    for i in range(nlat):
        for j in range(nlon):
            quad = (rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j])
            mid = sum((m.verts[x] for x in quad), Vector()) / 4.0
            m.face(quad, mid - centre, name)


# ---------------------------------------------------------------- the legs and feet

LEGS = [("upperarm.L", "forearm.L", "hand.L"), ("upperarm.R", "forearm.R", "hand.R"),
        ("thigh.L", "shin.L", "foot.L"), ("thigh.R", "shin.R", "foot.R")]


def leg(m, q, index):
    upper, lower, foot = LEGS[index]
    sx = -1.0 if upper.endswith("L") else 1.0
    fore = index < 2
    a, b, c = BONE[upper][1], BONE[upper][2], BONE[lower][2]
    body_bone = "chest" if fore else "hips"
    # (from inside the body: the leg's top swells out of the flank; the path is rounded at the elbow or knee so
    # that the inside of the bend does not fold through itself)
    inside = a - (b - a).normalized() * 2.2
    corners = [inside, a, b, c]
    dense, ds = [], []
    for seg in range(3):
        for k in range(60):
            f = k / 60.0
            dense.append(corners[seg] + (corners[seg + 1] - corners[seg]) * f)
            ds.append(seg + f)
    dense.append(c)
    ds.append(3.0)
    for _ in range(400):
        new = list(dense)
        for i in range(1, len(dense) - 1):
            if abs(ds[i] - 2.0) < 0.9:
                new[i] = dense[i] * 0.5 + (dense[i - 1] + dense[i + 1]) * 0.25
        dense = new
    if q.kind == "full":
        stations = [i / 20.0 * 3.0 for i in range(21)]
    elif q.kind == "game":
        stations = [0.0, 0.6, 1.0, 1.4, 1.75, 2.25, 2.6, 3.0]
    else:
        stations = [0.0, 1.0, 2.0, 3.0]

    def radius_at(s):
        if s < 1.0:
            return lerp(2.7, 2.6, s)
        if s < 2.0:
            f = s - 1.0
            return lerp(2.6, 1.85, f) * (1.0 + 0.1 * math.sin(PI * f))
        return lerp(1.85, 1.25, s - 2.0)

    def weights_at(s):
        if s < 1.0:
            return {body_bone: 1.0 - 0.5 * s, upper: 0.5 * s}
        if s < 2.0:
            f = s - 1.0
            if f < 0.35:
                k = smooth(0.0, 0.35, f)
                return {body_bone: 0.5 * (1.0 - k), upper: 0.5 + 0.5 * k}
            k = smooth(0.75, 1.0, f)
            return {upper: 1.0 - 0.5 * k, lower: 0.5 * k}
        f = s - 2.0
        if f < 0.25:
            k = smooth(0.0, 0.25, f)
            return {upper: 0.5 * (1.0 - k), lower: 0.5 + 0.5 * k}
        k = smooth(0.75, 1.0, f)
        return {lower: 1.0 - 0.4 * k, foot: 0.4 * k}
    pts = [dense[min(int(round(s * 60)), len(dense) - 1)] for s in stations]
    rad = [radius_at(s) for s in stations]
    first_n = Vector((0.0, 0.0, -1.0))
    tube(m, pts, rad, q.leg_sides, 0, "leg", lambda i, around: (2 + index + min(stations[i] / 3.0, 0.99), around),
         lambda i: 0.0, lambda i, p: weights_at(stations[i]), first_n, tip=False, root_cap=True)
    # The foot: a broad pad on the floor, four splayed toes, a dark claw on each.
    fb = BONE[foot]
    ankle, toe = fb[1], fb[2]
    fwd = Vector((toe.x - ankle.x, 0.0, toe.z - ankle.z)).normalized()
    side = Vector((0.0, 1.0, 0.0)).cross(fwd).normalized()
    pad_c = Vector((ankle.x, 0.6, ankle.z)) + fwd * 0.6
    fw = {foot: 1.0}
    nl = 12 if q.fine else (8 if q.kind == "game" else 5)
    lump(m, pad_c, Vector((1.8, 0.68, 1.95)), 0, "foot", (2 + index + 0.99, 0.5), 0.0, fw, nl, 4 if q.kind != "lo" else 2,
         axes=(side, Vector((0, 1, 0)), fwd))
    # (the ankle into the pad)
    tube(m, [ankle + Vector((0, 0.4, 0)), pad_c + Vector((0, 0.3, 0))], [1.22, 1.5], q.leg_sides, 0, "leg",
         lambda i, around: (2 + index + 0.99, around), lambda i: 0.0, lambda i, p: {lower: 0.4 * (1 - i), foot: 0.6 + 0.4 * i},
         first_n, tip=False, root_cap=False)
    toes = 4 if q.kind != "lo" else 3
    for k in range(toes):
        spread = lerp(-0.75, 0.75, k / (toes - 1)) * (1.0 if fore else 0.85)
        d = (fwd * math.cos(spread) + side * math.sin(spread)).normalized()
        base = pad_c + d * 1.45 + Vector((0, -0.05, 0))
        length = 1.8 - 0.35 * abs(spread)
        tp = [base, base + d * (length * 0.55) + Vector((0, 0.08, 0)), base + d * length + Vector((0, -0.05, 0))]
        tube(m, tp, [0.52, 0.44, 0.36], q.toe_sides, 0, "toe", lambda i, around: (2 + index + 0.99, around), lambda i: 0.0,
             lambda i, p: fw, Vector((0, 1, 0)), tip=True, root_cap=True)
        # the claw: a hooked cone, curving down to the floor
        tip0 = tp[-1]
        cp = []
        nc = 4 if q.fine else 2
        for i in range(nc + 1):
            f = i / nc
            cp.append(tip0 + d * (1.25 * f) + Vector((0.0, 0.25 * f - 0.6 * f * f, 0.0)))
        tube(m, cp, [lerp(0.36, 0.05, i / nc) for i in range(nc + 1)], q.toe_sides, 9, "claw", lambda i, around: (0.0, around),
             lambda i: i / nc, lambda i, p: fw, Vector((0, 1, 0)), tip=True, root_cap=True)


# ---------------------------------------------------------------- eyes, brows, horns, frills

EYE_Z, EYE_A, EYE_R = -14.6, 0.9, 0.66


def eye(m, q, sx):
    a = EYE_A * sx
    c, n = head_surface(EYE_Z, a)
    fwd = Vector((0.0, 0.0, -1.0))
    up = Vector((0.0, 1.0, 0.0)) - n * n.y
    up.normalize()
    to_nose = (fwd - n * n.dot(fwd) - up * up.dot(fwd)).normalized()
    w = {"head": 1.0}
    sides = q.eye_sides
    rings = []
    nr = 3 if q.fine else 1
    for k in range(nr + 1):
        al = (PI / 2) * k / (nr + 1)
        rho = EYE_R * math.cos(al)
        h = -0.1 * EYE_R + EYE_R * 0.6 * math.sin(al)
        row = []
        for j in range(sides):
            ph = TAU * j / sides
            p = c + n * h + (to_nose * math.cos(ph) + up * math.sin(ph)) * rho
            row.append(m.add(p, (math.cos(ph) * rho / EYE_R, math.sin(ph) * rho / EYE_R), 10, 0.0, w))
        rings.append(row)
    top = m.add(c + n * (EYE_R * 0.66), (0.0, 0.0), 10, 0.0, w)
    middle = c - n * EYE_R * 0.5
    for i in range(len(rings) - 1):
        for j in range(sides):
            k = (j + 1) % sides
            quad = (rings[i][j], rings[i][k], rings[i + 1][k], rings[i + 1][j])
            mid = sum((m.verts[x] for x in quad), Vector()) / 4.0
            m.face(quad, mid - middle, "eye")
    for j in range(sides):
        tri = (rings[-1][j], rings[-1][(j + 1) % sides], top)
        mid = sum((m.verts[x] for x in tri), Vector()) / 3.0
        m.face(tri, mid - middle, "eye")
    # The brow: a heavy ridge over the eye, lower towards the nose (a heavy, sleepy look), sunk into the head.
    brow_c = c + up * (EYE_R * 0.95) - to_nose * (EYE_R * 0.1) + n * (EYE_R * 0.05)
    brow_up = (up + to_nose * 0.25).normalized()
    brow_long = (to_nose - brow_up * brow_up.dot(to_nose)).normalized()
    lump(m, brow_c, Vector((EYE_R * 1.9, EYE_R * 0.85, EYE_R * 0.7)), 0, "brow", (along(EYE_Z), 0.9), 0.0, w,
         12 if q.fine else (10 if q.kind == "game" else 5), 6 if q.fine else (4 if q.kind == "game" else 2),
         axes=(brow_long, n, brow_up))
    # The horn: a stubby knob behind the brow, pointing back and up.
    hc, hn = head_surface(-12.9, 0.62 * sx)
    way = (hn + Vector((0.0, 0.7, 0.9))).normalized()
    hp = [hc - hn * 0.3, hc + way * 0.8, hc + way * 1.5]
    tube(m, hp, [0.55, 0.38, 0.12], 6 if q.kind != "lo" else 4, 0, "horn", lambda i, around: (along(-12.9), 0.95),
         lambda i: 0.0, lambda i, p: w, Vector((0, 0, 1)), tip=True, root_cap=True)


def frill(m, q, sx):
    """A gill frill behind the jaw: a fan of four soft rays with skin between, scalloped at its edge (two sheets back
    to back)."""
    root = Vector((3.85 * sx, 9.3, -11.6))
    w = {"head": 0.6, "neck": 0.4}
    out = Vector((sx, 0.0, 0.0))
    # the fan's plane: across the side of the neck, from pointing up and back to pointing back and down
    rays = []
    for k in range(4):
        ang = lerp(0.95, -0.35, k / 3.0)
        length = [3.6, 4.4, 4.1, 3.2][k]
        d = Vector((0.55 * sx, math.sin(ang), math.cos(ang))).normalized()
        rays.append((d, length))
    nu = 6 if q.fine else 2
    nv = 6 if q.fine else 3
    normal = out
    grid = []
    for i in range(3 * nu + 1):
        u = i / (3 * nu)
        seg = min(int(u * 3), 2)
        f = u * 3 - seg
        d = rays[seg][0].lerp(rays[seg + 1][0], f).normalized()
        length = lerp(rays[seg][1], rays[seg + 1][1], f) * (1.0 - 0.22 * math.sin(PI * f))
        col = []
        for j in range(nv + 1):
            v = j / nv
            p = root + d * (length * v) + out * (0.25 * v * v)
            col.append((p, u, v))
        grid.append(col)
    for sheet in (1.0, -1.0):
        idx = [[m.add(p + normal * (0.03 * sheet), (u, 0.0), 8, v, w) for (p, u, v) in col] for col in grid]
        for i in range(len(idx) - 1):
            for j in range(nv):
                quad = (idx[i][j], idx[i + 1][j], idx[i + 1][j + 1], idx[i][j + 1])
                m.face(quad, normal * sheet, "frill")


# ---------------------------------------------------------------- the reef on its back

def plate(m, q, centre, n, radius, thick, rnd, part, weights, extra, tilt_way=None, sides=6):
    """A slab of rock: an irregular polygon, bevelled on top, its foot sunk in the skin."""
    t1 = n.orthogonal().normalized()
    t2 = n.cross(t1).normalized()
    corners = []
    for k in range(sides):
        ang = TAU * k / sides + rnd.uniform(-0.25, 0.25)
        corners.append((t1 * math.cos(ang) + t2 * math.sin(ang)) * (radius * rnd.uniform(0.8, 1.15)))
    lift = lambda d: (n * (0.35 * thick * d.normalized().dot(tilt_way)) if tilt_way is not None else Vector())
    base = [m.add(centre - n * 0.5 + d * 0.92, (0.0, 0.0), part, extra, weights) for d in corners]
    outer = [m.add(centre + n * (thick * 0.7) + d + lift(d), (0.0, 0.3), part, extra, weights) for d in corners]
    inner = [m.add(centre + n * thick + d * 0.7 + lift(d) * 0.8, (0.0, 1.0), part, extra, weights) for d in corners]
    top = m.add(centre + n * (thick * 1.05), (0.0, 1.0), part, extra, weights)
    for k in range(sides):
        j = (k + 1) % sides
        d = (corners[k] + corners[j]).normalized()
        m.face((base[k], base[j], outer[j], outer[k]), d, "plate")
        m.face((outer[k], outer[j], inner[j], inner[k]), d * 0.6 + n, "plate")
        m.face((inner[k], inner[j], top), n, "plate")


def pile(z, a):
    """How high the pile of plates stands over the skin at a place on its back (0 at its edges)."""
    return (1.0 - min(abs(a), 1.25) / 1.25) * (1.0 - smooth(3.0, 5.5, z)) * smooth(-9.5, -6.0, z)


def on_pile(z, a, over=0.0):
    """A point on top of the pile of plates (and the way out there)."""
    n = body_normal(z, a)
    return body_at(z, a) + n * (1.6 * pile(z, a) + 1.0 + 0.6 * pile(z, a) + over), n


def plates(m, q, rnd):
    """The carapace: slabs of rock piled on its back, the middle ones highest (a mound, as a cairn), smaller and
    flatter down its flanks."""
    rows = [(-8.8, 4), (-6.6, 5), (-4.2, 6), (-1.8, 6), (0.6, 6), (2.9, 5), (5.0, 3)]
    for z0, cols in rows:
        for c in range(cols):
            a = lerp(-1.2, 1.2, (c + 0.5) / cols) + rnd.uniform(-0.07, 0.07)
            z = z0 + rnd.uniform(-0.3, 0.3) + (0.6 if c % 2 else 0.0)
            n = body_normal(z, a)
            middle = pile(z, a)
            p = body_at(z, a) + n * (1.6 * middle)
            size = rnd.uniform(1.7, 2.2) * (1.0 - 0.22 * abs(a))
            plate(m, q, p, n, size, rnd.uniform(1.0, 1.5) + 0.6 * middle, rnd, 3, spine_weights(z), rnd.random(),
                  tilt_way=Vector((0, 0, 1)), sides=6 if q.kind != "lo" else 5)
    # a few big flat stones on top of the pile
    for z, a in ((-5.4, 0.15), (-1.0, -0.2), (2.0, 0.3)):
        n = body_normal(z, a)
        p = body_at(z, a) + n * 2.6
        plate(m, q, p, (n + Vector((rnd.uniform(-0.2, 0.2), 0.3, rnd.uniform(-0.2, 0.2)))).normalized(), rnd.uniform(1.9, 2.4),
              1.2, rnd, 3, spine_weights(z), rnd.random(), tilt_way=Vector((0, 0, 1)), sides=6 if q.kind != "lo" else 5)


def tail_fin(m, q):
    """A low saw-edged fin along the top of its tail, from behind the carapace to near its tip (two sheets back to
    back)."""
    z0, z1 = 5.6, 16.6
    teeth = 9
    per = 4 if q.fine else 2
    edge = []
    for i in range(teeth * per + 1):
        z = z0 + (z1 - z0) * i / (teeth * per)
        f = (i % per) / per
        h = lerp(1.1, 0.25, (z - z0) / (z1 - z0)) * (0.45 + 0.55 * f)
        base = body_at(z, 0.0) - Vector((0.0, 0.25, 0.0))
        edge.append((base, base + Vector((0.0, h + 0.25, 0.25 * f)), z))
    for sheet in (1.0, -1.0):
        idx = [(m.add(b + Vector((0.05 * sheet, 0, 0)), (along(z), 1.0), 11, 0.0, spine_weights(z)),
                m.add(t + Vector((0.02 * sheet, 0, 0)), (along(z), 1.0), 11, 1.0, spine_weights(z))) for b, t, z in edge]
        for i in range(len(idx) - 1):
            m.face((idx[i][0], idx[i + 1][0], idx[i + 1][1], idx[i][1]), Vector((sheet, 0, 0)), "fin")



def blade(m, root, way, flat, length, width, segs, part, weights, rnd):
    seed = rnd.random()
    """A kelp blade: two sheets back to back, waving as it rises."""
    way = way.normalized()
    side = way.cross(flat).normalized()
    across = side.cross(way).normalized()
    lean = across * rnd.uniform(-0.4, 0.4) + side * rnd.uniform(-0.2, 0.2)
    ph = rnd.uniform(0.0, TAU)
    rows = []
    for k in range(segs + 1):
        f = k / segs
        c = root + way * (length * f) + lean * (length * f * f) + across * (0.12 * length * (math.sin(ph + f * 4.0) - math.sin(ph)) * f)
        wd = width * (0.4 + 0.6 * min(f * 4.0, 1.0)) * (1.0 - 0.6 * f)
        rows.append((c - side * wd, c + side * wd, f))
    for sheet in (1.0, -1.0):
        idx = [(m.add(l, (seed, 0.0), part, f, weights), m.add(r, (seed, 0.0), part, f, weights)) for l, r, f in rows]
        for k in range(segs):
            pa, pb, pc = m.verts[idx[k][0]], m.verts[idx[k][1]], m.verts[idx[k + 1][0]]
            m.face((idx[k][0], idx[k][1], idx[k + 1][1], idx[k + 1][0]), (pb - pa).cross(pc - pa) * sheet, "kelp")


def coral(m, q, base, n, rnd, weights, size):
    """Branching coral: a short trunk forking twice, each branch a tapering tube with a round tip."""
    sides = 6 if q.fine else 4
    up = (n + Vector((0, 1.2, 0))).normalized()

    def branch(start, way, length, r, depth, s0):
        n_pts = 4 if q.fine else 2
        bend = Vector((rnd.uniform(-1, 1), rnd.uniform(0, 0.6), rnd.uniform(-1, 1))) * 0.25
        pts = [start + way * (length * k / n_pts) + bend * (length * (k / n_pts) ** 2) for k in range(n_pts + 1)]
        rr = [lerp(r, r * 0.7, k / n_pts) for k in range(n_pts + 1)]
        tube(m, pts, rr, sides, 4, "coral", lambda i, a: (0.0, a), lambda i: s0 + (1.0 - s0) * 0.5 * i / n_pts,
             lambda i, p: weights, n, tip=True, root_cap=depth == 0)
        if depth < 2:
            forks = 2 if depth == 0 else rnd.choice((1, 2))
            for f in range(forks):
                d = (way + Vector((rnd.uniform(-0.9, 0.9), rnd.uniform(0.0, 0.5), rnd.uniform(-0.9, 0.9)))).normalized()
                branch(pts[-1] - way * (r * 0.3), d, length * 0.75, r * 0.7, depth + 1, s0 + (1.0 - s0) * 0.5)
    branch(base - n * 0.2, up, size, 0.32 * size / 1.6, 0, 0.0)


def barnacle(m, q, p, n, r, weights):
    sides = 7 if q.fine else 5
    t1 = n.orthogonal().normalized()
    t2 = n.cross(t1).normalized()
    ring = lambda rad, h, extra: [m.add(p + n * h + (t1 * math.cos(TAU * k / sides) + t2 * math.sin(TAU * k / sides)) * rad,
                                        (0.0, 0.0), 6, extra, weights) for k in range(sides)]
    foot = ring(r * 1.1, -0.15, 0.0)
    lip = ring(r * 0.6, r * 0.9, 0.0)
    pit = ring(r * 0.35, r * 0.45, 1.0)
    bottom = m.add(p + n * (r * 0.4), (0.0, 0.0), 6, 1.0, weights)
    for k in range(sides):
        j = (k + 1) % sides
        d = (foot[k], foot[j])
        mid_dir = (m.verts[foot[k]] + m.verts[foot[j]]) * 0.5 - p
        m.face((foot[k], foot[j], lip[j], lip[k]), mid_dir.normalized() + n * 0.3, "barnacle")
        m.face((lip[k], lip[j], pit[j], pit[k]), n - mid_dir.normalized() * 0.5, "barnacle")
        m.face((pit[k], pit[j], bottom), n, "barnacle")


def sponge(m, q, p, n, rnd, weights, size):
    """A tube sponge (open at its top) or a lumpy round one."""
    if rnd.random() < 0.5:
        lump(m, p + n * (size * 0.4), Vector((size, size * 0.8, size)), 7, "sponge", (0.0, 0.0), 0.0, weights,
             10 if q.fine else 6, 6 if q.fine else 3, rnd=rnd, rough=0.12)
        return
    sides = 8 if q.fine else 5
    t1 = n.orthogonal().normalized()
    t2 = n.cross(t1).normalized()
    way = (n + Vector((rnd.uniform(-0.3, 0.3), 0.5, rnd.uniform(-0.3, 0.3)))).normalized()
    h = size * rnd.uniform(1.8, 2.6)

    def ring(rad, along_, extra):
        c = p + way * along_
        return [m.add(c + (t1 * math.cos(TAU * k / sides) + t2 * math.sin(TAU * k / sides)) * rad, (0.0, 0.0), 7, extra, weights)
                for k in range(sides)]
    a = ring(size * 0.55, -0.2, 0.0)
    b = ring(size * 0.5, h, 0.0)
    c = ring(size * 0.36, h, 1.0)
    d = ring(size * 0.36, h * 0.35, 1.0)
    bottom = m.add(p + way * (h * 0.3), (0.0, 0.0), 7, 1.0, weights)
    for k in range(sides):
        j = (k + 1) % sides
        out = (m.verts[a[k]] + m.verts[a[j]]) * 0.5 - (p - way * 0.2)
        m.face((a[k], a[j], b[j], b[k]), out, "sponge")
        m.face((b[k], b[j], c[j], c[k]), way, "sponge")
        m.face((c[k], c[j], d[j], d[k]), -out, "sponge")
        m.face((d[k], d[j], bottom), way, "sponge")


def reef(m, q, rnd):
    """Coral, kelp, sponges and barnacles growing on its back, and barnacles on its flanks and shoulders."""
    amount = q.dressing
    spots = [(-6.0, 0.3), (-1.5, -0.45), (2.6, 0.2), (-3.6, 0.85), (0.8, 0.95), (-7.2, -0.7)]
    for k, (z, a) in enumerate(spots[:max(2, int(len(spots) * amount))]):
        p, _n = on_pile(z, a, -0.2)
        coral(m, q, p, body_normal(z, a), rnd, spine_weights(z), rnd.uniform(1.8, 2.6))
    clumps = [(-4.8, -0.9), (-0.2, 0.55), (3.6, -0.6), (-7.8, 0.85), (1.6, -1.05), (-2.8, 0.05)]
    for k, (z, a) in enumerate(clumps[:max(2, int(len(clumps) * amount))]):
        p, _n = on_pile(z, a, -0.4)
        n = body_normal(z, a)
        for b in range(3 if q.kind != "lo" else 2):
            flat = Vector((rnd.uniform(-1, 1), 0.0, rnd.uniform(-1, 1))).normalized()
            way = (n + Vector((rnd.uniform(-0.4, 0.4), 1.2, rnd.uniform(-0.4, 0.4)))).normalized()
            blade(m, p + flat * 0.3, way, flat, rnd.uniform(4.5, 7.5), 0.6, 8 if q.fine else (4 if q.kind == "game" else 2),
                  5, spine_weights(z), rnd)
    if q.kind == "lo":
        return
    for k in range(int(8 * amount)):
        z = rnd.uniform(-8.0, 4.5)
        a = rnd.uniform(-1.2, 1.2)
        p, _n = on_pile(z, a, -0.3)
        sponge(m, q, p, body_normal(z, a), rnd, spine_weights(z), rnd.uniform(0.6, 0.95))
    # barnacles in clusters: on the plates' edges, the flanks, the shoulders and the tail
    clusters = [(-5.5, 1.35), (-5.5, -1.4), (1.0, 1.45), (1.5, -1.5), (-9.5, 1.2), (6.5, 0.9), (8.5, -0.8), (-2.5, 1.6),
                (-2.0, -1.7), (4.0, 1.6)]
    for z0, a0 in clusters[:int(len(clusters) * amount + 0.5)]:
        for b in range(4 if q.fine else 3):
            z = z0 + rnd.uniform(-0.8, 0.8)
            a = a0 + rnd.uniform(-0.18, 0.18)
            barnacle(m, q, body_at(z, a), body_normal(z, a), rnd.uniform(0.4, 0.6), spine_weights(z))


# ---------------------------------------------------------------- making, weighting, checking, writing

def make(kind):
    q = Q(kind)
    m = Mesh()
    rnd = random.Random(11)
    body(m, q)
    head(m, q)
    for i in range(4):
        leg(m, q, i)
    for sx in (-1.0, 1.0):
        eye(m, q, sx)
        frill(m, q, sx)
    plates(m, q, random.Random(5))
    tail_fin(m, q)
    reef(m, q, random.Random(9))
    name = NAME + {"full": "", "game": "_game", "lo": "_lo"}[kind]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) for p in m.verts], [], m.faces)
    mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.new(name="UV2")
    uv = mesh.uv_layers["UVMap"].data
    uv2 = mesh.uv_layers["UV2"].data
    for poly in mesh.polygons:
        for corner, vi in enumerate(poly.vertices):
            d = m.data[vi]
            uv[poly.loop_start + corner].uv = d[0]
            uv2[poly.loop_start + corner].uv = d[1]
    material = bpy.data.materials.get(NAME) or bpy.data.materials.new(NAME)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.18, 0.4, 0.36, 1.0)
    material.diffuse_color = (0.18, 0.4, 0.36, 1.0)
    mesh.materials.append(material)
    mesh.update()
    winding(name, mesh, m)
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.set_sharp_from_angle(angle=math.radians(50.0))
    mesh.update()
    shading(name, mesh, m)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    # weights
    for b in BONES:
        obj.vertex_groups.new(name=b[0])
    for vi, w in enumerate(m.weights):
        total = sum(w.values())
        for bone, value in w.items():
            if value > 1e-4:
                obj.vertex_groups[bone].add([vi], value / total, "REPLACE")
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    lo = Vector((min(p.x for p in m.verts), min(p.y for p in m.verts), min(p.z for p in m.verts)))
    hi = Vector((max(p.x for p in m.verts), max(p.y for p in m.verts), max(p.z for p in m.verts)))
    print("BUILT %s verts=%d tris=%d box=%s..%s" % (name, len(mesh.vertices), tris, tuple(round(x, 2) for x in lo), tuple(round(x, 2) for x in hi)))
    print("PARTS %s %s" % (name, {k: v for k, v in m.count.items()}))
    return obj


def winding(name, mesh, m):
    bad = {}
    for poly in mesh.polygons:
        out, group = m.out[poly.index]
        if poly.normal.dot(to_b(out)) <= 0.0:
            bad[group] = bad.get(group, 0) + 1
    told = ["%s %d/%d wrong" % (g, bad.get(g, 0), c) for g, c in m.count.items()]
    print("WINDING %s: %s: %s" % (name, "ok" if not bad else "INSIDE OUT", ", ".join(told)))


def shading(name, mesh, m):
    bad = {}
    shown = 0
    normals = mesh.corner_normals
    mesh.calc_loop_triangles()
    for tri in mesh.loop_triangles:
        n = Vector((0.0, 0.0, 0.0))
        for li in tri.loops:
            n += normals[li].vector
        if n.dot(tri.normal) <= 0.0:
            group = m.out[tri.polygon_index][1]
            bad[group] = bad.get(group, 0) + 1
            if shown < 8 and "--why" in ARGS:
                shown += 1
                c = tri.center
                print("  against its corners: %s at %s" % (group, (round(c.x, 2), round(c.z, 2), round(-c.y, 2))))
    print("SHADING %s: %s %s" % (name, "ok" if not bad else "FACES AGAINST THEIR NORMALS", bad))


# ---------------------------------------------------------------- the skeleton and its clips

def make_rig():
    data = bpy.data.armatures.new("ReefBackRig")
    rig = bpy.data.objects.new("ReefBackRig", data)
    bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for name, h, t, parent, hint in BONES:
        eb = data.edit_bones.new(name)
        eb.head = to_b(h)
        eb.tail = to_b(t)
        eb.align_roll(to_b(pole_of(name)))
        eb.use_deform = name != "root"
    for name, h, t, parent, hint in BONES:
        if parent:
            data.edit_bones[name].parent = data.edit_bones[parent]
            data.edit_bones[name].use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    return rig


def frame_of(head, tail, pole):
    """A bone's frame (Godot space): Y along it, Z towards its pole."""
    y = (tail - head).normalized()
    z = (pole - y * pole.dot(y)).normalized()
    x = y.cross(z)
    m = Matrix.Identity(4)
    for r in range(3):
        m[r][0], m[r][1], m[r][2], m[r][3] = x[r], y[r], z[r], head[r]
    return m


def about(pivot, rot):
    return Matrix.Translation(pivot) @ rot.to_4x4() @ Matrix.Translation(-pivot)


def rot_xyz(pitch, yaw, roll):
    """A turn: pitch about X (nose up for +), yaw about Y (nose to its left for +), roll about Z."""
    return (Matrix.Rotation(yaw, 3, "Y") @ Matrix.Rotation(pitch, 3, "X") @ Matrix.Rotation(roll, 3, "Z"))


def two_bone(a, target, l1, l2, pole):
    """Where the knee goes: from `a`, reaching `target`, bending towards `pole`."""
    d = target - a
    dist = min(d.length, (l1 + l2) * 0.999)
    dn = d.normalized()
    x = (l1 * l1 - l2 * l2 + dist * dist) / (2.0 * dist)
    h = math.sqrt(max(l1 * l1 - x * x, 0.0))
    side = (pole - dn * pole.dot(dn)).normalized()
    return a + dn * x + side * h, a + dn * dist


def pose_at(t, walking):
    """Every bone's turn (a rigid transform of Godot space) at a time t (0..1) through the clip."""
    T = {}
    w = 1.0 if walking else 0.0
    s2 = math.sin(TAU * t)
    c4 = math.cos(2 * TAU * t)
    T["root"] = Matrix.Identity(4)
    # (it sags a little each time a foot lifts, sways and rolls with its steps; standing it only breathes)
    bob = -0.16 * (0.5 + 0.5 * c4) * w + 0.06 * math.sin(TAU * t) * (1 - w)
    hips_rot = rot_xyz(0.0, 0.05 * s2 * w, 0.03 * s2 * w)
    T["hips"] = Matrix.Translation(Vector((0.0, bob, 0.0))) @ about(BONE["hips"][1], hips_rot)
    chest_rot = rot_xyz(0.015 * math.sin(TAU * t) * (1 - w), -0.09 * math.sin(TAU * t + 0.3) * w, -0.035 * s2 * w)
    T["chest"] = T["hips"] @ about(BONE["chest"][1], chest_rot)
    T["neck"] = T["chest"] @ about(BONE["neck"][1], rot_xyz(0.03 * math.sin(2 * TAU * t + 0.6) * w + 0.02 * math.sin(TAU * t + 0.5) * (1 - w),
                                                            0.05 * math.sin(TAU * t + 0.9) * w, 0.0))
    T["head"] = T["neck"] @ about(BONE["head"][1], rot_xyz(-0.02 * math.sin(2 * TAU * t + 1.1) * w, -0.045 * math.sin(TAU * t + 1.2) * w, 0.0))
    T["jaw"] = T["head"]
    prev = "hips"
    for k in range(1, 6):
        name = "tail%d" % k
        amp = (0.07 + 0.025 * k) * w + (0.03 + 0.012 * k) * (1 - w)
        yaw = amp * math.sin(TAU * t - 0.75 * k)
        T[name] = T[prev] @ about(BONE[name][1], rot_xyz(0.015 * math.sin(2 * TAU * t - 0.5 * k) * w, yaw, 0.0))
        prev = name
    # the legs: lateral sequence, each foot planted for DUTY of the cycle
    offsets = {"thigh.L": 0.0, "upperarm.L": 0.25, "thigh.R": 0.5, "upperarm.R": 0.75}
    for upper, lower, foot in LEGS:
        parent = "chest" if upper.startswith("upperarm") else "hips"
        f = (t + offsets[upper]) % 1.0
        if not walking:
            dz, lift, pitch = 0.0, 0.0, 0.0
        elif f < DUTY:
            # (planted: it goes back under the body exactly as fast as the body goes forward)
            dz = -STRIDE * DUTY * 0.5 + STRIDE * f
            lift, pitch = 0.0, 0.0
        else:
            u = (f - DUTY) / (1.0 - DUTY)
            e = u * u * (3.0 - 2.0 * u)
            dz = STRIDE * DUTY * 0.5 - STRIDE * DUTY * e
            lift = LIFT * math.sin(PI * u)
            pitch = -0.35 * math.sin(PI * u)
        a_rest, k_rest = BONE[upper][1], BONE[upper][2]
        ank_rest = BONE[lower][2]
        foot_T = Matrix.Translation(Vector((0.0, lift, dz))) @ about(ank_rest, rot_xyz(pitch, 0.0, 0.0))
        T[foot] = foot_T
        ankle = foot_T @ ank_rest
        hip = T[parent] @ a_rest
        pole_rest = pole_of(upper)
        pole = (T[parent].to_3x3() @ pole_rest)
        knee, ankle_reached = two_bone(hip, ankle, (k_rest - a_rest).length, (ank_rest - k_rest).length, pole)
        T[upper] = frame_of(hip, knee, pole) @ frame_of(a_rest, k_rest, pole_rest).inverted()
        T[lower] = frame_of(knee, ankle_reached, pole) @ frame_of(k_rest, ank_rest, pole_rest).inverted()
        # (the foot follows the ankle where the leg could reach)
        T[foot] = Matrix.Translation(ankle_reached - ankle) @ foot_T
    return T


def bake(rig, action_name, walking):
    rig.animation_data_create()
    action = bpy.data.actions.new(action_name)
    rig.animation_data.action = action
    data = rig.data
    rest = {b.name: b.matrix_local.copy() for b in data.bones}
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
    for frame in range(FRAMES + 1):
        t = (frame % FRAMES) / FRAMES
        T = pose_at(t, walking)
        pose = {name: C4 @ T[name] @ C4I @ rest[name] for name in T}
        for pb in rig.pose.bones:
            name = pb.name
            if pb.parent:
                pn = pb.parent.name
                basis = rest[name].inverted() @ rest[pn] @ pose[pn].inverted() @ pose[name]
            else:
                basis = rest[name].inverted() @ pose[name]
            loc, rot, _ = basis.decompose()
            pb.location = loc
            pb.rotation_quaternion = rot
            pb.scale = Vector((1, 1, 1))
            pb.keyframe_insert("location", frame=frame)
            pb.keyframe_insert("rotation_quaternion", frame=frame)
            pb.keyframe_insert("scale", frame=frame)
    # (an action that does not change at all is left out of the export: nudge the root's scale on one key)
    track = rig.animation_data.nla_tracks.new()
    track.name = action_name
    track.strips.new(action_name, 0, action)
    rig.animation_data.action = None
    return action


def export_one(rig, obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_yup=True, use_selection=True,
                              export_animations=True, export_animation_mode="ACTIONS", export_texcoords=True,
                              export_skins=True, export_def_bones=False, export_force_sampling=True,
                              export_frame_range=False, export_anim_single_armature=True)


def render(folder, made, rig):
    scene = bpy.context.scene
    for track in rig.animation_data.nla_tracks:
        track.mute = True
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_cavity = True
    scene.display.shading.show_backface_culling = True
    scene.render.resolution_x, scene.render.resolution_y = 1200, 800
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.06, 0.08)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    # (Blender space: its nose towards +Y, up Z)
    views = [("left", (1, 0, 0.05), (0, 0, 7), 40), ("right", (-1, 0, 0.05), (0, 0, 7), 40), ("front", (0, 1, 0.1), (0, 0, 7), 26),
             ("back", (0, -1, 0.1), (0, 0, 7), 26), ("above", (0.001, 0, 1), (0, 0, 0), 40), ("quarter", (0.9, 0.9, 0.35), (0, 0, 7), 40),
             ("head", (0.7, 1.0, 0.3), (0, 14, 7.5), 13), ("concept", (-1.0, 0.45, 0.12), (0, 0, 7), 40), ("foot", (0.8, 0.9, 0.3), (5.5, 8, 1.5), 7)]
    for prefix, obj in zip(("", "game_", "lo_"), made):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if prefix == "lo_" and view not in ("quarter", "left"):
                continue
            offset = Vector(direction).normalized() * 200.0
            camera.data.ortho_scale = frame
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % (prefix, view))
            bpy.ops.render.render(write_still=True)
    # through a walking step and with the jaw open, the game model
    for other in made:
        other.hide_render = other is not made[1]
    walk = bpy.data.actions["walk"]
    rig.animation_data.action = walk
    for k in range(4):
        scene.frame_set(int(FRAMES * k / 4))
        for view, direction, target, frame in (views[7], views[0]):
            offset = Vector(direction).normalized() * 200.0
            camera.data.ortho_scale = frame
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y").to_euler()
            scene.render.filepath = os.path.join(folder, "walk_%s_%d.png" % (view, k))
            bpy.ops.render.render(write_still=True)
    rig.animation_data.action = None


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.frame_start = 0
    scene.frame_end = FRAMES
    full = make("full")
    game = make("game")
    low = make("lo")
    rig = make_rig()
    for obj in (full, game, low):
        obj.parent = rig
        mod = obj.modifiers.new("Skeleton", "ARMATURE")
        mod.object = rig
    bake(rig, "walk", True)
    bake(rig, "stand", False)
    os.makedirs(OUT, exist_ok=True)
    for obj, ending in ((full, ""), (game, "_game"), (low, "_lo")):
        export_one(rig, obj, os.path.join(OUT, NAME + ending + ".glb"))
    print("RIG bones=%d frames=%d stride=%.2f" % (len(BONES), FRAMES, STRIDE))
    game.location.x = 0.0
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, NAME + ".blend"))
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, game, low], rig)


if __name__ == "__main__":
    main()
