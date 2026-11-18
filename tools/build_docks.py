"""Builds the docks of the bay: wharf pilings with their mussel collars, a length of wharf deck, a floating dock
and a moored sailboat, for Monterey harbour and the Santa Cruz wharf (tools/MONTEREY.md).

    "C:/Program Files/Blender Foundation/Blender 4.3/blender.exe" --background --factory-startup --python tools/build_docks.py [-- <folder for pictures>]

Writes models/docks.glb and tools/blend/docks.blend (editable). The user (2026-11-18): "another location should be
the docks / marina", then "theres should be more docks by santa cruise / marina at the dock". scripts/scenery.gd
lays the pieces out (one MultiMesh a piece); the moored skiff is fishing_gear.glb's Skiff and the moored trawler is
models/shrimp_boat.glb, both used as they are.

The framework (Build, tube, lathe, box, rod, the inside-out check) is copied from tools/build_fishing_gear.py.
Everything is written in Godot's axes (metres, Y up, -Z ahead) and turned into Blender's as it is made.

Objects (each a node of the .glb, a MeshInstance3D in Godot):
  Piling     a wharf pile 0.44 m across, origin at its top (under the deck's cap beam), down 12 m: a band of
             barnacles at the waterline (1.0 to 1.7 m down), mussel clumps below it (1.9 to 3.0 m), weed to 5.5 m
  Deck       a 4 m length of wharf (along Z) 8 m wide, origin at the middle of its top; planks over three stringers
             and a cap beam at its north end (z = -2), under which the piles stand at x = -3.5, 0, 3.5 (0.7 m down)
  Float      a floating dock 8 m long (Z) and 2 m wide, origin on the waterline: a deck on three white floats
  Sailboat   a 9 m sloop moored, bow to -Z, origin amidships on the waterline: a fin keel with a bulb (1.8 m
             down), a rudder, a small cabin, a mast (11 m) and boom
"""

import bpy
import math
import os
import sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GLB = os.path.join(ROOT, "models", "docks.glb")
BLEND = os.path.join(HERE, "blend", "docks.blend")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

COLOURS = {
    # (colour, metallic, roughness): painterly flat colours, a few to a piece
    "pile_wood": ((0.2, 0.17, 0.13), 0.0, 0.9),
    "barnacle": ((0.46, 0.44, 0.36), 0.0, 0.9),
    "mussel": ((0.08, 0.09, 0.16), 0.1, 0.5),
    "weed": ((0.26, 0.34, 0.16), 0.0, 0.9),
    "deck": ((0.3, 0.25, 0.19), 0.0, 0.9),
    "deck_dark": ((0.24, 0.2, 0.15), 0.0, 0.9),
    "rubber": ((0.06, 0.06, 0.07), 0.0, 0.8),
    "rust": ((0.3, 0.17, 0.1), 0.3, 0.8),
    "pot_wire": ((0.3, 0.32, 0.3), 0.5, 0.6),
    "beam": ((0.16, 0.13, 0.1), 0.0, 0.9),
    "float": ((0.86, 0.86, 0.8), 0.0, 0.6),
    "hull": ((0.9, 0.9, 0.86), 0.0, 0.4),
    "bottom": ((0.12, 0.2, 0.36), 0.0, 0.6),
    "stripe": ((0.1, 0.32, 0.5), 0.0, 0.5),
    "keel": ((0.18, 0.18, 0.2), 0.3, 0.6),
    "cabin": ((0.8, 0.78, 0.7), 0.0, 0.5),
    "mast": ((0.75, 0.76, 0.78), 0.7, 0.3),
    "rock": ((0.2, 0.18, 0.16), 0.0, 0.95),
    "rock_dark": ((0.12, 0.11, 0.1), 0.0, 0.95),
    "rock_top": ((0.42, 0.37, 0.26), 0.0, 0.95),
}


def B(p):
    """Godot (x, y, z) to Blender (x, -z, y)."""
    return Vector((p[0], -p[2], p[1]))


def material(name):
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    colour, metal, rough = COLOURS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (colour[0], colour[1], colour[2], 1.0)
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Roughness"].default_value = rough
    m.diffuse_color = (colour[0], colour[1], colour[2], 1.0)
    m.use_backface_culling = name != "net"
    return m


class Build:
    """One exported object made of parts: closed solids (checked for inside-out faces) and sheets."""

    def __init__(self, name):
        self.name = name
        self.verts = []
        self.faces = []
        self.mats = []
        self.uvs = []          # per face, a list of (u, v) per corner, or None
        self.parts = []        # (label, first face, end face, closed)

    def part(self, label, verts, faces, mat, closed=True, uvs=None):
        V = [Vector(v) for v in verts]
        mats = mat if isinstance(mat, list) else [mat] * len(faces)
        faces = [list(f) for f in faces]
        if closed:
            # (outwards: a positive volume)
            vol = 0.0
            for f in faces:
                for k in range(1, len(f) - 1):
                    vol += V[f[0]].dot(V[f[k]].cross(V[f[k + 1]]))
            if vol < 0.0:
                faces = [list(reversed(f)) for f in faces]
                if uvs:
                    uvs = [list(reversed(u)) for u in uvs]
        base = len(self.verts)
        self.verts.extend(V)
        first = len(self.faces)
        self.faces.extend([[i + base for i in f] for f in faces])
        self.mats.extend(mats)
        self.uvs.extend(uvs if uvs else [None] * len(faces))
        self.parts.append((label, first, len(self.faces), closed))

    def tris(self):
        n = 0
        for f in self.faces:
            n += len(f) - 2
        return n

    def inside_out(self):
        """Faces facing inwards, over every closed part, each on its own."""
        wrong = 0
        bad = []
        for label, f0, f1, closed in self.parts:
            if not closed:
                continue
            tris = []
            for f in self.faces[f0:f1]:
                for k in range(1, len(f) - 1):
                    tris.append((f[0], f[k], f[k + 1]))
            used = sorted({i for t in tris for i in t})
            remap = {v: k for k, v in enumerate(used)}
            pts = [self.verts[i] for i in used]
            polys = [(remap[a], remap[b], remap[c]) for a, b, c in tris]
            tree = BVHTree.FromPolygons(pts, polys, epsilon=0.0)
            count = 0
            where = []
            for a, b, c in polys:
                pa, pb, pc = pts[a], pts[b], pts[c]
                n = (pb - pa).cross(pc - pa)
                if n.length < 1e-12:
                    continue
                n.normalize()
                odd = True
                for wa, wb, wc in ((1 / 3, 1 / 3, 1 / 3), (0.45, 0.33, 0.22)):
                    at = pa * wa + pb * wb + pc * wc + n * 1e-5
                    hits = 0
                    while hits < 60:
                        hit = tree.ray_cast(at, n)
                        if hit[0] is None:
                            break
                        hits += 1
                        at = hit[0] + n * 1e-5
                    if hits % 2 == 0:
                        odd = False
                        break
                if odd:
                    count += 1
                    where.append(tuple(round(x, 3) for x in (pa + pb + pc) / 3))
            if count:
                bad.append((label, count, len(polys), where[:6]))
            wrong += count
        return wrong, bad

    def make(self):
        mesh = bpy.data.meshes.new(self.name)
        mesh.from_pydata([B(v) for v in self.verts], [], self.faces)
        used = sorted(set(self.mats))
        for m in used:
            mesh.materials.append(material(m))
        mesh.polygons.foreach_set("material_index", [used.index(m) for m in self.mats])
        if any(u is not None for u in self.uvs):
            layer = mesh.uv_layers.new(name="UVMap")
            for pi, poly in enumerate(mesh.polygons):
                face_uv = self.uvs[pi]
                for k, li in enumerate(poly.loop_indices):
                    layer.data[li].uv = face_uv[k] if face_uv else (0.0, 0.0)
        mesh.update()
        mesh.validate()
        obj = bpy.data.objects.new(self.name, mesh)
        bpy.context.scene.collection.objects.link(obj)
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(40))
        return obj


# ---------------------------------------------------------------------------------------------- shapes
def frames(path):
    """A frame (tangent, normal, binormal) at each point of a path, carried along without twisting."""
    out = []
    n = None
    for k in range(len(path)):
        a = path[max(k - 1, 0)]
        b = path[min(k + 1, len(path) - 1)]
        t = (b - a).normalized()
        if n is None:
            guess = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
            n = (guess - t * guess.dot(t)).normalized()
        else:
            n = (n - t * n.dot(t)).normalized()
        out.append((t, n, t.cross(n)))
    return out


def tube(b, label, path, radii, sides, mat, loop=False):
    """A closed tube along a path (Godot points); a radius of 0 at an end makes a point there."""
    path = [Vector(p) for p in path]
    if loop:
        path_f = path + [path[0], path[1]]
        fr = frames([path[-1]] + path_f)[1:len(path) + 1]
    else:
        fr = frames(path)
    verts, faces = [], []
    rings = []
    for k, p in enumerate(path):
        r = radii[k] if isinstance(radii, (list, tuple)) else radii
        t, n, bn = fr[k]
        if r <= 1e-7:
            rings.append([len(verts)])
            verts.append(p)
            continue
        ring = []
        for j in range(sides):
            a = math.tau * j / sides
            ring.append(len(verts))
            verts.append(p + (n * math.cos(a) + bn * math.sin(a)) * r)
        rings.append(ring)
    count = len(rings) if loop else len(rings) - 1
    for k in range(count):
        r0, r1 = rings[k], rings[(k + 1) % len(rings)]
        if len(r0) == 1 and len(r1) == 1:
            continue
        for j in range(sides):
            j1 = (j + 1) % sides
            # (outwards: the ring goes round counter-clockwise as seen from ahead)
            if len(r0) == 1:
                faces.append([r0[0], r1[j1], r1[j]])
            elif len(r1) == 1:
                faces.append([r0[j], r0[j1], r1[0]])
            else:
                faces.append([r0[j], r0[j1], r1[j1], r1[j]])
    if not loop:
        if len(rings[0]) > 1:
            faces.append(list(reversed(rings[0])))
        if len(rings[-1]) > 1:
            faces.append(list(rings[-1]))
    b.part(label, verts, faces, mat)


def lathe(b, label, profile, segs, mat, axis="y", at=(0, 0, 0), mats_by=None):
    """A solid of revolution: profile is [(radius, along)], from one pole (radius 0) to the other."""
    verts, faces = [], []
    rings = []
    for r, y in profile:
        if r <= 1e-7:
            rings.append([len(verts)])
            verts.append(_axis(axis, 0.0, y, 0.0, at))
            continue
        ring = []
        for j in range(segs):
            a = math.tau * j / segs
            ring.append(len(verts))
            verts.append(_axis(axis, r * math.cos(a), y, r * math.sin(a), at))
        rings.append(ring)
    fm = []
    for k in range(len(rings) - 1):
        r0, r1 = rings[k], rings[k + 1]
        m = mats_by(k) if mats_by else mat
        for j in range(segs):
            j1 = (j + 1) % segs
            if len(r0) == 1:
                faces.append([r0[0], r1[j1], r1[j]])
            elif len(r1) == 1:
                faces.append([r0[j], r0[j1], r1[0]])
            else:
                faces.append([r0[j], r0[j1], r1[j1], r1[j]])
            fm.append(m)
    if len(rings[0]) > 1:
        faces.append(list(rings[0]))
        fm.append(mats_by(0) if mats_by else mat)
    if len(rings[-1]) > 1:
        faces.append(list(reversed(rings[-1])))
        fm.append(mats_by(len(rings) - 2) if mats_by else mat)
    b.part(label, verts, faces, fm)


def _axis(axis, x, y, z, at):
    if axis == "y":
        return Vector((x + at[0], y + at[1], z + at[2]))
    if axis == "x":
        return Vector((y + at[0], x + at[1], z + at[2]))
    return Vector((x + at[0], z + at[1], y + at[2]))


def box(b, label, lo, hi, mat):
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    f = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
    b.part(label, v, f, mat)


def rod(b, label, a, c, r0, r1, sides, mat):
    tube(b, label, [a, c], [r0, r1], sides, mat)




def loft(b, label, rings, mat_of):
    """A closed solid through rings of points (each the same count, in the same turn), capped at both ends."""
    verts, faces, fm = [], [], []
    idx = []
    for ring in rings:
        idx.append(list(range(len(verts), len(verts) + len(ring))))
        verts.extend(ring)
    n = len(rings[0])
    for k in range(len(rings) - 1):
        r0, r1 = idx[k], idx[k + 1]
        for j in range(n):
            j1 = (j + 1) % n
            faces.append([r0[j], r0[j1], r1[j1], r1[j]])
            fm.append(mat_of((verts[r0[j]] + verts[r0[j1]] + verts[r1[j1]] + verts[r1[j]]) * 0.25))
    faces.append(list(reversed(idx[0])))
    fm.append(mat_of(sum(rings[0], Vector()) / n))
    faces.append(list(idx[-1]))
    fm.append(mat_of(sum(rings[-1], Vector()) / n))
    b.part(label, verts, faces, fm)


# ---------------------------------------------------------------------------------------------- the pieces
def piling():
    # (after tools/art_src/concept_docks.jpg: dark old timber crusted all the way down with pale barnacle clusters
    # and hanging clumps of dark mussels, thickest from the waterline to half way down)
    import random
    rnd = random.Random(5)
    b = Build("Piling")
    r = 0.26
    tube(b, "pile", [(0, 0, 0), (0, -12.0, 0)], r, 8, "pile_wood")
    for k in range(26):
        a = rnd.uniform(0.0, math.tau)
        y = -1.0 - (rnd.random() ** 1.6) * 8.5
        size = rnd.uniform(0.06, 0.1)
        at = (math.cos(a) * (r + size * 0.3), y, math.sin(a) * (r + size * 0.3))
        lathe(b, "barnacles %d" % k, [(0.0, -size * 0.6), (size, -size * 0.3), (size * 0.8, size * 0.5), (0.0, size * 0.6)], 5, "barnacle", at=at)
    for k in range(16):
        a = rnd.uniform(0.0, math.tau)
        y = -1.3 - (rnd.random() ** 1.3) * 7.5
        size = rnd.uniform(0.08, 0.12)
        at = (math.cos(a) * (r + size * 0.4), y, math.sin(a) * (r + size * 0.4))
        # (a clump hangs: longer below than above)
        lathe(b, "mussels %d" % k, [(0.0, -size * 2.2), (size * 0.8, -size * 0.9), (size, 0.0), (0.0, size * 0.8)], 5, "mussel", at=at)
    return b


def deck():
    b = Build("Deck")
    # planks across the wharf, alternately darker
    # (the gaps between the planks let slats of light through, as in the concept)
    count = 8
    for k in range(count):
        z0 = -2.0 + 4.0 * k / count
        box(b, "plank %d" % k, (-4.0, -0.15, z0 + 0.07), (4.0, 0.0, z0 + 4.0 / count - 0.07), "deck" if k % 2 == 0 else "deck_dark")
    for x in (-3.5, -1.75, 0.0, 1.75, 3.5):
        box(b, "stringer %g" % x, (x - 0.12, -0.6, -2.0), (x + 0.12, -0.15, 2.0), "beam")
    box(b, "cap", (-4.1, -0.7, -2.2), (4.1, -0.2, -1.8), "beam")
    # a low kerb along each side
    for x in (-3.9, 3.9):
        box(b, "kerb %g" % x, (x - 0.1, 0.0, -2.0), (x + 0.1, 0.25, 2.0), "beam")
    return b


def float_dock():
    b = Build("Float")
    box(b, "deck", (-1.0, 0.25, -4.0), (1.0, 0.4, 4.0), "deck")
    for z in (-2.7, 0.0, 2.7):
        box(b, "float %g" % z, (-0.9, -0.3, z - 1.1), (0.9, 0.25, z + 1.1), "float")
    for x in (-1.0, 1.0):
        box(b, "rail %g" % x, (x - 0.08, 0.15, -4.0), (x + 0.08, 0.45, 4.0), "beam")
    return b


def sailboat():
    b = Build("Sailboat")
    # stations bow (-Z) to stern (+Z): z, half beam, sheer (above the water), draft of the hull
    stations = [(-4.5, 0.03, 1.15, 0.05), (-3.8, 0.55, 1.05, 0.35), (-2.6, 1.1, 0.95, 0.55), (-1.0, 1.45, 0.9, 0.62),
                (0.6, 1.5, 0.88, 0.58), (2.2, 1.42, 0.88, 0.45), (3.6, 1.25, 0.9, 0.28), (4.4, 1.1, 0.92, 0.12)]
    rings = []
    for z, half, sheer, draft in stations:
        rings.append([Vector((half, sheer, z)), Vector((half * 0.96, 0.15, z)), Vector((half * 0.75, -draft * 0.6, z)),
                      Vector((0.0, -draft, z)), Vector((-half * 0.75, -draft * 0.6, z)), Vector((-half * 0.96, 0.15, z)),
                      Vector((-half, sheer, z)), Vector((0.0, sheer + 0.08, z))])

    def hull_mat(p):
        if p.y < 0.02:
            return "bottom"
        return "stripe" if p.y < 0.3 else "hull"

    loft(b, "hull", rings, hull_mat)
    # the fin keel and its bulb, the rudder
    keel = [[Vector((0.07, -0.5, z)), Vector((0.07, -1.6, z + 0.25)), Vector((-0.07, -1.6, z + 0.25)), Vector((-0.07, -0.5, z))]
            for z in (-0.7, 0.5)]
    loft(b, "keel", keel, lambda p: "keel")
    lathe(b, "bulb", [(0.0, -0.9), (0.2, -0.5), (0.24, 0.2), (0.16, 0.8), (0.0, 1.0)], 8, "keel", axis="z", at=(0.0, -1.7, 0.0))
    rudder = [[Vector((0.05, -0.05, z)), Vector((0.05, -1.1, z + 0.15)), Vector((-0.05, -1.1, z + 0.15)), Vector((-0.05, -0.05, z))]
              for z in (3.5, 4.0)]
    loft(b, "rudder", rudder, lambda p: "keel")
    box(b, "cabin", (-0.9, 0.85, -1.6), (0.9, 1.45, 1.2), "cabin")
    rod(b, "mast", (0.0, 1.0, -1.4), (0.0, 11.5, -1.4), 0.07, 0.05, 6, "mast")
    rod(b, "boom", (0.0, 2.0, -1.35), (0.0, 2.0, 2.6), 0.05, 0.05, 6, "mast")
    return b


# ---------------------------------------------------------------------------------------------- the harbour's litter
# (the concept's floor under the wharf: an old tyre, a run of chain, a crab pot, an anchor)
def tyre():
    """An old tyre lying flat, origin at its middle on the floor."""
    b = Build("Tyre")
    ring = [(math.cos(math.tau * k / 12) * 0.34, 0.12, math.sin(math.tau * k / 12) * 0.34) for k in range(12)]
    tube(b, "tyre", ring, 0.12, 6, "rubber", loop=True)
    return b


def crab_pot():
    """A wire crab pot 0.9 x 0.45 x 0.9 m, origin at the middle of its foot: its frame and a few wires across."""
    b = Build("CrabPot")
    h, w = 0.45, 0.45
    corners = [(-w, 0.0, -w), (w, 0.0, -w), (w, 0.0, w), (-w, 0.0, w)]
    for k in range(4):
        x0, _, z0 = corners[k]
        x1, _, z1 = corners[(k + 1) % 4]
        rod(b, "foot %d" % k, (x0, 0.02, z0), (x1, 0.02, z1), 0.018, 0.018, 4, "pot_wire")
        rod(b, "top %d" % k, (x0, h, z0), (x1, h, z1), 0.018, 0.018, 4, "pot_wire")
        rod(b, "post %d" % k, (x0, 0.02, z0), (x0, h, z0), 0.018, 0.018, 4, "pot_wire")
    for k in range(1, 4):
        t = -w + 2 * w * k / 4
        rod(b, "wire x %d" % k, (t, h, -w), (t, h, w), 0.008, 0.008, 3, "pot_wire")
        rod(b, "wire side %d" % k, (t, 0.02, w), (t, h, w), 0.008, 0.008, 3, "pot_wire")
        rod(b, "wire back %d" % k, (t, 0.02, -w), (t, h, -w), 0.008, 0.008, 3, "pot_wire")
    return b


def chain():
    """A run of 14 rusty links lying in a curve on the floor, 3.6 m long, origin at its first link."""
    b = Build("Chain")
    for k in range(14):
        x = k * 0.26
        z = 0.5 * math.sin(k * 0.35)
        upright = k % 2 == 1
        loop = []
        for j in range(8):
            a = math.tau * j / 8
            u, v = math.cos(a) * 0.16, math.sin(a) * 0.09
            loop.append((x + u, 0.09 + (v if upright else 0.0), z + (0.0 if upright else v)))
        tube(b, "link %d" % k, loop, 0.025, 4, "rust", loop=True)
    return b


def anchor():
    """An old fisherman's anchor lying on its side, 1.4 m long, origin at the middle of its foot."""
    b = Build("Anchor")
    rod(b, "shank", (0.0, 0.08, -0.7), (0.0, 0.08, 0.6), 0.05, 0.05, 6, "rust")
    arc = [(math.sin(a) * 0.5, 0.08, 0.6 - math.cos(a) * 0.5 + 0.5) for a in [i * 0.35 - 1.05 for i in range(7)]]
    tube(b, "crown", arc, 0.045, 6, "rust")
    for side in (-1, 1):
        x = side * math.sin(1.05) * 0.5
        z = 0.6 - math.cos(1.05) * 0.5 + 0.5
        box(b, "fluke %d" % side, (x - 0.12, 0.03, z - 0.18), (x + 0.12, 0.13, z + 0.02), "rust")
    rod(b, "stock", (-0.45, 0.08, -0.6), (0.45, 0.08, -0.6), 0.035, 0.035, 6, "rust")
    lathe(b, "ring", [(0.0, -0.7 - 0.12), (0.09, -0.7 - 0.06), (0.09, -0.7 + 0.0), (0.0, -0.7 + 0.03)], 6, "rust", axis="z", at=(0.0, 0.08, 0.0))
    return b


# ---------------------------------------------------------------------------------------------- the pirate ship's rocks
# The outcrop the pirate ship struck (the user, 2026-11-18: "there shoule be an outcropping of rocks near the pirate
# ship, pillars and shards and an island that seals rest on"). Faceted, jagged, a few hundred triangles each.
def _jagged_rings(profile, sides, seed, lean=(0.0, 0.0), squash=1.0):
    """Rings for a rough rock: profile is [(radius, y)], each corner's radius jittered (the same jitter up a column,
    so that it reads as faceted stone, a little more each ring); `lean` moves each ring over by y times it."""
    import random
    rnd = random.Random(seed)
    column = [rnd.uniform(0.8, 1.15) for _ in range(sides)]
    rings = []
    for r, y in profile:
        ring = []
        for j in range(sides):
            a = math.tau * j / sides + rnd.uniform(-0.12, 0.12)
            rr = r * column[j] * rnd.uniform(0.92, 1.08)
            ring.append(Vector((math.cos(a) * rr + lean[0] * y, y, math.sin(a) * rr * squash + lean[1] * y)))
        rings.append(ring)
    return rings


def pillar():
    """A sea stack 14 m tall, origin at the middle of its foot: scaled in the game."""
    b = Build("Pillar")
    profile = [(1.9, -0.5), (1.8, 2.0), (1.5, 5.0), (1.45, 8.0), (1.2, 11.0), (0.9, 13.0), (0.35, 14.0)]
    loft(b, "stack", _jagged_rings(profile, 7, 3), lambda p: "rock_dark" if p.y < 4.0 else "rock")
    return b


def shard():
    """A leaning blade of rock 9 m long, origin at its foot, leaning towards +X; scaled and turned in the game."""
    b = Build("Shard")
    profile = [(1.4, -0.4), (1.2, 2.5), (0.9, 5.0), (0.55, 7.5), (0.1, 9.0)]
    loft(b, "blade", _jagged_rings(profile, 5, 7, lean=(0.35, 0.0), squash=0.45), lambda p: "rock_dark" if p.y < 3.0 else "rock")
    return b


def islet():
    """A low flat-topped rock 8 m across for seals to haul out on, origin at the middle of its top; its top stands
    1.1 m out of the water when placed there, with a ledge all round at the waterline, and it goes down 26 m."""
    b = Build("Islet")
    profile = [(5.6, -26.0), (4.6, -14.0), (4.1, -5.0), (3.6, -1.7), (4.0, -1.25), (3.95, -0.95), (3.0, -0.7),
               (3.1, -0.2), (2.6, 0.0)]
    rings = _jagged_rings(profile, 9, 11)

    def mat_of(p):
        if p.y > -0.15:
            return "rock_top"
        return "rock" if p.y > -5.0 else "rock_dark"

    loft(b, "rock", rings, mat_of)
    return b


# ---------------------------------------------------------------------------------------------- pictures
def render(folder, objects):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_backface_culling = True
    scene.render.resolution_x, scene.render.resolution_y = 360, 360
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    scene.collection.objects.link(camera)
    scene.camera = camera
    for obj in objects:
        for other in objects:
            other.hide_render = other is not obj
        lo = Vector([min(v.co[i] for v in obj.data.vertices) for i in range(3)])
        hi = Vector([max(v.co[i] for v in obj.data.vertices) for i in range(3)])
        middle = (lo + hi) * 0.5
        size = max((hi - lo).length, 0.01)
        camera.data.ortho_scale = size * 1.05
        camera.data.clip_end = size * 20
        for view, direction in (("front", (0, 1, 0.3)), ("back", (0, -1, 0.3)), ("side", (1, 0, 0.3)),
                                ("top", (0.01, 0.01, 1)), ("below", (0.01, 0.3, -1))):
            offset = Vector(direction).normalized() * size * 4
            camera.location = middle + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y").to_euler()
            scene.render.filepath = os.path.join(folder, "%s_%s.png" % (obj.name, view))
            bpy.ops.render.render(write_still=True)
    for other in objects:
        other.hide_render = False


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    builds = [piling(), deck(), float_dock(), sailboat(), tyre(), crab_pot(), chain(), anchor(), pillar(), shard(), islet()]
    wrong_all = 0
    total = 0
    for b in builds:
        wrong, bad = b.inside_out()
        wrong_all += wrong
        total += b.tris()
        print("DOCKS %s: %d triangles, %d facing inwards" % (b.name, b.tris(), wrong))
        for label, count, of, where in bad:
            print("   bad part %s: %d of %d at %s" % (label, count, of, where))
    print("TRIANGLES total: %d" % total)
    print("INSIDE-OUT %s" % ("PASSED" if wrong_all == 0 else "FAILED (%d)" % wrong_all))
    objects = [b.make() for b in builds]
    os.makedirs(os.path.dirname(BLEND), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    bpy.ops.object.select_all(action="DESELECT")
    kw = dict(filepath=GLB, export_format="GLB", export_apply=True, export_yup=True, export_cameras=False,
              export_lights=False, export_animations=False)
    bpy.ops.export_scene.gltf(**kw)
    print("WROTE", GLB)
    if ARGS:
        os.makedirs(ARGS[0], exist_ok=True)
        render(ARGS[0], objects)


main()
