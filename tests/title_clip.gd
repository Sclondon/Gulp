extends SceneTree
## Clipping on the title, measured: how many points of each of the helmet's two cables lie inside
## the computer's housings, its monitor or its bench (each part's own box, 1 cm in from its faces),
## and how deep the deepest is. Headless:
##   godot --headless --path . --audio-driver Dummy -s res://tests/title_clip.gd -- --title
## (Boxes, so a hollow or rounded part reads fuller than it is: a hit here is a lead, not a proof.)

var main: Node
var _frames := 0


func _initialize() -> void:
	main = (load("res://main.tscn") as PackedScene).instantiate()
	root.add_child(main)


func _process(_delta: float) -> bool:
	_frames += 1
	if _frames % 60 != 0:
		return false
	var title: Node3D = main.get("title")
	var boat: Node3D = title.get("boat")
	var solids: Array[MeshInstance3D] = []
	for each in boat.get_children():
		var n := String(each.name)
		if each.scene_file_path.ends_with("control_panel.glb") or n.contains("Monitor") or n.contains("Bench") or n.contains("Stool"):
			for m in [each] + each.find_children("*", "MeshInstance3D", true, false):
				if m is MeshInstance3D:
					solids.append(m)
	var cables: Array = title.get("_cables")
	for k in cables.size():
		var hits := {}
		var deepest := 0.0
		var total := 0
		for mesh: MeshInstance3D in (cables[k] as Node3D).find_children("*", "MeshInstance3D", true, false) + ([cables[k]] if cables[k] is MeshInstance3D else []):
			for s in mesh.mesh.get_surface_count():
				var points: PackedVector3Array = mesh.mesh.surface_get_arrays(s)[Mesh.ARRAY_VERTEX]
				for p in points:
					total += 1
					var world := mesh.global_transform * p
					for solid in solids:
						var local := solid.global_transform.affine_inverse() * world
						var box := solid.get_aabb().grow(-0.01 / maxf(solid.global_transform.basis.get_scale().x, 0.001))
						if box.has_point(local):
							var name := String(solid.get_parent().name) + "/" + String(solid.name)
							hits[name] = int(hits.get(name, 0)) + 1
							var inside := minf(minf(local.x - box.position.x, box.end.x - local.x), minf(minf(local.y - box.position.y, box.end.y - local.y), minf(local.z - box.position.z, box.end.z - local.z)))
							deepest = maxf(deepest, inside * solid.global_transform.basis.get_scale().x)
		print("CABLE %d (t=%ds): %d of %d points inside %s, deepest %.3f m" % [k, _frames / 60, hits.values().reduce(func(a, b): return a + b, 0), total, hits, deepest])
	return _frames >= 240
