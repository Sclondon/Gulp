extends RefCounted
## The angelfish's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`),
## as angelfish.gdshader moved it: a little bend behind the middle (the tail steers), the tail fin's
## edge lagging, the filament streaming, the soft rears of the dorsal and anal fins rippling, the
## pectoral fins rowing (turned about their root, the left after the right, the edge trailing), the
## lower jaw swinging down and the snout lifting, the gill arches spreading, the cartoon eye grown and
## squashed as it blinks; the curl and the arch. Each kind's own hinge, pectoral root and eye (hinge_s,
## hinge_y, pec_root, eye_skin, eye_size) are read from its material. The body is carried round the bend
## by the family (turned about the line, as the sardine's); the old shader kept each point's z, which
## differs by well under a millimetre.

const FAMILY := "swim"

const LENGTH := 0.35
const WAVE := 1.8
const GAPE_ANGLE := 0.8
const GAPE_LIFT := 0.16

# Parts: the model's (COLOR.r * 10) and one of ours.
const EYE := 2
const JAW := 20
const GILL := 10


static func numbers(old: Callable) -> Dictionary:
	var hinge_s: float = old.call(&"hinge_s")
	var hinge_y: float = old.call(&"hinge_y")
	var pec: Vector3 = old.call(&"pec_root")
	var eye: Vector3 = old.call(&"eye_skin")
	var eye_size: float = old.call(&"eye_size")
	var eye_at := Vector3(eye.x, eye.y, eye.z - 0.5) * LENGTH
	var hinge := Vector3(0.0, hinge_y * LENGTH, (hinge_s - 0.5) * LENGTH)
	var fin := LENGTH * 0.012
	return {
		"motion_length": LENGTH, "motion_nose": -0.5 * LENGTH, "wave": WAVE,
		# reach = 0.204 * (s - 0.3)^2 behind 0.3
		"env_poly": Vector4.ZERO, "env_pow": Vector3(0.204 * 0.49, 0.3, 2.0),
		"swim_from": 0.0, "swim_joint": 1.05, "swim_wrist": 0.0,
		"swim_curl_from": -0.2 * LENGTH, "swim_curl_span": 0.7 * LENGTH,
		"swim_arch_from": 0.0, "swim_arch_span": LENGTH, "swim_arch_both": true,
		"ops": [
			# the eye: squashed as it blinks, grown
			{"type": "scale", "parts": [EYE], "drive": "blink", "drive2": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": eye_at, "way": Vector3.UP, "k1": 0.0, "k2": -0.45},
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": eye_at, "k1": eye_size - 1.0, "k2": eye_size - 1.0},
			# the jaw down, the snout up
			{"type": "turn", "parts": [JAW], "drive": "gape", "c": -GAPE_ANGLE, "w": 1, "at": hinge, "way": Vector3.RIGHT},
			{"type": "turn", "parts": [0, 1], "drive": "gape", "c": GAPE_LIFT, "w": 1, "at": hinge, "way": Vector3.RIGHT},
			{"type": "move", "parts": [GILL], "drive": "gape", "c": LENGTH * 0.005, "w": 1, "way": Vector3.BACK},
			# the pectoral fins: the edge trailing, then the whole fin turned about its root
			{"type": "move", "parts": [9], "drive": "row", "a": LENGTH * 0.022, "beat": "strokes", "off": -1.3, "side_off": 0.9,
				"w": 1, "flags": ["mirror", "own_way"]},
			{"type": "turn", "parts": [9], "drive": "row", "c": 0.1, "a": 0.38, "beat": "strokes", "side_off": 0.9,
				"flags": ["mirror"], "at": Vector3(pec.x, pec.y, pec.z - 0.5) * LENGTH, "way": Vector3.UP},
			{"type": "move", "parts": [8], "drive": "row", "a": LENGTH * 0.012, "beat": "strokes", "off": 2.2, "side_off": 1.1,
				"w": 1, "lag": 2, "per_lag": -0.3, "flags": ["own_way"]},
			# the tail fin's edge, the filament
			{"type": "move", "parts": [6], "drive": "sway", "a": LENGTH * 0.03, "beat": "tail_beats", "off": -1.1,
				"w": 1, "lag": 2, "per_lag": -TAU / WAVE},
			{"type": "move", "parts": [5], "drive": "sway", "a": LENGTH * 0.05, "beat": "tail_beats", "w": 1, "lag": 2, "per_lag": -2.6},
			{"type": "move", "parts": [5], "a": LENGTH * 0.05 * 0.25, "beat": "tail_beats", "w": 1, "lag": 2, "per_lag": -2.6},
			# the soft rears of the dorsal and anal fins
			{"type": "move", "parts": [4, 7], "a": 0.4 * fin, "beat": "strokes", "w": 1, "lag": 2, "per_lag": -13.0},
			{"type": "move", "parts": [4, 7], "drive": "row", "a": 0.6 * fin, "beat": "strokes", "w": 1, "lag": 2, "per_lag": -13.0},
		],
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, colour: Color, old: Callable) -> Dictionary:
	var part := int(floor(colour.r * 10.0 + 0.5))
	var s := p.z / LENGTH + 0.5
	var hinge_s: float = old.call(&"hinge_s")
	var hinge_y: float = old.call(&"hinge_y")
	var r := uv.x
	if part == 1 or part == 0:
		if part == 1 or (colour.g > 0.5 and p.y < hinge_y * LENGTH):
			return {"part": JAW, "w": [_ss(hinge_s + 0.02, hinge_s - 0.008, s)]}
		return {"part": part, "w": [_ss(hinge_s + 0.04, hinge_s - 0.01, s)]}
	if part > 9 and part != 9:
		return {"part": GILL, "w": [floorf(uv.y) - 1.5]}
	if part >= 4:
		var way := Vector3(uv2.x, uv2.y, colour.b * 2.0 - 1.0).normalized()
		match part:
			9:
				return {"part": 9, "w": [r * r], "way": way}
			8:
				return {"part": 8, "w": [r * r, uv.y], "way": way}
			6:
				return {"part": 6, "w": [r * r, clampf(s, 0.0, 1.05)]}
			5:
				return {"part": 5, "w": [r * r, r]}
			_:
				return {"part": part, "w": [r * r * _ss(0.45, 0.7, s), s]}
	return {"part": part}


# GLSL's smoothstep, either way round.
static func _ss(e0: float, e1: float, x: float) -> float:
	var t := clampf((x - e0) / (e1 - e0), 0.0, 1.0)
	return t * t * (3.0 - 2.0 * t)
