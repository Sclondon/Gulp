extends RefCounted
## The sperm whale's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## sperm_whale.gdshader moved it: the flukes' wave up and down the body, the flukes one plate behind their
## joint, arch and curl; the lower jaw swung open; the cartoon eye grown in its own plane and sunk back
## along its axis by its sag. The old shader arched before it curled, the family curls first (the
## same while only one of them is on).

const FAMILY := "swim"

const LENGTH := 15.0
const HALF := 7.5
const JOINT := 13.5
const CORNER := 4.1
const HINGE_Y := -1.3262
const GAPE_MAX := 0.8
const REACH := 0.045
const EYE_CENTRE := Vector3(1.14778, -0.74, -2.95)
const EYE_OUT := Vector3(0.9829, -0.18, -0.0382)
const EYE_FWD := Vector3(-0.0375, 0.0069, -0.9993)
const EYE_UP := Vector3(0.1801, 0.9836, 0.0)
const EYE_SAG := 0.0663
const EYE_GROW := 2.2

# Parts (the model's UV2.y): 1 lower jaw, 3 inside it, 7 eye.
const EYE := 7


static func numbers(_old: Callable) -> Dictionary:
	var k := LENGTH / JOINT
	# reach = REACH * (0.05 - 0.28 s' + 0.3 s'^2 + 0.93 s'^4) body lengths, s' = metres behind the snout / JOINT
	return {
		"motion_length": LENGTH, "motion_nose": -HALF,
		"swim_axis": 1,
		"env_poly": Vector4(REACH * 0.05, REACH * -0.28 * k, REACH * 0.3 * k * k, 0.0),
		"env_pow": Vector3(REACH * 0.93 * k * k * k * k, 0.0, 4.0),
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
	var jaw := _smooth(CORNER + 0.45, CORNER + -0.15, p.z + HALF)
	var m := Vector3(1.0 if p.x >= 0.0 else -1.0, 1.0, 1.0)
	var d := p - EYE_CENTRE * m
	var pl := Vector2(d.dot(EYE_FWD * m), d.dot(EYE_UP * m))
	return {"part": part, "w": [jaw, pl.dot(pl)]}


static func _smooth(a: float, b: float, x: float) -> float:
	var t := clampf((x - a) / (b - a), 0.0, 1.0)
	return t * t * (3.0 - 2.0 * t)
