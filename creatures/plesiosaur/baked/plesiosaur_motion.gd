extends RefCounted
## The plesiosaur's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## plesiosaur.gdshader moved it: four flippers rowing (each feathered about its span, flapped about its
## chord, swept fore and aft; the hind pair half a beat after the fore), the short tail swinging, the
## jaw dropping, the long neck bent round into a turn with 0.7 of the curl (the tail the rest), the cartoon
## eyes grown. Numbers from plesiosaur.gdshader. Differs: the neck's arc runs on through the head (the old
## shader bent only the neck and carried the head straight on: the head turns a little further, about
## 0.2 rad at full curl); `neck` (aim the head, which the game does not set) is read once as it is dressed.

const FAMILY := "swim"

const LENGTH := 9.0
const HALF := 4.5
const NECK_BASE := 4.6
const HEAD_END := 0.5
const HIPS := 7.4
const CORNER := 0.42
const HINGE_Y := -0.0206
const HINGE_SPREAD := 0.03
const GAPE_MAX := 0.75
const NECK_MAX := Vector2(1.2, 0.9)
const CURL_NECK := 0.7
const FLAP := 0.45
const SWEEP := 0.2
const FEATHER := 0.5
const HIND_LAG := 0.5
const TAIL_SWING := 0.14
const FORE_ROOT := Vector3(0.4367, -0.32, 0.8)
const FORE_SPAN := Vector3(0.9322, -0.2051, 0.2983)
const FORE_CHORD := Vector3(-0.2933, 0.0549, 0.9544)
const HIND_ROOT := Vector3(0.4339, -0.3, 2.45)
const HIND_SPAN := Vector3(0.9036, -0.1988, 0.3795)
const HIND_CHORD := Vector3(-0.3727, 0.0721, 0.9251)
const EYE_CENTRE := Vector3(0.07922, 0.034, -4.19)
const EYE_OUT := Vector3(0.9098, 0.3756, -0.1767)
const EYE_FWD := Vector3(-0.1634, -0.0674, -0.9843)
const EYE_UP := Vector3(-0.3816, 0.9243, 0.0)
const EYE_SAG := 2.5851
const EYE_GROW := 1.6

const JAW := 1
const JAW_B := 3
const FORE := 6
const EYE := 7
const HIND := 8


static func numbers(old: Callable) -> Dictionary:
	var neck: Variant = old.call(&"neck")
	var aim: Vector2 = neck if neck is Vector2 else Vector2.ZERO
	var ops: Array = [
		{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
			"at": EYE_CENTRE, "way": EYE_OUT, "k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0},
		{"type": "move", "parts": [EYE], "drive": "cartoon_eyes", "c": EYE_SAG * (EYE_GROW - EYE_GROW * EYE_GROW), "w": 7,
			"flags": ["mirror"], "way": EYE_OUT},
		{"type": "turn", "parts": [JAW, JAW_B], "drive": "gape", "c": -GAPE_MAX, "w": 1,
			"at": Vector3(0.0, HINGE_Y, CORNER - HALF), "way": Vector3.RIGHT},
	]
	# each flipper: feathered (cos), flapped (its tip lagging, bent more), swept (twice a beat)
	for f in [[FORE, FORE_ROOT, FORE_SPAN, FORE_CHORD, 0.0], [HIND, HIND_ROOT, HIND_SPAN, HIND_CHORD, -TAU * HIND_LAG]]:
		var base := {"parts": [f[0]], "type": "turn", "drive": "sway", "flags": ["mirror"], "at": f[1]}
		ops.append(base.merged({"a": FEATHER, "off": f[4] + 0.5 * PI, "way": f[2]}, true))
		ops.append(base.merged({"a": FLAP, "off": f[4], "w": 2, "lag": 3, "per_lag": -0.25, "way": f[3]}, true))
		ops.append(base.merged({"a": SWEEP, "beats": 2.0, "off": 2.0 * f[4], "way": Vector3.UP}, true))
	ops.append_array([
		{"type": "move", "drive": "sway", "a": TAIL_SWING, "w": 4, "lag": 5, "per_lag": -0.6 * PI, "way": Vector3.RIGHT},
		# the neck: bent sideways by the curl's share (and the aim), up by the aim; after the tail's swing
		{"type": "bend", "drive": "curl", "c": -CURL_NECK, "plus": -NECK_MAX.x * aim.x, "flags": ["after", "ends"],
			"at": Vector3(0.0, 0.0, NECK_BASE - HALF), "way": Vector3.FORWARD, "k1": 0.0, "k2": NECK_BASE - HEAD_END},
		{"type": "bend", "c": NECK_MAX.y * aim.y, "flags": ["after", "bend_up", "ends"],
			"at": Vector3(0.0, 0.0, NECK_BASE - HALF), "way": Vector3.FORWARD, "k1": 0.0, "k2": NECK_BASE - HEAD_END},
	])
	return {
		"motion_length": LENGTH, "motion_nose": -HALF,
		"env_poly": Vector4.ZERO, "env_pow": Vector3(0.0, 0.0, 2.0),
		"swim_from": -10.0, "swim_joint": 10.0, "swim_wrist": 0.0,
		# (the tail gets 1 - CURL_NECK of the curl)
		"swim_curl_from": HIPS - HALF, "swim_curl_span": (LENGTH - HIPS) / (1.0 - CURL_NECK),
		"ops": ops,
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, _old: Callable) -> Dictionary:
	var part := int(uv2.y + 0.5)
	var xm := p.z + HALF
	var jaw := smoothstep(CORNER + 0.01, CORNER - HINGE_SPREAD, xm) if part == JAW or part == JAW_B else 0.0
	var t := uv.x if part == FORE or part == HIND else 0.0
	var s := clampf((xm - HIPS) / (LENGTH - HIPS), 0.0, 1.0)
	var r2 := 0.0
	if part == EYE:
		var m := Vector3(signf(p.x) if p.x != 0.0 else 1.0, 1.0, 1.0)
		var d := p - EYE_CENTRE * m
		var pl := Vector2(d.dot(EYE_FWD * m), d.dot(EYE_UP * m))
		r2 = pl.dot(pl)
	return {"part": part, "w": [jaw, 1.0 + 0.25 * t, t, s * s, s, 0.0, r2]}
