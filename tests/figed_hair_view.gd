extends SceneTree
## A figed head with its hair (tools/figed/hair.py -- ... --glb <file>) as the game draws it: the hair pieces wear
## shaders/hair_stylised.gdshader with the looks in tests/figed_hair_looks.gd, lit by a sun over the camera's shoulder
## and a sky light, from the head sheet's five angles (front, three-quarter right, side, three-quarter left, back),
## one strip.
##   godot --path . --audio-driver Dummy --resolution 420x480 --position 2600,60 -s tests/figed_hair_view.gd -- \
##       --glb=<file.glb> --out=<strip.png>
##       [--sheet=tools/art_src/concept_brother_bible_head.jpg]   the sheet's five heads in a row above, same scale
##       [--set=hair_locks.taper=0.5 ...]   a number setting tried without editing the looks
##       [--extra]    a second strip beside --out (<out>_extra.png): from below the fringe, from above, the head
##                    tipped back, tipped forward, turned on the neck
##       [--plain]    the carriers without the lock outline cut (what the shader starts from)
## Needs a real window (shaders draw only with a renderer); it closes itself.

const Looks := preload("res://tests/figed_hair_looks.gd")
const VIEWS := [0.0, -45.0, -90.0, 45.0, 180.0]
## the sheet's five heads: the middle of each (pixels of the 2576 x 1438 picture, at the eye line) and its scale
const SHEET_AT := [Vector2(309, 640), Vector2(818, 640), Vector2(1290, 640), Vector2(1795, 640), Vector2(2293, 640)]
const SHEET_PX_PER_M := 2230.0
const SEEN := 0.40

var _glb := ""
var _out := ""
var _sheet := ""
var _sets := {}
var _extra := false
var _plain := false


func _initialize() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--glb="):
			_glb = a.substr(6)
		elif a.begins_with("--out="):
			_out = a.substr(6)
		elif a.begins_with("--sheet="):
			_sheet = a.substr(8)
		elif a.begins_with("--set="):
			var kv := a.substr(6).split("=")
			_sets[kv[0]] = float(kv[1])
		elif a == "--extra":
			_extra = true
		elif a == "--plain":
			_plain = true
	_run.call_deferred()


func _find_skeleton(n: Node) -> Skeleton3D:
	if n is Skeleton3D:
		return n
	for c in n.get_children():
		var s := _find_skeleton(c)
		if s:
			return s
	return null


func _shoot(cam: Camera3D) -> Image:
	for _f in 4:
		await process_frame
	var shot := root.get_texture().get_image()
	shot.convert(Image.FORMAT_RGBA8)
	return shot


func _run() -> void:
	var doc := GLTFDocument.new()
	var state := GLTFState.new()
	if doc.append_from_file(_glb, state) != OK:
		push_error("cannot read " + _glb)
		quit(1)
		return
	var model: Node3D = doc.generate_scene(state)
	var pivot := Node3D.new()
	root.add_child(pivot)
	pivot.add_child(model)
	if _plain:
		for piece in Looks.LOOKS:
			_sets[piece + ".lock_shape"] = 0.0
	var worn: Array = Looks.wear(model, _sets)
	var box := AABB()
	var tris := 0
	for m in worn:
		if String(m.name).to_lower().begins_with("hair_cap"):
			box = m.global_transform * m.get_aabb()
		for s in m.mesh.get_surface_count():
			tris += m.mesh.surface_get_array_index_len(s) / 3
	print("hair pieces: ", worn.size(), ", ", tris, " triangles")
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.83, 0.82, 0.85)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(1, 1, 1)
	env.ambient_light_energy = 0.75
	var we := WorldEnvironment.new()
	we.environment = env
	root.add_child(we)
	var cam := Camera3D.new()
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.size = SEEN
	root.add_child(cam)
	var sun := DirectionalLight3D.new()
	sun.light_energy = 0.7
	cam.add_child(sun)
	sun.rotation_degrees = Vector3(-30, 25, 0)
	var centre := box.get_center() - Vector3(0, 0.055, 0)
	var size := root.size
	var rows := 2 if _sheet != "" else 1
	var strip := Image.create(size.x * VIEWS.size(), size.y * rows, false, Image.FORMAT_RGBA8)
	strip.fill(Color(0.83, 0.82, 0.85))
	if _sheet != "":
		var sheet := Image.load_from_file(_sheet)
		sheet.convert(Image.FORMAT_RGBA8)
		var h := int(SEEN * SHEET_PX_PER_M)
		var w := int(h * size.x / float(size.y))
		for i in VIEWS.size():
			var from := Rect2i(int(SHEET_AT[i].x) - w / 2, int(SHEET_AT[i].y) - h / 2, w, h).intersection(
					Rect2i(Vector2i.ZERO, sheet.get_size()))
			var cell := sheet.get_region(from)
			cell.resize(int(from.size.x * size.y / float(h)), int(from.size.y * size.y / float(h)), Image.INTERPOLATE_LANCZOS)
			var shift := Vector2i(int((from.position.x - (int(SHEET_AT[i].x) - w / 2)) * size.y / float(h)),
					int((from.position.y - (int(SHEET_AT[i].y) - h / 2)) * size.y / float(h)))
			strip.blit_rect(cell, Rect2i(Vector2i.ZERO, cell.get_size()), Vector2i(size.x * i, 0) + shift)
	for i in VIEWS.size():
		var a := deg_to_rad(VIEWS[i])
		cam.position = centre + Vector3(sin(a), 0, cos(a)) * 2.0
		cam.look_at(centre)
		var shot: Image = await _shoot(cam)
		strip.blit_rect(shot, Rect2i(Vector2i.ZERO, size), Vector2i(size.x * i, size.y * (rows - 1)))
	strip.save_png(_out)
	print("saved ", _out)
	if _extra:
		# from below the fringe, from above, then the head itself tipped back, tipped forward and turned (on its
		# bone when the file has a skeleton, else the whole model about the neck)
		var more := Image.create(size.x * 5, size.y, false, Image.FORMAT_RGBA8)
		var looks := [[Vector3(0.25, -0.75, 1.0), Vector3.ZERO], [Vector3(0.3, 1.0, 0.8), Vector3.ZERO],
				[Vector3(-0.5, 0.0, 1.0), Vector3(-28, 0, 0)], [Vector3(0.6, 0.1, 1.0), Vector3(25, 0, 0)],
				[Vector3(0.0, 0.05, 1.0), Vector3(0, 40, 14)]]
		var skel := _find_skeleton(model)
		var bone := skel.find_bone("head") if skel else -1
		var neck := centre - Vector3(0, 0.09, -0.01)
		for i in looks.size():
			var turn: Vector3 = looks[i][1]
			var q := Basis.from_euler(Vector3(deg_to_rad(turn.x), deg_to_rad(turn.y), deg_to_rad(turn.z)))
			if bone >= 0:
				skel.set_bone_pose_rotation(bone, skel.get_bone_rest(bone).basis.get_rotation_quaternion() * q.get_rotation_quaternion())
			else:
				pivot.transform = Transform3D(Basis.IDENTITY, neck) * Transform3D(q, Vector3.ZERO) * Transform3D(Basis.IDENTITY, -neck)
			cam.position = centre + (looks[i][0] as Vector3).normalized() * 2.0
			cam.look_at(centre)
			var shot: Image = await _shoot(cam)
			more.blit_rect(shot, Rect2i(Vector2i.ZERO, size), Vector2i(size.x * i, 0))
		more.save_png(_out.get_basename() + "_extra.png")
		print("saved ", _out.get_basename() + "_extra.png")
	quit()
