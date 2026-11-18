"""Builds the Pacific krill (creatures/krill) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/krill/tools/build_krill.py
    blender --background --python creatures/krill/tools/build_krill.py -- <preview folder>   # with pictures

Writes creatures/krill/models/krill.glb (the full model, for one seen close), krill_game.glb (the game model: few
triangles, spent where the eye looks: the outline, the big eyes, the basket), krill_lo.glb (far off, phones) and
krill_school.glb (a very light one whose look is in its vertex colours, for swarms of hundreds drawn by one
MultiMesh), and the editable creatures/krill/tools/krill.blend (all four; this folder has a .gdignore). The full,
the low and the school model come out as they did before the game model was added. The full, the game and the low
model are one still mesh with one surface each: the shader (krill.gdshader) draws every marking, beats its
swimmerets, pumps its feeding basket and curls its tail under (`curl`). It prints a WINDING line for each: the
check that nothing is inside out.

A Pacific krill (Euphausia pacifica), 0.03 m from the front of its eyes to the tip of its tail fan (a big one: a
game scales it up), built from the species (no picture was traced or copied):

- THE BODY: a slender carapace, a third of its length, with a short pointed rostrum between the eyes; an abdomen of
  six segments, the sixth the longest, curving a little down towards the tail; a narrow pointed telson between two
  pairs of paddles: the tail fan.
- TWO BIG BLACK EYES, round, on short stalks either side of the rostrum (krill's eyes are large for their size).
- The long ANTENNAE (a little shorter than the body), reaching forward and out and curving back; the ANTENNULES on
  their stalks, each with two short whips; the flat antennal scales.
- THE FEEDING BASKET: six pairs of thin legs under the carapace, held forward and down, each fringed along its
  inner side with a comb of feathery hairs (one flat fringe each): together a basket.
- FIVE PAIRS OF SWIMMERETS under the first five segments of the abdomen: fringed paddles that beat in a wave.

Everything here is in Godot space (metres, Y up, X to its left side, its head at -Z) until it is written out; the
origin is on its middle line half way along (0.015 m behind the front of its eyes).

What a point is, for the shader: see `Mesh` below. The parts: 0 the body, 1 a leg of the basket (`index` which,
0 the first; `root` where it joins the body; `a` 0 at its root to 1 at its tip), 2 a swimmeret (`index` 0 the
first to 4 the last; `root` where it hangs from; `a` 0 to 1), 3 an eye (`a` 0 its stalk, 1 the eye), 4 an antenna
(`index` 0 the long antenna, 1 an antennule; `root` its base; `a` 0 to 1 along it), 5 an antennal scale, 6 the tail
fan (`index` 0 the telson, 1 an inner paddle, 2 an outer one; `a` 0 to 1), 7 a fringe of hairs (on a basket leg or a
swimmeret: `index` and `root` those of its limb, UV.x 1 if it is a swimmeret's; `a` 0 to 1 along its limb).

The numbers marked "as the shader has it" are in krill.gdshader too: change one, change the other.
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

BODY, LEG, SWIM, EYE, ANTENNA, SCALE, FAN, FRINGE = range(8)
# As the shader has it: the box the joints' places are written in.
BOX = (Vector((-0.02, -0.01, -0.03)), Vector((0.02, 0.01, 0.03)))


def pick(low, full, lo, game):
    """The full model's number, the low one's or the game one's (`low` is False, True or "game")."""
    if low == "game":
        return game
    return lo if low else full


def to_b(p):
    """Godot's space (Y up, nose at -Z) to Blender's (Z up, nose at +Y)."""
    return Vector((p.x, -p.z, p.y))


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def bezier(points, t):
    points = [Vector(p) for p in points]
    while len(points) > 1:
        points = [points[i].lerp(points[i + 1], t) for i in range(len(points) - 1)]
    return points[0]


def through(points, t):
    """A smooth curve through `points` (Catmull-Rom), t 0 at the first to 1 at the last."""
    points = [Vector(p) for p in points]
    count = len(points) - 1
    f = min(max(t, 0.0), 1.0) * count
    i = min(int(f), count - 1)
    s = f - i
    p0 = points[max(i - 1, 0)]
    p1 = points[i]
    p2 = points[i + 1]
    p3 = points[min(i + 2, count)]
    return 0.5 * ((2 * p1) + (-p0 + p2) * s + (2 * p0 - 5 * p1 + 4 * p2 - p3) * s * s + (-p0 + 3 * p1 - 3 * p2 + p3) * s * s * s)


class Mesh:
    """The model as it is being made. What is written at each point, for the shader:
    UV2.y the part times 16 plus `index`; the colour's red, green and blue `root` (the joint the part turns
    about, as a place in BOX: 0 its least corner, 1 its greatest); the colour's alpha `a`; UV.x, UV.y and
    UV2.x `k` (three more numbers). (The glTF writer flips V: what is written is 1 - v, so that Godot reads v.)
    The school model writes only a colour at each point (`dab`)."""

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

    def dab(self, p, colour):
        self.verts.append(Vector(p))
        self.data.append(colour)
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
    """A skin through `rings` (closed loops of as many points each). A cap is None (left open), True (a
    fan to the loop's middle) or a place (a fan to that point)."""
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
    """A direction and two sideways axes at each point of a path, turning as little as they can."""
    count = len(path)
    tangents = [(path[min(i + 1, count - 1)] - path[max(i - 1, 0)]).normalized() for i in range(count)]
    if ref is None:
        ref = UP if abs(tangents[0].y) < 0.9 else Vector((1.0, 0.0, 0.0))
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


def tube(m, path, radii, sides, name, along=None, caps=(True, True), ref=None):
    """A round tube along `path`, `radii` at its points. With `along` (from, to), `a` runs from one to the
    other along its length."""
    path = [Vector(p) for p in path]
    lengths = [0.0]
    for i in range(1, len(path)):
        lengths.append(lengths[-1] + (path[i] - path[i - 1]).length)
    made = frames(path, ref)
    rings = []
    for (t, u, v), p, r in zip(made, path, radii):
        r = max(r, 1e-6) * FAT[0](sides)
        rings.append([p + (u * math.cos(TAU * s / sides) + v * math.sin(TAU * s / sides)) * r for s in range(sides)])

    def tags(p, ri, ci):
        if along is None:
            return None, None
        return None, along[0] + (along[1] - along[0]) * lengths[ri] / lengths[-1]

    loft(m, rings, name,
         cap0=(path[0] - made[0][0] * radii[0] * 0.5) if caps[0] else None,
         cap1=(path[-1] + made[-1][0] * radii[-1] * 0.5) if caps[1] else None, tags=tags)


def ball(m, centre, r, name, lat=8, lon=12):
    centre = Vector(centre)
    rings = []
    for i in range(1, lat):
        th = math.pi * i / lat
        rings.append([centre + Vector((r * math.sin(th) * math.cos(TAU * j / lon), r * math.sin(th) * math.sin(TAU * j / lon), -r * math.cos(th)))
                      for j in range(lon)])
    loft(m, rings, name, cap0=centre - Vector((0.0, 0.0, r)), cap1=centre + Vector((0.0, 0.0, r)), out=lambda middle: middle - centre)


def blade(m, name, point, facing, thick, nt, nu, tags=None):
    """A thin closed blade: `point(t, u)` a place in the model (t 0 at its root to 1 at its tip, u 0 at its
    leading edge to 1 at its trailing edge), `facing` the way one of its two skins faces. It is `thick` at
    its root, a foil across (nothing at either edge), thinning towards its tip. `tags(t, u)` gives (k, a)."""
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


# --- the body -------------------------------------------------------------------------------------

# Its outline along it: z, the middle line's height, half its depth above that, below it, half its width, how
# square its section is (2 an ellipse).
PROFILE = [
    (-0.0132, 0.00045, 0.00025, 0.00025, 0.00020, 2.0),
    (-0.0127, 0.00045, 0.00080, 0.00070, 0.00060, 2.0),
    (-0.0118, 0.00040, 0.00140, 0.00130, 0.00105, 2.1),
    (-0.0100, 0.00030, 0.00195, 0.00180, 0.00140, 2.2),
    (-0.0075, 0.00020, 0.00215, 0.00200, 0.00155, 2.2),
    (-0.0048, 0.00010, 0.00205, 0.00185, 0.00145, 2.3),
    (-0.0020, 0.00000, 0.00180, 0.00160, 0.00125, 2.4),
    (0.0010, -0.00010, 0.00155, 0.00140, 0.00108, 2.4),
    (0.0040, -0.00030, 0.00128, 0.00118, 0.00090, 2.3),
    (0.0068, -0.00055, 0.00098, 0.00090, 0.00068, 2.2),
    (0.0088, -0.00070, 0.00068, 0.00062, 0.00048, 2.1),
    (0.0098, -0.00078, 0.00035, 0.00035, 0.00028, 2.0),
]
BODY_FROM, BODY_TO = PROFILE[0][0], PROFILE[-1][0]
# As the shader has it: where the carapace ends and each segment of the abdomen begins (z).
SEGMENTS = (-0.0048, -0.0025, -0.0003, 0.0018, 0.0038, 0.0058)


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


_XS = [p[0] for p in PROFILE]
_CURVES = []
for _column in range(1, 6):
    _ys = [p[_column] for p in PROFILE]
    _CURVES.append((_ys, _slopes(_XS, _ys)))


def profile(z):
    z = max(_XS[0], min(_XS[-1], z))
    i = 0
    while i < len(_XS) - 2 and z > _XS[i + 1]:
        i += 1
    h = _XS[i + 1] - _XS[i]
    t = (z - _XS[i]) / h
    out = []
    for ys, m in _CURVES:
        a = (2 * t ** 3 - 3 * t ** 2 + 1) * ys[i] + (t ** 3 - 2 * t ** 2 + t) * h * m[i]
        b = (-2 * t ** 3 + 3 * t ** 2) * ys[i + 1] + (t ** 3 - t ** 2) * h * m[i + 1]
        out.append(a + b)
    return out


def section(z):
    cy, up, down, wide, power = profile(z)
    squeeze = 1.0
    for b in SEGMENTS:
        squeeze -= 0.08 * math.exp(-((z - b) / 0.00022) ** 2)
    return cy, max(up * squeeze, 0.00008), max(down * squeeze, 0.00008), max(wide * squeeze, 0.00008), power


def body(m, low):
    around = pick(low, 12, 6, 8)
    zs = []
    z = BODY_FROM
    step = 0.0022 if low else 0.0007
    while z < BODY_TO - 1e-9:
        zs.append(z)
        z += step
    zs.append(BODY_TO)
    if low == "game":
        # (few rings, evenly along the abdomen so that it curls smoothly, the grooves drawn by the shader;
        # the head's taper hidden behind the eyes)
        zs = [-0.0132, -0.0118, -0.0100, -0.0075, -0.0045, -0.0015, 0.0015, 0.0042, 0.0068, 0.0088, 0.0098]
    m.part, m.index, m.root, m.a = BODY, 0, None, 0.0
    rings = []
    for z in zs:
        cy, up, down, wide, power = section(z)
        ring = []
        for c in range(around):
            angle = c / around * TAU
            co, s = math.cos(angle), math.sin(angle)
            e = 2.0 / power
            ring.append(Vector((math.copysign(abs(s) ** e, s) * wide, cy + math.copysign(abs(co) ** e, co) * (up if co >= 0.0 else down), z)))
        rings.append(ring)

    def facing(middle):
        if middle.z <= zs[0] + 1e-9:
            return Vector((0.0, 0.0, -1.0))
        if middle.z >= zs[-1] - 1e-9:
            return Vector((0.0, 0.0, 1.0))
        cy = section(middle.z)[0]
        return Vector((middle.x, middle.y - cy, 0.0))

    loft(m, rings, "body", cap0=Vector((0.0, PROFILE[0][1], BODY_FROM - 0.0001)), cap1=Vector((0.0, PROFILE[-1][1], BODY_TO + 0.0001)), out=facing)
    # the rostrum: a short point forward between the eyes, from the top of the carapace's front
    if low == "game":
        # (the game model: a straight point)
        tube(m, [Vector((0.0, 0.0011, -0.0118)), Vector((0.0, 0.0009, -0.0140))], [0.00030, 0.00004], 3, "body", caps=(False, False))
    elif not low:
        tube(m, [Vector((0.0, 0.0011, -0.0118)), Vector((0.0, 0.0010, -0.0130)), Vector((0.0, 0.0009, -0.0140))],
             [0.00030, 0.00018, 0.00004], 4, "body", caps=(False, True))


def eyes(m, low):
    for sx in (1.0, -1.0):
        foot = Vector((sx * 0.0004, 0.0006, -0.0118))
        head = Vector((sx * 0.0011, 0.0008, -0.0128))
        m.part, m.index, m.root, m.a = EYE, 0, None, 0.0
        if low is not True:
            tube(m, [foot, head], [0.00055, 0.0006], pick(low, 7, 0, 3), "eyes", caps=(False, False))
        m.a = 1.0
        ball(m, head + Vector((sx * 0.0004, 0.0001, -0.0003)), 0.0011, "eyes", lat=pick(low, 6, 3, 5), lon=pick(low, 9, 5, 10))
    m.a = 0.0


def feelers(m, low):
    """The long antennae, the antennules and the antennal scales."""
    for sx in (1.0, -1.0):
        def v(x, y, z):
            return Vector((sx * x, y, z))
        # the long antenna: forward and out, then curving back and out
        base = v(0.0006, -0.0002, -0.0124)
        guide = [base, v(0.0016, 0.0002, -0.0170), v(0.0045, 0.0008, -0.0205), v(0.0085, 0.0008, -0.0215), v(0.0130, 0.0002, -0.0190), v(0.0165, -0.0006, -0.0135)]
        steps = pick(low, 16, 4, 6)
        path = [through(guide, i / steps) for i in range(steps + 1)]
        m.part, m.index, m.root = ANTENNA, 0, base
        tube(m, path, [0.00016 * (1.0 - 0.7 * i / steps) for i in range(steps + 1)], 3, "antennae", along=(0.0, 1.0), caps=(False, low != "game"))
        # the antennule: a stalk forward and up, then two short whips
        base = v(0.0003, 0.0004, -0.0128)
        if low is True:
            continue
        m.index, m.root = 1, base
        stalk = [base, v(0.0006, 0.0008, -0.0142), v(0.0008, 0.0011, -0.0152)]
        if low == "game":
            # (the game model: the stalk straight, open where the whips go on)
            tube(m, [stalk[0], stalk[2]], [0.00025, 0.00016], 3, "antennae", along=(0.0, 0.3), caps=(False, False))
        else:
            tube(m, stalk, [0.00025, 0.0002, 0.00016], pick(low, 4, 3, 3), "antennae", along=(0.0, 0.3))
        if low is not True:
            n = pick(low, 4, 0, 1)
            for lean, rise in ((1.0, 0.0012), (0.3, -0.0002)):
                whip = [bezier([stalk[-1], v(0.0010 + 0.0010 * lean, 0.0013 + rise * 0.5, -0.0175), v(0.0016 + 0.0028 * lean, 0.0016 + rise, -0.0205)], i / n) for i in range(n + 1)]
                tube(m, whip, [0.00011 * (1.0 - 0.6 * i / n) for i in range(n + 1)], 3, "antennae", along=(0.3, 0.7), caps=(low != "game", low != "game"))
        # the antennal scale: a small flat blade lying forward over the antenna's base
        m.part, m.index, m.root = SCALE, 0, None
        scale_root = v(0.0009, 0.0000, -0.0122)

        def scale_point(t, u, scale_root=scale_root, sx=sx):
            wide = 0.0007 * math.sin(math.pi * min(1.0, 0.2 + 0.8 * t)) ** 0.6 + 0.00008
            return scale_root + Vector((sx * (0.0006 * t + wide * (u - 0.3)), 0.0002 * t, -0.0038 * t))

        blade(m, "scales", scale_point, Vector((0.0, 1.0, 0.0)), 0.00012, pick(low, 4, 2, 1), pick(low, 3, 1, 1), tags=lambda t, u: (None, t))
    m.a = 0.0
    m.root = None


# The legs of the basket, first to last: where each joins the underside of the carapace (z), and how long it is.
BASKET = [(-0.0112, 0.0042), (-0.0102, 0.0050), (-0.0091, 0.0056), (-0.0080, 0.0058), (-0.0069, 0.0056), (-0.0058, 0.0050)]
# As the shader has it: where each pair of swimmerets hangs (z).
SWIMMERETS = (-0.0036, -0.0014, 0.0008, 0.0028, 0.0048)


def fringe(m, path, inward, long, nt, name):
    """A comb of feathery hairs along a limb, as one flat fringe: from `path` (the limb's line) out towards
    `inward`, `long` at its widest."""
    lengths = [0.0]
    for i in range(1, len(path)):
        lengths.append(lengths[-1] + (path[i] - path[i - 1]).length)
    total = lengths[-1]
    made = frames(path)

    def point(t, u):
        f = t * (len(path) - 1)
        i = min(int(f), len(path) - 2)
        p = path[i].lerp(path[i + 1], f - i)
        tangent = made[i][0]
        out = (inward - tangent * inward.dot(tangent)).normalized()
        wide = long * math.sin(math.pi * min(1.0, 0.08 + 0.92 * t)) ** 0.7
        # (the hairs lean towards the limb's tip)
        return p + out * (wide * u) + tangent * (0.3 * wide * u)

    facing = made[0][0].cross(inward).normalized()
    blade(m, name, point, facing, long * 0.06, nt, 1, tags=lambda t, u: (None, t))


def basket(m, low):
    for i, (z, long) in enumerate(BASKET):
        if low is True and i % 2 == 1:
            continue
        for sx in (1.0, -1.0):
            cy, up, down, wide, power = profile(z)
            root = Vector((sx * 0.0005, cy - down + 0.0003, z))
            # down and forward, bowing out, its end turned in: one side of the basket
            spread = 0.0007 + 0.00025 * i
            n = pick(low, 5, 2, 2)
            path = [bezier([root, root + Vector((sx * spread * 1.5, -long * 0.5, -long * 0.25)), root + Vector((sx * spread * 0.6, -long * 0.85, -long * 0.55))], s / n)
                    for s in range(n + 1)]
            m.part, m.index, m.root, m.k = LEG, i, root, Vector((0.0, 0.0, 0.0))
            tube(m, path, [0.00013 * (1.0 - 0.5 * s / (len(path) - 1)) for s in range(len(path))], pick(low, 4, 3, 3), "basket", along=(0.0, 1.0), caps=(False, low != "game"))
            if low is not True:
                m.part = FRINGE
                fringe(m, path, Vector((-sx, 0.15, -0.35)), 0.0009, pick(low, 4, 0, 2), "fringes")
    m.part, m.index, m.root = BODY, 0, None


def swimmerets(m, low):
    for i, z in enumerate(SWIMMERETS):
        cy, up, down, wide, power = profile(z)
        for sx in (1.0, -1.0):
            root = Vector((sx * 0.0004, cy - down + 0.00025, z))
            long = 0.0034 - 0.00012 * i
            path = [root + Vector((sx * 0.0002 * s / 4, -long * s / 4, 0.0007 * (s / 4) ** 2)) for s in range(5)]
            m.part, m.index, m.root = SWIM, i, root
            m.k = Vector((0.0, 0.0, 0.0))
            tube(m, path if not low else [path[0], path[4]], [0.00016, 0.00015, 0.00012, 0.0001, 0.00006] if not low else [0.00016, 0.00006], 3, "swimmerets", along=(0.0, 1.0), caps=(False, low != "game"))
            if low is not True:
                m.part = FRINGE
                m.k = Vector((1.0, 0.0, 0.0))
                fringe(m, path, Vector((0.0, 0.0, 1.0)), 0.0010, pick(low, 4, 0, 2), "fringes")
            m.k = Vector((0.0, 0.0, 0.0))
    m.part, m.index, m.root = BODY, 0, None


def tail_fan(m, low):
    """The telson (narrow, pointed) and two pairs of paddles either side of it."""
    nt = pick(low, 4, 2, 2)
    nu = pick(low, 2, 1, 1)
    up = Vector((0.0, 1.0, 0.0))
    m.part, m.root = FAN, None
    m.index = 0
    y0 = PROFILE[-1][1]

    def telson(t, u):
        wide = 0.00045 * (1.0 - t) ** 0.9 + 0.00004
        return Vector((wide * (2.0 * u - 1.0), y0 - 0.0006 * t, 0.0090 + 0.0058 * t))

    # (the game model: the telson keeps its thickness, seen edge on from the side)
    blade(m, "tail fan", telson, up, 0.0003, nt, pick(low, nu, nu, 2), tags=lambda t, u: (None, t))
    for sx in (1.0, -1.0):
        for k, (spread, long, wide) in enumerate(((0.14, 0.0050, 0.0011), (0.32, 0.0046, 0.0013))):
            m.index = 1 + k
            root = Vector((sx * 0.0003, y0 - 0.00005, 0.0092))
            way = Vector((sx * math.sin(spread), -0.1, math.cos(spread))).normalized()
            across = Vector((sx * math.cos(spread), 0.0, -math.sin(spread)))

            def point(t, u, root=root, way=way, across=across, long=long, wide=wide):
                w = wide * math.sin(math.pi * min(1.0, 0.18 + 0.82 * t)) ** 0.5 * (1.0 - 0.2 * t) + 0.00005
                return root + way * (long * t) + across * (w * (u - 0.35))

            blade(m, "tail fan", point, up, 0.0002, nt, nu, tags=lambda t, u: (None, t))
    m.index = 0


def make(low):
    FAT[0] = game_fat if low == "game" else (lambda sides: 1.0)
    m = Mesh()
    body(m, low)
    eyes(m, low)
    feelers(m, low)
    basket(m, low)
    swimmerets(m, low)
    tail_fan(m, low)
    return m


# --- the school model -------------------------------------------------------------------------------

C_BACK = (0.78, 0.36, 0.34)
C_SIDE = (0.92, 0.66, 0.62)
C_BELLY = (0.95, 0.80, 0.74)
C_EYE = (0.01, 0.01, 0.012)
C_LIMB = (0.88, 0.58, 0.52)
SCHOOL_RINGS = (-0.0128, -0.0105, -0.005, 0.002, 0.0098)


def make_school():
    m = Mesh()
    # the body: four points round (the back, the left side, the belly, the right side) at five places along it
    grid = []
    for z in SCHOOL_RINGS:
        cy, up, down, wide, power = section(z)
        grid.append([m.dab(Vector((0.0, cy + up, z)), C_BACK), m.dab(Vector((wide, cy, z)), C_SIDE),
                     m.dab(Vector((0.0, cy - down, z)), C_BELLY), m.dab(Vector((-wide, cy, z)), C_SIDE)])
    for r in range(len(grid) - 1):
        for c in range(4):
            n = (c + 1) % 4
            quad = (grid[r][c], grid[r][n], grid[r + 1][n], grid[r + 1][c])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            cy = section(middle.z)[0]
            m.face(quad, Vector((middle.x, middle.y - cy, 0.0)), "body")
    for row, z, way, colour in ((grid[0], BODY_FROM, -1.0, C_SIDE), (grid[-1], 0.0148, 1.0, C_LIMB)):
        tip = m.dab(Vector((0.0, section(z)[0], z)), colour)
        for c in range(4):
            m.face((tip, row[c], row[(c + 1) % 4]), Vector((0.0, 0.0, way)), "body")
    # the eyes: a black diamond standing out on each side of the head
    for sx in (1.0, -1.0):
        c = Vector((sx * 0.0016, 0.0008, -0.0124))
        ring = [m.dab(c + Vector((0.0, 0.0011, 0.0)), C_EYE), m.dab(c + Vector((sx * 0.0003, 0.0, -0.0011)), C_EYE),
                m.dab(c + Vector((0.0, -0.0011, 0.0)), C_EYE), m.dab(c + Vector((-sx * 0.0004, 0.0, 0.0011)), C_EYE)]
        m.face((ring[0], ring[1], ring[2]), Vector((sx, 0.0, 0.0)), "eyes")
        m.face((ring[0], ring[2], ring[3]), Vector((sx, 0.0, 0.0)), "eyes")

    # single sheets (drawn from both sides): the antennae, the basket, the swimmerets, the tail fan
    def sheet(points, colour, out):
        m.face(tuple(m.dab(p, colour) for p in points), out, "sheets (two-sided)")

    for sx in (1.0, -1.0):
        sheet((Vector((sx * 0.0005, 0.0, -0.0122)), Vector((sx * 0.0005, 0.0004, -0.0122)), Vector((sx * 0.0075, 0.0006, -0.0215))), C_LIMB, Vector((sx, 0.0, 0.0)))
    sheet((Vector((0.0, -0.0014, -0.0112)), Vector((0.0, -0.0052, -0.0135)), Vector((0.0, -0.0044, -0.0082)), Vector((0.0, -0.0014, -0.0058))), C_LIMB, Vector((1.0, 0.0, 0.0)))
    sheet((Vector((0.0, -0.0012, -0.0040)), Vector((0.0, -0.0042, -0.0030)), Vector((0.0, -0.0034, 0.0050)), Vector((0.0, -0.0008, 0.0050))), C_LIMB, Vector((1.0, 0.0, 0.0)))
    y0 = PROFILE[-1][1]
    sheet((Vector((-0.0002, y0, 0.0090)), Vector((0.0024, y0 - 0.0004, 0.0145)), Vector((-0.0024, y0 - 0.0004, 0.0145))), C_LIMB, Vector((0.0, 1.0, 0.0)))
    return m


def material_of(name, colour):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = colour
    material.diffuse_color = colour
    return material


def finish(name, m, colour, school=False):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) for p in m.verts], [], m.faces)
    # (every layer made first, then each looked up by name: making one moves the others)
    if not school:
        mesh.uv_layers.new(name="UVMap")
        mesh.uv_layers.new(name="UV2")
    mesh.color_attributes.new(name="Col", type="FLOAT_COLOR", domain="POINT")
    colours = mesh.color_attributes["Col"]
    if school:
        for i, d in enumerate(m.data):
            colours.data[i].color = (d[0], d[1], d[2], 1.0)
    else:
        uv = mesh.uv_layers["UVMap"].data
        uv2 = mesh.uv_layers["UV2"].data
        for poly in mesh.polygons:
            for corner, vi in enumerate(poly.vertices):
                d = m.data[vi]
                uv[poly.loop_start + corner].uv = d[0]
                uv2[poly.loop_start + corner].uv = d[1]
        for i, d in enumerate(m.data):
            colours.data[i].color = d[2]
    # (the glTF writer only writes the colour that is marked for rendering)
    mesh.color_attributes.active_color = colours
    mesh.color_attributes.render_color_index = 0
    mesh.materials.append(material_of(name, colour))
    for poly in mesh.polygons:
        poly.use_smooth = not school
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    lo = [min(p[i] for p in m.verts) for i in range(3)]
    hi = [max(p[i] for p in m.verts) for i in range(3)]
    print("BUILT %s verts=%d tris=%d from (%.4f, %.4f, %.4f) to (%.4f, %.4f, %.4f)" % ((name, len(mesh.vertices), tris) + tuple(lo) + tuple(hi)))
    # Nothing inside out: every face looks the way it was made to (Blender's front is the side a face's
    # normal is on).
    bad = {}
    for poly in mesh.polygons:
        out, group = m.out[poly.index]
        if poly.normal.dot(to_b(out)) <= 0.0:
            bad[group] = bad.get(group, 0) + 1
    told = ["%s %d/%d wrong" % (group, bad.get(group, 0), count) for group, count in m.count.items()]
    print("WINDING %s: %s: %s" % (name, "ok" if not bad else "INSIDE OUT", ", ".join(told)))
    return obj


def export_one(obj, path, school=False):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", export_yup=True, use_selection=True,
        export_animations=False, export_texcoords=not school,
        export_vertex_color="ACTIVE", export_all_vertex_colors=False,
    )


def render(folder, made, size):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.show_cavity = True
    scene.render.resolution_x, scene.render.resolution_y = 1200, 800
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 100.0
    camera.data.clip_start = 0.001
    scene.collection.objects.link(camera)
    scene.camera = camera
    views = [("left", (1, 0, 0), size), ("right", (-1, 0, 0), size), ("front", (0, 1, 0), size * 0.8), ("back", (0, -1, 0), size * 0.8),
             ("top", (0.001, 0, 1), size), ("under", (0.001, 0, -1), size), ("quarter", (0.7, 0.6, 0.45), size), ("head", (0.6, 0.6, 0.2), size * 0.45)]
    for obj in made:
        school = obj.name.endswith("_school")
        scene.display.shading.color_type = "VERTEX" if school else "MATERIAL"
        scene.display.shading.show_backface_culling = not school
        for other in made:
            other.hide_render = other is not obj
        for view, direction, wide in views:
            offset = Vector(direction).normalized() * 1.0
            camera.data.ortho_scale = wide
            target = Vector((0.0, 0.009, 0.0)) if view == "head" else Vector((0.0, 0.0, 0.0))
            camera.location = target + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s_%s.png" % (obj.name, view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    full = finish("krill", make(False), (0.9, 0.6, 0.55, 1.0))
    low = finish("krill_lo", make(True), (0.9, 0.6, 0.55, 1.0))
    school = finish("krill_school", make_school(), (1.0, 1.0, 1.0, 1.0), True)
    game = finish("krill_game", make("game"), (0.9, 0.6, 0.55, 1.0))
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, "krill.glb"))
    export_one(low, os.path.join(OUT, "krill_lo.glb"))
    export_one(school, os.path.join(OUT, "krill_school.glb"), True)
    export_one(game, os.path.join(OUT, "krill_game.glb"))
    # (in the .blend: the full model in the middle, the low one and the school one to its left, the game one to its right)
    low.location.x = 0.04
    school.location.x = 0.08
    game.location.x = -0.04
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "krill.blend"))
    low.location.x = 0.0
    school.location.x = 0.0
    game.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low, school, game], 0.05)


if __name__ == "__main__":
    main()
