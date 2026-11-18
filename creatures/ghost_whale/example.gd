extends Node3D
## A ghost whale swimming on the spot in dark water, seen from its side: it fades in, swims a while,
## opens its jaws now and then, and fades out again, over and over. Give this to a Node3D at the root
## of an empty scene and play that scene.

var it: GhostWhale
var _time := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.01, 0.04, 0.08)
	add_child(env)
	it = GhostWhale.new()
	it.game = true
	add_child(it)
	# (its nose is at -Z: turned a quarter, it faces the left of the picture)
	it.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(1.0, 2.0, 22.0), Vector3.ZERO)


func _process(delta: float) -> void:
	_time += delta
	it.step(Vector3.ZERO, delta)
	it.fade = clampf(sin(_time * 0.3) * 2.0 + 1.0, 0.0, 1.0)
	it.gape = clampf(sin(_time * 0.9) * 3.0 - 2.0, 0.0, 1.0)
