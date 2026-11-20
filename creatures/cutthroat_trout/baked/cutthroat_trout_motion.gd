extends RefCounted
## The cutthroat trout's motion in the swim family (scripts/motion.gd; GameCommon
## `godot/motion-families`), as cutthroat_trout.gdshader moved it: the body wave (by `swim`), the tail fin's
## edge and the soft fins lagging, the pectoral fins sculling and the pelvic fins paddling, the jaw
## opening a little with each breath and by `gape`, the gill covers flaring with each breath, the cartoon
## eye grown and shut as it blinks; the curl.
##
## Its body wave is driven by `swim`, not `sway` (the family's core reads `sway`), so here the core's
## wave is off and the wave is two moves driven by `swim`: each point turned about the body's line by the
## wave's slope (the slope itself, where the old shader took its angle: 3% less at the steepest), then
## carried sideways. Numbers from cutthroat_trout.gdshader; the eye's place and size from the material.

const FAMILY := "swim"

const LENGTH := 0.4
const HINGE_S := 0.112
const HINGE_Y := -0.031
const WAVE := 0.95
const ARCHES := false

# Parts (the model's, COLOR.r * 10).
const BODY := 0
const JAW := 1
const EYE := 2
const TAIL := 6
const PELVIC := 8
const PEC := 9
# Weight slots: 1..3 by part; 4 the wave's turn, 5 its reach, 6 and 7 their lags.


static func _hinge(old: Callable) -> Vector2:
	var h: Variant = old.call(&"hinge_s")
	var y: Variant = old.call(&"hinge_y")
	return Vector2(HINGE_S if h == null else float(h), HINGE_Y if y == null else float(y))


static func numbers(old: Callable) -> Dictionary:
	var L := LENGTH
	var h := _hinge(old)
	var hinge := Vector3(0.0, h.y * L, (h.x - 0.5) * L)
	var at: Vector3 = old.call(&"eye_at")
	var out: Vector3 = (old.call(&"eye_out") as Vector3).normalized()
	var up := (Vector3.UP - out * out.y).normalized()
	var grow: float = old.call(&"eye_grow")
	var ops := [
		{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"], "at": at, "way": out,
			"k1": grow - 1.0, "k2": grow - 1.0},
		{"type": "scale", "parts": [EYE], "drive": "blink", "c": 1.0, "flags": ["mirror"], "at": at, "way": up, "k2": -0.8},
		{"type": "turn", "parts": [JAW], "drive": "gape", "c": -1.0, "w": 1, "at": hinge, "way": Vector3.RIGHT},
		{"type": "turn", "parts": [JAW], "drive": "gape_breath", "c": -0.5, "a": 0.5, "off": 0.5 * PI, "beat": "breaths",
			"w": 1, "at": hinge, "way": Vector3.RIGHT},
		{"type": "move", "parts": [BODY], "drive": "gill_flare", "c": 0.5, "a": -0.5, "off": 0.5 * PI - 1.3, "beat": "breaths",
			"w": 1, "flags": ["mirror"], "way": Vector3.RIGHT},
		{"type": "move", "parts": [PEC], "drive": "scull", "c": 0.03 * L * 0.35, "a": 0.03 * L, "beat": "sculls",
			"side_off": 1.3, "w": 1, "flags": ["own_way"]},
		{"type": "move", "parts": [PEC], "drive": "scull", "a": 0.03 * L * 0.7, "off": -1.2, "beat": "sculls",
			"side_off": 1.3, "w": 2, "flags": ["own_way"]},
		{"type": "move", "parts": [PELVIC], "drive": "scull", "a": 0.012 * L, "off": 2.2, "beat": "sculls", "side_off": 1.1,
			"w": 2, "lag": 3, "per_lag": -0.25, "flags": ["own_way"]},
		{"type": "move", "parts": [TAIL], "drive": "swim", "a": 0.022 * L, "off": -1.1, "beat": "tail_beats", "w": 2, "lag": 3, "per_lag": -1.0},
		{"type": "move", "parts": [4, 5, 7], "drive": "swim", "a": 0.014 * L, "off": -1.0, "beat": "tail_beats", "w": 2, "lag": 3, "per_lag": -1.0},
		# the body's wave, by swim: turned about its line by the slope, then carried sideways
		{"type": "turn", "drive": "swim", "a": 1.0, "beat": "tail_beats", "w": 4, "lag": 6, "per_lag": -1.0,
			"flags": ["own_point"], "way": Vector3.UP},
		{"type": "move", "drive": "swim", "a": L, "beat": "tail_beats", "w": 5, "lag": 7, "per_lag": -1.0, "way": Vector3.RIGHT},
	]
	var out_numbers := {
		"motion_length": L, "motion_nose": -0.5 * L, "wave": WAVE,
		"env_poly": Vector4.ZERO, "env_pow": Vector3(0.0, 0.0, 2.0),
		"swim_curl_from": -0.2 * L, "swim_curl_span": 0.7 * L,
		"ops": ops,
	}
	if ARCHES:
		out_numbers.merge({"swim_arch_from": 0.0, "swim_arch_span": L, "swim_arch_both": true}, true)
	return out_numbers


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, colour: Color, _old: Callable) -> Dictionary:
	var L := LENGTH
	var part := int(floor(colour.r * 10.0 + 0.5))
	var s := p.z / L + 0.5
	var sb := clampf(s, 0.0, 1.05)
	var k := TAU / WAVE
	var reach := 0.012 - 0.05 * sb + 0.14 * sb * sb
	var slope_sin := -0.05 + 0.28 * sb
	var slope_cos := reach * k
	# (slope = swim * (slope_sin * sin(w) - slope_cos * cos(w)) = swim * A * sin(w - phi))
	var turn := sqrt(slope_sin * slope_sin + slope_cos * slope_cos)
	var phi := atan2(slope_cos, slope_sin)
	var w := [0.0, 0.0, 0.0, turn, reach, k * sb + phi, k * sb]
	var body := {"part": part, "w": w, "point": Vector3(0.0, p.y, p.z)}
	var r := uv.x
	match part:
		JAW:
			w[0] = _ss(0.137, 0.09, s)
		BODY:
			w[0] = colour.g
		PEC:
			w[0] = r
			w[1] = r * r
			body["way"] = Vector3(uv2.x, uv2.y, colour.b * 2.0 - 1.0).normalized()
		PELVIC:
			w[1] = r * r
			w[2] = uv.y
			body["way"] = Vector3(uv2.x, uv2.y, colour.b * 2.0 - 1.0).normalized()
		TAIL:
			w[1] = r * r
			w[2] = k * clampf(s, 0.0, 1.05)
		_:
			if part >= 4:
				w[1] = r * r
				w[2] = k * clampf(s, 0.0, 1.05) + uv.y * 0.2
	return body


# GLSL's smoothstep, either way round.
static func _ss(e0: float, e1: float, x: float) -> float:
	var t := clampf((x - e0) / (e1 - e0), 0.0, 1.0)
	return t * t * (3.0 - 2.0 * t)
