extends Node3D
## A California sea lion (a bull: it has its crest) flying on the spot in blue water, seen from its side, opening its mouth now and then; every third stroke it glides, its flippers folded back. Give this to a Node3D at the root of an empty scene and play that scene.

var lion: SeaLion
var _clock := 0.0


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
	lion = SeaLion.new()
	add_child(lion)
	# (its nose is at -Z: turned a quarter, it faces the left of the picture)
	lion.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.4, 0.3, 3.9), Vector3.ZERO)
	_more()


func _process(delta: float) -> void:
	_clock += delta
	lion.step(Vector3.ZERO, delta)
	# (it opens its mouth for a moment every few seconds)
	lion.gape = clampf(sin(_clock * 1.3) * 4.0 - 3.0, 0.0, 1.0)
	# (two strokes, then a glide)
	lion.fold = smoothstep(0.0, 0.3, fposmod(_clock / lion.beat, 3.0) - 2.0) * (1.0 - smoothstep(0.75, 1.0, fposmod(_clock / lion.beat, 3.0) - 2.0))


func _more() -> void:
	lion.crest = 1.0
