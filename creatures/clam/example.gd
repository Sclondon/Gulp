extends Node3D
## The three clams on a patch of sand: a giant clam opening and shutting slowly, a scallop that claps its way up
## off the bottom now and then and settles again, and a razor clam that lies with its foot out, then stands up
## and digs. Give this to a Node3D at the root of an empty scene and play that scene.

var giant: Clam
var scallop: Clam
var razor: Clam
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
	plane.size = Vector2(4.0, 4.0)
	sand.mesh = plane
	var grey := StandardMaterial3D.new()
	grey.albedo_color = Color(0.62, 0.56, 0.44)
	sand.material_override = grey
	add_child(sand)
	giant = Clam.new()
	giant.kind = Clam.Kind.GIANT
	add_child(giant)
	giant.position = Vector3(-0.5, 0.0, -0.3)
	# (the small two four times life size, so that they can be seen beside the giant)
	scallop = Clam.new()
	scallop.kind = Clam.Kind.SCALLOP
	add_child(scallop)
	scallop.position = Vector3(0.5, 0.0, 0.2)
	scallop.scale = Vector3.ONE * 4.0
	razor = Clam.new()
	razor.kind = Clam.Kind.RAZOR
	add_child(razor)
	razor.position = Vector3(0.6, 0.0, -0.5)
	razor.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	razor.scale = Vector3.ONE * 4.0
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 1.4, 2.6), Vector3(0.0, 0.2, -0.2))


func _process(delta: float) -> void:
	_time += delta
	var cycle := fposmod(_time, 12.0)
	giant.open = 0.5 - 0.5 * cos(_time * TAU / 12.0)
	# (the scallop swims for four seconds in twelve, rising, then sinks back and lies open)
	var swimming := cycle > 6.0 and cycle < 10.0
	scallop.swim = 1.0 if swimming else 0.0
	scallop.open = 0.7
	scallop.position.y = move_toward(scallop.position.y, 0.25 if swimming else 0.0, delta * 0.1)
	razor.dig = smoothstep(3.0, 5.0, cycle) - smoothstep(10.0, 12.0, cycle)
	razor.position.y = -0.2 * smoothstep(5.0, 10.0, cycle) * razor.dig
	for clam in [giant, scallop, razor]:
		clam.step(Vector3.ZERO, delta)
