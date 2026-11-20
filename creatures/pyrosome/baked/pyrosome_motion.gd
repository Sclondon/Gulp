extends RefCounted
## The pyrosome's motion in the jointed family (scripts/motion.gd; GameCommon `godot/motion-families`),
## as pyrosome.gdshader moved it: the colony sways along its length (side to side, and a third as much
## up and down, a little after), more towards the open end, the sway running down it; `curl` bends it
## round from its closed end. Its glow stays in its baked paint (baked_glow). Not drawn: the normals
## tipping with the sway (lit per vertex, the light hardly changes).

const FAMILY := "jointed"

const LENGTH := 2.0


static func numbers(old: Callable) -> Dictionary:
	var waves := float(old.call(&"sway_waves"))
	var sway := {"type": "move", "drive": "sway", "w": 1, "lag": 2, "per_lag": -TAU * waves}
	return {
		"ops": [
			sway.merged({"a": 0.085, "way": Vector3.RIGHT}, true),
			sway.merged({"a": 0.35 * 0.085, "off": 1.3, "way": Vector3.UP}, true),
			# (bent round from the closed end, z -1, towards +x)
			{"type": "bend", "drive": "curl", "c": 1.0, "at": Vector3(0.0, 0.0, -1.0), "way": Vector3.BACK, "k1": 0.0, "k2": LENGTH},
		],
	}


static func label(p: Vector3, _n: Vector3, _uv: Vector2, _uv2: Vector2, _colour: Color, _old: Callable) -> Dictionary:
	var s := clampf((p.z + 1.0) / LENGTH, 0.0, 1.0)
	return {"part": 0, "w": [pow(s, 1.6), s]}
