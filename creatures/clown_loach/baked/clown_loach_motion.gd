extends RefCounted
## The clown loach's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`),
## as clown_loach.gdshader moved it: the wave back along the body (four tail beats a loop), the curl; the
## pectoral fins fanning; the barbels twitching (three beats each, a different lag for each barbel), the
## lip barbels going with the jaw; the lower jaw and the lips swung open; the cartoon eye grown and its
## blink. Numbers from clown_loach.gdshader. The barbels' beats are fixed from `twitches` when it is put on.

const FAMILY := "swim"

const LENGTH := 0.2
const HALF := 0.1
const PECTORAL_ROOT := Vector3(0.00985, -0.00657, -0.05100)
const PECTORAL_AXIS := Vector3(-0.4633, -0.8623, -0.2043)
const MOUTH_TO := 0.0085
const HINGE := Vector2(0.0085, -0.00463)
const JAW_BACK := 0.0125
const GAPE_TURN := 0.75
const EYE_MIDDLE := Vector3(0.00909, 0.0092, -0.071)
const EYE_OUT := Vector3(0.9676, 0.1536, -0.2004)

const PECTORAL := 4
const EYE := 6
const BARBEL := 7
const LIP_BARBEL := 11
const JAW := 8
const LIP := 9


static func _value(old: Callable, name: StringName, otherwise: float) -> float:
	var v: Variant = old.call(name)
	return float(v) if v != null else otherwise


static func numbers(old: Callable) -> Dictionary:
	var grow := _value(old, &"eye_grow", 1.9)
	var sink := _value(old, &"eye_sink", 0.0)
	var tw := _value(old, &"twitches", 2.0)
	var o := EYE_OUT.normalized()
	var up := (Vector3.UP - o * o.y).normalized()
	var hinge := Vector3(0.0, HINGE.y, HINGE.x - HALF)
	var twitch := {"parts": [BARBEL, LIP_BARBEL], "drive": "twitch", "w": 2, "lag": 3}
	return {
		"motion_length": LENGTH, "motion_nose": -HALF,
		"env_poly": Vector4(0.016, -0.062, 0.146, 0.0),
		"swim_from": 0.0, "swim_joint": 1.0,
		"swim_curl_from": -0.2 * LENGTH, "swim_curl_span": 0.7 * LENGTH,
		"ops": [
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"], "at": EYE_MIDDLE, "way": o, "k1": grow - 1.0},
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "w": 2, "flags": ["mirror"], "at": EYE_MIDDLE, "way": o, "k2": grow - 1.0},
			{"type": "move", "parts": [EYE], "drive": "cartoon_eyes", "c": -sink * (grow * grow - 1.0), "w": 1, "flags": ["mirror"], "way": o},
			{"type": "scale", "parts": [EYE], "drive": "blink", "c": 1.0, "flags": ["mirror"], "at": EYE_MIDDLE, "way": up, "k2": -0.8},
			{"type": "turn", "parts": [PECTORAL], "drive": "fan", "c": -0.18, "a": -0.32, "beat": "fans", "lag": 1, "per_lag": -1.3,
				"flags": ["mirror"], "at": PECTORAL_ROOT, "way": PECTORAL_AXIS},
			twitch.merged({"type": "move", "a": 0.0013, "beats": tw, "per_lag": 2.4, "way": Vector3.RIGHT}),
			twitch.merged({"type": "move", "a": 0.5 * 0.0013, "beats": 2.0 * tw + 1.0, "per_lag": 4.1, "way": Vector3.RIGHT}),
			twitch.merged({"type": "move", "a": 0.3 * 0.0013, "beats": tw + 1.0, "per_lag": 1.7, "way": Vector3.UP}),
			twitch.merged({"type": "move", "a": 0.6 * 0.0013, "beats": tw + 1.0, "per_lag": 1.7, "way": Vector3.BACK}),
			{"type": "turn", "parts": [LIP_BARBEL], "drive": "gape", "c": -GAPE_TURN, "at": hinge, "way": Vector3.RIGHT},
			{"type": "turn", "parts": [JAW, LIP], "drive": "gape", "c": -GAPE_TURN, "w": 1, "at": hinge, "way": Vector3.RIGHT},
			{"type": "turn", "parts": [LIP], "c": GAPE_TURN, "w": 1, "at": hinge, "way": Vector3.RIGHT},
		],
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, old: Callable) -> Dictionary:
	if uv2.y > 5.5 and uv2.y < 6.5:
		var sx := 1.0 if p.x >= 0.0 else -1.0
		var at := Vector3(EYE_MIDDLE.x * sx, EYE_MIDDLE.y, EYE_MIDDLE.z)
		var o := Vector3(EYE_OUT.x * sx, EYE_OUT.y, EYE_OUT.z).normalized()
		var d := p - at
		var across := d - o * d.dot(o)
		return {"part": EYE, "w": [across.dot(across), 1.0 if d.dot(o) >= 0.0 else 0.0]}
	if uv2.y > 3.5 and uv2.y < 4.5:
		return {"part": PECTORAL, "w": [uv.x]}
	if uv2.y > 6.5 and uv2.y < 7.5:
		var id := uv.y * 8.0
		return {"part": LIP_BARBEL if id > 5.5 else BARBEL, "w": [0.0, uv.x * uv.x, id]}
	if uv2.y > 7.5 and uv2.y < 8.5:
		return {"part": JAW, "w": [_jaw_turn(p.z + HALF)]}
	if uv2.y > 8.5:
		return {"part": LIP, "w": [_jaw_turn(uv.x * LENGTH) * uv2.x]}
	return {"part": int(round(uv2.y))}


static func _jaw_turn(xm: float) -> float:
	return 1.0 - smoothstep(MOUTH_TO - 0.0015, JAW_BACK, xm)
