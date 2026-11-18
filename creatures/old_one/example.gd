extends Node3D
## The old one asleep in dark water, seen from ahead and above; every twelve seconds it stirs and settles again.
## Give this to a Node3D at the root of an empty scene and play that scene.

var it: OldOne
var _time := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.02, 0.07, 0.09)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.4, 0.6, 0.65)
	env.environment.ambient_light_energy = 0.6
	env.environment.fog_enabled = true
	env.environment.fog_light_color = Color(0.03, 0.1, 0.12)
	env.environment.fog_density = 0.008
	add_child(env)
	var sun := DirectionalLight3D.new()
	sun.light_energy = 0.7
	add_child(sun)
	sun.look_at_from_position(Vector3(-2.0, 6.0, -3.0), Vector3.ZERO)
	it = OldOne.new()
	it.game = true
	it.cartoon_eyes = 1.0
	add_child(it)
	var camera := Camera3D.new()
	camera.fov = 50.0
	camera.far = 400.0
	add_child(camera)
	camera.look_at_from_position(Vector3(-22.0, 16.0, -52.0), Vector3(0.0, 6.0, 0.0))


func _process(delta: float) -> void:
	_time += delta
	it.step(Vector3.ZERO, delta)
	it.wake = clampf(sin(_time * TAU / 24.0) * 1.6 - 0.4, 0.0, 1.0)
	it.eye_look = Vector2(sin(_time * 0.4), 0.3 * sin(_time * 0.7))
