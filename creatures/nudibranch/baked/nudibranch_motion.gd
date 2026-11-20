extends RefCounted
## The nudibranch's motion in the jointed family (scripts/motion.gd; GameCommon `godot/motion-families`),
## as nudibranch.gdshader moved it: its cerata and rhinophores wave (the wave running back along it), and
## sweep back when it swims; while it crawls (`swim` 0) ripples run back along its foot and body and its
## ends swing a little; swimming (`swim` 1) bends the whole body side to side about its middle. Each
## "crawl" term, sway * (1 - swim), is two ops (sway, and sway * swim taken off).

const FAMILY := "jointed"

const LENGTH := 0.07
const HALF := 0.035


static func numbers(old: Callable) -> Dictionary:
	var ripples := float(old.call(&"ripples"))
	var flex := float(old.call(&"flex"))
	var ops: Array = []
	# the cerata: weight 1 their reach, lag 2 / 3 where they are in the wave
	var tuft := {"type": "move", "parts": [1, 2, 3, 4, 5, 6, 7, 8], "w": 1, "per_lag": 1.0}
	ops.append(tuft.merged({"drive": "sway", "a": 1.0, "lag": 2, "way": Vector3.RIGHT}, true))
	ops.append(tuft.merged({"drive": "sway", "drive2": "swim", "a": 0.8, "lag": 2, "way": Vector3.RIGHT}, true))
	ops.append(tuft.merged({"drive": "sway", "a": 0.7, "off": 0.5 * PI, "lag": 7, "way": Vector3.BACK}, true))
	ops.append(tuft.merged({"drive": "sway", "drive2": "swim", "a": 0.56, "off": 0.5 * PI, "lag": 7, "way": Vector3.BACK}, true))
	ops.append({"type": "move", "parts": [1, 2, 3, 4, 5, 6, 7, 8], "drive": "sway", "drive2": "swim", "a": -0.004, "off": 0.5 * PI,
		"w": 4, "way": Vector3.RIGHT})
	# crawling: ripples (lag 5: how far along, 0..1), its ends swinging
	for k in [1.0, -1.0]:
		var crawl := {"drive": "sway", "drive2": "" if k > 0.0 else "swim", "lag": 5}
		ops.append(crawl.merged({"type": "scale", "a": 0.08 * k, "w": 6, "per_lag": -ripples * TAU, "way": Vector3.RIGHT, "k1": 0.0, "k2": 1.0}, true))
		# (weight 7 is the body's height above its sole; the cerata stand clear of it: 1)
		ops.append(crawl.merged({"type": "scale", "parts": [0], "a": -0.05 * k, "w": 7, "per_lag": -ripples * TAU, "way": Vector3.UP, "k1": 0.0, "k2": 1.0}, true))
		ops.append(crawl.merged({"type": "scale", "parts": [1, 2, 3, 4, 5, 6, 7, 8], "a": -0.05 * k, "per_lag": -ripples * TAU, "way": Vector3.UP, "k1": 0.0, "k2": 1.0}, true))
		ops.append(crawl.merged({"type": "move", "a": 0.0009 * k, "off": 0.5 * PI, "per_lag": -ripples * TAU, "way": Vector3.BACK}, true))
		ops.append(crawl.merged({"type": "move", "a": 0.0022 * k, "w": 3, "per_lag": -2.2, "way": Vector3.RIGHT}, true))
	# swimming: the body bent side to side about its middle (forward half and back half)
	ops.append({"type": "bend", "drive": "sway", "drive2": "swim", "a": flex, "way": Vector3.BACK, "k1": 0.0, "k2": LENGTH})
	ops.append({"type": "bend", "drive": "sway", "drive2": "swim", "a": -flex, "way": Vector3.FORWARD, "k1": 0.0, "k2": LENGTH})
	return {"ops": ops}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, _old: Callable) -> Dictionary:
	var part := int(round(uv2.y))
	var along := (p.z + HALF) / LENGTH
	var low := 1.0 - smoothstep(0.0, 0.006, p.y)
	var ends := (along - 0.5) * 2.0
	var reach := 0.0
	var swept := 0.0
	if part > 0:
		reach = uv.x * uv.x * (0.0036 if part == 1 else (0.0012 if part == 2 else 0.0032))
		swept = uv.x * uv.x * (0.4 + absf(along - 0.5) * 2.4)
	var lag := -along * 7.0 + uv2.x * 2.2
	return {"part": mini(part, 8), "w": [reach, lag, ends * ends, swept, along, 1.0 if part == 0 else 0.35, 1.0 - low if part == 0 else lag + uv2.x * 1.3]}
