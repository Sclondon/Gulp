class_name Bay
## The shape of the sea floor: a small Monterey Bay, laid out after the user's own drawing over a
## carved chart of the bay (tools/MONTEREY.md has the layout, the scale and whose calls they were).
## North is -Z, east is +X: the land is the north shore (Santa Cruz to Aptos), the east shore
## (Moss Landing, with Elkhorn Slough cut into it) and the Monterey Peninsula in the south-east,
## and the bay opens to the west, where the shelf's edge drops away to the open Pacific.
##
## `depth(x, z)` is the one sum: how far below the surface the floor lies. It is slow (it measures
## the distance to every piece of shore and canyon), so `Sea.ground` asks it once for every corner
## of a 2 m grid and reads the grid back. Change the numbers here and the whole sea follows.
##
## Pieces:
## - LAND: capsules (a segment and a radius): the shore is `radius` out from the segment.
## - Depth from the shore: the beach strip (0 to 5 m over the first 18 m), then the shelf.
## - The canyons: polylines, each point [where, half width, floor depth].
## - The flats: shelves made level for what lies on them (the liner, Atlantis, the pirate ship).

const SURFACE := 40.0
## Everything below is drawn on a chart (its own metres) and the world is the chart at this
## scale (the user, 2026-11-18: "the map doesnt need to be super huge either, nicely curated and
## big enough areas to recreate the intetion of hte map"): about the old sea's size. Depths are
## not scaled. Sea's ZONES, WRECK_AT and the rest are in the world's metres.
const K := 0.8
## The grid `Sea.ground` reads: from the north-west corner, a height every GRID metres (world).
const GRID := 2.0
## The world's bounds (world metres).
const WEST := -196.0 * K
const EAST := 150.0 * K
const NORTH := -170.0 * K
const SOUTH := 194.0 * K
## The shelf's edge (chart x), wavering along z (`edge_at`): beyond it the floor drops away.
const EDGE := -140.0
## How wide the beach strip is (chart m from the shore) and how deep it gets (m).
const BEACH := 18.0
const BEACH_DEEP := 5.0

const LAND := [
	[Vector2(-260.0, -198.0), Vector2(30.0, -198.0), 48.0],  # the north shore: Santa Cruz, Capitola, Aptos
	[Vector2(-85.0, -170.0), Vector2(-85.0, -170.0), 28.0],  # Lighthouse Point, west of the Santa Cruz wharf
	[Vector2(30.0, -198.0), Vector2(175.0, -110.0), 55.0],  # the bay's north-east corner (Watsonville)
	[Vector2(170.0, -110.0), Vector2(170.0, 45.0), 55.0],  # the east shore: Moss Landing, Marina
	[Vector2(170.0, 45.0), Vector2(115.0, 140.0), 55.0],  # Seaside and Sand City
	[Vector2(115.0, 140.0), Vector2(50.0, 130.0), 26.0],  # Monterey, round the harbour
	[Vector2(50.0, 130.0), Vector2(12.0, 124.0), 22.0],  # the peninsula's north shore: Cannery Row, Pacific Grove
	[Vector2(12.0, 124.0), Vector2(22.0, 150.0), 22.0],  # the peninsula's west shore: Point Pinos to Cypress Point
	[Vector2(12.0, 205.0), Vector2(12.0, 205.0), 22.0],  # Point Lobos
	[Vector2(30.0, 215.0), Vector2(170.0, 215.0), 30.0],  # Carmel and the Big Sur coast
]
## Elkhorn Slough: a channel winding inland from Moss Landing, half this wide, this deep.
const SLOUGH := [Vector2(108.0, -22.0), Vector2(124.0, -27.0), Vector2(134.0, -18.0), Vector2(145.0, -24.0), Vector2(156.0, -16.0)]
const SLOUGH_HALF := 8.0
const SLOUGH_DEEP := 4.0
## Harbours dredged level behind their walls: middle, radius, depth.
const HARBOURS := [
	[Vector2(42.0, 98.0), 26.0, 6.0],  # Monterey harbour, Fisherman's Wharf
	[Vector2(-45.0, -134.0), 14.0, 5.0],  # Santa Cruz wharf
	[Vector2(-18.0, -140.0), 9.0, 4.5],  # Santa Cruz small craft harbour
	[Vector2(35.0, 176.0), 16.0, 8.0],  # Carmel: a cove off Carmel Beach for the market's pier (tools/BIOMES.md 5.12; Claude's)
]
## The Monterey Canyon: its head at Moss Landing, a narrow arm west between the two kelp
## forests, then widening into the deep basin that fills the middle of the map and runs south to
## its lower end, where Atlantis is. Each: where, half width (m), floor depth (m).
const CANYON := [
	[Vector2(118.0, -10.0), 7.0, 22.0], [Vector2(95.0, -6.0), 8.0, 28.0], [Vector2(75.0, -14.0), 8.0, 34.0],
	[Vector2(55.0, -4.0), 9.0, 40.0], [Vector2(35.0, -12.0), 10.0, 46.0], [Vector2(15.0, -2.0), 12.0, 52.0],
	[Vector2(-8.0, -8.0), 16.0, 60.0], [Vector2(-30.0, 5.0), 30.0, 72.0], [Vector2(-50.0, 25.0), 46.0, 84.0],
	[Vector2(-65.0, 50.0), 54.0, 92.0], [Vector2(-78.0, 75.0), 56.0, 98.0], [Vector2(-86.0, 104.0), 52.0, 100.0],
	[Vector2(-92.0, 128.0), 40.0, 96.0],
]
## Where the canyon runs on out to sea, west across the shelf's edge.
const CANYON_OUT := [
	[Vector2(-45.0, 20.0), 14.0, 72.0], [Vector2(-100.0, 35.0), 14.0, 85.0], [Vector2(-150.0, 38.0), 16.0, 100.0],
	[Vector2(-210.0, 40.0), 18.0, 110.0],
]
## The Carmel Canyon: its head in Carmel Bay, between Pescadero Point and Point Lobos, running
## west past the liner's shelf and round to the north-west.
const CARMEL := [
	[Vector2(16.0, 178.0), 5.0, 18.0], [Vector2(-12.0, 186.0), 6.0, 26.0], [Vector2(-50.0, 192.0), 7.0, 36.0],
	[Vector2(-92.0, 186.0), 9.0, 48.0], [Vector2(-125.0, 168.0), 10.0, 60.0], [Vector2(-145.0, 138.0), 12.0, 72.0],
	[Vector2(-160.0, 100.0), 14.0, 85.0],
]
## Shelves made level (chart metres; their world sizes, 0.8 of these, are what the wrecks and
## Atlantis need): middle, flat out to, blended out to, depth at the middle (m), and how much
## deeper it gets per chart metre (x, z).
const WRECK_SHELF := [Vector2(-50.0, 162.0), 35.0, 48.0, 30.0, Vector2(-0.1, 0.03)]
const RUINS_TERRACE := [Vector2(-94.0, 92.0), 44.0, 54.0, 42.0, Vector2(-0.04, 0.06)]
const PIRATE_HOLLOW := [Vector2(-100.0, -16.0), 25.0, 37.0, 21.0, Vector2(-0.06, 0.08)]

static var _grid := PackedFloat32Array()
static var _cols := 0
static var _rows := 0


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


static func _build() -> void:
	_cols = int(round((EAST - WEST) / GRID)) + 1
	_rows = int(round((SOUTH - NORTH) / GRID)) + 1
	_grid.resize(_cols * _rows)
	for r in _rows:
		var z := NORTH + r * GRID
		for c in _cols:
			_grid[r * _cols + c] = height(WEST + c * GRID, z)


## The floor's height worked out from the shapes (slow: use `ground`).
static func height(x: float, z: float) -> float:
	var p := Vector2(x, z) / K
	var flat := 0.0
	var deep := depth(p)
	for shelf: Array in [WRECK_SHELF, RUINS_TERRACE, PIRATE_HOLLOW]:
		flat = maxf(flat, 1.0 - smoothstep(float(shelf[1]), float(shelf[2]), p.distance_to(shelf[0])))
	var bumps := 0.6 * sin(x * 0.07 + 1.3) * cos(z * 0.06) + 0.2 * sin(x * 0.21 + z * 0.17)
	return SURFACE - deep + bumps * clampf(deep * 0.15, 0.0, 1.0) * (1.0 - flat)


## How far from the shore a point is (world metres; less than 0 on land).
static func shore_distance(p: Vector2) -> float:
	return _shore(p / K) * K


static func _shore(p: Vector2) -> float:
	var d := INF
	for piece: Array in LAND:
		d = minf(d, p.distance_to(Geometry2D.get_closest_point_to_segment(p, piece[0], piece[1])) - float(piece[2]))
	# (the slough is water cut through the land)
	return maxf(d, SLOUGH_HALF - _line_distance(p, SLOUGH))


## How deep the water is at a point of the chart (m; less than 0 on land).
static func depth(p: Vector2) -> float:
	var d := _shore(p)
	var deep := 0.0
	if d < 0.0:
		deep = maxf(d * 0.25, -4.0)
	elif d < BEACH:
		deep = d * BEACH_DEEP / BEACH
	else:
		deep = minf(BEACH_DEEP + (d - BEACH) * 0.2, 24.0)
	var wet := smoothstep(-1.0, 3.0, d)
	# The slough's channel.
	var channel := 1.0 - smoothstep(SLOUGH_HALF - 3.0, SLOUGH_HALF, _line_distance(p, SLOUGH))
	deep = lerpf(deep, maxf(deep, SLOUGH_DEEP), channel * wet)
	# Harbours, dredged level up to their quays.
	for harbour: Array in HARBOURS:
		var r: float = harbour[1]
		var w := (1.0 - smoothstep(r * 0.6, r, p.distance_to(harbour[0]))) * smoothstep(1.0, 4.0, d)
		deep = lerpf(deep, maxf(deep, float(harbour[2])), w)
	# Past the shelf's edge the floor falls away.
	var over := _edge(p.y) - p.x
	deep += (40.0 * smoothstep(0.0, 16.0, over) + 0.1 * maxf(over, 0.0)) * smoothstep(4.0, 20.0, d)
	# The Monterey Canyon and its way out to sea.
	deep = _canyon(p, CANYON, deep, wet)
	deep = _canyon(p, CANYON_OUT, deep, wet)
	# The level shelves (Atlantis's terrace stands up out of the canyon's floor).
	for shelf: Array in [WRECK_SHELF, RUINS_TERRACE, PIRATE_HOLLOW]:
		var middle: Vector2 = shelf[0]
		var w := (1.0 - smoothstep(float(shelf[1]), float(shelf[2]), p.distance_to(middle))) * smoothstep(0.0, 6.0, d)
		deep = lerpf(deep, float(shelf[3]) + (shelf[4] as Vector2).dot(p - middle), w)
	# The Carmel Canyon cuts past the liner's shelf.
	deep = _canyon(p, CARMEL, deep, wet)
	return deep


## Where the shelf's edge is (world x) at a place along the coast (world z).
static func edge_at(z: float) -> float:
	return _edge(z / K) * K


static func _edge(z: float) -> float:
	return EDGE + 7.0 * sin(z * 0.035) + 3.0 * sin(z * 0.11 + 1.0)


# A canyon cut into the floor: deepest along its line, its walls `half` out to either side.
static func _canyon(p: Vector2, line: Array, deep: float, wet: float) -> float:
	var best := INF
	var half := 0.0
	var floor_deep := 0.0
	for i in line.size() - 1:
		var a: Vector2 = line[i][0]
		var b: Vector2 = line[i + 1][0]
		var on := Geometry2D.get_closest_point_to_segment(p, a, b)
		var far := p.distance_to(on)
		if far < best:
			best = far
			var t := on.distance_to(a) / maxf(a.distance_to(b), 0.001)
			half = lerpf(float(line[i][1]), float(line[i + 1][1]), t)
			floor_deep = lerpf(float(line[i][2]), float(line[i + 1][2]), t)
	# (walls that waver, not ruled lines)
	half *= 1.0 + 0.15 * sin(p.x * 0.09 + p.y * 0.05)
	var cut := (1.0 - smoothstep(half * 0.35, half, best)) * wet
	return lerpf(deep, maxf(deep, floor_deep), cut)


static func _line_distance(p: Vector2, line: Array) -> float:
	var best := INF
	for i in line.size() - 1:
		best = minf(best, p.distance_to(Geometry2D.get_closest_point_to_segment(p, line[i], line[i + 1])))
	return best
