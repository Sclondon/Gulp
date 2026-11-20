extends RefCounted
## The orca's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## orca.gdshader moved it: the flukes' wave up and down the body, the flukes one plate behind their
## joint, arch and curl; the lower jaw swung open; the cartoon eye grown in its own plane and sunk back
## along its axis by its sag. The old shader arched before it curled, the family curls first (the
## same while only one of them is on).

const FAMILY := "swim"

const LENGTH := 7.0
const HALF := 3.5
const JOINT := 6.2
const CORNER := 0.62
const HINGE_Y := -0.1212
const GAPE_MAX := 0.55
const REACH := 0.055
const EYE_CENTRE := Vector3(0.52138, -0.04, -2.7)
const EYE_OUT := Vector3(0.9801, -0.0098, -0.1984)
const EYE_FWD := Vector3(-0.1984, 0.002, -0.9801)
const EYE_UP := Vector3(0.01, 0.9999, 0.0)
const EYE_SAG := 0.5021
const EYE_GROW := 2.0

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
			# (the dorsal fin: the bull's blade, drawn down to the female's curved fin as fin_tall goes to 0)
			{"type": "move", "parts": [5], "drive": "fin_tall", "c": -1.0, "plus": 1.0, "flags": ["own_way"]},
			{"type": "turn", "parts": [1, 3], "drive": "gape", "c": -GAPE_MAX, "w": 1,
				"at": Vector3(0.0, HINGE_Y, CORNER - HALF), "way": Vector3.RIGHT},
		],
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, _old: Callable) -> Dictionary:
	var part := int(round(uv2.y))
	var jaw := _smooth(CORNER + 0.02, CORNER + -0.08, p.z + HALF)
	var m := Vector3(1.0 if p.x >= 0.0 else -1.0, 1.0, 1.0)
	var d := p - EYE_CENTRE * m
	var pl := Vector2(d.dot(EYE_FWD * m), d.dot(EYE_UP * m))
	if part == 5:
		var here := _dorsal(uv.x, uv.y, COW_LEAD, COW_TRAIL, COW_TIP) - _dorsal(uv.x, uv.y, BULL_LEAD, BULL_TRAIL, BULL_TIP)
		return {"part": part, "way": Vector3(0.0, here.y, here.x)}
	return {"part": part, "w": [jaw, pl.dot(pl)]}


const DORSAL_LEAD_ROOT := Vector2(2.42, 0.69)
const DORSAL_TRAIL_ROOT := Vector2(3.38, 0.675)
const BULL_LEAD := Vector2(2.66, 1.65)
const BULL_TRAIL := Vector2(3.05, 1.42)
const BULL_TIP := Vector2(2.88, 2.56)
const COW_LEAD := Vector2(2.92, 1.55)
const COW_TRAIL := Vector2(3.28, 0.95)
const COW_TIP := Vector2(3.52, 1.66)
const DORSAL_REACH := 0.985


# Where orca.gdshader put a point of the dorsal fin (along its root to tip, across lead to trail) on one shape.
static func _dorsal(t: float, u: float, lead: Vector2, trail: Vector2, tip: Vector2) -> Vector2:
	return _bezier(DORSAL_LEAD_ROOT, lead, tip, t * DORSAL_REACH).lerp(_bezier(DORSAL_TRAIL_ROOT, trail, tip, t * DORSAL_REACH), u)


static func _bezier(a: Vector2, b: Vector2, c: Vector2, t: float) -> Vector2:
	var s := 1.0 - t
	return s * s * a + 2.0 * s * t * b + t * t * c


static func _smooth(a: float, b: float, x: float) -> float:
	var t := clampf((x - a) / (b - a), 0.0, 1.0)
	return t * t * (3.0 - 2.0 * t)
