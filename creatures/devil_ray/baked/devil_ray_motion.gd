extends RefCounted
## The devil ray's motion in the flap family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## devil_ray.gdshader moved it (the manta's, in small): the wings beat (bending out along the span, the beat running out to the
## tips and back along the chord, the tips trailing), the tail's wave, the body's pitch, heave and bank,
## the jaw, the gill flaps, the cartoon eye grown. The cephalic fins, which the old shader built from
## their UVs and unrolled as it fed (`scoops`), are put where it put them rolled and drawn straight to
## where it put them unrolled (the old one rolled them along a curve). Numbers from devil_ray.gdshader.

const FAMILY := "flap"

const HALF := 0.5
const DISC := 0.52
const TAIL_LENGTH := 0.5
const HINGE := Vector2(-0.0473, -0.17)
const JAW_TURN := 0.75
const CEPH_ROOT := Vector3(0.07, 0.004, -0.215)
const CEPH_ALONG := Vector3(0.11767, -0.15689, -0.98058)
const CEPH_DOWN := Vector3(-0.25908, -0.95809, 0.12221)
const CEPH_IN := Vector3(-0.95866, 0.23967, -0.15339)
const CEPH_LENGTH := 0.105
const CEPH_WIDTH := 0.05
const CEPH_ROLL0 := 66.0
const CEPH_ROLL1 := 108.0
const CEPH_CUP := 14.0
const ROOT := 0.15
const FLAP := 0.72
const LIFT := 0.08
const TIP_LAG := 0.2
const BACK_LAG := 0.1
const PITCH := 0.06
const HEAVE := 0.014
const EYE_AT := Vector3(0.083, 0.008, -0.198)
const EYE_OUT := Vector3(0.88498, 0.20823, -0.41646)
const EYE_GROW := 1.9
const FLAP_W := 0.0104
const FLAP_OPEN := 0.6

# Parts (the model's UV2.y): 0 body, 1 jaw, 2 cephalic fins, 6 eyes, 8 gill flaps.
const CEPH := 2
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
			# (the cephalic fins: rolled as the old shader rolled them, then unrolled towards their open shape)
			{"type": "move", "parts": [CEPH], "c": 1.0, "flags": ["own_way"]},
			{"type": "draw", "parts": [CEPH], "drive": "scoops", "c": 1.0, "flags": ["own_point"], "way": Vector3.ZERO},
			{"type": "turn", "parts": [0, 1], "drive": "gape", "c": -JAW_TURN, "w": 1,
				"at": Vector3(0.0, HINGE.x, HINGE.y), "way": Vector3.RIGHT},
			# after the wings: the tail's wave and sideways curl, pitch, heave, bank
			{"type": "move", "drive": "sway", "a": 0.05 * TAIL_LENGTH, "w": 2, "off": -0.4 * PI, "per_lag": -1.8 * PI, "lag": 3,
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
	var out := {"part": part, "w": [jaw, pow(f, 1.5), f, behind * behind / (2.0 * TAIL_LENGTH), gill, 0.0, 0.0]}
	if part == CEPH:
		var sx := 1.0 if p.x >= 0.0 else -1.0
		var rolled := _ceph_point(uv.x, uv.y, uv2.x, sx, 0.0)
		out["way"] = rolled - p
		out["point"] = _ceph_point(uv.x, uv.y, uv2.x, sx, 1.0)
	return out


# Where devil_ray.gdshader put a point of a cephalic fin (`t` along it, `h` across it, `off` out
# of its middle sheet, its side), rolled (open 0) or unrolled (open 1).
static func _ceph_point(t: float, h: float, off: float, sx: float, open: float) -> Vector3:
	var k0 := lerpf(CEPH_ROLL0, CEPH_CUP, open)
	var k1 := CEPH_ROLL1 * (1.0 - open) / (2.0 * CEPH_WIDTH)
	var q := Vector2.ZERO
	var dh := h / 12.0
	for i in 12:
		var hm := (float(i) + 0.5) * dh
		var th := k0 * hm + k1 * hm * hm
		q += Vector2(cos(th), sin(th)) * dh
	var th := k0 * h + k1 * h * h
	var flip := Vector3(sx, 1.0, 1.0)
	var normal := (CEPH_IN * cos(th) - CEPH_DOWN * sin(th)) * flip
	return (CEPH_ROOT + CEPH_ALONG * (t * CEPH_LENGTH) + CEPH_DOWN * q.x + CEPH_IN * q.y) * flip + normal * off
