"""Builds the oysters (creatures/oyster) and exports them for Godot.

Run from the game's root:
    blender --background --factory-startup --python creatures/oyster/tools/build_oyster.py
    blender --background --factory-startup --python creatures/oyster/tools/build_oyster.py -- <preview folder>

Two models, each in three versions (the full model for close pictures, the game model at Twilight Princess weight,
the low model for far off), all wearing one shader (oyster.gdshader), which colours them and opens them:

    models/oyster.glb        oyster_game.glb        oyster_lo.glb         one oyster
    models/oyster_clump.glb  oyster_clump_game.glb  oyster_clump_lo.glb   five grown together, one piece

and the editable tools/oyster.blend with all six. Every model is one still mesh with one surface, built SHUT: the
shader swings each upper valve open about its hinge. The game and low models are built from the same outlines and
curves as the full one with fewer, better placed points. It prints a WINDING line per model (every face against the
way out it was built to face; and each closed piece's faces tested by rays for an odd number of crossings), a SIZE
line, and HINGE and PEARL lines: what the node script tells the shader (Oyster.KINDS: keep them in step).

The animal (built from what the species looks like; no picture was traced): a Pacific oyster (Magallana gigas),
0.16 m from its hinge to its bill: a rough, irregular, teardrop shell grown in layers, frilled where each layer ends;
the lower (left) valve a deep cup, cemented down; the upper (right) valve flatter, sitting just inside the lower
one's edge. Inside, mother-of-pearl (drawn by the shader) and the soft body lying in the cup, with its dark frilled
mantle edge; a pearl lying on it (shown by the shader when `pearl` is on).

Everything here is in Godot space (metres, Y up, X its left side, its bill at -Z) until it is written out. The
origin is on the ground under its middle.

What a point is, for the shader:
- UV2.y the part: 0 the shell's outside, 1 its inside, 2 its lip, 3 the soft body, 4 the pearl.
- UV2.x which oyster of the clump it is and which way it swings: 2 x (its number, 0..4) + 1 for the upper valve.
- UV, on the shell: x from the hinge (0) to the edge (1), y round it (0..1); on the body: x from its middle (0) to
  its edge (1), y round it; on the pearl: x, y round it.
(The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.)
"""

import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "models")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = ARGS[0] if ARGS else ""
TAU = math.tau
OUTSIDE, INSIDE, LIP, BODY, PEARL = range(5)
LEVELS = ("full", "game", "lo")


def to_b(p):
    return Vector((p.x, -p.z, p.y))


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


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
        self.open_groups = set()

    def add(self, p, uv, part, w=0.0, out=(0.0, 1.0, 0.0), col=(0.0, 0.0, 0.0)):
        self.verts.append(Vector(p))
        self.data.append(((uv[0], 1.0 - uv[1]), (w, 1.0 - part), col))
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

    def _together(self, tris, name, out):
        """Adds triangles that make one smooth sheet all wound alike: which way is decided once for the whole
        sheet, by most of their corners' (or `out`) ways out, so that a few faces on the steep edges of the
        shell's layers, where the smooth way out is a poor guide, are not turned against their neighbours."""
        vote = 0.0
        for t in tris:
            ps = [self.verts[i] for i in t]
            n = (ps[1] - ps[0]).cross(ps[2] - ps[0])
            way = out if out is not None else sum((self.hint[i] for i in t), Vector())
            vote += 1.0 if n.dot(way) > 0.0 else -1.0
        for t in tris:
            t = t if vote >= 0.0 else tuple(reversed(t))
            ps = [self.verts[i] for i in t]
            n = (ps[1] - ps[0]).cross(ps[2] - ps[0])
            if n.length > 1e-14:
                self.face(t, name, n)

    def rows(self, rows, name, wrap, out=None):
        tris = []
        for r in range(len(rows) - 1):
            a, b = rows[r], rows[r + 1]
            n = len(a) if wrap else len(a) - 1
            for c in range(n):
                k = (c + 1) % len(a)
                # (as two triangles split along the shorter diagonal: the rough shell bends sharply, and a
                # quad split the long way can fold over)
                if (self.verts[a[c]] - self.verts[b[k]]).length <= (self.verts[a[k]] - self.verts[b[c]]).length:
                    tris += [(a[c], a[k], b[k]), (a[c], b[k], b[c])]
                else:
                    tris += [(a[c], a[k], b[c]), (a[k], b[k], b[c])]
        self._together(tris, name, out)

    def fan(self, centre, row, name, wrap=True, out=None):
        n = len(row) if wrap else len(row) - 1
        self._together([(centre, row[c], row[(c + 1) % len(row)]) for c in range(n)], name, out)

    def zip(self, a, ta, b, tb, name, out):
        """Triangles between two lines of points that need not have as many points, each point at a place `t`
        along them (both from the same start to the same end)."""
        i = j = 0
        while i < len(a) - 1 or j < len(b) - 1:
            if j >= len(b) - 1 or (i < len(a) - 1 and ta[i + 1] <= tb[j + 1]):
                self.face((a[i], a[i + 1], b[j]), name, out)
                i += 1
            else:
                self.face((a[i], b[j + 1], b[j]), name, out)
                j += 1


def adaptive(f, a, b, tol, n_min, n_max):
    """Places to sample f (a function of one number giving a tuple) between a and b, more where it bends."""
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


def finger(m, part, name, curve, radius, sides, segs, w, own=0.0):
    """A stalk round `curve(t)` (t 0 at its root to 1 at its tip), `radius(t)` thick, closed by a point at its tip
    and at its root."""
    first = (curve(0.02) - curve(0.0)).normalized()
    ref = Vector((1.0, 0.0, 0.0))
    if abs(first.dot(ref)) > 0.8:
        ref = Vector((0.0, 1.0, 0.0))
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
            way = a * math.cos(turn) + b * math.sin(turn)
            row.append(m.add(here + way * r, (t, own), part, w, way))
        rows.append((here, row, along))
    m.rows([r[1] for r in rows], name, True)
    end = curve(1.0)
    tip = m.add(end, (1.0, own), part, w, end - rows[-1][0])
    m.fan(tip, rows[-1][1], name)
    if sides <= 4:
        m.face(tuple(rows[0][1]), name, -rows[0][2])
    else:
        root = m.add(rows[0][0], (0.0, own), part, w, -rows[0][2])
        m.fan(root, rows[0][1], name)


def bent(p0, p1, p2):
    def curve(t):
        a = 1.0 - t
        return p0 * (a * a) + p1 * (2.0 * a * t) + p2 * (t * t)
    return curve


def polar_outline(points):
    """r(theta): how far from the hinge's middle (the origin) the outline `points` (a closed list of (a, b), the
    origin on or inside it) lies, along the ray at `theta` (0 along +a, pi/2 along +b)."""
    def r(theta):
        d = (math.cos(theta), math.sin(theta))
        best = 0.0
        for i in range(len(points)):
            p, q = points[i], points[(i + 1) % len(points)]
            e = (q[0] - p[0], q[1] - p[1])
            den = d[0] * e[1] - d[1] * e[0]
            if abs(den) < 1e-12:
                continue
            t = (p[0] * e[1] - p[1] * e[0]) / den
            s = (p[0] * d[1] - p[1] * d[0]) / den
            if -1e-9 <= s <= 1.0 + 1e-9 and t > best:
                best = t
        return best
    return r


# ---------------------------------------------------------------------------------------------- a valve

class Valve:
    """One valve of a shell, a fan from its hinge's middle `origin`: `along` the hinge, `away` from it across the
    plane where the valves meet, `out` the way this valve bulges from that plane. A point at (u, theta), u from the
    hinge (0) to the edge (1), theta round the fan from +along (0) to -along (pi), lies at
        origin + (along cos theta + away sin theta) * u * r(theta) + out * (dome + ribs) + fold_way * fold
    (`fold` moves both valves the same way, so that their zigzag edges meet). Its inside is the smooth surface (no
    ribs) moved in by `thick`."""

    def __init__(self, origin, along, away, out, r, dome, ribs, fold, fold_way, thick, w):
        self.origin, self.along, self.away, self.out = Vector(origin), Vector(along), Vector(away), Vector(out)
        self.r, self.dome, self.ribs, self.fold, self.fold_way = r, dome, ribs, fold, Vector(fold_way)
        self.thick, self.w = thick, w
        self.name = "upper valve" if int(w) % 2 else "lower valve"
        # (each valve stands a hair off the plane where they meet, a thousandth of its size, so that the two
        # never share a point and each is a closed solid of its own)
        self.gap = 0.0006 * r(math.pi * 0.5)

    def smooth_at(self, u, th):
        flat = (self.along * math.cos(th) + self.away * math.sin(th)) * (u * self.r(th))
        return self.origin + flat + self.out * (self.dome(u, th) + self.gap) + self.fold_way * self.fold(u, th)

    def normal(self, u, th):
        du = self.smooth_at(min(u + 0.004, 1.0), th) - self.smooth_at(max(u - 0.004, 0.0), th)
        dt = self.smooth_at(u, th + 0.004) - self.smooth_at(u, th - 0.004)
        n = du.cross(dt)
        if n.length < 1e-12:
            return self.out
        n.normalize()
        return n if n.dot(self.out) > 0.0 else -n

    def outer(self, u, th):
        return self.smooth_at(u, th) + self.out * self.ribs(u, th)

    def inner(self, u, th):
        """The inside: drawn in from the edge by the shell's thickness and lowered by it, but never below 0.4 of
        the outside's height there (so that it never comes through the outside, nor down onto the plane where
        the valves meet: near the hinge, and at the edge, the shell is thinner)."""
        # (drawn in towards the middle as far as the outline is near on either side, so that at a corner of
        # the outline the inside stays within it)
        r_here = max(self.r(th), 1e-6)
        r_near = min(self.r(max(th - 0.05, 0.0)), r_here, self.r(min(th + 0.05, math.pi)))
        ui = u * max(0.3, 1.0 - (r_here - r_near + self.thick(u)) / r_here * smooth(0.5, 1.0, u))
        flat = (self.along * math.cos(th) + self.away * math.sin(th)) * (ui * self.r(th))
        d = self.dome(ui, th)
        return self.origin + flat + self.out * (max(d - self.thick(u), 0.4 * d) + self.gap) + self.fold_way * self.fold(ui, th)

    def build(self, m, us, thetas, in_us):
        """The valve as a closed solid: its outside on the rows `us` (from 0, the hinge) by the places `thetas`
        round it, its inside on the rows `in_us` by the same places, the lip along its edge, and walls at either
        end of the hinge."""
        th0, th1 = thetas[0], thetas[-1]
        span = th1 - th0
        tn = [(t - th0) / span for t in thetas]
        o_apex = m.add(self.origin + self.out * self.gap, (0.0, 0.5), OUTSIDE, self.w, self.out)
        # (the inside closes to the same point as the outside: the shell thins to its beak there)
        in_apex_at = self.origin + self.out * self.gap
        i_apex = m.add(in_apex_at, (0.0, 0.5), INSIDE, self.w, -self.out)
        outer_rows = []
        for u in us[1:]:
            outer_rows.append([m.add(self.outer(u, t), (u, n), OUTSIDE, self.w, self.normal(u, t)) for t, n in zip(thetas, tn)])
        inner_rows = []
        for u in in_us[1:]:
            inner_rows.append([m.add(self.inner(u, t), (u, n), INSIDE, self.w, -self.normal(u, t)) for t, n in zip(thetas, tn)])
        m.fan(o_apex, outer_rows[0], self.name, wrap=False)
        m.rows(outer_rows, self.name, False)
        m.fan(i_apex, inner_rows[0], self.name, wrap=False)
        m.rows(inner_rows, self.name, False)
        # the lip: its own points (so that it can be coloured as the lip), the outer edge and the inner edge
        lip_o = [m.add(self.outer(1.0, t), (1.0, n), LIP, self.w) for t, n in zip(thetas, tn)]
        lip_i = [m.add(self.inner(1.0, t), (1.0, n), LIP, self.w) for t, n in zip(thetas, tn)]
        # (the lip faces out of the shell across its edge: away from the shell a little in from it. Its
        # triangles are all wound alike, which way decided by most of them: where the lip is thin and flat,
        # out at an ear, the way out is a poor guide for one face by itself)
        tris = []
        vote = 0.0
        for k in range(len(thetas) - 1):
            t = 0.5 * (thetas[k] + thetas[k + 1])
            mid = (m.verts[lip_o[k]] + m.verts[lip_o[k + 1]] + m.verts[lip_i[k]] + m.verts[lip_i[k + 1]]) * 0.25
            lip_way = mid - (self.outer(0.9, t) + self.inner(0.9, t)) * 0.5
            for tri in ((lip_o[k], lip_o[k + 1], lip_i[k + 1]), (lip_o[k], lip_i[k + 1], lip_i[k])):
                ps = [m.verts[i] for i in tri]
                n = (ps[1] - ps[0]).cross(ps[2] - ps[0])
                if n.length > 1e-14:
                    vote += 1.0 if n.dot(lip_way) > 0.0 else -1.0
                    tris.append(tri)
        for tri in tris:
            tri = tri if vote >= 0.0 else tuple(reversed(tri))
            ps = [m.verts[i] for i in tri]
            m.face(tri, self.name, (ps[1] - ps[0]).cross(ps[2] - ps[0]))
        # the walls at either end of the hinge, from the hinge's middle out to the edge
        for th, far in ((th0, False), (th1, True)):
            col = -1 if far else 0
            a = [m.add(self.origin + self.out * self.gap, (0.0, 0.5), LIP, self.w)] + [m.add(m.verts[row[col]], (u, tn[col]), LIP, self.w) for row, u in zip(outer_rows, us[1:])]
            b = [m.add(in_apex_at, (0.0, 0.5), LIP, self.w)] + [m.add(m.verts[row[col]], (u, tn[col]), LIP, self.w) for row, u in zip(inner_rows, in_us[1:])]
            dt = self.smooth_at(0.6, th + 0.01) - self.smooth_at(0.6, th - 0.01)
            wall_out = dt.normalized() * (1.0 if far else -1.0)
            m.zip(a, us, b, in_us, self.name, wall_out)


# ---------------------------------------------------------------------------------------------- the oyster

OYSTER_LENGTH = 0.16
# how far round from straight ahead its outline narrows (radians): the teardrop's width
SPREAD = 0.64
D_LOW, D_UP = 0.032, 0.009
UP_TURN = 0.16
PEARL_R = 0.0058
# The clump: each oyster's size, which way its bill points (round, up), how it is rolled about its own length,
# and where its hinge is (metres, before the clump is set down on the ground).
CLUMP = [
    (1.0, 0.0, 0.22, 0.05, (0.0, 0.02, 0.05)),
    (0.84, 2.2, 0.95, 0.45, (0.022, 0.028, 0.012)),
    (0.76, -2.1, 1.1, -0.5, (-0.026, 0.024, 0.016)),
    (0.7, 0.95, 0.75, 0.6, (0.034, 0.03, 0.042)),
    (0.62, -0.85, 1.25, -0.35, (-0.022, 0.036, 0.046)),
]


def merge(into, other, xf):
    """Adds `other` to `into`, moved by the matrix `xf` (turned, moved, scaled the same every way)."""
    base = len(into.verts)
    turn = xf.to_3x3().normalized()
    for p, d, h in zip(other.verts, other.data, other.hint):
        into.verts.append(xf @ p)
        into.data.append(d)
        into.hint.append(turn @ h)
    for f, o, n in zip(other.faces, other.outs, other.names):
        into.faces.append(tuple(i + base for i in f))
        into.outs.append(turn @ o)
        into.names.append(n)
        into.count[n] = into.count.get(n, 0) + 1
    into.open_groups |= other.open_groups


def oyster_r(seed, shrink=1.0):
    """Its outline, a teardrop out from the hinge with a wavy, irregular edge: how far from the hinge it reaches
    at `theta` (0 to its left side along the hinge, pi/2 straight to the bill)."""
    rng = random.Random(seed)
    skew = rng.uniform(-0.1, 0.1)
    waves = [(rng.uniform(0.03, 0.06), 4, rng.uniform(0, TAU)), (rng.uniform(0.03, 0.06), 7, rng.uniform(0, TAU)),
             (rng.uniform(0.015, 0.03), 13, rng.uniform(0, TAU))]

    def r(th):
        d = th - math.pi * 0.5 - skew
        wavy = 1.0 + sum(a * math.sin(n * th + p) for a, n, p in waves)
        # (never quite to a point: the hinge has a little width)
        return OYSTER_LENGTH * shrink * (0.07 + 0.93 * math.exp(-(d / SPREAD) ** 2)) * wavy
    return r


def oyster_dome(depth, r):
    """How deep (or high) the valve bulges: most in its middle, and as little as the outline is narrow, so that
    by the hinge, where the outline closes to a point, the valve closes flat to it."""
    def dome(u, th):
        wide = min(1.0, r(th) / (0.55 * OYSTER_LENGTH)) ** 0.7
        return depth * max(math.sin(math.pi * min(u, 1.0) ** 0.75), 0.0) ** 0.9 * wide
    return dome


def lamellae(seed, layers, height, smooth_out):
    """The layers it grew in, each standing out a little further and frilled at its edge (a step out at the
    end of each), and low irregular flutes out from the hinge. `smooth_out`: their average only (for the game
    and low models, which have too few rows to show each layer: the shader draws them)."""
    rng = random.Random(seed + 100)
    p1, p2, p3 = rng.uniform(0, TAU), rng.uniform(0, TAU), rng.uniform(0, TAU)

    def f(u, th):
        x = u * layers + 0.35 * math.sin(3.0 * th + p1) + 0.2 * math.sin(7.0 * th + p2)
        s = x - math.floor(x)
        # (smoothed: near the top of each layer, which is what makes its outline)
        step = 0.9 if smooth_out else 0.3 + 0.7 * s ** 2.5
        flute = 0.5 + 0.5 * math.sin(9.0 * th + p3 + 2.0 * math.sin(4.0 * th))
        return height * smooth(0.04, 0.3, u) * (1.0 - smooth(0.9, 1.0, u)) * (step + 0.5 * flute * u)
    return f


def one_oyster(q, idx, seed, clump, pearl):
    """One oyster in its own frame: the hinge's middle at the origin, its bill to -Z, the lower valve below the
    plane y = 0 where the valves meet. Returns the mesh and the pearl's middle (or None)."""
    m = Mesh()
    r_low = oyster_r(seed)
    r_up = oyster_r(seed, 0.985)
    smooth_out = q != "full"
    if not clump:
        if q == "full":
            thetas = [math.pi * i / 128 for i in range(129)]
            us_low = [(i / 72) ** 0.95 for i in range(73)]
            us_up = [(i / 56) ** 0.95 for i in range(57)]
            in_us = [i / 24 for i in range(25)]
            body_t, body_r, pearl_n = 90, 14, (28, 18)
        elif q == "game":
            thetas = adaptive(lambda t: (r_low(t) * math.cos(t), r_low(t) * math.sin(t)), 0.0, math.pi, 0.0008, 10, 28)
            us_low = [0.0, 0.1, 0.22, 0.36, 0.5, 0.64, 0.77, 0.88, 0.96, 1.0]
            us_up = [0.0, 0.2, 0.45, 0.7, 0.9, 1.0]
            in_us = [0.0, 0.5, 1.0]
            body_t, body_r, pearl_n = 16, 3, (10, 6)
        else:
            thetas = adaptive(lambda t: (r_low(t) * math.cos(t), r_low(t) * math.sin(t)), 0.0, math.pi, 0.003, 6, 12)
            us_low = [0.0, 0.4, 0.75, 1.0]
            us_up = [0.0, 0.5, 1.0]
            in_us = [0.0, 0.5, 1.0]
            body_t, body_r, pearl_n = 8, 1, (6, 4)
    else:
        if q == "full":
            thetas = [math.pi * i / 64 for i in range(65)]
            us_low = [(i / 40) ** 0.95 for i in range(41)]
            us_up = [(i / 32) ** 0.95 for i in range(33)]
            in_us = [i / 12 for i in range(13)]
            body_t, body_r, pearl_n = 60, 8, (24, 16)
        elif q == "game":
            thetas = adaptive(lambda t: (r_low(t) * math.cos(t), r_low(t) * math.sin(t)), 0.0, math.pi, 0.0015, 8, 14)
            us_low = [0.0, 0.25, 0.55, 0.8, 1.0]
            us_up = [0.0, 0.45, 1.0]
            in_us = [0.0, 0.5, 1.0]
            body_t, body_r, pearl_n = 8, 1, (8, 5)
        else:
            thetas = adaptive(lambda t: (r_low(t) * math.cos(t), r_low(t) * math.sin(t)), 0.0, math.pi, 0.005, 6, 8)
            us_low = [0.0, 0.4, 0.75, 1.0]
            us_up = [0.0, 0.5, 1.0]
            in_us = [0.0, 0.4, 0.75, 1.0]
            body_t, body_r, pearl_n = 6, 1, (6, 4)
    origin = Vector((0.0, 0.0, 0.0))
    along, away = Vector((1.0, 0.0, 0.0)), Vector((0.0, 0.0, -1.0))
    low = Valve(origin, along, away, (0.0, -1.0, 0.0), r_low, oyster_dome(D_LOW, r_low),
                lamellae(seed, 8, 0.0028, smooth_out), lambda u, th: 0.0, (0.0, 1.0, 0.0),
                lambda u: 0.0016 + 0.0016 * (1.0 - u), 2 * idx)
    low.build(m, us_low, thetas, in_us)
    up = Valve(origin, along, away, (0.0, 1.0, 0.0), r_up, oyster_dome(D_UP, r_up),
               lamellae(seed + 7, 7, 0.0022, smooth_out), lambda u, th: 0.0, (0.0, 1.0, 0.0),
               lambda u: 0.0013 + 0.0012 * (1.0 - u), 2 * idx + 1)
    up.build(m, us_up, thetas, in_us)
    # The soft body, lying in the cup just below where the valves meet: a low mound out to its frilled edge,
    # which turns down into the cup (one face up: it is seen only from above, when the oyster is open).
    m.open_groups.add("body")
    rows = []
    bt = [0.18 + (math.pi - 0.36) * i / body_t for i in range(body_t + 1)]
    for k in range(body_r + 1):
        rb = 0.08 + 0.92 * k / body_r
        uv = 0.12 + 0.74 * rb
        row = []
        for t in bt:
            flat = (along * math.cos(t) + away * math.sin(t)) * (uv * r_low(t))
            y = -0.0035 - 0.0035 * rb * rb
            row.append(m.add(Vector((flat.x, y, flat.z)), (rb, (t - bt[0]) / (bt[-1] - bt[0])), BODY, 2 * idx, (0.0, 1.0, 0.0)))
        rows.append(row)
    # (its edge, turning down into the cup)
    edge = []
    for t in bt:
        flat = (along * math.cos(t) + away * math.sin(t)) * (0.88 * r_low(t))
        edge.append(m.add(Vector((flat.x, -0.0062, flat.z)), (1.0, (t - bt[0]) / (bt[-1] - bt[0])), BODY, 2 * idx, (flat.x, 0.4, flat.z)))
    rows.append(edge)
    m.rows(rows, "body", False, out=Vector((0.0, 1.0, 0.0)))
    centre = None
    if pearl:
        t = math.pi * 0.5 + 0.25
        flat = (along * math.cos(t) + away * math.sin(t)) * ((0.12 + 0.74 * 0.62) * r_low(t))
        # (half sunk in the soft body: its top just under the upper valve when the oyster is shut)
        centre = Vector((flat.x, 0.0012 - PEARL_R, flat.z))
        around, high = pearl_n
        ring_rows = []
        top = m.add(centre + Vector((0.0, PEARL_R, 0.0)), (0.5, 0.0), PEARL, 2 * idx, (0.0, 1.0, 0.0))
        bottom = m.add(centre - Vector((0.0, PEARL_R, 0.0)), (0.5, 1.0), PEARL, 2 * idx, (0.0, -1.0, 0.0))
        for j in range(1, high):
            a = math.pi * j / high
            ring = []
            for i in range(around):
                b = TAU * i / around
                way = Vector((math.sin(a) * math.cos(b), math.cos(a), math.sin(a) * math.sin(b)))
                ring.append(m.add(centre + way * PEARL_R, (i / around, j / high), PEARL, 2 * idx, way))
            ring_rows.append(ring)
        m.fan(top, ring_rows[0], "pearl")
        m.rows(ring_rows, "pearl", True)
        m.fan(bottom, ring_rows[-1], "pearl")
    return m, centre


SHIFTS = {}


def make_single(q):
    part, pearl = one_oyster(q, 0, 11, False, True)
    m = Mesh()
    # (every version is set down where the full model is, so that its hinges and pearl are in the same places)
    if "single" not in SHIFTS:
        full = part if q == "full" else one_oyster("full", 0, 11, False, True)[0]
        lo_y = min(p.y for p in full.verts)
        zs = [p.z for p in full.verts]
        SHIFTS["single"] = Matrix.Translation((0.0, -lo_y, -0.5 * (min(zs) + max(zs))))
    shift = SHIFTS["single"]
    merge(m, part, shift)
    hinges = [(shift @ Vector((0.0, 0.0, 0.0)), Vector((1.0, 0.0, 0.0)))]
    return m, hinges, shift @ pearl


def make_clump(q):
    m = Mesh()
    hinges = []
    pearl = None
    placed = []
    for idx, (size, yaw, pitch, roll, at) in enumerate(CLUMP):
        part, centre = one_oyster(q, idx, 21 + idx * 5, True, idx == 0)
        xf = Matrix.Translation(at) @ Matrix.Rotation(yaw, 4, "Y") @ Matrix.Rotation(pitch, 4, "X") @ Matrix.Rotation(roll, 4, "Z") @ Matrix.Scale(size, 4)
        placed.append((part, xf, centre))
    if "clump" not in SHIFTS:
        if q != "full":
            make_clump("full")
        else:
            every = [xf @ p for part, xf, _ in placed for p in part.verts]
            lo_y = min(p.y for p in every)
            xs = [p.x for p in every]
            zs = [p.z for p in every]
            SHIFTS["clump"] = Matrix.Translation((-0.5 * (min(xs) + max(xs)), -lo_y, -0.5 * (min(zs) + max(zs))))
    shift = SHIFTS["clump"]
    for part, xf, centre in placed:
        whole = shift @ xf
        merge(m, part, whole)
        hinges.append((whole @ Vector((0.0, 0.0, 0.0)), (whole.to_3x3().normalized() @ Vector((1.0, 0.0, 0.0))).normalized()))
        if centre is not None:
            pearl = whole @ centre
    return m, hinges, pearl


def to_object(name, m):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) for p in m.verts], [], m.faces)
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
    material = bpy.data.materials.get("oyster") or bpy.data.materials.new("oyster")
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.8, 0.75, 0.68, 1.0)
    material.diffuse_color = (0.8, 0.75, 0.68, 1.0)
    mesh.materials.append(material)
    for poly in mesh.polygons:
        # (the lip is a narrow edge: drawn flat, so that its shading does not bend round its sharp corners)
        poly.use_smooth = round(1.0 - m.data[m.faces[poly.index][0]][1][1]) != LIP
    # (the layers' frilled edges are sharp: their shading is split there, not bent round them)
    mesh.set_sharp_from_angle(angle=math.radians(70.0))
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
    """Nothing inside out: every face against the way out it was built to face; and each closed piece's faces, by
    rays: a line out of a face, the way it faces, must cross that piece's skin an even number of times."""
    bad = {}
    for poly in mesh.polygons:
        if poly.normal.dot(to_b(m.outs[poly.index])) <= 0.0:
            group = m.names[poly.index]
            bad[group] = bad.get(group, 0) + 1
            if bad[group] <= 3 and os.environ.get("OYSTER_DEBUG"):
                print("  wrong %s at %s" % (group, [tuple(round(c, 4) for c in m.verts[i]) for i in m.faces[poly.index]]))
    # (each piece is the faces joined by sharing points at the same place)
    key = {}
    parent = list(range(len(m.verts)))

    def root_of(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, p in enumerate(m.verts):
        k = (round(p.x, 7), round(p.y, 7), round(p.z, 7))
        if k in key:
            a, b = root_of(i), root_of(key[k])
            if a != b:
                parent[a] = b
        else:
            key[k] = i
    for f in m.faces:
        for i in f[1:]:
            a, b = root_of(f[0]), root_of(i)
            if a != b:
                parent[a] = b
    pieces = {}
    for fi, f in enumerate(m.faces):
        pieces.setdefault((m.names[fi], root_of(f[0])), []).append(fi)
    odd = {}
    seen = {}
    for (group, _), members in pieces.items():
        if group in m.open_groups:
            continue
        bm = bmesh.new()
        src = bm.faces.layers.int.new("src")
        made = {}
        for fi in members:
            vs = []
            for i in m.faces[fi]:
                k = (round(m.verts[i].x, 7), round(m.verts[i].y, 7), round(m.verts[i].z, 7))
                if k not in made:
                    made[k] = bm.verts.new(to_b(m.verts[i]))
                vs.append(made[k])
            try:
                f = bm.faces.new(vs)
                f[src] = fi
            except ValueError:
                pass
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bm.normal_update()
        tree = BVHTree.FromBMesh(bm)
        wrong = 0
        for f in bm.faces:
            if f.calc_area() < 1e-12:
                continue
            nudge = 1e-6
            at = f.calc_center_median() + f.normal * nudge
            hits = 0
            while hits < 60:
                hit = tree.ray_cast(at, f.normal)
                if hit[0] is None:
                    break
                hits += 1
                at = hit[0] + f.normal * nudge
            if hits % 2:
                wrong += 1
                if os.environ.get("OYSTER_DEBUG"):
                    d = m.data[m.faces[f[src]][0]]
                    tag = "%s part %d u %.1f w %d th %.1f" % (name, round(1.0 - d[1][1]), d[0][0], round(d[1][0]), 1.0 - d[0][1])
                    seen[tag] = seen.get(tag, 0) + 1
                    if os.environ.get("OYSTER_DEBUG") == "2" and name.endswith(os.environ.get("OYSTER_WHICH", "_game")):
                        c0 = f.calc_center_median()
                        print("  odd %s at %.5f %.5f %.5f facing %s hits %d area %.2e" % (tag, c0.x, c0.z, -c0.y, tuple(round(x, 2) for x in f.normal), hits, f.calc_area()))
        bm.free()
        odd[group] = odd.get(group, 0) + wrong
    if seen:
        print("  odd faces by part and u: %s" % sorted(seen.items()))
    told = ["%s %d/%d wrong, %s odd" % (g, bad.get(g, 0), c, "open:" if g in m.open_groups else odd.get(g, 0)) for g, c in m.count.items()]
    # (a few faces at sharp corners of the outline, the size of a pin prick, may cross a neighbour there)
    ok = not bad and all(odd[g] <= m.count[g] * 0.02 for g in odd)
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
        at = obj.location + Vector((0.0, 0.0, size * 0.2))
        for view, direction, frame in (("left", (1, 0, 0), 1.3), ("top", (0.001, 0, 1), 1.3),
                                       ("front", (0, 1, 0), 1.1), ("quarter", (0.8, 0.9, 0.6), 1.3)):
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
    for kind, maker, size in (("oyster", make_single, 0.17), ("oyster_clump", make_clump, 0.3)):
        for q in LEVELS:
            name = kind + {"full": "", "game": "_game", "lo": "_lo"}[q]
            m, hinges, pearl = maker(q)
            obj, tris = to_object(name, m)
            export_one(obj, os.path.join(OUT, name + ".glb"))
            made.append((name, obj, size))
            if q == "full":
                for i, (at, axis) in enumerate(hinges):
                    print("HINGE %s %d: at Vector3(%.5f, %.5f, %.5f) along Vector3(%.5f, %.5f, %.5f)" % (kind, i, at.x, at.y, at.z, axis.x, axis.y, axis.z))
                print("PEARL %s: at Vector3(%.5f, %.5f, %.5f)" % (kind, pearl.x, pearl.y, pearl.z))
    for i, (name, obj, size) in enumerate(made):
        obj.location = Vector(((i % 3) * 0.5, (i // 3) * 0.5, 0.0))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "oyster.blend"))
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, made)


if __name__ == "__main__":
    main()
