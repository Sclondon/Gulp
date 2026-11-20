extends RefCounted
## The spinosaurus's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## spinosaurus.gdshader moved it: the side-to-side wave along its body and tail (weaker, by 0.6 of it, as it
## wades: done here by moves, each point turned about its place on the middle line and carried sideways),
## the turning curl, the jaw dropping and the snout lifting as it gapes, wading (`wade`: arms and legs
## folded down at shoulder, elbow, wrist, hip, knee and ankle, the neck raised and the head tipped), the
## cartoon eyes grown (bulging out over a sagging rim). Numbers from spinosaurus.gdshader.

const FAMILY := "swim"

const LENGTH := 14.0
const HALF := 7.0
const CORNER := 1.45
const HINGE_Y := -0.066
const HINGE_SPREAD := 0.22
const SHOULDER := Vector2(3.72, -0.55)
const ELBOW := Vector2(4.18, -0.86)
const WRIST := Vector2(4.62, -0.9)
const AT_ELBOW := 0.558
const AT_WRIST := 1.0
const HIP := Vector2(5.85, -0.38)
const KNEE := Vector2(6.58, -0.64)
const ANKLE := Vector2(7.22, -0.58)
const AT_KNEE := 0.873
const AT_ANKLE := 1.516
const WADE_ARM := Vector3(1.15, 1.03, 0.35)
const WADE_LEG := Vector3(1.45, -0.14, 1.95)
const WADE_NECK := 0.42
const WADE_HEAD := -0.3
const GAPE_MAX := 0.95
const LIFT_MAX := 0.12
const REACH := 0.07
const EYE_CENTRE := Vector3(0.09325, 0.17, -5.8)
const EYE_OUT := Vector3(0.8195, 0.5197, -0.2417)
const EYE_FWD := Vector3(-0.2041, -0.1295, -0.9703)
const EYE_UP := Vector3(-0.5356, 0.8445, 0.0)
const EYE_SAG := 1.8675
const EYE_GROW := 2.4

const JAW := 1
const JAW_B := 3
const ARM := 5
const LEG := 6
const EYE := 7


# (a hinge's place, from the old shader's (metres behind the snout, height) pair)
static func _at(pivot: Vector2) -> Vector3:
	return Vector3(0.0, pivot.y, pivot.x - HALF)


static func numbers(old: Callable) -> Dictionary:
	var got: Variant = old.call(&"wave")
	var wave: float = got if got != null else 0.9
	var rest: Array = []
	for i in 24:
		if i != ARM and i != LEG:
			rest.append(i)
	var hinge := _at(Vector2(CORNER, HINGE_Y))
	var wave_op := {"drive": "sway", "beat": "tail_beats", "per_s": -TAU / wave}
	return {
		"motion_length": LENGTH, "motion_nose": -HALF,
		"env_poly": Vector4.ZERO, "env_pow": Vector3(0.0, 0.0, 2.0),
		"swim_from": -10.0, "swim_joint": 10.0, "swim_wrist": 0.0,
		"swim_curl_from": 2.5 - HALF, "swim_curl_span": LENGTH - 2.5,
		"ops": [
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": EYE_CENTRE, "way": EYE_OUT, "k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0},
			{"type": "move", "parts": [EYE], "drive": "cartoon_eyes", "c": EYE_SAG * (EYE_GROW - EYE_GROW * EYE_GROW), "w": 7,
				"flags": ["mirror"], "way": EYE_OUT},
			{"type": "turn", "parts": [JAW, JAW_B], "drive": "gape", "c": -GAPE_MAX, "w": 1, "at": hinge, "way": Vector3.RIGHT},
			{"type": "turn", "parts": [0, 2, EYE], "drive": "gape", "c": LIFT_MAX, "w": 1, "at": hinge, "way": Vector3.RIGHT},
			{"type": "turn", "parts": [ARM], "drive": "wade", "c": WADE_ARM.z, "w": 2, "at": _at(WRIST), "way": Vector3.RIGHT},
			{"type": "turn", "parts": [ARM], "drive": "wade", "c": WADE_ARM.y, "w": 3, "at": _at(ELBOW), "way": Vector3.RIGHT},
			{"type": "turn", "parts": [ARM], "drive": "wade", "c": WADE_ARM.x, "at": _at(SHOULDER), "way": Vector3.RIGHT},
			{"type": "turn", "parts": [LEG], "drive": "wade", "c": WADE_LEG.z, "w": 2, "at": _at(ANKLE), "way": Vector3.RIGHT},
			{"type": "turn", "parts": [LEG], "drive": "wade", "c": WADE_LEG.y, "w": 3, "at": _at(KNEE), "way": Vector3.RIGHT},
			{"type": "turn", "parts": [LEG], "drive": "wade", "c": WADE_LEG.x, "at": _at(HIP), "way": Vector3.RIGHT},
			{"type": "turn", "parts": rest, "drive": "wade", "c": WADE_HEAD, "w": 2, "at": _at(Vector2(1.7, 0.0)), "way": Vector3.RIGHT},
			{"type": "turn", "parts": rest, "drive": "wade", "c": WADE_NECK, "w": 3, "at": _at(Vector2(3.0, 0.05)), "way": Vector3.RIGHT},
			# the wave (1 - 0.6 wade of it): turned about the middle line by the slope, then carried sideways
			wave_op.merged({"type": "turn", "a": 1.0, "w": 4, "lag": 6, "per_lag": 1.0, "flags": ["own_point"], "way": Vector3.UP}, true),
			wave_op.merged({"type": "turn", "drive2": "wade", "a": -0.6, "w": 4, "lag": 6, "per_lag": 1.0, "flags": ["own_point"],
				"way": Vector3.UP}, true),
			wave_op.merged({"type": "move", "a": 1.0, "w": 5, "way": Vector3.RIGHT}, true),
			wave_op.merged({"type": "move", "drive2": "wade", "a": -0.6, "w": 5, "way": Vector3.RIGHT}, true),
		],
	}


static func label(p: Vector3, _n: Vector3, _uv: Vector2, uv2: Vector2, _colour: Color, old: Callable) -> Dictionary:
	var part := int(uv2.y + 0.5)
	var xm := p.z + HALF
	var along := uv2.x
	var got: Variant = old.call(&"wave")
	var wave: float = got if got != null else 0.9
	var jaw := 0.0
	if part == JAW or part == JAW_B:
		jaw = smoothstep(CORNER + 0.04, CORNER - HINGE_SPREAD, xm)
	elif part == 0 or part == 2 or part == EYE:
		jaw = smoothstep(CORNER + 0.45, CORNER - 0.1, xm) * smoothstep(HINGE_Y - 0.1, HINGE_Y + 0.04, p.y)
	var w2 := 0.0
	var w3 := 0.0
	if part == ARM:
		w2 = smoothstep(AT_WRIST - 0.04, AT_WRIST + 0.04, along)
		w3 = smoothstep(AT_ELBOW - 0.05, AT_ELBOW + 0.05, along)
	elif part == LEG:
		w2 = smoothstep(AT_ANKLE - 0.04, AT_ANKLE + 0.06, along)
		w3 = smoothstep(AT_KNEE - 0.06, AT_KNEE + 0.06, along)
	else:
		w2 = smoothstep(1.95, 1.45, xm)
		w3 = smoothstep(3.3, 2.3, xm)
	# the wave: h = f(s) sin(phi), f = L REACH P(s); its slope REACH P'(s) sin(phi) - f (TAU / (wave L)) cos(phi)
	var s := xm / LENGTH
	var f := LENGTH * REACH * (0.06 - 0.34 * s + 0.6 * s * s + 0.62 * s * s * s)
	var a := REACH * (-0.34 + 1.2 * s + 1.86 * s * s)
	var b := -f * TAU / (wave * LENGTH)
	var r2 := 0.0
	if part == EYE:
		var m := Vector3(signf(p.x) if p.x != 0.0 else 1.0, 1.0, 1.0)
		var d := p - EYE_CENTRE * m
		var pl := Vector2(d.dot(EYE_FWD * m), d.dot(EYE_UP * m))
		r2 = pl.dot(pl)
	return {"part": part, "w": [jaw, w2, w3, sqrt(a * a + b * b), f, atan2(b, a), r2], "point": Vector3(0.0, 0.0, p.z)}
