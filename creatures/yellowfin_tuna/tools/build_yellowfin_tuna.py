"""Builds the yellowfin tuna (creatures/yellowfin_tuna) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/yellowfin_tuna/tools/build_yellowfin_tuna.py
    blender --background --python creatures/yellowfin_tuna/tools/build_yellowfin_tuna.py -- <preview folder>   # with pictures

Writes creatures/yellowfin_tuna/models/yellowfin_tuna.glb (the full model, for close pictures),
yellowfin_tuna_game.glb (the game model) and yellowfin_tuna_lo.glb (far off, phones), and the editable
creatures/yellowfin_tuna/tools/yellowfin_tuna.blend (this folder has a .gdignore; it holds all three). Each
model is one still mesh: the full and the low model of two surfaces (the body as it always was, then the gills
and the back of the throat, added 2026-11-18 and written into the .glb by `merge_glb`), the game model of one.
The shader (yellowfin_tuna.gdshader) draws every marking and swims
it. It prints a WINDING line for each (the check that nothing is inside out) and an EYE line (the eye's
middle and facing, as the shader has them for its cartoon eye).

THE GAME MODEL (added 2026-11-18; the user, after looking at Twilight Princess's Link beside these: "We should
have a twilight princess model to compare to so we can make low poly versions while maintaining high quality
looks and silhouettes"). Built here from the same curves as the full model, not thinned from it, with its
triangles spent where they show: its rings are as few as follow the skin to within GAME_TOL (so they crowd at
the snout, the head and the tail wrist and spread out along the flanks), close enough through the mouth for
it to open cleanly; fewer points round the body; each fin with few rows across (its thickness hardly shows)
but enough along its edges for their curves and tips; the first dorsal's scallops a point at each spine's tip
and one between; a round eye of 28 spokes. Every UV and UV2 means what it does on the full model.

A yellowfin tuna (Thunnus albacares), 1.5 m from the tip of its snout to the tips of its tail, built from the
species (the component's README says which pictures were looked at; none was traced):

- THE BODY: a deep, round, rigid torpedo, deepest (0.39 m) and widest (0.28 m) a third of the way back, running
  to a very narrow tail wrist with a keel on each side. A pointed head; the line of the mouth, a groove; the
  gill cover, a step; a big eye, a low dome on each side.
- THE MOUTH (added 2026-11-17, the user: "the fish should be able to open their mouths"): the head is cut along
  the line of the mouth from near the tip of the snout back to its corner under the eye, and from there down
  round the back of the lower jaw to the throat. Above the cut is the body, its underside the roof of the mouth
  (hollowed up into the head); below it THE LOWER JAW, a part of its own, its top the floor of the mouth
  (hollowed down). Both are closed skins on the skin the fish had before (the same `body_point`), meeting lip to
  lip, so that shut it looks as it did; the shader swings the jaw down about its hinge at the corner (`gape`),
  the back of the jaw bending as the throat stretches. THE CHEEKS, a wall on each side of the mouth from lip to
  lip, close its sides when it gapes; the shader folds them away inside the head as it shuts.
- THE FINS, each a thin closed blade (two skins that meet at its edges): the first dorsal (thirteen spines, its
  edge scalloped between them; the shader folds it down); the long sickle second dorsal and anal fins; nine
  finlets above and eight below, from those back to the tail; the tall stiff crescent tail; two long pectoral
  fins held out like wings; two small pelvic fins.

Everything here is in Godot space (metres, Y up, X to its left side, its nose at -Z) until it is written out;
the origin is on its middle line, half way along (0.75 m behind the tip of its snout). `xm` below is metres
behind the tip of the snout.

What a point is, for the shader: UV2.y the part (0 body, 1 first dorsal, 2 the sickle fins, 3 a finlet, 4 the
tail, 5 a pectoral fin, 6 a pelvic fin, 7 an eye, 8 the lower jaw, 9 a cheek, 10 a gill: see `gills`). UV, on the body and the lower jaw: x how far
along (0 snout to 1 tail tips), y how high on its side (1 the ridge of the back, 0.5 its middle line, 0 the keel
of the belly); on a fin: x from its root (0) to its tip (1), y from its leading edge (0) to its trailing edge
(1); on an eye: x from its middle (0) to its rim (1). UV2.x, on the first dorsal, how far the point stands above
the fin's root (metres), for folding it; on the body and the lower jaw, how far inside the mouth the point is (0
the skin and the lips, 1 the middle of the mouth's roof or floor), for its dark lining; on a cheek, how far down
it is from the upper lip (0) to the lower (1). (The glTF writer flips
V: what is written here is 1 - v, so that Godot reads v.)

The numbers marked "as the shader has it" are in yellowfin_tuna.gdshader too (and the jaw's in the component's
tuna_check.gd): change one, change the other.
"""

import json
import math
import os
import struct
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "models")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = ARGS[0] if ARGS else ""

LENGTH = 1.5
HALF = 0.75
BODY, DORSAL, SICKLE, FINLET, TAIL, PECTORAL, PELVIC, EYE, JAW, CHEEK, GILLS = range(11)
TAU = math.tau

# The body's outline: metres behind the snout, half its depth above its middle line, half its depth below,
# half its width.
PROFILE = [
    (0.0, 0.0, 0.0, 0.0),
    (0.003, 0.0065, 0.0075, 0.0055),
    (0.012, 0.016, 0.019, 0.0135),
    (0.04, 0.037, 0.046, 0.031),
    (0.10, 0.071, 0.085, 0.057),
    (0.18, 0.108, 0.122, 0.085),
    (0.28, 0.146, 0.157, 0.112),
    (0.40, 0.175, 0.184, 0.133),
    (0.52, 0.189, 0.197, 0.142),
    (0.64, 0.186, 0.192, 0.140),
    (0.78, 0.162, 0.171, 0.123),
    (0.90, 0.127, 0.136, 0.100),
    (1.02, 0.089, 0.095, 0.072),
    (1.12, 0.058, 0.062, 0.049),
    (1.20, 0.038, 0.039, 0.034),
    (1.27, 0.024, 0.024, 0.025),
    (1.31, 0.019, 0.019, 0.021),
    (1.345, 0.020, 0.020, 0.012),
    (1.385, 0.003, 0.003, 0.002),
]
BODY_FROM = 0.002
BODY_TO = 1.385

# As the shader has it: the line of the mouth, the edge of the gill cover, the eye.
MOUTH_TO = 0.132
EYE_AT = (0.145, 0.024)
EYE_RADIUS = 0.03


def mouth_y(xm):
    return -0.004 - 0.34 * xm + 0.55 * xm * xm


def gill_x(y):
    return 0.36 - 3.0 * (y + 0.015) ** 2


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


_XS = [p[0] for p in PROFILE]
_CURVES = []
for column in (1, 2, 3):
    ys = [p[column] for p in PROFILE]
    _CURVES.append((ys, _slopes(_XS, ys)))


def outline(xm):
    """(half depth above, half depth below, half width) at `xm`."""
    xm = max(_XS[0], min(_XS[-1], xm))
    i = 0
    while i < len(_XS) - 2 and xm > _XS[i + 1]:
        i += 1
    h = _XS[i + 1] - _XS[i]
    t = (xm - _XS[i]) / h
    out = []
    for ys, m in _CURVES:
        a = (2 * t ** 3 - 3 * t ** 2 + 1) * ys[i] + (t ** 3 - 2 * t ** 2 + t) * h * m[i]
        b = (-2 * t ** 3 + 3 * t ** 2) * ys[i + 1] + (t ** 3 - t ** 2) * h * m[i + 1]
        out.append(max(a + b, 0.0005))
    return out


def top(xm):
    return outline(xm)[0]


def bottom(xm):
    return -outline(xm)[1]


def body_point(xm, angle, gill=True):
    """A point of the skin: `angle` round the body from the ridge of the back (0) by its left side (a
    quarter turn) to the keel of the belly (half a turn); without the step of the gill cover if not `gill`."""
    up, down, wide = outline(xm)
    c = math.cos(angle)
    s = math.sin(angle)
    y = c * (up if c >= 0.0 else down)
    side = math.copysign(abs(s) ** 0.92, s) * wide
    # the keels: a ridge along each side of the tail wrist
    keel = 0.009 * smooth(1.15, 1.27, xm) * (1.0 - smooth(1.32, 1.37, xm))
    side += math.copysign(keel * math.exp(-(c / 0.3) ** 2), s)
    # the mouth: a groove from the tip of the snout back and down to under the eye
    if xm < MOUTH_TO + 0.01:
        groove = math.exp(-((y - mouth_y(xm)) / 0.0035) ** 2) * smooth(0.004, 0.02, xm) * (1.0 - smooth(MOUTH_TO - 0.012, MOUTH_TO + 0.004, xm))
        side *= 1.0 - 0.08 * groove
    # the gill cover: it stands a little proud of the body behind its edge
    behind = xm - gill_x(y)
    if gill and behind > 0.0 and wide > 0.01:
        mask = smooth(-0.95, -0.8, c) * (1.0 - smooth(0.4, 0.6, c))
        step = 0.0045 * smooth(0.0, 0.004, behind) * math.exp(-behind / 0.035) * mask
        side *= 1.0 - step / wide
    return Vector((side, y, xm - HALF))


# The mouth. The lower jaw runs from JAW_FROM (just behind the tip of the snout) back to JAW_BACK (the throat).
# As the shader has it: it hinges at the corner of the mouth (HINGE: metres behind the snout, metres up) and
# swings down GAPE_TURN radians at `gape` 1, all of it ahead of the corner, less and less behind it, none at
# the throat (`jaw_turn`).
JAW_FROM = 0.006
JAW_BACK = 0.172
HINGE = (MOUTH_TO, mouth_y(MOUTH_TO))
GAPE_TURN = 0.55
# How far the roof of the mouth is hollowed up towards the top of the head, and the floor down towards the
# underside of the jaw, along their middles.
MOUTH_HOLLOW = 0.35
JAW_HOLLOW = 0.3
# The cheeks: how far in from the lips they hang (a share of the half width there), and in how many rows.
CHEEK_IN = 0.94
CHEEK_ROWS = 6


def roof(xm):
    """How high the cut between the body and the lower jaw is at `xm`: the line of the mouth as far back as its
    corner, then down round the back of the lower jaw to the belly by JAW_BACK."""
    line = mouth_y(min(xm, MOUTH_TO))
    return line + (bottom(xm) - line) * smooth(MOUTH_TO, JAW_BACK, xm) ** 1.5


def jaw_turn(xm):
    """As the shader has it: how much of the jaw's swing its points `xm` along take."""
    return 1.0 - smooth(MOUTH_TO - 0.02, JAW_BACK, xm)


def swung(p, angle):
    """`p` swung down about the jaw's hinge by `angle` (radians), as the shader swings the jaw."""
    hy, hz = HINGE[1], HINGE[0] - HALF
    dy, dz = p.y - hy, p.z - hz
    return Vector((p.x, hy + dy * math.cos(angle) + dz * math.sin(angle), hz + dz * math.cos(angle) - dy * math.sin(angle)))


def lined_share(xm, of_jaw):
    """How much of the mouth's dark lining there is at `xm` (none behind the corner of the mouth, nor at the
    jaw's very tip, where its skin closes over it)."""
    front = smooth(JAW_FROM, JAW_FROM + 0.012, xm) if of_jaw else 1.0
    return front * (1.0 - smooth(MOUTH_TO, MOUTH_TO + 0.012, xm))


def hollow_share(xm):
    return smooth(JAW_FROM, JAW_FROM + 0.03, xm) * (1.0 - smooth(MOUTH_TO - 0.03, MOUTH_TO, xm))


def lining(side, chord):
    """How far inside the mouth a point of its roof or floor is: 0 at the lips, 1 along the middle."""
    if chord < 1e-9 or abs(side) >= chord:
        return 0.0
    return (1.0 - (side / chord) ** 2) ** 2


def lip(xm, sx):
    """The point of the skin at `xm` on the cut (`roof`), on the side `sx` (1 its left, -1 its right), and how
    far round the body from the ridge of the back it is (radians)."""
    y = roof(xm)
    lo, hi = 0.0, math.pi
    for _ in range(50):
        middle = 0.5 * (lo + hi)
        if body_point(xm, middle).y > y:
            lo = middle
        else:
            hi = middle
    angle = 0.5 * (lo + hi)
    return body_point(xm, sx * angle), angle


def skin_normal(xm, angle, around):
    """Which way the skin the fish had before the mouth was cut faces at `xm` and `angle` (a unit vector), taken
    across a column of the model either way (as finely as the model itself can show it): what a point of the
    skin round the mouth is given as its normal, so that it shades across the lips as it did before."""
    e = 1e-4
    a = TAU / around
    n = (body_point(xm + e, angle) - body_point(xm - e, angle)).cross(body_point(xm, angle + a) - body_point(xm, angle - a))
    p = body_point(xm, angle)
    if n.dot(Vector((p.x, p.y, 0.0))) < 0.0:
        n = -n
    return n.normalized()


def mouth_ring(xm, around, of_jaw):
    """One ring of the body (`of_jaw` False) or of the lower jaw (True) where the cut runs through the head:
    (point, how far inside the mouth, which lip it is: 1, -1 or 0, where it is round the ring in columns, the
    normal of a point of the skin or None) for each of the body's `around` angles. The points on the part's own side of the cut are the skin as it was;
    the first point past the cut on each side is moved onto the lip (the same place for the body and the jaw,
    so that they meet); the rest are laid across the cut as the roof (or the floor) of the mouth."""
    raw = [body_point(xm, c / around * TAU) for c in range(around)]
    cut = roof(xm)
    lips = {1.0: lip(xm, 1.0), -1.0: lip(xm, -1.0)}
    chord = abs(lips[1.0][0].x)
    up, down, _ = outline(xm)
    gone = [(p.y < cut) != of_jaw for p in raw]
    ring = []
    for i, p in enumerate(raw):
        if not gone[i]:
            ring.append((p, 0.0, 0, float(i), skin_normal(xm, i / around * TAU, around)))
            continue
        sx = 1.0 if p.x >= 0.0 else -1.0
        if not gone[i - 1] or not gone[(i + 1) % around]:
            at, angle = lips[sx]
            column = angle / TAU * around
            ring.append((at.copy(), 0.0, int(sx), column if sx > 0.0 else around - column, skin_normal(xm, sx * angle, around)))
            continue
        side = math.copysign(min(abs(p.x), chord), p.x)
        deep = lining(side, chord) * hollow_share(xm)
        y = cut - JAW_HOLLOW * (cut + down) * deep if of_jaw else cut + MOUTH_HOLLOW * (up - cut) * deep
        ring.append((Vector((side, y, lips[1.0][0].z)), lining(side, chord) * lined_share(xm, of_jaw), 0, float(i), None))
    return ring


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        # per point: (uv, uv2)
        self.data = []
        # per face: the way it should face
        self.out = []
        self.count = {}
        # per face: 0 the body's surface, 1 the gills' and the back of the throat's (a second surface on the full model)
        self.layers = []
        self.layer = 0
        # per point on a lip: which lip (1 its left, -1 its right), and its normal; the edges along a lip are made sharp
        self.lips = {}
        self.normals = {}
        self.sharp = set()

    def tri(self, tri, judge):
        """A triangle of the head round the mouth; `judge(triangle)` says the way it must face and its name.
        An edge along a lip is marked sharp."""
        p, q, r = (self.verts[i] for i in tri)
        if (q - p).cross(r - p).length < 4e-10:
            # (a sliver where points crowd onto a lip: nothing to see, and its facing is only rounding)
            return
        out, name = judge(tri)
        if all(i in self.normals for i in tri):
            # (a triangle of the skin: it faces the way the skin there faced before the mouth was cut)
            out = sum((self.normals[i] for i in tri), Vector())
        self.face(tri, out, name)
        for k in range(3):
            p, q = tri[k], tri[(k + 1) % 3]
            if self.lips.get(p) and self.lips.get(p) == self.lips.get(q):
                self.sharp.add((min(p, q), max(p, q)))

    def zip(self, a, b, judge):
        """Two runs of points (index, where round the ring) on neighbouring rings, which start together and end
        together, joined by triangles in the order of where they are round the ring."""
        i = j = 0
        while i < len(a) - 1 or j < len(b) - 1:
            if j == len(b) - 1 or (i < len(a) - 1 and a[i + 1][1] <= b[j + 1][1]):
                self.tri((a[i][0], a[i + 1][0], b[j][0]), judge)
                i += 1
            else:
                self.tri((a[i][0], b[j + 1][0], b[j][0]), judge)
                j += 1

    def add(self, p, uv, part, high=0.0):
        self.verts.append(p)
        self.data.append(((uv[0], 1.0 - uv[1]), (high, 1.0 - part)))
        return len(self.verts) - 1

    def face(self, points, out, name):
        """A face wound so that its front (the side its points go round anticlockwise) is towards `out`."""
        ps = [self.verts[i] for i in points]
        n = Vector((0.0, 0.0, 0.0))
        for i in range(len(ps)):
            n += ps[i].cross(ps[(i + 1) % len(ps)])
        if n.length < 1e-12:
            return
        if n.dot(out) < 0.0:
            points = tuple(reversed(points))
        self.faces.append(tuple(points))
        self.out.append((Vector(out), name))
        self.count[name] = self.count.get(name, 0) + 1
        self.layers.append(self.layer)


# Which model is being built: "full", "low" or "game" (set by `make`).
LEVEL = "full"
# The game model (added 2026-11-18): points round its body, how closely its rings must follow the skin
# (metres), the longest step from one ring to the next (metres), how closely they must follow the step of the
# gill cover, and the longest step through the mouth.
GAME_AROUND = 20
GAME_TOL = 0.0015
GAME_STEP = 0.1
GAME_GILL_TOL = 0.004
GAME_MOUTH_STEP = 0.028


def rings(low):
    if LEVEL == "game":
        return game_rings()
    return even_rings(low)


def game_rings():
    """The game model's rings: from the full model's, as few as keep every point of the skin (sampled round
    it) within GAME_TOL of the straight line between the rings either side of it, never more than GAME_STEP
    apart (so the swimming bends smoothly) nor GAME_MOUTH_STEP through the mouth, with the two close rings
    where the lower jaw starts and one at the corner of the mouth."""
    fine = even_rings(False)
    angles = [k / 32 * TAU for k in range(17)]
    # (the step of the gill cover, a small edge, is held to a looser test: it is drawn by the shader too)
    smooth_skin = [[body_point(x, a, False) for a in angles] for x in fine]
    skin = [[body_point(x, a) for a in angles] for x in fine]

    def straight(i, k):
        for m in range(i + 1, k):
            t = (fine[m] - fine[i]) / (fine[k] - fine[i])
            for a in range(len(angles)):
                if (smooth_skin[m][a] - smooth_skin[i][a].lerp(smooth_skin[k][a], t)).length > GAME_TOL:
                    return False
                if (skin[m][a] - skin[i][a].lerp(skin[k][a], t)).length > GAME_GILL_TOL:
                    return False
        return True

    keep = [0]
    i = 0
    while i < len(fine) - 1:
        j = i + 1
        while j + 1 < len(fine):
            k = j + 1
            longest = GAME_MOUTH_STEP if fine[i] < JAW_BACK else GAME_STEP
            if fine[k] - fine[i] > longest + 1e-9 or not straight(i, k):
                break
            j = k
        keep.append(j)
        i = j
    xs = [fine[k] for k in keep]
    for extra in (JAW_FROM - 0.0012, JAW_FROM, MOUTH_TO):
        if min(abs(extra - x) for x in xs) > 0.0004:
            xs.append(extra)
    return sorted(xs)


def even_rings(low):
    xs = []
    x = BODY_FROM
    for until, step in ((0.20, 0.0035), (0.46, 0.0045), (1.18, 0.011), (BODY_TO, 0.0045)):
        if low:
            step *= 4.0
        n = max(1, round((until - x) / step))
        for i in range(n):
            xs.append(x + (until - x) * i / n)
        x = until
    xs.append(BODY_TO)
    # (two close rings where the lower jaw starts, so that the step from the whole head to the cut one is short)
    for extra in (JAW_FROM - 0.0012, JAW_FROM):
        if min(abs(extra - x) for x in xs) > 0.0004:
            xs.append(extra)
    return sorted(xs)


def cut_through(xm):
    return JAW_FROM <= xm <= JAW_BACK


def lined(m, tri):
    return max(m.data[q][1][0] for q in tri) > 0.0


def stitch(m, grid, around, judge, roof_first):
    """Rows of points round the body (each a list of (index, which lip, where round the ring, the index of a
    lip's twin for the inside of the mouth)) joined ring to ring: where both rings have both lips, each side of
    the cut is zipped on its own, so that the body and the jaw share the very same line of lip (the cut can
    cross several columns from one ring to the next); elsewhere point to point. The run from the left lip
    round by the belly to the right is the inside of the mouth if `roof_first` (the body), else the skin (the
    jaw); the other run is the other."""
    def runs(row):
        left = [k for k, (_, which, _, _) in enumerate(row) if which == 1]
        right = [k for k, (_, which, _, _) in enumerate(row) if which == -1]
        if not left or not right:
            return None

        def run(a, b, inside):
            out, k, base = [], a, 0.0
            while True:
                out.append((row[k][3] if inside else row[k][0], row[k][2] + base))
                if k == b:
                    return out
                k += 1
                if k == around:
                    k, base = 0, float(around)

        return run(left[0], right[0], roof_first), run(right[0], left[0], not roof_first)

    for r in range(len(grid) - 1):
        one, two = runs(grid[r]), runs(grid[r + 1])
        if one and two:
            m.zip(one[0], two[0], judge)
            m.zip(one[1], two[1], judge)
            continue
        for c in range(around):
            n = (c + 1) % around
            a, b, cc, d = grid[r][c][0], grid[r][n][0], grid[r + 1][n][0], grid[r + 1][c][0]
            m.tri((a, b, cc), judge)
            m.tri((a, cc, d), judge)


def body(m, low):
    around = GAME_AROUND if LEVEL == "game" else 28 if low else 96
    grid = []
    for xm in rings(low):
        row = []
        ring = mouth_ring(xm, around, False) if cut_through(xm) else None
        for c in range(around):
            angle = c / around * TAU
            uv = (xm / LENGTH, 0.5 + 0.5 * math.cos(angle))
            if ring:
                # (the head over the mouth: its underside the roof of the mouth)
                p, inside, which, where, normal = ring[c]
                at = m.add(p, uv, BODY, inside)
                twin = at
                if which:
                    # (a lip twice over: once for the skin, with the skin's normal, once for the roof of the mouth)
                    twin = m.add(p, uv, BODY, inside)
                    m.lips[at] = m.lips[twin] = which
                if normal:
                    m.normals[at] = normal
                row.append((at, which, where, twin))
            else:
                at = m.add(body_point(xm, angle), uv, BODY)
                row.append((at, 0, float(c), at))
        grid.append(row)

    def judge(tri):
        if lined(m, tri):
            # (the roof of the mouth faces down, into the mouth)
            return Vector((0.0, -1.0, 0.0)), "mouth roof"
        middle = sum((m.verts[q] for q in tri), Vector()) / 3.0
        return Vector((middle.x, middle.y, 0.0)), "body"

    stitch(m, grid, around, judge, True)
    # the tip of the snout and the end inside the tail: a fan each
    for row, xm, way in ((grid[0], 0.0, -1.0), (grid[-1], BODY_TO + 0.002, 1.0)):
        tip = m.add(Vector((0.0, 0.0, xm - HALF)), (xm / LENGTH, 0.5), BODY)
        for c in range(around):
            m.face((tip, row[c][0], row[(c + 1) % around][0]), Vector((0.0, 0.0, way)), "body")


def jaw(m, low):
    """The lower jaw: the skin the head had below the cut, on the same rings and angles as the body, closed over
    by the floor of the mouth; a cap at its tip (its back end comes to nothing at the belly)."""
    around = GAME_AROUND if LEVEL == "game" else 28 if low else 96
    xs = [xm for xm in rings(low) if cut_through(xm)]
    grid = []
    for xm in xs:
        row = []
        for c, (p, inside, which, where, normal) in enumerate(mouth_ring(xm, around, True)):
            at = m.add(p, (xm / LENGTH, 0.5 + 0.5 * math.cos(c / around * TAU)), JAW, inside)
            twin = at
            if which:
                # (a lip twice over: once for the skin, with the skin's normal, once for the floor of the mouth)
                twin = m.add(p, (xm / LENGTH, 0.5 + 0.5 * math.cos(c / around * TAU)), JAW, inside)
                m.lips[at] = m.lips[twin] = which
            if normal:
                m.normals[at] = normal
            row.append((at, which, where, twin))
        grid.append(row)

    def judge(tri):
        if lined(m, tri):
            # (the floor of the mouth faces up, into the mouth)
            return Vector((0.0, 1.0, 0.0)), "mouth floor"
        middle = sum((m.verts[q] for q in tri), Vector()) / 3.0
        at = middle.z + HALF
        return Vector((middle.x, middle.y - (roof(at) + bottom(at)) * 0.5, 0.0)), "lower jaw"

    stitch(m, grid, around, judge, False)
    xm = xs[0]
    tip = m.add(Vector((0.0, (roof(xm) + bottom(xm)) * 0.5, xm - HALF)), (xm / LENGTH, 0.25), JAW)
    for c in range(around):
        m.face((tip, grid[0][c][0], grid[0][(c + 1) % around][0]), Vector((0.0, 0.0, -1.0)), "lower jaw")


def cheeks(m, low):
    """The cheeks: on each side of the mouth, a little inside the lips, a wall from the upper lip to the lower
    (two skins back to back, one facing out, one in), the dark inside of the mouth seen from the side when it
    gapes. Built here as they hang with the mouth wide open, so that their faces have a size and a facing;
    each point says how far down from the upper lip to the lower it is (UV2.x, 0 to 1), and the shader folds
    them up to nothing along the line of the mouth, inside the head, as the mouth shuts."""
    rows = 3 if low or LEVEL == "game" else CHEEK_ROWS
    xs = [xm for xm in rings(low) if cut_through(xm) and xm <= MOUTH_TO]
    for sx in (1.0, -1.0):
        for facing in (1.0, -1.0):
            grid = []
            for xm in xs:
                at = lip(xm, sx)[0]
                base = Vector((at.x * CHEEK_IN, at.y, at.z))
                grid.append([m.add(swung(base, GAPE_TURN * jaw_turn(xm) * (k / rows)), (xm / LENGTH, k / rows), CHEEK, k / rows)
                             for k in range(rows + 1)])
            for r in range(len(grid) - 1):
                for k in range(rows):
                    a, b, c, d = grid[r][k], grid[r][k + 1], grid[r + 1][k + 1], grid[r + 1][k]
                    for tri in ((a, b, c), (a, c, d)):
                        m.tri(tri, lambda tri, way=Vector((sx * facing, 0.0, 0.0)): (way, "cheeks"))


# The gills (added 2026-11-18; the user: "The fish need modeled gills as well, well for relevant fish, so like when it
# opens its mouth wide you can see them"). This tuna's open mouth is walled at its sides by the cheeks, which hide
# all that is behind them, and it has no back wall to open into a throat: its roof and floor close to a line at the
# corner. So its gills are laid on the cheeks, in the back of the mouth where they are seen through it: on each side
# four gill arches running from the upper lip down to the lower, just outside the cheek (a share of the way out from
# the middle to the lip, the cheek being at CHEEK_IN), where they stand (metres behind the snout), and their bars,
# filaments and rakers (shares of the mouth's half width there).
ARCHES = (0.072, 0.086, 0.1, 0.114)
ARCH_OUT = 0.968
BAR = 0.02
FILAMENT = 0.15
RAKER = 0.06


def gills(m, low):
    """On each side of the mouth, on the cheek, four gill arches: a bar from the upper lip down the cheek to the lower,
    a fringe of filaments behind it, pale rakers before it, lying flat against the cheek. Like the cheeks, they are
    built as they hang with the mouth wide open, and the shader folds them away along the line of the mouth as it
    shuts: each point says how far down from the upper lip to the lower it is (UV2.x, 0 to 1), and UV.x is how far
    behind the snout its arch stands (a share of the length, as on a cheek). UV.y is what it is: 0 the bar, 0.4 to
    0.6 the filaments from their roots to their tips, 1 a raker. All of it is in the full model's second surface."""
    m.layer = 1
    game = LEVEL == "game"
    segments = 3 if low else 5 if game else 12
    sides = 3 if low or game else 6
    teeth = 1 if low else 2
    back = Vector((0.0, 0.0, 1.0))
    for sx in (1.0, -1.0):
        out = Vector((sx, 0.0, 0.0))
        for xm in ARCHES:
            at = lip(xm, sx)[0]
            chord = abs(at.x)
            bar, filament, raker = BAR * chord, FILAMENT * chord, RAKER * chord
            base = Vector((at.x * ARCH_OUT, at.y, at.z))
            turn = GAPE_TURN * jaw_turn(xm)

            def arch(s, base=base, turn=turn):
                return swung(base, turn * s)

            ss = [k / segments for k in range(segments + 1)]
            curve = [arch(s) for s in ss]
            uv_x = xm / LENGTH

            def tangent(k, curve=curve):
                return (curve[min(k + 1, segments)] - curve[max(k - 1, 0)]).normalized()

            # the bar: a tube down the cheek, closed at its ends
            tube = []
            for k, p in enumerate(curve):
                across = tangent(k).cross(out).normalized()
                tube.append([m.add(p + (out * math.cos(a) + across * math.sin(a)) * bar, (uv_x, 0.0), GILLS, ss[k])
                             for a in (q / sides * TAU for q in range(sides))])
            for k in range(segments):
                for q in range(sides):
                    w = (q + 1) % sides
                    quad = (tube[k][q], tube[k][w], tube[k + 1][w], tube[k + 1][q])
                    middle = sum((m.verts[i] for i in quad), Vector()) * 0.25
                    m.face(quad, middle - (curve[k] + curve[k + 1]) * 0.5, "gills")
            for k, way in ((0, -tangent(0)), (segments, tangent(segments))):
                cap = m.add(curve[k], (uv_x, 0.0), GILLS, ss[k])
                for q in range(sides):
                    m.face((cap, tube[k][q], tube[k][(q + 1) % sides]), way, "gills")
            # the filaments: a thin closed blade lying back along the cheek from the bar, its edge a comb of long and
            # short tips; the rakers: a pale tooth lying forward from it between each two points of it (each two skins
            # back to back, facing in and out)
            fine = [k / (segments * teeth) for k in range(segments * teeth + 1)]
            for skin in (1.0, -1.0):
                lift = out * skin * bar * 0.35
                roots, ends = [], []
                for j, s in enumerate(fine):
                    p = arch(s)
                    long = filament * (1.0 if j % teeth == 0 else 0.55) * (0.6 + 0.4 * math.sin(math.pi * s))
                    roots.append(m.add(p + back * bar * 0.6 + lift, (uv_x, 0.4), GILLS, s))
                    ends.append(m.add(p + back * long, (uv_x, 0.6), GILLS, s))
                for j in range(len(fine) - 1):
                    m.face((roots[j], roots[j + 1], ends[j + 1], ends[j]), out * skin, "gills")
                for k in range(segments):
                    a, b = curve[k], curve[k + 1]
                    s = (ss[k] + ss[k + 1]) * 0.5
                    tip = (a + b) * 0.5 - back * raker
                    tooth = (m.add(a - back * bar * 0.5 + lift * 0.8, (uv_x, 1.0), GILLS, ss[k]),
                             m.add(b - back * bar * 0.5 + lift * 0.8, (uv_x, 1.0), GILLS, ss[k + 1]),
                             m.add(tip, (uv_x, 1.0), GILLS, s))
                    m.face(tooth, out * skin, "gills")
    m.layer = 0


def eye_skin(sx):
    """A point of the skin `xm` behind the snout and `y` up, on the side `sx`."""
    def on_skin(xm, y):
        up, down, _ = outline(xm)
        c = max(-1.0, min(1.0, y / (up if y >= 0.0 else down)))
        return body_point(xm, sx * math.acos(c))
    return on_skin


def eye_frame(sx):
    """Where the middle of the eye lies on the skin, and the way the skin faces there (as the shader has it:
    the EYE line)."""
    on_skin = eye_skin(sx)
    xe, ye = EYE_AT
    here = on_skin(xe, ye)
    out = (on_skin(xe + 0.004, ye) - on_skin(xe - 0.004, ye)).cross(on_skin(xe, ye + 0.004) - on_skin(xe, ye - 0.004))
    out.normalize()
    if out.x * sx < 0.0:
        out = -out
    return here, out


def eye(m, sx, low):
    """A low dome lying on the skin of the head."""
    spokes = 28 if LEVEL == "game" else 12 if low else 40
    steps = 3 if low or LEVEL == "game" else 12
    xe, ye = EYE_AT
    on_skin = eye_skin(sx)
    here, out = eye_frame(sx)
    middle = m.add(here + out * 0.0066, (0.0, 0.0), EYE)
    last = None
    for k in range(1, steps + 1):
        r = k / steps
        row = []
        for s in range(spokes):
            a = s / spokes * TAU
            p = on_skin(xe + math.cos(a) * EYE_RADIUS * r, ye + math.sin(a) * EYE_RADIUS * r)
            row.append(m.add(p + out * (0.006 * (1.0 - r * r) + 0.0006 * (1.0 - r)), (r, 0.0), EYE))
        for s in range(spokes):
            n = (s + 1) % spokes
            if last is None:
                m.face((middle, row[s], row[n]), out, "eyes")
            else:
                m.face((last[s], row[s], row[n], last[n]), out, "eyes")
        last = row


def blade(m, part, name, point, place, facing, thick, nt, nu, high=None):
    """A fin: a thin closed blade. `point(t, u)` is a place in the fin's own flat (t 0 at its root to 1 at
    its tip, u 0 at its leading edge to 1 at its trailing edge), `place` puts that in the model, `facing`
    is the way one of its two skins faces. It is `thick` at its root, a foil across (nothing at either
    edge), thinning to nothing at its tip."""
    for side in (1.0, -1.0):
        grid = []
        for ti in range(nt + 1):
            t = ti / nt
            row = []
            for ui in range(nu + 1):
                u = ui / nu
                foil = 2.6 * math.sqrt(u) * (1.0 - u)
                swell = thick * (1.0 - t) ** 0.7 * foil
                p = place(point(t, u)) + facing * (side * swell * 0.5)
                row.append(m.add(p, (t, u), part, high(t, u) if high else 0.0))
            grid.append(row)
        for ti in range(nt):
            for ui in range(nu):
                m.face((grid[ti][ui], grid[ti][ui + 1], grid[ti + 1][ui + 1], grid[ti + 1][ui]), facing * side, name)


def bezier(p0, p1, p2, t):
    a = 1.0 - t
    return (a * a * p0[0] + 2 * a * t * p1[0] + t * t * p2[0], a * a * p0[1] + 2 * a * t * p1[1] + t * t * p2[1])


def swept(lead, trail, reach=0.985):
    """A fin drawn by its leading and trailing edges (three points each, root to tip; they meet at the tip)."""
    def point(t, u):
        a = bezier(*lead, t * reach)
        b = bezier(*trail, t * reach)
        return (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)
    return point


def upright(p):
    """A place in the flat of the middle fins (metres behind the snout, metres up) in the model."""
    return Vector((0.0, p[1], p[0] - HALF))


SIDE = Vector((1.0, 0.0, 0.0))


def cut(full, d, game, exact=False):
    """How many rows a fin is cut into: the full model's `full`, the low one's `full // d`, the game model's
    `game` (`exact` is for the calls' sake: the bluefin tuna's script, which shares them, scales the rest)."""
    return game if LEVEL == "game" else full // d


def fins(m, low):
    d = 3 if low else 1
    # The first dorsal: thirteen spines, the first the tallest, the edge falling away steeply behind and
    # scalloped between the spines; each leans back.
    spines = 13
    lean = math.radians(24.0)

    def dorsal_high(u):
        fall = 0.14 + 0.86 * (1.0 - u) ** 2.3
        scallop = 0.9 + 0.1 * abs(math.cos(math.pi * u * spines))
        return 0.14 * fall * scallop * (0.7 + 0.3 * smooth(0.0, 0.05, u))

    def dorsal_point(t, u):
        xm = 0.47 + 0.325 * u
        high = dorsal_high(u) * t
        return (xm + math.sin(lean) * high, top(xm) - 0.012 + math.cos(lean) * high * 1.0 + 0.012 * t)

    blade(m, DORSAL, "first dorsal", dorsal_point, upright, SIDE, 0.007, cut(12, d, 1, exact=True), cut(spines * 6, d, spines * 2, exact=True),
          high=lambda t, u: (dorsal_high(u) * math.cos(lean) + 0.012) * t)
    # The second dorsal and the anal fin: long sickles, narrow at the root and strongly arched: up and then far
    # back in a curve (the user, 2026-11-17: "The tunas yellow fins should be skinnier abd more arched").
    yd = top(0.85)
    tip = (1.21, yd + 0.33)
    blade(m, SICKLE, "second dorsal", swept(((0.80, top(0.80) - 0.014), (0.83, yd + 0.4), tip),
                                              ((0.862, top(0.862) - 0.014), (0.9, yd + 0.29), tip)),
          upright, SIDE, 0.011, cut(42, d, 14), cut(12, d, 2, exact=True))
    ya = bottom(0.93)
    tip = (1.29, ya - 0.32)
    blade(m, SICKLE, "anal", swept(((0.885, bottom(0.885) + 0.014), (0.915, ya - 0.4), tip),
                                    ((0.947, bottom(0.947) + 0.014), (0.985, ya - 0.29), tip)),
          upright, SIDE, 0.011, cut(42, d, 14), cut(12, d, 2, exact=True))
    # The finlets: nine above, eight below, smaller towards the tail.
    for way, first, count in ((1.0, 0.927, 9), (-1.0, 1.008, 8)):
        for k in range(count):
            share = k / (count - 1)
            x0 = first + (1.272 - first) * share
            chord = 0.03 - 0.01 * share
            high = (0.032 - 0.014 * share) * way
            y0 = (top(x0) if way > 0.0 else bottom(x0)) - 0.004 * way
            y1 = (top(x0 + chord) if way > 0.0 else bottom(x0 + chord)) - 0.004 * way
            tip = (x0 + chord * 1.55, y1 + high)
            blade(m, FINLET, "finlets", swept(((x0, y0), (x0 + chord * 0.6, y0 + high * 0.7), tip),
                                               ((x0 + chord, y1), (x0 + chord * 1.3, y1 + high * 0.25), tip), 0.97),
                  upright, SIDE, 0.0022, cut(8, min(d, 2), 2, exact=True), cut(5, min(d, 2), 2, exact=True))
    # The tail: a tall stiff crescent, two lobes that meet along the middle line.
    for way in (1.0, -1.0):
        tip = (1.5, 0.232 * way)
        blade(m, TAIL, "tail", swept(((1.28, 0.0), (1.36, 0.125 * way), tip),
                                      ((1.395, 0.0), (1.458, 0.082 * way), tip)),
              upright, SIDE, 0.017, cut(40, d, 12), cut(14, d, 3, exact=True))
    for sx in (1.0, -1.0):
        # The pectoral fins: long scythes held out like wings, swept back and a little down.
        up, down, wide = outline(0.40)
        root = Vector((sx * (wide - 0.034), -0.03, 0.385 - HALF))
        sweep = math.radians(34.0)
        span = Vector((sx * math.sin(sweep), -0.2, math.cos(sweep))).normalized()
        chord = Vector((0.0, -0.8, 1.0)).normalized()
        facing = span.cross(chord).normalized()
        if facing.y < 0.0:
            facing = -facing

        def pectoral_point(t, u):
            t *= 0.985
            lead = 0.07 * t * t
            wide_here = 0.072 * (1.0 - t) ** 0.75 * (1.0 + 0.5 * t) + 0.004
            return (0.41 * t, lead + wide_here * u)

        blade(m, PECTORAL, "pectorals", pectoral_point,
              lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.012, cut(40, d, 10), cut(12, d, 2, exact=True))
        # The pelvic fins: small, under the pectorals, pointing back and down.
        root = Vector((sx * 0.032, bottom(0.455) + 0.014, 0.455 - HALF))
        span = Vector((sx * 0.3, -0.5, 0.82)).normalized()
        chord = Vector((0.0, 0.12, 1.0)).normalized()
        facing = span.cross(chord).normalized()
        if facing.x * sx < 0.0:
            facing = -facing

        def pelvic_point(t, u):
            t *= 0.97
            return (0.115 * t, 0.02 * t * t + (0.042 * (1.0 - t) ** 0.8 + 0.003) * u)

        blade(m, PELVIC, "pelvics", pelvic_point,
              lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.007, cut(14, d, 4), cut(8, d, 2, exact=True))


def make(name, low, level=None):
    """Builds one model. The full and the low model come out as two objects: the body as it always was, and its
    gills and the back of its throat (`name`_gills), which are written into the same .glb as a second surface
    (`export`); the game model is one object."""
    global LEVEL
    LEVEL = level or ("low" if low else "full")
    m = Mesh()
    body(m, low)
    jaw(m, low)
    cheeks(m, low)
    for sx in (1.0, -1.0):
        eye(m, sx, low)
    fins(m, low)
    m.split = len(m.verts)
    gills(m, low)
    if LEVEL == "game":
        return mesh_object(name, m, list(range(len(m.faces))), 0, len(m.verts), "tuna", (0.45, 0.55, 0.7, 1.0)), None
    first = mesh_object(name, m, [i for i, layer in enumerate(m.layers) if layer == 0], 0, m.split, "tuna", (0.45, 0.55, 0.7, 1.0))
    inner = mesh_object(name + "_gills", m, [i for i, layer in enumerate(m.layers) if layer == 1], m.split, len(m.verts),
                        "tuna_gills", (0.4, 0.05, 0.06, 1.0))
    return first, inner


def mesh_object(name, m, faces, lo, hi, material_name, colour):
    """A Blender object of the faces `faces` of `m`, whose points are `lo` to `hi`."""
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) for p in m.verts[lo:hi]], [], [tuple(i - lo for i in m.faces[f]) for f in faces])
    # (the lips are sharp: the skin keeps its own smooth shading up to them, as it had before the mouth was cut)
    for edge in mesh.edges:
        if tuple(sorted(i + lo for i in edge.vertices)) in m.sharp:
            edge.use_edge_sharp = True
    # (every layer made first, then each looked up by name: making one moves the others)
    mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.new(name="UV2")
    uv = mesh.uv_layers["UVMap"].data
    uv2 = mesh.uv_layers["UV2"].data
    for poly in mesh.polygons:
        for corner, vi in enumerate(poly.vertices):
            d = m.data[vi + lo]
            uv[poly.loop_start + corner].uv = d[0]
            uv2[poly.loop_start + corner].uv = d[1]
    material = bpy.data.materials.get(material_name) or bpy.data.materials.new(material_name)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = colour
    material.diffuse_color = colour
    mesh.materials.append(material)
    # (smooth, but for the gills' filaments and rakers: thin folded blades, flat so that each face keeps its own
    # facing)
    for poly in mesh.polygons:
        poly.use_smooth = not (m.out[faces[poly.index]][1] == "gills" and m.data[m.faces[faces[poly.index]][0]][0][1] < 0.9)
    # (each point of the skin where the mouth is cut, the lips too, has the normal the skin had there before)
    mesh.normals_split_custom_set_from_vertices([to_b(m.normals[i]) if i in m.normals else (0.0, 0.0, 0.0) for i in range(lo, hi)])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    print("BUILT %s verts=%d tris=%d" % (name, len(mesh.vertices), tris))
    winding(name, mesh, m, faces)
    return obj


def winding(name, mesh, m, faces):
    """Nothing inside out: the skin of the body faces away from its middle line (the roof of the mouth down,
    into the mouth), the lower jaw's away from its own (the floor of the mouth up), each skin of a fin away
    from the fin's own flat, an eye out from the head, each part of a gill out of itself, each skin of the back
    of the throat its own way (Blender's front is the side a face's normal is on)."""
    bad = {}
    count = {}
    for poly in mesh.polygons:
        out, group = m.out[faces[poly.index]]
        count[group] = count.get(group, 0) + 1
        if poly.normal.dot(to_b(out)) <= 0.0:
            bad[group] = bad.get(group, 0) + 1
            if os.environ.get("WHY"):
                print("  wrong %s area=%.3g at %s" % (group, poly.area, tuple(round(v, 4) for v in poly.center)))
    told = ["%s %d/%d wrong" % (group, bad.get(group, 0), n) for group, n in count.items()]
    print("WINDING %s: %s: %s" % (name, "ok" if not bad else "INSIDE OUT", ", ".join(told)))


def export(obj, inner, path):
    """Writes `obj` to `path`, and `inner` (if any) into the same .glb as a second primitive of its mesh, so that
    Godot reads one mesh of two surfaces whose first is exactly what `obj` alone would have been."""
    export_one(obj, path)
    if inner is None:
        return
    extra = os.path.join(HERE, "_gills.glb")
    export_one(inner, extra)
    merge_glb(path, extra)
    os.remove(extra)


def _read_glb(path):
    with open(path, "rb") as f:
        data = f.read()
    json_length = struct.unpack_from("<I", data, 12)[0]
    gltf = json.loads(data[20:20 + json_length])
    at = 20 + json_length
    bin_length = struct.unpack_from("<I", data, at)[0]
    return gltf, bytearray(data[at + 8:at + 8 + bin_length])


def merge_glb(path, extra):
    """Adds the first mesh of the .glb `extra` to the first mesh of the .glb `path` as more primitives (its
    accessors, buffer views, materials and binary data appended after `path`'s own, which are left as they were)."""
    base, data = _read_glb(path)
    more, more_data = _read_glb(extra)
    data += b"\0" * (-len(data) % 4)
    shift = len(data)
    views = len(base["bufferViews"])
    accessors = len(base["accessors"])
    materials = len(base.setdefault("materials", []))
    for view in more["bufferViews"]:
        view = dict(view)
        view["buffer"] = 0
        view["byteOffset"] = view.get("byteOffset", 0) + shift
        base["bufferViews"].append(view)
    for accessor in more["accessors"]:
        accessor = dict(accessor)
        accessor["bufferView"] += views
        base["accessors"].append(accessor)
    base["materials"] += more.get("materials", [])
    for primitive in more["meshes"][0]["primitives"]:
        primitive = dict(primitive)
        primitive["attributes"] = {k: v + accessors for k, v in primitive["attributes"].items()}
        if "indices" in primitive:
            primitive["indices"] += accessors
        if "material" in primitive:
            primitive["material"] += materials
        base["meshes"][0]["primitives"].append(primitive)
    data += more_data
    data += b"\0" * (-len(data) % 4)
    base["buffers"][0]["byteLength"] = len(data)
    text = json.dumps(base, separators=(",", ":")).encode("utf-8")
    text += b" " * (-len(text) % 4)
    total = 12 + 8 + len(text) + 8 + len(data)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(text), 0x4E4F534A))
        f.write(text)
        f.write(struct.pack("<II", len(data), 0x004E4942))
        f.write(data)


def export_one(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", export_yup=True, use_selection=True,
        export_animations=False, export_texcoords=True,
    )


def render(folder, made):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_cavity = True
    scene.display.shading.show_backface_culling = True
    scene.render.resolution_x, scene.render.resolution_y = 1400, 800
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    # (Blender space: the fish lies along Y, its nose at +Y, up is Z)
    views = [("left", (1, 0, 0), (0, 0, 0), 1.7), ("right", (-1, 0, 0), (0, 0, 0), 1.7),
             ("front", (0, 1, 0), (0, 0, 0), 1.1), ("back", (0, -1, 0), (0, 0, 0), 1.1),
             ("top", (0.001, 0, 1), (0, 0, 0), 1.7), ("under", (0.001, 0, -1), (0, 0, 0), 1.7),
             ("head", (0.8, 0.5, 0.2), (0, 0.5, 0), 0.6), ("tail", (0.7, -0.6, 0.3), (0, -0.55, 0), 0.7),
             ("chin", (0.4, 0.6, -0.7), (0, 0.63, -0.03), 0.3)]
    for low, obj in ((False, made[0]), (True, made[1])):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if low and view not in ("left", "head"):
                continue
            offset = Vector(direction).normalized() * 40.0
            camera.data.ortho_scale = frame
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % ("lo_" if low else "", view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    full, full_inner = make("yellowfin_tuna", False)
    low, low_inner = make("yellowfin_tuna_lo", True)
    print("SHADER HINGE vec2(%.4f, %.4f)" % HINGE)
    os.makedirs(OUT, exist_ok=True)
    export(full, full_inner, os.path.join(OUT, "yellowfin_tuna.glb"))
    export(low, low_inner, os.path.join(OUT, "yellowfin_tuna_lo.glb"))
    # (the game model, built after the others are written out, so that they come out as they always did)
    game, _ = make("yellowfin_tuna_game", False, "game")
    export(game, None, os.path.join(OUT, "yellowfin_tuna_game.glb"))
    here, out = eye_frame(1.0)
    print("EYE yellowfin_tuna: EYE_MID=vec3(%.5f, %.5f, %.5f) EYE_OUT=vec3(%.5f, %.5f, %.5f) EYE_RADIUS=%.4f" % (tuple(here) + tuple(out) + (EYE_RADIUS,)))
    # (in the .blend, each model's gills ride with it)
    for owner, inner in ((full, full_inner), (low, low_inner)):
        inner.parent = owner
    low.location.x = 1.5
    game.location.x = -1.5
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "yellowfin_tuna.blend"))
    low.location.x = 0.0
    game.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low])


if __name__ == "__main__":
    main()
