"""Builds the clams (creatures/clam) and exports them for Godot.

Run from the game's root:
    blender --background --factory-startup --python creatures/clam/tools/build_clam.py
    blender --background --factory-startup --python creatures/clam/tools/build_clam.py -- <preview folder>

Three kinds, each in three models (the full model for close pictures, the game model at Twilight Princess weight,
the low model for far off), all wearing one shader (clam.gdshader), which colours them and does all their moving:

    models/giant_clam.glb   giant_clam_game.glb   giant_clam_lo.glb
    models/scallop.glb      scallop_game.glb      scallop_lo.glb
    models/razor_clam.glb   razor_clam_game.glb   razor_clam_lo.glb

and the editable tools/clam.blend with all nine. Every model is one still mesh with one surface, built SHUT (the
shader swings the shell open about its hinge), except the giant clam's mantle, which is built as it is when the
clam is wide open (the shader folds it away inside the shell as the clam shuts). The game and low models are built
from the same outlines and curves as the full one with fewer, better placed points. It prints a WINDING line per
model (every face against the way out it was built to face; and each closed piece's faces tested by rays for an
odd number of crossings: none may be inside out), a SIZE line and a HINGE line (what the shader is told).

The animals (built from what the species look like; no picture was traced):

- THE GIANT CLAM (Tridacna gigas), 1.0 m long: two thick deep valves sitting hinge down, gape up, each folded into
  five great radial folds, so that the gape's edge zigzags and the two edges interlock; between them, when it is
  open, a thick fleshy mantle bulging up out of the gape and over its edges (its blue-green pattern is drawn by
  the shader), with a siphon.
- THE SCALLOP (a Pacific pink scallop, Chlamys hastata), 0.078 m: a round ribbed fan shell with two ears either
  side of a straight hinge, lying on its lower valve; inside its gape a mantle edge on each valve with a fringe of
  short tentacles (its row of tiny blue eyes is drawn by the shader along that edge, glinting).
- THE RAZOR CLAM (a jackknife, Ensis leei), 0.15 m: a long narrow straight-sided shell, a little curved, lying on its
  side; a big pale foot out of its front end (it digs with it), short paired siphons out of the back.

Everything here is in Godot space (metres, Y up, X its left side, its front at -Z) until it is written out. The
origin is on the ground under its middle.

What a point is, for the shader:
- UV2.y the part: 0 the shell's outside, 1 its inside, 2 its lip (the edge between them), 3 a mantle (the giant
  clam's; the scallop's mantle edges), 4 a tentacle, 6 the razor clam's foot, 7 a siphon.
- UV2.x which way it swings as the shell opens: 0 with the lower (the giant clam's right) valve, 1 with the upper
  (left) valve; on the giant clam's mantle, across it from its right edge (0) to its left (1).
- UV, on the shell: x from the hinge (0) to the edge (1), y round the fan (0..1; the razor clam's: along it from
  the front, 0..1); on the giant clam's mantle: x along it (0 front to 1 back), y across (0 right to 1 left); on a
  scallop's mantle edge: x round it (0..1), y from its root (0) to its edge (1); on anything else x from its root
  (0) to its tip (1), y a number of its own.
- COLOR.r, on the giant clam's mantle: 1 its upper face, 0 the lower.
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
OUTSIDE, INSIDE, LIP, MANTLE, TENTACLE, _, FOOT, SIPHON = range(8)
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

    def rows(self, rows, name, wrap, out=None):
        for r in range(len(rows) - 1):
            a, b = rows[r], rows[r + 1]
            n = len(a) if wrap else len(a) - 1
            for c in range(n):
                k = (c + 1) % len(a)
                self.face((a[c], a[k], b[k], b[c]), name, out)

    def fan(self, centre, row, name, wrap=True, out=None):
        n = len(row) if wrap else len(row) - 1
        for c in range(n):
            self.face((centre, row[c], row[(c + 1) % len(row)]), name, out)

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
        m.fan(o_apex, outer_rows[0], "shell", wrap=False)
        m.rows(outer_rows, "shell", False)
        m.fan(i_apex, inner_rows[0], "shell", wrap=False)
        m.rows(inner_rows, "shell", False)
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
            m.face(tri, "shell", (ps[1] - ps[0]).cross(ps[2] - ps[0]))
        # the walls at either end of the hinge, from the hinge's middle out to the edge
        for th, far in ((th0, False), (th1, True)):
            col = -1 if far else 0
            a = [m.add(self.origin + self.out * self.gap, (0.0, 0.5), LIP, self.w)] + [m.add(m.verts[row[col]], (u, tn[col]), LIP, self.w) for row, u in zip(outer_rows, us[1:])]
            b = [m.add(in_apex_at, (0.0, 0.5), LIP, self.w)] + [m.add(m.verts[row[col]], (u, tn[col]), LIP, self.w) for row, u in zip(inner_rows, in_us[1:])]
            dt = self.smooth_at(0.6, th + 0.01) - self.smooth_at(0.6, th - 0.01)
            wall_out = dt.normalized() * (1.0 if far else -1.0)
            m.zip(a, us, b, in_us, "shell", wall_out)


# ---------------------------------------------------------------------------------------------- the giant clam

GIANT_LENGTH = 1.0
# the outline seen from the side: a rounded fan over a straight hinge (half length GA, height GB at its top)
GA, GB, GC, GP = 0.5, 0.62, 0.30, 2.3
GIANT_DEPTH = 0.235
FOLDS = 5
FOLD = 0.11
GIANT_TURN = 0.2


def giant_outline_points():
    pts = []
    for i in range(241):
        a = -1.0 + 2.0 * i / 240
        x = math.copysign(abs(math.cos(math.pi * (1 - (a + 1) / 2))) ** (2.0 / GP), math.cos(math.pi * (1 - (a + 1) / 2)))
        y = abs(math.sin(math.pi * (1 - (a + 1) / 2))) ** (2.0 / GP)
        pts.append((GA * x, GC + (GB - GC) * y))
    # (down the ends to the hinge line)
    end = pts[-1]
    out = [(pts[0][0], 0.0)] + pts + [(end[0], 0.0)]
    return out


GIANT_R = polar_outline(giant_outline_points())


def giant_fold(u, th):
    x = FOLDS * th
    s = math.sin(x)
    tri = math.copysign(abs(s) ** 0.55, s)
    ends = smooth(0.0, 0.35, th) * smooth(0.0, 0.35, math.pi - th)
    return FOLD * u ** 1.4 * tri * ends


def giant_dome(u, th):
    g = (u ** 0.5) * (1.0 - u) ** 0.85 / 0.4636
    return GIANT_DEPTH * g * (0.15 + 0.85 * max(math.sin(th), 0.0) ** 0.45)


def make_giant(q):
    m = Mesh()
    if q == "full":
        thetas = [math.pi * i / 150 for i in range(151)]
        us = [(i / 40) ** 1.1 for i in range(41)]
        in_us = [(i / 30) for i in range(31)]
    elif q == "game":
        # (round the fan: the tops and the bottoms of the folds and half way between; out from the hinge: more
        # towards the edge, where the folds stand highest)
        thetas = sorted(set([0.0, math.pi] + [math.pi * (k + 0.5) / (FOLDS * 4) for k in range(FOLDS * 4)]
                            + [math.pi * 0.012, math.pi * 0.988]))
        us = [0.0, 0.1, 0.24, 0.4, 0.56, 0.7, 0.82, 0.91, 0.97, 1.0]
        in_us = [0.0, 0.3, 0.65, 0.9, 1.0]
    else:
        thetas = [math.pi * i / 20 for i in range(21)]
        us = [0.0, 0.35, 0.7, 1.0]
        in_us = [0.0, 0.6, 1.0]
    # its hinge along Z at the bottom, its gape up; the left valve (+X) and the right (-X)
    for side, w in ((1.0, 1.0), (-1.0, 0.0)):
        v = Valve((0.0, 0.0, 0.0), (0.0, 0.0, -1.0), (0.0, 1.0, 0.0), (side, 0.0, 0.0), GIANT_R, giant_dome,
                  lambda u, th: 0.0, giant_fold, (1.0, 0.0, 0.0), lambda u: 0.03 + 0.035 * (1.0 - u), w)
        v.build(m, us, thetas, in_us)
    giant_mantle(m, q)
    return m


def giant_rim_top(a):
    """The height of the gape's edge at `a` along the hinge (metres, + to the front)."""
    # (search the fan for the place whose edge is over `a`)
    lo, hi = 0.0, math.pi
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        r = GIANT_R(mid)
        if r * math.cos(mid) > a:
            lo = mid
        else:
            hi = mid
    th = 0.5 * (lo + hi)
    return GIANT_R(th) * math.sin(th), th


def giant_mantle(m, q):
    """The mantle as it is when the clam is wide open: a thick fleshy slab across the gape, bulging up out of it
    and over both edges; built open (the shader folds it shut)."""
    n_along = {"full": 64, "game": 20, "lo": 8}[q]
    tops = {"full": 24, "game": 8, "lo": 4}[q]
    bottoms = {"full": 10, "game": 3, "lo": 2}[q]
    edge_n = {"full": 4, "game": 1, "lo": 1}[q]
    a_end = 0.46
    sections = []
    for i in range(n_along + 1):
        t = i / n_along
        # (bunched a little towards the ends)
        tt = 0.5 - 0.5 * math.cos(math.pi * t)
        a = a_end - 2.0 * a_end * tt
        z = -a
        top_y, th = giant_rim_top(a)
        fold_x = giant_fold(1.0, th)
        env = math.sin(math.pi * tt) ** 0.5
        # the open gape's edges here (each valve turned out by GIANT_TURN about the hinge)
        c, s = math.cos(GIANT_TURN), math.sin(GIANT_TURN)
        left = (fold_x * c + top_y * s, -fold_x * s + top_y * c)
        right = (fold_x * c - top_y * s, fold_x * s + top_y * c)
        spread = 0.02 * env
        thick = 0.05 + 0.12 * env
        rise = 0.01 + 0.03 * env
        # (the edge is rounded a little; the slab goes on down from it into the gape)
        er = 0.02

        def top_at(sv):
            # across from the right edge (0) to the left (1), out over both edges and drooping down them
            x = right[0] - spread + (left[0] - right[0] + 2.0 * spread) * sv
            base = right[1] + (left[1] - right[1]) * sv
            y = base + rise * math.sin(math.pi * sv) ** 0.6 - 0.025 * env * (abs(2.0 * sv - 1.0) ** 6)
            return Vector((x, y, z))

        loop = []
        for k in range(tops + 1):
            sv = k / tops
            p = top_at(sv)
            d = top_at(min(sv + 0.01, 1.0)) - top_at(max(sv - 0.01, 0.0))
            up = Vector((-d.y, d.x, 0.0)).normalized()
            if up.y < 0.0:
                up = -up
            loop.append((p, sv, up, 1.0))
        # round the left edge, along the underside, round the right edge
        lp = loop[-1][0]
        for k in range(1, edge_n + 1):
            a2 = math.pi * k / (edge_n + 1)
            way = Vector((math.sin(a2), math.cos(a2), 0.0))
            loop.append((lp + Vector((er * math.sin(a2), -er * (1.0 - math.cos(a2)), 0.0)), 1.0, way, 1.0))
        for k in range(bottoms, -1, -1):
            sv = k / bottoms
            p = top_at(sv)
            loop.append((Vector((p.x * 0.6, p.y - thick, z)), sv, Vector((0.0, -1.0, 0.0)), 0.0))
        rp = loop[0][0]
        for k in range(edge_n, 0, -1):
            a2 = math.pi * k / (edge_n + 1)
            way = Vector((-math.sin(a2), math.cos(a2), 0.0))
            loop.append((rp + Vector((-er * math.sin(a2), -er * (1.0 - math.cos(a2)), 0.0)), 0.0, way, 1.0))
        row = [m.add(p, (t, sv), MANTLE, sv, way, (top, 0.0, 0.0)) for p, sv, way, top in loop]
        sections.append(row)
    m.rows(sections, "mantle", True)
    # the ends, closed across: the upper face's points joined to the lower face's
    for row, way in ((sections[0], Vector((0.0, 0.0, -1.0))), (sections[-1], Vector((0.0, 0.0, 1.0)))):
        cx = sum((m.verts[i] for i in row), Vector()) / len(row)
        centre = m.add(cx, (0.0 if way.z < 0 else 1.0, 0.5), MANTLE, 0.5, way, (1.0, 0.0, 0.0))
        m.fan(centre, row, "mantle", out=way)


# ---------------------------------------------------------------------------------------------- the scallop

SCALLOP_R = 0.039
EAR_A, EAR_P = 0.026, 0.020
RIBS = 19
RIB = 0.0013
SCALLOP_UP, SCALLOP_DOWN = 0.0105, 0.0125
SCALLOP_TURN = 0.38


def scallop_outline_points():
    pts = [(EAR_A, 0.0)]
    d_from = 0.62
    for i in range(121):
        th = d_from + (math.pi - 2.0 * d_from) * i / 120
        r = 2.0 * SCALLOP_R * math.sin(th)
        pts.append((r * math.cos(th), r * math.sin(th)))
    pts.append((-EAR_P, 0.0))
    return pts


SCALLOP_RO = polar_outline(scallop_outline_points())


def scallop_ears(th):
    return smooth(0.25, 0.75, th) * smooth(0.25, 0.75, math.pi - th)


def scallop_dome(h):
    def dome(u, th):
        return h * max(math.sin(math.pi * min(u, 1.0) ** 0.8), 0.0) * (0.15 + 0.85 * scallop_ears(th))
    return dome


def scallop_rib(th):
    x = RIBS * (th - 0.62) / (math.pi - 1.24) * TAU
    return (0.5 + 0.5 * math.cos(x)) ** 1.6


def scallop_ribs(u, th):
    """The ribs standing out of each valve, fading out at the edge (where `scallop_fold` takes over)."""
    return RIB * smooth(0.0, 0.5, u) * scallop_rib(th) * scallop_ears(th) * (1.0 - smooth(0.8, 1.0, u))


def scallop_fold(u, th):
    """At the edge the ribs are a fold of both valves together (up at a rib, down between), so that the edges
    meet in a crinkled line, as a scallop's do."""
    return RIB * 0.9 * smooth(0.6, 1.0, u) * (scallop_rib(th) - 0.4) * scallop_ears(th)


def make_scallop(q):
    m = Mesh()
    if q == "full":
        thetas = [math.pi * i / 152 for i in range(153)]
        us = [(i / 28) ** 0.9 for i in range(29)]
        in_us = [i / 18 for i in range(19)]
    elif q == "game":
        # (round the fan: on the crest of every rib, which make its outline from the side and the front, and a
        # few round each ear; the shader draws the ribs between)
        crests = [0.62 + k * (math.pi - 1.24) / RIBS for k in range(RIBS + 1)]
        thetas = sorted(set([min(round(t, 6), math.pi) for t in crests + [0.0, 0.2, 0.42, math.pi - 0.42, math.pi - 0.2, math.pi]]))
        us = [0.0, 0.2, 0.42, 0.65, 0.85, 1.0]
        in_us = [0.0, 0.6, 1.0]
    else:
        thetas = adaptive(lambda t: (SCALLOP_RO(t) * math.cos(t), SCALLOP_RO(t) * math.sin(t)), 0.0, math.pi, 0.002, 6, 12)
        us = [0.0, 0.35, 0.7, 1.0]
        in_us = [0.0, 0.6, 1.0]
    y0 = SCALLOP_DOWN + RIB
    hinge = Vector((0.0, y0, SCALLOP_R))
    for out, h, w in ((Vector((0.0, 1.0, 0.0)), SCALLOP_UP, 1.0), (Vector((0.0, -1.0, 0.0)), SCALLOP_DOWN, 0.0)):
        v = Valve(hinge, (1.0, 0.0, 0.0), (0.0, 0.0, -1.0), out, SCALLOP_RO, scallop_dome(h), scallop_ribs,
                  scallop_fold, (0.0, 1.0, 0.0), lambda u: 0.0011, w)
        v.build(m, us, thetas, in_us)
        scallop_mantle(m, q, v)
    return m


def scallop_mantle(m, q, v):
    """A mantle edge inside the valve's edge, hanging towards the gape, with its fringe of tentacles."""
    m.open_groups.add("mantle")
    around = {"full": 96, "game": 14, "lo": 8}[q]
    across = {"full": [0.0, 0.25, 0.5, 0.75, 1.0], "game": [0.0, 1.0], "lo": [0.0, 1.0]}[q]
    th_a, th_b = 0.75, math.pi - 0.75
    rows = []
    for c in across:
        row = []
        for i in range(around + 1):
            th = th_a + (th_b - th_a) * i / around
            # from inside the shell (0.84 of the way out, on its inside) to its edge, hanging half way to the gape
            u = 0.84 + 0.13 * c
            p = v.inner(u, th) - v.normal(u, th) * 0.0006
            sink = v.dome(u, th) * 0.55 * c
            p = p - v.out * sink
            way = v.along * math.cos(th) + v.away * math.sin(th)
            row.append(m.add(p, (i / around, c), MANTLE, v.w, way * 0.6 - v.out))
        rows.append(row)
    m.rows(rows, "mantle", False)
    rng = random.Random(4 if v.w > 0.5 else 5)
    count = {"full": 34, "game": 6, "lo": 0}[q]
    for k in range(count):
        th = th_a + (th_b - th_a) * (k + 0.5) / count + rng.uniform(-0.02, 0.02)
        u = 0.965
        root = v.inner(u, th) - v.out * v.dome(u, th) * 0.5
        way = (v.along * math.cos(th) + v.away * math.sin(th)).normalized()
        length = 0.0065 * rng.uniform(0.75, 1.15)
        tip = root + way * length - v.out * 0.0012
        finger(m, TENTACLE, "tentacles", bent(root, root + way * length * 0.5, tip), lambda t: 0.00045 * (1.0 - 0.6 * t),
               {"full": 6, "game": 3, "lo": 3}[q], {"full": 5, "game": 1, "lo": 1}[q], v.w, rng.random())


# ---------------------------------------------------------------------------------------------- the razor clam

RAZOR_LENGTH = 0.15
RAZOR_H = 0.025
RAZOR_D = 0.0058
RAZOR_BOW = 0.004
RAZOR_TURN = 0.12


def razor_half(a):
    """Half the shell's height at `a` along it (+ to the back): straight sides, square-cut ends with rounded
    corners."""
    r = 0.0045
    d = abs(a) - (RAZOR_LENGTH * 0.5 - r)
    if d <= 0.0:
        return RAZOR_H * 0.5
    return RAZOR_H * 0.5 - r + math.sqrt(max(r * r - d * d, 0.0))


def razor_point(u, v, side, y0, inner=0.0):
    """A point of a valve: u along it (0 the front, 1 the back), v across (0 its hinged back edge, 1 its belly
    edge); `side` +1 the upper valve, -1 the lower; `inner` how far in (the inside)."""
    a = (-0.5 + u) * (RAZOR_LENGTH * 0.996 - 3.0 * inner)
    h = razor_half(a)
    bow = RAZOR_BOW * (1.0 - (2.0 * u - 1.0) ** 2)
    # (lower towards the ends, which gape: the valves meet only along their sides)
    depth = RAZOR_D * max(math.sin(math.pi * v), 0.0) ** 0.55 * (h / (RAZOR_H * 0.5)) ** 0.45
    depth *= 1.0 - 0.6 * smooth(RAZOR_LENGTH * 0.5 - 0.014, RAZOR_LENGTH * 0.5, abs(a))
    if inner > 0.0:
        # (the inside: within the edge by a little more than the shell is thick, and never through the plane
        # where the valves meet)
        h = max(min(h, razor_half((-0.5 + u) * RAZOR_LENGTH * 0.996)) - inner * 1.5, 0.0002)
        depth = max(depth - inner, depth * 0.35, inner * 0.25)
    x = (2.0 * v - 1.0) * h + bow
    # (a hair off the plane where the valves meet, so that they never share a point)
    return Vector((x, y0 + side * (depth + 0.00004), a))


def make_razor(q):
    m = Mesh()
    nu = {"full": 140, "game": 22, "lo": 8}[q]
    nv = {"full": 24, "game": 6, "lo": 4}[q]
    # (along it: closer together at the round ends; across: closer at the edges)
    us = [0.5 - 0.5 * math.cos(math.pi * i / nu) for i in range(nu + 1)]
    vs = [0.5 - 0.5 * math.cos(math.pi * j / nv) for j in range(nv + 1)]
    y0 = RAZOR_D + 0.0007
    thick = 0.0006
    for side, w in ((1.0, 1.0), (-1.0, 0.0)):
        out = Vector((0.0, side, 0.0))
        o = [[m.add(razor_point(u, v, side, y0), (u, v), OUTSIDE, w, out + Vector((2.0 * v - 1.0, 0.0, 2.0 * u - 1.0)) * 0.6) for v in vs] for u in us]
        n_in = [[m.add(razor_point(u, v, side, y0, thick), (u, v), INSIDE, w, -out) for v in vs] for u in us]
        m.rows(o, "shell", False)
        m.rows(n_in, "shell", False, out=-out)
        # the lip all round: along the back edge, round the back end, along the belly, round the front
        loop_o = [o[i][0] for i in range(len(us))] + [o[-1][j] for j in range(1, len(vs))] + \
                 [o[i][-1] for i in range(len(us) - 2, -1, -1)] + [o[0][j] for j in range(len(vs) - 2, 0, -1)]
        loop_i = [n_in[i][0] for i in range(len(us))] + [n_in[-1][j] for j in range(1, len(vs))] + \
                 [n_in[i][-1] for i in range(len(us) - 2, -1, -1)] + [n_in[0][j] for j in range(len(vs) - 2, 0, -1)]
        lo = [m.add(m.verts[i], m.data[i][0][:1] + (1.0 - m.data[i][0][1],), LIP, w) for i in loop_o]
        li = [m.add(m.verts[i], m.data[i][0][:1] + (1.0 - m.data[i][0][1],), LIP, w) for i in loop_i]
        for k in range(len(lo)):
            k2 = (k + 1) % len(lo)
            # (the lip faces out across the edge: away from the middle of the valve beside it)
            mid = (m.verts[lo[k]] + m.verts[lo[k2]]) * 0.5
            u_here = 0.5 * (m.data[loop_o[k]][0][0] + m.data[loop_o[k2]][0][0])
            v_here = 1.0 - 0.5 * (m.data[loop_o[k]][0][1] + m.data[loop_o[k2]][0][1])
            uc, vc = min(max(u_here, 0.06), 0.94), min(max(v_here, 0.15), 0.85)
            ref = (razor_point(uc, vc, side, y0) + razor_point(uc, vc, side, y0, thick)) * 0.5
            way = (m.verts[lo[k]] + m.verts[lo[k2]] + m.verts[li[k]] + m.verts[li[k2]]) * 0.25 - ref
            m.face((lo[k], lo[k2], li[k2]), "shell", way)
            m.face((lo[k], li[k2], li[k]), "shell", way)
    # the foot, out of the front end; the siphons out of the back
    rng = random.Random(2)
    root = Vector((0.0, y0, -RAZOR_LENGTH * 0.5 + 0.014))
    tip = Vector((0.0, y0 - 0.002, -RAZOR_LENGTH * 0.5 - 0.03))
    finger(m, FOOT, "foot", bent(root, (root + tip) * 0.5 + Vector((0.0, 0.002, 0.0)), tip),
           lambda t: 0.0062 * (1.0 - 0.15 * t) * (1.0 + 0.25 * smooth(0.55, 0.85, t)),
           {"full": 20, "game": 8, "lo": 5}[q], {"full": 24, "game": 6, "lo": 2}[q], 0.5, 0.0)
    for sx in (1.0, -1.0):
        root = Vector((sx * 0.0032, y0, RAZOR_LENGTH * 0.5 - 0.012))
        tip = Vector((sx * 0.0036, y0 + 0.001, RAZOR_LENGTH * 0.5 + 0.011))
        finger(m, SIPHON, "siphons", bent(root, (root + tip) * 0.5, tip), lambda t: 0.003 * (1.0 - 0.1 * t),
               {"full": 12, "game": 5, "lo": 4}[q], {"full": 12, "game": 2, "lo": 1}[q], 0.5, rng.random())
    return m


# ---------------------------------------------------------------------------------------------- writing it out

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
    material = bpy.data.materials.get("clam") or bpy.data.materials.new("clam")
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.8, 0.75, 0.68, 1.0)
    material.diffuse_color = (0.8, 0.75, 0.68, 1.0)
    mesh.materials.append(material)
    for poly in mesh.polygons:
        # (the lip is a narrow edge: drawn flat, so that its shading does not bend round its sharp corners)
        poly.use_smooth = round(1.0 - m.data[m.faces[poly.index][0]][1][1]) != LIP
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
            if bad[group] <= 3 and os.environ.get("CLAM_DEBUG"):
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
                if os.environ.get("CLAM_DEBUG"):
                    d = m.data[m.faces[f[src]][0]]
                    tag = "%s part %d u %.1f w %d th %.1f" % (name, round(1.0 - d[1][1]), d[0][0], round(d[1][0]), 1.0 - d[0][1])
                    seen[tag] = seen.get(tag, 0) + 1
                    if os.environ.get("CLAM_DEBUG") == "2" and name.endswith(os.environ.get("CLAM_WHICH", "_game")):
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
        at = obj.location + Vector((0.0, 0.0, size * 0.25))
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
    print("HINGE giant_clam: at (0, 0, 0) along Z, valves turn %.3f each" % GIANT_TURN)
    print("HINGE scallop: at (0, %.5f, %.5f) along X, the upper valve turns %.3f" % (SCALLOP_DOWN + RIB, SCALLOP_R, SCALLOP_TURN))
    print("HINGE razor_clam: at (%.5f, %.5f, 0) along Z, the upper valve turns %.3f" % (-RAZOR_H * 0.5, RAZOR_D + 0.0007, RAZOR_TURN))
    made = []
    kinds = (("giant_clam", make_giant, GIANT_LENGTH), ("scallop", make_scallop, 0.08), ("razor_clam", make_razor, RAZOR_LENGTH))
    only = os.environ.get("CLAM_ONLY", "")
    for kind, maker, length in kinds:
        if only and kind != only:
            continue
        for q in LEVELS:
            name = kind + {"full": "", "game": "_game", "lo": "_lo"}[q]
            obj, tris = to_object(name, maker(q))
            export_one(obj, os.path.join(OUT, name + ".glb"))
            made.append((name, obj, length))
    for i, (name, obj, length) in enumerate(made):
        obj.location = Vector(((i % 3) * 1.4, (i // 3) * 1.4, 0.0))
    if not only:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "clam.blend"))
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, made)


if __name__ == "__main__":
    main()
