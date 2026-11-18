"""Builds the seahorses (creatures/seahorse), one model of each type at each weight, and exports them for Godot.

Run from the game's root:
    blender --background --factory-startup --python creatures/seahorse/tools/build_seahorse.py
    blender --background --factory-startup --python creatures/seahorse/tools/build_seahorse.py -- <preview folder>
    blender --background --factory-startup --python creatures/seahorse/tools/build_seahorse.py -- <preview folder> pygmy

For each type (TYPES: common, spiny, pygmy; all, or those named after the preview folder) it writes
creatures/seahorse/models/seahorse_<type>.glb (the full model), seahorse_<type>_game.glb (the game model: the same
outline in about a ninth of the triangles) and seahorse_<type>_lo.glb (far off, phones, many at once), and the
editable creatures/seahorse/tools/seahorse_<type>.blend holding all three (this folder has a .gdignore). Each model
is one still mesh with one surface: the shader (seahorse.gdshader) curls its tail (`grip`), buzzes its fins, works
its mouth, bobs it and draws every marking. It prints a WINDING line for each model (nothing is inside out) and a
SHAPE line: the places on each type's model the shader needs (Seahorse.TYPES has them, copied across by hand).

Every type is built 0.15 m tall (LENGTH), from the tip of its tail hanging straight down to the top of its coronet.
**It stands upright: +Y is up, and it faces -Z** (its snout points along -Z, as every other creature's nose does);
+X is its right side. **Its origin is half way up its height, on the line of its tail** (the tail, as built, hangs
straight down along the Y axis; the belly bulges forward of it, towards -Z, and the head and snout are further
forward still).

- THE TRUNK AND TAIL: one skin round a line running up the middle: the tail straight down from the bottom of the
  belly, square in section, tapering to a point; the trunk above it with a round belly in front and the dorsal
  fin's ridge behind, seven-sided, rising to the neck. Bony rings run round it (raised rims, knobbed where they
  cross the long ridges): about eleven on the trunk and twenty-six on the tail.
- THE HEAD: held at right angles to the trunk, horizontal, on the arched neck: a long tube of a snout (short in
  the pygmy), the eyes high on its sides, and a CORONET, a little star-shaped crown, on top.
- THE MOUTH: at the tip of the snout. The upper side of the tip is the head's skin, flat underneath (the roof of
  the mouth); the LOWER JAW is a small part of its own (the shader swings it down about its hinge).
- THE FINS: thin closed solids: a fan of a DORSAL fin on its back above the tail and a pair of small ear-like
  PECTORAL fins behind the head.
- The spiny type has SPIKES on every ridge where the rings cross it; the pygmy is covered in round TUBERCLES.

What a point is, for the shader: vertex colour red the part, as a tenth (0 trunk and tail, 0.1 head, 0.2 lower
jaw, 0.3 eye, 0.4 coronet, 0.5 spike, 0.6 tubercle, 0.7 dorsal, 0.8 pectoral). On the trunk and tail: UV.x how
high (0 the tail's tip, 1 the top of the neck), UV.y how far round from the back line (0 to 1, the right side
first), UV2.x the ring it is on (0 where the tail meets the trunk, + up the trunk, - down the tail; a ring's
raised rim at each whole number). On the head and jaw: UV.x how far along (0 snout tip, 1 back of the head), UV.y
how high (0 bottom, 1 top); blue how much it is inside the mouth. On an eye: UV where a point is on its round
face seen straight on (its middle at 0.5, 0.5). On a fin: UV.x along its rays (0 root, 1 edge), UV.y across it
counted in rays; UV2 and blue the way its flat side faces (x, y, and z as z / 2 + 0.5). On a spike or tubercle:
UV.x from its root (0) to its tip (1). (The glTF writer flips V: what is written here is 1 - v, so that Godot
reads v.)

Everything here is worked out in heights (0.15 m) in Godot space (Y up, snout towards -Z) and written in metres.
"""

import bisect
import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "models")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = ARGS[0] if ARGS else ""

# Kept in step with seahorse.gd and seahorse.gdshader.
FAMILY = "seahorse"
LENGTH = 0.15
TAU = math.tau
TRUNK, HEAD, JAW, EYE, CORONET, SPIKE, BULB, DORSAL, PECTORAL = range(9)
# Where the tail meets the trunk (its root, y) and its tip; the top of the trunk (inside the head).
TAIL_ROOT = -0.06
TIP_Y = -0.5
NECK_TOP = 0.39
# The rings' rims on the trunk run from the tail's root up to here.
RING_TOP = 0.33
# The height of the snout's middle line; where the snout's tube ends and the head begins, where the eye is, where
# the coronet is and the back of the head (z).
SNOUT_Y = 0.383
SNOUT_BASE = -0.15
CROWN_Z = -0.008
OCCIPUT = 0.08

# The trunk: its middle line (y, z), and how far its skin is from that line in front (towards -Z), behind and to
# each side (y, distance); heights. Each type scales these.
TRUNK_Z = [(TIP_Y, 0.0), (TAIL_ROOT, 0.0), (0.0, -0.016), (0.08, -0.024), (0.16, -0.02), (0.24, -0.004),
           (0.3, 0.016), (0.35, 0.038), (NECK_TOP, 0.05)]
TRUNK_FRONT = [(TAIL_ROOT, 0.04), (-0.02, 0.074), (0.04, 0.108), (0.1, 0.108), (0.16, 0.09), (0.22, 0.068),
               (0.28, 0.05), (0.33, 0.042), (0.36, 0.034), (NECK_TOP, 0.022)]
TRUNK_BACK = [(TAIL_ROOT, 0.04), (-0.02, 0.05), (0.04, 0.056), (0.1, 0.058), (0.16, 0.056), (0.22, 0.052),
              (0.28, 0.05), (0.33, 0.05), (0.36, 0.044), (NECK_TOP, 0.028)]
TRUNK_SIDE = [(TAIL_ROOT, 0.038), (-0.02, 0.052), (0.04, 0.062), (0.1, 0.062), (0.16, 0.055), (0.22, 0.047),
              (0.28, 0.041), (0.33, 0.038), (0.36, 0.031), (NECK_TOP, 0.02)]

# The types. `snout`: how long the snout's tube is ahead of SNOUT_BASE, and its radius; `head`: how big the head is
# beside the common one's; `eye`: where (z, y), the eyeball's radius, how far it stands out, how much of its dome
# shows; `trunk`, `width`: the trunk's depth and width beside the common one's; `tail`: its tail's thickness;
# `ridge`, `ring`, `knob`: how high the long ridges, the rings' rims and the knobs where they cross stand out (of
# the radius); `trunk_rings`, `tail_rings`; `spikes`: how long its spikes are (0 none); `bulbs`: how many
# tubercles; `coronet`: the crown's radius and how tall; `dorsal`: its fin's root (y from, to) and length;
# `pectoral`: its fins' length.
TYPES = {
    "common": {
        "snout": (0.11, 0.0165), "head": 1.0, "eye": (-0.068, 0.404, 0.029, 0.012, 0.72),
        "trunk": 1.0, "width": 1.0, "tail": 1.0, "ridge": 0.07, "ring": 0.05, "knob": 0.1,
        "tail_ridge": 0.1, "tail_ring": 0.05, "trunk_rings": 11, "tail_rings": 26,
        "spikes": 0.0, "bulbs": 0, "coronet": (0.017, 0.05), "game": (18, 0, 14), "dorsal": (-0.035, 0.07, 0.062), "pectoral": 0.044,
    },
    "spiny": {
        "snout": (0.135, 0.0145), "head": 0.95, "eye": (-0.07, 0.405, 0.027, 0.012, 0.72),
        "trunk": 0.9, "width": 0.9, "tail": 0.9, "ridge": 0.09, "ring": 0.06, "knob": 0.12,
        "tail_ridge": 0.12, "tail_ring": 0.06, "trunk_rings": 11, "tail_rings": 26,
        "spikes": 0.034, "bulbs": 0, "coronet": (0.016, 0.055), "game": (11, 0, 11), "dorsal": (-0.035, 0.065, 0.058), "pectoral": 0.042,
    },
    "pygmy": {
        "snout": (0.035, 0.024), "head": 1.18, "eye": (-0.064, 0.41, 0.036, 0.015, 0.72),
        "trunk": 1.25, "width": 1.3, "tail": 1.3, "ridge": 0.0, "ring": 0.015, "knob": 0.0,
        "tail_ridge": 0.03, "tail_ring": 0.02, "trunk_rings": 8, "tail_rings": 18,
        "spikes": 0.0, "bulbs": 1, "coronet": (0.019, 0.04), "game": (14, 11, 14), "dorsal": (-0.03, 0.06, 0.05), "pectoral": 0.04,
    },
}
NAMES = list(TYPES)
WANTED = [name for name in ARGS[1:] if name in NAMES] or NAMES

# The game model's points round the trunk and tail (degrees from the back line, to the right first); each type's
# "game" is how many rings of points down its tail, up its trunk (0: one on each rim and one between) and along
# its head.
GAME_ANGLES = [0.0, 42.0, 90.0, 128.0, 156.0, 180.0, 204.0, 232.0, 270.0, 318.0]

GAME = False
LOW = False


def to_b(p):
    return Vector((p.x, -p.z, p.y))


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def curve(points):
    """A smooth line through (x, y) points that never overshoots them."""
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    n = len(xs)
    h = [xs[i + 1] - xs[i] for i in range(n - 1)]
    d = [(ys[i + 1] - ys[i]) / h[i] for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        if d[i - 1] * d[i] > 0.0:
            w1 = 2.0 * h[i] + h[i - 1]
            w2 = h[i] + 2.0 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])

    def f(x):
        if x <= xs[0]:
            return ys[0]
        if x >= xs[-1]:
            return ys[-1]
        i = bisect.bisect_right(xs, x) - 1
        t = (x - xs[i]) / h[i]
        t2, t3 = t * t, t * t * t
        return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h[i] * m[i]
                + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h[i] * m[i + 1])
    return f


def spread(lines_at, a, b, n, forced=(), even=0.35):
    """n + 1 places from a to b (a and b among them) for the game model, closer together where the lines
    `lines_at(t)` gives (a list of (x, y) points, one on each line) bend, `even` of the whole spread evenly. Each
    place in `forced` replaces the nearest place."""
    m = 800
    ts = [a + (b - a) * i / m for i in range(m + 1)]
    pts = [lines_at(t) for t in ts]
    w = [0.0] * m
    for k in range(len(pts[0])):
        seg = [(pts[i + 1][k][0] - pts[i][k][0], pts[i + 1][k][1] - pts[i][k][1]) for i in range(m)]
        lens = [math.hypot(*d) for d in seg]
        for i in range(1, m):
            if lens[i] > 1e-12 and lens[i - 1] > 1e-12:
                c = (seg[i][0] * seg[i - 1][0] + seg[i][1] * seg[i - 1][1]) / (lens[i] * lens[i - 1])
                turn = math.acos(max(-1.0, min(1.0, c)))
                w[i] += math.sqrt(turn * 0.5 * (lens[i] + lens[i - 1]))
    total = sum(w)
    share = (even * total / m) if total > 0.0 else 1.0
    w = [x + share for x in w]
    acc = [0.0]
    for x in w:
        acc.append(acc[-1] + x)
    out = [a]
    for j in range(1, n):
        want = acc[-1] * j / n
        i = min(bisect.bisect_right(acc, want) - 1, m - 1)
        f = (want - acc[i]) / max(acc[i + 1] - acc[i], 1e-12)
        out.append(ts[i] + (ts[i + 1] - ts[i]) * f)
    out.append(b)
    for f in forced:
        if a < f < b:
            j = min(range(1, len(out) - 1), key=lambda j: abs(out[j] - f))
            out[j] = f
    return sorted(set(out))


class Section:
    """A lofted skin along the head (s 0 snout tip to 1 back of the head): its top line, bottom line, half width,
    how far up from the bottom it is widest (0..1), how boxy its upper and lower halves are (2 an ellipse)."""

    def __init__(self, first, last, top, bot, hw, ycf, nt, nb):
        self.first = first
        self.last = last
        self.f = [top, bot, hw, ycf, nt, nb]

    def at(self, s):
        return [f(s) for f in self.f]

    def top(self, s):
        return self.f[0](s)

    def bot(self, s):
        return self.f[1](s)

    def x_at(self, s, y):
        top, bot, hw, ycf, nt, nb = self.at(s)
        yc = bot + ycf * (top - bot)
        if y >= yc:
            u, n = (y - yc) / max(top - yc, 1e-9), nt
        else:
            u, n = (yc - y) / max(yc - bot, 1e-9), nb
        u = max(0.0, min(1.0, u))
        return hw * (1.0 - u ** n) ** (1.0 / n)

    def outline(self, s, half):
        """half + 1 points down its right side from the top line to the bottom line: (x, y)."""
        top, bot, hw, ycf, nt, nb = self.at(s)
        yc = bot + ycf * (top - bot)
        dense = []
        steps = 160
        for i in range(steps + 1):
            phi = math.pi * i / steps
            c, sn = math.cos(phi), max(math.sin(phi), 0.0)
            if c >= 0.0:
                dense.append((hw * sn ** (2.0 / nt), yc + (top - yc) * c ** (2.0 / nt)))
            else:
                dense.append((hw * sn ** (2.0 / nb), yc - (yc - bot) * (-c) ** (2.0 / nb)))
        dense[0] = (0.0, top)
        dense[-1] = (0.0, bot)
        acc = [0.0]
        for i in range(steps):
            acc.append(acc[-1] + math.hypot(dense[i + 1][0] - dense[i][0], dense[i + 1][1] - dense[i][1]))
        out = []
        for j in range(half + 1):
            want = acc[-1] * j / half
            i = min(bisect.bisect_right(acc, want) - 1, steps - 1)
            span = acc[i + 1] - acc[i]
            t = (want - acc[i]) / span if span > 1e-12 else 0.0
            out.append((lerp(dense[i][0], dense[i + 1][0], t), lerp(dense[i][1], dense[i + 1][1], t)))
        return out


class Part:
    """One closed piece: points (heights), what each is for the shader, and faces. `done` welds it, turns every
    face outward and checks that."""

    def __init__(self, name):
        self.name = name
        self.verts = []
        self.data = []
        self.faces = []

    def add(self, p, uv, uv2, colour):
        self.verts.append(Vector(p))
        self.data.append((uv, uv2, colour))
        return len(self.verts) - 1

    def loft(self, rings, closed=True):
        for a, b in zip(rings, rings[1:]):
            n = len(a)
            for j in range(n if closed else n - 1):
                self.faces.append((a[j], a[(j + 1) % n], b[(j + 1) % n], b[j]))

    def cap(self, ring, hub):
        n = len(ring)
        for j in range(n):
            self.faces.append((ring[j], ring[(j + 1) % n], hub))

    def mirrored(self, name, flip):
        other = Part(name)
        for p, d in zip(self.verts, self.data):
            other.add((-p.x, p.y, p.z), *flip(d))
        other.faces = list(self.faces)
        return other

    @staticmethod
    def inside_out(bm):
        """How many of a closed solid's faces face inwards: a line out of a face, the way the face faces, comes out
        through the solid's skin an even number of times."""
        cut = bm.copy()
        bmesh.ops.triangulate(cut, faces=cut.faces)
        cut.normal_update()
        tree = BVHTree.FromBMesh(cut)
        wrong = 0
        counted = 0
        for f in cut.faces:
            if f.calc_area() > 1e-12:
                counted += 1
                at = f.calc_center_median() + f.normal * 1e-6
                hits = 0
                while hits < 40:
                    hit = tree.ray_cast(at, f.normal)
                    if hit[0] is None:
                        break
                    hits += 1
                    at = hit[0] + f.normal * 1e-6
                if hits % 2:
                    wrong += 1
        cut.free()
        return wrong, counted

    def done(self):
        bm = bmesh.new()
        uv = bm.loops.layers.uv.new("uv")
        uv2 = bm.loops.layers.uv.new("uv2")
        colour = bm.loops.layers.float_color.new("colour")
        made = [bm.verts.new(to_b(p * LENGTH)) for p in self.verts]
        for face in self.faces:
            try:
                f = bm.faces.new([made[i] for i in face])
            except ValueError:
                continue
            for loop, i in zip(f.loops, face):
                d = self.data[i]
                loop[uv].uv = d[0]
                loop[uv2].uv = d[1]
                loop[colour] = (d[2][0], d[2][1], d[2][2], 1.0)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-8)
        for f in list(bm.faces):
            if len(f.verts) == 4:
                off = [loop for loop in f.loops if abs(loop.vert.co.x) > 1e-9]
                if len(off) == 1:
                    bmesh.ops.connect_verts(bm, verts=[off[0].vert, off[0].link_loop_next.link_loop_next.vert])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.normal_update()
        wrong, counted = self.inside_out(bm)
        if wrong * 2 > counted:
            bmesh.ops.reverse_faces(bm, faces=bm.faces)
            bm.normal_update()
            wrong, counted = self.inside_out(bm)
        out = []
        for f in bm.faces:
            out.append([(loop.vert.co.copy(), tuple(loop[uv].uv), tuple(loop[uv2].uv), tuple(loop[colour]))
                        for loop in f.loops])
        bm.free()
        return out, wrong, counted


def flip_side(d):
    return d[0], (-d[1][0], d[1][1]), d[2]


# ---------------------------------------------------------------------------------------------------------------
# The type being built (set by `use`).
P = {}
SHAPE = {}


def use(name):
    """Makes `name` the shape being built: its trunk, tail and head."""
    global P
    P = dict(TYPES[name])
    P["name"] = name
    k, wk = P["trunk"], P["width"]
    P["z"] = curve(TRUNK_Z)
    P["front"] = curve([(y, d * k) for y, d in TRUNK_FRONT])
    P["back"] = curve([(y, d * lerp(1.0, k, 0.6)) for y, d in TRUNK_BACK])
    P["side"] = curve([(y, d * wk) for y, d in TRUNK_SIDE])
    # The tail: square, from its root's size to a point; how big it is down its length.
    root = P["side"](TAIL_ROOT)
    tk = P["tail"]

    def tail_size(y):
        u = (TAIL_ROOT - y) / (TAIL_ROOT - TIP_Y)
        return lerp(root, lerp(root, 0.0055 * tk, 1.0), min(max(u, 0.0), 1.0) ** 0.75) * (1.0 - smooth(0.975, 1.0, u) * 0.6)
    P["tail_size"] = tail_size
    # The rings: a coordinate up the trunk and down the tail, a rim at each whole number. Up the trunk evenly; down
    # the tail each ring as long as the tail is thick there (to a power), `tail_rings` of them.
    up = (RING_TOP - TAIL_ROOT) / P["trunk_rings"]
    steps = 600
    ys = [TAIL_ROOT - (TAIL_ROOT - TIP_Y) * i / steps for i in range(steps + 1)]
    inv = [1.0 / max(tail_size(y), 0.004) ** 0.7 for y in ys]
    acc = [0.0]
    for i in range(steps):
        acc.append(acc[-1] + 0.5 * (inv[i] + inv[i + 1]) * (ys[i] - ys[i + 1]))
    scale = P["tail_rings"] / acc[-1]

    def ring_at(y):
        if y >= TAIL_ROOT:
            return (y - TAIL_ROOT) / up
        i = min(int((TAIL_ROOT - y) / (TAIL_ROOT - TIP_Y) * steps), steps - 1)
        t = ((TAIL_ROOT - y) - (TAIL_ROOT - ys[i])) / ((TAIL_ROOT - TIP_Y) / steps)
        return -lerp(acc[i], acc[i + 1], t) * scale
    P["ring_at"] = ring_at
    P["ring_up"] = up
    # The head: a Section from the snout's tip to the back of the head. z = tip + s * head length.
    snout, sr = P["snout"]
    hk = P["head"]
    tip = SNOUT_BASE - snout
    hl = OCCIPUT - tip
    P["tip"], P["hl"] = tip, hl
    ez = P["eye"][0]

    def s_of(z):
        return (z - tip) / hl
    top = curve([(0.0, SNOUT_Y + sr * 0.9), (s_of(SNOUT_BASE), SNOUT_Y + sr + 0.002),
                 (s_of(SNOUT_BASE + 0.035), SNOUT_Y + 0.03 * hk), (s_of(ez), SNOUT_Y + 0.062 * hk),
                 (s_of(CROWN_Z), SNOUT_Y + 0.072 * hk), (s_of(CROWN_Z + 0.045), SNOUT_Y + 0.066 * hk),
                 (s_of(OCCIPUT - 0.025), SNOUT_Y + 0.045 * hk), (1.0, SNOUT_Y + 0.012)])
    bot = curve([(0.0, SNOUT_Y - sr * 0.9), (s_of(SNOUT_BASE), SNOUT_Y - sr - 0.002),
                 (s_of(SNOUT_BASE + 0.035), SNOUT_Y - 0.026 * hk), (s_of(ez), SNOUT_Y - 0.042 * hk),
                 (s_of(CROWN_Z), SNOUT_Y - 0.054 * hk), (s_of(CROWN_Z + 0.045), SNOUT_Y - 0.056 * hk),
                 (s_of(OCCIPUT - 0.025), SNOUT_Y - 0.04 * hk), (1.0, SNOUT_Y - 0.012)])
    hw = curve([(0.0, 0.0), (0.006 / hl, sr * 0.85), (s_of(SNOUT_BASE), sr), (s_of(SNOUT_BASE + 0.035), 0.028 * hk),
                (s_of(ez), 0.042 * hk), (s_of(CROWN_Z), 0.046 * hk), (s_of(CROWN_Z + 0.045), 0.044 * hk),
                (s_of(OCCIPUT - 0.025), 0.033 * hk), (1.0, 0.0)])
    # The mouth: the line of the mouth at the tip, the jaw's hinge 0.028 behind the tip.
    hs = 0.028 / hl
    hy = SNOUT_Y - 0.0045
    ym = SNOUT_Y - 0.0015
    P["hinge"] = (hs, hy)

    def roof(s):
        return lerp(ym, hy, min(s / hs, 1.0))

    def head_bot(s):
        return lerp(roof(s), bot(s), smooth(hs - 0.004 / hl, hs + 0.012 / hl, s))
    P["sil_top"], P["sil_bot"], P["sil_hw"] = top, bot, hw
    P["head_skin"] = Section(0.0, 1.0, top, head_bot, hw, lambda s: 0.45,
                             lambda s: 2.0 + 0.4 * smooth(0.4, 0.6, s), lambda s: lerp(3.0, 2.0, smooth(hs, hs + 0.05, s)))
    first = 0.002 / hl
    last = hs + 0.02 / hl

    def jaw_bot(s):
        return bot(s) + 0.0015 * smooth(hs, last, s)

    def jaw_top(s):
        if s <= hs:
            return max(roof(s) + 0.0008, jaw_bot(s) + 0.0012)
        return lerp(roof(hs) + 0.0008, jaw_bot(s) + 0.0005, smooth(hs, last, s))

    def jaw_hw(s):
        return 0.9 * hw(s) * min(1.0, max(s - first, 0.0) / (0.003 / hl)) ** 0.5 * (1.0 - smooth(hs + 0.006 / hl, last, s))
    P["jaw_skin"] = Section(first, last, jaw_top, jaw_bot, jaw_hw, lambda s: 0.75, lambda s: 3.5, lambda s: 2.0)


def head_z(s):
    return P["tip"] + s * P["hl"]


def head_frame(s, y):
    """A place on the head's right side: the point, the way out of the skin, and the way up along it."""
    skin = P["head_skin"]
    e = 0.002
    x = skin.x_at(s, y)
    dy = (skin.x_at(s, y + e) - skin.x_at(s, y - e)) / (2 * e)
    dz = (skin.x_at(s + e / P["hl"], y) - skin.x_at(s - e / P["hl"], y)) / (2 * e)
    return Vector((x, y, head_z(s))), Vector((1.0, -dy, -dz)).normalized(), Vector((dy, 1.0, 0.0)).normalized()


# ---------------------------------------------------------------------------------------------------------------
# The trunk and tail.

def ridges(y, phi):
    """How much a place round the body (phi from the back line, + to the right) is on one of its long ridges
    (0..1): seven round the trunk, one down the middle of the back; four at the corners of the tail."""
    tail = smooth(TAIL_ROOT + 0.025, TAIL_ROOT - 0.02, y)
    trunk_r = (0.5 + 0.5 * math.cos(7.0 * phi)) ** 6
    tail_r = (0.5 - 0.5 * math.cos(4.0 * phi)) ** 6
    return lerp(trunk_r, tail_r, tail), tail


def rim(ring):
    """How much a place is on a ring's raised rim (0..1)."""
    return (0.5 + 0.5 * math.cos(TAU * ring)) ** 4


def tube_frame(y):
    """The middle line at height y: the point, the way up it, the way back (towards +Z) across it."""
    e = 0.002
    z = P["z"](y)
    up = Vector((0.0, 2 * e, P["z"](y + e) - P["z"](y - e))).normalized()
    back = Vector((0.0, -up.z, up.y))
    return Vector((0.0, y, z)), up, back


def section(y):
    """How far the skin is from the middle line at y: in front, behind, to the side; and how square (2 round)."""
    if y >= TAIL_ROOT:
        fade = 1.0 - smooth(NECK_TOP - 0.03, NECK_TOP, y) * 0.75
        return P["front"](y) * fade, P["back"](y) * fade, P["side"](y) * fade, 2.2
    size = P["tail_size"](y)
    return size, size, size, lerp(2.2, 3.2, smooth(TAIL_ROOT, TAIL_ROOT - 0.04, y))


def tube_point(y, phi, lift=0.0, mean_rims=False):
    """A point on the skin of the trunk or tail at height y, phi round from the back line (+ to the right); `lift`
    takes it that much further out (heights)."""
    centre, up, back = tube_frame(y)
    front, behind, side, n = section(y)
    c, sn = math.cos(phi), math.sin(phi)
    depth = behind if c >= 0.0 else front
    x = side * math.copysign(abs(sn) ** (2.0 / n), sn)
    b = depth * math.copysign(abs(c) ** (2.0 / n), c)
    r_ridge, tail = ridges(y, phi)
    ring = P["ring_at"](y)
    # (the game model, whose rings of points do not fall on the rims: their average height, 70 / 256)
    on_rim = 0.2734 if mean_rims else rim(ring)
    ridge_amp = lerp(P["ridge"], P["tail_ridge"], tail)
    ring_amp = lerp(P["ring"], P["tail_ring"], tail)
    grow = 1.0 + ridge_amp * r_ridge + ring_amp * on_rim + P["knob"] * r_ridge * on_rim
    if y > RING_TOP:
        grow = 1.0 + (grow - 1.0) * (1.0 - smooth(RING_TOP, RING_TOP + 0.03, y))
    radial = Vector((x, 0.0, 0.0)) + back * b
    out = centre + radial * grow
    if lift:
        out += tube_normal(y, phi) * lift
    return out


def tube_normal(y, phi):
    e = 0.0015
    a = tube_point(y + e, phi) - tube_point(y - e, phi)
    b = tube_point(y, phi + e * 4.0) - tube_point(y, phi - e * 4.0)
    n = b.cross(a).normalized()
    centre = tube_frame(y)[0]
    if n.dot(tube_point(y, phi) - centre) < 0.0:
        n = -n
    return n


def mean_rims_at(y):
    """Whether the game model's ring of points at y stands for the rims' average height: on the tail, where its
    rings of points do not fall on the rims (on the trunk they fall on each rim and between)."""
    return y < TAIL_ROOT - 0.001


def hull_of(y):
    """The convex hull of the full model's cross-section at y, in the plane of the section: (x, how far back)
    about its middle. Seen from any side, a section shows no more than its hull."""
    centre, up, back = tube_frame(y)
    pts = []
    for k in range(240):
        p = tube_point(y, TAU * k / 240, mean_rims=mean_rims_at(y)) - centre
        pts.append((p.x, p.dot(back)))
    pts = sorted(set(pts))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0.0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0.0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def on_hull(y, phi, hull):
    """The game model's point at phi: where the line from the middle through the full model's point there meets
    the hull of the full model's section."""
    centre, up, back = tube_frame(y)
    p = tube_point(y, phi, mean_rims=mean_rims_at(y)) - centre
    d = (p.x, p.dot(back))
    length = math.hypot(*d)
    if length < 1e-9:
        return centre + p
    dx, dy = d[0] / length, d[1] / length
    best = length
    for i in range(len(hull)):
        a, b = hull[i], hull[(i + 1) % len(hull)]
        ex, ey = b[0] - a[0], b[1] - a[1]
        den = dx * ey - dy * ex
        if abs(den) < 1e-12:
            continue
        t = (a[0] * ey - a[1] * ex) / den
        u = (a[0] * dy - a[1] * dx) / den
        if t > 0.0 and -1e-9 <= u <= 1.0 + 1e-9:
            best = t
            break
    return centre + Vector((dx * best, 0.0, 0.0)) + back * (dy * best)


def tube_places():
    """The heights of the rings of points up the trunk and tail, bottom to top (the tip and the neck's top are
    closed by a point each)."""
    ring_at = P["ring_at"]
    if GAME:
        # (the trunk's on each rim and half way between, so that its knobbed outline keeps its teeth; the tail's
        # where its outline bends)
        tail = spread(lambda y: [(y, P["tail_size"](y)), (y, -P["tail_size"](y))], TIP_Y + 0.004, TAIL_ROOT, P["game"][0])
        if P["game"][1]:
            # (a smooth trunk, as the pygmy's: where its outline bends)
            trunk = spread(lambda y: [(y, P["z"](y) - P["front"](y)), (y, P["z"](y) + P["back"](y)), (y, P["side"](y))],
                           TAIL_ROOT, NECK_TOP - 0.004, P["game"][1])
        else:
            trunk = [y_of_ring(k * 0.5) for k in range(2 * P["trunk_rings"] + 1)]
            trunk += [lerp(RING_TOP, NECK_TOP - 0.004, i / 3) for i in (1, 2, 3)]
        return sorted(set(round(y, 7) for y in tail + trunk))
    if LOW:
        tail_n, trunk_n = 8, 6
        tail = spread(lambda y: [(y, P["tail_size"](y)), (y, -P["tail_size"](y))], TIP_Y + 0.004, TAIL_ROOT, tail_n)
        trunk = spread(lambda y: [(y, P["z"](y) - P["front"](y)), (y, P["z"](y) + P["back"](y)), (y, P["side"](y))],
                       TAIL_ROOT, NECK_TOP - 0.004, trunk_n)
        return sorted(set(tail + trunk))
    # The full model: points every so often round each ring, more on the trunk.
    places = []
    lo_ring, hi_ring = ring_at(TIP_Y + 0.004), ring_at(RING_TOP)
    # (down the tail: four to a ring, found by the ring coordinate)
    ys = [TIP_Y + 0.004 + (NECK_TOP - 0.004 - TIP_Y - 0.004) * i / 4000 for i in range(4001)]
    rs = [ring_at(y) for y in ys]
    want = []
    r = lo_ring
    while r < 0.0:
        want.append(r)
        r = math.floor(r * 4.0 + 1e-6) / 4.0 + 0.25
    r = 0.0
    while r < hi_ring:
        want.append(r)
        r += 1.0 / 6.0
    for w in want:
        i = min(bisect.bisect_left(rs, w), len(rs) - 1)
        places.append(ys[i])
    places += [lerp(RING_TOP, NECK_TOP - 0.004, i / 5) for i in range(6)]
    places.append(TIP_Y + 0.004)
    return sorted(set(round(y, 6) for y in places))


def trunk_and_tail():
    part = Part("trunk")
    # (the game model's ten points round: the back and front lines, each side's middle, and between)
    angles = [math.radians(a) for a in GAME_ANGLES] if GAME else [TAU * j / (8 if LOW else 28) for j in range(8 if LOW else 28)]
    around = len(angles)
    rings = []
    for y in tube_places():
        ring = []
        ring_c = P["ring_at"](y)
        # (round from the back line down the right side and back up the left; the back line twice, 0 and 1)
        hull = hull_of(y) if GAME else None
        for j in range(around + 1):
            phi = angles[j] if j < around else TAU
            p = on_hull(y, phi, hull) if GAME else tube_point(y, phi)
            ring.append(part.add(p, (y + 0.5, 1.0 - j / around), (ring_c, 1.0), (TRUNK / 10.0, 0.0, 0.0)))
        rings.append(ring)
    part.loft(rings, closed=False)
    # (closed by a point at the tail's tip and at the top of the neck, inside the head)
    tip = part.add(Vector((0.0, TIP_Y, 0.0)), (0.0, 0.5), (P["ring_at"](TIP_Y), 1.0), (TRUNK / 10.0, 0.0, 0.0))
    top = part.add(tube_frame(NECK_TOP)[0], (1.0, 0.5), (P["ring_at"](NECK_TOP), 1.0), (TRUNK / 10.0, 0.0, 0.0))
    for j in range(around):
        part.faces.append((rings[0][j + 1], rings[0][j], tip))
        part.faces.append((rings[-1][j], rings[-1][j + 1], top))
    return part


# ---------------------------------------------------------------------------------------------------------------
# The head, its jaw, eyes and coronet.

def head():
    part = Part("head")
    skin = P["head_skin"]
    hs = P["hinge"][0]
    hl = P["hl"]
    ez = (P["eye"][0] - P["tip"]) / hl
    ball = P["eye"][2] / hl
    cz = (CROWN_Z - P["tip"]) / hl
    if GAME:
        places = spread(lambda s: [(s, P["sil_top"](s)), (s, P["sil_bot"](s)), (s, P["sil_hw"](s))], 0.0, 1.0, P["game"][2],
                        (hs, hs + 0.008 / hl, ez - ball * 0.7, ez + ball * 0.7))
        half = 6
    elif LOW:
        places = [0.0, hs, 0.25, 0.45, 0.6, 0.75, 0.9, 1.0]
        half = 3
    else:
        places = [hs * (i / 6) for i in range(6)] + [lerp(hs, 1.0, (i / 50)) for i in range(51)]
        half = 12
    rings = []
    for s in sorted(set(places)):
        side = skin.outline(s, half)
        top, bot = skin.top(s), skin.bot(s)
        yc = bot + skin.at(s)[3] * (top - bot)
        ring = []
        for j in list(range(half + 1)) + list(range(half, 0, -1)):
            x, y = side[j]
            sign = 1.0 if len(ring) <= half else -1.0
            h = (y - bot) / max(top - bot, 1e-9)
            roof = smooth(0.4, 0.1, (y - bot) / max(yc - bot, 1e-9)) * smooth(hs + 0.006 / hl, hs - 0.002 / hl, s)
            ring.append(part.add((sign * x, y, head_z(s)), (s, 1.0 - h), (0.0, 1.0), (HEAD / 10.0, 0.0, roof)))
        rings.append(ring)
    part.loft(rings)
    return part


def jaw():
    part = Part("jaw")
    skin = P["jaw_skin"]
    hs = P["hinge"][0]
    hl = P["hl"]
    first, last = skin.first, skin.last
    if GAME or LOW:
        places = [first, lerp(first, hs, 0.5), hs, hs + 0.006 / hl, last]
        half = 3 if GAME else 2
    else:
        places = [lerp(first, last, (i / 10) ** 1.2) for i in range(11)]
        half = 5
    rings = []
    for s in places:
        side = skin.outline(s, half)
        top, bot = skin.top(s), skin.bot(s)
        yc = bot + skin.at(s)[3] * (top - bot)
        ring = []
        for j in list(range(half + 1)) + list(range(half, 0, -1)):
            x, y = side[j]
            sign = 1.0 if len(ring) <= half else -1.0
            h = (y - bot) / max(top - bot, 1e-9)
            inside = smooth(0.55, 0.92, (y - yc) / max(top - yc, 1e-9)) if y > yc else 0.0
            inside *= smooth(hs + 0.012 / hl, hs - 0.001 / hl, s)
            ring.append(part.add((sign * x, y, head_z(s)), (s, 1.0 - h), (0.0, 1.0), (JAW / 10.0, 0.0, inside)))
        rings.append(ring)
    part.loft(rings)
    return part


def eye():
    """The right eye: a dome set high in the side of the head."""
    part = Part("eye")
    ez, ey, ball, stands, shown = P["eye"]
    s = (ez - P["tip"]) / P["hl"]
    at, out, up = head_frame(s, ey)
    SHAPE["eye_skin"] = at.copy()
    SHAPE["eye_out"] = out.copy()
    along = up.cross(out).normalized()
    seen = math.sqrt(1.0 - (1.0 - stands / ball) ** 2)
    reach = math.asin(min(seen / shown, 0.999))
    centre = at - out * (ball - stands)
    rows = 2 if (LOW or GAME) else 6
    around = 24 if GAME else (8 if LOW else 24)
    rings = []
    for i in range(rows + 1):
        a = reach * i / rows
        ring = []
        for k in range(around):
            q = TAU * k / around
            p = centre + out * (ball * math.cos(a)) + (up * math.cos(q) + along * math.sin(q)) * (ball * math.sin(a))
            across = 0.5 * 0.644 * math.sin(a) / seen
            ring.append(part.add(p, (0.5 + across * math.cos(q), 1.0 - (0.5 + across * math.sin(q))), (0.0, 1.0),
                                 (EYE / 10.0, 0.0, 0.0)))
        rings.append(ring)
    part.loft(rings)
    hub = part.add(centre + out * (ball * math.cos(reach) - 0.004), (0.5, 0.5), (0.0, 1.0), (EYE / 10.0, 0.0, 0.0))
    part.cap(list(reversed(rings[-1])), hub)
    return part


def coronet():
    """The crown on top of the head: a short column, star-shaped in section, its points standing up round its top."""
    part = Part("coronet")
    radius, tall = P["coronet"]
    top_y = 0.5
    s = (CROWN_Z - P["tip"]) / P["hl"]
    base_y = P["sil_top"](s) - 0.012
    points = 5
    stations = [0.0, 0.7, 1.0] if (GAME or LOW) else [i / 8 for i in range(9)]
    rings = []
    for t in stations:
        y = lerp(base_y, top_y, t)
        ring = []
        flare = 1.0 + 0.25 * smooth(0.55, 1.0, t)
        for k in range(points * 2):
            q = TAU * k / (points * 2)
            r = radius * (1.0 if k % 2 == 0 else 0.55) * flare * (1.0 - 0.15 * t)
            if k % 2 == 1:
                r *= 1.0 - 0.25 * smooth(0.8, 1.0, t)
            ring.append(part.add((r * math.sin(q), y, CROWN_Z + r * math.cos(q)), (t, 0.5), (0.0, 1.0),
                                 (CORONET / 10.0, 0.0, 0.0)))
        rings.append(ring)
    part.loft(rings)
    # (its top dished between the points)
    hub = part.add((0.0, top_y - 0.008, CROWN_Z), (1.0, 0.5), (0.0, 1.0), (CORONET / 10.0, 0.0, 0.0))
    part.cap(rings[-1], hub)
    bottom = part.add((0.0, base_y - 0.004, CROWN_Z), (0.0, 0.5), (0.0, 1.0), (CORONET / 10.0, 0.0, 0.0))
    part.cap(list(reversed(rings[0])), bottom)
    return part


# ---------------------------------------------------------------------------------------------------------------
# Spikes and tubercles.

def cone(name, kind, root, out, long, thick, sides, sink):
    """A spike: a cone from `root` (sunk `sink` into the skin) straight out along `out`."""
    part = Part(name)
    out = out.normalized()
    side_a = out.cross(Vector((0.0, 1.0, 0.0)) if abs(out.y) < 0.9 else Vector((1.0, 0.0, 0.0))).normalized()
    side_b = out.cross(side_a).normalized()
    base = root - out * sink
    stations = [0.0, 0.5, 1.0] if sides > 3 else [0.0, 1.0]
    rings = []
    for t in stations:
        if t >= 1.0:
            rings.append([part.add(base + out * (long + sink), (1.0, 0.5), (0.0, 1.0), (kind / 10.0, 0.0, 0.0))])
            continue
        ring = []
        for k in range(sides):
            q = TAU * (k + 0.5) / sides
            p = base + out * ((long + sink) * t) + (side_a * math.cos(q) + side_b * math.sin(q)) * (thick * (1.0 - t) ** 1.2)
            ring.append(part.add(p, (t, 0.5), (0.0, 1.0), (kind / 10.0, 0.0, 0.0)))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        if len(b) == 1:
            part.cap(a, b[0])
        else:
            part.loft([a, b])
    if sides == 3:
        part.faces.append(tuple(reversed(rings[0])))
    else:
        hub = part.add(base - out * 0.0005, (0.0, 0.5), (0.0, 1.0), (kind / 10.0, 0.0, 0.0))
        part.cap(list(reversed(rings[0])), hub)
    return part


def bulb(name, centre, out, radius, around, rows):
    """A tubercle: a round knob, a little more than half of it out of the skin."""
    part = Part(name)
    out = out.normalized()
    side_a = out.cross(Vector((0.0, 1.0, 0.0)) if abs(out.y) < 0.9 else Vector((1.0, 0.0, 0.0))).normalized()
    side_b = out.cross(side_a).normalized()
    if GAME:
        radius *= 1.12 / math.cos(math.pi / around)
    middle = centre + out * (radius * 0.25)
    rings = []
    for i in range(1, rows):
        a = math.pi * i / rows
        ring = []
        for k in range(around):
            q = TAU * k / around
            p = middle + out * (radius * math.cos(a)) + (side_a * math.cos(q) + side_b * math.sin(q)) * (radius * math.sin(a))
            ring.append(part.add(p, (1.0 - i / rows, 0.5), (0.0, 1.0), (BULB / 10.0, 0.0, 0.0)))
        rings.append(ring)
    part.loft(rings)
    top = part.add(middle + out * radius, (1.0, 0.5), (0.0, 1.0), (BULB / 10.0, 0.0, 0.0))
    under = part.add(middle - out * radius, (0.0, 0.5), (0.0, 1.0), (BULB / 10.0, 0.0, 0.0))
    part.cap(rings[0], top)
    part.cap(list(reversed(rings[-1])), under)
    return part


def ridge_angles(tail):
    """The long ridges' places round the body (phi), right side and the middle line."""
    if tail:
        return [math.pi * 0.25, math.pi * 0.75, -math.pi * 0.25, -math.pi * 0.75]
    return [TAU * k / 7.0 for k in range(-3, 4)]


def y_of_ring(ring):
    lo, hi = TIP_Y + 0.004, NECK_TOP
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if P["ring_at"](mid) < ring:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def spikes():
    """The spiny type's spikes: one where each ring's rim crosses each long ridge (none down the front of the
    belly), the tail's on every other ring and smaller towards its tip; a few on the head."""
    made = []
    long = P["spikes"]
    sides = 6 if not (GAME or LOW) else 3
    for ring in range(1, P["trunk_rings"] + 1):
        y = y_of_ring(ring)
        for phi in ridge_angles(False):
            if abs(phi) > 2.5 or (abs(phi) > 1.5 and ring % 2 == 0):
                continue
            made.append(cone("spike", SPIKE, tube_point(y, phi), tube_normal(y, phi) + Vector((0, 0.15, 0)),
                             long * (0.75 if abs(phi) > 1.5 else 1.0), 0.0075, sides, 0.004))
    for ring in range(1, P["tail_rings"] - 5, 2):
        if LOW and ring % 4 != 1:
            continue
        y = y_of_ring(-ring)
        size = P["tail_size"](y) / P["tail_size"](TAIL_ROOT)
        for phi in ridge_angles(True):
            made.append(cone("spike", SPIKE, tube_point(y, phi), tube_normal(y, phi), long * (0.35 + 0.65 * size),
                             0.0065 * (0.4 + 0.6 * size), sides, 0.003))
    if LOW:
        made = made[::2]
    # (the head's: over each eye, on each cheek, two along the top of the snout)
    hl = P["hl"]
    for z, y_off, k in ((P["eye"][0] + 0.006, 0.03, 0.7), (P["eye"][0] + 0.045, -0.025, 0.6)):
        s = (z - P["tip"]) / hl
        y = P["eye"][1] + y_off
        at, out, up = head_frame(s, y)
        one = cone("spike", SPIKE, at, out + up * 0.6, long * k, 0.006, sides, 0.003)
        made += [one, one.mirrored("spike", lambda d: d)]
    for z in (SNOUT_BASE + 0.01, SNOUT_BASE + 0.06):
        s = (z - P["tip"]) / hl
        top = P["head_skin"].top(s)
        made.append(cone("spike", SPIKE, Vector((0.0, top, z)), Vector((0.0, 1.0, 0.25)), long * 0.6, 0.006, sides, 0.003))
    return made


def bulbs():
    """The pygmy's tubercles: big round knobs scattered over its trunk, down its tail and on its head."""
    made = []
    around, rows = (10, 6) if not (GAME or LOW) else ((5, 2) if GAME else (3, 2))
    # (a fixed scatter: so many to each ring, turned a little from ring to ring)
    for ring in range(1, P["trunk_rings"] + 1):
        y = y_of_ring(ring - 0.35)
        count = 3
        for k in range(count):
            phi = (TAU * (k + 0.5 * (ring % 2)) / count) + 0.35
            size = 0.024 if (k + ring) % 3 else 0.018
            made.append(bulb("bulb", tube_point(y, phi), tube_normal(y, phi), size, around, rows))
    for ring in range(1, P["tail_rings"] - 2, 2):
        y = y_of_ring(-ring)
        scale = P["tail_size"](y) / P["tail_size"](TAIL_ROOT)
        for phi in ((0.6, -2.0) if ring % 4 == 1 else (-0.6, 2.2)):
            made.append(bulb("bulb", tube_point(y, phi), tube_normal(y, phi), 0.022 * (0.45 + 0.55 * scale), around, rows))
    hl = P["hl"]
    for z, y_off, size in ((P["eye"][0] + 0.05, -0.02, 0.016), (P["eye"][0] + 0.08, 0.025, 0.014)):
        s = (z - P["tip"]) / hl
        at, out, up = head_frame(s, P["eye"][1] + y_off)
        one = bulb("bulb", at, out, size, around, rows)
        made += [one, one.mirrored("bulb", lambda d: d)]
    if LOW:
        made = made[::2]
    return made


# ---------------------------------------------------------------------------------------------------------------
# The fins.

def fin(name, kind, rays, base, direction, length, normal, thick, cols, rows):
    """A fin: `rays` rays fanned from the line `base(t)` (t 0 to 1), each going the way `direction(t)` for
    `length(t)`; flat, facing `normal`; `thick` at its root; `cols` strips across it and `rows` along its rays."""
    part = Part(name)
    normal = normal.normalized()
    left, right = [], []
    for i in range(cols + 1):
        t = i / cols
        b, d, long = base(t), direction(t).normalized(), length(t)
        edge = min(1.0, t / 0.06) ** 0.5 * min(1.0, (1.0 - t) / 0.06) ** 0.5
        a, c = [], []
        for j in range(rows + 1):
            r = j / rows
            taper = 1.0 - r
            th = edge * (taper ** 0.5) * thick * (0.12 + 0.88 * taper ** 1.6)
            mid = b + d * (long * r)
            data = ((r, 1.0 - t * rays), (normal.x, 1.0 - normal.y), (kind / 10.0, 0.0, normal.z * 0.5 + 0.5))
            a.append(part.add(mid + normal * (th * 0.5), *data))
            c.append(part.add(mid - normal * (th * 0.5), *data))
        left.append(a)
        right.append(c)
    for i in range(cols):
        for j in range(rows):
            for sheet in (left, right):
                a, b, c, d = sheet[i][j], sheet[i + 1][j], sheet[i + 1][j + 1], sheet[i][j + 1]
                if j == rows - 1 and i == 0:
                    part.faces += [(a, b, d), (b, c, d)]
                elif j == rows - 1 and i == cols - 1:
                    part.faces += [(a, b, c), (a, c, d)]
                else:
                    part.faces.append((a, b, c, d))
        part.faces.append((left[i][0], right[i][0], right[i + 1][0], left[i + 1][0]))
    return part


def fins():
    made = []
    y0, y1, long = P["dorsal"]

    # The dorsal fin: a fan along the middle of the back above the tail, its rays back and a little up.
    def d_base(t):
        y = lerp(y0, y1, t)
        return tube_point(y, 0.0) - Vector((0.0, 0.0, 0.006))

    def d_way(t):
        a = math.radians(lerp(-8.0, 38.0, t))
        return Vector((0.0, math.sin(a), math.cos(a)))

    def d_long(t):
        return long * (0.45 + 0.55 * math.sin(math.pi * (0.08 + 0.84 * t)) ** 0.8)
    cols = 16 if not (GAME or LOW) else (7 if GAME else 3)
    rows = 5 if not (GAME or LOW) else 2
    made.append(fin("dorsal", DORSAL, 18, d_base, d_way, d_long, Vector((1.0, 0.0, 0.0)), 0.004, cols, rows))
    SHAPE["dorsal"] = (d_base(0.0), d_base(1.0))
    # The pectoral fins: small ear-like fans on the sides of the neck, just behind the head.
    py = 0.338
    yy = [py + 0.012, py - 0.012]

    def on_neck(y):
        p = tube_point(y, math.pi * 0.5)
        return Vector((p.x - 0.004, y, p.z + 0.006))
    q0, q1 = on_neck(yy[0]), on_neck(yy[1])
    e0, e1 = Vector((0.55, 0.45, 0.7)), Vector((0.55, -0.35, 0.76))
    pl = P["pectoral"]
    pectoral = fin("pectoral", PECTORAL, 10, lambda t: q0.lerp(q1, t),
                   lambda t: (e0.lerp(e1, t)).normalized(),
                   lambda t: pl * (0.6 + 0.4 * math.sin(math.pi * (0.1 + 0.8 * t)) ** 0.7),
                   e0.cross(e1), 0.0035, 12 if not (GAME or LOW) else (4 if GAME else 2), 4 if not (GAME or LOW) else 1)
    made += [pectoral, pectoral.mirrored("pectoral_left", flip_side)]
    SHAPE["pec_root"] = (q0 + q1) * 0.5
    return made


# ---------------------------------------------------------------------------------------------------------------

def make(name, low, game=False):
    global GAME, LOW
    GAME, LOW = game, low
    parts = [trunk_and_tail(), head(), jaw()]
    ball = eye()
    parts += [ball, ball.mirrored("eye_left", lambda d: d), coronet()]
    if P["spikes"] > 0.0:
        parts += spikes()
    if P["bulbs"]:
        parts += bulbs()
    parts += fins()

    verts, faces, corners = [], [], []
    tally = {}
    counts = {}
    wrong_all = 0
    for part in parts:
        out, wrong, counted = part.done()
        was = tally.get(part.name, (0, 0))
        tally[part.name] = (was[0] + wrong, was[1] + counted)
        wrong_all += wrong
        tris = 0
        for face in out:
            first = len(verts)
            for co, uv, uv2, colour in face:
                verts.append(co)
                corners.append((uv, uv2, colour))
            faces.append(list(range(first, first + len(face))))
            tris += len(face) - 2
        counts[part.name] = counts.get(part.name, 0) + tris
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.new(name="UV2")
    mesh.color_attributes.new(name="Color", type="FLOAT_COLOR", domain="CORNER")
    uv = mesh.uv_layers["UVMap"].data
    uv2 = mesh.uv_layers["UV2"].data
    colour = mesh.color_attributes["Color"].data
    for poly in mesh.polygons:
        for corner, vi in enumerate(poly.vertices):
            d = corners[vi]
            uv[poly.loop_start + corner].uv = d[0]
            uv2[poly.loop_start + corner].uv = d[1]
            colour[poly.loop_start + corner].color = d[2]
    mesh.color_attributes.active_color = mesh.color_attributes["Color"]
    mesh.color_attributes.render_color_index = mesh.color_attributes.find("Color")
    material = bpy.data.materials.get(FAMILY) or bpy.data.materials.new(FAMILY)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.85, 0.6, 0.25, 1.0)
    material.diffuse_color = (0.85, 0.6, 0.25, 1.0)
    mesh.materials.append(material)
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-8)
    bpy.ops.object.mode_set(mode="OBJECT")
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    xs = [v.co.x for v in mesh.vertices]
    ys = [v.co.z for v in mesh.vertices]
    zs = [-v.co.y for v in mesh.vertices]
    told = ["%s %d/%d wrong" % (k, w, c) for k, (w, c) in tally.items()]
    print("BUILT %s verts=%d tris=%d reach (m): x %.4f..%.4f, up %.4f..%.4f, along %.4f..%.4f" % (
        name, len(mesh.vertices), tris, min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)))
    print("PARTS %s: %s" % (name, ", ".join("%s %d" % kv for kv in counts.items())))
    print("WINDING %s: %s: %s" % (name, "ok" if wrong_all == 0 else "INSIDE OUT", ", ".join(told)))
    return obj


def export_one(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", export_yup=True, use_selection=True,
        export_animations=False, export_vertex_color="ACTIVE", export_texcoords=True,
    )


def render(folder, made):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_cavity = True
    scene.render.resolution_x, scene.render.resolution_y = 700, 900
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 100.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    # (Blender space: the snout towards +Y, up is +Z; targets in heights)
    views = [("right", (1, 0, 0), (0, 0.06, 0), 1.1), ("left", (-1, 0, 0), (0, 0.06, 0), 1.1),
             ("front", (0, 1, 0), (0, 0, 0), 1.1), ("back", (0, -1, 0), (0, 0, 0), 1.1),
             ("top", (0, -0.001, 1), (0, 0.06, 0), 0.6), ("quarter", (0.8, 0.6, 0.2), (0, 0.04, 0), 1.1),
             ("head", (1, 0.3, 0.25), (0, 0.12, 0.4), 0.45), ("head_front", (0.4, 1.0, 0.2), (0, 0.2, 0.4), 0.3)]
    for tag, obj in made:
        for other in made:
            other[1].hide_render = other[1] is not obj
        for view, direction, target, frame in views:
            offset = Vector(direction).normalized() * 10.0
            camera.data.ortho_scale = frame * LENGTH
            camera.location = Vector(target) * LENGTH + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if view != "top" else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s_%s.png" % (tag, view))
            bpy.ops.render.render(write_still=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    for kind in WANTED:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version = 0
        use(kind)
        name = "%s_%s" % (FAMILY, kind)
        full = make(name, False)
        low = make(name + "_lo", True)
        game = make(name + "_game", False, True)
        e, o, pr = SHAPE["eye_skin"], SHAPE["eye_out"], SHAPE["pec_root"]
        d0, d1 = SHAPE["dorsal"]
        hs, hy = P["hinge"]
        print("SHAPE %s: \"hinge\": Vector2(%.4f, %.4f), \"eye_skin\": Vector3(%.4f, %.4f, %.4f), "
              "\"eye_out\": Vector3(%.4f, %.4f, %.4f), \"pec_root\": Vector3(%.4f, %.4f, %.4f), "
              "\"dorsal_root\": Vector4(%.4f, %.4f, %.4f, %.4f), \"tail_root\": %.4f" % (
                  kind, P["tip"] + hs * P["hl"], hy, e.x, e.y, e.z, o.x, o.y, o.z, pr.x, pr.y, pr.z,
                  d0.y, d0.z, d1.y, d1.z, TAIL_ROOT))
        print("SHAPE %s: snout tip z %.4f, trunk %.4f deep and %.4f wide (m); tail %.4f thick at its root" % (
            kind, P["tip"], max(P["front"](y / 100.0) + P["back"](y / 100.0) for y in range(-6, 33)) * LENGTH,
            2.0 * max(P["side"](y / 100.0) for y in range(-6, 33)) * LENGTH, 2.0 * P["tail_size"](TAIL_ROOT) * LENGTH))
        if "--game-only" not in ARGS:
            export_one(full, os.path.join(OUT, name + ".glb"))
            export_one(low, os.path.join(OUT, name + "_lo.glb"))
        export_one(game, os.path.join(OUT, name + "_game.glb"))
        low.location.x = LENGTH * 0.6
        game.location.x = -LENGTH * 0.6
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, name + ".blend"))
        low.location.x = 0.0
        game.location.x = 0.0
        if PREVIEW:
            folder = os.path.join(PREVIEW, kind)
            os.makedirs(folder, exist_ok=True)
            render(folder, [("full", full), ("game", game)])


if __name__ == "__main__":
    main()
