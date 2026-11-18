extends Node3D
## A northern pike in green lake water, seen from its side: it hangs still, then strikes (a few
## fast tail beats, its mouth opening), and hangs again. Give this to a Node3D at the root of an
## empty scene and play that scene.

var pike: NorthernPike
var _time := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.12, 0.2, 0.14)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.7, 0.78, 0.65)
	env.environment.ambient_light_energy = 0.7
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(1.5, 4.0, 2.5), Vector3.ZERO)
	pike = NorthernPike.new()
	add_child(pike)
	# (its nose is at -Z: turned a quarter, it faces the left of the picture)
	pike.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.1, 0.1, 2.0), Vector3.ZERO)


func _process(delta: float) -> void:
	_time += delta
	# four seconds hanging, then a strike of half a second
	var t := fmod(_time, 4.5)
	var striking := t > 4.0
	pike.sway = 1.6 if striking else 0.08
	pike.beat = 0.25 if striking else 3.0
	pike.gape = clampf(1.0 - absf(t - 4.3) / 0.2, 0.0, 1.0)
	pike.step(Vector3.ZERO, delta)
