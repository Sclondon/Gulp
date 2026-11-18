"""Builds the drowned precinct of Atlantis: a low-poly set piece with baked painted textures.

    blender --background --factory-startup --python tools/build_ruins.py [-- --no-bake] [--debug-spheres]

Writes models/atlantis_ruins.glb, textures/ruins_atlas.png (2048: the stone), textures/
ruins_atlas_statue.png (1024: her face, the statue and the reliefs) and tools/blend/atlantis_ruins.blend.
The design (plan, buildings, routes, palette, budget, quality passes) is tools/RUINS.md. The user
(2026-11-18): "another location should be atlanits ruins", then concept art made at their request
(tools/art_src/concept_atlantis.jpg), which the layout follows; the rest is Claude's design.

Everything here is laid out in GODOT's axes (x right, y up, z towards the visitor: the processional
way runs along +Z and a visitor swims in towards -Z), metres, the origin in the middle of the
precinct and y = 0 on the sea bed; `to_b` turns a point into Blender's axes as it is made, and the
glTF exporter turns it back.

Objects in the .glb (scripts/ruins.gd draws them):
  RuinsGate     the processional way and court paving, the gate's carved posts, lintel and frieze
  RuinsTemple   the round temple (platform, ring of columns, beam, broken dome, empty pedestal), the
                colossal hollow head and the hand, the crystal pillar
  RuinsStoa     the colonnade behind the temple: two rows of columns, a beam, fallen pieces
  RuinsPyramid  the stepped pyramid with its stair, doorway, chamber, shaft and high door
  RuinsField    carved frieze blocks, fallen drums, columns, capitals, amphorae, rubble
  RuinsGlow     what glows: the crystal, the orichalcum inlays (same shader, `glow` on)
  ReefSpot00..39  where sea life grows (their +Y: the surface's normal)
  FishSpot00..11, Lantern00..05
  Rock0000..    collision spheres (their scale is the radius), fitted to every solid piece

The low-poly helpers, the procedural paint and the bake follow tools/build_panel.py (its top part
is run from here for `material` and `unwrap`); the bake's light is the sea's: a sky overhead and a
sun from straight above, over a ground plane, so hollows and the foot of every wall come out dark.
"""
import heapq
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
source = open(os.path.join(HERE, "build_panel.py")).read()
exec(compile(source.split("# --- The helm housing")[0], "build_panel.py", "exec"))

from mathutils import Vector, Matrix  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402
from mathutils.kdtree import KDTree  # noqa: E402

GLB = os.path.join(HERE, "..", "models", "atlantis_ruins.glb")
BLEND = os.path.join(HERE, "blend", "atlantis_ruins.blend")
ATLAS = os.path.join(HERE, "..", "textures", "ruins_atlas.png")
ATLAS_SIZE = 2048
STATUE_ATLAS = os.path.join(HERE, "..", "textures", "ruins_atlas_statue.png")
STATUE_SIZE = 1024
BAKE = "--no-bake" not in sys.argv
RNG = random.Random(7)

# (the panel's own materials are not used here)
for made in list(bpy.data.materials):
    bpy.data.materials.remove(made)


# --- The paint: procedural materials for the bake. Every stone gets green-brown growth on what
# faces up and silt low down (both from where the face is in the world, so pieces that are joined
# share them).
def weathered(name, colour, patch_a, patch_b, size=1.6, growth=1.0, silt=1.0, blocks=None, rough=0.9):
    made = material(name, colour, patch_a, patch_b, size, rough)
    tree = made.node_tree
    shader = next(n for n in tree.nodes if n.type == "BSDF_PRINCIPLED")
    last = shader.inputs["Base Color"].links[0].from_node if shader.inputs["Base Color"].links else None
    place = tree.nodes.new("ShaderNodeTexCoord")
    split = tree.nodes.new("ShaderNodeSeparateXYZ")
    tree.links.new(place.outputs["Object"], split.inputs["Vector"])

    def mix_in(colour_out, fac_out, into):
        mix = tree.nodes.new("ShaderNodeMixRGB")
        if colour_out is None:
            mix.inputs["Color1"].default_value = (*colour, 1.0)
        else:
            tree.links.new(colour_out, mix.inputs["Color1"])
        mix.inputs["Color2"].default_value = (*into, 1.0)
        tree.links.new(fac_out, mix.inputs["Fac"])
        return mix

    current = last.outputs["Color"] if last else None
    if blocks:
        # cyclopean courses: dark joints between big blocks (rows by height, blocks along x + y)
        along = tree.nodes.new("ShaderNodeMath")
        along.operation = "ADD"
        tree.links.new(split.outputs["X"], along.inputs[0])
        tree.links.new(split.outputs["Y"], along.inputs[1])
        flat_xy = tree.nodes.new("ShaderNodeCombineXYZ")
        tree.links.new(along.outputs[0], flat_xy.inputs["X"])
        tree.links.new(split.outputs["Z"], flat_xy.inputs["Y"])
        brick = tree.nodes.new("ShaderNodeTexBrick")
        brick.inputs["Scale"].default_value = 1.0
        brick.inputs["Mortar Size"].default_value = 0.07
        brick.inputs["Mortar Smooth"].default_value = 0.4
        brick.inputs["Brick Width"].default_value = blocks[0]
        brick.inputs["Row Height"].default_value = blocks[1]
        brick.offset = 0.45
        brick.inputs["Color1"].default_value = (1.0, 1.0, 1.0, 1.0)
        brick.inputs["Color2"].default_value = (0.86, 0.86, 0.86, 1.0)
        brick.inputs["Mortar"].default_value = (0.3, 0.3, 0.3, 1.0)
        tree.links.new(flat_xy.outputs["Vector"], brick.inputs["Vector"])
        times = tree.nodes.new("ShaderNodeMixRGB")
        times.blend_type = "MULTIPLY"
        times.inputs["Fac"].default_value = 1.0
        if current is None:
            times.inputs["Color1"].default_value = (*colour, 1.0)
        else:
            tree.links.new(current, times.inputs["Color1"])
        tree.links.new(brick.outputs["Color"], times.inputs["Color2"])
        current = times.outputs["Color"]
    if growth > 0.0:
        geo = tree.nodes.new("ShaderNodeNewGeometry")
        up = tree.nodes.new("ShaderNodeSeparateXYZ")
        tree.links.new(geo.outputs["Normal"], up.inputs["Vector"])
        facing = tree.nodes.new("ShaderNodeMapRange")
        facing.inputs["From Min"].default_value = 0.45
        facing.inputs["From Max"].default_value = 0.9
        facing.inputs["To Max"].default_value = growth
        tree.links.new(up.outputs["Z"], facing.inputs["Value"])
        noise = tree.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 0.9
        noise.inputs["Detail"].default_value = 3.0
        tree.links.new(place.outputs["Object"], noise.inputs["Vector"])
        patchy = tree.nodes.new("ShaderNodeMapRange")
        patchy.inputs["From Min"].default_value = 0.35
        patchy.inputs["From Max"].default_value = 0.6
        tree.links.new(noise.outputs["Fac"], patchy.inputs["Value"])
        both = tree.nodes.new("ShaderNodeMath")
        both.operation = "MULTIPLY"
        tree.links.new(facing.outputs["Result"], both.inputs[0])
        tree.links.new(patchy.outputs["Result"], both.inputs[1])
        current = mix_in(current, both.outputs[0], (0.2, 0.27, 0.13)).outputs["Color"]
    if silt > 0.0:
        low = tree.nodes.new("ShaderNodeMapRange")
        low.inputs["From Min"].default_value = 1.1
        low.inputs["From Max"].default_value = 0.0
        low.inputs["To Max"].default_value = 0.75 * silt
        tree.links.new(split.outputs["Z"], low.inputs["Value"])
        current = mix_in(current, low.outputs["Result"], (0.2, 0.19, 0.16)).outputs["Color"]
    if current is not None:
        tree.links.new(current, shader.inputs["Base Color"])
    return made


# (the concept art's palette: grey-green stone streaked darker green, pale creamy marble for the
# statue, verdigris and copper inlays)
STONE = weathered("stone", (0.5, 0.53, 0.48), (0.38, 0.44, 0.37), (0.33, 0.36, 0.33), 1.8)
MASONRY = weathered("masonry", (0.47, 0.5, 0.45), (0.36, 0.42, 0.35), (0.31, 0.34, 0.31), 2.0, blocks=(1.6, 0.85))
STATUE = weathered("statue", (0.78, 0.76, 0.68), (0.68, 0.68, 0.6), (0.6, 0.62, 0.56), 1.2, growth=0.3)
FACE = weathered("face", (0.78, 0.76, 0.68), (0.68, 0.68, 0.6), (0.6, 0.62, 0.56), 1.2, growth=0.3)
RELIEF = weathered("relief", (0.58, 0.6, 0.54), (0.46, 0.5, 0.43), (0.4, 0.44, 0.38), 0.9, growth=0.4)
RED = weathered("shaft", (0.55, 0.57, 0.52), (0.4, 0.46, 0.39), (0.34, 0.38, 0.34), 1.0, growth=0.7)
DARK = weathered("capital", (0.06, 0.07, 0.1), (0.11, 0.13, 0.14), (0.08, 0.1, 0.1), 0.8, growth=0.7)
FRESCO = weathered("fresco", (0.1, 0.22, 0.38), (0.16, 0.27, 0.38), (0.08, 0.16, 0.26), 1.0, growth=0.2)
BRONZE = weathered("bronze", (0.15, 0.4, 0.32), (0.07, 0.19, 0.15), (0.3, 0.5, 0.4), 0.7, growth=0.3, silt=0.5, rough=0.6)
CLAY = weathered("clay", (0.48, 0.24, 0.13), (0.36, 0.2, 0.13), (0.42, 0.3, 0.2), 0.6, growth=0.6)
GOLD = weathered("orichalcum", (0.8, 0.36, 0.1), (0.2, 0.42, 0.32), (0.62, 0.26, 0.08), 0.5, growth=0.0, silt=0.3, rough=0.5)
CRYSTAL = material("crystal", (0.62, 0.95, 1.0))
_glass = next(n for n in CRYSTAL.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
_glass.inputs["Emission Color"].default_value = (0.55, 0.95, 1.0, 1.0)
_glass.inputs["Emission Strength"].default_value = 1.5
# (what the statue and the reliefs are painted with: they have a picture of their own)
BOOSTED = {"statue", "relief", "face"}

NAMES = ("RuinsGate", "RuinsTemple", "RuinsStoa", "RuinsPyramid", "RuinsField", "RuinsGlow")
PARTS = {name: [] for name in NAMES}
SOLIDS = []   # pieces that stop a swimmer (they get spheres)


# --- Points and turns in Godot's axes.
def to_b(p):
    return (p[0], -p[2], p[1])


def T(x, y, z):
    return Matrix.Translation(Vector((x, y, z)))


def RX(a):
    return Matrix.Rotation(a, 4, "X")


def RY(a):
    return Matrix.Rotation(a, 4, "Y")


def RZ(a):
    return Matrix.Rotation(a, 4, "Z")


def S(x, y=None, z=None):
    return Matrix.Diagonal((x, y if y is not None else x, z if z is not None else x, 1.0))


def piece(made, mat, part, M=Matrix(), collide=True, sharp=40.0):
    """A closed piece from (verts, faces) in its own space, put in place by M; its faces are
    turned outwards here (and checked later)."""
    verts, faces = made
    bm = bmesh.new()
    vs = [bm.verts.new(to_b(M @ Vector(p))) for p in verts]
    for f in faces:
        try:
            bm.faces.new([vs[i] for i in f])
        except ValueError:
            pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(part)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(part, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    obj["sharp"] = sharp
    PARTS[part].append(obj)
    if collide:
        SOLIDS.append(obj)
    return obj


# --- Shapes, each (verts, faces), closed.
def lathe(profile, sides, phase=0.0):
    """Turned about Y: `profile` (r, y) from bottom to top; r = 0 at an end makes a point there,
    otherwise that end is capped flat."""
    verts, faces, rings = [], [], []
    for r, y in profile:
        if r < 1e-6:
            rings.append([len(verts)])
            verts.append((0.0, y, 0.0))
        else:
            ring = []
            for k in range(sides):
                a = phase + math.tau * k / sides
                ring.append(len(verts))
                verts.append((r * math.sin(a), y, r * math.cos(a)))
            rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        if len(a) == 1:
            faces += [(a[0], b[(k + 1) % sides], b[k]) for k in range(sides)]
        elif len(b) == 1:
            faces += [(a[k], a[(k + 1) % sides], b[0]) for k in range(sides)]
        else:
            faces += [(a[k], a[(k + 1) % sides], b[(k + 1) % sides], b[k]) for k in range(sides)]
    if len(rings[0]) > 1:
        faces.append(tuple(reversed(rings[0])))
    if len(rings[-1]) > 1:
        faces.append(tuple(rings[-1]))
    return verts, faces


def revolve(outline, sides, phase=0.0, sweep=None):
    """A closed outline (r, y) turned about Y into a ring (a wall, a dome's shell, a band); with
    `sweep` (from, to, radians) only that much of it, capped at both ends."""
    verts, faces = [], []
    n = len(outline)
    steps = sides if sweep is None else sides + 1
    for k in range(steps):
        a = phase + (math.tau * k / sides if sweep is None else sweep[0] + (sweep[1] - sweep[0]) * k / sides)
        for r, y in outline:
            verts.append((r * math.sin(a), y, r * math.cos(a)))
    for k in range(sides):
        k2 = (k + 1) % steps if sweep is None else k + 1
        for i in range(n):
            i2 = (i + 1) % n
            faces.append((k * n + i, k * n + i2, k2 * n + i2, k2 * n + i))
    if sweep is not None:
        faces.append(tuple(range(n)))
        faces.append(tuple((steps - 1) * n + i for i in reversed(range(n))))
    return verts, faces


def frustum(sides, r0, r1, h, jag=0.0, phase=0.0, low_jag=0.0):
    """A column drum or shaft along +Y from 0 to h (r0 at the foot, r1 at the top). `jag` breaks
    its top (a broken column), `low_jag` its foot (a piece broken off something)."""
    verts, faces = [], []
    for k in range(sides):
        a = phase + math.tau * k / sides
        verts.append((r0 * math.sin(a), RNG.uniform(-low_jag, low_jag), r0 * math.cos(a)))
    for k in range(sides):
        a = phase + math.tau * k / sides
        verts.append((r1 * math.sin(a), h + RNG.uniform(-jag, jag * 0.4), r1 * math.cos(a)))
    faces += [(k, (k + 1) % sides, sides + (k + 1) % sides, sides + k) for k in range(sides)]
    if jag > 0.0:
        verts.append((RNG.uniform(-0.2, 0.2) * r1, h + RNG.uniform(-jag, jag * 0.3), RNG.uniform(-0.2, 0.2) * r1))
        top = len(verts) - 1
        faces += [(sides + k, sides + (k + 1) % sides, top) for k in range(sides)]
    else:
        faces.append(tuple(sides + k for k in range(sides)))
    if low_jag > 0.0:
        verts.append((0.0, RNG.uniform(-low_jag, low_jag), 0.0))
        bottom = len(verts) - 1
        faces += [((k + 1) % sides, k, bottom) for k in range(sides)]
    else:
        faces.append(tuple(reversed(range(sides))))
    return verts, faces


def box(sx, sy, sz, top_jag=0.0, taper=0.0):
    """A box centred on x and z, from y = 0 to sy; `taper` draws its top in (a battered tower),
    `top_jag` breaks its top corners to different heights."""
    hx, hz = sx * 0.5, sz * 0.5
    tx, tz = hx - taper, hz - taper
    verts = [(-hx, 0.0, -hz), (hx, 0.0, -hz), (hx, 0.0, hz), (-hx, 0.0, hz)]
    verts += [(x, sy + RNG.uniform(-top_jag, top_jag * 0.3), z) for x, z in ((-tx, -tz), (tx, -tz), (tx, tz), (-tx, tz))]
    faces = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    if top_jag > 0.0:
        # (a broken top: a peak or a dip off the middle)
        verts.append((RNG.uniform(-0.3, 0.3) * tx, sy + RNG.uniform(-top_jag, top_jag), RNG.uniform(-0.3, 0.3) * tz))
        faces[1:2] = [(4, 5, 8), (5, 6, 8), (6, 7, 8), (7, 4, 8)]
    return verts, faces


def prism(outline, depth):
    """A flat outline (x, y) given depth along Z, from -depth/2 to +depth/2."""
    n = len(outline)
    verts = [(x, y, -depth * 0.5) for x, y in outline] + [(x, y, depth * 0.5) for x, y in outline]
    faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    faces += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    return verts, faces


def torus(major, minor, sides=10, around=4):
    verts, faces = [], []
    for i in range(sides):
        a = math.tau * i / sides
        for j in range(around):
            b = math.tau * j / around + math.pi / around
            r = major + minor * math.cos(b)
            verts.append((r * math.sin(a), minor * math.sin(b), r * math.cos(a)))
    for i in range(sides):
        for j in range(around):
            i2 = (i + 1) % sides
            j2 = (j + 1) % around
            faces.append((i * around + j, i2 * around + j, i2 * around + j2, i * around + j2))
    return verts, faces


def loft(sections):
    """Closed sections (each the same count of points in space) joined one to the next, the ends
    capped: a hull."""
    n = len(sections[0])
    verts = [p for s in sections for p in s]
    faces = [tuple(reversed(range(n))), tuple(range((len(sections) - 1) * n, len(sections) * n))]
    for k in range(len(sections) - 1):
        faces += [(k * n + i, k * n + (i + 1) % n, (k + 1) * n + (i + 1) % n, (k + 1) * n + i) for i in range(n)]
    return verts, faces


def cut(obj, made, M=Matrix()):
    """Takes a shape away from a piece (a doorway, a chamber, a hole in a dome)."""
    cutter = piece(made, STONE, "RuinsField", M, collide=False)
    PARTS["RuinsField"].remove(cutter)
    mod = obj.modifiers.new("cut", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cutter
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter)


# --- Architecture.
def column(M, part, shaft=4.6, broken=0.0, inlay=False, sides=10):
    """A column in the island's manner: a red shaft that narrows DOWNWARDS (0.38 m at the foot,
    0.5 at the top), a dark cushion capital, a square abacus, on a round base. `broken`: broken
    off that high (no capital). Returns the height of its top."""
    piece(lathe([(0.0, -0.5), (0.58, -0.5), (0.58, 0.12), (0.5, 0.25), (0.0, 0.25)], sides), STONE, part, M)
    if broken > 0.0:
        piece(frustum(sides, 0.38, 0.38 + 0.12 * broken / shaft, broken, jag=0.35), RED, part, M @ T(0.0, 0.2, 0.0))
        return broken
    piece(frustum(sides, 0.38, 0.5, shaft), RED, part, M @ T(0.0, 0.2, 0.0))
    top = 0.2 + shaft
    piece(lathe([(0.0, top - 0.05), (0.52, top - 0.05), (0.74, top + 0.18), (0.72, top + 0.38), (0.56, top + 0.52), (0.0, top + 0.52)], sides), DARK, part, M)
    piece(box(1.5, 0.3, 1.5), STONE, part, M @ T(0.0, top + 0.5, 0.0))
    if inlay:
        piece(revolve([(0.47, top - 0.45), (0.53, top - 0.45), (0.53, top - 0.25), (0.47, top - 0.25)], sides), GOLD, "RuinsGlow", M, collide=False)
    return top + 0.8


def fallen_column(at, turn, part, lengths=(1.6, 1.5, 1.4), gaps=(0.25, 0.4), tilt=0.06, sink=0.1, capital=True):
    """A column lying where it fell: its drums apart, a little rolled, sunk into the sand."""
    along = 0.0
    for k, length in enumerate(lengths):
        r = 0.4 + 0.1 * along / 4.6
        M = T(*at) @ RY(turn) @ T(0.0, r - sink, along) @ RX(math.pi * 0.5) @ RZ(RNG.uniform(-0.3, 0.3)) @ RX(RNG.uniform(-tilt, tilt))
        piece(frustum(10, r, r + 0.1 * length / 4.6, length, jag=0.12 if k == len(lengths) - 1 and not capital else 0.0, low_jag=0.1 if k else 0.0), RED, part, M)
        along += length + (gaps[k] if k < len(gaps) else 0.3)
    if capital:
        M = T(*at) @ RY(turn) @ T(0.15, 0.62 - sink, along + 0.35) @ RX(math.pi * 0.5 + 0.15)
        piece(lathe([(0.0, -0.3), (0.52, -0.3), (0.74, -0.08), (0.72, 0.12), (0.56, 0.26), (0.0, 0.26)], 10), DARK, part, M)


def horns(M, part, size=1.0):
    """Horns of consecration: the island's sign of a holy place."""
    s = size
    outline = [(-1.2 * s, 0.0), (1.2 * s, 0.0), (1.2 * s, 0.45 * s), (1.05 * s, 0.9 * s), (1.0 * s, 1.75 * s), (0.72 * s, 0.95 * s),
               (0.5 * s, 0.55 * s), (-0.5 * s, 0.55 * s), (-0.72 * s, 0.95 * s), (-1.0 * s, 1.75 * s), (-1.05 * s, 0.9 * s), (-1.2 * s, 0.45 * s)]
    piece(prism(outline, 0.6 * s), STONE, part, M)


def fish_outline(length, mirror=False):
    """A leaping fish in profile (the relief's), nose to +x, tail forked."""
    pts = [(0.5, 0.0), (0.42, 0.1), (0.25, 0.17), (0.0, 0.18), (-0.22, 0.12), (-0.36, 0.05), (-0.5, 0.17), (-0.47, 0.0),
           (-0.5, -0.17), (-0.36, -0.05), (-0.22, -0.1), (0.0, -0.15), (0.12, -0.2), (0.15, -0.13), (0.3, -0.12), (0.42, -0.08)]
    pts = [(x * length, y * length) for x, y in pts]
    if mirror:
        pts = [(-x, y) for x, y in reversed(pts)]
    return pts


def spiral_outline(r, turns=1.5, steps=13, band=0.3):
    """A spiral as a flat band (the island's running spiral), its middle at the origin."""
    outer, inner = [], []
    for k in range(steps + 1):
        t = k / steps
        a = math.tau * turns * t
        rad = r * (0.22 + 0.78 * t)
        w = band * r * (0.45 + 0.55 * t)
        outer.append((math.cos(a) * (rad + w * 0.5), math.sin(a) * (rad + w * 0.5)))
        inner.append((math.cos(a) * (rad - w * 0.5), math.sin(a) * (rad - w * 0.5)))
    return outer + inner[::-1]


def amphora(M, part):
    piece(lathe([(0.0, 0.0), (0.12, 0.04), (0.3, 0.3), (0.36, 0.72), (0.27, 1.03), (0.11, 1.18), (0.1, 1.38), (0.16, 1.44), (0.0, 1.46)], 8), CLAY, part, M)


# ============================================================================================
# The layout follows the concept art (tools/art_src/concept_atlantis.jpg, seen from the way in, +Z):
# the gate at the left front, the round temple in the middle with the fallen head and hand on the
# paving before it, the colonnade behind, the stepped pyramid to the right, the crystal pillar at
# the right front, carved spiral-and-wave blocks, drums and amphorae strewn in the foreground.
GATE_X, GATE_Z = -18.0, 14.0
TX, TZ = -2.0, -6.0           # the temple's middle
PX, PZ = 26.0, -6.0           # the pyramid's middle
PILLAR_AT = (38.0, 6.0)

# --- The processional way (z 18 to 36 at the gate's x): broken paving, column stumps, a toppled
# column either side.
z = 18.4
while z < 36.0:
    for x in (-1.95, 0.0, 1.95):
        if RNG.random() < 0.17:
            continue
        M = T(GATE_X + x + RNG.uniform(-0.12, 0.12), RNG.uniform(-0.28, -0.16), z + RNG.uniform(-0.1, 0.1)) @ RY(RNG.uniform(-0.08, 0.08)) @ RX(RNG.uniform(-0.05, 0.05)) @ RZ(RNG.uniform(-0.05, 0.05))
        piece(box(1.85, 0.42, 1.6), STONE, "RuinsGate", M, collide=False)
    z += 1.72
for side, heights in ((-1.0, (2.3, 0.9, 3.3)), (1.0, (1.3, 3.0, 0.6))):
    for z, h in zip((22.0, 28.0, 34.0), heights):
        column(T(GATE_X + side * 4.6, -0.1, z) @ RY(RNG.uniform(0, 1)), "RuinsGate", broken=h)
fallen_column((GATE_X - 6.6, 0.0, 25.5), -0.25, "RuinsGate", (1.6, 1.6, 1.4))
fallen_column((GATE_X + 6.4, 0.0, 30.0), math.pi + 0.35, "RuinsGate", (1.5, 1.7), capital=True)
# paving in the court, from the gate to the temple and round the head (big slabs, many gone)
for i in range(46):
    x, zz = RNG.uniform(-20.0, 12.0), RNG.uniform(-1.0, 13.0)
    if math.hypot(x - TX, zz - TZ) < 11.0:
        continue
    M = T(x, RNG.uniform(-0.3, -0.18), zz) @ RY(RNG.uniform(-0.3, 0.3)) @ RX(RNG.uniform(-0.05, 0.05)) @ RZ(RNG.uniform(-0.05, 0.05))
    piece(box(RNG.uniform(1.6, 2.6), 0.42, RNG.uniform(1.4, 2.2)), STONE, "RuinsGate", M, collide=False)

# --- The gate: two carved posts with inlaid spiral panels, a heavy lintel with a running-spiral
# frieze and a cornice; an opening 5 m wide and 8.5 m high.
GATE = T(GATE_X, 0.0, GATE_Z)
for side in (-1.0, 1.0):
    post = GATE @ T(side * 3.4, 0.0, 0.0)
    piece(box(2.6, 1.0, 2.6, taper=0.1), STONE, "RuinsGate", post @ T(0.0, -0.6, 0.0))
    piece(box(1.8, 8.3, 1.8), STONE, "RuinsGate", post @ T(0.0, 0.2, 0.0) @ RZ(side * 0.004))
    for face in (1.0, -1.0):
        # the panel: verdigris bronze let into the post's face, three copper spirals on it
        panel = post @ RY(0.0 if face > 0 else math.pi) @ T(0.0, 1.3, 0.9)
        piece(box(1.1, 6.2, 0.08), BRONZE, "RuinsGate", panel, collide=False)
        for k in range(3):
            piece(prism(spiral_outline(0.42), 0.08), GOLD, "RuinsGlow", panel @ T(0.0, 1.1 + 2.0 * k, 0.07) @ RZ(math.pi * (k % 2)), collide=False)
LINTEL = GATE @ T(0.0, 8.5, 0.0) @ RZ(-0.018)
piece(box(9.6, 1.5, 2.2), STONE, "RuinsGate", LINTEL)
piece(box(10.4, 0.5, 2.7), STONE, "RuinsGate", LINTEL @ T(0.0, 1.5, 0.0))
for face in (1.0, -1.0):
    for k in range(5):
        x = -3.6 + 1.8 * k
        piece(prism(spiral_outline(0.55), 0.16), RELIEF, "RuinsGate", LINTEL @ RY(0.0 if face > 0 else math.pi) @ T(x, 0.75, 1.12) @ RZ(math.pi * (k % 2)), collide=False)
# a corner of the cornice, fallen
piece(box(1.8, 0.5, 2.7), STONE, "RuinsGate", GATE @ T(6.4, 0.05, 2.4) @ RY(0.7) @ RX(0.25) @ RZ(0.3))

# --- The temple: a stepped round platform, a ring of twelve columns carrying a round beam, and a
# dome on it broken open at the front: light falls in. One column of the ring broken, one fallen.
TEMPLE = T(TX, 0.0, TZ) @ RZ(0.015) @ RX(-0.01)
piece(lathe([(0.0, -1.2), (10.6, -1.2), (10.6, 0.4), (10.0, 0.4), (10.0, 0.8), (9.4, 0.8), (9.4, 1.2), (0.0, 1.2)], 24), STONE, "RuinsTemple", TEMPLE)
RING_R = 7.4
SHAFT = 7.0
for k in range(12):
    a = math.tau * (k + 0.5) / 12.0
    M = TEMPLE @ RY(a) @ T(0.0, 1.0, RING_R) @ RY(RNG.uniform(0, 1))
    if k == 5:
        column(M, "RuinsTemple", shaft=SHAFT, broken=2.4)
    else:
        column(M, "RuinsTemple", shaft=SHAFT, inlay=True)
# (column top: 1.0 + 0.2 + SHAFT + 0.52 capital + 0.3 abacus)
BEAM_Y = 1.0 + 0.2 + SHAFT + 0.82
piece(revolve([(6.5, BEAM_Y), (8.3, BEAM_Y), (8.3, BEAM_Y + 1.2), (6.5, BEAM_Y + 1.2)], 24, math.pi / 24.0), STONE, "RuinsTemple", TEMPLE)
piece(revolve([(6.7, BEAM_Y + 1.2), (8.7, BEAM_Y + 1.2), (8.7, BEAM_Y + 1.65), (6.7, BEAM_Y + 1.65)], 24, math.pi / 24.0), STONE, "RuinsTemple", TEMPLE)
for k in range(12):
    a = math.tau * k / 12.0
    piece(prism(spiral_outline(0.42), 0.12), RELIEF, "RuinsTemple", TEMPLE @ RY(a) @ T(0.0, BEAM_Y + 0.6, 8.32), collide=False)
D0 = BEAM_Y + 1.65
dome = piece(revolve([(8.2, D0), (7.9, D0 + 1.4), (7.0, D0 + 2.9), (5.4, D0 + 4.1), (3.0, D0 + 4.9), (0.9, D0 + 5.2), (0.6, D0 + 4.4), (2.6, D0 + 4.15),
                      (4.8, D0 + 3.45), (6.2, D0 + 2.35), (7.0, D0 + 1.1), (7.1, D0)], 24, math.pi / 24.0), MASONRY, "RuinsTemple", TEMPLE)
cut(dome, lathe([(0.0, -3.6), (2.6, -2.6), (3.6, 0.0), (2.6, 2.6), (0.0, 3.6)], 10), TEMPLE @ T(2.4, D0 + 4.0, 4.6) @ S(1.25, 1.0, 1.0))
# the pedestal she stood on, empty but for her broken feet (off the middle, clear of the way up)
piece(box(3.2, 1.5, 2.6, taper=0.08), MASONRY, "RuinsTemple", TEMPLE @ T(-3.0, 1.0, -2.2) @ RY(0.3))
piece(box(3.6, 0.3, 3.0), STONE, "RuinsTemple", TEMPLE @ T(-3.0, 2.45, -2.2) @ RY(0.3))
for side in (-1.0, 1.0):
    piece(frustum(7, 0.42, 0.38, 1.0, jag=0.3), FACE, "RuinsTemple", TEMPLE @ T(-3.0, 2.7, -2.2) @ RY(0.3) @ T(side * 0.7, 0.0, 0.1) @ S(1.0, 1.0, 1.6), sharp=70.0)
# the fallen column and stones of the dome, inside and beside
a = math.tau * 9.5 / 12.0
at = TEMPLE @ Vector((math.sin(a) * 10.6, 0.0, math.cos(a) * 10.6))
fallen_column((at.x, 0.0, at.z), a + 0.3, "RuinsField", (1.8, 1.7, 1.6), capital=True)
for x, zz, s in ((1.2, -2.8, 1.0), (-2.0, -3.4, 0.8), (3.2, 0.4, 0.7), (6.0, 8.2, 1.0), (9.5, 5.0, 0.8)):
    lift = 1.1 if math.hypot(x, zz) < 9.4 else 0.0
    M = TEMPLE @ T(x, RNG.uniform(-0.4, -0.2) + lift, zz) @ RY(RNG.uniform(0, 3)) @ RX(RNG.uniform(-0.4, 0.4)) @ RZ(RNG.uniform(-0.4, 0.4))
    piece(box(1.5 * s, 0.9 * s, 1.1 * s), MASONRY, "RuinsTemple", M)


# --- The colossal head: a sea queen in the archaic manner, built round her own axis (y up through
# her crown, her face to +z, chin at y = 0), as a grid of rows round her with the features pushed
# out of it, so that the face gets most of the points.
HEAD_ROWS = [-1.25, -0.9, -0.45, 0.0, 0.35, 0.7, 1.0, 1.3, 1.55, 1.75, 1.9, 2.02, 2.12, 2.22, 2.34, 2.48, 2.64, 2.8, 2.95, 3.1, 3.27,
             3.45, 3.62, 3.74, 3.86, 3.98, 4.1, 4.24, 4.4, 4.56, 4.7, 4.84, 5.0, 5.2, 5.42, 5.64, 5.86, 6.12, 6.4, 6.7]
HEAD_TOP = 7.05
HEAD_COLS = 52
# its shape, row by row: (y, half width, depth in front, depth behind)
HEAD_SHAPE = [(-1.25, 1.95, 1.55, 2.0), (0.0, 2.15, 1.95, 2.35), (1.0, 2.5, 2.25, 2.65), (2.5, 2.75, 2.42, 2.9), (3.8, 2.85, 2.4, 3.0),
              (4.8, 2.8, 2.36, 3.0), (5.8, 2.52, 2.05, 2.78), (6.6, 1.8, 1.4, 2.0), (7.05, 0.0, 0.0, 0.0)]


def smooth(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3.0 - 2.0 * t)


def shape_at(y):
    for a, b in zip(HEAD_SHAPE, HEAD_SHAPE[1:]):
        if y <= b[0]:
            t = smooth(a[0], b[0], y)
            return [a[i] + (b[i] - a[i]) * t for i in (1, 2, 3)]
    return HEAD_SHAPE[-1][1:]


def features(x, y):
    """How far the face stands out (+) or in (-) from the plain head, at x across it and y up it."""
    ax = abs(x)
    out = 0.0
    # the nose: a straight ridge from the brow to a broad tip, with its wings
    if 2.5 < y < 4.85:
        t = max(0.0, min(1.0, (y - 2.92) / (4.65 - 2.92)))
        h = (0.95 * (1.0 - t) + 0.22 * t) * smooth(2.55, 2.92, y)
        w = 0.5 * (1.0 - t) + 0.27 * t
        out += h * math.exp(-1.6 * (x / w) ** 2)
        out += 0.22 * math.exp(-((ax - 0.48) / 0.17) ** 2 - ((y - 2.97) / 0.19) ** 2)
    # the brow, a sharp arch over each eye
    arch = 4.72 + 0.14 * max(0.0, 1.0 - ((ax - 1.15) / 1.15) ** 2)
    out += 0.3 * math.exp(-((y - arch) / 0.2) ** 2) * (1.0 - smooth(1.9, 2.6, ax))
    # the sockets, and in each a deep almond hollow: the mask's empty eyes (the concept art's)
    ex, ey = ax - 1.15, y - 3.95
    out -= 0.22 * math.exp(-(ex / 0.85) ** 2 - (ey / 0.5) ** 2)
    k = max(0.0, 1.0 - (ex / 0.72) ** 2)
    if k > 0.0:
        out -= 0.55 * math.exp(-(ey / (0.3 * k ** 0.6 + 1e-3)) ** 2) * k ** 0.4
    # cheekbones and chin
    out += 0.16 * math.exp(-((ax - 1.85) / 0.6) ** 2 - ((y - 3.25) / 0.5) ** 2)
    out += 0.3 * math.exp(-(x / 0.85) ** 2 - ((y - 0.85) / 0.45) ** 2)
    # the lips, in the archaic smile (their corners up), a little parted
    line = 2.15 + 0.17 * (x / 0.95) ** 2
    lip = 1.0 - smooth(0.78, 1.15, ax)
    out += lip * (0.36 * math.exp(-((y - (line + 0.21)) / 0.16) ** 2) + 0.32 * math.exp(-((y - (line - 0.27)) / 0.19) ** 2)
                  - 0.2 * math.exp(-((y - line) / 0.07) ** 2))
    # the hair under the crown: a roll of waves across the forehead
    band = smooth(5.2, 5.45, y) * (1.0 - smooth(6.0, 6.3, y))
    out += band * 0.2 * (0.5 + 0.5 * math.cos(x * math.tau / 0.95))
    return out


def head(plain=False):
    """The head as a closed grid; `plain`: only its shape, coarse, no face (for hollowing it)."""
    verts, faces = [], []
    rows = HEAD_ROWS if not plain else HEAD_ROWS[::4] + [HEAD_ROWS[-1]]
    cols = HEAD_COLS if not plain else 20
    for row, y in enumerate(rows):
        a, f, b = shape_at(y)
        for k in range(cols):
            u = -1.0 + 2.0 * k / cols
            phi = math.pi * (0.42 * u + 0.58 * u ** 3) if not plain else math.pi * u
            s, c = math.sin(phi), math.cos(phi)
            n = 2.2
            x = a * math.copysign(abs(s) ** (2.0 / n), s)
            zz = (f if c > 0.0 else b) * math.copysign(abs(c) ** (2.0 / n), c)
            if c > 0.0 and not plain:
                zz += features(x, y) * c ** 0.6
            if not plain:
                # curls over the crown: rolls running back from the brow, all round
                curl = 0.24 * (0.5 + 0.5 * math.cos(phi * 14.0)) * smooth(5.25, 5.7, y) * (1.0 - smooth(6.55, 7.0, y))
                flat = math.hypot(x, zz)
                if flat > 1e-3:
                    x += x / flat * curl
                    zz += zz / flat * curl
            jag = RNG.uniform(-0.22, 0.22) if row == 0 and not plain else 0.0
            verts.append((x, y + jag, zz))
    for row in range(len(rows) - 1):
        for k in range(cols):
            k2 = (k + 1) % cols
            faces.append((row * cols + k, row * cols + k2, (row + 1) * cols + k2, (row + 1) * cols + k))
    verts.append((0.0, HEAD_TOP, -0.15))
    top = len(verts) - 1
    last = (len(rows) - 1) * cols
    faces += [(last + k, last + (k + 1) % cols, top) for k in range(cols)]
    # the break at the neck: rough, a little hollow
    verts.append((0.1, -0.95, 0.2))
    bottom = len(verts) - 1
    faces += [((k + 1) % cols, k, bottom) for k in range(cols)]
    return verts, faces



# She lies on the paving before the temple, on the back of her head, her face up and turned a little
# towards the way in, sunk in the sand to her ears. She is hollow (cast in a shell 0.6 m thick):
# broken through at both temples, so a fish swims in at one side and out at the other, and her
# parted lips open into the hollow for small fish.
HEAD_AT = T(5.2, 0.0, 9.8) @ RY(0.25) @ RX(1.0 - math.pi * 0.5)
face = piece(head(), FACE, "RuinsTemple", HEAD_AT, sharp=80.0)
inner_v, inner_f = head(plain=True)
inner_v = [(x * 0.78, (y - 3.0) * 0.8 + 3.0, z * 0.8 - 0.1) for x, y, z in inner_v]
cut(face, (inner_v, inner_f), HEAD_AT)
cut(face, lathe([(0.0, -1.2), (0.55, -0.8), (0.75, 0.0), (0.55, 0.8), (0.0, 1.2)], 10), HEAD_AT @ T(0.0, 2.12, 2.0) @ RX(math.pi * 0.5) @ S(1.15, 1.4, 0.45))
for side in (-1.0, 1.0):
    cut(face, lathe([(0.0, -1.0), (1.2, -0.7), (1.75, 0.0), (1.2, 0.7), (0.0, 1.0)], 10), HEAD_AT @ T(side * 2.9, 3.6, -0.4) @ RZ(math.pi * 0.5) @ S(1.0, 1.1, 1.15))
# broken bits of her shell in the sand by the holes
for side in (-1.0, 1.0):
    at = HEAD_AT @ Vector((side * 4.6, 3.2, -0.2))
    piece(box(1.3, 0.55, 0.9), STATUE, "RuinsTemple", T(at.x, -0.15, at.z) @ RY(RNG.uniform(0, 3)) @ RX(0.3))

# Her hand beside her, palm down on the paving, fingers spread and curled into the sand, a verdigris
# bracelet at the wrist (built wrist at the origin, fingers to +z, the back of the hand up).
HAND = T(11.6, 1.25, 12.4) @ RY(-0.5) @ S(1.3)
piece(frustum(8, 0.72, 0.8, 1.7, low_jag=0.2), STATUE, "RuinsTemple", HAND @ T(0.0, 0.0, 0.45) @ RX(-math.pi * 0.5))
piece(revolve([(0.74, -0.3), (0.98, -0.3), (0.98, 0.25), (0.74, 0.25)], 10), BRONZE, "RuinsTemple", HAND @ T(0.0, 0.0, -0.45) @ RX(math.pi * 0.5))
piece(box(1.9, 0.72, 2.05, taper=0.08), STATUE, "RuinsTemple", HAND @ T(0.0, -0.36, 1.375))
for x, scale, spread in ((-0.72, 0.85, -0.22), (-0.24, 1.0, -0.07), (0.24, 1.07, 0.07), (0.72, 1.0, 0.2)):
    M = HAND @ T(x, 0.0, 2.35) @ RY(spread)
    for length, curl in ((0.95, 0.22), (0.62, 0.4), (0.5, 0.42)):
        M = M @ RX(curl)
        piece(frustum(8, 0.27, 0.22, length * scale + 0.12, phase=0.5), STATUE, "RuinsTemple", M @ RX(math.pi * 0.5) @ T(0.0, -0.12, 0.0), sharp=80.0)
        M = M @ T(0.0, 0.0, length * scale - 0.08)
M = HAND @ T(0.95, -0.05, 0.95) @ RY(1.0)
for length, curl in ((0.85, 0.25), (0.65, 0.35)):
    M = M @ RX(curl)
    piece(frustum(6, 0.3, 0.25, length, phase=0.5), STATUE, "RuinsTemple", M @ RX(math.pi * 0.5), sharp=80.0)
    M = M @ T(0.0, 0.0, length)

# --- The colonnade behind the temple: two rows of six columns along x (an aisle 6 m wide between
# them), the beam still over part of the front row, the back row more broken.
STOA_Z = (-21.0, -27.0)
STOA_X = [0.6 + 3.6 * k for k in range(6)]
for row, zz in enumerate(STOA_Z):
    for k, x in enumerate(STOA_X):
        M = T(x, -0.2, zz) @ RY(RNG.uniform(0, 1))
        broken = {(0, 0): 3.1, (0, 5): 1.4, (1, 0): 2.2, (1, 2): 4.0, (1, 3): 0.9, (1, 5): 3.4}.get((row, k), 0.0)
        if (row, k) == (1, 4):
            piece(lathe([(0.0, -0.5), (0.58, -0.5), (0.58, 0.12), (0.5, 0.25), (0.0, 0.25)], 10), STONE, "RuinsStoa", M)
            continue
        column(M, "RuinsStoa", broken=broken)
# (column top: -0.2 + 0.2 + 4.6 + 0.82)
STOA_TOP = 5.42
piece(box(STOA_X[4] - STOA_X[1] + 1.6, 0.85, 1.2), STONE, "RuinsStoa", T((STOA_X[1] + STOA_X[4]) * 0.5, STOA_TOP, STOA_Z[0]))
piece(box(STOA_X[2] - STOA_X[0] + 1.4, 0.85, 1.2), STONE, "RuinsStoa", T(STOA_X[0] + 3.6, STOA_TOP - 1.6, STOA_Z[1] - 0.6) @ RZ(0.35) @ RY(0.05))
# a beam that fell across between the rows' ends, and a column fallen out of the back row
piece(box(4.6, 0.85, 1.2), STONE, "RuinsStoa", T(STOA_X[5] + 2.6, 0.2, -24.0) @ RY(1.2) @ RX(0.08))
fallen_column((STOA_X[4] + 0.3, 0.0, -28.8), -1.4, "RuinsStoa", (1.6, 1.5), capital=True)

# --- The stepped pyramid (to the right): five tiers and a pointed cap, a stair up its front (+Z)
# between low walls, a dark doorway at its foot beside the stair into a chamber, and a shaft up from
# the chamber that comes out at a small door high on the front.
PY = [(18.0, -1.2, 2.2), (14.8, 2.2, 4.4), (11.6, 4.4, 6.6), (8.4, 6.6, 8.8), (5.2, 8.8, 11.6)]
tiers = [piece(box(size, y1 - y0, size, taper=0.12), MASONRY, "RuinsPyramid", T(PX, y0, PZ)) for size, y0, y1 in PY]
piece(lathe([(3.0, 11.5), (0.0, 14.6)], 4, math.pi * 0.25), MASONRY, "RuinsPyramid", T(PX, 0.0, PZ))
CH = (PX + 2.2, PZ)           # the chamber's middle
SH = (PX, PZ)                 # the shaft's (the stair leads up to its door)
DOOR_X = PX + 3.8
for tier in tiers[:2]:
    cut(tier, box(7.0, 4.4, 7.0), T(CH[0], 0.2, CH[1]))
    cut(tier, box(3.0, 2.8, 8.0), T(DOOR_X, 0.2, PZ + 6.5))
for tier in tiers[1:]:
    cut(tier, box(3.0, 7.4, 3.0), T(SH[0], 4.0, SH[1]))
cut(tiers[4], box(3.0, 2.6, 6.0), T(SH[0], 8.85, SH[1] + 3.0))
STAIR_X = PX
profile = [(PZ + 13.0, -0.8)]
RISE = 14
for i in range(RISE):
    zz = PZ + 12.2 - (12.2 - 2.4) * i / RISE
    profile += [(zz, 8.8 * i / RISE), (zz, 8.8 * (i + 1) / RISE)]
profile += [(PZ + 1.8, 8.8), (PZ + 1.8, -0.8)]
# (laid out in (z, y): turned so its width runs along x)
piece(prism([(-zz, y) for zz, y in profile], 3.4), STONE, "RuinsPyramid", T(STAIR_X, 0.0, 0.0) @ RY(math.pi * 0.5))
for side in (-1.0, 1.0):
    wall = [(-(PZ + 12.6), -0.8), (-(PZ + 12.6), 0.9), (-(PZ + 2.4), 9.6), (-(PZ + 1.8), 9.6), (-(PZ + 1.8), -0.8)]
    piece(prism(wall, 0.45), STONE, "RuinsPyramid", T(STAIR_X + side * 1.92, 0.0, 0.0) @ RY(math.pi * 0.5))
piece(box(4.2, 0.6, 1.2), STONE, "RuinsPyramid", T(DOOR_X, 3.0, PZ + 9.2))
piece(prism(spiral_outline(0.42), 0.1), GOLD, "RuinsGlow", T(DOOR_X, 2.95 + 0.0, PZ + 9.84) @ T(0.0, 0.3, 0.0), collide=False)
for x, zz in ((PX + 9.6, PZ + 8.0), (PX + 8.4, PZ - 9.8), (PX - 9.2, PZ - 8.6)):
    piece(box(1.6, 1.0, 1.3), MASONRY, "RuinsPyramid", T(x, -0.35, zz) @ RY(RNG.uniform(0, 3)) @ RX(RNG.uniform(-0.3, 0.3)))

# --- The colossal pillar (right front), leaning a little: a slender shaft, a copper band under a
# cushion capital, a red-gold cup of leaves holding the glowing crystal.
PILLAR = T(PILLAR_AT[0], 0.0, PILLAR_AT[1]) @ RX(0.02) @ RZ(-0.02)
piece(box(3.0, 2.2, 3.0, taper=0.1), STONE, "RuinsTemple", PILLAR @ T(0.0, -1.0, 0.0) @ RY(0.3))
for k, (y0, y1) in enumerate(((1.2, 6.2), (6.2, 11.2), (11.2, 15.6))):
    piece(frustum(10, 0.82 + 0.03 * k, 0.85 + 0.03 * k, y1 - y0, phase=0.05 * k), RED, "RuinsTemple", PILLAR @ T(0.0, y0, 0.0))
for y in (6.0, 14.6):
    piece(revolve([(0.86, y), (1.02, y), (1.02, y + 0.42), (0.86, y + 0.42)], 10), GOLD, "RuinsGlow", PILLAR, collide=False)
piece(lathe([(0.0, 15.5), (0.95, 15.5), (1.4, 15.9), (1.35, 16.3), (1.0, 16.55), (0.0, 16.55)], 10), STONE, "RuinsTemple", PILLAR)
piece(box(2.3, 0.45, 2.3), STONE, "RuinsTemple", PILLAR @ T(0.0, 16.5, 0.0))
for k in range(6):
    leaf = [(-0.32, 0.0), (0.32, 0.0), (0.4, 0.5), (0.0, 1.15), (-0.4, 0.5)]
    piece(prism(leaf, 0.1), GOLD, "RuinsGlow", PILLAR @ RY(math.tau * k / 6.0) @ T(0.0, 16.95, 0.42) @ RX(-0.5), collide=False)
piece(lathe([(0.0, 16.95), (0.55, 16.95), (0.55, 17.25), (0.0, 17.25)], 10), GOLD, "RuinsGlow", PILLAR, collide=False)
piece(lathe([(0.0, 17.1), (0.48, 17.9), (0.4, 19.5), (0.0, 20.6)], 6), CRYSTAL, "RuinsGlow", PILLAR @ RZ(0.04))

# --- The field: carved blocks of a fallen frieze (running spirals over a copper wave band), drums,
# capitals and amphorae, strewn in the foreground and round the buildings.
WAVE = []
for k in range(25):
    t = k / 24.0
    WAVE.append((-2.6 + 5.2 * t, 0.12 + 0.13 * math.sin(t * math.tau * 4.0) + 0.1 * max(0.0, math.sin(t * math.tau * 4.0 + 1.2)) ** 6))
WAVE += [(2.6, -0.16), (-2.6, -0.16)]
for x, zz, turn, tilt in ((15.0, 19.5, -0.25, 0.0), (-7.0, 21.0, 0.35, 0.12), (-26.0, 6.0, 1.3, -0.08), (21.0, 9.0, 0.6, 0.18)):
    M = T(x, -0.35, zz) @ RY(turn) @ RZ(tilt)
    piece(box(6.0, 1.9, 1.5), STONE, "RuinsField", M)
    piece(box(6.3, 0.35, 1.7), STONE, "RuinsField", M @ T(0.0, 1.9, 0.0))
    for k in range(4):
        piece(prism(spiral_outline(0.5), 0.14), RELIEF, "RuinsField", M @ T(-2.1 + 1.4 * k, 1.35, 0.78) @ RZ(math.pi * (k % 2)), collide=False)
    piece(prism(WAVE, 0.08), GOLD, "RuinsGlow", M @ T(0.0, 0.55, 0.77), collide=False)
for i in range(13):
    x = RNG.uniform(6.0, 22.0) if i < 8 else RNG.uniform(-14.0, 2.0)
    zz = RNG.uniform(12.0, 24.0) if i < 8 else RNG.uniform(14.0, 30.0)
    if abs(x - GATE_X) < 4.5:
        continue
    r = RNG.uniform(0.45, 0.6)
    length = RNG.uniform(0.7, 1.15)
    if RNG.random() < 0.65:
        M = T(x, r - 0.15, zz) @ RY(RNG.uniform(0, math.pi)) @ RX(math.pi * 0.5 + RNG.uniform(-0.08, 0.08)) @ T(0.0, -length * 0.5, 0.0)
    else:
        M = T(x, -0.3, zz) @ RX(RNG.uniform(-0.12, 0.12)) @ RZ(RNG.uniform(-0.12, 0.12))
    piece(frustum(10, r, r, length, phase=RNG.uniform(0, 1)), RED, "RuinsField", M)
fallen_column((13.0, 0.0, 15.0), 1.9, "RuinsField", (1.8, 1.6), capital=False)
fallen_column((18.0, 0.0, -1.0), 2.6, "RuinsField", (1.7,), capital=True)
for x, zz in ((14.5, 26.0), (2.0, 16.0), (-11.0, 31.0)):
    M = T(x, 0.25, zz) @ RY(RNG.uniform(0, 3)) @ RX(RNG.uniform(-0.5, 0.5))
    piece(lathe([(0.0, -0.3), (0.52, -0.3), (0.74, -0.08), (0.72, 0.12), (0.56, 0.26), (0.0, 0.26)], 10), DARK, "RuinsField", M)
    piece(box(1.5, 0.3, 1.5), STONE, "RuinsField", M @ T(0.0, 0.24, 0.0))
for i in range(12):
    x, zz = (RNG.uniform(-24.0, 24.0), RNG.uniform(10.0, 30.0)) if i < 9 else (RNG.uniform(30.0, 36.0), RNG.uniform(-2.0, 4.0))
    if abs(x - GATE_X) < 3.0:
        x += 6.0
    if RNG.random() < 0.5:
        M = T(x, -0.45, zz) @ RX(RNG.uniform(-0.3, 0.3)) @ RZ(RNG.uniform(-0.3, 0.3))
    else:
        M = T(x, 0.3, zz) @ RY(RNG.uniform(0, 6)) @ RX(math.pi * 0.5 + RNG.uniform(-0.2, 0.2)) @ T(0.0, -0.7, 0.0)
    amphora(M @ S(1.25), "RuinsField")
# broken stone everywhere (the concept's strewn rubble)
for i in range(30):
    x, zz = RNG.uniform(-24.0, 36.0), RNG.uniform(-14.0, 32.0)
    if math.hypot(x - TX, zz - TZ) < 10.8 or abs(x - GATE_X) < 3.2 or (abs(x - PX) < 9.5 and abs(zz - PZ) < 9.5) or abs(zz - (-24.0)) < 4.0:
        continue
    s = RNG.uniform(0.35, 0.9)
    piece(box(s * RNG.uniform(1.0, 1.8), s * RNG.uniform(0.4, 0.8), s * RNG.uniform(0.8, 1.4), top_jag=0.1), STONE, "RuinsField",
          T(x, -0.15, zz) @ RY(RNG.uniform(0, 3)) @ RX(RNG.uniform(-0.3, 0.3)) @ RZ(RNG.uniform(-0.3, 0.3)), collide=s > 0.6)

LANTERNS = [(CH[0], 2.4, CH[1]), (TX, 6.0, TZ), (GATE_X, 4.0, GATE_Z), (PILLAR_AT[0], 19.4, PILLAR_AT[1]), (9.5, 4.0, -24.0),
            tuple(HEAD_AT @ Vector((0.0, 3.6, -0.6)))]
FISH = [(GATE_X, 3.0, 28.0), (-8.0, 4.5, 8.0), (TX + 10.0, 3.0, TZ), (TX + 2.0, 16.5, TZ + 3.0), (TX, 4.5, TZ), (9.0, 3.0, -24.0),
        (PILLAR_AT[0], 9.0, PILLAR_AT[1]), (PX, 16.0, PZ), (CH[0], 2.4, CH[1]), (16.0, 3.0, 18.0), (-24.0, 3.5, -4.0), (12.0, 4.0, 4.0)]


# ============================================================================================
# Checks on every piece by itself: faces outward (a line out of each face leaves the piece's skin
# an even number of times; turned over if most of a piece's faces fail).
def wrong_faces(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.normal_update()
    tree = BVHTree.FromBMesh(bm)
    wrong = counted = 0
    for f in bm.faces:
        if f.calc_area() < 1e-8:
            continue
        counted += 1
        votes = 0
        for nudge in (Vector((0.0, 0.0, 0.0)), Vector((0.013, 0.007, 0.0)), Vector((-0.009, 0.0, 0.011))):
            at = f.calc_center_median() + f.normal * 1e-5
            way = (f.normal + nudge).normalized()
            hits = 0
            while hits < 40:
                hit = tree.ray_cast(at, way)
                if hit[0] is None:
                    break
                hits += 1
                at = hit[0] + way * 1e-5
            votes += hits % 2
        if votes >= 2:
            wrong += 1
    bm.free()
    return wrong, counted


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


# --- Collision spheres, fitted to each solid piece: candidates inside it at many points (each as
# big as fits, up to RMAX), and the fewest of them that cover its skin above the sand (each point of
# the skin within TOL of a sphere). They stay inside the stone, so doorways stay open.
# The sand counts as solid too: a sphere may be centred under the sand (under the piece), as big as
# reaches no part of the piece's skin above the sand, so a few big ones cover a platform's top.
RMAX = 12.0
RMIN = 0.16
TOL = 0.34
# (a sphere may stand this far proud of the stone: a swimmer keeps that much further off a wall,
# and doorways are that much narrower to it: the route test allows for it)
PROUD = 0.25
COVER = 0.92
DEEP = (-0.8, -2.0, -3.8, -6.5, -10.0)
spheres = []


def fit_spheres(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.normal_update()
    tree = BVHTree.FromBMesh(bm)
    lo = Vector([min(v.co[i] for v in bm.verts) for i in range(3)])
    hi = Vector([max(v.co[i] for v in bm.verts) for i in range(3)])
    if hi.z < 0.1:
        bm.free()
        return []
    # the skin above the sand alone (what a sphere must not cross)
    above = bm.copy()
    bmesh.ops.bisect_plane(above, geom=above.verts[:] + above.edges[:] + above.faces[:], plane_co=(0.0, 0.0, 0.0), plane_no=(0.0, 0.0, 1.0), clear_inner=True)
    above.normal_update()
    skin_tree = BVHTree.FromBMesh(above) if above.faces else None
    above.free()
    if skin_tree is None:
        bm.free()
        return []

    def inside(p):
        # (lines out three ways; inside if most of them cross the skin an odd number of times. The
        # nearest face's normal was wrong at near ties by the rim of a ring: spheres in the cella's air)
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
    # the skin above the sand, as points
    skin = []
    for f in bm.faces:
        if max(v.co.z for v in f.verts) < -0.05:
            continue
        a, b, c = (v.co for v in f.verts)
        count = max(1, int(f.calc_area() / 0.3))
        for k in range(count):
            u, v = RNG.random(), RNG.random()
            if u + v > 1.0:
                u, v = 1.0 - u, 1.0 - v
            p = a + (b - a) * u + (c - a) * v
            if p.z > -0.05:
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
    size = hi - lo
    step = max(0.12, min(0.5, min(size) / 3.0))
    found = []
    nx, ny, nz = (max(1, int(size[i] / step) + 1) for i in range(3))
    heights = [lo.z + (k + 0.5) * size.z / nz for k in range(nz)]
    heights = [z for z in heights if z >= 0.0] + list(DEEP)
    for i in range(nx):
        for j in range(ny):
            for z in heights:
                p = Vector((lo.x + (i + 0.5) * size.x / nx, lo.y + (j + 0.5) * size.y / ny, z))
                if not inside(p if z >= 0.0 else Vector((p.x, p.y, 0.05))):
                    continue
                hit = skin_tree.find_nearest(p)
                if hit[0] is None or hit[3] < RMIN:
                    continue
                r = min(hit[3] + PROUD, RMAX)
                if p.z + r < 0.05:
                    continue
                found.append((p, r, {idx for _, idx, _ in kd.find_range(p, r + TOL)}))
    bm.free()
    # (greedy, lazily: a candidate's gain only shrinks as others are chosen)
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


thin = []
by_part = {}
for obj in SOLIDS:
    made = fit_spheres(obj)
    if not made and obj.dimensions.z > 0.3:
        thin.append(obj.name)
    for p, r in made:
        if "--debug-spheres" in sys.argv and r > 3.0 and p.z > 1.5:
            print("RUINS big sphere", obj.data.materials[0].name, tuple(round(c, 2) for c in p), round(r, 2), "dims", tuple(round(c, 1) for c in obj.dimensions))
    spheres += made
    by_part[obj.name.split(".")[0]] = by_part.get(obj.name.split(".")[0], 0) + len(made)
print("RUINS spheres: %d (pieces with none: %d): %s" % (len(spheres), len(thin), by_part))

# --- Joined into the parts; flat where edges are sharp, smooth across soft ones (the face).
parts = {}
for name in NAMES:
    objs = PARTS[name]
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
meshes = [parts[name] for name in NAMES]
triangles = {}
for obj in meshes:
    obj.data.calc_loop_triangles()
    triangles[obj.name] = len(obj.data.loop_triangles)
print("RUINS triangles %d: %s" % (sum(triangles.values()), ", ".join("%s %d" % kv for kv in triangles.items())))

# --- Empties: collision spheres, where life grows, where fish gather, where lamps could hang.
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


for i, (p, r) in enumerate(spheres):
    obj = bpy.data.objects.new("Rock%04d" % i, None)
    bpy.context.collection.objects.link(obj)
    obj.empty_display_type = "SPHERE"
    obj.location = p
    obj.scale = (r, r, r)

for i, at in enumerate(LANTERNS):
    empty("Lantern%02d" % i, at)
for i, at in enumerate(FISH):
    empty("FishSpot%02d" % i, at)

# where sea life grows: points on the stone facing up, spread over the precinct (the farthest from
# those already chosen, each time)
depsgraph = bpy.context.evaluated_depsgraph_get()
candidates = []
for i in range(1400):
    x, zz = RNG.uniform(-31.0, 38.0), RNG.uniform(-44.0, 37.0)
    hit, at, normal, _, obj, _ = bpy.context.scene.ray_cast(depsgraph, Vector(to_b((x, 30.0, zz))), Vector((0.0, 0.0, -1.0)))
    if hit and obj.name in parts and obj.name != "RuinsGlow" and at.z > 0.5 and normal.z > 0.6:
        candidates.append((Vector((at.x, at.z, -at.y)), Vector((normal.x, normal.z, -normal.y))))
reef = [candidates[0]]
while len(reef) < 40 and len(reef) < len(candidates):
    best = max(candidates, key=lambda c: min((c[0] - r[0]).length for r in reef))
    reef.append(best)
for i, (at, normal) in enumerate(reef):
    empty("ReefSpot%02d" % i, at, 1.0, normal)
print("RUINS reef spots %d (of %d places found)" % (len(reef), len(candidates)))

# --- Unwrapped into two pictures: the statue and the reliefs in one of their own (ruins_atlas_statue,
# 1024), everything else in the other (ruins_atlas, 2048); in that one, faces buried in the sand or
# facing straight down get less of it.
# Her face is one island, unwrapped round her head like a label (seam behind): smart projection cut
# it into islands whose edges drew dark lines across it. Which faces: those of the outer skin
# (facing out from her axis, not in the eye hollows, the mouth or the hollow inside).
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


temple_mesh = parts["RuinsTemple"].data
temple_names = [m.name for m in temple_mesh.materials]
skin = {poly.index for poly in temple_mesh.polygons if temple_names[poly.material_index] == "face" and on_face_skin(poly, temple_mesh)}
bpy.ops.object.select_all(action="DESELECT")
for obj in meshes:
    obj.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.mode_set(mode="EDIT")
bpy.context.tool_settings.mesh_select_mode = (False, False, True)
bpy.ops.mesh.select_all(action="SELECT")
edit = bmesh.from_edit_mesh(temple_mesh)
edit.faces.ensure_lookup_table()
for i in skin:
    edit.faces[i].select_set(False)
bmesh.update_edit_mesh(temple_mesh)
bpy.ops.uv.smart_project(angle_limit=math.radians(70.0), island_margin=0.003)
bpy.ops.object.mode_set(mode="OBJECT")
uv = temple_mesh.uv_layers.active.data
GIRTH = 2.0 * math.pi * 2.75
for i in skin:
    poly = temple_mesh.polygons[i]
    us = []
    for li in poly.loop_indices:
        p = head_local(temple_mesh.vertices[temple_mesh.loops[li].vertex_index].co)
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
        k = 1.0
        if names[poly.material_index] in BOOSTED:
            continue
        if max(mesh.vertices[v].co.z for v in poly.vertices) < -0.25:
            k = 0.25
        elif poly.normal.z < -0.7:
            k = 0.4
        if k != 1.0:
            for li in poly.loop_indices:
                uv[li].uv = uv[li].uv * k


def pack(chosen):
    """Packs the islands of the faces `chosen(material name)` picks into the whole square."""
    bpy.ops.object.select_all(action="DESELECT")
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.context.tool_settings.mesh_select_mode = (False, False, True)
    bpy.context.tool_settings.use_uv_select_sync = False
    bpy.ops.mesh.select_all(action="DESELECT")
    for obj in meshes:
        bm = bmesh.from_edit_mesh(obj.data)
        names = [m.name for m in obj.data.materials]
        for f in bm.faces:
            f.select_set(chosen(names[f.material_index]))
        bmesh.update_edit_mesh(obj.data)
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(margin=0.004, rotate=True)
    bpy.ops.object.mode_set(mode="OBJECT")


pack(lambda name: name in BOOSTED)
pack(lambda name: name not in BOOSTED)


def texel_density(obj, material_names, size=ATLAS_SIZE):
    """Pixels per metre on the faces painted with these materials."""
    mesh = obj.data
    mesh.calc_loop_triangles()
    uv = mesh.uv_layers.active.data
    names = [m.name for m in mesh.materials]
    area = uv_area = 0.0
    for tri in mesh.loop_triangles:
        if names[tri.material_index] not in material_names:
            continue
        a, b, c = (mesh.vertices[v].co for v in tri.vertices)
        area += (b - a).cross(c - a).length * 0.5
        p, q, r = (uv[li].uv for li in tri.loops)
        uv_area += abs((q - p).x * (r - p).y - (q - p).y * (r - p).x) * 0.5
    return size * math.sqrt(uv_area / area) if area > 0.0 else 0.0


print("RUINS texel density: face %.1f px/m, column shafts %.1f px/m, masonry %.1f px/m, plain stone %.1f px/m"
      % (texel_density(parts["RuinsTemple"], {"face"}, STATUE_SIZE), texel_density(parts["RuinsStoa"], {"shaft"}),
         texel_density(parts["RuinsPyramid"], {"masonry"}), texel_density(parts["RuinsGate"], {"stone"})))


# --- The bake: the sea's light (a sky overhead, a sun from straight above) over a ground plane.
def bake_ruins(meshes):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 64
    scene.cycles.device = "CPU"
    world = bpy.data.worlds.new("sea")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.9, 0.95, 1.0, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.85
    scene.world = world
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 1.2
    sun.angle = math.radians(20.0)
    lamp = bpy.data.objects.new("sun", sun)
    bpy.context.collection.objects.link(lamp)
    lamp.rotation_euler = (math.radians(12.0), math.radians(6.0), 0.0)
    # lamps at the lantern spots, so that what no sky reaches (the chamber, the hollow head, under
    # the dome) is painted lamplit, not black
    lamps = []
    for at in LANTERNS:
        glow = bpy.data.lights.new("lamp", "POINT")
        glow.energy = 220.0
        glow.color = (0.75, 0.95, 1.0)
        glow.shadow_soft_size = 0.6
        lamps.append(bpy.data.objects.new("lamp", glow))
        bpy.context.collection.objects.link(lamps[-1])
        lamps[-1].location = to_b(at)
    bpy.ops.mesh.primitive_plane_add(size=400.0, location=(0.0, 0.0, 0.0))
    ground = bpy.context.object
    ground.data.materials.append(material("sand", (0.5, 0.48, 0.42)))
    image = bpy.data.images.new(os.path.basename(ATLAS), ATLAS_SIZE, ATLAS_SIZE, alpha=False)
    statue = bpy.data.images.new(os.path.basename(STATUE_ATLAS), STATUE_SIZE, STATUE_SIZE, alpha=False)
    for made in bpy.data.materials:
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
    bpy.data.objects.remove(ground)
    bpy.data.objects.remove(lamp)
    for made in lamps:
        bpy.data.objects.remove(made)


if BAKE:
    bake_ruins(meshes)

os.makedirs(os.path.dirname(BLEND), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
bpy.ops.object.select_all(action="DESELECT")
for obj in bpy.data.objects:
    if obj.type in ("MESH", "EMPTY"):
        obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=GLB, export_format="GLB", export_apply=True, export_yup=True, use_selection=True, export_image_format="NONE")
print("RUINS wrote", GLB)
