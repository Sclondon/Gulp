"""Builds the anomalocaris (creatures/anomalocaris) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/anomalocaris/tools/build_anomalocaris.py
    blender --background --python creatures/anomalocaris/tools/build_anomalocaris.py -- <preview folder>   # with pictures

Writes creatures/anomalocaris/models/anomalocaris.glb (the full model), anomalocaris_game.glb (the game model: few
triangles, spent where the eye looks: the outline of the body and its lobes, the eyes, the spiny arms) and
anomalocaris_lo.glb (far off, phones), and the editable creatures/anomalocaris/tools/anomalocaris.blend (all three;
this folder has a .gdignore). Each is one still mesh with one surface: the shader (anomalocaris.gdshader) draws every
marking, ripples its swimming lobes, sways its tail fan and reaches out and curls its arms (`grasp`). It prints a
WINDING line for each: the check that nothing is inside out.

An anomalocaris (Anomalocaris canadensis, of the Cambrian Burgess Shale), 0.8 m from the front of its head to the
tips of its tail fan, built from what the fossils and the usual reconstructions show (no picture was traced or
copied):

- THE BODY: a flattened head under a smooth oval plate, a neck, then a body of eleven segments, widest near the
  front and narrowing to the tail, each segment's edge a groove; a swimming lobe out of each side of every segment,
  broad and swept back, each overlapping the one behind; a fan of three pairs of long blades at the tail.
- TWO BIG COMPOUND EYES, oval, on short stalks out of the top of the head to each side.
- TWO GRASPING ARMS out of the front of the head beneath, each thirteen segments (a long first one, then shorter
  and thinner to the tip), each segment after the first with a pair of spines on its inner side, long and short by
  turns; at rest they are curled down and back under the head like fern heads.
- THE MOUTH beneath the head: a round cone of radial plates, four of them bigger, round a dark opening.

Everything here is in Godot space (metres, Y up, X to its left side, its head at -Z) until it is written out. THE
ORIGIN is on its middle line half way from the front of its head to the tips of its tail fan.

What a point is, for the shader: see `Mesh` below. The parts: 0 the body, 1 a lobe (`index` 0 the first to 10,
`root` the middle of its hinge, `a` 0 at its hinge to 1 at its tip), 2 a tail blade (`index` 0 the inner pair to 2,
`root` its root, `a` 0 at its root to 1 at its tip), 3 an eye (`a` 0 its stalk, 1 the eye; on the eye `root` its
middle), 4 an arm (`index` which segment, 0 the first; `a` 0 at the arm's root to 1 at its tip), 5 a spine of an arm
(`index` the segment it stands on; `a` 0 at its foot to 1 at its point), 6 the mouth (`a` 0 at its rim to 1 in its
opening).

The numbers marked "as the shader has it" are in anomalocaris.gdshader too: change one, change the other (the arm's
joints are printed as ARM_P and ARM_D lines to copy).
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
    """A thin closed blade (a lobe, a tail blade): `point(t, u)` is a place in the model (t 0 at its root
    to 1 at its tip, u 0 at its leading edge to 1 at its trailing edge), `facing` the way one of its two
    skins faces. It is `thick` at its root, a foil across (nothing at either edge), thinning towards its
    tip; its rows are at `ts`."""
    facing = Vector(facing).normalized()
    for side in (1.0, -1.0):
        grid = []
        for t in ts:
            row = []
            for ui in range(nu + 1):
                u = ui / nu
                foil = 2.6 * math.sqrt(u) * (1.0 - u)
                swell = thick * (1.0 - 0.7 * t) * foil
                p = point(t, u) + facing * (side * swell * 0.5)
                k, a = tags(t, u) if tags else (None, None)
                row.append(m.add(p, k, a))
            grid.append(row)
        for ti in range(len(ts) - 1):
            for ui in range(nu):
                m.face((grid[ti][ui], grid[ti][ui + 1], grid[ti + 1][ui + 1], grid[ti + 1][ui]), facing * side, name)


def oval(m, centre, radii, name, lat, lon, axis):
    """An ellipsoid with the half widths `radii` along X, Y and Z, its mesh's poles along `axis` (so that its
    rings go round that way: an eye's rings round where it looks)."""
    centre = Vector(centre)
    ez = Vector(axis).normalized()
    ex = (UP if abs(ez.y) < 0.9 else Vector((1.0, 0.0, 0.0))).cross(ez).normalized()
    ey = ez.cross(ex)
    rings = []
    for i in range(1, lat):
        th = math.pi * i / lat
        ring = []
        for j in range(lon):
            d = ex * (math.sin(th) * math.cos(TAU * j / lon)) + ey * (math.sin(th) * math.sin(TAU * j / lon)) - ez * math.cos(th)
            ring.append(centre + Vector((d.x * radii[0], d.y * radii[1], d.z * radii[2])))
        rings.append(ring)
    loft(m, rings, name, cap0=centre - Vector((ez.x * radii[0], ez.y * radii[1], ez.z * radii[2])),
         cap1=centre + Vector((ez.x * radii[0], ez.y * radii[1], ez.z * radii[2])), out=lambda middle: middle - centre)


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


BODY, LOBE, TAIL, EYE, ARM, SPINE, MOUTH = range(7)
# As the shader has it: the box the joints are written in.
BOX = (Vector((-0.25, -0.2, -0.45)), Vector((0.25, 0.2, 0.45)))

# The body's outline along it: z, the middle line's height, half its depth above that, below it, half its width,
# and how square its section is (2 an ellipse).
PROFILE = [
    (-0.384, 0.000, 0.002, 0.002, 0.004, 2.0),
    (-0.378, 0.000, 0.012, 0.010, 0.024, 2.2),
    (-0.366, 0.001, 0.020, 0.017, 0.040, 2.4),
    (-0.345, 0.002, 0.027, 0.022, 0.054, 2.6),
    (-0.310, 0.002, 0.031, 0.026, 0.062, 2.7),
    (-0.270, 0.002, 0.031, 0.026, 0.061, 2.7),
    (-0.240, 0.001, 0.028, 0.024, 0.055, 2.7),
    (-0.228, 0.000, 0.026, 0.023, 0.051, 2.7),
    (-0.200, 0.000, 0.028, 0.025, 0.058, 2.7),
    (-0.130, 0.000, 0.030, 0.026, 0.064, 2.7),
    (-0.040, 0.000, 0.027, 0.024, 0.058, 2.7),
    (0.060, 0.000, 0.023, 0.021, 0.047, 2.6),
    (0.160, 0.000, 0.018, 0.016, 0.033, 2.5),
    (0.230, 0.000, 0.013, 0.012, 0.022, 2.3),
    (0.262, 0.000, 0.008, 0.008, 0.012, 2.1),
    (0.270, 0.000, 0.003, 0.003, 0.004, 2.0),
]
BODY_FROM, BODY_TO = PROFILE[0][0], PROFILE[-1][0]
# As the shader has it: the neck, then where each of the eleven segments begins (and the last ends).
NECK = -0.228
SEGMENTS = tuple(-0.215 + i * 0.043 for i in range(12))
# How far out each segment's lobe reaches beyond the body's edge (m).
LOBE_OUT = (0.07, 0.085, 0.093, 0.094, 0.09, 0.083, 0.075, 0.065, 0.055, 0.045, 0.035)

_XS = [p[0] for p in PROFILE]
_CURVES = []
for _column in range(1, 6):
    _ys = [p[_column] for p in PROFILE]
    _CURVES.append((_ys, _slopes(_XS, _ys)))


def profile(z):
    z = max(_XS[0], min(_XS[-1], z))
    i = 0
    while i < len(_XS) - 2 and z > _XS[i + 1]:
        i += 1
    h = _XS[i + 1] - _XS[i]
    t = (z - _XS[i]) / h
    out = []
    for ys, s in _CURVES:
        a = (2 * t ** 3 - 3 * t ** 2 + 1) * ys[i] + (t ** 3 - 2 * t ** 2 + t) * h * s[i]
        b = (-2 * t ** 3 + 3 * t ** 2) * ys[i + 1] + (t ** 3 - t ** 2) * h * s[i + 1]
        out.append(a + b)
    return out


def section(z):
    cy, up, down, wide, power = profile(z)
    # each groove (the neck and the segments' edges): a narrow dip all round
    squeeze = 1.0
    for b in (NECK,) + SEGMENTS[:-1]:
        squeeze -= 0.06 * math.exp(-((z - b) / 0.003) ** 2)
    return cy, max(up * squeeze, 0.0005), max(down * squeeze, 0.0005), max(wide * squeeze, 0.0005), power


def body(m, low):
    m.part, m.index, m.root, m.a = BODY, 0, None, 0.0
    if low == "game":
        # rings where the outline turns (the head's front, the eyes' place, the neck, the tail) and half way
        # along each segment (its outline there is the full model's; the grooves are the shader's); twelve round
        zs = sorted(set([round(z, 5) for z in _XS + [-0.381, -0.372] + [(SEGMENTS[i] + SEGMENTS[i + 1]) * 0.5 for i in range(len(SEGMENTS) - 1)] if z != -0.24]
                        ))
        zs = [z for z in zs if BODY_FROM <= z <= BODY_TO and not (SEGMENTS[-1] - 0.03 < z < BODY_TO - 0.001 and z not in _XS)]
        section_loft(m, zs, section, 12, "body")
        return
    step = 0.024 if low else 0.0035
    zs = []
    z = BODY_FROM
    while z < BODY_TO - 1e-9:
        zs.append(z)
        near = min(abs(z - b) for b in (NECK,) + SEGMENTS)
        z += step * (0.5 if near < 0.006 and not low else 1.0)
    zs.append(BODY_TO)
    section_loft(m, zs, section, 8 if low else 36, "body")


def lobes(m, low):
    ts = pick(low, [i / 12 for i in range(13)], [0.0, 0.6, 1.0], [0.0, 0.3, 0.55, 0.75, 0.9, 1.0])
    nu = pick(low, 8, 1, 1)
    for i in range(len(SEGMENTS) - 1):
        za = SEGMENTS[i] + 0.003
        zb = SEGMENTS[i + 1] + 0.026
        zm = (za + zb) * 0.5
        out = LOBE_OUT[i]
        for sx in (1.0, -1.0):
            cy = profile(zm)[0]
            root = Vector((sx * profile(zm)[3] * 0.9, cy - 0.003, zm))
            m.part, m.index, m.root = LOBE, i, root

            def point(t, u, za=za, zb=zb, zm=zm, out=out, sx=sx, cy=cy):
                z0 = za + (zb - za) * u
                xr = profile(z0)[3] * 0.9
                chord = math.sqrt(max(1.0 - t ** 2.4, 0.0)) * (1.0 - 0.15 * t) + 0.02
                z = zm + 0.55 * out * t ** 1.3 + (z0 - zm) * chord
                x = xr + (profile(zm)[3] * 0.9 - xr) * t + out * t
                return Vector((sx * x, cy - 0.003 - 0.012 * t * t, z))

            blade(m, "lobes", point, Vector((0.0, 1.0, 0.0)), 0.004, ts, nu, tags=lambda t, u: (None, t))
    m.root = None
    m.a = 0.0
    m.index = 0


# The tail fan: each pair's angle out from straight back (degrees), its length and its width.
TAIL_BLADES = ((12.0, 0.15, 0.032), (31.0, 0.135, 0.03), (50.0, 0.115, 0.026))
TAIL_ROOT = Vector((0.006, 0.004, 0.252))


def tail(m, low):
    ts = pick(low, [i / 12 for i in range(13)], [0.0, 0.5, 1.0], [0.0, 0.15, 0.35, 0.6, 0.85, 1.0])
    nu = pick(low, 6, 1, 1)
    for k, (angle, long, wide) in enumerate(TAIL_BLADES):
        for sx in (1.0, -1.0):
            a = math.radians(angle)
            root = Vector((sx * TAIL_ROOT.x, TAIL_ROOT.y, TAIL_ROOT.z))
            way = Vector((sx * math.sin(a), 0.0, math.cos(a)))
            way = (way * math.cos(math.radians(14.0)) + UP * math.sin(math.radians(14.0))).normalized()
            across = UP.cross(way).normalized()
            facing = way.cross(across).normalized()
            m.part, m.index, m.root = TAIL, k, root

            def point(t, u, root=root, way=way, across=across, long=long, wide=wide):
                w = wide * math.sin(math.pi * min(1.0, 0.1 + 0.9 * t)) ** 0.6 * (1.0 - 0.25 * t) + 0.001
                return root + way * (long * t) + across * (w * (u - 0.5))

            blade(m, "tail", point, facing, 0.003, ts, nu, tags=lambda t, u: (None, t))
    m.root = None
    m.a = 0.0
    m.index = 0


# As the shader has it: the middle of the left eye, the way it looks; its half widths.
EYE_AT = Vector((0.098, 0.04, -0.282))
EYE_GAZE = Vector((1.0, 0.3, -0.55))
EYE_RADII = (0.022, 0.023, 0.032)


def eyes(m, low):
    for sx in (1.0, -1.0):
        m.part, m.index, m.root, m.a = EYE, 0, None, 0.0
        foot = Vector((sx * 0.03, 0.02, -0.276))
        head = Vector((sx * 0.08, 0.036, -0.28))
        tube(m, [foot, foot.lerp(head, 0.5) + Vector((0.0, 0.004, 0.0)), head], [0.009, 0.0075, 0.007], pick(low, 10, 4, 5), "eyes", caps=(False, False))
        centre = Vector((sx * EYE_AT.x, EYE_AT.y, EYE_AT.z))
        m.root, m.a = centre, 1.0
        oval(m, centre, EYE_RADII, "eyes", pick(low, 16, 4, 7), pick(low, 32, 8, 24), (sx * EYE_GAZE.x, EYE_GAZE.y, EYE_GAZE.z))
    m.root = None
    m.a = 0.0


# The arms (the left one; the right one mirrored): where it grows from, each segment's length and its radius at
# its start; at rest (`grasp` 0) the way its first segment points (degrees down from straight ahead) and how far
# each joint after it bends down; reaching out (`grasp` 1) the same.
ARM_BASE = Vector((0.028, -0.02, -0.352))
ARM_LENGTHS = (0.032, 0.022, 0.02, 0.0185, 0.017, 0.016, 0.015, 0.014, 0.013, 0.012, 0.011, 0.01, 0.009)
REST_START = 62.0
REST_BENDS = (32.0,) + (24.0,) * 11
REACH_START = 6.0
REACH_BENDS = (4.0, 2.0, 2.0, 2.0, 2.0, 2.0, 3.0, 4.0, 6.0, 10.0, 16.0, 22.0)


def arm_radius(i, f=0.0):
    n = len(ARM_LENGTHS)
    return 0.0115 * (1.0 - 0.7 * (i + f) / n) ** 1.1


def arm_chain(start, bends):
    """The arm's joints (y, z) and each segment's angle (degrees down from straight ahead)."""
    points = [Vector((0.0, ARM_BASE.y, ARM_BASE.z))]
    angles = []
    angle = start
    for i, long in enumerate(ARM_LENGTHS):
        if i > 0:
            angle += bends[i - 1]
        angles.append(angle)
        a = math.radians(angle)
        points.append(points[-1] + Vector((0.0, -math.sin(a), -math.cos(a))) * long)
    return points, angles


def arms(m, low):
    points, angles = arm_chain(REST_START, REST_BENDS)
    n = len(ARM_LENGTHS)
    fractions = pick(low, (0.25, 0.5, 0.75), (0.5,), (0.5,))
    sides = pick(low, 12, 4, 5)
    spine_sides = pick(low, 6, 3, 3)
    for sx in (1.0, -1.0):
        x = sx * ARM_BASE.x
        # one tube along the whole arm: rings in each segment (its own), and a narrower ring at each joint (it
        # goes with the segment inside it)
        path = []
        radii = []
        owner = []
        for i in range(n):
            p0 = points[i]
            p1 = points[i + 1]
            if i > 0:
                path.append(p0)
                radii.append(arm_radius(i) * 0.86)
                owner.append(i - 1)
            for f in (fractions if i > 0 or low != "game" else (0.25, 0.75)):
                path.append(p0.lerp(p1, f))
                radii.append(arm_radius(i, f) * (1.0 + 0.06 * math.sin(math.pi * f)))
                owner.append(i)
        path = [Vector((x, p.y, p.z)) for p in path]
        total = sum(ARM_LENGTHS)
        lengths = [0.0]
        for i in range(1, len(path)):
            lengths.append(lengths[-1] + (path[i] - path[i - 1]).length)
        made = frames(path, Vector((1.0, 0.0, 0.0)))
        rings = []
        for (t, u, v), p, r in zip(made, path, radii):
            r *= FAT[0](sides)
            rings.append([p + (u * math.cos(TAU * s / sides) + v * math.sin(TAU * s / sides)) * r for s in range(sides)])
        m.part, m.root = ARM, None

        def tags(p, ri, ci, owner=owner, lengths=lengths):
            m.index = owner[ri]
            return None, lengths[ri] / lengths[-1]

        loft(m, rings, "arms", cap0=path[0] + (path[0] - path[1]).normalized() * radii[0] * 0.4,
             cap1=path[-1] + (path[-1] - path[-2]).normalized() * radii[-1] * 0.8, tags=tags)
        # the spines: a pair on the inner side of every segment after the first, long and short by turns
        m.part = SPINE
        for i in range(1, n):
            a = math.radians(angles[i])
            d = Vector((0.0, -math.sin(a), -math.cos(a)))
            inner = Vector((0.0, -math.cos(a), math.sin(a)))
            long = (0.03 if i % 2 == 1 else 0.014) * (1.0 - i / 17.0)
            r = arm_radius(i, 0.6)
            m.index = i
            for spread in (1.0, -1.0):
                foot = Vector((x, 0.0, 0.0)) + points[i].lerp(points[i + 1], 0.6) + inner * (r * 0.6) + Vector((spread * r * 0.45, 0.0, 0.0))
                way = (inner * math.cos(math.radians(28.0)) + d * math.sin(math.radians(28.0)) + Vector((spread * 0.3, 0.0, 0.0))).normalized()
                tip = foot + way * long
                tube(m, [foot, foot.lerp(tip, 0.5), tip] if not low else [foot, tip],
                     [r * 0.32, r * 0.17, 0.0003] if not low else [r * 0.3, 0.0003], spine_sides, "spines", along=(0.0, 1.0), caps=(False, False))
    m.root = None
    m.a = 0.0
    m.index = 0
    # the numbers the shader needs: each joint's place (y, z) at rest, and how far it turns about +X from rest to
    # reaching out (radians; + lifts the arm)
    reach, _ = arm_chain(REACH_START, REACH_BENDS)
    turns = [-(REACH_START - REST_START)] + [-(REACH_BENDS[i] - REST_BENDS[i]) for i in range(n - 1)]
    print("ARM_P " + ", ".join("vec2(%.5f, %.5f)" % (p.y, p.z) for p in points[:n]))
    print("ARM_D " + ", ".join("%.5f" % math.radians(t) for t in turns))
    print("ARM reach: tip at rest (%.3f, %.3f), reaching out (%.3f, %.3f)" % (points[-1].y, points[-1].z, reach[-1].y, reach[-1].z))


MOUTH_AT = Vector((0.0, -0.0255, -0.300))


def mouth(m, low):
    """A round cone of radial plates under the head, round a dark opening."""
    m.part, m.index, m.root = MOUTH, 0, None
    around = pick(low, 64, 8, 16)
    rings = []
    rows = pick(low, ((0.031, 0.002, 0.0), (0.028, -0.004, 0.25), (0.022, -0.0075, 0.5), (0.014, -0.009, 0.7), (0.0075, -0.006, 0.9)),
                ((0.031, 0.002, 0.0), (0.02, -0.007, 0.5), (0.0075, -0.006, 0.9)),
                ((0.031, 0.002, 0.0), (0.026, -0.0055, 0.3), (0.016, -0.0088, 0.6), (0.0075, -0.006, 0.9)))
    alongs = []
    for r, dy, a in rows:
        ring = []
        for c in range(around):
            phi = TAU * c / around
            ridge = 0.0
            if not low:
                # (the plates: 32 ridges, the four big ones higher)
                ridge = -0.0012 * math.cos(16.0 * phi) ** 2 - 0.0016 * max(math.cos(2.0 * phi) ** 2 - 0.85, 0.0) / 0.15
            ring.append(MOUTH_AT + Vector((r * math.sin(phi), dy + ridge * (1.0 if 0.0 < a < 0.9 else 0.0), r * math.cos(phi))))
        rings.append(ring)
        alongs.append(a)
    m.a = 0.0
    loft(m, rings, "mouth", cap1=MOUTH_AT + Vector((0.0, 0.004, 0.0)), tags=lambda p, ri, ci: (None, alongs[ri] if ri < len(alongs) and ci >= 0 else 1.0),
         out=lambda middle: Vector((0.0, -1.0, 0.0)))
    m.a = 0.0


def make(low):
    FAT[0] = game_fat if low == "game" else (lambda sides: 1.0)
    m = Mesh()
    body(m, low)
    lobes(m, low)
    tail(m, low)
    eyes(m, low)
    arms(m, low)
    mouth(m, low)
    return m


if __name__ == "__main__":
    build_all("anomalocaris", make, (0.55, 0.28, 0.2, 1.0), 0.95,
              close=[("head", (-1, 0.5, -0.8), (0, 0, -0.3), 0.3), ("under", (0, -1, 0.001), (0, -0.03, -0.3), 0.3),
                     ("side", (-1, 0, 0), (0, -0.02, -0.3), 0.3)])
