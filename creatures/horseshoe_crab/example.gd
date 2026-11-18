extends Node3D
## An Atlantic horseshoe crab ploughing slowly round a circle on a sandy floor, seen from a little
## above. Give this to a Node3D at the root of an empty scene and play that scene.

var crab: HorseshoeCrab
var angle := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.03, 0.16, 0.3)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.55, 0.68, 0.85)
	env.environment.ambient_light_energy = 0.7
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(1.5, 4.0, 2.5), Vector3.ZERO)
	var floor_mesh := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(4.0, 4.0)
	floor_mesh.mesh = plane
	var sand := StandardMaterial3D.new()
	sand.albedo_color = Color(0.62, 0.56, 0.42)
	floor_mesh.material_override = sand
	add_child(floor_mesh)
	crab = HorseshoeCrab.new()
	crab.walk = 1.0
	add_child(crab)
	var camera := Camera3D.new()
	camera.fov = 45.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 0.9, 1.4), Vector3.ZERO)


func _process(delta: float) -> void:
	# (round a circle 0.5 m across at 4 cm a second, its head the way it goes)
	var was := crab.position
	angle += delta * 0.04 / 0.5
	crab.position = Vector3(cos(angle), 0.0, sin(angle)) * 0.5
	crab.look_at(crab.position + Vector3(-sin(angle), 0.0, cos(angle)), Vector3.UP)
	crab.step((crab.position - was) / maxf(delta, 0.0001), delta)
