extends SceneTree
## How long each shader program takes to compile the first time it is drawn (tools/PERF.md,
## "Shader programs"). A window (headless compiles nothing). Run it under ANGLE, as Chrome on
## Windows draws, with Godot's shader cache moved aside first (or the programs come from it):
##
##   godot --path . --audio-driver Dummy --rendering-driver opengl3_angle --resolution 320x240 \
##     -s res://tools/compile_cost.gd -- [--kinds=sardine,garibaldi,...] [--parts] [--synthetic]
##
## Each thing is put in front of a camera alone and one frame is drawn and timed
## (`RenderingServer.force_draw`); a second frame is timed too, so the compile's share is plain.
## `--synthetic` times plain shaders (the cost of any program at all). `--parts` also times each
## kind's shader with its fragment made plain, and with its vertex made plain, to show which half
## costs. `--shaders=res://a.gdshader,...` times shader files on a sphere (and lit per vertex). Prints `COST <name> <ms first frame> <ms second frame>`.

var _view_root: Node3D
var _camera: Camera3D
var _kinds: PackedStringArray = []
var _parts := false
var _synthetic := false
var _salt := 0
var _variants := false
var _files: PackedStringArray = []
var _env: Environment


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--kinds="):
			_kinds = arg.get_slice("=", 1).split(",")
		elif arg == "--parts":
			_parts = true
		elif arg.begins_with("--shaders="):
			_files = arg.get_slice("=", 1).split(",")
		elif arg == "--variants":
			_variants = true
		elif arg == "--synthetic":
			_synthetic = true
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	_view_root = Node3D.new()
	root.add_child(_view_root)
	_camera = Camera3D.new()
	_camera.position = Vector3(0.0, 0.0, 3.0)
	_view_root.add_child(_camera)
	var sun := DirectionalLight3D.new()
	sun.rotation = Vector3(-0.8, 0.4, 0.0)
	_view_root.add_child(sun)
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.fog_enabled = true
	env.environment.fog_density = 0.03
	_view_root.add_child(env)
	_env = env.environment
	_run.call_deferred()


func _draw_ms() -> float:
	var t := Time.get_ticks_usec()
	RenderingServer.force_draw(false, 0.0)
	return (Time.get_ticks_usec() - t) / 1000.0


func _time(label: String, mesh: Mesh, material: Material) -> void:
	var one := MeshInstance3D.new()
	one.mesh = mesh
	one.material_override = material
	var box := mesh.get_aabb()
	one.scale = Vector3.ONE * (1.5 / maxf(box.size.length(), 0.01))
	one.position = -box.get_center() * one.scale.x
	_view_root.add_child(one)
	var first := _draw_ms()
	var second := _draw_ms()
	print("COST %s %.0f %.1f" % [label, first, second])
	one.queue_free()
	await process_frame


func _shader(code: String) -> ShaderMaterial:
	var s := Shader.new()
	# (a constant of its own, so that no cache has the program already)
	s.code = code + "\nconst float SALT_%d = %d.0;\n" % [_salt, randi()]
	_salt += 1
	var m := ShaderMaterial.new()
	m.shader = s
	return m


func _run() -> void:
	for i in 3:
		_draw_ms()
	var sphere := SphereMesh.new()
	if _synthetic or _kinds.is_empty():
		await _time("plain_lit_a", sphere, _shader("shader_type spatial;\nvoid fragment() { ALBEDO = vec3(0.5, 0.4, 0.3); }"))
		await _time("plain_lit_b", sphere, _shader("shader_type spatial;\nvoid fragment() { ALBEDO = vec3(0.3, 0.4, 0.5); }"))
		await _time("plain_lit_cull_off", sphere, _shader("shader_type spatial;\nrender_mode cull_disabled;\nvoid fragment() { ALBEDO = vec3(0.3, 0.4, 0.6); }"))
		await _time("plain_unshaded", sphere, _shader("shader_type spatial;\nrender_mode unshaded;\nvoid fragment() { ALBEDO = vec3(0.3, 0.4, 0.5); }"))
		await _time("plain_textured", sphere, _shader("shader_type spatial;\nuniform sampler2D t : source_color;\nvoid fragment() { ALBEDO = texture(t, UV).rgb; ROUGHNESS = 0.5; SPECULAR = 0.4; }"))
		await _time("plain_alpha", sphere, _shader("shader_type spatial;\nrender_mode blend_mix, depth_draw_never;\nvoid fragment() { ALBEDO = vec3(0.3, 0.4, 0.5); ALPHA = 0.5; }"))
		var std := StandardMaterial3D.new()
		std.albedo_color = Color(0.2, 0.5, 0.3)
		await _time("standard", sphere, std)
	if _variants:
		await _time_variants()
	for kind in _kinds:
		await _time_kind(kind)
	for file in _files:
		var code := FileAccess.get_file_as_string(file)
		await _time(file.get_file(), sphere, _shader(code))
		if not code.contains("unshaded"):
			await _time(file.get_file() + ":vertex_lit", sphere, _shader(_with_mode(code, "vertex_lighting")))
	quit()


func _time_kind(kind: String) -> void:
	if not Species.has(kind):
		print("COST %s missing" % kind)
		return
	var look := Species.make(kind)
	if &"game" in look:
		look.set(&"game", true)
	var hidden := Node3D.new()
	hidden.visible = false
	root.add_child(hidden)
	hidden.add_child(look)
	await process_frame
	await process_frame
	var seen := {}
	for mi: MeshInstance3D in look.find_children("*", "MeshInstance3D", true, false):
		if not mi.visible and mi.get_parent() == look:
			continue
		var material: Material = mi.material_override
		if material == null:
			material = mi.get_active_material(0)
		if not (material is ShaderMaterial) or (material as ShaderMaterial).shader == null:
			continue
		var shader: Shader = (material as ShaderMaterial).shader
		if seen.has(shader):
			continue
		seen[shader] = true
		var name := "%s/%s" % [kind, shader.resource_path.get_file()]
		await _time(name, mi.mesh, _shader(shader.code))
		if _parts:
			var code := shader.code
			var at := code.find("void fragment()")
			if at >= 0:
				var plain_frag := code.substr(0, at) + "void fragment() { ALBEDO = vec3(0.5); }\n"
				await _time(name + ":plain_fragment", mi.mesh, _shader(plain_frag))
				var tex_frag := code.substr(0, at) + "uniform sampler2D baked_ : source_color;\nvoid fragment() { ALBEDO = texture(baked_, UV).rgb; ROUGHNESS = 0.5; SPECULAR = 0.4; }\n"
				await _time(name + ":texture_fragment", mi.mesh, _shader(tex_frag))
			await _time(name + ":unshaded", mi.mesh, _shader(_unshaded(code)))
			var vl := _with_mode(code, "vertex_lighting")
			await _time(name + ":vertex_lit", mi.mesh, _shader(vl))
			if at >= 0:
				var vl_tex := vl.substr(0, vl.find("void fragment()")) + "uniform sampler2D baked_ : source_color;
void fragment() { ALBEDO = texture(baked_, UV).rgb; ROUGHNESS = 0.5; SPECULAR = 0.4; }
"
				await _time(name + ":vertex_lit_texture", mi.mesh, _shader(vl_tex))
			if at >= 0:
				var tex_unshaded := _unshaded(code).substr(0, _unshaded(code).find("void fragment()")) + "uniform sampler2D baked_ : source_color;\nvoid fragment() { ALBEDO = texture(baked_, UV).rgb; }\n"
				await _time(name + ":unshaded_texture", mi.mesh, _shader(tex_unshaded))
	hidden.queue_free()


# The same shader drawn unshaded (no lights).
func _unshaded(code: String) -> String:
	return _with_mode(code, "unshaded")


# The same shader with another render mode added.
func _with_mode(code: String, mode: String) -> String:
	var at := code.find("render_mode ")
	if at >= 0:
		return code.substr(0, at) + "render_mode " + mode + ", " + code.substr(at + "render_mode ".length())
	at = code.find(";")
	return code.substr(0, at + 1) + "\nrender_mode " + mode + ";" + code.substr(at + 1)


# One material drawn again under each thing that may make the engine compile another version of
# its program: an omni light, a spot light, a sky, a MultiMesh, no fog; and as vertex lighting.
func _time_variants() -> void:
	var sphere := SphereMesh.new()
	for lighting in ["", "render_mode vertex_lighting;
"]:
		var material := _shader("shader_type spatial;
" + lighting + "void fragment() { ALBEDO = vec3(0.5, 0.4, 0.3); }")
		var tag: String = "vertex_lit" if lighting != "" else "pixel_lit"
		await _time(tag + " base", sphere, material)
		await _time(tag + " again", sphere, material)
		var omni := OmniLight3D.new()
		omni.position = Vector3(0.0, 0.5, 1.0)
		omni.omni_range = 5.0
		_view_root.add_child(omni)
		await _time(tag + " omni", sphere, material)
		omni.queue_free()
		await process_frame
		var spot := SpotLight3D.new()
		spot.position = Vector3(0.0, 0.0, 2.0)
		spot.spot_range = 5.0
		_view_root.add_child(spot)
		await _time(tag + " spot", sphere, material)
		spot.queue_free()
		await process_frame
		_env.fog_enabled = false
		await _time(tag + " no_fog", sphere, material)
		_env.fog_enabled = true
		_env.background_mode = Environment.BG_SKY
		_env.sky = Sky.new()
		_env.sky.sky_material = ProceduralSkyMaterial.new()
		_env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
		_env.reflected_light_source = Environment.REFLECTION_SOURCE_DISABLED
		await _time(tag + " sky", sphere, material)
		_env.background_mode = Environment.BG_COLOR
		await process_frame
		var many := MultiMesh.new()
		many.transform_format = MultiMesh.TRANSFORM_3D
		many.mesh = sphere
		many.instance_count = 1
		var holder := MultiMeshInstance3D.new()
		holder.multimesh = many
		holder.material_override = material
		_view_root.add_child(holder)
		print("COST %s multimesh %.0f %.1f" % [tag, _draw_ms(), _draw_ms()])
		holder.queue_free()
		await process_frame
