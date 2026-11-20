extends RefCounted
## The cameroceras' motion in the jointed family (scripts/motion.gd; GameCommon `godot/motion-families`),
## as cameroceras.gdshader moved it: each arm curls (more towards its tip, the curl running out along it,
## each a little after the last) and swings sideways about the line out from the middle; a pulse each
## beat draws them a little in; `withdraw` pulls the soft parts back into the shell and shuts the hood;
## the whole animal rocks and bobs. The sideways swing is a move across each arm's root (as far as the
## old turn moved its middle line: small angles, so nearly the same); the pulse is its first two
## harmonics (see ammonite_motion.gd), not scaled down as it withdraws.

const FAMILY := "jointed"

const BOX_MIN := Vector3(-0.6, -0.6, 1.0)
const BOX_MAX := Vector3(0.6, 0.6, 2.6)
const APERTURE := Vector3(0.0, 0.0, 1.75)
const BACK := 0.5
const HOOD_SHUT := 1.5
const EYE_GROW := 1.45

const P0 := 0.2734
const P1 := 0.4375
const P2 := -0.21875

const BODY := 1
const EYE := 2
const HOOD := 3
const ARM := 4


static func _drawn(op: Dictionary, k: float) -> Array:
	return [
		op.merged({"drive": "sway", "c": 0.08 * P0 * k, "a": 0.08 * P1 * k, "plus": k, "drive3": "withdraw"}, true),
		op.merged({"drive": "sway", "a": 0.08 * P2 * k, "beats": 2.0, "off": 0.5 * PI}, true),
	]


static func numbers(_old: Callable) -> Dictionary:
	var ops: Array = []
	var curl := {"type": "turn", "parts": [ARM], "drive": "sway", "w": 1, "flags": ["own_point", "own_way"]}
	ops.append(curl.merged({"c": 0.12 - 0.45 * P0, "a": 0.28, "lag": 2, "per_lag": 1.0}, true))
	ops.append(curl.merged({"a": -0.45 * P1}, true))
	ops.append(curl.merged({"a": -0.45 * P2, "beats": 2.0, "off": 0.5 * PI}, true))
	ops.append({"type": "move", "parts": [ARM], "drive": "sway", "a": 0.2, "w": 1, "w2": 4, "lag": 3, "per_lag": 1.0, "flags": ["own_way"]})
	ops.append_array(_drawn({"type": "scale", "parts": [ARM], "flags": ["own_point"], "k1": -0.72, "k2": -0.72}, 1.0))
	ops.append({"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["own_point"],
		"k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0})
	var soft := [BODY, EYE, ARM]
	ops.append_array(_drawn({"type": "scale", "parts": soft, "at": APERTURE, "way": Vector3.BACK, "k1": -0.12, "k2": -0.3}, 1.0))
	ops.append_array(_drawn({"type": "move", "parts": soft, "way": Vector3.BACK}, -BACK))
	ops.append({"type": "scale", "parts": [HOOD], "drive": "withdraw", "c": 1.0, "flags": ["own_point"], "way": Vector3.BACK, "k1": 0.0, "k2": 0.45})
	ops.append({"type": "scale", "parts": [HOOD], "drive": "withdraw", "c": 1.0, "flags": ["own_point"], "way": Vector3.RIGHT, "k1": 0.0, "k2": -0.15})
	ops.append({"type": "turn", "parts": [HOOD], "drive": "withdraw", "c": HOOD_SHUT, "flags": ["own_point"], "way": Vector3.RIGHT})
	ops.append({"type": "turn", "drive": "sway", "a": 0.012, "off": 0.6, "way": Vector3.RIGHT})
	ops.append({"type": "move", "drive": "sway", "a": 0.025, "off": -1.0, "way": Vector3.UP})
	return {"ops": ops}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, colour: Color, _old: Callable) -> Dictionary:
	var code := floorf(uv2.y + 0.5)
	var part := int(floorf((code + 0.5) / 16.0))
	var index := code - float(part) * 16.0
	var along := colour.a
	var kk := Vector3(uv.x, uv.y, uv2.x)
	var joint := BOX_MIN + (BOX_MAX - BOX_MIN) * Vector3(colour.r, colour.g, colour.b)
	var out := {"part": part, "point": joint, "w": [along, -2.6 * along + index * 0.63, -1.8 * along + index * 1.3, 0.0]}
	if part == ARM and kk.length() > 0.0:
		var out_way := Vector3(joint.x, joint.y + 0.02, 0.0).normalized()
		var spread := kk.normalized().cross(out_way)
		if spread.length() > 0.0:
			spread = spread.normalized()
			out["way"] = spread
			# (a turn about out_way by a small angle moves a point by that angle times this, along `spread`)
			out["w"][3] = out_way.cross(p - joint).dot(spread)
	return out
