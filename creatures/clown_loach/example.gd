extends Node3D
## A clown loach wriggling on the spot in dim green water, seen from its side. Give this to a
## Node3D at the root of an empty scene and play that scene.

var loach: ClownLoach


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.05, 0.17, 0.15)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.75, 0.8, 0.75)
	env.environment.ambient_light_energy = 0.7
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(0.2, 0.5, 0.35), Vector3.ZERO)
	loach = ClownLoach.new()
	add_child(loach)
	# (its nose is at -Z: turned a quarter, it faces the left of the picture)
	loach.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	var camera := Camera3D.new()
	camera.fov = 40.0
	camera.near = 0.01
	add_child(camera)
	camera.look_at_from_position(Vector3(0.04, 0.03, 0.36), Vector3.ZERO)


func _process(delta: float) -> void:
	loach.step(Vector3.ZERO, delta)
