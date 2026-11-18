extends SceneTree
## Pictures of the caustics in the game itself (Main, its half-size picture and post shader), at chosen
## places and with chosen looks, to check that the net falls on fish, rocks, plants and wrecks
## (scripts/caustics.gd). No depth limit.
##   godot --path . --audio-driver Dummy --resolution 390x844 -s res://tests/caustics_view.gd -- --hour=12 --out=<folder> [--no-caustics] [--only=<name>]

var _out := "user://"
var _only := ""
var _main: Node
var _shots: Array = []
var _at := -1
var _wait := 0.0


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--out="):
			_out = arg.get_slice("=", 1)
		elif arg.begins_with("--only="):
			_only = arg.get_slice("=", 1)
	_main = load("res://main.tscn").instantiate()
	root.add_child(_main)
	# [name, the point looked at (x, z; y is the floor's + the third), from (offset), or a kind to look at]
	var docks: Vector2 = Sea.ZONES.docks.at
	var kelp: Vector2 = Sea.ZONES.kelp.at
	var crags: Vector2 = Sea.ZONES.crags.at
	_shots = [
		["docks", Vector3(docks.x, 1.0, docks.y), Vector3(0.0, 4.0, 7.0)],
		["kelp", Vector3(kelp.x, 1.5, kelp.y), Vector3(0.0, 5.0, 7.0)],
		["crags", Vector3(crags.x, 1.5, crags.y), Vector3(0.0, 5.0, 8.0)],
		["pirate", Sea.PIRATE_AT + Vector3(0.0, 3.0, 0.0), Vector3(0.0, 9.0, 16.0)],
		["reef", Sea.WRECK_AT + Vector3(0.0, 8.0, 0.0), Vector3(0.0, 9.0, 18.0)],
		["fish", "sand", 0.0],
		["fish2", "grass", 0.0],
		["fish3", "reef", 0.0],
	]
	if _only != "":
		_shots = _shots.filter(func(s: Array) -> bool: return String(s[0]).contains(_only))


func _process(delta: float) -> bool:
	if _main == null or not _main.is_node_ready():
		return false
	_wait -= delta
	if _wait > 0.0:
		_hold()
		return false
	if _at >= 0:
		var path := _out.path_join("cv_%s.png" % _shots[_at][0])
		root.get_texture().get_image().save_png(path)
		print("CAUSTICS VIEW ", path)
	_at += 1
	if _at >= _shots.size():
		quit()
		return true
	_main.set(&"limited", false)
	_place(_shots[_at])
	_wait = 5.0 if _at == 0 else 2.5
	return false


var _from := Vector3.ZERO
var _look := Vector3.ZERO
var _target: Node3D
var _offset := Vector3.ZERO


func _place(shot: Array) -> void:
	_target = null
	if shot[1] is String:
		# (the largest animal awake near a zone, seen from above and behind)
		var zone: Vector2 = Sea.ZONES[shot[1]].at
		var player: Node3D = _main.get(&"player")
		player.global_position = Vector3(zone.x, Sea.ground(zone.x, zone.y) + 4.0, zone.y)
		var life: Node = _main.get(&"life")
		var best: Node3D = null
		for each: Node3D in life.get(&"creatures"):
			var d := Vector2(each.global_position.x - zone.x, each.global_position.z - zone.y).length()
			if d < 40.0 and (best == null or float(each.get(&"length")) > float(best.get(&"length"))) and float(each.get(&"length")) < 4.0:
				best = each
		if best:
			_look = best.global_position
			_from = _look + Vector3(0.0, 2.0, 1.6) * maxf(float(best.get(&"length")), 0.8)
			_target = best
			_offset = _from - _look
			print("CAUSTICS VIEW looks at a ", best.get(&"kind"))
		return
	var p: Vector3 = shot[1]
	_look = Vector3(p.x, Sea.ground(p.x, p.z) + p.y, p.z) if p.y < 5.0 and shot[0] != "pirate" and shot[0] != "reef" else p
	_from = _look + (shot[2] as Vector3)
	_hold()


## (the fish is put back each frame, facing what is looked at, so it does not swim off)
func _hold() -> void:
	var player: Node3D = _main.get(&"player")
	if player == null:
		return
	if is_instance_valid(_target):
		_look = _target.global_position
		_from = _look + _offset
	var heading := (_look - _from).normalized()
	player.global_position = _from
	player.set(&"heading", heading)
	player.set(&"yaw", atan2(-heading.x, -heading.z))
	player.set(&"pitch", asin(clampf(heading.y, -1.0, 1.0)))
