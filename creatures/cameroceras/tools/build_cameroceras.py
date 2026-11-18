"""Builds the cameroceras (creatures/cameroceras) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/cameroceras/tools/build_cameroceras.py
    blender --background --python creatures/cameroceras/tools/build_cameroceras.py -- <preview folder>   # with pictures

Writes creatures/cameroceras/models/cameroceras.glb (the full model), cameroceras_game.glb (the game model: few
triangles, spent where the eye looks: the shell's round outline, the eyes, the hood's edge, the arms) and
cameroceras_lo.glb (far off, phones), and the editable creatures/cameroceras/tools/cameroceras.blend (all three;
this folder has a .gdignore). Each is one still mesh with one surface: the shader (cameroceras.gdshader) draws every
marking, trails and curls its arms, rocks it as it jets and pulls its head into the shell (`withdraw`). It prints a
WINDING line for each: the check that nothing is inside out.

A cameroceras, a giant straight-shelled nautiloid of the Ordovician seas, 6 m from the point of its shell to the tips
of its arms, built from what the fossils and the usual reconstructions show (no picture was traced or copied):

- THE SHELL: a long, straight, slowly widening cone (an orthocone), 4.75 m from its point to its opening and 0.72 m
  across there; shallow growth bands round it (in the model on the full one, drawn by the shader on all three); the
  last 0.7 m of it is the open body chamber: a lip, a smooth inner wall, the last septum at its back.
- THE SOFT BODY: a squid-like head filling the opening, a big eye each side, a thick leathery hood over the top of
  the head (hinged at the top of the opening, it shuts over it when the head is pulled in), a funnel beneath, and a
  crown of ten arms out of the front of the head, trailing back.

Everything here is in Godot space (metres, Y up, X to its left side) until it is written out. IT JETS SHELL FIRST:
its -Z (Godot's forward) is the way it goes, the point of the shell leading; the opening, the head and the arms face
+Z. THE ORIGIN is on the shell's axis half way along the whole animal (from the shell's point to the arms' tips).

What a point is, for the shader: see `Mesh` below. The parts: 0 the shell (`k`.z 0 its outside, 1 the inner wall of
the body chamber and the septum, 2 the lip), 1 the head (`index` 0) and the funnel (`index` 1, `a` 0 at its root to 1
at its mouth), 2 an eye (`root` its middle), 3 the hood (`root` its hinge, `a` 0 at the hinge to 1 at its front
edge), 4 an arm (`index` 0 to 9, `root` its root, `k` the way it points at rest, `a` 0 at its root to 1 at its tip).

The numbers marked "as the shader has it" are in cameroceras.gdshader too: change one, change the other.
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
TAU = math.tau
UP = Vector((0.0, 1.0, 0.0))


def pick(low, full, lo, game):
    """The full model's number, the low one's or the game one's (`low` is False, True or "game")."""
    if low == "game":
        return game
    return lo if low else full


def to_b(p):
    """Godot's space (Y up, nose at -Z) to Blender's (Z up, nose at +Y)."""
    return Vector((p.x, -p.z, p.y))


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


class Mesh:
    """The model as it is being made. What is written at each point, for the shader:
    UV2.y the part times 16 plus `index`; the colour's red, green and blue `root` (a place in BOX: 0 its
    least corner, 1 its greatest); the colour's alpha `a`; UV.x, UV.y and UV2.x `k` (three numbers).
    (The glTF writer flips V: what is written is 1 - v, so that Godot reads v.)"""

    def __init__(self):
        self.verts = []
        self.faces = []
        self.data = []
        self.out = []
        self.count = {}
        self.part = 0
        self.index = 0
        self.root = None
        self.k = Vector((0.0, 0.0, 0.0))
        self.a = 0.0

    def add(self, p, k=None, a=None):
        k = self.k if k is None else k
        a = self.a if a is None else a
        colour = (0.0, 0.0, 0.0)
        if self.root is not None:
            colour = tuple((self.root[i] - BOX[0][i]) / (BOX[1][i] - BOX[0][i]) for i in range(3))
            assert all(0.0 <= c <= 1.0 for c in colour), "a joint outside BOX: %s" % (self.root,)
        self.verts.append(Vector(p))
        self.data.append(((k[0], 1.0 - k[1]), (k[2], 1.0 - (self.part * 16 + self.index)), (colour[0], colour[1], colour[2], a)))
        return len(self.verts) - 1

    def face(self, points, out, name):
        """A face wound so that its front (the side its points go round anticlockwise) is towards `out`."""
        ps = [self.verts[i] for i in points]
        n = Vector((0.0, 0.0, 0.0))
        for i in range(len(ps)):
            n += ps[i].cross(ps[(i + 1) % len(ps)])
        if n.length < 1e-14:
            return
        if n.dot(out) < 0.0:
            points = tuple(reversed(points))
        self.faces.append(tuple(points))
        self.out.append((Vector(out), name))
        self.count[name] = self.count.get(name, 0) + 1


def loft(m, rings, name, cap0=None, cap1=None, tags=None, out=None):
    """A skin through `rings` (closed loops of as many points each). A cap is None (left open), True (a
    fan to the loop's middle) or a place (a fan to that point). `tags(p, ring, corner)` gives a point's
    (k, a); `out(middle of a face)` the way that face should look, where "away from the loops' middles"
    would be wrong."""
    centres = [sum(r, Vector()) / len(r) for r in rings]
    rows = []
    for ri, ring in enumerate(rings):
        row = []
        for ci, p in enumerate(ring):
            k, a = tags(p, ri, ci) if tags else (None, None)
            row.append(m.add(p, k, a))
        rows.append(row)
    count = len(rings[0])
    for r in range(len(rows) - 1):
        between = (centres[r] + centres[r + 1]) * 0.5
        for c in range(count):
            n = (c + 1) % count
            quad = (rows[r][c], rows[r][n], rows[r + 1][n], rows[r + 1][c])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, out(middle) if out else middle - between, name)
    for cap, row, centre, other, ri in ((cap0, rows[0], centres[0], centres[min(1, len(rings) - 1)], 0),
                                        (cap1, rows[-1], centres[-1], centres[max(len(rings) - 2, 0)], len(rings) - 1)):
        if cap is None:
            continue
        at = centre if cap is True else Vector(cap)
        k, a = tags(at, ri, -1) if tags else (None, None)
        tip = m.add(at, k, a)
        way = centre - other
        if cap is not True and (at - centre).length > 1e-9:
            way = way + (at - centre)
        for c in range(count):
            n = (c + 1) % count
            middle = (m.verts[tip] + m.verts[row[c]] + m.verts[row[n]]) / 3.0
            m.face((tip, row[c], row[n]), out(middle) if out else way, name)


def frames(path, ref=None):
    """A direction and two sideways axes at each point of a path, turning as little as they can."""
    count = len(path)
    tangents = [(path[min(i + 1, count - 1)] - path[max(i - 1, 0)]).normalized() for i in range(count)]
    if ref is None:
        ref = UP if abs(tangents[0].y) < 0.9 else Vector((1.0, 0.0, 0.0))
    u = Vector(ref)
    made = []
    for t in tangents:
        u = (u - t * u.dot(t)).normalized()
        made.append((t, u, t.cross(u)))
    return made


# The game model's tubes have few sides: each is made a little fatter, so that it looks as wide as the round
# one it stands for, seen from any side (a polygon of `sides` as wide on average as the circle).
FAT = [lambda sides: 1.0]


def game_fat(sides):
    return math.pi / (sides * math.sin(math.pi / sides))


def tube(m, path, radii, sides, name, along=None, caps=(True, True), ref=None, flat=1.0):
    """A round tube along `path`, `radii` at its points. With `along` (from, to), `a` runs from one to the
    other along its length."""
    path = [Vector(p) for p in path]
    lengths = [0.0]
    for i in range(1, len(path)):
        lengths.append(lengths[-1] + (path[i] - path[i - 1]).length)
    made = frames(path, ref)
    rings = []
    for (t, u, v), p, r in zip(made, path, radii):
        r = max(r, 1e-5) * FAT[0](sides)
        rings.append([p + (u * math.cos(TAU * s / sides) + v * (flat * math.sin(TAU * s / sides))) * r for s in range(sides)])

    def tags(p, ri, ci):
        if along is None:
            return None, None
        return None, along[0] + (along[1] - along[0]) * lengths[ri] / lengths[-1]

    loft(m, rings, name,
         cap0=(path[0] - made[0][0] * radii[0] * 0.5) if caps[0] else None,
         cap1=(path[-1] + made[-1][0] * radii[-1] * 0.5) if caps[1] else None, tags=tags)


def ball(m, centre, r, name, lat=8, lon=12, axis=None):
    """A sphere, its poles along `axis`."""
    centre = Vector(centre)
    ez = Vector(axis or (0.0, 0.0, 1.0)).normalized()
    ex = (UP if abs(ez.y) < 0.9 else Vector((1.0, 0.0, 0.0))).cross(ez).normalized()
    ey = ez.cross(ex)
    rings = []
    for i in range(1, lat):
        th = math.pi * i / lat
        rings.append([centre + ex * (r * math.sin(th) * math.cos(TAU * j / lon)) + ey * (r * math.sin(th) * math.sin(TAU * j / lon))
                      - ez * (r * math.cos(th)) for j in range(lon)])
    loft(m, rings, name, cap0=centre - ez * r, cap1=centre + ez * r, out=lambda middle: middle - centre)


def plate(m, name, point, normal, thick, ts, us, tags=None):
    """A thick curved plate: `point(t, u)` its middle surface (t 0 at its root to 1 at its far edge, u 0 at
    one side to 1 at the other), `normal(t, u)` the way its upper skin faces there. It is `thick` in its
    middle, thinning to nothing at its two sides and its far edge (closed there); its root is left open
    (it is sunk in what it grows from)."""
    for side in (1.0, -1.0):
        grid = []
        for t in ts:
            row = []
            for u in us:
                foil = 2.0 * math.sqrt(max(u * (1.0 - u), 0.0))
                swell = thick * foil * math.sqrt(max(1.0 - t, 0.0))
                p = point(t, u) + normal(t, u) * (side * swell * 0.5)
                k, a = tags(t, u) if tags else (None, None)
                row.append(m.add(p, k, a))
            grid.append(row)
        for ti in range(len(ts) - 1):
            for ui in range(len(us) - 1):
                tm = (ts[ti] + ts[ti + 1]) * 0.5
                um = (us[ui] + us[ui + 1]) * 0.5
                m.face((grid[ti][ui], grid[ti][ui + 1], grid[ti + 1][ui + 1], grid[ti + 1][ui]), normal(tm, um) * side, name)


def section_loft(m, zs, section, around, name, tags=None, caps=(True, True)):
    """A body along Z: `section(z)` gives (middle height, half depth above, half depth below, half
    width, squareness) at `z`; its rings are at `zs`."""
    rings = []
    for z in zs:
        cy, up, down, wide, power = section(z)
        ring = []
        for c in range(around):
            angle = c / around * TAU
            co = math.cos(angle)
            s = math.sin(angle)
            e = 2.0 / power
            y = math.copysign(abs(co) ** e, co) * (up if co >= 0.0 else down)
            x = math.copysign(abs(s) ** e, s) * wide
            ring.append(Vector((x, cy + y, z)))
        rings.append(ring)
    centres = [Vector((0.0, section(z)[0], z)) for z in zs]

    def facing(middle):
        if middle.z <= zs[0] + 1e-9:
            return Vector((0.0, 0.0, -1.0))
        if middle.z >= zs[-1] - 1e-9:
            return Vector((0.0, 0.0, 1.0))
        cy = section(min(max(middle.z, zs[0]), zs[-1]))[0]
        return Vector((middle.x, middle.y - cy, 0.0))

    loft(m, rings, name,
         cap0=centres[0] + Vector((0.0, 0.0, -0.002)) if caps[0] else None,
         cap1=centres[-1] + Vector((0.0, 0.0, 0.002)) if caps[1] else None,
         tags=tags, out=facing)
    return rings


def material_of(name, colour):
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = colour
    material.diffuse_color = colour
    return material


def finish(name, m, colour):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) for p in m.verts], [], m.faces)
    # (every layer made first, then each looked up by name: making one moves the others)
    mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.new(name="UV2")
    mesh.color_attributes.new(name="Col", type="FLOAT_COLOR", domain="POINT")
    uv = mesh.uv_layers["UVMap"].data
    uv2 = mesh.uv_layers["UV2"].data
    for poly in mesh.polygons:
        for corner, vi in enumerate(poly.vertices):
            d = m.data[vi]
            uv[poly.loop_start + corner].uv = d[0]
            uv2[poly.loop_start + corner].uv = d[1]
    colours = mesh.color_attributes["Col"]
    for i, d in enumerate(m.data):
        colours.data[i].color = d[2]
    # (the glTF writer only writes the colour that is marked for rendering)
    mesh.color_attributes.active_color = colours
    mesh.color_attributes.render_color_index = 0
    mesh.materials.append(material_of(name.replace("_lo", "").replace("_game", ""), colour))
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    lo = [min(p[i] for p in m.verts) for i in range(3)]
    hi = [max(p[i] for p in m.verts) for i in range(3)]
    print("BUILT %s verts=%d tris=%d from (%.3f, %.3f, %.3f) to (%.3f, %.3f, %.3f)" % ((name, len(mesh.vertices), tris) + tuple(lo) + tuple(hi)))
    # Nothing inside out: every face looks the way it was made to (Blender's front is the side a face's
    # normal is on).
    bad = {}
    for poly in mesh.polygons:
        out, group = m.out[poly.index]
        if poly.normal.dot(to_b(out)) <= 0.0:
            bad[group] = bad.get(group, 0) + 1
    told = ["%s %d/%d wrong" % (group, bad.get(group, 0), count) for group, count in m.count.items()]
    print("WINDING %s: %s: %s" % (name, "ok" if not bad else "INSIDE OUT", ", ".join(told)))
    return obj


def export_one(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", export_yup=True, use_selection=True,
        export_animations=False, export_texcoords=True,
        export_vertex_color="ACTIVE", export_all_vertex_colors=False,
    )


def render(folder, made, size, close=()):
    """Pictures of each model from every side (plain grey: the markings are the shader's)."""
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.show_cavity = True
    scene.display.shading.show_backface_culling = True
    scene.display.shading.color_type = "MATERIAL"
    scene.render.resolution_x, scene.render.resolution_y = 1200, 800
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    views = [("left", (1, 0, 0)), ("right", (-1, 0, 0)), ("front", (0, 1, 0)), ("back", (0, -1, 0)),
             ("top", (0.001, 0, 1)), ("under", (0.001, 0, -1)), ("quarter", (0.7, 0.6, 0.45))]
    for obj in made:
        for other in made:
            other.hide_render = other is not obj
        for view, direction in views:
            offset = Vector(direction).normalized() * 40.0
            camera.data.ortho_scale = size
            camera.location = offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s_%s.png" % (obj.name, view))
            bpy.ops.render.render(write_still=True)
    # close views: (name, direction in Godot space, where it looks in Godot space, how wide), of each model
    for obj in made:
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, wide in close:
            offset = to_b(Vector(direction)).normalized() * 40.0
            camera.data.ortho_scale = wide
            camera.location = to_b(Vector(target)) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(offset.normalized().z) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "close_%s_%s.png" % (obj.name, view))
            bpy.ops.render.render(write_still=True)


def build_all(name, make, colour, size, close=()):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    full = finish(name, make(False), colour)
    low = finish(name + "_lo", make(True), colour)
    game = finish(name + "_game", make("game"), colour)
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, name + ".glb"))
    export_one(low, os.path.join(OUT, name + "_lo.glb"))
    export_one(game, os.path.join(OUT, name + "_game.glb"))
    # (in the .blend: the full model in the middle, the low one to its left, the game one to its right)
    low.location.x = size * 0.3
    game.location.x = -size * 0.3
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, name + ".blend"))
    low.location.x = 0.0
    game.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low, game], size, close)


SHELL, HEAD, EYE, HOOD, ARM = range(5)
# As the shader has it: the box the joints are written in.
BOX = (Vector((-0.6, -0.6, 1.0)), Vector((0.6, 0.6, 2.6)))
# The shell: where its point is, where its opening is, its radius there, how thick its wall is there, how far
# back the open body chamber goes, how far apart its growth bands are (as the shader has them).
APEX_Z = -3.0
APERTURE_Z = 1.75
APERTURE_R = 0.36
WALL = 0.018
CHAMBER_Z = 1.05
BAND = 0.1
# The hood's hinge (as the shader has it), the eyes' middles (the left one; as the shader has it) and radius.
HINGE = Vector((0.0, 0.30, 1.74))
EYE_AT = Vector((0.262, 0.05, 1.93))
EYE_R = 0.105
# The arms: how many, where their crown is, how far out from its middle their roots are, how long they are.
ARMS = 10
CROWN = Vector((0.0, -0.02, 2.14))
CROWN_R = 0.13
ARM_LONG = 0.8


def shell_r(z, bands=False):
    """The shell's outer radius at `z` (the growth bands as low ridges, on the full model only)."""
    t = max((z - APEX_Z) / (APERTURE_Z - APEX_Z), 0.0)
    # (its point not quite sharp)
    r = APERTURE_R * (t + 0.003) ** 0.92
    if bands:
        f = ((APERTURE_Z - z) / BAND) % 1.0
        r *= 1.0 + 0.012 * smooth(0.0, 0.25, f) * (1.0 - smooth(0.3, 1.0, f)) * smooth(0.0, 0.1, t)
    return r


def shell(m, low):
    m.part, m.index, m.root, m.a = SHELL, 0, None, 0.0
    around = pick(low, 48, 10, 28)
    if low == "game":
        # rings close together where the point rounds off and at the opening, few along the straight cone
        zs = [APEX_Z + d for d in (0.012, 0.03, 0.08, 0.18, 0.35)]
        z = zs[-1]
        while z < APERTURE_Z - 0.6:
            z += 0.45
            zs.append(min(z, APERTURE_Z - 0.6))
        zs += [APERTURE_Z - 0.3, APERTURE_Z - 0.08, APERTURE_Z]
    else:
        step = pick(low, 0.016, 0.4, 0)
        zs = [APEX_Z + d for d in ((0.012, 0.03, 0.06, 0.1) if not low else (0.03,))]
        z = zs[-1]
        while z < APERTURE_Z - 1e-9:
            z = min(z + step, APERTURE_Z)
            zs.append(z)
    bands = not low
    rings = []
    for z in zs:
        r = shell_r(z, bands)
        rings.append([Vector((r * math.sin(TAU * c / around), r * math.cos(TAU * c / around), z)) for c in range(around)])
    m.k = Vector((0.0, 0.0, 0.0))
    loft(m, rings, "shell", cap0=Vector((0.0, 0.0, APEX_Z)), out=lambda middle: Vector((middle.x, middle.y, 0.0)) if middle.z > zs[0] else Vector((0.0, 0.0, -1.0)))
    # the inner wall of the body chamber, the septum at its back, and the lip
    m.k = Vector((0.0, 0.0, 1.0))
    inner = []
    izs = pick(low, [APERTURE_Z - i * 0.05 for i in range(15)] + [CHAMBER_Z], [APERTURE_Z, CHAMBER_Z], [APERTURE_Z, APERTURE_Z - 0.25, CHAMBER_Z])
    for z in izs:
        r = shell_r(z) - WALL
        inner.append([Vector((r * math.sin(TAU * c / around), r * math.cos(TAU * c / around), z)) for c in range(around)])
    loft(m, inner, "inner wall", out=lambda middle: Vector((-middle.x, -middle.y, 0.0)))
    # (the septum: a dish bowed back into the shell, facing the opening)
    rows = [inner[-1]]
    for f in pick(low, (0.75, 0.5, 0.25), (), (0.5,)):
        r = (shell_r(CHAMBER_Z) - WALL) * f
        rows.append([Vector((r * math.sin(TAU * c / around), r * math.cos(TAU * c / around), CHAMBER_Z - 0.06 * (1.0 - f * f))) for c in range(around)])
    loft(m, rows, "inner wall", cap1=Vector((0.0, 0.0, CHAMBER_Z - 0.06)), out=lambda middle: Vector((0.0, 0.0, 1.0)))
    m.k = Vector((0.0, 0.0, 2.0))
    lip = []
    for r, dz in ((shell_r(APERTURE_Z), 0.0), (shell_r(APERTURE_Z) - WALL * 0.5, 0.006), (shell_r(APERTURE_Z) - WALL, 0.0)):
        lip.append([Vector((r * math.sin(TAU * c / around), r * math.cos(TAU * c / around), APERTURE_Z + dz)) for c in range(around)])
    loft(m, lip, "lip", out=lambda middle: Vector((0.0, 0.0, 1.0)))
    m.k = Vector((0.0, 0.0, 0.0))


# The head along Z: z, the middle line's height, half its depth above that, below it, half its width.
HEAD_PROFILE = [
    (1.30, -0.01, 0.33, 0.33, 0.33),
    (1.80, -0.01, 0.325, 0.33, 0.33),
    (1.90, -0.01, 0.30, 0.325, 0.315),
    (1.98, -0.015, 0.27, 0.30, 0.29),
    (2.05, -0.02, 0.23, 0.25, 0.245),
    (2.11, -0.02, 0.185, 0.195, 0.19),
    (2.16, -0.02, 0.15, 0.15, 0.15),
    (2.19, -0.02, 0.10, 0.10, 0.10),
]


def head_section(z):
    z = max(HEAD_PROFILE[0][0], min(HEAD_PROFILE[-1][0], z))
    i = 0
    while i < len(HEAD_PROFILE) - 2 and z > HEAD_PROFILE[i + 1][0]:
        i += 1
    a, b = HEAD_PROFILE[i], HEAD_PROFILE[i + 1]
    t = (z - a[0]) / (b[0] - a[0])
    t = t * t * (3.0 - 2.0 * t)
    return tuple(a[j] + (b[j] - a[j]) * t for j in range(1, 5)) + (2.0,)


def head(m, low):
    m.part, m.index, m.root, m.a = HEAD, 0, None, 0.0
    if low == "game":
        zs = [1.4, 1.75, 1.86, 1.94, 2.0, 2.06, 2.11, 2.15, 2.19]
    elif low:
        zs = [1.5, 1.85, 2.0, 2.12, 2.19]
    else:
        zs = [1.30 + i * 0.89 / 60 for i in range(61)]
    section_loft(m, zs, head_section, pick(low, 40, 8, 20), "head")
    # the funnel: a tube under the head, its mouth facing back (+Z)
    m.index = 1
    n = pick(low, 12, 2, 3)
    path = [Vector((0.0, -0.22 - 0.07 * i / n, 1.80 + 0.27 * i / n)) for i in range(n + 1)]
    tube(m, path, [0.075 - 0.025 * i / n for i in range(n + 1)], pick(low, 16, 5, 8), "funnel", along=(0.0, 1.0), caps=(False, True))
    m.index = 0
    m.a = 0.0


def eyes(m, low):
    for sx in (1.0, -1.0):
        m.part, m.index, m.a = EYE, 0, 1.0
        centre = Vector((sx * EYE_AT.x, EYE_AT.y, EYE_AT.z))
        m.root = centre
        ball(m, centre, EYE_R, "eyes", lat=pick(low, 16, 4, 10), lon=pick(low, 32, 6, 24), axis=(sx, 0.0, 0.0))
    m.root = None
    m.a = 0.0


def hood(m, low):
    """A thick leathery hood over the top of the head, from the top of the opening forward."""
    m.part, m.index, m.root = HOOD, 0, HINGE
    front = 2.25

    def radius(z):
        cy, up, down, wide, power = head_section(z)
        return max(up, 0.12)

    def spread(t):
        # how far round the head it reaches, each side (radians): narrow at its hinge (so that, turned down,
        # it fits the opening), its front edge rounded
        return math.radians(78.0) * (0.5 + 0.5 * smooth(0.0, 0.4, t)) * math.sqrt(max(1.0 - t ** 3, 0.0)) * (1.0 - 0.25 * t) + 0.02

    def point(t, u):
        z = HINGE.z + (front - HINGE.z) * t
        r = min(radius(z) + 0.035, shell_r(APERTURE_Z) - WALL - 0.012) if t < 0.05 else radius(z) + 0.035
        a = (u - 0.5) * 2.0 * spread(t)
        return Vector((r * math.sin(a), -0.01 + r * math.cos(a), z))

    def normal(t, u):
        a = (u - 0.5) * 2.0 * spread(t)
        return Vector((math.sin(a), math.cos(a), 0.0))

    ts = pick(low, [i / 20 for i in range(21)], [0.0, 0.5, 1.0], [0.0, 0.25, 0.5, 0.7, 0.85, 1.0])
    us = pick(low, [i / 24 for i in range(25)], [0.0, 0.5, 1.0], [0.0, 0.06, 0.18, 0.34, 0.5, 0.66, 0.82, 0.94, 1.0])
    plate(m, "hood", point, normal, 0.06, ts, us, tags=lambda t, u: (None, t))
    m.root = None
    m.a = 0.0


def arms(m, low):
    for i in range(ARMS):
        angle = TAU * (i + 0.5) / ARMS
        out = Vector((math.sin(angle), math.cos(angle), 0.0))
        root = CROWN + out * CROWN_R
        # (the two lowest a little longer)
        long = ARM_LONG * (1.12 if abs(math.cos(angle)) > 0.9 and math.cos(angle) < 0.0 else 1.0)
        way = (Vector((0.0, 0.0, 1.0)) + out * 0.22 + Vector((0.0, -0.06, 0.0))).normalized()
        n = pick(low, 40, 5, 9)
        ts = [j / n for j in range(n + 1)]
        if low == "game":
            ts = [0.0, 0.08, 0.17, 0.27, 0.37, 0.47, 0.57, 0.66, 0.75, 0.83, 0.9, 0.95, 1.0]
        path = []
        for t in ts:
            s = long * t
            # trailing back, drooping a little, the tip turned out
            p = root + way * s + Vector((0.0, -0.05, 0.0)) * (t * t) + out * (0.06 * t ** 3)
            path.append(p)
        m.part, m.index, m.root = ARM, i, root
        m.k = way
        radii = [0.048 * (1.0 - 0.82 * t) ** 0.9 + 0.004 for t in ts]
        tube(m, path, radii, pick(low, 12, 4, 6), "arms", along=(0.0, 1.0), caps=(False, True))
    m.root = None
    m.k = Vector((0.0, 0.0, 0.0))
    m.a = 0.0
    m.index = 0


def make(low):
    FAT[0] = game_fat if low == "game" else (lambda sides: 1.0)
    m = Mesh()
    shell(m, low)
    head(m, low)
    eyes(m, low)
    hood(m, low)
    arms(m, low)
    return m


if __name__ == "__main__":
    print("AS THE SHADER HAS IT: HINGE %s EYE_AT %s CROWN %s" % (tuple(HINGE), tuple(EYE_AT), tuple(CROWN)))
    build_all("cameroceras", make, (0.78, 0.68, 0.52, 1.0), 6.6,
              close=[("head", (-1, 0.3, 0.5), (0, 0, 2.1), 1.6), ("front", (0, 0.2, 1), (0, 0, 2.1), 1.4), ("apex", (-1, 0.3, -0.4), (0, 0, -2.6), 0.9)])
