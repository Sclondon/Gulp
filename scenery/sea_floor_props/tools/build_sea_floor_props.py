"""Builds the sea floor kit: rocks, shelf cliffs, coral bommies, cold-water reef life and tropical
corals (models/sea_floor_props.glb, models/sea_floor_props_lo.glb, models/sea_floor_props.json).

Run from anywhere (Blender 4.3):
    blender --background --factory-startup --python build_sea_floor_props.py

Writes, beside this folder: ../models/sea_floor_props.glb (every piece, full), ../models/
sea_floor_props_lo.glb (every piece, low; objects named <name>_lo), ../models/sea_floor_props.json
(for each piece: its group, which material it takes, its size, its triangle counts, tints, and for
rocks, cliffs and bommies the spheres that roughly fill it), and sea_floor_props.blend (editable:
the pieces stand in rows; only their meshes are read by Godot, so where an object stands does not
matter).

Everything here is worked out in GODOT's space (metres, +Y up, a piece's base at y = 0) and turned
into Blender's (+Z up) only where points are made: to_b(). That is a turn, not a mirror image, so
nothing is turned inside out by it.

How the pieces are made:
- Rocks, cliffs and bommies: fractured blocks (balls cut by random planes) are joined into one skin
  by a voxel remesh, pushed about by noise (lumps, cracks, strata), cut flat underneath, thinned by
  a Decimate modifier (full and low), and painted by point: crevices dark (rays cast from each
  point), crusts of growth by noise.
- Living things: tubes, lathed shapes, balls and shells put together point by point (class Kit).
  The alpha of a point's colour is how far it sways (the soft shader reads it).

Inside-out checks (printed as WINDING lines): every closed part of every mesh must have a positive
volume (a part with a negative one is turned over and counted), and for rocks a ray from every
triangle along its normal must leave the skin an even number of times.
"""

import json
import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector, noise
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "models")
TAU = math.tau
INFO = {}
FULL = []
LOW = []


# ----------------------------------------------------------------------------- small helpers

def to_b(p):
    return Vector((p[0], -p[2], p[1]))


def to_g(p):
    return Vector((p[0], p[2], -p[1]))


def lin(c):
    """A colour as it is written into the mesh. Godot's shaders (ALBEDO = COLOR.rgb) show a point's
    colour as they show a material's albedo_color, so colours picked by eye go in as they are."""
    return tuple(c)


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def mul(a, k):
    return tuple(min(1.0, x * k) for x in a)


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def smooth(a, b, x):
    t = clamp((x - a) / (b - a))
    return t * t * (3.0 - 2.0 * t)


def fbm(p, octaves=3):
    total, amp = 0.0, 1.0
    for _ in range(octaves):
        total += amp * noise.noise(p)
        p = p * 2.03 + Vector((7.1, 3.3, 5.7))
        amp *= 0.5
    return total


def unit(rng):
    while True:
        v = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)))
        if 0.05 < v.length < 1.0:
            return v.normalized()


def perp(d):
    ref = Vector((0, 1, 0)) if abs(d.y) < 0.9 else Vector((1, 0, 0))
    return d.cross(ref).normalized()


_ICO = {}


def ico(subdiv):
    if subdiv not in _ICO:
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
        bm.verts.index_update()
        _ICO[subdiv] = ([v.co.normalized() for v in bm.verts], [[v.index for v in f.verts] for f in bm.faces])
        bm.free()
    return _ICO[subdiv]


def islands(bm):
    bm.faces.ensure_lookup_table()
    seen = set()
    out = []
    for face in bm.faces:
        if face.index in seen:
            continue
        stack = [face]
        seen.add(face.index)
        group = []
        while stack:
            f = stack.pop()
            group.append(f)
            for v in f.verts:
                for g in v.link_faces:
                    if g.index not in seen:
                        seen.add(g.index)
                        stack.append(g)
        out.append(group)
    return out


def volume_of(faces):
    total = 0.0
    for f in faces:
        vs = [v.co for v in f.verts]
        for i in range(1, len(vs) - 1):
            total += vs[0].dot(vs[i].cross(vs[i + 1]))
    return total / 6.0


def fix_winding(bm, name):
    """Every closed part must have a positive volume: one that has not is turned over."""
    bm.faces.index_update()
    flipped = 0
    opened = 0
    parts = islands(bm)
    for part in parts:
        closed = all(len(e.link_faces) == 2 for f in part for e in f.edges)
        if not closed:
            opened += 1
            continue
        if volume_of(part) < 0.0:
            flipped += 1
            for f in part:
                f.normal_flip()
    bm.normal_update()
    still = sum(1 for part in islands(bm) if volume_of(part) < 0.0)
    return len(parts), flipped, opened, still


def odd_rays(bm):
    """How many triangles a ray along the normal says face inward (rocks: one skin)."""
    tree = BVHTree.FromBMesh(bm)
    wrong = []
    rng = random.Random(1)
    for f in bm.faces:
        if f.calc_area() < 1e-7:
            continue
        votes = 0
        # (three rays a little apart: one alone can run along an edge and count it twice or not at all)
        for _ in range(3):
            ray = (f.normal + unit(rng) * 0.25).normalized()
            at = f.calc_center_median() + f.normal * 1e-4
            hits = 0
            for _ in range(60):
                hit = tree.ray_cast(at, ray)
                if hit[0] is None:
                    break
                hits += 1
                at = hit[0] + ray * 1e-4
            votes += hits % 2
        if votes >= 2:
            wrong.append(f)
    return wrong


def finish(name, bm, low, sharp=42.0):
    """A bmesh (Blender space, colours in layer Col) becomes an object; smooth but for sharp edges."""
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    limit = math.radians(sharp)
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        e.smooth = not (len(e.link_faces) == 2 and e.calc_face_angle(0.0) > limit)
    # (a triangle turned far from the smooth normals round it keeps its own, or it would be lit from behind)
    bm.normal_update()
    for f in bm.faces:
        if f.normal.dot(sum((v.normal for v in f.verts), Vector())) <= 1.0:
            for e in f.edges:
                e.smooth = False
    mesh = bpy.data.meshes.new(name + ("_lo" if low else ""))
    bm.to_mesh(mesh)
    mesh.color_attributes.active_color = mesh.color_attributes["Col"]
    mesh.color_attributes.render_color_index = mesh.color_attributes.find("Col")
    obj = bpy.data.objects.new(mesh.name, mesh)
    bpy.context.collection.objects.link(obj)
    (LOW if low else FULL).append(obj)
    # (as Godot will read it: no triangle may face against the normals at its own corners)
    against = 0
    for poly in mesh.polygons:
        total = Vector()
        for i in poly.loop_indices:
            total += mesh.corner_normals[i].vector
        if poly.area > 1e-9 and poly.normal.dot(total) <= 0.0:
            against += 1
    if against:
        print("WINDING %s: INSIDE OUT: %d triangles face against the normals at their corners" % (mesh.name, against))
    return obj, len(mesh.polygons)


def bounds(bm):
    lo = Vector((1e9, 1e9, 1e9))
    hi = -lo
    for v in bm.verts:
        g = to_g(v.co)
        for i in range(3):
            lo[i] = min(lo[i], g[i])
            hi[i] = max(hi[i], g[i])
    return lo, hi


def note(name, group, kind, bm, tris, low, tints=None, spheres=None):
    lo, hi = bounds(bm)
    if not low:
        INFO[name] = {
            "group": group, "material": kind,
            "size": [round(hi[i] - lo[i], 3) for i in range(3)],
            "low": [round(lo[i], 3) for i in range(3)],
            "tris": tris, "tris_lo": 0,
            "tints": [list(t) for t in (tints or [(1.0, 1.0, 1.0)])],
            "spheres": spheres or [],
        }
    else:
        INFO[name]["tris_lo"] = tris


# ----------------------------------------------------------------------------- the kit of parts

class Kit:
    """Points with a colour and a sway, and faces, in Godot's space; `xf` moves what is added."""

    def __init__(self):
        self.pts = []
        self.cols = []
        self.faces = []
        self.xf = Matrix.Identity(4)

    def v(self, p, c, a=0.0):
        self.pts.append(self.xf @ Vector(p))
        l = lin(c)
        self.cols.append((l[0], l[1], l[2], clamp(a)))
        return len(self.pts) - 1

    def rings(self, rings, pole0=None, pole1=None):
        for r0, r1 in zip(rings[:-1], rings[1:]):
            n = len(r0)
            for k in range(n):
                self.faces.append((r0[k], r1[k], r1[(k + 1) % n], r0[(k + 1) % n]))
        if pole0 is not None:
            r = rings[0]
            for k in range(len(r)):
                self.faces.append((pole0, r[k], r[(k + 1) % len(r)]))
        if pole1 is not None:
            r = rings[-1]
            for k in range(len(r)):
                self.faces.append((pole1, r[(k + 1) % len(r)], r[k]))

    def tube(self, path, radii, sides, col, sway=None, up=None, flat=1.0, round1=0.0):
        """A closed tube along `path`. radii: a number or (across, up) for each point. col(f, k)."""
        n = len(path)
        rings = []
        side = None
        t = Vector((0, 1, 0))
        for i, p in enumerate(path):
            t = (path[min(i + 1, n - 1)] - path[max(i - 1, 0)]).normalized()
            if up is not None:
                side = t.cross(up)
                side = side.normalized() if side.length > 1e-6 else Vector((1, 0, 0))
            elif side is None:
                side = perp(t)
            else:
                side = side - t * side.dot(t)
                side = side.normalized() if side.length > 1e-6 else perp(t)
            u = side.cross(t)
            r = radii[i]
            rx, ry = r if isinstance(r, tuple) else (r, r)
            f = i / (n - 1)
            ring = []
            for k in range(sides):
                a = TAU * k / sides
                s = math.sin(a)
                pt = p + side * (rx * math.cos(a)) + u * (ry * s * (flat if s < 0.0 else 1.0))
                ring.append(self.v(pt, col(f, k), sway(f) if sway else 0.0))
            rings.append(ring)
        p0 = self.v(path[0], col(0.0, 0), sway(0.0) if sway else 0.0)
        p1 = self.v(path[-1] + t * round1, col(1.0, 0), sway(1.0) if sway else 0.0)
        self.rings(rings, p0, p1)

    def cone(self, base, tip, r, sides, col0, col1, sway0=0.0, sway1=0.0):
        """A closed cone: a ring of `sides` points round `base`, a point at `tip`."""
        t = (tip - base).normalized()
        side = perp(t)
        u = side.cross(t)
        ring = [self.v(base + (side * math.cos(TAU * k / sides) + u * math.sin(TAU * k / sides)) * r, col0, sway0)
                for k in range(sides)]
        self.rings([ring], self.v(base, col0, sway0), self.v(tip, col1, sway1))

    def ball(self, subdiv, fn):
        """A ball: fn(direction) gives (point, colour, sway)."""
        dirs, faces = ico(subdiv)
        base = len(self.pts)
        for d in dirs:
            p, c, a = fn(d)
            self.v(p, c, a)
        for f in faces:
            self.faces.append(tuple(base + i for i in f))

    def lathe(self, profile, sides, col, sway=None, shape=None):
        """Turned about +Y. profile: (radius, y) points; a radius of 0 at either end is a pole.
        col(i, k), sway(i), shape(point, i, k) -> point."""
        rings = []
        poles = [None, None]
        for i, (r, y) in enumerate(profile):
            a_ = sway(i) if sway else 0.0
            if r <= 0.0 and i in (0, len(profile) - 1):
                p = Vector((0, y, 0))
                poles[0 if i == 0 else 1] = self.v(shape(p, i, 0) if shape else p, col(i, 0), a_)
                continue
            ring = []
            for k in range(sides):
                a = TAU * k / sides
                p = Vector((r * math.cos(a), y, r * math.sin(a)))
                ring.append(self.v(shape(p, i, k) if shape else p, col(i, k), a_))
            rings.append(ring)
        self.rings(rings, poles[0], poles[1])

    def valve(self, R, dome, na, nt, half, ribs, rib_amp, wave, col_out, col_in):
        """One shell valve: its hinge at the origin, fanning out along +Y, bulging to +Z."""
        def at(i, j, inner):
            a = -half + 2.0 * half * i / na
            t = j / nt
            w = a / half
            rr = R * (1.0 - 0.12 * w * w) * (1.0 + wave * math.cos(ribs * math.pi * w) * t)
            rib = 1.0 + rib_amp * math.cos(ribs * math.pi * w) * t
            z = dome * math.sin(math.pi * t ** 0.75) ** 0.6 * (1.0 - 0.8 * w ** 4) * rib
            if inner:
                z *= 0.72
            return Vector((math.sin(a) * rr * t, math.cos(a) * rr * t, z))
        umbo = self.v((0, 0, 0), col_out(0.5, 0.0))
        out = [[None] * (nt + 1) for _ in range(na + 1)]
        inn = [[None] * (nt + 1) for _ in range(na + 1)]
        for i in range(na + 1):
            for j in range(1, nt + 1):
                out[i][j] = self.v(at(i, j, False), col_out(i / na, j / nt))
                edge = i in (0, na) or j == nt
                inn[i][j] = out[i][j] if edge else self.v(at(i, j, True), col_in(i / na, j / nt))
        for i in range(na):
            self.faces.append((umbo, out[i][1], out[i + 1][1]))
            self.faces.append((umbo, inn[i + 1][1], inn[i][1]))
            for j in range(1, nt):
                self.faces.append((out[i][j], out[i][j + 1], out[i + 1][j + 1], out[i + 1][j]))
                self.faces.append((inn[i][j], inn[i + 1][j], inn[i + 1][j + 1], inn[i][j + 1]))

    def bmesh(self):
        bm = bmesh.new()
        layer = bm.verts.layers.float_color.new("Col")
        made = []
        for p, c in zip(self.pts, self.cols):
            v = bm.verts.new(to_b(p))
            v[layer] = c
            made.append(v)
        for f in self.faces:
            try:
                bm.faces.new([made[i] for i in f])
            except ValueError:
                pass
        bm.normal_update()
        return bm


def life(name, group, kind, make, tints=None, sharp=55.0):
    for low in (False, True):
        kit = Kit()
        make(kit, low)
        bm = kit.bmesh()
        parts, flipped, opened, still = fix_winding(bm, name)
        obj, tris = finish(name, bm, low, sharp)
        note(name, group, kind, bm, tris, low, tints)
        print("WINDING %s%s: %s: %d closed parts, %d turned over by the build, %d open, %d still inside out; tris=%d" % (
            name, "_lo" if low else "", "ok" if opened == 0 and still == 0 else "INSIDE OUT", parts, flipped, opened, still, tris))
        bm.free()


# ----------------------------------------------------------------------------- rock

def chunk(bm, centre, radii, seed, planes=12, boxy=False, cut=(0.72, 1.0), rot=None, extra=()):
    """A ball cut by random planes: a fractured block with flat faces."""
    rng = random.Random(seed)
    cuts = list(extra)
    if boxy:
        for axis in range(3):
            for sign in (-1.0, 1.0):
                n = Vector((0, 0, 0))
                n[axis] = sign
                n = (n + unit(rng) * 0.1).normalized()
                cuts.append((n, rng.uniform(0.63, 0.77)))
    for _ in range(planes):
        cuts.append((unit(rng), rng.uniform(*cut)))
    made = bmesh.ops.create_icosphere(bm, subdivisions=5, radius=1.0)
    centre = Vector(centre)
    for v in made["verts"]:
        d = v.co.normalized()
        r = min(1.22, min(h / max(d.dot(n), 1e-4) for n, h in cuts))
        p = Vector((d.x * radii[0], d.y * radii[1], d.z * radii[2])) * r
        if rot is not None:
            p = rot @ p
        v.co = to_b(centre + p)


def block(bm, centre, half, seed, planes=7, tilt=0.1):
    rng = random.Random(seed * 31 + 5)
    rot = Matrix.Rotation(rng.uniform(-tilt, tilt), 3, unit(rng))
    chunk(bm, centre, (half[0] / 0.7, half[1] / 0.7, half[2] / 0.7), seed, planes=planes, boxy=True,
          cut=(0.8, 1.1), rot=rot)


def apply_mod(obj, kind, **props):
    mod = obj.modifiers.new("m", kind)
    for key, value in props.items():
        setattr(mod, key, value)
    graph = bpy.context.evaluated_depsgraph_get()
    graph.update()
    mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(graph))
    obj.modifiers.remove(mod)
    return mesh


def cut_flat(bm, co, no):
    """Cuts away what is on the side `no` points to (Godot space) and closes the hole."""
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5, plane_co=to_b(co), plane_no=to_b(no), clear_outer=True)
    edges = [e for e in bm.edges if e.is_boundary]
    if edges:
        bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    # (a hole whose rim touches itself is left by holes_fill: filled with triangles instead)
    edges = [e for e in bm.edges if e.is_boundary]
    if edges:
        bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=edges)


ROCK = {
    "a": (0.40, 0.36, 0.31), "b": (0.29, 0.29, 0.30), "c": (0.47, 0.40, 0.30),
    "pink": (0.86, 0.52, 0.54), "mauve": (0.68, 0.42, 0.50), "pale": (0.84, 0.82, 0.72),
    "turf": (0.30, 0.34, 0.20), "silt": (0.62, 0.57, 0.45),
}
CORALS = [(0.93, 0.78, 0.22), (0.92, 0.45, 0.62), (0.58, 0.42, 0.88), (0.40, 0.78, 0.48), (0.96, 0.56, 0.20),
          (0.30, 0.58, 0.92), (0.85, 0.30, 0.30), (0.75, 0.85, 0.35)]


def paint_rock(bm, grain, style, height, seeds):
    layer = bm.verts.layers.float_color.new("Col")
    tree = BVHTree.FromBMesh(bm)
    rng = random.Random(3)
    rays = []
    while len(rays) < 14:
        d = unit(rng)
        if d.z > 0.15:
            rays.append(d)
    reach = grain * 0.3
    f = 1.0 / grain
    for v in bm.verts:
        n = v.normal
        # how shut in the point is: rays over the half of the sky its skin faces
        side = n.cross(Vector((0, 0, 1)) if abs(n.z) < 0.9 else Vector((1, 0, 0))).normalized()
        up = side.cross(n)
        shut = 0.0
        start = v.co + n * (grain * 0.004)
        for d in rays:
            ray = side * d.x + up * (-d.y) + n * d.z
            hit = tree.ray_cast(start, ray, reach)
            if hit[0] is not None:
                shut += 1.0 - hit[3] / reach
        shut /= len(rays)
        g = to_g(v.co)
        p = v.co * f
        crack = max(0.0, 1.0 - abs(noise.noise(p * 2.2 + Vector((11, 5, 3)))) / 0.07)
        open_ = 1.0 - smooth(0.1, 0.5, shut)
        if style == "bommie":
            c = mix((0.80, 0.76, 0.64), (0.64, 0.60, 0.52), 0.5 + 0.5 * noise.noise(p * 1.7))
            c = mix(c, ROCK["pink"], smooth(0.1, 0.35, noise.noise(p * 2.6 + Vector((3, 9, 1)))) * 0.7 * open_)
            c = mix(c, (0.38, 0.42, 0.24), smooth(0.2, 0.5, noise.noise(p * 3.1 + Vector((8, 1, 6)))) * 0.6)
            c = mix(c, (0.95, 0.5, 0.15), smooth(0.42, 0.55, noise.noise(p * 5.0 + Vector((1, 7, 4)))))
            c = mix(c, (0.6, 0.3, 0.75), smooth(0.45, 0.58, noise.noise(p * 5.5 + Vector((6, 2, 9)))))
            best = None
            for at, r, colour, kind in seeds:
                d = (g - at).length / r
                if d < 1.12 and (best is None or d < best[0]):
                    best = (d, at, r, colour, kind)
            if best is not None:
                d, at, r, colour, kind = best
                q = (g - at) / r
                if kind == 0:   # a brain head: winding ridges
                    ridge = smooth(0.0, 0.16, abs(noise.noise(q * 5.5 + at)))
                    cc = mix(mul(colour, 0.45), colour, ridge)
                elif kind == 1:   # a smooth head speckled with polyps
                    cc = mix(colour, mul(colour, 1.35), rng.random() * 0.7)
                else:   # a plate: pale at its rim
                    cc = mix(colour, (0.97, 0.95, 0.85), smooth(0.75, 1.05, d))
                c = mix(c, cc, 1.0 - smooth(1.0, 1.12, d))
            c = mul(c, 1.0 - 0.6 * smooth(0.12, 0.6, shut))
            c = mix(c, (0.80, 0.76, 0.62), 1.0 - smooth(0.0, 0.07 * height, g.y))
        else:
            c = mix(ROCK["a"], ROCK["b"], 0.5 + 0.6 * noise.noise(p * 1.3))
            c = mix(c, ROCK["c"], smooth(0.15, 0.5, noise.noise(p * 2.1 + Vector((4, 4, 4)))) * 0.7)
            c = mul(c, 0.82 + 0.3 * rng.random())
            deep = 1.0
            if style == "cliff":
                deep = smooth(0.25, 0.85, g.y / height)
                c = mix(mix(c, (0.24, 0.27, 0.33), 0.55), c, deep)
            pink = smooth(0.08, 0.32, noise.noise(p * 2.4 + Vector((3, 9, 1)))) * open_
            c = mix(c, mix(ROCK["pink"], ROCK["mauve"], 0.5 + 0.5 * noise.noise(p * 6.0)), pink * 0.85 * (0.25 + 0.75 * deep))
            turf = smooth(0.25, 0.55, noise.noise(p * 3.3 + Vector((8, 1, 6)))) * smooth(0.3, 0.8, n.z)
            c = mix(c, ROCK["turf"], turf * 0.7 * deep)
            pale = smooth(0.3, 0.42, noise.noise(p * 5.2 + Vector((1, 7, 4)))) * open_ * (0.4 + 0.6 * rng.random())
            c = mix(c, ROCK["pale"], pale * 0.85)
            if style == "cliff":   # pale sediment lying on the ledges
                c = mix(c, ROCK["silt"], smooth(0.75, 0.95, n.z) * 0.6)
            c = mul(c, 1.0 - 0.62 * smooth(0.12, 0.65, shut))
            if style == "rock":
                c = mul(c, 1.0 - 0.6 * crack)
            if style == "rock":
                c = mix(c, ROCK["silt"], (1.0 - smooth(0.0, 0.06 * height + 0.04, g.y)) * 0.8)
        l = lin(c)
        v[layer] = (l[0], l[1], l[2], 1.0)
    return tree


def fill_spheres(bm, tree, count, least, cliff=None):
    """Spheres (Godot space) that roughly fill the piece, biggest first, each inside its skin."""
    lo, hi = bounds(bm)
    front = tree
    if cliff:
        wide, tall = cliff
        keep = bmesh.new()
        for f in bm.faces:
            g = [to_g(v.co) for v in f.verts]
            if all(abs(p.z) < 0.02 for p in g) or all(abs(abs(p.x) - wide) < 0.02 for p in g) or all(p.y < lo.y + 0.02 for p in g):
                continue
            keep.faces.new([keep.verts.new(v.co) for v in f.verts])
        front = BVHTree.FromBMesh(keep)
        lo = Vector((-wide, lo.y, -7.0))
    step = max(hi.x - lo.x, hi.y - lo.y, hi.z - lo.z) / 26.0
    cands = []
    solid = 0
    x = lo.x + step * 0.5
    while x < hi.x:
        y = lo.y + step * 0.5
        while y < hi.y:
            z = lo.z + step * 0.5
            while z < hi.z:
                g = Vector((x, y, z))
                b = to_b(g)
                near = tree.find_nearest(b)
                inside = True
                for ray in (Vector((0.13, 0.21, 0.97)).normalized(), Vector((0.94, -0.29, 0.17)).normalized()):
                    hits = 0
                    start = b
                    for _ in range(60):
                        hit = tree.ray_cast(start, ray)
                        if hit[0] is None:
                            break
                        hits += 1
                        start = hit[0] + ray * 1e-4
                    inside = inside and hits % 2 == 1
                if cliff:
                    if inside or z < 0.0:
                        d = front.find_nearest(b)[3]
                        d = min(d, 6.0, tall - y if z < 0.0 else 99.0, cliff[0] - abs(x) + 1.5, y - lo.y + 1.5)
                        cands.append((d, g, inside))
                elif inside:
                    cands.append((near[3], g, True))
                solid += 1 if inside else 0
                z += step
            y += step
        x += step
    cands.sort(key=lambda c: -c[0])
    out = []
    for d, g, _ in cands:
        if len(out) >= count or d < least:
            break
        if all((g - Vector(s[:3])).length > s[3] * 0.92 for s in out):
            out.append((g.x, g.y, g.z, d * 1.12))
    covered = sum(1 for d, g, inside in cands if inside and any((g - Vector(s[:3])).length < s[3] for s in out))
    return [[round(x, 3) for x in s] for s in out], covered / max(1, solid)


def rock(name, group, make, size, tris, tris_lo, grain=None, style="rock", cuts=(), sink=None, spheres=8,
         least=None, cliff=None, seeds=(), seed=1, rough=1.0, voxels=70, hole=None):
    grain = grain or size
    bm = bmesh.new()
    make(bm)
    mesh = bpy.data.meshes.new(name + "_blocks")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name + "_work", mesh)
    bpy.context.collection.objects.link(obj)
    skin = apply_mod(obj, "REMESH", mode="VOXEL", voxel_size=size / voxels)
    bm = bmesh.new()
    bm.from_mesh(skin)
    bm.normal_update()
    f = 1.0 / grain
    off = Vector((seed * 3.7, seed * 1.3, seed * 2.9))
    for v in bm.verts:
        p = v.co * f + off
        push = grain * 0.03 * fbm(p * 3.2) + grain * 0.012 * noise.noise(p * 11.0)
        crack = max(0.0, 1.0 - abs(noise.noise(v.co * f * 2.2 + Vector((11, 5, 3)))) / 0.07)
        if style == "bommie":
            push = grain * 0.03 * fbm(p * 3.0) - grain * 0.03 * smooth(0.45, 0.6, noise.noise(p * 7.0))
        elif style == "cliff":
            push *= 0.6
            layer_ = (v.co.z + grain * 0.1 * noise.noise(p * 1.5)) / (grain * 0.11)
            push += grain * 0.014 * (layer_ - math.floor(layer_) - 0.5)
        else:
            push -= grain * 0.045 * crack
            layer_ = (v.co.z + grain * 0.1 * noise.noise(p * 1.5)) / (grain * 0.11)
            push += grain * 0.014 * (layer_ - math.floor(layer_) - 0.5)
        v.co += v.normal * push * rough
    sink = sink if sink is not None else min(0.3, size * 0.06)
    for co, no in list(cuts) + [((0, -sink, 0), (0, -1, 0))]:
        cut_flat(bm, co, no)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    if not cliff:   # stand it over its own middle
        lo, hi = bounds(bm)
        shift = to_b(Vector((-(lo.x + hi.x) * 0.5, 0, -(lo.z + hi.z) * 0.5)))
        for v in bm.verts:
            v.co += shift
        seeds = [(at + to_g(shift), r, c, k) for at, r, c, k in seeds]
    bm.to_mesh(skin)
    bm.free()
    obj.data = skin
    for low, want in ((False, tris), (True, tris_lo)):
        made = apply_mod(obj, "DECIMATE", decimate_type="COLLAPSE", ratio=min(1.0, want / len(skin.polygons)))
        bm = bmesh.new()
        bm.from_mesh(made)
        parts_ = sorted(islands(bm), key=len)
        small = [f_ for part in parts_[:-1] for f_ in part]   # (crumbs the remesh left loose)
        if small:
            bmesh.ops.delete(bm, geom=small, context="FACES")
            bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
        bm.normal_update()
        parts, flipped, opened, still = fix_winding(bm, name)
        # (thinning can fold a sliver of skin over on itself)
        bmesh.ops.dissolve_degenerate(bm, dist=1e-4, edges=bm.edges[:])
        bmesh.ops.triangulate(bm, faces=[f_ for f_ in bm.faces if len(f_.verts) > 3])
        bm.normal_update()
        for _ in range(12):
            folded = odd_rays(bm) + [f_ for f_ in bm.faces if f_.normal.dot(sum((v.normal for v in f_.verts), Vector())) <= 0.2]
            if not folded:
                break
            # (each folded sliver is closed up: the two ends of its shortest edge become one point)
            done = set()
            for f_ in folded:
                if not f_.is_valid:
                    continue
                edge = min(f_.edges, key=lambda e: e.calc_length())
                a, b = edge.verts
                if a in done or b in done:
                    continue
                done.update((a, b))
                bmesh.ops.pointmerge(bm, verts=[a, b], merge_co=(a.co + b.co) * 0.5)
            bmesh.ops.dissolve_degenerate(bm, dist=1e-4, edges=bm.edges[:])
            bm.normal_update()
            bm.faces.index_update()
        odd = len(odd_rays(bm)) + sum(1 for f_ in bm.faces if f_.normal.dot(sum((v.normal for v in f_.verts), Vector())) <= 0.0)
        lo, hi = bounds(bm)
        tree = paint_rock(bm, grain, style, hi.y, seeds)
        balls, share = None, 0.0
        if not low:
            balls, share = fill_spheres(bm, tree, spheres, least or size * 0.07, cliff)
            if hole is not None:
                # the way through (along z, at the height `hole`): how wide the skin leaves it, and the spheres
                def crossings(p):
                    hits = 0
                    ray = Vector((0.13, 0.21, 0.97)).normalized()
                    at = to_b(p)
                    for _ in range(60):
                        hit = tree.ray_cast(at, ray)
                        if hit[0] is None:
                            break
                        hits += 1
                        at = hit[0] + ray * 1e-4
                    return hits
                gaps = [x * 0.05 for x in range(-40, 41) if crossings(Vector((x * 0.05, hole, 0))) % 2 == 0]
                free = [x for x in gaps if all((Vector((x, hole, 0)) - Vector(s[:3])).length > s[3] for s in balls)]
                print("HOLE %s: %.2f m high, the way through is %.2f m wide in the skin (x %.2f to %.2f) and %.2f m wide between the spheres" % (
                    name, hole, len(gaps) * 0.05, min(gaps), max(gaps), len(free) * 0.05))
        obj2, count = finish(name, bm, low, 30.0)
        note(name, group, "rock", bm, count, low, None, balls)
        print("WINDING %s%s: %s: %d closed parts, %d turned over by the build, %d open, %d still inside out, %d triangles facing in by rays; tris=%d" % (
            name, "_lo" if low else "", "ok" if opened == 0 and still == 0 and odd == 0 else "INSIDE OUT", parts, flipped,
            opened, still, odd, count))
        if not low:
            print("SPHERES %s: %d, filling %.0f%% of it; size %s" % (name, len(balls), share * 100.0, INFO[name]["size"]))
        bm.free()
    bpy.data.objects.remove(obj)


def rocks():
    def small(bm):
        chunk(bm, (0, 0.14, 0), (0.30, 0.24, 0.27), 11, planes=10)
        chunk(bm, (0.13, 0.08, 0.1), (0.17, 0.15, 0.16), 12, planes=8)
    rock("rock_boulder_small", "rock", small, 0.55, 260, 70, spheres=5, seed=1, voxels=50)

    def boulder(bm):
        chunk(bm, (0, 0.38, 0), (0.72, 0.52, 0.62), 21)
        chunk(bm, (0.38, 0.22, 0.3), (0.42, 0.32, 0.36), 22, planes=9)
        chunk(bm, (-0.3, 0.18, -0.36), (0.36, 0.28, 0.32), 23, planes=9)
    rock("rock_boulder", "rock", boulder, 1.3, 600, 120, spheres=7, seed=2)

    def split(bm):
        chunk(bm, (-0.55, 0.72, 0), (0.80, 0.95, 0.9), 31, extra=[(Vector((1, 0.18, 0.12)).normalized(), 0.60)])
        chunk(bm, (0.62, 0.58, 0.05), (0.75, 0.80, 0.85), 32, extra=[(Vector((-1, -0.18, -0.12)).normalized(), 0.68)])
        chunk(bm, (0.2, 0.2, -0.75), (0.45, 0.32, 0.4), 33, planes=9)
    rock("rock_split", "rock", split, 2.0, 1100, 200, spheres=9, seed=3)

    def slab(bm):
        rot = Matrix.Rotation(math.radians(13.0), 3, "Z")
        chunk(bm, (0, 0.72, 0), (1.75 / 0.7, 0.3 / 0.7, 1.15 / 0.7), 41, planes=8, boxy=True, cut=(0.8, 1.1), rot=rot)
        chunk(bm, (1.0, 0.3, 0.15), (0.85, 0.62, 0.75), 42)
        chunk(bm, (-1.1, 0.1, -0.45), (0.6, 0.34, 0.5), 43, planes=9)
    rock("rock_slab", "rock", slab, 3.6, 1300, 240, spheres=12, least=0.16, seed=4)

    def stack(bm):
        block(bm, (0, 0.45, 0), (1.15, 0.65, 1.05), 51)
        block(bm, (0.12, 1.42, -0.06), (0.92, 0.5, 0.86), 52, tilt=0.16)
        block(bm, (-0.1, 2.2, 0.1), (0.76, 0.46, 0.7), 53, tilt=0.16)
        block(bm, (0.08, 2.86, 0), (0.5, 0.36, 0.5), 54, tilt=0.2)
        chunk(bm, (1.0, 0.25, 0.7), (0.6, 0.45, 0.5), 55, planes=9)
    rock("rock_stack", "rock", stack, 3.2, 1700, 300, spheres=10, seed=5)

    def ledge(bm):
        block(bm, (-1.5, 0.65, -0.6), (1.6, 0.95, 0.9), 61)
        block(bm, (1.3, 0.75, -0.7), (1.5, 1.05, 0.8), 62)
        block(bm, (0, 1.98, 0.1), (3.0, 0.48, 1.6), 63, planes=9, tilt=0.05)
        block(bm, (-1.2, 2.55, -0.5), (1.0, 0.32, 0.7), 64)
        chunk(bm, (2.6, 0.3, 0.6), (0.7, 0.5, 0.6), 65, planes=9)
    rock("rock_ledge", "rock", ledge, 6.0, 2600, 450, grain=3.5, spheres=16, least=0.25, seed=6, voxels=90)

    def pinnacle(bm):
        chunk(bm, (0, 0.9, 0), (1.5, 1.6, 1.4), 71)
        chunk(bm, (0.1, 2.4, 0), (1.15, 1.6, 1.1), 72)
        chunk(bm, (0.15, 3.9, 0.1), (0.85, 1.5, 0.8), 73)
        chunk(bm, (0.2, 5.1, 0.1), (0.5, 1.15, 0.5), 74, planes=9)
        chunk(bm, (-0.95, 0.8, 0.5), (0.9, 1.25, 0.8), 75)
    rock("rock_pinnacle", "rock", pinnacle, 6.0, 2400, 400, grain=3.5, spheres=12, least=0.22, seed=7, voxels=90)

    def arch(bm):
        chunk(bm, (-2.9, 1.2, 0), (1.5, 1.9, 1.6), 81)
        chunk(bm, (-2.75, 3.0, 0), (1.4, 1.5, 1.4), 82)
        chunk(bm, (2.9, 1.1, 0.1), (1.4, 1.8, 1.5), 83)
        chunk(bm, (2.8, 2.9, 0), (1.3, 1.5, 1.3), 84)
        block(bm, (0, 4.1, 0), (3.7, 0.75, 1.2), 85, planes=9, tilt=0.04)
        chunk(bm, (0.3, 4.65, 0), (2.0, 0.7, 1.1), 86)
        chunk(bm, (-3.9, 0.4, 0.9), (0.9, 0.7, 0.8), 87, planes=9)
    rock("rock_arch", "rock", arch, 8.0, 3600, 600, grain=4.0, spheres=18, least=0.28, seed=8, voxels=100, hole=1.5)
    # the arch's hole must stay open: nothing may reach the middle of it


CLIFF_WIDE = 12.0
CLIFF_TALL = 16.0


def cliffs():
    def wall(kind, seed):
        def make(bm):
            rng = random.Random(seed)
            made = bmesh.ops.create_cube(bm, size=1.0)
            for v in made["verts"]:
                v.co = to_b(Vector((v.co.x * 17.0, 7.5 + v.co.z * 19.0, 0.2 + v.co.y * 3.0)))
            y = -1.0
            row = 0
            while y < CLIFF_TALL + 0.5:
                h = rng.uniform(2.3, 4.4)
                spans = []
                x = -8.6 + rng.uniform(0.0, 1.2)
                while x < 8.6:
                    w = rng.uniform(2.8, 6.0)
                    spans.append((x, x + w))
                    x += w
                if kind == "crack":   # a chimney from top to bottom
                    at = 0.9 + 0.5 * math.sin(y * 0.3)
                    cut = []
                    for a, b in spans:
                        if a < at - 0.55 < b:
                            cut.append((a, at - 0.55))
                        if a < at + 0.55 < b:
                            cut.append((at + 0.55, b))
                        if b <= at - 0.55 or a >= at + 0.55:
                            cut.append((a, b))
                    spans = [s for s in cut if s[1] - s[0] > 0.5]
                mid = y + h * 0.5
                for a, b in spans:
                    cx = (a + b) * 0.5
                    out = rng.uniform(0.0, 1.4)
                    if kind == "ledges" and row in (1, 3):
                        out += 2.0
                    if kind == "overhang":
                        if mid > 10.5:
                            out += 2.3
                        elif mid > 5.5:
                            out = 0.1
                            if -3.5 < cx < 2.5:
                                continue
                    if kind == "buttress" and -4.4 < cx < -0.6:
                        out += 2.3 - 0.03 * mid
                    if kind == "crack" and abs(cx - 0.9) < 3.0:
                        out += 0.7
                    if abs(cx) > 5.6:   # the ends are alike on every piece, so that they meet
                        out = 0.6
                    front = 2.6 + out
                    block(bm, (cx, mid, (0.3 + front) * 0.5), ((b - a) * 0.5 * 0.93, h * 0.5 * 1.0, (front - 0.3) * 0.5),
                          rng.randint(0, 99999), tilt=0.13)
                y += h
                row += 1
        return make
    half = CLIFF_WIDE * 0.5 + 1.0
    cuts = [((half, 0, 0), (1, 0, 0)), ((-half, 0, 0), (-1, 0, 0)), ((0, CLIFF_TALL, 0), (0, 1, 0)), ((0, 0, 0), (0, 0, -1))]
    for i, kind in enumerate(("ledges", "crack", "overhang", "buttress")):
        rock("cliff_" + kind, "cliff", wall(kind, 100 + i), 16.0, 6000, 1100, grain=6.0, style="cliff", cuts=cuts, sink=0.5,
             spheres=30, least=0.6, cliff=(half, CLIFF_TALL), seed=20 + i, voxels=125)


def bommies():
    def head(name, size, parts, n_heads, n_plates, seed, tris, tris_lo, count):
        rng = random.Random(seed)
        seeds = []

        def make(bm):
            for i, (c, r) in enumerate(parts):
                chunk(bm, c, r, seed * 10 + i, planes=10, cut=(0.86, 1.02))
            for i in range(n_heads + n_plates):
                c, r = parts[rng.randrange(len(parts))]
                d = unit(rng)
                d.y = abs(d.y) * 0.9 + 0.1
                d.normalize()
                at = Vector(c) + Vector((d.x * r[0], d.y * r[1], d.z * r[2])) * 0.95
                colour = CORALS[(seed + i) % len(CORALS)]
                if i < n_heads:
                    rr = size * rng.uniform(0.07, 0.15)
                    chunk(bm, at, (rr, rr * 0.8, rr), seed * 100 + i, planes=3, cut=(0.92, 1.05))
                    seeds.append((at, rr, colour, i % 2))
                else:
                    rr = size * rng.uniform(0.12, 0.2)
                    at.y += rr * 0.2
                    chunk(bm, at + Vector((d.x, 0, d.z)) * rr * 0.5, (rr, rr * 0.16, rr), seed * 100 + i, planes=4, cut=(0.9, 1.05))
                    seeds.append((at + Vector((d.x, 0, d.z)) * rr * 0.5, rr, colour, 2))
        rock(name, "bommie", make, size, tris, tris_lo, style="bommie", spheres=count, seeds=seeds, seed=seed, rough=0.8,
             least=size * 0.05, voxels=80)
    head("bommie_small", 2.2, [((0, 0.6, 0), (1.1, 0.9, 1.0)), ((0.5, 0.35, 0.4), (0.7, 0.55, 0.6))], 7, 2, 3, 1500, 280, 8)
    head("bommie_mound", 3.2, [((0, 0.8, 0), (1.6, 1.2, 1.4)), ((-0.9, 0.5, 0.6), (1.0, 0.8, 0.9)), ((0.9, 1.3, -0.3), (0.9, 0.8, 0.8))],
         10, 3, 5, 2200, 380, 10)
    # (a tower: narrow at the waist, wide at the head, as a bommie that grew up to the light)
    head("bommie_tower", 4.0, [((0, 0.7, 0), (1.3, 1.0, 1.2)), ((0.1, 1.9, 0), (0.95, 1.1, 0.9)), ((0.15, 3.1, 0.05), (1.6, 0.95, 1.5)),
                               ((-0.8, 3.3, 0.5), (0.9, 0.6, 0.8))], 12, 4, 6, 3000, 500, 12)


# ----------------------------------------------------------------------------- living things

def grow(kit, rng, p, d, length, r, level, o):
    """A branch and its children. o: sides, segs, shrink, thin, kids, spread, up, bend, tip, round,
    col(level, f, last, y), sway(y)."""
    pts = [Vector(p)]
    dd = Vector(d).normalized()
    segs = 1 if level < o.get("twigs", 0) else o["segs"]
    for _ in range(segs):
        dd = (dd + unit(rng) * o["bend"] + Vector((0, o["up"], 0))).normalized()
        if "flat" in o:
            dd.z *= o["flat"]
            dd.normalize()
        pts.append(pts[-1] + dd * (length / segs))
    last = level == 0
    r1 = r * o["thin"] * (o["tip"] if last else 1.0)
    radii = [r + (r1 - r) * i / segs for i in range(segs + 1)]
    y0, y1 = pts[0].y, pts[-1].y
    if last and o.get("cone"):
        kit.cone(pts[0], pts[-1], r, o["sides"], o["col"](level, 0.0, last, y0), o["col"](level, 1.0, last, y1), o["sway"](y0), o["sway"](y1))
    else:
        kit.tube(pts, radii, o["sides"], lambda f, k: o["col"](level, f, last, y0 + (y1 - y0) * f),
                 sway=lambda f: o["sway"](y0 + (y1 - y0) * f), round1=r1 * o["round"] if last else 0.0)
    if last:
        if "end" in o:
            o["end"](pts[-1], dd)
        return
    n = 3 if rng.random() < o.get("third", -1.0) else rng.randint(*o["kids"])
    side = perp(dd)
    turn = rng.uniform(0, TAU)
    for j in range(n):
        if "flat" in o:
            a = (j - (n - 1) * 0.5) * o["spread"] * rng.uniform(0.8, 1.2) + rng.uniform(-0.1, 0.1)
            cd = Vector((dd.x * math.cos(a) + dd.y * math.sin(a), -dd.x * math.sin(a) + dd.y * math.cos(a), dd.z))
        else:
            tilt = o["spread"] * rng.uniform(0.6, 1.2)
            cd = dd * math.cos(tilt) + (Matrix.Rotation(turn + TAU * j / n + rng.uniform(-0.4, 0.4), 3, dd) @ side) * math.sin(tilt)
        grow(kit, rng, pts[-1], cd, length * o["shrink"] * rng.uniform(0.85, 1.1), r * o["thin"], level - 1, o)


def sea_fan(height, r0, base, tips, seed, levels, sway=0.7):
    def make(kit, low):
        rng = random.Random(seed)
        o = {"sides": 3, "segs": 1 if low else 2, "shrink": 0.86, "thin": 0.84 if not low else 0.9, "kids": (2, 2), "third": 0.0 if low else 0.06, "twigs": 3, "cone": not low,
             "spread": 0.46, "up": 0.1, "bend": 0.1, "tip": 0.6, "round": 1.0, "flat": 0.12,
             "col": lambda level, f, last, y: mix(mix(base, tips, clamp(y / height) ** 2), (1, 1, 1), 0.3 if rng.random() < 0.25 else 0.0),
             "sway": lambda y: sway * clamp(y / height) ** 1.5}
        grow(kit, rng, (0, -0.03, 0), (0, 1, 0), height * 0.19, r0 * (1.5 if low else 1.0), levels - (3 if low else 0), o)
    return make


def hydrocoral(kit, low):
    rng = random.Random(5)
    o = {"sides": 4 if low else 6, "segs": 1 if low else 2, "shrink": 0.78, "thin": 0.85, "kids": (2, 3), "spread": 0.7, "up": 0.25,
         "bend": 0.2, "tip": 0.85, "round": 0.9,
         "col": lambda level, f, last, y: mix((0.45, 0.22, 0.68), (0.80, 0.62, 0.92), (f if last else 0.0) * 0.9 + 0.1 * rng.random()),
         "sway": lambda y: 0.0}
    for i in range(3):
        a = TAU * i / 3 + 0.4
        grow(kit, rng, (math.cos(a) * 0.03, -0.02, math.sin(a) * 0.03), (math.cos(a) * 0.5, 1, math.sin(a) * 0.5), 0.1, 0.024,
             2 if low else 3, o)


def staghorn(kit, low):
    rng = random.Random(8)
    o = {"sides": 4 if low else 5, "segs": 1 if low else 2, "shrink": 0.82, "thin": 0.8, "kids": (2, 3), "spread": 0.6, "up": 0.3,
         "bend": 0.12, "tip": 0.35, "round": 1.5,
         "col": lambda level, f, last, y: mix((0.62, 0.62, 0.62), (1, 1, 1), (f if last else 0.0) ** 1.5) if not last or f > 0.3
         else (0.72, 0.72, 0.72),
         "sway": lambda y: 0.0}
    for i in range(4):
        a = TAU * i / 4 + rng.uniform(-0.3, 0.3)
        reach = 0.0 if i == 0 else 0.16
        grow(kit, rng, (math.cos(a) * reach, -0.03, math.sin(a) * reach), (math.cos(a) * 0.55, 1, math.sin(a) * 0.55), 0.26, 0.03,
             2 if low else 3, o)


def soft_coral(kit, low):
    rng = random.Random(13)

    def puff(at, d):
        r = rng.uniform(0.035, 0.05)
        seed = Vector((rng.uniform(0, 9), rng.uniform(0, 9), rng.uniform(0, 9)))
        tint = mix((0.95, 0.3, 0.6), (1.0, 0.55, 0.25), rng.random() * 0.6)
        kit.ball(1 if low else 2, lambda q: (at + d * r * 0.5 + q * r * (1.0 + 0.3 * noise.noise(q * 3.0 + seed)),
                                              mix(tint, (1.0, 0.85, 0.9), 0.4 * rng.random()), 0.75 * clamp(at.y / 0.5) ** 1.3))
    o = {"sides": 4 if low else 6, "segs": 2, "shrink": 0.7, "thin": 0.72, "kids": (2, 3), "spread": 0.75, "up": 0.3, "bend": 0.18,
         "tip": 0.8, "round": 0.5, "end": puff,
         "col": lambda level, f, last, y: mix((0.96, 0.82, 0.86), (0.98, 0.6, 0.72), clamp(y / 0.5)),
         "sway": lambda y: 0.75 * clamp(y / 0.5) ** 1.3}
    grow(kit, rng, (0, -0.03, 0), (0.05, 1, 0), 0.2, 0.045, 2 if low else 3, o)


def sea_rods(kit, low):
    rng = random.Random(17)
    for i in range(7):
        a = TAU * i / 7 + rng.uniform(-0.3, 0.3)
        reach = rng.uniform(0.02, 0.1)
        tall = rng.uniform(0.45, 0.9)
        base = mix((0.50, 0.36, 0.62), (0.70, 0.55, 0.40), rng.random())
        o = {"sides": 4 if low else 5, "segs": 2 if low else 4, "shrink": 0.75, "thin": 0.9, "kids": (2, 2), "spread": 0.3, "up": 0.5,
             "bend": 0.12, "tip": 0.8, "round": 1.0,
             "col": lambda level, f, last, y, base=base: mix(base, (1.0, 0.95, 0.8), 0.45 if rng.random() < 0.3 else 0.0),
             "sway": lambda y: 0.9 * clamp(y / 0.9) ** 1.6}
        grow(kit, rng, (math.cos(a) * reach, -0.03, math.sin(a) * reach), (math.cos(a) * 0.3, 1, math.sin(a) * 0.3), tall * 0.6, 0.02,
             1 if i % 2 == 0 else 0, o)


def pillar_coral(kit, low):
    rng = random.Random(21)
    for i in range(9):
        a = TAU * i / 8 + rng.uniform(-0.3, 0.3)
        reach = 0.0 if i == 8 else rng.uniform(0.1, 0.2)
        tall = rng.uniform(0.25, 0.5) + (0.25 if i == 8 else 0.0)
        r = rng.uniform(0.045, 0.065)
        lean = Vector((math.cos(a) * 0.12, 1, math.sin(a) * 0.12)).normalized()
        p0 = Vector((math.cos(a) * reach, -0.04, math.sin(a) * reach))
        n = 3 if low else 6
        pts = [p0 + lean * tall * j / n + Vector((noise.noise(Vector((i, j, 0.5))), 0, noise.noise(Vector((i, j, 7.5))))) * 0.02
               for j in range(n + 1)]
        radii = [r * (1.15 - 0.2 * j / n) * (1.0 + 0.12 * noise.noise(Vector((i * 3.1, j * 1.7, 2.0)))) for j in range(n + 1)]
        radii[-1] *= 0.75
        kit.tube(pts, radii, 5 if low else 8, lambda f, k: mul(mix((0.6, 0.6, 0.6), (1, 1, 1), f), 0.85 + 0.15 * rng.random()),
                 round1=r * 0.6)


def brain_coral(kit, low):
    R = 0.45
    seed = Vector((4.2, 1.7, 8.8))

    def at(d):
        groove = 1.0 - smooth(0.02, 0.13, abs(noise.noise(d * 3.4 + seed)))
        r = R * (1.0 + 0.06 * noise.noise(d * 1.6 + seed)) * (1.0 - 0.05 * groove)
        y = max(d.y, -0.3) * r * 0.8 + 0.3 * R * 0.8 - 0.05
        c = mix((1, 1, 1), (0.38, 0.38, 0.38), groove)
        return Vector((d.x * r, y, d.z * r)), mul(c, 0.55 + 0.45 * smooth(-0.3, 0.3, d.y)), 0.0
    kit.ball(3 if low else 5, at)


def table_coral(kit, low):
    rng = random.Random(27)
    R = 0.65

    def outline(a):
        return R * (1.0 + 0.14 * noise.noise(Vector((math.cos(a) * 1.3, math.sin(a) * 1.3, 3.0))))
    kit.lathe([(0, -0.05), (0.16, -0.05), (0.11, 0.12), (0.09, 0.3), (0, 0.3)], 5 if low else 8,
              lambda i, k: (0.5, 0.5, 0.5))
    profile = [(0, 0.27), (0.5, 0.29), (0.94, 0.35), (1.0, 0.385), (0.95, 0.41), (0.5, 0.365), (0, 0.345)]

    def shape(p, i, k):
        a = math.atan2(p.z, p.x)
        f = outline(a)
        wob = 0.02 * noise.noise(Vector((p.x * f * 4.0, p.z * f * 4.0, 1.0)))
        return Vector((p.x * f, p.y + wob, p.z * f))
    kit.lathe(profile, 10 if low else 22, lambda i, k: [(0.45,) * 3, (0.45,) * 3, (0.6,) * 3, (1, 1, 1), (1, 1, 1), (0.82,) * 3, (0.7,) * 3][i],
              shape=shape)
    if not low:   # the little branches standing on the table
        for _ in range(130):
            a = rng.uniform(0, TAU)
            t = math.sqrt(rng.random()) * 0.93
            f = outline(a) * t
            y = 0.345 + (0.365 - 0.345) * min(1.0, t / 0.5) + max(0.0, t - 0.5) / 0.45 * 0.045
            p = Vector((math.cos(a) * f, y - 0.008, math.sin(a) * f))
            h = rng.uniform(0.05, 0.09)
            lean = Vector((rng.uniform(-0.3, 0.3), 1, rng.uniform(-0.3, 0.3))).normalized()
            kit.cone(p, p + lean * h, 0.022, 3, (0.7, 0.7, 0.7), (1, 1, 1))


def barrel_sponge(kit, low):
    sides = 12 if low else 28
    profile = [(0, -0.06), (0.30, -0.06), (0.42, 0.2), (0.50, 0.6), (0.47, 0.92), (0.38, 1.1), (0.33, 1.14), (0.28, 1.1), (0.26, 0.75),
               (0.16, 0.4), (0, 0.34)]

    def shape(p, i, k):
        a = math.atan2(p.z, p.x)
        outer = 1.0 if i <= 5 else 0.0
        rib = 1.0 + outer * (0.07 * math.cos(a * 14.0 + 2.0 * noise.noise(Vector((p.y * 2.0, 0, 3.0))))
                             + 0.08 * noise.noise(Vector((p.x * 3.0, p.y * 3.0, p.z * 3.0))))
        return Vector((p.x * rib, p.y, p.z * rib))

    def col(i, k):
        a = TAU * k / sides
        if i >= 7:
            return (0.16, 0.08, 0.07)
        rib = 0.5 + 0.5 * math.cos(a * 14.0)
        return mix((0.42, 0.20, 0.17), (0.66, 0.36, 0.28), rib if i <= 5 else 0.6)
    kit.lathe(profile, sides, col, shape=shape)


def vase_sponge(kit, low):
    sides = 10 if low else 18
    profile = [(0, -0.04), (0.09, -0.04), (0.10, 0.12), (0.15, 0.3), (0.21, 0.46), (0.235, 0.58), (0.22, 0.6), (0.19, 0.56),
               (0.12, 0.34), (0.05, 0.16), (0, 0.13)]

    def shape(p, i, k):
        f = 1.0 + 0.12 * noise.noise(Vector((p.x * 5.0, p.y * 4.0, p.z * 5.0)))
        return Vector((p.x * f, p.y + (0.02 * math.sin(math.atan2(p.z, p.x) * 3.0) if 4 <= i <= 7 else 0.0), p.z * f))
    kit.lathe(profile, sides, lambda i, k: (0.33, 0.30, 0.24) if i >= 8 else mix((0.78, 0.72, 0.58), (0.93, 0.90, 0.78), i / 6.0),
              sway=lambda i: 0.12 * clamp(profile[i][1] / 0.6) ** 2, shape=shape)


def puffballs(kit, low):
    rng = random.Random(31)
    for at, r in (((0, 0.05, 0), 0.065), ((0.1, 0.035, 0.04), 0.048), ((-0.05, 0.03, 0.09), 0.04), ((-0.09, 0.025, -0.05), 0.034)):
        seed = Vector((rng.uniform(0, 9), rng.uniform(0, 9), rng.uniform(0, 9)))
        c = Vector(at)

        def fn(d, c=c, r=r, seed=seed):
            wart = noise.noise(d * 6.0 + seed)
            rr = r * (1.0 + 0.09 * wart)
            colour = mix((0.86, 0.38, 0.06), (1.0, 0.62, 0.16), 0.5 + 0.9 * wart)
            colour = mix(colour, (0.35, 0.12, 0.03), smooth(0.93, 0.99, d.y))
            return c + Vector((d.x * rr, d.y * rr * 0.9, d.z * rr)), colour, 0.0
        kit.ball(1 if low else 2, fn)


def green_anemone(kit, low):
    rng = random.Random(37)
    sides = 10 if low else 20

    def lumpy(p, i, k):
        f = 1.0 + (0.07 * noise.noise(Vector((p.x * 30.0, p.y * 30.0, p.z * 30.0))) if i < 4 else 0.0)
        return Vector((p.x * f, p.y, p.z * f))
    cols = [(0.22, 0.34, 0.2), (0.22, 0.34, 0.2), (0.26, 0.42, 0.22), (0.3, 0.5, 0.26), (0.25, 0.72, 0.42), (0.35, 0.86, 0.55),
            (0.16, 0.42, 0.3), (0.1, 0.25, 0.2)]
    kit.lathe([(0, -0.03), (0.085, -0.03), (0.08, 0.05), (0.095, 0.105), (0.11, 0.125), (0.07, 0.12), (0.02, 0.112), (0, 0.105)], sides,
              lambda i, k: cols[i], shape=lumpy)
    for ring, (reach, count) in enumerate(((0.105, 28), (0.086, 22), (0.066, 16)) if not low else ((0.1, 14), (0.075, 10))):
        for j in range(count):
            a = TAU * (j + 0.5 * ring) / count + rng.uniform(-0.05, 0.05)
            out = Vector((math.cos(a), 0, math.sin(a)))
            length = rng.uniform(0.065, 0.09) * (1.0 - 0.15 * ring)
            lean = 0.95 - 0.3 * ring + rng.uniform(-0.12, 0.12)
            p = out * reach + Vector((0, 0.118, 0))
            pts = [p]
            segs = 2 if low else 3
            for s in range(segs):
                tilt = lean + 0.35 * s / segs
                pts.append(pts[-1] + (out * math.sin(tilt) + Vector((0, math.cos(tilt), 0))) * (length / segs))
            radii = [0.0095 - 0.005 * s / segs for s in range(segs + 1)]
            kit.tube(pts, radii, 3 if low else 4, lambda f, k: mix((0.28, 0.74, 0.45), (0.66, 0.95, 0.80), f),
                     sway=lambda f: 0.3 * f, round1=0.004)


def strawberry(kit, low):
    rng = random.Random(41)

    def edge(a):
        return 0.26 * (1.0 + 0.22 * noise.noise(Vector((math.cos(a) * 1.2, math.sin(a) * 1.2, 9.0))))

    def shape(p, i, k):
        f = edge(math.atan2(p.z, p.x)) / 0.26
        return Vector((p.x * f, p.y, p.z * f))
    kit.lathe([(0, -0.03), (0.26, -0.03), (0.25, 0.0), (0.15, 0.012), (0, 0.016)], 8 if low else 16, lambda i, k: (0.62, 0.12, 0.2),
              shape=shape)
    placed = []
    want = 14 if low else 40
    tries = 0
    while len(placed) < want and tries < 4000:
        tries += 1
        a = rng.uniform(0, TAU)
        t = math.sqrt(rng.random())
        p = Vector((math.cos(a), 0, math.sin(a))) * edge(a) * t * 0.92
        if all((p - q).length > (0.1 if low else 0.06) for q in placed):
            placed.append(p)
    for p in placed:
        base = [(0.96, 0.32, 0.48), (0.88, 0.14, 0.18), (0.97, 0.48, 0.22), (0.98, 0.45, 0.6), (0.8, 0.5, 0.85)][rng.randrange(5)]
        r = rng.uniform(0.013, 0.018) * (1.3 if low else 1.0)
        h = rng.uniform(0.022, 0.034)
        kit.lathe([(0, 0.0), (r, 0.0), (r * 1.1, h), (r * 0.5, h * 0.92), (0, h * 0.85)], 5 if low else 7,
                  lambda i, k: [mul(base, 0.6), mul(base, 0.6), base, mul(base, 1.15), (1.0, 0.9, 0.9)][i],
                  sway=lambda i: 0.05 if i >= 2 else 0.0, shape=lambda q, i, k: q + p)
        count = 5 if low else 8
        for j in range(count):
            a = TAU * j / count + rng.uniform(-0.1, 0.1)
            out = Vector((math.cos(a), 0, math.sin(a)))
            start = p + out * r * 0.95 + Vector((0, h * 0.95, 0))
            tip = start + (out * 0.8 + Vector((0, 0.6, 0))) * rng.uniform(0.014, 0.02)
            kit.cone(start, tip, 0.0045, 3, base, (1.0, 0.97, 0.95), 0.04, 0.08)


def urchin(r, spine, base, tip, seed):
    def make(kit, low):
        rng = random.Random(seed)
        kit.ball(1 if low else 2, lambda d: (Vector((d.x * r, d.y * r * 0.7 + r * 0.55, d.z * r)), mul(base, 0.7), 0.0))
        count = 40 if low else 120
        for i in range(count):
            y = 1.0 - 1.45 * (i + 0.5) / count
            a = i * 2.39996
            flat = math.sqrt(max(0.0, 1.0 - y * y))
            d = (Vector((math.cos(a) * flat, y, math.sin(a) * flat)) + unit(rng) * 0.12).normalized()
            start = Vector((d.x * r * 0.9, d.y * r * 0.63 + r * 0.55, d.z * r * 0.9))
            length = spine * rng.uniform(0.75, 1.1)
            kit.cone(start, start + d * length, r * (0.11 if low else 0.075), 3, base, tip)
    return make


def sea_star(arm, width, high, webbed, seed):
    def make(kit, low):
        rng = random.Random(seed)
        if webbed:
            sides = 20 if low else 40

            def reach(a):
                return arm * (0.56 + 0.44 * abs(math.cos(2.5 * (a - 0.3))) ** 1.6)

            def shape(p, i, k):
                a = TAU * k / sides
                ridge = abs(math.cos(2.5 * (a - 0.3))) ** 3
                lift = (0.6 + 0.4 * ridge) if i >= 2 else 1.0
                return Vector((p.x * reach(a), p.y * high * lift, p.z * reach(a)))

            def tone(i, k):
                if i < 2:
                    return (0.72, 0.68, 0.62)
                a = TAU * k / sides
                return mul((1, 1, 1), 0.6 + 0.4 * smooth(-0.3, 0.3, noise.noise(Vector((math.cos(a) * i * 0.9, math.sin(a) * i * 0.9, seed)))))
            kit.lathe([(0, -0.3), (0.97, -0.3), (1.0, 0.0), (0.8, 0.45), (0.5, 0.8), (0.22, 1.0), (0, 1.05)], sides, tone, shape=shape)
            return
        segs = 3 if low else 7
        sides = 6 if low else 10
        for i in range(5):
            a = TAU * i / 5 + 0.3
            out = Vector((math.cos(a), 0, math.sin(a)))
            curl = rng.uniform(-0.25, 0.25) * (0.3 if webbed else 1.0)
            pts = []
            radii = []
            for s in range(segs + 1):
                t = s / segs
                turn = Matrix.Rotation(curl * t * t, 3, "Y")
                pts.append((turn @ out) * (arm * t * 0.97) + Vector((0, high * 0.3 - 0.01 - (0.4 * high * t * t), 0)))
                if webbed:
                    w = width * (1.0 - t) ** 1.25 + arm * 0.05
                else:
                    w = width * (1.0 - 0.72 * t ** 1.3)
                radii.append((w, high * (1.0 - 0.6 * t) * (0.75 if webbed else 1.0)))

            def col(f, k, a=a):
                top = math.sin(TAU * k / sides)
                if top < -0.1:
                    return (0.7, 0.66, 0.6)
                if webbed:   # mottled
                    return mul((1, 1, 1), 0.62 + 0.38 * smooth(-0.3, 0.3, noise.noise(Vector((f * 4.0 + a * 3.0, k * 0.9, seed)))))
                return (1.0, 1.0, 1.0) if rng.random() < 0.3 else (0.55, 0.55, 0.55)   # the pale net of spines
            kit.tube(pts, radii, sides, col, up=Vector((0, 1, 0)), flat=0.25, round1=arm * 0.03)
    return make


def scallop(kit, low):
    na, nt = (8, 3) if low else (18, 6)
    half = math.radians(62.0)

    def out(i, t):
        rib = 0.5 + 0.5 * math.cos(9.0 * math.pi * (i * 2.0 - 1.0))
        c = mix((0.60, 0.34, 0.24), (0.90, 0.62, 0.46), rib)
        return mix(c, (0.80, 0.52, 0.62), smooth(0.2, 0.5, noise.noise(Vector((i * 5.0, t * 5.0, 2.0)))))   # crusted, as rock scallops are
    inner = lambda i, t: (0.95, 0.9, 0.85)
    lay = Matrix.Rotation(math.radians(-90.0), 4, "X")   # the fan laid flat: its bulge up, its hinge to the back
    place = Matrix.Translation((0, 0.028, 0.07))
    kit.xf = place @ Matrix.Rotation(math.radians(20.0), 4, "X") @ lay
    kit.valve(0.15, 0.03, na, nt, half, 9, 0.22, 0.02, out, inner)
    kit.xf = place @ lay @ Matrix.Scale(-1.0, 4, (0, 0, 1))
    kit.valve(0.15, 0.035, na, nt, half, 9, 0.22, 0.02, out, inner)
    kit.xf = place @ Matrix.Rotation(math.radians(10.0), 4, "X") @ lay
    kit.valve(0.142, 0.012, na, nt, half, 9, 0.0, 0.02, lambda i, t: mix((0.75, 0.3, 0.05), (1.0, 0.55, 0.1), t),
              lambda i, t: mix((0.75, 0.3, 0.05), (1.0, 0.55, 0.1), t))
    kit.xf = Matrix.Identity(4)


def mussels(kit, low):
    rng = random.Random(47)
    count = 12 if low else 18
    for i in range(count):
        a = i * 2.39996
        t = math.sqrt((i + 0.5) / count)
        foot = Vector((math.cos(a) * 0.11 * t, -0.02 + 0.04 * (1.0 - t * t), math.sin(a) * 0.11 * t))
        axis = (Vector((math.cos(a) * t * 0.9, 1.0, math.sin(a) * t * 0.9)) + unit(rng) * 0.3).normalized()
        length = rng.uniform(0.09, 0.13)
        w = length * 0.33
        n = 3 if low else 5
        prof = [0.25, 0.75, 1.0, 0.95, 0.7, 0.4] if not low else [0.3, 0.9, 0.95, 0.5]
        pts = [foot + axis * length * j / n for j in range(n + 1)]
        radii = [(w * prof[j], w * 0.72 * prof[j]) for j in range(n + 1)]
        worn = rng.uniform(0.15, 0.45)

        def col(f, k, worn=worn):
            c = mix((0.07, 0.09, 0.17), (0.16, 0.2, 0.34), 0.5 + 0.5 * math.sin(f * 40.0))
            c = mix((0.6, 0.66, 0.76), c, smooth(worn * 0.5, worn, f))
            return mix(c, (0.85, 0.83, 0.75), 1.0 if rng.random() < 0.06 else 0.0)
        kit.tube(pts, radii, 5 if low else 8, col, up=perp(axis), round1=w * 0.3)


def feather_dusters(kit, low):
    rng = random.Random(53)
    for i in range(7):
        a = TAU * i / 7 + rng.uniform(-0.3, 0.3)
        reach = 0.0 if i == 0 else rng.uniform(0.04, 0.09)
        tall = rng.uniform(0.08, 0.2)
        lean = Vector((math.cos(a) * 0.3, 1, math.sin(a) * 0.3)).normalized()
        p0 = Vector((math.cos(a) * reach, -0.02, math.sin(a) * reach))
        top = p0 + lean * tall
        kit.tube([p0, p0 + lean * tall * 0.5, top], [0.014, 0.012, 0.011], 4 if low else 6,
                 lambda f, k: mul((0.62, 0.54, 0.40), 0.8 + 0.25 * rng.random()), sway=lambda f: 0.1 * f * tall / 0.2)
        band = [((0.95, 0.5, 0.15), (1.0, 0.92, 0.8)), ((0.55, 0.1, 0.16), (0.95, 0.75, 0.7)), ((0.85, 0.3, 0.1), (0.5, 0.12, 0.1))][i % 3]
        count = 8 if low else 15
        side = perp(lean)
        fore = lean.cross(side)
        length = rng.uniform(0.06, 0.085)
        w0 = 0.1 * tall / 0.2
        for j in range(count):
            b = TAU * j / count
            out = side * math.cos(b) + fore * math.sin(b)
            segs = 1 if low else 3
            pts = [top + out * 0.006]
            for s in range(segs):
                open_ = 0.5 + 0.7 * (s + 1) / segs
                pts.append(pts[-1] + (lean * math.cos(open_) + out * math.sin(open_)) * (length / segs))
            radii = [(0.004, 0.0012)] + [((0.009 if low else 0.007) * (1.0 - 0.6 * (s + 1) / segs), 0.0012) for s in range(segs)]
            kit.tube(pts, radii, 4, lambda f, k, band=band: band[int(f * 5.99) % 2], sway=lambda f, w0=w0: w0 + 0.3 * f,
                     up=out)


def giant_clam(kit, low):
    na, nt = (10, 3) if low else (24, 7)
    half = math.radians(80.0)

    def shell(i, t):
        c = mix((0.86, 0.83, 0.74), (0.68, 0.66, 0.6), 0.5 + 0.5 * math.sin(t * 30.0))
        return mix(c, (0.5, 0.58, 0.42), smooth(0.1, 0.5, noise.noise(Vector((i * 6.0, t * 6.0, 4.0)))) * 0.7)
    for sign in (1.0, -1.0):
        kit.xf = Matrix.Translation((0, -0.03, 0)) @ Matrix.Rotation(math.radians(24.0 * sign), 4, "X") @ Matrix.Scale(sign, 4, (0, 0, 1))
        kit.valve(0.52, 0.2, na, nt, half, 5, 0.3, 0.09, shell, lambda i, t: (0.93, 0.92, 0.88))
    kit.xf = Matrix.Identity(4)
    rng = random.Random(59)
    seed = Vector((3.0, 8.0, 1.0))

    def mantle(d):
        a = math.atan2(d.z, d.x)
        frill = 1.0 + 0.1 * math.cos(a * 10.0) * (1.0 - abs(d.y))
        p = Vector((d.x * 0.43 * frill, 0.30 + d.y * 0.13 + 0.07 * math.cos(d.x * 3.2) + 0.015 * math.cos(a * 10.0), d.z * 0.24 * frill))
        c = mix((0.06, 0.35, 0.85), (0.08, 0.72, 0.6), 0.5 + 0.9 * noise.noise(d * 2.5 + seed))
        c = mix(c, (0.03, 0.08, 0.2), smooth(0.25, 0.4, noise.noise(d * 9.0 + seed)))
        c = mix(c, (0.75, 0.95, 0.4), smooth(0.8, 0.95, abs(d.x) * 0.3 + abs(d.z)) * 0.8)   # a bright lip
        hole = (Vector((d.x, d.z)) - Vector((0.45, 0.0))).length
        c = mix((0.02, 0.03, 0.06), c, smooth(0.1, 0.2, hole) if d.y > 0 else 1.0)
        return p, c, 0.0
    kit.ball(2 if low else 3, mantle)


def living():
    red, gold = (0.78, 0.10, 0.08), (0.90, 0.62, 0.12)
    life("sea_fan_red", "cold", "soft", sea_fan(0.8, 0.014, (0.55, 0.05, 0.05), red, 3, 7))
    life("sea_fan_gold", "cold", "soft", sea_fan(0.45, 0.011, (0.6, 0.36, 0.08), gold, 4, 6))
    life("hydrocoral", "cold", "firm", hydrocoral)
    life("vase_sponge", "cold", "soft", vase_sponge)
    life("puffball_sponges", "cold", "firm", puffballs)
    life("green_anemone", "cold", "soft", green_anemone)
    life("strawberry_anemones", "cold", "soft", strawberry)
    life("urchin_purple", "cold", "firm", urchin(0.035, 0.032, (0.42, 0.2, 0.62), (0.75, 0.6, 0.9), 61))
    life("urchin_red", "cold", "firm", urchin(0.06, 0.075, (0.5, 0.05, 0.1), (0.85, 0.3, 0.3), 62))
    life("ochre_star", "cold", "firm", sea_star(0.13, 0.036, 0.03, False, 63),
         tints=[(0.50, 0.28, 0.66), (0.96, 0.52, 0.14), (0.60, 0.32, 0.20), (0.90, 0.72, 0.30)])
    life("bat_star", "cold", "firm", sea_star(0.085, 0.07, 0.022, True, 64),
         tints=[(0.95, 0.38, 0.14), (0.85, 0.16, 0.14), (0.55, 0.32, 0.70), (0.92, 0.76, 0.36), (0.42, 0.52, 0.42)])
    life("scallop", "cold", "firm", scallop)
    life("mussel_clump", "cold", "firm", mussels)
    life("feather_dusters", "cold", "soft", feather_dusters)
    life("brain_coral", "tropical", "firm", brain_coral, tints=[(0.82, 0.76, 0.30), (0.46, 0.74, 0.42), (0.90, 0.62, 0.50), (0.62, 0.50, 0.36)])
    life("table_coral", "tropical", "firm", table_coral, tints=[(0.84, 0.68, 0.46), (0.52, 0.54, 0.95), (0.50, 0.80, 0.56), (0.95, 0.56, 0.66)])
    life("staghorn_coral", "tropical", "firm", staghorn, tints=[(0.88, 0.72, 0.42), (0.45, 0.60, 0.98), (0.98, 0.62, 0.74), (0.60, 0.88, 0.60)])
    life("pillar_coral", "tropical", "firm", pillar_coral, tints=[(0.86, 0.72, 0.40), (0.95, 0.80, 0.25), (0.60, 0.80, 0.50), (0.80, 0.55, 0.80)])
    life("barrel_sponge", "tropical", "firm", barrel_sponge)
    life("sea_fan_purple", "tropical", "soft", sea_fan(1.0, 0.014, (0.36, 0.16, 0.6), (0.70, 0.45, 0.92), 6, 7, sway=0.9))
    life("soft_coral", "tropical", "soft", soft_coral, tints=[(1, 1, 1), (1.0, 0.75, 0.45), (0.8, 0.7, 1.0)])
    life("sea_rods", "tropical", "soft", sea_rods)
    life("giant_clam", "tropical", "firm", giant_clam)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rocks()
    cliffs()
    bommies()
    living()
    os.makedirs(OUT, exist_ok=True)
    for objs, path in ((FULL, "sea_floor_props.glb"), (LOW, "sea_floor_props_lo.glb")):
        bpy.ops.object.select_all(action="DESELECT")
        for obj in objs:
            obj.select_set(True)
        bpy.ops.export_scene.gltf(
            filepath=os.path.join(OUT, path), export_format="GLB", export_yup=True, use_selection=True,
            export_animations=False, export_texcoords=False, export_materials="NONE",
            export_vertex_color="ACTIVE", export_active_vertex_color_when_no_material=True, export_all_vertex_colors=False,
        )
    with open(os.path.join(OUT, "sea_floor_props.json"), "w") as out:
        json.dump(INFO, out, indent=1)
    # the editable file: full pieces in a row, their low ones in a row behind
    x = 0.0
    for full, low in zip(FULL, LOW):
        wide = INFO[full.name]["size"][0]
        x += wide * 0.5 + 0.5
        full.location = (x, 0, 0)
        low.location = (x, 22.0, 0)
        x += wide * 0.5 + 0.5
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "sea_floor_props.blend"))
    for name, info in INFO.items():
        print("BUILT %s group=%s material=%s size=%s tris=%d lo=%d spheres=%d" % (
            name, info["group"], info["material"], info["size"], info["tris"], info["tris_lo"], len(info["spheres"])))
    print("BUILD DONE %d pieces, %d triangles full, %d low" % (
        len(INFO), sum(i["tris"] for i in INFO.values()), sum(i["tris_lo"] for i in INFO.values())))


if __name__ == "__main__":
    main()
