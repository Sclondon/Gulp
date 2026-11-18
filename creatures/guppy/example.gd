extends Node3D
## A female guppy and the four kinds of male swimming on the spot, seen from the side. Give this to
## a Node3D at the root of an empty scene and play that scene.

var guppies: Array[Guppy] = []


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.05, 0.14, 0.12)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.6, 0.7, 0.65)
	env.environment.ambient_light_energy = 0.7
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(1.5, 4.0, 2.5), Vector3.ZERO)
	var row := 0
	for which: int in Guppy.Type.values():
		var guppy := Guppy.new()
		guppy.type = which
		guppy.phase = row * 0.21
		add_child(guppy)
		# (its nose is at -Z: turned a quarter, it faces the left of the picture)
		guppy.rotation_degrees = Vector3(0.0, 90.0, 0.0)
		guppy.position = Vector3(0.0, 0.05 - row * 0.025, 0.0)
		guppies.append(guppy)
		row += 1
	var camera := Camera3D.new()
	camera.fov = 40.0
	camera.near = 0.002
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 0.0, 0.2), Vector3.ZERO)


func _process(delta: float) -> void:
	for guppy in guppies:
		guppy.step(Vector3.ZERO, delta)
