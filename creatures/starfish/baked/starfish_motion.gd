extends RefCounted
## The starfish's motion in the jointed family (its bends; drawn one-sided as its own shader drew it) (scripts/motion.gd; GameCommon `godot/motion-families`),
## as starfish.gdshader moved it: each arm (its way out in the model's UV2.x) bent along itself in four
## arcs, its tip curling up and down, the arm lifting from near its root, and writhing side to side in
## two arcs; each arm a little after the one before; `curl_up` curls every arm up; the tube feet under
## the arms wave. The three kinds (common, sunflower, brittle) differ by their settings (arm_length, arms,
## lift_from, tip_wave, writhe), read from each material.

const FAMILY := "jointed"

const ARM := 1
const FEET := 2


static func numbers(old: Callable) -> Dictionary:
	var arm_length: float = old.call(&"arm_length")
	var from: float = float(old.call(&"lift_from")) * arm_length
	var tip_from := 0.55 * arm_length
	var half_from := from + 0.5 * (arm_length - from)
	var arcs := {"parts": [ARM, FEET], "drive": "sway", "lag": 2, "per_lag": 1.0, "flags": ["own_way"], "at": Vector3.ZERO}
	var tip := arcs.merged({"type": "bend", "drive2": "aux0", "c": 0.55, "a": 0.45, "plus": 2.1, "drive3": "curl_up",
		"flags": ["own_way", "bend_up"], "k1": tip_from, "k2": arm_length - tip_from}, true)
	var lift := arcs.merged({"type": "bend", "drive2": "aux0", "c": 0.06, "a": 0.06, "off": 1.3, "plus": 1.35, "drive3": "curl_up",
		"flags": ["own_way", "bend_up"], "k1": from, "k2": arm_length - from}, true)
	# (the sideways arcs bend away from the family's second axis, which is the arm's other side)
	var outer := arcs.merged({"type": "bend", "drive2": "aux1", "a": -1.2, "off": -1.9, "k1": half_from, "k2": arm_length - half_from}, true)
	var inner := arcs.merged({"type": "bend", "drive2": "aux1", "a": -0.7, "k1": from, "k2": arm_length - from}, true)
	var feet := {"type": "move", "parts": [FEET], "drive": "sway", "a": 1.0, "beats": 2.0, "w": 1, "lag": 3, "per_lag": 1.0,
		"flags": ["own_way"]}
	return {
		"aux0": float(old.call(&"tip_wave")), "aux1": float(old.call(&"writhe")),
		"ops": [tip, lift, outer, inner, feet],
	}


static func label(_p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, old: Callable) -> Dictionary:
	var part := int(round(uv2.y))
	if part <= 0:
		return {"part": 0}
	var angle := TAU * uv2.x
	var fwd := Vector3(sin(angle), 0.0, -cos(angle))
	var own := uv2.x * float(old.call(&"arms")) * 2.4
	var arm_length: float = old.call(&"arm_length")
	var feet := uv.y * arm_length * 0.006 if part == FEET else 0.0
	return {"part": FEET if part == FEET else ARM, "way": fwd, "w": [feet, own, uv.x * 61.0 + own]}
