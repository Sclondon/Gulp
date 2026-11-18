"""Builds the California spiny lobster (creatures/spiny_lobster) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/spiny_lobster/tools/build_spiny_lobster.py
    blender --background --python creatures/spiny_lobster/tools/build_spiny_lobster.py -- <preview folder>   # with pictures

Writes creatures/spiny_lobster/models/spiny_lobster.glb (the full model), spiny_lobster_game.glb (the game
model: few triangles, spent where the eye looks: the outline, the spines, the eyes) and spiny_lobster_lo.glb (far
off, phones), and the editable creatures/spiny_lobster/tools/spiny_lobster.blend (all three; this folder has a
.gdignore). The full and the low model come out as they did before the game model was added. Each
is one still mesh with one surface: the shader (spiny_lobster.gdshader) draws every marking, walks its legs and
swings its antennae. It prints a WINDING line for each: the check that nothing is inside out.

A California spiny lobster (Panulirus interruptus), 0.6 m from the front of its carapace (its horns) to the end
of its tail fan, built from the species (no picture was traced or copied):

- NO CLAWS. A round-sectioned carapace, 0.25 m long, covered in forward-pointing spines, with two big horns
  curving forward over the eyes; an abdomen of six segments, a little flattened, its plates' edges running
  down into spines at its sides; a broad tail fan (a telson between two pairs of paddles).
- TWO VERY LONG, THICK, SPINY ANTENNAE swept forward and out in a V, longer than the body: a heavy spiny base
  and then a whip tapering to a point. Two slender antennules between them, each forked at its end.
- Two dark eyes on stalks under the horns; leg-like mouthparts reaching forward under the head.
- TEN WALKING LEGS, five a side: out and up to a knee, then down to a point on the ground.

Everything here is in Godot space (metres, Y up, X to its left side, its head at -Z) until it is written out.
THE ORIGIN IS ON THE GROUND under the middle of the body (half way from its horns to the end of its tail fan):
its feet stand at y 0.

What a point is, for the shader: see `Mesh` below. The parts: 0 the body (the carapace and the abdomen), 1 a
walking leg (`index` which, 0 the first; `root` its joint with the body, `k` its knee, `a` 0 above the knee and 1
below it), 2 an eye (`a` 0 its stalk, 1 the eye), 3 an antenna (`index` 0 the big antenna, 1 an antennule;
`root` its base; `a` 0 at its base to 1 at its tip; the spines on it are part of it), 4 the tail fan (`index` 0
the telson, 1 an inner paddle, 2 an outer one; `a` 0 at its root to 1 at its end), 5 a spine or a horn on the
body (`a` 0 at its foot to 1 at its tip), 6 a mouthpart.

The numbers marked "as the shader has it" are in spiny_lobster.gdshader too: change one, change the other.
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

BODY, LEG, EYE, ANTENNA, FAN, SPINE, MOUTH = range(7)
# As the shader has it: the box the joints' places are written in; how far out along a leg its knee is.
BOX = (Vector((-0.1, 0.0, -0.3)), Vector((0.1, 0.2, 0.3)))
KNEE_AT = 0.42

# The body's outline along it: z, the middle line's height, half its depth above that, below it, half its
# width, and how square its section is (2 an ellipse).
PROFILE = [
    (-0.2860, 0.1120, 0.0040, 0.0040, 0.0060, 2.0),
    (-0.2780, 0.1110, 0.0240, 0.0200, 0.0280, 2.1),
    (-0.2620, 0.1085, 0.0420, 0.0350, 0.0450, 2.2),
    (-0.2300, 0.1065, 0.0530, 0.0450, 0.0560, 2.3),
    (-0.1700, 0.1050, 0.0590, 0.0500, 0.0620, 2.3),
    (-0.1000, 0.1050, 0.0590, 0.0500, 0.0630, 2.3),
    (-0.0500, 0.1040, 0.0550, 0.0465, 0.0600, 2.4),
    (-0.0350, 0.1030, 0.0510, 0.0430, 0.0575, 2.5),
    (-0.0200, 0.1030, 0.0440, 0.0370, 0.0560, 2.8),
    (0.0300, 0.1040, 0.0415, 0.0345, 0.0545, 2.9),
    (0.0800, 0.1020, 0.0385, 0.0320, 0.0505, 2.9),
    (0.1300, 0.0985, 0.0340, 0.0290, 0.0455, 2.8),
    (0.1700, 0.0945, 0.0290, 0.0250, 0.0385, 2.6),
    (0.2000, 0.0915, 0.0220, 0.0190, 0.0300, 2.4),
    (0.2120, 0.0905, 0.0100, 0.0090, 0.0140, 2.0),
]
BODY_FROM, BODY_TO = PROFILE[0][0], PROFILE[-1][0]
# As the shader has it: where the carapace ends and each segment of the abdomen begins; the groove across
# the carapace.
SEGMENTS = (-0.035, 0.006, 0.046, 0.086, 0.124, 0.160)
GROOVE = -0.15


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
    squeeze = 1.0
    for b in SEGMENTS:
        squeeze -= 0.05 * math.exp(-((z - b) / 0.004) ** 2)
        if b > SEGMENTS[0]:
            # (each plate of the abdomen starts a little inside the rear edge of the one in front)
            squeeze -= 0.03 * smooth(b - 0.0015, b + 0.0015, z) * (1.0 - smooth(b, b + 0.02, z))
    squeeze -= 0.02 * math.exp(-((z - GROOVE) / 0.004) ** 2)
    return cy, up * squeeze, down * squeeze, wide * squeeze, power


def surface(z, angle):
    """A point of the body's skin, `angle` round from the ridge of the back (0) by its left side (a
    quarter turn), and the way out from the skin there."""
    cy, up, down, wide, power = section(z)
    e = 2.0 / power

    def at(a):
        co = math.cos(a)
        s = math.sin(a)
        return Vector((math.copysign(abs(s) ** e, s) * wide, cy + math.copysign(abs(co) ** e, co) * (up if co >= 0.0 else down), z))

    p = at(angle)
    tangent = at(angle + 0.01) - at(angle - 0.01)
    out = Vector((0.0, 0.0, 1.0)).cross(tangent).normalized()
    if out.dot(Vector((p.x, p.y - cy, 0.0))) < 0.0:
        out = -out
    return p, out


def body(m, low):
    if low == "game":
        # rings where the outline turns, at each plate's edge and either side of it, few along the smooth
        # stretches; fourteen round, the ridge, the keel and the widest on points
        m.part, m.index, m.root, m.a = BODY, 0, None, 0.0
        section_loft(m, game_rings(_XS, SEGMENTS + (GROOVE,), 0.03, 0.003), section, 14, "body")
        return
    step = 0.012 if low else 0.006
    zs = []
    z = BODY_FROM
    while z < BODY_TO - 1e-9:
        zs.append(z)
        near = min(abs(z - b) for b in SEGMENTS + (GROOVE,))
        z += step * (0.5 if near < 0.008 and not low else 1.0)
    zs.append(BODY_TO)
    m.part, m.index, m.root, m.a = BODY, 0, None, 0.0
    section_loft(m, zs, section, 12 if low else 32, "body")


def spines(m, low):
    """The horns over the eyes, rows of forward-pointing spines on the carapace, a spine at the lower edge
    of each plate of the abdomen."""
    m.part, m.index, m.root = SPINE, 0, None
    sides = pick(low, 7, 4, 4)
    for sx in (1.0, -1.0):
        # the horns: big, curving forward and up over the eyes
        foot = Vector((sx * 0.024, 0.148, -0.262))
        path = [foot, Vector((sx * 0.028, 0.163, -0.282)), Vector((sx * 0.031, 0.181, -0.300))]
        m.a = 0.0
        tube(m, path, [0.013, 0.008, 0.0015], sides + 2, "spines", along=(0.0, 1.0), caps=(False, True))
        if low is True:
            continue
        # the carapace: rows of spines, more at the front and down the sides
        for z in (-0.245, -0.225, -0.205, -0.18, -0.125, -0.1, -0.075, -0.05):
            for degrees, size in ((22.0, 0.010), (48.0, 0.009), (72.0, 0.008), (96.0, 0.0065)):
                if z > GROOVE and degrees < 30.0:
                    size *= 0.7
                angle = math.radians(degrees + (6.0 if int(z * 1000) % 2 else 0.0))
                p, out = surface(z, sx * angle)
                way = (out + Vector((0.0, 0.25, -0.9))).normalized()
                m.a = 0.0
                spine(m, p - out * 0.002, p + way * size, size * 0.38, sides, "spines", tip_a=1.0)
        # the plates of the abdomen: a spine at the lower front corner of each, pointing down and back
        for b in SEGMENTS[1:]:
            z = b + 0.01
            p, out = surface(z, sx * math.radians(118.0))
            way = (out + Vector((0.0, -0.6, 0.6))).normalized()
            spine(m, p - out * 0.002, p + way * 0.011, 0.005, sides, "spines", tip_a=1.0)
    m.a = 0.0


def eyes(m, low):
    for sx in (1.0, -1.0):
        foot = Vector((sx * 0.016, 0.128, -0.262))
        head = Vector((sx * 0.028, 0.136, -0.286))
        m.part, m.index, m.root, m.a = EYE, 0, None, 0.0
        tube(m, [foot, head], [0.0075, 0.0068], pick(low, 10, 5, 6), "eyes", caps=(False, False))
        m.a = 1.0
        ball(m, head + Vector((sx * 0.002, 0.0, -0.003)), 0.0095, 0.0095, 0.0095, "eyes", lat=pick(low, 8, 3, 6), lon=pick(low, 12, 5, 14))
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


def antennae(m, low):
    """The two big spiny antennae, swept forward and out; the antennules between them; the mouthparts."""
    for sx in (1.0, -1.0):
        def v(x, y, z):
            return Vector((sx * x, y, z))
        base = v(0.033, 0.094, -0.27)
        guide = [base, v(0.045, 0.108, -0.33), v(0.072, 0.128, -0.44), v(0.125, 0.145, -0.62), v(0.195, 0.142, -0.80), v(0.26, 0.128, -0.96)]
        steps = 14 if low else 64
        # (sample the curve finely, then space the rings evenly along it)
        fine = [through(guide, i / 400.0) for i in range(401)]
        lengths = [0.0]
        for i in range(1, len(fine)):
            lengths.append(lengths[-1] + (fine[i] - fine[i - 1]).length)
        total = lengths[-1]

        def at(s):
            target = s * total
            j = 1
            while j < len(lengths) - 1 and lengths[j] < target:
                j += 1
            f = (target - lengths[j - 1]) / max(lengths[j] - lengths[j - 1], 1e-9)
            return fine[j - 1].lerp(fine[j], f)

        # (the thick spiny base, the first fifth of it, then the whip)
        def radius(s):
            if s < 0.2:
                return 0.017 - 0.03 * s + 0.0018 * math.cos(s * 160.0) * (1.0 if not low else 0.0)
            return 0.011 * (1.0 - (s - 0.2) / 0.8) ** 1.2 + 0.0012

        ss = [i / steps for i in range(steps + 1)]
        if low == "game":
            # (close together along the thick base, where it narrows fast, few along the whip)
            ss = [0.0, 0.03, 0.07, 0.11, 0.15, 0.2, 0.25, 0.31, 0.38, 0.46, 0.54, 0.62, 0.7, 0.78, 0.86, 0.93, 1.0]
        path = [at(s) for s in ss]
        m.part, m.index, m.root = ANTENNA, 0, base
        tube(m, path, [radius(s) for s in ss], pick(low, 7, 5, 5), "antennae", along=(0.0, 1.0), caps=(False, True))
        if low is not True:
            # spines along the base and, smaller, up the whip
            count = 34
            # (the game model: every other one)
            for k in range(0, count, pick(low, 1, 1, 2)):
                s = 0.02 + 0.5 * (k / count) ** 1.4
                p = at(s)
                ahead = (at(s + 0.01) - p).normalized()
                ring = ahead.cross(Vector((0.0, 1.0, 0.0))).normalized()
                turn = k * 2.4
                out = (ring * math.cos(turn) + ahead.cross(ring) * math.sin(turn)).normalized()
                r = radius(s)
                size = 0.012 if s < 0.2 else 0.006 * (1.0 - s)
                m.a = s
                spine(m, p + out * (r * 0.6), p + out * (r + size) + ahead * size * 0.8, size * 0.4 + 0.001, pick(low, 5, 0, 3), "antennae")
        # the antennule: a slender stalk forward, then two short whips
        base = v(0.011, 0.084, -0.278)
        m.index, m.root = 1, base
        stalk = [base, v(0.015, 0.094, -0.33), v(0.02, 0.102, -0.375)]
        tube(m, stalk, [0.0045, 0.0038, 0.003], pick(low, 7, 4, 5), "antennae", along=(0.0, 0.4))
        if low is not True:
            n = pick(low, 10, 0, 4)
            for lean, rise in ((1.0, 0.012), (0.3, -0.006)):
                whip = [bezier([stalk[-1], v(0.026 + 0.01 * lean, 0.105 + rise * 0.5, -0.41), v(0.04 + 0.03 * lean, 0.108 + rise, -0.45)], i / n) for i in range(n + 1)]
                tube(m, whip, [0.0024 * (1.0 - 0.6 * i / n) for i in range(n + 1)], pick(low, 5, 0, 3), "antennae", along=(0.4, 0.7))
        # a mouthpart: leg-like, reaching forward under the head
        if low is not True:
            m.part, m.index, m.root = MOUTH, 0, None
            n = pick(low, 10, 0, 4)
            path = [bezier([v(0.016, 0.062, -0.23), v(0.03, 0.045, -0.29), v(0.028, 0.055, -0.33)], i / n) for i in range(n + 1)]
            tube(m, path, [0.006 * (1.0 - 0.5 * i / n) for i in range(n + 1)], pick(low, 6, 0, 4), "mouthparts", along=(0.0, 1.0))
    m.a = 0.0
    m.root = None


# The walking legs of one side, first to last: (where its joint is, the way it points in degrees from
# straight out to its side towards the tail, how far out its tip stands, how high its knee is, how thick).
LEGS = [((0.034, 0.072, -0.205), -38.0, 0.120, 0.128, 0.0080),
        ((0.037, 0.070, -0.175), -14.0, 0.136, 0.134, 0.0080),
        ((0.039, 0.068, -0.145), 6.0, 0.142, 0.135, 0.0078),
        ((0.039, 0.068, -0.115), 24.0, 0.140, 0.132, 0.0076),
        ((0.036, 0.070, -0.085), 42.0, 0.132, 0.126, 0.0072)]


def tail_fan(m, low):
    """The telson and two pairs of paddles either side of it: broad, their rear edges soft and rounded."""
    nt = pick(low, 12, 3, 6)
    nu = pick(low, 8, 3, 2)
    up = Vector((0.0, 1.0, 0.0))
    m.part, m.root = FAN, None
    m.index = 0

    def telson(t, u):
        z = 0.196 + 0.104 * t
        wide = 0.024 * (0.9 + 0.1 * t) * (1.0 - smooth(0.82, 1.0, t) * 0.55) + 0.001
        return Vector((wide * (2.0 * u - 1.0), 0.0915 - 0.012 * t, z))

    blade(m, "tail fan", telson, up, 0.008, nt, nu, tags=lambda t, u: (None, t))
    for sx in (1.0, -1.0):
        for k, (spread, long, wide) in enumerate(((0.22, 0.098, 0.044), (0.46, 0.09, 0.05))):
            m.index = 1 + k
            root = Vector((sx * 0.012, 0.0905, 0.198))
            way = Vector((sx * math.sin(spread), -0.12, math.cos(spread))).normalized()
            across = Vector((sx * math.cos(spread), 0.0, -math.sin(spread)))

            def point(t, u, root=root, way=way, across=across, long=long, wide=wide):
                w = wide * math.sin(math.pi * min(1.0, 0.25 + 0.75 * t)) ** 0.4 + 0.001
                return root + way * (long * t) + across * (w * (u - 0.4))

            blade(m, "tail fan", point, up, 0.006, nt, nu, tags=lambda t, u: (None, t))
    m.index = 0


def make(low):
    FAT[0] = game_fat if low == "game" else (lambda sides: 1.0)
    m = Mesh()
    body(m, low)
    spines(m, low)
    eyes(m, low)
    antennae(m, low)
    for sx in (1.0, -1.0):
        for i, (root, heading, reach, knee_high, radius) in enumerate(LEGS):
            leg(m, LEG, i, (sx * root[0], root[1], root[2]), heading, reach, knee_high, radius, pick(low, 8, 3, 4), "legs", low)
    tail_fan(m, low)
    return m


if __name__ == "__main__":
    build_all("spiny_lobster", make, (0.5, 0.17, 0.08, 1.0), 2.0,
              close=[("side", (-1, 0, 0), (0, 0.1, 0), 0.75), ("above", (0, 1, 0.001), (0, 0.1, -0.1), 1.0),
                     ("head", (-1, 0.5, -0.8), (0, 0.12, -0.25), 0.3), ("under", (0, -1, 0.001), (0, 0.1, 0), 0.75),
                     ("quarter", (-1, 0.7, -0.9), (0, 0.1, -0.1), 1.0), ("tail", (-0.6, 0.8, 1), (0, 0.09, 0.22), 0.25),
                     ("front", (0, 0.1, -1), (0, 0.1, 0), 0.6)])
