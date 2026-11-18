extends Node3D
## A California halibut swimming on the spot over the sand's colour, seen from above and a
## little to one side, opening its mouth now and then. Give this to a Node3D at the root of an
## empty scene and play that scene.

var halibut: CaliforniaHalibut
var _time := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.03, 0.16, 0.34)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.55, 0.7, 0.9)
	env.environment.ambient_light_energy = 0.7
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(1.5, 4.0, 2.5), Vector3.ZERO)
	halibut = CaliforniaHalibut.new()
	add_child(halibut)
	# (its nose is at -Z: turned a quarter, it faces the left of the picture)
	halibut.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 1.3, 1.2), Vector3.ZERO)


func _process(delta: float) -> void:
	_time += delta
	halibut.step(Vector3.ZERO, delta)
	# (a bite every four seconds)
	halibut.gape = clampf(1.0 - absf(fmod(_time, 4.0) - 3.5) * 4.0, 0.0, 1.0)
