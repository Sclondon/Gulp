extends Node3D
## Two cutthroat trout over a grey floor: a greenback swimming slowly round in a
## circle (moved here, and told how fast with `step`), and a golden one holding its
## place in the middle (its `phase` set by hand, as a looping picture would). Give
## this to a Node3D at the root of an empty scene and play that scene.

var swimmer: CutthroatTrout
var holder: CutthroatTrout
var _clock := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.16, 0.3, 0.36)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.6, 0.7, 0.75)
	env.environment.ambient_light_energy = 0.6
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(1, 4, 2), Vector3.ZERO)
	var floor := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(6, 6)
	floor.mesh = plane
	floor.position.y = -0.3
	add_child(floor)
	swimmer = CutthroatTrout.new()
	add_child(swimmer)
	holder = CutthroatTrout.new()
	holder.look = CutthroatTrout.Look.GOLDEN
	holder.swim = 0.35
	add_child(holder)
	# (side on to the camera, nose to the left)
	holder.rotation.y = PI * 0.5
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0, 0.35, 1.5), Vector3(0, 0, 0))


func _process(delta: float) -> void:
	_clock += delta
	# The swimmer goes round the holder, nose first.
	var angle := _clock * 0.5
	var was := swimmer.global_position
	swimmer.global_position = Vector3(cos(angle), 0.12, sin(angle)) * Vector3(0.6, 1.0, 0.6)
	var going := Vector3(-sin(angle), 0.0, cos(angle))
	swimmer.look_at(swimmer.global_position + going, Vector3.UP)
	swimmer.step((swimmer.global_position - was) / maxf(delta, 0.0001), delta)
	# The holder's beat set by hand: it comes round again every `beat` seconds exactly.
	holder.phase = fposmod(_clock / holder.beat, 1.0)
