"""Builds the red mangrove's trees and root clusters (Rhizophora mangle) and saves them:

    blender --background --factory-startup --python plants/mangrove/tools/build_mangrove.py

run from a game's root (or GameCommon's godot/mangrove/files). It writes, beside this file's folder:

    ../models/mangrove_a.glb .. mangrove_d.glb        four trees (root spreads about 3, 4, 5 and 6 m)
    ../models/mangrove_roots_a.glb, _roots_b.glb      two root clusters (a low bough dropping roots to both sides)
    ../models/mangrove_<each>_lo.glb                  each of those, very light, for far off
    ../mangrove_shapes.gd                             the spheres that fill each one's root tangles (for a game's fish)
    mangrove.blend                                    all twelve, side by side, to edit

and prints a WINDING line for each mesh (the check that nothing is inside out) and a SPHERES line for each piece.

WHAT A TREE IS. In Godot's axes (+Y up), y = 0 is the WATERLINE and the tree's middle line is the Y axis.

- PROP ROOTS: arching tubes that leave the trunk (and the lower limbs) 0.6 to 2.6 m above the water, run out and
  curve down, go in through the surface steeply and down into the mud. The MUD LINE is y = -3 (MUD); roots go on
  0.5 m below it, so a game may sink a tree a little. Some fork near the water. They come in CLUSTERS, a few roots
  side by side, with open water between clusters (room for a small fish to thread through).
- HANGING AERIAL ROOTS: thin, from the limbs, hanging down; they end between 1.2 m under the water and 0.8 m above it,
  never reaching the mud. Their tips are pale (new growth).
- A short crooked TRUNK standing on its roots (its foot 0.4 to 0.8 m above the water), forking into crooked LIMBS.
- The CANOPY: a low dense dome of leaf clumps, each a dark lumpy core (an ellipsoid) inside an overlapping shell of
  leaf cards (each card a square that mangrove.gdshader cuts into nine twig tips of five thick oval leaves, about
  life size), up to 3.6 .. 6.3 m over the water.
- SEED PODS (propagules: long green cigars, brown at the tip) hanging under the canopy; a few have fallen and lie
  on the mud. FALLEN LEAVES: some float just under the surface (y = -0.01), some lie on the mud (y = MUD).

A ROOT CLUSTER is a low crooked bough lying along x 1.2 to 1.9 m over the water (sagging in the middle, rising at
its ends), three short twigs with small crowns, and twelve to fifteen prop roots arching down from it to both sides
in clusters along it (open water between), to thicken the fringe of a bank between trees.

The light pieces: roots and limbs as three- or four-sided tubes in few segments, no forks, no hanging roots, no pods
or fallen leaves; the clumps coarser, with a few big cards.

WHAT EACH POINT TELLS THE SHADER:
    UV      on a leaf card or a fallen leaf: x, y across it (0 to 1); along a pod: y from its stalk (0) to its tip (1)
    UV2     x: what it is (0 wood: trunk, limbs, roots; 1 leaf clump; 2 leaf card; 3 pod; 4 floating leaf;
            5 leaf on the mud); y: a number of its own (0 to 1)
    COLOR   r: crust (0 bare bark, 1 crusted: below the waterline, ragged at the edge); g: of the crust, how much is
            algae fuzz (1) rather than oysters and barnacles (0); b: a pale growing tip (hanging roots)
(The glTF exporter writes a UV's y as 1 - y; this script writes 1 - y, so that Godot reads y.)
"""
import math
import os
import random

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(HERE, "..", "models")
SHAPES = os.path.join(HERE, "..", "mangrove_shapes.gd")
TAU = math.tau
UP = Vector((0.0, 1.0, 0.0))
MUD = -3.0
BURIED = 0.5                 # how far the roots go on below the mud line
WOOD, CLUMP, CARD, POD, FLOATING, MUDLEAF = 0.0, 1.0, 2.0, 3.0, 4.0, 5.0
FISH_GAP = 0.45              # the least room left between two spheres of different clusters (a 0.3 m fish and some)


class Mesh:
    """Points in Godot's axes (+Y up), faces wound to face the way they are told to."""

    def __init__(self):
        self.verts = []
        self.colours = []
        self.faces = []      # (indices, uvs, uv2)
        self.told = []
        self.closed = []

    def dab(self, p, colour=(0.0, 0.0, 0.0, 1.0)):
        self.verts.append(Vector(p))
        self.colours.append(colour)
        return len(self.verts) - 1

    def face(self, idx, out, uvs, uv2, closed):
        idx = list(idx)
        uvs = list(uvs)
        a, b, c = (self.verts[i] for i in idx[:3])
        n = (b - a).cross(c - a)
        if len(idx) == 4:
            n += (self.verts[idx[2]] - a).cross(self.verts[idx[3]] - a)
        if n.dot(out) < 0.0:
            idx.reverse()
            uvs.reverse()
        self.faces.append((idx, uvs, uv2))
        self.told.append(Vector(out))
        self.closed.append(closed)

    def triangles(self):
        return sum(len(f[0]) - 2 for f in self.faces)


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def crust_of(p, rng, tip=0.0, shift=0.0):
    """The vertex colour of a point of wood: crusted below the waterline (ragged at the edge), more algae deeper."""
    edge = 0.08 + shift + rng.uniform(-0.08, 0.08)
    crust = smooth(edge, edge - 0.3, p.y)
    algae = max(0.0, min(1.0, smooth(-0.3, -2.0, p.y) * 0.8 + rng.uniform(-0.25, 0.25)))
    return (crust, algae, tip, 1.0)


def bezier(p0, p1, p2, p3, t):
    u = 1.0 - t
    return p0 * (u * u * u) + p1 * (3.0 * u * u * t) + p2 * (3.0 * u * t * t) + p3 * (t * t * t)


def tube(m, pts, radii, sides, uv2, rng, colour=None, lumpy=0.0, cap0=True, cap1=True):
    shift = rng.uniform(-0.3, 0.12)    # (each root is crusted to its own height)
    """A closed tube along `pts` (parallel-transported rings), capped at both ends. Lumpy below the waterline."""
    n = len(pts)
    tangents = []
    for i in range(n):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, n - 1)]
        tangents.append((b - a).normalized())
    t0 = tangents[0]
    ref = UP if abs(t0.y) < 0.9 else Vector((1.0, 0.0, 0.0))
    normal = t0.cross(ref).normalized()
    rings = []
    spin = rng.uniform(0.0, TAU)
    for i in range(n):
        t = tangents[i]
        normal = (normal - t * normal.dot(t)).normalized()
        other = t.cross(normal)
        ring = []
        for c in range(sides):
            a = TAU * c / sides + spin
            r = radii[i]
            p = pts[i] + (normal * math.cos(a) + other * math.sin(a)) * r
            if lumpy > 0.0 and p.y < 0.05:
                p = pts[i] + (normal * math.cos(a) + other * math.sin(a)) * r * (1.0 + rng.uniform(0.0, lumpy))
            ring.append(m.dab(p, colour(p, i / (n - 1)) if colour else crust_of(p, rng, 0.0, shift)))
        rings.append(ring)
    for i in range(n - 1):
        axis = (pts[i] + pts[i + 1]) * 0.5
        for c in range(sides):
            d = (c + 1) % sides
            quad = (rings[i][c], rings[i][d], rings[i + 1][d], rings[i + 1][c])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, middle - axis, [(0.0, 0.0)] * 4, uv2, True)
    for end, ring, sign, cap in ((0, rings[0], -1.0, cap0), (n - 1, rings[-1], 1.0, cap1)):
        if not cap:
            continue
        t = tangents[end]
        tip = m.dab(pts[end] + t * sign * radii[end] * 0.4, colour(pts[end], end / (n - 1)) if colour else crust_of(pts[end], rng, 0.0, shift))
        for c in range(sides):
            tri = (ring[c], ring[(c + 1) % sides], tip)
            m.face(tri, t * sign, [(0.0, 0.0)] * 3, uv2, True)
    return rings


def wander_path(points, steps, rng, kink):
    """Points along a polyline, `steps` between each pair, with a small crooked wander."""
    out = []
    for k in range(len(points) - 1):
        a, b = points[k], points[k + 1]
        for s in range(steps):
            t = s / steps
            p = a.lerp(b, t)
            if 0 < k or s > 0:
                p += Vector((rng.uniform(-kink, kink), rng.uniform(-kink, kink) * 0.4, rng.uniform(-kink, kink)))
            out.append(p)
    out.append(points[-1].copy())
    return out


# ---------------------------------------------------------------------------------------------------------------
# One tree (or one root cluster), as a plan first (so that the full and light pieces are the same tree)

def make_root(rng, start, out, land_at, r0, group, fork_chance=0.4):
    """A prop root from `start`, arching out along `out` and down into the mud at `land_at` (x, z)."""
    end = Vector((land_at.x, MUD - BURIED, land_at.z))
    drop = start.y - end.y
    reach = (end - start) * Vector((1.0, 0.0, 1.0))
    p1 = start + reach * rng.uniform(0.3, 0.45) + UP * rng.uniform(0.05, 0.3)
    p2 = end + UP * drop * rng.uniform(0.3, 0.72) - out * rng.uniform(-0.1, 0.3)
    return {"p": (start, p1, p2, end), "r": r0, "group": group,
            "fork": rng.random() < fork_chance, "fork_at": rng.uniform(0.55, 0.72),
            "fork_side": rng.choice((-1.0, 1.0)) * rng.uniform(0.16, 0.32), "fork_out": rng.uniform(0.15, 0.4)}


def add_pods_and_litter(plan, rng, pods_count, floating, on_mud, mud_pods, litter_r, mud_r):
    pods = []
    for i in range(pods_count):
        cl = rng.choice(plan["clumps"])
        a = rng.uniform(0.0, TAU)
        d = rng.uniform(0.2, 0.7)
        top = cl["c"] + Vector((math.cos(a) * cl["r"].x * d, -cl["r"].y * 0.75 * (1.0 - 0.45 * d * d) * 0.92, math.sin(a) * cl["r"].z * d))
        pods.append({"top": top, "long": rng.uniform(0.22, 0.34), "r": rng.uniform(0.012, 0.017),
                     "tilt": Vector((rng.uniform(-0.12, 0.12), 0.0, rng.uniform(-0.12, 0.12)))})
    plan["pods"] = pods
    litter = []
    for i in range(floating):
        a = rng.uniform(0.0, TAU)
        d = rng.uniform(0.35, 1.05) * litter_r
        litter.append({"at": Vector((math.cos(a) * d, -0.01, math.sin(a) * d)), "kind": FLOATING, "turn": rng.uniform(0.0, TAU)})
    for i in range(on_mud):
        a = rng.uniform(0.0, TAU)
        d = rng.uniform(0.2, 1.0) * mud_r
        litter.append({"at": Vector((math.cos(a) * d, MUD + 0.008, math.sin(a) * d)), "kind": MUDLEAF, "turn": rng.uniform(0.0, TAU)})
    plan["litter"] = litter
    plan["mud_pods"] = []
    for i in range(mud_pods):
        a = rng.uniform(0.0, TAU)
        d = rng.uniform(0.3, 1.0) * mud_r
        plan["mud_pods"].append({"at": Vector((math.cos(a) * d, MUD + 0.016, math.sin(a) * d)), "turn": rng.uniform(0.0, TAU)})


def plan_tree(seed, spread, tall, clusters):
    rng = random.Random(seed)
    k = spread / 4.0
    plan = {"spread": spread, "tall": tall, "young": False}
    # The trunk: its foot above the water, crooked up to where it forks.
    foot = rng.uniform(0.4, 0.8)
    fork = 0.38 * tall
    lean = Vector((rng.uniform(-0.25, 0.25), 0.0, rng.uniform(-0.25, 0.25))) * k
    trunk = [Vector((0.0, foot, 0.0)), Vector((lean.x * 0.4, foot + (fork - foot) * 0.45, lean.z * 0.4)), Vector((lean.x, fork, lean.z))]
    plan["trunk"] = trunk
    plan["trunk_r"] = 0.09 + 0.035 * spread

    def trunk_at(h):
        if h <= trunk[1].y:
            return trunk[0].lerp(trunk[1], (h - trunk[0].y) / (trunk[1].y - trunk[0].y))
        return trunk[1].lerp(trunk[2], min(1.0, (h - trunk[1].y) / (trunk[2].y - trunk[1].y)))

    # The limbs: crooked, out and up from the fork to the canopy's clumps.
    canopy_r = 0.55 * spread + 0.4
    limbs = []
    clumps = []
    n_limbs = 3 + (spread > 4.5) + rng.randint(0, 1)
    first = rng.uniform(0.0, TAU)
    for i in range(n_limbs):
        a = first + TAU * i / n_limbs + rng.uniform(-0.35, 0.35)
        out = Vector((math.cos(a), 0.0, math.sin(a)))
        reach = canopy_r * rng.uniform(0.45, 0.75)
        top = tall - rng.uniform(0.9, 1.5)
        end = trunk[2] + out * reach + UP * (top - trunk[2].y)
        mid = trunk[2].lerp(end, 0.5) + out * reach * 0.15 + Vector((rng.uniform(-0.2, 0.2), -0.15, rng.uniform(-0.2, 0.2)))
        limbs.append({"pts": [trunk[2].copy(), mid, end], "r": plan["trunk_r"] * 0.62, "out": out})
        clumps.append({"c": end + UP * 0.2, "r": Vector((rng.uniform(0.85, 1.25), rng.uniform(0.55, 0.75), rng.uniform(0.85, 1.25))) * k ** 0.5})
    # Fill the dome: a ring of clumps round the edge, lower, and one on top.
    ring = 4 + int(spread)
    for i in range(ring):
        a = first + TAU * (i + 0.5) / ring + rng.uniform(-0.2, 0.2)
        out = Vector((math.cos(a), 0.0, math.sin(a)))
        c = trunk[2] + out * canopy_r * rng.uniform(0.72, 0.9) + UP * (tall - 1.6 - rng.uniform(0.0, 0.5) - trunk[2].y)
        clumps.append({"c": c, "r": Vector((rng.uniform(0.8, 1.1), rng.uniform(0.5, 0.7), rng.uniform(0.8, 1.1))) * k ** 0.5})
    clumps.append({"c": trunk[2] + UP * (tall - 0.8 - trunk[2].y) + lean * 0.5, "r": Vector((1.2, 0.7, 1.2)) * k ** 0.5})
    plan["limbs"] = limbs
    plan["clumps"] = clumps

    # The prop roots, in clusters with open water between.
    roots = []
    n_roots = 12 + int(4.0 * spread)
    per = [n_roots // clusters + (1 if i < n_roots % clusters else 0) for i in range(clusters)]
    centre = rng.uniform(0.0, TAU)
    half = 0.24 * (5.0 / max(clusters, 1)) ** 0.3
    for g in range(clusters):
        a0 = centre + TAU * g / clusters + rng.uniform(-0.15, 0.15)
        for j in range(per[g]):
            a = a0 + (j / max(per[g] - 1, 1) - 0.5) * 2.0 * half + rng.uniform(-0.05, 0.05)
            out = Vector((math.cos(a), 0.0, math.sin(a)))
            # (where it leaves the tree: the trunk's foot, higher up the trunk, or a limb)
            pick = rng.random()
            if pick < 0.2:
                limb = min(limbs, key=lambda l: (l["out"] - out).length)
                start = limb["pts"][0].lerp(limb["pts"][1], rng.uniform(0.5, 0.9))
                r0 = limb["r"] * 0.55
            else:
                h = rng.uniform(foot, foot + 0.25) if pick < 0.4 else rng.uniform(foot + 0.2, min(trunk[2].y, 2.6))
                start = trunk_at(h) + out * plan["trunk_r"] * 0.5
                r0 = (0.045 + 0.01 * spread) * rng.uniform(0.85, 1.15)
            land = spread * 0.5 * rng.uniform(0.6, 1.0)
            roots.append(make_root(rng, start, out, out * land, r0, g))
    plan["roots"] = roots

    # Hanging aerial roots, from the limbs: they never reach the mud.
    hanging = []
    for i in range(5 + int(1.5 * spread)):
        limb = rng.choice(limbs)
        t = rng.uniform(0.35, 0.95)
        p = limb["pts"][1].lerp(limb["pts"][2], (t - 0.5) * 2.0) if t > 0.5 else limb["pts"][0].lerp(limb["pts"][1], t * 2.0)
        hanging.append({"top": p, "bottom": rng.uniform(-1.2, 0.8), "r": rng.uniform(0.016, 0.026),
                        "bend": Vector((rng.uniform(-0.25, 0.25), 0.0, rng.uniform(-0.25, 0.25)))})
    plan["hanging"] = hanging
    add_pods_and_litter(plan, rng, 8 + int(2 * spread), 10 + int(spread), 8 + int(spread), 3, canopy_r, spread * 0.5)
    plan["own"] = rng.random()
    plan["seed"] = seed
    return plan


def along_line(points, t):
    """The point a fraction `t` of the way along a polyline (by length)."""
    lengths = [(points[i + 1] - points[i]).length for i in range(len(points) - 1)]
    goal = t * sum(lengths)
    for i, l in enumerate(lengths):
        if goal <= l or i == len(lengths) - 1:
            return points[i].lerp(points[i + 1], min(goal / max(l, 1e-6), 1.0))
        goal -= l
    return points[-1].copy()


def plan_bough(seed, length, clusters):
    """A root cluster: a low crooked bough lying along x just over the water, sagging in the middle and rising at both
    ends into small leafy crowns, with prop roots arching down from it to both sides (a bank's fringe)."""
    rng = random.Random(seed)
    plan = {"spread": length, "tall": 0.0, "young": True}
    half = length * 0.5
    ys = (1.75, 1.35, 1.2, 1.3, 1.85)
    line = []
    for i, y in enumerate(ys):
        x = -half + length * i / (len(ys) - 1)
        line.append(Vector((x + rng.uniform(-0.1, 0.1), y + rng.uniform(-0.08, 0.08), rng.uniform(-0.22, 0.22))))
    plan["trunk"] = line
    plan["trunk_r"] = 0.075
    limbs = []
    clumps = []
    for at, lift in ((line[0], 0.45), (line[2], 0.95), (line[-1], 0.45)):
        end = at + UP * lift + Vector((rng.uniform(-0.2, 0.2), 0.0, rng.uniform(-0.2, 0.2)))
        limbs.append({"pts": [at.copy(), at.lerp(end, 0.5) + Vector((rng.uniform(-0.08, 0.08), 0.0, rng.uniform(-0.08, 0.08))), end],
                      "r": 0.045, "out": Vector((0.0, 0.0, 1.0))})
        clumps.append({"c": end + UP * 0.15, "r": Vector((rng.uniform(0.6, 0.75), rng.uniform(0.38, 0.48), rng.uniform(0.6, 0.75)))})
    plan["limbs"] = limbs
    plan["clumps"] = clumps
    plan["tall"] = max(c["c"].y + c["r"].y for c in clumps)
    roots = []
    n = rng.randint(12, 15)
    for i in range(n):
        # (each cluster keeps to the middle of its stretch of the bough, leaving open water between)
        seg = min(i * clusters // n, clusters - 1)
        first_i = -(-seg * n // clusters)
        last_i = -(-(seg + 1) * n // clusters) - 1
        frac = (i - first_i + 0.5) / max(last_i - first_i + 1, 1)
        t = (seg + 0.2 + 0.6 * frac + rng.uniform(-0.03, 0.03)) / clusters
        t = 0.06 + 0.88 * t
        side = 1.0 if (i % 2 == 0) == (rng.random() < 0.8) else -1.0
        start = along_line(line, t)
        out = Vector((rng.uniform(-0.3, 0.3) + (t - 0.5) * 0.8, 0.0, side)).normalized()
        land = rng.uniform(0.9, 1.4)
        land_at = start + out * land
        roots.append(make_root(rng, start, out, land_at, rng.uniform(0.032, 0.042), seg * 2 + (1 if side > 0 else 0), 0.3))
    plan["roots"] = roots
    hanging = []
    for i in range(3):
        top = along_line(line, rng.uniform(0.15, 0.85))
        hanging.append({"top": top, "bottom": rng.uniform(-0.9, 0.6), "r": rng.uniform(0.014, 0.02),
                        "bend": Vector((rng.uniform(-0.2, 0.2), 0.0, rng.uniform(-0.2, 0.2)))})
    plan["hanging"] = hanging
    add_pods_and_litter(plan, rng, 3, 4, 4, 1, half + 0.5, half)
    plan["own"] = rng.random()
    plan["seed"] = seed
    return plan


def root_points(root, steps):
    p0, p1, p2, p3 = root["p"]
    return [bezier(p0, p1, p2, p3, i / steps) for i in range(steps + 1)]


def root_radii(root, steps):
    return [root["r"] * (1.25 - 0.45 * (i / steps)) for i in range(steps + 1)]


def fork_points(root, steps):
    """A fork: leaves the root near the water and goes down beside it into the mud, a little to one side."""
    p0, p1, p2, p3 = root["p"]
    t = root["fork_at"]
    start = bezier(p0, p1, p2, p3, t)
    out = Vector((p3.x, 0.0, p3.z)).normalized()
    side = Vector((-out.z, 0.0, out.x))
    end = p3 + side * root["fork_side"] + out * root["fork_out"]
    end.y = MUD - BURIED
    # (it leaves along its parent, then bends away: no kink where they part)
    along = (bezier(p0, p1, p2, p3, t + 0.02) - start).normalized()
    mid1 = start + along * 0.35
    mid2 = end + UP * (start.y - end.y) * 0.45
    return [bezier(start, mid1, mid2, end, i / steps) for i in range(steps + 1)]


def build(plan, low):
    m = Mesh()
    rng = random.Random(plan["seed"] * 7 + (1 if low else 0))
    own = plan["own"]
    wood = (WOOD, own)
    # The trunk and limbs.
    trunk_pts = wander_path(plan["trunk"], 1 if low else 3, rng, 0.0 if low else 0.035)
    rs = [plan["trunk_r"] * (1.15 - 0.3 * i / (len(trunk_pts) - 1)) for i in range(len(trunk_pts))]
    tube(m, trunk_pts, rs, 4 if low else 8, wood, rng)
    for limb in plan["limbs"]:
        pts = wander_path(limb["pts"], 1 if low else 3, rng, 0.0 if low else 0.04)
        rs = [limb["r"] * (1.0 - 0.55 * i / (len(pts) - 1)) for i in range(len(pts))]
        tube(m, pts, rs, 3 if low else 6, wood, rng)
    # The prop roots, and their forks.
    steps = 4 if low else 10
    for root in plan["roots"]:
        tube(m, root_points(root, steps), root_radii(root, steps), 3 if low else 6, wood, rng, lumpy=0.0 if low else 0.22)
        if root["fork"] and not low:
            pts = fork_points(root, 6)
            rs = [root["r"] * 0.75 * (1.0 - 0.3 * i / 6) for i in range(7)]
            tube(m, pts, rs, 5, wood, rng, lumpy=0.22)
    # Hanging aerial roots.
    if not low:
        for h in plan["hanging"]:
            top = h["top"]
            pts = []
            n = 6
            for i in range(n + 1):
                t = i / n
                pts.append(Vector((top.x + h["bend"].x * t * t, top.y + (h["bottom"] - top.y) * t, top.z + h["bend"].z * t * t)))
            rs = [h["r"] * (1.0 - 0.35 * i / n) for i in range(n + 1)]
            bottom = h["bottom"]
            tube(m, pts, rs, 4, wood, rng,
                 colour=lambda p, t: (crust_of(p, rng)[0], crust_of(p, rng)[1], smooth(bottom + 0.35, bottom + 0.02, p.y), 1.0))
    # The canopy: clumps.
    for i, cl in enumerate(plan["clumps"]):
        # (the full piece: a dark core inside a shell of leaf cards; the light one: its core and a few big cards)
        clump(m, cl, (CLUMP, (own + i * 0.137) % 1.0), rng, 0 if low else 1, 1.0 if low else 0.84)
        cards(m, cl, rng, own, i, low)
    if not low:
        for pod in plan["pods"]:
            make_pod(m, pod["top"], pod["top"] + pod["tilt"] - UP * pod["long"], pod["r"], rng)
        for pod in plan["mud_pods"]:
            a = pod["turn"]
            along = Vector((math.cos(a), 0.0, math.sin(a)))
            make_pod(m, pod["at"] - along * 0.14, pod["at"] + along * 0.14 + UP * 0.002, 0.014, rng)
        for leaf in plan["litter"]:
            fallen_leaf(m, leaf, rng)
    return m


def clump(m, cl, uv2, rng, subdiv, grow):
    """A lumpy ellipsoid of leaves: an icosahedron (once divided for the full piece), jittered."""
    t = (1.0 + 5.0 ** 0.5) / 2.0
    verts = [Vector(v).normalized() for v in (
        (-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t),
        (0, -1, -t), (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1))]
    faces = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6),
             (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10),
             (8, 6, 7), (9, 8, 1)]
    for _ in range(subdiv):
        cache = {}
        new_faces = []

        def mid(a, b):
            key = (min(a, b), max(a, b))
            if key not in cache:
                verts.append((verts[a] + verts[b]).normalized())
                cache[key] = len(verts) - 1
            return cache[key]
        for a, b, c in faces:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            new_faces += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        faces = new_faces
    centre = cl["c"]
    r = cl["r"] * grow
    idx = []
    for v in verts:
        bump = 1.0 + rng.uniform(-0.12, 0.12)
        # (flatter underneath: a canopy's clumps sag less below than they bulge above)
        under = 0.75 if v.y < 0.0 else 1.0
        p = centre + Vector((v.x * r.x, v.y * r.y * under, v.z * r.z)) * bump
        idx.append(m.dab(p, (0.0, 0.0, 0.0, 1.0)))
    for a, b, c in faces:
        tri = (idx[a], idx[b], idx[c])
        middle = sum((m.verts[q] for q in tri), Vector()) / 3.0
        m.face(tri, middle - centre, [(0.0, 0.0)] * 3, uv2, True)


def cards(m, cl, rng, own, which, low):
    """Leaf cards in a shell round a clump, facing out and up (two-sided sheets) and overlapping, so that what is seen
    is leaves, not the clump."""
    centre = cl["c"]
    r = cl["r"]
    area = 4.0 * math.pi * (r.x * r.y + r.y * r.z + r.x * r.z) / 3.0
    count = int(area * 1.1) if low else int(area * 6.5)
    for i in range(count):
        # (a direction over the clump: all round, fewer underneath)
        while True:
            d = Vector((rng.gauss(0, 1), rng.gauss(0, 1), rng.gauss(0, 1))).normalized()
            if d.y > -0.75 or rng.random() < 0.5:
                break
        under = 0.75 if d.y < 0.0 else 1.0
        at = centre + Vector((d.x * r.x, d.y * r.y * under, d.z * r.z)) * rng.uniform(0.9, 1.06)
        normal = (Vector((d.x / r.x, d.y / r.y, d.z / r.z)).normalized() + UP * 0.35
                  + Vector((rng.uniform(-0.5, 0.5), rng.uniform(-0.3, 0.3), rng.uniform(-0.5, 0.5)))).normalized()
        side = normal.cross(UP if abs(normal.y) < 0.95 else Vector((1.0, 0.0, 0.0))).normalized()
        other = normal.cross(side)
        a = rng.uniform(0.0, TAU)
        u = side * math.cos(a) + other * math.sin(a)
        v = normal.cross(u)
        half = rng.uniform(0.5, 0.62) if low else rng.uniform(0.26, 0.36)
        # (bent a little along one way, so a card is not flat)
        corners = [at - u * half - v * half, at + u * half - v * half, at + u * half + v * half, at - u * half + v * half]
        corners = [p + normal * (0.05 * ((p - at).dot(u) / half) ** 2) for p in corners]
        ids = [m.dab(p, (0.0, 0.0, 0.0, 1.0)) for p in corners]
        tag = (CARD, (own * 3.1 + which * 0.31 + i * 0.0731) % 1.0)
        m.face(ids, normal, [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)], tag, False)


def make_pod(m, top, tip, r, rng):
    """A propagule: a long slender cigar, swelling a little below its stalk, pointed at the tip (five-sided)."""
    along = (tip - top)
    n = 4
    pts = [top + along * (i / n) for i in range(n + 1)]
    rs = [r * s for s in (0.45, 1.0, 1.0, 0.8, 0.35)]
    rings = []
    t = along.normalized()
    ref = UP if abs(t.y) < 0.9 else Vector((1.0, 0.0, 0.0))
    side = t.cross(ref).normalized()
    other = t.cross(side)
    tag = (POD, rng.random())
    for i in range(n + 1):
        ring = []
        for c in range(5):
            a = TAU * c / 5.0
            ring.append((m.dab(pts[i] + (side * math.cos(a) + other * math.sin(a)) * rs[i]), i / n))
        rings.append(ring)
    for i in range(n):
        axis = (pts[i] + pts[i + 1]) * 0.5
        for c in range(5):
            d = (c + 1) % 5
            quad = (rings[i][c][0], rings[i][d][0], rings[i + 1][d][0], rings[i + 1][c][0])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            v0, v1 = i / n, (i + 1) / n
            m.face(quad, middle - axis, [(0.5, 1.0 - v0), (0.5, 1.0 - v0), (0.5, 1.0 - v1), (0.5, 1.0 - v1)], tag, True)
    cap_top = m.dab(top - t * r * 0.3)
    cap_tip = m.dab(tip + t * r * 1.4)
    for c in range(5):
        d = (c + 1) % 5
        m.face((rings[0][c][0], rings[0][d][0], cap_top), -t, [(0.5, 1.0)] * 3, tag, True)
        m.face((rings[-1][c][0], rings[-1][d][0], cap_tip), t, [(0.5, 0.0)] * 3, tag, True)


def fallen_leaf(m, leaf, rng):
    """One leaf lying flat (floating just under the surface, or on the mud): a card the shader cuts to an oval."""
    a = leaf["turn"]
    u = Vector((math.cos(a), 0.0, math.sin(a)))
    v = Vector((-u.z, 0.0, u.x))
    long, wide = rng.uniform(0.055, 0.07), rng.uniform(0.028, 0.035)
    at = leaf["at"]
    corners = [at - u * long - v * wide, at + u * long - v * wide, at + u * long + v * wide, at - u * long + v * wide]
    ids = [m.dab(p) for p in corners]
    m.face(ids, UP, [(0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)], (leaf["kind"], rng.random()), False)


# ---------------------------------------------------------------------------------------------------------------
# The spheres that fill each cluster of roots under the water (for a game that keeps fish out with spheres)

def spheres_of(plan):
    groups = {}
    for root in plan["roots"]:
        pts = root_points(root, 24)
        if root["fork"]:
            pts += fork_points(root, 12)
        for p in pts:
            if MUD - 0.1 <= p.y <= 0.0:
                groups.setdefault(root["group"], []).append((p, root["r"]))
    spheres = []
    owners = []
    for g, pts in sorted(groups.items()):
        bands = 4
        for b in range(bands):
            top = -b * (-MUD / bands)
            bottom = -(b + 1) * (-MUD / bands)
            some = [(p, r) for p, r in pts if bottom - 0.05 <= p.y <= top + 0.05]
            if not some:
                continue
            c = sum((p for p, _ in some), Vector()) / len(some)
            radius = max((p - c).length + r * 1.2 for p, r in some)
            spheres.append([c, radius])
            owners.append(g)
    # Leave room for a fish between clusters: shrink any two that come too close.
    for _ in range(40):
        moved = False
        for i in range(len(spheres)):
            for j in range(i + 1, len(spheres)):
                if owners[i] == owners[j]:
                    continue
                gap = (spheres[i][0] - spheres[j][0]).length - spheres[i][1] - spheres[j][1]
                if gap < FISH_GAP:
                    need = (FISH_GAP - gap) * 0.5 + 0.001
                    spheres[i][1] -= need
                    spheres[j][1] -= need
                    moved = True
        if not moved:
            break
    # How much of the roots under the water is inside them.
    inside = 0
    total = 0
    for root in plan["roots"]:
        for p in root_points(root, 24):
            if MUD <= p.y <= 0.0:
                total += 1
                if any((p - c).length <= r + 0.02 for c, r in spheres):
                    inside += 1
    least = min(((spheres[i][0] - spheres[j][0]).length - spheres[i][1] - spheres[j][1])
                for i in range(len(spheres)) for j in range(i + 1, len(spheres)) if owners[i] != owners[j]) if len(set(owners)) > 1 else 99.0
    return [(c.x, c.y, c.z, max(r, 0.1)) for c, r in spheres], owners, inside / max(total, 1), least


# ---------------------------------------------------------------------------------------------------------------

def to_blender(p):
    """Godot (x, y up, z) to Blender (x, y, z up): the glTF exporter turns it back."""
    return (p.x, -p.z, p.y)


def to_object(name, m):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_blender(v) for v in m.verts], [], [f[0] for f in m.faces])
    # (every layer made first, then each looked up by name: making one moves the others)
    mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.new(name="UV2")
    mesh.color_attributes.new(name="Color", type="FLOAT_COLOR", domain="POINT")
    first = mesh.uv_layers["UVMap"].data
    second = mesh.uv_layers["UV2"].data
    for poly, (idx, uvs, uv2) in zip(mesh.polygons, m.faces):
        for corner, loop in enumerate(poly.loop_indices):
            first[loop].uv = (uvs[corner][0], 1.0 - uvs[corner][1])
            second[loop].uv = (uv2[0], 1.0 - uv2[1])
        poly.use_smooth = True
    colour = mesh.color_attributes["Color"].data
    for i, c in enumerate(m.colours):
        colour[i].color = c
    mesh.color_attributes.active_color = mesh.color_attributes["Color"]
    mesh.color_attributes.render_color_index = mesh.color_attributes.find("Color")
    material = bpy.data.materials.get("mangrove") or bpy.data.materials.new("mangrove")
    material.use_nodes = True
    mesh.materials.append(material)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def winding(name, m, obj):
    mesh = obj.data
    wrong = 0
    for poly, told in zip(mesh.polygons, m.told):
        n = poly.normal
        back = Vector((n.x, n.z, -n.y))
        if back.dot(told) <= 0.0:
            wrong += 1
    sheets = sum(1 for c in m.closed if not c)
    print("WINDING %s: %s: %d of %d faces against the way they were told to face (%d of them two-sided sheets), %d triangles"
          % (name, "ok" if wrong == 0 else "INSIDE OUT", wrong, len(mesh.polygons), sheets, m.triangles()))


def export_one(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", export_yup=True, use_selection=True,
        export_animations=False, export_texcoords=True, export_normals=True,
        export_vertex_color="ACTIVE",
    )


PIECES = [
    # name, seed, root spread (m), canopy top above the water (m), root clusters, young
    ("a", 11, 3.0, 3.6, 4, False),
    ("b", 23, 4.0, 4.4, 5, False),
    ("c", 37, 5.0, 5.2, 5, False),
    ("d", 41, 6.0, 6.0, 6, False),
    # (a root cluster: the length of its bough, the height is worked out, clusters along the bough on each side)
    ("roots_a", 53, 2.8, 0.0, 2, True),
    ("roots_b", 67, 3.4, 0.0, 3, True),
]


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    os.makedirs(MODELS, exist_ok=True)
    objects = []
    shapes = []
    for name, seed, spread, tall, clusters, young in PIECES:
        plan = plan_bough(seed, spread, clusters) if young else plan_tree(seed, spread, tall, clusters)
        spheres, owners, covered, least = spheres_of(plan)
        print("SPHERES mangrove_%s: %d spheres, %.0f%% of the roots under the water inside them, least gap between clusters %.2f m"
              % (name, len(spheres), covered * 100.0, least))
        shapes.append((name, spheres, owners))
        for low in (False, True):
            full_name = "mangrove_%s%s" % (name, "_lo" if low else "")
            m = build(plan, low)
            obj = to_object(full_name, m)
            winding(full_name, m, obj)
            export_one(obj, os.path.join(MODELS, full_name + ".glb"))
            obj.location.x = len(objects) * 7.0
            objects.append(obj)
    with open(SHAPES, "w", newline="\n") as f:
        f.write("## Written by tools/build_mangrove.py (do not edit: build again). For each piece, the spheres\n")
        f.write("## (x, y, z, radius, in the piece's own space at size 1) that roughly fill its root tangles under\n")
        f.write("## the water, with room for a 0.3 m fish between clusters.\n\n")
        f.write("const SPHERES := {\n")
        for name, spheres, owners in shapes:
            f.write('\t"%s": [\n' % name)
            for s in spheres:
                f.write("\t\tVector4(%.3f, %.3f, %.3f, %.3f),\n" % s)
            f.write("\t],\n")
        f.write("}\n\n")
        f.write("## Which cluster of roots each of those spheres fills (spheres of one cluster may touch; of two, never).\n")
        f.write("const CLUSTERS := {\n")
        for name, spheres, owners in shapes:
            f.write('\t"%s": [%s],\n' % (name, ", ".join(str(o) for o in owners)))
        f.write("}\n")
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "mangrove.blend"))
    print("BUILT mangrove")


if __name__ == "__main__":
    main()
