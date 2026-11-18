extends Node
## What a frame costs, place by place (`-- --perf=<places>`, run by Main as a child, in a window:
## headless draws nothing). Each place: the fish (a sardine, nothing hunting) is put there, the
## sea settles for SETTLE seconds (kinds new there get their models), then FRAMES frames are
## measured: the whole frame, the scripts' _process work (from a node that runs first to one that
## runs last), Life's own parts, what the sea's picture drew (draws, triangles, objects) and its
## render time on the CPU and GPU. Then the heaviest things in view (triangles a frame, by owner).
## One `PERF` line a place, and a table at the end. tools/PERF.md says how it was used.
##
##   godot --path . --audio-driver Dummy --disable-vsync --resolution 390x844 --position 2600,60 -- --perf=start,kelp,reef,pirate,ruins,docks,ball
##   godot ... -- --perf=title        (the title, behind the boat; start-up times as well)
##
## Places: start (where a run starts), a zone name (Sea.ZONES: kelp, reef (the liner), pirate,
## ruins, docks...), ball (inside the bait ball of 1,600 sardines), title. `--perf-as=<kind>` swims
## as another animal (a bigger fish sees further: the camera is further back).

const SETTLE := 4.0
const FRAMES := 300

var main: Node
var places: PackedStringArray = []
var as_kind := ""
## A folder to save a picture of each place into (`--perf-shots=<folder>`), or "".
var shots := ""

var _rows: Array = []
var _first: Node
var _last: Node
var _t_first := 0
var _script_usec := 0
var _start_ms := 0


class _Clock extends Node:
	var on_tick: Callable
	func _process(_d: float) -> void:
		on_tick.call()


func _ready() -> void:
	_start_ms = Time.get_ticks_msec()
	_first = _Clock.new()
	_first.process_priority = -100000
	_first.on_tick = func() -> void: _t_first = Time.get_ticks_usec()
	_last = _Clock.new()
	_last.process_priority = 100000
	_last.on_tick = func() -> void: _script_usec += Time.get_ticks_usec() - _t_first
	get_tree().root.add_child.call_deferred(_first)
	get_tree().root.add_child.call_deferred(_last)
	_run.call_deferred()


func _run() -> void:
	var view: SubViewport = main._viewport
	RenderingServer.viewport_set_measure_render_time(view.get_viewport_rid(), true)
	RenderingServer.viewport_set_measure_render_time(get_tree().root.get_viewport_rid(), true)
	main.life.hunting = false
	main.limited = false
	main.player.deepest = INF
	if "title" in places:
		await _startup()
	for place in places:
		if place != "title":
			_go(place)
		var wait_until := Time.get_ticks_msec() + int(SETTLE * 1000.0)
		while Time.get_ticks_msec() < wait_until:
			if place != "title":
				_hold(place)
			await get_tree().process_frame
		if shots != "":
			await RenderingServer.frame_post_draw
			get_viewport().get_texture().get_image().save_png(shots.path_join(place + ".png"))
		await _measure(place)
	_table()
	get_tree().quit()


# Start-up: when the first frame was drawn, when the starting waters' kinds were ready (the game
# may start), when every kind had been shown once.
func _startup() -> void:
	var near_at := -1
	var all_at := -1
	var first_at := -1
	var kinds := {}
	for thing: Array in main._warm_things:
		var m: Material = thing[1]
		var label := (m as ShaderMaterial).shader.resource_path.get_file() if m is ShaderMaterial and (m as ShaderMaterial).shader else m.get_class()
		kinds[label] = int(kinds.get(label, 0)) + 1
	print("PERF WARM materials: ", kinds)
	var slow := []
	var was := Time.get_ticks_usec()
	var until := Time.get_ticks_msec() + 240000
	while Time.get_ticks_msec() < until:
		var showing: String = main._warming[0] if not main._warming.is_empty() else ""
		await get_tree().process_frame
		var now := Time.get_ticks_usec()
		if now - was > 150000:
			slow.append("%s %d ms" % [showing, (now - was) / 1000])
		was = now
		if first_at < 0 and Engine.get_frames_drawn() > 0:
			first_at = Time.get_ticks_msec()
		var left: int = main._warming.size()
		if near_at < 0 and main._warm_all > 0 and left <= main._warm_all - main._warm_first:
			near_at = Time.get_ticks_msec()
		if left == 0 and main._warm_now == null:
			all_at = Time.get_ticks_msec()
			break
	print("PERF STARTUP engine to main ready %d ms; first frame %d ms; starting kinds ready (start button live) %d ms; every kind and material shown %d ms; %d in all (%d materials), %d first" % [
			_start_ms, first_at, near_at, all_at, main._warm_all, main._warm_things.size(), main._warm_first])
	print("PERF STARTUP frames over 150 ms (%d): %s" % [slow.size(), ", ".join(slow.slice(0, 60))])


func _go(place: String) -> void:
	var player: Player = main.player
	if as_kind != "":
		main._start_kind = as_kind
	match place:
		"start":
			main._near = ""
			main._start = Sea.START
			main.restart()
		"ball":
			main._near = ""
			main.restart()
			_hold(place)
		_:
			main._near = place
			main.restart()
	main.camera.global_position = main._camera_place()
	player.safe = 1000.0


# Keeps the fish where it was put (it always swims forward): inside the ball, the ball's middle.
func _hold(place: String) -> void:
	var player: Player = main.player
	if place == "ball":
		var ball: Dictionary = main.life.schools[Life.KRILL_CLOUDS]
		player.global_position = ball.mid
		player.heading = Vector3(1.0, 0.0, 0.3).normalized()
	player.stick = Vector2.ZERO
	player.throttle = 0.0


func _measure(place: String) -> void:
	var view: SubViewport = main._viewport
	var vrid := view.get_viewport_rid()
	var rrid := get_tree().root.get_viewport_rid()
	var life: Life = main.life
	var c0: Vector3 = life.cost_usec
	var f0: float = life.flock_ms
	var s0: int = life.steps
	_script_usec = 0
	var frame_us := PackedInt64Array()
	var draws := 0
	var prims := 0
	var objs := 0
	var all_draws := 0
	var gpu := 0.0
	var cpu := 0.0
	var root_gpu := 0.0
	var proc := 0.0
	print("PROFILE START %s" % place)
	var last := Time.get_ticks_usec()
	for i in FRAMES:
		if place != "title":
			_hold(place)
		await get_tree().process_frame
		var now := Time.get_ticks_usec()
		frame_us.append(now - last)
		last = now
		draws += RenderingServer.viewport_get_render_info(vrid, RenderingServer.VIEWPORT_RENDER_INFO_TYPE_VISIBLE, RenderingServer.VIEWPORT_RENDER_INFO_DRAW_CALLS_IN_FRAME)
		prims += RenderingServer.viewport_get_render_info(vrid, RenderingServer.VIEWPORT_RENDER_INFO_TYPE_VISIBLE, RenderingServer.VIEWPORT_RENDER_INFO_PRIMITIVES_IN_FRAME)
		objs += RenderingServer.viewport_get_render_info(vrid, RenderingServer.VIEWPORT_RENDER_INFO_TYPE_VISIBLE, RenderingServer.VIEWPORT_RENDER_INFO_OBJECTS_IN_FRAME)
		all_draws += int(Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME))
		gpu += RenderingServer.viewport_get_measured_render_time_gpu(vrid)
		cpu += RenderingServer.viewport_get_measured_render_time_cpu(vrid)
		root_gpu += RenderingServer.viewport_get_measured_render_time_gpu(rrid)
		proc += Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0
	print("PROFILE STOP %s" % place)
	var sorted := frame_us.duplicate()
	sorted.sort()
	var n := float(FRAMES)
	var total := 0
	for us in frame_us:
		total += us
	var steps := maxf(life.steps - s0, 1.0)
	var parts: Vector3 = (life.cost_usec - c0) / steps / 1000.0
	var row := {
		"place": place,
		"frame": total / n / 1000.0,
		"p95": sorted[int(n * 0.95)] / 1000.0,
		"scripts": _script_usec / n / 1000.0,
		"life": parts.x + parts.y + parts.z,
		"schools": parts.x, "fish": parts.y, "jellies": parts.z,
		"flocks": (life.flock_ms - f0) / steps,
		"draws": draws / n, "all_draws": all_draws / n, "tris": prims / n, "objects": objs / n,
		"gpu": gpu / n, "cpu_draw": cpu / n, "ui_gpu": root_gpu / n, "process": proc / n,
	}
	_rows.append(row)
	print("PERF %s: frame %.2f ms (95th %.2f), scripts %.2f ms (life %.2f: schools %.2f fish %.2f jellies %.2f; flocks %.2f), sea picture %d draws %d tris %d objects, render cpu %.2f gpu %.2f ms, ui gpu %.2f, all draws %d" % [
			place, row.frame, row.p95, row.scripts, row.life, row.schools, row.fish, row.jellies, row.flocks, row.draws, row.tris, row.objects, row.cpu_draw, row.gpu, row.ui_gpu, row.all_draws])
	await _heaviest(place)


# The heaviest things the camera can see: triangles by owner (estimated from the meshes; the
# draws and triangles above are what was really drawn).
func _heaviest(place: String) -> void:
	var view: SubViewport = main._viewport
	var camera: Camera3D = main.camera
	var planes := camera.get_frustum()
	var eye := camera.global_position
	var by := {}
	for node in view.find_children("*", "GeometryInstance3D", true, false):
		var g := node as GeometryInstance3D
		if not g.is_visible_in_tree():
			continue
		var tris := 0
		var box := AABB()
		var mm: MultiMesh = null
		if g is MultiMeshInstance3D:
			mm = (g as MultiMeshInstance3D).multimesh
			if mm == null or mm.mesh == null:
				continue
			var count := mm.visible_instance_count if mm.visible_instance_count >= 0 else mm.instance_count
			tris = _tris(mm.mesh) * count
		elif g is MeshInstance3D:
			var m := (g as MeshInstance3D).mesh
			if m == null:
				continue
			tris = _tris(m)
		elif g is CPUParticles3D:
			var p := g as CPUParticles3D
			tris = (_tris(p.mesh) if p.mesh else 2) * p.amount
		else:
			continue
		box = g.global_transform * g.get_aabb()
		var far := box.get_center().distance_to(eye) - box.size.length() * 0.5
		if g.visibility_range_end > 0.0 and far > g.visibility_range_end:
			continue
		if not _in_view(box, planes):
			continue
		var key := _owner_of(g, view)
		var had: Array = by.get(key, [0, 0, []])
		(had[2] as Array).append(g)
		by[key] = [int(had[0]) + tris, int(had[1]) + 1, had[2]]
	var keys := by.keys()
	keys.sort_custom(func(a, b) -> bool: return int(by[a][0]) > int(by[b][0]))
	var line := "PERF HEAVY %s:" % place
	for k in keys.slice(0, 14):
		line += " %s %dk tris/%d" % [k, int(by[k][0]) / 1000, int(by[k][1])]
	print(line)
	# What each of the eight heaviest really costs: drawn without it for a few frames, the
	# triangles and draws the picture loses.
	var vrid := view.get_viewport_rid()
	var base := await _drawn(vrid, place)
	line = "PERF DRAWN %s (all %dk tris, %d draws):" % [place, base.x / 1000, base.y]
	for k in keys.slice(0, 8):
		var nodes: Array = by[k][2]
		for g: GeometryInstance3D in nodes:
			g.visible = false
		var without := await _drawn(vrid, place)
		for g: GeometryInstance3D in nodes:
			g.visible = true
		line += " %s %dk/%d" % [k, (base.x - without.x) / 1000, base.y - without.y]
	print(line)


# The triangles and draws of the sea's picture, the average of a few frames.
func _drawn(vrid: RID, place: String) -> Vector2i:
	var sum := Vector2i.ZERO
	for i in 4:
		if place != "title":
			_hold(place)
		await get_tree().process_frame
		if i >= 2:
			sum += Vector2i(RenderingServer.viewport_get_render_info(vrid, RenderingServer.VIEWPORT_RENDER_INFO_TYPE_VISIBLE, RenderingServer.VIEWPORT_RENDER_INFO_PRIMITIVES_IN_FRAME),
					RenderingServer.viewport_get_render_info(vrid, RenderingServer.VIEWPORT_RENDER_INFO_TYPE_VISIBLE, RenderingServer.VIEWPORT_RENDER_INFO_DRAW_CALLS_IN_FRAME))
	return sum / 2


static var _tri_cache := {}


func _tris(m: Mesh) -> int:
	if _tri_cache.has(m):
		return _tri_cache[m]
	var t := 0
	for s in m.get_surface_count():
		if m is ArrayMesh:
			var am := m as ArrayMesh
			var idx := am.surface_get_array_index_len(s)
			t += (idx if idx > 0 else am.surface_get_array_len(s)) / 3
		else:
			var arrays := m.surface_get_arrays(s)
			var ind: PackedInt32Array = arrays[Mesh.ARRAY_INDEX] if arrays[Mesh.ARRAY_INDEX] != null else PackedInt32Array()
			t += (ind.size() if ind.size() > 0 else (arrays[Mesh.ARRAY_VERTEX] as PackedVector3Array).size()) / 3
	_tri_cache[m] = t
	return t


func _in_view(box: AABB, planes: Array[Plane]) -> bool:
	var c := box.get_center()
	var r := box.size.length() * 0.5
	for p in planes:
		if p.distance_to(c) > r:
			return false
	return true


# Who a drawn thing belongs to: a creature by its kind, a flock, or the node two levels under the
# sea's picture (Scenery/<piece>, Sea/<part>, Scenery's Wreck...).
func _owner_of(g: Node, view: Node) -> String:
	var n := g
	var chain: Array[Node] = []
	while n and n != view:
		chain.push_front(n)
		if n is Creature:
			return "fish:" + (n as Creature).kind
		if n is Flock:
			return "flock"
		n = n.get_parent()
	if chain.size() >= 2:
		var second := chain[1]
		var label: String = second.name
		if second.get_script():
			var cls: String = (second.get_script() as Script).get_global_name()
			if cls != "":
				label = cls
		if chain.size() >= 3 and (chain[2] is LodField or chain[1] is LodField or chain[2].name == &"Liner"):
			# (a LodField's full and light models apart; the liner's hull apart from its reef)
			var last := String(g.name)
			return "%s/%s/%s" % [_label(chain[0]), label, "light" if last.ends_with("_far") else ("full" if g is MultiMeshInstance3D else last)]
		return "%s/%s" % [_label(chain[0]), label]
	return chain[0].name if chain.size() > 0 else "?"


func _label(n: Node) -> String:
	if n.get_script():
		var cls: String = (n.get_script() as Script).get_global_name()
		if cls != "":
			return cls
	return n.name


func _table() -> void:
	print("PERF TABLE place | frame ms | 95th | scripts ms | life | flocks | draws | tris k | objects | render cpu | gpu")
	for r: Dictionary in _rows:
		print("PERF ROW %s | %.2f | %.2f | %.2f | %.2f | %.2f | %d | %d | %d | %.2f | %.2f" % [r.place, r.frame, r.p95, r.scripts, r.life, r.flocks, r.draws, int(r.tris) / 1000, r.objects, r.cpu_draw, r.gpu])
