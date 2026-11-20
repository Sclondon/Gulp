extends RefCounted
## The California halibut's motion in the swim family (scripts/motion.gd; GameCommon
## `godot/motion-families`), as california_halibut.gdshader moved it: a flatfish, so its wave runs up and
## down along its flat body (done here by moves, each point lifted and tipped by its place along the body,
## since the wave dies away as it settles: (1 - settle)), the quicker ripple along its fringe fins, its
## mouth swinging sideways open, lying down on the sand (`settle`: the rear and the fins laid flat), the
## turning curl, both cartoon eyes (on its upper side) grown. Numbers from california_halibut.gdshader.
## (The old shader also tipped the fringe's normals with the ripple; per-vertex light, so left out.)

const FAMILY := "swim"

const LENGTH := 1.0
const HALF := 0.5
const SEAM := -0.0145
const UNDER := -0.0355
const HINGE := 0.125
const MOUTH_K := 0.42
const EYE_AT := Vector3(-0.004, 0.01903, -0.412)
const EYE_OUT := Vector3(-0.03032, 0.97704, -0.21089)
const EYE2_AT := Vector3(0.036, 0.01439, -0.402)
const EYE2_OUT := Vector3(0.35365, 0.90199, -0.24768)
const EYE_RADIUS := 0.0125
const EYE_GROW := 1.45
const EYE_SINK := 0.3

# Parts: the model's (UV2.y) and ours.
const JAW := 1
const FRINGE := 2
const FRINGE_B := 3
const FIN := 4
const EYE_PART := 5
const EYE := 20
const EYE2 := 21


static func numbers(old: Callable) -> Dictionary:
	var got: Variant = old.call(&"wave")
	var wave: float = got if got != null else 1.05
	var hinge := Vector3(-MOUTH_K * HINGE, 0.0, HINGE - HALF)
	var not_jaw: Array = []
	for i in 24:
		if i != JAW:
			not_jaw.append(i)
	var ops: Array = []
	for e in [[EYE, EYE_AT, EYE_OUT], [EYE2, EYE2_AT, EYE2_OUT]]:
		var o: Vector3 = (e[2] as Vector3).normalized()
		ops.append({"type": "scale", "parts": [e[0]], "drive": "cartoon_eyes", "c": 1.0, "at": e[1], "way": o,
			"k1": EYE_GROW - 1.0, "k2": EYE_GROW - 1.0})
		ops.append({"type": "move", "parts": [e[0]], "drive": "cartoon_eyes", "c": -EYE_RADIUS * EYE_SINK * (EYE_GROW - 1.0), "way": o})
	ops.append_array([
		{"type": "turn", "parts": [JAW], "drive": "gape", "c": 0.62, "w": 1, "at": hinge, "way": Vector3.UP},
		{"type": "turn", "parts": not_jaw, "drive": "gape", "c": -0.1, "w": 1, "at": hinge, "way": Vector3.UP},
		{"type": "move", "drive": "settle", "c": -0.012, "w": 2, "way": Vector3.UP},
		{"type": "move", "drive": "settle", "c": -1.0, "w": 3, "way": Vector3.UP},
		# the fringe's ripple, twice a beat, (1 - settle) of it
		{"type": "move", "parts": [FRINGE, FRINGE_B], "drive": "sway", "a": 1.0, "beats": 2.0, "per_s": -TAU * LENGTH / 0.2,
			"w": 4, "way": Vector3.UP},
		{"type": "move", "parts": [FRINGE, FRINGE_B], "drive": "sway", "drive2": "settle", "a": -1.0, "beats": 2.0,
			"per_s": -TAU * LENGTH / 0.2, "w": 4, "way": Vector3.UP},
		# the body's wave: each point tipped about its place on the middle line, then lifted
		{"type": "turn", "drive": "sway", "a": -1.0, "w": 5, "lag": 7, "per_lag": 1.0, "per_s": -TAU / wave,
			"flags": ["own_point"], "way": Vector3.RIGHT},
		{"type": "turn", "drive": "sway", "drive2": "settle", "a": 1.0, "w": 5, "lag": 7, "per_lag": 1.0, "per_s": -TAU / wave,
			"flags": ["own_point"], "way": Vector3.RIGHT},
		{"type": "move", "drive": "sway", "a": 1.0, "w": 6, "per_s": -TAU / wave, "way": Vector3.UP},
		{"type": "move", "drive": "sway", "drive2": "settle", "a": -1.0, "w": 6, "per_s": -TAU / wave, "way": Vector3.UP},
	])
	return {
		"motion_length": LENGTH, "motion_nose": -HALF,
		"env_poly": Vector4.ZERO, "env_pow": Vector3(0.0, 0.0, 2.0),
		"swim_from": -10.0, "swim_joint": 10.0, "swim_wrist": 0.0,
		"swim_curl_from": -0.25 * LENGTH, "swim_curl_span": 0.75 * LENGTH,
		"ops": ops,
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, old: Callable) -> Dictionary:
	var part := int(uv2.y + 0.5)
	var xm := p.z + HALF
	var got: Variant = old.call(&"wave")
	var wave: float = got if got != null else 1.05
	if part == EYE_PART:
		part = EYE2 if p.x > 0.016 else EYE
	var jaw := smoothstep(HINGE, HINGE - 0.05, xm) if part == JAW else smoothstep(HINGE + 0.02, 0.0, xm)
	var rear := smoothstep(0.55, 0.88, xm)
	var fringe := part == FRINGE or part == FRINGE_B
	var flat_fin := fringe or (part == FIN and p.y < SEAM + 0.005)
	var laid := uv.x * (SEAM - UNDER - 0.003 - 0.012 * rear) if flat_fin else 0.0
	var ripple := 0.013 * uv.x if fringe else 0.0
	# the wave: lift = reach(s) sin(phi), its slope A sin(phi) + B cos(phi) = R sin(phi + d)
	var s := xm / LENGTH
	var reach := LENGTH * (0.005 + 0.05 * s * s)
	var a := 0.1 * s
	var b := -(TAU / wave) * (0.005 + 0.05 * s * s)
	return {"part": part, "w": [jaw, rear, laid, ripple, sqrt(a * a + b * b), reach, atan2(b, a)],
		"point": Vector3(0.0, 0.0, p.z)}
