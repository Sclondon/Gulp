extends SceneTree
## Pictures of creatures' models side on, the full one over the game one over the low one, with
## their triangle counts printed: for judging how heavy the models are and how the game model
## holds up. As wireframes, or (with --shaded) as they are drawn, cartoon eyes on.
##   godot --path . --audio-driver Dummy --resolution 1400x1200 -s res://tests/wire.gd -- --out=<folder> [--shaded] <kind> <kind> ...
## A kind is a name in Species.ALL. Prints "WIRE <kind> full <n> game <n> low <n>" for each (game 0:
## its component has no game model yet).

var _out := ""
var _shaded := false
var _kinds: Array[String] = []


func _initialize() -> void:
	RenderingServer.set_debug_generate_wireframes(true)
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--out="):
			_out = arg.get_slice("=", 1)
		elif arg == "--shaded":
			_shaded = true
		else:
			_kinds.append(arg)
	_run.call_deferred()


func _run() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.08, 0.1, 0.14) if not _shaded else Color(0.16, 0.3, 0.42)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color.WHITE
	env.ambient_light_energy = 1.0 if not _shaded else 0.7
	var world := WorldEnvironment.new()
	world.environment = env
	root.add_child(world)
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50.0, 110.0, 0.0)
	root.add_child(sun)
	var eye := Camera3D.new()
	eye.projection = Camera3D.PROJECTION_ORTHOGONAL
	eye.size = 1.75
	eye.position = Vector3(6.0, 0.0, 0.0)
	root.add_child(eye)
	eye.look_at(Vector3.ZERO)
	if not _shaded:
		root.debug_draw = Viewport.DEBUG_DRAW_WIREFRAME
	for kind in _kinds:
		if not Species.has(kind) or Species.of(kind).script == "":
			print("WIRE ", kind, " is not installed")
			continue
		var counts := []
		var made: Array[Node3D] = []
		for mode: String in ["full", "game", "low"]:
			var look := Species.make(kind)
			if mode == "game" and not (&"game" in look):
				look.free()
				counts.append(0)
				continue
			var long := Species.long_of(kind, look)
			# (side on, each as long as the last: full, game, low, top to bottom)
			var holder := Node3D.new()
			holder.scale = Vector3.ONE * (1.9 / long)
			holder.position = Vector3(0.0, {"full": 0.58, "game": 0.0, "low": -0.58}[mode], 0.0)
			root.add_child(holder)
			if mode == "game":
				look.set(&"game", true)
			if &"cartoon_eyes" in look and _shaded:
				look.set(&"cartoon_eyes", 1.0)
			holder.add_child(look)
			if &"low" in look:
				look.set(&"low", mode == "low")
			if &"detail_range" in look:
				look.set(&"detail_range", 0.0 if mode == "low" else 1000.0)
			if look.has_method(&"step"):
				look.call(&"step", Vector3.ZERO, 0.0)
			var triangles := 0
			for mesh: MeshInstance3D in look.find_children("*", "MeshInstance3D", true, false):
				mesh.lod_bias = 64.0
				if mesh.visible and mesh.mesh:
					for surface in mesh.mesh.get_surface_count():
						var arrays := mesh.mesh.surface_get_arrays(surface)
						var index: Variant = arrays[Mesh.ARRAY_INDEX]
						triangles += (index.size() if index != null else (arrays[Mesh.ARRAY_VERTEX] as PackedVector3Array).size()) / 3
			counts.append(triangles)
			made.append(holder)
		for i in 6:
			await process_frame
		await RenderingServer.frame_post_draw
		if _out != "":
			root.get_texture().get_image().save_png("%s/%s%s.png" % [_out, kind, "_shaded" if _shaded else ""])
		print("WIRE %s full %d game %d low %d" % [kind, counts[0], counts[1], counts[2]])
		for holder in made:
			holder.queue_free()
		await process_frame
	quit()
