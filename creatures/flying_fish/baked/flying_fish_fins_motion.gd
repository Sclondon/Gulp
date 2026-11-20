extends RefCounted
## The flying fish's see-through fins (flying_fish_fins.gdshader) in the swim family, drawn clear
## (swim_sheer): they move as the body does (flying_fish_motion.gd, whose moves and labels this takes).

const FAMILY := "swim_sheer"
const BODY := preload("res://creatures/flying_fish/baked/flying_fish_motion.gd")


static func numbers(_old: Callable) -> Dictionary:
	return {
		"motion_length": BODY.LENGTH, "motion_nose": -0.5 * BODY.LENGTH, "wave": BODY.WAVE,
		"env_poly": Vector4.ZERO, "env_pow": Vector3(0.0, 0.0, 2.0),
		"swim_curl_from": -0.2 * BODY.LENGTH, "swim_curl_span": 0.7 * BODY.LENGTH,
		"ops": BODY.moves(false),
	}


static func label(p: Vector3, n: Vector3, uv: Vector2, uv2: Vector2, colour: Color, old: Callable) -> Dictionary:
	return BODY.label(p, n, uv, uv2, colour, old)
