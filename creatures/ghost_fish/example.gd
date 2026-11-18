extends Node3D
## Ghost fish in dark water: one close up, swimming on the spot, and behind it a school of forty drawn
## by one MultiMesh with `GhostFish.school_material()`, each at its own beat, all fading in and out
## together. Give this to a Node3D at the root of an empty scene and play that scene.

var it: GhostFish
var _beats := PackedFloat32Array()
var _school: MultiMesh
var _time := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.01, 0.04, 0.08)
	add_child(env)
	it = GhostFish.new()
	add_child(it)
	it.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	_school = MultiMesh.new()
	_school.transform_format = MultiMesh.TRANSFORM_3D
	_school.use_custom_data = true
	_school.mesh = GhostFish.school_mesh(true)
	_school.instance_count = 40
	var rng := RandomNumberGenerator.new()
	rng.seed = 3
	for i in 40:
		var at := Vector3(rng.randf_range(-2.5, 2.5), rng.randf_range(-0.8, 0.8), rng.randf_range(-4.0, -1.5))
		_school.set_instance_transform(i, Transform3D(Basis(Vector3.UP, PI * 0.5 + rng.randf_range(-0.3, 0.3)), at))
		_beats.append(rng.randf() * TAU)
	var many := MultiMeshInstance3D.new()
	many.multimesh = _school
	many.material_override = GhostFish.school_material()
	add_child(many)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 0.3, 1.6), Vector3(0.0, 0.0, -1.0))


func _process(delta: float) -> void:
	_time += delta
	it.step(Vector3.ZERO, delta)
	var fade := clampf(sin(_time * 0.4) * 2.0 + 1.0, 0.0, 1.0)
	it.fade = fade
	GhostFish.school_material().set_shader_parameter(&"fade", fade)
	# (each fish's own beat, in radians, as GameCommon's Flock keeps it in the instance's custom data)
	for i in _beats.size():
		_beats[i] = fposmod(_beats[i] + delta * TAU / 0.6, TAU)
		_school.set_instance_custom_data(i, Color(_beats[i], 1.0, 0.0, 0.0))
