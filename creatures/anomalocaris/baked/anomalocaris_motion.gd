extends RefCounted
## The anomalocaris's motion in the jointed family (scripts/motion.gd; GameCommon
## `godot/motion-families`), as anomalocaris.gdshader moved it: the side lobes flapping in a wave from
## front to back (`flap`), the tail fan's blades nodding one after another, the body's gentle wave up and
## down behind the head, the two frontal arms curling segment by segment (`grasp`, with a small idle
## curl), the cartoon eyes grown. Numbers from anomalocaris.gdshader.
##
## Differs: the arms' idle curl was `0.04 * sway * sin(...) * (1 - grasp)`, clamped; here it does not
## fade out as the arms grasp (a few hundredths of a radian more at full grasp). The old shader also
## tipped the normals with the body's wave; the family does not.

const FAMILY := "jointed"

const BOX_MIN := Vector3(-0.25, -0.2, -0.45)
const BOX_MAX := Vector3(0.25, 0.2, 0.45)
const ARM_P := [Vector2(-0.02, -0.352), Vector2(-0.04825, -0.36702), Vector2(-0.0702, -0.36549), Vector2(-0.08786, -0.3561),
	Vector2(-0.09925, -0.34152), Vector2(-0.10336, -0.32503), Vector2(-0.10058, -0.30927), Vector2(-0.0922, -0.29683),
	Vector2(-0.08032, -0.28941), Vector2(-0.06745, -0.28761), Vector2(-0.05591, -0.29091), Vector2(-0.04749, -0.29798),
	Vector2(-0.0431, -0.30697)]
const ARM_D := [0.97738, 0.48869, 0.38397, 0.38397, 0.38397, 0.38397, 0.38397, 0.36652, 0.34907, 0.31416, 0.24435, 0.13963, 0.03491]
const EYE_GROW := 1.5

const LOBE := 1
const FAN := 2
const EYE := 8
# The arms' segments: part ARM + n for a point on segment n (0..12).
const ARM := 10


static func numbers(_old: Callable) -> Dictionary:
	var ops: Array = [
		{"type": "turn", "parts": [LOBE], "drive": "flap", "c": 0.08, "a": 0.42, "lag": 1, "per_lag": -0.58,
			"flags": ["own_point", "by_side"], "way": Vector3.BACK},
		{"type": "turn", "parts": [FAN], "drive": "sway", "a": 0.1, "off": -2.2, "lag": 1, "per_lag": -0.3,
			"flags": ["own_point"], "way": Vector3.RIGHT},
	]
	# (each arm hinge from the tip in: turning every segment from it out)
	for i in range(12, -1, -1):
		var parts: Array = []
		for seg in range(i, 13):
			parts.append(ARM + seg)
		ops.append({"type": "turn", "parts": parts, "drive": "sway", "a": 0.04 * ARM_D[i], "off": 1.0,
			"plus": ARM_D[i], "drive3": "grasp", "at": Vector3(0.0, ARM_P[i].x, ARM_P[i].y), "way": Vector3.RIGHT})
	ops.append({"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["own_point"],
		"k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0})
	ops.append({"type": "move", "drive": "sway", "a": 0.007, "w": 2, "lag": 3, "per_lag": -13.0, "way": Vector3.UP,
		"flags": ["after"]})
	return {"ops": ops}


static func label(p: Vector3, _n: Vector3, _uv: Vector2, uv2: Vector2, colour: Color, _old: Callable) -> Dictionary:
	var code := floorf(uv2.y + 0.5)
	var part := int(floorf((code + 0.5) / 16.0))
	var index := code - float(part) * 16.0
	var joint := BOX_MIN + (BOX_MAX - BOX_MIN) * Vector3(colour.r, colour.g, colour.b)
	var wave := [index, smoothstep(-0.3, 0.35, p.z), p.z]
	if part == 4 or part == 5:
		return {"part": ARM + clampi(int(index + 0.5), 0, 12), "w": wave}
	if part == 3:
		return {"part": EYE if colour.a > 0.5 else 3, "point": joint, "w": wave}
	return {"part": part, "point": joint, "w": wave}
