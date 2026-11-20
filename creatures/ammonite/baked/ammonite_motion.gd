extends RefCounted
## The ammonite's motion in the jointed family (scripts/motion.gd; GameCommon `godot/motion-families`),
## as ammonite.gdshader moved it: each tentacle curls (more towards its tip, the curl running out along
## it, each a little after the last) and swings sideways; a pulse each beat draws the soft parts a little
## in; `withdraw` pulls body, eyes and tentacles back into the shell and shuts the hood; the whole shell
## rocks and bobs. The pulse, pow(0.5 + 0.5 sin, 4) in the old shader, is its first two harmonics here
## (0.273 + 0.4375 sin - 0.219 cos 2x); it is not scaled down as it withdraws (the old one was).

const FAMILY := "jointed"

const BOX_MIN := Vector3(-0.3, -0.3, -0.3)
const BOX_MAX := Vector3(0.3, 0.3, 0.3)
const COIL := Vector3(0.0, 0.03827, 0.03553)
const APERTURE := Vector3(0.0, -0.12104, 0.01145)
const OUT_OF := Vector3(0.0, -0.28445, 0.95869)
const DOWN := Vector3(0.0, -0.95869, -0.28445)
const BACK := 0.85
const HOOD_SHUT := 1.45
const EYE_BIG := 1.4

# The pulse's harmonics: constant, sin x, cos 2x.
const P0 := 0.2734
const P1 := 0.4375
const P2 := -0.21875

# Parts as the model has them (UV2.y / 16): 1 body, 2 eyes, 3 hood, 4 tentacles.
const BODY := 1
const EYE := 2
const HOOD := 3
const ARM := 4


# The ops for an amount of k * w, w = withdraw + 0.1 * pulse (the old shader's soft parts' draw-in).
static func _drawn(op: Dictionary, k: float) -> Array:
	return [
		op.merged({"drive": "sway", "c": 0.1 * P0 * k, "a": 0.1 * P1 * k, "plus": k, "drive3": "withdraw"}, true),
		op.merged({"drive": "sway", "a": 0.1 * P2 * k, "beats": 2.0, "off": 0.5 * PI}, true),
	]


static func numbers(_old: Callable) -> Dictionary:
	var ops: Array = []
	ops.append({"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["own_point"],
		"k1": EYE_BIG - 1.0, "k2": EYE_BIG - 1.0})
	# the tentacles: curl about each one's own bending axis at its root, then swing about DOWN, then drawn in
	var curl := {"type": "turn", "parts": [ARM], "drive": "sway", "w": 1, "flags": ["own_point", "own_way"]}
	ops.append(curl.merged({"c": 0.3 - 0.25 * P0, "a": 0.3, "lag": 2, "per_lag": 1.0, "plus": 0.15}, true))
	ops.append(curl.merged({"a": -0.25 * P1}, true))
	ops.append(curl.merged({"a": -0.25 * P2, "beats": 2.0, "off": 0.5 * PI}, true))
	ops.append({"type": "turn", "parts": [ARM], "drive": "sway", "a": 0.18, "w": 1, "lag": 3, "per_lag": 1.0,
		"flags": ["own_point"], "way": DOWN})
	ops.append_array(_drawn({"type": "scale", "parts": [ARM], "flags": ["own_point"], "k1": -0.72, "k2": -0.72}, 1.0))
	# body, eyes and tentacles into the shell
	var soft := [BODY, EYE, ARM]
	ops.append_array(_drawn({"type": "scale", "parts": soft, "at": APERTURE, "k1": -0.22, "k2": -0.22}, 1.0))
	ops.append_array(_drawn({"type": "move", "parts": soft, "way": OUT_OF}, -0.025))
	ops.append_array(_drawn({"type": "turn", "parts": soft, "at": COIL, "way": Vector3.RIGHT}, BACK))
	# the hood
	ops.append({"type": "scale", "parts": [HOOD], "drive": "withdraw", "c": 1.0, "flags": ["own_point"], "way": OUT_OF, "k1": 0.0, "k2": 0.55})
	ops.append({"type": "turn", "parts": [HOOD], "drive": "withdraw", "c": HOOD_SHUT, "flags": ["own_point"], "way": Vector3.RIGHT})
	# the shell rocks and bobs
	ops.append({"type": "turn", "drive": "sway", "a": 0.06, "off": 0.6, "way": Vector3.RIGHT})
	ops.append({"type": "move", "drive": "sway", "a": 0.006, "off": -1.0, "way": Vector3.UP})
	return {"ops": ops}


static func label(_p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, colour: Color, _old: Callable) -> Dictionary:
	var code := floorf(uv2.y + 0.5)
	var part := int(floorf((code + 0.5) / 16.0))
	var index := code - float(part) * 16.0
	var along := colour.a
	var kk := Vector3(uv.x, uv.y, uv2.x)
	var joint := BOX_MIN + (BOX_MAX - BOX_MIN) * Vector3(colour.r, colour.g, colour.b)
	var out := {"part": part, "point": joint, "w": [along, -2.5 * along + index * 0.63, index * 1.3]}
	if part == ARM and kk.length() > 0.0:
		var bend := kk.normalized().cross(DOWN)
		if bend.length() > 0.0:
			out["way"] = bend.normalized()
	return out
