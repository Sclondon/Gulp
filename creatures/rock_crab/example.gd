extends Node3D
## A red rock crab walking sideways to and fro over sand, raising its claws at each end. Give this
## to a Node3D at the root of an empty scene and play that scene.

var crab: RockCrab
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
	crab = RockCrab.new()
	add_child(crab)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 0.32, 0.55), Vector3(0.0, 0.03, 0.0))


func _process(delta: float) -> void:
	_time += delta
	# (across and back every eight seconds, pausing at each end with its claws up)
	var t := fposmod(_time, 8.0)
	var velocity := Vector3.ZERO
	if t < 3.0:
		velocity.x = 0.06
	elif t >= 4.0 and t < 7.0:
		velocity.x = -0.06
	crab.claws = move_toward(crab.claws, 1.0 if velocity == Vector3.ZERO else 0.0, delta * 2.0)
	crab.position += velocity * delta
	crab.step(velocity, delta)
