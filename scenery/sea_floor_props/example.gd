extends Node3D
## A little reef laid out from SeaFloorProps: a rocky Californian reef on the left (an arch, a
## ledge, boulders, with fans, anemones, urchins and sea stars on them) and a coral reef on the
## right (bommies with corals, sponges and a giant clam). Give this to a Node3D at the root of an
## empty scene and play that scene. Each kind of piece is drawn by one MultiMesh.
##
## It moves the global shader uniform `water_clock` itself (and adds it if the project has not
## got it: a game should declare it in Project Settings, Shader Globals).

const ROCKY := [
	["rock_arch", Vector3(-9.0, 0.0, -3.0), 0.3, 1.0],
	["rock_ledge", Vector3(-4.5, 0.0, 2.5), -0.5, 1.0],
	["rock_stack", Vector3(-12.5, 0.0, 3.0), 1.2, 1.0],
	["rock_boulder", Vector3(-7.5, 0.0, 4.5), 2.0, 1.0],
	["rock_split", Vector3(-1.8, 0.0, -1.5), 0.7, 1.0],
	["rock_slab", Vector3(-13.0, 0.0, -1.0), 2.4, 1.0],
	["rock_boulder_small", Vector3(-6.0, 0.0, 5.8), 0.4, 1.0],
	["rock_boulder_small", Vector3(-2.6, 0.0, 4.6), 2.9, 1.4],
	["rock_pinnacle", Vector3(-15.0, 0.0, -6.0), 0.9, 1.0],
]
const CORAL := [
	["bommie_tower", Vector3(8.0, 0.0, -3.0), 0.4, 1.0],
	["bommie_mound", Vector3(4.0, 0.0, 1.5), 1.9, 1.0],
	["bommie_small", Vector3(10.5, 0.0, 3.0), 3.3, 1.0],
	["bommie_small", Vector3(13.5, 0.0, -0.5), 5.0, 1.3],
]
## What grows where: name, how many, on which side (-1 rocky, 1 coral), how big (least, most).
const GROWTH := [
	["sea_fan_red", 5, -1, 0.8, 1.2], ["sea_fan_gold", 7, -1, 0.9, 1.3], ["hydrocoral", 5, -1, 0.9, 1.4],
	["vase_sponge", 3, -1, 0.8, 1.2], ["puffball_sponges", 6, -1, 1.0, 1.6], ["green_anemone", 8, -1, 0.9, 1.5],
	["strawberry_anemones", 7, -1, 1.0, 1.6], ["urchin_purple", 14, -1, 1.0, 1.5], ["urchin_red", 6, -1, 0.9, 1.3],
	["ochre_star", 9, -1, 1.0, 1.5], ["bat_star", 9, -1, 1.0, 1.6], ["scallop", 4, -1, 1.0, 1.4],
	["mussel_clump", 5, -1, 1.0, 1.5], ["feather_dusters", 6, -1, 1.0, 1.6],
	["brain_coral", 5, 1, 0.6, 1.3], ["table_coral", 6, 1, 0.7, 1.3], ["staghorn_coral", 7, 1, 0.8, 1.4],
	["pillar_coral", 5, 1, 0.9, 1.5], ["barrel_sponge", 3, 1, 0.7, 1.1], ["sea_fan_purple", 6, 1, 0.7, 1.1],
	["soft_coral", 9, 1, 0.8, 1.5], ["sea_rods", 6, 1, 0.8, 1.3], ["giant_clam", 2, 1, 0.8, 1.1],
]

var _clock := 0.0
var _placed := {}
var _stones: Array = []


func _ready() -> void:
	if not ProjectSettings.has_setting("shader_globals/water_clock"):
		RenderingServer.global_shader_parameter_add(&"water_clock", RenderingServer.GLOBAL_VAR_TYPE_FLOAT, 0.0)
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.05, 0.3, 0.45)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.55, 0.75, 0.9)
	env.environment.ambient_light_energy = 0.7
	env.environment.fog_enabled = true
	env.environment.fog_light_color = Color(0.05, 0.3, 0.45)
	env.environment.fog_density = 0.018
	add_child(env)
	var sun := DirectionalLight3D.new()
	add_child(sun)
	sun.look_at_from_position(Vector3(2.0, 6.0, 3.0), Vector3.ZERO)
	var sand := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(120.0, 120.0)
	sand.mesh = plane
	var sandy := StandardMaterial3D.new()
	sandy.albedo_color = Color(0.74, 0.68, 0.52)
	sandy.roughness = 1.0
	sand.material_override = sandy
	add_child(sand)

	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	for stone: Array in ROCKY + CORAL:
		var at := Transform3D(Basis(Vector3.UP, stone[2]).scaled(Vector3.ONE * float(stone[3])), stone[1])
		_put(stone[0], at, Color.WHITE)
		_stones.append([at, SeaFloorProps.mesh_of(stone[0]).generate_triangle_mesh()])
	for growth: Array in GROWTH:
		var piece: String = growth[0]
		var tints := SeaFloorProps.tints_of(piece)
		var done := 0
		var tries := 0
		while done < int(growth[1]) and tries < 400:
			tries += 1
			var x := rng.randf_range(1.0, 15.0) * float(growth[2]) + (2.0 if int(growth[2]) < 0 else 0.0)
			var spot := _ground(Vector3(x, 0.0, rng.randf_range(-6.0, 6.5)))
			# (on a rock's top or its shoulder, not its wall; and most things on rock, not on sand)
			if spot[1].y < 0.55 or (spot[0].y < 0.05 and rng.randf() < 0.75):
				continue
			var turn := Basis(Vector3.UP, rng.randf() * TAU).scaled(Vector3.ONE * rng.randf_range(growth[3], growth[4]))
			_put(piece, Transform3D(turn, spot[0]), tints[rng.randi() % tints.size()])
			done += 1
	for piece: String in _placed:
		var many := MultiMesh.new()
		many.transform_format = MultiMesh.TRANSFORM_3D
		many.use_colors = true
		many.mesh = SeaFloorProps.mesh_of(piece)
		many.instance_count = (_placed[piece] as Array).size()
		for i in many.instance_count:
			many.set_instance_transform(i, _placed[piece][i][0])
			many.set_instance_color(i, _placed[piece][i][1])
		var drawn := MultiMeshInstance3D.new()
		drawn.name = piece
		drawn.multimesh = many
		drawn.material_override = SeaFloorProps.material_of(piece)
		add_child(drawn)
	var camera := Camera3D.new()
	camera.fov = 50.0
	add_child(camera)
	camera.look_at_from_position(Vector3(0.5, 5.0, 17.0), Vector3(0.0, 1.6, 0.0))
	camera.current = true


func _process(delta: float) -> void:
	_clock += delta
	RenderingServer.global_shader_parameter_set(&"water_clock", _clock)


func _put(piece: String, at: Transform3D, colour: Color) -> void:
	if not _placed.has(piece):
		_placed[piece] = []
	(_placed[piece] as Array).append([at, colour])


## The highest point of the rocks (or the sand) under a spot, and which way the skin faces there.
func _ground(spot: Vector3) -> Array:
	var best := Vector3(spot.x, 0.0, spot.z)
	var facing := Vector3.UP
	for stone: Array in _stones:
		var inverse: Transform3D = (stone[0] as Transform3D).affine_inverse()
		var hit: Dictionary = (stone[1] as TriangleMesh).intersect_ray(inverse * Vector3(spot.x, 30.0, spot.z), Vector3.DOWN)
		if not hit.is_empty():
			var world: Vector3 = (stone[0] as Transform3D) * (hit["position"] as Vector3)
			if world.y > best.y:
				best = world
				facing = ((stone[0] as Transform3D).basis * (hit["normal"] as Vector3)).normalized()
	return [best, facing]
