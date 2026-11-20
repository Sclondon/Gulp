extends RefCounted
## The sea myth shader's motion in the jointed family (scripts/motion.gd; GameCommon
## `godot/motion-families`), as sea_myth.gdshader moved those who wear it (the mermaid, the hippocampus and
## kelpie, the deep spawn: they differ by the shape settings each sends, read from the material): every
## move of the old shader was a push from the point's place at rest, so each is a move here: the wave
## along the tail (side to side or up and down, `wave_axis`) with the head's recoil, the arms swinging from
## the shoulder and bending at the elbow (each side `limb_off` after the other), hair and strands drifting,
## tentacles writhing and spreading as the mouth opens, fins rippling, the jaw, the arch and the curl, and
## the kelpie's mane shown only on the kelpie. Numbers from sea_myth.gdshader.
## Differs: the old shader tipped the normals with the wave, arch and curl (per-vertex light: the shine on
## a bent tail is a little different); a strand's place along it and its seed are taken from the model,
## the wave's place along the body likewise (as before).

const FAMILY := "jointed"

const JAW := 1
const LIMB := 2
const STRAND := 3
const TENTACLE := 4
const FIN_SIDE := 5
const FIN_UP := 6
const MANE := 8


static func _old_or(old: Callable, name: StringName, fallback: Variant) -> Variant:
	var v: Variant = old.call(name)
	return v if v != null else fallback


static func numbers(old: Callable) -> Dictionary:
	var jaw_hinge: Vector2 = _old_or(old, &"jaw_hinge", Vector2.ZERO)
	var shoulder: Vector3 = _old_or(old, &"shoulder", Vector3(0.2, 0.0, -0.5))
	var elbow: Vector3 = _old_or(old, &"elbow", Vector3(0.25, -0.1, -0.3))
	var limb_swing: float = _old_or(old, &"limb_swing", 0.3)
	var limb_bend: float = _old_or(old, &"limb_bend", 0.3)
	var limb_lag: float = _old_or(old, &"limb_lag", 0.2)
	var limb_off: float = _old_or(old, &"limb_off", 0.0)
	var limb_rest: float = _old_or(old, &"limb_rest", 0.0)
	var wave_amp: float = _old_or(old, &"wave_amp", 0.12)
	var wave_len: float = _old_or(old, &"wave_len", 1.1)
	var recoil: float = _old_or(old, &"recoil", 0.0)
	var axis: Vector3 = Vector3.RIGHT if float(_old_or(old, &"wave_axis", 0.0)) < 0.5 else Vector3.UP
	var x := Vector3.RIGHT
	var y := Vector3.UP
	var z := Vector3.BACK
	var strand := {"parts": [STRAND, MANE], "type": "move", "beat": "strand_beats", "w": 1, "per_lag": 1.0}
	var tent := {"parts": [TENTACLE], "type": "move", "beat": "strand_beats", "w": 1, "per_lag": 1.0}
	var fin := {"type": "move", "beat": "fin_beats", "w": 1, "lag": 2, "per_lag": 1.0}
	var ops: Array = [
		{"type": "turn", "parts": [JAW], "drive": "gape", "c": -float(_old_or(old, &"gape_max", 0.5)),
			"at": Vector3(0.0, jaw_hinge.x, jaw_hinge.y), "way": x},
		# arms: bent at the elbow (0.5 + 0.5 sin, a little behind the stroke), swung from the shoulder
		{"type": "turn", "parts": [LIMB], "drive": "sway", "c": -0.5 * limb_bend, "a": -0.5 * limb_bend, "beat": "limb_beats",
			"off": -TAU * limb_lag, "side_off": TAU * limb_off, "w": 1, "at": Vector3(0.0, elbow.y, elbow.z), "way": x},
		{"type": "turn", "parts": [LIMB], "drive": "sway", "a": -limb_swing, "plus": -limb_rest, "beat": "limb_beats",
			"side_off": TAU * limb_off, "at": Vector3(0.0, shoulder.y, shoulder.z), "way": x},
		# strands: (sin ph, 0.6 cos(ph + 3 seed), 0.25 sin(ph / 2)) * reach (0.6 + 0.6 sway)
		strand.merged({"a": 1.0, "lag": 2, "way": x}, true),
		strand.merged({"drive": "sway", "a": 1.0, "lag": 2, "way": x}, true),
		strand.merged({"a": 0.6, "off": 0.5 * PI, "lag": 3, "way": y}, true),
		strand.merged({"drive": "sway", "a": 0.6, "off": 0.5 * PI, "lag": 3, "way": y}, true),
		strand.merged({"a": 0.25, "beats": 0.5, "lag": 2, "per_lag": 0.5, "way": z}, true),
		strand.merged({"drive": "sway", "a": 0.25, "beats": 0.5, "lag": 2, "per_lag": 0.5, "way": z}, true),
		# tentacles: (sin ph, cos(0.8 ph + 5 seed)) * reach, twice the strands' beat; spread as it gapes
		tent.merged({"a": 1.0, "beats": 2.0, "lag": 2, "way": x}, true),
		tent.merged({"a": 1.0, "beats": 1.6, "off": 0.5 * PI, "lag": 3, "way": y}, true),
		{"type": "move", "parts": [TENTACLE], "drive": "gape", "c": float(_old_or(old, &"tent_spread", 0.1)), "flags": ["own_way"]},
		# fins: reach (0.5 + 0.5 sway)
		fin.merged({"parts": [FIN_SIDE], "a": 1.0, "way": x}, true),
		fin.merged({"parts": [FIN_SIDE], "drive": "sway", "a": 1.0, "way": x}, true),
		fin.merged({"parts": [FIN_UP], "a": 1.0, "way": y}, true),
		fin.merged({"parts": [FIN_UP], "drive": "sway", "a": 1.0, "way": y}, true),
		# the body's wave and the head's recoil
		{"type": "move", "drive": "sway", "a": wave_amp, "beat": "tail_beats", "w": 4, "per_s": -TAU / wave_len, "way": axis},
		{"type": "move", "drive": "sway", "a": -recoil, "beat": "tail_beats", "w": 5, "way": axis},
		{"type": "move", "drive": "arch", "c": 1.0, "w": 6, "way": y},
		{"type": "move", "drive": "curl", "c": 1.0, "w": 7, "way": x},
		# the mane: shrunk to nothing but on the kelpie
		{"type": "scale", "parts": [MANE], "drive": "kelpie", "shape": "on", "c": 1.0, "plus": -1.0, "at": Vector3.ZERO,
			"k1": 1.0, "k2": 1.0, "flags": ["after"]},
	]
	return {
		"motion_length": float(_old_or(old, &"body_len", 2.0)), "motion_nose": float(_old_or(old, &"nose_z", -1.0)),
		"ops": ops,
	}


static func label(p: Vector3, _n: Vector3, uv: Vector2, uv2: Vector2, _colour: Color, old: Callable) -> Dictionary:
	var part := int(uv2.y + 0.5)
	var w := uv2.x
	var seed := uv.y
	var nose_z: float = _old_or(old, &"nose_z", -1.0)
	var body_len: float = _old_or(old, &"body_len", 2.0)
	var wave_from: float = _old_or(old, &"wave_from", 0.3)
	var curl_from: float = _old_or(old, &"curl_from", 0.25)
	var s := clampf((p.z - nose_z) / body_len, 0.0, 1.0)
	var w1 := 0.0
	var lag_a := 0.0
	var lag_b := 0.0
	var way := Vector3.ZERO
	if part == LIMB:
		var elbow_w: float = _old_or(old, &"elbow_w", 0.5)
		w1 = smoothstep(elbow_w - 0.08, elbow_w + 0.08, w)
	elif part == STRAND or part == MANE:
		w1 = float(_old_or(old, &"strand_amp", 0.06)) * pow(w, 1.5) * 0.6
		lag_a = TAU * seed - w * 4.0
		lag_b = lag_a + seed * 3.0
	elif part == TENTACLE:
		w1 = float(_old_or(old, &"tent_amp", 0.05)) * pow(w, 1.2)
		lag_a = TAU * seed - w * 6.0
		lag_b = 0.8 * lag_a + seed * 5.0
		var mouth: Vector2 = _old_or(old, &"mouth_xy", Vector2.ZERO)
		var away := Vector2(p.x, p.y) - mouth
		var dir := away / away.length() if away.length() > 0.0001 else Vector2(0.0, 1.0)
		way = Vector3(dir.x * w, dir.y * w, 0.6 * w)
	elif part == FIN_SIDE or part == FIN_UP:
		w1 = float(_old_or(old, &"fin_amp", 0.02)) * w * 0.5
		lag_a = -uv.x * 2.5 - p.z * 4.0
	var grow := pow(smoothstep(wave_from, 1.0, s), 1.4)
	var head := 1.0 - smoothstep(0.0, wave_from + 0.1, s)
	var zr := p.z - (nose_z + 0.5 * body_len)
	var back := (1.0 - curl_from) * body_len
	var t := maxf(p.z - (nose_z + curl_from * body_len), 0.0)
	return {"part": part, "w": [w1, lag_a, lag_b, grow, head, zr * zr / body_len, t * t / (2.0 * back)], "way": way}
