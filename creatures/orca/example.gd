extends Node3D
## An orca swimming on the spot in blue water, seen from behind and above as a player who has
## grown into one sees it; now and then it opens its mouth, and its dorsal fin goes slowly from a
## female's to a bull's and back. Give this to a Node3D at the root of an empty scene and play it.

var orca: Orca
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
	orca = Orca.new()
	add_child(orca)
	# (its nose is at -Z, away from the camera)
	var camera := Camera3D.new()
	camera.fov = 50.0
	add_child(camera)
	camera.look_at_from_position(Vector3(2.0, 3.2, 9.5), Vector3(0.0, 0.0, -1.0))


func _process(delta: float) -> void:
	_time += delta
	orca.step(Vector3.ZERO, delta)
	orca.gape = clampf(sin(_time * 1.1) * 3.0 - 2.0, 0.0, 1.0)
	orca.fin_tall = 0.5 + 0.5 * sin(_time * 0.4)
