"""A sand dollar bed (Dendraster excentricus, tools/BIOMES.md section 8 item 8): grey-purple discs about 8 cm
across standing half buried on edge, leaning down-current (+X), packed in a patch about 1.6 m across, one
instance a patch. In the narrow band at 3.5 to 5 m where the beach strip meets the shelf.

    "C:/Program Files/Blender Foundation/Blender 4.3/blender.exe" --background --factory-startup --python tools/build_sand_dollars.py [-- <pictures folder>]

Writes models/kit/sand_dollars.glb and .json, tools/blend/kit_sand_dollars.blend. Base at y = 0 (the sand's
level: each disc's lower part is under it). Claude's design (2026-11-18).
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_build as kb  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

K = kb.K
DOLLAR = (0.36, 0.3, 0.38)
EDGE = (0.26, 0.21, 0.28)
STAR = (0.6, 0.55, 0.6)


def bed(kit, low):
    rng = random.Random(4)
    count = 14 if low else 34
    placed = []
    tries = 0
    while len(placed) < count and tries < 2000:
        tries += 1
        a = rng.uniform(0, math.tau)
        r = 0.8 * math.sqrt(rng.uniform(0, 1))
        at = Vector((math.cos(a) * r, 0.0, math.sin(a) * r * 0.75))
        if any((at - p).length < 0.085 for p in placed):
            continue
        placed.append(at)
        rad = rng.uniform(0.035, 0.045)
        # (standing on edge, its face across the current, leaning down-current, about 40% buried)
        turn = Matrix.Rotation(rng.uniform(-0.35, 0.35), 4, "Y") @ Matrix.Rotation(math.radians(rng.uniform(25, 45)), 4, "Z")
        kit.xf = Matrix.Translation(at + Vector((0, rad * 0.25, 0))) @ turn @ Matrix.Rotation(math.pi * 0.5, 4, "Z")
        sides = 5 if low else 7
        kit.lathe([(0.0, -0.004), (rad, -0.003), (rad, 0.003), (0.0, 0.005)], sides,
                  lambda i, k: STAR if i == 3 else (EDGE if i in (1, 2) else DOLLAR))
        kit.xf = Matrix.Identity(4)


def main():
    kb.start()
    K.life("sand_dollars", "kit", "firm", bed, tints=[(1.0, 1.0, 1.0), (0.85, 0.9, 1.0), (1.1, 1.0, 0.95)])
    kb.ship("sand_dollars", ["sand_dollars"], kb.ARGS[0] if kb.ARGS else None)


main()
