class_name BakedLook
## Draws a creature component from its baked paint (GameCommon `baked-look`; the user, 2026-11-19:
## "cant you use the shader to generate the textures? We dont need the shader for the color textures
## after its already made tho right", and baked textures "should be standard for most game objects").
##
## A component's markings were computed in its shader every pixel, every frame; `tools/bake_looks.gd`
## renders them once into a picture (its paint, and its glow where it glows), lays each model's
## surface out flat for it (a second set of UVs in CUSTOM0), and writes a copy of the shader that
## keeps the component's own vertex code (its swimming, jaw, fins: everything that moves) and reads
## the picture in place of the markings. Its lighting is worked out per vertex (`vertex_lighting`).
## Both make the program a browser compiles for it several times cheaper (tools/PERF.md, "Shader
## programs"). The component itself is unchanged: `apply(look)` swaps its meshes and its shader as it
## makes them. Without a `baked/look.res` beside the component's script nothing changes.
##
## Each component's `baked/look.res` holds (as metadata `look`): `shaders` (the component's shader
## path -> its baked copy), `meshes` (a mesh's key, see `key_of`, -> the baked mesh), `caches` (where
## the component keeps its loaded meshes, see `prime`), and `variants`,
## each {sets: the component's settings it was baked with, seed: its `pattern_seed` or -1, paint,
## glow (or ""), glow_scale, roughness, specular}.

## A component's index beside its script: baked/look.res for the script named as its folder,
## baked/<script>_look.res for another in the same folder.
static func index_name(script_name: String, folder_name := "") -> String:
	return "look.res" if folder_name == "" or script_name == folder_name else script_name + "_look.res"

static var _infos := {}
static var _loaded := {}
## Whether a component with a motion spec wears its family shader (scripts/motion.gd); false keeps the
## baked copy of its own shader (tests/motion_compare.gd draws both).
static var families := true


## Whether a component (by its script) has a baked look.
static func has_look(script: Script) -> bool:
	return not _info(script).is_empty()


## Draws `look` (a creature component, in the tree or about to be) from its baked paint: its meshes
## and shader now, and any model it makes later (its far model, made when it is first far off).
static func apply(look: Node3D) -> void:
	if look == null or look.get_script() == null:
		return
	var info := _info(look.get_script())
	if info.is_empty():
		return
	var variant := _variant(look, info)
	if variant.is_empty():
		return
	_prime(look.get_script(), info)
	look.set_meta(&"baked_variant", variant)
	look.set_meta(&"baked_families", families)
	if not look.child_entered_tree.is_connected(_on_child.bind(look)):
		look.child_entered_tree.connect(_on_child.bind(look))
	_swap_all(look, info, variant)


## Swaps everything under `look` again (after it changed its own settings, e.g. a new pattern).
static func refresh(look: Node3D) -> void:
	if look == null or look.get_script() == null or not look.has_meta(&"baked_variant"):
		return
	var info := _info(look.get_script())
	var variant := _variant(look, info)
	look.set_meta(&"baked_variant", variant)
	_swap_all(look, info, variant)
	# (and the motion's numbers again, from its new settings)
	var done := {}
	for mi: MeshInstance3D in look.find_children("*", "MeshInstance3D", true, false):
		for m: Material in [mi.material_override] + range(mi.get_surface_override_material_count()).map(mi.get_surface_override_material):
			if m is ShaderMaterial and m.has_meta(&"motion_own") and not done.has(m):
				done[m] = true
				_swap_material(m, info, variant, true)


## A mesh's key: how many surfaces, the first surface's vertex and index counts, its box (rounded).
static func key_of(mesh: Mesh) -> String:
	if mesh == null or mesh.get_surface_count() == 0:
		return ""
	var box := mesh.get_aabb()
	return "%d:%d:%d:%.3f,%.3f,%.3f:%.3f,%.3f,%.3f" % [mesh.get_surface_count(), mesh.surface_get_array_len(0),
			mesh.surface_get_array_index_len(0), box.position.x, box.position.y, box.position.z, box.size.x, box.size.y, box.size.z]


## Every baked shader, mesh and picture of every component under `folder` (for the loading screen
## to load and compile up front): {shaders: [paths], meshes: [paths], pictures: [paths]}.
static func everything(folder := "res://creatures") -> Dictionary:
	var out := {"shaders": [], "meshes": [], "pictures": []}
	var indexes: PackedStringArray = []
	for name in DirAccess.get_directories_at(folder):
		var dir := "%s/%s/baked" % [folder, name]
		if not DirAccess.dir_exists_absolute(dir):
			continue
		for file in DirAccess.get_files_at(dir):
			file = file.trim_suffix(".remap")
			if file.ends_with("look.res"):
				indexes.append(dir.path_join(file))
	if families:
		out.shaders.append_array(Motion.every_family())
	for path in indexes:
		var info: Dictionary = (load(path) as Resource).get_meta(&"look", {})
		for s: String in info.get("shaders", {}).values():
			out.shaders.append(s)
		for m: String in info.get("meshes", {}).values():
			out.meshes.append(m)
		for v: Dictionary in info.get("variants", []):
			out.pictures.append(v.paint)
			if v.glow != "":
				out.pictures.append(v.glow)
			if v.get("back", "") != "":
				out.pictures.append(v.back)
	return out


## Puts the baked meshes in the component's own cache of loaded meshes (its static `_meshes` and the
## like, as the bake found them), so that it never loads its own models: it takes the baked ones.
static func prime(script: Script) -> void:
	_prime(script, _info(script))


static var _primed := {}


static func _prime(script: Script, info: Dictionary) -> void:
	if _primed.has(script):
		return
	_primed[script] = true
	for c: Dictionary in info.get("caches", []):
		var mesh := _load(c.mesh)
		if c.key == null:
			script.set(c.var, mesh)
		else:
			var held: Variant = script.get(c.var)
			if held is Dictionary:
				(held as Dictionary)[c.key] = mesh


static func _info(script: Script) -> Dictionary:
	if _infos.has(script):
		return _infos[script]
	var info := {}
	var dir := script.resource_path.get_base_dir()
	var path := dir.path_join("baked").path_join(index_name(script.resource_path.get_file().get_basename(), dir.get_file()))
	if ResourceLoader.exists(path):
		info = (load(path) as Resource).get_meta(&"look", {})
	_infos[script] = info
	return info


# The variant baked with the settings `look` has now (its first, if none matches).
static func _variant(look: Node3D, info: Dictionary) -> Dictionary:
	var variants: Array = info.get("variants", [])
	if variants.is_empty():
		return {}
	var seed := -1
	var seeds := 0
	for v: Dictionary in variants:
		if int(v.seed) >= 0:
			seeds += 1
	if seeds > 0 and &"pattern_seed" in look:
		seed = int(look.get(&"pattern_seed"))
	var best: Dictionary = {}
	var matching: Array = []
	for v: Dictionary in variants:
		var sets: Dictionary = v.sets
		var ok := true
		for k: String in sets:
			if not (StringName(k) in look) or look.get(StringName(k)) != sets[k]:
				ok = false
				break
		if ok:
			matching.append(v)
	if matching.is_empty():
		return variants[0]
	# (the most particular first: one baked with no settings matches anything)
	var most := -1
	for v: Dictionary in matching:
		most = maxi(most, (v.sets as Dictionary).size())
	matching = matching.filter(func(v: Dictionary) -> bool: return (v.sets as Dictionary).size() == most)
	best = matching[0]
	if seed >= 0:
		var with_seed: Array = matching.filter(func(v: Dictionary) -> bool: return int(v.seed) >= 0)
		if not with_seed.is_empty():
			best = with_seed[posmod(seed, with_seed.size())]
			for v: Dictionary in with_seed:
				if int(v.seed) == seed:
					best = v
	return best


static func _on_child(node: Node, look: Node3D) -> void:
	if not look.has_meta(&"baked_variant"):
		return
	var info := _info(look.get_script())
	var variant: Dictionary = look.get_meta(&"baked_variant")
	var wear: bool = look.get_meta(&"baked_families", true)
	_swap_under_as(node, info, variant, wear)
	# (and again before the frame is drawn: some components give a mesh its model only after
	# adding it)
	(func() -> void:
		if is_instance_valid(node):
			_swap_under_as(node, info, variant, wear)).call_deferred()


# (as _swap_under, wearing the motion families or not as the look was first dressed)
static func _swap_under_as(node: Node, info: Dictionary, variant: Dictionary, wear: bool) -> void:
	var was := families
	families = wear
	_swap_under(node, info, variant)
	families = was


static func _swap_all(look: Node3D, info: Dictionary, variant: Dictionary) -> void:
	# (only where a baked mesh is drawn: a model the bake did not see, a full model in a game that
	# shows those, keeps its own shader)
	_swap_under(look, info, variant)


static func _swap_under(node: Node, info: Dictionary, variant: Dictionary) -> void:
	if node is MeshInstance3D:
		_swap_mesh(node, info, variant)
	for child in node.find_children("*", "MeshInstance3D", true, false):
		_swap_mesh(child, info, variant)


static func _swap_mesh(mi: MeshInstance3D, info: Dictionary, variant: Dictionary) -> void:
	if mi.mesh == null:
		return
	var meshes: Dictionary = info.get("meshes", {})
	var key := key_of(mi.mesh)
	if meshes.has(key):
		mi.mesh = _load(meshes[key])
	elif not mi.has_meta(&"baked"):
		# (a mesh not baked, already baked, or not a creature's: left as it is)
		var already := false
		for p: String in meshes.values():
			if mi.mesh.resource_path == p:
				already = true
		if not already:
			return
	mi.set_meta(&"baked", true)
	if mi.material_override is ShaderMaterial:
		_swap_material(mi.material_override, info, variant)
	for s in mi.get_surface_override_material_count():
		var m := mi.get_surface_override_material(s)
		if m is ShaderMaterial:
			_swap_material(m, info, variant)
	for s in mi.mesh.get_surface_count():
		var m := mi.mesh.surface_get_material(s)
		if m is ShaderMaterial:
			_swap_material(m, info, variant)


static func _swap_material(material: ShaderMaterial, info: Dictionary, variant: Dictionary, again := false) -> void:
	if material.shader == null:
		return
	var shaders: Dictionary = info.get("shaders", {})
	var path := material.shader.resource_path
	if shaders.has(path):
		# (its motion from a shared family shader where it has a spec: GameCommon motion-families)
		var spec: GDScript = Motion.spec_of(path) if families else null
		if spec != null:
			material.set_meta(&"motion_own", path)
			Motion.wear(material, material.shader, spec)
		else:
			material.shader = _load(shaders[path])
	elif material.has_meta(&"motion_own"):
		if again:
			var own: String = material.get_meta(&"motion_own")
			Motion.wear(material, _load(own), Motion.spec_of(own))
	elif not shaders.values().has(path):
		return
	material.set_shader_parameter(&"baked_paint", _load(variant.paint))
	if variant.glow != "":
		material.set_shader_parameter(&"baked_glow", _load(variant.glow))
	if variant.get("back", "") != "":
		material.set_shader_parameter(&"baked_back", _load(variant.back))
	material.set_shader_parameter(&"baked_glow_scale", float(variant.get("glow_scale", 1.0)))
	material.set_shader_parameter(&"baked_roughness", float(variant.get("roughness", 0.5)))
	material.set_shader_parameter(&"baked_specular", float(variant.get("specular", 0.5)))


static func _load(path: String) -> Resource:
	if not _loaded.has(path):
		_loaded[path] = load(path)
	return _loaded[path]
