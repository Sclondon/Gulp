"""The kelp canopy (tools/BIOMES.md 5.2, "a surface canopy"): a mat of giant kelp fronds lying along the
surface, streaming down-current (+X), blades hanging a little under them on their floats. Laid over the
thick of a kelp forest at the surface, a few metres apart, it closes the lid seen from below: dark
fronds against the bright surface, light in the gaps between mats.

    "C:/Program Files/Blender Foundation/Blender 4.3/blender.exe" --background --factory-startup --python tools/build_kelp_canopy.py [-- <pictures folder>]

Writes models/kit/kelp_canopy.glb and .json, tools/blend/kit_kelp_canopy.blend. Origin at the surface
(y = 0: the mat lies from 0 down to about 0.45 m), about 3.6 m long (x) by 2.4 m (z). Two-sided sheets
only; the alpha of a point's colour is its sway (the kit's soft shader, swaying as kelp: scripts/kit.gd).
Claude's design (2026-11-18).
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_build as kb  # noqa: E402
from mathutils import Vector  # noqa: E402

K = kb.K
FROND = (0.36, 0.27, 0.07)
BLADE = (0.5, 0.38, 0.1)
TIP = (0.64, 0.5, 0.15)


def strand(kit, rng, start, length, low):
    """One frond along the surface: a ribbon (the stipe and the blades seen as one, far off) or a
    stipe with blades hanging on alternating sides."""
    n = 6 if low else 10
    path = []
    wob = rng.uniform(0, math.tau)
    for i in range(n + 1):
        t = i / n
        path.append(start + Vector((length * t, -0.04 - 0.05 * t, 0.22 * math.sin(wob + t * 4.0) * t)))
    wide = 0.55 if low else 0.08
    rows = []
    for i, p in enumerate(path):
        a = (path[min(i + 1, n)] - path[max(i - 1, 0)]).normalized()
        side = Vector((0, 1, 0)).cross(a).normalized()
        w = wide * (1.0 - 0.5 * i / n)
        rows.append([p - side * w * 0.5, p + side * w * 0.5])
    kb.sheet(kit, rows, lambda i, j: K.mix(FROND, BLADE, i / n), lambda i, j: 0.3 + 0.7 * i / n)
    if low:
        return
    k = 0
    s = 0.25
    while s < length - 0.2:
        t = s / length
        i = min(int(t * n), n - 1)
        at = path[i].lerp(path[i + 1], t * n - i)
        a = (path[i + 1] - path[i]).normalized()
        side = Vector((0, 1, 0)).cross(a).normalized() * (1.0 if k % 2 == 0 else -1.0)
        out = (side * 0.8 + a * 0.6).normalized()
        kb.blade(kit, at, out, a, rng.uniform(0.55, 0.8), 0.24, 2, lambda f: K.mix(BLADE, TIP, f), 0.5, 1.0,
                 droop=Vector((0, -rng.uniform(0.18, 0.4), 0)) + a * 0.12)
        s += rng.uniform(0.26, 0.36)
        k += 1


def canopy(kit, low):
    rng = random.Random(11)
    for k in range(6):
        start = Vector((-1.8 + rng.uniform(-0.2, 0.3), 0.0, -1.0 + 2.0 * k / 5 + rng.uniform(-0.12, 0.12)))
        strand(kit, rng, start, rng.uniform(2.8, 3.5), low)


def main():
    kb.start()
    K.life("kelp_canopy", "kit", "soft", canopy, tints=[(1.0, 1.0, 1.0), (1.08, 1.0, 0.85), (0.9, 0.85, 0.75)])
    kb.ship("kelp_canopy", ["kelp_canopy"], kb.ARGS[0] if kb.ARGS else None)


main()
