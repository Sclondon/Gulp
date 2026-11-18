extends Node3D
## Two clownfish hovering over their anemone in blue water. Give this to a Node3D at the root of an
## empty scene and play that scene. The anemone sways on the global shader uniform `water_clock`,
## which the project must declare (Project Settings > Shader Globals: a float named water_clock);
## this example moves it on itself.

var fish: Array[Clownfish] = []
var _clock := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.03, 0.2, 0.36)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.6, 0.75, 0.9)
	env.environment.ambient_light_energy = 0.7
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(1.5, 4.0, 2.5), Vector3.ZERO)
	add_child(ClownfishAnemone.new())
	for i in 2:
		var one := Clownfish.new()
		add_child(one)
		one.position = Vector3(-0.08 + 0.16 * i, 0.24 + 0.03 * i, 0.02 * i)
		one.rotation_degrees = Vector3(0.0, 70.0 + 40.0 * i, 0.0)
		one.phase = 0.4 * i
		fish.append(one)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 0.45, 0.85), Vector3(0.0, 0.14, 0.0))


func _process(delta: float) -> void:
	_clock += delta
	RenderingServer.global_shader_parameter_set(&"water_clock", _clock)
	for one in fish:
		one.step(Vector3.ZERO, delta)
