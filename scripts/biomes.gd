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
		 "density": [2.6, 0.8], "spacing": 3.2, "clump": [1, 2, 3.0], "size": [0.8, 1.5], "lift": -0.25, "tint": Color(0.6, 0.55, 0.5)},
		{"what": "prop", "pieces": ["reef_slab_a", "reef_slab_b", "reef_slab_c"], "on": [1, 4], "depth": [4.5, 17.0], "slope_max": 0.6, "density": [4.4, 2.5],
		 "spacing": 3.6, "size": [0.8, 1.3], "lift": -0.35, "tint": Color(0.62, 0.57, 0.52)},
		{"what": "prop", "pieces": ["bull_kelp"], "on": [1], "depth": [5.0, 13.0], "slope_max": 0.7, "density": [0.0, 4.0], "spacing": 2.5, "to_surface": 8.0},
		{"what": "kelp", "on": [1], "depth": [5.5, 17.0], "slope_max": 0.8, "density": [4.2, 1.0], "noise": [0.09, 3, -0.45],
		 "spacing": 3.0, "clump": [4, 7, 1.0, 0.25], "reach": [1.2, 1.6], "edge_reach": [0.55, 0.95], "canopy": [3, 7.0]},
		{"what": "prop", "pieces": ["understory_kelp", "understory_kelp", "understory_kelp_b"], "on": [1], "depth": [4.0, 16.0], "density": [22.0, 6.0],
		 "noise": [0.15, 4, -0.2], "spacing": 0.9, "clump": [2, 6, 1.8], "size": [0.8, 1.4], "lift": -0.03},
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
		 "spacing": 3.5, "size": [0.8, 1.3], "lift": -0.35, "tint": Color(0.68, 0.64, 0.58)},
		{"what": "prop", "pieces": ["reef_slab_a", "reef_slab_b", "reef_slab_c"], "on": [1], "depth": [3.0, 12.5], "slope_max": 0.6, "density": [4.0, 2.0],
		 "spacing": 3.6, "size": [0.7, 1.1], "lift": -0.4, "tint": Color(0.7, 0.66, 0.6)},
		{"what": "kelp", "on": [1], "depth": [8.0, 12.5], "slope_max": 0.8, "density": [1.2, 0.5], "noise": [0.1, 6, -0.3],
		 "spacing": 3.6, "clump": [2, 3, 0.7, 0.25], "reach": [1.0, 1.3], "edge_reach": [0.7, 0.95]},
		# (the north forest is the bull kelp one: BIOMES.md 5.3)
		{"what": "prop", "pieces": ["bull_kelp"], "on": [1], "depth": [3.0, 12.5], "slope_max": 0.8, "density": [12.0, 4.0], "spacing": 1.8,
		 "clump": [1, 2, 0.9, 0.4], "to_surface": 8.0},
		{"what": "prop", "pieces": ["understory_kelp", "understory_kelp_b", "understory_kelp_b"], "on": [1], "depth": [3.0, 12.5], "density": [20.0, 6.0],
		 "spacing": 1.0, "clump": [2, 5, 1.6], "size": [0.7, 1.2], "lift": -0.03},
		{"what": "seaweed", "kind": 2, "on": [1], "depth": [2.0, 12.5], "density": [22.0, 8.0], "spacing": 0.8, "clump": [2, 5, 1.0], "size": [0.16, 0.3]},
		{"what": "seaweed", "kind": 3, "on": [1], "depth": [2.0, 7.0], "density": [6.0, 2.0], "spacing": 1.6, "size": [1.6, 2.6]},
		{"what": "prop", "pieces": ["ochre_star", "bat_star", "urchin_purple", "green_anemone", "puffball_sponges"], "on": [1], "depth": [3.0, 12.5],
		 "density": [3.0, 1.0], "spacing": 1.4, "size": [0.9, 1.4], "lift": -0.02},
	]},
	"outcrop": {"area": [Vector2(-98.0, -24.0), 20.0], "edge": 6.0, "layers": [
		{"what": "prop", "pieces": ["rock_boulder", "rock_boulder_small", "rock_split"], "on": [1], "depth": [16.0, 26.0], "density": [5.0, 0.5],
		 "spacing": 2.6, "clump": [1, 3, 2.5], "size": [0.9, 1.6], "lift": -0.25},
		{"what": "prop", "pieces": ["reef_slab_a", "reef_slab_b", "reef_slab_c"], "on": [1], "depth": [14.0, 26.0], "slope_max": 0.6, "density": [3.0, 1.0],
		 "spacing": 3.8, "size": [0.8, 1.2], "lift": -0.35, "tint": Color(0.66, 0.62, 0.58)},
		# (the outcrop's kelp is a ring of bull kelp, so the ship lies in open sand under light: BIOMES.md 5.6)
		{"what": "prop", "pieces": ["bull_kelp"], "on": [1], "depth": [3.0, 14.0], "density": [8.0, 2.0], "spacing": 2.0, "to_surface": 8.0},
		{"what": "prop", "pieces": ["strawberry_anemones", "hydrocoral", "sea_fan_red", "vase_sponge", "green_anemone", "ochre_star"], "on": [1],
		 "depth": [10.0, 26.0], "density": [4.0, 1.0], "spacing": 1.3, "near_rock": 2.5, "size": [0.9, 1.6], "lift": -0.02},
		{"what": "seaweed", "kind": 2, "on": [1], "depth": [3.0, 24.0], "density": [18.0, 6.0], "spacing": 0.9, "clump": [2, 5, 1.0], "size": [0.16, 0.28]},
	]},
	"carmel": {"area": [Vector2(14.0, 151.0), 13.0], "edge": 4.0, "layers": [
		{"what": "prop", "pieces": ["rock_boulder", "rock_split", "rock_stack"], "on": [1], "depth": [2.5, 15.0], "density": [3.0, 1.0],
		 "spacing": 3.0, "size": [0.8, 1.4], "lift": -0.25, "tint": Color(0.62, 0.57, 0.52)},
		{"what": "prop", "pieces": ["reef_slab_a", "reef_slab_b", "reef_slab_c"], "on": [1], "depth": [2.5, 15.0], "slope_max": 0.6, "density": [4.0, 2.0],
		 "spacing": 3.6, "size": [0.7, 1.2], "lift": -0.35, "tint": Color(0.64, 0.6, 0.55)},
		{"what": "kelp", "on": [1], "depth": [5.0, 15.0], "density": [4.0, 1.5], "spacing": 3.0, "clump": [3, 5, 0.8, 0.25], "reach": [1.2, 1.5], "edge_reach": [0.6, 0.95], "canopy": [1, 6.0]},
		{"what": "prop", "pieces": ["bull_kelp"], "on": [1], "depth": [4.0, 13.0], "density": [0.0, 5.0], "spacing": 2.2, "to_surface": 8.0},
		{"what": "prop", "pieces": ["understory_kelp", "understory_kelp_b"], "on": [1], "depth": [3.0, 14.0], "density": [25.0, 8.0], "spacing": 1.0, "clump": [2, 5, 1.6], "size": [0.7, 1.2], "lift": -0.03},
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
	# The rocky points of the beach strip: rockweed, surfgrass in the surge, feather boa, anemones, stars.
	"points": {"area": [], "edge": 2.0, "layers": [
		{"what": "prop", "pieces": ["surfgrass"], "on": [1], "depth": [0.5, 4.0], "slope_max": 0.8, "density": [40.0, 15.0], "noise": [0.12, 43, -0.3],
		 "spacing": 1.0, "clump": [3, 7, 0.9], "size": [0.8, 1.3], "lift": -0.02},
		{"what": "seaweed", "kind": 1, "on": [1], "depth": [0.3, 2.0], "density": [25.0, 10.0], "spacing": 0.6, "clump": [2, 5, 0.8], "size": [0.25, 0.4]},
		{"what": "seaweed", "kind": 3, "on": [1], "depth": [1.5, 5.5], "density": [5.0, 2.0], "spacing": 1.6, "size": [1.5, 2.5]},
		{"what": "prop", "pieces": ["green_anemone", "ochre_star", "mussel_clump", "bat_star"], "on": [1], "depth": [0.3, 5.5], "density": [5.0, 2.0],
		 "spacing": 1.0, "clump": [1, 3, 0.8], "size": [0.9, 1.4], "lift": -0.02},
	]},
	# The beach strip's sand dollar band, where it meets the shelf (BIOMES.md 5.1): beds on edge.
	"beach": {"area": [], "edge": 2.0, "layers": [
		{"what": "prop", "pieces": ["sand_dollars"], "on": [0, 5], "depth": [3.5, 5.0], "slope_max": 0.25, "density": [20.0, 20.0], "noise": [0.06, 47, -0.5],
		 "spacing": 2.0, "clump": [1, 3, 1.6, 1.0], "size": [0.8, 1.3], "lift": -0.01},
	]},
	# The sand flats off Santa Cruz (BIOMES.md 5.4): the sea pen meadow on the deeper, finer half.
	"sand_flats": {"area": [Vector2(-74.0, -78.0), 34.0], "edge": 6.0, "keep": [[[Vector2(-88.0, -72.0), Vector2(-62.0, -84.0)], 5.0]], "layers": [
		{"what": "prop", "pieces": ["sea_pen"], "on": [0, 2], "depth": [14.5, 22.0], "slope_max": 0.3, "density": [25.0, 3.0], "noise": [0.07, 31, -0.15],
		 "spacing": 1.3, "clump": [3, 8, 1.5], "size": [0.8, 1.3], "lift": -0.04},
	]},
	# The canyon's floor and the deep basin (BIOMES.md 5.5): tall white sea pens and sea whips on the mud.
	"canyon_floor": {"area": [], "edge": 2.0, "layers": [
		{"what": "prop", "pieces": ["sea_pen_deep", "sea_pen_deep", "sea_whip"], "on": [2], "depth": [60.0, 100.0], "slope_max": 0.3, "density": [6.0, 6.0],
		 "noise": [0.05, 53, -0.1], "spacing": 2.5, "clump": [4, 10, 2.0], "size": [0.8, 1.3], "lift": -0.05},
	]},
	# The canyons' rock bands and the shelf's edge: what grows on deep rock.
	"walls": {"area": [], "edge": 2.0, "layers": [
		{"what": "prop", "pieces": ["rock_ledge", "rock_slab", "rock_split"], "on": [1], "depth": [20.0, 95.0], "slope_min": 0.6, "density": [0.7, 0.7],
		 "spacing": 5.0, "size": [1.0, 1.6], "lift": -0.6, "downhill": true},
		{"what": "prop", "pieces": ["vase_sponge", "sea_fan_red", "puffball_sponges", "feather_dusters"], "on": [1], "depth": [22.0, 95.0], "slope_min": 0.4,
		 "density": [2.0, 2.0], "spacing": 1.8, "clump": [1, 3, 1.2], "size": [1.4, 2.4], "lift": -0.05},
	]},
}

## Which way the water streams over the sea floor (Scenery.current: the plants lean and stream this way).
const CURRENT := Vector2(0.3, 0.1)

## The places' order (big things first in each; the tables above).
const ORDER := ["kelp_south", "kelp_north", "outcrop", "carmel", "grass", "slough", "docks_monterey", "points", "beach", "sand_flats", "canyon_floor", "walls"]
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
	if layer.what == "prop":
		# (a piece of the kit not built yet is left out)
		var can: Array = (layer.pieces as Array).filter(func(p: String) -> bool: return Kit.exists(p))
		if can.is_empty():
			return 0
		if can.size() != (layer.pieces as Array).size():
			layer = layer.duplicate()
			layer.pieces = can
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
			var grew := 0
			for c in children:
				var p := at if c == 0 else at + Vector2.from_angle(_rng.randf() * TAU) * _rng.randf_range(float(clump[3]) if clump.size() > 3 else 0.3, float(clump[2]))
				if _fits(table, layer, p):
					_put(layer, p, edge)
					count += 1
					grew += 1
			# (a kelp clump in the thick of the forest throws its fronds along the surface: mats of
			# canopy down-current of it, BIOMES.md 5.2; drawn as floor pieces, near and far)
			if layer.has("canopy") and Kit.has("kelp_canopy") and grew >= 2 and edge > 0.45 and Sea.SURFACE - Sea.ground(at.x, at.y) > float(layer.canopy[1]):
				for k in int(layer.canopy[0]):
					var down := CURRENT.normalized()
					var spot := at + down * _rng.randf_range(0.5, 3.5) + down.orthogonal() * _rng.randf_range(-1.6, 1.6)
					var turn := -down.angle() + _rng.randf_range(-0.45, 0.45)
					add_piece("kelp_canopy", Transform3D(Basis(Vector3.UP, turn).scaled(Vector3(1.0, 1.0, 1.0) * _rng.randf_range(0.9, 1.35)),
							Vector3(spot.x, Sea.SURFACE - _rng.randf_range(0.08, 0.2), spot.y)))
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
			if layer.has("to_surface"):
				# (bull kelp: sized so its float rides at the surface; the model is `to_surface` m tall)
				big = deep / float(layer.to_surface) * _rng.randf_range(0.97, 1.03)
			var basis := Basis(Vector3.UP, _rng.randf() * TAU)
			if layer.get("downhill", false):
				# (a ledge on a wall faces down the slope)
				var fall := Vector2(Sea.ground(p.x + 1.0, p.y) - Sea.ground(p.x - 1.0, p.y), Sea.ground(p.x, p.y + 1.0) - Sea.ground(p.x, p.y - 1.0))
				basis = Basis(Vector3.UP, atan2(-fall.x, -fall.y))
			add_piece(piece, Transform3D(basis.scaled(Vector3.ONE * big), Vector3(p.x, floor_y + float(layer.get("lift", 0.0)), p.y)), layer.get("tint", Color.WHITE))
			if piece.begins_with("rock"):
				var reach := (_props.call(&"size_of", piece) as Vector3)
				_rocks.append(Vector3(p.x, maxf(reach.x, reach.z) * 0.5 * big, p.y))


## A floor piece placed (its spheres go to the sea's rocks), tinted with one of its tints.
func add_piece(piece: String, where: Transform3D, tint := Color.WHITE) -> void:
	if not pieces.has(piece):
		pieces[piece] = [[], []]
	var tints: PackedColorArray = _props.call(&"tints_of", piece)
	pieces[piece][0].append(where)
	pieces[piece][1].append((tints[_rng.randi() % tints.size()] if tints.size() > 0 else Color.WHITE) * tint)
	var big := where.basis.get_scale().x
	for sphere: Vector4 in _props.call(&"spheres_of", piece):
		var middle := where * Vector3(sphere.x, sphere.y, sphere.z)
		Sea.add_rock(Vector4(middle.x, middle.y, middle.z, sphere.w * big))


## A built thing's skin for `grow_on_skin`: its meshes (every MeshInstance3D under `root`, as
## triangle meshes in their own space, with where each stands) and its box in the world.
static func skin_of(root: Node3D) -> Dictionary:
	var parts: Array = []
	var box := AABB()
	var first := true
	for node in root.find_children("*", "MeshInstance3D", true, false):
		var drawn := node as MeshInstance3D
		if drawn.mesh == null or not drawn.is_visible_in_tree():
			continue
		var place := drawn.global_transform
		parts.append([drawn.mesh.generate_triangle_mesh(), place, place.affine_inverse()])
		var world := place * drawn.mesh.get_aabb()
		box = world if first else box.merge(world)
		first = false
	return {"parts": parts, "box": box}


## Growth on a built thing's real skin (BIOMES.md 3.4): rays from outside it at points inside its
## box find the face a diver would see; a piece from `list` grows there if the face looks within
## [low, high] (its normal's y), is within `depth` (m under the surface), is not where `clear(at)`
## says a swim route runs, and passes the weighting (high up and facing the current, thicker).
## Faces only reached from inside (the hold, under the decks) get none: no light reaches them.
func grow_on_skin(skin: Dictionary, list: Array, count: int, low: float, high: float, size := Vector2(0.9, 1.5),
		depth := Vector2(0.3, 999.0), clear := Callable()) -> int:
	var parts: Array = skin.parts
	if parts.is_empty() or _props == null:
		return 0
	var box: AABB = skin.box
	var reach := box.size.length()
	var placed := 0
	var tries := 0
	while placed < count and tries < count * 40:
		tries += 1
		var target := box.position + box.size * Vector3(_rng.randf(), _rng.randf(), _rng.randf())
		# (from above for faces that look up, from below for those that look down, else from the side)
		var d := Vector3(_rng.randf_range(-1.0, 1.0), _rng.randf_range(-1.0, 1.0), _rng.randf_range(-1.0, 1.0)).normalized()
		if low > 0.3:
			d.y = -absf(d.y) - 0.6
		elif high < -0.2:
			d.y = absf(d.y) + 0.6
		else:
			d.y *= 0.4
		d = d.normalized()
		var from := target - d * reach
		var best := INF
		var at := Vector3.ZERO
		var n := Vector3.UP
		for part: Array in parts:
			var inv: Transform3D = part[2]
			var hit: Dictionary = (part[0] as TriangleMesh).intersect_ray(inv * from, (inv.basis * d).normalized())
			if hit.is_empty():
				continue
			var p: Vector3 = (part[1] as Transform3D) * (hit.position as Vector3)
			var gap := p.distance_to(from)
			if gap < best:
				best = gap
				at = p
				n = ((part[1] as Transform3D).basis.inverse().transposed() * (hit.normal as Vector3)).normalized()
		if best == INF:
			continue
		# (a face turned away from the ray is a back face: seen from inside)
		if n.dot(d) > 0.0:
			n = -n
		if n.y < low or n.y > high:
			continue
		var facing := maxf(0.0, Vector2(n.x, n.z).dot(-CURRENT.normalized()))
		if _rng.randf() * 2.7 > (1.0 + 0.8 * inverse_lerp(box.position.y, box.end.y, at.y)) * (1.0 + 0.5 * facing):
			continue
		if at.y < Sea.ground(at.x, at.z) + 0.2 or Sea.SURFACE - at.y < depth.x or Sea.SURFACE - at.y > depth.y:
			continue
		if clear.is_valid() and clear.call(at):
			continue
		var up := n
		var side := up.cross(Vector3.RIGHT if absf(up.x) < 0.9 else Vector3.FORWARD).normalized()
		var basis := Basis(side, up, side.cross(up)).orthonormalized().rotated(up, _rng.randf() * TAU)
		var piece: String = list[_rng.randi() % list.size()]
		var where := Transform3D(basis.scaled(Vector3.ONE * _rng.randf_range(size.x, size.y)), at - n * 0.04)
		if not pieces.has(piece):
			pieces[piece] = [[], []]
		var tints: PackedColorArray = _props.call(&"tints_of", piece)
		pieces[piece][0].append(where)
		pieces[piece][1].append(tints[_rng.randi() % tints.size()] if tints.size() > 0 else Color.WHITE)
		placed += 1
	return placed


## Growth on a thing's surface (BIOMES.md 3.4): `count` pieces from `list` on its spheres (world
## x, y, z, radius), on faces whose normal's y is within [low, high], thickest high up and on the
## faces the current runs onto; within `depth` (m under the surface), and never where `clear(at)` says
## a swim route runs.
func grow_on(spheres: Array, list: Array, count: int, low: float, high: float, size := Vector2(0.9, 1.5),
		depth := Vector2(0.3, 999.0), clear := Callable(), skin := -0.08) -> int:
	if spheres.is_empty() or _props == null:
		return 0
	var top := -INF
	var bottom := INF
	for s: Vector4 in spheres:
		top = maxf(top, s.y + s.w)
		bottom = minf(bottom, s.y - s.w)
	var placed := 0
	var tries := 0
	while placed < count and tries < count * 30:
		tries += 1
		var s: Vector4 = spheres[_rng.randi() % spheres.size()]
		var n := Vector3(_rng.randf_range(-1.0, 1.0), _rng.randf_range(-1.0, 1.0), _rng.randf_range(-1.0, 1.0)).normalized()
		if n.y < low or n.y > high:
			continue
		# (a thing's spheres lie just inside its skin: out a little past it, bedded in)
		var at := Vector3(s.x, s.y, s.z) + n * (s.w + skin)
		# (BIOMES.md 3.4: x (1 + 0.8 height share) x (1 + 0.5 facing the current), out of 2.6)
		var facing := maxf(0.0, Vector2(n.x, n.z).dot(-CURRENT.normalized()))
		if _rng.randf() * 2.7 > (1.0 + 0.8 * inverse_lerp(bottom, top, at.y)) * (1.0 + 0.5 * facing):
			continue
		if at.y < Sea.ground(at.x, at.z) - 0.05 or Sea.SURFACE - at.y < depth.x or Sea.SURFACE - at.y > depth.y:
			continue
		if clear.is_valid() and clear.call(at):
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
