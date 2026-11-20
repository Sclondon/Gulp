extends RefCounted
## The lamprey's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## lamprey.gdshader moved it: an eel's wave of nearly even size down the whole body, the fins' edges
## lagging, the round sucker disc closing to a slit and opening (`gape`), the cartoon eye grown, bulging
## and pushed out, and shut as it blinks; the curl. The disc's squeeze is two scales each way (a fixed one
## to its shut shape, then opened by the gape), which come to the same as the old shader's.

const FAMILY := "swim"

const LENGTH := 0.7
const DISC_S := 0.024
const DISC_Y := -0.015
const DISC_AXIS := Vector3(0.0, -0.6, -0.8)
const DISC_V := Vector3(0.0, 0.8, -0.6)
const WAVE := 0.7
const EYE_MIDDLE := Vector3(0.01473, 0.00684, -0.30078)
const EYE_OUT := Vector3(0.9342, 0.3532, -0.0494)
const EYE_GROW := 1.6
const EYE_BULGE := 1.3
const EYE_PUSH := 0.003

# Parts (the model's, COLOR.r * 10).
const EYE := 2
const DISC := [1, 3]


static func numbers(_old: Callable) -> Dictionary:
	var L := LENGTH
	var o := EYE_OUT.normalized()
	var up := (Vector3.UP - o * o.y).normalized()
	var centre := Vector3(0.0, DISC_Y, DISC_S - 0.5) * L
	var axis := DISC_AXIS.normalized()
	var dv := DISC_V.normalized()
	return {
		"motion_length": L, "motion_nose": -0.5 * L, "wave": WAVE,
		"env_poly": Vector4(0.022, 0.048, 0.0, 0.0), "env_pow": Vector3(0.0, 0.0, 2.0),
		"swim_from": 0.0, "swim_joint": 1.02, "swim_wrist": 0.0,
		"swim_curl_from": -0.3 * L, "swim_curl_span": 0.7 * L,
		"ops": [
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": EYE_MIDDLE, "way": EYE_OUT, "k1": EYE_GROW - 1.0, "k2": EYE_BULGE - 1.0},
			{"type": "scale", "parts": [EYE], "drive": "blink", "c": 1.0, "flags": ["mirror"], "at": EYE_MIDDLE, "way": up, "k2": -0.8},
			{"type": "move", "parts": [EYE], "drive": "cartoon_eyes", "c": EYE_PUSH, "flags": ["mirror"], "way": o},
			# the disc: across to 0.1 and down its face to 0.72, sunk 0.009 lengths, shut; opened by the gape
			{"type": "scale", "parts": DISC, "c": 1.0, "at": centre, "way": Vector3.RIGHT, "k2": -0.9},
			{"type": "scale", "parts": DISC, "drive": "gape", "c": 1.0, "at": centre, "way": Vector3.RIGHT, "k2": 9.0},
			{"type": "scale", "parts": DISC, "c": 1.0, "at": centre, "way": dv, "k2": -0.28},
			{"type": "scale", "parts": DISC, "drive": "gape", "c": 1.0, "at": centre, "way": dv, "k2": 0.28 / 0.72},
			{"type": "move", "parts": DISC, "c": -0.009 * L, "way": axis},
			{"type": "move", "parts": DISC, "drive": "gape", "c": 0.009 * L, "way": axis},
			{"type": "move", "parts": [5, 6, 7, 8, 9, 10, 11], "drive": "sway", "a": 0.006 * L, "off": -0.8, "beat": "tail_beats",
				"w": 1, "lag": 2, "per_lag": -1.0},
		],
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, _uv2: Vector2, colour: Color, _old: Callable) -> Dictionary:
	var part := int(floor(colour.r * 10.0 + 0.5))
	if part >= 5:
		return {"part": mini(part, 11), "w": [uv.x * uv.x, TAU * (p.z / LENGTH + 0.5) / WAVE]}
	return {"part": part}
