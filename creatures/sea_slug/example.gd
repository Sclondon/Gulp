extends Node3D
## The three sea slugs on a patch of sand: a sea hare and a Spanish dancer crawling for a while, then swimming
## just above the bottom, then crawling again; a blue dragon floating upside down at a water's surface above
## them, drifting, then paddling. Give this to a Node3D at the root of an empty scene and play that scene.

var slugs: Array[SeaSlug] = []
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
	plane.size = Vector2(2.0, 2.0)
	sand.mesh = plane
	var grey := StandardMaterial3D.new()
	grey.albedo_color = Color(0.62, 0.56, 0.44)
	sand.material_override = grey
	add_child(sand)
	for k in [SeaSlug.Kind.SEA_HARE, SeaSlug.Kind.SPANISH_DANCER, SeaSlug.Kind.BLUE_DRAGON]:
		var slug := SeaSlug.new()
		slug.kind = k
		add_child(slug)
		slugs.append(slug)
	# (heads to the left of the picture; the blue dragon, eight times life size, at a surface 0.3 m up)
	slugs[0].position = Vector3(-0.2, 0.0, 0.0)
	slugs[1].position = Vector3(0.22, 0.0, 0.0)
	slugs[2].position = Vector3(0.0, 0.3, 0.0)
	slugs[2].scale = Vector3.ONE * 8.0
	for slug in slugs:
		slug.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 0.45, 1.1), Vector3(0.0, 0.1, 0.0))


func _process(delta: float) -> void:
	_time += delta
	# (six seconds on the bottom, six swimming just above it)
	var up := smoothstep(5.0, 6.0, fposmod(_time, 12.0)) - smoothstep(11.0, 12.0, fposmod(_time, 12.0))
	for slug in slugs:
		slug.swim = up
		var beats: Vector2 = SeaSlug.BEATS[slug.kind]
		slug.beat = lerpf(beats.x, beats.y, up)
		slug.step(Vector3.ZERO, delta)
	slugs[0].position.y = 0.06 * up
	slugs[1].position.y = 0.06 * up
