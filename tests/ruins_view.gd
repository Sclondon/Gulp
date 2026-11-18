extends SceneTree
## Atlantis in the Monterey Canyon (scripts/ruins.gd, tools/RUINS.md), on the game's own floor.
##
## Checks (headless, silent):
##   godot --headless --path . --audio-driver Dummy -s res://tests/ruins_view.gd -- --check
## - Sea.RUINS_AT is the table's origin (data/ruins_layout.json).
## - Every mesh of models/atlantis_canyon.glb wound outwards (the share of triangles whose winding
##   agrees with their normals, and the volume they enclose: tests/winding.gd's test).
## - Every swim route of `Ruins.routes()` open: walked every 0.4 m, each point must come out of
##   `Sea.clear_of_rocks` where it went in, and be at least its room above the floor.
## - Each building sits on the floor: its surface sampled every ~0.5 m, binned in 1 m columns; in each
##   column the lowest stone against `Sea.ground` there. A column whose stone is more than 0.3 m over
##   the floor is floating (the bridge's arch and the temple's jut are meant to: reported, not failed).
## Prints RUINS lines and RUINS CHECK PASSED or FAILED.
##
## Pictures (a real window, silent):
##   godot --path . --audio-driver Dummy --resolution 1280x720 -s res://tests/ruins_view.gd -- --out=<dir> [--only=<name>] [--sides]
## The sea and its scenery as in the game (no post tint): views along the canyon and from inside it;
## with --sides each building from four sides and above, in clearer water.

const STEP := 0.4
## Parts allowed to stand out over the floor (a bridge's arch, a jut over a drop, a lintel over its opening, the rim of
## the hole through her head where it opens just over the floor), and parts not judged.
const OVERHANGS: PackedStringArray = ["Bridge", "Temple", "Gate", "Queen"]
const UNJUDGED: PackedStringArray = ["RuinsGlow"]

var _out := ""
var _only := ""
var _check := false
var _sides := false


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg == "--check":
			_check = true
		elif arg == "--sides":
			_sides = true
		elif arg.begins_with("--out="):
			_out = arg.substr(6)
		elif arg.begins_with("--only="):
			_only = arg.substr(7)
	if _check:
		_run_checks.call_deferred()
	else:
		_take_pictures.call_deferred()


func _run_checks() -> void:
	var bad := 0
	var origin: Vector3 = load("res://scripts/ruins.gd").call(&"origin")
	if origin.distance_to(Sea.RUINS_AT) > 0.01:
		print("RUINS origin: the table's %s is not Sea.RUINS_AT %s" % [origin, Sea.RUINS_AT])
		bad += 1
	var model: Node3D = (load("res://models/atlantis_canyon.glb") as PackedScene).instantiate()
	var triangles := 0
	for part: MeshInstance3D in model.find_children("*", "MeshInstance3D", true, false):
		var counted := _judge(String(part.name), part.mesh)
		if counted < 0:
			bad += 1
		triangles += absi(counted)
	model.free()
	print("RUINS triangles %d" % triangles)
	var ruins: Node3D = load("res://scripts/ruins.gd").new()
	ruins.position = Sea.RUINS_AT
	root.add_child(ruins)
	var rocks: Array = ruins.call(&"rocks")
	print("RUINS collision spheres %d, fish spots %d, lanterns %d" % [rocks.size(), (ruins.call(&"fish_spots") as PackedVector3Array).size(), (ruins.call(&"lanterns") as PackedVector3Array).size()])
	var life := 0
	var life_tris := 0
	for many: MultiMeshInstance3D in ruins.find_children("Life_*", "MultiMeshInstance3D", true, false):
		life += many.multimesh.instance_count
		var mesh := many.multimesh.mesh
		var per := 0
		for s in mesh.get_surface_count():
			per += (mesh.surface_get_arrays(s)[Mesh.ARRAY_INDEX] as PackedInt32Array).size() / 3
		life_tris += per * many.multimesh.instance_count
	print("RUINS sea life: %d pieces, %d triangles" % [life, life_tris])
	bad += _check_routes(ruins)
	bad += _check_footing(ruins)
	print("RUINS CHECK PASSED" if bad == 0 else "RUINS CHECK FAILED (%d)" % bad)
	quit()


func _check_routes(ruins: Node3D) -> int:
	var bad := 0
	var routes: Dictionary = ruins.get_script().call(&"routes")
	for name: String in routes:
		var points: PackedVector3Array = routes[name][0]
		var room: float = routes[name][1]
		var worst := 0.0
		var at_worst := Vector3.ZERO
		var low := INF
		var at_low := Vector3.ZERO
		for i in points.size() - 1:
			var a := ruins.global_transform * points[i]
			var b := ruins.global_transform * points[i + 1]
			var steps := maxi(1, ceili(a.distance_to(b) / STEP))
			for k in steps + 1:
				var p := a.lerp(b, float(k) / steps)
				var moved := Sea.clear_of_rocks(p, room).distance_to(p)
				if moved > worst:
					worst = moved
					at_worst = p
				var over := p.y - Sea.ground(p.x, p.z) - room
				if over < low:
					low = over
					at_low = p
		var ok := worst < 0.001 and low >= 0.0
		if not ok:
			bad += 1
		var why := "open"
		if worst >= 0.001:
			why = "BLOCKED at %s, pushed %.2f m" % [at_worst, worst]
		elif low < 0.0:
			why = "UNDER THE FLOOR at %s by %.2f m" % [at_low, -low]
		print("RUINS route %s (room %.2f): %s" % [name, room, why])
		if worst >= 0.001:
			for rock: Vector4 in Sea.rocks:
				if Vector3(rock.x, rock.y, rock.z).distance_to(at_worst) < rock.w + room:
					print("RUINS   by sphere (%.2f, %.2f, %.2f) r %.2f" % [rock.x, rock.y, rock.z, rock.w])
	return bad


# Each part's lowest stone in each 1 m column against the floor there.
func _check_footing(ruins: Node3D) -> int:
	var bad := 0
	var rng := RandomNumberGenerator.new()
	rng.seed = 5
	for part: MeshInstance3D in ruins.find_children("*", "MeshInstance3D", true, false):
		var name := String(part.name)
		if name in UNJUDGED:
			continue
		var lowest := {}
		var to_world := part.global_transform
		for s in part.mesh.get_surface_count():
			var arrays := part.mesh.surface_get_arrays(s)
			var v: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var index: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
			for t in range(0, index.size(), 3):
				var a := to_world * v[index[t]]
				var b := to_world * v[index[t + 1]]
				var c := to_world * v[index[t + 2]]
				var area := (b - a).cross(c - a).length() * 0.5
				for k in maxi(1, int(area / 0.25)) + 2:
					var u := rng.randf()
					var w := rng.randf()
					if u + w > 1.0:
						u = 1.0 - u
						w = 1.0 - w
					var p := a + (b - a) * u + (c - a) * w
					var key := Vector2i(floori(p.x), floori(p.z))
					if not lowest.has(key) or p.y < float(lowest[key]):
						lowest[key] = p.y
		var gaps := {}
		for key: Vector2i in lowest:
			gaps[key] = float(lowest[key]) - Sea.ground(key.x + 0.5, key.y + 0.5)
		# (a column counts as floating only if every column round it that the part reaches floats too:
		# a cornice, a lip or a capital standing out up to a metre past what carries it is not floating)
		var floating := 0
		var worst := -INF
		var at_worst := Vector2i.ZERO
		var deepest := INF
		for key: Vector2i in gaps:
			var gap: float = gaps[key]
			deepest = minf(deepest, gap)
			if gap <= 0.3:
				continue
			var carried := false
			for dx in range(-1, 2):
				for dz in range(-1, 2):
					var near: Vector2i = key + Vector2i(dx, dz)
					if gaps.has(near) and float(gaps[near]) <= 0.3:
						carried = true
			if carried:
				continue
			floating += 1
			if gap > worst:
				worst = gap
				at_worst = key
		var share := 100.0 * floating / maxf(lowest.size(), 1.0)
		var meant := name in OVERHANGS
		var ok := meant or share <= 1.0
		if not ok:
			bad += 1
		var high := "none floats" if floating == 0 else "the highest %.2f m over the floor at (%d, %d)" % [worst, at_worst.x, at_worst.y]
		print("RUINS footing %s: %d columns, %d floating over 0.3 m (%.1f%%), %s, the deepest %.2f m into it: %s"
				% [name, lowest.size(), floating, share, high, -deepest, "an overhang, as meant" if meant else ("ok" if ok else "FLOATS")])
	return bad


# Winding against normals and the volume enclosed, for one part (all its pieces are closed solids).
# Returns its triangle count, negative if it fails.
func _judge(name: String, mesh: Mesh) -> int:
	var count := 0
	var agree := 0
	var volume := 0.0
	for surface in mesh.get_surface_count():
		var arrays := mesh.surface_get_arrays(surface)
		var points: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
		var index: PackedInt32Array = arrays[Mesh.ARRAY_INDEX] if arrays[Mesh.ARRAY_INDEX] != null else PackedInt32Array()
		var corners := index.size() if not index.is_empty() else points.size()
		for t in range(0, corners, 3):
			var ia := index[t] if not index.is_empty() else t
			var ib := index[t + 1] if not index.is_empty() else t + 1
			var ic := index[t + 2] if not index.is_empty() else t + 2
			var a := points[ia]
			var b := points[ib]
			var c := points[ic]
			var facing := (c - a).cross(b - a)
			if facing.length() * 0.5 < 0.0005:
				continue
			count += 1
			if facing.dot(normals[ia] + normals[ib] + normals[ic]) > 0.0:
				agree += 1
			elif OS.get_cmdline_user_args().has("--why"):
				print("RUINS   against its normals: %s at %s, area %.4f" % [name, (a + b + c) / 3.0, facing.length() * 0.5])
			volume += facing.dot(a + b + c) / 18.0
	var share := 100.0 * agree / maxf(count, 1.0)
	var good := share >= 99.0 and volume > 0.0
	print("RUINS winding %s: %d triangles, winding agrees with normals %.1f%%, volume %.1f m3: %s" % [name, count, share, volume, "ok" if good else "BAD"])
	return count if good else -count


func _take_pictures() -> void:
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_NO_FOCUS, true)
	if _out == "":
		_out = "user://ruins_shots"
	DirAccess.make_dir_recursive_absolute(_out)
	var sea: Node3D = load("res://scripts/sea.gd").new()
	root.add_child(sea)
	var scenery: Node3D = load("res://scripts/scenery.gd").new()
	root.add_child(scenery)
	var env: Environment = (sea.find_children("*", "WorldEnvironment", true, false)[0] as WorldEnvironment).environment
	var camera := Camera3D.new()
	camera.fov = 62.0
	camera.far = 400.0
	root.add_child(camera)
	camera.current = true
	sea.set(&"eye", camera)
	for f in 4:
		await process_frame
	var ruins: Node3D = null
	for child in scenery.get_children():
		if child.get_script() and (child.get_script() as Script).resource_path.ends_with("ruins.gd"):
			ruins = child
	if ruins == null:
		print("RUINS no ruins in the scenery")
		quit()
		return
	var R: Script = ruins.get_script()
	var at := func(local: Vector3) -> Vector3: return ruins.global_transform * local
	var game_fog := env.fog_density
	# name, from, looking at (the ruins' own space), fog (0: the game's; else its density)
	var shots := []
	if _sides:
		for name: String in (R.call(&"layout") as Dictionary).buildings:
			var f: Transform3D = R.call(&"frame", name)
			var size := 16.0 if name in ["Temple", "Pyramid", "Colonnade", "Bridge"] else 11.0
			var middle := f * Vector3(0.0, 4.0, 0.0)
			for k in 4:
				var a := f.basis.get_euler().y + TAU * k / 4.0
				shots.append(["%s_%d" % [name.to_lower(), k], middle + Vector3(sin(a) * size, size * 0.3, cos(a) * size), middle, 0.012])
			shots.append(["%s_top" % name.to_lower(), middle + Vector3(0.5, size * 1.4, 0.5), middle, 0.012])
	else:
		# (each given in the world as x, depth, z: easier to read against data/ruins_layout.json)
		var w := func(x: float, depth: float, z: float) -> Vector3: return Vector3(x, Sea.SURFACE - depth, z) - (R.call(&"origin") as Vector3)
		shots = [
			["concept_view", w.call(-94.0, 80.0, 66.0), w.call(-62.0, 52.0, 42.0), 0.0],
			["concept_view_east", w.call(-88.0, 70.0, 64.0), w.call(-50.0, 58.0, 48.0), 0.0],
			["concept_view_north", w.call(-60.0, 60.0, 66.0), w.call(-72.0, 40.0, 36.0), 0.0],
			["concept_view_high", w.call(-100.0, 60.0, 66.0), w.call(-55.0, 55.0, 40.0), 0.0],
			["temple_jut", w.call(-80.0, 50.0, 50.0), w.call(-80.0, 28.0, 30.0), 0.0],
			["north_wall", w.call(-70.0, 70.0, 64.0), w.call(-75.0, 45.0, 40.0), 0.0],
			["plan_clear", w.call(-62.0, 5.0, 50.0), w.call(-62.0, 90.0, 50.5), 0.003],
			["bridge_under", w.call(-48.0, 50.0, 40.0), w.call(-48.0, 44.0, 30.0), 0.0],
			["pyramid", w.call(-74.0, 64.0, 58.0), w.call(-52.0, 63.0, 57.5), 0.0],
			["queen", w.call(-92.0, 88.0, 59.0), w.call(-85.0, 95.0, 66.0), 0.0],
			["landing_pillar", w.call(-46.0, 36.0, 40.0), w.call(-34.0, 30.0, 30.0), 0.0],
			["along_from_east", w.call(-36.0, 45.0, 44.0), w.call(-75.0, 70.0, 56.0), 0.0],
			["from_floor_up", w.call(-80.0, 92.0, 66.0), w.call(-70.0, 50.0, 40.0), 0.0],
			["stair_east", w.call(-52.0, 52.0, 42.0), w.call(-40.0, 45.0, 47.0), 0.0],
			["facade_south", w.call(-68.0, 70.0, 55.0), w.call(-68.0, 66.0, 69.5), 0.0],
			["gate", w.call(-64.0, 22.0, 6.0), w.call(-64.0, 24.0, 23.0), 0.0],
		]
	for shot: Array in shots:
		if _only != "" and not String(shot[0]).contains(_only):
			continue
		var fog: float = shot[3]
		env.fog_density = game_fog if fog == 0.0 else fog
		var from: Vector3 = shot[1] if _sides else at.call(shot[1])
		var to: Vector3 = shot[2] if _sides else at.call(shot[2])
		if _sides:
			from = ruins.global_transform * from
			to = ruins.global_transform * to
		camera.look_at_from_position(from, to, Vector3.UP if absf((to - from).normalized().y) < 0.99 else Vector3.FORWARD)
		sea.call(&"set_above", from.y > Sea.SURFACE)
		for f in 8:
			await process_frame
		await RenderingServer.frame_post_draw
		root.get_texture().get_image().save_png(_out.path_join("%s.png" % shot[0]))
		print("RUINS shot ", shot[0])
	quit()
