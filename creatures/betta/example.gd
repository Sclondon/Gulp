extends Node3D
## The three bettas drifting on the spot, seen from the side: the royal blue calm, the red flaring
## and calming again every few seconds, the marble calm. Give this to a Node3D at the root of an
## empty scene and play that scene.

var bettas: Array[Betta] = []
var _time := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.03, 0.08, 0.08)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.6, 0.65, 0.7)
	env.environment.ambient_light_energy = 0.7
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(1.5, 4.0, 2.5), Vector3.ZERO)
	var row := 0
	for which: int in Betta.Type.values():
		var betta := Betta.new()
		betta.type = which
		betta.phase = row * 0.31
		add_child(betta)
		# (its nose is at -Z: turned a quarter, it faces the left of the picture)
		betta.rotation_degrees = Vector3(0.0, 90.0, 0.0)
		betta.position = Vector3(0.0, 0.045 - row * 0.045, 0.0)
		bettas.append(betta)
		row += 1
	var camera := Camera3D.new()
	camera.fov = 40.0
	camera.near = 0.002
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 0.0, 0.26), Vector3.ZERO)


func _process(delta: float) -> void:
	_time += delta
	for betta in bettas:
		betta.step(Vector3.ZERO, delta)
	# (the red one flares for two seconds in every six)
	var k := fmod(_time, 6.0)
	bettas[1].flare = clampf(minf(k - 1.5, 4.5 - k) * 1.5, 0.0, 1.0)
