extends RefCounted
## The sailfish's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`),
## as sailfish.gdshader moved it: the wave back along the body (the head and bill stiff ahead of it, the tail
## one plate behind its wrist), the turning curl, the lower jaw swinging down, the gill covers lifting and
## the gill arches spreading as the mouth opens, the sail folding down and rippling, the cartoon eye grown and squeezed shut as it
## blinks. Numbers from sailfish.gdshader.

const FAMILY := "swim"

const LENGTH := 2.6
const HALF := 1.3
const HEAD := 0.82
const JOINT := 2.29
const HINGE := Vector2(0.63, -0.06)
const GAPE_MAX := 0.36
const EYE_MIDDLE := Vector3(0.0507, 0.022, -0.665)
const EYE_GROW := 1.8
const COVER_BAND := 0.06
const COVER_FLARE := 0.008
const ARCH_SPREAD := 0.004
const CURL_FROM := 0.85
const SAIL_HIGH := 0.54

# Parts (the model's UV2.y): 0 the body, 1 the sail, 3 the lower jaw, 7 an eye, 8 a gill arch.
const BODY := 0
const SAIL := 1
const JAW := 3
const EYE := 7
const ARCH := 8


static func numbers(_old: Callable) -> Dictionary:
	# s' = metres behind the snout / JOINT = k s; reach = LENGTH * 0.42 * (0.006 + -0.02 s' + 0.02 s'^2 + 0.09 s'^4)
	var k := LENGTH / JOINT
	var core := {
		"env_poly": Vector4(0.006, -0.02 * k, 0.02 * k * k, 0.0) * 0.42,
		"env_pow": Vector3(0.09 * pow(k, 4.0) * 0.42, 0.0, 4.0),
		"swim_wave_scale": 1.0 / k,
		"swim_from": HEAD / LENGTH, "swim_wrist_from": 0.86 * JOINT / LENGTH,
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
			# the sail folds down into its groove (`sail` 0) and ripples while up
			{"type": "move", "parts": [SAIL], "c": 1.0, "plus": -1.0, "drive3": "sail", "w": 2, "way": Vector3(0.0, -0.97, 0.3)},
			{"type": "move", "parts": [SAIL], "drive": "sail", "drive2": "ripple", "a": 1.0, "w": 3, "lag": 4, "per_lag": -TAU * 1.4, "way": Vector3.RIGHT},
			{"type": "turn", "parts": [JAW], "drive": "gape", "c": -GAPE_MAX, "at": hinge, "way": Vector3.RIGHT},
		],
	}
	out.merge(core)
	return out


static func _gill_edge(y: float) -> float:
	return 0.83 - 2.5 * (y + 0.02) * (y + 0.02)


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, _old: Callable) -> Dictionary:
	var part := int(round(uv2.y))
	if part == SAIL:
		return {"part": SAIL, "w": [0.0, uv2.x, pow(uv2.x / SAIL_HIGH, 2.0), p.z]}
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
