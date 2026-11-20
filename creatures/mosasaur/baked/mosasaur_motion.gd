extends RefCounted
## The mosasaur's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## mosasaur.gdshader moved it: the wave back along the long body to the tail plate, the turning curl,
## the lower jaw swinging down behind its corner and the upper jaw and head lifting a little, the
## cartoon eye grown and domed. Numbers from mosasaur.gdshader.

const FAMILY := "swim"

const LENGTH := 12.0
const HALF := 6.0
const JOINT := 10.4
const CORNER := 1.42
const HINGE_Y := -0.111
const HINGE_SPREAD := 0.2
const GAPE_MAX := 1.1
const LIFT_MAX := 0.14
const REACH := 0.075
const EYE_CENTRE := Vector3(0.23987, 0.17500, -4.87000)
const EYE_OUT := Vector3(0.8469, 0.4999, -0.1815)
const EYE_FWD := Vector3(-0.1563, -0.0922, -0.9834)
const EYE_UP := Vector3(-0.5083, 0.8612, 0.0000)
const EYE_SAG := 0.9645
const EYE_GROW := 2.0

const EYE := 7


static func numbers(_old: Callable) -> Dictionary:
	var hinge := Vector3(0.0, HINGE_Y, CORNER - HALF)
	return {
		"motion_length": LENGTH, "motion_nose": -HALF,
		"env_poly": Vector4(REACH * 0.07, -REACH * 0.36, REACH * 0.62, REACH * 0.6),
		"swim_from": -10.0, "swim_joint": JOINT / LENGTH, "swim_wrist": 0.3, "swim_wrist_from": 0.85 * JOINT / LENGTH,
		"swim_curl_from": -0.3 * LENGTH, "swim_curl_span": 0.75 * LENGTH,
		"ops": [
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": EYE_CENTRE, "k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0},
			{"type": "move", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "w": 2, "flags": ["mirror"], "way": EYE_OUT},
			{"type": "turn", "parts": [1, 3], "drive": "gape", "c": -GAPE_MAX, "w": 1, "at": hinge, "way": Vector3.RIGHT},
			{"type": "turn", "parts": [0, 2, EYE], "drive": "gape", "c": LIFT_MAX, "w": 3, "at": hinge, "way": Vector3.RIGHT},
		],
	}


static func label(p: Vector3, _n: Vector3, _uv: Vector2, uv2: Vector2, _colour: Color, _old: Callable) -> Dictionary:
	var part := int(uv2.y + 0.5)
	var xm := p.z + HALF
	var lift := smoothstep(CORNER + 0.5, CORNER - 0.1, xm) * smoothstep(HINGE_Y - 0.12, HINGE_Y + 0.04, p.y)
	if part == 1 or part == 3:
		return {"part": part, "w": [smoothstep(CORNER + 0.04, CORNER - HINGE_SPREAD, xm)]}
	if part == EYE:
		var m := Vector3(1.0 if p.x >= 0.0 else -1.0, 1.0, 1.0)
		var d := p - EYE_CENTRE * m
		var pl := Vector2(d.dot(EYE_FWD * m), d.dot(EYE_UP * m))
		var g := EYE_GROW
		return {"part": EYE, "w": [0.0, EYE_SAG * pl.dot(pl) * (g - g * g), lift]}
	return {"part": part, "w": [0.0, 0.0, lift]}
