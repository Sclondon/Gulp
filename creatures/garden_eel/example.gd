extends Node3D
## A field of garden eels on the sand, with one close up in front, and a ball (standing in for
## something that frightens them) passing through: the eels near it sink and come back out after.
## Give this to a Node3D at the root of an empty scene and play that scene.

var eel: GardenEel
var colony: GardenEelColony
var ball: MeshInstance3D
var _time := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.05, 0.25, 0.4)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.55, 0.7, 0.85)
	env.environment.ambient_light_energy = 0.7
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(1.5, 4.0, 2.5), Vector3.ZERO)
	var sand := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(12.0, 12.0)
	sand.mesh = plane
	var tan := StandardMaterial3D.new()
	tan.albedo_color = Color(0.7, 0.64, 0.5)
	sand.material_override = tan
	add_child(sand)
	eel = GardenEel.new()
	add_child(eel)
	eel.position = Vector3(0.0, 0.0, 0.6)
	# (heads into the current, which comes from the left of the picture)
	eel.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	colony = GardenEelColony.new()
	colony.facing = Vector3(-1.0, 0.0, 0.0)
	add_child(colony)
	var places := PackedVector3Array()
	var dice := RandomNumberGenerator.new()
	dice.seed = 7
	while places.size() < 300:
		var at := Vector3(dice.randf_range(-3.0, 3.0), 0.0, dice.randf_range(-4.0, 0.2))
		var ok := true
		for other in places:
			if other.distance_to(at) < 0.22:
				ok = false
				break
		if ok:
			places.append(at)
	colony.plant(places)
	ball = MeshInstance3D.new()
	var round_mesh := SphereMesh.new()
	round_mesh.radius = 0.12
	round_mesh.height = 0.24
	ball.mesh = round_mesh
	add_child(ball)
	var camera := Camera3D.new()
	camera.fov = 45.0
	camera.near = 0.02
	add_child(camera)
	camera.look_at_from_position(Vector3(0.4, 0.55, 1.6), Vector3(0.0, 0.2, -0.6))


func _process(delta: float) -> void:
	_time += delta
	eel.step(Vector3.ZERO, delta)
	# (the ball swims across the field and back every 16 seconds)
	ball.position = Vector3(3.5 * sin(_time * TAU / 16.0), 0.45, -1.5)
	colony.disturb(ball.position, 1.0)
