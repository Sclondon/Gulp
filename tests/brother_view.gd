extends SceneTree
## The older brother (models/brother.glb, built by tools/build_brother.py) alone, for comparing with his sheets. Not in
## the game.
##   godot --path . --audio-driver Dummy --resolution 900x1200 -s tests/brother_view.gd -- --out=<folder> [--pose]
## Saves, lit by a high sun and a pale sky's light, and unlit (his painted pictures only): the whole of him from the
## front, his right side, the back and three-quarter (front-left), orthographic; his head from the front,
## three-quarter, his right side and the back; his left hand close from four sides. With --pose: the bend checks
## (arms down and forward, elbows and knees bent) from the front and the side. Then quits.

const MODEL := "res://models/brother.glb"
const GAME_LIGHT_SUN := 0.7   # --game-light: the sun's energy without shadows (see _process)
var _model_path := MODEL

var _out := ""
var _pose := false
var _winding := false
var _persp := false
var _posed := false
var _poses := false
var _headonly := false
var _grey: StandardMaterial3D
var _cam: Camera3D
var _sun: DirectionalLight3D
var _env: Environment
var _model: Node3D
var _shots: Array = []
var _frame := 0


func _initialize() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			_out = a.get_slice("=", 1)
		if a == "--pose":
			_pose = true
		if a == "--winding":
			_winding = true
		if a == "--persp":
			_persp = true
		if a == "--posed":
			_posed = true
		if a == "--headonly":
			# (twelfth round: only the large head views and the eyes, painted and grey, for quick before/after pairs)
			_persp = true
			_headonly = true
		if a == "--poses":
			_poses = true
		if a.begins_with("--model="):
			# (another figure of tools/build_brother.py: --model=res://models/npc/man_big.glb)
			_model_path = a.get_slice("=", 1)
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
	_model = (load(_model_path) as PackedScene).instantiate() as Node3D
	world.add_child(_model)
	if _winding:
		# Inside-out check (as tests/winding.gd judges the game's meshes): every piece's winding against its normals,
		# and the body's volume as its faces enclose it (the shorts and the ink layer are open sheets).
		var bad := 0
		for mesh: MeshInstance3D in _model.find_children("*", "MeshInstance3D", true, false):
			bad += _judge(String(mesh.name), mesh.mesh, String(mesh.name) == "brother_body")
		print("WINDING PASSED" if bad == 0 else "WINDING FAILED (%d)" % bad)
		_shots = []
		return
	for mesh: MeshInstance3D in _model.find_children("*", "MeshInstance3D", true, false):
		mesh.lod_bias = 64.0
		# (thirteenth round, diagnosis: --no-shadow-from=<name part> stops those pieces casting shadows)
		for a in OS.get_cmdline_user_args():
			if a.begins_with("--no-shadow-from=") and String(mesh.name).contains(a.get_slice("=", 1)):
				mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		# (the skin under the shorts is never drawn: whatever he wears covers it)
		if String(mesh.name).begins_with("brother_body_under"):
			mesh.visible = false
	_cam = Camera3D.new()
	_cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	world.add_child(_cam)
	if _persp or _posed or _poses:
		# As the game would show him: a perspective lens of 35 degrees at about eye height, a sun from the upper
		# front-left (as the camera sees him from the front) with shadows, a soft pale ambient.
		_cam.projection = Camera3D.PROJECTION_PERSPECTIVE
		_cam.fov = 35.0
		_sun.basis = Basis.looking_at(Vector3(0.55, -0.7, -0.45).normalized(), Vector3.UP)
		_sun.shadow_enabled = true
		_sun.directional_shadow_max_distance = 12.0
		# (fourteenth round: --game-light draws no sun shadows, as Gulp's world has none (CLAUDE.md, "What
		# Compatibility changed"): the brow and nose then cast no hard shadow over the eyes)
		if "--game-light" in OS.get_cmdline_user_args():
			_sun.shadow_enabled = false
		_grey = StandardMaterial3D.new()
		_grey.albedo_color = Color(0.5, 0.5, 0.52)
		_grey.roughness = 0.75
		var eye := Vector3(0, 1.62, 0)
		if _persp:
			if _headonly:
				for v in [["p_bigf", Vector3(0, 0, 1)], ["p_bigq", Vector3(-0.6, 0, 0.8)], ["p_bigs", Vector3(-1, 0, 0.02)]]:
					_shots.append({"name": v[0], "dir": v[1], "at": Vector3(0, 1.775, 0.06), "dist": 0.8, "eye": 1.79, "pose": "", "grey": false})
					_shots.append({"name": v[0] + "_grey", "dir": v[1], "at": Vector3(0, 1.775, 0.06), "dist": 0.8, "eye": 1.79, "pose": "", "grey": true})
				_shots.append({"name": "p_eyes", "dir": Vector3(-0.25, 0, 1), "at": Vector3(0, 1.81, 0.12), "dist": 0.42, "eye": 1.82, "pose": "", "grey": false})
				_shots.append({"name": "p_eyes_grey", "dir": Vector3(-0.25, 0, 1), "at": Vector3(0, 1.81, 0.12), "dist": 0.42, "eye": 1.82, "pose": "", "grey": true})
				# (the nose close, from the three-quarter front and the side, painted and grey)
				# (the eyes close: front, three-quarter and side, painted and grey, the eyes' height level with the camera)
				for v in [["p_eyef", Vector3(0, 0, 1), Vector3(0, 1.79, 0.13)], ["p_eyeq", Vector3(-0.6, 0, 0.8), Vector3(0, 1.79, 0.13)], ["p_eyesd", Vector3(-1, 0, 0.05), Vector3(-0.046, 1.79, 0.12)]]:
					_shots.append({"name": v[0], "dir": v[1], "at": v[2], "dist": 0.42, "eye": 1.79, "pose": "", "grey": false})
					_shots.append({"name": v[0] + "_grey", "dir": v[1], "at": v[2], "dist": 0.42, "eye": 1.79, "pose": "", "grey": true})
				# (fifteenth round: one eye (his right) close from the front, painted and grey, for the lids' edges)
				for g in [false, true]:
					_shots.append({"name": "p_eyez" + ("_grey" if g else ""), "dir": Vector3(0, 0, 1), "at": Vector3(-0.047, 1.79, 0.13), "dist": 0.17, "eye": 1.79, "pose": "", "grey": g})
				# (thirteenth round: the eyes from the front unlit, the albedo only)
				_shots.append({"name": "p_eyef_flat", "dir": Vector3(0, 0, 1), "at": Vector3(0, 1.79, 0.13), "dist": 0.42, "eye": 1.79, "pose": "", "grey": false, "unlit": true})
				# [name, direction, camera height]: front, three-quarter (the sheet's), side, from below
				for v in [["p_nosef", Vector3(0, 0, 1), 1.76], ["p_nose", Vector3(-0.55, 0, 0.85), 1.76], ["p_noses", Vector3(-1, 0, 0.05), 1.76], ["p_noseb", Vector3(-0.2, -0.75, 0.65), 1.45]]:
					_shots.append({"name": v[0], "dir": v[1], "at": Vector3(0, 1.75, 0.17), "dist": 0.4, "eye": v[2], "pose": "", "grey": false})
					_shots.append({"name": v[0] + "_grey", "dir": v[1], "at": Vector3(0, 1.75, 0.17), "dist": 0.4, "eye": v[2], "pose": "", "grey": true})
				return
			# [name, direction from him to the camera, look-at point, distance, pose, grey]
			for v in [["p_front", Vector3(0, 0, 1)], ["p_q", Vector3(-0.64, 0, 0.77)], ["p_side", Vector3(-1, 0, 0)], ["p_qb", Vector3(-0.64, 0, -0.77)]]:
				_shots.append({"name": v[0], "dir": v[1], "at": Vector3(0, 0.98, 0), "dist": 3.45, "eye": eye.y, "pose": "", "grey": false})
			_shots.append({"name": "p_head", "dir": Vector3(-0.6, 0, 0.8), "at": Vector3(0, 1.72, 0.05), "dist": 1.35, "eye": 1.76, "pose": "", "grey": false})
			_shots.append({"name": "p_head_grey", "dir": Vector3(-0.6, 0, 0.8), "at": Vector3(0, 1.72, 0.05), "dist": 1.35, "eye": 1.76, "pose": "", "grey": true})
			_shots.append({"name": "p_headf_grey", "dir": Vector3(0, 0, 1), "at": Vector3(0, 1.79, 0.06), "dist": 1.0, "eye": 1.8, "pose": "", "grey": true})
			_shots.append({"name": "p_heads_grey", "dir": Vector3(-1, 0, 0.05), "at": Vector3(0, 1.79, 0.06), "dist": 1.0, "eye": 1.8, "pose": "", "grey": true})
			# (tenth round: large lit head views, painted and grey, front, three-quarter and side, to set beside the
			# head sheet's top row)
			for v in [["p_bigf", Vector3(0, 0, 1)], ["p_bigq", Vector3(-0.6, 0, 0.8)], ["p_bigs", Vector3(-1, 0, 0.02)]]:
				_shots.append({"name": v[0], "dir": v[1], "at": Vector3(0, 1.775, 0.06), "dist": 0.8, "eye": 1.79, "pose": "", "grey": false})
				_shots.append({"name": v[0] + "_grey", "dir": v[1], "at": Vector3(0, 1.775, 0.06), "dist": 0.8, "eye": 1.79, "pose": "", "grey": true})
			_shots.append({"name": "p_eyes", "dir": Vector3(-0.25, 0, 1), "at": Vector3(0, 1.81, 0.12), "dist": 0.42, "eye": 1.82, "pose": "", "grey": false})
			_shots.append({"name": "p_eyes_grey", "dir": Vector3(-0.25, 0, 1), "at": Vector3(0, 1.81, 0.12), "dist": 0.42, "eye": 1.82, "pose": "", "grey": true})
			# (eleventh round: the head from below, and thrown back (the "up" pose), painted and grey: the jaw's edge
			# against the neck)
			for g in [false, true]:
				var sfx := "_grey" if g else ""
				_shots.append({"name": "p_below" + sfx, "dir": Vector3(-0.35, -0.75, 0.9), "at": Vector3(0, 1.74, 0.05), "dist": 0.85, "eye": 1.3, "pose": "", "grey": g})
				_shots.append({"name": "p_up" + sfx, "dir": Vector3(-0.8, -0.1, 0.6), "at": Vector3(0, 1.72, 0.03), "dist": 0.85, "eye": 1.62, "pose": "up", "grey": g})
			_shots.append({"name": "p_chest", "dir": Vector3(-0.15, 0, 1), "at": Vector3(0, 1.38, 0.1), "dist": 1.0, "eye": 1.45, "pose": "", "grey": false})
			_shots.append({"name": "p_feet", "dir": Vector3(-0.6, 0, 0.8), "at": Vector3(0.0, 0.1, 0.0), "dist": 1.25, "eye": 0.75, "pose": "", "grey": true})
			# (fifth round: close-ups of his left foot, painted and in grey from a low three-quarter and above, and of the
			# shorts from the front and the back)
			_shots.append({"name": "p_foot", "dir": Vector3(0.55, 0, 0.85), "at": Vector3(0.14, 0.06, 0.06), "dist": 0.75, "eye": 0.3, "pose": "", "grey": false})
			_shots.append({"name": "p_foot_grey", "dir": Vector3(0.55, 0, 0.85), "at": Vector3(0.14, 0.06, 0.06), "dist": 0.75, "eye": 0.3, "pose": "", "grey": true})
			_shots.append({"name": "p_foot_in_grey", "dir": Vector3(-0.35, 0, 1), "at": Vector3(0.12, 0.06, 0.06), "dist": 0.75, "eye": 0.2, "pose": "", "grey": true})
			_shots.append({"name": "p_foot_top_grey", "dir": Vector3(0.1, 0, 0.3), "at": Vector3(0.14, 0.03, 0.08), "dist": 0.25, "eye": 0.75, "pose": "", "grey": true})
			_shots.append({"name": "p_shorts", "dir": Vector3(-0.35, 0, 1), "at": Vector3(0, 0.98, 0), "dist": 1.5, "eye": 1.1, "pose": "", "grey": false})
			_shots.append({"name": "p_shorts_back", "dir": Vector3(0.35, 0, -1), "at": Vector3(0, 0.98, 0), "dist": 1.5, "eye": 1.1, "pose": "", "grey": false})
			_shots.append({"name": "p_hand","dir": Vector3(-0.2, 0, 1), "at": _hand_at() + Vector3(0, 0.02, 0), "dist": 0.6, "eye": _hand_at().y + 0.15, "pose": "", "grey": false})
		if _posed:
			for v in [["lift", Vector3(-0.64, 0, 0.77), false], ["lift", Vector3(-1, 0, 0), true], ["lift", Vector3(-0.64, 0, 0.77), true],
					["walk", Vector3(-1, 0, 0), true], ["walk", Vector3(-0.64, 0, 0.77), true], ["sit", Vector3(-1, 0, 0), true], ["sit", Vector3(-0.64, 0, 0.77), true],
					["reach", Vector3(-0.64, 0, 0.77), true]]:
				_shots.append({"name": "x_%s_%s%s" % [v[0], "side" if v[1].x < -0.9 else "q", "_grey" if v[2] else ""], "dir": v[1], "at": Vector3(0, 0.92, 0), "dist": 3.45, "eye": eye.y, "pose": v[0], "grey": v[2]})
		if _poses:
			# The pose test (tools/FIGURE_HEADS.md, "The pose test"): the eight poses of
			# tools/art_src/concept_brother_poses.jpg, each from about the sheet's own angle painted and grey, and from a
			# second angle in grey. POSE_SHOTS: [pose, sheet's angle (from him to the camera), second angle, look-at
			# height, distance, camera height]
			# (a first shot thrown away: the first frames drew him unposed)
			_shots.append({"name": "y_warm", "dir": Vector3(0, 0, 1), "at": Vector3(0, 1, 0), "dist": 3.4, "eye": 1.3, "pose": "laugh", "grey": true})
			for v in POSE_SHOTS:
				var at := Vector3(0, v[3], 0)
				_shots.append({"name": "y_%s_a" % v[0], "dir": v[1], "at": at, "dist": v[4], "eye": v[5], "pose": v[0], "grey": false})
				_shots.append({"name": "y_%s_a_grey" % v[0], "dir": v[1], "at": at, "dist": v[4], "eye": v[5], "pose": v[0], "grey": true})
				_shots.append({"name": "y_%s_b_grey" % v[0], "dir": v[2], "at": at, "dist": v[4], "eye": v[5], "pose": v[0], "grey": true})
			# close looks where poses break: under the jaw with the head thrown back, the shoulder with the arm
			# overhead, the hips seated, the gripping hands
			for c in POSE_CLOSE:
				_shots.append({"name": c[0], "dir": c[2], "at": c[3], "dist": c[4], "eye": c[5], "pose": c[1], "grey": c[6]})
		return
	if _pose:
		_bend()
		for b in [["pose_front", Vector3(0, 0, 1)], ["pose_side", Vector3(-1, 0, 0)], ["pose_q", Vector3(0.7, 0, 0.7)], ["pose_back", Vector3(0, 0, -1)]]:
			_shots.append([b[0], b[1], 1.0, 2.2, true])
		return
	var body := [["front", Vector3(0, 0, 1)], ["side", Vector3(-1, 0, 0)], ["back", Vector3(0, 0, -1)], ["three_quarter", Vector3(0.7, 0, 0.7)]]
	var head := [["head_front", Vector3(0, 0, 1)], ["head_three_quarter", Vector3(-0.62, 0, 0.78)], ["head_side", Vector3(-1, 0, 0)], ["head_back", Vector3(0, 0, -1)]]
	for lit in [true, false]:
		for b in body:
			_shots.append([b[0] + ("_lit" if lit else "_unlit"), b[1], 0.97, 2.05, lit])
		for h in head:
			_shots.append([h[0] + ("_lit" if lit else "_unlit"), h[1], Vector3(0, 1.79, 0.03), 0.42, lit])
	# His left hand close: its back, its palm, the thumb's side and fingertips-on. (Found from its bone below.)
	var hand_at := _hand_at()
	for h in [["hand_back", Vector3(1, 0, 0.35)], ["hand_palm", Vector3(-1, 0, -0.1)], ["hand_thumb", Vector3(0.1, 0, 1)], ["hand_tips", Vector3(0.15, -1, 0.1)]]:
		_shots.append([h[0], (h[1] as Vector3).normalized(), hand_at, 0.3, true, 0.15])


func _skeleton() -> Skeleton3D:
	return _model.find_children("*", "Skeleton3D", true, false)[0] as Skeleton3D


func _hand_at() -> Vector3:
	var sk := _skeleton()
	var i := sk.find_bone("finger_middle_1_l")
	var a := sk.get_bone_global_rest(sk.find_bone("hand_l")).origin
	var b := sk.get_bone_global_rest(i).origin
	return a.lerp(b, 0.6)


func _bend() -> void:
	## The checks for collapse: his left arm down at his side and his right arm forward, his left elbow and right knee
	## bent, his left thigh lifted forward (as a run or a climb would).
	var sk := _skeleton()
	var turn := func(bone: String, axis: Vector3, deg: float) -> void:
		var i := sk.find_bone(bone)
		sk.set_bone_pose_rotation(i, sk.get_bone_rest(i).basis.get_rotation_quaternion() * Quaternion(axis.normalized(), deg_to_rad(deg)))
	turn.call("upper_arm_l", Vector3(0, 0, 1), -40.0)
	turn.call("upper_arm_r", Vector3(1, 0, 0), -80.0)
	turn.call("forearm_l", Vector3(1, 0, 0), -90.0)
	turn.call("forearm_r", Vector3(1, 0, 0), -60.0)
	turn.call("thigh_l", Vector3(1, 0, 0), -70.0)
	turn.call("shin_l", Vector3(1, 0, 0), 90.0)
	turn.call("shin_r", Vector3(1, 0, 0), 45.0)
	turn.call("head", Vector3(0, 1, 0), 30.0)
	turn.call("spine", Vector3(1, 0, 0), -15.0)


## A turn `d` (in the bone's parent's frame) put on a bone, kept at `at` (its rest place if null).
func _put(bone: String, d: Basis, at = null) -> void:
	var sk := _skeleton()
	var i := sk.find_bone(bone)
	var rest := sk.get_bone_rest(i)
	sk.set_bone_pose_rotation(i, Quaternion((d * rest.basis).orthonormalized()))
	sk.set_bone_pose_position(i, rest.origin if at == null else at)


## A leg posed as scripts/title_figures.gd poses one: the thigh, shin and foot all hang from the hips (the rig's way),
## so the knee's and the ankle's places are worked out here and the shin and foot moved there. `lift` is the thigh
## forward of hanging, `knee` the bend, `foot` the foot's own turn (degrees; null: the shin's).
func _leg(side: String, lift: float, knee: float, foot = null) -> void:
	var sk := _skeleton()
	var H := sk.get_bone_rest(sk.find_bone("thigh_" + side)).origin
	var K0 := sk.get_bone_rest(sk.find_bone("shin_" + side)).origin
	var A0 := sk.get_bone_rest(sk.find_bone("foot_" + side)).origin
	var dt := Basis(Vector3.RIGHT, deg_to_rad(-lift))
	var ds := Basis(Vector3.RIGHT, deg_to_rad(-lift + knee))
	var K := H + dt * (K0 - H)
	var A := K + ds * (A0 - K0)
	_put("thigh_" + side, dt)
	_put("shin_" + side, ds, K)
	_put("foot_" + side, ds if foot == null else Basis(Vector3.RIGHT, deg_to_rad(-float(foot))), A)


func _arm_pose(side: String, down: float, fwd: float, elbow: float) -> void:
	var s := 1.0 if side == "l" else -1.0
	_put("upper_arm_" + side, Basis(Vector3.RIGHT, deg_to_rad(-fwd)) * Basis(Vector3.BACK, deg_to_rad(-s * down)))
	_put("forearm_" + side, Basis(Vector3.RIGHT, deg_to_rad(-elbow)))


func _set_pose(pose: String) -> void:
	var sk := _skeleton()
	sk.reset_bone_poses()
	match pose:
		"lift":
			_leg("l", 60.0, 90.0)
			_arm_pose("l", 38.0, 0.0, 0.0)
			_arm_pose("r", 38.0, 30.0, 70.0)
		"walk":
			_leg("l", 28.0, 12.0, 0.0)
			_leg("r", -18.0, 35.0, -30.0)
			_arm_pose("l", 36.0, -22.0, 15.0)
			_arm_pose("r", 36.0, 25.0, 30.0)
		"sit":
			var h := sk.find_bone("hips")
			sk.set_bone_pose_position(h, sk.get_bone_rest(h).origin + Vector3(0, -0.42, -0.1))
			_leg("l", 85.0, 85.0, 0.0)
			_leg("r", 85.0, 85.0, 0.0)
			_arm_pose("l", 30.0, 35.0, 50.0)
			_arm_pose("r", 30.0, 35.0, 50.0)
		"reach":
			_arm_pose("l", 38.0, 0.0, 0.0)
			_arm_pose("r", 30.0, 80.0, 100.0)
			_put("head", Basis(Vector3.UP, deg_to_rad(30.0)))
		_:
			if POSES.has(pose):
				_pose_spec(POSES[pose])


# ------------------------------------------------------------------------------------------------------------------
# The pose test's eight poses (concept_brother_poses.jpg), the body only (faces are the face rig's work). He faces +Z,
# +X is his left. Each bone: "aim" (the world direction its segment points: to its child joint), "g" (its world turn
# from rest, as [[axis, degrees], ...] in order), or "r" (its turn relative to its parent in the chain); unnamed bones
# keep their rest turn relative to their parent. The rig hangs the shin and foot from the hips, so the chain used here
# is thigh > shin > foot (as title_figures.gd's _leg works it out). "hips": [offset, [[axis, degrees]...]]; "ground":
# the lower ankle set back at its rest height. Hands: [grip, spread] for the left and right (grip 1 a fist, 0 rest,
# negative straighter; spread opens the fingers apart in the palm's plane).
# ------------------------------------------------------------------------------------------------------------------
const POSES := {
	"laugh": {"hips": [Vector3(0, 0, 0.03), []], "ground": true,
		"spine": {"aim": Vector3(0, 1, -0.12)}, "chest": {"aim": Vector3(0.05, 1, -0.28)},
		"neck": {"aim": Vector3(0, 1, -0.5)}, "head": {"aim": Vector3(0, 0.72, -0.7)},
		"upper_arm_r": {"aim": Vector3(-0.25, -0.75, 0.6)}, "forearm_r": {"aim": Vector3(0.85, 0.12, 0.5)},
		"upper_arm_l": {"aim": Vector3(0.3, -0.88, 0.37)}, "forearm_l": {"aim": Vector3(-0.08, -0.85, 0.52)},
		"thigh_l": {"aim": Vector3(0.2, -0.72, 0.66)}, "shin_l": {"aim": Vector3(0.05, -1, -0.32)}, "foot_l": {"g": []},
		"thigh_r": {"aim": Vector3(-0.24, -0.75, 0.6)}, "shin_r": {"aim": Vector3(-0.06, -1, -0.32)}, "foot_r": {"g": []},
		"hands": [[0.25, 0.0], [-0.2, 0.3]]},
	"shock": {"hips": [Vector3.ZERO, []], "ground": true,
		"spine": {"aim": Vector3(0, 1, -0.1)}, "chest": {"aim": Vector3(0, 1, -0.15)}, "head": {"aim": Vector3(0, 1, -0.22)},
		"upper_arm_l": {"aim": Vector3(0.88, -0.2, 0.42)}, "forearm_l": {"aim": Vector3(0.08, 1, 0.3)},
		"upper_arm_r": {"aim": Vector3(-0.88, -0.2, 0.42)}, "forearm_r": {"aim": Vector3(-0.08, 1, 0.3)},
		"hand_l": {"r": [["x", -10]]}, "hand_r": {"r": [["x", -10]]},
		"thigh_l": {"aim": Vector3(0.12, -0.35, 0.93)}, "shin_l": {"aim": Vector3(0.08, -0.92, -0.3)},
		"thigh_r": {"aim": Vector3(-0.06, -1, 0.04)}, "shin_r": {"aim": Vector3(-0.04, -1, -0.02)}, "foot_r": {"g": []},
		"hands": [[-0.3, 1.0], [-0.3, 1.0]]},
	"swim": {"hips": [Vector3(0, 0.0, 0), [["x", 90]]],
		"spine": {"aim": Vector3(0, 0.1, 1)}, "chest": {"aim": Vector3(0, 0.15, 1)},
		"neck": {"aim": Vector3(0, 0.4, 0.92)}, "head": {"aim": Vector3(0, 0.62, 0.78)},
		"upper_arm_r": {"aim": Vector3(-0.22, 0.1, 1)}, "forearm_r": {"aim": Vector3(-0.08, 0.02, 1)},
		"upper_arm_l": {"aim": Vector3(0.3, -0.12, 1)}, "forearm_l": {"aim": Vector3(0.12, -0.06, 1)},
		"thigh_l": {"aim": Vector3(0.08, 0.05, -1)}, "shin_l": {"aim": Vector3(0.08, 0.25, -0.97)},
		"foot_l": {"aim": Vector3(0.0, -0.35, -1)},
		"thigh_r": {"aim": Vector3(-0.08, -0.12, -1)}, "shin_r": {"aim": Vector3(-0.08, -0.06, -1)},
		"foot_r": {"aim": Vector3(0.0, -0.4, -1)},
		"hands": [[-0.2, 0.0], [-0.3, 0.1]]},
	"rope": {"hips": [Vector3(0, -0.06, -0.08), []], "ground": true,
		"spine": {"aim": Vector3(0, 1, -0.5)}, "chest": {"aim": Vector3(0, 1, -0.4)}, "neck": {"aim": Vector3(0, 1, -0.05)},
		"head": {"g": [["y", 25]]},
		"upper_arm_l": {"aim": Vector3(0.12, -0.78, 0.6)}, "forearm_l": {"aim": Vector3(-0.2, -0.1, 1)},
		"upper_arm_r": {"aim": Vector3(-0.12, -0.86, 0.48)}, "forearm_r": {"aim": Vector3(0.28, -0.12, 1)},
		"thigh_l": {"aim": Vector3(0.2, -0.68, 0.7)}, "shin_l": {"aim": Vector3(0.12, -0.95, 0.25)}, "foot_l": {"g": []},
		"thigh_r": {"aim": Vector3(-0.12, -0.92, -0.08)}, "shin_r": {"aim": Vector3(-0.06, -0.85, -0.5)},
		"foot_r": {"g": [["x", -10]]},
		"hands": [[1.0, 0.0], [1.0, 0.0]]},
	"cast": {"hips": [Vector3.ZERO, []], "ground": true,
		"spine": {"aim": Vector3(0, 1, -0.05)}, "chest": {"g": [["y", -25]]}, "head": {"g": [["y", 15]]},
		"upper_arm_r": {"aim": Vector3(-0.7, -0.45, 0.4)}, "forearm_r": {"aim": Vector3(0.15, 0.9, 0.35)},
		"upper_arm_l": {"aim": Vector3(-0.2, -0.45, 0.87)}, "forearm_l": {"aim": Vector3(-0.85, 0.45, 0.25)},
		"thigh_l": {"aim": Vector3(0.28, -0.95, 0.18)}, "shin_l": {"aim": Vector3(0.18, -1, -0.04)}, "foot_l": {"g": []},
		"thigh_r": {"aim": Vector3(-0.28, -0.95, -0.12)}, "shin_r": {"aim": Vector3(-0.2, -1, -0.04)}, "foot_r": {"g": []},
		"hands": [[1.0, 0.0], [1.0, 0.0]]},
	"seated": {"hips": [Vector3(0, -0.43, -0.08), []],
		"spine": {"aim": Vector3(0, 1, 0.9)}, "chest": {"aim": Vector3(0, 1, 1.3)}, "neck": {"aim": Vector3(0, 1, 0.6)},
		"head": {"aim": Vector3(0, 1, -0.1)},
		"upper_arm_l": {"aim": Vector3(0.04, -0.94, 0.33)}, "forearm_l": {"aim": Vector3(-0.42, 0.18, 0.89)},
		"upper_arm_r": {"aim": Vector3(-0.04, -0.94, 0.33)}, "forearm_r": {"aim": Vector3(0.48, -0.16, 0.86)},
		"thigh_l": {"aim": Vector3(0.16, -0.06, 1)}, "shin_l": {"aim": Vector3(0.03, -1, 0.06)}, "foot_l": {"g": []},
		"thigh_r": {"aim": Vector3(-0.16, -0.06, 1)}, "shin_r": {"aim": Vector3(-0.03, -1, 0.06)}, "foot_r": {"g": []},
		"hands": [[0.5, 0.0], [0.5, 0.0]]},
	"helmet": {"hips": [Vector3.ZERO, []], "ground": true,
		"chest": {"g": [["y", 10]]}, "head": {"g": [["y", 12], ["z", -6]]},
		"upper_arm_r": {"aim": Vector3(-0.42, -0.9, 0.1)}, "forearm_r": {"aim": Vector3(0.3, -0.25, 0.92)},
		"upper_arm_l": {"aim": Vector3(0.9, -0.12, 0.3)}, "forearm_l": {"aim": Vector3(0.1, 1, 0.12)},
		"thigh_l": {"aim": Vector3(0.06, -0.95, 0.32)}, "shin_l": {"aim": Vector3(0.03, -1, 0.0)}, "foot_l": {"g": []},
		"thigh_r": {"aim": Vector3(-0.06, -0.97, -0.2)}, "shin_r": {"aim": Vector3(-0.03, -0.9, -0.42)},
		"foot_r": {"g": [["x", 20]]},
		"hands": [[-0.3, 0.9], [0.7, 0.0]]},
	"up": {"hips": [Vector3.ZERO, []], "ground": true,
		"neck": {"aim": Vector3(0, 1, -0.15)}, "head": {"aim": Vector3(0, 0.85, -0.53)},
		"upper_arm_l": {"aim": Vector3(0.42, 0.88, 0.22)}, "forearm_l": {"aim": Vector3(-0.78, 0.22, 0.58)},
		"hand_l": {"aim": Vector3(-0.85, -0.05, 0.52)},
		"thigh_l": {"aim": Vector3(0.05, -1, 0.0)}, "shin_l": {"aim": Vector3(0.03, -1, 0.0)}, "foot_l": {"g": []},
		"hands": [[-0.3, 0.0], [0.15, 0.0]]},
}
const POSE_SHOTS := [
	["laugh", Vector3(-0.35, 0, 0.94), Vector3(-1, 0, 0.05), 0.9, 3.3, 1.3],
	["shock", Vector3(-0.3, 0, 0.95), Vector3(1, 0, 0.1), 0.98, 3.5, 1.3],
	["swim", Vector3(-0.6, 0.3, 0.75), Vector3(-1, 0.1, 0.1), 0.9, 4.4, 1.7],
	["rope", Vector3(0.8, 0, 0.6), Vector3(-0.6, 0, 0.8), 0.85, 3.4, 1.2],
	["cast", Vector3(0.6, 0, 0.8), Vector3(-1, 0, -0.1), 1.05, 3.6, 1.3],
	["seated", Vector3(0.2, 0, 1), Vector3(-1, 0, 0.1), 0.7, 3.0, 1.0],
	["helmet", Vector3(0.4, 0, 0.9), Vector3(-0.7, 0, -0.7), 0.95, 3.4, 1.3],
	["up", Vector3(0.3, 0, 0.95), Vector3(-1, 0, 0.05), 1.0, 3.4, 1.3],
]
# [name, pose, direction, look-at, distance, camera height, grey]
const POSE_CLOSE := [
	["y_laugh_neck_grey", "laugh", Vector3(-0.75, -0.25, 0.6), Vector3(0, 1.6, 0.04), 0.75, 1.45, true],
	["y_up_neck_grey", "up", Vector3(-0.95, 0, 0.3), Vector3(0, 1.68, 0.03), 0.75, 1.6, true],
	["y_cast_shoulder_grey", "cast", Vector3(-0.5, 0, 0.86), Vector3(-0.1, 1.55, 0.0), 1.0, 1.6, true],
	["y_shock_shoulder_grey", "shock", Vector3(0.6, 0.2, 0.8), Vector3(0.3, 1.55, 0.0), 1.1, 1.75, true],
	["y_seated_hips_grey", "seated", Vector3(-0.85, 0, 0.5), Vector3(0, 0.55, 0.15), 1.3, 0.8, true],
	["y_rope_hands", "rope", Vector3(0.6, 0.3, 0.75), Vector3(0, 1.15, 0.5), 0.8, 1.45, false],
	["y_laugh_belly_grey", "laugh", Vector3(0.2, 0, 1), Vector3(0, 1.1, 0.1), 1.0, 1.2, true],
	["y_up_hand", "up", Vector3(0.6, 0.2, 0.8), Vector3(0.05, 1.8, 0.1), 0.7, 1.9, false],
]
# (the upper arm hangs from the clavicle, here and (ninth round) in the rig: an arm lifted past the
# horizontal raises the clavicle (CLAVICLE_RAISE: degrees of clavicle a degree of arm past LIFT_FROM, at most CLAVICLE_MAX),
# which carries the shoulder joint up and in, as the shoulder blade and collarbone do)
const CHAIN := {"shin_l": "thigh_l", "foot_l": "shin_l", "shin_r": "thigh_r", "foot_r": "shin_r",
	"upper_arm_l": "clavicle_l", "upper_arm_r": "clavicle_r"}
const LIFT_FROM := 70.0
const CLAVICLE_RAISE := 0.3
const CLAVICLE_MAX := 25.0
const SEG := {"spine": "chest", "chest": "neck", "neck": "head", "upper_arm_l": "forearm_l", "forearm_l": "hand_l",
	"hand_l": "finger_middle_1_l", "upper_arm_r": "forearm_r", "forearm_r": "hand_r", "hand_r": "finger_middle_1_r",
	"thigh_l": "shin_l", "shin_l": "foot_l", "foot_l": "toe_l", "thigh_r": "shin_r", "shin_r": "foot_r", "foot_r": "toe_r"}


func _turns(list: Array) -> Basis:
	var b := Basis.IDENTITY
	for t in list:
		var ax: Vector3 = {"x": Vector3.RIGHT, "y": Vector3.UP, "z": Vector3.BACK}[t[0]]
		b = Basis(ax, deg_to_rad(float(t[1]))) * b
	return b


## The bones' world transforms worked out from the spec down the chain, then each bone's pose set from its skeleton
## parent's.
func _pose_spec(spec: Dictionary) -> void:
	var sk := _skeleton()
	var n := sk.get_bone_count()
	var rest_g: Array = []
	for i in n:
		rest_g.append(sk.get_bone_global_rest(i).origin)
	var specs := spec.duplicate(true)
	# the hands: grip and spread turned into the finger bones' own turns (the palm faces in, toward the body's middle,
	# the fingers hang along -Y at rest; the curl is about Z, the spread about X)
	var hands: Array = spec.get("hands", [[0.0, 0.0], [0.0, 0.0]])
	for k in 2:
		var sfx := "_l" if k == 0 else "_r"
		var s := 1.0 if k == 0 else -1.0
		var g: float = hands[k][0]
		var sp: float = hands[k][1]
		var fan := {"index": -12.0, "middle": -4.0, "ring": 4.0, "little": 12.0}
		for f in fan:
			for j in [1, 2, 3]:
				var curl: float = g * [55.0, 80.0, 55.0][j - 1]
				var t: Array = [["z", -s * curl]]
				if j == 1:
					t = [["x", fan[f] * sp], ["z", -s * curl]]
				specs["finger_%s_%d%s" % [f, j, sfx]] = {"r": t}
		specs["thumb_1" + sfx] = {"r": [["y", -s * 35.0 * maxf(g, 0.0) + s * 15.0 * sp], ["z", -s * 15.0 * g]]}
		specs["thumb_2" + sfx] = {"r": [["z", -s * 35.0 * g]]}
		specs["thumb_3" + sfx] = {"r": [["z", -s * 40.0 * g]]}
	for sfx in ["_l", "_r"]:
		var ua: Dictionary = specs.get("upper_arm" + sfx, {})
		if ua.has("aim") and not specs.has("clavicle" + sfx):
			var lift := rad_to_deg((ua["aim"] as Vector3).angle_to(Vector3.DOWN))
			var c := clampf((lift - LIFT_FROM) * CLAVICLE_RAISE, 0.0, CLAVICLE_MAX)
			specs["clavicle" + sfx] = {"g": [["z", c if sfx == "_l" else -c]]}
	var G: Array = []
	G.resize(n)
	for i in n:
		var name := sk.get_bone_name(i)
		var sp_i := sk.get_bone_parent(i)
		var lp := sk.find_bone(CHAIN[name]) if CHAIN.has(name) else sp_i
		var t := Transform3D()
		if lp < 0:
			var h: Array = spec.get("hips", [Vector3.ZERO, []])
			t = Transform3D(_turns(h[1]), rest_g[i] + h[0])
		else:
			var pg: Transform3D = G[lp]
			t.origin = pg.origin + pg.basis * (rest_g[i] - rest_g[lp])
			t.basis = pg.basis
			if specs.has(name):
				var d: Dictionary = specs[name]
				if d.has("aim") and (SEG.has(name) or name == "head"):
					var a: Vector3 = Vector3.UP if name == "head" else (rest_g[sk.find_bone(SEG[name])] - rest_g[i]).normalized()
					var want: Vector3 = (d["aim"] as Vector3).normalized()
					var axis := a.cross(want)
					t.basis = Basis.IDENTITY if axis.length() < 1e-5 else Basis(axis.normalized(), a.angle_to(want))
				elif d.has("g"):
					t.basis = _turns(d["g"])
				elif d.has("r"):
					t.basis = pg.basis * _turns(d["r"])
		G[i] = t
	if spec.get("ground", false):
		var low := minf(G[sk.find_bone("foot_l")].origin.y, G[sk.find_bone("foot_r")].origin.y)
		var dy: float = rest_g[sk.find_bone("foot_l")].y - low
		for i in n:
			var tt: Transform3D = G[i]
			tt.origin.y += dy
			G[i] = tt
	for i in n:
		var sp_i := sk.get_bone_parent(i)
		var L: Transform3D = G[i] if sp_i < 0 else (G[sp_i] as Transform3D).affine_inverse() * G[i]
		sk.set_bone_pose_position(i, L.origin)
		sk.set_bone_pose_rotation(i, L.basis.get_rotation_quaternion())


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
	if _shots[i] is Dictionary:
		var d: Dictionary = _shots[i]
		if f % 3 == 0:
			_set_lit(true)
			# (sixth round: measured, the old 0.7 sun and 0.45 ambient lit his chest at about 2.3 times its albedo
			# (sheet-coloured texture rendered 255,215,173) and left his back at 0.4 (116,92,76): a softer key and
			# more fill put both sides near the sheet's own peach-tan)
			# (seventh round: a light a game would plausibly use, a moderate sun and a sky's fill (the lit side about
			# twice the shaded), with his skin picture toned so the lit front lands on the sheet's warm peach-tan; the
			# 0.24 / 0.72 of the sixth round lit him flat and the texture read bleached)
			# Measured here (linear, his chest square to the camera): each unit of this sun lights his front about 6.8
			# times his albedo, each unit of this ambient about 1.0 times. 0.12 and 0.55: the lit front about 1.4 times
			# the albedo, the shaded back about 0.55 (two and a half to one), with the albedo at the sheet's own
			# painted tone (SKIN_TONE in tools/build_brother.py).
			_sun.light_energy = 0.12
			# (fourteenth round: with --game-light (no shadows) Compatibility lights the face far dimmer for the same
			# energy (forehead 0.62 against 0.86): the sun is raised so the lit front lands where it did)
			if not _sun.shadow_enabled:
				_sun.light_energy = GAME_LIGHT_SUN
			_env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
			_env.ambient_light_energy = 0.55
			if d.get("unlit", false):
				# (thirteenth round: the painted pictures alone, no light: what is paint and what is shadow)
				_set_lit(false)
			_set_pose(d["pose"])
			for mesh: MeshInstance3D in _model.find_children("*", "MeshInstance3D", true, false):
				if not String(mesh.name).begins_with("brother_body_under"):
					mesh.material_override = _grey if d["grey"] else null
					if d["grey"] and String(mesh.name).contains("ink"):
						mesh.visible = false
					elif String(mesh.name).contains("ink"):
						mesh.visible = true
			var at: Vector3 = d["at"]
			var dir: Vector3 = d["dir"]
			_cam.near = 0.02
			_cam.position = at + dir.normalized() * float(d["dist"])
			_cam.position.y = float(d["eye"])
			_cam.look_at(at, Vector3.UP)
		elif f % 3 == 2 and _out != "":
			root.get_texture().get_image().save_png("%s/%s.png" % [_out, d["name"]])
		return false
	var shot: Array = _shots[i]
	if f % 3 == 0:
		_set_lit(shot[4])
		var dir: Vector3 = shot[1]
		_cam.size = shot[3]
		var at: Vector3 = shot[2] if shot[2] is Vector3 else Vector3(0, shot[2], 0)
		var dist: float = shot[5] if shot.size() > 5 else 5.0
		_cam.near = 0.01
		_cam.position = at + dir * dist
		_cam.look_at(at, Vector3.UP if absf(dir.y) < 0.9 else Vector3.FORWARD)
	elif f % 3 == 2 and _out != "":
		root.get_texture().get_image().save_png("%s/%s.png" % [_out, shot[0]])
	return false


func _judge(name: String, mesh: Mesh, solid: bool) -> int:
	var count := 0
	var agree := 0
	var volume := 0.0
	for surface in mesh.get_surface_count():
		var arrays := mesh.surface_get_arrays(surface)
		var points: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
		var index: PackedInt32Array = arrays[Mesh.ARRAY_INDEX] if arrays[Mesh.ARRAY_INDEX] != null else PackedInt32Array()
		var corners := index.size() if not index.is_empty() else points.size()
		for t in range(0, corners, 3):
			var ia := index[t] if not index.is_empty() else t
			var ib := index[t + 1] if not index.is_empty() else t + 1
			var ic := index[t + 2] if not index.is_empty() else t + 2
			var a := points[ia]
			var b := points[ib]
			var c := points[ic]
			var facing := (c - a).cross(b - a)
			if facing.length_squared() < 1e-14:
				continue
			count += 1
			if facing.dot(normals[ia] + normals[ib] + normals[ic]) > 0.0:
				agree += 1
			volume += facing.dot(a + b + c) / 18.0
	var share := 100.0 * agree / maxf(count, 1.0)
	var good := share >= 99.0 and (volume > 0.0 or not solid)
	print("WINDING %s: %d triangles, winding agrees with normals %.1f%%, volume %.4f: %s" % [name, count, share, volume, "ok" if good else "BAD"])
	return 0 if good else 1
