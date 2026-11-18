extends Node3D
## A yellowfin tuna swimming on the spot in blue water, seen from its side. Give this to a
## Node3D at the root of an empty scene and play that scene.

var tuna: YellowfinTuna


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
	tuna = YellowfinTuna.new()
	add_child(tuna)
	# (its nose is at -Z: turned a quarter, it faces the left of the picture)
	tuna.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.3, 0.25, 2.6), Vector3.ZERO)


func _process(delta: float) -> void:
	tuna.step(Vector3.ZERO, delta)
