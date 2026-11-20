extends RefCounted
## The sea otter's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## sea_otter.gdshader moved it: a wave up and down the body, the hind feet beating with it; the jaw;
## the cartoon eye grown and sunk; the sideways curl and upward arch behind a fifth of the way back; and
## `afloat`: rolled on to its back, head and feet lifted, fore paws tucked to the chest, the feet
## bobbing. Different: the old shader eased `afloat` in (smoothstep) where this follows it straight (the
## same at 0, a half and 1); the swimming wave is stilled straight from afloat 0 to 0.6 (the old one eased),
## the feet's beat from 0 to 1.

const FAMILY := "swim"

const LENGTH := 1.3
const HALF := 0.65
const CORNER := 0.058
const HINGE_X := 0.094
const EYE_MID := Vector3(0.0428, 0.0449, -0.5900)
const EYE_OUT := Vector3(0.7041, 0.6234, -0.3401)
const EYE_SAG := 0.00062
const EYE_GROW := 1.9

# Our parts: the model's group (UV2.y * 8: 1 jaw, 2 and 3 the fore paws, 4 and 5 the hind feet), plus
# 8 for the eyes (COLOR.r * 10 = 1).
const EYES := [8, 9, 10, 11, 12, 13, 14, 15]
const JAW := [1, 9]
const PAWS := [2, 3, 10, 11]
const FEET := [4, 5, 6, 7, 12, 13, 14, 15]


static func numbers(_old: Callable) -> Dictionary:
	return {
		"motion_length": LENGTH, "motion_nose": -HALF,
		"swim_axis": 1,
		# (the wave stilled as it lies back: gone by afloat 0.6, as the old shader eased it out)
		"swim_still": "afloat", "swim_still_by": 1.0 / 0.6,
		"env_poly": Vector4(0.008, -0.03, 0.09, 0.0),
		"swim_from": 0.0, "swim_joint": 1.0, "swim_wrist": 0.0,
		"swim_curl_from": -0.2 * LENGTH, "swim_curl_span": 0.7 * LENGTH,
		"swim_arch_from": -0.2 * LENGTH, "swim_arch_span": 0.7 * LENGTH, "swim_arch_both": false,
		"ops": [
			{"type": "scale", "parts": EYES, "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": EYE_MID, "k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0},
			{"type": "move", "parts": EYES, "drive": "cartoon_eyes", "c": -(EYE_GROW * EYE_GROW - EYE_GROW) * EYE_SAG, "w": 2,
				"flags": ["mirror"], "way": EYE_OUT},
			{"type": "turn", "parts": JAW, "drive": "gape", "c": -0.75, "w": 1, "flags": ["own_point"], "way": Vector3.RIGHT},
			# (the fore paws tucked to the chest as it lies back)
			{"type": "turn", "parts": PAWS, "drive": "afloat", "c": 1.94, "flags": ["mirror", "own_point"],
				"way": Vector3(0.8, -0.575, -0.16).normalized()},
			# (the hind feet: their beat, with the wave at their own root; their lift and bob lying back)
			{"type": "turn", "parts": FEET, "drive": "sway", "a": 0.55, "off": -0.16 * TAU, "lag": 4, "per_lag": -TAU, "w": 3,
				"flags": ["own_point"], "way": Vector3.RIGHT},
			# (and that beat stilled lying back: the old shader eased it out by afloat 0.6, this by 1)
			{"type": "turn", "parts": FEET, "drive": "sway", "drive2": "afloat", "a": -0.55, "off": -0.16 * TAU, "lag": 4,
				"per_lag": -TAU, "w": 3, "flags": ["own_point"], "way": Vector3.RIGHT},
			{"type": "turn", "parts": FEET, "drive": "afloat", "c": 0.95, "w": 3, "flags": ["own_point"], "way": Vector3.RIGHT},
			{"type": "turn", "parts": FEET, "drive": "afloat", "drive2": "sway", "a": 0.12, "side_off": 2.0, "w": 3,
				"flags": ["own_point"], "way": Vector3.RIGHT},
			# after the swim: the head bent up ahead of a tenth of the way back, and the roll on to its back
			{"type": "bend", "drive": "afloat", "c": -1.0, "at": Vector3(0.0, 0.0, -0.1 * LENGTH), "way": Vector3.FORWARD,
				"k1": 0.0, "k2": 1.0, "flags": ["bend_up", "after"]},
			{"type": "turn", "drive": "afloat", "c": PI, "way": Vector3.BACK, "flags": ["after"]},
		],
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, colour: Color, old: Callable) -> Dictionary:
	var kind := int(floor(colour.r * 10.0 + 0.5))
	var group := int(uv2.y * 8.0 + 0.5)
	var hinge := (Vector3(uv2.x, uv.y, uv.x) - Vector3(0.5, 0.5, 0.5)) * LENGTH
	var jaw := 1.0 - _smooth(CORNER, HINGE_X, p.z + HALF)
	# (headless, the labeller cannot read a shader's defaults: the otter's own is 1.15)
	var wave_set: Variant = old.call(&"wave")
	var wave: float = 1.15 if wave_set == null else float(wave_set)
	var lag := (hinge.z + HALF) / LENGTH / wave + 0.1 * colour.b
	return {"part": group + (8 if kind == 1 else 0), "point": hinge,
		"w": [jaw, colour.b * colour.b, _smooth(0.0, 0.35, colour.b), lag]}


static func _smooth(a: float, b: float, x: float) -> float:
	var t := clampf((x - a) / (b - a), 0.0, 1.0)
	return t * t * (3.0 - 2.0 * t)
