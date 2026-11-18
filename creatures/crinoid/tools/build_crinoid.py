"""Builds the crinoids (creatures/crinoid) and exports them for Godot.

Run from the game's root:
    blender --background --factory-startup --python creatures/crinoid/tools/build_crinoid.py
    blender --background --factory-startup --python creatures/crinoid/tools/build_crinoid.py -- <preview folder>

Three kinds, each three models (one still mesh, one surface each):
    models/crinoid_<kind>.glb        the full model: every pinnule a thin strip of its own
    models/crinoid_<kind>_game.glb   the game model (Twilight Princess weight): the pinnules drawn on cards
    models/crinoid_<kind>_lo.glb     the low model: cards too, fewer pieces
and the editable tools/crinoid.blend with all nine (this folder has a .gdignore).

The kinds, built from what the animals look like (no picture traced):
- feather_star: a feather star of ten arms (a comatulid, after Florometra of the California coast): a small cup
  perched on a ring of curved jointed cirri that grip the ground, ten feathery arms rising from its rim.
- feather_star_twenty: the same with twenty arms.
- sea_lily: a stalked crinoid (an isocrinid): the crown of ten arms on a long jointed stem, whorls of cirri at its
  nodes, standing from a small holdfast.
Each arm is a jointed stem with a comb of pinnules along both sides, alternating, standing up from the arm in a
V (a trough), pointing forward along it.

Everything here is in Godot space (metres, Y up, X its left side, -Z its front) until it is written out. The
origin is on the ground under the middle of the cup (or of the stem). Arm 0 points to -Z, the others follow
round towards +X. At rest each arm runs straight from its root on the cup's rim, out and up at ARM_RISE; the
shader bends it (crinoid.gdshader), working out each point's place along its arm from where it is.

The pinnules: pinnule j on side sigma (+1 the arm's left, -1 its right) stands at s_j = PIN_FROM + j * PIN_GAP
(+ PIN_GAP / 2 on the right) along its arm, PIN_LENGTH * pin_profile(s_j / arm length) long, at PIN_ANGLE to the
arm, in the plane tipped up by PIN_TILT from the arm's side. The card shader draws exactly those (`pinnule`).

What a point is, for the shader:
    UV2.y the part: 0 the cup, 1 an arm's stem, 2 a pinnule (a strip), 3 a cirrus (on the cup), 4 a card of
        pinnules on an arm's left, 5 on its right, 6 the stalk, 7 a cirrus on the stalk, 8 the holdfast.
    UV2.x on anything of an arm: which arm (k / n); otherwise 0.
    UV, on an arm's stem: x how far along it (of its length), y round it; on a pinnule: x where along its arm it
        stands (of the arm's length), y from its root (0) to its tip (1); on a card: x how far along the arm
        (of its length), y how far out from the arm (of CARD_WIDTH); on a cirrus: y from its root (0) to its
        tip (1); on the stalk: y how high (of its height).
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
CUP, ARM, PINNULE, CIRRUS, CARD_L, CARD_R, STALK, STALK_CIRRUS, HOLDFAST = range(9)
WHICH = ("full", "game", "lo")

PIN_GAP = 0.0028
PIN_ANGLE = 0.8
PIN_TILT = 0.6
PIN_FROM_OF = 0.05

# n arms; La each arm's length; rise its angle above level at its root; cup: (radius, height of its middle,
# how far it reaches below and above); root: where the arms leave it (radius, height); pin: the longest pinnule;
# arm radius at root and tip; cirri on the cup (full, game, low); stalk: its height (0: none).
KINDS = {
    "feather_star": dict(n=10, La=0.15, rise=0.6, cup=(0.0075, 0.019, 0.006, 0.003), root=(0.0065, 0.0205),
                         pin=0.016, arm_r=(0.0013, 0.0005), cirri=(20, 10, 5), stalk=0.0),
    "feather_star_twenty": dict(n=20, La=0.14, rise=0.6, cup=(0.0085, 0.019, 0.006, 0.003), root=(0.0075, 0.0205),
                                pin=0.014, arm_r=(0.0012, 0.0005), cirri=(20, 10, 5), stalk=0.0),
    "sea_lily": dict(n=10, La=0.13, rise=0.75, cup=(0.0085, 0.42, 0.007, 0.002), root=(0.0075, 0.4215),
                     pin=0.014, arm_r=(0.0014, 0.0005), cirri=(0, 0, 0), stalk=0.42),
}
# Per model: arm segments, sides round an arm, cup rings and points round, cirrus segments and sides, stalk
# segments and sides, whorls' cirri and their segments.
DETAIL = {
    "full": dict(arm_segs=56, arm_sides=6, cup=(14, 24), cirrus=(12, 5), stalk=(140, 8), whorl=(5, 10)),
    "game": dict(arm_segs=8, arm_sides=3, cup=(4, 8), cirrus=(3, 3), stalk=(14, 4), whorl=(5, 2)),
    "lo": dict(arm_segs=4, arm_sides=3, cup=(3, 6), cirrus=(2, 3), stalk=(6, 3), whorl=(0, 0)),
}
# The twenty-armed star's game model has fewer arm segments, to keep in its budget.
SEGS_TWENTY_GAME = 7
WHORL_GAP = 0.06


def to_b(p):
    return Vector((p.x, -p.z, p.y))


def pin_profile(t):
    """How long a pinnule is (of the longest) at `t` of the way along its arm."""
    return min(1.0, (t + 0.02) / 0.15) * (1.0 - 0.55 * t)


def frame(k, a):
    """An arm's root and its way (f), up from it (n: up and in), and its side (s: its left)."""
    out = Vector((math.sin(a), 0.0, -math.cos(a)))
    up = Vector((0.0, 1.0, 0.0))
    f = out * math.cos(k["rise"]) + up * math.sin(k["rise"])
    n = -out * math.sin(k["rise"]) + up * math.cos(k["rise"])
    s = Vector((math.cos(a), 0.0, math.sin(a)))
    root = out * k["root"][0] + up * k["root"][1]
    return root, f, n, s


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.data = []
        self.out = []
        self.count = {}

    def add(self, p, uv, part, arm=0.0):
        self.verts.append(p)
        self.data.append(((uv[0], 1.0 - uv[1]), (arm, 1.0 - part)))
        return len(self.verts) - 1

    def face(self, points, out, name):
        """A face wound so that its front (the side its points go round anticlockwise) is towards `out`."""
        ps = [self.verts[i] for i in points]
        n = Vector((0.0, 0.0, 0.0))
        for i in range(len(ps)):
            n += ps[i].cross(ps[(i + 1) % len(ps)])
        if n.length < 1e-22:
            return
        if n.dot(out) < 0.0:
            points = tuple(reversed(points))
        self.faces.append(tuple(points))
        self.out.append((Vector(out), name))
        self.count[name] = self.count.get(name, 0) + 1


def tube(m, part, name, curve, radius, sides, segs, uvx, arm=0.0, close=True, uv_along=None):
    """A tube round `curve(t)`, t 0 to 1, `radius(t)` thick, closed by a point at its end, open at its start
    (which is sunk in what it grows from)."""
    rows = []
    prev_a = None
    for i in range(segs + 1):
        t = i / segs * (0.96 if close else 1.0)
        here = curve(t)
        along = (curve(min(t + 0.01, 1.0)) - curve(max(t - 0.01, 0.0))).normalized()
        ref = prev_a if prev_a is not None else (Vector((0.0, 1.0, 0.0)) if abs(along.y) < 0.9 else Vector((1.0, 0.0, 0.0)))
        b = along.cross(ref).normalized()
        a = b.cross(along).normalized()
        prev_a = a
        r = radius(t)
        v = uv_along(t) if uv_along else t
        rows.append((here, [m.add(here + (a * math.cos(TAU * j / sides) + b * math.sin(TAU * j / sides)) * r,
                                  (uvx(t), v) if callable(uvx) else (uvx, v), part, arm) for j in range(sides)]))
    for i in range(segs):
        axis = (rows[i][0] + rows[i + 1][0]) * 0.5
        for j in range(sides):
            q = (j + 1) % sides
            quad = (rows[i][1][j], rows[i][1][q], rows[i + 1][1][q], rows[i + 1][1][j])
            mid = sum((m.verts[x] for x in quad), Vector()) * 0.25
            m.face(quad, mid - axis, name)
    if close:
        end = curve(1.0)
        v = uv_along(1.0) if uv_along else 1.0
        tip = m.add(end, ((uvx(1.0) if callable(uvx) else uvx), v), part, arm)
        for j in range(sides):
            m.face((tip, rows[-1][1][j], rows[-1][1][(j + 1) % sides]), end - rows[-1][0], name)


def bezier(p0, p1, p2, p3):
    def curve(t):
        a = 1.0 - t
        return p0 * a ** 3 + p1 * (3 * a * a * t) + p2 * (3 * a * t * t) + p3 * t ** 3
    return curve


def cup(m, k, d):
    rings, around = d["cup"]
    r, y, below, above = k["cup"]
    middle = Vector((0.0, y, 0.0))
    top = m.add(Vector((0.0, y + above, 0.0)), (0.5, 0.0), CUP)
    bottom = m.add(Vector((0.0, y - below, 0.0)), (0.5, 1.0), CUP)
    grid = []
    for i in range(1, rings):
        th = math.pi * i / rings
        c = math.cos(th)
        grid.append([m.add(Vector((math.sin(th) * r * math.cos(TAU * j / around), y + (above if c > 0 else below) * c,
                                   math.sin(th) * r * math.sin(TAU * j / around))), (j / around, i / rings), CUP)
                     for j in range(around)])
    for j in range(around):
        q = (j + 1) % around
        m.face((top, grid[0][j], grid[0][q]), Vector((0, 1, 0)), "cup")
        m.face((bottom, grid[-1][j], grid[-1][q]), Vector((0, -1, 0)), "cup")
    for i in range(len(grid) - 1):
        for j in range(around):
            q = (j + 1) % around
            quad = (grid[i][j], grid[i][q], grid[i + 1][q], grid[i + 1][j])
            mid = sum((m.verts[x] for x in quad), Vector()) * 0.25
            m.face(quad, mid - middle, "cup")


def cirri(m, k, d, w):
    count = k["cirri"][w]
    segs, sides = d["cirrus"]
    r, y, below, _ = k["cup"]
    every = k["cirri"][0]
    for c in range(count):
        # (the lighter models' cirri are some of the full model's, in the same places)
        i = c * (every // count)
        a = TAU * (i + 0.5 * (i % 2)) / every
        out = Vector((math.sin(a), 0.0, -math.cos(a)))
        tilt = 0.55 + 0.35 * (i % 2)
        root = out * (r * math.sin(tilt + 1.2) * 0.8) + Vector((0.0, y - below * 0.6, 0.0))
        reach = 0.017 + 0.004 * ((i * 7) % 3)
        p1 = root + out * 0.008 + Vector((0.0, -0.002, 0.0))
        p2 = out * (r + reach) + Vector((0.0, 0.006, 0.0))
        p3 = out * (r + reach * 0.82) + Vector((0.0, 0.0004, 0.0))
        tube(m, CIRRUS, "cirri", bezier(root, p1, p2, p3), lambda t: 0.00065 * (1.0 - 0.45 * t), sides, segs, 0.0)


def arm(m, k, d, w, index, kind):
    a = TAU * index / k["n"]
    root, f, n, s = frame(k, a)
    own = index / k["n"]
    La = k["La"]
    segs = SEGS_TWENTY_GAME if (kind == "feather_star_twenty" and w == 1) else d["arm_segs"]
    r0, r1 = k["arm_r"]
    tube(m, ARM, "arms", lambda t: root + f * (La * t), lambda t: r0 + (r1 - r0) * t, d["arm_sides"], segs,
         lambda t: t, own, uv_along=lambda t: 0.0)
    pin_from = PIN_FROM_OF * La
    sinb, cosb = math.sin(PIN_ANGLE), math.cos(PIN_ANGLE)
    for sigma, part in ((1.0, CARD_L), (-1.0, CARD_R)):
        # the plane the pinnules of this side lie in: along the arm, and out to the side tipped up
        side = s * (sigma * math.cos(PIN_TILT)) + n * math.sin(PIN_TILT)
        if w == 0:
            j = 0
            while True:
                at = pin_from + (j + (0.0 if sigma > 0 else 0.5)) * PIN_GAP
                if at > La * 0.985:
                    break
                length = k["pin"] * pin_profile(at / La)
                way = f * cosb + side * sinb
                across = way.cross(f.cross(side)).normalized()
                base = root + f * at
                tip = base + way * length
                # a strip, tapering, in two lengths
                rows = []
                for t, wide in ((0.0, 0.00034), (0.5, 0.00026), (1.0, 0.00008)):
                    p = base + (tip - base) * t
                    rows.append([m.add(p + across * wide, (at / La, t), PINNULE, own),
                                 m.add(p - across * wide, (at / La, t), PINNULE, own)])
                normal = f.cross(side).normalized()
                for r in range(2):
                    m.face((rows[r][0], rows[r][1], rows[r + 1][1], rows[r + 1][0]), normal, "pinnules")
                j += 1
        else:
            # a card the pinnules are drawn on: from the arm's middle out, along the whole arm
            width = card_width(k)
            cs = segs
            for i in range(cs):
                t0 = i / cs
                t1 = (i + 1) / cs
                s0 = La * (0.02 + 1.02 * t0)
                s1 = La * (0.02 + 1.02 * t1)
                quad = []
                for at, q in ((s0, 0.0), (s1, 0.0), (s1, 1.0), (s0, 1.0)):
                    quad.append(m.add(root + f * at + side * (width * q), (at / La, q), part, own))
                m.face(tuple(quad), f.cross(side), "cards")


def card_width(k):
    return k["pin"] * math.sin(PIN_ANGLE) * 1.04


def stalk(m, k, d, w):
    H = k["stalk"]
    segs, sides = d["stalk"]
    top = k["cup"][1] - k["cup"][2] * 0.5
    tube(m, STALK, "stalk", lambda t: Vector((0.0, top * t, 0.0)),
         lambda t: 0.0042 - 0.0012 * t, sides, segs, 0.0, close=False, uv_along=lambda t: t * top / H)
    # the holdfast: a low flared foot
    rings, around = 3, max(sides * 2, 6)
    centre = Vector((0.0, 0.0, 0.0))
    grid = []
    for i, (rad, y) in enumerate(((0.012, 0.0), (0.009, 0.002), (0.005, 0.006))):
        grid.append([m.add(Vector((rad * math.cos(TAU * j / around), y, rad * math.sin(TAU * j / around))), (j / around, 0.0),
                           HOLDFAST) for j in range(around)])
    for i in range(len(grid) - 1):
        for j in range(around):
            q = (j + 1) % around
            quad = (grid[i][j], grid[i][q], grid[i + 1][q], grid[i + 1][j])
            mid = sum((m.verts[x] for x in quad), Vector()) * 0.25
            m.face(quad, Vector((mid.x, 0.4 * mid.y + 0.002, mid.z)), "holdfast")
    per, csegs = d["whorl"]
    if per == 0:
        return
    y = 0.1
    whorl = 0
    while y < top - 0.03:
        for i in range(per):
            a = TAU * (i + 0.5 * (whorl % 2)) / per
            out = Vector((math.sin(a), 0.0, -math.cos(a)))
            root = Vector((0.0, y, 0.0)) + out * 0.002
            length = 0.03 * (0.75 + 0.25 * y / top)
            p1 = root + out * (length * 0.45) + Vector((0.0, length * 0.05, 0.0))
            p2 = root + out * (length * 0.85) + Vector((0.0, -length * 0.2, 0.0))
            p3 = root + out * (length * 0.95) + Vector((0.0, -length * 0.55, 0.0))
            tube(m, STALK_CIRRUS, "stalk cirri", bezier(root, p1, p2, p3), lambda t: 0.0006 * (1.0 - 0.4 * t),
                 3 if w else 4, csegs, 0.0)
        y += WHORL_GAP
        whorl += 1


def make(kind, w):
    k = KINDS[kind]
    d = DETAIL[WHICH[w]]
    m = Mesh()
    cup(m, k, d)
    if k["stalk"] > 0.0:
        stalk(m, k, d, w)
    else:
        cirri(m, k, d, w)
    for i in range(k["n"]):
        arm(m, k, d, w, i, kind)
    name = "crinoid_%s%s" % (kind, "" if w == 0 else "_" + WHICH[w])
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
    material = bpy.data.materials.get("crinoid") or bpy.data.materials.new("crinoid")
    material.use_nodes = True
    bsdf = next(x for x in material.node_tree.nodes if x.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.9, 0.7, 0.1, 1.0)
    material.diffuse_color = (0.9, 0.7, 0.1, 1.0)
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
    xs = [math.hypot(p.x, p.z) for p in m.verts]
    print("SHAPE %s: reach %.4f, height %.4f, card width %.5f, pin from %.5f" % (
        name, max(xs), max(p.y for p in m.verts), card_width(k), PIN_FROM_OF * k["La"]))
    winding(name, mesh, m)
    return obj


def winding(name, mesh, m):
    """Nothing inside out: every closed skin faces away from its own middle line; the strips and cards (drawn
    from both sides) face up off the arm (Blender's front is the side a face's normal is on)."""
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
    scene.render.resolution_x, scene.render.resolution_y = 900, 900
    scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    for (kind, w), obj in made.items():
        if w:
            continue
        k = KINDS[kind]
        span = 0.36 if not k["stalk"] else 0.6
        target = Vector((0, 0, 0.03 if not k["stalk"] else 0.3))
        for other in made.values():
            other.hide_render = other is not obj
        for view, direction in (("side", (1, 0, 0.0001)), ("top", (0.001, 0, 1)), ("quarter", (0.8, -0.9, 0.6))):
            offset = Vector(direction).normalized() * 40.0
            camera.data.ortho_scale = span
            camera.location = target + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s_%s_%s.png" % (kind, WHICH[w], view))
            bpy.ops.render.render(write_still=True)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    os.makedirs(OUT, exist_ok=True)
    made = {}
    for kind in KINDS:
        for w in range(3):
            obj = make(kind, w)
            made[(kind, w)] = obj
            export_one(obj, os.path.join(OUT, obj.name + ".glb"))
    if PREVIEW:
        os.makedirs(PREVIEW, exist_ok=True)
        render(PREVIEW, made)
    # (laid out side by side in the .blend: a row per kind, full, game and low along it)
    for (kind, w), obj in made.items():
        obj.hide_render = False
        obj.location = Vector((w * 0.4, -list(KINDS).index(kind) * 0.4, 0.0))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "crinoid.blend"))


if __name__ == "__main__":
    main()
