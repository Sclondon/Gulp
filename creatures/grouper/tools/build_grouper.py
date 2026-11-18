"""Builds the broomtail grouper (creatures/grouper) and exports it for Godot.

Run from the game's root (or from anywhere: it writes beside itself):
    blender --background --factory-startup --python creatures/grouper/tools/build_grouper.py
    blender --background --factory-startup --python creatures/grouper/tools/build_grouper.py -- <preview folder>

It writes creatures/grouper/models/grouper.glb (the full model) and grouper_lo.glb (far off, phones, many of
them), and the editable creatures/grouper/tools/grouper.blend holding both (this folder has a .gdignore). Each
model is one still mesh with one surface: the shader (grouper.gdshader) bends it to swim, works its mouth and
fins, and draws every marking. It prints a WINDING line for each model (the check that nothing is inside out), a
SHAPE line (the numbers the shader and the script share) and CLEARANCE lines (the paired fins against the body).
With a preview folder it also renders both models from every side.

The broomtail grouper (Mycteroperca xenarcha) of the eastern Pacific reefs: a robust grouper about 1.2 m long,
a big thick-lipped mouth with the lower jaw standing forward, one long dorsal (spiny then soft), and a square
tail whose rays stand out past its edge: the ragged "broom" (its markings are drawn by the shader).

How it is put together (the method is the sockeye salmon's, GameCommon godot/sockeye-salmon):

- THE BODY: one skin from snout to the root of the tail (rows of top line, bottom line and half width, lofted).
  Ahead of the jaw's hinge it is the upper head only, flat underneath: the roof of the mouth.
- THE LOWER JAW: a part of its own, from its tip back into the throat. **It is built swung open** (GAPE_MAX
  about its hinge, as at `gape` 1) and the shader shuts it: shut, its lip lies just up inside the upper lip.
- THE MOUTH'S SIDES: on each side a thin skin from the upper lip to the lower jaw's lip (MEMBRANE), built spread
  as the mouth is when wide open, so that the open mouth is a round tube and not a bird's beak; shut, the shader
  folds it to nothing between the lips.
- A MAXILLA on each side (the plate along the upper lip: built shut; the shader swings its rear end down and
  forward as the mouth opens), EYES, and the FINS, thin closed solids with their rays as ridges: a spiny first
  dorsal (its edge cut in between the spines; the shader can fold it), a soft second dorsal, the tail, the anal
  fin, and a pair each of pelvic fins (under the pectorals, as a bass has them) and big round pectoral fins.

What a point is, for the shader: vertex colour red the part, as a tenth (0 body, 0.1 lower jaw, 0.2 eye, 0.3
maxilla, 0.4 spiny dorsal, 0.5 soft dorsal, 0.6 tail, 0.7 anal, 0.8 pelvic, 0.9 pectoral, 1.0 the mouth's side
skin). On the body: UV.x how far along the fish (0 the jaw's tip to 1 the tail's tip), UV.y how high on it (0
bottom line to 1 back line); UV2.x how far round the skin from the back line (metres, + on its right side, - on
its left), UV2.y the whole way from back line to belly line there; green how much of the gill cover's moving edge
it is, blue how much it is the roof of the mouth. On the jaw: UV as the body's (where it is when shut) but UV.y
from its keel (0) to its lip (1); blue the inside of the mouth. On an eye: UV where a point is on its round face.
On a maxilla: UV.x along the fish, UV.y across it; UV2 where the point is from the plate's front end (metres: up,
back). On a fin: UV.x along its rays (0 root to 1 edge), UV.y across it counted in rays; on the fins of the
middle line UV2 is where the point is from its ray's root (metres: up, back), on the paired fins UV2 and blue are
the way the fin's flat side faces. On the mouth's side skin: UV.x along the fish, UV.y from the upper lip (0) to
the lower (1), UV2.x how far out it is when shut (metres), blue its inner face. (The glTF writer flips V: what is
written here is 1 - v, so that Godot reads v.)

Everything here is worked out in body lengths in Godot space (Y up, nose towards -Z) and written out in metres.
The numbers the shader shares (LENGTH, HINGE_S, HINGE_Y, GILL_S, GAPE_MAX) are kept in step by hand: change one
here, copy the SHAPE line's numbers to the top of the shader.
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
TAU = math.tau
BODY, JAW, EYE, MAXILLA, SPINY, SOFT, TAIL, ANAL, PELVIC, PECTORAL, MEMBRANE = range(11)

# The broomtail grouper (Mycteroperca xenarcha). Kept in step with grouper.gd and grouper.gdshader.
NAME = "grouper"
LENGTH = 1.2
# All in body lengths; s is how far along (0 the jaw's tip, 1 the tail's tip), heights are from the middle line.
SP = {
    # The back's line, the underside's line (the roof of the mouth as far as the jaw's hinge, then the throat
    # and belly) and the half width: a robust, longish fish, the lower jaw standing out ahead of the snout.
    "top": [(0.014, 0.008), (0.018, 0.018), (0.035, 0.032), (0.07, 0.052), (0.12, 0.076), (0.18, 0.100), (0.26, 0.122),
            (0.34, 0.134), (0.44, 0.136), (0.54, 0.128), (0.64, 0.108), (0.72, 0.082), (0.78, 0.062), (0.82, 0.052),
            (0.862, 0.050)],
    "bot": [(0.014, 0.000), (0.018, -0.006), (0.035, -0.011), (0.07, -0.020), (0.11, -0.030), (0.145, -0.040),
            (0.165, -0.082), (0.195, -0.110), (0.26, -0.134), (0.34, -0.150), (0.44, -0.152), (0.54, -0.140),
            (0.64, -0.110), (0.72, -0.082), (0.78, -0.062), (0.82, -0.052), (0.862, -0.050)],
    "hw": [(0.014, 0.0), (0.018, 0.018), (0.035, 0.032), (0.07, 0.048), (0.12, 0.064), (0.18, 0.076), (0.26, 0.084),
           (0.34, 0.086), (0.44, 0.082), (0.54, 0.072), (0.64, 0.056), (0.72, 0.040), (0.78, 0.028), (0.82, 0.020),
           (0.862, 0.014)],
    # The lower jaw's underside, from its tip (well ahead of the snout) back into the throat.
    "chin": [(0.000, -0.002), (0.005, -0.018), (0.03, -0.040), (0.07, -0.062), (0.11, -0.082), (0.145, -0.098),
             (0.175, -0.108), (0.22, -0.116)],
    "jaw_wide": 0.95,
    "hinge": (0.145, -0.044),
    "gill_s": 0.30,
    "gape_max": 0.8,
    "mouth_front": 0.22,
    "mouth_bulge": 0.4,
    "eye": (0.10, 0.038, 0.026, 0.0048),
    "maxilla": (0.026, 0.158, 0.0055, 0.016),
    # Eleven spines, the third and fourth the longest, running straight into a long soft dorsal.
    "spiny": (0.33, 0.58, 11, [(0.0, 0.025), (0.12, 0.050), (0.25, 0.062), (0.5, 0.056), (1.0, 0.046)], 68.0, 50.0),
    "spiny_cut": 0.16,
    "soft": (0.58, 0.775, 16, [(0.0, 0.050), (0.2, 0.070), (0.5, 0.080), (0.8, 0.066), (1.0, 0.036)], 62.0, 22.0),
    "anal": (0.635, 0.75, 14, [(0.0, 0.030), (0.25, 0.075), (0.55, 0.085), (1.0, 0.040)], 62.0, 22.0),
    # The broom: a square tail whose rays stand out past the skin between them, a ragged edge.
    "tail": (0.862, 0.134, 0.172, 2.0, 20.0, 17, 0.09),
    "pelvic": (0.33, 0.10, 6),
    "pectoral": (0.312, 0.14, 17, 0.33),
    "detail": 0.95,
}

HINGE_S, HINGE_Y = SP["hinge"]
GILL_S = SP["gill_s"]
GAPE_MAX = SP["gape_max"]
JAW_TIP = SP["chin"][0][0]


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


def body_rows():
    """The body's rows from the species' three lines: s, top, bottom, half width, widest at, boxiness above and
    below. Ahead of the jaw's hinge the underside is the flat roof of the mouth."""
    top, bot, hw = curve(SP["top"]), curve(SP["bot"]), curve(SP["hw"])
    places = sorted(set([p[0] for p in SP["top"]] + [p[0] for p in SP["bot"]] + [p[0] for p in SP["hw"]]))
    rows = []
    for s in places:
        behind = smooth(HINGE_S - 0.005, HINGE_S + 0.07, s)
        rows.append((s, top(s), bot(s), hw(s), lerp(0.3, 0.52, behind), lerp(2.0, 2.25, behind), lerp(3.0, 2.3, behind)))
    # (the first row is the snout's tip: a point)
    first = rows[0]
    rows[0] = (first[0], first[1], first[2], 0.0, 0.3, 2.0, 2.6)
    # The root of the tail: the skin thins to nothing inside the tail fin, flaring a little where its rays begin.
    r = rows[-1]
    pd_top, pd_bot, w = r[1], r[2], r[3]
    for ds, k, wk in ((0.023, 1.07, 0.6), (0.048, 1.13, 0.3), (0.068, 1.0, 0.12), (0.076, 0.66, 0.0)):
        rows.append((r[0] + ds, pd_top * k, pd_bot * k, w * wk, 0.5, 2.0, 2.0))
    return rows


BODY_SKIN = Section(body_rows())


def lip(s):
    """The lower jaw's lip line when shut: just up inside the upper lip."""
    return BODY_SKIN.bot(s) + 0.002


def jaw_rows():
    """The lower jaw and throat, as the body's rows (shut): its top the lip line as far back as the hinge, then
    down into the throat; its bottom the chin's line; nearly as wide as the head above it."""
    chin = curve(SP["chin"])
    end = SP["chin"][-1][0]
    rows = [(JAW_TIP, chin(JAW_TIP) + 0.006, chin(JAW_TIP), 0.0, 0.75, 3.5, 2.0)]
    places = [JAW_TIP + 0.004]
    n = 9
    places += [lerp(JAW_TIP + 0.012, HINGE_S, i / n) for i in range(n + 1)]
    places += [lerp(HINGE_S, end, t) for t in (0.3, 0.6, 0.85)]
    for s in places:
        back = smooth(HINGE_S, end, s)
        bottom = chin(s)
        top = lerp(lip(min(s, HINGE_S)), bottom + 0.004, back)
        wide = SP["jaw_wide"] * BODY_SKIN.at(max(s, BODY_SKIN.first + 0.004))[2]
        # (its tip is blunt; its rear narrows into the throat)
        wide *= smooth(JAW_TIP - 0.004, JAW_TIP + 0.03, s) ** 0.5 * (1.0 - back) ** 0.7
        rows.append((s, top, bottom, max(wide, 0.002), lerp(0.78, 0.5, back), lerp(3.5, 2.0, back), 2.0))
    rows.append((end + 0.006, chin(end) + 0.002, chin(end) + 0.001, 0.0, 0.5, 2.0, 2.0))
    return rows


JAW_SKIN = Section(jaw_rows())


def jaw_weight(s):
    """How much of the jaw's swing a place takes (the throat behind the hinge stays): the shader's sum."""
    return 1.0 - smooth(HINGE_S - 0.03, HINGE_S + 0.07, s)


def swing(p, a):
    """A point turned about the jaw's hinge by `a` radians, the way the mouth opens: the shader's sum."""
    dy, dz = p.y - HINGE_Y, p.z - (HINGE_S - 0.5)
    c, sn = math.cos(a), math.sin(a)
    return Vector((p.x, HINGE_Y + dy * c + dz * sn, HINGE_S - 0.5 + dz * c - dy * sn))


def gill_edge(h):
    """Where the gill cover's rear edge is (s) at a height on the body (0 belly to 1 back): a crescent."""
    return GILL_S - 0.25 * (h - 0.45) ** 2


def gill_plate(s, h):
    """How far the gill cover stands out from the skin behind it (body lengths), and how much of its moving
    edge a point is (0..1)."""
    edge = gill_edge(h)
    band = smooth(0.06, 0.2, h) * (1.0 - smooth(0.78, 0.9, h))
    behind = 1.0 - smooth(edge - 0.004, edge + 0.008, s)
    raised = 0.006 * smooth(GILL_S - 0.086, GILL_S - 0.018, s) * behind * band
    moving = smooth(GILL_S - 0.068, edge, s) * behind * band
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
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-6 * LENGTH)
        # (where a skin closes to a line on the middle plane, or a fin on that plane thins to nothing at its
        # leading tip, a four-cornered face has three corners in that plane: cut it from its fourth corner, or
        # whoever cuts it in two later may leave a triangle lying flat in the plane, back to back with its twin)
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


def flip_side(d):
    return d[0], (-d[1][0], d[1][1]), d[2]


def same(d):
    return d


def skin(part, section, places, half, kind):
    """Lofts a Section into a Part. `kind` is BODY or JAW (the jaw is swung open as it is made)."""
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
            yc = bot + section.at(s)[3] * (top - bot)
            if kind == BODY:
                raised, moving = gill_plate(s, h)
                x += raised * (0.0 if ends else 1.0)
                # the roof of the mouth: the flat underside of the upper head, ahead of the jaw's hinge
                roof = smooth(0.4, 0.12, (y - bot) / max(yc - bot, 1e-9)) * smooth(HINGE_S + 0.015, HINGE_S - 0.012, s)
                ring.append(part.add((sign * x, y, s - 0.5), (s, 1.0 - h),
                                     (sign * arc * LENGTH, 1.0 - whole * LENGTH), (0.0, moving, roof)))
            else:
                inside = smooth(0.5, 0.9, (y - yc) / max(top - yc, 1e-9)) if y > yc else 0.0
                inside *= smooth(HINGE_S + 0.03, HINGE_S, s)
                p = swing(Vector((sign * x, y, s - 0.5)), GAPE_MAX * jaw_weight(s))
                ring.append(part.add(p, (s, 1.0 - h), (sign * x * LENGTH, 1.0), (JAW / 10.0, 0.0, inside)))
        rings.append(ring)
    part.loft(rings)


def body_places(low):
    k = SP["detail"]
    head = 18 if low else int(72 * k)
    rest = 24 if low else int(84 * k)
    behind = GILL_S + 0.014
    first = BODY_SKIN.first
    places = [first + (behind - first) * (i / head) ** 1.35 for i in range(head)]
    places += [lerp(behind, BODY_SKIN.last, i / rest) for i in range(rest + 1)]
    return places


def membrane(low):
    """The skin at the right side of the mouth, from the upper lip to the lower jaw's lip, spread as when the
    mouth is wide open (the jaw's lip swung GAPE_MAX about the hinge) and bulged out a little: it makes the open
    mouth a tube. A thin closed solid; its inner face is the mouth's inside."""
    part = Part("membrane")
    stations = 6 if low else 22
    rows = 3 if low else 8
    s0 = lerp(JAW_TIP, HINGE_S, SP["mouth_front"])
    s1 = HINGE_S - 0.004
    rings = []
    for i in range(stations + 1):
        s = lerp(s0, s1, i / stations)
        thick = 0.0 if i in (0, stations) else 0.003
        a_full = GAPE_MAX * jaw_weight(s)
        y_lip = lip(s)
        x_up = max(body_x(s, y_lip + 0.003) - 0.002, 0.002)
        x_low = max(JAW_SKIN.at(s)[2] * 0.9, 0.002)
        outer, inner = [], []
        for k in range(rows + 1):
            w = k / rows
            x = lerp(x_up, x_low, w)
            p = swing(Vector((x, lerp(y_lip + 0.003, y_lip - 0.004, w), s - 0.5)), a_full * w)
            bulge = 1.0 + SP["mouth_bulge"] * math.sin(math.pi * w) * smooth(s1, s0, s)
            outer.append(part.add((p.x * bulge, p.y, p.z), (s, 1.0 - w), (x * LENGTH, 1.0), (1.0, 0.0, 0.0)))
            inner.append(part.add((p.x * bulge - thick, p.y, p.z), (s, 1.0 - w), ((x - thick) * LENGTH, 1.0), (1.0, 0.0, 1.0)))
        rings.append(outer + inner[::-1])
    part.loft(rings)
    return part


def maxilla(low):
    """The plate along the upper lip of the right side, from near the snout back past the jaw's hinge, broad at
    its rear end (built with the mouth shut)."""
    part = Part("maxilla")
    stations = 8 if low else 26
    around = 6 if low else 12
    s_from, s_to, high_front, high_rear = SP["maxilla"]
    front = None
    rings = []
    for i in range(stations + 1):
        u = i / stations
        s = lerp(s_from, s_to, u)
        # (along the lip, and on down the line of the mouth behind the jaw's hinge)
        y = BODY_SKIN.bot(min(s, HINGE_S - 0.006)) + 0.0055 - max(s - HINGE_S + 0.006, 0.0) * 0.45
        at, out, up = body_frame(s, y)
        if front is None:
            front = at.copy()
        ends = math.sin(math.pi * u) ** 0.5 if 0.0 < u < 1.0 else 0.0
        if u > 0.5:
            ends = max(ends, 0.0 if u >= 1.0 else min(1.0, (1.0 - u) / 0.12) ** 0.5)
        high = lerp(high_front, high_rear, smooth(0.0, 0.85, u)) * ends
        thick = 0.0045 * ends
        ring = []
        for k in range(around):
            q = TAU * k / around
            p = at - out * 0.0012 + up * (high * math.cos(q)) + out * (thick * math.sin(q))
            ring.append(part.add(p, (s, 1.0 - 0.5 * (1.0 + math.cos(q))),
                                 ((p.y - front.y) * LENGTH, 1.0 - (p.z - front.z) * LENGTH), (MAXILLA / 10.0, 0.0, 0.0)))
        rings.append(ring)
    part.loft(rings)
    return part


def eye(low):
    """The right eye: a dome set in the side of the head."""
    part = Part("eye")
    eye_s, eye_y, ball, stands = SP["eye"]
    shown = 0.644
    at, out, up = body_frame(eye_s, eye_y)
    along = up.cross(out).normalized()
    # (the dome goes on under the skin: the eye's drawn face is fitted to the part that shows)
    seen = math.sqrt(1.0 - (1.0 - stands / ball) ** 2)
    reach = math.asin(min(seen / shown, 0.999))
    centre = at - out * (ball - stands)
    rows = 4 if low else 10
    around = 10 if low else 32
    rings = []
    for i in range(rows + 1):
        a = reach * i / rows
        ring = []
        for k in range(around):
            q = TAU * k / around
            p = centre + out * (ball * math.cos(a)) + (up * math.cos(q) + along * math.sin(q)) * (ball * math.sin(a))
            # (UV: where it is on the eye's round face, seen straight on: its middle at (0.5, 0.5), up towards +x)
            across = 0.5 * shown * math.sin(a) / seen
            ring.append(part.add(p, (0.5 + across * math.cos(q), 1.0 - (0.5 + across * math.sin(q))), (0.0, 1.0),
                                 (EYE / 10.0, 0.0, 0.0)))
        rings.append(ring)
    # (closed behind, inside the head)
    back = centre + out * (ball * math.cos(reach) - 0.003)
    rings.append([part.add(back, (0.5 + 0.5 * math.cos(TAU * k / around), 0.5 - 0.5 * math.sin(TAU * k / around)),
                           (0.0, 1.0), (EYE / 10.0, 0.0, 0.0)) for k in range(around)])
    part.loft(rings)
    return part


def fin(name, kind, rays, base, direction, length, normal, thick, low, paired=False, ridge_from=0.0, per_ray=4,
        ridge=0.0011):
    """A fin: `rays` rays fanned from the line `base(t)` (t 0 its leading edge to 1 its trailing edge), each
    going the way `direction(t)` for `length(t)`; flat, facing `normal`; `thick` at its root."""
    part = Part(name)
    per_ray = 1 if low else per_ray
    rows = 3 if low else 12
    cols = max(rays * per_ray, 6)
    normal = normal.normalized()
    left, right = [], []
    for i in range(cols + 1):
        t = i / cols
        b, d, long = base(t), direction(t).normalized(), length(t)
        ridged = 0.5 + 0.5 * math.cos(TAU * (t * rays - 0.5)) if (rays > 1 and not low) else 0.0
        edge = min(1.0, t / 0.06) ** 0.5 * min(1.0, (1.0 - t) / 0.1) ** 0.5
        a, c = [], []
        for j in range(rows + 1):
            r = j / rows
            taper = 1.0 - r
            th = edge * (taper ** 0.5) * (thick * (0.1 + 0.9 * taper ** 1.6) + ridge * ridged * smooth(ridge_from, ridge_from + 0.14, r))
            out = d * (long * r)
            mid = b + out
            if paired:
                data = ((r, 1.0 - t * rays), (normal.x, 1.0 - normal.y), (kind / 10.0, 0.0, normal.z * 0.5 + 0.5))
            else:
                data = ((r, 1.0 - t * rays), (out.y * LENGTH, 1.0 - out.z * LENGTH), (kind / 10.0, 0.0, 0.0))
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


def raked(a0, a1, t, down=False):
    a = math.radians(lerp(a0, a1, t))
    return Vector((0.0, -math.sin(a) if down else math.sin(a), math.cos(a)))


def fins(low):
    made = []
    side_way = Vector((1.0, 0.0, 0.0))
    # The spiny first dorsal: stout spines, the skin between them cut in at the edge.
    s0, s1, count, profile, a0, a1 = SP["spiny"]
    tall = curve(profile)
    cut = 0.0 if low else SP["spiny_cut"]
    made.append(fin(
        "dorsal_spiny", SPINY, count,
        lambda t: Vector((0.0, BODY_SKIN.top(lerp(s0, s1, t)) - 0.008, lerp(s0, s1, t) - 0.5)),
        lambda t: raked(a0, a1, t),
        lambda t: tall(t) * (1.0 - cut * (0.5 + 0.5 * math.cos(TAU * t * count))),
        side_way, 0.009, low, per_ray=6, ridge=0.0022))
    # The soft second dorsal.
    s0b, s1b, count_b, profile_b, b0, b1 = SP["soft"]
    tall_b = curve(profile_b)
    made.append(fin(
        "dorsal_soft", SOFT, count_b,
        lambda t: Vector((0.0, BODY_SKIN.top(lerp(s0b, s1b, t)) - 0.008, lerp(s0b, s1b, t) - 0.5)),
        lambda t: raked(b0, b1, t), tall_b, side_way, 0.009, low))
    # The tail.
    root, t_mid, t_long, t_power, t_spread, t_rays, ragged = SP["tail"]
    pd_top, pd_bot = BODY_SKIN.top(root), BODY_SKIN.bot(root)

    def tail_long(t):
        a = abs(2.0 * t - 1.0)
        long = lerp(t_mid, t_long, a ** t_power)
        if a > 0.9:
            long *= 1.0 - 0.1 * ((a - 0.9) / 0.1) ** 2
        if ragged > 0.0 and not low:
            # (each ray's tip stands out past the skin between the rays: a ragged edge)
            long *= 1.0 + ragged * (abs(((t * t_rays) % 1.0) - 0.5) * 2.0 - 0.5) * (-1.0)
        return long
    made.append(fin(
        "tail", TAIL, t_rays,
        lambda t: Vector((0.0, lerp(pd_top * 0.96, pd_bot * 0.96, t), root - 0.024 * (2.0 * t - 1.0) ** 2 - 0.5)),
        lambda t: raked(t_spread * (1.0 - 2.0 * t), t_spread * (1.0 - 2.0 * t), 0.0),
        tail_long, side_way, 0.02, low, ridge_from=0.3))
    # The anal fin: three spines and the soft rays, short-based and rounded.
    s0c, s1c, count_c, profile_c, c0, c1 = SP["anal"]
    tall_c = curve(profile_c)
    made.append(fin(
        "anal", ANAL, count_c,
        lambda t: Vector((0.0, BODY_SKIN.bot(lerp(s0c, s1c, t)) + 0.008, lerp(s0c, s1c, t) - 0.5)),
        lambda t: raked(c0, c1, t, True), tall_c, side_way, 0.009, low))

    # The paired fins, the right one of each (the left is its mirror picture).
    def on_body(s, up, sunk=0.005):
        y = lerp(BODY_SKIN.bot(s), BODY_SKIN.top(s), up)
        return Vector((body_x(s, y) - sunk, y, s - 0.5))
    # (the pelvic fins: under the pectorals, as a bass has them)
    pv_s, pv_long, pv_rays = SP["pelvic"]
    p0, p1 = on_body(pv_s, 0.035), on_body(pv_s + 0.03, 0.02)
    d0, d1 = Vector((0.4, -0.75, 0.55)), Vector((0.2, -0.3, 0.95))
    pelvic = fin(
        "pelvic", PELVIC, pv_rays, lambda t: p0.lerp(p1, t), lambda t: turn(d0, d1, t),
        lambda t: pv_long * (1.0 - 0.5 * t ** 1.2) * (0.88 + 0.12 * smooth(0.0, 0.16, t)) * (1.0 - 0.12 * smooth(0.8, 1.0, t)),
        d0.cross(d1), 0.008, low, paired=True)
    made += [pelvic, pelvic.mirrored("pelvic_left", flip_side)]
    print("CLEARANCE pelvic fin to body, sculling: %.1f mm" % clearance(pelvic, d0.cross(d1), lambda r: 0.012 * r * r))
    # (the pectoral fins: big round fans on the sides behind the gill covers, held a little out)
    pc_s, pc_long, pc_rays, pc_up = SP["pectoral"]
    q0, q1 = on_body(pc_s, pc_up + 0.085), on_body(pc_s + 0.012, pc_up - 0.035)
    e0, e1 = Vector((0.42, 0.22, 0.88)), Vector((0.34, -0.62, 0.7))
    pectoral = fin(
        "pectoral", PECTORAL, pc_rays, lambda t: q0.lerp(q1, t), lambda t: turn(e0, e1, t),
        lambda t: pc_long * (0.66 + 0.34 * math.sin(math.pi * t ** 0.9) ** 0.8),
        e0.cross(e1), 0.008, low, paired=True)
    made += [pectoral, pectoral.mirrored("pectoral_left", flip_side)]
    print("CLEARANCE pectoral fin to body, sculling: %.1f mm" % clearance(pectoral, e0.cross(e1), lambda r: 0.026 * (0.65 * r + 0.7 * r * r)))
    return made


def make(name, low):
    parts = []
    body = Part("body")
    k = SP["detail"]
    skin(body, BODY_SKIN, body_places(low), 9 if low else int(28 * k), BODY)
    parts.append(body)
    jaw = Part("jaw")
    jaw_rings = 14 if low else 44
    skin(jaw, JAW_SKIN, [lerp(JAW_SKIN.first, JAW_SKIN.last, (i / jaw_rings) ** 1.15) for i in range(jaw_rings + 1)],
         5 if low else 14, JAW)
    parts.append(jaw)
    side = membrane(low)
    parts += [side, side.mirrored("membrane_left", flip_side)]
    plate = maxilla(low)
    parts += [plate, plate.mirrored("maxilla_left", same)]
    ball = eye(low)
    parts += [ball, ball.mirrored("eye_left", same)]
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
    material = bpy.data.materials.get("fish") or bpy.data.materials.new("fish")
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
    xs = [v.co.x for v in mesh.vertices]
    ys = [v.co.y for v in mesh.vertices]
    zs = [v.co.z for v in mesh.vertices]
    print("BUILT %s verts=%d tris=%d" % (name, len(mesh.vertices), tris))
    print("REACH %s: nose %.3f tail %.3f up %.3f down %.3f side %.3f (metres from the origin)" % (
        name, max(ys), -min(ys), max(zs), -min(zs), max(xs)))
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
    # (Blender space: the nose is towards +Y, up is +Z; the views are laid out for a fish 1 long)
    views = [("right", (1, 0, 0), (0, 0, 0), 1.15), ("left", (-1, 0, 0), (0, 0, 0), 1.15),
             ("top", (0, -0.001, 1), (0, 0, 0), 1.15), ("under", (0, 0.001, -1), (0, 0, 0), 1.15),
             ("front", (0, 1, 0), (0, 0, 0), 0.75), ("back", (0, -1, 0), (0, 0, 0), 0.75),
             ("quarter", (0.7, 0.6, 0.35), (0, 0, 0), 1.1), ("low_quarter", (0.6, 0.6, -0.5), (0, 0, 0), 1.1),
             ("head", (1, 0.15, 0.05), (0, 0.33, -0.02), 0.5), ("head_front", (0.45, 1, -0.1), (0, 0.38, -0.03), 0.42),
             ("tail", (1, -0.2, 0.1), (0, -0.36, 0), 0.5)]
    for low, obj in ((False, made[0]), (True, made[1])):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if low and view not in ("right", "quarter", "head"):
                continue
            offset = Vector(direction).normalized() * 10.0 * LENGTH
            camera.data.ortho_scale = frame * LENGTH
            camera.location = Vector(target) * LENGTH + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "X" if view in ("top", "under") else "Y").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % ("lo_" if low else "", view))
            bpy.ops.render.render(write_still=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    print("SHAPE %s: LENGTH=%.3f HINGE_S=%.4f HINGE_Y=%.4f GILL_S=%.4f GAPE_MAX=%.3f depth=%.4f width=%.4f (body lengths)" % (
        NAME, LENGTH, HINGE_S, HINGE_Y, GILL_S, GAPE_MAX,
        max(BODY_SKIN.top(i / 200.0) - BODY_SKIN.bot(i / 200.0) for i in range(40, 140)),
        2.0 * max(BODY_SKIN.at(i / 200.0)[2] for i in range(40, 140))))
    full = make(NAME, False)
    low = make(NAME + "_lo", True)
    export_one(full, os.path.join(OUT, NAME + ".glb"))
    export_one(low, os.path.join(OUT, NAME + "_lo.glb"))
    low.location.x = LENGTH * 0.6
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, NAME + ".blend"))
    low.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low])


if __name__ == "__main__":
    main()
