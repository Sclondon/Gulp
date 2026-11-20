extends RefCounted
## The corydoras' motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## corydoras.gdshader moved it: the wave back along the body, the tail one plate behind its wrist, the
## curl; the mouth pushed forward and the lower jaw swung down as it opens, the gill arches parted; the
## cartoon eye grown (sunk at its rim into the head) and its blink. Numbers from corydoras.gdshader.

const FAMILY := "swim"

const LENGTH := 0.06
const HALF := 0.03
const JOINT := 0.0462
const JAW_TO := 0.0036
const HINGE_Y := -0.0048
const GAPE_OPEN := 0.9
const PROTRUDE := 0.0003
const EYE_MIDDLE := Vector3(0.00499, 0.0036, -0.0236)
const EYE_OUT := Vector3(0.8194, 0.4205, -0.3896)
const GILL_GAP := 0.00125

const EYE := 6
const JAW := 7
const GILL := 10


static func numbers(old: Callable) -> Dictionary:
	var k := LENGTH / JOINT
	var grow: float = old.call(&"eye_grow") if old.call(&"eye_grow") != null else 1.5
	var o := EYE_OUT.normalized()
	var up := (Vector3.UP - o * o.y).normalized()
	return {
		"motion_length": LENGTH, "motion_nose": -HALF,
		"env_poly": Vector4(0.006, -0.03 * k, 0.09 * k * k, 0.0),
		"swim_from": -10.0, "swim_joint": JOINT / LENGTH, "swim_wrist": 0.25, "swim_wrist_from": 0.85 * JOINT / LENGTH,
		"swim_curl_from": -0.2 * LENGTH, "swim_curl_span": 0.7 * LENGTH,
		"ops": [
			# the eye: grown across its face, and along its axis where it stands out of the head; sunk at
			# its rim; squashed shut by a blink
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"], "at": EYE_MIDDLE, "way": o, "k1": grow - 1.0},
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "w": 2, "flags": ["mirror"], "at": EYE_MIDDLE, "way": o, "k2": grow - 1.0},
			{"type": "move", "parts": [EYE], "drive": "cartoon_eyes", "c": -(grow * grow - 1.0), "w": 1, "flags": ["mirror"], "way": o},
			{"type": "scale", "parts": [EYE], "drive": "blink", "c": 1.0, "flags": ["mirror"], "at": EYE_MIDDLE, "way": up, "k2": -0.85},
			{"type": "move", "parts": [GILL], "drive": "gape", "c": 0.14 * GILL_GAP, "w": 1, "way": Vector3.BACK},
			{"type": "move", "parts": [0, JAW, 8], "drive": "gape", "c": -PROTRUDE, "w": 1, "way": Vector3.BACK},
			{"type": "turn", "parts": [JAW], "drive": "gape", "c": -GAPE_OPEN, "w": 2, "at": Vector3(0.0, HINGE_Y, JAW_TO - HALF), "way": Vector3.RIGHT},
		],
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, old: Callable) -> Dictionary:
	var part := int(round(uv2.y))
	var xm := p.z + HALF
	if uv2.y > 5.5 and uv2.y < 6.5:
		var sink: Variant = old.call(&"eye_sink")
		return {"part": EYE, "w": _eye(p, sink if sink != null else Vector2(75.0, 15.0))}
	if uv2.y > 9.5:
		return {"part": GILL, "w": [floorf(uv.y) - 1.5]}
	var w := 0.0
	if (uv2.y < 0.5 or (uv2.y > 6.5 and uv2.y < 8.5)) and xm < JAW_TO + (0.003 if uv2.y >= 7.5 else 0.0):
		w = 1.0 - smoothstep(0.3 * JAW_TO, JAW_TO, xm)
		if uv2.y > 7.5:
			w = 1.0 - smoothstep(0.5 * JAW_TO, 1.4 * JAW_TO, xm)
	if part == JAW:
		return {"part": JAW, "w": [w, 1.0 - smoothstep(0.55 * JAW_TO, 0.97 * JAW_TO, xm)]}
	return {"part": part if part == 8 else (0 if uv2.y < 0.5 else part), "w": [w]}


# The eye's weights: [how far its rim sinks (eye_sink's sum), 1 where it stands out of the head].
static func _eye(p: Vector3, sink: Vector2) -> Array:
	var sx := 1.0 if p.x >= 0.0 else -1.0
	var at := Vector3(EYE_MIDDLE.x * sx, EYE_MIDDLE.y, EYE_MIDDLE.z)
	var o := Vector3(EYE_OUT.x * sx, EYE_OUT.y, EYE_OUT.z).normalized()
	var up := (Vector3.UP - o * o.y).normalized()
	var d := p - at
	var across := d - o * d.dot(o)
	var up_d := up * across.dot(up)
	var before := sink.x * up_d.dot(up_d) + sink.y * (across - up_d).dot(across - up_d)
	return [before, 1.0 if d.dot(o) >= 0.0 else 0.0]
