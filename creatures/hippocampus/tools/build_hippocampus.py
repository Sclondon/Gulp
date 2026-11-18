"""Builds the hippocampus (creatures/hippocampus) and exports it for Godot.

Run from the game's root (or from GameCommon's godot/hippocampus/files):
    blender --background --python creatures/hippocampus/tools/build_hippocampus.py
    blender --background --python creatures/hippocampus/tools/build_hippocampus.py -- <preview folder>

Writes creatures/hippocampus/models/hippocampus.glb (full), hippocampus_game.glb (the game model, Twilight Princess
weight) and hippocampus_lo.glb (far off), and the editable creatures/hippocampus/tools/hippocampus.blend. Each is one
still mesh with one surface, worn with creatures/sea_myth/sea_myth.gdshader (what each point tells it: tools/myth_build.py
there). It prints a WINDING line for each (nothing inside out) and a BOX line.

The sea-horse of old maps (the user's ask and the concept picture, tools/art_src/concept_mythical.jpg in Gulp; nothing
traced): a horse's head, neck, chest and forelegs, the legs ending in hooves with webbed fins behind them, a finned crest
along the neck and a mane of kelp, the body running back into a long scaled fish tail that curls down and under at its
end in a coil (as a sea-horse's does), a fin along its back all the way. The kelpie is the same model in another look:
darker, with weed draped over it (KELPIE points: folded away unless the shader's `kelpie` is on).

`xm` below is metres behind the tip of its muzzle; Godot's z is xm - HALF. The neck, body and tail are one loft along
one curve, in the middle plane (x 0); the coil turns as the tail goes back, so the back of the tail stays on the outside.
"""

import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(HERE, "..", "..", "sea_myth", "tools"))
import myth_build as mb  # noqa: E402
from myth_build import V, lin, mixc, smooth, lerp, hash1, TAU, PI  # noqa: E402

OUT = os.path.join(HERE, "..", "models")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = ARGS[0] if ARGS else ""
NAME = "hippocampus"
HALF = 1.75

TEAL = lin((0.42, 0.6, 0.56))
TEAL_DARK = lin((0.28, 0.43, 0.41))
BELLY = lin((0.66, 0.73, 0.66))
MUZZLE = lin((0.38, 0.5, 0.48))
HOOF = lin((0.15, 0.14, 0.13))
FIN = lin((0.66, 0.42, 0.25))
FIN_EDGE = lin((0.82, 0.6, 0.38))
KELP = lin((0.56, 0.5, 0.2))
KELP_DARK = lin((0.36, 0.38, 0.13))
EYE = lin((0.05, 0.04, 0.035))
MOUTH = lin((0.42, 0.18, 0.2))
DRAPE = lin((0.22, 0.26, 0.1))
DRAPE_DARK = lin((0.14, 0.17, 0.08))

Q = {
    "full": dict(rings=150, cols=36, head_rings=36, head_cols=30, jaw_rings=16, jaw_cols=16, leg_sides=14,
                 leg_rings=28, mane=18, mane_seg=12, mane_sides=4, fin_rows=6, fin_cols=80, ear=8, eye=(16, 4),
                 drape=14, drape_seg=10, foot_fin=(6, 10)),
    "game": dict(rings=52, cols=14, head_rings=12, head_cols=14, jaw_rings=6, jaw_cols=8, leg_sides=6,
                 leg_rings=11, mane=10, mane_seg=5, mane_sides=3, fin_rows=1, fin_cols=26, ear=4, eye=(8, 2),
                 drape=9, drape_seg=4, foot_fin=(2, 4)),
    "low": dict(rings=22, cols=7, head_rings=5, head_cols=7, jaw_rings=3, jaw_cols=4, leg_sides=4,
                leg_rings=5, mane=4, mane_seg=3, mane_sides=3, fin_rows=1, fin_cols=14, ear=0, eye=(5, 1),
                drape=4, drape_seg=2, foot_fin=(1, 2)),
}


def P(x, y, xm):
    return V(x, y, xm - HALF)


def interp(values, f):
    """Values at control points, read at a float index (each a Catmull-Rom of its neighbours)."""
    n = len(values) - 1
    f = max(0.0, min(float(n), f))
    i = min(int(f), n - 1)
    t = f - i
    out = []
    for k in range(len(values[0])):
        p0 = values[max(i - 1, 0)][k]
        p1 = values[i][k]
        p2 = values[i + 1][k]
        p3 = values[min(i + 2, n)][k]
        t2 = t * t
        out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t2 * t))
    return out


# ---------------------------------------------------------------------------------------------------------------
# The spine: neck, body, tail, coil. (xm, height) and the section there: half-width, above the line, below it.

COIL_C = (3.0, -0.63)
COIL_R = 0.4
COIL_TURN = 1.35


def coil_points():
    pts = []
    sweep = COIL_TURN * TAU
    steps = 14
    for i in range(steps + 1):
        d = sweep * i / steps
        th = PI / 4.0 - d
        r = COIL_R * (1.0 - 0.0966 * d)
        pts.append((COIL_C[0] + r * math.cos(th), COIL_C[1] + r * math.sin(th)))
    return pts


SPINE = [
    ((0.47, 0.9), (0.085, 0.105, 0.11)),
    ((0.6, 0.77), (0.105, 0.14, 0.16)),
    ((0.77, 0.53), (0.14, 0.18, 0.24)),
    ((0.98, 0.28), (0.205, 0.22, 0.31)),
    ((1.25, 0.13), (0.21, 0.21, 0.26)),
    ((1.56, 0.05), (0.17, 0.17, 0.19)),
    ((1.98, -0.05), (0.15, 0.155, 0.155)),
    ((2.5, -0.13), (0.122, 0.128, 0.122)),
    ((2.9, -0.21), (0.1, 0.105, 0.098)),
]
COIL = coil_points()
for k, (z, y) in enumerate(COIL[1:], 1):
    f = k / (len(COIL) - 1)
    r = lerp(0.085, 0.016, f ** 0.9)
    SPINE.append(((z, y), (r * 0.9, r, r)))
CURVE = mb.Curve([P(0.0, y, xm) for (xm, y), _ in SPINE])
SIZES = [s for _, s in SPINE]
# (where along the curve the horse's body gives way to the fish's tail)
HIP_S = 0.27


def spine_frame(s):
    p = CURVE.at(s)
    t = CURVE.tangent(s)
    ex = V(1.0, 0.0, 0.0)
    ey = t.cross(ex).normalized()
    a, bu, bd = interp(SIZES, CURVE.param(s))
    return p, t, ex, ey, a, bu, bd


def body_point(s, th, out=0.0):
    p, t, ex, ey, a, bu, bd = spine_frame(s)
    n = 2.0 + 0.4 * smooth(0.1, 0.25, s) * (1.0 - smooth(0.3, 0.4, s))
    q = mb.section_point(p, ex, ey, a + out, bu + out, bd + out, n, th)
    return q


def body_colour(s, v):
    belly = 1.0 - abs(v - 0.5) * 2.0
    top = mixc(TEAL, TEAL_DARK, smooth(0.25, 0.6, s) * 0.6)
    c = mixc(top, BELLY, smooth(0.55, 0.9, belly) * (0.8 - 0.4 * smooth(0.3, 0.6, s)))
    c = mixc(c, TEAL_DARK, 0.4 * smooth(0.7, 1.0, 1.0 - belly) * smooth(0.0, 0.1, s))
    return c, smooth(HIP_S - 0.03, HIP_S + 0.05, s)


def body(m, q):
    gather = lambda s: 1.0 + 1.3 * math.exp(-((s - 0.1) / 0.1) ** 2) + 0.3 * smooth(0.6, 1.0, s)
    ss = mb.spread(q["rings"], gather)
    cols = q["cols"]
    rings, centres = [], []
    for s in ss:
        ring = []
        for j in range(cols):
            th = TAU * j / cols
            v = th / TAU
            col, scaly = body_colour(s, v)
            ring.append(m.add(body_point(s, th), uv=(s * CURVE.length, v), col=col, mask=scaly))
        rings.append(ring)
        centres.append(CURVE.at(s))
    t0 = CURVE.tangent(0.0)
    t1 = CURVE.tangent(1.0)
    start = m.add(CURVE.at(0.0) - t0 * 0.03, uv=(0.0, 0.0), col=TEAL)
    tip = m.add(CURVE.at(1.0) + t1 * 0.02, uv=(CURVE.length, 0.0), col=TEAL_DARK, mask=1.0)
    mb.loft(m, rings, "body", cap0=(start, -t0), cap1=(tip, t1), centres=centres)


# ---------------------------------------------------------------------------------------------------------------
# The head: one loft from behind the ears to the muzzle; the lower jaw its own part.

HEAD_BACK = P(0.0, 0.915, 0.46)
MUZZLE_TIP = P(0.0, 0.6, 0.04)
HEAD_AXIS = (MUZZLE_TIP - HEAD_BACK).normalized()
HEAD_LEN = (MUZZLE_TIP - HEAD_BACK).length
HEAD_UP = V(1, 0, 0).cross(HEAD_AXIS).normalized()
if HEAD_UP.y < 0.0:
    HEAD_UP = -HEAD_UP
MOUTH_LINE = -0.032
# (t along the head from its back to the muzzle: half-width, above, below, its middle moved along HEAD_UP)
HEAD = [
    (0.0, 0.08, 0.075, 0.085, 0.0),
    (0.12, 0.105, 0.092, 0.15, -0.012),
    (0.26, 0.105, 0.09, 0.19, -0.03),
    (0.4, 0.088, 0.082, 0.14, -0.025),
    (0.52, 0.07, 0.072, 0.08, -0.012),
    (0.63, 0.062, 0.066, 0.045, -0.004),
    (0.76, 0.06, 0.062, 0.04, 0.0),
    (0.88, 0.072, 0.068, 0.045, 0.0),
    (0.96, 0.068, 0.06, 0.04, 0.0),
    (1.0, 0.05, 0.045, 0.032, 0.0),
]
JAW_HINGE_T = 0.5


def head_section(t):
    rows = HEAD
    i = 0
    while i < len(rows) - 2 and rows[i + 1][0] < t:
        i += 1
    f = (t - rows[i][0]) / (rows[i + 1][0] - rows[i][0])
    vals = [lerp(rows[i][k], rows[i + 1][k], smooth(0.0, 1.0, f)) for k in range(1, 5)]
    return vals


def head_point(t, th, out=0.0):
    a, bu, bd, c = head_section(t)
    centre = HEAD_BACK + HEAD_AXIS * HEAD_LEN * t + HEAD_UP * c
    return mb.section_point(centre, V(1, 0, 0), HEAD_UP, a + out, bu + out, bd + out, 2.2, th)


def head(m, q):
    ts = mb.spread(q["head_rings"], lambda t: 1.0 + 0.8 * smooth(0.55, 1.0, t))
    cols = q["head_cols"]
    rings, centres = [], []
    for t in ts:
        ring = []
        for j in range(cols):
            th = TAU * j / cols
            p = head_point(t, th)
            under = smooth(0.3, 0.45, abs(th / TAU - 0.5) * -1.0 + 0.5)
            col = mixc(TEAL, MUZZLE, smooth(0.7, 0.95, t))
            # (the underside of the muzzle is the roof of the mouth)
            col = mixc(col, MOUTH, smooth(0.56, 0.64, t) * smooth(0.36, 0.44, 0.5 - abs(th / TAU - 0.5)))
            col = mixc(col, BELLY, 0.3 * under * (1.0 - smooth(0.5, 0.6, t)))
            ring.append(m.add(p, uv=(t * HEAD_LEN, th / TAU), col=col))
        rings.append(ring)
        centres.append(HEAD_BACK + HEAD_AXIS * HEAD_LEN * t)
    back = m.add(HEAD_BACK - HEAD_AXIS * 0.04, uv=(0.0, 0.0), col=TEAL)
    tip = m.add(MUZZLE_TIP + HEAD_AXIS * 0.005, uv=(HEAD_LEN, 0.0), col=MUZZLE)
    mb.loft(m, rings, "head", cap0=(back, -HEAD_AXIS), cap1=(tip, HEAD_AXIS), centres=centres)


def jaw_hinge():
    return HEAD_BACK + HEAD_AXIS * HEAD_LEN * JAW_HINGE_T + HEAD_UP * MOUTH_LINE


def jaw(m, q):
    """The lower jaw: flat on top (the floor of the mouth, dark), the chin and lower lip below; it turns down
    about the corner of the mouth."""
    ts = mb.spread(q["jaw_rings"], lambda t: 1.0 + 0.6 * t)
    cols = q["jaw_cols"]
    rings, centres = [], []
    for k, f in enumerate(ts):
        t = lerp(0.44, 0.985, f)
        a = lerp(0.062, 0.05, f) * (1.0 - 0.5 * smooth(0.85, 1.0, f))
        down = lerp(0.1, 0.055, smooth(0.0, 0.5, f)) * (1.0 - 0.45 * smooth(0.8, 1.0, f))
        centre = HEAD_BACK + HEAD_AXIS * HEAD_LEN * t + HEAD_UP * (MOUTH_LINE - 0.002)
        ring = []
        for j in range(cols):
            th = TAU * j / cols
            p = mb.section_point(centre, V(1, 0, 0), HEAD_UP, a, 0.004, down, 3.0, th)
            top = math.cos(th) > 0.2
            col = MOUTH if top else mixc(MUZZLE, TEAL, 0.3 * (1.0 - f))
            ring.append(m.add(p, uv=(t, th / TAU), part=mb.JAW, col=col))
        rings.append(ring)
        centres.append(centre + HEAD_UP * (-0.02))
    tip_c = HEAD_BACK + HEAD_AXIS * HEAD_LEN * 0.995 + HEAD_UP * (MOUTH_LINE - 0.015)
    tip = m.add(tip_c, uv=(1.0, 0.0), part=mb.JAW, col=MUZZLE)
    back = m.add(HEAD_BACK + HEAD_AXIS * HEAD_LEN * 0.42 + HEAD_UP * (MOUTH_LINE - 0.04), uv=(0.4, 0.0),
                 part=mb.JAW, col=MUZZLE)
    mb.loft(m, rings, "jaw", cap0=(back, -HEAD_AXIS), cap1=(tip, HEAD_AXIS), centres=centres)


def eyes(m, q):
    spokes, rings = q["eye"]
    for sx in (1.0, -1.0):
        t = 0.33
        th = sx * (TAU / 4.0 - 0.55)
        c = head_point(t, th, -0.003)
        centre = HEAD_BACK + HEAD_AXIS * HEAD_LEN * t
        n = (c - centre)
        n = (n - HEAD_AXIS * n.dot(HEAD_AXIS)).normalized()
        n = (n + HEAD_AXIS * 0.25).normalized()
        mb.dome(m, c, n, 0.026, 0.013, spokes, rings,
                lambda r: dict(uv=(r, 0.0), part=mb.EYE, col=mixc(EYE, lin((0.22, 0.16, 0.1)), smooth(0.6, 1.0, r))),
                "eyes", squash=0.8, up=HEAD_UP)


def ears(m, q):
    if q["ear"] == 0:
        return
    for sx in (1.0, -1.0):
        # (a horse's ear: a leaf, cupped forwards, pricked up and a little out)
        root = head_point(0.05, sx * 0.62, -0.015)
        way = (HEAD_UP * 1.0 - HEAD_AXIS * 0.15 + V(sx * 0.3, 0, 0)).normalized()
        pts = [root + way * 0.17 * t + HEAD_AXIS * 0.02 * math.sin(PI * t) for t in mb.spread(4)]
        mb.tube(m, pts, lambda t: (0.034 * math.sin(PI * (0.25 + 0.75 * t)) ** 0.8 + 0.003,
                                   0.014 * (1.0 - t) + 0.003), q["ear"],
                lambda t, v: dict(uv=(t, v), col=mixc(TEAL, TEAL_DARK, t)), "ears", up_hint=HEAD_AXIS)


# ---------------------------------------------------------------------------------------------------------------
# Forelegs

SHOULDER = (0.14, 0.1, 0.96)
ELBOW = (0.165, -0.12, 1.04)
KNEE = (0.17, -0.35, 0.86)
FETLOCK = (0.165, -0.55, 0.93)
HOOF_TOP = (0.16, -0.62, 0.86)
LEG_W = [0.0, 0.3, 0.55, 0.8, 0.92]


def leg(m, q, sx):
    joints = [P(sx * j[0], j[1], j[2]) for j in (SHOULDER, ELBOW, KNEE, FETLOCK, HOOF_TOP)]
    sizes = [(0.095, 0.1), (0.072, 0.078), (0.052, 0.056), (0.046, 0.05), (0.046, 0.048)]
    n = q["leg_rings"]
    pts, ws, rad = [], [], []
    # The path rounds each joint (a curve through points a little either side of it), so that the rings on
    # the inside of a bent knee never cross.
    ctrl = [joints[0]]
    for k in range(1, len(joints) - 1):
        r = 0.05 if k == 1 else 0.065
        ctrl.append(joints[k] + (joints[k - 1] - joints[k]).normalized() * r)
        ctrl.append(joints[k] + (joints[k + 1] - joints[k]).normalized() * r)
    ctrl.append(joints[-1])
    path = mb.Curve(ctrl)
    marks = [0.0, 1.5, 3.5, 5.5, 7.0]
    for t in mb.spread(n):
        c = path.param(t)
        k = 0
        while k < len(marks) - 2 and marks[k + 1] < c:
            k += 1
        f = k + (c - marks[k]) / (marks[k + 1] - marks[k])
        i = min(int(f), len(joints) - 2)
        g = f - i
        p = path.at(t)
        a = lerp(sizes[i][0], sizes[i + 1][0], g)
        b = lerp(sizes[i][1], sizes[i + 1][1], g)
        knob = 0.01 * math.exp(-((f - 2.0) / 0.2) ** 2) + 0.012 * math.exp(-((f - 3.0) / 0.2) ** 2)
        # (the forearm swells below the elbow, as a horse's does)
        swell = 0.014 * math.exp(-((f - 1.35) / 0.3) ** 2)
        pts.append(p)
        ws.append(lerp(LEG_W[i], LEG_W[i + 1], g))
        rad.append((a + knob + swell, b + knob + swell))
    count = len(pts) - 1
    mb.tube(m, pts, lambda t: rad[int(round(t * count))], q["leg_sides"],
            lambda t, v: dict(uv=(t, v), w=ws[int(round(t * count))], part=mb.LIMB,
                              col=mixc(TEAL, TEAL_DARK, smooth(0.5, 0.9, t))), "legs",
            up_hint=V(0, 0, -1), cap_end=False, cap_start=False)
    hoof(m, q, sx, joints[-1], (joints[-1] - joints[-2]).normalized())
    foot_fin(m, q, sx, joints[3], joints[4])


def hoof(m, q, sx, top, way):
    """The hoof: wider at its sole, dark; it points on from the pastern."""
    sole = top + way * 0.085
    pts = [top.lerp(sole, t) for t in mb.spread(2)]
    mb.tube(m, pts, lambda t: (0.045 + 0.016 * t, 0.046 + 0.018 * t), q["leg_sides"],
            lambda t, v: dict(uv=(t, v), w=0.95 + 0.05 * t, part=mb.LIMB, col=HOOF), "hooves",
            up_hint=V(0, 0, -1), cap_end=True, cap_start=True)


def foot_fin(m, q, sx, fetlock, top):
    """A webbed fin behind each fetlock, fanning back and down, its spines and the web between them."""
    rows, cols = q["foot_fin"]
    back = V(0.0, -0.35, 1.0).normalized()

    def point(t, u):
        base = fetlock.lerp(top, 0.1 + 0.6 * u) + V(0, 0, 0.03)
        spine = (back + V(0, -0.6, 0) * u).normalized()
        reach = 0.13 * (0.75 + 0.25 * abs(math.cos(u * 3.0 * PI))) * (1.0 - 0.4 * u)
        return base + spine * reach * t

    mb.blade(m, point, lambda t, u: V(1, 0, 0), lambda t, u: 0.004 * (1.0 - t) * math.sin(PI * u) ** 0.5,
             mb.spread(rows), mb.spread(cols),
             lambda t, u: dict(uv=(u, t), w=0.82 + 0.1 * t, part=mb.LIMB, col=mixc(FIN, FIN_EDGE, t)), "foot fins")


# ---------------------------------------------------------------------------------------------------------------
# Crest, back fin, mane, kelpie weed


def ridge_fin(m, q, s0, s1, height, name, cols):
    """An upright fin along the back between s0 and s1 of the curve: spines leaning back, scalloped between."""
    spines = max(3, int(cols / 3))

    def point(t, u):
        s = lerp(s0, s1, u)
        p, tan, ex, ey, a, bu, bd = spine_frame(s)
        base = p + ey * (bu - 0.012)
        h = height(u) * (0.4 + 0.6 * abs(math.cos(u * spines * PI)) ** 0.6)
        lean = (ey + tan * 0.55).normalized()
        return base + lean * h * t

    def normal(t, u):
        return V(1.0, 0.0, 0.0)

    rows = max(1, q["fin_rows"])
    mb.blade(m, point, normal, lambda t, u: 0.005 * (1.0 - t) * math.sin(PI * u) ** 0.3,
             mb.spread(rows), mb.spread(cols),
             lambda t, u: dict(uv=(u * spines * 0.25, t), w=t, part=mb.FIN_V, col=mixc(FIN, FIN_EDGE, t)), name)


def mane(m, q):
    """Kelp for a mane: long wavy blades from the crest and between the ears, streaming up and back."""
    n = q["mane"]
    for k in range(n):
        h = hash1(k * 4.1 + 0.3)
        f = (k + 0.5) / n
        side = 1.0 if k % 2 else -1.0
        if k == 0:
            # (the forelock: between the ears, lying back over the poll)
            root = head_point(0.08, 0.0, -0.01)
            way = V(0.0, 0.4, 1.0).normalized()
        else:
            s = lerp(0.0, 0.15, f)
            p, tan, ex, ey, a, bu, bd = spine_frame(s)
            root = p + ey * (bu - 0.015) + ex * side * 0.02
            way = (ey * 0.55 + tan * 0.35 + ex * side * 0.3 + V(0, 0.25, 0.45)).normalized()
        length = 0.38 + 0.3 * h
        seg = q["mane_seg"]
        pts = []
        for i in range(seg + 1):
            t = i / seg
            # (up off the crest, then streaming back, waving)
            p = root + way * length * t + V(0, -0.1, 1.0) * 0.35 * length * t * t
            p += V(side * 0.05 * t * t + math.sin(t * 8.0 + k) * 0.035 * t, math.cos(t * 7.0 + k * 2.0) * 0.04 * t, 0.0)
            pts.append(p)
        wide = 0.055 + 0.03 * h
        mb.tube(m, pts, lambda t, wide=wide: (wide * (0.5 + 0.7 * math.sin(PI * min(t * 1.4, 1.0))) * (1.0 - 0.6 * t) + 0.004, 0.006),
                q["mane_sides"],
                lambda t, v, h=h: dict(uv=(t, h), w=t, part=mb.STRAND, col=mixc(KELP, KELP_DARK, t * 0.7 + 0.3 * h)),
                "mane", up_hint=V(1, 0, 0), theta0=PI / q["mane_sides"])


def drape(m, q):
    """The kelpie's weed: hanging from its neck, its back and its tail (KELPIE points: only in that look)."""
    n = q["drape"]
    for k in range(n):
        h = hash1(k * 7.7 + 1.1)
        s = lerp(0.04, 0.62, (k + 0.5) / n) + (h - 0.5) * 0.03
        p, tan, ex, ey, a, bu, bd = spine_frame(s)
        side = 1.0 if k % 2 else -1.0
        root = p + ey * bu * 0.75 + ex * side * a * 0.65
        length = 0.25 + 0.3 * h
        seg = q["drape_seg"]
        pts = []
        for i in range(seg + 1):
            t = i / seg
            q0 = root + ex * side * 0.05 * math.sin(min(t * 3.0, 1.0) * PI * 0.5) + V(0, -1, 0.3).normalized() * length * t
            q0 += V(math.sin(t * 6.0 + k) * 0.03, 0.0, math.cos(t * 5.0 + k) * 0.02) * t
            pts.append(q0)
        mb.tube(m, pts, lambda t: (0.045 * (1.0 - 0.6 * t) + 0.004, 0.006), 3,
                lambda t, v, h=h: dict(uv=(t, h), w=t, part=mb.KELPIE, col=mixc(DRAPE, DRAPE_DARK, t)),
                "kelpie weed", up_hint=V(0, 0, 1), theta0=PI / 3.0)


# ---------------------------------------------------------------------------------------------------------------


def build(q, name):
    m = mb.Mesh()
    body(m, q)
    head(m, q)
    jaw(m, q)
    eyes(m, q)
    ears(m, q)
    for sx in (1.0, -1.0):
        leg(m, q, sx)
    ridge_fin(m, q, 0.02, 0.16, lambda u: 0.13 * math.sin(PI * (0.12 + 0.88 * u)) ** 0.6, "crest",
              max(6, q["fin_cols"] // 3))
    ridge_fin(m, q, 0.24, 0.965, lambda u: (0.19 - 0.13 * u) * smooth(0.0, 0.05, u) * (1.0 - smooth(0.96, 1.0, u)) + 0.004,
              "back fin", q["fin_cols"])
    mane(m, q)
    drape(m, q)
    obj = mb.make(m, name, (0.33, 0.5, 0.47))
    lo = [min(v[i] for v in m.verts) for i in range(3)]
    hi = [max(v[i] for v in m.verts) for i in range(3)]
    print("BOX %s: x %.3f..%.3f y %.3f..%.3f z %.3f..%.3f" % (name, lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
    print("CURVE length %.3f; jaw hinge (y, z) %.4f, %.4f; shoulder %s; knee %s" % (
        CURVE.length, jaw_hinge().y, jaw_hinge().z, tuple(round(c, 3) for c in P(*SHOULDER[:2], SHOULDER[2])),
        tuple(round(c, 3) for c in P(*KNEE[:2], KNEE[2]))))
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
    made[1][1].location.x = 2.0
    made[2][1].location.x = -2.0
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, NAME + ".blend"))
    for _, obj in made:
        obj.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        L = 3.6
        views = [("left", (-1, 0, 0), (0, 0.1, 0), 1.1 * L), ("right", (1, 0, 0), (0, 0.1, 0), 1.1 * L),
                 ("front", (0, 0, -1), (0, 0.1, 0), 0.6 * L), ("back", (0, 0, 1), (0, 0.1, 0), 0.6 * L),
                 ("top", (0, 1, 0.001), (0, 0, 0), 1.1 * L), ("under", (0, -1, 0.001), (0, 0, 0), 1.1 * L),
                 ("quarter", (-0.8, 0.4, -0.7), (0, 0.1, -0.2), 1.0 * L),
                 ("head", (-1.0, 0.25, -0.6), (0, 0.75, -1.5), 0.9), ("legs", (-0.8, -0.2, -0.6), (0.1, -0.3, -0.85), 1.1)]
        mb.render(PREVIEW, [(p, o) for p, o in made if p != "lo_"] + [made[1]], views)


if __name__ == "__main__":
    main()
