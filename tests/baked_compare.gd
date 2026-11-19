extends SceneTree
## Each kind drawn as its component draws it (its own shader) beside its baked look (BakedLook), lit
## as the sea lights it, from the side and from above and behind, on one sheet (tools/PERF.md,
## "Shader programs"). A window (headless draws nothing):
##
##   godot --path . --audio-driver Dummy --resolution 1280x720 -s res://tests/baked_compare.gd -- \
##     --out=<folder> [--kinds=garibaldi,orca,...] [--columns=4]
##
## Every tile: left the old look, right the baked one, labelled. Kinds with no baked look are drawn
## once and marked "not baked". `--vertex-old` lights the old look per vertex too. One sheet per 16 kinds (`sheet_<n>.png`).

const TILE := Vector2i(320, 180)

var _out := ""
var _kinds: PackedStringArray = []
var _columns := 4
# (the old look lit per vertex too, to tell the bake's difference from the lighting's)
var _vertex_old := false
var _view: SubViewport
var _stage: Node3D
var _camera: Camera3D


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--out="):
			_out = arg.get_slice("=", 1)
		elif arg.begins_with("--kinds="):
			_kinds = arg.get_slice("=", 1).split(",")
		elif arg == "--vertex-old":
			_vertex_old = true
		elif arg.begins_with("--columns="):
			_columns = int(arg.get_slice("=", 1))
	if _kinds.is_empty():
		for kind: String in Species.ALL:
			if Species.has(kind) and Species.of(kind).script != "":
				_kinds.append(kind)
	DirAccess.make_dir_recursive_absolute(_out)
	_run.call_deferred()


func _make_view() -> void:
	_view = SubViewport.new()
	_view.own_world_3d = true
	_view.size = TILE
	_view.msaa_3d = Viewport.MSAA_4X
	_view.render_target_update_mode = SubViewport.UPDATE_DISABLED
	root.add_child(_view)
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_COLOR
	env.environment.background_color = Color(0.32, 0.4, 0.46)
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.45, 0.55, 0.6)
	env.environment.ambient_light_energy = 0.7
	_view.add_child(env)
	var sun := DirectionalLight3D.new()
	sun.rotation = Vector3(-1.0, 0.5, 0.0)
	sun.light_energy = 1.1
	_view.add_child(sun)
	_camera = Camera3D.new()
	_camera.fov = 30.0
	_view.add_child(_camera)
	_stage = Node3D.new()
	_view.add_child(_stage)


func _run() -> void:
	_make_view()
	var tiles: Array = []
	var sheet := 0
	for kind in _kinds:
		for angle in [0, 1]:
			tiles.append(await _tile(kind, angle))
		if tiles.size() >= 32:
			_save(tiles, sheet)
			sheet += 1
			tiles.clear()
	if not tiles.is_empty():
		_save(tiles, sheet)
	print("COMPARE done: %d kinds" % _kinds.size())
	quit()


func _make(kind: String, baked: bool) -> Node3D:
	var look := Species.make(kind, false)
	if look == null:
		return null
	if &"game" in look:
		look.set(&"game", true)
	if &"cartoon_eyes" in look:
		look.set(&"cartoon_eyes", 1.0)
	if &"pattern_seed" in look:
		look.set(&"pattern_seed", 13)
	if baked:
		BakedLook.apply(look)
	elif _vertex_old and look.has_method(&"material"):
		var m: ShaderMaterial = look.call(&"material")
		var lit := Shader.new()
		lit.code = m.shader.code.replace("render_mode ", "render_mode vertex_lighting, ")
		m.shader = lit
	return look


func _tile(kind: String, angle: int) -> Image:
	for c in _stage.get_children():
		c.free()
	var old := _make(kind, false)
	var new := _make(kind, true)
	var long := Species.long_of(kind, old) if old else 1.0
	var baked := new != null and BakedLook.has_look(new.get_script())
	var holder_a := Node3D.new()
	holder_a.scale = Vector3.ONE / long
	_stage.add_child(holder_a)
	if old:
		holder_a.add_child(old)
	var holder_b := Node3D.new()
	holder_b.scale = Vector3.ONE / long
	_stage.add_child(holder_b)
	if new:
		holder_b.add_child(new)
	holder_a.position = Vector3(0.0, 0.5, 0.0)
	holder_b.position = Vector3(0.0, -0.5, 0.0)
	# (side on, the nose to the left; or from above and behind)
	if angle == 0:
		_camera.position = Vector3(-3.6, 0.0, 0.0)
		_camera.look_at(Vector3.ZERO, Vector3.UP)
	else:
		_camera.position = Vector3(-2.3, 2.0, 1.8)
		_camera.look_at(Vector3.ZERO, Vector3.UP)
	for i in 4:
		await process_frame
	_view.render_target_update_mode = SubViewport.UPDATE_ONCE
	await RenderingServer.frame_post_draw
	var image := _view.get_texture().get_image()
	image.convert(Image.FORMAT_RGBA8)
	_label(image, kind + ("" if baked else " (not baked)"))
	return image


func _label(image: Image, text: String) -> void:
	# (a dark bar on top; the name is printed by the sheet's index file)
	for y in 3:
		for x in image.get_width():
			image.set_pixel(x, y, Color.BLACK)
	image.set_meta(&"label", text)


func _save(tiles: Array, sheet: int) -> void:
	var rows := ceili(tiles.size() / float(_columns))
	var out := Image.create(TILE.x * _columns, TILE.y * rows, false, Image.FORMAT_RGBA8)
	var names: PackedStringArray = []
	for i in tiles.size():
		var t: Image = tiles[i]
		out.blit_rect(t, Rect2i(Vector2i.ZERO, TILE), Vector2i((i % _columns) * TILE.x, (i / _columns) * TILE.y))
		names.append("%d: %s" % [i, t.get_meta(&"label", "")])
	out.save_png(_out.path_join("sheet_%d.png" % sheet))
	var f := FileAccess.open(_out.path_join("sheet_%d.txt" % sheet), FileAccess.WRITE)
	f.store_string("\n".join(names))
	f.close()
