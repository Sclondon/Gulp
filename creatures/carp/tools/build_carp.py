"""Builds the carp (creatures/carp) and exports it for Godot.

Run from the game's root:
    blender --background --factory-startup --python creatures/carp/tools/build_carp.py
    blender --background --factory-startup --python creatures/carp/tools/build_carp.py -- <preview folder>

One shape for every type (the common carp and the koi are one species, Cyprinus carpio: Carp.Type picks the
colours and the pattern, all drawn by the shader). It writes creatures/carp/models/carp.glb (the full model, for
close pictures), carp_game.glb (the game model: about 3,000 triangles, spent as a Twilight Princess figure spends
them), carp_lo.glb (far off, phones, packs of fish) and the editable creatures/carp/tools/carp.blend (this folder has
a .gdignore). Each model is one still mesh with one surface: the shader (carp.gdshader) bends it to
swim, opens and pushes out its mouth, sculls its fins and draws every marking. It prints a WINDING line for each
model: the check that nothing is inside out.

0.7 m from snout to tail tip, nose towards -Z, belly down, its origin at the middle of its length on the line
through snout and tail. Built from the species' anatomy (the component's README says what was used):

- THE BODY: one skin from the snout to the root of the tail: deep and heavy, the back rising steeply behind the
  head to its highest just ahead of the dorsal fin, the belly full and rounded, a deep tail wrist; the gill cover a
  raised plate with a crescent rear edge. The upper head and snout are the front of the body's skin, flat
  underneath (the roof of the mouth) back to the corner of the mouth.
- THE MOUTH: small, at the front and a little under the snout. The LOWER JAW is a part of its own (with the lower
  lip, a thick roll along its edge) that runs back into the throat; the UPPER LIP is a thick roll round the front
  of the snout from one corner of the mouth to the other. The shader swings the jaw down about its hinge at the
  corner and pushes the lips and the front of the snout forward and down, so that the open mouth is a round tube.
- TWO BARBELS EACH SIDE: a short one on the upper lip towards the front, a longer one at the corner of the mouth.
- EYES: domes set high in the sides of the head.
- THE FINS: thin closed solids, thick at the root and fine at the edge, with their rays as ridges: the long dorsal
  (twenty rays, its leading spine the tallest, its edge falling and then running straight back), the forked tail
  (nineteen, its lobes rounded), the short anal (eight, its spine the longest), and a pair each of pelvic and
  pectoral fins held out and down. No adipose fin: a carp has none.

What a point is, for the shader: vertex colour red the part, as a tenth (0 body, 0.1 lower jaw with its lip, 0.2
eye, 0.3 upper lip, 0.4 dorsal, 0.5 barbel, 0.6 tail, 0.7 anal, 0.8 pelvic, 0.9 pectoral). On the body: UV.x how
far along the fish (0 snout to 1 tail tip), UV.y how high on it (0 belly line to 1 back line); UV2.x how far round
the skin from the back line (metres, + on its right side, - on its left), UV2.y the whole way from back line to
belly line there (metres); green how much of the gill cover's moving edge it is, blue how much it is inside the
mouth. On the jaw: UV as the body's but UV.y from its keel (0) to its lip (1); blue the inside of the mouth. On a
lip: UV.x how far along the fish, UV.y round the roll. On a barbel: UV.x along it (0 root to 1 tip), UV.y round it;
UV2 where its root is (how far along the fish, how high, in body lengths), for the shader to carry it with the lip.
On an eye: UV where a point is on its round face seen straight on. On a fin: UV.x along its rays (0 root to 1
edge), UV.y across it counted in rays (0 its leading edge); UV2 and blue the way its flat side faces (x, y, and z as
z / 2 + 0.5). (The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.)

Everything is worked out in body lengths in Godot space (Y up, nose towards -Z) and written out in metres. The
numbers the shader and the script share (LENGTH, the jaw's hinge, the gill cover's edge) are kept in step by hand:
change one, change the others (the SHAPE line prints them).
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

# Kept in step with carp.gd and carp.gdshader.
LENGTH = 0.7
TAU = math.tau
BODY, JAW, EYE, LIP_PART, DORSAL, BARBEL, TAIL, ANAL, PELVIC, PECTORAL = 0, 1, 2, 3, 4, 5, 6, 7, 8, 9

# Where the lower jaw hinges (the corner of the mouth) and the gill cover's rearmost reach, in body lengths.
HINGE_S = 0.066
GILL_S = 0.212
EYE_AT = (0.088, 0.03)
# The eyeball's radius, how far it stands out of the head, how much of the dome's width shows.
EYE_BALL = (0.021, 0.0036, 0.644)


def to_b(p):
    return Vector((p.x, -p.z, p.y))


# Which model is being built: FULL (close pictures), LOW (far off) or GAME (the game model: a Twilight Princess
# weight of about 2,900 triangles, spent on the outline, the eye, the lips and the fins' edges).
FULL, LOW, GAME = 0, 1, 2


def pick(lod, full, low, game):
    """The number for this model. (`lod` may be False or True, for FULL and LOW.)"""
    return (full, low, game)[int(lod)]


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
    """A lofted skin: at each place along the fish (s, 0 snout to 1 tail tip) its top line, bottom line, half
    width, how far up from the bottom it is widest (0..1), and how boxy its upper and lower halves are (2 an
    ellipse, more is squarer). All in body lengths."""

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

    def outline(self, s, half, bunch=0.0):
        """half + 1 points down its right side from the top line to the bottom line, evenly spaced along the
        skin (`bunch` more than 0: closer together at the top and bottom lines, where the outline seen from in
        front turns, and further apart across the flat flank): (x, y, how far round from the top)."""
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
            u = j / half
            want = whole * (u - bunch * math.sin(TAU * u) / TAU) if bunch else whole * j / half
            i = min(bisect.bisect_right(acc, want) - 1, steps - 1)
            span = acc[i + 1] - acc[i]
            t = (want - acc[i]) / span if span > 1e-12 else 0.0
            out.append((lerp(dense[i][0], dense[i + 1][0], t), lerp(dense[i][1], dense[i + 1][1], t), want))
        return out, whole


# The body and upper head: s, top, bottom, half width, widest at, boxiness above, below. Ahead of the hinge the
# bottom line is the roof of the mouth; behind it the throat, under which the jaw's skin runs back.
CARP_BODY = [
    (0.000, -0.004, -0.019, 0.000, 0.50, 2.0, 2.0),
    (0.005, 0.009, -0.024, 0.013, 0.45, 2.0, 2.3),
    (0.014, 0.019, -0.027, 0.021, 0.42, 2.0, 2.6),
    (0.028, 0.032, -0.029, 0.029, 0.40, 2.0, 2.8),
    (0.046, 0.047, -0.031, 0.037, 0.38, 2.1, 3.0),
    (0.066, 0.062, -0.033, 0.045, 0.36, 2.1, 3.0),
    (0.092, 0.080, -0.067, 0.053, 0.45, 2.2, 2.5),
    (0.122, 0.094, -0.080, 0.058, 0.50, 2.2, 2.4),
    (0.162, 0.110, -0.096, 0.063, 0.52, 2.2, 2.3),
    (0.205, 0.122, -0.106, 0.066, 0.53, 2.2, 2.3),
    (0.265, 0.134, -0.116, 0.068, 0.53, 2.2, 2.3),
    (0.335, 0.140, -0.121, 0.068, 0.53, 2.2, 2.3),
    (0.400, 0.139, -0.121, 0.066, 0.53, 2.2, 2.3),
    (0.480, 0.128, -0.115, 0.062, 0.53, 2.2, 2.3),
    (0.570, 0.106, -0.098, 0.053, 0.52, 2.2, 2.2),
    (0.660, 0.080, -0.077, 0.041, 0.51, 2.1, 2.1),
    (0.740, 0.063, -0.062, 0.031, 0.50, 2.0, 2.0),
    (0.800, 0.051, -0.051, 0.021, 0.50, 2.0, 2.0),
    (0.835, 0.051, -0.051, 0.014, 0.50, 2.0, 2.0),
    (0.860, 0.055, -0.055, 0.0085, 0.50, 2.0, 2.0),
    (0.882, 0.058, -0.058, 0.0045, 0.50, 2.0, 2.0),
    (0.902, 0.052, -0.052, 0.0016, 0.50, 2.0, 2.0),
    (0.911, 0.034, -0.034, 0.000, 0.50, 2.0, 2.0),
]
# The lower jaw and throat, as the body's rows. LIP for a top means the lip line: just up inside the upper lip.
LIP = None
CARP_JAW = [
    (0.006, -0.020, -0.023, 0.000, 0.75, 3.5, 2.0),
    (0.010, LIP, -0.029, 0.011, 0.75, 3.5, 2.0),
    (0.022, LIP, -0.037, 0.019, 0.78, 3.5, 2.0),
    (0.040, LIP, -0.044, 0.025, 0.80, 3.5, 2.0),
    (0.066, LIP, -0.054, 0.030, 0.80, 3.0, 2.0),
    (0.090, -0.046, -0.064, 0.030, 0.70, 2.4, 2.1),
    (0.114, -0.066, -0.082, 0.022, 0.60, 2.2, 2.1),
    (0.130, -0.077, -0.086, 0.010, 0.50, 2.0, 2.0),
    (0.136, -0.081, -0.084, 0.000, 0.50, 2.0, 2.0),
]

BODY_SKIN = Section(CARP_BODY)


def lip(s):
    """The lower jaw's lip line: just up inside the upper lip."""
    return BODY_SKIN.bot(s) + 0.002


JAW_SKIN = Section([(r[0], lip(r[0]) if r[1] is LIP else r[1]) + tuple(r[2:]) for r in CARP_JAW])
HINGE_Y = BODY_SKIN.bot(HINGE_S)


def gill_edge(h):
    """Where the gill cover's rear edge is (s) at a height on the body (0 belly to 1 back): a crescent."""
    return GILL_S - 0.25 * (h - 0.45) ** 2


def gill_plate(s, h):
    edge = gill_edge(h)
    band = smooth(0.06, 0.2, h) * (1.0 - smooth(0.78, 0.9, h))
    behind = 1.0 - smooth(edge - 0.004, edge + 0.008, s)
    raised = 0.0055 * smooth(GILL_S - 0.09, GILL_S - 0.018, s) * behind * band
    moving = smooth(GILL_S - 0.068, edge, s) * behind * band
    return raised, moving


def body_x(s, y):
    top, bot = BODY_SKIN.top(s), BODY_SKIN.bot(s)
    h = (y - bot) / max(top - bot, 1e-9)
    return BODY_SKIN.x_at(s, y) + gill_plate(s, h)[0]


def body_frame(s, y):
    """A place on the body's right side: the point, the way out of the skin there, and the way up along it."""
    e = 0.002
    x = body_x(s, y)
    dy = (body_x(s, y + e) - body_x(s, y - e)) / (2 * e)
    ds = (body_x(s + e, y) - body_x(s - e, y)) / (2 * e)
    return Vector((x, y, s - 0.5)), Vector((1.0, -dy, -ds)).normalized(), Vector((dy, 1.0, 0.0)).normalized()


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
        # (a four-cornered face with three corners on the middle plane: cut it from its fourth corner, so that
        # no triangle lies flat in the plane, back to back with its twin from the other side)
        for f in list(bm.faces):
            if len(f.verts) == 4:
                off = [loop for loop in f.loops if abs(loop.vert.co.x) > 1e-8]
                if len(off) == 1:
                    bmesh.ops.connect_verts(bm, verts=[off[0].vert, off[0].link_loop_next.link_loop_next.vert])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.normal_update()
        # The check, which does not trust the line above.
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


def skin(part, section, places, half, kind, bunch=0.0):
    """Lofts a Section into a Part. `kind` is BODY or JAW."""
    rings = []
    for s in places:
        side, whole = section.outline(s, half, bunch)
        top, bot = section.top(s), section.bot(s)
        ring = []
        ends = s <= section.first or s >= section.last
        # (down the right side and back up the left; the belly line is there twice, once for each side)
        for j in list(range(half + 1)) + list(range(half, 0, -1)):
            x, y, arc = side[j]
            sign = 1.0 if len(ring) <= half else -1.0
            h = (y - bot) / max(top - bot, 1e-9)
            yc = bot + section.at(s)[3] * (top - bot)
            if kind == BODY:
                raised, moving = gill_plate(s, h)
                x += raised * (0.0 if ends else 1.0)
                # the roof of the mouth: the flat underside of the upper head, ahead of the jaw's hinge
                roof = smooth(0.26, 0.06, (y - bot) / max(yc - bot, 1e-9)) * smooth(HINGE_S + 0.015, HINGE_S - 0.012, s)
                ring.append(part.add((sign * x, y, s - 0.5), (s, 1.0 - h),
                                     (sign * arc * LENGTH, 1.0 - whole * LENGTH), (0.0, moving, roof)))
            else:
                inside = smooth(0.55, 0.92, (y - yc) / max(top - yc, 1e-9)) if y > yc else 0.0
                inside *= smooth(HINGE_S + 0.025, HINGE_S - 0.002, s)
                ring.append(part.add((sign * x, y, s - 0.5), (s, 1.0 - h),
                                     (sign * x * LENGTH, 1.0), (JAW / 10.0, 0.0, inside)))
        rings.append(ring)
    part.loft(rings)


def body_places(low):
    if low == GAME:
        # (close together where the outline turns: round the snout and the mouth, over the gill cover's
        # crescent, and at the tail wrist and the flare into the tail; far apart along the smooth flank)
        return [0.0, 0.004, 0.01, 0.018, 0.028, 0.04, 0.053, 0.066, 0.08, 0.096, 0.114, 0.134, 0.154, 0.172,
                0.188, 0.2, 0.21, 0.218, 0.226, 0.25, 0.29, 0.335, 0.385, 0.44, 0.495, 0.55, 0.6, 0.645, 0.69,
                0.73, 0.765, 0.795, 0.82, 0.842, 0.861, 0.877, 0.89, 0.9, 0.907, 0.911]
    head = 22 if low else 90
    rest = 26 if low else 96
    behind = GILL_S + 0.014
    places = [behind * (i / head) ** 1.35 for i in range(head)]
    places += [lerp(behind, BODY_SKIN.last, i / rest) for i in range(rest + 1)]
    return places


def frames(points):
    """Tangents and a turning-free frame along a line of points."""
    n = len(points)
    ts = []
    for i in range(n):
        a, b = points[max(i - 1, 0)], points[min(i + 1, n - 1)]
        ts.append((b - a).normalized())
    seed = Vector((0.0, 1.0, 0.0)) if abs(ts[0].y) < 0.9 else Vector((1.0, 0.0, 0.0))
    ns = []
    nrm = (seed - ts[0] * seed.dot(ts[0])).normalized()
    for t in ts:
        nrm = (nrm - t * nrm.dot(t)).normalized()
        ns.append(nrm)
    return ts, ns


def tube(part, points, radii, around, data):
    """A closed tube along `points` (its first and last radius 0), `data(i, k)` what each point is."""
    ts, ns = frames(points)
    rings = []
    for i, (p, r) in enumerate(zip(points, radii)):
        b = ts[i].cross(ns[i])
        ring = []
        for k in range(around):
            q = TAU * k / around
            ring.append(part.add(p + (ns[i] * math.cos(q) + b * math.sin(q)) * r, *data(i, k)))
        rings.append(ring)
    part.loft(rings)


def lips(low):
    """The upper lip, a thick roll round the front of the snout from corner to corner of the mouth, and the lower
    lip, a thick roll along the jaw's edge (a part of the jaw: it swings with it)."""
    made = []
    stations = pick(low, 72, 24, 14)
    around = pick(low, 14, 6, 6)
    corner = HINGE_S - 0.004
    for which in ("upper", "lower"):
        part = Part(which + "_lip")
        points, radii, ss = [], [], []
        for i in range(stations + 1):
            # (closer together towards the ends, so that each closes in a round cap)
            u = math.sin(math.pi * 0.5 * (-1.0 + 2.0 * i / stations))
            a = abs(u)
            if which == "upper":
                # (round the nose the line of the lip is the outline of the snout, which passes through the
                # middle plane at its tip: s goes as the square, so that the line is smooth through it)
                s = lerp(0.0015, corner, a * a)
                y = BODY_SKIN.bot(s) + 0.0035
                x = math.copysign(max(BODY_SKIN.x_at(s, y) - 0.0025 * smooth(0.0, 0.3, a), 0.0), u)
                r = 0.0066 * math.sin(math.acos(min(a, 1.0))) ** 0.45
                p = Vector((x, y, s - 0.5))
            else:
                s = lerp(JAW_SKIN.first + 0.0015, corner - 0.002, a * a)
                y = JAW_SKIN.top(s) - 0.0035
                x = math.copysign(max(JAW_SKIN.x_at(s, y) - 0.0022 * smooth(0.0, 0.3, a), 0.0), u)
                r = 0.0056 * math.sin(math.acos(min(a, 1.0))) ** 0.45
                p = Vector((x, y, s - 0.5))
            points.append(p)
            radii.append(r)
            ss.append(s)
        # (the snout's outline is too sharp at its tip for a roll this thick: rounded off, or the roll folds
        # through itself there)
        for _ in range(int(60 * (stations / 72.0) ** 2)):
            points = [points[0]] + [(points[i - 1] + points[i] * 2.0 + points[i + 1]) / 4.0
                                    for i in range(1, len(points) - 1)] + [points[-1]]
        kind = LIP_PART if which == "upper" else JAW
        tube(part, points, radii, around,
             lambda i, k: ((ss[i], 1.0 - k / around), (0.0, 1.0), (kind / 10.0, 0.0, 0.0)))
        made.append(part)
    return made


# The barbels, the right one of each pair: where along (s) the root is, how long (body lengths), its root's
# radius, and the way it hangs (down, a little out, back or forward).
BARBELS = [
    ("rostral", 0.024, 0.021, 0.0016, Vector((0.4, -0.7, 0.6))),
    ("maxillary", HINGE_S - 0.008, 0.036, 0.0021, Vector((0.35, -0.6, 0.72))),
]


def barbels(low):
    made = []
    stations = pick(low, 16, 6, 5)
    around = pick(low, 10, 5, 4)
    for name, s, long, thick, way in BARBELS:
        part = Part("barbel_" + name)
        y = BODY_SKIN.bot(s) + 0.002
        root = Vector((BODY_SKIN.x_at(s, y + 0.003) - 0.002, y, s - 0.5))
        way = way.normalized()
        points, radii = [], []
        for i in range(stations + 1):
            t = i / stations
            # (it begins a little inside the lip, droops as it goes and curls a little back at the tip)
            droop = Vector((0.0, -0.15, 0.25)) * (t * t * long)
            points.append(root - way * 0.004 + way * (long * t + 0.004 * min(t * 4.0, 1.0)) + droop)
            radii.append(thick * (1.0 - 0.7 * t) * math.sqrt(max(0.0, min(1.0, (1.0 - t) * 12.0))) * min(1.0, 0.3 + t * 8.0) if 0 < i < stations else 0.0)
        tube(part, points, radii, around,
             lambda i, k: ((i / stations, 1.0 - k / around), (s, 1.0 - y), (BARBEL / 10.0, 0.0, 0.0)))
        made += [part, part.mirrored("barbel_%s_left" % name, flip_x)]
    return made


def eye(low):
    """The right eye: a dome set high in the side of the head."""
    part = Part("eye")
    at, out, up = body_frame(*EYE_AT)
    along = up.cross(out).normalized()
    ball, stands, shown = EYE_BALL
    seen = math.sqrt(1.0 - (1.0 - stands / ball) ** 2)
    reach = math.asin(min(seen / shown, 0.999))
    centre = at - out * (ball - stands)
    rows = pick(low, 10, 4, 3)
    around = pick(low, 32, 10, 24)
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
    back = centre + out * (ball * math.cos(reach) - 0.003)
    rings.append([part.add(back, (0.5 + 0.5 * math.cos(TAU * k / around), 0.5 - 0.5 * math.sin(TAU * k / around)),
                           (0.0, 1.0), (EYE / 10.0, 0.0, 0.0)) for k in range(around)])
    part.loft(rings)
    return part


def fin(name, kind, rays, base, direction, length, normal, thick, low, ridge_from=0.0, game_cols=None):
    """A fin: `rays` rays fanned from the line `base(t)` (t 0 its leading edge to 1 its trailing edge), each
    going the way `direction(t)` for `length(t)`; flat, facing `normal`; `thick` at its root. For the game
    model, `game_cols` is (how many columns, where column u (0..1) falls along the fin: a function)."""
    part = Part(name)
    per_ray = 1 if low else 4
    rows = pick(low, 12, 3, 2)
    cols = max(rays * per_ray, 6)
    spread = lambda u: u
    if low == GAME:
        cols, spread = game_cols
    normal = normal.normalized()
    left, right = [], []
    for i in range(cols + 1):
        t = spread(i / cols)
        b, d, long = base(t), direction(t).normalized(), length(t)
        ridge = 0.5 + 0.5 * math.cos(TAU * (t * rays - 0.5)) if (rays > 1 and not low) else 0.0
        edge = min(1.0, t / 0.06) ** 0.5 * min(1.0, (1.0 - t) / 0.1) ** 0.5
        a, c = [], []
        for j in range(rows + 1):
            r = j / rows
            taper = 1.0 - r
            th = edge * (taper ** 0.5) * (thick * (0.1 + 0.9 * taper ** 1.6) + 0.0011 * ridge * smooth(ridge_from, ridge_from + 0.14, r))
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


def clearance(part, normal, reach):
    """The least gap (mm) between a paired fin and the body's side as the shader sculls it."""
    normal = normal.normalized()
    least = 1e9
    for p, d in zip(part.verts, part.data):
        r = d[0][0]
        if r < 0.35:
            continue
        for way in (-1.0, 1.0):
            q = p + normal * (way * reach(r))
            s = q.z + 0.5
            if BODY_SKIN.bot(s) < q.y < BODY_SKIN.top(s):
                least = min(least, (q.x - body_x(s, q.y)) * LENGTH * 1000.0)
    return least if least < 1e8 else float("inf")


def fins(low):
    made = []

    def rake(a0, a1, down=False):
        return lambda t: Vector((0.0, (-1.0 if down else 1.0) * math.sin(math.radians(lerp(a0, a1, t))),
                                 math.cos(math.radians(lerp(a0, a1, t)))))
    # The dorsal fin: long-based (twenty rays; the species has three or four spines and 17 to 22 soft rays), from
    # over the pelvic fins nearly to the tail wrist: its leading spine the tallest, the edge falling quickly
    # behind it and then running back nearly straight.
    ds, de = 0.372, 0.665
    made.append(fin(
        "dorsal", DORSAL, 20,
        lambda t: Vector((0.0, BODY_SKIN.top(lerp(ds, de, t)) - 0.007, lerp(ds, de, t) - 0.5)),
        rake(64.0, 30.0),
        lambda t: (0.05 + 0.062 * (1.0 - smooth(0.02, 0.42, t)) - 0.008 * t) * (0.86 + 0.14 * smooth(0.0, 0.07, t))
        * (1.0 - 0.12 * smooth(0.86, 1.0, t)),
        Vector((1.0, 0.0, 0.0)), 0.009, low, game_cols=(12, lambda u: u ** 1.5)))
    # The tail: nineteen rays, forked, its lobes rounded at their ends.
    t_mid, t_long, t_power, t_spread = 0.088, 0.19, 1.35, 30.0

    def tail_long(t):
        a = abs(2.0 * t - 1.0)
        long = lerp(t_mid, t_long, a ** t_power)
        if a > 0.78:
            long *= 1.0 - 0.3 * ((a - 0.78) / 0.22) ** 2
        return long
    made.append(fin(
        "tail", TAIL, 19,
        lambda t: Vector((0.0, lerp(0.05, -0.05, t), 0.852 - 0.022 * (2.0 * t - 1.0) ** 2 - 0.5)),
        lambda t: Vector((0.0, math.sin(math.radians(t_spread * (1.0 - 2.0 * t))), math.cos(math.radians(t_spread * (1.0 - 2.0 * t))))),
        tail_long, Vector((1.0, 0.0, 0.0)), 0.02, low, 0.3, game_cols=(16, lambda u: 0.5 + 0.5 * (0.5 * (2.0 * u - 1.0) + 0.5 * math.sin(math.pi * (u - 0.5))))))
    # The anal fin: short (eight rays; the species has two or three spines and five or six soft rays), its spine
    # the longest.
    as_, ae = 0.655, 0.735
    made.append(fin(
        "anal", ANAL, 8,
        lambda t: Vector((0.0, BODY_SKIN.bot(lerp(as_, ae, t)) + 0.007, lerp(as_, ae, t) - 0.5)),
        rake(56.0, 26.0, True),
        lambda t: (0.094 - 0.055 * t ** 0.85) * (0.9 + 0.1 * smooth(0.0, 0.14, t)) * (1.0 - 0.12 * smooth(0.82, 1.0, t)),
        Vector((1.0, 0.0, 0.0)), 0.0085, low, game_cols=(6, lambda u: u)))

    # The paired fins, the right one of each (the left is its mirror picture).
    def on_body(s, up, sunk=0.004):
        y = BODY_SKIN.bot(s) + up
        return Vector((body_x(s, y) - sunk, y, s - 0.5))
    pv = 0.4
    p0, p1 = on_body(pv, 0.02), on_body(pv + 0.034, 0.011)
    d0, d1 = Vector((0.45, -0.75, 0.5)), Vector((0.25, -0.35, 0.9))
    pelvic = fin(
        "pelvic", PELVIC, 9, lambda t: p0.lerp(p1, t), lambda t: turn(d0, d1, t),
        lambda t: (0.102 - 0.05 * t ** 1.2) * (0.88 + 0.12 * smooth(0.0, 0.16, t)) * (1.0 - 0.12 * smooth(0.8, 1.0, t)),
        d0.cross(d1), 0.0075, low, game_cols=(7, lambda u: u))
    made += [pelvic, pelvic.mirrored("pelvic_left", flip_x)]
    print("CLEARANCE pelvic fin to body, sculling: %.1f mm" % clearance(pelvic, d0.cross(d1), lambda r: 0.012 * r * r))
    q0, q1 = on_body(GILL_S + 0.006, 0.04), on_body(GILL_S + 0.026, 0.02)
    e0, e1 = Vector((0.42, -0.32, 0.85)), Vector((0.22, -0.8, 0.55))
    pectoral = fin(
        "pectoral", PECTORAL, 16, lambda t: q0.lerp(q1, t), lambda t: turn(e0, e1, t),
        lambda t: (0.13 - 0.066 * t ** 1.15) * (0.88 + 0.12 * smooth(0.0, 0.14, t)) * (1.0 - 0.12 * smooth(0.8, 1.0, t)),
        e0.cross(e1), 0.008, low, game_cols=(8, lambda u: u))
    made += [pectoral, pectoral.mirrored("pectoral_left", flip_x)]
    print("CLEARANCE pectoral fin to body, sculling: %.1f mm" % clearance(pectoral, e0.cross(e1), lambda r: 0.03 * (0.65 * r + 0.7 * r * r)))
    return made


class OpenPart(Part):
    """A piece that is not a closed solid (the throat: a tunnel seen from inside). `done` welds it and turns
    every face to face `inward(point)`, the way into the tunnel there, and checks that instead of the
    ray test a closed solid gets."""

    def __init__(self, name, inward):
        super().__init__(name)
        self.inward = inward

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
        bm.normal_update()
        for f in list(bm.faces):
            if f.calc_area() > 1e-12 and f.normal.dot(to_b(self.inward(f.calc_center_median()))) < 0.0:
                f.normal_flip()
        bm.normal_update()
        wrong = 0
        counted = 0
        for f in bm.faces:
            if f.calc_area() > 1e-12:
                counted += 1
                wrong += f.normal.dot(to_b(self.inward(f.calc_center_median()))) <= 0.0
        out = []
        for f in bm.faces:
            out.append([(loop.vert.co.copy(), tuple(loop[uv].uv), tuple(loop[uv2].uv), tuple(loop[colour]))
                        for loop in f.loops])
        bm.free()
        return out, wrong, counted


# The throat and the gills (part 10): a short tunnel from behind the mouth back to the gills, seen through the
# open mouth; four gill arches a side across its walls, each a curved bar with pale gill rakers on its inner edge
# and a fringe of deep red filaments trailing back from it to the wall. All of it lies inside the head and the
# lower jaw, so that nothing of it shows while the mouth is shut. Vertex colour green says which piece (0 the
# tunnel's wall, 0.5 an arch with its rakers and filaments); on an arch UV.x is along it (0 its lower end to 1 its
# upper), UV.y across it (0 the rakers' edge to 1 the filaments' edge at the wall), UV2.x which arch (0 the first).
GILL = 10
# How far the floor of the mouth (the inside of the lower jaw, near its hinge) sinks as the mouth opens, so that
# it is not a wall across the way into the throat (body lengths; the shader's THROAT_SINK).
THROAT_SINK = 0.018
# And how far the roof of the mouth near the hinge vaults up into the head (the shader's THROAT_RAISE).
THROAT_RAISE = 0.02


def roof_raise(s):
    """How much of THROAT_RAISE the roof of the mouth rises at `s` (along its middle; the shader has the same sum
    times the roof's own weight, which is 1 along the middle)."""
    return smooth(0.03, 0.062, s) * smooth(HINGE_S + 0.015, HINGE_S - 0.012, s)


def floor_sink(s):
    """How much of THROAT_SINK the floor of the mouth sinks at `s`: near the hinge only, where the jaw is deep
    enough to take it (the shader has the same sum)."""
    return smooth(0.0, HINGE_S, s) * smooth(HINGE_S + 0.025, HINGE_S - 0.002, s)
THROAT_FROM, THROAT_TO = HINGE_S - 0.004, 0.205
ARCHES = (0.079, 0.094, 0.109, 0.124)


def throat(s):
    """The tunnel at `s`: its top, its bottom and its half width (body lengths). At the front it lies just under
    the roof of the mouth, inside the lower jaw; behind the hinge it rises into the head. Its floor is just over
    where the floor of the mouth sinks to with the mouth wide open, so that nothing of the jaw is left across it
    then; with the mouth shut all of it is inside the head and the jaw."""
    top = lerp(BODY_SKIN.bot(min(s, HINGE_S)) + THROAT_RAISE * roof_raise(s) - 0.002, -0.008, smooth(HINGE_S, 0.1, s))
    if s < JAW_SKIN.last - 0.004:
        bot = JAW_SKIN.top(s) - THROAT_SINK * floor_sink(s) + 0.003
        bot = max(bot, lerp(-1.0, BODY_SKIN.bot(s) + 0.022, smooth(0.1, 0.13, s)))
    else:
        bot = BODY_SKIN.bot(s) + 0.022
    half = lerp(0.016, 0.034, smooth(0.07, 0.13, s))
    # (it closes in a round cap behind the last arch)
    close = math.sqrt(max(0.0, 1.0 - smooth(THROAT_TO - 0.018, THROAT_TO, s) ** 2))
    mid = 0.5 * (top + bot)
    return mid + (top - mid) * close, mid + (bot - mid) * close, half * close


def throat_inward(p):
    """The way into the tunnel from a point on its wall (Blender space in, Godot body lengths worked in)."""
    q = Vector((p.x, p.z, -p.y)) / LENGTH
    s = q.z + 0.5
    top, bot, half = throat(min(max(s, THROAT_FROM), THROAT_TO))
    into = Vector((-q.x, 0.5 * (top + bot) - q.y, 0.0))
    if s > THROAT_TO - 0.02 and into.length < 0.25 * max(top - bot, 1e-6):
        # (on the cap: the way into the tunnel is forward)
        into = Vector((0.0, 0.0, -1.0))
    return into


def gills(low):
    made = []
    around = pick(low, 24, 8, 8)
    rings = pick(low, 26, 5, 6)
    tube = OpenPart("throat", throat_inward)
    places = [lerp(THROAT_FROM, THROAT_TO, (i / rings) ** 0.85) for i in range(rings + 1)]
    loops = []
    for s in places:
        top, bot, half = throat(s)
        mid, high = 0.5 * (top + bot), 0.5 * (top - bot)
        loop = []
        for k in range(around):
            a = TAU * k / around
            loop.append(tube.add((half * math.sin(a), mid + high * math.cos(a), s - 0.5), (s, 1.0 - k / around),
                                 (0.0, 1.0), (GILL / 10.0, 0.0, 0.0)))
        loops.append(loop)
    tube.loft(loops)
    # (the cap at the back: its last ring is a point, so the loft has closed it)
    made.append(tube)
    # The arches, the right one of each pair (the left is its mirror picture).
    cols = pick(low, 14, 4, 4)
    rows = pick(low, 8, 2, 2)
    for n, s0 in enumerate(ARCHES):
        top, bot, half = throat(s0)
        mid, high = 0.5 * (top + bot), 0.5 * (top - bot)
        part = Part("gill_arch_%d" % n)
        sheets = ([], [])
        for i in range(cols + 1):
            t = i / cols
            phi = math.radians(lerp(-72.0, 72.0, t))
            wall = Vector((half * math.cos(phi), mid + high * math.sin(phi), 0.0))
            centre = Vector((0.0, mid, 0.0))
            edge = min(1.0, t / 0.12) ** 0.5 * min(1.0, (1.0 - t) / 0.12) ** 0.5
            a, b = [], []
            for j in range(rows + 1):
                u = j / rows
                # (from the rakers' edge, well in from the wall, out to the wall; the filaments' part trails back)
                p = centre + (wall - centre) * lerp(0.12, 1.0, u)
                p.z = s0 - 0.5 + 0.01 * max(0.0, u - 0.4) ** 1.3
                # (the rakers' edge keeps a little thickness and is closed by its own strip: a blade edge of
                # no thickness, welded, leaves its points' normals lying in the blade, and Godot then reads
                # the first row's big triangles as wound against them)
                th = 0.0038 * edge * (0.3 + 0.7 * u)
                data = ((t, 1.0 - u), (float(n), 1.0 - 1.0), (GILL / 10.0, 0.5, 0.0))
                a.append(part.add(p + Vector((0.0, 0.0, -th * 0.5)), *data))
                b.append(part.add(p + Vector((0.0, 0.0, th * 0.5)), *data))
            sheets[0].append(a)
            sheets[1].append(b)
        for i in range(cols):
            for j in range(rows):
                for sheet in sheets:
                    q0, q1, q2, q3 = sheet[i][j], sheet[i + 1][j], sheet[i + 1][j + 1], sheet[i][j + 1]
                    part.faces.append((q0, q1, q2, q3))
            # (the root along the wall and the rakers' edge close it)
            part.faces.append((sheets[0][i][rows], sheets[0][i + 1][rows], sheets[1][i + 1][rows], sheets[1][i][rows]))
            part.faces.append((sheets[0][i][0], sheets[0][i + 1][0], sheets[1][i + 1][0], sheets[1][i][0]))
        made += [part, part.mirrored("gill_arch_%d_left" % n, flip_x)]
    return made


def make(name, low):
    parts = []
    body = Part("body")
    skin(body, BODY_SKIN, body_places(low), pick(low, 32, 10, 9), BODY, pick(low, 0.0, 0.0, 0.45))
    parts.append(body)
    jaw = Part("jaw")
    jaw_rings = pick(low, 44, 14, 10)
    skin(jaw, JAW_SKIN, [lerp(JAW_SKIN.first, JAW_SKIN.last, (i / jaw_rings) ** 1.25) for i in range(jaw_rings + 1)],
         pick(low, 14, 5, 5), JAW)
    parts.append(jaw)
    parts += lips(low)
    parts += barbels(low)
    ball = eye(low)
    parts += [ball, ball.mirrored("eye_left", lambda d: d)]
    parts += fins(low)
    # (the throat and the gills last: on the full model they are a second surface, so that the first is
    # exactly as it was before they were added)
    gill_parts = gills(low)
    parts += gill_parts

    verts, faces, corners = [], [], []
    told = []
    wrong_all = 0
    gill_from = None
    for part in parts:
        if part is gill_parts[0]:
            gill_from = len(faces)
        out, wrong, counted = part.done()
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
    material = bpy.data.materials.get("carp") or bpy.data.materials.new("carp")
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.62, 0.5, 0.3, 1.0)
    material.diffuse_color = (0.62, 0.5, 0.3, 1.0)
    mesh.materials.append(material)
    if low == FULL:
        inside = bpy.data.materials.get("carp_throat") or bpy.data.materials.new("carp_throat")
        inside.use_nodes = True
        next(n for n in inside.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0.5, 0.08, 0.08, 1.0)
        inside.diffuse_color = (0.5, 0.08, 0.08, 1.0)
        mesh.materials.append(inside)
        for poly in mesh.polygons[gill_from:]:
            poly.material_index = 1
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
    print("BUILT %s verts=%d tris=%d length=%.4f depth=%.4f width=%.4f" % (
        name, len(mesh.vertices), tris, max(ys) - min(ys), max(zs) - min(zs), max(xs) - min(xs)))
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
    # (Blender space: the nose is towards +Y, up is +Z; laid out for a fish 0.4 m long)
    views = [("right", (1, 0, 0), (0, 0, 0), 0.46), ("left", (-1, 0, 0), (0, 0, 0), 0.46),
             ("top", (0, -0.001, 1), (0, 0, 0), 0.46), ("under", (0, 0.001, -1), (0, 0, 0), 0.46),
             ("front", (0, 1, 0), (0, 0, 0), 0.24), ("back", (0, -1, 0), (0, 0, 0), 0.24),
             ("quarter", (0.7, 0.6, 0.35), (0, 0, 0), 0.44), ("head", (1, 0.15, 0.05), (0, 0.15, 0), 0.16),
             ("head_under", (0.5, 0.5, -0.7), (0, 0.15, -0.01), 0.16)]
    for low, obj in ((FULL, made[0]), (LOW, made[1]), (GAME, made[2])):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if low == LOW and view not in ("right", "quarter"):
                continue
            size = LENGTH / 0.4
            offset = Vector(direction).normalized() * 10.0
            camera.data.ortho_scale = frame * size
            camera.location = Vector(target) * size + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "X" if view in ("top", "under") else "Y").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % (("", "lo_", "game_")[low], view))
            bpy.ops.render.render(write_still=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    print("SHAPE carp: hinge_s=%.4f hinge_y=%.4f gill_s=%.4f body depth=%.4f m width=%.4f m" % (HINGE_S, HINGE_Y, GILL_S, LENGTH * max(BODY_SKIN.top(i / 400.0) - BODY_SKIN.bot(i / 400.0) for i in range(400)), LENGTH * 2.0 * max(BODY_SKIN.at(i / 400.0)[2] for i in range(400))))
    at, out, up = body_frame(*EYE_AT)
    centre = at - out * (EYE_BALL[0] - EYE_BALL[1])
    print("EYE carp (the right eye, Godot metres, for the shader's cartoon eye): centre=(%.5f, %.5f, %.5f) out=(%.4f, %.4f, %.4f)" % (
        centre.x * LENGTH, centre.y * LENGTH, centre.z * LENGTH, out.x, out.y, out.z))
    full = make("carp", FULL)
    low = make("carp_lo", LOW)
    game = make("carp_game", GAME)
    export_one(full, os.path.join(OUT, "carp.glb"))
    export_one(low, os.path.join(OUT, "carp_lo.glb"))
    export_one(game, os.path.join(OUT, "carp_game.glb"))
    low.location.x = 0.5
    game.location.x = 1.0
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "carp.blend"))
    low.location.x = 0.0
    game.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low, game])


if __name__ == "__main__":
    main()
