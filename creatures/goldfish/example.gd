extends Node3D
## Goldfish swimming on the spot, seen from the side: a common goldfish in each colouring above, a
## fantail in each below. Give this to a Node3D at the root of an empty scene and play that scene.

var fish: Array[Goldfish] = []


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.05, 0.2, 0.3)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.7, 0.78, 0.85)
	env.environment.ambient_light_energy = 0.7
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(1.5, 4.0, 2.5), Vector3.ZERO)
	for kind: int in [Goldfish.Kind.COMMON, Goldfish.Kind.FANTAIL]:
		for colouring: int in [Goldfish.Colouring.ORANGE, Goldfish.Colouring.RED_WHITE, Goldfish.Colouring.CALICO]:
			var one := Goldfish.new()
			one.kind = kind
			one.colouring = colouring
			add_child(one)
			# (its nose is at -Z: turned a quarter, it faces the left of the picture)
			one.rotation_degrees = Vector3(0.0, 90.0, 0.0)
			one.position = Vector3((colouring - 1) * 0.19, 0.06 - kind * 0.12, 0.0)
			one.phase = colouring * 0.3
			fish.append(one)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 0.02, 0.75), Vector3.ZERO)


func _process(delta: float) -> void:
	for one in fish:
		one.step(Vector3.ZERO, delta)
