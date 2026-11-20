extends RefCounted
## The whale shark's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`),
## as whale_shark.gdshader moved it: the wave back along the body (a little sway at the head, most behind
## its middle), the turning curl, the jaws (the lower jaw swinging down, its teeth and the cheeks' lower
## edges with it, the gill slits opening, the upper jaw pushed out and down), the cartoon eye grown.
## Differs: the head's small sway, 0.014 * (1 - smoothstep(0, 0.3, s)) in the old shader, is a cubic
## here (off by up to a sixth of it, a few millimetres); the tail tip behind s 1.0 turns as one plate
## (the family's wrist needs a joint); the slits open in step with the mouth (the old shader eased them).

const FAMILY := "swim"

const LENGTH := 10
const HINGE_S := 0.058
const HINGE_Y := -0.03
const JAW_TURN := 0.6
const PUSH := 0.003
const PUSH_DOWN := -0.03
const GILL_SPREAD := 0.004
const SLIT_LIFT := 0.0085
const EYE_MID := Vector3(0.7629, 0.06, -4.38)
const EYE_GROW := 2.4
const BOW := 0.02
const JAW_HALF := 0.066

# Parts (the model's COLOR.r * 20): 1 the lower jaw, 2 an eye, 4 the lower teeth, 11 a cheek, 12 a gill
# arch, 13 and over the gill slits.
const JAW := 1
const EYE := 2
const TEETH := 4
const CHEEK := 11
const ARCH := 12
const SLIT := 13


static func numbers(_old: Callable) -> Dictionary:
	var a := 0.012
	var hinge := Vector3(0.0, HINGE_Y, HINGE_S - 0.5) * LENGTH
	return {
		"motion_length": LENGTH, "motion_nose": -0.5 * LENGTH,
		"env_poly": Vector4(1.16772 * a + 0.004, -6.14294 * a, 9.93144 * a, -5.02743 * a),
		"env_pow": Vector3(0.085, 0.18, 1.6),
		"swim_from": -10.0, "swim_joint": 1.0, "swim_wrist": 0.25, "swim_wrist_from": 0.8,
		"swim_curl_from": -0.25 * LENGTH, "swim_curl_span": 0.75 * LENGTH,
		"ops": [
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": EYE_MID, "k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0},
			{"type": "move", "parts": [JAW], "drive": "gape", "c": -BOW * LENGTH, "w": 2, "way": Vector3.UP},
			{"type": "move", "parts": [ARCH], "drive": "gape", "c": GILL_SPREAD * LENGTH, "w": 2, "way": Vector3.BACK},
			{"type": "turn", "parts": [JAW, CHEEK, ARCH], "drive": "gape", "c": -JAW_TURN, "w": 1, "at": hinge, "way": Vector3.RIGHT},
			{"type": "turn", "parts": [TEETH], "drive": "gape", "c": -JAW_TURN, "at": hinge, "way": Vector3.RIGHT},
			{"type": "move", "parts": [SLIT], "drive": "gape", "c": SLIT_LIFT * LENGTH, "w": 1, "flags": ["own_way"]},
			{"type": "move", "drive": "gape", "c": LENGTH, "w": 3, "way": Vector3(0.0, -PUSH_DOWN, -PUSH)},
		],
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, _uv2: Vector2, colour: Color, _old: Callable) -> Dictionary:
	var part := int(floor(colour.r * 20.0 + 0.5))
	var s := p.z / LENGTH + 0.5
	var push := colour.g
	if part == JAW:
		return {"part": JAW, "w": [smoothstep(HINGE_S + 0.045, HINGE_S - 0.02, s), maxf(0.0, 1.0 - pow(p.x / (JAW_HALF * LENGTH), 2.0)) * smoothstep(HINGE_S, HINGE_S - 0.03, s), push]}
	if part == CHEEK or part == ARCH:
		return {"part": part, "w": [uv.x, uv.y - 0.5 if part == ARCH else 0.0, push]}
	if part >= SLIT:
		return {"part": SLIT, "w": [colour.b, 0.0, push], "way": Vector3(p.x, 0.6 * p.y, 0.0).normalized()}
	return {"part": part, "w": [0.0, 0.0, push]}
