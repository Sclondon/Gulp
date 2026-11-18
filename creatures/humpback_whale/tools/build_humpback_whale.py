"""Builds the humpback whale (creatures/humpback_whale) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/humpback_whale/tools/build_humpback_whale.py
    blender --background --python creatures/humpback_whale/tools/build_humpback_whale.py -- <preview folder>   # with pictures

Writes creatures/humpback_whale/models/humpback_whale.glb (the full model, for close up) and humpback_whale_lo.glb
(far off, phones), and the editable creatures/humpback_whale/tools/humpback_whale.blend (this folder has a
.gdignore). Each model is one still mesh with one surface: the shader (humpback_whale.gdshader) swims it, opens
its mouth and draws every marking. It prints a WINDING line: the check that nothing is inside out.

It also writes humpback_whale_game.glb, the game model (2026-11-18): at the weight of a Twilight Princess model, with
the full model's outline, for games. The user: "We should have a twilight princess model to compare to so we can
make low poly versions while maintaining high quality looks and silhouettes", then "just rebuild all of them, and
keep the high quality version as well". It is built from the same lines as the others, with fewer rings and
points placed where the outline bends (GAME_DEFAULTS, and GAME where a whale has its own); the full and low models come out as
before, byte for byte.

A humpback whale (Megaptera novaeangliae), 14 m from the tip of its snout to the notch of its flukes, built from
the species (no picture was traced), on the plan of GameCommon's blue whale:

- THE BODY: stout, deepest (3.2 m) and widest a little ahead of the middle, narrowing to a tail stock thin from
  side to side. The head a quarter of its length: the upper jaw slender and flat, studded with knobs (the
  tubercles: a row down its middle and two rows each side); a low splash guard ahead of the two blowholes. A small
  dorsal fin on a hump two thirds of the way back.
- THE LOWER JAW: its own closed part, broad and bowed out wider than the upper jaw, with a row of knobs along each
  lip and a cluster at the chin; the shader swings it down about its hinge under the eye. The throat behind it has
  broad pleats (drawn by the shader) back to the navel and balloons as the mouth opens.
- THE BALEEN: a curtain each side hanging from the edge of the roof of the mouth (dark plates, a grey fringe),
  inside the lower jaw's lips when the mouth is shut. Inside it, a dark wall each side of the mouth that unfolds
  from the roof of the mouth down to the lower jaw as it opens.
- THE FINS, each a thin closed blade: the very long flippers, a third of its length, their leading edges scalloped
  with knobs; the broad flukes, their trailing edge ragged, with a notch in the middle.

Everything here is worked out in body lengths in Godot space (Y up, nose towards -Z; s 0 the snout's tip to 1 the
flukes' notch, the origin at s 0.5 on the middle line) and written out in metres.

What a point is, for the shader: vertex colour red the part, as a tenth (0 body, 1 lower jaw, 2 eye, 3 baleen,
4 the mouth's wall, 5 dorsal, 6 flukes, 7 flipper, 8 a knob on the upper skin, 9 a knob on the lower jaw). On the
body and jaw: UV.x how far along (s), UV.y how high (0 the belly or keel line, 1 the back line or the middle of
the floor of the mouth); UV2.x how far round the skin from the top line (metres, + its left side, - its right),
UV2.y the whole way round from top line to bottom line (metres); green how much of the throat (it balloons),
blue how much inside the mouth. On a fin: UV.x root (0) to tip (1) (on the flukes, middle to tip), UV.y leading
(0) to trailing (1) edge; UV2 and blue the way its flat side faces. On the mouth's wall green is how far it
unfolds. On an eye or knob: UV where a point is on its round face. (The glTF writer flips V: what is written here
is 1 - v, so that Godot reads v.)

The numbers the shader shares (LENGTH, the hinge, FAN_OPEN, NAVEL_S) are kept in step by hand: change one, change
the other.
"""

import bisect
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
# What a point is, for the shader (vertex colour red, as a tenth).
K_BODY, K_JAW, K_EYE, K_BALEEN, K_FAN, K_DORSAL, K_FLUKES, K_FLIPPER, K_KNOB, K_JAW_KNOB = range(10)
LIP = None


def to_b(p):
    """Godot space (Y up, nose at -Z) to Blender space (Z up, nose at +Y)."""
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
    """A lofted skin: at each place along the animal (s, 0 the tip of the snout to 1 the notch of the flukes)
    its top line, bottom line, half width, how far up from the bottom it is widest (0..1), and how boxy its
    upper and lower halves are (2 an ellipse, more is squarer, less is pointed). All in body lengths."""

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

    def y_at(self, s, x, upper):
        """How high the skin is at x out from the middle, on the upper or the lower half."""
        top, bot, hw, ycf, nt, nb = self.at(s)
        yc = bot + ycf * (top - bot)
        f = min(abs(x) / max(hw, 1e-9), 1.0)
        if upper:
            return yc + (top - yc) * (1.0 - f ** nt) ** (1.0 / nt)
        return yc - (yc - bot) * (1.0 - f ** nb) ** (1.0 / nb)

    def outline(self, s, half, gain=0.0):
        """half + 1 points down its right side from the top line to the bottom line, evenly spaced along the
        skin: (x, y, how far round from the top). With `gain` (the game model) they are closer together where
        the skin bends more sharply (spaced as 1 / sqrt of its curvature, which spreads the error of straight
        edges evenly), so the outline seen from the front and from above stays round on few points."""
        top, bot, hw, ycf, nt, nb = self.at(s)
        yc = bot + ycf * (top - bot)
        dense = []
        steps = 240
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
        if gain > 0.0:
            # (each piece of the skin weighed by its length times 1 + gain * sqrt(how sharply it turns there))
            bend = []
            for i in range(steps):
                seg = acc[i + 1] - acc[i]
                a0 = math.atan2(dense[i][1] - dense[i - 1][1], dense[i][0] - dense[i - 1][0]) if i > 0 else None
                a1 = math.atan2(dense[i + 1][1] - dense[i][1], dense[i + 1][0] - dense[i][0])
                a2 = (math.atan2(dense[i + 2][1] - dense[i + 1][1], dense[i + 2][0] - dense[i + 1][0])
                      if i + 2 <= steps else None)
                turn = 0.0
                for a in (a0, a2):
                    if a is not None:
                        turn += abs((a1 - a + math.pi) % TAU - math.pi)
                bend.append(math.sqrt(turn / max(seg, 1e-12)) if seg > 1e-12 else 0.0)
            mean = sum(b * (acc[i + 1] - acc[i]) for i, b in enumerate(bend)) / max(whole, 1e-12)
            wacc = [0.0]
            for i in range(steps):
                wacc.append(wacc[-1] + (acc[i + 1] - acc[i]) * (1.0 + gain * bend[i] / max(mean, 1e-12)))
            for j in range(half + 1):
                want = wacc[-1] * j / half
                i = min(bisect.bisect_right(wacc, want) - 1, steps - 1)
                span = wacc[i + 1] - wacc[i]
                t = (want - wacc[i]) / span if span > 1e-12 else 0.0
                out.append((lerp(dense[i][0], dense[i + 1][0], t), lerp(dense[i][1], dense[i + 1][1], t),
                            lerp(acc[i], acc[i + 1], t)))
            out[0] = (dense[0][0], dense[0][1], 0.0)
            out[-1] = (dense[-1][0], dense[-1][1], whole)
            return out, whole
        for j in range(half + 1):
            want = whole * j / half
            i = min(bisect.bisect_right(acc, want) - 1, steps - 1)
            span = acc[i + 1] - acc[i]
            t = (want - acc[i]) / span if span > 1e-12 else 0.0
            out.append((lerp(dense[i][0], dense[i + 1][0], t), lerp(dense[i][1], dense[i + 1][1], t), want))
        return out, whole


BODY_SKIN = None
JAW_SKIN = None


def lip(s):
    """The lower jaw's lip line: just up inside the upper jaw's edge (its underside curves up to its edge,
    and the lower jaw is the wider: shut, its lips close up over the edge of the upper jaw)."""
    return BODY_SKIN.y_at(s, LIP_AT * BODY_SKIN.at(s)[2], False) + LIP_IN


def body_y(s, x, upper=True):
    """The body's skin at x out from the middle (the top's ridges and humps on it)."""
    y = BODY_SKIN.y_at(s, x, upper)
    return y + (extra_top(s, x) if upper else 0.0)


def body_frame(s, y):
    """A place on the body's right side (+x) at height y: the point, the way out of the skin, the way up it."""
    e = 0.0015
    x = BODY_SKIN.x_at(s, y)
    dy = (BODY_SKIN.x_at(s, y + e) - BODY_SKIN.x_at(s, y - e)) / (2 * e)
    ds = (BODY_SKIN.x_at(s + e, y) - BODY_SKIN.x_at(s - e, y)) / (2 * e)
    return Vector((x, y, s - 0.5)), Vector((1.0, -dy, -ds)).normalized(), Vector((dy, 1.0, 0.0)).normalized()


def jaw_frame(s, y):
    e = 0.0015
    x = JAW_SKIN.x_at(s, y)
    dy = (JAW_SKIN.x_at(s, y + e) - JAW_SKIN.x_at(s, y - e)) / (2 * e)
    ds = (JAW_SKIN.x_at(s + e, y) - JAW_SKIN.x_at(s - e, y)) / (2 * e)
    return Vector((x, y, s - 0.5)), Vector((1.0, -dy, -ds)).normalized(), Vector((dy, 1.0, 0.0)).normalized()


def top_frame(s, x):
    """A place on the upper skin at x out from the middle: the point, the way out, the way forward-ish up."""
    e = 0.0015
    y = body_y(s, x)
    dx = (body_y(s, x + e) - body_y(s, x - e)) / (2 * e)
    ds = (body_y(s + e, x) - body_y(s - e, x)) / (2 * e)
    out = Vector((-dx, 1.0, -ds)).normalized()
    return Vector((x, y, s - 0.5)), out


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

    def mirrored(self, name):
        other = Part(name)
        for p, d in zip(self.verts, self.data):
            other.add((-p.x, p.y, p.z), d[0], (-d[1][0], d[1][1]), d[2])
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
            if f.calc_area() > 1e-9:
                counted += 1
                at = f.calc_center_median() + f.normal * 2e-5
                hits = 0
                while hits < 40:
                    hit = tree.ray_cast(at, f.normal)
                    if hit[0] is None:
                        break
                    hits += 1
                    at = hit[0] + f.normal * 2e-5
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
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        # (where a skin closes to a line on the middle plane, a four-cornered face has three corners in that
        # plane: cut it from its fourth corner, so that no triangle lies flat in the plane)
        for f in list(bm.faces):
            if len(f.verts) == 4:
                off = [loop for loop in f.loops if abs(loop.vert.co.x) > 1e-7]
                if len(off) == 1:
                    bmesh.ops.connect_verts(bm, verts=[off[0].vert, off[0].link_loop_next.link_loop_next.vert])
        # (faces squashed to nothing where a skin closes go)
        bmesh.ops.dissolve_degenerate(bm, dist=1e-6, edges=bm.edges)
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


def places(n, first, last, density):
    """n + 1 places from first to last, closer together where `density(s)` is higher."""
    steps = 4000
    acc = [0.0]
    for i in range(steps):
        s = lerp(first, last, (i + 0.5) / steps)
        acc.append(acc[-1] + density(s))
    out = []
    for k in range(n + 1):
        want = acc[-1] * k / n
        i = min(bisect.bisect_right(acc, want) - 1, steps - 1)
        t = (want - acc[i]) / max(acc[i + 1] - acc[i], 1e-12)
        out.append(lerp(first, last, (i + t) / steps))
    return out


def bends(lines, first, last, steps=4000):
    """For the game model: how sharply the given lines (functions of s, or of r on a fin) bend at each of
    `steps` places from first to last, as sqrt(|second derivative|) summed, scaled to average 1. Points
    spaced as 1 / that put as much error between each pair (a straight edge between points is off by about
    h * h * |f''| / 8)."""
    h = (last - first) / steps
    out = []
    for i in range(steps):
        s = first + h * (i + 0.5)
        k = 0.0
        for f in lines:
            k += math.sqrt(abs(f(s + h) - 2.0 * f(s) + f(s - h)) / (h * h))
        out.append(k)
    mean = sum(out) / steps
    return [k / max(mean, 1e-12) for k in out]


def game_places(n, first, last, lines, gain, even=None):
    """n + 1 places from first to last for the game model: closer where the lines bend (weight `gain`), and
    where `even(s)` (another density, weight 1) asks."""
    table = bends(lines, first, last)
    steps = len(table)

    def density(s):
        i = min(max(int((s - first) / (last - first) * steps), 0), steps - 1)
        return (even(s) if even else 1.0) + gain * table[i]
    return places(n, first, last, density)


def skin(part, section, where, half, kind, gain=0.0):
    """Lofts a Section into a Part (BODY or JAW). UV: (s, 1 - h), h how high (0 the belly or keel line, 1 the
    back line or the middle of the floor of the mouth); UV2: (how far round from the top line, metres, + its
    left side (+x), - its right; 1 - the whole way round from the top line to the bottom line, metres)."""
    rings = []
    for s in where:
        side, whole = section.outline(s, half, gain)
        top, bot, hw, ycf, nt, nb = section.at(s)
        yc = bot + ycf * (top - bot)
        ring = []
        # (down the right side and back up the left; the bottom line is there twice, once for each side, so
        # that how far round a point is does not run from one side's number to the other's across one face)
        for j in list(range(half + 1)) + list(range(half, 0, -1)):
            x, y, arc = side[j]
            sign = 1.0 if len(ring) <= half else -1.0
            if kind == K_BODY:
                if y > yc:
                    y += extra_top(s, x)
                h = (y - bot) / max(top - bot, 1e-9)
                # the roof of the mouth: the flat underside of the upper jaw, ahead of the jaw's hinge
                roof = 0.0
                if y < yc:
                    roof = smooth(0.42, 0.14, (y - bot) / max(yc - bot, 1e-9)) * smooth(HINGE_S + 0.012, HINGE_S - 0.01, s)
                # how much of the throat this is, which balloons as the mouth opens
                throat = (smooth(HINGE_S - 0.005, HINGE_S + 0.04, s) * (1.0 - smooth(NAVEL_S - 0.16, NAVEL_S, s))
                          * smooth(0.55, 0.08, h))
                ring.append(part.add((sign * x, y, s - 0.5), (s, 1.0 - h),
                                     (sign * arc * LENGTH, 1.0 - whole * LENGTH), (K_BODY / 10.0, throat, roof)))
            else:
                h = (y - bot) / max(top - bot, 1e-9)
                inside = smooth(0.78, 0.97, (y - yc) / max(top - yc, 1e-9)) if y > yc else 0.0
                inside *= smooth(HINGE_S + 0.03, HINGE_S - 0.004, s) * smooth(-0.002, 0.015, s)
                ring.append(part.add((sign * x, y, s - 0.5), (s, 1.0 - h),
                                     (sign * arc * LENGTH, 1.0 - whole * LENGTH), (K_JAW / 10.0, 0.0, inside)))
        rings.append(ring)
    part.loft(rings)


def dome(part, kind, at, out, up, ball, stands, rows, around, uv_round=True, back_ring=True):
    """A dome set in a skin: a ball of radius `ball` standing `stands` out of it, closed behind, inside.
    Without `back_ring` (the game model's knobs) the rim is closed straight away by a fan to a point inside."""
    along = up.cross(out).normalized()
    up = out.cross(along).normalized()
    seen = math.sqrt(max(1.0 - (1.0 - stands / ball) ** 2, 1e-6))
    reach = math.asin(min(seen, 0.999))
    if stands > ball:
        reach = math.pi - math.asin(min(seen, 0.999))
    centre = at - out * (ball - stands)
    rings = []
    for i in range(1, rows + 1):
        a = reach * i / rows
        ring = []
        for k in range(around):
            q = TAU * k / around
            p = centre + out * (ball * math.cos(a)) + (up * math.cos(q) + along * math.sin(q)) * (ball * math.sin(a))
            r = 0.5 * i / rows
            ring.append(part.add(p, (0.5 + r * math.cos(q), 1.0 - (0.5 + r * math.sin(q))), (0.0, 1.0),
                                 (kind / 10.0, 0.0, 0.0)))
        rings.append(ring)
    back = centre + out * (ball * math.cos(reach) - 0.6 * stands)
    if not back_ring:
        tip = part.add(centre + out * ball, (0.5, 0.5), (0.0, 1.0), (kind / 10.0, 0.0, 0.0))
        first = rings[0]
        for k in range(around):
            part.faces.append((tip, first[(k + 1) % around], first[k]))
        part.loft(rings)
        last = rings[-1]
        mid = part.add(back, (0.5, 0.5), (0.0, 1.0), (kind / 10.0, 0.0, 0.0))
        for k in range(around):
            part.faces.append((mid, last[k], last[(k + 1) % around]))
        return
    rings.append([part.add(back, (0.5 + 0.5 * math.cos(TAU * k / around), 0.5 - 0.5 * math.sin(TAU * k / around)),
                           (0.0, 1.0), (kind / 10.0, 0.0, 0.0)) for k in range(around)])
    # (the middle of the top: a fan of triangles to one point)
    tip = part.add(centre + out * ball, (0.5, 0.5), (0.0, 1.0), (kind / 10.0, 0.0, 0.0))
    first = rings[0]
    for k in range(around):
        part.faces.append((tip, first[(k + 1) % around], first[k]))
    part.loft(rings)
    # (the back closed by a fan as well)
    last = rings[-1]
    mid = part.add(back - out * 0.2 * stands, (0.5, 0.5), (0.0, 1.0), (kind / 10.0, 0.0, 0.0))
    for k in range(around):
        part.faces.append((mid, last[k], last[(k + 1) % around]))


def airfoil(t):
    """How thick a fin is across its chord (0 its leading edge, 1 its trailing edge), 1 at its thickest."""
    t = max(0.0, min(1.0, t))
    return (t ** 0.5 * (1.0 - t)) / 0.3849


def blade(name, kind, rows, cols, mid, normal, thick, uvs, closed_root=True, t_power=1.0, r_at=None):
    """A fin: a thin closed solid round the surface mid(r, t) (r 0 root to 1 tip, t 0 leading to 1 trailing
    edge), `thick(r, t)` through, its two skins meeting at its edges; closed by a wall at its root (inside the
    body) when `closed_root`, else meeting there too. UV: `uvs(r, t)`; UV2 and blue the way it faces. `r_at`
    (the game model): the rows' places, rows + 1 of them from 0 to 1, instead of evenly."""
    part = Part(name)
    top, under = [], []
    for j in range(rows + 1):
        r = r_at[j] if r_at else j / rows
        a, b = [], []
        for i in range(cols + 1):
            t = (i / cols) ** t_power if t_power != 1.0 else i / cols
            # (finer towards the leading edge, where it is roundest)
            t = 0.5 - 0.5 * math.cos(math.pi * t)
            p = mid(r, t)
            n = normal(r, t).normalized()
            th = thick(r, t)
            data = (uvs(r, t), (n.x, 1.0 - n.y), (kind / 10.0, 0.0, n.z * 0.5 + 0.5))
            a.append(part.add(p + n * (0.5 * th), *data))
            b.append(part.add(p - n * (0.5 * th), *data))
        top.append(a)
        under.append(b)

    def zero(j, i):
        return i == 0 or i == cols or j == rows or (j == 0 and not closed_root)
    for j in range(rows):
        for i in range(cols):
            corners = [(j, i), (j, i + 1), (j + 1, i + 1), (j + 1, i)]
            flat = [zero(*c) for c in corners]
            for sheet in (top, under):
                q = [sheet[c[0]][c[1]] for c in corners]
                if flat.count(True) == 3:
                    k = flat.index(False)
                    part.faces += [(q[k], q[(k + 1) % 4], q[(k + 2) % 4]), (q[k], q[(k + 2) % 4], q[(k + 3) % 4])]
                elif flat.count(True) < 4:
                    part.faces.append(tuple(q))
    if closed_root:
        for i in range(cols):
            part.faces.append((top[0][i], under[0][i], under[0][i + 1], top[0][i + 1]))
    return part


def slab(name, kind, grid, normal, thick, data):
    """A thin closed solid round a grid of middle points grid[i][j], `thick` through along `normal`; data(i, j)
    gives (uv, uv2, colour)."""
    part = Part(name)
    n_i, n_j = len(grid), len(grid[0])
    a = [[part.add(grid[i][j] + normal * (0.5 * thick), *data(i, j)) for j in range(n_j)] for i in range(n_i)]
    b = [[part.add(grid[i][j] - normal * (0.5 * thick), *data(i, j)) for j in range(n_j)] for i in range(n_i)]
    for i in range(n_i - 1):
        for j in range(n_j - 1):
            part.faces.append((a[i][j], a[i + 1][j], a[i + 1][j + 1], a[i][j + 1]))
            part.faces.append((b[i][j], b[i][j + 1], b[i + 1][j + 1], b[i + 1][j]))
    for i in range(n_i - 1):
        for j in (0, n_j - 1):
            part.faces.append((a[i][j], b[i][j], b[i + 1][j], a[i + 1][j]))
    for j in range(n_j - 1):
        for i in (0, n_i - 1):
            part.faces.append((a[i][j], a[i][j + 1], b[i][j + 1], b[i][j]))
    return part


def rot_about_hinge(p, angle):
    """Turns a point about the jaw's hinge (in the up-and-down plane): more than 0 swings what is ahead of the
    hinge down, as the shader opens the jaw."""
    hy, hz = HINGE_Y, HINGE_S - 0.5
    dy, dz = p.y - hy, p.z - hz
    c, sn = math.cos(angle), math.sin(angle)
    return Vector((p.x, hy + dy * c + dz * sn, hz + dz * c - dy * sn))


def palate_point(s, x):
    """The roof of the mouth at x out from the middle."""
    return BODY_SKIN.y_at(s, x, False)


# The game model's numbers (Claude's picks, 2026-11-18; a whale's own GAME dict may change any of them): rings
# along the body and points down each side of it, how much the bends of its lines pull them together, the same
# for the lower jaw; the eye's rows and points round; the baleen's and the mouth wall's columns and rows; the
# fins' rows (placed where their edges bend) and columns; the knobs' points round.
GAME_DEFAULTS = {
    "body_rings": 48, "body_half": 13, "body_gain": 1.6, "body_round": 0.7,
    "jaw_rings": 16, "jaw_half": 7, "jaw_gain": 1.0, "jaw_round": 1.0,
    "eye": (3, 28), "baleen": (16, 1), "fan": (8, 3),
    "flipper_rows": 18, "flipper_cols": 3, "flipper_gain": 2.0,
    "dorsal": (7, 3), "flukes_rows": 30, "flukes_cols": 3, "flukes_gain": 2.0, "knob_around": 6, "body_keep": None,
}


def G(key):
    return dict(GAME_DEFAULTS, **(GAME if "GAME" in globals() and GAME else {}))[key]


def baleen(q):
    """The right side's baleen: a curtain hanging from the edge of the roof of the mouth, inside the lower
    jaw's lips when the mouth is shut. UV: (how far back along the row, 1 - how far down the curtain)."""
    low = q == "lo"
    b0, b1, height, inset = BALEEN
    cols = 14 if low else 60
    rows = 1 if low else 4
    if q == "game":
        cols, rows = G("baleen")
    grid = []
    least = 1e9
    for i in range(cols + 1):
        u = i / cols
        s = lerp(b0, b1, u)
        x = BODY_SKIN.at(s)[2] * inset
        y_top = palate_point(s, x) + 0.004
        # (no deeper than the lower jaw can hold: it closes over it)
        room = lip(s) - JAW_SKIN.y_at(s, x, False)
        hb = min(height(u), 0.8 * room)
        # (and not so deep that it pokes out through the side of the lower jaw, which narrows beneath)
        while hb > 0.002 and JAW_SKIN.x_at(s, y_top - hb) < x + 0.003:
            hb *= 0.9
        least = min(least, room - hb)
        grid.append([Vector((x, y_top - (hb + 0.004) * j / rows, s - 0.5)) for j in range(rows + 1)])
    th = 0.0025
    part = slab("baleen", K_BALEEN, grid, Vector((1.0, 0.0, 0.0)), th,
                lambda i, j: ((i / cols, 1.0 - j / rows), (0.0, 1.0), (K_BALEEN / 10.0, 0.0, 0.0)))
    print("BALEEN room left under it in the shut jaw: %.3f m" % (least * LENGTH))
    return part


def fan(q):
    """The right side's wall of the mouth: built folded up along the roof of the mouth, inside the head (each
    row turned `w` of FAN_OPEN, a sliver, about the hinge); the shader turns each point by w of (the gape -
    FAN_OPEN), so that open it walls the side of the mouth from the roof down to the lower jaw. Green: w."""
    low = q == "lo"
    f0, inset = FAN
    cols = 10 if low else 32
    rows = 2 if low else 8
    if q == "game":
        cols, rows = G("fan")
    s1 = HINGE_S - 0.014
    grid = []
    for i in range(cols + 1):
        s = lerp(f0, s1, i / cols)
        x = BODY_SKIN.at(s)[2] * inset
        p = Vector((x, palate_point(s, x) + 0.004, s - 0.5))
        grid.append([rot_about_hinge(p, FAN_OPEN * j / rows) for j in range(rows + 1)])
    return slab("fan", K_FAN, grid, Vector((1.0, 0.0, 0.0)), 0.002,
                lambda i, j: ((i / cols, 1.0 - j / rows), (0.0, 1.0), (K_FAN / 10.0, j / rows, 1.0)))


def eye(q):
    """The right eye: a small dome set in the side of the head over the corner of the mouth."""
    low = q == "lo"
    part = Part("eye")
    s, y, ball, stands = EYE
    at, out, up = body_frame(s, y)
    rows, around = (3 if low else 9), (8 if low else 28)
    if q == "game":
        rows, around = G("eye")
    dome(part, K_EYE, at, out, up, ball, stands, rows, around)
    if q == "full":
        # (for the shader's cartoon eye, which swells the eye about the middle of its rim, where it meets the skin)
        c = at * LENGTH
        print("EYE where it meets the skin (m, the +X eye) %.4f %.4f %.4f, facing %.4f %.4f %.4f" % (
            c.x, c.y, c.z, out.x, out.y, out.z))
    return part


def flipper_part(q):
    low = q == "lo"
    f = FLIPPER
    at, out, up = body_frame(f["s"], BODY_SKIN.bot(f["s"]) + f["up"] * (BODY_SKIN.top(f["s"]) - BODY_SKIN.bot(f["s"])))
    root = at - out * f["sink"]
    d = Vector(f["dir"]).normalized()
    back = Vector((0.0, 0.0, 1.0))
    chord_way = (back - d * back.dot(d)).normalized()
    # (the way its flat face looks: up and out; twisted a little along it)
    flat = d.cross(chord_way).normalized()
    if flat.y < 0.0:
        flat = -flat

    def mid(r, t):
        reach = f["length"] * r
        return root + d * reach + chord_way * (f["lead"](r) + t * f["chord"](r)) + flat * f.get("bow", 0.0) * math.sin(math.pi * r) * 0.0

    def normal(r, t):
        return flat

    def thick(r, t):
        return f["thick"] * (1.0 - r) ** 0.6 * (0.35 + 0.65 * (1.0 - r)) * airfoil(t)
    if q == "game":
        # (rows where its leading and trailing edges bend: the humpback's knobbed edge, the rounded tip)
        rows = G("flipper_rows")
        lead = f["lead"]
        r_at = game_places(rows, 0.0, 1.0, [lambda r: lead(min(max(r, 0.0), 1.0)) / f["length"],
                                             lambda r: (lead(min(max(r, 0.0), 1.0)) + f["chord"](min(max(r, 0.0), 1.0))) / f["length"]],
                           G("flipper_gain"))
        part = blade("flipper", K_FLIPPER, rows, G("flipper_cols"), mid, normal, thick, lambda r, t: (r, 1.0 - t),
                     r_at=r_at)
    else:
        part = blade("flipper", K_FLIPPER, 16 if low else f.get("rows", 48), 4 if low else f.get("cols", 14), mid, normal, thick,
                     lambda r, t: (r, 1.0 - t))
    tip = mid(1.0, 0.5)
    if q == "full":
        print("FLIPPER tip at x %.3f y %.3f z %.3f (m)" % (tip.x * LENGTH, tip.y * LENGTH, tip.z * LENGTH))
    return part


def dorsal_part(q):
    low = q == "lo"
    d = DORSAL
    s0, s1, tip_s, height, sink = d["s0"], d["s1"], d["tip_s"], d["height"], d["sink"]

    def mid(r, t):
        # (the leading edge sweeps back to the tip; the chord narrows to nothing there)
        lead = s0 + (tip_s - s0) * r ** d["lead_power"]
        trail = lead + (s1 - s0) * (1.0 - r) ** d["trail_power"]
        s = lerp(lead, trail, t)
        y = body_y(s, 0.0) - sink * (1.0 - r) + height * r
        return Vector((0.0, y, s - 0.5))

    def thick(r, t):
        return d["thick"] * (1.0 - r) ** 0.55 * airfoil(t)
    rows, cols = (5 if low else 22), (4 if low else 18)
    r_at = None
    if q == "game":
        rows, cols = G("dorsal")
        # (a little closer towards the tip, where it rounds over)
        r_at = [1.0 - (1.0 - j / rows) ** 1.3 for j in range(rows + 1)]
    return blade("dorsal", K_DORSAL, rows, cols, mid, lambda r, t: Vector((1.0, 0.0, 0.0)),
                 thick, lambda r, t: (r, 1.0 - t), r_at=r_at)


def flukes_part(q):
    low = q == "lo"
    f = FLUKES

    def mid(r, t):
        u = 2.0 * r - 1.0
        a = abs(u)
        lead, trail = f["lead"](a), f["trail"](a)
        s = lerp(lead, trail, t)
        return Vector((u * f["span"], f.get("droop", 0.0) * a * a, s - 0.5))

    def thick(r, t):
        a = abs(2.0 * r - 1.0)
        return f["thick"] * (1.0 - a ** 2) ** 0.7 * airfoil(t)
    rows, cols = (24 if low else f.get("rows", 110)), (4 if low else f.get("cols", 14))
    r_at = None
    if q == "game":
        # (rows where its edges bend: the notch, the tips, a ragged trailing edge's points); one half placed
        # and mirrored, so that both halves match and a row lies on the notch
        rows, cols = G("flukes_rows"), G("flukes_cols")
        half = rows // 2
        rows = half * 2

        def edge(fn):
            return lambda r: fn(min(max(1.0 - 2.0 * r, 0.0), 1.0)) / (2.0 * f["span"])
        left = game_places(half, 0.0, 0.5, [edge(f["lead"]), edge(f["trail"])], G("flukes_gain"))
        left[0], left[-1] = 0.0, 0.5
        r_at = left + [1.0 - r for r in reversed(left[:-1])]
    return blade("flukes", K_FLUKES, rows, cols, mid,
                 lambda r, t: Vector((0.0, 1.0, 0.0)), thick, lambda r, t: (abs(2.0 * r - 1.0), 1.0 - t),
                 closed_root=False, r_at=r_at)


def knob_parts(q):
    """Knobs (a humpback's tubercles), on the upper skin (KNOB) and on the lower jaw (JAW_KNOB). The game model
    keeps every one (they are in its outline), each a low six-sided cap."""
    if q == "lo" or not KNOBS:
        return []
    game = q == "game"
    # (each its own part: knobs that touch would confuse the check of which way a part's faces face)
    made = []
    for k, (where, s, w, ball, stands) in enumerate(KNOBS()):
        if where == "top":
            one = Part("knob_%d" % k)
            at, out = top_frame(s, w)
            ahead = Vector((0.0, 0.0, -1.0))
            if game:
                dome(one, K_KNOB, at - out * 0.0005, out, (ahead - out * ahead.dot(out)).normalized(), ball, stands,
                     1, G("knob_around"), back_ring=False)
            else:
                dome(one, K_KNOB, at - out * 0.0005, out, (ahead - out * ahead.dot(out)).normalized(), ball, stands, 3, 10)
            made.append(one)
        else:
            one = Part("jaw_knob_%d" % k)
            at, out, up = jaw_frame(s, w)
            if game:
                dome(one, K_JAW_KNOB, at - out * 0.0005, out, up, ball, stands, 1, G("knob_around"), back_ring=False)
            else:
                dome(one, K_JAW_KNOB, at - out * 0.0005, out, up, ball, stands, 3, 10)
            made += [one, one.mirrored(one.name + "_left")]
    return made


def make(name, q):
    """q: "full", "game" or "lo"."""
    low = q == "lo"
    parts = []
    body = Part("body")
    if q == "game":
        # rings closer where the lines of the back, the belly and the sides bend (the head, the jaw's corner,
        # the humps and knuckles, the tail stock), and where the full model's own spacing asks for them
        top_line = lambda s: BODY_SKIN.top(s) + extra_top(s, 0.0)
        mean_rd = sum(ring_density(BODY_SKIN.first + (BODY_SKIN.last - BODY_SKIN.first) * (i + 0.5) / 400)
                      for i in range(400)) / 400
        where = game_places(G("body_rings"), BODY_SKIN.first, BODY_SKIN.last,
                            [top_line, BODY_SKIN.bot, lambda s: BODY_SKIN.at(s)[2]], G("body_gain"),
                            lambda s: ring_density(s) / mean_rd)
        keep = G("body_keep")
        if keep:
            # (a run of knuckles: rings on each one's top and shoulders, as the whale's data lists them, in place
            # of the ones placed there by the bends)
            keep = sorted(keep)
            lo, hi = keep[0] - 0.004, keep[-1] + 0.004
            where = sorted([s for s in where if s < lo or s > hi] + keep)
        skin(body, BODY_SKIN, where, G("body_half"), K_BODY, G("body_round"))
    else:
        half = 9 if low else BODY_HALF
        where = places(60 if low else BODY_RINGS, BODY_SKIN.first, BODY_SKIN.last, ring_density)
        skin(body, BODY_SKIN, where, half, K_BODY)
    parts.append(body)
    jaw = Part("jaw")
    jaw_density = lambda s: 1.0 + 3.0 * smooth(0.03, -0.01, s)
    if q == "game":
        jaw_where = game_places(G("jaw_rings"), JAW_SKIN.first, JAW_SKIN.last,
                                [JAW_SKIN.top, JAW_SKIN.bot, lambda s: JAW_SKIN.at(s)[2]], G("jaw_gain"), jaw_density)
        skin(jaw, JAW_SKIN, jaw_where, G("jaw_half"), K_JAW, G("jaw_round"))
    else:
        jaw_where = places(18 if low else JAW_RINGS, JAW_SKIN.first, JAW_SKIN.last, jaw_density)
        skin(jaw, JAW_SKIN, jaw_where, 6 if low else JAW_HALF, K_JAW)
    parts.append(jaw)
    for maker in (eye, baleen, fan, flipper_part):
        one = maker(q)
        parts += [one, one.mirrored(one.name + "_left")]
    if DORSAL:
        parts.append(dorsal_part(q))
    parts.append(flukes_part(q))
    parts += knob_parts(q)

    verts, faces, corners = [], [], []
    told = []
    wrong_all = 0
    for part in parts:
        out, wrong, counted = part.done()
        if not part.name.startswith(("knob_", "jaw_knob_")) or wrong:
            told.append("%s %d/%d wrong" % (part.name, wrong, counted))
        elif part.name in ("knob_0", "jaw_knob_10"):
            told.append("(each knob checked by itself)")
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
    material = bpy.data.materials.get("whale") or bpy.data.materials.new("whale")
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = PREVIEW_COLOUR
    material.diffuse_color = PREVIEW_COLOUR
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
    bpy.ops.mesh.remove_doubles(threshold=1e-6)
    bpy.ops.object.mode_set(mode="OBJECT")
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    xs = [v.co.x for v in mesh.vertices]
    ys = [v.co.y for v in mesh.vertices]
    zs = [v.co.z for v in mesh.vertices]
    print("BUILT %s verts=%d tris=%d" % (name, len(mesh.vertices), tris))
    print("BOX %s (m, Godot axes): x %.3f..%.3f  y %.3f..%.3f  z %.3f..%.3f" % (
        name, min(xs), max(xs), min(zs), max(zs), -max(ys), -min(ys)))
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
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    # (Blender space: the nose is towards +Y, up is +Z; frames in body lengths)
    views = [("right", (-1, 0, 0), (0, 0, 0), 1.1), ("left", (1, 0, 0), (0, 0, 0), 1.1),
             ("top", (0, -0.001, 1), (0, 0, 0), 1.1), ("under", (0, 0.001, -1), (0, 0, 0), 1.1),
             ("front", (0, 1, 0), (0, 0, 0), 0.6), ("back", (0, -1, 0), (0, 0, 0), 0.6),
             ("quarter", (-0.7, 0.6, 0.35), (0, 0, 0), 1.0), ("low_quarter", (-0.6, 0.6, -0.5), (0, 0, 0), 1.0),
             ("head", (-1, 0.25, 0.1), (0, 0.38, 0), 0.36), ("head_top", (-0.3, 0.4, 1), (0, 0.38, 0), 0.36),
             ("head_under", (-0.5, 0.5, -0.7), (0, 0.38, -0.03), 0.36),
             ("tail", (-1, -0.3, 0.5), (0, -0.4, 0), 0.4)]
    for low, obj in ((False, made[0]), (True, made[1])):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if low and view not in ("right", "quarter"):
                continue
            offset = Vector(direction).normalized() * 3.0 * LENGTH
            camera.data.ortho_scale = frame * LENGTH
            camera.location = Vector(target) * LENGTH + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y").to_euler()
            if view == "top":
                camera.rotation_euler = (0.0, 0.0, math.pi / 2)
            elif view == "under":
                camera.rotation_euler = (math.pi, 0.0, -math.pi / 2)
            scene.render.filepath = os.path.join(folder, "%s%s.png" % ("lo_" if low else "", view))
            bpy.ops.render.render(write_still=True)


def main():
    global BODY_SKIN, JAW_SKIN
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    BODY_SKIN = Section(BODY_ROWS)
    rows = []
    for r in JAW_ROWS:
        rows.append((r[0], lip(r[0]) if r[1] is LIP else r[1]) + tuple(r[2:]))
    JAW_SKIN = Section(rows)
    full = make(NAME, "full")
    low = make(NAME + "_lo", "lo")
    game = make(NAME + "_game", "game")
    export_one(full, os.path.join(OUT, NAME + ".glb"))
    export_one(low, os.path.join(OUT, NAME + "_lo.glb"))
    export_one(game, os.path.join(OUT, NAME + "_game.glb"))
    # (in the .blend: the full model, the low one beside it, the game model beyond)
    low.location.x = 1.2 * FLUKES["span"] * 2.0 * LENGTH
    game.location.x = 2.4 * FLUKES["span"] * 2.0 * LENGTH
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, NAME + ".blend"))
    low.location.x = 0.0
    game.location.x = 0.0
    game.hide_render = True
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low])



# The humpback whale itself.

NAME = "humpback_whale"
LENGTH = 14.0
PREVIEW_COLOUR = (0.25, 0.26, 0.28, 1.0)
BODY_HALF = 34
BODY_RINGS = 200
JAW_HALF = 18
JAW_RINGS = 80

# The body and upper jaw: s, top, bottom, half width, widest at (0..1 up), boxiness above, below.
BODY_ROWS = [
    (0.000, 0.003, -0.005, 0.000, 0.40, 2.4, 3.6),
    (0.004, 0.007, -0.007, 0.011, 0.35, 2.4, 3.6),
    (0.015, 0.011, -0.010, 0.019, 0.30, 2.4, 3.6),
    (0.040, 0.016, -0.014, 0.027, 0.30, 2.4, 3.6),
    (0.080, 0.022, -0.018, 0.035, 0.30, 2.4, 3.6),
    (0.120, 0.029, -0.022, 0.042, 0.30, 2.4, 3.6),
    (0.160, 0.037, -0.026, 0.049, 0.32, 2.3, 3.4),
    (0.200, 0.048, -0.030, 0.057, 0.35, 2.2, 3.2),
    (0.228, 0.058, -0.033, 0.063, 0.38, 2.2, 3.0),
    (0.240, 0.063, -0.045, 0.067, 0.42, 2.2, 2.6),
    (0.252, 0.067, -0.094, 0.078, 0.44, 2.2, 2.6),
    (0.270, 0.074, -0.108, 0.088, 0.46, 2.2, 2.5),
    (0.300, 0.084, -0.120, 0.097, 0.50, 2.2, 2.4),
    (0.340, 0.093, -0.128, 0.104, 0.52, 2.2, 2.2),
    (0.400, 0.099, -0.130, 0.106, 0.53, 2.2, 2.2),
    (0.470, 0.098, -0.122, 0.101, 0.53, 2.2, 2.2),
    (0.540, 0.092, -0.102, 0.090, 0.52, 2.2, 2.2),
    (0.620, 0.080, -0.077, 0.072, 0.50, 2.0, 2.1),
    (0.700, 0.064, -0.057, 0.050, 0.50, 1.8, 2.0),
    (0.780, 0.050, -0.043, 0.032, 0.50, 1.7, 1.8),
    (0.850, 0.037, -0.033, 0.020, 0.50, 1.6, 1.7),
    (0.910, 0.025, -0.023, 0.013, 0.50, 1.6, 1.7),
    (0.950, 0.016, -0.015, 0.010, 0.50, 1.8, 1.8),
    (0.970, 0.010, -0.009, 0.008, 0.50, 2.0, 2.0),
    (0.980, 0.005, -0.005, 0.005, 0.50, 2.0, 2.0),
    (0.985, 0.0008, -0.0008, 0.0008, 0.50, 2.0, 2.0),
]
# The lower jaw: LIP for a top means just up inside the upper jaw's edge.
JAW_ROWS = [
    (-0.006, -0.005, -0.012, 0.000, 0.60, 3.0, 2.2),
    (-0.002, LIP, -0.020, 0.015, 0.70, 3.0, 2.2),
    (0.010, LIP, -0.031, 0.026, 0.75, 3.0, 2.2),
    (0.040, LIP, -0.048, 0.037, 0.78, 3.0, 2.2),
    (0.080, LIP, -0.064, 0.046, 0.80, 3.0, 2.2),
    (0.130, LIP, -0.079, 0.055, 0.80, 3.0, 2.2),
    (0.180, LIP, -0.091, 0.063, 0.80, 3.0, 2.2),
    (0.220, LIP, -0.099, 0.069, 0.78, 3.0, 2.2),
    (0.240, LIP, -0.103, 0.071, 0.72, 2.8, 2.2),
    (0.256, -0.050, -0.102, 0.064, 0.60, 2.4, 2.2),
    (0.272, -0.068, -0.100, 0.040, 0.50, 2.2, 2.2),
    (0.285, -0.080, -0.097, 0.000, 0.50, 2.2, 2.2),
]
LIP_IN = 0.0012
# (where on the upper jaw's underside the lips close: this far out of its half width)
LIP_AT = 0.97
# The jaw's hinge (how far along, how high), and how far back the pleated throat runs (the navel).
HINGE_S = 0.245
HINGE_Y = -0.03
NAVEL_S = 0.52
# The eye: where (s, height), the ball's radius, how far it stands out of the skin.
EYE = (0.249, -0.021, 0.008, 0.0015)
# The baleen: from, to (s), how long the plates are along the row (0..1 front to back), how far out under the
# upper jaw's edge (of its half width).
BALEEN = (0.03, 0.232, lambda u: 0.004 + 0.045 * math.sin(math.pi * min(u * 1.12, 1.0)) ** 0.6, 0.86)
# The mouth's wall: from (s), how far out (of the upper jaw's half width); built folded this far open (radians).
FAN = (0.03, 0.7)
FAN_OPEN = 0.03


def _scallops(r):
    """The knobs along a flipper's leading edge (body lengths ahead of its line), from a third of the way out."""
    bumps = max(0.0, math.sin(r * math.pi * 10.5)) ** 0.8
    return -0.0055 * bumps * smooth(0.22, 0.42, r) * (1.0 - smooth(0.9, 0.99, r))


FLIPPER = {
    "s": 0.29, "up": 0.3, "sink": 0.006, "dir": (0.6, -0.45, 0.66), "length": 0.31, "thick": 0.016, "rows": 100, "cols": 10,
    "chord": lambda r: 0.046 * (1.0 - r ** 3) ** 0.6 * (1.0 + 0.15 * math.sin(math.pi * r)) + 0.002,
    "lead": _scallops,
}
# The dorsal fin: small, on a hump (the hump is in extra_top).
DORSAL = {"s0": 0.618, "s1": 0.662, "tip_s": 0.664, "height": 0.02, "sink": 0.005, "lead_power": 1.3,
          "trail_power": 0.75, "thick": 0.01}


def _ragged(a):
    """The flukes' ragged trailing edge: points of uneven size along it (body lengths behind its line)."""
    k = a * 13.0
    i = math.floor(k)
    size = 0.6 + 0.8 * ((math.sin(i * 12.9898 + 4.1) * 43758.5453) % 1.0)
    tooth = (1.0 - abs(2.0 * (k - i) - 1.0)) ** 1.6
    return 0.0035 * size * tooth * smooth(0.08, 0.2, a) * (1.0 - smooth(0.85, 0.97, a))


FLUKES = {
    "span": 0.165, "thick": 0.013, "rows": 140, "cols": 10,
    "lead": lambda a: 0.925 + 0.07 * a ** 1.3,
    "trail": lambda a: (0.99 + 0.016 * math.sin(math.pi * a) ** 0.8 * (1.0 - 0.3 * a) + 0.007 * a
                        - 0.012 * (1.0 - smooth(0.0, 0.08, a)) + _ragged(a)),
}


# The game model: more rows along the flukes for their ragged edge (each point kept), thinner through (two
# columns), fewer rings along the body for that; rings on the knobs along the tail stock (the hollow and the
# top of each).
GAME = {"flukes_rows": 72, "flukes_cols": 2, "body_rings": 32,
        "body_keep": [0.7 + 0.022 * i + d for i in range(8) for d in (0.0, 0.011)]}


def KNOBS():
    """The tubercles: (where, s, x out on the upper jaw or height on the lower jaw, radius, how far it stands)."""
    rng = random.Random(7)
    made = []
    # down the middle of the upper jaw
    for i in range(10):
        s = 0.022 + 0.017 * i + rng.uniform(-0.003, 0.003)
        made.append(("top", s, 0.0, 0.0045, 0.0026))
    # two rows each side of it
    for frac, count, s0, s1 in ((0.42, 9, 0.03, 0.2), (0.74, 8, 0.045, 0.19)):
        for i in range(count):
            s = lerp(s0, s1, i / (count - 1)) + rng.uniform(-0.004, 0.004)
            w = frac * BODY_SKIN.at(s)[2] * rng.uniform(0.92, 1.08)
            size = rng.uniform(0.0036, 0.0048)
            made.append(("top", s, w, size, size * 0.6))
            made.append(("top", s + rng.uniform(-0.003, 0.003), -w * rng.uniform(0.95, 1.05), size, size * 0.6))
    # along the lower lip (each mirrored onto the left side with the jaw)
    for i in range(10):
        s = 0.012 + 0.019 * i + rng.uniform(-0.003, 0.003)
        made.append(("jaw", s, lip(s) - 0.006 - rng.uniform(0.0, 0.003), 0.0042, 0.0024))
    # the cluster at the chin
    for i in range(6):
        s = rng.uniform(-0.002, 0.016)
        y = JAW_SKIN.bot(s) + rng.uniform(0.004, 0.011)
        if JAW_SKIN.x_at(s, y) > 0.004:
            made.append(("jaw", s, y, 0.0045, 0.0026))
    return made


def extra_top(s, x):
    """The top's shapes: a low splash guard ahead of the blowholes, the hump under the dorsal fin, and low knobs
    along the ridge of the tail stock."""
    guard = 0.004 * math.exp(-((s - 0.212) / 0.012) ** 2) * math.exp(-(x / 0.016) ** 2)
    hump = 0.009 * math.exp(-((s - 0.636) / 0.034) ** 2) * math.exp(-(x / 0.03) ** 2)
    k = (s - 0.7) / 0.022
    knuckle = 0.0022 * (0.5 - 0.5 * math.cos(math.tau * k)) * smooth(0.69, 0.72, s) * (1.0 - smooth(0.84, 0.88, s))
    return guard + hump + knuckle * math.exp(-(x / 0.006) ** 2)


def ring_density(s):
    return (1.0 + 1.6 * smooth(0.3, 0.22, s) + 1.5 * math.exp(-((s - 0.21) / 0.02) ** 2)
            + 1.2 * smooth(0.88, 0.95, s) + 1.6 * math.exp(-((s - 0.64) / 0.04) ** 2)
            + 1.2 * smooth(0.68, 0.71, s) * (1.0 - smooth(0.85, 0.88, s)))


if __name__ == "__main__":
    main()
