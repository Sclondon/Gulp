extends Node3D
## A firefly squid swimming on the spot in the dark of the deep, seen from its side, waves of light running back
## along it, and behind it a small school drawn by one MultiMesh from `FireflySquid.school_mesh()`, whose lights glow
## by the mask in the mesh's vertex alpha. Every few seconds it flashes. Give this to a Node3D at the root of an
## empty scene and play that scene.

var squid: FireflySquid
var time := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.0, 0.005, 0.02)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.4, 0.5, 0.7)
	env.environment.ambient_light_energy = 0.3
	add_child(env)
	var sun := DirectionalLight3D.new()
	sun.light_energy = 0.4
	add_child(sun)
	sun.look_at_from_position(Vector3(1.5, 4.0, 2.5), Vector3.ZERO)
	squid = FireflySquid.new()
	add_child(squid)
	# (its arms are at -Z: turned a quarter, they point to the left of the picture)
	squid.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	add_child(_school())
	var camera := Camera3D.new()
	camera.fov = 40.0
	camera.near = 0.005
	add_child(camera)
	camera.look_at_from_position(Vector3(0.01, 0.012, 0.15), Vector3.ZERO)


func _process(delta: float) -> void:
	time += delta
	squid.step(Vector3.ZERO, delta)
	squid.spread = 0.5 + 0.5 * sin(time * 0.7)
	if fmod(time, 5.0) < delta:
		squid.flash()


# Forty still ones behind it: the school model, coloured by its own vertex colours, its lights made to glow by the
# vertex alpha (a game's school would be GameCommon's Flock with this mesh as its `custom_mesh`, which also swims
# them; Flock's own shader draws the lights bright but does not make them glow).
func _school() -> MultiMeshInstance3D:
	var many := MultiMesh.new()
	many.transform_format = MultiMesh.TRANSFORM_3D
	# (under GL Compatibility a MultiMesh's vertex colours come out black without these)
	many.use_colors = true
	many.mesh = FireflySquid.school_mesh()
	many.instance_count = 40
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	for i in many.instance_count:
		var at := Vector3(rng.randf_range(-0.25, 0.25), rng.randf_range(-0.1, 0.1), rng.randf_range(-0.45, -0.18))
		many.set_instance_transform(i, Transform3D(Basis(Vector3.UP, PI * 0.5 + rng.randf_range(-0.2, 0.2)), at))
		many.set_instance_color(i, Color.WHITE)
	var shader := Shader.new()
	shader.code = "shader_type spatial;\nrender_mode cull_disabled;\nvoid fragment() {\n\tALBEDO = COLOR.rgb;\n\tEMISSION = COLOR.rgb * COLOR.a * 2.0;\n\tROUGHNESS = 0.5;\n\tif (!FRONT_FACING) {\n\t\tNORMAL = -NORMAL;\n\t}\n}\n"
	var material := ShaderMaterial.new()
	material.shader = shader
	var school := MultiMeshInstance3D.new()
	school.multimesh = many
	school.material_override = material
	return school
