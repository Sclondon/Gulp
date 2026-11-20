extends RefCounted
## The flying fish's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`),
## as flying_fish.gdshader moved it: the wave back along the body (its size is the fish's `swim`, not
## `sway`, so it is done here as moves: each point carried sideways and turned along the bent body; the
## family's own wave is off), the fins' flutter, the jaw and its breathing, the gill covers' flare, the
## curl; the wings (the big pectoral and pelvic fins) from folded along the body to spread (`wings`); the
## cartoon eye grown and its blink. flying_fish_fins_motion.gd moves the see-through fins the same way.
## Numbers from flying_fish.gdshader. Differs: the wings go from folded to spread point by point in a
## straight line (the old shader swung them round); spread wings bend with the body's wave and curl (the
## old shader carried them stiff from their roots); the turn along the bent body is the slope itself
## (the old shader's atan of it: the same within a few per cent at these slopes).

const FAMILY := "swim"

const LENGTH := 0.3
const HINGE_S := 0.045
const HINGE_Y := -0.015
const WAVE := 0.95
const PECTORAL_AT := Vector3(0.01360, 0.01061, -0.08580)
const PECTORAL_BASE := 0.00750
const PECTORAL_FAN := 1.08210
const PECTORAL_RAYS := 15.0
const PECTORAL_SHUT := 0.020
const PECTORAL_HUG := 0.40000
const PECTORAL_SPREAD := Vector3(0.24435, 0.15708, 0.06981)
const PECTORAL_FOLDED := Vector3(1.53589, -0.02618, 1.78024)
const PELVIC_AT := Vector3(0.00935, -0.01626, -0.02250)
const PELVIC_BASE := 0.00480
const PELVIC_FAN := 0.95993
const PELVIC_RAYS := 6.0
const PELVIC_SHUT := 0.030
const PELVIC_HUG := 0.66667
const PELVIC_SPREAD := Vector3(0.52360, -0.12217, 0.00000)
const PELVIC_FOLDED := Vector3(1.53240, 0.08727, 1.08210)
const EYE_AT := Vector3(0.0126, 0.0033, -0.1275)
const EYE_OUT := Vector3(0.9816, 0.0554, -0.1829)

const BODY := 0
const JAW := 1
const EYE := 2
const TAIL_FIN := 6
const FIN := 4
const WING := 8

# Weight slots (the label's w[0..6] are slots 1..7). Every point: the wave's turn size, its turn's lag,
# its reach, its carry's lag. Wings: their spread move (x, y, z). Others: their own weight and lag.
const W_TURN := 4
const W_TURN_LAG := 5
const W_REACH := 6
const W_LAG := 7


static func numbers(old: Callable) -> Dictionary:
	var grow := float(old.call(&"eye_grow")) if old.call(&"eye_grow") != null else 1.3
	var o := EYE_OUT.normalized()
	var up := (Vector3.UP - o * o.y).normalized()
	var ops := [
		{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"], "at": EYE_AT, "way": o, "k1": grow - 1.0},
		{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "w": 1, "flags": ["mirror"], "at": EYE_AT, "way": o, "k2": grow - 1.0},
		{"type": "scale", "parts": [EYE], "drive": "blink", "c": 1.0, "flags": ["mirror"], "at": EYE_AT, "way": up, "k2": -0.8},
	]
	ops.append_array(moves(true))
	return {
		"motion_length": LENGTH, "motion_nose": -0.5 * LENGTH, "wave": WAVE,
		# (the family's own wave is off: the fish's moves below carry it, by `swim`)
		"env_poly": Vector4.ZERO, "env_pow": Vector3(0.0, 0.0, 2.0),
		"swim_curl_from": -0.2 * LENGTH, "swim_curl_span": 0.7 * LENGTH,
		"ops": ops,
	}


## The moves the body and the see-through fins share (`body`: the jaw and gills too).
static func moves(body: bool) -> Array:
	var hinge := Vector3(0.0, HINGE_Y, (HINGE_S - 0.5) * LENGTH)
	var out := []
	if body:
		out.append_array([
			{"type": "turn", "parts": [JAW], "drive": "gape", "c": -1.0, "w": 1, "at": hinge, "way": Vector3.RIGHT},
			{"type": "turn", "parts": [JAW], "drive": "gape_breath", "c": -0.5, "a": 0.5, "beat": "breaths", "off": 0.5 * PI, "w": 1, "at": hinge, "way": Vector3.RIGHT},
			{"type": "move", "parts": [BODY], "drive": "gill_flare", "c": 0.5, "a": -0.5, "beat": "breaths", "off": -1.3 + 0.5 * PI, "w": 1,
				"flags": ["by_side"], "way": Vector3.RIGHT},
		])
	out.append_array([
		{"type": "move", "parts": [TAIL_FIN], "drive": "swim", "a": 0.02 * LENGTH, "beat": "tail_beats", "off": -1.1, "w": 1, "lag": 2, "per_lag": 1.0, "way": Vector3.RIGHT},
		{"type": "move", "parts": [FIN], "drive": "swim", "a": 0.012 * LENGTH, "beat": "tail_beats", "off": -1.0, "w": 1, "lag": 2, "per_lag": 1.0, "way": Vector3.RIGHT},
		# the wings: folded (their own way), then spread by `wings`
		{"type": "move", "parts": [WING], "c": 1.0, "flags": ["own_way"]},
		{"type": "move", "parts": [WING], "drive": "wings", "c": 1.0, "w": 1, "way": Vector3.RIGHT},
		{"type": "move", "parts": [WING], "drive": "wings", "c": 1.0, "w": 2, "way": Vector3.UP},
		{"type": "move", "parts": [WING], "drive": "wings", "c": 1.0, "w": 3, "way": Vector3.BACK},
		# the swimming wave: each point turned along the bent body (about its own place on the line),
		# then carried sideways
		{"type": "turn", "drive": "swim", "a": 1.0, "beat": "tail_beats", "w": W_TURN, "lag": W_TURN_LAG, "per_lag": 1.0,
			"flags": ["own_point"], "way": Vector3.UP},
		{"type": "move", "drive": "swim", "a": LENGTH, "beat": "tail_beats", "w": W_REACH, "lag": W_LAG, "per_lag": 1.0, "way": Vector3.RIGHT},
	])
	return out


static func label(p: Vector3, _n: Vector3, uv: Vector2, _uv2: Vector2, colour: Color, _old: Callable) -> Dictionary:
	var part := floori(colour.r * 10.0 + 0.5)
	var w := [0.0, 0.0, 0.0]
	var way := Vector3.ZERO
	var here := p
	if part == JAW:
		w[0] = smoothstep(0.06, 0.035, p.z / LENGTH + 0.5)
	elif part == BODY:
		w[0] = colour.g
	elif part == EYE:
		var sx := 1.0 if p.x >= 0.0 else -1.0
		var d := p - Vector3(EYE_AT.x * sx, EYE_AT.y, EYE_AT.z)
		w[0] = 1.0 if d.dot(Vector3(EYE_OUT.x * sx, EYE_OUT.y, EYE_OUT.z).normalized()) >= 0.0 else 0.0
	elif part >= WING:
		var mirror := -1.0 if colour.g > 0.5 else 1.0
		var folded := _wing(p, part, uv, mirror, 0.0)
		var spread := _wing(p, part, uv, mirror, 1.0)
		way = folded - p
		var moved := spread - folded
		w = [moved.x, moved.y, moved.z]
		here = folded
		part = WING
	elif part == 6 or part >= 4:
		var s := clampf(p.z / LENGTH + 0.5, 0.0, 1.05)
		w = [uv.x * uv.x, -TAU * s / WAVE - (0.0 if part == 6 else uv.y * 0.2)]
		part = TAIL_FIN if part == 6 else FIN
	# the wave, worked out where the point is before it (for a wing, folded)
	var sb := clampf(here.z / LENGTH + 0.5, 0.0, 1.05)
	var reach := 0.012 - 0.05 * sb + 0.14 * sb * sb
	var reach_slope := -0.05 + 0.28 * sb
	var k := TAU * reach / WAVE
	var lag := -TAU * sb / WAVE
	while w.size() < 3:
		w.append(0.0)
	w.append_array([Vector2(reach_slope, -k).length(), lag + atan2(-k, reach_slope), reach, lag])
	return {"part": part, "w": w, "way": way, "point": Vector3(0.0, here.y, here.z)}


# Where flying_fish.gdshader's wing_pose put a wing's point, `open` 0 folded, 1 spread.
static func _wing(p: Vector3, part: int, uv: Vector2, mirror: float, open: float) -> Vector3:
	var pect := part == 9
	var at := PECTORAL_AT if pect else PELVIC_AT
	var base := PECTORAL_BASE if pect else PELVIC_BASE
	var fan := PECTORAL_FAN if pect else PELVIC_FAN
	var shut := PECTORAL_SHUT if pect else PELVIC_SHUT
	var hug := PECTORAL_HUG if pect else PELVIC_HUG
	var spread := PECTORAL_SPREAD if pect else PELVIC_SPREAD
	var folded := PECTORAL_FOLDED if pect else PELVIC_FOLDED
	var t := uv.y / (PECTORAL_RAYS if pect else PELVIC_RAYS)
	var v := Vector3(p.x * mirror, p.y, p.z)
	var was := _frame(spread)
	var d := v - at
	var angle := t * fan
	var off := d.dot(was[2])
	var along := d.dot(was[0]) * cos(angle) + (d.dot(was[1]) - base * t) * sin(angle)
	var now := _frame(folded.lerp(spread, open))
	var angle_now := angle * lerpf(shut, 1.0, open)
	var bow := hug * (1.0 - open) * along * along
	v = at + now[1] * (base * t) + (now[0] * cos(angle_now) + now[1] * sin(angle_now)) * along + now[2] * (off + bow)
	return Vector3(v.x * mirror, v.y, v.z)


static func _frame(held: Vector3) -> Array:
	var a := Vector3(cos(held.x) * cos(held.y), sin(held.y), sin(held.x) * cos(held.y))
	var b := a.cross(Vector3.UP).normalized()
	var n := b.cross(a)
	return [a, b * cos(held.z) - n * sin(held.z), n * cos(held.z) + b * sin(held.z)]
