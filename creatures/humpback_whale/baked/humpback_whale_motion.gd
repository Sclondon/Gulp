extends RefCounted
## The humpback whale's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## humpback_whale.gdshader moved it: the fluke's wave up and down the body (small ahead of a fifth of the way back,
## growing to the flukes), the flukes one plate behind their joint, curl and arch; the lower jaw swung
## open, the throat's pleats ballooning down and out and the baleen fans following the jaw as it gapes;
## the flippers sculling; the cartoon eye grown (without the old shader's small bulge out along its
## axis). As the old shader did, every point keeps its place along the body at rest (its own z) when the
## wave carries it: so the jaw and eye move only up/down and sideways before it.

const FAMILY := "swim"

const LENGTH := 14.0
const HINGE_S := 0.245
const HINGE_Y := -0.03
const FAN_OPEN := 0.03
const JOINT := 0.93
const GAPE_MAX := 1.0
const BALLOON := 0.06
const EYE_AT := Vector3(1.0551, -0.294, -3.514)
const EYE_GROW := 1.9
# (the wave's reach, body lengths; the flippers' scull, body lengths)
const REACH := 0.07
const SCULL := 0.012

# Parts (the model's COLOR.r * 10): 0 body, 1 lower jaw, 2 eye, 4 baleen fan, 7 flipper, 9 inside the jaw.
const EYE := 2


static func numbers(_old: Callable) -> Dictionary:
	return {
		"motion_length": LENGTH, "motion_nose": -0.5 * LENGTH,
		"swim_axis": 1,
		"env_poly": Vector4(REACH * 0.035, 0.0, 0.0, 0.0), "env_pow": Vector3(REACH * 0.965, 0.22, 2.1),
		"swim_from": -10.0, "swim_joint": JOINT, "swim_wrist": 0.55, "swim_wrist_from": JOINT - 0.06,
		"swim_curl_from": -0.22 * LENGTH, "swim_curl_span": 0.72 * LENGTH,
		"swim_arch_from": 0.0, "swim_arch_span": LENGTH, "swim_arch_both": true,
		"ops": [
			{"type": "turn", "parts": [1, 9], "drive": "gape", "c": -GAPE_MAX, "w": 1,
				"at": Vector3(0.0, HINGE_Y * LENGTH, (HINGE_S - 0.5) * LENGTH), "way": Vector3.RIGHT},
			{"type": "turn", "parts": [4], "drive": "gape", "c": -GAPE_MAX, "plus": FAN_OPEN, "w": 2,
				"at": Vector3(0.0, HINGE_Y * LENGTH, (HINGE_S - 0.5) * LENGTH), "way": Vector3.RIGHT},
			{"type": "move", "parts": [0], "drive": "gape", "c": -BALLOON * LENGTH, "w": 2, "way": Vector3.UP},
			{"type": "scale", "parts": [0], "drive": "gape", "c": 1.0, "w": 2, "way": Vector3.RIGHT, "k2": 3.0 * BALLOON},
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": EYE_AT, "k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0},
			{"type": "move", "parts": [7], "drive": "scull", "a": SCULL * LENGTH, "beat": "sculls", "side_off": 0.5,
				"w": 3, "lag": 4, "per_lag": -0.6, "flags": ["own_way"]},
			# (each point back to its own place along the body, as the old wave put it)
			{"type": "draw", "c": 1.0, "flags": ["own_point"], "way": Vector3.BACK},
		],
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, colour: Color, _old: Callable) -> Dictionary:
	var part := int(floor(colour.r * 10.0 + 0.5))
	var s := p.z / LENGTH + 0.5
	var jaw := _smooth(HINGE_S + 0.03, HINGE_S - 0.012, s)
	var flat_way := Vector3(uv2.x, uv2.y, colour.b * 2.0 - 1.0)
	return {"part": part, "w": [jaw, colour.g, uv.x * uv.x, uv.x], "point": p,
		"way": flat_way.normalized() if part == 7 and flat_way.length() > 0.0 else Vector3.ZERO}


static func _smooth(a: float, b: float, x: float) -> float:
	var t := clampf((x - a) / (b - a), 0.0, 1.0)
	return t * t * (3.0 - 2.0 * t)
