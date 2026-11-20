extends RefCounted
## The bat ray's motion in the flap family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## bat_ray.gdshader moved it: the disc's wings beat about the plane of the disc (a steady lift, the beat
## growing out to the tips, the tips `lag`ging the roots, the back of the wing a little after the
## front), the body's heave, the tail's wave, the turning curl of the rear, the jaw, the gill flaps,
## the cartoon eye grown and sunk a little. Numbers from bat_ray.gdshader. Its `lag` is read once, when
## it is dressed. (The old shader summed the wing in 6 steps, the family in 8; it clamped the chord's
## share to 0..1, the family does not: the very front and back of a wing differ by a few thousandths.)

const FAMILY := "flap"

const LENGTH := 1.4
const HALF := 0.7
const PLANE := -0.0235
const ROOT := 0.09
const HALF_SPAN := 0.6
const MOUTH_HINGE := 0.106
const MOUTH_Y := -0.0674
const EYE_AT := Vector3(0.07, 0.01562, -0.64)
const EYE_OUT := Vector3(0.8706, 0.42425, -0.24915)
const EYE_RADIUS := 0.011
const EYE_GROW := 2.3
const EYE_SINK := 0.3
const FLAP_W := 0.0084
const FLAP_OPEN := 0.6

# Parts (the model's UV2.y): 0 body (its wings), 1 jaw, 5 eyes, 8 gill flaps.
const JAW := 1
const EYE := 5
const GILL := 8


static func numbers(old: Callable) -> Dictionary:
	var lag: Variant = old.call(&"lag")
	return {
		"motion_length": LENGTH, "motion_nose": -HALF,
		"wing_root": ROOT, "wing_tip": HALF_SPAN, "wing_plane": PLANE, "wing_parts": 1,
		"wing_lift": Vector3(0.08, 0.0, 1.0), "wing_beat": Vector4(0.2, 0.8, 0.0, 4.0), "wing_tip_lag": 0.0,
		"wing_lag": Vector2(float(lag) if lag != null else 0.22, 0.06), "wing_chord_from": 0.1 - HALF, "wing_chord_span": 0.5,
		"wing_curl_bank": 0.0,
		"ops": [
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": EYE_AT, "way": EYE_OUT, "k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0},
			{"type": "move", "parts": [EYE], "drive": "cartoon_eyes", "c": -EYE_RADIUS * EYE_SINK * (EYE_GROW - 1.0),
				"flags": ["mirror"], "way": EYE_OUT.normalized()},
			{"type": "move", "parts": [GILL], "drive": "gape", "c": -FLAP_W * tan(FLAP_OPEN), "w": 1, "way": Vector3.UP},
			{"type": "move", "parts": [GILL], "drive": "gills", "c": -FLAP_W * tan(FLAP_OPEN), "w": 1, "way": Vector3.UP},
			{"type": "turn", "parts": [JAW], "drive": "gape", "c": -0.75,
				"at": Vector3(0.0, MOUTH_Y, MOUTH_HINGE - HALF), "way": Vector3.RIGHT},
			# after the wings: the heave, the tail's wave, the curl of the rear round to +x
			{"type": "move", "drive": "sway", "a": -0.02, "way": Vector3.UP, "flags": ["after"]},
			{"type": "move", "drive": "sway", "a": 0.05, "w": 2, "off": -0.6 * PI, "per_lag": -1.2 * PI, "lag": 3,
				"way": Vector3.UP, "flags": ["after"]},
			{"type": "bend", "drive": "curl", "c": 1.0, "way": Vector3.BACK, "k1": 0.5 - HALF, "k2": LENGTH - 0.5,
				"flags": ["after"]},
		],
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, _old: Callable) -> Dictionary:
	var part := int(round(uv2.y))
	var t := maxf(0.0, (p.z + HALF - 0.66) / (LENGTH - 0.66))
	var gill := uv.x if part == GILL else 0.0
	return {"part": part, "w": [gill, t * t, t]}
