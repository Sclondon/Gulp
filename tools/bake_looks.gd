extends SceneTree
## Bakes each creature component's markings into pictures, for `BakedLook` (scripts/baked_look.gd;
## GameCommon `baked-look`). A window (headless draws nothing):
##
##   godot --path . --audio-driver Dummy --resolution 320x240 -s res://tools/bake_looks.gd -- \
##     [--kinds=garibaldi,orca,...] [--components=garibaldi,...] [--seeds=3] [--plan=res://plan.json]
##
## `--imports` (headless will do) only writes the import settings of every baked picture already there
## (lossy, mipmaps): for a game that installed baked components from GameCommon; then `--import`.
##
## Which components and settings: `--plan` (a JSON object, component script -> list of settings
## dictionaries), or every kind in the game's Species table with its `set` (Gulp), or every
## component in res://creatures as it comes; `--kinds`/`--components` narrow it. For each component and each distinct set of settings
## (a "variant"; `pattern_seed` components get `--seeds` of them):
##
## 1. The component is made as a game makes it (`game` on where it has one, `cartoon_eyes` 1, its
##    settings) with its far model too, and its meshes are found.
## 2. Each mesh gets a second set of UVs laid out flat (xatlas, Godot's `lightmap_unwrap`; small
##    separate pieces such as eyes given up to nine times their share), packed into one picture per
##    variant: the models it shows near side by side in the top four fifths, its far model in a small
##    square below. They go in CUSTOM0; UV2 keeps what it was. Saved as `baked/<component>_<n>_<key>.res`,
##    and where the component keeps its loaded meshes (its static `_meshes`) is noted, so that
##    BakedLook can hand it the baked ones before it loads its own (`baked/primed.txt` lists the
##    models a web build can then leave out).
## 3. The component's shader is rewritten twice. The BAKE copy runs its own vertex code at rest, then
##    puts each point where its flat UVs say (`POSITION`), and runs its own fragment code unlit, with
##    `VIEW` along the normal (no rim) and `FRONT_FACING` true (false for a sheet's back, `_back.png`); a `bake_pass` setting chooses what
##    comes out (0 colour, 1 alpha/roughness/specular, 2 emission). The GAME copy keeps the vertex
##    code, gains `vertex_lighting`, and draws its fragment from the pictures
##    (`baked/<shader>_baked.gdshader`).
## 4. Each pass is drawn into a SubViewport at four times the size and shrunk, the gaps between
##    islands are filled from their edges (so mipmaps do not bleed the background in), and the
##    colour is saved as `baked/<variant>_paint.png` (its alpha: the shader's alpha, or 0 where the
##    back of the mouth is cut away when it opens). Only a component with its own `glow` setting
##    keeps its emission as `_glow.png`; any other emission (an eye's glint) is added to the colour.
##    Pictures are 128 x 160 for models under half a metre, 256 x 320 to 4 m, 512 x 640 beyond.
## 5. `baked/look.res` indexes it all.
##
## Components whose shaders have their own `light()` (the big jellies) are left alone: their look is
## in the light function. Prints `BAKED <component> <variant> ...` per variant.

const BIG := 0.8
## Each pass is drawn this many times the picture's size and shrunk (see _draw_pass).
const SUPER := 4
## Components whose colour is alive, so kept as they are: the squids' colour cells open and
## flash (`colour_phase`), the comb jelly's combs shimmer along its rows (`phase`), the anglerfish's
## lure pulses (`lure`), the reef-back's lights pulse (`pulse`), the firefly squid's lights.
const KEEP := ["humboldt_squid", "giant_squid", "firefly_squid", "comb_jelly", "deep_anglerfish", "reef_back"]
## How much of a picture's colour (on average, 0..1 a channel) may be lost to its size before the
## size doubles (see _bake_component).
const DETAIL := 0.05

var _only_kinds: PackedStringArray = []
var _only_components: PackedStringArray = []
var _seeds := 4
var _plan_file := ""
var _imports_only := false
var _stage: Node3D
var _view: SubViewport
var _camera: Camera3D
var _pad_view: SubViewport
var _pad_rect: TextureRect
var _summary: Array = []
# Each component's picture size, once its first variant has decided it.
var _sizes := {}


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--kinds="):
			_only_kinds = arg.get_slice("=", 1).split(",")
		elif arg.begins_with("--components="):
			_only_components = arg.get_slice("=", 1).split(",")
		elif arg.begins_with("--seeds="):
			_seeds = int(arg.get_slice("=", 1))
		elif arg.begins_with("--plan="):
			_plan_file = arg.get_slice("=", 1)
		elif arg == "--imports":
			_imports_only = true
	_run.call_deferred()


func _run() -> void:
	if _imports_only:
		# (a game that installed baked components: their pictures' import settings, then --import)
		var n := 0
		for folder in DirAccess.get_directories_at("res://creatures"):
			var dir := "res://creatures/%s/baked" % folder
			if not DirAccess.dir_exists_absolute(dir):
				continue
			for file in DirAccess.get_files_at(dir):
				if file.ends_with(".png"):
					_import_settings(dir.path_join(file))
					n += 1
		print("BAKED import settings for %d pictures" % n)
		quit()
		return
	_make_views()
	var plan := _plan()
	for script_path: String in plan:
		await _bake_component(script_path, plan[script_path])
	print("BAKED all: %d components" % plan.size())
	for line: String in _summary:
		print(line)
	quit()


# {component script path: [sets dictionaries]}: from `--plan=<json>` if given; else from the game's
# Species table if it has one (Gulp's: each kind's component and its `set`); else every component in
# res://creatures (its script named as its folder) with its own settings.
func _plan() -> Dictionary:
	var plan := {}
	if _plan_file != "":
		var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(_plan_file))
		if parsed is Dictionary:
			for path: String in parsed:
				plan[path] = parsed[path]
		return plan
	var species: Script = null
	for c: Dictionary in ProjectSettings.get_global_class_list():
		if c["class"] == &"Species":
			species = load(c.path)
	if species == null:
		for folder in DirAccess.get_directories_at("res://creatures"):
			var path := "res://creatures/%s/%s.gd" % [folder, folder]
			if ResourceLoader.exists(path) and (_only_components.is_empty() or _only_components.has(folder)):
				plan[path] = [{}]
		return plan
	var all: Dictionary = species.get_script_constant_map()["ALL"]
	for kind: String in all:
		if not _only_kinds.is_empty() and not _only_kinds.has(kind):
			continue
		if not species.call(&"has", kind):
			continue
		var entry: Dictionary = all[kind]
		if entry.script == "":
			continue
		var path := "res://creatures/%s.gd" % entry.script
		var component := path.get_base_dir().get_file()
		if not _only_components.is_empty() and not _only_components.has(component):
			continue
		var sets: Dictionary = entry.get("set", {}).duplicate()
		if not plan.has(path):
			plan[path] = []
		var known := false
		for s: Dictionary in plan[path]:
			if s == sets:
				known = true
		if not known:
			plan[path].append(sets)
	return plan


func _make_views() -> void:
	_view = SubViewport.new()
	_view.own_world_3d = true
	_view.transparent_bg = true
	_view.msaa_3d = Viewport.MSAA_DISABLED
	_view.render_target_update_mode = SubViewport.UPDATE_DISABLED
	_view.size = Vector2i(256, 320)
	root.add_child(_view)
	_camera = Camera3D.new()
	_camera.position = Vector3(0.0, 0.0, 3.0)
	_camera.near = 0.05
	_camera.far = 50.0
	_view.add_child(_camera)
	_stage = Node3D.new()
	_view.add_child(_stage)
	_pad_view = SubViewport.new()
	_pad_view.transparent_bg = true
	_pad_view.render_target_update_mode = SubViewport.UPDATE_DISABLED
	root.add_child(_pad_view)
	_pad_rect = TextureRect.new()
	_pad_rect.material = ShaderMaterial.new()
	(_pad_rect.material as ShaderMaterial).shader = _pad_shader()
	_pad_view.add_child(_pad_rect)


func _bake_component(script_path: String, variants: Array) -> void:
	var folder := script_path.get_base_dir()
	# (named by its script: a folder may hold two components, as the clownfish's holds its anemone)
	var component := script_path.get_file().get_basename()
	var out_dir := folder.path_join("baked")
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(out_dir))
	var script: GDScript = load(script_path)
	var info := {"shaders": {}, "meshes": {}, "variants": [], "caches": []}
	var shader_lights := false
	var list: Array = []
	for sets: Dictionary in variants:
		if &"pattern_seed" in _probe(script):
			for i in _seeds:
				list.append([sets, i * 97 + 13])
		else:
			list.append([sets, -1])
	var vn := 0
	for item: Array in list:
		var sets: Dictionary = item[0]
		var seed: int = item[1]
		var look: Node3D = script.new()
		for k: String in sets:
			look.set(k, sets[k])
		if &"game" in look:
			look.set(&"game", true)
		if &"cartoon_eyes" in look:
			look.set(&"cartoon_eyes", 1.0)
		if seed >= 0:
			look.set(&"pattern_seed", seed)
		var holder := Node3D.new()
		holder.visible = false
		root.add_child(holder)
		holder.add_child(look)
		await process_frame
		await process_frame
		# every mesh it made, and the material each surface wears: as it first shows, and with its
		# far model (some components show it in the same node)
		var found: Array = look.find_children("*", "MeshInstance3D", true, false).map(func(mi: MeshInstance3D) -> Array: return [mi, mi.mesh, false])
		if &"low" in look:
			look.set(&"low", true)
			# (some show their far model only when stepped, as the octopus does)
			if look.has_method(&"step"):
				look.call(&"step", Vector3.ZERO, 0.016)
			await process_frame
			await process_frame
			found.append_array(look.find_children("*", "MeshInstance3D", true, false).map(func(mi: MeshInstance3D) -> Array: return [mi, mi.mesh, true]))
		var parts: Array = []
		var had := {}
		for pair: Array in found:
			var mi: MeshInstance3D = pair[0]
			var mesh: Mesh = pair[1]
			if mesh == null or had.has(mesh):
				continue
			had[mesh] = true
			var mats: Array = []
			var any := false
			for s in mesh.get_surface_count():
				var m: Material = mi.material_override
				if m == null:
					m = mi.get_active_material(s)
				mats.append(m)
				if m is ShaderMaterial and (m as ShaderMaterial).shader and (m as ShaderMaterial).shader.resource_path.begins_with("res://creatures/") and not (m as ShaderMaterial).shader.resource_path.contains("/baked/"):
					any = true
					if (m as ShaderMaterial).shader.code.contains("void light("):
						shader_lights = true
					# (added light that depends on the angle it is seen at, a ghost's glow: not a colour)
					if _render_modes((m as ShaderMaterial).shader.code).has("blend_add"):
						shader_lights = true
			if any:
				parts.append({"node": mi, "mesh": mesh, "materials": mats, "far": pair[2], "area": _area(mesh)})
		if shader_lights or KEEP.has(component):
			print("BAKED %s skipped: its colour changes as it lives, or is light, not paint (its own light(), added light, or KEEP)" % component)
			holder.queue_free()
			return
		if parts.is_empty():
			print("BAKED %s skipped: no mesh wears its shader" % component)
			holder.queue_free()
			return
		# (the models it shows near come first and get the big region; its far model the small one, in
		# the order they were found: as it first shows, then with `low` on. Not by triangles: some far
		# models have more than the game model)
		# (the picture's size by the model's: small fish 128, most 256, the giants 512; small parts
		# such as eyes get more of it than their size, see _atlas_mesh)
		var length: float = (parts[0].mesh as Mesh).get_aabb().get_longest_axis_size()
		var size := 128 if length < 0.5 else (256 if length < 4.0 else 512)
		var name := component if sets.is_empty() else component + "_" + _sets_name(sets)
		if seed >= 0:
			name += "_s%d" % seed
		var baked_meshes: Array = []
		var by_mesh := {}
		for i in parts.size():
			var part: Dictionary = parts[i]
			var key := BakedLook.key_of(part.mesh)
			var mesh_path := "%s/%s_%d_%s.res" % [out_dir, component, i, key.md5_text().substr(0, 8)]
			if not info.meshes.has(key):
				var made := _atlas_mesh(part.mesh, _region(parts, i), size)
				if made == null:
					print("BAKED %s: unwrap failed" % component)
					holder.queue_free()
					return
				ResourceSaver.save(made, mesh_path, ResourceSaver.FLAG_COMPRESS)
				info.meshes[key] = mesh_path
			baked_meshes.append(load(mesh_path))
			by_mesh[part.mesh] = mesh_path
		# the shaders, rewritten
		var bake_materials: Array = []
		var keep_glow := false
		var two_sided := false
		for i in parts.size():
			var mats: Array = []
			for m: Material in parts[i].materials:
				if not (m is ShaderMaterial) or (m as ShaderMaterial).shader == null:
					mats.append(null)
					continue
				var original: Shader = (m as ShaderMaterial).shader
				# (beside its own shader, which several components may share)
				var game_dir := original.resource_path.get_base_dir().path_join("baked")
				DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(game_dir))
				var game_path := "%s/%s_baked.gdshader" % [game_dir, original.resource_path.get_file().get_basename()]
				var whole := _inlined(original.code, original.resource_path.get_base_dir())
				if not info.shaders.has(original.resource_path):
					var text := game_code(whole)
					var f := FileAccess.open(game_path, FileAccess.WRITE)
					f.store_string(text)
					f.close()
					info.shaders[original.resource_path] = game_path
				var bake := ShaderMaterial.new()
				bake.shader = Shader.new()
				bake.shader.code = bake_code(whole)
				for u: Dictionary in original.get_shader_uniform_list():
					var uname: StringName = u.name
					bake.set_shader_parameter(uname, (m as ShaderMaterial).get_shader_parameter(uname))
				for a: StringName in [&"phase", &"curl", &"gape", &"blink", &"flash"]:
					bake.set_shader_parameter(a, 0.0)
				# (a glow that is not the animal's own light, an eye's glint, goes into its colour)
				bake.set_shader_parameter(&"bake_fold", 0 if keeps_glow(whole) else 1)
				if keeps_glow(whole):
					keep_glow = true
				if _function(whole, "fragment").contains("FRONT_FACING"):
					two_sided = true
				bake.set_shader_parameter(&"eye_look", Vector2.ZERO)
				bake.set_shader_parameter(&"cartoon_eyes", 1.0)
				mats.append(bake)
			bake_materials.append(mats)
		# (fine markings get a bigger picture: while drawing at the picture's size loses more than DETAIL
		# of what twice the size shows, on average, it doubles, once at most: the emperor angelfish's yellow
		# and blue stripes came out grey at 128. Decided by the component's first variant.)
		if _sizes.has(component):
			size = _sizes[component]
		else:
			var most := mini(size * 2, 512)
			while size < most:
				var fine := await _draw_pass(baked_meshes, bake_materials, 0, Vector2i(size * 2, int(size * 2 * 1.25)), {})
				var lost := _lost_detail(fine)
				print("BAKED %s detail lost at %d: %.3f" % [component, size, lost])
				if lost < DETAIL:
					break
				size *= 2
			_sizes[component] = size
		var w := size
		var h := int(size * 1.25)
		var colour := await _draw_pass(baked_meshes, bake_materials, 0, Vector2i(w, h), {})
		var data := await _draw_pass(baked_meshes, bake_materials, 1, Vector2i(w, h), {})
		var glow := await _draw_pass(baked_meshes, bake_materials, 2, Vector2i(w, h), {})
		var opened := await _draw_pass(baked_meshes, bake_materials, 0, Vector2i(w, h), {&"gape": 1.0})
		# alpha, roughness, specular: alpha per texel, the others as one average
		var covered := 0
		var rough := 0.0
		var spec := 0.0
		var any_alpha := false
		var max_glow := 0.0
		var cut_any := false
		var cut := Image.create(w, h, false, Image.FORMAT_L8)
		for y in h:
			for x in w:
				var c := colour.get_pixel(x, y)
				if c.a < 0.5:
					continue
				covered += 1
				var d := data.get_pixel(x, y)
				rough += d.g
				spec += d.b
				if d.r < 0.98:
					any_alpha = true
				# (its alpha, and 0 where the back of the mouth is cut away when it opens)
				var open_cut := opened.get_pixel(x, y).a < 0.5
				colour.set_pixel(x, y, Color(c.r, c.g, c.b, 0.0 if open_cut else clampf(d.r, 0.0, 1.0)))
				var g := glow.get_pixel(x, y)
				max_glow = maxf(max_glow, maxf(g.r, maxf(g.g, g.b)))
				if open_cut:
					cut.set_pixel(x, y, Color.WHITE)
					cut_any = true
		rough = rough / maxf(covered, 1)
		spec = spec / maxf(covered, 1)
		# (coverage, to pad from: the colour pass's own, before alpha replaced it)
		var mask := await _draw_pass(baked_meshes, bake_materials, 0, Vector2i(w, h), {})
		colour = _with_alpha(colour, mask, any_alpha or cut_any)
		colour = await _pad(colour, mask)
		var paint_path := "%s/%s_paint.png" % [out_dir, name]
		colour.save_png(ProjectSettings.globalize_path(paint_path))
		_import_settings(paint_path)
		# (a sheet seen from both sides, a ray's wing or a shell, may be another colour behind: its
		# back drawn as a picture of its own)
		var back_path := ""
		if two_sided:
			var back := await _draw_pass(baked_meshes, bake_materials, 0, Vector2i(w, h), {&"bake_back": 1})
			back = await _pad(_with_alpha(back, mask, false), mask)
			back_path = "%s/%s_back.png" % [out_dir, name]
			back.save_png(ProjectSettings.globalize_path(back_path))
			_import_settings(back_path)
		var glow_path := ""
		var glow_scale := 1.0
		if keep_glow and max_glow > 0.004:
			# (emission over 1 is kept by scaling the picture down: `baked_glow_scale` scales it up again)
			glow_scale = maxf(1.0, max_glow * 4.0 / 4.0)
			var gi := Image.create(w, h, false, Image.FORMAT_RGBA8)
			for y in h:
				for x in w:
					if mask.get_pixel(x, y).a < 0.5:
						continue
					var g := glow.get_pixel(x, y)
					gi.set_pixel(x, y, Color(g.r, g.g, g.b, 1.0) if glow_scale == 1.0 else Color(g.r / glow_scale, g.g / glow_scale, g.b / glow_scale, 1.0))
			gi = await _pad(gi, mask)
			glow_path = "%s/%s_glow.png" % [out_dir, name]
			gi.save_png(ProjectSettings.globalize_path(glow_path))
			_import_settings(glow_path)
		for c: Dictionary in _caches(script, by_mesh):
			var known := false
			for had_c: Dictionary in info.caches:
				if had_c.var == c.var and had_c.key == c.key:
					known = true
			if not known:
				info.caches.append(c)
		info.variants.append({"sets": sets, "seed": seed, "paint": paint_path, "glow": glow_path, "back": back_path, "glow_scale": glow_scale,
				"roughness": rough, "specular": spec, "alpha": any_alpha, "cut": cut_any})
		_summary.append("BAKED %s %s %dx%d meshes %d alpha %s glow %.2f cut %s rough %.2f spec %.2f" % [component, name, w, h, parts.size(), any_alpha, max_glow, cut_any, rough, spec])
		print(_summary[-1])
		holder.queue_free()
		await process_frame
		vn += 1
	var index := Resource.new()
	index.set_meta(&"look", info)
	ResourceSaver.save(index, out_dir.path_join(BakedLook.index_name(component, folder.get_file())))
	# (the component's own models that the baked ones stand in for, never loaded once primed: a web
	# build can leave them out, tools/web_excludes.sh)
	var spare: PackedStringArray = []
	for c: Dictionary in info.caches:
		if c.key is String and (c.key as String).ends_with(".glb"):
			spare.append((c.key as String).trim_prefix("res://"))
	var f := FileAccess.open(out_dir.path_join("primed.txt" if component == folder.get_file() else component + "_primed.txt"), FileAccess.WRITE)
	f.store_string("\n".join(spare) + "\n")
	f.close()


# Where the component keeps the meshes it loaded (its static `_meshes` and the like), and which
# baked mesh each entry becomes: BakedLook puts the baked ones there first, so the component never
# loads its own models. [{var, key (null for a plain Mesh variable), mesh}]
func _caches(script: GDScript, by_mesh: Dictionary) -> Array:
	var out := []
	var re := RegEx.create_from_string("(?m)^static var (\\w+)")
	var names: PackedStringArray = []
	var at: Script = script
	while at:
		for m in re.search_all(at.source_code):
			names.append(m.get_string(1))
		at = at.get_base_script()
	for name in names:
		var v: Variant = script.get(name)
		if v is Dictionary:
			for k: Variant in v:
				if v[k] is Mesh and by_mesh.has(v[k]):
					out.append({"var": name, "key": k, "mesh": by_mesh[v[k]]})
		elif v is Mesh and by_mesh.has(v):
			out.append({"var": name, "key": null, "mesh": by_mesh[v]})
	return out


# How a baked picture is imported: lossy (WebP) with mipmaps, never VRAM-compressed (a web build
# for phones carries no VRAM formats). Written once; the next `--import` fills in the rest.
func _import_settings(path: String) -> void:
	var file := ProjectSettings.globalize_path(path + ".import")
	if FileAccess.file_exists(file):
		return
	var f := FileAccess.open(file, FileAccess.WRITE)
	f.store_string("[remap]\n\nimporter=\"texture\"\ntype=\"CompressedTexture2D\"\n\n[params]\n\ncompress/mode=1\ncompress/lossy_quality=0.85\nmipmaps/generate=true\ndetect_3d/compress_to=0\n")
	f.close()


# How much colour a picture loses when drawn at half its size (the mean difference over its covered
# texels between it and it halved and doubled again).
func _lost_detail(fine: Image) -> float:
	var coarse := fine.duplicate() as Image
	coarse.resize(fine.get_width() / 2, fine.get_height() / 2, Image.INTERPOLATE_BILINEAR)
	coarse.resize(fine.get_width(), fine.get_height(), Image.INTERPOLATE_BILINEAR)
	var sum := 0.0
	var n := 0
	for y in fine.get_height():
		for x in fine.get_width():
			var a := fine.get_pixel(x, y)
			if a.a < 0.5:
				continue
			var b := coarse.get_pixel(x, y)
			sum += (absf(a.r - b.r) + absf(a.g - b.g) + absf(a.b - b.b)) / 3.0
			n += 1
	return sum / maxf(n, 1)


func _probe(script: GDScript) -> Node:
	var n: Node = script.new()
	n.queue_free()
	return n


func _triangles(mesh: Mesh) -> int:
	var n := 0
	for s in mesh.get_surface_count():
		var idx: int = mesh.surface_get_array_index_len(s)
		n += (idx if idx > 0 else mesh.surface_get_array_len(s)) / 3
	return n


func _sets_name(sets: Dictionary) -> String:
	var bits: PackedStringArray = []
	for k: String in sets:
		bits.append("%s%s" % [k, str(sets[k]).replace(".", "_")])
	return "_".join(bits)


# Where model `i` goes in the picture (0..1).
func _region(parts: Array, i: int) -> Rect2:
	# (the near models share the top four fifths, side by side by their surface; the far ones get
	# fifth-wide squares along the bottom)
	var near_area := 0.0
	var before := 0.0
	var far_index := 0
	for j in parts.size():
		if not parts[j].far:
			near_area += float(parts[j].area)
			if j < i:
				before += float(parts[j].area)
		elif j < i:
			far_index += 1
	if not parts[i].far:
		return Rect2(before / near_area, 0.0, float(parts[i].area) / near_area, BIG)
	return Rect2(0.2 * float(far_index), BIG, 0.2, 1.0 - BIG)


func _area(mesh: Mesh) -> float:
	var total := 0.0
	for s in mesh.get_surface_count():
		var a := mesh.surface_get_arrays(s)
		var pos: PackedVector3Array = a[Mesh.ARRAY_VERTEX]
		var idx: PackedInt32Array = a[Mesh.ARRAY_INDEX] if a[Mesh.ARRAY_INDEX] != null else PackedInt32Array(range(pos.size()))
		for t in range(0, idx.size(), 3):
			total += (pos[idx[t + 1]] - pos[idx[t]]).cross(pos[idx[t + 2]] - pos[idx[t]]).length() * 0.5
	return maxf(total, 1e-9)



# A copy of `mesh` with flat UVs in CUSTOM0 (packed into `region`), UV2 as it was, no LODs.
# (xatlas keeps positions, normals, UVs, colours and bones but not UV2 or custom channels: each
# vertex's number rides in its colour through the unwrap, and its UV2 and colour come back by it)
func _atlas_mesh(mesh: Mesh, region: Rect2, size: int) -> ArrayMesh:
	var work := ArrayMesh.new()
	var originals: Array = []
	for s in mesh.get_surface_count():
		var arrays := mesh.surface_get_arrays(s)
		originals.append(arrays.duplicate())
		arrays[Mesh.ARRAY_TEX_UV2] = null
		# (each vertex's number in its colour, which the unwrap keeps: 24 bits, exact in 8-bit channels)
		var count: int = (arrays[Mesh.ARRAY_VERTEX] as PackedVector3Array).size()
		var tags := PackedColorArray()
		tags.resize(count)
		for i in count:
			tags[i] = Color8(i & 255, (i >> 8) & 255, (i >> 16) & 255, 255)
		arrays[Mesh.ARRAY_COLOR] = tags
		arrays[Mesh.ARRAY_VERTEX] = _boosted(arrays)
		for c in [Mesh.ARRAY_CUSTOM0, Mesh.ARRAY_CUSTOM1, Mesh.ARRAY_CUSTOM2, Mesh.ARRAY_CUSTOM3]:
			arrays[c] = null
		work.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	var texel := mesh.get_aabb().size.length() / float(size) * 1.6
	var err := work.lightmap_unwrap(Transform3D.IDENTITY, texel)
	if err != OK:
		return null
	var out := ArrayMesh.new()
	var ambiguous := 0
	for s in work.get_surface_count():
		var arrays := work.surface_get_arrays(s)
		var before: Array = originals[mini(s, originals.size() - 1)]
		var atlas: PackedVector2Array = arrays[Mesh.ARRAY_TEX_UV2]
		# (as floats: half floats came out empty in GL Compatibility)
		var custom := PackedFloat32Array()
		custom.resize(atlas.size() * 2)
		for i in atlas.size():
			custom[i * 2] = region.position.x + atlas[i].x * region.size.x
			custom[i * 2 + 1] = region.position.y + atlas[i].y * region.size.y
		arrays[Mesh.ARRAY_CUSTOM0] = custom
		arrays[Mesh.ARRAY_TEX_UV2] = null
		var tags: PackedColorArray = arrays[Mesh.ARRAY_COLOR]
		var from := PackedInt32Array()
		from.resize(atlas.size())
		var old_count: int = (before[Mesh.ARRAY_VERTEX] as PackedVector3Array).size()
		for i in atlas.size():
			var t := tags[i]
			from[i] = t.r8 | (t.g8 << 8) | (t.b8 << 16)
			if from[i] >= old_count:
				ambiguous += 1
				from[i] = 0
		# (positions as they were: the unwrap was given small parts made bigger)
		var old_pos: PackedVector3Array = before[Mesh.ARRAY_VERTEX]
		var pos := PackedVector3Array()
		pos.resize(atlas.size())
		for i in atlas.size():
			pos[i] = old_pos[from[i]]
		arrays[Mesh.ARRAY_VERTEX] = pos
		if before[Mesh.ARRAY_TEX_UV2] != null:
			var old_uv2: PackedVector2Array = before[Mesh.ARRAY_TEX_UV2]
			var uv2 := PackedVector2Array()
			uv2.resize(atlas.size())
			for i in atlas.size():
				uv2[i] = old_uv2[from[i]]
			arrays[Mesh.ARRAY_TEX_UV2] = uv2
		if before[Mesh.ARRAY_COLOR] != null:
			var old_colour: PackedColorArray = before[Mesh.ARRAY_COLOR]
			var colour := PackedColorArray()
			colour.resize(atlas.size())
			for i in atlas.size():
				colour[i] = old_colour[from[i]]
			arrays[Mesh.ARRAY_COLOR] = colour
		else:
			arrays[Mesh.ARRAY_COLOR] = null
		# (positions, normals and UVs compressed as Godot's importer does: half the weight; the game
		# models were imported so, so the values are the same)
		var squeeze := Mesh.ARRAY_FLAG_COMPRESS_ATTRIBUTES
		out.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays, [], {}, (Mesh.ARRAY_CUSTOM_RG_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM0_SHIFT) | squeeze)
		var m := mesh.surface_get_material(mini(s, mesh.get_surface_count() - 1))
		if m:
			out.surface_set_material(s, m)
	if ambiguous > 0:
		push_error("BAKED %d vertices came back from the unwrap without their number" % ambiguous)
	return out


# The positions with each separate piece of the model (an eye, a fin, a tooth: joined by its
# triangles, its seams welded) that has under 3% of the surface scaled up about its middle, so the
# unwrap gives it up to nine times its share of the picture: an eye is a few texels otherwise.
func _boosted(arrays: Array) -> PackedVector3Array:
	var pos: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var idx: PackedInt32Array = arrays[Mesh.ARRAY_INDEX] if arrays[Mesh.ARRAY_INDEX] != null else PackedInt32Array(range(pos.size()))
	# (vertices at one place are one: welded)
	var weld := {}
	var root := PackedInt32Array()
	root.resize(pos.size())
	for i in pos.size():
		var k := pos[i].snappedf(0.00001)
		if not weld.has(k):
			weld[k] = i
		root[i] = weld[k]
	var parent := PackedInt32Array(range(pos.size()))
	var find := func(i: int) -> int:
		while parent[i] != i:
			parent[i] = parent[parent[i]]
			i = parent[i]
		return i
	for t in range(0, idx.size(), 3):
		var a: int = find.call(root[idx[t]])
		for j in [1, 2]:
			var b: int = find.call(root[idx[t + j]])
			if a != b:
				parent[b] = a
	var area := {}
	var mid := {}
	var count := {}
	var total := 0.0
	for t in range(0, idx.size(), 3):
		var c: int = find.call(root[idx[t]])
		var tri := (pos[idx[t + 1]] - pos[idx[t]]).cross(pos[idx[t + 2]] - pos[idx[t]]).length() * 0.5
		area[c] = float(area.get(c, 0.0)) + tri
		total += tri
	for i in pos.size():
		var c: int = find.call(root[i])
		mid[c] = (mid.get(c, Vector3.ZERO) as Vector3) + pos[i]
		count[c] = int(count.get(c, 0)) + 1
	var out := pos.duplicate()
	for i in pos.size():
		var c: int = find.call(root[i])
		var share := float(area.get(c, 0.0)) / maxf(total, 1e-9)
		if share <= 0.0 or share >= 0.03:
			continue
		var k := clampf(sqrt(0.03 / share), 1.0, 3.0)
		var m: Vector3 = (mid[c] as Vector3) / float(count[c])
		out[i] = m + (pos[i] - m) * k
	return out


func _vertex_key(arrays: Array, i: int) -> Variant:
	var p: Vector3 = (arrays[Mesh.ARRAY_VERTEX] as PackedVector3Array)[i]
	var n: Vector3 = (arrays[Mesh.ARRAY_NORMAL] as PackedVector3Array)[i] if arrays[Mesh.ARRAY_NORMAL] != null else Vector3.ZERO
	var u: Vector2 = (arrays[Mesh.ARRAY_TEX_UV] as PackedVector2Array)[i] if arrays[Mesh.ARRAY_TEX_UV] != null else Vector2.ZERO
	return [p.snappedf(0.00001), n.snappedf(0.001), u.snappedf(0.00001)]


# (custom channels the source mesh already had are not expected on creatures)
func _custom_flags(_mesh: Mesh, _s: int) -> int:
	return 0


# A custom channel comes back as bytes or floats.
func _floats(v: Variant, count: int) -> PackedFloat32Array:
	if v is PackedFloat32Array:
		return v
	if v is PackedByteArray:
		return (v as PackedByteArray).to_float32_array()
	var out := PackedFloat32Array()
	out.resize(count * 2)
	return out


# Draws every model with its bake materials, pass `which` chosen, and returns the picture.
# Drawn at SUPER times the size and shrunk (a box filter), so that a shader that fades its fine
# detail by its own screen-space derivatives (fwidth) still draws it: at the picture's own size a
# texel is its "pixel", and spots and scales came out faded to their average.
func _draw_pass(meshes: Array, materials: Array, which: int, size: Vector2i, extra: Dictionary) -> Image:
	_view.size = size * SUPER
	for c in _stage.get_children():
		c.free()
	for i in meshes.size():
		var mi := MeshInstance3D.new()
		mi.mesh = meshes[i]
		mi.custom_aabb = AABB(Vector3(-100, -100, -100), Vector3(200, 200, 200))
		for s in (materials[i] as Array).size():
			var m: ShaderMaterial = materials[i][s]
			if m == null:
				continue
			m.set_shader_parameter(&"bake_pass", which)
			m.set_shader_parameter(&"gape", 0.0)
			m.set_shader_parameter(&"bake_back", 0)
			for k: StringName in extra:
				m.set_shader_parameter(k, extra[k])
			mi.set_surface_override_material(s, m)
		_stage.add_child(mi)
	_view.render_target_update_mode = SubViewport.UPDATE_ONCE
	await RenderingServer.frame_post_draw
	await process_frame
	var big := _view.get_texture().get_image()
	big.convert(Image.FORMAT_RGBA8)
	return _shrink(big, size)


# Halved (2x2 averages) down to `size`, then the colour divided by the coverage (the background is
# clear black, so an edge texel's colour is its covered part's), and covered where over half was.
func _shrink(image: Image, size: Vector2i) -> Image:
	var w := image.get_width()
	var h := image.get_height()
	while w > size.x:
		w /= 2
		h /= 2
		image.resize(w, h, Image.INTERPOLATE_BILINEAR)
	for y in h:
		for x in w:
			var c := image.get_pixel(x, y)
			if c.a <= 0.0:
				continue
			image.set_pixel(x, y, Color(c.r / c.a, c.g / c.a, c.b / c.a, 1.0 if c.a >= 0.5 else 0.0))
	return image


# `colour` with alpha from its own alpha where `use_alpha`, else covered texels opaque; uncovered 0.
func _with_alpha(colour: Image, mask: Image, use_alpha: bool) -> Image:
	var out := Image.create(colour.get_width(), colour.get_height(), false, Image.FORMAT_RGBA8)
	for y in colour.get_height():
		for x in colour.get_width():
			if mask.get_pixel(x, y).a < 0.5:
				continue
			var c := colour.get_pixel(x, y)
			out.set_pixel(x, y, Color(c.r, c.g, c.b, c.a if use_alpha else 1.0))
	return out


# Fills the texels outside the islands from their nearest edge (on the GPU), so that filtering and
# mipmaps never reach the empty background. Uncovered texels keep alpha 0 in `mask`'s sense only.
func _pad(image: Image, mask: Image) -> Image:
	var both := Image.create(image.get_width(), image.get_height(), false, Image.FORMAT_RGBA8)
	both.copy_from(image)
	var cover := ImageTexture.create_from_image(mask)
	var tex := ImageTexture.create_from_image(both)
	var mat := _pad_rect.material as ShaderMaterial
	mat.set_shader_parameter(&"src", tex)
	mat.set_shader_parameter(&"cover", cover)
	_pad_view.size = Vector2i(image.get_width(), image.get_height())
	_pad_rect.texture = tex
	_pad_rect.size = Vector2(image.get_width(), image.get_height())
	_pad_view.render_target_update_mode = SubViewport.UPDATE_ONCE
	await RenderingServer.frame_post_draw
	await process_frame
	var padded := _pad_view.get_texture().get_image()
	padded.convert(Image.FORMAT_RGBA8)
	# (the covered texels exactly as baked: the pad only fills the gaps)
	for y in image.get_height():
		for x in image.get_width():
			if mask.get_pixel(x, y).a >= 0.5:
				padded.set_pixel(x, y, image.get_pixel(x, y))
	return padded


func _pad_shader() -> Shader:
	var s := Shader.new()
	s.code = """shader_type canvas_item;
uniform sampler2D src : filter_nearest;
uniform sampler2D cover : filter_nearest;
void fragment() {
	ivec2 size = textureSize(src, 0);
	ivec2 at = ivec2(UV * vec2(size));
	if (texelFetch(cover, at, 0).a > 0.5) {
		COLOR = texelFetch(src, at, 0);
	} else {
		vec4 sum = vec4(0.0);
		float n = 0.0;
		for (int r = 1; r <= 8; r++) {
			for (int dy = -r; dy <= r; dy++) {
				for (int dx = -r; dx <= r; dx++) {
					if (max(abs(dx), abs(dy)) != r) { continue; }
					ivec2 q = clamp(at + ivec2(dx, dy), ivec2(0), size - 1);
					if (texelFetch(cover, q, 0).a > 0.5) {
						sum += texelFetch(src, q, 0);
						n += 1.0;
					}
				}
			}
			if (n > 0.0) { break; }
		}
		COLOR = n > 0.0 ? sum / n : vec4(0.0);
	}
}
"""
	return s


# ---------------------------------------------------------------------------------------------
# Rewriting a component's shader.

## Whether a shader's emission is the animal's own light (a `glow` setting), kept as a picture of its
## own; any other emission (an eye's glint) is baked into the colour.
static func keeps_glow(code: String) -> bool:
	return RegEx.create_from_string("(?m)^\\s*uniform\\s+float\\s+glow\\b").search(code) != null


## The game's copy: its own vertex code (reading the flat UVs into `bake_uv`), lit per vertex, its
## fragment drawn from the pictures.
static func game_code(code: String) -> String:
	var unshaded := _render_modes(code).has("unshaded")
	var modes := _render_modes(code)
	if not unshaded and not modes.has("vertex_lighting"):
		modes.append("vertex_lighting")
	var blended := false
	for m in modes:
		if m.begins_with("blend_") or m == "depth_prepass_alpha":
			blended = true
	var frag := _function(code, "fragment")
	var writes_alpha := frag.contains("ALPHA")
	var has_glow := keeps_glow(code) and not unshaded
	var cut := frag.contains("discard") and _uniform_names(code).has("gape")
	var out := _set_render_modes(code, modes)
	out = _insert_after_vertex_open(out, "\tbake_uv = CUSTOM0.xy;\n")
	var body := "void fragment() {\n\t// (a sharper mipmap than the usual: the markings were drawn per pixel, sharp, before)\n\tvec4 paint = texture(baked_paint, bake_uv, -1.0);\n"
	if cut:
		body += "\tif (gape > 0.0 && paint.a < 0.5) {\n\t\tdiscard;\n\t}\n"
	if frag.contains("FRONT_FACING"):
		body += "\tif (!FRONT_FACING) {\n\t\tpaint.rgb = texture(baked_back, bake_uv, -1.0).rgb;\n\t}\n"
	body += "\tALBEDO = paint.rgb;\n"
	if has_glow:
		body += "\tEMISSION = texture(baked_glow, bake_uv).rgb * baked_glow_scale;\n"
	if (writes_alpha or blended) and not cut:
		body += "\tALPHA = paint.a;\n"
	if not unshaded:
		body += "\tROUGHNESS = baked_roughness;\n\tSPECULAR = baked_specular;\n"
	body += "}\n"
	out = _replace_function(out, "fragment", body)
	var head := "\n// Drawn from its baked paint (GameCommon baked-look; tools/bake_looks.gd wrote this copy of\n// %s: its vertex code as it was, its fragment from the pictures, which hold the colours its fragment made, as they were: not sRGB-decoded).\nvarying vec2 bake_uv;\nuniform sampler2D baked_paint : filter_linear_mipmap, repeat_disable;\nuniform sampler2D baked_glow : filter_linear_mipmap, repeat_disable;\nuniform sampler2D baked_back : filter_linear_mipmap, repeat_disable;\nuniform float baked_glow_scale = 1.0;\nuniform float baked_roughness = 0.5;\nuniform float baked_specular = 0.5;\n" % "its component's shader"
	return _insert_after_header(out, head)


## The bake copy: its vertex code at rest, each point put where its flat UVs say, its fragment unlit.
static func bake_code(code: String) -> String:
	var modes: PackedStringArray = ["unshaded", "cull_disabled", "depth_test_disabled", "depth_draw_never"]
	if _render_modes(code).has("skip_vertex_transform"):
		modes.append("skip_vertex_transform")
	var out := _set_render_modes(code, modes)
	out = _insert_before_function_end(out, "vertex", "\tPOSITION = vec4(CUSTOM0.x * 2.0 - 1.0, CUSTOM0.y * 2.0 - 1.0, 0.5, 1.0);\n")
	var frag := _function(out, "fragment")
	var opened := frag.find("{")
	var body := frag.substr(opened + 1, frag.rfind("}") - opened - 1)
	body = _replace_word(body, "VIEW", "bk_view")
	body = _replace_word(body, "FRONT_FACING", "(bake_back == 0)")
	var new_frag := "void fragment() {\n\tvec3 bk_view = normalize(NORMAL);\n" + body + \
			"\n\tif (bake_pass == 0 && bake_fold == 1) {\n\t\tALBEDO += EMISSION;\n\t}\n\tif (bake_pass == 1) {\n\t\tALBEDO = vec3(ALPHA, ROUGHNESS, SPECULAR);\n\t} else if (bake_pass == 2) {\n\t\tALBEDO = EMISSION;\n\t}\n\tALPHA = 1.0;\n}\n"
	out = _replace_function(out, "fragment", new_frag)
	# (a light function is not run unshaded; left in, it would not compile without one)
	return _insert_after_header(out, "\nuniform int bake_pass = 0;\nuniform int bake_fold = 0;\nuniform int bake_back = 0;\n")


## `code` with each `#include "file"` replaced by that file's text (relative to `dir`, or res://).
static func _inlined(code: String, dir: String) -> String:
	var re := RegEx.create_from_string("(?m)^[ \\t]*#include\\s+\"([^\"]+)\"[^\\n]*$")
	var out := code
	for i in 8:
		var m := re.search(out)
		if m == null:
			break
		var file := m.get_string(1)
		var path := file if file.begins_with("res://") else dir.path_join(file)
		var text := FileAccess.get_file_as_string(path)
		out = out.substr(0, m.get_start()) + "// (from " + file + ")
" + text + out.substr(m.get_end())
	return out


static func _render_modes(code: String) -> PackedStringArray:
	var re := RegEx.create_from_string("(?m)^\\s*render_mode\\s+([^;]*);")
	var m := re.search(code)
	var out: PackedStringArray = []
	if m:
		for bit in m.get_string(1).split(","):
			var t := bit.strip_edges()
			if t != "":
				out.append(t)
	return out


static func _set_render_modes(code: String, modes: PackedStringArray) -> String:
	var line := "render_mode %s;" % ", ".join(modes)
	var re := RegEx.create_from_string("(?m)^\\s*render_mode\\s+[^;]*;")
	var m := re.search(code)
	if m:
		return code.substr(0, m.get_start()) + line + code.substr(m.get_end())
	var at := code.find(";", code.find("shader_type"))
	return code.substr(0, at + 1) + "\n" + line + code.substr(at + 1)


static func _uniform_names(code: String) -> PackedStringArray:
	var re := RegEx.create_from_string("(?m)^\\s*uniform\\s+\\w+\\s+(\\w+)")
	var out: PackedStringArray = []
	for m in re.search_all(code):
		out.append(m.get_string(1))
	return out


# After the shader_type and render_mode lines.
static func _insert_after_header(code: String, text: String) -> String:
	var re := RegEx.create_from_string("(?m)^\\s*render_mode\\s+[^;]*;")
	var m := re.search(code)
	var at := m.get_end() if m else code.find(";", code.find("shader_type")) + 1
	return code.substr(0, at) + "\n" + text + code.substr(at)


# The whole text of `void name() {...}` (empty if none).
static func _function(code: String, name: String) -> String:
	var span := _function_span(code, name)
	if span.x < 0:
		return ""
	return code.substr(span.x, span.y - span.x)


static func _function_span(code: String, name: String) -> Vector2i:
	var re := RegEx.create_from_string("(?m)^void\\s+%s\\s*\\(\\s*\\)\\s*\\{" % name)
	var m := re.search(code)
	if m == null:
		return Vector2i(-1, -1)
	var depth := 0
	var i := m.get_end() - 1
	while i < code.length():
		var ch := code[i]
		if ch == "{":
			depth += 1
		elif ch == "}":
			depth -= 1
			if depth == 0:
				return Vector2i(m.get_start(), i + 1)
		i += 1
	return Vector2i(m.get_start(), code.length())


static func _replace_function(code: String, name: String, text: String) -> String:
	var span := _function_span(code, name)
	if span.x < 0:
		return code + "\n" + text
	return code.substr(0, span.x) + text + code.substr(span.y)


static func _insert_after_vertex_open(code: String, text: String) -> String:
	var span := _function_span(code, "vertex")
	if span.x < 0:
		return code + "\nvoid vertex() {\n" + text + "}\n"
	var at := code.find("{", span.x) + 1
	return code.substr(0, at) + "\n" + text + code.substr(at)


static func _insert_before_function_end(code: String, name: String, text: String) -> String:
	var span := _function_span(code, name)
	if span.x < 0:
		return code + "\nvoid %s() {\n%s}\n" % [name, text]
	return code.substr(0, span.y - 1) + text + code.substr(span.y - 1)


static func _replace_word(text: String, word: String, by: String) -> String:
	var re := RegEx.create_from_string("\\b%s\\b" % word)
	return re.sub(text, by, true)
