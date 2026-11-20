extends RefCounted
## The sea lion's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## sea_lion.gdshader moved it: a gentle wave up and down the body; the fore flippers' stroke (each
## twisting about its span, flapping down and sweeping back to the belly, its tip trailing); the hind
## flippers trailing and steering; the jaw; the male's crest (`crest`); the cartoon eye grown and sunk;
## the sideways curl and the upward arch behind a quarter of the way back.
## Different: the old shader damped every stroke by (1 - fold); here `fold` only adds its steady fold
## (flippers back along the sides) and the stroke keeps going with `sway` (the game never sets fold).

const FAMILY := "swim"

const LENGTH := 2.2
const HALF := 1.1
const CORNER := 0.125
const HINGE_X := 0.192
const SPAN := Vector3(0.767, -0.307, 0.563)
const EYE_MID := Vector3(0.0528, 0.0447, -0.9320)
const EYE_OUT := Vector3(0.8190, 0.4546, -0.3500)
const EYE_SAG := 0.00159
const EYE_GROW := 1.85

# Our parts: the model's group (UV2.y * 8: 0 body, 1 jaw, 2 and 3 the fore flippers, 4 up the hind
# flippers), plus 8 for the eyes (COLOR.r * 10 = 1).
const EYES := [8, 9, 10, 11, 12, 13, 14, 15]
const JAW := [1, 9]
const FORE := [2, 3, 10, 11]
const HIND := [4, 5, 6, 7, 12, 13, 14, 15]


static func numbers(_old: Callable) -> Dictionary:
	var stroke := {"parts": FORE, "drive": "sway", "lag": 6, "per_lag": -0.09 * TAU, "flags": ["mirror", "own_point"]}
	return {
		"motion_length": LENGTH, "motion_nose": -HALF,
		"swim_axis": 1,
		"env_poly": Vector4(0.006, 0.0, 0.022, 0.0), "wave": 1.0 / 0.55, "swim_wave_off": -0.2 * PI,
		"swim_from": 0.0, "swim_joint": 1.0, "swim_wrist": 0.0,
		"swim_curl_from": -0.25 * LENGTH, "swim_curl_span": 0.75 * LENGTH,
		"swim_arch_from": -0.25 * LENGTH, "swim_arch_span": 0.75 * LENGTH, "swim_arch_both": false,
		"ops": [
			{"type": "scale", "parts": EYES, "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": EYE_MID, "k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0},
			{"type": "move", "parts": EYES, "drive": "cartoon_eyes", "c": -(EYE_GROW * EYE_GROW - EYE_GROW) * EYE_SAG, "w": 2,
				"flags": ["mirror"], "way": EYE_OUT},
			{"type": "move", "parts": [0], "drive": "crest", "c": 0.048, "w": 3, "way": Vector3.UP},
			{"type": "turn", "parts": JAW, "drive": "gape", "c": -0.7, "w": 1, "flags": ["own_point"], "way": Vector3.RIGHT},
			stroke.merged({"type": "turn", "a": 0.55, "w": 4, "way": SPAN}, true),
			stroke.merged({"type": "turn", "c": -0.28, "a": 0.62, "off": 0.5 * PI, "plus": -0.3, "drive3": "fold", "way": Vector3.BACK}, true),
			stroke.merged({"type": "turn", "c": 0.3, "a": -0.5, "off": 0.5 * PI - 0.9, "plus": 0.85, "drive3": "fold", "way": Vector3.DOWN}, true),
			{"type": "turn", "parts": HIND, "drive": "sway", "a": 0.22, "off": -1.5 * PI, "w": 5, "flags": ["own_point"], "way": Vector3.RIGHT},
		],
	}


static func label(p: Vector3, n: Vector3, uv: Vector2, uv2: Vector2, colour: Color, _old: Callable) -> Dictionary:
	var kind := int(floor(colour.r * 10.0 + 0.5))
	var group := int(uv2.y * 8.0 + 0.5)
	var hinge := (Vector3(uv2.x, uv.y, uv.x) - Vector3(0.5, 0.5, 0.5)) * LENGTH
	var xm := p.z + HALF
	var jaw := 1.0 - _smooth(CORNER, HINGE_X, xm)
	var bump := 0.0
	if group == 0 and kind == 0:
		bump = exp(-pow((xm - 0.225) / 0.065, 2.0)) * exp(-pow(p.x / 0.065, 2.0)) * _smooth(0.2, 0.95, n.y)
	var along := colour.b
	return {"part": group + (8 if kind == 1 else 0), "point": hinge,
		"w": [jaw, along * along, bump, _smooth(0.0, 0.5, along), _smooth(0.0, 0.6, along), along]}


static func _smooth(a: float, b: float, x: float) -> float:
	var t := clampf((x - a) / (b - a), 0.0, 1.0)
	return t * t * (3.0 - 2.0 * t)
