extends Node3D
## The three surgeonfish swimming on the spot in blue water, seen from their sides: a yellow tang,
## a powder blue and a convict, one above the other. Give this to a Node3D at the root of an empty
## scene and play that scene.

var fish: Array[Surgeonfish] = []


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
	for i in 3:
		var one := Surgeonfish.new()
		one.kind = i as Surgeonfish.Kind
		add_child(one)
		# (its nose is at -Z: turned a quarter, it faces the left of the picture)
		one.rotation_degrees = Vector3(0.0, 90.0, 0.0)
		one.position = Vector3(0.0, 0.3 - 0.3 * i, 0.0)
		one.phase = i * 0.3
		fish.append(one)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.05, 0.0, 1.25), Vector3.ZERO)


func _process(delta: float) -> void:
	for one in fish:
		one.step(Vector3.ZERO, delta)
