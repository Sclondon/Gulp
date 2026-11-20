extends RefCounted
## The mahi-mahi's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`),
## as mahi_mahi.gdshader moved it: the wave back along the body (the head and bill stiff ahead of it, the tail
## one plate behind its wrist), the turning curl, the lower jaw swinging down, the gill covers lifting and
## the gill arches spreading as the mouth opens, the cartoon eye grown and squeezed shut as it
## blinks. Numbers from mahi_mahi.gdshader.

const FAMILY := "swim"

const LENGTH := 1.2
const HALF := 0.6
const HEAD := 0.18
const JOINT := 1.04
const HINGE := Vector2(0.085, -0.024)
const GAPE_MAX := 0.62
const EYE_MIDDLE := Vector3(0.0314, 0.024, -0.532)
const EYE_GROW := 1.9
const COVER_BAND := 0.03
const COVER_FLARE := 0.003
const ARCH_SPREAD := 0.002
const CURL_FROM := 0.2

# Parts (the model's UV2.y): 0 the body, 3 the lower jaw, 7 an eye, 8 a gill arch.
const BODY := 0
const JAW := 3
const EYE := 7
const ARCH := 8


static func numbers(_old: Callable) -> Dictionary:
	# s' = metres behind the snout / JOINT = k s; reach = LENGTH * 0.4 * (0.01 + -0.035 s' + 0.07 s'^2 + 0.06 s'^4)
	var k := LENGTH / JOINT
	var core := {
		"env_poly": Vector4(0.01, -0.035 * k, 0.07 * k * k, 0.0) * 0.4,
		"env_pow": Vector3(0.06 * pow(k, 4.0) * 0.4, 0.0, 4.0),
		"swim_wave_scale": 1.0 / k,
		"swim_from": HEAD / LENGTH, "swim_wrist_from": 0.86 * JOINT / LENGTH,
	}
	var hinge := Vector3(0.0, HINGE.y, HINGE.x - HALF)
	var out := {
		"motion_length": LENGTH, "motion_nose": -HALF,
		"swim_joint": JOINT / LENGTH, "swim_wrist": 0.4,
		"swim_curl_from": CURL_FROM - HALF, "swim_curl_span": LENGTH - CURL_FROM,
		"ops": [
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": EYE_MIDDLE, "k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0},
			{"type": "scale", "parts": [EYE], "drive": "blink", "c": 1.0, "flags": ["mirror"],
				"at": EYE_MIDDLE, "way": Vector3.UP, "k2": -0.6},
			{"type": "move", "parts": [BODY], "drive": "gape", "c": COVER_FLARE, "w": 1, "flags": ["by_side"], "way": Vector3.RIGHT},
			{"type": "move", "parts": [ARCH], "drive": "gape", "c": ARCH_SPREAD, "w": 1, "way": Vector3.BACK},
			{"type": "turn", "parts": [JAW], "drive": "gape", "c": -GAPE_MAX, "w": 1, "at": hinge, "way": Vector3.RIGHT},
		],
	}
	out.merge(core)
	return out


static func _gill_edge(y: float) -> float:
	return 0.168 - 2.2 * (y + -0.02) * (y + -0.02)


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, _old: Callable) -> Dictionary:
	var part := int(round(uv2.y))
	if part == BODY:
		var c := uv.y * 2.0 - 1.0
		var ahead := _gill_edge(p.y) - (p.z + HALF)
		var mask := smoothstep(-0.95, -0.8, c) * (1.0 - smoothstep(0.4, 0.6, c))
		var lift := (1.0 if ahead >= 0.0 else 0.0) * (1.0 - smoothstep(0.0, COVER_BAND, ahead)) * mask
		return {"part": BODY, "w": [lift]}
	if part == ARCH and uv.x > 0.5:
		var arch := floorf(fposmod(uv.x + 0.001, 1.0) * 10.0 + 0.5)
		return {"part": ARCH, "w": [arch - 1.5]}
	if part == JAW:
		return {"part": JAW, "w": [smoothstep(HINGE.x + 0.03, HINGE.x - 0.002, p.z + HALF)]}
	return {"part": part}
