"""Builds the pufferfish (creatures/pufferfish) and exports it for Godot.

Run from the game's root:
    blender --background --factory-startup --python creatures/pufferfish/tools/build_pufferfish.py
    blender --background --factory-startup --python creatures/pufferfish/tools/build_pufferfish.py -- <preview folder>

It writes creatures/pufferfish/models/pufferfish.glb (the full model), pufferfish_game.glb (the game model: the
same outline in a sixth of the triangles) and pufferfish_lo.glb (far off, phones, many at once), and the editable
creatures/pufferfish/tools/pufferfish.blend holding all three (this folder has a .gdignore). Each model is one still
mesh with one surface: the shader (pufferfish.gdshader) blows it up into a ball (`puff`), stands its spines up,
buzzes its fins, works its jaw and draws every marking. It prints a WINDING line for each model (nothing is inside
out) and a SHAPE line: the places on the model the shader needs (copied into pufferfish.gdshader by hand).

A spotted puffer, after the bullseye puffer (Sphoeroides annulatus) of the Californian and Mexican coast, built
0.3 m long from the front of its beak to its tail tip, nose towards -Z, belly down, its origin on its middle line
half way along its length:

- THE BODY: blunt and boxy, broad-headed, flat on top, narrowing to a long wrist of a tail.
- THE MOUTH: small, at the front. The upper lip is the front of the body's skin; the LOWER JAW is a part of its
  own (the shader swings it down about its hinge). THE BEAK: four teeth fused into two plates, an upper and a lower,
  each a crescent with a groove down its middle (so two teeth either side).
- THE EYES: big and round, set high on the head.
- THE FINS: thin closed solids: one small rounded DORSAL fin and one ANAL fin far back, a small rounded TAIL and a
  pair of small rounded PECTORAL fins behind the head. No pelvic fins (puffers have none).
- THE SPINES: small cones over the back, sides and belly, lying flat along the skin pointing back; the shader
  stands them straight out as it blows the body up.

What a point is, for the shader: vertex colour red the part, as a tenth (0 body, 0.1 lower jaw, 0.2 eye, 0.3 upper
beak, 0.4 lower beak, 0.5 spine, 0.6 dorsal, 0.7 anal, 0.8 tail, 0.9 pectoral). On the body and jaw: UV.x how far
along the fish (0 snout to 1 tail tip), UV.y how high on it (0 belly line to 1 back line); blue how much it is
inside the mouth. On an eye: UV where a point is on its round face seen straight on (its middle at 0.5, 0.5). On a
fin: UV.x along its rays (0 root to 1 edge), UV.y across it counted in rays (0 its leading edge); UV2 and blue the
way its flat side faces (x, y, and z as z / 2 + 0.5). On a spine: UV.x along it (0 root, 1 tip); UV2 its root's
x and y and green its root's s (how far along, 0..1), all in body lengths; UV.y and blue the way it lies (x, and
y as y / 2 + 0.5; its z is the rest, always towards the tail). (The glTF writer flips V: what is written here is
1 - v, so that Godot reads v.)

Everything here is worked out in body lengths in Godot space (Y up, nose towards -Z) and written out in metres.
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

# Kept in step with pufferfish.gd and pufferfish.gdshader.
NAME = "pufferfish"
LENGTH = 0.3
TAU = math.tau
BODY, JAW, EYE, BEAK_UP, BEAK_LO, SPINE, DORSAL, ANAL, TAIL, PECTORAL = range(10)
LIP = -1

# The fish's outline seen from the side, (s, y) from the snout's tip (s 0) to where the body ends inside the tail
# fin (s 0.86); its half width. Body lengths.
TOP = [(0.0, 0.012), (0.015, 0.032), (0.04, 0.064), (0.08, 0.1), (0.13, 0.13), (0.19, 0.151), (0.27, 0.164),
       (0.36, 0.166), (0.45, 0.154), (0.54, 0.127), (0.62, 0.094), (0.69, 0.066), (0.75, 0.05), (0.81, 0.041),
       (0.86, 0.033)]
BOT = [(0.0, -0.03), (0.015, -0.052), (0.04, -0.082), (0.08, -0.11), (0.14, -0.134), (0.22, -0.153), (0.31, -0.162),
       (0.40, -0.158), (0.49, -0.14), (0.57, -0.108), (0.64, -0.077), (0.71, -0.055), (0.78, -0.043), (0.86, -0.033)]
HW = [(0.0, 0.0), (0.006, 0.022), (0.02, 0.05), (0.05, 0.086), (0.1, 0.118), (0.17, 0.137), (0.26, 0.145),
      (0.36, 0.141), (0.46, 0.123), (0.56, 0.094), (0.65, 0.064), (0.73, 0.043), (0.8, 0.029), (0.84, 0.016),
      (0.86, 0.0)]
BODY_END = 0.86
# The mouth: how high its line is at the snout's tip, and where the lower jaw hinges (s, y).
MOUTH_Y = -0.012
HINGE = (0.04, -0.028)
# The eye: where (s, y), the eyeball's radius, how far it stands out of the head, how much of the dome shows.
EYE_SPEC = (0.17, 0.104, 0.04, 0.017, 0.75)
# The dorsal and anal fins: from s0 to s1 along the back (the belly), so many rays; `len` (t, length) and `ang`
# (t, degrees up from straight back) across the fin, t 0 its leading edge to 1 its trailing edge.
DORSAL_SPEC = {"s0": 0.6, "s1": 0.675, "rays": 10,
               "len": [(0.0, 0.06), (0.25, 0.105), (0.6, 0.105), (1.0, 0.055)],
               "ang": [(0.0, 64.0), (0.5, 46.0), (1.0, 22.0)]}
ANAL_SPEC = {"s0": 0.625, "s1": 0.7, "rays": 9,
             "len": [(0.0, 0.055), (0.25, 0.095), (0.6, 0.095), (1.0, 0.05)],
             "ang": [(0.0, 60.0), (0.5, 42.0), (1.0, 20.0)]}
# The tail: where its root is (s), its spread (degrees) and how rounded its end is; half the height of its root.
TAIL_SPEC = (0.83, 24.0, 0.09)
PED = 0.03
# The pectoral fins: how far along, how high the top of the root, its length.
PEC_SPEC = (0.3, 0.035, 0.085)
# The ball it blows up into (`puff` 1): its middle (y, s) and radius, body lengths. Copied into the shader.
PUFF_CENTRE = (0.0, 0.38)
PUFF_RADIUS = 0.35
# The spines: rows from s0 to s1, so many down each side of each row (from the back line to the belly line), how
# long, how thick at the root.
SPINE_ROWS = (0.12, 0.6, 8)
SPINE_PER_SIDE = 6
SPINE_LONG = 0.075
SPINE_THICK = 0.0075

# The game model's numbers: rings along the body, points down each side of a ring; places across the tail.
GAME_BODY_RINGS = 20
GAME_HALF = 8
GAME_TAIL = 7

GAME = False


def to_b(p):
    return Vector((p.x, -p.z, p.y))


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def spread(lines_at, a, b, n, forced=(), even=0.35):
    """n + 1 places from a to b (a and b among them) for the game model, closer together where the lines
    `lines_at(t)` gives (a list of (x, y) points, one on each line) bend, and `even` of the whole spread evenly.
    Each place in `forced` replaces the nearest place."""
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
    fixed = {0, len(out) - 1}
    for f in forced:
        if not a < f < b:
            continue
        free = [j for j in range(len(out)) if j not in fixed]
        if free:
            j = min(free, key=lambda j: abs(out[j] - f))
            out[j] = f
            fixed.add(j)
        else:
            out.append(f)
        out.sort()
        fixed = {j for j, x in enumerate(out) if x in forced or j in (0, len(out) - 1)}
    return sorted(set(out))


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


class Section:
    """A lofted skin: at each place along the fish (s) its top line, bottom line, half width, how far up from the
    bottom it is widest (0..1), and how boxy its upper and lower halves are (2 an ellipse, more is squarer)."""

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
        """half + 1 points down its right side from the top line to the bottom line: (x, y, how far round)."""
        top, bot, hw, ycf, nt, nb = self.at(s)
        yc = bot + ycf * (top - bot)
        dense = []
        steps = 200
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
        whole = acc[-1]
        out = []
        if GAME:
            # (the game model: the points closer together where the ring bends, at the corners of the box)
            worth = [0.0]
            for i in range(steps):
                turn = 0.0
                if 0 < i:
                    ax, ay = dense[i][0] - dense[i - 1][0], dense[i][1] - dense[i - 1][1]
                    bx, by = dense[i + 1][0] - dense[i][0], dense[i + 1][1] - dense[i][1]
                    la, lb = math.hypot(ax, ay), math.hypot(bx, by)
                    if la > 1e-12 and lb > 1e-12:
                        turn = math.acos(max(-1.0, min(1.0, (ax * bx + ay * by) / (la * lb))))
                worth.append(math.sqrt(turn * (acc[i + 1] - acc[i])))
            bend = sum(worth)
            total = [0.0]
            for i in range(steps):
                total.append(total[-1] + worth[i + 1] + 0.9 * bend * (acc[i + 1] - acc[i]) / max(whole, 1e-12))
            for j in range(half + 1):
                want = total[-1] * j / half
                i = min(bisect.bisect_right(total, want) - 1, steps - 1)
                span = total[i + 1] - total[i]
                t = (want - total[i]) / span if span > 1e-12 else 0.0
                out.append((lerp(dense[i][0], dense[i + 1][0], t), lerp(dense[i][1], dense[i + 1][1], t),
                            lerp(acc[i], acc[i + 1], t)))
            return out, whole
        for j in range(half + 1):
            want = whole * j / half
            i = min(bisect.bisect_right(acc, want) - 1, steps - 1)
            span = acc[i + 1] - acc[i]
            t = (want - acc[i]) / span if span > 1e-12 else 0.0
            out.append((lerp(dense[i][0], dense[i + 1][0], t), lerp(dense[i][1], dense[i + 1][1], t), want))
        return out, whole


SIL_TOP = curve(TOP)
SIL_BOT = curve(BOT)
SIL_HW = curve(HW)
HINGE_S, HINGE_Y = HINGE


BODY_SKIN = Section(
    0.0, BODY_END, SIL_TOP, SIL_BOT, SIL_HW,
    lambda s: lerp(0.35, 0.47, smooth(0.0, 0.1, s)),
    lambda s: lerp(2.0, 2.7, smooth(0.0, 0.12, s)) - 0.5 * smooth(0.65, 0.8, s),
    lambda s: lerp(2.0, 2.4, smooth(0.0, 0.1, s)) - 0.3 * smooth(0.65, 0.8, s))
# The mouth: small pieces at the front of the blunt face, their backs buried in it. The UPPER LIP (a part of
# the body that lifts a little as the mouth opens) and the LOWER JAW (swung down about its hinge), each with the
# beak's plate along its front edge; they meet on the line of the mouth. The face behind them is dark (the
# shader draws it), so that it shows as the inside of the mouth when they part.
LIP_FIRST, LIP_LAST = -0.0055, 0.05
JAW_FIRST, JAW_LAST = -0.0055, 0.062
MOUTH_HW = curve([(-0.0055, 0.0), (-0.0035, 0.014), (0.0, 0.021), (0.008, 0.028), (0.02, 0.032), (0.07, 0.034)])
LIP_SKIN = Section(
    LIP_FIRST, LIP_LAST,
    curve([(-0.0055, MOUTH_Y + 0.0075), (0.0, MOUTH_Y + 0.0145), (0.01, MOUTH_Y + 0.0175), (0.05, MOUTH_Y + 0.016)]),
    lambda s: MOUTH_Y + 0.0004, lambda s: MOUTH_HW(s) * (1.0 - smooth(LIP_LAST - 0.025, LIP_LAST, s)) ** 0.5, lambda s: 0.16, lambda s: 2.2, lambda s: 5.0)
JAW_SKIN = Section(
    JAW_FIRST, JAW_LAST, lambda s: MOUTH_Y - 0.0004,
    curve([(-0.005, MOUTH_Y - 0.009), (0.0, MOUTH_Y - 0.016), (0.012, MOUTH_Y - 0.022), (0.03, MOUTH_Y - 0.025),
           (0.062, MOUTH_Y - 0.02)]),
    lambda s: 0.92 * MOUTH_HW(s) * (1.0 - smooth(JAW_LAST - 0.03, JAW_LAST, s)) ** 0.5, lambda s: 0.84, lambda s: 5.0, lambda s: 2.2)
EYE_SKIN = Vector()
EYE_OUT = Vector()
PEC_ROOT = Vector()
FIN_LINES = {}


def body_x(s, y):
    return BODY_SKIN.x_at(s, y)


def body_frame(s, y):
    """A place on the body's right side: the point, the way out of the skin there, and the way up along it."""
    e = 0.002
    x = body_x(s, y)
    dy = (body_x(s, y + e) - body_x(s, y - e)) / (2 * e)
    ds = (body_x(s + e, y) - body_x(s - e, y)) / (2 * e)
    return Vector((x, y, s - 0.5)), Vector((1.0, -dy, -ds)).normalized(), Vector((dy, 1.0, 0.0)).normalized()


def skin_point(s, h):
    """A point on the body's right side (s along, h 0 belly line to 1 back line) and the way out of the skin."""
    top, bot = BODY_SKIN.top(s), BODY_SKIN.bot(s)
    y = lerp(bot, top, h)
    e = 0.0015
    p = Vector((body_x(s, y), y, s - 0.5))
    # (the normal from the skin's two ways round, which works on the back and belly lines too)
    ya, yb = lerp(bot, top, min(h + 0.02, 1.0)), lerp(bot, top, max(h - 0.02, 0.0))
    pa = Vector((body_x(s, ya), ya, s - 0.5))
    pb = Vector((body_x(s, yb), yb, s - 0.5))
    ytop, ybot = lerp(BODY_SKIN.bot(s + e), BODY_SKIN.top(s + e), h), lerp(BODY_SKIN.bot(s - e), BODY_SKIN.top(s - e), h)
    pc = Vector((body_x(s + e, ytop), ytop, s + e - 0.5))
    pd = Vector((body_x(s - e, ybot), ybot, s - e - 0.5))
    n = (pc - pd).cross(pa - pb).normalized()
    if n.x < 0.0 or (abs(n.x) < 1e-6 and n.dot(Vector((0.0, p.y, 0.0))) < 0.0):
        n = -n
    return p, n


class Part:
    """One closed piece of the fish: points (body lengths), what each is for the shader, and faces. `done` welds
    it, turns every face outward and checks that."""

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

    def mirrored(self, name, flip):
        other = Part(name)
        for p, d in zip(self.verts, self.data):
            other.add((-p.x, p.y, p.z), *flip(d))
        other.faces = list(self.faces)
        return other

    @staticmethod
    def inside_out(bm):
        """How many of a closed solid's faces face inwards, and how many were looked at: a line out of a face,
        the way the face faces, comes out through the solid's skin an even number of times (none, for most)."""
        cut = bm.copy()
        bmesh.ops.triangulate(cut, faces=cut.faces)
        cut.normal_update()
        tree = BVHTree.FromBMesh(cut)
        wrong = 0
        counted = 0
        for f in cut.faces:
            if f.calc_area() > 1e-11:
                counted += 1
                at = f.calc_center_median() + f.normal * 2e-6
                hits = 0
                while hits < 40:
                    hit = tree.ray_cast(at, f.normal)
                    if hit[0] is None:
                        break
                    hits += 1
                    at = hit[0] + f.normal * 2e-6
                if hits % 2:
                    wrong += 1
        cut.free()
        return wrong, counted

    def done(self):
        """Returns (faces as lists of (point in Blender metres, uv, uv2, colour), faces wound wrongly, faces)."""
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
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
        # (a four-cornered face with three corners on the middle plane: cut it from its fourth corner)
        for f in list(bm.faces):
            if len(f.verts) == 4:
                off = [loop for loop in f.loops if abs(loop.vert.co.x) > 1e-8]
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


def skin(part, section, places, half, kind):
    """Lofts a Section into a Part. `kind` is BODY or JAW."""
    rings = []
    for s in places:
        side, whole = section.outline(s, half)
        top, bot = section.top(s), section.bot(s)
        ring = []
        for j in list(range(half + 1)) + list(range(half, 0, -1)):
            x, y, arc = side[j]
            sign = 1.0 if len(ring) <= half else -1.0
            h = (y - bot) / max(top - bot, 1e-9)
            yc = bot + section.at(s)[3] * (top - bot)
            if kind == BODY:
                ring.append(part.add((sign * x, y, s - 0.5), (s, 1.0 - h),
                                     (sign * arc * LENGTH, 1.0 - whole * LENGTH), (0.0, 0.0, 0.0)))
            elif kind == LIP:
                # (green 1: lifts with the mouth; blue: its flat underside, the roof of the mouth)
                inside = smooth(0.5, 0.9, (yc - y) / max(yc - bot, 1e-9)) if y < yc else 0.0
                ring.append(part.add((sign * x, y, s - 0.5), (s, 1.0 - h),
                                     (sign * x * LENGTH, 1.0), (0.0, 1.0, inside)))
            else:
                # (blue: its flat top, the floor of the mouth)
                inside = smooth(0.5, 0.9, (y - yc) / max(top - yc, 1e-9)) if y > yc else 0.0
                ring.append(part.add((sign * x, y, s - 0.5), (s, 1.0 - h),
                                     (sign * x * LENGTH, 1.0), (JAW / 10.0, 0.0, inside)))
        rings.append(ring)
    part.loft(rings)


def body_places(low):
    es, ball = EYE_SPEC[0], EYE_SPEC[2]
    if GAME:
        return spread(lambda s: [(s, BODY_SKIN.top(s)), (s, BODY_SKIN.bot(s)), (s, SIL_HW(s))],
                      0.0, BODY_END, GAME_BODY_RINGS,
                      (0.012, es - ball * 0.6, es + ball * 0.6))
    head = 6 if low else 30
    rest = 9 if low else 50
    behind = 0.3
    places = [behind * (i / head) ** 1.35 for i in range(head)]
    places += [lerp(behind, BODY_END, i / rest) for i in range(rest + 1)]
    return places


def eye(low):
    """The right eye: a dome set in the side of the head."""
    global EYE_SKIN, EYE_OUT
    part = Part("eye")
    at, out, up = body_frame(EYE_SPEC[0], EYE_SPEC[1])
    EYE_SKIN = at.copy()
    EYE_OUT = out.copy()
    along = up.cross(out).normalized()
    ball, stands, shown = EYE_SPEC[2:]
    seen = math.sqrt(1.0 - (1.0 - stands / ball) ** 2)
    reach = math.asin(min(seen / shown, 0.999))
    centre = at - out * (ball - stands)
    rows = 2 if (low or GAME) else 6
    around = 24 if GAME else (8 if low else 24)
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
    back = centre + out * (ball * math.cos(reach) - 0.004)
    rings.append([part.add(back, (0.5 + 0.5 * math.cos(TAU * k / around), 0.5 - 0.5 * math.sin(TAU * k / around)),
                           (0.0, 1.0), (EYE / 10.0, 0.0, 0.0)) for k in range(around)])
    part.loft(rings)
    hub = part.add(back - out * 0.001, (0.5, 0.5), (0.0, 1.0), (EYE / 10.0, 0.0, 0.0))
    last = rings[-1]
    for k in range(around):
        part.faces.append((last[(k + 1) % around], last[k], hub))
    return part


def beak(upper, low):
    """A beak plate: two fused teeth either side of a groove down its middle, a crescent round the front of the
    mouth, its cutting edge on the line of the mouth (the upper one hanging from the lip, the lower one standing
    on the jaw)."""
    part = Part("beak_upper" if upper else "beak_lower")
    kind = BEAK_UP if upper else BEAK_LO
    stations = 14 if not (low or GAME) else (8 if GAME else 4)
    reach = math.radians(82.0)
    half_w, deep, front = 0.025, 0.026, -0.0075
    rings = []
    for i in range(stations + 1):
        a = -reach + 2.0 * reach * i / stations
        # (along the crescent: its front the middle; the plate stands from its cutting edge to its root)
        x, s = half_w * math.sin(a), front + deep * (1.0 - math.cos(a))
        nx, ns = math.sin(a) * deep, -math.cos(a) * half_w
        n = Vector((nx, 0.0, ns)).normalized()
        groove = 1.0 - 0.35 * math.exp(-(x / 0.004) ** 2)
        edge = MOUTH_Y + (0.0006 if not upper else -0.0006)
        tall = 0.011 * groove * (0.75 + 0.25 * math.cos(a))
        root_y = edge + (tall if upper else -tall)
        thick = 0.0055
        corners = [(0.0, edge), (thick, edge), (thick, root_y), (0.0, root_y)]
        ring = []
        for k, (inward, y) in enumerate(corners):
            p = Vector((x, y, s - 0.5)) - n * inward
            ring.append(part.add(p, (i / stations, 1.0 - k / 3.0), (x * LENGTH, 1.0), (kind / 10.0, 0.0, 0.0)))
        rings.append(ring)
    part.loft(rings)
    # (closed at both ends of the crescent)
    part.faces.append(tuple(rings[0]))
    part.faces.append(tuple(reversed(rings[-1])))
    return part


def fin(name, kind, rays, base, direction, length, normal, thick, cols, rows, ts=None):
    """A fin: `rays` rays fanned from the line `base(t)` (t 0 its leading edge to 1 its trailing edge), each
    going the way `direction(t)` for `length(t)`; flat, facing `normal`; `thick` at its root; `cols` strips
    across it and `rows` along its rays (or strips between the places `ts`)."""
    part = Part(name)
    normal = normal.normalized()
    left, right = [], []
    if ts is not None:
        cols = len(ts) - 1
    for i in range(cols + 1):
        t = ts[i] if ts is not None else i / cols
        b, d, long = base(t), direction(t).normalized(), length(t)
        ridge = 0.5 + 0.5 * math.cos(TAU * (t * rays - 0.5)) if (cols >= rays * 2) else 0.0
        edge = min(1.0, t / 0.06) ** 0.5 * min(1.0, (1.0 - t) / 0.1) ** 0.5
        a, c = [], []
        for j in range(rows + 1):
            r = j / rows
            taper = 1.0 - r
            th = edge * (taper ** 0.5) * (thick * (0.1 + 0.9 * taper ** 1.6) + 0.0008 * ridge * smooth(0.0, 0.14, r))
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


def turn(d0, d1, t):
    d0, d1 = d0.normalized(), d1.normalized()
    angle = d0.angle(d1)
    return (d0 * math.sin((1.0 - t) * angle) + d1 * math.sin(t * angle)) / math.sin(angle)


def edge_places(base, direction, length, a, b, n, forced=()):
    def tip(t):
        p = base(t) + direction(t).normalized() * length(t)
        return [(p.z, p.y)]
    return spread(tip, a, b, n, forced)


def middle_fin(name, kind, spec, up, low):
    """The dorsal fin (up 1) or the anal fin (up -1): small, rounded, soft-rayed."""
    s0, s1, rays = spec["s0"], spec["s1"], spec["rays"]
    long = curve(spec["len"])
    angle = curve(spec["ang"])
    line = BODY_SKIN.top if up > 0 else BODY_SKIN.bot

    def base(t):
        return Vector((0.0, line(lerp(s0, s1, t)) - up * 0.012, lerp(s0, s1, t) - 0.5))

    def direction(t):
        return Vector((0.0, up * math.sin(math.radians(angle(t))), math.cos(math.radians(angle(t)))))
    # (where its root runs, for the shader, which carries the fin along with the skin as it puffs)
    FIN_LINES[name] = (base(0.0), base(1.0), rays)
    if GAME:
        ts = edge_places(base, direction, long, 0.0, 1.0, 6)
        return fin(name, kind, rays, base, direction, long, Vector((1.0, 0.0, 0.0)), 0.008, 0, 2, ts)
    return fin(name, kind, rays, base, direction, long, Vector((1.0, 0.0, 0.0)), 0.008,
               4 if low else rays * 2, 2 if low else 6)


def fins(low):
    global PEC_ROOT
    made = [middle_fin("dorsal", DORSAL, DORSAL_SPEC, 1.0, low), middle_fin("anal", ANAL, ANAL_SPEC, -1.0, low)]
    t_s, t_spread, t_round = TAIL_SPEC

    def tail_base(t):
        return Vector((0.0, lerp(PED, -PED, t), t_s + 0.01 - 0.016 * (2.0 * t - 1.0) ** 2 - 0.5))

    def tail_way(t):
        a = math.radians(t_spread * (1.0 - 2.0 * t))
        return Vector((0.0, math.sin(a), math.cos(a)))

    def tail_long(t):
        a = abs(2.0 * t - 1.0)
        reach = (0.5 - tail_base(t).z) / math.cos(math.radians(t_spread * a))
        return reach * (1.0 - t_round * a * a)
    if GAME:
        made.append(fin("tail", TAIL, 13, tail_base, tail_way, tail_long, Vector((1.0, 0.0, 0.0)), 0.012, 0, 3,
                        edge_places(tail_base, tail_way, tail_long, 0.0, 1.0, GAME_TAIL)))
    else:
        made.append(fin("tail", TAIL, 13, tail_base, tail_way, tail_long, Vector((1.0, 0.0, 0.0)), 0.012,
                        5 if low else 26, 2 if low else 6))
    # The pectoral fins: small rounded fans just behind the head, held out from the side.
    pc_s, pc_y, pc_long = PEC_SPEC

    def on_body(s, y, sunk=0.004):
        return Vector((max(body_x(s, y) - sunk, 0.0), y, s - 0.5))
    q0, q1 = on_body(pc_s, pc_y), on_body(pc_s + 0.006, pc_y - 0.06)
    e0, e1 = Vector((0.5, 0.42, 0.75)), Vector((0.5, -0.5, 0.7))
    pectoral = fin(
        "pectoral", PECTORAL, 12, lambda t: q0.lerp(q1, t), lambda t: turn(e0, e1, t),
        lambda t: pc_long * (0.55 + 0.45 * math.sin(math.pi * (0.1 + 0.8 * t)) ** 0.7),
        e0.cross(e1), 0.006, 5 if GAME else (3 if low else 24), 2 if (low or GAME) else 5)
    made += [pectoral, pectoral.mirrored("pectoral_left", flip_side)]
    PEC_ROOT = (q0 + q1) * 0.5
    return made


def spine_places():
    """Where each spine of the right side is rooted: (s, h), in rows, every other row staggered; none on the eye,
    the pectoral fin's root or the gill slit."""
    s0, s1, rows = SPINE_ROWS
    out = []
    for i in range(rows):
        s = lerp(s0, s1, i / (rows - 1))
        for k in range(SPINE_PER_SIDE):
            h = (k + (0.75 if i % 2 else 0.25)) / SPINE_PER_SIDE
            h = lerp(0.04, 0.96, h)
            top, bot = BODY_SKIN.top(s), BODY_SKIN.bot(s)
            y = lerp(bot, top, h)
            if math.hypot(s - EYE_SPEC[0], (y - EYE_SPEC[1]) * 1.1) < EYE_SPEC[2] * 1.7:
                h = min(h, (EYE_SPEC[1] - EYE_SPEC[2] * 1.6 - bot) / (top - bot))
            if abs(s - PEC_SPEC[0]) < 0.045 and PEC_SPEC[1] - 0.075 < y < PEC_SPEC[1] + 0.02:
                y = PEC_SPEC[1] + 0.035 if h > 0.5 else PEC_SPEC[1] - 0.09
                h = (y - bot) / (top - bot)
            out.append((s, h))
    return out


def spines(low):
    """The spines of both sides: small cones lying flat along the skin, pointing back, their tips just off it."""
    made = []
    sides = 3 if (low or GAME) else 6
    places = spine_places()
    if low:
        places = places[::2]
    for s, h in places:
        right = Part("spines")
        made.append(right)
        root, n0 = skin_point(s, h)
        long = SPINE_LONG * (0.7 + 0.3 * math.sin(math.pi * min(max((s - 0.08) / 0.56, 0.0), 1.0)))
        # (its tip on the skin `long` behind its root, a little off it)
        s_tip = s + long * 0.9
        tip_at, tip_n = skin_point(s_tip, h)
        tip = tip_at + tip_n * 0.0045
        root = root - n0 * 0.002
        way = (tip - root).normalized()
        if way.z < 0.1:
            raise RuntimeError("a spine points forward at s %.3f h %.3f" % (s, h))
        side_a = n0.cross(way).normalized()
        side_b = way.cross(side_a).normalized()
        thick = SPINE_THICK * (0.8 + 0.2 * long / SPINE_LONG)
        # (its base a little behind its root along its own line: standing, that is sunk in the skin)
        base = root - way * 0.006
        length = (tip - base).length
        stations = [0.0, 0.45, 1.0] if sides > 3 else [0.0, 1.0]
        rings = []
        for t in stations:
            ring = []
            radius = thick * (1.0 - t) ** 1.1
            for k in range(sides if t < 1.0 else 1):
                q = TAU * (k + 0.5) / sides
                # (squashed against the skin: wider than it is tall)
                p = base + way * (length * t) + side_a * (radius * 1.2 * math.cos(q)) + side_b * (radius * 0.75 * math.sin(q))
                data = ((t, 1.0 - way.x), (root.x, 1.0 - root.y), (SPINE / 10.0, root.z + 0.5, way.y * 0.5 + 0.5))
                ring.append(right.add(p, *data))
            rings.append(ring)
        for a, b in zip(rings, rings[1:]):
            if len(b) == 1:
                for j in range(sides):
                    right.faces.append((a[j], a[(j + 1) % sides], b[0]))
            else:
                for j in range(sides):
                    right.faces.append((a[j], a[(j + 1) % sides], b[(j + 1) % sides], b[j]))
        right.faces.append(tuple(reversed(rings[0])))

    def flip(d):
        uv, uv2, c = d
        return (uv[0], 2.0 - uv[1]), (-uv2[0], uv2[1]), c
    return made + [one.mirrored("spines_left", flip) for one in made]


def make(name, low, game=False):
    global GAME
    GAME = game
    parts = []
    body = Part("body")
    skin(body, BODY_SKIN, body_places(low), GAME_HALF if game else (5 if low else 16), BODY)
    parts.append(body)
    jaw = Part("jaw")
    lip = Part("lip")
    for section, part, kind in ((JAW_SKIN, jaw, JAW), (LIP_SKIN, lip, LIP)):
        first, last = section.first, section.last
        if low:
            places = [first, first + 0.003, 0.012, last]
        elif game:
            places = [first, first + 0.0015, first + 0.004, 0.006, 0.016, 0.03, last]
        else:
            places = [first] + [lerp(first, last, (i / 14) ** 1.6) for i in range(1, 15)]
        skin(part, section, places, 3 if low else (4 if game else 9), kind)
    parts.append(lip)
    parts.append(jaw)
    ball = eye(low)
    parts += [ball, ball.mirrored("eye_left", lambda d: d)]
    parts += [beak(True, low), beak(False, low)]
    parts += spines(low)
    parts += fins(low)

    verts, faces, corners = [], [], []
    told = []
    wrong_all = 0
    counts = {}
    tally = {}
    for part in parts:
        out, wrong, counted = part.done()
        was = tally.get(part.name, (0, 0))
        tally[part.name] = (was[0] + wrong, was[1] + counted)
        wrong_all += wrong
        tris = 0
        for face in out:
            first_v = len(verts)
            for co, uv, uv2, colour in face:
                verts.append(co)
                corners.append((uv, uv2, colour))
            faces.append(list(range(first_v, first_v + len(face))))
            tris += len(face) - 2
        counts[part.name] = counts.get(part.name, 0) + tris
    told = ["%s %d/%d wrong" % (k, w, c) for k, (w, c) in tally.items()]
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
    material = bpy.data.materials.get(NAME) or bpy.data.materials.new(NAME)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.7, 0.6, 0.4, 1.0)
    material.diffuse_color = (0.7, 0.6, 0.4, 1.0)
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
    bpy.ops.mesh.remove_doubles(threshold=1e-7)
    bpy.ops.object.mode_set(mode="OBJECT")
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    xs = [v.co.x for v in mesh.vertices]
    ys = [v.co.z for v in mesh.vertices]
    zs = [-v.co.y for v in mesh.vertices]
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
    scene.render.resolution_x, scene.render.resolution_y = 900, 700
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 100.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    # (Blender space: the nose is towards +Y, up is +Z; frames and targets in body lengths)
    views = [("right", (1, 0, 0), (0, 0, 0.0), 1.15), ("left", (-1, 0, 0), (0, 0, 0.0), 1.15),
             ("top", (0, -0.001, 1), (0, 0, 0), 1.15), ("under", (0, 0.001, -1), (0, 0, 0), 1.15),
             ("front", (0, 1, 0), (0, 0, 0.0), 0.6), ("back", (0, -1, 0), (0, 0, 0.0), 0.6),
             ("quarter", (0.7, 0.6, 0.35), (0, 0, 0.0), 1.1),
             ("head", (0.8, 0.6, 0.1), (0, 0.4, 0), 0.4), ("mouth", (0.15, 1.0, -0.15), (0, 0.48, -0.01), 0.18)]
    for tag, obj in made:
        for other in made:
            other[1].hide_render = other[1] is not obj
        for view, direction, target, frame in views:
            offset = Vector(direction).normalized() * 10.0
            camera.data.ortho_scale = frame * LENGTH
            camera.location = Vector(target) * LENGTH + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "X" if view in ("top", "under") else "Y").to_euler()
            scene.render.filepath = os.path.join(folder, "%s_%s.png" % (tag, view))
            bpy.ops.render.render(write_still=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    full = make(NAME, False)
    low = make(NAME + "_lo", True)
    game = make(NAME + "_game", False, True)
    d0, d1, dr = FIN_LINES["dorsal"]
    a0, a1, ar = FIN_LINES["anal"]
    depth = max(SIL_TOP(i / 200.0) - SIL_BOT(i / 200.0) for i in range(20, 160))
    width = 2.0 * max(SIL_HW(i / 200.0) for i in range(20, 160))
    print("SHAPE hinge_s=%.4f hinge_y=%.4f mouth_y=%.4f depth=%.4f m width=%.4f m" % (
        HINGE_S, HINGE_Y, MOUTH_Y, depth * LENGTH, width * LENGTH))
    print("SHAPE eye_out=(%.4f, %.4f, %.4f)" % tuple(EYE_OUT))
    print("SHAPE eye_skin=(%.4f, %.4f, %.4f) pec_root=(%.4f, %.4f, %.4f)" % (
        EYE_SKIN.x, EYE_SKIN.y, EYE_SKIN.z + 0.5, PEC_ROOT.x, PEC_ROOT.y, PEC_ROOT.z + 0.5))
    print("SHAPE dorsal_root=(%.4f, %.4f)..(%.4f, %.4f) rays %d  anal_root=(%.4f, %.4f)..(%.4f, %.4f) rays %d" % (
        d0.y, d0.z + 0.5, d1.y, d1.z + 0.5, dr, a0.y, a0.z + 0.5, a1.y, a1.z + 0.5, ar))
    print("SHAPE puff centre (y, s)=(%.4f, %.4f) radius %.4f: puffed %.4f m across, %.4f m with its spines" % (
        PUFF_CENTRE[0], PUFF_CENTRE[1], PUFF_RADIUS, 2.0 * PUFF_RADIUS * LENGTH,
        2.0 * (PUFF_RADIUS + SPINE_LONG * 0.95) * LENGTH))
    if "--game-only" not in ARGS:
        export_one(full, os.path.join(OUT, NAME + ".glb"))
        export_one(low, os.path.join(OUT, NAME + "_lo.glb"))
    export_one(game, os.path.join(OUT, NAME + "_game.glb"))
    low.location.x = LENGTH * 0.5
    game.location.x = -LENGTH * 0.5
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, NAME + ".blend"))
    low.location.x = 0.0
    game.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [("full", full), ("game", game), ("lo", low)])


if __name__ == "__main__":
    main()
