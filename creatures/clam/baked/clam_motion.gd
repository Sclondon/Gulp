extends RefCounted
## The clams' motion in the jointed family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## clam.gdshader moved them: the upper valve turns open about the hinge (`open`); the giant clam's mantle
## swells out of the gape as it opens and ripples; the scallop claps as it swims (`swim`), drawing its
## eyed mantle edge in as it shuts; the razor clam's foot pumps and grips and the whole clam tips down as it
## digs (`dig`). Approximations: the scallop's clap (fast shut, slow open) is its first four harmonics
## (within 0.06 of it; the mantle edge drawn in with it within 0.25); the giant clam's mantle and the scallop's mantle edge, which followed a smoothstep
## of `open`, follow a straight line from shut to the open they are given (0.7 and 0.5), which the game
## closes to 0 when alarmed (the giant clam's mantle is a little further out half way).

const FAMILY := "jointed"

const RAZOR_HALF := 0.075
const RAZOR_FOOT := -0.061

# The clap as its mean and first four harmonics, [amount, offset] for sin(k x + offset); and
# 1 - smoothstep(0.1, 0.7, clap) the same way (within 0.06 and 0.25 of them).
const CLAP := [0.54, [0.477, 2.7278], [0.1487, 2.1547], [0.0815, 1.606], [0.0504, 1.088]]
const PULL := [0.3959, [0.5725, -0.2629], [0.1623, -1.8094], [0.0969, -1.343], [0.0799, -2.3719]]


# Ops for swim * the series (its mean and harmonics) times k, on the given op.
static func _series(op: Dictionary, series: Array, k: float) -> Array:
	var out := [op.merged({"drive": "swim", "c": series[0] * k}, true)]
	for h in range(1, series.size()):
		out.append(op.merged({"drive": "swim", "a": series[h][0] * k, "beats": float(h), "off": series[h][1]}, true))
	return out

const MANTLE := 3
const EDGE := 4
const FOOT := 6
const SIPHON := 7


static func numbers(old: Callable) -> Dictionary:
	var kind := int(old.call(&"kind"))
	var at: Vector3 = old.call(&"hinge_at")
	var axis: Vector3 = old.call(&"hinge_axis")
	var ops: Array = []
	var valve_parts: Array = []
	for p in 24:
		if not (kind == 0 and p == MANTLE):
			valve_parts.append(p)
	if kind == 0:
		# 1 - m, m = smoothstep(0.25, 1, open), as 1 - 0.926 open (right shut and at its usual 0.7)
		for pair in [[Vector3.RIGHT, -0.85], [Vector3.UP, -0.5], [Vector3.BACK, -0.3]]:
			ops.append({"type": "scale", "parts": [MANTLE], "drive": "open", "c": -0.926, "plus": 1.0,
				"way": pair[0], "k1": 0.0, "k2": pair[1]})
		var ripple := {"type": "move", "parts": [MANTLE], "drive": "sway", "w": 1, "lag": 2, "per_lag": -6.0, "way": Vector3.UP}
		ops.append(ripple.merged({"drive2": "open", "a": 0.008 * 0.926}, true))
	elif kind == 1:
		var k := -0.0065
		var pull := {"type": "move", "parts": [EDGE], "w": 1, "flags": ["own_way"]}
		ops.append(pull.merged({"c": k}, true))
		ops.append(pull.merged({"drive": "open", "c": -1.482 * k}, true))
		ops.append(pull.merged({"drive": "swim", "c": -k}, true))
		ops.append(pull.merged({"drive": "open", "drive2": "swim", "c": 1.482 * k}, true))
		ops.append_array(_series(pull, PULL, k))
		ops.append({"type": "move", "parts": [EDGE], "drive": "sway", "a": 1.0, "beats": 2.0, "w": 2, "lag": 3, "per_lag": 1.0, "way": Vector3.UP})
	elif kind == 2:
		var foot_at := Vector3(0.0, at.y, RAZOR_FOOT)
		for pump in [["", 0.35], ["dig", 0.65]]:
			ops.append({"type": "scale", "parts": [FOOT], "drive": "sway", "drive2": pump[0], "a": pump[1],
				"at": foot_at, "way": Vector3.BACK, "k1": -0.225, "k2": 0.45})
			ops.append({"type": "scale", "parts": [FOOT], "drive": "sway", "drive2": pump[0], "a": pump[1], "shape": "upper",
				"off": PI - 0.6, "w": 1, "at": foot_at, "way": Vector3.BACK, "k1": 0.5, "k2": 0.0})
		ops.append({"type": "move", "parts": [SIPHON], "drive": "sway", "a": 0.0015, "w": 2, "lag": 3, "per_lag": 1.0, "way": Vector3.BACK})
	# the valves (the upper turns open; the lower by lower_turn, mostly 0): opened = open (1 - swim) + swim * clap
	var valve := {"type": "turn", "parts": valve_parts, "w": 4, "at": at, "way": axis}
	ops.append(valve.merged({"drive": "open", "c": 1.0}, true))
	ops.append(valve.merged({"drive": "open", "drive2": "swim", "c": -1.0}, true))
	ops.append_array(_series(valve, CLAP, 1.0))
	if kind == 2:
		ops.append({"type": "turn", "drive": "dig", "c": -1.25, "at": Vector3(0.0, 0.0, -RAZOR_HALF), "way": Vector3.RIGHT})
	return {"ops": ops}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, old: Callable) -> Dictionary:
	var kind := int(old.call(&"kind"))
	var part := int(uv2.y + 0.5)
	var at: Vector3 = old.call(&"hinge_at")
	var turn := lerpf(float(old.call(&"lower_turn")), float(old.call(&"upper_turn")), uv2.x)
	var out := {"part": part, "w": [0.0, 0.0, 0.0, turn]}
	if kind == 0 and part == MANTLE:
		out["w"] = [smoothstep(0.0, 0.3, uv.y) * smoothstep(1.0, 0.7, uv.y), p.z, 0.0, 0.0]
	elif kind == 1 and part == EDGE:
		out["way"] = Vector3(p.x - at.x, 0.0, p.z - at.z).normalized()
		out["w"] = [uv.x, uv.x * uv.x * 0.0012, uv.y * 6.0, turn]
	elif kind == 2 and part == FOOT:
		out["w"] = [smoothstep(0.55, 0.95, uv.x), 0.0, 0.0, turn]
	elif kind == 2 and part == SIPHON:
		out["w"] = [0.0, uv.x, uv.y * 3.0, turn]
	return out
