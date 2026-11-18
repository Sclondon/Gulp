class_name Bay
## The shape of the sea floor: Monterey Bay's real depths (CLAUDE.md, "Decision: the real bay"),
## baked by tools/bake_bay.gd into data/monterey.bin from GMRT's grid of the bay (MBARI's
## multibeam): 180 real metres a game metre, depths squeezed (100 m real is 25 m here, the canyon's
## 2,000 m about 100 m), the narrow canyons widened and the near shore eased for play. North is -Z,
## east is +X; the bay opens to the west, where the shelf falls away into the open Pacific.
##
## On top of the baked floor, what the real one has too small or not at all, for play: Elkhorn
## Slough's channel cut through the land at Moss Landing, the harbours dredged level, and three level
## shelves for the liner, Atlantis and the pirate ship. `Sea.ground` reads all of it from a 2 m grid
## made the first time it is asked.
##
## (Before 2026-11-18, late, the floor was a sum of shapes drawn to the user's layout: capsules of
## land, polyline canyons; see tools/MONTEREY.md. The user then asked for the real topography.)

const SURFACE := 40.0
## The floor was once drawn on a chart of its own metres; it is the world now (kept for the code that
## multiplies by it).
const K := 1.0
## The grid `Sea.ground` reads: from the north-west corner, a height every GRID metres (world).
const GRID := 2.0
## The world's bounds (world metres): the bake's.
const WEST := -122.0
const EAST := 122.0
const NORTH := -160.0
const SOUTH := 160.0
## Deeper than this (m), the floor is past the shelf's edge: `edge_at` finds where.
const EDGE_DEEP := 32.0
## (kept for Sea.EDGE: the shelf's edge at the middle of the map)
const EDGE := -20.0
## How wide the beach strip is (m from the shore) and how deep it gets (m): the bake eases the floor
## to this.
const BEACH := 14.0
const BEACH_DEEP := 5.0

const DATA := "res://data/monterey.bin"

## Elkhorn Slough: a channel winding inland from Moss Landing, half this wide, this deep.
const SLOUGH := [Vector2(99.0, -40.0), Vector2(106.0, -41.0), Vector2(111.0, -37.0), Vector2(116.0, -40.0), Vector2(121.0, -35.0)]
const SLOUGH_HALF := 5.0
const SLOUGH_DEEP := 4.0
## Harbours dredged level behind their walls: middle, radius, depth.
const HARBOURS := [
	[Vector2(66.0, 70.0), 20.0, 6.0],  # Monterey harbour (east of the wharf, off Del Monte: where the shore faces north)
	[Vector2(-6.0, -123.0), 11.0, 5.0],  # Santa Cruz wharf
	[Vector2(16.0, -128.0), 7.0, 4.5],  # Santa Cruz small craft harbour
	[Vector2(27.0, 116.0), 8.0, 8.0],  # Carmel: Stillwater Cove, for the market's pier
]
## Shelves made level (world metres): middle, flat out to, blended out to, depth at the middle (m),
## and how much deeper it gets per metre (x, z); a long one also its heading (as rotation.y) and how
## much narrower it is across (the liner's, along its hull).
## (the liner's is a spur raised off Carmel, which only fills: its 7th item)
const WRECK_SHELF := [Vector2(0.0, 122.0), 36.0, 84.0, 40.0, Vector2(-0.06, 0.0), Vector2(0.32, 1.9), true]
const RUINS_TERRACE := [Vector2(-53.0, 26.0), 34.0, 56.0, 93.0, Vector2(0.0, 0.0)]
const PIRATE_HOLLOW := [Vector2(-20.0, -62.0), 20.0, 38.0, 21.0, Vector2(0.0, 0.06)]

static var _grid := PackedFloat32Array()
static var _cols := 0
static var _rows := 0
# The baked floor: depth and shore distance every `_cell` metres from (_x0, _z0).
static var _depth := PackedFloat32Array()
static var _shore := PackedFloat32Array()
static var _dcols := 0
static var _drows := 0
static var _x0 := 0.0
static var _z0 := 0.0
static var _cell := 1.0
# The shelf's edge (world x) for each row of the 2 m grid.
static var _edges := PackedFloat32Array()


## The floor's height at a point, read from the grid (made the first time it is asked).
static func ground(x: float, z: float) -> float:
	if _grid.is_empty():
		_build()
	var gx := clampf((x - WEST) / GRID, 0.0, _cols - 1.001)
	var gz := clampf((z - NORTH) / GRID, 0.0, _rows - 1.001)
	var c := int(gx)
	var r := int(gz)
	var fx := gx - c
	var fz := gz - r
	var i := r * _cols + c
	var top := lerpf(_grid[i], _grid[i + 1], fx)
	var bottom := lerpf(_grid[i + _cols], _grid[i + _cols + 1], fx)
	return lerpf(top, bottom, fz)


static func _load() -> void:
	if not _depth.is_empty():
		return
	var f := FileAccess.open(DATA, FileAccess.READ)
	_dcols = f.get_32()
	_drows = f.get_32()
	_x0 = f.get_float()
	_z0 = f.get_float()
	_cell = f.get_float()
	_depth = f.get_buffer(_dcols * _drows * 4).to_float32_array()
	_shore = f.get_buffer(_dcols * _drows * 4).to_float32_array()


static func _build() -> void:
	_load()
	_cols = int(round((EAST - WEST) / GRID)) + 1
	_rows = int(round((SOUTH - NORTH) / GRID)) + 1
	_grid.resize(_cols * _rows)
	_edges.resize(_rows)
	for r in _rows:
		var z := NORTH + r * GRID
		var edge := WEST
		var open := true
		for c in _cols:
			var x := WEST + c * GRID
			_grid[r * _cols + c] = height(x, z)
			# (the edge: how far east the deep water reaches unbroken from the world's west side)
			if open and SURFACE - _grid[r * _cols + c] > EDGE_DEEP:
				edge = x
			else:
				open = false
		_edges[r] = edge


static func _sample(layer: PackedFloat32Array, x: float, z: float) -> float:
	_load()
	var gx := clampf((x - _x0) / _cell, 0.0, _dcols - 1.001)
	var gz := clampf((z - _z0) / _cell, 0.0, _drows - 1.001)
	var c := int(gx)
	var r := int(gz)
	var fx := gx - c
	var fz := gz - r
	var i := r * _dcols + c
	return lerpf(lerpf(layer[i], layer[i + 1], fx), lerpf(layer[i + _dcols], layer[i + _dcols + 1], fx), fz)


## The floor's height worked out from the baked floor and what is laid over it (slow: use `ground`).
static func height(x: float, z: float) -> float:
	var p := Vector2(x, z)
	var flat := 0.0
	var deep := depth(p)
	for shelf: Array in [WRECK_SHELF, RUINS_TERRACE, PIRATE_HOLLOW]:
		flat = maxf(flat, shelf_weight(p, shelf))
	var bumps := 0.6 * sin(x * 0.07 + 1.3) * cos(z * 0.06) + 0.2 * sin(x * 0.21 + z * 0.17)
	return SURFACE - deep + bumps * clampf(deep * 0.15, 0.0, 1.0) * (1.0 - flat)


## How far from the shore a point is (world metres; less than 0 on land).
static func shore_distance(p: Vector2) -> float:
	return _shore_at(p)


static func _shore_at(p: Vector2) -> float:
	# (the slough is water cut through the land)
	return maxf(_sample(_shore, p.x, p.y), SLOUGH_HALF - _line_distance(p, SLOUGH))


## How deep the water is at a point (m; less than 0 on land).
static func depth(p: Vector2) -> float:
	var deep := _sample(_depth, p.x, p.y)
	var d := _shore_at(p)
	# The slough's channel.
	var channel := 1.0 - smoothstep(SLOUGH_HALF - 2.0, SLOUGH_HALF, _line_distance(p, SLOUGH))
	deep = lerpf(deep, maxf(deep, SLOUGH_DEEP), channel)
	# Harbours, dredged level up to their quays.
	for harbour: Array in HARBOURS:
		var r: float = harbour[1]
		var w := (1.0 - smoothstep(r * 0.6, r, p.distance_to(harbour[0]))) * smoothstep(0.5, 2.5, d)
		deep = lerpf(deep, maxf(deep, float(harbour[2])), w)
	# The level shelves (Atlantis's terrace stands up out of the canyon's floor).
	for shelf: Array in [WRECK_SHELF, RUINS_TERRACE, PIRATE_HOLLOW]:
		var middle: Vector2 = shelf[0]
		# (never right up to a shore: the shallows stay as they are)
		var w := shelf_weight(p, shelf) * smoothstep(3.0, 10.0, d)
		var level := float(shelf[3]) + (shelf[4] as Vector2).dot(p - middle)
		# (a spur only raises the floor round what lies on it: where it is already shallower it is left
		# as it is, but under the thing itself it is level both ways)
		if shelf.size() > 6 and bool(shelf[6]):
			level = lerpf(minf(level, deep), level, smoothstep(0.85, 1.0, shelf_weight(p, shelf)))
		deep = lerpf(deep, level, w)
	return deep


## How much of a level shelf a point is on (1 on its flat, 0 off it). Its flat is round, as the set
## piece on it needs; its sides spread out unevenly, so it does not stand as a disc.
static func shelf_weight(p: Vector2, shelf: Array) -> float:
	var middle: Vector2 = shelf[0]
	var flat: float = shelf[1]
	var off := p - middle
	# (a long one, for a long hull: [its heading as Sea's rotation.y, how much narrower across])
	if shelf.size() > 5:
		var long: Vector2 = shelf[5]
		var along := Vector2(sin(long.x), cos(long.x))
		off = along * off.dot(along) + along.orthogonal() * off.dot(along.orthogonal()) * long.y
	var turn := atan2(off.y, off.x)
	var seed := middle.x * 0.13 + middle.y * 0.07
	var spread := 1.0 + 0.6 * sin(turn * 3.0 + seed) + 0.35 * sin(turn * 5.0 + seed * 2.3)
	var out := flat + (float(shelf[2]) - flat) * clampf(spread, 0.45, 1.35)
	return 1.0 - smoothstep(flat, out, off.length())


## Where the shelf's edge is (world x) at a place along the coast (world z): west of it the water
## is deeper than EDGE_DEEP all the way to the world's edge.
static func edge_at(z: float) -> float:
	if _grid.is_empty():
		_build()
	var r := clampi(int(round((z - NORTH) / GRID)), 0, _rows - 1)
	return _edges[r]


static func _line_distance(p: Vector2, line: Array) -> float:
	var best := INF
	for i in line.size() - 1:
		best = minf(best, p.distance_to(Geometry2D.get_closest_point_to_segment(p, line[i], line[i + 1])))
	return best
