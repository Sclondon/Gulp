"""Builds the flying fish (creatures/flying_fish) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/flying_fish/tools/build_flying_fish.py
    blender --background --python creatures/flying_fish/tools/build_flying_fish.py -- <preview folder>   # with pictures

Writes creatures/flying_fish/models/flying_fish.glb (the full model, for close pictures) and flying_fish_lo.glb
(far off, phones), and the editable creatures/flying_fish/tools/flying_fish.blend (this folder has a .gdignore).
Each model is one still mesh, its wings spread, with two surfaces: the body (with jaw, eyes and tail; material
"flying_fish", drawn by flying_fish.gdshader) and the see-through fins (dorsal, anal, pelvic and pectoral; material
"flying_fish_fins", drawn by flying_fish_fins.gdshader). The shaders bend it to swim, fold and spread its wings,
work its jaw and gill covers, and draw every marking. It prints a WINDING line for each model: the check that
nothing is inside out; and CLEARANCE lines: how near the folded wings lie to the body.

An Atlantic flyingfish (Cheilopogon melanurus), a four-winged flying fish, 0.3 m from snout to the tip of the
tail's longer lower lobe, nose towards -Z, belly down, its origin at the middle of its length on the line through
snout and tail wrist. Built from the species' anatomy:

- THE BODY: one skin from snout to the root of the tail: a slender torpedo, broad and flat across the back and
  flat-sided, widest and deepest at the shoulder, narrowing to a slim tail wrist; the gill cover a raised plate
  with a crescent rear edge.
- THE HEAD: short and blunt, the snout shorter than the eye; a small mouth at its tip, slanting up, whose LOWER JAW
  is a part of its own (the shader swings it about its hinge); very large EYES, domes set in the sides of the head.
- THE TAIL: deeply forked, stiff, the lower lobe much the longer (it is what sculls the water as the fish takes
  off).
- THE WINGS: the PECTORAL fins, rooted high on the side just behind the gill cover and nearly half the fish's
  length, fifteen rays fanned from a short root; and the PELVIC fins, rooted low on the side behind the middle of
  the body, six rays. Built spread, as in a glide; the shader folds them back along the body (the same
  sums as `wing_where` here, which is how the folded pictures and the CLEARANCE lines are made).
- THE OTHER FINS: a low dorsal fin far back, over the anal fin.

What a point is, for the shader: vertex colour red the part, as a tenth (0 body, 0.1 lower jaw, 0.2 eye,
0.4 dorsal, 0.6 tail, 0.7 anal, 0.8 pelvic, 0.9 pectoral; the numbers the cutthroat trout uses). On the body: UV.x
how far along the fish (0 snout to 1 tail tip), UV.y how high on it (0 belly line to 1 back line); UV2.x how far
round the skin from the back line (metres, + on its right side, - on its left), UV2.y the whole way from back line
to belly line there (metres); green how much of the gill cover's moving edge it is, blue how much it is inside
the mouth. On the jaw: UV as the body's but UV.y from its keel (0) to its lip (1); blue the inside of the mouth.
On an eye: UV where a point is on its round face seen straight on (its middle at 0.5, 0.5; its rim 0.5 away). On
a fin: UV.x along its rays (0 root to 1 edge), UV.y across it counted in rays (0 its leading edge); green 1 on a
left wing, 0 on a right one. (The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.)

Everything here is worked out in body lengths in Godot space (Y up, nose towards -Z) and written out in metres.
The numbers the shaders and the script share (LENGTH, the jaw's hinge, the gill cover's edge, the wings' roots and
angles) are kept in step by hand: change one, change the others. The script prints the wings' numbers as the
shader wants them (the SHADER lines).
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

# Kept in step with flying_fish.gd and flying_fish_motion.gdshaderinc.
LENGTH = 0.3
TAU = math.tau
BODY, JAW, EYE, DORSAL, TAIL, ANAL, PELVIC, PECTORAL = 0, 1, 2, 4, 6, 7, 8, 9
SEE_THROUGH = (DORSAL, ANAL, PELVIC, PECTORAL)
UP = Vector((0.0, 1.0, 0.0))


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
            i = min(bisect.bisect_right(acc, want) - 1, steps - 1)
            span = acc[i + 1] - acc[i]
            t = (want - acc[i]) / span if span > 1e-12 else 0.0
            out.append((lerp(dense[i][0], dense[i + 1][0], t), lerp(dense[i][1], dense[i + 1][1], t), want))
        return out, whole


# The body and upper head: s, top, bottom, half width, widest at, boxiness above, below.
BODY_ROWS = [
    (0.000, 0.006, -0.001, 0.000, 0.40, 2.0, 2.4),
    (0.004, 0.015, -0.005, 0.013, 0.40, 2.0, 2.4),
    (0.014, 0.024, -0.008, 0.022, 0.40, 2.1, 2.8),
    (0.030, 0.033, -0.011, 0.030, 0.38, 2.2, 3.0),
    (0.045, 0.039, -0.016, 0.035, 0.40, 2.3, 3.0),
    (0.060, 0.044, -0.034, 0.039, 0.50, 2.4, 2.6),
    (0.080, 0.049, -0.043, 0.043, 0.52, 2.5, 2.5),
    (0.110, 0.054, -0.052, 0.047, 0.54, 2.6, 2.5),
    (0.150, 0.058, -0.061, 0.050, 0.55, 2.7, 2.5),
    (0.200, 0.061, -0.068, 0.052, 0.56, 2.8, 2.5),
    (0.280, 0.063, -0.073, 0.051, 0.56, 2.8, 2.5),
    (0.380, 0.062, -0.073, 0.048, 0.56, 2.7, 2.5),
    (0.480, 0.057, -0.067, 0.043, 0.56, 2.6, 2.4),
    (0.580, 0.049, -0.056, 0.035, 0.55, 2.4, 2.3),
    (0.660, 0.039, -0.043, 0.026, 0.53, 2.2, 2.2),
    (0.720, 0.029, -0.031, 0.017, 0.50, 2.1, 2.1),
    (0.757, 0.023, -0.024, 0.0110, 0.50, 2.0, 2.0),
    (0.775, 0.024, -0.026, 0.0065, 0.50, 2.0, 2.0),
    (0.792, 0.027, -0.030, 0.0030, 0.50, 2.0, 2.0),
    (0.806, 0.023, -0.026, 0.0012, 0.50, 2.0, 2.0),
    (0.812, 0.014, -0.016, 0.000, 0.50, 2.0, 2.0),
]
# The lower jaw and chin.
JAW_ROWS = [
    (0.003, -0.004, -0.008, 0.000, 0.75, 3.5, 2.0),
    (0.007, -0.004, -0.013, 0.011, 0.75, 3.5, 2.0),
    (0.016, -0.006, -0.018, 0.019, 0.78, 3.5, 2.0),
    (0.030, -0.009, -0.024, 0.026, 0.80, 3.5, 2.0),
    (0.045, -0.014, -0.031, 0.031, 0.80, 3.0, 2.0),
    (0.058, -0.028, -0.037, 0.027, 0.70, 2.4, 2.1),
    (0.068, -0.037, -0.041, 0.012, 0.50, 2.0, 2.0),
    (0.072, -0.040, -0.041, 0.000, 0.50, 2.0, 2.0),
]
BODY_SKIN = Section(BODY_ROWS)
JAW_SKIN = Section(JAW_ROWS)


def gill_edge(h):
    """Where the gill cover's rear edge is (s) at a height on the body (0 belly to 1 back): a crescent."""
    return 0.19 - 0.2 * (h - 0.45) ** 2


def gill_plate(s, h):
    """How far the gill cover stands out from the skin behind it (body lengths), and how much of its moving
    edge a point is (0..1)."""
    edge = gill_edge(h)
    band = smooth(0.06, 0.2, h) * (1.0 - smooth(0.74, 0.88, h))
    behind = 1.0 - smooth(edge - 0.004, edge + 0.007, s)
    raised = 0.0035 * smooth(0.11, 0.17, s) * behind * band
    moving = smooth(0.13, edge, s) * behind * band
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


def body_gap(p):
    """How far a point is outside the body's skin (body lengths; less than 0 inside it), in the slice of the
    body it is beside."""
    s = p.z + 0.5
    if s <= BODY_SKIN.first or s >= BODY_SKIN.last:
        return 1.0
    side, _whole = BODY_SKIN.outline(s, 48)
    x, y = abs(p.x), p.y
    least = 1e9
    for (x0, y0, _a), (x1, y1, _b) in zip(side, side[1:]):
        dx, dy = x1 - x0, y1 - y0
        u = max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / max(dx * dx + dy * dy, 1e-18)))
        least = min(least, math.hypot(x - x0 - dx * u, y - y0 - dy * u))
    inside = BODY_SKIN.bot(s) < y < BODY_SKIN.top(s) and x < BODY_SKIN.x_at(s, y)
    return -least if inside else least


class Part:
    """One closed piece of the fish: points (body lengths), what each is for the shader, and four-cornered
    faces. `done` welds it, turns every face outward and checks that."""

    def __init__(self, name, kind):
        self.name = name
        self.kind = kind
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
        other = Part(name, self.kind)
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
        # leading tip, a four-cornered face has three corners in that plane: cut it from its fourth corner, or
        # whoever cuts it in two later may leave a triangle lying flat in the plane, back to back with its twin
        # from the other side)
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


def flip_wing(d):
    return d[0], d[1], (d[2][0], 1.0, d[2][2])


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
                roof = smooth(0.4, 0.12, (y - bot) / max(yc - bot, 1e-9)) * smooth(0.052, 0.04, s)
                ring.append(part.add((sign * x, y, s - 0.5), (s, 1.0 - h),
                                     (sign * arc * LENGTH, 1.0 - whole * LENGTH), (0.0, moving, roof)))
            else:
                yc = bot + section.at(s)[3] * (top - bot)
                inside = smooth(0.55, 0.92, (y - yc) / max(top - yc, 1e-9)) if y > yc else 0.0
                inside *= smooth(0.056, 0.044, s)
                ring.append(part.add((sign * x, y, s - 0.5), (s, 1.0 - h),
                                     (sign * x * LENGTH, 1.0), (JAW / 10.0, 0.0, inside)))
        rings.append(ring)
    part.loft(rings)


def body_places(low):
    head = 16 if low else 64
    rest = 26 if low else 96
    places = [0.2 * (i / head) ** 1.35 for i in range(head)]
    places += [lerp(0.2, BODY_SKIN.last, i / rest) for i in range(rest + 1)]
    return places


EYE_AT = (0.075, 0.011)


def eye(low):
    """The right eye: a dome set in the side of the head. Very large, as a flying fish's is."""
    part = Part("eye", EYE)
    at, out, up = body_frame(*EYE_AT)
    along = up.cross(out).normalized()
    ball = 0.07
    reach = math.radians(25.0)
    centre = at - out * (ball - 0.0052)
    rows = 4 if low else 10
    around = 12 if low else 36
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


def fin(name, kind, rays, where, thick, low, rows=0, ridge_from=0.0, ridge=0.0011):
    """A fin: `rays` rays side by side; `where(t, r)` gives the middle of its thickness at ray t (0 its leading
    edge to 1 its trailing edge) and r along that ray (0 root to 1 edge), and the way its flat side faces
    there; `thick` at its root."""
    part = Part(name, kind)
    per_ray = 1 if low else 4
    rows = rows or (3 if low else 12)
    cols = max(rays * per_ray, 6)
    left, right = [], []
    for i in range(cols + 1):
        t = i / cols
        ridged = 0.5 + 0.5 * math.cos(TAU * (t * rays - 0.5)) if (rays > 1 and not low) else 0.0
        edge = min(1.0, t / 0.06) ** 0.5 * min(1.0, (1.0 - t) / 0.1) ** 0.5
        a, c = [], []
        for j in range(rows + 1):
            r = j / rows
            taper = 1.0 - r
            th = edge * (taper ** 0.5) * (thick * (0.1 + 0.9 * taper ** 1.6) + ridge * ridged * smooth(ridge_from, ridge_from + 0.14, r) * (1.0 - smooth(0.8, 1.0, r)))
            mid, normal = where(t, r)
            data = ((r, 1.0 - t * rays), (0.0, 1.0), (kind / 10.0, 0.0, 0.0))
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


def flat_fin(base, direction, length):
    """`where` for a fin on the middle plane: rays fanned from the line `base(t)`, each going the way
    `direction(t)` for `length(t)`."""
    side = Vector((1.0, 0.0, 0.0))
    return lambda t, r: (base(t) + direction(t).normalized() * (length(t) * r), side)


def raked(degrees_from, degrees_to, down=False):
    """Rays leaning back: the angle each makes with the fish's length, from its leading ray to its trailing."""
    def direction(t):
        a = math.radians(lerp(degrees_from, degrees_to, t))
        return Vector((0.0, -math.sin(a) if down else math.sin(a), math.cos(a)))
    return direction


# The wings (the right one of each pair; the left is its mirror picture). `at`: the root of the leading ray;
# `base`: how long the root is, from the leading ray's root to the trailing ray's; `fan`: the angle between the
# leading and the trailing ray, spread; `spread` and `folded`: how the fin is held, as three angles (how far
# its leading ray is swept back from straight out to the side, how far that ray is lifted above level, and how
# far the fin is rolled about that ray, 0 flat with its trailing edge behind, a quarter turn its trailing edge
# straight down); `shut`: how much of the fan is left when it is folded; `hug`: how far the folded rays bow in
# towards the body (per body length squared). The shader has the same numbers (in metres).
def wing_root(s, up, sunk):
    y = BODY_SKIN.bot(s) + up * (BODY_SKIN.top(s) - BODY_SKIN.bot(s))
    return Vector((body_x(s, y) - sunk, y, s - 0.5))


PECTORAL_WING = {
    "name": "pectoral", "kind": PECTORAL, "rays": 15, "at": wing_root(0.214, 0.8, 0.003), "base": 0.025,
    "fan": math.radians(62.0), "spread": (math.radians(14.0), math.radians(9.0), math.radians(4.0)),
    "folded": (math.radians(88.0), math.radians(-1.5), math.radians(102.0)), "shut": 0.02, "hug": 0.12,
    "long": curve([(0.0, 0.44), (0.08, 0.455), (0.25, 0.405), (0.5, 0.31), (0.75, 0.225), (1.0, 0.16)]),
    "thick": 0.0045,
}
PELVIC_WING = {
    "name": "pelvic", "kind": PELVIC, "rays": 6, "at": wing_root(0.425, 0.13, 0.003), "base": 0.016,
    "fan": math.radians(55.0), "spread": (math.radians(30.0), math.radians(-7.0), math.radians(0.0)),
    "folded": (math.radians(87.8), math.radians(5.0), math.radians(62.0)), "shut": 0.03, "hug": 0.2,
    "long": curve([(0.0, 0.165), (0.2, 0.205), (0.5, 0.195), (0.75, 0.16), (1.0, 0.115)]),
    "thick": 0.004,
}


def wing_frame(angles):
    """The way a wing's leading ray goes, the way across it towards its trailing edge, and the way its flat
    side faces, from its three angles."""
    sweep, lift, roll = angles
    a = Vector((math.cos(sweep) * math.cos(lift), math.sin(lift), math.sin(sweep) * math.cos(lift)))
    b0 = a.cross(UP).normalized()
    n0 = b0.cross(a)
    return a, b0 * math.cos(roll) - n0 * math.sin(roll), n0 * math.cos(roll) + b0 * math.sin(roll)


def wing_where(wing, wings):
    """`where` for a wing held `wings` open (0 folded back along the body, 1 spread). The shader's
    `wing_pose` does these sums backwards from the spread model and forwards again."""
    held = [lerp(f, s, wings) for f, s in zip(wing["folded"], wing["spread"])]
    a, b, n = wing_frame(held)

    def where(t, r):
        angle = t * wing["fan"] * lerp(wing["shut"], 1.0, wings)
        along = wing["long"](t) * r
        bow = wing["hug"] * (1.0 - wings) * along * along
        return wing["at"] + b * (wing["base"] * t) + (a * math.cos(angle) + b * math.sin(angle)) * along + n * bow, n
    return where


def wing(spec, wings, low):
    return fin(spec["name"], spec["kind"], spec["rays"], wing_where(spec, wings), spec["thick"], low,
               5 if low else 14)


def clearance(part):
    """How near a folded wing lies to the body (mm): the least and the greatest gap between the body's skin
    and the wing's points from three tenths of the way out along its rays (nearer its root it is inside the body,
    where it grows from)."""
    gaps = [body_gap(p) * LENGTH * 1000.0 for p, d in zip(part.verts, part.data) if d[0][0] >= 0.3]
    return min(gaps), max(gaps)


def fins(low, wings):
    made = []
    top, bot = BODY_SKIN.top, BODY_SKIN.bot
    # The dorsal fin: twelve rays, low, far back, its leading rays the tallest.
    made.append(fin("dorsal", DORSAL, 12, flat_fin(
        lambda t: Vector((0.0, top(0.585 + 0.115 * t) - 0.005, 0.585 + 0.115 * t - 0.5)), raked(58.0, 20.0),
        lambda t: (0.066 - 0.044 * t ** 0.8) * (0.86 + 0.14 * smooth(0.0, 0.14, t))), 0.0055, low))
    # The tail: deeply forked, the lower lobe the longer.

    def tail_long(t):
        a = abs(2.0 * t - 1.0)
        long = lerp(0.04, 0.174 if t < 0.5 else 0.29, a ** 1.55)
        if a > 0.88:
            long *= 1.0 - 0.1 * ((a - 0.88) / 0.12) ** 2
        return long
    made.append(fin("tail", TAIL, 22, flat_fin(
        lambda t: Vector((0.0, lerp(0.0225, -0.0245, t), 0.776 - 0.012 * (2.0 * t - 1.0) ** 2 - 0.5)),
        lambda t: Vector((0.0, math.sin(math.radians(lerp(38.0, -27.0, t))), math.cos(math.radians(lerp(38.0, -27.0, t))))),
        tail_long), 0.014, low, 0, 0.25))
    # The anal fin: nine rays, under the rear of the dorsal.
    made.append(fin("anal", ANAL, 9, flat_fin(
        lambda t: Vector((0.0, bot(0.632 + 0.075 * t) + 0.005, 0.632 + 0.075 * t - 0.5)), raked(52.0, 20.0, True),
        lambda t: (0.044 - 0.026 * t ** 0.8) * (0.86 + 0.14 * smooth(0.0, 0.14, t))), 0.005, low))
    # The wings.
    for spec in (PELVIC_WING, PECTORAL_WING):
        right = wing(spec, wings, low)
        made += [right, right.mirrored(spec["name"] + "_left", flip_wing)]
        if wings == 0.0 and not low:
            print("CLEARANCE %s fin folded, to the body: least %.2f mm, greatest %.2f mm" % ((spec["name"],) + clearance(right)))
    return made


def make(name, low, wings=1.0):
    parts = []
    body = Part("body", BODY)
    skin(body, BODY_SKIN, body_places(low), 9 if low else 30, BODY)
    parts.append(body)
    jaw = Part("jaw", JAW)
    jaw_rings = 10 if low else 30
    skin(jaw, JAW_SKIN, [lerp(JAW_SKIN.first, JAW_SKIN.last, (i / jaw_rings) ** 1.25) for i in range(jaw_rings + 1)],
         5 if low else 12, JAW)
    parts.append(jaw)
    ball = eye(low)
    parts += [ball, ball.mirrored("eye_left", lambda d: d)]
    parts += fins(low, wings)

    verts, faces, corners, slots = [], [], [], []
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
            slots.append(1 if part.kind in SEE_THROUGH else 0)
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
    for slot, (label, shade) in enumerate((("flying_fish", (0.55, 0.62, 0.72, 1.0)), ("flying_fish_fins", (0.2, 0.26, 0.36, 1.0)))):
        material = bpy.data.materials.get(label) or bpy.data.materials.new(label)
        material.use_nodes = True
        bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Base Color"].default_value = shade
        material.diffuse_color = shade
        mesh.materials.append(material)
    for poly in mesh.polygons:
        poly.use_smooth = True
        poly.material_index = slots[poly.index]
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
    return obj


def export_one(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", export_yup=True, use_selection=True,
        export_animations=False, export_vertex_color="ACTIVE", export_texcoords=True,
    )


def tell_shader():
    """The wings' numbers as flying_fish_motion.gdshaderinc wants them (metres and radians)."""
    for spec in (PECTORAL_WING, PELVIC_WING):
        label = spec["name"].upper()
        at = spec["at"] * LENGTH
        print("SHADER const vec3 %s_AT = vec3(%.5f, %.5f, %.5f);" % (label, at.x, at.y, at.z))
        print("SHADER const float %s_BASE = %.5f; const float %s_FAN = %.5f; const float %s_RAYS = %.1f; const float %s_SHUT = %.3f; const float %s_HUG = %.5f;" % (
            label, spec["base"] * LENGTH, label, spec["fan"], label, spec["rays"], label, spec["shut"], label, spec["hug"] / LENGTH))
        print("SHADER const vec3 %s_SPREAD = vec3(%.5f, %.5f, %.5f);" % ((label,) + tuple(spec["spread"])))
        print("SHADER const vec3 %s_FOLDED = vec3(%.5f, %.5f, %.5f);" % ((label,) + tuple(spec["folded"])))


def render(folder, shown):
    """Pictures of each (label, object, the views wanted or None for all of them)."""
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
    views = [("right", (1, 0, 0), (0, 0, 0), 0.36), ("left", (-1, 0, 0), (0, 0, 0), 0.36),
             ("top", (0, -0.001, 1), (0, 0, 0), 0.5), ("under", (0, 0.001, -1), (0, 0, 0), 0.5),
             ("front", (0, 1, 0), (0, 0, 0), 0.4), ("back", (0, -1, 0), (0, 0, 0), 0.4),
             ("quarter", (0.7, 0.6, 0.35), (0, 0, 0), 0.4), ("low_quarter", (0.6, 0.6, -0.5), (0, 0, 0), 0.4),
             ("head", (1, 0.15, 0.05), (0, 0.11, 0), 0.11), ("head_under", (0.5, 0.5, -0.7), (0, 0.11, -0.005), 0.11),
             ("tail", (1, -0.2, 0.1), (0, -0.1, 0), 0.16)]
    everything = [obj for _label, obj, _wanted in shown]
    for label, obj, wanted in shown:
        for other in everything:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if wanted is not None and view not in wanted:
                continue
            offset = Vector(direction).normalized() * 10.0
            camera.data.ortho_scale = frame
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "X" if view in ("top", "under") else "Y").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % (label, view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    full = make("flying_fish", False)
    low = make("flying_fish_lo", True)
    tell_shader()
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, "flying_fish.glb"))
    export_one(low, os.path.join(OUT, "flying_fish_lo.glb"))
    low.location.x = 0.4
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "flying_fish.blend"))
    low.location.x = 0.0
    # The wings folded and half open, as the shader holds them: for the CLEARANCE lines and the pictures only
    # (made after the .blend is saved, so they are not in it).
    folded = make("flying_fish_folded", False, 0.0)
    if PREVIEW:
        half = make("flying_fish_half", False, 0.5)
        low_folded = make("flying_fish_lo_folded", True, 0.0)
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [("", full, None), ("folded_", folded, None), ("half_", half, ("right", "top", "front", "quarter")),
                         ("lo_", low, ("right", "top", "quarter")), ("lo_folded_", low_folded, ("right", "top"))])


if __name__ == "__main__":
    main()
