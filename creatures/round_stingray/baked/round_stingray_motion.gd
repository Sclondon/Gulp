extends RefCounted
## The round stingray's motion in the jointed family (scripts/motion.gd; GameCommon
## `godot/motion-families`), as round_stingray.gdshader moved it: ripples run round the rim of the disc
## from front to back (`waves` of them along each side, read once when it is dressed), the tail waves,
## the rear curls round, the jaw opens, the gill flaps lift, the cartoon eye is grown and sunk. Each
## point's share of the ripple and its place round the rim are worked out once from its place at rest.
## The old shader also tipped the normals with the ripple; the family does not (light per vertex only).

const FAMILY := "jointed"

const LENGTH := 0.5
const HALF := 0.25
const DISC_MID := 0.145
const DISC_LONG := 0.145
const DISC_WIDE := 0.14
const MOUTH_HINGE := 0.072
const MOUTH_Y := -0.0274
const EYE_MIDDLE := Vector3(0.029, 0.01851, -0.162)
const EYE_OUT := Vector3(0.63186, 0.7729, -0.05818)
const EYE_RADIUS := 0.007
const EYE_GROW := 2.0
const EYE_SINK := 0.3
const FLAP_W := 0.0044
const FLAP_OPEN := 0.6

const JAW := 1
const EYE := 5
const GILL := 8


static func numbers(old: Callable) -> Dictionary:
	var waves: Variant = old.call(&"waves")
	return {
		"motion_length": LENGTH, "motion_nose": -HALF,
		"ops": [
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": EYE_MIDDLE, "way": EYE_OUT, "k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0},
			{"type": "move", "parts": [EYE], "drive": "cartoon_eyes", "c": -EYE_RADIUS * EYE_SINK * (EYE_GROW - 1.0),
				"flags": ["mirror"], "way": EYE_OUT.normalized()},
			{"type": "move", "parts": [GILL], "drive": "gape", "c": -FLAP_W * tan(FLAP_OPEN), "w": 1, "way": Vector3.UP},
			{"type": "move", "parts": [GILL], "drive": "gills", "c": -FLAP_W * tan(FLAP_OPEN), "w": 1, "way": Vector3.UP},
			{"type": "turn", "parts": [JAW], "drive": "gape", "c": -0.75,
				"at": Vector3(0.0, MOUTH_Y, MOUTH_HINGE - HALF), "way": Vector3.RIGHT},
			# the ripple round the rim: sway * reach * sin(TAU * (phase - waves * round / PI))
			{"type": "move", "drive": "sway", "a": 1.0, "w": 2, "lag": 3, "per_lag": -2.0 * (float(waves) if waves != null else 1.4),
				"way": Vector3.UP},
			# the tail's wave, then the curl of the rear round to +x
			{"type": "move", "drive": "sway", "a": 0.014, "w": 4, "lag": 5, "per_lag": -0.8 * PI, "way": Vector3.RIGHT,
				"flags": ["after"]},
			{"type": "bend", "drive": "curl", "c": 1.0, "way": Vector3.BACK, "k1": 0.25 - HALF, "k2": LENGTH - 0.25,
				"flags": ["after"]},
		],
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, _old: Callable) -> Dictionary:
	var part := int(round(uv2.y))
	var xm := p.z + HALF
	var d := Vector2(p.x / DISC_WIDE, (xm - DISC_MID) / DISC_LONG)
	var rim := smoothstep(0.4, 1.0, d.length())
	var round_it := atan2(absf(d.x), -d.y)
	var reach := 0.02 * rim * sqrt(rim) * (0.4 + 0.6 * smoothstep(0.0, 0.9, round_it)) * (1.0 - smoothstep(2.3, 2.95, round_it))
	var t := maxf(0.0, (xm - 0.27) / (LENGTH - 0.27))
	var gill := uv.x if part == GILL else 0.0
	return {"part": part, "w": [gill, reach, round_it, t * t, t]}
