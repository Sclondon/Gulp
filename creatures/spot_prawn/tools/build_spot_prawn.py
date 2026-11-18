"""Builds the spot prawn (creatures/spot_prawn) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/spot_prawn/tools/build_spot_prawn.py
    blender --background --python creatures/spot_prawn/tools/build_spot_prawn.py -- <preview folder>   # with pictures

Writes creatures/spot_prawn/models/spot_prawn.glb (the full model), spot_prawn_game.glb (the game model: few
triangles, spent where the eye looks: the outline, the eyes, the rostrum's teeth) and spot_prawn_lo.glb (far off,
phones), and the editable creatures/spot_prawn/tools/spot_prawn.blend (all three; this folder has a .gdignore).
The full and the low model come out as they did before the game model was added. Each is one still mesh
with one surface: the shader (spot_prawn.gdshader) draws every marking, walks its legs, beats its swimmerets
and curls its tail under (`flick`). It prints a WINDING line for each: the check that nothing is inside out.

A spot prawn (Pandalus platyceros), 0.2 m from the tip of its rostrum to the tip of its tail fan, built from the
species (no picture was traced or copied):

- THE BODY: a carapace a little flattened from side to side, 0.052 m long, its front running up into a long thin
  rostrum (as long as the carapace, toothed along its top for most of its length and beneath near its tip,
  turned a little up at the end); an abdomen of six segments twice as long, humped at the third, each segment's
  rear edge a groove, then a narrow pointed telson between two pairs of paddles: the tail fan.
- Two black eyes on short stalks under the base of the rostrum; two very long thin antennae (about one and
  three quarter times the body) that go forward and then sweep out and back past the tail; two short antennules;
  the flat antennal scales; a pair of leg-like mouthparts reaching forward under the head.
- TEN WALKING LEGS, five a side, long and thin: out and up to a knee, then down to a point on the ground.
- FIVE PAIRS OF SWIMMERETS hanging under the first five segments of the abdomen, flat paddles that beat.

Everything here is in Godot space (metres, Y up, X to its left side, its head at -Z) until it is written out.
THE ORIGIN IS ON THE GROUND under the middle of the body (half way from the rostrum's tip to the tail's): its feet
stand at y 0.

What a point is, for the shader: see `Mesh` below. The parts: 0 the body (the carapace and the abdomen), 1 a
walking leg (`index` which, 0 the first; `root` its joint with the body, `k` its knee, `a` 0 above the knee and 1
below it), 2 a swimmeret (`index` which, 0 the first; `root` where it hangs from; `a` 0 at its root to 1 at its
end), 3 an eye (`a` 0 its stalk, 1 the eye), 4 an antenna (`index` 0 the long antenna, 1 an antennule; `root` its
base; `a` 0 at its base to 1 at its tip), 5 an antennal scale, 6 the tail fan (`index` 0 the telson, 1 an inner
paddle, 2 an outer one; `a` 0 at its root to 1 at its tip), 7 the rostrum (`a` the same), 8 a mouthpart.

The numbers marked "as the shader has it" are in spot_prawn.gdshader too: change one, change the other.
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


def spine(m, base, tip, radius, sides, name):
    """A cone standing on the skin (its foot is sunk in it, so it has no floor)."""
    base = Vector(base)
    tip = Vector(tip)
    t, u, v = frames([base, tip])[0]
    ring = [base + (u * math.cos(TAU * s / sides) + v * math.sin(TAU * s / sides)) * radius for s in range(sides)]
    middle = (base + tip) * 0.5
    loft(m, [ring], name, cap1=tip, out=lambda at: (at - middle) - t * (at - middle).dot(t) + t * radius * 0.2)


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
    if low:
        # (the game model: no cap at the knee on the upper length, the lower one's cap closes it)
        tube(m, [root, knee], [radius, radius * 0.95], sides, name, caps=(False, low != "game"))
    else:
        tube(m, [root, root.lerp(knee, 0.5), knee], [radius * 0.95, radius * 1.12, radius * 0.95], sides, name)
    m.a = 1.0
    if low:
        tube(m, [knee, bend, tip], [radius * 0.9, radius * 0.7, radius * 0.2], sides, name, caps=(True, False))
    else:
        tube(m, [knee, knee.lerp(bend, 0.5), bend, bend.lerp(tip, 0.5), tip],
             [radius * 0.9, radius * 0.95, radius * 0.72, radius * 0.55, radius * 0.2], sides, name)
    m.root = None
    m.a = 0.0
    m.index = 0
    return knee, tip


def blade(m, name, point, facing, thick, nt, nu, tags=None, ts=None):
    """A thin closed blade (a fin, a tail fan's paddle, a swimmeret): `point(t, u)` is a place in the
    model (t 0 at its root to 1 at its tip, u 0 at its leading edge to 1 at its trailing edge),
    `facing` the way one of its two skins faces. It is `thick` at its root, a foil across (nothing at
    either edge), thinning towards its tip. `tags(t, u)` gives a point's (k, a). `ts`, if given, are
    the places along it of its rows (instead of `nt` even steps)."""
    facing = Vector(facing).normalized()
    if ts:
        nt = len(ts) - 1
    for side in (1.0, -1.0):
        grid = []
        for ti in range(nt + 1):
            t = ts[ti] if ts else ti / nt
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

BODY, LEG, SWIM, EYE, ANTENNA, SCALE, FAN, ROSTRUM, MOUTH = range(9)
# As the shader has it: the box the joints' places are written in; how far out along a leg its knee is.
BOX = (Vector((-0.03, 0.0, -0.1)), Vector((0.03, 0.06, 0.1)))
KNEE_AT = 0.45

# The body's outline along it: z, the middle line's height, half its depth above that, below it, half its
# width, and how square its section is (2 an ellipse).
PROFILE = [
    (-0.0605, 0.0335, 0.0010, 0.0010, 0.0010, 2.0),
    (-0.0590, 0.0330, 0.0055, 0.0060, 0.0045, 2.0),
    (-0.0560, 0.0322, 0.0100, 0.0100, 0.0072, 2.1),
    (-0.0500, 0.0315, 0.0132, 0.0125, 0.0088, 2.2),
    (-0.0400, 0.0310, 0.0148, 0.0138, 0.0096, 2.2),
    (-0.0250, 0.0312, 0.0152, 0.0140, 0.0098, 2.2),
    (-0.0120, 0.0316, 0.0146, 0.0132, 0.0095, 2.3),
    (-0.0060, 0.0318, 0.0138, 0.0122, 0.0090, 2.4),
    (0.0000, 0.0322, 0.0130, 0.0118, 0.0084, 2.8),
    (0.0120, 0.0335, 0.0124, 0.0113, 0.0078, 2.8),
    (0.0250, 0.0348, 0.0116, 0.0106, 0.0071, 2.8),
    (0.0360, 0.0336, 0.0102, 0.0096, 0.0063, 2.7),
    (0.0460, 0.0300, 0.0086, 0.0082, 0.0055, 2.5),
    (0.0580, 0.0262, 0.0068, 0.0064, 0.0045, 2.3),
    (0.0700, 0.0240, 0.0050, 0.0046, 0.0035, 2.2),
    (0.0745, 0.0236, 0.0026, 0.0026, 0.0022, 2.0),
]
BODY_FROM, BODY_TO = PROFILE[0][0], PROFILE[-1][0]
# As the shader has it: where the carapace ends and each segment of the abdomen begins.
SEGMENTS = (-0.006, 0.007, 0.020, 0.033, 0.046, 0.058)


def _slopes(xs, ys):
    """Tangents for a curve through the points that never overshoots them (Fritsch and Carlson)."""
    d = [(ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]) for i in range(len(xs) - 1)]
    m = [d[0]]
    for i in range(1, len(xs) - 1):
        if d[i - 1] * d[i] <= 0.0:
            m.append(0.0)
        else:
            w1 = 2.0 * (xs[i + 1] - xs[i]) + (xs[i] - xs[i - 1])
            w2 = (xs[i + 1] - xs[i]) + 2.0 * (xs[i] - xs[i - 1])
            m.append((w1 + w2) / (w1 / d[i - 1] + w2 / d[i]))
    m.append(d[-1])
    return m


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
    for ys, m in _CURVES:
        a = (2 * t ** 3 - 3 * t ** 2 + 1) * ys[i] + (t ** 3 - 2 * t ** 2 + t) * h * m[i]
        b = (-2 * t ** 3 + 3 * t ** 2) * ys[i + 1] + (t ** 3 - t ** 2) * h * m[i + 1]
        out.append(a + b)
    return out


def section(z):
    cy, up, down, wide, power = profile(z)
    # each segment's rear edge: a groove, the segment behind starting a little smaller
    squeeze = 1.0
    for b in SEGMENTS:
        squeeze -= 0.07 * math.exp(-((z - b) / 0.0011) ** 2)
        if b > SEGMENTS[0]:
            squeeze -= 0.025 * smooth(b - 0.0004, b + 0.0004, z) * (1.0 - smooth(b, b + 0.006, z))
    return cy, max(up * squeeze, 0.0003), max(down * squeeze, 0.0003), max(wide * squeeze, 0.0003), power


def game_rings(knots, grooves, gap, fine=0.0):
    """Where the game model's rings go along the body: at every knot of its outline (where its curve
    turns), either side of and at each groove (`fine` out from it), and nowhere further apart than
    `gap`; two closer than a tenth of `gap` are one."""
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


def body(m, low):
    m.part, m.index, m.root, m.a = BODY, 0, None, 0.0
    if low == "game":
        # rings where the outline turns (the head's taper, the hump, the tail's end) and at each groove,
        # few along the smooth plates; twelve round, the ridge, the keel and the widest on points
        zs = game_rings(_XS, SEGMENTS, 0.008)
        section_loft(m, zs, section, 12, "body")
        return
    step = 0.004 if low else 0.0015
    zs = []
    z = BODY_FROM
    while z < BODY_TO - 1e-9:
        zs.append(z)
        # (finer at the grooves)
        near = min(abs(z - b) for b in SEGMENTS)
        z += step * (0.6 if near < 0.003 and not low else 1.0)
    zs.append(BODY_TO)
    section_loft(m, zs, section, 10 if low else 28, "body")


def rostrum(m, low):
    """A thin upright blade from the top of the carapace's front, toothed along its top."""
    root = Vector((0.0, 0.0425, -0.050))
    tip_z = -0.100
    nt = 8 if low else 48
    # the teeth along its top and beneath: how many to its length (the game model's are fewer, as big)
    top_teeth, under_teeth = pick(low, (16.0, 22.0), (0.0, 0.0), (7.0, 9.0))
    ts = None
    if low == "game":
        # a row at the foot, the point and the shoulder of every tooth, and a few more towards the tip
        ts = set([0.0, 0.72, 0.8, 1.0])
        for n, start, end in ((top_teeth, 0.0, 0.74), (under_teeth, 0.6, 0.96)):
            i = math.floor(start * n)
            while i / n < end:
                for f in (0.0, 0.08):
                    t = (i + f) / n
                    if start <= t <= end:
                        ts.add(round(t, 5))
                i += 1
        ts = sorted(ts)

    def point(t, u):
        z = root.z + (tip_z - root.z) * t
        # its upper edge: dipping a little, then turned up at the end
        top = root.y + 0.001 - 0.006 * math.sin(math.pi * 0.8 * t) + 0.0045 * t ** 3
        high = 0.0055 * (1.0 - t) ** 0.8 + 0.0004
        if low is not True:
            # the teeth: a row along its top for most of its length, a few beneath near its tip
            f = (t * top_teeth) % 1.0
            top += 0.0011 * (1.0 - f) ** 2 * smooth(0.0, 0.08, f) * (1.0 - smooth(0.6, 0.75, t))
            g = (t * under_teeth) % 1.0
            high += 0.0008 * (1.0 - g) ** 2 * smooth(0.0, 0.1, g) * smooth(0.62, 0.7, t) * (1.0 - smooth(0.9, 0.96, t)) * (1.0 if u > 0.5 else 0.0)
        return Vector((0.0, top - high * u, z))

    m.part, m.index, m.root = ROSTRUM, 0, None
    blade(m, "rostrum", point, Vector((1.0, 0.0, 0.0)), 0.0013, nt, pick(low, 4, 2, 2), tags=lambda t, u: (None, t), ts=ts)
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


def eyes(m, low):
    for sx in (1.0, -1.0):
        foot = Vector((sx * 0.004, 0.0365, -0.0555))
        head = Vector((sx * 0.0085, 0.0375, -0.0615))
        m.part, m.index, m.root, m.a = EYE, 0, None, 0.0
        tube(m, [foot, head], [0.0022, 0.0021], pick(low, 10, 4, 4), "eyes", caps=(False, False))
        m.a = 1.0
        ball(m, head + Vector((sx * 0.0008, 0.0, -0.0008)), 0.0034, 0.0034, 0.0034, "eyes", lat=pick(low, 8, 3, 6), lon=pick(low, 12, 5, 14))
    m.a = 0.0


def feelers(m, low):
    """The long antennae, the antennules, the antennal scales and the mouthparts."""
    for sx in (1.0, -1.0):
        def v(x, y, z):
            return Vector((sx * x, y, z))
        # the long antenna: forward and out, then sweeping out and back past the tail
        base = v(0.0045, 0.028, -0.059)
        guide = [base, v(0.010, 0.032, -0.085), v(0.028, 0.040, -0.095), v(0.048, 0.042, -0.070), v(0.062, 0.038, 0.000), v(0.072, 0.032, 0.100), v(0.078, 0.028, 0.200)]
        steps = pick(low, 70, 10, 12)
        # (the game model: its points close together round the bend at its front, few along its long sweep back)
        ts = pick(low, None, None, (0.0, 0.06, 0.12, 0.18, 0.24, 0.3, 0.36, 0.43, 0.5, 0.62, 0.75, 0.87, 1.0))
        ts = ts or [i / steps for i in range(steps + 1)]
        path = [through(guide, t) for t in ts]
        m.part, m.index, m.root = ANTENNA, 0, base
        radii = [0.0009 * (1.0 - 0.75 * t) for t in ts] if low == "game" else [0.0009 * (1.0 - 0.75 * i / steps) for i in range(steps + 1)]
        tube(m, path, radii, pick(low, 5, 3, 3), "antennae", along=(0.0, 1.0), caps=(False, True))
        # the antennule: a short stalk forward, then two short whips
        base = v(0.0025, 0.0335, -0.058)
        m.index, m.root = 1, base
        stalk = [base, v(0.004, 0.035, -0.072), v(0.0055, 0.036, -0.08)]
        tube(m, stalk, [0.0011, 0.0009, 0.0007], pick(low, 6, 3, 3), "antennae", along=(0.0, 0.3))
        if low is not True:
            n = pick(low, 12, 0, 1)
            for lean, rise in ((1.0, 0.004), (0.4, -0.002)):
                whip = [bezier([stalk[-1], v(0.006 + 0.004 * lean, 0.037 + rise * 0.5, -0.092), v(0.012 + 0.012 * lean, 0.038 + rise, -0.104)], i / n) for i in range(n + 1)]
                tube(m, whip, [0.0005 * (1.0 - 0.7 * i / n) for i in range(n + 1)], pick(low, 4, 0, 3), "antennae", along=(0.3, 0.6))
        # the antennal scale: a flat blade lying forward from the antenna's base
        m.part, m.index, m.root = SCALE, 0, None
        scale_root = v(0.0065, 0.0285, -0.060)

        def scale_point(t, u, scale_root=scale_root, sx=sx):
            z = scale_root.z - 0.028 * t
            wide = 0.0045 * math.sin(math.pi * min(1.0, 0.15 + 0.85 * t)) ** 0.6 * (1.0 - 0.6 * t) + 0.0004
            return scale_root + Vector((sx * (0.0025 * t + wide * (u - 0.3)), 0.002 * t - 0.001 * u, z - scale_root.z))

        blade(m, "scales", scale_point, Vector((0.0, 1.0, 0.0)), 0.0007, pick(low, 10, 3, 3), pick(low, 5, 2, 1), tags=lambda t, u: (None, t))
        # a mouthpart: leg-like, reaching forward under the head
        if low is not True:
            m.part, m.index, m.root = MOUTH, 0, None
            n = pick(low, 10, 0, 2)
            path = [bezier([v(0.004, 0.021, -0.046), v(0.007, 0.016, -0.066), v(0.006, 0.020, -0.084)], i / n) for i in range(n + 1)]
            tube(m, path, [0.0010 * (1.0 - 0.6 * i / n) for i in range(n + 1)], pick(low, 5, 0, 3), "mouthparts", along=(0.0, 1.0))
    m.a = 0.0


# The walking legs of one side, first to last: (where its joint is, the way it points in degrees from
# straight out to its side towards the tail, how far out its tip stands, how high its knee is, how thick).
LEGS = [((0.0050, 0.0215, -0.046), -50.0, 0.017, 0.025, 0.0011),
        ((0.0055, 0.0210, -0.038), -20.0, 0.022, 0.027, 0.0009),
        ((0.0060, 0.0205, -0.030), 0.0, 0.025, 0.028, 0.0009),
        ((0.0060, 0.0205, -0.021), 20.0, 0.025, 0.027, 0.0009),
        ((0.0055, 0.0210, -0.013), 42.0, 0.023, 0.026, 0.0009)]
# As the shader has it: where each pair of swimmerets hangs (z).
SWIMMERETS = (0.001, 0.0135, 0.0265, 0.0395, 0.0515)


def swimmerets(m, low):
    for i, z in enumerate(SWIMMERETS):
        cy, up, down, wide, power = profile(z)
        for sx in (1.0, -1.0):
            root = Vector((sx * 0.0035, cy - down + 0.0018, z))
            m.part, m.index, m.root = SWIM, i, root

            def point(t, u, root=root, sx=sx):
                long = 0.0095 - 0.0008 * i
                # hanging down and a little back, its two branches as one paddle
                return root + Vector((sx * (0.0012 * t + 0.0008 * (u - 0.5)), -long * t, -0.0015 * t + 0.0042 * (u - 0.4) * (1.0 - 0.5 * t)))

            blade(m, "swimmerets", point, Vector((sx * 0.15, 0.0, -1.0)), 0.0006, pick(low, 7, 2, 2), pick(low, 3, 1, 1), tags=lambda t, u: (None, t))
    m.root = None


def tail_fan(m, low):
    """The telson (narrow, pointed) and two pairs of paddles either side of it."""
    nt = pick(low, 12, 3, 4)
    nu = pick(low, 6, 2, 2)
    up = Vector((0.0, 1.0, 0.0))
    m.part, m.root = FAN, None
    m.index = 0

    def telson(t, u):
        z = 0.068 + 0.032 * t
        wide = 0.0026 * (1.0 - t) ** 0.9 + 0.0003
        return Vector((wide * (2.0 * u - 1.0), 0.0242 - 0.004 * t, z))

    blade(m, "tail fan", telson, up, 0.0016, nt, nu, tags=lambda t, u: (None, t))
    for sx in (1.0, -1.0):
        for k, (spread, long, wide) in enumerate(((0.16, 0.029, 0.0068), (0.33, 0.026, 0.0078))):
            m.index = 1 + k
            root = Vector((sx * 0.0025, 0.0240, 0.069))
            way = Vector((sx * math.sin(spread), -0.12, math.cos(spread))).normalized()
            across = Vector((sx * math.cos(spread), 0.0, -math.sin(spread)))

            def point(t, u, root=root, way=way, across=across, long=long, wide=wide):
                w = wide * math.sin(math.pi * min(1.0, 0.18 + 0.82 * t)) ** 0.5 * (1.0 - 0.25 * t) + 0.0003
                return root + way * (long * t) + across * (w * (u - 0.35))

            blade(m, "tail fan", point, up, 0.0011, nt, nu, tags=lambda t, u: (None, t))
    m.index = 0


def make(low):
    FAT[0] = game_fat if low == "game" else (lambda sides: 1.0)
    m = Mesh()
    body(m, low)
    rostrum(m, low)
    eyes(m, low)
    feelers(m, low)
    for sx in (1.0, -1.0):
        for i, (root, heading, reach, knee_high, radius) in enumerate(LEGS):
            leg(m, LEG, i, (sx * root[0], root[1], root[2]), heading, reach, knee_high, radius, pick(low, 6, 3, 3), "legs", low)
    swimmerets(m, low)
    tail_fan(m, low)
    return m


if __name__ == "__main__":
    build_all("spot_prawn", make, (0.75, 0.25, 0.12, 1.0), 0.42, close=[("side", (-1, 0, 0), (0, 0.03, 0), 0.22), ("head", (-1, 0.4, -0.8), (0, 0.032, -0.07), 0.08), ("above", (0, 1, 0.001), (0, 0.03, 0), 0.22), ("under", (0, -1, 0.001), (0, 0.03, 0), 0.22), ("quarter", (-1, 0.6, -0.9), (0, 0.03, 0), 0.24), ("tail", (-0.6, 0.6, 1), (0, 0.025, 0.08), 0.07)])
