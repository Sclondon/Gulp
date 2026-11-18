extends Node3D
## An oyster and a clump of oysters on a patch of sand, opening a little and shutting again; the single one has
## a pearl. Give this to a Node3D at the root of an empty scene and play that scene.

var single: Oyster
var clump: Oyster
var _time := 0.0


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
	var sand := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(1.0, 1.0)
	sand.mesh = plane
	var grey := StandardMaterial3D.new()
	grey.albedo_color = Color(0.62, 0.56, 0.44)
	sand.material_override = grey
	add_child(sand)
	single = Oyster.new()
	single.pearl = true
	add_child(single)
	single.position = Vector3(-0.12, 0.0, 0.0)
	clump = Oyster.new()
	clump.kind = Oyster.Kind.CLUMP
	add_child(clump)
	clump.position = Vector3(0.12, 0.0, 0.0)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 0.3, 0.45), Vector3(0.0, 0.04, 0.0))


func _process(delta: float) -> void:
	_time += delta
	var opened := smoothstep(1.0, 3.0, fposmod(_time, 8.0)) - smoothstep(6.0, 8.0, fposmod(_time, 8.0))
	for oyster in [single, clump]:
		oyster.open = opened
		oyster.step(Vector3.ZERO, delta)
