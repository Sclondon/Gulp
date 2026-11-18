extends SceneTree
## The new captain (models/captain.glb) as the game would show him: lit (a sun from his upper front left, soft sky
## light), a perspective camera of 35 degrees at about eye height. Front, three-quarter, side, three-quarter back, and a
## close head-and-shoulders three-quarter; cap on, then the same with the cap off.
##   godot --path . --audio-driver Dummy --resolution 700x900 -s tests/captain_beauty.gd -- --out=<folder>

const MODEL := "res://models/captain.glb"

var _out := ""
var _cam: Camera3D
var _model: Node3D
var _shots: Array = []
var _frame := 0
var _sun: DirectionalLight3D


func _initialize() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			_out = a.get_slice("=", 1)
	var world := Node3D.new()
	root.add_child(world)
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.78, 0.8, 0.82)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	# (fourteenth round: the shaded side went near black and grey under a weak blue sky light; a fuller, more neutral
	# sky light, as an outdoor day scene has)
	env.ambient_light_color = Color(0.86, 0.87, 0.9)
	env.ambient_light_energy = 0.35
	env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	var we := WorldEnvironment.new()
	we.environment = env
	world.add_child(we)
	var sun := DirectionalLight3D.new()
	sun.basis = Basis.looking_at(Vector3(-0.5, -0.7, -0.55).normalized(), Vector3.UP)
	sun.light_energy = 0.6
	_sun = sun
	sun.shadow_enabled = true
	world.add_child(sun)
	_model = (load(MODEL) as PackedScene).instantiate() as Node3D
	world.add_child(_model)
	for mesh: MeshInstance3D in _model.find_children("*", "MeshInstance3D", true, false):
		mesh.lod_bias = 64.0
		if String(mesh.name).begins_with("captain_body_under"):
			mesh.visible = false
	_cam = Camera3D.new()
	_cam.fov = 35.0
	_cam.near = 0.05
	world.add_child(_cam)
	for cap in [true, false]:
		var tag := "" if cap else "_nocap"
		for b in [["front", Vector3(0, 0, 1)], ["three_quarter", Vector3(0.7, 0, 0.7)], ["side", Vector3(-1, 0, 0)], ["three_quarter_back", Vector3(0.7, 0, -0.7)]]:
			_shots.append([b[0] + tag, (b[1] as Vector3).normalized(), Vector3(0, 0.86, 0), 3.3, cap])
		# (the close head shot pulled back and up a little: it cut off the top of his head)
		_shots.append(["close" + tag, Vector3(0.62, 0.05, 0.78).normalized(), Vector3(0.0, 1.4, 0.03), 1.95, cap])
	# close-ups of his left hand and left foot (cap on; it does not show)
	_shots.append(["hand", Vector3(0.75, 0.1, 0.65).normalized(), Vector3(0.43, 0.7, 0.0), 0.75, true])
	_shots.append(["foot", Vector3(0.35, 0.5, 0.8).normalized(), Vector3(0.17, 0.05, 0.1), 0.7, true])
	# (fifteenth round: the boxers close, from his front three-quarter)
	_shots.append(["boxers", Vector3(0.55, 0.12, 0.83).normalized(), Vector3(0.0, 0.62, 0.0), 1.05, true])


func _process(_delta: float) -> bool:
	var f := _frame
	_frame += 1
	var i := f / 5
	if i >= _shots.size():
		return true
	var shot: Array = _shots[i]
	if f % 5 == 0:
		for mesh: MeshInstance3D in _model.find_children("captain_cap*", "MeshInstance3D", true, false):
			mesh.visible = shot[4]
		var at: Vector3 = shot[2]
		# (the eye at about his eye height for the whole-body views, looking a little down at his middle)
		var eye: Vector3 = at + (shot[1] as Vector3) * float(shot[3])
		if float(shot[3]) > 2.0:
			eye.y = 1.5
		_cam.position = eye
		_cam.look_at(at, Vector3.UP)
		# (the sun over the camera's left shoulder for every shot, so no view is lit from behind)
		var to := (at - eye).normalized()
		var light := (to + _cam.global_transform.basis.x * -0.45 + Vector3(0, -0.6, 0)).normalized()
		_sun.basis = Basis.looking_at(light, Vector3.UP)
	elif f % 5 == 4 and _out != "":
		root.get_texture().get_image().save_png("%s/%s.png" % [_out, shot[0]])
	return false
