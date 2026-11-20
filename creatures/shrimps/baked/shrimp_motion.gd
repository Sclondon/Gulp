extends RefCounted
## The shrimps' motion in the jointed family (scripts/motion.gd; GameCommon `godot/motion-families`),
## as shrimp.gdshader moved them (cleaner, mantis and pistol shrimps, by their settings): the walking legs
## on their strides, the swimmerets paddling (`paddle`), the antennae swinging (`feel`) and waving up
## (`wave_up`), the eyes swivelling on their stalks each on its own (`swivel`: the mantis shrimp's), the
## mantis shrimp's club arms striking (`strike`) and the pistol shrimp's claw snapping open (`snap`),
## the tail flicked under (`flick`), the cartoon eyes grown. Numbers from shrimp.gdshader and each
## shrimp's settings.
##
## Differs: `wave_up` and `swivel` are read once when it is dressed (the family shaders do not take
## them live; nothing in the game changes them after). The strike's shoulder and elbow turned as
## smoothsteps of `strike` (full by 0.4 and from 0.2 to 1); here they turn evenly with it (the same at 0
## and 1). The tail's curl bends the whole tail beyond its start (the old one bent `curl_length` of it
## and carried the rest straight on).

const FAMILY := "jointed"

const STRIKE_SHOULDER := 0.6
const STRIKE_ELBOW := 1.9
const SNAP_OPEN := 1.25
const ON_GROUND := 0.65
const KNEE_AT := 0.45

# Our parts.
const BODY := 0
const LEG := 1
const PADDLE := 2
const STALK_R := 3
const FEELER := 4
const FAN := 6
const STRIKE_UPPER := 9
const STRIKE_LOWER := 10
const STALK_L := 11
const BALL_R := 12
const BALL_L := 13
const SNAPPER := 14
const STILL := 15


static func _v(old: Callable, name: StringName, fallback: Variant) -> Variant:
	var v: Variant = old.call(name)
	return v if v != null else fallback


static func numbers(old: Callable) -> Dictionary:
	var curl_y: float = _v(old, &"curl_y", 0.0103)
	var eye_middle: Vector3 = _v(old, &"eye_middle", Vector3(0.00286, 0.01251, -0.01908))
	var eye_grow: float = _v(old, &"eye_grow", 1.6)
	return {
		"aux0": float(_v(old, &"wave_up", 0.0)), "aux1": float(_v(old, &"swivel", 0.0)),
		"ops": [
			{"type": "leg", "parts": [LEG], "drive": "walk", "w": 1, "lag": 2, "per_lag": TAU,
				"way": Vector3.FORWARD, "k1": float(_v(old, &"stride", 0.003)), "k2": float(_v(old, &"lift", 0.0016)),
				"knee_at": KNEE_AT, "ground": ON_GROUND},
			{"type": "turn", "parts": [PADDLE], "drive": "paddle", "c": 0.15, "a": 0.55, "lag": 2, "per_lag": 0.4 * PI,
				"flags": ["own_point"], "way": Vector3.RIGHT},
			{"type": "scale", "parts": [BALL_R, BALL_L], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": eye_middle, "k1": eye_grow - 1.0, "k2": eye_grow - 1.0},
			# the eyes' swivel: the right's pitch 3 a beat, yaw 2; the left's pitch 2 (a cosine), yaw 3 (mirrored)
			{"type": "turn", "parts": [STALK_R, BALL_R], "drive": "aux1", "a": 0.35, "beats": 3.0, "off": 1.0,
				"flags": ["own_point"], "way": Vector3.RIGHT},
			{"type": "turn", "parts": [STALK_R, BALL_R], "drive": "aux1", "a": 0.55, "beats": 2.0,
				"flags": ["own_point"], "way": Vector3.UP},
			{"type": "turn", "parts": [STALK_L, BALL_L], "drive": "aux1", "a": 0.35, "beats": 2.0, "off": 0.5 * PI,
				"flags": ["own_point"], "way": Vector3.RIGHT},
			{"type": "turn", "parts": [STALK_L, BALL_L], "drive": "aux1", "a": -0.55, "beats": 3.0, "off": 2.0,
				"flags": ["own_point"], "way": Vector3.UP},
			# the antennae: waved up (twice a beat, the left 1.4 later), then swung side to side
			{"type": "turn", "parts": [FEELER], "drive": "aux0", "a": 1.0, "beats": 2.0, "w": 1, "lag": 2, "per_lag": -PI,
				"side_off": 1.4, "flags": ["own_point"], "way": Vector3.RIGHT},
			{"type": "turn", "parts": [FEELER], "drive": "feel", "a": 1.0, "w": 1, "lag": 2, "per_lag": -0.6 * PI,
				"flags": ["own_point", "by_side"], "way": Vector3.UP},
			# the mantis shrimp's club: the elbow (about its own hinge), then the shoulder
			{"type": "turn", "parts": [STRIKE_LOWER], "drive": "strike", "c": STRIKE_ELBOW, "flags": ["way_point"],
				"way": Vector3.RIGHT},
			{"type": "turn", "parts": [STRIKE_UPPER, STRIKE_LOWER], "drive": "strike", "c": STRIKE_SHOULDER,
				"flags": ["own_point"], "way": Vector3.RIGHT},
			{"type": "turn", "parts": [SNAPPER], "drive": "snap", "c": SNAP_OPEN, "flags": ["own_point"], "way": Vector3.RIGHT},
			# the tail curled under: down and forward about a line curl_y up
			{"type": "bend", "parts": [BODY, PADDLE, FAN], "drive": "flick", "c": -float(_v(old, &"curl_max", 2.7)),
				"flags": ["bend_up", "ends"], "at": Vector3(0.0, curl_y, 0.0), "way": Vector3.BACK,
				"k1": float(_v(old, &"curl_from", -0.0018)), "k2": float(_v(old, &"curl_length", 0.022))},
		],
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, colour: Color, old: Callable) -> Dictionary:
	var box_min: Vector3 = _v(old, &"box_min", Vector3(-0.012, 0.0, -0.032))
	var box_max: Vector3 = _v(old, &"box_max", Vector3(0.012, 0.024, 0.032))
	var kind := int(_v(old, &"kind", 0))
	var legs: float = _v(old, &"legs_a_side", 5.0)
	var code := floorf(uv2.y + 0.5)
	var part := int(floorf((code + 0.5) / 16.0))
	var index := code - float(part) * 16.0
	var along := colour.a
	var knee := Vector3(uv.x, uv.y, uv2.x)
	var joint := box_min + (box_max - box_min) * Vector3(colour.r, colour.g, colour.b)
	var right := joint.x >= 0.0
	match part:
		LEG:
			return {"part": LEG, "w": [along, -index / legs + (0.0 if right else 0.5)], "point": joint, "way": knee}
		PADDLE:
			return {"part": PADDLE, "w": [0.0, index], "point": joint}
		3:
			var ball := along > 0.5
			var which := (BALL_R if ball else STALK_R) if right else (BALL_L if ball else STALK_L)
			return {"part": which, "point": joint}
		FEELER:
			var k := 1.0 if index < 0.5 else 0.35
			return {"part": FEELER, "w": [k * along, along], "point": joint}
		9:
			return {"part": STRIKE_UPPER if kind == 1 else STILL, "point": joint}
		10:
			if kind == 1:
				return {"part": STRIKE_LOWER, "point": joint, "way": knee}
			return {"part": SNAPPER if kind == 2 else STILL, "point": joint}
		BODY, FAN:
			return {"part": part}
	return {"part": STILL}
