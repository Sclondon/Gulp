extends RefCounted
## The yellowfin tuna's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`),
## as yellowfin_tuna.gdshader moved it: the wave back along the body, the tail one plate behind its
## wrist, the turning curl, the first dorsal folding down into its groove (`first_dorsal`), the cartoon
## eye grown about its middle (its inner half by the growth, not its square), and the jaws: the model is
## built with its mouth open, so the lower jaw and the lips are swung shut at gape 0 and open with it.

const FAMILY := "swim"

const LENGTH := 1.5
const HALF := 0.75
const JOINT := 1.335
const MOUTH_TO := 0.132
const HINGE := Vector2(0.132, -0.0393)
const GAPE_TURN := 0.55
const JAW_BACK := 0.172
const EYE_MID := Vector3(0.07126, 0.024, -0.605)
const EYE_OUT := Vector3(0.92575, 0.18181, -0.33156)
const EYE_GROW := 1.6

# Parts (the model's UV2.y): 1 the first dorsal, 7 an eye, 8 the lower jaw, 9 and over 9.5 the lips' rims.
const DORSAL := 1
const EYE := 7
const JAW := 8
const RIM := 9
const RIM2 := 10


static func numbers(_old: Callable) -> Dictionary:
	var k := LENGTH / JOINT
	var hinge := Vector3(0.0, HINGE.y, HINGE.x - HALF)
	return {
		"motion_length": LENGTH, "motion_nose": -HALF,
		"env_poly": Vector4(0.012, -0.03 * k, 0.03 * k * k, 0.0) * 0.7,
		"env_pow": Vector3(0.085 * pow(k, 4.0) * 0.7, 0.0, 4.0),
		"swim_wave_scale": 1.0 / k,
		"swim_from": -10.0, "swim_joint": JOINT / LENGTH, "swim_wrist": 0.3, "swim_wrist_from": 0.86 * JOINT / LENGTH,
		"swim_curl_from": -0.2 * LENGTH, "swim_curl_span": 0.7 * LENGTH,
		"ops": [
			{"type": "move", "parts": [DORSAL], "c": 1.0, "plus": -1.0, "drive3": "first_dorsal", "w": 2, "way": Vector3(0.0, -0.93, 0.45)},
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": EYE_MID, "way": EYE_OUT, "k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0},
			{"type": "turn", "parts": [RIM, RIM2], "c": GAPE_TURN, "plus": -GAPE_TURN, "drive3": "gape", "w": 1, "at": hinge, "way": Vector3.RIGHT},
			{"type": "turn", "parts": [JAW], "drive": "gape", "c": -GAPE_TURN, "w": 1, "at": hinge, "way": Vector3.RIGHT},
		],
	}


static func _jaw_turn(xm: float) -> float:
	return 1.0 - smoothstep(MOUTH_TO - 0.02, JAW_BACK, xm)


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, _old: Callable) -> Dictionary:
	var part := int(round(uv2.y))
	if uv2.y > 9.5:
		return {"part": RIM2, "w": [_jaw_turn(uv.x * LENGTH) * uv2.x]}
	if part == RIM:
		return {"part": RIM, "w": [_jaw_turn(uv.x * LENGTH) * uv2.x]}
	if part == JAW:
		return {"part": JAW, "w": [_jaw_turn(p.z + HALF)]}
	return {"part": part, "w": [0.0, uv2.x if part == DORSAL else 0.0]}
