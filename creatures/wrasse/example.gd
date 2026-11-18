extends Node3D
## A bluestreak cleaner wrasse and a moon wrasse rowing on the spot in blue water, seen from their
## sides, each opening its mouth every few seconds. Give this to a Node3D at the root of an empty
## scene and play that scene.

var fish: Array[Wrasse] = []
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
	for which: Wrasse.Kind in [Wrasse.Kind.CLEANER, Wrasse.Kind.MOON]:
		var one := Wrasse.new()
		one.kind = which
		add_child(one)
		# (its nose is at -Z: turned a quarter, it faces the left of the picture)
		one.rotation_degrees = Vector3(0.0, 90.0, 0.0)
		one.position = Vector3(0.0, 0.09 if which == Wrasse.Kind.CLEANER else -0.07, 0.0)
		# (in their true sizes: the cleaner is under half as long as the moon)
		one.scale = Vector3.ONE * Wrasse.SIZE[which]
		fish.append(one)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 0.0, 0.55), Vector3.ZERO)


func _process(delta: float) -> void:
	_time = fmod(_time + delta, 4.0)
	for i in fish.size():
		fish[i].step(Vector3.ZERO, delta)
		# (a bite: open quickly, shut quicker, every four seconds, the two a second apart)
		var t := fmod(_time + i * 1.0, 4.0)
		fish[i].gape = smoothstep(3.3, 3.6, t) * (1.0 - smoothstep(3.7, 3.85, t))
