extends RefCounted
## The guppy's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## guppy.gdshader moved it (it worked in body lengths, `length_m` a metre count; here in metres): the
## wave back along the body, three tail beats a loop; a male's long tail swung less than his body and
## trailing behind it; ripples running through the tail and a male's dorsal fin; the curl; the lower jaw
## swung down, the back of the mouth lifted out of the way and the gill arches spread as it opens; the
## cartoon eye grown. Females, males and their colours differ by settings (length_m, joint, male, ...),
## read from each material; numbers from guppy.gdshader. Differs: the tail's own lesser swing is worked
## out from the body's slope at the joint as a sine (the old shader's atan of it), and the slight tilt the
## ripples gave the fins' normals is gone.

const FAMILY := "swim"

const HALF := 0.5
const GAPE_OPEN := 1.0
const DEFAULTS := {&"length_m": 0.04, &"jaw_to": 0.037, &"hinge_y": -0.01132, &"eye_at": Vector2(0.074, 0.013),
	&"eye_radius": 0.031, &"joint": 0.525, &"male": 1.0, &"tail_beats": 3.0, &"wave": 0.9, &"gill_from": 0.0806,
	&"gill_to": 0.146, &"wall_up": 0.0129, &"eye_big": 1.45}

const DORSAL := 1
const TAIL := 3
const EYE := 6
const JAW := 7
const GILL := 8
const WALL := 9


static func _value(old: Callable, name: StringName) -> Variant:
	var v: Variant = old.call(name)
	return v if v != null else DEFAULTS[name]


static func numbers(old: Callable) -> Dictionary:
	var length: float = _value(old, &"length_m")
	var joint: float = _value(old, &"joint")
	var male: float = _value(old, &"male")
	var wave: float = _value(old, &"wave")
	var jaw_to: float = _value(old, &"jaw_to")
	var eye_at: Vector2 = _value(old, &"eye_at")
	var big: float = _value(old, &"eye_big")
	var radius: float = _value(old, &"eye_radius")
	var mid: float = 0.5 * (float(_value(old, &"gill_from")) + float(_value(old, &"gill_to")))
	# (the body's slope at the joint, as a sine: the tail plate is turned back by 0.45 of it for a male)
	var reach := 0.008 - 0.03 + 0.085
	var reach_slope := (-0.03 + 2.0 * 0.085) / joint
	var k := TAU * reach / wave
	var size := Vector2(reach_slope, -k).length()
	var lead := atan2(-k, reach_slope)
	return {
		"motion_length": length, "motion_nose": -HALF * length,
		"env_poly": Vector4(0.008, -0.03 / joint, 0.085 / (joint * joint), 0.0),
		"swim_from": -10.0, "swim_joint": joint, "swim_wrist": 0.2, "swim_wrist_from": 0.86 * joint,
		"swim_curl_from": -0.2 * length, "swim_curl_span": 0.7 * length,
		"ops": [
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "at": Vector3(0.0, eye_at.y, eye_at.x - HALF) * length,
				"way": Vector3.RIGHT, "k1": big - 1.0},
			{"type": "move", "parts": [EYE], "drive": "cartoon_eyes", "c": (big - 1.0) * radius * 0.3 * length, "flags": ["mirror"], "way": Vector3.RIGHT},
			{"type": "move", "parts": [EYE], "drive": "cartoon_eyes", "c": (big - 1.0) * radius * 0.8 * length, "way": Vector3.BACK},
			{"type": "draw", "parts": [WALL], "drive": "gape", "shape": "on", "c": 1.0, "at": Vector3(0.0, float(_value(old, &"wall_up")) * length, 0.0), "way": Vector3.UP},
			{"type": "scale", "parts": [WALL], "drive": "gape", "shape": "on", "c": 1.0, "way": Vector3.RIGHT, "k2": -0.45},
			{"type": "move", "parts": [WALL], "drive": "gape", "shape": "on", "c": 0.004 * length, "way": Vector3.BACK},
			{"type": "scale", "parts": [GILL], "drive": "gape", "c": 1.0, "way": Vector3.RIGHT, "k2": 0.1},
			{"type": "scale", "parts": [GILL], "drive": "gape", "c": 1.0, "at": Vector3(0.0, 0.0, (mid - HALF) * length), "way": Vector3.BACK, "k2": 0.15},
			{"type": "turn", "parts": [JAW], "drive": "gape", "c": -GAPE_OPEN, "w": 1,
				"at": Vector3(0.0, float(_value(old, &"hinge_y")), jaw_to - HALF) * length, "way": Vector3.RIGHT},
			{"type": "move", "parts": [DORSAL, TAIL], "drive": "ripple", "a": length, "beat": "ripples", "w": 1, "lag": 2, "per_lag": 1.0, "way": Vector3.RIGHT},
			# a male's tail plate swung back by 0.45 of the body's turn at the joint (x 1.2, the wrist's flex)
			{"type": "turn", "drive": "sway", "a": -0.45 * 1.2 * male * size, "beat": "tail_beats",
				"off": -TAU * joint / wave + lead, "w": 3, "at": Vector3(0.0, 0.0, (joint - HALF) * length), "way": Vector3.UP},
			# and trailing behind it
			{"type": "move", "drive": "sway", "a": 0.24 * male * length, "beat": "tail_beats", "off": -0.16 * PI,
				"w": 4, "lag": 5, "per_lag": -TAU / wave, "way": Vector3.RIGHT, "flags": ["after"]},
		],
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, old: Callable) -> Dictionary:
	var length: float = _value(old, &"length_m")
	var joint: float = _value(old, &"joint")
	var male: float = _value(old, &"male")
	var jaw_to: float = _value(old, &"jaw_to")
	var v := p / length
	var xm := v.z + HALF
	var part := int(uv2.y + 0.5)
	# (every point behind the joint: its step, the trail's weight and how far back it is)
	var d := maxf(xm - joint, 0.0)
	var back := [1.0 if xm >= joint else 0.0, d * sqrt(d), xm]
	if part == 0 and uv2.x > 0.999 and uv.y > 0.45 and uv.y < 0.55 and absf(xm - jaw_to) < 0.0005:
		return {"part": WALL, "w": [0.0, 0.0] + back}
	if part == JAW:
		return {"part": JAW, "w": [1.0 - smoothstep(jaw_to - 0.016, jaw_to - 0.002, xm), 0.0] + back}
	if part == TAIL or part == DORSAL:
		var w: float
		if part == TAIL:
			w = smoothstep(joint, joint + 0.3, xm) * lerpf(0.004, 0.016, male)
		else:
			w = clampf((v.y - 0.05) / 0.1, 0.0, 1.0) * smoothstep(0.3, 0.6, xm) * 0.012 * male
		return {"part": part, "w": [w, -xm * 22.0 + v.y * 30.0] + back}
	return {"part": part, "w": [0.0, 0.0] + back}
