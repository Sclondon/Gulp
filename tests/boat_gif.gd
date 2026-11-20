extends SceneTree
## Frames of driving the shrimp boat, from the game's own camera, for a GIF (CLAUDE.md, "Decision:
## driving the shrimp boat"). Runs main.tscn with --helm (the title started, at the helm), puts the boat
## where the move starts, drives the panel's stick, lever and burst as fingers would, and saves every
## frame as a PNG; also prints one BOAT line a frame (speed, depth under it, its heel and pitch, the
## camera's height and roll).
##
##   godot --path . --audio-driver Dummy --fixed-fps 30 --resolution 390x844 -s res://tests/boat_gif.gd
##       -- --helm --offline --move=turn|swell|surf|shore|drop --dir=<folder>
##
## Moves: turn (an S-turn in open water), swell (flat out with the burst across the swell to the west),
## surf (in towards the break off Steamer Lane), shore (flat out at the Santa Cruz beach: pushed back),
## drop (a little way under way, then the dive switch is tapped and the eye goes down to the fish).
## Then: ffmpeg -framerate 30 -i <dir>/f_%04d.png <gif>.

const SECONDS := {"turn": 9.0, "swell": 7.0, "surf": 8.0, "shore": 9.0, "drop": 5.0}
## Where each move starts (x, z) and its heading (radians round from north towards west).
const STARTS := {
	"turn": [Vector2(-40.0, -55.0), 0.0],
	"swell": [Vector2(-60.0, -20.0), PI * 0.5],
	"surf": [Vector2(-40.0, -90.0), 0.0],
	"shore": [Vector2(-25.0, -95.0), 0.0],
	"drop": [Vector2(-30.0, -40.0), -0.6],
}

var _main: Node
var _move := "turn"
var _dir := ""
var _clock := 0.0
var _frame := 0
var _placed := -1.0
var _dropped := false


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--move="):
			_move = arg.get_slice("=", 1)
		elif arg.begins_with("--dir="):
			_dir = arg.get_slice("=", 1)
	if _dir != "":
		DirAccess.make_dir_recursive_absolute(_dir)
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_NO_FOCUS, true)
	_main = (load("res://main.tscn") as PackedScene).instantiate()
	root.add_child(_main)


func _process(delta: float) -> bool:
	_clock += delta
	if Time.get_ticks_msec() > 240000 or _main == null or _main.get_script() == null:
		print("BOAT GIF GAVE UP")
		return true
	if not _main.get(&"_at_helm") and _placed < 0.0:
		return false
	var title: Node3D = _main.get(&"title")
	var pad: Node = _main.get(&"pad")
	if _placed < 0.0:
		_placed = _clock
		var start: Array = STARTS.get(_move, STARTS["turn"])
		title.call(&"place", start[0], start[1])
		title.set(&"velocity", -title.global_basis.z * 4.0)
		print("BOAT GIF placed after %.1f s" % _clock)
		return false
	var t := _clock - _placed
	_drive(t, pad)
	if t > SECONDS.get(_move, 6.0):
		print("BOAT GIF DONE %s %d frames" % [_move, _frame])
		return true
	_save.call_deferred(title)
	return false


func _drive(t: float, pad: Node) -> void:
	var stick := Vector2.ZERO
	var boost := false
	var lever := 1.0
	match _move:
		"turn":
			stick = Vector2(1.0 if t < 4.0 else (-1.0 if t < 8.0 else 0.0), 0.0)
		"swell":
			boost = t > 1.0 and t < 3.0
			stick = Vector2(0.3 * sin(t * 0.8), 0.0)
		"surf":
			lever = 0.8
			stick = Vector2(0.25 * sin(t * 0.6), 0.0)
		"shore":
			boost = t < 2.0 or (t > 5.0 and t < 7.0)
		"drop":
			lever = 0.6
			stick = Vector2(0.4, 0.0) if t < 1.5 else Vector2.ZERO
			if t > 1.8 and not _dropped:
				_dropped = true
				# (a finger on the dive switch, as a phone's would land)
				var at: Vector2 = root.get_final_transform() * (pad.call(&"dive_home") as Vector2)
				for down in [true, false]:
					var touch := InputEventScreenTouch.new()
					touch.index = 3
					touch.position = at
					touch.pressed = down
					Input.parse_input_event(touch)
				print("BOAT GIF tapped the dive switch at %s" % at)
	pad.set(&"stick", stick)
	pad.set(&"boost", boost)
	pad.set(&"throttle", lever)


func _save(title: Node3D) -> void:
	await RenderingServer.frame_post_draw
	if _dir != "":
		root.get_texture().get_image().save_png("%s/f_%04d.png" % [_dir, _frame])
	var eye: Camera3D = _main.get(&"camera")
	var at := title.global_position
	var boat: Node3D = title.get(&"boat")
	var rot := eye.global_basis.get_euler()
	print("BOAT %d t %.2f at %.1f,%.1f speed %.2f depth %.1f water %.2f heel %.1f pitch %.1f eye_y %.2f eye_roll %.2f eye_pitch %.1f bow_depth %.1f rock %.2f" % [
		_frame, _clock - _placed, at.x, at.z, (title.get(&"velocity") as Vector3).length(), Sea.SURFACE - Sea.ground(at.x, at.z),
		Sea.surface_height(at.x, at.z) - Sea.SURFACE, rad_to_deg(boat.rotation.z), rad_to_deg(boat.rotation.x),
		eye.global_position.y - Sea.SURFACE, rad_to_deg(rot.z), rad_to_deg(rot.x), Sea.SURFACE - Sea.ground(at.x - title.global_basis.z.x * 5.0, at.z - title.global_basis.z.z * 5.0),
		Sea.clear_of_rocks(Vector3(at.x, Sea.SURFACE - 1.0, at.z), 4.0).distance_to(Vector3(at.x, Sea.SURFACE - 1.0, at.z))])
	_frame += 1
