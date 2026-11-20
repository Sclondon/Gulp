extends RefCounted
## The swordfish's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`),
## as swordfish.gdshader moved it: the wave back along the body (the head and sword stiff ahead of it, the tail
## one plate behind its wrist), the turning curl, the lower jaw swinging down, the gill covers lifting and
## the gill arches spreading as the mouth opens, the cartoon eye grown and squeezed shut as it
## blinks. Numbers from swordfish.gdshader.

const FAMILY := "swim"

const LENGTH := 3
const HALF := 1.5
const SWORD := 0.95
const JOINT := 2.68
const HINGE := Vector2(1.33, -0.16)
const GAPE_MAX := 0.5
const EYE_MIDDLE := Vector3(0.1008, 0.04, -0.295)
const EYE_GROW := 1.5
const COVER_BAND := 0.12
const COVER_FLARE := 0.015
const ARCH_SPREAD := 0.006
const CURL_FROM := 1.45

# Parts (the model's UV2.y): 0 the body, 3 the lower jaw, 6 an eye, 7 a gill arch.
const BODY := 0
const JAW := 3
const EYE := 6
const ARCH := 7


static func numbers(old: Callable) -> Dictionary:
	# s' = (metres behind the snout - SWORD) / (JOINT - SWORD) = a s + b; reach = (LENGTH - SWORD) * 0.7 * (0.012 s'^2 + 0.085 s'^4)
	var a := LENGTH / (JOINT - SWORD)
	var b := -SWORD / (JOINT - SWORD)
	var m := (LENGTH - SWORD) / LENGTH * 0.7
	var wave: float = old.call(&"wave")
	var core := {
		"env_poly": Vector4(0.012 * b * b, 0.024 * a * b, 0.012 * a * a, 0.0) * m,
		"env_pow": Vector3(0.085 * m * pow((LENGTH - SWORD) / (JOINT - SWORD), 4.0), SWORD / LENGTH, 4.0),
		"swim_wave_scale": 1.0 / a, "swim_wave_off": -TAU * b / wave,
		"swim_from": SWORD / LENGTH, "swim_wrist_from": 0.9 * JOINT / LENGTH,
	}
	var hinge := Vector3(0.0, HINGE.y, HINGE.x - HALF)
	var out := {
		"motion_length": LENGTH, "motion_nose": -HALF,
		"swim_joint": JOINT / LENGTH, "swim_wrist": 0.3,
		"swim_curl_from": CURL_FROM - HALF, "swim_curl_span": LENGTH - CURL_FROM,
		"ops": [
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": EYE_MIDDLE, "k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0},
			{"type": "scale", "parts": [EYE], "drive": "blink", "c": 1.0, "flags": ["mirror"],
				"at": EYE_MIDDLE, "way": Vector3.UP, "k2": -0.6},
			{"type": "move", "parts": [BODY], "drive": "gape", "c": COVER_FLARE, "w": 1, "flags": ["by_side"], "way": Vector3.RIGHT},
			{"type": "move", "parts": [ARCH], "drive": "gape", "c": ARCH_SPREAD, "w": 1, "way": Vector3.BACK},
			{"type": "turn", "parts": [JAW], "drive": "gape", "c": -GAPE_MAX, "at": hinge, "way": Vector3.RIGHT},
		],
	}
	out.merge(core)
	return out


static func _gill_edge(y: float) -> float:
	return 1.43 - 1.5 * (y + 0.02) * (y + 0.02)


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
		return {"part": JAW, "w": [1.0]}
	return {"part": part}
