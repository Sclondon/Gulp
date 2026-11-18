"""Builds the shrimp boat of the title screen: an old wooden Gulf of Mexico shrimp trawler.

    "C:/Program Files/Blender Foundation/Blender 4.3/blender.exe" --background --python tools/build_shrimp_boat.py

Writes models/shrimp_boat.glb and tools/blend/shrimp_boat.blend. The user (2026-11-18): "the main menu / start of
the game should be the boy from warren, a sea captain, and and oldtimy diver on a shrimping boat (look up reference
pics). In the open back cabin of the shrimping boat should be a old timey franketstein computer hooked up to a helmet
on the boys head". This file is only the boat; the figures, the computer and the helmet are made elsewhere.

The shape follows the usual Florida-style double-rigged shrimper (house forward, working deck aft, two outriggers
from the mast with a net and a pair of otter doors on each), from reference photos for shape only.

Axes (Blender): Z up, the bow towards +Y, starboard +X. The glTF exporter turns +Y into Godot's -Z, so in Godot the
bow points to -Z and starboard is +X. The origin is on the centre line amidships at the waterline (z = 0 is the sea's
surface); the hull goes on below it to the keel at about -0.9 m.

Objects (each a node of the .glb):
  Boat                 everything fixed, one mesh
  Wheel                the ship's wheel in the wheelhouse, origin at its hub, turns about local Y (Godot Z)
  OutriggerPort        the port outrigger with its net, floats, door and lines, origin at its hinge on the mast
  OutriggerStarboard   the same on the starboard side; both turn about local Y (Godot Z) to raise or lower
  ConsoleSpot, BoySpot, CaptainSpot, DiverSpot, HelmetCable, Waterline   empties (Godot Node3D): marker points.
  Each spot is a floor point; its -Z in Godot is the way that figure or thing faces.

Materials are plain colours with names (no image textures). A colour attribute "Col" multiplies them (plank tints,
grime at the boot top, the dark seams between planks, the mesh pattern of the nets) and is exported as COLOR_0.

Every part is a closed solid; each is checked for inside-out faces here (a ray out of every triangle must leave the
part's skin an even number of times) and the count is printed as the INSIDE-OUT line.
"""
import bpy
import math
import os
import random
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import tessellate_polygon

HERE = os.path.dirname(os.path.abspath(__file__))
GLB = os.path.normpath(os.path.join(HERE, "..", "models", "shrimp_boat.glb"))
BLEND = os.path.join(HERE, "blend", "shrimp_boat.blend")

bpy.ops.wm.read_factory_settings(use_empty=True)
RNG = random.Random(11)

MATERIALS = [
    ("hull_white", (0.86, 0.85, 0.80)),
    ("hull_stripe", (0.08, 0.32, 0.36)),
    ("bottom_red", (0.46, 0.15, 0.10)),
    ("deck_wood", (0.56, 0.47, 0.36)),
    ("cabin_wood", (0.55, 0.38, 0.22)),
    ("trim", (0.34, 0.22, 0.13)),
    ("roof", (0.72, 0.72, 0.68)),
    ("glass", (0.10, 0.15, 0.19)),
    ("net_green", (0.17, 0.31, 0.19)),
    ("rope", (0.68, 0.60, 0.44)),
    ("wire", (0.24, 0.24, 0.25)),
    ("metal_rust", (0.43, 0.25, 0.15)),
    ("metal_dark", (0.14, 0.14, 0.15)),
    ("brass", (0.74, 0.56, 0.24)),
    ("float_orange", (0.93, 0.42, 0.10)),
    ("door_wood", (0.30, 0.25, 0.19)),
    ("life_red", (0.78, 0.13, 0.10)),
    ("crate_wood", (0.60, 0.48, 0.31)),
    ("basket", (0.71, 0.62, 0.40)),
    ("hose_rubber", (0.20, 0.18, 0.16)),
    ("lamp_glass", (0.95, 0.90, 0.70)),
    ("mast_white", (0.80, 0.78, 0.72)),
]
MAT_NAMES = [m[0] for m in MATERIALS]

WHITE = (1.0, 1.0, 1.0)


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def smoothstep(a, b, x):
    t = clamp((x - a) / (b - a))
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------------------------------------- hull shape
LENGTH = 13.0
HALF = 6.5
T = 0.10   # bulwark thickness


def u_of(y):
    return (y + HALF) / LENGTH


def deck(y):
    """Deck height (the hull's deck surface; planks sit on it, their tops 3 cm higher)."""
    if y <= 2.0:
        return 0.80 + (y + HALF) / 8.5 * 0.12
    return 0.92 + 0.58 * ((y - 2.0) / 4.5) ** 2


def deck_top(y):
    return deck(y) + 0.03


def bulwark_h(y):
    return 0.55 + 0.2 * max(0.0, (y - 2.0) / 4.5) ** 2


def sheer(y):
    return deck(y) + bulwark_h(y)


def sheer_half(u):
    if u < 0.45:
        return 2.1 - 0.25 * ((0.45 - u) / 0.45) ** 2
    t = (u - 0.45) / 0.55
    return 2.1 * math.sqrt(max(0.0, 1 - t ** 2.6))


def water_half(u):
    return sheer_half(u) * (0.92 - 0.3 * smoothstep(0.55, 1.0, u))


def keel(u):
    if u < 0.7:
        return -0.15 - 0.75 * smoothstep(0.0, 0.18, u)
    return -0.9 + 0.45 * smoothstep(0.7, 1.0, u)


def bilge_p(u):
    return 2.6 - 1.45 * smoothstep(0.45, 1.0, u)


def rake(u):
    return 1.8 * smoothstep(0.62, 1.0, u)


def outer_half(u, z, sh):
    bs = sheer_half(u)
    bw = water_half(u)
    if z >= 0:
        return bw + (bs - bw) * clamp(z / sh) ** 0.7
    s = clamp(z / keel(u))
    return max(min(0.07, bw), bw * (1 - s ** bilge_p(u)))


def inner_half(y):
    """Half the deck's width between the bulwarks, at deck height."""
    u = u_of(y)
    return max(0.0, outer_half(u, deck(y), sheer(y)) - T)


# ---------------------------------------------------------------------------------------------- builder
def newell(pts):
    n = Vector((0, 0, 0))
    for i in range(len(pts)):
        a = pts[i]
        b = pts[(i + 1) % len(pts)]
        n.x += (a.y - b.y) * (a.z + b.z)
        n.y += (a.z - b.z) * (a.x + b.x)
        n.z += (a.x - b.x) * (a.y + b.y)
    return n


class Build:
    """One exported mesh object, made of closed parts."""

    def __init__(self, name, origin=(0, 0, 0)):
        self.name = name
        self.origin = Vector(origin)
        self.verts = []
        self.cols = []
        self.tris = []
        self.mats = []
        self.parts = []   # (label, first tri, end tri)

    def part(self, label, verts, polys, mats, cols=None, convex=False):
        V = [Vector(v) for v in verts]
        if cols is None:
            cols = [WHITE] * len(V)
        elif not isinstance(cols[0], (tuple, list)):
            cols = [tuple(cols)] * len(V)
        centre = sum(V, Vector()) / len(V)
        tris = []
        tmats = []
        for pi, poly in enumerate(polys):
            m = mats if isinstance(mats, str) else mats[pi]
            if len(poly) == 3:
                tt = [tuple(poly)]
            elif len(poly) == 4:
                tt = [(poly[0], poly[1], poly[2]), (poly[0], poly[2], poly[3])]
            else:
                pts = [V[i] for i in poly]
                n = newell(pts)
                tt = []
                for a, b, c in tessellate_polygon([pts]):
                    t = (poly[a], poly[b], poly[c])
                    if (V[t[1]] - V[t[0]]).cross(V[t[2]] - V[t[0]]).dot(n) < 0:
                        t = (t[0], t[2], t[1])
                    tt.append(t)
            for t in tt:
                a, b, c = V[t[0]], V[t[1]], V[t[2]]
                nrm = (b - a).cross(c - a)
                if nrm.length < 1e-9:
                    continue
                if convex and nrm.dot((a + b + c) / 3 - centre) < 0:
                    t = (t[0], t[2], t[1])
                tris.append(t)
                tmats.append(m)
        vol = sum(V[a].dot(V[b].cross(V[c])) for a, b, c in tris) / 6.0
        if vol < 0:
            tris = [(a, c, b) for a, b, c in tris]
        base = len(self.verts)
        self.verts.extend(V)
        self.cols.extend(cols)
        first = len(self.tris)
        self.tris.extend((a + base, b + base, c + base) for a, b, c in tris)
        self.mats.extend(tmats)
        self.parts.append((label, first, len(self.tris)))

    def inside_out(self):
        """(faces facing inwards, faces looked at), part by part."""
        wrong = 0
        counted = 0
        bad_parts = []
        for label, f0, f1 in self.parts:
            tris = self.tris[f0:f1]
            used = sorted({i for t in tris for i in t})
            remap = {v: k for k, v in enumerate(used)}
            pts = [self.verts[i] for i in used]
            polys = [(remap[a], remap[b], remap[c]) for a, b, c in tris]
            tree = BVHTree.FromPolygons(pts, polys, epsilon=0.0)
            bad = 0
            where = []
            for a, b, c in polys:
                pa, pb, pc = pts[a], pts[b], pts[c]
                n = (pb - pa).cross(pc - pa)
                if n.length < 1e-10:
                    continue
                n.normalize()
                counted += 1
                odd = True
                # a ray that grazes an edge can count one crossing twice: a face is wrong only if
                # rays from two different points of it both say so
                for wa, wb, wc in ((1 / 3, 1 / 3, 1 / 3), (0.45, 0.33, 0.22)):
                    at = pa * wa + pb * wb + pc * wc + n * 2e-5
                    hits = 0
                    while hits < 60:
                        hit = tree.ray_cast(at, n)
                        if hit[0] is None:
                            break
                        hits += 1
                        at = hit[0] + n * 2e-5
                    if hits % 2 == 0:
                        odd = False
                        break
                if odd:
                    bad += 1
                    where.append(tuple(round(c, 2) for c in (pa + pb + pc) / 3))
            if bad:
                bad_parts.append((label, bad, len(polys), where[:8]))
            wrong += bad
        return wrong, counted, bad_parts

    def make(self):
        mesh = bpy.data.meshes.new(self.name)
        mesh.from_pydata([v - self.origin for v in self.verts], [], self.tris)
        used = []
        for m in self.mats:
            if m not in used:
                used.append(m)
        used.sort()
        for m in used:
            mesh.materials.append(bpy.data.materials[m])
        mesh.polygons.foreach_set("material_index", [used.index(m) for m in self.mats])
        attr = mesh.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
        flat = []
        for c in self.cols:
            flat.extend((c[0], c[1], c[2], 1.0))
        attr.data.foreach_set("color", flat)
        mesh.color_attributes.active_color_name = "Col"
        mesh.color_attributes.render_color_index = mesh.color_attributes.find("Col")
        mesh.update()
        mesh.validate()
        obj = bpy.data.objects.new(self.name, mesh)
        bpy.context.scene.collection.objects.link(obj)
        obj.location = self.origin
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(38))
        return obj


# ---------------------------------------------------------------------------------------------- primitives
def box_corners(c):
    """Eight corners: bottom four round, then top four round. Returns (verts, polys)."""
    polys = [[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
    return c, polys


def box(b, x0, x1, y0, y1, z0, z1, mat, col=None, label="box"):
    c = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    v, p = box_corners(c)
    b.part(label, v, p, mat, col, convex=True)


def obox(b, centre, ax, ay, az, mat, col=None, label="obox"):
    c = Vector(centre)
    ax, ay, az = Vector(ax), Vector(ay), Vector(az)
    pts = []
    for sz in (-1, 1):
        for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            pts.append(c + ax * sx + ay * sy + az * sz)
    v, p = box_corners(pts)
    b.part(label, v, p, mat, col, convex=True)


def beam(b, p0, p1, w, h, mat, up=(0, 0, 1), col=None, label="beam"):
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    up = Vector(up)
    if abs(d.normalized().dot(up)) > 0.95:
        up = Vector((1, 0, 0))
    side = d.cross(up).normalized() * (w / 2)
    upv = side.cross(d).normalized() * (h / 2)
    obox(b, (p0 + p1) / 2, d / 2, side, upv, mat, col, label)


def frames(path, closed=False):
    """Parallel-transport frames (n, b) along a path; (n, b, tangent) is right-handed."""
    P = [Vector(p) for p in path]
    m = len(P)
    tangents = []
    for k in range(m):
        if closed:
            t = P[(k + 1) % m] - P[k - 1]
        elif k == 0:
            t = P[1] - P[0]
        elif k == m - 1:
            t = P[-1] - P[-2]
        else:
            t = P[k + 1] - P[k - 1]
        tangents.append(t.normalized())
    t0 = tangents[0]
    ref = Vector((0, 0, 1)) if abs(t0.z) < 0.9 else Vector((1, 0, 0))
    n = (ref - t0 * ref.dot(t0)).normalized()
    out = []
    for k in range(m):
        if k > 0:
            q = tangents[k - 1].rotation_difference(tangents[k])
            n = q @ n
            n = (n - tangents[k] * n.dot(tangents[k])).normalized()
        out.append((n.copy(), tangents[k].cross(n), tangents[k]))
    return P, out


def tube(b, path, radii, sides, mat, closed=False, cols=None, jitter=None, label="tube", ring_shift=None):
    """A tube round a path, capped at both ends unless the path is a closed loop. mat may be a
    function (k, j) -> name for the face starting at ring k, side j."""
    P, F = frames(path, closed)
    m = len(P)
    if not isinstance(radii, (list, tuple)):
        radii = [radii] * m
    verts = []
    for k in range(m):
        n, bb, _ = F[k]
        for j in range(sides):
            a = 2 * math.pi * j / sides
            r = radii[k] * (jitter(k, j) if jitter else 1.0)
            verts.append(P[k] + (n * math.cos(a) + bb * math.sin(a)) * r)
    polys = []
    pm = []
    for k in range(m if closed else m - 1):
        k1 = (k + 1) % m
        for j in range(sides):
            j1 = (j + 1) % sides
            polys.append([k * sides + j, k * sides + j1, k1 * sides + j1, k1 * sides + j])
            pm.append(mat(k, j) if callable(mat) else mat)
    if not closed:
        cap_m = mat(0, 0) if callable(mat) else mat
        polys.append([j for j in reversed(range(sides))])
        pm.append(cap_m)
        polys.append([(m - 1) * sides + j for j in range(sides)])
        pm.append(mat(m - 1, 0) if callable(mat) else mat)
    if cols is not None and callable(cols):
        cols = [cols(k, j) for k in range(m) for j in range(sides)]
    b.part(label, verts, polys, pm, cols)


def cyl(b, p0, p1, r0, r1, sides, mat, col=None, label="cyl"):
    tube(b, [p0, p1], [r0, r1], sides, mat, cols=col, label=label)


def torus(b, centre, axis, R, r, segs, sides, mat, label="torus", cols=None):
    axis = Vector(axis).normalized()
    ref = Vector((0, 0, 1)) if abs(axis.z) < 0.9 else Vector((1, 0, 0))
    e1 = (ref - axis * ref.dot(axis)).normalized()
    e2 = axis.cross(e1)
    c = Vector(centre)
    path = [c + (e1 * math.cos(2 * math.pi * i / segs) + e2 * math.sin(2 * math.pi * i / segs)) * R for i in range(segs)]
    tube(b, path, r, sides, mat, closed=True, label=label, cols=cols)


def sphere(b, centre, r, segs, rings, mat, label="sphere", squash=(1, 1, 1)):
    c = Vector(centre)
    verts = [c + Vector((0, 0, -r * squash[2]))]
    for i in range(1, rings):
        th = math.pi * i / rings - math.pi / 2
        for j in range(segs):
            ph = 2 * math.pi * j / segs
            verts.append(c + Vector((math.cos(th) * math.cos(ph) * r * squash[0],
                                     math.cos(th) * math.sin(ph) * r * squash[1], math.sin(th) * r * squash[2])))
    verts.append(c + Vector((0, 0, r * squash[2])))
    top = len(verts) - 1
    polys = []
    for j in range(segs):
        polys.append([0, 1 + (j + 1) % segs, 1 + j])
    for i in range(rings - 2):
        for j in range(segs):
            a = 1 + i * segs + j
            bq = 1 + i * segs + (j + 1) % segs
            polys.append([a, bq, bq + segs, a + segs])
    last = 1 + (rings - 2) * segs
    for j in range(segs):
        polys.append([last + j, last + (j + 1) % segs, top])
    b.part(label, verts, polys, mat, convex=True)


def prism(b, pts2d, origin, eu, ev, half, mat, label="prism", side_mat=None, col=None):
    """A flat polygon (convex or not) in the plane origin + u*eu + v*ev, thickened by half either way."""
    pts = list(pts2d)
    area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
    if area < 0:
        pts.reverse()
    o, eu, ev = Vector(origin), Vector(eu), Vector(ev)
    en = eu.cross(ev).normalized()
    n = len(pts)
    verts = [o + eu * u + ev * v - en * half for u, v in pts] + [o + eu * u + ev * v + en * half for u, v in pts]
    polys = [[j for j in reversed(range(n))], [n + j for j in range(n)]]
    pm = [mat, mat]
    for i in range(n):
        i1 = (i + 1) % n
        polys.append([i, i1, n + i1, n + i])
        pm.append(side_mat or mat)
    b.part(label, verts, polys, pm, col)


def wall(b, axis, t0, t1, a0, a1, z0, z1, holes, mat, label="wall"):
    """An axis-aligned wall (axis 'x': the wall's thickness is along x, it runs along y) with
    rectangular holes (a0, a1, z0, z1), made of boxes."""
    cuts = sorted({a0, a1} | {h[0] for h in holes} | {h[1] for h in holes})
    cuts = [c for c in cuts if a0 <= c <= a1]
    for s0, s1 in zip(cuts, cuts[1:]):
        over = sorted((h for h in holes if h[0] <= s0 + 1e-6 and h[1] >= s1 - 1e-6), key=lambda h: h[2])
        cur = z0
        spans = []
        for h in over:
            if h[2] > cur + 1e-6:
                spans.append((cur, h[2]))
            cur = max(cur, h[3])
        if cur < z1 - 1e-6:
            spans.append((cur, z1))
        for za, zb in spans:
            if axis == "x":
                box(b, t0, t1, s0, s1, za, zb, mat, label=label)
            else:
                box(b, s0, s1, t0, t1, za, zb, mat, label=label)


def catmull(points, per):
    P = [Vector(p) for p in points]
    out = []
    for i in range(len(P) - 1):
        p0 = P[max(i - 1, 0)]
        p1, p2 = P[i], P[i + 1]
        p3 = P[min(i + 2, len(P) - 1)]
        for s in range(per):
            t = s / per
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t))
    out.append(P[-1])
    return out


# ---------------------------------------------------------------------------------------------- materials
for name, rgb in MATERIALS:
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Roughness"].default_value = 0.35 if name in ("glass", "lamp_glass", "brass") else 0.85
    if name == "brass":
        bsdf.inputs["Metallic"].default_value = 0.6
    if name == "glass":
        # see-through, so that the wheel shows inside (exported as alphaMode BLEND)
        bsdf.inputs["Alpha"].default_value = 0.4
        mat.surface_render_method = "BLENDED"
    vc = nt.nodes.new("ShaderNodeVertexColor")
    vc.layer_name = "Col"
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = 1.0
    mix.inputs[6].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    nt.links.new(vc.outputs["Color"], mix.inputs[7])
    nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    mat.diffuse_color = (rgb[0], rgb[1], rgb[2], 1.0)
    if name.endswith("_2sided"):
        mat.use_backface_culling = False
    else:
        mat.use_backface_culling = True

# ---------------------------------------------------------------------------------------------- the boat
boat = Build("Boat")

# --- hull: a loft of cross-sections from the transom (u = 0) to the stem (u = 1), deck and bulwarks included
STATIONS = [0.0, 0.02, 0.06, 0.12, 0.2, 0.28, 0.36, 0.44, 0.52, 0.6, 0.66, 0.72, 0.77, 0.81, 0.85, 0.88,
            0.91, 0.935, 0.955, 0.97, 0.985, 1.0]
SEG_STAR = ["deck_wood", "hull_white", "trim", "hull_stripe", "hull_white", "hull_white",
            "bottom_red", "bottom_red", "bottom_red", "bottom_red", "bottom_red", "bottom_red", "bottom_red"]
GRIME = (0.86, 0.83, 0.76)


def station(u):
    y = -HALF + LENGTH * u
    d = deck(y)
    sh = sheer(y)
    k = keel(u)
    r = rake(u)
    bs = sheer_half(u)

    def yy(z):
        # the stem rakes below the deck only, so that the bulwark's inside (straight up from the deck's
        # edge) stays inside its outside
        return y - r * max(0.0, d - z) / (d - k)

    S = [(max(0.0, outer_half(u, d, sh) - T), y, d),
         (max(0.0, bs - T), y, sh),
         (bs, y, sh)]
    C = [(0.35, 0.33, 0.30), (0.95, 0.94, 0.92), WHITE]
    zs = [sh - 0.26, d, 0.15, 0.0] + [k * f for f in (0.3, 0.55, 0.75, 0.9)]
    zc = [WHITE, (0.95, 0.94, 0.91), GRIME, (0.9, 0.86, 0.82), WHITE, WHITE, WHITE, WHITE]
    for z, c in zip(zs, zc):
        S.append((outer_half(u, z, sh), yy(z), z))
        C.append(c)
    S.append((0.07 * min(1.0, bs / 0.3), yy(k), k))
    C.append(WHITE)
    ring = [(0.0, y, d)] + S + [(0.0, yy(k), k)] + [(-x, yv, z) for x, yv, z in reversed(S)]
    cols = [(0.3, 0.28, 0.26)] + C + [WHITE] + list(reversed(C))
    return ring, cols


rings = [station(u) for u in STATIONS]
N = len(rings[0][0])
hverts = []
hcols = []
for ring, cols in rings:
    hverts.extend(ring)
    hcols.extend(cols)
seg_mats = SEG_STAR + list(reversed(SEG_STAR))
polys = []
pm = []
for k in range(len(STATIONS) - 1):
    for i in range(N):
        i1 = (i + 1) % N
        polys.append([k * N + i, k * N + i1, (k + 1) * N + i1, (k + 1) * N + i])
        pm.append(seg_mats[i])
polys.append([i for i in reversed(range(N))])   # the transom
pm.append("hull_white")
boat.part("hull", hverts, polys, pm, hcols)

# rub rail along the bottom of the sheer stripe, and a stem bar
for s in (1, -1):
    pts = []
    for u in STATIONS:
        if u > 0.955:
            break
        ring, _ = station(u)
        x, y, z = ring[4]
        pts.append((s * (x + 0.03), y, z))
    tube(boat, pts, 0.045, 6, "trim", label="rub rail")
last, _ = station(1.0)
prev, _ = station(0.985)
stem = [last[3]] + [last[i] for i in range(4, 13)]
stem = [(0.0, y + 0.02, z) for _, y, z in stem]
tube(boat, stem, 0.055, 6, "trim", label="stem bar")

# transom bulwark board and its cap
yt = -HALF
ih = inner_half(yt + 0.1)
box(boat, -ih - 0.05, ih + 0.05, yt, yt + 0.1, deck(yt) - 0.05, sheer(yt), "hull_white", label="transom board")
box(boat, -sheer_half(0.0) - 0.02, sheer_half(0.0) + 0.02, yt - 0.03, yt + 0.12, sheer(yt), sheer(yt) + 0.05, "trim",
    label="transom cap")

# skeg, rudder, shoe, propeller
prism(boat, [(-5.25, -0.2), (-5.25, -0.95), (-2.4, -0.95), (-1.2, -0.7), (-3.5, -0.35)],
      (0, 0, 0), (0, 1, 0), (0, 0, 1), 0.07, "bottom_red", label="skeg")
prism(boat, [(-6.35, -0.12), (-6.35, -0.85), (-5.85, -0.85), (-5.85, -0.12)],
      (0, 0, 0), (0, 1, 0), (0, 0, 1), 0.04, "bottom_red", label="rudder")
box(boat, -0.05, 0.05, -6.35, -5.2, -0.99, -0.93, "metal_rust", label="shoe")
cyl(boat, (0, -5.72, -0.55), (0, -5.24, -0.55), 0.08, 0.08, 8, "brass", label="prop hub")
for i in range(4):
    a = math.pi / 2 * i + 0.4
    radial = Vector((math.cos(a), 0, math.sin(a)))
    tang = Vector((0, 1, 0)).cross(radial)
    tw = Matrix.Rotation(math.radians(35), 3, radial)
    obox(boat, Vector((0, -5.5, -0.55)) + radial * 0.22, radial * 0.15, tw @ (tang * 0.08), tw @ Vector((0, 0.012, 0)),
         "brass", label="prop blade")

# --- deck planks (gaps between them show the dark deck below)
PW = 0.15
GAP = 0.014


def plank_fits(xc, y):
    return abs(xc) + PW / 2 <= inner_half(y) - 0.01


Y_AFT = -HALF + 0.1
Y_FWD = 6.3
for i in range(-13, 13):
    xc = (i + 0.5) * PW
    ys = [Y_AFT + 0.05 * n for n in range(int((Y_FWD - Y_AFT) / 0.05) + 1)]
    fit = [y for y in ys if plank_fits(xc, y)]
    if not fit:
        continue
    ya, yb = fit[0], fit[-1]
    off = (i * 1.37) % 3.0
    cuts = [ya]
    c = Y_AFT + 1.0 + off
    while c < 2.0:
        if c > ya + 0.3:
            cuts.append(c)
        c += 3.0
    c = 2.0
    while c < yb:
        if c > cuts[-1] + 0.2:
            cuts.append(c)
        c += 0.45
    cuts.append(yb)
    x0 = xc - PW / 2 + GAP / 2
    x1 = xc + PW / 2 - GAP / 2
    for y0, y1 in zip(cuts, cuts[1:]):
        y1 = y1 - 0.008
        if y1 - y0 < 0.1:
            continue
        v = 0.8 + 0.2 * RNG.random()
        if RNG.random() < 0.12:
            v *= 0.82
        col = (v, v * 0.98, v * 0.94)
        c8 = [(x0, y0, deck(y0) - 0.012), (x1, y0, deck(y0) - 0.012), (x1, y1, deck(y1) - 0.012), (x0, y1, deck(y1) - 0.012),
              (x0, y0, deck_top(y0)), (x1, y0, deck_top(y0)), (x1, y1, deck_top(y1)), (x0, y1, deck_top(y1))]
        vv, pp = box_corners(c8)
        boat.part("plank", vv, pp, "deck_wood", col, convex=True)

# bulwark frames inside the bulwark, and cleats on the rail cap
for y in (-5.8, -4.6, -3.4, -2.2, -1.0, 4.6):
    u = u_of(y)
    ih = inner_half(y)
    it = sheer_half(u) - T
    d = deck(y)
    sh = sheer(y)
    for s in (1, -1):
        def X(x):
            return s * x
        c8 = [(X(ih - 0.05), y - 0.05, d), (X(ih + 0.05), y - 0.05, d), (X(ih + 0.05), y + 0.05, d), (X(ih - 0.05), y + 0.05, d),
              (X(it - 0.05), y - 0.05, sh), (X(it + 0.05), y - 0.05, sh), (X(it + 0.05), y + 0.05, sh), (X(it - 0.05), y + 0.05, sh)]
        vv, pp = box_corners(c8)
        boat.part("frame", vv, pp, "hull_white", (0.93, 0.92, 0.88), convex=True)
for y in (-6.0, -1.3, 4.9):
    u = u_of(y)
    xm = sheer_half(u) - T / 2
    sh = sheer(y)
    for s in (1, -1):
        box(boat, s * xm - 0.03, s * xm + 0.03, y - 0.06, y + 0.06, sh - 0.01, sh + 0.07, "metal_dark", label="cleat post")
        cyl(boat, (s * xm, y - 0.17, sh + 0.08), (s * xm, y + 0.17, sh + 0.08), 0.022, 0.022, 6, "metal_dark",
            label="cleat horn")

# --- wheelhouse (forward) with windows and a door
WH_X = 1.35
WH_Y0, WH_Y1 = 1.6, 3.9
WT = 0.08
WH_Z0 = deck(WH_Y0) - 0.08
WH_TOP = 3.07
win_front = [(-1.05, -0.45, 2.05, 2.7), (-0.32, 0.32, 2.05, 2.7), (0.45, 1.05, 2.05, 2.7)]
win_port = [(2.0, 2.6, 2.0, 2.65), (2.95, 3.55, 2.0, 2.65)]
win_star = [(2.95, 3.55, 2.0, 2.65)]
door = (1.85, 2.5, WH_Z0, 2.85)
wall(boat, "y", WH_Y1 - WT, WH_Y1, -WH_X, WH_X, WH_Z0, WH_TOP, win_front, "hull_white", "wheelhouse front")
wall(boat, "y", WH_Y0, WH_Y0 + WT, -WH_X, WH_X, WH_Z0, WH_TOP, [], "hull_white", "wheelhouse back")
wall(boat, "x", -WH_X, -WH_X + WT, WH_Y0 + WT, WH_Y1 - WT, WH_Z0, WH_TOP, win_port, "hull_white", "wheelhouse port")
wall(boat, "x", WH_X - WT, WH_X, WH_Y0 + WT, WH_Y1 - WT, WH_Z0, WH_TOP, win_star + [door], "hull_white",
     "wheelhouse starboard")
for a0, a1, z0, z1 in win_front:
    box(boat, a0 - 0.01, a1 + 0.01, WH_Y1 - WT / 2 - 0.01, WH_Y1 - WT / 2 + 0.01, z0 - 0.01, z1 + 0.01, "glass", label="glass")
    box(boat, a0 - 0.04, a1 + 0.04, WH_Y1 - 0.02, WH_Y1 + 0.05, z0 - 0.06, z0, "trim", label="sill")
for a0, a1, z0, z1 in win_port:
    box(boat, -WH_X + WT / 2 - 0.01, -WH_X + WT / 2 + 0.01, a0 - 0.01, a1 + 0.01, z0 - 0.01, z1 + 0.01, "glass", label="glass")
    box(boat, -WH_X - 0.05, -WH_X + 0.02, a0 - 0.04, a1 + 0.04, z0 - 0.06, z0, "trim", label="sill")
for a0, a1, z0, z1 in win_star:
    box(boat, WH_X - WT / 2 - 0.01, WH_X - WT / 2 + 0.01, a0 - 0.01, a1 + 0.01, z0 - 0.01, z1 + 0.01, "glass", label="glass")
    box(boat, WH_X - 0.02, WH_X + 0.05, a0 - 0.04, a1 + 0.04, z0 - 0.06, z0, "trim", label="sill")
# the door, a little ajar of the wall's face, with a small window and a knob
box(boat, WH_X - 0.05, WH_X - 0.02, door[0] + 0.01, door[1] - 0.01, door[2] + 0.1, door[3] - 0.01, "cabin_wood", label="door")
box(boat, WH_X - 0.025, WH_X + 0.005, door[0] + 0.15, door[1] - 0.15, 2.2, 2.6, "glass", label="door glass")
sphere(boat, (WH_X + 0.01, door[1] - 0.1, 1.95), 0.035, 8, 5, "brass", label="knob")
for x in (-WH_X, WH_X):
    for y in (WH_Y0, WH_Y1):
        box(boat, x - 0.05, x + 0.05, y - 0.05, y + 0.05, WH_Z0, WH_TOP, "trim", label="corner post")
box(boat, -WH_X - 0.15, WH_X + 0.15, WH_Y0 - 0.1, WH_Y1 + 0.25, 3.05, 3.15, "roof", label="wheelhouse roof")
box(boat, -WH_X - 0.16, WH_X + 0.16, WH_Y1 + 0.2, WH_Y1 + 0.27, 2.98, 3.16, "trim", label="roof fascia front")
# the wheel's pedestal and a shelf of instruments under the front windows
WHEEL_HUB = Vector((0.0, 3.35, deck(3.35) + 1.05))
box(boat, -0.12, 0.12, WHEEL_HUB.y + 0.08, WHEEL_HUB.y + 0.28, deck(3.4) - 0.02, WHEEL_HUB.z + 0.12, "cabin_wood",
    label="pedestal")
cyl(boat, (0, WHEEL_HUB.y + 0.08, WHEEL_HUB.z), (0, WHEEL_HUB.y - 0.02, WHEEL_HUB.z), 0.03, 0.03, 8, "brass",
    label="axle")
box(boat, -1.25, 1.25, WH_Y1 - 0.45, WH_Y1 - WT, 1.78, 1.86, "cabin_wood", label="chart shelf")
box(boat, -1.25, 1.25, WH_Y1 - 0.4, WH_Y1 - WT, deck(3.6) - 0.02, 1.78, "cabin_wood", label="shelf front")
# roof gear: searchlight, horn, exhaust stack
cyl(boat, (0.55, 3.75, 3.15), (0.55, 3.75, 3.36), 0.045, 0.045, 8, "metal_dark", label="light post")
cyl(boat, (0.55, 3.58, 3.45), (0.55, 3.9, 3.45), 0.13, 0.12, 12, "metal_dark", label="searchlight")
cyl(boat, (0.55, 3.9, 3.45), (0.55, 3.925, 3.45), 0.105, 0.105, 12, "lamp_glass", label="searchlight lens")
cyl(boat, (-0.45, 3.55, 3.15), (-0.45, 3.55, 3.32), 0.03, 0.03, 6, "metal_dark", label="horn post")
cyl(boat, (-0.45, 3.45, 3.36), (-0.45, 3.85, 3.36), 0.025, 0.09, 10, "brass", label="horn")
cyl(boat, (-0.95, 2.3, 3.1), (-0.95, 2.3, 4.35), 0.085, 0.08, 10, "metal_dark", label="stack")
cyl(boat, (-0.95, 2.3, 4.32), (-0.95, 2.3, 4.4), 0.12, 0.12, 10, "metal_dark", label="stack cap")
cyl(boat, (-0.95, 2.3, 3.12), (-0.95, 2.3, 3.24), 0.13, 0.12, 10, "metal_rust", label="stack collar")

# --- the open-backed cabin behind the wheelhouse: roof on the wheelhouse's back wall and two aft posts,
# low walls at the sides (closed above the waist in the forward half), wholly open aft
CB_X = 1.45
CB_Y0, CB_Y1 = -0.7, WH_Y0
CB_Z0 = deck(CB_Y0) - 0.06
WAIST = deck(CB_Y0) + 1.05
CB_ROOF = 3.06     # the cabin roof's underside: 2.13 m above the cabin floor
for s in (1, -1):
    xa, xb = sorted((s * CB_X, s * (CB_X - WT)))
    box(boat, xa, xb, CB_Y0, CB_Y1, CB_Z0, WAIST, "hull_white", label="cabin low wall")
    box(boat, xa, xb, 0.45, CB_Y1, WAIST, CB_ROOF + 0.02, "hull_white", label="cabin upper wall")
    xa2, xb2 = sorted((s * (CB_X + 0.03), s * (CB_X - WT - 0.03)))
    box(boat, xa2, xb2, CB_Y0 - 0.02, 0.45, WAIST, WAIST + 0.045, "trim", label="cabin wall cap")
    xa3, xb3 = sorted((s * (CB_X + 0.01), s * (CB_X - 0.11)))
    box(boat, xa3, xb3, CB_Y0, CB_Y0 + 0.12, CB_Z0, CB_ROOF + 0.02, "trim", label="cabin aft post")
    box(boat, xa3, xb3, 0.39, 0.51, CB_Z0, CB_ROOF + 0.02, "trim", label="cabin mid post")
box(boat, -CB_X - 0.13, CB_X + 0.13, CB_Y0 - 0.15, CB_Y1 + 0.05, CB_ROOF, CB_ROOF + 0.08, "roof", label="cabin roof")
box(boat, -CB_X - 0.14, CB_X + 0.14, CB_Y0 - 0.17, CB_Y0 - 0.1, CB_ROOF - 0.06, CB_ROOF + 0.09, "trim",
    label="cabin roof fascia")
# life ring on the cabin's port side, outside
torus(boat, (-CB_X - 0.07, 1.05, 2.45), (1, 0, 0), 0.27, 0.06, 16, 7,
      lambda k, j: "life_red" if (k // 2) % 2 == 0 else "hull_white", label="life ring")
box(boat, -CB_X - 0.03, -CB_X, 1.0, 1.1, 2.68, 2.78, "metal_dark", label="ring hook")

# --- mast, crosstree, boom and standing rigging
MAST_Y = 1.85
MAST_TOP = 9.5
cyl(boat, (0, MAST_Y, deck(MAST_Y) - 0.05), (0, MAST_Y, MAST_TOP), 0.12, 0.075, 10, "mast_white", label="mast")
sphere(boat, (0, MAST_Y, MAST_TOP + 0.06), 0.08, 8, 5, "lamp_glass", label="masthead light")
box(boat, -0.7, 0.7, MAST_Y - 0.05, MAST_Y + 0.05, 7.55, 7.65, "mast_white", label="crosstree")
box(boat, -0.48, 0.48, MAST_Y - 0.1, MAST_Y + 0.1, 3.36, 3.62, "metal_rust", label="outrigger collar")
BOOM0 = Vector((0, MAST_Y - 0.12, 4.05))
BOOM1 = Vector((0, -3.4, 5.45))
cyl(boat, BOOM0, BOOM1, 0.075, 0.05, 8, "mast_white", label="boom")
box(boat, -0.14, 0.14, MAST_Y - 0.2, MAST_Y + 0.0, 3.9, 4.2, "metal_rust", label="gooseneck")
LINE = 0.014
tube(boat, [(0, MAST_Y, MAST_TOP - 0.15), BOOM1 + Vector((0, 0, 0.05))], LINE, 5, "wire", label="topping lift")
block = BOOM1 + Vector((0, 0, -0.25))
box(boat, -0.05, 0.05, block.y - 0.06, block.y + 0.06, block.z - 0.12, block.z + 0.12, "metal_rust", label="boom block")
tube(boat, [BOOM1, block + Vector((0, 0, 0.1))], LINE, 5, "wire", label="block strop")
tube(boat, [block + Vector((0, 0, -0.1)), block + Vector((0, 0, -1.2))], LINE, 5, "wire", label="whip")
cyl(boat, block + Vector((0, 0, -1.2)), block + Vector((0, 0, -1.35)), 0.04, 0.02, 6, "metal_dark", label="hook")
stem_head = Vector((0, HALF - 0.1, sheer(HALF - 0.1) + 0.03))
tube(boat, [(0, MAST_Y + 0.05, MAST_TOP - 0.2), stem_head], LINE, 5, "wire", label="forestay")
for s in (1, -1):
    y = -6.1
    tube(boat, [(s * 0.05, MAST_Y - 0.05, MAST_TOP - 0.25), (s * (sheer_half(u_of(y)) - 0.05), y, sheer(y) + 0.02)],
         LINE, 5, "wire", label="backstay")
    y = 0.2
    tube(boat, [(s * 0.68, MAST_Y, 7.6), (s * (sheer_half(u_of(y)) - 0.05), y, sheer(y) + 0.02)],
         LINE, 5, "wire", label="shroud")

# --- winch just aft of the cabin, starboard of the middle
d = deck(-1.3)
box(boat, 0.45, 1.45, -1.5, -1.05, d - 0.02, d + 0.08, "metal_rust", label="winch base")
for x in (0.47, 1.39):
    box(boat, x, x + 0.04, -1.45, -1.1, d + 0.06, d + 0.48, "metal_rust", label="winch cheek")
cyl(boat, (0.45, -1.27, d + 0.32), (1.45, -1.27, d + 0.32), 0.03, 0.03, 8, "metal_dark", label="winch shaft")
for xa, xb in ((0.55, 0.85), (1.05, 1.35)):
    cyl(boat, (xa, -1.27, d + 0.32), (xb, -1.27, d + 0.32), 0.15, 0.15, 12, "wire", label="winch drum")
    for x in (xa, xb - 0.03):
        cyl(boat, (x, -1.27, d + 0.32), (x + 0.03, -1.27, d + 0.32), 0.22, 0.22, 12, "metal_rust", label="drum flange")
box(boat, 0.88, 1.02, -1.42, -1.12, d + 0.08, d + 0.45, "metal_rust", label="gearbox")

# --- the diver's air pump (a wooden box with a big wheel at each end) and its hose
PUMP = Vector((0.95, -2.9, deck_top(-2.9)))
d = PUMP.z
box(boat, PUMP.x - 0.23, PUMP.x + 0.23, PUMP.y - 0.22, PUMP.y + 0.22, d - 0.01, d + 0.72, "cabin_wood", label="pump box")
box(boat, PUMP.x - 0.25, PUMP.x + 0.25, PUMP.y - 0.24, PUMP.y + 0.24, d + 0.72, d + 0.77, "trim", label="pump lid")
box(boat, PUMP.x - 0.25, PUMP.x + 0.25, PUMP.y - 0.24, PUMP.y + 0.24, d - 0.01, d + 0.06, "trim", label="pump plinth")
cyl(boat, (PUMP.x, PUMP.y - 0.22, d + 0.55), (PUMP.x, PUMP.y - 0.255, d + 0.55), 0.08, 0.08, 12, "brass", label="gauge")
cyl(boat, (PUMP.x, PUMP.y - 0.25, d + 0.55), (PUMP.x, PUMP.y - 0.262, d + 0.55), 0.065, 0.065, 12, "lamp_glass",
    label="gauge face")
cyl(boat, (PUMP.x, PUMP.y + 0.05, d + 0.77), (PUMP.x, PUMP.y + 0.05, d + 0.86), 0.03, 0.025, 8, "brass", label="outlet")
WHEEL_Z = d + 0.42
cyl(boat, (PUMP.x - 0.33, PUMP.y, WHEEL_Z), (PUMP.x + 0.33, PUMP.y, WHEEL_Z), 0.025, 0.025, 8, "metal_dark",
    label="pump axle")
for s in (1, -1):
    wx = PUMP.x + s * 0.29
    torus(boat, (wx, PUMP.y, WHEEL_Z), (1, 0, 0), 0.34, 0.025, 20, 6, "metal_dark", label="pump wheel rim")
    cyl(boat, (wx - 0.03, PUMP.y, WHEEL_Z), (wx + 0.03, PUMP.y, WHEEL_Z), 0.06, 0.06, 10, "brass", label="pump hub")
    for i in range(6):
        a = math.pi / 3 * i + 0.3
        e = Vector((0, math.cos(a), math.sin(a)))
        c0 = Vector((wx, PUMP.y, WHEEL_Z))
        cyl(boat, c0 + e * 0.05, c0 + e * 0.33, 0.016, 0.014, 5, "metal_dark", label="pump spoke")
    a = 0.3
    grip = Vector((wx, PUMP.y + math.cos(a) * 0.3, WHEEL_Z + math.sin(a) * 0.3))
    cyl(boat, grip, grip + Vector((s * 0.16, 0, 0)), 0.022, 0.022, 6, "metal_dark", label="crank")
    cyl(boat, grip + Vector((s * 0.06, 0, 0)), grip + Vector((s * 0.17, 0, 0)), 0.03, 0.03, 6, "cabin_wood", label="crank grip")
dd = deck_top(-2.0)
COIL = Vector((1.45, -2.05, dd))
for i, R in enumerate((0.27, 0.24, 0.21)):
    torus(boat, COIL + Vector((0.01 * i, -0.01 * i, 0.03 + 0.05 * i)), (0, 0, 1), R, 0.028, 16, 6, "hose_rubber",
          label="hose coil")
hose = catmull([(PUMP.x, PUMP.y + 0.05, d + 0.86), (PUMP.x + 0.05, PUMP.y + 0.25, d + 0.95),
                (PUMP.x + 0.25, PUMP.y + 0.55, d + 0.45), (COIL.x - 0.15, COIL.y - 0.3, dd + 0.08),
                (COIL.x - 0.27, COIL.y, dd + 0.13)], 4)
tube(boat, hose, 0.028, 6, "hose_rubber", label="hose to coil")
HOSE_END = Vector((1.25, -3.55, deck_top(-3.55) + 0.03))
hose2 = catmull([(COIL.x + 0.21, COIL.y - 0.05, dd + 0.13), (COIL.x + 0.25, COIL.y - 0.4, dd + 0.05),
                 (1.5, -3.0, deck_top(-3.0) + 0.03), (HOSE_END.x + 0.1, HOSE_END.y + 0.2, HOSE_END.z),
                 (HOSE_END.x, HOSE_END.y, HOSE_END.z)], 4)
tube(boat, hose2, 0.028, 6, "hose_rubber", label="hose to diver")

# --- crates and baskets at the stern, a coil of rope to port
d = deck_top(-5.8)
box(boat, -1.5, -0.9, -6.2, -5.78, d - 0.005, d + 0.34, "crate_wood", (0.95, 0.95, 0.95), label="crate")
box(boat, -1.45, -0.95, -6.15, -5.8, d + 0.34, d + 0.64, "crate_wood", (0.82, 0.8, 0.76), label="crate")
box(boat, -1.5, -0.95, -5.72, -5.3, d - 0.005, d + 0.34, "crate_wood", (1.0, 0.98, 0.94), label="crate")
for cx, cy, n in ((1.15, -5.9, 3), (1.25, -5.2, 1)):
    for i in range(n):
        z0 = d - 0.005 + 0.12 * i
        cyl(boat, (cx, cy, z0), (cx, cy, z0 + 0.38), 0.21, 0.26, 12, "basket", label="basket")
        torus(boat, (cx, cy, z0 + 0.38), (0, 0, 1), 0.26, 0.02, 12, 4, "basket", label="basket rim")
d = deck_top(-2.0)
for i, R in enumerate((0.3, 0.26, 0.22)):
    torus(boat, (-1.35 + 0.01 * i, -2.0, d + 0.035 + 0.06 * i), (0, 0, 1), R, 0.035, 16, 6, "rope", label="rope coil")

# --- anchor hung on the starboard bow, its stock across the rail
AY = 5.2
ax_ = 1.5
top = sheer(AY) + 0.07
cyl(boat, (ax_, AY, 0.75), (ax_, AY, top), 0.035, 0.035, 6, "metal_rust", label="anchor shank")
cyl(boat, (1.18, AY, top - 0.03), (1.75, AY, top - 0.03), 0.025, 0.025, 6, "metal_rust", label="anchor stock")
sphere(boat, (1.75, AY, top - 0.03), 0.04, 6, 4, "metal_rust", label="stock ball")
torus(boat, (ax_, AY, top + 0.07), (1, 0, 0), 0.06, 0.015, 10, 4, "metal_rust", label="anchor ring")
for s in (1, -1):
    arm = [(ax_, AY, 0.78), (ax_, AY + s * 0.25, 0.8), (ax_, AY + s * 0.4, 0.95), (ax_, AY + s * 0.45, 1.1)]
    tube(boat, arm, 0.03, 6, "metal_rust", label="anchor arm")
    obox(boat, (ax_, AY + s * 0.43, 1.07), (0.012, 0, 0), (0, s * 0.06, -0.04), (0, 0.04, 0.08) if s > 0 else (0, -0.04, 0.08),
         "metal_rust", label="fluke")

# ---------------------------------------------------------------------------------------------- the wheel
wheel = Build("Wheel", WHEEL_HUB)
H = WHEEL_HUB
torus(wheel, H, (0, 1, 0), 0.34, 0.024, 24, 6, "cabin_wood", label="rim")
cyl(wheel, H + Vector((0, 0.05, 0)), H + Vector((0, -0.06, 0)), 0.07, 0.07, 12, "brass", label="hub")
cyl(wheel, H + Vector((0, -0.06, 0)), H + Vector((0, -0.08, 0)), 0.045, 0.04, 12, "brass", label="hub cap")
for i in range(8):
    a = math.pi / 4 * i
    e = Vector((math.cos(a), 0, math.sin(a)))
    tube(wheel, [H + e * 0.05, H + e * 0.3, H + e * 0.37, H + e * 0.42, H + e * 0.5],
         [0.018, 0.015, 0.016, 0.026, 0.02], 6, "cabin_wood", label="spoke")

# ---------------------------------------------------------------------------------------------- outriggers
OUT_LEN = 6.5
OUT_ANGLE = math.radians(65)
outriggers = []
for s, name in ((-1, "OutriggerPort"), (1, "OutriggerStarboard")):
    hinge = Vector((s * 0.42, MAST_Y, 3.5))
    o = Build(name, hinge)
    direction = Vector((s * math.cos(OUT_ANGLE), 0, math.sin(OUT_ANGLE)))
    tip = hinge + direction * OUT_LEN
    cyl(o, hinge, tip, 0.085, 0.05, 8, "mast_white", label="pole")
    box(o, hinge.x - 0.08, hinge.x + 0.08, hinge.y - 0.13, hinge.y + 0.13, hinge.z - 0.1, hinge.z + 0.1, "metal_rust",
        label="hinge")
    cyl(o, tip + Vector((0, -0.1, -0.1)), tip + Vector((0, 0.1, -0.1)), 0.09, 0.09, 10, "metal_rust", label="tip block")
    # lines: topping lift to the mast, guys forward and aft to the rail
    tube(o, [tip + Vector((-s * 0.03, 0, 0.02)), (s * 0.05, MAST_Y, MAST_TOP - 0.35)], LINE, 5, "wire", label="lift")
    for y in (4.4, -1.6):
        tube(o, [tip + Vector((0, 0, -0.05)), (s * (sheer_half(u_of(y)) - 0.05), y, sheer(y) + 0.02)], LINE, 5, "wire",
             label="guy")
    # otter door hung outboard against the hull, from a point along the pole
    hang = hinge + direction * 4.6
    DX = s * 2.42
    ring_at = Vector((DX, 1.0, 2.75))
    tube(o, [hang, ring_at], LINE * 1.3, 5, "wire", label="door line")
    torus(o, ring_at, (1, 0, 0), 0.05, 0.012, 8, 4, "metal_dark", label="door ring")
    dz0, dz1 = 1.0, 1.9
    dpts = [(0.0, dz0), (1.85, dz0), (2.0, dz0 + 0.15), (2.0, dz1 - 0.12), (1.88, dz1), (0.12, dz1), (0.0, dz1 - 0.12)]
    prism(o, dpts, (DX, 0.0, 0.0), (0, 1, 0), (0, 0, 1), 0.04, "door_wood", label="otter door")
    box(o, DX - 0.05, DX + 0.05, 0.0, 1.95, dz0 - 0.02, dz0 + 0.07, "metal_rust", label="door shoe")
    for yb in (0.45, 1.5):
        beam(o, (DX + s * 0.045, yb, dz0 + 0.07), (DX + s * 0.045, yb + (0.25 if yb < 1 else -0.25), dz1 - 0.05),
             0.08, 0.03, "metal_rust", up=(s, 0, 0), label="door brace")
        tube(o, [ring_at, (DX + s * 0.06, yb + (0.1 if yb < 1 else -0.1), dz1 - 0.05)], 0.012, 5, "metal_dark",
             label="bridle")
    # the net, hanging from the tip to drip dry: a lumpy bag with a mesh pattern in its colours
    tx, ty, tz = tip
    ctrl = [(tx, ty, tz - 0.1), (tx + s * 0.07, ty - 0.03, tz - 0.5), (tx + s * 0.15, ty - 0.09, tz - 1.3),
            (tx + s * 0.21, ty - 0.15, tz - 2.2), (tx + s * 0.23, ty - 0.21, tz - 3.2), (tx + s * 0.21, ty - 0.23, tz - 4.2),
            (tx + s * 0.17, ty - 0.19, tz - 5.1), (tx + s * 0.13, ty - 0.11, tz - 5.9), (tx + s * 0.09, ty - 0.01, tz - 6.5),
            (tx + s * 0.07, ty + 0.07, tz - 6.95), (tx + s * 0.06, ty + 0.11, tz - 7.2)]
    path = catmull(ctrl, 4)
    m = len(path)
    lumps_k = [0.85 + 0.3 * RNG.random() for _ in range(m)]
    lumps_j = [0.9 + 0.2 * RNG.random() for _ in range(16)]
    radii = []
    for k in range(m):
        t = k / (m - 1)
        r = (0.06 + 0.36 * t ** 0.7) * (1 - 0.85 * smoothstep(0.88, 1.0, t))
        radii.append(r * (1.0 if k == 0 else lumps_k[k]))

    def jit(k, j):
        return 1.0 if k in (0, m - 1) else lumps_j[j] * (1 + 0.08 * math.sin(k * 1.7 + j * 2.3))

    def mesh_col(k, j):
        return (0.55, 0.6, 0.55) if (k + j) % 2 else WHITE

    tube(o, path, radii, 16, "net_green", cols=mesh_col, jitter=jit, label="net")
    # head rope with floats, and a dark lead line, winding round the bag
    P, F = frames(path)

    def on_bag(t, turn, phase, out):
        k = min(int(t * (m - 1)), m - 2)
        f = t * (m - 1) - k
        p = P[k].lerp(P[k + 1], f)
        n, b2, _ = F[k]
        r = radii[k] + (radii[k + 1] - radii[k]) * f
        a = 2 * math.pi * turn * t + phase
        return p + (n * math.cos(a) + b2 * math.sin(a)) * (r * 1.02 + out)

    for phase, matn, rad in ((0.0, "rope", 0.02), (math.pi, "metal_dark", 0.022)):
        pts = [on_bag(0.06 + 0.86 * i / 40, 1.4, phase, rad) for i in range(41)]
        tube(o, pts, rad, 5, matn, label="net rope")
    for t in (0.25, 0.38, 0.5, 0.62, 0.74, 0.86):
        sphere(o, on_bag(t, 1.4, 0.0, 0.08), 0.075, 8, 5, "float_orange", label="float", squash=(1, 1, 0.8))
    tk = int(0.93 * (m - 1))
    n, b2, tt = F[tk]
    torus(o, P[tk], tt, radii[tk] * 0.9, 0.025, 12, 4, "rope", label="cod end tie")
    outriggers.append(o)

# ---------------------------------------------------------------------------------------------- check and write
total = 0
wrong_all = 0
for b in [boat, wheel] + outriggers:
    wrong, counted, bad = b.inside_out()
    print("INSIDE-OUT %s: %d of %d triangles face inwards, %d parts" % (b.name, wrong, counted, len(b.parts)))
    for label, n, of, where in bad:
        print("   bad part %s: %d of %d, at %s" % (label, n, of, where))
    wrong_all += wrong
    print("TRIANGLES %s: %d" % (b.name, len(b.tris)))
    total += len(b.tris)
print("TRIANGLES total: %d" % total)
print("INSIDE-OUT %s" % ("PASSED" if wrong_all == 0 else "FAILED (%d)" % wrong_all))

objects = [b.make() for b in [boat, wheel] + outriggers]


def marker(name, at, turn_deg=0.0):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = "ARROWS"
    e.empty_display_size = 0.4
    e.location = at
    e.rotation_euler = (0.0, 0.0, math.radians(turn_deg))
    bpy.context.scene.collection.objects.link(e)
    print("MARKER %s: blender (%.3f, %.3f, %.3f), godot (%.3f, %.3f, %.3f), turned %d deg"
          % (name, at[0], at[1], at[2], at[0], at[2], -at[1], turn_deg))


# Godot's -Z (Blender +Y, the bow) is the way an unturned marker faces; 180 turns it to face aft.
CONSOLE = (0.0, CB_Y1, deck_top(CB_Y1))
marker("ConsoleSpot", CONSOLE, 180)
marker("BoySpot", (0.0, CB_Y1 - 0.9, deck_top(CB_Y1 - 0.9)), 0)
marker("CaptainSpot", (-0.95, -3.4, deck_top(-3.4)), 180)
marker("DiverSpot", (0.95, -3.8, deck_top(-3.8)), 180)
marker("HelmetCable", (0.0, CB_Y1, deck_top(CB_Y1) + 1.5), 180)
marker("Waterline", (0.0, 0.0, 0.0), 0)
print("HOSE END (not a marker): blender (%.3f, %.3f, %.3f)" % tuple(HOSE_END))

lo = Vector((1e9, 1e9, 1e9))
hi = Vector((-1e9, -1e9, -1e9))
for b in [boat, wheel] + outriggers:
    for v in b.verts:
        lo = Vector(map(min, lo, v))
        hi = Vector(map(max, hi, v))
print("BOUNDS blender: x %.2f..%.2f, y %.2f..%.2f, z %.2f..%.2f" % (lo.x, hi.x, lo.y, hi.y, lo.z, hi.z))

os.makedirs(os.path.dirname(BLEND), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
bpy.ops.object.select_all(action="DESELECT")
kw = dict(filepath=GLB, export_format="GLB", export_apply=True, export_yup=True, export_cameras=False,
          export_lights=False)
try:
    bpy.ops.export_scene.gltf(**kw, export_vertex_color="ACTIVE")
except TypeError:
    bpy.ops.export_scene.gltf(**kw, export_colors=True)
print("WROTE", GLB)
