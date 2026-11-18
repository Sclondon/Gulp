extends Node3D
## The three anemones side by side on the sand, swaying; every few seconds each in turn draws in
## (`retract` up quickly) and slowly opens again. Give this to a Node3D at the root of an empty scene
## and play that scene. (The project must declare the shader global `water_clock`, a float; this
## example moves it on, as a game would.)

var anemones: Array[Anemone] = []
var _time := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.04, 0.2, 0.3)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.55, 0.7, 0.8)
	env.environment.ambient_light_energy = 0.7
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(1.0, 4.0, 2.0), Vector3.ZERO)
	var sand := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(3.0, 3.0)
	sand.mesh = plane
	var paint := StandardMaterial3D.new()
	paint.albedo_color = Color(0.62, 0.56, 0.42)
	sand.material_override = paint
	add_child(sand)
	for i in 3:
		var anemone := Anemone.new()
		anemone.kind = i as Anemone.Kind
		anemone.position = Vector3(-0.45 + 0.45 * i, 0.0, 0.0)
		add_child(anemone)
		anemones.append(anemone)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 0.55, 1.6), Vector3(0.0, 0.15, 0.0))


func _process(delta: float) -> void:
	_time += delta
	if ProjectSettings.has_setting("shader_globals/water_clock"):
		RenderingServer.global_shader_parameter_set(&"water_clock", _time)
	# (every nine seconds one of them is touched: it draws in in half a second, then opens over four)
	for i in anemones.size():
		var t := fposmod(_time - 3.0 * i, 9.0)
		anemones[i].retract = clampf(t / 0.5, 0.0, 1.0) if t < 0.5 else clampf(1.0 - (t - 1.5) / 4.0, 0.0, 1.0)
