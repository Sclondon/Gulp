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
## The garden eel colonies, all in the dune sea (BiomeRegions DUNES): each a band across the current
## (its two ends, world) and how many eels. (The old ridge off Santa Cruz and the small colony by the
## liner, moved into the dunes 2026-11-18.)
const EEL_COLONIES := [[[Vector2(-50.0, -98.0), Vector2(-42.0, -76.0)], 110], [[Vector2(2.0, -82.0), Vector2(8.0, -62.0)], 100],
		[[Vector2(-112.0, 128.0), Vector2(-104.0, 150.0)], 50]]
## The dune sea's anchors: where (world), how big, which way.
const DUNE_ANCHORS := [[Vector2(-28.0, -88.0), 2.2, 0.6], [Vector2(-78.0, -92.0), 1.6, 2.1]]
## How long a garden eel counts as for the eating rule (m), and how long one stays gone (s).
const EEL_LENGTH := 0.6
const EEL_BACK := 25.0
## Beyond this the water hides plants (m), and docks and moored boats.
const SEEN := 60.0
const DOCKS_SEEN := 80.0
## The eelgrass fields' tufts per square metre, as a multiple of SeaGrassBed's quality (1.8: 7.2 a square
## metre at MEDIUM, a little under what the placer's clumps came to in a meadow's core). How far the grass
## is drawn (40 m at MEDIUM, thinning from 14 m and sinking into the floor towards the end) is the quality's.
const GRASS_DENSITY := 1.8
## The share of the eelgrass tufts a phone draws (its grass quality is the sand's: the lowest).
const PHONE_GRASS := 0.8
## How many fish nearest the player lay the grass aside besides it, and within how far of it (m).
const GRASS_FISH := 3
const GRASS_FISH_NEAR := 12.0
## The giant kelp's levels (KelpForest): full pieces within KELP_NEAR of the eye, the light piece to
## KELP_MID, beyond it 24 m blocks of the light piece stretched KELP_FAR_PIECE m long, none past SEEN (m).
const KELP_NEAR := 5.0
const KELP_MID := 15.0
const KELP_FAR_PIECE := 4.0
## The giant kelp's colours and other settings (kelp.gdshader's), after Monterey photographs and concept_biome_kelp.png.
const KELP_COLOURS := [[&"blade", Color(0.27, 0.16, 0.05)], [&"blade_amber", Color(0.5, 0.28, 0.07)],
		[&"blade_lit", Color(0.92, 0.6, 0.2)], [&"bulb", Color(0.4, 0.27, 0.08)], [&"stipe", Color(0.18, 0.11, 0.04)],
		# (blades within 1.6 m of the camera dither away: a camera following the fish through the groves is not blinded)
		[&"eye_clear", 1.6]]
## The tint the outcrops' stacks and shards wear on the kit's rock.
const CRAG_ROCK := Color(0.32, 0.3, 0.3)
## The kit's pieces (rocks, cliffs, the reef's life): full models within PIECES_NEAR of the eye,
## light ones out to PIECES_SEEN, none beyond (m, to the nearest edge of the piece's cube).
const PIECES_NEAR := 8.0
const PIECES_SEEN := 60.0
## Growth on the set pieces and the outcrop: full models only this near (m).
const GROWTH_NEAR := 4.0
## How many drift kelp paddies float over the open ocean.
const RAFTS := 4
## The clear lanes kept for the wrecks' hulls (long, wide: m, along their headings).
const WRECK_LANE := Vector2(64.0, 14.0)
const PIRATE_LANE := Vector2(34.0, 12.0)
## How high a wharf's deck stands over the water (m), and how far under its top the piles stand.
const DECK_UP := 0.9
const PILE_DOWN := 0.7
## Where the two docks are (world): the middles of the docks zone's two patches.
const MONTEREY := Vector2(66.0, 68.0)
const SANTA_CRUZ := Vector2(3.0, -123.0)
## The outcrop the pirate ship struck, and its island (world).
const OUTCROP := Vector2(-93.0, -52.0)
## A second rocky islet, south-south-west of the pirate ship (no seals on it).
const OUTCROP_SOUTH := Vector2(-74.0, -14.0)
## The south kelp forest's landmark: the arch across its main channel (world x, z; BIOMES.md 5.2).
const ARCH := Vector2(42.4, 48.6)
## Where Carmel's pier starts at the shore (world; it runs north, BIOMES.md 5.12).
const CARMEL_PIER := Vector2(22.4, 111.2)
const OLD_ONE := "res://creatures/old_one/old_one.gd"
const REEF_BACK := "res://creatures/reef_back/reef_back.gd"
## Where the old one lies asleep (world x, z: the canyon's deep floor north-east of Atlantis, 85 m).
const OLD_ONE_AT := Vector2(10.0, -38.0)
## The reef back's loop on the deep floor past the shelf's edge (middle x, z; radius), and its pace (m/s).
const REEF_BACK_LOOP := Vector3(-90.0, 40.0, 15.0)
const REEF_BACK_PACE := 0.45
## Beyond this the two giants are their light models (m).
const GIANT_LOW := 60.0
## The old one and the reef-back are put in the sea (off: they wait for the special conditions that
## call the sea monsters up; Species `monster` holds the swimming ones back the same way).
const MONSTERS := false
## The old wall of cliff pieces along the drawn map's shelf edge (off: the real floor has its own).
const CLIFF_WALL := false

## Who lays the grass aside and frightens the eels (the player).
var player: Player
## The animals (the nearest few to the player lay the grass aside too).
var life: Life

# The eelgrass fields (SeaGrassBed), one a grass layer of the biomes.
var _grass: Array[Node3D] = []
var _eels: Node3D
var _colonies: Array[Dictionary] = []
var _props: GDScript
var _rng := RandomNumberGenerator.new()
# What has been placed of each piece: name -> [transforms, colours].
var _placed := {}
var _clock := 0.0
# The rule-based placer's output (scripts/biomes.gd).
var _biomes: Biomes
# Where the piles stand (their feet get a ring of shell hash on the floor).
var _shell_spots: Array[Vector2] = []
var _old_one: Node3D
var _reef_back: Node3D
var _reef_turn := 0.0
# The set pieces (by script path), and the spheres of the outcrop's islet, stacks and shards.
var _landmarks := {}
var _outcrop_spheres: Array = []


func _ready() -> void:
	_rng.seed = 11
	if ResourceLoader.exists(PROPS):
		# (GameCommon's sea floor kit and the sea's own pieces: scripts/kit.gd)
		_props = Kit
	_place_biomes()
	if _props:
		_place_reef()
		# (no wall of cliffs along the shelf's edge since the floor is the real bay's: its shelf break
		# is a slope of its own, and the "walls" biome puts rock on whatever is steep)
		if CLIFF_WALL:
			_place_cliffs()
		_place_breakwater()
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
	if _props:
		_grow_on_structures()
		_draw_pieces()
	_add_giants()


func _process(delta: float) -> void:
	_clock += delta
	_walk_giants(delta)
	if player == null:
		return
	if not _grass.is_empty():
		_push_grass()
	var eye := get_viewport().get_camera_3d()
	for colony: Dictionary in _colonies:
		var eels: Node3D = colony.node
		# (one draw of all of them, which nothing hid however far off: tools/PERF.md)
		if eye:
			eels.visible = Vector2(eye.global_position.x, eye.global_position.z).distance_to(colony.at) < float(colony.r) + SEEN
		if not player.alive:
			continue
		var at := player.global_position
		if Vector2(at.x, at.z).distance_to(colony.at) > float(colony.r) + 10.0:
			continue
		eels.call(&"disturb", at, 1.6 + player.length * 2.5)
		var mouth := player.mouth()
		var i: int = eels.call(&"nearest", mouth)
		var eaten: Dictionary = colony.eaten
		if i >= 0 and Life.is_food(player.length, EEL_LENGTH):
			var head: Vector3 = eels.call(&"head_of", i)
			if head.distance_to(mouth) < player.length * 0.3 + 0.06:
				eels.call(&"take", i)
				eaten[i] = _clock + EEL_BACK
				player.feed(EEL_LENGTH, 0.5)
		for gone: int in eaten.keys():
			if _clock > float(eaten[gone]):
				eaten.erase(gone)
				eels.call(&"restore", gone)


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
	# (a zone that is one of the user's drawn biomes: anywhere in it, in from its edge)
	if Sea.ZONES[zone].has("region"):
		return BiomeRegions.spot(_rng, Sea.ZONES[zone].region, 3.0 + 6.0 * (1.0 - share))
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
			or (ResourceLoader.exists(RUINS) and bool((load(RUINS) as GDScript).call(&"covers", at, margin)))


# The places' plants and floor pieces by rule (scripts/biomes.gd, tools/BIOMES.md): the kelp
# forests' rock reefs with their channels and barren, the outcrop's talus, the rocky points, the
# canyons' rock bands, the eelgrass, the slough, the harbours. The floor pieces join `_placed`
# (drawn by the LodField); kelp, grass and seaweed are planted from `_biomes` below. The south
# forest's landmark, the arch, stands across its main channel, its opening along the channel.
func _place_biomes() -> void:
	_biomes = Biomes.new()
	_biomes.run(_props, _kept_clear)
	if _props:
		_biomes.add_piece("rock_arch", Transform3D(Basis(Vector3.UP, PI * 0.5).scaled(Vector3.ONE * 1.2), Vector3(ARCH.x, Sea.ground(ARCH.x, ARCH.y) - 0.3, ARCH.y)))
		for piece: String in _biomes.pieces:
			if not _placed.has(piece):
				_placed[piece] = [[], []]
			_placed[piece][0].append_array(_biomes.pieces[piece][0])
			_placed[piece][1].append_array(_biomes.pieces[piece][1])
		_biomes.pieces.clear()


# The liner's reef (BIOMES.md 5.9): coral heads (bommies) on the sand round the wreck, thick near
# the hull and thinning out to 30 m, a rubble of red weed between; the corals, fans, sponges and
# clams grow on the bommies (lit tops: hard corals and clams; sides: fans, soft corals, sponges),
# not on the open sand. The lane where the hull lies is kept clear (the wreck grows its own reef).
func _place_reef() -> void:
	var heads: PackedStringArray = _props.call(&"names", "bommie")
	var middle := Vector2(Sea.WRECK_AT.x, Sea.WRECK_AT.z)
	var placed := 0
	var tries := 0
	var growth := Biomes.new()
	growth._props = _props
	growth._rng.seed = 77
	while placed < 26 and tries < 2000:
		tries += 1
		var at := middle + Vector2.from_angle(_rng.randf() * TAU) * _rng.randf_range(6.0, 32.0)
		var out := at.distance_to(middle)
		if _rng.randf() > lerpf(1.0, 0.12, inverse_lerp(8.0, 32.0, out)):
			continue
		var deep := Sea.SURFACE - Sea.ground(at.x, at.y)
		if deep < 18.0 or deep > 38.0 or FloorTypes.slope(at.x, at.y) > 0.4 or in_lane(at, Sea.WRECK_AT, Sea.WRECK_HEADING, WRECK_LANE, 4.0):
			continue
		var piece := heads[_rng.randi() % heads.size()]
		var where := _stand(piece, at, _rng.randf() * TAU, _rng.randf_range(0.9, 1.5), Color.WHITE, -0.3)
		var spheres: Array = []
		for s: Vector4 in _props.call(&"spheres_of", piece):
			var m := where * Vector3(s.x, s.y, s.z)
			spheres.append(Vector4(m.x, m.y, m.z, s.w * where.basis.get_scale().x))
		growth.grow_on(spheres, ["brain_coral", "table_coral", "staghorn_coral", "pillar_coral", "giant_clam"], 4, 0.55, 1.0, Vector2(0.7, 1.3))
		growth.grow_on(spheres, ["sea_fan_purple", "soft_coral", "sea_rods", "barrel_sponge"], 4, -0.2, 0.55, Vector2(0.7, 1.3))
		placed += 1
	for piece: String in growth.pieces:
		if not _placed.has(piece):
			_placed[piece] = [[], []]
		_placed[piece][0].append_array(growth.pieces[piece][0])
		_placed[piece][1].append_array(growth.pieces[piece][1])


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
#
# (Drawn by a LodField, tools/PERF.md: the full models near the eye, the light ones further off,
# none beyond PIECES_SEEN, where the water has long hidden them. Cliffs are light everywhere.)
func _draw_pieces() -> void:
	var field := LodField.new()
	field.name = "Pieces"
	field.near = PIECES_NEAR
	field.far = PIECES_SEEN
	for piece: String in _placed:
		var light: Mesh = _props.call(&"mesh_of", piece, true)
		var full: Mesh = light if piece.begins_with("cliff") else _props.call(&"mesh_of", piece, false)
		field.add(piece, full, light, _props.call(&"material_of", piece), _placed[piece][0], _placed[piece][1],
				(_props.call(&"size_of", piece) as Vector3).length() * 0.5)
	add_child(field)


# The kelp forests, by the placer's rules (BIOMES.md 5.2, 5.3): on rock only, thick at the core and
# thinning to the edge, each reaching for the surface (the longest lie along it as canopy).
func _plant_kelp() -> void:
	var forest: Node3D = (load(KELP) as GDScript).new()
	var phone := Tier.phone()
	# (a phone: the full pieces nearer, the light ones not as far, nothing past 50 m; CLAUDE.md, "Decision: a phone tier")
	forest.set(&"far", 50.0 if phone else SEEN)
	# (blocks of 12 m, not 8: half the draws in a forest, a few more full pieces near the eye; tools/BIOMES.md budget)
	forest.set(&"cell", 12.0)
	# (the dense forest's three levels, tools/BIOMES.md "The dense kelp": full pieces within KELP_NEAR, the
	# light piece to KELP_MID, then 24 m blocks of the light piece stretched KELP_FAR_PIECE m long)
	forest.set(&"near", KELP_NEAR * (0.7 if phone else 1.0))
	forest.set(&"mid", KELP_MID * (0.7 if phone else 1.0))
	forest.set(&"far_cell", 24.0)
	forest.set(&"far_piece", KELP_FAR_PIECE)
	forest.set(&"current", Vector2(0.3, 0.1))
	add_child(forest)
	# (the photographs' and the concept's colours: amber and golden olive, dark brown in shade, glowing where lit)
	for setting: Array in KELP_COLOURS:
		forest.call(&"set_shader_parameter", setting[0], setting[1])
	forest.call(&"plant", _biomes.kelp_places, _biomes.kelp_lengths, Sea.SURFACE, _biomes.kelp_widths)


# The sea grass, by the placer's rules (BIOMES.md 5.8 and 5.14): the meadows of the grass biome,
# thick at their core with bare blowouts and sandy paths, and eelgrass on the river's banks and
# mouth. Each grass layer is a SeaGrassBed field over its place (GameCommon sea-grass, Warren's way
# of spawning grass): its squares are filled with tufts by the layer's rules only as the eye nears,
# a little a frame, thinning with distance and sinking into the floor where it ends.
func _plant_grass() -> void:
	var bed := load(GRASS) as GDScript
	# (the quality follows the sand's: a phone or a browser 1, a desktop 2, a slow phone 0)
	bed.call(&"set_quality", clampi(Sand.quality, 0, 2))
	var floor_at := func(p: Vector2) -> float: return Sea.ground(p.x, p.y)
	for one: Dictionary in _biomes.grass_fields():
		# (a phone: fewer tufts, PHONE_GRASS of them; CLAUDE.md, "Decision: a phone tier")
		var made: Node3D = bed.call(&"field", self, one.area, GRASS_DENSITY * (PHONE_GRASS if Tier.phone() else 1.0), {
			"mask": one.mask, "height": floor_at, "tall": one.tall,
			# (squares of 12 m: about half the draws of 8 over a thick meadow)
			"cell": 12.0,
			# (leaning well over in the current, as the concept's meadow does: concept_biome_grass.png)
			"current": Vector2(0.55, 0.18),
			"seed": 1 + _grass.size()})
		# (the concept's olive and straw eelgrass, not the component's spring green)
		made.call(&"set_shader_parameter", &"grass_deep", Color(0.15, 0.25, 0.08))
		made.call(&"set_shader_parameter", &"grass_bright", Color(0.36, 0.5, 0.15))
		made.call(&"set_shader_parameter", &"tip_pale", Color(0.78, 0.74, 0.38))
		made.call(&"set_shader_parameter", &"grass_lit", Color(0.7, 0.78, 0.34))
		_grass.append(made)


## Fills the eelgrass within `radius` of `point` now (before a picture is taken, or where a run begins).
func fill_grass_near(point: Vector3, radius: float) -> void:
	for field: Node3D in _grass:
		field.call(&"fill_near", point, radius)


# The player and the few fish nearest it lay the eelgrass aside (each by its size).
func _push_grass() -> void:
	var at := player.global_position
	var points := PackedVector4Array([Vector4(at.x, at.y, at.z, maxf(0.7, player.length * 0.5))])
	if life != null:
		var near: Array = []
		for one: Creature in life.awake:
			var gap := one.global_position.distance_squared_to(at)
			if gap < GRASS_FISH_NEAR * GRASS_FISH_NEAR and one.visible:
				near.append([gap, one])
		near.sort_custom(func(a: Array, b: Array) -> bool: return a[0] < b[0])
		for k in mini(near.size(), GRASS_FISH):
			var fish: Creature = near[k][1]
			var p := fish.global_position
			points.append(Vector4(p.x, p.y, p.z, maxf(0.4, fish.length * 0.5)))
	for field: Node3D in _grass:
		field.call(&"set_pushers", points)


# Seaweed: the placer's (understory, red weed, feather boa on the reefs; rockweed on the rocky
# points and the breakwater; sea lettuce on the meadow, the slough and the harbour floors), and
# here red weed on the liner's shelf round its bommies and a few mats of sargassum afloat over the
# open ocean (BIOMES.md 4: sargassum is Atlantic; the open's drifting things are kelp rafts,
# `_place_rafts`; Claude's default for the user's question 5).
func _plant_seaweed() -> void:
	# The open ocean's drift kelp paddies (BIOMES.md 5.13, kit item 10): RAFTS of them afloat where the
	# water is over 30 m deep. They lie still (the design's slow drift is not done).
	if _props and Kit.exists("kelp_raft"):
		var made := 0
		var tries := 0
		while made < RAFTS and tries < 200:
			tries += 1
			var at := _in_zone("open", 0.9)
			if Sea.SURFACE - Sea.ground(at.x, at.y) < 30.0:
				continue
			_add_placed("kelp_raft", Transform3D(Basis(Vector3.UP, _rng.randf() * TAU).scaled(Vector3.ONE * _rng.randf_range(0.8, 1.2)),
					Vector3(at.x, Sea.SURFACE - 0.08, at.y)))
			made += 1
	var places := _biomes.weed_places
	var sizes := _biomes.weed_sizes
	var kinds := _biomes.weed_kinds
	for row: Array in [[2, "reef", 120, 0.16, 0.32], [5, "open", 3, 1.2, 1.8]]:
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
	bed.set(&"cell", 12.0)
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
			# (drawn from its baked paint: tools/bake_looks.gd -- --plan=res://tools/bake_scenery.json)
			BakedLook.apply(one)
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
		# (its game model: the full one is left out of the web pack, which could not load it, and is
		# 13,800 triangles against 2,540)
		home.set(&"game", true)
		BakedLook.apply(home)
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
				var p := at + across * side * _rng.randf_range(Bay.SLOUGH_HALF * Bay.K - 2.5, Bay.SLOUGH_HALF * Bay.K + 2.0)
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
	# The colonies, all in the dune sea now (BiomeRegions DUNES; the old ridge off Santa Cruz and the small
	# colony by the liner moved into it, 2026-11-18): each a band across the current over the dunes'
	# sand, its eels on clean sand only.
	for colony: Array in EEL_COLONIES:
		var ends: Array = colony[0]
		var places := PackedVector3Array()
		var tries := 0
		while places.size() < int(colony[1]) and tries < int(colony[1]) * 20:
			tries += 1
			var along: Vector2 = (ends[0] as Vector2).lerp(ends[1], _rng.randf())
			var at := along + Vector2.from_angle(_rng.randf() * TAU) * _rng.randf_range(0.0, 3.4) * Vector2(1.0, 0.6)
			if BiomeRegions.at(at.x, at.y) != BiomeRegions.DUNES or FloorTypes.of(at.x, at.y) != FloorTypes.SAND or _kept_clear(at, 3.0):
				continue
			places.append(Vector3(at.x, Sea.ground(at.x, at.y), at.y))
		var middle: Vector2 = (ends[0] as Vector2).lerp(ends[1], 0.5)
		_add_colony(places, middle, (ends[0] as Vector2).distance_to(ends[1]) * 0.5 + 4.0)


# The dune sea's litter (concept_biome_dunes.png): an old anchor half sunk in the sand on a dune's back,
# its chain trailing off down the slope in a curve; a second, smaller, further west. The docks' Anchor
# and Chain pieces, scaled up (the concept's anchor stands taller than a diver). Nothing else (the dune
# sea is open and bare).
func _build_dune_litter(kit: Node3D) -> void:
	for n in DUNE_ANCHORS.size():
		var each: Array = DUNE_ANCHORS[n]
		# (a site each, hidden beyond SEEN: one box round both was drawn from the far side of the map)
		var site := _Site.new()
		var at: Vector2 = each[0]
		var big: float = each[1]
		var turn: float = each[2]
		var floor_y := Sea.ground(at.x, at.y)
		# (stood up on its crown, leaning, the shank and stock out of the sand: the anchor lies along its
		# own Z, so it is tipped up about X; half of it under the sand)
		var basis := Basis(Vector3.UP, turn) * Basis(Vector3.RIGHT, 1.1) * Basis(Vector3.FORWARD, 0.25)
		var where := Transform3D(basis.scaled(Vector3.ONE * big), Vector3(at.x, floor_y + 0.45 * big, at.y))
		site.add("Anchor", where)
		Sea.add_rock(Vector4(at.x, floor_y + 0.4 * big, at.y, 0.35 * big))
		# The chain: three runs from under the ring, end to end, wandering over the sand.
		var from := Vector2((where * Vector3(0.0, 0.08, -0.82)).x, (where * Vector3(0.0, 0.08, -0.82)).z)
		var heading := turn + PI * 0.5
		for k in 3:
			var chain_at := from
			var foot := Sea.ground(chain_at.x, chain_at.y) - 0.06 * big
			site.add("Chain", Transform3D(Basis(Vector3.UP, heading).scaled(Vector3.ONE * big * 0.8), Vector3(chain_at.x, foot, chain_at.y)))
			from += Vector2(cos(-heading), sin(-heading)) * 3.6 * big * 0.8 * 0.95
			heading += _rng.randf_range(-0.5, 0.5)
		_draw_site(site, kit, "Dunes%d" % n, SEEN)


func _add_colony(places: PackedVector3Array, middle: Vector2, radius: float) -> void:
	if places.is_empty():
		return
	var colony: Node3D = (load(EELS) as GDScript).new()
	# (into the current, which runs in from the sea)
	colony.set(&"facing", Vector3(-1.0, 0.0, 0.3).normalized())
	colony.set(&"eel_scale", 1.5)
	add_child(colony)
	colony.call(&"plant", places)
	_colonies.append({"node": colony, "at": middle, "r": radius, "eaten": {}})
	if _eels == null:
		_eels = colony


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
	# Carmel (the user: "the fish markets should be at monteray, santa cruz, and carmel"): a short
	# wooden pier out into the cove dredged off Carmel Beach (Bay.HARBOURS), two skiffs at it, after
	# the small pier at Stillwater Cove (Claude's default, BIOMES.md 5.12). The fish shed is not built.
	site = _Site.new()
	# (the cove opens to the south: the pier runs out that way)
	_wharf(site, CARMEL_PIER, 3, deck_y, true)
	_boat(site, "Skiff", CARMEL_PIER + Vector2(-5.0, 4.0), 0.4)
	_boat(site, "Skiff", CARMEL_PIER + Vector2(5.5, 6.0), -0.3)
	_litter(site, "CrabPot", CARMEL_PIER + Vector2(-3.0, 7.0))
	_draw_site(site, kit, "Carmel")
	_build_outcrop(kit, OUTCROP, "Outcrop", 0.4, true)
	# (and a second, smaller and without seals, south-south-west of the ship: the user, 2026-11-18, "lets add
	# another rocky outcrop island just south south west of the pirate ship to fill in that empty spot")
	_build_outcrop(kit, OUTCROP_SOUTH, "OutcropSouth", 2.1, false)
	_build_dune_litter(kit)
	_paint_shells()
	kit.free()


# The outcrop the pirate ship struck (the user, 2026-11-18: "there shoule be an outcropping of
# rocks near the pirate ship, pillars and shards and an island that seals rest on"): at the
# ship's north-west end, clear of its lane, sea stacks and leaning shards round a low flat rock
# that stands out of the water, where seals and a sea lion lie hauled out (posed still: the
# components have no resting pose of their own). Where exactly is Claude's pick.
func _build_outcrop(kit: Node3D, middle: Vector2, label: String, turn_islet: float, seals: bool) -> void:
	var site := _Site.new()
	# The island.
	var top := Sea.SURFACE + 1.1
	site.add("Islet", Transform3D(Basis(Vector3.UP, turn_islet), Vector3(middle.x, top, middle.y)))
	var y := top - 26.0
	while y < top:
		var r := lerpf(5.0, 3.6, clampf((y - (top - 26.0)) / 24.0, 0.0, 1.0))
		Sea.add_rock(Vector4(middle.x, y, middle.y, r))
		_outcrop_spheres.append(Vector4(middle.x, y, middle.y, r))
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
			var stack := Vector4(at.x, foot + h, at.y, 1.5 * wide * lerpf(1.0, 0.6, h / (14.0 * tall)))
			Sea.add_rock(stack)
			_outcrop_spheres.append(stack)
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
			_outcrop_spheres.append(Vector4(p.x, p.y, p.z, 1.1 * big * (1.0 - s * 0.7)))
	_draw_site(site, kit, label)
	if not seals:
		return
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
		BakedLook.apply(animal)
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
	_grow_on_pile(at, top < Sea.SURFACE + 1.0)


# What grows on a pile, in bands (BIOMES.md 5.10): mussel clumps hanging just under the surface,
# below them anemones down to the floor (strawberry anemones on the shaded piles under a deck,
# plumose-like green ones on the lit mooring piles), a sea star at its foot. Drawn with the rest of
# the floor pieces (near and far).
func _grow_on_pile(at: Vector2, shaded: bool) -> void:
	if _props == null:
		return
	var floor_y := Sea.ground(at.x, at.y)
	for k in 3:
		var turn := _rng.randf() * TAU + k * TAU / 3.0
		var out := Vector3(sin(turn), 0.0, cos(turn))
		var y := Sea.SURFACE - _rng.randf_range(0.25, 1.3)
		if y < floor_y + 0.3:
			continue
		# (hanging off the pile's side, its top against the wood)
		var basis := Basis(out.cross(Vector3.UP).normalized(), out, Vector3.UP.cross(out.cross(Vector3.UP).normalized())).orthonormalized()
		_add_placed("mussel_clump", Transform3D(basis.scaled(Vector3.ONE * _rng.randf_range(0.9, 1.3)), Vector3(at.x, y, at.y) + out * 0.36))
	var low := "strawberry_anemones" if shaded else "green_anemone"
	var y2 := lerpf(floor_y + 0.5, Sea.SURFACE - 1.6, _rng.randf())
	if y2 > floor_y + 0.3:
		var turn2 := _rng.randf() * TAU
		var out2 := Vector3(sin(turn2), 0.0, cos(turn2))
		var basis2 := Basis(out2.cross(Vector3.UP).normalized(), out2, Vector3.UP.cross(out2.cross(Vector3.UP).normalized())).orthonormalized()
		_add_placed(low, Transform3D(basis2, Vector3(at.x, y2, at.y) + out2 * 0.4))
	if _rng.randf() < 0.5:
		var star := "ochre_star" if _rng.randf() < 0.6 else "bat_star"
		var foot := at + Vector2.from_angle(_rng.randf() * TAU) * 0.6
		_add_placed(star, Transform3D(Basis(Vector3.UP, _rng.randf() * TAU), Vector3(foot.x, Sea.ground(foot.x, foot.y) - 0.01, foot.y)))
	_shell_spots.append(at)


# The rings of shell hash round the piles' feet, painted on the sea's sand (FloorTypes: COARSE).
func _paint_shells() -> void:
	for node in get_parent().get_children():
		if node is Sea and (node as Sea).sand:
			for at in _shell_spots:
				(node as Sea).sand.paint(Sand.Kind.COARSE, at, 0.9, 1.0, 0.8)


# A floor piece added to what the LodField draws, in one of its tints (no spheres: it is small).
func _add_placed(piece: String, where: Transform3D) -> void:
	if not _placed.has(piece):
		_placed[piece] = [[], []]
	_placed[piece][0].append(where)
	_placed[piece][1].append(_tint(piece))


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
func _draw_site(site: _Site, kit: Node3D, label: String, seen := DOCKS_SEEN) -> void:
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
		# (the outcrops' stacks and shards wear the sea floor kit's rock, tinted dark, as the crags' own
		# pinnacles round them do: concept_biome_crags.png; their plain docks paint drew pale and flat)
		var kit_rock := _props != null and (piece == "Pillar" or piece == "Shard")
		many.use_colors = kit_rock
		many.instance_count = wheres.size()
		for i in wheres.size():
			many.set_instance_transform(i, wheres[i])
			if kit_rock:
				many.set_instance_color(i, CRAG_ROCK)
		var drawn := MultiMeshInstance3D.new()
		drawn.name = "%s%s" % [label, piece]
		drawn.multimesh = many
		if kit_rock:
			drawn.material_override = SeaFloorProps.material("rock")
		drawn.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		drawn.visibility_range_end = seen
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

## What grows on structures by which way a face looks (BIOMES.md 3.4): [up, side, under] lists of
## the kit's pieces, cold water (the outcrop, the pirate ship, Atlantis) and the liner's warm pocket.
const COLD_UP := ["ochre_star", "bat_star", "puffball_sponges", "vase_sponge"]
const COLD_UP_SHALLOW := ["green_anemone", "ochre_star", "urchin_purple"]
const COLD_SIDE := ["hydrocoral", "sea_fan_gold", "vase_sponge", "puffball_sponges", "sea_fan_red"]
const COLD_UNDER := ["strawberry_anemones", "puffball_sponges"]
const WARM_UP := ["table_coral", "pillar_coral", "giant_clam", "table_coral"]
const WARM_SIDE := ["sea_rods", "barrel_sponge", "sea_fan_purple"]
const WARM_UNDER := ["puffball_sponges"]


# Growth by rule on the structures that were bare of it (BIOMES.md 3.4, second pass 2026-11-18):
# the liner's hull and decks, the pirate ship, Atlantis's stones, the outcrop's stacks, shards and
# seal rock. Placed on each one's collision spheres by which way the face looks and how deep it is,
# thickest high up and on the faces the current runs onto, and never within a swim route's room
# (each set piece's own routes; growth adds no rocks, so the routes' checks are untouched). How many
# of each is Claude's pick, held down where the place is already dear (the liner: tools/PERF.md).
func _grow_on_structures() -> void:
	var growth := Biomes.new()
	growth._props = _props
	growth._rng.seed = 91
	var liner: Node3D = _landmarks.get(WRECK)
	if liner and liner.has_method(&"spheres"):
		var routes: Array = liner.call(&"routes")
		var off_route := func(at: Vector3) -> bool:
			for route: Dictionary in routes:
				var points: PackedVector3Array = route.points
				for i in points.size() - 1:
					if Geometry3D.get_closest_point_to_segment(at, points[i], points[i + 1]).distance_to(at) < float(route.room) + 1.2:
						return true
			return false
		var hull := Biomes.skin_of(liner)
		growth.grow_on_skin(hull, WARM_UP, 30, 0.6, 1.0, Vector2(0.6, 1.1), Vector2(0.3, 999.0), off_route)
		growth.grow_on_skin(hull, WARM_SIDE, 30, -0.3, 0.6, Vector2(0.6, 1.2), Vector2(0.3, 999.0), off_route)
		growth.grow_on_skin(hull, WARM_UNDER, 10, -1.0, -0.3, Vector2(0.6, 1.0), Vector2(0.3, 999.0), off_route)
	var pirate: Node3D = _landmarks.get(PIRATE)
	if pirate:
		var checks: Array = pirate.call(&"route_checks") if pirate.has_method(&"route_checks") else []
		var off_route := func(at: Vector3) -> bool:
			for c: Vector4 in checks:
				if Vector3(c.x, c.y, c.z).distance_to(at) < c.w + 1.2:
					return true
			return false
		var hull := Biomes.skin_of(pirate)
		# (a cold wreck: plumose-like white and orange growth on her high points, sponges and fans on her sides)
		growth.grow_on_skin(hull, COLD_UP, 100, 0.6, 1.0, Vector2(1.3, 2.2), Vector2(0.3, 999.0), off_route)
		growth.grow_on_skin(hull, COLD_SIDE, 120, -0.3, 0.6, Vector2(1.3, 2.3), Vector2(0.3, 999.0), off_route)
		growth.grow_on_skin(hull, COLD_UNDER, 30, -1.0, -0.3, Vector2(1.0, 1.6), Vector2(0.3, 999.0), off_route)
	var ruins: Node3D = _landmarks.get(RUINS)
	if ruins and ruins.has_method(&"rocks"):
		var place := ruins.global_transform
		var routes: Dictionary = ruins.get_script().call(&"routes")
		var off_route := func(at: Vector3) -> bool:
			for name: String in routes:
				var points: PackedVector3Array = routes[name][0]
				for i in points.size() - 1:
					if Geometry3D.get_closest_point_to_segment(at, place * points[i], place * points[i + 1]).distance_to(at) < float(routes[name][1]) + 1.2:
						return true
			return false
		var stones := Biomes.skin_of(ruins)
		# (42 m: no light for anything green; the giant deep forms, bigger)
		growth.grow_on_skin(stones, ["puffball_sponges", "vase_sponge", "vase_sponge", "bat_star"], 50, 0.6, 1.0, Vector2(1.2, 2.2), Vector2(0.3, 999.0), off_route)
		growth.grow_on_skin(stones, ["vase_sponge", "sea_fan_red", "hydrocoral", "strawberry_anemones"], 50, -0.3, 0.6, Vector2(1.0, 1.9), Vector2(0.3, 999.0), off_route)
	if not _outcrop_spheres.is_empty():
		# (the waterline band of mussels, green anemones and stars where the light is, the shaded
		# faces deeper red with strawberry anemones and fans; BIOMES.md 5.6)
		growth.grow_on(_outcrop_spheres, ["mussel_clump"], 45, -0.3, 0.7, Vector2(0.9, 1.4), Vector2(0.3, 2.5), Callable(), 0.25)
		growth.grow_on(_outcrop_spheres, COLD_UP_SHALLOW, 30, 0.5, 1.0, Vector2(0.9, 1.4), Vector2(0.3, 12.0), Callable(), 0.25)
		growth.grow_on(_outcrop_spheres, COLD_SIDE, 70, -0.3, 0.6, Vector2(0.9, 1.5), Vector2(6.0, 999.0), Callable(), 0.25)
		growth.grow_on(_outcrop_spheres, COLD_UNDER, 20, -1.0, -0.3, Vector2(0.8, 1.2), Vector2(6.0, 999.0), Callable(), 0.25)
	# The crags' pinnacles, stacks, arches and shards (concept_biome_crags.png): white plumose anemones
	# on their sides and lit shoulders, pink coralline (strawberry anemone sheets) over their faces, sea
	# stars and urchins on top.
	for spheres: Array in _biomes.grow_spheres:
		growth.grow_on(spheres, ["plumose_anemones"], 4, -0.1, 0.9, Vector2(1.4, 2.4), Vector2(3.0, 999.0), Callable(), 0.15)
		growth.grow_on(spheres, ["strawberry_anemones"], 3, -0.5, 0.8, Vector2(1.2, 2.0), Vector2(3.0, 999.0), Callable(), 0.1)
		growth.grow_on(spheres, ["ochre_star", "bat_star", "urchin_purple"], 1, 0.4, 1.0, Vector2(1.0, 1.5), Vector2(3.0, 999.0), Callable(), 0.1)
	var grown := 0
	for piece: String in growth.pieces:
		grown += (growth.pieces[piece][0] as Array).size()
	print("SCENERY growth on structures: %d pieces" % grown)
	# (drawn by a field of their own, full models only within GROWTH_NEAR: on a hull the eye is often
	# within 8 m of dozens of them, and their full models are dear: tools/PERF.md)
	var field := LodField.new()
	field.name = "Growth"
	field.near = GROWTH_NEAR
	field.far = PIECES_SEEN
	for piece: String in growth.pieces:
		field.add(piece, _props.call(&"mesh_of", piece, false), _props.call(&"mesh_of", piece, true), _props.call(&"material_of", piece),
				growth.pieces[piece][0], growth.pieces[piece][1], (_props.call(&"size_of", piece) as Vector3).length() * 0.5)
	add_child(field)


# The liner, Atlantis and the pirate ship (other agents' nodes), where Sea says, if they are there.
func _add_landmarks() -> void:
	for each: Array in [[WRECK, Sea.WRECK_AT, Sea.WRECK_HEADING], [RUINS, Sea.RUINS_AT, Sea.RUINS_HEADING], [PIRATE, Sea.PIRATE_AT, Sea.PIRATE_HEADING]]:
		if not ResourceLoader.exists(each[0]):
			continue
		var made: Node3D = (load(each[0]) as GDScript).new()
		made.position = each[1]
		made.rotation.y = each[2]
		add_child(made)
		_landmarks[each[0]] = made


# -+ the deep's set pieces

# The old one asleep on the canyon's deep floor, its face towards Atlantis, and the reef back
# walking its slow loop on the deep floor past the shelf's edge (GameCommon's old-one and
# reef-back; where they lie and walk is Claude's, tools/BIOMES.md). Their game models; the light
# ones beyond GIANT_LOW. The old one's body and head stop a swimmer; the reef back walks, so it
# does not (spheres are fixed).
func _add_giants() -> void:
	# (the user, 2026-11-18: "The giant monsters should not just spawn, those will need special
	# conditions": until those are made, neither is put in the sea)
	if not MONSTERS:
		return
	if ResourceLoader.exists(OLD_ONE):
		_old_one = (load(OLD_ONE) as GDScript).new()
		_old_one.set(&"game", true)
		_old_one.set(&"cartoon_eyes", 1.0)
		add_child(_old_one)
		var at := Vector3(OLD_ONE_AT.x, Sea.ground(OLD_ONE_AT.x, OLD_ONE_AT.y), OLD_ONE_AT.y)
		_old_one.global_position = at
		var face := Vector3(Sea.RUINS_AT.x, at.y, Sea.RUINS_AT.z) - at
		_old_one.rotation.y = atan2(-face.x, -face.z)
		for s: Vector4 in [Vector4(0.0, 4.0, 2.0, 11.0), Vector4(0.0, 13.0, -4.0, 8.5), Vector4(0.0, 19.0, -5.0, 5.0)]:
			var p := _old_one.global_transform * Vector3(s.x, s.y, s.z)
			Sea.add_rock(Vector4(p.x, p.y, p.z, s.w))
	if ResourceLoader.exists(REEF_BACK):
		_reef_back = (load(REEF_BACK) as GDScript).new()
		_reef_back.set(&"game", true)
		_reef_back.set(&"cartoon_eyes", 1.0)
		add_child(_reef_back)
		_walk_giants(0.0)


func _walk_giants(delta: float) -> void:
	var eye := player.global_position if player else (get_viewport().get_camera_3d().global_position if get_viewport().get_camera_3d() else Vector3.ZERO)
	if _old_one:
		var far := eye.distance_to(_old_one.global_position)
		# (it stirs as something comes near, slowly, and settles again when it has gone)
		var stir := 1.0 - smoothstep(22.0, 55.0, far)
		_old_one.set(&"wake", move_toward(float(_old_one.get(&"wake")), stir, delta * 0.12))
		_old_one.set(&"low", far > GIANT_LOW)
		_old_one.call(&"step", Vector3.ZERO, delta)
	if _reef_back:
		_reef_turn += delta * REEF_BACK_PACE / REEF_BACK_LOOP.z
		var at := Vector2(REEF_BACK_LOOP.x, REEF_BACK_LOOP.y) + Vector2.from_angle(_reef_turn) * REEF_BACK_LOOP.z
		var ahead := Vector2.from_angle(_reef_turn).orthogonal() * -1.0
		_reef_back.global_position = Vector3(at.x, Sea.ground(at.x, at.y), at.y)
		_reef_back.rotation.y = atan2(-ahead.x, -ahead.y)
		_reef_back.set(&"low", eye.distance_to(_reef_back.global_position) > GIANT_LOW)
		_reef_back.call(&"step", Vector3(ahead.x, 0.0, ahead.y) * REEF_BACK_PACE, delta)
