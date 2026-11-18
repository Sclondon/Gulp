class_name Scenery
extends Node3D
## What stands and grows in each part of the sea (Sea.ZONES), from GameCommon's components where
## they are installed: the kelp forest on its rocks, the sea grass bed, the coral reef, the cliffs
## of the shelf's edge, and the field of garden eels in the sand. The same places every time (a
## seed of its own).
##
## Rocks, coral heads and cliffs stop a swimmer (their spheres go to `Sea.add_rock`); kelp, grass,
## small reef life and the eels do not. The eels sink into the sand as the player comes near, and
## one still out when its mouth arrives is eaten.

const KELP := "res://plants/kelp/kelp_forest.gd"
const GRASS := "res://plants/sea_grass/sea_grass_bed.gd"
const PROPS := "res://scenery/sea_floor_props/sea_floor_props.gd"
const EELS := "res://creatures/garden_eel/garden_eel_colony.gd"
## How many kelp plants, tufts of grass and garden eels.
const KELPS := 150
const TUFTS := 2600
const EEL_COUNT := 260
## How long a garden eel counts as for the eating rule (m), and how long one stays gone (s).
const EEL_LENGTH := 0.6
const EEL_BACK := 25.0
## Beyond this the water hides plants (m).
const SEEN := 60.0

## Who lays the grass aside and frightens the eels (the player).
var player: Player

var _grass: Node3D
var _eels: Node3D
var _eaten := {}
var _props: GDScript
var _rng := RandomNumberGenerator.new()
# What has been placed of each piece: name -> [transforms, colours].
var _placed := {}
var _clock := 0.0


func _ready() -> void:
	_rng.seed = 11
	if ResourceLoader.exists(PROPS):
		_props = load(PROPS)
		_place_rocks()
		_place_reef()
		_place_cliffs()
		_draw_pieces()
	if ResourceLoader.exists(KELP):
		_plant_kelp()
	if ResourceLoader.exists(GRASS):
		_plant_grass()
	if ResourceLoader.exists(EELS):
		_plant_eels()


func _process(delta: float) -> void:
	_clock += delta
	if player == null:
		return
	if _grass:
		_grass.set(&"pushers", PackedVector3Array([player.global_position]))
	if _eels and player.alive:
		var zone: Dictionary = Sea.ZONES.sand
		var at := player.global_position
		if Vector2(at.x, at.z).distance_to(zone.at) > float(zone.radius) + 10.0:
			return
		_eels.call(&"disturb", at, 1.6 + player.length * 2.5)
		var mouth := player.mouth()
		var i: int = _eels.call(&"nearest", mouth)
		if i >= 0 and Life.is_food(player.length, EEL_LENGTH):
			var head: Vector3 = _eels.call(&"head_of", i)
			if head.distance_to(mouth) < player.length * 0.3 + 0.06:
				_eels.call(&"take", i)
				_eaten[i] = _clock + EEL_BACK
				player.feed(EEL_LENGTH, 0.5)
		for gone: int in _eaten.keys():
			if _clock > float(_eaten[gone]):
				_eaten.erase(gone)
				_eels.call(&"restore", gone)


# A piece of the kit stood somewhere: on the floor at a place, turned, at a size, tinted. Its
# spheres (if it has any) become rocks of the sea.
func _stand(piece: String, at: Vector2, turn: float, big := 1.0, tint := Color.WHITE, lift := 0.0) -> Transform3D:
	var where := Transform3D(Basis(Vector3.UP, turn).scaled(Vector3.ONE * big), Vector3(at.x, Sea.ground(at.x, at.y) + lift, at.y))
	if not _placed.has(piece):
		_placed[piece] = [[], []]
	_placed[piece][0].append(where)
	_placed[piece][1].append(tint)
	for sphere: Vector4 in _props.call(&"spheres_of", piece):
		var middle := where * Vector3(sphere.x, sphere.y, sphere.z)
		Sea.add_rock(Vector4(middle.x, middle.y, middle.z, sphere.w * big))
	return where


# One of a piece's tints, or white.
func _tint(piece: String) -> Color:
	var tints: PackedColorArray = _props.call(&"tints_of", piece)
	return tints[_rng.randi() % tints.size()] if tints.size() > 0 else Color.WHITE


func _in_zone(zone: Dictionary, share := 1.0) -> Vector2:
	var turn := _rng.randf() * TAU
	return zone.at + Vector2(cos(turn), sin(turn)) * float(zone.radius) * share * sqrt(_rng.randf())


# The rocky floor of the kelp forest: boulders, stacks, a ledge or two, an arch to swim through,
# and the cold-water life that grows on and round them.
func _place_rocks() -> void:
	var zone: Dictionary = Sea.ZONES.kelp
	var rocks: PackedStringArray = _props.call(&"names", "rock")
	var life: PackedStringArray = _props.call(&"names", "cold")
	_stand("rock_arch", zone.at + Vector2(6.0, 4.0), 0.6, 1.2, Color.WHITE, -0.3)
	for i in 46:
		var piece := rocks[_rng.randi() % rocks.size()]
		if piece == "rock_arch":
			piece = "rock_boulder"
		var at := _in_zone(zone, 1.05)
		_stand(piece, at, _rng.randf() * TAU, _rng.randf_range(0.8, 1.5), Color.WHITE, -0.25)
		# (a few living things on the sand at its foot)
		for k in 3:
			var kind := life[_rng.randi() % life.size()]
			var beside := at + Vector2.from_angle(_rng.randf() * TAU) * _rng.randf_range(1.0, 3.5)
			_stand(kind, beside, _rng.randf() * TAU, _rng.randf_range(0.9, 1.6), _tint(kind), -0.02)


# The coral reef: its body is coral heads (bommies) on the mound, dressed with corals, sponges,
# fans and clams.
func _place_reef() -> void:
	var zone: Dictionary = Sea.ZONES.reef
	var heads: PackedStringArray = _props.call(&"names", "bommie")
	var life: PackedStringArray = _props.call(&"names", "tropical")
	for i in 16:
		var at := _in_zone(zone, 0.8)
		_stand(heads[_rng.randi() % heads.size()], at, _rng.randf() * TAU, _rng.randf_range(0.9, 1.5), Color.WHITE, -0.3)
	for i in 130:
		var kind := life[_rng.randi() % life.size()]
		var at := _in_zone(zone, 0.95)
		_stand(kind, at, _rng.randf() * TAU, _rng.randf_range(0.8, 1.7), _tint(kind), -0.03)


# The shelf's edge: a wall of cliff pieces down from its lip, side by side along the coast.
func _place_cliffs() -> void:
	var walls: PackedStringArray = _props.call(&"names", "cliff")
	var wide: float = _props.get(&"CLIFF_WIDE")
	var tall: float = _props.get(&"CLIFF_TALL")
	var z := -Sea.SIDE - 6.0
	var i := 0
	while z < Sea.SIDE + 6.0:
		# (its back along the lip, its face out to sea)
		var lip := Vector2(Sea.edge_at(z) + 2.0, z)
		var slope := (Sea.edge_at(z + 1.0) - Sea.edge_at(z - 1.0)) * 0.5
		var top := Sea.ground(lip.x - 3.0, z)
		var turn := PI * 0.5 - atan(slope)
		var where := Transform3D(Basis(Vector3.UP, turn), Vector3(lip.x, top - tall + 0.4, lip.y))
		var piece := walls[i % walls.size()]
		if not _placed.has(piece):
			_placed[piece] = [[], []]
		_placed[piece][0].append(where)
		_placed[piece][1].append(Color.WHITE)
		for sphere: Vector4 in _props.call(&"spheres_of", piece):
			var middle := where * Vector3(sphere.x, sphere.y, sphere.z)
			Sea.add_rock(Vector4(middle.x, middle.y, middle.z, sphere.w))
		z += wide * 0.97
		i += 1


# Everything placed, drawn: one MultiMesh a piece. (Cliffs are drawn with their light model: there
# are many and they are seen from a little way off.)
func _draw_pieces() -> void:
	for piece: String in _placed:
		var wheres: Array = _placed[piece][0]
		var tints: Array = _placed[piece][1]
		var many := MultiMesh.new()
		many.transform_format = MultiMesh.TRANSFORM_3D
		many.use_colors = true
		many.mesh = _props.call(&"mesh_of", piece, piece.begins_with("cliff"))
		many.instance_count = wheres.size()
		for i in wheres.size():
			many.set_instance_transform(i, wheres[i])
			many.set_instance_color(i, tints[i])
		var drawn := MultiMeshInstance3D.new()
		drawn.name = piece
		drawn.multimesh = many
		drawn.material_override = _props.call(&"material_of", piece)
		drawn.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(drawn)


# The kelp forest: plants standing in clumps with clear lanes between, each reaching for the
# surface (the tallest lie along it).
func _plant_kelp() -> void:
	var zone: Dictionary = Sea.ZONES.kelp
	var places := PackedVector3Array()
	var heights := PackedFloat32Array()
	var clumps: Array[Vector2] = []
	for i in 22:
		clumps.append(_in_zone(zone, 0.95))
	for i in KELPS:
		var clump := clumps[i % clumps.size()]
		var at := clump + Vector2.from_angle(_rng.randf() * TAU) * _rng.randf_range(0.3, 4.5)
		var low := Sea.ground(at.x, at.y)
		var deep := Sea.SURFACE - low
		if deep < 5.0:
			continue
		places.append(Vector3(at.x, low - 0.1, at.y))
		heights.append(minf(deep * _rng.randf_range(0.7, 1.25), 25.0))
	var forest: Node3D = (load(KELP) as GDScript).new()
	forest.set(&"far", SEEN)
	forest.set(&"current", Vector2(0.3, 0.1))
	add_child(forest)
	forest.call(&"plant", places, heights, Sea.SURFACE)


# The sea grass bed: thick in the middle, thinning to its edge.
func _plant_grass() -> void:
	var zone: Dictionary = Sea.ZONES.grass
	var places := PackedVector3Array()
	var heights := PackedFloat32Array()
	for i in TUFTS:
		var turn := _rng.randf() * TAU
		# (more of them towards the middle)
		var at: Vector2 = zone.at + Vector2(cos(turn), sin(turn)) * float(zone.radius) * pow(_rng.randf(), 0.7)
		var low := Sea.ground(at.x, at.y)
		if Sea.SURFACE - low < 1.5:
			continue
		places.append(Vector3(at.x, low - 0.03, at.y))
		heights.append(_rng.randf_range(0.45, 1.2))
	_grass = (load(GRASS) as GDScript).new()
	_grass.set(&"far", SEEN)
	_grass.set(&"current", Vector2(0.3, 0.1))
	_grass.set(&"push_radius", 0.7)
	add_child(_grass)
	_grass.call(&"plant", places, heights)


# The garden eels: a few loose patches of them in the open sand, each in its burrow.
func _plant_eels() -> void:
	var zone: Dictionary = Sea.ZONES.sand
	var places := PackedVector3Array()
	var patches: Array[Vector2] = []
	for i in 7:
		patches.append(_in_zone(zone, 0.8))
	for i in EEL_COUNT:
		var at := patches[i % patches.size()] + Vector2.from_angle(_rng.randf() * TAU) * _rng.randf_range(0.4, 6.0)
		places.append(Vector3(at.x, Sea.ground(at.x, at.y), at.y))
	_eels = (load(EELS) as GDScript).new()
	# (into the current, which runs in from the sea)
	_eels.set(&"facing", Vector3(1.0, 0.0, 0.3).normalized())
	_eels.set(&"eel_scale", 1.5)
	add_child(_eels)
	_eels.call(&"plant", places)
