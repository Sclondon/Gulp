"""White plumose anemones (Metridium farcimen) in a clump, for the rocky crags (tools/BIOMES.md, "The eight biomes";
the crags' concept, tools/art_src/concept_biome_crags.png, has white plumose anemones on every rock): `plumose_anemones`,
three to five tall smooth white columns, each with a collar and a big lobed, frilled crown, 0.3 to 0.55 m tall. The
crown is a turned shape whose rim is lobed and waved up and down (the feathery head reads from its frills and the
pale-to-cream shading, not from modelled tentacles: a few hundred triangles a crown).

    "C:/Program Files/Blender Foundation/Blender 4.3/blender.exe" --background --factory-startup --python tools/build_plumose.py [-- <pictures folder>]

Writes models/kit/plumose_anemones.glb (and .json), tools/blend/kit_plumose.blend. Base at y = 0 (a little below, to
bed it on rock). Claude's design (2026-11-18). GameCommon's anemone component has a single plumose as a living node;
this is the cheap still kit piece drawn by the hundred in a MultiMesh.
"""

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_build as kb  # noqa: E402
from mathutils import Vector  # noqa: E402

K = kb.K
TAU = math.tau

# (white with a cream crown, the shaded column greyer at its foot)
FOOT = (0.62, 0.6, 0.56)
COLUMN = (0.9, 0.88, 0.83)
COLLAR = (0.97, 0.95, 0.9)
CROWN = (1.0, 0.98, 0.93)
FRILL = (0.93, 0.86, 0.74)


def one(kit, low, at, tall, wide, lean, seed):
    rng = random.Random(seed)
    lobes = rng.choice((5, 6, 7))
    phase = rng.uniform(0, TAU)
    sides = 7 if low else 22
    up = Vector((math.sin(lean[0]) * 0.6, 1.0, math.sin(lean[1]) * 0.6)).normalized()

    # the column: a foot spread on the rock, a smooth stalk, a collar under the crown
    col = tall * 0.62
    profile = [(0.0, -0.03), (wide * 0.55, -0.03), (wide * 0.5, 0.0), (wide * 0.36, col * 0.15), (wide * 0.32, col * 0.6),
               (wide * 0.36, col * 0.88), (wide * 0.44, col), (0.0, col)]
    cols = [FOOT, FOOT, FOOT, K.mix(FOOT, COLUMN, 0.5), COLUMN, COLLAR, COLLAR, COLLAR]

    def bend(p, i, k):
        # (the column leans: each ring moved over by how high it is)
        return Vector((at.x + p.x + up.x * p.y, at.y + p.y * up.y, at.z + p.z + up.z * p.y))

    kit.lathe(profile, 4 if low else 12, lambda i, k: cols[i], sway=lambda i: 0.25 * max(profile[i][1], 0.0) / tall, shape=bend)

    # the crown: a wide frilled bowl over the collar, its rim lobed and waved, rounding over to a shallow top
    rim = wide * rng.uniform(1.25, 1.5)
    crown = [(0.0, col - tall * 0.02), (wide * 0.44, col), (rim * 0.75, col + tall * 0.12), (rim, col + tall * 0.24), (rim * 0.92, col + tall * 0.34),
             (rim * 0.6, col + tall * 0.38), (rim * 0.25, col + tall * 0.36), (0.0, col + tall * 0.33)]
    ccols = [COLLAR, COLLAR, K.mix(COLLAR, CROWN, 0.5), FRILL, CROWN, CROWN, K.mix(CROWN, FRILL, 0.4), FRILL]

    def frill(p, i, k):
        a = math.atan2(p.z, p.x)
        out = (1.0 + 0.22 * math.cos(lobes * a + phase) + (0.0 if low else 0.06 * math.cos(3 * lobes * a))) if i >= 2 else 1.0
        wave = (tall * 0.07 * math.sin(lobes * a + phase) if 3 <= i <= 5 else 0.0)
        q = Vector((p.x * out, p.y + wave, p.z * out))
        return bend(q, i, k)

    kit.lathe(crown, sides, lambda i, k: ccols[i], sway=lambda i: 0.35 + 0.15 * min(i, 5) / 5, shape=frill)


def cluster(kit, low):
    rng = random.Random(53)
    count = 4
    spots = [Vector((0.0, 0.0, 0.0)), Vector((0.16, 0.0, 0.08)), Vector((-0.12, 0.0, 0.13)), Vector((0.03, 0.0, -0.17))]
    for n in range(count if not low else 2):
        tall = [0.55, 0.38, 0.3, 0.42][n]
        wide = [0.075, 0.06, 0.05, 0.065][n]
        one(kit, low, spots[n], tall, wide, (rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25)), 100 + n)


def main():
    kb.start()
    K.life("plumose_anemones", "kit", "soft", cluster,
           tints=[(1.0, 1.0, 1.0), (1.0, 0.97, 0.92), (1.0, 0.86, 0.7)])
    kb.ship("plumose", ["plumose_anemones"], kb.ARGS[0] if kb.ARGS else None)


main()
