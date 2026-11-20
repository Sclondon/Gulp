extends RefCounted
## The rock crab's motion in the jointed family (scripts/motion.gd; GameCommon
## `godot/motion-families`), as rock_crab.gdshader moved it: each leg's foot on its stride (back along
## the ground, lifted forward through the air, the legs of a side alternating) and the leg bent at its
## joint and knee to reach it; the claws raised and opened (`claws`); the body's bob as it walks; the
## cartoon eyes grown. Numbers from rock_crab.gdshader; the claw's raising axis measured from the model.

const FAMILY := "jointed"

const BOX_MIN := Vector3(-0.1, 0.0, -0.1)
const BOX_MAX := Vector3(0.1, 0.1, 0.1)
const KNEE_AT := 0.62
const FINGER_AXIS := Vector3(-0.361, 0.0, 0.933)
const ON_GROUND := 0.6
const STRIDE := 0.026
const LIFT := 0.012
const EYE_MIDDLE := Vector3(0.0178, 0.0412, -0.0497)
const EYE_GROW := 1.8
# (across the claw's reach, flat: from its shoulder (0.0514, 0.0208, -0.0318) to its hinge (0.0334, 0.0249, -0.0677))
const RAISE_AXIS := Vector3(0.894, 0.0, -0.448)

# Our parts.
const LEG := 1
const CLAW := 2
const FINGER := 3
const EYE := 4


static func numbers(_old: Callable) -> Dictionary:
	return {
		"ops": [
			{"type": "leg", "parts": [LEG], "drive": "walk", "w": 1, "lag": 2, "per_lag": TAU,
				"way": Vector3.RIGHT, "k1": STRIDE, "k2": LIFT, "knee_at": KNEE_AT, "ground": ON_GROUND},
			{"type": "turn", "parts": [FINGER], "drive": "claws", "c": -0.75, "flags": ["mirror", "way_point"], "way": FINGER_AXIS},
			{"type": "turn", "parts": [CLAW, FINGER], "drive": "claws", "c": 0.8, "flags": ["mirror", "own_point"], "way": RAISE_AXIS},
			{"type": "turn", "parts": [CLAW, FINGER], "drive": "claws", "c": -0.7, "flags": ["mirror", "own_point"], "way": Vector3.UP},
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": EYE_MIDDLE, "k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0},
			# the bob: 0.0012 * |walk| * (0.5 - 0.5 cos(2 beats))
			{"type": "move", "drive": "walk", "c": 0.0006, "a": -0.0006, "beats": 2.0, "off": 0.5 * PI,
				"way": Vector3.UP, "flags": ["abs", "after"]},
		],
	}


static func label(_p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, colour: Color, _old: Callable) -> Dictionary:
	var code := floorf(uv2.y + 0.5)
	var part := floorf((code + 0.5) / 16.0)
	var index := code - part * 16.0
	var along := colour.a
	var knee := Vector3(uv.x, uv.y, uv2.x)
	var joint := BOX_MIN + (BOX_MAX - BOX_MIN) * Vector3(colour.r, colour.g, colour.b)
	if part > 0.5 and part < 1.5:
		var flip := 0.0 if joint.x >= 0.0 else 1.0
		return {"part": LEG, "w": [along, 0.5 * fmod(index + flip, 2.0) + 0.06 * index], "point": joint, "way": knee}
	if part > 1.5 and part < 2.5:
		return {"part": FINGER if index > 1.5 else CLAW, "point": joint, "way": knee}
	if part > 2.5 and along > 0.5:
		return {"part": EYE}
	return {"part": 0}
