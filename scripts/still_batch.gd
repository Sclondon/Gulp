class_name StillBatch
## Merges the parts of a model that never move against each other into one mesh a material
## ("static batching"): a model of many pieces (the shrimp boat: about 45) was one draw call a
## piece, and a phone's browser pays dearly for each (tools/PERF.md, "Draw calls").
## The look is the same: the same triangles, the same materials. What moves is named in `moving`
## (it and everything under it are left as they are); skinned meshes, meshes with blend shapes,
## hidden ones and anything that is not triangles are left too. The merged pieces are hidden, not
## freed (markers and names are still found by them); the merged meshes are put under `root`, so
## they move with it.


## Returns how many pieces were merged, into how many meshes.
static func merge(root: Node3D, moving: Array = []) -> Vector2i:
	var tools := {}
	var paints := {}
	var merged := 0
	for mesh: MeshInstance3D in root.find_children("*", "MeshInstance3D", true, false):
		if mesh.mesh == null or not mesh.visible or mesh.skin != null:
			continue
		if mesh.mesh is ArrayMesh and (mesh.mesh as ArrayMesh).get_blend_shape_count() > 0:
			continue
		var still := true
		var place := Transform3D.IDENTITY
		var up: Node = mesh
		while up and up != root:
			if up in moving or not (up is Node3D) or not (up as Node3D).visible or up is Skeleton3D or up is BoneAttachment3D:
				still = false
				break
			place = (up as Node3D).transform * place
			up = up.get_parent()
		if not still or up != root:
			continue
		var whole := true
		for s in mesh.mesh.get_surface_count():
			if mesh.mesh.surface_get_primitive_type(s) != Mesh.PRIMITIVE_TRIANGLES:
				whole = false
		if not whole:
			continue
		for s in mesh.mesh.get_surface_count():
			var paint: Material = mesh.material_override
			if paint == null:
				paint = mesh.get_surface_override_material(s)
			if paint == null:
				paint = mesh.mesh.surface_get_material(s)
			# (by material and by which arrays it has: SurfaceTool joins only like with like)
			var key := "%d %d" % [paint.get_instance_id() if paint else 0, mesh.mesh.surface_get_format(s) & (Mesh.ARRAY_FORMAT_CUSTOM_BASE - 1)]
			if not tools.has(key):
				var st := SurfaceTool.new()
				st.begin(Mesh.PRIMITIVE_TRIANGLES)
				tools[key] = st
				paints[key] = paint
			(tools[key] as SurfaceTool).append_from(mesh.mesh, s, place)
		mesh.visible = false
		merged += 1
	for key: String in tools:
		var one := MeshInstance3D.new()
		one.name = "Still"
		one.mesh = (tools[key] as SurfaceTool).commit()
		one.material_override = paints[key]
		one.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		root.add_child(one)
	return Vector2i(merged, tools.size())
