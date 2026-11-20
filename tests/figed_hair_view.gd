extends SceneTree
## A figed head with its hair (tools/figed/hair.py -- ... --glb <file>) as the game draws it: the hair and moustache
## wear the hair shader (shaders/ink/hair_ink.gdshader), lit by a sun over the camera's shoulder and a sky light, from
## the head sheet's five angles (front, three-quarter right, side, three-quarter left, back), one strip.
##   godot --path . --audio-driver Dummy --resolution 420x480 --position 2600,60 -s tests/figed_hair_view.gd -- \
##       --glb=<file.glb> --out=<strip.png> [--set=hair.curl_rim=0.3 ...]   (a number setting tried without editing)
## The looks below are the older brother's (Claude's picks, to be tuned with the user).

const SHADER := preload("res://shaders/ink/hair_ink.gdshader")
const LOOKS := {
	"hair": {"albedo": Color(0.215, 0.115, 0.062), "ink": Color(0.085, 0.04, 0.025), "pale": Color(0.62, 0.36, 0.2),
			"lighten": 0.12, "soft": 1.0, "metres": 1.0, "root_ink": 0.0, "gap_ink": 0.12, "lit_lines": 0.0,
			"shadow_lines": 0.0, "locks": 0.0, "curl": 0.8, "curl_size": 0.036, "curl_gaps": 0.45, "curl_rim": 0.9,
			"curl_edge": 0.3, "flicks": Color(0.85, 0.45, 0.2), "flick_gain": 0.2, "flick_gloss": 10.0,
			"print_grain": 0.0, "wrap": 1.0, "flatness": 1.0, "shadow_fill": 0.85, "layer_shade": 1.0},
	"moustache": {"albedo": Color(0.55, 0.25, 0.1), "ink": Color(0.25, 0.09, 0.04), "pale": Color(0.8, 0.5, 0.25),
			"lighten": 0.1, "soft": 1.0, "metres": 1.0, "root_ink": 0.0, "gap_ink": 0.1, "strand_gap": 0.0016,
			"lit_lines": 0.35, "shadow_lines": 0.5, "tip_ragged": 0.1, "side_ragged": 0.05, "ragged_width": 0.003,
			"flick_gain": 0.1, "print_grain": 0.0, "wrap": 0.5, "flatness": 0.8, "shadow_fill": 0.5,
			"under_shade": 0.6},
}
const VIEWS := [0.0, -45.0, -90.0, 45.0, 180.0]

var _glb := ""
var _out := ""
var _sets := {}


func _initialize() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--glb="):
			_glb = a.substr(6)
		elif a.begins_with("--out="):
			_out = a.substr(6)
		elif a.begins_with("--set="):
			var kv := a.substr(6).split("=")
			_sets[kv[0]] = float(kv[1])
	_run.call_deferred()


func _meshes(n: Node, into: Array) -> void:
	if n is MeshInstance3D:
		into.append(n)
	for c in n.get_children():
		_meshes(c, into)


func _run() -> void:
	var doc := GLTFDocument.new()
	var state := GLTFState.new()
	if doc.append_from_file(_glb, state) != OK:
		push_error("cannot read " + _glb)
		quit(1)
		return
	var model: Node3D = doc.generate_scene(state)
	root.add_child(model)
	var all: Array = []
	_meshes(model, all)
	var box := AABB()
	for m in all:
		var key := String(m.name).to_lower()
		for piece in LOOKS:
			if key.begins_with(piece):
				var mat := ShaderMaterial.new()
				mat.shader = SHADER
				for k in LOOKS[piece]:
					mat.set_shader_parameter(k, LOOKS[piece][k])
				for k in _sets:
					if k.begins_with(piece + "."):
						mat.set_shader_parameter(k.substr(piece.length() + 1), _sets[k])
				m.material_override = mat
				if piece == "hair":
					box = m.global_transform * m.get_aabb()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.9, 0.9, 0.92)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(1, 1, 1)
	env.ambient_light_energy = 0.75
	var we := WorldEnvironment.new()
	we.environment = env
	root.add_child(we)
	var cam := Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.size = 0.42
	root.add_child(cam)
	var sun := DirectionalLight3D.new()
	sun.light_energy = 0.7
	cam.add_child(sun)
	sun.rotation_degrees = Vector3(-30, 25, 0)
	var centre := box.get_center() - Vector3(0, 0.07, 0)
	var size := root.size
	var strip := Image.create(size.x * VIEWS.size(), size.y, false, Image.FORMAT_RGBA8)
	for i in VIEWS.size():
		var a := deg_to_rad(VIEWS[i])
		cam.position = centre + Vector3(sin(a), 0, cos(a)) * 2.0
		cam.look_at(centre)
		for _f in 4:
			await process_frame
		var shot := root.get_texture().get_image()
		shot.convert(Image.FORMAT_RGBA8)
		strip.blit_rect(shot, Rect2i(Vector2i.ZERO, size), Vector2i(size.x * i, 0))
	strip.save_png(_out)
	print("saved ", _out)
	quit()
