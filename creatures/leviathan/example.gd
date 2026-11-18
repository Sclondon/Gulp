extends Node3D
## A leviathan swimming on the spot in blue water, seen from its side, opening its jaws now and
## then, its cartoon eyes looking about. Give this to a Node3D at the root of an empty scene and
## play that scene.

var it: Leviathan
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
	it = Leviathan.new()
	it.game = true
	it.cartoon_eyes = 1.0
	add_child(it)
	# (its nose is at -Z: turned a quarter, it faces the left of the picture)
	it.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	var camera := Camera3D.new()
	camera.fov = 40.0
	camera.far = 400.0
	add_child(camera)
	camera.look_at_from_position(Vector3(2.0, 6.0, 64.0), Vector3.ZERO)


func _process(delta: float) -> void:
	_time += delta
	it.step(Vector3.ZERO, delta)
	it.gape = clampf(sin(_time * 0.6) * 3.0 - 2.0, 0.0, 1.0)
	it.eye_look = Vector2(sin(_time * 0.5), 0.4 * sin(_time * 0.8))
	it.blink = 1.0 if fposmod(_time, 4.3) < 0.15 else 0.0
