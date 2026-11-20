extends SceneTree
## Writes what each point of a creature's baked models is into those models, for its motion family
## (scripts/motion.gd, GameCommon `godot/motion-families`). Headless is fine:
##
##   godot --headless --path . --audio-driver Dummy -s res://tools/motion_labels.gd -- [--components=<folder>,...]
##
## For every component one of whose shaders has a motion spec (`baked/<shader>_motion.gd` beside that
## shader, which may be another component's) it makes the component as the
## bake did (each baked variant, its far model too), finds which baked mesh surfaces wear that shader,
## asks the spec's `label()` about each vertex (its position, normal, UV, UV2 and colour at rest, and
## the material's settings) and stores the answer: CUSTOM0.z the part, CUSTOM0.w weight 1, CUSTOM1
## weights 2..5, CUSTOM2 its own point and weight 6, CUSTOM3 its own way and weight 7 (all floats). The
## baked meshes are saved over themselves (CUSTOM0.xy, the paint's place, is kept). Run it again after
## changing a spec's label() or re-baking (tools/bake_looks.gd). Prints `LABELS <component> ...`.

var _only: PackedStringArray = []


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--components="):
			_only = arg.get_slice("=", 1).split(",")
	_run.call_deferred()


func _run() -> void:
	BakedLook.families = false
	for folder in DirAccess.get_directories_at("res://creatures"):
		if not _only.is_empty() and not _only.has(folder):
			continue
		var dir := "res://creatures/%s/baked" % folder
		if not DirAccess.dir_exists_absolute(dir):
			continue
		for file in DirAccess.get_files_at(dir):
			file = file.trim_suffix(".remap")
			if not file.ends_with("look.res"):
				continue
			var script_name := folder if file == "look.res" else file.trim_suffix("_look.res")
			var script_path := "res://creatures/%s/%s.gd" % [folder, script_name]
			# (only where one of its shaders has a spec: a shader may be another folder's, as the
			# leviathan and the sea serpent wear the sea monster's)
			var info: Dictionary = (load(dir.path_join(file)) as Resource).get_meta(&"look", {})
			var any := false
			for own: String in info.get("shaders", {}):
				if Motion.spec_of(own) != null:
					any = true
			if any and ResourceLoader.exists(script_path):
				await _label_component(script_path, dir.path_join(file))
	quit()


func _label_component(script_path: String, index_path: String) -> void:
	var info: Dictionary = (load(index_path) as Resource).get_meta(&"look", {})
	var script: GDScript = load(script_path)
	var own_of := {}
	for own: String in info.get("shaders", {}):
		own_of[info.shaders[own]] = own
	# baked mesh path -> {surface: [material, spec]}
	var found := {}
	for v: Dictionary in info.get("variants", []):
		var look: Node3D = script.new()
		for k: String in v.sets:
			look.set(k, v.sets[k])
		if &"game" in look:
			look.set(&"game", true)
		if &"cartoon_eyes" in look:
			look.set(&"cartoon_eyes", 1.0)
		if int(v.seed) >= 0 and &"pattern_seed" in look:
			look.set(&"pattern_seed", int(v.seed))
		var holder := Node3D.new()
		holder.visible = false
		root.add_child(holder)
		BakedLook.apply(look)
		holder.add_child(look)
		await process_frame
		await process_frame
		_collect(look, own_of, found)
		if &"low" in look:
			look.set(&"low", true)
			if look.has_method(&"step"):
				look.call(&"step", Vector3.ZERO, 0.016)
			await process_frame
			await process_frame
			_collect(look, own_of, found)
		holder.queue_free()
		await process_frame
	var n_meshes := 0
	var n_points := 0
	for mesh_path: String in found:
		n_points += _label_mesh(mesh_path, found[mesh_path])
		n_meshes += 1
	print("LABELS %s: %d meshes, %d points" % [script_path.get_file().get_basename(), n_meshes, n_points])


func _collect(look: Node3D, own_of: Dictionary, found: Dictionary) -> void:
	for mi: MeshInstance3D in look.find_children("*", "MeshInstance3D", true, false):
		if mi.mesh == null or not mi.mesh.resource_path.contains("/baked/"):
			continue
		for s in mi.mesh.get_surface_count():
			var m := mi.get_active_material(s)
			if not (m is ShaderMaterial) or (m as ShaderMaterial).shader == null:
				continue
			var own: String = own_of.get((m as ShaderMaterial).shader.resource_path, "")
			if own == "":
				continue
			var spec := Motion.spec_of(own)
			if spec == null:
				continue
			if not found.has(mi.mesh.resource_path):
				found[mi.mesh.resource_path] = {}
			if not found[mi.mesh.resource_path].has(s):
				found[mi.mesh.resource_path][s] = [m, spec, load(own)]


func _label_mesh(mesh_path: String, surfaces: Dictionary) -> int:
	var mesh: ArrayMesh = load(mesh_path)
	var out := ArrayMesh.new()
	var points := 0
	for s in mesh.get_surface_count():
		var arrays := mesh.surface_get_arrays(s)
		var fmt := mesh.surface_get_format(s)
		var keep_flags := fmt & Mesh.ARRAY_FLAG_COMPRESS_ATTRIBUTES
		var custom0: PackedFloat32Array = arrays[Mesh.ARRAY_CUSTOM0]
		var count: int = (arrays[Mesh.ARRAY_VERTEX] as PackedVector3Array).size()
		# (CUSTOM0 was the atlas alone, two floats a point, or already four from an earlier run)
		var stride := custom0.size() / count
		var c0 := PackedFloat32Array()
		var c1 := PackedFloat32Array()
		var c2 := PackedFloat32Array()
		var c3 := PackedFloat32Array()
		for arr: PackedFloat32Array in [c0, c1, c2, c3]:
			arr.resize(count * 4)
		for i in count:
			c0[i * 4] = custom0[i * stride]
			c0[i * 4 + 1] = custom0[i * stride + 1]
		if surfaces.has(s):
			var material: ShaderMaterial = surfaces[s][0]
			var spec: GDScript = surfaces[s][1]
			var own: Shader = surfaces[s][2]
			var defaults := {}
			for u: Dictionary in own.get_shader_uniform_list():
				defaults[StringName(u.name)] = RenderingServer.shader_get_parameter_default(own.get_rid(), u.name)
			var old := func(name: StringName) -> Variant:
				var v: Variant = material.get_shader_parameter(name)
				return v if v != null else defaults.get(name)
			var pos: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var nor: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
			var uv: PackedVector2Array = arrays[Mesh.ARRAY_TEX_UV] if arrays[Mesh.ARRAY_TEX_UV] != null else PackedVector2Array()
			var uv2: PackedVector2Array = arrays[Mesh.ARRAY_TEX_UV2] if arrays[Mesh.ARRAY_TEX_UV2] != null else PackedVector2Array()
			var col: PackedColorArray = arrays[Mesh.ARRAY_COLOR] if arrays[Mesh.ARRAY_COLOR] != null else PackedColorArray()
			for i in count:
				var got: Dictionary = spec.call(&"label", pos[i], nor[i] if i < nor.size() else Vector3.UP,
						uv[i] if i < uv.size() else Vector2.ZERO, uv2[i] if i < uv2.size() else Vector2.ZERO,
						col[i] if i < col.size() else Color(1, 1, 1, 1), old)
				var w: Array = got.get("w", [])
				var wf := func(k: int) -> float: return float(w[k]) if k < w.size() else 0.0
				var p: Vector3 = got.get("point", Vector3.ZERO)
				var way: Vector3 = got.get("way", Vector3.ZERO)
				c0[i * 4 + 2] = float(got.get("part", 0))
				c0[i * 4 + 3] = wf.call(0)
				for k in 4:
					c1[i * 4 + k] = wf.call(1 + k)
				c2[i * 4] = p.x
				c2[i * 4 + 1] = p.y
				c2[i * 4 + 2] = p.z
				c2[i * 4 + 3] = wf.call(5)
				c3[i * 4] = way.x
				c3[i * 4 + 1] = way.y
				c3[i * 4 + 2] = way.z
				c3[i * 4 + 3] = wf.call(6)
			points += count
		arrays[Mesh.ARRAY_CUSTOM0] = c0
		arrays[Mesh.ARRAY_CUSTOM1] = c1
		arrays[Mesh.ARRAY_CUSTOM2] = c2
		arrays[Mesh.ARRAY_CUSTOM3] = c3
		var flags := keep_flags
		for k in 4:
			flags |= Mesh.ARRAY_CUSTOM_RGBA_FLOAT << (Mesh.ARRAY_FORMAT_CUSTOM0_SHIFT + k * Mesh.ARRAY_FORMAT_CUSTOM_BITS)
		out.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays, [], {}, flags)
		out.surface_set_name(s, mesh.surface_get_name(s))
		var m := mesh.surface_get_material(s)
		if m:
			out.surface_set_material(s, m)
	out.resource_name = mesh.resource_name
	ResourceSaver.save(out, mesh_path, ResourceSaver.FLAG_COMPRESS)
	return points
