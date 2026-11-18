extends SceneTree
## How the control panel's housings sit on the screen at the window's size: each housing's box (its
## mesh's bounds, pipes and all) as a screen rectangle, and how far each pair overlaps (pixels).
## In a window (the panel is laid out for the real window size):
##   godot --path . --audio-driver Dummy --resolution 390x844 --position 2600,60 -s res://tests/panel_overlap.gd -- --calm --shot=60
## (`--shot` keeps the title away, as a picture run does; the script quits long before then)

var main: Node
var _frames := 0


func _initialize() -> void:
	main = (load("res://main.tscn") as PackedScene).instantiate()
	root.add_child(main)


func _process(_delta: float) -> bool:
	_frames += 1
	if _frames < 90:
		return false
	var panel: Node = null
	for each in main.find_children("*", "SubViewport", true, false):
		if each.get_script() and (each.get_script() as Script).resource_path.ends_with("panel_model.gd"):
			panel = each
	if panel == null:
		print("PANEL not found")
		return true
	var rects := {}
	for name in ["helm", "engine", "gauges", "switches", "aux"]:
		var housing: Node3D = panel.get(name)
		# (its own mesh and everything under it, in the housing's space)
		var box := AABB()
		var first := true
		for each: Node in [housing] + housing.find_children("*", "VisualInstance3D", true, false):
			if not (each is VisualInstance3D):
				continue
			var v := each as VisualInstance3D
			var b := (housing.global_transform.affine_inverse() * v.global_transform) * v.get_aabb()
			box = b if first else box.merge(b)
			first = false
		var lo := Vector3(box.position.x, box.position.y, box.end.z)
		var hi := Vector3(box.end.x, box.end.y, box.end.z)
		var a: Vector2 = panel.call(&"to_screen", housing.position + lo * housing.scale.x)
		var b: Vector2 = panel.call(&"to_screen", housing.position + hi * housing.scale.x)
		var r := Rect2(Vector2(minf(a.x, b.x), minf(a.y, b.y)), (a - b).abs())
		rects[name] = r
		print("PANEL %s %s scale %.2f" % [name, r, housing.scale.x])
	var names := rects.keys()
	for i in names.size():
		for j in range(i + 1, names.size()):
			var o: Rect2 = (rects[names[i]] as Rect2).intersection(rects[names[j]])
			if o.size.x > 0.5 and o.size.y > 0.5:
				print("OVERLAP %s / %s: %.0f x %.0f px" % [names[i], names[j], o.size.x, o.size.y])
	print("SCREEN %s, in a row %s" % [root.size, panel.get("in_a_row")])
	return true
