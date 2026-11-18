extends Node3D
## Two sea otters in blue water, seen from the side: one swimming on the spot, opening its mouth now and then; over it, one that rolls on to its back to float, paws on its chest, and back again. Give this to a Node3D at the root of an empty scene and play that scene.

var otter: SeaOtter
var _clock := 0.0
var floater: SeaOtter


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
	otter = SeaOtter.new()
	add_child(otter)
	# (its nose is at -Z: turned a quarter, it faces the left of the picture)
	otter.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.2, 0.35, 2.6), Vector3.ZERO)
	_more()


func _process(delta: float) -> void:
	_clock += delta
	otter.step(Vector3.ZERO, delta)
	# (it opens its mouth for a moment every few seconds)
	otter.gape = clampf(sin(_clock * 1.3) * 4.0 - 3.0, 0.0, 1.0)
	floater.step(Vector3.ZERO, delta)
	floater.afloat = smoothstep(-0.4, 0.4, sin(_clock * 0.5))


func _more() -> void:
	floater = SeaOtter.new()
	add_child(floater)
	floater.position = Vector3(0.0, 0.55, 0.0)
	floater.rotation_degrees = Vector3(0.0, 90.0, 0.0)
