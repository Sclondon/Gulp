extends RefCounted
## The horseshoe crab's motion in the jointed family (scripts/motion.gd; GameCommon
## `godot/motion-families`), as horseshoe_crab.gdshader moved it: the legs on their strides under the
## shell, the book gills flapping one after another (`gills`), the tail spike swinging and lifting
## (`swing`), the rear shell turned on its hinge (`hinge`, read once when it is dressed: nothing sets it
## live), the cartoon eyes grown. Numbers from horseshoe_crab.gdshader.

const FAMILY := "jointed"

const BOX_MIN := Vector3(-0.2, 0.0, -0.3)
const BOX_MAX := Vector3(0.2, 0.15, 0.3)
const KNEE_AT := 0.45
const HINGE := Vector3(0.0, 0.03, -0.092)
const ON_GROUND := 0.65
const STRIDE := 0.016
const LIFT := 0.005
const EYE_MIDDLE := Vector3(0.071, 0.0458, -0.168)
const EYE_GROW := 1.3

# The model's parts: 1 rear shell, 2 tail spike, 3 legs, 4 gills, 5 eyes, 6 (rides the hinge).
const REAR := 1
const SPIKE := 2
const LEG := 3
const GILL := 4
const EYE := 5
const BACK := 6


static func numbers(old: Callable) -> Dictionary:
	var hinge: Variant = old.call(&"hinge")
	return {
		"aux0": float(hinge) if hinge != null else 0.0,
		"ops": [
			{"type": "leg", "parts": [LEG], "drive": "walk", "w": 1, "lag": 2, "per_lag": TAU,
				"way": Vector3.FORWARD, "k1": STRIDE, "k2": LIFT, "knee_at": KNEE_AT, "ground": ON_GROUND},
			{"type": "turn", "parts": [GILL], "drive": "gills", "c": 0.24, "a": 0.14, "lag": 2, "per_lag": -0.9,
				"flags": ["own_point"], "way": Vector3.RIGHT},
			{"type": "turn", "parts": [SPIKE], "drive": "swing", "c": -0.025, "a": -0.025, "beats": 2.0,
				"flags": ["own_point"], "way": Vector3.RIGHT},
			{"type": "turn", "parts": [SPIKE], "drive": "swing", "a": 0.14, "flags": ["own_point"], "way": Vector3.UP},
			{"type": "turn", "parts": [REAR, SPIKE, GILL, BACK], "drive": "aux0", "c": 1.0, "at": HINGE, "way": Vector3.RIGHT},
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": EYE_MIDDLE, "k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0},
		],
	}


static func label(_p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, colour: Color, _old: Callable) -> Dictionary:
	var code := floorf(uv2.y + 0.5)
	var part := int(floorf((code + 0.5) / 16.0))
	var index := code - float(part) * 16.0
	var along := colour.a
	var joint := BOX_MIN + (BOX_MAX - BOX_MIN) * Vector3(colour.r, colour.g, colour.b)
	if part == LEG:
		return {"part": LEG, "w": [along, -0.2 * index + (0.0 if joint.x >= 0.0 else 0.5)], "point": joint,
			"way": Vector3(uv.x, uv.y, uv2.x)}
	if part == GILL:
		return {"part": GILL, "w": [0.0, index], "point": joint}
	return {"part": part, "point": joint}
