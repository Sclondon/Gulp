@tool
extends Node
## Checks the bay editor inside a real (headless) Godot editor: how fast editor/bay_layout.tscn opens,
## that saving it with nothing changed leaves data/layout.json as it was, that a moved place and its
## undo save and unsave, that a brush stroke bakes into the floor and its undo bakes it back byte for
## byte, how long a rebake takes, that ctrl+S keeps the handles out of the scene file, and how closely
## the trench's traced outline follows the drawn mask. Puts every file back as it was.
##   godot --editor --headless --path . --audio-driver Dummy -- --bay-layout-test
## (the plugin, addons/bay_layout, starts it). Prints BAY lines, then BAY EDITOR PASS or FAIL, and quits.

const BAKE := preload("res://addons/bay_layout/bay_bake.gd")
const SCENE := "res://editor/bay_layout.tscn"

var plugin: EditorPlugin
var _bad := 0


func _ready() -> void:
	_run.call_deferred()


func _wait(frames: int) -> void:
	for i in frames:
		await get_tree().process_frame


func _check(what: String, ok: bool, note := "") -> void:
	print("BAY %s: %s%s" % [what, "ok" if ok else "BAD", ("  (" + note + ")") if note != "" else ""])
	if not ok:
		_bad += 1


func _run() -> void:
	await _wait(30)
	var layout_was := FileAccess.get_file_as_string(Layout.PATH)
	var floor_was := FileAccess.get_file_as_bytes(BAKE.OUT)
	var ruins_was := FileAccess.get_file_as_string("res://data/ruins_layout.json")
	var scene_was := FileAccess.get_file_as_string(SCENE)
	# Opening.
	var t := Time.get_ticks_msec()
	EditorInterface.open_scene_from_path(SCENE)
	var root: Node = EditorInterface.get_edited_scene_root()
	var opened := Time.get_ticks_msec() - t
	_check("the scene opens", root != null and root.get(&"floor_node") != null, "%d ms, %s" % [opened, root.get(&"status") if root else ""])
	if root == null:
		_end()
		return
	var count := 0
	for node in root.find_children("*", "", true, false):
		if node.owner == root:
			count += 1
	print("BAY handles: %d nodes in the scene tree" % count)
	# (the floor's picture: made now if it was not there or was old)
	t = Time.get_ticks_msec()
	var ms: int = root.call(&"refresh_floor_now", false)
	_check("the floor is drawn", (root.get(&"floor_node") as MeshInstance3D).mesh != null, "a fresh picture of the floor took %d ms" % ms)
	# Saving with nothing changed.
	var bake: bool = root.call(&"save_layout")
	var same := FileAccess.get_file_as_string(Layout.PATH) == layout_was
	_check("saving with nothing changed leaves the layout as it was", same and not bake, "bake asked: %s" % bake)
	if not same:
		_diff(layout_was, FileAccess.get_file_as_string(Layout.PATH))
	# A place moved, with undo.
	var start: Node3D = root.find_child("Start", true, false)
	var ur := plugin.get_undo_redo()
	ur.create_action("move the start")
	ur.add_do_property(start, &"position", start.position + Vector3(10.0, 0.0, 5.0))
	ur.add_undo_property(start, &"position", start.position)
	ur.commit_action()
	root.call(&"save_layout")
	Layout.reload()
	var moved := Layout.point("places.start")
	_check("a moved place is saved", moved.is_equal_approx(Vector2(-30.0, -50.0)), str(moved))
	ur.get_history_undo_redo(ur.get_object_history_id(start)).undo()
	root.call(&"save_layout")
	_check("its undo saves the layout as it was", FileAccess.get_file_as_string(Layout.PATH) == layout_was)
	# A circle resized and a zone's kinds changed, then put back.
	var zone: Node3D = root.find_child("Zone grass*", true, false)
	var kinds: PackedStringArray = zone.get(&"kinds")
	zone.set(&"radius", 20.0)
	zone.set(&"kinds", kinds + PackedStringArray(["lobster"]))
	root.call(&"save_layout")
	Layout.reload()
	_check("a zone's size and kinds are saved", float(Layout.value("zones.grass.radius")) == 20.0 and "grass" in (Layout.kind("lobster").zones as Array),
			str(Layout.kind("lobster").zones))
	zone.set(&"radius", 12.0)
	zone.set(&"kinds", kinds)
	root.call(&"save_layout")
	_check("and put back, as it was", FileAccess.get_file_as_string(Layout.PATH) == layout_was)
	# A brush stroke, baked; its undo, baked back.
	var floor_node: Node = root.get(&"floor_node")
	var before := (floor_node.get(&"adjust") as PackedFloat32Array).duplicate()
	var probe := Vector2(-20.0, -80.0)
	var h0: float = floor_node.call(&"height_at", probe.x, probe.y)
	floor_node.call(&"dab", "raise", probe, 8.0, 3.0)
	floor_node.call(&"rebuild")
	var h1: float = floor_node.call(&"height_at", probe.x, probe.y)
	_check("a raise brush raises the floor at once", h1 > h0 + 2.5, "%.2f -> %.2f" % [h0, h1])
	bake = root.call(&"save_layout")
	ms = root.call(&"refresh_floor_now", true)
	var h2: float = floor_node.call(&"height_at", probe.x, probe.y)
	_check("a rebake makes it real", bake and not floor_node.call(&"needs_bake") and absf(h2 - h1) < 0.6 and FileAccess.get_file_as_bytes(BAKE.OUT) != floor_was,
			"rebake and redraw %d ms; %.2f shown, %.2f baked" % [ms, h1, h2])
	print("BAY rebake: %d ms (bake and a fresh picture of the floor, in a process of its own)" % ms)
	floor_node.call(&"set_adjust", before)
	root.call(&"save_layout")
	root.call(&"refresh_floor_now", true)
	_check("the stroke undone and rebaked gives the floor back byte for byte", FileAccess.get_file_as_bytes(BAKE.OUT) == floor_was)
	# Ctrl+S.
	EditorInterface.save_scene()
	await _wait(2)
	var scene_now := FileAccess.get_file_as_string(SCENE)
	_check("ctrl+S writes the layout and keeps the handles out of the scene file", scene_now.count("[node ") == 1 and FileAccess.get_file_as_string(Layout.PATH) == layout_was,
			"%d nodes in the file" % scene_now.count("[node "))
	var owned := 0
	for node in root.find_children("*", "", true, false):
		if node.owner == root:
			owned += 1
	_check("and gives them back to the scene after", owned == count, "%d of %d" % [owned, count])
	# Play here (headless and silent here; the game prints GULP starting at ... when it gets --at).
	plugin.set(&"play_engine_args", "--headless --audio-driver Dummy --fixed-fps 60 --quit-after 240")
	var args_were := String(ProjectSettings.get_setting("editor/run/main_run_args", ""))
	# (the editor may have brought back another scene it had open: the bay's is the one being edited)
	EditorInterface.open_scene_from_path(SCENE)
	plugin.call(&"play_here")
	print("BAY   run args now: ", ProjectSettings.get_setting("editor/run/main_run_args", ""))
	var started := false
	for i in 600:
		await get_tree().process_frame
		if EditorInterface.is_playing_scene():
			started = true
			break
		if i % 100 == 0:
			print("BAY   waiting ", i, " ", EditorInterface.get_playing_scene())
	_check("Play here starts the game", started)
	for i in 900:
		await get_tree().process_frame
		if not EditorInterface.is_playing_scene():
			break
	if EditorInterface.is_playing_scene():
		EditorInterface.stop_playing_scene()
	_check("and puts the run settings back", String(ProjectSettings.get_setting("editor/run/main_run_args", "")) == args_were)
	# The trench's outline against the drawn mask.
	var size := BAKE.grid_size()
	var mask := BAKE.trench_inside(size.x, size.y)
	var loops: Array = root.call(&"trace_trench")
	var points := 0
	var off := 0
	var polys := []
	for loop: Array in loops:
		polys.append(PackedVector2Array(loop))
		points += loop.size()
	for r in size.y:
		for c in size.x:
			var p := Vector2(BAKE.WEST + c, BAKE.NORTH + r)
			var inside := false
			for poly: PackedVector2Array in polys:
				if Geometry2D.is_point_in_polygon(p, poly):
					inside = true
					break
			if inside != (mask[r * size.x + c] > 0.0):
				off += 1
	print("BAY trench outline: %d loops, %d points; %d of %d metre cells differ from the mask (%.2f%%)" % [loops.size(), points, off, mask.size(), 100.0 * off / mask.size()])
	# (everything back as it was)
	_put_back(Layout.PATH, layout_was)
	_put_back("res://data/ruins_layout.json", ruins_was)
	_put_back(SCENE, scene_was)
	if FileAccess.get_file_as_bytes(BAKE.OUT) != floor_was:
		var f := FileAccess.open(BAKE.OUT, FileAccess.WRITE)
		f.store_buffer(floor_was)
	for path in [BAKE.ADJUST, BAKE.ADJUST_BAKED]:
		if FileAccess.file_exists(path):
			DirAccess.remove_absolute(ProjectSettings.globalize_path(path))
	_end()


func _put_back(path: String, text: String) -> void:
	if FileAccess.get_file_as_string(path) != text:
		var f := FileAccess.open(path, FileAccess.WRITE)
		f.store_string(text)


func _diff(a: String, b: String) -> void:
	var la := a.split("\n")
	var lb := b.split("\n")
	var shown := 0
	for i in mini(la.size(), lb.size()):
		if la[i] != lb[i] and shown < 12:
			print("BAY   line %d: %s  ->  %s" % [i + 1, la[i].strip_edges(), lb[i].strip_edges()])
			shown += 1


func _end() -> void:
	print("BAY EDITOR PASS" if _bad == 0 else "BAY EDITOR FAIL (%d)" % _bad)
	get_tree().quit()
