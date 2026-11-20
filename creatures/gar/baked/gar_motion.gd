extends RefCounted
## The gar's motion in the swim family (scripts/motion.gd; GameCommon `godot/motion-families`), as
## gar.gdshader moved it: the wave back along the body to the tail plate, the turning curl, the
## lower jaw (and the lining below the hinge) swinging down and the snout lifting, the gill arches
## spreading as it opens, the dorsal fin folding down (`dorsal` 0), the pectoral fins rowing (held back as
## `scull` falls), the soft fins rippling, the cartoon eye grown, sunk at its rim and blinking; the head and beak
## snapping sideways as it strikes (`snap`). Numbers
## from gar.gdshader (its sums are in body lengths; here in metres). Differs: the blink's squash is
## the cartoon eye's (0.3 of it) whatever `cartoon_eyes` is; the pectorals' normals turn with the flap too; the snap's
## arc is each point turned about the middle of the bent stretch behind it (the same where the head is
## straight, close along the arc).

const FAMILY := "swim"

const LENGTH := 1.3
const JOINT := 0.885
const SWING := 0.05
const HINGE_S := 0.215
const HINGE_Y := -0.007
const GAPE_ANGLE := 0.5
const LIFT := 0.04
const LIFT_TO := 0.21
const LIFT_Y := 0.012
const PEC_ROOT := Vector3(0.0206, -0.03, 0.31)
const PEC_SWING := 0.22
const PEC_FLAP := 0.12
const PEC_ALT := 1.0
const PEC_HOLD := -0.3
const FIN_WAVE := 0.008
const SPINE_SHARE := 0.0
const GILL_GAP := 0.0136
const CURL_FROM := -0.15
const CURL_SPAN := 0.6
const EYE_SKIN := Vector3(0.0156, 0.011, 0.218)
const EYE_OUT := Vector3(0.8588, 0.4386, -0.2646)
const EYE_SINK := 0.00075
const EYE_R := 0.0075
const EYE_GROW := 1.8
const SNAP_FROM := -0.15
const SNAP_SPAN := 0.22
const SNAP_ANGLE := 0.7
const CORNER_B := 0.012
const CORNER_C := 0.035

# Parts (the model's UV2.y): 0 body, 1 lower jaw, 2 dorsal fin, 3, 4 and 8 the other soft fins,
# 5 pectorals, 7 eyes, 9 the mouth's lining, 10 gill arches.
const EYE := 7


static func numbers(_old: Callable) -> Dictionary:
	var L := LENGTH
	var centre := Vector3(EYE_SKIN.x, EYE_SKIN.y, EYE_SKIN.z - 0.5) * L
	var o := EYE_OUT.normalized()
	var up := (Vector3.UP - o * o.y).normalized()
	var root := Vector3(PEC_ROOT.x, PEC_ROOT.y, PEC_ROOT.z - 0.5) * L
	var pec := {"parts": [5], "type": "turn", "drive": "scull", "lag": 3, "per_lag": -1.3, "side_off": PEC_ALT * PI,
		"flags": ["mirror"], "at": root}
	return {
		"motion_length": L, "motion_nose": -0.5 * L,
		"env_poly": Vector4(SWING * 0.15, -SWING * 0.25 / JOINT, SWING * 1.1 / (JOINT * JOINT), 0.0),
		"swim_from": -10.0, "swim_joint": JOINT, "swim_wrist": 0.25, "swim_wrist_from": 0.86 * JOINT,
		"swim_curl_from": CURL_FROM * L, "swim_curl_span": CURL_SPAN * L,
		"ops": [
			{"type": "move", "parts": [10], "drive": "gape", "c": 0.14 * GILL_GAP * L, "w": 1, "way": Vector3.BACK},
			{"type": "turn", "parts": [1], "drive": "gape", "c": -GAPE_ANGLE, "w": 1,
				"at": Vector3(0.0, HINGE_Y, HINGE_S - 0.5) * L, "way": Vector3.RIGHT},
			{"type": "turn", "parts": [0], "drive": "gape", "c": LIFT, "w": 1,
				"at": Vector3(0.0, LIFT_Y, LIFT_TO - 0.5) * L, "way": Vector3.RIGHT},
			{"type": "move", "parts": [2], "drive": "dorsal", "c": -1.0, "plus": 1.0, "w": 1, "way": Vector3(0.0, -0.9, 0.5) * L},
			pec.merged({"way": Vector3.UP, "c": -PEC_HOLD, "a": PEC_SWING, "plus": PEC_HOLD}, true),
			pec.merged({"way": Vector3.BACK, "a": PEC_FLAP, "off": 0.5 * PI}, true),
			{"type": "scale", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "flags": ["mirror"],
				"at": centre, "k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0},
			{"type": "move", "parts": [EYE], "drive": "cartoon_eyes", "c": 1.0, "w": 1, "flags": ["mirror"], "way": o},
			{"type": "scale", "parts": [EYE], "drive": "blink", "c": 1.0, "flags": ["mirror"], "at": centre, "way": up, "k2": -0.3},
			{"type": "move", "parts": [2, 3, 4, 8], "a": 0.3 * FIN_WAVE * L, "off": -1.0, "w": 2, "lag": 3, "per_lag": -5.0, "way": Vector3.RIGHT},
			{"type": "move", "parts": [2, 3, 4, 8], "drive": "sway", "a": 0.7 * FIN_WAVE * L, "off": -1.0, "w": 2, "lag": 3, "per_lag": -5.0,
				"way": Vector3.RIGHT},
			# the head's sideways snap as it strikes (after the swimming): each point ahead of SNAP_FROM turned about
			# the middle of the bent stretch behind it, as far as the arc has turned there
			{"type": "turn", "drive": "snap", "c": -SNAP_ANGLE, "w": 6, "flags": ["own_point", "after"], "way": Vector3.UP},
		],
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, _old: Callable) -> Dictionary:
	var out := _label(p, uv, uv2)
	# (the snap: how far ahead of SNAP_FROM, the bent stretch's share, the middle of the bent stretch behind)
	var d := SNAP_FROM - p.z / LENGTH
	if d > 0.0:
		var bent := minf(d, SNAP_SPAN)
		var w: Array = out.get("w", [])
		w.resize(6)
		for i in 6:
			if w[i] == null:
				w[i] = 0.0
		w[5] = bent / SNAP_SPAN
		out["w"] = w
		out["point"] = Vector3(0.0, 0.0, (SNAP_FROM - 0.5 * bent) * LENGTH)
	return out


static func _label(p: Vector3, uv: Vector2, uv2: Vector2) -> Dictionary:
	var part := int(uv2.y + 0.5)
	var s := p.z / LENGTH + 0.5
	if part == 1 or (part == 9 and uv2.x > 0.5):
		return {"part": 1, "w": [1.0 - smoothstep(HINGE_S - CORNER_B, HINGE_S + CORNER_C, s)]}
	if part == 0 or part == 9:
		return {"part": 0, "w": [1.0 - smoothstep(0.0, LIFT_TO, s) if s < LIFT_TO else 0.0]}
	if part == 10:
		return {"part": 10, "w": [floorf(uv.y) - 1.5]}
	if part in [2, 3, 4, 8]:
		var soft := smoothstep(SPINE_SHARE - 0.1, SPINE_SHARE + 0.1, uv.y) if part == 2 else 1.0
		return {"part": part, "w": [uv2.x if part == 2 else 0.0, soft * uv.x * uv.x, uv.y]}
	if part == 5:
		return {"part": 5, "w": [0.0, 0.0, uv.x]}
	if part == EYE:
		var sg := 1.0 if p.x >= 0.0 else -1.0
		var centre := Vector3(sg * EYE_SKIN.x, EYE_SKIN.y, EYE_SKIN.z - 0.5)
		var o := Vector3(sg * EYE_OUT.x, EYE_OUT.y, EYE_OUT.z).normalized()
		var d := p / LENGTH - centre
		var dt := d - o * d.dot(o)
		var r2 := dt.dot(dt) / (EYE_R * EYE_R)
		var g := EYE_GROW
		# (the rim sinks by (g*g - g) * EYE_SINK * r2 at full growth; the op's amount is cartoon_eyes)
		return {"part": EYE, "w": [-(g * g - g) * EYE_SINK * r2 * LENGTH]}
	return {"part": part}
