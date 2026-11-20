extends RefCounted
## The remora's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## remora.gdshader moved it: the wave back along the body to the tail plate, the turning curl, the
## lower jaw swinging down and the upper lifting a little, the cartoon eye grown; riding a host, its
## tail tip shivers and its fins tremble. Numbers from remora.gdshader. Differs: riding does not damp
## the swimming wave and the curl here (the old one faded both out as `riding` rose; nothing in Gulp
## sets `riding` yet), and the tail's shiver is laid on before the body's line, not along it.

const FAMILY := "swim"

const LENGTH := 0.6
const HALF := 0.3
const JOINT := 0.543
const HINGE_S := 0.072
const HINGE_Y := -0.00423
const GAPE_OPEN := 0.55
const UPPER_LIFT := 0.1
const TREMBLE := 0.006
const FIN_TREMBLE := 0.004
const EYE_PIVOT := Vector3(0.037046, 0.0094, 0.098)
const EYE_BIG := 1.6

const EYE := 7


static func numbers(_old: Callable) -> Dictionary:
	var k := LENGTH / JOINT
	var m := 0.75
	return {
		"motion_length": LENGTH, "motion_nose": -HALF,
		"env_poly": Vector4(m * 0.018, -m * 0.04 * k, m * 0.045 * k * k, 0.0),
		"env_pow": Vector3(m * 0.07 * pow(k, 4.0), 0.0, 4.0),
		"swim_from": -10.0, "swim_joint": JOINT / LENGTH, "swim_wrist": 0.3, "swim_wrist_from": 0.86 * JOINT / LENGTH,
		"swim_curl_from": -0.2 * LENGTH, "swim_curl_span": 0.7 * LENGTH,
		"ops": [
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": Vector3(EYE_PIVOT.x, EYE_PIVOT.y, EYE_PIVOT.z - 0.5) * LENGTH, "k1": EYE_BIG - 1.0, "k2": EYE_BIG - 1.0},
			{"type": "move", "parts": [5, 6], "drive": "riding", "a": FIN_TREMBLE, "beats": 4.0, "w": 2, "lag": 3,
				"per_lag": 0.6 * PI, "flags": ["by_side"], "way": Vector3.RIGHT},
			{"type": "move", "parts": [1, 3], "drive": "riding", "a": 0.7 * FIN_TREMBLE, "beats": 4.0, "w": 2, "lag": 3,
				"per_lag": -3.0 * PI, "way": Vector3.RIGHT},
			{"type": "turn", "drive": "gape", "c": -1.0, "w": 1,
				"at": Vector3(0.0, HINGE_Y * LENGTH, (HINGE_S - 0.5) * LENGTH), "way": Vector3.RIGHT},
			# the tail tip's shiver while riding
			{"type": "move", "drive": "riding", "a": TREMBLE, "beats": 3.0, "w": 4, "lag": 5, "per_lag": -3.0 * PI, "way": Vector3.RIGHT},
		],
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, _old: Callable) -> Dictionary:
	var part := int(uv2.y + 0.5)
	var w := uv2.x
	var jaw := 0.0
	if absf(w) > 0.0001:
		jaw = GAPE_OPEN * w if w > 0.0 else UPPER_LIFT * w
	var s := (p.z + HALF) / JOINT
	return {"part": part, "w": [jaw, uv.x, uv.y, smoothstep(0.7, 1.0, s), s]}
