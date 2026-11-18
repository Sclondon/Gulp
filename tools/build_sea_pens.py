"""Sea pens and a sea whip (tools/BIOMES.md section 8 item 7): `sea_pen` (Ptilosarcus: an orange feather 0.35 m
on a fleshy stalk standing in sand), `sea_pen_deep` (a taller white one, 0.8 m, for the canyon's mud) and
`sea_whip` (a bare whip 1 m, for the canyon's floor). The feather's leaves are two-sided sheets.

    "C:/Program Files/Blender Foundation/Blender 4.3/blender.exe" --background --factory-startup --python tools/build_sea_pens.py [-- <pictures folder>]

Writes models/kit/sea_pen.glb, sea_pen_deep.glb, sea_whip.glb (and .json), tools/blend/kit_sea_pens.blend.
Base at y = 0 (a little stalk below, to bed it into the sand). Claude's design (2026-11-18).
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_build as kb  # noqa: E402
from mathutils import Vector  # noqa: E402

K = kb.K


def pen(tall, stalk_col, leaf_col, tip_col, leaves_full, leaves_low):
    def make(kit, low):
        stalk = tall * 0.35
        kit.tube([Vector((0, -0.05, 0)), Vector((0, stalk * 0.5, 0)), Vector((0.01, stalk, 0))],
                 [0.018 * tall / 0.35, 0.016 * tall / 0.35, 0.013 * tall / 0.35], 3 if low else 5,
                 lambda f, k: stalk_col, sway=lambda f: 0.3 * f)
        # the rachis up the middle of the feather
        top = Vector((0.03, tall, 0))
        kit.tube([Vector((0.01, stalk, 0)), top], [0.01 * tall / 0.35, 0.004], 3, lambda f, k: K.mix(leaf_col, tip_col, f), sway=lambda f: 0.3 + 0.5 * f)
        count = leaves_low if low else leaves_full
        for k in range(count):
            t = (k + 0.5) / count
            at = Vector((0.01, stalk, 0)).lerp(top, t)
            wide = (tall * 0.22) * math.sin(math.pi * (0.15 + 0.85 * t))
            for side in (-1.0, 1.0):
                spin = 0.9 * math.sin(k * 2.4)
                out = Vector((math.sin(spin) * side, 0.25, math.cos(spin) * side)).normalized()
                kb.blade(kit, at, out, Vector((0, 1, 0)), wide, tall * 0.06, 1, lambda f: K.mix(leaf_col, tip_col, f), 0.3 + 0.5 * t, 0.6 + 0.4 * t,
                         droop=Vector((0, 0.05 * tall, 0)))
    return make


def whip(kit, low):
    n = 3 if low else 7
    path = [Vector((0.12 * (i / n) ** 2, 1.0 * i / n - 0.04, 0.05 * math.sin(i / n * 3.0))) for i in range(n + 1)]
    kit.tube(path, [0.02 - 0.014 * (i / n) for i in range(n + 1)], 3 if low else 4,
             lambda f, k: K.mix((0.78, 0.66, 0.5), (0.9, 0.82, 0.66), f), sway=lambda f: f)


def main():
    kb.start()
    K.life("sea_pen", "kit", "soft", pen(0.35, (0.82, 0.46, 0.2), (0.94, 0.5, 0.16), (1.0, 0.72, 0.3), 7, 3),
           tints=[(1.0, 1.0, 1.0), (1.0, 0.85, 0.75), (0.95, 0.75, 0.6)])
    K.life("sea_pen_deep", "kit", "soft", pen(0.8, (0.82, 0.78, 0.7), (0.92, 0.9, 0.84), (1.0, 0.96, 0.9), 9, 3),
           tints=[(1.0, 1.0, 1.0), (1.0, 0.92, 0.85)])
    K.life("sea_whip", "kit", "soft", whip, tints=[(1.0, 1.0, 1.0), (1.0, 0.8, 0.6), (0.9, 0.6, 0.5)])
    kb.ship("sea_pens", ["sea_pen", "sea_pen_deep", "sea_whip"], kb.ARGS[0] if kb.ARGS else None)


main()
