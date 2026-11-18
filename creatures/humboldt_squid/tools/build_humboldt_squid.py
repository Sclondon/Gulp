"""Builds the Humboldt squid (creatures/humboldt_squid) and exports it for Godot.

Run from the game's root:
    blender --background --factory-startup --python creatures/humboldt_squid/tools/build_humboldt_squid.py
    blender --background --factory-startup --python creatures/humboldt_squid/tools/build_humboldt_squid.py -- <folder for pictures>

Writes creatures/humboldt_squid/models/humboldt_squid.glb (the full model), humboldt_squid_lo.glb (far off: no
sucker cups, fewer rings) and humboldt_squid_game.glb (the game model, at Twilight Princess weight: rings placed for
the outline, the flanges and the clubs, its cups painted by the shader: UV2.y is 2 more than the phase on its
strands), and the editable creatures/humboldt_squid/tools/humboldt_squid.blend (this folder has a
.gdignore). Each is one static mesh: the shader (humboldt_squid.gdshaderinc) pulses the mantle, flaps the fins, lays
every arm and tentacle along its rope, and draws the skin and its changing colour. It prints a WINDING line: the
check that nothing is inside out.

A Humboldt or jumbo squid (Dosidicus gigas, "diablo rojo") with a mantle 1.2 m long, about 2.5 m with its
tentacles, after the species accounts and the photographs the component's README names. Against the giant squid
(godot/giant-squid, which this is built on) it is far stockier:

- THE MANTLE: a stout muscular barrel, about a quarter as wide as it is long, nearly a cylinder for its front
  half, then tapering to a point; its collar a free edge with a lip, the head's neck inside it.
- THE FINS: two big triangular fins that together are a rhomboid (a diamond) across the mantle's back end: 45% of
  the mantle long and three quarters of it across, with straight edges and blunt side corners; thick.
- THE HEAD: as wide as the mantle, short, an eye on each side, the siphon under it.
- THE ARMS: eight, thick, 0.64 to 0.8 m (about two thirds of the mantle), three-sided, with a flange (the
  protective membrane) along each edge of the inner face and two rows of ringed sucker cups down it. In the
  middle of their ring, the pale bulb of the mouth with the dark tip of the beak.
- THE TENTACLES: two, only a little longer than the arms (1.0 m), their last two fifths a broad club with four
  rows of cups, the middle two rows big.

Godot space until it is written out (metres, Y up): the squid swims mantle first, towards -Z; its arms trail
towards +Z; its back is +Y, the siphon under it. The origin is the middle of the head, between the eyes.

In the model every arm and tentacle lies straight along +Z from its root. HumboldtSquid simulates each as a rope
and the shader lays it along that rope: the roots and lengths here are worked out the same way in
creatures/humboldt_squid/humboldt_squid.gd (`strands()`) and the roots again in the shader: change one, change the
others.

What a point is, for the shader: vertex colour red the part (0 the mantle, 0.2 a fin, 0.4 the head and siphon,
0.6 an eye, 0.8 the skin of an arm or tentacle, 1 a sucker cup); green 1 on a tentacle, and on the head 1 for the
bulb of the mouth; blue, on a strand, which one ((n + 0.5) / 16: arms 0 to 7, tentacles 8 and 9). UV.x round it
(on a fin: from where it joins the mantle, 0, to its edge, 1; on an eye or the mouth: from its middle, 0, outwards
to 1; on a strand: 0.5 down the middle of its inner, suckered face), UV.y along it (the mantle: collar 0 to tip 1;
a fin: front 0 to back 1; a strand: root 0 to tip 1). UV2.x a strand's length (metres), UV2.y its phase (0..1).
(The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.)

Two surfaces: "squid_body" (solid) and "squid_fins" (seen from both sides, drawn after it).
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


def pick(q, full, game, low):
    """A number for the model `q` being built: the full one, the game one or the low one."""
    return {"full": full, "game": game, "low": low}[q]


# Kept in step with humboldt_squid.gd and the shader.
MANTLE_FROM = -0.1
MANTLE_LONG = 1.2
FIN_FROM = 0.55
ARMS = 8
ARM_RING = 0.088
ARM_Z = 0.17
ARM_LONG = 0.72
TENTACLES = 2
TENTACLE_LONG = 1.0
CLUB_FROM = 0.6
BODY, FINS = 0, 1
SURFACES = ["squid_body", "squid_fins"]


def to_b(p):
    return Vector((p.x, -p.z, p.y))


def fract(x):
    return x - math.floor(x)


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def strand(k):
    """Strand k: its root, its length, its phase, the way out from the middle it lies (a unit, x and y)."""
    if k < ARMS:
        a = (k + 0.5) * TAU / ARMS
        out = Vector((math.cos(a), math.sin(a), 0.0))
        return out * ARM_RING + Vector((0.0, 0.0, ARM_Z)), ARM_LONG - 0.08 * math.sin(a), fract(k * 0.37 + 0.11), out
    side = 1.0 if k == ARMS else -1.0
    return Vector((side * 0.032, -0.02, ARM_Z + 0.015)), TENTACLE_LONG * (1.0 if side > 0.0 else 0.96), fract(k * 0.37 + 0.11), Vector((side, 0.0, 0.0))


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.surface = []
        self.data = []
        # faces wound against the way they should look: [wrong, all] for each kind of part
        self.wound = {}

    def add(self, p, uv, uv2, colour):
        self.verts.append(p)
        self.data.append((uv, uv2, colour))
        return len(self.verts) - 1

    def face(self, points, surface, kind, away):
        """A face; `away` is a point it should look away from (None: any way will do)."""
        self.faces.append(tuple(points))
        self.surface.append(surface)
        tally = self.wound.setdefault(kind, [0, 0])
        if away is not None:
            ps = [self.verts[i] for i in points]
            normal = Vector()
            for i in range(len(ps)):
                normal += ps[i].cross(ps[(i + 1) % len(ps)])
            if normal.length > 1e-12:
                tally[1] += 1
                middle = sum(ps, Vector()) / len(ps)
                if normal.dot(middle - away) <= 0.0:
                    tally[0] += 1


def mantle_radius(t):
    """How thick the mantle is, `t` from its collar (0) to its tip (1): a barrel, then a cone."""
    if t < 0.45:
        return 0.16 + 0.014 * smooth(0.0, 0.3, t)
    return max(0.174 * (1.0 - ((t - 0.45) / 0.55) ** 1.7) ** 0.85, 0.006)


def mantle_point(t, a, r_scale=1.0):
    r = mantle_radius(t) * r_scale
    # (a little flattened under it, and the collar's edge cut back under the head, where the siphon is)
    y = math.sin(a) * r * (0.95 if math.sin(a) < 0.0 else 1.0)
    z = MANTLE_FROM - t * MANTLE_LONG + 0.03 * (1.0 - smooth(0.0, 0.12, t)) * max(math.sin(a), -0.2) * (1.0 - t)
    return Vector((math.cos(a) * r, y, z))


def mantle(m, q):
    around = pick(q, 44, 22, 20)
    rings_n = pick(q, 46, 14, 18)
    colour = (0.0, 0.0, 0.0, 1.0)
    rings = []
    # (the lip of the collar: turned in, so that the edge has a thickness)
    for inset, deep in ((0.03, 0.07), (0.026, 0.0)):
        rings.append([m.add(mantle_point(0.0, c / around * TAU, 1.0 - inset / 0.16) + Vector((0.0, 0.0, -deep)), (c / around, 1.0), (0.0, 1.0), colour) for c in range(around)])
    for r in range(rings_n + 1):
        t = (r / rings_n) ** 1.1
        rings.append([m.add(mantle_point(t, c / around * TAU), (c / around, 1.0 - t), (0.0, 1.0), colour) for c in range(around)])
    for a, b in zip(rings[2:], rings[3:]):
        middle = (sum((m.verts[i] for i in a), Vector()) + sum((m.verts[i] for i in b), Vector())) / (2 * around)
        for c in range(around):
            d = (c + 1) % around
            m.face((a[c], b[c], b[d], a[d]), BODY, "mantle", middle)
    # the lip: its inside looks in towards the head, its edge forwards
    a, b = rings[0], rings[1]
    for c in range(around):
        d = (c + 1) % around
        m.face((a[c], b[c], b[d], a[d]), BODY, "lip", (m.verts[a[c]] + m.verts[b[d]]) * 0.5 * 3.0 - Vector((0.0, 0.0, 2.0 * (m.verts[a[c]].z + m.verts[b[d]].z) * 0.5)))
    a, b = rings[1], rings[2]
    for c in range(around):
        d = (c + 1) % around
        m.face((a[c], b[c], b[d], a[d]), BODY, "lip", (m.verts[a[c]] + m.verts[b[d]]) * 0.5 - Vector((0.0, 0.0, 1.0)))


def fin_wide(u):
    """How far a fin reaches out from the mantle, `u` from its front (0) to the mantle's tip (1): the two together
    a rhomboid, their side corners two fifths of the way back and a little blunt."""
    return 0.4 * min(u / 0.42, (1.0 - u) / 0.58, 0.94) ** 0.92


def fins(m, q):
    along_n = pick(q, 26, 12, 10)
    across_n = pick(q, 8, 3, 3)
    for side in (1.0, -1.0):
        rows = []
        for i in range(along_n + 1):
            u = i / along_n
            # joined along the mantle's upper side over its back 45%
            t = FIN_FROM + (1.0 - FIN_FROM) * u
            a = math.radians(18.0)
            root = mantle_point(t, a if side > 0.0 else math.pi - a, 0.9)
            wide = fin_wide(u)
            row = []
            for j in range(across_n + 1):
                w = j / across_n
                # (out sideways, drooping a little towards its edge)
                p = root + Vector((side * wide * w, -0.03 * w * w, 0.0))
                row.append(m.add(p, (w, 1.0 - u), (0.0, 1.0), (0.2, 0.0, 0.0, 1.0)))
            rows.append(row)
        for i in range(along_n):
            for j in range(across_n):
                quad = (rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j])
                if side < 0.0:
                    quad = quad[::-1]
                # (a sheet seen from both sides; wound so that its front is its upper side)
                m.face(quad, FINS, "fins", m.verts[rows[i][j]] + Vector((0.0, -10.0, 0.0)))


def head(m, q):
    around = pick(q, 28, 14, 14)
    colour = (0.4, 0.0, 0.0, 1.0)
    # (z, radius across, radius up and down): the neck inside the mantle, the swell at the eyes, the crown the arms leave
    shape = [(-0.24, 0.1, 0.1), (-0.15, 0.135, 0.13), (-0.07, 0.155, 0.145), (0.0, 0.16, 0.148), (0.07, 0.156, 0.145),
             (0.13, 0.148, 0.14), (0.175, 0.138, 0.134), (0.205, 0.105, 0.105), (0.222, 0.05, 0.05), (0.226, 0.012, 0.012)]
    rings = []
    for i, (z, rx, ry) in enumerate(shape):
        rings.append([m.add(Vector((math.cos(c / around * TAU) * rx, math.sin(c / around * TAU) * ry, z)), (c / around, i / (len(shape) - 1)), (0.0, 1.0), colour) for c in range(around)])
    for a, b in zip(rings, rings[1:]):
        middle = Vector((0.0, 0.0, (m.verts[a[0]].z + m.verts[b[0]].z) * 0.5))
        for c in range(around):
            d = (c + 1) % around
            m.face((a[c], a[d], b[d], b[c]), BODY, "head", middle)
    # The siphon: a tapered tube under the head, from inside the mantle forward, its mouth open.
    n = pick(q, 14, 8, 8)
    rings = []
    for z, r, y in ((-0.3, 0.07, -0.085), (-0.18, 0.07, -0.115), (-0.07, 0.06, -0.14), (0.02, 0.046, -0.152), (0.075, 0.038, -0.157), (0.075, 0.028, -0.157), (0.01, 0.025, -0.152)):
        rings.append([m.add(Vector((math.cos(c / n * TAU) * r, y + math.sin(c / n * TAU) * r * 0.8, z)), (c / n, 0.5), (0.0, 1.0), colour) for c in range(n)])
    for i, (a, b) in enumerate(zip(rings, rings[1:])):
        middle = (sum((m.verts[j] for j in a), Vector()) + sum((m.verts[j] for j in b), Vector())) / (2 * n)
        for c in range(n):
            d = (c + 1) % n
            # (the last rings turn back inside its mouth: any way will do there)
            m.face((a[c], a[d], b[d], b[c]), BODY, "siphon", middle if i < 4 else None)
    # The mouth: a pale bulb in the middle of the ring of arms, the dark tip of the beak in the middle of it.
    n = pick(q, 16, 10, 8)
    mouth = (0.4, 1.0, 0.0, 1.0)
    rings = []
    for out, z in ((1.0, 0.0), (0.92, 0.022), (0.7, 0.04), (0.42, 0.05), (0.2, 0.058)):
        rings.append([m.add(Vector((math.cos(c / n * TAU) * 0.052 * out, math.sin(c / n * TAU) * 0.052 * out, ARM_Z + 0.05 + z)), (out, 0.5), (0.0, 1.0), mouth) for c in range(n)])
    tip = m.add(Vector((0.0, 0.0, ARM_Z + 0.05 + 0.066)), (0.0, 0.5), (0.0, 1.0), mouth)
    inside = Vector((0.0, 0.0, ARM_Z))
    for a, b in zip(rings, rings[1:]):
        for c in range(n):
            d = (c + 1) % n
            m.face((a[c], a[d], b[d], b[c]), BODY, "mouth", inside)
    last = rings[-1]
    for c in range(n):
        m.face((last[c], last[(c + 1) % n], tip), BODY, "mouth", inside)


def eyes(m, q):
    around = pick(q, 20, 16, 10)
    rings_n = pick(q, 12, 5, 6)
    for side in (1.0, -1.0):
        centre = Vector((side * 0.112, 0.012, -0.005))
        rings = []
        for r in range(rings_n + 1):
            # from the pole that looks out sideways round to the back, inside the head
            polar = r / rings_n * math.pi * 0.72
            ring = []
            for c in range(around):
                a = c / around * TAU * side
                p = centre + Vector((side * math.cos(polar) * 0.056, math.sin(polar) * math.sin(a) * 0.082, math.sin(polar) * math.cos(a) * 0.082))
                ring.append(m.add(p, (polar / math.pi, 0.5), (0.0, 1.0), (0.6, 0.0, 0.0, 1.0)))
            rings.append(ring)
        for a, b in zip(rings, rings[1:]):
            for c in range(around):
                d = (c + 1) % around
                m.face((a[c], a[d], b[d], b[c]), BODY, "eyes", centre)


def strand_radius(k, s):
    if k < ARMS:
        return 0.043 * (1.0 - s) ** 0.75 + 0.004
    # a tentacle: a stalk, then the broad club
    club = smooth(CLUB_FROM, CLUB_FROM + 0.12, s) * (1.0 - smooth(0.84, 1.0, s))
    return 0.017 - 0.004 * s + 0.021 * club - 0.009 * smooth(0.93, 1.0, s)


def strand_point(k, s, around_at, extra=0.0):
    """A point on strand k's skin at rest: `s` along it, `around_at` round it (0 its outer face, 0.5 its inner, suckered
    face), `extra` further out from its skin."""
    root, long, _phase, out = strand(k)
    side = Vector((-out.y, out.x, 0.0))
    r = strand_radius(k, s)
    a = around_at * TAU
    if k >= ARMS:
        # (the club is flat: wide across, thin through)
        flat = 0.55 + 0.45 * (1.0 - smooth(CLUB_FROM, CLUB_FROM + 0.12, s))
        inner = Vector((0.0, 1.0, 0.0))
        side = Vector((1.0, 0.0, 0.0))
        return root + Vector((0.0, 0.0, s * long)) + (side * math.sin(a) + inner * -math.cos(a) * flat) * (r + extra)
    # An arm is three-sided: a rounded back, a flat inner face, and along each edge of that face a flange (the
    # protective membrane), which thins away towards the arm's tip.
    flat = 0.66 if math.cos(a) < 0.0 else 1.0
    from_edge = min(abs(around_at - 0.3), abs(around_at - 0.7))
    flange = 1.0 + 0.5 * math.exp(-(from_edge / 0.045) ** 2) * (1.0 - 0.6 * s)
    return root + Vector((0.0, 0.0, s * long)) + (out * math.cos(a) * flat + side * math.sin(a)) * (r * flange + extra)


def game_fat(k, s, at):
    """How much fatter the game model's strands are built, to cover the full model's outline: an arm a little all
    round (it has fewer sides); a club on its inner face, by the height of the cups it has no more."""
    if k < ARMS:
        return strand_radius(k, s) * 0.04
    club = smooth(CLUB_FROM, CLUB_FROM + 0.12, s) * (1.0 - smooth(0.84, 1.0, s))
    return 0.007 * club * max(-math.cos(at * TAU), 0.0)


def strand_skin(m, k, q):
    root, long, phase, _out = strand(k)
    tentacle = k >= ARMS
    colour = (0.8, 1.0 if tentacle else 0.0, (k + 0.5) / 16.0, 1.0)
    if q == "game":
        # The game model: its points round an arm bunched at the flanges (0.3 and 0.7 round), which are its
        # outline from the front; a tentacle's rings bunched in its club. UV2.y is 2 more than its phase: the
        # shader paints the sucker cups where the full model has them.
        ats = [0.0, 0.14, 0.26, 0.3, 0.37, 0.5, 0.63, 0.7, 0.74, 0.86, 1.0] if not tentacle else [c / 8 for c in range(9)]
        ss = [i / 10 for i in range(11)] if not tentacle else [0.0, 0.15, 0.3, 0.45, 0.56, 0.62, 0.67, 0.72, 0.77, 0.82, 0.86, 0.9, 0.94, 0.97, 1.0]
        phase += 2.0
    else:
        steps = (22 if tentacle else 16) if q == "low" else (60 if tentacle else 44)
        around = 8 if q == "low" else 20
        ats = [c / around for c in range(around + 1)]
        ss = [i / steps for i in range(steps + 1)]
    around = len(ats) - 1
    rings = []
    # (it starts inside the head: these rings are all at s = 0, so they stay with it)
    for back, thin in ((0.1, 0.55), (0.05, 0.9)):
        rings.append([m.add(strand_point(k, 0.0, at, strand_radius(k, 0.0) * (thin - 1.0)) - Vector((0.0, 0.0, back)), (at, 1.0), (long, 1.0 - phase), colour) for at in ats])
    for s in ss:
        rings.append([m.add(strand_point(k, s, at, game_fat(k, s, at) if q == "game" else 0.0), (at, 1.0 - s), (long, 1.0 - phase), colour) for at in ats])
    for a, b in zip(rings, rings[1:]):
        middle = (sum((m.verts[i] for i in a[:around]), Vector()) + sum((m.verts[i] for i in b[:around]), Vector())) / (2 * around)
        for c in range(around):
            d = c + 1
            m.face((a[c], a[d], b[d], b[c]), BODY, "strands", middle)
    tip = m.add(strand_point(k, 1.0, 0.0, -strand_radius(k, 1.0)) + Vector((0.0, 0.0, 0.006)), (0.5, 0.0), (long, 1.0 - phase), colour)
    last = rings[-1]
    for c in range(around):
        m.face((last[c], last[c + 1], tip), BODY, "strands", m.verts[tip] - Vector((0.0, 0.0, 0.1)))


def sucker(m, k, s, around_at, size):
    """A sucker cup on strand k's inner face: a short stalk, a rim, a hollow."""
    _root, long, phase, _out = strand(k)
    on = strand_point(k, s, around_at)
    up = (strand_point(k, s, around_at, 1.0) - on).normalized()
    along = Vector((0.0, 0.0, 1.0))
    across = up.cross(along).normalized()
    colour = (1.0, 1.0 if k >= ARMS else 0.0, (k + 0.5) / 16.0, 1.0)
    sides = 8
    rings = []
    # (how far out from the skin, how wide, how far round the cup's own profile)
    for high, wide, v in ((-0.25, 0.5, 0.0), (0.4, 0.6, 0.3), (0.7, 1.0, 0.6), (0.45, 0.62, 0.85)):
        rings.append([m.add(on + up * high * size + (along * math.cos(c / sides * TAU) + across * math.sin(c / sides * TAU)) * wide * size,
                            (v, 1.0 - s), (long, 1.0 - phase), colour) for c in range(sides)])
    centre = m.add(on + up * 0.2 * size, (1.0, 1.0 - s), (long, 1.0 - phase), colour)
    inside = on - up * size
    for i, (a, b) in enumerate(zip(rings, rings[1:])):
        for c in range(sides):
            d = (c + 1) % sides
            # (its outside looks away from its own middle line; its hollow looks out of the cup)
            if i < 2:
                m.face((a[c], a[d], b[d], b[c]), BODY, "suckers", on + up * 0.2 * size)
            else:
                m.face((a[c], a[d], b[d], b[c]), BODY, "suckers", inside)
    last = rings[-1]
    for c in range(sides):
        m.face((last[c], last[(c + 1) % sides], centre), BODY, "suckers", inside)


def suckers(m):
    for k in range(ARMS):
        pairs = 24
        for i in range(pairs):
            for row in (0, 1):
                s = 0.04 + 0.9 * ((i + 0.5 * row) / pairs) ** 0.9
                size = max(0.3 * strand_radius(k, s), 0.003)
                sucker(m, k, s, 0.5 + (0.07 if row else -0.07), size)
    for k in range(ARMS, ARMS + TENTACLES):
        # the club: four rows, the middle two the biggest
        count = 15
        for i in range(count):
            for row, (at, big) in enumerate(((0.33, 0.5), (0.445, 1.0), (0.555, 1.0), (0.67, 0.5))):
                s = CLUB_FROM + 0.05 + (0.33) * (i + 0.5 * (row % 2)) / count
                swell = math.sin(math.pi * (i + 0.5) / count) ** 0.6
                sucker(m, k, s, at, 0.0105 * big * (0.5 + 0.5 * swell))


def make(name, q):
    """The model `q`: "full", "game" or "low"."""
    m = Mesh()
    mantle(m, q)
    fins(m, q)
    head(m, q)
    eyes(m, q)
    for k in range(ARMS + TENTACLES):
        strand_skin(m, k, q)
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
    tints = {"squid_body": (0.55, 0.1, 0.08, 1.0), "squid_fins": (0.62, 0.2, 0.17, 1.0)}
    for surface in SURFACES:
        material = bpy.data.materials.get(surface) or bpy.data.materials.new(surface)
        material.use_nodes = True
        bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Base Color"].default_value = tints[surface]
        material.diffuse_color = tints[surface]
        mesh.materials.append(material)
    for poly in mesh.polygons:
        poly.use_smooth = True
        poly.material_index = m.surface[poly.index]
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
    # (Blender: the squid lies along Y, its mantle towards +Y, its back +Z)
    body = (0.0, 0.1, 0.0)
    views = [("side", (1, 0, 0), body, 2.9), ("other_side", (-1, 0, 0), body, 2.9), ("above", (0, 0.001, 1), body, 2.9),
             ("below", (0, 0.001, -1), body, 2.9), ("front", (0, 1, 0.0), (0, 0, 0), 1.3), ("back", (0, -1, 0.0), (0, 0, 0), 1.3),
             ("head", (0.7, -0.5, 0.35), (0, -0.1, 0), 0.9), ("crown", (0.25, -1.0, 0.2), (0, -0.2, 0), 0.5)]
    for low, obj in ((False, made[0]), (True, made[1]), ("game", made[2])):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if low and view not in ("side", "above"):
                continue
            offset = Vector(direction).normalized() * 60.0
            camera.data.ortho_scale = frame
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "X" if view in ("above", "below") else "Y").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % ("game_" if low == "game" else "lo_" if low else "", view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    full = make("humboldt_squid", "full")
    low = make("humboldt_squid_lo", "low")
    game = make("humboldt_squid_game", "game")
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, "humboldt_squid.glb"))
    export_one(low, os.path.join(OUT, "humboldt_squid_lo.glb"))
    export_one(game, os.path.join(OUT, "humboldt_squid_game.glb"))
    low.location.x = 1.5
    game.location.x = -1.5
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "humboldt_squid.blend"))
    low.location.x = 0.0
    game.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low, game])


if __name__ == "__main__":
    main()
