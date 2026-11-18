extends Node3D
## A longnose gar hanging nearly still in blue water, seen from its side, and every few seconds
## striking: its head and beak swing sideways as the beak opens and shuts. Give this to a Node3D
## at the root of an empty scene and play that scene.

var fish: Gar
var _time := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.05, 0.16, 0.2)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.6, 0.7, 0.75)
	env.environment.ambient_light_energy = 0.7
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(1.5, 4.0, 2.5), Vector3.ZERO)
	fish = Gar.new()
	fish.sway = 0.15
	add_child(fish)
	# (its nose is at -Z: turned a quarter, it faces the left of the picture)
	fish.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.1, 0.4, 1.6) * Gar.LENGTH, Vector3.ZERO)


func _process(delta: float) -> void:
	fish.step(Vector3.ZERO, delta)
	# (a strike every five seconds: the head swings out and the beak opens in a tenth of a
	# second, then both come back more slowly)
	_time = fmod(_time + delta, 5.0)
	var strike := smoothstep(4.3, 4.4, _time) * (1.0 - smoothstep(4.5, 4.9, _time))
	fish.snap = strike
	fish.gape = strike
