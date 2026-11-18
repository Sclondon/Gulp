extends Node3D
## Sea grass's example: a bed of 600 tufts on a sandy floor, a gentle current from the left, and a
## ball swimming through it that lays the grass aside. Give this script to a Node3D at the root
## of a scene and run it. (If the project declares no `water_clock` shader global, the bed adds
## one and runs it.)

var _bed: SeaGrassBed
var _ball: MeshInstance3D


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.1, 0.38, 0.45)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.55, 0.8, 0.85)
	env.environment.ambient_light_energy = 0.8
	env.environment.fog_enabled = true
	env.environment.fog_light_color = Color(0.1, 0.38, 0.45)
	env.environment.fog_density = 0.04
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(2.0, 10.0, 3.0), Vector3.ZERO)

	var floor_ := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(80.0, 80.0)
	floor_.mesh = plane
	var sand := StandardMaterial3D.new()
	sand.albedo_color = Color(0.55, 0.5, 0.38)
	floor_.material_override = sand
	add_child(floor_)

	var places := PackedVector3Array()
	var heights := PackedFloat32Array()
	var rng := RandomNumberGenerator.new()
	rng.seed = 5
	for i in 600:
		places.append(Vector3(rng.randf_range(-8.0, 8.0), 0.0, rng.randf_range(-10.0, 4.0)))
		heights.append(rng.randf_range(0.4, 1.2))
	_bed = SeaGrassBed.new()
	add_child(_bed)
	_bed.current = Vector2(0.35, 0.1)
	_bed.plant(places, heights)

	_ball = MeshInstance3D.new()
	_ball.mesh = SphereMesh.new()
	_ball.scale = Vector3.ONE * 0.4
	add_child(_ball)

	var camera := Camera3D.new()
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 2.2, 6.0), Vector3(0.0, 0.2, -3.0))
	camera.current = true
	print("SEA GRASS EXAMPLE ", _bed.counts())


func _process(_delta: float) -> void:
	var seconds := Time.get_ticks_msec() / 1000.0
	# (a project that declares `water_clock` runs it itself: here, as the game would)
	if ProjectSettings.has_setting("shader_globals/water_clock"):
		RenderingServer.global_shader_parameter_set(&"water_clock", seconds)
	_ball.position = Vector3(sin(seconds * 0.4) * 5.0, 0.35, -3.0 + cos(seconds * 0.3) * 4.0)
	_bed.pushers = PackedVector3Array([_ball.position])
