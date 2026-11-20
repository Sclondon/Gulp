extends RefCounted
## The sea slugs' motion in the jointed family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## sea_slug.gdshader moved them. Crawling (`swim` 0), ripples run along body and foot and its ends swing;
## swimming (`swim` 1), the body bends up and down about its middle. The sea hare's flaps open and close
## (wide and slow as it swims); its gills and rhinophores, and the dancer's, wave. The Spanish dancer's
## skirt curls along each edge as the old shader curled it, its frills ruffled, flapping in waves round it.
## Approximations: the skirt (always swimming, `swim` 1, as the dancer is) is bent twice from its root,
## its fixed curl and frills then the flapping, where the old shader bent it once by their sum (nearly the
## same where they are small); the skirt's tilt at its root each beat (0.12 radians) is folded into its curl.
## The blue dragon (kind 1) is not done (not in Gulp's sea).

const FAMILY := "jointed"

const SKIRT_W := 0.040
const SKIRT_L := 0.118
const SKIRT_Y := 0.014
const SKIRT_SIDE := 0.050
const SKIRT_END := 0.014


static func numbers(old: Callable) -> Dictionary:
	var kind := int(old.call(&"kind"))
	var length := float(old.call(&"body_length"))
	var ripples := float(old.call(&"ripples"))
	var flex := float(old.call(&"flex"))
	var ops: Array = []
	if kind == 0:
		var flap_open := float(old.call(&"flap_open"))
		var flap := {"type": "turn", "parts": [1], "drive": "sway", "w": 5, "per_lag": 1.0, "flags": ["own_point"], "way": Vector3.BACK}
		ops.append(flap.merged({"c": 0.025, "a": 0.025, "lag": 6}, true))
		ops.append(flap.merged({"drive2": "swim", "c": -0.025, "a": -0.025, "lag": 6}, true))
		ops.append(flap.merged({"drive2": "swim", "c": 0.2 + 0.5 * flap_open, "a": 0.5 * flap_open, "lag": 7}, true))
	elif kind == 2:
		var skirt := {"type": "bend", "parts": [1], "flags": ["own_point", "own_way", "bend_up"], "k1": 0.0, "k2": 1.0}
		ops.append(skirt.merged({"c": 1.0, "w": 5}, true))
		ops.append(skirt.merged({"drive": "sway", "a": 1.0, "w": 6, "lag": 7, "per_lag": 1.0}, true))
	var tufts: Array = []
	for p in range(2, 24):
		tufts.append(p)
	ops.append({"type": "move", "parts": tufts, "drive": "sway", "a": 1.0, "w": 5, "lag": 6, "per_lag": 1.0, "way": Vector3.RIGHT})
	ops.append({"type": "move", "parts": tufts, "drive": "sway", "a": 0.6, "off": 0.5 * PI, "w": 5, "lag": 7, "per_lag": 1.0, "way": Vector3.BACK})
	for k in [1.0, -1.0]:
		var crawl := {"drive": "sway", "drive2": "" if k > 0.0 else "swim", "lag": 4}
		ops.append(crawl.merged({"type": "scale", "a": 0.04 * k, "w": 1, "per_lag": -ripples * TAU, "way": Vector3.RIGHT, "k1": 0.0, "k2": 1.0}, true))
		ops.append(crawl.merged({"type": "scale", "a": -0.03 * k, "w": 2, "per_lag": -ripples * TAU, "way": Vector3.UP, "k1": 0.0, "k2": 1.0}, true))
		ops.append(crawl.merged({"type": "move", "a": 0.025 * length * k, "w": 3, "per_lag": -2.2, "way": Vector3.RIGHT}, true))
	# swimming: bent up and down about its middle (forward half and back half)
	for way in [Vector3.BACK, Vector3.FORWARD]:
		ops.append({"type": "bend", "drive": "sway", "drive2": "swim", "a": flex, "flags": ["bend_up"], "way": way, "k1": 0.0, "k2": length})
	return {"ops": ops}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, colour: Color, old: Callable) -> Dictionary:
	var kind := int(old.call(&"kind"))
	var length := float(old.call(&"body_length"))
	var along := clampf((p.z + float(old.call(&"body_half"))) / length, 0.0, 1.0)
	var part := int(uv2.y + 0.5)
	var low := 1.0 - smoothstep(0.0, 0.08 * length, p.y)
	var ends := (along - 0.5) * 2.0
	var w := [1.0 if part == 0 else 0.5, 1.0 - low, ends * ends, along, 0.0, 0.0, 0.0]
	var out := {"part": part, "w": w}
	if kind == 0 and part == 1:
		var sx := 1.0 if colour.b > 0.5 else -1.0
		out["point"] = Vector3(sx * colour.r * 0.1, colour.g * 0.1, 0.0)
		w[4] = -sx
		w[5] = -uv.x * 2.0
		w[6] = -uv.x * 1.6
	elif kind == 2 and part == 1:
		var th := uv.x * TAU
		var root := Vector3(SKIRT_W * sin(th), SKIRT_Y, -SKIRT_L * cos(th))
		var out_way := Vector3(sin(th) / SKIRT_W, 0.0, -cos(th) / SKIRT_L).normalized()
		var reach := SKIRT_END + (SKIRT_SIDE - SKIRT_END) * pow(sin(th) * sin(th), 0.7)
		var s_side := th / PI if th < PI else (TAU - th) / PI
		var frill := float(old.call(&"frill_depth")) * sin(float(old.call(&"frills")) * th)
		var phi := s_side * TAU * float(old.call(&"skirt_waves"))
		# 0.24 sin t (the root's tilt, doubled into a curl) + 1.1 sin(t - phi) = r sin(t + psi)
		var rc := 0.24 + 1.1 * cos(phi)
		var rs := -1.1 * sin(phi)
		out["point"] = root
		out["way"] = out_way
		w[4] = (0.12 + frill) / reach
		w[5] = sqrt(rc * rc + rs * rs) / reach
		w[6] = atan2(rs, rc)
	elif part >= 2:
		var reach := (0.0008 if kind == 1 else 0.004) * (1.0 if part == 4 or part == 5 else 0.5)
		var lag := -along * 5.0 + uv2.x * 2.4
		w[4] = uv.x * uv.x * reach
		w[5] = lag
		w[6] = lag + uv2.x * 1.3
	return out
