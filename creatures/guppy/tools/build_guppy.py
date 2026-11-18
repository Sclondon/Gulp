"""Builds the guppy (creatures/guppy), female and male, and exports them for Godot.

Run from the game's root:
    blender --background --python creatures/guppy/tools/build_guppy.py
    blender --background --python creatures/guppy/tools/build_guppy.py -- <preview folder>   # with pictures

Writes creatures/guppy/models/guppy_female.glb and guppy_male.glb (the full models, for one seen close), and
guppy_female_lo.glb and guppy_male_lo.glb (far off, phones), guppy_female_game.glb and guppy_male_game.glb (the game
models: Twilight Princess weight, several hundred triangles spent on the outline, the eye, the mouth and the fins'
edges, built from the same curves with fewer, better placed rings and points), and the editable
creatures/guppy/tools/guppy.blend (all six; this folder has a .gdignore). Each is one still mesh (the full ones keep
their throat and gills in a second surface, so that their first is exactly as it was before the gills): the shader (guppy.gdshader)
draws every marking (the male's colours and patterns are its settings) and swims it, ripples its fins and
opens its mouth. It prints a WINDING line for each: the check that nothing is inside out.

The guppy (Poecilia reticulata), a small livebearer, built from the species (no picture was traced or copied):

- THE FEMALE, 0.045 m from the tip of its jaw to the end of its tail: the bigger fish, a full body with a
  rounded belly deepest under the dorsal fin, a short head with a big eye and a small upturned mouth, a small
  rounded dorsal fin set well back, a small fan-shaped anal fin, small pelvics, a rounded tail.
- THE MALE, 0.04 m: a small slender body (a little over half its length) carrying a big fan tail as long as
  the body, a delta whose back edge is a little rounded; a long flag of a dorsal fin that trails back over the
  tail; the anal fin made into a gonopodium, a thin rod lying back under the belly.
- THE MOUTH: the head ahead of the jaw's hinge is in two closed pieces that meet along the line of the mouth,
  which runs from the tip of the snout down and back. The upper one is part of the body: its underside is the
  roof of the mouth, and a wall behind it is the throat. The LOWER JAW is a part of its own, its top the floor
  of the mouth; the shader swings it down about its hinge (`gape`).
- THE FINS, each a thin closed blade (two skins that meet at its edges).

Everything here is built in BODY LENGTHS (the tip of the jaw at 0, the end of the tail at 1), in Godot's axes
(Y up, X to its left side, its nose at -Z), with the origin on its middle line half way along; it is multiplied
by the model's length (metres) only as it is written out. `xm` below is body lengths behind the tip of the jaw.

What a point is, for the shader: UV2.y the part (0 body, 1 the dorsal fin, 2 the anal fin or gonopodium, 3 the
tail, 4 a pectoral fin, 5 a pelvic fin, 6 an eye, 7 the lower jaw, 8 a gill arch). UV2.x: 1 inside the mouth (its roof,
floor and throat), 0 elsewhere. THE GILLS: behind the mouth the throat is a short tunnel back to a dark wall, four
gill arches a side standing in it, seen only through the open mouth. UV, on the body and the jaw: x how far along (0 jaw to 1 tail end), y how high on its
side (1 the ridge of the back, 0.5 its middle line, 0 the keel of the belly); on a fin: x from its root (0) to
its tip or back edge (1), y from its leading (or upper) edge (0) to its trailing (or lower) edge (1); on an
eye: x from its middle (0) to its rim (1). (The glTF writer flips V: what is written here is 1 - v, so that
Godot reads v.)

The numbers in SHAPES that the shader needs (the hinge, the eye, the tail's root) are set in it by guppy.gd's
TYPES (in body lengths): change one, change the other. The script prints them for each model (SHADER line).
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

HALF = 0.5
BODY, DORSAL, ANAL, TAIL, PECTORAL, PELVIC, EYE, JAW, GILL = range(9)
TAU = math.tau

# Which model is being built: "full", "low" or "game" (the game model: Twilight Princess weight, built from
# the same curves with fewer, better placed rings and points; see GAME_* below).
LEVEL = ["full"]


def game():
    return LEVEL[0] == "game"


def pick(normal, for_game):
    """A count: `for_game` in the game model, `normal` (the full or the low model's own) otherwise."""
    return for_game if game() else normal


# Each model: its length (metres, jaw to tail end); its outline (body lengths behind the jaw, half its depth
# above its middle line, half its depth below, half its width); where its body ends inside the tail; the line
# of the mouth (y at the tip, slope), how far back the lower jaw runs (its hinge), the eye (place, radius),
# the gill cover's edge (x at the middle, how fast it curves forward), and where the tail fin's root is.
SHAPES = {
    "female": {
        "length": 0.045,
        "profile": [
            (0.0, 0.0, 0.0, 0.0),
            (0.004, 0.006, 0.009, 0.006),
            (0.014, 0.013, 0.029, 0.016),
            (0.030, 0.024, 0.050, 0.028),
            (0.060, 0.041, 0.073, 0.040),
            (0.100, 0.062, 0.090, 0.052),
            (0.160, 0.076, 0.110, 0.062),
            (0.240, 0.086, 0.126, 0.068),
            (0.320, 0.090, 0.132, 0.070),
            (0.400, 0.088, 0.124, 0.066),
            (0.480, 0.080, 0.100, 0.056),
            (0.560, 0.068, 0.074, 0.044),
            (0.640, 0.056, 0.056, 0.034),
            (0.710, 0.048, 0.046, 0.026),
            (0.760, 0.045, 0.043, 0.018),
            (0.785, 0.034, 0.033, 0.010),
            (0.800, 0.004, 0.004, 0.002),
        ],
        "body_to": 0.8, "mouth": (0.002, -0.36), "mouth_to": 0.04, "jaw_to": 0.042,
        "eye": (0.09, 0.018), "eye_radius": 0.037, "gill": (0.2, 7.0), "joint": 0.775,
    },
    "male": {
        "length": 0.04,
        "profile": [
            (0.0, 0.0, 0.0, 0.0),
            (0.004, 0.006, 0.009, 0.006),
            (0.014, 0.012, 0.027, 0.015),
            (0.030, 0.022, 0.045, 0.025),
            (0.055, 0.035, 0.059, 0.033),
            (0.090, 0.052, 0.066, 0.039),
            (0.140, 0.060, 0.074, 0.042),
            (0.200, 0.064, 0.076, 0.042),
            (0.270, 0.064, 0.072, 0.040),
            (0.340, 0.060, 0.062, 0.036),
            (0.410, 0.052, 0.050, 0.030),
            (0.470, 0.044, 0.040, 0.024),
            (0.510, 0.040, 0.036, 0.018),
            (0.535, 0.032, 0.030, 0.010),
            (0.548, 0.004, 0.004, 0.002),
        ],
        "body_to": 0.548, "mouth": (0.002, -0.36), "mouth_to": 0.035, "jaw_to": 0.037,
        "eye": (0.074, 0.013), "eye_radius": 0.031, "gill": (0.16, 8.0), "joint": 0.525,
    },
}

BODY_FROM = 0.003
SHAPE = {}
_XS = []
_CURVES = []
AROUND = [32]
BODY_TO = MOUTH_TO = JAW_TO = EYE_RADIUS = JOINT = 0.0
EYE_AT = (0.0, 0.0)


def use(name):
    """Makes `name` the model being built: its outline and its numbers."""
    global BODY_TO, MOUTH_TO, JAW_TO, EYE_AT, EYE_RADIUS, JOINT, GILL_TO, GILL_FROM, GILL_STEP, WALL_UP
    SHAPE.clear()
    SHAPE.update(SHAPES[name])
    SHAPE["name"] = name
    BODY_TO = SHAPE["body_to"]
    MOUTH_TO = SHAPE["mouth_to"]
    JAW_TO = SHAPE["jaw_to"]
    EYE_AT = SHAPE["eye"]
    EYE_RADIUS = SHAPE["eye_radius"]
    JOINT = SHAPE["joint"]
    profile = SHAPE["profile"]
    _XS[:] = [p[0] for p in profile]
    _CURVES.clear()
    for column in (1, 2, 3):
        ys = [p[column] for p in profile]
        _CURVES.append((ys, _slopes(_XS, ys)))
    # the gills: from a little ahead of the gill cover's edge forward; where the old wall across the back
    # of the full model's mouth is lifted to as it opens (as the shader has them: guppy.gd's SHAPES)
    GILL_TO = gill_x(-0.01) - 0.014
    GILL_FROM = JAW_TO + 0.4 * (GILL_TO - JAW_TO)
    GILL_STEP = (GILL_TO - 0.017 - GILL_FROM) / 3.0
    WALL_UP = 0.5 * top(JAW_TO)


def GAME_SPANS():
    """The game model's rings: (as far as, a step) from the snout back."""
    return ((JAW_TO, 0.014), (JAW_TO + 0.18, 0.045), (BODY_TO - 0.04, 0.08), (BODY_TO, 0.02))


def mouth_y(xm):
    a, b = SHAPE["mouth"]
    return a + b * xm


def gill_x(y):
    a, b = SHAPE["gill"]
    return a - b * (y + 0.008) ** 2


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
        out.append(max(a + b, 0.001))
    return out


def top(xm):
    return outline(xm)[0]


def bottom(xm):
    return -outline(xm)[1]


def body_point(xm, angle):
    """A point of the skin: `angle` round the body from the ridge of the back (0) by its left side (a
    quarter turn) to the keel of the belly (half a turn)."""
    up, down, wide = outline(xm)
    c = math.cos(angle)
    s = math.sin(angle)
    y = c * (up if c >= 0.0 else down)
    side = math.copysign(abs(s) ** 0.8, s) * wide
    # the top of the head a little flattened
    side *= 1.0 + 0.08 * smooth(0.3, 0.9, c) * (1.0 - smooth(0.1, 0.25, xm))
    # the mouth: a groove from the tip of the jaw back to its corner
    if xm < MOUTH_TO + 0.01:
        groove = math.exp(-((y - mouth_y(xm)) / 0.004) ** 2) * smooth(0.003, 0.012, xm) * (1.0 - smooth(MOUTH_TO - 0.01, MOUTH_TO + 0.003, xm))
        side *= 1.0 - 0.12 * groove
    # the gill cover: it stands a little proud of the body behind its edge
    behind = xm - gill_x(y)
    if behind > 0.0 and wide > 0.01:
        mask = smooth(-0.97, -0.82, c) * (1.0 - smooth(0.45, 0.65, c))
        step = 0.003 * smooth(0.0, 0.006, behind) * math.exp(-behind / 0.03) * mask
        side *= 1.0 - step / wide
    return Vector((side, y, xm - HALF))


def skin(xm, y, sx):
    """The point of the skin at `xm` and height `y`, on the left side (sx 1) or the right (-1)."""
    up, down, _ = outline(xm)
    c = max(-1.0, min(1.0, y / (up if y >= 0.0 else down)))
    return body_point(xm, sx * math.acos(c))


def to_b(p):
    """Godot's axes to Blender's, and body lengths to metres."""
    s = SHAPE["length"]
    return Vector((p.x * s, -p.z * s, p.y * s))


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        # per point: (uv, uv2)
        self.data = []
        # per face: the way it should face, and which surface it is in (see SURFACE)
        self.out = []
        self.surface = []
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
        self.faces.append(tuple(points))
        self.out.append((Vector(out), name))
        self.surface.append(SURFACE[0])
        self.count[name] = self.count.get(name, 0) + 1


# Which surface the faces being made go in. The full model keeps its first surface exactly as it was
# before the gills were added (so that Godot's importer makes the same thinned LOD meshes of it, and it
# looks the same at every distance); its throat and gills are a second surface. The low and the game
# models are one surface each.
SURFACE = [0]
# (the full model's throat is built after everything else: the opening it starts from, kept here)
THROAT = []


def rings(low):
    xs = []
    x = BODY_FROM
    spans = ((JAW_TO, 0.006), (JAW_TO + 0.18, 0.012), (BODY_TO - 0.04, 0.022), (BODY_TO, 0.008))
    if game():
        # (the game model: close at the snout and the tail's wrist, where the outline turns, few along the flank)
        spans = GAME_SPANS()
    for until, step in spans:
        if low:
            step *= 4.0
        n = max(1, round((until - x) / step))
        for i in range(n):
            xs.append(x + (until - x) * i / n)
        x = until
    xs.append(BODY_TO)
    return xs


def raw_lip_angle(xm):
    up, down, _ = outline(xm)
    y = mouth_y(xm)
    return math.acos(max(-0.999, min(0.999, y / (up if y >= 0.0 else down))))


def lip_angle(xm):
    """How far round the body from the ridge of the back the line of the mouth is, at `xm` (eased, towards
    the hinge, onto the column of the body's points nearest to it, so that the lip meets that column)."""
    snap = round(raw_lip_angle(JAW_TO) / (TAU / AROUND[0])) * TAU / AROUND[0]
    return raw_lip_angle(xm) + (snap - raw_lip_angle(JAW_TO)) * smooth(0.0, JAW_TO, xm)


def inside_point(xm, across, hollow):
    """A point of the roof (`hollow` up) or the floor (`hollow` down) of the mouth at `xm`: `across` 1 at the
    left lip, -1 at the right, the surface arched away from the line of the mouth between them."""
    lip = body_point(xm, lip_angle(xm))
    y = lip.y + hollow * (1.0 - across * across) * smooth(0.16 * JAW_TO, 0.47 * JAW_TO, xm)
    return Vector((lip.x * across, y, xm - HALF))


# As the shader has it: the gills. The throat runs back from the mouth to GILL_TO, a little ahead of the gill
# cover's edge; the four gill arches a side stand in it from GILL_FROM back.
# (each model's: set by use(), from where its gill cover's edge is)
GILL_TO = GILL_FROM = GILL_STEP = WALL_UP = 0.0


def tunnel_section(xm):
    """The throat's section at `xm`: the top and bottom of it and its half width, well inside the skin (and
    inside the low model's flat-sided skin too)."""
    up, down, wide = outline(xm)
    return 0.5 * up, -0.7 * down, 0.68 * wide


def throat(m, top, bottom):
    """The throat: a short tunnel from the back of the mouth (its opening is the roof's last arch, `top`, and
    the body's points under the line of the mouth at the hinge, `bottom`, both from the left lip to the right)
    back past the gill arches, closed by a dark wall behind them. All of it is inside the mouth (UV2.x 1), so
    the shader colours it as the inside of the mouth; shut, the head hides it."""
    loop = list(top) + list(reversed(bottom))
    ps = [m.verts[q] for q in loop]
    low_y = min(p.y for p in ps)
    high_y = max(p.y for p in ps)
    wide_x = max(abs(p.x) for p in ps)
    shape = [(p.x / wide_x, (p.y - 0.5 * (low_y + high_y)) / (0.5 * (high_y - low_y))) for p in ps]
    # (its own points: their UV's y is 0, which tells the shader they are the throat's, not the full
    # model's old wall across the back of the mouth, whose points' is 0.5)
    rows = [[m.add(p, (JAW_TO, 0.0), BODY, 1.0) for p in ps]]
    middles = [Vector((0.0, 0.5 * (low_y + high_y), JAW_TO - HALF))]
    for xm in (JAW_TO + 0.35 * (GILL_TO - JAW_TO), GILL_TO):
        high, low_, half_w = tunnel_section(xm)
        centre = 0.5 * (high + low_)
        reach = 0.5 * (high - low_)
        rows.append([m.add(Vector((half_w * s[0], centre + reach * s[1], xm - HALF)), (xm, 0.0), BODY, 1.0) for s in shape])
        middles.append(Vector((0.0, centre, xm - HALF)))
    n = len(loop)
    for r in range(len(rows) - 1):
        for k in range(n):
            j = (k + 1) % n
            a, b, c, d = rows[r][k], rows[r][j], rows[r + 1][j], rows[r + 1][k]
            # (as two triangles, each turned to face the tunnel's middle line)
            for tri in ((a, b, c), (a, c, d)):
                middle = sum((m.verts[q] for q in tri), Vector()) / 3.0
                axis = middles[r].lerp(middles[r + 1], 0.5)
                m.face(tri, Vector((axis.x - middle.x, axis.y - middle.y, 0.0)), "throat")
    # the wall behind the gills: a fan, facing the mouth
    end = m.add(middles[-1] + Vector((0.0, 0.0, 0.002)), (GILL_TO, 0.0), BODY, 1.0)
    for k in range(n):
        m.face((end, rows[-1][k], rows[-1][(k + 1) % n]), Vector((0.0, 0.0, -1.0)), "throat end")


def gills(m, low):
    """Four gill arches a side, standing in the throat: each a curved bar from the top of the throat to its
    floor, bent back in the middle (a "<" opening forward), as a thin closed blade: its inner, front edge the
    pale gill rakers, then the bar, then the fringe of red filaments reaching back and out to the throat's wall.
    UV x from its top (0) to its foot (1), y from the rakers (0) to the filaments' tips (1). Inside the head:
    only seen through the open mouth."""
    nt = 2 if low else pick(10, 3)
    nu = 1 if low else pick(3, 1)
    for sx in (1.0, -1.0):
        for k in range(4):
            at = GILL_FROM + GILL_STEP * k
            high, low_, half_w = tunnel_section(at)
            centre = 0.5 * (high + low_)
            reach = 0.5 * (high - low_)

            def place(t, u, at=at, centre=centre, reach=reach, half_w=half_w, sx=sx):
                y = centre + reach * 0.88 * (1.0 - 2.0 * t)
                wall = half_w * 0.95 * math.sqrt(max(0.05, 1.0 - ((y - centre) / reach) ** 2))
                xm = at + 0.012 * (1.0 - (2.0 * t - 1.0) ** 2)
                return Vector((sx * wall * (0.38 + 0.62 * u), y, xm - HALF + 0.026 * u - 0.004))

            d_t = place(0.6, 0.5) - place(0.4, 0.5)
            d_u = place(0.5, 0.6) - place(0.5, 0.4)
            facing = d_t.cross(d_u).normalized()
            for side in (1.0, -1.0):
                grid = []
                for ti in range(nt + 1):
                    t = ti / nt
                    row = []
                    for ui in range(nu + 1):
                        u = ui / nu
                        # (on the full model the filaments' edge is a fringe: every other point short of it)
                        reach_u = u * (0.8 if (not low and not game() and ui == nu and ti % 2 == 1) else 1.0)
                        foil = 2.6 * math.sqrt(reach_u) * (1.0 - reach_u) if ui < nu else 0.0
                        swell = 0.006 * foil * math.sin(math.pi * t) ** 0.6
                        row.append(m.add(place(t, reach_u) + facing * (side * swell * 0.5), (t, reach_u), GILL))
                    grid.append(row)
                for ti in range(nt):
                    for ui in range(nu):
                        m.face((grid[ti][ui], grid[ti][ui + 1], grid[ti + 1][ui + 1], grid[ti + 1][ui]), facing * side, "gills")


def body(m, low):
    around = AROUND[0]
    xs = rings(low)
    head = [xm for xm in xs if xm < JAW_TO - 1e-9]
    xs = xs[len(head):]
    grid = []
    for xm in xs:
        row = []
        for c in range(around):
            angle = c / around * TAU
            row.append(m.add(body_point(xm, angle), (xm, 0.5 + 0.5 * math.cos(angle)), BODY))
        grid.append(row)
    for r in range(len(grid) - 1):
        for c in range(around):
            n = (c + 1) % around
            quad = (grid[r][c], grid[r][n], grid[r + 1][n], grid[r + 1][c])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((middle.x, middle.y, 0.0)), "body")
    # the end inside the tail: a fan
    tip = m.add(Vector((0.0, 0.0, BODY_TO + 0.002 - HALF)), (BODY_TO + 0.002, 0.5), BODY)
    for c in range(around):
        m.face((tip, grid[-1][c], grid[-1][(c + 1) % around]), Vector((0.0, 0.0, 1.0)), "body")
    # The head ahead of the jaw's hinge: its skin above the line of the mouth (`half` columns each side of
    # the ridge, the last on the lip), and the roof of the mouth under it, lip to lip.
    half = round(lip_angle(JAW_TO) / (TAU / around))
    across = around - 2 * half
    uppers = []
    roofs = []
    for xm in head:
        reach = lip_angle(xm)
        up = outline(xm)[0]
        uppers.append([m.add(body_point(xm, j / half * reach), (xm, 0.5 + 0.5 * math.cos(j / half * reach)), BODY)
                       for j in range(-half, half + 1)])
        roofs.append([m.add(inside_point(xm, 1.0 - 2.0 * k / across, 0.4 * up), (xm, 0.5), BODY, smooth(BODY_FROM, 0.12 * JAW_TO, xm))
                      for k in range(across + 1)])
    # (where they join the whole body: its own points above the line of the mouth; below it the throat, a
    # wall across the back of the mouth, on the places of the body's points there)
    first = grid[0]
    uppers.append([first[j % around] for j in range(-half, half + 1)])
    roofs.append([m.add(m.verts[first[(half + k) % around]], (JAW_TO, 0.5), BODY, 1.0) for k in range(across + 1)])
    # (the throat has points of its own where it meets the roof, so that their shading is not shared)
    throat_top = []
    for q in roofs[len(head) - 1]:
        throat_top.append(m.add(m.verts[q], (0.0, 0.0), BODY, 1.0))
        m.data[-1] = (m.data[q][0], (1.0, 1.0 - BODY))
    for r in range(len(head)):
        for j in range(2 * half):
            quad = (uppers[r][j], uppers[r][j + 1], uppers[r + 1][j + 1], uppers[r + 1][j])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((middle.x, middle.y + 0.01, 0.0)), "body")
        for k in range(across):
            quad = (roofs[r][k], roofs[r][k + 1], roofs[r + 1][k + 1], roofs[r + 1][k])
            if r < len(head) - 1:
                m.face(quad, Vector((0.0, -1.0, 0.0)), "mouth roof")
            elif not low and not game():
                # The full model keeps the wall across the back of the mouth that it always had (the
                # shader lifts it out of the way as the mouth opens, onto the throat behind).
                # (as two triangles, each turned to face the mouth: at the corners the quad is a twisted sliver)
                a, b, c, d = throat_top[k], throat_top[k + 1], roofs[r + 1][k + 1], roofs[r + 1][k]
                m.face((a, b, c), Vector((0.0, -0.3, -1.0)), "throat wall")
                m.face((a, c, d), Vector((0.0, -0.3, -1.0)), "throat wall")
    # behind the mouth, the throat: a short tunnel back to the gills (the full model's is made last, in
    # its second surface)
    THROAT[:] = [list(throat_top), list(roofs[-1])]
    if low or game():
        throat(m, throat_top, roofs[-1])
    # the tip of the snout: a fan over the end of both
    loop = uppers[0] + roofs[0][1:-1]
    middle = sum((m.verts[q] for q in loop), Vector()) / len(loop)
    tip = m.add(middle + Vector((0.0, 0.0, -0.0015)), (0.0, 0.5), BODY)
    for i in range(len(loop)):
        m.face((tip, loop[i], loop[(i + 1) % len(loop)]), Vector((0.0, 0.0, -1.0)), "body")


def jaw(m, low):
    """The lower jaw: the body's own skin below the line of the mouth, ahead of the hinge, closed over by
    the floor of the mouth, with an end inside the head."""
    around = AROUND[0]
    # (as many columns as the body has below the line of the mouth, so that its end meets the body point for point)
    half = round(lip_angle(JAW_TO) / (TAU / around))
    under = around - 2 * half
    across = 4 if low else pick(8, 4)
    xs = [xm for xm in rings(low) if xm < JAW_TO + 1e-9]
    skins = []
    floors = []
    for xm in xs:
        reach = lip_angle(xm)
        down = outline(xm)[1]
        row = []
        for i in range(under + 1):
            angle = reach + (TAU - 2.0 * reach) * i / under
            if xm > JAW_TO - 1e-9:
                angle = (half + i) / around * TAU
            row.append(m.add(body_point(xm, angle), (xm, 0.5 + 0.5 * math.cos(angle)), JAW))
        skins.append(row)
        floors.append([m.add(inside_point(xm, 1.0 - 2.0 * k / across, -0.45 * down), (xm, 0.5), JAW, smooth(BODY_FROM, 0.12 * JAW_TO, xm))
                       for k in range(across + 1)])
    for r in range(len(xs) - 1):
        centre = 0.5 * (mouth_y(xs[r]) - outline(xs[r])[1])
        for i in range(under):
            quad = (skins[r][i], skins[r][i + 1], skins[r + 1][i + 1], skins[r + 1][i])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((middle.x, middle.y - centre, 0.0)), "jaw")
        for k in range(across):
            m.face((floors[r][k], floors[r][k + 1], floors[r + 1][k + 1], floors[r + 1][k]), Vector((0.0, 1.0, 0.0)), "mouth floor")
    # its tip, and its end inside the head: a fan each
    for r, z, way, inside in ((0, -HALF, -1.0, 0.0), (len(xs) - 1, JAW_TO - HALF, 1.0, 1.0)):
        loop = skins[r] + floors[r][-2:0:-1]
        if r > 0:
            # (points of its own, so that the skin's shading does not turn towards the end)
            loop = [m.add(m.verts[q], (xs[r], 0.5), JAW, 1.0) for q in loop]
        middle = sum((m.verts[q] for q in loop), Vector()) / len(loop)
        tip = m.add(Vector((0.0, 0.0 if r == 0 else middle.y, z)), (xs[r], 0.5), JAW, inside)
        for i in range(len(loop)):
            m.face((tip, loop[i], loop[(i + 1) % len(loop)]), Vector((0.0, 0.0, way)), "jaw" if r == 0 else "jaw end")


def eye(m, sx, low):
    """A low dome lying on the skin of the head."""
    spokes = 8 if low else pick(20, 12)
    steps = 1 if low else pick(5, 2)
    xe, ye = EYE_AT
    e = 0.004
    here = skin(xe, ye, sx)
    out = (skin(xe + e, ye, sx) - skin(xe - e, ye, sx)).cross(skin(xe, ye + e, sx) - skin(xe, ye - e, sx))
    out.normalize()
    if out.x * sx < 0.0:
        out = -out
    middle = m.add(here + out * 0.24 * EYE_RADIUS, (0.0, 1.0 if game() else 0.0), EYE)
    last = None
    for k in range(1, steps + 1):
        r = k / steps
        row = []
        for s in range(spokes):
            a = s / spokes * TAU
            p = skin(xe + math.cos(a) * EYE_RADIUS * r, ye + math.sin(a) * EYE_RADIUS * r, sx)
            row.append(m.add(p + out * EYE_RADIUS * (0.22 * (1.0 - r * r) + 0.02 * (1.0 - r) + 0.025), (r, 1.0 if game() else 0.0), EYE))
        for s in range(spokes):
            n = (s + 1) % spokes
            if last is None:
                m.face((middle, row[s], row[n]), out, "eyes")
            else:
                m.face((last[s], row[s], row[n], last[n]), out, "eyes")
        last = row


def blade(m, part, name, point, place, facing, thick, nt, nu):
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
                row.append(m.add(p, (t, u), part))
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
    """A place in the flat of the middle fins (body lengths behind the jaw, up) in the model."""
    return Vector((0.0, p[1], p[0] - HALF))


SIDE = Vector((1.0, 0.0, 0.0))


def fan(pivot, root_half, reach, spread, rounded):
    """A tail fin spread as a fan from its root: t from the root (a short upright line about `pivot`, half
    `root_half` long) to the back edge, `reach` away, u from its top edge (spread radians above the middle
    line) to its bottom edge. `rounded` bows the back edge out in the middle."""
    def point(t, u):
        a = spread * (1.0 - 2.0 * u)
        r = reach * t * 0.995 * (1.0 + rounded * (1.0 - (2.0 * u - 1.0) ** 2))
        return (pivot + r * math.cos(a), (1.0 - t) * root_half * (1.0 - 2.0 * u) + r * math.sin(a))
    return point


def pectorals_and_pelvics(m, low, pectoral_at, pectoral_long, pelvic_at, pelvic_long):
    d = 3 if low else 1
    for sx in (1.0, -1.0):
        # The pectoral fins: set behind the gill covers, a little below the middle, lying back and out.
        root = skin(pectoral_at, -0.012, sx)
        root.x -= sx * 0.003
        span = Vector((sx * 0.36, -0.12, 0.92)).normalized()
        chord = Vector((sx * 0.08, -0.9, 0.42)).normalized()
        facing = span.cross(chord).normalized()
        if facing.x * sx < 0.0:
            facing = -facing

        def pectoral_point(t, u):
            t *= 0.975
            wide_here = 0.4 * pectoral_long * (0.5 + 0.5 * smooth(0.0, 0.4, t)) * (1.0 - t) ** 0.5 + 0.002
            return (pectoral_long * t, 0.1 * pectoral_long * t * t + wide_here * u)

        blade(m, PECTORAL, "pectorals", pectoral_point,
              lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.005, pick(6 // d, 3), pick(5 // max(d - 1, 1), 2))
        # The pelvic fins: small, pointing back and down.
        root = Vector((sx * 0.012, bottom(pelvic_at) + 0.006, pelvic_at - HALF))
        span = Vector((sx * 0.22, -0.5, 0.84)).normalized()
        chord = Vector((0.0, 0.14, 1.0)).normalized()
        facing = span.cross(chord).normalized()
        if facing.x * sx < 0.0:
            facing = -facing

        def pelvic_point(t, u):
            t *= 0.97
            return (pelvic_long * t, 0.12 * pelvic_long * t * t + (0.36 * pelvic_long * (1.0 - t) ** 0.8 + 0.0015) * u)

        blade(m, PELVIC, "pelvics", pelvic_point,
              lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.004, pick(max(1, 4 // d), 2), pick(max(2, 4 // d), 1))


def fins_female(m, low):
    d = 3 if low else 1
    # The dorsal fin: small, rounded, set well back.
    def dorsal_point(t, u):
        xm = 0.5 + 0.09 * u
        high = 0.085 * (0.35 + 0.65 * math.sin(math.pi * (0.25 + 0.6 * u))) * (0.4 + 0.6 * smooth(0.0, 0.12, u)) * t
        return (xm + 0.45 * high, top(xm) - 0.004 + high + 0.004 * t)

    blade(m, DORSAL, "dorsal", dorsal_point, upright, SIDE, 0.006, pick(8 // d, 2), pick(8 // d, 3))

    # The anal fin: a small fan under the back half.
    def anal_point(t, u):
        xm = 0.56 + 0.08 * u
        high = 0.08 * (0.3 + 0.7 * (1.0 - u) ** 1.1) * (0.5 + 0.5 * smooth(0.0, 0.15, u)) * t
        return (xm + 0.6 * high, bottom(xm) + 0.004 - high - 0.004 * t)

    blade(m, ANAL, "anal", anal_point, upright, SIDE, 0.006, pick(6 // d, 2), pick(6 // d, 2))
    # The tail: a rounded fan.
    blade(m, TAIL, "tail", fan(0.765, 0.032, 0.225, 0.42, 0.06), upright, SIDE, 0.01, pick(10 // d, 2), pick(12 // d, 5))
    pectorals_and_pelvics(m, low, 0.2, 0.13, 0.42, 0.07)


def fins_male(m, low):
    d = 3 if low else 1
    # The dorsal fin: a long flag, its root on the back behind the middle of the body, trailing far back
    # over the tail.
    blade(m, DORSAL, "dorsal",
          swept(((0.29, top(0.29) - 0.005), (0.36, top(0.30) + 0.12), (0.70, top(0.42) + 0.10)),
                ((0.42, top(0.42) - 0.005), (0.62, top(0.42) + 0.015), (0.70, top(0.42) + 0.10))),
          upright, SIDE, 0.006, pick(14 // d, 4), pick(6 // d, 2))

    # The gonopodium: the anal fin made into a thin rod, lying back under the belly.
    def gonopodium_point(t, u):
        root = (0.33, bottom(0.33) + 0.006)
        along = (math.cos(-0.22), math.sin(-0.22))
        across = (-along[1], along[0])
        w = 0.016 * (1.0 - 0.55 * t)
        return (root[0] + along[0] * 0.15 * t + across[0] * w * (u - 0.5),
                root[1] + along[1] * 0.15 * t + across[1] * w * (u - 0.5))

    blade(m, ANAL, "gonopodium", gonopodium_point, upright, SIDE, 0.008, pick(8 // d, 2), pick(3 // max(d - 1, 1), 1))
    # The tail: a big fan, a delta with a rounded back edge, as long as the body.
    blade(m, TAIL, "tail", fan(0.515, 0.026, 0.47, 0.44, 0.03), upright, SIDE, 0.008, pick(16 // d, 4), pick(18 // d, 6))
    pectorals_and_pelvics(m, low, 0.16, 0.11, 0.27, 0.06)


def material_of(name, colour):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = colour
    material.diffuse_color = colour
    return material


def make(name, level):
    """One of a model's three: `level` "full", "low" or "game"."""
    LEVEL[0] = level
    low = level == "low"
    AROUND[0] = 10 if low else pick(32, 12)
    m = Mesh()
    body(m, low)
    jaw(m, low)
    for sx in (1.0, -1.0):
        eye(m, sx, low)
    if SHAPE["name"] == "male":
        fins_male(m, low)
    else:
        fins_female(m, low)
    if level == "full":
        # (the full model's throat and gills: its second surface, made after everything it had before)
        SURFACE[0] = 1
        throat(m, *THROAT)
    gills(m, low)
    SURFACE[0] = 0
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) for p in m.verts], [], m.faces)
    # (every layer made first, then each looked up by name: making one moves the others)
    mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.new(name="UV2")
    uv = mesh.uv_layers["UVMap"].data
    uv2 = mesh.uv_layers["UV2"].data
    for poly in mesh.polygons:
        for corner, vi in enumerate(poly.vertices):
            d = m.data[vi]
            uv[poly.loop_start + corner].uv = d[0]
            uv2[poly.loop_start + corner].uv = d[1]
    mesh.materials.append(material_of("guppy", (0.6, 0.58, 0.45, 1.0)))
    if 1 in m.surface:
        mesh.materials.append(material_of("guppy_throat", (0.5, 0.1, 0.1, 1.0)))
        for poly in mesh.polygons:
            poly.material_index = m.surface[poly.index]
    return finish(name, mesh, m)


def finish(name, mesh, m):
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    print("BUILT %s verts=%d tris=%d" % (name, len(mesh.vertices), tris))
    winding(name, mesh, m)
    return obj


def winding(name, mesh, m):
    """Nothing inside out: the skin of the body faces away from its middle line, each skin of a fin away
    from the fin's own flat, an eye out from the body (Blender's front is the side a face's normal is on)."""
    bad = {}
    for poly in mesh.polygons:
        out, group = m.out[poly.index]
        o = Vector((out.x, -out.z, out.y))
        if poly.normal.dot(o) <= 0.0:
            bad[group] = bad.get(group, 0) + 1
    told = ["%s %d/%d wrong" % (group, bad.get(group, 0), count) for group, count in m.count.items()]
    print("WINDING %s: %s: %s" % (name, "ok" if not bad else "INSIDE OUT", ", ".join(told)))


def export_one(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", export_yup=True, use_selection=True,
        export_animations=False, export_texcoords=True, export_vertex_color="NONE", export_all_vertex_colors=False,
    )


def render(folder, made, length, prefix_name):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.show_cavity = True
    scene.display.shading.show_backface_culling = True
    scene.display.shading.color_type = "MATERIAL"
    scene.render.resolution_x, scene.render.resolution_y = 1400, 800
    if scene.world is None:
        scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.get("Camera")
    if camera is None:
        camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
        camera.data.type = "ORTHO"
        camera.data.clip_end = 1000.0
        scene.collection.objects.link(camera)
    scene.camera = camera
    L = length
    # (Blender space: the fish lies along Y, its nose at +Y, up is Z)
    views = [("left", (1, 0, 0), (0, 0, 0), 1.15 * L), ("right", (-1, 0, 0), (0, 0, 0), 1.15 * L),
             ("front", (0, 1, 0), (0, 0, 0), 0.7 * L), ("back", (0, -1, 0), (0, 0, 0), 0.7 * L),
             ("top", (0.001, 0, 1), (0, 0, 0), 2.0 * L), ("under", (0.001, 0, -1), (0, 0, 0), 2.0 * L),
             ("head", (0.8, 0.5, 0.2), (0, 0.36 * L, 0), 0.4 * L), ("tail", (0.7, -0.6, 0.3), (0, -0.25 * L, 0), 0.8 * L)]
    everything = [o for o in bpy.data.objects if o.type == "MESH"]
    for prefix, obj, only in (("", made[0], None), ("lo_", made[1], ("left", "head", "top", "front")),
                              ("game_", made[2], ("left", "right", "head", "top", "front", "under"))):
        for other in everything:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if only and view not in only:
                continue
            offset = Vector(direction).normalized() * 40.0
            camera.data.ortho_scale = frame
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s_%s%s.png" % (prefix_name, prefix, view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    os.makedirs(OUT, exist_ok=True)
    built = {}
    for name in SHAPES:
        use(name)
        full = make("guppy_%s" % name, "full")
        low = make("guppy_%s_lo" % name, "low")
        game_model = make("guppy_%s_game" % name, "game")
        LEVEL[0] = "full"
        export_one(full, os.path.join(OUT, "guppy_%s.glb" % name))
        export_one(low, os.path.join(OUT, "guppy_%s_lo.glb" % name))
        export_one(game_model, os.path.join(OUT, "guppy_%s_game.glb" % name))
        built[name] = (full, low, game_model)
        print("SHADER %s: jaw_to %.4f hinge_y %.5f eye_at (%.3f, %.3f) eye_radius %.3f joint %.3f body_to %.3f mouth %s gill %s gill_from %.4f gill_to %.4f wall_up %.4f" % (
            name, JAW_TO, mouth_y(JAW_TO), EYE_AT[0], EYE_AT[1], EYE_RADIUS, JOINT, BODY_TO, SHAPE["mouth"], SHAPE["gill"], GILL_FROM, GILL_TO, WALL_UP))
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        for name, made in built.items():
            render(PREVIEW, made, SHAPES[name]["length"], name)
    # (side by side in the .blend: each model a row, full and low along it)
    for row, made in enumerate(built.values()):
        for k, obj in enumerate(made):
            obj.location = (0.06 * k, 0.0, -0.04 * row)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "guppy.blend"))


if __name__ == "__main__":
    main()
