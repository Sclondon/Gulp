extends SceneTree
## The younger boy (models/boy.glb, built by tools/build_boy.py) alone, for comparing with his sheet. Not in the game
## yet: the title still uses models/title_boy.glb.
##   godot --path . --audio-driver Dummy --resolution 600x720 -s tests/boy_view.gd -- --out=<folder>
## Saves, lit as the title lights its figures, orthographic: the whole of him at the sheet's scale (half size: the
## picture's 720 rows are the sheet's rows 60 to 1500) from the front, his right side (as the sheet's side view), the
## back and three-quarter; his head from the front, three-quarter, his right side and the back; his left hand from four
## sides; and a few poses to see how he bends (arm down and forward, elbow and knee bent). Then quits.

const MODEL := "res://models/boy.glb"
const SHEET_S := 1.5 / (1462.0 - 135.0)      # metres a sheet pixel (build_boy.py's S)
## The head sheet (concept_boy_head.jpg): metres a pixel, and the height of its row 1010 (build_boy.py's HS, hz)
const HEAD_S := 0.000635
const HEAD_MID_Y := (1462.0 - 380.0) * SHEET_S + (1165.0 - 1010.0) * HEAD_S

var _out := ""
var _cam: Camera3D
var _sun: DirectionalLight3D
var _env: Environment
var _model: Node3D
var _skel: Skeleton3D
var _shots: Array = []
var _grey: StandardMaterial3D
## The head sheet's five views: the eye's azimuth round him (0 his front, 90 his right); the 3/4 views' are found
## by the build and passed in (--hq=, --hqb=)
var _azimuth := {"hfront": 0.0, "hq": 40.0, "hside": 90.0, "hqb": 232.0, "hback": 180.0}
var _frame := 0
var _beauty := false


func _initialize() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			_out = a.get_slice("=", 1)
		elif a.begins_with("--hq="):
			_azimuth["hq"] = float(a.get_slice("=", 1))
		elif a.begins_with("--hqb="):
			_azimuth["hqb"] = float(a.get_slice("=", 1))
		elif a == "--beauty":
			_beauty = true
	var world := Node3D.new()
	root.add_child(world)
	_env = Environment.new()
	_env.background_mode = Environment.BG_COLOR
	_env.background_color = Color(0.84, 0.85, 0.87)
	_env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	_env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	var we := WorldEnvironment.new()
	we.environment = _env
	world.add_child(we)
	_sun = DirectionalLight3D.new()
	_sun.basis = Basis.looking_at(Vector3(-0.45, -0.75, -0.5).normalized(), Vector3.UP)
	world.add_child(_sun)
	_model = (load(MODEL) as PackedScene).instantiate() as Node3D
	world.add_child(_model)
	for mesh: MeshInstance3D in _model.find_children("*", "MeshInstance3D", true, false):
		mesh.lod_bias = 64.0
		if String(mesh.name).begins_with("boy_body_under"):
			mesh.visible = false
	_skel = _model.find_children("*", "Skeleton3D", true, false)[0] as Skeleton3D
	_cam = Camera3D.new()
	_cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	world.add_child(_cam)
	var body_size := 1440.0 * SHEET_S
	var body_at := Vector3(0, (1462.0 - 780.0) * SHEET_S, 0)
	# (name, eye direction from him, look-at, ortho size, lit, pose, eye distance, plain grey)
	# The plain grey shots (every surface one grey, lit by a low raking sun from his front left) show the forms that are
	# in the mesh, without the paint.
	var body := [["body_front", Vector3(0, 0, 1)], ["body_side", Vector3(-1, 0, 0)], ["body_back", Vector3(0, 0, -1)], ["body_three_quarter", Vector3(0.7, 0, 0.7)]]
	for grey in [false, true]:
		for b in body:
			_shots.append([("grey_" if grey else "") + b[0], b[1], body_at, body_size, true, "", 5.0, grey])
	_shots.append(["body_front_unlit", Vector3(0, 0, 1), body_at, body_size, false, "", 5.0, false])
	var head_at := Vector3(0, 1.36, 0.035)
	var head := [["head_front", Vector3(0, 0, 1)], ["head_three_quarter", Vector3(0.62, 0, 0.78)], ["head_side", Vector3(-1, 0, 0)], ["head_back", Vector3(0, 0, -1)], ["head_below", Vector3(0, -0.6, 0.8)]]
	for grey in [false, true]:
		for h in head:
			_shots.append([("grey_" if grey else "") + h[0], (h[1] as Vector3).normalized(), head_at, 0.36, true, "", 5.0, grey])
	var hand_at := _bone_at("finger_middle_1_l") * 0.6 + _bone_at("hand_l") * 0.4
	# (from close by, so that his body does not stand between the eye and the palm)
	var hand := [["hand_back", Vector3(1, 0, 0.35)], ["hand_palm", Vector3(-1, 0, -0.1)], ["hand_thumb", Vector3(0.1, 0, 1)], ["hand_tips", Vector3(0.15, -1, 0.1)]]
	for grey in [false, true]:
		for h in hand:
			_shots.append([("grey_" if grey else "") + h[0], (h[1] as Vector3).normalized(), hand_at, 0.2, true, "", 0.16, grey])
	# His bald head at the head sheet's scale and framing (its rows 700 to 1320), from each of its five views' angles,
	# in plain grey and painted, to lay beside the sheet.
	for grey in [false, true]:
		for v in ["hfront", "hq", "hside", "hqb", "hback"]:
			var a := deg_to_rad(float(_azimuth[v]))
			_shots.append([("bald_grey_" if grey else "bald_") + v, Vector3(-sin(a), 0, cos(a)), Vector3(0, HEAD_MID_Y, 0), 620.0 * HEAD_S, true, "", 5.0, grey])
	for p in [["pose_front", Vector3(0, 0, 1)], ["pose_side", Vector3(1, 0, 0)], ["pose_three_quarter", Vector3(0.7, 0.25, 0.7)]]:
		_shots.append([p[0], (p[1] as Vector3).normalized(), body_at, body_size, true, "bend", 5.0, false])
	# (fourth pass) unlit side and back, to tell the paint from the light
	for b in [["body_side_unlit", Vector3(-1, 0, 0)], ["body_back_unlit", Vector3(0, 0, -1)]]:
		_shots.append([b[0], b[1], body_at, body_size, false, "", 5.0, false])
	for p in [["grey_stride_side", Vector3(1, 0, 0)], ["grey_stride_q", Vector3(0.7, 0.15, 0.7)], ["grey_sit_side", Vector3(1, 0, 0)], ["grey_sit_q", Vector3(0.7, 0.15, 0.7)]]:
		_shots.append([p[0], (p[1] as Vector3).normalized(), body_at, body_size, true, "stride" if "stride" in p[0] else "sit", 5.0, true])
	# (--beauty: only the views as the game will show him: a perspective eye (35 degrees) at eye height, the sun over
	# the eye's left shoulder, soft sky light; a 900-row window is expected)
	if _beauty:
		_shots.clear()
		var at := Vector3(0, 0.76, 0)
		for b in [["beauty_front", 0.0], ["beauty_q", 40.0], ["beauty_side", 90.0], ["beauty_qb", 140.0], ["beauty_back", 180.0]]:
			var a := deg_to_rad(float(b[1]))
			_shots.append([b[0], Vector3(-sin(a), 0.22, cos(a)).normalized(), at, 0.0, true, "", 2.9, false, true])
		_shots.append(["beauty_head_q", Vector3(-sin(deg_to_rad(35.0)), 0.05, cos(deg_to_rad(35.0))).normalized(), Vector3(0, 1.3, 0), 0.0, true, "", 0.95, false, true])
		_shots.append(["beauty_head_front", Vector3(0, 0.05, 1).normalized(), Vector3(0, 1.3, 0), 0.0, true, "", 0.95, false, true])
	_grey = StandardMaterial3D.new()
	_grey.albedo_color = Color(0.7, 0.7, 0.72)
	_grey.roughness = 0.8


func _bone_at(name: String) -> Vector3:
	var i := _skel.find_bone(name)
	return _skel.get_bone_global_rest(i).origin


func _pose(kind: String) -> void:
	_skel.reset_bone_poses()
	if kind == "stride":
		_turn("upper_arm_l", Quaternion(Vector3.RIGHT, deg_to_rad(25.0)) * Quaternion(Vector3.FORWARD, deg_to_rad(45.0)))
		_turn("upper_arm_r", Quaternion(Vector3.RIGHT, deg_to_rad(-25.0)) * Quaternion(Vector3.FORWARD, deg_to_rad(-45.0)))
		_leg("l", -30.0, -5.0)
		_leg("r", 15.0, 50.0)
		return
	if kind == "sit":
		_turn("upper_arm_l", Quaternion(Vector3.FORWARD, deg_to_rad(45.0)))
		_turn("upper_arm_r", Quaternion(Vector3.FORWARD, deg_to_rad(-45.0)))
		_leg("l", -88.0, 0.0)
		_leg("r", -88.0, 0.0)
		return
	if kind != "bend":
		return
	# his left arm straight down at his side, its elbow bent forward a right angle; his right arm reaching forward;
	# his left thigh lifted forward, its knee bent; his right knee bent back (the shin and foot hang from the hips, so
	# the foot is carried round the knee by hand)
	_turn("upper_arm_l", Quaternion(Vector3.FORWARD, deg_to_rad(38.0)))
	_turn("forearm_l", Quaternion(Vector3.RIGHT, deg_to_rad(-90.0)))
	_turn("upper_arm_r", Quaternion(Vector3.RIGHT, deg_to_rad(-80.0)) * Quaternion(Vector3.FORWARD, deg_to_rad(-38.0)))
	var q_thigh := Quaternion(Vector3.RIGHT, deg_to_rad(-60.0))
	_turn("thigh_l", q_thigh)
	var hip := _rest("thigh_l")
	var knee := hip + q_thigh * (_rest("shin_l") - hip)
	var q_shin := Quaternion(Vector3.RIGHT, deg_to_rad(20.0))
	_place("shin_l", knee, q_shin)
	_place("foot_l", knee + q_shin * (_rest("foot_l") - _rest("shin_l")), q_shin)
	var q2 := Quaternion(Vector3.RIGHT, deg_to_rad(95.0))
	_place("shin_r", _rest("shin_r"), q2)
	_place("foot_r", _rest("shin_r") + q2 * (_rest("foot_r") - _rest("shin_r")), q2)


## A leg posed as scripts/title_figures.gd poses legs (the shin and foot hang from the hips): the thigh turned
## forward (negative) or back, the shin's own turn from straight down; the knee and foot carried round by hand.
func _leg(side: String, thigh_deg: float, shin_deg: float) -> void:
	var qt := Quaternion(Vector3.RIGHT, deg_to_rad(thigh_deg))
	_turn("thigh_" + side, qt)
	var hip := _rest("thigh_" + side)
	var knee := hip + qt * (_rest("shin_" + side) - hip)
	var qs := Quaternion(Vector3.RIGHT, deg_to_rad(shin_deg))
	_place("shin_" + side, knee, qs)
	_place("foot_" + side, knee + qs * (_rest("foot_" + side) - _rest("shin_" + side)), qs)


func _rest(name: String) -> Vector3:
	return _skel.get_bone_rest(_skel.find_bone(name)).origin


func _turn(name: String, q: Quaternion) -> void:
	_skel.set_bone_pose_rotation(_skel.find_bone(name), q)


func _place(name: String, at: Vector3, q: Quaternion) -> void:
	var i := _skel.find_bone(name)
	_skel.set_bone_pose_position(i, at)
	_skel.set_bone_pose_rotation(i, q)


func _set_lit(lit: bool) -> void:
	_sun.visible = lit
	_sun.light_energy = 0.9
	_env.ambient_light_color = Color(0.8, 0.85, 0.9) if lit else Color(1, 1, 1)
	_env.ambient_light_energy = 0.55 if lit else 1.0
	for mesh: MeshInstance3D in _model.find_children("*", "MeshInstance3D", true, false):
		for s in mesh.mesh.get_surface_count():
			var m := mesh.mesh.surface_get_material(s) as BaseMaterial3D
			if m:
				m.shading_mode = BaseMaterial3D.SHADING_MODE_PER_PIXEL if lit else BaseMaterial3D.SHADING_MODE_UNSHADED


func _process(_delta: float) -> bool:
	var f := _frame
	_frame += 1
	var i := f / 3
	if i >= _shots.size():
		return true
	var shot: Array = _shots[i]
	if f % 3 == 0:
		_set_lit(shot[4])
		var grey: bool = shot[7]
		for mesh: MeshInstance3D in _model.find_children("*", "MeshInstance3D", true, false):
			mesh.material_override = _grey if grey else null
		# (grey: the sun from over the eye's left shoulder, whichever way the eye looks, so the forms are raked)
		var look: Vector3 = -(shot[1] as Vector3)
		var right := look.cross(Vector3.UP).normalized() if absf(look.y) < 0.9 else Vector3.RIGHT
		var travel := (look * 0.35 + Vector3.DOWN * 0.55 + right).normalized()
		# (fourth pass: painted views too, so his side and back are not lit only by the sky: they were "very dark
		# brown" against the front, the light, not the paint, which matches the sheet's unlit to a few per cent)
		var key := (look * 0.6 + Vector3.DOWN * 0.6 + right * 0.55).normalized()
		_sun.basis = Basis.looking_at(travel if grey else key, Vector3.UP)
		var persp: bool = shot.size() > 8 and shot[8]
		_cam.projection = Camera3D.PROJECTION_PERSPECTIVE if persp else Camera3D.PROJECTION_ORTHOGONAL
		_cam.fov = 35.0
		_env.ambient_light_energy = 0.45 if grey else _env.ambient_light_energy
		_pose(shot[5])
		var dir: Vector3 = shot[1]
		_cam.size = shot[3]
		var at: Vector3 = shot[2]
		_cam.near = 0.01
		_cam.position = at + dir * float(shot[6])
		_cam.look_at(at, Vector3.UP if absf(dir.y) < 0.9 else Vector3.FORWARD)
	elif f % 3 == 2 and _out != "":
		root.get_texture().get_image().save_png("%s/%s.png" % [_out, shot[0]])
	return false
