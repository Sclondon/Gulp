extends Node3D
## Carp over a grey floor: a common carp swimming slowly round in a circle (moved here, and
## told how fast with `step`), opening its mouth now and then as it goes; inside the circle a
## row of koi holding their places, one of each type, and two more kohaku with other
## `pattern_seed`s (the last two bare meshes and materials from `mesh_of` and `new_material`,
## as a game that keeps its own MeshInstance3Ds would have them). Give this to a Node3D at the
## root of an empty scene and play it.

var swimmer: Carp
var holders: Array[Carp] = []
var bare: Array[ShaderMaterial] = []
var _clock := 0.0


func _ready() -> void:
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.16, 0.3, 0.3)
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
	floor.position.y = -0.6
	add_child(floor)
	swimmer = Carp.new()
	add_child(swimmer)
	var row := [Carp.Type.KOHAKU, Carp.Type.SANKE, Carp.Type.SHOWA, Carp.Type.YAMABUKI_OGON, Carp.Type.PLATINUM_OGON, Carp.Type.KOHAKU, Carp.Type.KOHAKU]
	for i in row.size():
		var at := Vector3((i % 4 - 1.5) * 0.8, 0.25 - 0.4 * (i / 4), 0.0)
		if i < 5:
			var holder := Carp.new()
			holder.type = row[i]
			holder.sway = 0.3
			add_child(holder)
			holder.position = at
			# (side on to the camera, nose to the left)
			holder.rotation.y = PI * 0.5
			holders.append(holder)
		else:
			var mesh := MeshInstance3D.new()
			mesh.mesh = Carp.mesh_of(true)
			var material := Carp.new_material(row[i], i)
			material.set_shader_parameter(&"sway", 0.3)
			mesh.material_override = material
			mesh.extra_cull_margin = Carp.LENGTH * 0.25
			add_child(mesh)
			mesh.position = at
			mesh.rotation.y = PI * 0.5
			bare.append(material)
	var camera := Camera3D.new()
	camera.fov = 40.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0, 0.6, 3.8), Vector3(0, 0, 0))


func _process(delta: float) -> void:
	_clock += delta
	# The swimmer goes round the others, nose first, and opens its mouth every few seconds.
	var angle := _clock * 0.4
	var was := swimmer.global_position
	swimmer.global_position = Vector3(cos(angle), 0.0, sin(angle)) * 1.7 + Vector3(0, -0.25, 0)
	var going := Vector3(-sin(angle), 0.0, cos(angle))
	swimmer.look_at(swimmer.global_position + going, Vector3.UP)
	swimmer.step((swimmer.global_position - was) / maxf(delta, 0.0001), delta)
	swimmer.gape = clampf(sin(_clock * 1.3) * 2.0 - 1.0, 0.0, 1.0)
	# The holders' beats set by hand: each comes round again every `beat` seconds exactly.
	for holder in holders:
		holder.phase = fposmod(_clock / holder.beat, 1.0)
	for material in bare:
		material.set_shader_parameter(&"phase", fposmod(_clock / 2.4, 1.0))
