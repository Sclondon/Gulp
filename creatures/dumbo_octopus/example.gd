extends Node3D
## A dumbo octopus hovering in the dark of the deep, its web pulsing, its fins flapping, glowing faintly, with a dim
## light from above. Give this to a Node3D at the root of an empty scene and play that scene.

var octopus: DumboOctopus
var time := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.0, 0.008, 0.025)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.4, 0.5, 0.7)
	env.environment.ambient_light_energy = 0.35
	add_child(env)
	var sun := DirectionalLight3D.new()
	sun.light_energy = 0.6
	add_child(sun)
	sun.look_at_from_position(Vector3(1.0, 4.0, 2.0), Vector3.ZERO)
	octopus = DumboOctopus.new()
	add_child(octopus)
	var camera := Camera3D.new()
	camera.fov = 40.0
	camera.near = 0.01
	add_child(camera)
	camera.look_at_from_position(Vector3(0.35, 0.12, -0.75), Vector3.ZERO)


func _process(delta: float) -> void:
	time += delta
	octopus.step(Vector3.ZERO, delta)
	# (it drifts up a little on each pulse and turns slowly)
	octopus.position.y = 0.02 * sin(TAU * octopus.phase - 0.8)
	octopus.rotation.y = 0.4 * sin(time * 0.3)
	octopus.curl = -0.25 * cos(time * 0.3)
