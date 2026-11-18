"""Builds the old-time submarine (creatures/submarine) as a low-poly model with one painted picture.

    blender --background --factory-startup --python creatures/submarine/tools/build_submarine.py [-- --no-bake] [-- --out=<folder for pictures>]

Writes creatures/submarine/models/submarine.glb, creatures/submarine/textures/submarine_atlas.png (the paint),
creatures/submarine/textures/submarine_glow.png (where it glows: the portholes, the lamps' lenses, the two
valve tubes) and the editable tools/submarine.blend (this folder has a .gdignore).

The user (2026-11-18), for Gulp: "there should also be a submarine". Built to the concept picture made for it
(Gulp's tools/art_src/concept_submarine.jpg): a stubby riveted hull of tarnished brass and dark rusted iron
plates, a big round glass dome at the bow in a brass frame, round portholes glowing warm, a small conning
tower with a hatch, a periscope and a short antenna, two jointed grabbing arms under the bow, searchlights, a
caged propeller and fin rudders at the stern, ballast tanks strapped to the sides with copper pipes.

How it is made, after Gulp's control panel (tools/build_panel.py) and reef wreck (tools/build_wreck.py), so
that it sits with them: low-poly parts, each with a procedural Blender material (rust and verdigris patches,
plate seams and rows of rivets as a bump), all unwrapped into one picture and baked by Cycles (colour times
how open each spot is to the sea's light). The game draws that picture lit (Godot's own StandardMaterial3D:
no shader of its own); the glass is a second surface of the same picture, glossy, glowing where the glow
picture says. The light beams are plain cones with vertex colours (bright at the lamp, none at the far end),
drawn additive.

Axes: built in Blender with the bow to +Y, up +Z, starboard +X, and written out for Godot (glTF, Y up): the
bow to -Z, up +Y, starboard +X. The origin is on the hull's middle line half way along its length (from the
cage's back to the dome's front). Metres.

Objects (the node names Godot sees):
  Hull                 everything that does not move, two materials: SubPaint, SubGlass
  Propeller            turns about its shaft (Godot Z), origin on the shaft
  Rudder               the two flaps behind the upper and lower fins, turns about Godot Y, origin on the hinge
  Planes               the two flaps behind the side fins, turns about Godot X, origin on the hinge
  Periscope            turns about Godot Y (and slides up), origin at its foot on its axis
  ArmLeft, ArmRight    the upper arms, turn about Godot X at the shoulder (+ swings the arm forward)
    ForearmLeft/Right  turn about Godot X at the elbow
      ClawLeftUpper/Lower, ClawRightUpper/Lower   turn about Godot X at the wrist (+ lifts)
  BeamTop, BeamLeft, BeamRight   the searchlights' cones (vertex colours), origin at the lamp's lens

It prints a WINDING line (each closed part's faces point out of it: a ray from every face's middle along its
normal leaves the part an even number of times), a CLIP line (the arms through their reach and grip against
the hull, the lamps and each other; the tanks', the straps' and the pipes' gaps to the hull) and a TRIS line.
"""
import bpy
import bmesh
import math
import os
import sys
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
GLB = os.path.join(ROOT, "models", "submarine.glb")
BLEND = os.path.join(HERE, "submarine.blend")
ATLAS = os.path.join(ROOT, "textures", "submarine_atlas.png")
GLOW = os.path.join(ROOT, "textures", "submarine_glow.png")
ATLAS_SIZE = 2048
GLOW_SIZE = 512
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
BAKE = "--no-bake" not in ARGS
SHOTS = next((a.split("=", 1)[1] for a in ARGS if a.startswith("--out=")), "")
SAMPLES = 64

# --- The submarine's numbers (metres; Blender axes: bow +Y, up +Z, starboard +X)
# The hull's outline: (y, radius) from the bow's band back to the end of the tail cone.
HULL = [(3.6, 1.30), (3.3, 1.33), (3.0, 1.35), (2.7, 1.36), (2.4, 1.37), (2.4, 1.40), (1.8, 1.44), (1.0, 1.46),
        (0.2, 1.46), (-0.6, 1.43), (-1.2, 1.37), (-1.6, 1.30), (-2.0, 1.17), (-2.4, 1.02), (-2.8, 0.86),
        (-3.2, 0.69), (-3.5, 0.55), (-3.72, 0.44)]
BRASS_FROM = 2.4    # the bow's brass band: from here forward
SIDES = 20          # round the hull
DOME_R = 1.18       # the glass dome's radius where it meets the band (y = 3.6), and how far it bulges forward
DOME_DEEP = 0.86
TOWER = (0.0, 0.85, 0.56, 0.74)   # the conning tower: x, y of its middle, its half width and half length
TOWER_TOP = 2.28
SHOULDER_Y = 3.0
SHOULDER_ANGLE = math.radians(-40.0)   # round from the starboard side, below the middle line
ARM_X = 1.28        # the arms swing in planes this far out to each side
UPPER = 0.85        # the upper arm, the forearm and the claw's fingers
FORE = 0.95
FINGER = 0.42
ARM_DOWN = math.radians(25.0)      # as built: the upper arm hangs this far forward of straight down
FORE_DOWN = math.radians(20.0)     # and the forearm this far below level
FINGER_OPEN = 0.42                 # each finger this far (radians) off the forearm's line, as built
# How the game moves them (the node script holds the same numbers): reach 1 turns the shoulder and the elbow by
# these; grip 1 turns each finger by this towards the other.
REACH_SHOULDER = 0.75
REACH_ELBOW = -1.15
GRIP_TURN = 0.22
PERISCOPE_LIFT = 0.45   # how far the game slides the periscope up (the node script holds it too)
TANK = (1.72, 0.25, -0.62, 0.43, 2.3)  # the ballast tanks: x (each side), y, z of the middle, radius, length
PROP_Y = -4.12
CAGE = (-3.84, -4.5, 0.86)          # the propeller's cage: front, back, radius
LAMPS = {"Top": ((0.0, 2.95, 1.6), (0.0, 1.0, -0.08)),
         "Left": ((-0.42, 3.25, -1.56), (-0.08, 1.0, -0.28)),
         "Right": ((0.42, 3.25, -1.56), (0.08, 1.0, -0.28))}
BEAM_LONG = 5.5
BEAM_WIDE = 1.2

bpy.ops.wm.read_factory_settings(use_empty=True)


# --- Materials: procedural, for the bake. Soft patches of rust or verdigris, runs of it downwards, and (on the
# plated materials) seams and rows of rivets as a bump, from where a point is in its object.
class Nodes:
    def __init__(self, made):
        self.tree = made.node_tree
        self.nodes = self.tree.nodes
        self.links = self.tree.links
        self.place = self.nodes.new("ShaderNodeTexCoord")
        self.split = self.nodes.new("ShaderNodeSeparateXYZ")
        self.links.new(self.place.outputs["Object"], self.split.inputs["Vector"])

    def link(self, a, b):
        self.links.new(a, b)

    def math(self, op, a, b=None, c=None):
        node = self.nodes.new("ShaderNodeMath")
        node.operation = op
        for k, v in enumerate((a, b, c)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                node.inputs[k].default_value = v
            else:
                self.links.new(v, node.inputs[k])
        return node.outputs[0]

    def xyz(self, k):
        return self.split.outputs[k]

    def noise(self, scale, shift, detail=2.0):
        stretch = self.nodes.new("ShaderNodeMapping")
        stretch.inputs["Scale"].default_value = scale
        stretch.inputs["Location"].default_value = shift
        self.links.new(self.place.outputs["Object"], stretch.inputs["Vector"])
        tex = self.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = 1.0
        tex.inputs["Detail"].default_value = detail
        tex.inputs["Roughness"].default_value = 0.55
        self.links.new(stretch.outputs["Vector"], tex.inputs["Vector"])
        return tex.outputs["Fac"]

    def ramp(self, fac, low, high):
        node = self.nodes.new("ShaderNodeMapRange")
        node.interpolation_type = "SMOOTHSTEP"
        node.inputs["From Min"].default_value = low
        node.inputs["From Max"].default_value = high
        self.links.new(fac, node.inputs["Value"])
        return node.outputs["Result"]

    def mix(self, first, colour, fac):
        node = self.nodes.new("ShaderNodeMixRGB")
        if isinstance(first, tuple):
            node.inputs["Color1"].default_value = (*first, 1.0)
        else:
            self.links.new(first, node.inputs["Color1"])
        if isinstance(colour, tuple):
            node.inputs["Color2"].default_value = (*colour, 1.0)
        else:
            self.links.new(colour, node.inputs["Color2"])
        self.links.new(fac, node.inputs["Fac"])
        return node.outputs["Color"]

    def near(self, value, period, offset):
        """How far `value` is from the nearest of offset + k * period."""
        t = self.math("DIVIDE", self.math("SUBTRACT", value, offset), period)
        f = self.math("SUBTRACT", self.math("FRACT", self.math("ADD", t, 0.5)), 0.5)
        return self.math("MULTIPLY", self.math("ABSOLUTE", f), period)

    def rivets(self, across, along, row, spacing, size):
        """Domes in two rows `row` either side of a seam: `across` the distance from the seam, `along` the
        distance along it."""
        a = self.math("ABSOLUTE", self.math("SUBTRACT", across, row))
        b = self.near(along, spacing, 0.0)
        d = self.math("SQRT", self.math("ADD", self.math("MULTIPLY", a, a), self.math("MULTIPLY", b, b)))
        return self.math("POWER", self.math("MAXIMUM", self.math("SUBTRACT", 1.0, self.math("DIVIDE", d, size)), 0.0), 0.5)


def material(name, base, patch, streak=None, size=1.2, plates=None, rough=0.7, glow=None):
    """A painted material: `base` with soft patches of `patch` and (if given) runs of `streak` down from them.
    `plates` (seam spacing along the hull, offset, rivet spacing, seams round it per turn or 0) puts plate seams
    and rivets in as a bump. `glow` makes it shine (for the glow picture)."""
    made = bpy.data.materials.new(name)
    made.use_nodes = True
    n = Nodes(made)
    shader = next(x for x in n.nodes if x.type == "BSDF_PRINCIPLED")
    shader.inputs["Roughness"].default_value = rough
    for key in ("Specular IOR Level", "Specular"):
        if key in shader.inputs:
            shader.inputs[key].default_value = 0.15
    k = 1.0 / size
    colour = n.mix(base, patch, n.ramp(n.noise((k, k, k * 0.6), (0.0, 0.0, 0.0)), 0.48, 0.72))
    colour = n.mix(colour, tuple(c * 0.8 for c in base), n.ramp(n.noise((k * 3, k * 3, k * 3), (4.0, 2.0, 1.0)), 0.55, 0.8))
    if streak:
        colour = n.mix(colour, streak, n.ramp(n.noise((k * 2.5, k * 2.5, k * 0.2), (3.1, 7.7, 1.3), 3.0), 0.58, 0.76))
    if plates:
        seam_step, seam_at, rivet_step, round_seams = plates
        x, y, z = n.xyz(0), n.xyz(1), n.xyz(2)
        radius = n.math("SQRT", n.math("ADD", n.math("MULTIPLY", x, x), n.math("MULTIPLY", z, z)))
        arc = n.math("MULTIPLY", n.math("ARCTAN2", z, x), radius)
        ring = n.near(y, seam_step, seam_at)
        bump = n.rivets(ring, arc, 0.065, rivet_step, 0.026)
        groove = n.math("SUBTRACT", 1.0, n.ramp(ring, 0.0, 0.012))
        if round_seams:
            period = n.math("MULTIPLY", radius, 2.0 * math.pi / round_seams)
            t = n.math("DIVIDE", arc, period)
            f = n.math("SUBTRACT", n.math("FRACT", n.math("ADD", t, 0.5)), 0.5)
            lengthwise = n.math("MULTIPLY", n.math("ABSOLUTE", f), period)
            bump = n.math("MAXIMUM", bump, n.rivets(lengthwise, y, 0.065, rivet_step, 0.026))
            groove = n.math("MAXIMUM", groove, n.math("SUBTRACT", 1.0, n.ramp(lengthwise, 0.0, 0.012)))
        height = n.math("SUBTRACT", n.math("MULTIPLY", bump, 1.0), n.math("MULTIPLY", groove, 0.6))
        node = n.nodes.new("ShaderNodeBump")
        node.inputs["Strength"].default_value = 0.9
        node.inputs["Distance"].default_value = 0.02
        n.link(height, node.inputs["Height"])
        n.link(node.outputs["Normal"], shader.inputs["Normal"])
        # (the seams a little darker, the rivets' tops a little brighter)
        colour = n.mix(colour, tuple(c * 0.45 for c in base), n.math("MULTIPLY", groove, 0.8))
        colour = n.mix(colour, tuple(min(1.0, c * 1.35) for c in base), n.math("MULTIPLY", bump, 0.5))
    n.link(colour, shader.inputs["Base Color"])
    if glow:
        shader.inputs["Emission Color"].default_value = (*glow, 1.0)
        shader.inputs["Emission Strength"].default_value = 1.0
    return made


IRON = material("iron", (0.11, 0.085, 0.075), (0.24, 0.1, 0.045), (0.3, 0.12, 0.04), 1.4, (1.0, 0.4, 0.16, 6))
CONE = material("cone", (0.11, 0.085, 0.075), (0.24, 0.1, 0.045), (0.3, 0.12, 0.04), 1.2, (0.7, -2.2, 0.14, 6))
TOWER_IRON = material("tower", (0.12, 0.095, 0.085), (0.24, 0.1, 0.045), (0.3, 0.12, 0.04), 0.8, (0.5, 0.0, 0.12, 0))
PLAIN_IRON = material("plain_iron", (0.11, 0.085, 0.075), (0.24, 0.1, 0.045), (0.3, 0.12, 0.04), 0.9)
BRASS = material("brass", (0.46, 0.28, 0.06), (0.3, 0.24, 0.1), (0.16, 0.22, 0.14), 0.9, (1.0, 0.5, 0.15, 0), 0.5)
BRASS_PLAIN = material("brass_plain", (0.46, 0.28, 0.06), (0.3, 0.22, 0.09), None, 0.6, None, 0.5)
COPPER = material("copper", (0.5, 0.22, 0.1), (0.2, 0.3, 0.22), None, 0.5, None, 0.5)
TANK_GREEN = material("tank", (0.09, 0.14, 0.1), (0.06, 0.09, 0.07), (0.26, 0.2, 0.1), 0.7)
STEEL = material("steel", (0.13, 0.13, 0.13), (0.22, 0.1, 0.05), (0.26, 0.11, 0.04), 0.6)
DARK = material("dark", (0.01, 0.01, 0.01), (0.015, 0.012, 0.01))
DOME_GLASS = material("dome_glass", (0.05, 0.13, 0.14), (0.08, 0.17, 0.16), None, 1.5, None, 0.1)
PORT_GLASS = material("port_glass", (0.85, 0.5, 0.16), (0.95, 0.6, 0.2), None, 0.3, None, 0.1, (1.0, 0.36, 0.06))
LAMP_GLASS = material("lamp_glass", (0.85, 0.8, 0.55), (0.95, 0.9, 0.65), None, 0.3, None, 0.1, (1.0, 0.92, 0.6))
TUBE_GREEN = material("tube_green", (0.3, 0.8, 0.55), (0.4, 0.9, 0.6), None, 0.3, None, 0.1, (0.1, 1.0, 0.35))
TUBE_RED = material("tube_red", (0.85, 0.3, 0.2), (0.95, 0.4, 0.25), None, 0.3, None, 0.1, (1.0, 0.15, 0.05))
PAPER = material("paper", (0.62, 0.56, 0.42), (0.5, 0.44, 0.3), None, 0.4)
GLASS_NAMES = {m.name for m in (DOME_GLASS, PORT_GLASS, LAMP_GLASS, TUBE_GREEN, TUBE_RED)}


# --- Parts, each a closed mesh object with one material. All built in place (Blender world).
PARTS = []   # (object, group): group names what it belongs to ("hull", or a moving part's name)


def new_object(bm, mat, group, name="part"):
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    PARTS.append((obj, group))
    return obj


def frame_of(axis):
    """Two unit vectors square to `axis` and to each other."""
    axis = Vector(axis).normalized()
    other = Vector((0.0, 0.0, 1.0)) if abs(axis.z) < 0.9 else Vector((1.0, 0.0, 0.0))
    u = axis.cross(other).normalized()
    v = axis.cross(u).normalized()
    return axis, u, v


def loft(rings, caps=(True, True), outward=None):
    """A closed tube through rings of points (each a list, all the same count, going round the same way), its
    ends capped (a fan to the middle). Faces wound to face away from the tube's middle line."""
    bm = bmesh.new()
    vs = [[bm.verts.new(p) for p in ring] for ring in rings]
    n = len(rings[0])
    for a, b in zip(vs, vs[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    for k, end in ((0, caps[0]), (-1, caps[1])):
        if end:
            mid = sum((v.co for v in vs[k]), Vector()) / n
            c = bm.verts.new(mid)
            for i in range(n):
                bm.faces.new((vs[k][i], vs[k][(i + 1) % n], c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def circle(middle, axis, r, sides, phase=0.0, squash=(1.0, 1.0)):
    axis, u, v = frame_of(axis)
    return [Vector(middle) + (u * math.cos(phase + i / sides * math.tau) * squash[0] + v * math.sin(phase + i / sides * math.tau) * squash[1]) * r for i in range(sides)]


def cylinder(mat, group, p0, p1, r0, r1=None, sides=10, name="cyl"):
    r1 = r0 if r1 is None else r1
    axis = Vector(p1) - Vector(p0)
    return new_object(loft([circle(p0, axis, r0, sides), circle(p1, axis, r1, sides)]), mat, group, name)


def torus(mat, group, middle, axis, big, small, sides=16, round_sides=4, name="ring"):
    axis, u, v = frame_of(axis)
    bm = bmesh.new()
    rings = []
    for i in range(sides):
        a = i / sides * math.tau
        out = u * math.cos(a) + v * math.sin(a)
        centre = Vector(middle) + out * big
        rings.append([bm.verts.new(centre + (out * math.cos(b) + axis * math.sin(b)) * small)
                      for b in (k / round_sides * math.tau + math.pi / round_sides for k in range(round_sides))])
    for i in range(sides):
        a, b = rings[i], rings[(i + 1) % sides]
        for k in range(round_sides):
            m = (k + 1) % round_sides
            bm.faces.new((a[k], a[m], b[m], b[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_object(bm, mat, group, name)


def box(mat, group, middle, size, turn=None, name="box"):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts)
    if turn is not None:
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0.0, 0.0, 0.0), matrix=turn)
    bmesh.ops.translate(bm, vec=middle, verts=bm.verts)
    return new_object(bm, mat, group, name)


def prism(mat, group, outline, origin, u, v, thick, name="plate"):
    """A flat shape (points in the plane of `u` and `v` about `origin`), `thick` through, both faces flat."""
    u, v = Vector(u).normalized(), Vector(v).normalized()
    w = u.cross(v).normalized() * thick * 0.5
    bm = bmesh.new()
    front = [bm.verts.new(Vector(origin) + u * a + v * b + w) for a, b in outline]
    back = [bm.verts.new(Vector(origin) + u * a + v * b - w) for a, b in outline]
    bm.faces.new(front)
    bm.faces.new(list(reversed(back)))
    n = len(outline)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((front[i], back[i], back[j], front[j]))
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 4])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return new_object(bm, mat, group, name)


def tube(mat, group, points, r, sides=6, name="pipe", rounded=True):
    """A pipe through points (its bends rounded by putting in two points round each corner), capped."""
    pts = [Vector(p) for p in points]
    path = [pts[0]]
    for i in range(1, len(pts) - 1):
        if not rounded:
            path.append(pts[i])
            continue
        a, b, c = pts[i - 1], pts[i], pts[i + 1]
        cut = min((b - a).length, (c - b).length) * 0.35
        path += [b + (a - b).normalized() * cut, b.lerp(b + ((a - b).normalized() + (c - b).normalized()) * cut * 0.5, 0.6), b + (c - b).normalized() * cut]
    path.append(pts[-1])
    rings = []
    last_u = None
    for i, p in enumerate(path):
        d = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
        if last_u is None:
            _, u, _ = frame_of(d)
        else:
            u = (last_u - d * last_u.dot(d)).normalized()
        last_u = u
        v = d.cross(u)
        rings.append([p + (u * math.cos(k / sides * math.tau) + v * math.sin(k / sides * math.tau)) * r for k in range(sides)])
    return new_object(loft(rings), mat, group, name)


def hull_at(y):
    """The hull's radius at `y` (straight between its outline's points)."""
    pts = HULL
    if y >= pts[0][0]:
        return pts[0][1]
    for (y0, r0), (y1, r1) in zip(pts, pts[1:]):
        if y1 <= y <= y0 and y0 != y1:
            return r0 + (r1 - r0) * (y0 - y) / (y0 - y1)
    return pts[-1][1]


def on_hull(y, angle, out=0.0):
    """A point `out` off the hull's skin at `y`, `angle` round from the starboard side towards the top."""
    r = hull_at(y) + out
    return Vector((math.cos(angle) * r, y, math.sin(angle) * r))


def hull_normal(y, angle):
    eps = 0.01
    slope = (hull_at(y + eps) - hull_at(y - eps)) / (2 * eps)
    return Vector((math.cos(angle), -slope, math.sin(angle))).normalized()


# --- The hull: the iron body and tail cone, the brass band at the bow, closed in front by a ring round the dome
rings = []
mats = []
for y, r in HULL:
    rings.append([Vector((math.cos(a) * r, y, math.sin(a) * r)) for a in (i / SIDES * math.tau for i in range(SIDES))])
# (each stretch of the hull is its own part, so that each has its own material: the band, the body, the cone)
def stretch(lo, hi, mat, cap_front=False, cap_back=False, name="hull"):
    rs = [ring for (y, r), ring in zip(HULL, rings) if lo <= y <= hi]
    if lo <= 2.4 <= hi:
        # (the band's step: only the ring on this stretch's side of it)
        pick = [ring for (y, r), ring in zip(HULL, rings) if lo <= y <= hi]
        rs = pick[1:] if mat is IRON else pick[:-1]
    return new_object(loft(rs, (cap_front, cap_back)), mat, "hull", name)


band = stretch(2.4, 3.6, BRASS, True, True, "band")
body = stretch(-1.6, 2.4, IRON, True, True, "body")
cone = stretch(-3.72, -1.6, CONE, True, True, "cone")
# the dome: a glass bulge on the front of the band, in a brass frame (a ring at its foot, a ring round its
# middle, an upright and a level bar across it)
dome_rings = []
for k, t in enumerate((0.0, 0.3, 0.55, 0.75, 0.9)):
    a = t * math.pi * 0.5
    dome_rings.append(circle((0.0, 3.58 + DOME_DEEP * math.sin(a), 0.0), (0.0, 1.0, 0.0), DOME_R * math.cos(a), SIDES))
dome_bm = loft(dome_rings, (True, True))
new_object(dome_bm, DOME_GLASS, "hull", "dome")


def dome_point(t, angle, out=0.0):
    a = t * math.pi * 0.5
    r = DOME_R * math.cos(a) + out * math.cos(a)
    return Vector((math.cos(angle) * r, 3.58 + (DOME_DEEP + out) * math.sin(a), math.sin(angle) * r))


torus(BRASS_PLAIN, "hull", (0.0, 3.62, 0.0), (0.0, 1.0, 0.0), 1.25, 0.12, SIDES, 4, "dome_foot")
torus(BRASS_PLAIN, "hull", (0.0, 3.58 + DOME_DEEP * math.sin(0.5 * math.pi * 0.5) + 0.02, 0.0), (0.0, 1.0, 0.0), DOME_R * math.cos(0.5 * math.pi * 0.5) + 0.03, 0.045, 20, 4, "dome_ring")
for angle in (0.5 * math.pi, 0.0):
    arc = [dome_point(t / 5.0, angle, 0.03) for t in range(6)]
    back = [dome_point(t / 5.0, angle + math.pi, 0.03) for t in range(5, -1, -1)]
    tube(BRASS_PLAIN, "hull", arc[:-1] + back[1:], 0.04, 4, "dome_bar", False)
# brass rims at the band's back edge and round the body's middle (the strap)
torus(BRASS_PLAIN, "hull", (0.0, 2.4, 0.0), (0.0, 1.0, 0.0), 1.405, 0.06, SIDES, 4, "band_rim")
torus(PLAIN_IRON, "hull", (0.0, -0.75, 0.0), (0.0, 1.0, 0.0), hull_at(-0.75) + 0.005, 0.07, SIDES, 4, "strap")
# the stern: the end of the cone, the shaft, the cage
cylinder(BRASS_PLAIN, "hull", (0.0, -3.7, 0.0), (0.0, -3.86, 0.0), 0.36, 0.3, 12, "stern_cap")
cylinder(STEEL, "hull", (0.0, -3.84, 0.0), (0.0, PROP_Y + 0.05, 0.0), 0.08, 0.08, 6, "shaft")
torus(BRASS_PLAIN, "hull", (0.0, CAGE[0], 0.0), (0.0, 1.0, 0.0), CAGE[2], 0.045, 12, 4, "cage_front")
torus(BRASS_PLAIN, "hull", (0.0, CAGE[1], 0.0), (0.0, 1.0, 0.0), CAGE[2], 0.045, 12, 4, "cage_back")
torus(BRASS_PLAIN, "hull", (0.0, 0.5 * (CAGE[0] + CAGE[1]), 0.0), (0.0, 1.0, 0.0), CAGE[2], 0.03, 12, 3, "cage_mid")
for k in range(6):
    a = (k + 0.5) / 6.0 * math.tau
    cylinder(BRASS_PLAIN, "hull", (math.cos(a) * CAGE[2], CAGE[0], math.sin(a) * CAGE[2]), (math.cos(a) * CAGE[2], CAGE[1], math.sin(a) * CAGE[2]), 0.025, None, 4, "cage_bar")
for a in (0.25 * math.pi, 0.75 * math.pi):
    # two crossed spokes over the cage's back
    cylinder(BRASS_PLAIN, "hull", (math.cos(a) * CAGE[2], CAGE[1] - 0.01, math.sin(a) * CAGE[2]), (-math.cos(a) * CAGE[2], CAGE[1] - 0.01, -math.sin(a) * CAGE[2]), 0.025, None, 4, "cage_spoke")
# (struts from the cone to the cage's front ring)
for k in range(4):
    a = (k + 0.5) / 4.0 * math.tau
    tube(BRASS_PLAIN, "hull", [on_hull(-3.45, a, -0.02), Vector((math.cos(a) * (CAGE[2] - 0.02), CAGE[0] + 0.02, math.sin(a) * (CAGE[2] - 0.02)))], 0.035, 4, "cage_strut")

# --- The fins: an upper and a lower fin and two side fins on the tail cone, each with a flap (the rudder, the
# planes) hinged behind it.
FIN_ROOT = (-2.0, -3.25)        # where each fin's root runs along the cone (y)
FIN_HINGE = -3.3                # the flaps' hinge
FIN_BACK = -3.62                # the flaps' back edge
FIN_SPAN = {"up": 1.0, "down": 0.85, "side": 0.75}


def fin(way, span, group):
    """A fixed fin and its flap. `way` the direction out from the cone (a unit vector square to Y)."""
    way = Vector(way)
    y0, y1 = FIN_ROOT
    r0, r1 = hull_at(y0), hull_at(y1)
    # the fixed fin: swept back, its tip square
    outline = [(y0, r0 - 0.05), (y1, r1 - 0.05), (y1 - 0.02, r1 + span * 0.92), (y0 - 0.65, r1 + span)]
    side = Vector((0.0, 1.0, 0.0)).cross(way).normalized()
    prism(PLAIN_IRON, "hull", [(a, b) for a, b in outline], (0.0, 0.0, 0.0), Vector((0.0, 1.0, 0.0)), way, 0.09, "fin")
    # the flap behind it
    rh = hull_at(FIN_HINGE)
    flap = [(FIN_HINGE, rh - 0.04), (FIN_BACK, hull_at(FIN_BACK) + 0.02), (FIN_BACK, rh + span * 0.88), (FIN_HINGE, rh + span * 0.9)]
    obj = prism(PLAIN_IRON, group, flap, (0.0, 0.0, 0.0), Vector((0.0, 1.0, 0.0)), way, 0.07, "flap")
    # (a hinge pin along the flap's front edge)
    return obj


fin((0.0, 0.0, 1.0), FIN_SPAN["up"], "Rudder")
fin((0.0, 0.0, -1.0), FIN_SPAN["down"], "Rudder")
fin((1.0, 0.0, 0.0), FIN_SPAN["side"], "Planes")
fin((-1.0, 0.0, 0.0), FIN_SPAN["side"], "Planes")

# --- The propeller: a hub and four twisted blades
cylinder(BRASS_PLAIN, "Propeller", (0.0, PROP_Y + 0.12, 0.0), (0.0, PROP_Y - 0.14, 0.0), 0.13, 0.06, 8, "hub")
for k in range(4):
    a = k / 4.0 * math.tau
    radial = Vector((math.cos(a), 0.0, math.sin(a)))
    round_way = Vector((0.0, 1.0, 0.0)).cross(radial)
    bm = bmesh.new()
    rows = []
    for t, chord, twist in ((0.1, 0.16, 0.95), (0.42, 0.3, 0.7), (0.66, 0.26, 0.55), (0.76, 0.1, 0.5)):
        c = radial * t + Vector((0.0, PROP_Y, 0.0))
        d = (round_way * math.cos(twist) + Vector((0.0, 1.0, 0.0)) * math.sin(twist)).normalized()
        n = d.cross(radial).normalized()
        rows.append([bm.verts.new(c + d * chord * 0.5), bm.verts.new(c + n * 0.025), bm.verts.new(c - d * chord * 0.5), bm.verts.new(c - n * 0.025)])
    for r0, r1 in zip(rows, rows[1:]):
        for i in range(4):
            j = (i + 1) % 4
            bm.faces.new((r0[i], r0[j], r1[j], r1[i]))
    bm.faces.new(rows[0])
    bm.faces.new(list(reversed(rows[-1])))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    new_object(bm, BRASS_PLAIN, "Propeller", "blade")

# --- The conning tower: an oval drum on the body, a brass collar at its foot, a low domed top with a round
# hatch, a door in its front with a slot of a window, and a rail of rivets.
tx, ty, tw, tl = TOWER
foot = hull_at(ty) - 0.12
tower_rings = []
for z, s in ((foot, 1.0), (TOWER_TOP - 0.08, 0.94), (TOWER_TOP, 0.92), (TOWER_TOP + 0.12, 0.78), (TOWER_TOP + 0.18, 0.5)):
    tower_rings.append([Vector((tx + math.cos(a) * tw * s, ty + math.sin(a) * tl * s, z)) for a in (i / 16 * math.tau for i in range(16))])
new_object(loft(tower_rings), TOWER_IRON, "hull", "tower")
collar = []
for z, s in ((hull_at(ty) - 0.05, 1.12), (hull_at(ty) + 0.12, 1.1), (hull_at(ty) + 0.16, 1.02)):
    collar.append([Vector((tx + math.cos(a) * tw * s, ty + math.sin(a) * tl * s, z)) for a in (i / 16 * math.tau for i in range(16))])
new_object(loft(collar), BRASS_PLAIN, "hull", "collar")
torus(BRASS_PLAIN, "hull", (tx, ty, TOWER_TOP - 0.04), (0.0, 0.0, 1.0), 1.0, 0.035, 16, 4, "tower_rim")
# (the rim is drawn round the oval by squashing it afterwards)
rim = PARTS[-1][0]
rim.data.transform(Matrix.Translation((tx, ty, TOWER_TOP - 0.04)) @ Matrix.Diagonal((tw * 0.96, tl * 0.96, 1.0, 1.0)) @ Matrix.Translation((-tx, -ty, -(TOWER_TOP - 0.04))))
cylinder(BRASS_PLAIN, "hull", (tx, ty - 0.1, TOWER_TOP + 0.15), (tx, ty - 0.1, TOWER_TOP + 0.24), 0.27, 0.25, 12, "hatch")
cylinder(BRASS_PLAIN, "hull", (tx, ty - 0.1, TOWER_TOP + 0.24), (tx, ty - 0.1, TOWER_TOP + 0.29), 0.07, 0.07, 6, "hatch_knob")
box(STEEL, "hull", (tx, ty - 0.1 - 0.27, TOWER_TOP + 0.2), (0.24, 0.07, 0.07), None, "hatch_hinge")
door_y = ty + tl * 0.97
box(PLAIN_IRON, "hull", (tx, door_y - 0.04, 1.86), (0.46, 0.18, 0.56), None, "door")
box(DARK, "hull", (tx, door_y + 0.055, 1.98), (0.24, 0.03, 0.07), None, "door_slot")
box(BRASS_PLAIN, "hull", (tx + 0.15, door_y + 0.07, 1.8), (0.05, 0.05, 0.12), None, "door_handle")
# the periscope: a pipe up out of the tower's top at its back, an elbow forward, a head with a lens
peri_foot = Vector((tx - 0.18, ty - 0.42, TOWER_TOP + 0.08))
tube(STEEL, "Periscope", [peri_foot - Vector((0.0, 0.0, 0.5)), peri_foot + Vector((0.0, 0.0, 0.62)), peri_foot + Vector((0.0, 0.28, 0.62))], 0.07, 6, "periscope")
cylinder(BRASS_PLAIN, "Periscope", peri_foot + Vector((0.0, 0.22, 0.62)), peri_foot + Vector((0.0, 0.36, 0.62)), 0.1, 0.1, 8, "periscope_head")
cylinder(DARK, "Periscope", peri_foot + Vector((0.0, 0.36, 0.62)), peri_foot + Vector((0.0, 0.38, 0.62)), 0.07, 0.07, 8, "periscope_lens")
cylinder(BRASS_PLAIN, "hull", peri_foot + Vector((0.0, 0.0, -0.04)), peri_foot + Vector((0.0, 0.0, 0.1)), 0.12, 0.1, 8, "periscope_gland")
# the antenna: a short mast with a coil, at the tower's back on the other side
mast = Vector((tx + 0.2, ty - 0.48, TOWER_TOP + 0.05))
cylinder(STEEL, "hull", mast, mast + Vector((0.0, 0.0, 0.85)), 0.025, 0.015, 4, "antenna")
cylinder(BRASS_PLAIN, "hull", mast + Vector((0.0, 0.0, 0.85)), mast + Vector((0.0, 0.0, 0.9)), 0.04, 0.01, 6, "antenna_tip")
for k in range(3):
    torus(COPPER, "hull", mast + Vector((0.0, 0.0, 0.42 + k * 0.07)), (0.0, 0.0, 1.0), 0.06, 0.016, 6, 3, "coil")
cylinder(BRASS_PLAIN, "hull", mast + Vector((0.0, 0.0, -0.05)), mast + Vector((0.0, 0.0, 0.08)), 0.07, 0.06, 6, "antenna_foot")
# two valve tubes glowing on the deck behind the tower (green and red, after the concept)
for k, (dx, glass) in enumerate(((0.14, TUBE_GREEN), (-0.14, TUBE_RED))):
    base = Vector((dx, ty - tl - 0.42, hull_at(ty - tl - 0.42) - 0.04))
    cylinder(BRASS_PLAIN, "hull", base, base + Vector((0.0, 0.0, 0.14)), 0.1, 0.09, 8, "tube_socket")
    cylinder(glass, "hull", base + Vector((0.0, 0.0, 0.14)), base + Vector((0.0, 0.0, 0.42)), 0.07, 0.06, 6, "valve_tube")
    cylinder(glass, "hull", base + Vector((0.0, 0.0, 0.42)), base + Vector((0.0, 0.0, 0.48)), 0.06, 0.015, 6, "valve_tip")
# a short vent pipe forward of the tower on the band's top (from the concept: a stub by the top lamp)
cylinder(BRASS_PLAIN, "hull", (0.32, 2.75, hull_at(2.75) - 0.05), (0.32, 2.75, hull_at(2.75) + 0.22), 0.07, 0.07, 6, "vent")
cylinder(DARK, "hull", (0.32, 2.75, hull_at(2.75) + 0.22), (0.32, 2.75, hull_at(2.75) + 0.23), 0.055, 0.055, 6, "vent_mouth")

# --- Portholes: two a side, each a brass ring and glass glowing behind it
PORTS = [(1.45, math.radians(14.0)), (0.35, math.radians(14.0))]
for side in (1.0, -1.0):
    for y, a in PORTS:
        angle = a if side > 0 else math.pi - a
        n = hull_normal(y, angle)
        at = on_hull(y, angle)
        torus(BRASS_PLAIN, "hull", at + n * 0.02, n, 0.25, 0.06, 10, 3, "port_ring")
        cylinder(PORT_GLASS, "hull", at - n * 0.05, at + n * 0.03, 0.21, 0.21, 10, "port_glass")
# gauges on the body's side behind the portholes (from the concept)
for side in (1.0, -1.0):
    for y, a, r in ((-0.35, math.radians(30.0), 0.13), (-1.05, math.radians(38.0), 0.1)):
        angle = a if side > 0 else math.pi - a
        n = hull_normal(y, angle)
        at = on_hull(y, angle)
        cylinder(BRASS_PLAIN, "hull", at - n * 0.03, at + n * 0.06, r, r, 8, "gauge")
        cylinder(PAPER, "hull", at + n * 0.06, at + n * 0.075, r * 0.78, r * 0.78, 8, "gauge_face")

# --- Ballast tanks: one a side, strapped on, with copper pipes up into the hull
TANKS = []
for side in (1.0, -1.0):
    x, y, z, r, long = TANK
    x *= side
    rings_t = []
    for t, s in ((-0.5, 0.0), (-0.47, 0.62), (-0.42, 0.9), (-0.36, 1.0), (0.36, 1.0), (0.42, 0.9), (0.47, 0.62), (0.5, 0.0)):
        if s == 0.0:
            continue
        rings_t.append(circle((x, y + t * long, z), (0.0, 1.0, 0.0), r * s, 12))
    TANKS.append(new_object(loft(rings_t), TANK_GREEN, "hull", "tank"))
    for t in (-0.25, 0.25):
        torus(PLAIN_IRON, "hull", (x, y + t * long, z), (0.0, 1.0, 0.0), r + 0.02, 0.05, 12, 3, "tank_strap")
        # (a bracket from the strap's top-inner side up into the hull)
        inner = math.atan2(0.35, -side)
        inner_pt = Vector((x + math.cos(inner) * (r + 0.02) * 1.0, y + t * long, z + math.sin(inner) * (r + 0.02)))
        ha = math.atan2(inner_pt.z, inner_pt.x)
        hull_pt = on_hull(y + t * long, ha, -0.06)
        tube(PLAIN_IRON, "hull", [inner_pt, hull_pt], 0.06, 4, "tank_bracket")
    # the copper pipes: from the tank's top up beside the hull, back along it over the strap, and into the
    # cone through a flange
    run = math.radians(-2.0) if side > 0 else math.pi + math.radians(2.0)
    top = Vector((x, y - 0.35, z + r - 0.03))
    pipe_pts = [top, on_hull(y - 0.35, run, 0.125), on_hull(-1.45, run, 0.125), on_hull(-1.85, run, 0.0)]
    tube(COPPER, "hull", pipe_pts, 0.045, 6, "copper_pipe")
    n4 = hull_normal(-1.85, run)
    p4 = on_hull(-1.85, run)
    cylinder(BRASS_PLAIN, "hull", p4 - n4 * 0.03, p4 + n4 * 0.06, 0.09, 0.09, 6, "pipe_flange")
    cylinder(BRASS_PLAIN, "hull", top - Vector((0.0, 0.0, 0.04)), top + Vector((0.0, 0.0, 0.05)), 0.08, 0.07, 6, "pipe_flange")
    # and a second from the tank's front end forward and up into the band's back edge
    low = math.radians(-12.0) if side > 0 else math.pi + math.radians(12.0)
    high = math.radians(-4.0) if side > 0 else math.pi + math.radians(4.0)
    front = Vector((x, y + 0.5 * long - 0.02, z + 0.12))
    q3 = on_hull(2.05, high)
    tube(COPPER, "hull", [front, front + Vector((0.0, 0.2, 0.0)), on_hull(y + 0.5 * long + 0.3, low, 0.1), q3], 0.04, 6, "copper_pipe")
    n3 = hull_normal(2.05, high)
    cylinder(BRASS_PLAIN, "hull", q3 - n3 * 0.03, q3 + n3 * 0.06, 0.08, 0.08, 6, "pipe_flange")
    cylinder(BRASS_PLAIN, "hull", front - Vector((0.0, 0.04, 0.0)), front + Vector((0.0, 0.05, 0.0)), 0.07, 0.07, 6, "pipe_flange")

# --- Searchlights: a brass drum on a bracket, a glowing lens in front
for key, (at, aim) in LAMPS.items():
    at, aim = Vector(at), Vector(aim).normalized()
    cylinder(BRASS_PLAIN, "hull", at - aim * 0.26, at - aim * 0.02, 0.1, 0.15, 10, "lamp")
    torus(BRASS_PLAIN, "hull", at - aim * 0.02, aim, 0.15, 0.03, 10, 3, "lamp_rim")
    cylinder(LAMP_GLASS, "hull", at - aim * 0.04, at + aim * 0.005, 0.13, 0.13, 10, "lamp_lens")
    # its bracket down (or up) to the hull
    toward = on_hull(at.y - 0.12, math.atan2(at.z, at.x), -0.06)
    tube(PLAIN_IRON, "hull", [at - aim * 0.16, toward], 0.045, 4, "lamp_bracket")

# --- The arms: a brass shoulder on each side of the band, an upper arm, a forearm, a two-fingered claw
ARMS = {}
for side, label in ((1.0, "Right"), (-1.0, "Left")):
    sa = SHOULDER_ANGLE if side > 0 else math.pi - SHOULDER_ANGLE
    hull_pt = on_hull(SHOULDER_Y, sa)
    shoulder = Vector((side * ARM_X, SHOULDER_Y, hull_pt.z))
    # the shoulder's mount: a brass boss on the band, its pin out to the arm
    cylinder(BRASS_PLAIN, "hull", Vector((hull_pt.x - side * 0.05, SHOULDER_Y, hull_pt.z)), Vector((side * (ARM_X - 0.1), SHOULDER_Y, hull_pt.z)), 0.24, 0.2, 12, "shoulder")
    down = Vector((0.0, math.sin(ARM_DOWN), -math.cos(ARM_DOWN)))
    elbow = shoulder + down * UPPER
    fore_dir = Vector((0.0, math.cos(FORE_DOWN), -math.sin(FORE_DOWN)))
    wrist = elbow + fore_dir * FORE
    g = "Arm" + label
    # the upper arm: a flat bar between two discs (shoulder and elbow)
    cylinder(STEEL, g, shoulder - Vector((side * 0.09, 0.0, 0.0)), shoulder + Vector((side * 0.09, 0.0, 0.0)), 0.16, 0.16, 10, "joint")
    cylinder(BRASS_PLAIN, g, shoulder + Vector((side * 0.09, 0.0, 0.0)), shoulder + Vector((side * 0.13, 0.0, 0.0)), 0.07, 0.07, 6, "pin")
    side_axis = Vector((1.0, 0.0, 0.0))
    bar_u = down
    bar_w = side_axis.cross(bar_u).normalized()
    bar = [(-0.02, -0.1), (UPPER + 0.02, -0.09), (UPPER + 0.02, 0.09), (-0.02, 0.12)]
    prism(STEEL, g, bar, shoulder, bar_u, bar_w, 0.13, "upper_arm")
    gf = "Forearm" + label
    cylinder(STEEL, gf, elbow - Vector((side * 0.08, 0.0, 0.0)), elbow + Vector((side * 0.08, 0.0, 0.0)), 0.13, 0.13, 10, "joint")
    cylinder(BRASS_PLAIN, gf, elbow + Vector((side * 0.08, 0.0, 0.0)), elbow + Vector((side * 0.12, 0.0, 0.0)), 0.06, 0.06, 6, "pin")
    fbar_w = side_axis.cross(fore_dir).normalized()
    prism(STEEL, gf, [(0.0, -0.075), (FORE - 0.05, -0.06), (FORE - 0.05, 0.06), (0.0, 0.075)], elbow, fore_dir, fbar_w, 0.1, "forearm")
    cylinder(STEEL, gf, wrist - fore_dir * 0.12, wrist + fore_dir * 0.03, 0.09, 0.1, 8, "wrist")
    for finger, way in (("Upper", 1.0), ("Lower", -1.0)):
        gc = "Claw" + label + finger
        open_dir = (fore_dir * math.cos(FINGER_OPEN) + fbar_w * (way * math.sin(FINGER_OPEN) * (1.0 if fbar_w.z > 0 else -1.0))).normalized()
        # (a finger: out along open_dir, then hooked back in towards the other)
        root = wrist + fbar_w * (way * 0.05 * (1.0 if fbar_w.z > 0 else -1.0))
        knuckle = root + open_dir * FINGER * 0.65
        tip = knuckle + (fore_dir - (open_dir - fore_dir * open_dir.dot(fore_dir)).normalized() * 0.3).normalized() * FINGER * 0.42
        u = (knuckle - root).normalized()
        w = side_axis.cross(u).normalized()
        prism(STEEL, gc, [(0.0, -0.035), (FINGER * 0.65 + 0.03, -0.03), (FINGER * 0.65 + 0.03, 0.03), (0.0, 0.035)], root, u, w, 0.07, "finger")
        u2 = (tip - knuckle).normalized()
        w2 = side_axis.cross(u2).normalized()
        prism(STEEL, gc, [(-0.03, -0.035), ((tip - knuckle).length, -0.008), ((tip - knuckle).length, 0.008), (-0.03, 0.035)], knuckle, u2, w2, 0.06, "finger_tip")
    cylinder(BRASS_PLAIN, gf, wrist - Vector((side * 0.06, 0.0, 0.0)), wrist + Vector((side * 0.06, 0.0, 0.0)), 0.05, 0.05, 6, "wrist_pin")
    ARMS[label] = {"shoulder": shoulder, "elbow": elbow, "wrist": wrist}

# --- The beams: cones from each lens, bright at the lamp, nothing at the far end (vertex colours), not baked
BEAMS = {}
BEAM_MAT = bpy.data.materials.new("SubBeam")
for key, (at, aim) in LAMPS.items():
    at, aim = Vector(at), Vector(aim).normalized()
    axis, u, v = frame_of(aim)
    bm = bmesh.new()
    colour = bm.verts.layers.float_color.new("Color")
    # (three rings: at the lens, a third of the way, the far end; the light falls off fast, then slowly)
    rings_b = []
    for t, bright in ((0.0, 0.3), (0.3, 0.09), (1.0, 0.0)):
        ring = []
        for k in range(12):
            a = k / 12 * math.tau
            p = at + aim * BEAM_LONG * t + (u * math.cos(a) + v * math.sin(a)) * (0.12 + (BEAM_WIDE - 0.12) * t)
            vert = bm.verts.new(p)
            vert[colour] = (bright, bright * 0.85, bright * 0.55, 1.0)
            ring.append(vert)
        rings_b.append(ring)
    for r0, r1 in zip(rings_b, rings_b[1:]):
        for k in range(12):
            j = (k + 1) % 12
            bm.faces.new((r0[k], r0[j], r1[j], r1[k]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new("Beam" + key)
    bm.to_mesh(mesh)
    bm.free()
    mesh.color_attributes.active_color = mesh.color_attributes["Color"]
    mesh.color_attributes.render_color_index = 0
    obj = bpy.data.objects.new("Beam" + key, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(BEAM_MAT)
    BEAMS[key] = (obj, at)


# ============================================================================================
# Checks: winding (each closed part by itself), then the gaps and clipping
# ============================================================================================
def tri_bvh(objs, matrix_of=None):
    verts = []
    polys = []
    for obj in objs:
        m = obj.matrix_world if matrix_of is None else matrix_of(obj)
        mesh = obj.data
        base = len(verts)
        verts += [m @ v.co for v in mesh.vertices]
        for p in mesh.polygons:
            vs = list(p.vertices)
            for i in range(1, len(vs) - 1):
                polys.append((base + vs[0], base + vs[i], base + vs[i + 1]))
    return BVHTree.FromPolygons(verts, polys), verts, polys


def inside_out(obj):
    """Faces whose normal points into their own part: a ray from just off the face's middle along its normal
    crosses the part's skin an odd number of times."""
    tree, verts, polys = tri_bvh([obj], lambda o: Matrix.Identity(4))
    mesh = obj.data
    wrong = 0
    for p in mesh.polygons:
        vs = [mesh.vertices[i].co for i in p.vertices]
        middle = (vs[0] + vs[1] + vs[2]) / 3.0
        n = (vs[1] - vs[0]).cross(vs[2] - vs[0]).normalized()
        if n.length < 0.5:
            continue
        start = middle + n * 1e-4
        hits = 0
        at = start
        for _ in range(64):
            hit = tree.ray_cast(at, n)
            if hit[0] is None:
                break
            hits += 1
            at = hit[0] + n * 1e-4
        if hits % 2 == 1:
            wrong += 1
    return wrong


wrong_parts = {}
all_faces = 0
for obj, group in PARTS:
    bpy.context.view_layer.update()
    w = inside_out(obj)
    all_faces += len(obj.data.polygons)
    if w:
        wrong_parts[obj.name] = w
by_name = {}
for obj, group in PARTS:
    key = obj.name.split(".")[0]
    by_name[key] = by_name.get(key, 0) + sum(len(p.vertices) - 2 for p in obj.data.polygons)
print("PARTS submarine: " + ", ".join("%s %d" % kv for kv in sorted(by_name.items(), key=lambda kv: -kv[1])))
print("WINDING submarine: %s: %d parts, %d faces, %s" % ("ok" if not wrong_parts else "INSIDE OUT", len(PARTS), all_faces, wrong_parts or "none inside out"))


def group_objs(*names):
    return [o for o, g in PARTS if g in names]


def overlap(a_objs, b_objs, ma=None):
    ta, _, _ = tri_bvh(a_objs, ma)
    tb, _, _ = tri_bvh(b_objs)
    return len(ta.overlap(tb))


def rot_x_about(p, angle):
    return Matrix.Translation(p) @ Matrix.Rotation(angle, 4, "X") @ Matrix.Translation(-p)


def arm_matrices(label, reach, grip, side):
    """Where each piece of an arm is at `reach` and `grip` (as the node script turns them)."""
    a = ARMS[label]
    m_up = rot_x_about(a["shoulder"], REACH_SHOULDER * reach)
    m_fore = m_up @ rot_x_about(a["elbow"], REACH_ELBOW * reach)
    # (the upper finger turns down to close, the lower up; which is which depends on the side only through w)
    m_cu = m_fore @ rot_x_about(a["wrist"], -GRIP_TURN * grip)
    m_cl = m_fore @ rot_x_about(a["wrist"], GRIP_TURN * grip)
    return {"Arm" + label: m_up, "Forearm" + label: m_fore, "Claw" + label + "Upper": m_cu, "Claw" + label + "Lower": m_cl}


clip = []
fixed = group_objs("hull")
for reach in (0.0, 0.5, 1.0):
    for grip in (0.0, 1.0):
        mats = {}
        for label, side in (("Right", 1.0), ("Left", -1.0)):
            mats.update(arm_matrices(label, reach, grip, side))
        for label in ("Right", "Left"):
            names = ["Arm" + label, "Forearm" + label, "Claw" + label + "Upper", "Claw" + label + "Lower"]
            pieces = group_objs(*names)
            group_of = {o: g for o, g in PARTS}
            # the arm against the fixed hull (but its own shoulder boss, which it turns on)
            others = [o for o in fixed if o.name.split(".")[0] != "shoulder"]
            hits = overlap(pieces, others, lambda o: mats[group_of[o]])
            # the two fingers against each other
            tu, _, _ = tri_bvh(group_objs("Claw" + label + "Upper"), lambda o: mats[group_of[o]])
            tl, _, _ = tri_bvh(group_objs("Claw" + label + "Lower"), lambda o: mats[group_of[o]])
            fingers = len(tu.overlap(tl))
            clip.append((label, reach, grip, hits, fingers))
bad = [c for c in clip if c[3] or c[4]]
# (how far each finger can turn in before the two touch)
a = ARMS["Right"]
for k in range(1, 41):
    turn = k * 0.01
    tu, _, _ = tri_bvh(group_objs("ClawRightUpper"), lambda o: rot_x_about(a["wrist"], -turn))
    tl, _, _ = tri_bvh(group_objs("ClawRightLower"), lambda o: rot_x_about(a["wrist"], turn))
    if tu.overlap(tl):
        print("CLIP fingers: they touch when each has turned %.2f radians in (GRIP_TURN is %.2f)" % (turn, GRIP_TURN))
        break
print("CLIP arms: %s: %s" % ("ok" if not bad else "CLIPPING", ", ".join("%s reach %.1f grip %.0f: %d against the hull, %d finger on finger" % c for c in clip)))


def gap_to_hull(points):
    """The least and the most distance from the hull's skin of a set of points (outside: positive)."""
    out = []
    for p in points:
        r = math.hypot(p.x, p.z)
        out.append(r - hull_at(p.y))
    return min(out), max(out)


for obj in TANKS:
    pts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    near = min(math.hypot(p.x, p.z) - hull_at(p.y) for p in pts)
    print("CLIP tank: its skin comes to %.3f m of the hull's (below 0: sunk in it, by design a little)" % near)
pipes = [o for o, g in PARTS if o.name.startswith("copper_pipe")]
for obj in pipes:
    pts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    lo, hi = gap_to_hull(pts)
    print("CLIP %s: its skin from %.3f to %.3f m off the hull (ends meet it in flanges, the tank's ends inside the tank)" % (obj.name, lo, hi))
# the pipes against the tanks other than at their own ends, and against the portholes and gauges
others = [o for o, g in PARTS if o.name.split(".")[0] in ("port_ring", "port_glass", "gauge", "gauge_face", "tank_strap", "strap")]
print("CLIP pipes against portholes, gauges and straps: %d touching triangle pairs" % overlap(pipes, others))
# the beams start at the lenses and run clear of the hull
for key, (obj, at) in BEAMS.items():
    print("CLIP beam %s: %d triangle pairs inside the arms (at rest)" % (key, overlap([obj], group_objs("ArmLeft", "ArmRight", "ForearmLeft", "ForearmRight"))))

# ============================================================================================
# Join each group into one object, smooth with hard edges, unwrap into one atlas, bake
# ============================================================================================
PIVOTS = {
    "Hull": Vector((0.0, 0.0, 0.0)),
    "Propeller": Vector((0.0, PROP_Y, 0.0)),
    "Rudder": Vector((0.0, FIN_HINGE, 0.0)),
    "Planes": Vector((0.0, FIN_HINGE, 0.0)),
    "Periscope": peri_foot,
}
for label in ("Left", "Right"):
    PIVOTS["Arm" + label] = ARMS[label]["shoulder"]
    PIVOTS["Forearm" + label] = ARMS[label]["elbow"]
    PIVOTS["Claw" + label + "Upper"] = ARMS[label]["wrist"]
    PIVOTS["Claw" + label + "Lower"] = ARMS[label]["wrist"]
PARENT = {}
for label in ("Left", "Right"):
    PARENT["Forearm" + label] = "Arm" + label
    PARENT["Claw" + label + "Upper"] = "Forearm" + label
    PARENT["Claw" + label + "Lower"] = "Forearm" + label

JOINED = {}
for name in PIVOTS:
    group = "hull" if name == "Hull" else name
    objs = group_objs(group)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    obj = bpy.context.view_layer.objects.active
    obj.name = name
    obj.data.name = name
    for poly in obj.data.polygons:
        poly.use_smooth = True
    split = obj.modifiers.new("split", "EDGE_SPLIT")
    split.split_angle = math.radians(40.0)
    bpy.ops.object.modifier_apply(modifier="split")
    JOINED[name] = obj
tris = {}
for name, obj in JOINED.items():
    obj.data.calc_loop_triangles()
    tris[name] = len(obj.data.loop_triangles)
beam_tris = sum(len(o.data.polygons) * 2 for o, _ in BEAMS.values())
print("TRIS submarine: %d in all (%s), and %d in the three beams" % (sum(tris.values()), ", ".join("%s %d" % kv for kv in tris.items()), beam_tris))

meshes = list(JOINED.values())
bpy.ops.object.select_all(action="DESELECT")
for obj in meshes:
    obj.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=math.radians(60.0), island_margin=0.003)
bpy.ops.uv.average_islands_scale()
bpy.ops.uv.pack_islands(margin=0.003, rotate=True)
bpy.ops.object.mode_set(mode="OBJECT")


def gpu():
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        for kind in ("OPTIX", "CUDA"):
            try:
                prefs.compute_device_type = kind
                prefs.get_devices()
                if any(d.type == kind for d in prefs.devices):
                    for d in prefs.devices:
                        d.use = d.type == kind
                    bpy.context.scene.cycles.device = "GPU"
                    return kind
            except Exception:
                continue
    except Exception:
        pass
    bpy.context.scene.cycles.device = "CPU"
    return "CPU"


def bake():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    print("SUBMARINE baking on", gpu())
    scene.cycles.samples = SAMPLES
    world = bpy.data.worlds.new("sea")
    world.use_nodes = True
    # (light from all round, stronger from above: the sea's light; a soft sun high over the bow's quarter)
    sky = world.node_tree.nodes["Background"]
    grad = world.node_tree.nodes.new("ShaderNodeTexGradient")
    coords = world.node_tree.nodes.new("ShaderNodeTexCoord")
    sep = world.node_tree.nodes.new("ShaderNodeSeparateXYZ")
    world.node_tree.links.new(coords.outputs["Generated"], sep.inputs["Vector"])
    ramp = world.node_tree.nodes.new("ShaderNodeMapRange")
    ramp.inputs["From Min"].default_value = -1.0
    ramp.inputs["From Max"].default_value = 1.0
    ramp.inputs["To Min"].default_value = 0.3
    ramp.inputs["To Max"].default_value = 0.95
    world.node_tree.links.new(sep.outputs["Z"], ramp.inputs["Value"])
    world.node_tree.links.new(ramp.outputs["Result"], sky.inputs["Strength"])
    sky.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    scene.world = world
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 0.7
    sun.angle = math.radians(25.0)
    lamp = bpy.data.objects.new("sun", sun)
    bpy.context.collection.objects.link(lamp)
    lamp.rotation_euler = (math.radians(30.0), 0.0, math.radians(-30.0))
    scene.render.bake.margin = 6
    for path, size, kind in ((ATLAS, ATLAS_SIZE, "COMBINED"), (GLOW, GLOW_SIZE, "EMIT")):
        image = bpy.data.images.new(os.path.basename(path), size, size, alpha=False)
        for made in bpy.data.materials:
            if not made.use_nodes or made.name == "SubBeam":
                continue
            node = next((x for x in made.node_tree.nodes if x.type == "TEX_IMAGE" and x.name == "bake"), None)
            if node is None:
                node = made.node_tree.nodes.new("ShaderNodeTexImage")
                node.name = "bake"
            node.image = image
            made.node_tree.nodes.active = node
        if kind == "COMBINED":
            bake_set = scene.render.bake
            bake_set.use_pass_direct = True
            bake_set.use_pass_indirect = True
            bake_set.use_pass_diffuse = True
            bake_set.use_pass_glossy = False
            bake_set.use_pass_transmission = False
            bake_set.use_pass_emit = False
        bpy.ops.object.select_all(action="DESELECT")
        for obj in meshes:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = meshes[0]
        bpy.ops.object.bake(type=kind, use_clear=True)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        image.filepath_raw = path
        image.file_format = "PNG"
        image.save()
        print("SUBMARINE baked", path)
    bpy.data.objects.remove(lamp, do_unlink=True)


if BAKE:
    # (the periscope baked raised, so that its shaft is painted as seen when it is up, not as dark as inside
    # the tower)
    JOINED["Periscope"].location.z += PERISCOPE_LIFT
    bpy.context.view_layer.update()
    bake()
    JOINED["Periscope"].location.z -= PERISCOPE_LIFT
    bpy.context.view_layer.update()

# --- Origins at the pivots, parents, then save the editable file (procedural materials kept)
for name, obj in JOINED.items():
    p = PIVOTS[name]
    obj.data.transform(Matrix.Translation(-p))
    obj.location = p
bpy.context.view_layer.update()
for child, parent in PARENT.items():
    c, pa = JOINED[child], JOINED[parent]
    c.parent = pa
    c.matrix_parent_inverse = Matrix.Identity(4)
    c.location = PIVOTS[child] - PIVOTS[parent]
for key, (obj, at) in BEAMS.items():
    obj.data.transform(Matrix.Translation(-at))
    obj.location = at
bpy.context.view_layer.update()
os.makedirs(os.path.dirname(BLEND), exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=BLEND)

# --- Pictures (Workbench, the baked paint), for looking at beside the concept
if SHOTS:
    os.makedirs(SHOTS, exist_ok=True)
    scene = bpy.context.scene
    have_paint = os.path.exists(ATLAS)
    if have_paint:
        paint = bpy.data.images.load(ATLAS)
        for made in bpy.data.materials:
            if not made.use_nodes or made.name == "SubBeam":
                continue
            node = next((x for x in made.node_tree.nodes if x.type == "TEX_IMAGE" and x.name == "bake"), None)
            if node is None:
                node = made.node_tree.nodes.new("ShaderNodeTexImage")
                node.name = "bake"
            node.image = paint
            made.node_tree.nodes.active = node
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "TEXTURE" if have_paint else "MATERIAL"
    scene.display.shading.show_cavity = False
    scene.display.shading.show_backface_culling = True
    scene.render.resolution_x, scene.render.resolution_y = 1400, 900
    scene.world = bpy.data.worlds.new("bg")
    scene.world.color = (0.08, 0.2, 0.25)
    for obj, at in BEAMS.values():
        obj.hide_render = True
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    camera.data.type = "ORTHO"
    camera.data.clip_end = 1000.0
    scene.collection.objects.link(camera)
    scene.camera = camera
    views = [("left", (-1, 0, 0), (0, 0, 0.3), 11.0), ("right", (1, 0, 0), (0, 0, 0.3), 11.0),
             ("front", (0, 1, 0), (0, 0, 0.4), 6.6), ("back", (0, -1, 0), (0, 0, 0.4), 6.6),
             ("top", (0.0, 0.001, 1), (0, 0, 0), 11.0), ("under", (0.0, 0.001, -1), (0, 0, 0), 11.0),
             ("quarter_front", (0.9, 0.9, 0.5), (0, 0.5, 0), 10.5), ("quarter_back", (-0.9, -0.9, 0.5), (0, -0.5, 0), 10.5),
             ("bow_close", (0.8, 1.0, -0.4), (0.0, 3.3, -0.6), 4.5), ("tower_close", (1.0, 0.8, 0.6), (0.0, 0.8, 1.9), 3.0),
             ("stern_close", (0.9, -1.0, 0.3), (0.0, -3.6, 0.0), 3.6)]
    for view, direction, target, frame in views:
        offset = Vector(direction).normalized() * 40.0
        camera.data.ortho_scale = frame
        camera.location = Vector(target) + offset
        camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(Vector(direction).normalized().z) < 0.9 else "X").to_euler()
        scene.render.filepath = os.path.join(SHOTS, "%s.png" % view)
        bpy.ops.render.render(write_still=True)

# --- For the game: one plain material for the paint, one for the glass (the game puts the picture on both)
paint_mat = bpy.data.materials.new("SubPaint")
glass_mat = bpy.data.materials.new("SubGlass")
for name, obj in JOINED.items():
    slots = [s.material for s in obj.material_slots]
    which = [1 if m.name in GLASS_NAMES else 0 for m in slots]
    index = [which[poly.material_index] for poly in obj.data.polygons]
    obj.data.materials.clear()
    obj.data.materials.append(paint_mat)
    if 1 in index:
        obj.data.materials.append(glass_mat)
    # (set after the slots are remade: clearing them sets every face back to the first)
    for poly, k in zip(obj.data.polygons, index):
        poly.material_index = k
    print("SURFACES %s: %d faces of paint, %d of glass" % (name, index.count(0), index.count(1)))
bpy.ops.object.select_all(action="DESELECT")
for obj in list(JOINED.values()) + [o for o, _ in BEAMS.values()]:
    obj.hide_render = False
    obj.select_set(True)
os.makedirs(os.path.dirname(GLB), exist_ok=True)
bpy.ops.export_scene.gltf(filepath=GLB, export_format="GLB", export_yup=True, use_selection=True, export_apply=True,
                          export_animations=False, export_image_format="NONE", export_vertex_color="ACTIVE",
                          export_all_vertex_colors=False)
print("SUBMARINE wrote", GLB)
