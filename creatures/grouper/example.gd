extends Node3D
## A broomtail grouper hovering in blue water, seen from its side, opening its mouth now and then. Give
## this to a Node3D at the root of an empty scene and play that scene.

var fish: Grouper
var _clock := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.04, 0.2, 0.32)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.6, 0.72, 0.85)
	env.environment.ambient_light_energy = 0.8
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(1.5, 4.0, 2.5), Vector3.ZERO)
	fish = Grouper.new()
	add_child(fish)
	# (its nose is at -Z: turned a quarter, it faces the left of the picture)
	fish.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 0.180, 2.28), Vector3.ZERO)


func _process(delta: float) -> void:
	fish.step(Vector3.ZERO, delta)
	# (a gulp every four seconds)
	_clock = fmod(_clock + delta, 4.0)
	fish.gape = clampf(1.0 - absf(_clock - 3.4) / 0.35, 0.0, 1.0)
