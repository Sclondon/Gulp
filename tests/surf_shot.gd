extends SceneTree
## Pictures of the surf and the rogue wave from a fixed eye (tools/WATER_FX.md, "Surf and rogue
## waves"). Runs the game (main.tscn) with the arguments after --, holds the eye where asked each
## frame after the game has placed it, and saves a picture at each of the times given:
##
##   godot --path . --audio-driver Dummy --resolution 390x844 -s res://tests/surf_shot.gd
##       -- --offline --hour=17 --times=3,4.5 --dir=<folder> [--tag=name]
##       [--shore=x,z] [--out=metres] [--up=metres] [--along]   (the eye out to sea from the shore near x,z)
##       [--eye=x,y,z --look=x,y,z]                             (or exactly)
##       [--rogue=metres ahead,age] [--across]                  (a rogue wave crossing the view, that old)
##
## --shore finds the nearest water 6 m from a shore near x, z and puts the eye `out` metres (22) out to
## sea from it, `up` metres (2) over the still surface, looking at the shore (--along: looking along it).
## --rogue sends one straight at the eye, at its highest that many metres ahead of it, and sets
## its age (s; its highest is at half its life, Surf.ROGUE_LIFE / 2). Prints a SURF line for each picture.

var _main: Node
var _times: Array[float] = []
var _dir := ""
var _tag := "surf"
var _clock := 0.0
var _saving := false
var _eye := Vector3.INF
var _look := Vector3.INF
var _shore := Vector2.INF
var _out := 22.0
var _up := 2.0
var _along := false
var _rogue := Vector2.INF
var _rogue_set := false


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		var v := arg.get_slice("=", 1)
		if arg.begins_with("--times="):
			for t in v.split(","):
				_times.append(float(t))
		elif arg.begins_with("--dir="):
			_dir = v
		elif arg.begins_with("--tag="):
			_tag = v
		elif arg.begins_with("--eye="):
			_eye = _vec3(v)
		elif arg.begins_with("--look="):
			_look = _vec3(v)
		elif arg.begins_with("--shore="):
			var p := v.split(",")
			_shore = Vector2(float(p[0]), float(p[1]))
		elif arg.begins_with("--out="):
			_out = float(v)
		elif arg.begins_with("--up="):
			_up = float(v)
		elif arg == "--along":
			_along = true
		elif arg.begins_with("--rogue="):
			var p := v.split(",")
			_rogue = Vector2(float(p[0]), float(p[1]))
	DirAccess.make_dir_recursive_absolute(_dir)
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_NO_FOCUS, true)
	if _shore != Vector2.INF:
		_find_shore()
	_main = (load("res://main.tscn") as PackedScene).instantiate()
	root.add_child(_main)
	RenderingServer.frame_pre_draw.connect(_place_eye)


func _vec3(text: String) -> Vector3:
	var p := text.split(",")
	return Vector3(float(p[0]), float(p[1]), float(p[2]))


# The eye out to sea from a point 6 m off the shore nearest to `_shore`.
func _find_shore() -> void:
	Sea.ground(0.0, 0.0)
	var best := Vector2.INF
	var best_off := INF
	for i in range(-30, 31):
		for j in range(-30, 31):
			var p := _shore + Vector2(i, j) * 1.5
			var d := Bay.shore_distance(p)
			var off := absf(d - 6.0) + p.distance_to(_shore) * 0.05
			if off < best_off and Surf.shoreward(p.x, p.y) != Vector2.ZERO:
				best_off = off
				best = p
	var way := Surf.shoreward(best.x, best.y)
	var from := best - way * _out
	if _along:
		from = best - way * _out * 0.4 + Vector2(-way.y, way.x) * _out
	_eye = Vector3(from.x, Sea.SURFACE + _up, from.y)
	_look = Vector3(best.x + way.x * 4.0, Sea.SURFACE + 0.2, best.y + way.y * 4.0)
	print("SURF shore point %s, shore distance %.1f, depth %.1f, way %s" % [best, Bay.shore_distance(best), Sea.SURFACE - Sea.ground(best.x, best.y), way])


func _process(delta: float) -> bool:
	_clock += delta
	if Time.get_ticks_msec() > 90000 or _main == null or _main.get_script() == null or (_clock > 1.0 and _main.get(&"player") == null):
		print("SURF GAVE UP (the game did not start, or took too long)")
		return true
	if _rogue != Vector2.INF and not _rogue_set and _clock > 0.2 and _eye != Vector3.INF:
		_rogue_set = true
		var sight := Vector2(_look.x - _eye.x, _look.z - _eye.z).normalized()
		var over := Vector2(_eye.x, _eye.z) + sight * _rogue.x
		# (coming straight at the eye, its crest across the view; with --across, passing across the view
		# from left to right, so its curl is seen from the side)
		var heading := Vector2(sight.y, -sight.x) if OS.get_cmdline_user_args().has("--across") else -sight
		Sea.rogue_wave(over, heading, true)
		if OS.get_cmdline_user_args().has("--across"):
			# (its crest right across the eye's sight at the age given, not at its highest)
			Surf.start_rogue(over - heading * Surf.ROGUE_SPEED * (_rogue.y + 0.8), heading)
		Surf.rogue_age = _rogue.y
	# (no static from the depth limit: the eye is not the fish's)
	_main.set(&"limited", false)
	if not _saving and not _times.is_empty() and _clock >= _times[0]:
		_saving = true
		_save(_times.pop_front())
	return _times.is_empty() and not _saving


func _place_eye() -> void:
	if _main == null or not is_instance_valid(_main) or _eye == Vector3.INF:
		return
	var cam: Camera3D = _main.get(&"camera")
	if cam == null:
		return
	# (the water only: no panel over it)
	for each in [&"pad", &"hud"]:
		var node: CanvasItem = _main.get(each)
		if node:
			node.visible = false
	cam.global_position = _eye
	cam.look_at(_look, Vector3.UP)
	cam.force_update_transform()
	var sea: Node = _main.get(&"sea")
	var post: ShaderMaterial = _main.get(&"_post")
	if sea and OS.get_cmdline_user_args().has("--debug"):
		(sea.get(&"_water") as ShaderMaterial).set_shader_parameter(&"surf_debug", 3 if OS.get_cmdline_user_args().has("--debug3") else (2 if OS.get_cmdline_user_args().has("--debug2") else 1))
	if sea:
		var above := _eye.y > Sea.surface_height(_eye.x, _eye.z)
		sea.call(&"set_above", above)
		if post:
			post.set_shader_parameter(&"underwater", 0.0 if above else 1.0)


func _save(at: float) -> void:
	await RenderingServer.frame_post_draw
	var file := "%s/%s_%05.2f.png" % [_dir, _tag, at]
	root.get_texture().get_image().save_png(file)
	print("SURF %s eye %s, surface there %.2f, rogue %s age %.1f" % [file.get_file(), _eye, Sea.surface_height(_eye.x, _eye.z), Surf.rogue_on, Surf.rogue_age])
	_saving = false
