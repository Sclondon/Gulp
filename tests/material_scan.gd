extends SceneTree
## Lists what the sea and the title draw, and every plain material among it (a StandardMaterial3D
## with no albedo picture: a flat colour), as evidence for the art-style pass (tools/QUALITY.md).
## Headless:
##   godot --headless --path . --audio-driver Dummy -s res://tests/material_scan.gd -- --title
## `--tree` also prints the scene's top three levels (to find what to photograph).

var main: Node
var _frames := 0
var _tree := false


func _initialize() -> void:
	_tree = OS.get_cmdline_user_args().has("--tree")
	main = (load("res://main.tscn") as PackedScene).instantiate()
	root.add_child(main)


func _process(_delta: float) -> bool:
	_frames += 1
	if _frames == 240:
		_report()
		return true
	return false


func _report() -> void:
	if _tree:
		_print_tree(main, 0)
	var plain := {}
	var counts := {"meshes": 0, "multimeshes": 0, "plain": 0}
	for node: Node in main.find_children("*", "GeometryInstance3D", true, false):
		var mesh: Mesh = null
		if node is MeshInstance3D:
			mesh = (node as MeshInstance3D).mesh
			counts.meshes += 1
		elif node is MultiMeshInstance3D and (node as MultiMeshInstance3D).multimesh:
			mesh = (node as MultiMeshInstance3D).multimesh.mesh
			counts.multimeshes += 1
		if mesh == null:
			continue
		var geometry := node as GeometryInstance3D
		for s in mesh.get_surface_count():
			var material: Material = geometry.material_override
			if material == null and node is MeshInstance3D:
				material = (node as MeshInstance3D).get_surface_override_material(s)
			if material == null:
				material = mesh.surface_get_material(s)
			var why := ""
			if material == null:
				why = "no material"
			elif material is StandardMaterial3D and (material as StandardMaterial3D).albedo_texture == null:
				var c := (material as StandardMaterial3D).albedo_color
				why = "flat %s (%.2f %.2f %.2f)%s" % [material.resource_name, c.r, c.g, c.b, " vertex colours" if (material as StandardMaterial3D).vertex_color_use_as_albedo else ""]
			if why == "":
				continue
			counts.plain += 1
			var key := "%s | %s" % [_owner_of(node), why]
			plain[key] = int(plain.get(key, 0)) + 1
	print("SCAN %d meshes, %d multimeshes, %d plain surfaces" % [counts.meshes, counts.multimeshes, counts.plain])
	var keys := plain.keys()
	keys.sort()
	for key: String in keys:
		print("PLAIN %s  x%d" % [key, plain[key]])


# The nearest ancestor that says what a thing is: a scene file, a script, else the node path's
# first three names.
func _owner_of(node: Node) -> String:
	var at := node
	while at and at != main:
		if at.scene_file_path != "":
			return at.scene_file_path.get_file() + "/" + String(node.name)
		var script: Script = at.get_script()
		if script and at != node:
			return script.resource_path.get_file() + ":" + String(at.name) + "/" + String(node.name)
		at = at.get_parent()
	return String(main.get_path_to(node))


func _print_tree(node: Node, depth: int) -> void:
	if depth > 4:
		return
	var script: Script = node.get_script()
	var n := node.get_child_count()
	print("TREE %s%s [%s%s] %s" % ["  ".repeat(depth), node.name, node.get_class(), (" " + script.resource_path.get_file()) if script else "", ("%d children" % n) if n > 12 else ""])
	if n > 12 and depth > 1:
		return
	for child in node.get_children():
		_print_tree(child, depth + 1)
