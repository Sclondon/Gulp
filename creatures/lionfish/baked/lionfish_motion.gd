extends RefCounted
## The lionfish's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## lionfish.gdshader moved it: the gentle wave back along the body to the tail plate, the turning curl,
## the lower jaw swinging down and the snout lifting; with `spread` falling, each dorsal spine folding
## back about its own root, the pectoral fans closing and folding back along the body and the pelvic fins
## tucking in; the pectoral fans and soft fins waving slowly (`scull`), the cartoon eye grown. Numbers
## from lionfish.gdshader (its sums are in body lengths; here in metres). Differs: `scull` is not capped
## at 2, `spread` not at 0..1.

const FAMILY := "swim"

const LENGTH := 0.35
const JOINT := 0.78
const SWING := 0.05
const HINGE_S := 0.1
const HINGE_Y := -0.062
const GAPE_ANGLE := 0.7
const LIFT := 0.08
const LIFT_TO := 0.11
const LIFT_Y := 0.06
const PEC_ROOT := Vector3(0.0619, -0.035, 0.285)
const PEC_FACING := Vector3(0.7912, -0.0907, -0.6048)
const PEC_FAN := 1.9199
const PEC_CLOSE := 0.8
const PEC_FOLD := 0.55
const SPINE_FOLD := 1.05
const PEC_WAVE := 0.03
const FIN_WAVE := 0.012
const SPINE_ROOT: Array[Vector2] = [
	Vector2(0.2000, 0.1130), Vector2(0.2296, 0.1203), Vector2(0.2592, 0.1260), Vector2(0.2887, 0.1283),
	Vector2(0.3183, 0.1293), Vector2(0.3479, 0.1299), Vector2(0.3775, 0.1299), Vector2(0.4071, 0.1272),
	Vector2(0.4367, 0.1222), Vector2(0.4662, 0.1167), Vector2(0.4958, 0.1109), Vector2(0.5254, 0.1039),
	Vector2(0.5550, 0.0961)]
const CURL_FROM := -0.15
const CORNER_B := 0.012
const CORNER_C := 0.035

# Parts (the model's UV2.y): 0 body, 1 and 9 the lower jaw, 2 dorsal spines, 3 and 4 soft fins,
# 5 pectoral fans, 6 pelvic fins, 7 eyes.
const EYE := 7


static func numbers(old: Callable) -> Dictionary:
	var L := LENGTH
	var g: float = old.call(&"eye_grow")
	var facing: Vector3 = old.call(&"eye_facing")
	var mid: Vector3 = old.call(&"eye_mid")
	var at := (Vector3(mid.x, mid.y, mid.z - 0.5) + facing * (g * float(old.call(&"eye_sink")) + 0.02 * float(old.call(&"eye_radius")))) * L
	var root := Vector3(PEC_ROOT.x, PEC_ROOT.y, PEC_ROOT.z - 0.5) * L
	var pec_wave := {"type": "move", "parts": [5], "drive": "scull", "w": 2, "lag": 3, "per_lag": -1.0, "flags": ["mirror"], "way": PEC_FACING}
	var fins := {"type": "move", "parts": [3, 4], "off": -1.5, "w": 2, "lag": 3, "per_lag": -6.0, "way": Vector3.RIGHT}
	return {
		"motion_length": L, "motion_nose": -0.5 * L,
		"env_poly": Vector4(SWING * 0.1, -SWING * 0.5 / JOINT, SWING * 1.4 / (JOINT * JOINT), 0.0),
		"swim_from": -10.0, "swim_joint": JOINT, "swim_wrist": 0.25, "swim_wrist_from": 0.86 * JOINT,
		"swim_curl_from": CURL_FROM * L, "swim_curl_span": 0.7 * L,
		"ops": [
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"], "at": at, "k1": g - 1.0, "k2": g - 1.0},
			{"type": "turn", "parts": [1, 9], "drive": "gape", "c": -GAPE_ANGLE, "w": 1,
				"at": Vector3(0.0, HINGE_Y, HINGE_S - 0.5) * L, "way": Vector3.RIGHT},
			{"type": "turn", "parts": [0], "drive": "gape", "c": LIFT, "w": 1,
				"at": Vector3(0.0, LIFT_Y, LIFT_TO - 0.5) * L, "way": Vector3.RIGHT},
			# (each spine about its own root by (1 - spread) * SPINE_FOLD * its share)
			{"type": "turn", "parts": [2], "drive": "spread", "c": -SPINE_FOLD, "plus": SPINE_FOLD, "w": 1,
				"flags": ["own_point"], "way": Vector3.RIGHT},
			# the pectoral fans: wave (more spread), close up their rays, fold back
			pec_wave.merged({"a": 0.4 * PEC_WAVE * L}, true),
			pec_wave.merged({"drive2": "spread", "a": 0.6 * PEC_WAVE * L}, true),
			{"type": "turn", "parts": [5], "drive": "spread", "c": -1.0, "plus": 1.0, "w": 4, "flags": ["mirror"], "at": root, "way": PEC_FACING},
			{"type": "turn", "parts": [5], "drive": "spread", "c": PEC_FOLD, "plus": -PEC_FOLD, "flags": ["mirror"], "at": root, "way": Vector3.UP},
			# the pelvic fins tuck in and wave
			{"type": "move", "parts": [6], "drive": "spread", "c": -1.0, "plus": 1.0, "w": 5, "way": Vector3(0.0, 0.04, 0.06) * L},
			{"type": "move", "parts": [6], "drive": "scull", "a": 0.008 * L, "off": -1.0, "w": 5, "flags": ["by_side"], "way": Vector3.RIGHT},
			fins.merged({"drive": "scull", "a": 0.4 * FIN_WAVE * L}, true),
			fins.merged({"drive": "sway", "a": 0.6 * FIN_WAVE * L}, true),
		],
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, _old: Callable) -> Dictionary:
	var part := int(uv2.y + 0.5)
	var s := p.z / LENGTH + 0.5
	match part:
		1, 9:
			return {"part": part, "w": [1.0 - smoothstep(HINGE_S - CORNER_B, HINGE_S + CORNER_C, s)]}
		0:
			return {"part": 0, "w": [1.0 - smoothstep(0.0, LIFT_TO, s) if s < LIFT_TO else 0.0]}
		2:
			var i := clampi(int(floor(uv.y + 0.04)), 0, 12)
			var root := SPINE_ROOT[i]
			return {"part": 2, "w": [0.75 + 0.25 * float(i) / 12.0], "point": Vector3(0.0, root.y, root.x - 0.5) * LENGTH}
		3, 4:
			return {"part": part, "w": [0.0, uv.x * uv.x, uv.y]}
		5:
			return {"part": 5, "w": [0.0, uv.x * uv.x, 3.0 * uv.y + 2.5 * uv.x, -(uv.y - 0.5) * PEC_FAN * PEC_CLOSE]}
		6:
			return {"part": 6, "w": [0.0, 0.0, 0.0, 0.0, uv.x]}
	return {"part": part}
