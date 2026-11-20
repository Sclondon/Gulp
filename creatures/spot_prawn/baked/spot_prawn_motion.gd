extends RefCounted
## The spot prawn's motion in the jointed family (scripts/motion.gd; GameCommon
## `godot/motion-families`), as spot_prawn.gdshader moved it: the walking legs on their strides (bent at
## joint and knee to reach each foot), the swimmerets paddling (`paddle`), the antennae swinging
## (`feel`), the tail flicked under in a curl (`flick`), the cartoon eyes grown. Numbers from
## spot_prawn.gdshader. The old curl bent only CURL_LENGTH of the tail and carried the rest straight on;
## the family's bend curls the whole tail beyond its start, so the tail fan curls a little further.

const FAMILY := "jointed"

const BOX_MIN := Vector3(-0.03, 0.0, -0.1)
const BOX_MAX := Vector3(0.03, 0.06, 0.1)
const KNEE_AT := 0.45
const ON_GROUND := 0.65
const STRIDE := 0.009
const LIFT := 0.005
const CURL_FROM := -0.004
const CURL_Y := 0.0318
const CURL_LENGTH := 0.072
const CURL_MAX := 2.7
const EYE_MIDDLE := Vector3(0.0093, 0.0375, -0.0623)
const EYE_GROW := 1.7

# Our parts: the model's (1 legs, 2 swimmerets, 3 eyes, 4 antennae; 0 and 6 curl with the body) and
# 5 for the antennae that do not swing.
const BODY := 0
const LEG := 1
const PADDLE := 2
const EYE := 3
const FEELER := 4
const STILL := 5
const FAN := 6


static func numbers(_old: Callable) -> Dictionary:
	return {
		"ops": [
			{"type": "leg", "parts": [LEG], "drive": "walk", "w": 1, "lag": 2, "per_lag": TAU,
				"way": Vector3.FORWARD, "k1": STRIDE, "k2": LIFT, "knee_at": KNEE_AT, "ground": ON_GROUND},
			{"type": "turn", "parts": [PADDLE], "drive": "paddle", "c": 0.15, "a": 0.55, "lag": 2, "per_lag": 0.4 * PI,
				"flags": ["own_point"], "way": Vector3.RIGHT},
			{"type": "turn", "parts": [FEELER], "drive": "feel", "a": 1.0, "w": 1, "lag": 1, "per_lag": -0.6 * PI,
				"flags": ["own_point", "by_side"], "way": Vector3.UP},
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": EYE_MIDDLE, "k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0},
			# the tail curled under: down and forward about a line CURL_Y up
			{"type": "bend", "parts": [BODY, PADDLE, FAN], "drive": "flick", "c": -CURL_MAX, "flags": ["bend_up", "ends"],
				"at": Vector3(0.0, CURL_Y, 0.0), "way": Vector3.BACK, "k1": CURL_FROM, "k2": CURL_LENGTH},
		],
	}


static func label(_p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, colour: Color, _old: Callable) -> Dictionary:
	var code := floorf(uv2.y + 0.5)
	var part := int(floorf((code + 0.5) / 16.0))
	var index := code - float(part) * 16.0
	var along := colour.a
	var knee := Vector3(uv.x, uv.y, uv2.x)
	var joint := BOX_MIN + (BOX_MAX - BOX_MIN) * Vector3(colour.r, colour.g, colour.b)
	if part == LEG:
		return {"part": LEG, "w": [along, -0.2 * index + (0.0 if joint.x >= 0.0 else 0.5)], "point": joint, "way": knee}
	if part == PADDLE:
		return {"part": PADDLE, "w": [0.0, index], "point": joint}
	if part == FEELER:
		return {"part": FEELER if index < 0.5 else STILL, "w": [along], "point": joint}
	if part == EYE:
		return {"part": EYE if along > 0.5 else STILL}
	if part == FAN:
		return {"part": FAN}
	if part == BODY:
		return {"part": BODY}
	return {"part": STILL}
