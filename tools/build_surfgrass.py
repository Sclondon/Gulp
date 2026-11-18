"""Surfgrass (Phyllospadix, tools/BIOMES.md section 8 item 6): a dense tuft of bright emerald, very long, very
thin ribbon blades on rock in the surge, leaning and curling down-current. On the rocky points of the beach
strip, 0.5 to 4 m deep.

    "C:/Program Files/Blender Foundation/Blender 4.3/blender.exe" --background --factory-startup --python tools/build_surfgrass.py [-- <pictures folder>]

Writes models/kit/surfgrass.glb and .json, tools/blend/kit_surfgrass.blend. Base at y = 0, about 0.9 m long
blades. Claude's design (2026-11-18).
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_build as kb  # noqa: E402
from mathutils import Vector  # noqa: E402

K = kb.K
ROOT = (0.08, 0.3, 0.12)
GREEN = (0.16, 0.6, 0.24)
TIP = (0.36, 0.78, 0.3)


def tuft(kit, low):
    rng = random.Random(9)
    count = 6 if low else 16
    for k in range(count):
        a = rng.uniform(0, math.tau)
        r = rng.uniform(0.0, 0.12)
        base = Vector((math.cos(a) * r, 0.0, math.sin(a) * r))
        lean = Vector((0.55 + rng.uniform(-0.25, 0.25), 1.0, rng.uniform(-0.35, 0.35))).normalized()
        across = Vector((0, 1, 0)).cross(lean).normalized() if abs(lean.y) < 0.99 else Vector((1, 0, 0))
        kb.blade(kit, base, lean, across, rng.uniform(0.6, 1.0), 0.05 if not low else 0.09, 1 if low else 4,
                 lambda f: K.mix(K.mix(ROOT, GREEN, min(1.0, f * 3.0)), TIP, f), 0.1, 1.0,
                 droop=Vector((0.35, -0.45, rng.uniform(-0.1, 0.1))), twist=rng.uniform(-1.2, 1.2))


def main():
    kb.start()
    K.life("surfgrass", "kit", "soft", tuft, tints=[(1.0, 1.0, 1.0), (0.9, 1.0, 0.85), (1.05, 1.05, 0.9)])
    kb.ship("surfgrass", ["surfgrass"], kb.ARGS[0] if kb.ARGS else None)


main()
