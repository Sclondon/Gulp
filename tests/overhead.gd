extends SceneTree
## The whole bay from straight above, as a chart: the floor and every piece of scenery, with the
## water, fog, snow and the post shader left out, in plain light from the upper left. It is taken
## in TILE-metre squares (the scenery draws only what is near its eye, so the eye is moved over
## each square) and stitched, then the places (Sea.ZONES) and set pieces are written over it.
##
##   godot --path . --audio-driver Dummy --resolution 400x400 -s res://tests/overhead.gd -- --out=<new folder>
##
## Saves overhead_raw.png (no labels) and overhead.png (labelled). Prints OVERHEAD DONE.

const TILE := 32.0
const PX := 256
const LABELLED := 1600

var _out := ""
var _view: SubViewport
var _camera: Camera3D
var _focus: Node3D
var _sea: Sea


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--out="):
			_out = arg.get_slice("=", 1)
	DirAccess.make_dir_recursive_absolute(_out)
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_NO_FOCUS, true)
	_view = SubViewport.new()
	_view.size = Vector2i(PX, PX)
	_view.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(_view)
	_focus = Node3D.new()
	_view.add_child(_focus)
	_camera = Camera3D.new()
	_camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	_camera.size = TILE
	_camera.near = 0.05
	_camera.far = 400.0
	_view.add_child(_camera)
	_camera.current = true
	_sea = Sea.new()
	_view.add_child(_sea)
	var scenery := Scenery.new()
	_view.add_child(scenery)
	_shoot()


func _plain() -> void:
	var env: Environment = _sea._env
	env.fog_enabled = false
	env.background_color = Color(0.05, 0.08, 0.12)
	env.ambient_light_color = Color(1.0, 1.0, 1.0)
	env.ambient_light_energy = 0.5
	env.glow_enabled = false
	for light: DirectionalLight3D in _sea.find_children("*", "DirectionalLight3D", true, false):
		light.light_color = Color(1.0, 0.97, 0.92)
		light.light_energy = 1.1
		light.global_basis = Basis.looking_at(Vector3(0.5, -1.0, 0.6).normalized(), Vector3.FORWARD)
	for node: Node in _sea.get_children():
		if node.name == "Water" or node.name == "Snow" or node is LightShafts or node is CPUParticles3D:
			(node as Node3D).visible = false


# Everything drawn whatever the distance: visibility ranges off, the scenery's near-and-far fields
# looking from the square's own floor, the wreck's halves shown.
func _uncull() -> void:
	for node: Node in _view.find_children("*", "", true, false):
		if node is GeometryInstance3D:
			(node as GeometryInstance3D).visibility_range_end = 0.0
			(node as GeometryInstance3D).visibility_range_begin = 0.0
		if node is LodField:
			(node as LodField).eye = _focus
			(node as LodField).far = INF
		if node is Wreck:
			node.set_process(false)
			for child: Node in node.find_children("*", "Node3D", true, false):
				(child as Node3D).visible = true


func _shoot() -> void:
	await process_frame
	_sea.eye = _focus
	_sea.sand.focus = _focus
	for frame in 6:
		await process_frame
	_plain()
	_uncull()
	var cols := ceili((Sea.EAST - Sea.WEST) / TILE)
	var rows := ceili((Sea.SOUTH - Sea.NORTH) / TILE)
	var whole := Image.create(cols * PX, rows * PX, false, Image.FORMAT_RGB8)
	for r in rows:
		for c in cols:
			var x := Sea.WEST + (c + 0.5) * TILE
			var z := Sea.NORTH + (r + 0.5) * TILE
			_focus.global_position = Vector3(x, Sea.ground(x, z) + 6.0, z)
			_camera.global_position = Vector3(x, Sea.SURFACE + 6.0, z)
			_camera.global_basis = Basis.looking_at(Vector3.DOWN, Vector3.FORWARD)
			for frame in 5:
				await process_frame
			_plain()
			await RenderingServer.frame_post_draw
			var tile := _view.get_texture().get_image()
			tile.convert(Image.FORMAT_RGB8)
			whole.blit_rect(tile, Rect2i(0, 0, PX, PX), Vector2i(c * PX, r * PX))
		print("OVERHEAD row %d of %d" % [r + 1, rows])
	whole.save_png(_out.path_join("overhead_raw.png"))
	await _label(whole, cols * TILE, rows * TILE)
	print("OVERHEAD DONE")
	quit()


func _label(whole: Image, wide: float, high: float) -> void:
	var w := LABELLED
	var h := int(LABELLED * high / wide)
	var small := whole.duplicate() as Image
	small.resize(w, h, Image.INTERPOLATE_LANCZOS)
	var sheet := SubViewport.new()
	sheet.size = Vector2i(w, h)
	sheet.transparent_bg = false
	sheet.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(sheet)
	var picture := TextureRect.new()
	picture.texture = ImageTexture.create_from_image(small)
	picture.size = Vector2(w, h)
	sheet.add_child(picture)
	var scale := w / wide
	var to_px := func(p: Vector2) -> Vector2: return Vector2((p.x - Sea.WEST) * scale, (p.y - Sea.NORTH) * scale)
	var marks := {}
	for zone: String in Sea.ZONES:
		if float(Sea.ZONES[zone].radius) > 0.0:
			marks[zone] = Sea.ZONES[zone].at
	marks["START"] = Sea.START
	marks["liner"] = Vector2(Sea.WRECK_AT.x, Sea.WRECK_AT.z) + Vector2(0.0, 8.0)
	marks["atlantis"] = Vector2(Sea.RUINS_AT.x, Sea.RUINS_AT.z) + Vector2(0.0, 8.0)
	marks["pirate ship"] = Vector2(Sea.PIRATE_AT.x, Sea.PIRATE_AT.z) + Vector2(0.0, 6.0)
	for market: String in Sea.MARKETS:
		marks["market: " + market] = Sea.MARKETS[market]
	for name: String in marks:
		var label := Label.new()
		label.text = name
		label.add_theme_font_size_override(&"font_size", 22)
		label.add_theme_color_override(&"font_color", Color(1.0, 0.95, 0.4))
		label.add_theme_color_override(&"font_outline_color", Color.BLACK)
		label.add_theme_constant_override(&"outline_size", 6)
		sheet.add_child(label)
		label.position = to_px.call(marks[name]) - Vector2(name.length() * 6.0, 12.0)
	# A 50 m bar, bottom left.
	var bar := ColorRect.new()
	bar.color = Color.WHITE
	bar.size = Vector2(50.0 * scale, 6.0)
	bar.position = Vector2(20.0, h - 30.0)
	sheet.add_child(bar)
	var bar_label := Label.new()
	bar_label.text = "50 m   (north up)"
	bar_label.add_theme_font_size_override(&"font_size", 20)
	bar_label.add_theme_constant_override(&"outline_size", 6)
	bar_label.add_theme_color_override(&"font_outline_color", Color.BLACK)
	bar_label.position = Vector2(20.0, h - 60.0)
	sheet.add_child(bar_label)
	for frame in 3:
		await process_frame
	await RenderingServer.frame_post_draw
	sheet.get_texture().get_image().save_png(_out.path_join("overhead.png"))
