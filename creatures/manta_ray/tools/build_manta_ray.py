"""Builds the giant oceanic manta ray (creatures/manta_ray) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/manta_ray/tools/build_manta_ray.py
    blender --background --python creatures/manta_ray/tools/build_manta_ray.py -- <preview folder>   # with pictures

Writes creatures/manta_ray/models/manta_ray.glb (the full model) and manta_ray_lo.glb (far off, phones), and the
editable creatures/manta_ray/tools/manta_ray.blend (this folder has a .gdignore). Each model is one still mesh with
one surface: the shader (manta_ray.gdshader) draws every marking, flaps the wings, opens the mouth and trails the
tail. It prints a WINDING line (the check that nothing is inside out), a SIZE line and a SHADER line (the
numbers the shader must have: change the SPEC here, build, and copy them into the shader's constants).

The same builder is in GameCommon's manta-ray, devil-ray and spotted-eagle-ray: only SPECIES below differs, and
SPECS holds all three animals. Improve one copy, copy it to the others.

Everything here is in Godot space (metres, Y up, the nose at -Z) until it is written out. The origin is on the
middle line, half way along the body disc. `zd` below is metres behind the front of the disc (the manta's
mouth, the others' snout tip); `a` is how far out along a wing (0 the middle line, 1 the wing tip).

HOW THE DISC IS BUILT: a ray is a wing. At each of many stations across the span there is a closed section,
like an aircraft wing's: a top skin and a bottom skin from the leading edge to the trailing edge, round at
the front and sharp at the back, thick in the middle of the animal and thin in the wings. The outline seen
from above is `lead(a)` and `trail(a)`; `thick(a, u)` is how thick it is.

THE MOUTH is a pocket let into those sections where the mouth is (across the front of the manta's head;
a slit under the head of the others): two lips that touch, and behind them a dark roof and floor that meet at
the jaw's hinge. The lower jaw (the lower lip, the floor and the skin under it) carries a weight, and the
shader turns it down about the hinge by `gape`.

What a point is, for the shader: UV2.y the part (0 skin, 1 inside the mouth, 2 a cephalic fin, 3 the tail,
4 the dorsal fin, 5 a tail spine, 6 an eye). On the skin and in the mouth: UV.x the jaw's weight (0 does not
move, 1 turns all the way), UV.y how far back from the leading edge (0) to the trailing edge (1), UV2.x +1
on top, -1 beneath, 0 along the edges. On a cephalic fin: UV.x from its root (0) to its tip (1), UV.y metres
across from its top edge, UV2.x metres off the middle of the sheet (+ its inner skin). On the tail: UV.x
from its root to its tip. On the other fins: UV.x root to tip, UV.y leading to trailing edge. On an eye:
UV.x from its middle (0) to its rim (1). (The glTF writer flips V: what is written here is 1 - v.)

THE GAME MODEL (models/manta_ray_game.glb, made in the same run; the .blend holds all three): the same curves and
profiles as the full model with far fewer, better placed points (the user, 2026-11-18: "We should have a twilight
princess model to compare to so we can make low poly versions while maintaining high quality looks and
silhouettes"). Its rows go where the outline and the profile bend most (`greedy`), with more round the eyes, the
mouth and the edges, and every UV, UV2 and part the shader reads, so it swims, opens its mouth and is marked as
the full one is. The full and low models come out exactly as before (their .glb files are byte for byte the same).

THE GILLS (2026-11-18): new parts 7 a gill arch, 8 a gill slit's flap (see gill_flaps / gills below). They are a second surface on
the full and low models, so that the body's surface is the same as before; the game model has one surface.
"""

import math
import os
import sys

import bpy
from mathutils import Vector

SPECIES = "manta_ray"

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "models")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = ARGS[0] if ARGS else ""

SKIN, MOUTH, CEPH, TAIL, DORSAL, SPINE, EYE = range(7)
TAU = math.tau
# True while the game model is being made (see GAME below SPECS): every count then comes from the species'
# "game" numbers, and the full and low models are made exactly as before.
GAME = False


def pick(full, low_value, game_value, low):
    """How many of something: on the game model, the low one, or the full one."""
    if GAME:
        return game_value
    return low_value if low else full


def greedy(fns, seeds, n, max_step):
    """`n` intervals from seeds[0] to seeds[-1], spent where the curves `fns` bend most: each interval longer
    than `max_step` is halved, then the interval whose middle strays furthest from the straight line between its
    ends (in any of `fns`) is halved, until there are `n`. For the game model: its points go where the outline
    and the profile need them."""
    xs = sorted(set(seeds))

    def err(a, b):
        worst = 0.0
        for f in fns:
            fa, fb = f(a), f(b)
            for s in (0.25, 0.5, 0.75):
                x = a + (b - a) * s
                worst = max(worst, abs(f(x) - (fa + (fb - fa) * s)))
        return worst

    changed = True
    while changed:
        changed = False
        for i in range(len(xs) - 1):
            if xs[i + 1] - xs[i] > max_step:
                xs.insert(i + 1, 0.5 * (xs[i] + xs[i + 1]))
                changed = True
                break
    while len(xs) - 1 < n:
        best = max(range(len(xs) - 1), key=lambda i: err(xs[i], xs[i + 1]) if xs[i + 1] - xs[i] > 1e-4 else -1.0)
        xs.insert(best + 1, 0.5 * (xs[best] + xs[best + 1]))
    return xs


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def soft(a):
    """|a| with its corner at the middle line rounded off (0 at 0)."""
    return math.sqrt(a * a + 0.0016) - 0.04


# ---------------------------------------------------------------- the three animals

def manta_lead(a):
    if a <= 0.16:
        return 0.0
    t = (a - 0.16) / 0.84
    return 0.035 * smooth(0.0, 0.1, t) + 0.30 * t ** 1.3 + 0.17 * t ** 5


def manta_trail(a):
    return 0.50 + 0.03 * a ** 6 + 0.47 * (1.0 - soft(a)) ** 1.55


def manta_thick(a, u, zd):
    foil = 2.6 * math.sqrt(u) * (1.0 - u)
    return (0.34 * math.exp(-(a / 0.2) ** 2) + 0.17 * (1.0 - a) ** 1.2 + 0.012) * foil


def devil_lead(a):
    if a <= 0.15:
        return 0.02 * (a / 0.15) ** 2
    t = (a - 0.15) / 0.85
    return 0.02 + 0.07 * smooth(0.0, 0.12, t) + 0.30 * t ** 1.25 + 0.14 * t ** 5


def devil_trail(a):
    return 0.52 + 0.03 * a ** 6 + 0.45 * (1.0 - soft(a)) ** 1.6


def devil_thick(a, u, zd):
    foil = 2.6 * math.sqrt(u) * (1.0 - u)
    return (0.088 * math.exp(-(a / 0.16) ** 2) + 0.04 * (1.0 - a) ** 1.2 + 0.003) * foil


def eagle_lead(a):
    if a <= 0.07:
        return 0.055 * (a / 0.07) ** 2.2
    if a <= 0.13:
        return 0.055 + 0.185 * smooth(0.07, 0.13, a)
    t = (a - 0.13) / 0.87
    return 0.24 + 0.27 * t ** 1.2 + 0.13 * t ** 5


def eagle_trail(a):
    return 0.61 + 0.035 * a ** 6 + 0.355 * (1.0 - soft(a)) ** 1.7


def eagle_thick(a, u, zd):
    foil = 2.6 * math.sqrt(u) * (1.0 - u)
    # (the bill is flat: the head only swells to its full depth behind it)
    bill = 0.42 + 0.58 * smooth(0.02, 0.2, zd)
    return (0.155 * math.exp(-(a / 0.135) ** 2) * bill + 0.07 * (1.0 - a) ** 1.2 + 0.005) * foil


SPECS = {
    "manta_ray": dict(
        title="giant oceanic manta ray", colour=(0.03, 0.03, 0.04),
        half=2.5, disc=2.2, lead=manta_lead, trail=manta_trail, thick=manta_thick, top_share=0.6,
        stations=((0.24, 0.0055), (0.97, 0.0125), (0.997, 0.0045)), around=44,
        mouth="front", mouth_half=0.40, mouth_at=0.0, jaw=0.5, pocket=5,
        ceph=dict(root=(0.5, 0.035, 0.14), along=(0.05, -0.10, -1.0), down=(-0.12, -1.0, 0.0),
                  length=0.58, width=0.30, thick=0.03, roll0=11.0, roll1=18.0, cup=2.6, nt=30, nh=22),
        tail=dict(length=1.5, radius=0.045, start=0.86, rings=44, around=8),
        dorsal=dict(at=0.80, chord=0.2, high=0.11),
        spines=(),
        eye=dict(at=(0.50, 0.035, 0.075), out=(0.8, 0.12, -0.5), radius=0.034),
    ),
    "devil_ray": dict(
        title="Munk's devil ray", colour=(0.3, 0.25, 0.3),
        half=0.5, disc=0.52, lead=devil_lead, trail=devil_trail, thick=devil_thick, top_share=0.6,
        stations=((0.24, 0.008), (0.97, 0.019), (0.997, 0.007)), around=30,
        mouth="under", mouth_half=0.052, mouth_at=0.04, jaw=0.05, pocket=4,
        ceph=dict(root=(0.07, 0.004, 0.045), along=(0.12, -0.16, -1.0), down=(-0.25, -1.0, 0.0),
                  length=0.105, width=0.05, thick=0.007, roll0=66.0, roll1=108.0, cup=14.0, nt=18, nh=14),
        tail=dict(length=0.5, radius=0.011, start=0.86, rings=30, around=6),
        dorsal=dict(at=0.80, chord=0.055, high=0.03),
        spines=(),
        eye=dict(at=(0.083, 0.008, 0.062), out=(0.85, 0.2, -0.4), radius=0.0095),
    ),
    "spotted_eagle_ray": dict(
        title="spotted eagle ray", colour=(0.06, 0.08, 0.15),
        half=1.0, disc=1.15, lead=eagle_lead, trail=eagle_trail, thick=eagle_thick, top_share=0.62,
        stations=((0.16, 0.004), (0.3, 0.008), (0.97, 0.0135), (0.997, 0.0045)), around=40,
        mouth="under", mouth_half=0.05, mouth_at=0.14, jaw=0.07, pocket=4,
        ceph=None,
        tail=dict(length=2.7, radius=0.02, start=0.86, rings=70, around=8),
        dorsal=dict(at=0.84, chord=0.085, high=0.045),
        spines=(0.015, 0.075),
        eye=dict(at=(0.107, 0.03, 0.225), out=(0.85, 0.45, -0.2), radius=0.016),
    ),
}

# The game model's counts (the full and low ones come from SPECS): `gaps` stations across each half of the span,
# placed by `greedy` where the outline and the section's thickness bend most, none more than `max_step` of the
# half span apart (so that the wing bends as a curve); `nu` points round each section's top and bottom skin;
# `pocket` points down each side of the mouth; (along, across) for a cephalic fin, (rings, around) for the
# tail, (spokes, rings) for an eye, (along, across) for the dorsal fin and a spine, and (along an arch, along a
# gill slit's flap) for the gills.
GAMES = {
    "manta_ray": dict(gaps=24, max_step=0.07, nu=18, pocket=3, ceph=(10, 6), tail=(24, 8), eye=(28, 4),
                      dorsal=(5, 4), spines=(5, 3), gills=(2, 3)),
    "devil_ray": dict(gaps=18, max_step=0.1, nu=12, pocket=3, ceph=(7, 5), tail=(16, 6), eye=(24, 3),
                      dorsal=(4, 3), spines=(4, 3), gills=(3, 4)),
    "spotted_eagle_ray": dict(gaps=21, max_step=0.08, nu=15, pocket=3, ceph=None, tail=(30, 8), eye=(26, 3),
                              dorsal=(4, 3), spines=(5, 3), gills=(2, 2)),
}

S = SPECS[SPECIES]
G = GAMES[SPECIES]
HALF = S["half"]
DISC = S["disc"]
MID = DISC * 0.5


def to_b(p):
    return Vector((p.x, -p.z, p.y))


def lead(a):
    return S["lead"](a) * DISC


def trail(a):
    return S["trail"](a) * DISC


def skin(sigma, u, top):
    """A point of the skin: `sigma` across the span (-1 to 1), `u` from the leading edge (0) to the trailing
    edge (1), on the top skin or the bottom one."""
    a = abs(sigma)
    front = lead(a)
    zd = front + (trail(a) - front) * u
    t = S["thick"](a, max(0.0, min(1.0, u)), zd)
    y = t * (S["top_share"] if top else S["top_share"] - 1.0)
    return Vector((sigma * HALF, y, zd - MID))


def skin_at(sigma, zd, top):
    a = abs(sigma)
    front = lead(a)
    return skin(sigma, max(0.0, min(1.0, (zd - front) / (trail(a) - front))), top)


def lateral(x):
    """How far the jaw opens at `x` across the mouth: all the way in the middle, nothing at its corners."""
    return max(0.0, 1.0 - (x / S["mouth_half"]) ** 2) ** 0.45


def jaw_weight(x, zd):
    back = (zd - S["mouth_at"]) / S["jaw"]
    return lateral(x) * (1.0 - smooth(0.12, 1.0, back))


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.data = []
        self.out = []
        self.count = {}

    def add(self, p, uv, part, extra=0.0):
        self.verts.append(Vector(p))
        self.data.append(((uv[0], 1.0 - uv[1]), (extra, 1.0 - part)))
        return len(self.verts) - 1

    def face(self, points, out, name):
        """A face wound so that its front (the side its points go round anticlockwise) is towards `out`."""
        clean = []
        for i in points:
            if i not in clean:
                clean.append(i)
        if len(clean) < 3:
            return
        ps = [self.verts[i] for i in clean]
        n = Vector((0.0, 0.0, 0.0))
        for i in range(len(ps)):
            n += ps[i].cross(ps[(i + 1) % len(ps)])
        if n.length < 1e-13:
            return
        if n.dot(out) < 0.0:
            clean.reverse()
        self.faces.append(tuple(clean))
        self.out.append((Vector(out), name))
        self.count[name] = self.count.get(name, 0) + 1


def stations(low):
    if GAME:
        # (and stations across the mouth, so that the jaw opens as a curve)
        seeds = [0.0, 0.14] + [S["mouth_half"] / HALF * k for k in (0.35, 0.7, 0.92, 1.0)] + [until for until, _ in S["stations"]]
        # (and round the eye, so that the skin there keeps its curve and does not bury the eye)
        seeds += [(S["eye"]["at"][0] + k * S["eye"]["radius"]) / HALF for k in (-1.5, 0.0, 1.5)]
        fns = [lead, trail, lambda a: skin(a, 0.3, True).y, lambda a: skin(a, 0.3, False).y,
               lambda a: skin(a, 0.08, True).y]
        xs = greedy(fns, seeds, G["gaps"], G["max_step"])
        return [-v for v in reversed(xs[1:])] + xs
    xs = [0.0]
    x = 0.0
    for until, step in S["stations"]:
        if low:
            step *= 3.2
        n = max(1, round((until - x) / step))
        for i in range(1, n + 1):
            xs.append(x + (until - x) * i / n)
        x = until
    return [-v for v in reversed(xs[1:])] + xs


def disc(m, low):
    nu = pick(S["around"], max(8, S["around"] // 3), G["nu"], low)
    pocket = pick(S["pocket"], max(2, S["pocket"] // 2), G["pocket"], low)
    us = [0.5 * (1.0 - math.cos(math.pi * k / nu)) for k in range(nu + 1)]
    front = S["mouth"] == "front"
    mouth_half = S["mouth_half"]
    slit = 0
    if not front:
        u0 = (S["mouth_at"] - lead(0.0)) / (trail(0.0) - lead(0.0))
        slit = min(range(1, nu), key=lambda k: abs(us[k] - u0))
    rows = []
    kinds = None
    for sigma in stations(low):
        a = abs(sigma)
        x = sigma * HALF
        inside = abs(x) < mouth_half * 0.999
        bottom_us = list(us)
        if not front:
            # (the bottom skin's lines are drawn together so that one of them runs along the slit)
            pull = 1.0 - smooth(mouth_half, mouth_half * 2.2, abs(x))
            here = (S["mouth_at"] - lead(a)) / (trail(a) - lead(a))
            if pull > 0.0 and 0.0 < here < 1.0:
                for k in range(nu + 1):
                    u = us[k]
                    warped = u * here / us[slit] if u < us[slit] else 1.0 - (1.0 - u) * (1.0 - here) / (1.0 - us[slit])
                    bottom_us[k] = u + (warped - u) * pull
        top = [m.add(skin(sigma, us[k], True), (0.0, us[k]), SKIN, smooth(0.0, 0.05, min(us[k], 1.0 - us[k])))
               for k in range(nu + 1)]
        bottom = [None] * (nu + 1)
        for k in range(1, nu):
            u = bottom_us[k]
            p = skin(sigma, u, False)
            weight = 0.0
            if inside and (front or k > slit):
                weight = jaw_weight(x, p.z + MID)
            bottom[k] = m.add(p, (weight, u), SKIN, -smooth(0.0, 0.05, min(u, 1.0 - u)))
        lip_a = top[0] if front else bottom[slit]
        entries = [lip_a] * (2 * pocket)
        if inside:
            here = Vector(m.verts[lip_a])
            lip_zd = here.z + MID
            entries[0] = m.add(here, (lateral(x), 0.0 if front else bottom_us[slit]), SKIN, -0.02 if front else -1.0)
            back_zd = S["mouth_at"] + S["jaw"]
            low_back = skin_at(sigma, back_zd, False)
            high_back = skin_at(sigma, back_zd, True)
            back = low_back + (high_back - low_back) * 0.42
            wide = lateral(x)
            line = []
            for j in range(1, pocket + 1):
                s = j / pocket
                p = here + (back - here) * s
                zd = p.z + MID
                arch = math.sin(math.pi * s ** 0.8) * wide
                up = skin_at(sigma, zd, True).y - p.y
                down = p.y - skin_at(sigma, zd, False).y
                line.append((p, zd, max(up, 0.0) * 0.55 * arch, max(down, 0.0) * 0.5 * arch))
            for j in range(1, pocket):
                p, zd, up, down = line[j - 1]
                entries[j] = m.add(p - Vector((0.0, down, 0.0)), (jaw_weight(x, zd), 0.5), MOUTH, 0.0)
                entries[2 * pocket - j] = m.add(p + Vector((0.0, up, 0.0)), (0.0, 0.5), MOUTH, 0.0)
            entries[pocket] = m.add(line[-1][0], (0.0, 0.5), MOUTH, 0.0)
        ring = list(top)
        kind = ["skin"] * (nu + 1)
        if front:
            ring += [bottom[k] for k in range(nu - 1, 0, -1)]
            kind += ["skin"] * (nu - 1)
            ring += entries
            kind += ["floor"] * pocket + ["roof"] * pocket
        else:
            ring += [bottom[k] for k in range(nu - 1, slit, -1)]
            kind += ["skin"] * (nu - 1 - slit)
            ring += entries
            kind += ["floor"] * pocket + ["roof"] * pocket
            ring += [bottom[k] for k in range(slit, 0, -1)]
            kind += ["skin"] * slit
        kinds = kind
        middle = skin(sigma, 0.33, True)
        middle.y = 0.0
        rows.append((ring, middle))
    count = len(kinds)
    for r in range(len(rows) - 1):
        one, c1 = rows[r]
        two, c2 = rows[r + 1]
        centre = (c1 + c2) * 0.5
        for j in range(count):
            n = (j + 1) % count
            quad = (one[j], one[n], two[n], two[j])
            if kinds[j] == "skin":
                at = sum((m.verts[q] for q in quad), Vector()) * 0.25
                m.face(quad, at - centre, "skin")
            elif kinds[j] == "floor":
                m.face(quad, Vector((0.0, 1.0, 0.0)), "mouth")
            else:
                m.face(quad, Vector((0.0, -1.0, 0.0)), "mouth")
    # the wing tips: a fan each
    for (ring, centre), way in ((rows[0], -1.0), (rows[-1], 1.0)):
        tip = skin(way, 0.5, True)
        tip.y = 0.0
        tip = m.add(tip, (0.0, 0.5), SKIN, 0.0)
        for j in range(count):
            m.face((tip, ring[j], ring[(j + 1) % count]), Vector((way, 0.0, 0.0)), "skin")


# ---------------------------------------------------------------- the cephalic fins

def ceph_frame():
    c = S["ceph"]
    along = Vector(c["along"]).normalized()
    down = Vector(c["down"])
    down = (down - along * down.dot(along)).normalized()
    inward = along.cross(down)
    if inward.x > 0.0:
        inward = -inward
    return along, down, inward


def ceph_width(t):
    c = S["ceph"]
    return c["width"] * math.sin(math.pi * (0.18 + 0.82 * t)) ** 0.7


def ceph_point(t, h, off, sx, scoops):
    """As the shader has it: a point of a cephalic fin, `t` along it, `h` metres across from its top edge,
    `off` metres off the middle of its sheet, rolled up (scoops 0) or spread (1)."""
    c = S["ceph"]
    along, down, inward = ceph_frame()
    k0 = c["roll0"] + (c["cup"] - c["roll0"]) * scoops
    k1 = c["roll1"] * (1.0 - scoops)
    qx = 0.0
    qy = 0.0
    dh = h / 12.0
    for i in range(12):
        hm = (i + 0.5) * dh
        th = k0 * hm + k1 * hm * hm / (2.0 * c["width"])
        qx += math.cos(th) * dh
        qy += math.sin(th) * dh
    th = k0 * h + k1 * h * h / (2.0 * c["width"])
    mirror = Vector((sx, 1.0, 1.0))
    normal = inward * math.cos(th) - down * math.sin(th)
    root = Vector((c["root"][0], c["root"][1], c["root"][2] - MID))
    p = root + along * (t * c["length"]) + down * qx + inward * qy + normal * off
    return Vector((p.x * mirror.x, p.y, p.z)), Vector((normal.x * sx, normal.y, normal.z))


def cephs(m, low):
    c = S["ceph"]
    nt = pick(c["nt"], max(6, c["nt"] // 3), G["ceph"][0], low)
    nh = pick(c["nh"], max(5, c["nh"] // 3), G["ceph"][1], low)
    for sx in (1.0, -1.0):
        for side in (1.0, -1.0):
            grid = []
            normals = []
            for ti in range(nt + 1):
                t = ti / nt * 0.99
                wide = ceph_width(t)
                row = []
                nrow = []
                for hi in range(nh + 1):
                    hf = hi / nh
                    h = wide * hf
                    foil = 2.6 * math.sqrt(hf) * (1.0 - hf) if hf < 1.0 else 0.0
                    swell = c["thick"] * foil * min(1.0, t / 0.1) ** 0.5 * (1.0 - t) ** 0.4
                    off = side * swell * 0.5
                    p, n = ceph_point(t, h, off, sx, 1.0)
                    row.append(m.add(p, (t, h), CEPH, off))
                    nrow.append(n * side)
                grid.append(row)
                normals.append(nrow)
            for ti in range(nt):
                for hi in range(nh):
                    m.face((grid[ti][hi], grid[ti][hi + 1], grid[ti + 1][hi + 1], grid[ti + 1][hi]),
                           normals[ti][hi] + normals[ti + 1][hi + 1], "cephalic fins")


# ---------------------------------------------------------------- the tail, its fin and spines, the eyes

def tail_radius(zd):
    t = S["tail"]
    start = t["start"] * DISC
    f = (zd - start) / (DISC + t["length"] - start)
    return t["radius"] * (1.0 - f) ** 0.75 * (1.0 - 0.45 * smooth(0.0, 0.25, f)) + 0.0012


def tail(m, low):
    t = S["tail"]
    rings = pick(t["rings"], max(8, t["rings"] // 3), G["tail"][0], low)
    around = pick(t["around"], 5, G["tail"][1], low)
    start = t["start"] * DISC
    end = DISC + t["length"]
    grid = []
    for r in range(rings + 1):
        f = r / rings
        # (closer rings near the root, where it bends most sharply for its size)
        zd = start + (end - start) * f ** 1.25
        radius = tail_radius(zd)
        row = []
        for c in range(around):
            angle = c / around * TAU
            p = Vector((math.sin(angle) * radius, math.cos(angle) * radius, zd - MID))
            row.append(m.add(p, ((zd - DISC) / t["length"], c / around), TAIL))
        grid.append(row)
    for r in range(rings):
        for c in range(around):
            n = (c + 1) % around
            quad = (grid[r][c], grid[r][n], grid[r + 1][n], grid[r + 1][c])
            at = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((at.x, at.y, 0.0)), "tail")
    for row, zd, way in ((grid[0], start, -1.0), (grid[-1], end + 0.002, 1.0)):
        tip = m.add(Vector((0.0, 0.0, zd - MID)), ((zd - DISC) / t["length"], 0.0), TAIL)
        for c in range(around):
            m.face((tip, row[c], row[(c + 1) % around]), Vector((0.0, 0.0, way)), "tail")


def blade(m, part, name, point, place, facing, thick, nt, nu):
    """A fin: a thin closed blade (see the yellowfin tuna's builder)."""
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


def swept(lead_edge, trail_edge, reach=0.985):
    def point(t, u):
        a = bezier(*lead_edge, t * reach)
        b = bezier(*trail_edge, t * reach)
        return (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)
    return point


def upright(p):
    return Vector((0.0, p[1], p[0] - MID))


SIDE = Vector((1.0, 0.0, 0.0))


def top_y(zd):
    if zd <= DISC * 0.999:
        return max(skin_at(0.0, zd, True).y, tail_radius(zd) if zd > S["tail"]["start"] * DISC else 0.0)
    return tail_radius(zd)


def fins(m, low):
    d = 3 if low else 1
    f = S["dorsal"]
    x0 = f["at"] * DISC
    x1 = x0 + f["chord"]
    sink = 0.12 * f["high"]
    tip = (x1 + 0.25 * f["chord"], top_y(x1) + f["high"])
    blade(m, DORSAL, "dorsal", swept(((x0, top_y(x0) - sink), (x0 + 0.55 * f["chord"], top_y(x0) + f["high"] * 0.9), tip),
                                     ((x1, top_y(x1) - sink), (x1 + 0.1 * f["chord"], top_y(x1) + f["high"] * 0.35), tip)),
          upright, SIDE, f["high"] * 0.16, pick(12, 12 // d, G["dorsal"][0], low), pick(9, 9 // d, G["dorsal"][1], low))
    for behind in S["spines"]:
        # a barbed spine lying back along the top of the tail
        x0 = DISC + behind
        y0 = tail_radius(x0) * 0.6
        tip = (x0 + 0.13, tail_radius(x0 + 0.13) + 0.016)
        blade(m, SPINE, "spines", swept(((x0, y0), (x0 + 0.05, y0 + 0.024), tip),
                                        ((x0 + 0.03, y0 - 0.002), (x0 + 0.07, y0 + 0.006), tip)),
              upright, SIDE, 0.007, pick(10, 10 // d, G["spines"][0], low), pick(6, 6 // d, G["spines"][1], low))


def eye(m, sx, low):
    e = S["eye"]
    spokes = pick(28, 10, G["eye"][0], low)
    steps = pick(8, 3, G["eye"][1], low)
    here = Vector((e["at"][0] * sx, e["at"][1], e["at"][2] - MID))
    out = Vector((e["out"][0] * sx, e["out"][1], e["out"][2])).normalized()
    one = out.cross(Vector((0.0, 1.0, 0.0))).normalized()
    two = out.cross(one).normalized()
    radius = e["radius"]
    middle = m.add(here + out * radius * 0.55, (0.0, 0.0), EYE)
    last = None
    for k in range(1, steps + 1):
        r = k / steps
        row = []
        for s in range(spokes):
            angle = s / spokes * TAU
            p = here + (one * math.cos(angle) + two * math.sin(angle)) * radius * r
            row.append(m.add(p + out * radius * (0.55 * (1.0 - r * r) - 0.45 * r * r), (r, 0.0), EYE))
        for s in range(spokes):
            n = (s + 1) % spokes
            if last is None:
                m.face((middle, row[s], row[n]), out, "eyes")
            else:
                m.face((last[s], row[s], row[n], last[n]), out, "eyes")
        last = row


# ---------------------------------------------------------------- the gills

# (added 2026-11-18, the user: "The fish need modeled gills as well, well for relevant fish, so like when it opens
# its mouth wide you can see them")
#
# Two things, both hidden while the mouth is shut and the slits closed, so that the animal looks exactly as before:
# - THE GILL ARCHES: four a side, hanging from the roof of the mouth's pocket near its back, across the throat. Each
#   a thin closed blade (UV.x from its root on the roof, 0, to its lower edge, 1; UV.y along it). Its front face is
#   drawn as pale gill rakers, its back face as deep red filaments. Seen when the lower jaw turns down.
# - THE GILL SLITS' FLAPS: five a side under the head, where the shader paints the slits. Each a thin closed blade
#   lying just inside the skin behind its slit (UV.x from the slit, 0, to its back edge, 1; UV.y 0.3; UV2.x -1, the
#   underside's). The shader drops its back edge as the gills open (`gape`, or `gills` for breathing), so that a flap
#   of skin lifts and the red of the gills shows under it.
# On the full model they are a second surface, so that the body's own surface is the same as it was.
GILLS, FLAPS = 7, 8
GILL_FACES = ("gill arches", "gill flaps")
# The slits as the shader paints them: at.x from `inner` to `outer`, at.y = `base` + `step` * k + a shallow arc
# (at = (|x| / HALF, z / DISC + 0.5)), and how far back each flap reaches (a part of the space between slits).
SLITS = {
    "manta_ray": dict(inner=(0.05, 0.004), outer=(0.155, -0.016), base=0.2, step=0.052),
    "devil_ray": dict(inner=(0.05, 0.004), outer=(0.14, -0.013), base=0.2, step=0.05),
    "spotted_eagle_ray": dict(inner=(0.045, 0.004), outer=(0.115, -0.009), base=0.27, step=0.036),
}
FLAP_SHARE = 0.4
# Where the arches hang in the pocket: `s` from the lip (0) to the back (1).
ARCH_AT = (0.5, 0.62, 0.74, 0.86)


def flap_width():
    return FLAP_SHARE * SLITS[SPECIES]["step"] * DISC


def pocket_at(x, s):
    """As disc() makes it: the point `s` of the way along the mouth's pocket at `x` across, how far its roof is above
    that, and how far its floor is below."""
    sigma = x / HALF
    lip = skin(sigma, 0.0, True) if S["mouth"] == "front" else skin_at(sigma, S["mouth_at"], False)
    back_zd = S["mouth_at"] + S["jaw"]
    low_back = skin_at(sigma, back_zd, False)
    high_back = skin_at(sigma, back_zd, True)
    back = low_back + (high_back - low_back) * 0.42
    p = lip + (back - lip) * s
    zd = p.z + MID
    arch = math.sin(math.pi * s ** 0.8) * lateral(x)
    up = max(skin_at(sigma, zd, True).y - p.y, 0.0) * 0.55 * arch
    down = max(p.y - skin_at(sigma, zd, False).y, 0.0) * 0.5 * arch
    return p, up, down


def closed_sheet(m, part, name, grid_point, nt, nu, thick, facing, extra=0.0, uv_y=None):
    """A thin closed blade: `grid_point(t, u)` is its middle, `facing` the way its first skin faces; `thick` at its
    root (t 0), nothing at its edge (t 1) and at both ends (u 0, 1)."""
    for side in (1.0, -1.0):
        grid = []
        for ti in range(nt + 1):
            t = ti / nt
            row = []
            for ui in range(nu + 1):
                u = ui / nu
                swell = thick * (1.0 - t) ** 0.7 * 2.6 * math.sqrt(u) * (1.0 - u)
                p = grid_point(t, u) + facing * (side * swell * 0.5)
                row.append(m.add(p, (t, u if uv_y is None else uv_y), part, extra))
            grid.append(row)
        for ti in range(nt):
            for ui in range(nu):
                m.face((grid[ti][ui], grid[ti][ui + 1], grid[ti + 1][ui + 1], grid[ti + 1][ui]), facing * side, name)


def gills(m, low):
    from mathutils.bvhtree import BVHTree
    # (the model as built so far: the arches and flaps are fitted to its own faces, which on the low and game
    # models lie a little inside the curves they were laid on)
    tree = BVHTree.FromPolygons(m.verts, m.faces)
    nt, nu = pick((3, 8), (1, 2), (1, G["gills"][0]), low)
    # the arches, a side each, hanging from the roof of the pocket
    half = S["mouth_half"]
    for s in ARCH_AT:
        for sx in (1.0, -1.0):
            def arch_point(t, u, s=s, sx=sx):
                x = sx * half * (0.06 + 0.76 * u)
                p, up, down = pocket_at(x, s)
                # (from just under the roof, as built, half way down to the floor)
                roof = tree.ray_cast(p, Vector((0.0, 1.0, 0.0)))[0]
                floor = tree.ray_cast(p, Vector((0.0, -1.0, 0.0)))[0]
                top = roof.y if roof is not None else p.y + up
                bottom = floor.y if floor is not None else p.y - down
                gap = max(top - bottom, 0.0)
                return Vector((p.x, top - gap * (0.12 + 0.4 * t), p.z))
            closed_sheet(m, GILLS, "gill arches", arch_point, nt, nu, 0.25 * pocket_at(0.0, s)[1],
                         Vector((0.0, 0.0, -1.0)))
    # the slits' flaps, each just inside the skin of the model as built (found by a ray up from below)
    sl = SLITS[SPECIES]
    width = flap_width()
    sink = 0.0016 * DISC
    thick = 0.0012 * DISC
    fnt, fnu = pick((3, 8), (1, 2), (1, G["gills"][1]), low)
    for k in range(5):
        inner = sl["inner"][0] + sl["inner"][1] * k
        outer = sl["outer"][0] + sl["outer"][1] * k
        mid = 0.5 * (inner + outer)
        for sx in (1.0, -1.0):
            def flap_point(t, u, inner=inner, outer=outer, mid=mid, sx=sx, k=k):
                ax = inner + (outer - inner) * (0.04 + 0.92 * u)
                along = sl["base"] + sl["step"] * k + 0.9 * (ax - mid) ** 2 / (outer - inner) - 0.05 * (ax - mid)
                x = sx * ax * HALF
                z = (along - 0.5) * DISC + t * width
                hit = tree.ray_cast(Vector((x, -50.0, z)), Vector((0.0, 1.0, 0.0)))
                y = hit[0].y if hit[0] is not None else skin_at(x / HALF, z + MID, False).y
                return Vector((x, y + sink + 0.5 * thick, z))
            closed_sheet(m, FLAPS, "gill flaps", flap_point, fnt, fnu, thick, Vector((0.0, -1.0, 0.0)), -1.0, 0.3)


def make(name, low):
    m = Mesh()
    disc(m, low)
    if S["ceph"]:
        cephs(m, low)
    tail(m, low)
    fins(m, low)
    for sx in (1.0, -1.0):
        eye(m, sx, low)
    gills(m, low)
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
    material = bpy.data.materials.get(SPECIES) or bpy.data.materials.new(SPECIES)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = S["colour"] + (1.0,)
    material.diffuse_color = S["colour"] + (1.0,)
    mesh.materials.append(material)
    if not GAME:
        # (the full and low models: the gills a second surface, so that the body's is the same as it was, and
        # Godot's importer thins it far off as it did; the game model is drawn without those thinned meshes)
        inner = bpy.data.materials.get(SPECIES + "_gills") or bpy.data.materials.new(SPECIES + "_gills")
        inner.diffuse_color = (0.5, 0.05, 0.05, 1.0)
        mesh.materials.append(inner)
        for poly in mesh.polygons:
            if m.out[poly.index][1] in GILL_FACES:
                poly.material_index = 1
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    print("BUILT %s verts=%d tris=%d" % (name, len(mesh.vertices), tris))
    lo = [min(p[i] for p in m.verts) for i in range(3)]
    hi = [max(p[i] for p in m.verts) for i in range(3)]
    print("SIZE %s: x %.3f to %.3f, y %.3f to %.3f, z %.3f to %.3f" % (name, lo[0], hi[0], lo[1], hi[1], lo[2], hi[2]))
    winding(name, mesh, m)
    return obj


def winding(name, mesh, m):
    """Nothing inside out: the skin faces away from the middle of its section, the mouth's roof down and
    its floor up, each skin of a fin away from the fin's own sheet, the tail away from its middle line, an
    eye out from the head (Blender's front is the side a face's normal is on)."""
    bad = {}
    for poly in mesh.polygons:
        out, group = m.out[poly.index]
        if poly.normal.dot(to_b(out)) <= 0.0:
            bad[group] = bad.get(group, 0) + 1
    told = ["%s %d/%d wrong" % (group, bad.get(group, 0), count) for group, count in m.count.items()]
    print("WINDING %s: %s: %s" % (name, "ok" if not bad else "INSIDE OUT", ", ".join(told)))


def shader_numbers():
    hinge_zd = S["mouth_at"] + S["jaw"]
    hinge = skin_at(0.0, hinge_zd, False)
    told = ["HALF = %.4f" % HALF, "DISC = %.4f" % DISC, "TAIL_LENGTH = %.4f" % S["tail"]["length"],
            "HINGE = vec2(%.4f, %.4f) (y, z)" % (hinge.y, hinge.z)]
    if S["ceph"]:
        c = S["ceph"]
        along, down, inward = ceph_frame()
        v = lambda p: "vec3(%.5f, %.5f, %.5f)" % (p.x, p.y, p.z)
        told += ["CEPH_ROOT = vec3(%.5f, %.5f, %.5f)" % (c["root"][0], c["root"][1], c["root"][2] - MID),
                 "CEPH_ALONG = " + v(along), "CEPH_DOWN = " + v(down), "CEPH_IN = " + v(inward),
                 "CEPH_LENGTH = %.4f" % c["length"], "CEPH_WIDTH = %.4f" % c["width"],
                 "CEPH_ROLL0 = %.2f" % c["roll0"], "CEPH_ROLL1 = %.2f" % c["roll1"], "CEPH_CUP = %.2f" % c["cup"]]
    e = S["eye"]
    out = Vector(e["out"]).normalized()
    told += ["EYE_AT = vec3(%.5f, %.5f, %.5f)" % (e["at"][0], e["at"][1], e["at"][2] - MID),
             "EYE_OUT = vec3(%.5f, %.5f, %.5f)" % (out.x, out.y, out.z), "EYE_RADIUS = %.4f" % e["radius"]]
    print("SHADER %s: %s" % (SPECIES, "; ".join(told)))


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
    scene.world.color = (0.25, 0.4, 0.6)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    # (Blender space: the ray lies along Y, its nose at +Y, up is Z)
    wide = HALF * 2.0 * 1.12
    long = (DISC + S["tail"]["length"]) * 1.15
    back = -S["tail"]["length"] * 0.5
    head = MID
    views = [("left", (1, 0, 0), (0, back, 0), long), ("right", (-1, 0, 0), (0, back, 0), long),
             ("front", (0, 1, 0), (0, 0, 0), wide), ("back", (0, -1, 0), (0, 0, 0), wide),
             ("top", (0.001, 0, 1), (0, back, 0), max(long * 1.8, wide)), ("under", (0.001, 0, -1), (0, back, 0), max(long * 1.8, wide)),
             ("head", (0.5, 0.8, 0.35), (0, head, 0), HALF * 0.7), ("head_under", (0.3, 0.7, -0.6), (0, head, 0), HALF * 0.7),
             ("head_side", (1, 0.15, 0.05), (0, head, 0), HALF * 0.6)]
    for low, obj in ((False, made[0]), (True, made[1])):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if low and view not in ("top", "head"):
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
    global GAME
    full = make(SPECIES, False)
    low = make(SPECIES + "_lo", True)
    GAME = True
    game = make(SPECIES + "_game", False)
    GAME = False
    shader_numbers()
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, SPECIES + ".glb"))
    export_one(low, os.path.join(OUT, SPECIES + "_lo.glb"))
    export_one(game, os.path.join(OUT, SPECIES + "_game.glb"))
    low.location.x = HALF * 2.3
    game.location.x = -HALF * 2.3
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, SPECIES + ".blend"))
    low.location.x = 0.0
    game.location.x = 0.0
    game.hide_render = True
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low])


if __name__ == "__main__":
    main()
