extends Node3D
## Two cory catfish, a bronze and a panda, on a sandy floor, seen from the side: the bronze one resting
## on its belly, the panda swimming on the spot above it. Give this to a Node3D at the root of an empty
## scene and play that scene.

var resting: Corydoras
var swimming: Corydoras


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
	var floor := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(0.6, 0.6)
	floor.mesh = plane
	var sand := StandardMaterial3D.new()
	sand.albedo_color = Color(0.76, 0.7, 0.56)
	floor.material_override = sand
	add_child(floor)
	resting = Corydoras.new()
	add_child(resting)
	# (its nose is at -Z: turned a quarter, it faces the left of the picture; its flat belly is
	# Corydoras.BELLY below its origin)
	resting.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	resting.position = Vector3(0.03, Corydoras.BELLY, 0.0)
	resting.sway = 0.15
	swimming = Corydoras.new()
	swimming.kind = Corydoras.Kind.PANDA
	add_child(swimming)
	swimming.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	swimming.position = Vector3(-0.03, 0.04, -0.02)
	var camera := Camera3D.new()
	camera.fov = 40.0
	camera.near = 0.005
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 0.03, 0.2), Vector3(0.0, 0.02, 0.0))


func _process(delta: float) -> void:
	resting.step(Vector3.ZERO, delta)
	swimming.step(Vector3.ZERO, delta)
