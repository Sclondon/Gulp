extends RefCounted
## The spotted eagle ray's motion in the flap family (scripts/motion.gd; GameCommon
## `godot/motion-families`), as spotted_eagle_ray.gdshader moved it: the wings beat (bending out along
## the span, the beat running out to the tips and back along the chord, the tips trailing), the long
## tail's wave, the body's pitch, heave and bank, the jaw, the gill flaps, the cartoon eye grown.
## Numbers from spotted_eagle_ray.gdshader.

const FAMILY := "flap"

const HALF := 1.0
const DISC := 1.15
const TAIL_LENGTH := 2.7
const HINGE := Vector2(-0.0801, -0.365)
const JAW_TURN := 0.75
const ROOT := 0.14
const FLAP := 0.7
const LIFT := 0.1
const TIP_LAG := 0.24
const BACK_LAG := 0.1
const PITCH := 0.05
const HEAVE := 0.03
const EYE_AT := Vector3(0.107, 0.03, -0.35)
const EYE_OUT := Vector3(0.86528, 0.45809, -0.20359)
const EYE_GROW := 1.6
const FLAP_W := 0.01656
const FLAP_OPEN := 0.6

# Parts (the model's UV2.y): 0 body, 1 jaw, 6 eyes, 8 gill flaps.
const EYE := 6
const GILL := 8


static func numbers(_old: Callable) -> Dictionary:
	return {
		"motion_length": 2.0 * HALF, "motion_nose": -HALF,
		"wing_root": ROOT * HALF, "wing_tip": HALF, "wing_plane": 0.0, "wing_parts": 0xFFFFFF,
		"wing_lift": Vector3(0.0, LIFT, 1.15), "wing_beat": Vector4(0.0, FLAP, 0.45 * FLAP, 4.0), "wing_tip_lag": 0.9,
		"wing_lag": Vector2(TIP_LAG, BACK_LAG), "wing_chord_from": -0.5 * DISC, "wing_chord_span": DISC, "wing_curl_bank": 0.35,
		"ops": [
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": EYE_AT, "way": EYE_OUT, "k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0},
			{"type": "move", "parts": [GILL], "drive": "gape", "c": -FLAP_W * tan(FLAP_OPEN), "w": 5, "way": Vector3.UP},
			{"type": "move", "parts": [GILL], "drive": "gills", "c": -FLAP_W * tan(FLAP_OPEN), "w": 5, "way": Vector3.UP},
			{"type": "turn", "parts": [0, 1], "drive": "gape", "c": -JAW_TURN, "w": 1,
				"at": Vector3(0.0, HINGE.x, HINGE.y), "way": Vector3.RIGHT},
			# after the wings: the tail's wave and sideways curl, pitch, heave, bank
			{"type": "move", "drive": "sway", "a": 0.035 * TAIL_LENGTH, "w": 2, "off": -0.4 * PI, "per_lag": -3.2 * PI, "lag": 3,
				"way": Vector3.UP, "flags": ["after"]},
			{"type": "move", "drive": "curl", "c": 1.0, "w": 4, "way": Vector3.RIGHT, "flags": ["after"]},
			{"type": "turn", "drive": "sway", "a": PITCH, "off": 0.5 * PI, "way": Vector3.RIGHT, "flags": ["after"]},
			{"type": "move", "drive": "sway", "a": -HEAVE, "off": -0.16 * PI, "way": Vector3.UP, "flags": ["after"]},
			{"type": "turn", "drive": "curl", "c": -0.6, "way": Vector3.BACK, "flags": ["after"]},
		],
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, _old: Callable) -> Dictionary:
	var part := int(round(uv2.y))
	var behind := maxf(p.z - (DISC * 0.5 - 0.08 * DISC), 0.0)
	var f := behind / TAIL_LENGTH
	var jaw := uv.x if part <= 1 and uv.x > 0.0 else 0.0
	var gill := uv.x if part == GILL else 0.0
	return {"part": part, "w": [jaw, pow(f, 1.3), f, behind * behind / (2.0 * TAIL_LENGTH), gill, 0.0, 0.0]}
