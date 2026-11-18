"""Builds the cutthroat trout (creatures/cutthroat_trout) and exports it for Godot.
(Added 2026-11-18: it also writes the GAME model, models/..._game.glb, a third model of the same curves with
far fewer, better placed points, into the same .blend; the full and low models come out exactly as before. See
GAME, `spread` and `make`, and the component's README.)

Run from the game's root:
    blender --background --python creatures/cutthroat_trout/tools/build_cutthroat_trout.py
    blender --background --python creatures/cutthroat_trout/tools/build_cutthroat_trout.py -- <preview folder>   # with pictures

Writes creatures/cutthroat_trout/models/cutthroat_trout.glb (the full model, for close pictures) and
cutthroat_trout_lo.glb (far off, phones), and the editable creatures/cutthroat_trout/tools/cutthroat_trout.blend
(this folder has a .gdignore). Each model is one still mesh with one surface: the shader
(cutthroat_trout.gdshader) bends it to swim, works its jaw, gill covers and fins, and draws every marking. It
prints a WINDING line for each model: the check that nothing is inside out.

A cutthroat trout (Oncorhynchus clarkii), 0.4 m from snout to tail tip, nose towards -Z, belly down, its origin at
the middle of its length on the line through snout and tail. Built from the species' anatomy:

- THE BODY: one skin from snout to the root of the tail, deepest at the shoulder (just ahead of the dorsal fin),
  narrowing to the wrist of the tail and flaring a little where the tail's rays begin; widest a little above its
  middle; the gill cover a raised plate with a crescent rear edge.
- THE HEAD: the upper head and snout are the front of the body's skin, flat underneath (the roof of the mouth); the
  LOWER JAW is a part of its own that fits up inside the upper lip and runs back into the throat (the shader swings
  it about its hinge under the eye); a MAXILLA on each side, the plate along the upper lip that in a cutthroat
  reaches back past the eye; EYES, domes set in the sides of the head.
- THE FINS: thin closed solids, thick at the root and fine at the edge, with their rays as ridges: the dorsal, the
  small fleshy adipose, the broad barely forked tail, the anal, and a pair each of pelvic and pectoral fins held out
  and down like small wings.

What a point is, for the shader: vertex colour red the part, as a tenth (0 body, 0.1 lower jaw, 0.2
eye, 0.3 maxilla, 0.4 dorsal, 0.5 adipose, 0.6 tail, 0.7 anal, 0.8 pelvic, 0.9 pectoral). On the body: UV.x how far along the
fish (0 snout to 1 tail tip), UV.y how high on it (0 belly line to 1 back line); UV2.x how far round the skin from
the back line (metres, + on its right side, - on its left), UV2.y the whole way from back line to belly line there
(metres); green how much of the gill cover's moving edge it is, blue how much it is inside the mouth. On the jaw:
UV as the body's but UV.y from its keel (0) to its lip (1); UV2.x how far to the side (metres); blue the inside of
the mouth. On an eye: UV where a point is on its round face seen straight on (its middle at 0.5, 0.5; its rim 0.5 away). On a fin: UV.x along its rays (0 root to 1 edge),
UV.y across it counted in rays (0 its leading edge); UV2 and blue the way its flat side faces (x, y, and z as
z / 2 + 0.5), which is the way the shader waves it. (The glTF writer flips V: what is written here is 1 - v, so
that Godot reads v.)

Everything here is worked out in body lengths in Godot space (Y up, nose towards -Z) and written out in metres.
The numbers the shader and the script share (LENGTH, the jaw's hinge, the gill cover's edge) are kept in step by
hand: change one, change the others.
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

# Kept in step with cutthroat_trout.gd and cutthroat_trout.gdshader.
LENGTH = 0.4
TAU = math.tau
BODY, JAW, EYE, MAXILLA, DORSAL, ADIPOSE, TAIL, ANAL, PELVIC, PECTORAL = 0, 1, 2, 3, 4, 5, 6, 7, 8, 9
# True while the GAME model is built (`make`): the same curves and parts as the full model with far fewer points,
# put where the outline bends (see `spread`). The full and low models never see it.
GAME = False


def spread(first, last, count, ring_at, floor=0.6):
    """For the game model: count + 1 places from `first` to `last` along the fish, close together where the skin
    bends most along its length (the snout, the gill cover's step, the wrist of the tail) and further apart along
    the flanks. `ring_at(s)` gives points round the skin at s. A straight line between places misses a curve by
    about its bend times the gap squared, so the places are spaced by the square root of the bend, plus `floor`
    of the mean so that no stretch is left bare (the swimming bend needs rings all the way)."""
    n = 360
    h = (last - first) / n
    ss = [first + h * i for i in range(n + 1)]
    rings = [ring_at(s) for s in ss]
    dens = []
    for i in range(n + 1):
        a, b, c = rings[max(i - 1, 0)], rings[i], rings[min(i + 1, n)]
        bend = max((a[k] - b[k] * 2.0 + c[k]).length for k in range(len(b))) / (h * h)
        dens.append(math.sqrt(bend))
    dens[0], dens[-1] = dens[1], dens[-2]
    mean = sum(dens) / len(dens)
    dens = [d + floor * mean for d in dens]
    acc = [0.0]
    for i in range(n):
        acc.append(acc[-1] + 0.5 * (dens[i] + dens[i + 1]))
    places = []
    for k in range(count + 1):
        want = acc[-1] * k / count
        i = min(bisect.bisect_right(acc, want) - 1, n - 1)
        t = (want - acc[i]) / max(acc[i + 1] - acc[i], 1e-12)
        places.append(lerp(ss[i], ss[i + 1], t))
    places[0], places[-1] = first, last
    return places


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
        """How far out the skin is at height y."""
        top, bot, hw, ycf, nt, nb = self.at(s)
        yc = bot + ycf * (top - bot)
        if y >= yc:
            u, n = (y - yc) / max(top - yc, 1e-9), nt
        else:
            u, n = (yc - y) / max(yc - bot, 1e-9), nb
        u = max(0.0, min(1.0, u))
        return hw * (1.0 - u ** n) ** (1.0 / n)

    def outline(self, s, half):
        """half + 1 points down its right side from the top line to the bottom line, evenly spaced along the
        skin: (x, y, how far round from the top)."""
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
            if GAME:
                # (a point on the widest place of every ring, so that the outline seen from above is whole;
                # closer together towards the back line and the belly line, where a narrow fish's skin
                # turns most, and further apart across the flat of its side)
                widest = acc[max(range(steps + 1), key=lambda k: dense[k][0])]
                jw = int(half * 0.45 + 0.5)
                if j <= jw:
                    u = j / jw
                    want = widest * (u - 0.3 * math.sin(math.pi * u) / math.pi)
                else:
                    u = (j - jw) / (half - jw)
                    want = widest + (whole - widest) * (u + 0.3 * math.sin(math.pi * u) / math.pi)
            i = min(bisect.bisect_right(acc, want) - 1, steps - 1)
            span = acc[i + 1] - acc[i]
            t = (want - acc[i]) / span if span > 1e-12 else 0.0
            out.append((lerp(dense[i][0], dense[i + 1][0], t), lerp(dense[i][1], dense[i + 1][1], t), want))
        return out, whole


# The body and upper head: s, top, bottom, half width, widest at, boxiness above, below.
BODY_ROWS = [
    (0.000, 0.008, -0.001, 0.000, 0.30, 2.0, 2.6),
    (0.004, 0.024, -0.008, 0.018, 0.30, 2.0, 2.6),
    (0.014, 0.034, -0.012, 0.027, 0.30, 2.0, 3.0),
    (0.032, 0.045, -0.016, 0.034, 0.28, 2.0, 3.2),
    (0.055, 0.054, -0.020, 0.040, 0.27, 2.1, 3.2),
    (0.085, 0.064, -0.025, 0.046, 0.27, 2.1, 3.2),
    (0.112, 0.072, -0.031, 0.050, 0.30, 2.2, 3.0),
    (0.140, 0.079, -0.064, 0.053, 0.45, 2.2, 2.6),
    (0.175, 0.086, -0.084, 0.056, 0.52, 2.2, 2.4),
    (0.215, 0.092, -0.096, 0.058, 0.56, 2.2, 2.3),
    (0.300, 0.101, -0.109, 0.062, 0.58, 2.2, 2.3),
    (0.380, 0.105, -0.114, 0.063, 0.58, 2.2, 2.3),
    (0.500, 0.099, -0.108, 0.058, 0.58, 2.2, 2.3),
    (0.600, 0.086, -0.092, 0.049, 0.57, 2.2, 2.2),
    (0.700, 0.067, -0.070, 0.037, 0.55, 2.1, 2.1),
    (0.780, 0.050, -0.052, 0.026, 0.52, 2.0, 2.0),
    (0.830, 0.043, -0.044, 0.018, 0.50, 2.0, 2.0),
    (0.862, 0.045, -0.046, 0.0115, 0.50, 2.0, 2.0),
    (0.885, 0.049, -0.050, 0.0070, 0.50, 2.0, 2.0),
    (0.910, 0.052, -0.053, 0.0035, 0.50, 2.0, 2.0),
    (0.930, 0.046, -0.047, 0.0015, 0.50, 2.0, 2.0),
    (0.938, 0.030, -0.031, 0.000, 0.50, 2.0, 2.0),
]
# The lower jaw and throat.
JAW_ROWS = [
    (0.004, -0.011, -0.016, 0.000, 0.75, 3.5, 2.0),
    (0.008, -0.009, -0.024, 0.015, 0.75, 3.5, 2.0),
    (0.022, -0.011, -0.033, 0.024, 0.78, 3.5, 2.0),
    (0.045, -0.015, -0.042, 0.030, 0.80, 3.5, 2.0),
    (0.078, -0.022, -0.054, 0.036, 0.80, 3.5, 2.0),
    (0.112, -0.029, -0.065, 0.041, 0.80, 3.0, 2.0),
    (0.140, -0.040, -0.074, 0.040, 0.70, 2.4, 2.1),
    (0.168, -0.062, -0.079, 0.024, 0.60, 2.2, 2.1),
    (0.186, -0.072, -0.078, 0.010, 0.50, 2.0, 2.0),
    (0.192, -0.075, -0.076, 0.000, 0.50, 2.0, 2.0),
]
BODY_SKIN = Section(BODY_ROWS)
JAW_SKIN = Section(JAW_ROWS)


def gill_edge(h):
    """Where the gill cover's rear edge is (s) at a height on the body (0 belly to 1 back): a crescent."""
    return 0.218 - 0.25 * (h - 0.45) ** 2


def gill_plate(s, h):
    """How far the gill cover stands out from the skin behind it (body lengths), and how much of its moving
    edge a point is (0..1)."""
    edge = gill_edge(h)
    band = smooth(0.06, 0.2, h) * (1.0 - smooth(0.78, 0.9, h))
    behind = 1.0 - smooth(edge - 0.004, edge + 0.008, s)
    raised = 0.006 * smooth(0.13, 0.2, s) * behind * band
    moving = smooth(0.15, edge, s) * behind * band
    return raised, moving


def body_x(s, y):
    """How far out the body's skin is at height y, gill cover and all."""
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
    """One closed piece of the fish: points (body lengths), what each is for the shader, and four-cornered
    faces. `done` welds it, turns every face outward and checks that."""

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
        """Returns (faces as lists of (point in Blender metres, uv, uv2, colour), faces wound wrongly, faces)."""
        bm = bmesh.new()
        uv = bm.loops.layers.uv.new("uv")
        uv2 = bm.loops.layers.uv.new("uv2")
        colour = bm.loops.layers.float_color.new("colour")
        made = [bm.verts.new(to_b(p * LENGTH)) for p in self.verts]
        for face in self.faces:
            # (a face that closes to a point at the end of a skin has corners in one place: the weld below
            # makes a triangle of it or drops it)
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
        # (where a skin closes to a line on the middle plane, or a fin on that plane thins to nothing at its
        # leading tip, a four-cornered face has three corners in that plane: cut it from its fourth corner, or whoever cuts it in two later may leave a triangle lying
        # flat in the plane, back to back with its twin from the other side)
        for f in list(bm.faces):
            if len(f.verts) == 4:
                off = [loop for loop in f.loops if abs(loop.vert.co.x) > 1e-8]
                if len(off) == 1:
                    bmesh.ops.connect_verts(bm, verts=[off[0].vert, off[0].link_loop_next.link_loop_next.vert])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.normal_update()
        # The check, which does not trust the line above (it has turned a whole fin inside out before now).
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


def flip_body(d):
    return d[0], (-d[1][0], d[1][1]), d[2]


def flip_fin(d):
    return d[0], (-d[1][0], d[1][1]), d[2]


def skin(part, section, places, half, kind):
    """Lofts a Section into a Part. `kind` is BODY or JAW."""
    rings = []
    for s in places:
        side, whole = section.outline(s, half)
        top, bot = section.top(s), section.bot(s)
        ring = []
        ends = s <= section.first or s >= section.last
        # (down the right side and back up the left; the belly line is there twice, once for each side, so that
        # how far round the skin a point is does not run from one side's number to the other's across one face)
        for j in list(range(half + 1)) + list(range(half, 0, -1)):
            x, y, arc = side[j]
            sign = 1.0 if len(ring) <= half else -1.0
            h = (y - bot) / max(top - bot, 1e-9)
            if kind == BODY:
                raised, moving = gill_plate(s, h)
                x += raised * (0.0 if ends else 1.0)
                # the roof of the mouth: the flat underside of the upper head, ahead of the jaw's hinge
                yc = bot + section.at(s)[3] * (top - bot)
                roof = smooth(0.4, 0.12, (y - bot) / max(yc - bot, 1e-9)) * smooth(0.127, 0.1, s)
                ring.append(part.add((sign * x, y, s - 0.5), (s, 1.0 - h),
                                     (sign * arc * LENGTH, 1.0 - whole * LENGTH), (0.0, moving, roof)))
            else:
                yc = bot + section.at(s)[3] * (top - bot)
                inside = smooth(0.55, 0.92, (y - yc) / max(top - yc, 1e-9)) if y > yc else 0.0
                inside *= smooth(0.137, 0.11, s)
                ring.append(part.add((sign * x, y, s - 0.5), (s, 1.0 - h),
                                     (sign * x * LENGTH, 1.0), (JAW / 10.0, 0.0, inside)))
        rings.append(ring)
    part.loft(rings)


def body_ring(s, half=10):
    """Points round the body's skin at s, the gill cover's plate and all (for `spread`)."""
    side, whole = BODY_SKIN.outline(s, half)
    top, bot = BODY_SKIN.top(s), BODY_SKIN.bot(s)
    return [Vector((x + gill_plate(s, (y - bot) / max(top - bot, 1e-9))[0], y, s)) for x, y, arc in side]


def body_places(low):
    if GAME:
        return spread(0.0, BODY_SKIN.last, GAME_BODY_RINGS, body_ring)
    head = 20 if low else 80
    rest = 26 if low else 92
    places = [0.23 * (i / head) ** 1.35 for i in range(head)]
    places += [lerp(0.23, BODY_SKIN.last, i / rest) for i in range(rest + 1)]
    return places


def maxilla(low):
    """The plate along the upper lip of the right side, from near the snout back past the eye."""
    part = Part("maxilla")
    stations = 8 if low else 26
    around = 6 if low else 12
    if GAME:
        stations, around = 5, 4
    rings = []
    for i in range(stations + 1):
        u = i / stations
        s = lerp(0.018, 0.132, u)
        # (along the lip, and on down the line of the mouth behind the jaw's hinge)
        y = BODY_SKIN.bot(min(s, 0.106)) + 0.0045 - max(s - 0.106, 0.0) * 0.3
        at, out, up = body_frame(s, y)
        ends = math.sin(math.pi * u) ** 0.5 if 0.0 < u < 1.0 else 0.0
        high = lerp(0.0035, 0.0095, smooth(0.0, 0.8, u)) * ends
        thick = 0.0042 * ends
        top, bot = BODY_SKIN.top(s), BODY_SKIN.bot(s)
        ring = []
        for k in range(around):
            q = TAU * k / around
            p = at - out * 0.0012 + up * (high * math.cos(q)) + out * (thick * math.sin(q))
            h = max(0.0, min(1.0, (p.y - bot) / (top - bot)))
            ring.append(part.add(p, (s, 1.0 - 0.5 * (1.0 + math.cos(q))), (0.0, 1.0), (MAXILLA / 10.0, 0.0, 0.0)))
        rings.append(ring)
    part.loft(rings)
    return part


EYE_AT = (0.07, 0.03)


def eye(low):
    """The right eye: a dome set in the side of the head."""
    part = Part("eye")
    at, out, up = body_frame(*EYE_AT)
    along = up.cross(out).normalized()
    ball = 0.028
    reach = math.radians(58.0)
    centre = at - out * (ball - 0.0045)
    # (for the shader's cartoon eye: the middle of the eye's face on the skin, and the way it faces, Godot metres)
    print("EYE at (%.5f, %.5f, %.5f) out (%.4f, %.4f, %.4f)" % (*(at * LENGTH), *out))
    rows = 4 if low else 10
    around = 10 if low else 32
    if GAME:
        # (round enough for the cartoon eye drawn on it: 24 a side)
        rows, around = 3, 24
    rings = []
    for i in range(rows + 1):
        a = reach * i / rows
        ring = []
        for k in range(around):
            q = TAU * k / around
            p = centre + out * (ball * math.cos(a)) + (up * math.cos(q) + along * math.sin(q)) * (ball * math.sin(a))
            # (UV: where it is on the eye's round face, seen straight on: its middle at (0.5, 0.5), up towards +x)
            across = 0.5 * math.sin(a) / math.sin(reach)
            ring.append(part.add(p, (0.5 + across * math.cos(q), 1.0 - (0.5 + across * math.sin(q))), (0.0, 1.0),
                                 (EYE / 10.0, 0.0, 0.0)))
        rings.append(ring)
    # (closed behind, inside the head)
    back = centre - out * 0.004
    rings.append([part.add(back, (0.5 + 0.5 * math.cos(TAU * k / around), 0.5 - 0.5 * math.sin(TAU * k / around)),
                           (0.0, 1.0), (EYE / 10.0, 0.0, 0.0)) for k in range(around)])
    part.loft(rings)
    return part


def fin(name, kind, rays, base, direction, length, normal, thick, low, fleshy=False, ridge_from=0.0):
    """A fin: `rays` rays fanned from the line `base(t)` (t 0 its leading edge to 1 its trailing edge), each
    going the way `direction(t)` for `length(t)`; flat, facing `normal`; `thick` at its root."""
    part = Part(name)
    per_ray = 1 if low else 4
    rows = 3 if low else 12
    cols = max(rays * per_ray, 6)
    if GAME:
        # (a point every second ray along the edge; two rows out along the rays, three on the big fins that bend)
        cols = max((rays + 1) // 2, 4)
        rows = 3 if rays >= 13 else 2
    normal = normal.normalized()
    left, right = [], []
    for i in range(cols + 1):
        t = i / cols
        if GAME:
            # (closer together at its leading edge and its trailing tip, where its outline turns)
            t = t - 0.55 * math.sin(TAU * t) / TAU
        b, d, long = base(t), direction(t).normalized(), length(t)
        ridge = 0.5 + 0.5 * math.cos(TAU * (t * rays - 0.5)) if (rays > 1 and not low) else 0.0
        edge = min(1.0, t / 0.06) ** 0.5 * min(1.0, (1.0 - t) / 0.1) ** 0.5
        a, c = [], []
        for j in range(rows + 1):
            r = j / rows
            # (finer rows towards the edge, where it bends most)
            taper = 1.0 - r
            if fleshy:
                th = thick * edge * (taper ** 0.45)
            else:
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
                # (at the two corners of its edge three of a face's corners have no thickness: cut it from
                # the fourth, so that no triangle lies flat between the fin's two sides)
                if j == rows - 1 and i == 0:
                    part.faces += [(a, b, d), (b, c, d)]
                elif j == rows - 1 and i == cols - 1:
                    part.faces += [(a, b, c), (a, c, d)]
                else:
                    part.faces.append((a, b, c, d))
        # (closed at the root, inside the body)
        part.faces.append((left[i][0], right[i][0], right[i + 1][0], left[i + 1][0]))
    return part


def turn(d0, d1, t):
    """From one direction round to another."""
    d0, d1 = d0.normalized(), d1.normalized()
    angle = d0.angle(d1)
    return (d0 * math.sin((1.0 - t) * angle) + d1 * math.sin(t * angle)) / math.sin(angle)


def clearance(part, normal, reach):
    """The least gap (mm) between a paired fin and the body's side as the shader sculls it: every point of the
    fin from a third of the way out, pushed as far as it goes either way (`reach(r)`, body lengths: the shader's
    numbers), against the body's skin at its height (points under the belly have no body beside them)."""
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
    # The dorsal fin: twelve rays, its leading edge the tallest, raked back.
    made.append(fin(
        "dorsal", DORSAL, 12,
        lambda t: Vector((0.0, BODY_SKIN.top(0.445 + 0.13 * t) - 0.007, 0.445 + 0.13 * t - 0.5)),
        lambda t: Vector((0.0, math.sin(math.radians(lerp(68.0, 30.0, t))), math.cos(math.radians(lerp(68.0, 30.0, t))))),
        lambda t: (0.118 - 0.056 * t ** 1.05) * (0.9 + 0.1 * smooth(0.0, 0.14, t)) * (1.0 - 0.14 * smooth(0.82, 1.0, t)),
        Vector((1.0, 0.0, 0.0)), 0.0085, low))
    # The adipose fin: a small fleshy flap with no rays, between the dorsal and the tail.
    made.append(fin(
        "adipose", ADIPOSE, 1,
        lambda t: Vector((0.0, BODY_SKIN.top(0.762 + 0.026 * t) - 0.004, 0.762 + 0.026 * t - 0.5)),
        lambda t: Vector((0.0, math.sin(math.radians(lerp(58.0, 16.0, t))), math.cos(math.radians(lerp(58.0, 16.0, t))))),
        lambda t: 0.036 * (0.72 + 0.28 * math.sin(math.pi * t ** 0.8)),
        Vector((1.0, 0.0, 0.0)), 0.0075, low, True))
    # The tail: nineteen rays, broad, barely forked, its lobes rounded.

    def tail_long(t):
        a = abs(2.0 * t - 1.0)
        long = lerp(0.104, 0.182, a ** 1.7)
        if a > 0.86:
            long *= 1.0 - 0.2 * ((a - 0.86) / 0.14) ** 2
        return long
    made.append(fin(
        "tail", TAIL, 19,
        lambda t: Vector((0.0, lerp(0.045, -0.046, t), 0.864 - 0.024 * (2.0 * t - 1.0) ** 2 - 0.5)),
        lambda t: Vector((0.0, math.sin(math.radians(27.0 * (1.0 - 2.0 * t))), math.cos(math.radians(27.0 * (1.0 - 2.0 * t))))),
        tail_long, Vector((1.0, 0.0, 0.0)), 0.02, low, False, 0.3))
    # The anal fin: eleven rays.
    made.append(fin(
        "anal", ANAL, 11,
        lambda t: Vector((0.0, BODY_SKIN.bot(0.705 + 0.09 * t) + 0.007, 0.705 + 0.09 * t - 0.5)),
        lambda t: Vector((0.0, -math.sin(math.radians(lerp(62.0, 28.0, t))), math.cos(math.radians(lerp(62.0, 28.0, t))))),
        lambda t: (0.094 - 0.048 * t ** 1.05) * (0.9 + 0.1 * smooth(0.0, 0.14, t)) * (1.0 - 0.14 * smooth(0.82, 1.0, t)),
        Vector((1.0, 0.0, 0.0)), 0.008, low))

    # The paired fins, the right one of each (the left is its mirror picture).
    def on_body(s, up, sunk=0.004):
        y = BODY_SKIN.bot(s) + up
        return Vector((body_x(s, y) - sunk, y, s - 0.5))
    p0, p1 = on_body(0.524, 0.016), on_body(0.55, 0.009)
    d0, d1 = Vector((0.45, -0.75, 0.5)), Vector((0.25, -0.35, 0.9))
    pelvic = fin(
        "pelvic", PELVIC, 9, lambda t: p0.lerp(p1, t), lambda t: turn(d0, d1, t),
        lambda t: (0.09 - 0.04 * t ** 1.2) * (0.88 + 0.12 * smooth(0.0, 0.16, t)) * (1.0 - 0.12 * smooth(0.8, 1.0, t)),
        d0.cross(d1), 0.007, low)
    made += [pelvic, pelvic.mirrored("pelvic_left", flip_fin)]
    print("CLEARANCE pelvic fin to body, sculling: %.1f mm" % clearance(pelvic, d0.cross(d1), lambda r: 0.012 * r * r))
    q0, q1 = on_body(0.226, 0.036), on_body(0.243, 0.017)
    e0, e1 = Vector((0.4, -0.3, 0.87)), Vector((0.2, -0.8, 0.55))
    pectoral = fin(
        "pectoral", PECTORAL, 13, lambda t: q0.lerp(q1, t), lambda t: turn(e0, e1, t),
        lambda t: (0.15 - 0.08 * t ** 1.15) * (0.88 + 0.12 * smooth(0.0, 0.14, t)) * (1.0 - 0.12 * smooth(0.8, 1.0, t)),
        e0.cross(e1), 0.0075, low)
    made += [pectoral, pectoral.mirrored("pectoral_left", flip_fin)]
    print("CLEARANCE pectoral fin to body, sculling: %.1f mm" % clearance(pectoral, e0.cross(e1), lambda r: 0.03 * (0.65 * r + 0.7 * r * r)))
    return made


GAME_BODY_RINGS = 26
GAME_HALF = 7


def make(name, low, game=False):
    """`game`: the game model (built on the low model's simpler parts, `low` True, with the counts GAME sets)."""
    global GAME
    GAME = game
    parts = []
    body = Part("body")
    skin(body, BODY_SKIN, body_places(low), GAME_HALF if game else (9 if low else 30), BODY)
    parts.append(body)
    jaw = Part("jaw")
    jaw_rings = 8 if game else (14 if low else 44)
    skin(jaw, JAW_SKIN, [lerp(JAW_SKIN.first, JAW_SKIN.last, (i / jaw_rings) ** 1.25) for i in range(jaw_rings + 1)],
         4 if game else (5 if low else 14), JAW)
    parts.append(jaw)
    plate = maxilla(low)
    parts += [plate, plate.mirrored("maxilla_left", flip_body)]
    ball = eye(low)
    parts += [ball, ball.mirrored("eye_left", lambda d: d)]
    parts += fins(low)

    verts, faces, corners = [], [], []
    told = []
    wrong_all = 0
    for part in parts:
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
    # (every layer made first, then each looked up by name: making one moves the others)
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
    material = bpy.data.materials.get("trout") or bpy.data.materials.new("trout")
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.62, 0.62, 0.52, 1.0)
    material.diffuse_color = (0.62, 0.62, 0.52, 1.0)
    mesh.materials.append(material)
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.update()
    # (every face was made with corners of its own; the same point with the same data is one point again)
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
    print("BUILT %s verts=%d tris=%d" % (name, len(mesh.vertices), tris))
    print("WINDING %s: %s: %s" % (name, "ok" if wrong_all == 0 else "INSIDE OUT", ", ".join(told)))
    GAME = False
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
    views = [("right", (1, 0, 0), (0, 0, 0), 0.46), ("left", (-1, 0, 0), (0, 0, 0), 0.46),
             ("top", (0, -0.001, 1), (0, 0, 0), 0.46), ("under", (0, 0.001, -1), (0, 0, 0), 0.46),
             ("front", (0, 1, 0), (0, 0, 0), 0.24), ("back", (0, -1, 0), (0, 0, 0), 0.24),
             ("quarter", (0.7, 0.6, 0.35), (0, 0, 0), 0.44), ("low_quarter", (0.6, 0.6, -0.5), (0, 0, 0), 0.44),
             ("head", (1, 0.15, 0.05), (0, 0.15, 0), 0.16), ("head_under", (0.5, 0.5, -0.7), (0, 0.15, -0.01), 0.16),
             ("tail", (1, -0.2, 0.1), (0, -0.15, 0), 0.2)]
    for low, obj in ((False, made[0]), (True, made[1])):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if low and view not in ("right", "quarter"):
                continue
            offset = Vector(direction).normalized() * 10.0
            camera.data.ortho_scale = frame
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "X" if view in ("top", "under") else "Y").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % ("lo_" if low else "", view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    full = make("cutthroat_trout", False)
    low = make("cutthroat_trout_lo", True)
    game = make("cutthroat_trout_game", True, True)
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, "cutthroat_trout.glb"))
    export_one(low, os.path.join(OUT, "cutthroat_trout_lo.glb"))
    export_one(game, os.path.join(OUT, "cutthroat_trout_game.glb"))
    low.location.x = 0.4
    game.location.x = 0.8
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "cutthroat_trout.blend"))
    low.location.x = 0.0
    game.location.x = 0.0
    game.hide_render = True
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low])


if __name__ == "__main__":
    main()
