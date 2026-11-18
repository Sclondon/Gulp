"""Builds the deep spawn (creatures/deep_spawn) and exports it for Godot.

Run from the game's root (or from GameCommon's godot/deep-spawn/files):
    blender --background --python creatures/deep_spawn/tools/build_deep_spawn.py
    blender --background --python creatures/deep_spawn/tools/build_deep_spawn.py -- <preview folder>

Writes creatures/deep_spawn/models/deep_spawn.glb (full), deep_spawn_game.glb (the game model, Twilight Princess
weight) and deep_spawn_lo.glb (far off), and the editable creatures/deep_spawn/tools/deep_spawn.blend. Each is one still
mesh with one surface, worn with creatures/sea_myth/sea_myth.gdshader (what each point tells it: tools/myth_build.py
there). It prints a WINDING line for each (nothing inside out) and a BOX line.

The old one's fish-spawn (the user's "old ones fish spawn creatues of the deep", and the concept picture,
tools/art_src/concept_mythical.jpg in Gulp; of our own design, nothing traced): a pale bloated fish, lumpy, with a
cluster of six small dark eyes over a round mouth ringed with pink tentacles that writhe (and spread when it opens its
mouth, `gape`), the mouth a dark funnel; long ragged fins and trailing membranes; rows of blue-white lights along its
flanks (drawn by the shader where COLOR.a says).

`xm` below is metres behind the front of its lips; Godot's z is xm - HALF.
"""

import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(HERE, "..", "..", "sea_myth", "tools"))
import myth_build as mb  # noqa: E402
from myth_build import V, lin, mixc, smooth, lerp, hash1, TAU, PI  # noqa: E402

OUT = os.path.join(HERE, "..", "models")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = ARGS[0] if ARGS else ""
NAME = "deep_spawn"
HALF = 0.706
MOUTH_Y = -0.015

PALE = lin((0.8, 0.82, 0.86))
PALE_BELLY = lin((0.9, 0.88, 0.9))
BRUISE = lin((0.62, 0.58, 0.7))
LIP = lin((0.8, 0.5, 0.56))
THROAT = lin((0.22, 0.06, 0.1))
EYE = lin((0.03, 0.025, 0.035))
SOCKET = lin((0.58, 0.52, 0.6))
FIN = lin((0.76, 0.79, 0.84))
FIN_EDGE = lin((0.9, 0.92, 0.95))
TENT = lin((0.84, 0.55, 0.62))
TENT_TIP = lin((0.9, 0.7, 0.74))

Q = {
    "full": dict(rings=70, cols=40, tent=9, tent_seg=14, tent_sides=6, eye=(14, 4), fin_rows=6, fin_cols=24,
                 pec=(6, 14), fil=4, fil_seg=10),
    "game": dict(rings=21, cols=14, tent=9, tent_seg=5, tent_sides=4, eye=(8, 2), fin_rows=2, fin_cols=10,
                 pec=(2, 6), fil=4, fil_seg=4),
    "low": dict(rings=10, cols=7, tent=6, tent_seg=3, tent_sides=3, eye=(4, 1), fin_rows=1, fin_cols=4,
                pec=(1, 3), fil=0, fil_seg=2),
}


def P(x, y, xm):
    return V(x, y, xm - HALF)


# (xm, middle height, half-width, above, below)
PROFILE = [
    (0.03, MOUTH_Y, 0.075, 0.075, 0.075),
    (0.07, -0.005, 0.128, 0.135, 0.122),
    (0.15, 0.01, 0.182, 0.205, 0.182),
    (0.27, 0.02, 0.215, 0.26, 0.236),
    (0.42, 0.02, 0.225, 0.275, 0.25),
    (0.6, 0.018, 0.205, 0.25, 0.222),
    (0.78, 0.02, 0.165, 0.2, 0.18),
    (0.95, 0.025, 0.12, 0.15, 0.13),
    (1.1, 0.03, 0.08, 0.1, 0.086),
    (1.22, 0.03, 0.05, 0.068, 0.056),
    (1.31, 0.03, 0.034, 0.05, 0.041),
    (1.36, 0.03, 0.024, 0.034, 0.03),
]
TAIL_END = 1.385


def profile_at(xm):
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
    for k in range(5):
        p0 = rows[max(i - 1, 0)][k]
        p1 = rows[i][k]
        p2 = rows[i + 1][k]
        p3 = rows[min(i + 2, len(rows) - 1)][k]
        f2 = f * f
        out.append(0.5 * (2 * p1 + (-p0 + p2) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f2 + (-p0 + 3 * p1 - 3 * p2 + p3) * f2 * f))
    return out


def lumps(xm, th):
    """Its bloated, lumpy skin: swellings here and there, a bulging brow over the eyes, a sagging throat."""
    s = smooth(0.05, 0.25, xm) * (1.0 - smooth(0.9, 1.2, xm))
    b = 1.0 + 0.075 * math.sin(3.0 * th + 7.0 * xm) * math.sin(11.0 * xm + 1.0) * s
    b += 0.05 * math.sin(5.0 * th - 4.0 * xm) * s * 0.6
    brow = math.exp(-((xm - 0.17) / 0.07) ** 2) * math.exp(-(math.sin(th / 2.0) / 0.35) ** 2)
    throat = math.exp(-((xm - 0.32) / 0.12) ** 2) * math.exp(-((abs(th - PI)) / 0.6) ** 2)
    return b + 0.07 * brow + 0.08 * throat


def surface(xm, th, out=0.0):
    _, cy, a, bu, bd = profile_at(xm)
    c = P(0.0, cy, xm)
    p = mb.section_point(c, V(1, 0, 0), V(0, 1, 0), a, bu, bd, 2.0, th, lumps(xm, th))
    if out:
        d = p - c
        d.z = 0.0
        p += d.normalized() * out
    return p


def body_colour(xm, v):
    belly = 1.0 - abs(v - 0.5) * 2.0
    c = mixc(PALE, PALE_BELLY, smooth(0.5, 0.9, belly))
    blot = 0.5 + 0.5 * math.sin(v * 31.0 + xm * 17.0) * math.sin(v * 13.0 - xm * 23.0)
    c = mixc(c, BRUISE, 0.35 * blot * smooth(0.15, 0.3, xm))
    c = mixc(c, LIP, 0.6 * (1.0 - smooth(0.03, 0.09, xm)))
    # (its lights: in rows down its flanks, from behind its head to its tail stock)
    d = abs(v - 0.25) if v < 0.5 else abs(v - 0.75)
    side = math.exp(-((d - 0.02) / 0.045) ** 2) + 0.8 * math.exp(-((d - 0.12) / 0.035) ** 2)
    glow = side * smooth(0.18, 0.3, xm) * (1.0 - smooth(1.15, 1.3, xm))
    return c, glow


def body(m, q):
    gather = lambda t: 1.0 + 1.0 * math.exp(-(t / 0.15) ** 2) + 0.5 * smooth(0.8, 1.0, t)
    xs = [lerp(PROFILE[0][0], PROFILE[-1][0], t) for t in mb.spread(q["rings"], gather)]
    cols = q["cols"]
    rings, centres = [], []
    for xm in xs:
        ring = []
        for j in range(cols):
            th = TAU * j / cols
            col, glow = body_colour(xm, th / TAU)
            ring.append(m.add(surface(xm, th), uv=(xm, th / TAU), col=col, mask=glow))
        rings.append(ring)
        centres.append(P(0.0, profile_at(xm)[1], xm))
    tip = m.add(P(0.0, 0.03, TAIL_END), uv=(TAIL_END, 0.0), col=PALE)
    mb.loft(m, rings, "body", cap1=(tip, V(0, 0, 1)), centres=centres)
    mouth(m, q, rings[0])


def mouth(m, q, lip):
    """The mouth: the lips rolled in from the body's first ring to a dark funnel."""
    cols = len(lip)
    inner = []
    throat = []
    for j in range(cols):
        th = TAU * j / cols
        a = th
        inner.append(m.add(P(0.052 * math.sin(a), MOUTH_Y + 0.05 * math.cos(a), 0.012), uv=(0.0, th / TAU), col=LIP))
        throat.append(m.add(P(0.03 * math.sin(a), MOUTH_Y + 0.028 * math.cos(a), 0.085), uv=(0.0, th / TAU),
                            col=THROAT))
    deep = m.add(P(0.0, MOUTH_Y, 0.13), uv=(0.0, 0.0), col=THROAT)
    axis = P(0.0, MOUTH_Y, 0.0)
    for j in range(cols):
        k = (j + 1) % cols
        quad = (lip[j], lip[k], inner[k], inner[j])
        m.face(quad, V(0, 0, -1), "mouth")
        quad = (inner[j], inner[k], throat[k], throat[j])
        c = m.centre(quad)
        inward = V(axis.x - c.x, axis.y - c.y, 0.0).normalized() + V(0, 0, -0.3)
        m.face(quad, inward, "mouth")
        tri = (throat[j], throat[k], deep)
        m.face(tri, V(0, 0, -1), "mouth")


def eyes(m, q):
    """A cluster of six small dark eyes over the mouth, each in a pale swollen socket."""
    spokes, rings = q["eye"]
    places = [(0.26, 0.07, 0.022), (-0.26, 0.07, 0.022), (0.0, 0.1, 0.025), (0.56, 0.105, 0.02),
              (-0.56, 0.105, 0.02), (0.0, 0.152, 0.018)]
    for th, xm, r in places:
        c = surface(xm, th, -0.004)
        n = (c - P(0.0, profile_at(xm)[1], xm))
        n = (n.normalized() + V(0, 0, -0.9)).normalized()
        # (the socket: a low pale swelling round the eye)
        mb.dome(m, c - n * 0.004, n, r * 1.45, r * 0.45, spokes, max(1, rings - 1),
                lambda t: dict(uv=(t, 0.0), col=mixc(SOCKET, PALE, t)), "sockets", up=V(0, 1, 0))
        mb.dome(m, c + n * r * 0.18, n, r, r * 0.7, spokes, rings,
                lambda t: dict(uv=(t, 0.0), part=mb.EYE, col=EYE), "eyes", up=V(0, 1, 0))


def tentacles(m, q):
    n = q["tent"]
    for k in range(n):
        h = hash1(k * 2.9 + 0.7)
        a = TAU * (k + 0.5) / n
        root = P(0.06 * math.sin(a), MOUTH_Y + 0.058 * math.cos(a), 0.022)
        out = V(math.sin(a), math.cos(a), 0.0)
        length = 0.24 + 0.17 * h
        seg = q["tent_seg"]
        pts = []
        for i in range(seg + 1):
            t = i / seg
            p = root + V(0, 0, -1) * length * 0.4 * math.sin(t * PI * 0.5) + out * length * 0.3 * math.sin(t * PI * 0.5)
            # (they droop and curl)
            p += V(0, -0.75, 0.15) * length * t * t
            p += V(math.sin(t * 5.0 + k), math.cos(t * 4.0 + k * 1.3), 0.0) * 0.03 * t * t
            pts.append(p)
        mb.tube(m, pts, lambda t: (0.017 * (1.0 - 0.8 * t) + 0.002, 0.015 * (1.0 - 0.8 * t) + 0.002), q["tent_sides"],
                lambda t, v, h=h: dict(uv=(t * length, h), w=t, part=mb.TENTACLE, col=mixc(TENT, TENT_TIP, t)),
                "tentacles", up_hint=out)


def ragged(u, k, depth=0.35, freq=23.0):
    """A ragged edge: notches and tatters along u."""
    return 1.0 - depth * (0.5 + 0.5 * math.sin(u * freq + k)) * (0.5 + 0.5 * math.sin(u * freq * 0.4 + k * 2.0))


def fins(m, q):
    rows, cols = q["fin_rows"], q["fin_cols"]
    attr = lambda part, k: (lambda t, u: dict(uv=(u, t), w=t, part=part, col=mixc(FIN, FIN_EDGE, t)))

    # The tail fin: forked, ragged, upright.
    def tail(t, u):
        phi = lerp(1.05, -1.05, u)
        reach = 0.27 * (0.55 + 0.45 * abs(2.0 * u - 1.0) ** 0.8) * ragged(u, 1.0, 0.25, 9.0)
        root = P(0.0, 0.03 + lerp(0.035, -0.03, u), 1.31)
        return root + V(0, math.sin(phi), math.cos(phi)) * reach * t

    mb.blade(m, tail, lambda t, u: V(1, 0, 0), lambda t, u: 0.005 * (1.0 - t) * math.sin(PI * u) ** 0.3,
             mb.spread(rows), mb.spread(cols), attr(mb.FIN_V, 1), "tail fin")

    # The fin along its back: a tall spine at the front, ragged and lower behind, its rear trailing.
    def dorsal(t, u):
        xm = lerp(0.36, 1.18, u)
        base = surface(xm, 0.0, -0.01)
        h = (0.2 * math.exp(-((u - 0.15) / 0.18) ** 2) + 0.07 + 0.04 * u) * ragged(u, 3.0)
        return base + V(0, 0.75, 0.66).normalized() * h * t + V(0, 0, 0.12) * t * u

    mb.blade(m, dorsal, lambda t, u: V(1, 0, 0), lambda t, u: 0.005 * (1.0 - t) * math.sin(PI * u) ** 0.3,
             mb.spread(rows), mb.spread(cols + 4), attr(mb.FIN_V, 3), "dorsal fin")

    # Two long pectoral fins behind its head, sweeping back and down, ragged; and two trailing fins under it.
    pr, pc = q["pec"]
    for sx in (1.0, -1.0):
        def pec(t, u, sx=sx):
            xm = lerp(0.27, 0.47, u)
            base = surface(xm, sx * (TAU / 4.0 + 0.45), -0.012)
            way = V(sx * 0.45, -0.35, 1.0).normalized()
            reach = 0.42 * (0.55 + 0.45 * u) * ragged(u, 5.0 + sx, 0.4, 7.0)
            return base + way * reach * t + V(0, -0.06, 0) * t * t * u

        mb.blade(m, pec, lambda t, u, sx=sx: V(sx * 0.45, 0.85, -0.2).normalized(),
                 lambda t, u: 0.004 * (1.0 - t) * math.sin(PI * u) ** 0.3, mb.spread(pr), mb.spread(pc),
                 attr(mb.FIN_H, 5), "pectoral fins")

        def ventral(t, u, sx=sx):
            xm = lerp(0.62, 0.9, u)
            base = surface(xm, sx * (PI - 0.35), -0.01)
            way = V(sx * 0.2, -0.75, 0.65).normalized()
            reach = 0.3 * (0.5 + 0.5 * u) * ragged(u, 7.0 + sx, 0.3, 6.0)
            return base + way * reach * t + V(0, 0, 0.15) * t * t

        mb.blade(m, ventral, lambda t, u: V(1, 0, 0), lambda t, u: 0.004 * (1.0 - t) * math.sin(PI * u) ** 0.3,
                 mb.spread(pr), mb.spread(pc), attr(mb.FIN_V, 7), "trailing fins")


def filaments(m, q):
    """Torn membranes trailing from its pectoral and trailing fins."""
    n = q["fil"]
    for k in range(n):
        sx = 1.0 if k % 2 else -1.0
        h = hash1(k * 6.1)
        if k < 2:
            root = surface(0.42, sx * (TAU / 4.0 + 0.6), -0.01)
            way = V(sx * 0.25, -0.45, 1.0).normalized()
            length = 0.5 + 0.15 * h
        else:
            root = surface(0.85, sx * (PI - 0.3), -0.01)
            way = V(sx * 0.1, -0.6, 1.0).normalized()
            length = 0.42 + 0.15 * h
        seg = q["fil_seg"]
        pts = [root + way * length * t + V(math.sin(t * 6.0 + k) * 0.03, 0.0, 0.0) * t for t in mb.spread(seg)]
        mb.tube(m, pts, lambda t: (0.02 * (1.0 - 0.7 * t) + 0.002, 0.003), 3,
                lambda t, v, h=h: dict(uv=(t, h), w=t, part=mb.STRAND, col=mixc(FIN, FIN_EDGE, t)),
                "filaments", up_hint=V(sx, 0, 0), theta0=PI / 3.0)


def build(q, name):
    m = mb.Mesh()
    body(m, q)
    eyes(m, q)
    tentacles(m, q)
    fins(m, q)
    filaments(m, q)
    obj = mb.make(m, name, (0.8, 0.82, 0.86))
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
        L = 1.9
        views = [("left", (-1, 0, 0), (0, 0, 0), 1.1 * L), ("right", (1, 0, 0), (0, 0, 0), 1.1 * L),
                 ("front", (0, 0, -1), (0, 0, 0), 0.7 * L), ("back", (0, 0, 1), (0, 0, 0), 0.7 * L),
                 ("top", (0, 1, 0.001), (0, 0, 0), 1.1 * L), ("under", (0, -1, 0.001), (0, 0, 0), 1.1 * L),
                 ("quarter", (-0.8, 0.4, -0.7), (0, 0, -0.1), 1.0 * L),
                 ("head", (-0.5, 0.25, -1.0), (0, 0.0, -0.75), 0.6)]
        mb.render(PREVIEW, [(p, o) for p, o in made if p != "lo_"] + [made[1]], views)


if __name__ == "__main__":
    main()
