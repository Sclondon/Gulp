class_name Biomes
extends RefCounted
## The rule-based placer of the sea's plants and floor pieces (tools/BIOMES.md, sections 3 and 6):
## one table a place (`TABLES`), each a list of layers, each layer a rule: what grows, on which
## floor (`FloorTypes`), how deep, how steep, how thick at the place's core and at its edge, in
## what clumps, how far apart, how tall. Same seed, same sea every time. `Scenery` runs it and
## draws what comes out: floor pieces through its LodField (near and far), kelp, grass and seaweed
## through their own components (each draws by cells with a near and a far of its own).
##
## The numbers are Claude's (the level design's) picks; change freely. Budgets are in BIOMES.md.

## The reefs: where the floor is rock for a biome (read by FloorTypes). Inside `r` of `at`, within
## `depth`, where the place's noise (`freq`, `seed`, its axes turned by `turn` and the first one
## squeezed by `stretch`, so reefs run as fingers) is above `above`, rising towards `rise` at the
## rim (so the reef breaks up towards its edge); never in its `channels` (polylines, half width).
const REEFS := [
	{"name": "kelp_south", "at": Vector2(53.0, 42.0), "r": 34.0, "depth": [4.5, 17.5], "freq": 0.07, "seed": 21, "above": -0.3, "rise": 0.35,
	 "turn": 0.05, "stretch": 0.35,
	 "channels": [[[Vector2(92.0, 47.0), Vector2(62.0, 47.0), Vector2(43.0, 49.0), Vector2(16.0, 52.0)], 3.2],
			[[Vector2(90.0, 28.0), Vector2(60.0, 27.0), Vector2(24.0, 22.0)], 2.6]],
	 "barrens": [[Vector2(60.0, 37.0), 6.0]]},
	{"name": "kelp_north", "at": Vector2(54.4, -64.0), "r": 22.0, "depth": [3.0, 12.5], "freq": 0.09, "seed": 22, "above": -0.15, "rise": 0.4,
	 "turn": -0.5, "stretch": 0.3, "channels": [], "barrens": []},
	{"name": "outcrop", "at": Vector2(-98.0, -24.0), "r": 20.0, "depth": [0.0, 26.0], "freq": 0.12, "seed": 23, "above": -0.5, "rise": 0.4,
	 "turn": 0.0, "stretch": 1.0, "channels": [], "barrens": []},
	{"name": "carmel", "at": Vector2(14.0, 151.0), "r": 13.0, "depth": [2.5, 15.0], "freq": 0.1, "seed": 24, "above": -0.25, "rise": 0.4,
	 "turn": 0.0, "stretch": 0.6, "channels": [], "barrens": []},
]

## The layers of each place. Keys (all optional but `what`):
## what: "prop" (the sea floor kit's `pieces`), "kelp", "grass", "seaweed" (`kind`: SeaweedBed.Kind)
## area: [middle, radius]; on: FloorTypes; depth: [from, to] m; slope_max; density: [core, edge] per
## 100 m², falling over the outer `edge` m of the area; noise: [freq, seed, above]; spacing: m apart
## on the jittered grid; clump: [least, most, within m]; size: [from, to] (scale for props, metres for
## plants); reach / edge_reach (kelp: its length as a share of the water's depth); lift (m);
## near_rock: only within this of a floor piece already placed; keep: [[polyline, half]...] clear.
const TABLES := {
	"kelp_south": {"area": [Vector2(53.0, 42.0), 34.0], "edge": 8.0, "layers": [
		{"what": "prop", "pieces": ["rock_boulder", "rock_split", "rock_ledge", "rock_stack", "rock_boulder_small"], "on": [1, 4], "depth": [5.0, 17.0],
		 "density": [2.6, 0.8], "spacing": 3.2, "clump": [1, 2, 3.0], "size": [0.8, 1.5], "lift": -0.25},
		{"what": "kelp", "on": [1], "depth": [5.5, 17.0], "slope_max": 0.8, "density": [12.0, 2.5], "noise": [0.09, 3, -0.45],
		 "spacing": 1.7, "clump": [1, 2, 1.4], "reach": [1.05, 1.4], "edge_reach": [0.55, 0.95]},
		{"what": "seaweed", "kind": 4, "on": [1], "depth": [4.0, 16.0], "density": [18.0, 5.0], "noise": [0.15, 4, -0.2],
		 "spacing": 0.9, "clump": [2, 6, 1.8], "size": [0.7, 1.3]},
		{"what": "seaweed", "kind": 2, "on": [1, 4], "depth": [3.0, 17.0], "density": [30.0, 10.0], "noise": [0.2, 5, -0.25],
		 "spacing": 0.7, "clump": [2, 6, 1.0], "size": [0.16, 0.3]},
		{"what": "seaweed", "kind": 3, "on": [1], "depth": [2.0, 8.0], "density": [6.0, 2.0], "spacing": 1.6, "size": [1.8, 3.0]},
		{"what": "prop", "pieces": ["urchin_purple"], "on": [4], "depth": [4.0, 17.0], "density": [45.0, 45.0], "spacing": 0.7,
		 "clump": [1, 3, 0.6], "size": [0.9, 1.3], "lift": -0.02},
		{"what": "prop", "pieces": ["urchin_purple", "urchin_red"], "on": [1], "depth": [5.0, 17.0], "density": [4.0, 1.0], "spacing": 1.2,
		 "clump": [2, 5, 1.0], "near_rock": 2.0, "size": [0.9, 1.3], "lift": -0.02},
		{"what": "prop", "pieces": ["sea_fan_red", "sea_fan_gold", "hydrocoral", "vase_sponge", "puffball_sponges", "strawberry_anemones"], "on": [1],
		 "depth": [8.0, 17.0], "density": [3.0, 0.8], "spacing": 1.5, "near_rock": 2.5, "size": [0.9, 1.6], "lift": -0.02},
		{"what": "prop", "pieces": ["ochre_star", "bat_star", "green_anemone"], "on": [1, 4], "depth": [4.0, 17.0], "density": [3.0, 1.0],
		 "spacing": 1.4, "size": [0.9, 1.5], "lift": -0.02},
	]},
	"kelp_north": {"area": [Vector2(54.4, -64.0), 22.0], "edge": 6.0, "layers": [
		{"what": "prop", "pieces": ["rock_ledge", "rock_slab", "rock_split"], "on": [1], "depth": [3.0, 12.5], "density": [2.0, 0.8],
		 "spacing": 3.5, "size": [0.8, 1.3], "lift": -0.35},
		{"what": "kelp", "on": [1], "depth": [5.0, 12.5], "slope_max": 0.8, "density": [7.0, 2.0], "noise": [0.1, 6, -0.3],
		 "spacing": 1.9, "clump": [1, 2, 1.5], "reach": [1.0, 1.3], "edge_reach": [0.6, 0.95]},
		{"what": "seaweed", "kind": 4, "on": [1], "depth": [3.0, 12.5], "density": [20.0, 6.0], "spacing": 1.0, "clump": [2, 5, 1.6], "size": [0.6, 1.2]},
		{"what": "seaweed", "kind": 2, "on": [1], "depth": [2.0, 12.5], "density": [22.0, 8.0], "spacing": 0.8, "clump": [2, 5, 1.0], "size": [0.16, 0.3]},
		{"what": "seaweed", "kind": 3, "on": [1], "depth": [2.0, 7.0], "density": [6.0, 2.0], "spacing": 1.6, "size": [1.6, 2.6]},
		{"what": "prop", "pieces": ["ochre_star", "bat_star", "urchin_purple", "green_anemone", "puffball_sponges"], "on": [1], "depth": [3.0, 12.5],
		 "density": [3.0, 1.0], "spacing": 1.4, "size": [0.9, 1.4], "lift": -0.02},
	]},
	"outcrop": {"area": [Vector2(-98.0, -24.0), 20.0], "edge": 6.0, "layers": [
		{"what": "prop", "pieces": ["rock_boulder", "rock_boulder_small", "rock_split"], "on": [1], "depth": [16.0, 26.0], "density": [5.0, 0.5],
		 "spacing": 2.6, "clump": [1, 3, 2.5], "size": [0.9, 1.6], "lift": -0.25},
		{"what": "kelp", "on": [1], "depth": [4.0, 16.0], "density": [6.0, 2.0], "spacing": 2.2, "reach": [1.05, 1.3], "edge_reach": [0.7, 1.0]},
		{"what": "prop", "pieces": ["strawberry_anemones", "hydrocoral", "sea_fan_red", "vase_sponge", "green_anemone", "ochre_star"], "on": [1],
		 "depth": [10.0, 26.0], "density": [4.0, 1.0], "spacing": 1.3, "near_rock": 2.5, "size": [0.9, 1.6], "lift": -0.02},
		{"what": "seaweed", "kind": 2, "on": [1], "depth": [3.0, 24.0], "density": [18.0, 6.0], "spacing": 0.9, "clump": [2, 5, 1.0], "size": [0.16, 0.28]},
	]},
	"carmel": {"area": [Vector2(14.0, 151.0), 13.0], "edge": 4.0, "layers": [
		{"what": "prop", "pieces": ["rock_boulder", "rock_split", "rock_stack"], "on": [1], "depth": [2.5, 15.0], "density": [3.0, 1.0],
		 "spacing": 3.0, "size": [0.8, 1.4], "lift": -0.25},
		{"what": "kelp", "on": [1], "depth": [5.0, 15.0], "density": [10.0, 3.0], "spacing": 1.8, "clump": [1, 2, 1.4], "reach": [1.05, 1.35], "edge_reach": [0.6, 0.95]},
		{"what": "seaweed", "kind": 4, "on": [1], "depth": [3.0, 14.0], "density": [25.0, 8.0], "spacing": 1.0, "clump": [2, 5, 1.6], "size": [0.7, 1.2]},
		{"what": "seaweed", "kind": 2, "on": [1], "depth": [2.0, 15.0], "density": [40.0, 10.0], "spacing": 0.8, "clump": [2, 5, 1.0], "size": [0.16, 0.3]},
	]},
	# The eelgrass meadow: on sand and mud 1.5 to 8 m (the zone's circle reaches the canyon's lip:
	# the depth band stops it), thick at its core, bare blowouts where the noise is low, a trail.
	"grass": {"area": [Vector2(-11.2, 78.4), 18.0], "edge": 5.0, "keep": [[[Vector2(-26.0, 84.0), Vector2(-12.0, 80.0), Vector2(2.0, 86.0)], 1.0]], "layers": [
		{"what": "grass", "on": [0, 2], "depth": [1.5, 8.0], "slope_max": 0.35, "density": [380.0, 70.0], "noise": [0.12, 7, -0.5],
		 "spacing": 0.5, "clump": [1, 3, 0.6], "size": [0.85, 1.2], "edge_size": [0.4, 0.7]},
		{"what": "seaweed", "kind": 0, "on": [0, 2], "depth": [1.0, 8.0], "density": [8.0, 3.0], "spacing": 1.0, "clump": [1, 3, 0.8], "size": [0.25, 0.5]},
	]},
	# The slough: eelgrass along the channel's shallow edges, sea lettuce on the mud.
	"slough": {"area": [Vector2(108.0, -18.0), 26.0], "edge": 3.0, "layers": [
		{"what": "grass", "on": [2], "depth": [1.0, 2.8], "slope_max": 0.6, "density": [250.0, 100.0], "spacing": 0.5, "clump": [1, 3, 0.6], "size": [0.45, 0.8]},
		{"what": "seaweed", "kind": 0, "on": [2], "depth": [0.6, 4.5], "density": [10.0, 4.0], "spacing": 1.0, "clump": [1, 3, 0.8], "size": [0.25, 0.45]},
	]},
	# The harbours' floors and the breakwater's foot.
	"docks_monterey": {"area": [Vector2(35.2, 78.4), 16.0], "edge": 3.0, "layers": [
		{"what": "seaweed", "kind": 0, "on": [2, 0], "depth": [1.0, 7.0], "density": [5.0, 2.0], "spacing": 1.2, "clump": [1, 3, 0.8], "size": [0.25, 0.45]},
		{"what": "seaweed", "kind": 1, "on": [1], "depth": [0.0, 3.0], "density": [40.0, 15.0], "spacing": 0.6, "clump": [2, 5, 0.8], "size": [0.25, 0.4]},
	]},
	# The rocky points of the beach strip: rockweed, feather boa, anemones, stars (surfgrass is not
	# in the kit yet: BIOMES.md section 8).
	"points": {"area": [], "edge": 2.0, "layers": [
		{"what": "seaweed", "kind": 1, "on": [1], "depth": [0.3, 2.0], "density": [25.0, 10.0], "spacing": 0.6, "clump": [2, 5, 0.8], "size": [0.25, 0.4]},
		{"what": "seaweed", "kind": 3, "on": [1], "depth": [1.5, 5.5], "density": [5.0, 2.0], "spacing": 1.6, "size": [1.5, 2.5]},
		{"what": "prop", "pieces": ["green_anemone", "ochre_star", "mussel_clump", "bat_star"], "on": [1], "depth": [0.3, 5.5], "density": [5.0, 2.0],
		 "spacing": 1.0, "clump": [1, 3, 0.8], "size": [0.9, 1.4], "lift": -0.02},
	]},
	# The canyons' rock bands and the shelf's edge: what grows on deep rock.
	"walls": {"area": [], "edge": 2.0, "layers": [
		{"what": "prop", "pieces": ["rock_ledge", "rock_slab", "rock_split"], "on": [1], "depth": [20.0, 95.0], "slope_min": 0.6, "density": [0.7, 0.7],
		 "spacing": 5.0, "size": [1.0, 1.6], "lift": -0.6, "downhill": true},
		{"what": "prop", "pieces": ["vase_sponge", "sea_fan_red", "puffball_sponges", "feather_dusters"], "on": [1], "depth": [22.0, 95.0], "slope_min": 0.4,
		 "density": [2.0, 2.0], "spacing": 1.8, "clump": [1, 3, 1.2], "size": [1.4, 2.4], "lift": -0.05},
	]},
}

## The places' order (big things first in each; the tables above).
const ORDER := ["kelp_south", "kelp_north", "outcrop", "carmel", "grass", "slough", "docks_monterey", "points", "walls"]
## The whole map's corners for the tables without an area of their own ("points", "walls").
const WHOLE := [Vector2(-157.0, -136.0), Vector2(120.0, 155.0)]

# What came out: floor pieces (name -> [transforms, colours]), kelp (places, lengths), grass
# (places, heights), seaweed (places, sizes, kinds), and how many of each layer (for the checks).
var pieces := {}
var kelp_places := PackedVector3Array()
var kelp_lengths := PackedFloat32Array()
var grass_places := PackedVector3Array()
var grass_heights := PackedFloat32Array()
var weed_places := PackedVector3Array()
var weed_sizes := PackedFloat32Array()
var weed_kinds := PackedInt32Array()
var made := {}

var _rng := RandomNumberGenerator.new()
var _props: GDScript
var _rocks: Array[Vector3] = []   # floor pieces' middles (x, z) and how far they reach (y)
var _kept: Callable


## Whether a point is on a reef's rock (FloorTypes asks: `noise` is the reef's own).
static func on_reef(reef: Dictionary, noise: FastNoiseLite, p: Vector2, deep: float) -> bool:
	var off := p - (reef.at as Vector2)
	var r: float = reef.r
	if off.length() > r or deep < float(reef.depth[0]) or deep > float(reef.depth[1]):
		return false
	for channel: Array in reef.channels:
		if _line_distance(p, channel[0]) < float(channel[1]):
			return false
	var turned := off.rotated(-float(reef.turn))
	var n := noise.get_noise_2d(turned.x * float(reef.stretch), turned.y)
	return n > lerpf(float(reef.above), float(reef.rise), smoothstep(0.55, 1.0, off.length() / r))


static func _line_distance(p: Vector2, line: Array) -> float:
	var best := INF
	for i in line.size() - 1:
		best = minf(best, p.distance_to(Geometry2D.get_closest_point_to_segment(p, line[i], line[i + 1])))
	return best


## Places every table's layers. `props` is the sea floor kit's script; `kept_clear(at)` says
## whether a point is kept clear for a wreck or Atlantis.
func run(props: GDScript, kept_clear: Callable) -> void:
	_props = props
	_kept = kept_clear
	_rng.seed = 1789
	for place: String in ORDER:
		var table: Dictionary = TABLES[place]
		for k in table.layers.size():
			var layer: Dictionary = table.layers[k]
			var n := _layer(table, layer)
			made["%s %d %s" % [place, k, layer.get("pieces", [layer.what])[0] if layer.what == "prop" else layer.what + str(layer.get("kind", ""))]] = n


func _layer(table: Dictionary, layer: Dictionary) -> int:
	if layer.what == "prop" and _props == null:
		return 0
	var area: Array = table.area
	var low: Vector2 = WHOLE[0] if area.is_empty() else (area[0] as Vector2) - Vector2.ONE * float(area[1])
	var high: Vector2 = WHOLE[1] if area.is_empty() else (area[0] as Vector2) + Vector2.ONE * float(area[1])
	var spacing: float = layer.get("spacing", 1.0)
	var density: Array = layer.get("density", [1.0, 1.0])
	var noise: FastNoiseLite = null
	if layer.has("noise"):
		noise = FastNoiseLite.new()
		noise.frequency = float(layer.noise[0])
		noise.seed = int(layer.noise[1])
		noise.fractal_octaves = 2
	var clump: Array = layer.get("clump", [1, 1, 0.0])
	var count := 0
	var z := low.y
	while z < high.y:
		var x := low.x
		while x < high.x:
			var at := Vector2(x + _rng.randf() * spacing, z + _rng.randf() * spacing)
			x += spacing
			var edge := _edge(table, at)
			if edge < 0.0 or not (layer.get("on", [0]) as Array).has(FloorTypes.of(at.x, at.y)):
				continue
			var d: float = lerpf(float(density[1]), float(density[0]), edge)
			if noise and noise.get_noise_2d(at.x, at.y) < float(layer.noise[2]):
				continue
			if _rng.randf() > d * spacing * spacing / 100.0:
				continue
			var children := _rng.randi_range(int(clump[0]), int(clump[1]))
			for c in children:
				var p := at if c == 0 else at + Vector2.from_angle(_rng.randf() * TAU) * _rng.randf_range(0.3, float(clump[2]))
				if _fits(table, layer, p):
					_put(layer, p, edge)
					count += 1
		z += spacing
	return count


# How far into its area a point is, 0 at the rim to 1 past `edge` (less than 0: outside).
func _edge(table: Dictionary, at: Vector2) -> float:
	var area: Array = table.area
	if area.is_empty():
		return 1.0
	var inside := float(area[1]) - at.distance_to(area[0])
	if inside < 0.0:
		return -1.0
	return smoothstep(0.0, float(table.edge), inside)


func _fits(table: Dictionary, layer: Dictionary, p: Vector2) -> bool:
	if Bay.shore_distance(p) < 0.3:
		return false
	var deep := Sea.SURFACE - Sea.ground(p.x, p.y)
	var depth: Array = layer.get("depth", [0.0, 999.0])
	if deep < float(depth[0]) or deep > float(depth[1]):
		return false
	if not (layer.get("on", [0]) as Array).has(FloorTypes.of(p.x, p.y)):
		return false
	var steep := FloorTypes.slope(p.x, p.y)
	if steep > float(layer.get("slope_max", 99.0)) or steep < float(layer.get("slope_min", 0.0)):
		return false
	for keep: Array in table.get("keep", []):
		if _line_distance(p, keep[0]) < float(keep[1]):
			return false
	if _kept.is_valid() and _kept.call(p):
		return false
	if layer.has("near_rock"):
		var reach: float = layer.near_rock
		var near := false
		for rock in _rocks:
			if Vector2(rock.x, rock.z).distance_to(p) < rock.y + reach:
				near = true
				break
		if not near:
			return false
	elif layer.what != "prop" or not (layer.pieces as Array)[0].begins_with("rock"):
		# (nothing grows inside a rock: keep out of the floor pieces' feet)
		for rock in _rocks:
			if Vector2(rock.x, rock.z).distance_to(p) < rock.y * 0.55:
				return false
	return true


func _put(layer: Dictionary, p: Vector2, edge: float) -> void:
	var floor_y := Sea.ground(p.x, p.y)
	var deep := Sea.SURFACE - floor_y
	var size: Array = layer.get("size", [1.0, 1.0])
	match layer.what:
		"kelp":
			var reach: Array = layer.reach if edge > 0.6 else layer.get("edge_reach", layer.reach)
			kelp_places.append(Vector3(p.x, floor_y - 0.1, p.y))
			kelp_lengths.append(minf(deep * _rng.randf_range(float(reach[0]), float(reach[1])), 25.0))
		"grass":
			var heights: Array = size if edge > 0.5 else layer.get("edge_size", size)
			grass_places.append(Vector3(p.x, floor_y - 0.03, p.y))
			grass_heights.append(_rng.randf_range(float(heights[0]), float(heights[1])))
		"seaweed":
			weed_places.append(Vector3(p.x, floor_y - 0.02, p.y))
			weed_sizes.append(_rng.randf_range(float(size[0]), float(size[1])) * lerpf(0.75, 1.0, edge))
			weed_kinds.append(int(layer.kind))
		"prop":
			var list: Array = layer.pieces
			var piece: String = list[_rng.randi() % list.size()]
			var big := _rng.randf_range(float(size[0]), float(size[1]))
			var basis := Basis(Vector3.UP, _rng.randf() * TAU)
			if layer.get("downhill", false):
				# (a ledge on a wall faces down the slope)
				var fall := Vector2(Sea.ground(p.x + 1.0, p.y) - Sea.ground(p.x - 1.0, p.y), Sea.ground(p.x, p.y + 1.0) - Sea.ground(p.x, p.y - 1.0))
				basis = Basis(Vector3.UP, atan2(-fall.x, -fall.y))
			add_piece(piece, Transform3D(basis.scaled(Vector3.ONE * big), Vector3(p.x, floor_y + float(layer.get("lift", 0.0)), p.y)))
			if piece.begins_with("rock"):
				var reach := (_props.call(&"size_of", piece) as Vector3)
				_rocks.append(Vector3(p.x, maxf(reach.x, reach.z) * 0.5 * big, p.y))


## A floor piece placed (its spheres go to the sea's rocks), tinted with one of its tints.
func add_piece(piece: String, where: Transform3D) -> void:
	if not pieces.has(piece):
		pieces[piece] = [[], []]
	var tints: PackedColorArray = _props.call(&"tints_of", piece)
	pieces[piece][0].append(where)
	pieces[piece][1].append(tints[_rng.randi() % tints.size()] if tints.size() > 0 else Color.WHITE)
	var big := where.basis.get_scale().x
	for sphere: Vector4 in _props.call(&"spheres_of", piece):
		var middle := where * Vector3(sphere.x, sphere.y, sphere.z)
		Sea.add_rock(Vector4(middle.x, middle.y, middle.z, sphere.w * big))


## Growth on a thing's surface (BIOMES.md 3.4): `count` pieces from `list` on its spheres (world
## x, y, z, radius), on faces whose normal's y is within [low, high], thickest high up.
func grow_on(spheres: Array, list: Array, count: int, low: float, high: float, size := Vector2(0.9, 1.5)) -> int:
	if spheres.is_empty() or _props == null:
		return 0
	var top := -INF
	var bottom := INF
	for s: Vector4 in spheres:
		top = maxf(top, s.y + s.w)
		bottom = minf(bottom, s.y - s.w)
	var placed := 0
	var tries := 0
	while placed < count and tries < count * 12:
		tries += 1
		var s: Vector4 = spheres[_rng.randi() % spheres.size()]
		var n := Vector3(_rng.randf_range(-1.0, 1.0), _rng.randf_range(-1.0, 1.0), _rng.randf_range(-1.0, 1.0)).normalized()
		if n.y < low or n.y > high:
			continue
		var at := Vector3(s.x, s.y, s.z) + n * s.w * 0.92
		if _rng.randf() > lerpf(0.35, 1.0, inverse_lerp(bottom, top, at.y)):
			continue
		if at.y < Sea.ground(at.x, at.z) - 0.05 or at.y > Sea.SURFACE - 0.3:
			continue
		# (inside another sphere of the thing is inside it: skip)
		var buried := false
		for o: Vector4 in spheres:
			if o != s and Vector3(o.x, o.y, o.z).distance_to(at) < o.w * 0.85:
				buried = true
				break
		if buried:
			continue
		var up := n if n.y > -0.95 else Vector3.UP
		var side := up.cross(Vector3.RIGHT if absf(up.x) < 0.9 else Vector3.FORWARD).normalized()
		var basis := Basis(side, up, side.cross(up)).orthonormalized().rotated(up, _rng.randf() * TAU)
		var piece: String = list[_rng.randi() % list.size()]
		var where := Transform3D(basis.scaled(Vector3.ONE * _rng.randf_range(size.x, size.y)), at)
		if not pieces.has(piece):
			pieces[piece] = [[], []]
		var tints: PackedColorArray = _props.call(&"tints_of", piece)
		pieces[piece][0].append(where)
		pieces[piece][1].append(tints[_rng.randi() % tints.size()] if tints.size() > 0 else Color.WHITE)
		placed += 1
	return placed
