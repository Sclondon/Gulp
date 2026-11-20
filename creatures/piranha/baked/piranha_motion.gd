extends RefCounted
## The piranha's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## piranha.gdshader moved it: the wave back along the body to the tail plate behind its wrist, the
## turning curl, the lower jaw (and the teeth on it) swinging down, the throat's ring drawn to the back
## of the mouth as it opens and the inside of the mouth folded away while it is shut, the gill arches
## widening, the cartoon eye grown (with its sag outward) and blinking. Numbers from piranha.gdshader.
## (The ring's draw is all or nothing here: the old one eased it in over the first third of the gape.)

const FAMILY := "swim"

const LENGTH := 0.30
const HALF := 0.15
const JOINT := 0.242
const JAW_TO := 0.030
const HINGE_Y := -0.0156
const GAPE_OPEN := 0.72
const THROAT_Q := Vector3(0.0, -0.02560, -0.09521)
const EYE_MID := Vector3(0.01712, 0.02050, -0.10800)
const EYE_OUT := Vector3(0.9562, 0.2059, -0.2082)
const EYE_SAG := Vector2(-6.022, -5.360)
const EYE_GROW := 1.45

# Parts: the model's (UV2.y: 6 eye, 7 lower jaw, 9 its teeth, 11 gill arches) and ours.
const EYE := 6
const JAW := 7
const TEETH := 9
const GILL := 11
const RING := 12
const INSIDE := 13


static func numbers(_old: Callable) -> Dictionary:
	var k := LENGTH / JOINT
	return {
		"motion_length": LENGTH, "motion_nose": -HALF,
		"env_poly": Vector4(0.006, -0.022 * k, 0.0, 0.072 * k * k * k),
		"swim_from": -10.0, "swim_joint": JOINT / LENGTH, "swim_wrist": 0.25, "swim_wrist_from": 0.86 * JOINT / LENGTH,
		"swim_curl_from": -0.2 * LENGTH, "swim_curl_span": 0.7 * LENGTH,
		"ops": [
			{"type": "draw", "parts": [RING], "drive": "gape", "shape": "on", "c": 1.0, "at": THROAT_Q, "way": Vector3.ZERO},
			# (shut: 1 - on(gape))
			{"type": "draw", "parts": [INSIDE, GILL], "drive": "gape", "shape": "on", "c": -1.0, "plus": 1.0,
				"at": THROAT_Q, "way": Vector3.ZERO},
			{"type": "scale", "parts": [GILL], "drive": "gape", "c": 1.0, "way": Vector3.RIGHT, "k2": 0.12},
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": EYE_MID, "k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0},
			{"type": "move", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "w": 1, "flags": ["mirror"], "way": EYE_OUT},
			{"type": "scale", "parts": [EYE], "drive": "blink", "c": 1.0, "flags": ["mirror"],
				"at": EYE_MID, "way": Vector3.UP, "k2": -0.85},
			{"type": "turn", "parts": [JAW, TEETH], "drive": "gape", "c": -GAPE_OPEN,
				"at": Vector3(0.0, HINGE_Y, JAW_TO - HALF), "way": Vector3.RIGHT},
		],
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, _old: Callable) -> Dictionary:
	var part := int(round(uv2.y))
	if part == 0 and uv2.x > 0.99 and absf(uv.x - JAW_TO / LENGTH) < 0.0001:
		return {"part": RING}
	if part == 0 and uv2.x > 0.99 and uv.x > JAW_TO / LENGTH + 0.0001:
		return {"part": INSIDE}
	if part == EYE:
		# (its sag outward as it grows: (s*s - s) at full growth, times the old sum)
		var mid := Vector3(EYE_MID.x * (1.0 if p.x >= 0.0 else -1.0), EYE_MID.y, EYE_MID.z)
		var dy := p.y - mid.y
		var dz := p.z - mid.z
		var g := EYE_GROW
		return {"part": EYE, "w": [(g * g - g) * (EYE_SAG.x * dy * dy + EYE_SAG.y * dz * dz)]}
	return {"part": part}
