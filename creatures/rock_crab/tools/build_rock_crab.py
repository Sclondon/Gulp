"""Builds the red rock crab (creatures/rock_crab) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/rock_crab/tools/build_rock_crab.py
    blender --background --python creatures/rock_crab/tools/build_rock_crab.py -- <preview folder>   # with pictures

Writes creatures/rock_crab/models/rock_crab.glb (the full model) and rock_crab_lo.glb (far off, phones), and the
editable creatures/rock_crab/tools/rock_crab.blend (this folder has a .gdignore). Each is one still mesh with
one surface: the shader (rock_crab.gdshader) draws every marking, walks its legs and raises its claws. It
prints a WINDING line for each: the check that nothing is inside out.

A red rock crab (Cancer productus), 0.16 m across its shell, built from the species (no picture was traced or
copied):

- THE SHELL: a fan, widest (0.16 m) a little behind its middle, its front edge a broad arc cut into nine
  teeth on each side from the eye to the widest point, five small teeth between the eyes, its rear edges
  drawing in to a narrow back; a low dome above, shallower beneath; 0.104 m from front to back.
- THE CLAWS: an arm out from under the front corner of the shell to an elbow, a swollen palm folded in across
  the front of the shell, a fixed finger and, above it, a finger that opens.
- EIGHT WALKING LEGS, four a side, splayed: out and a little up to a knee beyond the shell's edge, then down to a
  point on the ground.
- Two eyes on short stalks in notches of the front edge.

Everything here is in Godot space (metres, Y up, X to its left side, its front at -Z) until it is written out.
THE ORIGIN IS ON THE GROUND under the middle of the shell: its feet stand at y 0.

What a point is, for the shader: see `Mesh` below. The parts: 0 the shell (k.x how far out from its middle,
0 to 1 at its edge; k.y 1 on top, 0 beneath), 1 a walking leg (`index` which, 0 the first; `root` its joint
with the body, `k` its knee, `a` 0 above the knee and 1 below it), 2 a claw (`root` its shoulder, `k` the
hinge of its upper finger; `index` 0 the arm and palm, 1 the fixed finger, 2 the finger that opens; on a
finger `a` runs 0 to 1 to its tip), 3 an eye (`a` 0 its stalk, 1 the eye).

The numbers marked "as the shader has it" are in rock_crab.gdshader too: change one, change the other.
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


def bezier(points, t):
    points = [Vector(p) for p in points]
    while len(points) > 1:
        points = [points[i].lerp(points[i + 1], t) for i in range(len(points) - 1)]
    return points[0]


class Mesh:
    """The model as it is being made. What is written at each point, for the shader:
    UV2.y the part times 16 plus `index` (which leg, which side plate...); the colour's red, green and
    blue `root` (the joint the part turns about, as a place in BOX: 0 its least corner, 1 its greatest);
    the colour's alpha `a`; UV.x, UV.y and UV2.x `k` (three numbers: on a leg its knee, in metres).
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


def game_rings(knots, grooves, gap, fine=0.0):
    """Where the game model's rings go along the body: at every knot of its outline (where its curve
    turns), at each groove (and `fine` either side of it), and nowhere further apart than `gap`; two
    closer than a tenth of `gap` are one."""
    zs = sorted(set(list(knots) + [b + d for b in grooves for d in ((-fine, 0.0, fine) if fine else (0.0,))]))
    zs = [z for z in zs if knots[0] <= z <= knots[-1]]
    made = [zs[0]]
    for z in zs[1:]:
        start = made[-1]
        if z - start < gap * 0.1:
            if z == zs[-1]:
                made[-1] = z
            continue
        n = max(1, math.ceil((z - start) / gap - 1e-9))
        made += [start + (z - start) * i / n for i in range(1, n)] + [z]
    return made


def tube(m, path, radii, sides, name, flat=1.0, along=None, caps=(True, True), ref=None):
    """A round (or, with `flat`, flattened across `ref`) tube along `path`, `radii` at its points. With
    `along` (from, to), `a` runs from one to the other along its length."""
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


def ball(m, centre, rx, ry, rz, name, lat=8, lon=12, basis=None, tags=None):
    """An ellipsoid: `basis` its three axes (its poles on the third)."""
    centre = Vector(centre)
    ex, ey, ez = basis or (Vector((1.0, 0.0, 0.0)), Vector((0.0, 1.0, 0.0)), Vector((0.0, 0.0, 1.0)))
    rings = []
    for i in range(1, lat):
        th = math.pi * i / lat
        rings.append([centre + ex * (rx * math.sin(th) * math.cos(TAU * j / lon)) + ey * (ry * math.sin(th) * math.sin(TAU * j / lon))
                      - ez * (rz * math.cos(th)) for j in range(lon)])
    loft(m, rings, name, cap0=centre - ez * rz, cap1=centre + ez * rz, tags=tags, out=lambda middle: middle - centre)


def spine(m, base, tip, radius, sides, name, tip_a=None):
    """A cone standing on the skin (its foot is sunk in it, so it has no floor). With `tip_a`, its tip
    is given that `a` (its foot keeps the mesh's own)."""
    base = Vector(base)
    tip = Vector(tip)
    t, u, v = frames([base, tip])[0]
    ring = [base + (u * math.cos(TAU * s / sides) + v * math.sin(TAU * s / sides)) * radius for s in range(sides)]
    middle = (base + tip) * 0.5
    tags = None if tip_a is None else (lambda p, ri, ci: (None, tip_a if ci < 0 else None))
    loft(m, [ring], name, cap1=tip, tags=tags, out=lambda at: (at - middle) - t * (at - middle).dot(t) + t * radius * 0.2)


def basis_of(forward, up=UP):
    """Three axes for a `ball`: its poles along `forward`, its second axis as near `up` as it can be."""
    ez = Vector(forward).normalized()
    ex = Vector(up).cross(ez).normalized()
    return ex, ez.cross(ex), ez


def leg(m, part, index, root, heading, reach, knee_high, radius, sides, name, low=False):
    """A walking leg, in the upright plane through `root` that looks along `heading` (degrees from
    straight out to its side, towards its tail): up and out to its knee, KNEE_AT of the way out, then
    down to its tip on the ground `reach` out. The shader works the leg out again from the joint and
    the knee alone, so every leg must be made here."""
    root = Vector(root)
    side = 1.0 if root.x >= 0.0 else -1.0
    angle = math.radians(heading)
    d = Vector((side * math.cos(angle), 0.0, math.sin(angle)))
    knee = root + d * (KNEE_AT * reach)
    knee.y = knee_high
    tip = root + d * reach
    tip.y = 0.0
    bend = knee.lerp(tip, 0.5) + d * (0.07 * reach) + UP * (0.03 * reach)
    m.part, m.index, m.root, m.k = part, index, root, knee
    m.a = 0.0
    if low == "game":
        # (the game model: the full one's swell, no caps where the ends are hidden)
        tube(m, [root, root.lerp(knee, 0.5), knee], [radius * 0.95, radius * 1.12, radius * 0.95], sides, name, caps=(False, False))
    elif low:
        tube(m, [root, knee], [radius, radius * 0.95], sides, name, caps=(False, True))
    else:
        tube(m, [root, root.lerp(knee, 0.5), knee], [radius * 0.95, radius * 1.12, radius * 0.95], sides, name)
    m.a = 1.0
    if low == "game":
        tube(m, [knee, knee.lerp(bend, 0.5), bend, tip], [radius * 0.9, radius * 0.95, radius * 0.72, radius * 0.2], sides, name, caps=(True, False))
    elif low:
        tube(m, [knee, bend, tip], [radius * 0.9, radius * 0.7, radius * 0.2], sides, name, caps=(True, False))
    else:
        tube(m, [knee, knee.lerp(bend, 0.5), bend, bend.lerp(tip, 0.5), tip],
             [radius * 0.9, radius * 0.95, radius * 0.72, radius * 0.55, radius * 0.2], sides, name)
    m.root = None
    m.a = 0.0
    m.index = 0
    return knee, tip


def blade(m, name, point, facing, thick, nt, nu, tags=None):
    """A thin closed blade (a fin, a tail fan's paddle, a swimmeret): `point(t, u)` is a place in the
    model (t 0 at its root to 1 at its tip, u 0 at its leading edge to 1 at its trailing edge),
    `facing` the way one of its two skins faces. It is `thick` at its root, a foil across (nothing at
    either edge), thinning towards its tip. `tags(t, u)` gives a point's (k, a)."""
    facing = Vector(facing).normalized()
    for side in (1.0, -1.0):
        grid = []
        for ti in range(nt + 1):
            t = ti / nt
            row = []
            for ui in range(nu + 1):
                u = ui / nu
                foil = 2.6 * math.sqrt(u) * (1.0 - u)
                swell = thick * (1.0 - 0.7 * t) * foil
                p = point(t, u) + facing * (side * swell * 0.5)
                k, a = tags(t, u) if tags else (None, None)
                row.append(m.add(p, k, a))
            grid.append(row)
        for ti in range(nt):
            for ui in range(nu):
                m.face((grid[ti][ui], grid[ti][ui + 1], grid[ti + 1][ui + 1], grid[ti + 1][ui]), facing * side, name)


def section_loft(m, zs, section, around, name, tags=None, caps=(True, True)):
    """A body along Z: `section(z)` gives (middle height, half depth above, half depth below, half
    width, squareness) at `z`; its rings are at `zs`. A point is `angle` round from the ridge of the
    back (0) by its left side (a quarter turn) to the keel (half a turn)."""
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

    def out(middle):
        # (away from the middle line at that place along it)
        z = middle.z
        cy = section(min(max(z, zs[0]), zs[-1]))[0]
        return Vector((middle.x, middle.y - cy, 0.0)) if zs[0] < z < zs[-1] else None

    def facing(middle):
        if middle.z <= zs[0] + 1e-9:
            return Vector((0.0, 0.0, -1.0))
        if middle.z >= zs[-1] - 1e-9:
            return Vector((0.0, 0.0, 1.0))
        return out(middle)

    loft(m, rings, name,
         cap0=centres[0] + Vector((0.0, 0.0, -0.0005)) if caps[0] else None,
         cap1=centres[-1] + Vector((0.0, 0.0, 0.0005)) if caps[1] else None,
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
    # Nothing inside out: every face looks the way it was made to (the skin of a body or a limb away
    # from its middle line; Blender's front is the side a face's normal is on).
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
    # (Blender space: it lies along Y, its head at +Y, up is Z)
    views = [("left", (1, 0, 0)), ("right", (-1, 0, 0)), ("front", (0, 1, 0)), ("back", (0, -1, 0)),
             ("top", (0.001, 0, 1)), ("under", (0.001, 0, -1)), ("quarter", (0.7, 0.6, 0.45))]
    for obj in made:
        for other in made:
            other.hide_render = other is not obj
        for view, direction in views:
            offset = Vector(direction).normalized() * 40.0
            camera.data.ortho_scale = size
            camera.location = Vector((0.0, 0.0, size * 0.15)) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s_%s.png" % (obj.name, view))
            bpy.ops.render.render(write_still=True)
    # close views of the full model: (name, direction in Godot space, where it looks in Godot space, how wide)
    for other in made:
        other.hide_render = other is not made[0]
    for view, direction, target, wide in close:
        offset = to_b(Vector(direction)).normalized() * 40.0
        camera.data.ortho_scale = wide
        camera.location = to_b(Vector(target)) + offset
        camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(offset.normalized().z) < 0.9 else "X").to_euler()
        scene.render.filepath = os.path.join(folder, "close_%s.png" % view)
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
    low.location.x = size
    game.location.x = -size
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, name + ".blend"))
    low.location.x = 0.0
    game.location.x = 0.0
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low, game], size, close)

SHELL, LEG, CLAW, EYE = 0, 1, 2, 3
# As the shader has it: the box the joints' places are written in; how far out along a leg its knee is.
BOX = (Vector((-0.1, 0.0, -0.1)), Vector((0.1, 0.1, 0.1)))
KNEE_AT = 0.62
# As the shader has it: the height of the shell's edge.
RIM = 0.036
DOME = 0.022
KEEL = 0.021

# Half the shell's outline from above (x out to its side, z back), from the middle of its front to the
# middle of its back.
OUTLINE = [(0.0, -0.050), (0.0135, -0.0505), (0.021, -0.047), (0.034, -0.0435), (0.047, -0.037), (0.059, -0.0275),
           (0.069, -0.016), (0.0765, -0.003), (0.080, 0.010), (0.075, 0.024), (0.062, 0.037), (0.046, 0.047),
           (0.026, 0.053), (0.0, 0.054)]
# (the spans of it that carry the nine teeth: from the eye's notch to the widest point)
TEETH_FROM, TEETH_TO = 2, 8


def catmull(p0, p1, p2, p3, t):
    return 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t)


def outline(low):
    """The shell's edge from above, all the way round: (x, z, how much of a tooth's tip this point is)."""
    half = [Vector((x, z)) for x, z in OUTLINE]
    loop = half + [Vector((-p.x, p.y)) for p in reversed(half[1:-1])]
    count = len(loop)
    per = 2 if low else 8
    made = []
    for i in range(count):
        p0, p1, p2, p3 = loop[(i - 1) % count], loop[i], loop[(i + 1) % count], loop[(i + 2) % count]
        span = i if i < len(half) - 1 else count - 1 - i
        ts = [s / per for s in range(per)]
        if low == "game" and span >= len(half) - 3:
            # (the game model: one point to a span across the flat middle of its back)
            ts = [0.0]
        if low == "game" and TEETH_FROM <= span < TEETH_TO:
            # the game model: a point at the foot and at the tip of each tooth, where the full one has them
            ts = []
            for k in range(10):
                for f in (0.0, 0.1):
                    tt = (k + f) / 9.0 * (TEETH_TO - TEETH_FROM) - (span - TEETH_FROM)
                    t = tt if i < len(half) - 1 else 1.0 - tt
                    if 0.0 <= t < 1.0 - 1e-6:
                        ts.append(t)
            ts = sorted(set(round(t, 6) for t in ts))
        if low == "game" and span == 0:
            # the game model: a point at the tip and the notch of each small tooth between the eyes
            ts = []
            for k in range(5):
                tt = k * 0.0028 / OUTLINE[1][0]
                t = tt if i < len(half) - 1 else 1.0 - tt
                if 0.0 <= t < 1.0 - 1e-6:
                    ts.append(t)
            ts = sorted(ts)
        for t in ts:
            p = catmull(p0, p1, p2, p3, t)
            tooth = 0.0
            if TEETH_FROM <= span < TEETH_TO and low is not True:
                # nine teeth: each a rounded saw tooth that leans forward
                along = (span - TEETH_FROM + (t if i < len(half) - 1 else 1.0 - t)) / (TEETH_TO - TEETH_FROM) * 9.0
                f = along % 1.0
                tooth = (1.0 - f) ** 1.6 * smooth(0.0, 0.12, f)
            made.append((p.x, p.y, tooth))
    return made


def shell(m, low):
    edge = outline(low)
    middle = Vector((0.0, 0.004))
    tops = pick(low, (0.035, 0.1, 0.25, 0.42, 0.58, 0.72, 0.84, 0.93, 0.98, 1.0), (0.5, 1.0), (0.3, 0.62, 0.86, 0.975, 1.0))
    unders = pick(low, (0.97, 0.88, 0.7, 0.45, 0.18), (0.6,), (0.94, 0.65))
    rings = []
    info = []

    def at(rho, top):
        ring = []
        for x, z, tooth in edge:
            p = middle + (Vector((x, z)) - middle) * rho
            out = (Vector((x, z)) - middle).normalized()
            if top:
                p += out * (0.0055 * tooth * smooth(0.975, 1.0, rho))
            # the five small teeth between the eyes
            if abs(x) < 0.0135 and z < 0.0 and low is not True:
                p.y -= 0.003 * max(0.0, math.cos(TAU * p.x / 0.0056)) ** 0.7 * smooth(0.85, 1.0, rho)
            if top:
                y = RIM + DOME * (1.0 - rho * rho) ** 0.55
                # (the shell's regions: a low swell each side of the middle, a dip behind the front)
                y += 0.0022 * math.exp(-((abs(p.x) - 0.03) / 0.017) ** 2 - ((p.y - 0.008) / 0.02) ** 2)
                y -= 0.0012 * math.exp(-(p.x / 0.012) ** 2 - ((p.y + 0.012) / 0.01) ** 2)
            else:
                y = RIM - KEEL * (1.0 - rho ** 2.2) ** 0.7
            ring.append(Vector((p.x, y, p.y)))
        rings.append(ring)
        info.append((rho, 1.0 if top else 0.0))

    for rho in tops:
        at(rho, True)
    for rho in unders:
        at(rho, False)
    m.part, m.index, m.root = SHELL, 0, None

    def tags(p, ri, ci):
        if ci < 0:
            return Vector((0.0, info[ri][1], 0.0)), 0.0
        return Vector((info[ri][0], info[ri][1], 0.0)), 0.0

    crown = Vector((0.0, RIM + DOME, 0.004))
    keel = Vector((0.0, RIM - KEEL, 0.004))
    heart = Vector((0.0, RIM, 0.004))
    loft(m, rings, "shell", cap0=crown, cap1=keel, tags=tags,
         out=lambda at: Vector(((at.x - heart.x) * 0.15, (at.y - heart.y) * 6.0 + (0.002 if at.y > RIM else -0.002), (at.z - heart.z) * 0.15)))


def eyes(m, low):
    for sx in (1.0, -1.0):
        foot = Vector((sx * 0.0172, RIM + 0.0005, -0.0465))
        head = Vector((sx * 0.0178, RIM + 0.0052, -0.0497))
        m.part, m.index, m.root, m.a = EYE, 0, None, 0.0
        if low is not True:
            tube(m, [foot, head], [0.0019, 0.0017], pick(low, 8, 0, 5), "eyes", caps=(False, False))
        m.a = 1.0
        ball(m, head, 0.0026, 0.0026, 0.0026, "eyes", lat=pick(low, 6, 3, 5), lon=pick(low, 10, 4, 12))
    m.a = 0.0


def claws(m, low):
    """Each claw at rest: folded in across the front of the shell."""
    sides = pick(low, 10, 4, 5)
    told = None
    for sx in (1.0, -1.0):
        def v(x, y, z):
            return Vector((sx * x, y, z))
        shoulder = v(0.052, 0.021, -0.031)
        elbow = v(0.069, 0.019, -0.046)
        wrist = v(0.061, 0.019, -0.057)
        # the palm lies inward and forward from the wrist
        along = v(-0.93, -0.02, -0.36).normalized()
        palm = wrist + along * 0.017
        ex, ey, ez = basis_of(along)
        knuckle = palm + along * 0.0125
        hinge = knuckle + ey * 0.0065
        m.part, m.root, m.k = CLAW, shoulder, hinge
        m.index, m.a = 0, 0.0
        tube(m, [shoulder, shoulder.lerp(elbow, 0.5), elbow], [0.0055, 0.0068, 0.006], sides, "claws", caps=(low is False, True))
        tube(m, [elbow, wrist], [0.0062, 0.0066], sides, "claws")
        ball(m, palm, 0.0078, 0.0115, 0.0165, "claws", lat=pick(low, 9, 4, 5), lon=pick(low, 14, 6, 9), basis=(ex, ey, ez))
        # the fixed finger, below; and the finger that opens, above: both curve to meet at their tips
        tip = knuckle + along * 0.026 - ey * 0.002
        low_from = knuckle - ey * 0.0055
        steps = pick(low, 7, 2, 3)
        m.index = 1
        path = [bezier([low_from, low_from + along * 0.013 - ey * 0.004, tip], i / steps) for i in range(steps + 1)]
        tube(m, path, [0.0062 * (1.0 - 0.8 * (i / steps) ** 1.3) for i in range(steps + 1)], sides, "claws", flat=0.8, along=(0.0, 1.0), ref=ey)
        m.index = 2
        path = [bezier([hinge - along * 0.002, hinge + along * 0.014 + ey * 0.006, tip + ey * 0.0012], i / steps) for i in range(steps + 1)]
        tube(m, path, [0.0052 * (1.0 - 0.8 * (i / steps) ** 1.3) for i in range(steps + 1)], sides, "claws", flat=0.8, along=(0.0, 1.0), ref=ey)
        if sx > 0.0:
            told = (shoulder, hinge, ex)
    m.root, m.index, m.a = None, 0, 0.0
    return told


# The walking legs of one side, first to last: (where its joint is, the way it points in degrees from
# straight out to the side towards the tail, how far out its tip stands, how high its knee is).
LEGS = [((0.047, 0.0165, -0.013), -30.0, 0.072, 0.046),
        ((0.049, 0.0165, 0.001), -6.0, 0.078, 0.048),
        ((0.048, 0.0165, 0.015), 20.0, 0.076, 0.047),
        ((0.043, 0.0165, 0.028), 48.0, 0.066, 0.044)]


def make(low):
    FAT[0] = game_fat if low == "game" else (lambda sides: 1.0)
    m = Mesh()
    shell(m, low)
    eyes(m, low)
    told = claws(m, low)
    for sx in (1.0, -1.0):
        for i, (root, heading, reach, knee_high) in enumerate(LEGS):
            leg(m, LEG, i, (sx * root[0], root[1], root[2]), heading, reach, knee_high, 0.0052, pick(low, 8, 3, 3), "legs", low)
    if low is False:
        shoulder, hinge, ex = told
        print("CLAW the left one's shoulder (%.4f, %.4f, %.4f), its finger's hinge (%.4f, %.4f, %.4f), the hinge's axis (%.3f, %.3f, %.3f)"
              % (tuple(shoulder) + tuple(hinge) + tuple(ex)))
    return m


if __name__ == "__main__":
    build_all("rock_crab", make, (0.5, 0.14, 0.08, 1.0), 0.34)
