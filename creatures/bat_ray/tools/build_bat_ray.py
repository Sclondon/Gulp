"""Builds the bat ray (creatures/bat_ray) and exports it for Godot.

Run from the game's root:
    blender --background --python creatures/bat_ray/tools/build_bat_ray.py
    blender --background --python creatures/bat_ray/tools/build_bat_ray.py -- <preview folder>   # with pictures

Writes creatures/bat_ray/models/bat_ray.glb (the full model) and bat_ray_lo.glb (far off, phones), and the
editable creatures/bat_ray/tools/bat_ray.blend (this folder has a .gdignore). Each model is one still mesh with
one surface, its wings held out flat: the shader (bat_ray.gdshader) draws every marking, flaps the wings and
opens the mouth. It prints a WINDING line: the check that nothing is inside out.

A bat ray (Myliobatis californica), 1.2 m across its wings and 1.4 m from its nose to the tip of its tail,
built from what the species looks like (no picture was traced):

- THE HEAD: raised and blunt, standing out ahead of the wings, an eye on each of its sides.
- THE DISC: 0.7 m long. Two long pointed wings, their leading edges nearly straight and swept back to the tips
  (0.32 m behind the nose), their trailing edges hollowed; thick along the middle (the back, a rounded ridge),
  thin at the edges.
- THE TAIL: a whip as long as the disc, with a small dorsal fin at its root and a sting (a spine) behind that;
  a pelvic fin each side of its root.
- THE MOUTH is underneath: a small plate (the lower jaw) hinged at its rear, which the shader swings down.

Everything here is in Godot space (metres, Y up, nose at -Z) until it is written out; the origin is on its
middle line, half way from nose to tail tip (0.7 m behind the nose: where the disc ends and the tail begins)
and half way up its height. `xm` below is metres behind the nose, `x` metres to the side.

What a point is, for the shader: UV2.y the part (0 body, 1 the mouth's plate, 2 a pelvic fin or the dorsal fin,
5 an eye, 6 the tail, 7 the spine). UV, on the body: x how far along (0 nose to 1 tail tip), y how far across;
on a fin or the mouth's plate: x from its root (0) to its edge (1), y along it; on an eye: x from its middle
(0) to its rim (1); on the tail and spine: x along (0 to 1). (The glTF writer flips V: what is written here is
1 - v, so that Godot reads v.)

The numbers marked "as the shader has it" are in bat_ray.gdshader too: change one, change the other.

THE GAME MODEL (models/bat_ray_game.glb, made in the same run; the .blend holds all three): the same curves and
profiles as the full model with far fewer, better placed points (the user, 2026-11-18: "We should have a twilight
princess model to compare to so we can make low poly versions while maintaining high quality looks and
silhouettes"). Its rows go where the outline and the profile bend most (`greedy`), with more round the eyes, the
mouth and the edges, and every UV, UV2 and part the shader reads, so it swims, opens its mouth and is marked as
the full one is. The full and low models come out exactly as before (their .glb files are byte for byte the same).

THE GILLS (2026-11-18): new parts 8 a gill slit's flap (see gill_flaps / gills below). They are a second surface on
the full and low models, so that the body's surface is the same as before; the game model has one surface.
"""

NAME = "bat_ray"
LENGTH = 1.4
HALF = 0.7
SPAN = 1.2
BODY, JAW, FIN, EYE, TAIL, SPINE = 0, 1, 2, 5, 6, 7
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


# As the shader has it: the flat the wings lie in; where the wing tips are; where the disc ends; the mouth.
PLANE = -0.0235
TIP = 0.32
DISC_TO = 0.70
MOUTH_HINGE = 0.106
MOUTH_LONG = 0.03
MOUTH_WIDE = 0.08

# How high the back stands over the wings' flat along the middle line, and how far the belly hangs under it.
BACK = Curve([(0.0, 0.0), (0.004, 0.018), (0.015, 0.04), (0.04, 0.058), (0.08, 0.066), (0.14, 0.066), (0.24, 0.072),
              (0.36, 0.06), (0.5, 0.04), (0.62, 0.026), (0.70, 0.019)])
BELLY = Curve([(0.0, 0.0), (0.004, 0.008), (0.02, 0.018), (0.06, 0.024), (0.14, 0.03), (0.3, 0.034), (0.5, 0.024),
               (0.65, 0.016), (0.70, 0.016)])
# How far to each side the back's ridge reaches.
RIDGE = Curve([(0.0, 0.085), (0.1, 0.085), (0.25, 0.12), (0.45, 0.09), (0.6, 0.05), (0.7, 0.03)])


def half_width(xm):
    """How far the edge of the disc is from the middle line: the round head, then the wing's leading edge out
    to its tip, then its hollowed trailing edge back in to the root of the tail."""
    w = 0.085 * math.sqrt(max(0.0, 1.0 - (1.0 - min(xm, 0.08) / 0.08) ** 2))
    if xm > 0.075:
        w = max(w, 0.08 + 0.52 * min(1.0, (xm - 0.075) / (TIP - 0.075)) ** 0.92)
    if xm > TIP:
        t = (xm - TIP) / (0.65 - TIP)
        if t < 1.0:
            w = min(w, 0.085 + 0.515 * (1.0 - t) ** 1.5)
        else:
            w = lerp(0.085, 0.022, smooth(0.65, DISC_TO, xm))
    return max(w, 0.0005)


def wing_thick(xm, x):
    return (0.003 + 0.02 * smooth(0.0, 0.1, xm) * (1.0 - smooth(0.5, 0.7, xm))) * (1.0 - 0.8 * min(1.0, abs(x) / 0.6))


def top(xm, x):
    u = min(1.0, abs(x) / half_width(xm))
    # (the head's sides are steep; the back behind it slopes more gently into the wings)
    steep = lerp(0.75, 0.3, smooth(0.08, 0.2, xm))
    ridge = 1.0 - smooth(steep, 1.25, abs(x) / RIDGE(xm))
    return PLANE + math.sqrt(1.0 - u * u) * (wing_thick(xm, x) + BACK(xm) * ridge)


def bot(xm, x):
    u = min(1.0, abs(x) / half_width(xm))
    ridge = 1.0 - smooth(0.3, 1.4, abs(x) / (1.3 * RIDGE(xm)))
    return PLANE - math.sqrt(1.0 - u * u) * (0.6 * wing_thick(xm, x) + BELLY(xm) * ridge)


def skin(xm, x):
    return Vector((x, top(xm, x), xm - HALF))


def tail_middle(xm):
    t = (xm - 0.66) / (LENGTH - 0.66)
    return PLANE + 0.006 * (1.0 - t)


def tail_radius(xm):
    t = (xm - 0.66) / (LENGTH - 0.66)
    return 0.021 * (1.0 - t) ** 2.2 + 0.0013


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
GAME_EYE = (28, 3)


def make(low):
    m = Mesh()
    inner, outer = pick((22, 16), (5, 5), (6, 6), low)

    def columns(xm):
        # (even over the head and back, where the skin is steep; then closer and closer towards the edge; on the
        # game model nearer even, so that the wing bends as a curve, and one more just inside the edge to keep
        # its rim fine)
        w = half_width(xm)
        mid = min(0.16, 0.88 * w)
        if GAME:
            spread = [0.3 * s + 0.7 * math.sin(s * math.pi / 2.0) for s in (j / outer for j in range(outer))] + [0.975, 1.0]
        else:
            spread = [math.sin(j / outer * math.pi / 2.0) for j in range(outer + 1)]
        half = [mid * j / inner for j in range(inner)] + [mid + (w - mid) * s for s in spread]
        return [x for x in reversed(half)] + [-x for x in half[1:]]

    def data(xm, x, upper):
        return (xm / LENGTH, 0.5 + x / SPAN), BODY, 0.0

    if GAME:
        # (rows where the outline from above and the profile from the side bend most, and round the eyes)
        xs = greedy([half_width, lambda xm: top(xm, 0.0), lambda xm: bot(xm, 0.0), lambda xm: top(xm, 0.07)],
                    [0.0006, 0.01, 0.02, 0.035, 0.049, 0.06, 0.071, MOUTH_HINGE - MOUTH_LONG, 0.08, MOUTH_HINGE, 0.14, TIP, 0.66, DISC_TO], 20, 0.09)
    else:
        xs = steps(0.0006, [(0.02, 0.0015), (0.07, 0.004), (0.14, 0.002), (TIP, 0.0065), (0.66, 0.008), (DISC_TO, 0.008)], low)
    rows = slab_rows(m, xs, columns, top, bot, data)
    slab_faces(m, rows, "body")
    slab_cap(m, rows[0], m.add(Vector((0.0, PLANE, -HALF)), (0.0, 0.5), BODY), "body")
    slab_cap(m, rows[-1], m.add(Vector((0.0, PLANE, DISC_TO + 0.002 - HALF)), (DISC_TO / LENGTH, 0.5), BODY), "body")
    for sx in (1.0, -1.0):
        # An eye on each side of the head.
        dome(m, EYE, "eyes", skin, (0.06, sx * 0.070), 0.011, 0.007, Vector((sx, 0.3, 0.0)), low)

        # A pelvic fin each side of the tail's root: a rounded flap in the wings' flat.
        def pelvic(t, u):
            reach = 0.02 + 0.035 * math.sin(math.pi * u) ** 0.7
            return (lerp(0.62, 0.69, u) + 0.84 * reach * t, lerp(0.05, 0.025, u) + 0.55 * reach * t)

        blade(m, FIN, "pelvics", pelvic, lambda p, sx=sx: Vector((sx * p[1], PLANE, p[0] - HALF)), UP, 0.007,
              pick(10, 3, 3, low), pick(18, 5, 6, low))

    # The mouth's plate, underneath: hinged along its rear edge.
    def plate(t, u):
        return (MOUTH_HINGE - MOUTH_LONG * t, (u - 0.5) * MOUTH_WIDE * (1.0 - 0.25 * t * t))

    blade(m, JAW, "mouth", plate, lambda p: Vector((p[1], bot(p[0], p[1]) - 0.002, p[0] - HALF)), DOWN, 0.004,
          pick(8, 2, 2, low), pick(14, 4, 5, low))
    print("MOUTH hinge y %.4f" % (bot(MOUTH_HINGE, 0.0) - 0.002))
    # The tail: a whip.
    tube(m, TAIL, "tail", lambda t: Vector((0.0, tail_middle(lerp(0.66, LENGTH, t)), lerp(0.66, LENGTH, t) - HALF)),
         lambda t: (tail_radius(lerp(0.66, LENGTH, t)), 0.85 * tail_radius(lerp(0.66, LENGTH, t))),
         pick(70, 18, 14, low), pick(10, 6, 8, low))

    # The dorsal fin, small, on the tail's root.
    def dorsal(t, u):
        xr = lerp(0.705, 0.765, u)
        h = 0.035 * math.sin(math.pi * u ** 0.6) ** 0.8
        return (xr + 0.5 * h * t, tail_middle(xr) + 0.006 + (h + 0.012) * t)

    blade(m, FIN, "dorsal", dorsal, lambda p: Vector((0.0, p[1], p[0] - HALF)), SIDE, 0.006, pick(10, 3, 3, low), pick(14, 4, 5, low))

    # The sting: a spine lying along the top of the tail behind the dorsal fin.
    def spine_middle(t):
        xm = lerp(0.775, 0.885, t)
        return Vector((0.0, tail_middle(xm) + 0.85 * tail_radius(xm) + 0.002 + 0.007 * t, xm - HALF))

    tube(m, SPINE, "spine", spine_middle, lambda t: (0.0035 * (1.0 - t) + 0.0004, 0.0025 * (1.0 - t) + 0.0004),
         pick(10, 3, 4, low), pick(8, 4, 4, low))
    # The gill slits' flaps (see gill_flaps): as the shader paints the slits.
    def slit(k, u):
        side = 0.031 + (0.027 - 0.002 * k) * u
        return side, 0.155 + 0.021 * k + 0.25 * (side - 0.05)

    gill_flaps(m, low, FLAPS, slit, 0.0084, 0.0009, 0.0004)
    return m


if __name__ == "__main__":
    build_all(make, (0.24, 0.2, 0.13, 1.0), 1.6, 0.6)
