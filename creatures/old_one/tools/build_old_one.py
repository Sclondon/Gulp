"""Builds the old one (creatures/old_one) and exports it for Godot.

Run from the game's root (or anywhere: paths are from this file):
    blender --background --python creatures/old_one/tools/build_old_one.py
    blender --background --python creatures/old_one/tools/build_old_one.py -- <preview folder>   # with pictures

Writes creatures/old_one/models/old_one.glb (the full model, for close pictures), old_one_game.glb (the game model:
Twilight Princess boss weight, its triangles spent on the face, the eyes, the curls of the tentacles and the edges of
the wings), old_one_lo.glb (far off) and the editable creatures/old_one/tools/old_one.blend (this folder has a
.gdignore). Each model is one still mesh with one surface: the shader (old_one.gdshader) draws every marking, breathes
it, drifts its tentacles, parts its wings and lights its eyes. It prints a WINDING line for each model (the check that
nothing is inside out).

An original sea monster in the spirit of the cosmic-horror "old one" (not any published depiction): a vast thing
asleep on the floor of a deep basin, about 45 m across as it lies.

- THE HEAD: a great bulbous dome like an octopus's mantle, tilted back over its body, lumpy, with folds across its
  back; its face looks forward and down, and from it spills
- THE TENTACLES: fourteen thick ones (eight on the low model), a beard of shorter ones falling forward onto the floor
  and longer ones sprawled out to the sides, each lying along the floor and ending in a curl, some rolled up off the
  floor like a fern, some rolled sideways on it.
- THE EYES: a ring of ten small pale eyes round the top of the face, each in a raised socket.
- THE WINGS: two huge folded membranous wings, like collapsed sails, rising from its shoulders to a clawed wrist high
  above its head and hanging down from there in four fingers to the floor, the skin between them scalloped and torn.
- THE BODY: a low hunched mound behind the head, half buried, with a row of knobs down its back.
- Weed growing from its crown, its body and the tops of its wings.

Everything here is in Godot space (metres, Y up, its face towards -Z) until it is written out. The origin is on the
floor (y 0) under the middle of where it lies.

What a point is, for the shader: UV2.y the part:
  0 the body mound, 1 the head (mantle), 2 an eye, 3 an eye's socket, 4 a tentacle, 5 a wing's bones (arm and
  fingers), 6 a wing's membrane, 7 a wing's claw, 8 weed on the head or body, 9 weed on a wing, 10 a knob on the back.
UV2.x: on a tentacle which one ((n + 0.5) / 16); on an eye which one ((n + 0.5) / 10); on the membrane how far out from
the wrist (0..1); on weed how far along the blade (0 root, 1 tip); on weed of the head or body 0, and 1 for the head's.
UV: on the head and its sockets (around / tau + 0.5, along the head's axis 0 the face .. 1 the crown); on the body
(around, height); on a tentacle (around: 0.5 the side that lay on the floor, along 0 root .. 1 tip); on an eye the
point in the eye's own plane in eye radii (x across, y up); on every wing part (fan, attached): fan 1 at the leading
finger down to 0 at the last finger and the arm (how far it turns as the hand spreads), attached 1 moving with the arm,
0 fixed to the body (where the last skin meets the flank). (The glTF writer flips V: what is written here is 1 - v,
so that Godot reads v.)

The numbers marked "as the shader has it" are in old_one.gdshader too: change one, change the other.
"""

import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "models")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = ARGS[0] if ARGS and not ARGS[0].startswith("--") else ""

NAME = "old_one"
TAU = math.tau
PI = math.pi

# The head's axis: from the middle of its face to its crown (as the shader has it).
HEAD_A = Vector((0.0, 6.5, -5.0))
HEAD_B = Vector((0.0, 19.5, 3.0))
# The right wing's shoulder, elbow and wrist, its four knuckles and the tips of its four fingers (the left wing
# is its mirror). (as the shader has it: SHOULDER, WRIST)
SHOULDER = Vector((6.0, 5.5, 11.0))
ELBOW = Vector((9.0, 6.0, 15.5))
WRIST = Vector((9.5, 27.0, 8.0))
KNUCKLES = [Vector((19.0, 20.0, -4.0)), Vector((22.5, 14.0, 6.0)), Vector((18.5, 11.5, 15.0)), Vector((11.5, 9.0, 19.5))]
FINGERS = [Vector((23.5, 2.5, -10.0)), Vector((25.0, 0.8, 7.0)), Vector((20.0, 0.5, 17.5)), Vector((11.0, 0.4, 21.5))]
# Where the last skin of the wing meets the flank (on the floor beside the body).
FLANK = Vector((7.0, 0.3, 18.0))
# The body mound: an ellipsoid half sunk in the floor.
BODY_C = Vector((0.0, -1.2, 8.0))
BODY_R = Vector((9.5, 8.0, 11.0))
BODY_CUT = -1.0


class Q:
    """How finely each model is cut."""
    def __init__(self, kind):
        self.kind = kind
        full, game = kind == "full", kind == "game"
        self.head_round = 48 if full else (20 if game else 10)
        self.head_rings = 64 if full else (16 if game else 8)
        self.body_round = 40 if full else (14 if game else 8)
        self.body_rings = 20 if full else (6 if game else 3)
        self.tentacles = 14 if kind != "lo" else 8
        self.t_sides = 14 if full else (6 if game else 4)
        self.t_turn = math.radians(6 if full else (24 if game else 30))
        self.t_step = 0.5 if full else (3.2 if game else 5.0)
        self.eye_sides = 20 if full else (10 if game else 5)
        self.eye_rings = 6 if full else 2 if game else 1
        self.bone_sides = 12 if full else (5 if game else 4)
        self.bone_rings = 12 if full else (4 if game else 2)
        self.fan_u = 12 if full else (3 if game else 1)
        self.fan_v = 12 if full else (3 if game else 1)
        self.weeds = 1.0 if full else (0.7 if game else 0.0)
        self.weed_segs = 10 if full else 4
        self.knobs = kind != "lo"


def to_b(p):
    return Vector((p.x, -p.z, p.y))


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def lerp(a, b, t):
    return a + (b - a) * t


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.data = []
        self.out = []
        self.count = {}

    def add(self, p, uv, part, extra=0.0):
        self.verts.append(Vector(p))
        self.data.append(((uv[0], 1.0 - uv[1]), (extra, 1.0 - part)))
        return len(self.verts) - 1

    def face(self, points, out, name):
        """A face wound so that its front is towards `out` (points in the same place counted once)."""
        kept = []
        for i in points:
            if not any((self.verts[i] - self.verts[k]).length < 1e-4 for k in kept):
                kept.append(i)
        if len(kept) < 3:
            return
        points = tuple(kept)
        ps = [self.verts[i] for i in points]
        n = Vector((0.0, 0.0, 0.0))
        for i in range(len(ps)):
            n += ps[i].cross(ps[(i + 1) % len(ps)])
        if n.length < 1e-6:
            return
        if n.dot(out) < 0.0:
            points = tuple(reversed(points))
        self.faces.append(tuple(points))
        self.out.append((Vector(out), name))
        self.count[name] = self.count.get(name, 0) + 1


def grid(m, rows, name, around_closed, centre_of):
    """Quads between rows of point indices; each faces away from centre_of(i, j) (the middle line there)."""
    for i in range(len(rows) - 1):
        a, b = rows[i], rows[i + 1]
        n = len(a)
        last = n if around_closed else n - 1
        for j in range(last):
            k = (j + 1) % n
            q = (a[j], a[k], b[k], b[j])
            mid = sum((m.verts[x] for x in q), Vector()) / 4.0
            m.face(q, mid - centre_of(i, j), name)


# ---------------------------------------------------------------- the head (mantle)

AXIS = (HEAD_B - HEAD_A)
AXIS_LEN = AXIS.length
AXIS_D = AXIS.normalized()
SIDE = Vector((1.0, 0.0, 0.0))
UPF = AXIS_D.cross(SIDE).normalized()
if UPF.y < 0.0:
    UPF = -UPF
HEAD_KEYS = [(-0.08, 0.0), (-0.06, 2.9), (-0.03, 4.1), (0.0, 4.8), (0.15, 5.9), (0.35, 6.5), (0.55, 6.2), (0.75, 5.1),
             (0.88, 3.7), (0.96, 2.0), (1.0, 0.0)]


def head_r(t):
    for (t0, r0), (t1, r1) in zip(HEAD_KEYS, HEAD_KEYS[1:]):
        if t <= t1:
            f = (t - t0) / (t1 - t0)
            if r0 == 0.0:
                return r1 * math.sqrt(f)
            if r1 == 0.0:
                return r0 * math.sqrt(max(0.0, 1.0 - f * f))
            f = f * f * (3.0 - 2.0 * f)
            return r0 + (r1 - r0) * f
    return 0.0


def head_point(t, a):
    """A point on the head's skin: `t` along its axis (0 the face .. 1 the crown), `a` round it (0 the top of the
    forehead, + to its right)."""
    r = head_r(t)
    if r > 0.0:
        # lumps and folds: three folds across its back, a few broad swellings
        fold = sum(math.exp(-((t - c) / 0.035) ** 2) for c in (0.5, 0.64, 0.78)) * smooth(-0.4, 0.4, math.cos(a) + 0.3)
        lump = 0.045 * math.sin(3.0 * a + 7.0 * t) + 0.035 * math.sin(5.0 * a - 11.0 * t + 1.3) + 0.025 * math.sin(9.0 * a + 4.0 * t)
        ridge = math.exp(-(a / 0.3) ** 2) * smooth(0.22, 0.4, t) * (1.0 - smooth(0.8, 0.95, t))
        r *= 1.0 + (lump * smooth(0.0, 0.2, t) - 0.04 * fold + 0.11 * ridge) * (1.0 - smooth(0.8, 0.97, t))
    c = HEAD_A + AXIS_D * (t * AXIS_LEN)
    return c + UPF * (math.cos(a) * r * 0.98) + SIDE * (math.sin(a) * r * 1.02)


def head_normal(t, a):
    e = 1e-3
    p = head_point(t, a)
    dt = head_point(t + e, a) - head_point(t - e, a)
    da = head_point(t, a + e) - head_point(t, a - e)
    n = da.cross(dt)
    if n.dot(p - (HEAD_A + AXIS_D * (t * AXIS_LEN))) < 0.0:
        n = -n
    return n.normalized()


def head(m, q):
    ts = []
    # rings: gathered at the face's rim and the crown, where the outline curves
    n = q.head_rings
    for i in range(n + 1):
        f = i / n
        ts.append(-0.08 + 1.08 * (0.5 - 0.5 * math.cos(PI * f)) * 0.35 + 1.08 * f * 0.65)
    ts[0], ts[-1] = -0.08, 1.0
    rows = []
    for i, t in enumerate(ts):
        row = []
        if i == 0 or i == len(ts) - 1:
            p = HEAD_A + AXIS_D * (t * AXIS_LEN)
            idx = m.add(p, (0.5, max(t, 0.0)), 1)
            row = [idx] * (q.head_round + 1)
        else:
            for j in range(q.head_round + 1):
                a = -PI + TAU * j / q.head_round
                row.append(m.add(head_point(t, a), (a / TAU + 0.5, max(t, 0.0)), 1))
        rows.append(row)
    for i in range(len(rows) - 1):
        a, b = rows[i], rows[i + 1]
        for j in range(q.head_round):
            quad = [a[j], a[j + 1], b[j + 1], b[j]]
            pts = []
            for x in quad:
                if x not in pts:
                    pts.append(x)
            if len(pts) < 3:
                continue
            mid = sum((m.verts[x] for x in pts), Vector()) / len(pts)
            tm = (ts[i] + ts[i + 1]) * 0.5
            m.face(pts, mid - (HEAD_A + AXIS_D * (min(max(tm, 0.0), 0.99) * AXIS_LEN)), "head")


# ---------------------------------------------------------------- the eyes

# (t along the head, angle round it, radius): a ring round the top of the face, two higher and smaller
EYES = [(0.1, 0.0 + s * 0.28, 0.72) for s in (-1, 1)] + [(0.11, s * 0.75, 0.68) for s in (-1, 1)] + \
       [(0.13, s * 1.2, 0.62) for s in (-1, 1)] + [(0.16, s * 1.62, 0.55) for s in (-1, 1)] + \
       [(0.24, s * 0.5, 0.5) for s in (-1, 1)]


def eye(m, q, index, t, a, r):
    c = head_point(t, a)
    n = head_normal(t, a)
    up = Vector((0.0, 1.0, 0.0)) - n * n.y
    if up.length < 1e-3:
        up = UPF - n * n.dot(UPF)
    up.normalize()
    across = up.cross(n).normalized()
    extra = (index + 0.5) / len(EYES)
    sides = q.eye_sides
    # The eye: a dome rising out of its socket.
    rings = []
    for k in range(q.eye_rings + 1):
        al = (PI / 2) * k / (q.eye_rings + 1)
        rho = r * math.cos(al)
        h = r * 0.15 + r * 0.55 * math.sin(al)
        row = []
        for j in range(sides):
            ph = TAU * j / sides
            p = c + n * h + (across * math.cos(ph) + up * math.sin(ph)) * rho
            row.append(m.add(p, (math.cos(ph) * rho / r, math.sin(ph) * rho / r), 2, extra))
        rings.append(row)
    top = m.add(c + n * (r * 0.7), (0.0, 0.0), 2, extra)
    middle = c - n * (r * 0.6)
    grid(m, rings, "eye", True, lambda i, j: middle)
    last = rings[-1]
    for j in range(sides):
        tri = (last[j], last[(j + 1) % sides], top)
        mid = sum((m.verts[x] for x in tri), Vector()) / 3.0
        m.face(tri, mid - middle, "eye")
    # The socket: a raised lip round it, sinking into the skin outside.
    uv = (a / TAU + 0.5, t)
    lip = []
    for rr, hh in ((r * 0.98, r * 0.12), (r * 1.18, r * 0.34), (r * 1.6, -r * 0.15)):
        row = []
        for j in range(sides):
            ph = TAU * j / sides
            row.append(m.add(c + n * hh + (across * math.cos(ph) + up * math.sin(ph)) * rr, uv, 3))
        lip.append(row)

    def tube_centre(i, j):
        ph = TAU * (j + 0.5) / sides
        return c + (across * math.cos(ph) + up * math.sin(ph)) * (r * 1.22)
    grid(m, lip, "socket", True, tube_centre)


# ---------------------------------------------------------------- tubes (tentacles, wing bones, claws)

def frames(pts, first_n):
    """Rotation-minimising frames along a polyline (double reflection), from a first normal."""
    ts = []
    for i in range(len(pts)):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, len(pts) - 1)]
        ts.append((b - a).normalized())
    ns = []
    n = (first_n - ts[0] * first_n.dot(ts[0])).normalized()
    ns.append(n)
    for i in range(len(pts) - 1):
        v1 = pts[i + 1] - pts[i]
        c1 = v1.dot(v1)
        if c1 < 1e-12:
            ns.append(n)
            continue
        rl = n - v1 * (2.0 / c1 * v1.dot(n))
        tl = ts[i] - v1 * (2.0 / c1 * v1.dot(ts[i]))
        v2 = ts[i + 1] - tl
        c2 = v2.dot(v2)
        n = rl - v2 * (2.0 / c2 * v2.dot(rl)) if c2 > 1e-12 else rl
        n = (n - ts[i + 1] * n.dot(ts[i + 1])).normalized()
        ns.append(n)
    return ts, ns


def tube(m, pts, radii, sides, part, name, uv_of, extra, first_n, tip=True, root_cap=True, squash=1.0):
    """A tube along `pts` (radius `radii`), closed by a point at its tip and a flat cap at its root.
    uv_of(i, around) gives each point's UV."""
    ts, ns = frames(pts, first_n)
    rows = []
    for i, p in enumerate(pts):
        n = ns[i]
        b = ts[i].cross(n).normalized()
        row = []
        for j in range(sides + 1):
            ang = TAU * j / sides
            off = n * (math.cos(ang) * radii[i] * squash) + b * (math.sin(ang) * radii[i])
            row.append(m.add(p + off, uv_of(i, j / sides), part, extra))
        rows.append(row)
    for i in range(len(rows) - 1):
        a, bb = rows[i], rows[i + 1]
        mid_line = (pts[i] + pts[i + 1]) * 0.5
        for j in range(sides):
            quad = (a[j], a[j + 1], bb[j + 1], bb[j])
            mid = sum((m.verts[x] for x in quad), Vector()) / 4.0
            m.face(quad, mid - mid_line, name)
    if tip:
        end = pts[-1] + ts[-1] * radii[-1] * 1.5
        e = m.add(end, uv_of(len(pts) - 1, 0.5), part, extra)
        last = rows[-1]
        for j in range(sides):
            tri = (last[j], last[j + 1], e)
            m.face(tri, ts[-1] * 0.3 + (sum((m.verts[x] for x in tri), Vector()) / 3.0 - pts[-1]).normalized(), name)
    if root_cap:
        s = m.add(pts[0] - ts[0] * radii[0] * 0.3, uv_of(0, 0.5), part, extra)
        first = rows[0]
        for j in range(sides):
            tri = (first[j + 1], first[j], s)
            m.face(tri, -ts[0], name)
    return rows


def resample(dense, radii, turn, step, keep=()):
    """For a coarse model: the fewest points of a dense path such that between two kept ones it does not turn
    more than `turn`, its radius does not change by more than a third, and they are no more than `step` apart."""
    kept = [0]
    acc = 0.0
    dist = 0.0
    for i in range(1, len(dense) - 1):
        d0 = (dense[i] - dense[i - 1])
        d1 = (dense[i + 1] - dense[i])
        if d0.length > 1e-9 and d1.length > 1e-9:
            acc += d0.angle(d1)
        dist += d0.length
        r_last = radii[kept[-1]]
        # (and never so close after a turn that the rings, as wide as the tube, would cross on the inside of it)
        if (acc > turn or dist > step or abs(radii[i] - r_last) > 0.33 * r_last or i in keep) and dist > 2.2 * max(radii[i], r_last) * acc:
            kept.append(i)
            acc = 0.0
            dist = 0.0
    # (no sliver of a last piece before the tip)
    if len(kept) > 1 and (dense[-1] - dense[kept[-1]]).length < 2.0 * radii[kept[-1]]:
        kept.pop()
    kept.append(len(dense) - 1)
    return kept


def laplace(pts, passes, fixed_ends=2):
    for _ in range(passes):
        new = list(pts)
        for i in range(fixed_ends, len(pts) - fixed_ends):
            new[i] = pts[i] * 0.5 + (pts[i - 1] + pts[i + 1]) * 0.25
        pts = new
    return pts


def bend_radius(a, b, c):
    """The radius of the circle through three points (large where they lie straight)."""
    ab, bc, ca = (b - a).length, (c - b).length, (a - c).length
    area2 = (b - a).cross(c - a).length
    if area2 < 1e-12:
        return 1e9
    return ab * bc * ca / (2.0 * area2)


def thin_at_bends(pts, radii, margin=1.3):
    """Radii no bigger than the path's bend allows: where it curls tighter than its tube is thick, the inside of
    the bend would fold through itself and turn inside out, so the tube is made thinner there (and the thinning
    eased along it)."""
    out = list(radii)
    for i in range(1, len(pts) - 1):
        for step in (2, 4, 8):
            k = min(step, i, len(pts) - 1 - i)
            out[i] = min(out[i], bend_radius(pts[i - k], pts[i], pts[i + k]) / margin)
    for _ in range(6):
        out = [out[0]] + [min(out[i], (out[i - 1] + out[i] + out[i + 1]) / 3.0) for i in range(1, len(out) - 1)] + [out[-1]]
    return out


def bezier(p0, p1, p2, t):
    return p0 * ((1 - t) ** 2) + p1 * (2 * (1 - t) * t) + p2 * (t * t)


# The tentacles: (angle round the face (0 up, + its right), how far out on it, heading on the floor (radians from
# straight ahead, + its right), length of its run on the floor, root radius, curl: turns, curl radius, "up"/"side",
# which way a sideways curl rolls (+1 right)).
TENTACLES = [
    (PI, 2.2, 0.08, 10.0, 1.44, 0.41, 3.1, "up", 1),
    (PI - 0.55, 3.0, -0.4, 9.0, 1.37, 0.9, 3.0, "side", -1),
    (PI + 0.55, 3.0, 0.45, 10.0, 1.37, 0.38, 2.9, "up", 1),
    (PI - 1.05, 3.6, -0.85, 11.0, 1.30, 0.8, 3.2, "side", 1),
    (PI + 1.05, 3.6, 0.9, 10.5, 1.30, 1.0, 3.0, "side", 1),
    (PI - 1.5, 3.9, -1.35, 12.0, 1.22, 0.34, 3.2, "up", -1),
    (PI + 1.5, 3.9, 1.4, 12.5, 1.22, 0.85, 3.2, "side", -1),
    (PI - 2.0, 3.7, -1.9, 10.0, 1.12, 1.0, 2.8, "side", -1),
    (PI + 2.0, 3.7, 2.0, 9.5, 1.12, 0.38, 2.9, "up", 1),
    (PI - 0.2, 0.6, -0.15, 6.0, 1.22, 0.45, 2.2, "up", 1),
    (PI + 0.3, 0.8, 0.2, 5.0, 1.22, 1.1, 2.4, "side", 1),
    (PI - 0.8, 1.6, -0.6, 4.5, 1.15, 0.41, 2.4, "up", -1),
    (PI + 2.5, 3.2, 2.45, 8.0, 1.01, 0.9, 2.6, "side", 1),
    (PI - 2.5, 3.2, -2.4, 7.5, 1.01, 0.45, 2.5, "up", 1),
]
# which of them the low model keeps
LO_TENTACLES = [0, 1, 2, 3, 4, 5, 6, 8]


def tentacle_path(spec, seed):
    rnd = random.Random(seed)
    psi, rho, heading, run, r0, turns, curl_r, how, roll = spec
    face_mid = HEAD_A - AXIS_D * 0.4
    radial = UPF * math.cos(psi) - SIDE * math.sin(psi)
    root = face_mid + radial * rho * 0.9 + AXIS_D * 1.6
    h = Vector((math.sin(heading), 0.0, -math.cos(heading)))
    side = Vector((0.0, 1.0, 0.0)).cross(h).normalized()  # (to the left of the heading)
    pts = []
    p1 = root - AXIS_D * 2.6 + radial * 1.2 + Vector((0.0, -1.0, 0.0))
    q = Vector((root.x, 0.0, root.z)) + h * (2.5 + rho * 0.4)
    q.y = r0 * 0.6
    for k in range(24):
        pts.append(bezier(root, p1, q, k / 24.0))
    # along the floor, waving a little
    n_run = max(int(run / 0.25), 4)
    wave = rnd.uniform(0.6, 1.4)
    ph = rnd.uniform(0, TAU)
    for k in range(n_run):
        f = k / n_run
        p = q + h * (run * f) + side * (wave * math.sin(ph + f * TAU * 0.8) - wave * math.sin(ph))
        pts.append(p)
    end = pts[-1]
    tdir = (pts[-1] - pts[-2]).normalized()
    # the curl
    if how == "up":
        axis_up = (Vector((0.0, 1.0, 0.0)) + side * (roll * 0.9)).normalized()
    else:
        axis_up = side * roll
    n_curl = int(turns * 90)
    for k in range(1, n_curl + 1):
        th = TAU * turns * k / n_curl
        rr = curl_r * (1.0 - 0.6 * k / n_curl)
        p = end + axis_up * (rr - rr * math.cos(th)) + tdir * (rr * math.sin(th))
        # (a spiral: the radius shrinks, so pull towards the middle of the curl)
        p += axis_up * ((curl_r - rr) * 1.0)
        pts.append(p)
    pts = laplace(pts, 14)
    return pts, r0


def tentacle(m, q, index, spec):
    dense, r0 = tentacle_path(spec, 100 + index)
    lengths = [0.0]
    for a, b in zip(dense, dense[1:]):
        lengths.append(lengths[-1] + (b - a).length)
    total = lengths[-1]
    radii = []
    for i, p in enumerate(dense):
        s = lengths[i] / total
        r = r0 * (1.0 - 0.86 * s) ** 0.9 + 0.08
        r *= 1.0 + 0.15 * (1.0 - smooth(0.0, 0.1, s))
        radii.append(r)
    # rest on the floor (half buried at the root end)
    for i, p in enumerate(dense):
        s = lengths[i] / total
        # (continuous in its height, so that no step is made between one point and the next)
        k = smooth(4.0, 9.0, lengths[i]) * (1.0 - smooth(radii[i] * 0.9, radii[i] * 1.8, p.y))
        p.y = lerp(p.y, radii[i] * 0.55, k)
    dense = laplace(dense, 3)
    radii = thin_at_bends(dense, radii)
    keep = resample(dense, radii, q.t_turn, q.t_step)
    pts = [dense[i] for i in keep]
    rs = [radii[i] for i in keep]
    ss = [lengths[i] / total for i in keep]
    extra = (index + 0.5) / 16.0
    first_n = Vector((0.0, -1.0, 0.0))
    tube(m, pts, rs, q.t_sides, 4, "tentacle", lambda i, around: (around, ss[i]), extra, first_n, tip=True, root_cap=True)


# ---------------------------------------------------------------- the wings

def wing_plane_normal():
    n = (FINGERS[0] - WRIST).cross(FINGERS[3] - WRIST).normalized()
    # (the hand spreads by turning about this at the wrist: the leading finger must swing away from the last)
    swing = n.cross(FINGERS[0] - WRIST)
    if swing.dot(FINGERS[3] - WRIST) > 0.0:
        n = -n
    return n


SPREAD_AXIS = wing_plane_normal()


def mirror(p, sx):
    return Vector((p.x * sx, p.y, p.z))


def chain(points, n):
    """A smooth path through `points` (a rounded polyline: each corner cut by a curve), `n` points along it,
    evenly by length."""
    dense = []
    for i in range(len(points) - 1):
        a, b = points[i], points[i + 1]
        for k in range(40):
            dense.append(a + (b - a) * (k / 40.0))
    dense.append(points[-1])
    dense = laplace(dense, 30, 1)
    lengths = [0.0]
    for a, b in zip(dense, dense[1:]):
        lengths.append(lengths[-1] + (b - a).length)
    total = lengths[-1]
    out = []
    j = 0
    for k in range(n + 1):
        want = total * k / n
        while j < len(lengths) - 2 and lengths[j + 1] < want:
            j += 1
        f = (want - lengths[j]) / max(lengths[j + 1] - lengths[j], 1e-9)
        out.append(dense[j] + (dense[j + 1] - dense[j]) * min(max(f, 0.0), 1.0))
    return out


def along(path, s):
    """The point a fraction `s` of the way along a path of evenly spaced points."""
    x = s * (len(path) - 1)
    i = min(int(x), len(path) - 2)
    return path[i] + (path[i + 1] - path[i]) * (x - i)


def finger_paths(sx):
    W = mirror(WRIST, sx)
    paths = []
    for f, k in zip(FINGERS, KNUCKLES):
        paths.append(chain([W, mirror(k, sx), mirror(f, sx)], 60))
    return paths


def attach_of(p, sx):
    """How much a point of a wing moves with it as it lifts (0 where it is fixed to the body: the shoulder and
    the flank where the last skin meets it; 1 seven metres or more from both)."""
    return smooth(0.0, 7.0, (p - mirror(SHOULDER, sx)).length) * smooth(0.0, 7.0, (p - mirror(FLANK, sx)).length)


def wing(m, q, sx):
    W = mirror(WRIST, sx)
    S = mirror(SHOULDER, sx)
    E = mirror(ELBOW, sx)
    K = mirror(FLANK, sx)
    out_x = Vector((sx, 0.0, 0.0))
    up = Vector((0.0, 1.0, 0.0))
    fans = [1.0, 2.0 / 3.0, 1.0 / 3.0, 0.0]
    fingers = finger_paths(sx)
    att = lambda p: attach_of(p, sx)
    # The arm: shoulder to elbow to wrist, thick at the shoulder, rising out of the body.
    nb = q.bone_rings
    arm = chain([S - out_x * 2.0, E, W], 2 * nb + 2)
    radii = [lerp(2.6, 0.75, (k / (len(arm) - 1)) ** 0.6) for k in range(len(arm))]
    tube(m, arm, radii, q.bone_sides, 5, "wing bone", lambda i, a: (0.0, att(arm[i])), 0.0, up, tip=False)
    # (a knob at the elbow and at the wrist)
    for at, r in ((E, 1.6), (W, 1.05)):
        knob = [at - out_x * r * 0.3, at + out_x * r * 0.55]
        tube(m, knob, [r, r * 0.55], q.bone_sides, 5, "wing bone", lambda i, a, at=at: (0.0, att(at)), 0.0, up)
    # The fingers, each up to its knuckle and down to its tip; a claw on the leading knuckle.
    for k, path in enumerate(fingers):
        keep = [0] + [int(60 * (i + 1) / (nb + 3)) for i in range(nb + 2)] + [60]
        keep = sorted(set(keep))
        pts = [path[i] for i in keep]
        rr = [lerp(0.6, 0.14, i / 60.0) for i in keep]
        ext = pts[-1] + (pts[-1] - pts[-2]).normalized() * 0.8
        pts.append(ext)
        rr.append(0.08)
        fan = fans[k]
        tube(m, pts, rr, q.bone_sides, 5, "wing bone", lambda i, a, fan=fan, pts=pts: (fan, att(pts[i])), 0.0, up)
    # The claws: hooked, one at the wrist pointing up and back, a smaller one on the first knuckle.
    nc = 6 if q.kind == "full" else 3
    for at, size, fan in ((W, 1.0, 0.0), (mirror(KNUCKLES[0], sx), 0.55, 1.0)):
        claw = []
        for i in range(nc + 1):
            f = i / nc
            claw.append(at + Vector((sx * 0.5 * f, 3.6 * f - 0.6 * f * f * f, 1.6 * f * f)) * size)
        tube(m, claw, [lerp(0.75, 0.05, i / nc) * size for i in range(nc + 1)], q.bone_sides, 7, "claw",
             lambda i, a, fan=fan, at=at: (fan, att(at)), 0.0, Vector((0.0, 0.0, 1.0)))
    # The skins: one between each finger and the next, the last between the last finger and the arm and flank,
    # and one inside the arm (wrist to shoulder); each a thin closed slab, the trailing edges scalloped and torn
    # here and there.
    rnd = random.Random(7 if sx > 0 else 8)
    arm_flank = chain([W, E, K], 60)
    chains = fingers + [arm_flank]
    for k in range(4):
        fa = fans[k]
        fb = fans[k + 1] if k < 3 else 0.0
        membrane(m, q, chains[k], chains[k + 1], fa, fb, rnd, k == 3, sx)
    inner = chain([W, E, S], 60)
    straight = chain([W, (W + S) * 0.5 + Vector((0.0, -1.0, 1.5)), S], 60)
    membrane(m, q, inner, straight, 0.0, 0.0, rnd, True, sx)


def membrane(m, q, ca, cb, fa, fb, rnd, last, sx):
    nu = q.fan_u + (1 if last else 0)
    nv = q.fan_v + 1
    tears = [(rnd.uniform(0.2, 0.8), rnd.uniform(0.1, 0.25)) for _ in range(2)]
    if last:
        tears = [(0.5, 0.0)]
    sag = 0.0 if last else 0.18

    def reach(u):
        s = 1.0 - sag * math.sin(PI * u)
        for tu, depth in tears:
            s -= depth * max(0.0, 1.0 - abs(u - tu) / 0.06)
        return s

    def at(u, v):
        s = v * reach(u)
        if last:
            # (on the arm and flank side, the whole length of the skin's edge, not cut back)
            p = along(ca, s) * (1.0 - u) + along(cb, v) * u
        else:
            p = along(ca, s) * (1.0 - u) + along(cb, s) * u
        width = (along(ca, s) - along(cb, s)).length
        n = (along(ca, 0.5) - along(ca, 0.0)).cross(along(cb, 0.5) - along(cb, 0.0))
        if n.length > 1e-6:
            n.normalize()
            if n.x * sx < 0.0:
                n = -n
            p = p + n * (0.07 * width * math.sin(PI * u) * math.sin(PI * v))
        return p

    us = [i / nu for i in range(nu + 1)]
    if q.kind != "lo":
        for tu, depth in tears:
            if depth > 0.0:
                us.extend([tu - 0.06, tu, tu + 0.06])
        us = sorted(set(round(u, 4) for u in us if 0.0 <= u <= 1.0))
        # (no sliver columns: an even column too near a tear's is dropped)
        marks = [x for tu, depth in tears if depth > 0.0 for x in (tu - 0.06, tu, tu + 0.06)]
        us = [u for u in us if u in (0.0, 1.0) or any(abs(u - x) < 1e-6 for x in marks) or all(abs(u - x) > 0.035 for x in marks)]
    vs = [j / nv for j in range(nv + 1)]
    if q.kind != "lo":
        vs = sorted(set(vs + [0.94]))
    thick = 0.14
    skins = []
    for side in (1.0, -1.0):
        rows = []
        for v in vs:
            row = []
            for u in us:
                vv = max(v, 0.02)
                p = at(u, v)
                base = p.copy()
                # (both skins lie along the panel's own normal from the middle surface, so they never cross)
                n = (along(ca, 0.5) - along(ca, 0.0)).cross(along(cb, 0.5) - along(cb, 0.0))
                n = n.normalized() if n.length > 1e-9 else Vector((sx, 0.0, 0.0))
                if n.x * sx < 0.0:
                    n = -n
                wide = (along(ca, v * reach(u)) - along(cb, v * reach(u))).length
                p = p + n * (side * thick * (1.0 - 0.5 * v) * smooth(0.0, 1.5, wide))
                row.append((m.add(p, (lerp(fa, fb, u), attach_of(base, sx)), 6, v), n * side))
            rows.append(row)
        skins.append(rows)
    for rows in skins:
        for j in range(len(rows) - 1):
            for i in range(len(us) - 1):
                quad = (rows[j][i][0], rows[j][i + 1][0], rows[j + 1][i + 1][0], rows[j + 1][i][0])
                if j == 0:
                    quad = (rows[j][i][0], rows[j + 1][i + 1][0], rows[j + 1][i][0])
                m.face(quad, rows[j][i][1] + rows[j + 1][i + 1][1], "membrane")
    top, bot = skins
    jl = len(vs) - 1
    for i in range(len(us) - 1):
        quad = (top[jl][i][0], top[jl][i + 1][0], bot[jl][i + 1][0], bot[jl][i][0])
        um = (us[i] + us[i + 1]) * 0.5
        m.face(quad, at(um, 1.0) - at(um, 0.85), "membrane edge")
    for i_edge, sgn in ((0, -1.0), (len(us) - 1, 1.0)):
        for j in range(len(vs) - 1):
            quad = (top[j][i_edge][0], top[j + 1][i_edge][0], bot[j + 1][i_edge][0], bot[j][i_edge][0])
            if min((m.verts[top[j][i_edge][0]] - m.verts[bot[j][i_edge][0]]).length, (m.verts[top[j + 1][i_edge][0]] - m.verts[bot[j + 1][i_edge][0]]).length) < 0.04:
                continue
            u = us[i_edge]
            v = max((vs[j] + vs[j + 1]) * 0.5, 0.05)
            out = at(min(max(u + 0.03 * sgn, 0.0), 1.0), v) - at(min(max(u - 0.03 * sgn, 0.0), 1.0), v)
            if out.length < 1e-6:
                continue
            m.face(quad, out, "membrane side")


# ---------------------------------------------------------------- the body, the knobs, the weed

def body_point(lat, lon):
    r = Vector((BODY_R.x * math.cos(lat) * math.sin(lon), BODY_R.y * math.sin(lat), BODY_R.z * math.cos(lat) * math.cos(lon)))
    bump = 1.0 + (0.04 * math.sin(4.0 * lon + 3.0 * lat) + 0.03 * math.sin(7.0 * lon - 5.0 * lat + 1.0)) * math.cos(lat)
    return BODY_C + r * bump


def body(m, q):
    lat0 = math.asin((BODY_CUT - BODY_C.y) / BODY_R.y)
    rows = []
    for i in range(q.body_rings + 1):
        lat = lat0 + (PI / 2 - lat0) * (i / q.body_rings) ** 0.8
        row = []
        if i == q.body_rings:
            idx = m.add(BODY_C + Vector((0.0, BODY_R.y, 0.0)), (0.5, 1.0), 0)
            row = [idx] * (q.body_round + 1)
        else:
            for j in range(q.body_round + 1):
                lon = TAU * j / q.body_round
                row.append(m.add(body_point(lat, lon), (j / q.body_round, (lat - lat0) / (PI / 2 - lat0)), 0))
        rows.append(row)
    for i in range(len(rows) - 1):
        a, b = rows[i], rows[i + 1]
        for j in range(q.body_round):
            quad = [a[j], a[j + 1], b[j + 1], b[j]]
            pts = []
            for x in quad:
                if x not in pts:
                    pts.append(x)
            mid = sum((m.verts[x] for x in pts), Vector()) / len(pts)
            m.face(pts, mid - BODY_C, "body")
    # (its floor: flat, facing down)
    ring = rows[0][:-1]
    c = m.add(Vector((BODY_C.x, BODY_CUT, BODY_C.z)), (0.5, 0.0), 0)
    for j in range(len(ring)):
        m.face((ring[j], ring[(j + 1) % len(ring)], c), Vector((0.0, -1.0, 0.0)), "body")


def knobs(m, q):
    """A row of knobs down its back, behind the head."""
    sides = 6 if q.kind == "game" else 12
    for k in range(6):
        lon = 0.0
        lat = 1.05 - 0.13 * k
        base = body_point(lat, PI - 0.0) if False else None
        z = BODY_C.z + 1.0 + k * 1.7
        f = (z - BODY_C.z) / BODY_R.z
        y = BODY_C.y + BODY_R.y * math.sqrt(max(0.0, 1.0 - f * f))
        p0 = Vector((0.0, y - 0.6, z))
        h = 1.6 - 0.15 * k
        path = [p0, p0 + Vector((0.0, h * 0.6, 0.25)), p0 + Vector((0.0, h, 0.7))]
        tube(m, path, [0.9 - 0.06 * k, 0.55 - 0.04 * k, 0.12], sides, 10, "knob", lambda i, a: (a, i / 2.0), 0.0, Vector((0.0, 0.0, 1.0)))


def blade(m, q, root, way, flat, length, width, part, uv_root, extra_root, host_head, seed):
    """A ribbon of weed: two sheets back to back, waving and curling over as it rises."""
    rnd = random.Random(seed)
    segs = q.weed_segs
    way = way.normalized()
    side = way.cross(flat).normalized()
    across = side.cross(way).normalized()
    lean = across * rnd.uniform(-0.5, 0.5) + side * rnd.uniform(-0.3, 0.3)
    wave = rnd.uniform(0.08, 0.18) * length
    ph = rnd.uniform(0.0, TAU)
    rows = []
    for k in range(segs + 1):
        f = k / segs
        c = root + way * (length * f * (1.0 - 0.25 * f)) + lean * (length * f * f) + across * (wave * (math.sin(ph + f * 4.0) - math.sin(ph)) * f)
        w = width * (1.0 - 0.75 * f) * (0.45 + 0.55 * min(f * 4.0, 1.0))
        rows.append((c - side * w, c + side * w, f))
    for sheet in (1.0, -1.0):
        idx = []
        for l, r, f in rows:
            if part == 9:
                uv, ex = uv_root, f
            else:
                uv, ex = (0.0, f), (1.0 if host_head else 0.0)
            idx.append((m.add(l, uv, part, ex), m.add(r, uv, part, ex)))
        for k in range(segs):
            quad = (idx[k][0], idx[k][1], idx[k + 1][1], idx[k + 1][0])
            pa, pb = m.verts[idx[k][0]], m.verts[idx[k][1]]
            pc = m.verts[idx[k + 1][0]]
            n = (pb - pa).cross(pc - pa)
            m.face(quad, n * sheet, "weed")


def clump(m, q, p, n, count, length, part, uv_root, host_head, seed):
    rnd = random.Random(seed)
    for b in range(count):
        way = (n + Vector((rnd.uniform(-0.5, 0.5), 0.7, rnd.uniform(-0.5, 0.5)))).normalized()
        flat = Vector((rnd.uniform(-1, 1), 0.0, rnd.uniform(-1, 1))).normalized()
        if abs(flat.dot(way)) > 0.9:
            flat = Vector((1.0, 0.0, 0.0))
        off = Vector((rnd.uniform(-0.6, 0.6), 0.0, rnd.uniform(-0.6, 0.6)))
        blade(m, q, p - n * 0.25 + off, way, flat, length * rnd.uniform(0.6, 1.1), 0.5, part, uv_root, 0.0, host_head, seed * 13 + b)


def weeds(m, q):
    if q.weeds <= 0.0:
        return
    rnd = random.Random(3)
    per = 3 if q.kind == "full" else 2
    for k in range(int(7 * q.weeds)):
        t = rnd.uniform(0.35, 0.85)
        a = rnd.uniform(-1.3, 1.3)
        clump(m, q, head_point(t, a), head_normal(t, a), per + 1, rnd.uniform(4.5, 7.0), 8, None, True, 10 + k)
    for k in range(int(6 * q.weeds)):
        lat = rnd.uniform(0.3, 1.0)
        lon = rnd.uniform(0.6, 2.4) * (1 if k % 2 else -1)
        p = body_point(lat, lon)
        clump(m, q, p, (p - BODY_C).normalized(), per, rnd.uniform(2.5, 4.5), 8, None, False, 50 + k)
    # along the tops of the wings' arms
    for sx in (1.0, -1.0):
        arm = chain([mirror(ELBOW, sx), mirror(WRIST, sx)], 20)
        for k in range(int(5 * q.weeds)):
            p = along(arm, rnd.uniform(0.1, 0.8)) + Vector((0.0, 0.4, 0.0))
            n = Vector((sx * 0.7, 0.7, 0.0)).normalized()
            clump(m, q, p, n, per - 1, rnd.uniform(2.0, 3.5), 9, (0.0, attach_of(p, sx)), False, 90 + k + (0 if sx > 0 else 40))


# ---------------------------------------------------------------- making, checking, writing

def make(kind):
    q = Q(kind)
    m = Mesh()
    body(m, q)
    head(m, q)
    for i, (t, a, r) in enumerate(EYES):
        eye(m, q, i, t, a, r)
    which = LO_TENTACLES if kind == "lo" else range(len(TENTACLES))
    for i in which:
        tentacle(m, q, i, TENTACLES[i])
    for sx in (1.0, -1.0):
        wing(m, q, sx)
    if q.knobs:
        knobs(m, q)
    weeds(m, q)
    name = NAME + {"full": "", "game": "_game", "lo": "_lo"}[kind]
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
    material = bpy.data.materials.get(NAME) or bpy.data.materials.new(NAME)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.2, 0.32, 0.32, 1.0)
    material.diffuse_color = (0.2, 0.32, 0.32, 1.0)
    mesh.materials.append(material)
    mesh.update()
    winding(name, mesh, m)
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.set_sharp_from_angle(angle=math.radians(60.0))
    mesh.update()
    shading(name, mesh, m)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    lo = Vector((min(p.x for p in m.verts), min(p.y for p in m.verts), min(p.z for p in m.verts)))
    hi = Vector((max(p.x for p in m.verts), max(p.y for p in m.verts), max(p.z for p in m.verts)))
    print("BUILT %s verts=%d tris=%d box=%s..%s" % (name, len(mesh.vertices), tris, tuple(round(x, 2) for x in lo), tuple(round(x, 2) for x in hi)))
    return obj


def winding(name, mesh, m):
    bad = {}
    for poly in mesh.polygons:
        out, group = m.out[poly.index]
        if poly.normal.dot(to_b(out)) <= 0.0:
            bad[group] = bad.get(group, 0) + 1
    told = ["%s %d/%d wrong" % (g, bad.get(g, 0), c) for g, c in m.count.items()]
    print("WINDING %s: %s: %s" % (name, "ok" if not bad else "INSIDE OUT", ", ".join(told)))


def shading(name, mesh, m):
    """As Godot will read it: no face may be wound against the smoothed normals of its own corners (where a
    face turns against its neighbours, a fold, the shading normals say it faces the other way)."""
    bad = {}
    shown = 0
    normals = mesh.corner_normals
    mesh.calc_loop_triangles()
    for tri in mesh.loop_triangles:
        n = Vector((0.0, 0.0, 0.0))
        for li in tri.loops:
            n += normals[li].vector
        if n.dot(tri.normal) <= 0.0:
            group = m.out[tri.polygon_index][1]
            bad[group] = bad.get(group, 0) + 1
            if shown < 6 and "--why" in ARGS:
                shown += 1
                print("  against its corners: %s at %s" % (group, tuple(round(x, 2) for x in tri.center)))
    print("SHADING %s: %s %s" % (name, "ok" if not bad else "FACES AGAINST THEIR NORMALS", bad))


def export_one(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_yup=True, use_selection=True,
                              export_animations=False, export_texcoords=True)


def render(folder, made):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_cavity = True
    scene.display.shading.show_backface_culling = True
    scene.render.resolution_x, scene.render.resolution_y = 1200, 800
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.06, 0.08)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    # (Blender space: its face towards +Y, up Z)
    views = [("front", (0, 1, 0.12), (0, 0, 8), 52), ("back", (0, -1, 0.12), (0, 0, 8), 52),
             ("left", (1, 0, 0.1), (0, 0, 8), 56), ("right", (-1, 0, 0.1), (0, 0, 8), 56),
             ("above", (0.001, 0.0, 1), (0, 0, 0), 56), ("quarter", (0.8, 1.0, 0.45), (0, 0, 7), 54),
             ("head", (0.35, 1.0, 0.35), (0, 6, 9), 22), ("concept", (-0.5, 1.0, 0.25), (0, 0, 8), 52)]
    for prefix, obj in zip(("", "game_", "lo_"), made):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if prefix == "lo_" and view not in ("quarter", "front"):
                continue
            offset = Vector(direction).normalized() * 200.0
            camera.data.ortho_scale = frame
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % (prefix, view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    full = make("full")
    game = make("game")
    low = make("lo")
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, NAME + ".glb"))
    export_one(game, os.path.join(OUT, NAME + "_game.glb"))
    export_one(low, os.path.join(OUT, NAME + "_lo.glb"))
    print("SHADER HEAD_A=%s HEAD_B=%s SPREAD_AXIS=(%.4f, %.4f, %.4f) UPF=(%.4f, %.4f, %.4f)" % (
        tuple(HEAD_A), tuple(HEAD_B), SPREAD_AXIS.x, SPREAD_AXIS.y, SPREAD_AXIS.z, UPF.x, UPF.y, UPF.z))
    game.location.x = 60.0
    low.location.x = 120.0
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, NAME + ".blend"))
    game.location.x = 0.0
    low.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, game, low])


if __name__ == "__main__":
    main()
