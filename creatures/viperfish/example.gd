extends Node3D
## A viperfish swimming on the spot in the dark of the deep, seen from its side: its photophores and the light on
## its long dorsal ray glow, and every few seconds it strikes, its jaw dropping and its head lifting back. Give
## this to a Node3D at the root of an empty scene and play that scene.

var fish: Viperfish
var _time := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.0, 0.004, 0.012)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.4, 0.5, 0.7)
	env.environment.ambient_light_energy = 0.25
	add_child(env)
	var sun := DirectionalLight3D.new()
	sun.light_energy = 0.3
	add_child(sun)
	sun.look_at_from_position(Vector3(1.5, 4.0, 2.5), Vector3.ZERO)
	fish = Viperfish.new()
	add_child(fish)
	# (its nose is at -Z: turned a quarter, it faces the left of the picture)
	fish.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 0.03, 0.55), Vector3(0.0, 0.02, 0.0))


func _process(delta: float) -> void:
	_time += delta
	fish.step(Vector3.ZERO, delta)
	var strike := fmod(_time, 4.0)
	fish.gape = clampf(1.0 - absf(strike - 0.35) / 0.35, 0.0, 1.0) if strike < 1.0 else 0.0
