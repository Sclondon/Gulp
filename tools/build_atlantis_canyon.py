"""Builds Atlantis built into the walls of the Monterey Canyon: a low-poly set piece with baked paint.

    blender --background --factory-startup --python tools/build_atlantis_canyon.py [-- --no-bake]

Reads data/ruins_layout.json (THE table of where each building stands; Bay cuts the ledges under them
from it and Ruins reads it too) and tools/ruins_ground.json (the sea floor round it, in the ruins' own
space, with those ledges: written by tools/ruins_ground.gd; run that first whenever the floor or the
table changes). Writes models/atlantis_canyon.glb, textures/ruins_canyon_atlas.png (4096: the stone),
textures/ruins_canyon_statue.png (1024: her face, the statue and the reliefs) and
tools/blend/atlantis_canyon.blend. The design and its record: tools/RUINS.md. The user (2026-11-18):
"The Atlantis ruines area shouldnt just be a big open flat area, it should be built into the trench
sides"; concept tools/art_src/concept_atlantis_canyon.png, each building's look after concept_atlantis.jpg.

The helpers (shapes, columns, the head, the paint) are tools/build_ruins.py's: its top part is run from
here (that script built the first Atlantis on a flat floor; it and its model are retired, kept unused).

Everything is laid out in GODOT's axes (x east, y up, z south), metres, in the ruins' own space (the
table's origin at its origin_depth; no turn); each building in its own frame (front +Z, turned by its
heading, y = 0 at its depth). Every building's base reaches down to the floor (footings of masonry, a
crag of rock under the temple's jut), and what stands against a wall runs back into it.

Objects in the .glb (scripts/ruins.gd draws them): one mesh a building (Gate, Temple, Colonnade,
FacadeNorth, Bridge, Landing, Pyramid, Queen, FacadeSouth, FacadeTomb), one a stair (StairRim,
StairEast), Field (spilled stones), RuinsGlow (what glows); empties Rock<Building>0000..
(collision spheres, scale = radius), ReefSpot.., FishSpot.., Lantern...
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_helpers = open(os.path.join(HERE, "build_ruins.py")).read().split("# The layout follows the concept art")[0]
exec(compile(_helpers, "build_ruins.py", "exec"))
# (and its checks, sphere fitting numbers and packing, which come after its layout)
_source = open(os.path.join(HERE, "build_ruins.py")).read()


def _between(start, end):
    at = _source.index(start)
    return _source[at:_source.index(end, at)]


for _part in (_between("def wrong_faces(obj):", "all_pieces = "), _between("RMAX = 12.0", "spheres = []"),
              _between("def pack(chosen):", "pack(lambda"), _between("def texel_density(", "print(\"RUINS texel density"),
              _between("HEAD_ROWS = [", "# She lies on the paving")):
    # (its inside-out test nudges rays 1e-5 m off a face: far from the origin, as here, that is under a
    # float's step and the ray met its own face; a millimetre is still far below any piece's size)
    exec(compile(_part.replace("* 1e-5", "* 1e-3"), "build_ruins.py", "exec"))

GLB = os.path.join(HERE, "..", "models", "atlantis_canyon.glb")
BLEND = os.path.join(HERE, "blend", "atlantis_canyon.blend")
ATLAS = os.path.join(HERE, "..", "textures", "ruins_canyon_atlas.png")
STATUE_ATLAS = os.path.join(HERE, "..", "textures", "ruins_canyon_statue.png")
# (4096: the canyon's terraces, footings and fronts are about twice the old precinct's stone to paint)
ATLAS_SIZE = 4096
LAYOUT = json.load(open(os.path.join(HERE, "..", "data", "ruins_layout.json")))
GROUND = json.load(open(os.path.join(HERE, "ruins_ground.json")))
RNG.seed(11)
# (no spheres centred under the floor here: on a canyon's slope one so big came up through the floor
# beside its building, into open water; and none bigger than this)
DEEP = ()
RMAX = 5.0

SURFACE = 40.0
ORIGIN_Y = SURFACE - LAYOUT["origin_depth"]
BUILDINGS = list(LAYOUT["buildings"].keys())
STAIRS = list(LAYOUT["stairs"].keys())
NAMES = tuple(BUILDINGS + STAIRS + ["Field", "RuinsGlow"])
PARTS = {name: [] for name in NAMES}
PARTS["RuinsField"] = []  # (cut() makes its cutters there)
SOLIDS = []
ROCK = weathered("rock", (0.25, 0.27, 0.29), (0.2, 0.22, 0.24), (0.31, 0.33, 0.34), 2.6, growth=0.6)


def rock_block(sx, sy, sz, rough=0.25):
    """A block of the canyon's rock from y = 0 to sy, centred on x and z: its sides broken into
    facets (corners pushed in and out at three heights), its top left square for what stands on it."""
    hx, hz = sx * 0.5, sz * 0.5
    rings = [0.0, sy * RNG.uniform(0.35, 0.6), sy]
    # (a low block is left plain: jittered, its thin sides twisted inside out)
    rough = min(rough, sy * 0.12, sx * 0.08, sz * 0.08)
    verts = []
    for k, y in enumerate(rings):
        j = rough if k < 2 else 0.0
        for cx, cz in ((-hx, -hz), (hx, -hz), (hx, hz), (-hx, hz)):
            verts.append((cx + RNG.uniform(-j, j * 0.6) * (1.0 if cx > 0 else -1.0), y + (RNG.uniform(-1.0, 1.0) * min(0.3, sy * 0.1) if k == 1 else 0.0), cz + RNG.uniform(-j, j * 0.6) * (1.0 if cz > 0 else -1.0)))
    faces = [(0, 3, 2, 1), (8, 9, 10, 11)]
    for k in range(2):
        for i in range(4):
            i2 = (i + 1) % 4
            faces.append((k * 4 + i, k * 4 + i2, (k + 1) * 4 + i2, (k + 1) * 4 + i))
    return verts, faces


# --- The floor (the ruins' own x, z -> y).
def ground(x, z):
    gx = min(max((x - GROUND["x0"]) / GROUND["step"], 0.0), GROUND["cols"] - 1.001)
    gz = min(max((z - GROUND["z0"]) / GROUND["step"], 0.0), GROUND["rows"] - 1.001)
    c, r = int(gx), int(gz)
    fx, fz = gx - c, gz - r
    h = GROUND["heights"]
    i = r * GROUND["cols"] + c
    top = h[i] + (h[i + 1] - h[i]) * fx
    bottom = h[i + GROUND["cols"]] + (h[i + GROUND["cols"] + 1] - h[i + GROUND["cols"]]) * fx
    return top + (bottom - top) * fz


def ground_normal(x, z):
    dx = ground(x + 0.5, z) - ground(x - 0.5, z)
    dz = ground(x, z + 0.5) - ground(x, z - 0.5)
    return Vector((-dx, 1.0, -dz)).normalized()


def lowest_under(M, x0, x1, z0, z1, step=0.8):
    """The lowest floor under a rectangle of a frame M (its own x, z)."""
    low = 1e9
    nx = max(1, int((x1 - x0) / step) + 1)
    nz = max(1, int((z1 - z0) / step) + 1)
    for i in range(nx + 1):
        for j in range(nz + 1):
            p = M @ Vector((x0 + (x1 - x0) * i / nx, 0.0, z0 + (z1 - z0) * j / nz))
            low = min(low, ground(p.x, p.z))
    return low


def frame(name):
    b = LAYOUT["buildings"][name]
    return T(b["at"][0] - LAYOUT["origin"][0], SURFACE - b["depth"] - ORIGIN_Y, b["at"][1] - LAYOUT["origin"][1]) @ RY(b["heading"])


def footing(M, part, x0, x1, z0, z1, top, mat=None, below=1.0, band=2.4, cell=3.0):
    """What a terrace stands on, down into the floor under it: a band of masonry under its top (its
    built edge), and under that the canyon's own rock in blocks about `cell` square, each reaching
    down only as far as the floor under it, so the base steps down the terraced wall with it (one
    box to the lowest floor stood as a tower of masonry over the drop)."""
    made = [piece(box(x1 - x0, band, z1 - z0), mat or MASONRY, part, M @ T((x0 + x1) * 0.5, top - band, (z0 + z1) * 0.5))]
    inv = M.inverted()
    nx = max(1, int(math.ceil((x1 - x0) / cell)))
    nz = max(1, int(math.ceil((z1 - z0) / cell)))
    for i in range(nx):
        for j in range(nz):
            a0, a1 = x0 + (x1 - x0) * i / nx, x0 + (x1 - x0) * (i + 1) / nx
            b0, b1 = z0 + (z1 - z0) * j / nz, z0 + (z1 - z0) * (j + 1) / nz
            low = lowest_under(M, a0, a1, b0, b1, step=0.6) - below
            bottom = (inv @ Vector((M.translation.x, low, M.translation.z))).y
            # (a block under 0.6 m would lie buried under the band, and so thin its jittered sides fold)
            if bottom >= top - band - 0.6:
                continue
            # (a little uneven, so the blocks read as rock, not as a grid)
            inset = RNG.uniform(0.0, 0.18)
            made.append(piece(rock_block(a1 - a0 - inset, top - band + 0.05 - bottom, b1 - b0 - inset), ROCK, part,
                              M @ T((a0 + a1) * 0.5, bottom, (b0 + b1) * 0.5) @ RY(RNG.uniform(-0.02, 0.02))))
    return made[0]


def crag(M, part, top_r, top_y, bottom_y, lean=(0.0, 0.0), sides=9):
    """A jagged mass of rock tapering down from a round top (the temple's jut stands on one): rings
    of rock, each a little uneven, narrowing and leaning towards `lean` as they go down."""
    rings = 6
    verts, faces = [], []
    for k in range(rings):
        t = k / (rings - 1)
        y = top_y + (bottom_y - top_y) * t
        r = top_r * (1.0 - 0.72 * t ** 1.3)
        for s in range(sides):
            a = math.tau * (s + 0.37 * k) / sides
            rr = r * RNG.uniform(0.82, 1.08) if k else r * RNG.uniform(0.95, 1.0)
            verts.append((rr * math.sin(a) + lean[0] * t, y + (RNG.uniform(-0.6, 0.6) if k else 0.0), rr * math.cos(a) + lean[1] * t))
    for k in range(rings - 1):
        for s in range(sides):
            s2 = (s + 1) % sides
            faces.append((k * sides + s, k * sides + s2, (k + 1) * sides + s2, (k + 1) * sides + s))
    faces.append(tuple(reversed(range(sides))))
    verts.append((lean[0] * 1.1, bottom_y - 2.0, lean[1] * 1.1))
    tip = len(verts) - 1
    last = (rings - 1) * sides
    faces += [(last + s, last + (s + 1) % sides, tip) for s in range(sides)]
    # (the top ring is the platform's underside: capped flat)
    return piece((verts, faces), ROCK, part, M, sharp=30.0)


LANTERNS, FISH = [], []


def mark(M, lanterns=(), fish=()):
    for p in lanterns:
        LANTERNS.append(tuple(M @ Vector(p)))
    for p in fish:
        FISH.append(tuple(M @ Vector(p)))


# ============================================================================================
# --- The gate on the north rim: the way in from the shelf, through the carved gate, onto a small
# court at the head of the stair down the wall. Its own +Z is the way (north, out on the shelf).
B = frame("Gate")
z = 4.4
while z < 19.6:
    for x in (-1.95, 0.0, 1.95):
        if RNG.random() < 0.17:
            continue
        M = B @ T(x + RNG.uniform(-0.12, 0.12), RNG.uniform(-0.28, -0.16), z + RNG.uniform(-0.1, 0.1)) @ RY(RNG.uniform(-0.08, 0.08)) @ RX(RNG.uniform(-0.05, 0.05)) @ RZ(RNG.uniform(-0.05, 0.05))
        piece(box(1.85, 0.42, 1.6), STONE, "Gate", M, collide=False)
    z += 1.72
for side, heights in ((-1.0, (2.3, 0.9, 3.3)), (1.0, (1.3, 3.0, 0.6))):
    for zz, h in zip((7.0, 12.0, 17.0), heights):
        column(B @ T(side * 4.6, -0.1, zz) @ RY(RNG.uniform(0, 1)), "Gate", broken=h)
fallen_column(tuple(B @ Vector((-6.6, 0.0, 11.5))), B.to_euler().y - 0.25, "Gate", (1.6, 1.6, 1.4))
for i in range(9):
    x, zz = RNG.uniform(-6.0, 6.0), RNG.uniform(-4.0, -1.2)
    M = B @ T(x, RNG.uniform(-0.3, -0.18), zz) @ RY(RNG.uniform(-0.3, 0.3)) @ RX(RNG.uniform(-0.05, 0.05))
    piece(box(RNG.uniform(1.6, 2.4), 0.42, RNG.uniform(1.3, 1.9)), STONE, "Gate", M, collide=False)
for side in (-1.0, 1.0):
    post = B @ T(side * 3.4, 0.0, 0.0)
    piece(box(2.6, 1.6, 2.6, taper=0.1), STONE, "Gate", post @ T(0.0, -1.2, 0.0))
    piece(box(1.8, 8.3, 1.8), STONE, "Gate", post @ T(0.0, 0.2, 0.0) @ RZ(side * 0.004))
    for face in (1.0, -1.0):
        panel = post @ RY(0.0 if face > 0 else math.pi) @ T(0.0, 1.3, 0.9)
        piece(box(1.1, 6.2, 0.08), BRONZE, "Gate", panel, collide=False)
        for k in range(3):
            piece(prism(spiral_outline(0.42), 0.08), GOLD, "RuinsGlow", panel @ T(0.0, 1.1 + 2.0 * k, 0.07) @ RZ(math.pi * (k % 2)), collide=False)
LINTEL = B @ T(0.0, 8.5, 0.0) @ RZ(-0.018)
piece(box(9.6, 1.5, 2.2), STONE, "Gate", LINTEL)
piece(box(10.4, 0.5, 2.7), STONE, "Gate", LINTEL @ T(0.0, 1.5, 0.0))
for face in (1.0, -1.0):
    for k in range(5):
        piece(prism(spiral_outline(0.55), 0.16), RELIEF, "Gate", LINTEL @ RY(0.0 if face > 0 else math.pi) @ T(-3.6 + 1.8 * k, 0.75, 1.12) @ RZ(math.pi * (k % 2)), collide=False)
piece(box(1.8, 0.5, 2.7), STONE, "Gate", B @ T(6.0, 0.05, 3.0) @ RY(0.7) @ RX(0.25) @ RZ(0.3))
mark(B, lanterns=[(0.0, 4.0, 0.0)], fish=[(0.0, 3.0, 14.0), (0.0, 4.0, -3.0)])

# --- The temple on the north rim, jutting out over the drop on a crag of rock (the concept's upper
# left): a stepped round platform, twelve columns, a round beam, a dome broken open at its front, the
# empty pedestal with her broken feet.
B = frame("Temple")
TEMPLE = B @ RZ(0.015) @ RX(-0.01)
piece(lathe([(0.0, -1.6), (10.6, -1.6), (10.6, 0.4), (10.0, 0.4), (10.0, 0.8), (9.4, 0.8), (9.4, 1.2), (0.0, 1.2)], 24), STONE, "Temple", TEMPLE)
# (the crag: down to the floor under the platform's middle and leaning into the wall behind it)
deep_under = lowest_under(B, -3.0, 3.0, -3.0, 3.0)
into = (B.inverted().to_3x3() @ Vector((0.0, 0.0, -1.0)))
crag(B, "Temple", 10.3, -1.4, min(-14.0, (deep_under - B.translation.y) * 0.6), lean=(into.x * 4.0, into.z * 4.0))
RING_R = 7.4
SHAFT = 7.0
for k in range(12):
    a = math.tau * (k + 0.5) / 12.0
    M = TEMPLE @ RY(a) @ T(0.0, 1.0, RING_R) @ RY(RNG.uniform(0, 1))
    if k == 5:
        column(M, "Temple", shaft=SHAFT, broken=2.4)
    else:
        column(M, "Temple", shaft=SHAFT, inlay=True)
BEAM_Y = 1.0 + 0.2 + SHAFT + 0.82
piece(revolve([(6.5, BEAM_Y), (8.3, BEAM_Y), (8.3, BEAM_Y + 1.2), (6.5, BEAM_Y + 1.2)], 24, math.pi / 24.0), STONE, "Temple", TEMPLE)
piece(revolve([(6.7, BEAM_Y + 1.2), (8.7, BEAM_Y + 1.2), (8.7, BEAM_Y + 1.65), (6.7, BEAM_Y + 1.65)], 24, math.pi / 24.0), STONE, "Temple", TEMPLE)
for k in range(12):
    piece(prism(spiral_outline(0.42), 0.12), RELIEF, "Temple", TEMPLE @ RY(math.tau * k / 12.0) @ T(0.0, BEAM_Y + 0.6, 8.32), collide=False)
D0 = BEAM_Y + 1.65
dome = piece(revolve([(8.2, D0), (7.9, D0 + 1.4), (7.0, D0 + 2.9), (5.4, D0 + 4.1), (3.0, D0 + 4.9), (0.9, D0 + 5.2), (0.6, D0 + 4.4), (2.6, D0 + 4.15),
                      (4.8, D0 + 3.45), (6.2, D0 + 2.35), (7.0, D0 + 1.1), (7.1, D0)], 24, math.pi / 24.0), MASONRY, "Temple", TEMPLE)
cut(dome, lathe([(0.0, -3.6), (2.6, -2.6), (3.6, 0.0), (2.6, 2.6), (0.0, 3.6)], 10), TEMPLE @ T(2.4, D0 + 4.0, 4.6) @ S(1.25, 1.0, 1.0))
piece(box(3.2, 1.5, 2.6, taper=0.08), MASONRY, "Temple", TEMPLE @ T(-3.0, 1.0, -2.2) @ RY(0.3))
piece(box(3.6, 0.3, 3.0), STONE, "Temple", TEMPLE @ T(-3.0, 2.45, -2.2) @ RY(0.3))
for side in (-1.0, 1.0):
    piece(frustum(7, 0.42, 0.38, 1.0, jag=0.3), FACE, "Temple", TEMPLE @ T(-3.0, 2.7, -2.2) @ RY(0.3) @ T(side * 0.7, 0.0, 0.1) @ S(1.0, 1.0, 1.6), sharp=70.0)
for x, zz, s in ((1.2, -2.8, 1.0), (-2.0, -3.4, 0.8), (3.2, 0.4, 0.7)):
    M = TEMPLE @ T(x, RNG.uniform(-0.4, -0.2) + 1.1, zz) @ RY(RNG.uniform(0, 3)) @ RX(RNG.uniform(-0.4, 0.4)) @ RZ(RNG.uniform(-0.4, 0.4))
    piece(box(1.5 * s, 0.9 * s, 1.1 * s), MASONRY, "Temple", M)
mark(B, lanterns=[(0.0, 6.0, 0.0)], fish=[(0.0, 4.5, 0.0), (2.0, 16.5, 3.0), (0.0, 3.0, 12.5)])

WAVE = []
for k in range(25):
    t = k / 24.0
    WAVE.append((-2.6 + 5.2 * t, 0.12 + 0.13 * math.sin(t * math.tau * 4.0) + 0.1 * max(0.0, math.sin(t * math.tau * 4.0 + 1.2)) ** 6))
WAVE += [(2.6, -0.16), (-2.6, -0.16)]

# --- The colonnade on its terrace, built out from the north wall: two rows of six columns along the
# canyon (an aisle between), the beam over part of the front row, the back row more broken; a
# frieze of spirals along the terrace's front; the bridge comes onto its west end.
B = frame("Colonnade")
tr = LAYOUT["buildings"]["Colonnade"]["terrace"]
tx, tz, sx, sz = tr["at"][0], tr["at"][1], tr["size"][0], tr["size"][1]
footing(B, "Colonnade", tx - sx / 2, tx + sx / 2, tz - sz / 2, tz + sz / 2, 0.0)
piece(box(sx + 0.6, 0.5, sz + 0.6), STONE, "Colonnade", B @ T(tx, -0.45, tz))
for k in range(7):
    piece(prism(spiral_outline(0.6), 0.14), RELIEF, "Colonnade", B @ T(tx - sx / 2 + sx * (k + 0.5) / 7.0, -1.5, tz + sz / 2 + 0.04), collide=False)
piece(prism(WAVE, 0.08), GOLD, "RuinsGlow", B @ T(tx, -2.6, tz + sz / 2 + 0.02) @ S(sx / 5.4, 1.0, 1.0), collide=False)
STOA_Z = (2.7, -2.7)
STOA_X = [-6.4 + 3.2 * k for k in range(5)]
for row, zz in enumerate(STOA_Z):
    for k, x in enumerate(STOA_X):
        M = B @ T(x, -0.2, zz) @ RY(RNG.uniform(0, 1))
        if row == 1:
            # (the rock-cut front stands behind: the back row is gone, the aisle runs between)
            continue
        broken = {(0, 0): 3.1, (0, 5): 1.4, (1, 0): 2.2, (1, 2): 4.0, (1, 3): 0.9, (1, 5): 3.4}.get((row, k), 0.0)
        if (row, k) == (1, 4):
            piece(lathe([(0.0, -0.5), (0.58, -0.5), (0.58, 0.12), (0.5, 0.25), (0.0, 0.25)], 10), STONE, "Colonnade", M)
            continue
        column(M, "Colonnade", broken=broken)
STOA_TOP = 5.42
piece(box(STOA_X[4] - STOA_X[1] + 1.6, 0.85, 1.2), STONE, "Colonnade", B @ T((STOA_X[1] + STOA_X[4]) * 0.5, STOA_TOP, STOA_Z[0]))
for x, zz in ((STOA_X[1] + 1.6, 1.1), (STOA_X[3] + 1.4, -1.4)):
    piece(frustum(10, 0.5, 0.5, 0.9, phase=0.3), RED, "Colonnade", B @ T(x, 0.45, zz) @ RX(math.pi * 0.5) @ RZ(RNG.uniform(0, 3)) @ T(0.0, -0.45, 0.0))
mark(B, lanterns=[(0.0, 4.0, 0.0)], fish=[(0.0, 3.0, 0.0), (6.0, 3.0, 5.0), (-4.0, 7.0, 3.0)])


# --- Rock-cut temple fronts (Petra's way, in the island's style): a mass of the cliff's own rock with
# a front carved in it: a plinth, four half-columns with cushion capitals, a beam with running spirals,
# a low gable, a doorway into a small chamber cut back into the rock (fish can go in). The rock runs
# back `deep` metres into the wall, so its back is in the floor.
def facade(name):
    B = frame(name)
    W, H, D = LAYOUT["buildings"][name]["facade"]
    # (the floor behind it is filled up over its top: the table's fill ledge, so its rock is buried in a cliff)
    body = piece(box(W + 0.6, H + 3.0, D, top_jag=1.0), ROCK, name, B @ T(0.0, -3.0, -D * 0.5 + 0.2))
    cut(body, box(3.0, 5.2, 7.2), B @ T(0.0, 0.0, -2.6))
    footing(B, name, -W * 0.5, W * 0.5, 0.0, 1.6, 0.0, below=1.0)
    piece(box(W * 0.92, 0.6, 1.4), STONE, name, B @ T(0.0, -0.3, 0.9))
    top = H * 0.6
    for x in (-W * 0.36, -W * 0.16, W * 0.16, W * 0.36):
        piece(frustum(8, 0.42, 0.5, top - 0.8, phase=0.2), RED, name, B @ T(x, 0.3, 0.42))
        piece(lathe([(0.0, top - 0.55), (0.52, top - 0.55), (0.72, top - 0.32), (0.7, top - 0.12), (0.0, top - 0.12)], 8), DARK, name, B @ T(x, 0.0, 0.42))
    piece(box(W * 0.9, 1.3, 1.1), STONE, name, B @ T(0.0, top - 0.15, 0.45))
    for k in range(5):
        piece(prism(spiral_outline(0.45), 0.14), RELIEF, name, B @ T(-W * 0.32 + W * 0.16 * k, top + 0.5, 1.02) @ RZ(math.pi * (k % 2)), collide=False)
    piece(prism([(-W * 0.47, 0.0), (W * 0.47, 0.0), (0.0, 2.0)], 0.9), STONE, name, B @ T(0.0, top + 1.15, 0.35))
    piece(box(4.0, 0.6, 1.0), STONE, name, B @ T(0.0, 5.2, 0.4))
    piece(prism(spiral_outline(0.4), 0.1), GOLD, "RuinsGlow", B @ T(0.0, top + 1.8, 0.82), collide=False)
    mark(B, lanterns=[(0.0, 2.4, -4.0)], fish=[(0.0, 2.6, 3.5)])


for name in ("FacadeNorth", "FacadeSouth", "FacadeTomb"):
    facade(name)

# --- The bridge across the canyon (the concept's middle): a deck on a round arch springing from both
# walls, spandrels filled, a broken parapet; its own z runs north to south, its ends on the colonnade's
# terrace and the landing. span = [half its length, the arch's radius, how far below the deck it springs].
B = frame("Bridge")
L, R, SPRING = LAYOUT["buildings"]["Bridge"]["span"]
WIDTH = 4.6
piece(box(WIDTH, 1.2, 2.0 * L), STONE, "Bridge", B @ T(0.0, -1.2, 0.0))
outline = [(-L, -1.15), (L, -1.15), (L, -SPRING), (R, -SPRING)]
for k in range(1, 16):
    a = math.pi * k / 16.0
    outline.append((R * math.cos(a), -SPRING + R * math.sin(a)))
outline += [(-R, -SPRING), (-L, -SPRING)]
piece(prism([(-zz, y) for zz, y in outline], WIDTH - 0.4), MASONRY, "Bridge", B @ RY(math.pi * 0.5))
ring = []
for k in range(17):
    a = math.pi * k / 16.0
    ring.append((R * math.cos(a), -SPRING + R * math.sin(a)))
band = [((R + 1.0) * math.cos(math.pi * k / 16.0), -SPRING + (R + 1.0) * math.sin(math.pi * k / 16.0)) for k in reversed(range(17))]
piece(prism([(-zz, y) for zz, y in ring] + [(-zz, y) for zz, y in band], WIDTH), STONE, "Bridge", B @ RY(math.pi * 0.5))
for end in (-1.0, 1.0):
    z0, z1 = (R - 0.5, L) if end > 0 else (-L, -R + 0.5)
    footing(B, "Bridge", -WIDTH * 0.5 + 0.2, WIDTH * 0.5 - 0.2, z0, z1, -SPRING + 0.2)
for side in (-1.0, 1.0):
    zz = -L + 0.6
    while zz < L - 0.6:
        length = RNG.uniform(2.5, 5.5)
        if RNG.random() < 0.72:
            piece(box(0.45, RNG.uniform(0.7, 1.0), min(length, L - 0.6 - zz), top_jag=0.12), STONE, "Bridge", B @ T(side * (WIDTH * 0.5 - 0.22), -0.05, zz + min(length, L - 0.6 - zz) * 0.5))
        zz += length + RNG.uniform(0.6, 1.6)
mark(B, fish=[(0.0, -SPRING + 4.0, 0.0), (0.0, 2.5, 0.0)])

# --- The landing on the south wall where the bridge comes in, and on it the tall pillar with the
# glowing crystal (the concept's middle right).
B = frame("Landing")
tr = LAYOUT["buildings"]["Landing"]["terrace"]
tx, tz, sx, sz = tr["at"][0], tr["at"][1], tr["size"][0], tr["size"][1]
footing(B, "Landing", tx - sx / 2, tx + sx / 2, tz - sz / 2, tz + sz / 2, 0.0)
piece(box(sx + 0.6, 0.5, sz + 0.6), STONE, "Landing", B @ T(tx, -0.45, tz))
PILLAR = B @ T(-4.2, 0.0, 0.0) @ RX(0.02) @ RZ(-0.02)
piece(box(3.0, 2.2, 3.0, taper=0.1), STONE, "Landing", PILLAR @ T(0.0, -1.0, 0.0) @ RY(0.3))
for k, (y0, y1) in enumerate(((1.2, 6.2), (6.2, 11.2), (11.2, 15.6))):
    piece(frustum(10, 0.82 + 0.03 * k, 0.85 + 0.03 * k, y1 - y0, phase=0.05 * k), RED, "Landing", PILLAR @ T(0.0, y0, 0.0))
for y in (6.0, 14.6):
    piece(revolve([(0.86, y), (1.02, y), (1.02, y + 0.42), (0.86, y + 0.42)], 10), GOLD, "RuinsGlow", PILLAR, collide=False)
piece(lathe([(0.0, 15.5), (0.95, 15.5), (1.4, 15.9), (1.35, 16.3), (1.0, 16.55), (0.0, 16.55)], 10), STONE, "Landing", PILLAR)
piece(box(2.3, 0.45, 2.3), STONE, "Landing", PILLAR @ T(0.0, 16.5, 0.0))
for k in range(6):
    leaf = [(-0.32, 0.0), (0.32, 0.0), (0.4, 0.5), (0.0, 1.15), (-0.4, 0.5)]
    piece(prism(leaf, 0.1), GOLD, "RuinsGlow", PILLAR @ RY(math.tau * k / 6.0) @ T(0.0, 16.95, 0.42) @ RX(-0.5), collide=False)
piece(lathe([(0.0, 16.95), (0.55, 16.95), (0.55, 17.25), (0.0, 17.25)], 10), GOLD, "RuinsGlow", PILLAR, collide=False)
piece(lathe([(0.0, 17.1), (0.48, 17.9), (0.4, 19.5), (0.0, 20.6)], 6), CRYSTAL, "RuinsGlow", PILLAR @ RZ(0.04))
for x, zz in ((3.0, 1.6), (-2.0, -1.8)):
    amphora(B @ T(x, -0.2, zz) @ RX(RNG.uniform(-0.2, 0.2)) @ S(1.25), "Landing")
mark(B, lanterns=[(-4.2, 19.4, 0.0)], fish=[(-4.2, 9.0, 0.0), (2.0, 3.0, 2.0)])

# --- The stepped pyramid half into the south wall on its own terrace: five tiers and a cap, a stair up
# its front (+Z, north, to the canyon) to a small high door, a dark doorway at its foot into a
# chamber, a shaft up from the chamber to the high door. Its back is in the wall.
B = frame("Pyramid")
tr = LAYOUT["buildings"]["Pyramid"]["terrace"]
tx, tz, sx, sz = tr["at"][0], tr["at"][1], tr["size"][0], tr["size"][1]
footing(B, "Pyramid", tx - sx / 2, tx + sx / 2, tz - sz / 2, tz + sz / 2, -0.2)
PY = [(18.0, -1.2, 2.2), (14.8, 2.2, 4.4), (11.6, 4.4, 6.6), (8.4, 6.6, 8.8), (5.2, 8.8, 11.6)]
tiers = [piece(box(size, y1 - y0, size, taper=0.12), MASONRY, "Pyramid", B @ T(0.0, y0, 0.0)) for size, y0, y1 in PY]
piece(lathe([(3.0, 11.5), (0.0, 14.6)], 4, math.pi * 0.25), MASONRY, "Pyramid", B)
CH = (2.2, 0.0)
DOOR_X = 3.8
for tier in tiers[:2]:
    cut(tier, box(7.0, 4.4, 7.0), B @ T(CH[0], 0.2, CH[1]))
    cut(tier, box(3.0, 2.8, 8.0), B @ T(DOOR_X, 0.2, 6.5))
for tier in tiers[1:]:
    cut(tier, box(3.0, 7.4, 3.0), B @ T(0.0, 4.0, 0.0))
cut(tiers[4], box(3.0, 2.6, 6.0), B @ T(0.0, 8.85, 3.0))
profile = [(13.0, -0.8)]
RISE = 14
for i in range(RISE):
    zz = 12.2 - (12.2 - 2.4) * i / RISE
    profile += [(zz, 8.8 * i / RISE), (zz, 8.8 * (i + 1) / RISE)]
profile += [(1.8, 8.8), (1.8, -0.8)]
piece(prism([(-zz, y) for zz, y in profile], 3.4), STONE, "Pyramid", B @ RY(math.pi * 0.5))
for side in (-1.0, 1.0):
    wall = [(-12.6, -0.8), (-12.6, 0.9), (-2.4, 9.6), (-1.8, 9.6), (-1.8, -0.8)]
    piece(prism(wall, 0.45), STONE, "Pyramid", B @ T(side * 1.92, 0.0, 0.0) @ RY(math.pi * 0.5))
piece(box(4.2, 0.6, 1.2), STONE, "Pyramid", B @ T(DOOR_X, 3.0, 9.2))
piece(prism(spiral_outline(0.42), 0.1), GOLD, "RuinsGlow", B @ T(DOOR_X, 3.25, 9.84), collide=False)
for x, zz in ((9.0, 10.0), (-8.6, 7.4)):
    piece(box(1.6, 1.0, 1.3), MASONRY, "Pyramid", B @ T(x, -0.35, zz) @ RY(RNG.uniform(0, 3)) @ RX(RNG.uniform(-0.3, 0.3)))
mark(B, lanterns=[(CH[0], 2.4, CH[1])], fish=[(0.0, 16.0, 0.0), (CH[0], 2.4, CH[1]), (6.0, 4.0, 12.0)])

# (she lies sunk this far below her ledge: Ruins.routes uses the same)
QUEEN_SINK = -0.8
# --- The sea queen, fallen to the canyon's floor: her colossal hollow head on the back of it, face up
# and turned, sunk to the cheeks, and her hand palm down beside her.
B = frame("Queen")
HEAD_AT = B @ T(0.0, QUEEN_SINK, 0.0) @ RY(0.25) @ RX(1.0 - math.pi * 0.5)
face = piece(head(), FACE, "Queen", HEAD_AT, sharp=80.0)
inner_v, inner_f = head(plain=True)
inner_v = [(x * 0.78, (y - 3.0) * 0.8 + 3.0, z * 0.8 - 0.1) for x, y, z in inner_v]
cut(face, (inner_v, inner_f), HEAD_AT)
cut(face, lathe([(0.0, -1.2), (0.55, -0.8), (0.75, 0.0), (0.55, 0.8), (0.0, 1.2)], 10), HEAD_AT @ T(0.0, 2.12, 2.0) @ RX(math.pi * 0.5) @ S(1.15, 1.4, 0.45))
for side in (-1.0, 1.0):
    cut(face, lathe([(0.0, -1.0), (1.2, -0.7), (1.75, 0.0), (1.2, 0.7), (0.0, 1.0)], 10), HEAD_AT @ T(side * 2.9, 3.6, -0.4) @ RZ(math.pi * 0.5) @ S(1.0, 1.1, 1.15))
for side in (-1.0, 1.0):
    at = HEAD_AT @ Vector((side * 7.6, 3.2, -0.2))
    piece(box(1.3, 0.55, 0.9), STATUE, "Queen", T(at.x, ground(at.x, at.z) - 0.15, at.z) @ RY(RNG.uniform(0, 3)) @ RX(0.3))
HAND = B @ T(6.4, 1.25, 2.6) @ RY(-0.5) @ S(1.3)
hand_floor = ground(*(lambda p: (p.x, p.z))(HAND @ Vector((0.0, 0.0, 1.4)))) - B.translation.y
HAND = B @ T(6.4, 0.5 + hand_floor, 2.6) @ RY(-0.5) @ S(1.3)
piece(frustum(8, 0.72, 0.8, 1.7, low_jag=0.2), STATUE, "Queen", HAND @ T(0.0, 0.0, 0.45) @ RX(-math.pi * 0.5))
piece(revolve([(0.74, -0.3), (0.98, -0.3), (0.98, 0.25), (0.74, 0.25)], 10), BRONZE, "Queen", HAND @ T(0.0, 0.0, -0.45) @ RX(math.pi * 0.5))
piece(box(1.9, 0.72, 2.05, taper=0.08), STATUE, "Queen", HAND @ T(0.0, -0.36, 1.375))
for x, scale, spread in ((-0.72, 0.85, -0.22), (-0.24, 1.0, -0.07), (0.24, 1.07, 0.07), (0.72, 1.0, 0.2)):
    M = HAND @ T(x, 0.0, 2.35) @ RY(spread)
    for length, curl in ((0.95, 0.22), (0.62, 0.4), (0.5, 0.42)):
        M = M @ RX(curl)
        piece(frustum(8, 0.27, 0.22, length * scale + 0.12, phase=0.5), STATUE, "Queen", M @ RX(math.pi * 0.5) @ T(0.0, -0.12, 0.0), sharp=80.0)
        M = M @ T(0.0, 0.0, length * scale - 0.08)
M = HAND @ T(0.95, -0.05, 0.95) @ RY(1.0)
for length, curl in ((0.85, 0.25), (0.65, 0.35)):
    M = M @ RX(curl)
    piece(frustum(6, 0.3, 0.25, length, phase=0.5), STATUE, "Queen", M @ RX(math.pi * 0.5), sharp=80.0)
    M = M @ T(0.0, 0.0, length)
LANTERNS.append(tuple(HEAD_AT @ Vector((0.0, 3.6, -0.6))))
mark(B, fish=[(0.0, 9.0, 0.0), (8.0, 3.0, 4.0)])


# --- The stairs down the walls: each flight a solid of masonry with its steps on top and low walls
# either side, reaching down into the floor; a landing between two points at the same depth.
def stairs(name):
    s = LAYOUT["stairs"][name]
    w = s["width"]
    pts = [Vector((p[0] - LAYOUT["origin"][0], SURFACE - p[1] - ORIGIN_Y, p[2] - LAYOUT["origin"][1])) for p in s["points"]]
    for k, (a, b) in enumerate(zip(pts, pts[1:])):
        flat = Vector((b.x - a.x, 0.0, b.z - a.z))
        if k > 0 and abs(a.y - b.y) >= 0.05 and abs(pts[k - 1].y - a.y) < 0.05:
            # (a flight going down off a landing at a turn starts at the landing's edge, not its
            # middle: else the landing's slab covers its first steps)
            before = Vector((a.x - pts[k - 1].x, 0.0, a.z - pts[k - 1].z)).normalized()
            if abs(before.dot(flat.normalized())) < 0.7:
                a = a + flat.normalized() * (w * 0.5)
                flat = Vector((b.x - a.x, 0.0, b.z - a.z))
        run = flat.length
        mid = (a + b) * 0.5
        F = T(mid.x, 0.0, mid.z) @ RY(math.atan2(flat.x, flat.z))
        low = lowest_under(F, -w * 0.5, w * 0.5, -run * 0.5 - 0.6, run * 0.5 + 0.6) - 1.0
        if abs(a.y - b.y) < 0.05:
            footing(F, name, -w * 0.5, w * 0.5, -run * 0.5 - 0.6, run * 0.5 + 0.6, a.y)
            continue
        n = max(3, int(round(abs(a.y - b.y) / 0.55)))
        top = []
        for i in range(n):
            y = a.y + (b.y - a.y) * i / (n - 1)
            z0 = -run * 0.5 - 0.6 + (run + 1.2) * i / n
            z1 = -run * 0.5 - 0.6 + (run + 1.2) * (i + 1) / n
            top += [(z0, y), (z1, y)]
        # (the flight is a slab of masonry 3 m deep under its steps; rock stands under it down to the floor)
        outline = top + [(top[-1][0], b.y - 3.0), (top[0][0], a.y - 3.0)]
        piece(prism([(-zz, y) for zz, y in outline], w), MASONRY, name, F @ RY(math.pi * 0.5))
        cells = max(1, int(math.ceil((run + 1.2) / 3.0)))
        for c in range(cells):
            c0 = -run * 0.5 - 0.6 + (run + 1.2) * c / cells
            c1 = -run * 0.5 - 0.6 + (run + 1.2) * (c + 1) / cells
            under = a.y - 3.0 + (b.y - a.y) * max(0.0, min(1.0, ((c0 + c1) * 0.5 + run * 0.5) / max(run, 0.01))) + 0.4
            floor_low = lowest_under(F, -w * 0.5, w * 0.5, c0, c1, step=0.6) - 1.0
            if floor_low < under - 0.6:
                piece(rock_block(w - RNG.uniform(0.0, 0.2), under - floor_low, c1 - c0 - RNG.uniform(0.0, 0.15)), ROCK, name, F @ T(0.0, floor_low, (c0 + c1) * 0.5))
        for side in (-1.0, 1.0):
            # (the low walls stop short of both ends: a landing may turn off either way)
            ya = a.y + (b.y - a.y) * 1.6 / run
            yb = b.y - (b.y - a.y) * 1.6 / run
            wall = [(-run * 0.5 + 1.6, ya + 0.9), (run * 0.5 - 1.6, yb + 0.9), (run * 0.5 - 1.6, yb - 0.4), (-run * 0.5 + 1.6, ya - 0.4)]
            piece(prism([(-zz, y) for zz, y in wall], 0.4), STONE, name, F @ T(side * (w * 0.5 - 0.2), 0.0, 0.0) @ RY(math.pi * 0.5))


for name in STAIRS:
    stairs(name)


# --- What has spilled: carved frieze blocks, drums, capitals, jars and rubble on the canyon's floor
# and its rims (not on the steep walls, where nothing would stay), clear of the buildings and stairs.
def kept(x, z, margin):
    for name, b in LAYOUT["buildings"].items():
        Bf = frame(name).inverted()
        p = Bf @ Vector((x, ground(x, z), z))
        areas = [(l["at"], l.get("size"), l.get("radius")) for l in b.get("ledges", [])]
        if "terrace" in b:
            areas.append((b["terrace"]["at"], b["terrace"]["size"], None))
        if "facade" in b:
            areas.append(((0.0, 1.0), (b["facade"][0] + 2.0, 4.0), None))
        if "span" in b:
            areas.append(((0.0, 0.0), (5.2, b["span"][0] * 2.0), None))
        for at, size, radius in areas:
            dx, dz = p.x - at[0], p.z - at[1]
            if radius is not None and math.hypot(dx, dz) < radius + margin + (5.0 if name == "Queen" else 0.0):
                return True
            if size is not None and abs(dx) < size[0] * 0.5 + margin and abs(dz) < size[1] * 0.5 + margin:
                return True
    for name, s in LAYOUT["stairs"].items():
        pts = [(p[0] - LAYOUT["origin"][0], p[2] - LAYOUT["origin"][1]) for p in s["points"]]
        for (ax, az), (bx, bz) in zip(pts, pts[1:]):
            vx, vz = bx - ax, bz - az
            t = max(0.0, min(1.0, ((x - ax) * vx + (z - az) * vz) / max(vx * vx + vz * vz, 1e-6)))
            if math.hypot(x - ax - vx * t, z - az - vz * t) < s["width"] * 0.5 + margin:
                return True
    return False


def lying(x, z, sink=0.2):
    """A frame on the floor at (x, z), its up along the floor's normal, turned at random."""
    n = ground_normal(x, z)
    q = Vector((0.0, 1.0, 0.0)).rotation_difference(n).to_matrix().to_4x4()
    return T(x, ground(x, z) - sink, z) @ q @ RY(RNG.uniform(0, math.tau))


def spot(tries=60, steep=0.55, margin=1.5, box_=(-26.0, 34.0, -24.0, 22.0)):
    for _ in range(tries):
        x, z = RNG.uniform(box_[0], box_[1]), RNG.uniform(box_[2], box_[3])
        n = ground_normal(x, z)
        if n.y < math.cos(steep) or kept(x, z, margin):
            continue
        # (nor on the lip of a riser: the floor within 2 m dropping away more than a metre)
        g = ground(x, z)
        if any(ground(x + dx, z + dz) < g - 1.0 for dx, dz in ((2.0, 0.0), (-2.0, 0.0), (0.0, 2.0), (0.0, -2.0), (1.4, 1.4), (-1.4, 1.4), (1.4, -1.4), (-1.4, -1.4))):
            continue
        return x, z
    return None


WAVE = []
for k in range(25):
    t = k / 24.0
    WAVE.append((-2.6 + 5.2 * t, 0.12 + 0.13 * math.sin(t * math.tau * 4.0) + 0.1 * max(0.0, math.sin(t * math.tau * 4.0 + 1.2)) ** 6))
WAVE += [(2.6, -0.16), (-2.6, -0.16)]
for i in range(4):
    at = spot(margin=3.0)
    if at is None:
        continue
    M = lying(*at, sink=0.35) @ RZ(RNG.uniform(-0.15, 0.15))
    piece(box(6.0, 1.9, 1.5), STONE, "Field", M)
    piece(box(6.3, 0.35, 1.7), STONE, "Field", M @ T(0.0, 1.9, 0.0))
    for k in range(4):
        piece(prism(spiral_outline(0.5), 0.14), RELIEF, "Field", M @ T(-2.1 + 1.4 * k, 1.35, 0.78) @ RZ(math.pi * (k % 2)), collide=False)
    piece(prism(WAVE, 0.08), GOLD, "RuinsGlow", M @ T(0.0, 0.55, 0.77), collide=False)
for i in range(10):
    at = spot()
    if at is None:
        continue
    r = RNG.uniform(0.45, 0.6)
    length = RNG.uniform(0.7, 1.15)
    M = lying(*at, sink=0.15) @ T(0.0, r, 0.0) @ RX(math.pi * 0.5) @ T(0.0, -length * 0.5, 0.0)
    piece(frustum(10, r, r, length, phase=RNG.uniform(0, 1)), RED, "Field", M)
for i in range(3):
    at = spot(margin=2.5)
    if at is not None:
        fallen_column(tuple(lying(*at, sink=0.0).translation), RNG.uniform(0, math.tau), "Field", (1.7, 1.6), capital=i == 0)
for i in range(3):
    at = spot()
    if at is not None:
        M = lying(*at, sink=-0.2) @ RX(RNG.uniform(-0.5, 0.5))
        piece(lathe([(0.0, -0.3), (0.52, -0.3), (0.74, -0.08), (0.72, 0.12), (0.56, 0.26), (0.0, 0.26)], 10), DARK, "Field", M)
        piece(box(1.5, 0.3, 1.5), STONE, "Field", M @ T(0.0, 0.24, 0.0))
for i in range(10):
    at = spot(margin=1.0)
    if at is None:
        continue
    if RNG.random() < 0.5:
        M = lying(*at, sink=0.45) @ RX(RNG.uniform(-0.3, 0.3))
    else:
        M = lying(*at, sink=-0.3) @ RX(math.pi * 0.5 + RNG.uniform(-0.2, 0.2)) @ T(0.0, -0.7, 0.0)
    amphora(M @ S(1.25), "Field")
for i in range(34):
    at = spot(steep=0.9, margin=0.8)
    if at is None:
        continue
    s = RNG.uniform(0.35, 1.0)
    piece(box(s * RNG.uniform(1.0, 1.8), s * RNG.uniform(0.4, 0.8), s * RNG.uniform(0.8, 1.4), top_jag=0.1), STONE, "Field",
          lying(*at, sink=0.15) @ RX(RNG.uniform(-0.3, 0.3)) @ RZ(RNG.uniform(-0.3, 0.3)), collide=s > 0.6)


# ============================================================================================
# Checks on every piece by itself: faces outward (a line out of each face leaves the piece's skin an
# even number of times; turned over if most of a piece's faces fail).
all_pieces = [obj for part in NAMES for obj in PARTS[part]]
bad_total = 0
for obj in all_pieces:
    wrong, counted = wrong_faces(obj)
    if counted and wrong * 2 > counted:
        obj.data.flip_normals()
        wrong, counted = wrong_faces(obj)
    if wrong:
        bad_total += wrong
        print("RUINS inside-out faces: %s %d of %d" % (obj.name, wrong, counted))
print("RUINS inside-out check: %d pieces, %d faces wrong" % (len(all_pieces), bad_total))


# --- Collision spheres, fitted to each solid piece as tools/build_ruins.py does, but against the
# canyon's floor instead of a flat sand: only the skin above the floor must be covered, and a sphere
# may be centred under the floor (under the piece) as big as reaches no part of that skin.
def b2g(co):
    return Vector((co.x, co.z, -co.y))


def fit_spheres_on_floor(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.normal_update()
    tree = BVHTree.FromBMesh(bm)
    under = {}
    for v in bm.verts:
        g = b2g(v.co)
        under[v.index] = g.y - ground(g.x, g.z)
    if max(under.values()) < 0.1:
        bm.free()
        return []
    above = bm.copy()
    gone = [f for f in above.faces if max(under[v.index] for v in f.verts) < -0.05]
    bmesh.ops.delete(above, geom=gone, context="FACES")
    above.normal_update()
    skin_tree = BVHTree.FromBMesh(above) if above.faces else None
    above.free()
    if skin_tree is None:
        bm.free()
        return []

    def inside(p):
        votes = 0
        for way in ((0.0, 0.0, 1.0), (0.577, 0.577, 0.577), (-0.6, 0.3, 0.742)):
            way = Vector(way)
            at = p.copy()
            hits = 0
            while hits < 40:
                hit = tree.ray_cast(at, way)
                if hit[0] is None:
                    break
                hits += 1
                at = hit[0] + way * 1e-4
            votes += hits % 2
        return votes >= 2
    skin = []
    for f in bm.faces:
        if max(under[v.index] for v in f.verts) < -0.05:
            continue
        a, b, c = (v.co for v in f.verts)
        count = max(1, int(f.calc_area() / 0.3))
        for k in range(count):
            u, v = RNG.random(), RNG.random()
            if u + v > 1.0:
                u, v = 1.0 - u, 1.0 - v
            p = a + (b - a) * u + (c - a) * v
            g = b2g(p)
            if g.y > ground(g.x, g.z) - 0.05:
                skin.append(p)
        if count == 1:
            skin.append((a + b + c) / 3.0)
    if not skin:
        bm.free()
        return []
    kd = KDTree(len(skin))
    for i, p in enumerate(skin):
        kd.insert(p, i)
    kd.balance()
    lo = Vector([min(v.co[i] for v in bm.verts) for i in range(3)])
    hi = Vector([max(v.co[i] for v in bm.verts) for i in range(3)])
    size = hi - lo
    step = max(0.12, min(0.5, min(size) / 3.0))
    found = []
    nx, ny, nz = (max(1, int(size[i] / step) + 1) for i in range(3))
    heights = [lo.z + (k + 0.5) * size.z / nz for k in range(nz)]
    for i in range(nx):
        for j in range(ny):
            bx, by = lo.x + (i + 0.5) * size.x / nx, lo.y + (j + 0.5) * size.y / ny
            g = ground(bx, -by)
            column_in = inside(Vector((bx, by, g + 0.05)))
            for zz in [h for h in heights if h >= g] + [g + d for d in DEEP]:
                p = Vector((bx, by, zz))
                if not (inside(p) if zz >= g else column_in):
                    continue
                hit = skin_tree.find_nearest(p)
                if hit[0] is None or hit[3] < RMIN:
                    continue
                r = min(hit[3] + PROUD, RMAX)
                if zz + r < g + 0.05:
                    continue
                found.append((p, r, {idx for _, idx, _ in kd.find_range(p, r + TOL)}))
    bm.free()
    left = set(range(len(skin)))
    chosen = []
    heap = [(-len(c[2]), i) for i, c in enumerate(found)]
    heapq.heapify(heap)
    while heap and len(left) > (1.0 - COVER) * len(skin):
        worth, i = heapq.heappop(heap)
        gain = found[i][2] & left
        if len(gain) < -worth:
            if gain:
                heapq.heappush(heap, (-len(gain), i))
            continue
        if len(gain) < 2:
            break
        chosen.append((found[i][0], found[i][1]))
        left -= gain
    return chosen


SPHERES = {}
for obj in SOLIDS:
    owner = next(name for name in NAMES if obj in PARTS[name])
    SPHERES.setdefault(owner, []).extend(fit_spheres_on_floor(obj))
print("RUINS spheres: %d: %s" % (sum(len(v) for v in SPHERES.values()), {k: len(v) for k, v in SPHERES.items()}))

# --- Joined into the parts; flat where edges are sharp, smooth across soft ones (the face).
parts = {}
for name in NAMES:
    objs = PARTS[name]
    if not objs:
        continue
    for obj in objs:
        obj.data.shade_smooth()
        obj.data.set_sharp_from_angle(angle=math.radians(obj["sharp"]))
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objs:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = name
    obj.data.name = name
    parts[name] = obj
meshes = list(parts.values())
triangles = {}
for obj in meshes:
    obj.data.calc_loop_triangles()
    triangles[obj.name] = len(obj.data.loop_triangles)
print("RUINS triangles %d: %s" % (sum(triangles.values()), ", ".join("%s %d" % kv for kv in triangles.items())))

# --- Clipping between the buildings: faces of one part crossing faces of another above the floor
# (under it nothing is seen). Reported by pair, with the worst place.
_graph = bpy.context.evaluated_depsgraph_get()
_trees = {obj.name: BVHTree.FromObject(obj, _graph) for obj in meshes if obj.name != "RuinsGlow"}
for i, a in enumerate(meshes):
    for b in meshes[i + 1:]:
        if a.name not in _trees or b.name not in _trees:
            continue
        seen = 0
        where = None
        for pa, pb in _trees[a.name].overlap(_trees[b.name]):
            c = b2g(a.data.polygons[pa].center)
            if c.y > ground(c.x, c.z) + 0.1:
                seen += 1
                where = c
        if seen:
            print("RUINS clip %s / %s: %d face pairs cross above the floor, e.g. at %s" % (a.name, b.name, seen, tuple(round(v, 1) for v in where)))
print("RUINS clip check done")


def empty(name, at_godot, radius=1.0, normal=None):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.empty_display_type = "SPHERE" if name.startswith("Rock") else "PLAIN_AXES"
    obj.location = to_b(at_godot)
    obj.scale = (radius, radius, radius)
    if normal is not None:
        obj.rotation_mode = "QUATERNION"
        obj.rotation_quaternion = Vector(to_b(normal)).to_track_quat("Z", "Y")
    return obj


for owner, made in SPHERES.items():
    for i, (p, r) in enumerate(made):
        obj = bpy.data.objects.new("Rock%s%04d" % (owner, i), None)
        bpy.context.collection.objects.link(obj)
        obj.empty_display_type = "SPHERE"
        obj.location = p
        obj.scale = (r, r, r)
for i, at in enumerate(LANTERNS):
    empty("Lantern%02d" % i, at)
for i, at in enumerate(FISH):
    empty("FishSpot%02d" % i, at)

# where sea life grows: points on the stone facing up, spread over the precinct
depsgraph = bpy.context.evaluated_depsgraph_get()
candidates = []
for i in range(2400):
    x, zz = RNG.uniform(-30.0, 38.0), RNG.uniform(-30.0, 26.0)
    hit, at, normal, _, obj, _ = bpy.context.scene.ray_cast(depsgraph, Vector(to_b((x, 60.0, zz))), Vector((0.0, 0.0, -1.0)))
    if hit and obj.name in parts and obj.name not in ("RuinsGlow", "Queen") and normal.z > 0.6:
        g = Vector((at.x, at.z, -at.y))
        if g.y > ground(g.x, g.z) + 0.4:
            candidates.append((g, Vector((normal.x, normal.z, -normal.y))))
reef = [candidates[0]]
while len(reef) < 56 and len(reef) < len(candidates):
    reef.append(max(candidates, key=lambda c: min((c[0] - r[0]).length for r in reef)))
for i, (at, normal) in enumerate(reef):
    empty("ReefSpot%02d" % i, at, 1.0, normal)
print("RUINS reef spots %d (of %d places found)" % (len(reef), len(candidates)))

# --- Unwrapped into two pictures, as tools/build_ruins.py does (her face one island round her head);
# faces buried in the floor or facing straight down get less of the stone's picture.
HEAD_INV = HEAD_AT.inverted()


def head_local(co):
    return HEAD_INV @ Vector((co.x, co.z, -co.y))


def on_face_skin(poly, mesh):
    middle = head_local(poly.center)
    n = HEAD_INV.to_3x3() @ Vector((poly.normal.x, poly.normal.z, -poly.normal.y))
    flat = Vector((middle.x, 0.0, middle.z))
    if flat.length < 1e-3 or n.dot(flat.normalized()) < 0.3 or middle.y > 6.9:
        return False
    a, f, b = shape_at(middle.y)
    phi = math.atan2(middle.x, middle.z)
    s, c = math.sin(phi), math.cos(phi)
    plain = math.hypot(a * abs(s) ** (2.0 / 2.2), (f if c > 0.0 else b) * abs(c) ** (2.0 / 2.2))
    return flat.length > 0.85 * plain


queen_mesh = parts["Queen"].data
queen_names = [m.name for m in queen_mesh.materials]
skin = {poly.index for poly in queen_mesh.polygons if queen_names[poly.material_index] == "face" and on_face_skin(poly, queen_mesh)}
bpy.ops.object.select_all(action="DESELECT")
for obj in meshes:
    obj.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.mode_set(mode="EDIT")
bpy.context.tool_settings.mesh_select_mode = (False, False, True)
bpy.ops.mesh.select_all(action="SELECT")
edit = bmesh.from_edit_mesh(queen_mesh)
edit.faces.ensure_lookup_table()
for i in skin:
    edit.faces[i].select_set(False)
bmesh.update_edit_mesh(queen_mesh)
bpy.ops.uv.smart_project(angle_limit=math.radians(70.0), island_margin=0.003)
bpy.ops.object.mode_set(mode="OBJECT")
uv = queen_mesh.uv_layers.active.data
GIRTH = 2.0 * math.pi * 2.75
for i in skin:
    poly = queen_mesh.polygons[i]
    us = []
    for li in poly.loop_indices:
        p = head_local(queen_mesh.vertices[queen_mesh.loops[li].vertex_index].co)
        us.append((li, math.atan2(p.x, p.z) / math.tau + 0.5, p.y))
    wrap = max(u for _, u, _ in us) - min(u for _, u, _ in us) > 0.5
    for li, u, y in us:
        if wrap and u < 0.5:
            u += 1.0
        uv[li].uv = (u * GIRTH, y)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.select_all(action="SELECT")
bpy.ops.uv.average_islands_scale()
bpy.ops.object.mode_set(mode="OBJECT")
print("RUINS face skin: %d faces in one island" % len(skin))
for obj in meshes:
    mesh = obj.data
    uv = mesh.uv_layers.active.data
    names = [m.name for m in mesh.materials]
    for poly in mesh.polygons:
        if names[poly.material_index] in BOOSTED:
            continue
        k = 1.0
        buried = max(b2g(mesh.vertices[v].co).y - ground(b2g(mesh.vertices[v].co).x, b2g(mesh.vertices[v].co).z) for v in poly.vertices)
        if buried < -0.25:
            k = 0.12
        elif poly.normal.z < -0.7:
            k = 0.4
        elif poly.area > 24.0:
            # (the terraces' and footings' long plain walls: the shader's grain carries them)
            k = 0.55
        if k != 1.0:
            for li in poly.loop_indices:
                uv[li].uv = uv[li].uv * k

pack(lambda name: name in BOOSTED)
pack(lambda name: name not in BOOSTED)
print("RUINS texel density: face %.1f px/m, column shafts %.1f px/m, masonry %.1f px/m, rock %.1f px/m, plain stone %.1f px/m"
      % (texel_density(parts["Queen"], {"face"}, STATUE_SIZE), texel_density(parts["Colonnade"], {"shaft"}, ATLAS_SIZE),
         texel_density(parts["Pyramid"], {"masonry"}, ATLAS_SIZE), texel_density(parts["Temple"], {"rock"}, ATLAS_SIZE), texel_density(parts["Gate"], {"stone"}, ATLAS_SIZE)))


# --- The bake: the sea's light (a sky overhead, a sun from straight above) over the canyon's own floor,
# so its walls shade what stands low between them.
def floor_mesh():
    cols, rows = GROUND["cols"], GROUND["rows"]
    verts = []
    for r in range(rows):
        for c in range(cols):
            x = GROUND["x0"] + c * GROUND["step"]
            z = GROUND["z0"] + r * GROUND["step"]
            verts.append(to_b((x, GROUND["heights"][r * cols + c] - 0.02, z)))
    faces = [(r * cols + c, (r + 1) * cols + c, (r + 1) * cols + c + 1, r * cols + c + 1) for r in range(rows - 1) for c in range(cols - 1)]
    mesh = bpy.data.meshes.new("floor")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("floor", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material("sand", (0.5, 0.48, 0.42)))
    return obj


def bake_canyon(meshes):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 64
    scene.cycles.device = "CPU"
    world = bpy.data.worlds.new("sea")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.9, 0.95, 1.0, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
    scene.world = world
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 1.4
    sun.angle = math.radians(20.0)
    lamp = bpy.data.objects.new("sun", sun)
    bpy.context.collection.objects.link(lamp)
    lamp.rotation_euler = (math.radians(12.0), math.radians(6.0), 0.0)
    lamps = []
    for at in LANTERNS:
        glow = bpy.data.lights.new("lamp", "POINT")
        glow.energy = 220.0
        glow.color = (0.75, 0.95, 1.0)
        glow.shadow_soft_size = 0.6
        lamps.append(bpy.data.objects.new("lamp", glow))
        bpy.context.collection.objects.link(lamps[-1])
        lamps[-1].location = to_b(at)
    ground_obj = floor_mesh()
    image = bpy.data.images.new(os.path.basename(ATLAS), ATLAS_SIZE, ATLAS_SIZE, alpha=False)
    statue = bpy.data.images.new(os.path.basename(STATUE_ATLAS), STATUE_SIZE, STATUE_SIZE, alpha=False)
    for made in bpy.data.materials:
        if not made.use_nodes:
            continue
        node = made.node_tree.nodes.new("ShaderNodeTexImage")
        node.image = statue if made.name in BOOSTED else image
        made.node_tree.nodes.active = node
    bake_settings = scene.render.bake
    bake_settings.margin = 8
    bake_settings.use_pass_glossy = False
    bake_settings.use_pass_transmission = False
    bpy.ops.object.select_all(action="DESELECT")
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.bake(type="COMBINED", use_clear=True)
    for picture, path in ((image, ATLAS), (statue, STATUE_ATLAS)):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        picture.filepath_raw = path
        picture.file_format = "PNG"
        picture.save()
        print("RUINS baked", path)
    bpy.data.objects.remove(ground_obj)
    bpy.data.objects.remove(lamp)
    for made in lamps:
        bpy.data.objects.remove(made)


if BAKE:
    bake_canyon(meshes)

# (each part's origin at its own building, so it can be picked and moved as one in the .blend)
for name, obj in parts.items():
    if name in LAYOUT["buildings"]:
        anchor = Vector(to_b(tuple(frame(name).translation)))
    elif name in LAYOUT["stairs"]:
        p = LAYOUT["stairs"][name]["points"][0]
        anchor = Vector(to_b((p[0] - LAYOUT["origin"][0], SURFACE - p[1] - ORIGIN_Y, p[2] - LAYOUT["origin"][1])))
    else:
        continue
    obj.data.transform(Matrix.Translation(-anchor))
    obj.location = anchor

os.makedirs(os.path.dirname(BLEND), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
bpy.ops.object.select_all(action="DESELECT")
for obj in bpy.data.objects:
    if obj.type in ("MESH", "EMPTY"):
        obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=GLB, export_format="GLB", export_apply=True, export_yup=True, use_selection=True, export_image_format="NONE")
print("RUINS wrote", GLB)
