extends Node3D
## The three sea stars on a patch of sand, creeping; every few seconds the classic one curls its arms
## up and lays them down again. Give this to a Node3D at the root of an empty scene and play that
## scene. (`game` true shows the game models.)

@export var game := false

var stars: Array[Starfish] = []
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
	var places := [Vector3(-0.45, 0.0, 0.1), Vector3(0.25, 0.0, -0.2), Vector3(0.3, 0.0, 0.35)]
	for kind: Starfish.Kind in [Starfish.Kind.CLASSIC, Starfish.Kind.SUNFLOWER, Starfish.Kind.BRITTLE]:
		var star := Starfish.new()
		star.kind = kind
		star.game = game
		star.position = places[kind]
		star.rotation.y = kind * 0.7
		add_child(star)
		stars.append(star)
	var camera := Camera3D.new()
	camera.fov = 45.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 1.0, 1.1), Vector3(0.0, 0.0, 0.05))


func _process(delta: float) -> void:
	_time += delta
	for star in stars:
		star.step(Vector3.ZERO, delta)
	# (the classic star curls up for two seconds in every eight)
	var t := fposmod(_time, 8.0)
	stars[0].curl_up = move_toward(stars[0].curl_up, 1.0 if t > 5.0 and t < 7.0 else 0.0, delta * 1.2)
