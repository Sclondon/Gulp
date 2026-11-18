class_name Scenery
extends Node3D
## What stands and grows in each part of the bay (Sea.ZONES; the layout is tools/MONTEREY.md), from
## GameCommon's components where they are installed: the two kelp forests on their rocks, the sea
## grass off the peninsula, the mangroves of Elkhorn Slough, the coral and sponges round the sunken liner, the
## cliffs of the shelf's edge, the field of garden eels in the sand off Santa Cruz, and the docks
## (models/docks.glb, tools/build_docks.py) at Monterey harbour and the Santa Cruz wharf. The same
## places every time (a seed of its own). The liner, Atlantis and the pirate ship are other
## agents' nodes, added here if their scripts are there (`_add_landmarks`).
##
## Rocks, coral heads, cliffs, pilings, floats and moored hulls stop a swimmer (their spheres go to
## `Sea.add_rock`); kelp, grass, small reef life and the eels do not. The eels sink into the sand as
## the player comes near, and one still out when its mouth arrives is eaten.

const KELP := "res://plants/kelp/kelp_forest.gd"
const GRASS := "res://plants/sea_grass/sea_grass_bed.gd"
const PROPS := "res://scenery/sea_floor_props/sea_floor_props.gd"
const EELS := "res://creatures/garden_eel/garden_eel_colony.gd"
const ANEMONE := "res://creatures/clownfish/clownfish_anemone.gd"
const MANGROVE := "res://plants/mangrove/mangrove_stand.gd"
const SEAWEED := "res://plants/seaweed/seaweed_bed.gd"
const LIVE_ANEMONE := "res://creatures/anemone/anemone.gd"
const DOCKS := "res://models/docks.glb"
const GEAR := "res://models/fishing_gear.glb"
const TRAWLER := "res://models/shrimp_boat.glb"
const WRECK := "res://scripts/wreck.gd"
const RUINS := "res://scripts/ruins.gd"
const PIRATE := "res://scripts/pirate_wreck.gd"
## Mangroves along the river's mouth (Elkhorn Slough at Moss Landing): the user, 2026-11-17: "a
## mangrove / river entrance area", and 2026-11-18: "the margrove river part goes in the center
## part where that river meets the bay". Off: the slough's banks are bare.
const MANGROVES := true
## How many kelp plants (both forests), tufts of grass (the bed, and eelgrass in the slough's
## channel: none while the mangroves are there) and garden eels.
const KELPS := 180
const TUFTS := 2000
const SLOUGH_TUFTS := 0
const EEL_COUNT := 260
## How long a garden eel counts as for the eating rule (m), and how long one stays gone (s).
const EEL_LENGTH := 0.6
const EEL_BACK := 25.0
## Beyond this the water hides plants (m), and docks and moored boats.
const SEEN := 60.0
const DOCKS_SEEN := 80.0
## The clear lanes kept for the wrecks' hulls (long, wide: m, along their headings).
const WRECK_LANE := Vector2(64.0, 14.0)
const PIRATE_LANE := Vector2(34.0, 12.0)
## How high a wharf's deck stands over the water (m), and how far under its top the piles stand.
const DECK_UP := 0.9
const PILE_DOWN := 0.7
## Where the two docks are (world): the middles of the docks zone's two patches.
const MONTEREY := Vector2(35.2, 78.4)
const SANTA_CRUZ := Vector2(-27.2, -107.2)
## The outcrop the pirate ship struck, and its island (world).
const OUTCROP := Vector2(-98.0, -24.0)

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
		_place_breakwater()
		_draw_pieces()
	if ResourceLoader.exists(KELP):
		_plant_kelp()
	if ResourceLoader.exists(GRASS):
		_plant_grass()
	if ResourceLoader.exists(EELS):
		_plant_eels()
	if ResourceLoader.exists(ANEMONE):
		_plant_anemones()
	if MANGROVES and ResourceLoader.exists(MANGROVE):
		_plant_mangroves()
	if ResourceLoader.exists(SEAWEED):
		_plant_seaweed()
	if ResourceLoader.exists(LIVE_ANEMONE):
		_plant_live_anemones()
	if ResourceLoader.exists(DOCKS):
		_build_docks()
	_add_landmarks()


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


# A place in a zone (in one of its patches, picked by size), within `share` of its radius.
func _in_zone(zone: String, share := 1.0) -> Vector2:
	var all := Sea.patches(zone)
	var pick: Array = all[0]
	if all.size() > 1:
		var total := 0.0
		for patch: Array in all:
			total += pow(float(patch[1]), 2.0)
		var roll := _rng.randf() * total
		for patch: Array in all:
			roll -= pow(float(patch[1]), 2.0)
			pick = patch
			if roll <= 0.0:
				break
	var turn := _rng.randf() * TAU
	return pick[0] + Vector2(cos(turn), sin(turn)) * float(pick[1]) * share * sqrt(_rng.randf())


# Whether a place is inside a wreck's lane: a box `size` (long, wide) along a heading round a middle,
# with `margin` more all round.
static func in_lane(at: Vector2, middle: Vector3, heading: float, size: Vector2, margin := 0.0) -> bool:
	var along := Vector2(sin(heading), cos(heading))
	var off := at - Vector2(middle.x, middle.z)
	return absf(off.dot(along)) < size.x * 0.5 + margin and absf(off.dot(Vector2(along.y, -along.x))) < size.y * 0.5 + margin


# Whether a place is kept clear for a wreck or Atlantis.
func _kept_clear(at: Vector2, margin := 2.0) -> bool:
	return in_lane(at, Sea.WRECK_AT, Sea.WRECK_HEADING, WRECK_LANE, margin) or in_lane(at, Sea.PIRATE_AT, Sea.PIRATE_HEADING, PIRATE_LANE, margin) \
			or at.distance_to(Vector2(Sea.RUINS_AT.x, Sea.RUINS_AT.z)) < float(Bay.RUINS_TERRACE[2]) * Bay.K


# The rocky floor of the kelp forests: boulders, stacks, a ledge or two, an arch to swim through,
# and the cold-water life that grows on and round them.
func _place_rocks() -> void:
	var rocks: PackedStringArray = _props.call(&"names", "rock")
	var life: PackedStringArray = _props.call(&"names", "cold")
	var big: Dictionary = Sea.ZONES.kelp
	_stand("rock_arch", big.at + Vector2(-10.0, 6.0), 0.6, 1.2, Color.WHITE, -0.3)
	for i in 60:
		var piece := rocks[_rng.randi() % rocks.size()]
		if piece == "rock_arch":
			piece = "rock_boulder"
		var at := _in_zone("kelp", 1.05)
		if Sea.SURFACE - Sea.ground(at.x, at.y) < 3.0:
			continue
		_stand(piece, at, _rng.randf() * TAU, _rng.randf_range(0.8, 1.5), Color.WHITE, -0.25)
		# (a few living things on the sand at its foot)
		for k in 3:
			var kind := life[_rng.randi() % life.size()]
			var beside := at + Vector2.from_angle(_rng.randf() * TAU) * _rng.randf_range(1.0, 3.5)
			_stand(kind, beside, _rng.randf() * TAU, _rng.randf_range(0.9, 1.6), _tint(kind), -0.02)


# The liner's reef: coral heads (bommies) round the wreck and corals, sponges, fans and clams on its
# shelf, with the lane where its hull lies kept clear (the wreck itself is another agent's).
func _place_reef() -> void:
	var heads: PackedStringArray = _props.call(&"names", "bommie")
	var life: PackedStringArray = _props.call(&"names", "tropical")
	var placed := 0
	while placed < 16:
		var at := _in_zone("reef", 0.85)
		if in_lane(at, Sea.WRECK_AT, Sea.WRECK_HEADING, WRECK_LANE, 4.0):
			continue
		_stand(heads[_rng.randi() % heads.size()], at, _rng.randf() * TAU, _rng.randf_range(0.9, 1.5), Color.WHITE, -0.3)
		placed += 1
	placed = 0
	while placed < 150:
		var kind := life[_rng.randi() % life.size()]
		var at := _in_zone("reef", 0.95)
		# (thickest along the hull's sides, as on a wreck)
		if in_lane(at, Sea.WRECK_AT, Sea.WRECK_HEADING, WRECK_LANE, 0.5):
			continue
		_stand(kind, at, _rng.randf() * TAU, _rng.randf_range(0.8, 1.7), _tint(kind), -0.03)
		placed += 1


# The shelf's edge: a wall of cliff pieces down from its lip, side by side along the coast, facing
# west out to sea; none where the edge runs into the shore's shallows or across a canyon.
func _place_cliffs() -> void:
	var walls: PackedStringArray = _props.call(&"names", "cliff")
	var wide: float = _props.get(&"CLIFF_WIDE")
	var tall: float = _props.get(&"CLIFF_TALL")
	var z := Sea.NORTH
	var i := 0
	while z < Sea.SOUTH:
		var lip := Vector2(Sea.edge_at(z) + 2.0, z)
		var slope := (Sea.edge_at(z + 1.0) - Sea.edge_at(z - 1.0)) * 0.5
		var top := Sea.ground(lip.x + 3.0, z)
		var deep := Sea.SURFACE - top
		z += wide * 0.97
		i += 1
		if deep < 10.0 or deep > 30.0:
			continue
		var turn := PI * 1.5 - atan(slope)
		var where := Transform3D(Basis(Vector3.UP, turn), Vector3(lip.x, top - tall + 0.4, lip.y))
		var piece := walls[i % walls.size()]
		if not _placed.has(piece):
			_placed[piece] = [[], []]
		_placed[piece][0].append(where)
		_placed[piece][1].append(Color.WHITE)
		for sphere: Vector4 in _props.call(&"spheres_of", piece):
			var middle := where * Vector3(sphere.x, sphere.y, sphere.z)
			Sea.add_rock(Vector4(middle.x, middle.y, middle.z, sphere.w))


# Monterey's breakwater: dumped boulders in a line out from the shore round the harbour's west
# side, two deep, the upper ones breaking the surface.
func _place_breakwater() -> void:
	var rocks := ["rock_boulder", "rock_stack"]
	var o := MONTEREY - Vector2(44.0, 98.0)
	var line := [o + Vector2(10.0, 106.0), o + Vector2(16.0, 90.0), o + Vector2(26.0, 82.0)]
	for k in line.size() - 1:
		var a: Vector2 = line[k]
		var b: Vector2 = line[k + 1]
		var steps := int(a.distance_to(b) / 2.4)
		for s in steps:
			var at := a.lerp(b, float(s) / steps)
			for side: float in [-1.4, 1.4]:
				var p := at + (b - a).normalized().orthogonal() * side + Vector2(_rng.randf_range(-0.5, 0.5), _rng.randf_range(-0.5, 0.5))
				var deep := Sea.SURFACE - Sea.ground(p.x, p.y)
				var piece: String = rocks[_rng.randi() % rocks.size()] if _props.call(&"names", "rock").has(rocks[1]) else rocks[0]
				_stand(piece, p, _rng.randf() * TAU, _rng.randf_range(1.2, 1.7), Color(0.75, 0.73, 0.7), -0.2)
				_stand("rock_boulder", p + Vector2(_rng.randf_range(-0.6, 0.6), _rng.randf_range(-0.6, 0.6)), _rng.randf() * TAU,
						_rng.randf_range(1.0, 1.4), Color(0.8, 0.78, 0.74), maxf(deep - 1.2, 0.0))


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


# The kelp forests: plants standing in clumps with clear lanes between, each reaching for the
# surface (the tallest lie along it). Both patches of the zone, the big one in the south-east.
func _plant_kelp() -> void:
	var places := PackedVector3Array()
	var heights := PackedFloat32Array()
	var clumps: Array[Vector2] = []
	for i in 28:
		clumps.append(_in_zone("kelp", 0.95))
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


# The sea grass: the bed off the peninsula, thick in the middle and thinning to its edge, and
# eelgrass along Elkhorn Slough's channel.
func _plant_grass() -> void:
	var places := PackedVector3Array()
	var heights := PackedFloat32Array()
	var zone: Dictionary = Sea.ZONES.grass
	for i in TUFTS:
		var turn := _rng.randf() * TAU
		# (more of them towards the middle)
		var at: Vector2 = zone.at + Vector2(cos(turn), sin(turn)) * float(zone.radius) * pow(_rng.randf(), 0.7)
		var low := Sea.ground(at.x, at.y)
		if Sea.SURFACE - low < 1.5:
			continue
		places.append(Vector3(at.x, low - 0.03, at.y))
		heights.append(_rng.randf_range(0.45, 1.2))
	for i in SLOUGH_TUFTS:
		var k := _rng.randi() % (Bay.SLOUGH.size() - 1)
		var at: Vector2 = (Bay.SLOUGH[k] as Vector2).lerp(Bay.SLOUGH[k + 1], _rng.randf()) * Bay.K + Vector2(_rng.randf_range(-4.0, 4.0), _rng.randf_range(-4.0, 4.0))
		var low := Sea.ground(at.x, at.y)
		if Sea.SURFACE - low < 1.2:
			continue
		places.append(Vector3(at.x, low - 0.03, at.y))
		heights.append(_rng.randf_range(0.4, 0.9))
	_grass = (load(GRASS) as GDScript).new()
	_grass.set(&"far", SEEN)
	_grass.set(&"current", Vector2(0.3, 0.1))
	_grass.set(&"push_radius", 0.7)
	add_child(_grass)
	_grass.call(&"plant", places, heights)


# Seaweed (the user, 2026-11-18: "sea weed"; which kind grows where and how much is Claude's
# pick): sea lettuce in the sea grass and the slough, rockweed, feather boa kelp and sea palms
# among the kelp's rocks and on the docks' shore, red algae round the liner, and mats of sargassum
# afloat over the open ocean. Each row: the kind (SeaweedBed.Kind), the zone, how many, how tall.
func _plant_seaweed() -> void:
	var places := PackedVector3Array()
	var sizes := PackedFloat32Array()
	var kinds := PackedInt32Array()
	for row: Array in [[0, "grass", 140, 0.25, 0.5], [0, "river", 60, 0.25, 0.45], [1, "kelp", 200, 0.25, 0.45], [1, "docks", 50, 0.25, 0.45],
			[2, "reef", 160, 0.16, 0.32], [3, "kelp", 50, 1.8, 3.0], [4, "kelp", 50, 0.4, 0.7], [5, "open", 70, 0.8, 1.8]]:
		for i in int(row[2]):
			var at := _in_zone(row[1], 0.95)
			var low := Sea.ground(at.x, at.y)
			if Sea.SURFACE - low < 1.0 or (row[1] == "reef" and in_lane(at, Sea.WRECK_AT, Sea.WRECK_HEADING, WRECK_LANE)):
				continue
			places.append(Vector3(at.x, low - 0.02, at.y))
			sizes.append(_rng.randf_range(row[3], row[4]))
			kinds.append(int(row[0]))
	var bed: Node3D = (load(SEAWEED) as GDScript).new()
	bed.set(&"far", SEEN)
	bed.set(&"cell", 8.0)
	bed.set(&"current", Vector2(0.3, 0.1))
	add_child(bed)
	bed.call(&"plant", places, sizes, kinds, Sea.SURFACE)


# Living anemones (the user's list: "anemones"; where and how many is Claude's pick): giant green
# ones on the kelp's rocks and round the liner, tube anemones in the sand, plumose ones in the kelp
# and on the docks' piles' feet.
func _plant_live_anemones() -> void:
	for row: Array in [[0, "kelp", 6], [0, "reef", 6], [1, "sand", 10], [2, "kelp", 8], [2, "docks", 6]]:
		var made := 0
		var tries := 0
		while made < int(row[2]) and tries < 60:
			tries += 1
			var at := _in_zone(row[1], 0.85)
			if _kept_clear(at) or Sea.SURFACE - Sea.ground(at.x, at.y) < 1.0:
				continue
			var one: Node3D = (load(LIVE_ANEMONE) as GDScript).new()
			one.set(&"kind", int(row[0]))
			one.set(&"game", true)
			add_child(one)
			one.global_position = Vector3(at.x, Sea.ground(at.x, at.y) - 0.01, at.y)
			one.rotation.y = _rng.randf() * TAU
			one.scale = Vector3.ONE * _rng.randf_range(1.0, 1.8)
			made += 1


# The clownfish's homes: a few host anemones round the liner.
func _plant_anemones() -> void:
	var made := 0
	while made < 7:
		var at := _in_zone("reef", 0.7)
		if in_lane(at, Sea.WRECK_AT, Sea.WRECK_HEADING, WRECK_LANE, 1.0):
			continue
		var home: Node3D = (load(ANEMONE) as GDScript).new()
		add_child(home)
		home.global_position = Vector3(at.x, Sea.ground(at.x, at.y) - 0.02, at.y)
		home.scale = Vector3.ONE * _rng.randf_range(1.2, 2.0)
		made += 1


# The mangroves (see MANGROVES): along both banks of Elkhorn Slough, their roots down through
# the surface into the mud. Their root tangles stop a swimmer.
func _plant_mangroves() -> void:
	var places := PackedVector3Array()
	var turns := PackedFloat32Array()
	var sizes := PackedFloat32Array()
	var kinds := PackedInt32Array()
	for k in Bay.SLOUGH.size() - 1:
		var a: Vector2 = Bay.SLOUGH[k] * Bay.K
		var b: Vector2 = Bay.SLOUGH[k + 1] * Bay.K
		var across := (b - a).normalized().orthogonal()
		var s := 0.0
		while s < a.distance_to(b):
			var at := a + (b - a).normalized() * s
			for side: float in [-1.0, 1.0]:
				var p := at + across * side * _rng.randf_range(Bay.SLOUGH_HALF * Bay.K + 0.8, Bay.SLOUGH_HALF * Bay.K + 3.0)
				places.append(Vector3(p.x, Sea.SURFACE, p.y))
				turns.append(_rng.randf() * TAU)
				sizes.append(_rng.randf_range(0.8, 1.15))
				kinds.append(_rng.randi() % 6)
			s += _rng.randf_range(3.5, 5.5)
	var stand: Node3D = (load(MANGROVE) as GDScript).new()
	stand.set(&"far", SEEN)
	stand.set(&"near", 14.0)
	add_child(stand)
	stand.call(&"plant", places, turns, sizes, kinds)
	for sphere: Vector4 in stand.call(&"spheres"):
		Sea.add_rock(sphere)


# The garden eels: a few loose patches of them in the open sand, each in its burrow.
func _plant_eels() -> void:
	var zone: Dictionary = Sea.ZONES.sand
	var places := PackedVector3Array()
	var patches: Array[Vector2] = []
	for i in 7:
		patches.append(_in_zone("sand", 0.8))
	for i in EEL_COUNT:
		var at := patches[i % patches.size()] + Vector2.from_angle(_rng.randf() * TAU) * _rng.randf_range(0.4, 6.0)
		places.append(Vector3(at.x, Sea.ground(at.x, at.y), at.y))
	_eels = (load(EELS) as GDScript).new()
	# (into the current, which runs in from the sea)
	_eels.set(&"facing", Vector3(-1.0, 0.0, 0.3).normalized())
	_eels.set(&"eel_scale", 1.5)
	add_child(_eels)
	_eels.call(&"plant", places)


# ---------------------------------------------------------------------------------------- the docks

# The docks: Monterey harbour (Fisherman's Wharf, the commercial wharf, a marina of floating docks
# with boats in it, a trawler alongside) and the Santa Cruz wharf with the small craft harbour's
# floats beside it. Each site is its own set of MultiMeshes,
# so that it is hidden as a whole beyond DOCKS_SEEN.
func _build_docks() -> void:
	var kit: Node3D = (load(DOCKS) as PackedScene).instantiate()
	var deck_y := Sea.SURFACE + DECK_UP
	# Monterey (laid out round where it was on the chart: the docks are not scaled with the bay).
	var o := MONTEREY - Vector2(44.0, 98.0)
	var site := _Site.new()
	_wharf(site, o + Vector2(30.0, 104.0), 5, deck_y)
	_wharf(site, o + Vector2(60.0, 102.0), 5, deck_y)
	for at: Vector2 in [Vector2(44.0, 92.0), Vector2(44.0, 100.0)]:
		_float(site, o + at, 0.0)
	for at: Vector2 in [Vector2(40.0, 93.0), Vector2(40.0, 100.0), Vector2(48.0, 93.0), Vector2(48.0, 99.0)]:
		_float(site, o + at, PI * 0.5)
	for at: Vector2 in [Vector2(45.4, 87.6), Vector2(45.4, 104.4), Vector2(35.6, 96.5)]:
		_pile(site, o + at, Sea.SURFACE + 1.6)
	_boat(site, "Sailboat", o + Vector2(48.0, 96.0), PI * 0.5)
	_boat(site, "Sailboat", o + Vector2(40.0, 96.5), -PI * 0.5)
	_boat(site, "Skiff", o + Vector2(40.0, 90.6), PI * 0.5)
	# (the litter on the floor under the wharves: tools/art_src/concept_docks.jpg)
	for each: Array in [["Tyre", Vector2(34.0, 95.0)], ["Tyre", Vector2(52.0, 90.0)], ["Tyre", Vector2(27.0, 86.0)], ["CrabPot", Vector2(36.0, 88.0)],
			["CrabPot", Vector2(55.0, 97.0)], ["CrabPot", Vector2(46.0, 85.0)], ["Chain", Vector2(31.0, 99.0)], ["Chain", Vector2(50.0, 101.0)], ["Anchor", Vector2(51.0, 93.0)]]:
		_litter(site, each[0], o + (each[1] as Vector2))
	_draw_site(site, kit, "Monterey")
	_trawler(Vector3(67.5 + o.x, Sea.SURFACE, 94.0 + o.y), 0.0)
	# Santa Cruz.
	o = SANTA_CRUZ - Vector2(-34.0, -134.0)
	site = _Site.new()
	_wharf(site, o + Vector2(-45.0, -146.0), 8, deck_y, true)
	_float(site, o + Vector2(-18.0, -140.0), PI * 0.5)
	for at: Vector2 in [Vector2(-22.0, -135.0), Vector2(-14.0, -135.0)]:
		_float(site, o + at, 0.0)
	for at: Vector2 in [Vector2(-23.2, -141.2), Vector2(-12.8, -141.2)]:
		_pile(site, o + at, Sea.SURFACE + 1.6)
	_boat(site, "Sailboat", o + Vector2(-18.0, -133.0), 0.0)
	_boat(site, "Skiff", o + Vector2(-27.0, -136.0), 0.1)
	for each: Array in [["Tyre", Vector2(-41.0, -128.0)], ["CrabPot", Vector2(-30.0, -124.0)], ["CrabPot", Vector2(-49.0, -121.0)], ["Chain", Vector2(-44.0, -138.0)]]:
		_litter(site, each[0], o + (each[1] as Vector2))
	_draw_site(site, kit, "SantaCruz")
	_build_outcrop(kit)
	kit.free()


# The outcrop the pirate ship struck (the user, 2026-11-18: "there shoule be an outcropping of
# rocks near the pirate ship, pillars and shards and an island that seals rest on"): at the
# ship's north-west end, clear of its lane, sea stacks and leaning shards round a low flat rock
# that stands out of the water, where seals and a sea lion lie hauled out (posed still: the
# components have no resting pose of their own). Where exactly is Claude's pick.
func _build_outcrop(kit: Node3D) -> void:
	var site := _Site.new()
	var middle := OUTCROP
	# The island.
	var top := Sea.SURFACE + 1.1
	site.add("Islet", Transform3D(Basis(Vector3.UP, 0.4), Vector3(middle.x, top, middle.y)))
	var y := top - 26.0
	while y < top:
		var r := lerpf(5.0, 3.6, clampf((y - (top - 26.0)) / 24.0, 0.0, 1.0))
		Sea.add_rock(Vector4(middle.x, y, middle.y, r))
		y += 2.0
	# The stacks (some out of the water) and the shards round it.
	var stacks := [[Vector2(7.0, -7.0), 1.6], [Vector2(-8.0, -9.0), 1.2], [Vector2(9.0, 5.0), 0.9], [Vector2(-10.0, 4.0), 1.5],
			[Vector2(-2.0, -14.0), 0.8], [Vector2(3.0, 11.0), 1.1]]
	for each: Array in stacks:
		var at: Vector2 = middle + (each[0] as Vector2)
		if in_lane(at, Sea.PIRATE_AT, Sea.PIRATE_HEADING, PIRATE_LANE, 3.0):
			continue
		var foot := Sea.ground(at.x, at.y) - 0.5
		var tall: float = each[1]
		var wide := _rng.randf_range(0.9, 1.3)
		site.add("Pillar", Transform3D(Basis(Vector3.UP, _rng.randf() * TAU).scaled(Vector3(wide, tall, wide)), Vector3(at.x, foot, at.y)))
		var h := 0.0
		while h < 13.5 * tall:
			Sea.add_rock(Vector4(at.x, foot + h, at.y, 1.5 * wide * lerpf(1.0, 0.6, h / (14.0 * tall))))
			h += 1.6
	for k in 9:
		var turn := _rng.randf() * TAU
		var at: Vector2 = middle + Vector2.from_angle(_rng.randf() * TAU) * _rng.randf_range(6.0, 16.0)
		if in_lane(at, Sea.PIRATE_AT, Sea.PIRATE_HEADING, PIRATE_LANE, 3.0):
			continue
		var foot := Sea.ground(at.x, at.y) - 0.3
		var big := _rng.randf_range(0.8, 1.4)
		var where := Transform3D(Basis(Vector3.UP, turn).scaled(Vector3.ONE * big), Vector3(at.x, foot, at.y))
		site.add("Shard", where)
		for s: float in [0.15, 0.45, 0.75]:
			var p := where * Vector3(0.35 * 9.0 * s, 9.0 * s, 0.0)
			Sea.add_rock(Vector4(p.x, p.y, p.z, 1.1 * big * (1.0 - s * 0.7)))
	_draw_site(site, kit, "Outcrop")
	# The seals and a sea lion hauled out on it.
	for each: Array in [["harbor_seal/harbor_seal", Vector2(0.6, -0.4), 0.3, 0.0], ["harbor_seal/harbor_seal", Vector2(-1.2, 0.9), 2.2, 0.0],
			["harbor_seal/harbor_seal", Vector2(1.0, 1.6), 4.0, 0.0], ["sea_lion/sea_lion", Vector2(-3.0, -1.6), 1.0, -0.85]]:
		var path := "res://creatures/%s.gd" % each[0]
		if not ResourceLoader.exists(path):
			continue
		var animal: Node3D = (load(path) as GDScript).new()
		animal.set(&"game", true)
		animal.set(&"sway", 0.0)
		# (a seal hauled out lies in a curve, head and tail a little up)
		animal.set(&"arch", -0.25)
		animal.set(&"curl", _rng.randf_range(-0.4, 0.4))
		add_child(animal)
		var at: Vector2 = middle + (each[1] as Vector2)
		animal.global_position = Vector3(at.x, top + float(each[3]) + 0.22, at.y)
		animal.rotation.y = each[2]


# What one site of the docks has placed: transforms of each piece.
class _Site:
	var pieces := {}

	func add(piece: String, where: Transform3D) -> void:
		if not pieces.has(piece):
			pieces[piece] = []
		pieces[piece].append(where)


# A wharf running out from the shore (`from`, its first module's middle) to the north (-Z) or, with
# `south`, to the south: `modules` lengths of deck, piles under each cap beam and at the far end.
func _wharf(site: _Site, from: Vector2, modules: int, deck_y: float, south := false) -> void:
	var way := 4.0 if south else -4.0
	for k in modules:
		var middle := from + Vector2(0.0, way * k)
		site.add("Deck", Transform3D(Basis(), Vector3(middle.x, deck_y, middle.y)))
		var ends := [middle.y - 2.0]
		if south and k == modules - 1:
			ends.append(middle.y + 2.0)
		for z: float in ends:
			for x: float in [-3.5, 0.0, 3.5]:
				_pile(site, Vector2(middle.x + x, z), deck_y - PILE_DOWN)
		# (and a pile at the shore end)
		if k == 0 and not south:
			for x: float in [-3.5, 0.0, 3.5]:
				_pile(site, Vector2(middle.x + x, middle.y + 2.0), deck_y - PILE_DOWN)


# A pile with its top at a height: drawn, and a column of spheres where it stands in the water.
func _pile(site: _Site, at: Vector2, top: float) -> void:
	var turn := _rng.randf() * TAU
	site.add("Piling", Transform3D(Basis(Vector3.UP, turn), Vector3(at.x, top, at.y)))
	var y := maxf(Sea.ground(at.x, at.y), top - 12.0) + 0.3
	while y < Sea.SURFACE + 0.5:
		Sea.add_rock(Vector4(at.x, y, at.y, 0.42))
		y += 0.9


# A piece of litter lying on the floor, turned any way.
func _litter(site: _Site, piece: String, at: Vector2) -> void:
	site.add(piece, Transform3D(Basis(Vector3.UP, _rng.randf() * TAU), Vector3(at.x, Sea.ground(at.x, at.y) - 0.04, at.y)))


# A floating dock module, its length along a turn, and the spheres of its floats.
func _float(site: _Site, at: Vector2, turn: float) -> void:
	site.add("Float", Transform3D(Basis(Vector3.UP, turn), Vector3(at.x, Sea.SURFACE, at.y)))
	var along := Vector2(sin(turn), cos(turn))
	for s: float in [-3.0, -1.5, 0.0, 1.5, 3.0]:
		var p := at + along * s
		Sea.add_rock(Vector4(p.x, Sea.SURFACE - 0.05, p.y, 0.85))


# A moored boat (the docks' sailboat or the gear's skiff), bow along a turn, and its hull's spheres.
func _boat(site: _Site, piece: String, at: Vector2, turn: float) -> void:
	site.add(piece, Transform3D(Basis(Vector3.UP, turn), Vector3(at.x, Sea.SURFACE, at.y)))
	var along := Vector2(-sin(turn), -cos(turn))
	var hull := [[-3.0, 1.1], [-1.2, 1.4], [0.8, 1.4], [2.8, 1.2]] if piece == "Sailboat" else [[-1.2, 0.8], [0.8, 0.8]]
	for each: Array in hull:
		var p := at + along * float(each[0])
		Sea.add_rock(Vector4(p.x, Sea.SURFACE - 0.35, p.y, float(each[1])))
	if piece == "Sailboat":
		Sea.add_rock(Vector4(at.x, Sea.SURFACE - 1.4, at.y, 0.55))


# A site drawn: one MultiMesh a piece, hidden beyond DOCKS_SEEN.
func _draw_site(site: _Site, kit: Node3D, label: String) -> void:
	var skiff: MeshInstance3D = null
	if site.pieces.has("Skiff") and ResourceLoader.exists(GEAR):
		var gear: Node3D = (load(GEAR) as PackedScene).instantiate()
		skiff = gear.find_child("Skiff", true, false) as MeshInstance3D
		if skiff:
			skiff = skiff.duplicate() as MeshInstance3D
		gear.free()
	for piece: String in site.pieces:
		var source := skiff if piece == "Skiff" else kit.find_child(piece, true, false) as MeshInstance3D
		if source == null:
			continue
		var wheres: Array = site.pieces[piece]
		var many := MultiMesh.new()
		many.transform_format = MultiMesh.TRANSFORM_3D
		many.mesh = source.mesh
		many.instance_count = wheres.size()
		for i in wheres.size():
			many.set_instance_transform(i, wheres[i])
		var drawn := MultiMeshInstance3D.new()
		drawn.name = "%s%s" % [label, piece]
		drawn.multimesh = many
		drawn.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		drawn.visibility_range_end = DOCKS_SEEN
		add_child(drawn)
	if skiff:
		skiff.free()


# The moored trawler: the title's shrimp boat (models/shrimp_boat.glb, used as it is), alongside the
# commercial wharf, and its hull's spheres.
func _trawler(at: Vector3, turn: float) -> void:
	if not ResourceLoader.exists(TRAWLER):
		return
	var boat: Node3D = (load(TRAWLER) as PackedScene).instantiate()
	boat.name = "MooredTrawler"
	add_child(boat)
	boat.global_position = at
	boat.rotation.y = turn
	for node in boat.find_children("*", "GeometryInstance3D", true, false):
		(node as GeometryInstance3D).visibility_range_end = DOCKS_SEEN
	var along := Vector2(-sin(turn), -cos(turn))
	for s: float in [-5.0, -2.5, 0.0, 2.5, 5.0]:
		var p := Vector2(at.x, at.z) + along * s
		Sea.add_rock(Vector4(p.x, Sea.SURFACE - 0.6, p.y, 1.9))


# ------------------------------------------------------------------------------------- the landmarks

# The liner, Atlantis and the pirate ship (other agents' nodes), where Sea says, if they are there.
func _add_landmarks() -> void:
	for each: Array in [[WRECK, Sea.WRECK_AT, Sea.WRECK_HEADING], [RUINS, Sea.RUINS_AT, Sea.RUINS_HEADING], [PIRATE, Sea.PIRATE_AT, Sea.PIRATE_HEADING]]:
		if not ResourceLoader.exists(each[0]):
			continue
		var made: Node3D = (load(each[0]) as GDScript).new()
		made.position = each[1]
		made.rotation.y = each[2]
		add_child(made)
