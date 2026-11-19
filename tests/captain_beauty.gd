extends SceneTree
## The new captain (models/captain.glb) as the game would show him: lit (a sun from his upper front left, soft sky
## light), a perspective camera of 35 degrees at about eye height. Front, three-quarter, side, three-quarter back, and a
## close head-and-shoulders three-quarter; cap on, then the same with the cap off.
##   godot --path . --audio-driver Dummy --resolution 700x900 -s tests/captain_beauty.gd -- --out=<folder>

const MODEL := "res://models/captain.glb"

var _out := ""
var _only: PackedStringArray = []
var _hide: PackedStringArray = []
var _cam: Camera3D
var _model: Node3D
var _shots: Array = []
var _frame := 0
var _sun: DirectionalLight3D
var _grey := StandardMaterial3D.new()
var _barrel: MeshInstance3D


## Turns a bone about a world axis through its own joint, from its rest (degrees).
func _turn(sk: Skeleton3D, bone: String, axis: Vector3, deg: float) -> void:
	var b := sk.find_bone(bone)
	if b < 0:
		return
	var g := sk.get_bone_global_rest(b).basis.orthonormalized()
	var d := g.inverse() * Basis(axis, deg_to_rad(deg)) * g
	sk.set_bone_pose_rotation(b, (sk.get_bone_rest(b).basis.orthonormalized() * d).get_rotation_quaternion())


func _pose(name: String) -> void:
	for sk: Skeleton3D in _model.find_children("*", "Skeleton3D", true, false):
		sk.reset_bone_poses()
		match name:
			"up":
				_turn(sk, "neck", Vector3.RIGHT, -10.0)
				_turn(sk, "head", Vector3.RIGHT, -20.0)
			"down":
				_turn(sk, "neck", Vector3.RIGHT, 7.0)
				_turn(sk, "head", Vector3.RIGHT, 13.0)
			"turn":
				_turn(sk, "neck", Vector3.UP, 15.0)
				_turn(sk, "head", Vector3.UP, 30.0)
			"h_fist":
				_apply(sk, HAND_FIST)
			"h_grip":
				_apply(sk, HAND_GRIP)
			"h_half":
				_apply(sk, HAND_HALF)
			"h_relaxed":
				_apply(sk, HAND_RELAXED)
			"armfwd":
				# (twenty-third round: the arms reached forward, so a side view of the boxers is not hidden by the hand)
				_apply(sk, [["aim", "upper_arm_l", "forearm_l", Vector3(0.15, -0.35, 0.95)], ["aim", "forearm_l", "hand_l", Vector3(0.05, -0.2, 1.0)],
					["aim", "upper_arm_r", "forearm_r", Vector3(-0.15, -0.35, 0.95)], ["aim", "forearm_r", "hand_r", Vector3(-0.05, -0.2, 1.0)]])
			"bend", "bendb":
				# (eighteenth round: "the bent 40 degrees shots do not actually bend the hand": the turn was about the
				# arm's front-to-back axis, a sideways swing that hardly shows from the front. Now the hand is FLEXED (and
				# with bendb extended) 40 degrees about the wrist's own across axis, as the poser turns bones)
				var deg := 40.0 if name == "bend" else -40.0
				_apply(sk, [["flex", "_l", deg], ["flex", "_r", deg]])
			_:
				if POSES.has(name):
					_apply(sk, POSES[name]["ops"])


# --- The pose test (eighteenth round; the user: "match the models to the poses as well to make sure the topology is
# poseablw"). The eight poses of tools/art_src/concept_captain_poses.jpg, made with the skeleton only (faces are rigged
# elsewhere). Coordinates: his left +X, up +Y, his front +Z, metres. Each pose is a list of operations:
#   ["rot", bone, axis, degrees]   the bone turned about its own joint, the axis as at rest, after its parent's turn
#   ["aim", bone, child, dir]      the bone turned so its line to `child` points along `dir` (world)
#   ["root", offset, axis, deg]    the hips (and so all of him) turned about their joint and moved
#   ["leg", side, ankle, knee dir, foot pitch]   this rig hangs shin and foot from the hips (as title_figures' _leg):
#                                  the knee found from the two lengths, the thigh, shin and foot set to reach the ankle
#   ["curl", side, [index, middle, ring, little], thumb]   degrees at each finger joint toward the palm
#   ["flex", side, deg]            the hand bent at the wrist toward the palm
const POSES := {
	"laugh": {"cam": [Vector3(0.35, 0.05, 1.0), Vector3(0, 0.9, 0.05), 3.0], "ops": [
		["rot", "spine", Vector3.RIGHT, -6.0], ["rot", "chest", Vector3.RIGHT, -6.0],
		["rot", "neck", Vector3.RIGHT, -6.0], ["rot", "head", Vector3.RIGHT, -9.0],
		["aim", "upper_arm_l", "forearm_l", Vector3(0.25, -0.75, 0.35)], ["aim", "forearm_l", "hand_l", Vector3(-0.75, -0.25, 0.6)],
		["aim", "upper_arm_r", "forearm_r", Vector3(-0.25, -0.75, 0.35)], ["aim", "forearm_r", "hand_r", Vector3(0.75, -0.15, 0.6)],
		["flex", "_l", -25.0], ["flex", "_r", -25.0], ["curl", "_l", [15, 15, 18, 20], 10], ["curl", "_r", [15, 15, 18, 20], 10],
		["leg", "_l", Vector3(0.2, 0.136, 0.02), Vector3(0.3, 0, 1), 0.0], ["leg", "_r", Vector3(-0.2, 0.136, 0.02), Vector3(-0.3, 0, 1), 0.0]]},
	"shock": {"cam": [Vector3(0.2, 0.05, 1.0), Vector3(0, 0.9, 0.05), 3.2], "ops": [
		["root", Vector3(0, -0.02, -0.04), Vector3.RIGHT, -8.0],
		["rot", "chest", Vector3.RIGHT, -6.0], ["rot", "head", Vector3.RIGHT, -8.0],
		["aim", "upper_arm_l", "forearm_l", Vector3(0.9, 0.15, 0.4)], ["aim", "forearm_l", "hand_l", Vector3(0.75, 0.55, 0.35)],
		["aim", "upper_arm_r", "forearm_r", Vector3(-0.9, 0.1, 0.4)], ["aim", "forearm_r", "hand_r", Vector3(-0.7, 0.6, 0.4)],
		["flex", "_l", -45.0], ["flex", "_r", -45.0], ["curl", "_l", [0, 0, 3, 5], 0], ["curl", "_r", [0, 0, 3, 5], 0],
		["leg", "_l", Vector3(0.2, 0.36, 0.3), Vector3(0.1, 0.3, 1), -25.0], ["leg", "_r", Vector3(-0.15, 0.136, -0.05), Vector3(0, 0, 1), 0.0]]},
	"swim": {"cam": [Vector3(1.0, 0.45, 0.15), Vector3(0, 0.75, 0.55), 3.9], "ops": [
		["root", Vector3(0, 0.15, 0.0), Vector3.RIGHT, 82.0],
		["rot", "neck", Vector3.RIGHT, -25.0], ["rot", "head", Vector3.RIGHT, -25.0],
		["aim", "upper_arm_l", "forearm_l", Vector3(0.35, 0.0, 1.0)], ["aim", "forearm_l", "hand_l", Vector3(0.2, -0.05, 1.0)],
		["aim", "upper_arm_r", "forearm_r", Vector3(-0.35, -0.15, 1.0)], ["aim", "forearm_r", "hand_r", Vector3(-0.15, -0.2, 1.0)],
		["curl", "_l", [5, 5, 5, 5], 0], ["curl", "_r", [5, 5, 5, 5], 0]]},
	"wheel": {"cam": [Vector3(-0.4, 0.1, 1.0), Vector3(0, 0.9, 0.05), 3.0], "ops": [
		["root", Vector3(0, -0.05, 0), Vector3.RIGHT, 8.0],
		["rot", "chest", Vector3.RIGHT, 4.0], ["rot", "head", Vector3.RIGHT, 8.0],
		["aim", "upper_arm_l", "forearm_l", Vector3(0.3, -0.25, 0.9)], ["aim", "forearm_l", "hand_l", Vector3(-0.1, 0.75, 0.65)],
		["aim", "upper_arm_r", "forearm_r", Vector3(-0.25, -0.9, 0.35)], ["aim", "forearm_r", "hand_r", Vector3(0.2, -0.2, 0.95)],
		["flex", "_l", 20.0], ["flex", "_r", 20.0], ["curl3", "_l", [[60, 70, 40], [62, 72, 40], [65, 72, 40], [68, 72, 40]]], ["curl", "_l", [0, 0, 0, 0], 35], ["curl3", "_r", [[60, 70, 40], [62, 72, 40], [65, 72, 40], [68, 72, 40]]], ["curl", "_r", [0, 0, 0, 0], 35],
		["leg", "_l", Vector3(0.33, 0.136, 0.12), Vector3(0.5, 0, 1), 0.0], ["leg", "_r", Vector3(-0.33, 0.136, -0.12), Vector3(-0.5, 0, 1), 0.0]]},
	"shout": {"cam": [Vector3(0.3, 0.05, 1.0), Vector3(0.1, 0.9, 0.05), 3.3], "ops": [
		["root", Vector3(0, -0.04, 0), Vector3.RIGHT, 6.0],
		["rot", "chest", Vector3.RIGHT, 4.0], ["rot", "neck", Vector3.UP, 15.0], ["rot", "head", Vector3.UP, 10.0],
		["aim", "upper_arm_l", "forearm_l", Vector3(0.85, 0.2, 0.5)], ["aim", "forearm_l", "hand_l", Vector3(0.85, 0.25, 0.5)],
		["aim", "upper_arm_r", "forearm_r", Vector3(-0.35, -0.55, 0.75)], ["aim", "forearm_r", "hand_r", Vector3(0.55, 0.8, 0.25)],
		["curl", "_l", [0, 85, 85, 85], 40], ["flex", "_r", 10.0], ["curl", "_r", [35, 35, 35, 35], 10],
		["leg", "_l", Vector3(0.28, 0.136, 0.08), Vector3(0.5, 0, 1), 0.0], ["leg", "_r", Vector3(-0.26, 0.136, -0.04), Vector3(-0.5, 0, 1), 0.0]]},
	"sit": {"cam": [Vector3(0.45, 0.15, 1.0), Vector3(0, 0.65, 0.15), 3.0], "ops": [
		["root", Vector3(0, -0.2, -0.05), Vector3.RIGHT, 12.0],
		["rot", "spine", Vector3.RIGHT, 10.0], ["rot", "chest", Vector3.RIGHT, 10.0], ["rot", "head", Vector3.RIGHT, 18.0],
		["aim", "upper_arm_l", "forearm_l", Vector3(0.3, -0.75, 0.55)], ["aim", "forearm_l", "hand_l", Vector3(-0.45, -0.15, 0.9)],
		["aim", "upper_arm_r", "forearm_r", Vector3(-0.3, -0.75, 0.55)], ["aim", "forearm_r", "hand_r", Vector3(0.45, -0.1, 0.9)],
		["curl", "_l", [40, 45, 50, 55], 20], ["curl", "_r", [40, 45, 50, 55], 20],
		# (twenty-third round: the feet further forward, so the thighs lie nearly level on the barrel as the sheet's;
		# at z 0.3 they sloped down through its rim)
		["leg", "_l", Vector3(0.3, 0.136, 0.44), Vector3(0.5, 0.3, 1), 0.0], ["leg", "_r", Vector3(-0.3, 0.136, 0.44), Vector3(-0.5, 0.3, 1), 0.0]]},
	"haul": {"cam": [Vector3(-0.5, 0.1, 1.0), Vector3(0, 0.75, 0.15), 3.1], "ops": [
		["root", Vector3(0, -0.08, -0.06), Vector3.RIGHT, 22.0],
		["rot", "spine", Vector3.RIGHT, 12.0], ["rot", "chest", Vector3.RIGHT, 8.0], ["rot", "neck", Vector3.RIGHT, -20.0],
		["rot", "chest", Vector3.UP, -12.0],
		["aim", "upper_arm_l", "forearm_l", Vector3(-0.2, -0.6, 0.8)], ["aim", "forearm_l", "hand_l", Vector3(-0.55, -0.35, 0.75)],
		["aim", "upper_arm_r", "forearm_r", Vector3(-0.45, -0.7, 0.55)], ["aim", "forearm_r", "hand_r", Vector3(-0.5, -0.2, 0.85)],
		["curl3", "_l", [[60, 70, 40], [62, 72, 40], [65, 72, 40], [68, 72, 40]]], ["curl", "_l", [0, 0, 0, 0], 35], ["curl3", "_r", [[60, 70, 40], [62, 72, 40], [65, 72, 40], [68, 72, 40]]], ["curl", "_r", [0, 0, 0, 0], 35],
		["leg", "_l", Vector3(0.25, 0.136, 0.25), Vector3(0.3, 0, 1), 0.0], ["leg", "_r", Vector3(-0.2, 0.136, -0.34), Vector3(-0.3, 0, 1), 0.0]]},
	"look_up": {"cam": [Vector3(-0.35, 0.05, 1.0), Vector3(0, 0.9, 0.05), 3.0], "ops": [
		["rot", "neck", Vector3.RIGHT, -4.0], ["rot", "head", Vector3.RIGHT, -6.0],
		["aim", "upper_arm_r", "forearm_r", Vector3(-0.75, 0.5, 0.45)], ["aim", "forearm_r", "hand_r", Vector3(0.6, 0.45, 0.65)],
		["flex", "_r", -20.0], ["curl", "_r", [35, 40, 45, 50], 20], ["curl", "_l", [10, 12, 15, 18], 5]]},
}


## (twenty-third round) The fist and the grip of the hands sheet, each joint its own angle (knuckle, middle, tip),
## the thumb across: tuned by the --hands pictures.
const HAND_FIST := [["curl3", "_l", [[85, 95, 55], [85, 95, 55], [88, 95, 55], [90, 95, 55]]],
	# (twenty-fourth round: the thumb's turns found by a search over its bones (each joint about the hand's three
	# axes) for its last joint over the index finger's middle bone and its tip toward the middle finger's, clear of
	# the fingers: it lies across the curled fingers' undersides, its tip no longer poking out below the fist. The
	# round-23 thumb was across -30, palm -40; thumb_2 palm -30; thumb_3 palm -39. Searched from the thumb's new rest,
	# turned out by thumb_rest)
	["thumbrot", "_l", "thumb_1", "along", 19.2], ["thumbrot", "_l", "thumb_1", "palm", -22.1], ["thumbrot", "_l", "thumb_1", "across", 28.9],
	["thumbrot", "_l", "thumb_2", "palm", -24.9], ["thumbrot", "_l", "thumb_2", "across", -15.3], ["thumbrot", "_l", "thumb_2", "along", 26.7],
	["thumbrot", "_l", "thumb_3", "palm", -50.5], ["thumbrot", "_l", "thumb_3", "across", -13.3], ["thumbrot", "_l", "thumb_3", "along", 47.4],
	# (the fingers drawn together at the knuckles, so the curled fingers close side by side, not as separate hooks)
	["thumbrot", "_l", "finger_index_1", "palm", -7.0], ["thumbrot", "_l", "finger_ring_1", "palm", 5.0], ["thumbrot", "_l", "finger_little_1", "palm", 10.0]]
## The relaxed hand of the sheet's back, palm and thumb views: the thumb turned out from under the palm about the
## hand's length (tried along +-40, across +-35, palm +-30 and pairs: this one lies as the sheet draws it), the
## fingers a little curved.
const HAND_RELAXED := [["curl3", "_l", [[6, 10, 6], [6, 10, 6], [7, 11, 7], [8, 12, 8]]]]
## (twenty-fourth round) A half-closed hand, between the relaxed hand and the grip, for checking the joints part way.
const HAND_HALF := [["curl3", "_l", [[40, 50, 30], [40, 50, 30], [42, 52, 30], [45, 55, 30]]]]
const HAND_GRIP := [["curl3", "_l", [[60, 70, 40], [62, 72, 40], [65, 72, 40], [68, 72, 40]]],
	# (twenty-fourth round: the thumb now rests turned out 40 degrees about the hand's length (thumb_rest); the last turn
	# below takes it back to the old rest first, so the grip's thumb lies as it did)
	["thumbrot", "_l", "thumb_1", "across", -20.0], ["thumbrot", "_l", "thumb_1", "palm", -28.0], ["thumbrot", "_l", "thumb_1", "along", 40.0], ["thumbrot", "_l", "thumb_2", "palm", -20.0], ["thumbrot", "_l", "thumb_3", "palm", -25.0],
	["thumbrot", "_l", "finger_index_1", "palm", -5.0], ["thumbrot", "_l", "finger_ring_1", "palm", 4.0], ["thumbrot", "_l", "finger_little_1", "palm", 8.0]]


## How far the clavicle lifts (degrees) for an arm straight up, and comes forward for an arm straight ahead.
const CLAV_RISE := 24.0
const CLAV_FWD := 14.0


## The rigid move of each bone (skeleton space) for a list of operations, then set as the bones' poses.
func _apply(sk: Skeleton3D, ops: Array) -> void:
	var n := sk.get_bone_count()
	var rest: Array[Transform3D] = []
	for b in n:
		rest.append(sk.get_bone_global_rest(b))
	var X: Array[Transform3D] = []
	X.resize(n)
	var done: Array[bool] = []
	done.resize(n)
	var order: Array[int] = []
	var stack: Array[int] = []
	for b in n:
		if sk.get_bone_parent(b) < 0:
			stack.append(b)
	while not stack.is_empty():
		var b: int = stack.pop_front()
		order.append(b)
		for c in sk.get_bone_children(b):
			stack.append(c)
	var legs := {}
	for op in ops:
		if op[0] == "leg":
			legs[op[1]] = op
	for b in order:
		var p := sk.get_bone_parent(b)
		X[b] = X[p] if p >= 0 else Transform3D.IDENTITY
		var bname := sk.get_bone_name(b)
		var h := rest[b].origin
		for op in ops:
			match String(op[0]):
				"root":
					if p < 0:
						X[b] = Transform3D(Basis.IDENTITY, op[1]) * _about(h, op[2], op[3])
				"rot":
					if op[1] == bname:
						X[b] = X[b] * _about(h, op[2], op[3])
				"aim":
					if op[1] == bname:
						var c := sk.find_bone(op[2])
						var cur: Vector3 = X[b].basis * (rest[c].origin - h)
						var hp: Vector3 = X[b] * h
						var q := Quaternion(cur.normalized(), (op[3] as Vector3).normalized())
						X[b] = Transform3D(Basis(q), hp - Basis(q) * hp) * X[b]
				"curl3":
					# (twenty-third round) ["curl3", side, [[knuckle, middle, tip] for index, middle, ring, little]]:
					# each joint its own angle (an even curl at every joint made hooks, not a fist)
					var sfx3 := String(op[1])
					if bname.ends_with(sfx3) and bname.begins_with("finger_"):
						var fi := ["index", "middle", "ring", "little"].find(bname.get_slice("_", 1))
						var ji := int(bname.get_slice("_", 2)) - 1
						X[b] = X[b] * _about(h, _curl_axis(sk, rest, sfx3), float(op[2][fi][ji]))
				"thumbrot":
					# ["thumbrot", side, bone, axis ("along", "across", "palm"), degrees]: a thumb bone turned about one of
					# the hand's own axes at rest
					if bname == String(op[2]) + String(op[1]):
						var fr := _hand_axes(sk, rest, String(op[1]))
						X[b] = X[b] * _about(h, fr[["along", "across", "palm"].find(String(op[3]))], float(op[4]))
				"flex":
					if bname == "hand" + String(op[1]):
						X[b] = X[b] * _about(h, _wrist_axis(sk, rest, String(op[1])), float(op[2]))
				"curl":
					var sfx := String(op[1])
					if bname.ends_with(sfx) and (bname.begins_with("finger_") or bname.begins_with("thumb_")):
						var deg := 0.0
						if bname.begins_with("thumb_"):
							deg = 0.0 if bname.begins_with("thumb_1") else float(op[3])
						else:
							deg = float(op[2][["index", "middle", "ring", "little"].find(bname.get_slice("_", 1))])
						X[b] = X[b] * _about(h, _curl_axis(sk, rest, sfx), deg)
		# (twentieth round, as the boy's viewer: the upper arm hangs from the clavicle, which lifts with the arm's rise
		# above level and comes forward with its reach, so the shoulder's top rises instead of folding)
		if bname.begins_with("clavicle"):
			var cs := bname.right(2)
			var ua := sk.find_bone("upper_arm" + cs)
			if ua >= 0 and sk.get_bone_parent(ua) == b:
				for op in ops:
					if op[0] == "aim" and op[1] == "upper_arm" + cs:
						var to: Vector3 = (op[3] as Vector3).normalized()
						var sg := 1.0 if cs == "_l" else -1.0
						var rise := clampf((to.y + 0.35) / 1.35, 0.0, 1.0) * CLAV_RISE
						var fwd := clampf(to.z, 0.0, 1.0) * CLAV_FWD - clampf(-to.z, 0.0, 1.0) * 8.0
						X[b] = X[b] * _about(h, Vector3.BACK, rise * sg) * _about(h, Vector3.UP, -fwd * sg)
		for sfx in legs:
			var op: Array = legs[sfx]
			if bname == "thigh" + sfx or bname == "shin" + sfx or bname == "foot" + sfx:
				X[b] = _leg_move(sk, rest, X, sfx, bname, op)
	for b in order:
		var p := sk.get_bone_parent(b)
		var g := X[b] * rest[b]
		var local := ((X[p] * rest[p]).affine_inverse() * g) if p >= 0 else g
		sk.set_bone_pose_position(b, local.origin)
		sk.set_bone_pose_rotation(b, local.basis.orthonormalized().get_rotation_quaternion())


func _about(h: Vector3, axis: Vector3, deg: float) -> Transform3D:
	var bs := Basis(axis.normalized(), deg_to_rad(deg))
	return Transform3D(bs, h - bs * h)


## The wrist's across axis, signed so a positive turn bends the hand toward the palm.
func _wrist_axis(sk: Skeleton3D, rest: Array[Transform3D], sfx: String) -> Vector3:
	var along := (rest[sk.find_bone("hand" + sfx)].origin - rest[sk.find_bone("forearm" + sfx)].origin).normalized()
	var k := _curl_axis(sk, rest, sfx)
	return (k - along * k.dot(along)).normalized()


## The knuckles' line, signed so a positive turn curls a finger toward the palm (the palm faces where the thumb's
## middle joint stands off the knuckles' plane).
func _curl_axis(sk: Skeleton3D, rest: Array[Transform3D], sfx: String) -> Vector3:
	var i := rest[sk.find_bone("finger_index_1" + sfx)].origin
	var l := rest[sk.find_bone("finger_little_1" + sfx)].origin
	var m3 := rest[sk.find_bone("finger_middle_3" + sfx)].origin
	var m1 := rest[sk.find_bone("finger_middle_1" + sfx)].origin
	var t2 := rest[sk.find_bone("thumb_2" + sfx)].origin
	var k := (l - i).normalized()
	var along := (m3 - m1).normalized()
	var palm := (t2 - m1)
	palm = (palm - along * palm.dot(along) - k * palm.dot(k)).normalized()
	# a positive turn about k moves `along` toward k x along; that must be toward the palm
	return k if k.cross(along).dot(palm) > 0.0 else -k


## The hand's own axes at rest (skeleton space): along (wrist to the middle knuckle), across (index to little
## knuckle, square to along), palm (out of the palm, the side the thumb's middle joint stands).
func _hand_axes(sk: Skeleton3D, rest: Array[Transform3D], sfx: String) -> Array:
	var w := rest[sk.find_bone("hand" + sfx)].origin
	var m1 := rest[sk.find_bone("finger_middle_1" + sfx)].origin
	var i1 := rest[sk.find_bone("finger_index_1" + sfx)].origin
	var l1 := rest[sk.find_bone("finger_little_1" + sfx)].origin
	var t2 := rest[sk.find_bone("thumb_2" + sfx)].origin
	var along := (m1 - w).normalized()
	var across := (l1 - i1)
	across = (across - along * across.dot(along)).normalized()
	var palm := along.cross(across)
	if palm.dot(t2 - m1) < 0.0:
		palm = -palm
	return [along, across, palm, w, m1]


## (twenty-third round) An orthographic camera 0.3 m tall on the left hand, in the hand's own frame at rest (the hand
## bone is never turned in these poses): each view says where the eye is, what is up and what is to the right; when
## the camera's right comes out the other way the picture is mirrored (_mirror) so it lies as the sheet draws it.
const HAND_VIEWS := {
	"back": [["palm", -1.0], ["across", 1.0], ["along", 1.0]],
	"palm": [["palm", 1.0], ["along", 1.0], ["across", -1.0]],
	"thumb": [["across", -1.0], ["palm", -1.0], ["along", -1.0]],
	"little": [["across", 1.0], ["palm", -1.0], ["along", 1.0]],
	"tips": [["along", 1.0], ["palm", -1.0], ["across", -1.0]],
	"fistview": [["palm", -1.0], ["across", 1.0], ["along", 1.0]],
}
const HAND_ORTHO := 0.3
var _mirror := false


func _hand_camera(spec: Dictionary, pose: String) -> void:
	var sk: Skeleton3D = _model.find_children("*", "Skeleton3D", true, false)[0]
	var rest: Array[Transform3D] = []
	for b in sk.get_bone_count():
		rest.append(sk.get_bone_global_rest(b))
	var fr := _hand_axes(sk, rest, String(spec["sfx"]))
	var gb := sk.global_transform.basis
	var ax := {"along": (gb * (fr[0] as Vector3)).normalized(), "across": (gb * (fr[1] as Vector3)).normalized(),
		"palm": (gb * (fr[2] as Vector3)).normalized()}
	var wrist: Vector3 = sk.global_transform * (fr[3] as Vector3)
	var v: Array = HAND_VIEWS[String(spec["view"])]
	var d: Vector3 = ax[v[0][0]] * float(v[0][1])
	if String(spec["view"]) == "tips":
		d = (d - ax["palm"] * 0.5).normalized()
	if String(spec["view"]) == "fistview":
		d = (d + ax["along"] * 0.6 - ax["across"] * 0.3).normalized()
	var up: Vector3 = ax[v[1][0]] * float(v[1][1])
	var right: Vector3 = ax[v[2][0]] * float(v[2][1])
	var at: Vector3 = wrist + ax["along"] * (0.1 if pose == "h_relaxed" else 0.075)
	_cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	_cam.size = HAND_ORTHO
	_cam.near = 0.8   # (only what lies within 20 cm of the hand: the thigh and boxers were in front of it)
	_cam.far = 1.2
	_cam.position = at + d * 1.0
	_cam.look_at(at, up)
	_mirror = _cam.global_transform.basis.x.dot(right) < 0.0


func _leg_move(sk: Skeleton3D, rest: Array[Transform3D], X: Array[Transform3D], sfx: String, bname: String, op: Array) -> Transform3D:
	var hb := sk.find_bone("hips")
	var H0 := rest[sk.find_bone("thigh" + sfx)].origin
	var K0 := rest[sk.find_bone("shin" + sfx)].origin
	var A0 := rest[sk.find_bone("foot" + sfx)].origin
	var H: Vector3 = X[hb] * H0
	var A: Vector3 = op[2]
	var a := (K0 - H0).length()
	var b := (A0 - K0).length()
	var d := clampf((A - H).length(), 0.05, a + b - 0.002)
	var dir := (A - H).normalized()
	A = H + dir * d
	var along := (a * a - b * b + d * d) / (2.0 * d)
	var hh := sqrt(maxf(a * a - along * along, 0.0))
	var pole: Vector3 = (op[3] as Vector3).normalized()
	var pp := (pole - dir * pole.dot(dir)).normalized()
	var K := H + dir * along + pp * hh
	if bname == "thigh" + sfx:
		return _seg_move(H0, K0, H, K, pole)
	if bname == "shin" + sfx:
		return _seg_move(K0, A0, K, A, pole)
	var fb := X[hb].basis * Basis(Vector3.RIGHT, deg_to_rad(float(op[4])))
	return Transform3D(fb, A - fb * A0)


## The rigid move taking the segment p0->q0 (its pole the front at rest) to p1->q1 with its pole toward `pole`.
func _seg_move(p0: Vector3, q0: Vector3, p1: Vector3, q1: Vector3, pole: Vector3) -> Transform3D:
	var u0 := (q0 - p0).normalized()
	var f0 := Vector3.BACK - u0 * Vector3.BACK.dot(u0)
	f0 = f0.normalized()
	var u1 := (q1 - p1).normalized()
	var f1 := (pole - u1 * pole.dot(u1)).normalized()
	var B0 := Basis(u0, f0, u0.cross(f0))
	var B1 := Basis(u1, f1, u1.cross(f1))
	var R := B1 * B0.inverse()
	return Transform3D(R, p1 - R * p0)


func _initialize() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			_out = a.get_slice("=", 1)
		if a.begins_with("--only="):
			_only = a.get_slice("=", 1).split(",")
		if a.begins_with("--hide="):
			_hide = a.get_slice("=", 1).split(",")
	var world := Node3D.new()
	root.add_child(world)
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.78, 0.8, 0.82)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	# (fourteenth round: the shaded side went near black and grey under a weak blue sky light; a fuller, more neutral
	# sky light, as an outdoor day scene has)
	env.ambient_light_color = Color(0.86, 0.87, 0.9)
	env.ambient_light_energy = 0.35
	env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	var we := WorldEnvironment.new()
	we.environment = env
	world.add_child(we)
	var sun := DirectionalLight3D.new()
	sun.basis = Basis.looking_at(Vector3(-0.5, -0.7, -0.55).normalized(), Vector3.UP)
	sun.light_energy = 0.6
	_sun = sun
	sun.shadow_enabled = true
	world.add_child(sun)
	_model = (load(MODEL) as PackedScene).instantiate() as Node3D
	world.add_child(_model)
	for mesh: MeshInstance3D in _model.find_children("*", "MeshInstance3D", true, false):
		mesh.lod_bias = 64.0
		if String(mesh.name).begins_with("captain_body_under"):
			mesh.visible = false
	_grey.albedo_color = Color(0.7, 0.7, 0.7)
	_grey.roughness = 0.8
	# (twentieth round: 4x multisampling, so silhouettes are not stair-stepped into what reads as shards)
	root.msaa_3d = Viewport.MSAA_4X
	_cam = Camera3D.new()
	_cam.fov = 35.0
	_cam.near = 0.05
	world.add_child(_cam)
	for cap in [true, false]:
		var tag := "" if cap else "_nocap"
		for b in [["front", Vector3(0, 0, 1)], ["three_quarter", Vector3(0.7, 0, 0.7)], ["side", Vector3(-1, 0, 0)], ["three_quarter_back", Vector3(0.7, 0, -0.7)]]:
			_shots.append([b[0] + tag, (b[1] as Vector3).normalized(), Vector3(0, 0.86, 0), 3.3, cap])
		# (the close head shot pulled back and up a little: it cut off the top of his head)
		_shots.append(["close" + tag, Vector3(0.62, 0.05, 0.78).normalized(), Vector3(0.0, 1.4, 0.03), 1.95, cap])
	# close-ups of his left hand and left foot (cap on; it does not show)
	_shots.append(["hand", Vector3(0.75, 0.1, 0.65).normalized(), Vector3(0.43, 0.7, 0.0), 0.75, true])
	_shots.append(["foot", Vector3(0.35, 0.5, 0.8).normalized(), Vector3(0.17, 0.05, 0.1), 0.7, true])
	# (fifteenth round: the boxers close, from his front three-quarter)
	_shots.append(["boxers", Vector3(0.55, 0.12, 0.83).normalized(), Vector3(0.0, 0.62, 0.0), 1.05, true])
	# (seventeenth round, the user: "stop his chin and jaw phasing into his neck- have a pose where he is looking up to
	# see what I mean"; "his forearms and wrists"): the head tilted back 30 degrees (a third of it on the neck), down 20,
	# turned 45 to his left; painted and in grey (a plain grey material over everything); a close wrist from his left
	for g in [false, true]:
		var gt := "_grey" if g else ""
		for b in [["front", Vector3(0, -0.1, 1)], ["three_quarter", Vector3(0.7, -0.1, 0.7)], ["side", Vector3(-1, -0.1, 0)]]:
			_shots.append(["up_" + b[0] + gt, (b[1] as Vector3).normalized(), Vector3(0, 1.36, 0.03), 0.95, false, "up", g])
		_shots.append(["down_three_quarter" + gt, Vector3(0.7, 0.1, 0.7).normalized(), Vector3(0, 1.36, 0.03), 0.95, false, "down", g])
		_shots.append(["turn_front" + gt, Vector3(0, 0, 1), Vector3(0, 1.36, 0.03), 0.95, false, "turn", g])
		_shots.append(["wrist_front" + gt, Vector3(0.2, 0.05, 1).normalized(), Vector3(0.45, 0.8, 0.0), 0.6, true, "", g])
		_shots.append(["wrist_back" + gt, Vector3(0.2, 0.05, -1).normalized(), Vector3(0.45, 0.8, 0.0), 0.6, true, "", g])
		_shots.append(["wrist_out" + gt, Vector3(1, 0.05, 0.1).normalized(), Vector3(0.45, 0.8, 0.0), 0.6, true, "", g])
		_shots.append(["wrist_bent" + gt, Vector3(0.6, 0.05, 0.8).normalized(), Vector3(0.45, 0.8, 0.0), 0.6, true, "bend", g])
		_shots.append(["wrist_bentb" + gt, Vector3(0.6, 0.05, 0.8).normalized(), Vector3(0.45, 0.8, 0.0), 0.6, true, "bendb", g])
	# (nineteenth round: large close-ups of his left hand from four sides and his left foot from three, lit and grey; his
	# whole body in grey from the front, side and back)
	for g in [false, true]:
		var gt := "_grey" if g else ""
		for b in [["out", Vector3(1, 0.1, 0.2)], ["front", Vector3(0.2, 0.05, 1)], ["back", Vector3(0.25, 0.05, -1)], ["under", Vector3(-0.35, -0.55, 0.75)]]:
			_shots.append(["bighand_" + b[0] + gt, (b[1] as Vector3).normalized(), Vector3(0.53, 0.6, 0.02), 0.5, true, "", g])
		for b in [["front", Vector3(0.05, 0.35, 1)], ["side", Vector3(1, 0.15, 0.05)], ["top", Vector3(0.25, 1, 0.45)]]:
			_shots.append(["bigfoot_" + b[0] + gt, (b[1] as Vector3).normalized(), Vector3(0.17, 0.0, 0.16), 0.5, true, "", g])   # (twenty-first round: framed lower and wider, the foot whole)
	for b in [["front", Vector3(0, 0, 1)], ["side", Vector3(-1, 0, 0)], ["back", Vector3(0, 0, -1)]]:
		_shots.append(["greybody_" + b[0], b[1], Vector3(0, 0.8, 0), 3.0, false, "", true])
	# (twenty-second round: close-ups aimed at a bone of the posed figure (shot[7]): the wheel's fist and the net's grip,
	# the heel from behind, the boxers seated (side and back) and standing from the side, lit and grey)
	for g in [false, true]:
		var gt := "_grey" if g else ""
		_shots.append(["fist_back" + gt, Vector3(0.9, 0.3, 0.3).normalized(), Vector3.ZERO, 0.32, true, "wheel", g, "finger_middle_1_l"])
		_shots.append(["fist_front" + gt, Vector3(0.3, 0.2, 1).normalized(), Vector3.ZERO, 0.32, true, "wheel", g, "finger_middle_1_l"])
		_shots.append(["grip" + gt, Vector3(0.8, 0.3, 0.6).normalized(), Vector3.ZERO, 0.32, true, "haul", g, "finger_middle_1_l"])
		_shots.append(["heel_back" + gt, Vector3(0.15, 0.2, -1).normalized(), Vector3.ZERO, 0.45, true, "", g, "foot_l"])
		_shots.append(["boxers_sit_side" + gt, Vector3(-1, 0.1, 0.15).normalized(), Vector3.ZERO, 1.1, true, "sit", g, "hips"])
		_shots.append(["boxers_sit_back" + gt, Vector3(0.3, 0.15, -1).normalized(), Vector3.ZERO, 1.1, true, "sit", g, "hips"])
		_shots.append(["boxers_side" + gt, Vector3(-1, 0.05, 0.1).normalized(), Vector3(0, 0.62, 0.02), 1.0, true, "", g])
	# (twenty-third round: the before-and-after views of each adjustment, r23_<feature>_<view>, lit and grey)
	for g in [false, true]:
		var gt := "_grey" if g else ""
		var hd := Vector3(0, 1.395, 0.1)
		for s in [
				["box_front", Vector3(0, 0.05, 1), Vector3(0, 0.6, 0.02), 1.5, true, "armfwd"],
				["box_side", Vector3(-1, 0.05, 0.05), Vector3(0, 0.6, 0.02), 1.5, true, "armfwd"],
				["box_back", Vector3(0.1, 0.05, -1), Vector3(0, 0.6, 0.0), 1.5, true, "armfwd"],
				["box_sit", Vector3(-1, 0.15, -0.15), Vector3.ZERO, 1.5, true, "sit", "hips"],
				["box_sitb", Vector3(0.3, 0.15, -1), Vector3.ZERO, 1.5, true, "sit", "hips"],
				["box_haul", Vector3(-0.6, 0.1, 1), Vector3.ZERO, 1.9, true, "haul", "hips"],
				["heel_back", Vector3(0.1, 0.15, -1), Vector3.ZERO, 0.6, true, "", "foot_l"],
				["heel_q", Vector3(0.7, 0.15, -0.7), Vector3.ZERO, 0.6, true, "", "foot_l"],
				["toe_front", Vector3(0.4, 0.18, 0.9), Vector3(0.2, 0.03, 0.19), 0.36, true, ""],
				["toe_q", Vector3(0.9, 0.5, 0.3), Vector3(0.21, 0.025, 0.2), 0.32, true, ""],
				["nose_front", Vector3(0, 0, 1), hd, 0.42, false, ""],
				["nose_q", Vector3(0.7, 0, 0.7), hd, 0.42, false, ""],
				["nose_side", Vector3(-1, 0, 0), hd, 0.42, false, ""],
				["nose_below", Vector3(0.2, -0.6, 0.8), hd, 0.42, false, ""],
				["ear_side", Vector3(1, 0, 0.05), Vector3(0.05, 1.4, 0.0), 0.4, false, ""],
				["ear_back", Vector3(0.3, 0.05, -1), Vector3(0.0, 1.4, 0.0), 0.55, false, ""],
				["torso_back", Vector3(0.0, 0.05, -1), Vector3(0, 1.0, 0), 1.5, false, ""],
				["torso_front", Vector3(0.0, 0.05, 1), Vector3(0, 1.0, 0), 1.5, false, ""],
				["torso_q", Vector3(0.7, 0.05, 0.7), Vector3(0, 1.0, 0), 1.5, false, ""],
				["jaw_up_side", Vector3(-1, -0.1, 0), Vector3(0, 1.36, 0.03), 0.95, false, "up"],
				["jaw_up_q", Vector3(0.7, -0.1, 0.7), Vector3(0, 1.36, 0.03), 0.95, false, "up"],
				["jaw_front", Vector3(0.0, 0.0, 1), Vector3(0, 1.36, 0.03), 0.8, false, ""],
				["fist_back", Vector3(0.9, 0.3, 0.3), Vector3.ZERO, 0.32, true, "wheel", "finger_middle_1_l"],
				["fist_front", Vector3(0.3, 0.2, 1), Vector3.ZERO, 0.32, true, "wheel", "finger_middle_1_l"],
				["fist_grip", Vector3(0.8, 0.3, 0.6), Vector3.ZERO, 0.32, true, "haul", "finger_middle_1_l"],
				["nail_top", Vector3(0.6, 0.6, 0.6), Vector3(0.53, 0.6, 0.02), 0.35, true, ""]]:
			var sh_: Array = ["r23_" + s[0] + gt, (s[1] as Vector3).normalized(), s[2], s[3], s[4], s[5], g]
			if s.size() > 6:
				sh_.append(s[6])
			_shots.append(sh_)
	# (eighteenth round: --poses: the pose test alone: each pose from the sheet's angle and from a quarter turn round,
	# lit and in grey, cap on)
	if "--poses" in OS.get_cmdline_user_args():
		_shots = []
		for pname: String in POSES:
			var cam: Array = POSES[pname]["cam"]
			var d0: Vector3 = (cam[0] as Vector3).normalized()
			var d1: Vector3 = Basis(Vector3.UP, deg_to_rad(-80.0 if d0.x >= 0.0 else 80.0)) * d0
			for g in [false, true]:
				var gt := "_grey" if g else ""
				_shots.append(["pose_" + pname + "_a" + gt, d0, cam[1], cam[2], true, pname, g])
				_shots.append(["pose_" + pname + "_b" + gt, d1, cam[1], cam[2], true, pname, g])
	# (twenty-third round: --hands: his hands alone, orthographic, 0.3 m tall, in the hand's own frame, the views of
	# tools/art_src/concept_captain_hands.jpg: relaxed (back, palm, thumb side, little-finger side, fingertips on),
	# the fist and the grip round a spoke; mirrored where needed so each lies as the sheet draws it)
	if "--hands" in OS.get_cmdline_user_args():
		_shots = []
		# (twenty-fourth round: a darker grey for the hands, so the raking light shows knuckles and folds)
		_grey.albedo_color = Color(0.55, 0.55, 0.55)
		var vs := {"relaxed": ["back", "palm", "thumb", "little", "tips"], "fist": ["fistview", "back", "thumb", "tips", "little", "palm"],
			"grip": ["back", "thumb", "tips"], "half": ["back", "thumb", "palm"]}
		for pz: String in vs:
			for g in [false, true]:
				var gt := "_grey" if g else ""
				for v: String in vs[pz]:
					_shots.append(["hand_" + pz + "_" + v + gt, Vector3.ZERO, Vector3.ZERO, 1.0, true, "h_" + pz, g, "", {"view": v, "sfx": "_l"}])
	# (eighteenth round: --only=<a,b> keeps the shots whose names begin with one of them)
	if not _only.is_empty():
		_shots = _shots.filter(func(s: Array) -> bool:
			for o in _only:
				if String(s[0]).begins_with(o):
					return true
			return false)


func _process(_delta: float) -> bool:
	var f := _frame
	_frame += 1
	var i := f / 5
	if i >= _shots.size():
		return true
	var shot: Array = _shots[i]
	if f % 5 == 0:
		for mesh: MeshInstance3D in _model.find_children("captain_cap*", "MeshInstance3D", true, false):
			mesh.visible = shot[4]
		_pose(String(shot[5]) if shot.size() > 5 else "")
		# (nineteenth round, the fourth critic: "with no seat he crouches in the air": a stand-in barrel under him in
		# the seated pose only)
		if _barrel == null:
			_barrel = MeshInstance3D.new()
			var cyl := CylinderMesh.new()
			cyl.top_radius = 0.27
			cyl.bottom_radius = 0.25
			cyl.height = 0.4
			_barrel.mesh = cyl
			var bm := StandardMaterial3D.new()
			bm.albedo_color = Color(0.45, 0.3, 0.18)
			_barrel.material_override = bm
			# (twenty-third round: back under his seat and a little lower; it stood in front, through his thighs, and
			# cut the boxers' legs off at its rim, which read as a flap)
			_barrel.position = Vector3(0, 0.2, -0.17)
			_model.get_parent().add_child(_barrel)
		_barrel.visible = shot.size() > 5 and String(shot[5]) == "sit"
		var grey: bool = shot.size() > 6 and bool(shot[6])
		for mesh: MeshInstance3D in _model.find_children("*", "MeshInstance3D", true, false):
			mesh.material_override = _grey if grey and not String(mesh.name).begins_with("captain_ink") else null
			if String(mesh.name).begins_with("captain_ink"):
				mesh.visible = not grey
			for hn in _hide:
				if String(mesh.name).begins_with(hn):
					mesh.visible = false
		var at: Vector3 = shot[2]
		if shot.size() > 7:
			for sk: Skeleton3D in _model.find_children("*", "Skeleton3D", true, false):
				var bi := sk.find_bone(String(shot[7]))
				if bi >= 0:
					at = (sk.global_transform * sk.get_bone_global_pose(bi)).origin
					if String(shot[7]) == "foot_l":
						at.y = 0.05
		# (the eye at about his eye height for the whole-body views, looking a little down at his middle)
		var eye: Vector3 = at + (shot[1] as Vector3) * float(shot[3])
		if float(shot[3]) > 2.0 and not POSES.has(String(shot[5]) if shot.size() > 5 else ""):
			eye.y = 1.5
		_cam.position = eye
		_mirror = false
		if shot.size() > 8:
			_hand_camera(shot[8], String(shot[5]))
			eye = _cam.position
			at = _cam.position - _cam.global_transform.basis.z
		else:
			_cam.projection = Camera3D.PROJECTION_PERSPECTIVE
			_cam.near = 0.05
			_cam.far = 100.0
			_cam.look_at(at, Vector3.UP)
		# (the sun over the camera's left shoulder for every shot, so no view is lit from behind)
		var to := (at - eye).normalized()
		var light := (to + _cam.global_transform.basis.x * -0.45 + Vector3(0, -0.6, 0)).normalized()
		if shot.size() > 8:
			# (twenty-fourth round: the hand views light from the picture's upper left, raking, in the camera's own
			# frame: lit from the eye, the grey hands read as flat white cut-outs with no knuckles or folds)
			light = (to * 0.8 + _cam.global_transform.basis.x * 0.45 - _cam.global_transform.basis.y * 0.55).normalized()
		_sun.shadow_enabled = shot.size() <= 8   # (the hand's shadow fell on the thigh behind it as a second dark hand)
		_sun.basis = Basis.looking_at(light, Vector3.UP)
	elif f % 5 == 4 and _out != "":
		var img := root.get_texture().get_image()
		if _mirror:
			img.flip_x()
		img.save_png("%s/%s.png" % [_out, shot[0]])
	return false
