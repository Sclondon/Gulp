extends Node3D
## A submarine cruising round a slow circle in dark blue water, its lights on, its arms reaching out
## and gripping now and then, the camera following. Give this to a Node3D at the root of an empty
## scene and play that scene.

var sub: Submarine
var _time := 0.0
var _camera: Camera3D


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.02, 0.08, 0.14)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.45, 0.6, 0.75)
	env.environment.ambient_light_energy = 0.5
	env.environment.fog_enabled = true
	env.environment.fog_light_color = Color(0.03, 0.12, 0.2)
	env.environment.fog_density = 0.02
	add_child(env)
	var sun := DirectionalLight3D.new()
	sun.light_energy = 0.6
	add_child(sun)
	sun.look_at_from_position(Vector3(1.5, 6.0, 2.5), Vector3.ZERO)
	sub = Submarine.new()
	add_child(sub)
	_camera = Camera3D.new()
	_camera.fov = 50.0
	add_child(_camera)


func _process(delta: float) -> void:
	_time += delta
	# (round a circle 14 m across, at 1.5 m a second: it turns left all the way)
	var angle := _time * 1.5 / 7.0
	sub.position = Vector3(cos(angle), 0.0, -sin(angle)) * 7.0 + Vector3.UP * sin(_time * 0.3) * 0.8
	sub.basis = Basis(Vector3.UP, angle)
	sub.step(Vector3.ZERO, delta)
	# (the arms reach out and grip every eight seconds)
	var t := fposmod(_time, 8.0)
	sub.reach = clampf(minf(t - 2.0, 6.0 - t), 0.0, 1.0)
	sub.grip = clampf(minf(t - 3.0, 5.5 - t) * 2.0, 0.0, 1.0)
	sub.periscope_turn = sin(_time * 0.4) * 0.3
	_camera.look_at_from_position(sub.position + sub.basis * Vector3(-9.0, 3.0, -6.0), sub.position, Vector3.UP)
