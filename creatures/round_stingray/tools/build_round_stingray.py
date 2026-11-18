"""Builds the round stingray (creatures/round_stingray) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/round_stingray/tools/build_round_stingray.py
    blender --background --python creatures/round_stingray/tools/build_round_stingray.py -- <preview folder>   # with pictures

Writes creatures/round_stingray/models/round_stingray.glb (the full model) and round_stingray_lo.glb (far off,
phones), and the editable creatures/round_stingray/tools/round_stingray.blend (this folder has a .gdignore).
Each model is one still mesh with one surface, lying flat: the shader (round_stingray.gdshader) draws every
marking, ripples the disc's edge and opens the mouth. It prints a WINDING line: the check that nothing is
inside out.

A round stingray (Urobatis halleri), 0.5 m from its nose to the end of its tail (a big one), built from what
the species looks like (no picture was traced):

- THE DISC: nearly round, 0.29 m long and 0.28 m across, a low dome along the middle thinning to a fine edge
  all the way round. The eyes are on top, on two low bumps, a third of the way back.
- THE TAIL: short and stout, shorter than the disc, with a sting (a spine) half way along it and a small
  leaf-shaped tail fin round its end; no dorsal fin. A small rounded pelvic fin each side of its root.
- THE MOUTH is underneath: a small plate (the lower jaw) hinged at its rear, which the shader swings down.

Everything here is in Godot space (metres, Y up, nose at -Z) until it is written out; the origin is on its
middle line, half way from nose to tail end (0.25 m behind the nose) and half way up its height. `xm` below is
metres behind the nose, `x` metres to the side.

What a point is, for the shader: UV2.y the part (0 body, 1 the mouth's plate, 2 a pelvic fin, 3 the tail fin,
5 an eye, 6 the tail, 7 the spine). UV, on the body: x how far along (0 nose to 1 tail end), y how far across;
on a fin or the mouth's plate: x from its root (0) to its edge (1), y along it; on an eye: x from its middle
(0) to its rim (1); on the tail and spine: x along (0 to 1). (The glTF writer flips V: what is written here is
1 - v, so that Godot reads v.)

The numbers marked "as the shader has it" are in round_stingray.gdshader too: change one, change the other.

THE GAME MODEL (models/round_stingray_game.glb, made in the same run; the .blend holds all three): the same curves and
profiles as the full model with far fewer, better placed points (the user, 2026-11-18: "We should have a twilight
princess model to compare to so we can make low poly versions while maintaining high quality looks and
silhouettes"). Its rows go where the outline and the profile bend most (`greedy`), with more round the eyes, the
mouth and the edges, and every UV, UV2 and part the shader reads, so it swims, opens its mouth and is marked as
the full one is. The full and low models come out exactly as before (their .glb files are byte for byte the same).

THE GILLS (2026-11-18): new parts 8 a gill slit's flap (see gill_flaps / gills below). They are a second surface on
the full and low models, so that the body's surface is the same as before; the game model has one surface.
"""

NAME = "round_stingray"
LENGTH = 0.5
HALF = 0.25
BODY, JAW, FIN, TAILFIN, EYE, TAIL, SPINE = 0, 1, 2, 3, 5, 6, 7
# (a gill slit's flap, under the head)
FLAPS = 8


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
DOWN = Vector((0.0, -1.0, 0.0))
SIDE = Vector((1.0, 0.0, 0.0))

# True while the game model is being made: every count then comes from its own game numbers (in make), and
# the full and low models are made exactly as before.
GAME = False


def pick(full, low_value, game_value, low):
    """How many of something: on the game model, the low one, or the full one."""
    if GAME:
        return game_value
    return low_value if low else full


def greedy(fns, seeds, n, max_step):
    """`n` intervals from seeds[0] to seeds[-1], spent where the curves `fns` bend most: each interval longer
    than `max_step` is halved, then the interval whose middle strays furthest from the straight line between its
    ends (in any of `fns`) is halved, until there are `n`. For the game model: its points go where the outline
    and the profile need them."""
    xs = sorted(set(seeds))

    def err(a, b):
        worst = 0.0
        for f in fns:
            fa, fb = f(a), f(b)
            for s in (0.25, 0.5, 0.75):
                x = a + (b - a) * s
                worst = max(worst, abs(f(x) - (fa + (fb - fa) * s)))
        return worst

    changed = True
    while changed:
        changed = False
        for i in range(len(xs) - 1):
            if xs[i + 1] - xs[i] > max_step:
                xs.insert(i + 1, 0.5 * (xs[i] + xs[i + 1]))
                changed = True
                break
    while len(xs) - 1 < n:
        best = max(range(len(xs) - 1), key=lambda i: err(xs[i], xs[i + 1]) if xs[i + 1] - xs[i] > 1e-4 else -1.0)
        xs.insert(best + 1, 0.5 * (xs[best] + xs[best + 1]))
    return xs


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def soft(a):
    """|a| with its corner at the middle line rounded off (0 at 0)."""
    return math.sqrt(a * a + 0.0016) - 0.04




def to_b(p):
    return Vector((p.x, -p.z, p.y))


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def lerp(a, b, t):
    return a + (b - a) * t


class Curve:
    """A curve through (x, y) points that never overshoots them (Fritsch and Carlson)."""

    def __init__(self, points):
        self.xs = [p[0] for p in points]
        self.ys = [p[1] for p in points]
        xs, ys = self.xs, self.ys
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
        self.m = m

    def __call__(self, x):
        xs, ys, m = self.xs, self.ys, self.m
        x = max(xs[0], min(xs[-1], x))
        i = 0
        while i < len(xs) - 2 and x > xs[i + 1]:
            i += 1
        h = xs[i + 1] - xs[i]
        t = (x - xs[i]) / h
        a = (2 * t ** 3 - 3 * t ** 2 + 1) * ys[i] + (t ** 3 - 2 * t ** 2 + t) * h * m[i]
        b = (-2 * t ** 3 + 3 * t ** 2) * ys[i + 1] + (t ** 3 - t ** 2) * h * m[i + 1]
        return a + b


def steps(start, pieces, low, coarser=4.0):
    """Places along the animal: from `start`, then for each (until, step) piece, evenly to `until`."""
    xs = []
    x = start
    for until, step in pieces:
        if low:
            step *= coarser
        n = max(1, round((until - x) / step))
        for i in range(n):
            xs.append(x + (until - x) * i / n)
        x = until
    xs.append(x)
    return xs


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        # per point: (uv, uv2)
        self.data = []
        # per face: the way it should face
        self.out = []
        self.count = {}

    def add(self, p, uv, part, extra=0.0):
        self.verts.append(p)
        self.data.append(((uv[0], 1.0 - uv[1]), (extra, 1.0 - part)))
        return len(self.verts) - 1

    def face(self, points, out, name):
        """A face wound so that its front (the side its points go round anticlockwise) is towards `out`."""
        ps = [self.verts[i] for i in points]
        n = Vector((0.0, 0.0, 0.0))
        for i in range(len(ps)):
            n += ps[i].cross(ps[(i + 1) % len(ps)])
        if n.length < 1e-13:
            return
        if n.dot(out) < 0.0:
            points = tuple(reversed(points))
        self.faces.append(tuple(points))
        self.out.append((Vector(out), name))
        self.count[name] = self.count.get(name, 0) + 1


def slab_rows(m, xs, columns, top, bot, data, lo=0, hi=None, edges=(True, True), reuse=None):
    """Rows of a flat body's skin: at each place along it (`xs`, metres behind the nose) a row of points across
    its upper side and a row across its under side, at `columns(xm)[lo..hi]` (metres to the side, from its +X
    edge to its -X edge). Where an end of the row is the body's own edge (`edges`), the two sides share that
    point. `data(xm, x, upper)` gives a point's (uv, part, extra). `reuse` is a row to begin from in place of
    the first."""
    rows = []
    for k, xm in enumerate(xs):
        if k == 0 and reuse is not None:
            rows.append(reuse)
            continue
        cols = columns(xm)
        last = len(cols) - 1 if hi is None else hi
        t = []
        b = []
        for i in range(lo, last + 1):
            x = cols[i]
            uv, part, extra = data(xm, x, True)
            ti = m.add(Vector((x, top(xm, x), xm - HALF)), uv, part, extra)
            t.append(ti)
            if (i == lo and edges[0]) or (i == last and edges[1]):
                b.append(ti)
            else:
                uv, part, extra = data(xm, x, False)
                b.append(m.add(Vector((x, bot(xm, x), xm - HALF)), uv, part, extra))
        rows.append((t, b))
    return rows


def slab_faces(m, rows, name):
    for r in range(len(rows) - 1):
        for which, out in ((0, UP), (1, DOWN)):
            a = rows[r][which]
            b = rows[r + 1][which]
            for i in range(len(a) - 1):
                m.face((a[i], a[i + 1], b[i + 1], b[i]), out, name)


def slab_cap(m, row, tip, name):
    """Closes an end of a flat body: a fan from the point `tip` to each side of a row."""
    for which, out in ((0, UP), (1, DOWN)):
        a = row[which]
        for i in range(len(a) - 1):
            m.face((tip, a[i], a[i + 1]), out, name)


def blade(m, part, name, point, place, facing, thick, nt, nu, extra=None):
    """A fin: a thin closed blade. `point(t, u)` is a place in the fin's own flat (t 0 at its root to 1 at
    its edge, u 0 at its leading end to 1 at its trailing end), `place` puts that in the model, `facing`
    is the way one of its two skins faces. It is `thick` at its root, a foil across (nothing at either
    end), thinning to nothing at its edge."""
    for side in (1.0, -1.0):
        grid = []
        for ti in range(nt + 1):
            t = ti / nt
            row = []
            for ui in range(nu + 1):
                u = ui / nu
                foil = 2.6 * math.sqrt(u) * (1.0 - u)
                swell = thick * (1.0 - t) ** 0.7 * foil
                p = place(point(t, u)) + facing * (side * swell * 0.5)
                row.append(m.add(p, (t, u), part, extra(t, u) if extra else 0.0))
            grid.append(row)
        for ti in range(nt):
            for ui in range(nu):
                m.face((grid[ti][ui], grid[ti][ui + 1], grid[ti + 1][ui + 1], grid[ti + 1][ui]), facing * side, name)


def dome(m, part, name, skin, at, radius, height, toward, low):
    """An eye: a dome lying on the skin. `skin(a, b)` is a place on the skin by two coordinates (metres)."""
    spokes = pick(32, 10, GAME_EYE[0], low)
    rings = pick(10, 3, GAME_EYE[1], low)
    a0, b0 = at
    e = 0.003
    out = (skin(a0 + e, b0) - skin(a0 - e, b0)).cross(skin(a0, b0 + e) - skin(a0, b0 - e))
    out.normalize()
    if out.dot(toward) < 0.0:
        out = -out
    if not low and not GAME:
        base = skin(a0, b0)
        print("EYE at vec3(%.5f, %.5f, %.5f) out vec3(%.5f, %.5f, %.5f) radius %.4f" % (base.x, base.y, base.z, out.x, out.y, out.z, radius))
    middle = m.add(skin(a0, b0) + out * height, (0.0, 0.0), part)
    last = None
    for k in range(1, rings + 1):
        r = k / rings
        row = []
        for s in range(spokes):
            a = s / spokes * TAU
            p = skin(a0 + math.cos(a) * radius * r, b0 + math.sin(a) * radius * r)
            # (its rim is sunk a little into the skin, so that no gap shows under it)
            row.append(m.add(p + out * (height * (1.0 - r * r) ** 0.7 - 0.0012 * r ** 4), (r, 0.0), part))
        for s in range(spokes):
            n = (s + 1) % spokes
            if last is None:
                m.face((middle, row[s], row[n]), out, name)
            else:
                m.face((last[s], row[s], row[n], last[n]), out, name)
        last = row
    return out


def tube(m, part, name, centre, radii, nt, na):
    """A round tail or spine lying along the animal: `centre(t)` its middle and `radii(t)` its half width and
    half height, t 0 at its front to 1 at its end. Closed at both ends."""
    rows = []
    for i in range(nt + 1):
        t = i / nt
        c = centre(t)
        rx, ry = radii(t)
        rows.append([m.add(c + Vector((math.cos(k / na * TAU) * rx, math.sin(k / na * TAU) * ry, 0.0)), (t, k / na), part)
                     for k in range(na)])
    for i in range(nt):
        for k in range(na):
            n = (k + 1) % na
            a = (k + 0.5) / na * TAU
            m.face((rows[i][k], rows[i][n], rows[i + 1][n], rows[i + 1][k]), Vector((math.cos(a), math.sin(a), 0.0)), name)
    for row, t, way in ((rows[0], 0.0, -1.0), (rows[-1], 1.0, 1.0)):
        tip = m.add(centre(t) + Vector((0.0, 0.0, way * 0.0005)), (t, 0.0), part)
        for k in range(na):
            m.face((tip, row[k], row[(k + 1) % na]), Vector((0.0, 0.0, way)), name)


def make_object(name, m, colour):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) for p in m.verts], [], m.faces)
    # (every layer made first, then each looked up by name: making one moves the others)
    mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.new(name="UV2")
    uv = mesh.uv_layers["UVMap"].data
    uv2 = mesh.uv_layers["UV2"].data
    for poly in mesh.polygons:
        for corner, vi in enumerate(poly.vertices):
            d = m.data[vi]
            uv[poly.loop_start + corner].uv = d[0]
            uv2[poly.loop_start + corner].uv = d[1]
    material = bpy.data.materials.get(NAME) or bpy.data.materials.new(NAME)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = colour
    material.diffuse_color = colour
    mesh.materials.append(material)
    if not GAME:
        # (the full and low models: the gills a second surface, so that the body's is the same as it was, and
        # Godot's importer thins it far off as it did; the game model is drawn without those thinned meshes)
        inner = bpy.data.materials.get(NAME + "_gills") or bpy.data.materials.new(NAME + "_gills")
        inner.diffuse_color = (0.5, 0.05, 0.05, 1.0)
        mesh.materials.append(inner)
        for poly in mesh.polygons:
            if m.out[poly.index][1] in GILL_FACES:
                poly.material_index = 1
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    lo = [min(p[i] for p in m.verts) for i in range(3)]
    hi = [max(p[i] for p in m.verts) for i in range(3)]
    print("BUILT %s verts=%d tris=%d from (%.4f, %.4f, %.4f) to (%.4f, %.4f, %.4f)" % ((name, len(mesh.vertices), tris) + tuple(lo) + tuple(hi)))
    winding(name, mesh, m)
    return obj


def winding(name, mesh, m):
    """Nothing inside out: each face is looked at against the way it was built to face: the upper skin up,
    the under skin down, each skin of a fin away from the fin's own flat, an eye out from the head, a tail out
    from its middle (Blender's front is the side a face's normal is on)."""
    bad = {}
    for poly in mesh.polygons:
        out, group = m.out[poly.index]
        if poly.normal.dot(to_b(out)) <= 0.0:
            bad[group] = bad.get(group, 0) + 1
    told = ["%s %d/%d wrong" % (group, bad.get(group, 0), count) for group, count in m.count.items()]
    print("WINDING %s: %s: %s" % (name, "ok" if not bad else "INSIDE OUT", ", ".join(told)))


def export_one(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", export_yup=True, use_selection=True,
        export_animations=False, export_texcoords=True,
    )


def render(folder, made, frame, head_at):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_cavity = True
    scene.display.shading.show_backface_culling = True
    scene.render.resolution_x, scene.render.resolution_y = 1400, 800
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    # (Blender space: the animal lies along Y, its nose at +Y, up is Z)
    views = [("left", (1, 0, 0), (0, 0, 0), frame), ("right", (-1, 0, 0), (0, 0, 0), frame),
             ("front", (0, 1, 0), (0, 0, 0), frame * 0.8), ("back", (0, -1, 0), (0, 0, 0), frame * 0.8),
             ("top", (0.001, 0, 1), (0, 0, 0), frame * 1.8), ("under", (0.001, 0, -1), (0, 0, 0), frame * 1.8),
             ("head", (0.6, 0.6, 0.5), (0, head_at, 0), frame * 0.3),
             ("head_under", (0.5, 0.6, -0.6), (0, head_at, 0), frame * 0.3),
             ("tail", (0.7, -0.6, 0.4), (0, -head_at, 0), frame * 0.45)]
    for low, obj in ((False, made[0]), (True, made[1])):
        for other in made:
            other.hide_render = other is not obj
        for view, direction, target, size in views:
            if low and view not in ("top", "head"):
                continue
            offset = Vector(direction).normalized() * 40.0
            camera.data.ortho_scale = size
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s%s.png" % ("lo_" if low else "", view))
            bpy.ops.render.render(write_still=True)


def build_all(make, colour, frame, head_at):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    global GAME
    full = make_object(NAME, make(False), colour)
    low = make_object(NAME + "_lo", make(True), colour)
    GAME = True
    game = make_object(NAME + "_game", make(False), colour)
    GAME = False
    os.makedirs(OUT, exist_ok=True)
    export_one(full, os.path.join(OUT, NAME + ".glb"))
    export_one(low, os.path.join(OUT, NAME + "_lo.glb"))
    export_one(game, os.path.join(OUT, NAME + "_game.glb"))
    low.location.x = frame
    game.location.x = -frame
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, NAME + ".blend"))
    low.location.x = 0.0
    game.location.x = 0.0
    game.hide_render = True
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, [full, low], frame, head_at)


# As the shader has it: the flat the disc's edge lies in; the disc's middle and its half length and half
# width; where the eyes are; the mouth.
PLANE = -0.011
DISC_MID = 0.145
DISC_LONG = 0.145
DISC_WIDE = 0.14
EYE_AT = (0.088, 0.029)
MOUTH_HINGE = 0.072
MOUTH_LONG = 0.014
MOUTH_WIDE = 0.034
TAIL_Y = PLANE + 0.004

# How high the back stands over the edge's flat along the middle line.
BACK = Curve([(0.0, 0.0), (0.01, 0.006), (0.05, 0.022), (0.09, 0.030), (0.15, 0.034), (0.22, 0.028), (0.27, 0.018),
              (0.29, 0.012)])


def half_width(xm):
    return max(0.0005, DISC_WIDE * math.sqrt(max(0.0, 1.0 - ((xm - DISC_MID) / DISC_LONG) ** 2)))


def top(xm, x):
    u = min(1.0, abs(x) / half_width(xm))
    # (the eyes stand on two low bumps)
    orbit = 0.006 * math.exp(-((xm - EYE_AT[0]) ** 2 + (abs(x) - EYE_AT[1] + 0.002) ** 2) / 0.011 ** 2)
    return PLANE + math.sqrt(1.0 - u * u) * (0.006 + BACK(xm) * math.exp(-(x / 0.042) ** 2) + orbit)


def bot(xm, x):
    u = min(1.0, abs(x) / half_width(xm))
    return PLANE - math.sqrt(1.0 - u * u) * (0.004 + 0.42 * BACK(xm) * math.exp(-(x / 0.065) ** 2))


def skin(xm, x):
    return Vector((x, top(xm, x), xm - HALF))


def tail_radius(xm):
    return lerp(0.017, 0.004, max(0.0, (xm - 0.25) / 0.225) ** 0.8)


# ---------------------------------------------------------------- the gills

# (added 2026-11-18, the user: "The fish need modeled gills as well, well for relevant fish, so like when it opens
# its mouth wide you can see them")
GILL_FACES = ("gill arches", "gill flaps")


def closed_sheet(m, part, name, grid_point, nt, nu, thick, facing, extra=0.0, uv_y=None):
    """A thin closed blade: `grid_point(t, u)` is its middle, `facing` the way its first skin faces; `thick` at its
    root (t 0), nothing at its edge (t 1) and at both ends (u 0, 1)."""
    for side in (1.0, -1.0):
        grid = []
        for ti in range(nt + 1):
            t = ti / nt
            row = []
            for ui in range(nu + 1):
                u = ui / nu
                swell = thick * (1.0 - t) ** 0.7 * 2.6 * math.sqrt(u) * (1.0 - u)
                p = grid_point(t, u) + facing * (side * swell * 0.5)
                row.append(m.add(p, (t, u if uv_y is None else uv_y), part, extra))
            grid.append(row)
        for ti in range(nt):
            for ui in range(nu):
                m.face((grid[ti][ui], grid[ti][ui + 1], grid[ti + 1][ui + 1], grid[ti + 1][ui]), facing * side, name)


def gill_flaps(m, low, part, slit, width, sink, thick):
    """Five a side under the head, where the shader paints the gill slits: each a thin closed blade lying just
    inside the skin of the model as built (found by a ray up from below), from its slit (UV.x 0) back to its edge
    (UV.x 1). The shader drops its back edge as the gills open, so that a flap of skin lifts and the red of the gills
    shows under it. `slit(k, u)` is a point of slit k (0 to 4), u from its inner end (0) to its outer end (1), as
    (metres to the side, metres behind the nose)."""
    from mathutils.bvhtree import BVHTree
    tree = BVHTree.FromPolygons(m.verts, m.faces)
    nt, nu = pick((3, 8), (1, 2), (1, 2), low)
    for k in range(5):
        for sx in (1.0, -1.0):
            def flap_point(t, u, k=k, sx=sx):
                side, xm = slit(k, 0.04 + 0.92 * u)
                x = sx * side
                z = xm + t * width - HALF
                hit = tree.ray_cast(Vector((x, -50.0, z)), Vector((0.0, 1.0, 0.0)))
                y = hit[0].y if hit[0] is not None else bot(xm + t * width, side)
                return Vector((x, y + sink + 0.5 * thick, z))
            closed_sheet(m, part, "gill flaps", flap_point, nt, nu, thick, DOWN)


# The game model's eye: (spokes, rings).
GAME_EYE = (24, 3)


def make(low):
    m = Mesh()
    n = pick(57, 17, 15, low)

    def columns(xm):
        w = half_width(xm)
        cs = [math.cos(i / (n - 1) * math.pi) for i in range(n)]
        return [w * (0.6 * c + 0.4 * c ** 3) for c in cs]

    def data(xm, x, upper):
        return (xm / LENGTH, 0.5 + x / 0.3), BODY, 0.0

    if GAME:
        # (rows where the outline from above and the profile from the side bend most, and round the eyes)
        xs = greedy([half_width, lambda xm: top(xm, 0.0), lambda xm: bot(xm, 0.0), lambda xm: top(xm, EYE_AT[1])],
                    [0.0005, 0.012, 0.05, EYE_AT[0] - 0.007, EYE_AT[0], EYE_AT[0] + 0.007, 0.24, 0.287], 17, 0.03)
    else:
        xs = steps(0.0005, [(0.012, 0.001), (0.05, 0.003), (0.24, 0.0042), (0.287, 0.003)], low, 3.5)
    rows = slab_rows(m, xs, columns, top, bot, data)
    slab_faces(m, rows, "body")
    slab_cap(m, rows[0], m.add(Vector((0.0, PLANE, -HALF)), (0.0, 0.5), BODY), "body")
    slab_cap(m, rows[-1], m.add(Vector((0.0, PLANE, 0.29 - HALF)), (0.58, 0.5), BODY), "body")
    for sx in (1.0, -1.0):
        dome(m, EYE, "eyes", skin, (EYE_AT[0], sx * EYE_AT[1]), 0.007, 0.005, Vector((sx * 0.6, 1.0, 0.0)), low)

        # A pelvic fin each side of the tail's root: a small rounded flap.
        def pelvic(t, u):
            reach = 0.01 + 0.02 * math.sin(math.pi * u) ** 0.7
            return (lerp(0.245, 0.285, u) + 0.8 * reach * t, lerp(0.03, 0.014, u) + 0.6 * reach * t)

        blade(m, FIN, "pelvics", pelvic, lambda p, sx=sx: Vector((sx * p[1], PLANE, p[0] - HALF)), UP, 0.004,
              pick(8, 3, 2, low), pick(14, 5, 4, low))

    # The mouth's plate, underneath: hinged along its rear edge.
    def plate(t, u):
        return (MOUTH_HINGE - MOUTH_LONG * t, (u - 0.5) * MOUTH_WIDE * (1.0 - 0.25 * t * t))

    blade(m, JAW, "mouth", plate, lambda p: Vector((p[1], bot(p[0], p[1]) - 0.001, p[0] - HALF)), DOWN, 0.002,
          pick(6, 2, 2, low), pick(12, 4, 3, low))
    print("MOUTH hinge y %.4f" % (bot(MOUTH_HINGE, 0.0) - 0.001))
    # The tail: short and stout.
    tube(m, TAIL, "tail", lambda t: Vector((0.0, TAIL_Y, lerp(0.25, 0.475, t) - HALF)),
         lambda t: (tail_radius(lerp(0.25, 0.475, t)), 0.8 * tail_radius(lerp(0.25, 0.475, t))),
         pick(30, 8, 10, low), pick(12, 6, 8, low))

    # The tail fin: a small leaf round the end of the tail, a lobe above and a lobe below.
    for way, tall in ((1.0, 0.017), (-1.0, 0.013)):
        def lobe(t, u, way=way, tall=tall):
            xm = lerp(0.385, 0.5, u)
            return (xm, TAIL_Y + way * tall * (0.08 + 0.92 * math.sin(math.pi * u ** 0.75) ** 0.7) * t)

        blade(m, TAILFIN, "tail fin", lobe, lambda p: Vector((0.0, p[1], p[0] - HALF)), SIDE, 0.004, pick(8, 3, 2, low), pick(20, 5, 7, low))

    # The sting: a spine lying along the top of the tail, half way down it.
    def spine_middle(t):
        xm = lerp(0.365, 0.428, t)
        return Vector((0.0, TAIL_Y + 0.8 * tail_radius(xm) + 0.001 + 0.004 * t, xm - HALF))

    tube(m, SPINE, "spine", spine_middle, lambda t: (0.0022 * (1.0 - t) + 0.0003, 0.0016 * (1.0 - t) + 0.0003),
         pick(8, 3, 3, low), pick(8, 4, 4, low))
    # The gill slits' flaps (see gill_flaps): as the shader paints the slits.
    def slit(k, u):
        side = 0.0215 + 0.015 * u
        return side, 0.092 + 0.011 * k + 0.2 * (side - 0.03)

    gill_flaps(m, low, FLAPS, slit, 0.0044, 0.0003, 0.00025)
    return m


if __name__ == "__main__":
    build_all(make, (0.45, 0.36, 0.24, 1.0), 0.6, 0.17)
