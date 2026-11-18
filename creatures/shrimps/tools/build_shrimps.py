"""Builds the shrimps (creatures/shrimps, Shrimp) and exports them for Godot.

Run from the game's root (or anywhere: paths are from this file):
    blender --background --factory-startup --python creatures/shrimps/tools/build_shrimps.py
    blender --background --factory-startup --python creatures/shrimps/tools/build_shrimps.py -- <preview folder>

Three kinds, each three models (the full one, the game one and the low one), all built from the same lines here, on
the spot prawn's way (GameCommon's spot-prawn: its helpers are copied here, not shared):

- CLEANER: a scarlet cleaner shrimp (Lysmata amboinensis), 0.058 m from its rostrum's tip to its tail's: a smooth
  prawn-like body, a short rostrum, ten long thin legs, five pairs of swimmerets, a tail fan, and very long white
  antennae (more than twice its length) and white antennules, which it waves. Red down each side of its back with a
  white stripe down the middle, yellow-orange lower down (the shader's).
- MANTIS: a peacock mantis shrimp (Odontodactylus scyllarus), 0.15 m from the front of its head to its tail's tip:
  flattened and long, a small carapace, three bare thoracic segments, a broad abdomen of six segments, a broad
  telson and two pairs of paddle-shaped uropods; big eyes on stalks that swivel one by one; antennules of three
  whips each; broad antennal scales; two raptorial arms folded under its head, each ending in a club, that punch
  out (`strike`); three pairs of thin walking legs; five pairs of broad paddle swimmerets. Green, its arms red with
  spots, its scales and tail orange and blue (the shader's).
- PISTOL: a pistol (snapping) shrimp (Alpheus), 0.045 m from its rostrum's tip to its tail's: small and drab, a
  smooth carapace hooded over its eyes (which peep out under the hood on short stalks), one huge snapping claw on
  its right and a small one on its left, eight walking legs, swimmerets and a tail fan. The big claw's finger cocks
  open and snaps shut (`snap`).

It writes creatures/shrimps/models/shrimp_<kind>.glb, shrimp_<kind>_game.glb and shrimp_<kind>_lo.glb, and the
editable creatures/shrimps/tools/shrimp_<kind>.blend (all three models of that kind; this folder has a .gdignore).
Each is one still mesh with one surface: the shader (shrimp.gdshader) draws every marking, walks its legs, beats its
swimmerets, curls its tail under (`flick`), punches, snaps, swivels its eyes and waves its antennae. It prints a
WINDING line for each: the check that nothing is inside out.

Everything here is in Godot space (metres, Y up, X to its left side, its head at -Z) until it is written out.
THE ORIGIN IS ON THE GROUND under the middle of the body (half way along LENGTH): its feet stand at y 0.

What a point is, for the shader: UV2.y the part times 16 plus `index`; the colour's red, green and blue `root` (the
joint the part turns about, as a place in the kind's BOX: 0 its least corner, 1 its greatest); the colour's alpha
`a`; UV.x, UV.y and UV2.x `k` (three numbers, metres). The parts: 0 the body, 1 a walking leg (`root` its joint,
`k` its knee, `a` 0 above the knee and 1 below it), 2 a swimmeret (`root` where it hangs from; `a` 0 its root to 1 its
end), 3 an eye (`root` its stalk's foot; `a` 0 the stalk, 1 the eye), 4 an antenna (`index` 0 the long antenna, 1 an
antennule's stalk and whips; `root` its base; `a` 0 at its base to 1 at its tip), 5 an antennal scale, 6 the tail
fan (`index` 0 the telson, 1 an inner paddle, 2 an outer one; `a` 0 its root to 1 its tip), 7 the rostrum (the mantis
shrimp's rostral plate), 8 a mouthpart, 9 a claw's arm (the mantis shrimp's merus: `root` its shoulder, `k` its
elbow; the pistol shrimp's arms and palms, still: `index` 0 the big claw, 1 the small one), 10 a claw's moving part
(the mantis shrimp's forearm, club and hook: `root` its shoulder, `k` its elbow; the pistol shrimp's big finger:
`root` its hinge).

The numbers marked "as the shader has it" are set by shrimp.gd per kind (KINDS there): change one, change the other.
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
BODY, LEG, SWIM, EYE, ANTENNA, SCALE, FAN, ROSTRUM, MOUTH, ARM, HAND = range(11)
# As the shader has it: how far out along a leg (from its joint to its tip, seen from above) its knee is.
KNEE_AT = 0.45


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
    """The model as it is being made (see the top of this file for what each point carries).
    (The glTF writer flips V: what is written is 1 - v, so that Godot reads v.)"""

    def __init__(self, box):
        self.box = box
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
            colour = tuple((self.root[i] - self.box[0][i]) / (self.box[1][i] - self.box[0][i]) for i in range(3))
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
        if cap is not True and (at - centre).length > 1e-9:
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


# The game model's tubes have few sides: each is made a little fatter, so that it looks as wide as the round one it
# stands for, seen from any side.
FAT = [lambda sides: 1.0]


def game_fat(sides):
    return math.pi / (sides * math.sin(math.pi / sides))


def tube(m, path, radii, sides, name, flat=1.0, along=None, caps=(True, True), ref=None):
    """A round (or, with `flat`, flattened) tube along `path`, `radii` at its points. With `along` (from, to), `a`
    runs from one to the other along its length."""
    path = [Vector(p) for p in path]
    lengths = [0.0]
    for i in range(1, len(path)):
        lengths.append(lengths[-1] + (path[i] - path[i - 1]).length)
    made = frames(path, ref)
    rings = []
    for (t, u, v), p, r in zip(made, path, radii):
        r = max(r, 1e-5) * FAT[0](sides)
        rings.append([p + (u * math.cos(TAU * s / sides) + v * (flat * math.sin(TAU * s / sides))) * r for s in range(sides)])

    def tags(p, ri, ci):
        if along is None:
            return None, None
        return None, along[0] + (along[1] - along[0]) * lengths[ri] / lengths[-1]

    loft(m, rings, name,
         cap0=(path[0] - made[0][0] * radii[0] * 0.5) if caps[0] else None,
         cap1=(path[-1] + made[-1][0] * radii[-1] * 0.5) if caps[1] else None, tags=tags)


def ball(m, centre, rx, ry, rz, name, lat=8, lon=12, basis=None, tags=None):
    """An ellipsoid: `basis` its three axes (its poles on the third)."""
    centre = Vector(centre)
    ex, ey, ez = basis or (Vector((1.0, 0.0, 0.0)), Vector((0.0, 1.0, 0.0)), Vector((0.0, 0.0, 1.0)))
    rings = []
    for i in range(1, lat):
        th = math.pi * i / lat
        rings.append([centre + ex * (rx * math.sin(th) * math.cos(TAU * j / lon)) + ey * (ry * math.sin(th) * math.sin(TAU * j / lon))
                      - ez * (rz * math.cos(th)) for j in range(lon)])
    loft(m, rings, name, cap0=centre - ez * rz, cap1=centre + ez * rz, tags=tags, out=lambda middle: middle - centre)


def basis_of(forward, up=UP):
    """Three axes for a `ball`: its poles along `forward`, its second axis as near `up` as it can be."""
    ez = Vector(forward).normalized()
    ex = Vector(up).cross(ez).normalized()
    return ex, ez.cross(ex), ez


def blade(m, name, point, facing, thick, nt, nu, tags=None, ts=None):
    """A thin closed blade (a tail fan's paddle, a swimmeret, a scale): `point(t, u)` is a place in the model (t 0 at
    its root to 1 at its tip, u 0 at its leading edge to 1 at its trailing edge), `facing` the way one of its two skins
    faces. It is `thick` at its root, a foil across, thinning towards its tip."""
    facing = Vector(facing).normalized()
    if ts:
        nt = len(ts) - 1
    for side in (1.0, -1.0):
        grid = []
        for ti in range(nt + 1):
            t = ts[ti] if ts else ti / nt
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


def section_loft(m, zs, section, around, name, caps=(True, True)):
    """A body along Z: `section(z)` gives (middle height, half depth above, half depth below, half width, squareness)
    at `z`; its rings are at `zs`. A point is `angle` round from the ridge of the back (0) by its left side (a quarter
    turn) to the keel (half a turn)."""
    rings = []
    for z in zs:
        cy, up, down, wide, power = section(z)
        ring = []
        for c in range(around):
            angle = c / around * TAU
            co = math.cos(angle)
            s = math.sin(angle)
            e = 2.0 / power
            y = math.copysign(abs(co) ** e, co) * (up if co >= 0.0 else down)
            x = math.copysign(abs(s) ** e, s) * wide
            ring.append(Vector((x, cy + y, z)))
        rings.append(ring)
    centres = [Vector((0.0, section(z)[0], z)) for z in zs]

    def facing(middle):
        if middle.z <= zs[0] + 1e-9:
            return Vector((0.0, 0.0, -1.0))
        if middle.z >= zs[-1] - 1e-9:
            return Vector((0.0, 0.0, 1.0))
        cy = section(min(max(middle.z, zs[0]), zs[-1]))[0]
        return Vector((middle.x, middle.y - cy, 0.0))

    loft(m, rings, name,
         cap0=centres[0] + Vector((0.0, 0.0, -0.0002)) if caps[0] else None,
         cap1=centres[-1] + Vector((0.0, 0.0, 0.0002)) if caps[1] else None, out=facing)


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


class Profile:
    """A body's outline along it: rows of (z, the middle line's height, half its depth above, below, half its width,
    how square its section is), and the grooves between its segments."""

    def __init__(self, rows, grooves, groove_depth=0.07):
        self.rows = rows
        self.xs = [r[0] for r in rows]
        self.curves = []
        for column in range(1, 6):
            ys = [r[column] for r in rows]
            self.curves.append((ys, _slopes(self.xs, ys)))
        self.grooves = grooves
        self.groove_depth = groove_depth
        self.groove_width = (self.xs[-1] - self.xs[0]) * 0.008

    def at(self, z):
        xs = self.xs
        z = max(xs[0], min(xs[-1], z))
        i = 0
        while i < len(xs) - 2 and z > xs[i + 1]:
            i += 1
        h = xs[i + 1] - xs[i]
        t = (z - xs[i]) / h
        out = []
        for ys, m in self.curves:
            a = (2 * t ** 3 - 3 * t ** 2 + 1) * ys[i] + (t ** 3 - 2 * t ** 2 + t) * h * m[i]
            b = (-2 * t ** 3 + 3 * t ** 2) * ys[i + 1] + (t ** 3 - t ** 2) * h * m[i + 1]
            out.append(a + b)
        return out

    def section(self, z):
        cy, up, down, wide, power = self.at(z)
        squeeze = 1.0
        w = self.groove_width
        for b in self.grooves:
            squeeze -= self.groove_depth * math.exp(-((z - b) / w) ** 2)
        return cy, max(up * squeeze, 0.0002), max(down * squeeze, 0.0002), max(wide * squeeze, 0.0002), power


def game_rings(knots, grooves, gap, fine=0.0):
    """Where the game model's rings go along the body: at every knot of its outline, at each groove (and `fine` either
    side of it), and nowhere further apart than `gap`; two closer than a tenth of `gap` are one."""
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


def body(m, low, prof, step_full, step_lo, game_gap, around):
    m.part, m.index, m.root, m.a = BODY, 0, None, 0.0
    xs = prof.xs
    if low == "game":
        zs = game_rings(xs, prof.grooves, game_gap)
    else:
        step = step_lo if low else step_full
        zs = []
        z = xs[0]
        while z < xs[-1] - 1e-9:
            zs.append(z)
            near = min(abs(z - b) for b in prof.grooves) if prof.grooves else 1.0
            z += step * (0.6 if near < step * 2 and not low else 1.0)
        zs.append(xs[-1])
    section_loft(m, zs, prof.section, pick(low, around[0], around[1], around[2]), "body")


def leg(m, part, index, root, heading, reach, knee_high, radius, sides, name, low=False):
    """A walking leg, in the upright plane through `root` that looks along `heading` (degrees from straight out to its
    side, towards its tail): up and out to its knee, KNEE_AT of the way out, then down to its tip on the ground."""
    root = Vector(root)
    side = 1.0 if root.x >= 0.0 else -1.0
    angle = math.radians(heading)
    d = Vector((side * math.cos(angle), 0.0, math.sin(angle)))
    knee = root + d * (KNEE_AT * reach)
    knee.y = knee_high
    tip = root + d * reach
    tip.y = 0.0
    bend = knee.lerp(tip, 0.5) + d * (0.07 * reach) + UP * (0.03 * reach)
    m.part, m.index, m.root, m.k = part, index, root, knee
    m.a = 0.0
    if low:
        tube(m, [root, knee], [radius, radius * 0.95], sides, name, caps=(False, low != "game"))
    else:
        tube(m, [root, root.lerp(knee, 0.5), knee], [radius * 0.95, radius * 1.12, radius * 0.95], sides, name)
    m.a = 1.0
    if low:
        # (the game and low models: the lower length one straight piece, bent at the knee only)
        tube(m, [knee, tip], [radius * 0.9, radius * 0.25], sides, name, caps=(True, False))
    else:
        tube(m, [knee, knee.lerp(bend, 0.5), bend, bend.lerp(tip, 0.5), tip],
             [radius * 0.9, radius * 0.95, radius * 0.72, radius * 0.55, radius * 0.2], sides, name)
    m.root = None
    m.a = 0.0
    m.index = 0
    m.k = Vector((0.0, 0.0, 0.0))


def eyes(m, low, foot, head, radius, stalk, shape=(1.0, 1.0, 1.0), gaze=None, game_ball=(5, 9)):
    """Two eyes on stalks: the stalk from `foot` to `head` (the left side's; the right mirrored), the eye a ball of
    `radius` (times `shape` across, up and along its gaze) whose pole looks along `gaze`, so that its rings go round
    its middle and the cartoon eye drawn on it stays round."""
    for sx in (1.0, -1.0):
        f = Vector((sx * foot[0], foot[1], foot[2]))
        h = Vector((sx * head[0], head[1], head[2]))
        g = Vector((sx * gaze[0], gaze[1], gaze[2])) if gaze else (h - f)
        m.part, m.index, m.root, m.a = EYE, 0, f, 0.0
        if low:
            tube(m, [f, h], [stalk, stalk * 0.9], pick(low, 10, 3, 4), "eyes", caps=(False, False))
        else:
            tube(m, [f, f.lerp(h, 0.5), h], [stalk, stalk * 0.95, stalk * 0.9], 10, "eyes", caps=(False, False))
        m.a = 1.0
        ex, ey, ez = basis_of(g)
        middle = h + (h - f).normalized() * radius * 0.4
        if sx > 0.0 and not low:
            # (as the shader has it: EYES in shrimp.gd)
            print("EYE middle (%.5f, %.5f, %.5f) gaze (%.4f, %.4f, %.4f) foot (%.5f, %.5f, %.5f)" % (tuple(middle) + tuple(g.normalized()) + tuple(f)))
        ball(m, middle, radius * shape[0], radius * shape[1], radius * shape[2], "eyes",
             lat=pick(low, 10, 3, game_ball[0]), lon=pick(low, 16, 6, game_ball[1]), basis=(ex, ey, -ez))
    m.a = 0.0
    m.root = None


def whip(m, index, base, guide, steps, radius, sides, along=(0.0, 1.0), ts=None, taper=0.75, caps=(False, True)):
    """A feeler along a smooth curve through `guide` (its first point its base)."""
    ts = ts or [i / steps for i in range(steps + 1)]
    path = [through(guide, t) for t in ts]
    m.part, m.index, m.root = ANTENNA, index, Vector(base)
    tube(m, path, [radius * (1.0 - taper * t) for t in ts], sides, "antennae", along=along, caps=caps)
    m.root = None


def swimmerets(m, low, zs, prof, long, wide, xoff, nt, nu, facing_k=0.15):
    for i, z in enumerate(zs):
        cy, up, down, w, power = prof.at(z)
        for sx in (1.0, -1.0):
            root = Vector((sx * xoff, cy - down + 0.25 * down, z))
            m.part, m.index, m.root = SWIM, i, root
            length = long * (1.0 - 0.06 * i)

            def point(t, u, root=root, sx=sx, length=length):
                # hanging down and a little back, its two branches as one paddle
                return root + Vector((sx * (0.12 * length * t + 0.08 * length * (u - 0.5)), -length * t,
                                      -0.16 * length * t + wide * (u - 0.4) * (1.0 - 0.3 * t)))

            blade(m, "swimmerets", point, Vector((sx * facing_k, 0.0, -1.0)), wide * 0.14, nt, nu, tags=lambda t, u: (None, t))
    m.root = None


def tail_fan(m, low, telson, paddles, nt, nu):
    """The telson (`telson(t, u)` a place) and the paddles either side: (root, spread, long, wide, droop)."""
    m.part, m.root = FAN, None
    m.index = 0
    thick, point = telson
    blade(m, "tail fan", point, UP, thick, nt, nu, tags=lambda t, u: (None, t))
    for sx in (1.0, -1.0):
        for k, (root, spread, long, wide, droop) in enumerate(paddles):
            m.index = 1 + k
            r = Vector((sx * root[0], root[1], root[2]))
            way = Vector((sx * math.sin(spread), -droop, math.cos(spread))).normalized()
            across = Vector((sx * math.cos(spread), 0.0, -math.sin(spread)))

            def point(t, u, r=r, way=way, across=across, long=long, wide=wide):
                w = wide * math.sin(math.pi * min(1.0, 0.18 + 0.82 * t)) ** 0.5 * (1.0 - 0.25 * t) + 0.0001
                return r + way * (long * t) + across * (w * (u - 0.35))

            blade(m, "tail fan", point, UP, thick * 0.7, nt, nu, tags=lambda t, u: (None, t))
    m.index = 0


# ---------------------------------------------------------------------------------------------------------------
# THE SCARLET CLEANER SHRIMP: 0.058 m, z from -0.0285 (the rostrum's tip) to +0.0295 (the tail's).

CLEANER_BOX = (Vector((-0.012, 0.0, -0.032)), Vector((0.012, 0.024, 0.032)))
CLEANER = Profile([
    (-0.0178, 0.0104, 0.0004, 0.0004, 0.0004, 2.0),
    (-0.0172, 0.0103, 0.0019, 0.0020, 0.0015, 2.0),
    (-0.0160, 0.0101, 0.0034, 0.0034, 0.0025, 2.1),
    (-0.0140, 0.0100, 0.0044, 0.0042, 0.0030, 2.2),
    (-0.0100, 0.0100, 0.0048, 0.0045, 0.0032, 2.2),
    (-0.0050, 0.0101, 0.0047, 0.0043, 0.0031, 2.3),
    (-0.0018, 0.0102, 0.0044, 0.0038, 0.0029, 2.4),
    (0.0000, 0.0104, 0.0041, 0.0036, 0.0027, 2.7),
    (0.0040, 0.0108, 0.0039, 0.0034, 0.0025, 2.7),
    (0.0080, 0.0110, 0.0036, 0.0032, 0.0023, 2.7),
    (0.0112, 0.0105, 0.0031, 0.0029, 0.0020, 2.6),
    (0.0145, 0.0093, 0.0026, 0.0024, 0.0017, 2.4),
    (0.0180, 0.0083, 0.0020, 0.0019, 0.0014, 2.3),
    (0.0215, 0.0078, 0.0015, 0.0014, 0.0011, 2.2),
    (0.0228, 0.0077, 0.0008, 0.0008, 0.0007, 2.0),
], grooves=(-0.0018, 0.0022, 0.0061, 0.0100, 0.0139, 0.0176))
CLEANER_SWIM = (0.0003, 0.0042, 0.0081, 0.012, 0.0156)
CLEANER_LEGS = [((0.0016, 0.0067, -0.0138), -45.0, 0.0072, 0.0098, 0.00042),
                ((0.0018, 0.0066, -0.0112), -20.0, 0.0105, 0.0112, 0.00034),
                ((0.0019, 0.0065, -0.0088), 0.0, 0.0115, 0.0115, 0.00034),
                ((0.0019, 0.0065, -0.0062), 20.0, 0.0112, 0.0112, 0.00034),
                ((0.0018, 0.0066, -0.0040), 40.0, 0.0102, 0.0106, 0.00034)]


def make_cleaner(low):
    m = Mesh(CLEANER_BOX)
    body(m, low, CLEANER, 0.0005, 0.0032, 0.0042, (28, 6, 8))
    # a short rostrum: a thin blade up and forward from the carapace's front, a few teeth along its top
    m.part, m.index, m.root = ROSTRUM, 0, None

    def rostrum_point(t, u):
        z = -0.0168 - 0.0117 * t
        top = 0.0143 - 0.0008 * t + 0.0010 * t ** 2
        high = 0.0016 * (1.0 - t) ** 0.8 + 0.0001
        if low is not True:
            f = (t * 6.0) % 1.0
            top += 0.00035 * (1.0 - f) ** 2 * (1.0 - smooth(0.6, 0.8, t))
        return Vector((0.0, top - high * u, z))

    blade(m, "rostrum", rostrum_point, Vector((1.0, 0.0, 0.0)), 0.0004, pick(low, 24, 3, 4), pick(low, 3, 1, 1),
          tags=lambda t, u: (None, t))
    eyes(m, low, (0.0012, 0.0118, -0.0160), (0.0026, 0.0124, -0.0186), 0.0014, 0.00075, gaze=(0.6, 0.15, -0.78), game_ball=(4, 10))
    for sx in (1.0, -1.0):
        def v(x, y, z, sx=sx):
            return Vector((sx * x, y, z))
        # the long white antennae: forward and up, then sweeping out and back past the tail and beyond
        base = v(0.0014, 0.0082, -0.0172)
        guide = [base, v(0.003, 0.010, -0.026), v(0.008, 0.016, -0.034), v(0.020, 0.024, -0.030),
                 v(0.034, 0.026, -0.010), v(0.046, 0.024, 0.020), v(0.056, 0.020, 0.055), v(0.062, 0.016, 0.09)]
        ts = pick(low, None, None, (0.0, 0.05, 0.1, 0.16, 0.22, 0.29, 0.37, 0.46, 0.56, 0.67, 0.78, 0.89, 1.0))
        whip(m, 0, base, guide, pick(low, 80, 6, 5), 0.00032, pick(low, 5, 3, 3), ts=ts)
        # the antennules: a short stalk, then two whips, white too, one long and one short
        base = v(0.0008, 0.0108, -0.0176)
        stalk = [base, v(0.0013, 0.0114, -0.0215), v(0.0017, 0.0118, -0.0238)]
        whip(m, 1, base, stalk, pick(low, 4, 1, 1), 0.00042, pick(low, 6, 3, 3), along=(0.0, 0.25), taper=0.3, caps=(True, True))
        if low is not True:
            for lean, rise, reach in ((1.0, 0.006, 0.055), (0.3, -0.001, 0.028))[:pick(low, 2, 0, 1)]:
                g = [stalk[-1], v(0.003 + 0.006 * lean, 0.014 + rise * 0.5, -0.03 - reach * 0.3),
                     v(0.006 + 0.016 * lean, 0.016 + rise, -0.024 - reach * 0.55), v(0.01 + 0.03 * lean, 0.014 + rise, -0.016 - reach * 0.5)]
                whip(m, 1, base, g, pick(low, 30, 0, 4), 0.00022, pick(low, 4, 0, 3), along=(0.25, 1.0), taper=0.6)
        # the antennal scale, a little blade forward from the antenna's base
        m.part, m.index, m.root = SCALE, 0, None
        sr = v(0.0019, 0.0086, -0.0168)

        def scale_point(t, u, sr=sr, sx=sx):
            wide = 0.0012 * math.sin(math.pi * min(1.0, 0.15 + 0.85 * t)) ** 0.6 * (1.0 - 0.5 * t) + 0.0001
            return sr + Vector((sx * (0.0008 * t + wide * (u - 0.3)), 0.0006 * t, -0.0075 * t))

        blade(m, "scales", scale_point, Vector((0.0, 1.0, 0.0)), 0.00022, pick(low, 8, 2, 2), pick(low, 4, 1, 1), tags=lambda t, u: (None, t))
        # a pair of leg-like mouthparts forward under the head
        if not low:
            m.part, m.index, m.root = MOUTH, 0, None
            n = 8
            path = [bezier([v(0.0012, 0.0062, -0.0135), v(0.0022, 0.0042, -0.019), v(0.0018, 0.0058, -0.0235)], i / n) for i in range(n + 1)]
            tube(m, path, [0.0003 * (1.0 - 0.5 * i / n) for i in range(n + 1)], pick(low, 5, 0, 3), "mouthparts", along=(0.0, 1.0))
    m.a = 0.0
    for sx in (1.0, -1.0):
        for i, (root, heading, reach, knee_high, radius) in enumerate(CLEANER_LEGS):
            leg(m, LEG, i, (sx * root[0], root[1], root[2]), heading, reach, knee_high, radius, pick(low, 6, 3, 3), "legs", low)
    swimmerets(m, low, CLEANER_SWIM, CLEANER, 0.0028, 0.0012, 0.0011, pick(low, 6, 1, 1), pick(low, 3, 1, 1))

    def telson(t, u):
        wide = 0.0009 * (1.0 - t) ** 0.9 + 0.0001
        return Vector((wide * (2.0 * u - 1.0), 0.0077 - 0.0012 * t, 0.0205 + 0.0090 * t))

    tail_fan(m, low, (0.0005, telson), [((0.0008, 0.0077, 0.0207), 0.18, 0.0088, 0.0022, 0.1),
                                        ((0.0008, 0.0077, 0.0207), 0.36, 0.0080, 0.0025, 0.1)],
             pick(low, 10, 1, 2), pick(low, 5, 1, 1))
    return m


# ---------------------------------------------------------------------------------------------------------------
# THE PEACOCK MANTIS SHRIMP: 0.15 m, z from -0.075 (its rostral plate's front) to +0.075 (its telson's end).

MANTIS_BOX = (Vector((-0.03, 0.0, -0.09)), Vector((0.03, 0.05, 0.09)))
MANTIS = Profile([
    (-0.0700, 0.0170, 0.0010, 0.0010, 0.0020, 2.0),
    (-0.0690, 0.0170, 0.0040, 0.0040, 0.0060, 2.2),
    (-0.0660, 0.0168, 0.0060, 0.0056, 0.0085, 2.5),
    (-0.0560, 0.0165, 0.0068, 0.0060, 0.0098, 2.7),
    (-0.0420, 0.0160, 0.0068, 0.0058, 0.0108, 2.8),
    (-0.0330, 0.0156, 0.0064, 0.0055, 0.0104, 2.8),
    (-0.0290, 0.0153, 0.0052, 0.0050, 0.0086, 2.9),
    (-0.0200, 0.0150, 0.0054, 0.0050, 0.0094, 2.9),
    (-0.0100, 0.0148, 0.0060, 0.0052, 0.0124, 3.0),
    (0.0050, 0.0146, 0.0062, 0.0052, 0.0132, 3.0),
    (0.0250, 0.0142, 0.0060, 0.0050, 0.0132, 3.0),
    (0.0420, 0.0136, 0.0054, 0.0046, 0.0124, 2.9),
    (0.0540, 0.0130, 0.0044, 0.0038, 0.0110, 2.7),
    (0.0570, 0.0128, 0.0030, 0.0026, 0.0080, 2.4),
    (0.0580, 0.0128, 0.0010, 0.0010, 0.0030, 2.0),
], grooves=(-0.0310, -0.0250, -0.0190, -0.0124, -0.0010, 0.0105, 0.0220, 0.0332, 0.0442), groove_depth=0.09)
MANTIS_SWIM = (-0.0062, 0.0052, 0.0167, 0.0280, 0.0390)
MANTIS_LEGS = [((0.0075, 0.0105, -0.0275), -15.0, 0.0165, 0.0128, 0.0011),
               ((0.0080, 0.0105, -0.0215), 10.0, 0.0172, 0.0130, 0.0011),
               ((0.0080, 0.0105, -0.0155), 32.0, 0.0165, 0.0126, 0.0011)]
# As the shader has it (MANTIS in shrimp.gd): the left raptorial arm's shoulder and elbow.
MANTIS_SHOULDER = (0.0080, 0.0140, -0.0560)
MANTIS_ELBOW = (0.0105, 0.0100, -0.0690)


def make_mantis(low):
    m = Mesh(MANTIS_BOX)
    body(m, low, MANTIS, 0.0012, 0.0075, 0.012, (36, 8, 12))
    # the rostral plate: a small flat squarish plate over the base of the eyes
    m.part, m.index, m.root = ROSTRUM, 0, None

    def plate(t, u):
        wide = 0.0034 * (1.0 - 0.45 * t ** 2)
        return Vector((wide * (2.0 * u - 1.0), 0.0225 - 0.0008 * t, -0.0685 - 0.0055 * t))

    blade(m, "rostrum", plate, UP, 0.0008, pick(low, 5, 1, 2), pick(low, 6, 2, 3), tags=lambda t, u: (None, t))
    # big eyes on stalks, a little taller than wide (the shader swivels each on its own)
    eyes(m, low, (0.0026, 0.0205, -0.0685), (0.0055, 0.0250, -0.0722), 0.0046, 0.0019, shape=(1.0, 1.2, 1.0),
         gaze=(0.45, 0.25, -0.86), game_ball=(6, 12))
    for sx in (1.0, -1.0):
        def v(x, y, z, sx=sx):
            return Vector((sx * x, y, z))
        # the antennules: a jointed stalk forward, then three whips
        base = v(0.0022, 0.0180, -0.0700)
        stalk = [base, v(0.0035, 0.0205, -0.082), v(0.0055, 0.0235, -0.094)]
        whip(m, 1, base, stalk, pick(low, 6, 1, 2), 0.0009, pick(low, 7, 3, 3), along=(0.0, 0.35), taper=0.25, caps=(True, True))
        if low is not True:
            for lean, rise, reach in ((1.4, 0.004, 0.034), (0.5, 0.008, 0.03), (-0.1, 0.002, 0.026)):
                g = [stalk[-1], v(0.0065 + 0.006 * lean, 0.026 + rise, -0.094 - reach * 0.4),
                     v(0.007 + 0.012 * lean, 0.027 + rise * 1.5, -0.094 - reach * 0.75), v(0.007 + 0.02 * lean, 0.025 + rise, -0.094 - reach)]
                whip(m, 1, base, g, pick(low, 16, 0, 3), 0.0005, pick(low, 5, 0, 3), along=(0.35, 1.0), taper=0.6)
        # the antenna: a short stalk out and forward, its broad oval scale, and a short whip
        base = v(0.0060, 0.0150, -0.0660)
        whip(m, 0, base, [base, v(0.0105, 0.0160, -0.0730), v(0.0150, 0.0175, -0.0790)], pick(low, 4, 1, 2), 0.0008,
             pick(low, 6, 3, 3), along=(0.0, 0.4), taper=0.3, caps=(True, True))
        if low is not True:
            whip(m, 0, base, [v(0.0150, 0.0175, -0.0790), v(0.019, 0.019, -0.088), v(0.022, 0.0185, -0.097)],
                 pick(low, 8, 0, 1), 0.00045, pick(low, 4, 0, 3), along=(0.4, 1.0), taper=0.6)
        m.part, m.index, m.root = SCALE, 0, None
        sr = v(0.0100, 0.0165, -0.0720)

        def scale_point(t, u, sr=sr, sx=sx):
            # an oval paddle out and forward, tilted up at its outer edge
            wide = 0.0042 * math.sin(math.pi * min(1.0, 0.12 + 0.88 * t)) ** 0.7 + 0.0002
            across = (u - 0.5) * 2.0
            return sr + Vector((sx * (0.0085 * t + 0.0022 * across * 0.0 + wide * 0.5 * across * 0.55), 0.0035 * t + 0.0012 * across,
                                -0.0135 * t + wide * across * 0.85))

        blade(m, "scales", scale_point, Vector((0.0, 1.0, 0.0)), 0.0007, pick(low, 8, 2, 3), pick(low, 6, 1, 2), tags=lambda t, u: (None, t))
        # small folded mouthparts (maxillipeds) under the head, between the arms
        if low is not True:
            m.part, m.index, m.root = MOUTH, 0, None
            for j, (zz, yy) in enumerate(((-0.060, 0.010), (-0.054, 0.009))[:pick(low, 2, 0, 1)]):
                n = pick(low, 6, 0, 1)
                path = [bezier([v(0.003, yy + 0.002, zz + 0.006), v(0.0045, yy - 0.001, zz - 0.002), v(0.0035, yy + 0.002, zz - 0.007)], i / n) for i in range(n + 1)]
                tube(m, path, [0.0008 * (1.0 - 0.4 * i / n) for i in range(n + 1)], pick(low, 5, 0, 3), "mouthparts", along=(0.0, 1.0))
        # the raptorial arm, folded as a ">" seen from the side: the merus from the shoulder forward and down to the
        # elbow (the point of the ">", in front of the head), the forearm (propodus) from there back and down to the
        # club (the heel of the dactyl), the hooked dactyl folded forward from the club along the forearm's inside
        shoulder = v(*MANTIS_SHOULDER)
        elbow = v(*MANTIS_ELBOW)
        m.part, m.index, m.root, m.k, m.a = ARM, 0, shoulder, elbow, 0.0
        sides = pick(low, 10, 4, 5)
        mid = shoulder.lerp(elbow, 0.5) + Vector((sx * 0.0004, 0.0004, 0.0))
        if low:
            tube(m, [shoulder, mid, elbow], [0.0024, 0.0030, 0.0024], sides, "arms")
        else:
            tube(m, [shoulder, shoulder.lerp(mid, 0.5), mid, mid.lerp(elbow, 0.5), elbow], [0.0022, 0.0028, 0.0031, 0.0029, 0.0023], sides, "arms")
        m.part = HAND
        club = elbow + Vector((0.0, -0.0047, 0.0180))
        fore = [elbow + Vector((0.0, 0.0, 0.0)), elbow.lerp(club, 0.5) + Vector((sx * 0.0002, -0.0004, 0.0)), club + Vector((0.0, 0.0008, -0.003))]
        tube(m, fore if not low else [fore[0], fore[-1]], [0.0022, 0.0024, 0.0025] if not low else [0.0022, 0.0025], sides, "arms")
        m.a = 1.0
        ball(m, club, 0.0034, 0.0038, 0.0042, "arms", lat=pick(low, 10, 4, 5), lon=pick(low, 14, 6, 8),
             basis=basis_of((club - elbow).normalized()))
        m.a = 0.5
        hook = [club + Vector((sx * -0.0012, 0.0024, -0.0025)), club + Vector((sx * -0.0016, 0.0040, -0.0090)), club + Vector((sx * -0.0012, 0.0048, -0.0150))]
        n = pick(low, 6, 1, 2)
        tube(m, [bezier(hook, i / n) for i in range(n + 1)], [0.0012 * (1.0 - 0.7 * i / n) for i in range(n + 1)],
             pick(low, 6, 3, 3), "arms")
        m.part, m.root, m.k, m.a = BODY, None, Vector((0.0, 0.0, 0.0)), 0.0
    for sx in (1.0, -1.0):
        for i, (root, heading, reach, knee_high, radius) in enumerate(MANTIS_LEGS):
            leg(m, LEG, i, (sx * root[0], root[1], root[2]), heading, reach, knee_high, radius, pick(low, 6, 3, 3), "legs", low)
    # broad paddle swimmerets under the abdomen
    swimmerets(m, low, MANTIS_SWIM, MANTIS, 0.0066, 0.0062, 0.0042, pick(low, 5, 1, 1), pick(low, 4, 1, 2), facing_k=0.05)

    def telson(t, u):
        # a broad shield, rounded behind, with a low keel down its middle
        across = 2.0 * u - 1.0
        wide = 0.0108 * math.sqrt(max(0.0, 1.0 - t ** 2.4)) + 0.0004
        keel = 0.0009 * (1.0 - abs(across)) ** 3
        return Vector((wide * across, 0.0128 - 0.0008 * t + keel, 0.0540 + 0.0205 * t))

    tail_fan(m, low, (0.0016, telson), [((0.0070, 0.0122, 0.0545), 0.32, 0.0170, 0.0052, 0.05),
                                        ((0.0080, 0.0118, 0.0540), 0.62, 0.0150, 0.0060, 0.06)],
             pick(low, 10, 1, 2), pick(low, 8, 1, 2))
    return m


# ---------------------------------------------------------------------------------------------------------------
# THE PISTOL SHRIMP: 0.045 m, z from -0.0225 (the rostrum's tip) to +0.0225 (the tail's); its big claw on its right
# (-X) reaches 0.017 m ahead of the rostrum.

PISTOL_BOX = (Vector((-0.014, 0.0, -0.045)), Vector((0.014, 0.024, 0.025)))
PISTOL = Profile([
    (-0.0170, 0.0086, 0.0006, 0.0006, 0.0006, 2.0),
    (-0.0166, 0.0086, 0.0024, 0.0024, 0.0022, 2.0),
    (-0.0156, 0.0086, 0.0038, 0.0036, 0.0033, 2.1),
    (-0.0130, 0.0086, 0.0045, 0.0042, 0.0038, 2.2),
    (-0.0080, 0.0087, 0.0047, 0.0043, 0.0040, 2.2),
    (-0.0030, 0.0088, 0.0045, 0.0040, 0.0038, 2.3),
    (-0.0004, 0.0089, 0.0042, 0.0037, 0.0035, 2.5),
    (0.0030, 0.0090, 0.0040, 0.0035, 0.0033, 2.6),
    (0.0070, 0.0088, 0.0036, 0.0032, 0.0030, 2.6),
    (0.0105, 0.0082, 0.0030, 0.0027, 0.0025, 2.5),
    (0.0135, 0.0076, 0.0023, 0.0021, 0.0019, 2.3),
    (0.0160, 0.0073, 0.0016, 0.0015, 0.0013, 2.2),
    (0.0170, 0.0073, 0.0008, 0.0008, 0.0007, 2.0),
], grooves=(-0.0004, 0.0029, 0.0061, 0.0092, 0.0122, 0.0150), groove_depth=0.06)
PISTOL_SWIM = (0.0012, 0.0045, 0.0076, 0.0106, 0.0134)
PISTOL_LEGS = [((0.0016, 0.0058, -0.0098), -25.0, 0.0080, 0.0086, 0.00028),
               ((0.0018, 0.0057, -0.0078), 0.0, 0.0086, 0.0090, 0.00034),
               ((0.0018, 0.0057, -0.0058), 22.0, 0.0084, 0.0088, 0.00034),
               ((0.0017, 0.0058, -0.0040), 42.0, 0.0078, 0.0084, 0.00034)]
# As the shader has it (PISTOL in shrimp.gd): the big claw's finger's hinge.
PISTOL_HINGE = (-0.0070, 0.0087, -0.0274)


def claw(m, low, sx, root, elbow, palm_at, palm_size, finger_long, big):
    """A claw on its arm: the arm from `root` to `elbow`, the palm a swollen ellipsoid along -Z at `palm_at`, the
    fixed finger running on from its lower front, the moving finger (the dactyl) above it from its upper front."""
    m.part, m.index, m.root, m.a = ARM, 0 if big else 1, Vector(root), 0.0
    root, elbow, palm_at = Vector(root), Vector(elbow), Vector(palm_at)
    sides = pick(low, 8, 3, 4 if big else 3)
    pl, ph, pw = palm_size
    radius = ph * 0.32
    wrist = palm_at + Vector((0.0, 0.0, pl * 0.95))
    tube(m, [root, elbow, wrist] if not low or big else [root, wrist], [radius * 0.8, radius * 0.9, radius] if not low or big else [radius * 0.8, radius],
         sides, "claws", caps=(True, False))
    ball(m, palm_at, pw, ph, pl, "claws", lat=pick(low, 12, 4, 5 if big else 4), lon=pick(low, 14, 6, 8 if big else 6),
         basis=basis_of(Vector((0.0, 0.0, -1.0))))
    # the fixed finger (the pollex), from the palm's lower front, tapering to a point that turns up a little
    front = palm_at + Vector((0.0, -ph * 0.3, -pl * 0.8))
    n = pick(low, 6, 1, 2 if big else 1)
    fixed = [bezier([front, front + Vector((0.0, -ph * 0.1, -finger_long * 0.55)), front + Vector((0.0, ph * 0.25, -finger_long))], i / n) for i in range(n + 1)]
    tube(m, fixed, [ph * 0.32 * (1.0 - 0.75 * i / n) for i in range(n + 1)], sides, "claws", caps=(False, True))
    # the moving finger, hinged at the palm's upper front
    hinge = palm_at + Vector((0.0, ph * 0.45, -pl * 0.82))
    if big:
        hinge = Vector((sx * abs(PISTOL_HINGE[0]), PISTOL_HINGE[1], PISTOL_HINGE[2]))
    m.part, m.root = (HAND, hinge) if big else (ARM, Vector(root))
    m.a = 1.0
    moving = [bezier([hinge, hinge + Vector((0.0, ph * 0.12, -finger_long * 0.5)), hinge + Vector((0.0, -ph * 0.3, -finger_long * 1.02))], i / n) for i in range(n + 1)]
    tube(m, moving, [ph * 0.3 * (1.0 - 0.75 * i / n) for i in range(n + 1)], sides, "claws", caps=(True, True))
    if big and not low:
        # the plunger on the moving finger's underside, which fits a socket in the fixed one
        ball(m, hinge + Vector((0.0, -ph * 0.2, -finger_long * 0.3)), ph * 0.14, ph * 0.14, ph * 0.2, "claws",
             lat=pick(low, 6, 3, 3), lon=pick(low, 8, 4, 5))
    m.root = None
    m.a = 0.0


def make_pistol(low):
    m = Mesh(PISTOL_BOX)
    body(m, low, PISTOL, 0.00045, 0.0028, 0.0055, (26, 6, 8))
    # the carapace's hood over the eyes: a short shelf forward from its front either side of a tiny rostrum
    m.part, m.index, m.root = ROSTRUM, 0, None

    def hood(t, u):
        across = 2.0 * u - 1.0
        wide = 0.0034 * (1.0 - 0.3 * t)
        reach = 0.0052 * (1.0 - 0.55 * abs(across) ** 2) + 0.0018 * (1.0 - abs(across)) ** 6
        return Vector((wide * across, 0.0122 - 0.0012 * t - 0.0008 * abs(across), -0.0158 - reach * t))

    blade(m, "rostrum", hood, UP, 0.0007, pick(low, 5, 1, 1), pick(low, 10, 2, 3), tags=lambda t, u: (None, t))
    eyes(m, low, (0.0010, 0.0098, -0.0170), (0.0022, 0.0100, -0.0196), 0.0012, 0.0007, gaze=(0.35, 0.1, -0.93), game_ball=(4, 8))
    for sx in (1.0, -1.0):
        def v(x, y, z, sx=sx):
            return Vector((sx * x, y, z))
        base = v(0.0014, 0.0070, -0.0170)
        guide = [base, v(0.003, 0.0085, -0.026), v(0.008, 0.011, -0.030), v(0.016, 0.012, -0.025), v(0.024, 0.011, -0.010), v(0.028, 0.009, 0.006)]
        ts = pick(low, None, None, (0.0, 0.1, 0.22, 0.36, 0.52, 0.7, 0.85, 1.0))
        whip(m, 0, base, guide, pick(low, 40, 4, 4), 0.0003, pick(low, 5, 3, 3), ts=ts)
        base = v(0.0008, 0.0090, -0.0172)
        stalk = [base, v(0.0012, 0.0094, -0.0205), v(0.0016, 0.0096, -0.0225)]
        whip(m, 1, base, stalk, pick(low, 4, 1, 1), 0.00038, pick(low, 6, 3, 3), along=(0.0, 0.3), taper=0.3, caps=(True, True))
        if low is not True:
            for lean in (1.0, 0.2)[:pick(low, 2, 0, 1)]:
                g = [stalk[-1], v(0.0022 + 0.004 * lean, 0.0105, -0.026), v(0.003 + 0.008 * lean, 0.011, -0.031)]
                whip(m, 1, base, g, pick(low, 10, 0, 2), 0.0002, pick(low, 4, 0, 3), along=(0.3, 1.0), taper=0.5)
        m.part, m.index, m.root = SCALE, 0, None
        sr = v(0.0019, 0.0075, -0.0165)

        def scale_point(t, u, sr=sr, sx=sx):
            wide = 0.0010 * math.sin(math.pi * min(1.0, 0.15 + 0.85 * t)) ** 0.6 + 0.0001
            return sr + Vector((sx * (0.0008 * t + wide * (u - 0.3)), 0.0005 * t, -0.0055 * t))

        blade(m, "scales", scale_point, Vector((0.0, 1.0, 0.0)), 0.0002, pick(low, 6, 2, 2), pick(low, 3, 1, 1), tags=lambda t, u: (None, t))
    m.a = 0.0
    # the big snapping claw on its right, the small one on its left (Claude's pick of sides: both happen)
    claw(m, low, -1.0, (-0.0018, 0.0062, -0.0120), (-0.0055, 0.0060, -0.0150), (-0.0070, 0.0070, -0.0215),
         (0.0072, 0.0038, 0.0024), 0.0078, True)
    claw(m, low, 1.0, (0.0018, 0.0062, -0.0120), (0.0040, 0.0055, -0.0170), (0.0042, 0.0062, -0.0225),
         (0.0026, 0.0012, 0.0010), 0.0032, False)
    for sx in (1.0, -1.0):
        for i, (root, heading, reach, knee_high, radius) in enumerate(PISTOL_LEGS):
            leg(m, LEG, i, (sx * root[0], root[1], root[2]), heading, reach, knee_high, radius, pick(low, 6, 3, 3), "legs", low)
    swimmerets(m, low, PISTOL_SWIM, PISTOL, 0.0022, 0.0010, 0.0012, pick(low, 5, 1, 1), pick(low, 3, 1, 1))

    def telson(t, u):
        wide = 0.0013 * (1.0 - 0.5 * t) + 0.0001
        return Vector((wide * (2.0 * u - 1.0), 0.0073 - 0.0006 * t, 0.0155 + 0.0070 * t))

    tail_fan(m, low, (0.0005, telson), [((0.0008, 0.0073, 0.0157), 0.2, 0.0068, 0.0020, 0.08),
                                        ((0.0008, 0.0073, 0.0157), 0.42, 0.0062, 0.0022, 0.08)],
             pick(low, 8, 1, 2), pick(low, 4, 1, 1))
    return m


KINDS = {"cleaner": (make_cleaner, 0.08, (0.85, 0.2, 0.15, 1.0)),
         "mantis": (make_mantis, 0.2, (0.25, 0.6, 0.3, 1.0)),
         "pistol": (make_pistol, 0.075, (0.5, 0.46, 0.32, 1.0))}


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
    # (every layer made first, then each looked up by name: making one moves the others)
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
    # (the glTF writer only writes the colour that is marked for rendering)
    mesh.color_attributes.active_color = colours
    mesh.color_attributes.render_color_index = 0
    mesh.materials.append(material_of(name.replace("_lo", "").replace("_game", ""), colour))
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
    spent = {}
    for face, (out, group) in zip(m.faces, m.out):
        spent[group] = spent.get(group, 0) + len(face) - 2
    print("TRIANGLES %s: %s" % (name, ", ".join("%s %d" % item for item in spent.items())))
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
    """Pictures of each model from every side (plain: the markings are the shader's)."""
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.show_cavity = True
    scene.display.shading.show_backface_culling = True
    scene.display.shading.color_type = "MATERIAL"
    scene.render.resolution_x, scene.render.resolution_y = 1200, 800
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    views = [("left", (1, 0, 0)), ("right", (-1, 0, 0)), ("front", (0, 1, 0)), ("back", (0, -1, 0)),
             ("top", (0.001, 0, 1)), ("under", (0.001, 0, -1)), ("quarter", (0.7, 0.6, 0.45))]
    for obj in made:
        for other in made:
            other.hide_render = other is not obj
        for view, direction in views:
            offset = Vector(direction).normalized() * 40.0
            camera.data.ortho_scale = size
            camera.location = Vector((0.0, 0.0, size * 0.12)) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s_%s.png" % (obj.name, view))
            bpy.ops.render.render(write_still=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    only = [a for a in ARGS[1:] if a in KINDS]
    for kind, (make, size, colour) in KINDS.items():
        if only and kind not in only:
            continue
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version = 0
        name = "shrimp_" + kind
        made = []
        for low, suffix in ((False, ""), ("game", "_game"), (True, "_lo")):
            FAT[0] = game_fat if low == "game" else (lambda sides: 1.0)
            made.append(finish(name + suffix, make(low), colour))
        FAT[0] = lambda sides: 1.0
        for obj, suffix in zip(made, ("", "_game", "_lo")):
            export_one(obj, os.path.join(OUT, name + suffix + ".glb"))
        made[1].location.x = size
        made[2].location.x = size * 2.0
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, name + ".blend"))
        made[1].location.x = 0.0
        made[2].location.x = 0.0
        if PREVIEW:
            os.makedirs(PREVIEW, exist_ok=True)
            render(PREVIEW, made, size)


if __name__ == "__main__":
    main()
