extends RefCounted
## The carp's (and koi's) motion in the swim family (scripts/motion.gd; GameCommon
## `godot/motion-families`), as carp.gdshader moved it: the body wave, the tail fin's edge and the soft
## fins lagging, the pectoral fins sculling and the pelvic fins paddling, the barbels streaming, the
## sucker mouth (the jaw swinging down, the lips pushed forward and down, the throat's floor sinking
## and its roof rising, the gill arches spreading), the cartoon eye grown, bulging and pushed out, and
## shut as it blinks; the curl. Numbers from carp.gdshader.

const FAMILY := "swim"

const LENGTH := 0.7
const HINGE_S := 0.066
const HINGE_Y := -0.033
const WAVE := 0.95
const GAPE_TURN := 0.42
const PROTRUDE := 0.03
const DROP := 0.022
const THROAT_SINK := 0.018
const THROAT_RAISE := 0.02
const EYE_MIDDLE := Vector3(0.02285, 0.01832, -0.28474)
const EYE_OUT := Vector3(0.9280, 0.2197, -0.3008)
const EYE_GROW := 1.5
const EYE_BULGE := 1.15
const EYE_PUSH := 0.0025

# Parts (the model's, COLOR.r * 10).
const BODY := 0
const JAW := 1
const EYE := 2
const LIPS := 3
const BARBEL := 5
const TAIL := 6
const PELVIC := 8
const PEC := 9
const GILL := 10
# Weight slots: 1 the jaw's swing, 2 the throat, 3 the push forward, 4..6 by part.


static func numbers(_old: Callable) -> Dictionary:
	var L := LENGTH
	var o := EYE_OUT.normalized()
	var up := (Vector3.UP - o * o.y).normalized()
	return {
		"motion_length": L, "motion_nose": -0.5 * L, "wave": WAVE,
		"env_poly": Vector4(0.012, -0.05, 0.14, 0.0), "env_pow": Vector3(0.0, 0.0, 2.0),
		"swim_from": 0.0, "swim_joint": 1.05, "swim_wrist": 0.0,
		"swim_curl_from": -0.24 * L, "swim_curl_span": 0.7 * L,
		"ops": [
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": EYE_MIDDLE, "way": EYE_OUT, "k1": EYE_GROW - 1.0, "k2": EYE_BULGE - 1.0},
			{"type": "scale", "parts": [EYE], "drive": "blink", "c": 1.0, "flags": ["mirror"], "at": EYE_MIDDLE, "way": up, "k2": -0.8},
			{"type": "move", "parts": [EYE], "drive": "cartoon_eyes", "c": EYE_PUSH, "flags": ["mirror"], "way": o},
			{"type": "move", "parts": [JAW], "drive": "gape", "c": -THROAT_SINK * L, "w": 2, "way": Vector3.UP},
			{"type": "turn", "parts": [JAW], "drive": "gape", "c": -GAPE_TURN, "w": 1,
				"at": Vector3(0.0, HINGE_Y * L, (HINGE_S - 0.5) * L), "way": Vector3.RIGHT},
			{"type": "move", "parts": [BODY], "drive": "gape", "c": THROAT_RAISE * L, "w": 2, "way": Vector3.UP},
			{"type": "move", "parts": [BARBEL], "drive": "sway", "a": 0.004 * L, "beat": "tail_beats", "w": 5, "lag": 4, "per_lag": -2.0},
			{"type": "move", "parts": [BODY, JAW, LIPS, BARBEL], "drive": "gape", "c": L, "w": 3, "way": Vector3(0.0, -DROP, -PROTRUDE)},
			{"type": "move", "parts": [GILL], "drive": "gape", "c": 0.005 * L, "w": 4, "way": Vector3.BACK},
			{"type": "move", "parts": [PEC], "drive": "scull", "c": 0.03 * L * 0.35, "a": 0.03 * L, "beat": "sculls",
				"side_off": 1.3, "w": 4, "flags": ["own_way"]},
			{"type": "move", "parts": [PEC], "drive": "scull", "a": 0.03 * L * 0.7, "off": -1.2, "beat": "sculls",
				"side_off": 1.3, "w": 5, "flags": ["own_way"]},
			{"type": "move", "parts": [PELVIC], "drive": "scull", "a": 0.012 * L, "off": 2.2, "beat": "sculls", "side_off": 1.1,
				"w": 5, "lag": 6, "per_lag": -0.25, "flags": ["own_way"]},
			{"type": "move", "parts": [TAIL], "drive": "sway", "a": 0.024 * L, "off": -1.1, "beat": "tail_beats", "w": 5, "lag": 6, "per_lag": -1.0},
			{"type": "move", "parts": [4, 7], "drive": "sway", "a": 0.014 * L, "off": -1.0, "beat": "tail_beats", "w": 5, "lag": 6, "per_lag": -1.0},
		],
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, colour: Color, _old: Callable) -> Dictionary:
	var L := LENGTH
	var part := int(floor(colour.r * 10.0 + 0.5))
	var s := p.z / L + 0.5
	var y := p.y / L
	var r := uv.x
	var wave_lag := TAU * clampf(s, 0.0, 1.05) / WAVE
	match part:
		JAW:
			return {"part": JAW, "w": [_ss(HINGE_S + 0.025, HINGE_S - 0.02, s), colour.b * _ss(0.0, HINGE_S, s), _ss(0.095, 0.02, s)]}
		BODY:
			return {"part": BODY, "w": [0.0, colour.b * _ss(0.03, 0.062, s), _ss(0.06, 0.0, s) * _ss(-0.004, -0.024, y)]}
		LIPS:
			return {"part": LIPS, "w": [0.0, 0.0, _ss(0.085, 0.0, s)]}
		BARBEL:
			return {"part": BARBEL, "w": [0.0, 0.0, _ss(0.085, 0.0, uv2.x), r, r * r]}
		GILL:
			return {"part": GILL, "w": [0.0, 0.0, 0.0, (absf(uv2.x) - 1.5) if colour.g > 0.25 else 0.0]}
		EYE:
			return {"part": EYE}
	if part >= 4 and part < 10:
		var way := Vector3(uv2.x, uv2.y, colour.b * 2.0 - 1.0).normalized()
		match part:
			PEC:
				return {"part": PEC, "w": [0.0, 0.0, 0.0, r, r * r], "way": way}
			PELVIC:
				return {"part": PELVIC, "w": [0.0, 0.0, 0.0, 0.0, r * r, uv.y], "way": way}
			TAIL:
				return {"part": TAIL, "w": [0.0, 0.0, 0.0, 0.0, r * r, wave_lag]}
		return {"part": part, "w": [0.0, 0.0, 0.0, 0.0, r * r, wave_lag + uv.y * 0.2]}
	return {"part": part}


# GLSL's smoothstep, either way round.
static func _ss(e0: float, e1: float, x: float) -> float:
	var t := clampf((x - e0) / (e1 - e0), 0.0, 1.0)
	return t * t * (3.0 - 2.0 * t)
