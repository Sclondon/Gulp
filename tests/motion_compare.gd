extends SceneTree
## Each kind's motion as its own (baked) shader moves it against its motion family's
## (scripts/motion.gd), frame by frame. A window (headless draws nothing):
##
##   godot --path . --audio-driver Dummy --resolution 640x360 -s res://tests/motion_compare.gd -- \
##     --out=<folder> [--kinds=sardine,orca,...] [--sway=1] [--paint] [--set=walk:1,claws:0.5]
##
## For each kind: 8 frames through one beat (phase 0, 1/8, ...), then the mouth open (gape 1), then
## turning (curl 0.6) and arched (arch 0.5), each from above and from the side (orthographic, the nose
## to the left). In every tile grey is where both draw the animal, red where only its own shader does,
## cyan where only the family does (`--paint`: the family's paint where both draw). Prints
## `MOTION <kind> mean <share> worst <share> (<frame>)`: the share of the drawn area where they
## disagree (0 the same). Sheets: `<out>/<kind>.png`. Kinds with no motion spec print `MOTION <kind> none`.

const TILE := Vector2i(150, 96)
const FRAMES := ["0", "1/8", "2/8", "3/8", "4/8", "5/8", "6/8", "7/8", "gape", "curl", "arch"]

var _out := ""
var _kinds: PackedStringArray = []
var _sway := -1.0
var _paint := false
# (settings held through every frame: --set=walk:1,claws:0.5)
var _sets := {}
var _view: SubViewport
var _stage: Node3D
var _camera: Camera3D


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--out="):
			_out = arg.get_slice("=", 1)
		elif arg.begins_with("--kinds="):
			_kinds = arg.get_slice("=", 1).split(",")
		elif arg.begins_with("--sway="):
			_sway = float(arg.get_slice("=", 1))
		elif arg == "--paint":
			_paint = true
		elif arg.begins_with("--set="):
			for pair in arg.get_slice("=", 1).split(","):
				_sets[StringName(pair.get_slice(":", 0))] = float(pair.get_slice(":", 1))
	if _kinds.is_empty():
		for kind: String in Species.ALL:
			if Species.has(kind) and Species.of(kind).script != "":
				_kinds.append(kind)
	DirAccess.make_dir_recursive_absolute(_out)
	_run.call_deferred()


func _make_view() -> void:
	_view = SubViewport.new()
	_view.own_world_3d = true
	_view.transparent_bg = true
	_view.size = TILE
	_view.msaa_3d = Viewport.MSAA_DISABLED
	_view.render_target_update_mode = SubViewport.UPDATE_DISABLED
	root.add_child(_view)
	var env := WorldEnvironment.new()
	env.environment = Environment.new()
	env.environment.background_mode = Environment.BG_CLEAR_COLOR
	env.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.environment.ambient_light_color = Color(0.6, 0.65, 0.7)
	_view.add_child(env)
	var sun := DirectionalLight3D.new()
	sun.rotation = Vector3(-1.0, 0.5, 0.0)
	_view.add_child(sun)
	_camera = Camera3D.new()
	_camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	_view.add_child(_camera)
	_stage = Node3D.new()
	_view.add_child(_stage)


func _run() -> void:
	_make_view()
	for kind in _kinds:
		await _compare(kind)
	print("MOTION done: %d kinds" % _kinds.size())
	quit()


func _make(kind: String, family: bool) -> Node3D:
	var look := Species.make(kind, false)
	if look == null:
		return null
	if &"game" in look:
		look.set(&"game", true)
	if &"cartoon_eyes" in look:
		look.set(&"cartoon_eyes", 1.0)
	if &"pattern_seed" in look:
		look.set(&"pattern_seed", 13)
	BakedLook.families = family
	BakedLook.apply(look)
	BakedLook.families = true
	return look


func _materials(look: Node3D) -> Array:
	var out: Array = []
	for mi: MeshInstance3D in look.find_children("*", "MeshInstance3D", true, false):
		var ms: Array = [mi.material_override]
		for s in mi.get_surface_override_material_count():
			ms.append(mi.get_surface_override_material(s))
		if mi.mesh:
			for s in mi.mesh.get_surface_count():
				ms.append(mi.get_active_material(s))
		for m in ms:
			if m is ShaderMaterial and not out.has(m):
				out.append(m)
	return out


func _uses_family(look: Node3D) -> bool:
	for m: ShaderMaterial in _materials(look):
		if m.has_meta(&"motion_own"):
			return true
	return false


func _pose(look: Node3D, frame: int, has: Dictionary) -> void:
	for m: ShaderMaterial in _materials(look):
		if not m.has_meta(&"mc_sway"):
			m.set_meta(&"mc_sway", m.get_shader_parameter(&"sway"))
		var sway: Variant = m.get_meta(&"mc_sway")
		if _sway >= 0.0:
			sway = _sway
		m.set_shader_parameter(&"phase", float(frame) / 8.0 if frame < 8 else 0.25)
		if sway != null:
			m.set_shader_parameter(&"sway", sway)
		m.set_shader_parameter(&"gape", 1.0 if frame == 8 else 0.0)
		if has.has(&"curl"):
			m.set_shader_parameter(&"curl", 0.6 if frame == 9 else 0.0)
		if has.has(&"arch"):
			m.set_shader_parameter(&"arch", 0.5 if frame == 10 else 0.0)
		for k: StringName in _sets:
			m.set_shader_parameter(k, _sets[k])


func _shot() -> Image:
	_view.render_target_update_mode = SubViewport.UPDATE_ONCE
	await RenderingServer.frame_post_draw
	var image := _view.get_texture().get_image()
	image.convert(Image.FORMAT_RGBA8)
	return image


func _compare(kind: String) -> void:
	for c in _stage.get_children():
		c.free()
	var own := _make(kind, false)
	var fam := _make(kind, true)
	if own == null or fam == null:
		print("MOTION %s none (no component)" % kind)
		return
	_stage.add_child(own)
	_stage.add_child(fam)
	await process_frame
	await process_frame
	if not _uses_family(fam):
		print("MOTION %s none (no motion spec)" % kind)
		return
	if OS.get_cmdline_user_args().has("--verbose"):
		for m: ShaderMaterial in _materials(own):
			print("  own wears ", m.shader.resource_path)
		for m: ShaderMaterial in _materials(fam):
			print("  family wears ", m.shader.resource_path, " ops ", m.get_shader_parameter(&"op_count"))
	# (what its own shader takes: the family is not turned or arched where its own was not)
	var has := {}
	for m: ShaderMaterial in _materials(own):
		for u: Dictionary in m.shader.get_shader_uniform_list():
			has[StringName(u.name)] = true
	# (the box round both at rest)
	var box := AABB()
	var first := true
	for mi: MeshInstance3D in own.find_children("*", "MeshInstance3D", true, false):
		if mi.visible and mi.mesh:
			var b := mi.global_transform * mi.mesh.get_aabb()
			box = b if first else box.merge(b)
			first = false
	var middle := box.get_center()
	var size := box.size.length() * 0.62
	var sheet := Image.create(TILE.x * FRAMES.size(), TILE.y * 2 + 14, false, Image.FORMAT_RGBA8)
	sheet.fill(Color(0.1, 0.1, 0.12))
	var worst := 0.0
	var worst_at := ""
	var total := 0.0
	var n := 0
	for view in 2:
		_camera.size = size
		if view == 0:
			_camera.position = middle + Vector3(0.0, size * 2.0, 0.0)
			_camera.look_at(middle, Vector3.LEFT)
		else:
			_camera.position = middle + Vector3(size * 2.0, 0.0, 0.0)
			_camera.look_at(middle, Vector3.UP)
		_camera.near = 0.01 * size
		_camera.far = size * 5.0
		for f in FRAMES.size():
			_pose(own, f, has)
			_pose(fam, f, has)
			own.visible = true
			fam.visible = false
			await process_frame
			var a := await _shot()
			own.visible = false
			fam.visible = true
			await process_frame
			var b := await _shot()
			var only_a := 0
			var only_b := 0
			var both := 0
			var tile := Image.create(TILE.x, TILE.y, false, Image.FORMAT_RGBA8)
			for y in TILE.y:
				for x in TILE.x:
					var ca := a.get_pixel(x, y)
					var cb := b.get_pixel(x, y)
					var ia := ca.a > 0.5
					var ib := cb.a > 0.5
					var out := Color(0.1, 0.1, 0.12)
					if ia and ib:
						both += 1
						out = Color(cb.r, cb.g, cb.b) if _paint else Color(0.62, 0.62, 0.62)
					elif ia:
						only_a += 1
						out = Color(0.95, 0.15, 0.1)
					elif ib:
						only_b += 1
						out = Color(0.1, 0.85, 0.95)
					tile.set_pixel(x, y, out)
			var union := both + only_a + only_b
			var off := float(only_a + only_b) / float(maxi(union, 1))
			total += off
			n += 1
			if off > worst:
				worst = off
				worst_at = "%s %s" % [FRAMES[f], "above" if view == 0 else "side"]
			sheet.blit_rect(tile, Rect2i(Vector2i.ZERO, TILE), Vector2i(f * TILE.x, 14 + view * TILE.y))
	own.queue_free()
	fam.queue_free()
	sheet.save_png(_out.path_join(kind + ".png"))
	print("MOTION %s mean %.3f worst %.3f (%s)" % [kind, total / float(n), worst, worst_at])
