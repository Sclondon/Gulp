extends SceneTree
## Contact sheets for the art-style pass (tools/QUALITY.md): the game is built as it is played,
## then each thing it draws is copied (meshes and the materials the game gave them, no scripts)
## into a plain grey-blue room with a sun, framed from the side and a little above, and the
## pictures are laid out on one sheet a group, labelled. A window (headless draws nothing):
##
##   godot --path . --audio-driver Dummy --resolution 1280x720 --position 2600,60 \
##     -s res://tests/contact_sheet.gd -- --calm --groups=gear,docks,kit,setpieces,creatures --out=<folder>
##   godot ... -s res://tests/contact_sheet.gd -- --title --groups=title --out=<folder>
##
## Groups: gear (what Fishers draws), docks (the harbour pieces), kit (each plant and sea-floor
## piece Scenery places, and the outcrops), setpieces (the liner, the pirate ship, Atlantis, from
## four sides), creatures (a sample, made fresh), title (the boat and its figures in place, in the
## game's own light, from six sides and close).

const TILE := 300
const COLUMNS := 6
const SAMPLE := ["sardine", "salmon", "white_shark", "orca", "clownfish", "octopus", "humpback", "leviathan",
		"sea_serpent", "submarine", "remora", "mermaid", "hippocampus", "kelpie", "deep_spawn", "ghost_whale",
		"spinosaurus", "river_beast", "green_turtle", "starfish", "crab", "anglerfish"]

var main: Node
var out := ""
var groups: PackedStringArray = []
var props_only := false
var _room: World3D
var _view: SubViewport
var _camera: Camera3D
var _stage: Node3D


func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--out="):
			out = arg.get_slice("=", 1)
		elif arg.begins_with("--groups="):
			groups = arg.get_slice("=", 1).split(",")
		elif arg == "--props":
			props_only = true
	DirAccess.make_dir_recursive_absolute(out)
	main = (load("res://main.tscn") as PackedScene).instantiate()
	root.add_child(main)
	_run.call_deferred()


func _wait(frames: int) -> void:
	for i in frames:
		await process_frame


func _run() -> void:
	await _wait(240)
	_make_room()
	for group in groups:
		var tiles: Array = []
		match group:
			"gear":
				tiles = await _gear()
			"docks":
				tiles = await _docks()
			"kit":
				tiles = await _kit()
			"setpieces":
				tiles = await _setpieces()
			"creatures":
				tiles = await _creatures()
			"title":
				tiles = await _title()
		await _sheet(group, tiles)
	print("SHEETS DONE")
	quit()


# The plain room: a grey-blue background, soft light all round and a sun from the upper left.
func _make_room() -> void:
	_room = World3D.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.33, 0.37, 0.43)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.75, 0.78, 0.82)
	env.ambient_light_energy = 0.7
	_room.environment = env
	_view = SubViewport.new()
	_view.size = Vector2i(TILE, TILE)
	_view.world_3d = _room
	_view.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(_view)
	var sun := DirectionalLight3D.new()
	sun.rotation = Vector3(-0.8, -0.6, 0.0)
	sun.light_energy = 1.1
	_view.add_child(sun)
	_camera = Camera3D.new()
	_camera.fov = 38.0
	_camera.far = 2000.0
	_view.add_child(_camera)
	_stage = Node3D.new()
	_view.add_child(_stage)


# A picture of one thing (already under _stage) from a direction.
func _shoot(thing: Node3D, from: Vector3, label: String, wait := 3) -> Dictionary:
	var box := _box(thing)
	var middle := box.get_center()
	var r := maxf(box.size.length() * 0.5, 0.05)
	_camera.near = maxf(r * 0.01, 0.01)
	_camera.global_position = middle + from.normalized() * r / sin(deg_to_rad(_camera.fov * 0.5)) * 1.05
	_camera.look_at(middle, Vector3.UP if absf(from.normalized().y) < 0.95 else Vector3.FORWARD)
	await _wait(wait)
	await RenderingServer.frame_post_draw
	var img := _view.get_texture().get_image()
	return {"img": img, "label": label}


func _box(thing: Node3D) -> AABB:
	var box := AABB()
	var first := true
	for each: Node in [thing] + thing.find_children("*", "VisualInstance3D", true, false):
		if not (each is VisualInstance3D) or not (each as VisualInstance3D).is_visible_in_tree():
			continue
		var v := each as VisualInstance3D
		var b := v.global_transform * v.get_aabb()
		if b.size.length() < 0.0001:
			continue
		box = b if first else box.merge(b)
		first = false
	return box


# A copy of something the game draws: its meshes with their materials, no scripts, at the origin.
func _copy(source: Node3D) -> Node3D:
	var made := source.duplicate(0) as Node3D
	_strip(made)
	made.transform = Transform3D.IDENTITY
	made.visible = true
	_stage.add_child(made)
	for each in made.find_children("*", "Node3D", true, false):
		(each as Node3D).visible = true
	return made


func _strip(node: Node) -> void:
	node.set_script(null)
	for child in node.get_children():
		_strip(child)


# One piece of a MultiMesh, as one instance (keeping its colour and custom data).
func _copy_many(source: MultiMeshInstance3D) -> Node3D:
	var from := source.multimesh
	var many := MultiMesh.new()
	many.transform_format = MultiMesh.TRANSFORM_3D
	many.use_colors = from.use_colors
	many.use_custom_data = from.use_custom_data
	many.mesh = from.mesh
	many.instance_count = 1
	many.set_instance_transform(0, Transform3D.IDENTITY)
	if from.use_colors:
		many.set_instance_color(0, from.get_instance_color(0) if from.instance_count > 0 else Color.WHITE)
	if from.use_custom_data and from.instance_count > 0:
		many.set_instance_custom_data(0, from.get_instance_custom_data(0))
	var drawn := MultiMeshInstance3D.new()
	drawn.multimesh = many
	drawn.material_override = source.material_override
	_stage.add_child(drawn)
	return drawn


func _clear() -> void:
	for child in _stage.get_children():
		_stage.remove_child(child)
		child.queue_free()


const SIDE := Vector3(1.0, 0.45, -0.55)


func _gear() -> Array:
	var fishers: Node = main.get("fishers")
	var tiles := []
	var seen := {}
	for child in fishers.get_children():
		if not (child is Node3D):
			continue
		var sig := _signature(child)
		if sig == "" or seen.has(sig):
			continue
		seen[sig] = true
		var made := _copy(child)
		tiles.append(await _shoot(made, SIDE, sig.left(40)))
		_clear()
		if tiles.size() >= 18:
			break
	return tiles


# What a thing is made of: its meshes' materials' names.
func _signature(node: Node) -> String:
	var names := PackedStringArray()
	for each in [node] + node.find_children("*", "GeometryInstance3D", true, false):
		var mesh: Mesh = null
		if each is MeshInstance3D:
			mesh = (each as MeshInstance3D).mesh
		elif each is MultiMeshInstance3D and (each as MultiMeshInstance3D).multimesh:
			mesh = (each as MultiMeshInstance3D).multimesh.mesh
		if mesh == null:
			continue
		for s in mesh.get_surface_count():
			var m: Material = mesh.surface_get_material(s)
			if (each as GeometryInstance3D).material_override:
				m = (each as GeometryInstance3D).material_override
			var n := m.resource_name if m and m.resource_name != "" else (m.get_class() if m else "none")
			if not names.has(n):
				names.append(n)
	names.sort()
	return ",".join(names)


func _scenery() -> Node:
	for child in main.get("_viewport").get_children():
		if child.get_script() and (child.get_script() as Script).resource_path.ends_with("scenery.gd"):
			return child
	return null


func _docks() -> Array:
	var tiles := []
	var seen := {}
	for child in _scenery().get_children():
		var n := String(child.name)
		for place in ["Monterey", "SantaCruz", "Carmel", "Outcrop"]:
			if n.begins_with(place) and child is Node3D:
				var what := n.trim_prefix(place)
				if place == "Outcrop":
					what = n
				if seen.has(what):
					break
				seen[what] = true
				var made := _copy(child)
				tiles.append(await _shoot(made, SIDE, n))
				_clear()
				break
	return tiles


func _kit() -> Array:
	var tiles := []
	var seen := {}
	var scenery := _scenery()
	for each in scenery.find_children("*", "MultiMeshInstance3D", true, false):
		var drawn := each as MultiMeshInstance3D
		if drawn.multimesh == null or drawn.multimesh.mesh == null or String(drawn.name).ends_with("_far"):
			continue
		var mesh := drawn.multimesh.mesh
		var key := mesh.resource_path if mesh.resource_path != "" else str(mesh.get_instance_id())
		if seen.has(key):
			continue
		seen[key] = true
		var label := String(drawn.name)
		if label.begins_with("@"):
			label = mesh.resource_name if mesh.resource_name != "" else mesh.resource_path.get_file()
		if label == "":
			label = String(drawn.get_parent().name)
		# (`--props`: only the sea floor pieces, past the plants and the harbour's; light models left out)
		if props_only and (label.contains("_lo") or label.contains("_far") or ["kelp", "sea_grass", "mangrove", "seaweed", "Monterey", "SantaCruz", "Carmel", "Outcrop"].any(func(p: String) -> bool: return label.begins_with(p))):
			continue
		var made := _copy_many(drawn)
		tiles.append(await _shoot(made, SIDE, label.left(40)))
		_clear()
		if tiles.size() >= 60:
			break
	return tiles


func _setpieces() -> Array:
	var tiles := []
	var found := []
	for each in main.get("_viewport").find_children("*", "Node3D", true, false):
		var s: Script = each.get_script()
		if s and (s.resource_path.ends_with("/wreck.gd") or s.resource_path.ends_with("pirate_wreck.gd") or s.resource_path.ends_with("ruins.gd")):
			found.append(each)
	for piece: Node3D in found:
		var made := _copy(piece)
		for from in [Vector3(1, 0.4, -0.6), Vector3(-1, 0.4, 0.6), Vector3(0.2, 1.0, 0.1), Vector3(0.3, 0.15, 1.0)]:
			tiles.append(await _shoot(made, from, "%s %s" % [piece.get_script().resource_path.get_file(), from]))
		_clear()
	return tiles


func _creatures() -> Array:
	var tiles := []
	for kind: String in SAMPLE:
		if not Species.has(kind):
			continue
		var fish := Fish.new()
		_stage.add_child(fish)
		fish.length = 1.0
		fish.set_kind(kind)
		await _wait(2)
		tiles.append(await _shoot(fish, Vector3(1.0, 0.25, -0.5), kind))
		_clear()
	for named in ["old_one/old_one", "reef_back/reef_back"]:
		var path := "res://creatures/%s.gd" % named
		if not ResourceLoader.exists(path):
			continue
		var made: Node3D = (load(path) as GDScript).new()
		_stage.add_child(made)
		await _wait(3)
		tiles.append(await _shoot(made, Vector3(1.0, 0.5, -0.6), named.get_slice("/", 0)))
		_clear()
	return tiles


# The title in place, in the game's own world and light.
func _title() -> Array:
	var title: Node3D = main.get("title")
	_view.world_3d = (main.get("_viewport") as SubViewport).find_world_3d()
	var boat: Node3D = title.get("boat")
	var tiles := []
	for from in [Vector3(1, 0.35, 0), Vector3(-1, 0.35, 0), Vector3(0, 0.35, 1), Vector3(0, 0.35, -1), Vector3(0.5, 1, 0.5), Vector3(0.7, 0.25, 0.7)]:
		tiles.append(await _shoot(boat, from, "boat %s" % from))
	# (close: each figure, the computer and helmet, the net)
	for name in ["boy", "_captain", "_diver", "_helmet", "net"]:
		var thing: Node3D = title.get(name)
		if thing == null:
			continue
		for from in [Vector3(1, 0.3, 0.2), Vector3(-0.6, 0.4, -1)]:
			tiles.append(await _shoot(thing, from, "%s %s" % [name, from]))
	var logo: Node3D = title.get("logo")
	if logo:
		tiles.append(await _shoot(logo, Vector3(0.2, 0.1, 1), "logo"))
	_view.world_3d = _room
	return tiles


# The pictures laid out on one sheet with their names under them.
func _sheet(group: String, tiles: Array) -> void:
	if tiles.is_empty():
		print("SHEET %s: nothing" % group)
		return
	var rows := ceili(tiles.size() / float(COLUMNS))
	var page := SubViewport.new()
	page.size = Vector2i(COLUMNS * TILE, rows * (TILE + 22))
	page.transparent_bg = false
	page.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(page)
	var back := ColorRect.new()
	back.color = Color(0.1, 0.1, 0.12)
	back.size = Vector2(page.size)
	page.add_child(back)
	for i in tiles.size():
		var at := Vector2((i % COLUMNS) * TILE, (i / COLUMNS) * (TILE + 22))
		var pic := TextureRect.new()
		pic.texture = ImageTexture.create_from_image(tiles[i].img)
		pic.position = at
		page.add_child(pic)
		var words := Label.new()
		words.text = tiles[i].label
		words.position = at + Vector2(4, TILE)
		words.add_theme_font_size_override("font_size", 14)
		page.add_child(words)
	await _wait(3)
	await RenderingServer.frame_post_draw
	var path := out.path_join(group + ".png")
	page.get_texture().get_image().save_png(path)
	print("SHEET %s: %d pictures -> %s" % [group, tiles.size(), path])
	page.queue_free()
