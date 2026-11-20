extends RefCounted
## The sea turtles' motion in the jointed family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## sea_turtle.gdshader moved it: the fore flippers fly (flapped down and up, swept back and forward,
## twisted to feather on the upstroke, the tip a little after the root), the hind flippers trail and steer,
## the shell bobs, the head turns into a turn and tucks back (`tuck`, which also folds the flippers), the
## jaw drops, the whole body pitches with `arch` and banks with `curl`, the cartoon eyes grow. The four types
## (green, hawksbill, loggerhead, leatherback) differ by the settings each type sets, read from its material.
## Differs: the feathering twist was a smoothstep of the stroke; here a sine and a half-sine (within about
## 0.25 rad of it); `sway` is not held to 1.5 at most.

const FAMILY := "jointed"

const SPAN_M := 4.0

# Our parts: the model's groups (UV2.y * 8), an eye's group + 8.
const JAW := 1
const FORE_L := 2
const FORE_R := 3
const HIND_L := 4
const HIND_R := 5
const HEAD := 6
const EYES := [8, 9, 10, 11, 12, 13, 14]


static func _old_or(old: Callable, name: StringName, fallback: Variant) -> Variant:
	var v: Variant = old.call(name)
	return v if v != null else fallback


static func numbers(old: Callable) -> Dictionary:
	var shell_length: float = _old_or(old, &"shell_length", 1.1)
	var neck_pivot: Vector3 = _old_or(old, &"neck_pivot", Vector3(0.0, -0.044, -0.55))
	var tuck_back: float = _old_or(old, &"tuck_back", 0.07)
	var jaw_open: float = _old_or(old, &"jaw_open", 0.55)
	var fore_span: Vector3 = _old_or(old, &"fore_span", Vector3(0.95, -0.11, 0.29))
	var eye_mid: Vector3 = _old_or(old, &"eye_mid", Vector3(0.04, -0.019, -0.654))
	var eye_out: Vector3 = _old_or(old, &"eye_out", Vector3(0.8975, 0.389, -0.2078))
	var eye_sag: float = _old_or(old, &"eye_sag", 0.002)
	var eye_grow: float = _old_or(old, &"eye_grow", 1.7)
	var x := Vector3.RIGHT
	var y := Vector3.UP
	var z := Vector3.BACK
	var fore := [FORE_L, FORE_R]
	var hind := [HIND_L, HIND_R]
	var neck := [JAW, HEAD, JAW + 8, HEAD + 8]
	# the fore stroke: w = TAU (phase - 0.07 along), go = sway (1 - 0.5 tuck): each sway term twice, the
	# second times tuck at -0.5
	var stroke := {"parts": fore, "type": "turn", "lag": 3, "per_lag": -0.07 * TAU, "flags": ["mirror", "own_point"]}
	var ops: Array = [
		# the eyes: grown about their middle, the rim sagging
		{"type": "scale", "parts": EYES, "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
			"at": eye_mid, "way": eye_out, "k1": eye_grow - 1.0, "k2": eye_grow - 1.0},
		{"type": "move", "parts": EYES, "drive": "cartoon_eyes", "c": -(eye_grow * eye_grow - eye_grow) * eye_sag, "w": 5,
			"flags": ["mirror"], "way": eye_out},
		{"type": "turn", "parts": [JAW, JAW + 8], "drive": "gape", "c": -jaw_open, "w": 1, "flags": ["own_point"], "way": x},
		# the neck: turned into the turn, raised by the arch, tucked back
		{"type": "turn", "parts": neck, "drive": "curl", "c": -0.45, "w": 2, "at": neck_pivot, "way": y},
		{"type": "turn", "parts": neck, "drive": "arch", "c": -0.3, "plus": -0.25, "drive3": "tuck", "w": 2, "at": neck_pivot, "way": x},
		{"type": "move", "parts": neck, "drive": "tuck", "c": tuck_back, "way": Vector3(0.0, -0.12, 1.0)},
		# fore flippers, worked out on the +x side: twist about the span (feathering: 0.1279 + 0.3892 u
		# + 0.7372 max(u, 0), u = -sin(w - 0.25)), flap about z, sweep about y (the -x side mirrors them)
		stroke.merged({"drive": "sway", "c": 0.1279, "a": 0.3892, "off": PI - 0.25, "w": 4, "way": fore_span}, true),
		stroke.merged({"drive": "sway", "a": 0.7372, "shape": "upper", "off": PI - 0.25, "w": 4, "way": fore_span}, true),
		stroke.merged({"drive": "sway", "drive2": "tuck", "c": -0.064, "a": -0.1946, "off": PI - 0.25, "w": 4, "way": fore_span}, true),
		stroke.merged({"drive": "sway", "drive2": "tuck", "a": -0.3686, "shape": "upper", "off": PI - 0.25, "w": 4, "way": fore_span}, true),
		stroke.merged({"drive": "sway", "c": -0.05, "a": 0.6, "off": 0.5 * PI, "plus": -0.15, "drive3": "tuck", "way": z}, true),
		stroke.merged({"drive": "sway", "drive2": "tuck", "c": 0.025, "a": -0.3, "off": 0.5 * PI, "way": z}, true),
		stroke.merged({"drive": "sway", "c": -0.05, "a": 0.42, "off": 0.5 * PI - 0.5, "plus": -0.55, "drive3": "tuck", "way": y}, true),
		stroke.merged({"drive": "sway", "drive2": "tuck", "c": 0.025, "a": -0.21, "off": 0.5 * PI - 0.5, "way": y}, true),
		# hind flippers: lifted with the stroke and by the arch, steered by the curl, splayed as it tucks
		{"type": "turn", "parts": hind, "drive": "sway", "a": -0.14, "off": -0.6 * PI, "w": 4, "flags": ["own_point"], "way": x},
		{"type": "turn", "parts": hind, "drive": "sway", "drive2": "tuck", "a": 0.07, "off": -0.6 * PI, "w": 4, "flags": ["own_point"], "way": x},
		{"type": "turn", "parts": hind, "drive": "arch", "c": -0.5, "flags": ["own_point"], "way": x},
		{"type": "turn", "parts": hind, "drive": "curl", "c": 0.6, "flags": ["own_point"], "way": y},
		{"type": "turn", "parts": hind, "drive": "tuck", "c": -0.3, "flags": ["own_point", "by_side"], "way": y},
		# the shell's bob, then the whole body pitched and banked
		{"type": "move", "drive": "sway", "a": 0.008 * shell_length, "off": -0.3 * PI, "way": y, "flags": ["after"]},
		{"type": "move", "drive": "sway", "drive2": "tuck", "a": -0.004 * shell_length, "off": -0.3 * PI, "way": y, "flags": ["after"]},
		{"type": "turn", "drive": "arch", "c": -0.4, "way": x, "flags": ["after"]},
		{"type": "turn", "drive": "curl", "c": -0.5, "way": z, "flags": ["after"]},
	]
	return {"ops": ops}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, colour: Color, old: Callable) -> Dictionary:
	var group := int(uv2.y * 8.0 + 0.5)
	var kind := floorf(colour.r * 10.0 + 0.5)
	var extra := Vector2(colour.g, colour.b)
	var hinge := (Vector3(uv2.x, uv.y, uv.x) - Vector3(0.5, 0.5, 0.5)) * SPAN_M
	var part := group + (8 if kind == 1.0 else 0)
	var mouth_corner: float = _old_or(old, &"mouth_corner", -0.64)
	var neck_front: float = _old_or(old, &"neck_front", -0.55)
	var neck_back: float = _old_or(old, &"neck_back", -0.46)
	var jaw := 1.0 - smoothstep(mouth_corner, hinge.z, p.z) if group == JAW else 0.0
	var neck := 1.0 - smoothstep(neck_front, neck_back, p.z)
	var along := extra.y
	var swing := 0.0
	if group == FORE_L or group == FORE_R:
		swing = smoothstep(0.0, 0.35, along)
	elif group == HIND_L or group == HIND_R:
		swing = smoothstep(0.0, 0.6, extra.y)
	return {"part": part, "w": [jaw, neck, along, swing, extra.y * extra.y], "point": hinge}
