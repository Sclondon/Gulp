extends Node3D
## A red lionfish hovering in blue water, seen from its side, its fins spread and waving; every
## few seconds it folds its fins and spines back, gulps, and spreads them again. Give this to a
## Node3D at the root of an empty scene and play that scene.

var fish: Lionfish
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
	fish = Lionfish.new()
	add_child(fish)
	# (its nose is at -Z: turned a quarter, it faces the left of the picture)
	fish.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.1, 0.15, 2.4) * Lionfish.LENGTH, Vector3(0.0, 0.02, 0.0))


func _process(delta: float) -> void:
	fish.step(Vector3.ZERO, delta)
	# (every six seconds: fins fold, a gulp, fins spread again)
	_time = fmod(_time + delta, 6.0)
	fish.spread = 1.0 - smoothstep(3.5, 4.0, _time) * (1.0 - smoothstep(5.0, 5.8, _time))
	fish.gape = smoothstep(4.1, 4.3, _time) * (1.0 - smoothstep(4.4, 4.6, _time))
