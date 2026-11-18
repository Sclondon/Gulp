"""Builds the reef wreck: a sunken four-funnel liner, broken in two, as a low-poly model with one painted
picture per half.

    blender --background --factory-startup --python tools/build_wreck.py [-- --no-bake]

Writes models/wreck_liner.glb, models/wreck_liner.json (collision spheres and swim routes),
textures/wreck_atlas_bow.png, textures/wreck_atlas_stern.png and tools/blend/wreck_liner.blend.
The design sheet, the checks and whose calls they were: tools/WRECK.md.

The user (2026-11-18): "the reef should be built into a ship wreck like an onld timy passenger titanic
style". An original ship in the manner of the four-funnel liners of 1910: no name, no real ship's plan.

How it is made. The ship is built upright in its own frame (Blender: +Y to the bow, +X to starboard, +Z
up, the keel's bottom at z = 0, the middle of its length at y = 0). The hull is lofted from stations
(`ring`), the superstructure, forecastle and poop are prisms; they are joined into one solid and the
rooms, hatches, shafts, windows, portholes and the tear are cut out of it (exact booleans, each cutter
carrying the material its faces take). It is then broken in two along a jagged surface (`BREAK`). The
smaller parts (funnels, the staircase, davits, masts, the bridge, decals for painted portholes...) are
separate closed solids joined into the half they belong to. Each half is then laid on the bed
(`M_BOW`, `M_STERN`), unwrapped, and its paint baked by Cycles: colour from procedural materials
(`paint`) times how open each spot is to the sea's light (a plain sky over a sand plane: dark inside,
light on top). The game draws that picture lit by the sea (shaders/wreck.gdshader).

Collision: spheres for Sea.add_rock, made here (`spheres`) by covering every surface of the parts that
stop a swimmer, greedily, with the biggest sphere that bulges no more than BULGE out of the part, kept
off the swim routes (`ROUTES`). Both go to the JSON in Godot's axes.

Godot's axes: Blender (x, y, z) is Godot (x, z, -y). The bow points to Godot's -Z, starboard is +X, the
origin is the middle of the keel's resting line on the sea bed (y = 0 at the bed).
"""
import os
import sys
import math
import json
import random

HERE = os.path.dirname(os.path.abspath(__file__))
source = open(os.path.join(HERE, "build_panel.py")).read()
exec(compile(source.split("# --- The helm housing")[0], "build_panel.py", "exec"))

from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

# (the panel's own materials are not used here)
for made in list(bpy.data.materials):
    bpy.data.materials.remove(made)

GLB = os.path.join(HERE, "..", "models", "wreck_liner.glb")
DATA = os.path.join(HERE, "..", "models", "wreck_liner.json")
BLEND = os.path.join(HERE, "blend", "wreck_liner.blend")
ATLAS = {"bow": os.path.join(HERE, "..", "textures", "wreck_atlas_bow.png"),
         "stern": os.path.join(HERE, "..", "textures", "wreck_atlas_stern.png")}
ATLAS_SIZE = {"bow": 4096, "stern": 2048}
BAKE = "--no-bake" not in sys.argv
SAMPLES = 48
rng = random.Random(7)

# --- The ship's numbers (metres, in its own upright frame)
B = 3.5            # half the beam
DECK = 7.0         # the hull's top (the shelter deck)
WL = 3.6           # the old waterline: red below
PROM = 7.25        # the promenade's floor
CEIL = 9.6         # its ceiling, under the boat deck
BOAT = 9.9         # the boat deck
SUPER = 3.3        # the superstructure's half width
BREAK = -10.3      # where it broke (the middle of the jagged line)
WALL = 0.45        # the hull's thickness round the rooms
FUNNELS = {1: 10.5, 2: 3.5, 3: -3.0, 4: -15.5}   # y of each funnel's middle
FUN_AX = 1.3       # a funnel's half width across the ship
FUN_AY = 1.5       # and along it
FUN_TOP = 17.4     # the standing funnel's rim
STAIR = (-9.0, -5.8, 9)   # the grand staircase: foot, top (y), steps
DOME = (0.0, -7.6, 2.0)   # the skylight: middle and radius of its opening
# The halves as they lie (Blender world): the bow lists 12 degrees to port, nose a little down, sunk
# half a metre; the stern lies off, swung, rolled the other way and sunk deeper.
LIST = -12.0
M_BOW = Matrix.Translation((0.0, 0.0, -0.45)) @ Matrix.Rotation(math.radians(-1.2), 4, "X") @ Matrix.Rotation(math.radians(LIST), 4, "Y")
_PIVOT = Vector((0.0, -20.0, 0.0))
M_STERN = (Matrix.Translation((1.0, -5.5, -1.4)) @ Matrix.Translation(_PIVOT) @ Matrix.Rotation(math.radians(20.0), 4, "Z")
           @ Matrix.Rotation(math.radians(-2.0), 4, "X") @ Matrix.Rotation(math.radians(5.0), 4, "Y") @ Matrix.Translation(-_PIVOT))
M_OF = {"bow": M_BOW, "stern": M_STERN}
to_bow = M_BOW.inverted()


GAIN = 1.8


# --- Paint: procedural materials for the bake. Soft patches, rust running down, pale growth and
# silt on whatever faces up, planks on decks.
def paint(name, base, rust, growth, size=3.0, streak=None, planks=False, grow=0.6, seams=False, waterline=False, crust=0.0):
    # (every colour times GAIN: the first pictures in the game's water were far darker than its sand)
    base, rust, growth = (tuple(min(1.0, c * GAIN) for c in t) for t in (base, rust, growth))
    streak = tuple(min(1.0, c * GAIN) for c in streak) if streak else None
    made = bpy.data.materials.new(name)
    made.use_nodes = True
    nodes = made.node_tree.nodes
    links = made.node_tree.links
    shader = next(n for n in nodes if n.type == "BSDF_PRINCIPLED")
    shader.inputs["Roughness"].default_value = 1.0
    for key in ("Specular IOR Level", "Specular"):
        if key in shader.inputs:
            shader.inputs[key].default_value = 0.0
    place = nodes.new("ShaderNodeTexCoord")

    def noise(scale, shift, detail=2.0):
        stretch = nodes.new("ShaderNodeMapping")
        stretch.inputs["Scale"].default_value = scale
        stretch.inputs["Location"].default_value = shift
        links.new(place.outputs["Object"], stretch.inputs["Vector"])
        tex = nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = 1.0
        tex.inputs["Detail"].default_value = detail
        tex.inputs["Roughness"].default_value = 0.55
        links.new(stretch.outputs["Vector"], tex.inputs["Vector"])
        return tex.outputs["Fac"]

    def ramp(fac, low, high):
        node = nodes.new("ShaderNodeMapRange")
        node.interpolation_type = "SMOOTHSTEP"
        node.inputs["From Min"].default_value = low
        node.inputs["From Max"].default_value = high
        links.new(fac, node.inputs["Value"])
        return node.outputs["Result"]

    def mix(first, colour, fac):
        node = nodes.new("ShaderNodeMixRGB")
        if isinstance(first, tuple):
            node.inputs["Color1"].default_value = (*first, 1.0)
        else:
            links.new(first, node.inputs["Color1"])
        node.inputs["Color2"].default_value = (*colour, 1.0)
        links.new(fac, node.inputs["Fac"])
        return node.outputs["Color"]

    def times(a, b):
        node = nodes.new("ShaderNodeMath")
        node.operation = "MULTIPLY"
        links.new(a, node.inputs[0])
        links.new(b, node.inputs[1])
        return node.outputs["Value"]

    k = 1.0 / size
    colour = mix(base, rust, ramp(noise((k, k, k), (0.0, 0.0, 0.0)), 0.45, 0.72))
    if streak:
        # (runs of rust: noise stretched far down)
        colour = mix(colour, streak, ramp(noise((k * 2.5, k * 2.5, k * 0.18), (3.1, 7.7, 1.3), 3.0), 0.56, 0.74))
    if planks:
        wave = nodes.new("ShaderNodeTexWave")
        wave.wave_type = "BANDS"
        wave.bands_direction = "X"
        wave.inputs["Scale"].default_value = 1.1
        wave.inputs["Distortion"].default_value = 0.6
        links.new(place.outputs["Object"], wave.inputs["Vector"])
        seam = nodes.new("ShaderNodeMath")
        seam.operation = "SUBTRACT"
        seam.inputs[0].default_value = 1.0
        links.new(ramp(wave.outputs["Fac"], 0.04, 0.16), seam.inputs[1])
        colour = mix(colour, tuple(c * 0.35 for c in base), times(seam.outputs["Value"], ramp(noise((k * 4, k * 4, k * 4), (5.0, 1.0, 2.0)), 0.25, 0.5)))
    def flip(fac):
        node = nodes.new("ShaderNodeMath")
        node.operation = "SUBTRACT"
        node.inputs[0].default_value = 1.0
        links.new(fac, node.inputs[1])
        return node.outputs["Value"]

    def bands(direction, scale, shift=0.0):
        stretch = nodes.new("ShaderNodeMapping")
        stretch.inputs["Location"].default_value = (shift, shift, shift)
        links.new(place.outputs["Object"], stretch.inputs["Vector"])
        wave = nodes.new("ShaderNodeTexWave")
        wave.wave_type = "BANDS"
        wave.bands_direction = direction
        wave.inputs["Scale"].default_value = scale
        wave.inputs["Distortion"].default_value = 0.0
        links.new(stretch.outputs["Vector"], wave.inputs["Vector"])
        return wave.outputs["Fac"]

    if seams:
        # plate seams: strakes 1.4 m high, plates 3 m long, each seam with a fainter rivet row beside it
        line = tuple(c * 0.45 for c in base)
        colour = mix(colour, line, flip(ramp(bands("Z", 0.224), 0.0, 0.02)))
        colour = mix(colour, line, flip(ramp(bands("Y", 0.105), 0.0, 0.012)))
        faint = tuple(c * 0.75 for c in base)
        colour = mix(colour, faint, flip(ramp(bands("Z", 0.224, 0.09), 0.0, 0.01)))
    if crust:
        # growth breaking up the paint wherever it faces
        colour = mix(colour, growth, ramp(noise((k * 2.2, k * 2.2, k * 2.2), (2.0, 6.0, 1.0), 3.0), 0.62 - crust * 0.2, 0.72 - crust * 0.15))
    if waterline:
        # a band of weed along the old waterline
        split_at = nodes.new("ShaderNodeSeparateXYZ")
        links.new(place.outputs["Object"], split_at.inputs["Vector"])
        under = ramp(split_at.outputs["Z"], WL - 0.7, WL - 0.05)
        over = flip(ramp(split_at.outputs["Z"], WL + 0.1, WL + 1.0))
        weed = (0.05 * GAIN, 0.1 * GAIN, 0.03 * GAIN)
        colour = mix(colour, weed, times(times(under, over), ramp(noise((k * 3.0, k * 3.0, k * 1.0), (1.0, 4.0, 8.0), 3.0), 0.42, 0.62)))
    # pale growth and silt on what faces up
    geo = nodes.new("ShaderNodeNewGeometry")
    split = nodes.new("ShaderNodeSeparateXYZ")
    links.new(geo.outputs["Normal"], split.inputs["Vector"])
    up = ramp(split.outputs["Z"], 0.35, 0.9)
    patchy = ramp(noise((k * 1.7, k * 1.7, k * 1.7), (9.0, 2.0, 4.0)), 0.5 - grow * 0.35, 0.75 - grow * 0.2)
    colour = mix(colour, growth, times(up, patchy))
    links.new(colour, shader.inputs["Base Color"])
    return made


# (the palette after the concept art, tools/art_src/concept_liner_wreck.jpg: slate-blue hull plate
# with orange rust runs, a dull red bottom, grimy white houses, warm brown decks, moss on what faces up)
HULL = paint("hull", (0.028, 0.038, 0.048), (0.19, 0.075, 0.03), (0.13, 0.19, 0.08), 3.5, (0.26, 0.095, 0.03), seams=True, waterline=True)
ANTIFOUL = paint("antifoul", (0.16, 0.045, 0.028), (0.11, 0.05, 0.03), (0.16, 0.22, 0.1), 3.0, (0.21, 0.08, 0.03), seams=True, waterline=True, crust=0.3)
DECKING = paint("deck", (0.15, 0.095, 0.05), (0.09, 0.065, 0.04), (0.16, 0.22, 0.09), 2.5, None, True, 0.5)
WHITE = paint("super", (0.46, 0.48, 0.43), (0.24, 0.15, 0.07), (0.17, 0.25, 0.1), 2.5, (0.2, 0.085, 0.03), seams=True)
RUST = paint("rustrun", (0.075, 0.03, 0.012), (0.11, 0.04, 0.014), (0.075, 0.03, 0.012), 0.5, None, False, 0.0)
FUNNEL = paint("funnel", (0.36, 0.25, 0.12), (0.2, 0.09, 0.035), (0.17, 0.24, 0.1), 2.0, (0.12, 0.05, 0.02))
PANEL = paint("saloon", (0.09, 0.06, 0.035), (0.05, 0.036, 0.022), (0.24, 0.23, 0.19), 1.5, None, False, 0.7)
INSIDE = paint("inside", (0.1, 0.055, 0.035), (0.06, 0.04, 0.025), (0.22, 0.21, 0.18), 2.0, (0.14, 0.06, 0.03))
IRON = paint("iron", (0.14, 0.065, 0.03), (0.22, 0.09, 0.03), (0.16, 0.22, 0.09), 1.2)
BRONZE = paint("brass", (0.1, 0.2, 0.15), (0.16, 0.11, 0.05), (0.2, 0.28, 0.16), 0.8)
MOSS = paint("moss", (0.07, 0.15, 0.04), (0.12, 0.18, 0.05), (0.1, 0.2, 0.06), 0.8, None, False, 0.0)
GLASS = paint("glass", (0.28, 0.42, 0.42), (0.2, 0.3, 0.3), (0.3, 0.38, 0.34), 1.0, None, False, 0.3)
DARK = paint("dark", (0.006, 0.006, 0.007), (0.01, 0.009, 0.008), (0.012, 0.012, 0.012), 1.0, None, False, 0.0)
SAND = paint("sand", (0.4, 0.38, 0.33), (0.36, 0.34, 0.3), (0.4, 0.38, 0.33), 4.0)


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


# --- The hull's shape
ZS = [(0.15, 0.0), (B - 1.0, 0.0), (B - 0.5, 0.134), (B - 0.134, 0.5), (B, 1.0), (B, 2.0), (B, WL), (B, 4.6), (B, 5.9), (B, DECK)]
STATIONS = [-30.0, -29.5, -28.7, -27.6, -26.5, -25.8, -24.5, -23.0, -21.5, -20.0, -18.5, -17.0, -6.0, 6.0, 14.0, 16.0, 18.0,
            20.0, 22.0, 24.0, 25.5, 27.0, 28.0, 29.0, 29.6, 30.0]


def keel(y):
    """How high the hull's bottom is at a station: the forefoot rounds up; aft, it rises to clear the
    propeller, and the counter overhangs."""
    if y > 28.0:
        return (y - 28.0) * 0.35
    if y < -25.8:
        return 3.4 + (-25.8 - y) * 0.2
    return 3.4 * smooth(-19.5, -25.8, y)


def fine(y, z):
    """How much of the full beam the hull has at a station and height: the bow fines to a plumb stem,
    finer low down (flare above); aft, the run narrows under an elliptical counter."""
    if y > 14.0:
        t = max(0.0, (30.0 - y) / 16.0)
        e = 0.75 + 0.75 * (1.0 - min(z, DECK) / DECK)
        return t ** e
    if y < -17.0:
        up = math.sqrt(max(0.0, 1.0 - ((-17.0 - y) / 13.2) ** 2))
        low = max(0.0, min(1.0, (y + 25.8) / 9.5)) ** 1.1
        return low + (up - low) * smooth(2.4, 4.4, z)
    return 1.0


def hull_x(y, z):
    return max(B * fine(y, z), 0.03)


def ring(y, inset=0.0, floor=0.0, top=DECK):
    bottom = keel(y) + floor
    points = []
    for x, z in ZS:
        zz = bottom + z * (top - bottom) / DECK
        points.append((max(x * fine(y, zz) - inset, 0.03), zz))
    return [(x, y, z) for x, z in points] + [(-x, y, z) for x, z in reversed(points)]


def deck_edge(y):
    """Half the hull's width along its top."""
    return max(B * fine(y, DECK) - 0.01, 0.03)


def fc_top(y):
    return 8.6 + 0.45 * ((y - 19.0) / 11.0) ** 2


def poop_top(y):
    return 8.6 + 0.25 * ((-22.0 - y) / 8.0) ** 2


def break_y(x, z):
    """The jagged line it broke along: the bow is what lies forward of it."""
    return BREAK + 0.9 * math.sin(1.3 * x + 0.7 * z) + 0.55 * math.sin(2.9 * z - 0.8 * x + 1.0) + 0.35 * math.sin(5.1 * x + 3.7 * z)


# --- Building blocks: every one a closed solid, faces outward.
PARTS = []


def loft(rings, caps=True, cyclic=False):
    bm = bmesh.new()
    made = [[bm.verts.new(p) for p in r] for r in rings]
    n = len(rings[0])
    pairs = list(zip(made, made[1:])) + ([(made[-1], made[0])] if cyclic else [])
    for a, b in pairs:
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    if caps and not cyclic:
        bm.faces.new(made[0])
        bm.faces.new(list(reversed(made[-1])))
    return bm


def orient(bm):
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    volume = sum(f.calc_area() * f.normal.dot(f.calc_center_median()) for f in bm.faces)
    if volume < 0.0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
        bm.normal_update()


def sect_of(p):
    return "bow" if p[1] > break_y(p[0], p[2]) else "stern"


def part(name, bm, mats, closed=True, collide=False, sect=None, rule=None, matrix=None):
    """Makes an object of a bmesh. `mats` is one material or a list; `rule(face) -> index` picks each
    face's. `matrix` moves it (built at the origin). `sect` is the half it belongs to (else by where
    it is)."""
    if matrix is not None:
        bmesh.ops.transform(bm, matrix=matrix, verts=bm.verts[:])
    if closed:
        orient(bm)
    bm.normal_update()
    mats = list(mats) if isinstance(mats, (list, tuple)) else [mats]
    if rule:
        for f in bm.faces:
            f.material_index = rule(f)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    middle = sum((v.co for v in bm.verts), Vector()) / max(len(bm.verts), 1)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    for m in mats:
        mesh.materials.append(m)
    PARTS.append({"obj": obj, "closed": closed, "collide": collide, "sect": sect or sect_of(middle)})
    return obj


def ring4(x0, x1, y0, y1, z):
    return [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]


def block(x0, x1, y0, y1, z0, z1):
    return loft([ring4(x0, x1, y0, y1, z0), ring4(x0, x1, y0, y1, z1)])


def box(mat, x0, x1, y0, y1, z0, z1, **kw):
    return part(kw.pop("name", "box"), block(x0, x1, y0, y1, z0, z1), mat, **kw)


def plate(mat, size, matrix, **kw):
    """A box of a size about its own middle, moved by a matrix (for things lying askew)."""
    sx, sy, sz = size[0] * 0.5, size[1] * 0.5, size[2] * 0.5
    return part(kw.pop("name", "plate"), block(-sx, sx, -sy, sy, -sz, sz), mat, matrix=matrix, **kw)


def prism(mat, points, plane, a0, a1, **kw):
    """A flat outline extruded: plane "xy" (points x, y; from z = a0 to a1), "yz" (y, z; along x) or
    "xz" (x, z; along y)."""
    def at(u, v, a):
        return {"xy": (u, v, a), "yz": (a, u, v), "xz": (u, a, v)}[plane]
    return part(kw.pop("name", "prism"), loft([[at(u, v, a0) for u, v in points], [at(u, v, a1) for u, v in points]]), mat, **kw)


def frame(axis):
    a = axis.normalized()
    ref = Vector((0.0, 0.0, 1.0)) if abs(a.z) < 0.9 else Vector((1.0, 0.0, 0.0))
    u = a.cross(ref).normalized()
    return u, a.cross(u).normalized()


def circle(c, u, v, r, sides, sx=1.0, sy=1.0, phase=0.0):
    return [c + u * (math.cos(phase + math.tau * k / sides) * r * sx) + v * (math.sin(phase + math.tau * k / sides) * r * sy) for k in range(sides)]


def cyl(mat, p0, p1, r0, r1=None, sides=8, **kw):
    p0 = Vector(p0)
    p1 = Vector(p1)
    u, v = frame(p1 - p0)
    r1 = r0 if r1 is None else r1
    return part(kw.pop("name", "cyl"), loft([circle(p0, u, v, r0, sides, phase=math.pi / sides), circle(p1, u, v, r1, sides, phase=math.pi / sides)]), mat, **kw)


def rod(mat, points, r, sides=4, **kw):
    """A bar along a line of points (frames carried along it, so it does not twist)."""
    pts = [Vector(p) for p in points]
    rings = []
    u = None
    for i, p in enumerate(pts):
        t = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        if u is None:
            u, _ = frame(t)
        u = (u - t * u.dot(t)).normalized()
        v = t.cross(u)
        rings.append(circle(p, u, v, r, sides, phase=math.pi / sides))
    return part(kw.pop("name", "rod"), loft(rings), mat, **kw)


def cone(mat, top, length, r, **kw):
    """A rusticle: a four-sided cone hanging from a point."""
    bm = bmesh.new()
    t = Vector(top)
    ring_ = [bm.verts.new(t + Vector((math.cos(a) * r, math.sin(a) * r, 0.0))) for a in (0.4, 0.4 + math.pi / 2, 0.4 + math.pi, 0.4 + 1.5 * math.pi)]
    tip = bm.verts.new(t + Vector((rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05), -length)))
    bm.faces.new(ring_)
    for i in range(4):
        bm.faces.new((ring_[(i + 1) % 4], ring_[i], tip))
    return part(kw.pop("name", "rusticle"), bm, mat, **kw)


def ell(cx, cy, z, ax, ay, sides=16, shift=0.0, jag=None):
    return [Vector((cx + ax * math.cos(math.tau * k / sides), cy + shift + ay * math.sin(math.tau * k / sides), z + (jag(k) if jag else 0.0))) for k in range(sides)]


def decal(mat, middle, normal, outline, lift=0.012, **kw):
    """Paint, in effect: a flat outline (u, v pairs, in metres) lying on a surface, facing out of it."""
    n = Vector(normal).normalized()
    u = n.cross(Vector((0.0, 0.0, 1.0)))
    if u.length < 0.1:
        u = n.cross(Vector((1.0, 0.0, 0.0)))
    u.normalize()
    v = n.cross(u)
    if v.z < 0.0:
        v = -v
    c = Vector(middle) + n * lift
    bm = bmesh.new()
    face = bm.faces.new([bm.verts.new(c + u * a + v * b) for a, b in outline])
    bm.normal_update()
    if face.normal.dot(n) < 0.0:
        face.normal_flip()
    return part(kw.pop("name", "decal"), bm, mat, closed=False, **kw)


def octagon(r):
    return [(math.cos(math.tau * (k + 0.5) / 8) * r, math.sin(math.tau * (k + 0.5) / 8) * r) for k in range(8)]


def annulus(mat, middle, normal, r0, r1, lift=0.008, **kw):
    n = Vector(normal).normalized()
    u = n.cross(Vector((0.0, 0.0, 1.0)))
    if u.length < 0.1:
        u = n.cross(Vector((1.0, 0.0, 0.0)))
    u.normalize()
    v = n.cross(u)
    c = Vector(middle) + n * lift
    bm = bmesh.new()
    inner = [bm.verts.new(c + u * a + v * b) for a, b in octagon(r0)]
    outer = [bm.verts.new(c + u * a + v * b) for a, b in octagon(r1)]
    for i in range(8):
        j = (i + 1) % 8
        bm.faces.new((inner[i], inner[j], outer[j], outer[i]))
    bm.normal_update()
    for f in bm.faces:
        if f.normal.dot(n) < 0.0:
            f.normal_flip()
    return part(kw.pop("name", "ring"), bm, mat, closed=False, **kw)


def rect(w, h):
    return [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]


def hull_normal(side, y, z):
    e = 0.05
    dy = (hull_x(y + e, z) - hull_x(y - e, z)) / (2 * e)
    dz = (hull_x(y, z + e) - hull_x(y, z - e)) / (2 * e)
    return Vector((side, -side * dy, -side * dz)).normalized()


def on_top(f):
    return f.normal.z > 0.7


# --- Booleans
def apply_boolean(target, tool, op):
    mod = target.modifiers.new("cut", "BOOLEAN")
    mod.operation = op
    mod.solver = "EXACT"
    mod.object = tool
    if hasattr(mod, "material_mode"):
        mod.material_mode = "TRANSFER"
    bpy.ops.object.select_all(action="DESELECT")
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=mod.name)


def forget(obj):
    for i, p in enumerate(PARTS):
        if p["obj"] is obj:
            del PARTS[i]
            break
    bpy.data.objects.remove(obj, do_unlink=True)


def merge(objs):
    """Joins objects into the first (for a cutter made of many pieces)."""
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    for o in objs[1:]:
        for i, p in enumerate(PARTS):
            if p["obj"] is o:
                del PARTS[i]
                break
    return objs[0]


def cut(target, tool, op="DIFFERENCE"):
    apply_boolean(target, tool, op)
    forget(tool)


# ============================================================================================
# The body: hull, superstructure, forecastle and poop as one solid
# ============================================================================================
def hull_rule(f):
    if on_top(f):
        return 2
    return 1 if f.calc_center_median().z < WL else 0


body = part("Body", loft([ring(y) for y in STATIONS]), [HULL, ANTIFOUL, DECKING], rule=hull_rule, sect="bow")

# superstructure: the promenade deck's house, full length, its front rounded
front = [(SUPER, 13.3), (3.05, 14.25), (2.2, 14.6), (0.9, 14.78), (-0.9, 14.78), (-2.2, 14.6), (-3.05, 14.25), (-SUPER, 13.3)]
plan = [(-SUPER, -18.0), (SUPER, -18.0)] + front
house = prism([HULL, DECKING], plan, "xy", 6.9, BOAT, rule=lambda f: 1 if on_top(f) else 0)
cut(body, house, "UNION")

# forecastle and poop: raised over the hull's top, following its plan, their decks sheered up
def raised(y_list, top):
    pts = [(deck_edge(y) - 0.01, y) for y in y_list]
    outline = pts + [(-x, y) for x, y in reversed(pts)]
    bm = loft([[(x, y, 6.8) for x, y in outline], [(x, y, top(y)) for x, y in outline]])
    return bm


def raised_rule(f):
    if f.normal.z > 0.5:
        return 1
    return 2


fc = part("forecastle", raised([19.0, 20.5, 22.0, 23.5, 25.0, 26.5, 27.5, 28.5, 29.3, 30.0], fc_top), [HULL, DECKING, WHITE], rule=raised_rule)
cut(body, fc, "UNION")
poop = part("poop", raised([-30.0, -29.5, -28.7, -27.6, -26.5, -25.0, -23.5, -22.0], poop_top), [HULL, DECKING, WHITE], rule=raised_rule)
cut(body, poop, "UNION")


# --- The rooms: cut out, each cutter painting the faces it leaves
INSET_STATIONS = [-24.0, -23.0, -21.5, -20.0, -18.5, -17.0, -6.0, 6.0, 14.0, 16.0, 18.0, 20.0, 22.0, 24.0, 26.0]


def hold_room(mat, y0, y1, z0=0.6, z1=6.75):
    # (the floors are high enough that the sea bed, round the hull as it lies, stays under them)
    inner = part("inner", loft([ring(y, WALL, z0, 6.75) for y in INSET_STATIONS]), mat)
    limit = box(mat, -5.0, 5.0, y0, y1, z0, z1)
    cut(inner, limit, "INTERSECT")
    return inner


def ell_prism(mat, cx, cy, ax, ay, z0, z1, sides=16):
    return part("shaft", loft([ell(cx, cy, z0, ax, ay, sides), ell(cx, cy, z1, ax, ay, sides)]), mat)


cutters = [
    hold_room(INSIDE, 2.0, 13.5, 1.4),                                         # the boiler room
    hold_room(INSIDE, 14.0, 23.0, 1.7),                                        # the forward hold
    hold_room(INSIDE, -22.0, -9.0, 2.2),                                       # the engine room (stern)
    box(PANEL, -3.0, 3.0, -12.6, -4.5, 4.0, CEIL + 0.02),                 # the saloon under the dome
    box(WHITE, 0.6, 3.0, -4.6, 13.5, PROM, CEIL),                         # the promenade (starboard)
    box(PANEL, -3.0, 3.0, -13.8, -8.0, PROM, CEIL),                       # the stern's lounge
    ell_prism(INSIDE, 0.0, FUNNELS[1], FUN_AX - 0.3, FUN_AY - 0.3, 6.0, 10.6),   # down the first funnel
    ell_prism(INSIDE, 0.0, FUNNELS[4], FUN_AX - 0.3, FUN_AY - 0.3, 6.0, 10.6),   # down the fourth
    box(INSIDE, -1.5, 1.5, 14.7, 17.3, 6.0, 7.6),                         # the well deck's hatch
    box(INSIDE, -1.2, 1.2, 20.3, 22.3, 6.0, 9.6),                         # the forecastle's hatch
    box(INSIDE, -1.2, 1.2, 13.3, 14.3, 1.75, 4.2),                         # the bulkhead's broken door
    ell_prism(PANEL, DOME[0], DOME[1], DOME[2], DOME[2], 9.4, 10.3, 20),  # the skylight's opening
]
# the tear in the starboard side, into the boiler room
tear = []
for k in range(18):
    a = math.tau * k / 18
    jag = (1.0 if k % 2 == 0 else 0.6) + rng.uniform(-0.08, 0.08)
    tear.append((7.5 + math.cos(a) * 2.5 * jag, 3.45 + math.sin(a) * 1.9 * jag))
cutters.append(prism(INSIDE, tear, "yz", 2.4, 4.3))
# the saloon's starboard side torn open (the concept art's): the grand staircase seen from outside
SALOON_HOLE = (-7.4, 6.6)
gash = []
for k in range(22):
    a = math.tau * k / 22
    jag = (1.0 if k % 2 == 0 else 0.68) + rng.uniform(-0.1, 0.1)
    gash.append((SALOON_HOLE[0] + math.cos(a) * 2.1 * jag, SALOON_HOLE[1] + math.sin(a) * 2.0 * jag))
cutters.append(prism(INSIDE, gash, "yz", 2.55, 4.3))
for c in cutters:
    cut(body, c)

# windows: the promenade's long row (starboard, open), the saloon's and the lounge's (both sides)
WINDOWS = [12.2, 9.9, 7.6, 5.3, 3.0, 0.7, -1.6, -3.9]
holes = [box(WHITE, 2.8, 3.6, y - 0.75, y + 0.75, 7.9, 9.2) for y in WINDOWS]
for y in (-6.8, -9.3, -12.4):
    for side in (-1.0, 1.0):
        holes.append(box(WHITE, min(side * 2.8, side * 3.6), max(side * 2.8, side * 3.6), y - 0.7, y + 0.7, 7.9, 9.2))
cut(body, merge(holes))

# portholes, open where a room is behind them (0.5 m across: a sardine fits)
REAL = {1.0: [2.8, 4.3, 11.2, 12.6, 15.0, 16.5, 18.0, 19.5, 21.0, -6.0, -7.5, -9.0, -10.5, -12.0, -11.5, -13.0, -14.5, -17.5, -19.0],
        -1.0: [2.8, 4.3, 5.8, 7.3, 8.8, 10.3, 11.8, 15.0, 16.5, 18.0, 19.5, 21.0, -6.0, -7.5, -9.0, -10.5, -12.0, -11.5, -13.0, -14.5, -17.5, -19.0]}
# (the saloon's and the engine room's overlap by the break: keep one of each pair)
for side in REAL:
    REAL[side] = sorted(set(y for y in REAL[side] if not (-12.1 < y < -11.4)))
holes = []
for side, ys in REAL.items():
    for y in ys:
        x = hull_x(y, 5.9)
        holes.append(cyl(BRONZE, (side * (x - 0.9), y, 5.9), (side * (x + 0.3), y, 5.9), 0.25, sides=8))
cut(body, merge(holes))

# --- Broken in two
def break_cutter():
    xs = [-5.0 + k for k in range(11)]
    zs = [-2.0 + k for k in range(16)]
    bm = bmesh.new()
    front_ = [[bm.verts.new((x, break_y(x, z), z)) for x in xs] for z in zs]
    back = [[bm.verts.new((x, 45.0, z)) for x in xs] for z in zs]
    nx, nz = len(xs), len(zs)
    for j in range(nz - 1):
        for i in range(nx - 1):
            bm.faces.new((front_[j][i], front_[j][i + 1], front_[j + 1][i + 1], front_[j + 1][i]))
            bm.faces.new((back[j][i], back[j + 1][i], back[j + 1][i + 1], back[j][i + 1]))
    for i in range(nx - 1):
        bm.faces.new((front_[0][i], back[0][i], back[0][i + 1], front_[0][i + 1]))
        bm.faces.new((front_[-1][i], front_[-1][i + 1], back[-1][i + 1], back[-1][i]))
    for j in range(nz - 1):
        bm.faces.new((front_[j][0], front_[j + 1][0], back[j + 1][0], back[j][0]))
        bm.faces.new((front_[j][-1], back[j][-1], back[j + 1][-1], front_[j + 1][-1]))
    return part("break", bm, INSIDE)


stern_body = body.copy()
stern_body.data = body.data.copy()
bpy.context.collection.objects.link(stern_body)
stern_body.name = "BodyStern"
PARTS.append({"obj": stern_body, "closed": True, "collide": True, "sect": "stern"})
body.name = "BodyBow"
PARTS[0]["collide"] = True
cutter = break_cutter()
apply_boolean(body, cutter, "INTERSECT")
apply_boolean(stern_body, cutter, "DIFFERENCE")
forget(cutter)


# ============================================================================================
# The smaller parts
# ============================================================================================
def funnel_rule(top):
    return lambda f: 1 if f.calc_center_median().z > top else 0


def stump(cy, top, sect):
    """A funnel torn off low: an open elliptical collar, jagged, down to its shaft."""
    jag = lambda k: top + (0.55 if k % 3 == 0 else 0.15 if k % 3 == 1 else 0.35) + rng.uniform(-0.1, 0.1)
    tops = [jag(k) for k in range(16)]
    outer0 = ell(0.0, cy, BOAT - 0.15, FUN_AX, FUN_AY)
    outer1 = [Vector((p.x, p.y, tops[k])) for k, p in enumerate(ell(0.0, cy, 0.0, FUN_AX, FUN_AY))]
    inner1 = [Vector((p.x, p.y, tops[k] - 0.05)) for k, p in enumerate(ell(0.0, cy, 0.0, FUN_AX - 0.3, FUN_AY - 0.3))]
    inner0 = ell(0.0, cy, BOAT - 0.15, FUN_AX - 0.3, FUN_AY - 0.3)
    part("stump", loft([outer0, outer1, inner1, inner0], cyclic=True), FUNNEL, collide=True, sect=sect)
    # the casing round its foot
    part("casing", loft([ell(0.0, cy, BOAT - 0.1, FUN_AX + 0.18, FUN_AY + 0.18), ell(0.0, cy, BOAT + 0.45, FUN_AX + 0.12, FUN_AY + 0.12),
                         ell(0.0, cy, BOAT + 0.45, FUN_AX - 0.3, FUN_AY - 0.3), ell(0.0, cy, BOAT - 0.1, FUN_AX - 0.3, FUN_AY - 0.3)], cyclic=True),
         IRON, collide=True, sect=sect)


stump(FUNNELS[1], BOAT + 0.6, "bow")
stump(FUNNELS[4], BOAT + 0.5, "stern")

# the second funnel, still standing, raked aft; its top black
rake = math.tan(math.radians(7.0))
cy = FUNNELS[2]
height = FUN_TOP - BOAT
rings_ = [ell(0.0, cy, BOAT - 0.15, FUN_AX, FUN_AY), ell(0.0, cy, FUN_TOP, FUN_AX, FUN_AY, shift=-height * rake),
          ell(0.0, cy, FUN_TOP, FUN_AX - 0.22, FUN_AY - 0.22, shift=-height * rake), ell(0.0, cy, FUN_TOP - 1.2, FUN_AX - 0.22, FUN_AY - 0.22, shift=-(height - 1.2) * rake)]
part("funnel2", loft(rings_), [FUNNEL, HULL], collide=True, rule=funnel_rule(FUN_TOP - 1.5), sect="bow")
part("casing", loft([ell(0.0, cy, BOAT - 0.1, FUN_AX + 0.18, FUN_AY + 0.18), ell(0.0, cy, BOAT + 0.5, FUN_AX + 0.1, FUN_AY + 0.1)]), IRON, collide=True, sect="bow")
# a band round it, and the steam pipe up its forward side
for z in (12.6, 15.3):
    part("band", loft([ell(0.0, cy, z, FUN_AX + 0.04, FUN_AY + 0.04, shift=-(z - BOAT) * rake), ell(0.0, cy, z + 0.12, FUN_AX + 0.04, FUN_AY + 0.04, shift=-(z + 0.12 - BOAT) * rake)]), IRON, sect="bow")
cyl(IRON, (0.0, cy + FUN_AY + 0.12, BOAT), (0.0, cy + FUN_AY + 0.12 - (FUN_TOP + 0.4 - BOAT) * rake, FUN_TOP + 0.4), 0.11, sides=6, sect="bow")

# the third funnel: a low stump, and the funnel fallen to port across the deck and over the side
cy = FUNNELS[3]
tops = [BOAT + 0.5 + (0.45 if k % 2 else 0.1) + rng.uniform(-0.1, 0.1) for k in range(16)]
part("stump3", loft([ell(0.0, cy, BOAT - 0.15, FUN_AX, FUN_AY), [Vector((p.x, p.y, tops[k])) for k, p in enumerate(ell(0.0, cy, 0.0, FUN_AX, FUN_AY))],
                     [Vector((p.x, p.y, tops[k] - 0.05)) for k, p in enumerate(ell(0.0, cy, 0.0, FUN_AX - 0.25, FUN_AY - 0.25))],
                     ell(0.0, cy, BOAT + 0.2, FUN_AX - 0.25, FUN_AY - 0.25)]), FUNNEL, collide=True, sect="bow")


def fallen(p0, p1, wide, tall, wall=0.22, sides=16, black=False):
    p0 = Vector(p0)
    p1 = Vector(p1)
    axis = (p1 - p0).normalized()
    u = axis.cross(Vector((0.0, 0.0, 1.0))).normalized()
    v = u.cross(axis).normalized()
    if v.z < 0:
        v = -v
    o0 = circle(p0, u, v, 1.0, sides, wide, tall)
    o1 = circle(p1, u, v, 1.0, sides, wide, tall)
    i1 = circle(p1, u, v, 1.0, sides, wide - wall, tall - wall)
    i0 = circle(p0, u, v, 1.0, sides, wide - wall, tall - wall)
    length = (p1 - p0).length
    # (its top end black, as the funnels' tops were)
    rule = (lambda f: 1 if (f.calc_center_median() - p0).dot(axis) > length - 1.4 else 0) if black else None
    return part("fallen", loft([o0, o1, i1, i0], cyclic=True), [FUNNEL, HULL], collide=True, sect="bow", rule=rule)


fallen((-1.1, -2.6, 11.0), (-3.5, -1.1, 10.95), FUN_AY, 1.05)
fallen((-3.25, -1.25, 10.95), (-6.0, 0.3, 8.0), FUN_AY - 0.05, 1.0, black=True)

# the skylight over the grand staircase: a raised coaming round the opening, and the bare iron ribs of
# its dome (the glass long gone)
dx, dy, dr = DOME
part("coaming", loft([ell(dx, dy, BOAT - 0.1, dr + 0.3, dr + 0.3, 20), ell(dx, dy, BOAT + 0.45, dr + 0.3, dr + 0.3, 20),
                      ell(dx, dy, BOAT + 0.45, dr + 0.02, dr + 0.02, 20), ell(dx, dy, BOAT - 0.1, dr + 0.02, dr + 0.02, 20)], cyclic=True), WHITE, collide=True, sect="bow")
for k in range(8):
    a = math.tau * k / 8
    c, s = math.cos(a), math.sin(a)
    rod(IRON, [(dx + c * (dr + 0.15), dy + s * (dr + 0.15), BOAT + 0.45), (dx + c * 1.9, dy + s * 1.9, BOAT + 1.1), (dx + c * 1.1, dy + s * 1.1, BOAT + 1.75), (dx + c * 0.1, dy + s * 0.1, BOAT + 2.0)], 0.06, sect="bow")
    if k % 2 == 0:
        a2 = math.tau * (k + 1) / 8
        rod(IRON, [(dx + c * 1.75, dy + s * 1.75, BOAT + 1.35), (dx + math.cos(a2) * 1.75, dy + math.sin(a2) * 1.75, BOAT + 1.35)], 0.05, sect="bow")
cyl(BRONZE, (dx, dy, BOAT + 1.95), (dx, dy, BOAT + 2.25), 0.14, 0.05, sides=6, sect="bow")


def pane(corners, thick=0.035):
    """A pane of the dome's clouded glass: a thin plate on four corners."""
    c = [Vector(p) for p in corners]
    n = (c[1] - c[0]).cross(c[3] - c[0]).normalized()
    part("pane", loft([c, [p + n * thick for p in c]]), GLASS, sect="bow")


# the glass, clouded, a pane gone here and there (and on the +X side, where the way in is, all gone)
for k in range(8):
    if k in (0, 3, 7):
        continue
    a0 = math.tau * k / 8
    a1 = math.tau * (k + 1) / 8

    def on(a, r, h):
        return (dx + math.cos(a) * r, dy + math.sin(a) * r, BOAT + h)
    pane([on(a0, dr + 0.12, 0.47), on(a1, dr + 0.12, 0.47), on(a1, 1.84, 1.12), on(a0, 1.84, 1.12)])
    if k in (1, 4, 5):
        pane([on(a0, 1.84, 1.12), on(a1, 1.84, 1.12), on(a1, 1.12, 1.73), on(a0, 1.12, 1.73)])

# the grand staircase: one wide flight from the saloon's floor up to the gallery under the dome
foot, top_, steps = STAIR
run_ = (top_ - foot) / steps
rise = (PROM - 4.0) / steps
outline = [(foot, 4.0)]
for k in range(steps):
    outline += [(foot + k * run_, 4.0 + (k + 1) * rise), (foot + (k + 1) * run_, 4.0 + (k + 1) * rise)]
outline += [(top_ + 0.05, 4.0)]
prism([PANEL, DECKING], outline, "yz", -1.3, 1.3, collide=True, sect="bow", rule=lambda f: 0)
box(PANEL, -3.05, 3.05, top_, -4.4, 7.0, PROM, collide=True, sect="bow")    # the gallery
for side in (-1.0, 1.0):
    # balustrade up each side, the newel post at its foot with a lamp, the gallery's rail
    rod(BRONZE, [(side * 1.35, foot + 0.15, 5.0), (side * 1.35, top_ - 0.05, 8.15)], 0.05, sect="bow")
    for k in range(1, 5):
        y = foot + (top_ - foot) * k / 5.0
        z = 4.0 + (y - foot) / (top_ - foot) * (PROM - 4.0)
        box(PANEL, side * 1.35 - 0.04, side * 1.35 + 0.04, y - 0.04, y + 0.04, z, z + 0.85, sect="bow")
    box(PANEL, side * 1.35 - 0.17, side * 1.35 + 0.17, foot - 0.17, foot + 0.17, 4.0, 5.25, sect="bow")
    cyl(BRONZE, (side * 1.35, foot, 5.25), (side * 1.35, foot, 5.55), 0.16, 0.08, sides=6, sect="bow")
    rod(BRONZE, [(side * 1.4, top_ + 0.05, 8.15), (side * 2.95, top_ + 0.05, 8.15)], 0.05, sect="bow")
    for x in (1.9, 2.5):
        box(PANEL, side * x - 0.04, side * x + 0.04, top_, top_ + 0.08, PROM, 8.15, sect="bow")
    cyl(PANEL, (side * 2.2, top_ + 0.3, 4.0), (side * 2.2, top_ + 0.3, 7.0), 0.18, sides=8, sect="bow")

# boilers in the boiler room (port side, clear of the way from the tear to the shaft)
for y0, y1 in ((2.6, 5.4), (6.0, 8.8)):
    cyl(IRON, (-1.75, y0, 2.55), (-1.75, y1, 2.55), 1.15, sides=12, collide=True, sect="bow")
    cyl(IRON, (-1.75, y1, 2.55), (-1.75, y1 + 0.08, 2.55), 0.6, sides=8, sect="bow")

# the engines in the stern, either side of the fourth funnel's shaft
for side in (-1.0, 1.0):
    box(IRON, min(side * 1.2, side * 2.2), max(side * 1.2, side * 2.2), -17.4, -12.6, 2.15, 4.4, collide=True, sect="stern")
    for y in (-16.7, -15.0, -13.3):
        cyl(IRON, (side * 1.7, y, 4.3), (side * 1.7, y, 5.3), 0.5, sides=8, collide=True, sect="stern")

# --- The bridge, collapsed: its back wall, stubs of its sides, the wheelhouse roof sagging to the deck,
# the telemotor standing alone, the wings (one bent down)
box(WHITE, -3.0, 3.0, 12.4, 12.7, BOAT - 0.05, 12.0, collide=True, sect="bow")
box(WHITE, 2.7, 3.0, 12.7, 13.5, BOAT - 0.05, 11.4, sect="bow")
box(WHITE, -3.0, -2.7, 12.7, 13.1, BOAT - 0.05, 10.9, sect="bow")
roof_tilt = -math.atan2(1.7, 2.0)
plate([WHITE, DECKING], (6.4, 2.62, 0.18), Matrix.Translation((0.0, 13.4, 11.15)) @ Matrix.Rotation(roof_tilt, 4, "X") @ Matrix.Rotation(0.05, 4, "Y"),
      collide=True, sect="bow", rule=lambda f: 1 if f.normal.z > 0.5 else 0)
box(DECKING, 3.0, 4.3, 13.6, 14.4, 9.72, 9.92, sect="bow")
plate(DECKING, (1.3, 0.8, 0.2), Matrix.Translation((-3.6, 14.0, 9.55)) @ Matrix.Rotation(math.radians(28.0), 4, "Y"), sect="bow")
cyl(BRONZE, (0.0, 13.3, BOAT), (0.0, 13.3, 10.85), 0.16, 0.12, sides=8, sect="bow")
cyl(BRONZE, (0.0, 13.12, 10.8), (0.0, 13.04, 10.8), 0.38, sides=12, sect="bow")

# deckhouses on the boat deck
for x0, x1, y0, y1, z1, sect in ((-2.3, 2.3, 5.3, 8.9, 11.7, "bow"), (-2.0, 2.0, -0.9, 1.5, 11.5, "bow"), (-2.0, 2.0, -13.3, -11.2, 11.6, "stern")):
    box([WHITE, DECKING], x0, x1, y0, y1, BOAT - 0.05, z1, collide=True, sect=sect, rule=lambda f: 1 if on_top(f) else 0)
    for side in (-1.0, 1.0):
        for k in range(3):
            y = y0 + (y1 - y0) * (k + 0.5) / 3.0
            decal(DARK, (side * 2.0, y, z1 - 0.8), (side, 0.0, 0.0), rect(0.55, 0.6), sect=sect)

# --- Masts: the foremast still standing on the forecastle (as in the concept art), broken short,
# leaning a little aft, its crow's nest, weed hanging from its stays; its top lies on the sand off
# the port bow. A stub of the mainmast on the stern.
mast0 = Vector((0.2, 19.6, fc_top(19.6) - 0.05))
mast1 = Vector((0.05, 18.9, 15.3))
cyl(IRON, mast0, mast1, 0.28, 0.2, sides=8, collide=True, sect="bow")
axis = (mast1 - mast0).normalized()
# (the break: a jagged spike above the last whole piece)
cone(IRON, mast1 + axis * 0.55 + Vector((0.08, 0.0, 0.0)), 0.6, 0.17, sect="bow")
nest = mast0.lerp(mast1, 0.8)
cyl(IRON, nest - axis * 0.35, nest + axis * 0.35, 0.48, 0.52, sides=8, sect="bow")
STAY_TOP = mast0.lerp(mast1, 0.95)
STAYS = [(0.0, 29.75, fc_top(29.75) + 0.15)] + [(side * (deck_edge(20.2) - 0.06), 20.2, fc_top(20.2)) for side in (-1.0, 1.0)] + [(0.0, 14.5, 10.5)]
for end in STAYS:
    rod(IRON, [STAY_TOP, Vector(end)], 0.035, sect="bow")
    for k in range(1, 9):
        at = STAY_TOP.lerp(Vector(end), k / 9.0)
        if rng.random() < 0.75:
            cone(MOSS, at, rng.uniform(0.3, 1.2), 0.1, sect="bow")
cyl(IRON, to_bow @ Vector((-6.6, 19.0, 0.25)), to_bow @ Vector((-7.6, 13.8, 0.25)), 0.22, 0.15, sides=8, sect="bow")
cyl(IRON, (0.0, -21.0, DECK - 0.05), (0.05, -21.0, 9.4), 0.25, 0.2, sides=8, collide=True, sect="stern")

# --- Hatch coamings (their covers gone; one lies askew on the deck)
def coaming(x, y0, y1, z0, h):
    box(IRON, -x - 0.15, -x, y0 - 0.15, y1 + 0.15, z0, z0 + h)
    box(IRON, x, x + 0.15, y0 - 0.15, y1 + 0.15, z0, z0 + h)
    box(IRON, -x, x, y0 - 0.15, y0, z0, z0 + h)
    box(IRON, -x, x, y1, y1 + 0.15, z0, z0 + h)


coaming(1.5, 14.7, 17.3, DECK - 0.05, 0.55)
coaming(1.2, 20.3, 22.3, fc_top(20.3) - 0.05, 0.5)
plate(DECKING, (1.5, 1.2, 0.12), Matrix.Translation((-2.35, 18.2, 7.12)) @ Matrix.Rotation(math.radians(25.0), 4, "Z") @ Matrix.Rotation(math.radians(9.0), 4, "X"), sect="bow")

# --- The forecastle: capstans, bollards, chains to the hawse pipes, the anchors in them, the bow rail
for side in (-1.0, 1.0):
    z = fc_top(26.0)
    cyl(IRON, (side * 1.0, 26.0, z - 0.05), (side * 1.0, 26.0, z + 0.55), 0.32, sides=10)
    cyl(BRONZE, (side * 1.0, 26.0, z + 0.55), (side * 1.0, 26.0, z + 0.68), 0.42, 0.36, sides=10)
    hawse = Vector((side * (deck_edge(27.7) - 0.35), 27.7, fc_top(27.7) + 0.05))
    rod(IRON, [(side * 1.0, 26.25, z + 0.3), (side * 0.9, 26.9, fc_top(26.9) + 0.08), hawse], 0.1, sides=4)
    for y in (23.2, 23.8):
        cyl(IRON, (side * 1.3, y, fc_top(y) - 0.05), (side * 1.3, y, fc_top(y) + 0.45), 0.15, sides=8)
    # the anchor hanging in its hawse pipe against the bow
    ya, za = 27.0, 6.3
    n = hull_normal(side, ya, za)
    decal(DARK, (side * hull_x(ya, za + 0.85), ya, za + 0.85), n, [(math.cos(math.tau * k / 8) * 0.34, math.sin(math.tau * k / 8) * 0.26) for k in range(8)], sect="bow")
    flukes = [(-0.62, -0.85), (0.62, -0.85), (0.72, -0.45), (0.38, -0.66), (0.0, -0.56), (-0.38, -0.66), (-0.72, -0.45)]
    if side < 0.0:
        at = Vector((side * hull_x(ya, za), ya, za)) + n * 0.14
        box(IRON, at.x - 0.11, at.x + 0.11, ya - 0.11, ya + 0.11, za - 0.85, za + 0.75, sect="bow")
        prism(IRON, [(ya + u, za + v - 0.15) for u, v in flukes], "yz", at.x - 0.1, at.x + 0.1, sect="bow")
    else:
        # (the starboard anchor run out of its hawse: hanging low against the bow on its chain, as in
        # the concept art; half as big again)
        ring_at = Vector((side * (hull_x(25.6, 3.4) + 0.35), 25.6, 3.4))
        top = Vector((side * hull_x(ya, za + 0.85), ya, za + 0.85)) + n * 0.12
        x = ring_at.x
        box(IRON, x - 0.16, x + 0.16, 25.44, 25.76, 0.95, 3.35, sect="bow")
        prism(IRON, [(25.6 + u * 1.5, 1.6 + v * 1.5) for u, v in flukes], "yz", x - 0.15, x + 0.15, sect="bow")
        cyl(IRON, (x - 0.05, 25.6, 3.55), (x + 0.05, 25.6, 3.55), 0.28, sides=8, sect="bow")
        # the chain: links standing flat and edge on in turn, sagging from the hawse to the ring
        steps = 18
        for k in range(steps):
            t = (k + 0.5) / steps
            here = top.lerp(ring_at + Vector((0.0, 0.0, 0.25)), t) + Vector((side * 0.25 * math.sin(math.pi * t), 0.0, 0.0))
            ahead = top.lerp(ring_at, t + 0.05) - top.lerp(ring_at, t)
            m = Matrix.Translation(here) @ ahead.to_track_quat("Z", "Y").to_matrix().to_4x4() @ Matrix.Rotation(math.pi * 0.5 * (k % 2), 4, "Z")
            plate(IRON, (0.3, 0.1, 0.42), m, sect="bow")
        cone(RUST, ring_at + Vector((0.0, 0.0, -0.05)), 0.9, 0.09, sect="bow")
    # the bow rail, still standing (the famous one)
    ys = [22.0 + k * 1.0 for k in range(8)] + [29.6]
    for y in ys:
        x = side * (deck_edge(y) - 0.08)
        cyl(IRON, (x, y, fc_top(y) - 0.02), (x, y, fc_top(y) + 1.0), 0.03, sides=4, sect="bow")
    for h in (0.5, 1.0):
        rod(IRON, [(side * (deck_edge(y) - 0.08), y, fc_top(y) + h) for y in ys] + [(0.0, 29.85, fc_top(29.85) + h)], 0.035, sect="bow")
    # rusticles hanging off the forecastle's edge
    y = 19.4
    while y < 29.5:
        cone(IRON, (side * (deck_edge(y) + 0.02), y, fc_top(y) - 0.04), rng.uniform(0.3, 1.1), 0.075, sect="bow")
        y += rng.uniform(0.45, 0.9)
for side in (-1.0, 1.0):
    for y in (-24.0, -24.6):
        cyl(IRON, (side * 1.8, y, poop_top(y) - 0.05), (side * 1.8, y, poop_top(y) + 0.45), 0.15, sides=8, sect="stern")

# --- The boat deck: empty davits (some bent), cowl ventilators, what is left of the railings
def davit(side, y, bend, sect):
    box(IRON, side * 3.05 - 0.17, side * 3.05 + 0.17, y - 0.17, y + 0.17, BOAT - 0.05, BOAT + 0.4, sect=sect)
    arm = [Vector((0.0, 0.0, 0.3)), Vector((0.0, 0.0, 1.3)), Vector((0.35, 0.0, 2.0)), Vector((0.9, 0.0, 1.95)), Vector((1.0, 0.0, 1.5))]
    turn = Matrix.Rotation(-side * bend, 3, "Y")
    rod(IRON, [Vector((side * 3.05, y, BOAT)) + turn @ Vector((side * p.x, p.y, p.z)) for p in arm], 0.075, sect=sect)
    tip = Vector((side * 3.05, y, BOAT)) + turn @ Vector((side * arm[-1].x, 0.0, arm[-1].z))
    cone(MOSS, tip, rng.uniform(0.5, 1.4), 0.1, sect=sect)
    elbow = Vector((side * 3.05, y, BOAT)) + turn @ Vector((side * arm[2].x, 0.0, arm[2].z))
    cone(IRON, elbow, rng.uniform(0.2, 0.6), 0.06, sect=sect)


for y, bend in ((9.0, 0.0), (7.2, 0.5), (1.6, 0.0), (-0.2, 0.0)):
    davit(1.0, y, bend, "bow")
for y, bend in ((9.0, 0.0), (7.2, 0.0), (1.6, 0.9), (-0.2, 0.0)):
    davit(-1.0, y, bend, "bow")
for y, bend in ((-13.6, 0.0), (-17.2, 0.4)):
    davit(1.0, y, bend, "stern")
    davit(-1.0, y, 0.0, "stern")


def vent(x, y, face, height=1.1, sect=None):
    cyl(WHITE, (x, y, BOAT - 0.05), (x, y, BOAT + height), 0.2, sides=8, sect=sect)
    d = Vector((math.cos(face), math.sin(face), 0.0))
    top = Vector((x, y, BOAT + height - 0.05))
    cyl(WHITE, top, top + d * 0.5 + Vector((0.0, 0.0, 0.32)), 0.24, 0.46, sides=8, sect=sect)


vent(2.4, 5.0, math.pi * 0.5, sect="bow")
vent(-2.4, 5.4, math.pi * 0.6, sect="bow")
vent(2.5, -1.9, -math.pi * 0.5, sect="bow")
vent(-2.6, -5.0, math.pi * 0.45, 0.8, sect="bow")
vent(2.0, -12.0, math.pi * 0.5, sect="stern")
vent(-2.2, -17.6, -math.pi * 0.4, sect="stern")
# one lying where it fell
cyl(WHITE, (1.3, 9.1, BOAT + 0.2), (1.6, 7.9, BOAT + 0.2), 0.2, sides=8, sect="bow")
cyl(WHITE, (1.6, 7.9, BOAT + 0.25), (1.85, 7.4, BOAT + 0.5), 0.24, 0.45, sides=8, sect="bow")


def railing(side, y0, y1, droop, sect):
    turn = Matrix.Rotation(-side * droop, 3, "Y")
    base = Vector((side * 3.2, 0.0, BOAT))
    count = max(2, int(abs(y1 - y0) / 1.2) + 1)
    ys = [y0 + (y1 - y0) * k / (count - 1) for k in range(count)]
    for y in ys:
        cyl(IRON, Vector((side * 3.2, y, BOAT - 0.02)), Vector((side * 3.2, y, BOAT)) + turn @ Vector((0.0, 0.0, 1.0)), 0.03, sides=4, sect=sect)
    for h in (0.5, 1.0):
        rod(IRON, [Vector((side * 3.2, y, BOAT)) + turn @ Vector((0.0, 0.0, h)) for y in ys], 0.03, sect=sect)
    # (draped with weed, rusticles hanging)
    for a, b in zip(ys, ys[1:]):
        for t in (0.3, 0.75):
            at = Vector((side * 3.2, a + (b - a) * t, BOAT)) + turn @ Vector((0.0, 0.0, 0.98))
            cone(MOSS if rng.random() < 0.6 else IRON, at, rng.uniform(0.3, 1.0), 0.08, sect=sect)


railing(1.0, 1.8, 5.4, 0.0, "bow")
railing(-1.0, 8.6, 11.4, 0.7, "bow")
railing(1.0, -5.6, -8.4, 0.25, "bow")
railing(1.0, -17.0, -14.2, 0.35, "stern")
railing(-1.0, -0.6, 4.6, 0.45, "bow")
railing(1.0, 9.4, 11.8, 0.15, "bow")
railing(-1.0, -9.2, -6.2, 0.9, "bow")
railing(-1.0, -17.4, -15.0, 0.2, "stern")

# weed hanging in green drips off the deck edges (the concept art's), and promenade shutters fallen
# open below their windows
for side in (-1.0, 1.0):
    y = -9.0
    while y < 13.4:
        cone(MOSS, (side * (SUPER + 0.03), y, BOAT - 0.02), rng.uniform(0.4, 1.5), 0.13, sect="bow")
        y += rng.uniform(0.7, 2.0)
    y = 19.6
    while y < 29.0:
        cone(MOSS, (side * (deck_edge(y) + 0.03), y, fc_top(y) - 0.02), rng.uniform(0.5, 1.8), 0.14, sect="bow")
        y += rng.uniform(0.9, 2.2)
    y = -17.6
    while y < -12.0:
        cone(MOSS, (side * (SUPER + 0.03), y, BOAT - 0.02), rng.uniform(0.4, 1.3), 0.12, sect="stern")
        y += rng.uniform(0.9, 2.0)
for y in WINDOWS[::2]:
    hinge = Vector((SUPER + 0.02, y, 7.9))
    drop = Vector((math.sin(math.radians(35.0)), 0.0, -math.cos(math.radians(35.0))))
    plate(HULL, (0.06, 1.35, 0.85), Matrix.Translation(hinge + drop * 0.44) @ Matrix.Rotation(math.radians(-35.0), 4, "Y"), sect="bow")
# the forecastle's white strake has its own row of portholes
for side in (-1.0, 1.0):
    y = 19.8
    while y < 28.5:
        n = hull_normal(side, y, DECK)
        n = Vector((n.x, n.y, 0.0)).normalized()
        c = Vector((side * (deck_edge(y) - 0.01), y, 7.8))
        decal(DARK, c, n, octagon(0.2), 0.014)
        annulus(BRONZE, c, n, 0.2, 0.27, 0.009)
        y += 1.4

# rusticles off the boat deck's edges and the sagging roof
for side in (-1.0, 1.0):
    y = -8.6
    while y < 13.0:
        cone(IRON, (side * (SUPER + 0.02), y, BOAT - 0.04), rng.uniform(0.25, 0.8), 0.065, sect="bow")
        y += rng.uniform(1.0, 1.8)
for x in (-2.4, -1.1, 0.4, 1.6, 2.7):
    cone(IRON, (x, 14.45, 10.2), rng.uniform(0.3, 0.7), 0.06, sect="bow")

# --- The stern: sternpost, keel bar, rudder (turned), the shaft's bossing and a three-bladed propeller
box(ANTIFOUL, -0.17, 0.17, -27.75, -27.45, 0.0, 3.75, sect="stern")
box(ANTIFOUL, -0.17, 0.17, -27.75, -20.0, 0.0, 0.32, sect="stern")
rudder = [(-27.85, 0.3), (-29.2, 0.3), (-29.75, 1.4), (-29.65, 3.3), (-27.85, 3.95)]
prism(ANTIFOUL, rudder, "yz", -0.2, 0.2, collide=True, sect="stern")
r = PARTS[-1]["obj"]
r.data.transform(Matrix.Translation((0.0, -27.85, 0.0)) @ Matrix.Rotation(math.radians(18.0), 4, "Z") @ Matrix.Translation((0.0, 27.85, 0.0)))
HUB = Vector((0.0, -26.5, 1.9))
cyl(ANTIFOUL, (0.0, -25.0, 1.9), (0.0, -26.1, 1.9), 0.55, 0.4, sides=10, sect="stern")
cyl(BRONZE, (0.0, -26.05, 1.9), (0.0, -26.95, 1.9), 0.4, 0.28, sides=10, collide=True, sect="stern")
for k in range(3):
    a = math.tau * k / 3 + 0.5
    blade = [(0.3, -0.25), (0.8, -0.5), (1.25, -0.42), (1.48, 0.0), (1.3, 0.4), (0.8, 0.5), (0.3, 0.28)]
    bm = loft([[(u, v, -0.06) for u, v in blade], [(u, v, 0.06) for u, v in blade]])
    # (radial along x, across the disc along y, along the shaft along z; pitched; turned round the hub;
    # the shaft runs along the ship's y)
    m = (Matrix.Translation(HUB) @ Matrix.Rotation(-math.pi / 2, 4, "X") @ Matrix.Rotation(a, 4, "Z") @ Matrix.Rotation(math.radians(32.0), 4, "X"))
    part("blade", bm, BRONZE, matrix=m, sect="stern")
# the docking bridge across the poop
box(WHITE, -3.9, 3.9, -27.55, -26.95, 10.2, 10.42, collide=True, sect="stern")
for x in (-0.9, 0.9):
    box(WHITE, x - 0.1, x + 0.1, -27.35, -27.15, poop_top(-27.25) - 0.05, 10.2, sect="stern")

# --- The tear's plating, bent in and out; the break: a deck torn down from each half
for (y, z, ry, rz, out) in ((5.2, 4.6, 0.5, 0.0, 1.0), (9.9, 2.4, -0.6, 0.3, -1.0), (8.6, 5.15, 0.2, -0.4, 1.0), (6.4, 1.65, -0.3, 0.6, -1.0)):
    m = Matrix.Translation((3.45 + 0.35 * out, y, z)) @ Matrix.Rotation(rz, 4, "X") @ Matrix.Rotation(ry, 4, "Z")
    plate(HULL, (0.08, 1.3, 0.8), m, sect="bow")
plate(DECKING, (2.6, 2.4, 0.22), Matrix.Translation((2.0, -11.6, 8.9)) @ Matrix.Rotation(math.radians(55.0), 4, "X"), sect="bow")
plate(DECKING, (2.2, 2.0, 0.2), Matrix.Translation((-1.2, -9.0, 8.7)) @ Matrix.Rotation(math.radians(-48.0), 4, "X"), sect="stern")

# --- Painted portholes and windows where nothing is behind them
for side in (-1.0, 1.0):
    for z in (4.6, 5.9):
        y = -24.5
        while y < 27.5:
            ok = hull_x(y, z) > 1.0 and abs(y - BREAK) > 2.2
            if side > 0 and abs(y - 7.5) < 3.0 and z < 5.6:
                ok = False
            if side > 0 and 4.9 < y < 10.1:
                ok = False
            if side > 0 and -9.7 < y < -5.1:
                ok = False
            if z > 5.0 and any(abs(y - q) < 0.7 for q in REAL[side]):
                ok = False
            if ok:
                n = hull_normal(side, y, z)
                c = Vector((side * hull_x(y, z), y, z))
                decal(DARK, c, n, octagon(0.22), 0.014)
                annulus(BRONZE, c, n, 0.22, 0.3, 0.009)
            y += 1.5
    for y in REAL[side]:
        if side > 0 and -9.7 < y < -5.1:
            continue
        n = hull_normal(side, y, 5.9)
        annulus(BRONZE, Vector((side * hull_x(y, 5.9), y, 5.9)), n, 0.25, 0.33, 0.009)
# the port side's promenade windows (a cabin block behind: painted), the stern's, the front's
for y in WINDOWS:
    decal(DARK, (-SUPER, y, 8.55), (-1.0, 0.0, 0.0), rect(1.5, 1.3))
for side in (-1.0, 1.0):
    for y in (-14.7, -16.8):
        decal(DARK, (side * SUPER, y, 8.55), (side, 0.0, 0.0), rect(1.4, 1.2), sect="stern")
for x in (-2.2, -0.8, 0.8, 2.2):
    decal(DARK, (x, 14.78 - abs(x) * 0.12, 8.4), (0.0, 1.0, 0.0), rect(0.9, 1.1), sect="bow")


# --- Rust running down from every porthole, window and scupper (the concept art's streaks)
def run_down(c, n, top_w, length, lift=0.011, sect=None):
    """A tapering rust run painted down a surface from a point."""
    middle = Vector(c) + Vector((0.0, 0.0, -length * 0.5))
    decal(RUST, middle, n, [(-top_w * 0.4, length * 0.5), (top_w * 0.4, length * 0.5), (top_w * 0.3, 0.0), (top_w * 0.15, -length * 0.5), (-top_w * 0.2, -length * 0.5), (-top_w * 0.32, 0.0)], lift, sect=sect)


for side in (-1.0, 1.0):
    for z in (4.6, 5.9):
        y = -24.5
        while y < 27.5:
            ok = hull_x(y, z) > 1.0 and abs(y - BREAK) > 2.2 and not (side > 0 and 4.9 < y < 10.1) and not (side > 0 and -9.6 < y < -5.2)
            if ok and rng.random() < 0.8:
                n = hull_normal(side, y, z)
                length = rng.uniform(0.6, 2.2)
                run_down(Vector((side * hull_x(y, z - 0.3 - length * 0.5), y, z - 0.3)), n, 0.24, length)
            y += 1.5
    for y in REAL[side]:
        if side > 0 and -9.7 < y < -5.1:
            continue
        n = hull_normal(side, y, 5.4)
        run_down(Vector((side * hull_x(y, 5.0), y, 5.6)), n, 0.26, rng.uniform(0.8, 2.4))
    # scuppers along the deck edge, each with its run
    y = -23.0
    while y < 26.0:
        if abs(y - BREAK) > 2.0 and hull_x(y, 6.8) > 1.2 and not (side > 0 and -9.6 < y < -5.2):
            n = hull_normal(side, y, 6.6)
            c = Vector((side * hull_x(y, 6.75), y, 6.75))
            decal(DARK, c, n, rect(0.3, 0.14), 0.014)
            run_down(c + Vector((0.0, 0.0, -0.07)), n, 0.3, rng.uniform(1.0, 3.2))
        y += rng.uniform(2.0, 3.2)
    # under the promenade's windows (real on the starboard side, painted on the port)
    for y in WINDOWS:
        for k in range(2):
            run_down(Vector((side * (SUPER + 0.004), y + rng.uniform(-0.6, 0.6), 7.88)), (side, 0.0, 0.0), 0.3, rng.uniform(0.6, 1.6), 0.016)

# --- A second tier of white houses on the boat deck (the concept's), its windows painted
box([WHITE, DECKING], -1.75, 1.75, 5.8, 8.4, 11.65, 13.3, collide=True, sect="bow", rule=lambda f: 1 if on_top(f) else 0)
for side in (-1.0, 1.0):
    for y in (6.3, 7.1, 7.9):
        decal(DARK, (side * 1.75, y, 12.5), (side, 0.0, 0.0), rect(0.5, 0.55), sect="bow")
        run_down(Vector((side * 1.754, y, 12.2)), (side, 0.0, 0.0), 0.25, rng.uniform(0.5, 1.2), 0.016, sect="bow")
for x in (-0.9, 0.0, 0.9):
    decal(DARK, (x, 8.4, 12.5), (0.0, 1.0, 0.0), rect(0.5, 0.55), sect="bow")
for side in (-1.0, 1.0):
    y = 5.9
    while y < 8.4:
        cone(MOSS, (side * 1.78, y, 13.28), rng.uniform(0.4, 1.1), 0.1, sect="bow")
        y += rng.uniform(0.5, 1.0)

# --- The break: the hull's frames standing bare beyond the torn plating, some bent; plates peeled out
def frame_at(y, sect, bend):
    for side in (-1.0, 1.0):
        pts = []
        for x, z in ZS[3:]:
            zz = keel(y) + z * (DECK - keel(y)) / DECK
            pts.append(Vector((side * (x * fine(y, zz) - 0.22), y, zz)))
        pts += [Vector((side * (SUPER - 0.15), y, 7.6)), Vector((side * (SUPER - 0.15), y, BOAT - 0.15))]
        # (bent: the upper part dragged along the ship and outwards)
        pts = [p + Vector((side * bend * 0.3 * max(0.0, p.z - 4.0) / 6.0, bend * max(0.0, p.z - 4.0) / 6.0, 0.0)) for p in pts]
        rod(INSIDE, pts, 0.09, sect=sect)


for y, bend in ((-11.0, 0.0), (-11.8, -0.7), (-12.5, -1.4)):
    frame_at(y, "bow", bend)
for y, bend in ((-9.6, 0.0), (-8.9, 0.6), (-8.2, 1.2)):
    frame_at(y, "stern", bend)
for (x, y, z, turn, sect) in ((3.65, -10.9, 3.0, 0.5, "bow"), (-3.65, -11.2, 5.0, -0.45, "bow"), (3.6, -11.4, 8.4, 0.7, "bow"),
                              (3.65, -9.5, 2.6, -0.5, "stern"), (-3.65, -9.2, 4.4, 0.6, "stern")):
    plate(HULL, (0.08, 1.8, 1.4), Matrix.Translation((x, y, z)) @ Matrix.Rotation(turn, 4, "Z") @ Matrix.Rotation(rng.uniform(-0.3, 0.3), 4, "X"), sect=sect)
    for k in range(3):
        cone(IRON, (x + rng.uniform(-0.3, 0.3), y + rng.uniform(-0.8, 0.8), z - 0.6), rng.uniform(0.3, 0.8), 0.06, sect=sect)
# ribs either side of the saloon's torn side (its edges, clear of the way in)
for y in (SALOON_HOLE[0] - 1.9, SALOON_HOLE[0] + 1.9):
    rod(INSIDE, [(B - 0.1, y, 4.6), (B + 0.05, y + 0.15, 6.6), (SUPER - 0.05, y - 0.1, 8.7)], 0.08, sect="bow")


# ============================================================================================
# Debris in the gap (laid out in the world, then put in the bow's frame)
# ============================================================================================
to_bow = M_BOW.inverted()
cyl(IRON, to_bow @ Vector((-8.6, -12.2, 1.12)), to_bow @ Vector((-9.5, -15.0, 1.12)), 1.12, sides=12, collide=True, sect="bow")
cyl(IRON, to_bow @ Vector((-9.5, -15.0, 1.12)), to_bow @ Vector((-9.53, -15.08, 1.12)), 0.6, sides=8, sect="bow")
for at, size, tilt, turn in (((3.8, -14.4, 0.2), (2.0, 1.4, 0.1), 12.0, 30.0), ((-3.6, -16.4, 0.35), (1.6, 1.2, 0.1), 24.0, -50.0), ((6.0, -11.4, 0.18), (1.2, 1.8, 0.1), 8.0, 10.0)):
    plate(HULL, size, to_bow @ Matrix.Translation(at) @ Matrix.Rotation(math.radians(turn), 4, "Z") @ Matrix.Rotation(math.radians(tilt), 4, "X"), sect="bow")


# ============================================================================================
# Checks on the parts: inside-out faces (a ray out of each face must leave its own solid an even
# number of times)
# ============================================================================================
def inside_out(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.normal_update()
    tree = BVHTree.FromBMesh(bm)
    wrong = 0
    counted = 0
    for f in bm.faces:
        if f.calc_area() < 1e-8:
            continue
        counted += 1
        at = f.calc_center_median() + f.normal * 1e-4
        hits = 0
        while hits < 60:
            hit = tree.ray_cast(at, f.normal)
            if hit[0] is None:
                break
            hits += 1
            at = hit[0] + f.normal * 1e-4
        if hits % 2:
            wrong += 1
    bm.free()
    return wrong, counted


bad_parts = 0
for p in PARTS:
    if not p["closed"]:
        continue
    wrong, counted = inside_out(p["obj"])
    if wrong > max(2, counted * 0.01):
        bad_parts += 1
        print("WRECK inside-out %s: %d of %d faces" % (p["obj"].name, wrong, counted))
print("WRECK inside-out check: %d closed parts, %d with faces turned in" % (sum(1 for p in PARTS if p["closed"]), bad_parts))


# ============================================================================================
# Laid on the bed; the swim routes; the collision spheres
# ============================================================================================
for p in PARTS:
    p["obj"].matrix_world = M_OF[p["sect"]]
bpy.context.view_layer.update()


def to_world(sect, pts):
    return [M_OF[sect] @ Vector(p) for p in pts]


bow_mid = M_BOW @ Vector((0.0, BREAK, 3.0))
stern_mid = M_STERN @ Vector((0.0, BREAK, 3.0))
gap = (bow_mid + stern_mid) * 0.5
gap.z = 2.6
ROUTES = [
    ("tear, boiler room, up the first funnel", 0.5, to_world("bow", [(6.5, 7.5, 3.4), (3.6, 7.5, 3.4), (1.4, 8.6, 3.6), (0.0, 10.5, 4.4), (0.0, 10.5, 8.4), (0.0, 10.5, 12.0), (0.0, 10.5, 14.0)])),
    ("hatch, hold, forecastle hatch", 0.5, to_world("bow", [(0.0, 16.0, 11.0), (0.0, 16.0, 7.3), (0.0, 16.0, 3.8), (0.0, 19.0, 3.6), (0.0, 21.3, 4.4), (0.0, 21.3, 8.0), (0.0, 21.3, 11.5)])),
    ("hold through the bulkhead door to the boiler room", 0.55, to_world("bow", [(0.0, 16.0, 3.8), (0.0, 14.8, 3.0), (0.0, 13.0, 3.0), (0.6, 11.0, 3.3)])),
    ("promenade colonnade, gallery, staircase, break", 0.5, to_world("bow", [(6.0, 12.2, 8.55), (3.3, 12.2, 8.55), (1.8, 11.0, 8.45), (1.8, 4.0, 8.45), (1.8, -3.0, 8.45), (1.6, -4.7, 8.4), (0.5, -6.4, 8.2), (0.0, -7.6, 6.6), (0.0, -10.6, 5.8), (0.0, -14.0, 5.8)])),
    ("skylight into the saloon, out the break", 0.75, to_world("bow", [(3.2, -7.6, 13.0), (1.0, -7.6, 10.6), (0.0, -7.6, 8.6), (0.0, -10.4, 6.0), (0.0, -14.0, 5.8)])),
    ("the gap between the halves", 1.5, [gap + Vector((-7.0, 0.0, 0.0)), gap + Vector((7.0, 0.0, 0.0))]),
    ("the saloon's torn side, over the stairs, out the break", 0.5, to_world("bow", [(7.0, -7.4, 6.8), (3.3, -7.4, 6.8), (2.2, -7.4, 7.2), (0.0, -7.8, 8.0), (0.0, -10.4, 6.2), (0.0, -14.0, 5.8)])),
    ("a porthole (small fish)", 0.12, to_world("bow", [(5.0, 2.8, 5.9), (hull_x(2.8, 5.9) + 0.2, 2.8, 5.9), (2.3, 2.8, 5.9), (1.4, 2.8, 5.0)])),
    ("down the fourth funnel, the engine room, out the break", 0.5, to_world("stern", [(0.0, -15.5, 14.0), (0.0, -15.5, 8.4), (0.0, -15.5, 4.6), (0.0, -12.6, 4.6), (0.0, -9.0, 4.6), (0.0, -6.5, 4.6)])),
]


def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    return (a + ab * t - p).length


def route_room(p):
    """How far a sphere's skin must stay from p's nearest route: the least of (distance - room)."""
    best = 1e9
    for name, room, pts in ROUTES:
        for a, b in zip(pts, pts[1:]):
            best = min(best, seg_dist(p, a, b) - room - 0.04)
    return best


BULGE = 0.62
R_MAX = 1.5
SPACING = 0.42


def spheres():
    bodies = []
    for p in PARTS:
        if not p["collide"]:
            continue
        bm = bmesh.new()
        bm.from_mesh(p["obj"].data)
        bm.transform(p["obj"].matrix_world)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        bm.normal_update()
        tree = BVHTree.FromBMesh(bm)
        tris = [(f.verts[0].co.copy(), f.verts[1].co.copy(), f.verts[2].co.copy(), f.normal.copy(), f.calc_area()) for f in bm.faces]
        low = Vector((min(v.co.x for v in bm.verts), min(v.co.y for v in bm.verts), min(v.co.z for v in bm.verts)))
        high = Vector((max(v.co.x for v in bm.verts), max(v.co.y for v in bm.verts), max(v.co.z for v in bm.verts)))
        bm.free()
        bodies.append((tree, tris, low, high))
    probe = Vector((0.31, 0.27, 0.91)).normalized()

    def inside(q, tree):
        hits = 0
        at = q
        while hits < 80:
            hit = tree.ray_cast(at, probe)
            if hit[0] is None:
                break
            hits += 1
            at = hit[0] + probe * 1e-4
        return hits % 2 == 1

    samples = []
    for k, (tree, tris, low, high) in enumerate(bodies):
        for a, b, c, n, area in tris:
            want = area / (SPACING * SPACING)
            count = int(want) + (1 if rng.random() < want - int(want) else 0)
            for _ in range(count):
                u, v = rng.random(), rng.random()
                if u + v > 1.0:
                    u, v = 1.0 - u, 1.0 - v
                q = a + (b - a) * u + (c - a) * v
                if q.z < 0.08:
                    continue
                hidden = False
                for j, (other, _, lo, hi) in enumerate(bodies):
                    if j != k and lo.x - 0.01 < q.x < hi.x + 0.01 and lo.y - 0.01 < q.y < hi.y + 0.01 and lo.z - 0.01 < q.z < hi.z + 0.01:
                        if inside(q + n * 0.002, other):
                            hidden = True
                            break
                if hidden:
                    continue
                hit = tree.ray_cast(q - n * 0.002, -n, 4.0)
                thick = (hit[3] + 0.002) if hit[0] is not None else 0.3
                samples.append((q, n, thick))
    tree = KDTree(len(samples))
    for i, s in enumerate(samples):
        tree.insert(s[0], i)
    tree.balance()
    covered = [False] * len(samples)
    order = sorted(range(len(samples)), key=lambda i: -samples[i][2] + rng.random() * 0.3)
    made = []
    for i in order:
        if covered[i]:
            continue
        q, n, thick = samples[i]
        depth = min(thick * 0.5, R_MAX - BULGE)
        radius = max(0.55, min(R_MAX, thick * 0.5 + BULGE))
        middle = q - n * depth
        radius = min(radius, route_room(middle))
        if radius < depth + 0.06:
            continue
        if middle.z + radius < 0.0:
            continue
        made.append((middle, radius))
        for _, j, _ in tree.find_range(middle, radius * 0.985):
            covered[j] = True
    # (then drop the spheres whose every sample another sphere also covers, smallest first)
    holds = [0] * len(samples)
    inside_of = []
    for middle, radius in made:
        found = [j for _, j, _ in tree.find_range(middle, radius * 0.985)]
        inside_of.append(found)
        for j in found:
            holds[j] += 1
    kept = []
    for k in sorted(range(len(made)), key=lambda k: made[k][1]):
        if inside_of[k] and all(holds[j] > 1 for j in inside_of[k]):
            for j in inside_of[k]:
                holds[j] -= 1
        else:
            kept.append(made[k])
    print("WRECK collision: %d spheres dropped as covered twice" % (len(made) - len(kept)))
    made = kept
    left = sum(1 for c in covered if not c)
    print("WRECK collision: %d surface samples, %d spheres, %d samples left uncovered (by the routes' openings)" % (len(samples), len(made), left))
    bins = [0, 0, 0, 0]
    for _, r in made:
        bins[0 if r < 0.7 else 1 if r < 1.0 else 2 if r < 1.4 else 3] += 1
    print("WRECK spheres by radius: under 0.7 %d, 0.7-1.0 %d, 1.0-1.4 %d, 1.4-1.5 %d" % tuple(bins))
    return made


SPHERES = spheres()


# --- Places marked for the game: where reef grows (+Y out of the surface), where fish hang about,
# where a faint glow could sit
def spot(sect, at, normal=(0.0, 0.0, 1.0)):
    return (sect, Vector(at), Vector(normal).normalized())


REEF = [
    spot("bow", (-1.6, 24.0, fc_top(24.0))), spot("bow", (2.0, 23.5, fc_top(23.5))), spot("bow", (-0.6, 26.9, fc_top(26.9))), spot("bow", (0.0, 28.6, fc_top(28.6))),
    spot("bow", (2.6, 15.3, DECK)), spot("bow", (-2.6, 17.8, DECK)),
    spot("bow", (2.6, 9.7, BOAT)), spot("bow", (-2.5, 4.6, BOAT)), spot("bow", (2.65, -0.4, BOAT)), spot("bow", (-2.7, -4.9, BOAT)),
    spot("bow", (2.6, -9.0, BOAT)), spot("bow", (0.0, 7.0, 11.7)), spot("bow", (0.0, 0.3, 11.5)), spot("bow", (-2.6, 8.0, BOAT)),
    spot("bow", (1.12, FUNNELS[2] - (FUN_TOP - BOAT) * rake, FUN_TOP)), spot("bow", (-1.12, FUNNELS[2] - (FUN_TOP - BOAT) * rake, FUN_TOP)),
    spot("bow", (1.15, FUNNELS[1], BOAT + 0.75)), spot("bow", (-1.15, FUNNELS[1] - 0.4, BOAT + 0.75)), spot("bow", (0.0, FUNNELS[3] + 1.3, BOAT + 0.6)),
    spot("bow", (-2.3, -1.8, 12.05)),
    spot("bow", (3.05, 9.0, BOAT + 0.4)), spot("bow", (-3.05, 1.6, BOAT + 0.4)),
    spot("bow", (1.35, STAIR[0], 5.4)), spot("bow", (-1.35, STAIR[0], 5.4)),
    spot("bow", (2.2, -8.6, 4.0)), spot("bow", (-2.4, -5.2, PROM)),
    spot("bow", (B + 0.02, 1.0, 4.0), (1.0, 0.0, 0.0)), spot("bow", (B + 0.02, 12.8, 3.0), (1.0, 0.0, 0.0)), spot("bow", (B + 0.02, -2.5, 3.0), (1.0, 0.0, 0.0)),
    spot("bow", (0.0, 13.4, 11.2), (0.0, math.sin(-roof_tilt), math.cos(roof_tilt))), spot("bow", (-1.6, 13.0, 11.55), (0.0, math.sin(-roof_tilt), math.cos(roof_tilt))),
    spot("bow", (nest.x, nest.y, nest.z + 0.5)),
    spot("stern", (1.5, -25.0, poop_top(-25.0))), spot("stern", (-1.8, -28.0, poop_top(-28.0))), spot("stern", (1.15, FUNNELS[4], BOAT + 0.7)),
    spot("stern", (0.0, -12.2, 11.6)), spot("stern", (0.0, -26.95, 1.9), (0.0, -1.0, 0.0)), spot("stern", (3.05, -13.6, BOAT + 0.4)),
    spot("stern", (-B - 0.02, -16.0, 4.5), (-1.0, 0.0, 0.0)), spot("stern", (-B - 0.02, -19.5, 5.0), (-1.0, 0.0, 0.0)),
]
FISH = [
    spot("bow", (2.0, -8.0, 5.4)), spot("bow", (-2.2, -5.0, 8.4)), spot("bow", (0.0, 18.0, 3.6)), spot("bow", (0.0, 21.4, 3.6)),
    spot("bow", (1.2, 9.4, 4.2)), spot("bow", (1.0, 3.6, 3.3)), spot("bow", (1.8, 4.0, 8.45)), spot("bow", (1.8, -1.0, 8.45)),
    spot("stern", (0.0, -15.0, 4.9)), spot("stern", (3.2, -27.0, 2.4)), spot("stern", (0.0, -11.6, 8.4)),
    ("world", gap.copy(), Vector((0.0, 0.0, 1.0))),
]
LANTERNS = [
    spot("bow", (0.0, -7.6, 8.9)), spot("bow", (-2.0, -9.0, 5.2)), spot("bow", (0.8, 6.5, 5.0)), spot("bow", (1.0, 11.6, 3.2)),
    spot("bow", (0.0, 19.0, 5.0)), spot("stern", (0.0, -13.5, 4.6)),
]
assert len(REEF) == 40 and len(FISH) == 12 and len(LANTERNS) == 6, (len(REEF), len(FISH), len(LANTERNS))


def place_empty(name, sp, room=0.0):
    sect, at, normal = sp
    m = M_OF.get(sect, Matrix.Identity(4))
    world = m @ at
    if room > 0.0:
        # (a fish spot is moved out of the collision, as Sea.clear_of_rocks would move a fish there)
        start = world.copy()
        for _ in range(12):
            for middle, radius in SPHERES:
                away = world - middle
                if away.length < radius + room:
                    world = middle + away.normalized() * (radius + room + 0.02)
        if (world - start).length > 0.01:
            print("WRECK %s moved %.2f m out of the collision" % (name, (world - start).length))
    n = (m.to_3x3() @ normal).normalized()
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.empty_display_size = 0.4
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Vector((0.0, 0.0, 1.0)).rotation_difference(n)
    obj.location = world
    return obj


empties = []
for prefix, spots in (("ReefSpot", REEF), ("FishSpot", FISH), ("Lantern", LANTERNS)):
    for k, sp in enumerate(spots):
        empties.append(place_empty("%s%02d" % (prefix, k), sp, 0.32 if prefix == "FishSpot" else 0.0))


# ============================================================================================
# The two halves: joined, smoothed with hard edges kept, unwrapped, painted
# ============================================================================================
def join_section(sect, name, first):
    objs = [p["obj"] for p in PARTS if p["sect"] == sect]
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = first
    bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = name
    obj.data.name = name
    for poly in obj.data.polygons:
        poly.use_smooth = True
    split = obj.modifiers.new("split", "EDGE_SPLIT")
    split.split_angle = math.radians(40.0)
    bpy.ops.object.modifier_apply(modifier="split")
    return obj


bow = join_section("bow", "WreckBow", body)
stern = join_section("stern", "WreckStern", stern_body)
SECTIONS = {"bow": bow, "stern": stern}

triangles = {}
for key, obj in SECTIONS.items():
    obj.data.calc_loop_triangles()
    triangles[key] = len(obj.data.loop_triangles)
print("WRECK triangles: bow %d, stern %d, all %d" % (triangles["bow"], triangles["stern"], sum(triangles.values())))


def density(obj, size):
    """Texels per metre: the picture's side times the root of (share of the picture used / area)."""
    mesh = obj.data
    mesh.calc_loop_triangles()
    uv = mesh.uv_layers.active.data
    area3 = 0.0
    area2 = 0.0
    for tri in mesh.loop_triangles:
        area3 += tri.area
        a, b, c = (uv[i].uv for i in tri.loops)
        area2 += abs((b - a).x * (c - a).y - (b - a).y * (c - a).x) * 0.5
    return size * math.sqrt(area2 / area3), area3, area2


for key, obj in SECTIONS.items():
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=0.001)
    bpy.ops.uv.average_islands_scale()
    bpy.ops.uv.pack_islands(margin=0.0015, rotate=True, shape_method="CONCAVE")
    bpy.ops.object.mode_set(mode="OBJECT")
    texels, area3, used = density(obj, ATLAS_SIZE[key])
    print("WRECK atlas %s: %.0f m2 of surface, %.0f%% of the picture used, %.1f texels per metre (%.1f cm a texel)" % (key, area3, used * 100, texels, 100.0 / texels))


def gpu():
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for kind in ("OPTIX", "CUDA"):
            try:
                prefs.compute_device_type = kind
                prefs.get_devices()
                if any(d.type == kind for d in prefs.devices):
                    for d in prefs.devices:
                        d.use = d.type == kind
                    bpy.context.scene.cycles.device = "GPU"
                    return kind
            except Exception:
                continue
    except Exception:
        pass
    bpy.context.scene.cycles.device = "CPU"
    return "CPU"


def bake_all():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    print("WRECK baking on", gpu())
    scene.cycles.samples = SAMPLES
    world = bpy.data.worlds.new("sea")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.9, 0.93, 1.0, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
    scene.world = world
    bpy.ops.mesh.primitive_plane_add(size=160.0, location=(0.0, -10.0, 0.0))
    bed = bpy.context.object
    bed.name = "Bed"
    bed.data.materials.append(SAND)
    bake = scene.render.bake
    bake.use_pass_direct = True
    bake.use_pass_indirect = True
    bake.use_pass_diffuse = True
    bake.use_pass_glossy = False
    bake.use_pass_transmission = False
    bake.use_pass_emit = False
    bake.margin = 6
    for key, obj in SECTIONS.items():
        image = bpy.data.images.new("wreck_atlas_" + key, ATLAS_SIZE[key], ATLAS_SIZE[key], alpha=False)
        for slot in obj.material_slots:
            tree = slot.material.node_tree
            node = next((n for n in tree.nodes if n.type == "TEX_IMAGE" and n.name == "bake"), None)
            if node is None:
                node = tree.nodes.new("ShaderNodeTexImage")
                node.name = "bake"
            node.image = image
            tree.nodes.active = node
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.bake(type="COMBINED", use_clear=True)
        os.makedirs(os.path.dirname(ATLAS[key]), exist_ok=True)
        image.filepath_raw = ATLAS[key]
        image.file_format = "PNG"
        image.save()
        print("WRECK baked", ATLAS[key])
    bpy.data.objects.remove(bed, do_unlink=True)


if BAKE:
    bake_all()

os.makedirs(os.path.dirname(BLEND), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=BLEND)

# --- The data for the game, in Godot's axes (x, z, -y)
def godot(v):
    return [round(v.x, 3), round(v.z, 3), round(-v.y, 3)]


data = {
    "spheres": [godot(c) + [round(r, 3)] for c, r in SPHERES],
    "routes": [{"name": name, "room": room, "points": [godot(p) for p in pts]} for name, room, pts in ROUTES],
    "triangles": triangles,
}
with open(DATA, "w") as out:
    json.dump(data, out, separators=(",", ":"))

# --- For the game: one material a half (the game draws each with its own picture)
for key, obj in SECTIONS.items():
    plain = bpy.data.materials.new("Wreck" + key.capitalize() + "Paint")
    obj.data.materials.clear()
    obj.data.materials.append(plain)
    for poly in obj.data.polygons:
        poly.material_index = 0
bpy.ops.object.select_all(action="DESELECT")
for obj in list(SECTIONS.values()) + empties:
    obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=GLB, export_format="GLB", export_apply=True, export_yup=True, use_selection=True, export_image_format="NONE")
print("WRECK wrote", GLB, "and", DATA)
