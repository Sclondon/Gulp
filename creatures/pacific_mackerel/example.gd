extends Node3D
## A Pacific mackerel swimming on the spot in blue water, seen from its side, opening and shutting
## its mouth now and then, and behind it a small school drawn by one MultiMesh from
## `PacificMackerel.school_mesh()`. Give this to a Node3D at the root of an empty scene and play
## that scene.

var mackerel: PacificMackerel
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
	mackerel = PacificMackerel.new()
	add_child(mackerel)
	# (its nose is at -Z: turned a quarter, it faces the left of the picture)
	mackerel.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	add_child(_school())
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.07, 0.05, 0.78), Vector3.ZERO)


func _process(delta: float) -> void:
	_time += delta
	mackerel.step(Vector3.ZERO, delta)
	# (a bite every three seconds)
	mackerel.gape = clampf(1.0 - absf(fposmod(_time, 3.0) - 1.5) * 4.0, 0.0, 1.0)


# Forty still ones behind it: the school model, coloured by its own vertex colours (a game's
# school would be GameCommon's Flock with this mesh as its `custom_mesh`, which also swims them).
func _school() -> MultiMeshInstance3D:
	var many := MultiMesh.new()
	many.transform_format = MultiMesh.TRANSFORM_3D
	# (under GL Compatibility a MultiMesh's vertex colours come out black without these)
	many.use_colors = true
	many.mesh = PacificMackerel.school_mesh()
	many.instance_count = 40
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	for i in many.instance_count:
		var at := Vector3(rng.randf_range(-1.3, 1.3), rng.randf_range(-0.55, 0.55), rng.randf_range(-2.2, -0.9))
		many.set_instance_transform(i, Transform3D(Basis(Vector3.UP, PI * 0.5 + rng.randf_range(-0.2, 0.2)), at))
		many.set_instance_color(i, Color.WHITE)
	var shader := Shader.new()
	shader.code = "shader_type spatial;\nrender_mode cull_disabled;\nvoid fragment() {\n\tALBEDO = COLOR.rgb;\n\tROUGHNESS = 0.5;\n\tif (!FRONT_FACING) {\n\t\tNORMAL = -NORMAL;\n\t}\n}\n"
	var material := ShaderMaterial.new()
	material.shader = shader
	var school := MultiMeshInstance3D.new()
	school.multimesh = many
	school.material_override = material
	return school
