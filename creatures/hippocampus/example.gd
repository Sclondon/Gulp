extends Node3D
## A hippocampus beside a kelpie, swimming on the spot, seen from their sides; each opens its mouth
## now and then. Give this to a Node3D at the root of an empty scene and play that scene.

var hippocampus: Hippocampus
var kelpie: Hippocampus
var _time := 0.0


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
	hippocampus = Hippocampus.new()
	hippocampus.game = true
	add_child(hippocampus)
	hippocampus.position = Vector3(0.0, 1.3, 0.0)
	hippocampus.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	kelpie = Hippocampus.new()
	kelpie.game = true
	kelpie.kelpie = true
	kelpie.phase = 0.4
	add_child(kelpie)
	kelpie.position = Vector3(0.0, -1.3, 0.0)
	kelpie.rotation_degrees = Vector3(0.0, 90.0, 0.0)
	var camera := Camera3D.new()
	camera.fov = 50.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.0, 0.3, 7.0), Vector3.ZERO)


func _process(delta: float) -> void:
	_time += delta
	hippocampus.step(Vector3.ZERO, delta)
	kelpie.step(Vector3.ZERO, delta)
	hippocampus.gape = clampf(sin(_time * 1.1) * 3.0 - 2.0, 0.0, 1.0)
	kelpie.gape = clampf(sin(_time * 0.9 + 2.0) * 3.0 - 2.0, 0.0, 1.0)
