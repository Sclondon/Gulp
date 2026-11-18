extends Node3D
## A neon tetra and a cardinal tetra swimming on the spot in dark water, seen from the side, and
## behind them a small school of neons drawn by one MultiMesh from `NeonTetra.school_mesh()`.
## Give this to a Node3D at the root of an empty scene and play that scene.

var neon: NeonTetra
var cardinal: NeonTetra


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.02, 0.06, 0.08)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.5, 0.6, 0.6)
	env.environment.ambient_light_energy = 0.6
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(1.5, 4.0, 2.5), Vector3.ZERO)
	neon = NeonTetra.new()
	add_child(neon)
	# (its nose is at -Z: turned a quarter, it faces the left of the picture)
	neon.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	neon.position = Vector3(0.0, 0.012, 0.0)
	cardinal = NeonTetra.new()
	cardinal.type = NeonTetra.Type.CARDINAL
	add_child(cardinal)
	cardinal.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	cardinal.position = Vector3(0.004, -0.014, 0.0)
	cardinal.phase = 0.37
	add_child(_school())
	var camera := Camera3D.new()
	camera.fov = 40.0
	camera.near = 0.002
	add_child(camera)
	camera.look_at_from_position(Vector3(0.006, 0.004, 0.11), Vector3.ZERO)


func _process(delta: float) -> void:
	neon.step(Vector3.ZERO, delta)
	cardinal.step(Vector3.ZERO, delta)


# Forty still neons behind them: the school model, coloured by its own vertex colours (a game's
# school would be GameCommon's Flock with this mesh as its `custom_mesh`, which also swims them).
func _school() -> MultiMeshInstance3D:
	var many := MultiMesh.new()
	many.transform_format = MultiMesh.TRANSFORM_3D
	# (under GL Compatibility a MultiMesh's vertex colours come out black without these)
	many.use_colors = true
	many.mesh = NeonTetra.school_mesh(NeonTetra.Type.NEON)
	many.instance_count = 40
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	for i in many.instance_count:
		var at := Vector3(rng.randf_range(-0.12, 0.12), rng.randf_range(-0.05, 0.05), rng.randf_range(-0.25, -0.08))
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
