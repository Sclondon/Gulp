class_name TitleFigures
extends RefCounted
## The three figures of the title scene, ready to drop in: the boy from Warren, a sea captain and an old-time
## diver (models/title_*.glb, built by tools/build_title_figures.py; tools/TITLE_FIGURES.md says what each is).
##
##     var boy := TitleFigures.boy()          # stands at his origin, feet at y = 0, facing -Z
##     add_child(boy)                         # he breathes and looks about by himself once in the tree
##     TitleFigures.head_node(boy).add_child(helmet)   # rides on his head, turns with it
##     TitleFigures.look_at_point(boy, screen.global_position)   # and TitleFigures.look_about(boy) to let go
##
## All three are on the boy's skeleton (GameCommon's character controller) and are posed here, live, a few bones
## each frame: breathing, a little sway, hands at rest, the head turned toward what they look at. (Not the
## controller's CharacterRig: Gulp has a `Player` of its own, the fish, which the rig would collide with.)

const BOY_MODEL := "res://models/title_boy.glb"
const CAPTAIN_MODEL := "res://models/title_captain.glb"
const DIVER_MODEL := "res://models/title_diver.glb"
## The adults are modelled 1.25 m tall, as the boy is, and stood this much bigger (1.8 m).
const ADULT_SCALE := 1.44

enum Kind { BOY, CAPTAIN, DIVER }


static func boy() -> Node3D:
	return _make(BOY_MODEL, Kind.BOY, 1.0)


static func captain() -> Node3D:
	return _make(CAPTAIN_MODEL, Kind.CAPTAIN, ADULT_SCALE)


static func diver() -> Node3D:
	return _make(DIVER_MODEL, Kind.DIVER, ADULT_SCALE)


## Where a helmet goes on the boy: a BoneAttachment3D on his head bone, at the joint where the head meets the neck
## (0.0, 1.012, 0.0) when he stands straight; in its own frame +Y is up and +Z is the way he faces (his model is
## made facing +Z and turned round under the root). His head's size and top: tools/TITLE_FIGURES.md.
static func head_node(figure: Node3D) -> Node3D:
	return (figure as Idle).head_mount if figure is Idle else null


## Turns the figure's head (the diver: his whole top half, the helmet being fixed to his breastplate) toward a
## point in the world, as far as a neck goes; eased.
static func look_at_point(figure: Node3D, world_point: Vector3) -> void:
	if figure is Idle:
		(figure as Idle).look_target = world_point
		(figure as Idle).looking = true


## Lets the figure look about by itself again.
static func look_about(figure: Node3D) -> void:
	if figure is Idle:
		(figure as Idle).looking = false


static func _make(path: String, kind: Kind, size: float) -> Node3D:
	var figure := Idle.new()
	figure.name = String(Kind.keys()[kind]).capitalize()
	figure.kind = kind
	var model := (load(path) as PackedScene).instantiate() as Node3D
	model.name = "Model"
	# (modelled facing +Z, as the boy's rig wants; turned to face -Z)
	model.rotation.y = PI
	model.scale = Vector3.ONE * size
	figure.add_child(model)
	figure.skeleton = model.find_children("*", "Skeleton3D", true, false)[0] as Skeleton3D
	for mesh: MeshInstance3D in model.find_children("*", "MeshInstance3D", true, false):
		# (the importer's automatic LODs bend a skinned body in straight pieces; seen close, never wanted)
		mesh.lod_bias = 64.0
	var mount := BoneAttachment3D.new()
	mount.name = "HeadMount"
	mount.bone_name = "head"
	figure.skeleton.add_child(mount)
	figure.head_mount = mount
	figure.seed_time = float(kind) * 2.3
	return figure


## A figure standing about: poses its skeleton every frame.
class Idle extends Node3D:
	var kind := Kind.BOY
	var skeleton: Skeleton3D
	var head_mount: BoneAttachment3D
	var look_target := Vector3.ZERO
	var looking := false
	var seed_time := 0.0
	var _time := 0.0
	var _look := Vector2.ZERO  # yaw, pitch, eased
	var _bones := {}

	func _ready() -> void:
		_time = seed_time
		for i in skeleton.get_bone_count():
			_bones[skeleton.get_bone_name(i)] = i

	func _turn(bone: String, rotation_now: Quaternion) -> void:
		var i: int = _bones.get(bone, -1)
		if i >= 0:
			skeleton.set_bone_pose_rotation(i, rotation_now)

	func _process(delta: float) -> void:
		_time += delta
		var breath := sin(_time * TAU / 4.2)
		var sway := sin(_time * TAU / 7.3 + 1.0)
		# Where to look: the target, or a slow wander about the middle distance.
		var want := Vector2(sin(_time * 0.37) * 0.25 + sin(_time * 0.13) * 0.15, 0.05 + sin(_time * 0.29) * 0.06)
		var head_bone: int = _bones.get("head", -1)
		if looking and head_bone >= 0:
			var at := skeleton.get_bone_global_rest(head_bone).origin
			var d := skeleton.global_transform.affine_inverse() * look_target - at
			var flat := Vector2(d.x, d.z).length()
			want = Vector2(atan2(d.x, d.z), -atan2(d.y, flat))
		var reach := Vector2(0.75, 0.45) if kind == Kind.DIVER else Vector2(1.25, 0.6)
		want = want.clamp(-reach, reach)
		_look = _look.lerp(want, 1.0 - exp(-delta * 3.0))
		var yaw := _look.x
		var pitch := _look.y
		_turn("spine", Quaternion.from_euler(Vector3(breath * 0.01, yaw * 0.35 if kind == Kind.DIVER else yaw * 0.08, sway * 0.012)))
		var chest_yaw := yaw * 0.65 if kind == Kind.DIVER else yaw * 0.12
		var chest_pitch := pitch * 0.4 if kind == Kind.DIVER else 0.0
		_turn("chest", Quaternion.from_euler(Vector3(-breath * 0.018 + chest_pitch, chest_yaw, -sway * 0.008)))
		if kind != Kind.DIVER:
			_turn("neck", Quaternion.from_euler(Vector3(pitch * 0.4, yaw * 0.32, 0.0)))
			_turn("head", Quaternion.from_euler(Vector3(pitch * 0.6, yaw * 0.48, -sway * 0.01)))
		if kind == Kind.BOY:
			# His arms are made straight out to the sides: down by his sides, the elbows a little bent.
			var down := deg_to_rad(80.0) + breath * 0.015
			_turn("upper_arm_l", Quaternion(Vector3.BACK, -down))
			_turn("upper_arm_r", Quaternion(Vector3.BACK, down))
			_turn("forearm_l", Quaternion(Vector3.UP, -0.22))
			_turn("forearm_r", Quaternion(Vector3.UP, 0.22))
			for side in ["l", "r"]:
				var curl := -0.32 if side == "l" else 0.32
				for f in 4:
					for joint in ["a", "b", "c"]:
						_turn("finger%d%s_%s" % [f, joint, side], Quaternion(Vector3.BACK, curl))
				_turn("thumba_" + side, Quaternion(Vector3.BACK, curl * 0.4))
		else:
			# The adults' arms are made hanging: only the breath in them, and the elbows a little bent.
			_turn("upper_arm_l", Quaternion(Vector3.BACK, breath * 0.012))
			_turn("upper_arm_r", Quaternion(Vector3.BACK, -breath * 0.012))
			_turn("forearm_l", Quaternion(Vector3.RIGHT, -0.12))
			_turn("forearm_r", Quaternion(Vector3.RIGHT, -0.12))
