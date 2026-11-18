extends Node3D
## The three shrimps on the sand: the cleaner walking to and fro waving its antennae, the mantis
## shrimp punching every few seconds with its eyes swivelling, the pistol shrimp cocking its claw
## and snapping it shut; every eight seconds each darts back with a flick of its tail. Give this to
## a Node3D at the root of an empty scene and play that scene.

var shrimps: Array[Shrimp] = []
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
	plane.size = Vector2(1.0, 1.0)
	sand.mesh = plane
	var paint := StandardMaterial3D.new()
	paint.albedo_color = Color(0.62, 0.56, 0.42)
	sand.material_override = paint
	add_child(sand)
	for i in 3:
		var shrimp := Shrimp.new()
		shrimp.kind = i as Shrimp.Kind
		shrimp.cartoon_eyes = 1.0
		shrimp.rotation_degrees.y = 90.0
		shrimp.position = Vector3(0.0, 0.0, -0.12 + 0.12 * i)
		add_child(shrimp)
		shrimps.append(shrimp)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 0.16, 0.42), Vector3(0.0, 0.02, 0.0))


func _process(delta: float) -> void:
	_time += delta
	for i in shrimps.size():
		var shrimp := shrimps[i]
		var t := fposmod(_time + 1.3 * i, 8.0)
		var ahead := -shrimp.global_basis.z
		var velocity := Vector3.ZERO
		if t < 6.0:
			shrimp.flick = 0.0
			shrimp.paddle = 0.0
			shrimp.position.y = 0.0
			if shrimp.kind == Shrimp.Kind.CLEANER:
				shrimp.walk = 1.0
				velocity = ahead * 0.012 * (1.0 if t < 3.0 else -1.0)
			else:
				shrimp.walk = 0.0
			if shrimp.kind == Shrimp.Kind.MANTIS:
				# a punch every three seconds: out and back in a tenth of a second
				shrimp.strike = sin(PI * clampf(fposmod(t, 3.0) / 0.1, 0.0, 1.0))
			if shrimp.kind == Shrimp.Kind.PISTOL:
				# cocked over a second, then snapped shut at once
				var c := fposmod(t, 3.0)
				shrimp.snap = clampf(c - 1.0, 0.0, 1.0) if c < 2.0 else 0.0
		else:
			var s := t - 6.0
			shrimp.walk = 0.0
			shrimp.strike = 0.0
			shrimp.snap = 0.0
			shrimp.flick = sin(PI * clampf(s / 0.2, 0.0, 1.0))
			shrimp.paddle = 1.0
			shrimp.position.y = 0.02 * sin(PI * clampf(s / 2.0, 0.0, 1.0))
			velocity = -ahead * 0.25 * exp(-s * 5.0)
		shrimp.position += velocity * delta
		shrimp.position.x = wrapf(shrimp.position.x, -0.3, 0.3)
		shrimp.step(velocity, delta)
