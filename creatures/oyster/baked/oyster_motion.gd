extends RefCounted
## The oyster's motion in the jointed family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## oyster.gdshader moved it: each upper valve turns open about its own hinge (`open`; a cluster's valves
## each by their own share), the mantle edge ripples while open, the pearl is there only with `pearl` on.
## Each valve's hinge point and axis (the script's hinge arrays) are written into its points.

const FAMILY := "jointed"

const MANTLE := 3
const PEARL := 4


static func numbers(old: Callable) -> Dictionary:
	var size := float(old.call(&"size"))
	return {
		"ops": [
			# (the pearl is drawn into its point, out of sight, without `pearl`)
			{"type": "draw", "parts": [PEARL], "drive": "pearl", "shape": "on", "c": -1.0, "plus": 1.0,
				"at": old.call(&"pearl_at"), "way": Vector3.ZERO},
			{"type": "move", "parts": [MANTLE], "drive": "sway", "drive2": "open", "a": 0.0006 * size / 0.16, "w": 1,
				"lag": 2, "per_lag": 1.0, "way": Vector3.UP},
			{"type": "turn", "drive": "open", "c": 1.0, "w": 3, "flags": ["own_point", "own_way"]},
		],
	}


static func label(_p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, old: Callable) -> Dictionary:
	var part := int(uv2.y + 0.5)
	var which := int(floorf(uv2.x * 0.5 + 0.01))
	var upper := fmod(floorf(uv2.x + 0.01), 2.0) > 0.5
	var at: Variant = old.call(&"hinge_at")
	var axis: Variant = old.call(&"hinge_axis")
	var opens: Variant = old.call(&"opens")
	var out := {"part": part, "w": [1.0 - uv.x, uv.y * 3.0, 0.0]}
	if upper and which < at.size():
		out["point"] = at[which]
		out["way"] = axis[which]
		out["w"][2] = opens[which] * float(old.call(&"upper_turn"))
	return out
