extends SceneTree
## Pictures of a barrel at a surf break (scripts/breakers.gd; tools/WATER_FX.md, "Barrels"). Runs the
## game (main.tscn) with the arguments after --, holds the water's clock where one section of a break
## is at a given stage of its break, puts the eye where asked relative to that section's tube, and
## saves a picture for each stage given:
##
##   godot --path . --audio-driver Dummy --resolution 390x844 -s res://tests/barrel_shot.gd
##       -- --offline --hour=11 --dir=<folder> [--tag=name] [--site=steamer_lane] [--at=0.5]
##       [--stages=0.2,0.55,0.8,1.0,1.2] [--view=side|inside|under|beach|sea|top] [--debug=4]
##
## --at is how far along the strip (0..1) the section is; --view: side (from in front of the shoulder,
## looking along into the tube), inside (in the tube looking out along it to its open end), under
## (under the water in front of it, looking up at the lip), beach (from the shore), sea (from behind,
## out at sea), top (from above). The wave's height H scales every distance. Prints a BARREL line each.

var _main: Node
var _dir := ""
var _tag := "barrel"
var _site := "steamer_lane"
var _at := 0.5
var _stages: Array[float] = [0.8]
var _view := "side"
var _debug := 0
var _clock := 0.0
var _hold := -1.0
var _eye := Vector3.INF
var _look := Vector3.INF
var _saving := false
var _settle := 0
var _follow := false
var _aimed := false


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		var v := arg.get_slice("=", 1)
		if arg.begins_with("--dir="):
			_dir = v
		elif arg.begins_with("--tag="):
			_tag = v
		elif arg.begins_with("--site="):
			_site = v
		elif arg.begins_with("--at="):
			_at = float(v)
		elif arg.begins_with("--stages="):
			_stages.clear()
			for s in v.split(","):
				_stages.append(float(s))
		elif arg.begins_with("--view="):
			_view = v
		elif arg.begins_with("--debug="):
			_debug = int(v)
		elif arg == "--follow":
			_follow = true
	DirAccess.make_dir_recursive_absolute(_dir)
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_NO_FOCUS, true)
	_main = (load("res://main.tscn") as PackedScene).instantiate()
	root.add_child(_main)
	RenderingServer.frame_pre_draw.connect(_place)


func _site_data() -> Dictionary:
	for site: Dictionary in Breakers.sites():
		if site.name == _site:
			return site
	return Breakers.sites()[0]


# The first time from `from` on when the section is at `stage`.
func _time_for(site: Dictionary, i: int, stage: float, from: float) -> float:
	var best := from
	var off := INF
	var t := from
	while t < from + Surf.PERIOD + 0.1:
		var cr := Breakers.crest(site.points[i], site.ways[i], t)
		var s: float = (cr.y - float(site.tb[i])) / Breakers.BREAK_TIME
		if absf(s - stage) < off:
			off = absf(s - stage)
			best = t
		t += 0.01
	return best


func _aim(site: Dictionary, i: int) -> void:
	var t := _hold
	var base: Vector2 = site.points[i]
	var way: Vector2 = site.ways[i]
	var cr := Breakers.crest(base, way, t)
	var dc := Breakers.d_of(cr.x)
	var h: float = site.height * (0.8 + 0.3 * sin(cr.z * 0.27 + 1.0)) / 1.1
	var crest := base + (Breakers.DEPTH_LINE - dc) * way
	# (the strip runs from section 0 to the last: the break peels that way, so the open end of the
	# tube is towards the higher sections)
	var pts: PackedVector2Array = site.points
	var along := (pts[mini(i + 1, pts.size() - 1)] - pts[maxi(i - 1, 0)]).normalized()
	var tube := crest + way * 0.7 * h
	var tube_y := Sea.SURFACE + 0.32 * h
	var at := Vector3(tube.x, tube_y, tube.y)
	var way3 := Vector3(way.x, 0.0, way.y)
	var along3 := Vector3(along.x, 0.0, along.y)
	match _view:
		"side":
			_eye = at + along3 * 5.5 * h + way3 * 2.2 * h + Vector3(0.0, 0.25 * h, 0.0)
			_look = at + along3 * 0.5 * h
		"inside":
			_eye = at - along3 * 0.6 * h + Vector3(0.0, -0.05 * h, 0.0)
			_look = at + along3 * 4.0 * h + way3 * 0.15 * h
		"under":
			_eye = at + way3 * 1.1 * h + along3 * 2.0 * h + Vector3(0.0, -0.32 * h - 2.0, 0.0)
			_look = at + way3 * 0.3 * h - along3 * 1.0 * h + Vector3(0.0, 0.2 * h, 0.0)
		"beach":
			_eye = at + way3 * 6.0 * h + along3 * 2.5 * h + Vector3(0.0, 0.4 * h, 0.0)
			_look = at
		"sea":
			_eye = at - way3 * 6.0 * h + along3 * 2.0 * h + Vector3(0.0, 1.2 * h, 0.0)
			_look = at
		"top":
			_eye = at + way3 * 3.0 * h + along3 * 3.0 * h + Vector3(0.0, 5.0 * h, 0.0)
			_look = at
		"high":
			_eye = at + way3 * 4.0 * h + Vector3(0.0, 16.0 * h, 0.0)
			_look = at + way3 * 3.9 * h
	print("BARREL %s section %d of %d, stage %.2f at t %.2f, height %.2f m, tube %s" % [_site, i, pts.size(), (cr.y - float(site.tb[i])) / Breakers.BREAK_TIME, t, h, at])


func _process(delta: float) -> bool:
	_clock += delta
	if Time.get_ticks_msec() > 120000 or _main == null or _main.get_script() == null or (_clock > 1.0 and _main.get(&"player") == null):
		print("BARREL GAVE UP (the game did not start, or took too long)")
		return true
	if _clock < 1.5:
		return false
	_main.set(&"limited", false)
	if _saving:
		return false
	if _stages.is_empty():
		return true
	var site := _site_data()
	var i := clampi(int(round(_at * (site.points.size() - 1))), 0, site.points.size() - 1)
	if _hold < 0.0 or _settle == 0:
		var sea: Node = _main.get(&"sea")
		_hold = _time_for(site, i, _stages[0], maxf(float(sea.get(&"clock")), 2.0))
		# (the eye stays where it was put for the first stage, so a strip shows one wave going by;
		# --follow puts it again for each)
		if _follow or not _aimed:
			_aim(site, i)
			_aimed = true
		_settle = 1
		return false
	_settle += 1
	# (a few frames for the spray to fly and the picture to settle)
	if _settle >= 12:
		_saving = true
		_save(_stages.pop_front())
	return false


func _place() -> void:
	if _main == null or not is_instance_valid(_main) or _eye == Vector3.INF:
		return
	var sea: Node = _main.get(&"sea")
	if sea == null:
		return
	# (the clock held, the spray going on: the spray is fed from Surf.clock)
	sea.set(&"clock", _hold)
	Surf.clock = _hold
	RenderingServer.global_shader_parameter_set(&"water_clock", _hold)
	var cam: Camera3D = _main.get(&"camera")
	if cam == null:
		return
	for each in [&"pad", &"hud"]:
		var node: CanvasItem = _main.get(each)
		if node:
			node.visible = false
	cam.global_position = _eye
	cam.look_at(_look, Vector3.UP)
	cam.force_update_transform()
	if _debug > 0:
		(sea.get(&"_water") as ShaderMaterial).set_shader_parameter(&"surf_debug", _debug)
	var above := _eye.y > Sea.surface_height(_eye.x, _eye.z)
	sea.call(&"set_above", above)
	var post: ShaderMaterial = _main.get(&"_post")
	if post:
		post.set_shader_parameter(&"underwater", 0.0 if above else 1.0)


func _save(stage: float) -> void:
	await RenderingServer.frame_post_draw
	var file := "%s/%s_%s_%.2f.png" % [_dir, _tag, _view, stage]
	root.get_texture().get_image().save_png(file)
	print("BARREL saved %s" % file.get_file())
	_settle = 0
	_saving = false
