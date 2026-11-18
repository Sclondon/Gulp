extends Node3D
## Two flying fish in blue water: one swimming round in a circle with its wings folded
## (moved here, and told how fast with `step`; `curl` bends it into the turn), and
## one holding its place in the middle that spreads and folds its wings over and over
## (its `phase` set by hand, as a looping picture would). Give this to a Node3D at
## the root of an empty scene and play that scene.

var swimmer: FlyingFish
var holder: FlyingFish
var _clock := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.05, 0.22, 0.42)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.55, 0.7, 0.85)
	env.environment.ambient_light_energy = 0.7
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(1, 4, 2), Vector3.ZERO)
	swimmer = FlyingFish.new()
	add_child(swimmer)
	holder = FlyingFish.new()
	holder.swim = 0.2
	add_child(holder)
	# (side on to the camera, nose to the left)
	holder.rotation.y = PI * 0.5
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0, 0.3, 1.2), Vector3(0, 0, 0))


func _process(delta: float) -> void:
	_clock += delta
	# The swimmer goes round the holder, nose first, bent into its turn.
	var angle := _clock * 0.9
	var was := swimmer.global_position
	swimmer.global_position = Vector3(cos(angle), 0.1, sin(angle)) * Vector3(0.45, 1.0, 0.45)
	var going := Vector3(-sin(angle), 0.0, cos(angle))
	swimmer.look_at(swimmer.global_position + going, Vector3.UP)
	swimmer.step((swimmer.global_position - was) / maxf(delta, 0.0001), delta)
	# (the circle is 0.45 m across its radius: the body, 0.21 m from gills to tail, lies
	# along 0.21 / 0.45 of a radian of it; the middle of the circle is on its +X side)
	swimmer.set_shader_parameter(&"curl", 0.21 / 0.45)
	# The holder's beat set by hand: it comes round again every `beat` seconds exactly,
	# and its wings open and shut once in two beats.
	holder.phase = fposmod(_clock / holder.beat, 1.0)
	holder.wings = 0.5 - 0.5 * cos(TAU * _clock / (holder.beat * 2.0))
