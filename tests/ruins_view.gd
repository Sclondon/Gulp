extends SceneTree
## The Atlantis ruins (scripts/ruins.gd) stood on a flat sand floor 40 m under the game's water.
##
## Checks (headless, silent):
##   godot --headless --path . --audio-driver Dummy -s res://tests/ruins_view.gd -- --check
## Every mesh of models/atlantis_ruins.glb wound outwards (the share of triangles whose winding agrees
## with their normals, and the volume they enclose: tests/winding.gd's test), and every swim route of
## `Ruins.routes()` open: walked every 0.4 m, each point must come out of `Sea.clear_of_rocks` where it
## went in. Prints RUINS lines and RUINS CHECK PASSED or FAILED.
##
## Pictures (a real window, silent):
##   godot --path . --audio-driver Dummy --resolution 1280x720 -s res://tests/ruins_view.gd -- --out=<dir> [--only=<name>]
## The approach, the plan from above, each building from two sides, and from inside each swim route,
## in the game's water (and a few in clearer water, to judge the model).

const STEP := 0.4

var _out := ""
var _only := ""
var _check := false
var _ruins: Node3D
var _sea: Node3D
var _camera: Camera3D
var _env: Environment


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg == "--check":
			_check = true
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
	var model: Node3D = (load("res://models/atlantis_ruins.glb") as PackedScene).instantiate()
	var triangles := 0
	for part: MeshInstance3D in model.find_children("*", "MeshInstance3D", true, false):
		var counted := _judge(String(part.name), part.mesh)
		if counted < 0:
			bad += 1
		triangles += absi(counted)
	model.free()
	print("RUINS triangles %d" % triangles)
	var ruins: Node3D = load("res://scripts/ruins.gd").new()
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
	var routes: Dictionary = ruins.get_script().call(&"routes")
	for name: String in routes:
		var points: PackedVector3Array = routes[name][0]
		var room: float = routes[name][1]
		var worst := 0.0
		var at_worst := Vector3.ZERO
		for i in points.size() - 1:
			var a := points[i]
			var b := points[i + 1]
			var steps := maxi(1, ceili(a.distance_to(b) / STEP))
			for k in steps + 1:
				var p := a.lerp(b, float(k) / steps)
				var pushed := Sea.clear_of_rocks(p, room)
				var moved := pushed.distance_to(p)
				if moved > worst:
					worst = moved
					at_worst = p
		var ok := worst < 0.001
		if not ok:
			bad += 1
		print("RUINS route %s (room %.2f): %s" % [name, room, "open" if ok else "BLOCKED at %s, pushed %.2f m" % [at_worst, worst]])
		if not ok:
			# (which spheres: in the world, centre and radius)
			for rock: Vector4 in Sea.rocks:
				if Vector3(rock.x, rock.y, rock.z).distance_to(at_worst) < rock.w + room:
					print("RUINS   by sphere (%.2f, %.2f, %.2f) r %.2f" % [rock.x, rock.y, rock.z, rock.w])
	print("RUINS CHECK PASSED" if bad == 0 else "RUINS CHECK FAILED (%d)" % bad)
	quit()


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
				# (slivers of no size, where a long concave face was cut into triangles, say nothing of which way it faces)
				continue
			count += 1
			if facing.dot(normals[ia] + normals[ib] + normals[ic]) > 0.0:
				agree += 1
			elif OS.get_cmdline_user_args().has("--why"):
				print("RUINS   against its normals: %s at %s, area %.4f, facing %s, normals %s %s %s" % [name, (a + b + c) / 3.0, facing.length() * 0.5, facing.normalized(), normals[ia], normals[ib], normals[ic]])
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
	_sea = load("res://scripts/sea.gd").new()
	root.add_child(_sea)
	(_sea.get(&"sand") as Node3D).visible = false
	var floor_sand: Node3D = load("res://scripts/sand_ground.gd").new()
	floor_sand.set(&"half", Vector2(130.0, 130.0))
	floor_sand.set(&"cell", 2.0)
	floor_sand.set(&"colour", Color(0.62, 0.63, 0.6))
	floor_sand.set(&"ripples", 1)
	floor_sand.set(&"solid", false)
	floor_sand.set(&"casts_shadow", false)
	floor_sand.set(&"height", func(x: float, z: float) -> float: return 0.15 * sin(x * 0.21) * cos(z * 0.17))
	root.add_child(floor_sand)
	_env = (_sea.find_children("*", "WorldEnvironment", true, false)[0] as WorldEnvironment).environment
	_ruins = load("res://scripts/ruins.gd").new()
	root.add_child(_ruins)
	# (lamps at its lantern spots, as the game might hang them: the pictures only)
	for at: Vector3 in _ruins.call(&"lanterns"):
		var lamp := OmniLight3D.new()
		lamp.light_color = Color(0.55, 0.9, 1.0)
		lamp.light_energy = 1.6
		lamp.omni_range = 9.0
		root.add_child(lamp)
		lamp.global_position = at
	_camera = Camera3D.new()
	_camera.fov = 62.0
	_camera.far = 400.0
	root.add_child(_camera)
	_camera.current = true
	_sea.set(&"eye", _camera)
	var temple := Vector3(-2.0, 0.0, -6.0)
	# (her face, the middle of the tunnel through her head, and its way: from tools/build_ruins.py's HEAD_AT)
	var face := Vector3(5.27, 4.35, 10.09)
	var tunnel := Vector3(4.64, 2.81, 7.59)
	var across := Vector3(0.969, 0.0, -0.247)
	# name, from, looking at, clear water (0: the game's water; else the fog's density; -1 the plan)
	var shots := [
		["concept_view", Vector3(2.0, 4.5, 36.0), Vector3(8.0, 5.0, -4.0), 0.0],
		["concept_view_clear", Vector3(2.0, 4.5, 36.0), Vector3(8.0, 5.0, -4.0), 0.012],
		["approach", Vector3(6.0, 7.0, 52.0), Vector3(4.0, 5.0, -2.0), 0.0],
		["plan", Vector3(8.0, 36.0, 2.0), Vector3(8.0, 0.0, 1.99), -1.0],
		["overview_clear", Vector3(52.0, 34.0, 46.0), Vector3(6.0, 2.0, -2.0), 0.006],
		["gate_front", Vector3(-22.0, 4.0, 30.0), Vector3(-18.0, 5.0, 14.0), 0.0],
		["gate_back", Vector3(-10.0, 6.0, 1.0), Vector3(-18.0, 5.0, 14.0), 0.0],
		["gate_through", Vector3(-18.0, 2.4, 27.0), Vector3(-13.0, 2.6, 0.0), 0.0],
		["temple_front", Vector3(-6.0, 7.0, 16.0), temple + Vector3(0.0, 7.0, 0.0), 0.0],
		["temple_side", Vector3(-26.0, 12.0, -14.0), temple + Vector3(0.0, 6.0, 0.0), 0.0],
		["temple_inside_dome", temple + Vector3(-1.0, 2.6, -2.0), temple + Vector3(2.0, 14.0, 3.0), 0.0],
		["temple_between_columns", temple + Vector3(-9.0, 3.2, 3.0), temple + Vector3(4.0, 4.0, -1.0), 0.0],
		["statue_from_above", face + Vector3(1.0, 16.0, 2.0), face, 0.0],
		["statue_face", face + Vector3(1.9, 4.9, 7.4), face, 0.0],
		["statue_side", tunnel + across * 10.0 + Vector3(0.0, 2.0, 0.0), tunnel, 0.0],
		["statue_tunnel", tunnel - across * 6.5, tunnel + across * 3.0, 0.0],
		["statue_hand", Vector3(17.0, 5.0, 19.0), Vector3(11.6, 1.2, 12.4), 0.0],
		["stoa_front", Vector3(12.0, 6.0, -10.0), Vector3(10.0, 3.0, -24.0), 0.0],
		["stoa_back", Vector3(8.0, 7.0, -40.0), Vector3(10.0, 3.0, -24.0), 0.0],
		["stoa_inside", Vector3(-4.0, 3.0, -24.0), Vector3(22.0, 3.0, -24.0), 0.0],
		["pyramid_front", Vector3(20.0, 7.0, 22.0), Vector3(26.0, 5.0, -6.0), 0.0],
		["pyramid_back", Vector3(44.0, 12.0, -26.0), Vector3(26.0, 5.0, -6.0), 0.0],
		["pyramid_chamber", Vector3(30.6, 1.2, -3.2), Vector3(26.0, 9.0, -6.6), 0.0],
		["pyramid_chamber_walls", Vector3(26.0, 1.5, -4.0), Vector3(31.0, 1.4, -9.0), 0.0],
		["pyramid_door", Vector3(30.0, 2.0, 10.0), Vector3(29.8, 1.8, -6.0), 0.0],
		["pyramid_high_door", Vector3(26.0, 11.0, 10.0), Vector3(26.0, 10.0, -6.0), 0.0],
		["pillar", Vector3(30.0, 9.0, 24.0), Vector3(38.0, 12.0, 6.0), 0.0],
		["field", Vector3(24.0, 4.0, 30.0), Vector3(12.0, 1.0, 18.0), 0.0],
	]
	for shot: Array in shots:
		if _only != "" and not String(shot[0]).contains(_only):
			continue
		var clear: float = shot[3]
		_env.fog_density = 0.04 if clear == 0.0 else maxf(clear, 0.0)
		_camera.projection = Camera3D.PROJECTION_ORTHOGONAL if clear < 0.0 else Camera3D.PROJECTION_PERSPECTIVE
		_camera.size = 92.0
		_camera.look_at_from_position(shot[1], shot[2], Vector3.UP if absf((shot[2] - shot[1]).normalized().y) < 0.99 else Vector3.FORWARD)
		for f in 8:
			await process_frame
		await RenderingServer.frame_post_draw
		var image := root.get_texture().get_image()
		image.save_png(_out.path_join("%s.png" % shot[0]))
		print("RUINS shot ", shot[0])
	quit()
