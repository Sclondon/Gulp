"""Bull kelp (Nereocystis luetkeana, tools/BIOMES.md section 8 item 4): one thin stipe rising 8 m to a single
round float about 13 cm across, a mop of long strap blades streaming down-current (+X) from it along the
surface. The north forest's kelp and the outer edge of the south one. Sized in the game so the float sits
at the surface (scale = depth / 8).

    "C:/Program Files/Blender Foundation/Blender 4.3/blender.exe" --background --factory-startup --python tools/build_bull_kelp.py [-- <pictures folder>]

Writes models/kit/bull_kelp.glb and .json, tools/blend/kit_bull_kelp.blend. Base (the holdfast) at y = 0,
the float at y = 8. The alpha of a point's colour is its sway (scripts/kit.gd sways it as kelp). Claude's
design (2026-11-18).
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_build as kb  # noqa: E402
from mathutils import Vector  # noqa: E402

K = kb.K
STIPE = (0.34, 0.26, 0.09)
FLOAT = (0.44, 0.35, 0.12)
BLADE = (0.5, 0.4, 0.12)
TIP = (0.66, 0.53, 0.17)
TALL = 8.0


def bull(kit, low):
    rng = random.Random(5)
    n = 4 if low else 9
    path = []
    for i in range(n + 1):
        t = i / n
        # (a slight lean down-current, the top more)
        path.append(Vector((0.6 * t * t, TALL * t - 0.08, 0.15 * math.sin(t * 3.0))))
    top = path[-1]
    kit.tube(path, [0.025 + 0.02 * (i / n) for i in range(n + 1)], 3 if low else 4,
             lambda f, k: K.mix(STIPE, FLOAT, f), sway=lambda f: f ** 1.5)
    float_at = top + Vector((0.0, 0.04, 0.0))
    kit.lathe([(0.0, -0.06), (0.05, -0.05), (0.068, 0.0), (0.05, 0.05), (0.0, 0.065)] if not low else [(0.0, -0.05), (0.06, 0.0), (0.0, 0.06)],
              4 if low else 6, lambda i, k: FLOAT, sway=lambda i: 1.0,
              shape=lambda p, i, k: p + float_at)
    count = 6 if low else 18
    for k in range(count):
        a = (k / count - 0.5) * 1.4 + rng.uniform(-0.1, 0.1)
        out = Vector((math.cos(a), 0.0, math.sin(a)))
        length = rng.uniform(1.6, 2.6)
        kb.blade(kit, float_at, out, Vector((0, 1, 0)).cross(out), length, 0.2, 1 if low else 3,
                 lambda f: K.mix(BLADE, TIP, f), 0.9, 1.0, droop=Vector((0, -rng.uniform(0.15, 0.5), 0)), twist=rng.uniform(-0.6, 0.6))
    # a small holdfast
    for k in range(0 if low else 4):
        a = math.tau * k / 4 + 0.4
        kit.cone(Vector((0, 0.05, 0)), Vector((math.cos(a) * 0.14, -0.03, math.sin(a) * 0.14)), 0.025, 3, STIPE, STIPE)


def main():
    kb.start()
    K.life("bull_kelp", "kit", "soft", bull, tints=[(1.0, 1.0, 1.0), (1.06, 1.0, 0.86), (0.9, 0.86, 0.78)])
    kb.ship("bull_kelp", ["bull_kelp"], kb.ARGS[0] if kb.ARGS else None)


main()
