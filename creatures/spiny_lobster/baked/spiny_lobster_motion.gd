extends RefCounted
## The spiny lobster's motion in the jointed family (scripts/motion.gd; GameCommon
## `godot/motion-families`), as spiny_lobster.gdshader moved it: each walking leg's foot on its stride
## (back along the ground, lifted forward through the air; the legs of a side one after another, the
## two sides half a stride apart) and the leg bent at its joint and knee to reach it; the antennae
## feeling about (`feel`), swung side to side and nodding about their roots; the cartoon eyes grown.
## Numbers from spiny_lobster.gdshader.

const FAMILY := "jointed"

const BOX_MIN := Vector3(-0.1, 0.0, -0.3)
const BOX_MAX := Vector3(0.1, 0.2, 0.3)
const KNEE_AT := 0.42
const ON_GROUND := 0.65
const STRIDE := 0.05
const LIFT := 0.025
const EYE_MIDDLE := Vector3(0.03, 0.136, -0.289)
const EYE_GROW := 1.45

# Our parts (the model's: 1 legs, 2 eyes and stalks, 3 antennae).
const LEG := 1
const EYE := 2
const FEELER := 3


static func numbers(_old: Callable) -> Dictionary:
	return {
		"ops": [
			{"type": "leg", "parts": [LEG], "drive": "walk", "w": 1, "lag": 2, "per_lag": TAU,
				"way": Vector3.FORWARD, "k1": STRIDE, "k2": LIFT, "knee_at": KNEE_AT, "ground": ON_GROUND},
			# the antennae: a nod about x, then a swing about up, both about their roots
			{"type": "turn", "parts": [FEELER], "drive": "feel", "a": 0.4, "off": 0.4 * PI, "w": 3,
				"flags": ["own_point"], "way": Vector3.RIGHT},
			{"type": "turn", "parts": [FEELER], "drive": "feel", "a": 1.0, "w": 3, "lag": 4, "per_lag": -0.5 * PI,
				"flags": ["own_point", "by_side"], "way": Vector3.UP},
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": EYE_MIDDLE, "k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0},
		],
	}


static func label(_p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, colour: Color, _old: Callable) -> Dictionary:
	var code := floorf(uv2.y + 0.5)
	var part := int(floorf((code + 0.5) / 16.0))
	var index := code - float(part) * 16.0
	var along := colour.a
	var knee := Vector3(uv.x, uv.y, uv2.x)
	var joint := BOX_MIN + (BOX_MAX - BOX_MIN) * Vector3(colour.r, colour.g, colour.b)
	var flip := 0.0 if joint.x >= 0.0 else 0.5
	if part == 1:
		return {"part": LEG, "w": [along, -0.2 * index + flip], "point": joint, "way": knee}
	if part == 3:
		var amount := along * (1.0 if index < 0.5 else 0.5)
		return {"part": FEELER, "w": [0.0, 0.0, amount, along], "point": joint}
	if part == 2 and along > 0.5:
		return {"part": EYE}
	return {"part": 0}
