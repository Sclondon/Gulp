"""Reef slabs (tools/BIOMES.md section 8 item 2): low, wide tiles of rock, 3 to 5 m across and 0.3 to 1.2 m
high, cracked and stepped on top, that pave a rock reef's floor cheaply so that rock is not only a colour on
the sand. Three variants. Made as GameCommon's rocks are (fractured blocks joined by a voxel remesh, pushed
by noise, cut flat underneath, thinned, painted by point: build_sea_floor_props.rock()), with spheres for
swimmers.

    "C:/Program Files/Blender Foundation/Blender 4.3/blender.exe" --background --factory-startup --python tools/build_reef_slabs.py [-- <pictures folder>]

Writes models/kit/reef_slab_{a,b,c}.glb and .json, tools/blend/kit_reef_slabs.blend. Claude's design (2026-11-18).
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_build as kb  # noqa: E402
from mathutils import Matrix  # noqa: E402

K = kb.K


def slab_a(bm):
    rot = Matrix.Rotation(math.radians(8.0), 3, "Z")
    K.chunk(bm, (0, 0.05, 0), (2.2, 0.55, 1.6), 101, planes=8, boxy=True, cut=(0.8, 1.1), rot=rot)
    K.chunk(bm, (1.1, 0.25, 0.4), (0.9, 0.5, 0.8), 102, planes=8)
    K.chunk(bm, (-1.0, 0.0, -0.6), (1.0, 0.4, 0.9), 103, planes=8)


def slab_b(bm):
    K.block(bm, (-0.7, 0.1, 0.0), (1.4, 0.45, 1.3), 111, planes=7, tilt=0.06)
    K.block(bm, (1.0, 0.0, 0.3), (1.2, 0.35, 1.1), 112, planes=7, tilt=0.06)
    K.block(bm, (0.2, 0.45, -0.3), (0.9, 0.35, 0.8), 113, planes=7, tilt=0.1)


def slab_c(bm):
    K.chunk(bm, (0, 0.0, 0), (2.6, 0.38, 1.4), 121, planes=9, boxy=True, cut=(0.85, 1.1))
    K.chunk(bm, (-1.4, 0.2, 0.5), (0.8, 0.55, 0.7), 122, planes=8)
    K.chunk(bm, (1.5, 0.1, -0.4), (0.7, 0.4, 0.6), 123, planes=8)


def main():
    kb.start()
    K.rock("reef_slab_a", "kit", slab_a, 4.4, 340, 70, spheres=8, least=0.18, seed=11, voxels=60)
    K.rock("reef_slab_b", "kit", slab_b, 4.0, 340, 64, spheres=8, least=0.18, seed=14, voxels=64)
    K.rock("reef_slab_c", "kit", slab_c, 5.0, 340, 70, spheres=8, least=0.18, seed=13, voxels=60)
    kb.ship("reef_slabs", ["reef_slab_a", "reef_slab_b", "reef_slab_c"], kb.ARGS[0] if kb.ARGS else None)


main()
