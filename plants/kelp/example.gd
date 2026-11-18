extends Node3D
## Kelp's example: forty plants of mixed lengths on a sea floor 14 m down, a current from the
## left, seen from among them. Give this script to a Node3D at the root of a scene and run it.
## (If the project declares no `water_clock` shader global, the forest adds one and runs it.)


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.05, 0.3, 0.42)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.55, 0.8, 0.85)
	env.environment.ambient_light_energy = 0.8
	env.environment.fog_enabled = true
	env.environment.fog_light_color = Color(0.05, 0.3, 0.42)
	env.environment.fog_density = 0.03
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(2.0, 10.0, 3.0), Vector3.ZERO)

	var places := PackedVector3Array()
	var heights := PackedFloat32Array()
	var rng := RandomNumberGenerator.new()
	rng.seed = 5
	for i in 40:
		places.append(Vector3(rng.randf_range(-12.0, 12.0), -14.0, rng.randf_range(-14.0, 2.0)))
		heights.append(rng.randf_range(6.0, 20.0))
	var forest := KelpForest.new()
	add_child(forest)
	forest.current = Vector2(0.5, 0.1)
	forest.plant(places, heights, 0.0)

	var camera := Camera3D.new()
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, -9.0, 10.0), Vector3(0.0, -5.0, -6.0))
	camera.current = true
	print("KELP EXAMPLE ", forest.counts())


func _process(_delta: float) -> void:
	# (a project that declares `water_clock` runs it itself: here, as the game would)
	if ProjectSettings.has_setting("shader_globals/water_clock"):
		RenderingServer.global_shader_parameter_set(&"water_clock", Time.get_ticks_msec() / 1000.0)
