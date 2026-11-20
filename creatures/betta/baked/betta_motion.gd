extends RefCounted
## The betta's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## betta.gdshader moved it (it worked in body lengths, `length_m` a metre count; here in metres): the wave
## back along the body, the long tail swung half as much as the body and trailing; the fins billowing,
## rippling and (the tail) pleated, folded back while calm and spread wide as it flares (`flare`): the
## tail fanned open, the dorsal and anal fins raised, the pelvic fins swung down, the gill covers turned
## out and the beard brought out and ruffled; the lower jaw, the back of the mouth and the gill arches as
## it opens; the curl; the cartoon eye grown. Numbers from betta.gdshader.
## Differs: the fins' billow, ripple and pleat are worked out where the fins lie calm (the old shader
## worked them out where the flare had moved them); the beard comes out evenly with `flare` (the old one
## eased in and out); the fins' normals are not tilted by the ripples.

const FAMILY := "swim"

const HALF := 0.5
const JOINT := 0.535
const EYE_AT := Vector2(0.072, 0.016)
const EYE_RADIUS := 0.028
const JAW_TO := 0.037
const HINGE_Y := -0.01265
const GAPE_OPEN := 1.0
const TAIL_PIVOT := 0.525
const COVER_HINGE := Vector2(0.0485, 0.098)
const BEARD_LONG := 0.08
const BEARD_RUFFLE := 0.012
const BEARD_WAY := Vector3(0.8554, -0.2516, 0.4528)
const GILL_FROM := 0.0826
const GILL_TO := 0.151
const WALL_UP := 0.0141
const EYE_BIG := 1.6

const DORSAL := 1
const ANAL := 2
const TAIL := 3
const PELVIC := 5
const EYE := 6
const JAW := 7
const COVER := 8
const BEARD := 9
const GILL := 10
const WALL := 11
# (a part behind the joint is its number + BEHIND: what is there turns only half the body's turn)
const BEHIND := 12


static func numbers(old: Callable) -> Dictionary:
	var length := float(old.call(&"length_m")) if old.call(&"length_m") != null else 0.065
	var wave := float(old.call(&"wave")) if old.call(&"wave") != null else 1.1
	var big := EYE_BIG
	var fins := [DORSAL, ANAL, TAIL, PELVIC, DORSAL + BEHIND, ANAL + BEHIND, TAIL + BEHIND, PELVIC + BEHIND]
	# (the body's slope at the joint, as a sine: what is behind the joint turns half of it)
	var reach := 0.006 - 0.022 + 0.07
	var reach_slope := (-0.022 + 2.0 * 0.07) / JOINT
	var k := TAU * reach / wave
	var size := Vector2(reach_slope, -k).length()
	var lead := atan2(-k, reach_slope)
	var bw := Vector3(BEARD_WAY.x, BEARD_WAY.y, BEARD_WAY.z)
	var across := Vector3.UP.cross(bw).normalized()
	return {
		"motion_length": length, "motion_nose": -HALF * length,
		"env_poly": Vector4(0.006, -0.022 / JOINT, 0.07 / (JOINT * JOINT), 0.0),
		"swim_from": -10.0, "swim_joint": JOINT,
		"swim_curl_from": -0.2 * length, "swim_curl_span": 0.7 * length,
		"ops": [
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "at": Vector3(0.0, EYE_AT.y, EYE_AT.x - HALF) * length,
				"way": Vector3.RIGHT, "k1": big - 1.0},
			{"type": "move", "parts": [EYE], "drive": "cartoon_eyes", "c": (big - 1.0) * EYE_RADIUS * length, "flags": ["mirror"], "way": Vector3(0.3, 0.0, 0.8)},
			{"type": "draw", "parts": [WALL], "drive": "gape", "shape": "on", "c": 1.0, "at": Vector3(0.0, WALL_UP * length, 0.0), "way": Vector3.UP},
			{"type": "scale", "parts": [WALL], "drive": "gape", "shape": "on", "c": 1.0, "way": Vector3.RIGHT, "k2": -0.45},
			{"type": "move", "parts": [WALL], "drive": "gape", "shape": "on", "c": 0.004 * length, "way": Vector3.BACK},
			{"type": "scale", "parts": [GILL], "drive": "gape", "c": 1.0, "way": Vector3.RIGHT, "k2": 0.1},
			{"type": "scale", "parts": [GILL], "drive": "gape", "c": 1.0, "at": Vector3(0.0, 0.0, (0.5 * (GILL_FROM + GILL_TO) - HALF) * length),
				"way": Vector3.BACK, "k2": 0.15},
			{"type": "turn", "parts": [JAW], "drive": "gape", "c": -GAPE_OPEN, "w": 1, "at": Vector3(0.0, HINGE_Y, JAW_TO - HALF) * length, "way": Vector3.RIGHT},
			{"type": "turn", "parts": [COVER], "drive": "flare", "c": 1.1, "flags": ["mirror"],
				"at": Vector3(COVER_HINGE.x, 0.0, COVER_HINGE.y - HALF) * length, "way": Vector3.UP},
			# the beard: folded in (its own way, the spread) unless flaring, ruffled when out
			{"type": "move", "parts": [BEARD], "c": -1.0, "plus": -(-1.0), "drive3": "flare", "flags": ["own_way"]},
			{"type": "move", "parts": [BEARD], "drive": "flare", "drive2": "flow", "a": 0.006 * length, "beat": "ripples", "w": 1, "lag": 2,
				"per_lag": -9.0, "flags": ["mirror"], "way": across},
			# the fins calm (folded back) less the flare's share
			{"type": "turn", "parts": [TAIL, TAIL + BEHIND], "c": 1.0, "plus": -(1.0), "drive3": "flare", "w": 7, "at": Vector3(0.0, 0.0, (TAIL_PIVOT - HALF) * length), "way": Vector3.RIGHT},
			{"type": "move", "parts": [DORSAL, DORSAL + BEHIND], "c": length, "plus": -(length), "drive3": "flare", "w": 6, "way": Vector3(0.0, -0.42, 0.95)},
			{"type": "move", "parts": [ANAL, ANAL + BEHIND], "c": length, "plus": -(length), "drive3": "flare", "w": 6, "way": Vector3(0.0, 0.15, 0.75)},
			{"type": "turn", "parts": [PELVIC, PELVIC + BEHIND], "c": -0.75, "plus": -(-0.75), "drive3": "flare", "at": Vector3(0.0, -0.07, 0.2 - HALF) * length, "way": Vector3.RIGHT},
			# the fins sideways: the trail behind the joint (less as it flares), the billow and the ripples (loose:
			# flow, less as it flares), the tail's pleats (calm only)
			{"type": "move", "parts": fins, "drive": "sway", "a": 0.3 * length, "beat": "tail_beats", "off": -0.5, "per_s": -TAU / wave, "w": 1, "way": Vector3.RIGHT},
			{"type": "move", "parts": fins, "drive": "sway", "drive2": "flare", "a": -0.15 * length, "beat": "tail_beats", "off": -0.5, "per_s": -TAU / wave, "w": 1, "way": Vector3.RIGHT},
			{"type": "move", "parts": fins, "drive": "flow", "a": 0.05 * length, "beat": "billows", "w": 2, "lag": 3, "per_lag": 1.0, "way": Vector3.RIGHT},
			{"type": "move", "parts": fins, "drive": "flow", "drive2": "flare", "a": -0.75 * 0.05 * length, "beat": "billows", "w": 2, "lag": 3, "per_lag": 1.0, "way": Vector3.RIGHT},
			{"type": "move", "parts": fins, "drive": "flow", "a": 0.01 * length, "beat": "ripples", "w": 4, "lag": 5, "per_lag": 1.0, "way": Vector3.RIGHT},
			{"type": "move", "parts": fins, "drive": "flow", "drive2": "flare", "a": -0.75 * 0.01 * length, "beat": "ripples", "w": 4, "lag": 5, "per_lag": 1.0, "way": Vector3.RIGHT},
			{"type": "move", "parts": [TAIL, TAIL + BEHIND], "c": length, "plus": -(length), "drive3": "flare", "w": 6, "way": Vector3.RIGHT},
			# what is behind the joint turned back by half the body's turn there
			{"type": "turn", "drive": "sway", "a": -0.5 * size, "beat": "tail_beats", "off": -TAU * JOINT / wave + lead,
				"parts": [BEHIND, DORSAL + BEHIND, ANAL + BEHIND, TAIL + BEHIND, 4 + BEHIND, PELVIC + BEHIND], "at": Vector3(0.0, 0.0, (JOINT - HALF) * length), "way": Vector3.UP},
		],
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, old: Callable) -> Dictionary:
	var length := float(old.call(&"length_m")) if old.call(&"length_m") != null else 0.065
	var v := p / length
	var xm := v.z + HALF
	var part := int(uv2.y + 0.5)
	var behind := BEHIND if xm >= JOINT else 0
	if part == EYE:
		return {"part": EYE}
	if part == 0 and uv2.x > 0.999 and uv.y > 0.45 and uv.y < 0.55 and absf(xm - JAW_TO) < 0.0005:
		return {"part": WALL}
	if part == GILL:
		return {"part": GILL}
	if part == JAW:
		return {"part": JAW, "w": [1.0 - smoothstep(JAW_TO - 0.016, JAW_TO - 0.002, xm)]}
	if part == COVER:
		return {"part": COVER}
	if part == BEARD:
		var sx := 1.0 if v.x >= 0.0 else -1.0
		var way := Vector3(BEARD_WAY.x * sx, BEARD_WAY.y, BEARD_WAY.z)
		var across := Vector3.UP.cross(way).normalized()
		var t := uv.x
		var u := uv.y
		var reach := BEARD_LONG * (0.6 + 0.4 * sin(PI * u))
		var spread := way * (t * reach) + across * (BEARD_RUFFLE * t * sin(u * 6.0 * PI))
		return {"part": BEARD, "w": [t, u], "way": spread * length}
	if part == DORSAL or part == ANAL or part == TAIL or part == PELVIC:
		# (where the fin lies calm: the lateral moves are worked out there)
		var calm := v
		var h := 0.0
		var turn := 0.0
		var pleat := 0.0
		if part == TAIL:
			var d := Vector2(xm - TAIL_PIVOT, v.y)
			var r := d.length()
			var a := atan2(d.y, d.x)
			var w := smoothstep(0.03, 0.1, r)
			var a2 := lerpf(a, a * 0.42 - 0.32, w)
			turn = -(a2 - a)
			calm = Vector3(v.x, r * sin(a2), TAIL_PIVOT - HALF + r * cos(a2))
		elif part == DORSAL:
			h = maxf(v.y - 0.055, 0.0)
			calm = v + Vector3(0.0, -0.42, 0.95) * h
		elif part == ANAL:
			h = maxf(-0.065 - v.y, 0.0)
			calm = v + Vector3(0.0, 0.15, 0.75) * h
		else:
			var root := Vector2(-0.07, 0.2 - HALF)
			var dd := Vector2(v.y - root.x, v.z - root.y)
			var ca := cos(-0.75)
			var sa := sin(-0.75)
			calm = Vector3(v.x, root.x + dd.x * ca - dd.y * sa, root.y + dd.x * sa + dd.y * ca)
		var cx := calm.z + HALF
		var cy := calm.y
		var away := _out_of(cx, cy, part)
		var dj := maxf(cx - JOINT, 0.0)
		var offset := 1.7 if part == ANAL else (3.1 if part == DORSAL else 0.0)
		if part == TAIL:
			var dt := Vector2(cx - TAIL_PIVOT, cy)
			var rt := dt.length()
			pleat = 0.035 * rt * smoothstep(0.03, 0.12, rt) * sin(atan2(dt.y, dt.x) * 16.0)
		return {"part": part + (BEHIND if cx >= JOINT else 0), "w": [dj * sqrt(dj), away * away, -away * 4.0 + offset, smoothstep(0.02, 0.15, away),
			-cx * 26.0 + cy * 34.0, pleat if part == TAIL else h, turn]}
	return {"part": part + behind if part == 0 or part == 4 else part}


static func _out_of(xm: float, y: float, p: int) -> float:
	if p == TAIL:
		return Vector2(xm - TAIL_PIVOT, y).length()
	elif p == DORSAL:
		return maxf(y - 0.06, 0.0)
	elif p == ANAL:
		return maxf(-0.07 - y, 0.0)
	return maxf(-0.08 - y, 0.0) * 0.8
