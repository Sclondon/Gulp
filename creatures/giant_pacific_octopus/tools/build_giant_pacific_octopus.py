"""Builds the giant Pacific octopus (creatures/giant_pacific_octopus) and exports it for Godot.

Run from the game's root:
    blender --background --factory-startup --python creatures/giant_pacific_octopus/tools/build_giant_pacific_octopus.py
    blender --background --factory-startup --python creatures/giant_pacific_octopus/tools/build_giant_pacific_octopus.py -- <folder for pictures>

Writes creatures/giant_pacific_octopus/models/giant_pacific_octopus.glb (the full model),
giant_pacific_octopus_lo.glb (far off: no suckers, no papillae, fewer rings) and giant_pacific_octopus_game.glb (the
game model, about 4,400 triangles at Twilight Princess weight: rings placed where the outline and the eye need them,
the biggest papillae only, and no sucker geometry: green 1 on its arms' skin tells the shader to paint the suckers
where the full model has them), and the editable
creatures/giant_pacific_octopus/tools/giant_pacific_octopus.blend (this folder has a .gdignore). Each is one static
mesh with one surface: the shader (giant_pacific_octopus.gdshader) pulses the mantle, lays every arm along its
rope, hangs the web between the arms, and draws the skin. It prints a WINDING line: the check that nothing is
inside out (every face is given a point it must look away from; a face that does not is counted).

A giant Pacific octopus (Enteroctopus dofleini): about 1.0 m from the mantle's tip to the web's edge, arms 1.6 m.

- THE MANTLE: a baggy sack 0.55 m long, widest behind its middle, round at its end, sagging a little; its skin
  thrown into folds and lumps, with pointed papillae standing on its back and sides.
- THE HEAD: narrower than the mantle; an eye raised on a turret on each side of its top (a gold eye, the pupil a
  level slit), horns of skin over them; the siphon a tube out from under the mantle's collar on its +X side.
- THE ARMS: eight, thick at the root and tapering to a thread, round-backed, the inner face flatter with two rows
  of suckers all the way down, biggest near the mouth.
- THE WEB: a sheet of skin between each arm and the next over the first fifth of their length (two sheets back to
  back, one looking out and one in, so that it is seen from both sides in one solid draw).
- THE MOUTH: a pale disc in the middle of the ring of arms.

Godot space until it is written out (metres, Y up): it swims mantle first, towards -Z; its arms trail towards +Z;
its back is +Y. The origin is the middle of the head, between the eyes.

In the model every arm lies straight along +Z from its root. GiantPacificOctopus simulates each as a rope and the
shader lays it along that rope: the roots and lengths here are worked out the same way in
creatures/giant_pacific_octopus/giant_pacific_octopus.gd (`strands()`) and the roots again in the shader: change
one, change the others.

What a point is, for the shader: vertex colour red the part (0 the mantle, 0.2 the web, 0.4 the head and siphon,
0.6 an eye, 0.8 the skin of an arm, 1 a sucker); green: on the web 0 the sheet that looks out and 1 the one that
looks in, on the head 1 for the mouth, on an eye 1 for the one on -X; blue: on an arm, a sucker or the web which
arm ((n + 0.5) / 16), on the mantle and head 1 at a papilla's point. UV.x round it (the web: 0 at its own arm to
1 at the next; an arm: 0.5 down the middle of its inner, suckered face; a sucker: 0 its foot to 1 the middle of
its cup; an eye: across its face, 0.5 the middle), UV.y along it (the mantle: collar 0 to tip 1; an arm, a sucker
or the web: root 0 to tip 1; an eye: up its face, 0.5 the middle). UV2.x an arm's length (metres), UV2.y its
phase (0..1). (The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.)
"""

import math
import os
import random
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "models")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = ARGS[0] if ARGS else ""
TAU = math.tau


def pick(q, full, game, low):
    """A number for the model `q` being built: the full one, the game one or the low one."""
    return {"full": full, "game": game, "low": low}[q]


# Kept in step with giant_pacific_octopus.gd and the shader.
MANTLE_FROM = -0.03
MANTLE_LONG = 0.55
ARMS = 8
ARM_RING = 0.09
ARM_Z = 0.13
ARM_LONG = 1.6
WEB = 0.2
NAME = "giant_pacific_octopus"


def to_b(p):
    return Vector((p.x, -p.z, p.y))


def fract(x):
    return x - math.floor(x)


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def hash3(x, y, z):
    return fract(math.sin(x * 127.1 + y * 311.7 + z * 74.7) * 43758.5453)


def noise3(p):
    """Smooth noise, 0..1."""
    ix, iy, iz = math.floor(p.x), math.floor(p.y), math.floor(p.z)
    fx, fy, fz = p.x - ix, p.y - iy, p.z - iz
    fx, fy, fz = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy), fz * fz * (3 - 2 * fz)

    def mix(a, b, t):
        return a + (b - a) * t
    return mix(
        mix(mix(hash3(ix, iy, iz), hash3(ix + 1, iy, iz), fx), mix(hash3(ix, iy + 1, iz), hash3(ix + 1, iy + 1, iz), fx), fy),
        mix(mix(hash3(ix, iy, iz + 1), hash3(ix + 1, iy, iz + 1), fx), mix(hash3(ix, iy + 1, iz + 1), hash3(ix + 1, iy + 1, iz + 1), fx), fy),
        fz)


def strand(k):
    """Arm k: its root, its length, its phase, the way out from the middle it lies (a unit, x and y)."""
    a = (k + 0.5) * TAU / ARMS
    out = Vector((math.cos(a), math.sin(a), 0.0))
    return out * ARM_RING + Vector((0.0, 0.0, ARM_Z)), ARM_LONG * (1.0 - 0.05 * math.sin(a)), fract(k * 0.37 + 0.11), out


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.data = []
        # faces wound against the way they should look: [wrong, all] for each kind of part
        self.wound = {}

    def add(self, p, uv, uv2, colour):
        self.verts.append(p)
        self.data.append(((uv[0], 1.0 - uv[1]), (uv2[0], 1.0 - uv2[1]), colour))
        return len(self.verts) - 1

    def face(self, points, kind, away):
        """A face; `away` is a point it must look away from (None: any way will do)."""
        self.faces.append(tuple(points))
        tally = self.wound.setdefault(kind, [0, 0])
        if away is not None:
            ps = [self.verts[i] for i in points]
            normal = Vector()
            for i in range(len(ps)):
                normal += ps[i].cross(ps[(i + 1) % len(ps)])
            if normal.length > 1e-14:
                tally[1] += 1
                middle = sum(ps, Vector()) / len(ps)
                if normal.dot(middle - away) <= 0.0:
                    tally[0] += 1


def mantle_radius(t):
    """How thick the mantle is, `t` from its collar (0) to its tip (1): a sack, widest behind its middle."""
    if t < 0.55:
        return 0.135 + 0.065 * smooth(0.0, 0.55, t)
    return max(0.2 * max(1.0 - ((t - 0.55) / 0.45) ** 2, 0.0) ** 0.5, 0.004)


def mantle_point(t, a, wrinkled=True):
    r = mantle_radius(t)
    ca, sa = math.cos(a), math.sin(a)
    z = MANTLE_FROM - t * MANTLE_LONG
    if wrinkled:
        # folds across it, lumps, and a slow unevenness: a bag of skin (less at the collar and the very end)
        q = Vector((ca * 0.2, sa * 0.2, z))
        fold = math.sin(t * 34.0 + 5.0 * noise3(q * 6.0) + 2.0 * sa)
        lump = noise3(q * 24.0) - 0.5
        slow = noise3(q * 7.0 + Vector((3.1, 0.0, 0.0))) - 0.5
        r += (0.007 * fold + 0.016 * lump + 0.03 * slow) * smooth(0.0, 0.14, t) * min(r / 0.1, 1.0)
    # (taller than wide behind, and sagging)
    return Vector((ca * r, sa * r * (1.0 + 0.08 * smooth(0.2, 0.7, t)) - 0.035 * smooth(0.1, 0.9, t), z))


def mantle_normal(t, a):
    e = 0.004
    n = (mantle_point(t, a + e) - mantle_point(t, a - e)).cross(mantle_point(min(t + e, 1.0), a) - mantle_point(max(t - e, 0.0), a))
    if n.length < 1e-12:
        return Vector((math.cos(a), math.sin(a), 0.0))
    n.normalize()
    return n if n.dot(Vector((math.cos(a), math.sin(a), 0.0))) > 0.0 else -n


def mantle(m, q):
    around = pick(q, 56, 20, 16)
    rings_n = pick(q, 52, 22, 12)
    colour = (0.0, 0.0, 0.0, 1.0)
    rings = []
    # (the lip of the collar: turned in, so that the edge has a thickness and the head's neck goes inside it)
    for wide, deep in ((0.7, 0.07), (0.84, 0.0)):
        ring = []
        for c in range(around):
            p = mantle_point(0.0, c / around * TAU, False)
            ring.append(m.add(Vector((p.x * wide, p.y * wide, p.z - deep)), (c / around, 0.0), (0.0, 0.0), colour))
        rings.append(ring)
    for r in range(rings_n + 1):
        u = r / rings_n
        t = 0.55 * u / 0.5 if u < 0.5 else 0.55 + 0.45 * math.sin((u - 0.5) / 0.5 * math.pi * 0.5)
        rings.append([m.add(mantle_point(t, c / around * TAU), (c / around, t), (0.0, 0.0), colour) for c in range(around)])
    for a, b in zip(rings[2:], rings[3:]):
        middle = (sum((m.verts[i] for i in a), Vector()) + sum((m.verts[i] for i in b), Vector())) / (2 * around)
        for c in range(around):
            d = (c + 1) % around
            m.face((a[c], b[c], b[d], a[d]), "mantle", middle)
    tip = m.add(Vector((0.0, mantle_point(1.0, 0.0).y, MANTLE_FROM - MANTLE_LONG - 0.002)), (0.0, 1.0), (0.0, 0.0), colour)
    last = rings[-1]
    for c in range(around):
        m.face((last[c], tip, last[(c + 1) % around]), "mantle", Vector((0.0, 0.0, MANTLE_FROM - MANTLE_LONG + 0.1)))
    # the lip: its inside looks in towards the neck, its edge towards the arms
    a, b = rings[0], rings[1]
    for c in range(around):
        d = (c + 1) % around
        mid = (m.verts[a[c]] + m.verts[b[d]]) * 0.5
        m.face((a[c], b[c], b[d], a[d]), "lip", Vector((mid.x * 3.0, mid.y * 3.0, mid.z)))
    a, b = rings[1], rings[2]
    for c in range(around):
        d = (c + 1) % around
        m.face((a[c], b[c], b[d], a[d]), "lip", (m.verts[a[c]] + m.verts[b[d]]) * 0.5 - Vector((0.0, 0.0, 1.0)))


def papilla(m, p, n, wide, high, along, part, kind="papillae", sides=5):
    """A pointed papilla standing on the skin at `p`, which looks along `n`."""
    side = n.cross(Vector((0.0, 0.0, 1.0)))
    if side.length < 0.01:
        side = n.cross(Vector((1.0, 0.0, 0.0)))
    side.normalize()
    other = n.cross(side)
    ring = [m.add(p - n * 0.004 + (side * math.cos(c / sides * TAU) + other * math.sin(c / sides * TAU)) * wide, (0.0, along), (0.0, 0.0), (part, 0.0, 0.0, 1.0)) for c in range(sides)]
    top = m.add(p + n * high, (0.0, along), (0.0, 0.0), (part, 0.0, 1.0, 1.0))
    for c in range(sides):
        m.face((ring[c], ring[(c + 1) % sides], top), kind, p - n * 0.01)


def papillae(m, q):
    """The full model: 230 on the mantle and 26 on the head. The game model: only the same mantle's biggest, with
    four sides (they break its outline)."""
    rng = random.Random(7)
    made = 0
    while made < 230:
        t = rng.uniform(0.07, 0.97)
        a = rng.uniform(-0.4, math.pi + 0.4)
        # (fewer where the sack narrows to its end)
        if rng.random() > min(mantle_radius(t) / 0.15, 1.0):
            continue
        big = rng.random() ** 2.5
        # (low, soft flaps of skin, a few of them taller: not spines)
        if q == "full":
            papilla(m, mantle_point(t, a), mantle_normal(t, a), 0.006 + 0.007 * big, 0.004 + 0.011 * big, t, 0.0)
        elif big > 0.6:
            papilla(m, mantle_point(t, a), mantle_normal(t, a), 0.006 + 0.007 * big, 0.004 + 0.011 * big, t, 0.0, sides=4)
        made += 1
    if q != "full":
        return
    for i in range(26):
        z = rng.uniform(-0.04, 0.13)
        a = rng.uniform(0.35, math.pi - 0.35)
        p, n = head_point(z, a)
        papilla(m, p, n, 0.006, 0.006 + 0.009 * rng.random(), 0.0, 0.4)


# (z, radius across, radius up and down): the neck inside the mantle, the head, the crown the arms leave
HEAD = [(-0.17, 0.075, 0.075), (-0.1, 0.105, 0.1), (-0.04, 0.12, 0.112), (0.02, 0.128, 0.116), (0.08, 0.134, 0.12),
        (0.13, 0.136, 0.124), (0.165, 0.118, 0.11), (0.185, 0.07, 0.066), (0.193, 0.02, 0.02)]


def head_point(z, a):
    """A point of the head's skin, and the way it looks."""
    for (z0, x0, y0), (z1, x1, y1) in zip(HEAD, HEAD[1:]):
        if z <= z1:
            f = (z - z0) / (z1 - z0)
            rx, ry = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
            n = Vector((math.cos(a) / rx, math.sin(a) / ry, 0.0)).normalized()
            return Vector((math.cos(a) * rx, math.sin(a) * ry, z)), n
    return Vector((0.0, 0.0, z)), Vector((0.0, 1.0, 0.0))


def eye_at(side):
    """An eye: its middle, and the way it looks (out and up)."""
    return Vector((side * 0.074, 0.092, 0.0)), Vector((side * 0.75, 0.66, 0.0)).normalized()


def head(m, q):
    around = pick(q, 28, 16, 10)
    colour = (0.4, 0.0, 0.0, 1.0)
    rings = []
    for i, (z, rx, ry) in enumerate(HEAD):
        rings.append([m.add(Vector((math.cos(c / around * TAU) * rx, math.sin(c / around * TAU) * ry, z)), (c / around, i / (len(HEAD) - 1)), (0.0, 0.0), colour) for c in range(around)])
    for a, b in zip(rings, rings[1:]):
        middle = Vector((0.0, 0.0, (m.verts[a[0]].z + m.verts[b[0]].z) * 0.5 - 0.02))
        for c in range(around):
            d = (c + 1) % around
            m.face((a[c], a[d], b[d], b[c]), "head", middle)
    # The turrets the eyes sit in, and a horn of skin over each eye.
    n = pick(q, 14, 10, 7)
    rows = pick(q, 9, 5, 4)
    for side in (1.0, -1.0):
        centre, out = eye_at(side)
        centre = centre - out * 0.03
        rings = []
        for r in range(1, rows):
            polar = r / rows * math.pi
            rings.append([m.add(centre + Vector((math.sin(polar) * math.cos(c / n * TAU) * 0.058, math.cos(polar) * 0.058, math.sin(polar) * math.sin(c / n * TAU) * 0.07)), (0.0, 0.3), (0.0, 0.0), colour) for c in range(n)])
        top = m.add(centre + Vector((0.0, 0.058, 0.0)), (0.0, 0.3), (0.0, 0.0), colour)
        bottom = m.add(centre - Vector((0.0, 0.058, 0.0)), (0.0, 0.3), (0.0, 0.0), colour)
        for a, b in zip(rings, rings[1:]):
            for c in range(n):
                d = (c + 1) % n
                m.face((a[c], a[d], b[d], b[c]), "turrets", centre)
        for c in range(n):
            d = (c + 1) % n
            m.face((rings[0][d], rings[0][c], top), "turrets", centre)
            m.face((rings[-1][c], rings[-1][d], bottom), "turrets", centre)
        if q != "low":
            for lean, wide, high in ((Vector((side * 0.25, 1.0, -0.3)), 0.011, 0.034), (Vector((side * 0.1, 1.0, 0.45)), 0.008, 0.018), (Vector((side * 0.9, 0.5, -0.55)), 0.007, 0.014)):
                lean = lean.normalized()
                papilla(m, centre + Vector((lean.x * 0.058, lean.y * 0.058, lean.z * 0.07)), lean, wide, high, 0.0, 0.4, "horns", pick(q, 5, 4, 5))
    # The siphon: a tapered tube out from under the mantle's collar on its +X side, its mouth open towards the arms.
    n = pick(q, 14, 10, 7)
    rings = []
    for x, y, z, r in ((0.045, -0.07, -0.13, 0.05), (0.065, -0.105, -0.04, 0.046), (0.082, -0.128, 0.03, 0.036), (0.094, -0.14, 0.085, 0.028),
                       (0.094, -0.14, 0.087, 0.02), (0.088, -0.134, 0.04, 0.017)):
        rings.append([m.add(Vector((x + math.cos(c / n * TAU) * r, y + math.sin(c / n * TAU) * r * 0.85, z)), (c / n, 0.5), (0.0, 0.0), colour) for c in range(n)])
    for i, (a, b) in enumerate(zip(rings, rings[1:])):
        middle = (sum((m.verts[j] for j in a), Vector()) + sum((m.verts[j] for j in b), Vector())) / (2 * n)
        for c in range(n):
            d = (c + 1) % n
            # (the last rings turn back inside its mouth: its lip looks towards the arms, its inside inwards)
            away = middle if i < 3 else (middle - Vector((0.0, 0.0, 1.0)) if i == 3 else Vector((m.verts[a[c]].x * 3.0 - middle.x * 2.0, m.verts[a[c]].y * 3.0 - middle.y * 2.0, middle.z)))
            m.face((a[c], a[d], b[d], b[c]), "siphon", away)
    # The mouth: a pale disc in the middle of the ring of arms.
    n = pick(q, 16, 10, 8)
    mouth = (0.4, 1.0, 0.0, 1.0)
    rings = []
    for out, z in ((1.0, 0.0), (0.9, 0.016), (0.6, 0.026), (0.3, 0.03)):
        rings.append([m.add(Vector((math.cos(c / n * TAU) * 0.06 * out, math.sin(c / n * TAU) * 0.06 * out, ARM_Z + 0.045 + z)), (out, 0.5), (0.0, 0.0), mouth) for c in range(n)])
    tip = m.add(Vector((0.0, 0.0, ARM_Z + 0.045 + 0.032)), (0.0, 0.5), (0.0, 0.0), mouth)
    inside = Vector((0.0, 0.0, ARM_Z - 0.05))
    for a, b in zip(rings, rings[1:]):
        for c in range(n):
            d = (c + 1) % n
            m.face((a[c], a[d], b[d], b[c]), "mouth", inside)
    last = rings[-1]
    for c in range(n):
        m.face((last[c], last[(c + 1) % n], tip), "mouth", inside)


def eyes(m, q):
    around = pick(q, 20, 16, 8)
    rings_n = pick(q, 10, 5, 4)
    for side in (1.0, -1.0):
        centre, out = eye_at(side)
        along = Vector((0.0, 0.0, 1.0))
        up = along.cross(out)
        if up.y < 0.0:
            up = -up
        colour = (0.6, 0.0 if side > 0.0 else 1.0, 0.0, 1.0)
        rings = []
        for r in range(rings_n + 1):
            # from the pole that looks out, round to inside the turret; across its face 1 is 0.3 of a half turn
            polar = r / rings_n * math.pi * 0.45
            far = polar / (math.pi * 0.3)
            ring = []
            for c in range(around):
                a = c / around * TAU
                p = centre + (out * math.cos(polar) + (along * math.cos(a) + up * math.sin(a)) * math.sin(polar)) * 0.036
                ring.append(m.add(p, (0.5 + 0.5 * far * math.cos(a), 0.5 + 0.5 * far * math.sin(a)), (0.0, 0.0), colour))
            rings.append(ring)
        for a, b in zip(rings, rings[1:]):
            for c in range(around):
                d = (c + 1) % around
                m.face((a[c], a[d], b[d], b[c]) if side > 0.0 else (b[c], b[d], a[d], a[c]), "eyes", centre)


def arm_radius(s):
    return 0.05 * (1.0 - s) ** 0.85 + 0.0035


def arm_point(k, s, around_at, extra=0.0):
    """A point on arm k's skin at rest: `s` along it, `around_at` round it (0 its outer face, 0.5 its inner, suckered
    face), `extra` further out from its skin."""
    root, long, _phase, out = strand(k)
    side = Vector((-out.y, out.x, 0.0))
    r = arm_radius(s)
    a = around_at * TAU
    # (a round back, a flatter inner face)
    flat = 0.7 if math.cos(a) < 0.0 else 1.0
    return root + Vector((0.0, 0.0, s * long)) + (out * math.cos(a) * flat + side * math.sin(a)) * (r + extra)


def arm_skin(m, k, q):
    root, long, phase, _out = strand(k)
    steps = pick(q, 64, 14, 22)
    around = pick(q, 16, 8, 7)
    # (green 1: the game model, whose suckers the shader paints on the inner face)
    colour = (0.8, 1.0 if q == "game" else 0.0, (k + 0.5) / 16.0, 1.0)
    rings = []
    # (it starts inside the head: these rings are all at s = 0)
    for back, thin in ((0.1, 0.55), (0.05, 0.9)):
        rings.append([m.add(arm_point(k, 0.0, c / around, arm_radius(0.0) * (thin - 1.0)) - Vector((0.0, 0.0, back)), (c / around, 0.0), (long, phase), colour) for c in range(around + 1)])
    for i in range(steps + 1):
        # (more rings towards the tip, where it curls tightest)
        s = 1.0 - (1.0 - i / steps) ** (1.7 if q == "game" else 1.25)
        # (the game model's eight-sided arm built a little fatter, to cover the round one's outline and its suckers)
        fat = arm_radius(s) * 0.07 if q == "game" else 0.0
        rings.append([m.add(arm_point(k, s, c / around, fat), (c / around, s), (long, phase), colour) for c in range(around + 1)])
    for a, b in zip(rings, rings[1:]):
        middle = (sum((m.verts[i] for i in a[:around]), Vector()) + sum((m.verts[i] for i in b[:around]), Vector())) / (2 * around)
        for c in range(around):
            d = c + 1
            m.face((a[c], a[d], b[d], b[c]), "arms", middle)
    tip = m.add(root + Vector((0.0, 0.0, long + 0.004)), (0.5, 1.0), (long, phase), colour)
    last = rings[-1]
    for c in range(around):
        m.face((last[c], last[c + 1], tip), "arms", m.verts[tip] - Vector((0.0, 0.0, 0.1)))


def sucker(m, k, s, around_at, size):
    """A sucker on arm k's inner face: a short foot, a rim, a shallow cup."""
    _root, long, phase, _out = strand(k)
    on = arm_point(k, s, around_at)
    up = (arm_point(k, s, around_at, 1.0) - on).normalized()
    along = Vector((0.0, 0.0, 1.0))
    across = up.cross(along).normalized()
    colour = (1.0, 0.0, (k + 0.5) / 16.0, 1.0)
    sides = 6
    rings = []
    # (how far out from the skin, how wide, how far round the sucker's own profile)
    for high, wide, v in ((-0.3, 0.72, 0.0), (0.55, 1.0, 0.45), (0.5, 0.58, 0.7)):
        rings.append([m.add(on + up * high * size + (along * math.cos(c / sides * TAU) + across * math.sin(c / sides * TAU)) * wide * size,
                            (v, s), (long, phase), colour) for c in range(sides)])
    centre = m.add(on + up * 0.2 * size, (1.0, s), (long, phase), colour)
    inside = on - up * size
    for i, (a, b) in enumerate(zip(rings, rings[1:])):
        for c in range(sides):
            d = (c + 1) % sides
            # (its outside looks away from its own middle line; its rim and cup look out of it)
            m.face((a[c], a[d], b[d], b[c]), "suckers", on + up * 0.1 * size if i == 0 else inside)
    last = rings[-1]
    for c in range(sides):
        m.face((last[c], last[(c + 1) % sides], centre), "suckers", inside)


def suckers(m):
    pairs = 52
    for k in range(ARMS):
        for i in range(pairs):
            for row in (0, 1):
                # (set closer together as they get smaller)
                x = (i + 0.25 + 0.5 * row) / pairs
                s = 0.015 + 0.97 * (1.0 - (1.0 - x) ** 2)
                sucker(m, k, s, 0.5 + (0.085 if row else -0.085), max(0.4 * arm_radius(s), 0.0022))


def web_reach(w):
    """How far down the arms the web goes, `w` across it from one arm (0) to the next (1): furthest along the arms,
    cut back in a curve between them."""
    return WEB * (1.0 - 0.3 * math.sin(math.pi * w))


def web(m, q):
    across_n = pick(q, 6, 3, 2)
    along_n = pick(q, 8, 3, 3)
    for k in range(ARMS):
        root_a, long_a, phase, _out = strand(k)
        root_b, long_b, _phase, _out = strand((k + 1) % ARMS)
        for sheet in (0.0, 1.0):
            rows = []
            for j in range(along_n + 1):
                row = []
                for i in range(across_n + 1):
                    w = i / across_n
                    s = web_reach(w) * j / along_n
                    p = (root_a + Vector((0.0, 0.0, s * long_a))).lerp(root_b + Vector((0.0, 0.0, s * long_b)), w)
                    row.append(m.add(p, (w, s), (long_a, phase), (0.2, sheet, (k + 0.5) / 16.0, 1.0)))
                rows.append(row)
            for j in range(along_n):
                for i in range(across_n):
                    quad = (rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i])
                    middle = sum((m.verts[v] for v in quad), Vector()) / 4.0
                    axis = Vector((0.0, 0.0, middle.z))
                    if sheet > 0.5:
                        # (the inner sheet looks in, towards the middle line: away from a point further out)
                        m.face(quad[::-1], "web", axis + (middle - axis) * 3.0)
                    else:
                        m.face(quad, "web", axis)


def make(name, q):
    """The model `q`: "full", "game" or "low"."""
    m = Mesh()
    mantle(m, q)
    head(m, q)
    eyes(m, q)
    for k in range(ARMS):
        arm_skin(m, k, q)
    web(m, q)
    if q != "low":
        papillae(m, q)
    if q == "full":
        suckers(m)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) for p in m.verts], [], m.faces)
    # (every layer made first, then each looked up by name: making one moves the others)
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
            colour[poly.loop_start + corner].color = d[2]
    mesh.color_attributes.active_color = mesh.color_attributes["Color"]
    mesh.color_attributes.render_color_index = mesh.color_attributes.find("Color")
    material = bpy.data.materials.get("octopus_skin") or bpy.data.materials.new("octopus_skin")
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.5, 0.14, 0.08, 1.0)
    material.diffuse_color = (0.5, 0.14, 0.08, 1.0)
    mesh.materials.append(material)
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    print("BUILT %s verts=%d tris=%d" % (name, len(mesh.vertices), tris))
    wrong = sum(t[0] for t in m.wound.values())
    print("WINDING %s: %s: %s" % (name, "ok" if wrong == 0 else "INSIDE OUT",
                                  ", ".join("%s %d/%d wrong" % (kind, t[0], t[1]) for kind, t in m.wound.items())))
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
    scene.render.resolution_x, scene.render.resolution_y = 1600, 800
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    # (Blender: it lies along Y, its mantle towards +Y, its back +Z)
    body = (0.0, -0.6, 0.0)
    views = [("side", (1, 0, 0), body, 2.6), ("other_side", (-1, 0, 0), body, 2.6), ("above", (0, 0.001, 1), body, 2.6),
             ("below", (0, 0.001, -1), body, 2.6), ("front", (0, 1, 0.0), (0, 0, 0), 0.9), ("back", (0, -1, 0.0), (0, 0, 0), 0.9),
             ("head", (0.7, 0.35, 0.4), (0, 0.15, 0), 1.1), ("head_other", (-0.6, -0.5, 0.5), (0, 0.1, 0), 1.1),
             ("under", (0.5, -0.3, -0.7), (0, -0.1, 0), 1.0)]
    for low, obj in ((False, made[0]), (True, made[1]), ("game", made[2])):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if low and view not in ("side", "above", "head"):
                continue
            offset = Vector(direction).normalized() * 60.0
            camera.data.ortho_scale = frame
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "X" if view in ("above", "below") else "Y").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % (("game_" if low == "game" else "lo_" if low else "", view)))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    full = make(NAME, "full")
    low = make(NAME + "_lo", "low")
    game = make(NAME + "_game", "game")
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, NAME + ".glb"))
    export_one(low, os.path.join(OUT, NAME + "_lo.glb"))
    export_one(game, os.path.join(OUT, NAME + "_game.glb"))
    low.location.x = 1.5
    game.location.x = -1.5
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, NAME + ".blend"))
    low.location.x = 0.0
    game.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low, game])


if __name__ == "__main__":
    main()
