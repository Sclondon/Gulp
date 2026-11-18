extends Node3D
## A remora swimming on the spot in blue water, seen from its side, then riding for a while under a
## grey slab (a stand-in for a host's belly), then letting go. Give this to a Node3D at the root of
## an empty scene and play that scene.

var remora: Remora
var _time := 0.0
var _slab: MeshInstance3D


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
	_slab = MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = Vector3(0.6, 0.06, 1.2)
	_slab.mesh = box
	_slab.position = Vector3(0.0, 0.2, 0.0)
	add_child(_slab)
	remora = Remora.new()
	remora.cartoon_eyes = 1.0
	add_child(remora)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(1.3, 0.05, 0.0), Vector3(0.0, 0.05, 0.0))


func _process(delta: float) -> void:
	_time += delta
	remora.step(Vector3.ZERO, delta)
	# (eight seconds swimming below the slab, eight riding on it)
	var on := fposmod(_time, 16.0) > 8.0
	remora.riding = move_toward(remora.riding, 1.0 if on else 0.0, delta * 2.0)
	var swimming := Transform3D(Basis.IDENTITY, Vector3(0.0, -0.05, 0.0))
	var riding := Remora.riding_transform(Vector3(0.0, 0.17, 0.0), Vector3.DOWN, Vector3.FORWARD)
	remora.transform = swimming.interpolate_with(riding, remora.riding)
	# (a snap of its jaws every three seconds while it swims)
	remora.gape = clampf(1.0 - absf(fposmod(_time, 3.0) - 1.5) * 4.0, 0.0, 1.0) * (1.0 - remora.riding)
