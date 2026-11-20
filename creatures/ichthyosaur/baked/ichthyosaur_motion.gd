extends RefCounted
## The ichthyosaur's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`),
## as ichthyosaur.gdshader moved it: the wave back along the body (growing fast towards the tail) to the
## crescent tail plate, the turning curl, the long lower jaw swinging down behind its corner, the cartoon
## eye grown and domed. Numbers from ichthyosaur.gdshader.

const FAMILY := "swim"

const LENGTH := 4.0
const HALF := 2.0
const JOINT := 3.42
const CORNER := 0.74
const HINGE_Y := -0.0252
const HINGE_SPREAD := 0.06
const GAPE_MAX := 0.55
const REACH := 0.07
const EYE_CENTRE := Vector3(0.15064, 0.05000, -1.08000)
const EYE_OUT := Vector3(0.9659, 0.1317, -0.2229)
const EYE_FWD := Vector3(-0.2208, -0.0301, -0.9748)
const EYE_UP := Vector3(-0.1351, 0.9908, 0.0000)
const EYE_SAG := 0.9110
const EYE_GROW := 1.3

const EYE := 7


static func numbers(_old: Callable) -> Dictionary:
	var k := LENGTH / JOINT
	return {
		"motion_length": LENGTH, "motion_nose": -HALF,
		# reach = REACH (0.06 - 0.28 s' + 0.33 s'^2 + 0.9 s'^4), s' = metres behind the snout / JOINT
		"env_poly": Vector4(REACH * 0.06, -REACH * 0.28 * k, REACH * 0.33 * k * k, 0.0),
		"env_pow": Vector3(REACH * 0.9 * pow(k, 4.0), 0.0, 4.0),
		"swim_wave_scale": 1.0 / k,
		"swim_from": -10.0, "swim_joint": JOINT / LENGTH, "swim_wrist": 0.4, "swim_wrist_from": 0.85 * JOINT / LENGTH,
		"swim_curl_from": -0.2 * LENGTH, "swim_curl_span": 0.7 * LENGTH,
		"ops": [
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": EYE_CENTRE, "k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0},
			{"type": "move", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "w": 2, "flags": ["mirror"], "way": EYE_OUT},
			{"type": "turn", "parts": [1, 3], "drive": "gape", "c": -GAPE_MAX, "w": 1,
				"at": Vector3(0.0, HINGE_Y, CORNER - HALF), "way": Vector3.RIGHT},
		],
	}


static func label(p: Vector3, _n: Vector3, _uv: Vector2, uv2: Vector2, _colour: Color, _old: Callable) -> Dictionary:
	var part := int(uv2.y + 0.5)
	if part == 1 or part == 3:
		return {"part": part, "w": [smoothstep(CORNER + 0.015, CORNER - HINGE_SPREAD, p.z + HALF)]}
	if part == EYE:
		var m := Vector3(1.0 if p.x >= 0.0 else -1.0, 1.0, 1.0)
		var d := p - EYE_CENTRE * m
		var pl := Vector2(d.dot(EYE_FWD * m), d.dot(EYE_UP * m))
		var g := EYE_GROW
		# (the dome: a push along the eye's facing of EYE_SAG r^2 (g - g^2) at full growth)
		return {"part": EYE, "w": [0.0, EYE_SAG * pl.dot(pl) * (g - g * g)]}
	return {"part": part}
