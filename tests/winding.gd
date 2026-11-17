extends SceneTree
## Inside-out check for every mesh the game draws: the fish (Salmon Run 2's, built by
## scripts/world/props.gd) and the two models (the moon jelly and the rocks).
##
##   godot --headless --path . --audio-driver Dummy -s res://tests/winding.gd
##
## For each mesh: the share of its triangles whose winding (Godot's front faces wind clockwise
## as seen, so a triangle a, b, c faces along (c - a) x (b - a)) agrees with its normals, and
## its volume as its faces enclose it (positive: they face outwards). A solid passes if nearly
## all its triangles agree and its volume is positive; the jelly is thin two-sided sheets, so
## only its winding against its normals is judged. Prints a WINDING line each and PASSED or FAILED.

const Props := preload("res://scripts/world/props.gd")


func _initialize() -> void:
	var bad := 0
	var meshes := {
		"sardine": Props.sardine(),
		"small fish": Props.small_fish(Color.WHITE, Color.WHITE),
		"smolt": Props.salmon("smolt"),
		"salmon": Props.salmon("ocean"),
		"tuna": Props.tuna(),
		"shark": Props.shark_whole(),
	}
	for name: String in meshes:
		bad += _judge(name, meshes[name], true)
	bad += _judge("rocks (sea_floor.glb)", _model("res://models/sea_floor.glb"), true)
	bad += _judge("moon jelly (moon_jelly.glb)", _model("res://models/moon_jelly.glb"), false)
	print("WINDING PASSED" if bad == 0 else "WINDING FAILED (%d)" % bad)
	quit()


func _model(path: String) -> Mesh:
	var made := (load(path) as PackedScene).instantiate()
	var mesh := (made.find_children("*", "MeshInstance3D", true, false)[0] as MeshInstance3D).mesh
	made.free()
	return mesh


func _judge(name: String, mesh: Mesh, solid: bool) -> int:
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
	var share := 100.0 * agree / maxf(count, 1.0)
	var good := share >= 99.0 and (volume > 0.0 or not solid)
	print("WINDING %s: %d triangles, winding agrees with normals %.1f%%, volume %.4f: %s" % [name, count, share, volume, "ok" if good else "BAD"])
	return 0 if good else 1
