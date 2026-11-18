"""Builds the Atlantic horseshoe crab (creatures/horseshoe_crab) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/horseshoe_crab/tools/build_horseshoe_crab.py
    blender --background --python creatures/horseshoe_crab/tools/build_horseshoe_crab.py -- <preview folder>   # with pictures

Writes creatures/horseshoe_crab/models/horseshoe_crab.glb (the full model), horseshoe_crab_game.glb (the game
model: few triangles, spent where the eye looks: the shells' outline and the flare of the rim, the eyes, the tail
spike) and horseshoe_crab_lo.glb (far off, phones), and the editable creatures/horseshoe_crab/tools/horseshoe_crab.blend
(all three; this folder has a .gdignore). The full and the low model come out as they did before the game model
was added. Each
is one still mesh with one surface: the shader (horseshoe_crab.gdshader) draws every marking, walks its legs,
flaps its book gills, swings its tail spike and bends its rear shell on its hinge. It prints a WINDING line for
each: the check that nothing is inside out.

An Atlantic horseshoe crab (Limulus polyphemus), 0.5 m from the front of its shell to the tip of its tail spike,
built from the species (no picture was traced or copied):

- THE FRONT SHELL (prosoma): a smooth dome, horseshoe-shaped from above (round in front, its rear corners points),
  wider (0.25 m) than long (0.16 m), flaring to a thin rim close to the ground; a ridge down its middle and a
  ridge either side of it, a kidney-shaped compound eye on the outside of each side ridge; beneath, a vault over
  the legs.
- THE REAR SHELL (opisthosoma), hinged to the front one: a smaller shield narrowing to the back, with six movable
  spines along each side edge, a row of short spines down its middle, a notch at its back for the tail.
- THE TAIL SPIKE (telson): long (0.24 m), rigid, three-sided with a keel along its top, tapering to a point.
- FIVE PAIRS OF WALKING LEGS under the front shell, from round the mouth, mostly hidden under it.
- FIVE BOOK GILLS under the rear shell, broad flaps lying back one over the next.

Everything here is in Godot space (metres, Y up, X to its left side, its head at -Z) until it is written out.
THE ORIGIN IS ON THE GROUND under its middle (half way from the front of its shell to the tip of its tail spike):
its feet stand at y 0.

What a point is, for the shader: see `Mesh` below. The parts: 0 the front shell (UV2.x 1 on its underside), 1 the
rear shell (UV2.x 1 on its underside), 2 the tail spike (`a` 0 at its root to 1 at its tip), 3 a walking leg
(`index` which, 0 the first; `root` its joint with the body, `k` its knee, `a` 0 above the knee and 1 below it), 4
a book gill (`index` 0 the first to 4 the last; `root` its hinge; `a` 0 at its hinge to 1 at its free edge), 5 an
eye, 6 a spine of the rear shell. On the shells UV.x is how far out from the middle of the shell (0 to 1, the rim).

The numbers marked "as the shader has it" are in horseshoe_crab.gdshader too: change one, change the other.
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
TAU = math.tau
UP = Vector((0.0, 1.0, 0.0))
X = Vector((1.0, 0.0, 0.0))

PROSOMA, OPISTHOSOMA, TELSON, LEG, GILL, EYE, SPINE = range(7)
# As the shader has it: the box the joints' places are written in; how far out along a leg its knee is; the
# hinge between the two shells; the tail spike's root.
BOX = (Vector((-0.2, 0.0, -0.3)), Vector((0.2, 0.15, 0.3)))
KNEE_AT = 0.45
HINGE = Vector((0.0, 0.03, -0.092))
TAIL_ROOT = Vector((0.0, 0.022, 0.006))


def pick(low, full, lo, game):
    """The full model's number, the low one's or the game one's (`low` is False, True or "game")."""
    if low == "game":
        return game
    return lo if low else full


def to_b(p):
    """Godot's space (Y up, head at -Z) to Blender's (Z up, head at +Y)."""
    return Vector((p.x, -p.z, p.y))


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


class Mesh:
    """The model as it is being made. What is written at each point, for the shader:
    UV2.y the part times 16 plus `index`; the colour's red, green and blue `root` (the joint the part turns
    about, as a place in BOX: 0 its least corner, 1 its greatest); the colour's alpha `a`; UV.x, UV.y and UV2.x
    `k` (three numbers: on a leg its knee, in metres; on a shell how far out, unused, and 1 on its underside).
    (The glTF writer flips V: what is written is 1 - v, so that Godot reads v.)"""

    def __init__(self):
        self.verts = []
        self.faces = []
        self.data = []
        self.out = []
        self.count = {}
        self.part = 0
        self.index = 0
        self.root = None
        self.k = Vector((0.0, 0.0, 0.0))
        self.a = 0.0

    def add(self, p, k=None, a=None):
        k = self.k if k is None else k
        a = self.a if a is None else a
        colour = (0.0, 0.0, 0.0)
        if self.root is not None:
            colour = tuple((self.root[i] - BOX[0][i]) / (BOX[1][i] - BOX[0][i]) for i in range(3))
            assert all(0.0 <= c <= 1.0 for c in colour), "a joint outside BOX: %s" % (self.root,)
        self.verts.append(Vector(p))
        self.data.append(((k[0], 1.0 - k[1]), (k[2], 1.0 - (self.part * 16 + self.index)), (colour[0], colour[1], colour[2], a)))
        return len(self.verts) - 1

    def face(self, points, out, name):
        """A face wound so that its front (the side its points go round anticlockwise) is towards `out`."""
        ps = [self.verts[i] for i in points]
        n = Vector((0.0, 0.0, 0.0))
        for i in range(len(ps)):
            n += ps[i].cross(ps[(i + 1) % len(ps)])
        if n.length < 1e-16:
            return
        if n.dot(out) < 0.0:
            points = tuple(reversed(points))
        self.faces.append(tuple(points))
        self.out.append((Vector(out), name))
        self.count[name] = self.count.get(name, 0) + 1


def loft(m, rings, name, cap0=None, cap1=None, tags=None, out=None):
    centres = [sum(r, Vector()) / len(r) for r in rings]
    rows = []
    for ri, ring in enumerate(rings):
        row = []
        for ci, p in enumerate(ring):
            k, a = tags(p, ri, ci) if tags else (None, None)
            row.append(m.add(p, k, a))
        rows.append(row)
    count = len(rings[0])
    for r in range(len(rows) - 1):
        between = (centres[r] + centres[r + 1]) * 0.5
        for c in range(count):
            n = (c + 1) % count
            quad = (rows[r][c], rows[r][n], rows[r + 1][n], rows[r + 1][c])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, out(middle) if out else middle - between, name)
    for cap, row, centre, other, ri in ((cap0, rows[0], centres[0], centres[min(1, len(rings) - 1)], 0),
                                        (cap1, rows[-1], centres[-1], centres[max(len(rings) - 2, 0)], len(rings) - 1)):
        if cap is None:
            continue
        at = centre if cap is True else Vector(cap)
        k, a = tags(at, ri, -1) if tags else (None, None)
        tip = m.add(at, k, a)
        way = centre - other
        if cap is not True and (at - centre).length > 1e-12:
            way = way + (at - centre)
        for c in range(count):
            n = (c + 1) % count
            middle = (m.verts[tip] + m.verts[row[c]] + m.verts[row[n]]) / 3.0
            m.face((tip, row[c], row[n]), out(middle) if out else way, name)


def frames(path, ref=None):
    count = len(path)
    tangents = [(path[min(i + 1, count - 1)] - path[max(i - 1, 0)]).normalized() for i in range(count)]
    if ref is None:
        ref = UP if abs(tangents[0].y) < 0.9 else X
    u = Vector(ref)
    made = []
    for t in tangents:
        u = (u - t * u.dot(t)).normalized()
        made.append((t, u, t.cross(u)))
    return made


# The game model's tubes have few sides: each is made a little fatter, so that it looks as wide as the round
# one it stands for, seen from any side (a polygon of `sides` as wide on average as the circle).
FAT = [lambda sides: 1.0]


def game_fat(sides):
    return math.pi / (sides * math.sin(math.pi / sides))


def game_rings(knots, grooves, gap, fine=0.0):
    """Where the game model's rings go along the body: at every knot of its outline (where its curve
    turns), at each groove (and `fine` either side of it), and nowhere further apart than `gap`; two
    closer than a tenth of `gap` are one."""
    zs = sorted(set(list(knots) + [b + d for b in grooves for d in ((-fine, 0.0, fine) if fine else (0.0,))]))
    zs = [z for z in zs if knots[0] <= z <= knots[-1]]
    made = [zs[0]]
    for z in zs[1:]:
        start = made[-1]
        if z - start < gap * 0.1:
            if z == zs[-1]:
                made[-1] = z
            continue
        n = max(1, math.ceil((z - start) / gap - 1e-9))
        made += [start + (z - start) * i / n for i in range(1, n)] + [z]
    return made


def tube(m, path, radii, sides, name, caps=(True, True)):
    path = [Vector(p) for p in path]
    made = frames(path)
    rings = [[p + (u * math.cos(TAU * s / sides) + v * math.sin(TAU * s / sides)) * max(r, 1e-5) * FAT[0](sides) for s in range(sides)]
             for (t, u, v), p, r in zip(made, path, radii)]
    loft(m, rings, name,
         cap0=(path[0] - made[0][0] * radii[0] * 0.5) if caps[0] else None,
         cap1=(path[-1] + made[-1][0] * radii[-1] * 0.5) if caps[1] else None)


def ellipsoid(m, centre, axes, radii, name, lat, lon):
    centre = Vector(centre)
    e0, e1, e2 = axes
    rings = []
    for i in range(1, lat):
        th = math.pi * i / lat
        rings.append([centre - e0 * (radii[0] * math.cos(th)) + e1 * (radii[1] * math.sin(th) * math.cos(TAU * j / lon))
                      + e2 * (radii[2] * math.sin(th) * math.sin(TAU * j / lon)) for j in range(lon)])
    loft(m, rings, name, cap0=centre - e0 * radii[0], cap1=centre + e0 * radii[0], out=lambda middle: middle - centre)


def blade(m, name, point, facing, thick, nt, nu, tags=None):
    """A thin closed blade: `point(t, u)` a place in the model, `facing` the way one of its two skins faces."""
    facing = Vector(facing).normalized()
    for side in (1.0, -1.0):
        grid = []
        for ti in range(nt + 1):
            t = ti / nt
            row = []
            for ui in range(nu + 1):
                u = ui / nu
                foil = 2.6 * math.sqrt(u) * (1.0 - u)
                swell = thick * (1.0 - 0.7 * t) * foil
                p = point(t, u) + facing * (side * swell * 0.5)
                k, a = tags(t, u) if tags else (None, None)
                row.append(m.add(p, k, a))
            grid.append(row)
        for ti in range(nt):
            for ui in range(nu):
                m.face((grid[ti][ui], grid[ti][ui + 1], grid[ti + 1][ui + 1], grid[ti + 1][ui]), facing * side, name)


# --- the shells -----------------------------------------------------------------------------------

# Each shell's outline seen from above, its left half from the middle of its front round to the middle of its
# back (x, z); and the middle it is built out from.
PROSOMA_OUTLINE = [(0.0, -0.250), (0.045, -0.2435), (0.080, -0.2255), (0.104, -0.199), (0.119, -0.168), (0.1255, -0.137),
                   (0.1245, -0.108), (0.119, -0.086), (0.112, -0.070), (0.092, -0.079), (0.074, -0.0875), (0.040, -0.0915), (0.0, -0.092)]
PROSOMA_MIDDLE = Vector((0.0, 0.0, -0.160))
OPISTHOSOMA_OUTLINE = [(0.0, -0.100), (0.055, -0.0995), (0.073, -0.094), (0.0715, -0.078), (0.066, -0.058), (0.057, -0.038),
                       (0.045, -0.018), (0.031, -0.002), (0.016, 0.009), (0.008, 0.012), (0.0, 0.006)]
OPISTHOSOMA_MIDDLE = Vector((0.0, 0.0, -0.050))
# How high the rim stands off the ground, how high each dome rises above it.
CLEAR = 0.012
PROSOMA_HIGH = 0.062
OPISTHOSOMA_HIGH = 0.026
# The rear shell's movable spines: where along its side edge (z), how long.
EDGE_SPINES = [(-0.082, 0.014), (-0.068, 0.016), (-0.054, 0.017), (-0.040, 0.017), (-0.026, 0.016), (-0.012, 0.014)]


def outline_points(half, per_side):
    """The whole outline, both halves, as points (left half, then the right half mirrored back), each segment
    cut in `per_side` pieces."""
    left = []
    for i in range(len(half) - 1):
        a = Vector((half[i][0], 0.0, half[i][1]))
        b = Vector((half[i + 1][0], 0.0, half[i + 1][1]))
        for k in range(per_side):
            left.append(a.lerp(b, k / per_side))
    left.append(Vector((half[-1][0], 0.0, half[-1][1])))
    # (the right half: the left mirrored, back from the rear middle to the front, the two middles not twice)
    right = [Vector((-p.x, 0.0, p.z)) for p in reversed(left[1:-1])]
    return left + right


def prosoma_top(s, p):
    """How high the front shell's top is at `s` (0 its middle to 1 its rim) and `p` (the place on the ground
    under it): a dome flaring to the rim, a ridge down its middle, a ridge each side."""
    # (a smooth dome on an ellipse, not on the outline, so that the horseshoe's corners are flat flanges and no
    # crease runs to them; brought down to the rim at the outline)
    e = math.hypot(p.x / 0.126, (p.z - PROSOMA_MIDDLE.z) / 0.086)
    dome = PROSOMA_HIGH * math.cos(min(e, 1.0) * math.pi * 0.5) ** 1.3 * (1.0 - min(s, 1.0) ** 6)
    keep = 1.0 - smooth(0.72, 0.92, s)
    ridges = 0.0045 * math.exp(-(p.x / 0.007) ** 2) * keep * smooth(-0.245, -0.215, p.z)
    side = 0.038 + 0.22 * (p.z + 0.16)
    for sx in (1.0, -1.0):
        ridges += 0.004 * math.exp(-((p.x - sx * side) / 0.0075) ** 2) * keep * smooth(-0.235, -0.2, p.z)
    # (the rear edge stands up at the hinge, over the front of the rear shell)
    hinge = 0.032 * smooth(-0.125, -0.092, p.z) * math.exp(-(p.x / 0.055) ** 2)
    return CLEAR + 0.0035 + max(dome, hinge) + ridges


def prosoma_under(s, p):
    """The vault under the front shell: a little over half as high as its top everywhere (so it never comes
    through the top), meeting it at the rim."""
    return CLEAR + 0.58 * (prosoma_top(s, p) - CLEAR - 0.0035)


def opisthosoma_top(s, p):
    e = math.hypot(p.x / 0.072, (p.z - OPISTHOSOMA_MIDDLE.z) / 0.056)
    dome = OPISTHOSOMA_HIGH * math.cos(min(e, 1.0) * math.pi * 0.5) ** 1.2 * (1.0 - min(s, 1.0) ** 6)
    keel = 0.004 * math.exp(-(p.x / 0.006) ** 2) * (1.0 - smooth(0.75, 0.95, s))
    # (its front stands up at the hinge, under the rear edge of the front shell)
    hinge = 0.027 * (1.0 - smooth(-0.1, -0.055, p.z)) * math.exp(-(p.x / 0.05) ** 2)
    return CLEAR + 0.004 + max(dome, hinge) + keel


def opisthosoma_under(s, p):
    return CLEAR + 0.45 * (opisthosoma_top(s, p) - CLEAR - 0.004)


def shield(m, part, outline, middle, top, under, rings, name, under_rings, steps=None, under_steps=None):
    """A shell: its top built out from `middle` to the outline in `rings` steps, its rim, and its underside.
    `steps` and `under_steps`, if given, are where (0 the middle to 1 the rim) its rings are instead."""
    m.part, m.index, m.root, m.a = part, 0, None, 0.0
    count = len(outline)

    def grid(levels, height, below, given=None):
        rows = []
        for i in range(1, (len(given) if given else levels) + 1):
            s = given[i - 1] if given else i / levels
            row = []
            for q in outline:
                p = middle + (q - middle) * s
                row.append(m.add(Vector((p.x, height(s, p), p.z)), Vector((s, 0.0, 1.0 if below else 0.0))))
            rows.append(row)
        centre = m.add(Vector((middle.x, height(0.0, middle), middle.z)), Vector((0.0, 0.0, 1.0 if below else 0.0)))
        return rows, centre

    tops, centre = grid(rings, top, False, steps)
    for c in range(count):
        n = (c + 1) % count
        m.face((centre, tops[0][c], tops[0][n]), UP, name)
    for r in range(len(tops) - 1):
        for c in range(count):
            n = (c + 1) % count
            quad = (tops[r][c], tops[r][n], tops[r + 1][n], tops[r + 1][c])
            ps = [m.verts[q] for q in quad]
            # (up, and out from the middle where it slopes)
            mid = sum(ps, Vector()) * 0.25
            m.face(quad, UP + (mid - Vector((middle.x, mid.y, middle.z))) * 2.0, name)
    unders, centre_u = grid(under_rings, under, True, under_steps)
    for c in range(count):
        n = (c + 1) % count
        m.face((centre_u, unders[0][c], unders[0][n]), -UP, name)
    for r in range(len(unders) - 1):
        for c in range(count):
            n = (c + 1) % count
            quad = (unders[r][c], unders[r][n], unders[r + 1][n], unders[r + 1][c])
            mid = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, -UP - (mid - Vector((middle.x, mid.y, middle.z))) * 1.0, name)
    # the rim: the top's edge down to the underside's
    for c in range(count):
        n = (c + 1) % count
        a, b = tops[-1][c], tops[-1][n]
        quad = (a, b, unders[-1][n], unders[-1][c])
        mid = sum((m.verts[q] for q in quad), Vector()) * 0.25
        m.face(quad, mid - Vector((middle.x, mid.y, middle.z)), name)
    return tops


def surface_height(outline, middle, top, at):
    """How high a shell's top is over the place `at` (x, z): found along the ray from its middle."""
    d = Vector((at[0], 0.0, at[1])) - middle
    best = None
    count = len(outline)
    for c in range(count):
        a = outline[c] - middle
        b = outline[(c + 1) % count] - middle
        # where the ray along d meets the segment a..b
        den = d.x * (b.z - a.z) - d.z * (b.x - a.x)
        if abs(den) < 1e-12:
            continue
        t = (a.x * (b.z - a.z) - a.z * (b.x - a.x)) / den
        u = (a.x * d.z - a.z * d.x) / den
        if t > 0.0 and 0.0 <= u <= 1.0:
            best = t if best is None else min(best, t)
    s = 1.0 / best if best else 0.0
    p = middle + d
    return top(s, p), s


def shells(m, low):
    # (the game model: its rings close together where the dome flares down to the rim, few over the smooth top;
    # the outline is straight between its points, so fewer points along it lose nothing of it)
    game = low == "game"
    shield(m, PROSOMA, outline_points(PROSOMA_OUTLINE, pick(low, 6, 2, 2)), PROSOMA_MIDDLE, prosoma_top, prosoma_under,
           4 if low else 16, "front shell", 2 if low else 7,
           (0.22, 0.42, 0.6, 0.75, 0.87, 0.95, 1.0) if game else None, (0.55, 1.0) if game else None)
    m.root = HINGE
    shield(m, OPISTHOSOMA, outline_points(OPISTHOSOMA_OUTLINE, 1 if low else 4), OPISTHOSOMA_MIDDLE, opisthosoma_top,
           opisthosoma_under, 3 if low else 10, "rear shell", 2 if low else 5,
           (0.3, 0.6, 0.82, 0.95, 1.0) if game else None, (0.6, 1.0) if game else None)
    # the spines of the rear shell: six along each side edge, a row down its middle
    m.part, m.index = SPINE, 0
    sides = pick(low, 6, 3, 3)
    outline = outline_points(OPISTHOSOMA_OUTLINE, 8)
    for z, long in EDGE_SPINES:
        for sx in (1.0, -1.0):
            # (the edge there: the outline point nearest that z on this side)
            edge = min((q for q in outline if q.x * sx > 0.0), key=lambda q: abs(q.z - z))
            y = opisthosoma_top(1.0, edge) - 0.001
            root = Vector((edge.x - sx * 0.003, y, edge.z))
            tip = root + Vector((sx * long * 0.55, -0.002, long * 0.83))
            cone(m, root, tip, 0.0028, sides, "spines")
    if low is not True:
        for z in (-0.075, -0.05, -0.025):
            h, s = surface_height(outline, OPISTHOSOMA_MIDDLE, opisthosoma_top, (0.0, z))
            cone(m, Vector((0.0, h - 0.002, z)), Vector((0.0, h + 0.006, z + 0.004)), 0.0022, pick(low, 5, 0, 4), "spines")
    m.root = None


def cone(m, base, tip, radius, sides, name):
    """A spine standing on a surface (its foot is sunk in it, so it has no floor)."""
    t, u, v = frames([Vector(base), Vector(tip)])[0]
    ring = [base + (u * math.cos(TAU * s / sides) + v * math.sin(TAU * s / sides)) * radius for s in range(sides)]
    middle = (base + tip) * 0.5
    loft(m, [ring], name, cap1=tip, out=lambda at: (at - middle) - t * (at - middle).dot(t) + t * radius * 0.2)


def eyes(m, low):
    outline = outline_points(PROSOMA_OUTLINE, 6)
    m.part, m.index, m.root = EYE, 0, None
    for sx in (1.0, -1.0):
        x, z = sx * 0.071, -0.168
        h, s = surface_height(outline, PROSOMA_MIDDLE, prosoma_top, (x, z))
        # (lying along the side ridge, its outer face tilted out)
        along = Vector((sx * 0.22, 0.0, 1.0)).normalized()
        out = Vector((sx * 0.8, 0.6, 0.0)).normalized()
        across = out.cross(along).normalized()
        ellipsoid(m, Vector((x, h - 0.0016, z)), (along, across, out), (0.013, 0.0062, 0.0045), "eyes", pick(low, 8, 4, 6), pick(low, 12, 6, 14))
        if sx > 0.0 and low is False:
            print("EYE the left one's middle (%.4f, %.4f, %.4f), along (%.3f, %.3f, %.3f), out (%.3f, %.3f, %.3f)" % ((x, h - 0.0016, z) + tuple(along) + tuple(out)))


def telson(m, low):
    """The tail spike: three-sided with a keel along its top, tapering to a point."""
    steps = pick(low, 30, 6, 12)
    m.part, m.index, m.root = TELSON, 0, TAIL_ROOT
    rings = []
    for i in range(steps + 1):
        t = i / steps
        z = TAIL_ROOT.z + (0.25 - TAIL_ROOT.z) * t
        y = TAIL_ROOT.y + 0.010 * math.sin(math.pi * t * 0.8) - 0.016 * t
        wide = 0.0095 * (1.0 - t) ** 0.85 + 0.0005
        high = 0.0085 * (1.0 - t) ** 0.8 + 0.0005
        rings.append([Vector((0.0, y + high, z)), Vector((wide, y - 0.1 * high, z)), Vector((0.0, y - 0.45 * high, z)), Vector((-wide, y - 0.1 * high, z))])

    def tags(p, ri, ci):
        return None, ri / steps if ri >= 0 else 1.0

    loft(m, rings, "tail spike", cap0=True, cap1=rings[-1][0].lerp(rings[-1][2], 0.5) + Vector((0.0, 0.0, 0.002)), tags=tags)
    m.a = 0.0
    m.root = None


# The legs of one side, first to last: (where its joint is, the way it points in degrees from straight out to its
# side towards the tail, how far out its tip stands, how high its knee is, how thick).
LEGS = [((0.010, 0.028, -0.188), -48.0, 0.060, 0.021, 0.0042),
        ((0.012, 0.029, -0.176), -22.0, 0.068, 0.028, 0.0045),
        ((0.013, 0.029, -0.163), 2.0, 0.072, 0.030, 0.0047),
        ((0.013, 0.028, -0.150), 26.0, 0.072, 0.028, 0.0048),
        ((0.012, 0.025, -0.140), 44.0, 0.074, 0.020, 0.0052)]


def leg(m, index, root, heading, reach, knee_high, radius, sides, low):
    """A walking leg, in the upright plane through `root` that looks along `heading`: out and up to its knee,
    KNEE_AT of the way out, then down to its tip on the ground `reach` out (as the shader works it out again)."""
    root = Vector(root)
    side = 1.0 if root.x >= 0.0 else -1.0
    angle = math.radians(heading)
    d = Vector((side * math.cos(angle), 0.0, math.sin(angle)))
    knee = root + d * (KNEE_AT * reach)
    knee.y = knee_high
    tip = root + d * reach
    tip.y = 0.0
    bend = knee.lerp(tip, 0.5) + d * (0.05 * reach) + UP * (0.02 * reach)
    m.part, m.index, m.root, m.k = LEG, index, root, knee
    m.a = 0.0
    if low:
        # (the game model: no cap at the knee on the upper length, the lower one's cap closes it)
        tube(m, [root, knee], [radius, radius * 0.95], sides, "legs", caps=(False, low != "game"))
    else:
        tube(m, [root, root.lerp(knee, 0.5), knee], [radius * 1.05, radius * 1.1, radius * 0.95], sides, "legs")
    m.a = 1.0
    if low:
        tube(m, [knee, bend, tip], [radius * 0.9, radius * 0.7, radius * 0.25], sides, "legs", caps=(True, False))
    else:
        tube(m, [knee, knee.lerp(bend, 0.5), bend, bend.lerp(tip, 0.5), tip],
             [radius * 0.9, radius * 0.88, radius * 0.75, radius * 0.6, radius * 0.25], sides, "legs")
    m.root = None
    m.a = 0.0
    m.index = 0
    m.k = Vector((0.0, 0.0, 0.0))


# As the shader has it: where each book gill hangs from (z) under the rear shell.
GILLS = (-0.086, -0.072, -0.058, -0.044, -0.030)


def gills(m, low):
    outline = outline_points(OPISTHOSOMA_OUTLINE, 8)
    for i, z in enumerate(GILLS):
        wide = 0.050 - 0.004 * i
        y = opisthosoma_under(0.0, OPISTHOSOMA_MIDDLE) - 0.0035 - 0.001 * i
        hinge = Vector((0.0, y, z))
        m.part, m.index, m.root = GILL, i, hinge

        def point(t, u, hinge=hinge, wide=wide):
            # (t back from its hinge, u across from its left end to its right; it lies back and a little down)
            across = (u - 0.5) * 2.0
            return hinge + Vector((across * wide * (1.0 - 0.15 * t), -0.004 * t - 0.002 * across * across, 0.020 * t))

        blade(m, "book gills", point, -UP, 0.0016, pick(low, 4, 2, 2), pick(low, 8, 2, 2), tags=lambda t, u: (None, t))
    m.root = None


def legs_clear():
    """How far each leg (from its joint to its knee and on half way down to its foot) stays under the
    front shell's underside: none may poke through it."""
    outline = outline_points(PROSOMA_OUTLINE, 6)
    worst = 1.0
    for root, heading, reach, knee_high, radius in LEGS:
        angle = math.radians(heading)
        d = Vector((math.cos(angle), 0.0, math.sin(angle)))
        knee = Vector(root) + d * (KNEE_AT * reach)
        knee.y = knee_high
        tip = Vector(root) + d * reach
        tip.y = 0.0
        for t in (0.0, 0.25, 0.5, 0.75, 1.0, 1.15, 1.3, 1.5):
            p = Vector(root).lerp(knee, t) if t <= 1.0 else knee.lerp(tip, t - 1.0)
            roof, s = surface_height(outline, PROSOMA_MIDDLE, prosoma_under, (p.x, p.z))
            worst = min(worst, roof - (p.y + radius))
    print("LEGS CLEAR: the legs stay at least %.4f m under the front shell (less than 0 pokes through)" % worst)


def make(low):
    FAT[0] = game_fat if low == "game" else (lambda sides: 1.0)
    m = Mesh()
    shells(m, low)
    eyes(m, low)
    telson(m, low)
    for sx in (1.0, -1.0):
        for i, (root, heading, reach, knee_high, radius) in enumerate(LEGS):
            leg(m, i, (sx * root[0], root[1], root[2]), heading, reach, knee_high, radius, pick(low, 7, 3, 3), low)
    gills(m, low)
    return m


def material_of(name, colour):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = colour
    material.diffuse_color = colour
    return material


def finish(name, m, colour):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) for p in m.verts], [], m.faces)
    mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.new(name="UV2")
    mesh.color_attributes.new(name="Col", type="FLOAT_COLOR", domain="POINT")
    uv = mesh.uv_layers["UVMap"].data
    uv2 = mesh.uv_layers["UV2"].data
    for poly in mesh.polygons:
        for corner, vi in enumerate(poly.vertices):
            d = m.data[vi]
            uv[poly.loop_start + corner].uv = d[0]
            uv2[poly.loop_start + corner].uv = d[1]
    colours = mesh.color_attributes["Col"]
    for i, d in enumerate(m.data):
        colours.data[i].color = d[2]
    mesh.color_attributes.active_color = colours
    mesh.color_attributes.render_color_index = 0
    mesh.materials.append(material_of("horseshoe_crab", colour))
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    lo = [min(p[i] for p in m.verts) for i in range(3)]
    hi = [max(p[i] for p in m.verts) for i in range(3)]
    print("BUILT %s verts=%d tris=%d from (%.4f, %.4f, %.4f) to (%.4f, %.4f, %.4f)" % ((name, len(mesh.vertices), tris) + tuple(lo) + tuple(hi)))
    bad = {}
    for poly in mesh.polygons:
        out, group = m.out[poly.index]
        if poly.normal.dot(to_b(out)) <= 0.0:
            bad[group] = bad.get(group, 0) + 1
    told = ["%s %d/%d wrong" % (group, bad.get(group, 0), count) for group, count in m.count.items()]
    print("WINDING %s: %s: %s" % (name, "ok" if not bad else "INSIDE OUT", ", ".join(told)))
    return obj


def export_one(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", export_yup=True, use_selection=True,
        export_animations=False, export_texcoords=True,
        export_vertex_color="ACTIVE", export_all_vertex_colors=False,
    )


def render(folder, made, size):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.show_cavity = True
    scene.display.shading.show_backface_culling = True
    scene.display.shading.color_type = "MATERIAL"
    scene.render.resolution_x, scene.render.resolution_y = 1200, 900
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 100.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    views = [("left", (1, 0, 0.0001)), ("front", (0, 1, 0.0001)), ("back", (0, -1, 0.0001)), ("top", (0.0001, 0, 1)),
             ("under", (0.0001, 0, -1)), ("quarter", (0.7, 0.6, 0.45)), ("rear_quarter", (0.6, -0.7, 0.5)), ("low_side", (0.8, 0.3, -0.12))]
    for obj in made:
        for other in made:
            other.hide_render = other is not obj
        for view, direction in views:
            offset = Vector(direction).normalized() * 5.0
            camera.data.ortho_scale = size
            camera.location = Vector((0.0, 0.0, 0.03)) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s_%s.png" % (obj.name, view))
            bpy.ops.render.render(write_still=True)


def main():
    legs_clear()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    full = finish("horseshoe_crab", make(False), (0.36, 0.3, 0.18, 1.0))
    low = finish("horseshoe_crab_lo", make(True), (0.36, 0.3, 0.18, 1.0))
    game = finish("horseshoe_crab_game", make("game"), (0.36, 0.3, 0.18, 1.0))
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, "horseshoe_crab.glb"))
    export_one(low, os.path.join(OUT, "horseshoe_crab_lo.glb"))
    export_one(game, os.path.join(OUT, "horseshoe_crab_game.glb"))
    # (in the .blend: the full model in the middle, the low one to its left, the game one to its right)
    low.location.x = 0.35
    game.location.x = -0.35
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "horseshoe_crab.blend"))
    low.location.x = 0.0
    game.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low, game], 0.56)


if __name__ == "__main__":
    main()
