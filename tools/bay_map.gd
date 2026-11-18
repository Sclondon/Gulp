extends SceneTree
## The bay seen from above, as a chart: depth in colours, the zones outlined and named, the
## places of the liner, Atlantis and the pirate ship, and the title boat's circle (for comparing
## with the user's drawing; tools/MONTEREY.md).
##   godot --path . --audio-driver Dummy -s tools/bay_map.gd -- --out=<png>
## Needs a window (it draws the names with a font); `--headless` writes the picture without them.

const PX := 2.0  # pixels a metre

var _out := "user://bay_map.png"


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--out="):
			_out = arg.get_slice("=", 1)
	var t0 := Time.get_ticks_msec()
	Bay.ground(0.0, 0.0)
	print("BAY grid built in %d ms" % (Time.get_ticks_msec() - t0))
	var t1 := Time.get_ticks_usec()
	var s := 0.0
	for i in 20000:
		s += Sea.ground(randf_range(-190.0, 140.0), randf_range(-160.0, 190.0))
	print("BAY ground() %.2f us a call" % ((Time.get_ticks_usec() - t1) / 20000.0))
	var w := int((Bay.EAST - Bay.WEST) * PX)
	var h := int((Bay.SOUTH - Bay.NORTH) * PX)
	var image := Image.create(w, h, false, Image.FORMAT_RGBA8)
	for py in h:
		for px in w:
			var x := Bay.WEST + px / PX
			var z := Bay.NORTH + py / PX
			var deep := Bay.SURFACE - Sea.ground(x, z)
			var c: Color
			if deep < 0.0:
				c = Color(0.55, 0.47, 0.32).lerp(Color(0.4, 0.5, 0.3), clampf(-deep / 4.0, 0.0, 1.0))
			else:
				c = Color(0.62, 0.86, 0.9).lerp(Color(0.18, 0.42, 0.66), clampf(deep / 25.0, 0.0, 1.0))
				if deep > 25.0:
					c = Color(0.18, 0.42, 0.66).lerp(Color(0.03, 0.06, 0.2), clampf((deep - 25.0) / 80.0, 0.0, 1.0))
				# contour every 10 m
				if fmod(deep, 10.0) < 0.35:
					c = c.darkened(0.25)
				# the beach strip's outer edge (dotted)
				if (px + py) % 6 < 3 and absf(Bay.shore_distance(Vector2(x, z)) - Bay.BEACH * Bay.K) < 0.5:
					c = Color(1.0, 0.2, 0.8)
			image.set_pixel(px, py, c)
	var tex := ImageTexture.create_from_image(image)
	if DisplayServer.get_name() == "headless":
		image.save_png(_out)
		print("BAY MAP (no names) ", _out)
		quit()
		return
	var view := SubViewport.new()
	view.size = Vector2i(w, h)
	view.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	get_root().add_child(view)
	var chart := Chart.new()
	chart.texture = tex
	chart.size = Vector2(w, h)
	view.add_child(chart)
	await process_frame
	await process_frame
	await RenderingServer.frame_post_draw
	view.get_texture().get_image().save_png(_out)
	print("BAY MAP ", _out)
	quit()


class Chart extends Control:
	var texture: Texture2D

	func _at(p: Vector2) -> Vector2:
		return (p - Vector2(Bay.WEST, Bay.NORTH)) * PX

	func _draw() -> void:
		draw_texture(texture, Vector2.ZERO)
		var font := ThemeDB.fallback_font
		var colours := {"river": Color(0.2, 0.6, 1.0), "grass": Color(0.6, 0.2, 0.8), "sand": Color(0.95, 0.85, 0.1), "kelp": Color(0.9, 0.1, 0.1),
				"reef": Color(0.1, 0.75, 0.2), "open": Color(1.0, 0.55, 0.0), "trench": Color(0.1, 0.2, 1.0), "docks": Color(0.0, 0.9, 0.9),
				"ruins": Color(1.0, 0.85, 0.4), "pirate": Color(0.05, 0.05, 0.05), "beach": Color(1.0, 0.2, 0.8)}
		# the shelf's edge
		var edge := PackedVector2Array()
		var z := Bay.NORTH
		while z <= Bay.SOUTH:
			edge.append(_at(Vector2(Bay.edge_at(z), z)))
			z += 4.0
		draw_polyline(edge, colours.open, 3.0)
		for zone: String in Sea.ZONES:
			var entry: Dictionary = Sea.ZONES[zone]
			var colour: Color = colours.get(zone, Color.WHITE)
			if zone == "beach" or zone == "open":
				draw_string(font, _at(entry.at) - Vector2(30, 0), zone.to_upper(), HORIZONTAL_ALIGNMENT_LEFT, -1, 22, colour)
				continue
			for patch: Array in Sea.patches(zone):
				draw_arc(_at(patch[0]), float(patch[1]) * PX, 0.0, TAU, 64, colour, 3.0)
				draw_string(font, _at(patch[0]) - Vector2(30, -8), zone.to_upper(), HORIZONTAL_ALIGNMENT_LEFT, -1, 22, colour)
		# the beach strip: where the depth is 0.5 to 5 m
		for piece: Array in [[Sea.WRECK_AT, Sea.WRECK_HEADING, Vector2(14, 64), "liner"], [Sea.PIRATE_AT, Sea.PIRATE_HEADING, Vector2(12, 34), "pirate ship"],
				[Sea.RUINS_AT, Sea.RUINS_HEADING, Vector2(70, 70), "Atlantis"]]:
			var at: Vector3 = piece[0]
			var h: float = piece[1]
			var size: Vector2 = piece[2]
			var along := Vector2(sin(h), cos(h))
			var across := Vector2(along.y, -along.x)
			var mid := Vector2(at.x, at.z)
			var box := PackedVector2Array()
			for corner: Vector2 in [Vector2(-1, -1), Vector2(1, -1), Vector2(1, 1), Vector2(-1, 1), Vector2(-1, -1)]:
				box.append(_at(mid + across * corner.x * size.x * 0.5 + along * corner.y * size.y * 0.5))
			draw_polyline(box, Color.BLACK, 2.0)
		# the pirate ship's outcrop and its seal rock
		draw_circle(_at(Scenery.OUTCROP), 4.0 * PX, Color(0.25, 0.22, 0.2))
		draw_arc(_at(Scenery.OUTCROP), 16.0 * PX, 0.0, TAU, 32, Color(0.25, 0.22, 0.2), 1.5)
		draw_string(font, _at(Scenery.OUTCROP) + Vector2(-40, -36), "seal rock", HORIZONTAL_ALIGNMENT_LEFT, -1, 16, Color.WHITE)
		# the docks themselves
		draw_string(font, _at(Scenery.MONTEREY) + Vector2(-30, 40), "Monterey", HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color.WHITE)
		draw_string(font, _at(Scenery.SANTA_CRUZ) + Vector2(24, 34), "Santa Cruz", HORIZONTAL_ALIGNMENT_LEFT, -1, 14, Color.WHITE)
		# the title boat's circle
		var start: Vector2 = Sea.START
		draw_arc(_at(start + Vector2(45.0, 4.0)), 45.0 * PX, 0.0, TAU, 96, Color.WHITE, 1.5)
		draw_circle(_at(start), 5.0, Color.WHITE)
		draw_string(font, _at(start) + Vector2(8, 4), "start", HORIZONTAL_ALIGNMENT_LEFT, -1, 18, Color.WHITE)
		draw_string(font, Vector2(10, 26), "N up (-Z)   1 px = 0.5 m (world)   contours every 10 m", HORIZONTAL_ALIGNMENT_LEFT, -1, 18, Color.WHITE)
