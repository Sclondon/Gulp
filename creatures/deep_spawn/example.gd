extends Node3D
## Three deep spawn swimming on the spot in the dark, sharing one material, their tentacles spreading
## now and then. Give this to a Node3D at the root of an empty scene and play that scene.

var spawn: Array[DeepSpawn] = []
var _time := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.01, 0.03, 0.05)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.3, 0.4, 0.5)
	env.environment.ambient_light_energy = 0.5
	add_child(env)
	var sun := DirectionalLight3D.new()
	sun.light_energy = 0.4
	add_child(sun)
	sun.look_at_from_position(Vector3(1.5, 4.0, 2.5), Vector3.ZERO)
	for k in 3:
		var one := DeepSpawn.new()
		one.game = true
		one.phase = k * 0.3
		add_child(one)
		one.position = Vector3(0.0, 0.7 * (k - 1), -0.6 * absf(k - 1))
		one.rotation_degrees = Vector3(0.0, 90.0, 0.0)
		spawn.append(one)
	var camera := Camera3D.new()
	camera.fov = 45.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 0.3, 3.6), Vector3.ZERO)


func _process(delta: float) -> void:
	_time += delta
	for k in spawn.size():
		spawn[k].step(Vector3.ZERO, delta)
		spawn[k].gape = clampf(sin(_time * 1.2 + k * 2.0) * 3.0 - 2.0, 0.0, 1.0)
