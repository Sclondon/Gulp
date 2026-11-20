extends RefCounted
## The wrasse's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## wrasse.gdshader moved it (the cleaner wrasse and the wrasse, by their settings): the wave back along the
## body to the tail plate, the turning curl, the lower jaw swinging down, the upper lip pushed forward and
## lifting, the dorsal fin folding down (`dorsal` 0), the pectoral fins rowing it along (held back as
## `scull` falls) with the body bobbing and pitching to each stroke, the soft fins rippling, the cartoon eye
## grown. Numbers from wrasse.gdshader (its sums are in body lengths; here in metres). Differs: the
## stroke's pitch turns the body a little where the old one sheared it; `scull` over 1 is not capped at 1.5.

const FAMILY := "swim"

const LENGTH := 0.25
const SWING := 0.05
const HINGE_S := 0.052
const HINGE_Y := -0.024
const MOUTH_Y0 := -0.013
const MOUTH_BOW := 1.2
const GAPE_ANGLE := 0.65
const LIFT := 0.12
const LIFT_TO := 0.06
const LIFT_Y := 0.02
const PROTRUDE := 0.008
const PEC_SWING := 0.6
const PEC_FLAP := 0.45
const PEC_ALT := 0.0
const PEC_HOLD := -0.3
const BOB := 0.012
const BOB_PITCH := 0.04
const FIN_WAVE := 0.005
const SPINE_SHARE := 0.44
const CURL_FROM := -0.25
const CORNER_B := 0.012
const CORNER_C := 0.035

# Parts (the model's UV2.y): 0 body, 1 lower jaw, 2 dorsal fin, 3 and 4 the other soft fins, 5 pectorals, 7 eyes.
const EYE := 7


static func numbers(old: Callable) -> Dictionary:
	var L := LENGTH
	var g: float = old.call(&"eye_grow")
	var facing: Vector3 = old.call(&"eye_facing")
	var mid: Vector3 = old.call(&"eye_mid")
	var at := (Vector3(mid.x, mid.y, mid.z - 0.5) + facing * (g * float(old.call(&"eye_sink")) + 0.02 * float(old.call(&"eye_radius")))) * L
	var pec_root: Vector3 = old.call(&"pec_root")
	var root := Vector3(pec_root.x, pec_root.y, pec_root.z - 0.5) * L
	var joint: float = old.call(&"joint")
	var pec := {"parts": [5], "type": "turn", "drive": "scull", "lag": 3, "per_lag": -1.1, "side_off": PEC_ALT * PI,
		"flags": ["mirror"], "at": root}
	return {
		"motion_length": L, "motion_nose": -0.5 * L,
		"env_poly": Vector4(SWING * 0.1, -SWING * 0.5 / joint, SWING * 1.4 / (joint * joint), 0.0),
		"swim_from": -10.0, "swim_joint": joint, "swim_wrist": 0.25, "swim_wrist_from": 0.86 * joint,
		"swim_curl_from": CURL_FROM * L, "swim_curl_span": 0.7 * L,
		"ops": [
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"], "at": at, "k1": g - 1.0, "k2": g - 1.0},
			{"type": "turn", "parts": [1], "drive": "gape", "c": -GAPE_ANGLE, "w": 1,
				"at": Vector3(0.0, HINGE_Y, HINGE_S - 0.5) * L, "way": Vector3.RIGHT},
			{"type": "move", "parts": [0], "drive": "gape", "c": -PROTRUDE * L, "w": 4, "way": Vector3.BACK},
			{"type": "turn", "parts": [0], "drive": "gape", "c": LIFT, "w": 1,
				"at": Vector3(0.0, LIFT_Y, LIFT_TO - 0.5) * L, "way": Vector3.RIGHT},
			{"type": "move", "parts": [2], "drive": "dorsal", "c": -1.0, "plus": 1.0, "w": 1, "way": Vector3(0.0, -0.9, 0.5) * L},
			pec.merged({"way": Vector3.UP, "c": -PEC_HOLD, "a": PEC_SWING, "plus": PEC_HOLD}, true),
			pec.merged({"way": Vector3.BACK, "a": PEC_FLAP, "off": 0.5 * PI}, true),
			{"type": "move", "parts": [2, 3, 4], "a": 0.3 * FIN_WAVE * L, "off": -1.0, "w": 2, "lag": 3, "per_lag": -5.0, "way": Vector3.RIGHT},
			{"type": "move", "parts": [2, 3, 4], "drive": "sway", "a": 0.7 * FIN_WAVE * L, "off": -1.0, "w": 2, "lag": 3, "per_lag": -5.0,
				"way": Vector3.RIGHT},
			# after the swimming: the stroke's bob and pitch
			{"type": "move", "drive": "scull", "a": BOB * L, "way": Vector3.UP, "flags": ["after"]},
			{"type": "turn", "drive": "scull", "a": -BOB_PITCH, "off": 0.5 * PI, "way": Vector3.RIGHT, "flags": ["after"]},
		],
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, _old: Callable) -> Dictionary:
	var part := int(uv2.y + 0.5)
	var s := p.z / LENGTH + 0.5
	match part:
		1:
			return {"part": 1, "w": [1.0 - smoothstep(HINGE_S - CORNER_B, HINGE_S + CORNER_C, s)]}
		0:
			if s >= LIFT_TO:
				return {"part": 0}
			var y := p.y / LENGTH
			var mouth_y := MOUTH_Y0 + (HINGE_Y - MOUTH_Y0) * pow(maxf(s, 0.0) / HINGE_S, MOUTH_BOW)
			var lip := (1.0 - smoothstep(0.0, 0.012, absf(y - mouth_y) - 0.004)) * (1.0 - smoothstep(0.02, HINGE_S, s))
			return {"part": 0, "w": [1.0 - smoothstep(0.0, LIFT_TO, s), 0.0, 0.0, lip]}
		2, 3, 4:
			var soft := smoothstep(SPINE_SHARE - 0.1, SPINE_SHARE + 0.1, uv.y) if part == 2 else 1.0
			return {"part": part, "w": [uv2.x if part == 2 else 0.0, soft * uv.x * uv.x, uv.y]}
		5:
			return {"part": 5, "w": [0.0, 0.0, uv.x]}
	return {"part": part}
