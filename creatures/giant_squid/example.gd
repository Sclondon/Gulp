extends Node3D
## A giant squid jetting slowly round in a ring in dark blue water, mantle first, its arms and
## tentacles trailing. Play creatures/giant_squid/example.tscn.

var squid: GiantSquid
var _clock := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.02, 0.06, 0.2)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.45, 0.55, 0.7)
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(2, 10, 4), Vector3.ZERO)
	squid = GiantSquid.new()
	add_child(squid)
	var camera := Camera3D.new()
	add_child(camera)
	camera.look_at_from_position(Vector3(0, 5, 20), Vector3(0, 0, 0))


func _process(delta: float) -> void:
	_clock += delta
	# (it goes fastest as it squeezes: a jet)
	var turn := _clock * 0.12 + 0.05 * (0.5 - squid.fullness)
	var at := Vector3(cos(turn) * 6.0, 0.5 * sin(_clock * 0.3), sin(turn) * 6.0)
	var ahead := Vector3(-sin(turn), 0.0, cos(turn))
	# (its mantle leads: its own -Z points the way it goes)
	squid.global_transform = Transform3D(Basis.looking_at(ahead, Vector3.UP), at)
	squid.step(Vector3.ZERO, delta)
