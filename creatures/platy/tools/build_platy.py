"""Builds the platy (creatures/platy) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/platy/tools/build_platy.py
    blender --background --python creatures/platy/tools/build_platy.py -- <preview folder>   # with pictures

Writes creatures/platy/models/platy.glb (the full model) and platy_lo.glb (far off, phones, many at once), and
the editable tools/platy.blend (this folder has a .gdignore). Each is one still mesh with one surface: the shader
(platy.gdshader) draws every marking (sunset, red wagtail or blue mickey mouse: the same model) and swims it. It
prints a WINDING line for each (the check that nothing is inside out) and a NUMBERS line (what the shader has to
agree with).

A southern platy (Xiphophorus maculatus), 0.05 m from the tip of its snout to the edge of its tail, built from
what the fish looks like (no picture was traced or copied): a short deep body, flattened from side to side,
deepest (0.0178 m) under the front of the dorsal fin, with a deep root to its tail; a small upturned mouth, a big
eye; a rounded dorsal fin, a small anal fin, a broad rounded fan of a tail, small pectoral and pelvic fins. Its
LOWER JAW is a part of its own that swings down about its hinge (the shader's `gape`), with the inside of the
mouth behind it.

Everything here is in Godot space (metres, Y up, X to its left side, its nose at -Z) until it is written out;
the origin is on its middle line, half way along (0.025 m behind the tip of the snout). `xm` below is metres
behind the tip of the snout.

What a point is, for the shader: UV2.y the part (0 body, 1 the dorsal fin, 2 the anal fin, 3 the tail, 4 a
pectoral fin, 5 a pelvic fin, 6 an eye, 7 the lower jaw). UV2.x: 1 inside the mouth, 0 elsewhere. UV, on the
body and the jaw: x how far along (0 snout to 1 tail edge), y how high on its side (1 the ridge of the back, 0 the
keel of the belly); on a fin: x from its root (0) to its edge (1), y from its leading edge (0) to its trailing
edge (1); on an eye: x from its middle (0) to its rim (1). (The glTF writer flips V: what is written here is
1 - v, so that Godot reads v.)
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

LENGTH = 0.05
HALF = 0.025
BODY, DORSAL, ANAL, TAIL, PECTORAL, PELVIC, EYE, JAW = range(8)
TAU = math.tau
SIDE = Vector((1.0, 0.0, 0.0))


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def to_b(p):
    return Vector((p.x, -p.z, p.y))


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


class Curves:
    """Smooth curves through rows of (x, a, b, ...): `at(x)` is [a, b, ...] there."""

    def __init__(self, rows):
        self.xs = [r[0] for r in rows]
        self.curves = []
        for column in range(1, len(rows[0])):
            ys = [r[column] for r in rows]
            self.curves.append((ys, _slopes(self.xs, ys)))

    def at(self, x):
        xs = self.xs
        x = max(xs[0], min(xs[-1], x))
        i = 0
        while i < len(xs) - 2 and x > xs[i + 1]:
            i += 1
        h = xs[i + 1] - xs[i]
        t = (x - xs[i]) / h
        out = []
        for ys, m in self.curves:
            a = (2 * t ** 3 - 3 * t ** 2 + 1) * ys[i] + (t ** 3 - 2 * t ** 2 + t) * h * m[i]
            b = (-2 * t ** 3 + 3 * t ** 2) * ys[i + 1] + (t ** 3 - t ** 2) * h * m[i + 1]
            out.append(a + b)
        return out


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.data = []
        self.out = []
        self.count = {}

    def add(self, p, uv, part, inside=0.0):
        self.verts.append(p)
        self.data.append(((uv[0], 1.0 - uv[1]), (inside, 1.0 - part)))
        return len(self.verts) - 1

    def face(self, points, out, name):
        """A face wound so that its front (the side its points go round anticlockwise) is towards `out`."""
        ps = [self.verts[i] for i in points]
        n = Vector((0.0, 0.0, 0.0))
        for i in range(len(ps)):
            n += ps[i].cross(ps[(i + 1) % len(ps)])
        if n.length < 1e-14:
            return
        if n.dot(out) < 0.0:
            points = tuple(reversed(points))
        if len(points) == 4:
            # (a quad that is not flat is cut into two triangles along the diagonal that leaves both facing
            # the way it should: Godot draws triangles, and the wrong cut of a twisted quad turns one over)
            a, b, c, d = points
            v = self.verts

            def facing(p, q, r):
                return (v[q] - v[p]).cross(v[r] - v[p]).dot(out)

            if min(facing(a, b, c), facing(a, c, d)) < min(facing(a, b, d), facing(b, c, d)):
                tris = ((a, b, d), (b, c, d))
            else:
                tris = ((a, b, c), (a, c, d))
            for tri in tris:
                self.faces.append(tri)
                self.out.append((Vector(out), name))
            self.count[name] = self.count.get(name, 0) + 2
            return
        self.faces.append(tuple(points))
        self.out.append((Vector(out), name))
        self.count[name] = self.count.get(name, 0) + 1


def blade(m, part, name, point, place, facing, thick, nt, nu):
    """A fin: a thin closed blade. `point(t, u)` is a place in the fin's own flat (t 0 at its root to 1 at its
    edge, u 0 at its leading edge to 1 at its trailing edge), `place` puts that in the model, `facing` is
    roughly the way one of its two skins faces (each point's own way is worked out from its neighbours, so a
    fin may be curved). It is `thick` at its root, a foil across (nothing at either edge), thinning to nothing
    at its edge."""
    def at(t, u):
        return place(point(t, u))

    def way(t, u):
        e = 0.002
        a = at(min(t + e, 1.0), u) - at(max(t - e, 0.0), u)
        b = at(t, min(u + e, 1.0)) - at(t, max(u - e, 0.0))
        n = a.cross(b)
        if n.length < 1e-14:
            return Vector(facing)
        n.normalize()
        return n if n.dot(facing) >= 0.0 else -n

    for side in (1.0, -1.0):
        grid = []
        for ti in range(nt + 1):
            t = ti / nt
            row = []
            for ui in range(nu + 1):
                u = ui / nu
                foil = 2.6 * math.sqrt(u) * (1.0 - u)
                swell = thick * (1.0 - t) ** 0.7 * foil
                row.append(m.add(at(t, u) + way(t, u) * (side * swell * 0.5), (t, u), part))
            grid.append(row)
        for ti in range(nt):
            for ui in range(nu):
                out = way((ti + 0.5) / nt, (ui + 0.5) / nu) * side
                m.face((grid[ti][ui], grid[ti][ui + 1], grid[ti + 1][ui + 1], grid[ti + 1][ui]), out, name)


def between(root, edge):
    """A fin drawn from its root line to its edge (each a function of u, 0 to 1, giving (xm, y))."""
    def point(t, u):
        a = root(u)
        b = edge(u)
        return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
    return point


def through(points):
    """A smooth line through (u, xm, y) points (u rising): a function of u giving (xm, y)."""
    curve = Curves(points)
    return lambda u: tuple(curve.at(u))


def upright(p):
    """A place in the flat of the middle fins (metres behind the snout, metres up) in the model."""
    return Vector((0.0, p[1], p[0] - HALF))


def spread(sx, pivot, angle, gap):
    """A place in the flat of a middle fin turned out to one side (`sx`) about a line along the body at height
    `pivot` (a number, or a function of xm), by `angle` (a number, or a function of what the caller passes:
    t, or xm): what is below the line
    swings out, what is above it stays upright, `gap` to that side of the middle."""
    def place_at(p, t):
        y0 = pivot(p[0]) if callable(pivot) else pivot
        a = angle(t) if callable(angle) else angle
        # (how far below the line, eased in over a few millimetres so that the fin bends round smoothly)
        x = y0 - p[1]
        d = x * x / (x + 0.003) if x > 0.0 else 0.0
        return Vector((sx * (gap + math.sin(a) * d), p[1] + d * (1.0 - math.cos(a)), p[0] - HALF))
    return place_at


class Fish:
    """One model's shape. A kind sets PROFILE (xm, half depth above, half depth below, half width), BODY_TO,
    JAW_TO (the jaw's hinge), EYE_AT, EYE_RADIUS, RINGS, mouth_y, gill_x and fins."""

    LOW_STEP = 4.0

    def __init__(self, low):
        self.low = low
        self.outline_curves = Curves(self.PROFILE)

    def outline(self, xm):
        return [max(v, 0.0013 * LENGTH) for v in self.outline_curves.at(xm)]

    def mid(self, xm):
        return 0.0

    def section(self, xm, angle, up, down, wide):
        c = math.cos(angle)
        s = math.sin(angle)
        y = c * (up if c >= 0.0 else down)
        side = math.copysign(abs(s) ** 0.9, s) * wide
        return side, y

    def body_point(self, xm, angle):
        up, down, wide = self.outline(xm)
        side, y = self.section(xm, angle, up, down, wide)
        return Vector((side, self.mid(xm) + y, xm - HALF))

    def top(self, xm):
        return self.body_point(xm, 0.0).y

    def bottom(self, xm):
        return self.body_point(xm, math.pi).y

    def angle_at(self, xm, y):
        lo, hi = 0.0, math.pi
        for _ in range(40):
            half = 0.5 * (lo + hi)
            if self.body_point(xm, half).y > y:
                lo = half
            else:
                hi = half
        return 0.5 * (lo + hi)

    def skin(self, xm, y, sx):
        return self.body_point(xm, sx * self.angle_at(xm, y))

    def lip_angle(self, xm):
        return self.angle_at(xm, self.mouth_y(xm))

    def rings(self):
        xs = []
        x = self.BODY_FROM
        for until, step in self.RINGS:
            if self.low:
                step *= self.LOW_STEP
            n = max(1, round((until - x) / step))
            for i in range(n):
                xs.append(x + (until - x) * i / n)
            x = until
        xs.append(self.BODY_TO)
        return xs

    def around(self):
        return self.AROUND_LOW if self.low else self.AROUND

    def inside_point(self, xm, across, roof):
        """A point of the roof or the floor of the mouth at `xm`: `across` 1 at the left lip, -1 at the right,
        the surface arched away from the line of the mouth between them."""
        lip = self.body_point(xm, self.lip_angle(xm))
        up, down, _ = self.outline(xm)
        if roof:
            depth = 0.45 * (self.mid(xm) + up - lip.y)
        else:
            depth = -0.5 * (lip.y - (self.mid(xm) - down))
        y = lip.y + depth * (1.0 - across * across) * smooth(0.1 * self.JAW_TO, 0.5 * self.JAW_TO, xm)
        return Vector((lip.x * across, y, xm - HALF))

    # --- the body and the head above the mouth -----------------------------------------------------------

    def body(self, m):
        around = self.around()
        xs = self.rings()
        head = [xm for xm in xs if xm < self.JAW_TO - 1e-9]
        xs = xs[len(head):]
        grid = []
        for xm in xs:
            row = []
            for c in range(around):
                angle = c / around * TAU
                row.append(m.add(self.body_point(xm, angle), (xm / LENGTH, 0.5 + 0.5 * math.cos(angle)), BODY))
            grid.append(row)
        for r in range(len(grid) - 1):
            for c in range(around):
                n = (c + 1) % around
                quad = (grid[r][c], grid[r][n], grid[r + 1][n], grid[r + 1][c])
                middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
                m.face(quad, Vector((middle.x, middle.y - self.mid(middle.z + HALF), 0.0)), "body")
        end = self.BODY_TO + 0.0027 * LENGTH
        tip = m.add(Vector((0.0, self.mid(end), end - HALF)), (end / LENGTH, 0.5), BODY)
        for c in range(around):
            m.face((tip, grid[-1][c], grid[-1][(c + 1) % around]), Vector((0.0, 0.0, 1.0)), "body")
        half = round(self.lip_angle(self.JAW_TO) / (TAU / around))
        across = around - 2 * half
        uppers = []
        roofs = []
        for xm in head:
            reach = self.lip_angle(xm)
            uppers.append([m.add(self.body_point(xm, j / half * reach), (xm / LENGTH, 0.5 + 0.5 * math.cos(j / half * reach)), BODY)
                           for j in range(-half, half + 1)])
            roofs.append([m.add(self.inside_point(xm, 1.0 - 2.0 * k / across, True), (xm / LENGTH, 0.5), BODY,
                                smooth(self.BODY_FROM, 0.12 * self.JAW_TO, xm))
                          for k in range(across + 1)])
        first = grid[0]
        uppers.append([first[j % around] for j in range(-half, half + 1)])
        roofs.append([m.add(m.verts[first[(half + k) % around]], (self.JAW_TO / LENGTH, 0.5), BODY, 1.0) for k in range(across + 1)])
        for r in range(len(head)):
            centre = self.mouth_y(head[r]) - 0.1 * self.outline(head[r])[0]
            for j in range(2 * half):
                quad = (uppers[r][j], uppers[r][j + 1], uppers[r + 1][j + 1], uppers[r + 1][j])
                middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
                m.face(quad, Vector((middle.x, middle.y - centre, 0.0)), "body")
            for k in range(across):
                quad = (roofs[r][k], roofs[r][k + 1], roofs[r + 1][k + 1], roofs[r + 1][k])
                if r < len(head) - 1:
                    m.face(quad, Vector((0.0, -1.0, 0.0)), "mouth roof")
                else:
                    m.face(quad, Vector((0.0, -0.3, -1.0)), "throat")
        loop = uppers[0] + roofs[0][1:-1]
        middle = sum((m.verts[q] for q in loop), Vector()) / len(loop)
        tip = m.add(middle + Vector((0.0, 0.0, -0.002 * LENGTH)), (0.0, 0.5), BODY)
        for i in range(len(loop)):
            m.face((tip, loop[i], loop[(i + 1) % len(loop)]), Vector((0.0, 0.0, -1.0)), "body")

    def jaw(self, m):
        """The lower jaw: the body's own skin below the line of the mouth, ahead of the hinge, closed over by
        the floor of the mouth, with an end inside the head."""
        around = self.around()
        half = round(self.lip_angle(self.JAW_TO) / (TAU / around))
        under = around - 2 * half
        across = 4 if self.low else 10
        xs = [xm for xm in self.rings() if xm < self.JAW_TO + 1e-9]
        skins = []
        floors = []
        for xm in xs:
            reach = self.lip_angle(xm)
            row = []
            for i in range(under + 1):
                angle = reach + (TAU - 2.0 * reach) * i / under
                if xm > self.JAW_TO - 1e-9:
                    angle = (half + i) / around * TAU
                row.append(m.add(self.body_point(xm, angle), (xm / LENGTH, 0.5 + 0.5 * math.cos(angle)), JAW))
            skins.append(row)
            floors.append([m.add(self.inside_point(xm, 1.0 - 2.0 * k / across, False), (xm / LENGTH, 0.5), JAW,
                                 smooth(self.BODY_FROM, 0.12 * self.JAW_TO, xm))
                           for k in range(across + 1)])
        for r in range(len(xs) - 1):
            centre = 0.5 * (self.mouth_y(xs[r]) + self.bottom(xs[r]))
            for i in range(under):
                quad = (skins[r][i], skins[r][i + 1], skins[r + 1][i + 1], skins[r + 1][i])
                middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
                m.face(quad, Vector((middle.x, middle.y - centre, 0.0)), "jaw")
            for k in range(across):
                m.face((floors[r][k], floors[r][k + 1], floors[r + 1][k + 1], floors[r + 1][k]), Vector((0.0, 1.0, 0.0)), "mouth floor")
        for r, way, inside in ((0, -1.0, 0.0), (len(xs) - 1, 1.0, 1.0)):
            loop = skins[r] + floors[r][-2:0:-1]
            if r > 0:
                loop = [m.add(m.verts[q], (xs[r] / LENGTH, 0.5), JAW, 1.0) for q in loop]
            middle = sum((m.verts[q] for q in loop), Vector()) / len(loop)
            z = xs[r] - HALF + (-0.0013 * LENGTH if r == 0 else 0.0)
            tip = m.add(Vector((0.0, middle.y, z)), (xs[r] / LENGTH, 0.5), JAW, inside)
            for i in range(len(loop)):
                m.face((tip, loop[i], loop[(i + 1) % len(loop)]), Vector((0.0, 0.0, way)), "jaw" if r == 0 else "jaw end")

    def eye(self, m, sx):
        """A low dome lying on the skin of the head."""
        spokes = 8 if self.low else 22
        steps = 1 if self.low else 5
        xe, ye = self.EYE_AT
        rad = self.EYE_RADIUS
        e = rad * 0.12
        here = self.skin(xe, ye, sx)
        out = (self.skin(xe + e, ye, sx) - self.skin(xe - e, ye, sx)).cross(self.skin(xe, ye + e, sx) - self.skin(xe, ye - e, sx))
        out.normalize()
        if out.x * sx < 0.0:
            out = -out
        bulge = rad * self.EYE_BULGE
        middle = m.add(here + out * bulge, (0.0, 0.0), EYE)
        last = None
        for k in range(1, steps + 1):
            r = k / steps
            row = []
            for s in range(spokes):
                a = s / spokes * TAU
                p = self.skin(xe + math.cos(a) * rad * r, ye + math.sin(a) * rad * r, sx)
                row.append(m.add(p + out * (bulge * (1.0 - r * r) + 0.02 * rad * (1.0 - r)), (r, 0.0), EYE))
            for s in range(spokes):
                n = (s + 1) % spokes
                if last is None:
                    m.face((middle, row[s], row[n]), out, "eyes")
                else:
                    m.face((last[s], row[s], row[n], last[n]), out, "eyes")
            last = row

    def paired(self, m, part, name, sx, root, span, chord, length, width, thick, nt, nu, shape):
        """A paired fin from `root`, reaching `length` along `span`, `width` along `chord` (shape(t) 0..1)."""
        span = Vector((sx * span[0], span[1], span[2])).normalized()
        chord = Vector((sx * chord[0], chord[1], chord[2])).normalized()
        facing = span.cross(chord).normalized()
        if facing.x * sx < 0.0:
            facing = -facing

        def point(t, u):
            t *= 0.975
            return (length * t, width * shape(t) * u + 0.002 * LENGTH * u)

        blade(m, part, name, point, lambda p: root + span * p[0] + chord * p[1], facing, thick, nt, nu)

    def extras(self, m):
        """Anything else a kind has (barbels...): none here."""

    def make(self, name):
        m = Mesh()
        self.body(m)
        self.jaw(m)
        for sx in (1.0, -1.0):
            self.eye(m, sx)
        self.fins(m)
        self.extras(m)
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
        mesh.materials.append(material_of(self.NAME, self.COLOUR))
        for poly in mesh.polygons:
            poly.use_smooth = True
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
        print("BUILT %s verts=%d tris=%d" % (name, len(mesh.vertices), tris))
        winding(name, mesh, m)
        return obj, m


# --- the platy --------------------------------------------------------------------------------------------

class Platy(Fish):
    NAME = "platy"
    COLOUR = (0.95, 0.5, 0.12, 1.0)
    PROFILE = [
        (0.0, 0.0, 0.0, 0.0),
        (0.0003, 0.0010, 0.0009, 0.0008),
        (0.001, 0.0019, 0.0017, 0.0015),
        (0.0025, 0.0032, 0.0030, 0.0024),
        (0.005, 0.0050, 0.0048, 0.0032),
        (0.008, 0.0068, 0.0066, 0.0036),
        (0.012, 0.0083, 0.0083, 0.0038),
        (0.016, 0.0088, 0.0090, 0.0037),
        (0.020, 0.0085, 0.0088, 0.0034),
        (0.024, 0.0075, 0.0076, 0.0029),
        (0.028, 0.0060, 0.0058, 0.0023),
        (0.031, 0.0050, 0.0048, 0.0018),
        (0.034, 0.0045, 0.0044, 0.0013),
        (0.036, 0.0042, 0.0042, 0.0009),
        (0.0375, 0.0006, 0.0006, 0.0004),
    ]
    BODY_FROM = 0.0002
    BODY_TO = 0.0375
    JAW_TO = 0.0022
    JOINT = 0.0352
    EYE_AT = (0.0051, 0.0013)
    EYE_RADIUS = 0.0016
    EYE_BULGE = 0.26
    GILL_AT = 0.0098
    AROUND = 26
    AROUND_LOW = 8
    RINGS = ((0.0022, 0.0002), (0.009, 0.00035), (0.034, 0.0006), (0.0375, 0.0004))

    def mouth_y(self, xm):
        # a small mouth turned up: its line runs down and back from the tip
        return 0.0005 - 0.3 * xm

    def fins(self, m):
        low = self.low
        # The dorsal fin: rounded, its rays longest a third of the way back along it.
        def dorsal_root(u):
            xm = 0.0155 + 0.0095 * u
            return (xm, self.top(xm) - 0.0003)

        def dorsal_edge(u):
            xm = 0.0155 + 0.0095 * u
            h = 0.0068 * (0.28 + 0.72 * math.sin(math.pi * (0.2 + 0.8 * (1.0 - u)) * 0.85) ** 1.3) * (0.5 + 0.5 * smooth(0.0, 0.2, u))
            return (xm + 0.35 * h, self.top(xm) - 0.0003 + h)

        blade(m, DORSAL, "dorsal", between(dorsal_root, dorsal_edge), upright, SIDE, 0.0003, (7 if not low else 2), (10 if not low else 3))
        # The anal fin: small, behind the pelvic fins.
        def anal_root(u):
            xm = 0.0225 + 0.0045 * u
            return (xm, self.bottom(xm) + 0.00025)

        def anal_edge(u):
            xm = 0.0225 + 0.0045 * u
            h = 0.0045 * (0.3 + 0.7 * (1.0 - u) ** 0.9) * (0.6 + 0.4 * smooth(0.0, 0.15, u))
            return (xm + 0.4 * h, self.bottom(xm) + 0.00025 - h)

        blade(m, ANAL, "anal", between(anal_root, anal_edge), upright, SIDE, 0.0003, (5 if not low else 2), (6 if not low else 2))
        # The tail: a broad fan, its edge rounded.
        tail_root = lambda u: (0.0345, 0.0040 * (1.0 - 2.0 * u))
        tail_edge = through([
            (0.0, 0.0356, 0.0064), (0.1, 0.0420, 0.0084), (0.2, 0.0462, 0.0082), (0.3, 0.0487, 0.0064),
            (0.4, 0.0498, 0.0034), (0.5, 0.0501, 0.0), (0.6, 0.0498, -0.0034), (0.7, 0.0487, -0.0064),
            (0.8, 0.0462, -0.0082), (0.9, 0.0420, -0.0084), (1.0, 0.0356, -0.0064)])
        blade(m, TAIL, "tail", between(tail_root, tail_edge), upright, SIDE, 0.0004, (8 if not low else 3), (16 if not low else 6))
        for sx in (1.0, -1.0):
            root = self.skin(0.0102, -0.0028, sx)
            root.x -= sx * 0.0002
            self.paired(m, PECTORAL, "pectorals", sx, root, (0.35, -0.2, 0.9), (0.06, -0.9, 0.42),
                        0.0058, 0.0030, 0.0003, (6 if not low else 2), (4 if not low else 1),
                        lambda t: (0.5 + 0.5 * smooth(0.0, 0.3, t)) * (1.0 - t) ** 0.45)
            root = Vector((sx * 0.0012, self.bottom(0.0185) + 0.0003, 0.0185 - HALF))
            self.paired(m, PELVIC, "pelvics", sx, root, (0.28, -0.55, 0.78), (0.0, 0.14, 1.0),
                        0.0042, 0.0018, 0.0002, (5 if not low else 2), (3 if not low else 1),
                        lambda t: (1.0 - t) ** 0.7)


def material_of(name, colour):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = colour
    material.diffuse_color = colour
    return material


def winding(name, mesh, m):
    """Nothing inside out: every face's front is the way it was meant to face (Blender's front is the side a
    face's normal is on)."""
    bad = {}
    for poly in mesh.polygons:
        out, group = m.out[poly.index]
        if poly.normal.dot(to_b(out)) <= 0.0:
            bad[group] = bad.get(group, 0) + 1
            if os.environ.get("DEBUG_WINDING"):
                print("  bad", group, [tuple(round(x, 3) for x in m.data[v][0]) for v in poly.vertices],
                      tuple(round(x, 3) for x in out), tuple(round(x, 3) for x in poly.normal))
    told = ["%s %d/%d wrong" % (group, bad.get(group, 0), count) for group, count in m.count.items()]
    print("WINDING %s: %s: %s" % (name, "ok" if not bad else "INSIDE OUT", ", ".join(told)))


def export_one(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", export_yup=True, use_selection=True,
        export_animations=False, export_texcoords=True, export_vertex_color="NONE", export_all_vertex_colors=False,
    )


def render(folder, prefix, full, low, colours=False):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.show_cavity = True
    # (a model whose look is in its vertex colours has single-sheet fins, drawn from both sides)
    scene.display.shading.show_backface_culling = not colours
    scene.display.shading.color_type = "VERTEX" if colours else "MATERIAL"
    scene.render.resolution_x, scene.render.resolution_y = 1200, 800
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    L = LENGTH
    views = [("left", (1, 0, 0), (0, 0, 0), 1.15 * L), ("right", (-1, 0, 0), (0, 0, 0), 1.15 * L),
             ("front", (0, 1, 0), (0, 0, 0), 0.6 * L), ("back", (0, -1, 0), (0, 0, 0), 0.6 * L),
             ("top", (0.001, 0, 1), (0, 0, 0), 1.15 * L), ("under", (0.001, 0, -1), (0, 0, 0), 1.15 * L),
             ("head", (0.8, 0.5, 0.2), (0, HALF - 0.12 * L, 0), 0.42 * L),
             ("tail", (0.7, -0.6, 0.3), (0, -HALF + 0.2 * L, 0), 0.6 * L)]
    for tag, obj, only in (("", full, None), ("lo_", low, ("left", "head", "top", "back"))):
        for other in bpy.context.scene.objects:
            if other.type == "MESH":
                other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if only and view not in only:
                continue
            offset = Vector(direction).normalized() * 10.0
            camera.data.ortho_scale = frame
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y").to_euler()
            if view == "top":
                camera.rotation_euler = (0.0, 0.0, math.pi / 2)
            elif view == "under":
                camera.rotation_euler = (math.pi, 0.0, math.pi / 2)
            scene.render.filepath = os.path.join(folder, "%s_%s%s.png" % (prefix, tag, view))
            bpy.ops.render.render(write_still=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    fish = Platy(False)
    full, _ = fish.make(Platy.NAME)
    low, _ = Platy(True).make(Platy.NAME + "_lo")
    print("NUMBERS %s: joint=%.4f jaw_to=%.4f hinge_y=%.5f body_to=%.4f eye=(%.4f, %.4f) gill=%.4f" % (
        Platy.NAME, Platy.JOINT, Platy.JAW_TO, fish.mouth_y(Platy.JAW_TO), Platy.BODY_TO,
        Platy.EYE_AT[0], Platy.EYE_AT[1], Platy.GILL_AT))
    export_one(full, os.path.join(OUT, Platy.NAME + ".glb"))
    export_one(low, os.path.join(OUT, Platy.NAME + "_lo.glb"))
    low.location.x = 0.02
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, Platy.NAME + ".blend"))
    low.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, Platy.NAME, full, low)


if __name__ == "__main__":
    main()
