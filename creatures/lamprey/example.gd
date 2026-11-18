extends Node3D
## Sea lampreys over a grey floor: one swimming slowly round in a circle (moved here, and told
## how fast with `step`), opening its sucker now and then as it goes; one holding its place side
## on with its sucker open (its `phase` set by hand, as a looping picture would); and a bare mesh
## and material from `mesh_of` and `new_material`, as a game that keeps its own
## MeshInstance3Ds would have it. Give this to a Node3D at the root of an empty scene and play it.

var swimmer: Lamprey
var holder: Lamprey
var bare: ShaderMaterial
var _clock := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.16, 0.26, 0.28)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.65, 0.72, 0.7)
	env.environment.ambient_light_energy = 0.6
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(1, 4, 2), Vector3.ZERO)
	var floor := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(10, 10)
	floor.mesh = plane
	floor.position.y = -0.3
	add_child(floor)
	swimmer = Lamprey.new()
	add_child(swimmer)
	holder = Lamprey.new()
	holder.gape = 1.0
	holder.sway = 0.4
	add_child(holder)
	holder.position = Vector3(0.0, 0.1, 0.0)
	# (side on to the camera, nose to the left)
	holder.rotation.y = PI * 0.5
	var mesh := MeshInstance3D.new()
	mesh.mesh = Lamprey.mesh_of(true)
	bare = Lamprey.new_material()
	bare.set_shader_parameter(&"sway", 0.6)
	mesh.material_override = bare
	mesh.extra_cull_margin = Lamprey.LENGTH * 0.1
	add_child(mesh)
	mesh.position = Vector3(0.0, -0.15, 0.0)
	mesh.rotation.y = PI * 0.5
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0, 0.5, 2.4), Vector3(0, 0, 0))


func _process(delta: float) -> void:
	_clock += delta
	# The swimmer goes round the others, nose first, and opens its sucker every few seconds.
	var angle := _clock * 0.5
	var was := swimmer.global_position
	swimmer.global_position = Vector3(cos(angle), 0.0, sin(angle)) * 1.0 + Vector3(0, -0.05, 0)
	var going := Vector3(-sin(angle), 0.0, cos(angle))
	swimmer.look_at(swimmer.global_position + going, Vector3.UP)
	swimmer.step((swimmer.global_position - was) / maxf(delta, 0.0001), delta)
	swimmer.gape = clampf(sin(_clock * 0.9) * 2.0 - 1.0, 0.0, 1.0)
	# The holder's beat set by hand: it comes round again every `beat` seconds exactly.
	holder.phase = fposmod(_clock / holder.beat, 1.0)
	bare.set_shader_parameter(&"phase", fposmod(_clock / 1.6, 1.0))
