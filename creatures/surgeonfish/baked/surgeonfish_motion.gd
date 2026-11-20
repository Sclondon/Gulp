extends RefCounted
## The surgeonfish's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`),
## as surgeonfish.gdshader moved it: a small body wave, the tail fin's edge and the soft fins lagging, the pectoral fins
## rowing (the edge trailing, swept fore and aft), the pelvic fins flicking, the jaw dropping and the lip
## lifting, the throat deepening as it opens, the gill covers flaring, the cartoon eye grown and shut as
## it blinks; the curl. Numbers from surgeonfish.gdshader; the jaw's opening (gape_angle), the lip's lift,
## the eye's middle and size are read from the material. The family turns the body about its line
## where the old shader kept each point's z: under a tenth of a millimetre here.

const FAMILY := "swim"

const P := {
	"length": 0.25, "hinge_s": 0.05, "hinge_y": -0.007, "gill_s": 0.245, "wave": 1.05, "row_reach": 0.035,
	"jaw_from": 0.022, "pec_side": 0.3, "pec_across": 0.9, "pec_z": 0.03, "pelvic": 0.01, "pelvic_side": 0.4,
	"tail": 0.05, "fins": 0.03, "fins_across": 2.5, "waggle": false, "reach": Vector3(0.008, -0.04, 0.13),
}
const THROAT_LIFT := 0.03
const THROAT_DEPTH := 0.085
const THROAT_BACK := 0.02

# Parts (the model's, COLOR.r * 10).
const JAW := 1
const EYE := 2
const GILL := 5
const PEC := 9
const PELVIC := 8
const TAIL := 6


static func _hinge(old: Callable) -> Vector3:
	var h: Variant = old.call(&"hinge_s")
	var y: Variant = old.call(&"hinge_y")
	var g: Variant = old.call(&"gill_s")
	return Vector3(P.hinge_s if h == null else h, P.hinge_y if y == null else y, P.gill_s if g == null else g)


static func numbers(old: Callable) -> Dictionary:
	var L: float = P.length
	var h := _hinge(old)
	var hinge := Vector3(0.0, h.y * L, (h.x - 0.5) * L)
	var eye: Vector3 = old.call(&"eye_centre")
	var grow: float = old.call(&"eye_grow")
	var reach: Vector3 = P.reach
	var ops: Array = [
		{"type": "turn", "parts": [JAW], "drive": "gape", "drive2": "aux0", "c": -1.0, "w": 1, "at": hinge, "way": Vector3.RIGHT},
		{"type": "turn", "parts": [0], "drive": "gape", "drive2": "aux1", "c": 1.0, "w": 1, "at": hinge, "way": Vector3.RIGHT},
		{"type": "move", "parts": [0], "drive": "gape", "c": L * THROAT_LIFT, "w": 2, "way": Vector3.UP},
		{"type": "move", "parts": [0], "drive": "gape", "c": L * THROAT_DEPTH, "w": 3, "way": Vector3.BACK},
		{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"], "at": eye, "k1": grow - 1.0, "k2": grow - 1.0},
		{"type": "scale", "parts": [EYE], "drive": "blink", "c": 1.0, "flags": ["mirror"], "at": eye, "way": Vector3.UP, "k1": 0.0, "k2": -0.8},
		{"type": "scale", "parts": [GILL], "drive": "gape", "c": 1.0, "way": Vector3.RIGHT, "k2": 0.12},
		{"type": "move", "parts": [PEC], "drive": "row", "c": 0.5 * L * P.row_reach, "a": L * P.row_reach, "beat": "strokes",
			"side_off": P.pec_side, "w": 1, "lag": 2, "per_lag": -P.pec_across, "flags": ["own_way"]},
		{"type": "move", "parts": [PEC], "drive": "row", "a": L * P.pec_z, "beat": "strokes", "off": 0.5 * PI,
			"side_off": P.pec_side, "w": 1, "lag": 2, "per_lag": -P.pec_across, "way": Vector3.BACK},
		{"type": "move", "parts": [PELVIC], "drive": "row", "a": L * P.pelvic, "beat": "strokes", "off": 1.8,
			"side_off": P.pelvic_side, "w": 1, "flags": ["own_way"]},
		{"type": "move", "parts": [TAIL], "drive": "sway", "a": L * P.tail, "beat": "tail_beats", "off": -1.1, "w": 1, "lag": 2, "per_lag": -1.0},
		{"type": "move", "parts": [4, 7, 10, 11, 12], "drive": "sway", "a": L * P.fins, "beat": "tail_beats", "off": -1.0, "w": 1, "lag": 2, "per_lag": -1.0},
	]
	if P.waggle:
		ops.append({"type": "turn", "drive": "waggle", "a": 0.1, "beat": "tail_beats", "off": 0.7,
			"at": Vector3(0.0, 0.0, -0.15 * L), "way": Vector3.UP})
	return {
		"motion_length": L, "motion_nose": -0.5 * L, "wave": P.wave,
		"env_poly": Vector4(reach.x, reach.y, reach.z, 0.0), "env_pow": Vector3(0.0, 0.0, 2.0),
		"swim_from": 0.0, "swim_joint": 1.05, "swim_wrist": 0.0,
		"swim_curl_from": (h.z - 0.5) * L, "swim_curl_span": 0.7 * L,
		"aux0": float(old.call(&"gape_angle")), "aux1": float(old.call(&"lip_lift")),
		"ops": ops,
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, colour: Color, old: Callable) -> Dictionary:
	var L: float = P.length
	var part := int(floor(colour.r * 10.0 + 0.5))
	var s := p.z / L + 0.5
	var h := _hinge(old)
	var r := uv.x
	var across := colour.g
	var wave_lag := TAU * clampf(s, 0.0, 1.05) / float(P.wave)
	match part:
		JAW:
			return {"part": JAW, "w": [_ss(h.x + P.jaw_from, h.x - 0.008, s)]}
		0:
			var tw := maxf(colour.b, colour.g) * _ss(h.x * 0.35, h.x, s)
			return {"part": 0, "w": [_ss(h.x + 0.012, h.x - 0.02, s), tw, tw * _ss(h.x - THROAT_BACK, h.x, s)]}
		EYE, GILL:
			return {"part": part}
	if part >= 4:
		var way := Vector3(uv2.x, uv2.y, colour.b * 2.0 - 1.0).normalized()
		match part:
			PEC:
				return {"part": PEC, "w": [r, across], "way": way}
			PELVIC:
				return {"part": PELVIC, "w": [r * r], "way": way}
			TAIL:
				return {"part": TAIL, "w": [r * r, wave_lag + across * 0.4]}
			_:
				return {"part": part, "w": [r * r, wave_lag + across * float(P.fins_across)]}
	return {"part": part}


# GLSL's smoothstep, either way round.
static func _ss(e0: float, e1: float, x: float) -> float:
	var t := clampf((x - e0) / (e1 - e0), 0.0, 1.0)
	return t * t * (3.0 - 2.0 * t)
