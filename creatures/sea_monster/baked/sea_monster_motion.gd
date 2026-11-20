extends RefCounted
## The sea monster shader's motion in the swim family (scripts/motion.gd; GameCommon
## `godot/motion-families`), as sea_monster.gdshader moved the two that wear it (the leviathan and the sea
## serpent, which differ only by the shape settings each sends: read from the material): the wave side to
## side along the body to a one-plate tail; the serpent's humps, a second wave up and down (done here by
## moves: each point tipped about its place on the middle line and lifted); its fins' flap and trailing
## ripple; ropes and weed hanging from it swaying; the jaw dropping and the snout lifting as it gapes; the
## tail coiling up (`coil`); rearing (`rear`); the turning curl (after the coil, as the old shader had it);
## the cartoon eyes grown.
## Differs: rearing and coiling bend along an arc that runs on to the end of the body, where the old shader
## bent only `span` metres and carried the rest straight (the coil's tail end curls a little further; the
## rear's head would curl far too far: the game sets neither); the humps do not stop at the tail's joint.

const FAMILY := "swim"

const ROPE := 10
const WEED := 5
const FIN := 6
const FIN_SIDE := 4
const JAW := 1
const JAW_B := 3
const EYE := 7


static func _old_or(old: Callable, name: StringName, fallback: Variant) -> Variant:
	var v: Variant = old.call(name)
	return v if v != null else fallback


static func numbers(old: Callable) -> Dictionary:
	var length: float = _old_or(old, &"body_length", 40.0)
	var half := length * 0.5
	var joint: float = _old_or(old, &"joint", 37.2)
	var corner: float = _old_or(old, &"corner", 10.2)
	var hinge_y: float = _old_or(old, &"hinge_y", -1.5)
	var gape_max: float = _old_or(old, &"gape_max", 1.05)
	var lift_max: float = _old_or(old, &"lift_max", 0.2)
	var reach: float = _old_or(old, &"reach", 0.05)
	var poly: Vector4 = _old_or(old, &"reach_poly", Vector4(0.05, -0.3, 0.6, 0.6))
	var hump_wave: float = _old_or(old, &"hump_wave", 0.45)
	var flap: float = _old_or(old, &"flap", 0.6)
	var trail: float = _old_or(old, &"trail", 0.25)
	var eye_centre: Vector3 = _old_or(old, &"eye_centre", Vector3(2.6, 1.2, -13.0))
	var eye_out: Vector3 = _old_or(old, &"eye_out", Vector3.RIGHT)
	var eye_sag: float = _old_or(old, &"eye_sag", 0.08)
	var eye_grow: float = _old_or(old, &"eye_grow", 2.0)
	var rear_max: float = _old_or(old, &"rear_max", 1.1)
	var hinge := Vector3(0.0, hinge_y, corner - half)
	var body: Array = []
	for i in 24:
		if not i in [ROPE, WEED, FIN, FIN_SIDE]:
			body.append(i)
	var bend_rear := func(at: float, span: float, k: float) -> Dictionary:
		return {"type": "bend", "drive": "rear", "c": k * rear_max, "flags": ["bend_up"],
			"at": Vector3(0.0, 0.0, at - half), "way": Vector3.FORWARD, "k1": 0.0, "k2": span}
	return {
		"motion_length": length, "motion_nose": -half,
		"env_poly": poly * reach,
		"swim_from": -10.0, "swim_joint": joint / length, "swim_wrist": 0.0,
		# (the curl is a move of its own, after the coil; the family's own is kept off)
		"swim_curl_from": 1.0e9, "swim_curl_span": 0.7 * length,
		"ops": [
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": eye_centre, "way": eye_out, "k1": eye_grow - 1.0, "k2": eye_grow - 1.0},
			{"type": "move", "parts": [EYE], "drive": "cartoon_eyes", "c": eye_sag * (eye_grow - eye_grow * eye_grow), "w": 4,
				"flags": ["mirror"], "way": eye_out},
			# ropes and weed
			{"type": "move", "parts": [ROPE, WEED], "a": 1.0, "w": 2, "lag": 3, "per_lag": 1.0, "way": Vector3.RIGHT},
			{"type": "move", "parts": [ROPE, WEED], "a": 0.35, "off": 1.3, "w": 2, "lag": 3, "per_lag": 1.0, "way": Vector3.UP},
			# fins: the flap and the trailing ripple
			{"type": "move", "parts": [FIN], "a": flap, "off": 0.6, "w": 2, "way": Vector3.UP},
			{"type": "move", "parts": [FIN], "a": trail, "w": 4, "lag": 3, "per_lag": 1.0, "way": Vector3.UP},
			{"type": "move", "parts": [FIN_SIDE], "a": trail, "w": 2, "lag": 3, "per_lag": 1.0, "way": Vector3.RIGHT},
			# jaw and snout
			{"type": "turn", "parts": [JAW, JAW_B], "drive": "gape", "c": -gape_max, "w": 1, "at": hinge, "way": Vector3.RIGHT},
			{"type": "turn", "parts": [0, 2, EYE, 8, WEED, 11], "drive": "gape", "c": lift_max, "w": 1, "at": hinge, "way": Vector3.RIGHT},
			# rearing up: the head kept level, the neck, the body raised from rear_at forward
			bend_rear.call(float(_old_or(old, &"head_at", 2.6)), float(_old_or(old, &"head_span", 1.0)), -float(_old_or(old, &"head_keep", 0.9))),
			bend_rear.call(float(_old_or(old, &"neck_at", 4.2)), float(_old_or(old, &"neck_span", 1.4)), -float(_old_or(old, &"neck_keep", 0.0))),
			bend_rear.call(float(_old_or(old, &"rear_at", 8.0)), float(_old_or(old, &"rear_span", 5.0)), 1.0),
			# the humps (humps * hump_height * e(s) * sin): each point tipped by the slope, then lifted
			{"type": "turn", "drive": "humps", "a": -1.0, "w": 6, "lag": 7, "per_lag": 1.0, "per_s": -TAU / hump_wave,
				"flags": ["own_point"], "way": Vector3.RIGHT},
			# (lifted by where it was before it was tipped: from its place at rest; the hanging and fin parts, whose
			# weight 3 is their own ripple's, by where it is)
			{"type": "move", "parts": body, "drive": "humps", "a": 1.0, "w": 5, "lag": 3, "per_lag": 1.0, "way": Vector3.UP},
			{"type": "move", "parts": [ROPE, WEED, FIN, FIN_SIDE], "drive": "humps", "a": 1.0, "w": 5, "per_s": -TAU / hump_wave, "way": Vector3.UP},
			# after the swimming: the coil, then the curl
			{"type": "bend", "drive": "coil", "c": float(_old_or(old, &"coil_max", 3.0)), "flags": ["bend_up", "after"],
				"at": Vector3(0.0, 0.0, float(_old_or(old, &"coil_at", 27.0)) - half), "way": Vector3.BACK,
				"k1": 0.0, "k2": float(_old_or(old, &"coil_span", 11.0))},
			{"type": "bend", "drive": "curl", "c": 1.0, "flags": ["after"], "at": Vector3.ZERO, "way": Vector3.BACK,
				"k1": -0.3 * length, "k2": 0.7 * length},
		],
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, old: Callable) -> Dictionary:
	var part := int(uv2.y + 0.5)
	var length: float = _old_or(old, &"body_length", 40.0)
	var half := length * 0.5
	var xm := p.z + half
	var corner: float = _old_or(old, &"corner", 10.2)
	var hinge_y: float = _old_or(old, &"hinge_y", -1.5)
	var spread: float = _old_or(old, &"hinge_spread", 1.2)
	var jaw := 0.0
	if part == JAW or part == JAW_B:
		jaw = smoothstep(corner + 0.04 * spread, corner - spread, xm)
	elif part in [0, 2, EYE, 8, WEED, 11]:
		jaw = smoothstep(corner + 2.0 * spread, corner - 0.2 * spread, xm) * smoothstep(hinge_y - 0.1 * spread, hinge_y + 0.05 * spread, p.y)
	var w2 := 0.0
	var lag := 0.0
	var w4 := 0.0
	if part == ROPE or part == WEED:
		w2 = float(_old_or(old, &"rope_sway" if part == ROPE else &"weed_sway", 1.0)) * uv.x * uv.x
		lag = -1.6 * PI * uv.x + 0.15 * p.z
	elif part == FIN:
		w2 = uv.x * uv.x
		w4 = uv.x * uv.y
		lag = -PI * uv.y
	elif part == FIN_SIDE:
		w2 = uv.x * uv.y
		lag = -PI * uv.y + 0.2 * p.z
	if part == EYE:
		var m := Vector3(signf(p.x) if p.x != 0.0 else 1.0, 1.0, 1.0)
		var centre: Vector3 = _old_or(old, &"eye_centre", Vector3(2.6, 1.2, -13.0))
		var d := p - centre * m
		var fwd: Vector3 = _old_or(old, &"eye_fwd", Vector3.FORWARD)
		var up: Vector3 = _old_or(old, &"eye_up", Vector3.UP)
		var pl := Vector2(d.dot(fwd * m), d.dot(up * m))
		w4 = pl.dot(pl)
	# the humps: up = H e(xm) sin(phi), e = smoothstep(from, from + rise, xm) (1 - 0.3 s); its slope
	# H (e' sin(phi) - e TAU / (L hump_wave) cos(phi))
	var height: float = _old_or(old, &"hump_height", 0.0)
	var from: float = _old_or(old, &"hump_from", 6.0)
	var rise: float = _old_or(old, &"hump_rise", 4.0)
	var hump_wave: float = _old_or(old, &"hump_wave", 0.45)
	var s := xm / length
	var sm := smoothstep(from, from + rise, xm)
	var t := clampf((xm - from) / rise, 0.0, 1.0)
	var dsm := 6.0 * t * (1.0 - t) / rise if xm > from and xm < from + rise else 0.0
	var e := sm * (1.0 - 0.3 * s)
	var de := dsm * (1.0 - 0.3 * s) - sm * 0.3 / length
	var a := height * de
	var b := -height * e * TAU / (length * hump_wave)
	if not part in [ROPE, WEED, FIN, FIN_SIDE]:
		lag = -TAU * s / hump_wave
	return {"part": part, "w": [jaw, w2, lag, w4, height * e, sqrt(a * a + b * b), atan2(b, a)], "point": Vector3(0.0, 0.0, p.z)}
