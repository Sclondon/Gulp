class_name Motion
## Motion families (GameCommon `godot/motion-families`). The user, 2026-11-19: "each animal should not
## need its own shader for swimming or motion"; they chose a few shared motion families, each animal
## setting its own numbers as uniforms. So a creature drawn from its baked paint (BakedLook) wears one
## of a handful of shaders (res://shaders/motion/: swim, swim_sheer, flap, jointed, radial) in place of
## a copy of its own, and a browser compiles five programs for every animal in the sea, not one each.
##
## An animal's motion is its SPEC, a small script beside its baked look,
## `baked/<its shader's name>_motion.gd`, with:
##   const FAMILY := "swim"                      (a key of FAMILIES)
##   static func numbers(old: Callable) -> Dictionary
##       the family's uniforms for it (`ops`: its moves, see `pack`), worked out from its own shader's
##       settings: old.call(&"name") is the value its material has (set by its script), or its own
##       shader's default
##   static func label(p, n, uv, uv2, colour, old) -> Dictionary  (tools/motion_labels.gd only)
##       what one point of its model is: {part: 0..23, w: [up to 7 weights], point: Vector3, way: Vector3}
## tools/motion_labels.gd writes the labels into the baked meshes (CUSTOM0.zw, CUSTOM1..3).
##
## Its script goes on setting phase, sway, gape and the rest on its material each frame, by the same
## names: the family shaders declare them (INPUTS, the same list as motion.gdshaderinc's).

const FAMILIES := {
	"swim": "res://shaders/motion/swim.gdshader",
	"swim_sheer": "res://shaders/motion/swim_sheer.gdshader",
	"flap": "res://shaders/motion/flap.gdshader",
	"jointed": "res://shaders/motion/jointed.gdshader",
	"radial": "res://shaders/motion/radial.gdshader",
}

## The live settings an op may be driven by, in the order of motion.gdshaderinc's `inputs` (index 0 is
## 1.0, "").
const INPUTS: Array[StringName] = [&"", &"sway", &"gape", &"cartoon_eyes", &"blink", &"curl", &"arch", &"tail_beats", &"scull", &"sculls",
	&"swim", &"dorsal", &"strokes", &"row", &"breaths", &"gills", &"walk", &"gape_breath", &"gill_flare", &"first_dorsal",
	&"ripples", &"open", &"withdraw", &"spread", &"strike", &"scoops", &"wings", &"snap", &"buzzes", &"paddle",
	&"flick", &"feel", &"flap", &"grasp", &"billows", &"flow", &"flare", &"settle", &"dig", &"waggle",
	&"fans", &"twitches", &"fan", &"twitch", &"furl", &"fin_ripples", &"flaps", &"breathe", &"sit", &"billow",
	&"ripple", &"swing", &"jaw", &"tusk", &"pearl", &"puff", &"riding", &"stand", &"claws", &"sail",
	&"bobs", &"bob", &"grip", &"fold", &"crest", &"afloat", &"flex", &"tuck", &"enroll", &"curl_up",
	&"retract", &"fin_waves", &"fin_lift", &"arm_sway", &"wade", &"lean", &"sink", &"fin_tall", &"tusks", &"humps",
	&"rear", &"coil", &"sway_speed", &"limb_beats", &"strand_beats", &"fin_beats", &"kelpie", &"flaps_open", &"aux0", &"aux1",
	&"aux2", &"aux3", &"phase"]

const MAX_OPS := 24
const TYPES := {"turn": 1, "move": 2, "scale": 3, "draw": 4, "bend": 5, "leg": 6}
const SHAPES := {"sine": 0, "upper": 1, "stride": 2, "lift": 3, "on": 4}
## An op's flags (see motion.gdshaderinc).
const FLAGS := {"mirror": 1, "by_side": 2, "own_point": 4, "own_way": 8, "normal_way": 16, "bend_up": 32, "after": 64, "way_point": 128, "abs": 256, "ends": 512}

static var _specs := {}
static var _families := {}


## The spec of an animal's shader (its path), or null.
static func spec_of(shader_path: String) -> GDScript:
	if _specs.has(shader_path):
		return _specs[shader_path]
	var path := shader_path.get_base_dir().path_join("baked").path_join(shader_path.get_file().get_basename() + "_motion.gd")
	var spec: GDScript = load(path) if ResourceLoader.exists(path) else null
	_specs[shader_path] = spec
	return spec


static func family_shader(spec: GDScript) -> Shader:
	var name: String = spec.get_script_constant_map().get("FAMILY", "swim")
	if not _families.has(name):
		_families[name] = load(FAMILIES[name])
	return _families[name]


## Every family shader (for the loading screen).
static func every_family() -> Array[String]:
	var out: Array[String] = []
	for k: String in FAMILIES:
		out.append(FAMILIES[k])
	return out


## Puts `material` (wearing the animal's own shader, `own`) onto its family's shader with its numbers.
## Every live setting it has not been given yet keeps its own shader's default.
static func wear(material: ShaderMaterial, own: Shader, spec: GDScript) -> void:
	var defaults := defaults_of(own)
	var old := func(name: StringName) -> Variant:
		var v: Variant = material.get_shader_parameter(name)
		return v if v != null else defaults.get(name)
	var numbers: Dictionary = spec.call(&"numbers", old)
	var family := family_shader(spec)
	material.shader = family
	# (every setting the family shares with its own shader, by name and type, that its script has not
	# set: its own default, e.g. its `wave`, `tail_beats`)
	for u: Dictionary in family.get_shader_uniform_list():
		var name := StringName(u.name)
		if material.get_shader_parameter(name) == null and defaults.get(name) != null and typeof(defaults[name]) == u.type:
			material.set_shader_parameter(name, defaults[name])
	for k: String in numbers:
		if k == "ops":
			continue
		# (a setting named where the family wants its number in INPUTS: swim_drive, swim_still)
		if numbers[k] is String or numbers[k] is StringName:
			material.set_shader_parameter(k, _input(numbers[k]))
			continue
		material.set_shader_parameter(k, numbers[k])
	var packed := pack(numbers.get("ops", []))
	for k: String in packed:
		material.set_shader_parameter(k, packed[k])


## A shader's uniforms' defaults by name. The engine's own (RenderingServer) where it gives them;
## read from the code where it does not (a headless run gives none: every one would be null).
static func defaults_of(shader: Shader) -> Dictionary:
	if _defaults.has(shader):
		return _defaults[shader]
	var out := {}
	for u: Dictionary in shader.get_shader_uniform_list():
		out[StringName(u.name)] = RenderingServer.shader_get_parameter_default(shader.get_rid(), u.name)
	var re := RegEx.create_from_string("(?m)^uniform\\s+(float|int|bool|vec2|vec3|vec4)\\s+(\\w+)[^=;]*=\\s*([^;]+);")
	for m in re.search_all(shader.code):
		var name := StringName(m.get_string(2))
		if out.get(name) != null:
			continue
		var text := m.get_string(3).strip_edges()
		match m.get_string(1):
			"float":
				out[name] = text.to_float()
			"int":
				out[name] = text.to_int()
			"bool":
				out[name] = text == "true"
			_:
				# (vec3(1.0) in a shader is that number in every place)
				var inner := text.get_slice("(", 1).trim_suffix(")")
				if not inner.contains(","):
					var x := inner.to_float()
					out[name] = {"vec2": Vector2(x, x), "vec3": Vector3(x, x, x), "vec4": Vector4(x, x, x, x)}[m.get_string(1)]
					continue
				var e := Expression.new()
				if e.parse(text.replace("vec2", "Vector2").replace("vec3", "Vector3").replace("vec4", "Vector4")) == OK:
					var v: Variant = e.execute()
					if not e.has_execute_failed():
						out[name] = v
	_defaults[shader] = out
	return out


static var _defaults := {}


## The moves as the family shaders take them. Each op is a Dictionary:
##   type   "turn" (about `at`, axis `way`, radians), "move" (along `way`, metres), "scale" (about `at`:
##          1 + amount * k1 across `way`, 1 + amount * k2 along it), "draw" (towards `at` along `way`, 0..1),
##          "bend" (along `way` beyond k1 metres from `at`, amount radians over k2 metres),
##          "leg" (jointed only: a leg's stride; its own point the joint, its own way the knee, weight[w]
##          over 0.5 the lower leg; the foot moves along `way` by drive * k1 * stride and up by
##          k2 * min(|drive|, 1) * lift; knee_at the knee's share of the reach)
##   parts  the parts it moves (Array of ints 0..23; all if left out)
##   drive, drive2  names in INPUTS ("" or left out: 1.0) the amount is multiplied by
##   c, a   amount = (drive * drive2 * (c + a * shape(angle)) + plus * drive3) * weight[w] * weight[w2]
##   plus, drive3  a second, steady part of the amount (drive3 "" is 1.0)
##   shape  "sine" (default), "upper", "stride", "lift", "on" (c while drive > 0); ground (0.6) for strides
##   beats, beat  angle = TAU * phase * beats * input[beat] + off + side_off (on the -x side)
##          + per_s * s + per_lag * weight[lag]
##   w, w2, lag  weight slots 0..7 (0 is 1.0; 1..7 the label's w[0..6])
##   at, way, k1, k2  as above (way defaults to +x)
##   flags  Array of names in FLAGS ("way_point": the point is the vertex's own way, a second point)
static func pack(ops: Array) -> Dictionary:
	var a := PackedVector4Array()
	var b := PackedVector4Array()
	var c := PackedVector4Array()
	var d := PackedVector4Array()
	var e := PackedVector4Array()
	var f := PackedVector4Array()
	for arr: PackedVector4Array in [a, b, c, d, e, f]:
		arr.resize(MAX_OPS)
	if ops.size() > MAX_OPS:
		push_error("Motion: %d moves, at most %d" % [ops.size(), MAX_OPS])
	for i in mini(ops.size(), MAX_OPS):
		var op: Dictionary = ops[i]
		var parts := 0xFFFFFF
		if op.has("parts"):
			parts = 0
			for p: int in op.parts:
				parts |= 1 << p
		var flags := 0
		for fl: String in op.get("flags", []):
			flags |= FLAGS[fl]
		var drive := _input(op.get("drive", ""))
		var drive2 := _input(op.get("drive2", ""))
		var drive3 := _input(op.get("drive3", ""))
		a[i] = Vector4(TYPES[op.get("type", "move")], parts, flags, drive + 128 * drive2 + 16384 * drive3)
		b[i] = Vector4(op.get("c", 0.0), op.get("a", 0.0), op.get("beats", 1.0), op.get("off", 0.0))
		c[i] = Vector4(op.get("side_off", 0.0), op.get("per_s", 0.0), op.get("per_lag", 0.0),
				int(op.get("w", 0)) + 8 * int(op.get("w2", 0)) + 64 * int(op.get("lag", 0)))
		var at: Vector3 = op.get("at", Vector3.ZERO)
		var way: Vector3 = op.get("way", Vector3.RIGHT)
		d[i] = Vector4(at.x, at.y, at.z, op.get("k1", 0.0))
		e[i] = Vector4(way.x, way.y, way.z, op.get("k2", 0.0))
		f[i] = Vector4(_input(op.get("beat", "")), SHAPES[op.get("shape", "sine")], op.get("ground", 0.6), op.get("knee_at", 0.6) if op.get("type", "") == "leg" else op.get("plus", 0.0))
	return {"op_count": mini(ops.size(), MAX_OPS), "op_a": a, "op_b": b, "op_c": c, "op_d": d, "op_e": e, "op_f": f}


static func _input(name: String) -> int:
	var i := INPUTS.find(StringName(name))
	if i < 0:
		push_error("Motion: no live setting %s in the family shaders (add it to INPUTS and motion.gdshaderinc)" % name)
		return 0
	return i
