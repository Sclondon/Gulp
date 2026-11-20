extends RefCounted
## The kelp bass's motion in the swim family (scripts/motion.gd; GameCommon
## `godot/motion-families`), as kelp_bass.gdshader moved it: its body wave, the tail fin's edge
## and the soft fins lagging, the pectoral fins sculling and the pelvic fins paddling, and its big
## mouth: the model is built open, so the jaw is swung shut and opens by `gape` and a little with each
## breath (`gape_breath`, `breaths`), the upper jaw (maxilla) swings down and the lips push forward, the
## lips close across as it shuts, the throat floor drops and its roof lifts and parts, the throat
## widens, the gill covers flare with each breath; the cartoon eye grown; the curl.
##
## As the family has it: the mouth's opening is the sum of gape and the breath (the old shader clamped
## it at wide open, so with the mouth wide open each breath opens it up to 6% further), and the throat's
## smaller moves (the floor's drop, the roof's lift and parting, its widening, and the flare's share
## of the opening) follow `gape` only, not the breath (6% of an opening at most), to keep within the
## family's 24 moves. Numbers from kelp_bass.gdshader.

const FAMILY := "swim"

const LENGTH := 0.5
const HINGE_S := 0.13
const HINGE_Y := -0.038
const GILL_S := 0.29
const GAPE_MAX := 0.8
const MAXILLA_S := 0.022
const MAXILLA_Y := -0.001
const WAVE := 1.0
const PROTRUDE := 0.018
const MAXILLA_SWING := 0.2
const THROAT_WIDE := 0.0283
const ROOF_LIFT := 0.0156
const FLOOR_DROP := 0.0187
const EYE_AT := Vector3(0.0163, 0.0180, -0.2040)
const EYE_OUT := Vector3(0.7814, 0.5361, -0.3195)
const EYE_BIG := 1.45

# Parts: the model's (COLOR.r * 10), 11 the throat's widening rows.
const BODY := 0
const JAW := 1
const EYE := 2
const MAXILLA := 3
const PEC := 9
const PELVIC := 8
const TAIL := 6
const LIP := 10
const THROAT := 11
# Weight slots: 1 the jaw's swing, 2 the lips' push, 3 the maxilla's swing, 4..6 by part.


static func numbers(_old: Callable) -> Dictionary:
	var L := LENGTH
	var hinge := Vector3(0.0, HINGE_Y * L, (HINGE_S - 0.5) * L)
	# (an amount that follows the mouth's opening: gape, and the breath's 0.5 - 0.5 cos)
	var by_open := func(op: Dictionary, k: float) -> Array:
		var a := op.duplicate()
		a["drive"] = "gape"
		a["c"] = k
		var b := op.duplicate()
		b["drive"] = "gape_breath"
		b["c"] = 0.5 * k
		b["a"] = -0.5 * k
		b["off"] = 0.5 * PI
		b["beat"] = "breaths"
		return [a, b]
	var push_way := Vector3(0.0, -0.3, -1.0)
	var ops: Array = []
	ops.append({"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
		"at": EYE_AT, "way": EYE_OUT, "k1": EYE_BIG - 1.0, "k2": sqrt(EYE_BIG) - 1.0})
	# the jaw: built open, swung shut by GAPE_MAX * (1 - open)
	var jaw := {"type": "turn", "parts": [JAW, LIP], "w": 1, "at": hinge, "way": Vector3.RIGHT}
	ops.append(jaw.merged({"c": GAPE_MAX}, true))
	ops.append_array(by_open.call(jaw, -GAPE_MAX))
	ops.append({"type": "move", "parts": [JAW], "drive": "gape", "c": -FLOOR_DROP * L, "w": 4, "way": Vector3.UP})
	# the maxilla swings down (the lips about the maxilla's hinge, the maxilla about its front)
	ops.append_array(by_open.call({"type": "turn", "parts": [MAXILLA, LIP], "w": 3, "flags": ["own_point"], "way": Vector3.RIGHT}, MAXILLA_SWING))
	# the lips close across as it shuts: to their closed place, then back out as it opens
	ops.append({"type": "draw", "parts": [LIP], "c": 1.0, "flags": ["way_point"], "way": Vector3.RIGHT})
	ops.append_array(by_open.call({"type": "move", "parts": [LIP], "w": 4, "way": Vector3.RIGHT}, 1.0))
	# the lips and maxilla pushed forward
	ops.append_array(by_open.call({"type": "move", "parts": [BODY, MAXILLA, LIP], "w": 2, "way": push_way}, PROTRUDE * L))
	# the gill covers flare with each breath, and as it opens
	ops.append({"type": "move", "parts": [BODY], "drive": "gill_flare", "c": 0.5, "a": -0.5, "off": 0.5 * PI - 1.3, "beat": "breaths",
		"w": 4, "flags": ["mirror"], "way": Vector3.RIGHT})
	ops.append({"type": "move", "parts": [BODY], "drive": "gill_flare", "drive2": "gape", "c": 1.5, "w": 4, "flags": ["mirror"], "way": Vector3.RIGHT})
	# the throat's roof lifts and parts; its rows widen
	ops.append({"type": "move", "parts": [BODY], "drive": "gape", "c": ROOF_LIFT * L, "w": 5, "way": Vector3.UP})
	ops.append({"type": "draw", "parts": [BODY], "drive": "gape", "c": 1.0, "w": 6, "flags": ["own_point"], "way": Vector3.RIGHT})
	ops.append({"type": "scale", "parts": [THROAT], "drive": "gape", "c": 1.0, "way": Vector3.RIGHT, "k2": 0.08})
	# the fins
	var scull := 0.026 * L
	ops.append({"type": "move", "parts": [PEC], "drive": "scull", "c": scull * 0.65 * 0.35, "a": scull * 0.65, "beat": "sculls",
		"side_off": 1.3, "w": 4, "flags": ["own_way"]})
	ops.append({"type": "move", "parts": [PEC], "drive": "scull", "a": scull * 0.7, "off": -1.2, "beat": "sculls",
		"side_off": 1.3, "w": 5, "flags": ["own_way"]})
	ops.append({"type": "move", "parts": [PELVIC], "drive": "scull", "a": 0.012 * L, "off": 2.2, "beat": "sculls", "side_off": 1.1,
		"w": 5, "lag": 6, "per_lag": -0.25, "flags": ["own_way"]})
	ops.append({"type": "move", "parts": [TAIL], "drive": "sway", "a": 0.03 * L, "off": -1.1, "beat": "tail_beats",
		"w": 5, "lag": 6, "per_lag": -1.0})
	ops.append({"type": "move", "parts": [4, 5, 7], "drive": "sway", "a": 0.012 * L, "off": -1.0, "beat": "tail_beats",
		"w": 5, "lag": 6, "per_lag": -1.0})
	return {
		"motion_length": L, "motion_nose": -0.5 * L, "wave": WAVE,
		"env_poly": Vector4(0.01, -0.06, 0.15, 0.0), "env_pow": Vector3(0.0, 0.0, 2.0),
		"swim_from": 0.0, "swim_joint": 1.05, "swim_wrist": 0.0,
		"swim_curl_from": (GILL_S - 0.5) * L, "swim_curl_span": (1.0 - GILL_S) * L,
		"ops": ops,
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, colour: Color, _old: Callable) -> Dictionary:
	var L := LENGTH
	var part := int(floor(colour.r * 10.0 + 0.5))
	if colour.r * 10.0 - float(part) > 0.25:
		part = THROAT
	var H := HINGE_S
	var across := 1.0 - _ss(0.7, 1.05, absf(p.x) / (THROAT_WIDE * L))
	var maxilla := Vector3(0.0, MAXILLA_Y * L, (MAXILLA_S - 0.5) * L)
	match part:
		JAW:
			var drop := _ss(H - 0.05, H - 0.015, uv.x) * (1.0 - _ss(H + 0.05, H + 0.075, uv.x)) * across * _ss(0.5, 0.85, uv.y)
			return {"part": JAW, "w": [_jaw(uv.x), 0.0, 0.0, drop]}
		LIP:
			var w := uv.y
			return {"part": LIP, "w": [_jaw(uv.x) * w, (1.0 - w) * _lip(uv.x, 0.0), 1.0 - w, p.x - uv2.x],
				"point": maxilla, "way": Vector3(uv2.x, 0.0, 0.0)}
		MAXILLA:
			return {"part": MAXILLA, "w": [0.0, 1.0, 1.0], "point": Vector3(0.0, p.y - uv2.x, p.z - uv2.y)}
		EYE, THROAT:
			return {"part": part}
		BODY:
			var lift := 0.0
			var parted := 0.0
			if uv2.y > 0.0001:
				lift = _ss(H - 0.045, H - 0.012, uv.x) * (1.0 - _ss(H + 0.005, H + 0.02, uv.x)) * _ss(0.2, 0.6, colour.b) * across
				parted = _ss(H - 0.022, H - 0.006, uv.x) * (1.0 - _ss(H + 0.012, H + 0.025, uv.x)) * across
			return {"part": BODY, "w": [0.0, _lip(uv.x, uv.y), 0.0, colour.g, lift, parted],
				"point": Vector3((1.0 if uv2.x >= 0.0 else -1.0) * THROAT_WIDE * L, 0.0, 0.0)}
	var s := p.z / L + 0.5
	var r := uv.x
	var way := Vector3(uv2.x, uv2.y, colour.b * 2.0 - 1.0).normalized()
	match part:
		PEC:
			return {"part": PEC, "w": [0.0, 0.0, 0.0, r, r * r], "way": way}
		PELVIC:
			return {"part": PELVIC, "w": [0.0, 0.0, 0.0, 0.0, r * r, uv.y], "way": way}
		TAIL:
			return {"part": TAIL, "w": [0.0, 0.0, 0.0, 0.0, r * r, TAU * s / WAVE]}
	return {"part": part, "w": [0.0, 0.0, 0.0, 0.0, r * r, TAU * s / WAVE + uv.y * 0.2]}


static func _jaw(s: float) -> float:
	return 1.0 - _ss(HINGE_S - 0.03, HINGE_S + 0.07, s)


static func _lip(s: float, h: float) -> float:
	return (1.0 - _ss(HINGE_S - 0.03, HINGE_S + 0.02, s)) * (1.0 - _ss(0.2, 0.55, h))


# GLSL's smoothstep, either way round.
static func _ss(e0: float, e1: float, x: float) -> float:
	var t := clampf((x - e0) / (e1 - e0), 0.0, 1.0)
	return t * t * (3.0 - 2.0 * t)
