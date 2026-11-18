extends Node3D
## The three crinoids on a patch of sand, swaying in the current (one of each colour). Every few
## seconds the ten-armed feather star furls into a ball and opens again, and the twenty-armed one
## swims up and settles. Give this to a Node3D at the root of an empty scene and play that scene.
## (`game` true shows the game models.)

@export var game := false

var crinoids: Array[Crinoid] = []
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
	plane.size = Vector2(3.0, 3.0)
	sand.mesh = plane
	var paint := StandardMaterial3D.new()
	paint.albedo_color = Color(0.62, 0.56, 0.42)
	sand.material_override = paint
	add_child(sand)
	for kind: Crinoid.Kind in [Crinoid.Kind.FEATHER_STAR, Crinoid.Kind.FEATHER_STAR_TWENTY, Crinoid.Kind.SEA_LILY]:
		var crinoid := Crinoid.new()
		crinoid.kind = kind
		crinoid.colour = [Crinoid.Colour.YELLOW, Crinoid.Colour.BLACK_WHITE, Crinoid.Colour.RED][kind]
		crinoid.game = game
		crinoid.position = Vector3((kind - 1) * 0.4, 0.0, 0.0)
		add_child(crinoid)
		crinoids.append(crinoid)
	var camera := Camera3D.new()
	camera.fov = 45.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 0.5, 1.3), Vector3(0.0, 0.15, 0.0))


func _process(delta: float) -> void:
	_time += delta
	var t := fposmod(_time, 10.0)
	# (the ten-armed one furls for three seconds in ten)
	crinoids[0].furl = move_toward(crinoids[0].furl, 1.0 if t > 4.0 and t < 7.0 else 0.0, delta * 0.8)
	# (the twenty-armed one swims up for three seconds in ten, then sinks back)
	var twenty := crinoids[1]
	twenty.swim = move_toward(twenty.swim, 1.0 if t < 3.0 else 0.0, delta * 2.0)
	twenty.position.y = move_toward(twenty.position.y, 0.15 if t < 3.0 else 0.0, delta * (0.06 if t < 3.0 else 0.03))
	for crinoid in crinoids:
		crinoid.step(Vector3.ZERO, delta)
