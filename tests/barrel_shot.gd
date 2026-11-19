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
## out at sea), top (from above), high (a drone over the shoulder), wide (from the beach, well back: the whole
## strip). The wave's height H scales every distance. Prints a BARREL line each.
##
## --run [--run-for=9] (third pass): the clock is not held but RUNS from the first stage given to the last (or for
## that long), and every frame is saved (<tag>_<view>_NNN.png). With --fixed-fps 25 the frames are 0.04 s apart, a
## stage step of 0.02, so the spray and the crash fly as the player sees them (--fixed-fps 30 for a clip).

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
var _run := false
var _seconds := 0.0
var _run_start := 0.0
var _run_end := 0.0
var _frame := 0
var _recording := false


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
		elif arg == "--run":
			_run = true
		elif arg.begins_with("--run-for="):
			_seconds = float(v)
	DirAccess.make_dir_recursive_absolute(_dir)
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_NO_FOCUS, true)
	_main = (load("res://main.tscn") as PackedScene).instantiate()
	root.add_child(_main)
	RenderingServer.frame_pre_draw.connect(_place)
	RenderingServer.frame_post_draw.connect(_grab)


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


## (Second round: the views that ride with the tube, a surfer's and a diver's, are put again for every
## stage, so the eye stays in the tube or under it as the wave comes in; the others stay where the
## wave is at stage 0.7, in the middle of the break, so the frame holds the whole curl.)
const RIDING := ["inside", "under"]


func _aim(site: Dictionary, i: int, t: float) -> void:
	var base: Vector2 = site.points[i]
	var way: Vector2 = site.ways[i]
	var cr := Breakers.crest(base, way, t)
	var dc := Breakers.d_of(cr.x)
	var h: float = float(site.heights[i]) * Breakers.sets(cr.z)
	var crest := base + (Breakers.DEPTH_LINE - dc) * way
	# (the strip runs from section 0 to the last: the break peels that way, so the open end of the
	# tube is towards the higher sections)
	var pts: PackedVector2Array = site.points
	var along := (pts[mini(i + 1, pts.size() - 1)] - pts[maxi(i - 1, 0)]).normalized()
	# (the middle of the tube: 0.8 heights in from the crest, a third of a height up, on the water's
	# own level there, the swell)
	var tube := crest + way * 0.8 * h
	var level: float = Breakers.water_at(tube, t, 1.0)[1]
	var tube_y := Sea.SURFACE + level + 0.34 * h
	var at := Vector3(tube.x, tube_y, tube.y)
	var way3 := Vector3(way.x, 0.0, way.y)
	var along3 := Vector3(along.x, 0.0, along.y)
	var up := Vector3.UP
	match _view:
		"side":
			_eye = at + along3 * 5.5 * h + way3 * 2.2 * h + up * 0.25 * h
			_look = at + along3 * 0.5 * h
		"inside":
			# (in the tube, low, looking out along it to its open end, the shoulder)
			# (lower as the tube closes after the lip lands, so it stays in the air pocket)
			var st: float = (cr.y - float(site.tb[i])) / Breakers.BREAK_TIME
			var sink := clampf((st - 0.9) / 0.45, 0.0, 1.0) * 0.28 * h
			_eye = at - along3 * 0.3 * h + up * (-0.05 * h - sink) + way3 * 0.1 * h
			_look = at + along3 * 4.0 * h + way3 * 0.1 * h + up * 0.05 * h
		"under":
			# (under the water behind the crest, where it is deep enough to swim, along it, looking in and up at
			# the wave going over, its lip and tube against the bright surface: under the tube itself the water is
			# too shallow for an eye, a barrel breaks in water little deeper than it is high)
			_eye = at - way3 * 2.2 * h + along3 * 1.5 * h + up * (-0.34 * h - 1.8)
			_eye.y = maxf(_eye.y, Sea.ground(_eye.x, _eye.z) + 0.3)
			_look = at + way3 * 0.2 * h - along3 * 0.6 * h + up * 0.3 * h
		"beach":
			# (from the shore, off to the side, so the eye sees into the open end of the tube)
			_eye = at + way3 * 3.5 * h + along3 * 5.0 * h + up * 0.9 * h
			_look = at - along3 * 0.8 * h + up * 0.1 * h
		"sea":
			# (out at sea behind the break and above it, as from a boat's deck or the bluff: over the crest
			# onto the lip throwing and the white water landing; from at the water out at sea a wave is only its
			# back and the plume off its crest)
			_eye = at - way3 * 4.0 * h + along3 * 3.0 * h + up * 2.6 * h
			_look = at + way3 * 0.5 * h
		"top":
			_eye = at + way3 * 3.0 * h + along3 * 3.0 * h + up * 5.0 * h
			_look = at
		"wide":
			# (from the beach and well back, a little up: the whole strip, the peel running across the frame)
			_eye = at + way3 * 6.5 * h + along3 * 0.5 * h + up * 3.2 * h
			_look = at - way3 * 0.4 * h + up * 0.2 * h
		"high":
			# (a drone's view, high over the shoulder looking down along the break)
			_eye = at + along3 * 6.0 * h + way3 * 2.0 * h + up * 6.0 * h
			_look = at - along3 * 1.0 * h
	print("BARREL %s section %d of %d, stage %.2f at t %.2f, height %.2f m, tube %s" % [_site, i, pts.size(), (cr.y - float(site.tb[i])) / Breakers.BREAK_TIME, t, h, at])


func _process(delta: float) -> bool:
	_clock += delta
	if Time.get_ticks_msec() > (300000 if _run else 120000) or _main == null or _main.get_script() == null or (_clock > 1.0 and _main.get(&"player") == null):
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
	if _run:
		return _run_on(site, i, delta)
	if _hold < 0.0 or _settle == 0:
		var sea: Node = _main.get(&"sea")
		_hold = _time_for(site, i, _stages[0], maxf(float(sea.get(&"clock")), 2.0))
		# (the eye stays where the wave is at stage 0.7, so a strip shows one wave going by; the riding
		# views and --follow put it again for each)
		if _follow or _view in RIDING:
			_aim(site, i, _hold)
		elif not _aimed:
			_aim(site, i, _time_for(site, i, 0.7, _hold - 1.0))
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
	var above := _eye.y > Sea.surface_height(_eye.x, _eye.z, _eye.y)
	sea.call(&"set_above", above)
	var post: ShaderMaterial = _main.get(&"_post")
	if post:
		post.set_shader_parameter(&"underwater", 0.0 if above else 1.0)


func _save(stage: float) -> void:
	await RenderingServer.frame_post_draw
	var file := "%s/%s_%s_%.2f.png" % [_dir, _tag, _view, stage]
	root.get_texture().get_image().save_png(file)
	print("BARREL saved %s (eye %s the water: %.2f m, the surface there %.2f)" % [file.get_file(), "above" if _eye.y > Sea.surface_height(_eye.x, _eye.z, _eye.y) else "under", _eye.y, Sea.surface_height(_eye.x, _eye.z, _eye.y)])
	_settle = 0
	_saving = false


# The running clock (--run): a short run-up before the first stage, so what flies is already in the air; then every
# frame is saved until the last stage (or --run-for).
func _run_on(site: Dictionary, i: int, delta: float) -> bool:
	if _hold < 0.0:
		var sea: Node = _main.get(&"sea")
		_run_start = _time_for(site, i, _stages[0], maxf(float(sea.get(&"clock")), 2.0))
		_run_end = _run_start + (_seconds if _seconds > 0.0 else (_stages[_stages.size() - 1] - _stages[0]) * Breakers.BREAK_TIME)
		_aim(site, i, _run_start if _view in RIDING else _time_for(site, i, 0.7, _run_start - 1.0))
		_hold = _run_start - 0.8
		return false
	_hold += delta
	if _view in RIDING or _follow:
		_aim(site, i, _hold)
	_recording = _hold >= _run_start - 0.001
	if _hold > _run_end + 0.001:
		print("BARREL ran %d frames, the clock from %.2f to %.2f" % [_frame, _run_start, _run_end])
		return true
	return false


func _grab() -> void:
	if not _recording:
		return
	_recording = false
	var file := "%s/%s_%s_%03d.png" % [_dir, _tag, _view, _frame]
	root.get_texture().get_image().save_png(file)
	_frame += 1
