extends SceneTree
## Stands a PirateWreck on the sand under the game's water (a Sea, nothing else) and checks and pictures it.
##
##   godot --path . --audio-driver Dummy --resolution 1280x720 -s res://tests/pirate_view.gd -- --out=<dir> [--fog=light]
##   godot --headless --path . --audio-driver Dummy -s res://tests/pirate_view.gd -- --check
##
## Checks (both ways): every swim route's check point is clear of her own rocks and of all the sea's rocks
## (`Sea.clear_of_rocks` leaves it where it is), the most rocks in one of the sea's squares near her, and how long
## `Sea.clear_of_rocks` takes there. Prints PIRATE lines and PIRATE VIEW PASSED or FAILED. With --out it saves
## pictures: both sides, bow-on, stern-on, from above, three-quarters, and from inside each route (the great cabin
## looking out of the stern windows, the gun deck, the hold with the treasure), and close-ups. `--fog=light` thins
## the water's fog for looking at the whole ship (the game's fog hides most of her from 30 m).

const SPOT := Vector2(30.0, 0.0)
const FLOOR := 22.0

var _out := ""
var _fog := "game"
var _check_only := false
var _wreck: Node3D
var _sea: Node3D
var _camera: Camera3D
var _frames := 0
var _shots: Array = []
var _shot := 0
var _failed := false


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--out="):
			_out = arg.substr(6)
		elif arg.begins_with("--fog="):
			_fog = arg.substr(6)
		elif arg == "--check":
			_check_only = true


# (built on the first frame: in _initialize the root is not yet in the tree)
func _setup() -> void:
	if not _check_only:
		DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_NO_FOCUS, true)
	_sea = (load("res://scripts/sea.gd") as GDScript).new()
	root.add_child(_sea)
	# (flat sand, the game's sand as the sea lays it, FLOOR high: 18 m of water over it)
	var old: Node3D = _sea.get(&"sand")
	var flat: Node3D = (load("res://scripts/sand_ground.gd") as GDScript).new()
	for key: StringName in [&"half", &"cell", &"colour", &"ripples", &"solid", &"casts_shadow"]:
		flat.set(key, old.get(key))
	flat.set(&"height", func(_x: float, _z: float) -> float: return FLOOR)
	old.queue_free()
	_sea.add_child(flat)
	_wreck = (load("res://scripts/pirate_wreck.gd") as GDScript).new()
	_wreck.position = Vector3(SPOT.x, FLOOR, SPOT.y)
	root.add_child(_wreck)
	_camera = Camera3D.new()
	_camera.near = 0.05
	_camera.fov = 62.0
	root.add_child(_camera)
	_camera.current = true
	_sea.set(&"eye", _camera)
	_check()
	if _check_only or _out == "":
		_finish()
		return
	if _fog == "light":
		var env: Environment = (_sea.find_children("*", "WorldEnvironment", true, false)[0] as WorldEnvironment).environment
		env.fog_density = 0.012
	DirAccess.make_dir_recursive_absolute(_out)
	var data: Dictionary = (load("res://models/pirate_wreck.json") as JSON).data
	_shots = [
		["port", Vector3(-30.0, 9.0, 2.0), Vector3(0.0, 4.5, 0.0)],
		["starboard", Vector3(31.0, 10.0, -1.0), Vector3(2.0, 4.0, -1.0)],
		["bow", Vector3(-5.0, 7.0, -38.0), Vector3(0.0, 5.0, -5.0)],
		["stern", Vector3(4.0, 8.0, 35.0), Vector3(0.0, 6.0, 5.0)],
		["above", Vector3(3.0, 16.5, 0.5), Vector3(3.0, 0.0, 0.0)],
		["three_quarter", Vector3(24.0, 12.0, 24.0), Vector3(2.0, 4.0, 0.0)],
		["concept_angle", Vector3(26.0, 6.0, -6.0), Vector3(1.0, 5.0, -1.0)],
	]
	for name: String in data.views:
		var v: Array = data.views[name]
		_shots.append(["inside_" + name, Vector3(v[0][0], v[0][1], v[0][2]), Vector3(v[1][0], v[1][1], v[1][2])])


var _started := false


func _process(_delta: float) -> bool:
	if not _started:
		_started = true
		_setup()
		return false
	if _shots.is_empty():
		return false
	_frames += 1
	if _frames == 1:
		var shot: Array = _shots[_shot]
		var from: Vector3 = _wreck.global_transform * (shot[1] as Vector3)
		var to: Vector3 = _wreck.global_transform * (shot[2] as Vector3)
		_camera.fov = 72.0 if String(shot[0]).begins_with("inside") else 50.0
		_camera.global_position = from
		var up := Vector3.UP if absf((to - from).normalized().y) < 0.95 else Vector3.FORWARD
		_camera.look_at(to, up)
	elif _frames == 24:
		var image := root.get_viewport().get_texture().get_image()
		var path := "%s/%02d_%s.png" % [_out, _shot, _shots[_shot][0]]
		image.save_png(path)
		print("PIRATE picture ", path)
		_shot += 1
		_frames = 0
		if _shot >= _shots.size():
			_shots.clear()
			_finish()
	return false


func _check() -> void:
	var blocked: int = _wreck.call(&"routes_blocked")
	var moved := 0
	var points := 0
	for check: Vector4 in _wreck.call(&"route_checks"):
		var p := Vector3(check.x, check.y, check.z)
		points += 1
		if Sea.clear_of_rocks(p, check.w).distance_to(p) > 0.0001:
			moved += 1
	print("PIRATE routes: %d check points, %d blocked by her own rocks, %d moved by Sea.clear_of_rocks" % [points, blocked, moved])
	# the busiest of the sea's squares near her, and what clear_of_rocks costs there
	var most := 0
	var at := _wreck.global_position
	for cx in range(floori((at.x - 30.0) / Sea.CELL), floori((at.x + 30.0) / Sea.CELL) + 1):
		for cz in range(floori((at.z - 30.0) / Sea.CELL), floori((at.z + 30.0) / Sea.CELL) + 1):
			var list: Variant = Sea._cells.get(Vector2i(cx, cz))
			if list != null:
				most = maxi(most, (list as PackedInt32Array).size())
	var rng := RandomNumberGenerator.new()
	rng.seed = 3
	var probe := PackedVector3Array()
	for i in 4000:
		probe.append(at + Vector3(rng.randf_range(-8.0, 12.0), rng.randf_range(0.5, 12.0), rng.randf_range(-22.0, 22.0)))
	var start := Time.get_ticks_usec()
	for p in probe:
		Sea.clear_of_rocks(p, 0.3)
	var each := float(Time.get_ticks_usec() - start) / probe.size()
	print("PIRATE rocks: %d in all; at most %d in one of the sea's %d m squares near her; Sea.clear_of_rocks takes %.1f us there"
			% [Sea.rocks.size(), most, int(Sea.CELL), each])
	print("PIRATE spots: %d fish spots, %d lanterns, treasure at %s" % [(_wreck.call(&"fish_spots") as PackedVector3Array).size(),
			(_wreck.call(&"lanterns") as PackedVector3Array).size(), _wreck.call(&"treasure")])
	var tris := 0
	for drawn: MeshInstance3D in _wreck.find_children("*", "MeshInstance3D", true, false):
		for s in drawn.mesh.get_surface_count():
			tris += (drawn.mesh.surface_get_arrays(s)[Mesh.ARRAY_INDEX] as PackedInt32Array).size() / 3
	var life := 0
	for many: MultiMeshInstance3D in _wreck.find_children("*", "MultiMeshInstance3D", true, false):
		life += many.multimesh.instance_count
	print("PIRATE drawn: %d triangles in her model, %d pieces of sea life on her" % [tris, life])
	# inside-out faces, read back from the imported model: each triangle's winding (Godot's front faces wind
	# clockwise, so a, b, c faces along (c - a) x (b - a)) against its normals, and the volume its faces enclose
	var wound_wrong := 0
	for drawn: MeshInstance3D in _wreck.find_children("*", "MeshInstance3D", true, false):
		var count := 0
		var agree := 0
		var volume := 0.0
		for s in drawn.mesh.get_surface_count():
			var arrays := drawn.mesh.surface_get_arrays(s)
			var at_: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var nm: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
			var ix: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
			for t in range(0, ix.size(), 3):
				var a := at_[ix[t]]
				var b := at_[ix[t + 1]]
				var c := at_[ix[t + 2]]
				var facing := (c - a).cross(b - a)
				if facing.length_squared() < 1e-14:
					continue
				count += 1
				if facing.dot(nm[ix[t]] + nm[ix[t + 1]] + nm[ix[t + 2]]) > 0.0:
					agree += 1
				volume += facing.dot(a + b + c) / 18.0
		var share := 100.0 * agree / maxf(count, 1.0)
		var good := share >= 99.0 and volume > 0.0
		print("PIRATE WINDING %s: %d triangles, winding agrees with normals %.2f%%, volume %.1f: %s" % [drawn.name, count, share, volume, "ok" if good else "BAD"])
		if not good:
			wound_wrong += 1
	_failed = blocked > 0 or moved > 0 or points == 0 or Sea.rocks.is_empty() or wound_wrong > 0


func _finish() -> void:
	print("PIRATE VIEW FAILED" if _failed else "PIRATE VIEW PASSED")
	quit(1 if _failed else 0)
