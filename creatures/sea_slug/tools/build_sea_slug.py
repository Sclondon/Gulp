"""Builds the sea slugs (creatures/sea_slug) and exports them for Godot.

Run from the game's root:
    blender --background --factory-startup --python creatures/sea_slug/tools/build_sea_slug.py
    blender --background --factory-startup --python creatures/sea_slug/tools/build_sea_slug.py -- <preview folder>

Three kinds, each in three models (the full model for close pictures, the game model at Twilight Princess weight,
the low model for far off), all wearing one shader (sea_slug.gdshader), which colours them and does all of their
moving:

    models/sea_hare.glb        sea_hare_game.glb        sea_hare_lo.glb
    models/blue_dragon.glb     blue_dragon_game.glb     blue_dragon_lo.glb
    models/spanish_dancer.glb  spanish_dancer_game.glb  spanish_dancer_lo.glb

and the editable tools/sea_slug.blend with all nine. Every model is one still mesh with one surface. The game and
low models are built from the same outlines and curves as the full one, with fewer, better placed rings (the
body's rings are placed where its outline bends most). It prints a WINDING line per model (every face against the
way out it was built to face, and every part's faces tested by rays for an odd number of crossings: none may be
inside out) and a SIZE line.

The animals (built from what the species look like; no picture was traced):

- THE SEA HARE (Aplysia californica), 0.30 m: a plump soft body, highest over its middle, a head on a narrower neck,
  a tapering tail; two ear-like rolled rhinophores on the head and two broad rolled oral tentacles at its front
  corners; two thick wing flaps (parapodia) rising from its sides and folded up over its back, nearly meeting.
- THE BLUE DRAGON (Glaucus atlanticus), 0.035 m: a slender tapering body with a long tail, three pairs of short arms
  each ending in a fan of finger-like cerata spread out flat, tiny head tentacles. It floats UPSIDE DOWN at the
  surface: it is built with its foot facing up, at the waterline (y = 0), and the rest hanging below it.
- THE SPANISH DANCER (Hexabranchus sanguineus), 0.30 m: a broad flattened oval body, a wide frilled mantle skirt
  all round it, two club rhinophores at the front, a rosette of six branched gills on its back near the rear. The
  skirt is built flat; the shader drapes it, frills it and ripples it.

Everything here is in Godot space (metres, Y up, X its left side, its head at -Z) until it is written out. The
origin is on the ground under its middle (the blue dragon's: at the waterline over its middle). `xm` is metres
behind the front of the head.

What a point is, for the shader:
- UV2.y the part: 0 body, 1 a flap (the sea hare's parapodia, the dancer's skirt), 2 a rhinophore, 3 an oral
  tentacle, 4 a ceras (the blue dragon's fingers and the stalks that carry them), 5 a gill (the dancer's).
- UV, on the body: x how far along (0 head to 1 tail), y how high (0 the foot to 1 the top of the back); on a sea
  hare's flap: x how far along (0 its front to 1 its back), y from its root (0) to its edge (1); on the dancer's
  skirt: x round it (0 at the head, through its left side at 0.25, to 1), y from its root (0) to its edge (1); on
  anything else: x from its root (0) to its tip (1).
- UV2.x, on anything but the body, a number of its own (0..1) so that no two wave quite together; on the dancer's
  skirt, how far the point stands above (+) or below (-) the skirt's middle sheet, in mm.
- COLOR, on the sea hare's flaps: r and g the flap's root (where it hinges) at that point, |x| and y in tenths of
  a metre, b 1 for the flap on its left side (+X), 0 for the right.
(The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.)
"""

import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "models")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = ARGS[0] if ARGS else ""
TAU = math.tau
BODY, FLAP, RHINOPHORE, ORAL, CERAS, GILL = range(6)
LEVELS = ("full", "game", "lo")


def to_b(p):
    return Vector((p.x, -p.z, p.y))


# ---------------------------------------------------------------------------------------------- the mesh

class Mesh:
    """Points with their data and a way out (a rough normal, used to wind every face the right way and to check it)."""

    def __init__(self):
        self.verts = []
        self.data = []
        self.hint = []
        self.faces = []
        self.outs = []
        self.names = []
        self.count = {}

    def add(self, p, uv, part, own=0.0, out=(0.0, 1.0, 0.0), col=(0.0, 0.0, 0.0)):
        self.verts.append(Vector(p))
        self.data.append(((uv[0], 1.0 - uv[1]), (own, 1.0 - part), col))
        self.hint.append(Vector(out))
        return len(self.verts) - 1

    def face(self, points, name, out=None):
        """A face wound so that its front is towards `out` (or its corners' ways out)."""
        ps = [self.verts[i] for i in points]
        n = Vector((0.0, 0.0, 0.0))
        for i in range(len(ps)):
            n += ps[i].cross(ps[(i + 1) % len(ps)])
        if n.length < 1e-14:
            return
        if out is None:
            out = sum((self.hint[i] for i in points), Vector())
        if n.dot(out) < 0.0:
            points = tuple(reversed(points))
        self.faces.append(tuple(points))
        self.outs.append(Vector(out))
        self.names.append(name)
        self.count[name] = self.count.get(name, 0) + 1

    def rows(self, rows, name, wrap):
        """Quads between each row of points and the next (each row closed round if `wrap`)."""
        for r in range(len(rows) - 1):
            a, b = rows[r], rows[r + 1]
            n = len(a) if wrap else len(a) - 1
            for c in range(n):
                k = (c + 1) % len(a)
                self.face((a[c], a[k], b[k], b[c]), name)

    def fan(self, centre, row, name, wrap=True):
        n = len(row) if wrap else len(row) - 1
        for c in range(n):
            self.face((centre, row[c], row[(c + 1) % len(row)]), name)


def adaptive(f, a, b, tol, n_min, n_max):
    """Places to sample f (a function of one number giving a tuple) between a and b, more where it bends: the
    span whose middle is furthest from the straight line between its ends is halved, until none is further than
    `tol` or there are n_max spans."""
    xs = [a + (b - a) * i / n_min for i in range(n_min + 1)]

    def err(x0, x1):
        m = 0.5 * (x0 + x1)
        f0, f1, fm = f(x0), f(x1), f(m)
        return max(abs(fm[i] - 0.5 * (f0[i] + f1[i])) for i in range(len(fm)))

    while len(xs) - 1 < n_max:
        worst = max(range(len(xs) - 1), key=lambda i: err(xs[i], xs[i + 1]))
        if err(xs[worst], xs[worst + 1]) < tol:
            break
        xs.insert(worst + 1, 0.5 * (xs[worst] + xs[worst + 1]))
    return xs


def _slopes(xs, ys):
    """Tangents for a curve through the points that never overshoots them (Fritsch and Carlson)."""
    d = [(ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]) for i in range(len(xs) - 1)]
    m = [d[0]]
    for i in range(1, len(xs) - 1):
        if d[i - 1] * d[i] <= 0.0:
            m.append(0.0)
        else:
            w1 = 2.0 * (xs[i + 1] - xs[i]) + (xs[i] - xs[i - 1])
            w2 = (xs[i + 1] - xs[i]) + 2.0 * (xs[i] - xs[i - 1])
            m.append((w1 + w2) / (w1 / d[i - 1] + w2 / d[i]))
    m.append(d[-1])
    return m


class Outline:
    """A body's outline from a table of (metres behind the front, half width, height)."""

    def __init__(self, table):
        self.xs = [p[0] for p in table]
        self.curves = []
        for column in (1, 2):
            ys = [p[column] for p in table]
            self.curves.append((ys, _slopes(self.xs, ys)))

    def __call__(self, xm):
        xs = self.xs
        xm = max(xs[0], min(xs[-1], xm))
        i = 0
        while i < len(xs) - 2 and xm > xs[i + 1]:
            i += 1
        h = xs[i + 1] - xs[i]
        t = (xm - xs[i]) / h
        out = []
        for ys, m in self.curves:
            a = (2 * t ** 3 - 3 * t ** 2 + 1) * ys[i] + (t ** 3 - 2 * t ** 2 + t) * h * m[i]
            b = (-2 * t ** 3 + 3 * t ** 2) * ys[i + 1] + (t ** 3 - t ** 2) * h * m[i + 1]
            out.append(max(a + b, 0.00005))
        return out


def section_point(wide, high, angle, flat=0.72):
    """A point of a slug's cross-section: `angle` round from the top of the back (0) by its left side to the middle
    of the foot (half a turn). The foot is flat on the ground; `flat` says how much of the underside is foot."""
    c = math.cos(angle)
    s = math.sin(angle)
    y = high * max(0.0, min(1.0, (c + flat) / (1.0 + flat)))
    return math.copysign(abs(s) ** 0.85, s) * wide, y


def slug_body(m, outline, length, half, around, xs, flat=0.72):
    """The body: rings round the outline at `xs` (metres behind the front), closed by a point at each end."""
    grid = []
    for xm in xs:
        wide, high = outline(xm)
        row = []
        for c in range(around):
            x, y = section_point(wide, high, c / around * TAU, flat)
            p = Vector((x, y, xm - half))
            row.append(m.add(p, (xm / length, y / high), BODY, 0.0, (x / wide, (y - 0.4 * high) / high, 0.0)))
        grid.append(row)
    m.rows(grid, "body", True)
    for row, xm, way in ((grid[0], xs[0], -1.0), (grid[-1], xs[-1], 1.0)):
        high = outline(xm)[1]
        tip = m.add(Vector((0.0, 0.4 * high, xm - half + way * 0.0002 * length / 0.07)), (xm / length, 0.4), BODY, 0.0, (0.0, 0.0, way))
        m.fan(tip, row, "body")


def finger(m, part, name, curve, radius, sides, segs, own, flat=1.0, roll=None):
    """A stalk round `curve(t)` (t 0 at its root to 1 at its tip), `radius(t)` thick (`flat` times as thick one way
    as the other), closed by a point at its tip and a cap at its root (which is sunk in what carries it)."""
    first = (curve(0.02) - curve(0.0)).normalized()
    ref = Vector((1.0, 0.0, 0.0)) if roll is None else Vector(roll)
    if abs(first.dot(ref.normalized())) > 0.8:
        ref = Vector((0.0, 0.0, 1.0))
    rows = []
    for i in range(segs + 1):
        t = 0.97 * i / segs
        here = curve(t)
        along = (curve(min(t + 0.02, 1.0)) - curve(max(t - 0.02, 0.0))).normalized()
        a = along.cross(ref).normalized()
        b = along.cross(a).normalized()
        # (a stalk of few sides is drawn a little thicker, so that its outline is as wide as a round one's)
        r = radius(t) * 2.0 / (1.0 + math.cos(math.pi / sides))
        row = []
        for k in range(sides):
            turn = k / sides * TAU
            out = a * math.cos(turn) * flat + b * math.sin(turn)
            way = a * math.cos(turn) / flat + b * math.sin(turn)
            row.append(m.add(here + out * r, (t, k / sides), part, own, way))
        rows.append((here, row, along))
    m.rows([r[1] for r in rows], name, True)
    end = curve(1.0)
    tip = m.add(end, (1.0, 0.0), part, own, end - rows[-1][0])
    m.fan(tip, rows[-1][1], name)
    if sides <= 4:
        # (a thin stalk's root, sunk out of sight, closed by one flat face)
        m.face(tuple(rows[0][1]), name, -rows[0][2])
    else:
        root = m.add(rows[0][0], (0.0, 0.0), part, own, -rows[0][2])
        m.fan(root, rows[0][1], name)


def bent(p0, p1, p2):
    def curve(t):
        a = 1.0 - t
        return p0 * (a * a) + p1 * (2.0 * a * t) + p2 * (t * t)
    return curve


# ---------------------------------------------------------------------------------------------- the sea hare

HARE_LENGTH = 0.30
HARE_HALF = 0.15
HARE = Outline([
    (0.0008, 0.0090, 0.0110),
    (0.004, 0.0170, 0.0210),
    (0.012, 0.0215, 0.0295),
    (0.024, 0.0225, 0.0340),
    (0.040, 0.0200, 0.0340),
    (0.060, 0.0265, 0.0440),
    (0.090, 0.0400, 0.0620),
    (0.130, 0.0500, 0.0780),
    (0.170, 0.0530, 0.0840),
    (0.205, 0.0480, 0.0760),
    (0.240, 0.0360, 0.0540),
    (0.265, 0.0220, 0.0320),
    (0.285, 0.0100, 0.0140),
    (0.2985, 0.0020, 0.0025),
])
FLAP_FROM, FLAP_TO = 0.072, 0.262
FLAP_ROOT = 1.62


def hare_flap_height(xm):
    """How far up over the back the flap reaches at `xm` (0 none, 1 to the top)."""
    t = (xm - FLAP_FROM) / (FLAP_TO - FLAP_FROM)
    return max(0.0, math.sin(math.pi * t)) ** 0.55


def hare_flaps(m, q):
    along = {"full": 72, "game": 13, "lo": 6}[q]
    out_n = {"full": 14, "game": 4, "lo": 2}[q]
    edge_n = {"full": 6, "game": 2, "lo": 2}[q]
    in_n = out_n
    for sx in (1.0, -1.0):
        sections = []
        for i in range(along + 1):
            # (bunched towards the ends, where the flap's edge comes down fastest)
            t = 0.5 - 0.5 * math.cos(math.pi * i / along)
            xm = FLAP_FROM + 0.004 + (FLAP_TO - FLAP_FROM - 0.008) * t
            wide, high = HARE(xm)
            centre = Vector((0.0, 0.42 * high, xm - HARE_HALF))
            reach = 0.08 + 0.92 * hare_flap_height(xm)
            a_edge = FLAP_ROOT - (FLAP_ROOT - 0.1) * reach
            env = hare_flap_height(xm)

            def sheet(r):
                a = FLAP_ROOT + (a_edge - FLAP_ROOT) * r
                x, y = section_point(wide, high, sx * a)
                p = Vector((x, y, xm - HARE_HALF))
                way = Vector((p.x - centre.x, p.y - centre.y, 0.0)).normalized()
                gap = -0.0065 + 0.0175 * max(r, 0.0) ** 0.75
                return p + way * gap, way

            def mid(r):
                """A point of the flap's middle sheet, and the way square to the sheet, out from the body."""
                p, way = sheet(r)
                d = sheet(min(r + 0.01, 1.0))[0] - sheet(max(r - 0.01, 0.0))[0]
                n = Vector((d.y, -d.x, 0.0)).normalized()
                return p, (n if n.dot(way) > 0.0 else -n)

            thick = 0.0025 + 0.0055 * env
            root, _ = mid(0.0)
            col = (abs(root.x) * 10.0, root.y * 10.0, 1.0 if sx > 0 else 0.0)
            loop = []
            # the outer face, root to edge
            for k in range(out_n + 1):
                r = k / out_n
                c, way = mid(r)
                th = thick * (1.0 - 0.55 * r)
                loop.append((c + way * th * 0.5, r, way))
            # round the edge
            c1, way1 = mid(1.0)
            c0, _ = mid(0.97)
            on = (c1 - c0).normalized()
            th = thick * 0.45
            for k in range(1, edge_n + 1):
                a = math.pi * k / (edge_n + 1)
                loop.append((c1 + way1 * th * 0.5 * math.cos(a) + on * th * 0.5 * math.sin(a), 1.0, way1 * math.cos(a) + on * math.sin(a)))
            # the inner face, edge to root
            for k in range(in_n, -1, -1):
                r = k / in_n
                c, way = mid(r)
                th = thick * (1.0 - 0.55 * r)
                loop.append((c - way * th * 0.5, r, -way))
            # (the wall at the root faces back down the flap, away from its edge)
            back = (mid(0.0)[0] - mid(0.05)[0]).normalized()
            loop[0] = (loop[0][0], loop[0][1], loop[0][2] + back * 1.5)
            loop[-1] = (loop[-1][0], loop[-1][1], loop[-1][2] + back * 1.5)
            row = [m.add(p, ((xm - FLAP_FROM) / (FLAP_TO - FLAP_FROM), r), FLAP, 0.0, w, col) for p, r, w in loop]
            sections.append((row, xm, root, col))
        m.rows([s[0] for s in sections], "flaps", True)
        # Each end closed across the flap's thickness: the outer face's points joined to the inner face's at
        # the same distance from the root, and the rounded edge as one face (a fan from a middle point would
        # cross itself, the flap being curved).
        n = out_n
        for row, way in ((sections[0][0], -1.0), (sections[-1][0], 1.0)):
            out = Vector((0.0, 0.0, way))
            last = len(row) - 1
            for k in range(n):
                m.face((row[k], row[k + 1], row[last - 1 - k], row[last - k]), "flaps", out)
            m.face(tuple(row[n:last - n + 1]), "flaps", out)


def hare_head(m, q):
    rng = random.Random(5)
    sides = {"full": 14, "game": 6, "lo": 4}[q]
    segs = {"full": 18, "game": 5, "lo": 2}[q]
    for sx in (1.0, -1.0):
        # A rhinophore: an ear, rolled, rising up, out and back from the top of the head.
        xm = 0.03
        root = Vector((sx * 0.0085, HARE(xm)[1] - 0.004, xm - HARE_HALF))
        tip = root + Vector((sx * 0.013, 0.03, 0.014))
        mid = root + Vector((sx * 0.003, 0.018, 0.0))
        finger(m, RHINOPHORE, "rhinophores", bent(root, mid, tip),
               lambda t: 0.0055 * (1.0 + 0.45 * math.sin(math.pi * min(t / 0.55, 1.0))) * (1.0 - 0.5 * t ** 2.5),
               sides, segs, rng.random(), flat=0.42, roll=(0.0, 0.0, 1.0))
        # An oral tentacle: broad, rolled, from the front corner of the head forward, out and down.
        root = Vector((sx * 0.012, 0.012, 0.006 - HARE_HALF))
        tip = root + Vector((sx * 0.024, -0.007, -0.016))
        mid = root + Vector((sx * 0.006, 0.002, -0.012))
        finger(m, ORAL, "oral tentacles", bent(root, mid, tip),
               lambda t: 0.0062 * (1.0 + 0.45 * math.sin(math.pi * min(t / 0.55, 1.0))) * (1.0 - 0.5 * t ** 2.5),
               sides, segs, rng.random(), flat=0.38, roll=(0.0, 1.0, 0.0))


def make_hare(q):
    m = Mesh()
    if q == "full":
        xs = [0.0008 + (0.2985 - 0.0008) * i / 124 for i in range(125)]
        around = 48
    else:
        xs = adaptive(lambda x: HARE(x), 0.0008, 0.2985, 0.0007 if q == "game" else 0.003, 6, 20 if q == "game" else 9)
        around = 16 if q == "game" else 8
    slug_body(m, HARE, HARE_LENGTH, HARE_HALF, around, xs)
    hare_flaps(m, q)
    hare_head(m, q)
    return m


# ---------------------------------------------------------------------------------------------- the blue dragon

DRAGON_LENGTH = 0.035
DRAGON_HALF = 0.0175
DRAGON = Outline([
    (0.0003, 0.0007, 0.0007),
    (0.0015, 0.0014, 0.0014),
    (0.0035, 0.0019, 0.0018),
    (0.0070, 0.0022, 0.0021),
    (0.0110, 0.0024, 0.0022),
    (0.0150, 0.0023, 0.0021),
    (0.0195, 0.0019, 0.0017),
    (0.0240, 0.0013, 0.0012),
    (0.0290, 0.0007, 0.0007),
    (0.0347, 0.00012, 0.00012),
])
# The arms: metres behind the front, how far the fan stands out from the side, how many fingers, how long.
ARMS = [(0.0085, 0.0028, 10, 0.0052), (0.0140, 0.0024, 8, 0.0046), (0.0185, 0.0020, 6, 0.0038)]


def flip(p):
    """Upside down (turned half round its own length): its foot up at the waterline, its back below."""
    return Vector((-p.x, -p.y, p.z))


def make_dragon(q):
    m = Mesh()
    if q == "full":
        xs = [0.0003 + (0.0347 - 0.0003) * i / 70 for i in range(71)]
        around = 32
    else:
        xs = adaptive(lambda x: DRAGON(x), 0.0003, 0.0347, 0.00008 if q == "game" else 0.0003, 5, 14 if q == "game" else 7)
        around = 10 if q == "game" else 6
    slug_body(m, DRAGON, DRAGON_LENGTH, DRAGON_HALF, around, xs, flat=0.5)
    rng = random.Random(3)
    sides = {"full": 8, "game": 3, "lo": 3}[q]
    segs = {"full": 8, "game": 1, "lo": 1}[q]
    stalk_sides = {"full": 8, "game": 4, "lo": 3}[q]
    for sx in (1.0, -1.0):
        for n, (xm, out, fingers, reach) in enumerate(ARMS):
            wide, high = DRAGON(xm)
            root = Vector((sx * wide * 0.5, high * 0.55, xm - DRAGON_HALF))
            hub = Vector((sx * (wide + out), high * 0.5, xm - DRAGON_HALF + 0.0004))
            finger(m, CERAS, "arms", bent(root, (root + hub) * 0.5 + Vector((0.0, 0.0002, 0.0)), hub),
                   lambda t: 0.00055 * (1.0 - 0.25 * t), stalk_sides, {"full": 6, "game": 1, "lo": 1}[q], rng.random())
            if q == "lo":
                fingers = max(3, fingers // 2)
            for k in range(fingers):
                # spread out flat in a fan, from forward and out to back and out
                a = math.radians(-58.0 + 116.0 * (k + 0.5) / fingers) + rng.uniform(-0.06, 0.06)
                way = Vector((sx * math.cos(a), -0.12, math.sin(a)))
                length = reach * (0.75 + 0.25 * math.cos(1.2 * (a))) * rng.uniform(0.9, 1.1)
                p0 = hub - way * 0.0003
                p1 = hub + way * length * 0.5 + Vector((0.0, 0.0002, 0.0))
                p2 = hub + way * length + Vector((0.0, -0.0004, 0.0))
                thick = 0.00042 * rng.uniform(0.9, 1.1)
                finger(m, CERAS, "cerata", bent(p0, p1, p2),
                       lambda t, thick=thick: thick * (1.0 + 0.2 * math.sin(math.pi * min(t / 0.5, 1.0))) * (1.0 - 0.6 * t ** 2),
                       sides, segs, rng.random())
        # tiny head tentacles: a rhinophore and an oral tentacle each side
        for part, name, root, tip, r in (
                (RHINOPHORE, "rhinophores", Vector((sx * 0.0006, 0.0014, 0.0016 - DRAGON_HALF)), Vector((sx * 0.0012, 0.0024, 0.0008 - DRAGON_HALF)), 0.00022),
                (ORAL, "oral tentacles", Vector((sx * 0.0005, 0.0006, 0.0006 - DRAGON_HALF)), Vector((sx * 0.0014, 0.0004, -0.0006 - DRAGON_HALF)), 0.0002)):
            finger(m, part, name, bent(root, (root + tip) * 0.5, tip), lambda t, r=r: r * (1.0 - 0.6 * t),
                   {"full": 6, "game": 3, "lo": 3}[q], {"full": 4, "game": 1, "lo": 1}[q], rng.random())
    m.verts = [flip(p) for p in m.verts]
    m.hint = [flip(h) for h in m.hint]
    m.outs = [flip(o) for o in m.outs]
    return m


# ---------------------------------------------------------------------------------------------- the Spanish dancer

DANCER_LENGTH = 0.30
DANCER_HALF = 0.15
DANCER = Outline([
    (0.004, 0.012, 0.012),
    (0.012, 0.026, 0.022),
    (0.028, 0.036, 0.030),
    (0.060, 0.044, 0.035),
    (0.110, 0.047, 0.037),
    (0.160, 0.047, 0.037),
    (0.210, 0.044, 0.034),
    (0.250, 0.035, 0.028),
    (0.276, 0.022, 0.020),
    (0.292, 0.010, 0.012),
    (0.298, 0.002, 0.003),
])
# The skirt's root, round the body (kept in step with the shader's SKIRT_*): an ellipse of half width SKIRT_W and
# half length SKIRT_L about the middle, at height SKIRT_Y; how far the skirt reaches out from it at the sides
# (SKIRT_SIDE) and at the ends (SKIRT_END).
SKIRT_W, SKIRT_L, SKIRT_Y = 0.040, 0.118, 0.014
SKIRT_SIDE, SKIRT_END = 0.050, 0.014


def skirt_root(theta):
    return Vector((SKIRT_W * math.sin(theta), SKIRT_Y, -SKIRT_L * math.cos(theta)))


def skirt_out(theta):
    """The way out from the root, flat, square to the root's ellipse."""
    return Vector((math.sin(theta) / SKIRT_W, 0.0, -math.cos(theta) / SKIRT_L)).normalized()


def skirt_reach(theta):
    s = math.sin(theta) ** 2
    return SKIRT_END + (SKIRT_SIDE - SKIRT_END) * s ** 0.7


def dancer_skirt(m, q):
    # (the game model's points round it fall on the tops and the troughs of the shader's 16 frills; across it,
    # more on the upper face, which curls)
    around = {"full": 288, "game": 64, "lo": 32}[q]
    tops = {"full": [k / 10 for k in range(11)], "game": [0.0, 0.4, 0.75, 1.0], "lo": [0.0, 0.6, 1.0]}[q]
    bottoms = {"full": [k / 10 for k in range(11)], "game": [0.0, 0.5, 1.0], "lo": [0.0, 1.0]}[q]
    edge_n = {"full": 4, "game": 1, "lo": 1}[q]
    sections = []
    for i in range(around + 1):
        u = i / around
        theta = u * TAU
        root = skirt_root(theta)
        out = skirt_out(theta)
        reach = skirt_reach(theta)
        loop = []
        # the upper face from root to edge, round the edge, the lower face back, and a wall at the root

        def thick(r):
            return 0.005 * (1.0 - 0.6 * r)

        for r in tops:
            loop.append((root + out * reach * r + Vector((0.0, thick(r) * 0.5, 0.0)), r, Vector((0.0, 1.0, 0.0))))
        th = thick(1.0)
        for k in range(1, edge_n + 1):
            a = math.pi * k / (edge_n + 1)
            loop.append((root + out * (reach + th * 0.5 * math.sin(a)) + Vector((0.0, th * 0.5 * math.cos(a), 0.0)), 1.0, out * math.sin(a) + Vector((0.0, math.cos(a), 0.0))))
        for r in reversed(bottoms):
            loop.append((root + out * reach * r - Vector((0.0, thick(r) * 0.5, 0.0)), r, Vector((0.0, -1.0, 0.0))))
        row = []
        for j, (p, r, w) in enumerate(loop):
            if j == len(loop) - 1 or j == 0:
                # (the root's points lean in towards the body, so the wall between them faces in)
                w = w + (-out) * 1.5
            row.append(m.add(p, (u, r), FLAP, (p.y - SKIRT_Y) * 1000.0, w))
        sections.append(row)
    # the root wall: the last point of each loop joins the first
    m.rows(sections, "skirt", True)


def dancer_head(m, q):
    rng = random.Random(9)
    sides = {"full": 10, "game": 5, "lo": 4}[q]
    for sx in (1.0, -1.0):
        xm = 0.03
        root = Vector((sx * 0.012, DANCER(xm)[1] - 0.003, xm - DANCER_HALF))
        way = Vector((sx * 0.25, 1.0, -0.3)).normalized()
        length = 0.022

        def ring(t, full=q == "full"):
            leaves = 0.45 * max(0.0, math.sin(TAU * 7.0 * t)) * min(1.0, max(0.0, (t - 0.3) / 0.1)) if full else 0.0
            return 0.003 * (1.0 - 0.5 * t) * (1.0 + leaves)

        finger(m, RHINOPHORE, "rhinophores", bent(root, root + way * length * 0.5, root + way * length), ring,
               sides, {"full": 36, "game": 4, "lo": 2}[q], rng.random())


def dancer_gills(m, q):
    """Six branched gills in a ring on its back near the rear, splayed out and up."""
    rng = random.Random(13)
    xm = 0.215
    centre = Vector((0.0, DANCER(xm)[1] - 0.002, xm - DANCER_HALF))
    main_sides = {"full": 8, "game": 4, "lo": 3}[q]
    main_segs = {"full": 10, "game": 2, "lo": 1}[q]
    branches = {"full": 4, "game": 2, "lo": 0}[q]
    for k in range(6):
        a = TAU * (k + 0.5) / 6
        out = Vector((math.sin(a), 0.0, math.cos(a)))
        root = centre + out * 0.006
        tip = root + out * 0.022 + Vector((0.0, 0.016, 0.0))
        p1 = root + out * 0.006 + Vector((0.0, 0.014, 0.0))
        curve = bent(root, p1, tip)
        own = rng.random()
        finger(m, GILL, "gills", curve, lambda t: 0.0026 * (1.0 - 0.6 * t), main_sides, main_segs, own)
        side = out.cross(Vector((0.0, 1.0, 0.0))).normalized()
        for b in range(branches):
            t = (0.35, 0.65)[b // 2] if branches > 2 else 0.5
            s = 1.0 if b % 2 == 0 else -1.0
            at = curve(t)
            bw = (side * s + out * 0.6 + Vector((0.0, 0.5, 0.0))).normalized()
            blen = 0.010 * (1.0 - 0.4 * t)
            finger(m, GILL, "gills", bent(at, at + bw * blen * 0.5, at + bw * blen + Vector((0.0, 0.003, 0.0))),
                   lambda tt: 0.0014 * (1.0 - 0.6 * tt), max(3, main_sides - 2), max(1, main_segs // 2), own)


def make_dancer(q):
    m = Mesh()
    if q == "full":
        xs = [0.004 + (0.298 - 0.004) * i / 100 for i in range(101)]
        around = 40
    else:
        xs = adaptive(lambda x: DANCER(x), 0.004, 0.298, 0.0008 if q == "game" else 0.004, 6, 16 if q == "game" else 8)
        around = 12 if q == "game" else 8
    slug_body(m, DANCER, DANCER_LENGTH, DANCER_HALF, around, xs, flat=0.6)
    dancer_skirt(m, q)
    dancer_head(m, q)
    dancer_gills(m, q)
    return m


# ---------------------------------------------------------------------------------------------- writing it out

def to_object(name, m):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) for p in m.verts], [], m.faces)
    # (every layer made first, then each looked up by name: making one moves the others)
    mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.new(name="UV2")
    mesh.color_attributes.new(name="Color", type="FLOAT_COLOR", domain="CORNER")
    uv = mesh.uv_layers["UVMap"].data
    uv2 = mesh.uv_layers["UV2"].data
    colour = mesh.color_attributes["Color"].data
    for poly in mesh.polygons:
        for corner, vi in enumerate(poly.vertices):
            d = m.data[vi]
            uv[poly.loop_start + corner].uv = d[0]
            uv2[poly.loop_start + corner].uv = d[1]
            colour[poly.loop_start + corner].color = (d[2][0], d[2][1], d[2][2], 1.0)
    mesh.color_attributes.active_color = mesh.color_attributes["Color"]
    mesh.color_attributes.render_color_index = mesh.color_attributes.find("Color")
    material = bpy.data.materials.get("sea_slug") or bpy.data.materials.new("sea_slug")
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.6, 0.35, 0.25, 1.0)
    material.diffuse_color = (0.6, 0.35, 0.25, 1.0)
    mesh.materials.append(material)
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    lo = Vector((min(p.x for p in m.verts), min(p.y for p in m.verts), min(p.z for p in m.verts)))
    hi = Vector((max(p.x for p in m.verts), max(p.y for p in m.verts), max(p.z for p in m.verts)))
    print("BUILT %s verts=%d tris=%d" % (name, len(mesh.vertices), tris))
    print("SIZE %s: x %.4f..%.4f y %.4f..%.4f z %.4f..%.4f" % (name, lo.x, hi.x, lo.y, hi.y, lo.z, hi.z))
    winding(name, mesh, m)
    return obj, tris


def winding(name, mesh, m):
    """Nothing inside out: every face against the way out it was built to face; and each part's faces, by rays:
    a line out of a face, the way it faces, must cross that part's skin an even number of times."""
    bad = {}
    for poly in mesh.polygons:
        out = m.outs[poly.index]
        if poly.normal.dot(to_b(out)) <= 0.0:
            group = m.names[poly.index]
            bad[group] = bad.get(group, 0) + 1
            if bad[group] <= 3 and os.environ.get("SLUG_DEBUG"):
                print("  wrong %s at %s" % (group, [tuple(round(c, 4) for c in m.verts[i]) for i in m.faces[poly.index]]))
    # (each piece, a set of faces joined by their points, is a closed skin of its own: tested by itself)
    parent = list(range(len(m.verts)))

    def root_of(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for f in m.faces:
        for i in f[1:]:
            a, b = root_of(f[0]), root_of(i)
            if a != b:
                parent[a] = b
    pieces = {}
    for fi, f in enumerate(m.faces):
        pieces.setdefault((m.names[fi], root_of(f[0])), []).append(fi)
    odd = {}
    for (group, _), members in pieces.items():
        bm = bmesh.new()
        made = {}
        for fi in members:
            f = m.faces[fi]
            vs = []
            for i in f:
                if i not in made:
                    made[i] = bm.verts.new(to_b(m.verts[i]))
                vs.append(made[i])
            try:
                bm.faces.new(vs)
            except ValueError:
                pass
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bm.normal_update()
        tree = BVHTree.FromBMesh(bm)
        wrong = 0
        for f in bm.faces:
            if f.calc_area() < 1e-13:
                continue
            nudge = 1e-7
            at = f.calc_center_median() + f.normal * nudge
            hits = 0
            while hits < 40:
                hit = tree.ray_cast(at, f.normal)
                if hit[0] is None:
                    break
                hits += 1
                at = hit[0] + f.normal * nudge
            if hits % 2:
                wrong += 1
                if wrong <= 4 and os.environ.get("SLUG_DEBUG"):
                    c0 = f.calc_center_median()
                    print("  odd %s at %.4f %.4f %.4f facing %s hits %d" % (group, c0.x, c0.z, -c0.y, tuple(round(x, 2) for x in f.normal), hits))
        bm.free()
        odd[group] = odd.get(group, 0) + wrong
    told = ["%s %d/%d wrong, %d odd" % (g, bad.get(g, 0), c, odd.get(g, 0)) for g, c in m.count.items()]
    ok = not bad and all(odd[g] <= m.count[g] * 0.01 for g in odd)
    print("WINDING %s: %s: %s" % (name, "ok" if ok else "INSIDE OUT", ", ".join(told)))


def export_one(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", export_yup=True, use_selection=True,
        export_animations=False, export_vertex_color="ACTIVE", export_texcoords=True,
    )


def render(folder, objects):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_cavity = True
    scene.display.shading.show_backface_culling = True
    scene.render.resolution_x, scene.render.resolution_y = 1000, 600
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    for name, obj, size in objects:
        for other in bpy.data.objects:
            if other.type == "MESH":
                other.hide_render = other is not obj
        at = obj.location
        for view, direction, frame in (("left", (1, 0, 0), 1.15), ("top", (0.001, 0, 1), 1.15),
                                       ("front", (0, 1, 0), 0.8), ("quarter", (0.8, 0.9, 0.6), 1.0)):
            offset = Vector(direction).normalized() * 40.0 * size
            camera.data.ortho_scale = frame * size
            camera.location = at + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s_%s.png" % (name, view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    os.makedirs(OUT, exist_ok=True)
    made = []
    kinds = (("sea_hare", make_hare, HARE_LENGTH), ("blue_dragon", make_dragon, DRAGON_LENGTH),
             ("spanish_dancer", make_dancer, DANCER_LENGTH))
    for row, (kind, maker, length) in enumerate(kinds):
        for col, q in enumerate(LEVELS):
            name = kind + {"full": "", "game": "_game", "lo": "_lo"}[q]
            obj, tris = to_object(name, maker(q))
            export_one(obj, os.path.join(OUT, name + ".glb"))
            made.append((name, obj, length))
    # (laid out in the .blend side by side, each kind in a row)
    for i, (name, obj, length) in enumerate(made):
        obj.location = Vector(((i % 3) * 0.4, (i // 3) * 0.4, 0.0))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "sea_slug.blend"))
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, made)


if __name__ == "__main__":
    main()
