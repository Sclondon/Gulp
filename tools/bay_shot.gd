extends SceneTree
## Pictures of the bay's places without the game: the sea and its scenery only, a camera at a
## place looking at another (for checking the docks, the shelves and the canyon by eye).
##   godot --path . --audio-driver Dummy -s tools/bay_shot.gd -- --out=<folder> [--above]
## With --above, one picture of the whole bay from high over it, the water hidden. With --biomes, views
## inside each of the eight biomes (tools/BIOMES.md, "The eight biomes"), to hold against their concepts
## (tools/art_src/concept_biome_*.png); --only=<name part> keeps the views whose names have it.

var _out := "user://"
var _above := false
var _biomes := false
var _only := ""


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--out="):
			_out = arg.get_slice("=", 1)
		elif arg == "--above":
			_above = true
		elif arg == "--biomes":
			_biomes = true
		elif arg.begins_with("--only="):
			_only = arg.get_slice("=", 1)
	var view := get_root()
	view.size = Vector2i(960, 720)
	var sea := Sea.new()
	view.add_child(sea)
	var scenery := Scenery.new()
	view.add_child(scenery)
	var camera := Camera3D.new()
	camera.far = 900.0
	view.add_child(camera)
	sea.eye = camera
	var water := sea.find_child("Water", true, false) as Node3D
	var shots := []
	if _biomes:
		await process_frame
		shots = _biome_views(scenery)
	elif _above:
		shots = [["bay_above", Vector3(-18.0, 420.0, 20.0), Vector3(-18.0, 0.0, 9.0)]]
	else:
		var m: Vector2 = Scenery.MONTEREY
		var s: Vector2 = Scenery.SANTA_CRUZ
		shots = [
			["docks_monterey", Vector3(m.x, 36.5, m.y - 22.0), Vector3(m.x, 36.0, m.y)],
			["docks_monterey_wharf", Vector3(m.x - 20.0, 37.0, m.y - 4.0), Vector3(m.x - 10.0, 39.0, m.y)],
			["docks_santacruz", Vector3(s.x + 4.0, 37.0, s.y + 22.0), Vector3(s.x - 8.0, 36.0, s.y)],
			["river_mangroves", Vector3(96.0, 38.0, -30.0), Vector3(108.0, 37.0, -39.0)],
			["wreck_shelf", Sea.WRECK_AT + Vector3(0.0, 14.0, -30.0), Sea.WRECK_AT],
			["wreck_bridge_from_canyon", Sea.WRECK_AT + Vector3(-28.0, -22.0, 2.0), Sea.WRECK_AT + Vector3(0.0, 2.0, 0.0)],
			["wreck_bridge_side", Sea.WRECK_AT + Vector3(-40.0, 2.0, 0.0), Sea.WRECK_AT + Vector3(0.0, -8.0, 0.0)],
			["terraces_basin_east_wall", Vector3(-62.0, -8.0, 46.0), Vector3(-30.0, -18.0, 52.0)],
			["terraces_basin_from_rim", Vector3(-24.0, 22.0, 40.0), Vector3(-50.0, -30.0, 52.0)],
			["ruins_terrace", Sea.RUINS_AT + Vector3(22.0, 14.0, -26.0), Sea.RUINS_AT],
			["pirate_hollow", Sea.PIRATE_AT + Vector3(16.0, 10.0, -18.0), Sea.PIRATE_AT],
			["seal_rock_above", Vector3(Scenery.OUTCROP.x + 14.0, 45.0, Scenery.OUTCROP.y + 12.0), Vector3(Scenery.OUTCROP.x, 40.5, Scenery.OUTCROP.y)],
			["seal_rock_below", Vector3(Scenery.OUTCROP.x + 18.0, 30.0, Scenery.OUTCROP.y + 16.0), Vector3(Scenery.OUTCROP.x, 26.0, Scenery.OUTCROP.y)],
			["outcrop_south_above", Vector3(Scenery.OUTCROP_SOUTH.x + 16.0, 46.0, Scenery.OUTCROP_SOUTH.y + 14.0), Vector3(Scenery.OUTCROP_SOUTH.x, 40.5, Scenery.OUTCROP_SOUTH.y)],
			["outcrop_south_below", Vector3(Scenery.OUTCROP_SOUTH.x + 20.0, 28.0, Scenery.OUTCROP_SOUTH.y + 16.0), Vector3(Scenery.OUTCROP_SOUTH.x, 24.0, Scenery.OUTCROP_SOUTH.y)],
			["canyon_head", Vector3(70.0, 28.0, -20.0), Vector3(90.0, 22.0, -37.0)],
			["kelp_south", Vector3(36.0, 34.0, 40.0), Vector3(44.0, 30.0, 55.0)],
			["canyon_wall_north", Vector3(40.0, 0.0, -18.0), Vector3(40.0, 5.0, -42.0)],
			["canyon_wall_from_floor", Vector3(20.0, -20.0, -30.0), Vector3(30.0, 10.0, -45.0)],
			["canyon_from_rim", Vector3(30.0, 22.0, -55.0), Vector3(30.0, -10.0, -30.0)],
			["ruins_from_canyon", Sea.RUINS_AT + Vector3(30.0, -10.0, 10.0), Sea.RUINS_AT],
		]
	for shot: Array in shots:
		if _only != "" and not String(shot[0]).contains(_only):
			continue
		camera.global_position = shot[1]
		camera.look_at(shot[2], Vector3.FORWARD if _above else Vector3.UP)
		if _above:
			camera.fov = 40.0
			if water:
				water.visible = false
			sea.set_above(true)
		else:
			sea.set_above(camera.global_position.y > Sea.SURFACE)
		for i in 8:
			await process_frame
		await RenderingServer.frame_post_draw
		var path := _out.path_join("%s.png" % shot[0])
		view.get_texture().get_image().save_png(path)
		print("BAY SHOT ", path)
	quit()


# Views in each biome: [name, eye, looking at]. Most are set by hand (x, z in the world; heights over
# the floor there); the kelp and grass ones look at the thickest stand the placer made. Every eye is put
# outside the rocks.
func _biome_views(scenery: Scenery) -> Array:
	var views := []
	var thickest := func(places: PackedVector3Array, within: float, region: String) -> Vector3:
		var best := Vector3.ZERO
		var most := -1
		for i in range(0, places.size(), maxi(places.size() / 300, 1)):
			if BiomeRegions.at(places[i].x, places[i].z) != region:
				continue
			var n := 0
			for j in range(0, places.size(), maxi(places.size() / 2000, 1)):
				if places[i].distance_to(places[j]) < within:
					n += 1
			if n > most:
				most = n
				best = places[i]
		return best
	var kelp: Vector3 = thickest.call(scenery._biomes.kelp_places, 8.0, BiomeRegions.KELP)
	var grass: Vector3 = thickest.call(scenery._biomes.grass_places, 4.0, BiomeRegions.GRASS)
	var k := Vector2(kelp.x, kelp.z)
	var g := Vector2(grass.x, grass.z)
	for each: Array in [
			["kelp_grove", k + Vector2(-14.0, -6.0), 4.0, k, 7.0],
			["kelp_up_to_canopy", k + Vector2(-3.0, -2.0), 2.0, k + Vector2(2.0, 2.0), 20.0],
			["kelp_floor", k + Vector2(-8.0, 6.0), 1.5, k + Vector2(4.0, 0.0), 1.0],
			["dunes_across", Vector2(-44.0, -84.0), 4.0, Vector2(-16.0, -78.0), 1.0],
			["dunes_eels", Vector2(-38.0, -92.0), 2.5, Vector2(-47.0, -87.0), 0.5],
			["dunes_anchor", Vector2(-22.0, -83.0), 2.5, Vector2(-28.0, -88.0), 1.5],
			["grass_meadow", g + Vector2(-8.0, -5.0), 2.0, g + Vector2(4.0, 3.0), 0.5],
			["grass_low", g + Vector2(-5.0, 4.0), 0.8, g + Vector2(5.0, -2.0), 0.6],
			["crags_pinnacles", Vector2(-60.0, -28.0), 9.0, Vector2(-76.0, -40.0), 3.0],
			["crags_west", Vector2(-100.0, -32.0), 8.0, Vector2(-86.0, -46.0), 3.0],
			["crags_east", Vector2(-30.0, -40.0), 7.0, Vector2(-46.0, -52.0), 3.0],
			["crags_ship", Vector2(-44.0, -36.0), 5.0, Vector2(-62.0, -44.0), 3.0],
			["trench_terraces", Vector2(-2.0, -16.0), 22.0, Vector2(0.0, -46.0), 2.0],
			["trench_floor", Vector2(-4.0, -14.0), 3.0, Vector2(14.0, -20.0), 4.0],
			["beach_shallows", Vector2(50.0, -118.0), 1.0, Vector2(40.0, -128.0), 0.4],
			["beach_rocks", Vector2(-20.0, -126.0), 1.2, Vector2(-26.0, -134.0), 0.4],
			["river_mangroves", Vector2(104.0, -41.0), 1.8, Vector2(124.0, -40.0), 1.5],
			["river_estuary", Vector2(88.0, -58.0), 1.4, Vector2(100.0, -46.0), 0.4],
			["reef_liner", Vector2(-20.0, 112.0), 6.0, Vector2(-37.0, 126.0), 4.0]]:
		var from: Vector2 = each[1]
		var to: Vector2 = each[3]
		var eye := Vector3(from.x, minf(Sea.ground(from.x, from.y) + float(each[2]), Sea.SURFACE - 0.5), from.y)
		eye = Sea.clear_of_rocks(eye, 2.5)
		var aim := Vector3(to.x, minf(Sea.ground(to.x, to.y) + float(each[4]), Sea.SURFACE - 0.3), to.y)
		views.append(["biome_" + String(each[0]), eye, aim])
	return views
