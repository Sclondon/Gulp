extends SceneTree
## The baked floor (data/monterey.bin) as a chart with a grid of game metres, for placing things:
## depth by colour, a line every 5 m of depth (darker every 25), land in tan, grid lines every 20 m
## with their coordinates. With --zones, Sea.ZONES' circles and the set pieces are drawn over it.
##
##   godot --path . --audio-driver Dummy --resolution 400x400 -s res://tools/bay_chart.gd -- --out=<png> [--zones]

const PX := 4.0


func _initialize() -> void:
	var out := ""
	var zones := false
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--out="):
			out = arg.get_slice("=", 1)
		elif arg == "--zones":
			zones = true
	var w := int((Bay.EAST - Bay.WEST) * PX)
	var h := int((Bay.SOUTH - Bay.NORTH) * PX)
	var img := Image.create(w, h, false, Image.FORMAT_RGB8)
	var light := Vector3(-0.6, 0.7, -0.5).normalized()
	for y in h:
		for x in w:
			var wx := Bay.WEST + (x + 0.5) / PX
			var wz := Bay.NORTH + (y + 0.5) / PX
			var g := Bay.SURFACE - Bay.ground(wx, wz)
			var gx := Bay.ground(wx + 0.5, wz) - Bay.ground(wx - 0.5, wz)
			var gz := Bay.ground(wx, wz + 0.5) - Bay.ground(wx, wz - 0.5)
			var n := Vector3(-gx, 1.0, -gz).normalized()
			var shade := clampf(n.dot(light), 0.0, 1.0) * 0.5 + 0.6
			var c: Color
			if g <= 0.0:
				c = Color(0.62, 0.58, 0.45)
			else:
				var t := clampf(g / 100.0, 0.0, 1.0)
				c = Color(0.72, 0.93, 0.92).lerp(Color(0.22, 0.6, 0.78), smoothstep(0.0, 0.25, t)).lerp(Color(0.03, 0.1, 0.32), smoothstep(0.2, 1.0, t))
				if fmod(g, 5.0) < 0.3:
					c = c.darkened(0.4 if fmod(g, 25.0) < 0.3 else 0.18)
			if fmod(wx + 1000.0, 20.0) < 0.25 or fmod(wz + 1000.0, 20.0) < 0.25:
				c = c.lerp(Color.WHITE, 0.35)
			img.set_pixel(x, y, Color(c.r * shade, c.g * shade, c.b * shade))
	var sheet := SubViewport.new()
	sheet.size = Vector2i(w, h)
	sheet.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(sheet)
	var picture := TextureRect.new()
	picture.texture = ImageTexture.create_from_image(img)
	sheet.add_child(picture)
	var to_px := func(p: Vector2) -> Vector2: return (p - Vector2(Bay.WEST, Bay.NORTH)) * PX
	for gx in range(int(ceil(Bay.WEST / 20.0)) * 20, int(Bay.EAST), 40):
		for gz in range(int(ceil(Bay.NORTH / 20.0)) * 20, int(Bay.SOUTH), 40):
			_text(sheet, "%d,%d" % [gx, gz], to_px.call(Vector2(gx, gz)) + Vector2(3, 1), 14, Color(1, 1, 1, 0.85))
	if zones:
		for zone: String in Sea.ZONES:
			for patch: Array in Sea.patches(zone):
				var r := float(patch[1])
				if r <= 0.0:
					continue
				var ring := Line2D.new()
				ring.width = 3.0
				ring.default_color = Color(1.0, 0.85, 0.2)
				for k in 49:
					ring.add_point(to_px.call(patch[0] + Vector2.from_angle(TAU * k / 48.0) * r))
				sheet.add_child(ring)
				_text(sheet, zone, to_px.call(patch[0]) - Vector2(20, 10), 22, Color(1.0, 0.95, 0.4))
		var marks := {"START": Sea.START, "liner": Vector2(Sea.WRECK_AT.x, Sea.WRECK_AT.z), "atlantis": Vector2(Sea.RUINS_AT.x, Sea.RUINS_AT.z),
				"pirate": Vector2(Sea.PIRATE_AT.x, Sea.PIRATE_AT.z)}
		for market: String in Sea.MARKETS:
			marks["$" + market] = Sea.MARKETS[market]
		for name: String in marks:
			var dot := ColorRect.new()
			dot.color = Color(1.0, 0.2, 0.2)
			dot.size = Vector2(10, 10)
			dot.position = to_px.call(marks[name]) - Vector2(5, 5)
			sheet.add_child(dot)
			_text(sheet, name, to_px.call(marks[name]) + Vector2(8, -12), 20, Color(1.0, 0.6, 0.6))
	for frame in 3:
		await process_frame
	await RenderingServer.frame_post_draw
	sheet.get_texture().get_image().save_png(out)
	print("CHART saved ", out)
	quit()


func _text(parent: Node, text: String, at: Vector2, size: int, colour: Color) -> void:
	var label := Label.new()
	label.text = text
	label.add_theme_font_size_override(&"font_size", size)
	label.add_theme_color_override(&"font_color", colour)
	label.add_theme_color_override(&"font_outline_color", Color.BLACK)
	label.add_theme_constant_override(&"outline_size", 5)
	label.position = at
	parent.add_child(label)
