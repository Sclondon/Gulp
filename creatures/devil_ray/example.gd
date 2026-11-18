extends Node3D
## A Munk's devil ray flying on the spot in blue water, seen from ahead and a little above;
## every few beats it unrolls its cephalic fins and opens its mouth, then banks.
## Give this to a Node3D at the root of an empty scene and play that scene.

var ray: DevilRay
var _time := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.03, 0.16, 0.34)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.55, 0.7, 0.9)
	env.environment.ambient_light_energy = 0.8
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(1.5, 4.0, -2.5), Vector3.ZERO)
	ray = DevilRay.new()
	add_child(ray)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	# (its snout is at -Z: the camera is ahead of it, to one side and above)
	camera.look_at_from_position(Vector3(-0.8, 0.45, -1.25), Vector3(0.0, 0.0, 0.08))


func _process(delta: float) -> void:
	_time += delta
	ray.step(Vector3.ZERO, delta)
	var feeding := smoothstep(0.3, 0.45, fposmod(_time / 16.0, 1.0)) * (1.0 - smoothstep(0.7, 0.85, fposmod(_time / 16.0, 1.0)))
	ray.scoops = feeding
	ray.gape = feeding
	ray.curl = 0.6 * sin(_time * 0.4) * (1.0 - feeding)
