extends RefCounted
## The arowana's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## arowana.gdshader moved it: the wave back along the long body to the tail plate, the turning curl and
## the arch (its own arch bends the other way from the family's, so its span is negative), the lower jaw
## swinging down and the snout lifting a little, the throat's ring drawn to the back of the mouth as it
## opens and the inside folded away while it is shut, the gill arches widening, the cartoon eye grown
## (with its sag outward) and blinking. Numbers from arowana.gdshader. (The ring's draw is all or nothing
## here: the old one eased it in over the first third of the gape.)

const FAMILY := "swim"

const LENGTH := 0.9
const HALF := 0.45
const JOINT := 0.805
const JAW_TO := 0.105
const HINGE_Y := -0.005
const GAPE_OPEN := 0.8
const SNOUT_LIFT := 0.06
const THROAT_Q := Vector3(0.0, -0.01881, -0.30150)
const EYE_MID := Vector3(0.01838, 0.04000, -0.38200)
const EYE_OUT := Vector3(0.9873, 0.1409, -0.0741)
const EYE_SAG := Vector2(-4.398, -0.563)
const EYE_GROW := 1.55

# Parts: the model's (UV2.y: 6 eye, 7 and 8 the lower jaw, 9 gill arches) and ours.
const EYE := 6
const GILL := 9
const RING := 12
const INSIDE := 13


static func numbers(_old: Callable) -> Dictionary:
	var k := LENGTH / JOINT
	var hinge := Vector3(0.0, HINGE_Y, JAW_TO - HALF)
	return {
		"motion_length": LENGTH, "motion_nose": -HALF,
		"env_poly": Vector4(0.009, -0.03 * k, 0.078 * k * k, 0.0),
		"swim_from": -10.0, "swim_joint": JOINT / LENGTH, "swim_wrist": 0.15, "swim_wrist_from": 0.86 * JOINT / LENGTH,
		"swim_curl_from": -0.2 * LENGTH, "swim_curl_span": 0.7 * LENGTH,
		"swim_arch_from": 0.0, "swim_arch_span": -LENGTH, "swim_arch_both": true,
		"ops": [
			{"type": "draw", "parts": [RING], "drive": "gape", "shape": "on", "c": 1.0, "at": THROAT_Q, "way": Vector3.ZERO},
			{"type": "draw", "parts": [INSIDE, GILL], "drive": "gape", "shape": "on", "c": -1.0, "plus": 1.0,
				"at": THROAT_Q, "way": Vector3.ZERO},
			{"type": "scale", "parts": [GILL], "drive": "gape", "c": 1.0, "way": Vector3.RIGHT, "k2": 0.12},
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": EYE_MID, "k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0},
			{"type": "move", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "w": 1, "flags": ["mirror"], "way": EYE_OUT},
			{"type": "scale", "parts": [EYE], "drive": "blink", "c": 1.0, "flags": ["mirror"],
				"at": EYE_MID, "way": Vector3.UP, "k2": -0.85},
			{"type": "turn", "parts": [7, 8], "drive": "gape", "c": -GAPE_OPEN, "at": hinge, "way": Vector3.RIGHT},
			{"type": "turn", "parts": [0, EYE, RING, INSIDE], "drive": "gape", "c": SNOUT_LIFT, "w": 2, "at": hinge, "way": Vector3.RIGHT},
		],
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, _old: Callable) -> Dictionary:
	var part := int(round(uv2.y))
	var snout := 1.0 - smoothstep(JAW_TO * 0.4, JAW_TO * 1.1, p.z + HALF)
	if part == 0 and uv2.x > 0.99 and absf(uv.x - JAW_TO / LENGTH) < 0.0001:
		return {"part": RING, "w": [0.0, snout]}
	if part == 0 and uv2.x > 0.99 and uv.x > JAW_TO / LENGTH + 0.0001:
		return {"part": INSIDE, "w": [0.0, snout]}
	if part == EYE:
		var mid := Vector3(EYE_MID.x * (1.0 if p.x >= 0.0 else -1.0), EYE_MID.y, EYE_MID.z)
		var dy := p.y - mid.y
		var dz := p.z - mid.z
		var g := EYE_GROW
		return {"part": EYE, "w": [(g * g - g) * (EYE_SAG.x * dy * dy + EYE_SAG.y * dz * dz), snout]}
	return {"part": part, "w": [0.0, snout]}
