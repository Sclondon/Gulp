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

## The reefs left as circles: where the floor is rock round Carmel's cove (read by FloorTypes; the
## kelp forests' and the crags' rock is painted by their regions now: FloorTypes._type_at). Inside
## `r` of `at`, within `depth`, where the place's noise (`freq`, `seed`, its axes turned by `turn` and
## the first one squeezed by `stretch`, so reefs run as fingers) is above `above`, rising towards
## `rise` at the rim; never in its `channels` (polylines, half width).
## (Retired 2026-11-18, for the user's drawn biomes: the circle reefs kelp_south, kelp_north (Capitola,
## outside the user's green), outcrop and outcrop_south (inside the crags now).)
const REEFS := [
	{"name": "carmel", "at": Vector2(21.2, 130.7), "r": 13.0, "depth": [2.5, 15.0], "freq": 0.1, "seed": 24, "above": -0.25, "rise": 0.4,
	 "turn": 0.0, "stretch": 0.6, "channels": [], "barrens": []},
]

## The layers of each place. Keys (all optional but `what`):
## what: "prop" (the sea floor kit's `pieces`), "kelp", "grass", "seaweed" (`kind`: SeaweedBed.Kind)
## region: a BiomeRegions name (the place is that biome, faded in over its edge); or area: [middle,
## radius] and edge (m); or neither (the whole map). avoid: [[middle, radius]...] kept clear.
## on: FloorTypes; depth: [from, to] m; slope_max / slope_min; density: [core, edge] per 100 m²;
## noise: [freq, seed, above]; spacing: m apart on the jittered grid; clump: [least, most, within m];
## size: [from, to] (scale for props, metres for plants); reach / edge_reach (kelp: its length as a
## share of the water's depth); lift (m); lean (props: tipped up to this many radians, as a leaning
## pinnacle); grow (props: growth is put on them after, `grow_spheres`); near_rock: only within this
## of a floor piece already placed; keep: [[polyline, half]...] clear.
##
## The eight biomes are the user's (BiomeRegions); what is in each, how thick and every number here
## are Claude's picks from the concept art (tools/art_src/concept_biome_*.png) and BIOMES.md's
## research: change freely. Budgets: BIOMES.md, "The eight biomes".
const TABLES := {
	# Kelp forest (concept_biome_kelp.png): groves of tall giant kelp up to a canopy on rock ridges, lanes
	# of sand between (the grove noise leaves lanes; FloorTypes leaves sand channels between ridges),
	# understory, red weed, urchins on pink barrens, stars, fans and sponges by the rocks.
	"kelp": {"region": "kelp", "layers": [
		{"what": "prop", "pieces": ["rock_boulder", "rock_split", "rock_ledge", "rock_stack", "rock_boulder_small"], "on": [1, 4], "depth": [3.0, 28.0],
		 "density": [1.4, 0.5], "spacing": 3.8, "clump": [1, 2, 3.0], "size": [0.8, 1.5], "lift": -0.25, "tint": Color(0.66, 0.53, 0.52)},
		# (the kelp's rock and slabs tinted pinker: the coralline crust of the photographs, at no cost)
		{"what": "prop", "pieces": ["reef_slab_a", "reef_slab_b", "reef_slab_c"], "on": [1, 4], "depth": [3.0, 28.0], "slope_max": 0.6, "density": [2.6, 1.2],
		 "spacing": 4.2, "size": [0.8, 1.3], "lift": -0.35, "tint": Color(0.68, 0.54, 0.53)},
		# (Monterey's giant kelp, after real photographs: a wall of columns 1 to 3 m apart in the groves, each a
		# bundle of many stipes (a clump of 2 or 3 wide plants: `width`), with narrow lanes of light between
		# them, the rock ridges' sand channels and the grove noise's gaps left open to swim. 2026-11-18)
		{"what": "kelp", "on": [1], "depth": [5.0, 28.0], "slope_max": 0.8, "density": [19.0, 4.0], "noise": [0.04, 3, -0.24],
		 "spacing": 2.3, "clump": [2, 3, 0.55, 0.2], "width": [1.3, 1.9], "reach": [1.05, 1.3], "edge_reach": [0.55, 0.9], "canopy": [3, 7.0]},
		{"what": "prop", "pieces": ["bull_kelp"], "on": [1], "depth": [4.0, 12.0], "slope_max": 0.7, "density": [1.0, 3.0], "spacing": 2.5, "to_surface": 8.0},
		{"what": "prop", "pieces": ["understory_kelp", "understory_kelp", "understory_kelp_b"], "on": [1], "depth": [3.0, 28.0], "density": [20.0, 5.0],
		 "noise": [0.15, 4, -0.2], "spacing": 1.0, "clump": [2, 5, 1.6], "size": [0.8, 1.4], "lift": -0.03},
		{"what": "seaweed", "kind": 2, "on": [1, 4], "depth": [3.0, 28.0], "density": [24.0, 8.0], "noise": [0.2, 5, -0.25],
		 "spacing": 0.8, "clump": [2, 6, 1.0], "size": [0.16, 0.3]},
		{"what": "seaweed", "kind": 3, "on": [1], "depth": [2.0, 9.0], "density": [6.0, 2.0], "spacing": 1.6, "size": [1.8, 3.0]},
		{"what": "prop", "pieces": ["urchin_purple"], "on": [4], "depth": [4.0, 28.0], "density": [30.0, 20.0], "spacing": 0.8,
		 "clump": [1, 3, 0.6], "size": [0.9, 1.3], "lift": -0.02},
		{"what": "prop", "pieces": ["urchin_purple", "urchin_red"], "on": [1], "depth": [5.0, 28.0], "density": [3.0, 1.0], "spacing": 1.3,
		 "clump": [2, 5, 1.0], "near_rock": 2.0, "size": [0.9, 1.3], "lift": -0.02},
		{"what": "prop", "pieces": ["sea_fan_red", "sea_fan_gold", "hydrocoral", "vase_sponge", "puffball_sponges", "strawberry_anemones"], "on": [1],
		 "depth": [8.0, 28.0], "density": [2.2, 0.6], "spacing": 1.6, "near_rock": 2.5, "size": [0.9, 1.6], "lift": -0.02},
		{"what": "prop", "pieces": ["ochre_star", "bat_star", "green_anemone"], "on": [1, 4], "depth": [4.0, 28.0], "density": [2.4, 0.8],
		 "spacing": 1.5, "size": [0.9, 1.5], "lift": -0.02},
	]},
	# Rocky crags (concept_biome_crags.png): leaning pinnacles and sea stacks, shards, arches and boulder
	# piles with many gaps to dart through, round the pirate ship and its islets (clear of the ship's lane:
	# Scenery._kept_clear, and of the islets' own columns). Pink coralline crust on the floor and on the
	# rocks (strawberry anemone sheets, tinted), white plumose anemones, sea stars, urchins.
	"crags": {"region": "crags", "avoid": [[Vector2(-93.0, -52.0), 8.0], [Vector2(-74.0, -14.0), 7.0]],
		"keep": [[[Vector2(-86.0, -42.0), Vector2(-44.0, -42.0)], 10.0]], "layers": [
		{"what": "prop", "pieces": ["rock_pinnacle"], "on": [1, 4, 0], "depth": [10.0, 30.0], "slope_max": 0.6, "density": [1.3, 0.3], "spacing": 7.0,
		 "size": [1.1, 2.0], "lift": -0.5, "lean": 0.4, "grow": true, "tint": Color(0.56, 0.54, 0.52)},
		# (the shards: pinnacles leaning hard over, as the concept's blades of rock)
		{"what": "prop", "pieces": ["rock_pinnacle"], "on": [1, 4, 0], "depth": [10.0, 30.0], "slope_max": 0.6, "density": [0.6, 0.15], "spacing": 8.0,
		 "size": [0.9, 1.5], "lift": -0.6, "lean": 0.75, "grow": true, "tint": Color(0.52, 0.5, 0.5)},
		{"what": "prop", "pieces": ["rock_stack", "rock_ledge", "rock_stack"], "on": [1, 4], "depth": [10.0, 30.0], "slope_max": 0.6, "density": [1.2, 0.4],
		 "spacing": 6.0, "size": [1.1, 2.0], "lift": -0.45, "lean": 0.28, "grow": true, "tint": Color(0.58, 0.55, 0.52)},
		{"what": "prop", "pieces": ["rock_arch"], "on": [1, 4, 0], "depth": [12.0, 30.0], "slope_max": 0.4, "density": [0.16, 0.0], "spacing": 14.0,
		 "size": [1.0, 1.4], "lift": -0.3, "grow": true, "tint": Color(0.58, 0.55, 0.52)},
		{"what": "prop", "pieces": ["rock_split", "rock_boulder", "rock_boulder_small", "rock_boulder"], "on": [1, 4, 0], "depth": [8.0, 30.0], "density": [1.8, 0.6],
		 "spacing": 3.6, "clump": [2, 5, 2.4], "size": [0.8, 1.6], "lift": -0.25, "tint": Color(0.6, 0.57, 0.54)},
		{"what": "prop", "pieces": ["reef_slab_a", "reef_slab_b", "reef_slab_c"], "on": [1, 4], "depth": [8.0, 30.0], "slope_max": 0.6, "density": [1.6, 0.8],
		 "spacing": 4.4, "size": [0.8, 1.2], "lift": -0.35, "tint": Color(0.64, 0.58, 0.56)},
		{"what": "prop", "pieces": ["plumose_anemones"], "on": [1, 4], "depth": [6.0, 30.0], "density": [4.0, 1.0], "spacing": 1.3, "clump": [1, 3, 0.9],
		 "near_rock": 2.2, "size": [1.5, 2.6], "lift": -0.03},
		{"what": "prop", "pieces": ["strawberry_anemones"], "on": [1, 4], "depth": [6.0, 30.0], "density": [4.0, 1.5], "spacing": 1.1, "clump": [1, 3, 0.8],
		 "near_rock": 2.0, "size": [1.0, 1.8], "lift": -0.02},
		{"what": "prop", "pieces": ["ochre_star", "bat_star", "urchin_purple", "urchin_red", "green_anemone"], "on": [1, 4], "depth": [6.0, 30.0],
		 "density": [4.0, 1.5], "spacing": 1.2, "size": [0.9, 1.5], "lift": -0.02},
		{"what": "prop", "pieces": ["hydrocoral", "sea_fan_red", "vase_sponge"], "on": [1, 4], "depth": [10.0, 30.0], "density": [1.6, 0.5], "spacing": 1.6,
		 "near_rock": 2.5, "size": [1.0, 1.7], "lift": -0.02},
		{"what": "seaweed", "kind": 2, "on": [1, 4], "depth": [3.0, 30.0], "density": [8.0, 3.0], "spacing": 1.0, "clump": [2, 5, 1.0], "size": [0.16, 0.28]},
	]},
	"carmel": {"area": [Vector2(21.2, 130.7), 13.0], "edge": 4.0, "layers": [
		{"what": "prop", "pieces": ["rock_boulder", "rock_split", "rock_stack"], "on": [1], "depth": [2.5, 15.0], "density": [3.0, 1.0],
		 "spacing": 3.0, "size": [0.8, 1.4], "lift": -0.25, "tint": Color(0.62, 0.57, 0.52)},
		{"what": "prop", "pieces": ["reef_slab_a", "reef_slab_b", "reef_slab_c"], "on": [1], "depth": [2.5, 15.0], "slope_max": 0.6, "density": [4.0, 2.0],
		 "spacing": 3.6, "size": [0.7, 1.2], "lift": -0.35, "tint": Color(0.64, 0.6, 0.55)},
		{"what": "kelp", "on": [1], "depth": [5.0, 15.0], "density": [14.0, 4.0], "spacing": 2.4, "clump": [2, 3, 0.55, 0.2], "width": [1.2, 1.7], "reach": [1.2, 1.5], "edge_reach": [0.6, 0.95], "canopy": [1, 6.0]},
		{"what": "prop", "pieces": ["bull_kelp"], "on": [1], "depth": [4.0, 13.0], "density": [0.0, 5.0], "spacing": 2.2, "to_surface": 8.0},
		{"what": "prop", "pieces": ["understory_kelp", "understory_kelp_b"], "on": [1], "depth": [3.0, 14.0], "density": [25.0, 8.0], "spacing": 1.0, "clump": [2, 5, 1.6], "size": [0.7, 1.2], "lift": -0.03},
		{"what": "seaweed", "kind": 2, "on": [1], "depth": [2.0, 15.0], "density": [40.0, 10.0], "spacing": 0.8, "clump": [2, 5, 1.0], "size": [0.16, 0.3]},
	]},
	# Sea grass (concept_biome_grass.png): dense eelgrass meadows leaning in the current, bare sandy
	# blowouts where the noise is low, and sandy paths winding through (`keep`): cozy cover for small fish.
	"grass": {"region": "grass", "keep": [
			[[Vector2(-100.0, -30.0), Vector2(-86.0, -24.0), Vector2(-78.0, -14.0), Vector2(-64.0, -12.0), Vector2(-52.0, -6.0), Vector2(-44.0, -14.0)], 1.4],
			[[Vector2(-92.0, 14.0), Vector2(-90.0, 0.0), Vector2(-96.0, -14.0), Vector2(-94.0, -30.0)], 1.2],
			[[Vector2(-64.0, 18.0), Vector2(-60.0, 8.0), Vector2(-62.0, -4.0), Vector2(-58.0, -14.0)], 1.2],
			[[Vector2(-28.0, 60.0), Vector2(-34.0, 74.0), Vector2(-46.0, 84.0), Vector2(-62.0, 94.0)], 1.4],
			[[Vector2(-20.0, 98.0), Vector2(-26.0, 88.0), Vector2(-22.0, 76.0)], 1.2]], "layers": [
		{"what": "grass", "on": [0, 2], "depth": [1.0, 30.0], "slope_max": 0.35, "density": [520.0, 110.0], "noise": [0.06, 7, -0.38],
		 "spacing": 0.55, "clump": [2, 4, 0.6], "size": [0.95, 1.2], "edge_size": [0.45, 0.8]},
		{"what": "seaweed", "kind": 0, "on": [0, 2], "depth": [1.0, 30.0], "density": [2.0, 1.0], "spacing": 1.6, "clump": [1, 3, 0.8], "size": [0.25, 0.5]},
	]},
	# The dune sea (concept_biome_dunes.png): open, exposed, rolling pale sand (the dunes are the floor's
	# own shape: Bay.dune_height), sparse life: sea pen meadows in the troughs' patches, sand dollars,
	# scallops, a few lone boulders. The garden eels and the anchor are Scenery's.
	"dunes": {"region": "dunes", "layers": [
		{"what": "prop", "pieces": ["sea_pen"], "on": [0], "depth": [10.0, 30.0], "slope_max": 0.25, "density": [10.0, 2.0], "noise": [0.05, 31, 0.05],
		 "spacing": 1.5, "clump": [3, 9, 1.8], "size": [0.9, 1.4], "lift": -0.04},
		{"what": "prop", "pieces": ["sand_dollars"], "on": [0], "depth": [8.0, 30.0], "slope_max": 0.2, "density": [1.6, 0.4], "noise": [0.06, 47, 0.15],
		 "spacing": 3.0, "clump": [1, 2, 1.6, 1.0], "size": [0.8, 1.2], "lift": -0.01},
		{"what": "prop", "pieces": ["scallop"], "on": [0], "depth": [10.0, 30.0], "density": [1.5, 0.4], "spacing": 2.2, "clump": [1, 3, 1.0], "size": [0.9, 1.3], "lift": -0.02},
		{"what": "prop", "pieces": ["rock_boulder", "rock_boulder_small"], "on": [0], "depth": [10.0, 30.0], "slope_max": 0.3, "density": [0.2, 0.05], "spacing": 6.0,
		 "size": [0.8, 1.4], "lift": -0.25, "tint": Color(0.75, 0.72, 0.66)},
	]},
	# The river (Elkhorn Slough, concept_biome_river.png: the mangroves are Scenery's) and its estuary round
	# the mouth (the user: "a seaweedy / grassy area around the mouth instead of regular beach"): eelgrass
	# meadows on the mud of the banks and the mouth's flats, sea lettuce and red weed among it, thinning
	# down the channel's middle; it fades into the beach along the shore and the canyon head offshore.
	"river": {"region": "river", "layers": [
		{"what": "grass", "on": [0, 2], "depth": [0.4, 7.0], "slope_max": 0.6, "density": [320.0, 90.0], "noise": [0.09, 77, -0.35],
		 "spacing": 0.55, "clump": [2, 4, 0.6], "size": [0.6, 1.1], "edge_size": [0.4, 0.7]},
		{"what": "seaweed", "kind": 0, "on": [0, 2], "depth": [0.4, 9.0], "density": [14.0, 5.0], "spacing": 1.0, "clump": [1, 3, 0.8], "size": [0.25, 0.5]},
		{"what": "seaweed", "kind": 2, "on": [0, 2], "depth": [1.0, 10.0], "density": [6.0, 2.0], "spacing": 1.2, "clump": [2, 4, 0.8], "size": [0.16, 0.3]},
	]},
	# The harbours' floors and the breakwater's foot.
	"docks_monterey": {"area": [Vector2(66.0, 68.0), 18.0], "edge": 3.0, "layers": [
		{"what": "seaweed", "kind": 0, "on": [2, 0], "depth": [1.0, 7.0], "density": [5.0, 2.0], "spacing": 1.2, "clump": [1, 3, 0.8], "size": [0.25, 0.45]},
		{"what": "seaweed", "kind": 1, "on": [1], "depth": [0.0, 3.0], "density": [40.0, 15.0], "spacing": 0.6, "clump": [2, 5, 0.8], "size": [0.25, 0.4]},
	]},
	# The beach shallows: on the rocky points rockweed, surfgrass in the surge, feather boa, anemones and
	# stars; on the sand a sand dollar band where it meets the shelf (BIOMES.md 5.1).
	"beach": {"region": "beach", "layers": [
		# (concept_biome_beach.png: tide-pool rocks along the sandy shores too, in patches, each with its
		# surfgrass, rockweed, anemones and stars round it)
		{"what": "prop", "pieces": ["rock_boulder", "rock_split", "rock_boulder_small", "rock_slab"], "on": [0], "depth": [0.6, 4.5], "density": [1.0, 0.5],
		 "noise": [0.05, 44, 0.2], "spacing": 4.0, "clump": [2, 5, 2.5], "size": [0.7, 1.3], "lift": -0.25, "tint": Color(0.72, 0.68, 0.6)},
		{"what": "prop", "pieces": ["surfgrass"], "on": [0], "depth": [0.4, 4.5], "density": [40.0, 20.0], "spacing": 0.8, "clump": [3, 6, 0.8],
		 "near_rock": 1.6, "size": [0.9, 1.4], "lift": -0.02},
		{"what": "seaweed", "kind": 1, "on": [0], "depth": [0.3, 4.5], "density": [25.0, 10.0], "spacing": 0.7, "clump": [2, 4, 0.8], "near_rock": 1.0,
		 "size": [0.25, 0.4]},
		{"what": "prop", "pieces": ["green_anemone", "ochre_star", "bat_star"], "on": [0], "depth": [0.3, 4.5], "density": [6.0, 3.0], "spacing": 1.0,
		 "clump": [1, 2, 0.6], "near_rock": 1.2, "size": [0.9, 1.4], "lift": -0.02},
		{"what": "prop", "pieces": ["surfgrass"], "on": [1], "depth": [0.5, 4.0], "slope_max": 0.8, "density": [40.0, 15.0], "noise": [0.12, 43, -0.3],
		 "spacing": 1.0, "clump": [3, 7, 0.9], "size": [0.8, 1.3], "lift": -0.02},
		{"what": "seaweed", "kind": 1, "on": [1], "depth": [0.3, 2.0], "density": [25.0, 10.0], "spacing": 0.6, "clump": [2, 5, 0.8], "size": [0.25, 0.4]},
		{"what": "seaweed", "kind": 3, "on": [1], "depth": [1.5, 5.5], "density": [5.0, 2.0], "spacing": 1.6, "size": [1.5, 2.5]},
		{"what": "prop", "pieces": ["green_anemone", "ochre_star", "mussel_clump", "bat_star"], "on": [1], "depth": [0.3, 5.5], "density": [5.0, 2.0],
		 "spacing": 1.0, "clump": [1, 3, 0.8], "size": [0.9, 1.4], "lift": -0.02},
		{"what": "prop", "pieces": ["sand_dollars"], "on": [0, 5], "depth": [2.5, 6.0], "slope_max": 0.5, "density": [20.0, 20.0], "noise": [0.06, 47, -0.5],
		 "spacing": 2.0, "clump": [1, 3, 1.6, 1.0], "size": [0.8, 1.3], "lift": -0.01},
	]},
	# The trench (the drawn trench and its terraced walls, deeper than the shelf; not Atlantis's basin):
	# rock pieces on the steep risers, deep growth on them, tall white sea pens and sea whips on the
	# mud of the treads and the floor.
	"trench": {"region": "trench", "layers": [
		{"what": "prop", "pieces": ["rock_ledge", "rock_slab", "rock_split", "rock_stack"], "on": [1], "depth": [12.0, 106.0], "slope_min": 0.5, "density": [2.4, 2.4],
		 "noise": [0.06, 61, -0.35], "spacing": 3.4, "clump": [1, 3, 3.0], "size": [1.3, 2.8], "lift": -0.8, "downhill": true, "tint": Color(0.6, 0.58, 0.55)},
		{"what": "prop", "pieces": ["vase_sponge", "sea_fan_red", "puffball_sponges", "feather_dusters"], "on": [1], "depth": [22.0, 95.0], "slope_min": 0.4,
		 "density": [2.0, 2.0], "spacing": 1.8, "clump": [1, 3, 1.2], "size": [1.4, 2.4], "lift": -0.05},
		# (concept_biome_trench.png: silted ledges with white anemones and sponges on their lips, sea pens on them)
		{"what": "prop", "pieces": ["plumose_anemones"], "on": [0, 1, 2], "depth": [28.0, 106.0], "slope_max": 0.4, "density": [2.0, 1.0], "spacing": 2.0,
		 "clump": [2, 4, 1.0], "near_rock": 3.0, "size": [1.6, 2.6], "lift": -0.05},
		{"what": "prop", "pieces": ["vase_sponge", "puffball_sponges", "vase_sponge"], "on": [0, 2], "depth": [28.0, 106.0], "slope_max": 0.3, "density": [1.6, 0.8],
		 "spacing": 2.2, "clump": [1, 3, 1.2], "size": [1.5, 2.6], "lift": -0.03},
		{"what": "prop", "pieces": ["sea_pen_deep", "sea_pen_deep", "sea_whip"], "on": [0, 2], "depth": [28.0, 106.0], "slope_max": 0.3, "density": [5.0, 5.0],
		 "noise": [0.05, 53, -0.1], "spacing": 2.5, "clump": [4, 10, 2.0], "size": [0.8, 1.3], "lift": -0.05},
	]},
	# The liner's reef (concept_biome_reef.png): its bommies and their corals are Scenery._place_reef's and the
	# wreck's own; here the canyon's rims and walls either side of where it bridges grow the warm pocket's
	# corals, fans and sponges too, so the reef runs off the hull onto the rock.
	"reef": {"region": "reef", "layers": [
		{"what": "prop", "pieces": ["brain_coral", "barrel_sponge", "soft_coral", "sea_rods", "sea_fan_purple", "table_coral"], "on": [0, 1, 2], "depth": [18.0, 45.0],
		 "slope_max": 0.5, "density": [1.4, 0.4], "noise": [0.08, 71, -0.2], "spacing": 2.4, "clump": [1, 3, 1.4], "size": [0.9, 1.6], "lift": -0.05},
		{"what": "prop", "pieces": ["sea_fan_purple", "barrel_sponge", "sea_rods", "pillar_coral"], "on": [1], "depth": [26.0, 70.0], "slope_min": 0.5,
		 "density": [1.2, 0.4], "spacing": 2.4, "clump": [1, 2, 1.2], "size": [1.0, 1.7], "lift": -0.05},
	]},
}

## Which way the water streams over the sea floor (Scenery.current: the plants lean and stream this way).
const CURRENT := Vector2(0.3, 0.1)

## The places' order (big things first in each; the tables above).
const ORDER := ["kelp", "crags", "carmel", "grass", "dunes", "river", "docks_monterey", "beach", "trench", "reef"]
## The whole map's corners for the tables without an area of their own ("points", "walls").
const WHOLE := [Vector2(Bay.WEST, Bay.NORTH), Vector2(Bay.EAST, Bay.SOUTH)]

# What came out: floor pieces (name -> [transforms, colours]), kelp (places, lengths), grass
# (places, heights), seaweed (places, sizes, kinds), and how many of each layer (for the checks).
var pieces := {}
var kelp_places := PackedVector3Array()
var kelp_lengths := PackedFloat32Array()
## How many times as wide each kelp plant's bundle is (KelpForest.plant's `widths`).
var kelp_widths := PackedFloat32Array()
## The eelgrass layers ([table, layer]), drawn as SeaGrassBed fields (`grass_fields`), not as points.
var grass_layers: Array = []
var weed_places := PackedVector3Array()
var weed_sizes := PackedFloat32Array()
var weed_kinds := PackedInt32Array()
var made := {}
## The spheres (world x, y, z, radius) of each placed piece of a `grow` layer, one array a piece:
## Scenery grows the crags' coralline, anemones and stars on them (`grow_on`).
var grow_spheres: Array = []

var _rng := RandomNumberGenerator.new()
var _props: GDScript
var _rocks: Array[Vector3] = []   # floor pieces' middles (x, z) and how far they reach (y)
# (the same, by 8 m square of floor: a candidate is tried only against the rocks round it)
var _rock_cells := {}
const _ROCK_CELL := 8.0
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


## The eelgrass as fields (SeaGrassBed.field, the user's "Yep", 2026-11-18, to Warren's way of spawning
## grass): one a "grass" layer, over its place's box, each {area, mask, tall}. The mask is the layer's
## own rules, asked at a point instead of at the placer's grid: the place's weight (thick at its core,
## thinning to its edge, as the placer's chance of a clump there, `density` at `spacing`), the floor
## type, depth, slope, the noise's bare blowouts, the sandy paths and set pieces kept clear and the
## rocks' feet. `tall` gives the tufts' least and most height there (`size` in the core, `edge_size`
## towards the edge). Call after `run` (the rocks are all placed by then).
func grass_fields() -> Array:
	var out := []
	for one: Array in grass_layers:
		var table: Dictionary = one[0]
		var layer: Dictionary = one[1]
		var box := Rect2()
		if table.has("region"):
			box = BiomeRegions.bounds(table.region)
		elif not (table.get("area", []) as Array).is_empty():
			box = Rect2((table.area[0] as Vector2) - Vector2.ONE * float(table.area[1]), Vector2.ONE * float(table.area[1]) * 2.0)
		else:
			box = Rect2(WHOLE[0], WHOLE[1] - WHOLE[0])
		if box.size == Vector2.ZERO:
			continue
		var noise: FastNoiseLite = null
		if layer.has("noise"):
			noise = FastNoiseLite.new()
			noise.frequency = float(layer.noise[0])
			noise.seed = int(layer.noise[1])
			noise.fractal_octaves = 2
		var spacing: float = layer.get("spacing", 1.0)
		var density: Array = layer.get("density", [1.0, 1.0])
		var full := minf(1.0, float(density[0]) * spacing * spacing / 100.0)
		# (the last point's edge, which `tall` asks for right after `mask` at the same point)
		var last := {"p": Vector2.INF, "edge": 0.0}
		var mask := func(p: Vector2) -> float:
			var edge := _edge(table, p)
			last.p = p
			last.edge = edge
			if edge < 0.0:
				return 0.0
			if noise and noise.get_noise_2d(p.x, p.y) < float(layer.noise[2]):
				return 0.0
			if not _fits(table, layer, p):
				return 0.0
			return minf(1.0, lerpf(float(density[1]), float(density[0]), edge) * spacing * spacing / 100.0) / full
		var size: Array = layer.get("size", [1.0, 1.0])
		var edge_size: Array = layer.get("edge_size", size)
		var tall := func(p: Vector2) -> Vector2:
			var edge: float = last.edge if last.p == p else _edge(table, p)
			var core := smoothstep(0.35, 0.65, edge)
			return Vector2(lerpf(float(edge_size[0]), float(size[0]), core), lerpf(float(edge_size[1]), float(size[1]), core))
		out.append({"area": box.grow(1.0), "mask": mask, "tall": tall})
	return out


func _layer(table: Dictionary, layer: Dictionary) -> int:
	if layer.what == "prop" and _props == null:
		return 0
	if layer.what == "grass":
		# (eelgrass is not placed here: it is a field, filled near the eye by the same rules: `grass_fields`)
		grass_layers.append([table, layer])
		return 0
	if layer.what == "prop":
		# (a piece of the kit not built yet is left out)
		var can: Array = (layer.pieces as Array).filter(func(p: String) -> bool: return Kit.exists(p))
		if can.is_empty():
			return 0
		if can.size() != (layer.pieces as Array).size():
			layer = layer.duplicate()
			layer.pieces = can
	var low: Vector2 = WHOLE[0]
	var high: Vector2 = WHOLE[1]
	if table.has("region"):
		var box := BiomeRegions.bounds(table.region)
		if box.size == Vector2.ZERO:
			return 0
		low = box.position
		high = box.end
	elif not (table.get("area", []) as Array).is_empty():
		var area: Array = table.area
		low = (area[0] as Vector2) - Vector2.ONE * float(area[1])
		high = (area[0] as Vector2) + Vector2.ONE * float(area[1])
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
	if table.has("region"):
		if BiomeRegions.at(at.x, at.y) != table.region:
			return -1.0
		return BiomeRegions.weight(table.region, at.x, at.y)
	var area: Array = table.get("area", [])
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
	if table.has("region") and BiomeRegions.at(p.x, p.y) != table.region:
		return false
	for away: Array in table.get("avoid", []):
		if p.distance_to(away[0]) < float(away[1]):
			return false
	for keep: Array in table.get("keep", []):
		if _line_distance(p, keep[0]) < float(keep[1]):
			return false
	if _kept.is_valid() and _kept.call(p):
		return false
	if layer.has("near_rock"):
		var reach: float = layer.near_rock
		var near := false
		for rock: Vector3 in _rocks_near(p):
			if Vector2(rock.x, rock.z).distance_to(p) < rock.y + reach:
				near = true
				break
		if not near:
			return false
	elif layer.what != "prop" or not (layer.pieces as Array)[0].begins_with("rock"):
		# (nothing grows inside a rock: keep out of the floor pieces' feet)
		for rock: Vector3 in _rocks_near(p):
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
			var wide: Array = layer.get("width", [1.0, 1.0])
			kelp_widths.append(_rng.randf_range(float(wide[0]), float(wide[1])))
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
			if layer.has("lean"):
				# (a tall piece stays under the surface, 2 m clear)
				big = minf(big, (deep - 2.0) / maxf((_props.call(&"size_of", piece) as Vector3).y, 0.1))
			var basis := Basis(Vector3.UP, _rng.randf() * TAU)
			if layer.get("downhill", false):
				# (a ledge on a wall faces down the slope)
				var fall := Vector2(Sea.ground(p.x + 1.0, p.y) - Sea.ground(p.x - 1.0, p.y), Sea.ground(p.x, p.y + 1.0) - Sea.ground(p.x, p.y - 1.0))
				basis = Basis(Vector3.UP, atan2(-fall.x, -fall.y))
			if layer.has("lean"):
				# (a leaning pinnacle: tipped over some way, by up to `lean`)
				var way := _rng.randf() * TAU
				basis = Basis(Vector3(cos(way), 0.0, sin(way)), _rng.randf_range(0.3, 1.0) * float(layer.lean)) * basis
			var where := Transform3D(basis.scaled(Vector3.ONE * big), Vector3(p.x, floor_y + float(layer.get("lift", 0.0)), p.y))
			add_piece(piece, where, layer.get("tint", Color.WHITE))
			if layer.get("grow", false):
				var spheres: Array = []
				for s: Vector4 in _props.call(&"spheres_of", piece):
					var m := where * Vector3(s.x, s.y, s.z)
					spheres.append(Vector4(m.x, m.y, m.z, s.w * big))
				grow_spheres.append(spheres)
			if piece.begins_with("rock"):
				var reach := (_props.call(&"size_of", piece) as Vector3)
				var rock := Vector3(p.x, maxf(reach.x, reach.z) * 0.5 * big, p.y)
				_rocks.append(rock)
				var key := Vector2i(floori(p.x / _ROCK_CELL), floori(p.y / _ROCK_CELL))
				if not _rock_cells.has(key):
					_rock_cells[key] = []
				(_rock_cells[key] as Array).append(rock)


# The rocks placed so far whose middles are within two squares of a point (none reaches further).
func _rocks_near(p: Vector2) -> Array:
	var out := []
	var cx := floori(p.x / _ROCK_CELL)
	var cz := floori(p.y / _ROCK_CELL)
	for x in range(cx - 2, cx + 3):
		for z in range(cz - 2, cz + 3):
			var list: Variant = _rock_cells.get(Vector2i(x, z))
			if list != null:
				out.append_array(list)
	return out


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
