"""Builds the sea lamprey (creatures/lamprey) and exports it for Godot.

Run from the game's root:
    blender --background --factory-startup --python creatures/lamprey/tools/build_lamprey.py
    blender --background --factory-startup --python creatures/lamprey/tools/build_lamprey.py -- <preview folder>

It writes creatures/lamprey/models/lamprey.glb (the full model, for close pictures), lamprey_lo.glb (far off,
phones) and the editable creatures/lamprey/tools/lamprey.blend (this folder has a .gdignore). Each model is one
still mesh with one surface: the shader (lamprey.gdshader) bends it to swim, opens and closes its sucker and draws
every marking. It prints a WINDING line for each model: the check that nothing is inside out.

0.7 m from the front of the sucker to the tip of the tail, nose towards -Z, belly down, its origin at the middle
of its length on its middle line. Built from the species' anatomy (the component's README says what was used):

- THE BODY: one scaleless skin, long and eel-like: round in section at the head, deepest about the middle, and
  flattened from side to side towards the tail, which tapers to a point. No paired fins, no jaws.
- THE SUCKER (the oral disc): a round cup on the front of the head, facing forward and down: its rim fringed
  with small papillae, its inner face a shallow funnel to the round mouth in the middle, the throat behind it. It
  is built OPEN; the shader folds it shut into a slit (`gape` 0).
- THE TEETH: horny cones on the sucker's inner face in rings round the mouth, pointing in towards it, bigger
  towards the middle: the two big cusps of the supraoral plate above the mouth, the curved row of the infraoral
  plate below it, a few inner laterals each side, then rings of smaller ones out to the rim.
- THE EYES: small domes on the sides of the head, behind the sucker. ONE NOSTRIL: a short tube on the top of
  the head between and ahead of the eyes. The seven gill openings each side are drawn by the shader.
- THE FINS: thin closed solids: a low rounded first dorsal; a second dorsal, taller, that runs back into the
  tail fin round the tip of the tail; the tail fin's lower lobe under the tail.

What a point is, for the shader: vertex colour red the part, as a tenth (0 body, 0.1 sucker, 0.2 eye, 0.3
teeth, 0.4 nostril, 0.5 first dorsal, 0.6 second dorsal and tail, 0.7 tail's lower lobe). On the body: UV.x how
far along the fish (0 the front of the head to 1 the tail tip), UV.y how high on it (0 belly line to 1 back line);
UV2.x how far round the skin from the back line (metres, + on its right side, - on its left), UV2.y the whole way
from back line to belly line there (metres). On the sucker: UV.x how far out from its middle (1 the rim), UV.y
how far round it (0..1); UV2.x which part of it (0 the throat, 1 the inner face, 2 the fringed rim, 3 the outside).
On a tooth: UV.x from its root (0) to its tip (1). On the nostril: UV.x how far out from its middle. On an eye: UV
where a point is on its round face seen straight on. On a fin: UV.x from its root (0) to its edge (1), UV.y along
it. (The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.)

Everything is worked out in body lengths in Godot space (Y up, nose towards -Z) and written out in metres. The
numbers the shader shares (LENGTH, where the sucker is and the way it faces) are kept in step by hand.
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

# Kept in step with lamprey.gd and lamprey.gdshader.
LENGTH = 0.7
TAU = math.tau
BODY, DISC, EYE, TEETH, NOSTRIL, DORSAL1, DORSAL2, CAUDAL = 0, 1, 2, 3, 4, 5, 6, 7

# The sucker: the middle of its rim (body lengths, s along), the way its face looks (forward and down), and the
# two ways across it (X its width; V up and forward along its face).
DISC_S, DISC_Y = 0.024, -0.015
DISC_AXIS = Vector((0.0, -0.6, -0.8)).normalized()
DISC_X = Vector((1.0, 0.0, 0.0))
DISC_V = Vector((0.0, 0.8, -0.6))
DISC_R = 0.0305
EYE_AT = (0.07, 0.012)
EYE_BALL = (0.0095, 0.0032, 0.644)
NOSTRIL_S = 0.046


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


class Section:
    """A lofted skin: at each place along it (s) its top line, bottom line, half width, how far up from the bottom
    it is widest (0..1), and how boxy its upper and lower halves are (2 an ellipse). All in body lengths."""

    def __init__(self, rows):
        self.first = rows[0][0]
        self.last = rows[-1][0]
        self.f = [curve([(r[0], r[k]) for r in rows]) for k in range(1, 7)]

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
        for j in range(half + 1):
            want = whole * j / half
            i = min(bisect.bisect_right(acc, want) - 1, steps - 1)
            span = acc[i + 1] - acc[i]
            t = (want - acc[i]) / span if span > 1e-12 else 0.0
            out.append((lerp(dense[i][0], dense[i + 1][0], t), lerp(dense[i][1], dense[i + 1][1], t), want))
        return out, whole


# The body: s, top, bottom, half width, widest at, boxiness above, below. Round at the head (its front cut back
# on a slant behind the sucker), deepest about the middle, flattened from side to side towards the tail.
LAMPREY_BODY = [
    # (the front of the head is cut back on a slant above and behind the sucker, which is in front of it: the
    # sucker's cup must stay clear of the head, or the head shows inside it; SUCKER CLEAR checks)
    (0.020, 0.0235, 0.0195, 0.000, 0.50, 2.0, 2.0),
    (0.026, 0.0268, 0.0140, 0.016, 0.50, 2.0, 2.0),
    (0.034, 0.0285, 0.0030, 0.024, 0.50, 2.0, 2.0),
    (0.044, 0.0300, -0.0102, 0.027, 0.50, 2.0, 2.0),
    (0.054, 0.0310, -0.0235, 0.028, 0.50, 2.0, 2.0),
    (0.066, 0.0318, -0.0330, 0.029, 0.50, 2.0, 2.0),
    (0.090, 0.0330, -0.0350, 0.030, 0.50, 2.0, 2.0),
    (0.120, 0.035, -0.036, 0.030, 0.50, 2.0, 2.0),
    (0.200, 0.037, -0.038, 0.031, 0.50, 2.0, 2.0),
    (0.300, 0.039, -0.039, 0.031, 0.50, 2.0, 2.0),
    (0.400, 0.040, -0.039, 0.030, 0.50, 2.0, 2.0),
    (0.500, 0.040, -0.038, 0.027, 0.50, 2.0, 2.0),
    (0.600, 0.038, -0.035, 0.022, 0.50, 2.0, 2.0),
    (0.700, 0.034, -0.031, 0.017, 0.50, 2.0, 2.0),
    (0.800, 0.028, -0.025, 0.012, 0.50, 2.0, 2.0),
    (0.880, 0.021, -0.019, 0.0085, 0.50, 2.0, 2.0),
    (0.940, 0.014, -0.012, 0.005, 0.50, 2.0, 2.0),
    (0.975, 0.007, -0.006, 0.0025, 0.50, 2.0, 2.0),
    (0.992, 0.0012, -0.0004, 0.000, 0.50, 2.0, 2.0),
]
BODY_SKIN = Section(LAMPREY_BODY)


def body_x(s, y):
    return BODY_SKIN.x_at(s, y)


def body_frame(s, y):
    """A place on the body's right side: the point, the way out of the skin there, and the way up along it."""
    e = 0.002
    x = body_x(s, y)
    dy = (body_x(s, y + e) - body_x(s, y - e)) / (2 * e)
    ds = (body_x(s + e, y) - body_x(s - e, y)) / (2 * e)
    return Vector((x, y, s - 0.5)), Vector((1.0, -dy, -ds)).normalized(), Vector((dy, 1.0, 0.0)).normalized()


class Part:
    """One closed piece: points (body lengths), what each is for the shader, and faces. `done` welds it, turns
    every face outward and checks that."""

    def __init__(self, name):
        self.name = name
        self.verts = []
        self.data = []
        self.faces = []

    def add(self, p, uv, uv2, colour):
        self.verts.append(Vector(p))
        self.data.append((uv, uv2, colour))
        return len(self.verts) - 1

    def loft(self, rings):
        for a, b in zip(rings, rings[1:]):
            n = len(a)
            for j in range(n):
                self.faces.append((a[j], a[(j + 1) % n], b[(j + 1) % n], b[j]))

    def mirrored(self, name, flip):
        other = Part(name)
        for p, d in zip(self.verts, self.data):
            other.add((-p.x, p.y, p.z), *flip(d))
        other.faces = list(self.faces)
        return other

    @staticmethod
    def inside_out(bm):
        """How many of a closed solid's faces face inwards: a line out of a face, the way the face faces, comes
        out through the solid's skin an even number of times."""
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
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-6)
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


def flip_x(d):
    return d[0], (-d[1][0], d[1][1]), d[2]


def body(low):
    part = Part("body")
    half = 8 if low else 24
    head = 16 if low else 90
    rest = 30 if low else 150
    places = [lerp(BODY_SKIN.first, 0.13, (i / head) ** 1.3) for i in range(head)]
    places += [lerp(0.13, BODY_SKIN.last, i / rest) for i in range(rest + 1)]
    rings = []
    for s in places:
        side, whole = BODY_SKIN.outline(s, half)
        top, bot = BODY_SKIN.top(s), BODY_SKIN.bot(s)
        ring = []
        for j in list(range(half + 1)) + list(range(half, 0, -1)):
            x, y, arc = side[j]
            sign = 1.0 if len(ring) <= half else -1.0
            h = (y - bot) / max(top - bot, 1e-9)
            ring.append(part.add((sign * x, y, s - 0.5), (s, 1.0 - h),
                                 (sign * arc * LENGTH, 1.0 - whole * LENGTH), (BODY / 10.0, 0.0, 0.0)))
        rings.append(ring)
    part.loft(rings)
    return part


def disc_point(r, f, q):
    centre = Vector((0.0, DISC_Y, DISC_S - 0.5))
    return centre + (DISC_X * math.cos(q) + DISC_V * math.sin(q)) * r + DISC_AXIS * f


def face_f(r):
    """How far forward of the rim's plane the sucker's inner face is (it is a shallow funnel)."""
    return -0.012 + 0.0118 * max(0.0, (r - 0.0055) / 0.0235) ** 1.4


def disc(low):
    """The sucker, built open: one profile (how far out from its middle, how far forward) turned round its axis,
    from the bottom of the throat out over the inner face, round the fringed rim, and back over its outside."""
    part = Part("disc")
    around = 18 if low else 120
    face_steps = 4 if low else 14
    profile = [(0.0, -0.0165, 0), (0.0035, -0.016, 0), (0.0042, -0.0145, 0), (0.0048, -0.0125, 0)]
    for i in range(face_steps + 1):
        r = lerp(0.0055, 0.029, i / face_steps)
        profile.append((r, face_f(r), 1))
    profile += [(0.0305, 0.0012, 2), (0.0318, 0.0004, 2), (0.0322, -0.0012, 2), (0.0315, -0.003, 2),
                (0.0305, -0.008, 3), (0.029, -0.016, 3), (0.027, -0.024, 3), (0.022, -0.031, 3), (0.012, -0.035, 3),
                (0.004, -0.036, 3), (0.0, -0.036, 3)]
    rings = []
    for r, f, region in profile:
        ring = []
        for k in range(around):
            q = TAU * k / around
            rr = r
            if region == 2 and not low:
                # (the fringe: small papillae all round the rim)
                rr += 0.0011 * max(0.0, math.cos(q * 30.0)) ** 2
            ring.append(part.add(disc_point(rr, f, q), (r / DISC_R, 1.0 - k / around), (float(region), 0.0),
                                 (DISC / 10.0, 0.0, 0.0)))
        rings.append(ring)
    # (the loft runs round each ring, closing it, and from ring to ring; the first and last rings are points)
    for a, b in zip(rings, rings[1:]):
        n = len(a)
        for j in range(n):
            part.faces.append((a[j], a[(j + 1) % n], b[(j + 1) % n], b[j]))
    return part


def cone(part, root, way, wide, tall, sides, kind, sunk=0.0007):
    """A closed cone: its base round `root` (sunk a little), pointing along `way`."""
    way = way.normalized()
    side_a = way.cross(Vector((0.0, 0.0, 1.0)) if abs(way.z) < 0.9 else Vector((1.0, 0.0, 0.0))).normalized()
    side_b = way.cross(side_a)
    base = root - way * sunk
    ring = [part.add(base + (side_a * math.cos(TAU * k / sides) + side_b * math.sin(TAU * k / sides)) * wide,
                     (0.0, 1.0), (0.0, 1.0), (kind / 10.0, 0.0, 0.0)) for k in range(sides)]
    mid = [part.add(base + (side_a * math.cos(TAU * k / sides) + side_b * math.sin(TAU * k / sides)) * wide * 0.55
                    + way * (tall + sunk) * 0.45, (0.55, 1.0), (0.0, 1.0), (kind / 10.0, 0.0, 0.0)) for k in range(sides)]
    tip = part.add(base + way * (tall + sunk), (1.0, 1.0), (0.0, 1.0), (kind / 10.0, 0.0, 0.0))
    bottom = part.add(base, (0.0, 1.0), (0.0, 1.0), (kind / 10.0, 0.0, 0.0))
    for k in range(sides):
        n = (k + 1) % sides
        part.faces.append((ring[k], ring[n], mid[n], mid[k]))
        part.faces.append((mid[k], mid[n], tip))
        part.faces.append((ring[n], ring[k], bottom))


def tooth_at(made, r, q, wide, tall, sides, lean=0.4):
    """A tooth on the sucker's inner face at `r` out and `q` round, leaning in towards the mouth: a closed solid
    of its own (some stand close enough to touch, and each is checked alone)."""
    part = Part("tooth")
    e = 0.0005
    slope = (face_f(r + e) - face_f(r - e)) / (2 * e)
    out = DISC_X * math.cos(q) + DISC_V * math.sin(q)
    normal = (DISC_AXIS - out * slope).normalized()
    way = (normal - out * lean).normalized()
    cone(part, disc_point(r, face_f(r), q), way, wide * 1.35, tall * 1.4, sides, TEETH)
    made.append(part)


def teeth(low):
    part = []
    sides = 3 if low else 6
    up = math.pi * 0.5
    # The supraoral plate: two big cusps above the mouth.
    for q in (up - 0.2, up + 0.2):
        tooth_at(part, 0.0074, q, 0.0021, 0.0042, sides, 0.55)
    # The infraoral plate: a curved row of cusps below it.
    count = 5 if low else 7
    for i in range(count):
        q = -up + lerp(-0.62, 0.62, i / (count - 1))
        tooth_at(part, 0.0078, q, 0.0012, 0.0028, sides, 0.55)
    # The inner laterals, each side of the mouth.
    for centre in (0.0, math.pi):
        for d in ((-0.35, 0.35) if low else (-0.6, -0.2, 0.2, 0.6)):
            tooth_at(part, 0.0082, centre + d, 0.0015, 0.0032, sides, 0.5)
    # Rings of smaller teeth out towards the rim.
    rings = [(0.0145, 12, 0.0013, 0.0027)] if low else [
        (0.0122, 14, 0.00135, 0.0029), (0.0158, 18, 0.0012, 0.0025), (0.0194, 22, 0.001, 0.0021),
        (0.023, 26, 0.00085, 0.0016), (0.0262, 30, 0.0007, 0.0012)]
    for n, (r, count, wide, tall) in enumerate(rings):
        for i in range(count):
            # (each ring half a step round from the last, so the teeth fall in rows that curve out from the mouth)
            q = TAU * (i + 0.5 * (n % 2)) / count + 0.07 * math.sin(i * 2.3 + n)
            tooth_at(part, r, q, wide, tall, sides, 0.35)
    return part


def nostril(low):
    """The one nostril: a short tube on the top of the head, open at its tip."""
    part = Part("nostril")
    around = 8 if low else 20
    s = NOSTRIL_S
    top = BODY_SKIN.top(s)
    centre = Vector((0.0, top, s - 0.5))
    # (it leans back a little)
    up = Vector((0.0, 0.94, 0.34)).normalized()
    across = Vector((0.0, -0.34, 0.94)).normalized()
    profile = [(0.0, -0.004), (0.0042, -0.004), (0.0042, -0.0005), (0.0034, 0.0022), (0.0031, 0.0032),
               (0.0022, 0.0034), (0.0013, 0.0018), (0.0, 0.0012)]
    rings = []
    for r, h in profile:
        ring = []
        for k in range(around):
            q = TAU * k / around
            p = centre + (Vector((1.0, 0.0, 0.0)) * math.cos(q) + across * math.sin(q)) * r + up * h
            ring.append(part.add(p, (r / 0.0042, 1.0 - k / around), (0.0, 1.0), (NOSTRIL / 10.0, 0.0, 0.0)))
        rings.append(ring)
    part.loft(rings)
    return part


def eye(low):
    """The right eye: a small dome in the side of the head behind the sucker."""
    part = Part("eye")
    at, out, up = body_frame(*EYE_AT)
    along = up.cross(out).normalized()
    ball, stands, shown = EYE_BALL
    seen = math.sqrt(1.0 - (1.0 - stands / ball) ** 2)
    reach = math.asin(min(seen / shown, 0.999))
    centre = at - out * (ball - stands)
    rows = 4 if low else 10
    around = 10 if low else 28
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
    back = centre + out * (ball * math.cos(reach) - 0.002)
    rings.append([part.add(back, (0.5 + 0.5 * math.cos(TAU * k / around), 0.5 - 0.5 * math.sin(TAU * k / around)),
                           (0.0, 1.0), (EYE / 10.0, 0.0, 0.0)) for k in range(around)])
    part.loft(rings)
    return part


def fin(name, kind, rays, base, direction, length, thick, low):
    """A fin on the middle plane: `rays` (soft lines drawn by the shader) fanned from the line `base(t)` (t 0 its
    front to 1 its rear), each going the way `direction(t)` for `length(t)`; thin, `thick` at its root."""
    part = Part(name)
    per_ray = 1 if low else 3
    rows = 3 if low else 10
    cols = max(rays * per_ray, 6)
    normal = Vector((1.0, 0.0, 0.0))
    left, right = [], []
    for i in range(cols + 1):
        t = i / cols
        b, d, long = base(t), direction(t).normalized(), length(t)
        edge = min(1.0, t / 0.05) ** 0.5 * min(1.0, (1.0 - t) / 0.05) ** 0.5
        a, c = [], []
        for j in range(rows + 1):
            r = j / rows
            taper = 1.0 - r
            th = edge * (taper ** 0.5) * thick * (0.12 + 0.88 * taper ** 1.6)
            mid = b + d * (long * r)
            data = ((r, 1.0 - t * rays), (0.0, 1.0), (kind / 10.0, 0.0, 0.0))
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


def fins(low):
    def rake(a0, a1, down=False):
        return lambda t: Vector((0.0, (-1.0 if down else 1.0) * math.sin(math.radians(lerp(a0, a1, t))),
                                 math.cos(math.radians(lerp(a0, a1, t)))))
    made = []
    # The first dorsal: low and rounded.
    d0, d1 = 0.5, 0.636
    made.append(fin(
        "dorsal_first", DORSAL1, 12,
        lambda t: Vector((0.0, BODY_SKIN.top(lerp(d0, d1, t)) - 0.004, lerp(d0, d1, t) - 0.5)),
        rake(82.0, 50.0),
        lambda t: 0.004 + 0.02 * math.sin(math.pi * min(1.0, t ** 0.75)) ** 0.7,
        0.0042, low))
    # The second dorsal, taller, running back into the tail fin round the tip of the tail.
    e0, e1 = 0.662, 0.988
    made.append(fin(
        "dorsal_second", DORSAL2, 26,
        lambda t: Vector((0.0, BODY_SKIN.top(lerp(e0, e1, t)) - 0.003, lerp(e0, e1, t) - 0.5)),
        rake(80.0, 6.0),
        lambda t: (0.005 + 0.027 * smooth(0.0, 0.2, t) * (1.0 - 0.4 * smooth(0.3, 0.72, t))
                   + 0.009 * smooth(0.72, 0.92, t)) * (1.0 - 0.45 * smooth(0.93, 1.0, t)),
        0.0042, low))
    # The tail fin's lower lobe, under the tail.
    c0, c1 = 0.885, 0.988
    made.append(fin(
        "caudal_lower", CAUDAL, 9,
        lambda t: Vector((0.0, BODY_SKIN.bot(lerp(c0, c1, t)) + 0.003, lerp(c0, c1, t) - 0.5)),
        rake(70.0, 8.0, True),
        lambda t: (0.004 + 0.017 * smooth(0.0, 0.45, t)) * (1.0 - 0.4 * smooth(0.9, 1.0, t)),
        0.0038, low))
    return made


def make(name, low):
    parts = [body(low), disc(low), nostril(low)] + teeth(low)
    # (the head must stay out of the sucker's cup: no point of its skin within the rim's reach, ahead of the
    # plane the throat goes back to)
    centre = Vector((0.0, DISC_Y, DISC_S - 0.5))
    inside = 0
    for p in parts[0].verts:
        d = p - centre
        f = d.dot(DISC_AXIS)
        rr = (d - DISC_AXIS * f).length
        if (rr < 0.0295 and face_f(max(rr, 0.0055)) - 0.0004 < f < 0.004) or (rr < 0.005 and -0.0168 < f < 0.004):
            inside += 1
            if inside <= 8:
                print("  in the cup: s=%.4f y=%.4f x=%.4f f=%.4f r=%.4f" % (p.z + 0.5, p.y, p.x, f, (d - DISC_AXIS * f).length))
    print("SUCKER CLEAR %s: %s: %d points of the head inside the sucker's cup" % (name, "ok" if inside == 0 else "WRONG", inside))
    ball = eye(low)
    parts += [ball, ball.mirrored("eye_left", lambda d: d)]
    parts += fins(low)

    verts, faces, corners = [], [], []
    told = []
    wrong_all = 0
    teeth_told = [0, 0, 0]
    for part in parts:
        out, wrong, counted = part.done()
        if part.name == "tooth":
            teeth_told = [teeth_told[0] + 1, teeth_told[1] + wrong, teeth_told[2] + counted]
        else:
            told.append("%s %d/%d wrong" % (part.name, wrong, counted))
        wrong_all += wrong
        for face in out:
            first = len(verts)
            for co, uv, uv2, colour in face:
                verts.append(co)
                corners.append((uv, uv2, colour))
            faces.append(list(range(first, first + len(face))))
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
    material = bpy.data.materials.get("lamprey") or bpy.data.materials.new("lamprey")
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.4, 0.36, 0.24, 1.0)
    material.diffuse_color = (0.4, 0.36, 0.24, 1.0)
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
    ys = [v.co.y for v in mesh.vertices]
    zs = [v.co.z for v in mesh.vertices]
    xs = [v.co.x for v in mesh.vertices]
    print("BUILT %s verts=%d tris=%d length=%.4f depth=%.4f width=%.4f (front %.4f, back %.4f)" % (
        name, len(mesh.vertices), tris, max(ys) - min(ys), max(zs) - min(zs), max(xs) - min(xs), max(ys), min(ys)))
    told.append("%d teeth %d/%d wrong" % tuple(teeth_told))
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
    scene.render.resolution_x, scene.render.resolution_y = 1400, 800
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 100.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    # (Blender space: the nose is towards +Y, up is +Z)
    views = [("right", (1, 0, 0), (0, 0, 0), 0.75), ("left", (-1, 0, 0), (0, 0, 0), 0.75),
             ("top", (0, -0.001, 1), (0, 0, 0), 0.75), ("under", (0, 0.001, -1), (0, 0, 0), 0.75),
             ("front", (0, 1, 0), (0, 0, 0), 0.1), ("back", (0, -1, 0), (0, 0, 0), 0.1),
             ("quarter", (0.7, 0.6, 0.35), (0, 0, 0), 0.75), ("head", (1, 0.15, 0.05), (0, 0.3, 0), 0.16),
             ("head_under", (0.4, 0.5, -0.7), (0, 0.32, -0.01), 0.12), ("tail", (1, -0.2, 0.1), (0, -0.28, 0), 0.2)]
    for low, obj in ((False, made[0]), (True, made[1])):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if low and view not in ("right", "quarter", "head_under"):
                continue
            offset = Vector(direction).normalized() * 10.0
            camera.data.ortho_scale = frame
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "X" if view in ("top", "under") else "Y").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % ("lo_" if low else "", view))
            bpy.ops.render.render(write_still=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    print("SHAPE lamprey: body depth=%.4f m width=%.4f m" % (
        LENGTH * max(BODY_SKIN.top(i / 400.0) - BODY_SKIN.bot(i / 400.0) for i in range(400)),
        LENGTH * 2.0 * max(BODY_SKIN.at(i / 400.0)[2] for i in range(400))))
    full = make("lamprey", False)
    low = make("lamprey_lo", True)
    export_one(full, os.path.join(OUT, "lamprey.glb"))
    export_one(low, os.path.join(OUT, "lamprey_lo.glb"))
    low.location.x = 0.3
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "lamprey.blend"))
    low.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low])


if __name__ == "__main__":
    main()
