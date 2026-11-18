"""The three figures of the title scene: the boy from Warren, a sea captain and an old-time diver, all on the shared
skeleton, built in Blender from the existing figures. See tools/TITLE_FIGURES.md (with the design sheets).

    blender -b --factory-startup --python tools/build_title_figures.py

Writes tools/blend/title_figures.blend (all three, editable, a collection each) and models/title_boy.glb,
title_captain.glb, title_diver.glb. Then `godot --headless --path . --import`.

Where each comes from (read in place, never copied or changed):
- The boy: GameCommon's boy (character controller, models/boy_tp.glb and boy.glb) as Warren turns him out
  (Warren's scripts/looks.gd): HeadShape "inside_round", the bowl cut, Warren's colours.
- The captain and the diver: GameCommon's man (godot/man, models/man.glb: Gloaming's man, on the boy's skeleton),
  his skeleton, his build keys, his hands, and garments grown from his own body's surface (as build_man.py cuts his
  braies from his skin and stands them off it). The captain wears the man's own `legs__trousers` piece (trousers
  into boots) and the boy's mask head (boy.glb `boy_head__base`, as HeadShape reshapes it) sized to a man, with a big
  nose and a beard. The diver's gear is new (nothing like it exists): built with build_character.py's Builder.

Godot space in all the sums (metres as modelled, Y up, he faces +Z, +X is his left); the man is modelled 1.25 m
tall and stood at 1.44 times that by TitleFigures.
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
COMMON = "C:/Projects/GameCommon/godot/character-controller/files"
MAN = "C:/Projects/GameCommon/godot/man/files/models/man.glb"
sys.path.insert(0, os.path.join(COMMON, "tools"))
import build_character as kit  # noqa: E402

X, Y, Z = kit.X, kit.Y, kit.Z
G = kit.from_blender
B = kit.to_blender


def ease(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


# =====================================================================================================
# Shared helpers
# =====================================================================================================

def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    return [o for o in bpy.data.objects if o not in before]


def make_material(name, srgb, metallic=0.0, roughness=1.0):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    colour = tuple(kit.linear(c) for c in srgb) + (1.0,)
    shader = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    shader.inputs["Base Color"].default_value = colour
    shader.inputs["Roughness"].default_value = roughness
    shader.inputs["Metallic"].default_value = metallic
    material.diffuse_color = colour
    return material


def settle(o):
    """Bakes an imported object's place into its points and frees it of parent and modifiers."""
    o.data.transform(o.matrix_world)
    o.parent = None
    o.matrix_world = Matrix.Identity(4)
    for m in list(o.modifiers):
        o.modifiers.remove(m)


def weld(o):
    """Joins the points the glTF split at every seam, so a surface grown from it can be stood off whole."""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.to_mesh(o.data)
    bm.free()


def activate(o):
    for other in bpy.context.view_layer.objects:
        other.select_set(False)
    bpy.context.view_layer.objects.active = o
    o.select_set(True)


def apply_keys(o, values):
    """Sets the shape keys (the man's build) and bakes the mix in."""
    if not o.data.shape_keys:
        return
    blocks = o.data.shape_keys.key_blocks
    basis = [Vector(d.co) for d in blocks[0].data]
    mixed = [p.copy() for p in basis]
    for key in blocks[1:]:
        share = values.get(key.name, 0.0)
        if share:
            for i, d in enumerate(key.data):
                mixed[i] += (d.co - basis[i]) * share
    o.shape_key_clear()
    for v, p in zip(o.data.vertices, mixed):
        v.co = p
    o.data.update()


def copy_of(o, name):
    made = o.copy()
    made.data = o.data.copy()
    made.name = name
    made.data.name = name
    bpy.context.scene.collection.objects.link(made)
    return made


def keep_only(o, keep):
    """Deletes the faces whose middle (Godot space) `keep` refuses, and the points left loose."""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    gone = [f for f in bm.faces if not keep(G(f.calc_center_median()))]
    bmesh.ops.delete(bm, geom=gone, context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    bm.to_mesh(o.data)
    bm.free()


def stand_off(o, thickness, smooth=0, lam=0.5):
    """Moves every point out along its normal by thickness(point), then smooths (the border held)."""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.normal_update()
    moves = [(v, v.normal.copy() * thickness(G(v.co))) for v in bm.verts]
    for v, d in moves:
        v.co += d
    inner = [v for v in bm.verts if not v.is_boundary]
    for _ in range(smooth):
        bmesh.ops.smooth_vert(bm, verts=inner, factor=lam, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.normal_update()
    bm.to_mesh(o.data)
    bm.free()


def cut(o, point, normal):
    """Cuts an object by a plane (Godot space) and keeps what lies on the side the normal points to."""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=B(point), plane_no=B(normal),
                           clear_inner=True)
    bm.to_mesh(o.data)
    bm.free()


def sleeve_at(o, x, band=0.006):
    """Where a sleeve (held out along x, T pose) is at x: its middle and its largest radius there."""
    near = [G(v.co) for v in o.data.vertices if abs(G(v.co).x - x) < band]
    c = sum(near, Vector()) / len(near)
    c.x = x
    r = max(Vector((0.0, p.y - c.y, p.z - c.z)).length for p in near)
    return c, r


_TREES = {}


def nearest_weights(o, p):
    """The skin weights of the point of `o` nearest p (for a piece made to lie on it)."""
    from mathutils import kdtree
    if o.name not in _TREES:
        tree = kdtree.KDTree(len(o.data.vertices))
        for v in o.data.vertices:
            tree.insert(G(v.co), v.index)
        tree.balance()
        _TREES[o.name] = tree
    _, index, _ = _TREES[o.name].find(p)
    names = {g.index: g.name for g in o.vertex_groups}
    return {names[g.group]: g.weight for g in o.data.vertices[index].groups if g.group in names}


def decimate(o, tris):
    now = kit.triangle_count(o.data)
    if now <= tris:
        return
    m = o.modifiers.new("decimate", "DECIMATE")
    m.ratio = tris / now
    m.use_symmetry = True
    m.symmetry_axis = "X"
    activate(o)
    bpy.ops.object.modifier_apply(modifier=m.name)


def recolour(o, by_name, fallback):
    for i, slot in enumerate(o.material_slots):
        base = slot.material.name.split(".")[0] if slot.material else ""
        o.data.materials[i] = by_name.get(base, fallback)


def smooth_shade(o):
    for poly in o.data.polygons:
        poly.use_smooth = True


def from_builder(name, builder, fuse, material, weigh):
    """A Builder's shapes as an object of their own, one material, skin weights from weigh(point) -> {bone: share}."""
    mesh = kit.fused(builder, fuse)
    o = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(o)
    mesh.materials.append(material)
    groups = {}
    for v in mesh.vertices:
        for bone, share in weigh(G(v.co)).items():
            if share > 0.001:
                if bone not in groups:
                    groups[bone] = o.vertex_groups.new(name=bone)
                groups[bone].add([v.index], share, "REPLACE")
    smooth_shade(o)
    return o


def held_by_chest(o, edge, reach):
    """Gives the points of `o` above edge(point) (and within `reach` of the middle) to the chest, eased in over a
    few centimetres below it."""
    chest = o.vertex_groups.get("chest") or o.vertex_groups.new(name="chest")
    names = {g.index: g for g in o.vertex_groups}
    for v in o.data.vertices:
        p = G(v.co)
        if abs(p.x) > reach:
            continue
        share = ease(edge(p) - 0.02, edge(p) + 0.04, p.y) * ease(reach, reach - 0.04, abs(p.x))
        if share <= 0.0:
            continue
        old = [(names[g.group], g.weight) for g in v.groups]
        for group, weight in old:
            group.add([v.index], weight * (1.0 - share), "REPLACE")
        have = next((w for g, w in old if g == chest), 0.0)
        chest.add([v.index], have * (1.0 - share) + share, "REPLACE")


def surface_path(o, points, centre_of, off):
    """Points laid on an object's surface: each point (Godot space) moved to where a ray from centre_of(point)
    through it meets the surface, then `off` out along the surface's normal. Gives (points, normals)."""
    tree = BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())
    laid, normals = [], []
    for p in points:
        c = centre_of(p)
        d = (p - c).normalized()
        hit = tree.ray_cast(B(c + d * 0.6), B(-d) - B(Vector()))
        if hit[0] is None:
            laid.append(p)
            normals.append(d)
            continue
        n = (G(hit[1]) - G(Vector())).normalized()
        if n.dot(d) < 0.0:
            n = -n
        laid.append(G(hit[0]) + n * off)
        normals.append(n)
    return laid, normals


def strap(b, points, normals, width, thick, segments=6):
    """A flat strap along points lying on a surface (its face along the normals)."""
    rings = []
    for i, (p, n) in enumerate(zip(points, normals)):
        ahead = (points[min(i + 1, len(points) - 1)] - points[max(i - 1, 0)]).normalized()
        across = ahead.cross(n).normalized()
        rings.append((p, across * width, n * thick))
    b.tube(rings, segments)


def smooth_path(pts, steps=2):
    """A Catmull-Rom curve through the points."""
    out = []
    for i in range(len(pts) - 1):
        p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, len(pts) - 1)]
        for k in range(steps):
            t = k / steps
            out.append(0.5 * (2.0 * p1 + (p2 - p0) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t * t + (3.0 * p1 - p0 - 3.0 * p2 + p3) * t * t * t))
    out.append(pts[-1])
    return out


def rigid(bone):
    return lambda p: {bone: 1.0}


def finish(name, joints, parts, collection, shade=None):
    """Joins a figure's parts into one mesh on a new skeleton at the man's joints (every bone straight up and
    unrotated, kit.make_armature), in its collection. `shade(material, point)` gives each corner a soft tint (a
    vertex colour, multiplied into the material's colour: ribs, stains, patina); 1 leaves it as it is."""
    armature = kit.make_armature(joints)
    armature.name = name + "_armature"
    activate(parts[0])
    for o in parts[1:]:
        o.select_set(True)
    bpy.ops.object.join()
    body = parts[0]
    body.name = name
    body.data.name = name
    mesh = body.data
    for attribute in list(mesh.color_attributes):
        mesh.color_attributes.remove(attribute)
    if shade:
        tint = mesh.color_attributes.new("Tint", "BYTE_COLOR", "CORNER")
        names = [s.material.name.split("_", 1)[1] for s in body.material_slots]
        for poly in mesh.polygons:
            material = names[poly.material_index]
            for li in poly.loop_indices:
                p = G(mesh.vertices[mesh.loops[li].vertex_index].co)
                f = max(0.0, min(1.0, shade(material, p)))
                tint.data[li].color = (f, f, f, 1.0)
        mesh.color_attributes.active_color = tint
        mesh.color_attributes.render_color_index = mesh.color_attributes.find("Tint")
    body.parent = armature
    body.modifiers.new("Armature", "ARMATURE").object = armature
    for o in (armature, body):
        for c in o.users_collection:
            c.objects.unlink(o)
        collection.objects.link(o)
    print("FIGURE %s tris=%d" % (name, kit.triangle_count(body.data)))
    return armature


def extents(o, y, band=0.006, keep=lambda p: True):
    """The span of an object's points near height y: (largest |x|, back z, front z)."""
    pts = [G(v.co) for v in o.data.vertices]
    near = [p for p in pts if abs(p.y - y) < band and keep(p)]
    if not near:
        return None
    return max(abs(p.x) for p in near), min(p.z for p in near), max(p.z for p in near)


# =====================================================================================================
# The man (GameCommon godot/man)
# =====================================================================================================

def import_man(keys):
    """The man's body and his trousers piece, his build set by `keys`, and his joints."""
    made = import_glb(MAN)
    armature = next(o for o in made if o.type == "ARMATURE")
    joints = [(b.name, G(b.head_local), b.parent.name if b.parent else None) for b in armature.data.bones]
    body = next(o for o in made if o.type == "MESH" and o.name.split(".")[0] == "man")
    legs = next(o for o in made if o.type == "MESH" and o.name.split(".")[0] == "man_legs__trousers")
    for o in made:
        if o not in (body, legs):
            bpy.data.objects.remove(o, do_unlink=True)
    for o in (body, legs):
        settle(o)
        apply_keys(o, keys)
        weld(o)
    return joints, body, legs


# His hands, out past the cuffs (he is modelled in a T pose, the wrists at |x| 0.48)
HAND_FROM = 0.445


def hands_of(body, name, skin, size=1.0):
    """His hands, made `size` times bigger about the wrists (the captain's big working hands, the diver's gloves)."""
    hands = copy_of(body, name)
    keep_only(hands, lambda p: abs(p.x) > HAND_FROM)
    wrist = Vector((0.484, 0.934, 0.0))
    for v in hands.data.vertices:
        p = G(v.co)
        w = Vector((math.copysign(wrist.x, p.x), wrist.y, wrist.z))
        grow = 1.0 + (size - 1.0) * ease(HAND_FROM, wrist.x + 0.01, abs(p.x))
        v.co = B(w + (p - w) * grow)
    decimate(hands, 560)
    recolour(hands, {}, skin)
    smooth_shade(hands)
    return hands


# =====================================================================================================
# HeadShape (the boy's mask heads)
# =====================================================================================================

SHAPES = {
    "inside_round": {"chin": 0.15, "forward": 0.15, "jaw": 0.14, "flat": 0.07, "cheek": 0.07, "tall": 0.05, "brow": 0.03},
    "mask_long": {"chin": 0.26, "forward": 0.14, "jaw": 0.3, "flat": 0.2, "cheek": 0.1, "tall": 0.08, "brow": 0.0},
    "mask_brow": {"chin": 0.15, "forward": 0.12, "jaw": 0.2, "flat": 0.26, "cheek": 0.1, "tall": 0.03, "brow": 0.05},
    "inside": {"chin": 0.15, "forward": 0.17, "jaw": 0.15, "flat": 0.25, "cheek": 0.11, "tall": 0.05, "brow": 0.02},
}


def head_shaped(p, centre, reach, how):
    """HeadShape._shaped, line for line (Godot space)."""
    u = Vector(((p.x - centre.x) / reach.x, (p.y - centre.y) / reach.y, (p.z - centre.z) / reach.z))
    front = ease(-0.15, 0.75, u.z)
    low = ease(0.05, -0.95, u.y)
    out = u.copy()
    out.x *= 1.0 - how["jaw"] * low * front
    out.x *= 1.0 - how["cheek"] * front * (1.0 - low) * ease(1.0, 0.0, abs(u.y))
    out.y -= how["chin"] * low * front * front * 1.6
    out.z += how["forward"] * low * front
    flat = how["flat"]
    plane = 1.0 - flat
    if out.z > plane - 0.25:
        over = out.z - (plane - 0.25)
        out.z = plane - 0.25 + over / (1.0 + over * flat * 6.0)
    out.z += how["brow"] * front * ease(0.0, 0.25, u.y) * ease(0.6, 0.3, u.y) * 2.0
    out.y *= 1.0 + how["tall"] * ease(0.0, 1.0, u.y)
    return Vector((centre.x + out.x * reach.x, centre.y + out.y * reach.y, centre.z + out.z * reach.z))


def reshape_head(head, shape):
    points = [G(v.co) for v in head.data.vertices]
    low = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    high = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    centre, reach = (low + high) * 0.5, (high - low) * 0.5
    for v, p in zip(head.data.vertices, points):
        v.co = B(head_shaped(p, centre, reach, SHAPES[shape]))
    head.data.update()


# =====================================================================================================
# The boy, as Warren has him (Warren's scripts/looks.gd, Looks.decode for the first seat).
# =====================================================================================================

BOY_TP = os.path.join(COMMON, "models", "boy_tp.glb")
BOY_FULL = os.path.join(COMMON, "models", "boy.glb")
# Looks: SHIRTS[0], TROUSERS, BOOTS, socks as the trousers, SKIN, HAIR_COLOUR (sRGB, as the rig's colours are)
BOY_COLOURS = {"shirt": (0.37, 0.19, 0.175), "overalls": (0.17, 0.17, 0.19), "boots": (0.17, 0.13, 0.1),
               "socks": (0.17, 0.17, 0.19), "skin": (0.79, 0.65, 0.54), "hair": (0.2, 0.16, 0.13)}
# What shows (CharacterLook.parts_for("bowl", false, "base", "trousers"), with Looks.apply's "over": "none"):
# the hands (the unslotted `boy`), the long body, the boots, the bowl cut; no face, cap, braces or patch.
BOY_KEEP = ("boy", "boy_body__long", "boy_boots")
# ...and these from the full boy.glb, seen close (collapsed, the cut went ragged at its edges)
BOY_FULL_KEEP = ("boy_head__base", "boy_hair__bowl", "boy_hairtop__bowl")
BOY_JOINT = Vector((0.0, 1.012, 0.0))  # the boy's head joint


def build_boy(collection):
    tp = import_glb(BOY_TP)
    full = import_glb(BOY_FULL)
    source_armature = next(o for o in tp if o.type == "ARMATURE")
    joints = [(b.name, G(b.head_local), b.parent.name if b.parent else None) for b in source_armature.data.bones]
    keep = [o for o in tp if o.type == "MESH" and o.name.split(".")[0] in BOY_KEEP]
    fine = [o for o in full if o.type == "MESH" and o.name.split(".")[0] in BOY_FULL_KEEP]
    head = next(o for o in fine if o.name.split(".")[0] == "boy_head__base")
    parts = keep + fine
    for o in parts:
        settle(o)
    for o in tp + full:
        if o not in parts:
            bpy.data.objects.remove(o, do_unlink=True)
    # The head reshaped as Warren's: HeadShape "inside_round" (Warren's Looks.HEAD), from the round head's own bounds.
    reshape_head(head, "inside_round")
    armature = kit.make_armature(joints)
    armature.name = "boy_armature"
    materials = {name: make_material("boy_" + name, colour) for name, colour in BOY_COLOURS.items()}
    for o in parts:
        o.name = o.name.split(".")[0]
        o.data.name = o.name
        recolour(o, materials, materials["skin"])
        smooth_shade(o)
        o.parent = armature
        o.modifiers.new("Armature", "ARMATURE").object = armature
    for o in [armature] + parts:
        for c in o.users_collection:
            c.objects.unlink(o)
        collection.objects.link(o)


# =====================================================================================================
# The captain (design sheet: tools/TITLE_FIGURES.md)
# =====================================================================================================

CAPTAIN_KEYS = {"heavy": 0.5, "body_gut": 0.35, "body_shoulders": 0.3, "body_neck": 0.4}
CAPTAIN_HEAD = "mask_long"
# The boy's head made a man's: this much of the boy's size, its joint on the man's, a little forward.
HEAD_SCALE = 0.64
HEAD_FORWARD = 0.018
CAPTAIN_COLOURS = {
    # (after the concept art, tools/art_src/concept_characters.jpg: muted, a little greyed)
    "skin": (0.76, 0.58, 0.48), "nose": (0.78, 0.46, 0.40), "gansey": (0.14, 0.16, 0.23), "rib": (0.14, 0.16, 0.23),
    "oilskin": (0.70, 0.57, 0.27), "rubber": (0.09, 0.09, 0.09), "beard": (0.80, 0.79, 0.76), "hair": (0.60, 0.59, 0.56),
    "cap": (0.15, 0.17, 0.23), "peak": (0.06, 0.06, 0.07), "brass": (0.66, 0.55, 0.32), "pipe": (0.34, 0.22, 0.14),
    "braces": (0.13, 0.12, 0.11), "steel": (0.45, 0.45, 0.46),
}
# Ribs round the bands: so many to a turn (each a pair of rings of points, dark then light)
RIBS = {"hem": 96, "cuff": 40, "collar": 64}
GANSEY_HEM = 0.535
CUFF = 0.462  # the sleeves end here (|x|, T pose)


def build_captain(collection):
    m = {name: make_material("captain_" + name, c, 0.35 if name in ("brass", "steel") else 0.0, 0.5 if name in ("brass", "steel", "peak", "rubber", "oilskin") else 1.0)
         for name, c in CAPTAIN_COLOURS.items()}
    joints, body, legs = import_man(CAPTAIN_KEYS)
    head_joint = next(at for name, at, _ in joints if name == "head")
    parts = []

    # His hands.
    parts.append(hands_of(body, "captain_hands", m["skin"], 1.15))

    # The gansey, grown from his body: stood off it, smoothed of his muscles, ending at the hem, cuffs and neck.
    gansey = copy_of(body, "captain_gansey")
    keep_only(gansey, lambda p: p.y > GANSEY_HEM - 0.02 and abs(p.x) < CUFF + 0.02 and not (p.y > 0.975 and abs(p.x) < 0.07) and p.y < 1.04)
    # (standing further off over the hips, where his trousers are worn under it)
    stand_off(gansey, lambda p: 0.014 + 0.022 * ease(0.74, 0.6, p.y), smooth=24)
    # (clean edges at the hem and cuffs: cut by planes)
    cut(gansey, Vector((0.0, GANSEY_HEM, 0.0)), Y)
    cut(gansey, Vector((CUFF, 0.0, 0.0)), -X)
    cut(gansey, Vector((-CUFF, 0.0, 0.0)), X)
    decimate(gansey, 1000)
    recolour(gansey, {}, m["gansey"])
    smooth_shade(gansey)
    parts.append(gansey)
    # Ribbed bands at the hem and the cuffs, round the gansey as it is there, a little proud.
    b = kit.Builder()
    hx, hback, hfront = extents(gansey, GANSEY_HEM + 0.012, 0.012)
    hcz, hrz = (hback + hfront) * 0.5, (hfront - hback) * 0.5
    b.tube([kit.upright(0.0, y, hcz, hx + d, hrz + d) for y, d in ((GANSEY_HEM - 0.003, 0.004), (GANSEY_HEM, 0.011), (GANSEY_HEM + 0.036, 0.009), (GANSEY_HEM + 0.04, 0.0))], RIBS["hem"])
    for side in (1.0, -1.0):
        c, r = sleeve_at(gansey, side * (CUFF - 0.02))
        b.tube([(Vector((side * x, c.y, c.z)), Y * (r + d), Z * (r + d)) for x, d in ((CUFF - 0.036, -0.004), (CUFF - 0.032, 0.005), (CUFF - 0.002, 0.005), (CUFF + 0.002, 0.0))], RIBS["cuff"])
    parts.append(from_builder("captain_bands", b, None, m["rib"], lambda p, g=gansey: nearest_weights(g, p)))
    cuff_centres = {}
    for side in (1.0, -1.0):
        cuff_centres[side] = sleeve_at(gansey, side * (CUFF - 0.02))[0]

    # Braces (the concept's): dark straps from clips at the hem over each shoulder, meeting in a Y at his back.
    fx, fback, ffront = extents(gansey, 0.75, 0.02, lambda p: abs(p.x) < 0.2)
    b = kit.Builder()
    clips = kit.Builder()

    def centre_of(p):
        return Vector((0.0, p.y, 0.0)) if p.y < 0.93 else Vector((p.x * 0.35, 0.80, 0.0))

    for s in (1.0, -1.0):
        path = [Vector((s * x, y, z)) for x, y, z in (
            (0.072, GANSEY_HEM + 0.012, 0.2), (0.075, 0.62, 0.2), (0.08, 0.72, 0.2), (0.088, 0.82, 0.2), (0.095, 0.90, 0.15),
            (0.10, 0.95, 0.08), (0.10, 0.985, 0.0), (0.095, 0.95, -0.08), (0.085, 0.90, -0.15), (0.06, 0.83, -0.2),
            (0.028, 0.77, -0.2), (0.004, 0.74, -0.2))]
        laid, normals = surface_path(gansey, smooth_path(path, 2), centre_of, 0.004)
        strap(b, laid, normals, 0.011, 0.0025)
        clip_at, clip_n = laid[0], normals[0]
        clips.ellipsoid(clip_at + clip_n * 0.003 + Vector((0.0, 0.006, 0.0)), Vector((0.012, 0.014, 0.004)), None, 8, 3)
    path = [Vector((0.0, y, -0.2)) for y in (0.745, 0.70, 0.64, 0.59, GANSEY_HEM + 0.012)]
    laid, normals = surface_path(gansey, smooth_path(path, 2), centre_of, 0.004)
    strap(b, laid, normals, 0.012, 0.0025)
    clips.ellipsoid(laid[-1] + normals[-1] * 0.003 + Vector((0.0, 0.006, 0.0)), Vector((0.013, 0.014, 0.004)), None, 8, 3)
    parts.append(from_builder("captain_braces", b, None, m["braces"], lambda p, g=gansey: nearest_weights(g, p)))
    parts.append(from_builder("captain_clips", clips, None, m["steel"], lambda p, g=gansey: nearest_weights(g, p)))

    # The man's own trousers piece, in oilskin and rubber, its top (under the gansey) cut away.
    cut(legs, Vector((0.0, 0.542, 0.0)), -Y)
    # (and its top drawn in a little, so nothing of it shows past the hem under his belly)
    for v in legs.data.vertices:
        p = G(v.co)
        k = 1.0 - 0.14 * ease(0.49, 0.54, p.y)
        v.co = B(Vector((p.x * k, p.y, 0.015 + (p.z - 0.015) * k)))
    decimate(legs, 600)
    recolour(legs, {"hose": m["oilskin"], "boots": m["rubber"]}, m["oilskin"])
    smooth_shade(legs)
    legs.name = "captain_legs"
    parts.append(legs)

    # The boy's mask head, a man's size.
    made = import_glb(BOY_FULL)
    head = next(o for o in made if o.type == "MESH" and o.name.split(".")[0] == "boy_head__base")
    for o in made:
        if o is not head:
            bpy.data.objects.remove(o, do_unlink=True)
    settle(head)
    weld(head)
    reshape_head(head, CAPTAIN_HEAD)
    for v in head.data.vertices:
        p = G(v.co)
        v.co = B(head_joint + (p - BOY_JOINT) * HEAD_SCALE + Vector((0.0, 0.0, HEAD_FORWARD)))
    head.data.update()
    head.name = "captain_head"
    recolour(head, {}, m["skin"])
    smooth_shade(head)
    pts = [G(v.co) for v in head.data.vertices]
    top = max(p.y for p in pts)
    centre_z = (min(p.z for p in pts) + max(p.z for p in pts)) * 0.5
    tree = BVHTree.FromObject(head, bpy.context.evaluated_depsgraph_get())

    def front_at(y, x=0.0):
        hit = tree.ray_cast(B(Vector((x, y, 0.5))), B(Vector((0.0, 0.0, -1.0))) - B(Vector()))
        return G(hit[0]).z if hit[0] else centre_z + 0.06

    nose_y = head_joint.y + (top - head_joint.y) * 0.40
    face = front_at(nose_y)
    print("CAPTAIN head top %.3f centre z %.3f nose y %.3f face z %.3f" % (top, centre_z, nose_y, face))

    # The beard: his face's own surface below the nose, stood off it, thick at the chin, thinning to nothing at its
    # edges; and under the chin, hanging a little.
    mouth_y = nose_y - 0.022
    beard = copy_of(head, "captain_beard")
    keep_only(beard, lambda p: p.y < mouth_y + 0.004 and p.z > centre_z - 0.035)

    def beard_depth(p):
        edge = ease(mouth_y + 0.004, mouth_y - 0.012, p.y) * ease(centre_z - 0.035, centre_z - 0.012, p.z)
        chin = ease(mouth_y, mouth_y - 0.05, p.y)
        return edge * (0.007 + 0.013 * chin)

    stand_off(beard, beard_depth, smooth=3, lam=0.4)
    bm = bmesh.new()
    bm.from_mesh(beard.data)
    for v in bm.verts:
        p = G(v.co)
        hang = ease(mouth_y - 0.03, mouth_y - 0.07, p.y) * ease(centre_z - 0.01, centre_z + 0.03, p.z)
        v.co = B(p + Vector((0.0, -0.012 * hang, 0.006 * hang)))
    bm.to_mesh(beard.data)
    bm.free()
    decimate(beard, 450)
    recolour(beard, {}, m["beard"])
    smooth_shade(beard)

    # His hair, close under the cap at the back and sides: the head's own surface, a little proud.
    hair = copy_of(head, "captain_hair")
    keep_only(hair, lambda p: 1.0 < p.y < top - 0.036 and (p.z < centre_z - 0.012 or (p.y > nose_y - 0.03 and abs(p.x) > 0.048 and p.z < centre_z + 0.008)))
    stand_off(hair, lambda p: 0.008, smooth=3, lam=0.3)
    decimate(hair, 260)
    recolour(hair, {}, m["hair"])
    smooth_shade(hair)
    parts += [beard, hair]

    # The nose: big and round, set on the mask (the one feature it is given).
    b = kit.Builder()
    b.ellipsoid(Vector((0.0, nose_y + 0.012, face - 0.004)), Vector((0.010, 0.020, 0.012)))
    b.ellipsoid(Vector((0.0, nose_y - 0.004, face + 0.008)), Vector((0.017, 0.015, 0.015)))
    for side in (1.0, -1.0):
        b.ellipsoid(Vector((side * 0.011, nose_y - 0.009, face + 0.002)), Vector((0.010, 0.009, 0.010)))
    parts.append(from_builder("captain_nose", b, (0.002, 2, 420), m["nose"], rigid("head")))

    # The moustache: two soft rolls under the nose, into the beard.
    b = kit.Builder()
    for side in (1.0, -1.0):
        b.ellipsoid(Vector((side * 0.014, mouth_y + 0.002, front_at(mouth_y, side * 0.014) + 0.006)), Vector((0.019, 0.008, 0.010)),
                    Matrix.Rotation(side * -0.32, 3, "Z"))
    parts.append(from_builder("captain_moustache", b, (0.002, 2, 300), m["beard"], rigid("head")))

    # The cap: a band round his head, a soft crown standing out over it, a short peak, a cord.
    head_now = bpy.data.objects["captain_head"]
    rings = []
    band_y = top - 0.052
    bx, bback, bfront = extents(head_now, band_y + 0.008, 0.006)
    bcz, brz = (bback + bfront) * 0.5, (bfront - bback) * 0.5
    # (height, how far out past the band, how far forward): a band, then a soft crown flaring over it
    for y, out, fwd in ((band_y, 0.005, 0.0), (band_y + 0.02, 0.006, 0.0), (band_y + 0.034, 0.016, 0.004), (top + 0.004, 0.022, 0.007),
                        (top + 0.014, 0.020, 0.007)):
        rings.append((y, bx + out, brz + out, bcz + fwd))
    rings.append((top + 0.020, rings[-1][1] * 0.8, rings[-1][2] * 0.8, rings[-1][3]))
    rings.append((top + 0.023, rings[-1][1] * 0.45, rings[-1][2] * 0.45, rings[-1][3]))
    b = kit.Builder()
    b.tube([kit.upright(0.0, y, cz, rx, rz) for y, rx, rz, cz in rings], 24)
    parts.append(from_builder("captain_cap", b, None, m["cap"], rigid("head")))
    y0, rx0, rz0, cz0 = rings[0]
    front = cz0 + rz0
    b = kit.Builder()
    peak = [(Vector((0.0, y0 + 0.004 - 0.3 * dz, front - 0.006 + dz)), X * half, Y * 0.0035)
            for dz, half in ((0.0, rx0 * 0.95), (0.016, rx0 * 0.9), (0.03, rx0 * 0.74), (0.04, rx0 * 0.5))]
    b.tube(peak + kit.dome(peak[-1], Z, 0.005, 2), 14)
    parts.append(from_builder("captain_peak", b, None, m["peak"], rigid("head")))
    b = kit.Builder()
    cord = [Vector((math.sin(a) * (rx0 + 0.002), y0 + 0.009, cz0 + math.cos(a) * (rz0 + 0.002))) for a in (-0.85, -0.4, 0.0, 0.4, 0.85)]
    b.strand(cord, [0.0026] * len(cord), 6)
    parts.append(from_builder("captain_cord", b, None, m["brass"], rigid("head")))
    # (what of the head is under the cap is not kept)
    cut(head_now, Vector((0.0, top - 0.03, 0.0)), -Y)
    decimate(head_now, 1200)
    parts.append(head_now)

    # The roll collar of the gansey, round his neck.
    span = extents(body, 1.0, 0.008, lambda p: abs(p.x) < 0.08 and p.z < 0.075)
    nx, nb, nf = span
    ncz, nrz = (nb + nf) * 0.5, (nf - nb) * 0.5
    b = kit.Builder()
    b.tube([kit.upright(0.0, y, ncz, nx + g, nrz + g) for y, g in ((0.955, 0.03), (0.968, 0.036), (0.988, 0.036), (1.006, 0.03), (1.022, 0.022), (1.03, 0.012), (1.034, 0.004))], RIBS["collar"])
    parts.append(from_builder("captain_collar", b, None, m["rib"],
                              lambda p: {"neck": ease(0.97, 1.02, p.y), "chest": 1.0 - ease(0.97, 1.02, p.y)}))

    # A short briar pipe, out of the beard at the left corner of where his mouth would be.
    beard_front = front_at(mouth_y - 0.006, 0.02)
    b = kit.Builder()
    stem = [Vector((0.018, mouth_y - 0.004, beard_front - 0.006)), Vector((0.03, mouth_y - 0.01, beard_front + 0.022)),
            Vector((0.040, mouth_y - 0.016, beard_front + 0.042))]
    b.strand(stem, [0.0032, 0.0035, 0.004], 8)
    bowl = Vector((0.045, mouth_y - 0.012, beard_front + 0.050))
    b.tube([(bowl + Y * y, X * r, Z * r) for y, r in ((-0.012, 0.005), (-0.009, 0.009), (0.003, 0.010), (0.011, 0.009), (0.012, 0.007))], 12)
    parts.append(from_builder("captain_pipe", b, None, m["pipe"], rigid("head")))

    from mathutils import noise

    def rib(a, count):
        # (each point of a band is a rib's ridge or its groove, in turn round it)
        return 0.78 if round(a / math.tau * count) % 2 else 1.0

    def shade(material, p):
        if material == "rib":
            if abs(p.x) > 0.3:
                c = cuff_centres[1.0 if p.x > 0 else -1.0]
                return rib(math.atan2(p.z - c.z, p.y - c.y), RIBS["cuff"])
            if p.y > 0.9:
                return rib(math.atan2((p.z - ncz) / nrz, p.x / nx), RIBS["collar"])
            return rib(math.atan2((p.z - hcz) / hrz, p.x / hx), RIBS["hem"])
        if material == "gansey":
            # knit: faint ribs up and down the body
            return 0.93 + 0.07 * math.cos(math.atan2(p.x, p.z) * 60.0) if abs(p.x) < 0.25 else 1.0
        if material in ("oilskin", "cap"):
            # worn: soft lighter and darker patches
            return 0.92 + 0.1 * noise.noise(p * 9.0)
        return 1.0

    bpy.data.objects.remove(body, do_unlink=True)
    return finish("captain", joints, parts, collection, shade)


# =====================================================================================================
# The diver (design sheet: tools/TITLE_FIGURES.md)
# =====================================================================================================

DIVER_COLOURS = {
    # (after the concept art, tools/art_src/concept_characters.jpg: muted, a little greyed)
    "skin": (0.76, 0.58, 0.48), "suit": (0.55, 0.49, 0.39), "rubber": (0.10, 0.10, 0.10), "copper": (0.64, 0.41, 0.30),
    "brass": (0.70, 0.58, 0.34), "glass": (0.10, 0.13, 0.13), "lead": (0.38, 0.39, 0.40), "leather": (0.36, 0.23, 0.14),
    "boots": (0.30, 0.30, 0.30), "steel": (0.48, 0.48, 0.49), "glove": (0.11, 0.11, 0.11),
}
METAL = {"copper": (0.55, 0.42), "brass": (0.6, 0.38), "glass": (0.0, 0.15), "rubber": (0.0, 0.55), "lead": (0.0, 0.7),
         "steel": (0.5, 0.4), "glove": (0.0, 0.5)}
BOOT_TOP = 0.20
NECK_RING = 1.02


def build_diver(collection):
    m = {name: make_material("diver_" + name, c, *METAL.get(name, (0.0, 1.0))) for name, c in DIVER_COLOURS.items()}
    joints, body, legs = import_man({})
    bpy.data.objects.remove(legs, do_unlink=True)
    at = {name: p for name, p, _ in joints}
    # Black rubber gauntlet gloves (the concept's): his own hands, a size bigger.
    parts = [hands_of(body, "diver_gloves", m["glove"], 1.18)]

    # The dress: grown from his body, stood well off it and smoothed into baggy canvas.
    dress = copy_of(body, "diver_dress")
    keep_only(dress, lambda p: BOOT_TOP - 0.03 < p.y < 1.0 and abs(p.x) < 0.475 and not (p.y > 0.965 and abs(p.x) < 0.08))
    stand_off(dress, lambda p: 0.026, smooth=14, lam=0.6)
    # (under the corselet the dress goes with the chest, as the corselet does, so a raised arm does not push its
    # shoulder out through the copper)
    held_by_chest(dress, lambda p: 0.80 + 0.075 * min(1.0, (abs(p.x) / 0.22) ** 2), 0.17)
    cut(dress, Vector((0.455, 0.0, 0.0)), -X)
    cut(dress, Vector((-0.455, 0.0, 0.0)), X)
    # Black rubber cuffs round the ends of the sleeves.
    b = kit.Builder()
    for side in (1.0, -1.0):
        c, r = sleeve_at(dress, side * 0.44)
        b.tube([(Vector((side * x, c.y, c.z)), Y * (r + d), Z * (r + d)) for x, d in ((0.385, -0.004), (0.39, 0.012), (0.43, 0.014), (0.452, 0.008), (0.458, -0.004))], 14)
    cuffs = from_builder("diver_cuffs", b, None, m["glove"], lambda p, g=dress: nearest_weights(g, p))
    parts.append(cuffs)
    belt = copy_of(dress, "diver_belt")
    keep_only(belt, lambda p: 0.585 < p.y < 0.642 and abs(p.x) < 0.2)
    cut(belt, Vector((0.0, 0.595, 0.0)), Y)
    cut(belt, Vector((0.0, 0.632, 0.0)), -Y)
    stand_off(belt, lambda p: 0.006, smooth=1)
    for piece, tris, mat in ((dress, 950, "suit"), (belt, 180, "leather")):
        decimate(piece, tris)
        recolour(piece, {}, m[mat])
        smooth_shade(piece)
        parts.append(piece)

    # Measure the dress for the corselet, the boots and the belt's fittings.
    torso = lambda p: abs(p.x) < 0.2
    print("DIVER dress spans", [(y, tuple(round(v, 3) for v in (extents(dress, y, 0.008, torso) or (0, 0, 0)))) for y in (0.62, 0.8, 0.86, 0.9, 0.95, 0.98)])
    belt_span = extents(dress, 0.615, 0.01, torso)
    leg_span = extents(dress, BOOT_TOP - 0.015, 0.02, lambda p: p.x > 0.0)
    print("DIVER leg span", leg_span)

    # The corselet: a copper yoke on chest, back and shoulders, its edge riding up over the shoulders.
    profile = []
    for y in (0.80, 0.84, 0.88, 0.92, 0.95):
        rx, back, front = extents(dress, y, 0.01, torso)
        grow = 0.024 + 0.014 * ease(0.84, 0.92, y)
        profile.append((y, max(rx, 0.19) + grow, (front - back) * 0.5 + grow, (front + back) * 0.5))
    cz = profile[-1][3]
    profile += [(0.975, 0.232, 0.142, cz), (0.995, 0.19, 0.124, cz), (1.008, 0.125, 0.1, cz), (NECK_RING - 0.002, 0.088, 0.082, cz)]
    edge_rx, edge_rz = profile[0][1], profile[0][2]

    def lift(p):
        up = 0.075 * min(1.0, (abs(p.x) / edge_rx) ** 2) * kit.blend(0.93, 0.80, p.y)
        return Vector((p.x, p.y + up, p.z))

    b = kit.Builder()
    b.place = lift
    b.tube([kit.upright(0.0, y, z, rx, rz) for y, rx, rz, z in profile], 24)
    parts.append(from_builder("diver_corselet", b, None, m["copper"], rigid("chest")))

    # Brass: the band round the corselet's edge and its twelve studs, the neck ring, the valve, the inlet's
    # goose-neck, the lights' rims and guards, the belt's buckle, the knife's sheath.
    ccz = profile[0][3]
    b = kit.Builder()
    b.place = lift
    b.tube([kit.upright(0.0, y, ccz, edge_rx + d, edge_rz + d) for y, d in ((0.795, 0.0), (0.798, 0.006), (0.822, 0.006), (0.826, 0.0))], 24)
    b.place = None
    for k in range(12):
        a = math.tau * (k + 0.5) / 12
        stud = lift(Vector((math.sin(a) * (edge_rx + 0.007), 0.81, ccz + math.cos(a) * (edge_rz + 0.007))))
        b.ellipsoid(stud, Vector((0.007, 0.007, 0.007)), None, 6, 2)
    b.tube([kit.upright(0.0, y, cz, r, r * 0.95) for y, r in ((NECK_RING - 0.006, 0.086), (NECK_RING - 0.002, 0.096), (NECK_RING + 0.02, 0.096), (NECK_RING + 0.024, 0.088))], 20)
    for centre, normal, radius, bars in LIGHTS(cz):
        u = normal.cross(Y if abs(normal.y) < 0.9 else X).normalized()
        v = normal.cross(u)
        rim = 12 if radius > 0.04 else 8
        ring = [centre + normal * 0.006 + (u * math.cos(a) + v * math.sin(a)) * (radius + 0.006) for a in (math.tau * k / rim for k in range(rim + 1))]
        b.strand(ring, [0.0072] * len(ring), 4)
        for k in range(bars):
            off = (k - (bars - 1) / 2) * radius * 0.55
            b.strand([centre + normal * 0.016 + v * off + u * radius * s for s in (-1.0, 0.0, 1.0)], [0.004] * 3, 4)
    valve = Vector((-0.082, NECK_RING + 0.075, cz + 0.08))
    axis = Vector((-0.75, 0.0, 0.66)).normalized()
    b.tube([(valve + axis * d, Y * r, axis.cross(Y) * r) for d, r in ((0.0, 0.016), (0.028, 0.016), (0.03, 0.02), (0.04, 0.02), (0.042, 0.011))], 10)
    goose = [Vector((0.035, NECK_RING + 0.15, cz - 0.10)), Vector((0.038, NECK_RING + 0.172, cz - 0.13)), Vector((0.04, NECK_RING + 0.168, cz - 0.16))]
    b.strand(goose, [0.015, 0.015, 0.016], 8)
    bx, bback, bfront = belt_span
    b.ellipsoid(Vector((0.0, 0.614, bfront + 0.012)), Vector((0.022, 0.018, 0.007)), None, 8, 3)
    parts.append(from_builder("diver_brass", b, None, m["brass"], lambda p: {"hips": 1.0} if p.y < 0.75 else {"chest": 1.0}))

    # The knife: a brass-tipped sheath and a wooden handle on his right hip (made with the belt's leather).
    b = kit.Builder()
    knife_at = Vector((-bx * 0.72, 0.54, bfront * 0.75))
    turn = Matrix.Rotation(-0.6, 3, "Y")
    b.ellipsoid(knife_at, Vector((0.018, 0.062, 0.011)), turn, 10, 4)
    b.ellipsoid(knife_at + Vector((0.0, 0.085, 0.003)), Vector((0.013, 0.03, 0.012)), turn, 10, 4)
    parts.append(from_builder("diver_knife", b, None, m["leather"], rigid("hips")))

    # The copper bonnet on the neck ring.
    b = kit.Builder()
    base = NECK_RING + 0.024
    bonnet = [(0.0, 0.092), (0.025, 0.106), (0.065, 0.116), (0.105, 0.118), (0.145, 0.112), (0.18, 0.097),
              (0.205, 0.074), (0.221, 0.045), (0.227, 0.02)]
    b.tube([kit.upright(0.0, base + h, cz, r, r * 0.98) for h, r in bonnet], 24)
    parts.append(from_builder("diver_helmet", b, None, m["copper"], rigid("chest")))

    b = kit.Builder()
    for centre, normal, radius, _ in LIGHTS(cz):
        u = normal.cross(Y if abs(normal.y) < 0.9 else X).normalized()
        v = normal.cross(u)
        b.tube([(centre + normal * h, u * r, v * r) for h, r in ((-0.01, radius * 0.98), (0.0, radius), (0.006, radius * 0.9), (0.008, radius * 0.5))], 10)
    parts.append(from_builder("diver_glass", b, None, m["glass"], rigid("chest")))

    # Lead weights hung front and back of the corselet.
    b = kit.Builder()
    for sign, z_edge in ((1.0, ccz + edge_rz), (-1.0, ccz - edge_rz)):
        rings = []
        for x in (-0.10, -0.08, -0.04, 0.0, 0.04, 0.08, 0.10):
            h = 0.068 if abs(x) < 0.09 else 0.05
            bow = 0.012 * (1.0 - (x / 0.1) ** 2)
            rings.append((Vector((x, 0.80, z_edge + sign * (0.006 + bow * 0.5))), Y * h, Z * 0.016))
        b.tube(rings, 6)
    parts.append(from_builder("diver_lead", b, None, m["lead"], rigid("chest")))

    # The boots: canvas uppers over the dress's legs, lead soles, brass toe caps and ankle straps.
    lx, lback, lfront = leg_span
    leg_r = (lx - at["foot_l"].x) + 0.008
    leg_rz = (lfront - lback) * 0.5 + 0.01
    up, sole, toe = kit.Builder(), kit.Builder(), kit.Builder()
    for side in (1.0, -1.0):
        ankle = Vector((side * at["foot_l"].x, at["foot_l"].y, (lfront + lback) * 0.5))
        foot = [(-0.06, 0.0, 0.046, 0.042), (-0.03, 0.01, 0.054, 0.054), (0.02, 0.0, 0.058, 0.048),
                (0.07, -0.012, 0.06, 0.036), (0.115, -0.015, 0.058, 0.028), (0.150, -0.017, 0.047, 0.022)]
        rings = [(ankle + Vector((0.0, y, z)), X * rx, Y * ry) for z, y, rx, ry in foot]
        up.tube(kit.dome(rings[0], -Z, 0.016, 3)[::-1] + rings + kit.dome(rings[-1], Z, 0.02, 3), 14, 0.032)
        up.tube([kit.upright(ankle.x, y, ankle.z, r * leg_r, r * leg_rz) for y, r in ((0.05, 0.85), (0.12, 0.94), (BOOT_TOP - 0.02, 1.0), (BOOT_TOP + 0.015, 1.06), (BOOT_TOP + 0.02, 0.94))], 14)
        sole.tube([(Vector((ankle.x, 0.017, ankle.z + z)), X * w, Y * 0.017) for z, w in ((-0.075, 0.045), (-0.06, 0.056), (0.0, 0.062), (0.08, 0.064), (0.15, 0.060), (0.185, 0.045))], 10, 0.0)
        toe.ellipsoid(ankle + Vector((0.0, -0.008, 0.15)), Vector((0.052, 0.034, 0.05)), None, 12, 4)
        toe.tube([kit.upright(ankle.x, y, ankle.z - 0.002, r, r * 1.05) for y, r in ((0.13, 0.066), (0.132, 0.072), (0.158, 0.074), (0.16, 0.068))], 12)

    def boot_weights(p):
        s = "_l" if p.x > 0 else "_r"
        shin = kit.blend(0.06, 0.11, p.y)
        return {"shin" + s: shin, "foot" + s: 1.0 - shin}

    parts.append(from_builder("diver_boots", up, (0.005, 2, 380), m["boots"], boot_weights))
    parts.append(from_builder("diver_soles", sole, None, m["lead"], boot_weights))
    parts.append(from_builder("diver_toes", toe, None, m["brass"], boot_weights))

    # The air hose: from the goose-neck, down his back, to the deck and away to the pump.
    pts = [goose[-1], Vector((0.045, NECK_RING + 0.15, cz - 0.20)), Vector((0.05, 1.08, cz - 0.235)), Vector((0.06, 0.92, cz - 0.255)),
           Vector((0.07, 0.68, cz - 0.27)), Vector((0.08, 0.40, cz - 0.30)), Vector((0.09, 0.17, cz - 0.35)),
           Vector((0.10, 0.06, cz - 0.42)), Vector((0.11, 0.026, cz - 0.52)), Vector((0.13, 0.024, cz - 0.64))]
    smooth = []
    for i in range(len(pts) - 1):
        p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, len(pts) - 1)]
        for k in range(2):
            t = k / 2.0
            smooth.append(0.5 * (2.0 * p1 + (p2 - p0) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t * t + (3.0 * p1 - p0 - 3.0 * p2 + p3) * t * t * t))
    smooth.append(pts[-1])
    b = kit.Builder()
    b.strand(smooth, [0.016] * len(smooth), 5)
    parts.append(from_builder("diver_hose", b, None, m["rubber"], lambda p: {"chest": 1.0 - kit.blend(0.9, 0.55, p.y), "hips": kit.blend(0.9, 0.55, p.y)}))

    bpy.data.objects.remove(body, do_unlink=True)
    return finish("diver", joints, parts, collection)


def LIGHTS(cz):
    """(centre, which way it looks out, glass radius, guard bars) of the bonnet's four lights."""
    mid = NECK_RING + 0.024 + 0.105
    return [
        (Vector((0.0, mid, cz + 0.121)), Vector((0.0, 0.0, 1.0)), 0.048, 0),
        (Vector((0.117, mid, cz)), Vector((1.0, 0.0, 0.0)), 0.034, 2),
        (Vector((-0.117, mid, cz)), Vector((-1.0, 0.0, 0.0)), 0.034, 2),
        (Vector((0.0, mid + 0.082, cz + 0.088)), Vector((0.0, 0.6, 0.8)), 0.025, 1),
    ]


# =====================================================================================================

def export(collection, path):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in collection.objects:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_yup=True,
                              export_animations=False, export_skins=True, export_vertex_color="NONE")
    tris = sum(kit.triangle_count(o.data) for o in collection.objects if o.type == "MESH")
    print("EXPORTED %s tris=%d" % (os.path.basename(path), tris))


bpy.ops.wm.read_factory_settings(use_empty=True)
made = {}
for name in ("boy", "captain", "diver"):
    made[name] = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(made[name])
build_boy(made["boy"])
build_captain(made["captain"])
build_diver(made["diver"])
for mat in list(bpy.data.materials):
    if mat.users == 0:
        bpy.data.materials.remove(mat)
for c in list(bpy.data.collections):
    if c.name.startswith("glTF_not_exported"):
        bpy.data.collections.remove(c)
os.makedirs(os.path.join(HERE, "blend"), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "blend", "title_figures.blend"))
for name, collection in made.items():
    export(collection, os.path.join(ROOT, "models", "title_%s.glb" % name))
