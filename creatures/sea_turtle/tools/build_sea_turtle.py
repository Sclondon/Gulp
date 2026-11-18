"""Builds GameCommon's sea turtles (creatures/sea_turtle) and exports them for Godot.

Run from the game's root (or anywhere: paths are from this file):
    blender --background --python creatures/sea_turtle/tools/build_sea_turtle.py
    blender --background --python creatures/sea_turtle/tools/build_sea_turtle.py -- [--only=green,leatherback] [<preview folder>]

For each type (green, hawksbill, loggerhead, leatherback) it writes three models to creatures/sea_turtle/models:
sea_turtle_<type>.glb (the full model, for close pictures), sea_turtle_<type>_game.glb (the game model: a few thousand
triangles spent on its outline, head, eyes and flippers) and sea_turtle_<type>_lo.glb (far off, many of them), and the
editable creatures/sea_turtle/tools/sea_turtle_<type>.blend holding all three (this folder has a .gdignore). Each model
is one still mesh with one surface: the shader (sea_turtle.gdshader) draws the shell's plates and pattern, the scales
and the eyes, strokes the fore flippers, steers with the hind ones, opens the beak, turns the head and draws it in. It
prints a WINDING line per model (nothing inside out) and an EYE line per type (the eye's place, for the shader).

Four sea turtles, built from what each species looks like (no picture was traced):

- GREEN (Chelonia mydas), a shell 1.1 m long: a smooth, low, teardrop shell, its plates side by side (five down the
  middle, four a side, a ring of small ones round the rim), each with a starburst pattern; a small blunt rounded head.
- HAWKSBILL (Eretmochelys imbricata), 0.9 m: a narrower shell, pointed behind, its thick plates overlapping like roof
  tiles and its rear rim serrated; a long narrow head with a hooked beak like a hawk's; amber and brown tortoiseshell.
- LOGGERHEAD (Caretta caretta), 1.0 m: a reddish-brown heart-shaped shell (broad in front, tapering behind), five
  plates a side; a very big, broad, blocky head with strong jaws.
- LEATHERBACK (Dermochelys coriacea), 1.8 m: no plates: a long leathery back tapering to a point behind, with seven
  ridges along it; blue-black speckled with white; very long fore flippers; a rounded head with two cusps on its beak.

Every one: a pale plastron (the shell's underside), a scaly head and flippers (scales drawn in the shader), a horny
beak whose lower half (a part of its own) the shader swings open, fore flippers held out like wings (the shader
strokes them), hind flippers trailing behind.

The numbers marked "as the shader has it" are in sea_turtle.gd / sea_turtle.gdshader too: change one, change the
other (the shell's plate layout: the scute function below and `_scute` in the shader must agree).
"""

import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "models")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ONLY = []
PREVIEW = ""
for _a in ARGS:
    if _a.startswith("--only="):
        ONLY = _a.split("=", 1)[1].split(",")
    else:
        PREVIEW = _a

NAME = "sea_turtle"
COLOUR = (0.3, 0.25, 0.15, 1.0)
# As the shader has it: hinges are written as metres / SPAN_M plus a half.
SPAN_M = 4.0

# ======================================================================================================
# The four types. Shell numbers are in shell lengths (L), from its front (s 0) to its back (s 1); head numbers in
# head lengths (HL); flipper numbers in shell lengths.
#   plan    half the shell's width, by s
#   top     how high the carapace rises above the rim, by s
#   under   how deep the plastron lies below height 0, by s
#   rim     how high the rim (the edge of the carapace) is, by s
#   wp      the plastron's half width as a share of the shell's; th the rim's thickness; bulge the plastron's
#   dome    how the carapace falls from its middle line to the rim (exponent: lower is rounder)
#   plates  the plate layout (as the shader has it, in sea_turtle.gd's TYPES): vw the middle row's half width as a
#           share of the shell's; mw the rim's ring of plates, how wide; nm how many rim plates a side (with half
#           the one at the front); vert, cost the seams of the middle row and of the side plates, by s (2: none);
#           slant how the side seams fan out; step how far each plate stands up from its seams; imb how much
#           thicker each plate grows towards its rear edge (overlapping plates); serr the rear rim's teeth
#   ridges  (leatherback) where the ridges run, as shares of the half width, and how high
# ======================================================================================================

TYPES = {
    "green": {
        "L": 1.1,
        "plan": [(0.0, 0.0), (0.006, 0.075), (0.02, 0.15), (0.05, 0.235), (0.1, 0.31), (0.2, 0.38), (0.32, 0.415),
                 (0.42, 0.425), (0.52, 0.418), (0.64, 0.39), (0.75, 0.34), (0.85, 0.27), (0.92, 0.195),
                 (0.965, 0.12), (0.99, 0.05), (1.0, 0.0)],
        "top": [(0.0, 0.0), (0.02, 0.032), (0.08, 0.078), (0.2, 0.128), (0.35, 0.152), (0.5, 0.158), (0.65, 0.146),
                (0.8, 0.112), (0.92, 0.062), (0.98, 0.022), (1.0, 0.0)],
        "under": [(0.0, 0.0), (0.03, 0.035), (0.1, 0.078), (0.2, 0.105), (0.4, 0.12), (0.6, 0.116), (0.78, 0.097),
                  (0.9, 0.064), (0.97, 0.03), (1.0, 0.0)],
        "rim": [(0.0, 0.018), (0.15, 0.003), (0.5, -0.008), (0.85, 0.002), (1.0, 0.016)],
        "wp": 0.68, "th": 0.012, "bulge": 0.01, "dome": 0.9,
        "plates": {"vw": 0.3, "mw": 0.062, "nm": 12.5, "vert": (0.25, 0.43, 0.6, 0.77), "cost": (0.31, 0.52, 0.73, 2.0),
                   "slant": 0.9, "step": 0.0035, "imb": 0.0, "serr": 0.0},
        "head": {
            "HL": 0.15, "ahead": 0.98, "y": -0.04, "wide": 1.2, "neck_wide": 0.12,
            "profile": [(0.0, 0.02, -0.06, -0.12, 0.004), (0.015, 0.1, -0.05, -0.18, 0.07),
                        (0.05, 0.17, -0.04, -0.23, 0.13), (0.12, 0.24, -0.03, -0.27, 0.19),
                        (0.25, 0.3, -0.02, -0.3, 0.25), (0.42, 0.33, -0.02, -0.32, 0.29),
                        (0.6, 0.33, -0.03, -0.33, 0.31), (0.78, 0.3, -0.04, -0.33, 0.3),
                        (0.95, 0.25, -0.06, -0.31, 0.27), (1.15, 0.23, -0.07, -0.31, 0.27),
                        (1.4, 0.25, -0.08, -0.34, 0.3), (1.7, 0.27, -0.09, -0.37, 0.33),
                        (1.95, 0.25, -0.09, -0.35, 0.3), (2.05, 0.12, -0.09, -0.26, 0.15)],
            "lip": [(0.0, -0.11), (0.42, -0.135), (1.0, -0.16)], "cusp": (0.0, 0.0, 1.0),
            "jaw_tip": 0.02, "jaw_round": 0.07, "corner": 0.42, "hinge_x": 0.62, "hinge_y": -0.17,
            "overhang": 0.025, "eye": (0.35, 60.0, 0.085, 0.03), "tongue": (0.12, 0.38, 0.035),
        },
        "fore": {"s": 0.17, "xin": 0.74, "y": -0.035, "length": 0.62, "chord": 0.17, "back": 0.3, "droop": 0.12,
                 "sweep": 0.3, "claws": (0.42,)},
        "hind": {"s": 0.8, "xin": 0.45, "y": -0.07, "length": 0.21, "chord": 0.15, "out": 0.17},
    },
    "hawksbill": {
        "L": 0.9,
        "plan": [(0.0, 0.0), (0.006, 0.066), (0.02, 0.13), (0.05, 0.205), (0.1, 0.265), (0.2, 0.325), (0.32, 0.355),
                 (0.42, 0.36), (0.52, 0.352), (0.64, 0.322), (0.75, 0.278), (0.85, 0.213), (0.92, 0.148),
                 (0.965, 0.085), (0.99, 0.03), (1.0, 0.0)],
        "top": [(0.0, 0.0), (0.02, 0.03), (0.08, 0.072), (0.2, 0.118), (0.35, 0.14), (0.5, 0.145), (0.65, 0.133),
                (0.8, 0.1), (0.92, 0.055), (0.98, 0.02), (1.0, 0.0)],
        "under": [(0.0, 0.0), (0.03, 0.033), (0.1, 0.075), (0.2, 0.1), (0.4, 0.115), (0.6, 0.112), (0.78, 0.093),
                  (0.9, 0.06), (0.97, 0.028), (1.0, 0.0)],
        "rim": [(0.0, 0.018), (0.15, 0.003), (0.5, -0.008), (0.85, 0.004), (1.0, 0.02)],
        "wp": 0.66, "th": 0.013, "bulge": 0.01, "dome": 0.85,
        "plates": {"vw": 0.27, "mw": 0.07, "nm": 12.5, "vert": (0.25, 0.43, 0.6, 0.77), "cost": (0.31, 0.52, 0.73, 2.0),
                   "slant": 0.9, "step": 0.0025, "imb": 0.005, "serr": 0.02},
        "head": {
            "HL": 0.17, "ahead": 1.05, "y": -0.04, "wide": 1.15, "neck_wide": 0.15,
            "profile": [(0.0, -0.05, -0.15, -0.205, 0.004), (0.02, 0.03, -0.12, -0.215, 0.035),
                        (0.07, 0.1, -0.09, -0.22, 0.07), (0.15, 0.16, -0.07, -0.23, 0.11),
                        (0.28, 0.22, -0.05, -0.26, 0.16), (0.45, 0.27, -0.04, -0.29, 0.21),
                        (0.62, 0.29, -0.04, -0.3, 0.24), (0.8, 0.27, -0.05, -0.3, 0.24),
                        (0.95, 0.22, -0.06, -0.29, 0.21), (1.15, 0.19, -0.07, -0.28, 0.19),
                        (1.4, 0.21, -0.08, -0.31, 0.23), (1.7, 0.24, -0.09, -0.34, 0.27),
                        (1.95, 0.23, -0.09, -0.33, 0.26), (2.05, 0.11, -0.09, -0.24, 0.14)],
            "lip": [(0.0, -0.215), (0.03, -0.205), (0.08, -0.17), (0.2, -0.135), (0.5, -0.13), (1.0, -0.15)],
            "cusp": (0.0, 0.0, 1.0),
            "jaw_tip": 0.06, "jaw_round": 0.08, "corner": 0.46, "hinge_x": 0.66, "hinge_y": -0.17,
            "overhang": 0.02, "eye": (0.42, 58.0, 0.075, 0.026), "tongue": (0.16, 0.42, 0.03),
        },
        "fore": {"s": 0.17, "xin": 0.74, "y": -0.035, "length": 0.6, "chord": 0.165, "back": 0.3, "droop": 0.12,
                 "sweep": 0.3, "claws": (0.38, 0.5)},
        "hind": {"s": 0.8, "xin": 0.45, "y": -0.07, "length": 0.21, "chord": 0.15, "out": 0.17},
    },
    "loggerhead": {
        "L": 1.0,
        "plan": [(0.0, 0.0), (0.006, 0.1), (0.02, 0.19), (0.05, 0.28), (0.1, 0.35), (0.18, 0.405), (0.28, 0.43),
                 (0.38, 0.43), (0.5, 0.41), (0.62, 0.37), (0.74, 0.31), (0.84, 0.24), (0.92, 0.165), (0.965, 0.1),
                 (0.99, 0.04), (1.0, 0.0)],
        "top": [(0.0, 0.0), (0.02, 0.035), (0.08, 0.085), (0.2, 0.14), (0.35, 0.165), (0.5, 0.17), (0.65, 0.158),
                (0.8, 0.12), (0.92, 0.065), (0.98, 0.022), (1.0, 0.0)],
        "under": [(0.0, 0.0), (0.03, 0.04), (0.1, 0.085), (0.2, 0.112), (0.4, 0.128), (0.6, 0.124), (0.78, 0.103),
                  (0.9, 0.068), (0.97, 0.032), (1.0, 0.0)],
        "rim": [(0.0, 0.02), (0.15, 0.004), (0.5, -0.008), (0.85, 0.003), (1.0, 0.018)],
        "wp": 0.68, "th": 0.013, "bulge": 0.012, "dome": 0.8,
        "plates": {"vw": 0.3, "mw": 0.064, "nm": 12.5, "vert": (0.24, 0.42, 0.6, 0.77), "cost": (0.24, 0.4, 0.56, 0.73),
                   "slant": 0.9, "step": 0.004, "imb": 0.0, "serr": 0.0},
        "head": {
            "HL": 0.25, "ahead": 0.95, "y": -0.035, "wide": 1.05, "neck_wide": 0.1,
            "profile": [(0.0, 0.03, -0.06, -0.14, 0.006), (0.015, 0.12, -0.05, -0.2, 0.09),
                        (0.05, 0.19, -0.04, -0.26, 0.16), (0.12, 0.26, -0.03, -0.31, 0.23),
                        (0.25, 0.32, -0.03, -0.34, 0.31), (0.42, 0.36, -0.03, -0.36, 0.37),
                        (0.6, 0.37, -0.04, -0.37, 0.41), (0.78, 0.35, -0.05, -0.37, 0.42),
                        (0.92, 0.29, -0.07, -0.35, 0.37), (1.05, 0.22, -0.08, -0.31, 0.27),
                        (1.3, 0.2, -0.09, -0.3, 0.25), (1.52, 0.22, -0.1, -0.32, 0.27),
                        (1.68, 0.2, -0.1, -0.3, 0.25), (1.75, 0.1, -0.1, -0.22, 0.13)],
            "lip": [(0.0, -0.13), (0.45, -0.16), (1.0, -0.19)], "cusp": (0.0, 0.0, 1.0),
            "jaw_tip": 0.02, "jaw_round": 0.07, "corner": 0.45, "hinge_x": 0.66, "hinge_y": -0.2,
            "overhang": 0.025, "eye": (0.33, 60.0, 0.065, 0.022), "tongue": (0.12, 0.4, 0.04),
        },
        "fore": {"s": 0.17, "xin": 0.74, "y": -0.035, "length": 0.62, "chord": 0.17, "back": 0.3, "droop": 0.12,
                 "sweep": 0.3, "claws": (0.38, 0.5)},
        "hind": {"s": 0.8, "xin": 0.45, "y": -0.07, "length": 0.21, "chord": 0.15, "out": 0.17},
    },
    "leatherback": {
        "L": 1.8,
        "plan": [(0.0, 0.0), (0.006, 0.07), (0.02, 0.13), (0.05, 0.19), (0.1, 0.245), (0.2, 0.29), (0.32, 0.305),
                 (0.45, 0.3), (0.58, 0.27), (0.7, 0.215), (0.8, 0.155), (0.88, 0.1), (0.94, 0.056), (0.98, 0.022),
                 (1.0, 0.0)],
        "top": [(0.0, 0.0), (0.03, 0.05), (0.1, 0.1), (0.25, 0.143), (0.4, 0.15), (0.6, 0.128), (0.8, 0.085),
                (0.92, 0.048), (0.98, 0.018), (1.0, 0.0)],
        "under": [(0.0, 0.0), (0.04, 0.06), (0.12, 0.12), (0.3, 0.158), (0.5, 0.152), (0.7, 0.115), (0.85, 0.065),
                  (0.95, 0.025), (1.0, 0.0)],
        "rim": [(0.0, 0.01), (0.2, -0.01), (0.5, -0.02), (0.8, -0.005), (1.0, 0.03)],
        "wp": 0.3, "th": 0.004, "bulge": 0.0, "dome": 0.6,
        "plates": None,
        "ridges": {"at": (0.0, 0.37, 0.72), "high": 0.009, "wide": 0.035},
        "head": {
            "HL": 0.145, "ahead": 1.0, "y": -0.045, "wide": 1.15, "neck_wide": 0.1,
            "profile": [(0.0, 0.03, -0.07, -0.16, 0.005), (0.015, 0.12, -0.06, -0.21, 0.08),
                        (0.05, 0.19, -0.05, -0.25, 0.14), (0.12, 0.26, -0.04, -0.29, 0.2),
                        (0.25, 0.32, -0.03, -0.32, 0.27), (0.42, 0.36, -0.03, -0.34, 0.32),
                        (0.6, 0.37, -0.04, -0.35, 0.34), (0.78, 0.35, -0.05, -0.36, 0.34),
                        (0.95, 0.31, -0.06, -0.36, 0.32), (1.15, 0.3, -0.07, -0.37, 0.31),
                        (1.4, 0.32, -0.08, -0.4, 0.34), (1.62, 0.31, -0.08, -0.39, 0.33),
                        (1.72, 0.15, -0.08, -0.28, 0.17)],
            "lip": [(0.0, -0.14), (0.45, -0.17), (1.0, -0.2)], "cusp": (0.045, 0.07, 0.022),
            "jaw_tip": 0.02, "jaw_round": 0.07, "corner": 0.45, "hinge_x": 0.66, "hinge_y": -0.2,
            "overhang": 0.02, "eye": (0.34, 62.0, 0.07, 0.024), "tongue": (0.12, 0.4, 0.035),
        },
        "fore": {"s": 0.15, "xin": 0.78, "y": -0.04, "length": 0.72, "chord": 0.17, "back": 0.3, "droop": 0.1,
                 "sweep": 0.32, "claws": ()},
        "hind": {"s": 0.8, "xin": 0.45, "y": -0.06, "length": 0.21, "chord": 0.15, "out": 0.6},
    },
}
ORDER = ("green", "hawksbill", "loggerhead", "leatherback")

# How many points: (columns over the carapace from the middle line to the rim, round the rim and under it to the
# plastron's edge, across the plastron) a side; rings along the shell (the step, as a share of L, mid shell and at
# its ends).
SHELL_FULL = (36, 12, 8)
SHELL_LO = (7, 3, 2)
SHELL_GAME = (8, 4, 3)
SHELL_GAME_BIG = (10, 4, 3)
RING_STEP = (0.0075, 0.003)
# The head's points round it, full and low; how closely the rings are spaced, in head lengths.
HEAD_AROUND = 60
HEAD_AROUND_LO = 14
HEAD_RINGS = ((1.0, 0.018), (99.0, 0.05))
ROUND = 0.92
JAW_WIDE = 0.96
GAP = 0.001
PALATE = 0.12
TROUGH = 0.2
# The game model: points round the head; how near (metres) the head's and the shell's skins keep to the full
# model's; how far apart their rings may be (metres); rings in the lower jaw; how many points the eye has.
GAME_AROUND = 16
GAME_TOL = 0.0015
GAME_SHELL_TOL = 0.0035
GAME_STEP = 0.05
GAME_MOUTH_STEP = 0.025
GAME_SHELL_STEP = 0.12
GAME_JAW = 7
GAME_EYE = (26, 2)
GAME_KEEP = ()


def smooth(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


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


class Curve:
    """A smooth curve through (x, y) points that never overshoots them."""

    def __init__(self, points, scale=1.0, xscale=1.0):
        self.xs = [p[0] * xscale for p in points]
        self.ys = [p[1] * scale for p in points]
        self.m = _slopes(self.xs, self.ys)

    def __call__(self, x):
        xs = self.xs
        x = max(xs[0], min(xs[-1], x))
        i = 0
        while i < len(xs) - 2 and x > xs[i + 1]:
            i += 1
        h = xs[i + 1] - xs[i]
        t = (x - xs[i]) / h
        return ((2 * t ** 3 - 3 * t ** 2 + 1) * self.ys[i] + (t ** 3 - 2 * t ** 2 + t) * h * self.m[i]
                + (-2 * t ** 3 + 3 * t ** 2) * self.ys[i + 1] + (t ** 3 - t ** 2) * h * self.m[i + 1])


# ======================================================================================================
# The type being built: `use(name)` sets these.
T = {}
L = 1.0
HALF = 0.5
NOSE_Z = -1.0
HL = 0.15
PROFILE = []
_XS = []
_CURVES = []
CORNER = HINGE_X = HINGE_Y = JAW_TIP = JAW_ROUND = OVERHANG = 0.0
EYE_AT = (0.0, 0.0, 0.0, 0.0)
TONGUE_AT = (0.0, 0.0, 0.0)
_LIP = None
_CUSP = (0.0, 0.0, 1.0)
W = TOP = UNDER = RIM = None
PLATES = None
RIDGES = None
BODY_FROM = BODY_TO = 0.0
_EDGE = None
GAME = False


def use(name):
    global T, L, HALF, NOSE_Z, HL, PROFILE, _XS, _CURVES, CORNER, HINGE_X, HINGE_Y, JAW_TIP, JAW_ROUND, OVERHANG
    global EYE_AT, TONGUE_AT, _LIP, _CUSP, W, TOP, UNDER, RIM, PLATES, RIDGES, BODY_FROM, BODY_TO
    T = TYPES[name]
    L = T["L"]
    HALF = L * 0.5
    h = T["head"]
    HL = h["HL"] * L
    NOSE_Z = -HALF - h["ahead"] * HL
    y0 = h["y"] * L
    PROFILE = [(p[0] * HL, p[1] * HL + y0, p[2] * HL + y0, p[3] * HL + y0, p[4] * HL * h.get("wide", 1.0) * (1.0 + h.get("neck_wide", 0.0) * smooth(0.95, 1.3, p[0]))) for p in h["profile"]]
    _XS = [p[0] for p in PROFILE]
    _CURVES = []
    for column in (1, 2, 3, 4):
        ys = [p[column] for p in PROFILE]
        _CURVES.append((ys, _slopes(_XS, ys)))
    BODY_FROM = 0.0015 * HL / 0.15
    BODY_TO = PROFILE[-1][0]
    _LIP = Curve([(x * HL, y * HL + y0) for x, y in h["lip"]])
    _CUSP = (h["cusp"][0] * HL, h["cusp"][1] * HL, h["cusp"][2] * HL)
    CORNER = h["corner"] * HL
    HINGE_X = h["hinge_x"] * HL
    HINGE_Y = h["hinge_y"] * HL + y0
    JAW_TIP = h["jaw_tip"] * HL
    JAW_ROUND = h["jaw_round"] * HL
    OVERHANG = h["overhang"] * HL
    e = h["eye"]
    EYE_AT = (e[0] * HL, e[1], e[2] * HL, e[3] * HL)
    t = h["tongue"]
    TONGUE_AT = (t[0] * HL, t[1] * HL, t[2] * HL)
    W = Curve(T["plan"], L)
    TOP = Curve(T["top"], L)
    UNDER = Curve(T["under"], L)
    RIM = Curve(T["rim"], L)
    PLATES = T.get("plates")
    RIDGES = T.get("ridges")
    edge_table()


# ======================================================================================================
# What a point is, for the shader:
#   vertex colour red   what it is made of, as a tenth (0 skin of the head and neck, 1 an eye, 2 a claw, 3 the
#                       tongue, 4 the carapace, 5 the plastron and the rim's underside, 6 the skin of a flipper)
#   vertex colour green on the head: how far inside the mouth it is (0 outside, 1 inside); on the shell: how far
#                       round the rim its nearest point of the rim is (0 the front middle, 1 the back middle)
#   vertex colour blue  on a flipper: how far along it, 0 its root to 1 its tip; on an eye, 0 its middle to 1 its
#                       rim; on the head and jaw: how far from the line of the mouth (0.5 on it; above it on the
#                       head and below it on the jaw, 0.5 + 1.25 x head lengths)
#   UV2.y               what moves it, as an eighth (0 nothing, 1 the lower jaw, 2 and 3 the left and right fore
#                       flippers, 4 and 5 the left and right hind flippers, 6 the head and neck)
#   UV.x, UV.y, UV2.x   for a moving part, its hinge (z, y, x, as metres / SPAN_M plus a half); on the shell, UV.x is
#                       half its width there and UV.y how far the point is from the rim, both in shell lengths
#                       (seen from above)
# (The glTF writer flips V: what is written here is 1 - v, so that Godot reads v.)

SKIN, EYE, CLAW, TONGUE, CARAPACE, PLASTRON, FLIPPER = range(7)
STILL, JAW, FORE_L, FORE_R, HIND_L, HIND_R, HEAD = range(7)
X = Vector((1.0, 0.0, 0.0))
Y = Vector((0.0, 1.0, 0.0))
Z = Vector((0.0, 0.0, 1.0))
TAU = math.tau


def to_b(p):
    return Vector((p.x, -p.z, p.y))


class Mesh:
    def __init__(self):
        self.verts = []
        self.faces = []
        # per point: (uv.x, uv.y, uv2.x, group, red, green, blue)
        self.data = []
        self.out = []
        self.count = {}
        self.kind = SKIN
        self.group = STILL
        self.hinge = Vector((0.0, 0.0, 0.0))

    def part(self, kind, group=STILL, hinge=None):
        self.kind = kind
        self.group = group
        self.hinge = Vector(hinge) if hinge is not None else Vector((0.0, 0.0, 0.0))

    def add(self, p, inside=0.0, along=0.0):
        h = self.hinge
        self.verts.append(Vector(p))
        self.data.append((h.z / SPAN_M + 0.5, h.y / SPAN_M + 0.5, h.x / SPAN_M + 0.5, self.group, self.kind / 10.0,
                          inside, along))
        return len(self.verts) - 1

    def add_shell(self, p, kind, wide, edge, round_at):
        self.verts.append(Vector(p))
        self.data.append((wide / L, edge / L, 0.5, STILL, kind / 10.0, round_at, 0.0))
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
            n = -n
        if len(points) == 4:
            a, b, c, d = points
            pa, pb, pc, pd = (self.verts[i] for i in points)

            def faces_out(p, q, r):
                return (q - p).cross(r - p).dot(n) > 0.0

            first = faces_out(pa, pb, pc) and faces_out(pa, pc, pd)
            second = faces_out(pa, pb, pd) and faces_out(pb, pc, pd)
            if not (first and second):
                halves = ((a, b, d), (b, c, d)) if second and not first else ((a, b, c), (a, c, d))
                for half in halves:
                    self.face(half, out, name)
                return
        self.faces.append(tuple(points))
        self.out.append((Vector(out), name))
        self.count[name] = self.count.get(name, 0) + 1


# ======================================================================================================
# THE SHELL. Seen from above it is the outline W(s) on each side; across, the carapace rises from the rim in a dome
# and the underside curves in and down to the flat plastron. `s` is how far back (0 its front, 1 its back).

def edge_table():
    """The rim seen from above, as a line of points down the left side from the front middle to the back middle
    (without the rear rim's teeth): for how far each point is from the rim, and how far round it."""
    global _EDGE
    ss = [i / 600.0 for i in range(601)]
    pts = np.array([(W(s), -HALF + s * L) for s in ss])
    seg = np.diff(pts, axis=0)
    lens = np.sqrt((seg ** 2).sum(axis=1))
    acc = np.concatenate([[0.0], np.cumsum(lens)])
    _EDGE = (pts, seg, lens, acc)


def rim_length():
    return float(_EDGE[3][-1])


def edge_of(xs, zs):
    """For points seen from above (|x|, z): how far each is from the rim (metres) and how far round it its nearest
    point of the rim is (0 the front middle, 1 the back middle)."""
    pts, seg, lens, acc = _EDGE
    p = np.stack([np.abs(np.asarray(xs)), np.asarray(zs)], axis=1)
    d = p[:, None, :] - pts[None, :-1, :]
    t = np.clip((d * seg[None, :, :]).sum(axis=2) / np.maximum(lens ** 2, 1e-12)[None, :], 0.0, 1.0)
    near = pts[None, :-1, :] + seg[None, :, :] * t[:, :, None]
    dist = np.sqrt(((p[:, None, :] - near) ** 2).sum(axis=2))
    k = dist.argmin(axis=1)
    rows = np.arange(len(p))
    return dist[rows, k], (acc[k] + t[rows, k] * lens[k]) / acc[-1]


def teeth_cut(s):
    """How far the rear rim is cut back between its teeth at `s` (metres): each rim plate's rear outer corner stands
    out as a point (as the shader has it: the rim plates)."""
    if not PLATES or PLATES["serr"] <= 0.0:
        return 0.0
    _, p = edge_of([W(s)], [-HALF + s * L])
    q = float(p[0]) * PLATES["nm"] + 0.5
    rear = smooth(0.55, 0.7, float(p[0])) * (1.0 - smooth(0.96, 1.0, float(p[0])))
    return PLATES["serr"] * L * (1.0 - (q - math.floor(q))) * rear


def tooth_rings():
    """The places along the shell where the rear rim's teeth have their points and notches."""
    if not PLATES or PLATES["serr"] <= 0.0:
        return []
    out = []
    pts, seg, lens, acc = _EDGE
    for k in range(1, int(PLATES["nm"]) + 1):
        for f in (k - 0.5 - 0.004, k - 0.5 + 0.004):
            p = f / PLATES["nm"]
            if 0.5 < p < 0.995:
                at = p * acc[-1]
                i = int(np.searchsorted(acc, at)) - 1
                i = max(0, min(len(lens) - 1, i))
                z = pts[i][1] + seg[i][1] * (at - acc[i]) / max(lens[i], 1e-9)
                out.append((z + HALF) / L)
    return out


def scute(s, a, w, e, p):
    """The plate at a place on the carapace (as the shader has it, `_scute`): s how far back, a how far out to the
    side, w the shell's half width there, e how far from the rim (all in shell lengths), p how far round the rim.
    Returns (how far to its nearest seam, how far from its front edge to its rear one 0..1)."""
    P = PLATES
    mw = P["mw"]
    if e < mw:
        q = p * P["nm"] + 0.5
        fr = q - math.floor(q)
        return min(mw - e, min(fr, 1.0 - fr) * (rim_length() / L) / P["nm"]), fr
    vw = P["vw"] * w
    if a < vw:
        b = (0.0,) + tuple(P["vert"]) + (1.0,)
        k = 0
        while k < 4 and s >= b[k + 1]:
            k += 1
        return min(vw - a, s - b[k], b[k + 1] - s, e - mw), (s - b[k]) / (b[k + 1] - b[k])
    cs = 0.5 + (s - 0.5) / (1.0 + P["slant"] * (a / max(w, 1e-6) - P["vw"]))
    c = (0.0,) + tuple(x for x in P["cost"] if x < 1.5) + (1.0,)
    k = 0
    while k < len(c) - 2 and cs >= c[k + 1]:
        k += 1
    return min(a - vw, cs - c[k], c[k + 1] - cs, e - mw), (cs - c[k]) / (c[k + 1] - c[k])


def plate_lift(s, a, w, e, p):
    """How far the carapace stands up from its plain dome at a place (shell lengths): each plate a shallow step
    up from its seams, and (hawksbill) thicker towards its rear edge, where it overlaps the next."""
    if not PLATES:
        return 0.0
    seam, fr = scute(s, a, w, e, p)
    up = smooth(0.0, 0.009, seam) * smooth(0.0, 0.012, e)
    return PLATES["step"] * up + PLATES["imb"] * fr * up


def ridge_lift(f, s):
    """(leatherback) how far its ridges stand up, `f` the share of the half width out from the middle."""
    if not RIDGES:
        return 0.0
    fade = smooth(0.0, 0.12, s) * (1.0 - 0.6 * smooth(0.7, 0.93, s)) * (1.0 - smooth(0.93, 1.0, s))
    up = 0.0
    for at in RIDGES["at"]:
        up += math.exp(-((f - at) / RIDGES["wide"]) ** 2)
    up += 0.8 * math.exp(-((f - 1.0) / (RIDGES["wide"] * 0.6)) ** 2)
    return RIDGES["high"] * up * fade


def section(s, cols):
    """One ring of the shell, down its left side from the middle of the carapace round the rim to the middle of the
    plastron: [(x, y, kind, carapace share f or -1)]. `cols` = (carapace, rim, plastron) points."""
    # (the rear rim's teeth cut only the rim back: the points near it, not the whole ring)
    w = max(W(s), 1e-5)
    cut = min(teeth_cut(s), w * 0.15)
    wplain = w
    top = TOP(s)
    rim = RIM(s)
    under = UNDER(s)
    th = T["th"] * L * (0.35 + 0.65 * smooth(0.0, 0.05, s) * (1.0 - smooth(0.95, 1.0, s)))
    nc, nr, np_ = cols
    out = []
    fs = []
    for i in range(nc + 1):
        fs.append(math.sin(0.5 * math.pi * i / nc) ** 1.1)
    if RIDGES and nc < 20:
        # (the game and low models: a column on each ridge's crest and one either side of it, so the ridges stay)
        fs = [0.0]
        wide = RIDGES["wide"] * 1.3
        for at in RIDGES["at"][1:]:
            fs += [at - wide, at, at + wide] if nc >= 8 else [at]
        fs += [1.0 - wide * 0.8, 1.0] if nc >= 8 else [1.0]
        fs = [f for f in fs if f >= 0.0]
        if nc >= 8:
            fs.insert(1, wide)
    if PLATES and nc >= 10:
        # (columns on the seams: the middle row's edge and the rim plates' inner edge)
        # (the same column in every ring, so that the rings' columns line up; kept between its neighbours)
        base = list(fs)
        for at in (PLATES["vw"], 1.0 - PLATES["mw"] * L / max(W(0.45), 1e-5)):
            k = min(range(1, nc), key=lambda j: abs(base[j] - at))
            want = PLATES["vw"] if at == PLATES["vw"] else 1.0 - PLATES["mw"] * L / wplain
            fs[k] = min(max(want, base[k - 1] + 0.25 * (base[k] - base[k - 1])), base[k + 1] - 0.25 * (base[k + 1] - base[k]))
    dome = T["dome"]
    for f in fs:
        y = rim + top * (1.0 - f * f) ** dome * (1.0 - 0.25 * f * f) / 1.0
        out.append((w * f - cut * smooth(0.75 * w, w, w * f), y, CARAPACE, f))
    # round the rim and under it: a quarter ellipse to the plastron's edge
    wp = T["wp"] * w
    for j in range(1, nr + 1):
        a = 0.5 * math.pi * j / nr
        a0 = 0.5 * math.pi * 0.12
        a = a0 + (0.5 * math.pi - a0) * (j - 1) / max(nr - 1, 1) if nr > 1 else 0.5 * math.pi
        x = wp + (w - th * 0.3 - wp) * math.cos(a)
        x -= cut * smooth(0.75 * w, w, x)
        y = rim - th - (rim - th + under) * math.sin(a)
        out.append((x, y, PLASTRON, -1.0))
    bulge = T["bulge"] * L * smooth(0.0, 0.2, s) * (1.0 - smooth(0.8, 1.0, s))
    for j in range(1, np_ + 1):
        x = wp * (1.0 - j / np_)
        out.append((x, -under - bulge * (1.0 - (x / max(wp, 1e-6)) ** 2), PLASTRON, -1.0))
    return out, w - cut


def shell_rings(low):
    if GAME:
        return game_shell_rings()
    return even_shell_rings(low)


def even_shell_rings(low):
    mid, end = RING_STEP
    if low:
        mid, end = mid * 7.0, end * 5.0
    xs = [0.002]
    while xs[-1] < 0.998:
        s = xs[-1]
        near = min(s, 1.0 - s)
        step = end + (mid - end) * smooth(0.0, 0.08, near)
        xs.append(min(0.998, s + step))
    if not low:
        xs = sorted(set(xs + tooth_rings() + [b for b in (PLATES["vert"] if PLATES else ()) if b < 1.5]))
    return xs


def game_shell_rings():
    """The game model's rings: of the full model's (and the rear rim's teeth), as few as keep its outline from the
    side, above and across within GAME_SHELL_TOL of the full model's, never further apart than GAME_SHELL_STEP."""
    cols = (6, 3, 2)
    # (one ring at each of the rear rim's teeth's points, where the full model has two: the notch behind each point
    # is then a slope across one ring's gap, not a cliff)
    teeth = tooth_rings()[1::2]
    xs = sorted(set(x for x in even_shell_rings(False) if x not in tooth_rings()) | set(teeth))
    hard = set(teeth) | {xs[0], xs[-1]}
    pts = []
    for s in xs:
        sec, _ = section(s, cols)
        pts.append([(x, y) for x, y, _, _ in sec])

    def fits(i, k):
        for m in range(i + 1, k):
            t = (xs[m] - xs[i]) / (xs[k] - xs[i])
            dz = 0.0
            for a in range(len(pts[i])):
                sx = pts[i][a][0] + (pts[k][a][0] - pts[i][a][0]) * t
                sy = pts[i][a][1] + (pts[k][a][1] - pts[i][a][1]) * t
                if math.hypot(sx - pts[m][a][0], sy - pts[m][a][1]) > GAME_SHELL_TOL * (L / 1.1) ** 0.5:
                    return False
        return True

    kept = [0]
    i = 0
    while i < len(xs) - 1:
        j = i + 1
        while j + 1 < len(xs) and xs[j] not in hard:
            k = j + 1
            if (xs[k] - xs[i]) * L > GAME_SHELL_STEP or not fits(i, k):
                break
            j = k
        kept.append(j)
        i = j
    return [xs[k] for k in kept]


def shell(m, low):
    """The shell: one closed skin, the carapace above and the plastron below, a ring for each place along it."""
    cols = SHELL_LO if low else ((SHELL_GAME_BIG if L > 1.5 else SHELL_GAME) if GAME else SHELL_FULL)
    grid = []
    centres = []
    for s in shell_rings(low):
        sec, w = section(s, cols)
        z = -HALF + s * L
        # one side (left, +x) from the carapace's middle to the plastron's; the other side mirrored
        half = len(sec) - 1
        xs = [x for x, _, _, _ in sec]
        es, ps = edge_of(xs, [z] * len(xs))
        row_pts = []
        for i, (x, y, kind, f) in enumerate(sec):
            e = float(es[i])
            p = float(ps[i])
            if kind == CARAPACE:
                y += plate_lift(s, x / L, W(s) / L, e / L, p) * L + ridge_lift(f, s) * L
            row_pts.append((x, y, kind, e, p))
        ids = [None] * (2 * half)
        for i in range(half + 1):
            x, y, kind, e, p = row_pts[i]
            ids[i] = m.add_shell(Vector((x, y, z)), kind, W(s), e, p)
        for i in range(1, half):
            x, y, kind, e, p = row_pts[i]
            ids[2 * half - i] = m.add_shell(Vector((-x, y, z)), kind, W(s), e, p)
        grid.append(ids)
        centres.append(Vector((0.0, 0.5 * (row_pts[0][1] + row_pts[-1][1]), z * 0.6)))
    around = len(grid[0])
    for r in range(len(grid) - 1):
        for c in range(around):
            n = (c + 1) % around
            quad = (grid[r][c], grid[r][n], grid[r + 1][n], grid[r + 1][c])
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, middle - (centres[r] + centres[r + 1]) * 0.5, "shell")
    # the front and the back: a fan each, to a point on the rim
    for row, s, way in ((grid[0], 0.0, -1.0), (grid[-1], 1.0, 1.0)):
        z = -HALF + s * L
        e, p = edge_of([0.0], [z])
        tip = m.add_shell(Vector((0.0, RIM(s), z)), CARAPACE, 0.0, 0.0, float(p[0]))
        for c in range(around):
            m.face((tip, row[c], row[(c + 1) % around]), Vector((0.0, 0.0, way)), "shell")


def shell_surface(s, x):
    """(carapace height, plastron depth) of the plain shell at a place (for putting flippers and the neck)."""
    sec, w = section(s, (40, 12, 8))
    f = min(1.0, abs(x) / w)
    top = RIM(s) + TOP(s) * (1.0 - f * f) ** T["dome"] * (1.0 - 0.25 * f * f)
    return top, -UNDER(s)


# ======================================================================================================
# THE HEAD AND NECK: a tube from the tip of the beak back into the shell, the upper head cut away below the line of
# the mouth; the lower jaw a part of its own (as GameCommon's sea mammals' heads are built). `xm` is metres behind
# the tip of the beak.

def zof(xm):
    return NOSE_Z + xm


def lip(xm):
    """The line of the mouth: how high, `xm` behind the tip of the beak (and the leatherback's two cusps)."""
    at, depth, wide = _CUSP
    return _LIP(xm) - depth * math.exp(-((xm - at) / wide) ** 2)


def sculpt(xm, c):
    return 1.0


def outline(xm):
    xm = max(_XS[0], min(_XS[-1], xm))
    i = 0
    while i < len(_XS) - 2 and xm > _XS[i + 1]:
        i += 1
    h = _XS[i + 1] - _XS[i]
    t = (xm - _XS[i]) / h
    out = []
    for ys, mm in _CURVES:
        a = (2 * t ** 3 - 3 * t ** 2 + 1) * ys[i] + (t ** 3 - 2 * t ** 2 + t) * h * mm[i]
        b = (-2 * t ** 3 + 3 * t ** 2) * ys[i + 1] + (t ** 3 - t ** 2) * h * mm[i + 1]
        out.append(a + b)
    out[3] = max(out[3], 0.0003)
    return out


def full_point(xm, angle):
    top, mid, bot, wide = outline(xm)
    c = math.cos(angle)
    s = math.sin(angle)
    y = mid + c * ((top - mid) if c >= 0.0 else (mid - bot))
    side = math.copysign(abs(s) ** ROUND, s) * wide
    return side * sculpt(xm, c), y


def angle_at(xm, y):
    top, mid, bot, _ = outline(xm)
    if y >= mid:
        c = min(1.0, (y - mid) / max(top - mid, 1e-6))
    else:
        c = -min(1.0, (mid - y) / max(mid - bot, 1e-6))
    return math.acos(c)


def skin(xm, angle):
    side, y = full_point(xm, angle)
    return Vector((side, y, zof(xm)))


def out_of_skin(xm, angle):
    sx = 1.0 if angle >= 0.0 else -1.0
    along = skin(xm + 0.003, angle) - skin(xm - 0.003, angle)
    around = skin(xm, angle + 0.02) - skin(xm, angle - 0.02)
    out = around.cross(along)
    out.normalize()
    here = skin(xm, angle)
    if out.dot(Vector((here.x, here.y - outline(xm)[1], 0.0))) < 0.0:
        out = -out
    if out.length < 0.5:
        out = Vector((sx, 0.0, 0.0))
    return out


def palate_at(xm, share):
    front = smooth(JAW_TIP + JAW_ROUND * 0.5, JAW_TIP + JAW_ROUND * 1.5, xm)
    return PALATE * max(0.0, outline(xm)[0] - lip(xm)) * (1.0 - min(1.0, share) ** 4) * (1.0 - wall(xm)) * front


def trough_at(xm, share):
    return TROUGH * max(0.0, jaw_floor(xm) - outline(xm)[2]) * (1.0 - min(1.0, share) ** 2) ** 2


def jaw_grow(xm):
    return max(0.0, min(1.0, (xm - JAW_TIP) / JAW_ROUND)) ** 0.5


def wall(xm):
    return smooth(CORNER, HINGE_X, xm)


def roof(xm):
    line = lip(xm)
    if xm <= CORNER:
        # (the upper beak's edge comes down a little outside the lower)
        return line - OVERHANG * smooth(JAW_TIP, JAW_TIP + JAW_ROUND, xm) * (1.0 - smooth(CORNER - 0.3 * (HINGE_X - CORNER), CORNER, xm))
    bot = outline(xm)[2]
    return line - wall(xm) * (line - bot)


def jaw_floor(xm):
    return (lip(xm) if xm <= CORNER else roof(xm)) - GAP * (1.0 - wall(xm))


def columns(xm, half, split, cut, even_share):
    even = [math.pi * h / half for h in range(half + 1)]
    if even_share >= 1.0:
        return even
    a = min(max(angle_at(xm, cut), 0.2 * math.pi), 0.985 * math.pi)
    out = []
    for h in range(half + 1):
        mine = a * h / split if h <= split else a + (math.pi - a) * (h - split) / (half - split)
        out.append(mine + (even[h] - mine) * even_share)
    return out


def from_mouth(d):
    """How far from the line of the mouth, as the shader reads it (vertex colour blue on the head and jaw)."""
    return max(0.0, min(1.0, 0.5 + 1.25 * d / HL))


def even_rings(low):
    xs = []
    x = BODY_FROM
    for until, step in HEAD_RINGS:
        until = min(until * HL, BODY_TO)
        step *= HL * (4.0 if low else 1.0)
        n = max(1, round((until - x) / step))
        for i in range(n):
            xs.append(x + (until - x) * i / n)
        x = until
        if x >= BODY_TO:
            break
    xs.append(BODY_TO)
    return xs


def head_rings(low):
    if not GAME:
        return even_rings(low)
    xe, _, radius, _ = EYE_AT
    must = [BODY_FROM, BODY_TO, JAW_TIP, JAW_TIP + JAW_ROUND, CORNER, HINGE_X] + [xe + radius * k for k in (-1.0, -0.5, 0.0, 0.5, 1.0)]
    if _CUSP[1] > 0.0:
        must += [_CUSP[0] - _CUSP[2], _CUSP[0], _CUSP[0] + _CUSP[2]]
    must = [x for x in must + [k * HL for k in GAME_KEEP] if BODY_FROM <= x <= BODY_TO]
    xs = sorted(set(even_rings(False) + must))
    hard = set(must)
    angles = [math.pi * k / 16.0 for k in range(17)]

    def sample(xm):
        out = []
        for a in angles:
            side, y = full_point(xm, a)
            if xm < HINGE_X:
                y = max(y, roof(xm))
            out.append((side, y))
        return out

    points = [sample(x) for x in xs]

    def fits(i, k):
        for m in range(i + 1, k):
            t = (xs[m] - xs[i]) / (xs[k] - xs[i])
            for a in range(len(angles)):
                sx = points[i][a][0] + (points[k][a][0] - points[i][a][0]) * t
                sy = points[i][a][1] + (points[k][a][1] - points[i][a][1]) * t
                if math.hypot(sx - points[m][a][0], sy - points[m][a][1]) > GAME_TOL * HL / 0.165:
                    return False
        return True

    kept = [0]
    i = 0
    while i < len(xs) - 1:
        j = i + 1
        while j + 1 < len(xs) and xs[j] not in hard:
            k = j + 1
            if xs[k] - xs[i] > (GAME_MOUTH_STEP * HL / 0.165 if xs[i] < HINGE_X else GAME_STEP * HL / 0.165) or not fits(i, k):
                break
            j = k
        kept.append(j)
        i = j
    return [xs[k] for k in kept]


def neck_hinge():
    return (0.0, T["head"]["y"] * L, -HALF)


def head(m, low):
    """The skin of the head and neck from the tip of the beak back into the shell, the upper head cut away below the
    line of the mouth: its underside there is the roof of the mouth."""
    m.part(SKIN, HEAD, neck_hinge())
    half = (GAME_AROUND if GAME else (HEAD_AROUND_LO if low else HEAD_AROUND)) // 2
    around = half * 2
    split = round(half * 0.62)
    cols_share = (GAME_AROUND if GAME else (HEAD_AROUND_LO if low else HEAD_AROUND)) / HEAD_AROUND
    grid = []
    cut_away = []
    centre = []
    for xm in head_rings(low):
        mouth = xm < HINGE_X
        cut = roof(xm) if mouth else -1e9
        angles = columns(xm, half, split, cut, wall(xm) if mouth else 1.0)
        front = smooth(JAW_TIP + JAW_ROUND * 0.8, JAW_TIP + JAW_ROUND * 1.8, xm)
        edge = max(abs(full_point(xm, angles[split])[0]), 1e-6)
        row = []
        flags = []
        for c in range(around):
            h = c if c <= half else around - c
            angle = angles[h] if c <= half else -angles[h]
            side, y = full_point(xm, angle)
            inside = 0.0
            gone = False
            if mouth and y <= cut + 1e-7:
                gone = y < cut - 1e-7 or h > split
                y = max(y, cut)
                if xm <= CORNER:
                    inside = min(1.0, max(0.0, (h - split) / (4.0 * cols_share)))
                    y += palate_at(xm, abs(side) / edge)
                else:
                    # (the side of the cut, where the jaw meets the head behind the corner of the mouth, stays skin)
                    inside = 1.0 if gone and abs(side) < 0.75 * edge else 0.0
                inside *= front
            row.append(m.add(Vector((side, y, zof(xm))), inside, from_mouth(y - lip(xm)) if inside < 0.5 else 0.5))
            flags.append(gone)
        grid.append(row)
        cut_away.append(flags)
        top, _, bot, _ = outline(xm)
        centre.append(0.5 * (top + max(bot, cut)))
    for r in range(len(grid) - 1):
        for c in range(around):
            n = (c + 1) % around
            quad = (grid[r][c], grid[r][n], grid[r + 1][n], grid[r + 1][c])
            if cut_away[r][c] and cut_away[r][n] and cut_away[r + 1][n] and cut_away[r + 1][c]:
                m.face(quad, Vector((0.0, -1.0, -1.0)), "mouth")
                continue
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((middle.x, middle.y - 0.5 * (centre[r] + centre[r + 1]), 0.0)), "head")
    first = m.verts[grid[0][0]]
    last = m.verts[grid[-1][0]]
    for row, at, way in ((grid[0], Vector((0.0, centre[0], first.z - 0.001)), -1.0),
                         (grid[-1], Vector((0.0, centre[-1], last.z + 0.002)), 1.0)):
        tip = m.add(at, 0.0, from_mouth(at.y - lip(0.0)) if way < 0.0 else 1.0)
        for c in range(around):
            m.face((tip, row[c], row[(c + 1) % around]), Vector((0.0, 0.0, way)), "head")


def jaw_point(xm, angle, clamp):
    floor = jaw_floor(xm)
    grow = jaw_grow(xm)
    narrow = JAW_WIDE + (1.0 - JAW_WIDE) * smooth(CORNER - 0.4 * (HINGE_X - CORNER), CORNER, xm)
    side, y = full_point(xm, angle)
    if clamp:
        # (the floor of the mouth: straight across from the middle line to the jaw's edge at the height of the floor;
        # behind the corner of the mouth the floor sinks below the head's widest, and the ellipse's upper points
        # would stand out past the skin)
        a = min(max(angle_at(xm, floor), 0.2 * math.pi), 0.985 * math.pi)
        share = min(1.0, abs(angle) / a)
        side = math.copysign(abs(full_point(xm, a)[0]) * share, angle if angle != 0.0 else 1.0)
        y = floor - trough_at(xm, share)
    y = floor - (floor - min(y, floor)) * grow
    return Vector((side * narrow * grow, y, zof(xm)))


def jaw(m, low):
    """The lower jaw: a part of its own from its tip back to its hinge; the shader swings it down (and moves it with
    the head). Its top is the floor of the mouth."""
    m.part(SKIN, JAW, (0.0, HINGE_Y, zof(HINGE_X)))
    base = GAME_AROUND if GAME else (HEAD_AROUND_LO if low else HEAD_AROUND)
    half = max(6, base // 4)
    around = half * 2
    split = max(2, round(half * 0.3))
    cols_share = base / HEAD_AROUND
    n = GAME_JAW if GAME else (8 if low else 40)
    grid = []
    centre = []
    xs = [JAW_TIP + (HINGE_X - JAW_TIP) * (i / n) ** 1.35 for i in range(1, n + 1)]
    if GAME and _CUSP[1] > 0.0:
        xs = sorted(set(xs + [_CUSP[0] - _CUSP[2], _CUSP[0], _CUSP[0] + _CUSP[2]]))
        xs = [x for x in xs if x > JAW_TIP]
    for xm in xs:
        floor = jaw_floor(xm)
        angles = columns(xm, half, split, floor, 0.0)
        row = []
        for c in range(around):
            h = c if c <= half else around - c
            angle = angles[h] if c <= half else -angles[h]
            inside = min(1.0, max(0.0, (split - h) / (4.0 * cols_share)))
            if xm > CORNER:
                inside = 1.0 if h < split - 1 else 0.0
            p = jaw_point(xm, angle, h <= split)
            row.append(m.add(p, inside, from_mouth(lip(xm) - p.y) if inside < 0.5 else 0.5))
        grid.append(row)
        centre.append(0.5 * (floor + m.verts[row[half]].y))
    for r in range(len(grid) - 1):
        for c in range(around):
            n2 = (c + 1) % around
            hs = [q if q <= half else around - q for q in (c, n2)]
            quad = (grid[r][c], grid[r][n2], grid[r + 1][n2], grid[r + 1][c])
            if max(hs) <= split:
                m.face(quad, Y, "jaw floor")
                continue
            middle = sum((m.verts[q] for q in quad), Vector()) * 0.25
            m.face(quad, Vector((middle.x, middle.y - 0.5 * (centre[r] + centre[r + 1]), 0.0)), "jaw")
    tip = m.add(Vector((0.0, lip(JAW_TIP) - GAP, zof(JAW_TIP))), 0.0, 0.5)
    for c in range(around):
        m.face((tip, grid[0][c], grid[0][(c + 1) % around]), Vector((0.0, -0.3, -1.0)), "jaw")


def blob(m, centre, ax, ay, az, name, around=14, rows=8, along=None):
    def point(p):
        return m.add(p, 0.0, along(p) if along else 0.0)
    north = point(centre + az)
    south = point(centre - az)
    grid = []
    for r in range(1, rows):
        lat = math.pi * r / rows
        row = []
        for s in range(around):
            lon = s / around * TAU
            row.append(point(centre + az * math.cos(lat) + (ax * math.cos(lon) + ay * math.sin(lon)) * math.sin(lat)))
        grid.append(row)

    def out(points):
        middle = sum((m.verts[q] for q in points), Vector()) / len(points) - centre
        return Vector([sum(middle.dot(axis) / axis.length_squared * axis[k] / axis.length_squared for axis in (ax, ay, az)) for k in range(3)])

    for s in range(around):
        n = (s + 1) % around
        m.face((north, grid[0][s], grid[0][n]), out((north, grid[0][s], grid[0][n])), name)
        m.face((south, grid[-1][s], grid[-1][n]), out((south, grid[-1][s], grid[-1][n])), name)
        for r in range(len(grid) - 1):
            quad = (grid[r][s], grid[r][n], grid[r + 1][n], grid[r + 1][s])
            m.face(quad, out(quad), name)


def tongue(m, low):
    m.part(TONGUE, JAW, (0.0, HINGE_Y, zof(HINGE_X)))
    front, back, thick = TONGUE_AT
    middle = 0.5 * (front + back)
    floor = lip(middle) - GAP - trough_at(middle, 0.0) * 0.8
    wide = abs(full_point(middle, angle_at(middle, lip(middle)))[0]) * JAW_WIDE * 0.5
    blob(m, Vector((0.0, floor - thick * 0.3, zof(middle))), X * wide, Y * thick,
         Vector((0.0, 0.5 * (lip(front) - lip(back)), -0.5 * (back - front))), "tongue",
         8 if GAME else (8 if low else 16), 4 if GAME else (4 if low else 8))


def eye(m, sx, low):
    """A dome lying on the skin of the head."""
    m.part(EYE, HEAD, neck_hinge())
    spokes, steps = GAME_EYE if GAME else ((12, 2) if low else (36, 8))
    xe, degrees, radius, bulge = EYE_AT
    angle = math.radians(degrees)
    here = skin(xe, sx * angle)
    round_here = max(0.01, Vector((here.x, here.y - outline(xe)[1])).length)

    def on_skin(dx, dy):
        return skin(xe + dx, sx * (angle - dy / round_here))

    out = out_of_skin(xe, sx * angle)
    if sx > 0.0 and not low and not GAME:
        ahead = (-Z - out * out.dot(-Z)).normalized()
        up = out.cross(ahead) if out.cross(ahead).y > 0.0 else ahead.cross(out)
        print("EYE %s middle Vector3(%.4f, %.4f, %.4f) out Vector3(%.4f, %.4f, %.4f) ahead Vector3(%.4f, %.4f, %.4f) up Vector3(%.4f, %.4f, %.4f) radius %.4f sag %.5f" % (
            CURRENT, here.x, here.y, here.z, out.x, out.y, out.z, ahead.x, ahead.y, ahead.z, up.x, up.y, up.z, radius,
            radius * radius / (2.0 * round_here)))
    middle = m.add(here + out * (bulge + 0.0006), 0.0, 0.0)
    last = None
    for k in range(1, steps + 1):
        r = k / steps
        row = []
        for s in range(spokes):
            a = s / spokes * TAU
            p = on_skin(math.cos(a) * radius * r, math.sin(a) * radius * r)
            row.append(m.add(p + out * (bulge * (1.0 - r * r) + 0.0006 * (1.0 - r)), 0.0, r))
        for s in range(spokes):
            n = (s + 1) % spokes
            if last is None:
                m.face((middle, row[s], row[n]), out, "eyes")
            else:
                m.face((last[s], row[s], row[n], last[n]), out, "eyes")
        last = row


# ======================================================================================================
# THE FLIPPERS

def blade(m, name, point, place, facing, thick, nt, nu, edge=0.0, tip=0.0, ts=None):
    """A flipper: a closed blade. `point(t, u)` is a place in its own flat (t 0 at its root to 1 at its tip, u 0 at
    its leading edge to 1 at its trailing edge), `place` puts that in the model, `facing` is the way one of its two
    skins faces. It is `thick` at its root (left open: bury it), a foil across, thinning to `tip` of that at its tip.
    The two skins share their points round the edges. `ts` gives the rows' places along it (else even)."""
    ts = ts or [ti / nt for ti in range(nt + 1)]
    nt = len(ts) - 1
    grids = []
    for side in (1.0, -1.0):
        grid = []
        for ti, t in enumerate(ts):
            row = []
            for ui in range(nu + 1):
                u = ui / nu
                foil = edge + (1.0 - edge) * 2.6 * math.sqrt(u) * (1.0 - u)
                if edge > 0.0:
                    foil *= math.sqrt(max(0.0, 1.0 - (2.0 * u - 1.0) ** 6))
                swell = thick * (tip + (1.0 - tip) * (1.0 - t) ** 0.7) * foil * math.sqrt(max(0.0, 1.0 - t ** 10))
                if side < 0.0 and swell < 1e-9:
                    row.append(grids[0][ti][ui])
                else:
                    row.append(m.add(place(point(t, u)) + facing * (side * swell * 0.5), 0.0, t))
            grid.append(row)
        grids.append(grid)
        for ti in range(nt):
            for ui in range(nu):
                a, b, c, d = grid[ti][ui], grid[ti][ui + 1], grid[ti + 1][ui + 1], grid[ti + 1][ui]
                if ti == nt - 1 and ui == 0:
                    m.face((a, b, d), facing * side, name)
                    m.face((b, c, d), facing * side, name)
                elif ti == nt - 1 and ui == nu - 1:
                    m.face((a, b, c), facing * side, name)
                    m.face((a, c, d), facing * side, name)
                else:
                    m.face((a, b, c, d), facing * side, name)


def claw(m, base, tip, radius, along, sides, rows):
    """A claw on a flipper's leading edge: round at `base` (bury it), coming to `tip`; it moves as its flipper does
    at `along`."""
    axis = tip - base
    way = axis.normalized()
    a = way.orthogonal().normalized()
    b = way.cross(a)
    last = None
    for r in range(rows):
        t = r / rows
        ring = [m.add(base + axis * t + (a * math.cos(s / sides * TAU) + b * math.sin(s / sides * TAU)) * radius * (1.0 - t) ** 0.8, 0.0, along)
                for s in range(sides)]
        if last:
            for s in range(sides):
                n = (s + 1) % sides
                middle = (m.verts[last[s]] + m.verts[ring[n]]) * 0.5
                m.face((last[s], last[n], ring[n], ring[s]), middle - (base + axis * (t - 0.5 / rows)), "claws")
        last = ring
    end = m.add(tip, 0.0, along)
    for s in range(sides):
        n = (s + 1) % sides
        middle = (m.verts[last[s]] + m.verts[last[n]]) * 0.5
        m.face((last[s], last[n], end), middle - (base + axis * (1.0 - 1.0 / rows)), "claws")


def fore_frame(sx):
    """(root, the way it runs out, the way back across it, the way its upper skin faces) of a fore flipper, its left
    one for sx 1 (as the shader has it: the way it runs out, `fore_span`)."""
    f = T["fore"]
    s = f["s"]
    w = W(s)
    top, bot = shell_surface(s, w * f["xin"])
    root = Vector((sx * w * f["xin"], f["y"] * L, -HALF + s * L))
    span = Vector((sx * 1.0, -f["droop"], f["back"])).normalized()
    chord = (Z - span * span.dot(Z)).normalized()
    facing = span.cross(chord).normalized()
    if facing.y < 0.0:
        facing = -facing
    return root, span, chord, facing


def hind_frame(sx):
    h = T["hind"]
    s = h["s"]
    w = W(s)
    root = Vector((sx * w * h["xin"], h["y"] * L, -HALF + s * L))
    span = Vector((sx * h["out"], -0.08, 1.0)).normalized()
    chord = (Vector((sx, 0.0, 0.0)) - span * span.x * sx).normalized()
    facing = span.cross(chord).normalized()
    if facing.y < 0.0:
        facing = -facing
    return root, span, chord, facing


def flippers(m, low):
    f = T["fore"]
    h = T["hind"]
    for sx in (1.0, -1.0):
        # The fore flippers: long and narrow, curved back, the leading edge thick and the tip pointed.
        root, span, chord, facing = fore_frame(sx)
        lf = f["length"] * L
        cf = f["chord"] * L
        sweep = f["sweep"]

        def fore_point(t, u, lf=lf, cf=cf, sweep=sweep):
            back = lf * sweep * t * t
            wide = cf * (0.55 + 0.45 * math.sin(math.pi * min(1.0, t * 1.25)) ** 0.8) * math.sqrt(max(0.0, 1.0 - t ** 3))
            if t > 0.75:
                wide *= 1.0 - 0.15 * smooth(0.75, 1.0, t)
            lead = back - 0.38 * wide
            return (t * lf, lead + wide * u)

        m.part(FLIPPER, FORE_L if sx > 0.0 else FORE_R, root)
        if GAME:
            ts = [0.0, 0.18, 0.34, 0.48, 0.6, 0.71, 0.8, 0.88, 0.95, 1.0]
            nu = 4
        elif low:
            ts, nu = [0.0, 0.25, 0.5, 0.72, 0.88, 1.0], 3
        else:
            ts, nu = [k / 44 for k in range(45)], 12
        blade(m, "fore flippers", fore_point, lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.06 * L, 0, nu, edge=0.25, tip=0.18, ts=ts)
        # claws on the leading edge
        if not low:
            m.part(CLAW, FORE_L if sx > 0.0 else FORE_R, root)
            for t in f["claws"]:
                p = fore_point(t, 0.02)
                base = root + span * p[0] + chord * (p[1] + 0.004 * L)
                tip = base + (span * 0.8 - chord * 0.6).normalized() * 0.035 * L
                claw(m, base, tip, 0.006 * L, t, 4 if GAME else 7, 1 if GAME else 3)
        # The hind flippers: broad rounded paddles trailing behind, under the back of the shell.
        root, span, chord, facing = hind_frame(sx)
        lh = h["length"] * L
        ch = h["chord"] * L

        def hind_point(t, u, lh=lh, ch=ch):
            wide = ch * (0.5 + 0.5 * math.sin(math.pi * min(1.0, t * 1.1)) ** 0.7) * math.sqrt(max(0.0, 1.0 - t ** 4))
            return (t * lh, (u - 0.45) * wide)

        m.part(FLIPPER, HIND_L if sx > 0.0 else HIND_R, root)
        if GAME:
            ts, nu = [0.0, 0.3, 0.55, 0.75, 0.9, 1.0], 4
        elif low:
            ts, nu = [0.0, 0.4, 0.75, 1.0], 3
        else:
            ts, nu = [k / 22 for k in range(23)], 12
        blade(m, "hind flippers", hind_point, lambda p, root=root, span=span, chord=chord: root + span * p[0] + chord * p[1],
              facing, 0.045 * L, 0, nu, edge=0.25, tip=0.2, ts=ts)


# ======================================================================================================

CURRENT = ""


def make(name, low):
    m = Mesh()
    shell(m, low)
    head(m, low)
    jaw(m, low)
    tongue(m, low)
    for sx in (1.0, -1.0):
        eye(m, sx, low)
    flippers(m, low)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata([to_b(p) for p in m.verts], [], m.faces)
    mesh.uv_layers.new(name="UVMap")
    mesh.uv_layers.new(name="UV2")
    mesh.color_attributes.new(name="Color", type="FLOAT_COLOR", domain="CORNER")
    uv = mesh.uv_layers["UVMap"].data
    uv2 = mesh.uv_layers["UV2"].data
    colour = mesh.color_attributes["Color"].data
    for poly in mesh.polygons:
        for corner, vi in enumerate(poly.vertices):
            u, v, u2, group, r, g, b = m.data[vi]
            uv[poly.loop_start + corner].uv = (u, 1.0 - v)
            uv2[poly.loop_start + corner].uv = (u2, 1.0 - group / 8.0)
            colour[poly.loop_start + corner].color = (r, g, b, 1.0)
    mesh.color_attributes.active_color = mesh.color_attributes["Color"]
    mesh.color_attributes.render_color_index = mesh.color_attributes.find("Color")
    material = bpy.data.materials.get(NAME) or bpy.data.materials.new(NAME)
    material.use_nodes = True
    bsdf = next(n for n in material.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = COLOUR
    material.diffuse_color = COLOUR
    mesh.materials.append(material)
    for poly in mesh.polygons:
        poly.use_smooth = True
    mesh.set_sharp_from_angle(angle=math.radians(50.0))
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    tris = sum(len(p.vertices) - 2 for p in mesh.polygons)
    box = [(min(p[k] for p in m.verts), max(p[k] for p in m.verts)) for k in range(3)]
    print("BUILT %s verts=%d tris=%d x %.3f..%.3f y %.3f..%.3f z %.3f..%.3f" % (
        name, len(mesh.vertices), tris, box[0][0], box[0][1], box[1][0], box[1][1], box[2][0], box[2][1]))
    winding(name, mesh, m)
    return obj


def winding(name, mesh, m):
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
        export_animations=False, export_vertex_color="ACTIVE", export_texcoords=True,
    )


def render(folder, kind, made):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_cavity = True
    scene.display.shading.show_backface_culling = True
    scene.render.resolution_x, scene.render.resolution_y = 1000, 700
    if scene.world is None:
        scene.world = bpy.data.worlds.new("World")
    scene.world.color = (0.02, 0.05, 0.3)
    camera = scene.camera
    if camera is None:
        camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
        camera.data.type = "ORTHO"
        camera.data.clip_end = 1000.0
        scene.collection.objects.link(camera)
        scene.camera = camera
    long = (L + HL * 2.5) * 1.15
    nose = -NOSE_Z
    views = [("left", (1, 0, 0), (0, 0, 0), long), ("front", (0, 1, 0), (0, 0, 0), long * 0.8),
             ("back", (0, -1, 0), (0, 0, 0), long * 0.8), ("top", (0.001, 0, 1), (0, 0, 0), long * 1.1),
             ("under", (0.001, 0, -1), (0, 0, 0), long * 1.1),
             ("head", (0.8, 0.5, 0.25), (0, nose - HL * 0.6, 0), HL * 2.6),
             ("quarter", (0.8, 0.8, 0.5), (0, 0, 0), long * 1.0)]
    for label, obj in made:
        for _, other in made:
            other.hide_render = other is not obj
        for view, direction, target, frame in views:
            if label != "full" and view not in ("left", "top", "head", "quarter"):
                continue
            offset = Vector(direction).normalized() * 40.0
            camera.data.ortho_scale = frame
            camera.location = Vector(target) + offset
            camera.rotation_euler = (-offset).to_track_quat("-Z", "Y" if abs(direction[2]) < 0.9 else "X").to_euler()
            scene.render.filepath = os.path.join(folder, "%s_%s_%s.png" % (kind, label, view))
            bpy.ops.render.render(write_still=True)


def main():
    global GAME, CURRENT
    for kind in ORDER:
        if ONLY and kind not in ONLY:
            continue
        CURRENT = kind
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.preferences.filepaths.save_version = 0
        use(kind)
        name = "%s_%s" % (NAME, kind)
        # (what the shader is given for this type: sea_turtle.gd's TYPES)
        _, span, _, _ = fore_frame(1.0)
        print('SHADER %s "shell_length": %.3f, "nose_z": %.4f, "head_length": %.4f, "neck_front": %.4f, "neck_back": %.4f, '
              '"neck_pivot": Vector3(0.0, %.4f, %.4f), "tuck_back": %.4f, "mouth_corner": %.4f, '
              '"fore_span": Vector3(%.4f, %.4f, %.4f), "rim_len": %.4f, "corner_hl": %.3f' % (
                  kind, L, NOSE_Z, HL, zof(1.0 * HL), -HALF + 0.08 * L, neck_hinge()[1], neck_hinge()[2], 0.42 * HL,
                  zof(CORNER), span.x, span.y, span.z, rim_length() / L, CORNER / HL))
        full = make(name, False)
        low = make(name + "_lo", True)
        GAME = True
        game = make(name + "_game", False)
        GAME = False
        os.makedirs(OUT, exist_ok=True)
        export_one(full, os.path.join(OUT, name + ".glb"))
        export_one(low, os.path.join(OUT, name + "_lo.glb"))
        export_one(game, os.path.join(OUT, name + "_game.glb"))
        low.location.x = L * 1.5
        game.location.x = L * 3.0
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, name + ".blend"))
        low.location.x = 0.0
        game.location.x = 0.0
        if PREVIEW:
            os.makedirs(PREVIEW, exist_ok=True)
            render(PREVIEW, kind, [("full", full), ("game", game), ("lo", low)])


if __name__ == "__main__":
    main()
