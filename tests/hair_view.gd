extends SceneTree
## The figures' hair (tools/build_hair.py) as the game would show it: lit (a sun over the camera's shoulder, a sky
## light), a 35 degree perspective camera, from the front, three-quarter, side, three-quarter back, back, above and
## below, then the head thrown back and turned; the concept sheet's views in a row above. One sheet a figure.
##   godot --path . --audio-driver Dummy --resolution 360x360 --position 2600,60 -s tests/hair_view.gd -- \
##       --fig=brother|boy|captain|all --out=<folder> [--grey] [--beauty]
## Attaching hair in the game: each piece is in its figure's model space at rest; put it under a BoneAttachment3D on
## `head` with the transform `attach()` gives it, and wear `material(fig)`.

const SHADER := preload("res://shaders/hair_cards.gdshader")
const CELL := 360
## Per figure: the hair pieces, the concept sheet and its top-row views (x0, y0, x1, y1 in a 2000-wide copy), which
## side the sheet's profile faces (1: the nose to the right), and the shader's settings.
const FIGS := {
	"brother": {
		"pieces": ["hair", "moustache"],
		"sheet": "res://tools/art_src/concept_brother_head3.jpg",
		"views": [[95, 40, 445, 560], [450, 40, 820, 560], [825, 40, 1200, 560], [1210, 40, 1570, 560],
				[1575, 40, 1960, 560]],
		"face": 1.0,
		"look": {"sheen_gain": 0.3, "rim_gain": 0.35, "gloss_gain": 0.1, "sheen": Color(1.0, 0.5, 0.2)},
	},
	"boy": {
		"pieces": ["hair"],
		"sheet": "res://tools/art_src/concept_boy_head2.jpg",
		"views": [[80, 40, 440, 540], [440, 40, 820, 540], [820, 40, 1200, 540], [1200, 40, 1580, 540],
				[1580, 40, 1940, 540]],
		"face": 1.0,
		"look": {"sheen_gain": 0.25, "rim_gain": 0.3, "gloss_gain": 0.18, "sheen": Color(1.0, 0.9, 0.6)},
	},
	"captain": {
		"pieces": ["hair", "beard", "moustache", "brows"],
		"sheet": "res://tools/art_src/concept_captain_head.jpg",
		"views": [[90, 80, 490, 690], [520, 80, 950, 690], [1000, 80, 1480, 690], [1520, 80, 1920, 690],
				[1490, 680, 1940, 1100]],
		# (the head without its cap, for the shots with the cap off; the beard there is a stubble, judge only the fringe)
		"bare": "res://tools/art_src/concept_captain_head_bare.jpg",
		"bare_views": [[40, 100, 440, 670], [460, 100, 840, 670], [850, 100, 1240, 670], [1240, 100, 1620, 670],
				[1640, 100, 1960, 450]],
		"face": -1.0,
		"look": {"sheen_gain": 0.0, "rim_gain": 0.25, "gloss_gain": 0.1, "sheen": Color(0.9, 0.92, 1.0)},
	},
}

var _out := ""
var _figs: Array = []
var _grey := false
var _beauty := false
var _world: Node3D
var _cam: Camera3D
var _sun: DirectionalLight3D
var _model: Node3D
var _skel: Skeleton3D
var _hair: Array = []
var _shots: Array = []
var _images: Array = []
var _rows: Array = []  # (the shot each row of five angles starts at: a concept row goes above each)
var _frame := 0
var _fig := ""
var _centre := Vector3.ZERO
var _reach := 0.4


static func material(fig: String) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = SHADER
	m.set_shader_parameter("locks", load("res://textures/hair/%s_locks.png" % fig))
	var look: Dictionary = FIGS[fig]["look"]
	for k in look:
		m.set_shader_parameter(k, look[k])
	return m


## Which bone a piece rides: the beard and moustache go on `jaw` when the figure has one (tools/face_rig.py adds it,
## a child of `head` at the jaw hinge), so they open with the mouth; everything else on `head`. Rigid for now:
## face_rig.bind_to_face would weight them to the jaw and its shapes instead.
static func bone_for(piece: String, skel: Skeleton3D) -> String:
	if piece in ["beard", "moustache"] and skel.find_bone("jaw") >= 0:
		return "jaw"
	return "head"


## The transform a hair piece needs under a BoneAttachment3D on `bone` of `skel`, inside `model` (both at rest).
static func attach(model: Node3D, skel: Skeleton3D, bone := "head") -> Transform3D:
	# (walked by local transforms, so it works before the nodes are in the tree)
	var to_skel := Transform3D.IDENTITY
	var n: Node = skel
	while n != model and n is Node3D:
		to_skel = (n as Node3D).transform * to_skel
		n = n.get_parent()
	var rest := skel.get_bone_global_rest(skel.find_bone(bone))
	return (to_skel * rest).affine_inverse()


func _turn(bone: String, axis: Vector3, deg: float) -> void:
	var b := _skel.find_bone(bone)
	if b < 0:
		return
	var g := _skel.get_bone_global_rest(b).basis.orthonormalized()
	var d := g.inverse() * Basis(axis, deg_to_rad(deg)) * g
	_skel.set_bone_pose_rotation(b, (_skel.get_bone_rest(b).basis.orthonormalized() * d).get_rotation_quaternion())


func _initialize() -> void:
	var which := "brother"
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			_out = a.get_slice("=", 1)
		elif a.begins_with("--fig="):
			which = a.get_slice("=", 1)
		elif a == "--grey":
			_grey = true
		elif a == "--beauty":
			_beauty = true
	_figs = FIGS.keys() if which == "all" else [which]
	DirAccess.make_dir_recursive_absolute(_out)
	_world = Node3D.new()
	root.add_child(_world)
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.82, 0.84, 0.86)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.86, 0.87, 0.9)
	env.ambient_light_energy = 0.38
	env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	var we := WorldEnvironment.new()
	we.environment = env
	_world.add_child(we)
	_sun = DirectionalLight3D.new()
	_sun.light_energy = 0.75
	_sun.shadow_enabled = false  # (the game draws no sun shadows)
	_sun.shadow_bias = 0.03
	_world.add_child(_sun)
	_cam = Camera3D.new()
	_cam.fov = 35.0
	_cam.near = 0.03
	_world.add_child(_cam)
	_cam.current = true
	if _beauty:
		_figs = ["captain", "brother", "boy"]
	_next_figure()


func _next_figure() -> bool:
	if _figs.is_empty():
		return false
	_fig = _figs.pop_front()
	_load(_fig, Vector3.ZERO)
	_shots.clear()
	var face: float = FIGS[_fig]["face"]
	if _beauty:
		# (a column a figure, the captain twice (cap on, cap off): front, three-quarter, side, close)
		for st in (["", "nocap"] if _fig == "captain" else [""]):
			for az in [0.0, 38.0, 90.0]:
				_shots.append({"az": az * face, "el": 5.0, "state": st, "close": 1})
		return true
	_images.clear()
	_rows.clear()
	var states := [""]
	if _fig == "captain":
		states = ["", "nocap"]
	for st in states:
		_rows.append(_shots.size())
		for az in [0.0, 40.0, 90.0, 140.0, 180.0]:
			_shots.append({"az": az * face, "el": 4.0, "state": st})
	_shots.append({"az": 25.0 * face, "el": 62.0, "state": states[-1]})
	_shots.append({"az": 20.0 * face, "el": -45.0, "state": states[-1]})
	_shots.append({"az": 80.0 * face, "el": 0.0, "state": "up"})
	_shots.append({"az": 50.0 * face, "el": 10.0, "state": "turn"})
	_shots.append({"az": 145.0 * face, "el": 35.0, "state": "up"})
	return true


func _load(fig: String, at: Vector3) -> void:
	_model = (load("res://models/%s.glb" % fig) as PackedScene).instantiate() as Node3D
	_world.add_child(_model)
	_model.position = at
	_skel = _model.find_children("*", "Skeleton3D", true, false)[0]
	for mesh: MeshInstance3D in _model.find_children("*", "MeshInstance3D", true, false):
		mesh.lod_bias = 64.0
		if String(mesh.name).ends_with("_body_under") or OS.get_cmdline_user_args().has("--nobody"):
			mesh.visible = false
		if _grey:
			var g := StandardMaterial3D.new()
			g.albedo_color = Color(0.7, 0.7, 0.7)
			mesh.material_override = g
	var mat := material(fig)
	_hair.clear()
	var box := AABB()
	var first := true
	for piece in FIGS[fig]["pieces"]:
		var path := "res://models/hair/%s_%s.glb" % [fig, piece]
		if not ResourceLoader.exists(path):
			continue
		var h := (load(path) as PackedScene).instantiate() as Node3D
		var on := bone_for(piece, _skel)
		var bone := BoneAttachment3D.new()
		bone.bone_name = on
		_skel.add_child(bone)
		bone.add_child(h)
		h.transform = attach(_model, _skel, on)
		for mi: MeshInstance3D in h.find_children("*", "MeshInstance3D", true, false):
			mi.material_override = mat
			if OS.get_cmdline_user_args().has("--flat"):
				var f := StandardMaterial3D.new()
				f.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
				f.vertex_color_use_as_albedo = true
				f.cull_mode = BaseMaterial3D.CULL_DISABLED
				mi.material_override = f
			mi.lod_bias = 64.0
			var b := mi.get_aabb()
			b = Transform3D(Basis(), at) * b
			box = b if first else box.merge(b)
			first = false
		_hair.append(h)
	_centre = box.get_center()
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--mark="):
			# (debug: a red ball at a point given in Blender's model space, x,y,z)
			var v := a.get_slice("=", 1).split_floats(",")
			var ball := MeshInstance3D.new()
			var sm := SphereMesh.new()
			sm.radius = 0.004
			sm.height = 0.008
			ball.mesh = sm
			var red := StandardMaterial3D.new()
			red.albedo_color = Color.RED
			red.no_depth_test = true
			red.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
			ball.material_override = red
			_model.add_child(ball)
			ball.position = Vector3(v[0], v[2], -v[1])
	_reach = box.size.length()


func _apply(shot: Dictionary) -> void:
	_skel.reset_bone_poses()
	for c in _model.find_children("*_cap*", "MeshInstance3D", true, false):
		(c as MeshInstance3D).visible = shot["state"] != "nocap"
	match shot["state"]:
		"up":
			_turn("neck", Vector3.RIGHT, -20.0)
			_turn("head", Vector3.RIGHT, -35.0)
		"turn":
			_turn("neck", Vector3.UP, 20.0)
			_turn("head", Vector3.UP, 30.0)
			_turn("head", Vector3.FORWARD, 12.0)
			# (the mouth a little open, when there is a jaw: the beard and moustache must go with it)
			_turn("jaw", Vector3.RIGHT, 12.0)
	var el := deg_to_rad(shot["el"])
	var az := deg_to_rad(shot["az"])
	var dir := Vector3(-sin(az) * cos(el), sin(el), cos(az) * cos(el))
	var target := _centre + Vector3(0, -0.035, 0)
	_cam.position = target + dir * _reach * (1.8 if shot.has("close") else 1.5)
	_cam.look_at(target, Vector3.UP if absf(shot["el"]) < 80.0 else Vector3.FORWARD)
	_light_from_camera()


func _light_from_camera() -> void:
	# (over the camera's shoulder: from behind it, up and to its left)
	var b := _cam.global_transform.basis
	var from := b.z * 0.6 + Vector3.UP * 0.75 - b.x * 0.55
	_sun.basis = Basis.looking_at(-from.normalized(), Vector3.UP)


func _process(_delta: float) -> bool:
	_frame += 1
	if _shots.is_empty():
		return true
	var shot: Dictionary = _shots[0]
	if _frame == 1:
		_apply(shot)
		return false
	if _frame < 4:
		return false
	var img := root.get_viewport().get_texture().get_image()
	_images.append(img)
	if OS.get_cmdline_user_args().has("--each"):
		img.save_png(_out.path_join("%s_%02d.png" % [_fig, _images.size() - 1]))
	_shots.pop_front()
	_frame = 0
	if _shots.is_empty():
		if _beauty:
			_model.queue_free()
			if _figs.is_empty():
				_save_beauty()
				return true
			return not _next_figure()
		_save_sheet()
		_model.queue_free()
		return not _next_figure()
	return false


func _save_beauty() -> void:
	var w: int = (_images[0] as Image).get_width()
	var h: int = (_images[0] as Image).get_height()
	# (a column a figure (the captain twice: cap on, cap off): front, three-quarter, side)
	var cols := int(ceil(_images.size() / 3.0))
	var sheet := Image.create(w * cols, h * 3, false, Image.FORMAT_RGB8)
	for i in _images.size():
		var im: Image = _images[i]
		im.convert(Image.FORMAT_RGB8)
		sheet.blit_rect(im, Rect2i(0, 0, w, h), Vector2i(w * (i / 3), h * (i % 3)))
	sheet.save_png(_out.path_join("hair_beauty.png"))
	print("HAIR saved beauty")


func _concept_row(sheet: Image, path: String, views: Array, y: int) -> void:
	var src := Image.load_from_file(ProjectSettings.globalize_path(path))
	src.convert(Image.FORMAT_RGB8)
	var k := src.get_width() / 2000.0
	for i in views.size():
		var v: Array = views[i]
		var r := Rect2i(int(v[0] * k), int(v[1] * k), int((v[2] - v[0]) * k), int((v[3] - v[1]) * k))
		var crop := src.get_region(r)
		var s := minf(float(CELL) / r.size.x, float(CELL) / r.size.y)
		crop.resize(int(r.size.x * s), int(r.size.y * s), Image.INTERPOLATE_BILINEAR)
		sheet.blit_rect(crop, Rect2i(Vector2i.ZERO, crop.get_size()),
				Vector2i(CELL * i + (CELL - crop.get_width()) / 2, y + (CELL - crop.get_height()) / 2))


func _save_sheet() -> void:
	# (rows: the sheet's five views, the same five angles lit; for the captain again for the cap off, over the bare
	# head's sheet; then the extra angles: above, below, thrown back, turned)
	var cols := 5
	var conf: Dictionary = FIGS[_fig]
	var concept_rows := 2 if conf.has("bare") else 1
	var rows := int(ceil(_images.size() / float(cols))) + concept_rows
	var sheet := Image.create(CELL * cols, CELL * rows, false, Image.FORMAT_RGB8)
	sheet.fill(Color(0.82, 0.84, 0.86))
	_concept_row(sheet, conf["sheet"], conf["views"], 0)
	if conf.has("bare"):
		_concept_row(sheet, conf["bare"], conf["bare_views"], CELL * 2)
	for i in _images.size():
		var im: Image = _images[i]
		im.convert(Image.FORMAT_RGB8)
		if im.get_width() != CELL:
			im.resize(CELL, CELL)
		var row := i / cols
		# (render rows sit under their concept rows: row 0 under concept 0, row 1 under concept 1 (the bare head))
		var y := 1 + row + (mini(row + 1, concept_rows) - 1 if concept_rows > 1 else 0)
		sheet.blit_rect(im, Rect2i(0, 0, CELL, CELL), Vector2i(CELL * (i % cols), CELL * y))
	var name := "%s_hair%s.png" % [_fig, "_grey" if _grey else ""]
	sheet.save_png(_out.path_join(name))
	print("HAIR saved ", name)
