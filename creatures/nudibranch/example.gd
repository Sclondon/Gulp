extends Node3D
## A nudibranch on a patch of sand, crawling for a while, then swimming, then crawling again.
## Give this to a Node3D at the root of an empty scene and play that scene.

var slug: Nudibranch
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
	plane.size = Vector2(0.6, 0.6)
	sand.mesh = plane
	var grey := StandardMaterial3D.new()
	grey.albedo_color = Color(0.62, 0.56, 0.44)
	sand.material_override = grey
	add_child(sand)
	slug = Nudibranch.new()
	add_child(slug)
	# (its head is at -Z: turned a quarter, it faces the left of the picture)
	slug.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	var camera := Camera3D.new()
	camera.fov = 30.0
	camera.near = 0.01
	add_child(camera)
	camera.look_at_from_position(Vector3(0.03, 0.09, 0.2), Vector3(0.0, 0.015, 0.0))


func _process(delta: float) -> void:
	_time += delta
	# (six seconds on the bottom, six swimming just above it)
	var up := smoothstep(5.0, 6.0, fposmod(_time, 12.0)) - smoothstep(11.0, 12.0, fposmod(_time, 12.0))
	slug.swim = up
	slug.position.y = 0.025 * up
	slug.beat = lerpf(2.4, 1.1, up)
	slug.step(Vector3.ZERO, delta)
