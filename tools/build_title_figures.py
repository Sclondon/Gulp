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
    key = (o.name, len(o.data.vertices))
    if key not in _TREES:
        tree = kdtree.KDTree(len(o.data.vertices))
        for v in o.data.vertices:
            tree.insert(G(v.co), v.index)
        tree.balance()
        _TREES[key] = tree
    _, index, _ = _TREES[key].find(p)
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


def paint_tint(body, shade):
    """Gives each corner of `body` the soft tint shade(material, point) (see `finish`), after taking away any
    vertex colours it had."""
    mesh = body.data
    for called in [a.name for a in mesh.color_attributes]:
        mesh.color_attributes.remove(mesh.color_attributes[called])
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
    paint_tint(body, shade)
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


def hands_of(body, name, skin, size=1.0, tris=560):
    """His hands, made `size` times bigger about the wrists (the captain's big working hands, the diver's gloves)."""
    hands = copy_of(body, name)
    keep_only(hands, lambda p: abs(p.x) > HAND_FROM)
    wrist = Vector((0.484, 0.934, 0.0))
    for v in hands.data.vertices:
        p = G(v.co)
        w = Vector((math.copysign(wrist.x, p.x), wrist.y, wrist.z))
        grow = 1.0 + (size - 1.0) * ease(HAND_FROM, wrist.x + 0.01, abs(p.x))
        v.co = B(w + (p - w) * grow)
    decimate(hands, tris)
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
# The boy: an old-time sailor boy (tools/art_src/concept_sailor_boy.jpg), on GameCommon's boy
# =====================================================================================================
#
# The user (2026-11-18): "Nick of Time by Ned Bell is part of the inspiration, and the art on the cover- the boy needs
# and old timey sailor boy outfit". Built to the concept: a loose cream shirt, collar open, sleeves rolled above the
# elbow; a faded navy neckerchief knotted at the throat, its flap on his back; high-waisted khaki trousers with a
# worn leather belt, rolled at the ankle; scuffed brown boots; a rope bracelet; a clasp knife on a lanyard at the
# belt; wind-tossed sandy hair. The face stays the game's smooth mask.
#
# Everything is grown from the boy's own bare body (boy.glb `boy_body__bare`), as the captain's clothes are from
# the man's: the shirt and trousers are its surface stood off; the rolls, turn-ups, belt and bracelet are bands of those
# surfaces made solid; the collar, neckerchief and knife are laid on them by rays. Only the skin that shows is kept
# of the body (neck and open chest, forearms, ankles). His hands (boy_tp.glb `boy`), boots (`boy_boots`) and mask
# head (boy.glb `boy_head__base`, HeadShape "inside_round" as Warren has it) are the boy's own.

BOY_TP = os.path.join(COMMON, "models", "boy_tp.glb")
BOY_FULL = os.path.join(COMMON, "models", "boy.glb")
BOY_JOINT = Vector((0.0, 1.012, 0.0))  # the boy's head joint
# sRGB; sombre, muted, weathered (the concept's)
BOY_COLOURS = {
    "skin": (0.78, 0.62, 0.51), "shirt": (0.80, 0.76, 0.65), "kerchief": (0.21, 0.25, 0.35),
    "trousers": (0.55, 0.50, 0.36), "belt": (0.38, 0.23, 0.13), "iron": (0.42, 0.42, 0.42), "boots": (0.40, 0.26, 0.16),
    "hair": (0.74, 0.61, 0.40), "rope": (0.66, 0.56, 0.39), "wood": (0.40, 0.26, 0.15), "steel": (0.62, 0.62, 0.64),
}
BOY_METAL = {"iron": (0.4, 0.55), "steel": (0.6, 0.35), "boots": (0.0, 0.7), "belt": (0.0, 0.75)}
SLEEVE_END = 0.29     # |x| where the rolled sleeves end (T pose; the elbow is at 0.32)
OPEN_NECK = 0.855     # the bottom of the shirt's open neck, in front
TROUSER_TOP = 0.705   # high-waisted (his hips' joint is at 0.62); just above the belt, under the shirt
TROUSER_END = 0.19    # where the legs are cut, the turn-ups round them
BELT = (0.664, 0.698)
BRACELET = (0.447, 0.466)  # |x| of the rope round his right wrist
# The helmet scripts/title.gd puts on his head: tools/build_helmet.py's cap (outer radius 1.1, inner 1.02, cut 0.18
# above its middle) at HEAD 0.128, (0, 0.1, 0.005) from the head mount, in his model's space.
HELMET_MIDDLE = BOY_JOINT + Vector((0.0, 0.1, 0.005))
HELMET_INSIDE = 1.02 * 0.128
HELMET_RIM = HELMET_MIDDLE.y + 0.18 * 0.128


def under_helmet(p, margin=0.003):
    """Whether a point keeps clear of the helmet: under its rim, or inside its shell."""
    return p.y < HELMET_RIM - margin or (p - HELMET_MIDDLE).length < HELMET_INSIDE - margin


def lay(objs, points, centre_of, off):
    """Points laid on the outermost of several surfaces: a ray from far out, back toward centre_of(point) through
    the point; the hit furthest out wins. Gives [(point moved `off` out along the surface's normal, normal)]."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    trees = [BVHTree.FromObject(o, depsgraph) for o in objs]
    out = []
    for p in points:
        c = centre_of(p)
        d = (p - c).normalized()
        best = None
        for tree in trees:
            hit = tree.ray_cast(B(c + d * 0.6), B(-d))
            if hit[0] is None:
                continue
            q = G(hit[0])
            far = (q - c).dot(d)
            if best is None or far > best[0]:
                n = G(hit[1]).normalized()
                if n.dot(d) < 0.0:
                    n = -n
                best = (far, q, n)
        if best is None:
            print("LAY missed at (%.3f, %.3f, %.3f)" % tuple(p))
        out.append((p, d) if best is None else (best[1] + best[2] * off, best[2]))
    return out


def laid_strip(objs, path, widths, centre_of, off, across=5):
    """Rows of laid points for a strip of cloth along a path, `widths[i]` either side of it, across the surface."""
    middle = lay(objs, path, centre_of, off)
    rows = []
    for i, (p, n) in enumerate(middle):
        ahead = (middle[min(i + 1, len(middle) - 1)][0] - middle[max(i - 1, 0)][0]).normalized()
        side = ahead.cross(n).normalized()
        row = [p + side * widths[i] * (2.0 * k / (across - 1) - 1.0) for k in range(across)]
        rows.append(lay(objs, row, centre_of, off))
    return rows


def sheet(name, rows, thick, material, weigh):
    """A thin slab of cloth over rows of laid (point, normal): its underside on the points, its top `thick` out."""
    bm = bmesh.new()
    low = [[bm.verts.new(B(p)) for p, n in row] for row in rows]
    high = [[bm.verts.new(B(p + n * thick)) for p, n in row] for row in rows]
    count, cols = len(rows), len(rows[0])
    for r in range(count - 1):
        for c in range(cols - 1):
            bm.faces.new((high[r][c], high[r][c + 1], high[r + 1][c + 1], high[r + 1][c]))
            bm.faces.new((low[r][c], low[r + 1][c], low[r + 1][c + 1], low[r][c + 1]))
    rim = ([(0, c) for c in range(cols)] + [(r, cols - 1) for r in range(1, count)]
           + [(count - 1, c) for c in range(cols - 2, -1, -1)] + [(r, 0) for r in range(count - 2, 0, -1)])
    for i, (r0, c0) in enumerate(rim):
        r1, c1 = rim[(i + 1) % len(rim)]
        bm.faces.new((low[r0][c0], low[r1][c1], high[r1][c1], high[r0][c0]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
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


def band_of(o, name, keep, planes, out, thick, material):
    """A solid band of a surface (a roll, a turn-up, a belt): the faces `keep` takes, cut clean by the planes
    [(point, normal kept)], stood `out` off it, then made `thick` deep inward."""
    band = copy_of(o, name)
    keep_only(band, keep)
    for point, normal in planes:
        cut(band, point, normal)
    stand_off(band, lambda p: out)
    solid = band.modifiers.new("solid", "SOLIDIFY")
    solid.thickness = thick
    solid.offset = -1.0
    solid.use_even_offset = True
    from mathutils import kdtree
    was = kdtree.KDTree(len(band.data.vertices))
    for v in band.data.vertices:
        was.insert(v.co, v.index)
    was.balance()
    activate(band)
    bpy.ops.object.modifier_apply(modifier=solid.name)
    # (a sliver at a cut can be thrown far out by the even offset: such a point is put back on the surface)
    for v in band.data.vertices:
        at, _, far = was.find(v.co)
        if far > 0.05:
            print("BAND %s: a point thrown %.2f m out, put back" % (name, far))
            v.co = at
    recolour(band, {}, material)
    smooth_shade(band)
    return band


def blended_weights(o, p, count=4):
    """Skin weights at p blended from the `count` nearest points of `o`, nearer counting more."""
    from mathutils import kdtree
    key = (o.name, len(o.data.vertices))
    if key not in _TREES:
        tree = kdtree.KDTree(len(o.data.vertices))
        for v in o.data.vertices:
            tree.insert(G(v.co), v.index)
        tree.balance()
        _TREES[key] = tree
    names = {g.index: g.name for g in o.vertex_groups}
    total, out = 0.0, {}
    for _, index, distance in _TREES[key].find_n(p, count):
        share = 1.0 / max(distance, 0.002)
        total += share
        for g in o.data.vertices[index].groups:
            if g.group in names:
                out[names[g.group]] = out.get(names[g.group], 0.0) + g.weight * share
    return {bone: w / total for bone, w in out.items()}


def hair_uvs(o, crown, centre):
    """Gives a hair shell the coordinates the hair shader reads (GameCommon ink-figure's hair_ink, as the locks get
    them from the Builder): UV (along the hair, from the crown 0 down to the hairline about 1; round the head 0..1)
    and a second set, `Metres`, the same in metres. The hair runs from the crown down and out, as the locks do."""
    mesh = o.data
    while mesh.uv_layers:
        mesh.uv_layers.remove(mesh.uv_layers[0])
    plain, metres = mesh.uv_layers.new(name="UVMap"), mesh.uv_layers.new(name="Metres")
    up = (crown - centre).normalized()
    for poly in mesh.polygons:
        coords = []
        for li in poly.loop_indices:
            d = (G(mesh.vertices[mesh.loops[li].vertex_index].co) - centre).normalized()
            angle = math.acos(max(-1.0, min(1.0, d.dot(up))))
            coords.append([angle / 2.2, (math.atan2(d.x, d.z) / math.tau) % 1.0, angle])
        # (a face across the seam at the back: its corners kept on one side of it)
        if max(c[1] for c in coords) - min(c[1] for c in coords) > 0.5:
            for c in coords:
                if c[1] < 0.5:
                    c[1] += 1.0
        for li, (along, round_, angle) in zip(poly.loop_indices, coords):
            plain.data[li].uv = (along, round_)
            metres.data[li].uv = (angle * 0.125, round_ * 0.75)
    mesh.uv_layers.active = plain


def boy_hair(head, m, bare):
    """Wind-tossed sandy hair: a shell grown from his scalp and chunky locks on it, swept to his right and back.
    Gives (what always shows, the crown). The crown is what the title's helmet (a close skullcap) would crush: it is
    its own mesh, `boy_hairtop`, which TitleFigures hides while the helmet is on (see under_helmet)."""
    pts = [G(v.co) for v in head.data.vertices]
    low = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    high = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    mid = (low + high) * 0.5

    def scalp(p):
        front = (math.cos(math.atan2(p.x, p.z - mid.z)) + 1.0) * 0.5
        return p.y > 1.04 + 0.112 * front ** 2.4

    shell = copy_of(head, "boy_hairshell")
    keep_only(shell, scalp)
    stand_off(shell, lambda p: 0.009, smooth=3, lam=0.3)
    decimate(shell, 420)
    top = copy_of(shell, "boy_hairtop_shell")
    cut(shell, Vector((0.0, HELMET_RIM - 0.002, 0.0)), -Y)
    cut(top, Vector((0.0, HELMET_RIM - 0.002, 0.0)), Y)
    crown = Vector((0.006, high.y + 0.01, mid.z - 0.03))
    wind = Vector((-1.0, 0.25, -0.55)).normalized()
    import random
    rnd = random.Random(11)
    keep_b, top_b = kit.Builder(), kit.Builder()
    def lock(b, base, n, way, length, width, lift):
        """A clump of hair: flat, wide at the root, arching out from the scalp by `lift` of its length, to a
        blunt point."""
        side = way.cross(n).normalized()
        pts = [base, base + way * length * 0.5 + n * length * lift * 0.35, base + way * length + n * length * lift * 0.15]
        b.tube([(p, side * width * w, n * width * t) for p, (w, t) in zip(pts, ((1.0, 0.55), (0.8, 0.45), (0.22, 0.12)))], 5)

    # (around from the front toward his left, up from the head's middle, length, how far it arches out, width,
    # how much the wind takes it)
    locks = []
    for a in (-0.7, -0.38, -0.08, 0.22, 0.52):  # the fringe, falling from the hairline, swept to his right
        locks.append((a, 0.52, 0.095, 0.35, 0.028, 0.7))
    for a in (-0.62, -0.36, -0.1, 0.16, 0.42):  # short locks on the brow: what shows under the helmet's rim
        locks.append((a, 0.16, 0.04, 0.2, 0.03, 0.5))
    for side in (1.0, -1.0):  # temples and over the ears
        for a, e in ((0.95, 0.3), (1.35, 0.14), (1.78, 0.06)):
            locks.append((side * a, e, 0.075, 0.55, 0.027, 0.45))
    for a, e, length in ((2.1, 0.02, 0.055), (2.45, -0.06, 0.07), (2.8, 0.0, 0.05), (3.1, -0.09, 0.075), (-2.9, -0.02, 0.06),
                         (-2.55, -0.08, 0.068), (-2.2, 0.03, 0.05), (2.6, 0.12, 0.05), (-2.75, 0.13, 0.055)):  # the back and nape
        locks.append((a, e, length * 1.15, 0.6, 0.026, 0.35))
    for a in (0.0, 0.8, 1.6, 2.4, 3.14, -2.4, -1.6, -0.8):  # the crown's ring, tossed up and back
        locks.append((a, 0.85, 0.1, 0.75, 0.03, 0.8))
    for a, e in ((0.4, 1.25), (2.0, 1.2), (-1.2, 1.2), (3.0, 1.1)):  # tufts on top
        locks.append((a, e, 0.075, 1.1, 0.026, 0.9))
    centre = Vector((0.0, mid.y - 0.01, mid.z))
    shown, hidden = 0, 0
    for a, e, length, lift, width, blow in locks:
        a += rnd.uniform(-0.06, 0.06)
        length *= rnd.uniform(0.8, 1.25)
        aim = centre + Vector((math.sin(a) * math.cos(e), math.sin(e), math.cos(a) * math.cos(e)))
        (base, n), = lay([shell, top, head], [aim], lambda p: centre, -0.004)
        flow = base - crown
        flow -= n * flow.dot(n)
        if flow.length < 1e-4:
            flow = -wind
        way = flow.normalized() + wind * blow * 0.6
        way -= n * way.dot(n)
        way.normalize()
        one = kit.Builder()
        lock(one, base, n, way, length, width, lift)
        fits = all(under_helmet(G(v.co)) for v in one.bm.verts)
        one.bm.free()
        lock(keep_b if fits else top_b, base, n, way, length, width, lift)
        shown, hidden = (shown + 1, hidden) if fits else (shown, hidden + 1)
    print("BOY hair locks: %d always shown, %d in the crown" % (shown, hidden))
    hair = from_builder("boy_hairlocks", keep_b, None, m["hair"], rigid("head"))
    crown_locks = from_builder("boy_hairtop", top_b, None, m["hair"], rigid("head"))
    for o in (shell, top):
        recolour(o, {}, m["hair"])
        smooth_shade(o)
        for g in list(o.vertex_groups):
            o.vertex_groups.remove(g)
        o.vertex_groups.new(name="head").add([v.index for v in o.data.vertices], 1.0, "REPLACE")
        hair_uvs(o, crown, centre)
    bad = [p for p in (G(v.co) for o in (shell, hair) for v in o.data.vertices) if not under_helmet(p, 0.0)]
    print("BOY hair always shown, points into the helmet: %d" % len(bad))
    # Two meshes, each a shell and its locks: what always shows, and the crown. (Not joined into his body: the hair
    # shader reads UV as (along the lock, round it) and UV2 in metres, which his body's surfaces do not have.)
    made = []
    for base, locks_of, name in ((shell, hair, "boy_hair"), (top, crown_locks, "boy_hairtop")):
        activate(base)
        locks_of.select_set(True)
        bpy.ops.object.join()
        base.name = base.data.name = name
        made.append(base)
    return made


def build_boy(collection):
    m = {name: make_material("boy_" + name, c, *BOY_METAL.get(name, (0.0, 1.0))) for name, c in BOY_COLOURS.items()}
    tp = import_glb(BOY_TP)
    full = import_glb(BOY_FULL)
    source_armature = next(o for o in tp if o.type == "ARMATURE")
    joints = [(b.name, G(b.head_local), b.parent.name if b.parent else None) for b in source_armature.data.bones]

    def mesh_of(made, name):
        return next(o for o in made if o.type == "MESH" and o.name.split(".")[0] == name)

    hands, boots = mesh_of(tp, "boy"), mesh_of(tp, "boy_boots")
    bare, head = mesh_of(full, "boy_body__bare"), mesh_of(full, "boy_head__base")
    kept = (hands, boots, bare, head)
    for o in tp + full:
        if o not in kept:
            bpy.data.objects.remove(o, do_unlink=True)
    bpy.context.view_layer.update()
    for o in kept:
        settle(o)
        for called in [a.name for a in o.data.color_attributes]:
            o.data.color_attributes.remove(o.data.color_attributes[called])
    weld(bare)
    weld(head)
    # The head as Warren has it: HeadShape "inside_round", from the round head's own bounds.
    reshape_head(head, "inside_round")
    decimate(head, 1300)
    head.name = "boy_head"
    recolour(head, {}, m["skin"])
    smooth_shade(head)
    hands.name = "boy_hands"
    recolour(hands, {}, m["skin"])
    smooth_shade(hands)
    boots.name = "boy_boots"
    recolour(boots, {}, m["boots"])
    smooth_shade(boots)
    def weigh(p):
        """The body's weights where cloth lies on it: blended from the few nearest points of the body (one point's
        weights alone change in steps, and cloth laid over the shirt then parts from it as he moves)."""
        return blended_weights(bare, p)

    # The skin that shows: his neck and open chest, his forearms below the rolls, his ankles above the boots.
    skin = copy_of(bare, "boy_skin")
    keep_only(skin, lambda p: (p.y > 0.9 and math.hypot(p.x, p.z) < 0.058)
              or (p.z > 0.0 and p.y > OPEN_NECK - 0.015 and abs(p.x) < 0.03 + (p.y - OPEN_NECK) * 0.5)
              or (abs(p.x) > SLEEVE_END - 0.018 and p.y > 0.8) or (0.08 < p.y < TROUSER_END + 0.02 and abs(p.x) < 0.2))
    decimate(skin, 360)
    recolour(skin, {}, m["skin"])
    smooth_shade(skin)

    # The shirt: his body stood off, loose on the arms, tucked in at the waist, its neck open in front.
    shirt = copy_of(bare, "boy_shirt")

    def in_shirt(p):
        if p.y < 0.6 or abs(p.x) > SLEEVE_END + 0.02:
            return False
        if p.y > 0.93 and math.hypot(p.x, p.z) < 0.055:
            return False
        return not (p.z > 0.0 and p.y > OPEN_NECK and abs(p.x) < 0.006 + (p.y - OPEN_NECK) * 0.42)

    keep_only(shirt, in_shirt)
    stand_off(shirt, lambda p: 0.005 + 0.005 * ease(0.66, 0.76, p.y) + 0.007 * ease(0.15, 0.21, abs(p.x)), smooth=6)
    # (tucked in: its hem under the trousers, which come up to TROUSER_TOP)
    cut(shirt, Vector((0.0, 0.685, 0.0)), Y)
    # (the sleeves rolled up above the elbow: a roll round each end, the sleeve cut under it)
    rolls = [band_of(shirt, "boy_roll", lambda p, s=s: p.x * s > SLEEVE_END - 0.045,
                     [(Vector((s * (SLEEVE_END - 0.032), 0.0, 0.0)), X * s), (Vector((s * (SLEEVE_END + 0.004), 0.0, 0.0)), -X * s)],
                     0.008, 0.013, m["shirt"]) for s in (1.0, -1.0)]
    for roll in rolls:
        decimate(roll, 170)
    cut(shirt, Vector((SLEEVE_END, 0.0, 0.0)), -X)
    cut(shirt, Vector((-SLEEVE_END, 0.0, 0.0)), X)
    decimate(shirt, 950)
    recolour(shirt, {}, m["shirt"])
    smooth_shade(shirt)

    # The trousers: his hips and legs stood off, loose and wide in the leg, high at the waist.
    trousers = copy_of(bare, "boy_trousers")
    keep_only(trousers, lambda p: TROUSER_END - 0.04 < p.y < TROUSER_TOP + 0.025 and abs(p.x) < 0.2)

    def loose(p):
        t = 0.012 + 0.014 * ease(0.6, 0.42, p.y) + 0.008 * ease(0.62, 0.68, p.y)
        crotch = ease(0.42, 0.5, p.y) * ease(0.06, 0.025, abs(p.x))
        return t * (1.0 - 0.75 * crotch)

    stand_off(trousers, loose, smooth=12)
    turnups = band_of(trousers, "boy_turnups", lambda p: p.y < TROUSER_END + 0.03,
                      [(Vector((0.0, TROUSER_END - 0.028, 0.0)), Y), (Vector((0.0, TROUSER_END + 0.018, 0.0)), -Y)],
                      0.008, 0.014, m["trousers"])
    belt = band_of(trousers, "boy_belt", lambda p: BELT[0] - 0.012 < p.y < BELT[1] + 0.012,
                   [(Vector((0.0, BELT[0], 0.0)), Y), (Vector((0.0, BELT[1], 0.0)), -Y)], 0.007, 0.006, m["belt"])
    cut(trousers, Vector((0.0, TROUSER_TOP, 0.0)), -Y)
    cut(trousers, Vector((0.0, TROUSER_END, 0.0)), Y)
    decimate(trousers, 950)
    decimate(turnups, 220)
    decimate(belt, 160)
    recolour(trousers, {}, m["trousers"])
    smooth_shade(trousers)

    # The rope bracelet round his right wrist (his right is -X).
    bracelet = band_of(hands, "boy_bracelet", lambda p: -BRACELET[1] - 0.02 < p.x < -BRACELET[0] + 0.02,
                       [(Vector((-BRACELET[1], 0.0, 0.0)), X), (Vector((-BRACELET[0], 0.0, 0.0)), -X)], 0.006, 0.006,
                       m["rope"])
    decimate(bracelet, 120)
    wrist = sleeve_at(hands, -(BRACELET[0] + BRACELET[1]) * 0.5, 0.01)[0]

    parts = [head, hands, boots, skin, shirt] + rolls + [trousers, turnups, belt, bracelet]

    # The collar, open: laid on the shirt round the back of his neck, its points on his chest either side.
    neck_axis = lambda p: Vector((0.0, p.y, 0.0))  # noqa: E731  (level rays: sloping ones met the tops of his
    # shoulders first and laid the neckerchief out across them)
    under = [shirt, skin]
    for s in (1.0, -1.0):
        path, widths = [], []
        for k in range(12):
            a = math.pi - (math.pi - 0.45) * k / 11.0  # from the back of his neck round to the front
            y = 0.945 - 0.012 * ease(math.pi, 1.4, a) - 0.06 * ease(1.2, 0.45, a)
            r = 0.08  # (outside the neckerchief round his neck, which covers the shirt's neck edge)
            path.append(Vector((s * (math.sin(a) * r + 0.012 * ease(0.9, 0.45, a)), y, math.cos(a) * r)))
            widths.append(0.013 + 0.007 * ease(1.4, 0.7, a))
        widths[-1] = 0.004
        parts.append(sheet("boy_collar", laid_strip(under, path, widths, neck_axis, 0.0015), 0.004, m["shirt"], weigh))
    collars = parts[-2:]

    # The neckerchief: a flap on his back, the cloth round his neck to a knot at his throat, two tails.
    on = under + collars
    rows = []
    for r in range(7):
        t = r / 6.0
        half = 0.1 * (1.0 - t) + 0.004 * t
        row = []
        for c in range(7):
            x = half * (c / 3.0 - 1.0)
            y = (0.958 - 0.08 * (x / 0.1) ** 2) * (1.0 - t) + 0.805 * t
            row.append(Vector((x, y, -0.3)))
        rows.append(lay(on, row, lambda p: Vector((p.x * 0.8, p.y, 0.0)), 0.0025))  # (rays straight in from behind: slanting
        # ones met the backs of his arms)
    flap = sheet("boy_flap", rows, 0.004, m["kerchief"], weigh)
    knot_at = lay(under, [Vector((0.0, 0.872, 0.3))], neck_axis, 0.0)[0]
    pieces = [flap]
    for s in (1.0, -1.0):
        path, widths = [], []
        for k in range(12):
            a = math.pi * (1.0 - k / 11.0)
            # (close round the neck, then steeply down to the knot, a narrow V as the concept has it)
            y = 0.956 - 0.006 * ease(math.pi, 1.5, a) - 0.084 * ease(1.1, 0.0, a)
            r = 0.054
            path.append(Vector((s * (math.sin(a) * r * (1.0 - 0.55 * ease(1.1, 0.0, a)) + 0.008 * ease(0.5, 0.0, a)), y, math.cos(a) * r)))
            widths.append(0.012 - 0.003 * ease(0.8, 0.0, a))
        pieces.append(sheet("boy_kerchief", laid_strip(on + [flap], path, widths, neck_axis, 0.007, 7), 0.005,
                            m["kerchief"], weigh))
    # (the tails hang from the knot, one a little longer, splayed)
    for s, drop, splay in ((1.0, 0.085, 0.022), (-1.0, 0.1, 0.012)):
        path = [knot_at[0] + Vector((s * (0.006 + splay * f), -drop * f, 0.0)) for f in (0.0, 0.25, 0.5, 0.75, 1.0)]
        widths = [0.009, 0.012, 0.013, 0.011, 0.005]
        pieces.append(sheet("boy_tail", laid_strip(under + collars, path, widths, lambda p: Vector((p.x * 0.5, p.y, 0.0)), 0.002, 3),
                            0.004, m["kerchief"], weigh))
    b = kit.Builder()
    p, n = knot_at
    b.ellipsoid(p + n * 0.012 + Vector((0.0, -0.002, 0.0)), Vector((0.02, 0.013, 0.008)), None, 8, 4)
    pieces.append(from_builder("boy_knot", b, None, m["kerchief"], weigh))
    parts += pieces

    # The belt's buckle: an iron frame at the front, its tongue across it.
    (front, fn), = lay([belt], [Vector((0.0, (BELT[0] + BELT[1]) * 0.5, 0.3))], lambda p: Vector((0.0, p.y, 0.0)), 0.0)
    b = kit.Builder()
    y0 = (BELT[0] + BELT[1]) * 0.5
    hw, hh = 0.02, 0.021
    corners = [Vector((-hw, y0 - hh, 0.0)), Vector((hw, y0 - hh, 0.0)), Vector((hw, y0 + hh, 0.0)), Vector((-hw, y0 + hh, 0.0))]
    z = front.z + 0.004
    for i in range(4):
        a0, a1 = corners[i], corners[(i + 1) % 4]
        along = (a1 - a0).normalized()
        across = along.cross(Z)
        # (a flat bar: a tube of four sides set square, 7 mm wide and 4 mm deep)
        bar = [(Vector((c.x, c.y, z)) + along * e, across * 0.0035 + Z * 0.002, -across * 0.0035 + Z * 0.002)
               for c, e in ((a0, -0.0035), (a1, 0.0035))]
        b.tube(bar, 4)
    b.tube([(Vector((x, y0, z + 0.0015)), Y * 0.002 + Z * 0.0015, -Y * 0.002 + Z * 0.0015) for x in (-hw, hw * 0.6)], 4)
    parts.append(from_builder("boy_buckle", b, None, m["iron"], rigid("hips")))

    # The clasp knife on a lanyard from his belt, on his right hip, lying on his thigh.
    hip = lambda p: Vector((-0.074 if p.y < 0.62 else 0.0, p.y, 0.0))  # noqa: E731
    a = 0.75
    aim = lambda y: Vector((-math.sin(a) * 0.3, y, math.cos(a) * 0.3))  # noqa: E731
    (hook, hn), = lay([belt], [aim(BELT[0] + 0.006)], lambda p: Vector((0.0, p.y, 0.0)), 0.002)
    laid = lay([trousers], [aim(y) for y in (0.6, 0.575, 0.55, 0.525, 0.5, 0.48)], hip, 0.0)
    ring = laid[0][0] + laid[0][1] * 0.012
    b = kit.Builder()
    for s in (1.0, -1.0):
        mid = (hook + ring) * 0.5 + hn * 0.006 + Vector((s * 0.004, 0.0, 0.0))
        b.strand([hook + Vector((s * 0.004, 0.0, 0.0)), mid, ring], [0.0018] * 3, 4)
    lanyard = from_builder("boy_lanyard", b, None, m["rope"], lambda p: nearest_weights(trousers, p))
    b, blade = kit.Builder(), kit.Builder()
    handle = [(q + nq * 0.011, nq) for q, nq in laid[:4]]
    rings = []
    for i, (q, nq) in enumerate(handle):
        down = (handle[min(i + 1, 3)][0] - handle[max(i - 1, 0)][0]).normalized()
        side = down.cross(nq).normalized()
        w = (0.008, 0.0105, 0.0105, 0.009)[i]
        rings.append((q, side * w, nq * 0.0065))
    b.tube(rings, 8)
    b.ellipsoid(handle[0][0], Vector((0.006, 0.006, 0.006)), None, 6, 3)
    tip_q, tip_n = laid[5][0] + laid[5][1] * 0.009, laid[5][1]
    top_q = handle[-1][0]
    down = (tip_q - top_q).normalized()
    side = down.cross(tip_n).normalized()
    blade.tube([(top_q.lerp(tip_q, f), side * w, tip_n * 0.002) for f, w in ((0.0, 0.009), (0.5, 0.008), (0.85, 0.005), (1.0, 0.0015))], 4)
    parts.append(lanyard)
    parts.append(from_builder("boy_knife", b, None, m["wood"], lambda p: nearest_weights(trousers, p)))
    parts.append(from_builder("boy_blade", blade, None, m["steel"], lambda p: nearest_weights(trousers, p)))

    # The hair.
    hair_meshes = boy_hair(head, m, bare)

    from mathutils import noise

    def shade(material, p):
        stain = ease(0.1, 0.55, noise.noise(p * 6.0 + Vector((1.3, 7.1, 2.9))))
        if material == "shirt":
            return 0.95 - 0.1 * stain + 0.04 * noise.noise(p * 25.0)
        if material in ("trousers", "kerchief"):
            return 0.93 - 0.14 * stain + 0.05 * noise.noise(p * 21.0) - 0.08 * ease(0.3, 0.17, p.y)
        if material in ("boots", "belt"):
            return 0.82 + 0.18 * ease(-0.2, 0.5, noise.noise(p * 30.0))
        if material == "rope":
            turn = math.atan2(p.z - wrist.z, p.y - wrist.y) if abs(p.x - wrist.x) < 0.05 else p.y * 300.0
            return 0.72 + 0.28 * (0.5 + 0.5 * math.cos(turn * 7.0 + p.x * 700.0))
        if material == "hair":
            return 0.86 + 0.14 * noise.noise(p * 40.0 + Vector((0.0, 3.0, 0.0)))
        return 1.0

    print("BOY parts", ", ".join("%s %d" % (o.name, kit.triangle_count(o.data)) for o in parts + hair_meshes))
    bpy.data.objects.remove(bare, do_unlink=True)
    armature = finish("boy", joints, parts, collection, shade)
    for hair in hair_meshes:
        paint_tint(hair, None)  # (no tint: the hair shader colours it)
        hair.parent = armature
        hair.modifiers.new("Armature", "ARMATURE").object = armature
        for c in hair.users_collection:
            c.objects.unlink(hair)
        collection.objects.link(hair)
        print("FIGURE %s tris=%d" % (hair.name, kit.triangle_count(hair.data)))
    return armature


# =====================================================================================================
# The captain (design sheet: tools/TITLE_FIGURES.md)
# =====================================================================================================

CAPTAIN_KEYS = {"heavy": 0.5, "body_gut": 0.35, "body_shoulders": 0.3, "body_neck": 0.4}
CAPTAIN_HEAD = "mask_long"
# The boy's head made a man's: this much of the boy's size, its joint on the man's, a little forward.
HEAD_SCALE = 0.64
HEAD_FORWARD = 0.018
# The closed outfit (the first concept): ribs round the gansey's bands, so many to a turn (each a pair of rings of
# points, dark then light), its hem, and where its sleeves end (|x|, T pose)
RIBS = {"hem": 56, "cuff": 24, "collar": 40}
GANSEY_HEM = 0.535
CUFF = 0.462
CAPTAIN_COLOURS = {
    # (after the concept art, tools/art_src/concept_characters.jpg: muted, a little greyed)
    "skin": (0.76, 0.58, 0.48), "nose": (0.78, 0.46, 0.40), "coat": (0.14, 0.16, 0.23),
    "gansey": (0.14, 0.16, 0.23), "rib": (0.14, 0.16, 0.23),
    "vest": (0.80, 0.78, 0.72), "stripe": (0.24, 0.29, 0.40), "chesthair": (0.70, 0.69, 0.66),
    "oilskin": (0.70, 0.57, 0.27), "rubber": (0.09, 0.09, 0.09), "beard": (0.80, 0.79, 0.76), "hair": (0.60, 0.59, 0.56),
    "cap": (0.15, 0.17, 0.23), "peak": (0.06, 0.06, 0.07), "brass": (0.66, 0.55, 0.32), "pipe": (0.34, 0.22, 0.14),
    "braces": (0.21, 0.19, 0.17), "steel": (0.45, 0.45, 0.46), "gold": (0.83, 0.66, 0.3),
    "slit": (0.2, 0.12, 0.1), "crease": (0.6, 0.42, 0.34),
}


# The captain as the second concept draws him (tools/art_src/concept_captain.jpg): the user (2026-11-18), "captian
# should have bushy chest hair and tattoos", and "the captain should have a tasteful bulge".
COAT_SLEEVE = 0.36    # |x| where his coat's pushed-up sleeves end (T pose; the elbow is at 0.341)
COAT_HEM = 0.535
ARM_Y = 0.934         # the height of his arms' joints, held out in the T pose
SCOOP = 0.865         # the bottom of his undershirt's low neck, in front
VEST_HEM = 0.575
STRIPE = 0.028        # each stripe of the undershirt, cream then navy
TROUSERS_TOP = 0.542  # (where the closed outfit has always cut them, under the gansey's hem)
TATTOOS = os.path.join(HERE, "art_src", "captain_tattoos.png")
# (the tattoo picture: the forearms in its lower three quarters, the left (his left, +X) in its left half, round
# the arm across and elbow to wrist up; his chest in the top quarter)
TATTOO_ARM = (COAT_SLEEVE - 0.06, HAND_FROM + 0.012)
TATTOO_CHEST = (-0.14, 0.14, SCOOP - 0.05, 1.0)
ARM_ROUND = 0.042     # about the radius of his forearm (m), to lay the pictures out true


def coat_open(y):
    """How far either side of his middle the front of his coat is open, at a height."""
    return 0.08 + (y - COAT_HEM) * 0.12


def cut_front(o, point, normal):
    """Cuts the front of one side of an object (z > 0, and x on the point's side) by a plane, keeping the side the
    normal points to; the back and the other side are left whole."""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    faces = [f for f in bm.faces if G(f.calc_center_median()).z > 0.0 and G(f.calc_center_median()).x * point.x > 0.0]
    edges = list({e for f in faces for e in f.edges})
    verts = list({v for f in faces for v in f.verts})
    bmesh.ops.bisect_plane(bm, geom=verts + edges + faces, plane_co=B(point), plane_no=B(normal), clear_inner=True)
    bm.to_mesh(o.data)
    bm.free()


def hair_lock(b, base, n, way, length, width, lift):
    """A clump of hair (the boy's locks, and the captain's chest hair): flat, wide at the root, arching out from the
    skin by `lift` of its length, to a blunt point. Its UV runs along it, as the hair shader wants."""
    side = way.cross(n).normalized()
    pts = [base, base + way * length * 0.5 + n * length * lift * 0.35, base + way * length + n * length * lift * 0.15]
    b.tube([(p, side * width * w, n * width * t) for p, (w, t) in zip(pts, ((1.0, 0.55), (0.8, 0.45), (0.22, 0.12)))], 5)


def tattoo_uvs(o):
    """Lays the tattoo picture (paint_tattoos) round his forearms and over his chest: UV of each corner."""
    mesh = o.data
    while mesh.uv_layers:
        mesh.uv_layers.remove(mesh.uv_layers[0])
    uv = mesh.uv_layers.new(name="UVMap")
    lo, hi = TATTOO_ARM
    x0, x1, y0, y1 = TATTOO_CHEST
    for poly in mesh.polygons:
        coords = []
        for li in poly.loop_indices:
            p = G(mesh.vertices[mesh.loops[li].vertex_index].co)
            if abs(p.x) > 0.2:
                a = math.atan2(p.z, p.y - ARM_Y)  # 0 on top of the arm, a quarter turn to the front
                coords.append([(a / math.tau + 0.5), min(max((abs(p.x) - lo) / (hi - lo), 0.0), 0.999), p.x > 0.0])
            else:
                coords.append([None, (p.x - x0) / (x1 - x0), min(max((p.y - y0) / (y1 - y0), 0.0), 0.999)])
        if coords[0][0] is not None and max(c[0] for c in coords) - min(c[0] for c in coords) > 0.5:
            for c in coords:
                if c[0] < 0.5:
                    c[0] += 1.0
        for li, c in zip(poly.loop_indices, coords):
            if c[0] is None:
                uv.data[li].uv = (min(max(c[1], 0.0), 0.999), 0.75 + 0.25 * c[2])
            else:
                u = min(max(c[0], 0.0), 1.0)
                uv.data[li].uv = ((0.0 if c[2] else 0.5) + 0.5 * u, 0.75 * c[1])


def paint_tattoos(skin, size=1024):
    """Paints his tattoos: old sailor's flash (anchor, swallow, compass star, a ship on a ribbon, a heart; no letters),
    faded blue-black ink on his skin's colour. Shapes are drawn true in metres on the arm (see tattoo_uvs).
    Gives a Blender image, also saved as tools/art_src/captain_tattoos.png."""
    import numpy as np
    j, i = np.mgrid[0:size, 0:size]
    u, v = (i + 0.5) / size, (j + 0.5) / size
    ink = np.zeros((size, size))
    lo, hi = TATTOO_ARM
    x0, x1, y0, y1 = TATTOO_CHEST
    # (each pixel's place: round and along an arm, or on the chest)
    left = (u < 0.5) & (v < 0.75)
    right = (u >= 0.5) & (v < 0.75)
    ul = np.where(u < 0.5, u * 2.0, (u - 0.5) * 2.0)
    s = (ul - 0.5) * math.tau * ARM_ROUND
    t = lo + v / 0.75 * (hi - lo)
    cx, cy = x0 + u * (x1 - x0), y0 + (v - 0.75) / 0.25 * (y1 - y0)

    def poly(X, Y, pts):
        inside = np.zeros(X.shape, bool)
        for (ax, ay), (bx, by) in zip(pts, pts[1:] + pts[:1]):
            cross = ((ay > Y) != (by > Y)) & (X < (bx - ax) * (Y - ay) / (by - ay + 1e-9) + ax)
            inside ^= cross
        return inside

    def disc(X, Y, x, y, r):
        return (X - x) ** 2 + (Y - y) ** 2 < r * r

    def ring(X, Y, x, y, r, w):
        d = np.sqrt((X - x) ** 2 + (Y - y) ** 2)
        return np.abs(d - r) < w

    def anchor(X, Y):
        m = (np.abs(X) < 0.07) & (np.abs(Y + 0.05) < 0.6)
        m |= ring(X, Y, 0.0, 0.72, 0.13, 0.05)
        m |= (np.abs(X) < 0.36) & (np.abs(Y - 0.42) < 0.06)
        m |= ring(X, Y, 0.0, -0.15, 0.5, 0.07) & (Y < -0.15)
        for sx in (1.0, -1.0):
            m |= poly(X, Y, [(sx * 0.5, 0.0), (sx * 0.72, -0.28), (sx * 0.34, -0.22)])
        return m, m & False

    def swallow(X, Y):
        m = ((X / 0.36) ** 2 + ((Y + 0.02) / 0.17) ** 2 < 1.0) | disc(X, Y, 0.36, 0.06, 0.13)
        m |= poly(X, Y, [(0.05, 0.08), (-0.55, 0.75), (-0.2, 0.05)])
        m |= poly(X, Y, [(0.1, -0.05), (-0.45, -0.6), (-0.15, -0.08)])
        m |= poly(X, Y, [(-0.3, 0.0), (-0.85, 0.22), (-0.62, 0.0), (-0.85, -0.2)])
        dark = m & (Y > 0.0) & (X > -0.3)
        return m, dark

    def star(X, Y):
        pts = []
        for k in range(10):
            a = math.pi / 2 + k * math.pi / 5
            r = 0.75 if k % 2 == 0 else 0.3
            pts.append((r * math.cos(a), r * math.sin(a)))
        m = poly(X, Y, pts)
        sector = (np.arctan2(Y, X) - math.pi / 2) % (2 * math.pi / 5)
        return m, m & (sector < math.pi / 5)

    def heart(X, Y):
        m = disc(X, Y, -0.25, 0.15, 0.3) | disc(X, Y, 0.25, 0.15, 0.3) | poly(X, Y, [(-0.53, 0.06), (0.53, 0.06), (0.0, -0.62)])
        hollow = disc(X, Y, -0.22, 0.17, 0.17) | disc(X, Y, 0.22, 0.17, 0.17) | poly(X, Y, [(-0.36, 0.1), (0.36, 0.1), (0.0, -0.4)])
        return m, m & ~hollow

    def ship(X, Y):
        m = poly(X, Y, [(-0.62, 0.0), (0.62, 0.0), (0.45, -0.24), (-0.45, -0.24)])
        m |= (np.abs(X + 0.15) < 0.03) & (Y > 0.0) & (Y < 0.85)
        m |= (np.abs(X - 0.22) < 0.03) & (Y > 0.0) & (Y < 0.7)
        sails = poly(X, Y, [(-0.13, 0.8), (-0.13, 0.08), (-0.52, 0.1)]) | poly(X, Y, [(0.24, 0.66), (0.24, 0.08), (0.56, 0.1)])
        wave = Y + 0.05 * np.sin(X * 7.0)
        ribbon = (np.abs(X) < 0.8) & (wave < -0.32) & (wave > -0.52) & ~poly(X, Y, [(0.8, -0.3), (0.66, -0.42), (0.8, -0.54)]) \
            & ~poly(X, Y, [(-0.8, -0.3), (-0.66, -0.42), (-0.8, -0.54)])
        return m | sails | ribbon, m

    def place(shape, mask, X0, Y0, x, y, size_m, turn=0.0):
        X, Y = (X0 - x) / size_m, (Y0 - y) / size_m
        if turn:
            X, Y = X * math.cos(turn) - Y * math.sin(turn), X * math.sin(turn) + Y * math.cos(turn)
        m, dark = shape(X, Y)
        return np.where(mask & m, np.where(dark, 1.0, 0.55), 0.0)

    # (on the arms "up" is toward the elbow, as a tattoo reads with the arm hanging: Y = -(t - y))
    arm_up = lambda shape, mask, x, y, size_m, turn=0.0: place(shape, mask, s, -t, x, -y, size_m, turn)  # noqa: E731
    # his right forearm: an anchor, and a compass star by the wrist
    ink = np.maximum(ink, arm_up(anchor, right, 0.02, 0.37, 0.034))
    ink = np.maximum(ink, arm_up(star, right, 0.035, 0.425, 0.018))
    # his left: a swallow by the elbow, a ship on a ribbon, a heart by the wrist
    ink = np.maximum(ink, arm_up(swallow, left, 0.035, 0.345, 0.022, 0.4))
    ink = np.maximum(ink, arm_up(ship, left, 0.018, 0.39, 0.03))
    ink = np.maximum(ink, arm_up(heart, left, 0.045, 0.437, 0.014))
    # his chest, beside the hair on his left: a small anchor
    ink = np.maximum(ink, place(anchor, v >= 0.75, cx, cy, 0.082, 0.915, 0.024, -0.25))
    # (faded and soft: blurred a little, grain through it)
    soft = ink.copy()
    for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        soft += np.roll(np.roll(ink, di, 1), dj, 0)
    ink = soft / 5.0 * 0.78 * (0.9 + 0.1 * np.random.default_rng(3).random((size, size)))
    colour = np.array([kit.linear(c) for c in (0.17, 0.22, 0.29)])
    base = np.array([kit.linear(c) for c in skin])
    rgb = base[None, None, :] * (1.0 - ink[..., None]) + colour[None, None, :] * ink[..., None]
    pixels = np.concatenate([rgb, np.ones((size, size, 1))], axis=2).astype(np.float32)
    image = bpy.data.images.new("captain_tattoos", size, size)
    image.colorspace_settings.name = "sRGB"
    image.pixels.foreach_set(np.ravel(np.power(np.clip(pixels, 0, 1), [1 / 2.2, 1 / 2.2, 1 / 2.2, 1.0])).astype(np.float32))
    image.filepath_raw = TATTOOS
    image.file_format = "PNG"
    image.save()
    image.pack()
    return image


def inked_material(image):
    material = bpy.data.materials.new("captain_inked")
    material.use_nodes = True
    shader = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    texture = material.node_tree.nodes.new("ShaderNodeTexImage")
    texture.image = image
    material.node_tree.links.new(texture.outputs["Color"], shader.inputs["Base Color"])
    shader.inputs["Roughness"].default_value = 1.0
    return material


def build_captain(collection):
    m = {name: make_material("captain_" + name, c, 0.35 if name in ("brass", "steel", "gold") else 0.0, 0.5 if name in ("brass", "steel", "peak", "rubber", "oilskin", "gold") else 1.0)
         for name, c in CAPTAIN_COLOURS.items()}
    m["inked"] = inked_material(paint_tattoos(CAPTAIN_COLOURS["skin"]))
    joints, body, legs = import_man(CAPTAIN_KEYS)
    head_joint = next(at for name, at, _ in joints if name == "head")
    parts = []

    # His hands, and his forearms bare below the pushed-up sleeves, heavy, with old sailor's tattoos (a picture
    # painted by paint_tattoos, laid round each forearm).
    parts.append(hands_of(body, "captain_hands", m["skin"], 1.15))
    # His two outfits (the user: "the captain should have the outfit from teh first concept as well to switch into"):
    # the open coat (concept_captain.jpg, the default) and the closed gansey (concept_characters.jpg); each its own mesh,
    # captain_outfit__open and captain_outfit__closed, shown or hidden by TitleFigures.wear.
    opened, closed = [], []
    forearms = copy_of(body, "captain_forearms")
    keep_only(forearms, lambda p: COAT_SLEEVE - 0.035 < abs(p.x) < HAND_FROM + 0.012 and p.y > 0.85)
    for v in forearms.data.vertices:
        p = G(v.co)
        # (heavier in the middle of the forearm, back to his own size at the elbow and the wrist)
        swell = 1.0 + 0.12 * ease(COAT_SLEEVE - 0.02, 0.38, abs(p.x)) * ease(HAND_FROM, 0.41, abs(p.x))
        v.co = B(Vector((p.x, ARM_Y + (p.y - ARM_Y) * swell, p.z * swell)))
    decimate(forearms, 520)
    recolour(forearms, {}, m["inked"])
    smooth_shade(forearms)
    tattoo_uvs(forearms)
    opened.append(forearms)

    # The striped undershirt, cut low: his body stood off, from the hips to the neck, no sleeves (the coat's cover
    # his arms), the stripes cut in as faces of two colours.
    vest = copy_of(body, "captain_vest")

    def in_vest(p):
        if not 0.54 < p.y < 1.04 or abs(p.x) > 0.21:
            return False
        if p.y > 0.96 and math.hypot(p.x, p.z) < 0.075:
            return False
        return not (p.z > 0.0 and abs(p.x) < 0.095 and p.y > SCOOP + 7.0 * p.x * p.x)

    keep_only(vest, in_vest)
    stand_off(vest, lambda p: 0.007, smooth=6)
    cut(vest, Vector((0.0, VEST_HEM, 0.0)), Y)
    for s in (1.0, -1.0):
        cut(vest, Vector((s * 0.19, 0.0, 0.0)), -X * s)
    decimate(vest, 480)
    bm = bmesh.new()
    bm.from_mesh(vest.data)
    y = VEST_HEM + STRIPE
    while y < 1.0:
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=B(Vector((0.0, y, 0.0))), plane_no=B(Y))
        y += STRIPE
    bm.to_mesh(vest.data)
    bm.free()
    vest.data.materials.clear()
    vest.data.materials.append(m["vest"])
    vest.data.materials.append(m["stripe"])
    for poly in vest.data.polygons:
        poly.material_index = int((G(poly.center).y - VEST_HEM) / STRIPE) % 2
    smooth_shade(vest)
    opened.append(vest)

    # The skin of his neck and chest where the undershirt is cut low (a tattoo on it, beside the hair).
    chest = copy_of(body, "captain_chest")
    keep_only(chest, lambda p: p.y < 1.04 and ((p.y > 0.95 and math.hypot(p.x, p.z) < 0.085)
              or (p.z > 0.0 and abs(p.x) < 0.11 and p.y > SCOOP - 0.02 + 5.6 * p.x * p.x)))
    decimate(chest, 380)
    recolour(chest, {}, m["inked"])
    smooth_shade(chest)
    tattoo_uvs(chest)
    opened.append(chest)

    # The coat, hanging open: his body stood well off, open down the front and wider toward the neck (where it
    # turns back), sleeves pushed up to below the elbow and bunched there; given an inside (solid), so the open
    # front shows its lining, not nothing.
    coat = copy_of(body, "captain_coat")

    def in_coat(p):
        if p.y < COAT_HEM - 0.02 or abs(p.x) > COAT_SLEEVE + 0.03:
            return False
        if p.y > 0.95 and math.hypot(p.x, p.z) < 0.078:
            return False
        return not (p.z > 0.0 and abs(p.x) < coat_open(p.y) - 0.025)

    keep_only(coat, in_coat)
    stand_off(coat, lambda p: 0.03 + 0.016 * ease(0.66, 0.58, p.y), smooth=10)
    # (the open front cut clean, each side by a slanting plane through its front only)
    for s in (1.0, -1.0):
        cut_front(coat, Vector((s * coat_open(COAT_HEM), COAT_HEM, 0.0)), Vector((s, -0.12, 0.0)))
    rolls = [band_of(coat, "captain_roll", lambda p, s=s: p.x * s > COAT_SLEEVE - 0.05,
                     [(Vector((s * (COAT_SLEEVE - 0.036), 0.0, 0.0)), X * s), (Vector((s * (COAT_SLEEVE + 0.004), 0.0, 0.0)), -X * s)],
                     0.01, 0.02, m["coat"]) for s in (1.0, -1.0)]
    cut(coat, Vector((0.0, COAT_HEM, 0.0)), Y)
    for s in (1.0, -1.0):
        cut(coat, Vector((s * COAT_SLEEVE, 0.0, 0.0)), -X * s)
    decimate(coat, 700)
    # (slivers left by the cuts and the decimation would be thrown far out by the solidify: dissolved first)
    bm = bmesh.new()
    bm.from_mesh(coat.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0008)
    bmesh.ops.dissolve_degenerate(bm, dist=0.0008, edges=bm.edges)
    # (and a stray point the cut at the sleeve ends left far off, with its faces)
    stray = [v for v in bm.verts if (G(v.co) - Vector((0.0, 0.75, 0.0))).length > 0.8]
    print("CAPTAIN coat: %d stray points taken away" % len(stray))
    bmesh.ops.delete(bm, geom=stray, context="VERTS")
    bm.to_mesh(coat.data)
    bm.free()
    solid = coat.modifiers.new("solid", "SOLIDIFY")
    solid.thickness = 0.006
    solid.offset = -1.0
    from mathutils import kdtree
    was = kdtree.KDTree(len(coat.data.vertices))
    for v in coat.data.vertices:
        was.insert(v.co, v.index)
    was.balance()
    activate(coat)
    bpy.ops.object.modifier_apply(modifier=solid.name)
    # (and any point the solidify still threw out is put back where the surface was)
    thrown = 0
    for v in coat.data.vertices:
        at, _, far = was.find(v.co)
        if far > 0.02:
            v.co = at
            thrown += 1
    print("CAPTAIN coat: %d points thrown out by the solidify, put back" % thrown)
    recolour(coat, {}, m["coat"])
    smooth_shade(coat)
    for roll in rolls:
        decimate(roll, 200)
    opened += [coat] + rolls
    weigh = lambda p: blended_weights(body, p)  # noqa: E731
    # (its collar, turned down round the back of his neck)
    neck_axis = lambda p: Vector((0.0, p.y, 0.0))  # noqa: E731
    for s in (1.0, -1.0):
        path = [Vector((s * math.sin(a) * 0.1, 0.975 - 0.03 * ease(1.6, 0.9, a), math.cos(a) * 0.1)) for a in
                (math.pi - (math.pi - 0.9) * k / 7.0 for k in range(8))]
        opened.append(sheet("captain_collar", laid_strip([coat], path, [0.024] * 7 + [0.012], neck_axis, 0.001, 5), 0.008,
                           m["coat"], weigh))

    # The braces: in front on the undershirt, from clips at the trousers up under the coat; behind, over the coat
    # from his shoulders to a Y and down (as the concept draws them).
    b, clips = kit.Builder(), kit.Builder()
    front = lambda p: Vector((0.0, p.y, 0.0))  # noqa: E731
    for s in (1.0, -1.0):
        path = [Vector((s * x, y, 0.3)) for x, y in ((0.085, VEST_HEM + 0.012), (0.088, 0.66), (0.092, 0.76), (0.1, 0.86), (0.11, 0.93))]
        laid = lay([vest], smooth_path(path, 2), front, 0.005)
        strap(b, [p for p, n in laid], [n for p, n in laid], 0.011, 0.0025, 4)
        clips.ellipsoid(laid[0][0] + laid[0][1] * 0.003 + Vector((0.0, 0.006, 0.0)), Vector((0.012, 0.014, 0.004)), None, 8, 3)
        path = [Vector((s * x, y, -0.3)) for x, y in ((0.11, 0.96), (0.09, 0.88), (0.05, 0.81), (0.012, 0.77))]
        laid = lay([coat], smooth_path(path, 2), lambda p: Vector((p.x * 0.5, p.y, 0.0)), 0.005)
        strap(b, [p for p, n in laid], [n for p, n in laid], 0.011, 0.0025, 4)
    path = [Vector((0.0, y, -0.3)) for y in (0.775, 0.71, 0.65, 0.6, COAT_HEM + 0.02)]
    laid = lay([coat], smooth_path(path, 2), lambda p: Vector((0.0, p.y, 0.0)), 0.005)
    strap(b, [p for p, n in laid], [n for p, n in laid], 0.012, 0.0025, 4)
    opened.append(from_builder("captain_braces", b, None, m["braces"], weigh))
    opened.append(from_builder("captain_clips", clips, None, m["steel"], weigh))

    # A thick bush of grey chest hair in the low neck of his undershirt: a shell on his chest and tufts on it,
    # curling up and out, drawn by the hair shader as the boy's hair is (its own mesh: the shader reads UV along the
    # hair and UV2 in metres).
    bush = copy_of(body, "captain_chesthair")
    keep_only(bush, lambda p: p.z > 0.02 and SCOOP - 0.005 < p.y < 0.97 and abs(p.x) < 0.024 + 0.45 * (p.y - SCOOP))
    stand_off(bush, lambda p: 0.007, smooth=3, lam=0.3)
    decimate(bush, 160)
    tufts = kit.Builder()
    import random
    rnd = random.Random(5)
    centre = Vector((0.0, 0.86, -0.05))
    for k in range(26):
        y = SCOOP + 0.008 + 0.088 * rnd.random()
        x = (0.02 + 0.42 * (y - SCOOP)) * rnd.uniform(-0.95, 0.95)
        (base, n), = lay([bush], [Vector((x, y, 0.3))], lambda p: Vector((p.x * 0.5, p.y, 0.0)), -0.003)
        way = Vector((rnd.uniform(-0.6, 0.6) + x * 6.0, 1.0, 0.0))
        way -= n * way.dot(n)
        way.normalize()
        hair_lock(tufts, base, n, way, rnd.uniform(0.018, 0.03), rnd.uniform(0.009, 0.013), rnd.uniform(0.6, 1.0))
    locks = from_builder("captain_chestlocks", tufts, None, m["chesthair"], rigid("chest"))
    recolour(bush, {}, m["chesthair"])
    smooth_shade(bush)
    mesh = bush.data
    while mesh.uv_layers:
        mesh.uv_layers.remove(mesh.uv_layers[0])
    plain, metres = mesh.uv_layers.new(name="UVMap"), mesh.uv_layers.new(name="Metres")
    for li, loop in enumerate(mesh.loops):
        p = G(mesh.vertices[loop.vertex_index].co)
        plain.data[li].uv = ((p.y - SCOOP) / 0.1, p.x / 0.16 + 0.5)
        metres.data[li].uv = (p.y - SCOOP, p.x)
    activate(bush)
    locks.select_set(True)
    bpy.ops.object.join()
    bush.name = bush.data.name = "captain_chesthair"
    for g in list(bush.vertex_groups):
        bush.vertex_groups.remove(g)
    groups = {}
    for v in mesh.vertices:
        for bone, share in blended_weights(body, G(v.co)).items():
            if share > 0.001:
                if bone not in groups:
                    groups[bone] = bush.vertex_groups.new(name=bone)
                groups[bone].add([v.index], share, "REPLACE")

    # The closed outfit, as the first concept has him: a navy gansey with ribbed bands, braces over it.
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
    closed.append(gansey)
    # Ribbed bands at the hem and the cuffs, round the gansey as it is there, a little proud.
    b = kit.Builder()
    hx, hback, hfront = extents(gansey, GANSEY_HEM + 0.012, 0.012)
    hcz, hrz = (hback + hfront) * 0.5, (hfront - hback) * 0.5
    b.tube([kit.upright(0.0, y, hcz, hx + d, hrz + d) for y, d in ((GANSEY_HEM - 0.003, 0.004), (GANSEY_HEM, 0.011), (GANSEY_HEM + 0.036, 0.009), (GANSEY_HEM + 0.04, 0.0))], RIBS["hem"])
    for side in (1.0, -1.0):
        c, r = sleeve_at(gansey, side * (CUFF - 0.02))
        b.tube([(Vector((side * x, c.y, c.z)), Y * (r + d), Z * (r + d)) for x, d in ((CUFF - 0.036, -0.004), (CUFF - 0.032, 0.005), (CUFF - 0.002, 0.005), (CUFF + 0.002, 0.0))], RIBS["cuff"])
    closed.append(from_builder("captain_bands", b, None, m["rib"], lambda p, g=gansey: nearest_weights(g, p)))
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
        laid, normals = surface_path(gansey, smooth_path(path, 1), centre_of, 0.004)
        strap(b, laid, normals, 0.011, 0.0025, 4)
        clip_at, clip_n = laid[0], normals[0]
        clips.ellipsoid(clip_at + clip_n * 0.003 + Vector((0.0, 0.006, 0.0)), Vector((0.012, 0.014, 0.004)), None, 8, 3)
    path = [Vector((0.0, y, -0.2)) for y in (0.745, 0.70, 0.64, 0.59, GANSEY_HEM + 0.012)]
    laid, normals = surface_path(gansey, smooth_path(path, 2), centre_of, 0.004)
    strap(b, laid, normals, 0.012, 0.0025, 4)
    clips.ellipsoid(laid[-1] + normals[-1] * 0.003 + Vector((0.0, 0.006, 0.0)), Vector((0.013, 0.014, 0.004)), None, 8, 3)
    closed.append(from_builder("captain_braces", b, None, m["braces"], lambda p, g=gansey: nearest_weights(g, p)))
    closed.append(from_builder("captain_clips", clips, None, m["steel"], lambda p, g=gansey: nearest_weights(g, p)))


    # The man's own trousers piece, in oilskin and rubber, its top (under the undershirt) cut away and drawn in a
    # little; with a modest fullness at the fly (the user: "the captain should have a tasteful bulge").
    cut(legs, Vector((0.0, TROUSERS_TOP, 0.0)), -Y)
    for v in legs.data.vertices:
        p = G(v.co)
        k = 1.0 - 0.16 * ease(TROUSERS_TOP - 0.05, TROUSERS_TOP, p.y)
        q = Vector((p.x * k, p.y, 0.015 + (p.z - 0.015) * k))
        if q.z > 0.0:
            q.z += 0.006 * math.exp(-((q.x / 0.03) ** 2 + ((q.y - 0.515) / 0.03) ** 2))
        v.co = B(q)
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

    # His eyes (the user: "his eyes should just be wrinkly slits", "maybe added on as afacial feature"): on the mask,
    # as the nose is, two narrow creased squints between puffy lids, under heavy white brows, with crow's feet at the
    # outer corners. No eyeballs.
    slits, lids, brows, creases = kit.Builder(), kit.Builder(), kit.Builder(), kit.Builder()
    eye_y = nose_y + 0.023
    for s in (1.0, -1.0):
        x = s * 0.031
        z = front_at(eye_y, x)
        tilt = Matrix.Rotation(s * 0.12, 3, "Z")
        slits.ellipsoid(Vector((x, eye_y, z - 0.0012)), Vector((0.0135, 0.0019, 0.003)), tilt, 8, 2)
        lids.ellipsoid(Vector((x, eye_y + 0.0042, z - 0.0002)), Vector((0.0155, 0.0045, 0.0048)), tilt, 8, 2)
        lids.ellipsoid(Vector((x, eye_y - 0.004, z - 0.001)), Vector((0.014, 0.0034, 0.0042)), tilt, 8, 2)
        by = eye_y + 0.0135
        bz = front_at(by, x)
        brows.ellipsoid(Vector((x + s * 0.002, by, bz + 0.002)), Vector((0.021, 0.0062, 0.0075)), Matrix.Rotation(s * -0.18, 3, "Z"), 8, 3)
        brows.ellipsoid(Vector((x + s * 0.012, by - 0.003, bz - 0.002)), Vector((0.01, 0.0045, 0.006)), Matrix.Rotation(s * -0.5, 3, "Z"), 8, 2)
        corner = Vector((x + s * 0.016, eye_y, 0.0))
        for turn in (-0.45, 0.0, 0.4):
            way = Vector((s * math.cos(turn), math.sin(turn), 0.0))
            pts = [corner + way * d for d in (0.002, 0.006, 0.01)]
            pts = [Vector((p.x, p.y, front_at(p.y, p.x) + 0.0002)) for p in pts]
            creases.strand(pts, [0.0007, 0.0008, 0.0004], 4)
    parts.append(from_builder("captain_slits", slits, None, m["slit"], rigid("head")))
    parts.append(from_builder("captain_lids", lids, None, m["skin"], rigid("head")))
    parts.append(from_builder("captain_brows", brows, None, m["beard"], rigid("head")))
    parts.append(from_builder("captain_creases", creases, None, m["crease"], rigid("head")))

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
    decimate(head_now, 1000)
    parts.append(head_now)

    # A gold ring in his left ear (the concept's): a small hoop through the lobe.
    (lobe, ln), = lay([head_now], [Vector((0.2, nose_y - 0.018, centre_z - 0.008))], lambda p: Vector((0.0, p.y, centre_z - 0.008)), 0.0)
    b = kit.Builder()
    across = (Z * 0.8 + X * 0.6).normalized()
    hoop = [lobe + ln * 0.01 + (Y * -(1.0 - math.cos(a)) + across * math.sin(a)) * 0.0065 for a in (math.tau * k / 12 for k in range(13))]
    b.strand(hoop, [0.0014] * len(hoop), 4)
    opened.append(from_builder("captain_earring", b, None, m["gold"], rigid("head")))

    # (the closed outfit's roll collar of the gansey, round his neck)
    span = extents(body, 1.0, 0.008, lambda p: abs(p.x) < 0.08 and p.z < 0.075)
    nx, nb, nf = span
    ncz, nrz = (nb + nf) * 0.5, (nf - nb) * 0.5
    b = kit.Builder()
    b.tube([kit.upright(0.0, y, ncz, nx + g, nrz + g) for y, g in ((0.955, 0.03), (0.972, 0.037), (0.998, 0.034), (1.022, 0.022), (1.034, 0.006))], RIBS["collar"])
    closed.append(from_builder("captain_rollcollar", b, None, m["rib"],
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
        if material in ("oilskin", "cap", "coat"):
            # worn: soft lighter and darker patches
            return 0.92 + 0.1 * noise.noise(p * 9.0)
        if material in ("vest", "stripe"):
            return 0.95 + 0.05 * noise.noise(p * 14.0)
        return 1.0

    bpy.data.objects.remove(body, do_unlink=True)
    for label, group in (("parts", parts), ("open", opened + [bush]), ("closed", closed)):
        print("CAPTAIN %s:" % label, ", ".join("%s %d" % (o.name, kit.triangle_count(o.data)) for o in group))
    armature = finish("captain", joints, parts, collection, shade)
    # The outfits, a mesh each on the same skeleton (as Gloaming's man has his: man_<slot>__<option>), and the chest
    # hair, its own mesh for the hair shader (it goes with the open outfit).
    for name, group, tint in (("captain_outfit__open", opened, shade), ("captain_outfit__closed", closed, shade),
                              ("captain_chesthair__open", [bush], None)):
        activate(group[0])
        for o in group[1:]:
            o.select_set(True)
        if len(group) > 1:
            bpy.ops.object.join()
        one = group[0]
        one.name = one.data.name = name
        paint_tint(one, tint)
        one.parent = armature
        one.modifiers.new("Armature", "ARMATURE").object = armature
        for c in one.users_collection:
            c.objects.unlink(one)
        collection.objects.link(one)
        print("FIGURE %s tris=%d" % (name, kit.triangle_count(one.data)))
    return armature


# =====================================================================================================
# The diver (design sheet: tools/TITLE_FIGURES.md)
# =====================================================================================================

DIVER_COLOURS = {
    # (after the concept art, tools/art_src/concept_characters.jpg: muted, a little greyed)
    "skin": (0.76, 0.58, 0.48), "suit": (0.55, 0.49, 0.39), "rubber": (0.10, 0.10, 0.10), "copper": (0.64, 0.41, 0.30),
    "brass": (0.70, 0.58, 0.34), "glass": (0.10, 0.13, 0.13), "lead": (0.38, 0.39, 0.40), "leather": (0.36, 0.23, 0.14),
    "boots": (0.30, 0.30, 0.30), "steel": (0.48, 0.48, 0.49), "glove": (0.11, 0.11, 0.11),
}
METAL = {"copper": (0.5, 0.55), "brass": (0.6, 0.38), "glass": (0.0, 0.15), "rubber": (0.0, 0.55), "lead": (0.0, 0.7),
         "steel": (0.5, 0.4), "glove": (0.0, 0.5)}
BOOT_TOP = 0.20
NECK_RING = 1.02


def build_diver(collection):
    m = {name: make_material("diver_" + name, c, *METAL.get(name, (0.0, 1.0))) for name, c in DIVER_COLOURS.items()}
    joints, body, legs = import_man({})
    bpy.data.objects.remove(legs, do_unlink=True)
    at = {name: p for name, p, _ in joints}
    # Black rubber gauntlet gloves (the concept's): his own hands, a size bigger.
    parts = [hands_of(body, "diver_gloves", m["glove"], 1.18, 420)]

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
    for piece, tris, mat in ((dress, 850, "suit"), (belt, 180, "leather")):
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
        b.ellipsoid(stud, Vector((0.007, 0.007, 0.007)), None, 4, 2)
    b.tube([kit.upright(0.0, y, cz, r, r * 0.95) for y, r in ((NECK_RING - 0.006, 0.086), (NECK_RING - 0.002, 0.096), (NECK_RING + 0.02, 0.096), (NECK_RING + 0.024, 0.088))], 20)
    for centre, normal, radius, grille in LIGHTS(cz):
        u = normal.cross(Y if abs(normal.y) < 0.9 else X).normalized()
        v = normal.cross(u)
        rim = 12 if radius > 0.04 else 8
        ring = [centre + normal * 0.006 + (u * math.cos(a) + v * math.sin(a)) * (radius + 0.006) for a in (math.tau * k / rim for k in range(rim + 1))]
        b.strand(ring, [0.0072] * len(ring), 4)
        # the guards over the glass (the concept's): a cross over the front light, bars over the sides, a grid on top
        lines = []
        if grille == "cross":
            lines = [(u + v).normalized(), (u - v).normalized()]
            spans = [(d, 0.0) for d in lines]
        else:
            count = 3 if grille == "bars" else 2
            spans = [(u, (k - (count - 1) / 2) * radius * 0.6) for k in range(count)]
            if grille == "grid":
                spans += [(v, (k - (count - 1) / 2) * radius * 0.6) for k in range(count)]
        for along, off in spans:
            side = normal.cross(along).normalized()
            reach = math.sqrt(max(radius * radius - off * off, 0.0))
            b.strand([centre + normal * 0.014 + side * off + along * reach * s for s in (-1.0, 0.0, 1.0)], [0.0038] * 3, 3)
    valve = Vector((-0.082, NECK_RING + 0.075, cz + 0.08))
    axis = Vector((-0.75, 0.0, 0.66)).normalized()
    b.tube([(valve + axis * d, Y * r, axis.cross(Y) * r) for d, r in ((0.0, 0.016), (0.028, 0.016), (0.03, 0.02), (0.04, 0.02), (0.042, 0.011))], 10)
    goose = [Vector((0.035, NECK_RING + 0.15, cz - 0.10)), Vector((0.038, NECK_RING + 0.172, cz - 0.13)), Vector((0.04, NECK_RING + 0.168, cz - 0.16))]
    b.strand(goose, [0.015, 0.015, 0.016], 8)
    bx, bback, bfront = belt_span
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
    for centre, normal, radius, _grille in LIGHTS(cz):
        u = normal.cross(Y if abs(normal.y) < 0.9 else X).normalized()
        v = normal.cross(u)
        b.tube([(centre + normal * h, u * r, v * r) for h, r in ((-0.01, radius * 0.98), (0.0, radius), (0.006, radius * 0.9), (0.008, radius * 0.5))], 10)
    parts.append(from_builder("diver_glass", b, None, m["glass"], rigid("chest")))

    # The concept's gear on his chest and belt: two lead weights on leather straps (up under the corselet's edge
    # and down to the belt), a strap crossed on his back, a small brass plate on the corselet, a steel buckle,
    # a pouch on his left hip.
    corselet = bpy.data.objects["diver_corselet"]
    def round_x(p):
        return Vector((p.x * 0.6, p.y, ccz))
    lead, straps, steel, plate = kit.Builder(), kit.Builder(), kit.Builder(), kit.Builder()
    for s in (1.0, -1.0):
        spot, n = surface_path(dress, [Vector((s * 0.075, 0.72, 0.3))], round_x, 0.0)
        spot, n = spot[0], n[0]
        rings = []
        for dy, w in ((-0.05, 0.026), (-0.046, 0.032), (0.046, 0.032), (0.05, 0.026)):
            rings.append((spot + n * 0.019 + Y * dy, n.cross(Y).normalized() * w, n * 0.017))
        lead.tube(rings, 6)
        up_path = [Vector((s * 0.075, y, 0.3)) for y in (0.84, 0.80, 0.77, 0.74)]
        down_path = [Vector((s * 0.075, y, 0.3)) for y in (0.70, 0.67, 0.64, 0.615)]
        for path in (up_path, down_path):
            laid, normals = surface_path(dress, path, round_x, 0.004)
            strap(straps, laid, normals, 0.012, 0.003, 4)
        back = [Vector((s * x, y, -0.3)) for x, y in ((0.13, 0.835), (0.09, 0.77), (0.03, 0.70), (-0.04, 0.645), (-0.07, 0.615))]
        laid, normals = surface_path(dress, smooth_path(back, 2), round_x, 0.004)
        strap(straps, laid, normals, 0.012, 0.003, 4)
    spot, n = surface_path(corselet, [Vector((0.0, 0.952, 0.4))], lambda p: Vector((0.0, 0.93, ccz)), 0.001)
    side = n[0].cross(Y).normalized() * -1.0
    up = n[0].cross(side).normalized() * -1.0
    plate.tube([(spot[0] + n[0] * h, side * w, up * w * 0.42) for h, w in ((-0.002, 0.032), (0.002, 0.034), (0.004, 0.03))], 12)
    bx, bback, bfront = belt_span
    steel.tube([(Vector((0.0, 0.614, bfront + 0.012 + h)), X * w, Y * w * 0.75) for h, w in ((-0.004, 0.022), (0.0, 0.026), (0.004, 0.024))], 4)
    parts.append(from_builder("diver_lead", lead, None, m["lead"], rigid("chest")))
    parts.append(from_builder("diver_straps", straps, None, m["leather"], lambda p, g=dress: nearest_weights(g, p)))
    parts.append(from_builder("diver_plate", plate, None, m["brass"], rigid("chest")))
    parts.append(from_builder("diver_buckle", steel, None, m["steel"], rigid("hips")))
    b = kit.Builder()
    pouch_at = Vector((bx * 0.78, 0.585, bfront * 0.7))
    b.tube([(pouch_at + Y * y, X * 0.03, Z * 0.016) for y in (-0.035, -0.03, 0.025, 0.03)], 6)
    parts.append(from_builder("diver_pouch", b, None, m["leather"], rigid("hips")))

    # The boots: canvas uppers over the dress's legs, lead soles, brass toe caps and ankle straps.
    lx, lback, lfront = leg_span
    leg_r = (lx - at["foot_l"].x) + 0.008
    leg_rz = (lfront - lback) * 0.5 + 0.01
    up, sole, toe, bands = kit.Builder(), kit.Builder(), kit.Builder(), kit.Builder()
    for side in (1.0, -1.0):
        ankle = Vector((side * at["foot_l"].x, at["foot_l"].y, (lfront + lback) * 0.5))
        foot = [(-0.06, 0.0, 0.046, 0.042), (-0.03, 0.01, 0.054, 0.054), (0.02, 0.0, 0.058, 0.048),
                (0.07, -0.012, 0.06, 0.036), (0.115, -0.015, 0.058, 0.028), (0.150, -0.017, 0.047, 0.022)]
        rings = [(ankle + Vector((0.0, y, z)), X * rx, Y * ry) for z, y, rx, ry in foot]
        up.tube(kit.dome(rings[0], -Z, 0.016, 3)[::-1] + rings + kit.dome(rings[-1], Z, 0.02, 3), 14, 0.032)
        up.tube([kit.upright(ankle.x, y, ankle.z, r * leg_r, r * leg_rz) for y, r in ((0.05, 0.85), (0.12, 0.94), (BOOT_TOP - 0.02, 1.0), (BOOT_TOP + 0.015, 1.06), (BOOT_TOP + 0.02, 0.94))], 14)
        sole.tube([(Vector((ankle.x, 0.017, ankle.z + z)), X * w, Y * 0.017) for z, w in ((-0.075, 0.045), (-0.06, 0.056), (0.0, 0.062), (0.08, 0.064), (0.15, 0.060), (0.185, 0.045))], 10, 0.0)
        toe.ellipsoid(ankle + Vector((0.0, -0.008, 0.15)), Vector((0.052, 0.034, 0.05)), None, 10, 3)
        bands.tube([kit.upright(ankle.x, y, ankle.z - 0.002, r * leg_r / 0.066, r * leg_rz / 0.066) for y, r in ((0.13, 0.064), (0.132, 0.07), (0.152, 0.071), (0.154, 0.065))], 12)

    def boot_weights(p):
        s = "_l" if p.x > 0 else "_r"
        shin = kit.blend(0.06, 0.11, p.y)
        return {"shin" + s: shin, "foot" + s: 1.0 - shin}

    parts.append(from_builder("diver_boots", up, (0.005, 2, 380), m["boots"], boot_weights))
    parts.append(from_builder("diver_soles", sole, None, m["lead"], boot_weights))
    parts.append(from_builder("diver_toes", toe, None, m["brass"], boot_weights))
    parts.append(from_builder("diver_bootstraps", bands, None, m["rubber"], boot_weights))

    # The air hose: from the goose-neck, down his back on his right, to the deck and away to the pump; and (the
    # concept's) a coil of spare hose hung on his back over his left shoulder.
    pts = [goose[-1], Vector((0.02, NECK_RING + 0.15, cz - 0.20)), Vector((-0.03, 1.08, cz - 0.235)), Vector((-0.06, 0.92, cz - 0.255)),
           Vector((-0.07, 0.68, cz - 0.27)), Vector((-0.08, 0.40, cz - 0.30)), Vector((-0.09, 0.17, cz - 0.35)),
           Vector((-0.10, 0.06, cz - 0.42)), Vector((-0.11, 0.026, cz - 0.52)), Vector((-0.13, 0.024, cz - 0.64))]
    b = kit.Builder()
    b.strand(smooth_path(pts, 2), [0.016] * len(smooth_path(pts, 2)), 4)
    back_z = min(extents(corselet, y, 0.012, lambda p: p.x > 0.0)[1] for y in (0.84, 0.88, 0.92)) - 0.004
    for k in range(3):
        c = Vector((0.115 + 0.014 * k, 0.765 - 0.01 * k, back_z - 0.017 - 0.012 * k))
        loop = [c + Vector((0.07 * math.sin(a) + 0.012 * math.cos(a), 0.17 * math.cos(a), 0.0)) for a in (math.tau * i / 11 for i in range(12))]
        b.strand(loop, [0.0145] * len(loop), 4)
    parts.append(from_builder("diver_hose", b, None, m["rubber"], lambda p: {"chest": 1.0 - kit.blend(0.66, 0.5, p.y), "hips": kit.blend(0.66, 0.5, p.y)}))

    from mathutils import noise

    def shade(material, p):
        if material == "suit":
            # the concept's worn canvas: soft darker stains, and dirtier toward the boots
            stain = ease(0.05, 0.5, noise.noise(p * 7.0 + Vector((3.1, 0.0, 1.7))))
            return 1.0 - 0.3 * stain - 0.14 * ease(0.5, 0.2, p.y) + 0.05 * noise.noise(p * 23.0)
        if material in ("copper", "brass"):
            # old metal: darker patches of tarnish
            return 0.84 + 0.16 * noise.noise(p * 16.0) - 0.22 * ease(0.0, 0.5, noise.noise(p * 5.0))
        if material in ("boots", "lead"):
            return 0.9 + 0.1 * noise.noise(p * 12.0)
        return 1.0

    bpy.data.objects.remove(body, do_unlink=True)
    return finish("diver", joints, parts, collection, shade)


def LIGHTS(cz):
    """(centre, which way it looks out, glass radius, its guard) of the bonnet's four lights."""
    mid = NECK_RING + 0.024 + 0.105
    return [
        (Vector((0.0, mid, cz + 0.121)), Vector((0.0, 0.0, 1.0)), 0.048, "cross"),
        (Vector((0.117, mid, cz)), Vector((1.0, 0.0, 0.0)), 0.034, "bars"),
        (Vector((-0.117, mid, cz)), Vector((-1.0, 0.0, 0.0)), 0.034, "bars"),
        # (on the dome, tipped forward: the concept's top light with its grid)
        (Vector((0.0, mid + 0.106, cz + 0.066)), Vector((0.0, 0.8, 0.6)).normalized(), 0.03, "grid"),
    ]


# =====================================================================================================

def export(collection, path):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in collection.objects:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_yup=True,
                              export_animations=False, export_skins=True, export_vertex_color="ACTIVE")
    tris = sum(kit.triangle_count(o.data) for o in collection.objects if o.type == "MESH")
    print("EXPORTED %s tris=%d" % (os.path.basename(path), tris))


# (`-- --try <boy|captain|diver> <folder>` builds that one figure alone and writes only its glb and a .blend of it
# there, for trying it out; tools/blend/title_figures.blend and the game's models are left alone)
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ONLY, TRY = (ARGS[ARGS.index("--try") + 1], ARGS[ARGS.index("--try") + 2]) if "--try" in ARGS else (None, None)
BUILDS = {"boy": build_boy, "captain": build_captain, "diver": build_diver}
bpy.ops.wm.read_factory_settings(use_empty=True)
made = {}
for name in (ONLY,) if ONLY else ("boy", "captain", "diver"):
    made[name] = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(made[name])
    BUILDS[name](made[name])
for mat in list(bpy.data.materials):
    if mat.users == 0:
        bpy.data.materials.remove(mat)
for c in list(bpy.data.collections):
    if c.name.startswith("glTF_not_exported"):
        bpy.data.collections.remove(c)
if TRY:
    os.makedirs(TRY, exist_ok=True)
    export(made[ONLY], os.path.join(TRY, "title_%s.glb" % ONLY))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(TRY, "title_%s.blend" % ONLY))
else:
    os.makedirs(os.path.join(HERE, "blend"), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "blend", "title_figures.blend"))
    for name, collection in made.items():
        export(collection, os.path.join(ROOT, "models", "title_%s.glb" % name))
