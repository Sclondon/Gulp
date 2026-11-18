"""Builds the goldfish (creatures/goldfish) and exports it for Godot.

(Added 2026-11-18: it also writes the GAME model, models/..._game.glb, a third model of the same curves with
far fewer points put where the outline bends (`Fish.GAME_*`, `spaced`, each fin's counts through `Fish.n`), into the
same .blend; and all three models now have a throat behind the mouth (`Fish.throat`) and four gill arches a side
in it (`Fish.gills`, part 10, GILL: UV.x 0 the rakers' side, about 0.35 the bar, 1 the filaments; UV.y the arch's
number plus how far along it, 0 low to 1 high). It prints an EYE line and a GILLS line: the numbers the shader's
cartoon eye and gills are given. See the component's README.)

Run from the game's root:
    blender --background --python creatures/goldfish/tools/build_goldfish.py
    blender --background --python creatures/goldfish/tools/build_goldfish.py -- <preview folder>   # with pictures

Writes creatures/goldfish/models/goldfish_common.glb and goldfish_fantail.glb (the full models), each with a _lo
(far off, phones, many at once), and the editable tools/goldfish_common.blend and goldfish_fantail.blend (this
folder has a .gdignore). Each is one still mesh with one surface: the shader (goldfish.gdshader) draws every
marking and swims it. It prints a WINDING line for each (the check that nothing is inside out) and a NUMBERS
line (the numbers the shader is given for that kind: goldfish.gd's KINDS has them).

Two kinds of goldfish (Carassius auratus), both 0.15 m from the tip of the snout to the tips of the tail, built
from what the fish look like (no picture was traced or copied):

- THE COMMON GOLDFISH: the wild shape kept: a torpedo a little flattened from side to side, deepest (0.043 m) a
  third of the way back, a rounded snout with a small end-on mouth, a big eye; one long-based dorsal fin highest
  at its front, a single forked tail, one small anal fin, paired pectoral and pelvic fins.
- THE FANTAIL: an egg-shaped body (0.055 m deep, 0.039 wide) only 0.09 m long, and a long double tail: two
  forked tails side by side, joined along the top and spread apart below like an upturned V seen from behind;
  paired anal fins spread the same way; one dorsal fin.

Each has a LOWER JAW of its own that swings down about its hinge (the shader's `gape`), and the inside of the
mouth (roof, floor, throat), as GameCommon's sardine has. Shut, the two lie lip to lip.

Everything here is in Godot space (metres, Y up, X to its left side, its nose at -Z) until it is written out;
the origin is on its middle line, half way along (0.075 m behind the tip of the snout). `xm` below is metres
behind the tip of the snout.

What a point is, for the shader: UV2.y the part (0 body, 1 the dorsal fin, 2 an anal fin, 3 a tail, 4 a
pectoral fin, 5 a pelvic fin, 6 an eye, 7 the lower jaw). UV2.x: 1 inside the mouth, 0 elsewhere. UV, on the
body and the jaw: x how far along (0 snout to 1 tail tips), y how high on its side (1 the ridge of the back, 0
the keel of the belly); on a fin: x from its root (0) to its edge (1), y from its leading edge (0) to its
trailing edge (1); on an eye: x from its middle (0) to its rim (1). (The glTF writer flips V: what is written
here is 1 - v, so that Godot reads v.)
"""

import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "models")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = ARGS[0] if ARGS else ""

LENGTH = 0.15
HALF = 0.075
BODY, DORSAL, ANAL, TAIL, PECTORAL, PELVIC, EYE, JAW = range(8)
# (10: the gill arches, added 2026-11-18; 8 and 9 are some kinds' barbels and adipose fin)
GILL = 10
# (10: the gill arches, added 2026-11-18; 8 and 9 are some kinds' barbels and adipose fin)
GILL = 10
# (10: the gill arches, added 2026-11-18; 8 and 9 are some kinds' barbels and adipose fin)
GILL = 10
# (10: the gill arches, added 2026-11-18; 8 and 9 are some kinds' barbels and adipose fin)
GILL = 10
# (10: the gill arches, added 2026-11-18; 8 and 9 are some kinds' barbels and adipose fin)
GILL = 10
TAU = math.tau
SIDE = Vector((1.0, 0.0, 0.0))


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def to_b(p):
    return Vector((p.x, -p.z, p.y))


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


class Curves:
    """Smooth curves through rows of (x, a, b, ...): `at(x)` is [a, b, ...] there."""

    def __init__(self, rows):
        self.xs = [r[0] for r in rows]
        self.curves = []
        for column in range(1, len(rows[0])):
            ys = [r[column] for r in rows]
            self.curves.append((ys, _slopes(self.xs, ys)))

    def at(self, x):
        xs = self.xs
        x = max(xs[0], min(xs[-1], x))
        i = 0
        while i < len(xs) - 2 and x > xs[i + 1]:
            i += 1
        h = xs[i + 1] - xs[i]
        t = (x - xs[i]) / h
        out = []
        for ys, m in self.curves:
            a = (2 * t ** 3 - 3 * t ** 2 + 1) * ys[i] + (t ** 3 - 2 * t ** 2 + t) * h * m[i]
            b = (-2 * t ** 3 + 3 * t ** 2) * ys[i + 1] + (t ** 3 - t ** 2) * h * m[i + 1]
            out.append(a + b)
        return out


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.data = []
        self.out = []
        self.count = {}

    def add(self, p, uv, part, inside=0.0):
        self.verts.append(p)
        self.data.append(((uv[0], 1.0 - uv[1]), (inside, 1.0 - part)))
        return len(self.verts) - 1

    def face(self, points, out, name):
        """A face wound so that its front (the side its points go round anticlockwise) is towards `out`."""
        ps = [self.verts[i] for i in points]
        n = Vector((0.0, 0.0, 0.0))
        for i in range(len(ps)):
            n += ps[i].cross(ps[(i + 1) % len(ps)])
        if n.length < 1e-14:
            return
        if n.dot(out) < 0.0:
            points = tuple(reversed(points))
        if len(points) == 4:
            # (a quad that is not flat is cut into two triangles along the diagonal that leaves both facing
            # the way it should: Godot draws triangles, and the wrong cut of a twisted quad turns one over)
            a, b, c, d = points
            v = self.verts

            def facing(p, q, r):
                return (v[q] - v[p]).cross(v[r] - v[p]).dot(out)

            if min(facing(a, b, c), facing(a, c, d)) < min(facing(a, b, d), facing(b, c, d)):
                tris = ((a, b, d), (b, c, d))
            else:
                tris = ((a, b, c), (a, c, d))
            for tri in tris:
                self.faces.append(tri)
                self.out.append((Vector(out), name))
            self.count[name] = self.count.get(name, 0) + 2
            return
        self.faces.append(tuple(points))
        self.out.append((Vector(out), name))
        self.count[name] = self.count.get(name, 0) + 1


def blade(m, part, name, point, place, facing, thick, nt, nu):
    """A fin: a thin closed blade. `point(t, u)` is a place in the fin's own flat (t 0 at its root to 1 at its
    edge, u 0 at its leading edge to 1 at its trailing edge), `place` puts that in the model, `facing` is
    roughly the way one of its two skins faces (each point's own way is worked out from its neighbours, so a
    fin may be curved). It is `thick` at its root, a foil across (nothing at either edge), thinning to nothing
    at its edge."""
    def at(t, u):
        return place(point(t, u))

    def way(t, u):
        e = 0.002
        a = at(min(t + e, 1.0), u) - at(max(t - e, 0.0), u)
        b = at(t, min(u + e, 1.0)) - at(t, max(u - e, 0.0))
        n = a.cross(b)
        if n.length < 1e-14:
            return Vector(facing)
        n.normalize()
        return n if n.dot(facing) >= 0.0 else -n

    for side in (1.0, -1.0):
        grid = []
        for ti in range(nt + 1):
            t = ti / nt
            row = []
            for ui in range(nu + 1):
                u = ui / nu
                foil = 2.6 * math.sqrt(u) * (1.0 - u)
                swell = thick * (1.0 - t) ** 0.7 * foil
                row.append(m.add(at(t, u) + way(t, u) * (side * swell * 0.5), (t, u), part))
            grid.append(row)
        for ti in range(nt):
            for ui in range(nu):
                out = way((ti + 0.5) / nt, (ui + 0.5) / nu) * side
                m.face((grid[ti][ui], grid[ti][ui + 1], grid[ti + 1][ui + 1], grid[ti + 1][ui]), out, name)


def between(root, edge):
    """A fin drawn from its root line to its edge (each a function of u, 0 to 1, giving (xm, y))."""
    def point(t, u):
        a = root(u)
        b = edge(u)
        return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
    return point


def through(points):
    """A smooth line through (u, xm, y) points (u rising): a function of u giving (xm, y)."""
    curve = Curves(points)
    return lambda u: tuple(curve.at(u))


def upright(p):
    """A place in the flat of the middle fins (metres behind the snout, metres up) in the model."""
    return Vector((0.0, p[1], p[0] - HALF))


def spread(sx, pivot, angle, gap):
    """A place in the flat of a middle fin turned out to one side (`sx`) about a line along the body at height
    `pivot` (a number, or a function of xm), by `angle` (a number, or a function of what the caller passes:
    t, or xm): what is below the line
    swings out, what is above it stays upright, `gap` to that side of the middle."""
    def place_at(p, t):
        y0 = pivot(p[0]) if callable(pivot) else pivot
        a = angle(t) if callable(angle) else angle
        # (how far below the line, eased in over a few millimetres so that the fin bends round smoothly)
        x = y0 - p[1]
        d = x * x / (x + 0.003) if x > 0.0 else 0.0
        return Vector((sx * (gap + math.sin(a) * d), p[1] + d * (1.0 - math.cos(a)), p[0] - HALF))
    return place_at


def spaced(first, last, count, ring_at, floor=0.6):
    """For the game model: count + 1 places from `first` to `last` along the fish, close together where the skin
    bends most along its length (the snout, the forehead, the wrist of the tail) and further apart along the
    flanks. `ring_at(xm)` gives points round the skin at xm. A straight line between places misses a curve by
    about its bend times the gap squared, so the places are spaced by the square root of the bend, plus `floor`
    of the mean so that no stretch is left bare (the swimming bend needs rings all the way). (As GameCommon's
    clown loach does it.)"""
    n = 360
    h = (last - first) / n
    ss = [first + h * i for i in range(n + 1)]
    made = [ring_at(s) for s in ss]
    dens = []
    for i in range(n + 1):
        a, b, c = made[max(i - 1, 0)], made[i], made[min(i + 1, n)]
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
        i = next((j for j in range(n) if acc[j + 1] >= want), n - 1)
        t = (want - acc[i]) / max(acc[i + 1] - acc[i], 1e-12)
        places.append(ss[i] + (ss[i + 1] - ss[i]) * t)
    places[0], places[-1] = first, last
    return places


def bar(m, part, name, frames, outline, uvs):
    """A closed bar along a line: `frames` (place, inward, back, along) at each step of it, `outline` its
    section as (d, dz) points (d towards `inward`, dz towards `back`; one list for every step, or one list per
    step), `uvs(i, j)` the UV of step i's point j. Each side is a strip of its own points (so that it shades
    as one face across, as a blade's sides do) and each end is closed by a fan."""
    steps = len(frames)
    rings = [outline[i] if isinstance(outline[0], list) else outline for i in range(steps)]
    n = len(rings[0])
    # (its section's points go round anticlockwise as (d, dz): each side's outward way is the edge turned)
    area = sum(rings[0][j][0] * rings[0][(j + 1) % n][1] - rings[0][(j + 1) % n][0] * rings[0][j][1] for j in range(n))
    order = list(range(n)) if area > 0.0 else list(reversed(range(n)))

    def place(i, j):
        o, inward, back, _ = frames[i]
        d, dz = rings[i][j]
        return o + inward * d + back * dz

    for e in range(n):
        j, k = order[e], order[(e + 1) % n]
        column = [(m.add(place(i, j), uvs(i, j), part, 1.0), m.add(place(i, k), uvs(i, k), part, 1.0)) for i in range(steps)]
        for i in range(steps - 1):
            ed = rings[i][k][0] - rings[i][j][0]
            ez = rings[i][k][1] - rings[i][j][1]
            _, inward, back, _ = frames[i]
            out = inward * ez - back * ed
            m.face((column[i][0], column[i][1], column[i + 1][1], column[i + 1][0]), out, name)
    for i, way in ((0, -1.0), (steps - 1, 1.0)):
        loop = [m.add(place(i, j), uvs(i, j), part, 1.0) for j in order]
        middle = sum((m.verts[q] for q in loop), Vector()) / len(loop)
        tip = m.add(middle, uvs(i, order[0]), part, 1.0)
        for e in range(n):
            m.face((tip, loop[e], loop[(e + 1) % n]), frames[i][3] * way, name)


class Fish:
    """One model's shape. A kind sets PROFILE (xm, half depth above, half depth below, half width), BODY_TO,
    JAW_TO (the jaw's hinge), EYE_AT, EYE_RADIUS, RINGS, mouth_y, gill_x and fins.

    Three models of each: the full one, the low one (`low`) and the GAME model (`game`, added 2026-11-18: the same
    curves and parts with far fewer points, put where the outline bends: GAME_RINGS rings along the body behind
    the hinge and GAME_HEAD ahead of it, spaced by `spaced`; GAME_AROUND points round each ring; an eye of
    GAME_EYE (spokes, rows); each fin's counts given by the kind's `fins` through `n`)."""

    LOW_STEP = 4.0
    GAME_RINGS = 20
    GAME_HEAD = 3
    GAME_AROUND = 16
    GAME_EYE = (24, 2)
    GAME_JAW = 6
    GAME_THROAT = 3
    GAME_GILL = 3
    GAME_GILL_SIDES = 4
    # The throat and the gills (added 2026-11-18): the throat behind the hinge is GILL_WIDE of the body's half
    # width wide, GILL_HIGH of its half depth above its middle line high and GILL_DEEP below; its middle line
    # GILL_DROP of the body's half depth below below the body's. The game model's throat has GAME_THROAT rings
    # behind the hinge and each of its arches GAME_GILL steps, a bar of GAME_GILL_SIDES sides (4 or 3).
    GILL_WIDE = 0.55
    GILL_HIGH = 0.45
    GILL_DEEP = 0.42
    GILL_DROP = 0.28

    def __init__(self, low, game=False):
        self.low = low and not game
        self.game = game
        self.outline_curves = Curves(self.PROFILE)

    def n(self, full, low, game):
        """A count: the full model's, the low model's or the game model's."""
        return game if self.game else (low if self.low else full)

    def outline(self, xm):
        return [max(v, 0.0013 * LENGTH) for v in self.outline_curves.at(xm)]

    def mid(self, xm):
        return 0.0

    def section(self, xm, angle, up, down, wide):
        c = math.cos(angle)
        s = math.sin(angle)
        y = c * (up if c >= 0.0 else down)
        side = math.copysign(abs(s) ** 0.9, s) * wide
        return side, y

    def body_point(self, xm, angle):
        up, down, wide = self.outline(xm)
        side, y = self.section(xm, angle, up, down, wide)
        return Vector((side, self.mid(xm) + y, xm - HALF))

    def top(self, xm):
        return self.body_point(xm, 0.0).y

    def bottom(self, xm):
        return self.body_point(xm, math.pi).y

    def angle_at(self, xm, y):
        lo, hi = 0.0, math.pi
        for _ in range(40):
            half = 0.5 * (lo + hi)
            if self.body_point(xm, half).y > y:
                lo = half
            else:
                hi = half
        return 0.5 * (lo + hi)

    def skin(self, xm, y, sx):
        return self.body_point(xm, sx * self.angle_at(xm, y))

    def lip_angle(self, xm):
        return self.angle_at(xm, self.mouth_y(xm))

    def rings(self):
        if self.game:
            def ring_at(xm):
                return [self.body_point(xm, c / 16 * TAU) for c in range(16)]
            head = spaced(self.BODY_FROM, self.JAW_TO, self.GAME_HEAD, ring_at)[:-1]
            return head + spaced(self.JAW_TO, self.BODY_TO, self.GAME_RINGS, ring_at)
        xs = []
        x = self.BODY_FROM
        for until, step in self.RINGS:
            if self.low:
                step *= self.LOW_STEP
            n = max(1, round((until - x) / step))
            for i in range(n):
                xs.append(x + (until - x) * i / n)
            x = until
        xs.append(self.BODY_TO)
        return xs

    def around(self):
        return self.GAME_AROUND if self.game else (self.AROUND_LOW if self.low else self.AROUND)

    def jaw_across(self):
        return self.n(10, 4, self.GAME_JAW)

    def inside_point(self, xm, across, roof):
        """A point of the roof or the floor of the mouth at `xm`: `across` 1 at the left lip, -1 at the right,
        the surface arched away from the line of the mouth between them."""
        lip = self.body_point(xm, self.lip_angle(xm))
        up, down, _ = self.outline(xm)
        if roof:
            depth = 0.45 * (self.mid(xm) + up - lip.y)
        else:
            depth = -0.5 * (lip.y - (self.mid(xm) - down))
        y = lip.y + depth * (1.0 - across * across) * smooth(0.1 * self.JAW_TO, 0.5 * self.JAW_TO, xm)
        return Vector((lip.x * across, y, xm - HALF))

    # --- the body and the head above the mouth -----------------------------------------------------------

    def body(self, m):
        around = self.around()
        xs = self.rings()
        head = [xm for xm in xs if xm < self.JAW_TO - 1e-9]
        xs = xs[len(head):]
        grid = []
        for xm in xs:
            row = []
            for c in range(around):
                angle = c / around * TAU
                row.append(m.add(self.body_point(xm, angle), (xm / LENGTH, 0.5 + 0.5 * math.cos(angle)), BODY))
            grid.append(row)
        for r in range(len(grid) - 1):
            for c in range(around):
                n = (c + 1) % around
                quad = (grid[r][c], grid[r][n], grid[r + 1][n], grid[r + 1][c])
                middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
                m.face(quad, Vector((middle.x, middle.y - self.mid(middle.z + HALF), 0.0)), "body")
        end = self.BODY_TO + 0.0027 * LENGTH
        tip = m.add(Vector((0.0, self.mid(end), end - HALF)), (end / LENGTH, 0.5), BODY)
        for c in range(around):
            m.face((tip, grid[-1][c], grid[-1][(c + 1) % around]), Vector((0.0, 0.0, 1.0)), "body")
        half = round(self.lip_angle(self.JAW_TO) / (TAU / around))
        across = around - 2 * half
        uppers = []
        roofs = []
        for xm in head:
            reach = self.lip_angle(xm)
            uppers.append([m.add(self.body_point(xm, j / half * reach), (xm / LENGTH, 0.5 + 0.5 * math.cos(j / half * reach)), BODY)
                           for j in range(-half, half + 1)])
            roofs.append([m.add(self.inside_point(xm, 1.0 - 2.0 * k / across, True), (xm / LENGTH, 0.5), BODY,
                                smooth(self.BODY_FROM, 0.12 * self.JAW_TO, xm))
                          for k in range(across + 1)])
        first = grid[0]
        uppers.append([first[j % around] for j in range(-half, half + 1)])
        # (the roof of the mouth goes on back past the hinge as the roof of the throat: a short tunnel back to
        # the gills, `throat`; until 2026-11-18 the mouth ended at the hinge in a dark wall down to the belly)
        roofs.append(self.throat(m, across))
        for r in range(len(head)):
            centre = self.mouth_y(head[r]) - 0.1 * self.outline(head[r])[0]
            for j in range(2 * half):
                quad = (uppers[r][j], uppers[r][j + 1], uppers[r + 1][j + 1], uppers[r + 1][j])
                middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
                m.face(quad, Vector((middle.x, middle.y - centre, 0.0)), "body")
            for k in range(across):
                quad = (roofs[r][k], roofs[r][k + 1], roofs[r + 1][k + 1], roofs[r + 1][k])
                m.face(quad, Vector((0.0, -1.0, 0.0)), "mouth roof")
        loop = uppers[0] + roofs[0][1:-1]
        middle = sum((m.verts[q] for q in loop), Vector()) / len(loop)
        tip = m.add(middle + Vector((0.0, 0.0, -0.002 * LENGTH)), (0.0, 0.5), BODY)
        for i in range(len(loop)):
            m.face((tip, loop[i], loop[(i + 1) % len(loop)]), Vector((0.0, 0.0, -1.0)), "body")

    # --- the throat and the gills (added 2026-11-18) -------------------------------------------------------

    def gill_span(self):
        """Where the first and the last of the four gill arches stand (metres behind the snout, at the throat's
        middle line), the gap between two, and where the throat ends behind them."""
        j, g = self.JAW_TO, self.GILL_AT
        first = j + 0.42 * (g - j)
        last = g - 0.06 * (g - j)
        return first, last, (last - first) / 3.0, g + 0.15 * (g - j)

    def throat_shape(self, xm):
        """The throat behind the hinge at xm: (half width, the height of its middle line, height above it,
        depth below it), narrowing to its end behind the gills."""
        up, down, wide = self.outline(xm)
        _, last, _, end = self.gill_span()
        narrow = 1.0 - 0.45 * smooth(last, end, xm)
        return (self.GILL_WIDE * wide * narrow, self.mid(xm) - self.GILL_DROP * down,
                self.GILL_HIGH * up * narrow, self.GILL_DEEP * down * narrow)

    def throat_point(self, xm, a, roof):
        """A point of the throat's roof or floor at xm (`a` 1 at its left side, -1 at its right): at the hinge
        the mouth's own roof and floor, which meet at the corners of the mouth, rounding out behind it into an
        oval about a line low in the head."""
        j = self.JAW_TO
        end = self.gill_span()[3]
        b = smooth(j, j + 0.3 * (end - j), xm)
        front = self.inside_point(j, a, roof)
        front.z = xm - HALF
        w, cy, hu, hd = self.throat_shape(xm)
        back = Vector((w * math.sin(0.5 * math.pi * a), cy + (hu if roof else -hd) * math.cos(0.5 * math.pi * a), xm - HALF))
        return front.lerp(back, b)

    def throat_wall(self, xm, angle, sx):
        """A point of the throat's wall behind the hinge (its oval): `angle` 0 at the middle of its roof, a half
        turn at the middle of its floor, on the `sx` side."""
        w, cy, hu, hd = self.throat_shape(xm)
        c = math.cos(angle)
        return Vector((sx * w * math.sin(angle), cy + (hu if c >= 0.0 else hd) * c, xm - HALF))

    def throat(self, m, across):
        """The throat: the roof of the mouth and the floor of the jaw carried on behind the hinge as a short
        tunnel (its walls dark, `inside` 1, of the body's part) back past the gill arches to an end. Returns the
        roof's points at the hinge (for the roof of the mouth ahead of it to join)."""
        floor_across = self.jaw_across()
        end = self.gill_span()[3]
        steps = self.n(10, 2, self.GAME_THROAT)
        xs = [self.JAW_TO + (end - self.JAW_TO) * i / steps for i in range(steps + 1)]
        rings = []
        for i, xm in enumerate(xs):
            u = (xm / LENGTH, 0.5)
            roof = [m.add(self.throat_point(xm, 1.0 - 2.0 * k / across, True), u, BODY, 1.0) for k in range(across + 1)]
            floor = [m.add(self.throat_point(xm, 1.0 - 2.0 * k / floor_across, False), u, BODY, 1.0)
                     for k in range(floor_across - 1, 0, -1)]
            rings.append(roof + floor)
        count = len(rings[0])
        for i in range(steps):
            for c in range(count):
                quad = (rings[i][c], rings[i][(c + 1) % count], rings[i + 1][(c + 1) % count], rings[i + 1][c])
                middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
                axis = sum((m.verts[q] for q in rings[i] + rings[i + 1]), Vector()) / (2 * count)
                m.face(quad, Vector((axis.x - middle.x, axis.y - middle.y, 0.0)), "throat")
        middle = sum((m.verts[q] for q in rings[-1]), Vector()) / count
        tip = m.add(middle, (end / LENGTH, 0.5), BODY, 1.0)
        for c in range(count):
            m.face((tip, rings[-1][c], rings[-1][(c + 1) % count]), Vector((0.0, 0.0, -1.0)), "throat")
        return rings[0][:across + 1]

    def gills(self, m):
        """Four gill arches a side in the throat, each a closed bar of the GILL part: a curved bar (blood red)
        from low in the throat round its side and up under its roof, its top leaning back, a fringe of
        filaments behind it out to the throat's wall (deep red) and pale gill rakers on its front. UV.x: 0 the
        rakers' side, about 0.35 the bar, 1 the filaments; UV.y: the arch's number (0 the front one) plus how far
        along it (0 its lower end to 1 its upper end). The full model's has a toothed fringe and the rakers as
        spikes; the game model's is a bar of four sides, the low model's of three."""
        first, _, gap, _ = self.gill_span()
        steps = self.n(16, 2, self.GAME_GILL)
        rb = 0.16 * gap
        bar_d = 0.38 * gap
        for sx in (1.0, -1.0):
            for k in range(4):
                xa = first + gap * k
                frames = []
                for i in range(steps + 1):
                    t = i / steps
                    angle = math.pi * (0.22 + 0.68 * (1.0 - t))
                    xm = xa + 0.25 * gap * math.cos(angle)
                    wall = self.throat_wall(xm, angle, sx)
                    _, cy, _, _ = self.throat_shape(xm)
                    inward = Vector((-wall.x, cy - wall.y, 0.0)).normalized()
                    ahead = self.throat_wall(xm, angle - 0.01, sx) - self.throat_wall(xm, angle + 0.01, sx)
                    frames.append((wall, inward, Vector((0.0, 0.0, 1.0)), ahead.normalized()))
                if self.game and self.GAME_GILL_SIDES == 4:
                    outline = [(bar_d + rb, -0.4 * rb), (bar_d + 0.3 * rb, rb), (0.08 * gap, 0.62 * gap), (0.08 * gap, -0.12 * gap)]
                    pieces = (0.0, 0.35, 1.0, 0.85)
                elif self.low or self.game:
                    outline = [(bar_d + rb, 0.0), (0.08 * gap, 0.62 * gap), (0.08 * gap, -0.12 * gap)]
                    pieces = (0.0, 1.0, 0.85)
                else:
                    outline = []
                    for i in range(steps + 1):
                        # (the fringe's back edge toothed: its filaments in bunches)
                        tip = 0.62 * gap if i % 2 == 0 else 0.44 * gap
                        ring = [(0.08 * gap, -0.12 * gap)]
                        for a in (-120.0, -60.0, 0.0, 60.0, 120.0):
                            r = math.radians(a)
                            ring.append((bar_d + rb * math.cos(r), rb * math.sin(r)))
                        ring.append((0.08 * gap, tip))
                        outline.append(ring)
                    pieces = (0.85, 0.35, 0.15, 0.0, 0.15, 0.35, 1.0)
                bar(m, GILL, "gills", frames, outline, lambda i, j: (pieces[j], k + i / steps))
                if not self.game and not self.low:
                    self.rakers(m, frames, bar_d, rb, k, steps)

    def rakers(self, m, frames, bar_d, rb, k, steps):
        """The full model's gill rakers: short pale spikes along the front of an arch, pointing in and forward."""
        count = 12
        for r in range(count):
            t = (r + 0.5) / count
            i = min(int(t * steps), steps - 1)
            f = t * steps - i
            o = frames[i][0].lerp(frames[i + 1][0], f)
            inward = frames[i][1].lerp(frames[i + 1][1], f).normalized()
            back = Vector((0.0, 0.0, 1.0))
            along = frames[i][3].lerp(frames[i + 1][3], f).normalized()
            a = math.radians(-35.0)
            root = o + inward * (bar_d + rb * math.cos(a)) + back * (rb * math.sin(a))
            size = rb * 0.4
            base = [root + along * size, root - along * size * 0.5 + back * size * 0.8, root - along * size * 0.5 - back * size * 0.8]
            apex = root + inward * (rb * 1.2) - back * (rb * 0.5)
            pts = [m.add(p, (0.0, k + t), GILL, 1.0) for p in base]
            tip = m.add(apex, (0.0, k + t), GILL, 1.0)
            centre = (base[0] + base[1] + base[2] + apex) * 0.25
            for p, q, s in ((pts[0], pts[1], pts[2]), (pts[0], pts[1], tip), (pts[1], pts[2], tip), (pts[2], pts[0], tip)):
                middle = (m.verts[p] + m.verts[q] + m.verts[s]) / 3.0
                m.face((p, q, s), middle - centre, "gill rakers")

    def jaw(self, m):
        """The lower jaw: the body's own skin below the line of the mouth, ahead of the hinge, closed over by
        the floor of the mouth, with an end inside the head."""
        around = self.around()
        half = round(self.lip_angle(self.JAW_TO) / (TAU / around))
        under = around - 2 * half
        across = self.jaw_across()
        xs = [xm for xm in self.rings() if xm < self.JAW_TO + 1e-9]
        skins = []
        floors = []
        for xm in xs:
            reach = self.lip_angle(xm)
            row = []
            for i in range(under + 1):
                angle = reach + (TAU - 2.0 * reach) * i / under
                if xm > self.JAW_TO - 1e-9:
                    angle = (half + i) / around * TAU
                row.append(m.add(self.body_point(xm, angle), (xm / LENGTH, 0.5 + 0.5 * math.cos(angle)), JAW))
            skins.append(row)
            floors.append([m.add(self.inside_point(xm, 1.0 - 2.0 * k / across, False), (xm / LENGTH, 0.5), JAW,
                                 smooth(self.BODY_FROM, 0.12 * self.JAW_TO, xm))
                           for k in range(across + 1)])
        for r in range(len(xs) - 1):
            centre = 0.5 * (self.mouth_y(xs[r]) + self.bottom(xs[r]))
            for i in range(under):
                quad = (skins[r][i], skins[r][i + 1], skins[r + 1][i + 1], skins[r + 1][i])
                middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
                m.face(quad, Vector((middle.x, middle.y - centre, 0.0)), "jaw")
            for k in range(across):
                m.face((floors[r][k], floors[r][k + 1], floors[r + 1][k + 1], floors[r + 1][k]), Vector((0.0, 1.0, 0.0)), "mouth floor")
        for r, way, inside in ((0, -1.0, 0.0), (len(xs) - 1, 1.0, 1.0)):
            loop = skins[r] + floors[r][-2:0:-1]
            if r > 0:
                loop = [m.add(m.verts[q], (xs[r] / LENGTH, 0.5), JAW, 1.0) for q in loop]
            middle = sum((m.verts[q] for q in loop), Vector()) / len(loop)
            z = xs[r] - HALF + (-0.0013 * LENGTH if r == 0 else 0.0)
            tip = m.add(Vector((0.0, middle.y, z)), (xs[r] / LENGTH, 0.5), JAW, inside)
            for i in range(len(loop)):
                m.face((tip, loop[i], loop[(i + 1) % len(loop)]), Vector((0.0, 0.0, way)), "jaw" if r == 0 else "jaw end")

    def eye(self, m, sx):
        """A low dome lying on the skin of the head."""
        spokes, steps = self.GAME_EYE if self.game else ((8, 1) if self.low else (22, 5))
        xe, ye = self.EYE_AT
        rad = self.EYE_RADIUS
        e = rad * 0.12
        here = self.skin(xe, ye, sx)
        out = (self.skin(xe + e, ye, sx) - self.skin(xe - e, ye, sx)).cross(self.skin(xe, ye + e, sx) - self.skin(xe, ye - e, sx))
        out.normalize()
        if out.x * sx < 0.0:
            out = -out
        if sx > 0.0:
            # (for the shader's cartoon eye: the middle of the left eye on the skin and the way it faces)
            self.eye_middle = (here, out)
        bulge = rad * self.EYE_BULGE
        middle = m.add(here + out * bulge, (0.0, 0.0), EYE)
        last = None
        for k in range(1, steps + 1):
            r = k / steps
            row = []
            for s in range(spokes):
                a = s / spokes * TAU
                p = self.skin(xe + math.cos(a) * rad * r, ye + math.sin(a) * rad * r, sx)
                row.append(m.add(p + out * (bulge * (1.0 - r * r) + 0.02 * rad * (1.0 - r)), (r, 0.0), EYE))
            for s in range(spokes):
                n = (s + 1) % spokes
                if last is None:
                    m.face((middle, row[s], row[n]), out, "eyes")
                else:
                    m.face((last[s], row[s], row[n], last[n]), out, "eyes")
            last = row

    def paired(self, m, part, name, sx, root, span, chord, length, width, thick, nt, nu, shape):
        """A paired fin from `root`, reaching `length` along `span`, `width` along `chord` (shape(t) 0..1)."""
        span = Vector((sx * span[0], span[1], span[2])).normalized()
        chord = Vector((sx * chord[0], chord[1], chord[2])).normalized()
        facing = span.cross(chord).normalized()
        if facing.x * sx < 0.0:
            facing = -facing

        def point(t, u):
            t *= 0.975
            return (length * t, width * shape(t) * u + 0.002 * LENGTH * u)

        blade(m, part, name, point, lambda p: root + span * p[0] + chord * p[1], facing, thick, nt, nu)

    def extras(self, m):
        """Anything else a kind has (barbels...): none here."""

    def make(self, name):
        m = Mesh()
        self.body(m)
        self.jaw(m)
        self.gills(m)
        for sx in (1.0, -1.0):
            self.eye(m, sx)
        self.fins(m)
        self.extras(m)
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
        mesh.materials.append(material_of(self.NAME, self.COLOUR))
        for poly in mesh.polygons:
            poly.use_smooth = True
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
        print("BUILT %s verts=%d tris=%d" % (name, len(mesh.vertices), tris))
        winding(name, mesh, m)
        if not self.low and not self.game:
            here, out = self.eye_middle
            print("EYE %s: middle=(%.5f, %.5f, %.5f) out=(%.4f, %.4f, %.4f) at=(%.4f, %.4f) radius=%.4f" % (
                name, here.x, here.y, here.z, out.x, out.y, out.z, self.EYE_AT[0], self.EYE_AT[1], self.EYE_RADIUS))
            first, last, gap, end = self.gill_span()
            print("GILLS %s: first=%.4f last=%.4f gap=%.5f throat_end=%.4f" % (name, first, last, gap, end))
        return obj, m


# --- the two kinds ---------------------------------------------------------------------------------------

class Common(Fish):
    NAME = "goldfish_common"
    COLOUR = (0.9, 0.35, 0.05, 1.0)
    PROFILE = [
        (0.0, 0.0, 0.0, 0.0),
        (0.0006, 0.0026, 0.0024, 0.0022),
        (0.0025, 0.0052, 0.0048, 0.0043),
        (0.006, 0.0085, 0.0078, 0.0066),
        (0.011, 0.0122, 0.0110, 0.0086),
        (0.018, 0.0163, 0.0148, 0.0103),
        (0.027, 0.0200, 0.0186, 0.0115),
        (0.038, 0.0226, 0.0218, 0.0120),
        (0.050, 0.0232, 0.0232, 0.0119),
        (0.062, 0.0218, 0.0224, 0.0111),
        (0.073, 0.0190, 0.0196, 0.0097),
        (0.084, 0.0148, 0.0153, 0.0077),
        (0.095, 0.0112, 0.0113, 0.0057),
        (0.103, 0.0088, 0.0088, 0.0044),
        (0.109, 0.0076, 0.0076, 0.0034),
        (0.113, 0.0066, 0.0066, 0.0021),
        (0.116, 0.0012, 0.0012, 0.0006),
    ]
    BODY_FROM = 0.0006
    BODY_TO = 0.116
    JAW_TO = 0.0095
    JOINT = 0.108
    EYE_AT = (0.0175, 0.0042)
    EYE_RADIUS = 0.0043
    EYE_BULGE = 0.24
    GILL_AT = 0.029
    AROUND = 32
    AROUND_LOW = 10
    RINGS = ((0.0095, 0.0009), (0.03, 0.0016), (0.1, 0.0026), (0.116, 0.0016))

    def mouth_y(self, xm):
        # a small end-on mouth, its line running a little down and back to the corner under the nostril
        return -0.0004 - 0.12 * xm

    def fins(self, m):
        # The dorsal fin: long-based, highest at its front, its rays leaning back, its edge a little rounded.
        def dorsal_root(u):
            xm = 0.041 + 0.050 * u
            return (xm, self.top(xm) - 0.0009)

        def dorsal_edge(u):
            xm = 0.041 + 0.050 * u
            h = 0.0145 * (0.25 + 0.75 * (1.0 - u) ** 1.1) * (0.45 + 0.55 * smooth(0.0, 0.16, u))
            return (xm + 0.42 * h, self.top(xm) - 0.0009 + h)

        blade(m, DORSAL, "dorsal", between(dorsal_root, dorsal_edge), upright, SIDE, 0.0011, self.n(9, 3, 2), self.n(12, 4, 6))
        # The anal fin: small, far back, leaning back.
        def anal_root(u):
            xm = 0.087 + 0.012 * u
            return (xm, self.bottom(xm) + 0.0008)

        def anal_edge(u):
            xm = 0.087 + 0.012 * u
            h = 0.0095 * (0.3 + 0.7 * (1.0 - u) ** 1.2) * (0.6 + 0.4 * smooth(0.0, 0.15, u))
            return (xm + 0.6 * h, self.bottom(xm) + 0.0008 - h)

        blade(m, ANAL, "anal", between(anal_root, anal_edge), upright, SIDE, 0.0009, self.n(6, 2, 1), self.n(8, 2, 3))
        # The tail: one, forked, two rounded-pointed lobes and a shallow notch.
        tail_root = lambda u: (0.1045, 0.0072 * (1.0 - 2.0 * u))
        tail_edge = through([
            (0.0, 0.111, 0.0098), (0.1, 0.133, 0.0158), (0.2, 0.149, 0.0188), (0.3, 0.146, 0.0120),
            (0.4, 0.137, 0.0050), (0.5, 0.1325, 0.0), (0.6, 0.137, -0.0050), (0.7, 0.146, -0.0120),
            (0.8, 0.149, -0.0188), (0.9, 0.133, -0.0158), (1.0, 0.111, -0.0098)])
        blade(m, TAIL, "tail", between(tail_root, tail_edge), upright, SIDE, 0.0012, self.n(10, 3, 2), self.n(18, 6, 10))
        for sx in (1.0, -1.0):
            root = self.skin(0.0305, -0.0118, sx)
            root.x -= sx * 0.0006
            self.paired(m, PECTORAL, "pectorals", sx, root, (0.38, -0.3, 0.87), (0.06, -0.88, 0.45),
                        0.0175, 0.0085, 0.0008, self.n(8, 2, 3), self.n(6, 3, 2),
                        lambda t: (0.45 + 0.55 * smooth(0.0, 0.35, t)) * (1.0 - t) ** 0.5)
            root = Vector((sx * 0.0035, self.bottom(0.056) + 0.0012, 0.056 - HALF))
            self.paired(m, PELVIC, "pelvics", sx, root, (0.3, -0.55, 0.78), (0.0, 0.14, 1.0),
                        0.0125, 0.0058, 0.0007, self.n(6, 2, 2), self.n(4, 2, 2),
                        lambda t: (1.0 - t) ** 0.7)


class Fantail(Fish):
    NAME = "goldfish_fantail"
    COLOUR = (0.9, 0.35, 0.05, 1.0)
    PROFILE = [
        (0.0, 0.0, 0.0, 0.0),
        (0.0006, 0.0032, 0.0029, 0.0028),
        (0.0025, 0.0062, 0.0056, 0.0053),
        (0.0065, 0.0104, 0.0094, 0.0087),
        (0.011, 0.0142, 0.0134, 0.0115),
        (0.016, 0.0183, 0.0180, 0.0141),
        (0.025, 0.0230, 0.0238, 0.0173),
        (0.035, 0.0256, 0.0270, 0.0189),
        (0.046, 0.0260, 0.0279, 0.0192),
        (0.057, 0.0240, 0.0259, 0.0178),
        (0.067, 0.0196, 0.0207, 0.0146),
        (0.075, 0.0140, 0.0142, 0.0100),
        (0.081, 0.0094, 0.0090, 0.0060),
        (0.085, 0.0074, 0.0070, 0.0038),
        (0.088, 0.0060, 0.0056, 0.0020),
        (0.0905, 0.0010, 0.0010, 0.0006),
    ]
    BODY_FROM = 0.0006
    BODY_TO = 0.0905
    JAW_TO = 0.0085
    JOINT = 0.083
    EYE_AT = (0.0148, 0.0052)
    EYE_RADIUS = 0.0046
    EYE_BULGE = 0.26
    GILL_AT = 0.026
    AROUND = 32
    AROUND_LOW = 10
    RINGS = ((0.0085, 0.0008), (0.028, 0.0015), (0.08, 0.0022), (0.0905, 0.0012))
    TAIL_PIVOT = 0.0045
    # (the game model: fewer rings along its short body, more rows across its spreading tails)
    GAME_RINGS = 15

    def mouth_y(self, xm):
        return -0.0006 - 0.14 * xm

    def fins(self, m):
        def dorsal_root(u):
            xm = 0.028 + 0.036 * u
            return (xm, self.top(xm) - 0.0009)

        def dorsal_edge(u):
            xm = 0.028 + 0.036 * u
            h = 0.0215 * (0.22 + 0.78 * (1.0 - u) ** 1.0) * (0.4 + 0.6 * smooth(0.0, 0.2, u))
            return (xm + 0.55 * h, self.top(xm) - 0.0009 + h)

        blade(m, DORSAL, "dorsal", between(dorsal_root, dorsal_edge), upright, SIDE, 0.0011, self.n(9, 3, 2), self.n(12, 4, 6))
        for sx in (1.0, -1.0):
            # The paired anal fins: side by side under the tail's root, spread apart.
            def anal_root(u):
                xm = 0.063 + 0.011 * u
                return (xm, self.bottom(xm) + 0.0006)

            def anal_edge(u):
                xm = 0.063 + 0.011 * u
                h = 0.0115 * (0.3 + 0.7 * (1.0 - u) ** 1.1) * (0.6 + 0.4 * smooth(0.0, 0.15, u))
                return (xm + 0.7 * h, self.bottom(xm) + 0.0006 - h)

            pivot = lambda xm: self.bottom(xm) + 0.0006
            place = spread(sx, pivot, 0.5, 0.0012)
            point = between(anal_root, anal_edge)
            blade(m, ANAL, "anals", lambda t, u: (point(t, u), t), lambda p: place(p[0], p[1]),
                  Vector((sx, 0.45, 0.0)), 0.0008, self.n(6, 2, 1), self.n(8, 2, 3))
            # The double tail: two forked tails, one each side, joined along the top and spread apart below.
            tail_root = lambda u: (0.0795, 0.0060 - 0.0118 * u)
            tail_edge = through([
                (0.0, 0.0835, 0.0108), (0.1, 0.110, 0.0215), (0.2, 0.140, 0.0280), (0.27, 0.1495, 0.0225),
                (0.36, 0.141, 0.0105), (0.46, 0.1295, 0.0000), (0.55, 0.137, -0.0110), (0.66, 0.1475, -0.0240),
                (0.76, 0.143, -0.0350), (0.88, 0.116, -0.0300), (1.0, 0.0905, -0.0150)])
            point_t = between(tail_root, tail_edge)
            if self.game:
                # (the game model's ten steps across each tail fall on the points its edge is drawn through,
                # so that the lobes' tips and the notch are kept)
                point_t = between(tail_root, lambda u, e=tail_edge: e(on_points(u, (0.0, 0.1, 0.2, 0.27, 0.36, 0.46, 0.55, 0.66, 0.76, 0.88, 1.0))))
            place_t = spread(sx, self.TAIL_PIVOT, lambda xm: 0.8 * smooth(0.0785, 0.092, xm), 0.0009)
            # (each point of the tail is turned out by how far back it is)
            blade(m, TAIL, "tails", lambda t, u, point_t=point_t: (point_t(t, u), point_t(t, u)[0]),
                  lambda p, place_t=place_t: place_t(p[0], p[1]), Vector((sx * 0.75, 0.65, 0.0)), 0.0,
                  self.n(12, 3, 5), self.n(18, 6, 10))
            root = self.skin(0.0265, -0.0150, sx)
            root.x -= sx * 0.0006
            self.paired(m, PECTORAL, "pectorals", sx, root, (0.42, -0.32, 0.85), (0.06, -0.88, 0.45),
                        0.0170, 0.0090, 0.0008, self.n(8, 2, 3), self.n(6, 3, 2),
                        lambda t: (0.45 + 0.55 * smooth(0.0, 0.35, t)) * (1.0 - t) ** 0.5)
            root = Vector((sx * 0.0045, self.bottom(0.045) + 0.0014, 0.045 - HALF))
            self.paired(m, PELVIC, "pelvics", sx, root, (0.32, -0.58, 0.75), (0.0, 0.14, 1.0),
                        0.0140, 0.0065, 0.0007, self.n(6, 2, 2), self.n(4, 2, 2),
                        lambda t: (1.0 - t) ** 0.7)


def on_points(u, us):
    """u (0 to 1, in even steps) carried onto the uneven places `us` (one more than the steps), straight between."""
    k = min(int(u * (len(us) - 1)), len(us) - 2)
    f = u * (len(us) - 1) - k
    return us[k] + (us[k + 1] - us[k]) * f


def material_of(name, colour):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = colour
    material.diffuse_color = colour
    return material


def winding(name, mesh, m):
    """Nothing inside out: every face's front is the way it was meant to face (Blender's front is the side a
    face's normal is on)."""
    bad = {}
    for poly in mesh.polygons:
        out, group = m.out[poly.index]
        if poly.normal.dot(to_b(out)) <= 0.0:
            bad[group] = bad.get(group, 0) + 1
            if os.environ.get("DEBUG_WINDING"):
                print("  bad", group, [tuple(round(x, 3) for x in m.data[v][0]) for v in poly.vertices],
                      tuple(round(x, 3) for x in out), tuple(round(x, 3) for x in poly.normal))
    told = ["%s %d/%d wrong" % (group, bad.get(group, 0), count) for group, count in m.count.items()]
    print("WINDING %s: %s: %s" % (name, "ok" if not bad else "INSIDE OUT", ", ".join(told)))


def export_one(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", export_yup=True, use_selection=True,
        export_animations=False, export_texcoords=True, export_vertex_color="NONE", export_all_vertex_colors=False,
    )


def render(folder, prefix, full, low, colours=False, game=None):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.show_cavity = True
    # (a model whose look is in its vertex colours has single-sheet fins, drawn from both sides)
    scene.display.shading.show_backface_culling = not colours
    scene.display.shading.color_type = "VERTEX" if colours else "MATERIAL"
    scene.render.resolution_x, scene.render.resolution_y = 1200, 800
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    L = LENGTH
    views = [("left", (1, 0, 0), (0, 0, 0), 1.15 * L), ("right", (-1, 0, 0), (0, 0, 0), 1.15 * L),
             ("front", (0, 1, 0), (0, 0, 0), 0.6 * L), ("back", (0, -1, 0), (0, 0, 0), 0.6 * L),
             ("top", (0.001, 0, 1), (0, 0, 0), 1.15 * L), ("under", (0.001, 0, -1), (0, 0, 0), 1.15 * L),
             ("head", (0.8, 0.5, 0.2), (0, HALF - 0.12 * L, 0), 0.42 * L),
             ("tail", (0.7, -0.6, 0.3), (0, -HALF + 0.2 * L, 0), 0.6 * L)]
    shown = [("", full, None), ("lo_", low, ("left", "head", "top", "back"))] + ([("game_", game, None)] if game else [])
    for tag, obj, only in shown:
        for other in bpy.context.scene.objects:
            if other.type == "MESH":
                other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if only and view not in only:
                continue
            offset = Vector(direction).normalized() * 10.0
            camera.data.ortho_scale = frame
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y").to_euler()
            if view == "top":
                camera.rotation_euler = (0.0, 0.0, math.pi / 2)
            elif view == "under":
                camera.rotation_euler = (math.pi, 0.0, math.pi / 2)
            scene.render.filepath = os.path.join(folder, "%s_%s%s.png" % (prefix, tag, view))
            bpy.ops.render.render(write_still=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    for kind in (Common, Fantail):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version = 0
        full_fish = kind(False)
        full, _ = full_fish.make(kind.NAME)
        low, _ = kind(True).make(kind.NAME + "_lo")
        game, _ = kind(False, True).make(kind.NAME + "_game")
        print("NUMBERS %s: joint=%.4f jaw_to=%.4f hinge_y=%.5f body_to=%.4f eye=(%.4f, %.4f) gill=%.4f" % (
            kind.NAME, kind.JOINT, kind.JAW_TO, full_fish.mouth_y(kind.JAW_TO), kind.BODY_TO,
            kind.EYE_AT[0], kind.EYE_AT[1], kind.GILL_AT))
        export_one(full, os.path.join(OUT, kind.NAME + ".glb"))
        export_one(low, os.path.join(OUT, kind.NAME + "_lo.glb"))
        export_one(game, os.path.join(OUT, kind.NAME + "_game.glb"))
        low.location.x = 0.06
        game.location.x = 0.12
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, kind.NAME + ".blend"))
        low.location.x = 0.0
        game.location.x = 0.0
        if PREVIEW:
            os.makedirs(PREVIEW, exist_ok=True)
            render(PREVIEW, kind.NAME, full, low, game=game)


if __name__ == "__main__":
    main()
