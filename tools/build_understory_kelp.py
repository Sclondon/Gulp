"""Understory kelp (Pterygophora californica / Laminaria setchellii, tools/BIOMES.md section 8 item 3):
a stiff woody stipe with a crown of strap blades drooping like a small palm, standing on the rock under
the giant kelp. Two variants: `understory_kelp` (Pterygophora: a taller stipe, blades in two ranks down
its top) and `understory_kelp_b` (Laminaria: a short stipe, a fan of broad split blades).

    "C:/Program Files/Blender Foundation/Blender 4.3/blender.exe" --background --factory-startup --python tools/build_understory_kelp.py [-- <pictures folder>]

Writes models/kit/understory_kelp(_b).glb and .json, tools/blend/kit_understory_kelp.blend.
Base at y = 0; the alpha of a point's colour is its sway (the kit's soft shader). The game tints each
plant (tints below) and sizes it 0.8 to 1.5. Claude's design (2026-11-18), after the research in
BIOMES.md; looked at from four sides and above.
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_build as kb  # noqa: E402
from mathutils import Vector  # noqa: E402

K = kb.K
STIPE = (0.22, 0.15, 0.07)
BLADE = (0.42, 0.33, 0.1)
TIP = (0.58, 0.47, 0.17)


def pterygophora(kit, low):
    rng = random.Random(3)
    top = Vector((0.06, 0.95, 0.02))
    path = [Vector((0, 0, 0)), Vector((0.02, 0.35, 0.0)), Vector((0.05, 0.7, 0.01)), top]
    kit.tube(path, [0.035, 0.03, 0.026, 0.02] if not low else [0.03, 0.025, 0.022, 0.018], 5 if not low else 3,
             lambda f, k: K.mix(STIPE, (0.3, 0.22, 0.1), f), sway=lambda f: 0.25 * f * f)
    # a small holdfast of root-like haptera
    for k in range(5 if not low else 0):
        a = math.tau * k / 5 + 0.3
        kit.cone(Vector((0, 0.04, 0)), Vector((math.cos(a) * 0.12, -0.02, math.sin(a) * 0.12)), 0.018, 3, STIPE, STIPE)
    count = 14 if not low else 6
    for k in range(count):
        # (two ranks down the top 0.35 m of the stipe, alternating sides, the lower ones longer)
        t = k / max(count - 1, 1)
        at = path[2].lerp(top, t) if not low else top
        side = 1.0 if k % 2 == 0 else -1.0
        turn = side * math.pi * 0.5 + rng.uniform(-0.35, 0.35) + k * 0.4
        out = Vector((math.cos(turn), 0.0, math.sin(turn)))
        along = (out + Vector((0, 0.9 - 0.5 * t, 0))).normalized()
        length = rng.uniform(0.45, 0.6) * (1.15 - 0.35 * t)
        kb.blade(kit, at, along, Vector((0, 1, 0)).cross(out) if abs(out.y) < 0.9 else Vector((1, 0, 0)), length, 0.12,
                 3 if not low else 2, lambda f: K.mix(BLADE, TIP, f), 0.3, 1.0, droop=Vector((0, -0.42, 0)) + out * 0.08)
    # the terminal blade
    kb.blade(kit, top, Vector((0.1, 1, 0)), Vector((1, 0, 0.3)), 0.4, 0.12, 3 if not low else 2, lambda f: K.mix(BLADE, TIP, f), 0.3, 1.0,
             droop=Vector((0.15, -0.12, 0)))


def laminaria(kit, low):
    rng = random.Random(7)
    top = Vector((0.0, 0.32, 0.03))
    kit.tube([Vector((0, 0, 0)), Vector((0.01, 0.16, 0.01)), top], [0.03, 0.026, 0.022], 5 if not low else 3,
             lambda f, k: STIPE, sway=lambda f: 0.2 * f)
    count = 9 if not low else 4
    for k in range(count):
        # a fan of broad straps split from one blade, falling over in an arc
        turn = (k / (count - 1) - 0.5) * 2.2 + rng.uniform(-0.12, 0.12)
        out = Vector((math.sin(turn), 0.0, math.cos(turn) * 0.45)).normalized()
        along = (out * 0.45 + Vector((0, 1, 0))).normalized()
        kb.blade(kit, top, along, Vector((1, 0, 0)).cross(along) if abs(along.x) < 0.9 else Vector((0, 0, 1)),
                 rng.uniform(0.6, 0.85), 0.11, 4 if not low else 2, lambda f: K.mix((0.36, 0.28, 0.08), (0.55, 0.43, 0.13), f), 0.3, 1.0,
                 droop=out * 0.35 + Vector((0, -0.45, 0)))


def main():
    kb.start()
    tints = [(1.0, 1.0, 1.0), (0.85, 0.92, 0.8), (1.1, 1.0, 0.85), (0.9, 0.82, 0.75)]
    K.life("understory_kelp", "kit", "soft", pterygophora, tints=tints)
    K.life("understory_kelp_b", "kit", "soft", laminaria, tints=tints)
    kb.ship("understory_kelp", ["understory_kelp", "understory_kelp_b"], kb.ARGS[0] if kb.ARGS else None)


main()
