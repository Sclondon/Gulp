extends Node3D
## Three comb jellies drifting in the dark of the deep, their comb rows running with rainbow light, one in front
## turning slowly. Give this to a Node3D at the root of an empty scene and play that scene.

var jellies: Array[CombJelly] = []
var time := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.0, 0.01, 0.03)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.4, 0.5, 0.7)
	env.environment.ambient_light_energy = 0.3
	add_child(env)
	var sun := DirectionalLight3D.new()
	sun.light_energy = 0.5
	add_child(sun)
	sun.look_at_from_position(Vector3(1.0, 4.0, 2.0), Vector3.ZERO)
	for i in 3:
		var jelly := CombJelly.new()
		add_child(jelly)
		jelly.position = [Vector3.ZERO, Vector3(-0.16, 0.06, -0.25), Vector3(0.15, -0.05, -0.3)][i]
		jelly.phase = i * 0.37
		jellies.append(jelly)
	var camera := Camera3D.new()
	camera.fov = 40.0
	camera.near = 0.01
	add_child(camera)
	camera.look_at_from_position(Vector3(0.05, 0.05, 0.3), Vector3(0.0, 0.0, -0.1))


func _process(delta: float) -> void:
	time += delta
	for jelly in jellies:
		jelly.step(Vector3.ZERO, delta)
	jellies[0].rotation.y = time * 0.3
	jellies[0].curl = 0.3 * sin(time * 0.5)
