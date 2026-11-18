"""Builds the control panel as a 3D model: three rusted housings with their moving parts.

    blender --background --python tools/build_panel.py

Writes models/control_panel.glb and tools/blend/control_panel.blend. The user (2026-11-18):
"lets recreate the ui as a 3d model to interact with", "the model should be very similar in
style to the first concpet art- though the texture needs to be less noisy" (the first concept is
tools/art_src/panel_concept_1.png: rusted plate with verdigris, brass rings and pipes, red valve
wheels, a copper coil, dials with coloured ends, an orange plunger). Laid out as the user drew
it: "The sonar map should be bigger and hust off center to the left, the speed dial should be
above the boost and soeed controls to the right and bigger, and the evolution dial should be
above the joystick to the left. There can be a little dwpth dial next to sonar".

  Helm    (bottom left): the socket and stick, the evolution dial over it, two electrodes
  Engine  (bottom right): the plunger, the lever's slot curving round it, the speed dial over it
  Gauges  (between): the sonar scope, small dials for depth and for burst left (the burst dial
          is Claude's pick of place), two switches, a grille, a valve wheel, a coil

Units: 1 m here is 100 of TouchPad's layout units. Each housing's origin is the middle of its foot,
its face towards -Y (Godot's +Z, the camera), Z up. scripts/panel_model.gd places and moves the
parts by these names:
  Helm    > Stick (pivot in the socket), NeedleEvolve, SparkA, SparkB (the electrodes' tips)
  Engine  > Plunger (pushed in along +Y), Lever (turned about Y round the plunger) > Grip,
            NeedleSpeed
  Gauges  > NeedleDepth, NeedleBurst, Scope, ScopeEdge
Needles point straight up as built and turn about Y, 2.2 radians either way.
Materials are plain colours with names; the game swaps each for its painted shader by name.
The numbers in CAPITALS are printed at the end as the PANEL line, and panel_model.gd holds the
same ones: change both.
"""
import bpy
import bmesh
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
GLB = os.path.join(HERE, "..", "models", "control_panel.glb")
BLEND = os.path.join(HERE, "blend", "control_panel.blend")

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


def material(name, colour):
    made = bpy.data.materials.new(name)
    made.use_nodes = True
    shader = next(n for n in made.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    shader.inputs["Base Color"].default_value = (*colour, 1.0)
    shader.inputs["Roughness"].default_value = 0.6
    return made


IRON = material("iron", (0.42, 0.2, 0.08))
BRASS = material("brass", (0.72, 0.45, 0.13))
COPPER = material("copper", (0.75, 0.32, 0.15))
RUBBER = material("rubber", (0.03, 0.03, 0.035))
DARK = material("dark", (0.01, 0.01, 0.012))
PAPER = material("paper", (0.85, 0.75, 0.5))
INK = material("ink", (0.05, 0.03, 0.02))
RED = material("red", (0.7, 0.08, 0.05))
ORANGE = material("orange", (0.85, 0.45, 0.08))
GREEN = material("green", (0.3, 0.5, 0.15))
STEEL = material("steel", (0.4, 0.4, 0.38))
SCREEN = material("screen", (0.03, 0.2, 0.05))
LAMP = material("lamp", (0.35, 0.2, 0.1))

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


def box(mat, size, at, bevel=0.03):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=at)
    obj = keep(mat)
    obj.scale = size
    settle(obj)
    if bevel > 0.0:
        mod = obj.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        bpy.ops.object.modifier_apply(modifier="bevel")
    return obj


def cyl(mat, radius, depth, at, axis="Y", sides=28, bevel=0.0, top=None):
    """A cylinder (or, with `top`, a cone frustum)."""
    if top is None:
        bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, vertices=sides, location=at, rotation=TURN[axis])
    else:
        bpy.ops.mesh.primitive_cone_add(radius1=radius, radius2=top, depth=depth, vertices=sides, location=at, rotation=TURN[axis])
    obj = keep(mat)
    settle(obj)
    if bevel > 0.0:
        mod = obj.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        mod.limit_method = "ANGLE"
        bpy.ops.object.modifier_apply(modifier="bevel")
    return obj


def ball(mat, radius, at, squash=(1.0, 1.0, 1.0), fine=16):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, segments=fine, ring_count=fine // 2, location=at)
    obj = keep(mat)
    obj.scale = squash
    settle(obj)
    return obj


def torus(mat, major, minor, at, axis="Y", fine=32):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=fine, minor_segments=8, location=at, rotation=TURN[axis])
    obj = keep(mat)
    settle(obj)
    return obj


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


def band(mat, middle, radius, half, a0, a1, front, depth, steps=24, round_ends=False):
    """A curved band in the face's plane round `middle` (x, z), from angle a0 to a1."""
    def at(a, r):
        return (middle[0] + math.cos(a) * r, middle[1] + math.sin(a) * r)
    outer = [at(a0 + (a1 - a0) * k / steps, radius + half) for k in range(steps + 1)]
    inner = [at(a0 + (a1 - a0) * k / steps, radius - half) for k in range(steps + 1)]
    cap0 = []
    cap1 = []
    if round_ends:
        way = 1.0 if a1 > a0 else -1.0
        for k in range(1, 6):
            b = math.pi * k / 6.0
            # past the a1 end, from the outer edge round to the inner; past the a0 end, inner to outer
            c1 = at(a1, radius)
            cap1.append((c1[0] + math.cos(a1) * half * math.cos(b) - math.sin(a1) * way * half * math.sin(b),
                         c1[1] + math.sin(a1) * half * math.cos(b) + math.cos(a1) * way * half * math.sin(b)))
            c0 = at(a0, radius)
            cap0.append((c0[0] - math.cos(a0) * half * math.cos(b) + math.sin(a0) * way * half * math.sin(b),
                         c0[1] - math.sin(a0) * half * math.cos(b) - math.cos(a0) * way * half * math.sin(b)))
    return prism(mat, outer + cap1 + inner[::-1] + cap0, front, depth)


def pipe(mat, points, radius, fine=5):
    """A pipe through points (x, y, z), its bends rounded."""
    curve = bpy.data.curves.new("pipe", "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = radius
    curve.bevel_resolution = 2
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


def collar(at, radius, axis="Z"):
    """A brass flange round a pipe."""
    cyl(BRASS, radius * 1.45, radius * 0.9, at, axis, 16, 0.01)


def rivet(x, z, size=0.075, front=0.0):
    ball(BRASS, size, (x, front, z), (1.0, 0.6, 1.0), 10)


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
    # smooth, with hard edges kept; normals outward
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    for poly in obj.data.polygons:
        poly.use_smooth = True
    split = obj.modifiers.new("split", "EDGE_SPLIT")
    split.split_angle = math.radians(38.0)
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
    box(IRON, (wide, thick, tall), (0.0, thick * 0.5, tall * 0.5), 0.07)
    for x, z, r in heads:
        cyl(IRON, r, thick, (x, thick * 0.5, z), "Y", 40, 0.06)
        torus(IRON, r - 0.05, 0.05, (x, 0.0, z), "Y", 40)
        count = int(r * 14)
        for k in range(count):
            a = math.tau * (k + 0.5) / count
            if z + math.sin(a) * r > tall - 0.1:
                bolt(x + math.cos(a) * (r - 0.14), z + math.sin(a) * (r - 0.14), 0.04)
    for side in (-1.0, 1.0):
        box(IRON, (0.09, 0.07, tall - 0.1), (side * (wide * 0.5 - 0.045), -0.02, tall * 0.5), 0.02)
        rows = max(2, round((tall - 0.4) / 0.5) + 1)
        for k in range(rows):
            rivet(side * (wide * 0.5 - 0.2), 0.2 + (tall - 0.4) * k / (rows - 1.0), 0.06)
        cyl(BRASS, 0.2, 0.16, (side * (wide * 0.5 - 0.3), thick * 0.5, 0.02), "Z", 16, 0.02)
        # a brass corner bracket at each foot
        prism(BRASS, [(side * wide * 0.5, 0.0), (side * (wide * 0.5 - 0.34), 0.0), (side * wide * 0.5, 0.34)], -0.06, 0.05)
    box(IRON, (wide - 0.1, 0.07, 0.09), (0.0, -0.02, 0.045), 0.02)
    across = max(2, round((wide - 0.4) / 0.5) + 1)
    for k in range(1, across - 1):
        rivet(-wide * 0.5 + 0.2 + (wide - 0.4) * k / (across - 1.0), 0.2, 0.06)


def bolt(x, z, size=0.05, front=0.0):
    """A six-sided bolt head."""
    cyl(STEEL, size, size * 0.9, (x, front - size * 0.4, z), "Y", 6)


def patch(x, z, wide, tall, turn):
    """A smaller sheet of iron bolted over the plate, a little askew."""
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(x, -0.02, z), rotation=(0.0, turn, 0.0))
    obj = keep(IRON)
    obj.scale = (wide, 0.06, tall)
    settle(obj)
    mod = obj.modifiers.new("bevel", "BEVEL")
    mod.width = 0.015
    mod.segments = 2
    bpy.ops.object.modifier_apply(modifier="bevel")
    for sx in (-1.0, 1.0):
        for sz in (-1.0, 1.0):
            px = sx * (wide * 0.5 - 0.06)
            pz = sz * (tall * 0.5 - 0.06)
            bolt(x + px * math.cos(turn) + pz * math.sin(turn), z - px * math.sin(turn) + pz * math.cos(turn), 0.035, -0.05)


def thin(points, radius=0.045, mat=None):
    """A thin copper pipe across a face, with a brass union at each end."""
    pipe(mat or COPPER, points, radius, 4)
    for at in (points[0], points[-1]):
        cyl(BRASS, radius * 1.9, radius * 2.6, at, "Y", 10, 0.008)


def mini_gauge(x, z, r=0.15):
    """A small pressure gauge with a fixed needle: furniture."""
    cyl(BRASS, r + 0.03, 0.1, (x, -0.02, z), "Y", 16, 0.01)
    torus(BRASS, r, 0.035, (x, -0.07, z), "Y", 16)
    cyl(PAPER, r - 0.01, 0.02, (x, -0.075, z), "Y", 16)
    prism(INK, [(x - 0.012, z - 0.02), (x + 0.012, z - 0.02), (x + r * 0.55, z + r * 0.6)], -0.09, 0.008)


def side_pipe(x, tall, lean):
    """A pipe up a housing's side that bends in over its top."""
    pipe(BRASS, [(x, 0.2, 0.1), (x, 0.2, tall - 0.25), (x + lean * 0.12, 0.2, tall + 0.08), (x + lean * 0.45, 0.2, tall + 0.14)], 0.11)
    collar((x, 0.2, 0.55), 0.11)
    collar((x, 0.2, tall - 0.55), 0.11)


def well(mat_inside):
    """The brass ring and the recess of a socket or a button, at the housing's well."""
    torus(BRASS, WELL_OUT - 0.11, 0.11, (0.0, -0.02, WELL_Z))
    cyl(BRASS, WELL_OUT - 0.1, 0.08, (0.0, 0.0, WELL_Z), "Y", 32)
    cyl(mat_inside, WELL_OUT - 0.22, 0.02, (0.0, -0.045, WELL_Z), "Y", 32)
    for k in range(6):
        a = math.tau * (k + 0.5) / 6.0
        rivet(math.cos(a) * (WELL_OUT - 0.11), WELL_Z + math.sin(a) * (WELL_OUT - 0.11), 0.05, -0.12)


def turn_of(value):
    """The angle in the face's plane a needle points at for a value 0..1."""
    return math.pi * 0.5 + SWING - 2.0 * SWING * value


def dial(x, z, r, marks, hot):
    """A dial's fixed parts: a brass ring, a paper face, `marks` ticks from the lower left stop over
    the top to the lower right, and (hot) orange and red stretches at its top end."""
    torus(BRASS, r + 0.07, 0.25 * r + 0.02, (x, -0.03, z), "Y", 28)
    cyl(BRASS, r + 0.09, 0.07, (x, 0.0, z), "Y", 28)
    cyl(PAPER, r + 0.03, 0.06, (x, -0.02, z), "Y", 28)
    if hot:
        band(GREEN, (x, z), r * 0.86, r * 0.07, turn_of(0.0), turn_of(0.62), -0.05, 0.008, 16)
        band(ORANGE, (x, z), r * 0.86, r * 0.07, turn_of(0.62), turn_of(0.82), -0.05, 0.008, 8)
        band(RED, (x, z), r * 0.86, r * 0.07, turn_of(0.82), turn_of(1.0), -0.05, 0.008, 8)
    for k in range(marks):
        a = turn_of(k / (marks - 1.0))
        long = r * (0.3 if hot and k % 4 == 0 or not hot else 0.17)
        wide = r * 0.04
        far = r * (0.76 if hot else 0.92)
        c = math.cos(a)
        s = math.sin(a)
        prism(INK, [(x + c * (far - long) - s * wide, z + s * (far - long) + c * wide), (x + c * far - s * wide, z + s * far + c * wide),
                    (x + c * far + s * wide, z + s * far - c * wide), (x + c * (far - long) + s * wide, z + s * (far - long) - c * wide)], -0.052, 0.01)
    for k in range(4):
        a = math.tau * (k + 0.5) / 4.0
        rivet(x + math.cos(a) * (r + 0.07), z + math.sin(a) * (r + 0.07), 0.03 + r * 0.03, -0.03 - 0.25 * r - 0.02)


def needle(name, x, z, r, parent):
    prism(RED, [(x - r * 0.07, z - r * 0.2), (x + r * 0.07, z - r * 0.2), (x, z + r * 0.86)], -0.08, 0.012)
    cyl(BRASS, r * 0.14, 0.035, (x, -0.09, z), "Y", 12)
    join("Needle" + name, (x, 0.0, z), parent)


def valve(x, z, r, front=-0.16):
    """A red valve wheel on a brass stem."""
    cyl(BRASS, r * 0.3, 0.2, (x, front + 0.1, z), "Y", 12)
    torus(RED, r, r * 0.16, (x, front, z), "Y", 24)
    for k in range(4):
        a = math.pi * k / 4.0
        c = math.cos(a)
        s = math.sin(a)
        w = r * 0.09
        prism(RED, [(x - c * r - s * w, z - s * r + c * w), (x + c * r - s * w, z + s * r + c * w),
                    (x + c * r + s * w, z + s * r - c * w), (x - c * r + s * w, z - s * r - c * w)], front - 0.02, 0.04)
    ball(BRASS, r * 0.26, (x, front - 0.03, z), (1.0, 0.7, 1.0), 10)


def ring_points(middle, radius, a0, a1, y, count=7):
    """Points on an arc in the face's plane (degrees), for a pipe that hugs a round head."""
    out = []
    for k in range(count):
        a = math.radians(a0 + (a1 - a0) * k / (count - 1.0))
        out.append((middle[0] + math.cos(a) * radius, y, middle[1] + math.sin(a) * radius))
    return out


def outline(inner):
    """Pipes and wires that shape a side housing's outline (the user: "Still not enough pipes /
    wires shaping the ui outline"): a pipe over its arched head, loops standing off its inner
    side (`inner` 1: its right, -1: its left), wires drooping from the head."""
    half = SIDE_WIDE * 0.5
    over = ring_points(BIG_DIAL, 0.95, 212.0, -32.0, 0.14, 9)
    pipe(BRASS, over, 0.075)
    for k in (2, 4, 6):
        ball(BRASS, 0.115, over[k], (1.0, 1.0, 1.0), 10)
    # a fat loop off the inner side, low down, with a valve on it
    pipe(BRASS, [(inner * (half - 0.15), 0.14, 1.62), (inner * (half + 0.22), 0.14, 1.55), (inner * (half + 0.33), 0.14, 1.15),
                 (inner * (half + 0.33), 0.14, 0.55), (inner * (half + 0.2), 0.14, 0.18), (inner * (half - 0.15), 0.14, 0.14)], 0.095)
    collar((inner * (half + 0.33), 0.14, 0.85), 0.095)
    valve(inner * (half + 0.33), 1.2, 0.15, -0.02)
    # a thin copper loop over it
    pipe(COPPER, [(inner * (half - 0.1), 0.1, 2.3), (inner * (half + 0.2), 0.1, 2.22), (inner * (half + 0.24), 0.1, 1.95), (inner * (half - 0.1), 0.1, 1.82)], 0.05, 4)
    # wires from the head's crown, drooping down outside the inner shoulder and the outer one
    for way, reach in ((inner, 1.0), (-inner, 0.8)):
        pipe(RUBBER, [(way * 0.25, -0.04, BIG_DIAL[1] + 0.72), (way * 0.8 * reach, -0.08, BIG_DIAL[1] + 0.98), (way * (half + 0.18) * reach, 0.0, BIG_DIAL[1] + 0.5),
                      (way * (half + 0.12) * reach, 0.1, SHOULDER + 0.05), (way * (half - 0.12), 0.1, SHOULDER - 0.2)], 0.04, 5)
    cyl(BRASS, 0.09, 0.12, (inner * 0.25, -0.06, BIG_DIAL[1] + 0.72), "Y", 10, 0.01)
    cyl(BRASS, 0.09, 0.12, (-inner * 0.25, -0.06, BIG_DIAL[1] + 0.72), "Y", 10, 0.01)


# --- The helm housing: a socket with a rubber boot and a stick; over it the evolution dial,
# between two electrodes that stand over the housing's top.
plate(SIDE_WIDE, SHOULDER, [(BIG_DIAL[0], BIG_DIAL[1], 0.8)])
side_pipe(-SIDE_WIDE * 0.5 - 0.02, SHOULDER - 0.2, 1.0)
well(DARK)
for major, out in ((0.46, -0.07), (0.36, -0.13), (0.27, -0.18)):
    torus(RUBBER, major, 0.085, (0.0, out, WELL_Z), "Y", 24)
dial(BIG_DIAL[0], BIG_DIAL[1], BIG_DIAL_R, 9, False)
POSTS = 0.84
for side in (-1.0, 1.0):
    cyl(BRASS, 0.09, 1.3, (side * POSTS, -0.14, SHOULDER + 0.2), "Z", 16)
    collar((side * POSTS, -0.14, SHOULDER - 0.32), 0.1)
    collar((side * POSTS, -0.14, SHOULDER + 0.05), 0.1)
    collar((side * POSTS, -0.14, SHOULDER + 0.6), 0.09)
    ball(BRASS, 0.1, (side * POSTS, -0.14, SHOULDER + 0.9), (1.0, 1.0, 1.0), 12)
    # a cable from the post's foot down to the socket's ring
    pipe(RUBBER, [(side * POSTS, -0.2, SHOULDER - 0.4), (side * (POSTS + 0.12), -0.2, SHOULDER - 0.62), (side * (POSTS - 0.02), -0.14, SHOULDER - 0.8)], 0.035, 4)
thin([(-1.0, -0.06, 2.02), (-0.4, -0.06, 1.98), (0.35, -0.06, 2.03), (1.0, -0.06, 1.98)])
mini_gauge(-0.86, 0.32)
patch(0.82, 0.34, 0.42, 0.36, 0.12)
outline(1.0)
helm = join("Helm")
marker("SparkA", (-POSTS, -0.14, SHOULDER + 0.9), helm)
marker("SparkB", (POSTS, -0.14, SHOULDER + 0.9), helm)
needle("Evolve", BIG_DIAL[0], BIG_DIAL[1], BIG_DIAL_R, helm)

# the stick: a shaft out of the boot, a collar, a brass ball
cyl(STEEL, 0.085, 0.62, (0.0, -0.36, WELL_Z), "Y", 12)
cyl(BRASS, 0.15, 0.14, (0.0, -0.62, WELL_Z), "Y", 16, 0.02)
ball(BRASS, 0.36, (0.0, -0.95, WELL_Z), (1.0, 1.0, 1.0), 24)
join("Stick", (0.0, 0.0, WELL_Z), helm)

# --- The engine housing: a plunger in its ring, a slot curving round it with a lever in it, and
# the speed dial over them.
plate(SIDE_WIDE, SHOULDER, [(BIG_DIAL[0], BIG_DIAL[1], 0.8)])
side_pipe(SIDE_WIDE * 0.5 + 0.02, SHOULDER - 0.2, -1.0)
well(DARK)
band(BRASS, (0.0, WELL_Z), SLOT_R, 0.15, SLOT_FROM, SLOT_TO, -0.03, 0.06, 28, True)
band(DARK, (0.0, WELL_Z), SLOT_R, 0.085, SLOT_FROM, SLOT_TO, -0.045, 0.04, 28, True)
dial(BIG_DIAL[0], BIG_DIAL[1], BIG_DIAL_R, 9, True)
valve(0.86, SHOULDER - 0.28, 0.17)
thin([(0.86, -0.06, SHOULDER - 0.5), (0.99, -0.06, 1.75), (0.99, -0.06, 0.95), (0.99, -0.06, 0.3)])
mini_gauge(-0.86, 2.22)
patch(-0.82, 0.32, 0.4, 0.34, -0.1)
outline(-1.0)
engine = join("Engine")
needle("Speed", BIG_DIAL[0], BIG_DIAL[1], BIG_DIAL_R, engine)

# the plunger: a domed button with a double chevron
cyl(BRASS, 0.56, 0.2, (0.0, -0.1, WELL_Z), "Y", 32, 0.03)
ball(LAMP, 0.5, (0.0, -0.2, WELL_Z), (1.0, 0.22, 1.0), 24)
for shift in (-0.17, 0.09):
    prism(INK, [(shift - 0.05, WELL_Z + 0.2), (shift + 0.05, WELL_Z + 0.2), (shift + 0.24, WELL_Z), (shift + 0.05, WELL_Z - 0.2),
                (shift - 0.05, WELL_Z - 0.2), (shift + 0.13, WELL_Z)], -0.325, 0.04)
join("Plunger", (0.0, 0.0, WELL_Z), engine)

# the lever, built standing at the top of its arc (turned about Y by the game): a boss riding in the
# slot, a tapered brass grip standing out of the housing towards the eye, a ball on its end
cyl(BRASS, 0.13, 0.1, (0.0, -0.08, WELL_Z + SLOT_R), "Y", 16, 0.02)
cyl(STEEL, 0.05, 0.3, (0.0, -0.2, WELL_Z + SLOT_R), "Y", 10)
cyl(BRASS, 0.15, 0.55, (0.0, -0.6, WELL_Z + SLOT_R), "Y", 16, 0.0, 0.08)
ball(BRASS, 0.16, (0.0, -0.9, WELL_Z + SLOT_R), (1.0, 1.0, 1.0), 16)
lever = join("Lever", (0.0, 0.0, WELL_Z), engine)
marker("Grip", (0.0, -0.75, WELL_Z + SLOT_R), lever)

# --- The instrument housing: the scope, two small dials, two switches, a grille, a valve, a coil.
plate(GAUGE_WIDE, BODY, [(SCOPE[0], SCOPE[1], 1.0), (SMALL_DIALS["Depth"][0], SMALL_DIALS["Depth"][1], 0.46)])
thin([(0.4, -0.08, 2.5), (0.58, -0.08, 2.64), (0.74, -0.08, 2.56)])
thin([(0.42, -0.08, 1.72), (0.58, -0.08, 1.55), (0.72, -0.08, 1.6)])
patch(1.2, 1.07, 0.4, 0.28, 0.1)
patch(-1.38, 1.2, 0.36, 0.5, -0.08)
pipe(BRASS, [(1.5, -0.05, 0.1), (1.5, -0.05, 1.0), (1.5, -0.05, 2.0), (1.5, -0.05, BODY - 0.1)], 0.08)
collar((1.5, -0.05, 0.3), 0.08)
collar((1.5, -0.05, BODY - 0.3), 0.08)
# a copper coil wound round that pipe
coil = []
for k in range(49):
    a = math.tau * k / 8.0
    coil.append((1.5 + math.cos(a) * 0.13, -0.05 + math.sin(a) * 0.13, 0.75 + 0.95 * k / 48.0))
pipe(COPPER, coil, 0.03, 2)
# the scope
torus(BRASS, SCOPE_R + 0.1, 0.11, (SCOPE[0], -0.04, SCOPE[1]), "Y", 40)
cyl(BRASS, SCOPE_R + 0.12, 0.1, (SCOPE[0], 0.0, SCOPE[1]), "Y", 40)
ball(SCREEN, SCOPE_R, (SCOPE[0], -0.05, SCOPE[1]), (1.0, 0.1, 1.0), 32)
for k in range(8):
    a = math.tau * (k + 0.5) / 8.0
    rivet(SCOPE[0] + math.cos(a) * (SCOPE_R + 0.1), SCOPE[1] + math.sin(a) * (SCOPE_R + 0.1), 0.045, -0.14)
for name, (x, z) in SMALL_DIALS.items():
    dial(x, z, SMALL_DIAL_R, 9, name == "Burst")
# the switches: a steel plate, a slot, a red handle
for x in (-0.95, -0.25):
    box(STEEL, (0.55, 0.06, 0.8), (x, -0.02, 0.56), 0.02)
    box(DARK, (0.1, 0.03, 0.42), (x, -0.045, 0.52), 0.0)
    box(RED, (0.3, 0.26, 0.24), (x, -0.16, 0.74), 0.04)
    for sx in (-1.0, 1.0):
        for sz in (0.24, 0.88):
            rivet(x + sx * 0.2, sz, 0.035, -0.05)
# the grille
torus(BRASS, 0.3, 0.06, (0.9, -0.03, 0.56), "Y", 24)
cyl(DARK, 0.27, 0.03, (0.9, -0.035, 0.56), "Y", 24)
for k in range(5):
    z = 0.56 + (k - 2) * 0.09
    half = math.sqrt(max(0.0, 0.25 * 0.25 - (z - 0.56) ** 2))
    box(BRASS, (half * 2.0, 0.03, 0.03), (0.9, -0.06, z), 0.0)
valve(0.32, 0.56, 0.2)
# pipes and wires that shape its outline: one over the scope's head and down both sides, a second
# over the small dial's head, cables slung between the heads, an aerial
half = GAUGE_WIDE * 0.5
pipe(BRASS, [(-half - 0.08, 0.2, 0.15), (-half - 0.08, 0.2, 1.3)] + ring_points(SCOPE, 1.12, 172.0, 28.0, 0.2, 7)
     + [(0.75, 0.2, 2.9), (SMALL_DIALS["Depth"][0], 0.2, SMALL_DIALS["Depth"][1] + 0.58), (half + 0.02, 0.2, 2.5), (half + 0.1, 0.2, 1.9), (half + 0.1, 0.2, 0.15)], 0.08)
for at in ((-half - 0.08, 0.2, 0.7), (half + 0.1, 0.2, 1.2), (half + 0.1, 0.2, 0.5)):
    collar(at, 0.08)
pipe(COPPER, [(-half + 0.1, 0.12, 2.2), (-half - 0.22, 0.12, 2.1), (-half - 0.26, 0.12, 1.75), (-half + 0.1, 0.12, 1.6)], 0.05, 4)
pipe(RUBBER, [(SCOPE[0] - 0.2, -0.04, SCOPE[1] + 0.9), (0.1, -0.1, SCOPE[1] + 1.28), (0.7, -0.08, SCOPE[1] + 1.02), (SMALL_DIALS["Depth"][0], -0.04, SMALL_DIALS["Depth"][1] + 0.4)], 0.04, 5)
pipe(RUBBER, [(SCOPE[0] + 0.5, -0.04, SCOPE[1] + 0.8), (0.55, -0.1, SCOPE[1] + 0.82), (SMALL_DIALS["Depth"][0] + 0.3, -0.04, SMALL_DIALS["Depth"][1] + 0.3)], 0.03, 5)
pipe(RUBBER, [(SCOPE[0] - 0.6, -0.04, SCOPE[1] + 0.75), (-1.3, -0.08, SCOPE[1] + 1.05), (-half - 0.25, 0.05, SCOPE[1] + 0.3), (-half - 0.05, 0.12, BODY - 0.5)], 0.04, 5)
cyl(STEEL, 0.03, 0.9, (1.32, 0.1, 3.2), "Z", 6)
ball(BRASS, 0.07, (1.32, 0.1, 3.66), (1.0, 1.0, 1.0), 8)
cyl(BRASS, 0.07, 0.12, (1.32, 0.1, 2.82), "Z", 8, 0.01)
gauges = join("Gauges")
marker("Scope", (SCOPE[0], -0.12, SCOPE[1]), gauges)
marker("ScopeEdge", (SCOPE[0] + SCOPE_R, -0.12, SCOPE[1]), gauges)
for name, (x, z) in SMALL_DIALS.items():
    needle(name, x, z, SMALL_DIAL_R, gauges)

triangles = 0
for obj in bpy.data.objects:
    if obj.type == "MESH":
        obj.data.calc_loop_triangles()
        triangles += len(obj.data.loop_triangles)
print("PANEL triangles %d; side %.2f x %.2f; well z %.2f; slot r %.2f from %.1f to %.1f deg; gauges %.2f x %.2f; swing %.1f"
      % (triangles, SIDE_WIDE, SIDE_TALL, WELL_Z, SLOT_R, math.degrees(SLOT_FROM), math.degrees(SLOT_TO), GAUGE_WIDE, GAUGE_TALL, SWING))

os.makedirs(os.path.dirname(BLEND), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=GLB, export_format="GLB", export_apply=True, export_yup=True)
print("PANEL wrote", GLB)
