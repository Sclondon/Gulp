extends Node3D
## Angelfish over a grey floor: an emperor paddling slowly round in a circle (moved here,
## and told how fast with `step`), now and then nipping (`gape`); and inside the circle a
## queen hovering, side on (its `phase` set by hand, as a looping picture would), and a
## French angelfish that is a bare low mesh and a material from `mesh_of` and
## `new_material`, as a game that keeps its own MeshInstance3Ds would have it. Give this to
## a Node3D at the root of an empty scene and play it.

var swimmer: Angelfish
var holder: Angelfish
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
	plane.size = Vector2(6, 6)
	floor.mesh = plane
	floor.position.y = -0.4
	add_child(floor)
	# (`-- --game` on the command line: the game models, with cartoon eyes)
	var game := "--game" in OS.get_cmdline_user_args()
	swimmer = Angelfish.new()
	swimmer.game = game
	swimmer.cartoon_eyes = 1.0 if game else 0.0
	add_child(swimmer)
	holder = Angelfish.new()
	holder.type = Angelfish.Type.QUEEN
	holder.game = game
	add_child(holder)
	holder.position = Vector3(-0.25, 0.0, 0.0)
	# (side on to the camera, nose to the left)
	holder.rotation.y = PI * 0.5
	var mesh := MeshInstance3D.new()
	mesh.mesh = Angelfish.game_mesh(Angelfish.Type.FRENCH) if game else Angelfish.mesh_of(Angelfish.Type.FRENCH, true)
	bare = Angelfish.new_material(Angelfish.Type.FRENCH)
	mesh.material_override = bare
	mesh.extra_cull_margin = Angelfish.LENGTH * 0.3
	add_child(mesh)
	mesh.position = Vector3(0.25, 0.0, 0.0)
	mesh.rotation.y = PI * 0.5
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0, 0.4, 2.2), Vector3(0, 0, 0))


func _process(delta: float) -> void:
	_clock += delta
	# The swimmer goes round the others, nose first, and nips every few seconds.
	var angle := _clock * 0.35
	var was := swimmer.global_position
	swimmer.global_position = Vector3(cos(angle), 0.0, sin(angle)) * 1.0 + Vector3(0, -0.05, 0)
	var going := Vector3(-sin(angle), 0.0, cos(angle))
	swimmer.look_at(swimmer.global_position + going, Vector3.UP)
	swimmer.step((swimmer.global_position - was) / maxf(delta, 0.0001), delta)
	swimmer.gape = maxf(0.0, sin(_clock * 6.0)) if fmod(_clock, 4.0) < 1.05 else 0.0
	# The others' beats set by hand: each comes round again every beat exactly.
	holder.phase = fposmod(_clock / holder.beat, 1.0)
	bare.set_shader_parameter(&"phase", fposmod(_clock / 2.6, 1.0))
