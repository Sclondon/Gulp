"""Builds the trilobites (creatures/trilobite) and exports them for Godot.

Run from the game's root:
    blender --background --python creatures/trilobite/tools/build_trilobite.py
    blender --background --python creatures/trilobite/tools/build_trilobite.py -- <preview folder>   # with pictures

Writes, for each kind (smooth, spiny, cheeks), creatures/trilobite/models/trilobite_<kind>.glb (the full model),
trilobite_<kind>_game.glb (the game model: few triangles, spent where the eye looks: the shell's outline, its eyes,
its spines) and trilobite_<kind>_lo.glb (far off, phones), and the editable creatures/trilobite/tools/trilobite.blend
(all nine; this folder has a .gdignore). Each is one still mesh with one surface: the shader (trilobite.gdshader)
draws every marking, walks its legs, beats its gills, swings its antennae and rolls it up (`enroll`). It prints a
WINDING line for each: the check that nothing is inside out.

Trilobites, built from what the fossils and the usual reconstructions show (no picture was traced or copied), three
kinds:

- SMOOTH (0.15 m): a smooth, rounded, very domed one (as Bumastus): a big head shield and a big tail shield, ten
  narrow body segments between them, the three lobes all but smoothed away, big eyes at the back of its cheeks.
- SPINY (0.2 m, spines not counted): a spiny one (as the odontopleurids): a narrow body with a strong middle lobe,
  long spines out and back from every body segment, long cheek spines, a row of short spines up its back, two long
  spines behind its tail shield, its eyes raised.
- CHEEKS (0.3 m): one with long swept-back cheek spines (as Olenellus): a broad half-moon head shield with long
  crescent eyes and a glabella widening forwards, its cheek spines sweeping back along its body, fourteen body
  segments ending in short points (the third with long ones), a tiny tail shield and a long spine back from its
  last segment.

Each has under its shell a pair of walking legs and of feathery gills to every segment (as many pairs as the kind
has), and two antennae out of the front of its head.

Everything here is in Godot space (metres, Y up, X to its left side, its head at -Z) until it is written out. THE
ORIGIN IS ON THE GROUND under the middle of its shell (half way from the front of its head shield to the back of its
tail shield): its feet stand at y 0, the bottom of its shell's rim is `VENTER` of its length up.

What a point is, for the shader: see `Mesh` below. The parts: 0 the shell (top and underside), 1 a walking leg
(`index` which pair, 0 the first; `root` its joint with the body, `k` its knee, `a` 0 above the knee and 1 below it),
2 a gill (`index`, `root` and `k` those of its leg; `a` 0 at its root to 1 at its tip), 3 an eye (`root` its
middle), 4 an antenna (`root` its base, `a` 0 at its base to 1 at its tip), 5 a spine (`index` 0 a cheek spine, 1 a
body segment's, 2 one up its back, 3 one behind its tail, 4 the long ones of the third segment; `root` its foot,
`a` 0 at its foot to 1 at its point).

The numbers marked "as the shader has it" are in trilobite.gdshader (as numbers times the animal's length) and in
trilobite.gd's KINDS: change one, change the others.
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



def blade(m, name, point, facing, thick, ts, nu, tags=None):
    """A thin closed blade (a gill): `point(t, u)` is a place in the model (t 0 at its root to 1 at its tip,
    u 0 at its leading edge to 1 at its trailing edge), `facing` the way one of its two skins faces. It is
    `thick` at its root, a foil across (nothing at either edge: with `nu` 1 a two-sided sheet)."""
    facing = Vector(facing).normalized()
    for side in (1.0, -1.0):
        grid = []
        for t in ts:
            row = []
            for ui in range(nu + 1):
                u = ui / nu
                foil = 2.6 * math.sqrt(u) * (1.0 - u)
                p = point(t, u) + facing * (side * thick * (1.0 - 0.7 * t) * min(1.0, 5.0 * (1.0 - t)) * foil * 0.5)
                k, a = tags(t, u) if tags else (None, None)
                row.append(m.add(p, k, a))
            grid.append(row)
        for ti in range(len(ts) - 1):
            for ui in range(nu):
                m.face((grid[ti][ui], grid[ti][ui + 1], grid[ti + 1][ui + 1], grid[ti + 1][ui]), facing * side, name)


def dome(m, centre, radii, axis, name, rings, around):
    """The front of an ellipsoid (an eye standing out of the shell): from its pole on `axis` back a little past
    its equator, open behind (sunk in the shell). `radii` are its half widths along X, Y and Z; its rings go
    round `axis` (so that an eye's rings go round where it looks)."""
    centre = Vector(centre)
    ez = Vector(axis).normalized()
    ex = (UP if abs(ez.y) < 0.9 else Vector((1.0, 0.0, 0.0))).cross(ez).normalized()
    ey = ez.cross(ex)
    loops = []
    for i in range(1, rings + 1):
        th = math.radians(105.0) * i / rings
        loop = []
        for j in range(around):
            d = ex * (math.sin(th) * math.cos(TAU * j / around)) + ey * (math.sin(th) * math.sin(TAU * j / around)) + ez * math.cos(th)
            loop.append(centre + Vector((d.x * radii[0], d.y * radii[1], d.z * radii[2])))
        loops.append(loop)
    pole = centre + Vector((ez.x * radii[0], ez.y * radii[1], ez.z * radii[2]))
    loft(m, list(reversed(loops)), name, cap1=pole, out=lambda middle: middle - centre)


def _slopes(xs, ys):
    """Tangents for a curve through the points that never overshoots them (Fritsch and Carlson)."""
    d = [(ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]) for i in range(len(xs) - 1)]
    s = [d[0]]
    for i in range(1, len(xs) - 1):
        if d[i - 1] * d[i] <= 0.0:
            s.append(0.0)
        else:
            w1 = 2.0 * (xs[i + 1] - xs[i]) + (xs[i] - xs[i - 1])
            w2 = (xs[i + 1] - xs[i]) + 2.0 * (xs[i] - xs[i - 1])
            s.append((w1 + w2) / (w1 / d[i - 1] + w2 / d[i]))
    s.append(d[-1])
    return s


class Curve:
    """A smooth curve through (x, y) knots that never overshoots them."""

    def __init__(self, knots):
        self.xs = [k[0] for k in knots]
        self.ys = [k[1] for k in knots]
        self.s = _slopes(self.xs, self.ys)

    def __call__(self, x):
        xs, ys, s = self.xs, self.ys, self.s
        x = max(xs[0], min(xs[-1], x))
        i = 0
        while i < len(xs) - 2 and x > xs[i + 1]:
            i += 1
        h = xs[i + 1] - xs[i]
        t = (x - xs[i]) / h
        return ((2 * t ** 3 - 3 * t ** 2 + 1) * ys[i] + (t ** 3 - 2 * t ** 2 + t) * h * s[i]
                + (-2 * t ** 3 + 3 * t ** 2) * ys[i + 1] + (t ** 3 - t ** 2) * h * s[i + 1])


SHELL, LEG, GILL, EYE, ANTENNA, SPINE = range(6)
GENAL, PLEURAL, AXIAL, TAIL, MACRO = range(5)
# As the shader has it (times the animal's length): the box the joints are written in; how far out along a leg
# (from its joint to its tip, seen from above) its knee is.
BOX_UNIT = (Vector((-0.9, -0.1, -0.9)), Vector((0.9, 0.6, 1.0)))
BOX = [Vector((0, 0, 0)), Vector((1, 1, 1))]
KNEE_AT = 0.45

# Each kind, every length as a share of its body's length (the front of its head shield to the back of its tail
# shield): `length` metres; where its head shield ends and its tail shield begins (z, as the shader has it); how
# many body segments; `venter` how high the bottom of its shell's rim stands (as the shader has it); `rim` how thick
# the rim is; its outline's half width, its dome's height, its middle lobe's half width and how high that stands,
# each as knots along it; `teeth` how far the body segments' points stand out; its eye (middle (x, z), half widths
# (x, y, z), the way it looks; as the shader has it); how many pairs of legs.
KINDS = {
    "smooth": {
        "length": 0.15, "head_back": -0.12, "tail_front": 0.12, "segments": 10, "venter": 0.06, "rim": 0.014,
        "width": [(-0.5, 0.0), (-0.495, 0.07), (-0.48, 0.14), (-0.44, 0.21), (-0.38, 0.265), (-0.3, 0.305), (-0.2, 0.33),
                  (-0.12, 0.34), (0.0, 0.335), (0.12, 0.322), (0.24, 0.295), (0.34, 0.25), (0.42, 0.19), (0.47, 0.12),
                  (0.492, 0.06), (0.5, 0.0)],
        "dome": [(-0.5, 0.0), (-0.48, 0.07), (-0.44, 0.135), (-0.38, 0.18), (-0.28, 0.215), (-0.12, 0.225), (0.12, 0.22),
                 (0.28, 0.205), (0.38, 0.17), (0.45, 0.115), (0.49, 0.055), (0.5, 0.0)],
        "axis": [(-0.5, 0.12), (-0.12, 0.13), (0.12, 0.125), (0.5, 0.1)],
        "raise": [(-0.5, 0.0), (-0.4, 0.008), (0.4, 0.008), (0.5, 0.0)],
        "teeth": 0.0,
        "eye": ((0.205, -0.19), (0.04, 0.032, 0.05), (1.0, 0.75, 0.05)),
        "legs": 10,
    },
    "spiny": {
        "length": 0.2, "head_back": -0.2, "tail_front": 0.3, "segments": 9, "venter": 0.07, "rim": 0.012,
        "width": [(-0.5, 0.0), (-0.495, 0.07), (-0.47, 0.15), (-0.42, 0.22), (-0.34, 0.27), (-0.26, 0.29), (-0.2, 0.29),
                  (-0.18, 0.26), (-0.05, 0.245), (0.1, 0.225), (0.3, 0.18), (0.38, 0.14), (0.45, 0.09), (0.49, 0.045),
                  (0.5, 0.0)],
        "dome": [(-0.5, 0.0), (-0.47, 0.035), (-0.4, 0.06), (-0.3, 0.075), (-0.2, 0.075), (0.3, 0.065), (0.42, 0.045),
                 (0.48, 0.022), (0.5, 0.0)],
        "axis": [(-0.5, 0.06), (-0.44, 0.11), (-0.3, 0.115), (-0.2, 0.095), (0.3, 0.075), (0.5, 0.04)],
        "raise": [(-0.5, 0.0), (-0.45, 0.05), (-0.32, 0.07), (-0.2, 0.05), (0.3, 0.045), (0.45, 0.025), (0.5, 0.0)],
        "teeth": 0.0,
        "eye": ((0.15, -0.31), (0.034, 0.03, 0.04), (1.0, 0.9, -0.1)),
        "legs": 11,
    },
    "cheeks": {
        "length": 0.3, "head_back": -0.17, "tail_front": 0.43, "segments": 14, "venter": 0.05, "rim": 0.01,
        "width": [(-0.5, 0.0), (-0.497, 0.08), (-0.485, 0.16), (-0.455, 0.24), (-0.4, 0.305), (-0.32, 0.35), (-0.24, 0.37),
                  (-0.175, 0.375), (-0.165, 0.29), (-0.05, 0.27), (0.1, 0.24), (0.25, 0.19), (0.38, 0.12), (0.43, 0.075),
                  (0.47, 0.05), (0.5, 0.0)],
        "dome": [(-0.5, 0.0), (-0.47, 0.03), (-0.4, 0.05), (-0.3, 0.06), (-0.17, 0.058), (0.3, 0.05), (0.43, 0.035),
                 (0.48, 0.02), (0.5, 0.0)],
        "axis": [(-0.5, 0.05), (-0.45, 0.105), (-0.33, 0.085), (-0.18, 0.07), (0.0, 0.075), (0.43, 0.04), (0.5, 0.03)],
        "raise": [(-0.5, 0.0), (-0.46, 0.04), (-0.18, 0.035), (0.43, 0.03), (0.5, 0.0)],
        "teeth": 0.0,
        "eye": ((0.165, -0.3), (0.028, 0.026, 0.075), (1.0, 0.85, 0.15)),
        "legs": 11,
    },
}


class Shape:
    """One kind's shell, in metres."""

    def __init__(self, kind):
        k = KINDS[kind]
        self.k = k
        self.L = k["length"]
        self.head_back = k["head_back"]
        self.tail_front = k["tail_front"]
        self.n = k["segments"]
        self.venter = k["venter"] * self.L
        self.rim = k["rim"] * self.L
        self.width = Curve(k["width"])
        self.dome = Curve(k["dome"])
        self.axis = Curve(k["axis"])
        self.raise_ = Curve(k["raise"])
        self.seg = (self.tail_front - self.head_back) / self.n
        # (the grooves between the body segments are in the full model's shape; the others' are the shader's)
        self.grooves = True

    def segment_at(self, zu):
        """Which body segment `zu` (a share of the length) is in, and how far through it (or None)."""
        if not self.head_back <= zu < self.tail_front:
            return None, 0.0
        f = (zu - self.head_back) / self.seg
        i = min(int(f), self.n - 1)
        return i, f - i

    def half_width(self, zu):
        w = self.width(zu)
        i, f = self.segment_at(zu)
        if i is not None and self.k["teeth"] > 0.0:
            # each segment ends in a point, standing out at its back
            w += self.k["teeth"] * f ** 3 * smooth(0.0, 0.3, f)
        return max(w, 0.0) * self.L

    def top(self, x, zu):
        """The height of the top of the shell at `x` (metres) across, `zu` along."""
        w = max(self.half_width(zu), 1e-6)
        u = min(abs(x) / w, 1.0)
        h = self.dome(zu) * self.L
        a = max(self.axis(zu) * self.L / w, 0.05)
        r = self.raise_(zu) * self.L
        dome = (1.0 - u ** 2.2) ** 0.75
        lobe = (1.0 - smooth(a * 0.7, a * 1.05, u)) * (1.0 - 0.35 * (u / a) ** 2 if u < a else 0.65)
        groove = 0.0
        i, f = self.segment_at(zu)
        if i is not None and self.grooves:
            # each segment's front edge a narrow groove across it
            groove = 0.18 * math.exp(-((min(f, 1.0 - f)) / 0.12) ** 2)
        return self.venter + self.rim + (h * dome + r * lobe) * (1.0 - groove * 0.5) - self.rim * groove * 0.3

    def ring(self, zu, across, under):
        """The shell's section at `zu`: across its top from its left edge to its right, then back under it."""
        w = max(self.half_width(zu), 1e-5)
        points = []
        for j in range(across + 1):
            u = -math.cos(math.pi * j / across)
            x = u * w
            points.append(Vector((x, self.top(x, zu) if abs(u) < 0.999 else self.venter + self.rim, zu * self.L)))
        for j in range(under + 1):
            u = math.cos(math.pi * j / under)
            points.append(Vector((u * w * 0.95, self.venter, zu * self.L)))
        return points


def ring_places(shape, low):
    """Where the shell's rings go (shares of its length)."""
    k = shape.k
    ends = [-0.5, 0.5]
    knots = sorted(set([x for x, _ in k["width"]] + [x for x, _ in k["dome"]]))
    bounds = [shape.head_back + i * shape.seg for i in range(shape.n + 1)]
    if low == "game":
        # a ring half way along each body segment (its crest: the grooves between are the shader's), and at
        # each knot of the outline that is not close to one of those
        mids = [b + 0.5 * shape.seg for b in bounds[:-1]]
        zs = set(round(z, 6) for z in mids)
        zs.update(z for z in knots if min(abs(z - x) for x in mids) > 0.3 * shape.seg)
        if k["teeth"] > 0.0:
            # (where a segment's point is, and the outline's step behind it)
            zs.update(round(b + f * shape.seg, 6) for b in bounds[:-1] for f in (0.03, 0.97))
        zs.update([0.5 - 0.002, -0.5 + 0.002])
        # (and no more than 0.075 apart over the head and tail shields)
        zs = sorted(z for z in zs if -0.5 < z < 0.5)
        more = []
        for a, b in zip(zs, zs[1:]):
            n = math.ceil((b - a) / 0.075 - 1e-9)
            more += [a + (b - a) * j / n for j in range(1, n)]
        return sorted(zs + more)
    if low:
        zs = set(knots[::2] + bounds)
        zs = sorted(z for z in zs if -0.5 < z < 0.5)
        return zs
    zs = []
    z = -0.5 + 0.002
    while z < 0.5 - 0.002:
        zs.append(z)
        near = min(abs(z - b) for b in bounds)
        z += 0.004 if near < 0.02 else 0.008
    zs.append(0.5 - 0.002)
    return zs


def shell(m, shape, low):
    m.part, m.index, m.root, m.a = SHELL, 0, None, 0.0
    across, under = pick(low, (28, 8), (6, 2), (8, 2))
    zs = ring_places(shape, low)
    rings = [shape.ring(z, across, under) for z in zs]
    mid_y = shape.venter + shape.rim * 0.4
    first, last = zs[0] * shape.L, zs[-1] * shape.L

    def out(middle):
        # (away from a line along it just above the bottom of its rim; at its ends, away from that line's end)
        end = min(middle.z - first, 0.0) + max(middle.z - last, 0.0)
        return Vector((middle.x, middle.y - mid_y, end))

    loft(m, rings, "shell", cap0=Vector((0.0, shape.venter + shape.rim * 0.6, -0.5 * shape.L)),
         cap1=Vector((0.0, shape.venter + shape.rim * 0.6, 0.5 * shape.L)), out=out)


def leg(m, index, root, heading, reach, knee_high, radius, sides, low):
    """A walking leg, in the upright plane through `root` that looks along `heading` (degrees from straight
    out to its side, towards its tail): out to its knee, KNEE_AT of the way out, then down to its tip on the
    ground `reach` out. The shader works the leg out again from the joint and the knee alone."""
    root = Vector(root)
    side = 1.0 if root.x >= 0.0 else -1.0
    angle = math.radians(heading)
    d = Vector((side * math.cos(angle), 0.0, math.sin(angle)))
    knee = root + d * (KNEE_AT * reach)
    knee.y = knee_high
    tip = root + d * reach
    tip.y = 0.0
    bend = knee.lerp(tip, 0.5)
    m.part, m.index, m.root, m.k = LEG, index, root, knee
    m.a = 0.0
    if low:
        tube(m, [root, knee], [radius, radius * 0.95], sides, "legs", caps=(False, low != "game"))
    else:
        tube(m, [root, root.lerp(knee, 0.5), knee], [radius * 0.95, radius * 1.1, radius * 0.95], sides, "legs")
    m.a = 1.0
    if low:
        tube(m, [knee, tip], [radius * 0.85, radius * 0.25], sides, "legs", caps=(True, False))
    else:
        tube(m, [knee, knee.lerp(bend, 0.5), bend, bend.lerp(tip, 0.5), tip],
             [radius * 0.9, radius * 0.9, radius * 0.7, radius * 0.5, radius * 0.2], sides, "legs")
    m.a = 0.0
    return knee, d


def legs(m, shape, low):
    L = shape.L
    count = shape.k["legs"]
    first = shape.head_back - 0.16
    last = shape.tail_front + 0.06
    for i in range(count):
        zu = first + (last - first) * i / (count - 1)
        heading = -38.0 + 76.0 * i / (count - 1)
        for sx in (1.0, -1.0):
            root = Vector((sx * 0.07 * L, shape.venter, zu * L))
            out = shape.half_width(zu) * 0.88 - 0.07 * L
            reach = out / max(math.cos(math.radians(heading)), 0.5)
            knee, d = leg(m, i, root, heading, reach, shape.venter * 0.8, 0.012 * L, pick(low, 6, 3, 3), low)
            # its gill: a feathery blade lying back from the leg's root, just under the shell
            m.part, m.index, m.root, m.k = GILL, i, root, knee
            back = Vector((0.0, 0.0, 1.0))
            way = (d + back * 0.55).normalized()
            across = Vector((way.z, 0.0, -way.x)) * sx
            long = reach * 0.85
            wide = 0.075 * L

            def point(t, u, root=root, way=way, across=across, long=long, wide=wide):
                w = wide * math.sin(math.pi * min(1.0, 0.15 + 0.85 * t)) ** 0.5 + 0.001 * L
                return Vector((root.x, shape.venter * 0.93, root.z)) + way * (long * t) + across * (w * (u - 0.5))

            blade(m, "gills", point, UP, 0.006 * L, pick(low, [j / 6 for j in range(7)], [0.0, 1.0], [0.0, 1.0]),
                  pick(low, 3, 1, 1), tags=lambda t, u: (None, t))
    m.root = None
    m.k = Vector((0.0, 0.0, 0.0))
    m.a = 0.0
    m.index = 0


def eyes(m, shape, low):
    (ex, ez), radii, gaze = shape.k["eye"]
    L = shape.L
    for sx in (1.0, -1.0):
        x = sx * ex * L
        centre = Vector((x, shape.top(x, ez) - radii[1] * L * 0.25, ez * L))
        m.part, m.index, m.root, m.a = EYE, 0, centre, 1.0
        dome(m, centre, [r * L for r in radii], (sx * gaze[0], gaze[1], gaze[2]), "eyes", pick(low, 10, 2, 3), pick(low, 32, 8, 24))
    m.root = None
    m.a = 0.0


def antennae(m, shape, low):
    L = shape.L
    v = shape.venter
    for sx in (1.0, -1.0):
        guide = [Vector((sx * 0.05 * L, v + 0.012 * L, -0.42 * L)), Vector((sx * 0.08 * L, v + 0.004 * L, -0.53 * L)),
                 Vector((sx * 0.15 * L, v + 0.01 * L, -0.66 * L)), Vector((sx * 0.25 * L, v + 0.03 * L, -0.76 * L)),
                 Vector((sx * 0.33 * L, v + 0.04 * L, -0.8 * L))]
        ts = pick(low, [i / 30 for i in range(31)], [0.0, 0.4, 1.0], [0.0, 0.3, 0.6, 1.0])
        path = [through(guide, t) for t in ts]
        m.part, m.index, m.root = ANTENNA, 0, guide[0]
        tube(m, path, [0.009 * L * (1.0 - 0.7 * t) for t in ts], pick(low, 6, 3, 3), "antennae", along=(0.0, 1.0), caps=(False, True))
    m.root = None
    m.a = 0.0


def through(points, t):
    """A smooth curve through `points` (Catmull-Rom), t 0 at the first to 1 at the last."""
    count = len(points) - 1
    f = min(max(t, 0.0), 1.0) * count
    i = min(int(f), count - 1)
    s = f - i
    p0 = points[max(i - 1, 0)]
    p1 = points[i]
    p2 = points[i + 1]
    p3 = points[min(i + 2, count)]
    return 0.5 * ((2 * p1) + (-p0 + p2) * s + (2 * p0 - 5 * p1 + 4 * p2 - p3) * s * s + (-p0 + 3 * p1 - 3 * p2 + p3) * s * s * s)


def spine(m, low, kind, guide, radius, sides, steps):
    """A spine along the curve through `guide` (its foot first), tapering to a point."""
    ts = [i / steps for i in range(steps + 1)]
    path = [through(guide, t) for t in ts]
    m.part, m.index, m.root = SPINE, kind, guide[0]
    tube(m, path, [radius * (1.0 - 0.9 * t) ** 0.9 + radius * 0.04 for t in ts], sides, "spines", along=(0.0, 1.0), caps=(False, not low))
    m.root = None


def spines(m, shape, kind, low):
    L = shape.L
    rim = shape.venter + shape.rim * 0.5
    sides = pick(low, 8, 3, 4)
    steps = pick(low, 10, 2, 4)
    if kind == "smooth":
        return
    for sx in (1.0, -1.0):
        if kind == "spiny":
            zb = shape.head_back
            w = shape.half_width(zb - 0.005)
            spine(m, low, GENAL, [Vector((sx * w * 0.92, rim, (zb - 0.03) * L)), Vector((sx * (w + 0.08 * L), rim - 0.005 * L, (zb + 0.12) * L)),
                                  Vector((sx * (w + 0.13 * L), rim - 0.02 * L, (zb + 0.35) * L)), Vector((sx * (w + 0.15 * L), rim - 0.03 * L, (zb + 0.5) * L))],
                  0.03 * L, sides, steps)
            for i in range(shape.n):
                zu = shape.head_back + (i + 0.6) * shape.seg
                w = shape.half_width(zu)
                lean = 0.15 + 0.3 * i / shape.n
                spine(m, low, PLEURAL, [Vector((sx * w * 0.85, rim, zu * L)), Vector((sx * (w + 0.1 * L), rim - 0.01 * L, (zu + 0.05 + lean * 0.15) * L)),
                                        Vector((sx * (w + 0.26 * L), rim - 0.04 * L, (zu + 0.08 + lean * 0.45) * L))],
                      0.016 * L, pick(low, 6, 3, 3), pick(low, 6, 1, 2))
            # two long spines behind the tail shield
            spine(m, low, TAIL, [Vector((sx * 0.06 * L, rim, 0.44 * L)), Vector((sx * 0.1 * L, rim - 0.01 * L, 0.6 * L)),
                                 Vector((sx * 0.13 * L, rim - 0.02 * L, 0.8 * L))], 0.022 * L, sides, pick(low, 8, 1, 3))
        else:
            # the long cheek spines, sweeping back along the body
            zb = shape.head_back
            w = shape.half_width(zb - 0.01)
            spine(m, low, GENAL, [Vector((sx * w * 0.9, rim, (zb - 0.06) * L)), Vector((sx * (w + 0.015 * L), rim, (zb + 0.08) * L)),
                                  Vector((sx * (w + 0.04 * L), rim - 0.008 * L, (zb + 0.3) * L)), Vector((sx * (w + 0.07 * L), rim - 0.015 * L, (zb + 0.55) * L))],
                  0.035 * L, sides, pick(low, 12, 2, 5))
            # the third segment's long spines
            zu = shape.head_back + 2.7 * shape.seg
            w = shape.half_width(zu)
            spine(m, low, MACRO, [Vector((sx * w * 0.85, rim, zu * L)), Vector((sx * (w + 0.06 * L), rim - 0.005 * L, (zu + 0.08) * L)),
                                  Vector((sx * (w + 0.1 * L), rim - 0.01 * L, (zu + 0.3) * L))], 0.022 * L, pick(low, 6, 3, 3), pick(low, 8, 1, 3))
            # each of the other segments ends in a short straight point, out and back
            for i in range(shape.n):
                if i == 2:
                    continue
                zu = shape.head_back + (i + 0.55) * shape.seg
                w = shape.half_width(zu)
                spine(m, low, PLEURAL, [Vector((sx * w * 0.9, rim, zu * L)), Vector((sx * (w + 0.055 * L), rim - 0.006 * L, (zu + 0.06 + 0.006 * i) * L))],
                      0.014 * L, pick(low, 6, 3, 3), pick(low, 3, 1, 1))
    if kind == "spiny":
        # a row of short spines up its back, one on each body segment
        for i in range(shape.n):
            zu = shape.head_back + (i + 0.5) * shape.seg
            top = shape.top(0.0, zu)
            spine(m, low, AXIAL, [Vector((0.0, top - 0.01 * L, zu * L)), Vector((0.0, top + 0.06 * L, (zu + 0.05) * L))],
                  0.012 * L, pick(low, 6, 3, 3), pick(low, 3, 1, 1))
    elif kind == "cheeks":
        # a long spine back from its last segment
        zu = shape.tail_front - 0.5 * shape.seg
        top = shape.top(0.0, zu)
        spine(m, low, AXIAL, [Vector((0.0, top - 0.008 * L, zu * L)), Vector((0.0, top + 0.01 * L, (zu + 0.1) * L)),
                              Vector((0.0, top + 0.015 * L, (zu + 0.28) * L))], 0.016 * L, pick(low, 6, 3, 3), pick(low, 6, 1, 2))


def make(kind, low):
    FAT[0] = game_fat if low == "game" else (lambda sides: 1.0)
    shape = Shape(kind)
    shape.grooves = not low
    BOX[0] = BOX_UNIT[0] * shape.L
    BOX[1] = BOX_UNIT[1] * shape.L
    m = Mesh()
    shell(m, shape, low)
    legs(m, shape, low)
    eyes(m, shape, low)
    antennae(m, shape, low)
    spines(m, shape, kind, low)
    return m


if __name__ == "__main__":
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    os.makedirs(OUT, exist_ok=True)
    made = []
    for n, kind in enumerate(KINDS):
        shape = Shape(kind)
        print("AS THE SHADER HAS IT: %s length %.3f venter %.4f (x length) head_back %.3f tail_front %.3f segments %d top %.4f eye %s"
              % (kind, shape.L, KINDS[kind]["venter"], shape.head_back, shape.tail_front, shape.n, shape.top(0.0, 0.0) / shape.L, KINDS[kind]["eye"]))
        for low, suffix in ((False, ""), (True, "_lo"), ("game", "_game")):
            name = "trilobite_%s%s" % (kind, suffix)
            obj = finish(name, make(kind, low), (0.55, 0.38, 0.24, 1.0))
            export_one(obj, os.path.join(OUT, name + ".glb"))
            made.append(obj)
    # (in the .blend: the kinds one behind the other, full in the middle, the low one to its left, the game one to
    # its right)
    for i, obj in enumerate(made):
        obj.location = Vector(((i % 3 - 1) * -0.5, (i // 3) * 0.6, 0.0))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "trilobite.blend"))
    for obj in made:
        obj.location = Vector((0.0, 0.0, 0.0))
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, made, 0.5, close=[("head", (-1, 0.6, -0.8), (0, 0.02, -0.04), 0.12), ("under", (0, -1, 0.001), (0, 0.0, 0.0), 0.36)])
