extends SceneTree
## The new captain (models/captain.glb, built by tools/build_captain.py) alone, for comparing with his sheets. Not
## the game's captain yet: the title still uses models/title_captain.glb.
##   godot --path . --audio-driver Dummy --resolution 900x1200 -s tests/captain_view.gd -- --out=<folder>
## Saves, lit as the title lights its figures (a high sun and a pale sky's light) and unlit (his painted pictures
## only): the whole of him from the front, his right side, the back and three-quarter (front-left), orthographic;
## and his head from the front, three-quarter and his left side. Then quits.

const MODEL := "res://models/captain.glb"
const HAIR_SHADER := "res://shaders/ink/hair_ink.gdshader"
## Hair colours by mesh name: albedo, pale, ink, flicks, and the beard's look (see _hair).
const HAIR := {
	"captain_beard": [Color(0.5, 0.48, 0.45), Color(0.62, 0.6, 0.57), Color(0.24, 0.23, 0.22), Color(0.85, 0.84, 0.8)],
	"captain_headhair": [Color(0.46, 0.46, 0.45), Color(0.58, 0.58, 0.57), Color(0.22, 0.22, 0.22), Color(0.8, 0.8, 0.78)],
	"captain_chesthair": [Color(0.4, 0.38, 0.36), Color(0.5, 0.48, 0.46), Color(0.2, 0.19, 0.18), Color(0.75, 0.74, 0.72)],
}

var _out := ""
var _cam: Camera3D
var _sun: DirectionalLight3D
var _env: Environment
var _model: Node3D
var _shots: Array = []
var _frame := 0


func _initialize() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			_out = a.get_slice("=", 1)
	var world := Node3D.new()
	root.add_child(world)
	_env = Environment.new()
	_env.background_mode = Environment.BG_COLOR
	_env.background_color = Color(0.84, 0.85, 0.87)
	_env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	_env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	var we := WorldEnvironment.new()
	we.environment = _env
	world.add_child(we)
	_sun = DirectionalLight3D.new()
	# (the title's sun at mid morning: high, from his front left)
	_sun.basis = Basis.looking_at(Vector3(-0.45, -0.75, -0.5).normalized(), Vector3.UP)
	world.add_child(_sun)
	_model = (load(MODEL) as PackedScene).instantiate() as Node3D
	world.add_child(_model)
	for mesh: MeshInstance3D in _model.find_children("*", "MeshInstance3D", true, false):
		mesh.lod_bias = 64.0
		for key: String in HAIR:
			if String(mesh.name).begins_with(key):
				mesh.material_override = _hair(key)
	_cam = Camera3D.new()
	_cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	world.add_child(_cam)
	# (name, eye direction from him, look-at height, ortho size)
	var body := [["front", Vector3(0, 0, 1)], ["side", Vector3(-1, 0, 0)], ["back", Vector3(0, 0, -1)], ["three_quarter", Vector3(0.7, 0, 0.7)]]
	var head := [["head_front", Vector3(0, 0, 1)], ["head_three_quarter", Vector3(0.62, 0, 0.78)], ["head_side", Vector3(1, 0, 0)]]
	for lit in [true, false]:
		for b in body:
			_shots.append([b[0] + ("_lit" if lit else "_unlit"), b[1], 0.84, 1.78, lit])
		for h in head:
			_shots.append([h[0] + ("_lit" if lit else "_unlit"), h[1], 1.47, 0.46, lit])


func _hair(key: String) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = load(HAIR_SHADER)
	var c: Array = HAIR[key]
	m.set_shader_parameter(&"albedo", c[0])
	m.set_shader_parameter(&"pale", c[1])
	m.set_shader_parameter(&"ink", c[2])
	m.set_shader_parameter(&"flicks", c[3])
	m.set_shader_parameter(&"metres", 1.0)
	m.set_shader_parameter(&"strand_gap", 0.0038)
	m.set_shader_parameter(&"lit_lines", 0.035)
	m.set_shader_parameter(&"shadow_lines", 0.2)
	m.set_shader_parameter(&"wrap", 0.5)
	m.set_shader_parameter(&"shadow_fill", 0.5)
	m.set_shader_parameter(&"root_ink", 0.08)
	m.set_shader_parameter(&"gap_ink", 0.04)
	m.set_shader_parameter(&"flick_gain", 0.14)
	m.set_shader_parameter(&"lighten", 0.0)
	m.set_shader_parameter(&"tip_ragged", 0.22)
	m.set_shader_parameter(&"strand_cover", 0.92)
	m.set_shader_parameter(&"layer_shade", 1.0)
	m.set_shader_parameter(&"root_dark", 0.35)
	return m


func _set_lit(lit: bool) -> void:
	_sun.visible = lit
	_sun.light_energy = 0.9
	_env.ambient_light_color = Color(0.8, 0.85, 0.9) if lit else Color(1, 1, 1)
	_env.ambient_light_energy = 0.55 if lit else 1.0
	for mesh: MeshInstance3D in _model.find_children("*", "MeshInstance3D", true, false):
		for s in mesh.mesh.get_surface_count():
			var m := mesh.mesh.surface_get_material(s) as BaseMaterial3D
			if m:
				m.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL if lit else BaseMaterial3D.SHADING_MODE_UNSHADED


func _process(_delta: float) -> bool:
	var f := _frame
	_frame += 1
	var i := f / 3
	if i >= _shots.size():
		return true
	var shot: Array = _shots[i]
	if f % 3 == 0:
		_set_lit(shot[4])
		var dir: Vector3 = shot[1]
		_cam.size = shot[3]
		var at := Vector3(0, shot[2], 0)
		_cam.position = at + dir * 5.0
		_cam.look_at(at, Vector3.UP)
	elif f % 3 == 2 and _out != "":
		root.get_texture().get_image().save_png("%s/%s.png" % [_out, shot[0]])
	return false
