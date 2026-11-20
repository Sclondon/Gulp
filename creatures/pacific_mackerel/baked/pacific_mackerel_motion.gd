extends RefCounted
## The Pacific mackerel's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`),
## as pacific_mackerel.gdshader moved it: the wave back along the body (reach 0.7 * (0.01 - 0.03 s' + 0.035 s'^2 + 0.075 s'^4) body lengths,
## s' = metres behind the jaw / JOINT), the tail one plate behind its wrist, the turning curl, the
## lower jaw swinging down and the snout lifting a little (each point by its own share, UV2.x), the
## cartoon eye grown. Numbers from pacific_mackerel.gdshader.

const FAMILY := "swim"

const LENGTH := 0.4
const HALF := 0.2
const JOINT := 0.346
const HINGE_S := 0.095
const HINGE_Y := -0.02454
const GAPE_OPEN := 0.62
const UPPER_LIFT := 0.1
const EYE_PIVOT := Vector3(0.03604, 0.0274, 0.088)
const EYE_BIG := 1.45

# Parts: the model's (UV2.y: 7 an eye) and ours (the jaw's two sides).
const EYE := 7
const JAW := 20
const SNOUT := 21


static func numbers(_old: Callable) -> Dictionary:
	var k := LENGTH / JOINT
	var scale := 0.7
	return {
		"motion_length": LENGTH, "motion_nose": -HALF,
		"env_poly": Vector4(0.01, -0.03 * k, 0.035 * k * k, 0.0) * scale,
		"env_pow": Vector3(0.075 * pow(k, 4.0) * scale, 0.0, 4.0),
		"swim_from": -10.0, "swim_joint": JOINT / LENGTH, "swim_wrist": 0.25, "swim_wrist_from": 0.86 * JOINT / LENGTH,
		"swim_curl_from": -0.2 * LENGTH, "swim_curl_span": 0.7 * LENGTH,
		"ops": [
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": Vector3(EYE_PIVOT.x, EYE_PIVOT.y, EYE_PIVOT.z - 0.5) * LENGTH, "k1": EYE_BIG - 1.0, "k2": EYE_BIG - 1.0},
			{"type": "turn", "parts": [JAW], "drive": "gape", "c": -GAPE_OPEN, "w": 1,
				"at": Vector3(0.0, HINGE_Y, HINGE_S - 0.5) * LENGTH, "way": Vector3.RIGHT},
			{"type": "turn", "parts": [SNOUT], "drive": "gape", "c": -UPPER_LIFT, "w": 1,
				"at": Vector3(0.0, HINGE_Y, HINGE_S - 0.5) * LENGTH, "way": Vector3.RIGHT},
		],
	}


static func label(_p: Vector3, _n: Vector3, _uv: Vector2, uv2: Vector2, _colour: Color, _old: Callable) -> Dictionary:
	var part := int(round(uv2.y))
	if part == EYE:
		return {"part": EYE}
	if absf(uv2.x) > 0.0001:
		return {"part": JAW if uv2.x > 0.0 else SNOUT, "w": [uv2.x]}
	return {"part": part}
