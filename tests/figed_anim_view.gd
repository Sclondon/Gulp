extends SceneTree
## A dressed figed figure (tools/figed/garments.py ... --glb) playing clips carried onto its skeleton
## (tools/figed/retarget.py), in Godot. For each clip asked for: frames for a GIF (<out>/<clip>_NN.png) and a contact
## sheet of eight moments (<out>/<clip>_sheet.png), from the front quarter (or --side).
##   godot --path . --audio-driver Dummy --resolution 360x460 --position 2600,60 -s tests/figed_anim_view.gd -- \
##       --glb=<figure.glb> --clips=<clips.glb> --out=<folder> [--clip=Walk_Loop,Idle_Loop] [--frames=24] [--side]
## The clips' tracks are pointed at the dressed figure's own skeleton by bone name (the two files hold the same
## skeleton).

var _glb := ""
var _clips := ""
var _out := ""
var _want: PackedStringArray = []
var _frames := 24
var _side := false
var _skel: Skeleton3D


func _initialize() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--glb="):
			_glb = a.substr(6)
		elif a.begins_with("--clips="):
			_clips = a.substr(8)
		elif a.begins_with("--out="):
			_out = a.substr(6)
		elif a.begins_with("--clip="):
			_want = a.substr(7).split(",")
		elif a.begins_with("--frames="):
			_frames = int(a.substr(9))
		elif a == "--side":
			_side = true
	_run.call_deferred()


func _load(path: String) -> Node3D:
	var doc := GLTFDocument.new()
	var state := GLTFState.new()
	if doc.append_from_file(path, state) != OK:
		push_error("cannot read " + path)
		return null
	return doc.generate_scene(state)


func _first(n: Node, kind: String) -> Node:
	if n.is_class(kind):
		return n
	for c in n.get_children():
		var f := _first(c, kind)
		if f:
			return f
	return null


func _run() -> void:
	var model := _load(_glb)
	var source := _load(_clips)
	if model == null or source == null:
		quit(1)
		return
	root.add_child(model)
	preload("res://tests/figed_hair_looks.gd").wear(model)   # the hair pieces wear the hair shader
	_skel = _first(model, "Skeleton3D")
	var from: AnimationPlayer = _first(source, "AnimationPlayer")
	var player := AnimationPlayer.new()
	model.add_child(player)
	var lib := AnimationLibrary.new()
	var to_skel := String(model.get_path_to(_skel))
	for name in from.get_animation_list():
		var anim: Animation = from.get_animation(name).duplicate()
		for t in anim.get_track_count():
			var bone := String(anim.track_get_path(t)).get_slice(":", 1)
			anim.track_set_path(t, NodePath(to_skel + ":" + bone))
		anim.loop_mode = Animation.LOOP_LINEAR
		lib.add_animation(name, anim)
	player.add_animation_library("", lib)
	print("clips here: ", ", ".join(player.get_animation_list()))
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.9, 0.9, 0.92)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(1, 1, 1)
	env.ambient_light_energy = 0.8
	var we := WorldEnvironment.new()
	we.environment = env
	root.add_child(we)
	var cam := Camera3D.new()
	cam.fov = 30.0
	root.add_child(cam)
	var centre := Vector3(0, 0.9, 0)
	var a := deg_to_rad(-90.0 if _side else -32.0)
	cam.position = centre + Vector3(sin(a), 0.12, cos(a)) * 4.3
	cam.look_at(centre)
	var sun := DirectionalLight3D.new()
	sun.light_energy = 0.6
	cam.add_child(sun)
	sun.rotation_degrees = Vector3(-30, 25, 0)
	var size := root.size
	DirAccess.make_dir_recursive_absolute(_out)
	for clip in player.get_animation_list():
		if _want.size() > 0 and not _want.has(clip):
			continue
		var length := player.get_animation(clip).length
		player.play(clip)
		player.pause()
		var sheet := Image.create(size.x * 8, size.y, false, Image.FORMAT_RGBA8)
		for i in _frames:
			player.seek(length * float(i) / float(_frames), true)
			for _f in 3:
				await process_frame
			var shot := root.get_texture().get_image()
			shot.convert(Image.FORMAT_RGBA8)
			shot.save_png("%s/%s_%02d.png" % [_out, clip, i])
			if i % (_frames / 8) == 0 and i / (_frames / 8) < 8:
				sheet.blit_rect(shot, Rect2i(Vector2i.ZERO, size), Vector2i(size.x * (i / (_frames / 8)), 0))
		sheet.save_png("%s/%s_sheet.png" % [_out, clip])
		print("saved ", clip, " ", length, " s")
	quit()
