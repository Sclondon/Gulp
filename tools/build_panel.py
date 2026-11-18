"""Builds the control panel as a low-poly 3D model with one painted texture.

    blender --background --python tools/build_panel.py [-- --no-bake]

Writes models/control_panel.glb, textures/panel/panel_atlas.png and tools/blend/control_panel.blend.

The user (2026-11-18): "lets recreate the ui as a 3d model to interact with", "the model should be
very similar in style to the first concpet art- though the texture needs to be less noisy" (the
first concept is tools/art_src/panel_concept_1.png), "the ui model is too blocky and not lumpy and
greebled like the concept", "Still not enough pipes / wires shaping the ui outline", "the dials
need labels", and then "Pipes and wires need proper connections, nails need proper models /
textures, and make it low poly twilight princess style". Laid out as the user drew it: "The sonar
map should be bigger and hust off center to the left, the speed dial should be above the boost
and soeed controls to the right and bigger, and the evolution dial should be above the joystick
to the left. There can be a little dwpth dial next to sonar".

Twilight Princess style here means: few triangles (the whole panel is about the weight of two of
that game's characters), spent on the outline, and the detail in ONE painted texture. The paint
is made by Blender: every part has a procedural material (soft patches of rust and verdigris,
worn brass), the parts are unwrapped into one atlas, and Cycles bakes colour, light from the
upper left, and the shadows and grime where parts meet into it. The game draws that picture
unlit (shaders/panel.gdshader) with a little shine on the brass.

  Helm    (bottom left): the socket and stick, the evolution dial over it, two electrodes
  Engine  (bottom right): the plunger, the lever's slot curving round it, the speed dial over it
  Gauges  (between): the sonar scope, small dials for depth and for burst left (the burst dial
          is Claude's pick of place), two switches, a grille, a valve wheel, a coil

Every pipe and wire ends in something: a flange bolted to a face, a collar into a housing's side
or top, a terminal. Rivets are six-sided domes on a washer; bolts are hexagon heads on a washer.

Units: 1 m here is 100 of TouchPad's layout units. Each housing's origin is the middle of its foot,
its face towards -Y (Godot's +Z, the camera), Z up. scripts/panel_model.gd places and moves the
parts by these names:
  Helm    > Stick (pivot in the socket), NeedleEvolve, SparkA, SparkB (the electrodes' tips)
  Engine  > Plunger (pushed in along +Y), Lever (turned about Y round the plunger) > Grip,
            NeedleSpeed
  Gauges  > NeedleDepth, NeedleBurst, Scope, ScopeEdge
Needles point straight up as built and turn about Y, 2.2 radians either way.
Material names stay on the model (the game gives each its shine by name).
The numbers in CAPITALS are printed at the end as the PANEL line, and panel_model.gd holds the
same ones: change both.
"""
import bpy
import bmesh
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GLB = os.path.join(HERE, "..", "models", "control_panel.glb")
BLEND = os.path.join(HERE, "blend", "control_panel.blend")
ATLAS = os.path.join(HERE, "..", "textures", "panel", "panel_atlas.png")
ATLAS_SIZE = 2048
BAKE = "--no-bake" not in sys.argv

SIDE_WIDE = 2.2
SIDE_TALL = 3.5
SHOULDER = 2.5     # the side housings' square part; over it an arched head round the big dial
BODY = 2.3         # the instrument housing's square part; over it heads round the scope and a dial
WELL_Z = 1.05      # the socket's and the plunger's middle, above the foot
WELL_OUT = 0.82    # their brass ring
SLOT_R = 1.0       # the lever's slot: an arc round the plunger
SLOT_FROM = math.radians(162.0)   # dead slow (lower left)
SLOT_TO = math.radians(74.0)      # full ahead (upper right)
BIG_DIAL = (0.0, 2.84)            # the evolution dial on the helm, the speed dial on the engine
BIG_DIAL_R = 0.5
GAUGE_WIDE = 3.3
GAUGE_TALL = 3.0
SCOPE = (-0.45, 2.02)
SCOPE_R = 0.72
SMALL_DIALS = {"Depth": (1.02, 2.45), "Burst": (1.02, 1.6)}
SMALL_DIAL_R = 0.25
SWING = 2.2        # how far a needle turns either way from straight up (radians)

bpy.ops.wm.read_factory_settings(use_empty=True)


# --- Materials: procedural, for the bake. Soft broad patches, no grain.
def material(name, colour, patch_a=None, patch_b=None, size=1.6, rough=0.75):
    """A painted material: `colour`, with soft patches of `patch_a` and fewer of `patch_b`."""
    made = bpy.data.materials.new(name)
    made.use_nodes = True
    tree = made.node_tree
    shader = next(n for n in tree.nodes if n.type == "BSDF_PRINCIPLED")
    shader.inputs["Roughness"].default_value = rough
    if patch_a is None:
        shader.inputs["Base Color"].default_value = (*colour, 1.0)
        return made
    place = tree.nodes.new("ShaderNodeTexCoord")
    last = None
    for k, (patch, low, high, scale) in enumerate(((patch_a, 0.42, 0.62, 1.0), (patch_b or patch_a, 0.52, 0.66, 0.7))):
        stretch = tree.nodes.new("ShaderNodeMapping")
        # (stretched downwards, as rust and verdigris run; the second set shifted)
        stretch.inputs["Scale"].default_value = (scale / size, scale / size, 0.45 * scale / size)
        stretch.inputs["Location"].default_value = (3.7 * k, 1.1 * k, 7.3 * k)
        tree.links.new(place.outputs["Object"], stretch.inputs["Vector"])
        noise = tree.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 2.2
        noise.inputs["Detail"].default_value = 2.0
        noise.inputs["Roughness"].default_value = 0.5
        tree.links.new(stretch.outputs["Vector"], noise.inputs["Vector"])
        ramp = tree.nodes.new("ShaderNodeMapRange")
        ramp.interpolation_type = "SMOOTHSTEP"
        ramp.inputs["From Min"].default_value = low
        ramp.inputs["From Max"].default_value = high
        tree.links.new(noise.outputs["Fac"], ramp.inputs["Value"])
        mix = tree.nodes.new("ShaderNodeMixRGB")
        if last is None:
            mix.inputs["Color1"].default_value = (*colour, 1.0)
        else:
            tree.links.new(last.outputs["Color"], mix.inputs["Color1"])
        mix.inputs["Color2"].default_value = (*patch, 1.0)
        tree.links.new(ramp.outputs["Result"], mix.inputs["Fac"])
        last = mix
    tree.links.new(last.outputs["Color"], shader.inputs["Base Color"])
    return made


IRON = material("iron", (0.30, 0.11, 0.04), (0.12, 0.045, 0.02), (0.13, 0.22, 0.14), 1.4)
BRASS = material("brass", (0.62, 0.36, 0.07), (0.42, 0.22, 0.05), (0.36, 0.3, 0.1), 1.0, 0.5)
COPPER = material("copper", (0.6, 0.2, 0.07), (0.42, 0.14, 0.06), (0.2, 0.36, 0.26), 0.8, 0.5)
RUBBER = material("rubber", (0.02, 0.02, 0.025), None, None, 1.0, 0.6)
DARK = material("dark", (0.004, 0.003, 0.003))
PAPER = material("paper", (0.78, 0.62, 0.34), (0.62, 0.45, 0.22), (0.7, 0.55, 0.3), 0.7)
INK = material("ink", (0.02, 0.012, 0.008))
RED = material("red", (0.5, 0.03, 0.02), (0.28, 0.04, 0.03), (0.3, 0.08, 0.04), 0.6)
ORANGE = material("orange", (0.8, 0.25, 0.02))
GREEN = material("green", (0.16, 0.3, 0.05))
STEEL = material("steel", (0.24, 0.23, 0.2), (0.2, 0.1, 0.04), (0.16, 0.16, 0.14), 0.8, 0.5)
SCREEN = material("screen", (0.005, 0.07, 0.012), (0.008, 0.11, 0.02), None, 0.9, 0.3)
LAMP = material("lamp", (0.2, 0.09, 0.04), (0.14, 0.06, 0.03), None, 0.7, 0.4)

parts = []


def keep(mat):
    obj = bpy.context.object
    obj.data.materials.append(mat)
    parts.append(obj)
    return obj


def settle(obj):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)


TURN = {"Y": (math.pi * 0.5, 0.0, 0.0), "Z": (0.0, 0.0, 0.0), "X": (0.0, math.pi * 0.5, 0.0)}


# --- Low-poly pieces. `sides` is asked for as on a smooth model and cut down here.
def few(sides):
    return 6 if sides <= 10 else 8 if sides <= 16 else 12 if sides <= 28 else 16


def box(mat, size, at, turn=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=at, rotation=(0.0, turn, 0.0))
    obj = keep(mat)
    obj.scale = size
    settle(obj)
    return obj


def cyl(mat, radius, depth, at, axis="Y", sides=28, top=None):
    """A cylinder (or, with `top`, a cone frustum: `radius` at the far end)."""
    if top is None:
        bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, vertices=few(sides), location=at, rotation=TURN[axis])
    else:
        bpy.ops.mesh.primitive_cone_add(radius1=radius, radius2=top, depth=depth, vertices=few(sides), location=at, rotation=TURN[axis])
    obj = keep(mat)
    settle(obj)
    return obj


def ball(mat, radius, at, squash=(1.0, 1.0, 1.0), fine=16):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, segments=8 if fine <= 16 else 12, ring_count=4 if fine <= 16 else 6, location=at)
    obj = keep(mat)
    obj.scale = squash
    settle(obj)
    return obj


def torus(mat, major, minor, at, axis="Y", fine=32):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=few(fine) + 4, minor_segments=4, location=at, rotation=TURN[axis])
    obj = keep(mat)
    settle(obj)
    return obj


def flat(mat, points, front):
    """A flat shape on a face (points are x, z), facing the eye: paint, in effect."""
    mesh = bpy.data.meshes.new("flat")
    bm = bmesh.new()
    face = bm.faces.new([bm.verts.new((x, front, z)) for x, z in points])
    if face.normal.y > 0.0:
        face.normal_flip()
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("flat", mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    return keep(mat)


def prism(mat, points, front, depth):
    """A flat shape in the face's plane (points are x, z), from y = front back to front + depth."""
    mesh = bpy.data.meshes.new("prism")
    bm = bmesh.new()
    face = bm.faces.new([bm.verts.new((x, front, z)) for x, z in points])
    made = bmesh.ops.extrude_face_region(bm, geom=[face])
    bmesh.ops.translate(bm, verts=[v for v in made["geom"] if isinstance(v, bmesh.types.BMVert)], vec=(0.0, depth, 0.0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("prism", mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    return keep(mat)


def band(mat, middle, radius, half, a0, a1, front, depth, steps=10, round_ends=False):
    """A curved band in the face's plane round `middle` (x, z), from angle a0 to a1 (depth 0: flat)."""
    def at(a, r):
        return (middle[0] + math.cos(a) * r, middle[1] + math.sin(a) * r)
    outer = [at(a0 + (a1 - a0) * k / steps, radius + half) for k in range(steps + 1)]
    inner = [at(a0 + (a1 - a0) * k / steps, radius - half) for k in range(steps + 1)]
    cap0 = []
    cap1 = []
    if round_ends:
        way = 1.0 if a1 > a0 else -1.0
        for k in range(1, 4):
            b = math.pi * k / 4.0
            c1 = at(a1, radius)
            cap1.append((c1[0] + math.cos(a1) * half * math.cos(b) - math.sin(a1) * way * half * math.sin(b),
                         c1[1] + math.sin(a1) * half * math.cos(b) + math.cos(a1) * way * half * math.sin(b)))
            c0 = at(a0, radius)
            cap0.append((c0[0] - math.cos(a0) * half * math.cos(b) + math.sin(a0) * way * half * math.sin(b),
                         c0[1] - math.sin(a0) * half * math.cos(b) - math.cos(a0) * way * half * math.sin(b)))
    points = outer + cap1 + inner[::-1] + cap0
    return prism(mat, points, front, depth) if depth > 0.0 else flat(mat, points, front)


def pipe(mat, points, radius, fine=3):
    """A pipe through points (x, y, z), its bends rounded: six-sided."""
    curve = bpy.data.curves.new("pipe", "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_resolution = 1
    curve.use_fill_caps = True
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for point, at in zip(spline.bezier_points, points):
        point.co = at
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    spline.resolution_u = fine
    obj = bpy.data.objects.new("pipe", curve)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    return keep(mat)


# --- Fixings: what pipes and wires end in, and what holds the plates on.
def flange(at, radius, axis, mat=None):
    """Where a pipe meets a housing: a wide collar flat against it and a narrower neck."""
    out = {"Y": (0.0, -1.0, 0.0), "Z": (0.0, 0.0, 1.0), "X": (1.0, 0.0, 0.0), "-X": (-1.0, 0.0, 0.0), "-Z": (0.0, 0.0, -1.0)}[axis]
    line = axis[-1]
    cyl(mat or BRASS, radius * 2.1, radius * 0.7, tuple(at[i] + out[i] * radius * 0.35 for i in range(3)), line, 10)
    cyl(mat or BRASS, radius * 1.45, radius * 1.1, tuple(at[i] + out[i] * radius * 1.2 for i in range(3)), line, 10)


def collar(at, radius, axis="Z"):
    """A brass coupling round a pipe, part way along it."""
    cyl(BRASS, radius * 1.5, radius * 1.1, at, axis, 10)


def run(mat, points, radius, ends, fine=3):
    """A pipe or a wire with both ends made fast. `ends` names what each end meets: "Y" a face (the
    pipe turns in to it), "X" / "-X" a housing's side, "Z" its top, "-Z" its underside, None nothing."""
    points = list(points)
    for which, end in ((0, ends[0]), (-1, ends[1])):
        if end == "Y":
            # (a short turn in towards the face, so the pipe meets it square)
            tip = points[which]
            stand = (tip[0], tip[1] - radius * 2.6, tip[2])
            if which == 0:
                points.insert(1, stand)
            else:
                points.insert(len(points) - 1, stand)
    pipe(mat, points, radius, fine)
    for which, end in ((0, ends[0]), (-1, ends[1])):
        if end:
            flange(points[which], radius, end, BRASS)


def rivet(x, z, size=0.075, front=0.0):
    """A rivet: a six-sided dome on a thin washer."""
    cyl(BRASS, size * 1.25, size * 0.2, (x, front - size * 0.1, z), "Y", 6)
    cyl(BRASS, size * 0.95, size * 0.6, (x, front - size * 0.45, z), "Y", 6, size * 0.5)


def bolt(x, z, size=0.05, front=0.0):
    """A bolt: a hexagon head on a round washer."""
    cyl(STEEL, size * 1.5, size * 0.25, (x, front - size * 0.12, z), "Y", 10)
    cyl(STEEL, size, size * 0.8, (x, front - size * 0.6, z), "Y", 6)


def join(name, origin=(0.0, 0.0, 0.0), parent=None):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    if len(parts) > 1:
        bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = name
    obj.data.name = name
    parts.clear()
    # smooth, with hard edges kept; normals outward (flat paint keeps the way it was laid)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    split = obj.modifiers.new("split", "EDGE_SPLIT")
    split.split_angle = math.radians(50.0)
    bpy.ops.object.modifier_apply(modifier="split")
    bpy.context.scene.cursor.location = origin
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
    if parent is not None:
        obj.parent = parent
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
    return obj


def marker(name, at, parent):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.location = at
    bpy.context.view_layer.update()
    obj.parent = parent
    obj.matrix_parent_inverse = parent.matrix_world.inverted()
    return obj


def plate(wide, tall, heads=(), thick=0.32):
    """A housing's rusted plate, its face at y = 0: a square part `tall` high with a raised rim,
    rivets and feet, and round heads (x, z, radius) standing over it, bolted round."""
    box(IRON, (wide, thick, tall), (0.0, thick * 0.5, tall * 0.5))
    for x, z, r in heads:
        cyl(IRON, r, thick, (x, thick * 0.5, z), "Y", 40)
        cyl(IRON, r - 0.1, 0.05, (x, -0.015, z), "Y", 40)
        count = int(r * 9)
        for k in range(count):
            a = math.tau * (k + 0.5) / count
            if z + math.sin(a) * r > tall - 0.1:
                bolt(x + math.cos(a) * (r - 0.05), z + math.sin(a) * (r - 0.05), 0.04)
    for side in (-1.0, 1.0):
        box(IRON, (0.1, 0.07, tall), (side * (wide * 0.5 - 0.05), -0.02, tall * 0.5))
        rows = max(2, round((tall - 0.4) / 0.6) + 1)
        for k in range(rows):
            rivet(side * (wide * 0.5 - 0.2), 0.2 + (tall - 0.4) * k / (rows - 1.0), 0.06)
        # a foot, and a brass corner bracket over it
        cyl(BRASS, 0.2, 0.16, (side * (wide * 0.5 - 0.3), thick * 0.5, 0.02), "Z", 12)
        prism(BRASS, [(side * wide * 0.5, 0.0), (side * (wide * 0.5 - 0.34), 0.0), (side * wide * 0.5, 0.34)], -0.06, 0.05)
    box(IRON, (wide - 0.2, 0.07, 0.1), (0.0, -0.02, 0.05))
    across = max(2, round((wide - 0.4) / 0.6) + 1)
    for k in range(1, across - 1):
        rivet(-wide * 0.5 + 0.2 + (wide - 0.4) * k / (across - 1.0), 0.2, 0.06)


def patch(x, z, wide, tall, turn):
    """A smaller sheet of iron bolted over the plate, a little askew."""
    box(IRON, (wide, 0.06, tall), (x, -0.02, z), turn)
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            px = sx * (wide * 0.5 - 0.06)
            pz = sz * (tall * 0.5 - 0.06)
            bolt(x + px * math.cos(turn) + pz * math.sin(turn), z - px * math.sin(turn) + pz * math.cos(turn), 0.035, -0.05)


def mini_gauge(x, z, r=0.15):
    """A small pressure gauge with a fixed needle: furniture."""
    cyl(BRASS, r + 0.03, 0.1, (x, -0.02, z), "Y", 16)
    cyl(PAPER, r - 0.01, 0.02, (x, -0.075, z), "Y", 16)
    flat(INK, [(x - 0.012, z - 0.02), (x + 0.012, z - 0.02), (x + r * 0.55, z + r * 0.6)], -0.088)


def side_pipe(x, tall, lean):
    """A pipe up a housing's side, out of a flange on its foot, that bends in over the shoulder and
    down into the housing's top."""
    run(BRASS, [(x, 0.16, 0.12), (x, 0.16, tall - 0.3), (x + lean * 0.1, 0.16, tall + 0.08), (x + lean * 0.36, 0.16, tall + 0.11), (x + lean * 0.5, 0.16, tall)], 0.11, ("Z", "Z"))
    collar((x, 0.16, 0.7), 0.11)
    collar((x, 0.16, tall - 0.6), 0.11)


def well(mat_inside):
    """The brass ring and the recess of a socket or a button, at the housing's well."""
    cyl(BRASS, WELL_OUT, 0.1, (0.0, -0.02, WELL_Z), "Y", 32)
    torus(BRASS, WELL_OUT - 0.11, 0.1, (0.0, -0.07, WELL_Z), "Y", 32)
    cyl(mat_inside, WELL_OUT - 0.22, 0.02, (0.0, -0.105, WELL_Z), "Y", 32)
    for k in range(6):
        a = math.tau * (k + 0.5) / 6.0
        rivet(math.cos(a) * (WELL_OUT - 0.06), WELL_Z + math.sin(a) * (WELL_OUT - 0.06), 0.045, -0.07)


def turn_of(value):
    """The angle in the face's plane a needle points at for a value 0..1."""
    return math.pi * 0.5 + SWING - 2.0 * SWING * value


def sign(x, z, s, what, front):
    """A dial's label, as a symbol in ink on its face (the user: "the dials need labels"; symbols,
    not words, as on the buttons): "speed" a double chevron, "fish" a small fish and a big one
    (how far it has grown), "depth" a wave with an arrow down from it, "bolt" a lightning bolt
    (how much burst is left). `s` is half its height."""
    def ink(points):
        flat(INK, [(x + px * s, z + pz * s) for px, pz in points], front)
    if what == "speed":
        for shift in (-0.75, 0.15):
            ink([(shift, 0.8), (shift + 0.4, 0.8), (shift + 1.0, 0.0), (shift + 0.4, -0.8), (shift, -0.8), (shift + 0.6, 0.0)])
    elif what == "bolt":
        ink([(0.2, 1.0), (-0.55, -0.15), (-0.08, -0.15), (-0.3, -1.0), (0.55, 0.2), (0.06, 0.2)])
    elif what == "depth":
        ink([(-0.16, 0.35), (0.16, 0.35), (0.16, -0.3), (0.5, -0.3), (0.0, -1.0), (-0.5, -0.3), (-0.16, -0.3)])
        top = [(-1.0, 0.7), (-0.5, 1.0), (0.0, 0.7), (0.5, 1.0), (1.0, 0.7)]
        ink(top + [(px, pz - 0.24) for px, pz in reversed(top)])
    elif what == "fish":
        for cx, k in ((-1.2, 0.5), (0.45, 1.0)):
            ink([(cx + math.cos(math.tau * i / 8.0) * 0.7 * k - 0.15 * k, math.sin(math.tau * i / 8.0) * 0.42 * k) for i in range(8)])
            ink([(cx + 0.4 * k, 0.0), (cx + 1.0 * k, 0.42 * k), (cx + 1.0 * k, -0.42 * k)])


def dial(x, z, r, marks, hot, label):
    """A dial's fixed parts: a brass ring, a paper face, `marks` ticks from the lower left stop over
    the top to the lower right, (hot) green, orange and red stretches round it, and its label."""
    cyl(BRASS, r + 0.17, 0.1, (x, -0.02, z), "Y", 28)
    torus(BRASS, r + 0.09, 0.075, (x, -0.075, z), "Y", 28)
    cyl(PAPER, r + 0.03, 0.02, (x, -0.075, z), "Y", 28)
    face = -0.088
    if hot:
        band(GREEN, (x, z), r * 0.86, r * 0.07, turn_of(0.0), turn_of(0.62), face, 0.0, 8)
        band(ORANGE, (x, z), r * 0.86, r * 0.07, turn_of(0.62), turn_of(0.82), face, 0.0, 3)
        band(RED, (x, z), r * 0.86, r * 0.07, turn_of(0.82), turn_of(1.0), face, 0.0, 3)
    for k in range(marks):
        a = turn_of(k / (marks - 1.0))
        long = r * (0.3 if hot and k % 4 == 0 or not hot else 0.17)
        wide = r * 0.045
        far = r * (0.76 if hot else 0.92)
        c = math.cos(a)
        s = math.sin(a)
        flat(INK, [(x + c * (far - long) - s * wide, z + s * (far - long) + c * wide), (x + c * far - s * wide, z + s * far + c * wide),
                   (x + c * far + s * wide, z + s * far - c * wide), (x + c * (far - long) + s * wide, z + s * (far - long) - c * wide)], face - 0.001)
    sign(x, z - r * 0.56, r * 0.27, label, face - 0.001)
    for k in range(4):
        a = math.tau * (k + 0.5) / 4.0
        rivet(x + math.cos(a) * (r + 0.1), z + math.sin(a) * (r + 0.1), 0.03 + r * 0.03, -0.11)


def needle(name, x, z, r, parent):
    flat(RED, [(x - r * 0.08, z - r * 0.2), (x + r * 0.08, z - r * 0.2), (x, z + r * 0.86)], -0.1)
    cyl(BRASS, r * 0.14, 0.035, (x, -0.105, z), "Y", 8)
    join("Needle" + name, (x, 0.0, z), parent)


def valve(x, z, r, front=-0.16):
    """A red valve wheel on a brass stem with a flange."""
    flange((x, front + 0.2, z), r * 0.3, "Y")
    cyl(BRASS, r * 0.22, 0.2, (x, front + 0.1, z), "Y", 8)
    torus(RED, r, r * 0.17, (x, front, z), "Y", 12)
    for k in range(2):
        a = math.pi * k / 2.0 + 0.4
        c = math.cos(a)
        s = math.sin(a)
        w = r * 0.1
        prism(RED, [(x - c * r - s * w, z - s * r + c * w), (x + c * r - s * w, z + s * r + c * w),
                    (x + c * r + s * w, z + s * r - c * w), (x - c * r + s * w, z - s * r - c * w)], front - 0.02, 0.04)
    cyl(BRASS, r * 0.26, 0.07, (x, front - 0.04, z), "Y", 6)


def ring_points(middle, radius, a0, a1, y, count=7):
    """Points on an arc in the face's plane (degrees), for a pipe that hugs a round head."""
    out = []
    for k in range(count):
        a = math.radians(a0 + (a1 - a0) * k / (count - 1.0))
        out.append((middle[0] + math.cos(a) * radius, y, middle[1] + math.sin(a) * radius))
    return out


def outline(inner):
    """Pipes and wires that shape a side housing's outline (the user: "Still not enough pipes /
    wires shaping the ui outline"), every one made fast at both ends: a pipe over its arched head
    from shoulder to shoulder, loops standing off its inner side (`inner` 1: its right, -1: its
    left), wires from terminals on the head's crown down into the housing's sides."""
    half = SIDE_WIDE * 0.5
    side = "X" if inner > 0.0 else "-X"
    other = "-X" if inner > 0.0 else "X"
    over = ring_points(BIG_DIAL, 0.885, 180.0, 0.0, 0.16, 7)
    over = [(over[0][0], 0.16, SHOULDER)] + over + [(over[-1][0], 0.16, SHOULDER)]
    run(BRASS, over, 0.075, ("Z", "Z"))
    for k in (3, 4, 5):
        collar(over[k], 0.075, "Y")
    # a fat loop out of the inner side and back in, low down, with a valve on it
    run(BRASS, [(inner * half, 0.16, 1.62), (inner * (half + 0.11), 0.16, 1.55), (inner * (half + 0.16), 0.16, 1.15),
                (inner * (half + 0.16), 0.16, 0.6), (inner * (half + 0.11), 0.16, 0.22), (inner * half, 0.16, 0.16)], 0.095, (side, side))
    collar((inner * (half + 0.16), 0.16, 0.85), 0.095)
    valve(inner * (half + 0.16), 1.22, 0.15, -0.04)
    # a thin copper loop over it
    run(COPPER, [(inner * half, 0.12, 2.3), (inner * (half + 0.1), 0.12, 2.22), (inner * (half + 0.12), 0.12, 1.95), (inner * half, 0.12, 1.84)], 0.05, (side, side))
    # wires from terminals on the head's crown, drooping down into the housing's two sides
    for way, reach, into in ((inner, 1.0, side), (-inner, 0.92, other)):
        run(RUBBER, [(way * 0.3, -0.02, BIG_DIAL[1] + 0.66), (way * 0.75 * reach, -0.1, BIG_DIAL[1] + 0.86), (way * (half + 0.06) * reach, 0.0, BIG_DIAL[1] + 0.45),
                     (way * (half + 0.05) * reach, 0.12, SHOULDER - 0.05), (way * half, 0.12, SHOULDER - 0.3)], 0.04, ("Y", into), 4)


# --- The helm housing: a socket with a rubber boot and a stick; over it the evolution dial,
# between two electrodes that stand over the housing's top.
plate(SIDE_WIDE, SHOULDER, [(BIG_DIAL[0], BIG_DIAL[1], 0.8)])
side_pipe(-SIDE_WIDE * 0.5 - 0.02, SHOULDER - 0.2, 1.0)
well(DARK)
for major, out in ((0.44, -0.12), (0.33, -0.19), (0.23, -0.25)):
    torus(RUBBER, major, 0.09, (0.0, out, WELL_Z), "Y", 16)
dial(BIG_DIAL[0], BIG_DIAL[1], BIG_DIAL_R, 9, False, "fish")
POSTS = 0.84
for side in (-1.0, 1.0):
    # an electrode: a post on a bolted foot, an insulator, a ball
    flange((side * POSTS, -0.02, SHOULDER - 0.5), 0.11, "Y")
    run(BRASS, [(side * POSTS, -0.02, SHOULDER - 0.5), (side * POSTS, -0.13, SHOULDER - 0.42), (side * POSTS, -0.13, SHOULDER + 0.1), (side * POSTS, -0.13, SHOULDER + 0.8)], 0.085, (None, None))
    collar((side * POSTS, -0.13, SHOULDER + 0.05), 0.1)
    cyl(PAPER, 0.13, 0.12, (side * POSTS, -0.13, SHOULDER + 0.55), "Z", 8)
    ball(BRASS, 0.11, (side * POSTS, -0.13, SHOULDER + 0.9))
    # a wire from the post's foot to a terminal on the socket's ring
    run(RUBBER, [(side * (POSTS + 0.02), -0.04, SHOULDER - 0.72), (side * (POSTS + 0.1), -0.16, SHOULDER - 0.95), (side * 0.8, -0.05, WELL_Z + 0.52)], 0.035, ("Y", "Y"), 4)
# a copper pipe across the face, between two fittings
run(COPPER, [(-0.9, 0.0, 2.0), (-0.35, -0.07, 1.97), (0.35, -0.07, 2.03), (0.9, 0.0, 2.0)], 0.045, ("Y", "Y"))
mini_gauge(-0.86, 0.32)
patch(0.82, 0.34, 0.42, 0.36, 0.12)
outline(1.0)
helm = join("Helm")
marker("SparkA", (-POSTS, -0.13, SHOULDER + 0.9), helm)
marker("SparkB", (POSTS, -0.13, SHOULDER + 0.9), helm)
needle("Evolve", BIG_DIAL[0], BIG_DIAL[1], BIG_DIAL_R, helm)

# the stick: a shaft out of the boot, a collar, a brass ball
cyl(STEEL, 0.085, 0.62, (0.0, -0.4, WELL_Z), "Y", 8)
cyl(BRASS, 0.15, 0.14, (0.0, -0.66, WELL_Z), "Y", 10)
ball(BRASS, 0.36, (0.0, -1.0, WELL_Z), (1.0, 1.0, 1.0), 24)
join("Stick", (0.0, 0.0, WELL_Z), helm)

# --- The engine housing: a plunger in its ring, a slot curving round it with a lever in it, and
# the speed dial over them.
plate(SIDE_WIDE, SHOULDER, [(BIG_DIAL[0], BIG_DIAL[1], 0.8)])
side_pipe(SIDE_WIDE * 0.5 + 0.02, SHOULDER - 0.2, -1.0)
well(DARK)
band(BRASS, (0.0, WELL_Z), SLOT_R, 0.15, SLOT_FROM, SLOT_TO, -0.05, 0.05, 10, True)
band(DARK, (0.0, WELL_Z), SLOT_R, 0.085, SLOT_FROM, SLOT_TO, -0.052, 0.0, 10, True)
dial(BIG_DIAL[0], BIG_DIAL[1], BIG_DIAL_R, 9, True, "speed")
valve(0.86, SHOULDER - 0.28, 0.17)
# a copper pipe from under the valve down the face to a fitting by the foot
run(COPPER, [(0.86, 0.0, SHOULDER - 0.56), (0.97, -0.07, 1.8), (0.97, -0.07, 0.95), (0.97, 0.0, 0.34)], 0.045, ("Y", "Y"))
mini_gauge(-0.86, 2.22)
patch(-0.82, 0.32, 0.4, 0.34, -0.1)
outline(-1.0)
engine = join("Engine")
needle("Speed", BIG_DIAL[0], BIG_DIAL[1], BIG_DIAL_R, engine)

# the plunger: a domed button with a double chevron
cyl(BRASS, 0.56, 0.2, (0.0, -0.16, WELL_Z), "Y", 32)
cyl(LAMP, 0.5, 0.08, (0.0, -0.3, WELL_Z), "Y", 32, 0.38)
for shift in (-0.17, 0.09):
    flat(INK, [(shift - 0.05, WELL_Z + 0.2), (shift + 0.05, WELL_Z + 0.2), (shift + 0.24, WELL_Z), (shift + 0.05, WELL_Z - 0.2),
               (shift - 0.05, WELL_Z - 0.2), (shift + 0.13, WELL_Z)], -0.342)
join("Plunger", (0.0, 0.0, WELL_Z), engine)

# the lever, built standing at the top of its arc (turned about Y by the game): a boss riding in the
# slot, a tapered brass grip standing out of the housing towards the eye, a ball on its end
cyl(BRASS, 0.14, 0.1, (0.0, -0.1, WELL_Z + SLOT_R), "Y", 8)
cyl(STEEL, 0.05, 0.3, (0.0, -0.25, WELL_Z + SLOT_R), "Y", 6)
cyl(BRASS, 0.15, 0.55, (0.0, -0.62, WELL_Z + SLOT_R), "Y", 10, 0.08)
ball(BRASS, 0.17, (0.0, -0.92, WELL_Z + SLOT_R))
lever = join("Lever", (0.0, 0.0, WELL_Z), engine)
marker("Grip", (0.0, -0.75, WELL_Z + SLOT_R), lever)

# --- The instrument housing: the scope, two small dials, two switches, a grille, a valve, a coil.
plate(GAUGE_WIDE, BODY, [(SCOPE[0], SCOPE[1], 1.0), (SMALL_DIALS["Depth"][0], SMALL_DIALS["Depth"][1], 0.46)])
half = GAUGE_WIDE * 0.5
# a pipe up the right of the face, between two fittings, with a copper coil wound round it
run(BRASS, [(1.48, 0.0, 0.22), (1.48, -0.12, 0.5), (1.48, -0.12, 1.2), (1.48, 0.0, 1.5)], 0.075, ("Y", "Y"))
coil = []
for k in range(25):
    a = math.tau * k / 6.0
    coil.append((1.48 + math.cos(a) * 0.125, -0.12 + math.sin(a) * 0.125, 0.55 + 0.6 * k / 24.0))
pipe(COPPER, coil, 0.028, 1)
# the scope
cyl(BRASS, SCOPE_R + 0.2, 0.1, (SCOPE[0], -0.02, SCOPE[1]), "Y", 40)
torus(BRASS, SCOPE_R + 0.1, 0.1, (SCOPE[0], -0.07, SCOPE[1]), "Y", 40)
cyl(SCREEN, SCOPE_R + 0.03, 0.02, (SCOPE[0], -0.09, SCOPE[1]), "Y", 40)
for k in range(8):
    a = math.tau * (k + 0.5) / 8.0
    rivet(SCOPE[0] + math.cos(a) * (SCOPE_R + 0.14), SCOPE[1] + math.sin(a) * (SCOPE_R + 0.14), 0.045, -0.12)
for name, (x, z) in SMALL_DIALS.items():
    dial(x, z, SMALL_DIAL_R, 9, name == "Burst", "bolt" if name == "Burst" else "depth")
# copper pipes from the scope's ring to each small dial's
run(COPPER, [(0.36, -0.04, 2.5), (0.5, -0.14, 2.62), (0.68, -0.04, 2.56)], 0.04, ("Y", "Y"))
run(COPPER, [(0.38, -0.04, 1.74), (0.52, -0.14, 1.58), (0.68, -0.04, 1.62)], 0.04, ("Y", "Y"))
patch(1.2, 1.07, 0.4, 0.28, 0.1)
patch(-1.38, 1.2, 0.36, 0.5, -0.08)
# the switches: a steel plate, a slot, a red handle
for x in (-0.95, -0.25):
    box(STEEL, (0.55, 0.06, 0.8), (x, -0.02, 0.56))
    flat(DARK, [(x - 0.05, 0.31), (x + 0.05, 0.31), (x + 0.05, 0.73), (x - 0.05, 0.73)], -0.052)
    cyl(STEEL, 0.04, 0.2, (x, -0.12, 0.74), "Y", 6)
    box(RED, (0.3, 0.2, 0.24), (x, -0.26, 0.74))
    for sx in (-1.0, 1.0):
        for sz in (0.24, 0.88):
            bolt(x + sx * 0.2, sz, 0.035, -0.05)
# the grille
cyl(BRASS, 0.34, 0.08, (0.9, -0.02, 0.56), "Y", 16)
cyl(DARK, 0.27, 0.02, (0.9, -0.055, 0.56), "Y", 16)
for k in range(5):
    z = 0.56 + (k - 2) * 0.09
    wide = math.sqrt(max(0.0, 0.25 * 0.25 - (z - 0.56) ** 2))
    flat(BRASS, [(0.9 - wide, z - 0.017), (0.9 + wide, z - 0.017), (0.9 + wide, z + 0.017), (0.9 - wide, z + 0.017)], -0.068)
valve(0.32, 0.56, 0.2)
# pipes and wires that shape its outline, every one made fast: a pipe out of the left foot, over
# the scope's head and into the small dial's head; one from that head down the right side into the
# foot; a copper loop off the left side; cables slung between terminals on the heads; an aerial
depth = SMALL_DIALS["Depth"]
run(BRASS, [(-half - 0.06, 0.18, 0.12), (-half - 0.06, 0.18, 1.3)] + ring_points(SCOPE, 1.085, 170.0, 25.0, 0.18, 6) + [(depth[0] - 0.42, 0.18, depth[1] + 0.2)], 0.08, ("Z", "-X"))
run(BRASS, [(depth[0] + 0.42, 0.18, depth[1] + 0.2), (half + 0.06, 0.18, depth[1] + 0.05), (half + 0.07, 0.18, 1.9), (half + 0.07, 0.18, 0.12)], 0.08, ("X", "Z"))
for at in ((-half - 0.06, 0.18, 0.75), (half + 0.07, 0.18, 1.3), (half + 0.07, 0.18, 0.6)):
    collar(at, 0.08)
run(COPPER, [(-half, 0.12, 2.2), (-half - 0.1, 0.12, 2.1), (-half - 0.12, 0.12, 1.78), (-half, 0.12, 1.62)], 0.05, ("-X", "-X"))
run(RUBBER, [(SCOPE[0] - 0.15, -0.02, SCOPE[1] + 0.92), (0.1, -0.12, SCOPE[1] + 1.14), (0.7, -0.1, SCOPE[1] + 1.0), (depth[0] - 0.1, -0.02, depth[1] + 0.4)], 0.04, ("Y", "Y"), 4)
run(RUBBER, [(SCOPE[0] - 0.6, -0.02, SCOPE[1] + 0.74), (-1.25, -0.1, SCOPE[1] + 0.96), (-half - 0.07, 0.05, SCOPE[1] + 0.3), (-half, 0.12, BODY - 0.5)], 0.04, ("Y", "-X"), 4)
flange((1.3, 0.16, BODY), 0.05, "Z")
cyl(STEEL, 0.03, 1.2, (1.3, 0.16, BODY + 0.6), "Z", 6)
ball(BRASS, 0.07, (1.3, 0.16, BODY + 1.22))
gauges = join("Gauges")
marker("Scope", (SCOPE[0], -0.12, SCOPE[1]), gauges)
marker("ScopeEdge", (SCOPE[0] + SCOPE_R, -0.12, SCOPE[1]), gauges)
for name, (x, z) in SMALL_DIALS.items():
    needle(name, x, z, SMALL_DIAL_R, gauges)

meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
triangles = 0
for obj in meshes:
    obj.data.calc_loop_triangles()
    triangles += len(obj.data.loop_triangles)
print("PANEL triangles %d; side %.2f x %.2f; well z %.2f; slot r %.2f from %.1f to %.1f deg; gauges %.2f x %.2f; swing %.1f"
      % (triangles, SIDE_WIDE, SIDE_TALL, WELL_Z, SLOT_R, math.degrees(SLOT_FROM), math.degrees(SLOT_TO), GAUGE_WIDE, GAUGE_TALL, SWING))

# --- The paint: every part unwrapped into one atlas, and colour, light and contact shadow baked
# into it. The housings are stood apart for the bake (as built they overlap: the game places them).
bpy.ops.object.select_all(action="DESELECT")
for obj in meshes:
    obj.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=0.002)
bpy.ops.uv.average_islands_scale()
bpy.ops.uv.pack_islands(margin=0.002)
bpy.ops.object.mode_set(mode="OBJECT")

if BAKE:
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 96
    scene.cycles.device = "CPU"
    world = bpy.data.worlds.new("sky")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.9, 0.86, 0.8, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.55
    scene.world = world
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 1.7
    sun.angle = math.radians(12.0)
    lamp = bpy.data.objects.new("sun", sun)
    bpy.context.collection.objects.link(lamp)
    # (from the upper left, in front)
    lamp.rotation_euler = (math.radians(58.0), 0.0, math.radians(-32.0))
    image = bpy.data.images.new("panel_atlas", ATLAS_SIZE, ATLAS_SIZE, alpha=False)
    for made in bpy.data.materials:
        node = made.node_tree.nodes.new("ShaderNodeTexImage")
        node.image = image
        made.node_tree.nodes.active = node
    engine.location.x = 8.0
    gauges.location.x = -8.0
    bpy.context.view_layer.update()
    bodies = [helm, engine, gauges]
    movers = [obj for obj in meshes if obj not in bodies]
    scene.render.bake.margin = 6
    # first the housings, with nothing that moves in the way (its shadow would stay behind) ...
    for obj in movers:
        obj.hide_render = True
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bodies:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = bodies[0]
    bpy.ops.object.bake(type="COMBINED", use_clear=True)
    # ... then the moving parts, in their places
    for obj in movers:
        obj.hide_render = False
    bpy.ops.object.select_all(action="DESELECT")
    for obj in movers:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = movers[0]
    bpy.ops.object.bake(type="COMBINED", use_clear=False)
    engine.location.x = 0.0
    gauges.location.x = 0.0
    bpy.context.view_layer.update()
    os.makedirs(os.path.dirname(ATLAS), exist_ok=True)
    image.filepath_raw = ATLAS
    image.file_format = "PNG"
    image.save()
    print("PANEL baked", ATLAS)

os.makedirs(os.path.dirname(BLEND), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
bpy.ops.object.select_all(action="DESELECT")
for obj in bpy.data.objects:
    if obj.type in ("MESH", "EMPTY"):
        obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=GLB, export_format="GLB", export_apply=True, export_yup=True, use_selection=True, export_image_format="NONE")
print("PANEL wrote", GLB)
