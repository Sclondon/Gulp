extends RefCounted
## The dumbo octopus's motion in the jointed family (scripts/motion.gd; GameCommon `godot/motion-families`),
## as dumbo_octopus.gdshader moved it: its webbed arms beat in and out (the web's curve tightening and
## opening each beat, a wave running round it; `open` opens or shuts it), its ear fins flap (`flaps` a
## beat), its cartoon eyes are grown and squint as they blink, and it curls as it turns.
## Approximations: the web's change of curve is a straight move of each point by how far the old shader
## moved it per unit of curve (measured over the beat's range, 5 +/- 3), not the curve itself.

const FAMILY := "jointed"

const R0 := 0.0695
const Y0 := -0.010
const THETA0 := 0.2
const KAPPA := 5.0
const FIN_ROOT := Vector3(0.06043, 0.092, 0.0)
const EYE_BASE := Vector3(0.04053, 0.034, -0.05678)
const LENGTH := 0.3
const EYE_GROW := 1.7
# (the curve's change measured over this either side of KAPPA)
const SPAN := 3.0

const WEB := 1
const FIN := 3
const EYE := 4


static func numbers(_old: Callable) -> Dictionary:
	var web := {"type": "move", "parts": [WEB], "flags": ["own_way"]}
	return {
		"ops": [
			web.merged({"drive": "open", "c": 4.0}, true),
			web.merged({"drive": "sway", "a": 3.0, "off": 0.5 * PI}, true),
			web.merged({"drive": "sway", "a": 0.9, "lag": 2, "per_lag": 1.0}, true),
			{"type": "turn", "parts": [FIN], "drive": "sway", "a": 0.42, "beat": "flaps", "w": 1, "lag": 3, "per_lag": 1.0,
				"flags": ["mirror"], "at": FIN_ROOT, "way": Vector3.BACK},
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"], "at": EYE_BASE,
				"k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0},
			{"type": "scale", "parts": [EYE], "drive": "blink", "drive2": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": EYE_BASE, "way": Vector3.UP, "k1": 0.0, "k2": -0.3},
			# (bent down from y 0.03 towards +x: a way a hair off straight down, so the bend's sideways axis is +x)
			{"type": "bend", "drive": "curl", "c": 1.0, "at": Vector3(0.0, 0.03, 0.0), "way": Vector3(0.0, -1.0, 0.0001), "k1": 0.0, "k2": 0.6 * LENGTH},
		],
	}


static func _web_line(d: float, k: float) -> Vector3:
	var th := THETA0 + k * d
	if absf(k) < 0.001:
		return Vector3(R0 + sin(THETA0) * d, Y0 - cos(THETA0) * d, th)
	return Vector3(R0 + (cos(THETA0) - cos(th)) / k, Y0 - (sin(th) - sin(THETA0)) / k, th)


# Where the old shader put a point of the web for a curve k.
static func _web_point(v: Vector3, along: float, k: float) -> Vector3:
	var e := Vector3(v.x, 0.0, v.z).normalized()
	var side := Vector3(-e.z, 0.0, e.x)
	var was := _web_line(along, KAPPA)
	var tw := e * sin(was.z) - Vector3(0.0, cos(was.z), 0.0)
	var nw := e * cos(was.z) + Vector3(0.0, sin(was.z), 0.0)
	var o := v - (e * was.x + Vector3(0.0, was.y, 0.0))
	var ot := o.dot(tw)
	var on := o.dot(nw)
	var os := o.dot(side)
	var now := _web_line(along, k)
	var tn := e * sin(now.z) - Vector3(0.0, cos(now.z), 0.0)
	var nn := e * cos(now.z) + Vector3(0.0, sin(now.z), 0.0)
	return e * now.x + Vector3(0.0, now.y, 0.0) + tn * ot + nn * on + side * os


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, _old: Callable) -> Dictionary:
	var part := int(uv2.y + 0.5)
	var along := uv2.x
	var curl_w := maxf(0.03 - p.y, 0.0)
	if (part == 1 or part == 2) and along > 0.0:
		var e := Vector3(p.x, 0.0, p.z).normalized()
		var way := (_web_point(p, along, KAPPA + SPAN) - _web_point(p, along, KAPPA - SPAN)) / (2.0 * SPAN)
		return {"part": WEB, "way": way, "w": [0.0, 3.0 * atan2(e.x, -e.z), 0.0, curl_w]}
	if part == 3:
		return {"part": FIN, "w": [0.35 + 0.65 * uv.x, 0.0, -0.9 * uv.x, curl_w]}
	if part == 4:
		return {"part": EYE, "w": [0.0, 0.0, 0.0, curl_w]}
	return {"part": 0, "w": [0.0, 0.0, 0.0, curl_w]}
