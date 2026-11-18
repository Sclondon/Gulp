"""Builds six kinds of seaweed and saves them:

    blender --background --python plants/seaweed/tools/build_seaweed.py

run from a game's root (or GameCommon's godot/seaweed/files). It writes, beside this file's folder:

    ../models/seaweed_<kind>.glb      one plant, full detail, for near the camera
    ../models/seaweed_<kind>_lo.glb   the same plant, very light, for far off
    seaweed.blend                     all twelve, side by side, to edit

for the kinds sea_lettuce, rockweed, red_algae, feather_boa, sea_palm and sargassum, and prints a WINDING line
for each (the check that nothing is inside out) and a SIZE line (how far it reaches).

WHAT EACH IS (at scale 1; SeaweedBed.SIZE holds the same numbers, and the shader's `model_tall` with them):
    sea_lettuce  (Ulva)                    0.35 m: four broad bright-green sheets, ruffled at the edges, cupped
    rockweed     (Fucus)                   0.32 m: three flat olive straps forking three times, a midrib, swollen
                                           pointed tips and pairs of air bladders along the lower forks
    red_algae    (a feathery red weed)     0.22 m: seven flat crimson fronds, each a rachis with alternate pinnae
                                           and pinnules: a feather
    feather_boa  (Egregia menziesii)       2.5 m: two long flat straps, twisting as they rise, fringed along both
                                           edges with small blades and oval floats
    sea_palm     (Postelsia palmaeformis)  0.5 m: a stout hollow stalk flared at its foot, under a crown of
                                           eighteen narrow drooping blades
    sargassum    (Sargassum natans)        1.0 m across: a floating mat of five sprigs radiating from the middle,
                                           lance-shaped leaves and berry-like floats. y = 0 is the WATERLINE: the
                                           floats ride on it (their tops 1 cm above), stems and leaves hang
                                           2 to 9 cm below.

Every blade, leaf and strap is ONE SHEET (no thickness): seaweed.gdshader draws both sides. The closed parts
(bladders, floats, berries and the sea palm's stalk) face outward; their insides are never seen.

In Godot: +Y is up, a plant stands on y = 0 round the Y axis (sargassum floats round it, on y = 0).

WHAT EACH POINT TELLS THE SHADER:
    UV   x across the part (0 one edge, 1 the other), y along it (0 at its foot, 1 at its tip)
    UV2  x: a number of the part's own (0 to 1)
         y: which part and where it is carried: part / 3 + 0.3 * carrier, part 0 a blade or leaf, 1 a stem or
            stalk, 2 a float or bladder; carrier (0 to 1) the height of the point on the plant's axis that carries
            it, of the kind's height: the shader bends the plant there (a sea palm's blades are all carried by the
            top of its stalk; a strap's points by their own heights)
(The glTF exporter writes a UV's y as 1 - y; this script writes 1 - y, so that Godot reads y.)
"""
import math
import os
import random

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(HERE, "..", "models")
TAU = math.tau
UP = Vector((0.0, 1.0, 0.0))

# Heights at scale 1 (metres): must match SeaweedBed.SIZE.
TALL = {
    "sea_lettuce": 0.35,
    "rockweed": 0.32,
    "red_algae": 0.22,
    "feather_boa": 2.5,
    "sea_palm": 0.5,
    "sargassum": 1.0,
}

BLADE, STEM, FLOAT = 0, 1, 2


class Mesh:
    """Points in Godot's axes (+Y up), triangles wound to face the way they are told to."""

    def __init__(self, tall):
        self.tall = tall
        self.verts = []
        self.uv = []
        self.uv2 = []
        self.faces = []
        self.told = []

    def dab(self, p, u, v, own, part, carrier=None):
        p = Vector(p)
        if carrier is None:
            carrier = p.y
        c = min(max(carrier / self.tall, 0.0), 1.0)
        self.verts.append(p)
        self.uv.append((u, v))
        self.uv2.append((own, part / 3.0 + 0.3 * c))
        return len(self.verts) - 1

    def tri(self, a, b, c, out):
        pa, pb, pc = self.verts[a], self.verts[b], self.verts[c]
        n = (pb - pa).cross(pc - pa)
        if n.length < 1e-12:
            raise ValueError("degenerate triangle")
        if n.dot(out) < 0.0:
            b, c = c, b
        self.faces.append((a, b, c))
        self.told.append(Vector(out))


def sheet(m, grid, uvs, own, part, carriers=None):
    """A single sheet through rows of points (grid[r][c]); every triangle told to face the same side."""
    ids = []
    for r, row in enumerate(grid):
        ids.append([m.dab(p, uvs[r][c][0], uvs[r][c][1], own, part,
                          None if carriers is None else carriers[r]) for c, p in enumerate(row)])
    for r in range(len(grid) - 1):
        for c in range(len(grid[r]) - 1):
            p00, p01, p10, p11 = grid[r][c], grid[r][c + 1], grid[r + 1][c], grid[r + 1][c + 1]
            out = ((p01 - p00) + (p11 - p10)).cross((p10 - p00) + (p11 - p01))
            m.tri(ids[r][c], ids[r][c + 1], ids[r + 1][c + 1], out)
            m.tri(ids[r][c], ids[r + 1][c + 1], ids[r + 1][c], out)
    return ids


def ribbon(m, centres, acrosses, halves, vs, own, part, tip=None, carriers=None, tip_carrier=None):
    """A strap: a pair of points each side of each centre, and a pointed tip if one is given."""
    grid = []
    uvs = []
    for c, a, h, v in zip(centres, acrosses, halves, vs):
        grid.append([c - a * h, c + a * h])
        uvs.append([(0.0, v), (1.0, v)])
    ids = sheet(m, grid, uvs, own, part, carriers)
    if tip is not None:
        last = grid[-1]
        out = (last[1] - last[0]).cross(tip - (last[0] + last[1]) * 0.5)
        t = m.dab(tip, 0.5, 1.0, own, part, tip_carrier)
        m.tri(ids[-1][0], ids[-1][1], t, out)


def berry(m, c, a, b, n, ra, rb, rn, own, carrier=None):
    """A small closed float (an octahedron with its points' normals outward: round enough at a few centimetres)."""
    pts = [c + a * ra, c - a * ra, c + b * rb, c - b * rb, c + n * rn, c - n * rn]
    uv = [(1.0, 0.5), (0.0, 0.5), (0.5, 1.0), (0.5, 0.0), (0.5, 0.5), (0.5, 0.5)]
    ids = [m.dab(p, uv[i][0], uv[i][1], own, FLOAT, c.y if carrier is None else carrier) for i, p in enumerate(pts)]
    for sa in (0, 1):
        for sb in (2, 3):
            for sn in (4, 5):
                mid = (pts[sa] + pts[sb] + pts[sn]) / 3.0
                m.tri(ids[sa], ids[sb], ids[sn], mid - c)


def frame(t):
    """Two directions square to t and to each other."""
    t = t.normalized()
    side = t.cross(Vector((1.0, 0.0, 0.0)) if abs(t.x) < 0.9 else Vector((0.0, 0.0, 1.0))).normalized()
    return side, t.cross(side).normalized()


def tube(m, centres, radii, sides, own, cap=True):
    """A closed-sided stalk through centres (open at its foot, which stands in the ground), capped at the top."""
    rings = []
    for i, (c, r) in enumerate(zip(centres, radii)):
        t = centres[min(i + 1, len(centres) - 1)] - centres[max(i - 1, 0)]
        u, w = frame(t)
        if i == 0:
            u0, w0 = u, w
        # (keep each ring's start turned the same way as the first's, so that the sides do not twist)
        u = (u0 - t.normalized() * u0.dot(t.normalized())).normalized()
        w = t.normalized().cross(u)
        v = i / (len(centres) - 1)
        ring = []
        for k in range(sides):
            ang = TAU * k / sides
            ring.append((c + (u * math.cos(ang) + w * math.sin(ang)) * r, k / sides, v))
        rings.append(ring)
    ids = [[m.dab(p, uu, vv, own, STEM) for p, uu, vv in ring] for ring in rings]
    for i in range(len(rings) - 1):
        mid = (centres[i] + centres[i + 1]) * 0.5
        for k in range(sides):
            k2 = (k + 1) % sides
            a, b, c2, d = ids[i][k], ids[i][k2], ids[i + 1][k2], ids[i + 1][k]
            pa, pc = rings[i][k][0], rings[i + 1][k2][0]
            out = (pa + pc) * 0.5 - mid
            m.tri(a, b, c2, out)
            m.tri(a, c2, d, out)
    if cap:
        top = centres[-1]
        t = (centres[-1] - centres[-2]).normalized()
        apex = m.dab(top + t * radii[-1] * 0.6, 0.5, 1.0, own, STEM)
        for k in range(sides):
            k2 = (k + 1) % sides
            out = (rings[-1][k][0] + rings[-1][k2][0]) * 0.5 - top + t * radii[-1]
            m.tri(ids[-1][k], ids[-1][k2], apex, out)


def spine(foot, out, lean, bow, length, v, steps=16, power=1.5):
    """A point and the way along at fraction v of a curve rising from foot, tilting from up towards `out` from
    `lean` to `lean + bow` (radians) at its tip."""
    p = Vector(foot)
    n = max(1, math.ceil(v * steps))
    for s in range(n):
        tilt = lean + bow * ((s + 0.5) * v / n) ** power
        p += (out * math.sin(tilt) + UP * math.cos(tilt)) * length * v / n
    tilt = lean + bow * v ** power
    return p, (out * math.sin(tilt) + UP * math.cos(tilt)).normalized()


def turned(vec, axis, angle):
    return Matrix.Rotation(angle, 3, axis.normalized()) @ vec


# ---------------------------------------------------------------- sea lettuce

def sea_lettuce(low):
    rng = random.Random(21)
    m = Mesh(TALL["sea_lettuce"])
    sheets = 3 if low else 4
    rows = 2 if low else 8
    cols = 2 if low else 4
    for s in range(sheets):
        heading = TAU * (s + rng.uniform(-0.2, 0.2)) / sheets
        out = Vector((math.cos(heading), 0.0, math.sin(heading)))
        side = out.cross(UP).normalized()
        length = 0.45 if s == 0 else rng.uniform(0.3, 0.43)
        maxw = length * rng.uniform(0.6, 0.8)
        lean = math.radians(rng.uniform(8.0, 22.0))
        bow = math.radians(rng.uniform(35.0, 70.0))
        twist = rng.uniform(-0.5, 0.5)
        foot = out * rng.uniform(0.004, 0.015)
        phase = rng.uniform(0.0, TAU)
        own = rng.random()
        grid, uvs = [], []
        for r in range(rows + 1):
            v = r / rows
            width = (0.06 + 0.94 * smooth(0.0, 0.35, v)) * (1.0 - 0.5 * smooth(0.7, 1.0, v))
            row, uvrow = [], []
            for c in range(cols + 1):
                u = -1.0 + 2.0 * c / cols
                # (the top is rounded: its corners come lower down the sheet)
                vv = v * (1.0 - 0.2 * u * u * v ** 3)
                p, along = spine(foot, out, lean, bow, length, vv)
                tw = twist * vv
                flat = along.cross(side).normalized()
                across = (side * math.cos(tw) + flat * math.sin(tw)).normalized()
                normal = along.cross(across).normalized()
                half = 0.5 * maxw * width
                ruffle = 0.075 * maxw * abs(u) ** 1.5 * math.sin(u * 2.3 + vv * 11.0 + phase) * (0.3 + 0.7 * vv)
                if low:
                    ruffle = 0.0
                cup = 0.12 * maxw * u * u * width
                row.append(p + across * u * half + normal * (ruffle + cup))
                uvrow.append(((u + 1.0) * 0.5, vv))
            grid.append(row)
            uvs.append(uvrow)
        sheet(m, grid, uvs, own, BLADE)
    return m


def smooth(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


# ---------------------------------------------------------------- rockweed

def rockweed(low):
    rng = random.Random(5)
    m = Mesh(TALL["rockweed"])
    fronds = 3
    for f in range(fronds):
        heading = TAU * (f + rng.uniform(-0.2, 0.2)) / fronds
        out = Vector((math.cos(heading), 0.0, math.sin(heading)))
        side = out.cross(UP).normalized()
        lean = math.radians(rng.uniform(10.0, 25.0))
        start = (UP * math.cos(lean) + out * math.sin(lean)).normalized()
        own = rng.random()
        scale = 1.0 if f == 0 else rng.uniform(0.8, 0.95)
        if low:
            rockweed_low_frond(m, out * 0.008, start, side, out, scale, own)
        else:
            rockweed_piece(m, rng, out * 0.008, start, side, out, 0.12 * scale, 0.0125, 0, 0.0, own, scale)
    return m


ROCK_DEPTH = 3          # forks: 1, 2, 4, then 8 tips
ROCK_LONG = (0.12, 0.1, 0.09, 0.11)


def rockweed_piece(m, rng, p0, d, side, out, length, half, depth, v0, own, scale):
    tip = depth == ROCK_DEPTH
    vlen = 0.25          # how much of the frond's whole length (UV y) a piece is
    normal = d.cross(side).normalized()
    across = normal.cross(d).normalized()
    # (a gentle curve out from the middle, as the straps lean over)
    bowv = (out - d * d.dot(out)) * 0.12

    def at(t):
        return p0 + d * length * t + bowv * length * t * t

    if tip:
        # A swollen pointed tip (the receptacle): wider at its middle, then a point.
        ts, ws = (0.0, 0.5, 0.92), (half, half * 1.45, half * 0.8)
        centres = [at(t) for t in ts]
        ribbon(m, centres, [across] * 3, ws, [v0 + vlen * t for t in ts], own, BLADE, tip=at(1.15))
        return
    centres = [at(0.0), at(1.0)]
    ribbon(m, centres, [across] * 2, [half, half * 0.95], [v0, v0 + vlen], own, BLADE)
    if depth < 2:
        # A pair of air bladders, either side of the midrib, bulging both faces.
        c = at(0.55)
        for s in (-1.0, 1.0):
            berry(m, c + across * s * half * 0.42, d, across, normal, 0.015, 0.0075, 0.0075, own)
    end = at(1.0)
    dn = (d + bowv * 2.0).normalized()
    spread = math.radians(rng.uniform(17.0, 27.0))
    for s in (-1.0, 1.0):
        child = turned(dn, normal, s * spread)
        rockweed_piece(m, rng, end, child, side, out, ROCK_LONG[depth + 1] * scale * rng.uniform(0.85, 1.1),
                       half * 0.92, depth + 1, v0 + vlen, own, scale)


def rockweed_low_frond(m, p0, d, side, out, scale, own):
    normal = d.cross(side).normalized()
    across = normal.cross(d).normalized()
    fork = p0 + d * 0.2 * scale + out * 0.02
    ribbon(m, [p0, fork], [across] * 2, [0.012, 0.03], [0.0, 0.5], own, BLADE)
    for s in (-1.0, 1.0):
        tipd = turned(d, normal, s * 0.4)
        tip = fork + tipd * 0.2 * scale + out * 0.02
        a = m.dab(fork + across * s * 0.03, 1.0 if s > 0 else 0.0, 0.5, own, BLADE)
        b = m.dab(fork, 0.5, 0.5, own, BLADE)
        c = m.dab(tip, 0.5, 1.0, own, BLADE)
        m.tri(a, b, c, normal)


# ---------------------------------------------------------------- red algae

def red_algae(low):
    rng = random.Random(33)
    m = Mesh(TALL["red_algae"])
    fronds = 5 if low else 7
    for f in range(fronds):
        heading = TAU * (f + rng.uniform(-0.3, 0.3)) / fronds
        out = Vector((math.cos(heading), 0.0, math.sin(heading)))
        # (each frond is a flat feather, its plane turned a little from facing out)
        side = turned(out.cross(UP).normalized(), UP, rng.uniform(-0.5, 0.5))
        length = 0.3 if f == 0 else rng.uniform(0.17, 0.29)
        lean = math.radians(rng.uniform(10.0, 40.0))
        bow = math.radians(rng.uniform(15.0, 50.0))
        own = rng.random()
        foot = out * rng.uniform(0.003, 0.012)

        def pt(v):
            return spine(foot, out, lean, bow, length, v)

        if low:
            p0, d0 = pt(0.0)
            pm, dm = pt(0.5)
            p1, d1 = pt(1.0)
            normal = dm.cross(side).normalized()
            across = normal.cross(dm).normalized()
            a = m.dab(p0, 0.5, 0.0, own, BLADE)
            b = m.dab(pm - across * length * 0.22, 0.0, 0.5, own, BLADE)
            c = m.dab(pm + across * length * 0.22, 1.0, 0.5, own, BLADE)
            t = m.dab(p1, 0.5, 1.0, own, BLADE)
            m.tri(a, c, b, normal)
            m.tri(b, c, t, normal)
            continue
        vs = (0.0, 0.25, 0.5, 0.75, 0.95)
        centres, acrosses, halves = [], [], []
        for v in vs:
            p, d = pt(v)
            normal = d.cross(side).normalized()
            centres.append(p)
            acrosses.append(normal.cross(d).normalized())
            halves.append(0.005 * (1.0 - 0.5 * v))
        ribbon(m, centres, acrosses, halves, list(vs), own, BLADE, tip=pt(1.0)[0])
        for k in range(6):
            v = 0.16 + k * 0.135
            s = 1.0 if k % 2 == 0 else -1.0
            base, d = pt(v)
            normal = d.cross(side).normalized()
            across = normal.cross(d).normalized()
            angle = math.radians(52.0 + rng.uniform(-6.0, 6.0))
            pd = (d * math.cos(angle) + across * s * math.sin(angle)).normalized()
            plen = length * (0.34 - 0.04 * k)
            pacr = normal.cross(pd).normalized()
            # (each pinna curves a little up along the frond)
            mid = base + pd * plen * 0.5 + d * plen * 0.06
            end = base + pd * plen + d * plen * 0.18
            ph = 0.0045 * (1.0 - 0.08 * k)
            ribbon(m, [base, mid], [pacr, pacr], [ph, ph * 0.8], [v, v + 0.06], own, BLADE, tip=end,
                   carriers=None)
            # Two pinnules off its outer side, single slivers.
            for q in (0.35, 0.68):
                foot_q = base + pd * plen * q + d * plen * 0.06 * q * 2.0
                qd = (pd * math.cos(0.9) + d * math.sin(0.9)).normalized()
                along = pd * plen * 0.07
                tipq = foot_q + qd * plen * 0.45
                a = m.dab(foot_q - along, 0.0, v, own, BLADE)
                b = m.dab(foot_q + along, 1.0, v, own, BLADE)
                c = m.dab(tipq, 0.5, v + 0.1, own, BLADE)
                m.tri(a, b, c, normal)
    return m


# ---------------------------------------------------------------- feather boa kelp

def feather_boa(low):
    rng = random.Random(8)
    m = Mesh(TALL["feather_boa"])
    straps = 2
    for s in range(straps):
        heading = TAU * (s * 0.5 + rng.uniform(-0.1, 0.1))
        out = Vector((math.cos(heading), 0.0, math.sin(heading)))
        side0 = out.cross(UP).normalized()
        length = 2.5 if s == 0 else 2.2
        lean = math.radians(rng.uniform(4.0, 10.0))
        phase = rng.uniform(0.0, TAU)
        twist_turns = rng.uniform(2.0, 3.0)
        own = rng.random()
        segs = 6 if low else 20
        # The strap's middle line: rising, leaning out, with a slow S.
        steps = 60
        line = [Vector(out * 0.01)]
        for i in range(steps):
            v = (i + 0.5) / steps
            tilt = lean + 0.22 * math.sin(v * math.pi * 1.6 + phase) * v
            drift = side0 * 0.12 * math.sin(v * math.pi * 1.2 + phase) * v
            dirn = (out * math.sin(tilt) + UP * math.cos(tilt) + drift).normalized()
            line.append(line[-1] + dirn * length / steps)

        def at(v):
            f = v * steps
            i = min(int(f), steps - 1)
            return line[i].lerp(line[i + 1], f - i), (line[i + 1] - line[i]).normalized()

        centres, acrosses, halves, vs = [], [], [], []
        frames = []
        for r in range(segs + 1):
            v = r / segs * 0.985
            c, d = at(v)
            tw = twist_turns * v
            a0 = (side0 - d * d.dot(side0)).normalized()
            across = turned(a0, d, tw)
            normal = d.cross(across).normalized()
            half = (0.065 if low else 0.03) * (0.55 + 0.45 * smooth(0.0, 0.08, v)) * (1.0 - 0.4 * smooth(0.85, 1.0, v))
            centres.append(c)
            acrosses.append(across)
            halves.append(half)
            vs.append(v)
            frames.append((c, d, across, normal, half))
        tip, _ = at(1.0)
        ribbon(m, centres, acrosses, halves, vs, own, BLADE, tip=tip)
        if low:
            continue
        # The fringe: a small blade or an oval float off each edge at each row.
        for r in range(2, segs):
            c, d, across, normal, half = frames[r]
            for k, sgn in enumerate((-1.0, 1.0)):
                edge = c + across * sgn * half
                own_k = (own + r * 0.137 + k * 0.31) % 1.0
                if (r * 2 + k) % 5 == 0:
                    fd = (across * sgn * 0.75 + d * 0.65).normalized()
                    centre = edge + fd * 0.024
                    berry(m, centre, fd, normal.cross(fd).normalized(), normal, 0.024, 0.013, 0.013, own_k,
                          carrier=c.y)
                else:
                    ang = rng.uniform(0.55, 0.85)
                    fd = (across * sgn * math.sin(ang) + d * math.cos(ang)).normalized()
                    fd = turned(fd, d, rng.uniform(-0.35, 0.35))
                    fl = rng.uniform(0.08, 0.12)
                    perp = normal.cross(fd).normalized()
                    hw = fl * 0.2
                    a = m.dab(edge - d * 0.004, 0.5, 0.0, own_k, BLADE, c.y)
                    b = m.dab(edge + fd * fl * 0.4 + perp * hw, 0.0, 0.5, own_k, BLADE, c.y)
                    e = m.dab(edge + fd * fl * 0.4 - perp * hw, 1.0, 0.5, own_k, BLADE, c.y)
                    t = m.dab(edge + fd * fl, 0.5, 1.0, own_k, BLADE, c.y)
                    face_n = perp.cross(fd)
                    m.tri(a, b, e, face_n)
                    m.tri(b, t, e, face_n)
    return m


# ---------------------------------------------------------------- sea palm

def sea_palm(low):
    rng = random.Random(12)
    m = Mesh(TALL["sea_palm"])
    own = rng.random()
    top_y = 0.42
    if low:
        ys, rs, sides = (0.0, top_y), (0.032, 0.013), 3
    else:
        ys = (0.0, 0.025, 0.1, 0.2, 0.31, top_y)
        rs = (0.045, 0.028, 0.021, 0.017, 0.015, 0.013)
        sides = 6
    centres = [Vector((0.012 * (y / top_y) ** 2, y, 0.004 * (y / top_y))) for y in ys]
    tube(m, centres, rs, sides, own)
    top = centres[-1]
    blades = 6 if low else 18
    for k in range(blades):
        heading = TAU * (k + rng.uniform(-0.3, 0.3)) / blades
        out = Vector((math.cos(heading), 0.0, math.sin(heading)))
        length = rng.uniform(0.17, 0.24)
        lean = math.radians(rng.uniform(25.0, 55.0))
        bow = math.radians(rng.uniform(85.0, 120.0))
        foot = top + out * 0.01 + UP * rng.uniform(-0.01, 0.02)
        own_k = rng.random()
        side = out.cross(UP).normalized()
        vs = (0.0, 0.5) if low else (0.0, 0.3, 0.6, 0.85)
        centres_b, acr, halves = [], [], []
        for v in vs:
            p, d = spine(foot, out, lean, bow, length, v, power=1.2)
            centres_b.append(p)
            normal = side.cross(d).normalized()
            acr.append(d.cross(normal).normalized())
            halves.append((0.016 if low else 0.009) * (0.6 + 0.4 * smooth(0.0, 0.25, v)) * (1.0 - 0.3 * v))
        tip, _ = spine(foot, out, lean, bow, length, 1.0, power=1.2)
        ribbon(m, centres_b, acr, halves, list(vs), own_k, BLADE, tip=tip,
               carriers=[top_y] * len(vs), tip_carrier=top_y)
    return m


# ---------------------------------------------------------------- sargassum

def sargassum(low):
    rng = random.Random(44)
    m = Mesh(TALL["sargassum"])
    sprigs = 6
    for s in range(sprigs):
        heading = TAU * (s + rng.uniform(-0.25, 0.25)) / sprigs
        out = Vector((math.cos(heading), 0.0, math.sin(heading)))
        side = out.cross(UP).normalized()
        length = rng.uniform(0.38, 0.48)
        own = rng.random()
        start = out * rng.uniform(0.0, 0.06) + side * rng.uniform(-0.04, 0.04)
        depth = rng.uniform(0.03, 0.05)
        wav = rng.uniform(0.0, TAU)

        def stem_at(v, start=start, out=out, side=side, length=length, depth=depth, wav=wav):
            p = start + out * length * v + side * 0.05 * math.sin(v * 4.0 + wav)
            p.y = -depth - 0.015 * math.sin(v * 5.0 + wav)
            return p

        if low:
            # One wide golden strip a sprig, where the leaves and floats lie.
            ps = [stem_at(0.0), stem_at(0.6), stem_at(1.0)]
            acr = [side, side, side]
            ribbon(m, ps, acr, [0.05, 0.09, 0.07], [0.0, 0.6, 1.0], own, BLADE, carriers=[0.0] * 3)
            continue
        # The main stem, a narrow strap lying flat, and one side branch.
        vs = (0.0, 0.35, 0.7, 1.0)
        ribbon(m, [stem_at(v) for v in vs], [side] * 4, [0.004] * 4, list(vs), own, STEM, carriers=[0.0] * 4)
        bv = rng.uniform(0.35, 0.5)
        bs = 1.0 if s % 2 == 0 else -1.0
        bstart = stem_at(bv)
        bdir = (out * 0.6 + side * bs * 0.8).normalized()
        blen = length * 0.45
        bends = [bstart, bstart + bdir * blen * 0.5 + Vector((0.0, 0.01, 0.0)), bstart + bdir * blen]
        bacr = bdir.cross(UP).normalized()
        ribbon(m, bends, [bacr] * 3, [0.0035] * 3, [0.0, 0.5, 1.0], own, STEM, carriers=[0.0] * 3)
        # Leaves: narrow lance blades off the stems, hanging a little below them.
        spots = [(stem_at(v), out, k) for k, v in enumerate((0.08, 0.2, 0.32, 0.44, 0.56, 0.68, 0.8, 0.92))]
        spots += [(bstart + bdir * blen * q, bdir, 8 + k) for k, q in enumerate((0.4, 0.85, 1.0))]
        for p, along, k in spots:
            sgn = 1.0 if k % 2 == 0 else -1.0
            lside = along.cross(UP).normalized()
            ld = (lside * sgn * 0.8 + along * 0.5 + Vector((0.0, -0.3, 0.0))).normalized()
            ld = turned(ld, UP, rng.uniform(-0.3, 0.3))
            ll = rng.uniform(0.11, 0.15)
            lw = ll * 0.2
            perp = ld.cross(UP).normalized()
            if perp.length < 0.1:
                perp = lside
            fold = ld.cross(perp).normalized() * lw * 0.3
            own_k = rng.random()
            a = m.dab(p, 0.5, 0.0, own_k, BLADE, 0.0)
            b = m.dab(p + ld * ll * 0.45 + perp * lw + fold, 0.0, 0.45, own_k, BLADE, 0.0)
            e = m.dab(p + ld * ll * 0.45 - perp * lw + fold, 1.0, 0.45, own_k, BLADE, 0.0)
            t = m.dab(p + ld * ll, 0.5, 1.0, own_k, BLADE, 0.0)
            face_n = perp.cross(ld)
            m.tri(a, b, e, face_n)
            m.tri(b, t, e, face_n)
        # Berry floats, riding on the waterline (y = 0) in a little cluster near the sprig's end.
        for k in range(3):
            v = rng.uniform(0.45, 0.95)
            c = stem_at(v) + side * rng.uniform(-0.05, 0.05) + out * rng.uniform(-0.03, 0.03)
            c.y = -0.004
            r = rng.uniform(0.011, 0.014)
            ang = rng.uniform(0.0, TAU)
            a = Vector((math.cos(ang), 0.0, math.sin(ang)))
            berry(m, c, a, UP, a.cross(UP).normalized(), r, r, r, rng.random(), carrier=0.0)
    return m


# ---------------------------------------------------------------- out to Blender, and checks

def to_blender(p):
    """Godot (x, y up, z) to Blender (x, y, z up): the glTF exporter turns it back."""
    return (p.x, -p.z, p.y)


def to_object(name, m):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_blender(v) for v in m.verts], [], [list(f) for f in m.faces])
    mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.new(name="UV2")
    first = mesh.uv_layers["UVMap"]
    second = mesh.uv_layers["UV2"]
    for poly in mesh.polygons:
        for loop in poly.loop_indices:
            vi = mesh.loops[loop].vertex_index
            first.data[loop].uv = (m.uv[vi][0], 1.0 - m.uv[vi][1])
            second.data[loop].uv = (m.uv2[vi][0], 1.0 - m.uv2[vi][1])
        poly.use_smooth = True
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def winding(name, m, obj):
    """Every face as Blender holds it against the way it was told to face."""
    wrong = 0
    for poly, told in zip(obj.data.polygons, m.told):
        n = poly.normal
        back = Vector((n.x, n.z, -n.y))
        if back.dot(told) <= 0.0:
            wrong += 1
    print("WINDING %s: %s: %d of %d triangles against the way they were told to face" % (
        name, "ok" if wrong == 0 and len(obj.data.polygons) == len(m.faces) else "INSIDE OUT", wrong,
        len(obj.data.polygons)))
    lo = Vector((min(v.x for v in m.verts), min(v.y for v in m.verts), min(v.z for v in m.verts)))
    hi = Vector((max(v.x for v in m.verts), max(v.y for v in m.verts), max(v.z for v in m.verts)))
    print("SIZE %s: x %.3f..%.3f  y %.3f..%.3f  z %.3f..%.3f" % (name, lo.x, hi.x, lo.y, hi.y, lo.z, hi.z))


def export_one(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", export_yup=True, use_selection=True,
        export_animations=False, export_texcoords=True, export_normals=True,
        export_materials="NONE", export_vertex_color="NONE",
    )


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    os.makedirs(MODELS, exist_ok=True)
    builders = [
        ("sea_lettuce", sea_lettuce),
        ("rockweed", rockweed),
        ("red_algae", red_algae),
        ("feather_boa", feather_boa),
        ("sea_palm", sea_palm),
        ("sargassum", sargassum),
    ]
    x = 0.0
    for kind, build in builders:
        for low in (False, True):
            name = "seaweed_%s%s" % (kind, "_lo" if low else "")
            m = build(low)
            obj = to_object(name, m)
            winding(name, m, obj)
            export_one(obj, os.path.join(MODELS, name + ".glb"))
            obj.location.x = x
            obj.location.y = 0.0 if not low else -1.5
        x += max(TALL[kind], 0.6) * 1.4
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "seaweed.blend"))
    print("BUILT seaweed")


if __name__ == "__main__":
    main()
