extends Node3D
## A spot prawn walking slowly forwards over sand, then darting backwards with a flick of its tail
## and settling again, swimmerets beating. Give this to a Node3D at the root of an empty scene and
## play that scene.

var prawn: SpotPrawn
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
	plane.size = Vector2(2.0, 2.0)
	sand.mesh = plane
	var paint := StandardMaterial3D.new()
	paint.albedo_color = Color(0.62, 0.56, 0.42)
	sand.material_override = paint
	add_child(sand)
	prawn = SpotPrawn.new()
	prawn.rotation_degrees.y = 90.0
	add_child(prawn)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 0.2, 0.6), Vector3(0.0, 0.04, 0.0))


func _process(delta: float) -> void:
	_time += delta
	# (every six seconds: four walking forwards, then a dart back, then drifting down)
	var t := fposmod(_time, 6.0)
	var ahead := -prawn.global_basis.z
	var velocity := Vector3.ZERO
	if t < 4.0:
		prawn.walk = 1.0
		prawn.paddle = 0.0
		prawn.flick = 0.0
		prawn.position.y = 0.0
		velocity = ahead * 0.02
	else:
		var s := t - 4.0
		prawn.walk = 0.0
		# a flick in a quarter of a second, lifting it and throwing it back; then it drifts down
		prawn.flick = sin(PI * clampf(s / 0.25, 0.0, 1.0))
		prawn.paddle = 1.0
		prawn.position.y = 0.06 * sin(PI * clampf(s / 2.0, 0.0, 1.0))
		velocity = -ahead * 0.5 * exp(-s * 4.0)
	prawn.position += velocity * delta
	prawn.position.x = wrapf(prawn.position.x, -0.4, 0.4)
	prawn.step(velocity, delta)
