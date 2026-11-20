extends RefCounted
## The trilobites' motion in the jointed family (scripts/motion.gd; GameCommon `godot/motion-families`),
## as trilobite.gdshader moved them: the legs on their strides (bent at joint and knee to reach each
## foot), the gill branches above them swinging with them (about up only, by a small-angle
## sum of the legs' turn) and with `feel`, the antennae feeling about,
## the cartoon eyes grown; rolling up into a ball (`enroll`): the body curled down and under from its
## middle, the sides curled down, legs and antennae drawn in, the ball lifted onto the floor.
##
## Differs when it enrolls (it walks and feels as before): the old shader carried legs, eyes and
## antennae with the body at their joints and bent the shields exactly; here each point bends by its own
## place, the shields by a bend before the middle's (close, not exact), and the lift onto the floor is fitted to `enroll` (right at 0, a half and 1). The legs
## still stride a little while rolled (the old ones stopped: `walk * (1 - enroll)`); they are drawn in.

const FAMILY := "jointed"

const BOX_MIN := Vector3(-0.9, -0.1, -0.9)
const BOX_MAX := Vector3(0.9, 0.6, 1.0)
const KNEE_AT := 0.45
const ON_GROUND := 0.6
const STRIDE := 0.05
const LIFT := 0.025
const LEG_LAG := 0.14
const ENROLL_MAX := 5.75
const SHIELD_BEND := 0.5
const SIDE_CURL := 0.9

const BODY := 0
const LEG := 1
const GILL := 2
const EYE := 3
const FEELER := 4
const SHIELD := 5


static func _f(old: Callable, name: StringName, fallback: float) -> float:
	var v: Variant = old.call(name)
	return float(v) if v != null else fallback


static func numbers(old: Callable) -> Dictionary:
	var size := _f(old, &"size", 0.15)
	var venter := _f(old, &"venter", 0.06)
	var head_back := _f(old, &"head_back", -0.12)
	var tail_front := _f(old, &"tail_front", 0.12)
	var y0 := venter * size
	var z0 := 0.5 * (head_back + tail_front) * size
	var half_len := 0.5 * (tail_front - head_back) * size
	var head_len := (head_back + 0.5) * size
	var tail_len := (0.5 - tail_front) * size
	# (its middle at one curvature, the shields beyond at half of it: a bend of the shields alone first, by the
	# difference, then the whole length at the middle's, all of them down: curvature a unit of enroll)
	var kt := ENROLL_MAX / (2.0 * half_len + SHIELD_BEND * (head_len + tail_len))
	var shields := {"type": "bend", "drive": "enroll", "c": kt * (1.0 - SHIELD_BEND), "flags": ["bend_up", "after"],
		"at": Vector3(0.0, y0, z0), "k1": half_len, "k2": 1.0}
	var bend := {"type": "bend", "drive": "enroll", "c": -kt, "flags": ["bend_up", "after"], "at": Vector3(0.0, y0, z0),
		"k1": 0.0, "k2": 1.0}
	# (the lift onto the floor, fitted as l1 * enroll + l2 * enroll^2 through its value at a half and at full)
	var top := _f(old, &"top_height", 0.24)
	var at_half := _lift_at(0.5, size, y0, half_len, head_len, tail_len, top)
	var at_full := _lift_at(1.0, size, y0, half_len, head_len, tail_len, top)
	var l2 := 2.0 * at_full - 4.0 * at_half
	var l1 := at_full - l2
	var stride := {"type": "leg", "drive": "walk", "lag": 2, "per_lag": TAU, "way": Vector3.FORWARD,
		"k1": STRIDE * size, "k2": LIFT * size, "knee_at": KNEE_AT, "ground": ON_GROUND}
	return {
		"ops": [
			stride.merged({"parts": [LEG], "w": 1}, true),
			# (the gill branches only swing about up: by the stride, as the leg under each turns, and by feel)
			{"type": "turn", "parts": [GILL], "drive": "walk", "a": STRIDE * size, "shape": "stride", "ground": ON_GROUND,
				"w": 5, "lag": 2, "per_lag": TAU, "flags": ["own_point", "by_side"], "way": Vector3.UP},
			{"type": "turn", "parts": [GILL], "drive": "feel", "a": 0.3, "lag": 2, "per_lag": TAU,
				"flags": ["own_point", "by_side"], "way": Vector3.UP},
			{"type": "scale", "parts": [LEG, GILL], "drive": "enroll", "c": 1.0, "flags": ["own_point"], "k1": -0.6, "k2": -0.6},
			{"type": "turn", "parts": [FEELER], "drive": "feel", "a": 1.0, "w": 3, "lag": 3, "per_lag": -0.6 * PI,
				"off": 1.0, "side_off": -2.0, "flags": ["own_point", "by_side"], "way": Vector3.UP},
			{"type": "scale", "parts": [FEELER], "drive": "enroll", "c": 1.0, "flags": ["own_point"], "k1": -0.55, "k2": -0.55},
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["own_point"],
				"k1": _f(old, &"eye_grow", 1.6) - 1.0, "k2": _f(old, &"eye_grow", 1.6) - 1.0},
			{"type": "move", "parts": [BODY, EYE, SHIELD], "drive": "enroll", "c": -SIDE_CURL, "w": 4, "way": Vector3.UP},
			# rolled up: behind the middle, then before it (the way reversed), then lifted onto the floor
			shields.merged({"way": Vector3.BACK}, true),
			shields.merged({"way": Vector3.FORWARD}, true),
			bend.merged({"way": Vector3.BACK}, true),
			bend.merged({"way": Vector3.FORWARD}, true),
			{"type": "move", "drive": "enroll", "c": l1, "way": Vector3.UP, "flags": ["after"]},
			{"type": "move", "drive": "enroll", "drive2": "enroll", "c": l2, "way": Vector3.UP, "flags": ["after"]},
		],
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, colour: Color, old: Callable) -> Dictionary:
	var size := _f(old, &"size", 0.15)
	var code := floorf(uv2.y + 0.5)
	var part := int(floorf((code + 0.5) / 16.0))
	var index := code - float(part) * 16.0
	var along := colour.a
	var joint := (BOX_MIN + (BOX_MAX - BOX_MIN) * Vector3(colour.r, colour.g, colour.b)) * size
	var flip := 0.0 if p.x >= 0.0 else 0.5
	var sx := minf(absf(p.x) / size, 0.45)
	# (how far out the foot under a gill branch is: for the swing a stride gives it)
	var knee := Vector3(uv.x, uv.y, uv2.x)
	var reach := Vector2(knee.x - joint.x, knee.z - joint.z).length() / KNEE_AT
	return {"part": part, "point": joint, "way": knee,
		"w": [1.0 if along > 0.5 else 0.0, -LEG_LAG * index + flip, along, sx * sx * size, 1.0 / maxf(reach, 0.0001)]}


# How far the old shader lifted the ball onto the floor, rolled by `enroll` (its `lowest`).
static func _lift_at(enroll: float, size: float, y0: float, half_len: float, head_len: float, tail_len: float, top_height: float) -> float:
	var kt := enroll * ENROLL_MAX / (2.0 * half_len + SHIELD_BEND * (head_len + tail_len))
	var ks := kt * SHIELD_BEND
	var low := maxf(_lowest(half_len + head_len, half_len, kt, ks, top_height * size),
			_lowest(half_len + tail_len, half_len, kt, ks, top_height * size))
	return maxf(low - y0, 0.0)


static func _arc_at(s: float, half_len: float, kt: float, ks: float) -> Vector3:
	var s1 := minf(s, half_len)
	var s2 := maxf(s - half_len, 0.0)
	var t1 := kt * s1
	var r := Vector3(s1, 0.0, t1)
	if kt > 1e-5:
		r.x = sin(t1) / kt
		r.y = (1.0 - cos(t1)) / kt
	if s2 > 0.0:
		var t2 := t1 + ks * s2
		if ks > 1e-5:
			r.x += (sin(t2) - sin(t1)) / ks
			r.y += (cos(t1) - cos(t2)) / ks
		else:
			r.x += cos(t1) * s2
			r.y += sin(t1) * s2
		r.z = t2
	return r


static func _lowest(reach: float, half_len: float, kt: float, ks: float, top: float) -> float:
	var s := reach
	var turn_mid := kt * half_len
	if turn_mid >= PI:
		s = PI / maxf(kt, 1e-5)
	elif turn_mid + ks * (reach - half_len) >= PI:
		s = half_len + (PI - turn_mid) / maxf(ks, 1e-5)
	var r := _arc_at(s, half_len, kt, ks)
	return r.y - top * minf(cos(r.z), 0.0)
