extends RefCounted
## The rockfish's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## rockfish.gdshader moved it: the wave back along the body to the tail plate, the turning curl, the
## lower jaw swinging down and the snout lifting, the dorsal fin folding down (`dorsal` 0), the
## pectoral fins rowing (swung out and back, flapped, held back as `scull` falls), the soft fins rippling,
## the cartoon eye grown and domed and blinking. Numbers from rockfish.gdshader (its sums are in body
## lengths; here in metres). Differs: the eye's dome is a straight push outward as it grows, the blink a
## squash along the eye's facing; the pectorals' normals turn with the flap too.

const FAMILY := "swim"

const LENGTH := 0.5
const JOINT := 0.82
const SWING := 0.06
const HINGE_S := 0.155
const HINGE_Y := -0.078
const GAPE_ANGLE := 0.7
const LIFT := 0.06
const LIFT_TO := 0.09
const LIFT_Y := 0.06
const PEC_ROOT := Vector3(0.0685, -0.07, 0.33)
const PEC_SWING := 0.17
const PEC_FLAP := 0.12
const PEC_ALT := 1.0
const PEC_HOLD := -0.28
const FIN_WAVE := 0.006
const SPINE_SHARE := 0.64
const EYE_MID := Vector3(0.0637, 0.04, 0.128)
const EYE_FACING := Vector3(0.9038, 0.3196, -0.2846)
const EYE_R := 0.031
const EYE_SAG := -0.1043
const EYE_GROW := 1.85
const CORNER_B := 0.012
const CORNER_C := 0.035

# Parts (the model's UV2.y): 0 body, 1 lower jaw, 2 dorsal fin, 3 and 4 the other soft fins, 5 pectorals, 7 eyes.
const EYE := 7


static func numbers(_old: Callable) -> Dictionary:
	var L := LENGTH
	var mid := Vector3(EYE_MID.x, EYE_MID.y, EYE_MID.z - 0.5) * L
	var facing := EYE_FACING.normalized()
	var root := Vector3(PEC_ROOT.x, PEC_ROOT.y, PEC_ROOT.z - 0.5) * L
	var pec := {"parts": [5], "type": "turn", "drive": "scull", "lag": 3, "per_lag": -1.3, "side_off": PEC_ALT * PI,
		"flags": ["mirror"], "at": root}
	return {
		"motion_length": L, "motion_nose": -0.5 * L,
		"env_poly": Vector4(SWING * 0.1, -SWING * 0.5 / JOINT, SWING * 1.4 / (JOINT * JOINT), 0.0),
		"swim_from": -10.0, "swim_joint": JOINT, "swim_wrist": 0.25, "swim_wrist_from": 0.86 * JOINT,
		"swim_curl_from": -0.2 * L, "swim_curl_span": 0.7 * L,
		"ops": [
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": mid, "k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0},
			{"type": "move", "parts": [EYE], "drive": "cartoon_eyes", "c": EYE_GROW - 1.0, "w": 1, "flags": ["mirror"], "way": facing},
			{"type": "scale", "parts": [EYE], "drive": "blink", "c": 1.0, "flags": ["mirror"], "at": mid, "way": facing, "k2": -0.4},
			{"type": "turn", "parts": [1], "drive": "gape", "c": -GAPE_ANGLE, "w": 1,
				"at": Vector3(0.0, HINGE_Y, HINGE_S - 0.5) * L, "way": Vector3.RIGHT},
			{"type": "turn", "parts": [0], "drive": "gape", "c": LIFT, "w": 1,
				"at": Vector3(0.0, LIFT_Y, LIFT_TO - 0.5) * L, "way": Vector3.RIGHT},
			# (the dorsal fin folds by 1 - dorsal)
			{"type": "move", "parts": [2], "drive": "dorsal", "c": -1.0, "plus": 1.0, "w": 1, "way": Vector3(0.0, -0.9, 0.5) * L},
			pec.merged({"way": Vector3.UP, "c": -PEC_HOLD, "a": PEC_SWING, "plus": PEC_HOLD}, true),
			pec.merged({"way": Vector3.BACK, "a": PEC_FLAP, "off": 0.5 * PI}, true),
			{"type": "move", "parts": [2, 3, 4], "a": 0.3 * FIN_WAVE * L, "off": -1.0, "w": 2, "lag": 3, "per_lag": -5.0, "way": Vector3.RIGHT},
			{"type": "move", "parts": [2, 3, 4], "drive": "sway", "a": 0.7 * FIN_WAVE * L, "off": -1.0, "w": 2, "lag": 3, "per_lag": -5.0,
				"way": Vector3.RIGHT},
		],
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, _old: Callable) -> Dictionary:
	var part := int(uv2.y + 0.5)
	var s := p.z / LENGTH + 0.5
	match part:
		1:
			return {"part": 1, "w": [1.0 - smoothstep(HINGE_S - CORNER_B, HINGE_S + CORNER_C, s)]}
		0:
			return {"part": 0, "w": [1.0 - smoothstep(0.0, LIFT_TO, s) if s < LIFT_TO else 0.0]}
		2, 3, 4:
			var soft := smoothstep(SPINE_SHARE - 0.1, SPINE_SHARE + 0.1, uv.y) if part == 2 else 1.0
			return {"part": part, "w": [uv2.x if part == 2 else 0.0, soft * uv.x * uv.x, uv.y]}
		5:
			return {"part": 5, "w": [0.0, 0.0, uv.x]}
		EYE:
			var r := uv.x
			return {"part": EYE, "w": [(EYE_SAG * EYE_R * EYE_GROW * r * r - 0.02 * EYE_R) * LENGTH]}
	return {"part": part}
