extends SceneTree
## The older brother (models/brother.glb, built by tools/build_brother.py) alone, for comparing with his sheets. Not in
## the game.
##   godot --path . --audio-driver Dummy --resolution 900x1200 -s tests/brother_view.gd -- --out=<folder> [--pose]
## Saves, lit by a high sun and a pale sky's light, and unlit (his painted pictures only): the whole of him from the
## front, his right side, the back and three-quarter (front-left), orthographic; his head from the front,
## three-quarter, his right side and the back; his left hand close from four sides. With --pose: the bend checks
## (arms down and forward, elbows and knees bent) from the front and the side. Then quits.

const MODEL := "res://models/brother.glb"

var _out := ""
var _pose := false
var _winding := false
var _persp := false
var _posed := false
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
		# (the skin under the shorts is never drawn: whatever he wears covers it)
		if String(mesh.name).begins_with("brother_body_under"):
			mesh.visible = false
	_cam = Camera3D.new()
	_cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	world.add_child(_cam)
	if _persp or _posed:
		# As the game would show him: a perspective lens of 35 degrees at about eye height, a sun from the upper
		# front-left (as the camera sees him from the front) with shadows, a soft pale ambient.
		_cam.projection = Camera3D.PROJECTION_PERSPECTIVE
		_cam.fov = 35.0
		_sun.basis = Basis.looking_at(Vector3(0.55, -0.7, -0.45).normalized(), Vector3.UP)
		_sun.shadow_enabled = true
		_sun.directional_shadow_max_distance = 12.0
		_grey = StandardMaterial3D.new()
		_grey.albedo_color = Color(0.5, 0.5, 0.52)
		_grey.roughness = 0.75
		var eye := Vector3(0, 1.62, 0)
		if _persp:
			# [name, direction from him to the camera, look-at point, distance, pose, grey]
			for v in [["p_front", Vector3(0, 0, 1)], ["p_q", Vector3(-0.64, 0, 0.77)], ["p_side", Vector3(-1, 0, 0)], ["p_qb", Vector3(-0.64, 0, -0.77)]]:
				_shots.append({"name": v[0], "dir": v[1], "at": Vector3(0, 0.98, 0), "dist": 3.45, "eye": eye.y, "pose": "", "grey": false})
			_shots.append({"name": "p_head", "dir": Vector3(-0.6, 0, 0.8), "at": Vector3(0, 1.72, 0.05), "dist": 1.35, "eye": 1.76, "pose": "", "grey": false})
			_shots.append({"name": "p_head_grey", "dir": Vector3(-0.6, 0, 0.8), "at": Vector3(0, 1.72, 0.05), "dist": 1.35, "eye": 1.76, "pose": "", "grey": true})
			_shots.append({"name": "p_headf_grey", "dir": Vector3(0, 0, 1), "at": Vector3(0, 1.79, 0.06), "dist": 1.0, "eye": 1.8, "pose": "", "grey": true})
			_shots.append({"name": "p_heads_grey", "dir": Vector3(-1, 0, 0.05), "at": Vector3(0, 1.79, 0.06), "dist": 1.0, "eye": 1.8, "pose": "", "grey": true})
			_shots.append({"name": "p_eyes", "dir": Vector3(-0.25, 0, 1), "at": Vector3(0, 1.81, 0.12), "dist": 0.42, "eye": 1.82, "pose": "", "grey": false})
			_shots.append({"name": "p_eyes_grey", "dir": Vector3(-0.25, 0, 1), "at": Vector3(0, 1.81, 0.12), "dist": 0.42, "eye": 1.82, "pose": "", "grey": true})
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
			_sun.light_energy = 0.7
			_env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
			_env.ambient_light_energy = 0.45
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
