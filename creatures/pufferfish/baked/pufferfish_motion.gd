extends RefCounted
## The pufferfish's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## pufferfish.gdshader moved it: the little tail wave and tail fin beat; the pectoral fins rowing (each
## turning about its root, its edge fluttering); the dorsal and anal fins buzzing; the jaws opening; the
## cartoon eye grown and its blink; and puffing up (`puff`): the body blown out towards a ball, the mouth,
## eyes, fins and spines carried out with it, the spines turned to stand out from the ball. Numbers from
## pufferfish.gdshader. Differs: the body's normals no longer turn towards the ball as it puffs (the light
## on a puffed ball is that of the slimmer fish); the eyes and spines turn out in step with `puff` (the old
## shader eased the spines up between 0.1 and 0.9); the swimming wave is worked out where the puffed body
## is, not where it was (the tail is barely puffed, so it matters little).

const FAMILY := "swim"

const LENGTH := 0.3
const HINGE := Vector2(0.04, -0.028)
const MOUTH_Y := -0.012
const EYE_SKIN := Vector3(0.1117, 0.104, 0.17)
const EYE_OUT := Vector3(0.7829, 0.5802, -0.2244)
const PEC_ROOT := Vector3(0.1393, 0.005, 0.303)
const DORSAL_ROOT := Vector4(0.0904, 0.6, 0.0592, 0.675)
const DORSAL_RAYS := 10.0
const ANAL_ROOT := Vector4(-0.071, 0.625, -0.0454, 0.7)
const ANAL_RAYS := 9.0
const PUFF_AT := Vector2(0.0, 0.38)
const PUFF_RADIUS := 0.35
const GAPE_ANGLE := 0.75
const GAPE_LIFT := 0.22

# Our parts.
const LOWER := 1
const EYE := 2
const UPPER := 3
const SPINE := 5
const DORSAL := 6
const ANAL := 7
const FIN := 8
const PECTORAL := 9


static func numbers(old: Callable) -> Dictionary:
	var eye_size := float(old.call(&"eye_size")) if old.call(&"eye_size") != null else 1.9
	var at := Vector3(EYE_SKIN.x, EYE_SKIN.y, EYE_SKIN.z - 0.5) * LENGTH
	var at_now := _puffed(at)
	var now_out := (at_now - _ball()).normalized()
	var eye_axis := EYE_OUT.cross(now_out)
	var eye_angle := atan2(eye_axis.length(), EYE_OUT.dot(now_out))
	eye_axis = eye_axis.normalized() if eye_axis.length() > 1e-5 else Vector3.RIGHT
	var pec := Vector3(PEC_ROOT.x, PEC_ROOT.y, PEC_ROOT.z - 0.5) * LENGTH
	var out := []
	out.append_array([
		{"type": "turn", "parts": [LOWER], "drive": "gape", "c": -GAPE_ANGLE, "at": Vector3(0.0, HINGE.y, HINGE.x - 0.5) * LENGTH, "way": Vector3.RIGHT},
		{"type": "turn", "parts": [UPPER], "drive": "gape", "c": GAPE_LIFT, "at": Vector3(0.0, MOUTH_Y + 0.014, HINGE.x - 0.5) * LENGTH, "way": Vector3.RIGHT},
		# (the body blown out, the mouth carried with it: each its own move)
		{"type": "move", "parts": [0, LOWER, UPPER], "drive": "puff", "c": 1.0, "flags": ["own_way"]},
		{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"], "at": at, "k1": eye_size - 1.0, "k2": eye_size - 1.0},
		{"type": "scale", "parts": [EYE], "drive": "blink", "drive2": "cartoon_eyes", "c": 1.0, "flags": ["mirror"], "at": at, "way": Vector3.UP, "k2": -0.45},
		{"type": "turn", "parts": [EYE], "drive": "puff", "c": eye_angle, "flags": ["mirror"], "at": at, "way": eye_axis},
		{"type": "move", "parts": [EYE], "drive": "puff", "c": 1.0, "flags": ["mirror"], "way": at_now - at},
		# the spines stand out from the ball (about their own roots, on their own axes)
		{"type": "turn", "parts": [SPINE], "drive": "puff", "c": 1.0, "w": 4, "flags": ["own_point", "own_way"]},
		# the fins buzz, the tail fin beats
		{"type": "move", "parts": [DORSAL, ANAL], "drive": "row", "a": 0.03 * LENGTH, "beat": "buzzes", "w": 4, "lag": 5, "per_lag": 1.0, "way": Vector3.RIGHT},
		{"type": "move", "parts": [FIN], "drive": "sway", "a": 0.03 * LENGTH, "beat": "tail_beats", "off": -PI - 1.1, "w": 1, "way": Vector3.RIGHT},
		# and are carried out with the ball (their roots' moves, weights 1..3)
		{"type": "move", "parts": [SPINE, DORSAL, ANAL], "drive": "puff", "c": 1.0, "w": 1, "way": Vector3.RIGHT},
		{"type": "move", "parts": [SPINE, DORSAL, ANAL], "drive": "puff", "c": 1.0, "w": 2, "way": Vector3.UP},
		{"type": "move", "parts": [SPINE, DORSAL, ANAL], "drive": "puff", "c": 1.0, "w": 3, "way": Vector3.BACK},
		# the pectoral fins: the edge's flutter (along its flat side), then the turn about the root
		{"type": "move", "parts": [PECTORAL], "drive": "row", "a": 0.02 * LENGTH, "beat": "strokes", "off": -1.3, "side_off": PI, "w": 1,
			"flags": ["mirror", "own_way"]},
		{"type": "turn", "parts": [PECTORAL], "drive": "row", "c": 0.05, "a": 0.45, "beat": "strokes", "side_off": PI,
			"flags": ["mirror"], "at": pec, "way": Vector3.UP},
		{"type": "move", "parts": [PECTORAL], "drive": "puff", "c": 1.0, "flags": ["mirror"], "way": _puffed(pec) - pec},
	])
	return {
		"motion_length": LENGTH, "motion_nose": -0.5 * LENGTH,
		"env_pow": Vector3(0.6 * 0.45 * 0.45, 0.55, 2.0), "wave": 2.0,
		"swim_from": 0.0, "swim_joint": 1.05,
		"swim_curl_from": -0.15 * LENGTH, "swim_curl_span": 0.65 * LENGTH,
		"ops": out,
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, colour: Color, _old: Callable) -> Dictionary:
	var part := floori(colour.r * 10.0 + 0.5)
	var mouth := Vector3(0.0, MOUTH_Y, -0.505) * LENGTH
	if part == 1 or part == 4:
		return {"part": LOWER, "way": _puffed(mouth) - mouth}
	if part == 3 or (part == 0 and colour.g > 0.5):
		return {"part": UPPER, "way": _puffed(mouth) - mouth}
	if part == 0:
		return {"part": 0, "way": _puffed(p) - p}
	if part == 2:
		return {"part": EYE}
	if part == 5:
		var root := Vector3(uv2.x, uv2.y, colour.g - 0.5) * LENGTH
		var way := Vector3(uv.y, colour.b * 2.0 - 1.0, 0.0)
		way.z = sqrt(maxf(1.0 - way.x * way.x - way.y * way.y, 0.0))
		var root_now := _puffed(root)
		var out_way := (root_now - _ball()).normalized()
		var axis := way.cross(out_way)
		var angle := atan2(axis.length(), way.dot(out_way))
		axis = axis.normalized() if axis.length() > 1e-5 else Vector3.RIGHT
		var moved := root_now - root
		return {"part": SPINE, "w": [moved.x, moved.y, moved.z, angle], "point": root, "way": axis}
	var r := uv.x
	if part == 9:
		return {"part": PECTORAL, "w": [r * r], "way": Vector3(uv2.x, uv2.y, colour.b * 2.0 - 1.0).normalized()}
	if part == 6 or part == 7:
		var line := DORSAL_ROOT if part == 6 else ANAL_ROOT
		var t := clampf(uv.y / (DORSAL_RAYS if part == 6 else ANAL_RAYS), 0.0, 1.0)
		var root := Vector3(0.0, lerpf(line.x, line.z, t), lerpf(line.y, line.w, t) - 0.5) * LENGTH
		var moved := _puffed(root) - root
		return {"part": DORSAL if part == 6 else ANAL, "w": [moved.x, moved.y, moved.z, pow(r, 1.4), -t * 2.2 + (PI if part == 7 else 0.0)]}
	return {"part": FIN, "w": [r * r]}


static func _ball() -> Vector3:
	return Vector3(0.0, PUFF_AT.x, PUFF_AT.y - 0.5) * LENGTH


# Where pufferfish.gdshader's `puffed(p, 1)` put a point: blown out to the ball.
static func _puffed(p: Vector3) -> Vector3:
	var c := _ball()
	var r := PUFF_RADIUS * LENGTH
	var m := Vector3(0.0, MOUTH_Y, -0.505) * LENGTH
	var dm := c + (m - c).normalized() * r - m
	var d := p - c
	var dp := c + d / maxf(d.length(), 1e-6) * r - p
	var s := p.z / LENGTH + 0.5
	var a := smoothstep(0.02, 0.09, s)
	var b := smoothstep(0.7, 0.8, s)
	return p + dm.lerp(dp, a) * (1.0 - b)
