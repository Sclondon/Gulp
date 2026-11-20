extends RefCounted
## The seahorse's motion in the jointed family (scripts/motion.gd; GameCommon `godot/motion-families`),
## as seahorse.gdshader moved it: the tail curled under (and curled right round as it grips, `grip`),
## swaying; the dorsal fin buzzing; the pectoral fins rowing; the snout's jaw opening; the cartoon eye
## grown and its blink; the whole body rocking and bobbing. The three seahorses differ by their settings
## (hinge, eye_skin, pec_root, tail_root, eye_size), read from each material; numbers from
## seahorse.gdshader. Differs: the tail goes from its loose curl to its tight one in a straight line, point
## by point (the old shader curled it along the way); exact loose and fully gripping, shortened between.
## The tail's normals keep their loose curl.

const FAMILY := "jointed"

const LENGTH := 0.15
const TIP_Y := -0.5
const GAPE_ANGLE := 0.7
const GAPE_LIFT := 0.12
const DEFAULTS := {&"hinge": Vector2(-0.232, 0.3785), &"eye_skin": Vector3(0.0411, 0.404, -0.068),
	&"pec_root": Vector3(0.0325, 0.338, 0.0388), &"tail_root": -0.06, &"eye_size": 1.7}

const UPPER := 1
const LOWER := 2
const EYE := 3
const DORSAL := 7
const PECTORAL := 8
const TAIL := 10


static func _value(old: Callable, name: StringName) -> Variant:
	var v: Variant = old.call(name)
	return v if v != null else DEFAULTS[name]


static func numbers(old: Callable) -> Dictionary:
	var hinge: Vector2 = _value(old, &"hinge")
	var eye_skin: Vector3 = _value(old, &"eye_skin")
	var pec: Vector3 = _value(old, &"pec_root")
	var eye_size: float = _value(old, &"eye_size")
	var at := Vector3(0.0, hinge.y, hinge.x) * LENGTH
	return {
		"ops": [
			{"type": "turn", "parts": [LOWER], "drive": "gape", "c": -GAPE_ANGLE, "w": 1, "at": at, "way": Vector3.RIGHT},
			{"type": "turn", "parts": [UPPER], "drive": "gape", "c": GAPE_LIFT, "w": 1, "at": at, "way": Vector3.RIGHT},
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"], "at": eye_skin * LENGTH,
				"k1": eye_size - 1.0, "k2": eye_size - 1.0},
			{"type": "scale", "parts": [EYE], "drive": "blink", "drive2": "cartoon_eyes", "c": 1.0, "flags": ["mirror"], "at": eye_skin * LENGTH,
				"way": Vector3.UP, "k2": -0.45},
			{"type": "move", "parts": [DORSAL], "drive": "row", "a": 0.014 * LENGTH, "beat": "buzzes", "w": 1, "lag": 2, "per_lag": -4.0, "way": Vector3.RIGHT},
			{"type": "turn", "parts": [PECTORAL], "drive": "row", "c": 0.1, "a": 0.5, "beat": "strokes", "side_off": PI,
				"flags": ["mirror"], "at": pec * LENGTH, "way": Vector3.UP},
			{"type": "move", "parts": [PECTORAL], "drive": "row", "a": 0.006 * LENGTH, "beat": "strokes", "off": -1.3, "side_off": PI, "w": 1,
				"flags": ["mirror"], "way": Vector3.RIGHT},
			# the tail: to its loose curl, towards its gripping curl, and its sway (sideways: the curl is up and down)
			{"type": "move", "parts": [TAIL], "c": 1.0, "flags": ["own_way"]},
			{"type": "draw", "parts": [TAIL], "drive": "grip", "c": 1.0, "flags": ["own_point"], "way": Vector3.ZERO},
			{"type": "move", "parts": [TAIL], "drive": "sway", "a": 0.03 * LENGTH, "beat": "bobs", "beats": 2.0, "w": 1, "lag": 2, "per_lag": -2.5, "way": Vector3.RIGHT},
			# the whole body rocks and bobs
			{"type": "turn", "drive": "bob", "a": 0.05, "beat": "bobs", "off": 1.2, "way": Vector3.RIGHT},
			{"type": "move", "drive": "bob", "a": 0.012 * LENGTH, "beat": "bobs", "way": Vector3.UP},
		],
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, _uv2: Vector2, colour: Color, old: Callable) -> Dictionary:
	var part := floori(colour.r * 10.0 + 0.5)
	var z := p.z / LENGTH
	var hinge: Vector2 = _value(old, &"hinge")
	if part == 2:
		return {"part": LOWER, "w": [smoothstep(hinge.x + 0.012, hinge.x - 0.004, z)]}
	if part == 1:
		return {"part": UPPER, "w": [smoothstep(hinge.x + 0.02, hinge.x - 0.004, z)]}
	if part == 3:
		return {"part": EYE}
	if part == 7:
		return {"part": DORSAL, "w": [pow(uv.x, 1.3), clampf(uv.y / 18.0, 0.0, 1.0)]}
	if part == 8:
		return {"part": PECTORAL, "w": [uv.x * uv.x]}
	var tail_root: float = _value(old, &"tail_root")
	var root_y := tail_root * LENGTH
	if p.y < root_y and (part == 0 or part == 5 or part == 6):
		var tail_long := (tail_root - TIP_Y) * LENGTH
		var l := clampf(root_y - p.y, 0.0, tail_long)
		var u := l / tail_long
		var loose := _curled(p, 0.0, root_y, tail_long)
		return {"part": TAIL, "w": [u * u, u], "way": loose - p, "point": _curled(p, 1.0, root_y, tail_long)}
	return {"part": part}


# Where seahorse.gdshader curled a point of the tail, gripping by `grip` (0..1); x is left alone.
static func _curled(p: Vector3, grip: float, root_y: float, tail_long: float) -> Vector3:
	var l := clampf(root_y - p.y, 0.0, tail_long)
	var u := l / tail_long
	var total := lerpf(0.75, 8.6, grip)
	var power := lerpf(2.4, 1.75, grip)
	var along := Vector2.ZERO
	var dl := l / 14.0
	for i in 14:
		var th := total * pow((float(i) + 0.5) * dl / tail_long, power)
		along += dl * Vector2(-cos(th), -sin(th))
	var th := total * pow(u, power)
	return Vector3(p.x, root_y + along.x - p.z * sin(th), along.y + p.z * cos(th))
