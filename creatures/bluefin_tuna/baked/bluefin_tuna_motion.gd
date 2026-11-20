extends RefCounted
## The bluefin tuna's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`),
## as bluefin_tuna.gdshader moved it (which works in a 1.5 m frame, U = LENGTH / 1.5, and scales back): the
## wave back along the body, the tail one plate behind its wrist, the turning curl, the first dorsal
## folding down into its groove (`first_dorsal`), the cartoon eye grown about its middle, the gill
## arches spreading, the lower jaw swinging down and the snout lifting ahead of the hinge. The eye's
## inner half grew by the square of its growth in the old shader; here by the growth, as the rest.

const FAMILY := "swim"

const LENGTH := 2.5
const U := LENGTH / 1.5
const HALF := 0.75
const JOINT := 1.335
const HINGE := 0.14
const HINGE_Y := -0.0536
const SOFT := 0.4
const JAW_DROP := 0.62
const SNOUT_LIFT := 0.06
const EYE_MID := Vector3(0.08427, 0.026, -0.598)
const EYE_OUT := Vector3(0.91521, 0.1723, -0.36428)
const EYE_GROW := 1.5

# Parts (the model's UV2.y): 1 the first dorsal, 7 an eye, 8 a gill arch; ours: the lower jaw.
const DORSAL := 1
const EYE := 7
const GILL := 8
const JAW := 20


static func numbers(_old: Callable) -> Dictionary:
	var k := 1.5 / JOINT
	var not_jaw: Array = range(24)
	not_jaw.erase(JAW)
	return {
		"motion_length": LENGTH, "motion_nose": -HALF * U,
		"env_poly": Vector4(0.012, -0.03 * k, 0.03 * k * k, 0.0) * 0.7,
		"env_pow": Vector3(0.085 * pow(k, 4.0) * 0.7, 0.0, 4.0),
		"swim_wave_scale": 1.0 / k,
		"swim_from": -10.0, "swim_joint": JOINT / 1.5, "swim_wrist": 0.3, "swim_wrist_from": 0.86 * JOINT / 1.5,
		"swim_curl_from": -0.3 * U, "swim_curl_span": 1.05 * U,
		"ops": [
			{"type": "move", "parts": [DORSAL], "c": 1.0, "plus": -1.0, "drive3": "first_dorsal", "w": 2, "way": Vector3(0.0, -0.93, 0.45)},
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": EYE_MID * U, "way": EYE_OUT, "k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0},
			{"type": "scale", "parts": [GILL], "drive": "gape", "c": 1.0, "way": Vector3.RIGHT, "k2": 0.1},
			{"type": "turn", "parts": [JAW], "drive": "gape", "c": -JAW_DROP, "w": 1,
				"at": Vector3(0.0, HINGE_Y, HINGE - HALF) * U, "way": Vector3.RIGHT},
			{"type": "turn", "parts": not_jaw, "drive": "gape", "c": SNOUT_LIFT, "w": 1,
				"at": Vector3(0.0, HINGE_Y, HINGE - HALF) * U, "way": Vector3.RIGHT},
		],
	}


static func label(p: Vector3, _n: Vector3, _uv: Vector2, uv2: Vector2, _colour: Color, _old: Callable) -> Dictionary:
	var part := int(round(uv2.y))
	var xm := p.z / U + HALF
	var taper := 1.0 - smoothstep(HINGE * (1.0 - SOFT), HINGE, xm) if xm < HINGE else 0.0
	var what := uv2.x if part == 0 else 0.0
	var inside := floorf(what * 0.5 + 0.2)
	var jaw := what - 2.0 * inside
	if part == 0 and jaw > 0.5:
		return {"part": JAW, "w": [taper]}
	return {"part": part, "w": [taper, uv2.x if part == DORSAL else 0.0]}
