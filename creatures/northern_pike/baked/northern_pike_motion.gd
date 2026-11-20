extends RefCounted
## The northern pike's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`),
## as northern_pike.gdshader moved it: the wave back along the body, the tail one plate behind its wrist,
## the turning curl, the lower jaw swinging down and the snout lifting, the cartoon eye grown and squeezed
## as it blinks, and the throat: shut, the inside of the mouth and the gill arches are folded away to one
## point in the throat; open, the ring at the back of the mouth is drawn there and the arches spread.
## Differs: the ring goes to the throat at once as the mouth starts to open (the old shader eased it over
## the first third), and the eye's slight sag as it grows is left out.

const FAMILY := "swim"

const LENGTH := 1.0
const HALF := 0.5
const JOINT := 0.866
const JAW_TO := 0.135
const HINGE_Y := -0.009075
const GAPE_OPEN := 0.55
const SNOUT_LIFT := 0.07
const THROAT_Q := Vector3(0.0, -0.01961, -0.29303)
const EYE_MID := Vector3(0.03328, 0.0265, -0.347)
const EYE_GROW := 1.6

# Parts (the model's UV2.y): 0 the body, 6 an eye, 7 the lower jaw, 8 the snout's parts, 9 the lower
# teeth, 10 a gill arch; ours: the ring at the back of the mouth, the inside behind it.
const BODY := 0
const EYE := 6
const JAW := 7
const SNOUT := 8
const TEETH := 9
const GILL := 10
const RING := 11
const INSIDE := 12


static func numbers(_old: Callable) -> Dictionary:
	var k := LENGTH / JOINT
	var hinge := Vector3(0.0, HINGE_Y, JAW_TO - HALF)
	return {
		"motion_length": LENGTH, "motion_nose": -HALF,
		"env_poly": Vector4(0.006, -0.026 * k, 0.08 * k * k, 0.0),
		"swim_from": -10.0, "swim_joint": JOINT / LENGTH, "swim_wrist": 0.2, "swim_wrist_from": 0.86 * JOINT / LENGTH,
		"swim_curl_from": -0.2 * LENGTH, "swim_curl_span": 0.7 * LENGTH,
		"ops": [
			{"type": "draw", "parts": [RING], "drive": "gape", "shape": "on", "c": 1.0, "at": THROAT_Q, "way": Vector3.ZERO},
			# (shut: folded away into the throat)
			{"type": "draw", "parts": [INSIDE, GILL], "drive": "gape", "shape": "on", "c": -1.0, "plus": 1.0, "at": THROAT_Q, "way": Vector3.ZERO},
			{"type": "scale", "parts": [GILL], "drive": "gape", "c": 1.0, "way": Vector3.RIGHT, "k2": 0.12},
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": EYE_MID, "k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0},
			{"type": "scale", "parts": [EYE], "drive": "blink", "c": 1.0, "flags": ["mirror"],
				"at": EYE_MID, "way": Vector3.UP, "k2": -0.85},
			{"type": "turn", "parts": [JAW, TEETH], "drive": "gape", "c": -GAPE_OPEN, "at": hinge, "way": Vector3.RIGHT},
			{"type": "turn", "parts": [BODY, EYE, SNOUT], "drive": "gape", "c": SNOUT_LIFT, "w": 1, "at": hinge, "way": Vector3.RIGHT},
		],
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, _old: Callable) -> Dictionary:
	var part := int(round(uv2.y))
	if part == BODY and uv2.x > 0.99:
		if absf(uv.x - JAW_TO / LENGTH) < 0.0001:
			return {"part": RING}
		if uv.x > JAW_TO / LENGTH + 0.0001:
			return {"part": INSIDE}
	return {"part": part, "w": [1.0 - smoothstep(JAW_TO * 0.4, JAW_TO, p.z + HALF)]}
