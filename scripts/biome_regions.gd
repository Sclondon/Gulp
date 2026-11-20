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
static var EDGE: float = Layout.number("biomes.edge")
## The trench: floor deeper than this (m; the shelf is 26 m, its bumps and the dunes within 1).
static var TRENCH_DEEP: float = Layout.number("biomes.trench_deep")
## Atlantis's basin (world middle, radius): no trench dressing there (the ruins dress their own).
static var RUINS_CLEAR: Array = [Layout.point("biomes.ruins_clear.at"), Layout.number("biomes.ruins_clear.radius")]
## The river: within this of Elkhorn Slough's channel's edge (m); and the estuary round its mouth at Moss
## Landing (the user, 2026-11-18: "there should be a seaweedy / grassy area around the mouth instead of
## regular beach"): within RIVER_MOUTH of ESTUARY, along the shore both ways, out to where the canyon head
## falls below ESTUARY_DEEP.
static var RIVER_BANK: float = Layout.number("river.banks")
static var ESTUARY: Vector2 = Layout.point("river.estuary")
static var RIVER_MOUTH: float = Layout.number("river.mouth")
static var ESTUARY_DEEP: float = Layout.number("river.mouth_deep")
## The beach: within Bay.BEACH of the shore and shallower than this (m).
static var BEACH_DEEP: float = Layout.number("biomes.beach_deep")

## The drawn outlines (world x, z; data/layout.json, "biomes" "shapes", since 2026-11-20): kelp along the Monterey side,
## from the canyon's south rim to Monterey and down past Point Pinos, and east of the Soquel branch north of the canyon
## (was dune sea: the user's second drawing); dunes on the north shelf, Santa Cruz to the canyon, and in the far
## south-west corner; grass west of the trench south of the pirate ship, on the shelf between the basin and the
## Carmel Canyon, and in two strips south of the Carmel Canyon either side of the liner's south end; crags round the
## pirate ship and its seal rock and a patch inside the western grass round the second islet; the liner's reef round
## the wreck where its bommies stand (Scenery._place_reef, out to 32 m).
static var SHAPES: Dictionary = Layout.shapes()
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
