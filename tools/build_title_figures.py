"""The three figures of the title scene: the boy from Warren, a sea captain and an old-time diver, on the boy's
skeleton (GameCommon's character controller), built in Blender. See tools/TITLE_FIGURES.md.

    blender -b --factory-startup --python tools/build_title_figures.py

Writes tools/blend/title_figures.blend (all three, editable, each in a collection of its own) and
models/title_boy.glb, title_captain.glb, title_diver.glb. Then `godot --headless --path . --import`.

- The boy is GameCommon's boy as Warren turns him out (Warren's scripts/looks.gd): the trousers outfit without its
  braces, no cap, the plain face, the head reshaped as HeadShape's "inside_round" (the same sum as
  scripts/head_shape.gd, done here once instead of at run time), the bowl cut, and Warren's colours. His body,
  hands, boots and hair are from GameCommon's boy_tp.glb (the boy collapsed to a crowd's budget); his head is the
  full boy.glb's, since it is seen close.
- The captain and the diver are built the way GameCommon's tools/build_figure_template.py builds a figure: with
  build_character.py's Builder (tubes and ellipsoids, each garment melted into one surface), its skeleton and its
  export, used in place from GameCommon (not copied). Each is modelled 1.25 m tall like the boy, as the template
  asks; TitleFigures stands them at 1.44 times that (1.8 m). Their arms hang a little out from the body (an A pose;
  the contract allows any angle from hanging to straight out) so that standing about needs little bending.

Godot space throughout (metres, Y up, the figure faces +Z, +X is his left), as in build_character.py.
"""

import math
import os
import sys
import tempfile

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
COMMON = "C:/Projects/GameCommon/godot/character-controller/files"
sys.path.insert(0, os.path.join(COMMON, "tools"))
import build_character as kit  # noqa: E402

X, Y, Z = kit.X, kit.Y, kit.Z
blend = kit.blend
# (kit.export writes its own .blend and .glb under kit.ROOT: they go to a scratch folder, and the figures are
# gathered from there into one .blend and exported again below)
STAGE = tempfile.mkdtemp(prefix="title_figures_")
os.makedirs(os.path.join(STAGE, "tools"), exist_ok=True)
kit.ROOT = STAGE
kit.PREVIEW_DIR = None
kit.ONLY = []

# --- The adults' skeleton (modelled 1.25 m tall). ---

ANKLE_Y = 0.05
SHIN, THIGH = 0.29, 0.30
KNEE_Y = ANKLE_Y + SHIN
HIP_Y = KNEE_Y + THIGH
SHOULDER_Y = 1.0
UPPER_ARM, FOREARM = 0.205, 0.185
WRIST_T = UPPER_ARM + FOREARM
TOE = Vector((0.0, -0.035, 0.085))
HEAD_CENTRE = Vector((0.0, 1.16, 0.008))
HEAD_RADII = Vector((0.060, 0.080, 0.072))


class Frame:
    """One adult's joints: how far apart his hips and shoulders are and how far out his arms hang."""

    def __init__(self, hip_x, shoulder_x, arm_angle):
        self.hip_x = hip_x
        self.shoulder_x = shoulder_x
        self.angle = math.radians(arm_angle)

    def shoulder(self, side):
        return Vector((side * self.shoulder_x, SHOULDER_Y, 0.0))

    def down(self, side):
        """Down the arm, from the shoulder."""
        return Vector((side * math.sin(self.angle), -math.cos(self.angle), 0.0))

    def out(self, side):
        """Square to the arm in his own plane, away from the body (the back of the hanging hand)."""
        return Vector((side * math.cos(self.angle), math.sin(self.angle), 0.0))

    def on_arm(self, side, t):
        return self.shoulder(side) + self.down(side) * t

    def bones(self):
        listed = [("hips", Vector((0.0, HIP_Y + 0.03, 0.0)), None), ("spine", Vector((0.0, 0.74, 0.0)), "hips"),
                  ("chest", Vector((0.0, 0.86, 0.0)), "spine"), ("neck", Vector((0.0, 1.035, 0.0)), "chest"),
                  ("head", Vector((0.0, 1.075, 0.0)), "neck")]
        for side, s in ((1.0, "_l"), (-1.0, "_r")):
            listed.append(("upper_arm" + s, self.shoulder(side), "chest"))
            listed.append(("forearm" + s, self.on_arm(side, UPPER_ARM), "upper_arm" + s))
            listed.append(("hand" + s, self.on_arm(side, WRIST_T), "forearm" + s))
            hip = Vector((side * self.hip_x, HIP_Y, 0.0))
            listed.append(("thigh" + s, hip, "hips"))
            listed.append(("shin" + s, hip - Y * THIGH, "hips"))
            listed.append(("foot" + s, hip - Y * (THIGH + SHIN), "hips"))
            listed.append(("toe" + s, hip - Y * (THIGH + SHIN) + TOE, "foot" + s))
        return listed

    def weights(self, part, p, rigid=(), head_parts=()):
        """Skin weights from where a point sits: smooth steps across each joint, as the template's."""
        side = 1.0 if p.x >= 0.0 else -1.0
        suffix = "_l" if side > 0 else "_r"
        if part in head_parts:
            return {"head": 1.0}
        if part in rigid:
            return {"chest": 1.0}
        if part == "head":
            skull = blend(1.06, 1.10, p.y)
            return {"neck": 1.0 - skull, "head": skull}
        if part == "hose":
            low = blend(0.95, 0.55, p.y)
            return {"chest": 1.0 - low, "hips": low}
        if part == "boots":
            shin = blend(0.06, 0.11, p.y)
            toe = blend(TOE.z - 0.022, TOE.z + 0.022, p.z) * (1.0 - shin)
            return {"shin" + suffix: shin, "foot" + suffix: 1.0 - shin - toe, "toe" + suffix: toe}
        # How far down the arm a point is, and how far from its line.
        rel = p - self.shoulder(side)
        t = rel.dot(self.down(side))
        radial = (rel - self.down(side) * t).length
        arm = blend(-0.03, 0.05, t) * blend(0.11, 0.075, radial) if p.y < SHOULDER_Y + 0.06 else 0.0
        if part == "hands":
            arm = 1.0
        fore = blend(UPPER_ARM - 0.035, UPPER_ARM + 0.035, t)
        hand = blend(WRIST_T - 0.02, WRIST_T + 0.015, t)
        leg = blend(HIP_Y + 0.035, HIP_Y - 0.05, p.y)
        left = blend(-0.015, 0.015, p.x)
        shin = blend(KNEE_Y + 0.04, KNEE_Y - 0.04, p.y)
        low = blend(0.74 + 0.05, 0.74 - 0.05, p.y)
        high = blend(0.86 - 0.06, 0.86 + 0.05, p.y)
        neck = blend(1.035 - 0.03, 1.035 + 0.015, p.y) if abs(p.x) < 0.09 else 0.0
        trunk = (1.0 - arm) * (1.0 - leg)
        result = {
            "hips": trunk * low,
            "spine": trunk * (1.0 - low) * (1.0 - high),
            "chest": trunk * (1.0 - low) * high * (1.0 - neck),
            "neck": trunk * (1.0 - low) * high * neck,
            "upper_arm" + suffix: arm * (1.0 - fore),
            "forearm" + suffix: arm * fore * (1.0 - hand),
            "hand" + suffix: arm * fore * hand,
        }
        for name, share in (("_l", left), ("_r", 1.0 - left)):
            result["thigh" + name] = leg * share * (1.0 - shin)
            result["shin" + name] = leg * share * shin
        return result


def sleeve(b, frame, side, profile, segments=14):
    """A tube down the arm: (distance from the shoulder, radius across, radius front to back)."""
    rings = [(frame.on_arm(side, t), frame.out(side) * rx, Z * rz) for t, rx, rz in profile]
    b.tube(rings, segments)


def mitten(b, frame, side, size=1.0):
    """A hanging hand, palm in to the thigh, fingers together and a little curled, the thumb forward."""
    down, out = frame.down(side), frame.out(side)
    wrist = frame.on_arm(side, WRIST_T)
    # (distance past the wrist, half thickness, half width, how far curled in)
    palm = [(-0.045, 0.026, 0.030, 0.0), (0.0, 0.020, 0.028, 0.0), (0.03, 0.017, 0.036, 0.0), (0.065, 0.015, 0.037, 0.003),
            (0.095, 0.013, 0.032, 0.010), (0.112, 0.010, 0.024, 0.018)]
    rings = [(wrist + down * d * size - out * curl * size, out * ry * size, Z * rz * size) for d, ry, rz, curl in palm]
    b.tube(rings + kit.dome(rings[-1], down - out * 0.5, 0.010 * size, 2), 12)
    thumb = [wrist + (down * d - out * o + Z * f) * size for d, o, f in ((0.012, 0.004, 0.022), (0.035, 0.010, 0.036), (0.058, 0.016, 0.042))]
    b.strand(thumb, [0.012 * size, 0.011 * size, 0.009 * size])


def head_with_face(b, nose=1.0):
    """An egg of a head narrowing to the jaw, on a neck, with a brow, cheekbones, a nose and ears: form, no eyes."""
    c, r = HEAD_CENTRE, HEAD_RADII
    b.tube([kit.upright(0.0, y, -0.004, 0.040, 0.042) for y in (1.0, 1.04, 1.09)], 12)
    rings = []
    for k in range(1, 14):
        phi = -math.pi / 2 + math.pi * k / 14
        co, si = math.cos(phi), math.sin(phi)
        jaw = max(0.0, -si)
        rings.append(kit.upright(0.0, c.y + r.y * si, c.z + 0.008 * jaw, r.x * co * (1.0 - 0.18 * jaw ** 1.4), r.z * co))
    b.tube(rings, 20)
    b.ellipsoid(c + Vector((0.0, 0.015, 0.058)), Vector((0.048, 0.011, 0.016)))  # the brow
    for side in (1.0, -1.0):
        b.ellipsoid(c + Vector((side * 0.032, -0.014, 0.054)), Vector((0.022, 0.015, 0.016)))  # cheekbones
        b.ellipsoid(c + Vector((side * 0.060, -0.002, -0.006)), Vector((0.010, 0.022, 0.015)))  # ears
    b.ellipsoid(c + Vector((0.0, -0.008, 0.070)), Vector((0.012, 0.024, 0.014)))  # the bridge of the nose
    b.ellipsoid(c + Vector((0.0, -0.030, 0.080)), Vector((0.016 * nose, 0.014 * nose, 0.014 * nose)))  # its end


# =====================================================================================================
# The captain: a fishing-boat skipper. Peaked cap, white beard, a roll-neck fisherman's jumper, dark
# trousers, tall rubber sea boots, a pipe.
# =====================================================================================================

CAPTAIN = Frame(0.075, 0.14, 18.0)
C_SWEATER, C_TROUSERS, C_SKIN, C_BEARD, C_BOOTS, C_CAP, C_PEAK, C_PIPE, C_BRASS = range(9)
CAPTAIN_MATERIALS = [
    ("sweater", (0.80, 0.75, 0.63)),
    ("trousers", (0.20, 0.22, 0.27)),
    ("skin", (0.80, 0.60, 0.48)),
    ("beard", (0.80, 0.79, 0.76)),
    ("boots", (0.14, 0.13, 0.12)),
    ("cap", (0.15, 0.18, 0.27)),
    ("peak", (0.07, 0.07, 0.08)),
    ("pipe", (0.34, 0.21, 0.12)),
    ("brass", (0.78, 0.62, 0.30)),
]


def captain_sweater(b):
    # (height, half width, half depth, forward): a barrel of a man, his belly carried low
    profile = [(0.585, 0.130, 0.106, 0.006), (0.600, 0.140, 0.114, 0.008), (0.66, 0.146, 0.122, 0.014),
               (0.74, 0.147, 0.124, 0.016), (0.82, 0.145, 0.116, 0.010), (0.90, 0.152, 0.106, 0.004),
               (0.955, 0.158, 0.098, 0.0), (0.99, 0.150, 0.090, 0.0), (1.015, 0.118, 0.076, 0.0), (1.035, 0.070, 0.060, -0.002)]
    b.tube([kit.upright(0.0, y, z, rx, rz) for y, rx, rz, z in profile], 24)
    # The roll neck
    b.tube([kit.upright(0.0, y, -0.004, r, r * 1.02) for y, r in ((1.015, 0.057), (1.04, 0.059), (1.07, 0.057), (1.085, 0.050))], 20)
    for side in (1.0, -1.0):
        b.ellipsoid(CAPTAIN.shoulder(side) + Vector((-side * 0.025, -0.025, 0.0)), Vector((0.062, 0.045, 0.062)))
        sleeve(b, CAPTAIN, side, [(0.02, 0.054, 0.056), (0.12, 0.050, 0.052), (UPPER_ARM, 0.047, 0.049),
                                  (0.30, 0.044, 0.045), (0.35, 0.042, 0.043), (0.37, 0.040, 0.041)], 16)
    # A ribbed hem and cuffs
    b.tube([kit.upright(0.0, y, 0.006, rx, rz) for y, rx, rz in ((0.575, 0.128, 0.104), (0.582, 0.136, 0.110), (0.615, 0.140, 0.114), (0.622, 0.136, 0.110))], 24)
    for side in (1.0, -1.0):
        sleeve(b, CAPTAIN, side, [(0.335, 0.041, 0.042), (0.342, 0.045, 0.046), (0.378, 0.044, 0.045), (0.385, 0.039, 0.040)], 14)


def captain_trousers(b):
    b.tube([kit.upright(0.0, y, 0.004, rx, rz) for y, rx, rz in ((0.53, 0.06, 0.06), (0.56, 0.124, 0.104), (0.60, 0.128, 0.104), (0.63, 0.112, 0.090))], 20)
    for side in (1.0, -1.0):
        leg = [(HIP_Y, 0.064), (HIP_Y - 0.04, 0.070), (0.48, 0.066), (KNEE_Y + 0.03, 0.058), (0.30, 0.054)]
        b.tube([kit.upright(side * CAPTAIN.hip_x, y, 0.0, r, r * 1.04) for y, r in leg], 16)


def sea_boots(b, frame, top=0.33):
    for side in (1.0, -1.0):
        ankle = Vector((side * frame.hip_x, ANKLE_Y, 0.0))
        # heel to toe: (forward, centre height from the ankle, half width, half height)
        foot = [(-0.056, -0.016, 0.040, 0.034), (-0.024, -0.004, 0.049, 0.050), (0.022, -0.012, 0.052, 0.043),
                (0.066, -0.024, 0.055, 0.030), (0.112, -0.028, 0.054, 0.026), (0.150, -0.031, 0.044, 0.020)]
        rings = [(ankle + Vector((0.0, y, z)), X * rx, Y * ry) for z, y, rx, ry in foot]
        b.tube(kit.dome(rings[0], -Z, 0.016, 3)[::-1] + rings + kit.dome(rings[-1], Z, 0.022, 3), 16, 0.0)
        leg = [(0.03, 0.050, 0.004), (0.08, 0.054, 0.0), (0.16, 0.060, -0.002), (top - 0.035, 0.064, -0.002), (top - 0.03, 0.071, -0.002),
               (top + 0.01, 0.072, -0.002), (top + 0.012, 0.066, -0.002)]
        b.tube([kit.upright(ankle.x, y, z, r, r * 1.06) for y, r, z in leg], 16)


def captain_head(b):
    head_with_face(b, nose=1.15)


def captain_beard(b):
    """A full short beard and moustache, bushy brows, and the grey hair that shows under the cap: one surface."""
    c = HEAD_CENTRE
    b.ellipsoid(c + Vector((0.0, -0.066, 0.040)), Vector((0.044, 0.036, 0.036)))  # chin
    for side in (1.0, -1.0):
        b.ellipsoid(c + Vector((side * 0.040, -0.046, 0.022)), Vector((0.027, 0.036, 0.038)))  # jaw
        b.ellipsoid(c + Vector((side * 0.050, -0.016, 0.012)), Vector((0.018, 0.030, 0.034)))  # cheek
        b.ellipsoid(c + Vector((side * 0.057, 0.010, -0.002)), Vector((0.010, 0.030, 0.020)))  # sideburn
        b.ellipsoid(c + Vector((side * 0.020, -0.042, 0.074)), Vector((0.024, 0.010, 0.014)),
                    Matrix.Rotation(side * -0.35, 3, "Z"))  # moustache
        b.ellipsoid(c + Vector((side * 0.022, 0.026, 0.068)), Vector((0.019, 0.007, 0.009)),
                    Matrix.Rotation(side * 0.18, 3, "Z"))  # brows
    # the hair round the back and sides, under the cap
    b.ellipsoid(c + Vector((0.0, -0.008, -0.016)), Vector((0.063, 0.072, 0.066)))


def captain_cap(b):
    """A skipper's peaked cap: a band, a soft flat crown standing out over it."""
    crown = [(1.188, 0.063, 0.075), (1.205, 0.064, 0.076), (1.226, 0.067, 0.079), (1.244, 0.071, 0.083),
             (1.256, 0.069, 0.081), (1.264, 0.052, 0.062), (1.268, 0.028, 0.034)]
    b.tube([kit.upright(0.0, y, HEAD_CENTRE.z, rx, rz) for y, rx, rz in crown], 24)


def captain_peak(b):
    front = HEAD_CENTRE.z + 0.072
    peak = [(Vector((0.0, 1.198 - 0.30 * (z - front), z)), X * half, Y * 0.0045)
            for z, half in ((front, 0.064), (front + 0.022, 0.060), (front + 0.040, 0.050), (front + 0.052, 0.036))]
    b.tube(peak + kit.dome(peak[-1], Z, 0.006, 2), 14)


def captain_braid(b):
    # a cord over the peak, and a button at each end of it
    front = HEAD_CENTRE.z + 0.074
    pts = [Vector((math.sin(a) * 0.066, 1.205, HEAD_CENTRE.z + math.cos(a) * 0.078)) for a in (-0.9, -0.45, 0.0, 0.45, 0.9)]
    b.strand(pts, [0.0035] * len(pts), 6)
    for a in (-0.9, 0.9):
        b.ellipsoid(Vector((math.sin(a) * 0.069, 1.205, HEAD_CENTRE.z + math.cos(a) * 0.081)), Vector((0.006, 0.006, 0.004)),
                    Matrix.Rotation(a, 3, "Y"), 8, 3)
    del front


def captain_pipe(b):
    """A short straight pipe in the left corner of his mouth, the bowl up."""
    c = HEAD_CENTRE
    stem = [c + Vector((0.020, -0.046, 0.070)), c + Vector((0.032, -0.052, 0.098)), c + Vector((0.044, -0.058, 0.122))]
    b.strand(stem, [0.0042, 0.0045, 0.005], 8)
    bowl = c + Vector((0.050, -0.052, 0.130))
    b.tube([(bowl + Y * y, X * r, Z * r) for y, r in ((-0.016, 0.006), (-0.012, 0.012), (0.004, 0.013), (0.014, 0.012), (0.015, 0.009))], 12)


def captain_hands(b):
    for side in (1.0, -1.0):
        mitten(b, CAPTAIN, side, 1.05)


CAPTAIN_PARTS = [
    ("sweater", C_SWEATER, captain_sweater, (0.006, 3, 1300)),
    ("trousers", C_TROUSERS, captain_trousers, (0.006, 3, 500)),
    ("boots", C_BOOTS, lambda b: sea_boots(b, CAPTAIN), (0.005, 3, 700)),
    ("head", C_SKIN, captain_head, (0.0035, 3, 900)),
    ("beard", C_BEARD, captain_beard, (0.0035, 3, 600)),
    ("cap", C_CAP, captain_cap, None),
    ("peak", C_PEAK, captain_peak, None),
    ("braid", C_BRASS, captain_braid, None),
    ("pipe", C_PIPE, captain_pipe, None),
    ("hands", C_SKIN, captain_hands, (0.003, 2, 700)),
]


def captain_weights(part, p):
    return CAPTAIN.weights(part, p, head_parts=("beard", "cap", "peak", "braid", "pipe"))


# =====================================================================================================
# The diver, in standard dress (after the US Navy Mark V and Siebe Gorman's: shape only): a spun-copper
# helmet with four lights screwed onto a copper breastplate (the corselet), held to a rubberised canvas suit
# by brass brails with wing nuts; lead weights hung front and back; a belt with a knife; lead-soled canvas
# boots with brass toes; the air hose from the back of the helmet.
# =====================================================================================================

DIVER = Frame(0.082, 0.16, 22.0)
D_SUIT, D_RUBBER, D_SKIN, D_COPPER, D_BRASS, D_GLASS, D_LEAD, D_LEATHER, D_CANVAS = range(9)
DIVER_MATERIALS = [
    ("suit", (0.60, 0.53, 0.40)),
    ("rubber", (0.13, 0.12, 0.11)),
    ("skin", (0.80, 0.62, 0.50)),
    ("copper", (0.74, 0.44, 0.27)),
    ("brass", (0.80, 0.64, 0.32)),
    ("glass", (0.12, 0.16, 0.16)),
    ("lead", (0.34, 0.35, 0.37)),
    ("leather", (0.32, 0.20, 0.12)),
    ("canvas", (0.47, 0.41, 0.32)),
]
CORSELET_FRONT = 0.005


def corselet_lift(p):
    """The corselet's lower edge rides up over the shoulders, so the arms come out under it."""
    lift = 0.07 * min(1.0, (abs(p.x) / 0.2) ** 2) * blend(0.97, 0.86, p.y)
    return Vector((p.x, p.y + lift, p.z))


def diver_suit(b):
    profile = [(0.56, 0.150, 0.122, 0.004), (0.62, 0.166, 0.132, 0.008), (0.70, 0.171, 0.136, 0.012),
               (0.80, 0.170, 0.132, 0.010), (0.90, 0.172, 0.124, 0.006), (0.97, 0.160, 0.110, 0.0),
               (1.02, 0.120, 0.090, 0.0), (1.06, 0.070, 0.066, 0.0), (1.08, 0.058, 0.058, 0.0)]
    b.tube([kit.upright(0.0, y, z, rx, rz) for y, rx, rz, z in profile], 24)
    b.tube([kit.upright(0.0, y, 0.004, rx, rz) for y, rx, rz in ((0.50, 0.07, 0.07), (0.54, 0.14, 0.11), (0.60, 0.16, 0.124))], 20)
    for side in (1.0, -1.0):
        b.ellipsoid(DIVER.shoulder(side) + Vector((-side * 0.035, -0.035, 0.0)), Vector((0.065, 0.045, 0.068)))
        sleeve(b, DIVER, side, [(0.05, 0.058, 0.062), (0.10, 0.062, 0.064), (UPPER_ARM, 0.058, 0.06),
                                (0.29, 0.054, 0.056), (0.34, 0.048, 0.050), (0.36, 0.040, 0.042)], 16)
        leg = [(HIP_Y + 0.03, 0.082), (HIP_Y - 0.04, 0.085), (0.50, 0.080), (KNEE_Y + 0.02, 0.074), (0.26, 0.068), (0.19, 0.062)]
        b.tube([kit.upright(side * DIVER.hip_x, y, 0.0, r, r * 1.04) for y, r in leg], 16)
        # baggy folds: a ring at the knee, one at the elbow
        b.tube([kit.upright(side * DIVER.hip_x, y, 0.0, r, r * 1.04) for y, r in ((0.36, 0.074), (0.35, 0.079), (0.33, 0.079), (0.32, 0.073))], 16)
        sleeve(b, DIVER, side, [(UPPER_ARM - 0.02, 0.058, 0.060), (UPPER_ARM - 0.01, 0.063, 0.065), (UPPER_ARM + 0.012, 0.063, 0.065), (UPPER_ARM + 0.022, 0.057, 0.059)], 16)


def diver_cuffs(b):
    for side in (1.0, -1.0):
        sleeve(b, DIVER, side, [(0.33, 0.040, 0.042), (0.335, 0.053, 0.055), (0.385, 0.050, 0.052), (0.39, 0.036, 0.038)], 14)


def diver_hands(b):
    for side in (1.0, -1.0):
        mitten(b, DIVER, side, 1.08)


CORSELET = [(0.86, 0.200, 0.160), (0.90, 0.215, 0.168), (0.95, 0.240, 0.165), (1.00, 0.228, 0.150),
            (1.04, 0.180, 0.124), (1.07, 0.110, 0.100), (1.088, 0.098, 0.092), (1.096, 0.094, 0.088)]


def diver_corselet(b):
    b.place = corselet_lift
    b.tube([kit.upright(0.0, y, CORSELET_FRONT, rx, rz) for y, rx, rz in CORSELET], 24)
    b.place = None


def diver_brass(b):
    """The brails round the corselet's edge with their wing nuts, the neck ring, studs, the exhaust valve,
    the air inlet's elbow, the rims of the lights and the bars over the side and top ones, the belt buckle."""
    b.place = corselet_lift
    b.tube([kit.upright(0.0, y, CORSELET_FRONT, rx, rz) for y, rx, rz in ((0.852, 0.200, 0.160), (0.856, 0.208, 0.168), (0.882, 0.212, 0.171), (0.886, 0.205, 0.165))], 20)
    b.place = None
    for k in range(8):
        a = math.tau * (k + 0.5) / 8
        at = corselet_lift(Vector((math.sin(a) * 0.214, 0.869, CORSELET_FRONT + math.cos(a) * 0.173)))
        outward = Vector((math.sin(a) / 0.214, 0.0, math.cos(a) / 0.173)).normalized()
        turn = Matrix.Rotation(math.atan2(outward.x, outward.z), 3, "Y")
        b.ellipsoid(at, Vector((0.012, 0.006, 0.006)), turn, 6, 2)  # a wing nut
    # the neck ring the helmet screws onto
    b.tube([kit.upright(0.0, y, CORSELET_FRONT, r, r * 0.95) for y, r in ((1.088, 0.095), (1.092, 0.104), (1.112, 0.104), (1.116, 0.096))], 24)
    for side in (1.0, -1.0):
        for y, z in ((0.98, 0.125), (0.98, -0.12)):  # studs the weights hang on
            b.ellipsoid(Vector((side * 0.10, y, z)), Vector((0.009, 0.009, 0.009)), None, 6, 2)
    # the exhaust valve, low on his right
    valve = Vector((-0.085, 1.150, 0.082))
    axis = Vector((-0.75, 0.0, 0.66)).normalized()
    b.tube([(valve + axis * d, Y * r, axis.cross(Y) * r) for d, r in ((0.0, 0.017), (0.03, 0.017), (0.032, 0.021), (0.042, 0.021), (0.044, 0.012))], 12)
    # the air inlet at the back, an elbow the hose screws onto
    b.strand([Vector((0.035, 1.235, -0.105)), Vector((0.038, 1.258, -0.135)), Vector((0.04, 1.254, -0.165))], [0.016, 0.016, 0.017], 10)
    # the lights' rims and guards
    for centre, normal, radius, bars in LIGHTS:
        u = normal.cross(Y if abs(normal.y) < 0.9 else X).normalized()
        v = normal.cross(u)
        # (a ring: a strand round the glass, closed on itself)
        rim = 14 if radius > 0.04 else 10
        ring = [centre + normal * 0.006 + (u * math.cos(a) + v * math.sin(a)) * (radius + 0.006) for a in (math.tau * k / rim for k in range(rim + 1))]
        b.strand(ring, [0.0075] * len(ring), 5)
        for k in range(bars):
            off = (k - (bars - 1) / 2) * radius * 0.55
            b.strand([centre + normal * 0.016 + v * off + u * radius * s for s in (-1.0, 0.0, 1.0)], [0.0042] * 3, 4)
    # the belt's buckle
    b.ellipsoid(Vector((0.0, 0.68, 0.150)), Vector((0.026, 0.022, 0.008)), None, 10, 3)


# (centre, which way it looks out, glass radius, guard bars)
LIGHTS = [
    (Vector((0.0, 1.205, 0.126)), Vector((0.0, 0.0, 1.0)), 0.050, 0),
    (Vector((0.118, 1.205, 0.004)), Vector((1.0, 0.0, 0.0)), 0.036, 2),
    (Vector((-0.118, 1.205, 0.004)), Vector((-1.0, 0.0, 0.0)), 0.036, 2),
    (Vector((0.0, 1.287, 0.090)), Vector((0.0, 0.6, 0.8)), 0.026, 1),
]


def diver_helmet(b):
    profile = [(1.106, 0.098), (1.13, 0.110), (1.17, 0.120), (1.21, 0.122), (1.25, 0.116), (1.29, 0.100),
               (1.318, 0.075), (1.334, 0.045), (1.340, 0.020)]
    b.tube([kit.upright(0.0, y, 0.004, r, r * 0.98) for y, r in profile], 24)


def diver_glass(b):
    for centre, normal, radius, _ in LIGHTS:
        u = normal.cross(Y if abs(normal.y) < 0.9 else X).normalized()
        v = normal.cross(u)
        b.tube([(centre + normal * h, u * r, v * r) for h, r in ((-0.01, radius * 0.98), (0.0, radius), (0.006, radius * 0.9), (0.008, radius * 0.5))], 10)


def diver_weights_lead(b):
    """The lead weights hung front and back, each a shallow curved slab."""
    for z_side in (1.0, -1.0):
        rings = []
        for x in (-0.11, -0.09, -0.05, 0.0, 0.05, 0.09, 0.11):
            bulge = 0.17 - 0.12 * (x / 0.11) ** 2 * 0.25
            h = 0.075 if abs(x) < 0.1 else 0.055
            rings.append((Vector((x, 0.885, z_side * bulge)), Y * h, Z * 0.017))
        b.tube(rings, 6)


def diver_belt(b):
    b.tube([kit.upright(0.0, y, 0.006, rx, rz) for y, rx, rz in ((0.655, 0.168, 0.134), (0.66, 0.175, 0.142), (0.70, 0.176, 0.143), (0.705, 0.169, 0.135))], 18)
    # the knife's sheath, hung on his right, its handle up
    b.ellipsoid(Vector((-0.118, 0.585, 0.118)), Vector((0.020, 0.07, 0.012)), Matrix.Rotation(-0.6, 3, "Y"), 10, 5)
    b.ellipsoid(Vector((-0.120, 0.672, 0.124)), Vector((0.015, 0.032, 0.013)), Matrix.Rotation(-0.6, 3, "Y"), 10, 5)


def diver_boots(b):
    for side in (1.0, -1.0):
        ankle = Vector((side * DIVER.hip_x, ANKLE_Y, 0.0))
        foot = [(-0.06, 0.0, 0.045, 0.040), (-0.03, 0.01, 0.053, 0.052), (0.02, 0.0, 0.057, 0.046),
                (0.07, -0.01, 0.059, 0.034), (0.115, -0.012, 0.057, 0.028), (0.150, -0.014, 0.046, 0.022)]
        rings = [(ankle + Vector((0.0, y, z)), X * rx, Y * ry) for z, y, rx, ry in foot]
        b.tube(kit.dome(rings[0], -Z, 0.016, 3)[::-1] + rings + kit.dome(rings[-1], Z, 0.02, 3), 16, 0.032)
        b.tube([kit.upright(ankle.x, y, z, r, r * 1.05) for y, r, z in ((0.05, 0.058, 0.004), (0.12, 0.066, 0.0), (0.18, 0.070, -0.002), (0.215, 0.072, -0.002), (0.22, 0.066, -0.002))], 16)


def diver_soles(b):
    for side in (1.0, -1.0):
        x = side * DIVER.hip_x
        # the lead sole: a slab under the boot, heel to toe
        rings = [(Vector((x, 0.017, z)), X * w, Y * 0.017) for z, w in ((-0.075, 0.045), (-0.06, 0.056), (0.0, 0.062), (0.08, 0.064), (0.15, 0.060), (0.185, 0.045))]
        b.tube(rings, 12, 0.0)


def diver_toes(b):
    for side in (1.0, -1.0):
        b.ellipsoid(Vector((side * DIVER.hip_x, 0.052, 0.150)), Vector((0.052, 0.034, 0.05)), None, 12, 4)
        # leather straps over the instep and round the ankle
        b.tube([kit.upright(side * DIVER.hip_x, y, 0.006, r, r * 1.05) for y, r in ((0.14, 0.066), (0.142, 0.072), (0.168, 0.074), (0.17, 0.068))], 12)


def diver_hose(b):
    pts = [Vector(p) for p in ((0.04, 1.254, -0.16), (0.045, 1.24, -0.20), (0.05, 1.17, -0.235), (0.06, 1.0, -0.255),
                               (0.07, 0.75, -0.27), (0.08, 0.45, -0.30), (0.09, 0.20, -0.35), (0.10, 0.07, -0.42),
                               (0.11, 0.026, -0.52), (0.13, 0.024, -0.64))]
    smooth = []
    for i in range(len(pts) - 1):
        p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, len(pts) - 1)]
        for k in range(2):
            t = k / 2.0
            smooth.append(0.5 * (2.0 * p1 + (p2 - p0) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t * t + (3.0 * p1 - p0 - 3.0 * p2 + p3) * t * t * t))
    smooth.append(pts[-1])
    b.strand(smooth, [0.017] * len(smooth), 6)


DIVER_PARTS = [
    ("suit", D_SUIT, diver_suit, (0.006, 3, 1100)),
    ("cuffs", D_RUBBER, diver_cuffs, None),
    ("hands", D_SKIN, diver_hands, (0.003, 2, 460)),
    ("corselet", D_COPPER, diver_corselet, None),
    ("helmet", D_COPPER, diver_helmet, None),
    ("brass", D_BRASS, diver_brass, None),
    ("glass", D_GLASS, diver_glass, None),
    ("lead", D_LEAD, diver_weights_lead, None),
    ("belt", D_LEATHER, diver_belt, None),
    ("boots", D_CANVAS, diver_boots, (0.005, 2, 450)),
    ("soles", D_LEAD, diver_soles, None),
    ("toes", D_BRASS, diver_toes, None),
    ("hose", D_RUBBER, diver_hose, None),
]


def diver_weights(part, p):
    return DIVER.weights(part, p, rigid=("corselet", "helmet", "brass", "glass", "lead"))


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
# HeadShape.SHAPES "inside_round" (Warren's Looks.HEAD)
INSIDE_ROUND = {"chin": 0.15, "forward": 0.15, "jaw": 0.14, "flat": 0.07, "cheek": 0.07, "tall": 0.05, "brow": 0.03}


def _ease(a, b, x):
    t = min(max((x - a) / (b - a), 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


def head_shaped(p, centre, reach, how):
    """HeadShape._shaped, line for line (Godot space)."""
    u = Vector(((p.x - centre.x) / reach.x, (p.y - centre.y) / reach.y, (p.z - centre.z) / reach.z))
    front = _ease(-0.15, 0.75, u.z)
    low = _ease(0.05, -0.95, u.y)
    out = u.copy()
    out.x *= 1.0 - how["jaw"] * low * front
    out.x *= 1.0 - how["cheek"] * front * (1.0 - low) * _ease(1.0, 0.0, abs(u.y))
    out.y -= how["chin"] * low * front * front * 1.6
    out.z += how["forward"] * low * front
    flat = how["flat"]
    plane = 1.0 - flat
    if out.z > plane - 0.25:
        over = out.z - (plane - 0.25)
        out.z = plane - 0.25 + over / (1.0 + over * flat * 6.0)
    out.z += how["brow"] * front * _ease(0.0, 0.25, u.y) * _ease(0.6, 0.3, u.y) * 2.0
    out.y *= 1.0 + how["tall"] * _ease(0.0, 1.0, u.y)
    return Vector((centre.x + out.x * reach.x, centre.y + out.y * reach.y, centre.z + out.z * reach.z))


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


def build_boy(collection):
    tp = import_glb(BOY_TP)
    full = import_glb(BOY_FULL)
    source_armature = next(o for o in tp if o.type == "ARMATURE")
    joints = []
    for bone in source_armature.data.bones:
        joints.append((bone.name, kit.from_blender(bone.head_local), bone.parent.name if bone.parent else None))
    keep = [o for o in tp if o.type == "MESH" and o.name.split(".")[0] in BOY_KEEP]
    fine = [o for o in full if o.type == "MESH" and o.name.split(".")[0] in BOY_FULL_KEEP]
    head = next(o for o in fine if o.name.split(".")[0] == "boy_head__base")
    parts = keep + fine
    for o in parts:
        o.data.transform(o.matrix_world)
        o.parent = None
        o.matrix_world = Matrix.Identity(4)
        for m in list(o.modifiers):
            o.modifiers.remove(m)
    for o in tp + full:
        if o not in parts:
            bpy.data.objects.remove(o, do_unlink=True)
    # The head reshaped as Warren's: HeadShape "inside_round", from the round head's own bounds.
    points = [kit.from_blender(v.co) for v in head.data.vertices]
    low = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    high = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    centre, reach = (low + high) * 0.5, (high - low) * 0.5
    for v, p in zip(head.data.vertices, points):
        v.co = kit.to_blender(head_shaped(p, centre, reach, INSIDE_ROUND))
    head.data.update()
    # A new skeleton at the same joints, every bone straight up and unrotated (kit.make_armature), as the boy's is.
    armature = kit.make_armature(joints)
    armature.name = "boy_armature"
    materials = {name: make_material("boy_" + name, colour) for name, colour in BOY_COLOURS.items()}
    for o in parts:
        o.name = o.name.split(".")[0]
        o.data.name = o.name
        for i, slot in enumerate(o.material_slots):
            base = slot.material.name.split(".")[0] if slot.material else "skin"
            o.data.materials[i] = materials.get(base, materials["skin"])
        for poly in o.data.polygons:
            poly.use_smooth = True
        o.parent = armature
        o.modifiers.new("Armature", "ARMATURE").object = armature
    for o in [armature] + parts:
        for c in o.users_collection:
            c.objects.unlink(o)
        collection.objects.link(o)
    for m in list(bpy.data.materials):
        if m.users == 0:
            bpy.data.materials.remove(m)
    for c in list(bpy.data.collections):
        if c.name.startswith("glTF_not_exported"):
            bpy.data.collections.remove(c)
    return armature


# =====================================================================================================

METAL = {"copper": (0.55, 0.42), "brass": (0.6, 0.38), "glass": (0.0, 0.15)}


def gather(name, collection):
    """Brings a figure kit.export staged into this file, its names made its own."""
    path = os.path.join(STAGE, "tools", name + ".blend")
    with bpy.data.libraries.load(path, link=False) as (src, dst):
        dst.objects = list(src.objects)
    for o in dst.objects:
        collection.objects.link(o)
        if o.type == "ARMATURE":
            o.name = name + "_armature"
        else:
            o.name = name
            o.data.name = name
            for slot in o.material_slots:
                base = slot.material.name.split(".")[0]
                slot.material.name = name + "_" + base
                if base in METAL:
                    shader = next(n for n in slot.material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
                    shader.inputs["Metallic"].default_value = METAL[base][0]
                    shader.inputs["Roughness"].default_value = METAL[base][1]


def export(collection, path):
    bpy.ops.object.select_all(action="DESELECT")
    for o in collection.objects:
        o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_yup=True,
                              export_animations=False, export_skins=True, export_vertex_color="NONE")
    tris = sum(kit.triangle_count(o.data) for o in collection.objects if o.type == "MESH")
    print("EXPORTED %s tris=%d" % (os.path.basename(path), tris))


kit.export("captain", CAPTAIN.bones(), CAPTAIN_PARTS, captain_weights, CAPTAIN_MATERIALS)
kit.export("diver", DIVER.bones(), DIVER_PARTS, diver_weights, DIVER_MATERIALS)

bpy.ops.wm.read_factory_settings(use_empty=True)
made = {}
for name in ("boy", "captain", "diver"):
    made[name] = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(made[name])
build_boy(made["boy"])
gather("captain", made["captain"])
gather("diver", made["diver"])
os.makedirs(os.path.join(HERE, "blend"), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "blend", "title_figures.blend"))
for name, collection in made.items():
    export(collection, os.path.join(ROOT, "models", "title_%s.glb" % name))
