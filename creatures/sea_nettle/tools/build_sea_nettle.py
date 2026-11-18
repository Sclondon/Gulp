"""Builds the sea nettle (creatures/sea_nettle) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/sea_nettle/tools/build_sea_nettle.py
    blender --background --python creatures/sea_nettle/tools/build_sea_nettle.py -- <preview folder>   # with pictures

Writes creatures/sea_nettle/models/sea_nettle.glb (the full model, near) and sea_nettle_lo.glb (for far off and
for phones), and the editable creatures/sea_nettle/tools/sea_nettle.blend (this folder has a .gdignore). Each
model is one static mesh: the shader (sea_nettle.gdshader) folds the bell and swings the strands. It prints a
WINDING line: the check that nothing is inside out.

A Pacific sea nettle (Chrysaora fuscescens), grown huge: the bell 1.8 m across (a big wild one is 0.5 m).
Rebuilt 2026-11-17 after the user's own aquarium photographs (described in the component's README):

- THE BELL: a dome (0.7 m high) with soft lobes, its rim cut into thirty-two small lappets that hang a little
  below it and curl in; a jelly wall, thick at the crown and thin at the rim; the hollow under it open, a short
  fluted stalk in the middle of it from which the oral arms hang. Its markings are drawn by the shader.
- THE ORAL ARMS ("the bushy part"): four, each a bundle of thin sheets through one middle line, every sheet
  deeply ruffled at its edges (the edge is far longer than the middle, so it folds like lettuce: a big wave with a
  finer crinkle on it, curling over as well as in and out). Just under the bell they fan out wide into a bushy
  mass, with extra short sheets in it; further down they gather into one long frilled plume, in bunches, thinning
  to a ribbon. About 4.2 m.
- THE TENTACLES: twenty-four, hair-fine, thicker and paler where they leave the rim, about 5 m: three in each
  eighth of the rim, in the clefts between its lappets (the fourth cleft of each eighth has a sense organ).

At rest every strand hangs straight down; SeaNettle simulates each as a rope and the shader lays it along it. The lengths, roots and
phases are worked out the same way in creatures/sea_nettle/sea_nettle.gd (`strands()`), which uses them to
know where they are for stinging: change one, change the other.

What a point is, for the shader: vertex colour red the part (0 the top of the bell, 0.25 its underside,
0.5 an oral arm, 1 a tentacle); green, on the top of the bell, 1 for the copy of it that is drawn only where it
is seen from inside (see below), and on an oral arm 1 for a long sheet (it has the dark line down its middle),
0 for a short one of the bushy mass; blue, on an arm or a tentacle, which strand it is ((n + 0.5) / 32:
the arms 0 to 3, then the tentacles 4 to 27, as `strands()` lists them), for the shader to lay it along that
strand's rope. UV.x across an arm (0..1; on the bell, round it, 0..1), UV.y how far along a
strand (0 at its root, 1 its tip; on the bell, 0 at the top to 1 at the rim); UV2.x the strand's length
(metres), UV2.y its phase (0..1). (The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.)

Four surfaces, drawn in this order by SeaNettle (jelly is clear, so what is behind must be drawn first):
"nettle_far" (the top of the bell again, seen from inside: its far wall), "nettle_under" (the underside),
"nettle_strands" (arms and tentacles), "nettle_near" (the top of the bell, seen from outside).

Everything here is in Godot space (metres, Y up) until it is written out; the origin is the middle of the rim.
"""

import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "models")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREVIEW = ARGS[0] if ARGS else ""

# Kept in step with sea_nettle.gd.
RADIUS = 0.9
HEIGHT = 0.7
LAPPETS = 32
ARMS = 4
ARM_LONG = 4.2
TENTACLE_LONG = 5.0
GROUPS = 8

SURFACES = ["nettle_far", "nettle_under", "nettle_strands", "nettle_near"]
FAR, UNDER, STRANDS, NEAR = 0, 1, 2, 3
TAU = math.tau


def to_b(p):
    return Vector((p.x, -p.z, p.y))


def fract(x):
    return x - math.floor(x)


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def arm_strand(k):
    a = math.pi * 0.25 + k * math.pi * 0.5
    root = Vector((math.cos(a) * 0.12, -0.05, math.sin(a) * 0.12))
    return root, ARM_LONG * (1.0 + 0.1 * math.sin(k * 2.1 + 0.4)), fract(k * 0.37 + 0.11), a


def tentacle_strand(i):
    g, j = divmod(i, 3)
    a = g * TAU / GROUPS + math.pi / GROUPS + (j - 1) * TAU / LAPPETS
    root = Vector((math.cos(a) * RADIUS * 0.96, 0.02, math.sin(a) * RADIUS * 0.96))
    return root, TENTACLE_LONG * (1.0 + 0.12 * math.sin(i * 2.3 + 1.0)), fract(i * 0.618), a


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.surface = []
        # per point: (uv, uv2, colour)
        self.data = []
        # (name, first face, one past the last, what its faces should face: "out", "in" or "")
        self.groups = []
        # tentacle faces: [wound wrongly, all]
        self.tubes = [0, 0]

    def add(self, p, uv, uv2, colour):
        self.verts.append(p)
        self.data.append((uv, uv2, colour))
        return len(self.verts) - 1

    def quad(self, a, b, c, d, surface):
        self.faces.append((a, b, c, d))
        self.surface.append(surface)


def bell_point(v, a, inner):
    """A point of the bell: `v` 0 at the crown to 1 at the rim, `a` the angle round it."""
    phi = v * math.pi * 0.5
    rad = RADIUS * math.sin(phi) ** 0.85
    y = HEIGHT * math.cos(phi)
    rim = smooth(0.84, 1.0, v)
    # 1 in the clefts between the lappets (at a = k * TAU / 32, where the tentacles leave), 0 on a lappet
    cleft = abs(math.cos(a * LAPPETS * 0.5)) ** 8
    # the dome's soft lobes, sixteen of them, swelling between the second ring of markings and the rim
    rad *= 1.0 + 0.016 * math.cos(a * 16.0) * smooth(0.4, 0.8, v) * (1.0 - 0.5 * rim)
    # the lappets hang below the rim and curl in; the clefts are cut up into it
    y -= 0.075 * rim * rim * (1.0 - cleft)
    rad -= 0.04 * rim * rim * (1.0 - cleft) + 0.022 * rim * cleft
    if inner:
        # the wall: thick jelly at the crown, thin at the rim
        rad *= 0.93
        y = y * 0.76 - 0.015 * (1.0 - rim)
    return Vector((math.cos(a) * rad, y, math.sin(a) * rad))


def bell(m, low):
    around = 32 if low else 128
    rings = 9 if low else 26
    grids = {}
    for name, inner, colour in (("near", False, (0.0, 0.0, 0.0, 1.0)), ("far", False, (0.0, 1.0, 0.0, 1.0)),
                                ("under", True, (0.25, 0.0, 0.0, 1.0))):
        grid = []
        for r in range(rings + 1):
            v = r / rings
            row = []
            for c in range(around + 1):
                a = c / around * TAU
                row.append(m.add(bell_point(v, a, inner), (c / around, 1.0 - v), (0.0, 1.0), colour))
            grid.append(row)
        grids[name] = grid
    for name, surface, facing in (("far", FAR, "out"), ("under", UNDER, "in"), ("near", NEAR, "out")):
        first = len(m.faces)
        grid = grids[name]
        for r in range(rings):
            for c in range(around):
                a, b = grid[r][c], grid[r][c + 1]
                d, e = grid[r + 1][c], grid[r + 1][c + 1]
                if facing == "in":
                    m.quad(a, d, e, b, surface)
                else:
                    m.quad(a, b, e, d, surface)
        m.groups.append((name, first, len(m.faces), facing))
    # (the lip: the underside's edge joined to the top's, a strip of its own points coloured as the underside)
    lip = []
    for grid in (grids["near"], grids["under"]):
        row = []
        for c in range(around + 1):
            row.append(m.add(m.verts[grid[rings][c]].copy(), (c / around, 0.0), (0.0, 1.0), (0.25, 0.0, 0.0, 1.0)))
        lip.append(row)
    for c in range(around):
        m.quad(lip[0][c], lip[1][c], lip[1][c + 1], lip[0][c + 1], UNDER)


WIDTHS = [(0.0, 0.09), (0.05, 0.44), (0.12, 0.5), (0.25, 0.3), (0.45, 0.19), (0.7, 0.14), (0.9, 0.09), (1.0, 0.03)]


def arm_width(s):
    """Half the width of an oral arm (metres), `s` along it: a wide bushy mass under the bell, then a plume."""
    for (s0, w0), (s1, w1) in zip(WIDTHS, WIDTHS[1:]):
        if s <= s1:
            return w0 + (w1 - w0) * smooth(s0, s1, s)
    return WIDTHS[-1][1]


def arm_sheet(m, k, turned, s_from, s_to, wide, long_sheet, seed, steps, across_steps):
    """One ruffled sheet of oral arm `k`, through the arm's middle line, turned `turned` round it."""
    root, long, phase, a = arm_strand(k)
    rows = []
    colour = (0.5, 1.0 if long_sheet else 0.0, (k + 0.5) / 32.0, 1.0)

    def row_of(axis, twist, width, s, ruffle):
        across = Vector((math.cos(twist), 0.0, math.sin(twist)))
        facing = Vector((-math.sin(twist), 0.0, math.cos(twist)))
        arc = s * long
        row = []
        for w_i in range(across_steps + 1):
            u = w_i / across_steps * 2.0 - 1.0
            e = abs(u)
            side = 2.2 if u > 0.0 else 0.0
            # the big wave of the ruffle, and the finer crinkle on it: both longer further down the arm
            big = arc / (0.42 + 0.30 * s) * TAU + seed + side
            fine = arc / (0.17 + 0.12 * s) * TAU + seed * 2.3 + side * 1.7 + u * 2.0
            out = width * ruffle * (0.50 * e ** 1.5 * math.sin(big) + 0.20 * e ** 2.2 * math.sin(fine))
            # (it curls over along the arm as well, and what is thrown out sideways is drawn in a little)
            along = width * ruffle * (0.20 * e ** 1.5 * math.cos(big) + 0.10 * e ** 2.2 * math.cos(fine))
            reach = u * width * (1.0 - 0.18 * ruffle * e * abs(math.sin(big)))
            p = axis + across * reach + facing * out + Vector((0.0, along, 0.0))
            row.append(m.add(p, ((u + 1.0) * 0.5, 1.0 - s), (long, 1.0 - phase), colour))
        return row

    if long_sheet and s_from <= 0.0:
        # The stalk: above its root an arm runs up to the middle of the underside of the bell (these rows are
        # all at s = 0, so they stay with the bell).
        twist = a + turned + 0.5 * math.sin(seed)
        for up in (0.565, 0.37, 0.18):
            share = up / 0.565
            axis = Vector((root.x * (1.0 - 0.55 * share), root.y + up, root.z * (1.0 - 0.55 * share)))
            rows.append(row_of(axis, twist, 0.09 * (1.0 - 0.3 * share), 0.0, 0.0))
    for s_i in range(steps + 1):
        t = s_i / steps
        # (more rows near the bell, where the ruffles are fine)
        s = s_from + (s_to - s_from) * t ** 1.6
        arc = s * long
        twist = a + turned + arc * 0.8 + 0.5 * math.sin(arc * 0.7 + seed)
        width = arm_width(s) * wide
        # (the plume comes in bunches)
        width *= 1.0 + 0.24 * math.sin(arc * 2.6 + k * 1.7 + seed) * smooth(0.15, 0.3, s)
        # (a short sheet tapers away at both its ends)
        if not long_sheet:
            width *= smooth(0.0, 0.25, t) * (1.0 - smooth(0.6, 1.0, t)) + 0.05
        axis = root + Vector((0.0, -arc, 0.0))
        rows.append(row_of(axis, twist, width, s, smooth(0.0, 0.03, s)))
    for r in range(len(rows) - 1):
        for w_i in range(across_steps):
            m.quad(rows[r][w_i], rows[r][w_i + 1], rows[r + 1][w_i + 1], rows[r + 1][w_i], STRANDS)


def oral_arm(m, k, low):
    if low:
        arm_sheet(m, k, 0.0, 0.0, 1.0, 1.0, True, k * 1.3, 40, 4)
        arm_sheet(m, k, math.pi * 0.5, 0.0, 0.8, 0.85, True, k * 1.3 + 4.0, 32, 4)
        return
    # three long sheets through the middle line, a sixth of a turn apart, and two short wide ones in the mass
    arm_sheet(m, k, 0.0, 0.0, 1.0, 1.0, True, k * 1.3, 220, 12)
    arm_sheet(m, k, math.pi / 3.0, 0.0, 0.88, 0.86, True, k * 1.3 + 4.0, 190, 12)
    arm_sheet(m, k, math.pi * 2.0 / 3.0, 0.0, 0.7, 0.74, True, k * 1.3 + 8.0, 160, 12)
    arm_sheet(m, k, math.pi / 6.0, 0.012, 0.3, 1.12, False, k * 1.3 + 11.0, 100, 12)
    arm_sheet(m, k, math.pi * 0.5, 0.02, 0.36, 1.0, False, k * 1.3 + 15.0, 100, 12)


def tentacle(m, i, low):
    root, long, phase, a = tentacle_strand(i)
    steps = 12 if low else 40
    sides = 3 if low else 4
    rows = []
    middles = []
    for s_i in range(steps + 1):
        s = (s_i / steps) ** 1.3
        # thicker where it leaves the rim, then hair-fine (a little thicker far off, or it would not be seen)
        thick = 0.0045 + 0.011 * math.exp(-s * 30.0) + 0.0015 * (1.0 - s)
        if low:
            thick *= 1.6
        # (never quite straight)
        bent = smooth(0.0, 0.08, s) * 0.035
        middle = root + Vector((math.sin(s * long * 2.1 + i * 1.3) * bent, -s * long, math.cos(s * long * 1.7 + i * 2.1) * bent))
        middles.append(middle)
        row = []
        for c in range(sides):
            t = c / sides * TAU
            p = middle + Vector((math.cos(t) * thick, 0.0, math.sin(t) * thick))
            row.append(m.add(p, (c / sides, 1.0 - s), (long, 1.0 - phase), (1.0, 0.0, (ARMS + i + 0.5) / 32.0, 1.0)))
        rows.append(row)
    for s_i in range(steps):
        for c in range(sides):
            n = (c + 1) % sides
            quad = (rows[s_i][c], rows[s_i][n], rows[s_i + 1][n], rows[s_i + 1][c])
            m.quad(*quad, STRANDS)
            # (its skin faces away from its own middle line: a face's front is the side its points go round
            # anticlockwise, seen from there)
            pa, pb, pc, pd = (m.verts[q] for q in quad)
            away = (pa + pb + pc + pd) * 0.25 - (middles[s_i] + middles[s_i + 1]) * 0.5
            m.tubes[1] += 1
            if (pb - pa).cross(pc - pa).dot(away) <= 0.0:
                m.tubes[0] += 1


def make(name, low):
    m = Mesh()
    bell(m, low)
    for k in range(ARMS):
        oral_arm(m, k, low)
    for i in range(GROUPS * 3):
        tentacle(m, i, low)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) for p in m.verts], [], m.faces)
    # (every layer made first, then each looked up by name: making one moves the others)
    mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.new(name="UV2")
    mesh.color_attributes.new(name="Color", type="FLOAT_COLOR", domain="CORNER")
    uv = mesh.uv_layers["UVMap"].data
    uv2 = mesh.uv_layers["UV2"].data
    colour = mesh.color_attributes["Color"].data
    for poly in mesh.polygons:
        for corner, vi in enumerate(poly.vertices):
            d = m.data[vi]
            uv[poly.loop_start + corner].uv = d[0]
            uv2[poly.loop_start + corner].uv = d[1]
            colour[poly.loop_start + corner].color = d[2]
    mesh.color_attributes.active_color = mesh.color_attributes["Color"]
    mesh.color_attributes.render_color_index = mesh.color_attributes.find("Color")
    tints = {"nettle_far": (0.9, 0.6, 0.4, 1.0), "nettle_under": (0.95, 0.8, 0.72, 1.0),
             "nettle_strands": (0.98, 0.66, 0.46, 1.0), "nettle_near": (0.9, 0.58, 0.34, 1.0)}
    for surface in SURFACES:
        material = bpy.data.materials.get(surface) or bpy.data.materials.new(surface)
        material.use_nodes = True
        bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        bsdf.inputs["Base Color"].default_value = tints[surface]
        material.diffuse_color = tints[surface]
        mesh.materials.append(material)
    for poly in mesh.polygons:
        poly.use_smooth = True
        poly.material_index = m.surface[poly.index]
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    print("BUILT %s verts=%d tris=%d" % (name, len(mesh.vertices), tris))
    winding(name, mesh, m)
    return obj


def winding(name, mesh, m):
    """Nothing inside out: the top of the bell faces out from its middle, its underside in towards it, and
    a tentacle's skin away from its own middle line (Blender's front is the side a face's normal is on)."""
    wrong = 0
    told = []
    middle = to_b(Vector((0.0, 0.18, 0.0)))
    for group, first, last, facing in m.groups:
        bad = 0
        for f in range(first, last):
            poly = mesh.polygons[f]
            side = poly.normal.dot(poly.center - middle)
            if facing == "in":
                side = -side
            if side <= 0.0:
                bad += 1
        told.append("%s %d/%d wrong" % (group, bad, last - first))
        wrong += bad
    told.append("tentacles %d/%d wrong" % (m.tubes[0], m.tubes[1]))
    wrong += m.tubes[0]
    print("WINDING %s: %s: %s" % (name, "ok" if wrong == 0 else "INSIDE OUT", ", ".join(told)))


def export_one(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", export_yup=True, use_selection=True,
        export_animations=False, export_vertex_color="ACTIVE", export_texcoords=True,
    )


def render(folder, made):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_cavity = True
    scene.render.resolution_x, scene.render.resolution_y = 1000, 1000
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    views = [("front", (0, -1, 0.0), (0, 0, -2.0), 7.0), ("side", (1, 0, 0.0), (0, 0, -2.0), 7.0),
             ("back", (0, 1, 0.0), (0, 0, -2.0), 7.0), ("left", (-1, 0, 0.0), (0, 0, -2.0), 7.0),
             ("top", (0.0, -0.01, 1.0), (0, 0, 0), 2.6), ("under", (0.1, -0.2, -1.0), (0, 0, 0), 2.6),
             ("bell", (0.7, -0.7, 0.4), (0, 0, -0.3), 3.2), ("bush", (0.5, -0.8, -0.25), (0, 0, -0.6), 3.2)]
    for low, obj in ((False, made[0]), (True, made[1])):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if low and view not in ("front", "bell"):
                continue
            offset = Vector(direction).normalized() * 40.0
            camera.data.ortho_scale = frame
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % ("lo_" if low else "", view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    full = make("sea_nettle", False)
    low = make("sea_nettle_lo", True)
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, "sea_nettle.glb"))
    export_one(low, os.path.join(OUT, "sea_nettle_lo.glb"))
    low.location.x = 3.0
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "sea_nettle.blend"))
    low.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low])


if __name__ == "__main__":
    main()
