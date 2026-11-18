extends Node3D
## Butterflyfish over a grey floor: a threadfin paddling slowly round in a circle (moved
## here, and told how fast with `step`), now and then pecking (`gape`); and inside the
## circle the other four types in a row, side on, hovering (their `phase` set by hand, as
## a looping picture would; the last two are bare low meshes and materials from `mesh_of`
## and `new_material`, as a game that keeps its own MeshInstance3Ds would have them). Give
## this to a Node3D at the root of an empty scene and play it.

var swimmer: Butterflyfish
var holders: Array[Butterflyfish] = []
var bare: Array[ShaderMaterial] = []
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
	plane.size = Vector2(4, 4)
	floor.mesh = plane
	floor.position.y = -0.25
	add_child(floor)
	# (`-- --game` on the command line: the game models, with cartoon eyes)
	var game := "--game" in OS.get_cmdline_user_args()
	swimmer = Butterflyfish.new()
	swimmer.game = game
	swimmer.cartoon_eyes = 1.0 if game else 0.0
	add_child(swimmer)
	var row := [
		Butterflyfish.Type.RACCOON, Butterflyfish.Type.COPPERBAND, Butterflyfish.Type.LONGNOSE,
		Butterflyfish.Type.BANNERFISH,
	]
	for i in row.size():
		var at := Vector3((i - 1.5) * 0.24, 0.0, 0.0)
		if i < 2:
			var holder := Butterflyfish.new()
			holder.type = row[i]
			holder.game = game
			add_child(holder)
			holder.position = at
			# (side on to the camera, nose to the left)
			holder.rotation.y = PI * 0.5
			holders.append(holder)
		else:
			var mesh := MeshInstance3D.new()
			mesh.mesh = Butterflyfish.game_mesh(row[i]) if game else Butterflyfish.mesh_of(row[i], true)
			var material := Butterflyfish.new_material(row[i])
			mesh.material_override = material
			mesh.extra_cull_margin = Butterflyfish.LENGTH * 0.3
			add_child(mesh)
			mesh.position = at
			mesh.rotation.y = PI * 0.5
			bare.append(material)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0, 0.25, 1.25), Vector3(0, 0, 0))


func _process(delta: float) -> void:
	_clock += delta
	# The swimmer goes round the others, nose first, and pecks every few seconds.
	var angle := _clock * 0.35
	var was := swimmer.global_position
	swimmer.global_position = Vector3(cos(angle), 0.0, sin(angle)) * 0.6 + Vector3(0, -0.05, 0)
	var going := Vector3(-sin(angle), 0.0, cos(angle))
	swimmer.look_at(swimmer.global_position + going, Vector3.UP)
	swimmer.step((swimmer.global_position - was) / maxf(delta, 0.0001), delta)
	swimmer.gape = maxf(0.0, sin(_clock * 6.0)) if fmod(_clock, 4.0) < 1.05 else 0.0
	# The holders' beats set by hand: each comes round again every `beat` seconds exactly.
	for holder in holders:
		holder.phase = fposmod(_clock / holder.beat, 1.0)
	for material in bare:
		material.set_shader_parameter(&"phase", fposmod(_clock / 2.0, 1.0))
