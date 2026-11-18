extends Node3D
## Seaweed's example: patches of each of the five floor kinds on a sandy floor, mats of sargassum
## on the surface 6 m up, a gentle current from the left, and a camera turning slowly round. Give
## this script to a Node3D at the root of a scene and run it. (If the project declares no
## `water_clock` shader global, the bed adds one and runs it.)

const SURFACE := 6.0

var _camera: Camera3D


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
	var sizes := PackedFloat32Array()
	var kinds := PackedInt32Array()
	var rng := RandomNumberGenerator.new()
	rng.seed = 5
	# (each kind in a patch of its own round a point; sargassum spread over the whole surface)
	var patches := {
		SeaweedBed.Kind.SEA_LETTUCE: Vector2(-4.0, 3.0),
		SeaweedBed.Kind.ROCKWEED: Vector2(4.0, 3.0),
		SeaweedBed.Kind.RED_ALGAE: Vector2(0.0, -1.0),
		SeaweedBed.Kind.FEATHER_BOA: Vector2(-4.0, -5.0),
		SeaweedBed.Kind.SEA_PALM: Vector2(4.0, -5.0),
		SeaweedBed.Kind.SARGASSUM: Vector2(0.0, 0.0),
	}
	for kind: int in patches:
		var spread := 8.0 if kind == SeaweedBed.Kind.SARGASSUM else 2.5
		for i in 50:
			var r := sqrt(rng.randf()) * spread
			var a := rng.randf() * TAU
			var at: Vector2 = patches[kind] + Vector2(cos(a), sin(a)) * r
			places.append(Vector3(at.x, 0.0, at.y))
			sizes.append(SeaweedBed.SIZE[kind] * rng.randf_range(0.7, 1.4))
			kinds.append(kind)
	var bed := SeaweedBed.new()
	add_child(bed)
	bed.current = Vector2(0.3, 0.05)
	bed.plant(places, sizes, kinds, SURFACE)

	_camera = Camera3D.new()
	add_child(_camera)
	_camera.current = true
	print("SEAWEED EXAMPLE ", bed.counts())


func _process(_delta: float) -> void:
	var seconds := Time.get_ticks_msec() / 1000.0
	# (a project that declares `water_clock` runs it itself: here, as the game would)
	if ProjectSettings.has_setting("shader_globals/water_clock"):
		RenderingServer.global_shader_parameter_set(&"water_clock", seconds)
	var a := seconds * 0.1
	_camera.look_at_from_position(Vector3(sin(a) * 11.0, 2.0, cos(a) * 11.0), Vector3(0.0, 1.0, -1.0))
