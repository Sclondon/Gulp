extends SceneTree
## The reef wreck by itself (scripts/wreck.gd, tools/WRECK.md), before the map has a place for it.
##
##   godot --headless --path . --audio-driver Dummy -s res://tests/wreck_view.gd -- --check
##   godot --path . --audio-driver Dummy --resolution 1280x720 -s res://tests/wreck_view.gd -- --out=<new folder>
##
## --check (headless): the model's faces (winding against normals, volume), its triangles, every
## swim route sampled every 0.2 m (Sea.clear_of_rocks must leave each point where it is, for a fish
## of the route's room), the fish spots, and what a call to Sea.clear_of_rocks costs beside it.
## Prints WRECK lines and WRECK CHECK PASSED or FAILED.
##
## --out (a window): pictures under the game's water and its half-size picture with the post shader:
## the whole wreck from both sides, bow-on, stern-on, from above, the break (with the fog thinned so
## the whole of it shows), a view at the game's own fog, and from inside each swim-through.

const SHOTS_FOG := 0.014

var _out := ""
var _wreck: Wreck
var _sea: Sea
var _camera: Camera3D
var _bed := 10.0


func _initialize() -> void:
	var check := false
	for arg in OS.get_cmdline_user_args():
		if arg == "--check":
			check = true
		elif arg.begins_with("--out="):
			_out = arg.get_slice("=", 1)
	if check:
		_check()
		return
	_pictures()


# --- Where things are, from the ship's own upright frame (Blender's: x starboard, y to the bow, z
# up from the keel) to the wreck's local space, by the same placing build_wreck.py gives each half.
func _from_blender(p: Vector3) -> Vector3:
	return Vector3(p.x, p.z, -p.y)


func bow_at(x: float, y: float, z: float) -> Vector3:
	var turn := Basis(Vector3.RIGHT, deg_to_rad(-1.2)) * Basis(Vector3.BACK, deg_to_rad(12.0))
	return _wreck.global_transform * (Vector3(0.0, -0.45, 0.0) + turn * _from_blender(Vector3(x, y, z)))


func stern_at(x: float, y: float, z: float) -> Vector3:
	var pivot := Vector3(0.0, 0.0, 20.0)
	var turn := Basis(Vector3.UP, deg_to_rad(20.0)) * Basis(Vector3.RIGHT, deg_to_rad(-2.0)) * Basis(Vector3.BACK, deg_to_rad(-5.0))
	var local := Vector3(1.0, -1.4, 5.5) + pivot + turn * (_from_blender(Vector3(x, y, z)) - pivot)
	return _wreck.global_transform * local


# --- Checks
func _check() -> void:
	var bad := 0
	var made: Node = (load(Wreck.MODEL) as PackedScene).instantiate()
	var total := 0
	for drawn: MeshInstance3D in made.find_children("*", "MeshInstance3D", true, false):
		var judged := _winding(drawn.mesh)
		total += judged.x
		var good: bool = judged.y >= 99.0 and judged.z > 0.0
		print("WRECK winding %s: %d triangles, winding agrees with normals %.2f%%, volume %.1f m3: %s" % [drawn.name, judged.x, judged.y, judged.z, "ok" if good else "BAD"])
		if not good:
			bad += 1
	var markers := {"ReefSpot": 0, "FishSpot": 0, "Lantern": 0}
	for node: Node in made.find_children("*", "", true, false):
		for key: String in markers:
			if String(node.name).begins_with(key):
				markers[key] += 1
	made.free()
	print("WRECK triangles %d; markers %s" % [total, markers])
	if markers.ReefSpot != 40 or markers.FishSpot != 12 or markers.Lantern != 6:
		bad += 1
	_wreck = Wreck.new()
	root.add_child(_wreck)
	await process_frame
	var spheres := _wreck.spheres()
	print("WRECK frame check: FishSpot00 %s, by the test's mapping %s" % [_wreck.fish_spots()[0], bow_at(2.0, -8.0, 5.4)])
	if spheres.size() < 100:
		bad += 1
	print("WRECK collision spheres: %d (radius %.2f to %.2f)" % [spheres.size(), _min_radius(spheres), _max_radius(spheres)])
	for route: Dictionary in _wreck.routes():
		var room: float = route.room
		var worst := INF
		var moved := 0
		var points: PackedVector3Array = route.points
		for i in points.size() - 1:
			var a := points[i]
			var b := points[i + 1]
			var steps := maxi(1, int(a.distance_to(b) / 0.2))
			for k in steps + 1:
				var p := a.lerp(b, float(k) / steps)
				if Sea.clear_of_rocks(p, room).distance_to(p) > 0.005:
					moved += 1
				worst = minf(worst, _clearance(p, spheres))
		var fits := worst / 0.3
		var good := moved == 0
		print("WRECK route %s: room %.2f, clearance at its tightest %.2f m (a fish up to about %.1f m long), %d points pushed: %s" % [route.name, room, worst, fits, moved, "ok" if good else "BLOCKED"])
		if not good:
			bad += 1
	var tight := 0
	for p in _wreck.fish_spots():
		if Sea.clear_of_rocks(p, 0.3).distance_to(p) > 0.005:
			tight += 1
			print("WRECK fish spot inside a sphere: %s" % p)
	print("WRECK fish spots: %d, %d inside the collision" % [_wreck.fish_spots().size(), tight])
	if tight > 0:
		bad += 1
	# What a swimmer's call costs beside it, and the most spheres any one square of Sea's grid holds.
	var most := 0
	for key: Variant in Sea._cells:
		most = maxi(most, (Sea._cells[key] as PackedInt32Array).size())
	var rng := RandomNumberGenerator.new()
	rng.seed = 3
	var tries := 20000
	var started := Time.get_ticks_usec()
	for i in tries:
		var p := Vector3(rng.randf_range(-12.0, 12.0), rng.randf_range(0.5, 16.0), rng.randf_range(-36.0, 36.0))
		Sea.clear_of_rocks(p, 0.3)
	var cost := float(Time.get_ticks_usec() - started) / tries
	print("WRECK Sea.clear_of_rocks beside the wreck: %.1f us a call; at most %d spheres in one %d m square" % [cost, most, int(Sea.CELL)])
	print("WRECK reef pieces: %d kinds, %d placed" % _reef_count())
	print("WRECK CHECK PASSED" if bad == 0 else "WRECK CHECK FAILED (%d)" % bad)
	quit()


func _reef_count() -> Array:
	var kinds := 0
	var placed := 0
	var reef := _wreck.get_node_or_null(^"Reef")
	if reef:
		for many: MultiMeshInstance3D in reef.get_children():
			kinds += 1
			placed += many.multimesh.instance_count
	return [kinds, placed]


func _clearance(p: Vector3, spheres: Array[Vector4]) -> float:
	var best := INF
	for s in spheres:
		best = minf(best, p.distance_to(Vector3(s.x, s.y, s.z)) - s.w)
	return best


func _min_radius(spheres: Array[Vector4]) -> float:
	var r := INF
	for s in spheres:
		r = minf(r, s.w)
	return r


func _max_radius(spheres: Array[Vector4]) -> float:
	var r := 0.0
	for s in spheres:
		r = maxf(r, s.w)
	return r


func _winding(mesh: Mesh) -> Vector3:
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
			if facing.length_squared() < 1e-14:
				continue
			count += 1
			if facing.dot(normals[ia] + normals[ib] + normals[ic]) > 0.0:
				agree += 1
			volume += facing.dot(a + b + c) / 18.0
	return Vector3(count, 100.0 * agree / maxf(count, 1.0), volume)


# --- Pictures
func _pictures() -> void:
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_NO_FOCUS, true)
	DirAccess.make_dir_recursive_absolute(_out)
	var container := SubViewportContainer.new()
	container.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	container.stretch = true
	container.stretch_shrink = 2
	container.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	var post := ShaderMaterial.new()
	post.shader = load("res://shaders/post.gdshader")
	post.set_shader_parameter(&"underwater", 1.0)
	post.set_shader_parameter(&"water_tint", Color(0.06, 0.2, 0.5))
	post.set_shader_parameter(&"tint", 0.35)
	post.set_shader_parameter(&"sway", 0.002)
	post.set_shader_parameter(&"shafts", 0.12)
	post.set_shader_parameter(&"levels", 28.0)
	post.set_shader_parameter(&"dither", 0.5)
	post.set_shader_parameter(&"vignette", 0.3)
	container.material = post
	root.add_child(container)
	var view := SubViewport.new()
	container.add_child(view)
	_sea = Sea.new()
	view.add_child(_sea)
	# (a level bed 30 m under the surface, as the map's shelf for it)
	_bed = Sea.SURFACE - 30.0
	var floor_ := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(400.0, 400.0)
	floor_.mesh = plane
	var sand := StandardMaterial3D.new()
	sand.albedo_color = Color(0.62, 0.63, 0.6)
	sand.roughness = 1.0
	floor_.material_override = sand
	floor_.position = Vector3(0.0, _bed, 0.0)
	view.add_child(floor_)
	_camera = Camera3D.new()
	_camera.near = 0.05
	_camera.far = 150.0
	_camera.fov = 60.0
	view.add_child(_camera)
	_camera.current = true
	_wreck = Wreck.new()
	_wreck.position = Vector3(0.0, _bed, 0.0)
	view.add_child(_wreck)
	_shoot()


func _shoot() -> void:
	# (the wreck is placed only once the tree runs: wait for that before working out where to look)
	await process_frame
	var shots := [
		["side_starboard", Vector3(58.0, _bed + 12.0, -6.0), Vector3(0.0, _bed + 5.0, 2.0), true],
		["side_port", Vector3(-58.0, _bed + 12.0, -2.0), Vector3(0.0, _bed + 5.0, 2.0), true],
		["bow_on", bow_at(14.0, 58.0, 9.0), bow_at(0.0, 18.0, 6.0), true],
		["stern_on", stern_at(-12.0, -52.0, 9.0), stern_at(0.0, -20.0, 4.0), true],
		["above", Vector3(1.0, _bed + 27.0, 3.0), Vector3(0.0, _bed, 3.0), true],
		["three_quarter", bow_at(30.0, 44.0, 22.0), bow_at(0.0, 0.0, 6.0), true],
		["the_break", bow_at(16.0, -14.0, 13.0), bow_at(0.0, -10.0, 5.0), true],
		["game_fog", bow_at(13.0, 22.0, 9.0), bow_at(0.0, 10.0, 7.0), false],
		["bow_rail", bow_at(4.0, 33.0, 12.5), bow_at(0.0, 25.0, 8.8), false],
		["saloon_up_the_stairs", bow_at(0.0, -10.1, 6.6), bow_at(0.0, -5.0, 10.4), false],
		["promenade_colonnade", bow_at(1.9, -3.4, 8.4), bow_at(1.9, 10.0, 8.4), false],
		["tear_from_outside", bow_at(8.5, 7.5, 3.6), bow_at(0.0, 8.0, 3.2), false],
		["boiler_room_to_tear", bow_at(-0.2, 11.8, 4.6), bow_at(3.6, 7.2, 3.2), false],
		["hold_from_hatch", bow_at(0.3, 15.4, 9.6), bow_at(0.0, 19.0, 2.0), false],
		["down_the_funnel", bow_at(0.2, 10.4, 14.0), bow_at(0.0, 10.5, 2.0), false],
		["up_the_funnel_shaft", bow_at(1.0, 7.0, 3.0), bow_at(0.0, 10.5, 12.0), false],
		["engine_room", stern_at(0.0, -9.0, 4.0), stern_at(0.0, -17.0, 3.0), false],
		["under_the_stern", stern_at(5.0, -32.0, 2.5), stern_at(0.0, -27.0, 2.2), false],
	]
	_sea.sand.visible = false
	_sea.eye = _camera
	for frame in 8:
		await process_frame
	for shot: Array in shots:
		_sea._env.fog_density = SHOTS_FOG if shot[3] else 0.04
		_camera.look_at_from_position(shot[1], shot[2])
		for frame in 4:
			await process_frame
		await RenderingServer.frame_post_draw
		var image := root.get_texture().get_image()
		image.save_png(_out.path_join(String(shot[0]) + ".png"))
		print("WRECK shot ", shot[0])
	print("WRECK PICTURES DONE")
	quit()
