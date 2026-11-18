extends Node3D
## The mangroves' example: a bank of twenty trees and root clusters along a muddy shore, seen from
## under the water among their roots. Give this script to a Node3D at the root of a scene and run
## it. (If the project declares no `water_clock` shader global, the stand adds one and runs it.)


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.12, 0.3, 0.26)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.6, 0.75, 0.65)
	env.environment.ambient_light_energy = 0.8
	env.environment.fog_enabled = true
	env.environment.fog_light_color = Color(0.12, 0.3, 0.26)
	env.environment.fog_density = 0.05
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(2.0, 10.0, 3.0), Vector3.ZERO)

	var mud := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(80.0, 80.0)
	mud.mesh = plane
	mud.position.y = MangroveStand.MUD
	var brown := StandardMaterial3D.new()
	brown.albedo_color = Color(0.25, 0.2, 0.14)
	mud.material_override = brown
	add_child(mud)

	var places := PackedVector3Array()
	var turns := PackedFloat32Array()
	var sizes := PackedFloat32Array()
	var variants := PackedInt32Array()
	var rng := RandomNumberGenerator.new()
	rng.seed = 5
	for i in 20:
		places.append(Vector3(-24.0 + i * 2.5 + rng.randf_range(-0.8, 0.8), 0.0, -6.0 + rng.randf_range(-2.5, 2.5)))
		turns.append(rng.randf() * TAU)
		sizes.append(1.0)
		variants.append(4 + i % 2 if i % 3 == 2 else rng.randi() % MangroveStand.TREES)
	var stand := MangroveStand.new()
	add_child(stand)
	stand.plant(places, turns, sizes, variants)

	var camera := Camera3D.new()
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, -1.6, 5.0), Vector3(0.0, -1.0, -6.0))
	camera.current = true
	print("MANGROVE EXAMPLE ", stand.counts(), " spheres ", stand.spheres().size())


func _process(_delta: float) -> void:
	# (a project that declares `water_clock` runs it itself: here, as the game would)
	if ProjectSettings.has_setting("shader_globals/water_clock"):
		RenderingServer.global_shader_parameter_set(&"water_clock", Time.get_ticks_msec() / 1000.0)
