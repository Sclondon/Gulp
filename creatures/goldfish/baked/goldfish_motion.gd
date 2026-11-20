extends RefCounted
## The goldfish's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## goldfish.gdshader moved it: the wave back along the body, the tail one plate behind its wrist, the
## curl; the mouth pushed forward (the upper lip lifted) and the lower jaw swung down as it opens, the
## gill arches parted; the fins billowing (the tail most, a fantail's long veils with it); the cartoon
## eye grown (sunk at its rim into the head) and its blink. The plain goldfish and the fantail differ by
## their settings (joint, jaw_to, hinge_y, the eye's), read from each material; numbers from
## goldfish.gdshader.

const FAMILY := "swim"

const LENGTH := 0.15
const HALF := 0.075
const GAPE_OPEN := 0.95
const PROTRUDE := 0.0012
const LIFT := 0.0003
# (goldfish.gdshader's defaults, for a material that has not set its own)
const DEFAULTS := {&"joint": 0.108, &"jaw_to": 0.0095, &"hinge_y": -0.00154, &"eye_middle": Vector3(0.00989, 0.0042, -0.0575),
	&"eye_out": Vector3(0.9694, 0.1511, -0.1933), &"eye_grow": 1.55, &"eye_sink": Vector2(30.0, 6.0), &"gill_gap": 0.00338}

const TAIL := 3
const EYE := 6
const JAW := 7
const GILL := 10


static func _value(old: Callable, name: StringName) -> Variant:
	var v: Variant = old.call(name)
	return v if v != null else DEFAULTS[name]


static func numbers(old: Callable) -> Dictionary:
	var joint: float = _value(old, &"joint")
	var jaw_to: float = _value(old, &"jaw_to")
	var k := LENGTH / joint
	var grow: float = _value(old, &"eye_grow")
	var middle: Vector3 = _value(old, &"eye_middle")
	var o: Vector3 = (_value(old, &"eye_out") as Vector3).normalized()
	var up := (Vector3.UP - o * o.y).normalized()
	var fx := 0.05 * LENGTH
	var fy := -0.5 * 0.012 * LENGTH
	var flow := {"parts": [1, 2, TAIL, 4, 5], "lag": 3, "per_lag": -TAU}
	return {
		"motion_length": LENGTH, "motion_nose": -HALF,
		"env_poly": Vector4(0.01, -0.035 * k, 0.085 * k * k, 0.0),
		"swim_from": -10.0, "swim_joint": joint / LENGTH, "swim_wrist": 0.25, "swim_wrist_from": 0.85 * joint / LENGTH,
		"swim_curl_from": -0.2 * LENGTH, "swim_curl_span": 0.7 * LENGTH,
		"ops": [
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"], "at": middle, "way": o, "k1": grow - 1.0},
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "w": 2, "flags": ["mirror"], "at": middle, "way": o, "k2": grow - 1.0},
			{"type": "move", "parts": [EYE], "drive": "cartoon_eyes", "c": -(grow * grow - 1.0), "w": 1, "flags": ["mirror"], "way": o},
			{"type": "scale", "parts": [EYE], "drive": "blink", "c": 1.0, "flags": ["mirror"], "at": middle, "way": up, "k2": -0.85},
			{"type": "move", "parts": [GILL], "drive": "gape", "c": 0.14 * float(_value(old, &"gill_gap")), "w": 1, "way": Vector3.BACK},
			{"type": "move", "parts": [0, JAW], "drive": "gape", "c": -PROTRUDE, "w": 1, "way": Vector3.BACK},
			{"type": "move", "parts": [0], "drive": "gape", "c": LIFT, "w": 1, "way": Vector3.UP},
			{"type": "turn", "parts": [JAW], "drive": "gape", "c": -GAPE_OPEN, "w": 2,
				"at": Vector3(0.0, float(_value(old, &"hinge_y")), jaw_to - HALF), "way": Vector3.RIGHT},
			# the fins billow: billow * (0.4 + 0.6 sway) * (1 the tail, 0.3 the rest) along a wave out each fin
			flow.merged({"type": "move", "drive": "billow", "a": 0.4 * fx, "w": 1, "way": Vector3.RIGHT}),
			flow.merged({"type": "move", "drive": "billow", "drive2": "sway", "a": 0.6 * fx, "w": 1, "way": Vector3.RIGHT}),
			flow.merged({"type": "move", "drive": "billow", "c": 0.4 * fy, "a": 0.4 * fy, "w": 2, "way": Vector3.UP}),
			flow.merged({"type": "move", "drive": "billow", "drive2": "sway", "c": 0.6 * fy, "a": 0.6 * fy, "w": 2, "way": Vector3.UP}),
		],
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, old: Callable) -> Dictionary:
	var part := int(round(uv2.y))
	var xm := p.z + HALF
	var jaw_to: float = _value(old, &"jaw_to")
	if uv2.y > 5.5 and uv2.y < 6.5:
		return {"part": EYE, "w": _eye(p, _value(old, &"eye_middle"), _value(old, &"eye_out"), _value(old, &"eye_sink"))}
	if uv2.y > 9.5:
		return {"part": GILL, "w": [floorf(uv.y) - 1.5]}
	if uv2.y > 0.5 and uv2.y < 5.5:
		var t := uv.x
		var f := 1.0 if (uv2.y > 2.5 and uv2.y < 3.5) else 0.3
		return {"part": part, "w": [f * pow(t, 1.5), f * t * t, 0.75 * t + 0.25 * uv.y]}
	var w := 0.0
	if (uv2.y < 0.5 or (uv2.y > 6.5 and uv2.y < 7.5)) and xm < jaw_to:
		w = 1.0 - smoothstep(0.3 * jaw_to, jaw_to, xm)
	if part == JAW:
		return {"part": JAW, "w": [w, 1.0 - smoothstep(0.55 * jaw_to, 0.97 * jaw_to, xm)]}
	return {"part": 0 if uv2.y < 0.5 else part, "w": [w]}


static func _eye(p: Vector3, middle: Vector3, out: Vector3, sink: Vector2) -> Array:
	var sx := 1.0 if p.x >= 0.0 else -1.0
	var at := Vector3(middle.x * sx, middle.y, middle.z)
	var o := Vector3(out.x * sx, out.y, out.z).normalized()
	var up := (Vector3.UP - o * o.y).normalized()
	var d := p - at
	var across := d - o * d.dot(o)
	var up_d := up * across.dot(up)
	var before := sink.x * up_d.dot(up_d) + sink.y * (across - up_d).dot(across - up_d)
	return [before, 1.0 if d.dot(o) >= 0.0 else 0.0]
