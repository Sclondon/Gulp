extends Node3D
## A gulper eel swimming on the spot in the dark of the deep, seen from its side: its tail organ glows pink-red,
## and every few seconds it opens its mouth, the pouch ballooning out like a net, and closes it again. Give this to
## a Node3D at the root of an empty scene and play that scene.

var eel: GulperEel
var _time := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.0, 0.004, 0.012)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.4, 0.5, 0.7)
	env.environment.ambient_light_energy = 0.3
	add_child(env)
	var sun := DirectionalLight3D.new()
	sun.light_energy = 0.35
	add_child(sun)
	sun.look_at_from_position(Vector3(1.5, 4.0, 2.5), Vector3.ZERO)
	eel = GulperEel.new()
	add_child(eel)
	# (its nose is at -Z: turned a quarter, it faces the left of the picture)
	eel.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 0.1, 1.3), Vector3(0.0, 0.0, 0.0))


func _process(delta: float) -> void:
	_time += delta
	eel.step(Vector3.ZERO, delta)
	# open slowly, hold, close
	var t := fmod(_time, 7.0)
	eel.gape = clampf(minf(t / 1.5, (5.0 - t) / 1.0), 0.0, 1.0) if t < 5.0 else 0.0
