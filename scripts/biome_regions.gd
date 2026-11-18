class_name BiomeRegions
## The bay's biomes where the user drew them (2026-11-18, over the overhead chart: "We need to make proper biomes,
## with concept art for each considering our needs. Green is kelp forest, yellow is sand dune sea, red is sea
## grassy fields, purple is rocky crags"; then "This trench needs to be enlarged and then the green section
## should be kelp forest not dune sea"; and "You shouldnt be that exact just look at the map and see the areas I
## was trying to highlight"). So each is a rough outline read off the drawings by eye (world x, z), not a trace.
## Where two overlap, the earlier in ORDER wins. The drawings: tools/art_src/user_biome_lines.png and the second
## one's description in CLAUDE.md.

const KELP := "kelp"
const DUNES := "dunes"
const GRASS := "grass"
const CRAGS := "crags"
## Which wins where two overlap.
const ORDER := [CRAGS, KELP, GRASS, DUNES]
## How far (m) a biome's look fades in across its edge.
const EDGE := 8.0

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
}

static var _packed := {}


## The biome at a point ("" for none).
static func at(x: float, z: float) -> String:
	var p := Vector2(x, z)
	for name: String in ORDER:
		for shape: PackedVector2Array in _shapes(name):
			if Geometry2D.is_point_in_polygon(p, shape):
				return name
	return ""


## How much a point is in a biome, 0..1, fading in over EDGE metres inside its edge (and 0 where a biome earlier
## in ORDER has it).
static func weight(name: String, x: float, z: float) -> float:
	if at(x, z) != name:
		return 0.0
	var p := Vector2(x, z)
	var near := INF
	for shape: PackedVector2Array in _shapes(name):
		if not Geometry2D.is_point_in_polygon(p, shape):
			continue
		for i in shape.size():
			near = minf(near, p.distance_to(Geometry2D.get_closest_point_to_segment(p, shape[i], shape[(i + 1) % shape.size()])))
	return smoothstep(0.0, EDGE, near)


static func _shapes(name: String) -> Array:
	if not _packed.has(name):
		var list := []
		for shape: Array in SHAPES[name]:
			list.append(PackedVector2Array(shape))
		_packed[name] = list
	return _packed[name]
