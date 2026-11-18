"""Builds the helmet the boy wears on the boat, wired to the computer.

    blender --background --python tools/build_helmet.py

Writes models/brain_helmet.glb and tools/blend/brain_helmet.blend. The user (2026-11-18): "In the
open back cabin of the shrimping boat should be a old timey franketstein computer hooked up to a
helmet on the boys head". The computer is the control panel (tools/build_panel.py); this is its
other end: a riveted iron skullcap with brass bands, an electrode at each temple, three valves
glowing on top, a copper coil, and two sockets at the back for the cables.

It is built round a head of radius 1 with its middle at the origin (Z up, the face towards -Y):
the game scales it to the head it goes on. Objects: "Helmet", with markers "CableA" and "CableB"
at its sockets; and "Cable", a slack length of rubber cable from the origin to (1, 0, 0), which
the game stretches between a socket and the computer.

The helpers and materials are tools/build_panel.py's own (its top part is run from here), so the
game's panel paints fit this too.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
source = open(os.path.join(HERE, "build_panel.py")).read()
exec(compile(source.split("# --- The helm housing")[0], "build_panel.py", "exec"))

GLB = os.path.join(HERE, "..", "models", "brain_helmet.glb")
BLEND = os.path.join(HERE, "blend", "brain_helmet.blend")
RIM = 0.18   # the cap's edge, above the head's middle


def cut_below(obj, z):
    """Takes away what is under a height."""
    bpy.context.view_layer.objects.active = obj
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0.0, 0.0, z), plane_no=(0.0, 0.0, 1.0), clear_inner=True)
    bm.to_mesh(obj.data)
    bm.free()
    return obj


# the cap: a shell of iron
cap = cut_below(ball(IRON, 1.1, (0.0, 0.0, 0.0), (1.0, 1.0, 1.0), 32), RIM)
shell = cap.modifiers.new("shell", "SOLIDIFY")
shell.thickness = 0.08
shell.offset = -1.0
bpy.context.view_layer.objects.active = cap
bpy.ops.object.modifier_apply(modifier="shell")
# brass bands: round the rim, over the top front to back, and ear to ear
torus(BRASS, 1.1, 0.075, (0.0, 0.0, RIM), "Z", 40)
cut_below(torus(BRASS, 1.12, 0.06, (0.0, 0.0, 0.0), "X", 40), RIM)
cut_below(torus(BRASS, 1.12, 0.06, (0.0, 0.0, 0.0), "Y", 40), RIM)
# rivets along the rim band and up the bands
for k in range(12):
    a = math.tau * (k + 0.5) / 12.0
    ball(BRASS, 0.06, (math.cos(a) * 1.17, math.sin(a) * 1.17, RIM), (1.0, 1.0, 1.0), 8)
# an electrode at each temple: a brass stud with a steel bolt through it
for side in (-1.0, 1.0):
    cyl(BRASS, 0.2, 0.2, (side * 1.12, -0.1, 0.5), "X", 16, 0.02)
    cyl(STEEL, 0.08, 0.5, (side * 1.25, -0.1, 0.5), "X", 8)
    ball(BRASS, 0.12, (side * 1.5, -0.1, 0.5), (1.0, 1.0, 1.0), 10)
# three valves on top, glowing: a brass base, a glass body, a domed tip
for x, y in ((0.0, -0.25), (-0.42, 0.2), (0.42, 0.2)):
    top = math.sqrt(max(0.0, 1.1 * 1.1 - x * x - y * y))
    cyl(BRASS, 0.17, 0.14, (x, y, top + 0.02), "Z", 14, 0.02)
    cyl(LAMP, 0.12, 0.34, (x, y, top + 0.25), "Z", 12)
    ball(LAMP, 0.12, (x, y, top + 0.42), (1.0, 1.0, 1.0), 12)
# a copper coil standing at the back of the crown
coil = []
for k in range(41):
    a = math.tau * k / 8.0
    coil.append((math.cos(a) * 0.14, 0.62 + math.sin(a) * 0.14, 0.85 + 0.5 * k / 40.0))
cyl(STEEL, 0.05, 0.6, (0.0, 0.62, 1.1), "Z", 8)
pipe(COPPER, coil, 0.035, 2)
ball(BRASS, 0.09, (0.0, 0.62, 1.42), (1.0, 1.0, 1.0), 10)
# two sockets at the back for the cables
SOCKETS = ((-0.4, 0.98, 0.48), (0.4, 0.98, 0.48))
for at in SOCKETS:
    cyl(BRASS, 0.15, 0.3, (at[0], at[1] + 0.02, at[2]), "Y", 12, 0.02)
    cyl(RUBBER, 0.09, 0.2, (at[0], at[1] + 0.22, at[2]), "Y", 10)
helmet = join("Helmet")
for name, at in zip(("CableA", "CableB"), SOCKETS):
    marker(name, (at[0], at[1] + 0.3, at[2]), helmet)

# the bench the computer stands on: planks on an iron frame (its origin on the floor, under its middle)
WOOD = material("wood", (0.35, 0.22, 0.12))
box(WOOD, (2.7, 0.6, 0.08), (0.0, -0.05, 0.46), 0.015)
for x in (-1.25, 1.25):
    box(IRON, (0.1, 0.5, 0.44), (x, -0.05, 0.22), 0.02)
box(IRON, (2.5, 0.06, 0.08), (0.0, -0.28, 0.25), 0.015)
join("Bench")

# a slack cable, one unit long
pipe(RUBBER, [(0.0, 0.0, 0.0), (0.2, 0.0, -0.14), (0.5, 0.0, -0.22), (0.8, 0.0, -0.14), (1.0, 0.0, 0.0)], 0.03, 6)
join("Cable")

triangles = 0
for obj in bpy.data.objects:
    if obj.type == "MESH":
        obj.data.calc_loop_triangles()
        triangles += len(obj.data.loop_triangles)
print("HELMET triangles %d" % triangles)
os.makedirs(os.path.dirname(BLEND), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=GLB, export_format="GLB", export_apply=True, export_yup=True)
print("HELMET wrote", GLB)
