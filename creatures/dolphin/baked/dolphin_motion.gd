extends RefCounted
## The dolphin's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## dolphin.gdshader moved it: the flukes' wave up and down the body, the flukes one plate behind their
## joint, arch and curl; the lower jaw swung open; the cartoon eye grown in its own plane and sunk back
## along its axis by its sag. The old shader arched before it curled, the family curls first (the
## same while only one of them is on).

const FAMILY := "swim"

const LENGTH := 2.8
const HALF := 1.4
const JOINT := 2.5
const CORNER := 0.3
const HINGE_Y := -0.0318
const GAPE_MAX := 0.62
const REACH := 0.06
const EYE_CENTRE := Vector3(0.16277, -0.004, -1.032)
const EYE_OUT := Vector3(0.9681, -0.0444, -0.2465)
const EYE_FWD := Vector3(-0.2463, 0.0113, -0.9691)
const EYE_UP := Vector3(0.0458, 0.999, 0.0)
const EYE_SAG := 1.5054
const EYE_GROW := 1.9

# Parts (the model's UV2.y): 1 lower jaw, 3 inside it, 7 eye.
const EYE := 7


static func numbers(_old: Callable) -> Dictionary:
	var k := LENGTH / JOINT
	# reach = REACH * (0.07 - 0.3 s' + 0.33 s'^2 + 0.9 s'^4) body lengths, s' = metres behind the snout / JOINT
	return {
		"motion_length": LENGTH, "motion_nose": -HALF,
		"swim_axis": 1,
		"env_poly": Vector4(REACH * 0.07, REACH * -0.3 * k, REACH * 0.33 * k * k, 0.0),
		"env_pow": Vector3(REACH * 0.9 * k * k * k * k, 0.0, 4.0),
		"swim_wave_scale": 1.0 / k,
		"swim_from": -10.0, "swim_joint": JOINT / LENGTH, "swim_wrist": 0.35, "swim_wrist_from": 0.86 * JOINT / LENGTH,
		"swim_curl_from": -0.2 * LENGTH, "swim_curl_span": 0.7 * LENGTH,
		"swim_arch_from": 0.0, "swim_arch_span": LENGTH, "swim_arch_both": true,
		"ops": [
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": EYE_CENTRE, "k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0},
			{"type": "move", "parts": [EYE], "drive": "cartoon_eyes", "c": EYE_SAG * EYE_GROW * (1.0 - EYE_GROW), "w": 2,
				"flags": ["mirror"], "way": EYE_OUT},
			{"type": "turn", "parts": [1, 3], "drive": "gape", "c": -GAPE_MAX, "w": 1,
				"at": Vector3(0.0, HINGE_Y, CORNER - HALF), "way": Vector3.RIGHT},
		],
	}


static func label(p: Vector3, _n: Vector3, _uv: Vector2, uv2: Vector2, _colour: Color, _old: Callable) -> Dictionary:
	var part := int(round(uv2.y))
	var jaw := _smooth(CORNER + 0.01, CORNER + -0.035, p.z + HALF)
	var m := Vector3(1.0 if p.x >= 0.0 else -1.0, 1.0, 1.0)
	var d := p - EYE_CENTRE * m
	var pl := Vector2(d.dot(EYE_FWD * m), d.dot(EYE_UP * m))
	return {"part": part, "w": [jaw, pl.dot(pl)]}


static func _smooth(a: float, b: float, x: float) -> float:
	var t := clampf((x - a) / (b - a), 0.0, 1.0)
	return t * t * (3.0 - 2.0 * t)
