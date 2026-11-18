extends Node3D
## The three kinds of trilobite walking slowly over sand side by side; every few seconds each in
## turn rolls up into a ball and opens out again. Give this to a Node3D at the root of an empty
## scene and play that scene.

var trilobites: Array[Trilobite] = []
var _time := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.04, 0.2, 0.3)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.55, 0.7, 0.8)
	env.environment.ambient_light_energy = 0.7
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(1.0, 4.0, 2.0), Vector3.ZERO)
	var sand := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(3.0, 3.0)
	sand.mesh = plane
	var paint := StandardMaterial3D.new()
	paint.albedo_color = Color(0.62, 0.56, 0.42)
	sand.material_override = paint
	add_child(sand)
	for which: Trilobite.Kind in [Trilobite.Kind.SMOOTH, Trilobite.Kind.SPINY, Trilobite.Kind.CHEEKS]:
		var trilobite := Trilobite.new()
		trilobite.kind = which
		trilobite.game = true
		trilobite.cartoon_eyes = 1.0
		trilobite.walk = 1.0
		# (its -Z is its front: turned a quarter, it walks to the left of the picture)
		trilobite.rotation_degrees.y = 90.0
		trilobite.position = Vector3(0.0, 0.0, -0.35 + 0.3 * which)
		add_child(trilobite)
		trilobites.append(trilobite)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 0.55, 1.1), Vector3(0.0, 0.03, 0.0))


func _process(delta: float) -> void:
	_time += delta
	for i in trilobites.size():
		var trilobite := trilobites[i]
		# (each rolls up for two seconds in every nine, one after another)
		var t := fposmod(_time - 3.0 * i, 9.0)
		trilobite.enroll = sin(PI * clampf((t - 6.0) / 3.0, 0.0, 1.0))
		var velocity := Vector3.ZERO
		if trilobite.enroll < 0.01:
			velocity = -trilobite.global_basis.z * 0.015 * Trilobite.LENGTHS[trilobite.kind] / 0.15
		trilobite.position += velocity * delta
		trilobite.position.x = wrapf(trilobite.position.x, -0.6, 0.6)
		trilobite.step(velocity, delta)
