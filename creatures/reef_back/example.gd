extends Node3D
## A reef-back walking a slow circle on a sea floor, seen from the side; now and then it stops, opens its jaw and
## its throat glows brighter. Give this to a Node3D at the root of an empty scene and play that scene.

var it: ReefBack
var _time := 0.0
var _angle := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.03, 0.14, 0.17)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.5, 0.68, 0.7)
	env.environment.ambient_light_energy = 0.7
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(-2.0, 6.0, 3.0), Vector3.ZERO)
	var ground := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(300.0, 300.0)
	ground.mesh = plane
	add_child(ground)
	it = ReefBack.new()
	it.game = true
	it.cartoon_eyes = 1.0
	add_child(it)
	var camera := Camera3D.new()
	camera.fov = 50.0
	camera.far = 600.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 22.0, 95.0), Vector3(0.0, 6.0, 0.0))


func _process(delta: float) -> void:
	_time += delta
	# (it walks for twenty seconds, then stands for eight)
	var walking := fposmod(_time, 28.0) < 20.0
	var speed := 0.7 if walking else 0.0
	_angle += speed * delta / 40.0
	var at := Vector3(sin(_angle), 0.0, cos(_angle)) * 40.0
	var heading := Vector3(cos(_angle), 0.0, -sin(_angle))
	var velocity := heading * speed
	it.position = at
	it.look_at(at + heading, Vector3.UP)
	it.step(velocity, delta)
	it.curl = -0.15 if walking else 0.0
	it.gape = 0.0 if walking else clampf(sin((fposmod(_time, 28.0) - 20.0) * 0.8) * 1.5, 0.0, 1.0)
	it.glow = 1.0 + it.gape
	it.blink = 1.0 if fposmod(_time, 4.3) < 0.15 else 0.0
