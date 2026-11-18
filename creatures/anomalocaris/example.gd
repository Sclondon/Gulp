extends Node3D
## An anomalocaris swimming on the spot in blue water, seen from a little above and to the side;
## every few seconds it strikes with its arms. Give this to a Node3D at the root of an empty scene
## and play that scene.

var anomalocaris: Anomalocaris
var time := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.03, 0.16, 0.34)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.55, 0.7, 0.9)
	env.environment.ambient_light_energy = 0.7
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(1.5, 4.0, 2.5), Vector3.ZERO)
	anomalocaris = Anomalocaris.new()
	anomalocaris.game = true
	anomalocaris.cartoon_eyes = 1.0
	add_child(anomalocaris)
	# (its -Z is its front: turned a quarter, it faces the left of the picture)
	anomalocaris.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.3, 0.7, 1.4), Vector3(0.0, -0.02, 0.0))


func _process(delta: float) -> void:
	time += delta
	anomalocaris.step(Vector3.ZERO, delta)
	# (a strike every five seconds: out in a fifth of a second, back in half a second)
	var t := fmod(time, 5.0) - 4.0
	anomalocaris.grasp = clampf(t / 0.2, 0.0, 1.0) if t < 0.2 else clampf(1.0 - (t - 0.2) / 0.5, 0.0, 1.0)
	anomalocaris.blink = 1.0 if fmod(time, 3.3) < 0.12 else 0.0
