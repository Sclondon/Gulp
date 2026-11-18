class_name BiomeRegions
## The bay's eight biomes, where the user drew or named them: the one source of where each is
## (tools/BIOMES.md, "The eight biomes"). Biomes' tables, FloorTypes' paint, Bay's dunes and the
## animals' zones (Sea.ZONES "region") all ask here.
##
## Four are rough outlines the user drew over the overhead chart (2026-11-18: "We need to make proper
## biomes, with concept art for each considering our needs. Green is kelp forest, yellow is sand dune
## sea, red is sea grassy fields, purple is rocky crags"; then "the green section should be kelp forest
## not dune sea"; and "You shouldnt be that exact just look at the map and see the areas I was trying
## to highlight"): read off the drawings by eye (world x, z), not traced. The drawings:
## tools/art_src/user_biome_lines.png and the second one's description in CLAUDE.md.
## Four more the user named ("Trench, beach shallows, and river need to count as biomes as well, and
## the reef on the ship"): the trench is the floor deeper than the shelf (the bake raises everything
## outside the drawn trench to 26 m), less Atlantis's basin; the beach is the shallows strip along every
## shore (Bay.BEACH); the river is Elkhorn Slough at Moss Landing; the reef is the liner's.
##
## Worked out once on Bay's 2 m grid (the first time it is asked): which biome each corner is in (the
## first in ORDER that has it), and how far it is in from the biome's edge (for `weight`).

const KELP := "kelp"
const DUNES := "dunes"
const GRASS := "grass"
const CRAGS := "crags"
const TRENCH := "trench"
const BEACH := "beach"
const RIVER := "river"
const REEF := "reef"
## Which wins where two overlap: the small named places first, then the trench by depth (so the
## drawn outlines never spill down a canyon wall), the shore's strip, then the drawn four.
const ORDER := [RIVER, REEF, TRENCH, BEACH, CRAGS, KELP, GRASS, DUNES]
## How far (m) a biome's look fades in across its edge.
const EDGE := 8.0
## The trench: floor deeper than this (m; the shelf is 26 m, its bumps and the dunes within 1).
const TRENCH_DEEP := 28.0
## Atlantis's basin (world middle, radius): no trench dressing there (the ruins dress their own).
const RUINS_CLEAR := [Vector2(-64.0, 48.0), 30.0]
## The river: within this of Elkhorn Slough's channel's edge (m); and the estuary round its mouth at Moss
## Landing (the user, 2026-11-18: "there should be a seaweedy / grassy area around the mouth instead of
## regular beach"): within RIVER_MOUTH of ESTUARY, along the shore both ways, out to where the canyon head
## falls below ESTUARY_DEEP.
const RIVER_BANK := 5.0
const ESTUARY := Vector2(96.0, -40.0)
const RIVER_MOUTH := 25.0
const ESTUARY_DEEP := 10.0
## The beach: within Bay.BEACH of the shore and shallower than this (m).
const BEACH_DEEP := 6.0

const SHAPES := {
	KELP: [
		# along the Monterey side, from the canyon's south rim to Monterey and down past Point Pinos
		[Vector2(-10.0, 6.0), Vector2(4.0, 12.0), Vector2(19.0, 11.0), Vector2(56.0, -20.0), Vector2(65.0, -18.0), Vector2(65.0, 16.0),
			Vector2(72.0, 40.0), Vector2(83.0, 42.0), Vector2(76.0, 61.0), Vector2(64.0, 78.0), Vector2(54.0, 80.0), Vector2(44.0, 54.0),
			Vector2(35.0, 54.0), Vector2(28.0, 58.0), Vector2(11.0, 91.0), Vector2(-10.0, 94.0), Vector2(-16.0, 85.0), Vector2(-28.0, 77.0),
			Vector2(-30.0, 64.0), Vector2(-26.0, 40.0), Vector2(-18.0, 24.0)],
		# east of the Soquel branch, north of the canyon (was dune sea: the user's second drawing)
		[Vector2(19.0, -77.0), Vector2(22.0, -90.0), Vector2(41.0, -91.0), Vector2(51.0, -80.0), Vector2(57.0, -64.0), Vector2(57.0, -42.0),
			Vector2(40.0, -34.0), Vector2(27.0, -32.0), Vector2(20.0, -48.0)],
	],
	DUNES: [
		# the north shelf, Santa Cruz to the canyon
		[Vector2(-96.0, -120.0), Vector2(-62.0, -113.0), Vector2(-32.0, -101.0), Vector2(19.0, -104.0), Vector2(38.0, -90.0), Vector2(56.0, -73.0),
			Vector2(52.0, -58.0), Vector2(40.0, -45.0), Vector2(17.0, -45.0), Vector2(6.0, -58.0), Vector2(-5.0, -50.0), Vector2(-32.0, -51.0),
			Vector2(-47.0, -56.0), Vector2(-61.0, -64.0), Vector2(-103.0, -83.0), Vector2(-104.0, -96.0), Vector2(-100.0, -117.0)],
		# the far south-west corner
		[Vector2(-122.0, 118.0), Vector2(-110.0, 146.0), Vector2(-84.0, 147.0), Vector2(-71.0, 160.0), Vector2(-122.0, 160.0)],
	],
	GRASS: [
		# west of the trench, south of the pirate ship
		[Vector2(-103.0, -46.0), Vector2(-101.0, 0.0), Vector2(-95.0, 16.0), Vector2(-80.0, 24.0), Vector2(-61.0, 19.0), Vector2(-50.0, 10.0),
			Vector2(-40.0, -11.0), Vector2(-40.0, -16.0), Vector2(-82.0, -22.0), Vector2(-101.0, -43.0)],
		# the shelf between the basin and the Carmel Canyon
		[Vector2(-30.0, 54.0), Vector2(-45.0, 80.0), Vector2(-68.0, 91.0), Vector2(-70.0, 102.0), Vector2(-50.0, 94.0), Vector2(-32.0, 99.0),
			Vector2(-24.0, 103.0), Vector2(-16.0, 96.0), Vector2(-14.0, 83.0), Vector2(-20.0, 78.0), Vector2(-28.0, 69.0)],
		# two strips south of the Carmel Canyon, either side of the liner's south end
		[Vector2(-85.0, 137.0), Vector2(-66.0, 135.0), Vector2(-65.0, 145.0), Vector2(-53.0, 160.0), Vector2(-60.0, 160.0), Vector2(-74.0, 147.0)],
		[Vector2(-18.0, 130.0), Vector2(-12.0, 130.0), Vector2(-4.0, 142.0), Vector2(-4.0, 160.0), Vector2(-13.0, 160.0), Vector2(-13.0, 152.0),
			Vector2(-18.0, 141.0)],
	],
	CRAGS: [
		# round the pirate ship and its seal rock
		[Vector2(-103.0, -76.0), Vector2(-82.0, -72.0), Vector2(-65.0, -68.0), Vector2(-53.0, -58.0), Vector2(-32.0, -50.0), Vector2(-27.0, -45.0),
			Vector2(-27.0, -32.0), Vector2(-32.0, -21.0), Vector2(-40.0, -17.0), Vector2(-61.0, -18.0), Vector2(-82.0, -22.0), Vector2(-100.0, -38.0),
			Vector2(-108.0, -51.0), Vector2(-108.0, -61.0)],
		# a patch inside the western grass (round the second islet)
		[Vector2(-89.0, -4.0), Vector2(-79.0, -9.0), Vector2(-69.0, -4.0), Vector2(-67.0, 10.0), Vector2(-76.0, 10.0), Vector2(-89.0, 6.0)],
	],
	# The liner's reef: round the wreck where its bommies stand (Scenery._place_reef, out to 32 m).
	REEF: [
		[Vector2(-37.0, 92.0), Vector2(-15.0, 100.0), Vector2(-8.0, 126.0), Vector2(-15.0, 152.0), Vector2(-37.0, 160.0), Vector2(-59.0, 152.0),
			Vector2(-66.0, 126.0), Vector2(-59.0, 100.0)],
	],
}
## The order the drawn outlines win in among themselves (for Bay's dunes, which cannot ask the grid:
## the grid needs the floor, and the floor needs the dunes).
const SHAPE_ORDER := [REEF, CRAGS, KELP, GRASS, DUNES]

static var _packed := {}
static var _ids := PackedByteArray()
static var _inside := PackedFloat32Array()
static var _cells := {}
static var _cols := 0
static var _rows := 0


## The biome at a point ("" for none).
static func at(x: float, z: float) -> String:
	_build()
	var id := _ids[_index(x, z)]
	return "" if id == 0 else ORDER[id - 1]


## How much a point is in a biome, 0..1, fading in over EDGE metres inside its edge (0 outside it).
static func weight(name: String, x: float, z: float) -> float:
	_build()
	var i := _index(x, z)
	var id := _ids[i]
	if id == 0 or ORDER[id - 1] != name:
		return 0.0
	return smoothstep(0.0, EDGE, _inside[i])


## A box round every corner of a biome (world x, z).
static func bounds(name: String) -> Rect2:
	_build()
	var list: PackedInt32Array = _cells.get(name, PackedInt32Array())
	if list.is_empty():
		return Rect2()
	var low := Vector2(INF, INF)
	var high := -low
	for i in list:
		var p := _corner(i)
		low = low.min(p)
		high = high.max(p)
	return Rect2(low - Vector2.ONE * Bay.GRID, high - low + Vector2.ONE * Bay.GRID * 2.0)


## A place (x, z) in a biome at random, at least `inside` metres in from its edge if it can be had.
static func spot(rng: RandomNumberGenerator, name: String, inside := 2.0) -> Vector2:
	_build()
	var list: PackedInt32Array = _cells.get(name, PackedInt32Array())
	if list.is_empty():
		return Vector2.ZERO
	var i := list[rng.randi() % list.size()]
	for tries in 8:
		if _inside[i] >= inside:
			break
		i = list[rng.randi() % list.size()]
	return _corner(i) + Vector2(rng.randf_range(-1.0, 1.0), rng.randf_range(-1.0, 1.0)) * Bay.GRID * 0.5


## How much a point is in one of the drawn outlines alone (no grid, no floor): 0..1 over EDGE in
## from its edge, 0 where an outline earlier in SHAPE_ORDER has it. (Bay's dunes ask this.)
static func shape_weight(name: String, x: float, z: float) -> float:
	var p := Vector2(x, z)
	for other: String in SHAPE_ORDER:
		if other == name:
			break
		for shape: PackedVector2Array in _shapes(other):
			if Geometry2D.is_point_in_polygon(p, shape):
				return 0.0
	var near := -1.0
	for shape: PackedVector2Array in _shapes(name):
		if not Geometry2D.is_point_in_polygon(p, shape):
			continue
		near = INF
		for i in shape.size():
			near = minf(near, p.distance_to(Geometry2D.get_closest_point_to_segment(p, shape[i], shape[(i + 1) % shape.size()])))
	return 0.0 if near < 0.0 else smoothstep(0.0, EDGE, near)


static func _in_shape(name: String, p: Vector2) -> bool:
	for shape: PackedVector2Array in _shapes(name):
		if Geometry2D.is_point_in_polygon(p, shape):
			return true
	return false


static func _shapes(name: String) -> Array:
	if not _packed.has(name):
		var list := []
		for shape: Array in SHAPES.get(name, []):
			list.append(PackedVector2Array(shape))
		_packed[name] = list
	return _packed[name]


static func _index(x: float, z: float) -> int:
	var c := clampi(int(round((x - Bay.WEST) / Bay.GRID)), 0, _cols - 1)
	var r := clampi(int(round((z - Bay.NORTH) / Bay.GRID)), 0, _rows - 1)
	return r * _cols + c


static func _corner(i: int) -> Vector2:
	return Vector2(Bay.WEST + (i % _cols) * Bay.GRID, Bay.NORTH + (i / _cols) * Bay.GRID)


# Which biome a corner is in, by the rules in ORDER.
static func _rule(p: Vector2) -> int:
	var deep := Bay.SURFACE - Bay.ground(p.x, p.y)
	var shore := Bay.shore_distance(p)
	for k in ORDER.size():
		var name: String = ORDER[k]
		match name:
			TRENCH:
				if deep > TRENCH_DEEP and p.distance_to(RUINS_CLEAR[0]) > float(RUINS_CLEAR[1]):
					return k + 1
			RIVER:
				# (Elkhorn Slough: its channel and banks, however it winds: Bay.SLOUGH, and its mouth)
				if Bay._line_distance(p, Bay.SLOUGH) < Bay.SLOUGH_HALF + RIVER_BANK or (p.distance_to(ESTUARY) < RIVER_MOUTH and deep < ESTUARY_DEEP):
					return k + 1
			BEACH:
				if shore > -0.5 and shore < Bay.BEACH * Bay.K and deep < BEACH_DEEP:
					return k + 1
			_:
				if _in_shape(name, p):
					return k + 1
	return 0


static func _build() -> void:
	if not _ids.is_empty():
		return
	# (Bay's floor first: its shore distances are read from what that loads)
	Bay.ground(0.0, 0.0)
	_cols = int(round((Bay.EAST - Bay.WEST) / Bay.GRID)) + 1
	_rows = int(round((Bay.SOUTH - Bay.NORTH) / Bay.GRID)) + 1
	var n := _cols * _rows
	_ids.resize(n)
	_inside.resize(n)
	for i in n:
		var p := _corner(i)
		# (dry land is no biome)
		_ids[i] = 0 if Bay.shore_distance(p) < -0.5 else _rule(p)
	# How far in from its biome's edge each corner is: a two-pass chamfer distance from the corners
	# whose neighbour is in another biome (or out of the world), capped past EDGE.
	var cap := EDGE + Bay.GRID
	for i in n:
		var r := i / _cols
		var c := i % _cols
		var edge := r == 0 or c == 0 or r == _rows - 1 or c == _cols - 1
		if not edge:
			edge = _ids[i - 1] != _ids[i] or _ids[i + 1] != _ids[i] or _ids[i - _cols] != _ids[i] or _ids[i + _cols] != _ids[i]
		_inside[i] = 0.0 if edge else cap
	var g := Bay.GRID
	var d := g * sqrt(2.0)
	for r in range(1, _rows):
		for c in range(1, _cols - 1):
			var i := r * _cols + c
			_inside[i] = minf(_inside[i], minf(minf(_inside[i - 1] + g, _inside[i - _cols] + g), minf(_inside[i - _cols - 1] + d, _inside[i - _cols + 1] + d)))
	for r in range(_rows - 2, -1, -1):
		for c in range(_cols - 2, 0, -1):
			var i := r * _cols + c
			_inside[i] = minf(_inside[i], minf(minf(_inside[i + 1] + g, _inside[i + _cols] + g), minf(_inside[i + _cols + 1] + d, _inside[i + _cols - 1] + d)))
	# (each biome's corners, for `spot` and `bounds`; a PackedInt32Array is a value: put back after appending)
	var filled := {}
	for k in ORDER.size():
		filled[ORDER[k]] = PackedInt32Array()
	for i in n:
		if _ids[i] > 0:
			var list: PackedInt32Array = filled[ORDER[_ids[i] - 1]]
			list.append(i)
			filled[ORDER[_ids[i] - 1]] = list
	_cells = filled
