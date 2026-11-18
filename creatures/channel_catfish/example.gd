extends Node3D
## A channel catfish swimming on the spot in green-blue water, seen from its side and a little
## in front: water runs past it, so its barbels trail. Give this to a Node3D at the root of an
## empty scene and play that scene.

var catfish: ChannelCatfish


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.05, 0.2, 0.24)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.6, 0.75, 0.8)
	env.environment.ambient_light_energy = 0.7
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(0.6, 1.6, 1.0), Vector3.ZERO)
	catfish = ChannelCatfish.new()
	add_child(catfish)
	# (its nose is at -Z: turned a quarter, it faces the left of the picture)
	catfish.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	catfish.lay_ropes()
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(-0.35, 0.12, 0.95), Vector3(-0.03, 0.0, 0.0))


func _process(delta: float) -> void:
	# (held where it is, swimming at 0.25 m/s against water that runs past it)
	catfish.step(-catfish.global_basis.z.normalized() * 0.25, delta)
