extends RefCounted
## The gulper eel's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## gulper_eel.gdshader moved it: the long wave back along the whip of a body, the turning curl, the huge
## lower jaw dropping with its pouch ballooning deep and wide as it gapes, the head lifting, the gills
## spreading and the old wall at the back of the mouth lifted away, the tail's end fluttering, the cartoon
## eye grown (longer than it is tall) and squashed as it blinks. Numbers from gulper_eel.gdshader.

const FAMILY := "swim"

const LENGTH := 0.80
const HALF := 0.40
const BODY_TO := 0.778
const JAW_TO := 0.16
const HINGE_Y := -0.0027
const SLOPE := 0.02
const GAPE_OPEN := 0.8
const HEAD_LIFT := 0.16
const POUCH_DEEP := 1.9
const POUCH_WIDE := 1.5
const EYE_BASE := Vector3(0.00387, 0.0022, -0.3895)
const EYE_GROW := Vector3(1.05, 1.15, 1.8)
const GILL_FROM := 0.169
const GILL_TO := 0.19
const WALL_UP := 0.00788

# Parts: the model's (UV2.y) and one of ours.
const TAIL := 3
const EYE := 6
const JAW := 7
const GILL := 8
const WALL := 16


static func numbers(_old: Callable) -> Dictionary:
	var hinge := Vector3(0.0, HINGE_Y, JAW_TO - HALF)
	return {
		"motion_length": LENGTH, "motion_nose": -HALF,
		# reach = 0.005 + 0.072 s'^1.4 body lengths, s' = metres behind the jaw / BODY_TO; the wave per BODY_TO
		"env_poly": Vector4(0.005, 0.0, 0.0, 0.0), "env_pow": Vector3(0.072 * pow(LENGTH / BODY_TO, 1.4), 0.0, 1.4),
		"swim_wave_scale": BODY_TO / LENGTH,
		"swim_from": -10.0, "swim_joint": BODY_TO / LENGTH, "swim_wrist": 0.0,
		"swim_curl_from": -0.2, "swim_curl_span": 0.6 * LENGTH,
		"ops": [
			# (the eye grows 1.05 across, 1.15 up, 1.8 along: along z, then up again)
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": EYE_BASE, "way": Vector3.BACK, "k1": EYE_GROW.x - 1.0, "k2": EYE_GROW.z - 1.0},
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": EYE_BASE, "way": Vector3.UP, "k1": 0.0, "k2": EYE_GROW.y / EYE_GROW.x - 1.0},
			{"type": "scale", "parts": [EYE], "drive": "blink", "drive2": "cartoon_eyes", "c": -0.45, "flags": ["mirror"],
				"at": EYE_BASE, "way": Vector3.UP, "k1": 0.0, "k2": 1.0},
			{"type": "draw", "parts": [WALL], "drive": "gape", "shape": "on", "c": 1.0, "at": Vector3(0.0, WALL_UP, 0.0), "way": Vector3.UP},
			{"type": "scale", "parts": [WALL], "drive": "gape", "shape": "on", "c": 1.0, "way": Vector3.RIGHT, "k2": -0.45},
			{"type": "move", "parts": [WALL], "drive": "gape", "shape": "on", "c": 0.1 * (GILL_TO - JAW_TO), "way": Vector3.BACK},
			{"type": "scale", "parts": [GILL], "drive": "gape", "c": 1.0, "way": Vector3.RIGHT, "k2": 0.1},
			{"type": "scale", "parts": [GILL], "drive": "gape", "c": 1.0, "at": Vector3(0.0, 0.0, 0.5 * (GILL_FROM + GILL_TO) - HALF),
				"way": Vector3.BACK, "k2": 0.15},
			# the pouch: deeper below the lip line (its own point), wider
			{"type": "scale", "parts": [JAW], "drive": "gape", "c": 1.0, "w": 1, "flags": ["own_point"],
				"way": Vector3.UP, "k1": 0.0, "k2": POUCH_DEEP},
			{"type": "scale", "parts": [JAW], "drive": "gape", "c": 1.0, "w": 1, "way": Vector3.RIGHT, "k1": 0.0, "k2": POUCH_WIDE},
			{"type": "turn", "parts": [JAW], "drive": "gape", "c": -GAPE_OPEN, "w": 2, "at": hinge, "way": Vector3.RIGHT},
			{"type": "move", "parts": [TAIL], "drive": "sway", "a": 0.004, "off": -1.2, "w": 4, "way": Vector3.RIGHT},
			{"type": "turn", "drive": "gape", "c": HEAD_LIFT, "w": 3, "at": hinge, "way": Vector3.RIGHT},
		],
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, _old: Callable) -> Dictionary:
	var part := int(uv2.y + 0.5)
	var xm := p.z + HALF
	if part == 0 and uv2.x > 0.999 and uv.y > 0.45 and uv.y < 0.55 and absf(xm - JAW_TO) < 0.0001:
		part = WALL
	var out := {"part": part}
	var bump := 0.0
	var jaw := 0.0
	if part == JAW:
		bump = pow(sin(PI * clampf(xm / JAW_TO, 0.0, 1.0)), 0.8)
		jaw = 1.0 - smoothstep(JAW_TO - 0.05, JAW_TO - 0.002, xm)
		out["point"] = Vector3(0.0, 0.0005 - SLOPE * xm, 0.0)
	var lift := 1.0 - smoothstep(JAW_TO - 0.02, JAW_TO + 0.05, xm)
	var tail := smoothstep(0.6, 1.0, uv.x) if part == TAIL else 0.0
	out["w"] = [bump, jaw, lift, tail]
	return out
