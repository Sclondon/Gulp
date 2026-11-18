extends SceneTree
## A strip of pictures from the game's own camera, for checking the water's effects
## (tools/WATER_FX.md). Runs the game (main.tscn) with the arguments after --, and saves a picture
## at each of the times given:
##
##   godot --path . --audio-driver Dummy --fixed-fps 60 --resolution 1280x720 -s res://tests/fx_strip.gd
##       -- --offline --leap --as=salmon --times=0.6,0.9,1.2 --dir=<folder> [--tag=name] [--burst]
##       [--hour=<0..24>] [--side] [--hold-up] [--burst=<from seconds>]
##
## --burst holds the burst button from the start; --hold-up holds the stick up; --side moves the
## camera out to the fish's side (each frame, after the game has placed it).
## Prints a STRIP line for each picture: where the eye and the fish are, and whether it is in the air.

var _main: Node
var _times: Array[float] = []
var _dir := ""
var _tag := "strip"
var _clock := 0.0
var _burst := false
var _burst_from := 0.0
var _up := false
var _side := false
var _floor := false
var _saving := false


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--times="):
			for t in arg.get_slice("=", 1).split(","):
				_times.append(float(t))
		elif arg.begins_with("--dir="):
			_dir = arg.get_slice("=", 1)
		elif arg.begins_with("--tag="):
			_tag = arg.get_slice("=", 1)
		elif arg == "--burst":
			_burst = true
		elif arg.begins_with("--burst="):
			_burst = true
			_burst_from = float(arg.get_slice("=", 1))
		elif arg == "--hold-up":
			_up = true
		elif arg == "--side":
			_side = true
		elif arg == "--floor":
			_floor = true
	DirAccess.make_dir_recursive_absolute(_dir)
	# (the user's keys and pad must not reach it)
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_NO_FOCUS, true)
	_main = (load("res://main.tscn") as PackedScene).instantiate()
	root.add_child(_main)
	# (the eye is moved after the game has placed it, just before the frame is drawn)
	RenderingServer.frame_pre_draw.connect(_place_eye)


func _process(delta: float) -> bool:
	_clock += delta
	# (never left running: a script error at start, from a half-made edit, stops it saving anything)
	if Time.get_ticks_msec() > 60000 or _main == null or _main.get_script() == null or (_clock > 1.0 and _main.get(&"player") == null):
		print("STRIP GAVE UP (the game did not start, or took too long)")
		return true
	var player: Node = _main.get(&"player")
	var pad: Node = _main.get(&"pad")
	if pad:
		# (as fingers on the panel would: main reads the pad each frame)
		if _burst:
			pad.set(&"boost", _clock >= _burst_from)
		if _up:
			pad.set(&"stick", Vector2(0.0, 1.0))
	if not _saving and not _times.is_empty() and _clock >= _times[0]:
		_saving = true
		_save(_times.pop_front())
	if _times.is_empty() and not _saving:
		return true
	return false



func _place_eye() -> void:
	if _main == null or not is_instance_valid(_main):
		return
	var player: Node = _main.get(&"player")
	if player and _floor:
		# (the eye a few metres over the floor beside the fish, looking down at the sea bed ahead)
		var eye: Camera3D = _main.get(&"camera")
		var q: Vector3 = player.global_position
		var g := Sea.ground(q.x, q.z)
		eye.global_position = Vector3(q.x, minf(g + 4.0, Sea.SURFACE - 0.6), q.z)
		eye.look_at(Vector3(q.x + 4.0, g, q.z + 1.0), Vector3.UP)
		eye.force_update_transform()
		if Engine.get_process_frames() % 30 == 0:
			print("FLOOR ground %.1f eye %s depth %.1f" % [g, eye.global_position, Sea.SURFACE - g])
	elif player:
		if _side:
			var cam: Camera3D = _main.get(&"camera")
			var p: Vector3 = player.global_position
			var h: Vector3 = player.get(&"heading")
			var flat := Vector3(h.x, 0.0, h.z).normalized()
			var long: float = player.get(&"length")
			cam.global_position = p + flat.cross(Vector3.UP) * (1.0 + long * 2.5) + Vector3.UP * 0.2
			cam.look_at(p, Vector3.UP)
			cam.force_update_transform()


func _save(at: float) -> void:
	await RenderingServer.frame_post_draw
	var file := "%s/%s_%05.2f.png" % [_dir, _tag, at]
	root.get_texture().get_image().save_png(file)
	var player: Node = _main.get(&"player")
	var cam: Camera3D = _main.get(&"camera")
	print("STRIP %s eye y %.2f, fish y %.2f, in air %s, speed %.2f, length %.2f" % [file.get_file(), cam.global_position.y, player.global_position.y, player.get(&"in_air"), (player.get(&"velocity") as Vector3).length(), player.get(&"length")])
	_saving = false
