extends Node3D
## A Pacific krill swimming on the spot in blue water, seen from its side, and behind it a small
## swarm drawn by one MultiMesh from `Krill.school_mesh()`. Give this to a Node3D at the root of an
## empty scene and play that scene.

var krill: Krill


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
	krill = Krill.new()
	add_child(krill)
	# (its head is at -Z: turned a quarter, it faces the left of the picture)
	krill.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	add_child(_swarm())
	var camera := Camera3D.new()
	camera.fov = 40.0
	camera.near = 0.005
	add_child(camera)
	camera.look_at_from_position(Vector3(0.006, 0.005, 0.07), Vector3.ZERO)


func _process(delta: float) -> void:
	krill.step(Vector3.ZERO, delta)


# Sixty still ones behind it: the school model, coloured by its own vertex colours (a game's swarm
# would be GameCommon's Flock with this mesh as its `custom_mesh`, which also swims them).
func _swarm() -> MultiMeshInstance3D:
	var many := MultiMesh.new()
	many.transform_format = MultiMesh.TRANSFORM_3D
	# (under GL Compatibility a MultiMesh's vertex colours come out black without these)
	many.use_colors = true
	many.mesh = Krill.school_mesh()
	many.instance_count = 60
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	for i in many.instance_count:
		var at := Vector3(rng.randf_range(-0.12, 0.12), rng.randf_range(-0.05, 0.05), rng.randf_range(-0.2, -0.06))
		many.set_instance_transform(i, Transform3D(Basis(Vector3.UP, PI * 0.5 + rng.randf_range(-0.4, 0.4)), at))
		many.set_instance_color(i, Color.WHITE)
	var shader := Shader.new()
	shader.code = "shader_type spatial;\nrender_mode cull_disabled;\nvoid fragment() {\n\tALBEDO = COLOR.rgb;\n\tROUGHNESS = 0.4;\n\tif (!FRONT_FACING) {\n\t\tNORMAL = -NORMAL;\n\t}\n}\n"
	var material := ShaderMaterial.new()
	material.shader = shader
	var swarm := MultiMeshInstance3D.new()
	swarm.multimesh = many
	swarm.material_override = material
	return swarm
