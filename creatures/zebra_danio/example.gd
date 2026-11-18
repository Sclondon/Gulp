extends Node3D
## A zebra danio swimming on the spot in blue water, seen from its side, and behind it a small school
## drawn by one MultiMesh from `ZebraDanio.school_mesh()`. Give this to a Node3D at the root of an
## empty scene and play that scene.

var danio: ZebraDanio


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
	danio = ZebraDanio.new()
	add_child(danio)
	# (its nose is at -Z: turned a quarter, it faces the left of the picture)
	danio.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	add_child(_school())
	var camera := Camera3D.new()
	camera.fov = 40.0
	camera.near = 0.005
	add_child(camera)
	camera.look_at_from_position(Vector3(0.01, 0.008, 0.11), Vector3.ZERO)


func _process(delta: float) -> void:
	danio.step(Vector3.ZERO, delta)


# Forty still ones behind it: the school model, coloured by its own vertex colours (a game's school
# would be GameCommon's Flock with this mesh as its `custom_mesh`, which also swims them).
func _school() -> MultiMeshInstance3D:
	var many := MultiMesh.new()
	many.transform_format = MultiMesh.TRANSFORM_3D
	# (under GL Compatibility a MultiMesh's vertex colours come out black without these)
	many.use_colors = true
	many.mesh = ZebraDanio.school_mesh()
	many.instance_count = 40
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	for i in many.instance_count:
		var at := Vector3(rng.randf_range(-0.15, 0.15), rng.randf_range(-0.06, 0.06), rng.randf_range(-0.3, -0.12))
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
