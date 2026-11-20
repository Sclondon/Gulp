extends RefCounted
## The sardine's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`),
## as sardine.gdshader moved it: the wave back along the body (small at the head, growing to the
## tail), the forked tail one plate behind its wrist, the turning curl, the lower jaw swinging down,
## the old wall at the back of the full model's mouth lifted out of the way as it opens, the cartoon
## eye grown. Numbers from sardine.gdshader (kept in step with the model).

const FAMILY := "swim"

const LENGTH := 0.22
const HALF := 0.11
const JOINT := 0.183
const JAW_TO := 0.019
const HINGE_Y := -0.0049
const GAPE_OPEN := 0.8
const WALL_Y := 0.00134
const EYE_PIVOT := Vector3(0.00596, 0.00756, 0.021)
const EYE_BIG := 1.45

# Parts: the model's (UV2.y) and one of ours.
const EYE := 6
const JAW := 7
const WALL := 9


static func numbers(_old: Callable) -> Dictionary:
	var k := LENGTH / JOINT
	return {
		"motion_length": LENGTH, "motion_nose": -HALF,
		# reach = 0.008 - 0.03 s' + 0.082 s'^2 body lengths, s' = metres behind the jaw / JOINT
		"env_poly": Vector4(0.008, -0.03 * k, 0.082 * k * k, 0.0),
		"swim_from": -10.0, "swim_joint": JOINT / LENGTH, "swim_wrist": 0.2, "swim_wrist_from": 0.86 * JOINT / LENGTH,
		"swim_curl_from": -0.2 * LENGTH, "swim_curl_span": 0.7 * LENGTH,
		"ops": [
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": Vector3(EYE_PIVOT.x, EYE_PIVOT.y, EYE_PIVOT.z - HALF), "k1": EYE_BIG - 1.0, "k2": EYE_BIG - 1.0},
			{"type": "draw", "parts": [WALL], "drive": "gape", "shape": "on", "c": 1.0, "at": Vector3(0.0, WALL_Y, 0.0), "way": Vector3.UP},
			{"type": "scale", "parts": [WALL], "drive": "gape", "shape": "on", "c": 1.0, "way": Vector3.RIGHT, "k2": -0.5},
			{"type": "turn", "parts": [JAW], "drive": "gape", "c": -GAPE_OPEN, "w": 1,
				"at": Vector3(0.0, HINGE_Y, JAW_TO - HALF), "way": Vector3.RIGHT},
		],
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, _old: Callable) -> Dictionary:
	var part := int(round(uv2.y))
	var xm := p.z + HALF
	if part == 0 and uv2.x > 0.5 and absf(uv.y - 0.5) < 0.01 and xm > JAW_TO - 0.0002:
		return {"part": WALL}
	if part == JAW:
		return {"part": JAW, "w": [1.0 - smoothstep(JAW_TO - 0.008, JAW_TO - 0.0005, xm)]}
	return {"part": part}
