extends SceneTree
## Frames of a move at the surface, from the game's own camera, for a GIF (CLAUDE.md, "Decision: the
## camera at the surface"). Runs main.tscn, puts the fish where the move starts, drives the panel's
## stick, burst and lever as fingers would, and saves every frame as a PNG; also prints one EYE line a
## frame (eye and fish height, the water there, above or under, the eye's roll and pitch).
##
##   godot --path . --audio-driver Dummy --fixed-fps 30 --resolution 390x844 -s res://tests/surface_gif.gd
##       -- --offline --calm --move=cruise|break|leap|surf_leap|surf_cruise [--as=sardine] --dir=<folder>
##
## Moves: cruise (just under the top, turning), break (rising slowly into the top at a low lever),
## leap (a burst up through calm water), surf_leap / surf_cruise (the same in the swell off Steamer Lane).
## Then: ffmpeg -framerate 30 -i <dir>/f_%04d.png <gif>. --probe prints the water off Steamer Lane.

const SECONDS := {"cruise": 5.0, "break": 5.0, "leap": 4.5, "surf_leap": 4.5, "surf_cruise": 5.0}
## Off Steamer Lane, seaward of the break (scripts/breakers.gd), where the swell runs in.
const SURF_AT := Vector2(-40.0, -108.0)
## Open water by the start, clear of the boat that lies hove-to over it (Main: the start plus 4 m in z).
static var CALM_AT: Vector2 = Sea.START + Vector2(0.0, -16.0)

var _main: Node
var _move := "leap"
var _dir := ""
var _clock := 0.0
var _frame := 0
var _placed := false
var _probe := false
var _debug := 0


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--move="):
			_move = arg.get_slice("=", 1)
		elif arg.begins_with("--dir="):
			_dir = arg.get_slice("=", 1)
		elif arg == "--probe":
			_probe = true
		elif arg.begins_with("--debug="):
			_debug = int(arg.get_slice("=", 1))
	if _dir != "":
		DirAccess.make_dir_recursive_absolute(_dir)
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_NO_FOCUS, true)
	_main = (load("res://main.tscn") as PackedScene).instantiate()
	root.add_child(_main)


func _process(delta: float) -> bool:
	_clock += delta
	if Time.get_ticks_msec() > 120000 or _main == null or _main.get_script() == null or (_clock > 1.0 and _main.get(&"player") == null):
		print("SURFACE GIF GAVE UP")
		return true
	var player: Node3D = _main.get(&"player")
	var pad: Node = _main.get(&"pad")
	if player == null or pad == null:
		return false
	if _probe:
		if _clock > 0.5:
			for dz in range(0, 36, 3):
				var p := Vector2(SURF_AT.x, -126.0 + dz) if dz < 33 else CALM_AT
				print("PROBE z %.0f depth %.1f water %.2f" % [p.y, Sea.SURFACE - Sea.ground(p.x, p.y), Sea.surface_height(p.x, p.y) - Sea.SURFACE])
			return true
		return false
	var t := _clock - 0.4
	if t < 0.0:
		return false
	if not _placed:
		_placed = true
		if _debug > 0:
			((_main.get(&"sea") as Node).get(&"_water") as ShaderMaterial).set_shader_parameter(&"surf_debug", _debug)
		_place(player)
	_drive(t, pad)
	if t > SECONDS.get(_move, 4.0):
		print("SURFACE GIF DONE %s %d frames" % [_move, _frame])
		return true
	_save.call_deferred(player)
	return false


func _place(player: Node3D) -> void:
	var at := CALM_AT
	if _move.begins_with("surf"):
		at = SURF_AT
	var deep := 0.45 if _move.ends_with("cruise") else (2.2 if _move == "break" else 1.6)
	player.global_position = Vector3(at.x, Sea.surface_height(at.x, at.y) - deep, at.y)
	# (heading out along the coast, the swell coming from the side)
	player.set(&"yaw", -PI * 0.5)
	player.set(&"pitch", 0.0 if _move.ends_with("cruise") else (0.35 if _move == "break" else 0.75))
	player.set(&"safe", 0.0)
	player.set(&"heading", Vector3(1, 0, 0))
	var eye: Camera3D = _main.get(&"camera")
	eye.global_position = player.global_position - Vector3(1, 0, 0) * 0.8 + Vector3.UP * 0.2


func _drive(t: float, pad: Node) -> void:
	var stick := Vector2.ZERO
	var boost := false
	var lever := 0.7
	match _move:
		"cruise", "surf_cruise":
			# (along the top, nudging up to stay there, a turn one way then the other)
			stick = Vector2(0.6 * sin(t * 1.4), 0.25)
		"break":
			lever = 0.0
			stick = Vector2(0.0, 0.2)
		"leap", "surf_leap":
			boost = t < 1.2
			stick = Vector2(0.0, 0.6 if t < 0.5 else 0.0)
	pad.set(&"stick", stick)
	pad.set(&"boost", boost)
	pad.set(&"throttle", lever)


func _save(player: Node3D) -> void:
	await RenderingServer.frame_post_draw
	var eye: Camera3D = _main.get(&"camera")
	var sea: Node = _main.get(&"sea")
	if _dir != "":
		root.get_texture().get_image().save_png("%s/f_%04d.png" % [_dir, _frame])
	var e := eye.global_position
	var p := player.global_position
	var rot := eye.global_basis.get_euler()
	print("EYE %d t %.2f eye %.2f water@eye %.2f above %s fish %.2f water@fish %.2f air %s pitch %.1f roll %.1f" % [
		_frame, _clock - 0.4, e.y - Sea.SURFACE, Sea.surface_height(e.x, e.z, e.y) - Sea.SURFACE, sea.get(&"above"),
		p.y - Sea.SURFACE, Sea.surface_height(p.x, p.z) - Sea.SURFACE, player.get(&"in_air"), rad_to_deg(rot.x), rad_to_deg(rot.z)])
	_frame += 1
