extends RefCounted
## The sea urchins' motion in the jointed family (scripts/motion.gd; GameCommon `godot/motion-families`),
## as sea_urchin.gdshader moved them: every spine (and tube foot, and pedicellaria) sways about its root on
## the test, each at its own time; a long spine bends, more towards its tip. Approximations: the old
## spine's tip went round a small ellipse (two tilts a quarter beat apart, at random times); here it tilts
## back and forth along that ellipse's long axis. Not drawn: leaning towards `threat` (the game never sets
## it).

const FAMILY := "jointed"

const SPINE := 1
const LONG := 2
const FOOT := 4


static func numbers(_old: Callable) -> Dictionary:
	var tilt := {"type": "turn", "drive": "sway", "w": 1, "lag": 2, "per_lag": 1.0, "flags": ["own_point", "own_way"]}
	return {
		"ops": [
			tilt.merged({"parts": [SPINE], "a": atan(0.07)}, true),
			tilt.merged({"parts": [LONG], "a": atan(0.55)}, true),
			tilt.merged({"parts": [FOOT], "a": atan(0.04)}, true),
		],
	}


static func _f(x: float) -> float:
	var a := PackedFloat32Array([x])
	return a[0]


static func _fract(x: float) -> float:
	return _f(x - floorf(x))


# hash2 as a GPU works it out in 32-bit floats.
static func _hash2(p: Vector2) -> float:
	var px := _f(p.x)
	var py := _f(p.y)
	var q := Vector3(_fract(_f(px * _f(0.1031))), _fract(_f(py * _f(0.1030))), _fract(_f(px * _f(0.0973))))
	var d := _f(_f(_f(q.x * _f(q.y + _f(33.33))) + _f(q.y * _f(q.z + _f(33.33)))) + _f(q.z * _f(q.x + _f(33.33))))
	q = Vector3(_f(q.x + d), _f(q.y + d), _f(q.z + d))
	return _fract(_f(_f(q.x + q.y) * q.z))


static func label(_p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, old: Callable) -> Dictionary:
	var part := int(uv2.y + 0.5)
	if part != SPINE and part != LONG and part != FOOT:
		return {"part": 0}
	var th := uv.y * PI
	var ph := uv.x * TAU
	var below_lean := float(old.call(&"below_lean"))
	var t := th if th < PI * 0.5 else PI * 0.5 + (th - PI * 0.5) * (1.0 - below_lean)
	var d := Vector3(sin(t) * cos(ph), cos(t), sin(t) * sin(ph))
	var c := cos(th)
	var rho := float(old.call(&"test_radius")) * sin(th)
	var tp := Vector3(rho * cos(ph), float(old.call(&"test_middle")) + (float(old.call(&"test_top")) if c > 0.0 else float(old.call(&"test_bottom"))) * c, rho * sin(ph))
	var root := tp - d * float(old.call(&"sink"))
	var e1 := d.cross(Vector3.UP if absf(d.y) < 0.9 else Vector3.RIGHT).normalized()
	var e2 := d.cross(e1)
	var h1 := _hash2(uv * 917.0) * TAU
	var h2 := _hash2(uv * 613.0 + Vector2(7.0, 7.0)) * TAU
	# m(t) = e1 sin(t + h1) + e2 cos(t + h2) = A sin t + B cos t; its long axis and its phase along it
	var a_ := e1 * cos(h1) - e2 * sin(h2)
	var b_ := e1 * sin(h1) + e2 * cos(h2)
	var xx := (a_.dot(e1) ** 2 + b_.dot(e1) ** 2)
	var yy := (a_.dot(e2) ** 2 + b_.dot(e2) ** 2)
	var xy := a_.dot(e1) * a_.dot(e2) + b_.dot(e1) * b_.dot(e2)
	var ang := 0.5 * atan2(2.0 * xy, xx - yy)
	var u := e1 * cos(ang) + e2 * sin(ang)
	var su := a_.dot(u)
	var cu := b_.dot(u)
	var reach := sqrt(su * su + cu * cu)
	var lag := atan2(cu, su)
	var w := reach * (uv2.x if part == LONG else 1.0)
	return {"part": part, "point": root, "way": d.cross(u).normalized(), "w": [w, lag]}
