extends Node3D
## A mermaid swimming on the spot in green-blue water, seen from her side. Give this to a Node3D at
## the root of an empty scene and play that scene.

var mermaid: Mermaid


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.04, 0.18, 0.22)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.55, 0.72, 0.78)
	env.environment.ambient_light_energy = 0.7
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(1.5, 4.0, 2.5), Vector3.ZERO)
	mermaid = Mermaid.new()
	mermaid.game = true
	add_child(mermaid)
	# (her nose is at -Z: turned a quarter, she faces the left of the picture)
	mermaid.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.3, 0.5, 3.4), Vector3.ZERO)


func _process(delta: float) -> void:
	mermaid.step(Vector3.ZERO, delta)
