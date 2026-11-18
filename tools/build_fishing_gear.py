"""Builds the fishing gear of the sea: hooks, floats, nets, a trawl and an angler's skiff.

    "C:/Program Files/Blender Foundation/Blender 4.3/blender.exe" --background --factory-startup --python tools/build_fishing_gear.py [-- <folder for pictures>]

Writes models/fishing_gear.glb and tools/blend/fishing_gear.blend (editable). The user (2026-11-18): "We need to add
fisherman- hooks nets and trawlers". The game's side is scripts/fishers.gd; the design is in tools/FISHERS.md.

Everything is written here in Godot's axes (metres, Y up, -Z ahead) and turned into Blender's (Z up) as it is made
(Godot (x, y, z) is Blender (x, -z, y)); the glTF exporter turns it back.

Objects (each a node of the .glb, a MeshInstance3D in Godot):
  Hook        a J hook with a barb, 5 cm, origin at its eye, hanging down -Y; the point on +X
  Worm        a worm threaded on the hook (same origin as the hook)
  BaitFish    a small silver fish hooked through the back (same origin as the hook)
  Sinker      a teardrop of lead, origin at its top
  Bobber      a red and white float with a stick on top, origin at its middle (the waterline)
  NetFloat    a float of a net's headrope, its axis along X (the rope), origin at its middle
  NetWeight   a lead weight of a net's footrope, axis along X
  MarkerBuoy  a net's end marker: a ball with a pole and a flag, origin at the waterline
  OtterDoor   a trawl door: a board 1.8 m long and 0.9 m high, thin along X, with a steel shoe; origin at its middle
  Skiff       an angler's open boat, 4.2 m, bow to -Z, origin amidships on the waterline, an outboard motor and two
              rods (tips at Godot (+-1.55, 1.62, 0.55): ROD_TIPS below)
  NetPanel    a curtain of net: a flat unit square, x -0.5..0.5, y 0..-1 (origin at the top middle), facing +Z;
              scaled in the game. Its mesh pattern is drawn by shaders/net.gdshader from its local position.
  Trawl       the trawl: a funnel of net with its mouth at z = 0 (6 m wide, 3 m high, the middle at y = 0) tapering
              to a cod end 8 m behind (+Z) and a bag to 9.8 m; a headrope with seven floats and a heavier footrope
              round the mouth. Its net's UVs are in metres (round, along) for the same shader.
  Line        a unit line: a thin six-sided rod from y = 0 to y = 1, 1 unit across; scaled between two points.

The net surfaces use the material "net" (no backface culling); the game draws them with its own shader. Every other
part is a closed solid, checked here for inside-out faces (a ray from each triangle out along its normal must leave
the part's own skin an odd number of times) and the sheets for winding against their normals: the INSIDE-OUT line.
"""

import bpy
import math
import os
import sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GLB = os.path.join(ROOT, "models", "fishing_gear.glb")
BLEND = os.path.join(HERE, "blend", "fishing_gear.blend")
ARGS = [a for a in (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []) if not a.startswith("--")]

ROD_TIPS = [(-1.55, 1.62, 0.55), (1.55, 1.62, 0.55)]

COLOURS = {
    "steel": ((0.62, 0.64, 0.68), 0.8, 0.3),
    "lead": ((0.26, 0.27, 0.3), 0.3, 0.6),
    "float_red": ((0.8, 0.06, 0.04), 0.0, 0.4),
    "float_white": ((0.92, 0.92, 0.88), 0.0, 0.4),
    "float_orange": ((1.0, 0.38, 0.03), 0.0, 0.4),
    "worm": ((0.72, 0.3, 0.32), 0.0, 0.35),
    "bait_silver": ((0.7, 0.76, 0.82), 0.6, 0.3),
    "bait_back": ((0.12, 0.22, 0.32), 0.2, 0.4),
    "door_wood": ((0.32, 0.2, 0.1), 0.0, 0.8),
    "skiff_hull": ((0.82, 0.82, 0.76), 0.0, 0.5),
    "skiff_bottom": ((0.22, 0.12, 0.08), 0.0, 0.7),
    "skiff_inside": ((0.5, 0.4, 0.28), 0.0, 0.8),
    "motor": ((0.08, 0.08, 0.09), 0.2, 0.5),
    "rod": ((0.1, 0.1, 0.12), 0.1, 0.4),
    "rope": ((0.5, 0.42, 0.28), 0.0, 0.9),
    "chain": ((0.18, 0.18, 0.2), 0.6, 0.5),
    "flag": ((0.85, 0.08, 0.06), 0.0, 0.7),
    "line": ((0.85, 0.9, 0.9), 0.0, 0.5),
    "net": ((0.62, 0.72, 0.62), 0.0, 0.8),
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


# ---------------------------------------------------------------------------------------------- the gear
def hook():
    b = Build("Hook")
    # the eye: a ring in the XY plane
    eye = [(0.0035 * math.sin(math.tau * k / 10), -0.0035 - 0.0035 * math.cos(math.tau * k / 10), 0.0) for k in range(10)]
    tube(b, "eye", eye, 0.0011, 6, "steel", loop=True)
    path = [(0.0, -0.0072, 0.0), (0.0, -0.022, 0.0), (0.0, -0.036, 0.0)]
    for k in range(1, 9):
        a = math.pi + math.pi * k / 8
        path.append((0.009 + 0.009 * math.cos(a), -0.036 + 0.009 * math.sin(a), 0.0))
    path += [(0.018, -0.030, 0.0), (0.0178, -0.024, 0.0), (0.0175, -0.020, 0.0)]
    radii = [0.0012] * (len(path) - 3) + [0.0011, 0.0008, 0.0]
    tube(b, "shank and bend", path, radii, 6, "steel")
    # the barb, back down from the point towards the shank
    tube(b, "barb", [(0.0179, -0.0225, 0.0), (0.0158, -0.0275, 0.0)], [0.0009, 0.0], 5, "steel")
    return b


def worm():
    b = Build("Worm")
    path = []
    for k in range(15):
        s = k / 14
        a = math.pi * 0.9 + s * math.pi * 1.6
        r = 0.011 + 0.006 * math.sin(s * 9.0)
        path.append((0.009 + r * math.cos(a), -0.034 + r * math.sin(a) * 1.3 - 0.008 * s, 0.004 * math.sin(s * 7.0)))
    radii = [0.0, 0.0032, 0.0038, 0.004, 0.004, 0.0042, 0.0042, 0.0042, 0.004, 0.004, 0.0038, 0.0036, 0.0032, 0.0026, 0.0]
    tube(b, "worm", path, radii, 6, "worm")
    return b


def bait_fish():
    b = Build("BaitFish")
    # hooked through the back, lying along X, its nose to -X
    long = 0.075
    mid = Vector((0.009, -0.041, 0.0))
    path = [mid + Vector((-long * 0.5 + long * k / 8, 0.0, 0.0)) for k in range(9)]
    radii = [0.0, 0.006, 0.009, 0.0105, 0.0105, 0.009, 0.0065, 0.0035, 0.0015]
    tube(b, "body", path, radii, 8, "bait_silver")
    # (the tail: a thin fan, a closed wedge)
    t = mid + Vector((long * 0.5, 0.0, 0.0))
    v = [t + Vector((-0.004, 0.0, -0.0012)), t + Vector((0.012, 0.009, -0.0006)), t + Vector((0.012, -0.009, -0.0006)),
         t + Vector((-0.004, 0.0, 0.0012)), t + Vector((0.012, 0.009, 0.0006)), t + Vector((0.012, -0.009, 0.0006))]
    b.part("tail", v, [[0, 1, 2], [3, 5, 4], [0, 3, 4, 1], [1, 4, 5, 2], [2, 5, 3, 0]], "bait_silver")
    # (a dark back: a flat ridge along the top)
    tube(b, "back", [mid + Vector((-long * 0.32, 0.0085, 0.0)), mid + Vector((long * 0.3, 0.0062, 0.0))], [0.0032, 0.0018], 5, "bait_back")
    return b


def sinker():
    b = Build("Sinker")
    prof = [(0.0, 0.0), (0.0016, -0.0015), (0.0018, -0.004), (0.0045, -0.009), (0.0072, -0.016), (0.008, -0.022),
            (0.0065, -0.028), (0.0035, -0.031), (0.0, -0.032)]
    lathe(b, "sinker", prof, 10, "lead")
    return b


def bobber():
    b = Build("Bobber")
    prof = [(0.0, -0.055)]
    for k in range(1, 8):
        a = -math.pi * 0.5 + math.pi * k / 8
        prof.append((0.034 * math.cos(a), 0.034 * math.sin(a)))
    prof.append((0.0, 0.034))
    lathe(b, "ball", [(0.0, -0.034)] + prof[1:], 12, "float_white", mats_by=lambda k: "float_red" if k < 4 else "float_white")
    rod(b, "stick", (0.0, 0.025, 0.0), (0.0, 0.085, 0.0), 0.004, 0.0035, 6, "float_red")
    rod(b, "stem", (0.0, -0.025, 0.0), (0.0, -0.05, 0.0), 0.0035, 0.002, 6, "float_white")
    return b


def net_float():
    b = Build("NetFloat")
    prof = [(0.0, -0.09), (0.035, -0.085), (0.06, -0.06), (0.068, -0.02), (0.068, 0.02), (0.06, 0.06), (0.035, 0.085), (0.0, 0.09)]
    lathe(b, "float", prof, 10, "float_orange", axis="x")
    return b


def net_weight():
    b = Build("NetWeight")
    prof = [(0.0, -0.035), (0.022, -0.033), (0.03, -0.02), (0.03, 0.02), (0.022, 0.033), (0.0, 0.035)]
    lathe(b, "weight", prof, 8, "lead", axis="x")
    return b


def marker_buoy():
    b = Build("MarkerBuoy")
    prof = [(0.0, -0.24)]
    for k in range(1, 8):
        a = -math.pi * 0.5 + math.pi * k / 8
        prof.append((0.24 * math.cos(a), 0.06 + 0.24 * math.sin(a) * (1.0 if a < 0 else 0.9)))
    prof.append((0.0, 0.28))
    lathe(b, "ball", prof, 12, "float_orange")
    rod(b, "pole", (0.0, 0.2, 0.0), (0.0, 1.7, 0.0), 0.022, 0.016, 6, "rod")
    box(b, "flag", (0.015, 1.3, -0.006), (0.4, 1.62, 0.006), "flag")
    return b


def otter_door():
    b = Build("OtterDoor")
    # the board, slightly bowed outwards (+X), 1.8 m along Z, 0.9 m high
    verts, faces = [], []
    cols = 7
    for k in range(cols):
        z = -0.9 + 1.8 * k / (cols - 1)
        bow = 0.07 * (1.0 - (z / 0.9) ** 2)
        for y in (-0.45, 0.45):
            for x in (-0.04, 0.04):
                verts.append((x + bow, y, z))
    def at(k, yi, xi):
        return k * 4 + yi * 2 + xi
    for k in range(cols - 1):
        faces.append([at(k, 0, 1), at(k, 1, 1), at(k + 1, 1, 1), at(k + 1, 0, 1)])      # outer face
        faces.append([at(k, 0, 0), at(k + 1, 0, 0), at(k + 1, 1, 0), at(k, 1, 0)])      # inner face
        faces.append([at(k, 1, 0), at(k + 1, 1, 0), at(k + 1, 1, 1), at(k, 1, 1)])      # top
        faces.append([at(k, 0, 0), at(k, 0, 1), at(k + 1, 0, 1), at(k + 1, 0, 0)])      # bottom
    faces.append([at(0, 0, 0), at(0, 1, 0), at(0, 1, 1), at(0, 0, 1)])
    last = cols - 1
    faces.append([at(last, 0, 0), at(last, 0, 1), at(last, 1, 1), at(last, 1, 0)])
    b.part("board", verts, faces, "door_wood")
    box(b, "shoe", (-0.05, -0.52, -0.85), (0.12, -0.43, 0.85), "chain")
    for z in (-0.45, 0.45):
        box(b, "brace", (-0.11, -0.4, z - 0.035), (-0.035, 0.4, z + 0.035), "chain")
    rod(b, "bridle pin", (-0.04, 0.0, -0.75), (-0.32, 0.0, -0.75), 0.02, 0.02, 6, "chain")
    return b


def skiff():
    b = Build("Skiff")
    # stations along z (bow -2.1 to transom +2.1): (z, half breadth at the gunwale, depth of the keel, sheer height)
    stations = [(-2.1, 0.04, 0.12, 0.62), (-1.8, 0.32, 0.22, 0.56), (-1.3, 0.58, 0.28, 0.5), (-0.6, 0.74, 0.3, 0.46),
                (0.2, 0.78, 0.3, 0.44), (1.0, 0.76, 0.28, 0.44), (1.7, 0.7, 0.25, 0.45), (2.1, 0.66, 0.22, 0.46)]
    shape = [(-1.0, 1.0), (-0.98, 0.15), (-0.86, -0.3), (-0.5, -0.8), (0.0, -1.0), (0.5, -0.8), (0.86, -0.3), (0.98, 0.15), (1.0, 1.0)]
    verts, faces, mats = [], [], []
    n = len(shape)
    for z, half, keel, sheer in stations:
        for sx, sy in shape:
            # (the gunwale, the chine just above the water, the bottom down to the keel)
            if sy >= 1.0:
                y = sheer
            elif sy > 0.0:
                y = 0.12
            else:
                y = keel * sy
            verts.append((sx * half, y, z))
    for k in range(len(stations) - 1):
        for j in range(n):
            j1 = (j + 1) % n
            a, c = k * n + j, (k + 1) * n + j
            a1, c1 = k * n + j1, (k + 1) * n + j1
            faces.append([a, a1, c1, c])
            if j == n - 1:
                mats.append("skiff_inside")
            else:
                low = min(verts[a][1], verts[a1][1])
                mats.append("skiff_bottom" if low < -0.05 else "skiff_hull")
    sides = len(faces)
    faces.append(list(range(n)))
    mats.append("skiff_hull")
    last = (len(stations) - 1) * n
    faces.append([last + j for j in range(n)])
    mats.append("skiff_hull")
    # (every face outwards: away from the line down the middle of the hull, and the two ends away from
    # amidships; each section is convex, so that is enough)
    for k, f in enumerate(faces):
        pts = [Vector(verts[i]) for i in f]
        centre = sum(pts, Vector()) / len(pts)
        normal = Vector((0, 0, 0))
        for i in range(len(pts)):
            p, q = pts[i], pts[(i + 1) % len(pts)]
            normal += p.cross(q)
        away = centre - Vector((0.0, 0.15, centre.z if k < sides else 0.0))
        if normal.dot(away) < 0.0:
            faces[k] = list(reversed(f))
    b.part("hull", verts, faces, mats)
    # a keel strip, the gunwale rails, two thwarts
    box(b, "keel", (-0.03, -0.34, -1.9), (0.03, -0.22, 1.9), "skiff_bottom")
    for side in (-1, 1):
        rail = []
        for z, half, keel, sheer in stations[1:]:
            rail.append((side * (half + 0.015), sheer + 0.02, z))
        tube(b, "rail", rail, 0.03, 5, "skiff_inside")
    for z in (-0.7, 0.6):
        box(b, "thwart", (-0.72, 0.42, z - 0.12), (0.72, 0.5, z + 0.12), "skiff_inside")
    # the outboard motor on the transom
    box(b, "motor head", (-0.16, 0.42, 2.12), (0.16, 0.8, 2.52), "motor")
    rod(b, "motor leg", (0.0, 0.45, 2.3), (0.0, -0.55, 2.3), 0.06, 0.05, 6, "motor")
    lathe(b, "motor foot", [(0.0, -0.08), (0.06, -0.06), (0.07, 0.0), (0.06, 0.12), (0.0, 0.16)], 6, "motor", axis="z", at=(0.0, -0.58, 2.3))
    for k in range(3):
        a = math.tau * k / 3
        tip = Vector((0.0, -0.58, 2.48)) + Vector((math.cos(a), math.sin(a), 0.0)) * 0.13
        tube(b, "blade", [(0.0, -0.58, 2.47), tip], [0.03, 0.012], 4, "motor")
    # two rods, one over each side from the stern thwart
    for tip in ROD_TIPS:
        side = 1.0 if tip[0] > 0 else -1.0
        rod(b, "rod", (side * 0.45, 0.5, 1.0), tip, 0.014, 0.004, 5, "rod")
        lathe(b, "reel", [(0.0, -0.03), (0.035, -0.03), (0.035, 0.03), (0.0, 0.03)], 8, "steel", axis="x",
              at=(side * 0.62, 0.66, 0.92))
    return b


def net_panel():
    b = Build("NetPanel")
    cols, rows = 12, 4
    verts, faces, uvs = [], [], []
    for r in range(rows + 1):
        for c in range(cols + 1):
            verts.append((-0.5 + c / cols, -r / rows, 0.0))
    for r in range(rows):
        for c in range(cols):
            a = r * (cols + 1) + c
            # (facing +Z: counter-clockwise as seen from +Z)
            f = [a, a + cols + 1, a + cols + 2, a + 1]
            faces.append(f)
            uvs.append([(verts[i][0] + 0.5, -verts[i][1]) for i in f])
    b.part("curtain", verts, faces, "net", closed=False, uvs=uvs)
    return b


def trawl_section(z):
    """The trawl's half width and half height at a distance z behind its mouth (to the bag at 9.8 m)."""
    if z <= 8.0:
        s = (z / 8.0) ** 0.8
        return 3.0 + (0.45 - 3.0) * s, 1.5 + (0.45 - 1.5) * s
    bulge = 0.45 + 0.15 * math.sin(min((z - 8.0) / 1.8, 1.0) * math.pi * 0.8)
    return bulge, bulge


def trawl():
    b = Build("Trawl")
    sides = 12
    zs = [0.0, 0.8, 1.8, 3.0, 4.3, 5.6, 6.8, 8.0, 8.7, 9.4]
    verts, faces, uvs = [], [], []
    for z in zs:
        a, h = trawl_section(z)
        for j in range(sides + 1):
            t = math.tau * j / sides
            verts.append((a * math.sin(t), h * math.cos(t), z))
    tip = len(verts)
    verts.append((0.0, 0.0, 9.8))
    per = sides + 1

    def round_m(k, j):
        a, h = trawl_section(zs[k])
        return j / sides * math.pi * (a + h)

    for k in range(len(zs) - 1):
        for j in range(sides):
            p, q = k * per + j, (k + 1) * per + j
            # (normals outwards: counter-clockwise as seen from outside)
            f = [p, q, q + 1, p + 1]
            faces.append(f)
            uvs.append([(round_m(k, j), zs[k]), (round_m(k + 1, j), zs[k + 1]), (round_m(k + 1, j + 1), zs[k + 1]), (round_m(k, j + 1), zs[k])])
    k = len(zs) - 1
    for j in range(sides):
        p = k * per + j
        faces.append([p, tip, p + 1])
        uvs.append([(round_m(k, j), zs[k]), (round_m(k, j) + 0.1, 9.8), (round_m(k, j + 1), zs[k])])
    # (outwards: check one face against its place, flip all if wrong)
    v0 = [Vector(verts[i]) for i in faces[0]]
    n = (v0[1] - v0[0]).cross(v0[2] - v0[0])
    centre = sum(v0, Vector()) / 4
    if n.dot(Vector((centre.x, centre.y, 0.0))) < 0:
        faces = [list(reversed(f)) for f in faces]
        uvs = [list(reversed(u)) for u in uvs]
    b.part("funnel", verts, faces, "net", closed=False, uvs=uvs)
    # the headrope over the top of the mouth (with floats) and the heavier footrope under it
    head = [(3.0 * math.sin(t), 1.5 * math.cos(t), 0.0) for t in [math.pi * (-0.5 + k / 12) for k in range(13)]]
    foot = [(3.0 * math.sin(t), 1.5 * math.cos(t), 0.0) for t in [math.pi * (0.5 + k / 12) for k in range(13)]]
    tube(b, "headrope", head, 0.03, 4, "rope")
    tube(b, "footrope", foot, 0.06, 5, "chain")
    for k in range(7):
        t = math.pi * (-0.375 + 0.75 * k / 6)
        at = (3.0 * math.sin(t), 1.5 * math.cos(t) + 0.1, 0.0)
        lathe(b, "float", [(0.0, -0.1), (0.07, -0.07), (0.1, 0.0), (0.07, 0.07), (0.0, 0.1)], 6, "float_orange", at=at)
    return b


def line():
    b = Build("Line")
    rod(b, "line", (0.0, 0.0, 0.0), (0.0, 1.0, 0.0), 0.5, 0.5, 6, "line")
    return b


# ---------------------------------------------------------------------------------------------- pictures
def render(folder, objects):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_backface_culling = True
    scene.render.resolution_x, scene.render.resolution_y = 420, 420
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
        # (Blender axes: front is Godot -Z, Blender +Y)
        for view, direction in (("front", (0, 1, 0.3)), ("back", (0, -1, 0.3)), ("side", (1, 0, 0.3)),
                                ("top", (0.01, 0.01, 1)), ("below", (0.01, 0.3, -1))):
            offset = Vector(direction).normalized() * size * 4
            camera.location = middle + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y").to_euler()
            scene.render.filepath = os.path.join(folder, "%s_%s.png" % (obj.name, view))
            bpy.ops.render.render(write_still=True)
    for other in objects:
        other.hide_render = False


# ---------------------------------------------------------------------------------------------- the paint
# (the quality pass, 2026-11-18: the user, "make sure things have textures that fit our art style"). As the shrimp
# boat's (tools/build_shrimp_boat.py, where the same helpers are explained): each solid part's material becomes a
# procedural paint (worn white paint on the skiff, wood grain, mottled metal, grime in the corners), every solid part
# is unwrapped into ONE atlas and Cycles bakes it under an even sky (contact shadow, no sun); the materials keep their
# names and draw the picture (embedded in the .glb as a JPEG; lit as before). Not baked: the net (the game's net
# shader draws it from its own UVs), the unit Line (scaled in the game) and the Trawl (its net's UVs are in metres for
# that shader): the Trawl's rope and floats get plain copies of their materials, named "<name>_plain".
# `-- --no-bake` skips it. 1024 px: the gear is small and seen small (the skiff, 4.2 m, is the biggest).
BAKE = "--no-bake" not in sys.argv
BAKE_SIZE = 1024
ATLAS = os.path.join(ROOT, "textures", "boat", "gear_atlas.png")
UNBAKED = ("NetPanel", "Trawl", "Line")
PAINT_KIND = {"skiff_hull": "paint", "float_white": "paint", "skiff_bottom": "bottom", "skiff_inside": "wood",
              "door_wood": "wood", "steel": "metal", "lead": "metal", "chain": "metal", "motor": "metal",
              "rope": "weave", "net": "skip", "line": "skip"}


def _n(nt, kind, **inputs):
    made = nt.nodes.new(kind)
    for key, value in inputs.items():
        made.inputs[key].default_value = value
    return made


def _noise(nt, coords, scale, stretch=(1.0, 1.0, 1.0), detail=3.0, rough=0.55, shift=(0.0, 0.0, 0.0)):
    mapping = _n(nt, "ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = stretch
    mapping.inputs["Location"].default_value = shift
    nt.links.new(coords, mapping.inputs["Vector"])
    noise = _n(nt, "ShaderNodeTexNoise", Scale=scale, Detail=detail, Roughness=rough)
    nt.links.new(mapping.outputs["Vector"], noise.inputs["Vector"])
    return noise.outputs["Fac"]


def _ramp(nt, value, low, high):
    ramp = _n(nt, "ShaderNodeMapRange")
    ramp.interpolation_type = "SMOOTHSTEP"
    ramp.inputs["From Min"].default_value = low
    ramp.inputs["From Max"].default_value = high
    nt.links.new(value, ramp.inputs["Value"])
    return ramp.outputs["Result"]


def _mix(nt, a, b, fac, amount=1.0):
    mix = nt.nodes.new("ShaderNodeMixRGB")
    scaled = _n(nt, "ShaderNodeMath")
    scaled.operation = "MULTIPLY"
    nt.links.new(fac, scaled.inputs[0])
    scaled.inputs[1].default_value = amount
    nt.links.new(scaled.outputs[0], mix.inputs["Fac"])
    for slot, value in (("Color1", a), ("Color2", b)):
        if isinstance(value, tuple):
            mix.inputs[slot].default_value = (*value[:3], 1.0)
        else:
            nt.links.new(value, mix.inputs[slot])
    return mix.outputs["Color"]


def _paint_for_bake(mat):
    rgb = COLOURS[mat.name][0]
    kind = PAINT_KIND.get(mat.name, "plain")
    nt = mat.node_tree
    nt.nodes.clear()
    out = _n(nt, "ShaderNodeOutputMaterial")
    bsdf = _n(nt, "ShaderNodeBsdfPrincipled", Roughness=1.0, Metallic=0.0)
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    where = _n(nt, "ShaderNodeTexCoord").outputs["Object"]
    col = _mix(nt, tuple(rgb), tuple(c * 0.84 for c in rgb), _ramp(nt, _noise(nt, where, 1.4, detail=2.0), 0.35, 0.75), 0.6)
    if kind == "paint":
        chips = _ramp(nt, _noise(nt, where, 3.2, detail=3.0, rough=0.5, shift=(2.0, 5.0, 1.0)), 0.69, 0.71)
        col = _mix(nt, col, (0.30, 0.24, 0.19), chips, 0.85)
        runs = _ramp(nt, _noise(nt, where, 5.0, (5.0, 5.0, 0.35), 4.0, 0.6, (7.0, 3.0, 0.0)), 0.52, 0.72)
        col = _mix(nt, col, tuple(c * 0.62 for c in rgb), runs, 0.5)
    elif kind == "bottom":
        col = _mix(nt, col, tuple(c * 0.55 for c in rgb), _ramp(nt, _noise(nt, where, 3.0, detail=5.0, rough=0.65), 0.45, 0.7), 0.6)
    elif kind == "wood":
        grain = _noise(nt, where, 6.0, (14.0, 0.5, 14.0), 6.0, 0.62)
        col = _mix(nt, col, tuple(c * 0.62 for c in rgb), _ramp(nt, grain, 0.42, 0.62), 0.7)
        col = _mix(nt, col, (0.40, 0.38, 0.34), _ramp(nt, _noise(nt, where, 2.0, shift=(1.0, 8.0, 3.0)), 0.45, 0.75), 0.3)
    elif kind == "metal":
        col = _mix(nt, col, (0.30, 0.15, 0.07), _ramp(nt, _noise(nt, where, 18.0, detail=5.0, rough=0.65), 0.55, 0.7), 0.5)
    elif kind == "weave":
        col = _mix(nt, col, tuple(c * 0.7 for c in rgb), _ramp(nt, _noise(nt, where, 60.0, (1.0, 1.0, 3.0), 2.0), 0.4, 0.6), 0.6)
    ao = _n(nt, "ShaderNodeAmbientOcclusion", Distance=0.12)
    ao.samples = 16
    inv = _n(nt, "ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    nt.links.new(ao.outputs["AO"], inv.inputs[1])
    col = _mix(nt, col, (0.10, 0.08, 0.06), inv.outputs[0], 0.7)
    nt.links.new(col, bsdf.inputs["Base Color"])


def _paint_from_atlas(mat, image):
    colour, metal, rough = COLOURS[mat.name]
    nt = mat.node_tree
    nt.nodes.clear()
    out = _n(nt, "ShaderNodeOutputMaterial")
    bsdf = _n(nt, "ShaderNodeBsdfPrincipled", Roughness=rough, Metallic=min(metal, 0.5))
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = image
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])


def bake_paint(objects):
    """The gear's paint, baked into one picture (see above)."""
    import time
    started = time.time()
    baked = [o for o in objects if o.name not in UNBAKED]
    # (what the unbaked parts share with the baked ones keeps a plain copy of its own)
    for obj in objects:
        if obj.name in UNBAKED:
            for k, slot in enumerate(obj.data.materials):
                if slot.name not in ("net", "line"):
                    plain = slot.copy()
                    plain.name = slot.name + "_plain"
                    obj.data.materials[k] = plain
    bpy.ops.object.select_all(action="DESELECT")
    for obj in baked:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = baked[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60.0), island_margin=0.003)
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(margin=0.003)
    bpy.ops.object.mode_set(mode="OBJECT")
    painted = sorted({slot.name for o in baked for slot in o.data.materials if slot.name not in ("net", "line")})
    for name in painted:
        _paint_for_bake(bpy.data.materials[name])
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 96
    scene.cycles.device = "CPU"
    world = bpy.data.worlds.new("sky")
    world.use_nodes = True
    wt = world.node_tree
    bg = next(n for n in wt.nodes if n.type == "BACKGROUND")
    up = wt.nodes.new("ShaderNodeSeparateXYZ")
    wt.links.new(wt.nodes.new("ShaderNodeTexCoord").outputs["Generated"], up.inputs[0])
    sky = wt.nodes.new("ShaderNodeMapRange")
    sky.inputs["From Min"].default_value = -1.0
    sky.inputs["To Min"].default_value = 0.4
    sky.inputs["To Max"].default_value = 1.12
    wt.links.new(up.outputs["Z"], sky.inputs["Value"])
    wt.links.new(sky.outputs["Result"], bg.inputs["Strength"])
    bg.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    scene.world = world
    image = bpy.data.images.new("gear_atlas", BAKE_SIZE, BAKE_SIZE, alpha=False)
    for name in painted:
        nt = bpy.data.materials[name].node_tree
        node = nt.nodes.new("ShaderNodeTexImage")
        node.image = image
        nt.nodes.active = node
    scene.render.bake.margin = 3
    bpy.ops.object.select_all(action="DESELECT")
    for obj in baked:
        obj.select_set(True)
    # (every part sits at the origin as built: stood apart for the bake, or each shades the others)
    for k, obj in enumerate(objects):
        obj.location.x += 12.0 * k
    bpy.context.view_layer.update()
    bpy.context.view_layer.objects.active = baked[0]
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"DIRECT", "INDIRECT", "COLOR"}, use_clear=True)
    for k, obj in enumerate(objects):
        obj.location.x -= 12.0 * k
    bpy.context.view_layer.update()
    os.makedirs(os.path.dirname(ATLAS), exist_ok=True)
    image.filepath_raw = ATLAS
    image.file_format = "PNG"
    image.save()
    for name in painted:
        _paint_from_atlas(bpy.data.materials[name], image)
    print("BAKED %s (%d px) in %.0f s" % (ATLAS, BAKE_SIZE, time.time() - started))


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    builds = [hook(), worm(), bait_fish(), sinker(), bobber(), net_float(), net_weight(), marker_buoy(), otter_door(),
              skiff(), net_panel(), trawl(), line()]
    wrong_all = 0
    total = 0
    for b in builds:
        wrong, bad = b.inside_out()
        wrong_all += wrong
        total += b.tris()
        print("GEAR %s: %d triangles, %d facing inwards" % (b.name, b.tris(), wrong))
        for label, count, of, where in bad:
            print("   bad part %s: %d of %d at %s" % (label, count, of, where))
    print("TRIANGLES total: %d" % total)
    print("INSIDE-OUT %s" % ("PASSED" if wrong_all == 0 else "FAILED (%d)" % wrong_all))
    objects = [b.make() for b in builds]
    if BAKE:
        bake_paint(objects)
    os.makedirs(os.path.dirname(BLEND), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND)
    bpy.ops.object.select_all(action="DESELECT")
    kw = dict(filepath=GLB, export_format="GLB", export_apply=True, export_yup=True, export_cameras=False,
              export_lights=False, export_animations=False)
    if BAKE:
        kw["export_image_format"] = "JPEG"
    bpy.ops.export_scene.gltf(**kw)
    print("WROTE", GLB)
    if ARGS:
        os.makedirs(ARGS[0], exist_ok=True)
        render(ARGS[0], objects)


main()
