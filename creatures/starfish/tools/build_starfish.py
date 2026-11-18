"""Builds the sea stars (creatures/starfish) and exports them for Godot.

Run from the game's root:
    blender --background --factory-startup --python creatures/starfish/tools/build_starfish.py
    blender --background --factory-startup --python creatures/starfish/tools/build_starfish.py -- <preview folder>

Three kinds, each three models (one still mesh, one surface each):
    models/starfish_<kind>.glb        the full model (close pictures)
    models/starfish_<kind>_game.glb   the game model (Twilight Princess weight: triangles spent on the outline)
    models/starfish_<kind>_lo.glb     the low model (far off, many of them)
and the editable tools/starfish.blend with all nine (this folder has a .gdignore).

The kinds, built from what the animals look like (no picture traced):
- classic: a five-armed sea star after the ochre star (Pisaster ochraceus) of the California coast: a raised disc,
  five stout tapering arms, a knobbly skin (a net of pale blunt spines; on the full model the knobs are in the
  shape, on the others the shader draws them in the same places).
- sunflower: a sunflower star (Pycnopodia helianthoides): a broad soft disc and twenty arms.
- brittle: a brittle star after the spiny brittle star (Ophiothrix spiculata): a small pentagonal disc and five long
  thin arms with glassy spines along their sides.
Beneath every arm, rows of tube feet down to the ground.

Everything here is in Godot space (metres, Y up, X its left side, -Z its front) until it is written out. The
origin is on the ground under the middle of the disc; arm 0 points to -Z, the others follow round towards +X.

What a point is, for the shader (starfish.gdshader):
    UV2.y the part: 0 the disc, 1 an arm, 2 a tube foot, 3 a spine on an arm.
    UV2.x which arm it belongs to, as a fraction of a turn (arm k of n: k / n); the disc 0.
    UV, on the disc: x how far out (0 middle, 1 its edge), y how high (0 underneath, 1 its top).
        on an arm: x how far along it (metres from the middle / the arm's length), y how high (0 its flat
        underside, 1 the top of its back, at that place along it).
        on a foot or spine: x as the arm's at its root, y from its root (0) to its tip (1).
(The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.)
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
DISC, ARM, FOOT, SPINE = range(4)

# n arms; L from the middle to an arm's tip; w the arm's half width at its root and its tip; h its height (above
# its underside) at its root and tip; rd, hd the disc's radius and height; y0 the underside's height above the
# ground (the tube feet below it); knobs: the lattice's cell, a knob's radius and height (height 0: drawn only).
KINDS = {
    "classic": dict(n=5, L=0.135, w=(0.025, 0.009), h=(0.026, 0.009), rd=0.038, hd=0.032, flare=0.7, y0=0.0025,
                    cell=0.0075, knob_r=0.0019, knob_h=0.0014, spines=False, lobes=0.0),
    "sunflower": dict(n=20, L=0.29, w=(0.03, 0.01), h=(0.02, 0.0065), rd=0.105, hd=0.028, flare=0.3, y0=0.0025,
                      cell=0.0075, knob_r=0.0019, knob_h=0.0, spines=False, lobes=0.0),
    "brittle": dict(n=5, L=0.1, w=(0.0024, 0.0006), h=(0.0028, 0.0007), rd=0.012, hd=0.0062, flare=0.0, y0=0.0006,
                    cell=0.0, knob_r=0.0, knob_h=0.0, spines=True, lobes=0.09),
}

# How finely each model is cut: arm rings (and their bunching at the tip), points round an arm, disc rings and
# points round it, tube feet (rows, spacing, sides), spines every how many segments.
DETAIL = {
    "full": dict(ring=None, around=32, disc_rings=24, disc_around=96, feet_gap=0.0025, foot_sides=4, foot_segs=1,
                 spine_every=1),
    "game": dict(ring=None, around=10, disc_rings=5, disc_around=25, feet_gap=None, foot_sides=3, foot_segs=0,
                 spine_every=2),
    "lo": dict(ring=None, around=6, disc_rings=2, disc_around=15, feet_gap=None, foot_sides=3, foot_segs=0,
               spine_every=0),
}
# Arm rings: (full spacing in metres, game ring count, low ring count) per kind, and points round an arm (full,
# game, low).
RINGS = {"classic": (0.0015, 11, 6), "sunflower": (0.005, 7, 4), "brittle": (0.0008, 16, 7)}
AROUND = {"classic": (32, 10, 6), "sunflower": (16, 8, 6), "brittle": (12, 6, 6)}
# Feet per row on an arm for the game and low models (the full model: one every feet_gap metres).
FEET = {"classic": (6, 0), "sunflower": (2, 0), "brittle": (0, 0)}
SPINE_GAP = 0.003


def to_b(p):
    return Vector((p.x, -p.z, p.y))


# ---- the knobs: a jittered lattice in the top plane, the same sums as the shader's (integer hash: exact) ----

def hash32(x):
    x &= 0xFFFFFFFF
    x ^= x >> 16
    x = (x * 0x7FEB352D) & 0xFFFFFFFF
    x ^= x >> 15
    x = (x * 0x846CA68B) & 0xFFFFFFFF
    x ^= x >> 16
    return x


def knob_point(i, j, cell):
    seed = (((i + 4096) * 73856093) ^ ((j + 4096) * 19349663)) & 0xFFFFFFFF
    a = hash32(seed)
    jx = float(a & 0xFFFF) / 65535.0
    jy = float((a >> 16) & 0xFFFF) / 65535.0
    return ((i + 0.5 * (j & 1) + 0.6 * jx - 0.3) * cell, (j * 0.866 + 0.5 * jy - 0.25) * cell)


def knob_at(x, z, k):
    """0..1: how far up a knob a point of the top (x, z) is."""
    cell = k["cell"]
    if cell <= 0.0 or k["knob_h"] <= 0.0:
        return 0.0
    j0 = math.floor(z / (0.866 * cell))
    best = 0.0
    for j in (j0 - 1, j0, j0 + 1):
        i0 = math.floor(x / cell - 0.5 * (j & 1))
        for i in (i0 - 1, i0, i0 + 1):
            px, pz = knob_point(i, j, cell)
            d = math.hypot(x - px, z - pz) / k["knob_r"]
            if d < 1.0:
                best = max(best, (1.0 - d * d) ** 2)
    return best


# ---- the shape ----

def arm_dir(a):
    return Vector((math.sin(a), 0.0, -math.cos(a))), Vector((math.cos(a), 0.0, math.sin(a)))


def arm_size(k, u):
    """(half width, height) of the arm `u` metres out from the middle: a taper, rounded off at the tip."""
    L = k["L"]
    t = max(0.0, min(1.0, u / L))
    w = k["w"][0] + (k["w"][1] - k["w"][0]) * t
    h = k["h"][0] + (k["h"][1] - k["h"][0]) * t
    # (broadening into the disc where the arm joins it)
    near = max(0.0, 1.0 - u / (1.6 * k["rd"])) ** 2
    w += k["w"][0] * k["flare"] * near
    h += k["h"][0] * 0.12 * k["flare"] * near
    end = L - k["w"][1]
    if u > end:
        c = math.sqrt(max(0.0, 1.0 - ((u - end) / k["w"][1]) ** 2))
        w *= c
        h *= max(c, 0.0) ** 0.8
    return max(w, 1e-5), max(h, 1e-5)


def section(c, w, h):
    """A point round an arm's cross-section: `c` round from the top of its back (0) by its left side to the middle
    of its underside (half a turn); (across, up) from its underside's middle. Flat beneath, a dome above."""
    s = math.sin(c)
    up = h * max(0.0, min(1.0, (math.cos(c) + 0.72) / 1.72))
    return math.copysign(abs(s) ** 0.85, s) * w, up


def around_angles(count):
    """Angles round an arm: evenly, but with a point always at each side's widest (a quarter turn) and the top."""
    if count < 12:
        # (spent on the outline: the top, the shoulders, the widest point, the edge of the flat underside)
        base = {6: [0.0, 1.2, 2.2], 8: [0.0, 0.8, 1.57, 2.3], 10: [0.0, 0.62, 1.2, 1.7, 2.35]}[count]
        out = base + [math.pi] + [-a for a in reversed(base[1:])]
        return out
    return [-math.pi + TAU * i / count for i in range(count)]


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.data = []
        self.out = []
        self.count = {}

    def add(self, p, uv, part, own=0.0):
        self.verts.append(p)
        self.data.append(((uv[0], 1.0 - uv[1]), (own, 1.0 - part)))
        return len(self.verts) - 1

    def face(self, points, out, name):
        """A face wound so that its front (the side its points go round anticlockwise) is towards `out`."""
        ps = [self.verts[i] for i in points]
        n = Vector((0.0, 0.0, 0.0))
        for i in range(len(ps)):
            n += ps[i].cross(ps[(i + 1) % len(ps)])
        if n.length < 1e-18:
            return
        if n.dot(out) < 0.0:
            points = tuple(reversed(points))
        self.faces.append(tuple(points))
        self.out.append((Vector(out), name))
        self.count[name] = self.count.get(name, 0) + 1


def disc(m, k, d):
    rd, hd, y0 = k["rd"], k["hd"], k["y0"]
    rings, around = d["disc_rings"], d["disc_around"]

    def edge(th):
        # (the brittle star's disc is a rounded pentagon, its corners between the arms)
        return rd * (1.0 + k["lobes"] * math.cos(k["n"] * th + math.pi))

    top = [m.add(Vector((0.0, y0 + hd, 0.0)), (0.0, 1.0), DISC)]
    grid = []
    for r in range(1, rings + 1):
        f = r / rings
        f = 1.0 - (1.0 - f) ** 1.6 if d is DETAIL["full"] else math.sin(f * math.pi * 0.5)
        row = []
        for c in range(around):
            th = TAU * c / around
            rr = edge(th) * f
            y = y0 + hd * max(0.0, 1.0 - f ** 2.4) ** 0.5
            row.append(m.add(Vector((math.sin(th) * rr, y, -math.cos(th) * rr)), (f, (y - y0) / hd), DISC))
        grid.append(row)
    for c in range(around):
        n = (c + 1) % around
        p = m.verts[grid[0][c]]
        m.face((top[0], grid[0][c], grid[0][n]), Vector((0.0, 1.0, 0.0)), "disc")
    for r in range(rings - 1):
        for c in range(around):
            n = (c + 1) % around
            quad = (grid[r][c], grid[r][n], grid[r + 1][n], grid[r + 1][c])
            mid = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((mid.x, mid.y - y0 + 0.3 * hd, mid.z)), "disc")
    under = m.add(Vector((0.0, y0, 0.0)), (0.0, 0.0), DISC)
    for c in range(around):
        n = (c + 1) % around
        m.face((under, grid[-1][c], grid[-1][n]), Vector((0.0, -1.0, 0.0)), "disc")


def ring_places(k, kind, d, which):
    L = k["L"]
    start = k["rd"] * 0.25
    end = L - 0.0004 * L / 0.1
    if which == "full":
        n = max(4, round((end - start) / RINGS[kind][0]))
        qs = [i / n for i in range(n + 1)]
        return [start + (end - start) * (1.0 - (1.0 - q) ** 1.25) for q in qs]
    n = RINGS[kind][1 if which == "game" else 2]
    # (bunched towards the tip, where the outline turns)
    return [start + (end - start) * (1.0 - (1.0 - i / n) ** 1.7) for i in range(n + 1)]


def arm(m, k, kind, d, which, index):
    a = TAU * index / k["n"]
    fwd, side = arm_dir(a)
    up = Vector((0.0, 1.0, 0.0))
    own = index / k["n"]
    y0 = k["y0"]
    angles = around_angles(AROUND[kind][("full", "game", "lo").index(which)])
    us = ring_places(k, kind, d, which)
    grid = []
    for u in us:
        w, h = arm_size(k, u)
        row = []
        for c in angles:
            x, y = section(c, w, h)
            p = fwd * u + side * x + up * (y0 + y)
            if which == "full" and k["knob_h"] > 0.0 and y > 0.25 * h:
                # (the knobs stand out of the back and the upper sides)
                axis = fwd * u + up * (y0 + 0.35 * h)
                p += (p - axis).normalized() * (k["knob_h"] * knob_at(p.x, p.z, k) * min(1.0, (y / h - 0.25) * 3.0))
            row.append(m.add(p, (u / k["L"], y / h), ARM, own))
        grid.append(row)
    na = len(angles)
    for r in range(len(us) - 1):
        _, h = arm_size(k, 0.5 * (us[r] + us[r + 1]))
        for c in range(na):
            n = (c + 1) % na
            quad = (grid[r][c], grid[r][n], grid[r + 1][n], grid[r + 1][c])
            mid = sum((m.verts[q] for q in quad), Vector()) * 0.25
            axis = fwd * fwd.dot(mid) + up * (y0 + 0.35 * h)
            m.face(quad, mid - axis, "arms")
    tip_u = k["L"]
    tip = m.add(fwd * tip_u + up * (y0 + 0.3 * arm_size(k, us[-1])[1]), (1.0, 0.3), ARM, own)
    for c in range(na):
        m.face((tip, grid[-1][c], grid[-1][(c + 1) % na]), fwd, "arms")
    feet(m, k, kind, d, which, fwd, side, own)
    if k["spines"] and d["spine_every"]:
        spines(m, k, d, fwd, side, own)


def tube(m, part, name, root, tip, r0, r1, sides, segs, uvx, own, close=True):
    along = (tip - root).normalized()
    ref = Vector((0.0, 1.0, 0.0)) if abs(along.y) < 0.9 else Vector((1.0, 0.0, 0.0))
    a = along.cross(ref).normalized()
    b = along.cross(a).normalized()
    rows = []
    for i in range(segs + 1):
        # (no segments: a pyramid, its root ring straight to its tip)
        t = i / segs * (0.85 if close else 1.0) if segs else 0.0
        here = root + (tip - root) * t
        r = r0 + (r1 - r0) * t
        rows.append((here, [m.add(here + (a * math.cos(TAU * s / sides) + b * math.sin(TAU * s / sides)) * r,
                                  (uvx, t), part, own) for s in range(sides)]))
    for i in range(segs):
        axis = (rows[i][0] + rows[i + 1][0]) * 0.5
        for s in range(sides):
            n = (s + 1) % sides
            quad = (rows[i][1][s], rows[i][1][n], rows[i + 1][1][n], rows[i + 1][1][s])
            mid = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, mid - axis, name)
    point = m.add(tip, (uvx, 1.0), part, own)
    for s in range(sides):
        m.face((point, rows[-1][1][s], rows[-1][1][(s + 1) % sides]), tip - rows[-1][0], name)


def feet(m, k, kind, d, which, fwd, side, own):
    y0 = k["y0"]
    first = k["rd"] * 0.55
    last = k["L"] * 0.9
    if which == "full":
        count = max(2, round((last - first) / max(d["feet_gap"] * k["L"] / 0.135, 0.0012)))
    else:
        count = FEET[kind][0 if which == "game" else 1]
    if count == 0:
        return
    radius = max(0.0004, k["w"][0] * 0.07)
    for i in range(count):
        u = first + (last - first) * (i + 0.5) / count
        w, _ = arm_size(k, u)
        for row in (-1.0, 1.0):
            across = row * w * (0.32 if i % 2 else 0.22)
            root = fwd * u + side * across + Vector((0.0, y0 + 0.0008, 0.0))
            tip = fwd * (u + 0.0008 * row) + side * (across * 1.25) + Vector((0.0, 0.0003, 0.0))
            tube(m, FOOT, "feet", root, tip, radius, radius * 0.8, d["foot_sides"], d["foot_segs"], u / k["L"], own)


def spines(m, k, d, fwd, side, own):
    """The brittle star's arm spines: a pair to each side at every segment, glassy, standing out and forward."""
    y0 = k["y0"]
    u = k["rd"] * 1.1
    seg = 0
    while u < k["L"] * 0.94:
        if seg % d["spine_every"] == 0:
            w, h = arm_size(k, u)
            for sx in (-1.0, 1.0):
                for lift, reach in ((0.65, 3.2), (0.3, 2.6)) if d["spine_every"] == 1 else ((0.5, 3.0),):
                    root = fwd * u + side * (sx * w * 0.7) + Vector((0.0, y0 + lift * h, 0.0))
                    out = (side * sx + fwd * 0.35 + Vector((0.0, 0.35 * lift, 0.0))).normalized()
                    length = reach * w + 0.0008
                    tube(m, SPINE, "spines", root, root + out * length, w * 0.16, 0.0, 3, 0, u / k["L"], own)
        u += SPINE_GAP
        seg += 1


def make(kind, which):
    k = KINDS[kind]
    d = DETAIL[which]
    m = Mesh()
    disc(m, k, d)
    for i in range(k["n"]):
        arm(m, k, kind, d, which, i)
    name = "starfish_%s%s" % (kind, "" if which == "full" else "_" + which)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) for p in m.verts], [], m.faces)
    # (every layer made first, then each looked up by name: making one moves the others)
    mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.new(name="UV2")
    uv = mesh.uv_layers["UVMap"].data
    uv2 = mesh.uv_layers["UV2"].data
    for poly in mesh.polygons:
        for corner, vi in enumerate(poly.vertices):
            dd = m.data[vi]
            uv[poly.loop_start + corner].uv = dd[0]
            uv2[poly.loop_start + corner].uv = dd[1]
    material = bpy.data.materials.get("starfish") or bpy.data.materials.new("starfish")
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.8, 0.4, 0.15, 1.0)
    material.diffuse_color = (0.8, 0.4, 0.15, 1.0)
    mesh.materials.append(material)
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    parts = {}
    for poly, (out, group) in zip(mesh.polygons, m.out):
        parts[group] = parts.get(group, 0) + len(poly.vertices) - 2
    print("BUILT %s verts=%d tris=%d %s" % (name, len(mesh.vertices), tris, parts))
    winding(name, mesh, m)
    return obj


def winding(name, mesh, m):
    """Nothing inside out: every skin faces away from its own middle line (Blender's front is the side a face's
    normal is on)."""
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
        export_animations=False, export_texcoords=True, export_normals=True,
    )


def render(folder, made):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_cavity = True
    scene.display.shading.show_backface_culling = True
    scene.render.resolution_x, scene.render.resolution_y = 1000, 700
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    for (kind, which), obj in made.items():
        k = KINDS[kind]
        span = 2.9 * k["L"]
        views = [("top", (0.001, 0, 1), span), ("side", (1, 0, 0.0001), span), ("under", (0.001, 0, -1), span),
                 ("quarter", (0.8, -0.9, 0.7), span)]
        for other in made.values():
            other.hide_render = other is not obj
        for view, direction, frame in views:
            if which != "full" and view in ("under", "quarter"):
                continue
            offset = Vector(direction).normalized() * 40.0
            camera.data.ortho_scale = frame
            camera.location = Vector((0, 0, 0.3 * k["hd"])) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s_%s_%s.png" % (kind, which, view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    os.makedirs(OUT, exist_ok=True)
    made = {}
    for row, kind in enumerate(KINDS):
        for col, which in enumerate(("full", "game", "lo")):
            obj = make(kind, which)
            made[(kind, which)] = obj
            export_one(obj, os.path.join(OUT, obj.name + ".glb"))
    # (laid out side by side in the .blend: a row per kind, full, game and low along it)
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, made)
    for (kind, which), obj in made.items():
        obj.hide_render = False
        obj.location = Vector((("full", "game", "lo").index(which) * 0.7, -list(KINDS).index(kind) * 0.7, 0.0))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "starfish.blend"))


if __name__ == "__main__":
    main()
