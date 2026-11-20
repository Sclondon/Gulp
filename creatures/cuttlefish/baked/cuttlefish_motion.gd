extends RefCounted
## The cuttlefish's motion in the jointed family (scripts/motion.gd; GameCommon `godot/motion-families`),
## as cuttlefish.gdshader moved it: ripples run back along its fin skirt; its arms sway (each a little
## after the last) and spread (`spread`); the two long tentacles shoot out (`strike`); the mantle curls as
## it turns (`curl`); the cartoon eyes grown. Each arm's bend is a turn of its points about its root by the
## angle halfway along the bend to them (the chord of the old arc: nearly the same; a fully spread arm is
## about a tenth longer). Not drawn: the fins' normals tipping with the ripple.

const FAMILY := "jointed"

const MANTLE_FROM := -0.06
const MANTLE_LONG := 0.26
const TENTACLE_X := 0.005
const TENTACLE_Y := -0.004
const TENTACLE_Z := -0.12
const ARM_RX := 0.019
const ARM_RY := 0.014
const ARM_Z := -0.126
const EYE := Vector3(0.042, 0.014, -0.09)
const CARTOON_EYE := 1.6

const BODY := 0
const FIN := 1
const EYES := 2
const ARMS := 3
const TENTACLES := 4
const OTHER := 5


static func numbers(old: Callable) -> Dictionary:
	var fin_waves := float(old.call(&"fin_waves"))
	var arm := {"type": "turn", "parts": [ARMS], "flags": ["own_point", "own_way"]}
	return {
		"ops": [
			{"type": "move", "parts": [FIN], "drive": "fin_lift", "a": 1.0, "beat": "fin_ripples", "w": 1, "lag": 2,
				"per_lag": -TAU * fin_waves, "way": Vector3.UP},
			arm.merged({"drive": "spread", "c": 1.0, "w": 1}, true),
			arm.merged({"drive": "arm_sway", "a": 0.22 * 0.4, "w": 3, "lag": 4, "per_lag": 1.0}, true),
			arm.merged({"drive": "arm_sway", "drive2": "spread", "a": 0.22 * 0.6, "w": 3, "lag": 4, "per_lag": 1.0}, true),
			# the tentacles: drawn in along their length (reach 0.05) and thinner (0.6) when not striking
			{"type": "scale", "parts": [TENTACLES], "drive": "strike", "c": -1.0, "plus": 1.0, "flags": ["own_point"],
				"way": Vector3.BACK, "k1": -0.4, "k2": -0.95},
			{"type": "move", "parts": [TENTACLES], "drive": "strike", "c": -0.006, "plus": 0.006, "way": Vector3.BACK},
			{"type": "move", "parts": [TENTACLES], "drive": "strike", "c": 0.012, "w": 1},
			{"type": "scale", "parts": [EYES], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"], "at": EYE,
				"k1": CARTOON_EYE - 1.0, "k2": CARTOON_EYE - 1.0},
			{"type": "bend", "parts": [BODY, FIN], "drive": "curl", "c": 1.0, "at": Vector3(0.0, 0.0, MANTLE_FROM),
				"way": Vector3.BACK, "k1": 0.0, "k2": MANTLE_LONG},
		],
	}


static func label(_p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, colour: Color, _old: Callable) -> Dictionary:
	var part := colour.r
	var row := int(floorf(colour.b * 16.0))
	if part > 0.1 and part < 0.3:
		var t := uv.y
		var lift := pow(uv.x, 1.3) * smoothstep(0.0, 0.12, t) * (1.0 - smoothstep(0.85, 1.0, t) * 0.5)
		return {"part": FIN, "w": [lift, t]}
	if part > 0.7 and part < 0.9:
		var s := uv.y
		var a := (float(row) + 0.5) * 0.7853982
		var lean := Vector3(cos(a), sin(a), 0.0)
		var root := Vector3(cos(a) * ARM_RX, sin(a) * ARM_RY, ARM_Z)
		var axis := Vector3(0.0, 0.0, -1.0).cross(lean).normalized()
		var follows := smoothstep(0.0, 0.08, s)
		var sc := maxf(s, 0.0)
		return {"part": ARMS, "point": root, "way": axis,
			"w": [(1.0 + 0.8 * sc) * follows, 0.0, (0.3 + 0.5 * sc) * follows, float(row) * 0.9]}
	if part > 0.9:
		var side := 1.0 if row == 8 else -1.0
		return {"part": TENTACLES, "point": Vector3(side * TENTACLE_X, TENTACLE_Y, TENTACLE_Z), "w": [side * uv.y]}
	if part > 0.5 and part < 0.7:
		return {"part": EYES}
	if part < 0.1:
		return {"part": BODY}
	return {"part": OTHER}
