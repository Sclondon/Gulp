"""A drift kelp paddy (tools/BIOMES.md section 8 item 10): a raft of torn-off giant kelp floating at the surface
over the open ocean, about 6 m across, its fronds tangled round each other on their floats, a few hanging 2 to
3 m down from it (where juvenile fish shelter). The open ocean's landmark: a dark shape against the bright
surface from below.

    "C:/Program Files/Blender Foundation/Blender 4.3/blender.exe" --background --factory-startup --python tools/build_kelp_raft.py [-- <pictures folder>]

Writes models/kit/kelp_raft.glb and .json, tools/blend/kit_kelp_raft.blend. Origin at the surface (y = 0).
Two-sided sheets and float balls; sways as kelp (scripts/kit.gd). Claude's design (2026-11-18).
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_build as kb  # noqa: E402
from mathutils import Vector  # noqa: E402

K = kb.K
FROND = (0.32, 0.24, 0.07)
BLADE = (0.46, 0.35, 0.1)
TIP = (0.6, 0.46, 0.14)


def raft(kit, low):
    rng = random.Random(21)
    strands = 7 if low else 16
    for s in range(strands):
        # (a frond lying in a loose curl round the raft's middle)
        a0 = rng.uniform(0, math.tau)
        r0 = rng.uniform(0.0, 1.0)
        n = 4 if low else 8
        path = []
        for i in range(n + 1):
            t = i / n
            a = a0 + t * rng.uniform(1.2, 2.2)
            r = r0 + t * rng.uniform(0.6, 1.5)
            path.append(Vector((math.cos(a) * r * 1.25, -0.05 - 0.08 * rng.random(), math.sin(a) * r)))
        wide = 0.6 if low else 0.12
        rows = []
        for i, p in enumerate(path):
            d = (path[min(i + 1, n)] - path[max(i - 1, 0)]).normalized()
            side = Vector((0, 1, 0)).cross(d).normalized()
            rows.append([p - side * wide * 0.5, p + side * wide * 0.5])
        kb.sheet(kit, rows, lambda i, j: K.mix(FROND, BLADE, i / n), lambda i, j: 0.4 + 0.6 * i / n)
        if low:
            continue
        for i in range(1, n):
            d = (path[i + 1] - path[i - 1]).normalized()
            side = Vector((0, 1, 0)).cross(d).normalized() * (1 if i % 2 else -1)
            kb.blade(kit, path[i], (side + d * 0.4).normalized(), d, rng.uniform(0.5, 0.8), 0.22, 2,
                     lambda f: K.mix(BLADE, TIP, f), 0.6, 1.0, droop=Vector((0, -rng.uniform(0.15, 0.4), 0)))
        if s % 3 == 0:
            kit.lathe([(0.0, -0.07), (0.06, 0.0), (0.0, 0.07)], 5, lambda i, k: (0.5, 0.4, 0.13), sway=lambda i: 0.6,
                      shape=lambda p, i, k, at=path[n // 2]: p + at)
    # fronds hanging down from it
    for h in range(3 if low else 8):
        a = rng.uniform(0, math.tau)
        at = Vector((math.cos(a) * 1.6, -0.1, math.sin(a) * 1.3))
        kb.blade(kit, at, Vector((0.15, -1, 0.05)), Vector((1, 0, 0.3)), rng.uniform(1.8, 3.0), 0.25, 1 if low else 4,
                 lambda f: K.mix(BLADE, TIP, f), 0.5, 1.0, droop=Vector((0.6, 0, 0)), twist=rng.uniform(-1, 1))


def main():
    kb.start()
    K.life("kelp_raft", "kit", "soft", raft, tints=[(1.0, 1.0, 1.0), (1.05, 0.98, 0.85)])
    kb.ship("kelp_raft", ["kelp_raft"], kb.ARGS[0] if kb.ARGS else None)


main()
