"""Builds the sea anemones (creatures/anemone, Anemone) and exports them for Godot.

Run from the game's root (or anywhere: paths are from this file):
    blender --background --factory-startup --python creatures/anemone/tools/build_anemone.py
    blender --background --factory-startup --python creatures/anemone/tools/build_anemone.py -- <preview folder>

Three kinds, each three models (the full one, the game one and the low one), all built from the same lines here:

- GIANT GREEN (Anthopleura xanthogrammica, of the Californian rocky shore): squat, a stout olive column studded with
  rows of small bumps (verrucae), a broad flat green oral disc with a slit mouth in its middle, and rows of short,
  thick, blunt green tentacles round the outer part of the disc. 0.19 m across, 0.08 m high.
- TUBE (Pachycerianthus fimbriatus, the Californian tube-dwelling anemone): a long slender felt tube standing out of
  the sand, the animal's small oral disc at its mouth, an inner ring of short tentacles over the mouth and a crown of
  very long thin outer tentacles that arch out and trail down. The tube 0.27 m high; the crown about 0.36 m across.
- PLUMOSE (Metridium farcimen, the giant plumose anemone): a tall smooth column with a collar under its top, crowned
  by a mass of lobed, ruffled disc covered in very many fine short tentacles: the feathery head. 0.44 m high, the
  crown about 0.34 m across.

It writes creatures/anemone/models/anemone_<kind>.glb, anemone_<kind>_game.glb and anemone_<kind>_lo.glb, and the
editable creatures/anemone/tools/anemone_<kind>.blend (all three models of that kind; this folder has a .gdignore).
Each is one still mesh with one surface: the shader (anemone.gdshader) sways the tentacles, pulls them in and squats
the column (`retract`), and draws the colours. Every part (the body, each tentacle, the tube) is a closed solid, and
the script prints a WINDING line: a ray out of every triangle of a part must leave that part an even number of times.

THE BASE IS AT y = 0, its middle on the Y axis (the tube goes 0.012 m below it, into the sand).

What a point is, for the shader (all kinds):
- COLOR.r the part, as a tenth: 0 the body (its foot, column and, on the plumose, the crown's underside), 1 the oral
  disc (on the plumose the top of the crown), 2 a tentacle, 3 the tube.
- On the body and the disc: UV.x `u`, how far along the body's profile (0 the middle of the foot, 1 the foot's rim,
  2 the top of the column at the disc's margin, 3 the middle of the disc); UV.y how far round (0..1).
- On a tentacle: UV.x how far along it (0 its root, 1 its tip); UV.y its root's height; UV2 its root's x and z;
  COLOR.g a number of its own (0..1); COLOR.b how far out on the disc its root is (1 - (u - 2): 0 the middle, 1 the
  margin); on the tube anemone COLOR.a is 1 for the long outer tentacles and 0 for the short inner ones.
- On the tube: UV.x how far up it (0 its foot, 1 its lip); UV.y how far round.
(The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.)

The numbers marked "as the shader has it" are in anemone.gdshader too (or set by anemone.gd per kind): change one,
change the other.
"""

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
BODY, DISC, TENTACLE, TUBE = 0, 1, 2, 3
UP = Vector((0.0, 1.0, 0.0))


def to_b(p):
    """Godot's space (Y up) to Blender's (Z up)."""
    return Vector((p.x, -p.z, p.y))


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


# ---------------------------------------------------------------------------------------------------------------
# The bodies: shape(u, angle) -> (how far out, how high), u as above (0..1 the foot, 1..2 the column, 2..3 the disc).

def green_margin(a):
    return 0.093 * (1.0 + 0.025 * math.sin(3.0 * a + 0.6) + 0.015 * math.sin(7.0 * a))


def green_shape(u, a):
    foot = 0.078
    high = 0.058
    if u <= 1.0:
        return foot * u, 0.0
    if u <= 2.0:
        s = u - 1.0
        # a stout column, a little waisted, flaring at its top into the disc's margin
        r = foot * (1.0 - 0.07 * math.sin(math.pi * s)) + (green_margin(a) - foot) * s ** 3
        return r, high * s
    s = u - 2.0
    # the disc: a rolled lip at the margin, flat to a little sunk towards the middle, the mouth's lips raised
    r = green_margin(a) * (1.0 - s)
    y = high + 0.007 * math.sin(0.5 * math.pi * min(s / 0.12, 1.0)) - 0.004 * smooth(0.12, 0.8, s)
    y += 0.0025 * math.exp(-((s - 0.93) / 0.035) ** 2)
    return r, y


TUBE_TOP = 0.27        # the tube's lip
TUBE_R = 0.02          # the tube's outer radius at its foot (wider at its lip)


def tube_margin(a):
    return 0.022


def tube_shape(u, a):
    # the animal inside its tube: its foot down in the tube, its oral disc a low dome at the tube's mouth
    base = TUBE_TOP - 0.06
    if u <= 1.0:
        return 0.015 * u, base
    if u <= 2.0:
        s = u - 1.0
        r = 0.015 + (tube_margin(a) - 0.015) * s ** 3
        return r, base + (TUBE_TOP + 0.003 - base) * s
    s = u - 2.0
    r = tube_margin(a) * (1.0 - s)
    y = TUBE_TOP + 0.003 + 0.004 * math.sin(0.5 * math.pi * min(s / 0.5, 1.0)) - 0.0015 * math.exp(-((s - 1.0) / 0.12) ** 2)
    return r, y


PLUME_COLLAR = 0.29    # the collar under the crown


def plume_margin(a):
    """How far out the crown's margin is, and how high: six big lobes, each frilled again into smaller folds that
    rise and fall, the whole margin hanging out and down round the crown (a cauliflower of a head)."""
    r = 0.158 * (1.0 + 0.1 * math.cos(6.0 * a) + 0.045 * math.cos(12.0 * a + 0.7) + 0.035 * math.sin(5.0 * a + 1.3)
                 + 0.02 * math.cos(2.0 * a))
    y = 0.352 + 0.026 * math.sin(6.0 * a + 0.9) + 0.016 * math.cos(12.0 * a + 0.3) + 0.012 * math.sin(5.0 * a + 2.1)
    return r, y


def plume_shape(u, a):
    foot = 0.078
    if u <= 1.0:
        return foot * u, 0.0
    if u <= 2.0:
        s = u - 1.0
        if s <= 0.8:
            # the pedal disc flaring onto the rock, then a long smooth column, the collar a ridge under the crown
            k = s / 0.8
            r = 0.05 + (foot - 0.05) * (1.0 - smooth(0.0, 0.13, k)) ** 2
            r += 0.006 * math.exp(-((k - 0.97) / 0.035) ** 2) - 0.002 * math.sin(math.pi * k)
            return r, PLUME_COLLAR * k
        # the crown's underside: out and up from just above the collar to the frilled margin
        k = (s - 0.8) / 0.2
        mr, my = plume_margin(a)
        r = 0.05 + (mr - 0.05) * (1.0 - (1.0 - k) ** 1.6)
        y = PLUME_COLLAR + (my - PLUME_COLLAR) * (1.0 - (1.0 - k) ** 2.2)
        return r, y
    s = u - 2.0
    # the crown's top: the margin rolling up and over into a lumpy dome, a shallow dip round the mouth
    mr, my = plume_margin(a)
    r = mr * (1.0 - s) ** 0.85
    top = 0.448 + 0.012 * math.sin(6.0 * a + 2.0)
    y = my + (top - my) * math.sin(0.5 * math.pi * min(s / 0.42, 1.0)) - 0.024 * smooth(0.5, 1.0, s)
    return r, y


# ---------------------------------------------------------------------------------------------------------------
# Each kind: its body, its tentacles, and how fine each of its three models is ("full", "game", "low").

KINDS = {
    "giant_green": {
        "shape": green_shape, "margin": green_margin, "seed": 3,
        # the body: points round it, then the u of each ring
        "around": {"full": 64, "game": 22, "low": 10},
        "rings": {
            "full": [0.5, 1.0] + [1.0 + i / 12 for i in range(1, 13)] + [2.0 + s for s in (0.02, 0.05, 0.08, 0.12, 0.17, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.83, 0.88, 0.91, 0.93, 0.95, 0.97)],
            "game": [1.0, 1.25, 1.55, 1.8, 1.92, 2.0, 2.05, 2.12, 2.4, 2.8, 2.93],
            "low": [1.0, 1.5, 2.0, 2.12, 2.6],
        },
        # tentacles: how many, sides, the places of their rings along them (and how thick there, of the root)
        "tentacles": {
            "full": (210, 6, [0.0, 0.3, 0.6, 0.85], [1.0, 0.95, 0.85, 0.66]),
            "game": (70, 5, [0.0, 0.8], [1.0, 0.8]),
            "low": (35, 3, [0.0], [1.0]),
        },
        "thick": {"full": 1.0, "game": 1.32, "low": 1.7},
    },
    "tube": {
        "shape": tube_shape, "margin": tube_margin, "seed": 5,
        "around": {"full": 40, "game": 12, "low": 8},
        "rings": {
            "full": [1.0, 1.5, 1.8, 1.92, 2.0, 2.15, 2.35, 2.6, 2.85],
            "game": [1.0, 1.9, 2.0, 2.4],
            "low": [1.0, 2.0],
        },
        # (outer tentacles: count, sides, rings; inner ones: count, sides, rings)
        "tentacles": {
            "full": ((120, 6, 14), (42, 5, 4)),
            "game": ((40, 3, 6), (14, 3, 2)),
            "low": ((20, 3, 3), (0, 3, 1)),
        },
        "thick": {"full": 1.0, "game": 1.25, "low": 1.5},
        "tube": {"full": (40, 18), "game": (12, 5), "low": (8, 2)},
    },
    "plumose": {
        "shape": plume_shape, "margin": lambda a: plume_margin(a)[0], "seed": 7,
        "around": {"full": 144, "game": 36, "low": 14},
        "rings": {
            "full": [0.5, 1.0, 1.02, 1.04, 1.06, 1.08, 1.11, 1.15, 1.25, 1.35, 1.45, 1.55, 1.65, 1.72, 1.76, 1.78, 1.8,
                     1.82, 1.85, 1.88, 1.91, 1.94, 1.97, 2.0, 2.03, 2.07, 2.12, 2.2, 2.3, 2.42, 2.56, 2.72, 2.9],
            "game": [1.0, 1.04, 1.1, 1.4, 1.75, 1.785, 1.81, 1.87, 1.94, 2.0, 2.08, 2.22, 2.5, 2.85],
            "low": [1.0, 1.1, 1.78, 1.9, 2.0, 2.3, 2.75],
        },
        "tentacles": {
            "full": (1530, 4, [0.0, 0.7], [1.0, 0.85]),
            "game": (170, 3, [0.0], [1.0]),
            "low": (0, 3, [0.0], [1.0]),
        },
        "thick": {"full": 1.0, "game": 1.5, "low": 1.0},
    },
}


class Part:
    """One closed piece: points (metres), what each is for the shader, and faces. `done` welds it, turns every
    face outward and checks that."""

    def __init__(self, name):
        self.name = name
        self.verts = []
        self.data = []
        self.faces = []

    def add(self, p, uv, uv2, colour):
        self.verts.append(Vector(p))
        self.data.append((uv, uv2, colour))
        return len(self.verts) - 1

    @staticmethod
    def inside_out(bm):
        cut = bm.copy()
        bmesh.ops.triangulate(cut, faces=cut.faces)
        cut.normal_update()
        tree = BVHTree.FromBMesh(cut)
        wrong = 0
        counted = 0
        for f in cut.faces:
            if f.calc_area() > 1e-12:
                counted += 1
                at = f.calc_center_median() + f.normal * 1e-6
                hits = 0
                while hits < 40:
                    hit = tree.ray_cast(at, f.normal)
                    if hit[0] is None:
                        break
                    hits += 1
                    at = hit[0] + f.normal * 1e-6
                if hits % 2:
                    wrong += 1
        cut.free()
        return wrong, counted

    def done(self):
        bm = bmesh.new()
        uv = bm.loops.layers.uv.new("uv")
        uv2 = bm.loops.layers.uv.new("uv2")
        colour = bm.loops.layers.float_color.new("colour")
        made = [bm.verts.new(to_b(p)) for p in self.verts]
        for face in self.faces:
            try:
                f = bm.faces.new([made[i] for i in face])
            except ValueError:
                continue
            for loop, i in zip(f.loops, face):
                d = self.data[i]
                loop[uv].uv = d[0]
                loop[uv2].uv = d[1]
                loop[colour] = d[2]
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.normal_update()
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


def body(kind, level):
    """The foot, the column and the disc as one closed solid: rings round the Y axis at each u."""
    info = KINDS[kind]
    shape = info["shape"]
    around = info["around"][level]
    part = Part("body")
    centre = part.add((0.0, shape(0.0, 0.0)[1], 0.0), (0.0, 0.0), (0.0, 0.0), (BODY / 10.0, 0.0, 0.0, 0.0))
    rings = []
    for u in info["rings"][level]:
        code = DISC if u > 2.0 + 1e-9 else BODY
        ring = []
        for k in range(around + 1):
            a = TAU * k / around
            r, y = shape(u, a)
            ring.append(part.add((r * math.cos(a), y, r * math.sin(a)), (u, 1.0 - k / around), (0.0, 0.0),
                                 (code / 10.0, 0.0, 0.0, 0.0)))
        rings.append(ring)
    # the disc's middle: the mouth
    top = part.add((0.0, shape(3.0, 0.0)[1], 0.0), (3.0, 0.0), (0.0, 0.0), (DISC / 10.0, 0.0, 0.0, 0.0))
    for k in range(around):
        part.faces.append((centre, rings[0][k + 1], rings[0][k]))
        part.faces.append((top, rings[-1][k], rings[-1][k + 1]))
    for a, b in zip(rings, rings[1:]):
        for k in range(around):
            part.faces.append((a[k], a[k + 1], b[k + 1], b[k]))
    return part


def disc_point(kind, s, a):
    """A point on the disc (s 0 at the margin to 1 at the middle) and the way its surface faces."""
    shape = KINDS[kind]["shape"]

    def at(s_, a_):
        r, y = shape(2.0 + s_, a_)
        return Vector((r * math.cos(a_), y, r * math.sin(a_)))

    p = at(s, a)
    ds = at(min(s + 0.01, 1.0), a) - at(max(s - 0.01, 0.0), a)
    da = at(s, a + 0.01) - at(s, a - 0.01)
    n = da.cross(ds)
    if n.y < 0.0:
        n = -n
    return p, n.normalized()


def tentacle(kind, rng, s, a, long, thick, sides, line, stations, radii, outer=1.0, seed=None):
    """One tentacle: rings along `line(t)` (t 0 its root to 1 its tip), a rounded tip, its root closed flat (sunk
    in the disc, where nothing sees it)."""
    part = Part("tentacle")
    root, _ = disc_point(kind, s, a)
    seed = rng.random() if seed is None else seed
    out_k = 1.0 - s
    tags_uv2 = (root.x, 1.0 - root.z)
    colour = (TENTACLE / 10.0, seed, out_k, outer)
    rings = []
    round_way = Vector((-math.sin(a), 0.0, math.cos(a)))
    for t, k in zip(stations, radii):
        at = line(t)
        ahead = (line(min(t + 0.02, 1.0)) - line(max(t - 0.02, 0.0))).normalized()
        side = (round_way - ahead * round_way.dot(ahead)).normalized()
        other = side.cross(ahead).normalized()
        ring = []
        # (a polygon of few sides is made a little fatter, to look as wide as the round one it stands for)
        fat = math.pi / (sides * math.sin(math.pi / sides))
        for j in range(sides):
            q = TAU * j / sides
            ring.append(part.add(at + (side * math.cos(q) + other * math.sin(q)) * (thick * k * fat),
                                 (t, 1.0 - root.y), tags_uv2, colour))
        rings.append(ring)
    tip = part.add(line(1.0), (1.0, 1.0 - root.y), tags_uv2, colour)
    for r0, r1 in zip(rings, rings[1:]):
        for j in range(sides):
            n = (j + 1) % sides
            part.faces.append((r0[j], r0[n], r1[n], r1[j]))
    last = rings[-1]
    for j in range(sides):
        part.faces.append((last[j], last[(j + 1) % sides], tip))
    part.faces.append(tuple(reversed(rings[0])))
    return part


def green_tentacles(kind, level, rng):
    """(The game and low models have every third and sixth of the full model's own tentacles.)"""
    count, sides, stations, radii = KINDS[kind]["tentacles"][level]
    full = KINDS[kind]["tentacles"]["full"][0]
    parts = []
    golden = math.pi * (3.0 - math.sqrt(5.0))
    for i in range(full):
        # rows round the outer part of the disc (its middle bare): from 0.58 of the way out to the lip
        a = i * golden + rng.uniform(-0.05, 0.05)
        wander = Vector((rng.uniform(-0.12, 0.12), 0.0, rng.uniform(-0.12, 0.12)))
        long_k = rng.uniform(0.022, 0.03)
        thick = rng.uniform(0.0042, 0.0050) * KINDS[kind]["thick"][level]
        droop_k = rng.uniform(0.0, 0.1)
        seed = rng.random()
        if count == 0 or i % (full // count):
            continue
        reach = (i + 0.5) / full
        out = 0.58 + 0.39 * math.sqrt(reach)
        s = 1.0 - out
        root, n = disc_point(kind, s, a)
        root = root - n * 0.002
        outward = Vector((math.cos(a), 0.0, math.sin(a)))
        lean = (n * (1.0 - 0.45 * out ** 3) + outward * (0.15 + 0.85 * out ** 3)).normalized()
        lean = (lean + wander).normalized()
        long = long_k * (0.85 + 0.3 * out)
        droop = 0.35 * out ** 2 + droop_k

        def line(t, root=root, lean=lean, long=long, droop=droop, outward=outward):
            return root + lean * (long * t) + outward * (long * 0.1 * t * t) - UP * (long * droop * t * t)

        # (stout, blunt: thick to near the tip, then a round end)
        parts.append(tentacle(kind, rng, s, a, long, thick, sides, line, stations, radii, 1.0, seed))
    return parts


def tube_tentacles(kind, level, rng):
    """The game and low models have every third (sixth) of the full model's own tentacles, the very same ones, so
    that what they show stands where the full model's does."""
    (outer_n, outer_sides, outer_rings), (inner_n, inner_sides, inner_rings) = KINDS[kind]["tentacles"][level]
    (full_outer, _, _), (full_inner, _, _) = KINDS[kind]["tentacles"]["full"]
    fat = KINDS[kind]["thick"][level]
    parts = []
    # the outer crown: two staggered rows at the disc's margin, each tentacle arching out and trailing down
    for i in range(full_outer):
        row = i % 2
        a = TAU * (i + 0.5 * row) / full_outer + rng.uniform(-0.02, 0.02)
        s = 0.02 + 0.08 * row
        long = rng.uniform(0.15, 0.19) * (1.0 - 0.12 * row)
        rise = 0.38 + 0.25 * row + rng.uniform(-0.08, 0.08)
        fall = 1.0 + rng.uniform(-0.2, 0.25)
        twist = rng.uniform(-0.12, 0.12)
        seed = rng.random()
        if outer_n == 0 or i % (full_outer // outer_n):
            continue
        root, n = disc_point(kind, s, a)
        root = root - UP * 0.0015
        outward = Vector((math.cos(a), 0.0, math.sin(a)))
        side = Vector((-math.sin(a), 0.0, math.cos(a)))

        def line(t, root=root, outward=outward, side=side, long=long, rise=rise, fall=fall, twist=twist):
            # up and out from the margin, then out and over, the tip hanging down
            return (root + outward * (long * (0.82 * t - 0.12 * t * t)) + UP * (long * (rise * t - fall * t * t))
                    + side * (long * twist * t * t))

        stations = [(j / (outer_rings - 1)) ** 1.1 * 0.94 for j in range(outer_rings)]
        radii = [1.0 - 0.7 * t for t in stations]
        thick = 0.0013 * fat
        parts.append(tentacle(kind, rng, s, a, long, thick, outer_sides, line, stations, radii, 1.0, seed))
    # the inner ring: short tentacles curling up and in over the mouth
    for i in range(full_inner):
        a = TAU * (i + 0.3) / full_inner + rng.uniform(-0.05, 0.05)
        s = 0.5 + rng.uniform(-0.04, 0.04)
        long = rng.uniform(0.022, 0.032)
        seed = rng.random()
        if inner_n == 0 or i % (full_inner // inner_n):
            continue
        root, n = disc_point(kind, s, a)
        root = root - UP * 0.001
        outward = Vector((math.cos(a), 0.0, math.sin(a)))

        def line(t, root=root, outward=outward, long=long):
            return root + UP * (long * (0.95 * t - 0.15 * t * t)) + outward * (long * (0.25 * t - 0.55 * t * t))

        stations = [j / inner_rings * 0.85 for j in range(inner_rings)]
        radii = [1.0 - 0.5 * t for t in stations]
        parts.append(tentacle(kind, rng, s, a, long, 0.0011 * fat, inner_sides, line, stations, radii, 0.0, seed))
    return parts


def plume_tentacles(kind, level, rng):
    """(The game model has every ninth of the full model's own tentacles.)"""
    count, sides, stations, radii = KINDS[kind]["tentacles"][level]
    full = KINDS[kind]["tentacles"]["full"][0]
    parts = []
    golden = math.pi * (3.0 - math.sqrt(5.0))
    for i in range(full):
        # over the crown's top, thickest towards the lobes' edges
        a = i * golden + rng.uniform(-0.02, 0.02)
        wander = Vector((rng.uniform(-0.3, 0.3), rng.uniform(-0.1, 0.1), rng.uniform(-0.3, 0.3)))
        long_k = rng.uniform(0.008, 0.015)
        seed = rng.random()
        if count == 0 or i % (full // count):
            continue
        reach = (i + 0.5) / full
        s = 0.004 + 0.72 * reach ** 1.6
        root, n = disc_point(kind, s, a)
        root = root - n * 0.0008
        outward = Vector((math.cos(a), 0.0, math.sin(a)))
        lean = (n + outward * (0.5 * (1.0 - s))).normalized()
        lean = (lean + wander).normalized()
        long = long_k * (0.8 + 0.4 * (1.0 - s))
        thick = 0.0016 * KINDS[kind]["thick"][level]

        def line(t, root=root, lean=lean, long=long, outward=outward):
            return root + lean * (long * t) + outward * (long * 0.15 * t * t) - UP * (long * 0.15 * t * t)

        parts.append(tentacle(kind, rng, s, a, long, thick, sides, line, stations, radii, 1.0, seed))
    return parts


def tube_part(level):
    """The tube anemone's felt tube: a thick-walled tube from below the sand to its lip, open at its top, its
    floor inside it (where the animal's foot is)."""
    around, rings_up = KINDS["tube"]["tube"][level]
    part = Part("tube")
    bottom = -0.012
    floor = TUBE_TOP - 0.065
    wall = 0.0028

    def outer_r(t, a):
        # a little wider and more ragged towards its lip
        return TUBE_R * (1.0 + 0.12 * t ** 3) * (1.0 + 0.03 * math.sin(5.0 * a + 7.0 * t) * t)

    def ring(points, t):
        return [part.add(p, (t, 1.0 - k / around), (0.0, 0.0), (TUBE / 10.0, 0.0, 0.0, 0.0)) for k, p in enumerate(points)]

    profile = []
    for j in range(rings_up + 1):
        t = 1.0 - (1.0 - j / rings_up) ** 1.4 if level == "full" else j / rings_up
        y = bottom + (TUBE_TOP - bottom) * t
        profile.append(("out", t, y))
    rows = []
    for kind_, t, y in profile:
        pts = []
        for k in range(around + 1):
            a = TAU * k / around
            r = outer_r(t, a)
            pts.append(Vector((r * math.cos(a), y, r * math.sin(a))))
        rows.append(ring(pts, t))
    # the lip's inner edge, the inside wall down to the floor
    inner = []
    for y in (TUBE_TOP, floor):
        pts = []
        for k in range(around + 1):
            a = TAU * k / around
            r = outer_r(1.0 if y == TUBE_TOP else 0.6, a) - wall
            pts.append(Vector((r * math.cos(a), y, r * math.sin(a))))
        inner.append(ring(pts, 1.0))
    rows += inner
    for r0, r1 in zip(rows, rows[1:]):
        for k in range(around):
            part.faces.append((r0[k], r0[k + 1], r1[k + 1], r1[k]))
    foot = part.add((0.0, bottom, 0.0), (0.0, 0.0), (0.0, 0.0), (TUBE / 10.0, 0.0, 0.0, 0.0))
    top = part.add((0.0, floor, 0.0), (1.0, 0.0), (0.0, 0.0), (TUBE / 10.0, 0.0, 0.0, 0.0))
    for k in range(around):
        part.faces.append((foot, rows[0][k + 1], rows[0][k]))
        part.faces.append((top, rows[-1][k], rows[-1][k + 1]))
    return part


def make(kind, level, name):
    rng = random.Random(KINDS[kind]["seed"])
    parts = [body(kind, level)]
    if kind == "giant_green":
        parts += green_tentacles(kind, level, rng)
    elif kind == "tube":
        parts.append(tube_part(level))
        parts += tube_tentacles(kind, level, rng)
    else:
        parts += plume_tentacles(kind, level, rng)
    verts, faces, corners = [], [], []
    wrong_by, counted_by = {}, {}
    for part in parts:
        out, wrong, counted = part.done()
        wrong_by[part.name] = wrong_by.get(part.name, 0) + wrong
        counted_by[part.name] = counted_by.get(part.name, 0) + counted
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
    tint = {"giant_green": (0.2, 0.55, 0.3, 1.0), "tube": (0.75, 0.5, 0.3, 1.0), "plumose": (0.9, 0.88, 0.82, 1.0)}[kind]
    material = bpy.data.materials.get("anemone_" + kind) or bpy.data.materials.new("anemone_" + kind)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = tint
    material.diffuse_color = tint
    mesh.materials.append(material)
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    # (every face was made with corners of its own: the same point is one point again)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.remove_doubles(threshold=1e-8)
    bpy.ops.object.mode_set(mode="OBJECT")
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    lo = [min(v.co[k] for v in mesh.vertices) for k in range(3)]
    hi = [max(v.co[k] for v in mesh.vertices) for k in range(3)]
    reach = max(math.hypot(v.co.x, v.co.y) for v in mesh.vertices)
    print("BUILT %s verts=%d tris=%d parts=%d x %.3f..%.3f z %.3f..%.3f y %.3f..%.3f reach %.3f" % (
        name, len(mesh.vertices), tris, len(parts), lo[0], hi[0], -hi[1], -lo[1], lo[2], hi[2], reach))
    bad = sum(wrong_by.values())
    print("WINDING %s: %s: %s" % (name, "ok" if bad == 0 else "INSIDE OUT",
                                  ", ".join("%s %d/%d wrong" % (k, wrong_by[k], counted_by[k]) for k in wrong_by)))
    return obj


def export_one(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", export_yup=True, use_selection=True,
        export_animations=False, export_vertex_color="ACTIVE", export_texcoords=True,
    )


def render(folder, kind, made, size, mid):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_cavity = True
    scene.display.shading.show_backface_culling = True
    scene.render.resolution_x, scene.render.resolution_y = 1000, 800
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 100.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    views = [("side", (1, 0, 0.0001)), ("side2", (0, 1, 0.0001)), ("top", (0.0001, 0, 1)), ("under", (0.0001, 0, -1)),
             ("quarter", (0.7, 0.6, 0.6))]
    for obj in made:
        for other in made:
            other.hide_render = other is not obj
        for view, direction in views:
            offset = Vector(direction).normalized() * 10.0
            camera.data.ortho_scale = size
            camera.location = Vector((0.0, 0.0, mid)) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "X" if view in ("top", "under") else "Y").to_euler()
            scene.render.filepath = os.path.join(folder, "%s_%s.png" % (obj.name, view))
            bpy.ops.render.render(write_still=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    for kind, size, mid in (("giant_green", 0.26, 0.04), ("tube", 0.46, 0.14), ("plumose", 0.62, 0.23)):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version = 0
        name = "anemone_" + kind
        full = make(kind, "full", name)
        game = make(kind, "game", name + "_game")
        low = make(kind, "low", name + "_lo")
        export_one(full, os.path.join(OUT, name + ".glb"))
        export_one(game, os.path.join(OUT, name + "_game.glb"))
        export_one(low, os.path.join(OUT, name + "_lo.glb"))
        # (in the .blend: the full model in the middle, the game one to its right, the low one beyond)
        game.location.x = size
        low.location.x = size * 2.0
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, name + ".blend"))
        game.location.x = 0.0
        low.location.x = 0.0
        if PREVIEW:
            os.makedirs(PREVIEW, exist_ok=True)
            render(PREVIEW, kind, [full, game, low], size, mid)


if __name__ == "__main__":
    main()
