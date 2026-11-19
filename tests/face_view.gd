extends SceneTree
## Expression sheet for a figure made by tools/face_rig.py (models/face/<figure>_face.glb): neutral, smile, laugh,
## shock, shout, sad, bored, cheeks puffed, blink, looking up; front and three-quarter lit, three-quarter in plain
## grey, the concept sheet's matching face above where there is one. Also a talk cycle strip and three big beauty
## shots (laugh, shock, looking up).
##   godot --path . --audio-driver Dummy --resolution 520x520 --position 2600,60 -s tests/face_view.gd -- \
##       --figure=brother --out=<folder>
##   ... -- --combine --out=<folder>     (stacks <figure>_beauty.png of all three into faces_beauty.png)
## Blend shapes: MeshInstance3D.set_blend_shape_value(find_blend_shape_by_name(name), v). The jaw: `bone_turn`
## (a world axis through the bone's joint, from rest): a positive turn about +X drops the chin.

const TILE := 260
const BIG := 520

## The recipes come from models/face/face_expressions.json (written by tools/face_rig.py from its EXPRESSIONS,
## built from FACS action units). Each row here: [name, shapes, jaw, head, neck, eye yaw, eye pitch].
var EXPRESSIONS: Array = []
const ORDER := ["neutral", "smile", "laugh", "shock", "shout", "sad", "bored", "puff", "blink half", "blink",
	"look up", "look left", "look right", "look down"]

## The concept pose sheets' faces: [x, y, size] in the sheet's 2000-wide display coordinates.
const CONCEPT := {
	"brother": {"laugh": [240, 95, 170], "shock": [590, 120, 160], "shout": [1855, 120, 160],
		"look up": [1690, 615, 160], "puff": [1300, 175, 150], "smile": [1255, 580, 160]},
	"captain": {"laugh": [228, 110, 170], "shock": [600, 125, 160], "shout": [330, 705, 160],
		"look up": [1810, 645, 160], "bored": [840, 700, 160]},
	"boy": {"laugh": [215, 100, 160], "shock": [590, 110, 160], "puff": [1290, 200, 140],
		"look up": [1625, 630, 160], "bored": [735, 735, 170], "smile": [330, 725, 160]},
}

const TALK := [
	["X", {}, 0.0], ["B", {}, 4.0], ["C", {"mouth_wide": 0.3}, 10.0], ["D", {"mouth_wide": 0.6}, 22.0],
	["E", {"mouth_o": 0.5}, 8.0], ["F", {"mouth_o": 1.0}, 2.0], ["A", {"lips_press": 1.0}, 0.0],
	["C", {"mouth_wide": 0.3, "smile": 0.4}, 12.0],
]

var _out := ""
var _figure := "brother"
var _model: Node3D
var _cam: Camera3D
var _sun: DirectionalLight3D
var _grey := StandardMaterial3D.new()
var _heads: Array = []
var _sk: Skeleton3D
var _vp: SubViewport
var _hide := ""
var _face_local := Vector3.ZERO
var _hsize := 0.31
var _file := ""      # --file=<name>: load models/face/<name>.glb instead of <figure>_face.glb
var _only := ""      # --only=<expression>: one big three-quarter picture, <file>_<expression>.png


func bone_turn(sk: Skeleton3D, bone: String, axis: Vector3, deg: float) -> void:
	var b := sk.find_bone(bone)
	if b < 0:
		push_warning("no bone " + bone)
		return
	var g := sk.get_bone_global_rest(b).basis.orthonormalized()
	var d := g.inverse() * Basis(axis, deg_to_rad(deg)) * g
	sk.set_bone_pose_rotation(b, (sk.get_bone_rest(b).basis.orthonormalized() * d).get_rotation_quaternion())


## The reference face driver (what the game's will do): the expression's weights, plus each eye's blink corrective
## blink_arc_X = 4c(1 - c), c = eyes_closed + eyes_closed_X (keeps a half-closed lid on its arc over the eyeball).
static func drive_correctives(shapes: Dictionary) -> Dictionary:
	var out := shapes.duplicate()
	for s in ["L", "R"]:
		var c := clampf(float(shapes.get("eyes_closed", 0.0)) + float(shapes.get("eyes_closed_" + s, 0.0)), 0.0, 1.0)
		if c > 0.0 and c < 1.0:
			out["blink_arc_" + s] = 4.0 * c * (1.0 - c)
	return out


## Aim both eyes: yaw > 0 turns them to the figure's own left, pitch > 0 up (degrees, from rest).
func aim_eyes(sk: Skeleton3D, yaw: float, pitch: float) -> void:
	for b in ["eye_l", "eye_r"]:
		var i := sk.find_bone(b)
		if i < 0:
			continue
		var g := sk.get_bone_global_rest(i).basis.orthonormalized()
		var turn := Basis(Vector3.UP, deg_to_rad(yaw)) * Basis(Vector3.RIGHT, deg_to_rad(-pitch))
		sk.set_bone_pose_rotation(i, (sk.get_bone_rest(i).basis.orthonormalized() * (g.inverse() * turn * g)).get_rotation_quaternion())


func _pose(shapes: Dictionary, jaw: float, head: float, neck: float, eyes := Vector2.ZERO) -> void:
	var w := drive_correctives(shapes)
	for mi: MeshInstance3D in _heads:
		for i in mi.mesh.get_blend_shape_count():
			mi.set_blend_shape_value(i, 0.0)
		for k in w:
			var i: int = mi.find_blend_shape_by_name(k)
			if i < 0:
				push_warning("no shape " + k)
			else:
				mi.set_blend_shape_value(i, w[k])
	_sk.reset_bone_poses()
	bone_turn(_sk, "jaw", Vector3.RIGHT, jaw)
	bone_turn(_sk, "head", Vector3.RIGHT, head)
	bone_turn(_sk, "neck", Vector3.RIGHT, neck)
	aim_eyes(_sk, eyes.x, eyes.y)


func _pose_row(e: Array) -> void:
	_pose(e[1], e[2], e[3], e[4], Vector2(e[5], e[6]))


func _load_expressions() -> void:
	var f := FileAccess.open("res://models/face/face_expressions.json", FileAccess.READ)
	var d: Dictionary = JSON.parse_string(f.get_as_text())
	var ex: Dictionary = d["expressions"]
	for n in ORDER:
		var x: Dictionary = ex[n]
		var ey: Array = x.get("eyes", [0.0, 0.0])
		EXPRESSIONS.append([n, x.get("shapes", {}), float(x.get("jaw", 0.0)), float(x.get("head", 0.0)),
			float(x.get("neck", 0.0)), float(ey[0]), float(ey[1])])


func _grey_on(on: bool) -> void:
	for mi: MeshInstance3D in _model.find_children("*", "MeshInstance3D", true, false):
		mi.material_override = _grey if on else null


func _aim(yaw: float, dist_k: float = 1.0, lift: float = 0.0) -> void:
	var hb := _sk.find_bone("head")
	var hg: Transform3D = _sk.global_transform * _sk.get_bone_global_pose(hb)
	var target := hg * _face_local + Vector3(0, lift * _hsize / 0.31, 0)
	var dist := 2.1 * _hsize * dist_k
	var dir := Vector3(sin(deg_to_rad(yaw)), 0.05, cos(deg_to_rad(yaw))).normalized()
	_cam.global_position = target + dir * dist
	_cam.look_at(target, Vector3.UP)
	# the sun over the camera's left shoulder
	var from := _cam.global_position + _cam.global_basis.x * -0.5 + Vector3(0, 0.6, 0)
	_sun.global_position = from
	_sun.look_at(target, Vector3.UP)


func _shot() -> Image:
	await process_frame
	await process_frame
	await RenderingServer.frame_post_draw
	return _vp.get_texture().get_image()


func _tile(img: Image, size: int) -> Image:
	var c := img.duplicate()
	c.resize(size, size, Image.INTERPOLATE_LANCZOS)
	return c


func _label(sheet: Image, x: int, y: int, w: int, col: Color) -> void:
	# a thin coloured bar under each column head (text drawing is not available on Image)
	sheet.fill_rect(Rect2i(x, y, w, 4), col)


func _initialize() -> void:
	var combine := false
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			_out = a.get_slice("=", 1)
		if a.begins_with("--figure="):
			_figure = a.get_slice("=", 1)
		if a.begins_with("--hide="):
			_hide = a.get_slice("=", 1)
		if a == "--combine":
			combine = true
		if a.begins_with("--file="):
			_file = a.get_slice("=", 1)
		if a.begins_with("--only="):
			_only = a.get_slice("=", 1)
	_load_expressions()
	if combine:
		_combine()
		quit()
		return
	_run.call_deferred()


func _combine() -> void:
	var rows: Array[Image] = []
	for f in ["brother", "boy", "captain"]:
		var p := _out.path_join(f + "_beauty.png")
		if FileAccess.file_exists(p):
			rows.append(Image.load_from_file(p))
	if rows.is_empty():
		return
	var w := rows[0].get_width()
	var h := 0
	for r in rows:
		h += r.get_height()
	var sheet := Image.create(w, h, false, Image.FORMAT_RGB8)
	var y := 0
	for r in rows:
		r.convert(Image.FORMAT_RGB8)
		sheet.blit_rect(r, Rect2i(0, 0, r.get_width(), r.get_height()), Vector2i(0, y))
		y += r.get_height()
	sheet.save_png(_out.path_join("faces_beauty.png"))
	print("FACEVIEW wrote faces_beauty.png")


func _run() -> void:
	_vp = SubViewport.new()
	_vp.size = Vector2i(BIG, BIG)
	_vp.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	_vp.own_world_3d = true
	_vp.msaa_3d = Viewport.MSAA_4X
	root.add_child(_vp)
	var world := Node3D.new()
	_vp.add_child(world)
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.8, 0.81, 0.83)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.62, 0.64, 0.68)
	env.ambient_light_energy = 0.75
	var we := WorldEnvironment.new()
	we.environment = env
	world.add_child(we)
	_sun = DirectionalLight3D.new()
	_sun.light_energy = 1.25
	world.add_child(_sun)
	_cam = Camera3D.new()
	_cam.fov = 26.0
	_cam.near = 0.02
	world.add_child(_cam)
	_cam.current = true
	_grey.albedo_color = Color(0.72, 0.72, 0.72)
	_grey.roughness = 0.8
	var path := "res://models/face/%s.glb" % (_file if _file != "" else _figure + "_face")
	var ps: PackedScene = load(path)
	if ps == null:
		push_error("cannot load " + path)
		quit(1)
		return
	_model = ps.instantiate()
	world.add_child(_model)
	_sk = _model.find_children("*", "Skeleton3D", true, false)[0]
	for mi: MeshInstance3D in _model.find_children("*", "MeshInstance3D", true, false):
		if mi.mesh and mi.mesh.get_blend_shape_count() > 0:
			_heads.append(mi)
		print("FACEVIEW mesh ", mi.name, " surfaces ", mi.mesh.get_surface_count(), " shapes ", mi.mesh.get_blend_shape_count())
	var cap := _model.find_child("*_cap", true, false)
	if cap:
		cap.visible = false
	if _hide != "":
		for mi: MeshInstance3D in _model.find_children("*" + _hide + "*", "MeshInstance3D", true, false):
			mi.visible = false
	print("FACEVIEW bones ", _sk.get_bone_count(), " head ", _sk.find_bone("head"), " jaw ", _sk.find_bone("jaw"),
		" eye_l ", _sk.find_bone("eye_l"), " eye_r ", _sk.find_bone("eye_r"))
	var hm: MeshInstance3D = _heads[0]
	var bb: AABB = hm.global_transform * hm.get_aabb()
	_hsize = bb.size.y
	var fp := Vector3(0.0, bb.get_center().y - 0.02 * _hsize, bb.get_center().z + 0.1 * _hsize)
	var hr: Transform3D = _sk.global_transform * _sk.get_bone_global_rest(_sk.find_bone("head"))
	_face_local = hr.affine_inverse() * fp
	print("FACEVIEW head size ", _hsize, " face point ", fp)

	if _only != "":
		for e in EXPRESSIONS:
			if e[0] == _only:
				_pose_row(e)
				_aim(28.0, 1.25, 0.0)
				var one: Image = await _shot()
				one.save_png(_out.path_join((_file if _file != "" else _figure) + "_" + _only.replace(" ", "_") + ".png"))
				print("FACEVIEW wrote one picture")
		quit()
		return

	# concept sheet
	var concept: Image = null
	var cpath := ProjectSettings.globalize_path("res://tools/art_src/concept_%s_poses.jpg" % _figure)
	if FileAccess.file_exists(cpath):
		concept = Image.load_from_file(cpath)
	var crops: Dictionary = CONCEPT.get(_figure, {})
	var ncol := EXPRESSIONS.size()
	var nrow := 4
	var sheet := Image.create(ncol * TILE, nrow * TILE + 8, false, Image.FORMAT_RGB8)
	sheet.fill(Color(0.93, 0.93, 0.93))
	for c in ncol:
		var e: Array = EXPRESSIONS[c]
		if concept and crops.has(e[0]):
			var q: Array = crops[e[0]]
			if q[2] > 1:
				var k := concept.get_width() / 2000.0
				var s := int(q[2] * k)
				var r := Rect2i(int(q[0] * k) - s / 2, int(q[1] * k) - s / 2, s, s)
				var crop := concept.get_region(r)
				crop.convert(Image.FORMAT_RGB8)
				sheet.blit_rect(_tile(crop, TILE), Rect2i(0, 0, TILE, TILE), Vector2i(c * TILE, 0))
		for row in [1, 2, 3]:
			_pose_row(e)
			_grey_on(row == 3)
			_aim(0.0 if row == 1 else 35.0, 1.0, 0.03 if e[0] == "look up" else 0.0)
			var img: Image = await _shot()
			img.convert(Image.FORMAT_RGB8)
			sheet.blit_rect(_tile(img, TILE), Rect2i(0, 0, TILE, TILE), Vector2i(c * TILE, row * TILE))
		_label(sheet, c * TILE + 6, nrow * TILE + 2, TILE - 12, Color.from_hsv(float(c) / ncol, 0.6, 0.7))
	sheet.save_png(_out.path_join(_figure + "_expressions.png"))
	print("FACEVIEW wrote ", _figure, "_expressions.png")

	# close-ups for checking: blink and laugh, eye and mouth, front and side
	# (blink half and blink at the eye; the laugh's mouth front and three-quarter; the mouth at rest; shock's eyes)
	var cl := [[8, 0.0, 0.04, 0.42], [9, 0.0, 0.04, 0.42], [2, 0.0, -0.05, 0.6], [2, 35.0, -0.05, 0.6],
		[0, 25.0, -0.06, 0.35], [3, 0.0, 0.04, 0.45]]
	var close := Image.create(cl.size() * TILE * 2, TILE * 2, false, Image.FORMAT_RGB8)
	for i in cl.size():
		var q: Array = cl[i]
		var e: Array = EXPRESSIONS[q[0]]
		_pose_row(e)
		_grey_on(false)
		_aim(q[1], q[3], q[2])
		var img: Image = await _shot()
		img.convert(Image.FORMAT_RGB8)
		close.blit_rect(_tile(img, TILE * 2), Rect2i(0, 0, TILE * 2, TILE * 2), Vector2i(i * TILE * 2, 0))
	close.save_png(_out.path_join(_figure + "_close.png"))

	# talk cycle
	var strip := Image.create(TALK.size() * TILE, TILE, false, Image.FORMAT_RGB8)
	_grey_on(false)
	for i in TALK.size():
		var t: Array = TALK[i]
		_pose(t[1], t[2], 0.0, 0.0)
		_aim(20.0, 0.8)
		var img: Image = await _shot()
		img.convert(Image.FORMAT_RGB8)
		strip.blit_rect(_tile(img, TILE), Rect2i(0, 0, TILE, TILE), Vector2i(i * TILE, 0))
	strip.save_png(_out.path_join(_figure + "_talk.png"))

	# beauty: laugh, shock, look up, big, three-quarter
	var picks := [2, 3, 5, 10]
	var beauty := Image.create(picks.size() * BIG, BIG, false, Image.FORMAT_RGB8)
	for i in picks.size():
		var e: Array = EXPRESSIONS[picks[i]]
		_pose_row(e)
		_aim(28.0, 1.05, 0.03 if e[0] == "look up" else 0.0)
		var img: Image = await _shot()
		img.convert(Image.FORMAT_RGB8)
		beauty.blit_rect(_tile(img, BIG), Rect2i(0, 0, BIG, BIG), Vector2i(i * BIG, 0))
	beauty.save_png(_out.path_join(_figure + "_beauty.png"))
	print("FACEVIEW done")
	quit()
