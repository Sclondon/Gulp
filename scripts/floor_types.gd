class_name FloorTypes
## What the sea floor is made of at every corner of Bay's 2 m grid: sand, rock, mud, shell hash,
## pink coralline crust, or Carmel's white sand (tools/BIOMES.md, section 3.1). Worked out once,
## by rules, from the floor's own shape (depth, slope, the shore) and the biomes' reef masks
## (`Biomes.REEFS`), the first time it is asked. The sand shows it by GameCommon's own painted
## kinds (`SandGround.paint_all`: rock is its SANDSTONE, mud its DIRT, shell its COARSE, crust its
## RED and white its WHITE, recoloured here), so no new shader program is made. Every placement
## rule in `Biomes` reads `of(x, z)`.

enum { SAND, ROCK, MUD, SHELL, CRUST, WHITE }

## Each type's kind on the sand (`Sand.Kind`), in the order of the enum (sand paints nothing).
const SAND_KIND := [-1, Sand.Kind.SANDSTONE, Sand.Kind.DIRT, Sand.Kind.COARSE, Sand.Kind.RED, Sand.Kind.WHITE]
## The colours they are drawn in here (Claude's picks, against the sea's grey sand): rock a cool
## grey-brown, mud a dark olive, crust coralline pink, Carmel's sand a pale white.
const ROCK_COLOUR := Color(0.38, 0.36, 0.36)
const MUD_COLOUR := Color(0.34, 0.31, 0.24)
const CRUST_COLOUR := Color(0.78, 0.5, 0.55)
const WHITE_COLOUR := Color(0.86, 0.85, 0.8)
## Rocky shores: within this of the shore (m) near the rocky points (world: a segment and how far
## along the shore from it the rock goes).
const SHORE_ROCK := 7.0
const ROCKY_POINTS := [
	[Vector2(-68.0, -136.0), Vector2(-68.0, -136.0), 26.0],  # Lighthouse Point, Santa Cruz
	[Vector2(9.6, 99.0), Vector2(17.6, 120.0), 14.0],  # Point Pinos to Cypress Point
	[Vector2(40.0, 104.0), Vector2(9.6, 99.0), 8.0],  # Cannery Row and Pacific Grove (behind the south kelp)
	[Vector2(9.6, 150.0), Vector2(9.6, 164.0), 18.0],  # Point Lobos
]
## Carmel's beach (world): white sand within this.
const CARMEL_BEACH := [Vector2(42.0, 144.0), 20.0]
## Steep ground (rise over run) that may be rock, where the noise allows: canyon walls, the shelf's edge.
const STEEP := 0.6

static var _types := PackedByteArray()
static var _slopes := PackedFloat32Array()
static var _cols := 0
static var _rows := 0


## The type of floor at a point (world x, z).
static func of(x: float, z: float) -> int:
	if _types.is_empty():
		_build()
	var c := clampi(int(round((x - Bay.WEST) / Bay.GRID)), 0, _cols - 1)
	var r := clampi(int(round((z - Bay.NORTH) / Bay.GRID)), 0, _rows - 1)
	return _types[r * _cols + c]


## How steep the floor is at a point (rise over run).
static func slope(x: float, z: float) -> float:
	if _types.is_empty():
		_build()
	var c := clampi(int(round((x - Bay.WEST) / Bay.GRID)), 0, _cols - 1)
	var r := clampi(int(round((z - Bay.NORTH) / Bay.GRID)), 0, _rows - 1)
	return _slopes[r * _cols + c]


## How many corners are of each type (for the checks).
static func counts() -> PackedInt32Array:
	if _types.is_empty():
		_build()
	var n := PackedInt32Array()
	n.resize(6)
	for t in _types:
		n[t] += 1
	return n


## Paints the floor's types on the sea's sand (its corners are Bay's grid) and recolours the kinds.
static func paint(sand: SandGround) -> void:
	if _types.is_empty():
		_build()
	for type in [ROCK, MUD, SHELL, CRUST, WHITE]:
		var shares := PackedByteArray()
		shares.resize(_types.size())
		for i in _types.size():
			shares[i] = 255 if _types[i] == type else 0
		sand.paint_all(SAND_KIND[type], shares)
	var look := sand.material()
	if look:
		look.set_shader_parameter(&"stone_colour", ROCK_COLOUR)
		look.set_shader_parameter(&"dirt_colour", MUD_COLOUR)
		look.set_shader_parameter(&"red_sand", CRUST_COLOUR)
		look.set_shader_parameter(&"white_sand", WHITE_COLOUR)


static func _build() -> void:
	_cols = int(round((Bay.EAST - Bay.WEST) / Bay.GRID)) + 1
	_rows = int(round((Bay.SOUTH - Bay.NORTH) / Bay.GRID)) + 1
	_types.resize(_cols * _rows)
	_slopes.resize(_cols * _rows)
	var walls := FastNoiseLite.new()
	walls.seed = 41
	walls.frequency = 0.06
	walls.fractal_octaves = 3
	var reefs: Array = []
	for reef: Dictionary in Biomes.REEFS:
		var noise := FastNoiseLite.new()
		noise.seed = int(reef.seed)
		noise.frequency = float(reef.freq)
		noise.fractal_octaves = 3
		reefs.append(noise)
	for r in _rows:
		var z := Bay.NORTH + r * Bay.GRID
		for c in _cols:
			var x := Bay.WEST + c * Bay.GRID
			var i := r * _cols + c
			var g := Sea.ground(x, z)
			var s := Vector2(Sea.ground(x + 1.0, z) - Sea.ground(x - 1.0, z), Sea.ground(x, z + 1.0) - Sea.ground(x, z - 1.0)).length() * 0.5
			_slopes[i] = s
			_types[i] = _type_at(Vector2(x, z), Sea.SURFACE - g, s, walls, reefs)


static func _type_at(p: Vector2, deep: float, steep: float, walls: FastNoiseLite, reefs: Array) -> int:
	var shore := Bay.shore_distance(p)
	if shore < -1.0:
		return SAND
	var chart := p / Bay.K
	# The slough and the harbours: mud.
	if Bay._line_distance(chart, Bay.SLOUGH) < Bay.SLOUGH_HALF + 2.0 and chart.x > 104.0:
		return MUD
	for harbour: Array in Bay.HARBOURS:
		if chart.distance_to(harbour[0]) < float(harbour[1]) * 0.75:
			return MUD
	# The biomes' reefs (kelp on rock, the outcrop's talus): rock, crust in the barrens.
	for k in Biomes.REEFS.size():
		var reef: Dictionary = Biomes.REEFS[k]
		if Biomes.on_reef(reef, reefs[k], p, deep):
			for barren: Array in reef.get("barrens", []):
				if p.distance_to(barren[0]) < float(barren[1]):
					return CRUST
			return ROCK
	# Rocky points along the shore.
	if shore < SHORE_ROCK:
		for point: Array in ROCKY_POINTS:
			var on := Geometry2D.get_closest_point_to_segment(p, point[0], point[1])
			if p.distance_to(on) < float(point[2]) + SHORE_ROCK:
				return ROCK
	if p.distance_to(CARMEL_BEACH[0]) < float(CARMEL_BEACH[1]) and deep < 9.0:
		return WHITE
	# Steep walls (the canyons, the shelf's edge): rock in bands, mud between.
	if steep > STEEP and deep > 18.0:
		return ROCK if walls.get_noise_2d(p.x, p.y * 0.35) > -0.1 else MUD
	# The canyons' floors and the deep basin: mud.
	if deep > 45.0 and steep < 0.35:
		return MUD
	return SAND
