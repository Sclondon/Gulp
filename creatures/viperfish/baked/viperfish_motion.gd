extends RefCounted
## The viperfish's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## viperfish.gdshader moved it: the wave back along the body to a one-plate tail, the turning curl, the
## lower jaw dropping and the head lifting as it gapes (the gills spreading, the old wall at the back of
## the mouth lifted away), the long dorsal ray swaying and leaning (`ray_lean`), the pectoral fins
## fluttering, the cartoon eye grown and squashed as it blinks. Numbers from viperfish.gdshader.

const FAMILY := "swim"

const LENGTH := 0.30
const HALF := 0.15
const JOINT := 0.268
const JAW_TO := 0.04
const HINGE_Y := -0.0029
const GAPE_OPEN := 1.05
const HEAD_LIFT := 0.32
const RAY_ROOT := Vector2(0.01581, -0.09)
const EYE_BASE := Vector3(0.00801, 0.0042, -0.1355)
const EYE_GROW := 1.35
const GILL_FROM := 0.0436
const GILL_TO := 0.052
const WALL_UP := 0.01194

# Parts: the model's (UV2.y) and one of ours.
const PECTORAL := 4
const RAY := 5
const EYE := 6
const JAW := 7
const JAW_B := 9
const RAY_B := 10
const GILL := 14
const WALL := 16


static func numbers(old: Callable) -> Dictionary:
	var k := LENGTH / JOINT
	var hinge := Vector3(0.0, HINGE_Y, JAW_TO - HALF)
	return {
		"motion_length": LENGTH, "motion_nose": -HALF,
		"env_poly": Vector4(0.006, -0.022 * k, 0.075 * k * k, 0.0),
		"swim_from": -10.0, "swim_joint": JOINT / LENGTH, "swim_wrist": 0.2, "swim_wrist_from": 0.9 * JOINT / LENGTH,
		"swim_curl_from": -0.09, "swim_curl_span": 0.75 * LENGTH,
		"aux0": float(old.call(&"ray_lean")),
		"ops": [
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": EYE_BASE, "k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0},
			{"type": "scale", "parts": [EYE], "drive": "blink", "drive2": "cartoon_eyes", "c": -0.45, "flags": ["mirror"],
				"at": EYE_BASE, "way": Vector3.UP, "k1": 0.0, "k2": 1.0},
			{"type": "draw", "parts": [WALL], "drive": "gape", "shape": "on", "c": 1.0, "at": Vector3(0.0, WALL_UP, 0.0), "way": Vector3.UP},
			{"type": "scale", "parts": [WALL], "drive": "gape", "shape": "on", "c": 1.0, "way": Vector3.RIGHT, "k2": -0.45},
			{"type": "move", "parts": [WALL], "drive": "gape", "shape": "on", "c": 0.1 * (GILL_TO - JAW_TO), "way": Vector3.BACK},
			{"type": "scale", "parts": [GILL], "drive": "gape", "c": 1.0, "way": Vector3.RIGHT, "k2": 0.1},
			{"type": "scale", "parts": [GILL], "drive": "gape", "c": 1.0, "at": Vector3(0.0, 0.0, 0.5 * (GILL_FROM + GILL_TO) - HALF),
				"way": Vector3.BACK, "k2": 0.15},
			{"type": "turn", "parts": [JAW, JAW_B], "drive": "gape", "c": -GAPE_OPEN, "w": 1, "at": hinge, "way": Vector3.RIGHT},
			{"type": "turn", "parts": [RAY, RAY_B], "drive": "sway", "a": -0.1, "off": 1.0, "plus": -1.0, "drive3": "aux0", "w": 3,
				"at": Vector3(0.0, RAY_ROOT.x, RAY_ROOT.y), "way": Vector3.RIGHT},
			{"type": "move", "parts": [RAY, RAY_B], "drive": "sway", "a": 0.006, "off": 2.2, "w": 4, "way": Vector3.RIGHT},
			{"type": "move", "parts": [PECTORAL], "drive": "sway", "a": 0.0025, "w": 5, "flags": ["by_side"], "way": Vector3.RIGHT},
			{"type": "turn", "drive": "gape", "c": HEAD_LIFT, "w": 2, "at": hinge, "way": Vector3.RIGHT},
		],
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, _old: Callable) -> Dictionary:
	var part := int(uv2.y + 0.5)
	var xm := p.z + HALF
	if part == 0 and uv2.x > 0.999 and uv.y > 0.45 and uv.y < 0.55 and absf(xm - JAW_TO) < 0.0001:
		part = WALL
	var jaw := 1.0 - smoothstep(JAW_TO - 0.016, JAW_TO - 0.0005, xm) if part == JAW or part == JAW_B else 0.0
	var lift := 1.0 - smoothstep(JAW_TO - 0.012, JAW_TO + 0.03, xm)
	var t := uv.x if part == RAY else 1.0
	return {"part": part, "w": [jaw, lift, t, pow(t, 1.5), uv.x]}
