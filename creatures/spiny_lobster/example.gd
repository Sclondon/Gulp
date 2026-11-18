extends Node3D
## A California spiny lobster walking slowly forwards over sand, pausing now and then, its
## antennae swinging. Give this to a Node3D at the root of an empty scene and play that scene.

var lobster: SpinyLobster
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
	plane.size = Vector2(8.0, 8.0)
	sand.mesh = plane
	var paint := StandardMaterial3D.new()
	paint.albedo_color = Color(0.62, 0.56, 0.42)
	sand.material_override = paint
	add_child(sand)
	lobster = SpinyLobster.new()
	lobster.rotation_degrees.y = 90.0
	add_child(lobster)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 0.8, 2.2), Vector3(0.0, 0.1, 0.0))


func _process(delta: float) -> void:
	_time += delta
	# (every eight seconds: six walking forwards, two standing)
	var walking := fposmod(_time, 8.0) < 6.0
	lobster.walk = 1.0 if walking else 0.0
	var velocity := -lobster.global_basis.z * 0.08 if walking else Vector3.ZERO
	lobster.position += velocity * delta
	lobster.position.x = wrapf(lobster.position.x, -1.5, 1.5)
	lobster.step(velocity, delta)
