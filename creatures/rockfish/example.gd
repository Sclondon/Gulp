extends Node3D
## A vermilion rockfish hovering on the spot in blue water, seen from its side, opening its mouth every
## few seconds. Give this to a Node3D at the root of an empty scene and play that scene.

var fish: Rockfish
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
	fish = Rockfish.new()
	add_child(fish)
	# (its nose is at -Z: turned a quarter, it faces the left of the picture)
	fish.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.1, 0.1, 1.8) * Rockfish.LENGTH, Vector3.ZERO)


func _process(delta: float) -> void:
	fish.step(Vector3.ZERO, delta)
	# (a bite: open quickly, shut quicker, every four seconds)
	_time = fmod(_time + delta, 4.0)
	fish.gape = smoothstep(3.3, 3.7, _time) * (1.0 - smoothstep(3.8, 3.95, _time))
