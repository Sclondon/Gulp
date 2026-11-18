extends SceneTree
## Pictures of the bay's places without the game: the sea and its scenery only, a camera at a
## place looking at another (for checking the docks, the shelves and the canyon by eye).
##   godot --path . --audio-driver Dummy -s tools/bay_shot.gd -- --out=<folder> [--above]
## With --above, one picture of the whole bay from high over it, the water hidden.

var _out := "user://"
var _above := false


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--out="):
			_out = arg.get_slice("=", 1)
		elif arg == "--above":
			_above = true
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
	if _above:
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
			["canyon_head", Vector3(70.0, 28.0, -20.0), Vector3(90.0, 22.0, -37.0)],
			["kelp_south", Vector3(36.0, 34.0, 40.0), Vector3(44.0, 30.0, 55.0)],
			["canyon_wall_north", Vector3(40.0, 0.0, -18.0), Vector3(40.0, 5.0, -42.0)],
			["canyon_wall_from_floor", Vector3(20.0, -20.0, -30.0), Vector3(30.0, 10.0, -45.0)],
			["canyon_from_rim", Vector3(30.0, 22.0, -55.0), Vector3(30.0, -10.0, -30.0)],
			["ruins_from_canyon", Sea.RUINS_AT + Vector3(30.0, -10.0, 10.0), Sea.RUINS_AT],
		]
	for shot: Array in shots:
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
