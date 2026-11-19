extends SceneTree
## The younger boy (models/boy.glb, built by tools/build_boy.py) alone, for comparing with his sheet. Not in the game
## yet: the title still uses models/title_boy.glb.
##   godot --path . --audio-driver Dummy --resolution 600x720 -s tests/boy_view.gd -- --out=<folder>
## Saves, lit as the title lights its figures, orthographic: the whole of him at the sheet's scale (half size: the
## picture's 720 rows are the sheet's rows 60 to 1500) from the front, his right side (as the sheet's side view), the
## back and three-quarter; his head from the front, three-quarter, his right side and the back; his left hand from four
## sides; and a few poses to see how he bends (arm down and forward, elbow and knee bent). Then quits.

const MODEL := "res://models/boy.glb"
const SHEET_S := 1.5 / (1495.0 - 73.0)       # metres a sheet pixel (build_boy.py's S; fifth pass: concept_boy_tpose2.jpg)
## The head sheet (concept_boy_head2.jpg): metres a pixel, and the height of its row 1150 (build_boy.py HS, hz)
const HEAD_S := SHEET_S * 0.535
const HEAD_MID_Y := (1495.0 - 310.0) * SHEET_S + (1305.0 - 1150.0) * HEAD_S

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
var _poses := false
## (--only=pose,pose: only those poses; --focus=bone:size:az,az: framed on that posed bone, from those azimuths)
var _only := PackedStringArray()
var _focus := ""


func _initialize() -> void:
	if "--wire" in OS.get_cmdline_user_args():
		RenderingServer.set_debug_generate_wireframes(true)
		root.debug_draw = Viewport.DEBUG_DRAW_WIREFRAME
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			_out = a.get_slice("=", 1)
		elif a.begins_with("--hq="):
			_azimuth["hq"] = float(a.get_slice("=", 1))
		elif a.begins_with("--hqb="):
			_azimuth["hqb"] = float(a.get_slice("=", 1))
		elif a == "--beauty":
			_beauty = true
		elif a == "--poses":
			_poses = true
		elif a.begins_with("--only="):
			_only = a.get_slice("=", 1).split(",")
		elif a.begins_with("--focus="):
			_focus = a.get_slice("=", 1)
		elif a.begins_with("--fist="):
			for v in a.get_slice("=", 1).split(","):
				_fist.append(float(v))
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
	# (twelfth pass) --glb=<absolute path>: a model built elsewhere (tools/build_boy.py -- --glb <path>), read as it
	# stands without importing it, so before/after builds can be pictured side by side
	var glb := ""
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--glb="):
			glb = a.get_slice("=", 1)
	if glb != "":
		var doc := GLTFDocument.new()
		var st := GLTFState.new()
		doc.append_from_file(glb, st)
		_model = doc.generate_scene(st) as Node3D
	else:
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
	var body_at := Vector3(0, (1495.0 - 780.0) * SHEET_S, 0)
	# (name, eye direction from him, look-at, ortho size, lit, pose, eye distance, plain grey)
	# The plain grey shots (every surface one grey, lit by a low raking sun from his front left) show the forms that are
	# in the mesh, without the paint.
	var body := [["body_front", Vector3(0, 0, 1)], ["body_side", Vector3(-1, 0, 0)], ["body_back", Vector3(0, 0, -1)], ["body_three_quarter", Vector3(0.7, 0, 0.7)]]
	for grey in [false, true]:
		for b in body:
			_shots.append([("grey_" if grey else "") + b[0], b[1], body_at, body_size, true, "", 5.0, grey])
	_shots.append(["body_front_unlit", Vector3(0, 0, 1), body_at, body_size, false, "", 5.0, false])
	var head_at := Vector3(0, 1.35, 0.03)
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
	# (seventh pass; the critic: "render these two poses large, from front and side")
	for p in [["grey_stride_front", Vector3(0, 0, 1)], ["grey_stride_side", Vector3(1, 0, 0)], ["grey_stride_q", Vector3(0.7, 0.15, 0.7)], ["grey_sit_front", Vector3(0, 0, 1)], ["grey_sit_side", Vector3(1, 0, 0)], ["grey_sit_q", Vector3(0.7, 0.15, 0.7)]]:
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
		# (fifth pass) close-ups of his left hand and left foot, lit, and the stride and the sitting pose in grey
		_shots.append(["beauty_hand", Vector3(0.9, 0.1, 0.45).normalized(), hand_at, 0.0, true, "", 0.42, false, true])
		var foot_at := _bone_at("foot_l") * 0.45 + _bone_at("toe_l") * 0.55 + Vector3(0, -0.04, 0)
		_shots.append(["beauty_foot", Vector3(0.55, 0.55, 0.65).normalized(), foot_at, 0.0, true, "", 0.6, false, true])
		_shots.append(["beauty_stride_grey", Vector3(0.7, 0.15, 0.7).normalized(), at, 0.0, true, "stride", 2.9, true, true])
		_shots.append(["beauty_sit_grey", Vector3(0.7, 0.15, 0.7).normalized(), at, 0.0, true, "sit", 2.9, true, true])
	# (--poses, eighth pass: the pose sheet's eight poses and the stride and sitting poses, each from the sheet's angle
	# and one other, painted and lit and in plain grey; framed on the posed bones; an 800x800 window is expected)
	if _poses:
		_shots.clear()
		for pn in POSE_NAMES + ["stride", "sit", "hands", "elbow0", "elbow90", "elbow140", "knee0", "knee90", "knee140"]:
			if (_only.is_empty() and (pn == "hands" or pn.begins_with("elbow") or pn.begins_with("knee"))) or (not _only.is_empty() and not pn in _only):
				continue
			var pv: Array = POSE_VIEWS.get(pn, [[], 35.0, 90.0])
			if _focus != "":
				pv = [[], float(_focus.get_slice(":", 2).get_slice(",", 0)), float(_focus.get_slice(":", 2).get_slice(",", 1))]
			for vi in [1, 2]:
				var a := deg_to_rad(float(pv[vi]))
				var d := Vector3(-sin(a), 0.12, cos(a)).normalized()
				for grey in [false, true]:
					_shots.append(["pose_%s_%d%s" % [pn, vi, "_grey" if grey else ""], d, null, 0.0, true, pn, 5.0, grey])
	# (--face, twelfth pass: the face close up at the head sheet's scale, its rows 1000 to 1300 in a 720-row window
	# (2.4 pixels a sheet pixel, row 1150 in the middle), from the sheet's front, three-quarter and side, painted and
	# grey; and his left eye closer, front and three-quarter: for before/after pairs of the face's adjustments)
	if "--face" in OS.get_cmdline_user_args():
		_shots.clear()
		for grey in [false, true]:
			for v in ["hfront", "hq", "hside"]:
				var a := deg_to_rad(float(_azimuth[v]))
				_shots.append([("face_grey_" if grey else "face_") + v, Vector3(-sin(a), 0, cos(a)), Vector3(0, HEAD_MID_Y, 0), 300.0 * HEAD_S, true, "", 5.0, grey])
			for e in [["eye_front", 0.0], ["eye_q", 40.0]]:
				var a := deg_to_rad(float(e[1]))
				_shots.append([(e[0] as String) + ("_grey" if grey else ""),Vector3(-sin(a), 0, cos(a)), Vector3(0.045, HEAD_MID_Y + 46.0 * HEAD_S, 0), 110.0 * HEAD_S, true, "", 5.0, grey])
	# (--hand=fist,point,...: ninth pass, close-ups of his left hand in those finger presets, the arm hanging a little
	# out from his side, seen from the hand's own back, palm, thumb side, little-finger side and fingertips, lit and grey)
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--hand="):
			_shots.clear()
			for preset in a.get_slice("=", 1).split(","):
				for view in ["back", "palm", "thumb", "little", "tips"]:
					for grey in [false, true]:
						_shots.append(["hand_%s_%s%s" % [preset, view, "_grey" if grey else ""], view, null, 0.17, true, "hand:" + preset, 0.12, grey])
	_grey = StandardMaterial3D.new()
	_grey.albedo_color = Color(0.7, 0.7, 0.72)
	_grey.roughness = 0.8


func _bone_at(name: String) -> Vector3:
	var i := _skel.find_bone(name)
	return _skel.get_bone_global_rest(i).origin


func _pose(kind: String) -> void:
	_skel.reset_bone_poses()
	if kind.begins_with("hand:"):
		_apply({"fingers_l": kind.get_slice(":", 1), "arm_l": [Vector3(0.45, -1, 0.3), Vector3(0.45, -1, 0.3)]})
		return
	if POSES.has(kind):
		_apply(POSES[kind])
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


## (eighth pass) Poses by aim: every bone's place in the skeleton's space is worked out down a chain in which the shin
## hangs from the thigh and the foot from the shin (in the rig both hang from the hips, as title_figures.gd's _leg
## carries them), then each bone's own pose is that place seen from its rig parent. A spec (all optional):
##   "turn": the hips' turn (euler degrees, his frame: +X his left, +Y up, +Z his front), "root": the hips moved,
##   "spine"/"chest"/"neck"/"head": a turn of that bone in his frame (not added to its parent's),
##   "arm_l": [upper arm's way, forearm's way, (twist of the upper arm, degrees), (twist of the forearm)],
##   "hand_l": euler degrees from the forearm, "fingers_l": a name in HANDS or [index, middle, ring, little curl
##   (degrees a joint), spread, thumb across the palm, thumb curl], "leg_l": [thigh's way, shin's way],
##   "foot_l"/"toe_l": euler degrees from the shin/foot; "ground": "feet" (the lower foot's ankle at its rest
##   height), "toes", "hips" (the lowest of the seat at the floor), or none. "_r" keys default to the "_l" ones mirrored.
const HANDS := {
	"relax": [12.0, 18.0, 24.0, 30.0, 6.0, -12.0, 14.0],
	"open": [2.0, 2.0, 3.0, 4.0, 10.0, 5.0, 0.0],
	"spread": [0.0, 0.0, 2.0, 3.0, 22.0, -10.0, 0.0],
	"fist": [88.0, 90.0, 90.0, 80.0, 0.0, 0.0, 34.0, 0.55, 1.0, 0.0],   # (eleventh pass: the rest fan taken out first, c[8], so the fingers curl side by side; the thumb aimed less hard, 0.7 drove it through the index finger)
	"point": [2.0, 90.0, 90.0, 80.0, 0.0, 0.0, 25.0, 0.4, 1.0, 0.0],
	"rest": [18.0, 22.0, 26.0, 30.0, 4.0, -8.0, 18.0],
	"flat": [0.0, 0.0, 0.0, 0.0, 3.0, 0.0, 0.0],
}
const POSES := {
	# (the critic's two test poses, made natural: elbows a little bent, arms swinging against the legs)
	"stride": {"arm_l": [Vector3(0.12, -1, -0.32), Vector3(0.1, -0.8, 0.15)], "arm_r": [Vector3(-0.1, -1, 0.35), Vector3(-0.12, -0.72, 0.62)],
		"fingers_l": "relax", "leg_l": [Vector3(0.03, -1, 0.5), Vector3(0.0, -1, 0.06)], "leg_r": [Vector3(-0.03, -1, -0.28), Vector3(-0.02, -0.85, -0.7)],
		"foot_r": Vector3(-10, 0, 0), "spine": Vector3(3, 0, 0), "chest": Vector3(3, 0, 0), "ground": "feet"},
	"sit": {"arm_l": [Vector3(0.18, -1, 0.22), Vector3(0.05, -0.62, 0.8)], "hand_l": Vector3(0, 0, 0), "fingers_l": "rest",
		"leg_l": [Vector3(0.08, -0.08, 1), Vector3(0.02, -1, 0.08)], "spine": Vector3(4, 0, 0), "chest": Vector3(6, 0, 0), "head": Vector3(4, 0, 0), "root": Vector3(0, -0.36, 0)},
	"laugh": {"spine": Vector3(6, 0, 0), "chest": Vector3(6, 0, 0), "neck": Vector3(-30, 0, 0), "head": Vector3(-40, 0, 0),   # (eleventh pass, the critic: knees bent, chest forward, then the head back)
		"arm_l": [Vector3(0.28, -1, 0.12), Vector3(-0.8, -0.3, 0.5), 0.0, -20.0], "hand_l": Vector3(0, 0, 0), "fingers_l": "relax",
		"leg_l": [Vector3(0.1, -1, 0.38), Vector3(0.02, -1, -0.32)], "ground": "feet"},
	"shock": {"spine": Vector3(-6, 0, 0), "chest": Vector3(-6, 0, 0), "head": Vector3(-4, 0, 0),
		"arm_l": [Vector3(0.8, -0.55, 0.3), Vector3(0.1, 1, 0.3), 0.0, -70.0], "fingers_l": "spread", "fingers_r": "spread",
		"arm_r": [Vector3(-0.8, -0.5, 0.3), Vector3(-0.1, 1, 0.3), 0.0, -70.0],
		"leg_l": [Vector3(0.12, -0.35, 1), Vector3(0.12, -1, -0.15)], "foot_l": Vector3(-25, 0, 0),
		"leg_r": [Vector3(-0.08, -1, 0.12), Vector3(-0.05, -1, -0.05)], "ground": "feet"},
	"swim": {"turn": Vector3(88, 0, 0), "spine": Vector3(88, 0, 0), "chest": Vector3(85, 0, 0), "neck": Vector3(68, 0, 0), "head": Vector3(52, 0, 0),
		"arm_l": [Vector3(0.18, -0.08, 1), Vector3(0.12, -0.12, 1)], "hand_l": Vector3(0, 0, 0), "fingers_l": "flat",
		"leg_l": [Vector3(0.12, 0.08, -1), Vector3(0.05, 0.1, -1)], "foot_l": Vector3(60, 0, 0),
		"leg_r": [Vector3(-0.08, 0.15, -1), Vector3(-0.04, 0.75, -0.66)], "foot_r": Vector3(40, 0, 0), "root": Vector3(0, 0.15, 0)},
	"run": {"turn": Vector3(12, 0, 0), "spine": Vector3(8, 0, 0), "chest": Vector3(6, 0, 0), "neck": Vector3(-10, 0, 0), "head": Vector3(-12, 0, 0),   # (eleventh pass: the whole body leaning forward about 20 degrees, the lead fist before the chest, not the face)
		"arm_l": [Vector3(0.12, -0.5, -0.86), Vector3(0.08, -0.85, 0.52)], "fingers_l": "fist",
		"arm_r": [Vector3(-0.1, -0.55, 0.85), Vector3(-0.35, 0.45, 0.85)], "fingers_r": "fist",
		"leg_r": [Vector3(-0.04, -0.25, 1), Vector3(-0.02, -1, 0.12)], "foot_r": Vector3(5, 0, 0),
		"leg_l": [Vector3(0.04, -0.82, -0.58), Vector3(0.03, 0.2, -1)], "foot_l": Vector3(35, 0, 0), "root": Vector3(0, -0.03, 0)},
	"crouch": {"spine": Vector3(30, 0, 0), "chest": Vector3(22, -8, 0), "neck": Vector3(0, 0, 0), "head": Vector3(8, 12, 0),
		"leg_l": [Vector3(0.3, 0.45, 1), Vector3(0.05, -1, -0.85)], "foot_l": Vector3(-28, 0, 0),
		"arm_l": [Vector3(0.25, -0.5, 0.82), Vector3(0.0, -0.85, 0.15)], "hand_l": Vector3(0, 0, 0), "fingers_l": "rest",
		"arm_r": [Vector3(-0.35, -0.75, 0.6), Vector3(-0.35, -0.65, 0.7)], "fingers_r": "point", "ground": "feet"},
	"cross": {"spine": Vector3(22, 0, 0), "chest": Vector3(18, 0, 0), "neck": Vector3(-14, 0, 0), "head": Vector3(-16, 0, 0),   # (eleventh pass: hunched, cheeks in open hands)
		"leg_l": [Vector3(0.82, -0.1, 0.56), Vector3(-0.93, -0.08, 0.3)], "foot_l": Vector3(-50, 0, -40),
		"leg_r": [Vector3(-0.82, -0.1, 0.56), Vector3(0.96, -0.1, 0.1)],
		"arm_l": [Vector3(0.15, -0.45, 0.88), Vector3(-0.2, 0.92, -0.3)], "hand_l": Vector3(0, 0, 0), "fingers_l": "relax", "ground": "hips"},
	"reach": {"spine": Vector3(-4, 0, 0), "chest": Vector3(-8, 0, 0), "neck": Vector3(-20, 0, 0), "head": Vector3(-34, 0, 0),
		"arm_l": [Vector3(0.12, 1, 0.12), Vector3(0.06, 1, 0.12)], "fingers_l": "spread",
		"arm_r": [Vector3(-0.15, -1, -0.12), Vector3(-0.1, -1, 0.08)], "fingers_r": "relax",
		"leg_l": [Vector3(0.03, -1, -0.02), Vector3(0.02, -1, 0.0)], "foot_l": Vector3(55, 0, 0), "toe_l": Vector3(-55, 0, 0), "ground": "toes"},
	"hands": {"fingers_l": "fist", "fingers_r": "point", "arm_l": [Vector3(0.6, -1, 0.3), Vector3(0.6, -1, 0.3)], "arm_r": [Vector3(-0.6, -1, 0.3), Vector3(-0.6, -1, 0.3)]},
	# (ninth pass) the elbow and knee at 0, 90 and 140 degrees, for close-ups (--only=elbow90 --focus=forearm_l:0.4:90,0)
	"elbow0": {"arm_l": [Vector3(0.29, -0.96, 0), Vector3(0.29, -0.96, 0)], "fingers_l": "relax"},
	"elbow90": {"arm_l": [Vector3(0.29, -0.96, 0), Vector3(0, 0, 1)], "fingers_l": "relax"},
	"elbow140": {"arm_l": [Vector3(0.29, -0.96, 0), Vector3(-0.22, 0.735, 0.643)], "fingers_l": "relax"},
	"knee0": {"leg_l": [Vector3(0.03, -1, 0), Vector3(0.03, -1, 0)]},
	"knee90": {"leg_l": [Vector3(0.03, -1, 0), Vector3(0, 0, -1)]},
	"knee140": {"leg_l": [Vector3(0.03, -1, 0), Vector3(0, 0.766, -0.643)]},
	"lookup": {"neck": Vector3(-18, 0, 0), "head": Vector3(-30, 0, 0), "chest": Vector3(-4, 0, 0),
		"arm_l": [Vector3(0.7, 0.68, 0.25), Vector3(-0.8, 0.58, -0.12), 0.0, -60.0], "hand_l": Vector3(0, 0, 70), "fingers_l": "flat",   # (eleventh pass: the hand at the brow, not on the crown)
		"arm_r": [Vector3(-0.12, -1, 0.02), Vector3(-0.08, -1, 0.15)], "fingers_r": "relax",
		"leg_l": [Vector3(0.04, -1, 0.0), Vector3(0.03, -1, 0.0)], "ground": "feet"},
}
const POSE_NAMES := ["laugh", "shock", "swim", "run", "crouch", "cross", "reach", "lookup"]
## Each sheet pose: its box on concept_boy_poses.jpg (x0, y0, x1, y1), the sheet's eye azimuth round him and one other
const POSE_VIEWS := {"laugh": [[179, 48, 509, 915], 15.0, 75.0], "shock": [[647, 55, 1073, 908], 8.0, 80.0],
	"swim": [[1080, 117, 2119, 454], 90.0, 25.0], "run": [[1968, 55, 2683, 784], 82.0, 20.0],
	"crouch": [[193, 908, 702, 1424], 50.0, -30.0], "cross": [[812, 908, 1259, 1431], 0.0, 70.0],
	"reach": [[1582, 523, 1913, 1431], 120.0, 35.0], "lookup": [[2188, 715, 2491, 1438], 18.0, 100.0]}
const V_PARENT := {"shin_l": "thigh_l", "shin_r": "thigh_r", "foot_l": "shin_l", "foot_r": "shin_r"}
const AIM_CHILD := {"upper_arm": "forearm", "forearm": "hand", "thigh": "shin", "shin": "foot"}

var _G := {}
## (--fist=a,b,c,...: twelfth pass, a trial fist in place of HANDS["fist"], to compare before choosing one)
var _fist: Array = []


func _mx(v: Vector3) -> Vector3:
	return Vector3(-v.x, v.y, v.z)


func _side_spec(spec: Dictionary, key: String, side: String) -> Variant:
	if spec.has(key + side):
		return spec[key + side]
	if side == "_r" and spec.has(key + "_l"):
		var v = spec[key + "_l"]
		if v is Vector3:
			return Vector3(v.x, -v.y, -v.z)
		if v is Array and v.size() > 0 and v[0] is Vector3:
			var out := []
			for e in v:
				out.append(_mx(e) if e is Vector3 else e)
			return out
		return v
	return null


func _eul(v: Vector3) -> Basis:
	return Basis.from_euler(Vector3(deg_to_rad(v.x), deg_to_rad(v.y), deg_to_rad(v.z)))


func _rest_g(name: String) -> Transform3D:
	return _skel.get_bone_global_rest(_skel.find_bone(name))


func _apply(spec: Dictionary) -> void:
	_G.clear()
	var n := _skel.get_bone_count()
	# (the curl axes at rest, per hand: across the knuckles, and the palm's normal)
	var axes := {}
	for side in ["_l", "_r"]:
		var h := _rest_g("hand" + side).origin
		var across := (_rest_g("finger_index_1" + side).origin - _rest_g("finger_little_1" + side).origin).normalized()
		var along := (_rest_g("finger_middle_1" + side).origin - h).normalized()
		var palm := along.cross(across).normalized()
		# (eleventh pass) the curl axis square to the hand's length: the knuckles' line slants 13 degrees off square, and
		# fingers curled about it swept sideways as they closed, crossing in a fist
		across = (across - along * across.dot(along)).normalized()
		axes[side] = [across, along, palm]
	for i in n:
		var name := _skel.get_bone_name(i)
		var rg := _skel.get_bone_global_rest(i)
		var pi := _skel.get_bone_parent(i)
		var vp: String = V_PARENT.get(name, _skel.get_bone_name(pi) if pi >= 0 else "")
		var g := Transform3D()
		if vp == "":
			var t: Vector3 = spec.get("turn", Vector3.ZERO)
			g = Transform3D(_eul(t) * rg.basis, rg.origin + spec.get("root", Vector3.ZERO))
		else:
			var gp: Transform3D = _G[vp]
			var rel := _rest_g(vp).affine_inverse() * rg
			g = gp * rel
		var side := "_l" if name.ends_with("_l") else ("_r" if name.ends_with("_r") else "")
		var base := name.trim_suffix(side)
		var sg := 1.0 if side == "_l" else -1.0
		if side == "" and spec.has(name):
			g.basis = _eul(spec[name]) * rg.basis
		elif base == "clavicle":
			# (the shoulder lifts with the arm and comes forward with it, as a shoulder does: a share of the upper
			# arm's rise above level and of its reach forward, unless the spec turns the clavicle itself)
			var s = _side_spec(spec, "arm", side)
			var e: Variant = _side_spec(spec, "clavicle", side)
			if e != null:
				g.basis = (_G[vp] as Transform3D).basis * _eul(e) * (_rest_g(vp).basis.inverse() * rg.basis)
			elif s != null:
				var to: Vector3 = (s[0] as Vector3).normalized()
				var rise := clampf((to.y + 0.35) / 1.35, 0.0, 1.0) * 24.0
				var fwd := clampf(to.z, 0.0, 1.0) * 14.0 - clampf(-to.z, 0.0, 1.0) * 8.0
				g.basis = (_G[vp] as Transform3D).basis * _eul(Vector3(0, -fwd * sg, rise * sg)) * (_rest_g(vp).basis.inverse() * rg.basis)
		elif base in AIM_CHILD:
			var key := "arm" if base in ["upper_arm", "forearm"] else "leg"
			var s = _side_spec(spec, key, side)
			if s != null:
				var k := 0 if base in ["upper_arm", "thigh"] else 1
				var child := _rest_g(AIM_CHILD[base] + side).origin
				var rd := (child - rg.origin).normalized()
				var to: Vector3 = (s[k] as Vector3).normalized()
				var q := Quaternion(rd, to)
				if s.size() > 2 + k:
					q = Quaternion(to, deg_to_rad(float(s[2 + k]) * sg)) * q
				g.basis = Basis(q) * rg.basis
		elif base in ["hand", "foot", "toe"]:
			var s = _side_spec(spec, base, side)
			if s != null:
				var gp: Transform3D = _G[vp]
				g.basis = gp.basis * _eul(s) * (_rest_g(vp).basis.inverse() * rg.basis)
		elif base.begins_with("finger_") or base.begins_with("thumb_"):
			var f = _side_spec(spec, "fingers", side)
			if f == null:
				f = "rest"
			var c: Array = HANDS[f] if f is String else f
			if f is String and f == "fist" and not _fist.is_empty():
				c = _fist
			var ax: Array = axes[side]
			var q := Quaternion()
			if base.begins_with("finger_"):
				var which := ["index", "middle", "ring", "little"].find(base.get_slice("_", 1))
				var curl: float = c[which]
				var seg := int(base.get_slice("_", 2))
				q = Quaternion(ax[0], -deg_to_rad(curl * [1.0, 1.0, 1.1, 0.6][seg]) * sg)
				if seg == 1:
					q = Quaternion(ax[2], deg_to_rad(c[4] * [1.0, 0.3, -0.5, -1.0][which]) * sg) * q
					# (eleventh pass) c[8]: the share of each finger's rest fan taken out about the palm's normal, so the
					# fingers lie parallel before they curl and curl in parallel planes (a fist's fingers had fanned in
					# from their rest spread about the one curl axis and crossed like loose sticks); c[9] the fingers'
					# convergence toward the middle finger's line as they close (degrees at the little finger)
					if c.size() > 8 and float(c[8]) != 0.0:
						var fname: String = base.get_slice("_", 1)
						var d1: Vector3 = _rest_g("finger_" + fname + "_2" + side).origin - rg.origin
						d1 = (d1 - ax[2] * d1.dot(ax[2])).normalized()
						var along_p: Vector3 = ((ax[1] as Vector3) - (ax[2] as Vector3) * (ax[1] as Vector3).dot(ax[2])).normalized()
						var ang := atan2(along_p.cross(d1).dot(ax[2]), along_p.dot(d1))
						var conv := 0.0
						if c.size() > 9:
							conv = float(c[9]) * [-0.6, 0.0, 0.45, 1.0][which] * sg
						q = Quaternion(ax[2], ang * float(c[8]) + deg_to_rad(conv)) * q
			else:
				var seg := int(base.get_slice("_", 1))
				if seg == 1:
					q = Quaternion(ax[2], deg_to_rad(c[5]) * sg)
				else:
					q = Quaternion(ax[0], -deg_to_rad(c[6]) * sg)
			var gp: Transform3D = _G[vp]
			# (tenth pass: the curl axes are in the skeleton's rest space, so the turn goes between the parent's posed
			# change and the bone's rest; put inside the parent's own frame it was turned by the parent's rest basis, and
			# each finger curled about a skewed axis: the fist's fingers splayed and crossed into shards)
			g.basis = gp.basis * _rest_g(vp).basis.inverse() * Basis(q) * rg.basis
			# (a closed hand: the thumb's first bone aimed, by the share c[7], at the index finger's middle joint as
			# posed, so the thumb lies across the curled fingers)
			if base == "thumb_1" and c.size() > 7 and float(c[7]) > 0.0:
				var tip: Vector3 = (_G["finger_index_2" + side] as Transform3D).origin
				var cur: Vector3 = g.basis * (_rest_g("thumb_2" + side).origin - rg.origin)
				var want := tip - g.origin
				var full := Quaternion(cur.normalized(), want.normalized())
				g.basis = Basis(Quaternion().slerp(full, float(c[7]))) * g.basis
			# (ninth pass) the thumb's second and end bones bend toward the middle finger's middle joint as posed (its
			# pad toward the fingers), not round the fingers' own axis, which swung it out sideways in a fist
			if base in ["thumb_2", "thumb_3"]:
				var g0: Basis = gp.basis * (_rest_g(vp).basis.inverse() * rg.basis)
				var seg_dir: Vector3 = g0 * (_rest_g("thumb_3" + side).origin - _rest_g("thumb_2" + side).origin)
				var aim: Vector3 = (_G["finger_middle_2" + side] as Transform3D).origin - g.origin
				var axw := seg_dir.cross(aim)
				if axw.length() > 1e-6:
					g.basis = Basis(Quaternion(axw.normalized(), deg_to_rad(c[6]))) * g0
		_G[name] = g
	# (down to the floor)
	var ground: String = spec.get("ground", "")
	var dy := 0.0
	if ground == "feet":
		dy = _rest_g("foot_l").origin.y - minf(_G["foot_l"].origin.y, _G["foot_r"].origin.y)
	elif ground == "toes":
		dy = _rest_g("toe_l").origin.y - minf(_G["toe_l"].origin.y, _G["toe_r"].origin.y)
	elif ground == "hips":
		dy = 0.09 - _G["hips"].origin.y
	for k in _G:
		var t: Transform3D = _G[k]
		t.origin.y += dy
		_G[k] = t
	for i in n:
		var name := _skel.get_bone_name(i)
		var pi := _skel.get_bone_parent(i)
		var l: Transform3D = _G[name] if pi < 0 else (_G[_skel.get_bone_name(pi)] as Transform3D).affine_inverse() * _G[name]
		_skel.set_bone_pose_position(i, l.origin)
		_skel.set_bone_pose_rotation(i, l.basis.get_rotation_quaternion())
		_skel.set_bone_pose_scale(i, Vector3.ONE)


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
		if shot[1] is String:
			_pose(shot[5])
			# (the hand's own directions, as posed: its back faced out and 38 degrees forward at rest)
			var hg: Transform3D = _G["hand_l"]
			var turn := hg.basis * _rest_g("hand_l").basis.inverse()
			var back := (turn * Vector3(0.79, 0, 0.62)).normalized()
			var fwd := ((_G["finger_middle_1_l"] as Transform3D).origin - hg.origin).normalized()
			var thumb_side := ((_G["finger_index_1_l"] as Transform3D).origin - (_G["finger_little_1_l"] as Transform3D).origin).normalized()
			var tilt := back * 0.25
			shot[1] = ({"back": back + fwd * 0.15, "palm": -back - fwd * 0.1, "thumb": thumb_side + tilt, "little": -thumb_side + tilt, "tips": fwd + back * 0.35} as Dictionary)[shot[1]].normalized()
			shot[2] = hg.origin * 0.3 + (_G["finger_middle_1_l"] as Transform3D).origin * 0.45 + (_G["finger_middle_2_l"] as Transform3D).origin * 0.25
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
		if float(shot[3]) > 0.0:
			_cam.size = shot[3]
		if shot[2] == null:
			# (framed on the posed bones, seen across the eye's way)
			var r := dir.cross(Vector3.UP).normalized()
			var lo := Vector3(INF, INF, INF)
			var hi := -lo
			for k in _G:
				var p: Vector3 = (_G[k] as Transform3D).origin
				var h := Vector3(p.dot(r), p.y, 0)
				lo = lo.min(h)
				hi = hi.max(h)
			var hp: Vector3 = (_G["head"] as Transform3D) * Vector3(0, 0.16, 0)
			hi = hi.max(Vector3(hp.dot(r), hp.y, 0))
			lo = lo.min(Vector3(hp.dot(r), hp.y, 0))
			lo.y = minf(lo.y, 0.0)
			var c := (lo + hi) * 0.5
			shot[2] = r * c.x + Vector3(0, c.y, 0)
			_cam.size = maxf(hi.x - lo.x, hi.y - lo.y) * 1.12 + 0.12
			if _focus != "":
				shot[2] = (_G[_focus.get_slice(":", 0)] as Transform3D).origin
				if _focus.get_slice_count(":") > 3:
					var o := _focus.get_slice(":", 3).split(",")
					shot[2] += Vector3(float(o[0]), float(o[1]), float(o[2]))
				_cam.size = float(_focus.get_slice(":", 1))
		var at: Vector3 = shot[2]
		_cam.near = 0.01
		_cam.position = at + dir * float(shot[6])
		_cam.look_at(at, Vector3.UP if absf(dir.y) < 0.9 else Vector3.FORWARD)
	elif f % 3 == 2 and _out != "":
		root.get_texture().get_image().save_png("%s/%s.png" % [_out, shot[0]])
	return false
