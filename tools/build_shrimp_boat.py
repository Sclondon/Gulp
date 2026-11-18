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
  PumpWheel            the diver's air pump's crank wheel, origin at its hub, turns about local X (athwartships)
  OutriggerPort        the port outrigger with its net, floats, door and lines, origin at its hinge on the mast
  OutriggerStarboard   the same on the starboard side; both turn about local Y (Godot Z) to raise or lower
  ConsoleSpot, BoySpot, CaptainSpot, DiverSpot, HelmetCable, MonitorSpot, BowWave, Wake, Waterline   empties:
  marker points. Each spot is a floor point; its -Z in Godot is the way that figure or thing faces.

The title camera stands abeam off the starboard side (the user, 2026-11-18: "The boat should be perpendicular in the
start scene, and the pc against the portside wall", "And hooked up to a monitor"), so the cabin is walled to port and
open to starboard and aft, and nothing on the starboard side hangs between that camera and the cabin or the people.
tools/SHRIMP_BOAT.md holds the design sheet this follows.

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
    ("hull_white", (0.74, 0.73, 0.69)),
    ("hull_stripe", (0.23, 0.35, 0.35)),
    ("bottom_red", (0.38, 0.17, 0.12)),
    ("deck_wood", (0.50, 0.42, 0.32)),
    ("cabin_wood", (0.55, 0.38, 0.22)),
    ("trim", (0.34, 0.22, 0.13)),
    ("roof", (0.62, 0.62, 0.59)),
    ("glass", (0.55, 0.62, 0.66)),    # thin panes, lightly tinted: the captain shows through them
    ("net_green", (0.13, 0.20, 0.15)),
    ("rust", (0.46, 0.22, 0.10)),
    ("name_board", (0.88, 0.86, 0.78)),
    ("primer_red", (0.47, 0.24, 0.17)),
    ("lamp_green", (0.20, 0.75, 0.35)),
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
    ("spar_wood", (0.44, 0.39, 0.33)),
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
    # low aft, so that the deck's people show over it from abeam; the sheer sweeps up to the bow
    return 0.45 + 0.32 * max(0.0, (y - 2.0) / 4.5) ** 2


def sheer(y):
    return deck(y) + bulwark_h(y)


def sheer_half(u):
    if u < 0.45:
        return 2.1 - 0.25 * ((0.45 - u) / 0.45) ** 2
    t = (u - 0.45) / 0.55
    return 2.1 * math.sqrt(max(0.0, 1 - t ** 2.6))


def water_half(u):
    return sheer_half(u) * (0.92 - 0.36 * smoothstep(0.55, 1.0, u))


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
        self.ends = {}    # part index -> (first point, last point) of a line (an open tube)
        self.smooth_deg = 38   # edges sharper than this stay hard; the outriggers (nets) are smoothed more

    def part(self, label, verts, polys, mats, cols=None, convex=False, ends=None):
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
        if ends is not None:
            self.ends[len(self.parts) - 1] = (Vector(ends[0]), Vector(ends[1]))

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
                for wa, wb, wc in ((1 / 3, 1 / 3, 1 / 3), (0.45, 0.33, 0.22), (0.2, 0.3, 0.5)):
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
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(self.smooth_deg))
        return obj


# ---------------------------------------------------------------------------------------------- primitives
def box_corners(c):
    """Eight corners: bottom four round, then top four round. Returns (verts, polys)."""
    polys = [[0, 1, 2, 3], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
    return c, polys


FOOT_GRIME = (0.84, 0.81, 0.74)

RUST_TINT = (0.52, 0.31, 0.19)   # times hull_white: a rust brown


def weep(t):
    """Rust weeping down white paint: strong at the top, fading into the white (t: 0 top, 1 bottom)."""
    k = (1 - t) ** 0.8
    # fades to a pale rust, never to white: a run is its own slab with its own shading, so a foot faded to the
    # hull's white showed as a pale stripe (concept pass 3)
    base = (0.8, 0.68, 0.58)
    return tuple(b + (c - b) * k for b, c in zip(base, RUST_TINT))




def box(b, x0, x1, y0, y1, z0, z1, mat, col=None, label="box", grime=False):
    """grime: the bottom corners darker (dirt and wet at the foot of a painted wall)."""
    c = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
         (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    v, p = box_corners(c)
    if grime:
        top = col if col is not None else WHITE
        col = [FOOT_GRIME] * 4 + [top] * 4
    b.part(label, v, p, mat, col, convex=True)


def hull_patch(b, s, ys, zlo, zhi, mat, label="patch", nz=3, width=None, out=0.006, cols=None):
    """A thin closed slab lying on the hull's outside (side s: +1 starboard, -1 port), over the y values ys,
    between heights zlo(y) and zhi(y). width(t) (t 0 at the top, 1 at the bottom), if given, makes it a
    streak instead: centred on the middle of ys, that wide at each height. Only where the hull is not raked
    (aft of y 1.5, or above the deck)."""
    rows = []
    for i, y in enumerate(ys):
        rows.append(y)
    grid_f = []
    grid_b = []
    yc = (ys[0] + ys[-1]) / 2
    for i, y in enumerate(rows):
        cf = []
        cb = []
        for j in range(nz + 1):
            t = j / nz
            yy = y
            if width is not None:
                f = i / (len(rows) - 1) - 0.5
                yy = yc + f * width(t)
            z = zhi(yy) + (zlo(yy) - zhi(yy)) * t
            u = u_of(yy)
            sh = sheer(yy)
            x = outer_half(u, min(z, sh - 0.005), sh) + lap_extra(yy, z)
            cf.append((s * (x + out), yy, z))
            cb.append((s * (x - 0.012 - out), yy, z))   # (each slab its own back plane: no coincident faces)
        grid_f.append(cf)
        grid_b.append(cb)
    ni = len(rows)
    nj = nz + 1
    verts = [p for row in grid_f for p in row] + [p for row in grid_b for p in row]
    if callable(cols):
        cols = [cols(j / nz) for _ in range(2 * ni) for j in range(nj)]
    F = lambda i, j: i * nj + j
    B = lambda i, j: ni * nj + i * nj + j
    polys = []
    for i in range(ni - 1):
        for j in range(nj - 1):
            # j runs downwards (t), so (y, -z) orders these the other way round from (y, z)
            polys.append([F(i, j), F(i, j + 1), F(i + 1, j + 1), F(i + 1, j)])
            polys.append([B(i, j), B(i + 1, j), B(i + 1, j + 1), B(i, j + 1)])
    for i in range(ni - 1):
        polys.append([F(i, 0), F(i + 1, 0), B(i + 1, 0), B(i, 0)])
        polys.append([B(i, nj - 1), B(i + 1, nj - 1), F(i + 1, nj - 1), F(i, nj - 1)])
    for j in range(nj - 1):
        polys.append([F(0, j), B(0, j), B(0, j + 1), F(0, j + 1)])
        polys.append([F(ni - 1, j), F(ni - 1, j + 1), B(ni - 1, j + 1), B(ni - 1, j)])
    b.part(label, verts, polys, mat, cols)


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
    b.part(label, verts, polys, pm, cols, ends=None if closed else (P[0], P[-1]))


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
        bsdf.inputs["Alpha"].default_value = 0.22
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
# the topsides are lapped strakes (clinker): each plank's lower edge stands LAP proud of the one below it, so a line
# of shadow runs under every seam. One strake low on the side is the second teal band.
W_, T_, R_ = "hull_white", "hull_stripe", "bottom_red"
SEG_STAR = ["deck_wood", W_, "trim", T_,
            W_, W_, W_, W_, W_, W_, W_, T_, T_, W_, W_, W_,
            R_, R_, R_, R_, R_, R_, R_]
GRIME = (0.86, 0.83, 0.76)
LAP = 0.03
BOOT = 0.35        # the top of the bottom paint


def strake_profile(y):
    """(height, how far proud of the smooth hull) down the topsides, from the bottom of the sheer band (zA) to the
    boot top (0.25): seams s3 (in the bulwark), s1 and s2 (between the deck and the boot top), each a pair of
    points (the upper strake's proud lower edge, then the lower strake tucked in under it). The deck's height d is
    kept as a point too (the stem's rake hinges there)."""
    u = u_of(y)
    d = deck(y)
    zA = sheer(y) - 0.26
    lap = LAP * min(1.0, sheer_half(u) / 0.3)
    s3 = d + (zA - d) * 0.5
    out = [(zA, 0.0), (s3, lap), (s3 - 0.008, 0.0), (d, 0.0)]
    for f in (0.8, 0.6, 0.4, 0.2):
        z = BOOT + (d - BOOT) * f
        out += [(z, lap), (z - 0.008, 0.0)]
    return out + [(BOOT, 0.0)]


def lap_extra(y, z):
    prof = strake_profile(y)
    if z >= prof[0][0] or z <= prof[-1][0]:
        return 0.0
    for (za, ea), (zb, eb) in zip(prof, prof[1:]):
        if zb <= z <= za:
            return ea + (eb - ea) * (za - z) / max(za - zb, 1e-6)
    return 0.0


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
    SEAM = (0.68, 0.66, 0.62)     # a little grime in the shadow under each lap
    prof = strake_profile(y)
    zs = [(z, e) for z, e in prof] + [(0.0, 0.0)] + [(k * f, 0.0) for f in (0.3, 0.55, 0.75, 0.9)]
    zc = [WHITE, WHITE, SEAM, (0.95, 0.94, 0.91), WHITE, SEAM, WHITE, SEAM, WHITE, SEAM, WHITE, SEAM, GRIME,
          (0.9, 0.86, 0.82), WHITE, WHITE, WHITE, WHITE]
    for (z, e), c in zip(zs, zc):
        S.append((outer_half(u, z, sh) + e, yy(z), z))
        C.append(c)
    S.append((0.07 * min(1.0, bs / 0.3), yy(k), k))
    C.append(WHITE)
    ring = [(0.0, y, d)] + S + [(0.0, yy(k), k)] + [(-x, yv, z) for x, yv, z in reversed(S)]
    # faded, uneven paint: each station a shade lighter or darker above the water
    m = 0.95 + 0.06 * RNG.random()
    C = [C[0]] + [(c[0] * m, c[1] * m, c[2] * m * 0.99) for c in C[1:16]] + C[16:]
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
    # the lower teal band ends in a rubbing strake along its proud lower edge
    pts = []
    for u in STATIONS:
        if u > 0.955:
            break
        ring, _ = station(u)
        x, y, z = ring[12]
        pts.append((s * (x + 0.012), y, z + 0.01))
    tube(boat, pts, 0.03, 6, "hull_stripe", label="lower rubbing strake")
last, _ = station(1.0)
prev, _ = station(0.985)
stem = [last[3]] + [last[i] for i in range(4, 23)]
stem = [(0.0, y + 0.02, z) for _, y, z in stem]
stem = [(0.0, stem[0][1] + 0.05, stem[0][2] + 0.38)] + stem   # the stem head stands up above the rail
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
PROP = Vector((0, -5.55, -0.7))
cyl(boat, (0, -5.7, PROP.z), (0, -5.22, PROP.z), 0.07, 0.07, 8, "brass", label="prop hub")
for i in range(4):
    a = math.pi / 2 * i + math.pi / 4     # no blade straight up: they clear the hull's bottom
    radial = Vector((math.cos(a), 0, math.sin(a)))
    tang = Vector((0, 1, 0)).cross(radial)
    tw = Matrix.Rotation(math.radians(35), 3, radial)
    obox(boat, PROP + radial * 0.15, radial * 0.095, tw @ (tang * 0.07), tw @ Vector((0, 0.012, 0)),
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
        c += 0.9
    cuts.append(yb)
    x0 = xc - PW / 2 + GAP / 2
    x1 = xc + PW / 2 - GAP / 2
    for y0, y1 in zip(cuts, cuts[1:]):
        y1 = y1 - 0.008
        if y1 - y0 < 0.1:
            continue
        v = 0.8 + 0.2 * RNG.random()
        roll = RNG.random()
        if roll < 0.12:
            v *= 0.82                                   # oil and fish stains
        if roll > 0.95:
            col = (1.0, 0.93, 0.80)                     # a plank put in new, not yet weathered
        else:
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
WH_TOP = 3.27      # the wheelhouse stands a step higher than the cabin behind it
WH_ROOF = 3.25     # underside of its roof
RT = WH_ROOF + 0.1  # top of its roof
# Windows right round at standing height: framed and glazed (thin, lightly tinted panes) with sills, lintels and
# jambs outside, the wall between panes for mullions. To starboard (the title camera's side) a door in the aft half
# stands open, folded forward flat against the house side and hooked there; the wall behind it has a window under
# the door's own window, so the camera abeam sees the captain through the doorway and through both panes.
WZ0, WZ1 = deck(2.75) + 1.02, deck(2.75) + 1.85     # sill and head of the side windows
win_front = [(-1.05, -0.45, WZ0 + 0.1, WZ1), (-0.32, 0.32, WZ0 + 0.1, WZ1), (0.45, 1.05, WZ0 + 0.1, WZ1)]
win_port = [(1.8, 2.35, WZ0, WZ1), (2.45, 3.05, WZ0, WZ1), (3.15, 3.72, WZ0, WZ1)]
DOOR = (1.78, 2.48)                 # the doorway, along y
DOOR_TOP = 2.92
DOOR_W = DOOR[1] - DOOR[0]
SILL_TOP = deck(2.1) + 0.15         # the raised sill you step over
DOOR_WIN = (0.12, DOOR_W - 0.12, WZ0 + 0.05, WZ1 - 0.05)   # the door's window, across its width from the hinge
win_star = [(DOOR[1] + DOOR_WIN[0] - 0.02, DOOR[1] + DOOR_WIN[1] + 0.02, WZ0, WZ1),
            (3.24, 3.48, WZ0, WZ1), (3.55, 3.76, WZ0, WZ1)]
wall(boat, "y", WH_Y1 - WT, WH_Y1, -WH_X, WH_X, WH_Z0, WH_TOP, win_front, "hull_white", "wall wheelhouse front")
wall(boat, "y", WH_Y0, WH_Y0 + WT, -WH_X, WH_X, WH_Z0, WH_TOP, [], "hull_white", "wall wheelhouse back")
wall(boat, "x", -WH_X, -WH_X + WT, WH_Y0 + WT, WH_Y1 - WT, WH_Z0, WH_TOP, win_port, "hull_white", "wall wheelhouse port")
wall(boat, "x", WH_X - WT, WH_X, WH_Y0 + WT, WH_Y1 - WT, WH_Z0, WH_TOP,
     win_star + [(DOOR[0], DOOR[1], WH_Z0, DOOR_TOP)], "hull_white", "wall wheelhouse starboard")
# a grimy foot round the house where the deck water runs (not across the doorway)
for s in (1, -1):
    xa, xb = sorted((s * (WH_X + 0.005), s * (WH_X - 0.02)))
    spans = [(WH_Y0, DOOR[0]), (DOOR[1], WH_Y1)] if s > 0 else [(WH_Y0, WH_Y1)]
    for ya, yb in spans:
        box(boat, xa, xb, ya, yb, WH_Z0, deck(WH_Y1) + 0.22, "hull_white", (0.9, 0.88, 0.82), label="house foot",
            grime=True)
PANE = 0.003    # half the glass's thickness


def window_frame(side_x, out, a0, a1, z0, z1, along_y=True, lintel=True):
    """Sill, lintel and jambs round one opening, on the outside face of a wall (side_x: the face's coordinate,
    out: +1 or -1, the way out of the wall). along_y: the wall runs along y (a side wall), else along x."""
    def bx(u0, u1, v0, v1, w0, w1, label):
        if along_y:
            xa, xb = sorted((side_x + out * u0, side_x + out * u1))
            box(boat, xa, xb, v0, v1, w0, w1, "trim", label=label)
        else:
            ya, yb = sorted((side_x + out * u0, side_x + out * u1))
            box(boat, v0, v1, ya, yb, w0, w1, "trim", label=label)
    bx(-0.02, 0.05, a0 - 0.05, a1 + 0.05, z0 - 0.05, z0, "sill")
    if lintel:
        bx(0.0, 0.035, a0 - 0.05, a1 + 0.05, z1, z1 + 0.045, "lintel")
    bx(0.0, 0.03, a0 - 0.04, a0, z0, z1, "jamb")
    bx(0.0, 0.03, a1, a1 + 0.04, z0, z1, "jamb")


for a0, a1, z0, z1 in win_front:
    box(boat, a0 - 0.01, a1 + 0.01, WH_Y1 - WT / 2 - PANE, WH_Y1 - WT / 2 + PANE, z0 - 0.01, z1 + 0.01, "glass", label="glass")
    window_frame(WH_Y1, 1, a0, a1, z0, z1, along_y=False, lintel=False)
for a0, a1, z0, z1 in win_port:
    box(boat, -WH_X + WT / 2 - PANE, -WH_X + WT / 2 + PANE, a0 - 0.01, a1 + 0.01, z0 - 0.01, z1 + 0.01, "glass", label="glass")
    window_frame(-WH_X, -1, a0, a1, z0, z1)
for i, (a0, a1, z0, z1) in enumerate(win_star):
    box(boat, WH_X - WT / 2 - PANE, WH_X - WT / 2 + PANE, a0 - 0.01, a1 + 0.01, z0 - 0.01, z1 + 0.01, "glass", label="glass")
    if i > 0:      # the first is under the folded door, which is its frame
        window_frame(WH_X, 1, a0, a1, z0, z1)
# the doorway: a raised sill to step over, jambs and a lintel
box(boat, WH_X - WT - 0.03, WH_X + 0.05, DOOR[0], DOOR[1], WH_Z0, SILL_TOP, "trim", label="door sill")
box(boat, WH_X, WH_X + 0.03, DOOR[0] - 0.04, DOOR[0], SILL_TOP, DOOR_TOP, "trim", label="door jamb")
box(boat, WH_X, WH_X + 0.03, DOOR[1], DOOR[1] + 0.03, SILL_TOP, DOOR_TOP, "trim", label="door jamb")
box(boat, WH_X, WH_X + 0.035, DOOR[0] - 0.04, DOOR[1] + 0.03, DOOR_TOP, DOOR_TOP + 0.05, "trim", label="door lintel")
# the door, open: folded forward through 180 degrees about its hinges on the forward jamb, lying flat against the
# house side (x from DX0 to DX1), hooked to an eye on the wall at its free edge
DX0, DX1 = WH_X + 0.035, WH_X + 0.075
DY0, DY1 = DOOR[1] + 0.005, DOOR[1] + DOOR_W - 0.005
DZ0, DZ1 = SILL_TOP + 0.01, DOOR_TOP - 0.015
dwin = (DY0 + DOOR_WIN[0], DY0 + DOOR_WIN[1], DOOR_WIN[2], DOOR_WIN[3])
wall(boat, "x", DX0, DX1, DY0, DY1, DZ0, DZ1, [dwin], "cabin_wood", "door")
box(boat, (DX0 + DX1) / 2 - PANE, (DX0 + DX1) / 2 + PANE, dwin[0] - 0.01, dwin[1] + 0.01, dwin[2] - 0.01, dwin[3] + 0.01,
    "glass", label="door glass")
for z in (DZ0 + 0.25, DZ1 - 0.25):
    box(boat, WH_X + 0.03, DX1 + 0.006, DOOR[1] - 0.005, DOOR[1] + 0.07, z, z + 0.1, "metal_dark", label="door hinge")
# the handle on the door's face (outward now), and the hook to an eye on the wall forward of it
box(boat, DX1, DX1 + 0.03, DY1 - 0.1, DY1 - 0.07, 1.9, 1.98, "brass", label="handle boss")
box(boat, DX1 + 0.03, DX1 + 0.05, DY1 - 0.2, DY1 - 0.07, 1.92, 1.96, "brass", label="handle")
box(boat, WH_X, WH_X + 0.04, DY1 + 0.04, DY1 + 0.08, 1.3, 1.34, "metal_dark", label="hook eye")
cyl(boat, (DX1 - 0.01, DY1 - 0.02, 1.32), (WH_X + 0.03, DY1 + 0.06, 1.32), 0.008, 0.008, 4, "metal_dark", label="door hook")
for x in (-WH_X, WH_X):
    for y in (WH_Y0, WH_Y1):
        box(boat, x - 0.05, x + 0.05, y - 0.05, y + 0.05, WH_Z0, WH_TOP, "trim", label="corner post")
box(boat, -WH_X - 0.15, WH_X + 0.15, WH_Y0 - 0.1, WH_Y1 + 0.25, WH_ROOF, RT, "roof", label="wheelhouse roof")
box(boat, -WH_X - 0.16, WH_X + 0.16, WH_Y1 + 0.2, WH_Y1 + 0.27, WH_ROOF - 0.07, RT + 0.01, "hull_stripe", label="roof fascia front")
for s in (1, -1):
    xa, xb = sorted((s * (WH_X + 0.15), s * (WH_X + 0.21)))
    box(boat, xa, xb, WH_Y0 - 0.1, WH_Y1 + 0.27, WH_ROOF - 0.07, RT + 0.01, "hull_stripe", label="roof fascia side")
# a brow over the front windows
beam(boat, (0, WH_Y1 + 0.02, 2.98), (0, WH_Y1 + 0.3, 2.9), 2.6, 0.04, "trim", label="brow")
box(boat, -WH_X, WH_X, WH_Y1, WH_Y1 + 0.06, 2.92, 2.98, "trim", label="brow back")
# running lights on boards at the house's front corners: green to starboard, red to port
for s, lamp in ((1, "lamp_green"), (-1, "life_red")):
    xa, xb = sorted((s * (WH_X + 0.0), s * (WH_X + 0.05)))
    box(boat, xa, xb, WH_Y1 - 0.42, WH_Y1 - 0.04, 2.95, 3.15, "trim", label="light board")
    xa, xb = sorted((s * (WH_X + 0.05), s * (WH_X + 0.13)))
    box(boat, xa, xb, WH_Y1 - 0.2, WH_Y1 - 0.08, 3.0, 3.1, lamp, label="running light")
# the wheel's pedestal and a shelf of instruments under the front windows
CAPTAIN = Vector((0.0, 2.75, deck_top(2.75)))   # where the helmsman stands, facing the bow
WHEEL_HUB = Vector((0.0, CAPTAIN.y + 0.45, CAPTAIN.z + 1.05))
box(boat, -0.12, 0.12, WHEEL_HUB.y + 0.08, WHEEL_HUB.y + 0.28, deck(3.4) - 0.02, WHEEL_HUB.z + 0.12, "cabin_wood",
    label="pedestal")
cyl(boat, (0, WHEEL_HUB.y + 0.08, WHEEL_HUB.z), (0, WHEEL_HUB.y - 0.02, WHEEL_HUB.z), 0.03, 0.03, 8, "brass",
    label="axle")
box(boat, -1.25, 1.25, WH_Y1 - 0.45, WH_Y1 - WT, 1.78, 1.86, "cabin_wood", label="chart shelf")
box(boat, -1.25, 1.25, WH_Y1 - 0.4, WH_Y1 - WT, deck(3.6) - 0.02, 1.78, "cabin_wood", label="shelf front")
# roof gear: searchlight, horn, exhaust stack
cyl(boat, (0.55, 3.75, RT), (0.55, 3.75, RT + 0.21), 0.045, 0.045, 8, "metal_dark", label="light post")
cyl(boat, (0.55, 3.58, RT + 0.3), (0.55, 3.9, RT + 0.3), 0.13, 0.12, 12, "metal_dark", label="searchlight")
cyl(boat, (0.55, 3.9, RT + 0.3), (0.55, 3.925, RT + 0.3), 0.105, 0.105, 12, "lamp_glass", label="searchlight lens")
cyl(boat, (-0.45, 3.55, RT), (-0.45, 3.55, RT + 0.17), 0.03, 0.03, 6, "metal_dark", label="horn post")
cyl(boat, (-0.45, 3.45, RT + 0.21), (-0.45, 3.85, RT + 0.21), 0.025, 0.09, 10, "brass", label="horn")
# the exhaust stack: black, standing up through the cabin roof's forward port corner, its top cut at a slant and
# turned aft; a rusty collar where it meets the roof
SX, SY = -0.95, 1.3
cyl(boat, (SX, SY, 3.08), (SX, SY, 4.45), 0.1, 0.095, 10, "metal_dark", label="stack")
tube(boat, [(SX, SY, 4.4), (SX, SY, 4.55), (SX, SY - 0.06, 4.66), (SX, SY - 0.18, 4.74)], 0.095, 10, "metal_dark",
     label="stack bend")
cyl(boat, (SX, SY, 3.12), (SX, SY, 3.26), 0.15, 0.13, 10, "metal_rust", label="stack collar")
cyl(boat, (SX, SY, 3.95), (SX, SY, 4.0), 0.11, 0.11, 10, "metal_rust", label="stack band")
# rust weeping down the house's starboard face from the corners of its opening and from under the roof
def wall_weep(y, ztop, length, wide):
    cs = [weep(1.0)] * 4 + [weep(0.0)] * 4
    v, pp = box_corners([(WH_X, y - wide * 0.3, ztop - length), (WH_X + 0.004, y - wide * 0.3, ztop - length),
                         (WH_X + 0.004, y + wide * 0.3, ztop - length), (WH_X, y + wide * 0.3, ztop - length),
                         (WH_X, y - wide / 2, ztop), (WH_X + 0.004, y - wide / 2, ztop),
                         (WH_X + 0.004, y + wide / 2, ztop), (WH_X, y + wide / 2, ztop)])
    boat.part("house rust", v, pp, "hull_white", cs, convex=True)


for y, zt, ln, wd in ((win_star[1][0] + 0.06, WZ0 - 0.05, 0.3, 0.06), (win_star[2][1] - 0.05, WZ0 - 0.05, 0.24, 0.05),
                      (2.3, WH_TOP - 0.03, 0.2, 0.1), (3.4, WH_TOP - 0.03, 0.16, 0.07)):
    wall_weep(y, zt, ln, wd)
# a whip aerial on the roof's starboard aft corner
cyl(boat, (1.2, 1.75, RT), (1.2, 1.75, RT + 0.12), 0.04, 0.04, 6, "metal_dark", label="aerial base")
cyl(boat, (1.2, 1.75, RT + 0.1), (1.2, 1.75, 5.9), 0.012, 0.006, 4, "metal_dark", label="aerial")

# --- the open cabin behind the wheelhouse: a full wall to PORT (the console stands against it inside), open to
# starboard and aft from deck to roof (posts at the corners only), roofed lower than the wheelhouse
CB_X = 1.45
CB_Y0, CB_Y1 = -1.25, WH_Y0
CB_Z0 = deck(CB_Y0) - 0.06
CB_ROOF = 3.06     # the cabin roof's underside: 2.15 m above the cabin floor at its aft end
LINE_T = 0.018     # the dark board lining inside the port wall; its face is the wall's inside face (x = -CB_X + WT)
box(boat, -CB_X, -CB_X + WT - LINE_T, CB_Y0, CB_Y1, CB_Z0, CB_ROOF + 0.02, "hull_white", label="cabin port wall",
    grime=True)
# the wall's inside: upright dark boards, each its own shade, under the console, monitor and pipes
nb = 19
for i in range(nb):
    y0 = CB_Y0 + (CB_Y1 - CB_Y0) * i / nb
    y1 = CB_Y0 + (CB_Y1 - CB_Y0) * (i + 1) / nb - 0.006
    v = 0.75 + 0.3 * RNG.random()
    box(boat, -CB_X + WT - LINE_T, -CB_X + WT, y0, y1, CB_Z0 + 0.05, CB_ROOF, "door_wood", (v, v * 0.97, v * 0.92),
        label="wall board")
# pipes running up the wall to the roof, clear of the console's length (y -0.98..1.33 from the main session's size)
PIPE_X = -CB_X + WT + 0.07
for py, pr in ((-1.04, 0.04), (1.46, 0.04)):
    tube(boat, [(PIPE_X, py, deck(py) + 0.03), (PIPE_X, py, CB_ROOF - 0.14), (PIPE_X, py + (0.1 if py < 0 else -0.1),
         CB_ROOF - 0.07), (PIPE_X, py + (0.35 if py < 0 else -0.35), CB_ROOF - 0.06)], pr, 8, "metal_rust",
         label="wall pipe")
    for z in (deck(py) + 0.6, CB_ROOF - 0.5):
        box(boat, -CB_X + WT, PIPE_X + 0.01, py - 0.03, py + 0.03, z, z + 0.04, "metal_dark", label="pipe clip")
tube(boat, [(PIPE_X, -0.69, CB_ROOF - 0.06), (PIPE_X, 1.11, CB_ROOF - 0.06)], 0.03, 8, "metal_rust", label="roof pipe")
box(boat, -CB_X - 0.03, -CB_X + WT + 0.01, CB_Y0, CB_Y1, CB_Z0, deck(CB_Y0) + 0.1, "trim", label="port wall foot")
for y in (CB_Y0,):   # forward, the wheelhouse corner post holds the roof
    box(boat, CB_X - 0.11, CB_X + 0.01, y, y + 0.12, CB_Z0, CB_ROOF + 0.02, "trim", label="cabin starboard post")
box(boat, -CB_X - 0.01, -CB_X + 0.11, CB_Y0, CB_Y0 + 0.12, CB_Z0, CB_ROOF + 0.02, "trim", label="cabin port post")
box(boat, -CB_X - 0.13, CB_X + 0.13, CB_Y0 - 0.15, CB_Y1 + 0.05, CB_ROOF, CB_ROOF + 0.08, "roof", label="cabin roof")
box(boat, -CB_X - 0.14, CB_X + 0.14, CB_Y0 - 0.17, CB_Y0 - 0.1, CB_ROOF - 0.06, CB_ROOF + 0.09, "hull_stripe",
    label="cabin roof fascia")
for s in (1, -1):
    xa, xb = sorted((s * (CB_X + 0.13), s * (CB_X + 0.19)))
    box(boat, xa, xb, CB_Y0 - 0.17, CB_Y1 + 0.05, CB_ROOF - 0.04, CB_ROOF + 0.09, "hull_stripe", label="cabin roof side fascia")
# a low grab rail round the cabin roof's edge
for s in (1, -1):
    x = s * (CB_X + 0.05)
    tube(boat, [(x, CB_Y0 - 0.05, CB_ROOF + 0.08), (x, CB_Y0 - 0.05, CB_ROOF + 0.3), (x, CB_Y1 - 0.15, CB_ROOF + 0.3),
                (x, CB_Y1 - 0.15, CB_ROOF + 0.08)], 0.022, 5, "metal_dark", label="roof rail")
# the life ring, hung outside the starboard bulwark forward of the house
LR_Y = 3.35
LR_Z = sheer(LR_Y) - 0.64      # hung below the rub rail
LR_X = outer_half(u_of(LR_Y), LR_Z + 0.3, sheer(LR_Y)) + LAP + 0.1
LR_AX = Vector((1, 0, 0.25)).normalized()
LR_TOP = Vector((LR_X, LR_Y, LR_Z)) + (Vector((0, 0, 1)) - LR_AX * LR_AX.z).normalized() * (0.25 + 0.05)
torus(boat, (LR_X, LR_Y, LR_Z), (1, 0, 0.25), 0.25, 0.055, 16, 7,
      lambda k, j: "life_red" if (k // 2) % 2 == 0 else "hull_white", label="life ring")
tube(boat, [LR_TOP, (sheer_half(u_of(LR_Y)) + 0.13, LR_Y, sheer(LR_Y) - 0.2),
            (sheer_half(u_of(LR_Y)) - 0.03, LR_Y, sheer(LR_Y) + 0.03)], 0.012, 5, "rope",
     label="ring lanyard")

# --- the rig: one mast, stepped on deck just abaft the house (the open cabin), as on a Gulf double-rigger. It is
# stayed by a forestay to the stem head, shrouds over a crosstree to the rails (with turnbuckles) and two
# backstays to the quarters. It carries: the two outriggers, pivoting on pins in a collar above the cabin roof and
# held up by topping lifts from a crane at the masthead; the heel blocks the trawl cables lead through from the
# winch; and the cargo boom, swung aft over the working deck, for lifting the cod end. Every line ends on a fitting.
MAST_Y = -1.62
MAST_TOP = 9.5
MAST_R0, MAST_R1 = 0.13, 0.075
LINE = 0.014


def mast_r(z):
    return MAST_R0 + (MAST_R1 - MAST_R0) * (z - deck(MAST_Y)) / (MAST_TOP - deck(MAST_Y))


def rail_padeye(s, y, label="padeye"):
    """A padeye on the rail cap; returns the point a line made fast to it ends at."""
    x = s * (sheer_half(u_of(y)) - T / 2)
    sh = sheer(y)
    box(boat, x - 0.03, x + 0.03, y - 0.05, y + 0.05, sh - 0.005, sh + 0.035, "metal_dark", label=label)
    torus(boat, (x, y, sh + 0.06), (0, 1, 0), 0.03, 0.009, 8, 4, "metal_dark", label=label + " eye")
    return Vector((x, y, sh + 0.075))


cyl(boat, (0, MAST_Y, deck(MAST_Y) - 0.05), (0, MAST_Y, MAST_TOP), MAST_R0, MAST_R1, 10, "spar_wood", label="mast")
box(boat, -0.18, 0.18, MAST_Y - 0.18, MAST_Y + 0.18, deck(MAST_Y) - 0.02, deck_top(MAST_Y) + 0.1, "metal_rust",
    label="mast step")
cyl(boat, (0, MAST_Y, MAST_TOP - 0.02), (0, MAST_Y, MAST_TOP + 0.06), 0.09, 0.09, 10, "metal_dark", label="mast cap")
sphere(boat, (0, MAST_Y, MAST_TOP + 0.12), 0.07, 8, 5, "lamp_glass", label="masthead light")
# the masthead crane: a bar across with an eye at each end for the outriggers' topping lifts, one aft for the boom's
CRANE_Z = MAST_TOP - 0.22
box(boat, -0.3, 0.3, MAST_Y - 0.04, MAST_Y + 0.04, CRANE_Z - 0.04, CRANE_Z + 0.04, "metal_dark", label="masthead crane")
CRANE_EYE = {}
for s in (1, -1):
    torus(boat, (s * 0.27, MAST_Y, CRANE_Z - 0.07), (0, 1, 0), 0.035, 0.01, 8, 4, "metal_dark", label="crane eye")
    CRANE_EYE[s] = Vector((s * 0.27, MAST_Y, CRANE_Z - 0.1))
box(boat, -0.03, 0.03, MAST_Y - 0.2, MAST_Y - 0.06, CRANE_Z - 0.04, CRANE_Z + 0.02, "metal_dark", label="crane aft arm")
BOOM_LIFT_EYE = Vector((0, MAST_Y - 0.17, CRANE_Z - 0.05))
box(boat, -0.02, 0.02, MAST_Y + 0.04, MAST_Y + 0.13, MAST_TOP - 0.18, MAST_TOP - 0.12, "metal_dark", label="forestay tang")
FORESTAY_TOP = Vector((0, MAST_Y + 0.13, MAST_TOP - 0.15))
# crosstree with the shrouds over its ends
CT_Z = 7.6
box(boat, -0.72, 0.72, MAST_Y - 0.05, MAST_Y + 0.05, CT_Z - 0.05, CT_Z + 0.05, "spar_wood", label="crosstree")
# the outrigger pivot: a steel collar with a pin each side (the outriggers' jaws close round these)
HINGE_Z = 3.65
box(boat, -0.3, 0.3, MAST_Y - 0.14, MAST_Y + 0.14, HINGE_Z - 0.16, HINGE_Z + 0.14, "metal_rust", label="pivot collar")
for s in (1, -1):
    cyl(boat, (s * 0.25, MAST_Y, HINGE_Z), (s * 0.5, MAST_Y, HINGE_Z), 0.035, 0.035, 8, "metal_dark", label="pivot pin")
    cyl(boat, (s * 0.42, MAST_Y - 0.1, HINGE_Z), (s * 0.42, MAST_Y + 0.1, HINGE_Z), 0.04, 0.04, 8, "metal_dark",
        label="pivot pin")
# heel blocks for the trawl cables, hung on straps aft of the collar
HEEL_BLOCK = {}
for s in (1, -1):
    hb = Vector((s * 0.3, MAST_Y - 0.26, HINGE_Z - 0.32))
    HEEL_BLOCK[s] = hb
    beam(boat, (s * 0.2, MAST_Y - 0.13, HINGE_Z - 0.12), hb + Vector((0, 0.02, 0.05)), 0.04, 0.015, "metal_dark",
         label="heel strap")
    cyl(boat, hb + Vector((0, -0.04, 0)), hb + Vector((0, 0.04, 0)), 0.075, 0.075, 10, "metal_rust", label="heel block")
# a cleat on the mast for the lazy lines and one for the boom's whip
for s in (1, -1):
    box(boat, s * 0.06 - 0.025, s * 0.06 + 0.025, MAST_Y + 0.07, MAST_Y + 0.14, 4.45, 4.75, "metal_dark",
        label="mast cleat")
MAST_CLEAT = {s: Vector((s * 0.06, MAST_Y + 0.14, 4.6)) for s in (1, -1)}
# standing rigging
stem_last, _ = station(1.0)
STEM_HEAD = Vector((0.0, stem_last[3][1] + 0.07, stem_last[3][2] + 0.36))
tube(boat, [FORESTAY_TOP, STEM_HEAD], LINE, 5, "wire", label="line forestay")
for s in (1, -1):
    top = Vector((s * 0.06, MAST_Y - 0.06, MAST_TOP - 0.3))
    end = rail_padeye(s, -6.27, "backstay padeye")
    tube(boat, [top, end], LINE, 5, "wire", label="line backstay")
    # shroud: crosstree end to a padeye on the rail just aft of the mast, set up with a turnbuckle
    end = rail_padeye(s, -2.05, "shroud padeye")
    start = Vector((s * 0.7, MAST_Y, CT_Z + 0.05))
    d = (end - start).normalized()
    tb0 = end - d * 0.32
    tb1 = end - d * 0.06
    tube(boat, [start, tb0], LINE, 5, "wire", label="line shroud")
    cyl(boat, tb0 - d * 0.01, tb1, 0.025, 0.025, 6, "metal_dark", label="turnbuckle")
    tube(boat, [tb1 - d * 0.01, end], LINE * 1.3, 5, "metal_dark", label="line turnbuckle eye")
# the cargo boom, swung aft over the working deck: gooseneck on the mast, topping lift to the masthead crane, a
# block at its end with the whip and hook, the whip's hauling part led along the boom to a cleat at its heel
GOOSE_Z = 4.1
box(boat, -0.08, 0.08, MAST_Y - mast_r(GOOSE_Z) - 0.12, MAST_Y - mast_r(GOOSE_Z) + 0.02, GOOSE_Z - 0.15, GOOSE_Z + 0.15,
    "metal_rust", label="gooseneck")
BOOM0 = Vector((0, MAST_Y - mast_r(GOOSE_Z) - 0.1, GOOSE_Z))
BOOM1 = Vector((0, -5.3, 4.85))
cyl(boat, BOOM0, BOOM1, 0.07, 0.05, 8, "spar_wood", label="boom")
bd = (BOOM1 - BOOM0).normalized()
cyl(boat, BOOM1 - bd * 0.12, BOOM1 + bd * 0.02, 0.065, 0.065, 8, "metal_dark", label="boom end band")
torus(boat, BOOM1 - bd * 0.05 + Vector((0, 0, 0.07)), (0, 1, 0), 0.03, 0.009, 8, 4, "metal_dark", label="boom lift eye")
tube(boat, [BOOM_LIFT_EYE, BOOM1 - bd * 0.05 + Vector((0, 0, 0.1))], LINE, 5, "rope", label="line boom topping lift")
blk = BOOM1 - bd * 0.05 + Vector((0, 0, -0.3))
tube(boat, [BOOM1 - bd * 0.05 + Vector((0, 0, -0.05)), blk + Vector((0, 0, 0.09))], 0.012, 5, "metal_dark",
     label="line block strop")
box(boat, -0.05, 0.05, blk.y - 0.08, blk.y + 0.08, blk.z - 0.09, blk.z + 0.09, "metal_rust", label="boom block")
HOOK = blk + Vector((0, 0, -1.1))
tube(boat, [blk + Vector((0, 0, -0.09)), HOOK + Vector((0, 0, 0.02))], LINE, 5, "rope", label="line whip")
cyl(boat, HOOK + Vector((0, 0, 0.04)), HOOK + Vector((0, 0, -0.12)), 0.035, 0.02, 6, "metal_dark", label="hook")
boom_cleat = BOOM0 + bd * 0.6
box(boat, 0.04, 0.11, boom_cleat.y - 0.08, boom_cleat.y + 0.08, boom_cleat.z - 0.03, boom_cleat.z + 0.03, "metal_dark",
    label="boom cleat")
tube(boat, [blk + Vector((0.05, 0.0, 0.0)), BOOM1 - bd * 0.35 + Vector((0.1, 0, 0)),
            boom_cleat + Vector((0.1, -0.08, 0.0))], 0.011, 5, "rope", label="line whip hauling part")
# --- the trawl winch on the middle line just abaft the mast: a drum each side for the trawl cables, a narrow middle
# drum (the try net's), the gearbox, and a warping head on each end of the shaft
WIN_Y = -2.25
d = deck(WIN_Y)
WIN_Z = d + 0.34                     # the shaft's height
DRUM_R = 0.15
box(boat, -0.66, 0.66, WIN_Y - 0.22, WIN_Y + 0.22, d - 0.02, d + 0.08, "metal_rust", label="winch base")
for x in (-0.6, -0.06, 0.06, 0.6):
    xa, xb = (x - 0.02, x + 0.02)
    box(boat, xa, xb, WIN_Y - 0.17, WIN_Y + 0.17, d + 0.06, WIN_Z + 0.12, "metal_rust", label="winch cheek")
cyl(boat, (-0.86, WIN_Y, WIN_Z), (0.86, WIN_Y, WIN_Z), 0.03, 0.03, 8, "metal_dark", label="winch shaft")
DRUM_X = {}
for s in (1, -1):
    xa, xb = sorted((s * 0.1, s * 0.56))
    cyl(boat, (xa, WIN_Y, WIN_Z), (xb, WIN_Y, WIN_Z), DRUM_R, DRUM_R, 12, "wire", label="winch drum")
    for x in (xa - 0.015, xb - 0.015):
        cyl(boat, (x, WIN_Y, WIN_Z), (x + 0.03, WIN_Y, WIN_Z), 0.22, 0.22, 12, "metal_rust", label="drum flange")
    DRUM_X[s] = s * 0.35
    # the warping head (gypsy) outside the cheek
    cyl(boat, (s * 0.63, WIN_Y, WIN_Z), (s * 0.82, WIN_Y, WIN_Z), 0.11, 0.08, 10, "metal_dark", label="warping head")
cyl(boat, (-0.04, WIN_Y, WIN_Z), (0.04, WIN_Y, WIN_Z), 0.12, 0.12, 10, "wire", label="try net drum")
box(boat, -0.12, 0.12, WIN_Y + 0.12, WIN_Y + 0.4, d + 0.06, d + 0.42, "metal_rust", label="winch gearbox")
# the trawl cables, each from the top of its drum up and forward to its heel block on the mast
for s in (1, -1):
    hb = HEEL_BLOCK[s]
    start = Vector((DRUM_X[s], WIN_Y + 0.02, WIN_Z + DRUM_R - 0.004))
    tube(boat, [start, hb + Vector((0, -0.02, -0.07))], 0.016, 5, "wire", label="line trawl cable lead")
# a fish hold hatch in the middle of the aft deck, aft of the diver's pump
d = deck_top(-4.55)
box(boat, -0.95, 0.25, -5.0, -4.1, d - 0.02, d + 0.26, "trim", label="hatch coaming", grime=True)
box(boat, -1.0, 0.3, -5.05, -4.05, d + 0.26, d + 0.31, "deck_wood", (0.78, 0.74, 0.68), label="hatch cover")
for y in (-4.8, -4.3):
    box(boat, -1.02, 0.32, y - 0.04, y + 0.04, d + 0.3, d + 0.34, "metal_rust", label="hatch batten")

# --- the diver's air pump: an old two-cylinder pump in a wooden chest near the middle line, wound by a big crank
# wheel on its starboard side (the PumpWheel node). The diver stands forward of the wheel facing aft, side on to
# the title camera, which sees the wheel face on.
DIVER = Vector((-0.2, -3.0, deck_top(-3.0)))
PUMP_HUB = Vector((DIVER.x, DIVER.y - 0.5, DIVER.z + 1.0))
CH_X0, CH_X1 = DIVER.x - 0.72, DIVER.x - 0.1      # the chest, to port of the wheel
CH_Y0, CH_Y1 = PUMP_HUB.y - 0.36, PUMP_HUB.y + 0.36
d = DIVER.z
CH_TOP = d + 1.12     # the chest stands above the crank wheel's hub, which turns on a shaft out of its side
box(boat, CH_X0, CH_X1, CH_Y0, CH_Y1, d - 0.01, CH_TOP, "cabin_wood", label="pump chest", grime=True)
box(boat, CH_X0 - 0.02, CH_X1 + 0.02, CH_Y0 - 0.02, CH_Y1 + 0.02, CH_TOP, CH_TOP + 0.05, "trim", label="pump lid")
box(boat, CH_X0 - 0.02, CH_X1 + 0.02, CH_Y0 - 0.02, CH_Y1 + 0.02, d - 0.01, d + 0.07, "trim", label="pump plinth")
for z in (d + 0.3, d + 0.62):
    box(boat, CH_X0 - 0.008, CH_X1 + 0.008, CH_Y0 - 0.008, CH_Y1 + 0.008, z, z + 0.035, "brass", label="chest band")
# the two brass cylinders standing on the lid, a crosshead over them, an outlet and a gauge
cx = (CH_X0 + CH_X1) / 2
for y in (PUMP_HUB.y - 0.17, PUMP_HUB.y + 0.17):
    cyl(boat, (cx, y, CH_TOP + 0.04), (cx, y, CH_TOP + 0.3), 0.075, 0.075, 12, "brass", label="pump cylinder")
    cyl(boat, (cx, y, CH_TOP + 0.3), (cx, y, CH_TOP + 0.34), 0.09, 0.09, 12, "brass", label="cylinder cap")
    cyl(boat, (cx, y, CH_TOP + 0.34), (cx, y, CH_TOP + 0.46), 0.02, 0.02, 6, "metal_dark", label="piston rod")
box(boat, cx - 0.04, cx + 0.04, PUMP_HUB.y - 0.24, PUMP_HUB.y + 0.24, CH_TOP + 0.46, CH_TOP + 0.51, "metal_dark",
    label="crosshead")
cyl(boat, (cx, PUMP_HUB.y, CH_TOP + 0.04), (cx, PUMP_HUB.y, CH_TOP + 0.16), 0.03, 0.025, 8, "brass", label="outlet")
cyl(boat, (cx, CH_Y0 + 0.001, d + 0.5), (cx, CH_Y0 - 0.03, d + 0.5), 0.08, 0.08, 12, "brass", label="gauge")
cyl(boat, (cx, CH_Y0 - 0.02, d + 0.5), (cx, CH_Y0 - 0.036, d + 0.5), 0.065, 0.065, 12, "lamp_glass", label="gauge face")
# the wheel's shaft out of the chest's starboard side, with a bearing
cyl(boat, (CH_X1 - 0.02, PUMP_HUB.y, PUMP_HUB.z), (PUMP_HUB.x - 0.03, PUMP_HUB.y, PUMP_HUB.z), 0.028, 0.028, 8, "metal_dark",
    label="pump shaft")
cyl(boat, (CH_X1 - 0.01, PUMP_HUB.y, PUMP_HUB.z), (CH_X1 + 0.03, PUMP_HUB.y, PUMP_HUB.z), 0.07, 0.07, 10, "brass",
    label="bearing")
# the air hose: from the outlet to a coil on deck by the pump, and on to the diver's feet
dd = deck_top(-3.6)
COIL = Vector((0.42, -3.75, dd))
for i, R in enumerate((0.27, 0.24, 0.21)):
    torus(boat, COIL + Vector((0.01 * i, -0.01 * i, 0.03 + 0.05 * i)), (0, 0, 1), R, 0.028, 16, 6, "hose_rubber",
          label="hose coil")
hose = catmull([(cx, PUMP_HUB.y, CH_TOP + 0.16), (cx + 0.05, PUMP_HUB.y - 0.12, CH_TOP + 0.22),
                (cx + 0.2, CH_Y0 - 0.12, CH_TOP - 0.1), (COIL.x - 0.3, COIL.y - 0.22, dd + 0.08),
                (COIL.x - 0.18, COIL.y - 0.1, dd + 0.13)], 4)
tube(boat, hose, 0.028, 6, "hose_rubber", label="hose to coil")
HOSE_END = Vector((0.15, -2.75, deck_top(-2.75) + 0.03))
hose2 = catmull([(COIL.x + 0.2, COIL.y + 0.1, dd + 0.13), (COIL.x + 0.3, COIL.y + 0.4, dd + 0.05),
                 (0.5, -3.0, deck_top(-3.0) + 0.03), (HOSE_END.x, HOSE_END.y, HOSE_END.z)], 4)
tube(boat, hose2, 0.028, 6, "hose_rubber", label="hose to diver")

# --- crates and baskets at the stern, a coil of rope to port
d = deck_top(-5.8)
box(boat, -1.5, -0.9, -6.2, -5.78, d - 0.005, d + 0.34, "crate_wood", (0.95, 0.95, 0.95), label="crate")
box(boat, -1.45, -0.95, -6.15, -5.8, d + 0.34, d + 0.64, "crate_wood", (0.82, 0.8, 0.76), label="crate")
box(boat, -1.5, -0.95, -5.72, -5.3, d - 0.005, d + 0.34, "crate_wood", (1.0, 0.98, 0.94), label="crate")
for cx, cy, n in ((1.15, -5.9, 3), (-0.35, -6.0, 1)):
    for i in range(n):
        z0 = d - 0.005 + 0.12 * i
        cyl(boat, (cx, cy, z0), (cx, cy, z0 + 0.38), 0.21, 0.26, 12, "basket", label="basket")
        torus(boat, (cx, cy, z0 + 0.38), (0, 0, 1), 0.26, 0.02, 12, 4, "basket", label="basket rim")
d = deck_top(-2.0)
for i, R in enumerate((0.3, 0.265, 0.23)):
    torus(boat, (-1.35 + 0.01 * i, -2.0, d + 0.035 + 0.05 * i), (0, 0, 1), R, 0.035, 16, 6, "rope", label="rope coil")

# --- the anchor stowed for sea: lying on the foredeck to starboard, its stock folded along its shank
AX = 0.55


def on_deck(x, y, up=0.035):
    return (x, y, deck_top(y) + up)


tube(boat, [on_deck(AX, 4.45), on_deck(AX, 5.0), on_deck(AX, 5.5)], 0.035, 6, "metal_rust", label="anchor shank")
torus(boat, on_deck(AX, 5.58, 0.03), (0, 0, 1), 0.07, 0.016, 10, 4, "metal_rust", label="anchor ring")
tube(boat, [on_deck(AX + 0.08, 4.75, 0.025), on_deck(AX + 0.08, 5.45, 0.025)], 0.025, 6, "metal_rust", label="anchor stock")
sphere(boat, on_deck(AX + 0.08, 5.45, 0.03), 0.04, 6, 4, "metal_rust", label="stock ball")
for s in (1, -1):
    arm = [on_deck(AX, 4.45), on_deck(AX + s * 0.22, 4.5), on_deck(AX + s * 0.36, 4.65), on_deck(AX + s * 0.42, 4.85)]
    tube(boat, arm, 0.03, 6, "metal_rust", label="anchor arm")
    p = Vector(on_deck(AX + s * 0.41, 4.8, 0.03))
    obox(boat, p, (0.07, 0, 0), (0, 0.09, 0.0), (0, 0, 0.012), "metal_rust", label="fluke")
# a lashing over the shank to the deck
torus(boat, on_deck(AX, 5.05, 0.02), (0, 1, 0), 0.05, 0.012, 10, 4, "rope", label="anchor lashing")

# --- wear and repair on the hull: scuppers with rust weeping from them, rust under the cleats and the
# hawse, a patch of red primer, a patch of fresher white, blank name boards, tyre fenders to starboard


def flat(z):
    return lambda y: z


def under_rail(dz):
    return lambda y: sheer(y) - dz


def streak(s, y, top, length, wide):
    """A few thin runs of rust from one point, each its own length."""
    runs = ((-wide * 0.35, 0.55 + 0.3 * RNG.random(), 0.004), (0.0, 1.0, 0.007), (wide * 0.4, 0.4 + 0.4 * RNG.random(), 0.01))
    for k_, (dy, f, out) in enumerate(runs):
        ln = length * f
        w = wide * (0.5 if dy else 0.8)
        hull_patch(boat, s, [y + dy - w / 2, y + dy, y + dy + w / 2], lambda yy, a=top, b=ln: a(yy) - b, lambda yy, a=top, k=k_: a(yy) - 0.004 * k,
                   "hull_white", label="rust run", nz=3, width=lambda t, w=w: w * (1 - 0.8 * t), out=out, cols=weep)


for s in (1, -1):
    for i, y in enumerate((-5.2, -3.6, -2.0, -0.4, 1.0)):
        # a freeing port at deck level: a dark slot in the bulwark
        hull_patch(boat, s, [y - 0.13, y + 0.13], lambda yy: deck(yy) + 0.02, lambda yy: deck(yy) + 0.1, "metal_dark",
                   label="scupper", nz=1)
        if (i + (s > 0)) % 2 == 0:
            streak(s, y, lambda yy: deck(yy) + 0.02, 0.3 + 0.2 * RNG.random(), 0.08)
    for y in (-6.0, -1.3):
        streak(s, y, under_rail(0.31), 0.3 + 0.15 * RNG.random(), 0.06)
# single runs of rust from under the rail along the starboard side (the camera's side), each its own length
for y in (-5.7, -4.6, -2.7, -1.5, -0.9, 0.3, 1.3):
    ln = 0.25 + 0.45 * RNG.random()
    w = 0.025 + 0.025 * RNG.random()
    hull_patch(boat, 1, [y - w / 2, y, y + w / 2], lambda yy, ln=ln: sheer(yy) - 0.31 - ln, under_rail(0.31), "hull_white",
               label="rail rust", nz=3, width=lambda t, w=w: w * (1 - 0.5 * t), out=0.012, cols=weep)
# the anchor's stain, above the deck on the starboard bow
streak(1, 5.2, under_rail(0.31), 0.25, 0.16)
# a plank renewed below the stripe, primed red-lead and never painted over
hull_patch(boat, 1, [-3.4, -3.0, -2.6, -2.25], flat(0.47), flat(0.54), "primer_red", label="primer plank", nz=1)
# blank name boards on the bow bulwarks (the name is left off)
for s in (1, -1):
    ys = [3.95, 4.3, 4.6, 4.95]
    hull_patch(boat, s, ys, under_rail(0.5), under_rail(0.31), "trim", label="name board frame", nz=1, out=0.01)
    hull_patch(boat, s, [y if i in (1, 2) else y + (0.04 if i == 0 else -0.04) for i, y in enumerate(ys)],
               under_rail(0.48), under_rail(0.33), "name_board", label="name board", nz=1, out=0.018)
box(boat, -1.0, 1.0, -HALF - 0.03, -HALF + 0.02, 0.7, 1.0, "trim", label="transom board frame")
box(boat, -0.95, 0.95, -HALF - 0.045, -HALF + 0.02, 0.73, 0.97, "name_board", label="transom name board")
# tyre fenders hung on ropes from the starboard rail
for y in (-3.2, 0.5):
    zt = sheer(y) - 0.62
    xt = outer_half(u_of(y), zt + 0.3, sheer(y)) + LAP + 0.14
    torus(boat, (xt, y, zt), (1, 0, 0.3), 0.24, 0.095, 18, 6, "hose_rubber", label="tyre")
    t_ax = Vector((1, 0, 0.3)).normalized()
    t_top = Vector((xt, y, zt)) + (Vector((0, 0, 1)) - t_ax * t_ax.z).normalized() * (0.24 + 0.08)
    bs_ = sheer_half(u_of(y))
    tube(boat, [t_top, (bs_ + 0.1, y, sheer(y) - 0.12), (bs_ - 0.05, y, sheer(y) + 0.012)], 0.016, 5, "rope",
         label="tyre rope")

# ---------------------------------------------------------------------------------------------- the wheel
wheel = Build("Wheel", WHEEL_HUB)
H = WHEEL_HUB
torus(wheel, H, (0, 1, 0), 0.3, 0.024, 24, 6, "cabin_wood", label="rim")
cyl(wheel, H + Vector((0, 0.05, 0)), H + Vector((0, -0.06, 0)), 0.07, 0.07, 12, "brass", label="hub")
cyl(wheel, H + Vector((0, -0.06, 0)), H + Vector((0, -0.08, 0)), 0.045, 0.04, 12, "brass", label="hub cap")
for i in range(8):
    a = math.pi / 4 * i
    e = Vector((math.cos(a), 0, math.sin(a)))
    tube(wheel, [H + e * 0.05, H + e * 0.26, H + e * 0.33, H + e * 0.38, H + e * 0.45],
         [0.018, 0.015, 0.016, 0.026, 0.02], 6, "cabin_wood", label="spoke")

# ---------------------------------------------------------------------------------------------- the pump's crank wheel
# The diver's air pump: an old two-cylinder pump in a wooden chest, wound by a big crank wheel on its starboard
# side. The wheel turns about X (athwartships), so the title camera abeam sees it face on; the handle is at the
# top (radius 0.22) when the wheel is unturned.
pump_wheel = Build("PumpWheel", PUMP_HUB)
H = PUMP_HUB
torus(pump_wheel, H, (1, 0, 0), 0.35, 0.026, 24, 6, "metal_dark", label="rim")
cyl(pump_wheel, H + Vector((-0.04, 0, 0)), H + Vector((0.04, 0, 0)), 0.065, 0.065, 12, "brass", label="hub")
for i in range(6):
    a = math.pi / 3 * i + math.pi / 6
    e = Vector((0, math.cos(a), math.sin(a)))
    cyl(pump_wheel, H + e * 0.05, H + e * 0.34, 0.017, 0.014, 6, "metal_dark", label="spoke")
grip = H + Vector((0, 0, 0.22))
cyl(pump_wheel, H + Vector((0.0, 0, 0.0)) + Vector((0.01, 0, 0)), grip + Vector((0.01, 0, 0)), 0.02, 0.02, 6, "metal_dark",
    label="crank arm")
cyl(pump_wheel, grip, grip + Vector((0.2, 0, 0)), 0.018, 0.018, 6, "metal_dark", label="crank pin")
cyl(pump_wheel, grip + Vector((0.05, 0, 0)), grip + Vector((0.19, 0, 0)), 0.03, 0.03, 8, "cabin_wood", label="crank grip")

# ---------------------------------------------------------------------------------------------- outriggers
# Each outrigger pivots on its pin in the mast's collar and stands raised 65 degrees, held by its topping lift to
# the masthead crane and steadied by a fore guy and an aft guy to padeyes on the rail. At its end hangs the towing
# block; the trawl cable comes from the winch through the heel block, runs up along the outrigger to the towing
# block and down to a ring from which that side's pair of trawl doors hang in the travelling ("doors up") position.
# The net is bundled and lashed along the forward side of the outrigger, floats along its headrope, its cod end at
# the heel with chafing gear, made fast to a cleat on the mast by its lazy line. Everything here turns with the
# outrigger, so these lines are right only at the built angle.
OUT_LEN = 6.5
OUT_ANGLE = math.radians(65)
# the guys' and topping lifts' deck ends are fixed fittings in Boat
GUY_FWD = {s: rail_padeye(s, 4.6, "guy padeye") for s in (1, -1)}
GUY_AFT = {s: rail_padeye(s, -5.6, "guy padeye") for s in (1, -1)}
outriggers = []
for s, name in ((-1, "OutriggerPort"), (1, "OutriggerStarboard")):
    hinge = Vector((s * 0.42, MAST_Y, HINGE_Z))
    o = Build(name, hinge)
    o.smooth_deg = 65
    dvec = Vector((s * math.cos(OUT_ANGLE), 0, math.sin(OUT_ANGLE)))      # along the outrigger
    up = Vector((-s * math.sin(OUT_ANGLE), 0, math.cos(OUT_ANGLE)))       # square to it, upward and inboard
    fwd = Vector((0, 1, 0))
    tip = hinge + dvec * OUT_LEN

    def at(L, u=0.0, f=0.0):
        return hinge + dvec * L + up * u + fwd * f

    def pole_r(L):
        return 0.085 + (0.05 - 0.085) * L / OUT_LEN

    cyl(o, at(0.12), tip, pole_r(0.12), 0.05, 8, "spar_wood", label="pole")
    # the heel's steel jaw round the pivot pin
    box(o, hinge.x - 0.05, hinge.x + 0.05, MAST_Y - 0.09, MAST_Y + 0.09, HINGE_Z - 0.07, HINGE_Z + 0.07, "metal_rust",
        label="heel jaw")
    cyl(o, hinge, at(0.45), pole_r(0.0) + 0.02, pole_r(0.45) + 0.02, 10, "metal_rust", label="heel ferrule")
    # the end fitting: a band, an eye on top for the topping lift and guys, and the towing block under it
    cyl(o, at(OUT_LEN - 0.18), tip + dvec * 0.02, 0.06, 0.06, 8, "metal_dark", label="end band")
    eye = at(OUT_LEN - 0.08, 0.09)
    torus(o, eye, (0, 1, 0), 0.035, 0.01, 8, 4, "metal_dark", label="end eye")
    tb = at(OUT_LEN - 0.02, -0.2) + dvec * 0.0
    beam(o, at(OUT_LEN - 0.08, -0.04), tb + up * 0.08, 0.05, 0.02, "metal_dark", up=(0, 1, 0), label="block strap")
    cyl(o, tb + Vector((0, -0.045, 0)), tb + Vector((0, 0.045, 0)), 0.1, 0.1, 12, "metal_rust", label="towing block")
    # topping lift to the masthead crane, guys to the rail
    tube(o, [eye + up * 0.03, CRANE_EYE[s]], LINE, 5, "rope", label="line topping lift")
    tube(o, [eye + Vector((0, 0.03, 0.02)), GUY_FWD[s]], LINE, 5, "rope", label="line fore guy")
    tube(o, [eye + Vector((0, -0.03, 0.02)), GUY_AFT[s]], LINE, 5, "rope", label="line aft guy")
    # the trawl cable: from the heel block up along the outrigger's upper side to the towing block, and down
    # from the block to the doors' ring
    hb = HEEL_BLOCK[s]
    # along the outrigger's underside: the heel block and the towing block both hang under it
    c_top = tb - dvec * 0.1
    tube(o, [hb + Vector((0, 0.02, 0.07)), at(1.0, -0.2), c_top], 0.016, 5, "wire", label="line trawl cable")
    RING = tb + Vector((s * 0.09, 0, -0.75))
    tube(o, [tb + Vector((s * 0.09, 0, -0.04)), RING + Vector((0, 0, 0.05))], 0.016, 5, "wire", label="line trawl cable down")
    torus(o, RING, (0, 1, 0), 0.05, 0.014, 8, 4, "metal_dark", label="door ring")
    # the pair of trawl doors (otter boards) hanging from the ring on short chain bridles, one aft, one forward
    DX = RING.x + s * 0.02
    dz1 = RING.z - 0.3
    dz0 = dz1 - 0.72
    for k, dy0 in enumerate((MAST_Y - 1.0, MAST_Y + 0.08)):
        dl = 0.92
        dpts = [(0.0, dz0), (dl - 0.1, dz0), (dl, dz0 + 0.1), (dl, dz1 - 0.08), (dl - 0.08, dz1), (0.08, dz1),
                (0.0, dz1 - 0.08)]
        prism(o, dpts, (DX, dy0, 0.0), (0, 1, 0), (0, 0, 1), 0.035, "door_wood", label="otter door")
        box(o, DX - 0.045, DX + 0.045, dy0, dy0 + dl, dz0 - 0.03, dz0 + 0.05, "metal_rust", label="door shoe")
        for yb, dyb in ((0.22, 0.18), (dl - 0.22, -0.18)):
            beam(o, (DX + s * 0.04, dy0 + yb, dz0 + 0.05), (DX + s * 0.04, dy0 + yb + dyb, dz1 - 0.04),
                 0.06, 0.025, "metal_rust", up=(s, 0, 0), label="door brace")
            tube(o, [RING + Vector((0, (yb - dl / 2) * 0.05, -0.04)), (DX + s * 0.06, dy0 + yb + dyb, dz1 - 0.04)],
                 0.011, 4, "metal_dark", label="line door bridle")
        if k == 0:
            box(o, DX + s * 0.035 - 0.004, DX + s * 0.035 + 0.004, dy0 + 0.42, dy0 + 0.5, dz0 + 0.05, dz1 - 0.15, "rust",
                label="door rust")
    # the net, bundled along the outrigger's forward side and lashed to it at four points, sagging between them
    LASH = [1.15, 2.25, 3.35, 4.4]
    L0, L1 = 0.8, 4.65
    n_pts = 26
    path, radii = [], []
    for i in range(n_pts):
        L = L0 + (L1 - L0) * i / (n_pts - 1)
        r = 0.15 + 0.03 * math.sin(i * 1.3) + (0.06 if L < 1.05 else 0.0)
        gap = min(abs(L - a) for a in LASH)
        sag = 0.0 if gap < 0.06 else 0.1 * math.sin(math.pi * min(1.0, gap / 0.55))
        path.append(at(L, -sag, pole_r(L) + r + 0.005))
        radii.append(r)
    # the bundle's ends close in over three rings (a flat end read as a cup)
    for k, f in enumerate((0.25, 0.65, 0.9)):
        radii[k] *= f
        radii[-1 - k] *= f
    tube(o, path, radii, 10, "net_green", cols=lambda k, j: (0.55, 0.6, 0.55) if (k + j) % 2 else WHITE,
         jitter=lambda k, j: 1.0 + 0.08 * math.sin(k * 2.3 + j * 1.9), label="net bundle")
    # the lashings: a loop of rope round outrigger and bundle at each lashing point
    for a in LASH:
        p = at(a)
        i = min(range(n_pts), key=lambda i: abs(L0 + (L1 - L0) * i / (n_pts - 1) - a))
        q = path[i]
        rq = radii[i] + 0.02
        rp = pole_r(a) + 0.015
        loop = []
        e2 = up                         # the loop lies square to the outrigger: in the plane of up and fwd
        for j in range(8):              # round the far side of the pole (aft)
            t = math.pi / 2 + math.pi * j / 7
            loop.append(p + e2 * (rp * math.sin(t)) + fwd * (rp * math.cos(t)))
        for j in range(8):              # round the far side of the bundle (forward)
            t = -math.pi / 2 + math.pi * j / 7
            loop.append(q + e2 * (rq * math.sin(t)) + fwd * (rq * math.cos(t)))
        tube(o, loop, 0.014, 4, "rope", closed=True, label="net lashing")
    # floats along the headrope, on the bundle's outboard side
    for i in range(4, n_pts - 2, 3):
        Li = L0 + (L1 - L0) * i / (n_pts - 1)
        if min(abs(Li - a) for a in LASH) < 0.25:
            continue
        q = path[i]
        sphere(o, q + Vector((s * 0.0, 0, 0)) - up * (radii[i] + 0.035), 0.065, 6, 4, "float_orange", label="float",
               squash=(1, 1, 0.8))
    # chafing gear on the cod end (at the heel), and the lazy line from it to the cleat on the mast
    for i in (1, 3):
        q = path[i]
        torus(o, q, dvec, radii[i] * 1.02, 0.03, 12, 4, "metal_rust", label="chafing gear")
    tube(o, [path[0] - dvec * 0.03, MAST_CLEAT[s]], 0.013, 5, "rope", label="line lazy line")
    outriggers.append(o)

# ---------------------------------------------------------------------------------------------- check and write
total = 0
wrong_all = 0
for b in [boat, wheel, pump_wheel] + outriggers:
    wrong, counted, bad = b.inside_out()
    print("INSIDE-OUT %s: %d of %d triangles face inwards, %d parts" % (b.name, wrong, counted, len(b.parts)))
    for label, n, of, where in bad:
        print("   bad part %s: %d of %d, at %s" % (label, n, of, where))
    wrong_all += wrong
    print("TRIANGLES %s: %d" % (b.name, len(b.tris)))
    total += len(b.tris)
print("TRIANGLES total: %d" % total)
print("INSIDE-OUT %s" % ("PASSED" if wrong_all == 0 else "FAILED (%d)" % wrong_all))

# ---------------------------------------------------------------------------------------------- clipping check
# Every part against every other, in place: bounding boxes first, then BVH triangle overlap; for pairs whose
# triangles cross, how deep each one's corners sit inside the other (a ray-parity inside test against the other's
# closed skin, then the distance to its surface). A pair deeper than CLIP_MM that is not listed in SET_INTO (parts
# meant to be set one into the other) is printed as CLIP. Also printed: coincident faces (z-fighting), parts that
# touch nothing (floating), parts not joined to the hull through what they touch, and line ends made fast to nothing.
import fnmatch

CLIP_MM = 4.0
SET_INTO = [   # (label pattern, label pattern, why it is meant)
    ("hull", "plank", "planks are laid 1 cm into the deck surface"),
    ("hull", "frame", "bulwark frames are let into the bulwark"),
    ("hull", "*rail*", "rub rails and the rail cap's fittings are fastened into the planking"),
    ("hull", "*strake*", "the rubbing strake is fastened into the planking"),
    ("hull", "stem bar", "the stem post is the hull's own"),
    ("hull", "transom*", "transom boards are part of the stern"),
    ("hull", "skeg", "the skeg is the hull's"), ("hull", "rudder", "the rudder's head is in the hull"),
    ("skeg", "prop*", "the shaft and hub come out of the skeg"), ("skeg", "shoe", "the shoe is bolted to the skeg"),
    ("rudder", "shoe", "the rudder's heel sits in the shoe"), ("prop hub", "prop blade", "blades are cast on the hub"),
    ("hull", "*wall*", "house walls go down through the deck"), ("plank", "*wall*", "house walls go down through the deck"),
    ("hull", "*post*", "posts are stepped in the deck"), ("plank", "*post*", "posts are stepped in the deck"),
    ("hull", "house foot", "the house's foot board goes down to the deck"), ("plank", "house foot", "as above"),
    ("hull", "door sill", "the sill is let into the deck"), ("plank", "door sill", "as above"),
    ("hull", "pedestal", "on the deck"), ("plank", "pedestal", "on the deck"),
    ("hull", "shelf front", "on the deck"), ("plank", "shelf front", "on the deck"),
    ("hull", "mast*", "the mast is stepped through the deck"), ("plank", "mast*", "the mast is stepped through the deck"),
    ("mast", "mast step", "the step is round the mast"), ("mast", "mast cap", "the cap is on the mast"),
    ("mast", "masthead*", "the light and crane are on the mast"), ("mast", "crane*", "on the mast"),
    ("mast", "forestay tang", "on the mast"), ("mast", "crosstree", "through the mast"),
    ("mast", "pivot*", "the collar is round the mast"), ("mast", "gooseneck", "on the mast"),
    ("mast", "mast cleat", "on the mast"), ("mast", "heel strap", "strapped to the collar on the mast"),
    ("pivot*", "pivot*", "collar and pins are one fitting"), ("pivot*", "heel strap", "strapped to the collar"),
    ("heel strap", "heel block", "the block hangs in its strap"),
    ("pivot pin", "heel jaw", "the jaw closes round the pin"), ("heel jaw", "heel ferrule", "one fitting"),
    ("heel ferrule", "pole", "the ferrule is on the pole's heel"), ("heel jaw", "pole", "the jaw is on the pole's heel"),
    ("pole", "end band", "the band is round the pole's end"), ("end band", "block strap", "one fitting"),
    ("end band", "end eye", "welded on"), ("block strap", "towing block", "the block hangs in its strap"),
    ("pole", "block strap", "strapped to the pole's end"), ("pole", "end eye", "welded to the band"),
    ("crane*", "crane*", "one fitting"),
    ("boom", "gooseneck", "the boom's heel is in the gooseneck"), ("boom", "boom end band", "on the boom"),
    ("boom*", "boom lift eye", "on the band"), ("boom", "boom cleat", "on the boom"),
    ("boom block", "line block strop", "the strop holds the block"),
    ("hull", "*padeye*", "padeyes are bolted through the rail cap"), ("*padeye", "*padeye eye", "one fitting"),
    ("turnbuckle", "line*", "the wire's eye is in the turnbuckle"),
    ("*roof*", "*post*", "posts hold the roofs"), ("*roof*", "*wall*", "walls hold the roofs"),
    ("*roof*", "*fascia*", "the fascia is the roof's edge"), ("*fascia*", "*fascia*", "boards meet at the corners"),
    ("*roof*", "stack*", "the stack goes up through the roof"), ("stack*", "stack*", "one stack"),
    ("*roof*", "light post", "on the roof"), ("*roof*", "horn post", "on the roof"), ("*roof*", "aerial base", "on the roof"),
    ("*roof*", "roof rail", "the rail's feet are on the roof"),
    ("*wall*", "*wall*", "walls meet at the corners"), ("*wall*", "*post*", "corner posts"),
    ("*wall*", "glass", "panes sit in the walls"), ("*wall*", "sill", "sills are let into the walls"),
    ("*wall*", "lintel", "on the wall"), ("*wall*", "jamb", "on the wall"), ("*wall*", "door*", "the doorway's frame"),
    ("*wall*", "house foot", "on the wall"), ("*wall*", "light board", "on the wall"),
    ("*wall*", "chart shelf", "the shelf is built into the house"), ("*wall*", "shelf front", "as above"),
    ("chart shelf", "shelf front", "one piece"), ("*wall*", "brow*", "the brow is on the front wall"),
    ("brow*", "brow*", "one piece"), ("*wall*", "running light", "on the board"), ("light board", "running light", "on the board"),
    ("sill", "jamb", "frame corners"), ("lintel", "jamb", "frame corners"), ("glass", "jamb", "the pane's edge is in the frame"),
    ("glass", "sill", "as above"), ("glass", "lintel", "as above"),
    ("door", "door*", "the door's own pieces"), ("door jamb", "door lintel", "frame corner"),
    ("door sill", "door jamb", "frame corner"), ("door hinge", "*jamb*", "hinged on the jamb"),
    ("door*", "house foot", "the folded door lies on the foot board's edge"),
    ("corner post", "*", "corner posts are the house's corners"),
    ("pedestal", "axle", "the wheel's axle is in the pedestal"), ("rim", "spoke", "the wheel's own"),
    ("hub*", "spoke", "the wheel's own"), ("hub", "hub cap", "the wheel's own"), ("axle", "hub", "the wheel is on its axle"),
    ("hub", "crank*", "the crank is on the hub"), ("crank*", "crank*", "one crank"),
    ("pump*", "pump*", "the pump's own pieces"), ("pump*", "chest band", "bands round the chest"),
    ("pump*", "bearing", "the shaft's bearing"), ("pump shaft", "hub", "the wheel is on the shaft"),
    ("pump lid", "*cylinder*", "the cylinders stand on the lid"), ("*cylinder*", "*cap*", "one cylinder"),
    ("*cap*", "piston rod", "the rod comes out of the cylinder"), ("piston rod", "crosshead", "the rod holds the crosshead"),
    ("pump lid", "outlet", "on the lid"), ("pump chest", "gauge*", "on the chest"), ("gauge", "gauge face", "one gauge"),
    ("hose*", "*", "a rubber hose lies over and round things"),
    ("winch*", "winch*", "the winch's own pieces"), ("winch*", "drum*", "the winch's own"), ("drum*", "drum*", "one drum"),
    ("winch*", "*drum", "the winch's own"), ("winch*", "warping head", "on the shaft"),
    ("*drum*", "line trawl cable lead", "the cable leaves its drum"), ("heel block", "line trawl cable*", "led through the block"),
    ("towing block", "line trawl cable*", "led over the block"), ("door ring", "line*", "made fast to the ring"),
    ("otter door", "door*", "the door's own fittings"), ("door*", "line door bridle", "the bridle's shackle"),
    ("door shoe", "door brace", "one fitting"), ("door brace", "door brace", "one fitting"),
    ("net bundle", "net lashing", "the lashing is drawn tight round the bundle"),
    ("pole", "net lashing", "the lashing is drawn tight round the outrigger"),
    ("net bundle", "float", "floats are on the headrope"), ("net bundle", "chafing gear", "round the cod end"),
    ("net bundle", "line lazy line", "made fast to the cod end"), ("mast cleat", "line*", "made fast"),
    ("end eye", "line*", "made fast to the eye"), ("crane eye", "line*", "made fast to the eye"),
    ("*padeye*", "line*", "made fast to the padeye"), ("boom lift eye", "line*", "made fast"),
    ("boom block", "line*", "led through the block"), ("boom cleat", "line*", "made fast"), ("hook", "line whip", "on the hook"),
    ("forestay tang", "line forestay", "made fast"), ("stem bar", "line forestay", "made fast to the stem head"),
    ("mast", "line backstay", "made fast at the masthead"), ("crosstree", "line shroud", "over the crosstree's end"),
    ("line*", "line*", "lines made fast to the same fitting meet there"),
    ("crate", "crate", "stacked"), ("basket*", "basket*", "stacked and nested"),
    ("rope coil", "rope coil", "a coil"), ("hose coil", "hose coil", "a coil"),
    ("hatch*", "hatch*", "the hatch's own pieces"), ("plank", "hatch*", "the coaming is on the deck"),
    ("hull", "hatch*", "the coaming is on the deck"),
    ("*", "scupper", "a slot cut in the bulwark"), ("*", "rust run", "paint on the planking"),
    ("*", "rail rust", "paint"), ("*", "primer plank", "paint"), ("*", "name board*", "fastened on the bulwark"),
    ("*", "house rust", "paint"), ("*", "door rust", "paint"),
    ("cleat post", "cleat horn", "one cleat"), ("hull", "cleat*", "on the rail cap"),
    ("anchor*", "anchor*", "one anchor"), ("anchor*", "stock ball", "one anchor"), ("anchor*", "fluke", "one anchor"),
    ("plank", "anchor*", "lying on the deck"), ("hull", "anchor*", "lying on the deck"),
    ("tyre", "tyre rope", "the rope through the tyre"), ("hull", "tyre rope", "made fast round the rail"),
    ("life ring", "ring lanyard", "the lanyard round the ring"), ("hull", "ring lanyard", "made fast round the rail"),
    ("hull", "winch*", "the winch's bed is bolted down through the deck"), ("light post", "searchlight", "on its post"),
    ("transom*", "transom*", "boards on the transom"), ("aerial*", "aerial*", "the aerial in its base"),
    ("door hook", "hook eye", "hooked in the eye"), ("boom end band", "line*", "made fast to the band"),
    ("masthead crane", "crane*", "one fitting"), ("crank*", "spoke", "the crank is on a spoke"),
    ("pipe clip", "*pipe", "the clip holds the pipe"), ("mast cap", "masthead light", "on the cap"),
    ("pivot pin", "heel ferrule", "the pin goes through the outrigger's heel"), ("heel strap", "line*", "at the block"),
    ("horn post", "horn", "on its post"), ("*wall*", "pipe clip", "screwed to the wall"), ("*wall*", "*pipe", "against the wall"),
    ("*wall*", "wall board", "the lining on the wall"), ("wall board", "wall board", "boards side by side"),
    ("wall board", "pipe clip", "screwed through the lining"), ("*wall*", "*foot", "the wall's foot board"),
    ("plank", "*", "things standing on the deck are set into the planks' tops by their own weight (less than CLIP_MM)"),
]


def _allowed(la, lb):
    for pa, pb, _why in SET_INTO:
        if (fnmatch.fnmatch(la, pa) and fnmatch.fnmatch(lb, pb)) or (fnmatch.fnmatch(lb, pa) and fnmatch.fnmatch(la, pb)):
            return True
    return False


class _Rec:
    pass


_recs = []
for b in [boat, wheel, pump_wheel] + outriggers:
    for pi, (label, f0, f1) in enumerate(b.parts):
        tris = b.tris[f0:f1]
        if not tris:
            continue
        used = sorted({i for tri in tris for i in tri})
        rm = {v: k for k, v in enumerate(used)}
        r = _Rec()
        r.name = "%s/%s#%d" % (b.name, label, pi)
        r.label = label
        r.pts = [b.verts[i] for i in used]
        r.polys = [(rm[a], rm[c2], rm[c3]) for a, c2, c3 in tris]
        r.lo = Vector((min(p.x for p in r.pts), min(p.y for p in r.pts), min(p.z for p in r.pts)))
        r.hi = Vector((max(p.x for p in r.pts), max(p.y for p in r.pts), max(p.z for p in r.pts)))
        r.tree = BVHTree.FromPolygons(r.pts, r.polys, epsilon=0.0)
        r.ends = b.ends.get(pi)
        r.touch = set()
        _recs.append(r)
_RAY = Vector((0.3117, 0.5371, 0.7838)).normalized()


def _inside(r, p):
    hits = 0
    at = p.copy()
    while hits < 80:
        h = r.tree.ray_cast(at, _RAY)
        if h[0] is None:
            break
        hits += 1
        at = h[0] + _RAY * 1e-5
    return hits % 2 == 1


def _in_box(r, p, pad):
    return all(r.lo[k] - pad <= p[k] <= r.hi[k] + pad for k in range(3))


def _depth(ra, rb):
    deep = 0.0
    for p in ra.pts:
        if _in_box(rb, p, 0.0) and _inside(rb, p):
            hit = rb.tree.find_nearest(p)
            if hit[0] is not None:
                deep = max(deep, hit[3])
    return deep


def _near(ra, rb, dist):
    for p in ra.pts:
        if _in_box(rb, p, dist):
            hit = rb.tree.find_nearest(p, dist)
            if hit[0] is not None:
                return True
    return False


order = sorted(range(len(_recs)), key=lambda i: _recs[i].lo.x)
clips = {}
zfights = []
n_cand = n_cross = n_set = 0
PAD = 0.006
for oi, i in enumerate(order):
    ri = _recs[i]
    for j in order[oi + 1:]:
        rj = _recs[j]
        if rj.lo.x > ri.hi.x + PAD:
            break
        if (rj.lo.y > ri.hi.y + PAD or ri.lo.y > rj.hi.y + PAD or rj.lo.z > ri.hi.z + PAD or ri.lo.z > rj.hi.z + PAD):
            continue
        n_cand += 1
        ov = ri.tree.overlap(rj.tree)
        if ov:
            n_cross += 1
            ri.touch.add(j)
            rj.touch.add(i)
            deep = max(_depth(ri, rj), _depth(rj, ri))
            # coincident faces: triangles that cross while lying in one plane
            for a, c in ov[:400]:
                pa = [ri.pts[k] for k in ri.polys[a]]
                pc = [rj.pts[k] for k in rj.polys[c]]
                na = (pa[1] - pa[0]).cross(pa[2] - pa[0])
                nc = (pc[1] - pc[0]).cross(pc[2] - pc[0])
                if na.length < 1e-9 or nc.length < 1e-9:
                    continue
                na.normalize()
                nc.normalize()
                # only faces turned the same way fight; opposite faces pressed together are hidden
                if na.dot(nc) > 0.9999 and all(abs((q - pa[0]).dot(na)) < 2e-4 for q in pc):
                    zfights.append((ri.name, rj.name))
                    break
            if deep * 1000 > CLIP_MM:
                if _allowed(ri.label, rj.label):
                    n_set += 1
                else:
                    key = tuple(sorted((ri.label, rj.label)))
                    worst = clips.get(key, (0, 0.0, ""))
                    clips[key] = (worst[0] + 1, max(worst[1], deep), worst[2] or "%s x %s" % (ri.name, rj.name))
        elif _near(ri, rj, PAD) or _near(rj, ri, PAD):
            ri.touch.add(j)
            rj.touch.add(i)
print("CLIP CHECK: %d parts, %d pairs with touching boxes, %d pairs whose faces cross, %d of them set in on purpose "
      "deeper than %.0f mm" % (len(_recs), n_cand, n_cross, n_set, CLIP_MM))
for key, (n, deep, eg) in sorted(clips.items(), key=lambda kv: -kv[1][1]):
    print("   CLIP %s x %s: %d pair(s), up to %.1f mm deep (e.g. %s)" % (key[0], key[1], n, deep * 1000, eg))
print("CLIP pairs not meant: %d" % sum(v[0] for v in clips.values()))
print("ZFIGHT coincident faces: %d" % len(zfights))
for a, c in zfights[:20]:
    print("   ZFIGHT %s x %s" % (a, c))
floating = [r.name for r in _recs if not r.touch]
print("FLOATING (touching nothing): %d" % len(floating))
for nme in floating[:30]:
    print("   FLOAT %s" % nme)
# joined to the hull through what touches what
hull_i = [i for i, r in enumerate(_recs) if r.label == "hull"]
seen = set(hull_i)
stack_ = list(hull_i)
while stack_:
    i = stack_.pop()
    for j in _recs[i].touch:
        if j not in seen:
            seen.add(j)
            stack_.append(j)
loose = [r.name for i, r in enumerate(_recs) if i not in seen and r.touch]
print("NOT JOINED TO THE HULL: %d" % len(loose))
for nme in loose[:30]:
    print("   LOOSE %s" % nme)
dangling = []
for i, r in enumerate(_recs):
    if not r.ends or not (r.label.startswith("line") or r.label in ("ring lanyard", "tyre rope", "door hook")):
        continue
    for e in r.ends:
        ok = False
        for j, q in enumerate(_recs):
            if j == i or not _in_box(q, e, 0.03):
                continue
            hit = q.tree.find_nearest(e, 0.03)
            if hit[0] is not None:
                ok = True
                break
        if not ok:
            dangling.append("%s end at (%.2f, %.2f, %.2f)" % (r.name, e.x, e.y, e.z))
print("LINE ENDS made fast to nothing: %d" % len(dangling))
for dd in dangling[:30]:
    print("   DANGLE %s" % dd)

objects = [b.make() for b in [boat, wheel, pump_wheel] + outriggers]


def marker(name, at, turn_deg=0.0):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = "ARROWS"
    e.empty_display_size = 0.4
    e.location = at
    e.rotation_euler = (0.0, 0.0, math.radians(turn_deg))
    bpy.context.scene.collection.objects.link(e)
    print("MARKER %s: blender (%.3f, %.3f, %.3f), godot (%.3f, %.3f, %.3f), turned %d deg"
          % (name, at[0], at[1], at[2], at[0], at[2], -at[1], turn_deg))


# Godot's -Z (Blender +Y, the bow) is the way an unturned marker faces; -90 turns it to face starboard (+X),
# 90 to face port, 180 to face aft.
WALL_X = -CB_X + WT                    # the inside face of the cabin's port wall
CY = (CB_Y0 + CB_Y1) / 2               # the middle of the wall's length
CONSOLE = (WALL_X, CY, deck_top(CY))
marker("ConsoleSpot", CONSOLE, -90)
CONSOLE_DEEP = 0.6                     # the console bench's depth out from the wall (the main session's size)
marker("BoySpot", (WALL_X + CONSOLE_DEEP + 0.62, CY, deck_top(CY)), 90)   # where he sits on his stool
marker("HelmetCable", (WALL_X, CY, deck_top(CY) + 1.3), -90)
marker("MonitorSpot", (WALL_X, CY, deck_top(CY) + 1.75), -90)
marker("CaptainSpot", tuple(CAPTAIN), 0)       # at the wheel, facing the bow
marker("DiverSpot", tuple(DIVER), 180)         # at the pump, facing aft
stem_wl = station(1.0)[0][17]                  # the stem's point on the waterline
marker("BowWave", (0.0, stem_wl[1], 0.0), 180)
marker("Wake", (0.0, -HALF, 0.0), 180)
marker("Waterline", (0.0, 0.0, 0.0), 0)
print("HOSE END (not a marker): blender (%.3f, %.3f, %.3f)" % tuple(HOSE_END))

lo = Vector((1e9, 1e9, 1e9))
hi = Vector((-1e9, -1e9, -1e9))
for b in [boat, wheel, pump_wheel] + outriggers:
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
