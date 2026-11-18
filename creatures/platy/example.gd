extends Node3D
## Three platies swimming on the spot, seen from the side: a sunset, a red wagtail and a blue mickey
## mouse. Give this to a Node3D at the root of an empty scene and play that scene.

var fish: Array[Platy] = []


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.05, 0.2, 0.3)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.7, 0.78, 0.85)
	env.environment.ambient_light_energy = 0.7
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(1.5, 4.0, 2.5), Vector3.ZERO)
	for colouring: int in [Platy.Colouring.SUNSET, Platy.Colouring.RED_WAGTAIL, Platy.Colouring.BLUE_MICKEY]:
		var one := Platy.new()
		one.colouring = colouring
		add_child(one)
		# (its nose is at -Z: turned a quarter, it faces the left of the picture)
		one.rotation_degrees = Vector3(0.0, 90.0, 0.0)
		one.position = Vector3((colouring - 1) * 0.065, 0.0, 0.0)
		one.phase = colouring * 0.3
		fish.append(one)
	var camera := Camera3D.new()
	camera.fov = 40.0
	camera.near = 0.005
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 0.01, 0.28), Vector3.ZERO)


func _process(delta: float) -> void:
	for one in fish:
		one.step(Vector3.ZERO, delta)
