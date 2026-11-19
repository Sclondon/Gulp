class_name Hitches
extends Node
## A frame that takes too long (a hitch: a freeze of 50 ms or more) and what happened in it, for
## finding what freezes the game (tools/PERF.md, "Hitches"). On with `-- --hitches` (Main adds it);
## off, `note` costs one test of a static flag.
##
## A hitch is reported as one `GULP HITCH` line: its length, how much of it the scripts took (from the
## first node that runs a frame to the last), the sea picture's render time on the CPU (where a
## shader compiled on first draw shows), the notes other code made that frame (`Hitches.note`: an
## animal dressed, a grass square filled...), which nodes were added (counted by kind), and which
## materials were in view for the first time (each a program a browser compiles when first drawn:
## by shader and the way it is drawn, as Main's warm-up keys them). `report()` prints a summary.

## Frames at least this long (ms) are reported.
const LONG_MS := 50.0

static var on := false
static var _notes := PackedStringArray()

## Says what was done this frame (shown if the frame turns out long).
static func note(what: String) -> void:
	if on:
		_notes.append(what)


## The sea's picture (its render time is read), and Main, for where the title's warm-up draws.
var view: SubViewport
var main: Node

var _last_us := 0
var _first_us := 0
var _script_us := 0
var _frame := 0
var _added := {}
# nodes added and not yet seen in view with all their materials: instance id -> node
var _pending := {}
var _seen := {}
var _new_now := PackedStringArray()
var _hitches: Array = []
var _own_us := 0
var _own_most := 0
## A label for the summary (the title, play...), set by whoever drives.
var stage := "start"


class _Tail extends Node:
	var on_tick: Callable
	func _process(_d: float) -> void:
		on_tick.call()


func _ready() -> void:
	on = true
	process_priority = -100000
	var tail := _Tail.new()
	tail.process_priority = 100000
	tail.on_tick = _tail
	get_tree().root.add_child.call_deferred(tail)
	get_tree().node_added.connect(_on_added)
	for node in get_tree().root.find_children("*", "GeometryInstance3D", true, false):
		_pending[node.get_instance_id()] = node
	if view:
		RenderingServer.viewport_set_measure_render_time(view.get_viewport_rid(), true)


func _on_added(node: Node) -> void:
	var label := node.get_class()
	var script: Script = node.get_script()
	if script and script.get_global_name() != "":
		label = script.get_global_name()
	_added[label] = int(_added.get(label, 0)) + 1
	if node is GeometryInstance3D:
		_pending[node.get_instance_id()] = node


func _process(_delta: float) -> void:
	var now := Time.get_ticks_usec()
	if _last_us > 0:
		var ms := (now - _last_us) / 1000.0
		if ms >= LONG_MS:
			var render := RenderingServer.viewport_get_measured_render_time_cpu(view.get_viewport_rid()) if view else 0.0
			var added := []
			for k: String in _added:
				added.append([k, _added[k]])
			added.sort_custom(func(a: Array, b: Array) -> bool: return int(a[1]) > int(b[1]))
			var added_text := PackedStringArray()
			for a: Array in added.slice(0, 8):
				added_text.append("%s x%d" % [a[0], a[1]])
			var hitch := {"frame": _frame, "ms": ms, "scripts": _script_us / 1000.0, "render": render, "stage": stage,
				"notes": _notes.duplicate(), "new": _new_now.duplicate(), "added": ", ".join(added_text)}
			_hitches.append(hitch)
			var cam: Camera3D = view.get_camera_3d() if view else null
			print("GULP HITCH %.0f ms (frame %d, %s, at %s): scripts %.1f ms, sea render cpu %.1f ms | notes: %s | first in view: %s | added: %s" % [
					ms, _frame, stage, ("(%.0f, %.0f, %.0f)" % [cam.global_position.x, cam.global_position.y, cam.global_position.z]) if cam else "?",
					hitch.scripts, render, _short(hitch.notes), _short(hitch.new), hitch.added])
	_last_us = now
	_first_us = now
	_frame += 1
	_notes.clear()
	_new_now.clear()
	_added.clear()


# Last thing each frame before it is drawn: what is now in view whose material has not been before.
func _tail() -> void:
	var t0 := Time.get_ticks_usec()
	_script_us = t0 - _first_us
	var done: Array[int] = []
	for id: int in _pending:
		var node: Variant = _pending[id]
		if not is_instance_valid(node):
			done.append(id)
			continue
		var g := node as GeometryInstance3D
		if not g.is_inside_tree() or not g.is_visible_in_tree():
			continue
		var keys := keys_of(g)
		var fresh := false
		for k: String in keys:
			if not _seen.has(k):
				fresh = true
		if not fresh:
			done.append(id)
			continue
		var by := "warm" if main and main.get(&"warmer") and main.warmer.now and (main.warmer.now as Node).is_ancestor_of(g) else ""
		if by == "" and not _in_view(g):
			continue
		for k: String in keys:
			if not _seen.has(k):
				_seen[k] = _frame
				_new_now.append("%s%s" % [_label(g, k), " (warm)" if by != "" else ""])
		done.append(id)
	for id in done:
		_pending.erase(id)
	var spent := Time.get_ticks_usec() - t0
	_own_us += spent
	_own_most = maxi(_own_most, spent)


## The keys of what a drawn thing needs compiled: each surface's shader (or material), and how it is
## drawn (alone, or in a MultiMesh of a format).
static func keys_of(node: GeometryInstance3D) -> PackedStringArray:
	var out := PackedStringArray()
	var mesh: Mesh = null
	var many: MultiMesh = null
	if node is MeshInstance3D:
		mesh = (node as MeshInstance3D).mesh
	elif node is MultiMeshInstance3D and (node as MultiMeshInstance3D).multimesh:
		many = (node as MultiMeshInstance3D).multimesh
		if many.visible_instance_count == 0 or many.instance_count == 0:
			return out
		mesh = many.mesh
	elif node is CPUParticles3D:
		mesh = (node as CPUParticles3D).mesh
	if mesh == null:
		return out
	for s in mesh.get_surface_count():
		var material: Material = node.material_override
		if material == null and node is MeshInstance3D:
			material = (node as MeshInstance3D).get_active_material(s)
		if material == null:
			material = mesh.surface_get_material(s)
		if material == null:
			continue
		var what: Object = (material as ShaderMaterial).shader if material is ShaderMaterial and (material as ShaderMaterial).shader else material
		out.append("%d %s" % [what.get_instance_id(), "" if many == null else "%d%d%d" % [many.transform_format, int(many.use_colors), int(many.use_custom_data)]])
	return out


func _in_view(g: GeometryInstance3D) -> bool:
	var cam := g.get_viewport().get_camera_3d()
	if cam == null:
		return false
	var box := g.global_transform * g.get_aabb()
	var c := box.get_center()
	var r := box.size.length() * 0.5
	var far := c.distance_to(cam.global_position) - r
	if far > cam.far or (g.visibility_range_end > 0.0 and far > g.visibility_range_end):
		return false
	for p in cam.get_frustum():
		if p.distance_to(c) > r:
			return false
	return true


func _label(g: Node, key: String) -> String:
	var shader_name := ""
	var id := int(key.get_slice(" ", 0))
	var obj := instance_from_id(id)
	if obj is Resource:
		shader_name = (obj as Resource).resource_path.get_file()
		if shader_name == "":
			shader_name = (obj as Resource).get_class()
	var n := g
	var owner_name := String(g.name)
	while n:
		if n.get_script() and (n.get_script() as Script).get_global_name() != "":
			owner_name = (n.get_script() as Script).get_global_name() + "/" + String(g.name)
			break
		n = n.get_parent()
	var tail := key.get_slice(" ", 1)
	return "%s[%s%s]" % [owner_name, shader_name, (" mm" + tail) if tail != "" else ""]


func _short(list: PackedStringArray) -> String:
	if list.is_empty():
		return "-"
	if list.size() > 12:
		return ", ".join(list.slice(0, 12)) + " (+%d)" % (list.size() - 12)
	return ", ".join(list)


## The summary: how many hitches (over 50, 100, 250 ms), the worst, the time lost, by stage.
func report() -> void:
	var by_stage := {}
	for h: Dictionary in _hitches:
		var s: Dictionary = by_stage.get(h.stage, {"n": 0, "n100": 0, "n250": 0, "lost": 0.0, "worst": 0.0})
		s.n += 1
		s.n100 += 1 if h.ms >= 100.0 else 0
		s.n250 += 1 if h.ms >= 250.0 else 0
		s.lost += h.ms - 16.7
		s.worst = maxf(s.worst, h.ms)
		by_stage[h.stage] = s
	for k: String in by_stage:
		var s: Dictionary = by_stage[k]
		print("GULP HITCHES %s: %d over 50 ms, %d over 100, %d over 250, worst %.0f ms, %.1f s lost" % [k, s.n, s.n100, s.n250, s.worst, s.lost / 1000.0])
	var sorted := _hitches.duplicate()
	sorted.sort_custom(func(a: Dictionary, b: Dictionary) -> bool: return a.ms > b.ms)
	for h: Dictionary in sorted.slice(0, 12):
		print("GULP WORST %.0f ms (%s, frame %d): scripts %.1f, render %.1f | %s | %s" % [h.ms, h.stage, h.frame, h.scripts, h.render, _short(h.notes), _short(h.new)])
	print("GULP HITCH LOGGER own cost %.2f ms a frame on average, %.1f ms at most; %d keys seen" % [_own_us / 1000.0 / maxf(_frame, 1.0), _own_most / 1000.0, _seen.size()])
