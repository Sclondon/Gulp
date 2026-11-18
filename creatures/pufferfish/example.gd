extends Node3D
## A pufferfish over a grey floor, pottering slowly round in a circle (moved here, and told how
## fast with `step`): every few seconds it takes fright and blows itself up into a spiny ball,
## then lets itself down again, and now and then it bites (`gape`). In the middle a second one,
## a bare mesh and material (`game_mesh` or `mesh_of(true)` and `new_material`, as a game that
## keeps its own MeshInstance3Ds would have them), side on, hovering, its beat set by hand.
## Give this to a Node3D at the root of an empty scene and play it (`-- --game`: the game models,
## with cartoon eyes).

var swimmer: Pufferfish
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
	plane.size = Vector2(5, 5)
	floor.mesh = plane
	floor.position.y = -0.3
	add_child(floor)
	var game := "--game" in OS.get_cmdline_user_args()
	swimmer = Pufferfish.new()
	swimmer.game = game
	swimmer.cartoon_eyes = 1.0 if game else 0.0
	add_child(swimmer)
	var mesh := MeshInstance3D.new()
	mesh.mesh = Pufferfish.game_mesh() if game else Pufferfish.mesh_of(true)
	bare = Pufferfish.new_material()
	mesh.material_override = bare
	mesh.extra_cull_margin = Pufferfish.PUFFED_REACH * 0.6
	add_child(mesh)
	# (side on to the camera, nose to the left)
	mesh.rotation.y = PI * 0.5
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0, 0.45, 2.0), Vector3(0, 0, 0))


func _process(delta: float) -> void:
	_clock += delta
	var angle := _clock * 0.25
	var was := swimmer.global_position
	swimmer.global_position = Vector3(cos(angle), 0.0, sin(angle)) * 0.8
	var going := Vector3(-sin(angle), 0.0, cos(angle))
	swimmer.look_at(swimmer.global_position + going, Vector3.UP)
	swimmer.step((swimmer.global_position - was) / maxf(delta, 0.0001), delta)
	# Every eight seconds it blows up for three, easing in and out over half a second.
	var t := fmod(_clock, 8.0)
	swimmer.puff = smoothstep(4.0, 4.5, t) * (1.0 - smoothstep(7.0, 7.5, t))
	swimmer.gape = maxf(0.0, sin(_clock * 5.0)) if fmod(_clock, 5.0) < 0.65 else 0.0
	bare.set_shader_parameter(&"phase", fposmod(_clock / 2.0, 1.0))
