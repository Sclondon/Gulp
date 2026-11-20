extends RefCounted
## The walrus's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## walrus.gdshader moved it: the wave side to side, growing to the hind flippers, which are one plate
## behind the joint; the hind flippers spread and close (each opening as the other closes); the lower
## jaw swung open about its own hinge; the cartoon eye grown and sunk by its sag; then the sideways curl
## and the upward arch, both behind a fifth of the way back. The tusks grow from their roots by `tusks` (at 0 the old shader shrank them to their roots; this leaves a stub 0.6 thick there).

const FAMILY := "swim"

const LENGTH := 3.0
const HALF := 1.5
const CORNER := 0.13
const HINGE_X := 0.2
const JOINT := 2.5
const GAPE_TURN := 0.62
const EYE_MID := Vector3(0.166, 0.1017, -1.285)
const EYE_OUT := Vector3(0.7508, 0.5791, -0.3177)
const EYE_SAG := 0.00067
const EYE_GROW := 1.6
const TUSK_WAY := Vector3(0.13, -1.0, 0.14)

# Our parts: the model's group (UV2.y * 8: 1 the jaw, 4 and 5 the hind flippers), plus 8 for the eyes
# (COLOR.r * 10 = 1), plus 16 for the tusks (COLOR.r * 10 = 7).
const EYES := [8, 9, 10, 11, 12, 13, 14, 15]
const JAW := [1, 9, 17]
const HIND := [4, 5, 6, 7, 12, 13, 14, 15, 20, 21, 22, 23]
const TUSKS := [16, 17, 18, 19, 20, 21, 22, 23]


static func numbers(old: Callable) -> Dictionary:
	var k := LENGTH / JOINT
	var wave: float = old.call(&"wave")
	# reach = 0.004 - 0.012 s' + 0.01 s'^2 + 0.072 s'^3 body lengths, s' = metres behind the snout / JOINT
	return {
		"motion_length": LENGTH, "motion_nose": -HALF,
		"env_poly": Vector4(0.004, -0.012 * k, 0.01 * k * k, 0.072 * k * k * k),
		"swim_wave_scale": 1.0 / k,
		"swim_from": 0.0, "swim_joint": JOINT / LENGTH, "swim_wrist": 0.45, "swim_wrist_from": 0.85 * JOINT / LENGTH,
		"swim_curl_from": -0.2 * LENGTH, "swim_curl_span": 0.7 * LENGTH,
		"swim_arch_from": -0.2 * LENGTH, "swim_arch_span": 0.7 * LENGTH, "swim_arch_both": false,
		"ops": [
			{"type": "scale", "parts": EYES, "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": EYE_MID, "k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0},
			{"type": "move", "parts": EYES, "drive": "cartoon_eyes", "c": -(EYE_GROW * EYE_GROW - EYE_GROW) * EYE_SAG, "w": 2,
				"flags": ["mirror"], "way": EYE_OUT},
			{"type": "scale", "parts": TUSKS, "drive": "tusks", "c": 1.0, "plus": -1.0, "k1": 0.4, "k2": 1.0,
				"flags": ["own_point", "own_way"]},
			{"type": "turn", "parts": JAW, "drive": "gape", "c": -GAPE_TURN, "w": 1, "flags": ["own_point"], "way": Vector3.RIGHT},
			# (the hind flippers spread up and down about their hinge: 1 - 0.34 sway side cos(TAU (phase - 1 / wave)))
			{"type": "scale", "parts": HIND, "drive": "sway", "a": -0.34, "off": 0.5 * PI - TAU / wave, "w": 3,
				"flags": ["own_point"], "way": Vector3.UP, "k1": 0.0, "k2": 1.0},
		],
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, colour: Color, _old: Callable) -> Dictionary:
	var kind := int(floor(colour.r * 10.0 + 0.5))
	var group := int(uv2.y * 8.0 + 0.5)
	var part := group + (8 if kind == 1 else 0) + (16 if kind == 7 else 0)
	var hinge := (Vector3(uv2.x, uv.y, uv.x) - Vector3(0.5, 0.5, 0.5)) * LENGTH
	var jaw := 1.0 - _smooth(CORNER, HINGE_X, p.z + HALF)
	var hind := 0.0
	if group >= 4:
		hind = (1.0 if group == 4 else -1.0) * _smooth(0.0, 0.5, colour.b)
	var out := {"part": part, "w": [jaw, colour.b * colour.b, hind], "point": hinge}
	if kind == 7:
		out["way"] = Vector3(signf(hinge.x) * TUSK_WAY.x, TUSK_WAY.y, TUSK_WAY.z).normalized()
	return out


static func _smooth(a: float, b: float, x: float) -> float:
	var t := clampf((x - a) / (b - a), 0.0, 1.0)
	return t * t * (3.0 - 2.0 * t)
