"""Builds the helmet the boy wears on the boat, wired to the computer, and the computer's bench.

    blender --background --python tools/build_helmet.py

Writes models/brain_helmet.glb, textures/panel/helmet_atlas.png and tools/blend/brain_helmet.blend.
The user (2026-11-18): "In the open back cabin of the shrimping boat should be a old timey
franketstein computer hooked up to a helmet on the boys head". The computer is the control panel
(tools/build_panel.py); this is its other end: a riveted iron skullcap with brass bands, an
electrode at each temple, three valves glowing on top, a copper coil, and two sockets at the back
for the cables.

The helmet is built round a head of radius 1 with its middle at the origin (Z up, the face towards
-Y): the game scales it to the head it goes on. Objects: "Helmet", with markers "CableA" and
"CableB" at its sockets; "Cable", a slack length of rubber cable from the origin to (1, 0, 0),
which the game stretches between a socket and the computer; and "Bench", the planks on an iron
frame the computer stands on (in metres, its origin on the floor under its middle).

The low-poly helpers, the materials and the bake are tools/build_panel.py's own (its top part is
run from here), so it is painted as the panel is: one baked picture, drawn by the panel's shader.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
source = open(os.path.join(HERE, "build_panel.py")).read()
exec(compile(source.split("# --- The helm housing")[0], "build_panel.py", "exec"))

GLB = os.path.join(HERE, "..", "models", "brain_helmet.glb")
BLEND = os.path.join(HERE, "blend", "brain_helmet.blend")
ATLAS = os.path.join(HERE, "..", "textures", "panel", "helmet_atlas.png")
RIM = 0.18   # the cap's edge, above the head's middle
WOOD = material("wood", (0.2, 0.11, 0.05), (0.13, 0.07, 0.03), (0.26, 0.16, 0.08), 0.5)


def cut_below(obj, z):
    """Takes away what is under a height."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0.0, 0.0, z), plane_no=(0.0, 0.0, 1.0), clear_inner=True)
    bm.to_mesh(obj.data)
    bm.free()
    return obj


# the cap: a shell of iron
cap = cut_below(ball(IRON, 1.1, (0.0, 0.0, 0.0), (1.0, 1.0, 1.0), 24), RIM)
shell = cap.modifiers.new("shell", "SOLIDIFY")
shell.thickness = 0.08
shell.offset = -1.0
bpy.context.view_layer.objects.active = cap
bpy.ops.object.modifier_apply(modifier="shell")
# brass bands: round the rim, over the top front to back, and ear to ear
torus(BRASS, 1.1, 0.08, (0.0, 0.0, RIM), "Z", 28)
cut_below(torus(BRASS, 1.12, 0.065, (0.0, 0.0, 0.0), "X", 28), RIM)
cut_below(torus(BRASS, 1.12, 0.065, (0.0, 0.0, 0.0), "Y", 28), RIM)
# rivets round the rim band
for k in range(10):
    a = math.tau * (k + 0.5) / 10.0
    ball(BRASS, 0.07, (math.cos(a) * 1.18, math.sin(a) * 1.18, RIM), (1.0, 1.0, 1.0), 8)
# an electrode at each temple: a brass stud with a steel bolt through it
for side in (-1.0, 1.0):
    cyl(BRASS, 0.2, 0.2, (side * 1.12, -0.1, 0.5), "X", 12)
    cyl(STEEL, 0.08, 0.5, (side * 1.25, -0.1, 0.5), "X", 6)
    ball(BRASS, 0.13, (side * 1.5, -0.1, 0.5))
# three valves on top, glowing: a brass base, a glass body, a domed tip
for x, y in ((0.0, -0.25), (-0.42, 0.2), (0.42, 0.2)):
    top = math.sqrt(max(0.0, 1.1 * 1.1 - x * x - y * y))
    cyl(BRASS, 0.17, 0.14, (x, y, top + 0.02), "Z", 10)
    cyl(LAMP, 0.12, 0.34, (x, y, top + 0.25), "Z", 8)
    ball(LAMP, 0.12, (x, y, top + 0.42))
# a copper coil standing at the back of the crown
coil = []
for k in range(25):
    a = math.tau * k / 6.0
    coil.append((math.cos(a) * 0.14, 0.62 + math.sin(a) * 0.14, 0.85 + 0.5 * k / 24.0))
cyl(STEEL, 0.05, 0.6, (0.0, 0.62, 1.1), "Z", 6)
pipe(COPPER, coil, 0.035, 1)
ball(BRASS, 0.09, (0.0, 0.62, 1.42))
# two sockets at the back for the cables
SOCKETS = ((-0.4, 0.98, 0.48), (0.4, 0.98, 0.48))
for at in SOCKETS:
    cyl(BRASS, 0.15, 0.3, (at[0], at[1] + 0.02, at[2]), "Y", 10)
    cyl(RUBBER, 0.09, 0.2, (at[0], at[1] + 0.22, at[2]), "Y", 8)
helmet = join("Helmet")
for name, at in zip(("CableA", "CableB"), SOCKETS):
    marker(name, (at[0], at[1] + 0.3, at[2]), helmet)

# the bench the computer stands on: planks on an iron frame
for k in range(3):
    box(WOOD, (2.4, 0.19, 0.07), (0.0, -0.25 + 0.2 * k, 0.465))
for x in (-1.1, 1.1):
    box(IRON, (0.1, 0.5, 0.43), (x, -0.05, 0.215))
box(IRON, (2.2, 0.06, 0.08), (0.0, -0.28, 0.25))
bench = join("Bench")

# the monitor the computer is hooked up to (the user: "And hooked up to a monitor"): an iron box on
# a wall bracket with a round glass screen in a brass ring, two knobs, a vent (in metres; its origin
# is the middle of its back, against the wall; its face towards -Y)
box(IRON, (0.72, 0.3, 0.56), (0.0, -0.17, 0.0))
box(IRON, (0.78, 0.05, 0.62), (0.0, -0.3, 0.0))
cyl(BRASS, 0.24, 0.06, (-0.08, -0.34, 0.03), "Y", 28)
torus(BRASS, 0.2, 0.04, (-0.08, -0.37, 0.03), "Y", 28)
for z in (0.14, -0.02, -0.16):
    cyl(BRASS, 0.04, 0.06, (0.27, -0.35, z), "Y", 8)
for x, z in ((-0.33, 0.25), (0.33, 0.25), (-0.33, -0.25), (0.33, -0.25)):
    rivet(x, z, 0.03, -0.325)
box(IRON, (0.1, 0.3, 0.1), (-0.25, -0.02, -0.33))
box(IRON, (0.1, 0.3, 0.1), (0.25, -0.02, -0.33))
run(RUBBER, [(0.0, -0.1, -0.28), (0.05, -0.16, -0.5), (0.0, -0.12, -0.75)], 0.03, ("-Z", None), 4)
monitor = join("Monitor")
cyl(SCREEN, 0.19, 0.02, (-0.08, -0.365, 0.03), "Y", 28)
screen = join("MonitorScreen", (-0.08, -0.365, 0.03), monitor)

# the boy's stool (the user: "the boy sitting on a stool"): a round wooden seat 0.42 m up on three
# iron legs with a foot ring (in metres; its origin on the floor under its middle)
cyl(WOOD, 0.17, 0.05, (0.0, 0.0, 0.395), "Z", 16)
for k in range(3):
    a = math.tau * k / 3.0 + 0.5
    pipe(IRON, [(math.cos(a) * 0.1, math.sin(a) * 0.1, 0.38), (math.cos(a) * 0.2, math.sin(a) * 0.2, 0.0)], 0.018, 1)
torus(IRON, 0.17, 0.014, (0.0, 0.0, 0.14), "Z", 16)
stool = join("Stool")

# a slack cable, one unit long
pipe(RUBBER, [(0.0, 0.0, 0.0), (0.2, 0.0, -0.14), (0.5, 0.0, -0.22), (0.8, 0.0, -0.14), (1.0, 0.0, 0.0)], 0.03, 4)
cable = join("Cable")

meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
triangles = 0
for obj in meshes:
    obj.data.calc_loop_triangles()
    triangles += len(obj.data.loop_triangles)
print("HELMET triangles %d" % triangles)
# (stood apart for the bake)
unwrap(meshes)
bench.location.x = 6.0
cable.location.x = -6.0
monitor.location.x = 12.0
stool.location.x = 18.0
bpy.context.view_layer.update()
bake(ATLAS, 1024, meshes)
bench.location.x = 0.0
cable.location.x = 0.0
monitor.location.x = 0.0
stool.location.x = 0.0
bpy.context.view_layer.update()
os.makedirs(os.path.dirname(BLEND), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
bpy.ops.object.select_all(action="DESELECT")
for obj in bpy.data.objects:
    if obj.type in ("MESH", "EMPTY"):
        obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=GLB, export_format="GLB", export_apply=True, export_yup=True, use_selection=True, export_image_format="NONE")
print("HELMET wrote", GLB)
