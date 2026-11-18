"""Builds the mermaid (creatures/mermaid) and exports it for Godot.

Run from the game's root (or from GameCommon's godot/mermaid/files):
    blender --background --python creatures/mermaid/tools/build_mermaid.py
    blender --background --python creatures/mermaid/tools/build_mermaid.py -- <preview folder>   # with pictures

Writes creatures/mermaid/models/mermaid.glb (full), mermaid_game.glb (the game model, Twilight Princess weight) and
mermaid_lo.glb (far off), and the editable creatures/mermaid/tools/mermaid.blend. Each model is one still mesh with one
surface, worn with creatures/sea_myth/sea_myth.gdshader (what each point tells it: tools/myth_build.py there). It
prints a WINDING line for each (nothing inside out) and a BOX line (how far it reaches).

A mermaid of sailors' tales, not a pretty one (the user's ask and the concept picture, tools/art_src/concept_mythical.jpg
in Gulp; nothing traced): swimming flat out as a dolphin does, her nose (the front of her head) at -Z. A long scaled
tail with a broad flat fluke that beats UP AND DOWN; a woman's body above the hips in pale grey-green skin; webbed
hands of four long fingers with fins along the backs of her forearms; fin ears; long hair of weed-tangled locks
streaming back; a necklace of shells and a wrap of weed and shells across her chest. Her face is a smooth blank
MASK (brow, nose, chin and shallow sockets; no eyes, no mouth), a pale shell over the front of her head.

`xm` below is metres behind the front of her head; Godot's z is xm - HALF.
"""

import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(HERE, "..", "..", "sea_myth", "tools"))
import myth_build as mb  # noqa: E402
from myth_build import V, lin, mixc, smooth, lerp, hash1, TAU, PI  # noqa: E402

OUT = os.path.join(HERE, "..", "models")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = ARGS[0] if ARGS else ""
NAME = "mermaid"
HALF = 0.96

# As the shader settings have them (mermaid.gd): her shoulder and elbow (right side).
SHOULDER = (0.18, 0.0, 0.33)
ELBOW = (0.27, -0.085, 0.53)
WRIST = (0.29, -0.13, 0.74)

SKIN = lin((0.6, 0.67, 0.63))
SKIN_DARK = lin((0.42, 0.5, 0.47))
MASK = lin((0.86, 0.87, 0.83))
SCALE_BACK = lin((0.16, 0.3, 0.29))
SCALE_SIDE = lin((0.26, 0.44, 0.41))
SCALE_BELLY = lin((0.5, 0.6, 0.55))
FIN = lin((0.42, 0.56, 0.52))
FIN_EDGE = lin((0.62, 0.74, 0.7))
HAIR = lin((0.3, 0.37, 0.17))
HAIR_TIP = lin((0.46, 0.52, 0.22))
WEED = lin((0.3, 0.42, 0.16))
WEED_DARK = lin((0.18, 0.27, 0.1))
SHELL = lin((0.88, 0.8, 0.68))
SHELL_PINK = lin((0.86, 0.66, 0.6))
CORD = lin((0.45, 0.36, 0.25))

# Quality: (rings along the body, columns round it, head latitudes, head longitudes, mask rows, mask columns,
# arm sides, arm rings, hand rows, hair locks, hair segments, hair sides, fluke rows, fluke columns)
Q = {
    "full": dict(rings=90, cols=48, lats=34, lons=44, mrows=12, mcols=16, arm_sides=14, arm_rings=22, hand_rows=10,
                 hand_cols=16, locks=40, lock_seg=14, lock_sides=4, fl_rows=14, fl_cols=10, ear=6, neck=14,
                 cord=40, cord_sides=5, shell=10, wrap_cols=48, wrap_rows=5),
    "game": dict(rings=24, cols=16, lats=10, lons=14, mrows=7, mcols=6, arm_sides=7, arm_rings=8, hand_rows=4,
                 hand_cols=8, locks=15, lock_seg=5, lock_sides=4, fl_rows=6, fl_cols=4, ear=2, neck=7,
                 cord=14, cord_sides=3, shell=4, wrap_cols=14, wrap_rows=2),
    "low": dict(rings=13, cols=8, lats=6, lons=8, mrows=2, mcols=3, arm_sides=4, arm_rings=5, hand_rows=2,
                hand_cols=4, locks=6, lock_seg=3, lock_sides=3, fl_rows=3, fl_cols=2, ear=0, neck=4,
                cord=0, cord_sides=3, shell=0, wrap_cols=8, wrap_rows=1),
}


def P(x, y, xm):
    return V(x, y, xm - HALF)


# ---------------------------------------------------------------------------------------------------------------
# The body: neck to the tail stock, one loft. (xm, middle height, half-width, half-height above, below, squareness)

PROFILE = [
    (0.235, 0.004, 0.06, 0.05, 0.05, 2.0),
    (0.26, 0.008, 0.12, 0.06, 0.065, 2.2),
    (0.29, 0.005, 0.172, 0.07, 0.08, 2.6),
    (0.33, 0.0, 0.192, 0.08, 0.095, 2.8),
    (0.38, 0.0, 0.178, 0.085, 0.11, 2.5),
    (0.44, 0.0, 0.163, 0.08, 0.115, 2.3),
    (0.50, 0.0, 0.148, 0.075, 0.095, 2.2),
    (0.57, 0.005, 0.124, 0.07, 0.08, 2.2),
    (0.64, 0.005, 0.13, 0.07, 0.083, 2.2),
    (0.72, 0.005, 0.15, 0.075, 0.088, 2.3),
    (0.80, 0.005, 0.15, 0.078, 0.085, 2.3),
    (0.90, 0.005, 0.135, 0.075, 0.078, 2.2),
    (1.02, 0.008, 0.115, 0.068, 0.07, 2.1),
    (1.14, 0.01, 0.095, 0.06, 0.06, 2.0),
    (1.26, 0.012, 0.075, 0.052, 0.052, 2.0),
    (1.38, 0.012, 0.056, 0.045, 0.044, 2.0),
    (1.48, 0.01, 0.04, 0.038, 0.036, 2.0),
    (1.56, 0.008, 0.028, 0.032, 0.03, 2.0),
    (1.62, 0.005, 0.021, 0.028, 0.026, 2.0),
    (1.67, 0.004, 0.018, 0.021, 0.019, 2.0),
    (1.70, 0.003, 0.01, 0.011, 0.011, 2.0),
]
TAIL_END = 1.715


def profile_at(xm):
    """The body's section at xm: a smooth curve through PROFILE (each value a Catmull-Rom of its neighbours)."""
    rows = PROFILE
    if xm <= rows[0][0]:
        return rows[0]
    if xm >= rows[-1][0]:
        return rows[-1]
    i = 0
    while rows[i + 1][0] < xm:
        i += 1
    f = (xm - rows[i][0]) / (rows[i + 1][0] - rows[i][0])
    out = []
    for k in range(6):
        p0 = rows[max(i - 1, 0)][k]
        p1 = rows[i][k]
        p2 = rows[i + 1][k]
        p3 = rows[min(i + 2, len(rows) - 1)][k]
        f2 = f * f
        out.append(0.5 * (2 * p1 + (-p0 + p2) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f2 + (-p0 + 3 * p1 - 3 * p2 + p3) * f2 * f))
    return out


def surface(xm, theta, out=0.0):
    _, cy, a, bu, bd, n = profile_at(xm)
    c = P(0.0, cy, xm)
    p = mb.section_point(c, V(1, 0, 0), V(0, 1, 0), a, bu, bd, n, theta)
    if out:
        d = p - c
        d.z = 0.0
        p += d.normalized() * out
    return p


def body_colour(xm, v):
    """Skin above the hips, scales below them: darker on the back, paler on the belly."""
    belly = 1.0 - abs(v - 0.5) * 2.0
    scale = mixc(SCALE_BACK, SCALE_SIDE, smooth(0.0, 0.35, 1.0 - belly))
    scale = mixc(SCALE_SIDE, scale, smooth(0.3, 0.75, 1.0 - belly))
    scale = mixc(scale, SCALE_BELLY, smooth(0.6, 0.95, belly))
    skin = mixc(SKIN, SKIN_DARK, 0.25 * smooth(0.6, 1.0, 1.0 - belly))
    # (the scales begin at the hips in a ragged edge, lower on her sides)
    edge = 0.76 + 0.035 * math.sin(v * TAU * 7.0) + 0.04 * belly
    t = smooth(edge - 0.03, edge + 0.03, xm)
    return mixc(skin, scale, t), t


def body(m, q):
    gather = lambda t: 1.0 + 1.6 * math.exp(-((t - 0.07) / 0.08) ** 2) + 1.0 * math.exp(-((t - 0.95) / 0.06) ** 2)
    xs = [lerp(PROFILE[0][0], PROFILE[-1][0], t) for t in mb.spread(q["rings"], gather)]
    cols = q["cols"]
    thetas = [TAU * j / cols for j in range(cols)]
    rings, centres = [], []
    for xm in xs:
        ring = []
        for th in thetas:
            p = surface(xm, th)
            v = th / TAU
            col, scaly = body_colour(xm, v)
            ring.append(m.add(p, uv=(xm, v), part=mb.BODY, col=col, mask=scaly))
        rings.append(ring)
        centres.append(P(0.0, profile_at(xm)[1], xm))
    tip = m.add(P(0.0, 0.003, TAIL_END), uv=(TAIL_END, 0.0), col=body_colour(TAIL_END, 0.25)[0], mask=1.0)
    start = m.add(P(0.0, 0.004, 0.22), uv=(0.22, 0.0), col=SKIN)
    mb.loft(m, rings, "body", cap0=(start, V(0, 0, -1)), cap1=(tip, V(0, 0, 1)), centres=centres)


# ---------------------------------------------------------------------------------------------------------------
# The head, its mask, its ears, the neck

FACE_DOWN = math.radians(40.0)
HEAD_C = P(0.0, 0.075, 0.115)
CROWN = V(0.0, math.cos(FACE_DOWN), -math.sin(FACE_DOWN))
BACK = V(0.0, math.sin(FACE_DOWN), math.cos(FACE_DOWN))
HEAD_B = Matrix((V(1, 0, 0), CROWN, BACK)).transposed()


def head_radius(d):
    """Her head's radius along its own direction d (x right, y her crown, z the back of her head)."""
    rx = 0.076 * (1.0 - 0.3 * smooth(-0.2, -0.85, d.y))
    ry = 0.104 if d.y > 0.0 else 0.122
    rz = 0.094 if d.z < 0.0 else 0.1
    r = 1.0 / math.sqrt((d.x / rx) ** 2 + (d.y / ry) ** 2 + (d.z / rz) ** 2)
    front = smooth(-0.5, -0.88, d.z)
    ax = abs(d.x)
    r += 0.007 * math.exp(-((d.y - 0.24) / 0.07) ** 2) * front * (1.0 - 0.6 * smooth(0.3, 0.6, ax))
    r -= 0.009 * math.exp(-(((ax - 0.3) / 0.12) ** 2 + ((d.y - 0.1) / 0.075) ** 2)) * front
    nose = smooth(0.16, -0.02, d.y) * (1.0 - smooth(-0.1, -0.2, d.y))
    r += 0.021 * math.exp(-(d.x / 0.07) ** 2) * nose * front
    r += 0.005 * math.exp(-(((ax - 0.42) / 0.12) ** 2 + ((d.y + 0.03) / 0.1) ** 2)) * front
    r += 0.004 * math.exp(-((d.x / 0.2) ** 2 + ((d.y + 0.36) / 0.08) ** 2)) * front
    r += 0.011 * math.exp(-((d.x / 0.16) ** 2 + ((d.y + 0.64) / 0.1) ** 2)) * smooth(-0.3, -0.8, d.z)
    return r


def head_point(d, out=0.0):
    return HEAD_C + HEAD_B @ (d * (head_radius(d) + out))


def head(m, q):
    lats = [math.sin(a) for a in [lerp(PI / 2, -PI / 2, t) for t in
                                  mb.spread(q["lats"], lambda t: 1.0 + 0.8 * math.exp(-((t - 0.55) / 0.2) ** 2))]]
    gather = lambda t: 1.0 + 1.2 * math.exp(-((t - 0.5) / 0.18) ** 2)
    lons = [TAU * t for t in mb.spread(q["lons"], gather)[:-1]]
    # (under the mask the head is sunk a little, so that no point of it shows through the mask's facets)
    sunk = lambda d: head_radius(d) - 0.009 * (1.0 - smooth(0.55, 0.92, mask_reach(d)))
    mb.blob(m, HEAD_C, HEAD_B, sunk, lats, lons,
            lambda d: dict(uv=(0.1, 0.0), col=mixc(SKIN, SKIN_DARK, 0.3 * smooth(0.2, 0.9, d.z))), "head")


MASK_LON = 1.08
MASK_DOWN = 0.9
MASK_UP = 0.72
MASK_MID = 0.04


def mask_reach(d):
    """How far out on the mask a direction of her head is: under 1 inside it."""
    du =(abs(math.atan2(d.x, -d.z))) / MASK_LON
    lat = math.asin(max(-1.0, min(1.0, d.y))) - MASK_MID
    dv = lat / (MASK_DOWN if lat < 0.0 else MASK_UP)
    return math.sqrt(du * du + dv * dv)


def mask_dir(i, j, rows, cols):
    """The mask: an oval over the front of her head, as a grid squeezed into a disc."""
    u = -1.0 + 2.0 * j / cols
    u = math.copysign(abs(u) ** 1.3, u)
    v = -1.0 + 2.0 * i / rows
    v = math.copysign(abs(v) ** 1.3, v)
    du = u * math.sqrt(max(1.0 - 0.5 * v * v, 0.0))
    dv = v * math.sqrt(max(1.0 - 0.5 * u * u, 0.0))
    lon = PI + du * MASK_LON
    lat = MASK_MID + dv * (MASK_DOWN if dv < 0.0 else MASK_UP)
    c = math.cos(lat)
    return V(c * math.sin(lon), math.sin(lat), c * math.cos(lon)), max(abs(u), abs(v))


def mask(m, q):
    rows, cols = q["mrows"] * 2, q["mcols"] * 2
    grid = []
    for i in range(rows + 1):
        row = []
        for j in range(cols + 1):
            d, edge = mask_dir(i, j, rows, cols)
            lift = 0.0012 if edge > 0.999 else 0.0042
            socket = math.exp(-(((abs(d.x) - 0.3) / 0.12) ** 2 + ((d.y - 0.1) / 0.075) ** 2))
            col = mixc(MASK, lin((0.62, 0.64, 0.6)), 0.55 * socket)
            row.append(m.add(head_point(d, lift), uv=(0.1, 0.0), col=col))
        grid.append(row)
    for i in range(rows):
        for j in range(cols):
            quad = (grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j])
            m.face(quad, m.centre(quad) - HEAD_C, "mask")


def ears(m, q):
    """Fin ears: a fan of spines on each side of her head, swept back, webbed between."""
    if q["ear"] == 0:
        return
    for sx in (1.0, -1.0):
        d0 = V(sx, 0.12, 0.02).normalized()
        root = head_point(d0, -0.004)
        out = (HEAD_B @ V(sx, 0.0, 0.0)).normalized()
        up = CROWN
        back = BACK

        def point(t, u, root=root, out=out):
            fan = lerp(-0.55, 1.15, u)
            spine = (out * 0.75 + back * math.cos(fan) * 0.75 + up * math.sin(fan) * 0.9).normalized()
            reach = 0.078 * (0.62 + 0.38 * abs(math.cos(u * 4.0 * PI))) * (0.8 + 0.3 * u)
            base = root + up * (u - 0.4) * 0.05 + back * (u - 0.4) * 0.012
            return base + spine * reach * t

        def normal(t, u, out=out):
            return (out - back * 0.35).normalized()

        mb.blade(m, point, normal, lambda t, u: 0.004 * (1.0 - t) * math.sin(PI * u) ** 0.5,
                 mb.spread(q["ear"]), mb.spread(q["ear"] * 3),
                 lambda t, u: dict(uv=(u, t), col=mixc(FIN, FIN_EDGE, t)), "ears")


def neck(m, q):
    base = P(0.0, 0.0, 0.31)
    top = HEAD_C + HEAD_B @ V(0.0, -0.55, 0.45) * 0.07
    pts = [base.lerp(top, t) + V(0, 0.012 * math.sin(PI * t), 0) for t in mb.spread(3)]
    mb.tube(m, pts, lambda t: (0.05 - 0.008 * t, 0.046 - 0.004 * t), q["neck"],
            lambda t, v: dict(uv=(0.25, v), col=SKIN), "neck", cap_end=True, cap_start=True)


# ---------------------------------------------------------------------------------------------------------------
# Arms and webbed hands


def arm(m, q, sx):
    s = P(sx * SHOULDER[0], SHOULDER[1], SHOULDER[2])
    e = P(sx * ELBOW[0], ELBOW[1], ELBOW[2])
    w = P(sx * WRIST[0], WRIST[1], WRIST[2])
    n = q["arm_rings"]
    pts = []
    ws = []
    for k in range(n + 1):
        t = k / n
        if t < 0.5:
            f = t / 0.5
            p = s.lerp(e, f) + V(sx * 0.012, 0.004, 0.0) * math.sin(PI * f)
            aw = 0.5 * f
        else:
            f = (t - 0.5) / 0.5
            p = e.lerp(w, f) + V(sx * 0.006, 0.0, 0.0) * math.sin(PI * f)
            aw = 0.5 + 0.3 * f
        pts.append(p)
        ws.append(aw)

    def size(t):
        if t < 0.5:
            f = t / 0.5
            r = lerp(0.046, 0.031, f) + 0.006 * math.exp(-((f - 0.25) / 0.2) ** 2)
            return r, r * 0.95
        f = (t - 0.5) / 0.5
        r = lerp(0.031, 0.022, f) + 0.007 * math.exp(-((f - 0.25) / 0.25) ** 2)
        return r * (1.0 + 0.3 * f), r * (1.0 - 0.3 * f)

    mb.tube(m, pts, size, q["arm_sides"],
            lambda t, v: dict(uv=(0.5, v), w=ws[min(int(round(t * n)), n)], part=mb.LIMB, col=SKIN), "arms",
            up_hint=V(0, 1, 0), cap_end=True, cap_start=False)
    hand(m, q, sx, e, w)
    forearm_fin(m, q, sx, e, w)


def hand(m, q, sx, e, w):
    """A webbed hand: four long fingers with webs between them, as one blade thicker over each finger, the
    fingertips curling a little towards the palm."""
    along = (w - e).normalized()
    along = (along + V(sx * 0.15, -0.05, 0.0)).normalized()
    palm = V(-sx * 0.55, -0.85, 0.0).normalized()
    palm = (palm - along * palm.dot(along)).normalized()
    across = along.cross(palm).normalized() * sx
    length = 0.2

    def finger(u):
        return 0.5 + 0.5 * math.cos(TAU * (4.0 * u - 0.5))

    def reach(u):
        # (the webs reach a little past the knuckles; the fingers on to claw tips, the middle two longest)
        long = 1.0 - 0.08 * abs(u - 0.5) * 2.0
        return long * (0.62 + 0.38 * finger(u) ** 2.0)

    def width(t):
        return lerp(0.05, 0.078, smooth(0.0, 0.5, t)) + 0.01 * smooth(0.5, 1.0, t)

    def point(t, u):
        tt = t * reach(u)
        p = w + along * (length * tt - 0.012) + across * (u - 0.5) * width(tt)
        return p + palm * (0.045 * tt ** 2.2)

    def thick(t, u):
        return (0.0095 * (1.0 - 0.6 * t) * (0.2 + 0.8 * finger(u) ** 1.5) * math.sin(PI * u) ** 0.35
                * (1.0 - t) ** 0.3)

    def colour(t, u):
        web = (1.0 - finger(u)) * smooth(0.35, 0.6, t)
        return mixc(mixc(SKIN, SKIN_DARK, 0.4 * t * finger(u)), FIN_EDGE, 0.75 * web)

    rows = mb.spread(q["hand_rows"], lambda t: 1.0 + t)
    cols = mb.spread(q["hand_cols"])
    mb.blade(m, point, lambda t, u: -palm, thick, rows, cols,
             lambda t, u: dict(uv=(u, t), w=0.8 + 0.2 * t, part=mb.LIMB, col=colour(t, u)), "hands")
    # (her thumb)
    root = w + across * (-0.5 * 0.05) * 1.0 + along * 0.01
    tip = root + (along * 0.6 - across * 0.55 - palm * 0.3).normalized() * 0.075
    pts = [root.lerp(tip, t) for t in mb.spread(max(2, q["hand_rows"] // 2))]
    mb.tube(m, pts, lambda t: (0.011 * (1 - 0.5 * t), 0.008 * (1 - 0.5 * t)), max(3, q["arm_sides"] - 3),
            lambda t, v: dict(uv=(0.9, v), w=0.85 + 0.1 * t, part=mb.LIMB, col=SKIN), "hands")


def forearm_fin(m, q, sx, e, w):
    """A fin along the back of each forearm, its spines swept back, its edge ragged between them."""
    out = V(sx * 0.75, 0.55, 0.15).normalized()

    def point(t, u):
        base = e.lerp(w, 0.12 + 0.72 * u) + out * 0.02
        spikes = 0.7 + 0.3 * abs(math.cos(u * 4.0 * PI))
        reach = 0.075 * math.sin(PI * (0.15 + 0.85 * u)) ** 0.6 * spikes
        return base + (out * 0.6 + V(0, 0, 1) * 0.8).normalized() * reach * t

    side = V(0, 0, 1).cross(out).normalized()
    mb.blade(m, point, lambda t, u: side, lambda t, u: 0.003 * (1.0 - t) * math.sin(PI * u) ** 0.5,
             mb.spread(max(1, q["fl_rows"] // 2)), mb.spread(max(2, q["fl_cols"] * 2)),
             lambda t, u: dict(uv=(u, t), w=0.5 + 0.3 * u, part=mb.LIMB, col=mixc(FIN, FIN_EDGE, t)), "arm fins")


# ---------------------------------------------------------------------------------------------------------------
# The fluke and the little fins at her hips


def fluke(m, q):
    for sx in (1.0, -1.0):
        def point(t, u, sx=sx):
            lead = 1.6 + 0.24 * t ** 1.9
            trail = 1.75 + 0.15 * t ** 0.55 - 0.035 * math.sin(t * PI * 4.0) ** 2 * t * (1.0 - t)
            xm = lerp(lead, trail, u)
            return P(sx * (0.004 + 0.32 * t ** 0.95), 0.004 - 0.014 * t * t, xm)

        def thick(t, u):
            return 0.013 * math.sin(PI * u) ** 0.7 * (1.0 - t * t) ** 0.6

        mb.blade(m, point, lambda t, u: V(0, 1, 0), thick,
                 mb.spread(q["fl_rows"], lambda t: 1.0 + 1.5 * t), mb.spread(q["fl_cols"]),
                 lambda t, u: dict(uv=(u, t), w=0.3 + 0.7 * t, part=mb.FIN_H, col=mixc(FIN, FIN_EDGE, t * 0.8)),
                 "fluke")


def hip_fins(m, q):
    for sx in (1.0, -1.0):
        def point(t, u, sx=sx):
            base = surface(lerp(0.8, 0.9, u), sx * TAU / 4.0 + sx * 0.25, -0.004)
            spike = 0.75 + 0.25 * abs(math.cos(u * 3.0 * PI))
            return base + V(sx * 0.6, -0.15, 0.8).normalized() * 0.09 * t * spike * (0.6 + 0.6 * u)

        mb.blade(m, point, lambda t, u: V(0, 1, 0), lambda t, u: 0.003 * (1.0 - t) * math.sin(PI * u) ** 0.5,
                 mb.spread(max(1, q["fl_rows"] // 2)), mb.spread(max(2, q["fl_cols"])),
                 lambda t, u: dict(uv=(u, t), w=t, part=mb.FIN_H, col=mixc(FIN, FIN_EDGE, t)), "hip fins")


# ---------------------------------------------------------------------------------------------------------------
# Hair, necklace, wrap


def hair(m, q):
    n = q["locks"]
    for k in range(n):
        h = hash1(k * 3.7 + 1.0)
        h2 = hash1(k * 5.3 + 2.0)
        # (roots over the crown, the back and the sides of her head, behind the mask)
        f = (k + 0.5) / n
        lon = lerp(-1.75, 1.75, f) + (h - 0.5) * 0.2
        lat = lerp(1.05, 0.2, abs(math.sin(f * PI * 2.5)) * 0.45 + h2 * 0.55)
        if abs(lon) > 1.3:
            lat = max(lat, 0.5)
        c = math.cos(lat)
        d = V(c * math.sin(lon), math.sin(lat), c * math.cos(lon))
        root = head_point(d, -0.006)
        normal = (HEAD_B @ d).normalized()
        # (first back over her head, close to it; then streaming behind her, spreading and waving)
        over = (BACK - normal * BACK.dot(normal)).normalized()
        length = 0.4 + 0.32 * h
        side = math.sin(lon)
        lift = 0.14 + 0.24 * h2 - 0.12 * abs(side)
        seg = q["lock_seg"]
        pts = []
        for i in range(seg + 1):
            t = i / seg
            near = min(t / 0.22, 1.0)
            p = root + normal * 0.018 * math.sin(near * PI * 0.5) + over * 0.06 * near
            flow = V(side * (0.3 + 0.2 * h), lift - 0.25 * t, 1.0).normalized()
            p += flow * length * max(t - 0.1, 0.0)
            wave = math.sin(t * (6.0 + 3.0 * h) + k * 1.3)
            p += V(wave * 0.7, math.cos(t * 5.0 + k * 1.7), 0.0) * 0.06 * t
            pts.append(p)
        weed = hash1(k * 9.1) > 0.72
        tip = mixc(WEED, WEED_DARK, 0.3) if weed else HAIR_TIP
        wide = 0.03 + 0.02 * h2
        mb.tube(m, pts, lambda t, wide=wide: (wide * (1.0 - 0.7 * t), 0.011 * (1.0 - 0.6 * t)), q["lock_sides"],
                lambda t, v, seed=h, tip=tip: dict(uv=(t, seed), w=t, part=mb.STRAND, col=mixc(HAIR, tip, t)),
                "hair", up_hint=normal, theta0=0.0 if q["lock_sides"] % 2 == 0 else PI / q["lock_sides"])


NECK_BASE = P(0.0, 0.0, 0.31)
NECK_TOP = HEAD_C + HEAD_B @ V(0.0, -0.55, 0.45) * 0.07


def outside_body(p, gap):
    """A point pushed out of the body to `gap` off its skin, if it is inside."""
    xm = p.z + HALF
    if xm < PROFILE[0][0] or xm > PROFILE[-1][0]:
        return p
    cy = profile_at(xm)[1]
    c = P(0.0, cy, xm)
    d = p - c
    phi = math.atan2(d.x, d.y)
    r = (surface(xm, phi) - c).length
    if d.length < r + gap:
        return c + d.normalized() * (r + gap)
    return p


def necklace_at(th):
    """Her necklace: a loop round her neck just ahead of her shoulders (th 0 the back of her neck, PI her throat),
    sagging a little at the throat where the shells hang."""
    nc = NECK_BASE.lerp(NECK_TOP, 0.58)
    axis = (NECK_TOP - NECK_BASE).normalized()
    e2 = V(1, 0, 0).cross(axis).normalized()
    if e2.y < 0.0:
        e2 = -e2
    f = 0.5 - 0.5 * math.cos(th)
    p = nc + (V(1, 0, 0) * math.sin(th) + e2 * math.cos(th)) * (0.054 + 0.006 * f) + V(0.0, -0.012, 0.01) * f * f
    return outside_body(p, 0.004)


def necklace(m, q):
    n = q["cord"]
    if n == 0:
        return
    pts = [necklace_at(TAU * i / n) for i in range(n + 1)]
    mb.tube(m, pts, lambda t: (0.0035, 0.0035), q["cord_sides"],
            lambda t, v: dict(uv=(t, v), col=CORD), "necklace", up_hint=V(0, 0, 1), cap_end=False)
    shells = q["shell"]
    nc = NECK_BASE.lerp(NECK_TOP, 0.58)
    axis = (NECK_TOP - NECK_BASE).normalized()
    for k in range(5):
        th = PI + (k - 2) * 0.42
        on = necklace_at(th)
        nrm = on - nc
        nrm = (nrm - axis * nrm.dot(axis)).normalized()
        # (each shell hangs from the cord, a little towards her chest, facing out)
        c = on + nrm * 0.004 + axis * -0.012
        colour = SHELL if k % 2 == 0 else SHELL_PINK
        mb.dome(m, c, nrm, 0.016 if k == 2 else 0.012, 0.007, shells, 2,
                lambda r, colour=colour: dict(uv=(r, 0.0), col=mixc(colour, lin((0.6, 0.52, 0.45)), 0.4 * r)),
                "shells", squash=0.85, up=V(0, 0, 1))


def wrap(m, q):
    """A wrap of weed across her chest, its edges ragged, two shells on it and weed trailing from its sides."""
    cols = q["wrap_cols"]
    rows = q["wrap_rows"]
    grid = []
    for i in range(rows + 1):
        f = i / rows
        row = []
        for j in range(cols):
            th = TAU * j / cols
            rag = 0.012 * math.sin(th * 9.0 + 1.3) + 0.008 * math.sin(th * 23.0)
            xm = lerp(0.37 + rag * (1.0 - f) * 0.7, 0.475 + rag * f, f)
            p = surface(xm, th, 0.0075 * math.sin(PI * (0.15 + 0.7 * f)) + 0.002)
            col = mixc(WEED, HAIR_TIP, 0.5 + 0.5 * math.sin(th * 13.0 + f * 5.0))
            row.append(m.add(p, uv=(xm, th / TAU), col=col))
        grid.append(row)
    centres = [P(0.0, 0.0, 0.42)] * len(grid)
    # (a band lying on her skin, a few millimetres off it: its inside is never seen)
    mb.loft(m, grid, "wrap", centres=centres)
    if q["shell"]:
        for th, size in ((PI + 0.42, 0.016), (PI - 0.42, 0.016)):
            c = surface(0.42, th, 0.011)
            nrm = c - P(0.0, 0.0, 0.42)
            nrm.z = 0.0
            mb.dome(m, c, nrm.normalized(), size, 0.009, q["shell"], 2,
                    lambda r: dict(uv=(r, 0.0), col=mixc(SHELL_PINK, SHELL, r)), "shells", squash=0.9,
                    up=V(0, 0, 1))
    for k, th in enumerate((TAU * 0.27, TAU * 0.73, TAU * 0.31, TAU * 0.69)):
        root = surface(0.47, th, 0.006)
        sx = 1.0 if th < PI else -1.0
        length = 0.16 + 0.06 * (k % 2)
        seg = max(2, q["lock_seg"] // 2)
        pts = [root + V(sx * 0.02 * t, -0.03 * t, length * t) + V(0.01 * math.sin(t * 6.0 + k), 0, 0)
               for t in mb.spread(seg)]
        mb.tube(m, pts, lambda t: (0.012 * (1.0 - 0.6 * t), 0.003), 3,
                lambda t, v, k=k: dict(uv=(t, 0.3 * k), w=t, part=mb.STRAND, col=mixc(WEED, WEED_DARK, t)),
                "wrap weed", up_hint=V(0, 1, 0))


# ---------------------------------------------------------------------------------------------------------------


def build(q, name):
    m = mb.Mesh()
    body(m, q)
    head(m, q)
    mask(m, q)
    ears(m, q)
    neck(m, q)
    for sx in (1.0, -1.0):
        arm(m, q, sx)
    fluke(m, q)
    hip_fins(m, q)
    hair(m, q)
    necklace(m, q)
    wrap(m, q)
    obj = mb.make(m, name, (0.55, 0.62, 0.58))
    lo = [min(v[i] for v in m.verts) for i in range(3)]
    hi = [max(v[i] for v in m.verts) for i in range(3)]
    print("BOX %s: x %.3f..%.3f y %.3f..%.3f z %.3f..%.3f" % (name, lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
    return obj


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    os.makedirs(OUT, exist_ok=True)
    made = []
    for ending, q in (("", Q["full"]), ("_lo", Q["low"]), ("_game", Q["game"])):
        obj = build(q, NAME + ending)
        mb.export_one(obj, os.path.join(OUT, NAME + ending + ".glb"))
        made.append((ending.strip("_") + "_" if ending else "", obj))
    made[1][1].location.x = 1.0
    made[2][1].location.x = -1.0
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, NAME + ".blend"))
    for _, obj in made:
        obj.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        L = 2.0
        views = [("left", (-1, 0, 0), (0, 0, 0), 1.1 * L), ("right", (1, 0, 0), (0, 0, 0), 1.1 * L),
                 ("front", (0, 0, -1), (0, 0, 0), 0.6 * L), ("back", (0, 0, 1), (0, 0, 0), 0.6 * L),
                 ("top", (0, 1, 0.001), (0, 0, 0), 1.1 * L), ("under", (0, -1, 0.001), (0, 0, 0), 1.1 * L),
                 ("quarter", (-0.8, 0.5, -0.7), (0, 0, -0.2), 1.0 * L),
                 ("head", (-0.6, -0.25, -1.0), (0, 0.05, -0.8), 0.32), ("headside", (-1, 0, 0), (0, 0.05, -0.75), 0.4),
                 ("hand", (-0.5, -0.6, 0.3), (0.3, -0.13, -0.15), 0.35)]
        mb.render(PREVIEW, [(p, o) for p, o in made if p != "lo_"] + [made[1]], views)


if __name__ == "__main__":
    main()
