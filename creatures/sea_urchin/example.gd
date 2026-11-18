extends Node3D
## The three sea urchins on a patch of sand, their spines swaying; a pebble circles them and each
## leans its spines towards it as it comes near. Give this to a Node3D at the root of an empty scene
## and play that scene. (`game` true shows the game models.)

@export var game := false

var urchins: Array[SeaUrchin] = []
var pebble: MeshInstance3D
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
	plane.size = Vector2(2.0, 2.0)
	sand.mesh = plane
	var paint := StandardMaterial3D.new()
	paint.albedo_color = Color(0.62, 0.56, 0.42)
	sand.material_override = paint
	add_child(sand)
	for kind: SeaUrchin.Kind in [SeaUrchin.Kind.LONG_SPINED, SeaUrchin.Kind.PURPLE, SeaUrchin.Kind.SLATE_PENCIL]:
		var urchin := SeaUrchin.new()
		urchin.kind = kind
		urchin.game = game
		urchin.position = Vector3((kind - 1) * 0.32, 0.0, 0.0)
		add_child(urchin)
		urchins.append(urchin)
	pebble = MeshInstance3D.new()
	var ball := SphereMesh.new()
	ball.radius = 0.02
	ball.height = 0.04
	pebble.mesh = ball
	add_child(pebble)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 0.45, 0.9), Vector3(0.0, 0.04, 0.0))


func _process(delta: float) -> void:
	_time += delta
	pebble.position = Vector3(sin(_time * 0.6) * 0.5, 0.12, cos(_time * 0.6) * 0.25)
	for urchin in urchins:
		urchin.step(Vector3.ZERO, delta)
		var to := pebble.global_position - urchin.global_position - Vector3(0.0, 0.03, 0.0)
		# (alarmed as the pebble comes within 0.3 m; the threat is in the urchin's own space)
		var alarm := clampf(1.0 - to.length() / 0.3, 0.0, 1.0)
		urchin.threat = urchin.global_basis.inverse() * to.normalized() * alarm
