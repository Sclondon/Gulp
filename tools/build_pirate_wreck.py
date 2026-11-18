"""Builds the pirate ship wreck: a wooden three-master of about 1700 lying heeled on the sand, with its treasure.

    "C:/Program Files/Blender Foundation/Blender 4.3/blender.exe" -b --factory-startup --python tools/build_pirate_wreck.py [-- --no-bake]

Writes tools/blend/pirate_wreck.blend (editable), models/pirate_wreck.glb, models/pirate_wreck.json (collision
spheres, swim-route check points, camera views for tests/pirate_view.gd) and textures/pirate_atlas.png.
The user (2026-11-18): "and another location should be pirate ship wreck". tools/PIRATE_WRECK.md is the design sheet.

Built as the control panel is (tools/build_panel.py, whose top part is run from here for its helpers and its
procedural `material`): low-poly parts, every one a closed solid, unwrapped into one atlas that Cycles bakes
(colour, light from the surface, shadow where parts meet). The game draws it unlit with shaders/pirate_wreck.gdshader.

Two frames. The ship is built upright in her own frame (Blender: Z up, bow +Y, starboard +X, keel bottom at z = 0,
amidships y = 0), then laid as she lies (`LIE`: heeled 20 degrees to starboard about the keel, bow up 6.5 degrees
about the keel's middle). What lies on the sand is built in the world frame (z = 0 is the sand). The glTF exporter
turns Blender +Y into Godot -Z: in Godot the bow points to -Z, starboard +X, and the origin is the middle of the
keel's resting line at the sand.

The hull is one solid: a loft of waterlines trimmed to the sheer, with the cabin, decks and hold cut out of it by
Boolean (exact) and the openings cut through it. Collision spheres are fitted to the solid parts here (see
`fit_spheres`): never more than SLACK_IN into a space a fish swims in, never more than BULGE out into open sea,
never into a swim route.
"""
import os
import sys
import json
import math
import random

MY_DIR = os.path.dirname(os.path.abspath(__file__))
_source = open(os.path.join(MY_DIR, "build_panel.py")).read()
exec(compile(_source.split("# --- The helm housing")[0], "build_panel.py", "exec"))

import bpy
import bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

HERE = MY_DIR
GLB = os.path.normpath(os.path.join(HERE, "..", "models", "pirate_wreck.glb"))
DATA = os.path.normpath(os.path.join(HERE, "..", "models", "pirate_wreck.json"))
BLEND = os.path.join(HERE, "blend", "pirate_wreck.blend")
ATLAS = os.path.normpath(os.path.join(HERE, "..", "textures", "pirate_atlas.png"))
ATLAS_SIZE = 2048
BAKE = "--no-bake" not in sys.argv
RNG = random.Random(1700)

# --- How she lies.
HEEL = math.radians(20.0)     # to starboard
PITCH = math.radians(6.5)     # bow up
LIE = Matrix.Rotation(PITCH, 4, "X") @ Matrix.Rotation(HEEL, 4, "Y")

# --- Her heights (ship frame, metres; the keel's bottom is z = 0).
WALL = 0.5           # the hull's side: frames, planking and ceiling
HOLD = (0.8, 3.3)    # the forward hold: its floor (sand and ballast) and the gun deck's underside
GUN = (3.75, 6.45)   # the gun deck: its planks and the upper deck's underside
UPPER = 6.9          # the upper deck (the waist and the great cabin's floor)
CABIN_TOP = 9.3      # the quarterdeck's underside
QD = 9.75            # the quarterdeck
FC = 9.6             # the forecastle deck
PORT_Z = (4.35, 5.0) # the gun ports' sill and head
PORTS_Y = (-13.5, -10.5, -7.5, -4.5, -1.5, 1.5, 4.5, 7.5, 10.5)
MAINMAST_Y = 1.0
FOREMAST_Y = 10.6
MIZZEN_Y = -13.6
HOARD = Vector((0.3, 9.8, HOLD[0]))   # the middle of the treasure's heap, on the hold's floor

# --- Collision: spheres.
GRID = 0.3
SLACK_IN = 0.6       # how far a sphere may reach into a cabin, deck or hold
BULGE = 1.2          # how far into open sea
COVER = 0.08         # a solid point counts as covered this far outside a sphere (no fish is this thin)
# the parts that stop a swimmer (by name, less its number): the hull and its big timbers, masts and spars, guns,
# the figurehead, the rocks, the drift, barrels and the anchor; small trim does not
SOLID_NAMES = {"Hull", "Keel", "Stem", "Sternpost", "Rudder", "Rib", "Knee", "MermaidBody", "MermaidTail", "Gallery",
               "MainStump", "Foremast", "Mizzen", "ForemastTopmast", "MizzenTopmast", "ForemastTop", "MizzenTop", "ForemastYard",
               "MizzenYard", "Bowsprit", "MainMast", "MainTopmast", "MainYard", "MainTop", "BowRock", "SandRock", "Drift", "Barrel",
               "AnchorShank", "Stock", "SandGun", "Slid", "Fallen", "Gun", "Spar"}
R_CAP = 2.5
ROUTE_R = 0.92       # the swim routes' tube: radius, and lines either side of it
ROUTE_SIDE = 0.25


def smoothstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


def lerp(a, b, t):
    return a + (b - a) * t


# --- Materials (procedural, for the bake). `seams`: plank seams, (axis, spacing).
def paint(name, colour, patch_a=None, patch_b=None, size=1.6, rough=0.8, seams=None, glow=None):
    made = material(name, colour, patch_a, patch_b, size, rough)
    tree = made.node_tree
    shader = next(n for n in tree.nodes if n.type == "BSDF_PRINCIPLED")
    if seams:
        axis, spacing = seams
        place = tree.nodes.new("ShaderNodeTexCoord")
        split = tree.nodes.new("ShaderNodeSeparateXYZ")
        tree.links.new(place.outputs["Object"], split.inputs["Vector"])
        over = tree.nodes.new("ShaderNodeMath")
        over.operation = "DIVIDE"
        tree.links.new(split.outputs[axis], over.inputs[0])
        over.inputs[1].default_value = spacing
        frac = tree.nodes.new("ShaderNodeMath")
        frac.operation = "FRACT"
        tree.links.new(over.outputs[0], frac.inputs[0])
        # a dark line at each seam
        line = tree.nodes.new("ShaderNodeMapRange")
        line.interpolation_type = "SMOOTHSTEP"
        line.inputs["From Min"].default_value = 0.0
        line.inputs["From Max"].default_value = 0.09
        line.inputs["To Min"].default_value = 0.45
        line.inputs["To Max"].default_value = 1.0
        tree.links.new(frac.outputs[0], line.inputs["Value"])
        # each plank a little lighter or darker than the next
        whole = tree.nodes.new("ShaderNodeMath")
        whole.operation = "FLOOR"
        tree.links.new(over.outputs[0], whole.inputs[0])
        noise = tree.nodes.new("ShaderNodeTexWhiteNoise")
        noise.noise_dimensions = "1D"
        tree.links.new(whole.outputs[0], noise.inputs["W"])
        tone = tree.nodes.new("ShaderNodeMapRange")
        tone.inputs["To Min"].default_value = 0.8
        tone.inputs["To Max"].default_value = 1.12
        tree.links.new(noise.outputs["Value"], tone.inputs["Value"])
        both = tree.nodes.new("ShaderNodeMath")
        both.operation = "MULTIPLY"
        tree.links.new(line.outputs["Result"], both.inputs[0])
        tree.links.new(tone.outputs["Result"], both.inputs[1])
        mix = tree.nodes.new("ShaderNodeMixRGB")
        mix.blend_type = "MULTIPLY"
        mix.inputs["Fac"].default_value = 1.0
        base = shader.inputs["Base Color"]
        if base.links:
            tree.links.new(base.links[0].from_socket, mix.inputs["Color1"])
        else:
            mix.inputs["Color1"].default_value = base.default_value
        tree.links.new(both.outputs[0], mix.inputs["Color2"])
        tree.links.new(mix.outputs["Color"], base)
    if glow:
        shader.inputs["Emission Color"].default_value = (*glow[0], 1.0)
        shader.inputs["Emission Strength"].default_value = glow[1]
    return made


# (the concept art, tools/art_src/concept_pirate_wreck.jpg: warm honey-brown timber, weathered paler in patches and
# greened with weed, darker brown below the lower wale, gilt trim, white sand)
TIMBER = paint("timber", (0.36, 0.19, 0.06), (0.2, 0.16, 0.05), (0.48, 0.31, 0.13), 2.2, seams=("Z", 0.34))
TAR = paint("tar", (0.11, 0.06, 0.03), (0.07, 0.08, 0.04), (0.18, 0.12, 0.07), 2.5, seams=("Z", 0.34))
DECK = paint("deck", (0.3, 0.19, 0.09), (0.42, 0.36, 0.25), (0.15, 0.14, 0.06), 2.0, seams=("X", 0.28))
INNER = paint("inner", (0.12, 0.07, 0.035), (0.08, 0.08, 0.04), (0.18, 0.11, 0.05), 1.5, seams=("Z", 0.34))
CARVE = paint("carve", (0.45, 0.3, 0.09), (0.3, 0.18, 0.06), (0.16, 0.17, 0.07), 0.7, 0.5)
FIGURE = paint("figure", (0.36, 0.38, 0.32), (0.22, 0.27, 0.2), (0.46, 0.45, 0.4), 0.6)
LIDRED = paint("lidred", (0.28, 0.05, 0.025), (0.17, 0.05, 0.03), (0.32, 0.14, 0.06), 0.6)
RUST = paint("rust", (0.1, 0.05, 0.03), (0.05, 0.04, 0.035), (0.2, 0.09, 0.04), 0.6)
BRONZE = paint("bronze", (0.07, 0.16, 0.12), (0.1, 0.07, 0.035), (0.17, 0.28, 0.21), 0.5, 0.5)
ROPE = paint("rope", (0.13, 0.11, 0.075), (0.07, 0.08, 0.05), None, 1.0)
SAIL = paint("sail", (0.24, 0.2, 0.14), (0.13, 0.12, 0.07), (0.32, 0.28, 0.2), 1.0)
FLAG = paint("flag", (0.012, 0.012, 0.012), (0.03, 0.03, 0.025), None, 0.5)
BONE = paint("bone", (0.55, 0.52, 0.42))
SAND = paint("sand", (0.25, 0.27, 0.27), (0.22, 0.24, 0.24), (0.29, 0.31, 0.31), 3.0)
ROCK = paint("rock", (0.14, 0.13, 0.12), (0.08, 0.1, 0.06), (0.22, 0.21, 0.19), 1.2)
STAVE = paint("stave", (0.17, 0.12, 0.07), (0.1, 0.11, 0.06), (0.22, 0.18, 0.12), 0.8)
GLASS = paint("glass", (0.03, 0.06, 0.05), None, None, 1.0, 0.2)
HOLE = paint("hole", (0.004, 0.004, 0.004))
GOLD = paint("gold", (0.75, 0.48, 0.1), (0.95, 0.68, 0.2), (0.55, 0.32, 0.06), 0.25, 0.3, glow=((1.0, 0.62, 0.18), 0.7))
RUBY = paint("ruby", (0.5, 0.02, 0.03), glow=((0.9, 0.05, 0.05), 0.8))
EMERALD = paint("emerald", (0.03, 0.4, 0.12), glow=((0.05, 0.8, 0.2), 0.6))

# --- The parts: every one an object, kept with what it is.
PARTS = []    # dicts: obj, frame ("ship"/"world"), group ("hull"/"rig"/"treasure"), weight (texels), solid, look
CUTTERS = []  # the hull's cutters (spaces a fish swims in), ship frame


def keep_part(obj, group="hull", frame="ship", weight=1.0, solid=True, look="plain"):
    PARTS.append({"obj": obj, "group": group, "frame": frame, "weight": weight, "solid": solid, "look": look})
    return obj


def mesh_object(name, verts, faces, mat, face_mats=None, fix=True):
    """A closed solid from points and faces: welded, its faces turned outwards (the volume it encloses must come
    out positive). `face_mats`: a material for each face (else `mat` for all)."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    obj = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(obj)
    mats = [mat]
    if face_mats:
        for m in face_mats:
            if m not in mats:
                mats.append(m)
    for m in mats:
        me.materials.append(m)
    if face_mats:
        for poly, m in zip(me.polygons, face_mats):
            poly.material_index = mats.index(m)
    if fix:
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        if bm.calc_volume(signed=True) < 0.0:
            bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
    return obj


def loft(name, rings, mat, closed=True, cap=True, face_mat=None):
    """Joins rings of points (each the same count, each a loop if `closed`) and caps both ends."""
    verts = []
    faces = []
    mats = []
    n = len(rings[0])
    for r in rings:
        verts.extend(r)
    for k in range(len(rings) - 1):
        for i in range(n if closed else n - 1):
            j = (i + 1) % n
            a, b, c, d = k * n + i, k * n + j, (k + 1) * n + j, (k + 1) * n + i
            faces.append((a, b, c, d))
            mats.append(face_mat(k, i) if face_mat else mat)
    if cap:
        faces.append(tuple(range(n))[::-1])
        mats.append(face_mat(-1, 0) if face_mat else mat)
        last = (len(rings) - 1) * n
        faces.append(tuple(range(last, last + n)))
        mats.append(face_mat(len(rings), 0) if face_mat else mat)
    return mesh_object(name, verts, faces, mat, mats)


def frames_along(points):
    """A tangent and two normals at each point of a line (parallel transport)."""
    pts = [Vector(p) for p in points]
    out = []
    t0 = (pts[1] - pts[0]).normalized()
    up = Vector((0.0, 0.0, 1.0)) if abs(t0.z) < 0.9 else Vector((1.0, 0.0, 0.0))
    n1 = t0.cross(up).normalized()
    for i in range(len(pts)):
        if i == 0:
            t = t0
        elif i == len(pts) - 1:
            t = (pts[i] - pts[i - 1]).normalized()
        else:
            t = (pts[i + 1] - pts[i - 1]).normalized()
        n1 = (n1 - t * n1.dot(t)).normalized()
        n2 = t.cross(n1).normalized()
        out.append((t, n1, n2))
    return pts, out


def tube(name, mat, points, radii, sides=8, jag=0.0, jag_start=0.0, turn=0.0):
    """A round (`sides`-sided) tube through points, its radius at each; `jag` breaks its far end raggedly."""
    pts, fr = frames_along(points)
    if not isinstance(radii, (list, tuple)):
        radii = [radii] * len(pts)
    rings = []
    for i, (p, (t, n1, n2)) in enumerate(zip(pts, fr)):
        ring = []
        for s in range(sides):
            a = math.tau * s / sides + turn
            q = p + (n1 * math.cos(a) + n2 * math.sin(a)) * radii[i]
            if i == len(pts) - 1 and jag:
                q = q + t * (RNG.uniform(-1.0, 1.0) * jag)
            if i == 0 and jag_start:
                q = q + t * (RNG.uniform(-1.0, 1.0) * jag_start)
            ring.append(q)
        rings.append(ring)
    return loft(name, rings, mat)


def bar(name, mat, points, wide, tall, up=(0.0, 0.0, 1.0)):
    """A timber of `wide` x `tall` section along points; `up` says which way `tall` is."""
    pts = [Vector(p) for p in points]
    upv = Vector(up)
    rings = []
    for i, p in enumerate(pts):
        if i == 0:
            t = (pts[1] - pts[0]).normalized()
        elif i == len(pts) - 1:
            t = (pts[i] - pts[i - 1]).normalized()
        else:
            t = (pts[i + 1] - pts[i - 1]).normalized()
        side = t.cross(upv)
        if side.length < 1e-4:
            side = t.cross(Vector((1.0, 0.0, 0.0)))
        side.normalize()
        u = side.cross(t).normalized()
        rings.append([p + side * sx * wide * 0.5 + u * sz * tall * 0.5 for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    return loft(name, rings, mat)


def block(name, mat, centre, size, axes=None):
    """A box: its middle, its size along its own three axes (default the frame's)."""
    c = Vector(centre)
    ax = [Vector(a).normalized() for a in axes] if axes else [Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))]
    hx, hy, hz = (s * 0.5 for s in size)
    verts = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                verts.append(c + ax[0] * sx * hx + ax[1] * sy * hy + ax[2] * sz * hz)
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    return mesh_object(name, verts, faces, mat)


def turned(axis, angle):
    """Three axes turned by `angle` about `axis` ("X", "Y", "Z" or a vector)."""
    m = Matrix.Rotation(angle, 3, axis)
    return [m @ Vector((1, 0, 0)), m @ Vector((0, 1, 0)), m @ Vector((0, 0, 1))]


def slab(name, mat, outline, along, depth, face_mats=None):
    """A flat shape (points in 3D, one plane) pushed `depth` along `along`."""
    pts = [Vector(p) for p in outline]
    off = Vector(along).normalized() * depth
    n = len(pts)
    verts = pts + [p + off for p in pts]
    faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
    for i in range(n):
        j = (i + 1) % n
        faces.append((i, j, n + j, n + i))
    return mesh_object(name, verts, faces, mat)


def lathe(name, profile, centre, sides=8, mat=None, row_mats=None, axis=None):
    """A turned solid: profile of (radius, height) from the bottom up, about an axis (default Z) through centre."""
    c = Vector(centre)
    ax = turned("Z", 0.0) if axis is None else axis
    rings = []
    for r, h in profile:
        rings.append([c + ax[2] * h + (ax[0] * math.cos(math.tau * s / sides) + ax[1] * math.sin(math.tau * s / sides)) * max(r, 0.004) for s in range(sides)])
    fm = None
    if row_mats:
        def fm(k, i):
            return row_mats[min(max(k, 0), len(row_mats) - 1)]
    return loft(name, rings, mat, face_mat=fm)


def rock_lump(name, mat, centre, size, seed, sub=1):
    """A low boulder: an icosphere pushed about."""
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub, radius=1.0, location=(0, 0, 0))
    obj = bpy.context.object
    obj.name = name
    rng = random.Random(seed)
    for v in obj.data.vertices:
        k = rng.uniform(0.78, 1.18)
        v.co = Vector((v.co.x * size[0] * k, v.co.y * size[1] * k, v.co.z * size[2] * k)) + Vector(centre)
    obj.data.materials.append(mat)
    return obj


# --- The hull's shape.
def hb_mid(z):
    """Half the beam amidships at a height (outside the planking)."""
    if z <= 4.6:
        return 5.3 * math.sqrt(max(0.0, 1.0 - ((4.6 - z) / 4.4) ** 2))
    return 5.3 - 0.045 * (z - 4.6) ** 2


def y_bow(z):
    """Where the stem is at a height."""
    return 14.0 + 4.2 * math.sqrt(min(max(z / 8.5, 0.0), 1.5))


def y_aft(z):
    """Where the sternpost (low down) or the transom (above the wing transom) is at a height."""
    b = smoothstep(2.6, 5.2, z)
    return lerp(-16.6, -17.4 - 1.1 * smoothstep(5.2, 11.9, z), b)


def fy(y, z):
    if y >= 4.0:
        u = (y - 4.0) / (y_bow(z) - 4.0)
        return math.sqrt(max(0.0, 1.0 - max(u, 0.0) ** 2.2))
    if y <= -6.0:
        u = min(1.0, (-6.0 - y) / (-6.0 - y_aft(z)))
        b = smoothstep(2.6, 5.2, z)
        return lerp(math.sqrt(max(0.0, 1.0 - u * u)), 1.0 - 0.3 * u * u, b)
    return 1.0


def hb(y, z, inset=0.0):
    return max(0.08, hb_mid(z) * fy(y, z) - inset)


def stations(n):
    return [(1.0 - math.cos(math.pi * j / (n - 1))) * 0.5 for j in range(n)]


def waterline(z, inset=0.0, ya=None, yb=None, n=18):
    """A ring round the hull at a height: port from aft to forward, then starboard back."""
    lo = y_aft(z) + (0.55 if inset else 0.0)
    hi = y_bow(z) - (1.1 if inset else 0.0)
    if ya is not None:
        lo = max(lo, ya)
    if yb is not None:
        hi = min(hi, yb)
    ys = [lo + (hi - lo) * s for s in stations(n)]
    return [Vector((-hb(y, z, inset), y, z)) for y in ys] + [Vector((hb(y, z, inset), y, z)) for y in reversed(ys)]


LEVELS = [0.35, 0.8, 1.5, 2.3, 3.0, 3.6, 4.35, 5.0, 5.6, 6.3, 7.2, 8.2, 9.2, 10.2, 11.0, 11.9]


def sheer(y):
    """The top of the side (the rail) along the ship."""
    pts = [(-30.0, 11.9), (-18.6, 11.9), (-17.0, 11.4), (-14.0, 10.8), (-8.3, 10.7), (-7.5, 8.0), (10.6, 8.0), (11.4, 10.3), (30.0, 10.3)]
    for (y0, z0), (y1, z1) in zip(pts, pts[1:]):
        if y0 <= y <= y1:
            return lerp(z0, z1, (y - y0) / (y1 - y0))
    return 10.3


# ======================================================================== the ship (ship frame)
def build_hull():
    rings = [waterline(z) for z in LEVELS]

    def side_mat(k, i):
        if k < 0:
            return TAR
        if k >= len(rings) - 1:
            return TIMBER
        return TAR if LEVELS[k] < 3.45 else TIMBER
    hull = loft("Hull", rings, TIMBER, face_mat=side_mat)
    # the sheer: everything above the rail is cut away
    profile = [(-30.0, -2.0), (30.0, -2.0)] + [(y, sheer(y)) for y in (30.0, 11.4, 10.6, -7.5, -8.3, -14.0, -17.0, -18.6, -30.0)]
    trim = slab("SheerTrim", TIMBER, [(-9.0, y, z) for y, z in profile], (1.0, 0.0, 0.0), 18.0)
    boolean(hull, trim, "INTERSECT")
    bpy.data.objects.remove(trim)
    # the spaces in her, and the openings through her
    for c in make_cutters():
        CUTTERS.append(c)
    coll = bpy.data.collections.new("Cutters")
    bpy.context.scene.collection.children.link(coll)
    for c in CUTTERS:
        for u in c.users_collection:
            u.objects.unlink(c)
        coll.objects.link(c)
    mod = hull.modifiers.new("cut", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.operand_type = "COLLECTION"
    mod.collection = coll
    mod.solver = "EXACT"
    mod.material_mode = "TRANSFER"
    bpy.context.view_layer.objects.active = hull
    bpy.ops.object.modifier_apply(modifier=mod.name)
    for c in CUTTERS:
        c.hide_render = True
        c.hide_set(True)
    # (the Booleans leave slivers: weld them and drop what has no area)
    bm = bmesh.new()
    bm.from_mesh(hull.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(hull.data)
    bm.free()
    return keep_part(hull, weight=1.0)


def boolean(target, cutter, op):
    mod = target.modifiers.new("b", "BOOLEAN")
    mod.operation = op
    mod.object = cutter
    mod.solver = "EXACT"
    mod.material_mode = "TRANSFER"
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=mod.name)


def space(name, z0, z1, ya=None, yb=None, top=None):
    """A space inside her (a cutter): the inside of the hull between two heights and (optionally) along y; its
    floor will be deck planks, its walls and ceiling the ship's inside."""
    zs = [z0] + [z for z in LEVELS if z0 < z < z1] + [z1]
    rings = [waterline(z, WALL, ya, yb, 12) for z in zs]
    if top:
        rings.append([Vector((p.x, p.y, top)) for p in rings[-1]])

    def mat(k, i):
        return DECK if k < 0 else INNER
    return loft(name, rings, INNER, face_mat=mat)


def box_cut(name, x0, x1, y0, y1, z0, z1):
    return block(name, INNER, ((x0 + x1) * 0.5, (y0 + y1) * 0.5, (z0 + z1) * 0.5), (x1 - x0, y1 - y0, z1 - z0))


def jagged_cut(name, x0, x1, y0, y1, z0, z1, seed, rough=0.45):
    """A hole with broken edges through a deck: a ragged outline pushed through it."""
    rng = random.Random(seed)
    pts = []
    for k in range(7):
        pts.append((lerp(x0, x1, k / 7.0), y0 + rng.uniform(0.0, rough)))
    for k in range(6):
        pts.append((x1 - rng.uniform(0.0, rough), lerp(y0, y1, k / 6.0)))
    for k in range(7):
        pts.append((lerp(x1, x0, k / 7.0), y1 - rng.uniform(0.0, rough)))
    for k in range(6):
        pts.append((x0 + rng.uniform(0.0, rough), lerp(y1, y0, k / 6.0)))
    return slab(name, INNER, [(x, y, z0) for x, y in pts], (0.0, 0.0, 1.0), z1 - z0)


def make_cutters():
    out = [
        space("Hold", HOLD[0], HOLD[1], 1.5, 12.5),
        space("GunDeck", GUN[0], GUN[1], None, 15.5),
        space("Cabin", UPPER, CABIN_TOP, None, -8.5),
        space("Waist", UPPER, 13.0, -8.0, 11.0),
        space("QuarterDeck", QD, 13.5, None, -8.0),
        space("Forecastle", FC, 13.0, 11.5, None),
        # the stern windows: the middle three broken out into one hole; one whole window each side
        box_cut("SternHole", -1.4, 1.4, -21.0, -15.8, 7.0, 9.2),
        box_cut("SternWindowP", -2.85, -2.25, -21.0, -15.8, 7.4, 8.8),
        box_cut("SternWindowS", 2.25, 2.85, -21.0, -15.8, 7.4, 8.8),
        box_cut("CabinDoor", -1.4, 1.4, -9.0, -7.6, UPPER + 0.05, 9.2),
        # the waist's fallen deck, the main hatch, the hole a gun fell through
        jagged_cut("FallenDeck", -3.4, 2.6, -7.4, -0.7, GUN[1] - 0.2, UPPER + 0.2, 3, 0.6),
        box_cut("MainHatch", -1.5, 1.5, 4.9, 7.9, HOLD[1] - 0.1, GUN[0] + 0.15),
        jagged_cut("GunHole", 0.9, 2.9, 2.6, 4.3, HOLD[1] - 0.1, GUN[0] + 0.15, 5, 0.3),
        # planking gone: the hold's port side (out of which the route leaves), and the gun deck's port side aft
        box_cut("HoldBreach", -8.0, -2.0, 4.0, 11.0, 0.95, 3.2),
        box_cut("RibsAft", -8.0, -4.0, -11.2, -6.6, 4.5, 6.0),
    ]
    for side in (-1.0, 1.0):
        for y in PORTS_Y:
            if side < 0.0 and -11.2 < y < -6.6:
                continue
            x0, x1 = (3.6, 7.5) if side > 0.0 else (-7.5, -3.6)
            out.append(box_cut("Port", x0, x1, y - 0.33, y + 0.33, PORT_Z[0], PORT_Z[1]))
    return out


def hull_skin(y, z, side, out=0.0):
    """A point on the outside of the hull (side: -1 port, 1 starboard), `out` beyond it."""
    return Vector((side * (hb(y, z) + out), y, z))


def build_timbers():
    """Keel, stem, sternpost, rudder, wales, rail caps, channels, ribs."""
    keep_part(block("Keel", TAR, (0.0, -1.2, 0.25), (0.36, 31.0, 0.5)))
    stem = [Vector((0.0, y_bow(z) + 0.05, z)) for z in (0.25, 0.8, 1.8, 3.2, 5.0, 7.0, 9.0, 10.9)]
    keep_part(bar("Stem", TAR, stem, 0.34, 0.5, up=(0.0, 1.0, 0.0)))
    keep_part(bar("Sternpost", TAR, [(0.0, -16.75, 0.1), (0.0, -16.95, 5.3)], 0.34, 0.45, up=(0.0, 1.0, 0.0)))
    keep_part(slab("Rudder", TAR, [(-0.17, -16.95, 0.2), (-0.17, -18.2, 0.2), (-0.17, -18.0, 2.5), (-0.17, -17.6, 5.4), (-0.17, -17.0, 5.4)], (1, 0, 0), 0.34))
    # the wales: thick bands of plank along her sides
    for z, mat in ((3.5, TAR), (6.2, CARVE)):
        for side in (-1.0, 1.0):
            ys = [lerp(y_aft(z) + 0.15, y_bow(z) - 0.35, s) for s in stations(10)]
            keep_part(bar("Wale", mat, [hull_skin(y, z, side, 0.06) for y in ys], 0.2, 0.32))
    # rail caps along the waist and the quarterdeck, channels for the shrouds
    for side in (-1.0, 1.0):
        ys = [lerp(-7.3, 10.4, k / 7.0) for k in range(8)]
        keep_part(bar("RailCap", TIMBER, [Vector((side * (hb(y, 8.0) - 0.25), y, 8.05)) for y in ys], 0.62, 0.12))
        ys = [lerp(-16.8, -8.5, k / 5.0) for k in range(6)]
        keep_part(bar("RailCapQD", TIMBER, [Vector((side * (hb(y, 10.7) - 0.25), y, 10.75)) for y in ys], 0.62, 0.12))
        for y in (MAINMAST_Y, FOREMAST_Y):
            z = 7.5
            keep_part(block("Channel", TIMBER, (side * (hb(y, z) + 0.25), y, z), (0.55, 2.4, 0.14)))
    # ribs where the planking has gone
    for y in (4.35, 5.45, 9.35, 10.45):
        pts = [Vector((-(hb(y, z) - WALL * 0.5), y, z)) for z in (0.9, 1.6, 2.4, 3.25)]
        keep_part(bar("Rib", INNER, pts, 0.3, 0.52, up=(1.0, 0.0, 0.0)), look="rib")
    for y in (-10.9, -10.0, -9.1, -8.2, -7.3):
        pts = [Vector((-(hb(y, z) - WALL * 0.5), y, z)) for z in (4.45, 5.2, 6.05)]
        keep_part(bar("Rib", INNER, pts, 0.25, 0.52, up=(1.0, 0.0, 0.0)), look="rib")
    # broken plank ends at the breaches
    rng = random.Random(9)
    for k in range(5):
        y = rng.uniform(4.2, 10.8)
        if 5.6 < y < 9.2:
            continue
        z = rng.choice((0.95, 3.15))
        keep_part(block("PlankEnd", TIMBER, (-(hb(y, z) - 0.05), y + 0.4, z), (0.08, 0.9, 0.3), turned("X", rng.uniform(-0.4, 0.4))))
    # boards hanging from the fallen deck's edges, and debris on the gun deck under it
    for x, y, a in ((-3.0, -6.9, 0.9), (2.2, -2.4, -0.8), (-2.4, -1.2, 1.0), (1.4, -7.0, 0.7)):
        keep_part(block("Board", DECK, (x, y, GUN[1] - 0.5), (0.3, 1.6, 0.07), turned("X", a)))
    for x, y, a in ((2.0, -6.6, 0.3), (2.6, -5.4, -0.5), (-2.9, -2.6, 0.2)):
        keep_part(block("Debris", DECK, (x, y, GUN[0] + 0.12), (0.3, 1.8, 0.08), turned("Z", a)))


def gun(name, at, out, carriage=True, length=2.3, mat=BRONZE):
    """A gun: its barrel from the breech at `at` along `out`, on a carriage under it if `carriage`."""
    o = Vector(out).normalized()
    a = Vector(at)
    pts = [a - o * 0.18, a, a + o * length * 0.25, a + o * length * 0.55, a + o * length * 0.92, a + o * length]
    keep_part(tube(name, mat, pts, [0.1, 0.27, 0.24, 0.2, 0.2, 0.24], 8), look="gun", weight=1.2)
    if carriage:
        side = Vector((0.0, 0.0, 1.0)).cross(o).normalized()
        floor_z = a.z - 0.875
        for s in (-1.0, 1.0):
            keep_part(block(name + "Cheek", TIMBER, a - o * 0.05 + side * s * 0.3 + Vector((0, 0, -0.3)), (1.2, 0.12, 0.5), [o, side, Vector((0, 0, 1))]))
        for k in (-0.45, 0.35):
            keep_part(block(name + "Axle", TIMBER, a + o * k + Vector((0, 0, -0.5)), (0.18, 0.9, 0.16), [o, side, Vector((0, 0, 1))]))
            if k < 0.0:
                continue
            for s in (-1.0, 1.0):
                c = a + o * k + side * s * 0.5
                c.z = floor_z + 0.2
                keep_part(tube(name + "Truck", TIMBER, [c - side * 0.06, c + side * 0.06], 0.2, 6))


def build_guns():
    zc = (PORT_Z[0] + PORT_Z[1]) * 0.5 - 0.05
    star = (-13.5, -10.5, -7.5, -4.5, -1.5, 4.5, 7.5)
    port = (-13.5, 4.5, 7.5, 10.5)
    k = 0
    for side, ys in ((1.0, star), (-1.0, port)):
        for y in ys:
            muzzle = hb(y, zc) + 0.22
            gun("Gun%02d" % k, (side * (muzzle - 2.3), y, zc), (side, 0.0, 0.0))
            k += 1
    # two port guns slid down to starboard, the gun fallen into the hold, one in the cabin's stern port
    gun("Slid0", (1.4, -3.9, GUN[0] + 0.27), (0.9, 0.35, 0.02), False)
    gun("Slid1", (1.6, -0.2, GUN[0] + 0.27), (0.8, -0.55, 0.02), False)
    gun("Fallen", (1.85, 3.25, GUN[0] + 0.25), (-0.12, 0.5, -0.85), False)


def lid(y, side, angle, z_hinge=PORT_Z[1] + 0.06):
    """A gun port's lid, hinged at its top, swung out and up by `angle`."""
    out = Vector((side, 0.0, 0.0))
    up = Vector((0.0, 0.0, 1.0))
    hinge = Vector((side * (hb(y, z_hinge) + 0.05), y, z_hinge))
    down = (out * math.sin(angle) - up * math.cos(angle)).normalized()
    thick = down.cross(Vector((0.0, 1.0, 0.0))).normalized()
    keep_part(block("Lid", LIDRED, hinge + down * 0.37, (0.06, 0.8, 0.74), [thick, Vector((0, 1, 0)), down]))


def build_lids():
    for y in PORTS_Y:
        lid(y, 1.0, math.radians(100.0) if y != 1.5 else math.radians(10.0))
    for y in (-13.5, 1.5, 7.5, 10.5):
        lid(y, -1.0, math.radians(25.0 + 25.0 * (y > 0)))


def stern_y(z):
    return y_aft(z) - 0.02


def build_stern():
    """The carved stern (after the concept art: a gallery of many-paned windows, carved scrolls above, a lantern on
    each top corner, a quarter gallery on each side): window frames, the balcony ledge and its balusters, pilasters,
    the scallop and scrolls, the arched crest, quarter galleries, the lanterns."""
    def on(x, z, out=0.0, zref=None):
        return Vector((x, stern_y(z if zref is None else zref) - out, z))

    def frame(x0, x1, z0, z1, broken_top=False):
        t = 0.15
        keep_part(block("Frame", CARVE, on((x0 + x1) * 0.5, z0 - t * 0.5, 0.06), (x1 - x0 + 2 * t, 0.14, t)), weight=1.6, look="stern")
        if broken_top:
            for a, b in ((x0 - t, x0 + 0.5), (x1 - 0.35, x1 + t)):
                keep_part(block("Frame", CARVE, on((a + b) * 0.5, z1 + t * 0.5, 0.06), (b - a, 0.14, t)), weight=1.6, look="stern")
        else:
            keep_part(block("Frame", CARVE, on((x0 + x1) * 0.5, z1 + t * 0.5, 0.06), (x1 - x0 + 2 * t, 0.14, t)), weight=1.6, look="stern")
        for x in (x0 - t * 0.5, x1 + t * 0.5):
            keep_part(block("Frame", CARVE, on(x, (z0 + z1) * 0.5, 0.06), (t, 0.14, z1 - z0)), weight=1.6, look="stern")
    frame(-1.4, 1.4, 7.0, 9.2, True)
    for s in (-1.0, 1.0):
        frame(-2.85 if s < 0 else 2.25, -2.25 if s < 0 else 2.85, 7.4, 8.8)
        # its glazing bars: two up, two across
        for dx in (-0.1, 0.1):
            keep_part(block("Mullion", CARVE, on(s * 2.55 + dx, 8.1, 0.05), (0.05, 0.1, 1.4)), weight=1.6, look="stern")
        for dz in (-0.25, 0.25):
            keep_part(block("Mullion", CARVE, on(s * 2.55, 8.1 + dz, 0.05), (0.6, 0.1, 0.05)), weight=1.6, look="stern")
    # the balcony: a ledge under the windows, balusters and a rail but where it has broken away
    keep_part(block("Ledge", CARVE, on(0.0, 6.78, 0.25), (6.8, 0.6, 0.16)), weight=1.6, look="stern")
    for s in (-1.0, 1.0):
        for x in (1.65, 2.05, 2.45, 2.85, 3.2):
            keep_part(tube("Baluster", CARVE, [on(s * x, 6.86, 0.42), on(s * x, 7.2, 0.42), on(s * x, 7.5, 0.42)], [0.06, 0.08, 0.05], 4), weight=1.6, look="stern")
        keep_part(block("BalconyRail", CARVE, on(s * 2.42, 7.55, 0.42), (1.7, 0.12, 0.1)), weight=1.6, look="stern")
        keep_part(block("Pilaster", CARVE, on(s * 1.82, 9.1, 0.08), (0.22, 0.16, 4.3)), weight=1.6, look="stern")
    # a moulding over the windows, the scallop fan and scrolls above it
    keep_part(block("Moulding", CARVE, on(0.0, 9.5, 0.1), (5.8, 0.2, 0.18)), weight=1.6, look="stern")
    fan_c = (0.0, 9.62)
    for k in range(7):
        a0 = math.radians(12.0 + 156.0 * k / 7.0)
        a1 = math.radians(12.0 + 156.0 * (k + 0.82) / 7.0)
        r0, r1 = 0.22, 1.0 + 0.08 * (k % 2)
        ring = [(fan_c[0] + math.cos(a0) * r0, fan_c[1] + math.sin(a0) * r0), (fan_c[0] + math.cos(a0) * r1, fan_c[1] + math.sin(a0) * r1),
                (fan_c[0] + math.cos((a0 + a1) * 0.5) * (r1 + 0.1), fan_c[1] + math.sin((a0 + a1) * 0.5) * (r1 + 0.1)),
                (fan_c[0] + math.cos(a1) * r1, fan_c[1] + math.sin(a1) * r1), (fan_c[0] + math.cos(a1) * r0, fan_c[1] + math.sin(a1) * r0)]
        keep_part(slab("Shell", CARVE, [on(x, z, 0.08, 10.1) for x, z in ring], (0.0, -1.0, 0.0), 0.16 + 0.04 * (k % 2)), weight=2.0, look="stern")
    for s in (-1.0, 1.0):
        # a scroll: a curling band
        pts = []
        for k in range(9):
            a = math.radians(-90.0 + 300.0 * k / 8.0)
            r = 0.45 - 0.035 * k
            pts.append(on(s * (1.55 + math.cos(a) * r * s), 10.2 + math.sin(a) * r, 0.12))
        keep_part(bar("Scroll", CARVE, pts, 0.14, 0.16, up=(0.0, -1.0, 0.0)), weight=2.0, look="stern")
    # the arched crest on top
    crest = [(-2.4, 11.35), (-1.8, 11.75), (-0.9, 12.05), (0.0, 12.15), (0.9, 12.05), (1.8, 11.75), (2.4, 11.35)]
    keep_part(slab("Crest", CARVE, [on(x, z, -0.25, 11.6) for x, z in crest + [(2.4, 11.0), (-2.4, 11.0)]], (0.0, -1.0, 0.0), 0.32), weight=1.6, look="stern")
    # quarter galleries: a bay on each corner with a domed top, a drop under it and its windows
    for s in (-1.0, 1.0):
        y = -16.0
        x = s * (hb(y, 8.3) + 0.3)
        keep_part(block("Gallery", CARVE, (x, y, 8.3), (0.65, 1.9, 2.4)), weight=1.4, look="stern")
        keep_part(block("GalleryWin", GLASS, (x + s * 0.3, y, 8.45), (0.06, 1.3, 0.9)), weight=1.4, look="stern")
        for dy in (-0.33, 0.0, 0.33):
            keep_part(block("GalleryBar", CARVE, (x + s * 0.34, y + dy, 8.45), (0.05, 0.06, 0.95)), weight=1.4, look="stern")
        keep_part(block("GalleryBar", CARVE, (x + s * 0.34, y, 8.45), (0.05, 1.35, 0.06)), weight=1.4, look="stern")
        keep_part(lathe("GalleryTop", [(0.95, 0.0), (0.6, 0.35), (0.12, 0.7), (0.02, 0.8)], (x - s * 0.1, y, 9.5), 6, CARVE), weight=1.4, look="stern")
        keep_part(lathe("GalleryDrop", [(0.02, -0.9), (0.25, -0.5), (0.75, 0.0)], (x - s * 0.1, y, 7.1), 6, CARVE), weight=1.4, look="stern")
        # a lantern on each top corner of the stern, on an iron post
        foot = on(s * 2.25, 11.3, 0.05)
        keep_part(bar("LanternPost", RUST, [foot, foot + Vector((0.0, -0.15, 0.8))], 0.09, 0.09, up=(0, 1, 0)))
        lantern("SternLantern", foot + Vector((0.0, -0.15, 0.72)), 1.4)


def lantern(name, base, size, hanging=False):
    """A ship's lantern: a six-sided iron frame with glass, a cone of a roof, a ring on top."""
    b = Vector(base)
    s = size
    if hanging:
        keep_part(tube(name + "Chain", RUST, [b + Vector((0, 0, 0.7 * s)), b + Vector((0, 0, 1.2 * s))], 0.02 * s, 4))
    keep_part(lathe(name, [(0.24 * s, 0.0), (0.28 * s, 0.08 * s), (0.3 * s, 0.5 * s), (0.36 * s, 0.56 * s), (0.18 * s, 0.82 * s), (0.04 * s, 0.95 * s)], b, 6, RUST,
                    row_mats=[RUST, GLASS, RUST, RUST, RUST]), weight=1.4, look="stern")


def rail_posts(y0, y1, z, step=0.9, high=0.65):
    """An open rail on posts along both sides, standing on the bulwark's top (as in the concept art)."""
    n = max(2, int((y1 - y0) / step) + 1)
    for s in (-1.0, 1.0):
        ys = [lerp(y0, y1, k / (n - 1.0)) for k in range(n)]
        for y in ys:
            keep_part(block("RailPost", TIMBER, (s * (hb(y, z) - 0.25), y, z + high * 0.5), (0.12, 0.12, high)))
        keep_part(bar("Rail", TIMBER, [Vector((s * (hb(y, z) - 0.25), y, z + high + 0.05)) for y in ys[::max(1, n // 4)] + [ys[-1]]], 0.18, 0.1))


def build_decks():
    """What stands on the decks: the wheel, the mainmast's stump, rails, deadeyes, the grating, the hatch's coaming,
    the lanterns inside."""
    # the wheel on the quarterdeck: its axle fore and aft on two posts, the wheel at its after end
    c = Vector((0.0, -11.4, QD + 1.0))
    for dy in (-0.05, 0.75):
        keep_part(block("WheelPost", TIMBER, (0.0, c.y + dy, QD + 0.5), (0.2, 0.14, 1.0)))
    keep_part(tube("WheelAxle", TIMBER, [c + Vector((0, -0.2, 0)), c + Vector((0, 0.85, 0))], 0.12, 6))
    rim = []
    for k in range(11):
        a = math.tau * 0.97 * k / 10.0
        rim.append(c + Vector((0.0, -0.18, 0.0)) + Vector((math.cos(a), 0.0, math.sin(a))) * 0.72)
    keep_part(tube("WheelRim", TIMBER, rim, 0.06, 4))
    for k in range(8):
        a = math.tau * k / 8.0 + 0.2
        d = Vector((math.cos(a), 0.0, math.sin(a)))
        keep_part(tube("Spoke", TIMBER, [c + Vector((0, -0.18, 0)), c + Vector((0, -0.18, 0)) + d * 1.0], [0.045, 0.035], 4))
    keep_part(tube("Hub", TIMBER, [c + Vector((0, -0.3, 0)), c + Vector((0, -0.05, 0))], 0.14, 8))
    # the mainmast's stump in the waist (down through the gun deck), jagged
    keep_part(tube("MainStump", TIMBER, [(0.0, MAINMAST_Y, HOLD[1] - 0.2), (0.0, MAINMAST_Y, UPPER), (0.0, MAINMAST_Y, 8.6)], [0.55, 0.55, 0.53], 8, jag=0.4), look="mast")
    keep_part(block("Partners", TIMBER, (0.0, MAINMAST_Y, UPPER + 0.1), (1.6, 1.6, 0.2)))
    # open rails on posts round the quarterdeck and the forecastle
    rail_posts(-16.6, -8.6, 10.75)
    rail_posts(11.8, 16.4, 10.35, 0.9, 0.55)
    # deadeyes on the channels, their chain plates down the side
    for y0, z in ((FOREMAST_Y, 7.5), (MAINMAST_Y, 7.5), (MIZZEN_Y + 0.6, 10.1)):
        for s in (-1.0, 1.0):
            if z > 9.0:
                keep_part(block("Channel", TIMBER, (s * (hb(y0, z) + 0.25), y0, z), (0.55, 2.2, 0.14)))
            for dy in (-0.8, 0.0, 0.8):
                y = y0 + dy
                out = hb(y, z) + 0.42
                keep_part(lathe("Deadeye", [(0.19, -0.06), (0.19, 0.06)], (s * out, y, z + 0.28), 6, STAVE, axis=turned("X", math.pi * 0.5)))
                if False:
                    keep_part(bar("ChainPlate", RUST, [Vector((s * out, y, z + 0.1)), Vector((s * (hb(y, z - 1.1) + 0.06), y, z - 1.1))], 0.06, 0.04, up=(s, 0, 0)))
    # the grating in the waist, over its coaming
    keep_part(block("Coaming", TIMBER, (0.0, 6.4, UPPER + 0.15), (2.6, 2.8, 0.3)))
    for k in range(5):
        keep_part(block("Grate", DECK, (-0.9 + 0.45 * k, 6.4, UPPER + 0.33), (0.1, 2.6, 0.1)))
    for k in range(5):
        keep_part(block("Grate", DECK, (0.0, 5.4 + 0.5 * k, UPPER + 0.38), (2.4, 0.1, 0.06)))
    # the main hatch's coaming on the gun deck
    for x, y, sx, sy in ((0.0, 4.8, 3.2, 0.2), (0.0, 8.0, 3.2, 0.2), (-1.6, 6.4, 0.2, 3.4), (1.6, 6.4, 0.2, 3.4)):
        keep_part(block("HatchCoaming", TIMBER, (x, y, GUN[0] + 0.12), (sx, sy, 0.24)))
    # deck beams under each deck (not where the deck has fallen in, nor across the hatch)
    def beams(ys, z, name):
        for y in ys:
            half = hb(y, z, WALL) + 0.05
            keep_part(block(name, INNER, (0.0, y, z - 0.12), (half * 2.0, 0.26, 0.24)))
    beams([y for y in (-15.4, -13.8, -12.2, -10.6, -9.0, 0.4, 2.0, 3.6, 8.4, 10.0, 11.6, 13.2, 14.6)], GUN[1], "GunBeam")
    beams((4.2, 8.6, 10.4, 12.0), HOLD[1], "HoldBeam")
    beams((-15.6, -14.0, -12.4, -10.8, -9.2), CABIN_TOP, "CabinBeam")
    # the lanterns inside: a hanging one each in the cabin, the gun deck and the hold
    lantern("CabinLantern", (1.6, -13.0, CABIN_TOP - 0.75), 0.6, True)
    lantern("GunLantern", (2.2, -9.0, GUN[1] - 0.75), 0.6, True)
    lantern("HoldLantern", (1.6, 8.0, HOLD[1] - 0.75), 0.6, True)


def build_bow():
    """The beakhead: its knee and head rails, the mermaid figurehead (as in the concept art), the bowsprit,
    catheads, the hawse hole."""
    knee = [(y_bow(5.0) - 0.1, 5.0), (19.1, 5.6), (20.3, 6.7), (20.7, 7.8), (20.1, 8.6), (y_bow(9.0) - 0.1, 9.1)]
    keep_part(slab("Knee", CARVE, [(-0.22, y, z) for y, z in knee], (1.0, 0.0, 0.0), 0.44), look="bow")
    for s in (-1.0, 1.0):
        rail = [(s * (hb(17.0, 9.3) - 0.1), 17.0, 9.3), (s * 0.9, 18.9, 9.0), (s * 0.35, 20.0, 8.55)]
        keep_part(bar("HeadRail", CARVE, rail, 0.14, 0.18), look="bow")
        rail = [(s * (hb(17.3, 8.3) - 0.1), 17.3, 8.3), (s * 0.85, 18.9, 7.85), (s * 0.3, 20.1, 7.35)]
        keep_part(bar("HeadRail", CARVE, rail, 0.12, 0.16), look="bow")
    # the mermaid: her tail curled down the knee to a fluke, leaning out from the bow, arms crossed on her breast,
    # her hair down her back; weathered pale stone-green paint
    fig = FIGURE
    w = 2.2
    fwd = Vector((0.0, 1.0, 0.0))
    up = Vector((0.0, 0.55, 0.83)).normalized()
    side = Vector((1.0, 0.0, 0.0))
    n_fig = len(PARTS)
    hips = Vector((0.0, 20.55, 7.55))
    tail = [hips, Vector((0.0, 20.55, 6.95)), Vector((0.0, 20.3, 6.35)), Vector((0.0, 19.85, 5.95)), Vector((0.0, 19.5, 6.05))]
    keep_part(tube("MermaidTail", fig, tail, [0.3, 0.27, 0.2, 0.12, 0.06], 8), weight=w, look="bow")
    end = tail[-1]
    keep_part(slab("MermaidFluke", fig, [end + Vector((0, 0.0, 0.0)), end + Vector((0, -0.45, 0.35)), end + Vector((0, -0.25, 0.05)), end + Vector((0, -0.5, -0.25))],
                   (1.0, 0.0, 0.0), 0.08), weight=w, look="bow")
    chest_at = hips + up * 0.75
    neck = hips + up * 1.05
    keep_part(tube("MermaidBody", fig, [hips - up * 0.05, hips + up * 0.35, chest_at, neck], [0.3, 0.24, 0.29, 0.13], 8), weight=w, look="bow")
    head = neck + up * 0.24 + fwd * 0.04
    keep_part(lathe("MermaidHead", [(0.02, -0.21), (0.15, -0.16), (0.2, -0.02), (0.18, 0.1), (0.1, 0.19), (0.02, 0.22)], head, 8, fig, axis=[side, fwd.cross(side) * -1.0, up]),
              weight=w, look="bow")
    hair = [head + up * 0.12 - fwd * 0.08, head - up * 0.1 - fwd * 0.22, neck - up * 0.25 - fwd * 0.3, chest_at - up * 0.25 - fwd * 0.3]
    keep_part(tube("MermaidHair", fig, hair, [0.2, 0.2, 0.15, 0.06], 6), weight=w, look="bow")
    for s in (-1.0, 1.0):
        shoulder = neck - up * 0.1 + side * s * 0.27
        elbow = chest_at - up * 0.12 + side * s * 0.3 + fwd * 0.2
        hand = chest_at + up * 0.08 - side * s * 0.15 + fwd * 0.27
        keep_part(tube("MermaidArm", fig, [shoulder, elbow, hand], [0.085, 0.075, 0.06], 6), weight=w, look="bow")
    # (half as big again, from where she meets the knee: she must read from far off)
    pivot = Vector((0.0, 20.45, 7.3))
    for p in PARTS[n_fig:]:
        for v in p["obj"].data.vertices:
            v.co = pivot + (v.co - pivot) * 1.5
    # the bowsprit, up out of the forecastle over the figurehead; broken at its end
    keep_part(tube("Bowsprit", TIMBER, [(0.0, 15.0, 9.1), (0.0, 18.5, 10.5), (0.0, 22.2, 12.0)], [0.38, 0.33, 0.26], 8, jag=0.3), group="rig", look="mast")
    for s in (-1.0, 1.0):
        keep_part(block("Cathead", TIMBER, (s * (hb(16.0, 10.0) + 0.4), 16.2, 10.1), (1.3, 0.35, 0.35), turned("Z", s * 0.5)))
    # the port hawse hole, where the anchor's chain comes out
    keep_part(lathe("Hawse", [(0.22, 0.0), (0.22, 0.1)], hull_skin(17.0, 7.2, -1.0, -0.04), 8, HOLE, axis=[Vector((0, 1, 0)), Vector((0, 0, 1)), Vector((-1, 0, 0))]))


def build_mast(name, y, foot_z, height, top, lean_deg, yard_len, sails, flag, channel_z, stay_to=None):
    """A standing mast: the lower mast to its top (a platform on trestle trees) and cap, the topmast broken off a
    little above it (the black flag's rag on it if `flag`), a yard cock-billed across it hung with shreds of sail,
    shrouds to the channels (the starboard ones slack), a stay forward. Returns its head."""
    foot = Vector((0.0, y, foot_z))
    lean = Matrix.Rotation(math.radians(lean_deg), 3, "Y")
    axes = [lean @ Vector((1, 0, 0)), lean @ Vector((0, 1, 0)), lean @ Vector((0, 0, 1))]

    def m(x, yy, z):
        return foot + lean @ Vector((x, yy, z))
    r0 = 0.5 if height > 5.0 else 0.4
    keep_part(tube(name, TIMBER, [m(0, 0, -0.4), m(0, 0, height * 0.5), m(0, 0, height)], [r0, r0 * 0.94, r0 * 0.84], 8), group="rig", look="mast")
    sc = 1.0 if height > 5.0 else 0.8
    pts = [m(math.cos(a) * 1.25 * sc, (0.15 + math.sin(a) * 1.0) * sc, top) for a in [math.radians(d) for d in range(0, 181, 30)]] + [m(-1.25 * sc, -0.6 * sc, top), m(1.25 * sc, -0.6 * sc, top)]
    keep_part(slab(name + "Top", TIMBER, pts[::-1], axes[2], 0.18), group="rig", look="mast")
    for s in (-1.0, 1.0):
        keep_part(block(name + "Trestle", TIMBER, m(s * 0.45 * sc, 0.0, top - 0.15), (0.16, 2.0 * sc, 0.2), axes), group="rig")
    keep_part(block(name + "Cap", TIMBER, m(0.0, 0.28 * sc, height + 0.1), (0.7 * sc, 1.3 * sc, 0.25), axes), group="rig")
    stub = top + 1.5 * sc
    keep_part(tube(name + "Topmast", TIMBER, [m(0, 0.55 * sc, top - 0.6), m(0, 0.55 * sc, height + 0.4), m(0, 0.55 * sc, stub)], [0.27 * sc, 0.25 * sc, 0.23 * sc], 6, jag=0.3), group="rig", look="mast")
    if flag:
        rag = [(0.0, 0.0), (0.0, -0.75), (0.18, -0.95), (0.3, -0.7), (0.5, -1.0), (0.62, -0.62), (0.85, -0.8), (0.92, -0.35), (1.0, -0.15), (0.95, 0.0)]
        corner = m(0.0, 0.8 * sc, stub - 0.15)
        keep_part(slab("Flag", FLAG, [corner + lean @ Vector((-0.015, px * 1.1, pz * 0.9)) for px, pz in rag], axes[0], 0.03), group="rig", weight=1.8, look="flag")
        for s in (-1.0, 1.0):
            sk = corner + lean @ Vector((0.017 * s, 0.55, -0.42))

            def at(u, v):
                return sk + lean @ Vector((0.0, u, v))
            skull = [at(math.cos(a) * 0.13, 0.06 + math.sin(a) * 0.14) for a in [math.tau * k / 8 for k in range(8)]]
            keep_part(slab("Skull", BONE, skull, axes[0] * s, 0.01), group="rig", weight=1.8, look="flag")
            for a in (0.7, -0.7):
                d = Vector((0.0, math.cos(a), math.sin(a)))
                n = Vector((0.0, -math.sin(a), math.cos(a))) * 0.025
                p = Vector((0.0, 0.0, -0.2))
                bone = [p - d * 0.24 + n, p + d * 0.24 + n, p + d * 0.24 - n, p - d * 0.24 - n]
                keep_part(slab("Bone", BONE, [at(q.y, q.z) for q in bone], axes[0] * s, 0.01), group="rig", weight=1.8, look="flag")
    # the yard, cock-billed, with shreds of sail hanging from it
    yard_z = top - 0.9
    tilt = Matrix.Rotation(math.radians(-14.0), 3, "Y")
    ends = [foot + lean @ (tilt @ Vector((x, -0.55, 0.0)) + Vector((0, 0, yard_z))) for x in (-yard_len, -yard_len * 0.45, 0.0, yard_len * 0.45, yard_len)]
    keep_part(tube(name + "Yard", TIMBER, ends, [0.09, 0.17, 0.21, 0.17, 0.09], 8), group="rig", look="mast")
    rng = random.Random(len(name) * 7 + int(y))
    for x0, x1, drop in sails:
        ragged = [(x0, 0.0), (x1, 0.0)]
        for j in range(5):
            ragged.append((lerp(x0, x1, 1.0 - j / 4.0), -drop * rng.uniform(0.45, 1.0)))
        pts = [foot + lean @ (tilt @ Vector((x, -0.75, z)) + Vector((0, 0, yard_z - 0.15))) for x, z in ragged]
        keep_part(slab("Sail", SAIL, pts, axes[1], 0.03), group="rig", weight=0.9, look="sail")
    head = m(0.0, 0.0, top - 0.3)
    for s in (-1.0, 1.0):
        for dy in (-0.8, 0.0, 0.8):
            low = Vector((s * (hb(y + dy, channel_z) + 0.42), y + dy, channel_z + 0.4))
            sag = 0.5 if s > 0 else 0.05
            mid = head.lerp(low, 0.5) + Vector((s * sag * 0.4, 0.0, -sag))
            keep_part(tube("Shroud", ROPE, [head, head.lerp(mid, 0.5), mid, mid.lerp(low, 0.5), low], 0.05, 4), group="rig", weight=0.6, solid=False, look="rope")
    if stay_to is not None:
        a = m(0, 0.4, top + 0.2)
        keep_part(tube("Stay", ROPE, [a, a.lerp(stay_to, 0.5) + Vector((0, 0, -0.6)), stay_to], 0.06, 4), group="rig", weight=0.6, solid=False, look="rope")
    return head


def build_masts():
    fore = build_mast("Foremast", FOREMAST_Y, UPPER, 6.4, 5.9, 8.0, 4.6, ((-4.3, -2.6, 3.4), (-2.5, -0.4, 4.4), (0.4, 2.0, 2.6), (2.1, 4.2, 3.8)),
                      False, 7.5, Vector((0.0, 20.5, 11.65)))
    build_mast("Mizzen", MIZZEN_Y, QD, 4.6, 4.1, 4.0, 3.4, ((-3.2, -1.4, 2.6), (-1.3, 0.9, 2.9), (1.0, 3.2, 2.2)), True, 10.1)
    return fore


# ======================================================================== the treasure (ship frame)
def coin(at, tilt=0.0, turn=0.0):
    ax = turned("X", tilt)
    rot = Matrix.Rotation(turn, 3, "Z")
    ax = [rot @ a for a in ax]
    keep_part(lathe("Coin", [(0.1, 0.0), (0.1, 0.025)], at, 6, GOLD, axis=ax), group="treasure", weight=3.0, solid=False, look="gold")


def chest(name, at, turn, lid_open, full=True):
    """A treasure chest: its box, iron straps, a lid swung open, gold heaped in it."""
    c = Vector(at)
    rot = Matrix.Rotation(turn, 3, "Z")
    ax = [rot @ Vector((1, 0, 0)), rot @ Vector((0, 1, 0)), Vector((0, 0, 1))]
    keep_part(block(name, STAVE, c + Vector((0, 0, 0.27)), (1.0, 0.62, 0.54), ax), group="treasure", weight=2.0, look="chest")
    for k in (-0.3, 0.3):
        keep_part(block(name + "Strap", RUST, c + ax[0] * k + Vector((0, 0, 0.27)), (0.07, 0.66, 0.56), ax), group="treasure", weight=2.0, look="chest")
    hinge = c + ax[1] * 0.31 + Vector((0, 0, 0.54))
    a = lid_open
    up = (Vector((0, 0, 1)) * math.cos(a) + ax[1] * math.sin(a)).normalized()
    back = (ax[1] * math.cos(a) - Vector((0, 0, 1)) * math.sin(a)).normalized()
    keep_part(block(name + "Lid", STAVE, hinge - back * 0.31 + up * 0.08, (1.02, 0.64, 0.16), [ax[0], back, up]), group="treasure", weight=2.0, look="chest")
    if full:
        keep_part(lathe(name + "Gold", [(0.42, 0.0), (0.4, 0.08), (0.22, 0.17), (0.02, 0.2)], c + Vector((0, 0, 0.52)), 6, GOLD,
                        axis=[ax[0], ax[1] * 0.75, Vector((0, 0, 1))]), group="treasure", weight=3.0, solid=False, look="gold")


def goblet(at, tilt=0.0, turn=0.0):
    ax = turned("X", tilt)
    rot = Matrix.Rotation(turn, 3, "Z")
    ax = [rot @ a for a in ax]
    keep_part(lathe("Goblet", [(0.1, 0.0), (0.03, 0.04), (0.025, 0.16), (0.1, 0.24), (0.12, 0.36), (0.1, 0.37)], at, 6, GOLD, axis=ax),
              group="treasure", weight=3.0, solid=False, look="gold")


def build_treasure():
    """The hoard in the hold under the hatch's fore edge, and a little in the great cabin."""
    h = HOARD
    rng = random.Random(77)
    rings = []
    for r, z in ((1.25, 0.0), (1.0, 0.18), (0.7, 0.38), (0.35, 0.56), (0.08, 0.64)):
        ring = []
        for k in range(12):
            a = math.tau * k / 12.0
            rr = r * rng.uniform(0.85, 1.12)
            ring.append(h + Vector((math.cos(a) * rr, math.sin(a) * rr * 0.85, z)))
        rings.append(ring)
    keep_part(loft("Heap", rings, GOLD), group="treasure", weight=3.0, solid=False, look="gold")
    # the crown on top of the heap, a little askew, its points and stones
    crown_at = h + Vector((0.05, 0.0, 0.58))
    ax = turned(Vector((1.0, 0.4, 0.0)).normalized(), 0.3)
    pts_out = []
    pts_in = []
    for k in range(10):
        a = math.tau * k / 10.0
        for r, out in ((0.2, pts_out), (0.17, pts_in)):
            out.append((a, r))
    rings = []
    for z in (0.0, 0.14):
        rings.append([crown_at + ax[0] * math.cos(a) * r + ax[1] * math.sin(a) * r + ax[2] * z for a, r in pts_out])
    tips = []
    for k, (a, r) in enumerate(pts_out):
        z = 0.32 if k % 2 == 0 else 0.16
        tips.append(crown_at + ax[0] * math.cos(a) * r + ax[1] * math.sin(a) * r + ax[2] * z)
    rings.append(tips)
    keep_part(loft("Crown", rings, GOLD), group="treasure", weight=4.0, solid=False, look="gold")
    for k in range(5):
        a = math.tau * k / 5.0
        keep_part(block("Gem", RUBY if k % 2 == 0 else EMERALD, crown_at + ax[0] * math.cos(a) * 0.205 + ax[1] * math.sin(a) * 0.205 + ax[2] * 0.08,
                        (0.06, 0.06, 0.06), [ax[0] * math.cos(a) + ax[1] * math.sin(a), -ax[0] * math.sin(a) + ax[1] * math.cos(a), ax[2]]),
                  group="treasure", weight=4.0, solid=False, look="gold")
    chest("Chest", h + Vector((0.6, 1.5, 0.0)), 0.25, math.radians(110.0))
    chest("ChestB", h + Vector((-1.25, 0.55, 0.0)), -0.9, math.radians(95.0))
    for k, (x, y) in enumerate(((1.15, -0.4), (-0.6, -1.0), (1.4, 0.8))):
        goblet(h + Vector((x, y, 0.0 if k else 0.1)), math.radians(80.0) if k == 0 else 0.0, rng.uniform(0, 6))
    for k in range(3):
        keep_part(block("Ingot", GOLD, h + Vector((-0.4 + 0.3 * k, -1.35, 0.06)), (0.24, 0.12, 0.1), turned("Z", 0.3 * k)),
                  group="treasure", weight=3.0, solid=False, look="gold")
    for k in range(7):
        a = rng.uniform(0, math.tau)
        r = rng.uniform(1.3, 2.1)
        coin(h + Vector((math.cos(a) * r, math.sin(a) * r * 0.7, 0.01)), rng.uniform(0.0, 0.25), rng.uniform(0, 3))
    # in the great cabin: a small chest spilling coins, a goblet
    cab = Vector((-1.8, -14.2, UPPER))
    chest("CabinChest", cab, 1.2, math.radians(120.0))
    goblet(cab + Vector((1.0, 0.6, 0.0)), 0.0, 0.3)
    for k in range(3):
        coin(cab + Vector((rng.uniform(0.4, 1.6), rng.uniform(-0.7, 0.9), 0.01)), rng.uniform(0.0, 0.2), rng.uniform(0, 3))


# ======================================================================== on the sand (world frame)
def W(p):
    """A ship-frame point where it lies."""
    return LIE @ Vector(p)


def build_sand(fore_head):
    """The rock under the bow, the drift of sand on her low side and stern, the fallen mainmast and its rigging,
    the anchor and its cable, and what spilled out of her."""
    # the rock her forefoot rests on
    foot = W((0.0, 12.0, 0.0))
    rock_lump("BowRock", ROCK, (foot.x + 0.2, foot.y - 0.1, foot.z * 0.5 - 0.35), (2.0, 1.6, max(foot.z * 0.5 + 0.55, 1.0)), 21, 2)
    keep_part(bpy.context.object, frame="world", weight=0.7)
    rock_lump("SandRock", ROCK, (-9.5, 2.5, -0.1), (1.1, 0.9, 0.6), 22, 1)
    keep_part(bpy.context.object, frame="world", weight=0.6)
    # the drift: banked against the starboard side and round the stern (a heightfield on a closed skirt)
    cols, rows = 11, 16
    x0, x1, y0, y1 = -4.0, 10.0, -24.0, 2.0
    verts = []
    faces = []

    def height(x, y):
        stern = smoothstep(4.0, -18.0, y)
        e = math.sqrt(((x - 1.6) / 4.6) ** 2 + ((y + 1.0) / 17.5) ** 2)
        d = max(0.0, (e - 1.0) * 4.6)
        side = 1.0 if x > 1.6 else 0.45
        h = (0.25 + 1.2 * stern) * side * (1.0 - smoothstep(0.0, 3.0, d))
        rim = min(1.0, min(x - x0, x1 - x, y - y0, y1 - y) / 2.5)
        return h * max(rim, 0.0) - 0.04
    for j in range(rows):
        for i in range(cols):
            x = lerp(x0, x1, i / (cols - 1.0))
            y = lerp(y0, y1, j / (rows - 1.0))
            verts.append(Vector((x, y, height(x, y))))
    for j in range(rows - 1):
        for i in range(cols - 1):
            a = j * cols + i
            faces.append((a, a + 1, a + cols + 1, a + cols))
    # a skirt down and a floor, to close it
    edge = [j * cols for j in range(rows)][::-1] + list(range(cols)) + [j * cols + cols - 1 for j in range(rows)] + [(rows - 1) * cols + i for i in range(cols)][::-1]
    ring = []
    seen = set()
    for e in edge:
        if e not in seen:
            seen.add(e)
            ring.append(e)
    base = len(verts)
    for e in ring:
        verts.append(Vector((verts[e].x, verts[e].y, -0.6)))
    n = len(ring)
    for k in range(n):
        a, b = ring[k], ring[(k + 1) % n]
        faces.append((b, a, base + k, base + (k + 1) % n))
    faces.append(tuple(base + k for k in range(n)))
    keep_part(mesh_object("Drift", verts, faces, SAND), frame="world", weight=0.5, look="sand")
    # the fallen mainmast: from its broken butt over the deck, across the starboard rail, down into the sand
    butt = W((0.9, MAINMAST_Y + 0.4, 8.6))
    rail = W((hb(MAINMAST_Y - 0.4, 8.0) - 0.2, MAINMAST_Y - 0.4, 8.15))
    d = (rail - butt).normalized()
    t_end = (rail.z - 0.45) / -d.z
    tip = rail + d * t_end
    length = (tip - butt).length
    keep_part(tube("MainMast", TIMBER, [butt, rail, rail.lerp(tip, 0.5), tip], [0.5, 0.5, 0.45, 0.4], 8, jag_start=0.35), group="rig", frame="world", look="mast")
    # its top, lying tilted at the mast head; the topmast beyond it, broken; the main yard across, on the sand
    head = butt + d * (length - 1.2)
    side = d.cross(Vector((0, 0, 1))).normalized()
    plat = [head + side * math.sin(a) * 1.3 + d * math.cos(a) * 1.0 for a in [math.radians(x) for x in range(-90, 91, 30)]]
    plat += [head - d * 0.6 + side * 1.3, head - d * 0.6 - side * 1.3]
    keep_part(slab("MainTop", TIMBER, plat, side.cross(d).normalized(), 0.18), group="rig", frame="world", look="mast")
    tm_a = tip + d * -0.5 + side * 0.5 + Vector((0, 0, 0.0))
    tm_b = tm_a + Vector((d.x, d.y, 0.0)).normalized() * 5.5 + side * 1.2
    tm_b.z = 0.25
    keep_part(tube("MainTopmast", TIMBER, [tm_a, tm_a.lerp(tm_b, 0.5), tm_b], [0.3, 0.26, 0.22], 6, jag=0.3), group="rig", frame="world", look="mast")
    yc = rail + d * (t_end * 0.62)
    across = Vector((-d.y, d.x, 0.0)).normalized()
    ya_ = yc + across * 6.5
    yb_ = yc - across * 6.0
    ya_.z, yb_.z = 0.3, 0.25
    mid = yc.copy()
    mid.z = max(yc.z - 0.55, 0.35)
    keep_part(tube("MainYard", TIMBER, [ya_, ya_.lerp(mid, 0.5), mid, mid.lerp(yb_, 0.5), yb_], [0.1, 0.17, 0.22, 0.17, 0.1], 8), group="rig", frame="world", look="mast")
    # a shred of the mainsail fouled on the yard and lying out over the sand
    sail = [yb_.lerp(mid, 0.2) + Vector((0, 0, 0.18)), yb_.lerp(mid, 0.85) + Vector((0, 0, 0.18))]
    sail += [yb_.lerp(mid, 0.75) + d * 2.2 + Vector((0, 0, 0.04)), yb_.lerp(mid, 0.45) + d * 3.0 + Vector((0, 0, 0.03)), yb_.lerp(mid, 0.25) + d * 1.6 + Vector((0, 0, 0.05))]
    keep_part(slab("MainSail", SAIL, sail, (0.0, 0.0, 1.0), 0.04), group="rig", frame="world", weight=0.9, solid=False, look="sail")
    # its shrouds, from the starboard main channel to the mast head, sagging
    for k, dy in enumerate((-1.0, -0.2, 0.6, 1.4)):
        low = W((hb(MAINMAST_Y + dy, 7.5) + 0.42, MAINMAST_Y + dy, 7.5))
        top = head - d * (0.3 + 0.25 * k) + side * (0.3 * (k - 1.5))
        mid = low.lerp(top, 0.5) - Vector((0, 0, 0.8))
        keep_part(tube("MainShroud", ROPE, [low, low.lerp(mid, 0.6), mid, mid.lerp(top, 0.5), top], 0.05, 4), group="rig", frame="world", weight=0.6, solid=False, look="rope")
    # ropes hanging from the mast either side of the way along her side, down to the sand
    for k, (t, s) in enumerate(((0.3, 1.0), (0.42, -1.0), (0.55, 1.0), (0.62, -1.0))):
        on = rail + d * (t_end * t) + side * s * 0.2
        lowp = on + side * s * 1.0 + d * 0.8
        lowp.z = 0.05
        mid = on.lerp(lowp, 0.5) + side * s * 0.3
        keep_part(tube("Hanging", ROPE, [on, mid, lowp], 0.045, 4), group="rig", frame="world", weight=0.6, solid=False, look="rope")
    # the main stay: from the foremast's head down to the fallen mast
    keep_part(tube("MainStay", ROPE, [W(fore_head), W(fore_head).lerp(head, 0.5) - Vector((0, 0, 1.6)), head], 0.06, 4), group="rig", frame="world", weight=0.6, solid=False, look="rope")
    # the anchor on the sand close under her bow (as in the concept art), its chain taut from the port hawse hole:
    # it lies on its stock's end and one arm, the other fluke dug into the sand
    hawse = W(hull_skin(17.0, 7.2, -1.0, 0.05))
    ring_at = Vector((-3.4, 22.6, 0.45))
    shank_dir = Vector((-0.35, 1.0, 0.0)).normalized()
    crown = ring_at + shank_dir * 2.9 + Vector((0.0, 0.0, -0.2))
    up = Vector((0.0, 0.0, 1.0))
    sideways = shank_dir.cross(up).normalized()
    keep_part(bar("AnchorShank", RUST, [ring_at, crown], 0.2, 0.2), frame="world", look="iron")
    for s in (-1.0, 1.0):
        arm = [crown, crown + up * s * 0.65 - shank_dir * 0.2, crown + up * s * 1.0 - shank_dir * 0.85]
        keep_part(bar("AnchorArm", RUST, arm, 0.17, 0.17, up=tuple(sideways)), frame="world", look="iron")
        keep_part(block("Fluke", RUST, arm[-1] - shank_dir * 0.1, (0.07, 0.55, 0.5), [sideways, shank_dir, up]), frame="world", look="iron")
    keep_part(block("Stock", STAVE, ring_at + shank_dir * 0.35, (2.8, 0.24, 0.24), [sideways, shank_dir, up]), frame="world")
    keep_part(lathe("AnchorRing", [(0.25, -0.05), (0.25, 0.05)], ring_at - shank_dir * 0.15, 8, RUST, axis=[shank_dir, up, sideways]), frame="world", look="iron")
    chain = [hawse, hawse.lerp(ring_at, 0.35) + Vector((0, 0, -0.3)), hawse.lerp(ring_at, 0.7) + Vector((0, 0, -0.3)), ring_at - shank_dir * 0.35]
    keep_part(tube("Chain", RUST, chain, 0.1, 4), frame="world", weight=0.6, solid=False, look="iron")
    # a chest of gold fallen out of the breach in her side onto the sand, coins spilled (as in the concept art)
    n = len(PARTS)
    chest("SandGold", Vector((-7.8, 9.6, -0.05)), 0.7, math.radians(105.0))
    rng = random.Random(31)
    for k in range(5):
        coin(Vector((-7.8 + rng.uniform(-1.2, 1.4), 9.6 + rng.uniform(-1.6, 0.6), 0.0)), rng.uniform(0.0, 0.3), rng.uniform(0, 3))
    for p in PARTS[n:]:
        p["frame"] = "world"
    # what spilled out of her: barrels, a chest, shot, a gun, a broken spar, planks
    def barrel(at, lying=0.0, turn=0.0, buried=0.0):
        ax = [Matrix.Rotation(turn, 3, "Z") @ a for a in turned("X", lying)]
        prof = [(0.3, 0.0), (0.32, 0.08), (0.39, 0.47), (0.32, 0.86), (0.3, 0.94)]
        c = Vector(at) - ax[2] * buried
        keep_part(lathe("Barrel", prof, c, 8, STAVE, row_mats=[RUST, STAVE, STAVE, RUST]), frame="world", look="barrel")
    barrel((-4.6, -20.5, 0.0), 0.0, 0.0, 0.15)
    barrel((-5.6, -19.2, 0.38), math.radians(90), 0.6)
    barrel((-3.2, -22.6, 0.36), math.radians(88), -0.4)
    barrel((13.0, -9.0, 0.37), math.radians(90), 1.2)
    barrel((-8.2, 1.4, 0.36), math.radians(92), 2.0)
    chest("SandChest", Vector((-6.3, -17.0, -0.12)), 0.5, math.radians(25.0), full=False)
    for p in PARTS[-4:]:
        if p["obj"].name.startswith("SandChest"):
            p["group"] = "hull"
            p["frame"] = "world"
            p["solid"] = True
    shot = []
    for i, (x, y) in enumerate(((0, 0), (0.34, 0), (0.68, 0), (0.17, 0.3), (0.51, 0.3), (0.34, 0.6))):
        shot.append(Vector((x, y, 0.15)))
    shot += [Vector((0.17, 0.1, 0.42)), Vector((0.51, 0.1, 0.42)), Vector((0.34, 0.4, 0.42)), Vector((0.34, 0.2, 0.68))]
    for p in shot:
        bpy.ops.mesh.primitive_uv_sphere_add(segments=5, ring_count=3, radius=0.16, location=Vector((-5.0, -14.5, 0.0)) + p)
        bpy.context.object.data.materials.append(RUST)
        keep_part(bpy.context.object, frame="world", look="iron")
    for x, y in ((-3.6, -24.0), (12.5, -3.2), (-6.9, -11.0)):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=5, ring_count=3, radius=0.16, location=(x, y, 0.12))
        bpy.context.object.data.materials.append(RUST)
        keep_part(bpy.context.object, frame="world", look="iron")
    gun("SandGun", (6.0, -19.5, 0.18), (0.4, -0.9, 0.05), False)
    for p in PARTS:
        if p["obj"].name.startswith("SandGun"):
            p["frame"] = "world"
    keep_part(tube("Spar", TIMBER, [(-8.5, -6.0, 0.15), (-9.6, -1.0, 0.2)], [0.2, 0.16], 6, jag=0.3, jag_start=0.3), frame="world", look="mast")
    keep_part(block("Plank", DECK, (-6.5, -8.5, 0.05), (0.32, 3.0, 0.08), turned("Z", 0.4)), frame="world")
    keep_part(block("Plank", DECK, (11.0, -12.5, 0.08), (0.32, 2.4, 0.08), turned("Z", -0.9)), frame="world")


# ======================================================================== checks, unwrapping, the bake
def triangles(obj):
    obj.data.calc_loop_triangles()
    return len(obj.data.loop_triangles)


def inside_out(obj):
    """How many of a closed part's faces face inwards (a line out of each must leave its skin an even number of
    times), and how many were looked at."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.normal_update()
    tree = BVHTree.FromBMesh(bm)
    wrong = counted = 0
    for f in bm.faces:
        if f.calc_area() < 1e-8:
            continue
        counted += 1
        at = f.calc_center_median() + f.normal * 2e-5
        hits = 0
        while hits < 60:
            hit = tree.ray_cast(at, f.normal)
            if hit[0] is None:
                break
            hits += 1
            at = hit[0] + f.normal * 2e-5
        if hits % 2:
            wrong += 1
            if wrong <= 4:
                print('PIRATE inside-out face of %s at %s, area %.4f' % (obj.name, tuple(round(v, 2) for v in f.calc_center_median()), f.calc_area()))
    bm.free()
    return wrong, counted


OWNERS = []


def world_tris(objs, owners=None):
    verts = []
    tris = []
    for obj in objs:
        mw = obj.matrix_world
        me = obj.data
        me.calc_loop_triangles()
        base = len(verts)
        verts.extend([mw @ v.co for v in me.vertices])
        tris.extend([(base + t.vertices[0], base + t.vertices[1], base + t.vertices[2]) for t in me.loop_triangles])
        if owners is not None:
            owners.extend([obj.name] * len(me.loop_triangles))
    return verts, tris


RAY_DIR = Vector((0.0131, 0.0217, 1.0)).normalized()


def depth_at(tree, p, start_dir=RAY_DIR):
    """How many closed solids a point is inside (rays out, counting exits less entries)."""
    count = 0
    at = Vector(p)
    for _ in range(80):
        hit = tree.ray_cast(at, start_dir)
        if hit[0] is None:
            break
        count += 1 if hit[1].dot(start_dir) > 0.0 else -1
        at = hit[0] + start_dir * 1e-4
    return count


def column_runs(tree, x, y, z0=-6.0):
    """Where a vertical line at (x, y) is inside the solids: a list of (from, to) heights."""
    at = Vector((x, y, z0))
    up = Vector((0.0, 0.0, 1.0))
    depth = 0
    runs = []
    start = None
    for _ in range(200):
        hit = tree.ray_cast(at, up)
        if hit[0] is None:
            break
        if hit[1].z < 0.0:
            depth += 1
            if depth == 1:
                start = hit[0].z
        else:
            depth -= 1
            if depth == 0 and start is not None:
                runs.append((start, hit[0].z))
                start = None
        at = hit[0] + up * 1e-4
    return runs


def segment_distance(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.length_squared, 1e-9)))
    return (p - (a + ab * t)).length


def fit_spheres(solids, cutters, routes):
    """Spheres that fill the solid parts: chosen greedily, each as big as it may be (never more than SLACK_IN into a
    space inside her, BULGE into open sea, or anything into a swim route), until every point of the solid on a GRID
    is inside one."""
    OWNERS.clear()
    verts, tris = world_tris(solids, OWNERS)
    tree = BVHTree.FromPolygons(verts, tris)
    cv, ct = world_tris(cutters)
    cut_tree = BVHTree.FromPolygons(cv, ct)
    xs = [v.x for v in verts]
    ys = [v.y for v in verts]
    zs = [v.z for v in verts]
    lo = Vector((min(xs) - 1.0, min(ys) - 1.0, 0.05))
    hi = Vector((max(xs) + 1.0, max(ys) + 1.0, max(zs)))
    # the solid's points on the grid
    inside = []
    nx = int((hi.x - lo.x) / GRID) + 1
    ny = int((hi.y - lo.y) / GRID) + 1
    for i in range(nx):
        x = lo.x + i * GRID
        for j in range(ny):
            y = lo.y + j * GRID
            for a, b in column_runs(tree, x, y):
                k0 = max(0, math.ceil((max(a, lo.z) - lo.z) / GRID))
                k1 = math.floor((b - lo.z) / GRID)
                for k in range(k0, k1 + 1):
                    inside.append(Vector((x, y, lo.z + k * GRID)))
    # samples of the skin, each facing a space inside her or open sea
    cav = []
    sea = []
    rng = random.Random(5)
    for t in tris:
        a, b, c = verts[t[0]], verts[t[1]], verts[t[2]]
        n = (b - a).cross(c - a)
        area = n.length * 0.5
        if area < 1e-6:
            continue
        n.normalize()
        count = max(1, int(area / 0.02))
        for _ in range(count):
            u, v = rng.random(), rng.random()
            if u + v > 1.0:
                u, v = 1.0 - u, 1.0 - v
            p = a + (b - a) * u + (c - a) * v
            if p.z < -0.05:
                continue
            q = p + n * 0.12
            if depth_at(tree, q) > 0:
                continue
            (cav if depth_at(cut_tree, q) > 0 else sea).append(p)
    cav_tree = KDTree(len(cav))
    for i, p in enumerate(cav):
        cav_tree.insert(p, i)
    cav_tree.balance()
    sea_tree = KDTree(len(sea))
    for i, p in enumerate(sea):
        sea_tree.insert(p, i)
    sea_tree.balance()
    # the routes' tubes: capsules
    caps = []
    for route in routes:
        pts = route["points"]
        for a, b in zip(pts, pts[1:]):
            side = route["side"]
            for off in (-ROUTE_SIDE, 0.0, ROUTE_SIDE):
                caps.append((a + side * off, b + side * off))

    def d_route(p):
        return min(segment_distance(p, a, b) for a, b in caps) - ROUTE_R

    def reach(p, is_inside):
        dc = cav_tree.find(p)[2] if cav else 99.0
        ds = sea_tree.find(p)[2] if sea else 99.0
        r = min(dc + SLACK_IN, (ds + BULGE) if is_inside else (BULGE - ds), R_CAP)
        if r > 0.1:
            r = min(r, d_route(p))
        return r
    # candidate middles: the solid's grid points, and points just outside its sea-facing skin
    cands = [(p, reach(p, True)) for p in inside]
    seen = set()
    for p in sea[::3]:
        n = Vector((0.0, 0.0, 0.0))
        loc, nrm, _, _ = tree.find_nearest(p)
        if nrm is None:
            continue
        for k in (0.2, 0.45, 0.7):
            q = p + nrm * k
            key = (round(q.x / 0.25), round(q.y / 0.25), round(q.z / 0.25))
            if key in seen or q.z < 0.0:
                continue
            seen.add(key)
            if depth_at(cut_tree, q) > 0 or depth_at(tree, q) > 0:
                continue
            cands.append((q, reach(q, False)))
    cands = [(p, r) for p, r in cands if r > 0.12]
    ctree = KDTree(len(cands))
    for i, (p, r) in enumerate(cands):
        ctree.insert(p, i)
    ctree.balance()
    ttree = KDTree(len(inside))
    for i, p in enumerate(inside):
        ttree.insert(p, i)
    ttree.balance()
    covered = [False] * len(inside)
    order = sorted(range(len(inside)), key=lambda i: -min(cav_tree.find(inside[i])[2] if cav else 9.0, sea_tree.find(inside[i])[2] if sea else 9.0))
    spheres = []
    missed = 0
    for i in order:
        if covered[i]:
            continue
        t = inside[i]
        # the few candidates that hold this point deepest; of them, the one that covers most still uncovered
        options = [(cands[idx][1] - dist, idx) for p, idx, dist in ctree.find_range(t, R_CAP) if cands[idx][1] - dist > 0.04]
        if not options:
            missed += 1
            covered[i] = True
            continue
        options.sort(reverse=True)
        best = None
        best_gain = -1
        for score, idx in options[:10]:
            c, r = cands[idx]
            gain = sum(1 for p, j, dist in ttree.find_range(c, r + COVER) if not covered[j])
            if gain > best_gain:
                best_gain = gain
                best = idx
        c, r = cands[best]
        spheres.append((c.copy(), r))
        for p, idx, dist in ttree.find_range(c, r + COVER):
            covered[idx] = True
        covered[i] = True
    # drop spheres whose every point another sphere covers too (smallest first)
    count = [0] * len(inside)
    holds = []
    for c, r in spheres:
        mine = [j for p, j, dist in ttree.find_range(c, r + COVER)]
        holds.append(mine)
        for j in mine:
            count[j] += 1
    keep = [True] * len(spheres)
    for k in sorted(range(len(spheres)), key=lambda k: spheres[k][1]):
        if holds[k] and all(count[j] > 1 for j in holds[k]):
            keep[k] = False
            for j in holds[k]:
                count[j] -= 1
    dropped = keep.count(False)
    spheres = [s for s, kept in zip(spheres, keep) if kept]
    print("PIRATE spheres %d (%d more dropped as covered twice) from %d solid points (%d could not be covered), %d skin samples facing inside, %d facing the sea"
          % (len(spheres), dropped, len(inside), missed, len(cav), len(sea)))
    return spheres, tree


def route_checks(routes, spheres, tree):
    """Points along each route that must be clear: its middle (room ROUTE_R - 0.02), and either side and above and
    below it (room 0.02). Checked here against the spheres and against the solid itself."""
    checks = []
    worst = {}
    for route in routes:
        pts = route["points"]
        side = route["side"]
        up = route["up"]
        name = route["name"]
        for a, b in zip(pts, pts[1:]):
            steps = max(1, int((b - a).length / 0.4))
            for k in range(steps + 1):
                p = a.lerp(b, k / steps)
                for q, room in ((p, ROUTE_R - 0.02), (p + side * 1.1, 0.02), (p - side * 1.1, 0.02), (p + up * 0.88, 0.02), (p - up * 0.88, 0.02)):
                    checks.append((name, q, room))
    bad = 0
    why = {}
    for name, q, room in checks:
        hit = any((q - c).length < r + room for c, r in spheres)
        loc, _, index, _ = tree.find_nearest(q)
        mesh_clear = (loc - q).length if loc is not None else 99.0
        inside_solid = depth_at(tree, q) > 0
        if hit or inside_solid or (room > 0.5 and mesh_clear < room) or q.z < room:
            bad += 1
            key = '%s: %s%s%s near %s' % (name, 'sphere ' if hit else '', 'inside ' if inside_solid else '', 'close ' if mesh_clear < room else '', OWNERS[index] if index is not None else '-')
            why[key] = why.get(key, 0) + 1
        if room > 0.5:
            worst[name] = min(worst.get(name, 99.0), mesh_clear)
    for name in worst:
        print("PIRATE route %s: the solid is at least %.2f m from its middle line" % (name, worst[name]))
    for key in sorted(why):
        print('PIRATE blocked %s (%d)' % (key, why[key]))
    print("PIRATE routes: %d check points, %d blocked" % (len(checks), bad))
    return checks, bad


def unwrap_all(parts):
    meshes = [p["obj"] for p in parts]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60.0), island_margin=0.002)
    bpy.ops.uv.average_islands_scale()
    bpy.ops.object.mode_set(mode="OBJECT")
    # more texels where they are looked at (the stern, the figurehead, the treasure), fewer where buried
    for p in parts:
        w = p["weight"]
        if abs(w - 1.0) < 1e-3:
            continue
        uv = p["obj"].data.uv_layers.active.data
        for loop in uv:
            loop.uv = loop.uv * w


def pack_all(objs):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objs:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(rotate=True, rotate_method="ANY", shape_method="CONCAVE", margin=0.001)
    bpy.ops.object.mode_set(mode="OBJECT")


def texel_density(parts_by_look):
    out = {}
    for look, faces in parts_by_look.items():
        uv_area = sum(a for a, w in faces)
        world_area = sum(w for a, w in faces)
        if world_area > 0:
            out[look] = math.sqrt(uv_area * ATLAS_SIZE * ATLAS_SIZE / world_area)
    return out


def bake_atlas(objs, lights_at):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 64
    scene.cycles.device = "CPU"
    world = bpy.data.worlds.new("sea")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.8, 0.88, 0.95, 1.0)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.55
    scene.world = world
    temp = []
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 2.6
    sun.angle = math.radians(14.0)
    lamp = bpy.data.objects.new("sun", sun)
    bpy.context.collection.objects.link(lamp)
    lamp.rotation_euler = (math.radians(-18.0), math.radians(-12.0), 0.0)
    temp.append(lamp)
    for k, p in enumerate(lights_at):
        lt = bpy.data.lights.new("fill%d" % k, "POINT")
        lt.energy = 110.0
        lt.color = (1.0, 0.92, 0.78)
        lt.shadow_soft_size = 0.6
        o = bpy.data.objects.new("fill%d" % k, lt)
        o.location = p
        bpy.context.collection.objects.link(o)
        temp.append(o)
    bpy.ops.mesh.primitive_plane_add(size=120.0, location=(0.0, 0.0, -0.02))
    floor = bpy.context.object
    floor.data.materials.append(SAND)
    temp.append(floor)
    image = bpy.data.images.new(os.path.basename(ATLAS), ATLAS_SIZE, ATLAS_SIZE, alpha=False)
    for made in bpy.data.materials:
        if not made.use_nodes:
            continue
        node = made.node_tree.nodes.new("ShaderNodeTexImage")
        node.image = image
        made.node_tree.nodes.active = node
    scene.render.bake.margin = 4
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objs:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.bake(type="COMBINED", use_clear=True)
    os.makedirs(os.path.dirname(ATLAS), exist_ok=True)
    image.filepath_raw = ATLAS
    image.file_format = "PNG"
    image.save()
    for o in temp:
        bpy.data.objects.remove(o, do_unlink=True)
    print("PIRATE baked", ATLAS)


def merge(parts, name):
    objs = [p["obj"] for p in parts]
    # the first ship-frame one leads, so the object keeps the ship's frame (and the lie) for the bake
    lead = next((o for p, o in zip(parts, objs) if p["frame"] == "ship"), objs[0])
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objs:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = lead
    if len(objs) > 1:
        bpy.ops.object.join()
    obj = bpy.context.object
    obj.name = name
    obj.data.name = name
    for poly in obj.data.polygons:
        poly.use_smooth = True
    split = obj.modifiers.new("split", "EDGE_SPLIT")
    split.split_angle = math.radians(40.0)
    bpy.ops.object.modifier_apply(modifier="split")
    return obj


def empty(name, at, normal=None):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.location = at
    if normal is not None:
        obj.rotation_mode = "QUATERNION"
        obj.rotation_quaternion = Vector((0.0, 0.0, 1.0)).rotation_difference(Vector(normal).normalized())
    obj.empty_display_size = 0.4
    return obj


def to_godot(v):
    return [round(v.x, 4), round(v.z, 4), round(-v.y, 4)]


# ======================================================================== build it
hull = build_hull()
build_timbers()
build_guns()
build_lids()
build_stern()
build_decks()
build_bow()
fore_head = build_masts()
build_treasure()

# gun() registered its barrels by name; find any part made but not kept
kept = {id(p["obj"]) for p in PARTS}
for obj in list(bpy.data.objects):
    if obj.type == "MESH" and id(obj) not in kept and obj not in CUTTERS and not obj.name.startswith("SheerTrim"):
        group = "hull"
        PARTS.append({"obj": obj, "group": group, "frame": "ship", "weight": 1.2, "solid": True, "look": "gun"})

# lay the ship as she lies; then what lies on the sand, built where it is
for p in PARTS:
    p["obj"].matrix_world = LIE @ p["obj"].matrix_world
for c in CUTTERS:
    c.matrix_world = LIE @ c.matrix_world
before = len(PARTS)
build_sand(fore_head)
kept = {id(p["obj"]) for p in PARTS}
for obj in list(bpy.data.objects):
    if obj.type == "MESH" and id(obj) not in kept and obj not in CUTTERS:
        PARTS.append({"obj": obj, "group": "hull", "frame": "world", "weight": 1.2, "solid": True, "look": "gun"})
bpy.context.view_layer.update()

# every part a closed solid, faces outwards
wrong_total = 0
for p in PARTS:
    wrong, counted = inside_out(p["obj"])
    if wrong:
        print("PIRATE INSIDE-OUT %s: %d of %d faces" % (p["obj"].name, wrong, counted))
    wrong_total += wrong
print("PIRATE INSIDE-OUT parts %d, faces facing inwards %d" % (len(PARTS), wrong_total))

# the swim routes (world frame): middle lines, which way is "side" and "up" in the ship's own frame
ship_up = (LIE.to_3x3() @ Vector((0, 0, 1))).normalized()
ship_side = (LIE.to_3x3() @ Vector((1, 0, 0))).normalized()
ship_fore = (LIE.to_3x3() @ Vector((0, 1, 0))).normalized()
CAB_Z = (UPPER + CABIN_TOP) * 0.5
GUN_Z = (GUN[0] + GUN[1]) * 0.5
HOLD_Z = (HOLD[0] + HOLD[1]) * 0.5
bow_route_y = W((0.0, 17.3, 0.0)).y
rail_mast = None
routes = [
    {"name": "stern_cabin_waist", "points": [W(p) for p in ((0, -21.5, CAB_Z), (0, -17.0, CAB_Z), (0, -12.0, CAB_Z), (0, -8.25, CAB_Z), (0, -5.6, CAB_Z))], "side": ship_side, "up": ship_up},
    {"name": "fallen_deck_gun_deck", "points": [W(p) for p in ((0, -5.6, CAB_Z), (-0.2, -5.0, GUN_Z), (-2.1, -1.0, GUN_Z), (-2.1, 2.6, GUN_Z), (0, 4.6, GUN_Z), (0, 6.4, GUN_Z))], "side": ship_side, "up": ship_up},
    {"name": "hatch_hold_breach", "points": [W(p) for p in ((0, 6.4, GUN_Z), (0, 6.4, HOLD_Z), (-2.2, 7.4, HOLD_Z), (-7.5, 7.4, HOLD_Z))], "side": ship_fore, "up": ship_up},
    {"name": "under_the_bow", "points": [Vector((-7.5, bow_route_y, 1.15)), Vector((7.5, bow_route_y, 1.15))], "side": Vector((0, 1, 0)), "up": Vector((0, 0, 1))},
    {"name": "fallen_rigging", "points": [Vector((9.6, -11.0, 2.1)), Vector((9.6, 7.0, 2.1))], "side": Vector((1, 0, 0)), "up": Vector((0, 0, 1))},
]
# (the down-the-hatch leg runs vertically: its "side" across it is the ship's fore and aft, and the cabin route's
# first legs run fore and aft: its "side" is athwartships)

def base_name(name):
    return name.split(".")[0].rstrip("0123456789")


solid_objs = [p["obj"] for p in PARTS if base_name(p["obj"].name) in SOLID_NAMES]
by_name = {}
for p in PARTS:
    by_name[base_name(p["obj"].name)] = by_name.get(base_name(p["obj"].name), 0) + triangles(p["obj"])
print("PIRATE triangles by part: " + ", ".join("%s %d" % kv for kv in sorted(by_name.items(), key=lambda kv: -kv[1])))
spheres, solid_tree = fit_spheres(solid_objs, CUTTERS, routes)
checks, blocked = route_checks(routes, spheres, solid_tree)
owner_count = {}
for c, r in spheres:
    index = solid_tree.find_nearest(c)[2]
    key = base_name(OWNERS[index]) if index is not None else "-"
    owner_count[key] = owner_count.get(key, 0) + 1
print("PIRATE spheres by part: " + ", ".join("%s %d" % kv for kv in sorted(owner_count.items(), key=lambda kv: -kv[1])))

# triangles
tri = {"hull": 0, "rig": 0, "treasure": 0}
for p in PARTS:
    tri[p["group"]] += triangles(p["obj"])
print("PIRATE triangles: hull %d, rig %d, treasure %d, all %d" % (tri["hull"], tri["rig"], tri["treasure"], sum(tri.values())))

# unwrap, then join into the three objects, pack, bake
unwrap_all(PARTS)
looks = {}
for p in PARTS:
    obj = p["obj"]
    me = obj.data
    uv = me.uv_layers.active.data
    mw = obj.matrix_world
    for poly in me.polygons:
        pts = [uv[i].uv for i in poly.loop_indices]
        a = 0.0
        for k in range(1, len(pts) - 1):
            a += abs((pts[k] - pts[0]).cross(pts[k + 1] - pts[0])) * 0.5
        w = poly.area * mw.to_scale()[0] ** 2
        looks.setdefault(p["look"], []).append((a, w))
groups = {}
for p in PARTS:
    groups.setdefault(p["group"], []).append(p)
hull_obj = merge(groups["hull"], "PirateHull")
rig_obj = merge(groups["rig"], "PirateRig")
treasure_obj = merge(groups["treasure"], "PirateTreasure")
finals = [hull_obj, rig_obj, treasure_obj]
pack_all(finals)
# texel density after packing: scale the per-look sums by how much packing shrank everything
total_uv_before = sum(a for faces in looks.values() for a, w in faces)
total_uv_after = 0.0
for obj in finals:
    uv = obj.data.uv_layers.active.data
    for poly in obj.data.polygons:
        pts = [uv[i].uv for i in poly.loop_indices]
        for k in range(1, len(pts) - 1):
            total_uv_after += abs((pts[k] - pts[0]).cross(pts[k + 1] - pts[0])) * 0.5
shrink = total_uv_after / max(total_uv_before, 1e-9)
density = texel_density({k: [(a * shrink, w) for a, w in v] for k, v in looks.items()})
print("PIRATE texels per metre: " + ", ".join("%s %.0f" % (k, v) for k, v in sorted(density.items())) + " (atlas %d, %.0f%% of it used)" % (ATLAS_SIZE, 100.0 * total_uv_after))

if BAKE:
    fills = [W((1.6, -13.0, CABIN_TOP - 0.75)), W((0.0, -10.0, GUN_Z)), W((0.0, 2.0, GUN_Z)), W((0.0, 10.0, GUN_Z)), W((1.6, 8.0, HOLD[1] - 0.75))]
    bake_atlas(finals, fills)

# lie the meshes down for good: the objects' frames become the world's
for obj in finals:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# how much open water is overhead at each point (0 indoors, 1 under the open sky): the shader lets the sun's
# ripples fall only where the sky shows. Kept as the colour of each point (COLOR_0 in the glTF).
sky_verts, sky_tris = world_tris(finals)
sky_tree = BVHTree.FromPolygons(sky_verts, sky_tris)
SKY_RAYS = [Vector((0.0, 0.0, 1.0)), Vector((0.35, 0.2, 1.0)).normalized(), Vector((-0.3, -0.25, 1.0)).normalized(), Vector((0.1, -0.4, 1.0)).normalized()]
for obj in finals:
    me = obj.data
    attr = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
    me.color_attributes.active_color = attr
    me.color_attributes.render_color_index = me.color_attributes.find("Col")
    attr = me.color_attributes["Col"]
    for v in me.vertices:
        start = v.co + v.normal * 0.06
        seen = sum(1 for d in SKY_RAYS if sky_tree.ray_cast(start, d)[0] is None) / len(SKY_RAYS)
        attr.data[v.index].color = (seen, seen, seen, 1.0)

# empties: reef spots (on upward faces, spread out, clear of the routes), fish spots, the treasure, the lanterns
bvh_verts, bvh_tris = world_tris([hull_obj, rig_obj])
look_tree = BVHTree.FromPolygons(bvh_verts, bvh_tris)
cands = []
for i in range(-10, 23):
    for j in range(-26, 28):
        x = i * 1.0 + 0.37 * ((j * 7) % 3)
        y = j * 1.0 + 0.29 * ((i * 5) % 3)
        hit = look_tree.ray_cast(Vector((x, y, 40.0)), Vector((0, 0, -1)))
        if hit[0] is None or hit[1].z < 0.55 or hit[0].z < 0.4:
            continue
        p = hit[0]
        near_route = False
        for route in routes:
            for a, b in zip(route["points"], route["points"][1:]):
                if segment_distance(p, a, b) < ROUTE_R + 1.6:
                    near_route = True
        if near_route or (p - W(HOARD)).length < 4.0:
            continue
        cands.append((p, hit[1]))
picked = [max(cands, key=lambda c: c[0].z)]
while len(picked) < 24 and len(picked) < len(cands):
    best = max(cands, key=lambda c: min((c[0] - q[0]).length for q in picked))
    picked.append(best)
for k, (p, n) in enumerate(picked):
    empty("ReefSpot%02d" % k, p, n)
fish_at = [W((0, -12.5, CAB_Z)), W((0, -12.0, GUN_Z)), W((0.0, 12.0, GUN_Z)), W((-1.5, 4.0, HOLD_Z)),
           Vector((0.0, bow_route_y, 1.2)), Vector((9.6, -3.0, 2.1)), W((0.0, -3.5, UPPER + 1.6)), W((-6.5, -15.0, 3.0))]
for k, p in enumerate(fish_at):
    empty("FishSpot%02d" % k, p)
empty("TreasureSpot", W(HOARD + Vector((0.0, 0.0, 0.35))))
for k, p in enumerate((W((-2.25, stern_y(11.3) - 0.2, 12.45)), W((2.25, stern_y(11.3) - 0.2, 12.45)), W((1.6, -13.0, CABIN_TOP - 0.45)), W((1.6, 8.0, HOLD[1] - 0.45)))):
    empty("Lantern%02d" % k, p)

# what the game reads: spheres, route checks, views for the test
views = {
    "cabin": [W((0.6, -9.2, CAB_Z + 0.2)), W((0.0, -20.0, CAB_Z - 0.1))],
    "gundeck": [W((-0.5, -13.5, GUN_Z + 0.3)), W((0.0, 4.0, GUN_Z - 0.4))],
    "hold": [W((-2.8, 4.2, HOLD_Z + 0.5)), W(HOARD + Vector((0.0, 0.0, 0.3)))],
    "waist": [W((-3.0, -8.2, UPPER + 3.2)), W((0.0, 0.0, GUN_Z))],
    "rigging": [Vector((9.6, -13.5, 2.6)), Vector((9.6, 2.0, 1.8))],
    "bow_under": [Vector((-9.0, bow_route_y - 2.5, 1.4)), Vector((2.0, bow_route_y, 1.6))],
    "stern_close": [W((0.0, -27.0, 9.0)), W((0.0, -17.5, 9.0))],
    "figurehead": [W((-5.0, 25.0, 9.5)), W((0.0, 21.0, 8.3))],
    "breach": [W((-11.0, 7.4, HOLD_Z + 1.0)), W((-3.0, 7.4, HOLD_Z))],
}
data = {
    "spheres": [to_godot(c) + [round(r, 3)] for c, r in spheres],
    "checks": [to_godot(q) + [room] for name, q, room in checks],
    "routes": {r["name"]: [to_godot(p) for p in r["points"]] for r in routes},
    "views": {k: [to_godot(a), to_godot(b)] for k, (a, b) in views.items()},
}
with open(DATA, "w") as f:
    json.dump(data, f)
print("PIRATE wrote", DATA)

xs = [v.co.x for o in finals for v in o.data.vertices]
ys = [v.co.y for o in finals for v in o.data.vertices]
zs = [v.co.z for o in finals for v in o.data.vertices]
print("PIRATE bounds x %.1f..%.1f, along %.1f..%.1f (Blender y: bow +), up to %.1f m above the sand" % (min(xs), max(xs), min(ys), max(ys), max(zs)))
print("PIRATE final triangles: " + ", ".join("%s %d" % (o.name, triangles(o)) for o in finals) + ", all %d" % sum(triangles(o) for o in finals))

os.makedirs(os.path.dirname(BLEND), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=BLEND)
bpy.ops.object.select_all(action="DESELECT")
for obj in bpy.data.objects:
    if obj in finals or obj.type == "EMPTY":
        obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=GLB, export_format="GLB", export_apply=True, export_yup=True, use_selection=True, export_image_format="NONE", export_vertex_color="ACTIVE")
print("PIRATE wrote", GLB)
