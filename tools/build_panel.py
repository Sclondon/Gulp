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
          is Claude's pick of place)
  Switches (a small box): two knife switches for special abilities that do not exist yet
  Aux     (a small box): the pause button, and two vacuum tubes (TubeGlass: their clear glass)

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

SIDE_WIDE = 2.6
SIDE_TALL = 3.9
SHOULDER = 2.55    # the side housings' square part; over it an arched head round the big dial
BODY = 1.3         # the instrument housing's square part; over it heads round the scope and a dial
WELL_Z = 1.3       # the socket's and the plunger's middle, above the foot
WELL_OUT = 1.08    # their brass ring (the user: "The boost and joysrick areas look small")
ENGINE_WELL_X = 0.15              # the plunger sits a little right, so its slot clears the left edge
SLOT_R = 1.3       # the lever's slot: an arc round the plunger's left
SLOT_FROM = math.radians(200.0)   # dead slow (lower left)
SLOT_TO = math.radians(108.0)     # full ahead (the top)
HELM_DIAL = (0.0, 3.1)            # the growth dial on the helm
ENGINE_DIAL = (0.5, 3.1)          # the speed dial on the engine, clear of the slot's top end
BIG_DIAL_R = 0.5
GAUGE_WIDE = 3.3
GAUGE_TALL = 2.3
SCOPE = (-0.55, 1.12)
SCOPE_R = 0.78
SMALL_DIALS = {"Depth": (1.02, 1.85), "Burst": (1.02, 0.78)}
SMALL_DIAL_R = 0.26
SMALL_WIDE = 1.5   # the switch box and the valve box
SMALL_TALL = 1.1
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
    for k, (patch, low, high, scale) in enumerate(((patch_a, 0.3, 0.8, 1.0), (patch_b or patch_a, 0.42, 0.85, 0.7))):
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


IRON = material("iron", (0.085, 0.07, 0.062), (0.13, 0.07, 0.04), (0.075, 0.1, 0.085), 1.6)
BRASS = material("brass", (0.27, 0.2, 0.1), (0.19, 0.14, 0.08), (0.16, 0.17, 0.12), 1.2, 0.5)
COPPER = material("copper", (0.26, 0.13, 0.08), (0.18, 0.1, 0.07), (0.12, 0.17, 0.14), 0.9, 0.5)
RUBBER = material("rubber", (0.02, 0.02, 0.025), None, None, 1.0, 0.6)
DARK = material("dark", (0.004, 0.003, 0.003))
PAPER = material("paper", (0.52, 0.45, 0.31), (0.42, 0.34, 0.22), (0.47, 0.4, 0.27), 0.8)
INK = material("ink", (0.02, 0.012, 0.008))
RED = material("red", (0.27, 0.035, 0.028), (0.16, 0.035, 0.03), (0.17, 0.06, 0.04), 0.7)
ORANGE = material("orange", (0.5, 0.2, 0.04))
GREEN = material("green", (0.13, 0.21, 0.08))
STEEL = material("steel", (0.15, 0.15, 0.14), (0.12, 0.08, 0.05), (0.1, 0.1, 0.095), 0.9, 0.5)
SCREEN = material("screen", (0.005, 0.07, 0.012), (0.008, 0.11, 0.02), None, 0.9, 0.3)
LAMP = material("lamp", (0.16, 0.08, 0.045), (0.12, 0.06, 0.035), None, 0.8, 0.4)
GLASS = material("glass", (0.5, 0.6, 0.55))
EMBER = material("ember", (1.0, 0.4, 0.08))
next(n for n in EMBER.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Emission Color"].default_value = (1.0, 0.35, 0.05, 1.0)
next(n for n in EMBER.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Emission Strength"].default_value = 6.0

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
    return 6 if sides <= 10 else 10 if sides <= 16 else 16 if sides <= 28 else 24


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
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, segments=10 if fine <= 16 else 16, ring_count=5 if fine <= 16 else 8, location=at)
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
    split.split_angle = math.radians(42.0)
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


def well(x, mat_inside):
    """The brass ring and the recess of a socket or a button, at the housing's well."""
    cyl(BRASS, WELL_OUT, 0.1, (x, -0.02, WELL_Z), "Y", 32)
    torus(BRASS, WELL_OUT - 0.11, 0.1, (x, -0.07, WELL_Z), "Y", 32)
    cyl(mat_inside, WELL_OUT - 0.22, 0.02, (x, -0.105, WELL_Z), "Y", 32)
    for k in range(6):
        a = math.tau * (k + 0.5) / 6.0
        rivet(x + math.cos(a) * (WELL_OUT - 0.06), WELL_Z + math.sin(a) * (WELL_OUT - 0.06), 0.045, -0.07)


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
    if label:
        sign(x, z - r * 0.55, r * 0.3, label, face - 0.001)
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


def words(text, x, z, high, front):
    """Lettering in ink on a face, its middle at (x, z)."""
    curve = bpy.data.curves.new("words", "FONT")
    curve.body = text
    curve.size = high
    curve.align_x = "CENTER"
    curve.align_y = "CENTER"
    curve.resolution_u = 1
    obj = bpy.data.objects.new("words", curve)
    bpy.context.collection.objects.link(obj)
    obj.location = (x, front, z)
    obj.rotation_euler = (math.pi * 0.5, 0.0, 0.0)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.object.convert(target="MESH")
    obj = keep(INK)
    settle(obj)
    return obj


def plaque(text, x, z, wide, front=-0.13):
    """A brass label plate with a word on it, held by two rivets (the user: "The dials need way
    better labels")."""
    high = wide * 0.27
    box(BRASS, (wide, 0.05, high), (x, front + 0.025, z))
    words(text, x, z - high * 0.02, high * 0.62, front - 0.003)
    for side in (-1.0, 1.0):
        rivet(x + side * (wide * 0.5 - high * 0.22), z, high * 0.14, front)


def outline(inner, dial_at):
    """Pipes and wires that shape a side housing's outline (the user: "Still not enough pipes /
    wires shaping the ui outline", "they should hug the panel tighter"), every one made fast at
    both ends: a pipe over its arched head from shoulder to shoulder, loops standing off its inner
    side (`inner` 1: its right, -1: its left), wires from terminals on the head's crown down into
    the housing's sides."""
    half = SIDE_WIDE * 0.5
    side = "X" if inner > 0.0 else "-X"
    other = "-X" if inner > 0.0 else "X"
    over = ring_points(dial_at, 0.885, 180.0, 0.0, 0.16, 7)
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
    run(COPPER, [(inner * half, 0.12, 2.5), (inner * (half + 0.1), 0.12, 2.42), (inner * (half + 0.12), 0.12, 2.15), (inner * half, 0.12, 2.04)], 0.05, (side, side))
    # wires from terminals on the head's crown, drooping down into the housing's two sides
    for way, into in ((1.0, "X"), (-1.0, "-X")):
        run(RUBBER, [(dial_at[0] + way * 0.3, -0.02, dial_at[1] + 0.66), (dial_at[0] + way * 0.7, -0.1, dial_at[1] + 0.86), (way * (half + 0.05), 0.0, SHOULDER + 0.5),
                     (way * (half + 0.05), 0.12, SHOULDER - 0.05), (way * half, 0.12, SHOULDER - 0.3)], 0.04, ("Y", into), 4)


# --- The paint: every part unwrapped into one atlas, and colour, light and contact shadow baked
# into it.
def unwrap(meshes):
    """Lays every mesh out in one picture, at one scale."""
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


def bake(path, size, first, then=()):
    """Bakes the paint into a picture: `first` with `then` out of the way (what moves would leave
    its shadow behind), then `then` in their places. Light from the upper left, in front."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 96
    scene.cycles.device = "CPU"
    world = bpy.data.worlds.new("sky")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.85, 0.87, 0.9, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
    scene.world = world
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 1.8
    sun.angle = math.radians(12.0)
    lamp = bpy.data.objects.new("sun", sun)
    bpy.context.collection.objects.link(lamp)
    lamp.rotation_euler = (math.radians(58.0), 0.0, math.radians(-32.0))
    image = bpy.data.images.new(os.path.basename(path), size, size, alpha=False)
    for made in bpy.data.materials:
        node = made.node_tree.nodes.new("ShaderNodeTexImage")
        node.image = image
        made.node_tree.nodes.active = node
    scene.render.bake.margin = 6
    for k, group in enumerate((first, then)):
        if not group:
            continue
        for obj in then:
            obj.hide_render = k == 0
        bpy.ops.object.select_all(action="DESELECT")
        for obj in group:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = group[0]
        bpy.ops.object.bake(type="COMBINED", use_clear=k == 0)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    image.filepath_raw = path
    image.file_format = "PNG"
    image.save()
    print("PANEL baked", path)


# --- The helm housing: a socket with a rubber boot and a stick; over it the growth dial, between
# two electrodes that stand over the housing's top.
plate(SIDE_WIDE, SHOULDER, [(HELM_DIAL[0], HELM_DIAL[1], 0.8)])
side_pipe(-SIDE_WIDE * 0.5 - 0.02, SHOULDER - 0.2, 1.0)
well(0.0, DARK)
for major, out in ((0.6, -0.12), (0.45, -0.2), (0.3, -0.27)):
    torus(RUBBER, major, 0.11, (0.0, out, WELL_Z), "Y", 16)
dial(HELM_DIAL[0], HELM_DIAL[1], BIG_DIAL_R, 9, False, None)
plaque("GROWTH", HELM_DIAL[0], HELM_DIAL[1] - 0.68, 0.78)
POSTS = 1.02
for side in (-1.0, 1.0):
    # an electrode: a post on a bolted foot, an insulator, a ball
    flange((side * POSTS, -0.02, SHOULDER - 0.2), 0.11, "Y")
    run(BRASS, [(side * POSTS, -0.02, SHOULDER - 0.2), (side * POSTS, -0.13, SHOULDER - 0.12), (side * POSTS, -0.13, SHOULDER + 0.3), (side * POSTS, -0.13, SHOULDER + 0.8)], 0.085, (None, None))
    collar((side * POSTS, -0.13, SHOULDER + 0.1), 0.1)
    cyl(PAPER, 0.13, 0.12, (side * POSTS, -0.13, SHOULDER + 0.55), "Z", 8)
    ball(BRASS, 0.11, (side * POSTS, -0.13, SHOULDER + 0.9))
mini_gauge(-1.08, 0.3)
patch(1.04, 0.3, 0.42, 0.34, 0.12)
outline(1.0, HELM_DIAL)
helm = join("Helm")
marker("SparkA", (-POSTS, -0.13, SHOULDER + 0.9), helm)
marker("SparkB", (POSTS, -0.13, SHOULDER + 0.9), helm)
marker("Length", (HELM_DIAL[0], -0.12, HELM_DIAL[1] - BIG_DIAL_R * 0.5), helm)
needle("Evolve", HELM_DIAL[0], HELM_DIAL[1], BIG_DIAL_R, helm)

# the stick: a shaft out of the boot, a collar, a brass ball
cyl(STEEL, 0.1, 0.7, (0.0, -0.45, WELL_Z), "Y", 8)
cyl(BRASS, 0.18, 0.16, (0.0, -0.74, WELL_Z), "Y", 10)
ball(BRASS, 0.46, (0.0, -1.14, WELL_Z), (1.0, 1.0, 1.0), 24)
join("Stick", (0.0, 0.0, WELL_Z), helm)

# --- The engine housing: a plunger in its ring (a little to the right, to make room), a slot
# curving round its left with a lever in it, and the speed dial over them.
plate(SIDE_WIDE, SHOULDER, [(ENGINE_DIAL[0], ENGINE_DIAL[1], 0.8)])
side_pipe(SIDE_WIDE * 0.5 + 0.02, SHOULDER - 0.2, -1.0)
well(ENGINE_WELL_X, DARK)
band(BRASS, (ENGINE_WELL_X, WELL_Z), SLOT_R, 0.15, SLOT_FROM, SLOT_TO, -0.05, 0.05, 12, True)
band(DARK, (ENGINE_WELL_X, WELL_Z), SLOT_R, 0.085, SLOT_FROM, SLOT_TO, -0.052, 0.0, 12, True)
dial(ENGINE_DIAL[0], ENGINE_DIAL[1], BIG_DIAL_R, 9, True, "speed")
plaque("SPEED", ENGINE_DIAL[0], ENGINE_DIAL[1] - 0.68, 0.7)
valve(-0.95, SHOULDER + 0.28, 0.15, -0.2)
patch(1.06, 0.26, 0.36, 0.3, -0.1)
outline(-1.0, ENGINE_DIAL)
engine = join("Engine")
needle("Speed", ENGINE_DIAL[0], ENGINE_DIAL[1], BIG_DIAL_R, engine)

# the plunger: a domed button with a double chevron
cyl(BRASS, 0.78, 0.22, (ENGINE_WELL_X, -0.17, WELL_Z), "Y", 32)
cyl(LAMP, 0.7, 0.09, (ENGINE_WELL_X, -0.32, WELL_Z), "Y", 32, 0.55)
for shift in (-0.24, 0.12):
    flat(INK, [(ENGINE_WELL_X + shift - 0.07, WELL_Z + 0.28), (ENGINE_WELL_X + shift + 0.07, WELL_Z + 0.28), (ENGINE_WELL_X + shift + 0.33, WELL_Z),
               (ENGINE_WELL_X + shift + 0.07, WELL_Z - 0.28), (ENGINE_WELL_X + shift - 0.07, WELL_Z - 0.28), (ENGINE_WELL_X + shift + 0.18, WELL_Z)], -0.367)
join("Plunger", (ENGINE_WELL_X, 0.0, WELL_Z), engine)

# the lever, built standing at the top of its arc (turned about Y by the game): a boss riding in the
# slot, a tapered brass grip standing out of the housing towards the eye, a ball on its end
cyl(BRASS, 0.15, 0.1, (ENGINE_WELL_X, -0.1, WELL_Z + SLOT_R), "Y", 8)
cyl(STEEL, 0.06, 0.3, (ENGINE_WELL_X, -0.25, WELL_Z + SLOT_R), "Y", 6)
cyl(BRASS, 0.17, 0.6, (ENGINE_WELL_X, -0.65, WELL_Z + SLOT_R), "Y", 10, 0.09)
ball(BRASS, 0.2, (ENGINE_WELL_X, -0.98, WELL_Z + SLOT_R))
lever = join("Lever", (ENGINE_WELL_X, 0.0, WELL_Z), engine)
marker("Grip", (ENGINE_WELL_X, -0.8, WELL_Z + SLOT_R), lever)

# --- The instrument housing: the scope, and small dials for depth and for burst left.
depth = SMALL_DIALS["Depth"]
burst = SMALL_DIALS["Burst"]
plate(GAUGE_WIDE, BODY, [(SCOPE[0], SCOPE[1], SCOPE_R + 0.3), (depth[0], depth[1], 0.5)])
half = GAUGE_WIDE * 0.5
cyl(BRASS, SCOPE_R + 0.2, 0.1, (SCOPE[0], -0.02, SCOPE[1]), "Y", 40)
torus(BRASS, SCOPE_R + 0.1, 0.1, (SCOPE[0], -0.07, SCOPE[1]), "Y", 40)
cyl(SCREEN, SCOPE_R + 0.03, 0.02, (SCOPE[0], -0.09, SCOPE[1]), "Y", 40)
for k in range(8):
    a = math.tau * (k + 0.5) / 8.0
    rivet(SCOPE[0] + math.cos(a) * (SCOPE_R + 0.14), SCOPE[1] + math.sin(a) * (SCOPE_R + 0.14), 0.045, -0.12)
dial(depth[0], depth[1], SMALL_DIAL_R, 9, False, "depth")
plaque("DEPTH", depth[0], depth[1] - 0.47, 0.5)
dial(burst[0], burst[1], SMALL_DIAL_R, 9, True, "bolt")
plaque("BURST", burst[0], burst[1] - 0.47, 0.5)
# copper pipes from the scope's ring to each small dial's
run(COPPER, [(SCOPE[0] + SCOPE_R + 0.12, -0.04, depth[1] - 0.1), (0.45, -0.12, depth[1] + 0.02), (depth[0] - 0.36, -0.04, depth[1])], 0.04, ("Y", "Y"))
run(COPPER, [(SCOPE[0] + SCOPE_R + 0.12, -0.04, burst[1] + 0.1), (0.45, -0.12, burst[1] - 0.02), (burst[0] - 0.36, -0.04, burst[1])], 0.04, ("Y", "Y"))
# pipes and wires that shape its outline, every one made fast: a pipe out of the left foot, over
# the scope's head and into the small dial's head; one from that head down the right side into the
# foot; a cable slung between terminals on the two heads; an aerial
run(BRASS, [(-half - 0.06, 0.18, 0.12), (-half - 0.06, 0.18, 0.7)] + ring_points(SCOPE, SCOPE_R + 0.39, 165.0, 40.0, 0.18, 6) + [(depth[0] - 0.46, 0.18, depth[1] + 0.2)], 0.08, ("Z", "-X"))
run(BRASS, [(depth[0] + 0.46, 0.18, depth[1] + 0.2), (half + 0.05, 0.18, depth[1] + 0.02), (half + 0.07, 0.18, BODY), (half + 0.07, 0.18, 0.12)], 0.08, ("X", "Z"))
collar((half + 0.07, 0.18, 0.6), 0.08)
run(RUBBER, [(SCOPE[0] + 0.1, -0.02, SCOPE[1] + SCOPE_R + 0.22), (0.3, -0.12, SCOPE[1] + SCOPE_R + 0.3), (depth[0] - 0.2, -0.02, depth[1] + 0.42)], 0.04, ("Y", "Y"), 4)
flange((depth[0] + 0.25, 0.16, depth[1] + 0.42), 0.05, "Z")
cyl(STEEL, 0.03, 0.9, (depth[0] + 0.25, 0.16, depth[1] + 0.87), "Z", 6)
ball(BRASS, 0.07, (depth[0] + 0.25, 0.16, depth[1] + 1.34))
gauges = join("Gauges")
marker("Scope", (SCOPE[0], -0.12, SCOPE[1]), gauges)
marker("ScopeEdge", (SCOPE[0] + SCOPE_R, -0.12, SCOPE[1]), gauges)
needle("Depth", depth[0], depth[1], SMALL_DIAL_R, gauges)
needle("Burst", burst[0], burst[1], SMALL_DIAL_R, gauges)

# --- The switch box: two knife switches for special abilities (which do not exist yet), always in
# sight (the user: "what happend to the special ability switches?").
plate(SMALL_WIDE, SMALL_TALL)
for k, x in enumerate((-0.36, 0.36)):
    box(STEEL, (0.5, 0.06, 0.68), (x, -0.02, 0.56))
    flat(DARK, [(x - 0.05, 0.34), (x + 0.05, 0.34), (x + 0.05, 0.74), (x - 0.05, 0.74)], -0.052)
    cyl(STEEL, 0.04, 0.2, (x, -0.12, 0.72), "Y", 6)
    box(RED, (0.28, 0.2, 0.22), (x, -0.26, 0.72))
    for sx in (-1.0, 1.0):
        for sz in (0.3, 0.82):
            bolt(x + sx * 0.19, sz, 0.03, -0.05)
run(RUBBER, [(-0.36, -0.02, 0.92), (0.0, -0.1, 1.04), (0.36, -0.02, 0.92)], 0.03, ("Y", "Y"), 4)
switches = join("Switches")

# --- The valve box: a pause button (the user: "There should also be a pause button built into the
# ui panel so we can hide the x button on mobile"), and two vacuum tubes glowing beside it ("There
# should be ar lwast 1 vaccume tube thingy").
plate(SMALL_WIDE, SMALL_TALL)
PAUSE = (-0.34, 0.55)
cyl(BRASS, 0.36, 0.1, (PAUSE[0], -0.02, PAUSE[1]), "Y", 24)
torus(BRASS, 0.3, 0.06, (PAUSE[0], -0.07, PAUSE[1]), "Y", 24)
cyl(STEEL, 0.25, 0.1, (PAUSE[0], -0.1, PAUSE[1]), "Y", 24)
for side in (-1.0, 1.0):
    flat(INK, [(PAUSE[0] + side * 0.09 - 0.04, PAUSE[1] - 0.12), (PAUSE[0] + side * 0.09 + 0.04, PAUSE[1] - 0.12),
               (PAUSE[0] + side * 0.09 + 0.04, PAUSE[1] + 0.12), (PAUSE[0] + side * 0.09 - 0.04, PAUSE[1] + 0.12)], -0.152)
TUBES_AT = ((0.2, 0.3), (0.52, 0.3))
box(BRASS, (0.66, 0.26, 0.1), (0.36, -0.13, 0.25))
for x, z in TUBES_AT:
    cyl(BRASS, 0.11, 0.1, (x, -0.14, z + 0.04), "Z", 10)
    # the works inside: a grey plate round a glowing filament, a getter on top
    cyl(STEEL, 0.06, 0.26, (x, -0.14, z + 0.25), "Z", 6)
    cyl(EMBER, 0.02, 0.34, (x, -0.14, z + 0.27), "Z", 6)
    cyl(STEEL, 0.05, 0.02, (x, -0.14, z + 0.47), "Z", 6)
run(RUBBER, [(0.2, -0.02, 0.95), (0.36, -0.1, 1.02), (0.52, -0.02, 0.95)], 0.03, ("Y", "Y"), 4)
aux = join("Aux")
marker("Pause", (PAUSE[0], -0.15, PAUSE[1]), aux)
# the tubes' glass: clear, so not in the paint (the game draws it with its own shader)
for x, z in TUBES_AT:
    cyl(GLASS, 0.1, 0.4, (x, -0.14, z + 0.3), "Z", 10)
    ball(GLASS, 0.1, (x, -0.14, z + 0.5))
glass = join("TubeGlass", (0.0, 0.0, 0.0), aux)

meshes = [obj for obj in bpy.data.objects if obj.type == "MESH" and obj != glass]
triangles = 0
for obj in meshes:
    obj.data.calc_loop_triangles()
    triangles += len(obj.data.loop_triangles)
print("PANEL triangles %d; side %.2f x %.2f; well z %.2f; slot r %.2f from %.1f to %.1f deg; gauges %.2f x %.2f; swing %.1f"
      % (triangles, SIDE_WIDE, SIDE_TALL, WELL_Z, SLOT_R, math.degrees(SLOT_FROM), math.degrees(SLOT_TO), GAUGE_WIDE, GAUGE_TALL, SWING))

# The housings are stood apart for the bake (as built they overlap: the game places them).
unwrap(meshes)
if BAKE:
    bodies = [helm, engine, gauges, switches, aux]
    for k, body in enumerate(bodies):
        body.location.x = 8.0 * k
    glass.hide_render = True
    bpy.context.view_layer.update()
    bake(ATLAS, ATLAS_SIZE, bodies, [obj for obj in meshes if obj not in bodies])
    for body in bodies:
        body.location.x = 0.0
    bpy.context.view_layer.update()

os.makedirs(os.path.dirname(BLEND), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
bpy.ops.object.select_all(action="DESELECT")
for obj in bpy.data.objects:
    if obj.type in ("MESH", "EMPTY"):
        obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=GLB, export_format="GLB", export_apply=True, export_yup=True, use_selection=True, export_image_format="NONE")
print("PANEL wrote", GLB)
