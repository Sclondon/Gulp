extends Node3D
## Seahorses over a grey floor: a common one drifting slowly round in a circle, upright, facing
## the way it goes (moved here, and told how fast with `step`), its eyes swivelling each on its
## own and now and then snapping at something (`gape`); and in the middle the other two side on,
## hanging still, their tails curling and letting go (`grip`): the spiny one a node, the pygmy a
## bare mesh and material, as a game that keeps its own MeshInstance3Ds would have it. Give this
## to a Node3D at the root of an empty scene and play it (`-- --game`: the game models, with
## cartoon eyes).

var swimmer: Seahorse
var holder: Seahorse
var bare: ShaderMaterial
var _clock := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.08, 0.3, 0.45)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.7, 0.8, 0.85)
	env.environment.ambient_light_energy = 0.7
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(1, 4, 2), Vector3.ZERO)
	var floor := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(3, 3)
	floor.mesh = plane
	floor.position.y = -0.12
	add_child(floor)
	var game := "--game" in OS.get_cmdline_user_args()
	swimmer = Seahorse.new()
	swimmer.game = game
	swimmer.cartoon_eyes = 1.0 if game else 0.0
	add_child(swimmer)
	holder = Seahorse.new()
	holder.type = Seahorse.Type.SPINY
	holder.game = game
	holder.cartoon_eyes = 1.0 if game else 0.0
	add_child(holder)
	holder.position = Vector3(-0.08, 0.0, 0.0)
	# (side on to the camera, snout to the left)
	holder.rotation.y = -PI * 0.5
	var mesh := MeshInstance3D.new()
	mesh.mesh = Seahorse.game_mesh(Seahorse.Type.PYGMY) if game else Seahorse.mesh_of(Seahorse.Type.PYGMY, true)
	bare = Seahorse.new_material(Seahorse.Type.PYGMY)
	mesh.material_override = bare
	mesh.extra_cull_margin = Seahorse.LENGTH * 0.3
	add_child(mesh)
	mesh.position = Vector3(0.08, 0.0, 0.0)
	mesh.rotation.y = -PI * 0.5
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0, 0.12, 0.75), Vector3(0, 0, 0))


func _process(delta: float) -> void:
	_clock += delta
	var angle := _clock * 0.2
	var was := swimmer.global_position
	swimmer.global_position = Vector3(cos(angle), 0.0, sin(angle)) * 0.3
	var going := Vector3(-sin(angle), 0.0, cos(angle))
	# (upright, facing the way it goes: its snout is along its -Z)
	swimmer.look_at(swimmer.global_position + going, Vector3.UP)
	swimmer.step((swimmer.global_position - was) / maxf(delta, 0.0001), delta)
	swimmer.eye_look = Vector2(sin(_clock * 0.9), 0.5 * sin(_clock * 1.3))
	swimmer.eye_look_other = Vector2(sin(_clock * 0.7 + 2.0), 0.5 * cos(_clock * 1.1))
	swimmer.gape = maxf(0.0, sin(_clock * 8.0)) if fmod(_clock, 4.0) < 0.4 else 0.0
	swimmer.blink = 1.0 if fmod(_clock, 3.3) < 0.12 else 0.0
	holder.step(Vector3.ZERO, delta)
	holder.grip = 0.5 + 0.5 * sin(_clock * 0.8)
	bare.set_shader_parameter(&"phase", fposmod(_clock / 2.0, 1.0))
	bare.set_shader_parameter(&"grip", 0.5 + 0.5 * sin(_clock * 0.8 + 1.5))
