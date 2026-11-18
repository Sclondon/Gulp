extends Node3D
## A pyrosome drifting in the dark of the deep, closed end first, swaying like a windsock, waves of light running
## along it, turning slowly. Give this to a Node3D at the root of an empty scene and play that scene.

var colony: Pyrosome
var time := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.0, 0.006, 0.02)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.4, 0.5, 0.7)
	env.environment.ambient_light_energy = 0.25
	add_child(env)
	var sun := DirectionalLight3D.new()
	sun.light_energy = 0.4
	add_child(sun)
	sun.look_at_from_position(Vector3(1.0, 4.0, 2.0), Vector3.ZERO)
	colony = Pyrosome.new()
	add_child(colony)
	var camera := Camera3D.new()
	camera.fov = 45.0
	add_child(camera)
	camera.look_at_from_position(Vector3(3.0, 0.8, 1.2), Vector3.ZERO)


func _process(delta: float) -> void:
	time += delta
	colony.step(Vector3.ZERO, delta)
	colony.rotation.y = 0.3 * sin(time * 0.1)
	colony.curl = 0.25 * sin(time * 0.17)
