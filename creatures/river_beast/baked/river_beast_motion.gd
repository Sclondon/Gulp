extends RefCounted
## The river beast's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## river_beast.gdshader moved it: swimming, its tail waves side to side and its hind feet kick (each side
## half a beat after the other, the ankle flexing after the hip); standing (`stand`), it rears up on its
## hind legs: body tipped up about the hips, legs, arms, neck and tail folded at their joints; the jaw drops
## and the snout lifts as it gapes; the turning curl; the cartoon eyes grown. Numbers from
## river_beast.gdshader. Differs: the fur clumps' normals are as the model has them (the old shader turned them
## outward each frame, so the fur's light is a little different).

const FAMILY := "swim"

const LENGTH := 3.93
const HALF := 1.965
const CORNER := 0.58
const HINGE_Y := -0.012
const HINGE_SPREAD := 0.1
const SHOULDER := Vector2(1.26, -0.26)
const ELBOW := Vector2(1.58, -0.44)
const WRIST := Vector2(1.9, -0.46)
const AT_ELBOW := 0.3758
const AT_WRIST := 0.6965
const HIP := Vector2(2.28, -0.13)
const KNEE := Vector2(2.73, -0.31)
const ANKLE := Vector2(3.13, -0.29)
const AT_KNEE := 0.5383
const AT_ANKLE := 0.939
const STAND_ARM := Vector3(-0.05, 1.22, -0.87)
const STAND_LEG := Vector3(1.31, 0.1, 1.8)
const STAND_BODY := 1.36
const NECK := Vector2(0.8, 0.0)
const STAND_HEAD := -1.42
const TAIL_ROOT := Vector2(2.42, -0.05)
const STAND_TAIL := 1.15
const TAIL_MID := Vector2(2.85, -0.02)
const STAND_TAIL_MID := -0.62
const GAPE_MAX := 0.85
const LIFT_MAX := 0.14
const EYE_CENTRE := Vector3(0.149, 0.112, -1.475)
const EYE_OUT := Vector3(0.6413, 0.7464, -0.1778)
const EYE_FWD := Vector3(-0.1158, -0.1348, -0.9841)
const EYE_UP := Vector3(-0.7585, 0.6517, 0.0)
const EYE_SAG := 2.5903
const EYE_GROW := 2.2

const JAW := 1
const JAW_B := 3
const ARM := 5
const LEG := 6
const EYE := 7


static func _at(pivot: Vector2) -> Vector3:
	return Vector3(0.0, pivot.y, pivot.x - HALF)


static func numbers(old: Callable) -> Dictionary:
	var got: Variant = old.call(&"wave")
	var wave: float = got if got != null else 0.7
	var not_legs: Array = []
	var body: Array = []
	for i in 24:
		if i != LEG:
			not_legs.append(i)
			if i != ARM:
				body.append(i)
	var hinge := _at(Vector2(CORNER, HINGE_Y))
	var x := Vector3.RIGHT
	return {
		"motion_length": LENGTH, "motion_nose": -HALF,
		"env_poly": Vector4.ZERO, "env_pow": Vector3(0.0, 0.0, 2.0),
		"swim_from": -10.0, "swim_joint": 10.0, "swim_wrist": 0.0,
		# (the curl is a move of its own, after: curl * (1 - stand); the family's own curl is kept off)
		"swim_curl_from": 1.0e6, "swim_curl_span": LENGTH - 0.8,
		"ops": [
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": EYE_CENTRE, "way": EYE_OUT, "k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0},
			{"type": "move", "parts": [EYE], "drive": "cartoon_eyes", "c": EYE_SAG * (EYE_GROW - EYE_GROW * EYE_GROW), "w": 7,
				"flags": ["mirror"], "way": EYE_OUT},
			{"type": "turn", "parts": [JAW, JAW_B], "drive": "gape", "c": -GAPE_MAX, "w": 1, "at": hinge, "way": x},
			{"type": "turn", "parts": [0, 2, EYE], "drive": "gape", "c": LIFT_MAX, "w": 1, "at": hinge, "way": x},
			# the tail's wave: sideways only (and before the joints turn: they turn in the upright plane)
			{"type": "move", "parts": not_legs, "drive": "sway", "a": 1.0, "beat": "tail_beats", "per_s": -TAU / wave, "w": 2, "way": x},
			# the hind legs: kick and flex while swimming (1 - stand of it), fold as it stands
			{"type": "turn", "parts": [LEG], "drive": "stand", "c": STAND_LEG.z, "w": 3, "at": _at(ANKLE), "way": x},
			{"type": "turn", "parts": [LEG], "drive": "sway", "a": 0.5, "off": -1.2, "side_off": PI, "beat": "tail_beats", "w": 3,
				"at": _at(ANKLE), "way": x},
			{"type": "turn", "parts": [LEG], "drive": "sway", "drive2": "stand", "a": -0.5, "off": -1.2, "side_off": PI,
				"beat": "tail_beats", "w": 3, "at": _at(ANKLE), "way": x},
			{"type": "turn", "parts": [LEG], "drive": "stand", "c": STAND_LEG.y, "w": 4, "at": _at(KNEE), "way": x},
			{"type": "turn", "parts": [LEG], "drive": "stand", "c": STAND_LEG.x, "at": _at(HIP), "way": x},
			{"type": "turn", "parts": [LEG], "drive": "sway", "a": 0.38, "side_off": PI, "beat": "tail_beats", "at": _at(HIP), "way": x},
			{"type": "turn", "parts": [LEG], "drive": "sway", "drive2": "stand", "a": -0.38, "side_off": PI, "beat": "tail_beats",
				"at": _at(HIP), "way": x},
			# the arms fold
			{"type": "turn", "parts": [ARM], "drive": "stand", "c": STAND_ARM.z, "w": 3, "at": _at(WRIST), "way": x},
			{"type": "turn", "parts": [ARM], "drive": "stand", "c": STAND_ARM.y, "w": 4, "at": _at(ELBOW), "way": x},
			{"type": "turn", "parts": [ARM], "drive": "stand", "c": STAND_ARM.x, "at": _at(SHOULDER), "way": x},
			# the head, the tail
			{"type": "turn", "parts": body, "drive": "stand", "c": STAND_HEAD, "w": 3, "at": _at(NECK), "way": x},
			{"type": "turn", "parts": body, "drive": "stand", "c": STAND_TAIL_MID, "w": 4, "at": _at(TAIL_MID), "way": x},
			{"type": "turn", "parts": body, "drive": "stand", "c": STAND_TAIL, "w": 5, "at": _at(TAIL_ROOT), "way": x},
			# the body tipped up about the hips (breathing a little)
			{"type": "turn", "parts": not_legs, "drive": "stand", "c": STAND_BODY, "w": 6, "at": _at(HIP), "way": x},
			{"type": "turn", "parts": not_legs, "drive": "stand", "a": 0.025, "beat": "tail_beats", "w": 6, "at": _at(HIP), "way": x},
			{"type": "bend", "drive": "curl", "drive2": "stand", "c": -1.0, "plus": 1.0, "drive3": "curl", "flags": ["after"],
				"at": Vector3.ZERO, "way": Vector3.BACK, "k1": 0.8 - HALF, "k2": LENGTH - 0.8},
		],
	}


static func label(p: Vector3, _n: Vector3, _uv: Vector2, uv2: Vector2, _colour: Color, old: Callable) -> Dictionary:
	var part := int(uv2.y + 0.5)
	var xm := p.z + HALF
	var along := uv2.x
	var jaw := 0.0
	if part == JAW or part == JAW_B:
		jaw = smoothstep(CORNER + 0.03, CORNER - HINGE_SPREAD, xm)
	elif part == 0 or part == 2 or part == EYE:
		jaw = smoothstep(CORNER + 0.2, CORNER - 0.04, xm) * smoothstep(HINGE_Y - 0.06, HINGE_Y + 0.02, p.y)
	var s := clampf((xm - 2.1) / (LENGTH - 2.1), 0.0, 1.0)
	var w3 := 0.0
	var w4 := 0.0
	var w5 := 0.0
	if part == LEG:
		w3 = smoothstep(AT_ANKLE - 0.03, AT_ANKLE + 0.05, along)
		w4 = smoothstep(AT_KNEE - 0.05, AT_KNEE + 0.05, along)
	elif part == ARM:
		w3 = smoothstep(AT_WRIST - 0.03, AT_WRIST + 0.04, along)
		w4 = smoothstep(AT_ELBOW - 0.05, AT_ELBOW + 0.05, along)
	else:
		w3 = smoothstep(NECK.x + 0.12, NECK.x - 0.12, xm)
		w4 = smoothstep(TAIL_MID.x - 0.1, TAIL_MID.x + 0.15, xm)
		w5 = smoothstep(TAIL_ROOT.x - 0.15, TAIL_ROOT.x + 0.1, xm)
	var body := 1.0 if part == ARM else smoothstep(HIP.x + 0.12, HIP.x - 0.18, xm)
	var r2 := 0.0
	if part == EYE:
		var m := Vector3(signf(p.x) if p.x != 0.0 else 1.0, 1.0, 1.0)
		var d := p - EYE_CENTRE * m
		var pl := Vector2(d.dot(EYE_FWD * m), d.dot(EYE_UP * m))
		r2 = pl.dot(pl)
	return {"part": part, "w": [jaw, 0.22 * s * s, w3, w4, w5, body, r2]}
