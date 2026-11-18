# Builds the on-screen controls as brass fittings of an old submarine and renders each as a
# picture with a clear background (textures/controls/*.png), for scripts/touch_pad.gd to draw.
# The models are kept in tools/blend/controls.blend.
#   blender --background --python tools/build_controls.py
# One Blender unit is 100 of the pad's layout units (see TouchPad.unit). Seen from straight above;
# +X is the screen's right, +Y the screen's up.
import bpy, math, os
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "textures", "controls")
os.makedirs(OUT, exist_ok=True)

# The lever's arc as the pad has it (screen angles, y down): dead slow and full ahead.
SLOW_AT = math.pi * 1.03
FULL_AT = math.pi * 1.52
LEVER_R = 1.5

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def material(name, colour, metal, rough):
    made = bpy.data.materials.new(name)
    made.use_nodes = True
    shader = next(n for n in made.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    shader.inputs["Base Color"].default_value = (*colour, 1.0)
    shader.inputs["Metallic"].default_value = metal
    shader.inputs["Roughness"].default_value = rough
    return made


BRASS = material("brass", (0.72, 0.45, 0.13), 1.0, 0.42)
BRASS_WORN = material("brass_worn", (0.42, 0.27, 0.09), 1.0, 0.55)
IRON = material("iron", (0.02, 0.022, 0.025), 0.3, 0.6)
RUBBER = material("rubber", (0.02, 0.02, 0.022), 0.0, 0.75)
RED = material("red", (0.7, 0.06, 0.04), 0.0, 0.4)


def collection(name):
    made = bpy.data.collections.new(name)
    scene.collection.children.link(made)
    return made


def put(obj, into, mat):
    for old in obj.users_collection:
        old.objects.unlink(obj)
    into.objects.link(obj)
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def torus(into, mat, major, minor, at=(0, 0, 0), squash=1.0):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=96, minor_segments=20, location=at)
    obj = bpy.context.object
    obj.scale.z = squash
    return put(obj, into, mat)


def disc(into, mat, radius, depth, at=(0, 0, 0), bevel=0.0):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, vertices=96, location=at)
    obj = put(bpy.context.object, into, mat)
    if bevel > 0.0:
        mod = obj.modifiers.new("bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 4
    return obj


def ball(into, mat, radius, at, squash=1.0):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, segments=40, ring_count=20, location=at)
    obj = bpy.context.object
    obj.scale.z = squash
    return put(obj, into, mat)


def prism(into, mat, points, depth, z):
    # a flat piece with the given outline (x, y), `depth` thick, its top at z
    mesh = bpy.data.meshes.new("prism")
    n = len(points)
    verts = [(x, y, z) for x, y in points] + [(x, y, z - depth) for x, y in points]
    faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    faces += [(i, (i + 1) % n, n + (i + 1) % n, n + i)[::-1] for i in range(n)]
    mesh.from_pydata(verts, [], faces)
    obj = bpy.data.objects.new("prism", mesh)
    into.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def rivets(into, count, radius, z, size=0.04, turn=0.5):
    for k in range(count):
        a = math.tau * (k + turn) / count
        ball(into, BRASS_WORN, size, (math.cos(a) * radius, math.sin(a) * radius, z), 0.6)


def arc_strip(into, mat, radius, half_wide, a0, a1, z, depth, steps=64):
    # a flat curved band between two screen angles (y down, so the Blender angle is the negative)
    outer = [(math.cos(-(a0 + (a1 - a0) * i / steps)) * (radius + half_wide), math.sin(-(a0 + (a1 - a0) * i / steps)) * (radius + half_wide)) for i in range(steps + 1)]
    inner = [(math.cos(-(a0 + (a1 - a0) * i / steps)) * (radius - half_wide), math.sin(-(a0 + (a1 - a0) * i / steps)) * (radius - half_wide)) for i in range(steps, -1, -1)]
    obj = prism(into, mat, outer + inner, depth, z)
    mod = obj.modifiers.new("bevel", "BEVEL")
    mod.width = min(0.02, half_wide * 0.4)
    mod.segments = 3
    return obj


# --- The helm: a riveted brass ring round a dark well, an arrowhead each way, the stick's boot.
helm_plate = collection("helm_plate")
disc(helm_plate, IRON, 1.0, 0.06, (0, 0, -0.03))
torus(helm_plate, BRASS, 0.98, 0.10, (0, 0, 0.0), 0.7)
torus(helm_plate, BRASS_WORN, 0.76, 0.025, (0, 0, 0.0))
rivets(helm_plate, 12, 0.98, 0.07)
for k in range(4):
    a = k * math.pi * 0.5
    way = Vector((math.cos(a), math.sin(a)))
    side = Vector((-way.y, way.x))
    tip = way * 0.66
    prism(helm_plate, BRASS, [tuple(tip), tuple(tip - way * 0.15 + side * 0.10), tuple(tip - way * 0.15 - side * 0.10)], 0.03, 0.03)
ball(helm_plate, RUBBER, 0.22, (0, 0, 0.0), 0.5)

helm_knob = collection("helm_knob")
disc(helm_knob, BRASS_WORN, 0.2, 0.08, (0, 0, 0.0), 0.02)
ball(helm_knob, BRASS, 0.34, (0, 0, 0.12))

# --- The burst: a riveted brass ring with a dark channel for the gauge, and the plunger's cap.
burst_plate = collection("burst_plate")
disc(burst_plate, IRON, 0.9, 0.06, (0, 0, -0.03))
torus(burst_plate, BRASS, 0.86, 0.075, (0, 0, 0.0), 0.7)
torus(burst_plate, BRASS_WORN, 0.60, 0.03, (0, 0, 0.0))
rivets(burst_plate, 10, 0.86, 0.055, 0.032)
prism(burst_plate, RED, [(-0.02, 0.63), (0.02, 0.63), (0.02, 0.80), (-0.02, 0.80)], 0.02, 0.03)

burst_cap = collection("burst_cap")
ball(burst_cap, BRASS, 0.58, (0, 0, -0.02), 0.32)
torus(burst_cap, BRASS_WORN, 0.57, 0.03, (0, 0, 0.0))
for k in range(2):
    x = (k - 0.5) * 0.32 - 0.04
    # a chevron, as a bent bar
    chevron = [(x - 0.10, 0.20), (x - 0.03, 0.20), (x + 0.13, 0.0), (x - 0.03, -0.20), (x - 0.10, -0.20), (x + 0.06, 0.0)]
    prism(burst_cap, IRON, chevron, 0.03, 0.19)

# --- The speed lever: a slotted brass track round the burst button with a tick for each order.
lever_arc = collection("lever_arc")
arc_strip(lever_arc, BRASS, LEVER_R, 0.17, SLOW_AT - 0.09, FULL_AT + 0.09, 0.0, 0.06)
arc_strip(lever_arc, IRON, LEVER_R, 0.04, SLOW_AT - 0.02, FULL_AT + 0.02, 0.012, 0.03)
arc_strip(lever_arc, BRASS_WORN, LEVER_R + 0.15, 0.012, SLOW_AT - 0.09, FULL_AT + 0.09, 0.02, 0.02)
arc_strip(lever_arc, BRASS_WORN, LEVER_R - 0.15, 0.012, SLOW_AT - 0.09, FULL_AT + 0.09, 0.02, 0.02)
for end in (SLOW_AT - 0.09, FULL_AT + 0.09):
    ball(lever_arc, BRASS_WORN, 0.04, (math.cos(-end) * LEVER_R, math.sin(-end) * LEVER_R, 0.02), 0.6)
for k in range(5):
    a = -(SLOW_AT + (FULL_AT - SLOW_AT) * k / 4.0)
    way = Vector((math.cos(a), math.sin(a)))
    side = Vector((-way.y, way.x))
    near = way * (LEVER_R + 0.23)
    far = way * (LEVER_R + 0.23 + 0.09 + 0.05 * k)
    wide = 0.016 + 0.004 * k
    prism(lever_arc, BRASS, [tuple(near + side * wide), tuple(far + side * wide), tuple(far - side * wide), tuple(near - side * wide)], 0.03, 0.0)

# The handle: an arm that reaches in towards the hub (-X here: the pad turns the picture) and a grip.
lever_handle = collection("lever_handle")
prism(lever_handle, BRASS_WORN, [(-0.62, 0.05), (0.0, 0.065), (0.0, -0.065), (-0.62, -0.05)], 0.05, 0.05)
disc(lever_handle, IRON, 0.25, 0.05, (0, 0, 0.03), 0.01)
ball(lever_handle, BRASS, 0.2, (0, 0, 0.12))

# --- Light and camera: brass needs something to reflect.
world = bpy.data.worlds.new("world")
world.use_nodes = True
tree = world.node_tree
sky = tree.nodes.new("ShaderNodeTexSky")
sky.sky_type = "PREETHAM"
sky.turbidity = 4.0
tree.links.new(sky.outputs[0], tree.nodes["Background"].inputs[0])
tree.nodes["Background"].inputs[1].default_value = 0.16
scene.world = world
for at, power, size in [((-2.5, 2.5, 4.0), 260.0, 3.0), ((3.0, -1.0, 3.0), 60.0, 5.0)]:
    lamp_data = bpy.data.lights.new("lamp", "AREA")
    lamp_data.energy = power
    lamp_data.size = size
    lamp = bpy.data.objects.new("lamp", lamp_data)
    lamp.location = at
    lamp.rotation_euler = (Vector((0, 0, 0)) - Vector(at)).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(lamp)
camera_data = bpy.data.cameras.new("eye")
camera_data.type = "ORTHO"
eye = bpy.data.objects.new("eye", camera_data)
eye.location = (0, 0, 10)
scene.collection.objects.link(eye)
scene.camera = eye
scene.render.engine = "CYCLES"
scene.cycles.samples = 64
scene.cycles.use_denoising = True
scene.render.film_transparent = True
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.view_settings.view_transform = "Filmic"
scene.view_settings.look = "Medium High Contrast"

# Each picture: which collection, how many pixels, and how wide a square it covers (Blender units).
SHOTS = [
    ("helm_plate", helm_plate, 512, 2.4),
    ("helm_knob", helm_knob, 256, 0.9),
    ("burst_plate", burst_plate, 512, 2.0),
    ("burst_cap", burst_cap, 256, 1.3),
    ("lever_arc", lever_arc, 1024, 4.2),
    ("lever_handle", lever_handle, 512, 2.0),
]
everything = [shot[1] for shot in SHOTS]
for name, shown, pixels, wide in SHOTS:
    for each in everything:
        each.hide_render = each is not shown
    camera_data.ortho_scale = wide
    scene.render.resolution_x = pixels
    scene.render.resolution_y = pixels
    scene.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True)
    print("CONTROL", name, pixels, "px covers", wide * 100.0, "units")
for each in everything:
    each.hide_render = False
os.makedirs(os.path.join(HERE, "blend"), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "blend", "controls.blend"))
