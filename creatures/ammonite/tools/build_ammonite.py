"""Builds the ammonite (creatures/ammonite) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/ammonite/tools/build_ammonite.py
    blender --background --python creatures/ammonite/tools/build_ammonite.py -- <preview folder>   # with pictures

Writes creatures/ammonite/models/ammonite.glb (the full model) and ammonite_lo.glb (far off, phones), and the
editable creatures/ammonite/tools/ammonite.blend (this folder has a .gdignore). Each is one still mesh with one
surface: the shader (ammonite.gdshader) draws every marking, rocks and bobs it, trails and curls its tentacles and
pulls its head into the shell (`withdraw`). It prints a WINDING line for each: the check that nothing is inside
out, and the numbers the shader must have (AS THE SHADER HAS IT).

An ammonite, 0.4 m across its shell, built from what fossil ammonites show and what is thought of their soft
parts (no picture was traced or copied):

- THE SHELL: a tube coiled tightly in one plane (planispiral), each whorl about 2.4 times as big as the one inside
  it and lapping over a quarter of it, so the inner whorls show in the middle (the umbilicus); its section a
  little taller than wide, with flat-ish sides; strong ribs across it, 26 to a turn, crossing its outer edge (the
  venter). The last part of the tube, the body chamber, is open at its end (the aperture), with a lip and a
  smooth inner wall back to the last septum.
- THE SOFT BODY, out of the aperture: a rounded head with a big eye on each side, a thick leathery hood over the
  top of the head (on the side towards the coil's middle), a short funnel under it (the jet), and ten short
  tentacles round the mouth, trailing back and down.

Everything here is in Godot space (metres, Y up, X to its left side) until it is written out. IT JETS SHELL FIRST:
its -Z is the way it goes, the shell's outer edge leading; the aperture, the head and the tentacles face +Z,
behind it. The coil lies in the YZ plane about an axis along X; the aperture is at the bottom of the coil, so it
hangs shell-up with its head low at the back. The origin is the middle of the shell's outline (half way across it
from front to back, and from top to bottom), on its middle plane.

What a point is, for the shader: UV2.y the part times 16 plus `index` (0 the shell, 1 the head and funnel, 2 an
eye, 3 the hood, 4 a tentacle, `index` which, 0 to 9); the colour's red, green and blue `root` (the place a part
turns about, in BOX: on a tentacle its root, on the hood its hinge, on the head the aperture.s middle, on an eye its own middle);
the colour's alpha `a` (along a tentacle 0 at its root to 1 at its tip; on the hood 0 at its hinge to 1 at its
front edge); UV.x, UV.y and UV2.x `k`: on the shell, k.x how far round the coil (radians, `phi`), k.y how far round
the section from the venter (0) to the inner side (1), the same on both flanks, k.z 0 the outside, 1 the inside wall and
the septum, 2 the lip; on a tentacle, its direction at rest. (The glTF writer flips V: what is written is 1 - v,
so that Godot reads v.)
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
X = Vector((1.0, 0.0, 0.0))

SHELL, HEAD, EYE, HOOD, TENTACLE = range(5)
# As the shader has it: the box the joints' places are written in.
BOX = (Vector((-0.3, -0.3, -0.3)), Vector((0.3, 0.3, 0.3)))

# The coil: how much bigger each whorl is than the one inside it; where the aperture is (phi, from the front of
# the coil round by the bottom); how far in the inner side of a whorl reaches (of the outer edge's radius);
# how wide the section is (of its height); the ribs (how many to a turn, how high).
W = 2.4
B = math.log(W) / TAU
PHI_END = math.pi * 0.5 - 0.15
TURNS = 3.5
INNER = 0.354
WIDE = 0.7
RIBS = 26
RIB_HIGH = 0.07
DIAMETER = 0.4


def to_b(p):
    """Godot's space (Y up, front at -Z) to Blender's (Z up, front at +Y)."""
    return Vector((p.x, -p.z, p.y))


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


class Mesh:
    """The model as it is being made: see the top of this file for what is written at each point."""

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
        self.verts.append(Vector(p))
        self.data.append([None if self.root is None else Vector(self.root), Vector(self.k if k is None else k),
                          self.a if a is None else a, self.part * 16 + self.index])
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

    def shift(self, by):
        for i in range(len(self.verts)):
            self.verts[i] += by
            if self.data[i][0] is not None:
                self.data[i][0] = self.data[i][0] + by


def loft(m, rings, name, cap0=None, cap1=None, out=None, tags=None):
    centres = [sum(r, Vector()) / len(r) for r in rings]
    rows = []
    for ri, ring in enumerate(rings):
        row = []
        for ci, p in enumerate(ring):
            k, a = tags(ri, ci) if tags else (None, None)
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
        k, a = tags(ri, -1) if tags else (None, None)
        tip = m.add(at, k, a)
        way = centre - other
        if cap is not True and (at - centre).length > 1e-12:
            way = way + (at - centre)
        for c in range(count):
            n = (c + 1) % count
            middle = (m.verts[tip] + m.verts[row[c]] + m.verts[row[n]]) / 3.0
            m.face((tip, row[c], row[n]), out(middle) if out else way, name)


def frames(path, ref):
    count = len(path)
    tangents = [(path[min(i + 1, count - 1)] - path[max(i - 1, 0)]).normalized() for i in range(count)]
    u = Vector(ref)
    made = []
    for t in tangents:
        u = (u - t * u.dot(t)).normalized()
        made.append((t, u, t.cross(u)))
    return made


def tube(m, path, radii, sides, name, ref, along=True):
    path = [Vector(p) for p in path]
    lengths = [0.0]
    for i in range(1, len(path)):
        lengths.append(lengths[-1] + (path[i] - path[i - 1]).length)
    made = frames(path, ref)
    rings = [[p + (u * math.cos(TAU * s / sides) + v * math.sin(TAU * s / sides)) * max(r, 1e-5) for s in range(sides)]
             for (t, u, v), p, r in zip(made, path, radii)]
    loft(m, rings, name, cap1=path[-1] + made[-1][0] * radii[-1] * 0.6,
         tags=(lambda ri, ci: (None, lengths[ri] / lengths[-1])) if along else None)


def ellipsoid(m, centre, axes, radii, name, lat, lon):
    """An ellipsoid: `axes` three unit axes, its poles on the first."""
    centre = Vector(centre)
    e0, e1, e2 = axes
    rings = []
    for i in range(1, lat):
        th = math.pi * i / lat
        rings.append([centre - e0 * (radii[0] * math.cos(th)) + e1 * (radii[1] * math.sin(th) * math.cos(TAU * j / lon))
                      + e2 * (radii[2] * math.sin(th) * math.sin(TAU * j / lon)) for j in range(lon)])
    loft(m, rings, name, cap0=centre - e0 * radii[0], cap1=centre + e0 * radii[0], out=lambda middle: middle - centre)


# --- the coil ---------------------------------------------------------------------------------------

def outer_radius(phi):
    """How far the venter (the tube's outer edge) is from the coil's axis at `phi` (before it is scaled)."""
    return math.exp(B * (phi - PHI_END))


def radial(phi):
    """Out from the coil's axis at `phi`: phi 0 is the front of the coil (-Z), a quarter turn its bottom."""
    return Vector((0.0, -math.sin(phi), -math.cos(phi)))


def section(phi):
    """(the middle of the tube's section, half its height across the coil, half its width)."""
    rv = outer_radius(phi)
    rd = rv * INNER
    middle = radial(phi) * ((rv + rd) * 0.5)
    half = (rv - rd) * 0.5
    return middle, half, half * WIDE


def rib(phi, psi):
    """How far a rib lifts the shell at `phi`, `psi` round the section (0 the venter): sharp crests, 26 to a turn,
    strongest across the venter and the outer flanks, fading towards the coil's middle and on the inner whorls."""
    crest = (0.5 + 0.5 * math.cos(RIBS * phi)) ** 4
    across = 0.35 + 0.65 * (0.5 + 0.5 * math.cos(psi))
    fade = smooth(PHI_END - TAU * 1.9, PHI_END - TAU * 1.2, phi)
    return RIB_HIGH * crest * across * fade


def round_of(c, around):
    """How far round the section a column is, for the shader: 0 the venter, 1 the inner side (the same on both
    flanks, so the seam needs no second points)."""
    return 0.5 - 0.5 * math.cos(TAU * c / around)


def shell_point(phi, psi, scale, ribbed=True):
    middle, half, wide = section(phi)
    c, s = math.cos(psi), math.sin(psi)
    e = 2.0 / 2.6
    lift = 1.0 + (rib(phi, psi) if ribbed else 0.0)
    p = middle + radial(phi) * (math.copysign(abs(c) ** e, c) * half * lift) + X * (math.copysign(abs(s) ** e, s) * wide * lift)
    return (p - middle) * scale + middle


def shell(m, low):
    around = 7 if low else 18
    per_turn = (24, 12, 5) if low else (104, 78, 26)
    phis = []
    phi = PHI_END - TAU * TURNS
    while phi < PHI_END - 1e-9:
        back = PHI_END - phi
        n = per_turn[0] if back <= TAU else (per_turn[1] if back <= TAU * 2 else per_turn[2])
        phis.append(phi)
        phi += TAU / n
    phis.append(PHI_END)
    m.part, m.index, m.root, m.a = SHELL, 0, None, 0.0
    rows = []
    for phi in phis:
        row = []
        for c in range(around):
            psi = c / around * TAU
            row.append(m.add(shell_point(phi, psi, 1.0, not low), Vector((phi, round_of(c, around), 0.0))))
        # (the seam along the venter shares its points, so that the shading does not crease there)
        row.append(row[0])
        rows.append(row)
    for r in range(len(rows) - 1):
        middle_line = section(0.5 * (phis[r] + phis[r + 1]))[0]
        for c in range(around):
            quad = (rows[r][c], rows[r][c + 1], rows[r + 1][c + 1], rows[r + 1][c])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, middle - middle_line, "shell")
    # the first, tiny end of the tube: closed
    centre, _, _ = section(phis[0])
    tip = m.add(centre, Vector((phis[0], 0.5, 0.0)))
    way = section(phis[0])[0] - section(phis[1])[0]
    for c in range(around):
        m.face((tip, rows[0][c], rows[0][c + 1]), way, "shell")
    # The body chamber's inner wall, smooth, from the aperture back to the last septum; the lip between the
    # two at the aperture; the septum.
    deep = 1.0
    thick = 0.92
    inner_phis = [PHI_END - deep * i / (4 if low else 16) for i in range((4 if low else 16) + 1)]
    inside = []
    for phi in inner_phis:
        row = [m.add(shell_point(phi, c / around * TAU, thick, False), Vector((phi, round_of(c, around), 1.0))) for c in range(around)]
        inside.append(row + [row[0]])
    for r in range(len(inside) - 1):
        middle_line = section(0.5 * (inner_phis[r] + inner_phis[r + 1]))[0]
        for c in range(around):
            quad = (inside[r][c], inside[r][c + 1], inside[r + 1][c + 1], inside[r + 1][c])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, middle_line - middle, "inner wall")
    tangent = (section(PHI_END)[0] - section(PHI_END - 0.01)[0]).normalized()
    lip_out = [m.add(m.verts[rows[-1][c]], Vector((PHI_END, round_of(c, around), 2.0))) for c in range(around)]
    lip_out.append(lip_out[0])
    lip_in = [m.add(m.verts[inside[0][c]], Vector((PHI_END, round_of(c, around), 2.0))) for c in range(around)]
    lip_in.append(lip_in[0])
    for c in range(around):
        m.face((lip_out[c], lip_out[c + 1], lip_in[c + 1], lip_in[c]), tangent, "lip")
    septum_at = section(inner_phis[-1])[0]
    tip = m.add(septum_at, Vector((inner_phis[-1], 0.5, 1.0)))
    way = (section(inner_phis[-1] + 0.01)[0] - septum_at).normalized()
    for c in range(around):
        m.face((tip, inside[-1][c], inside[-1][c + 1]), way, "septum")


# --- the soft body ------------------------------------------------------------------------------------

def aperture():
    """The aperture's middle, the way out of it (T), down its section towards the venter (R), its half height."""
    middle, half, wide = section(PHI_END)
    t = (section(PHI_END + 0.001)[0] - section(PHI_END - 0.001)[0]).normalized()
    r = radial(PHI_END)
    r = (r - t * r.dot(t)).normalized()
    return middle, t, r, half, wide


def body(m, low):
    ca, t, r, half, wide = aperture()
    up = -r
    # the head: rounded, filling the aperture and out of it
    m.part, m.index, m.root, m.a = HEAD, 0, ca, 0.0
    m.k = Vector((0.0, 0.0, 0.0))
    head_at = ca + t * (half * 0.25) + r * (half * 0.05)
    ellipsoid(m, head_at, (t, r, X), (half * 0.78, half * 0.68, wide * 0.78), "head", 4 if low else 10, 6 if low else 14)
    # the funnel: a short tube under the head, pointing back out of the aperture
    if not low:
        path = [head_at + r * (half * 0.55) - t * (half * 0.15), head_at + r * (half * 0.62) + t * (half * 0.35), head_at + r * (half * 0.62) + t * (half * 0.6)]
        tube(m, path, [half * 0.17, half * 0.14, half * 0.12], 8, "funnel", X, along=False)
    # the eyes: big, one on each side of the head
    m.part = EYE
    for sx in (1.0, -1.0):
        at = head_at + X * (sx * wide * 0.6) + t * (half * 0.12) - r * (half * 0.12)
        # (an eye turns about nothing: its root is its own middle, for the shader to draw its pupil round)
        m.root = at
        ellipsoid(m, at, (X * sx, t, r), (half * 0.24, half * 0.31, half * 0.31), "eyes", 3 if low else 8, 5 if low else 12)
    # the hood: a thick leathery shield from the aperture's inner edge over the top of the head, curving down at
    # its front
    m.part = HOOD
    hinge = ca + up * (half * 0.78)
    m.root = hinge
    nt, nu = (3, 3) if low else (8, 10)
    long = half * 1.15
    for side in (1.0, -1.0):
        grid = []
        for ti in range(nt + 1):
            tt = ti / nt
            row = []
            for ui in range(nu + 1):
                u = ui / nu
                across = (u - 0.5) * 2.0
                spread = wide * (0.95 - 0.25 * tt) * (1.0 - 0.15 * tt * tt)
                # (it arches over: highest along its middle, lower at its sides)
                arch = half * (0.16 * (1.0 - across * across) + 0.02)
                p = hinge + t * (long * tt) + up * (arch - half * 0.62 * tt * tt) + X * (across * spread)
                thick = half * 0.09 * math.sqrt(max(0.0, 1.0 - across * across)) * (1.0 - tt ** 3)
                row.append(m.add(p + up * (side * thick), None, tt))
            grid.append(row)
        for ti in range(nt):
            for ui in range(nu):
                quad = (grid[ti][ui], grid[ti][ui + 1], grid[ti + 1][ui + 1], grid[ti + 1][ui])
                middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
                # (each skin faces away from the hood's middle surface: up for the top skin, down for the under one)
                tt = (ti + 0.5) / nt
                m.face(quad, up * side + t * (side * 1.2 * tt), "hood")
    # the tentacles: ten round the mouth, trailing back and down
    m.part = TENTACLE
    mouth = head_at + t * (half * 0.7) + r * (half * 0.1)
    for i in range(10):
        angle = TAU * (i + 0.5) / 10
        out = X * math.cos(angle) + r * math.sin(angle)
        root = mouth + X * (math.cos(angle) * wide * 0.36) + r * (math.sin(angle) * half * 0.36)
        way = (t * 1.0 + out * 0.32 + r * 0.22).normalized()
        long = half * (1.05 + 0.25 * math.sin(i * 2.3))
        segments = 2 if low else 8
        path = [root + way * (long * s / segments) + r * (half * 0.25 * (s / segments) ** 2) for s in range(segments + 1)]
        m.index, m.root = i, root
        m.k = way
        tube(m, path, [half * 0.09 * (1.0 - 0.7 * s / segments) for s in range(segments + 1)], 3 if low else 6, "tentacles", r)
    m.index, m.root, m.a = 0, None, 0.0
    m.k = Vector((0.0, 0.0, 0.0))


# --- the game model -----------------------------------------------------------------------------------------
# The user, 2026-11-18: "We should have a twilight princess model to compare to so we can make low poly versions
# while maintaining high quality looks and silhouettes", then "just rebuild all of them, and keep the high
# quality version as well". The game model is built from the same coil, section and soft parts as the full one,
# its triangles spent on what shows: the last whorl (the whole outline from the side) ribbed in the model, a ring
# on every rib's crest and one in every furrow, so its edge is scalloped as the full one's is; eight points round
# the section, on the venter, the inner side and each flank at its widest (the outline from the front and from
# above); the hidden inner whorls smooth (lifted by the ribs' average height) and few rings round; a round head,
# round eyes for the cartoon eye, and the ten tentacles three-sided, of four pieces, so that they curl smoothly.

GAME_AROUND = 8
# How high the game model's ribs stand on the last whorl, of the full model's: a ring on each crest and one in
# each furrow makes a zigzag that stands out more than the full model's sharp crests, so they are made lower.
GAME_RIB = 0.62
# How far out from the section's curve its four in-between points stand (eight points cut its rounded corners).
GAME_CORNER = 1.14


def shell_game(m):
    around = GAME_AROUND
    phis = []
    # the hidden inner whorls: few rings round (fewer the smaller the whorl)
    phi = PHI_END - TAU * TURNS
    while phi < PHI_END - TAU - 1e-9:
        back = PHI_END - phi
        phis.append(phi)
        phi += TAU / (12 if back <= TAU * 2 else (7 if back <= TAU * 3 else 4))
    # the last whorl: a ring on each rib's crest and one in each furrow (cos(RIBS * phi) = 1 and -1)
    k = math.ceil((PHI_END - TAU) * 2.0 * RIBS / TAU)
    while k * TAU / (2.0 * RIBS) < PHI_END - 1e-9:
        phis.append(k * TAU / (2.0 * RIBS))
        k += 1
    phis.append(PHI_END)
    m.part, m.index, m.root, m.a = SHELL, 0, None, 0.0
    rows = []
    for phi in phis:
        last = phi > PHI_END - TAU - 1e-9
        row = []
        for c in range(around):
            psi = c / around * TAU
            if last:
                # (the rib, as the full model has it here, but lower: see GAME_RIB)
                p = shell_point(phi, psi, 1.0 + rib(phi, psi) * GAME_RIB, False)
            else:
                # (smooth, but as big as the ribbed tube there on average: a sharp crest's mean height is about
                # a quarter of its top)
                across = 0.35 + 0.65 * (0.5 + 0.5 * math.cos(psi))
                fade = smooth(PHI_END - TAU * 1.9, PHI_END - TAU * 1.2, phi)
                p = shell_point(phi, psi, 1.0 + 0.273 * RIB_HIGH * across * fade, False)
            if c % 2 == 1:
                # (the points between the venter, the flanks and the inner side stand out a little from the
                # section's curve, so that the straight sides between them lie across it, not inside it)
                p = section(phi)[0] + (p - section(phi)[0]) * GAME_CORNER
            row.append(m.add(p, Vector((phi, round_of(c, around), 0.0))))
        row.append(row[0])
        rows.append(row)
    for r in range(len(rows) - 1):
        middle_line = section(0.5 * (phis[r] + phis[r + 1]))[0]
        for c in range(around):
            quad = (rows[r][c], rows[r][c + 1], rows[r + 1][c + 1], rows[r + 1][c])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, middle - middle_line, "shell")
    centre, _, _ = section(phis[0])
    tip = m.add(centre, Vector((phis[0], 0.5, 0.0)))
    way = section(phis[0])[0] - section(phis[1])[0]
    for c in range(around):
        m.face((tip, rows[0][c], rows[0][c + 1]), way, "shell")
    # the body chamber's inner wall, the lip and the septum, as the low model has them but round as above
    deep = 1.0
    thick = 0.92
    inner_phis = [PHI_END - deep * i / 4 for i in range(5)]
    inside = []
    for phi in inner_phis:
        row = [m.add(shell_point(phi, c / around * TAU, thick, False), Vector((phi, round_of(c, around), 1.0))) for c in range(around)]
        inside.append(row + [row[0]])
    for r in range(len(inside) - 1):
        middle_line = section(0.5 * (inner_phis[r] + inner_phis[r + 1]))[0]
        for c in range(around):
            quad = (inside[r][c], inside[r][c + 1], inside[r + 1][c + 1], inside[r + 1][c])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, middle_line - middle, "inner wall")
    tangent = (section(PHI_END)[0] - section(PHI_END - 0.01)[0]).normalized()
    lip_out = [m.add(m.verts[rows[-1][c]], Vector((PHI_END, round_of(c, around), 2.0))) for c in range(around)]
    lip_out.append(lip_out[0])
    lip_in = [m.add(m.verts[inside[0][c]], Vector((PHI_END, round_of(c, around), 2.0))) for c in range(around)]
    lip_in.append(lip_in[0])
    for c in range(around):
        m.face((lip_out[c], lip_out[c + 1], lip_in[c + 1], lip_in[c]), tangent, "lip")
    septum_at = section(inner_phis[-1])[0]
    tip = m.add(septum_at, Vector((inner_phis[-1], 0.5, 1.0)))
    way = (section(inner_phis[-1] + 0.01)[0] - septum_at).normalized()
    for c in range(around):
        m.face((tip, inside[-1][c], inside[-1][c + 1]), way, "septum")


def body_game(m):
    """The soft body as the full model has it (the same places, sizes and ways), lighter: the head 4 rings by 10
    round, each eye 2 rings by 10 round (a round outline for the cartoon eye), the hood 4 by 4 a skin, the funnel
    six-sided, each tentacle three-sided, of four pieces, 1.2 times as thick (as wide as the round one)."""
    ca, t, r, half, wide = aperture()
    up = -r
    m.part, m.index, m.root, m.a = HEAD, 0, ca, 0.0
    m.k = Vector((0.0, 0.0, 0.0))
    head_at = ca + t * (half * 0.25) + r * (half * 0.05)
    ellipsoid(m, head_at, (t, r, X), (half * 0.78, half * 0.68, wide * 0.78), "head", 5, 10)
    path = [head_at + r * (half * 0.55) - t * (half * 0.15), head_at + r * (half * 0.62) + t * (half * 0.35), head_at + r * (half * 0.62) + t * (half * 0.6)]
    tube(m, path, [half * 0.17, half * 0.14, half * 0.12], 6, "funnel", X, along=False)
    m.part = EYE
    for sx in (1.0, -1.0):
        at = head_at + X * (sx * wide * 0.6) + t * (half * 0.12) - r * (half * 0.12)
        m.root = at
        ellipsoid(m, at, (X * sx, t, r), (half * 0.24, half * 0.31, half * 0.31), "eyes", 3, 10)
    m.part = HOOD
    hinge = ca + up * (half * 0.78)
    m.root = hinge
    nt, nu = 4, 4
    long = half * 1.15
    for side in (1.0, -1.0):
        grid = []
        for ti in range(nt + 1):
            tt = ti / nt
            row = []
            for ui in range(nu + 1):
                u = ui / nu
                across = (u - 0.5) * 2.0
                spread = wide * (0.95 - 0.25 * tt) * (1.0 - 0.15 * tt * tt)
                arch = half * (0.16 * (1.0 - across * across) + 0.02)
                p = hinge + t * (long * tt) + up * (arch - half * 0.62 * tt * tt) + X * (across * spread)
                thick = half * 0.09 * math.sqrt(max(0.0, 1.0 - across * across)) * (1.0 - tt ** 3)
                row.append(m.add(p + up * (side * thick), None, tt))
            grid.append(row)
        for ti in range(nt):
            for ui in range(nu):
                quad = (grid[ti][ui], grid[ti][ui + 1], grid[ti + 1][ui + 1], grid[ti + 1][ui])
                tt = (ti + 0.5) / nt
                m.face(quad, up * side + t * (side * 1.2 * tt), "hood")
    m.part = TENTACLE
    mouth = head_at + t * (half * 0.7) + r * (half * 0.1)
    for i in range(10):
        angle = TAU * (i + 0.5) / 10
        out = X * math.cos(angle) + r * math.sin(angle)
        root = mouth + X * (math.cos(angle) * wide * 0.36) + r * (math.sin(angle) * half * 0.36)
        way = (t * 1.0 + out * 0.32 + r * 0.22).normalized()
        long = half * (1.05 + 0.25 * math.sin(i * 2.3))
        segments = 4
        path = [root + way * (long * s / segments) + r * (half * 0.25 * (s / segments) ** 2) for s in range(segments + 1)]
        m.index, m.root = i, root
        m.k = way
        tube(m, path, [1.2 * half * 0.09 * (1.0 - 0.7 * s / segments) for s in range(segments + 1)], 3, "tentacles", r)
    m.index, m.root, m.a = 0, None, 0.0
    m.k = Vector((0.0, 0.0, 0.0))


def make(low, game=False):
    m = Mesh()
    if game:
        shell_game(m)
        body_game(m)
        return m
    shell(m, low)
    body(m, low)
    return m


# --- out to Blender, and the checks -------------------------------------------------------------------------

def material_of(name, colour):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = colour
    material.diffuse_color = colour
    return material


def placed(m, like=None):
    """Scales the model to DIAMETER across and puts the middle of the shell's outline at the origin; returns
    the scale and the shift. `like`: the scale and shift to use instead (the game model is placed as the full
    one is, so that the two lie exactly on each other and the shader's numbers fit both)."""
    if like is not None:
        scale, middle = like
    else:
        shell_points = [p for p, d in zip(m.verts, m.data) if d[3] == SHELL * 16]
        lo = Vector([min(p[i] for p in shell_points) for i in range(3)])
        hi = Vector([max(p[i] for p in shell_points) for i in range(3)])
        scale = DIAMETER / max(hi.z - lo.z, hi.y - lo.y)
        middle = (lo + hi) * 0.5
        middle.x = 0.0
    for i in range(len(m.verts)):
        m.verts[i] = (m.verts[i] - middle) * scale
        if m.data[i][0] is not None:
            m.data[i][0] = (m.data[i][0] - middle) * scale
    return scale, middle


def finish(name, m, low, like=None):
    global PLACED
    scale, middle = placed(m, like)
    PLACED = (scale, middle)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) for p in m.verts], [], m.faces)
    mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.new(name="UV2")
    mesh.color_attributes.new(name="Col", type="FLOAT_COLOR", domain="POINT")
    uv = mesh.uv_layers["UVMap"].data
    uv2 = mesh.uv_layers["UV2"].data
    for poly in mesh.polygons:
        for corner, vi in enumerate(poly.vertices):
            root, k, a, code = m.data[vi]
            uv[poly.loop_start + corner].uv = (k[0], 1.0 - k[1])
            uv2[poly.loop_start + corner].uv = (k[2], 1.0 - code)
    colours = mesh.color_attributes["Col"]
    for i, (root, k, a, code) in enumerate(m.data):
        joint = (0.0, 0.0, 0.0)
        if root is not None:
            joint = tuple((root[j] - BOX[0][j]) / (BOX[1][j] - BOX[0][j]) for j in range(3))
            assert all(0.0 <= c <= 1.0 for c in joint), "a joint outside BOX: %s" % (root,)
        colours.data[i].color = (joint[0], joint[1], joint[2], a)
    mesh.color_attributes.active_color = colours
    mesh.color_attributes.render_color_index = 0
    mesh.materials.append(material_of("ammonite", (0.85, 0.75, 0.62, 1.0)))
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
    if not low and like is None:
        ca, t, r, half, wide = aperture()
        axis = (Vector((0.0, 0.0, 0.0)) - middle) * scale
        mouth = (ca - middle) * scale
        print("AS THE SHADER HAS IT: APERTURE = vec3(%.5f, %.5f, %.5f); " % (mouth.x, mouth.y, mouth.z))
        print("AS THE SHADER HAS IT: COIL = vec3(%.5f, %.5f, %.5f); OUT_OF = vec3(%.5f, %.5f, %.5f); DOWN = vec3(%.5f, %.5f, %.5f); B = %.5f; HALF = %.5f; SCALE = %.5f"
              % (axis.x, axis.y, axis.z, t.x, t.y, t.z, r.x, r.y, r.z, B, half * scale, scale))
        # (the eye: its radius across its face, for the cartoon eye's sums)
        print("AS THE SHADER HAS IT: EYE_R = %.5f" % (half * 0.31 * scale))
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
    scene.render.resolution_x, scene.render.resolution_y = 1000, 800
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 100.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    # (Blender space: its front at +Y, up Z)
    views = [("left", (1, 0, 0)), ("right", (-1, 0, 0)), ("front", (0, 1, 0)), ("back", (0, -1, 0)),
             ("top", (0.001, 0, 1)), ("under", (0.001, 0, -1)), ("quarter", (0.7, -0.6, 0.2)), ("head", (0.5, -0.8, -0.3))]
    for obj in made:
        for other in made:
            other.hide_render = other is not obj
        for view, direction in views:
            offset = Vector(direction).normalized() * 5.0
            camera.data.ortho_scale = size * (0.6 if view == "head" else 1.0)
            target = Vector((0.0, -0.12, -0.12)) if view == "head" else Vector((0.0, 0.0, 0.0))
            camera.location = target + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s_%s.png" % (obj.name, view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    full = finish("ammonite", make(False), False)
    like = PLACED
    low = finish("ammonite_lo", make(True), True)
    game = finish("ammonite_game", make(False, True), False, like)
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, "ammonite.glb"))
    export_one(low, os.path.join(OUT, "ammonite_lo.glb"))
    export_one(game, os.path.join(OUT, "ammonite_game.glb"))
    # (in the .blend all three side by side: the full, the game model, the low)
    game.location.x = 0.4
    low.location.x = 0.8
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "ammonite.blend"))
    game.location.x = 0.0
    low.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low, game], 0.62)


if __name__ == "__main__":
    main()
