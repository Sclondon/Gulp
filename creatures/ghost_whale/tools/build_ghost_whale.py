"""Builds the ghost whale (creatures/ghost_whale) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/ghost_whale/tools/build_ghost_whale.py
    blender --background --python creatures/ghost_whale/tools/build_ghost_whale.py -- <preview folder>   # with pictures

Writes creatures/ghost_whale/models/ghost_whale.glb (the full model, for close pictures), ghost_whale_lo.glb (far
off) and ghost_whale_game.glb (the game model: its bones at Twilight Princess weight, plus the mist), and the
editable creatures/ghost_whale/tools/ghost_whale.blend (this folder has a .gdignore). Each model is one still mesh
with one surface, drawn by creatures/ghost_whale/ghost.gdshader (additive glow, no lights), which swims it, opens
its jaws and fades it in and out. It prints a WINDING line for each model (the check that nothing is inside out).

A whale's skeleton swimming (a baleen whale's, after a humpback's: Claude's design from the concept sheet's fourth
panel, nothing traced), 14 m from the tip of its snout to the notch of its flukes, wreathed in a pale glowing mist
in the shape of the body it lost:

- THE SKULL: a long flat rostrum, a domed braincase with a wing of bone over each eye socket, and the two long
  bowed lower jawbones, hinged at the back of the skull (`gape` drops them).
- THE SPINE: seven short neck vertebrae, fourteen with ribs, ten lumbar ones with wide side processes, and the
  tail's, smaller and smaller to the flukes, chevrons under the first of them; every vertebra a round body with a
  spine standing up from it.
- THE RIBS: fourteen pairs, curving out and down round where the chest was.
- THE FLIPPERS: a fan of a shoulder blade, the arm bones and four long fingers of little bones, as a humpback's.
- THE MIST: two soft shells of the whale's outline, one inside the other, and its flippers and flukes as blades of
  mist (there are no bones in a whale's flukes): the shader makes them a pale haze that wavers and trails.

Everything here is in Godot space (metres, Y up, its nose at -Z) until it is written out; the origin is on its
middle line, half way along (7 m behind the tip of its snout). `xm` below is metres behind that tip.

What a point is, for the shader: UV2.y the part (0 a bone, 1 a lower jawbone, 2 the mist's shells, 3 a flipper's
bone, 4 the mist's flippers and flukes); UV2.x: on the mist, how far out the shell is (0 the inner, 1 the outer;
on the blades 0.5); on a flipper's bone, which side it is on (0 its left, +X; 1 its right). UV.x how far along the
whale (0 the tip of the snout, 1 the notch of the flukes); UV.y on a bone, how far along that bone (0 its root to 1
its end); on the mist, how far round (0 the ridge of the back, 1 the keel of the belly) or across a blade.
(The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.)

The numbers marked "as the shader has it" are in ghost.gdshader (as GhostWhale sets them) too.
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "models")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = ARGS[0] if ARGS else ""

NAME = "ghost_whale"
LENGTH = 14.0
HALF = 7.0
BONE, JAWBONE, MIST, FLIPPER_BONE, MIST_BLADE = range(5)
TAU = math.tau
PI = math.pi

# The body it lost (the mist's outline): metres behind the tip, the height of the ridge of the back, of the keel
# of the belly, half the width.
PROFILE = [
    (0.0, 0.05, -0.2, 0.15),
    (0.6, 0.32, -0.5, 0.55),
    (1.5, 0.55, -0.85, 0.88),
    (2.8, 0.82, -1.25, 1.16),
    (4.0, 1.02, -1.48, 1.35),
    (5.5, 1.15, -1.52, 1.45),
    (7.0, 1.12, -1.3, 1.3),
    (8.5, 0.95, -0.9, 0.95),
    (10.0, 0.66, -0.56, 0.56),
    (11.5, 0.43, -0.36, 0.3),
    (12.6, 0.29, -0.26, 0.18),
    (13.4, 0.17, -0.16, 0.12),
    (14.0, 0.06, -0.06, 0.05),
]

# The skeleton, as the shader has it where it says so: the hinge of the jaw (metres behind the tip, metres up,
# how far out to each side), the spine's sections (from, to, how many vertebrae), the root of a flipper.
JAW_HINGE = (3.55, -0.3, 0.86)
SPINE = [("neck", 3.85, 4.45, 7), ("chest", 4.45, 7.7, 14), ("loins", 7.7, 10.1, 10), ("tail", 10.1, 13.55, 18)]
FLIPPER_ROOT = (4.35, -0.75, 1.0)
FLUKE_AT = 13.1


def to_b(p):
    return Vector((p.x, -p.z, p.y))


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def _slopes(xs, ys):
    """Tangents for a curve through the points that never overshoots them (Fritsch and Carlson)."""
    d = [(ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]) for i in range(len(xs) - 1)]
    m = [d[0]]
    for i in range(1, len(xs) - 1):
        if d[i - 1] * d[i] <= 0.0:
            m.append(0.0)
        else:
            w1 = 2.0 * (xs[i + 1] - xs[i]) + (xs[i] - xs[i - 1])
            w2 = (xs[i + 1] - xs[i]) + 2.0 * (xs[i] - xs[i - 1])
            m.append((w1 + w2) / (w1 / d[i - 1] + w2 / d[i]))
    m.append(d[-1])
    return m


def curve(points):
    xs = [p[0] for p in points]
    cols = []
    for c in range(1, len(points[0])):
        ys = [p[c] for p in points]
        cols.append((ys, _slopes(xs, ys)))

    def at(x):
        x = max(xs[0], min(xs[-1], x))
        i = 0
        while i < len(xs) - 2 and x > xs[i + 1]:
            i += 1
        h = xs[i + 1] - xs[i]
        t = (x - xs[i]) / h
        out = []
        for ys, m in cols:
            a = (2 * t ** 3 - 3 * t ** 2 + 1) * ys[i] + (t ** 3 - 2 * t ** 2 + t) * h * m[i]
            b = (-2 * t ** 3 + 3 * t ** 2) * ys[i + 1] + (t ** 3 - t ** 2) * h * m[i + 1]
            out.append(a + b)
        return out
    return at


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.data = []
        self.out = []
        self.count = {}

    def add(self, p, uv, part, extra=0.0):
        self.verts.append(p)
        self.data.append(((uv[0], 1.0 - uv[1]), (extra, 1.0 - part)))
        return len(self.verts) - 1

    def face(self, points, out, name):
        """A face wound so that its front (the side its points go round anticlockwise) is towards `out`."""
        ps = [self.verts[i] for i in points]
        n = Vector((0.0, 0.0, 0.0))
        for i in range(len(ps)):
            n += ps[i].cross(ps[(i + 1) % len(ps)])
        if n.length < 1e-13:
            return
        if n.dot(out) < 0.0:
            points = tuple(reversed(points))
        self.faces.append(tuple(points))
        self.out.append((Vector(out), name))
        self.count[name] = self.count.get(name, 0) + 1


def blade(m, part, name, point, place, facing, thick, nt, nu, extra=0.0, uv=None, tgather=1.0):
    """A thin closed blade. `point(t, u)` is a place in its own flat, `place` puts that in the model, `facing`
    is the way one of its two skins faces. `thick` at its root (t 0), a foil across (nothing at u 0 or 1),
    thinning to nothing at t 1."""
    for side in (1.0, -1.0):
        grid = []
        for ti in range(nt + 1):
            t = 1.0 - (1.0 - ti / nt) ** tgather
            row = []
            for ui in range(nu + 1):
                u = ui / nu
                foil = 2.6 * math.sqrt(u) * (1.0 - u)
                swell = thick * (1.0 - t) ** 0.7 * foil
                p = place(point(t, u)) + facing * (side * swell * 0.5)
                row.append(m.add(p, uv(t, u) if uv else (t, u), part, extra(p) if callable(extra) else extra))
            grid.append(row)
        for ti in range(nt):
            for ui in range(nu):
                m.face((grid[ti][ui], grid[ti][ui + 1], grid[ti + 1][ui + 1], grid[ti + 1][ui]), facing * side, name)


def along_of(points):
    """Distances from the first point along a chain of points."""
    out = [0.0]
    for i in range(1, len(points)):
        out.append(out[-1] + (points[i] - points[i - 1]).length)
    return out


def winding(name, mesh, m):
    """Nothing inside out: every face's normal on the side it was meant to face."""
    bad = {}
    for poly in mesh.polygons:
        out, group = m.out[poly.index]
        if poly.normal.dot(to_b(out)) <= 0.0:
            bad[group] = bad.get(group, 0) + 1
    told = ["%s %d/%d wrong" % (group, bad.get(group, 0), count) for group, count in m.count.items()]
    print("WINDING %s: %s: %s" % (name, "ok" if not bad else "INSIDE OUT", ", ".join(told)))


def export_one(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", export_yup=True, use_selection=True,
        export_animations=False, export_texcoords=True,
    )


_OUTLINE = curve(PROFILE)
_SPINE_Y = curve([(3.85, 0.2), (6.0, 0.45), (9.0, 0.36), (11.5, 0.12), (13.6, 0.0)])
_CENTRUM = curve([(3.85, 0.19), (6.0, 0.24), (9.0, 0.21), (11.0, 0.14), (13.6, 0.055)])
# The skull: metres behind the tip, the height of its middle, half its thickness, half its width.
_SKULL = curve([(0.05, -0.12, 0.05, 0.07), (0.6, -0.09, 0.09, 0.25), (1.4, -0.05, 0.13, 0.43),
                (2.3, 0.0, 0.18, 0.6), (2.9, 0.06, 0.26, 0.72), (3.25, 0.16, 0.42, 0.8), (3.6, 0.22, 0.48, 0.74),
                (3.95, 0.2, 0.34, 0.44)])


def outline(xm):
    out = _OUTLINE(xm)
    return out[0], out[1], max(out[2], 0.001)


# How fine each model is: (sides of a vertebra, of a rib, segments of a rib, sides of the skull, its rings,
# sides of the mist, its rings, a flipper's bones' sides).
DETAIL = {"full": (10, 6, 14, 12, 30, 24, 60, 8), "game": (5, 3, 6, 6, 10, 12, 24, 4),
          "low": (3, 3, 3, 4, 6, 8, 14, 3)}


def bone(m, part, points, radii, sides, extra=0.0, flat=1.0, up=None, name="bones", caps=True):
    """A closed bone through `points` (each with its radius); `flat` squashes its section across `up`. UV.x is
    how far along the whale each point is, UV.y how far along the bone."""
    alongs = along_of(points)
    total = max(alongs[-1], 1e-6)
    rows = []
    for i, p in enumerate(points):
        if i == 0:
            axis = points[1] - points[0]
        elif i == len(points) - 1:
            axis = points[-1] - points[-2]
        else:
            axis = points[i + 1] - points[i - 1]
        axis.normalize()
        ref = up if up is not None else Vector((0.0, 1.0, 0.0))
        side = axis.cross(ref)
        if side.length < 1e-4:
            side = axis.cross(Vector((1.0, 0.0, 0.0)))
        side.normalize()
        other = side.cross(axis).normalized()
        row = []
        for s in range(sides):
            a = s / sides * TAU + PI / sides
            q = p + (side * math.cos(a) + other * math.sin(a) * flat) * radii[i]
            row.append(m.add(q, ((q.z + HALF) / LENGTH, alongs[i] / total), part, extra))
        rows.append((row, p))
    for i in range(len(rows) - 1):
        a, pa = rows[i]
        b, pb = rows[i + 1]
        axis = (pb - pa).normalized()
        for s in range(sides):
            n = (s + 1) % sides
            quad = (a[s], a[n], b[n], b[s])
            at = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, at - (pa + axis * (at - pa).dot(axis)), name)
    if caps:
        for end, way in ((0, points[0] - points[1]), (-1, points[-1] - points[-2])):
            row, p = rows[end]
            if sides <= 4:
                m.face(tuple(row), way, name)
            else:
                tip = m.add(p + way.normalized() * radii[end] * 0.3, ((p.z + HALF) / LENGTH, 0.0 if end == 0 else 1.0), part, extra)
                for s in range(len(row)):
                    m.face((tip, row[s], row[(s + 1) % len(row)]), way, name)


def W(xm, y, x):
    return Vector((x, y, xm - HALF))


def skull(m, detail):
    sides, rings = detail[3], detail[4]
    pts = []
    rad = []
    rows = []
    for i in range(rings + 1):
        xm = 0.05 + (3.95 - 0.05) * (i / rings) ** 0.9
        yc, thick, wide = _SKULL(xm)
        row = []
        for s in range(sides):
            a = s / sides * TAU + PI / sides
            # (a flattened round: the rostrum a flat blade, the braincase a dome)
            p = W(xm, yc + math.cos(a) * thick, math.sin(a) * wide)
            row.append(m.add(p, (xm / LENGTH, i / rings), BONE))
        rows.append((row, W(xm, yc, 0.0)))
    for i in range(rings):
        a, pa = rows[i]
        b, pb = rows[i + 1]
        for s in range(sides):
            n = (s + 1) % sides
            quad = (a[s], a[n], b[n], b[s])
            at = sum((m.verts[q] for q in quad), Vector()) * 0.25
            mid = pa + (pb - pa) * 0.5
            m.face(quad, Vector((at.x, at.y - mid.y, 0.0)), "skull")
    for end, way in ((0, -1.0), (-1, 1.0)):
        row, p = rows[end]
        tip = m.add(p + Vector((0.0, 0.0, way * 0.04)), (p.z / LENGTH + 0.5, 0.0), BONE)
        for s in range(sides):
            m.face((tip, row[s], row[(s + 1) % sides]), Vector((0.0, 0.0, way)), "skull")
    # The wings of bone over the eye sockets, and the bony ridge down the middle of the rostrum.
    for sx in (1.0, -1.0):
        def point(t, u, sx=sx):
            xm = 3.0 + 0.7 * u - 0.15 * t * (u - 0.5)
            return Vector((sx * (0.6 + 0.62 * t * (1.0 - 0.25 * abs(2.0 * u - 1.0) ** 2)), 0.16 - 0.1 * t, xm - HALF))
        blade(m, BONE, "skull", point, lambda p: p, Vector((0.0, 1.0, 0.0)), 0.08, 2 if sides < 8 else 6,
              3 if sides < 8 else 8, uv=lambda t, u: (3.3 / LENGTH, t))
    ridge = [W(0.3, -0.05, 0.0), W(1.6, 0.06, 0.0), W(2.9, 0.22, 0.0)]
    bone(m, BONE, ridge, [0.03, 0.05, 0.07], max(3, sides // 2), name="skull")


def jaws(m, detail):
    sides = detail[0] + 1 if detail[0] < 8 else detail[0]
    segs = detail[4]
    for sx in (1.0, -1.0):
        pts = []
        radii = []
        for i in range(segs + 1):
            t = i / segs
            x = 0.1 + (JAW_HINGE[2] - 0.1) * t + 0.36 * math.sin(PI * t ** 0.85)
            y = -0.28 - 0.1 * math.sin(PI * t) + (JAW_HINGE[1] + 0.28) * t
            xm = 0.08 + (JAW_HINGE[0] - 0.08) * t
            pts.append(W(xm, y, sx * x))
            radii.append(0.05 + 0.08 * math.sin(PI * min(1.0, t * 1.4) * 0.5) + 0.04 * smooth(0.8, 1.0, t))
        bone(m, JAWBONE, pts, radii, sides, flat=1.4, name="jawbones")


def vertebrae(m, detail):
    sides = detail[0]
    count = 0
    for name, a, b, n in SPINE:
        if detail[0] <= 3 and name == "neck":
            n = 3
        pitch = (b - a) / n
        for i in range(n):
            x0 = a + pitch * i
            x1 = x0 + pitch * (0.78 if name != "neck" else 0.6)
            xc = 0.5 * (x0 + x1)
            y = _SPINE_Y(xc)[0]
            r = _CENTRUM(xc)[0]
            bone(m, BONE, [W(x0, y, 0.0), W(x1, y, 0.0)], [r, r], sides, name="vertebrae")
            count += 1
            # the spine standing up from it, leaning back
            if name != "neck":
                h = {"chest": 0.55, "loins": 0.5, "tail": 0.42}[name] * (1.0 - 0.75 * smooth(10.5, 13.4, xc))
                top = W(xc + 0.18 * h, y + r + h, 0.0)
                bone(m, BONE, [W(xc - 0.02, y + r * 0.6, 0.0), top], [r * 0.45, r * 0.22], 4, flat=0.35,
                     up=Vector((1.0, 0.0, 0.0)), name="vertebrae")
            # the loins' wide processes to each side
            if name == "loins" and detail[0] > 3:
                for sx in (1.0, -1.0):
                    bone(m, BONE, [W(xc, y, sx * r * 0.8), W(xc + 0.05, y - 0.05, sx * (r + 0.42))], [r * 0.35, r * 0.15],
                         4, flat=0.4, name="vertebrae")
            # the chevrons under the first of the tail's
            if name == "tail" and i < 11 and detail[0] > 3:
                d = 0.32 * (1.0 - i / 13.0)
                for sx in (1.0, -1.0):
                    bone(m, BONE, [W(xc, y - r * 0.8, sx * r * 0.45), W(xc + 0.1, y - r - d, sx * 0.02)],
                         [r * 0.25, r * 0.15], 4, name="vertebrae")
    return count


def ribs(m, detail):
    sides, segs = detail[1], detail[2]
    a, b, n = SPINE[1][1], SPINE[1][2], SPINE[1][3]
    pitch = (b - a) / n
    for i in range(n):
        xm = a + pitch * (i + 0.4)
        y0 = _SPINE_Y(xm)[0]
        r = _CENTRUM(xm)[0]
        # (the first and the last pairs are short; the middle ones reach round to the belly)
        reach = 0.55 + 0.27 * math.sin(PI * min(1.0, (i + 1.5) / (n * 0.8)))
        if i >= n - 3:
            reach *= 0.75
        for sx in (1.0, -1.0):
            pts = []
            radii = []
            for k in range(segs + 1):
                t = k / segs
                ang = 0.12 * PI + reach * PI * t
                xt = xm + 0.4 * t * t
                up, down, wide = outline(xt)
                yc = 0.5 * (up + down) - 0.05
                hh = 0.5 * (up - down)
                q = 0.84 * (1.0 - 0.05 * t)
                pts.append(W(xt, min(y0, yc + math.cos(ang) * hh * q) if k == 0 else yc + math.cos(ang) * hh * q,
                             sx * (r + 0.05 if k == 0 else max(r + 0.05, math.sin(ang) * wide * q))))
                radii.append(0.075 - 0.035 * t)
            bone(m, BONE, pts, radii, sides, flat=0.7, up=Vector((0.0, 0.0, 1.0)), name="ribs")


def flipper(m, sx, detail):
    sides = detail[7]
    side = 0.0 if sx > 0 else 1.0
    root = W(FLIPPER_ROOT[0], FLIPPER_ROOT[1], sx * FLIPPER_ROOT[2])
    out = Vector((sx * 0.78, -0.42, 0.46)).normalized()
    chord = out.cross(Vector((0.0, 1.0, 0.0))).normalized()
    if chord.z < 0.0:
        chord = -chord
    flat = out.cross(chord).normalized()
    # The shoulder blade: a fan of bone against the ribs, above the root.
    def fan(t, u):
        return root + Vector((0.0, 1.0, 0.0)) * (0.85 * t) + Vector((0.0, 0.0, 1.0)) * ((u - 0.5) * (0.22 + 0.45 * t))
    blade(m, FLIPPER_BONE, "flippers", fan, lambda p: p + Vector((sx * -0.05, 0.0, 0.0)), Vector((sx, 0.0, 0.0)),
          0.07, 2 if sides < 6 else 5, 3 if sides < 6 else 8, extra=side, uv=lambda t, u: (FLIPPER_ROOT[0] / LENGTH, t))
    elbow = root + out * 0.6
    bone(m, FLIPPER_BONE, [root, elbow], [0.16, 0.12], sides + 1, extra=side, name="flippers")
    wrist = elbow + out * 0.85
    for d in (-0.09, 0.09):
        bone(m, FLIPPER_BONE, [elbow + chord * d, wrist + chord * d * 1.3], [0.07, 0.06], sides, extra=side, name="flippers")
    bone(m, FLIPPER_BONE, [wrist - chord * 0.18, wrist + chord * 0.2], [0.08, 0.08], sides, extra=side, flat=0.6, name="flippers")
    # Four long fingers of little bones, fanning a little, the leading one the longest.
    for f, (d, long, count) in enumerate(((-0.17, 2.55, 6), (-0.05, 2.3, 6), (0.07, 1.9, 5), (0.19, 1.25, 4))):
        way = (out + chord * (0.05 * f)).normalized()
        start = wrist + chord * d + way * 0.08
        pitch = long / count
        for k in range(count):
            a = start + way * (pitch * k)
            b = a + way * (pitch * 0.8)
            r = 0.055 * (1.0 - 0.6 * k / count) * (1.0 - 0.12 * f)
            bone(m, FLIPPER_BONE, [a, b], [r, r * 0.85], sides, extra=side, name="flippers")


def mist(m, detail):
    """The mist: two shells of the body's outline, one inside the other, and blades of mist for the flippers
    and the flukes."""
    sides, rings = detail[5], detail[6]
    for k, (grow, add) in enumerate(((1.0, 0.0), (1.12, 0.14))):
        rows = []
        for i in range(rings + 1):
            xm = 0.0 + 14.0 * (i / rings)
            up, down, wide = outline(xm)
            yc = 0.5 * (up + down)
            hh = 0.5 * (up - down) * grow + add
            ww = wide * grow + add
            row = []
            for s in range(sides):
                ang = s / sides * TAU
                p = W(xm, yc + math.cos(ang) * hh, math.sin(ang) * ww)
                row.append(m.add(p, (xm / LENGTH, abs(ang - PI) / PI), MIST, float(k)))
            rows.append((row, yc))
        for i in range(rings):
            a, ya = rows[i]
            b = rows[i + 1][0]
            for s in range(sides):
                n = (s + 1) % sides
                quad = (a[s], a[n], b[n], b[s])
                at = sum((m.verts[q] for q in quad), Vector()) * 0.25
                m.face(quad, Vector((at.x, at.y - ya, 0.0)), "mist")
        for end, way in ((0, -1.0), (-1, 1.0)):
            row, yc = rows[end]
            xm = 0.0 if end == 0 else 14.0
            tip = m.add(W(xm + way * (0.05 + add), yc, 0.0), (xm / LENGTH, 0.5), MIST, float(k))
            for s in range(sides):
                m.face((tip, row[s], row[(s + 1) % sides]), Vector((0.0, 0.0, way)), "mist")
    nt, nu = (3, 3) if sides < 16 else (8, 8)
    # the flippers' mist, along their bones
    for sx in (1.0, -1.0):
        root = W(FLIPPER_ROOT[0], FLIPPER_ROOT[1], sx * FLIPPER_ROOT[2])
        out = Vector((sx * 0.78, -0.42, 0.46)).normalized()
        chord = out.cross(Vector((0.0, 1.0, 0.0))).normalized()
        if chord.z < 0.0:
            chord = -chord
        facing = out.cross(chord).normalized()
        if facing.y < 0.0:
            facing = -facing

        def point(t, u, root=root, out=out, chord=chord):
            wide = 0.95 * (1.0 - t ** 2.5) ** 0.6 + 0.08
            return root + out * (4.3 * t * 0.985) + chord * ((u - 0.35) * wide)
        blade(m, MIST_BLADE, "mist", point, lambda p: p, facing, 0.25, nt, nu, extra=0.5,
              uv=lambda t, u: (FLIPPER_ROOT[0] / LENGTH, u))
    # the flukes, flat, out to each side and back
    for sx in (1.0, -1.0):
        def point(t, u, sx=sx):
            lead = FLUKE_AT + 0.25 * t + 0.55 * t * t
            trail = 14.0 + 0.05 * t + 0.35 * t * t
            xm = lead + (trail - lead) * u
            return W(xm, 0.0 - 0.05 * t, sx * (0.1 + 2.25 * t * 0.985))
        blade(m, MIST_BLADE, "mist", point, lambda p: p, Vector((0.0, 1.0, 0.0)), 0.2, nt + 1, nu,
              extra=0.5, uv=lambda t, u: (FLUKE_AT / LENGTH, u))


def make(name, detail):
    m = Mesh()
    skull(m, detail)
    jaws(m, detail)
    count = vertebrae(m, detail)
    ribs(m, detail)
    for sx in (1.0, -1.0):
        flipper(m, sx, detail)
    bones_end = len(m.faces)
    mist(m, detail)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) for p in m.verts], [], m.faces)
    mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.new(name="UV2")
    uv = mesh.uv_layers["UVMap"].data
    uv2 = mesh.uv_layers["UV2"].data
    for poly in mesh.polygons:
        for corner, vi in enumerate(poly.vertices):
            d = m.data[vi]
            uv[poly.loop_start + corner].uv = d[0]
            uv2[poly.loop_start + corner].uv = d[1]
    material = bpy.data.materials.get(NAME) or bpy.data.materials.new(NAME)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.75, 0.88, 1.0, 1.0)
    material.diffuse_color = (0.75, 0.88, 1.0, 1.0)
    mesh.materials.append(material)
    mesh.update()
    winding(name, mesh, m)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bm.to_mesh(mesh)
    bm.free()
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.set_sharp_from_angle(angle=math.radians(60.0))
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    bone_tris = sum(len(p.vertices) - 2 for p in mesh.polygons if p.index < bones_end)
    print("BUILT %s verts=%d tris=%d (bones %d, mist %d; %d vertebrae)" % (name, len(mesh.vertices), tris, bone_tris, tris - bone_tris, count))
    return obj


def render(folder, made):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_cavity = True
    # (see-through, so that the bones show inside the mist)
    scene.display.shading.show_xray = True
    scene.display.shading.xray_alpha = 0.35
    scene.display.shading.show_backface_culling = True
    scene.render.resolution_x, scene.render.resolution_y = 1400, 800
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    f = LENGTH
    views = [("left", (1, 0, 0), (0, 0, 0), 1.15 * f), ("front", (0, 1, 0), (0, 0, 0), 0.5 * f),
             ("top", (0.001, 0, 1), (0, 0, 0), 1.15 * f), ("quarter", (0.7, 0.5, 0.4), (0, 0, 0), 1.0 * f),
             ("head", (0.8, 0.5, 0.3), (0, HALF - 2.0, 0), 5.0)]
    for prefix, obj in zip(("", "lo_", "game_"), made):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            offset = Vector(direction).normalized() * 100.0
            camera.data.ortho_scale = frame
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % (prefix, view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    full = make(NAME, DETAIL["full"])
    low = make(NAME + "_lo", DETAIL["low"])
    game = make(NAME + "_game", DETAIL["game"])
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, NAME + ".glb"))
    export_one(low, os.path.join(OUT, NAME + "_lo.glb"))
    export_one(game, os.path.join(OUT, NAME + "_game.glb"))
    low.location.x = 6.0
    game.location.x = -6.0
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, NAME + ".blend"))
    low.location.x = 0.0
    game.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low, game])


if __name__ == "__main__":
    main()
