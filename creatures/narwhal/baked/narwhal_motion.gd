extends RefCounted
## The narwhal's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## narwhal.gdshader moved it: the flukes' wave up and down the body, the flukes one plate behind their
## joint, arch and curl; the lower jaw swung open; the cartoon eye grown in its own plane and sunk back
## along its axis by its sag. The tusk grows from its root by `tusk`. The old shader arched before it curled, the family curls first (the
## same while only one of them is on). The old one carried the tusk straight ahead of the nose when arched; here it bends with the arch.

const FAMILY := "swim"

const LENGTH := 4.5
const HALF := 2.25
const JOINT := 3.95
const CORNER := 0.23
const HINGE_Y := -0.1148
const GAPE_MAX := 0.5
const REACH := 0.055
const EYE_CENTRE := Vector3(0.28382, -0.085, -1.905)
const EYE_OUT := Vector3(0.9275, -0.2772, -0.2507)
const EYE_FWD := Vector3(-0.2402, 0.0718, -0.9681)
const EYE_UP := Vector3(0.2863, 0.9581, 0.0)
const EYE_SAG := 0.8866
const EYE_GROW := 1.7
const TUSK_ROOT := Vector3(-0.062, -0.045, -2.16)

# Parts (the model's UV2.y): 1 lower jaw, 7 eye, 8 tusk.
const EYE := 7
const TUSK := 8


static func numbers(_old: Callable) -> Dictionary:
	var k := LENGTH / JOINT
	# reach = REACH * (0.07 - 0.3 s' + 0.33 s'^2 + 0.9 s'^4) body lengths, s' = metres behind the snout / JOINT
	return {
		"motion_length": LENGTH, "motion_nose": -HALF,
		"swim_axis": 1,
		"env_poly": Vector4(REACH * 0.07, REACH * -0.3 * k, REACH * 0.33 * k * k, 0.0),
		"env_pow": Vector3(REACH * 0.9 * k * k * k * k, 0.0, 4.0),
		"swim_wave_scale": 1.0 / k,
		"swim_from": 0.0, "swim_joint": JOINT / LENGTH, "swim_wrist": 0.35, "swim_wrist_from": 0.86 * JOINT / LENGTH,
		"swim_curl_from": -0.2 * LENGTH, "swim_curl_span": 0.7 * LENGTH,
		"swim_arch_from": 0.0, "swim_arch_span": LENGTH, "swim_arch_both": true,
		"ops": [
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": EYE_CENTRE, "k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0},
			{"type": "move", "parts": [EYE], "drive": "cartoon_eyes", "c": EYE_SAG * EYE_GROW * (1.0 - EYE_GROW), "w": 2,
				"flags": ["mirror"], "way": EYE_OUT},
			# (the tusk: as long as `tusk` says from its root, thinner when short; at 0 the old shader shrank it
			# to its root, this leaves a 0.55-wide stub there, inside the head)
			{"type": "scale", "parts": [TUSK], "drive": "tusk", "c": 1.0, "plus": -1.0, "at": TUSK_ROOT, "way": Vector3.BACK,
				"k1": 0.45, "k2": 1.0},
			{"type": "turn", "parts": [1], "drive": "gape", "c": -GAPE_MAX, "w": 1,
				"at": Vector3(0.0, HINGE_Y, CORNER - HALF), "way": Vector3.RIGHT},
		],
	}


static func label(p: Vector3, _n: Vector3, _uv: Vector2, uv2: Vector2, _colour: Color, _old: Callable) -> Dictionary:
	var part := int(round(uv2.y))
	var jaw := _smooth(CORNER + 0.01, CORNER + -0.04, p.z + HALF)
	var m := Vector3(1.0 if p.x >= 0.0 else -1.0, 1.0, 1.0)
	var d := p - EYE_CENTRE * m
	var pl := Vector2(d.dot(EYE_FWD * m), d.dot(EYE_UP * m))
	return {"part": part, "w": [jaw, pl.dot(pl)]}


static func _smooth(a: float, b: float, x: float) -> float:
	var t := clampf((x - a) / (b - a), 0.0, 1.0)
	return t * t * (3.0 - 2.0 * t)
