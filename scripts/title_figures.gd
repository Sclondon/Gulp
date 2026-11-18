class_name TitleFigures
extends RefCounted
## The three figures of the title scene, ready to drop in: the boy from Warren, a sea captain and an old-time
## diver (models/title_*.glb, built by tools/build_title_figures.py; tools/TITLE_FIGURES.md says what each is).
##
##     var boy := TitleFigures.boy()          # at his origin on the deck, facing -Z; at work once in the tree
##     add_child(boy)
##     TitleFigures.head_node(boy).add_child(helmet)   # rides on his head, turns with it
##     TitleFigures.look_at_point(boy, screen.global_position)   # and TitleFigures.look_about(boy) to let go
##
## What each does (the user, 2026-11-18: "The captain needs to be driving the boat ..., the boy sitting on a stool
## plugged into the vr head set, and the diver operating machinery in the back"):
## - the boy sits on a stool (its seat BOY_SEAT_HEIGHT above his origin), feet on its rung, his left hand working a
##   stick at BOY_LEFT_HAND and his right on a button at BOY_RIGHT_HAND;
## - the captain stands at a ship's wheel (hub CAPTAIN_WHEEL_HUB, rim CAPTAIN_WHEEL_RADIUS), both hands on the rim at
##   ten and two, turning it a little now and then: `wheel_turn(captain)` is how far, to turn the boat's wheel by;
## - the diver turns the crank of a hand pump (hub DIVER_CRANK_HUB, handle on a circle of DIVER_CRANK_RADIUS in the
##   up-and-forward plane), both hands on its handle, one turn every DIVER_CRANK_TURN seconds: `crank_angle(diver)`.
## `stand(figure)` gives the plain standing idle instead.
##
## All points are in the figure's own space (its root): metres, Y up, -Z ahead of him, +X to HIS RIGHT.
##
## The boy is GameCommon's boy (character controller); the captain and the diver are GameCommon's man (godot/man,
## Gloaming's), on the same skeleton. They are posed here, live, a few bones each frame, the arms and legs by a
## two-bone solve so the hands and feet are where they should be. (Not the controller's CharacterRig: Gulp has a
## `Player` of its own, the fish, which the rig would collide with.)

const BOY_MODEL := "res://models/title_boy.glb"
const CAPTAIN_MODEL := "res://models/title_captain.glb"
const DIVER_MODEL := "res://models/title_diver.glb"
## The adults are modelled 1.25 m tall, as the boy is, and stood this much bigger (1.8 m).
const ADULT_SCALE := 1.44

## The boy's stool: its seat this high above his origin (the stool stands at his origin), and the rung his feet rest
## on (where his soles are: the middle between them, and how far apart).
const BOY_SEAT_HEIGHT := 0.42
const BOY_RUNG := Vector3(0.0, 0.14, -0.2)
const BOY_FEET_APART := 0.16
## Where his hands are: the left round the ball of a stick, the right on a button (the middle of the grip).
const BOY_LEFT_HAND := Vector3(-0.2, 0.8, -0.32)
const BOY_RIGHT_HAND := Vector3(0.2, 0.74, -0.32)
## The ship's wheel: its hub, and the radius of the rim his hands hold. Its axis is along his facing.
const CAPTAIN_WHEEL_HUB := Vector3(0.0, 1.05, -0.45)
const CAPTAIN_WHEEL_RADIUS := 0.3
## The pump's crank: its hub, the radius of the handle's circle (its axis along his left-right), seconds a turn.
const DIVER_CRANK_HUB := Vector3(0.0, 1.0, -0.34)
const DIVER_CRANK_RADIUS := 0.2
const DIVER_CRANK_TURN := 2.4

enum Kind { BOY, CAPTAIN, DIVER }
## How far each brings his arms down from the T pose he is made in, standing (degrees).
const ARM_DOWN := [80.0, 79.0, 70.0]
## How far each model's soles are above its origin as built (the man's boots stand 0.0075 up), taken off.
const SINK := [0.0, 0.011, 0.0]


static func boy() -> Node3D:
	return _make(BOY_MODEL, Kind.BOY, 1.0)


static func captain() -> Node3D:
	return _make(CAPTAIN_MODEL, Kind.CAPTAIN, ADULT_SCALE)


static func diver() -> Node3D:
	return _make(DIVER_MODEL, Kind.DIVER, ADULT_SCALE)


## Where a helmet goes on the boy: a BoneAttachment3D on his head bone, at the joint where the head meets the neck;
## in its own frame +Y is up and +Z is the way he faces (his model is made facing +Z and turned round under the
## root). Where it is when he sits, and his head's size: tools/TITLE_FIGURES.md.
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


## Which look the captain wears (the user, 2026-11-18: "the captain should have the outfit from teh first concept as
## well to switch into", and his base body "so you can add clothes on top"): "open" (his coat open over a striped
## undershirt; the default), "closed" (the navy gansey) or "boxers" (his base body in heart-print boxer shorts).
## His model's meshes named <part>__<looks> show in the looks listed after the "__" (joined by "_"); the rest always.
static func wear(figure: Node3D, outfit: String) -> void:
	_choose(figure, OUTFITS, outfit)


## Which face the captain has (a test, the user, 2026-11-18: "can the models look that good? remember twilight
## princess", "lets try it"): "painted" (a low-poly head with a face painted from the concept; the default for the
## test) or "mask" (the smooth mask face with modelled slits for eyes).
static func face(figure: Node3D, which: String) -> void:
	_choose(figure, FACES, which)


const OUTFITS := ["open", "closed", "boxers"]
const FACES := ["mask", "painted"]


## Shows, of the meshes named <part>__<options> whose options are among `options`, those that list `chosen`.
static func _choose(figure: Node3D, options: Array, chosen: String) -> void:
	for mesh: MeshInstance3D in figure.find_children("*__*", "MeshInstance3D", true, false):
		var listed := String(mesh.name).get_slice("__", 1).split("_")
		if Array(listed).any(func(o: String) -> bool: return o in options):
			mesh.visible = chosen in listed


## The plain standing idle instead of the figure's task (`work(figure)` puts him back to it).
static func stand(figure: Node3D) -> void:
	if figure is Idle:
		(figure as Idle).set_working(false)


static func work(figure: Node3D) -> void:
	if figure is Idle:
		(figure as Idle).set_working(true)


## How far the captain has the wheel turned, in radians: positive turns its top to his right (clockwise as he
## sees it), about its axis along his facing.
static func wheel_turn(figure: Node3D) -> float:
	return (figure as Idle).wheel if figure is Idle else 0.0


## Where the diver's crank handle is, in radians: 0 straight up from the hub, growing as the top of it goes forward,
## away from him (so a quarter turn has it furthest ahead). The handle is at
## DIVER_CRANK_HUB + DIVER_CRANK_RADIUS * (0, cos a, -sin a).
static func crank_angle(figure: Node3D) -> float:
	return (figure as Idle).crank if figure is Idle else 0.0


static func _make(path: String, kind: Kind, size: float) -> Node3D:
	var figure := Idle.new()
	figure.name = String(Kind.keys()[kind]).capitalize()
	figure.kind = kind
	var model := (load(path) as PackedScene).instantiate() as Node3D
	model.name = "Model"
	# (modelled facing +Z, as the boy's rig wants; turned to face -Z)
	model.rotation.y = PI
	model.scale = Vector3.ONE * size
	model.position.y = -SINK[kind]
	figure.add_child(model)
	figure.skeleton = model.find_children("*", "Skeleton3D", true, false)[0] as Skeleton3D
	for mesh: MeshInstance3D in model.find_children("*", "MeshInstance3D", true, false):
		# (the importer's automatic LODs bend a skinned body in straight pieces; seen close, never wanted)
		mesh.lod_bias = 64.0
		# (all three carry a soft tint in their vertex colours: ribs, stains, tarnish, wear; multiplied into each colour)
		for s in mesh.mesh.get_surface_count():
			var material := mesh.mesh.surface_get_material(s) as BaseMaterial3D
			if material:
				material.vertex_color_use_as_albedo = true
	var mount := BoneAttachment3D.new()
	mount.name = "HeadMount"
	mount.bone_name = "head"
	figure.skeleton.add_child(mount)
	figure.head_mount = mount
	# (hair drawn by the hair shader: the boy's, and the captain's chest; tools/TITLE_FIGURES.md)
	for hair_name: String in HAIR_COLOURS:
		var hair := model.find_child(hair_name, true, false) as MeshInstance3D
		if hair:
			hair.set_surface_override_material(0, _hair_material(hair_name))
	# (the boy's crown of hair is its own mesh, which a helmet on his head would crush: hidden while anything is
	# on the mount)
	var crown := model.find_child("boy_hairtop", true, false) as Node3D
	if crown:
		mount.child_entered_tree.connect(func(_on: Node) -> void: crown.visible = false)
		mount.child_exiting_tree.connect(func(_off: Node) -> void: crown.visible = mount.get_child_count() > 1)
	if kind == Kind.CAPTAIN:
		wear(figure, "open")
		face(figure, "painted")
		# (the painted face carries the concept's own light and shade, so it is drawn unlit, as the panel's baked
		# paint is: lit again it went dark and muddy)
		var painted := model.find_child("captain_face__painted", true, false) as MeshInstance3D
		if painted:
			for s in painted.mesh.get_surface_count():
				var material := painted.mesh.surface_get_material(s) as BaseMaterial3D
				if material and material.albedo_texture:
					material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	figure.seed_time = float(kind) * 2.3
	return figure


## Hair as the user's figures have theirs (the user, 2026-11-18: "sthe boys hair should use our hair shader to recreate
## that look"): GameCommon ink-figure's hair_ink shader (shaders/ink/, copied unchanged). It reads UV along each lock
## and UV2 in metres, which the build script gives these meshes. Their colours: albedo, pale, ink, flicks.
const HAIR_SHADER := "res://shaders/ink/hair_ink.gdshader"
const HAIR_COLOURS := {
	"boy_hair": [Color(0.74, 0.61, 0.4), Color(0.93, 0.84, 0.64), Color(0.3, 0.2, 0.11), Color(0.98, 0.93, 0.8)],
	"boy_hairtop": [Color(0.74, 0.61, 0.4), Color(0.93, 0.84, 0.64), Color(0.3, 0.2, 0.11), Color(0.98, 0.93, 0.8)],
	"captain_chesthair__open_boxers": [Color(0.42, 0.4, 0.37), Color(0.62, 0.6, 0.57), Color(0.2, 0.19, 0.18), Color(0.95, 0.95, 0.93)],
	"captain_bellyhair__boxers": [Color(0.42, 0.4, 0.37), Color(0.62, 0.6, 0.57), Color(0.2, 0.19, 0.18), Color(0.95, 0.95, 0.93)],
}
static var _hair := {}


static func _hair_material(hair_name: String) -> ShaderMaterial:
	if not _hair.has(hair_name):
		var made := ShaderMaterial.new()
		made.shader = load(HAIR_SHADER)
		var colours: Array = HAIR_COLOURS[hair_name]
		made.set_shader_parameter(&"albedo", colours[0])
		made.set_shader_parameter(&"pale", colours[1])
		made.set_shader_parameter(&"ink", colours[2])
		made.set_shader_parameter(&"flicks", colours[3])
		made.set_shader_parameter(&"metres", 1.0)
		# (finer, fainter strand lines and softer ink than the shader's inked-print defaults: painted, not inked)
		made.set_shader_parameter(&"strand_gap", 0.0014)
		made.set_shader_parameter(&"lit_lines", 0.05)
		made.set_shader_parameter(&"shadow_lines", 0.3)
		made.set_shader_parameter(&"wrap", 0.4)
		made.set_shader_parameter(&"shadow_fill", 0.4)
		made.set_shader_parameter(&"root_ink", 0.12)
		made.set_shader_parameter(&"gap_ink", 0.18)
		made.set_shader_parameter(&"flick_gain", 0.4)
		_hair[hair_name] = made
	return _hair[hair_name]


## A figure at work (or standing about): poses its skeleton every frame.
class Idle extends Node3D:
	var kind := Kind.BOY
	var skeleton: Skeleton3D
	var head_mount: BoneAttachment3D
	var look_target := Vector3.ZERO
	var looking := false
	var seed_time := 0.0
	var working := true
	## The captain's wheel (radians) and the diver's crank (radians), as they are this frame.
	var wheel := 0.0
	var crank := 0.0
	## How far each hand's grip is from where it should be just now (metres; for checking).
	var miss := Vector2.ZERO
	var _time := 0.0
	var _look := Vector2.ZERO  # yaw, pitch, eased
	var _bones := {}
	var _root_to_skeleton := Transform3D.IDENTITY

	func _ready() -> void:
		_time = seed_time
		for i in skeleton.get_bone_count():
			_bones[skeleton.get_bone_name(i)] = i

	func set_working(on: bool) -> void:
		working = on
		if skeleton:
			skeleton.reset_bone_poses()

	func _bone(name: String) -> int:
		return _bones.get(name, -1)

	func _turn(bone: String, rotation_now: Quaternion) -> void:
		var i := _bone(bone)
		if i >= 0:
			skeleton.set_bone_pose_rotation(i, rotation_now)

	func _rest(name: String) -> Vector3:
		return skeleton.get_bone_rest(_bone(name)).origin

	func _process(delta: float) -> void:
		_time += delta
		if not working:
			_stand(delta)
			return
		_root_to_skeleton = skeleton.global_transform.affine_inverse() * global_transform
		match kind:
			Kind.BOY:
				_sit_at_console(delta)
			Kind.CAPTAIN:
				_steer(delta)
			Kind.DIVER:
				_crank(delta)

	# --- The plain standing idle ---

	func _look_toward(delta: float, wander: Vector2, reach: Vector2) -> Vector2:
		var want := wander
		var head_bone := _bone("head")
		if looking and head_bone >= 0:
			var at := skeleton.get_bone_global_rest(head_bone).origin
			var d := skeleton.global_transform.affine_inverse() * look_target - at
			want = Vector2(atan2(d.x, d.z), -atan2(d.y, Vector2(d.x, d.z).length()))
		_look = _look.lerp(want.clamp(-reach, reach), 1.0 - exp(-delta * 3.0))
		return _look

	func _stand(delta: float) -> void:
		var breath := sin(_time * TAU / 4.2)
		var sway := sin(_time * TAU / 7.3 + 1.0)
		var reach := Vector2(0.75, 0.45) if kind == Kind.DIVER else Vector2(1.25, 0.6)
		var look := _look_toward(delta, Vector2(sin(_time * 0.37) * 0.25 + sin(_time * 0.13) * 0.15, 0.05 + sin(_time * 0.29) * 0.06), reach)
		var yaw := look.x
		var pitch := look.y
		_turn("spine", Quaternion.from_euler(Vector3(breath * 0.01, yaw * 0.35 if kind == Kind.DIVER else yaw * 0.08, sway * 0.012)))
		var chest_yaw := yaw * 0.65 if kind == Kind.DIVER else yaw * 0.12
		var chest_pitch := pitch * 0.4 if kind == Kind.DIVER else 0.0
		_turn("chest", Quaternion.from_euler(Vector3(-breath * 0.018 + chest_pitch, chest_yaw, -sway * 0.008)))
		if kind != Kind.DIVER:
			_turn("neck", Quaternion.from_euler(Vector3(pitch * 0.4, yaw * 0.32, 0.0)))
			_turn("head", Quaternion.from_euler(Vector3(pitch * 0.6, yaw * 0.48, -sway * 0.01)))
		# All three are made in a T pose (the arms straight out to the sides): brought down by their sides, the elbows a
		# little bent and the fingers curled; the diver's held a little out from his baggy dress.
		var down := deg_to_rad(ARM_DOWN[kind]) + breath * 0.015
		_turn("upper_arm_l", Quaternion(Vector3.BACK, -down))
		_turn("upper_arm_r", Quaternion(Vector3.BACK, down))
		_turn("forearm_l", Quaternion(Vector3.UP, -0.22))
		_turn("forearm_r", Quaternion(Vector3.UP, 0.22))
		_curl(0.32)

	func _curl(amount: float) -> void:
		for bone: String in _bones:
			var curl := -amount if bone.ends_with("_l") else amount
			if bone.begins_with("finger"):
				_turn(bone, Quaternion(Vector3.BACK, curl))
			elif bone.begins_with("thumb") and (bone.contains("a_") or bone.contains("_1_")):
				_turn(bone, Quaternion(Vector3.BACK, curl * 0.4))

	# --- The body: hips, spine, chest, neck and head, posed and their places in the skeleton worked out ---

	## Poses the trunk (rotations as Euler angles, X pitch forward, Y yaw to his left, Z roll) and gives back the
	## hips' and chest's transforms in the skeleton's space.
	func _trunk(hips_shift: Vector3, hips: Vector3, spine: Vector3, chest: Vector3) -> Array[Transform3D]:
		var h := _bone("hips")
		var hips_at := skeleton.get_bone_rest(h).origin + hips_shift
		skeleton.set_bone_pose_position(h, hips_at)
		var qh := Quaternion.from_euler(hips)
		var qs := Quaternion.from_euler(spine)
		var qc := Quaternion.from_euler(chest)
		_turn("hips", qh)
		_turn("spine", qs)
		_turn("chest", qc)
		var g_hips := Transform3D(Basis(qh), hips_at)
		var g_spine := g_hips * Transform3D(Basis(qs), _rest("spine"))
		var g_chest := g_spine * Transform3D(Basis(qc), _rest("chest"))
		return [g_hips, g_chest]

	func _head(yaw: float, pitch: float, roll := 0.0) -> void:
		_turn("neck", Quaternion.from_euler(Vector3(pitch * 0.4, yaw * 0.4, roll * 0.5)))
		_turn("head", Quaternion.from_euler(Vector3(pitch * 0.6, yaw * 0.6, roll * 0.5)))

	## A root-space point in the skeleton's space.
	func _here(point: Vector3) -> Vector3:
		return _root_to_skeleton * point

	## A root-space direction in the skeleton's space.
	func _way(direction: Vector3) -> Vector3:
		return (_root_to_skeleton.basis * direction).normalized()

	static func _frame(along: Vector3, up: Vector3) -> Basis:
		var x := along.normalized()
		var y := (up - x * up.dot(x)).normalized()
		return Basis(x, y, x.cross(y))

	## A turn taking `rest_along` to `along` and the rest's `rest_up` as near `up` as it can go.
	static func _aim(rest_along: Vector3, rest_up: Vector3, along: Vector3, up: Vector3) -> Basis:
		return _frame(along, up) * _frame(rest_along, rest_up).transposed()

	## Where the middle joint of a two-bone limb goes, from its root to its end, bending toward `pole`.
	static func _bend(root: Vector3, end: Vector3, a: float, b: float, pole: Vector3) -> Vector3:
		var to := end - root
		var d := clampf(to.length(), absf(a - b) + 0.001, a + b - 0.001)
		var axis := to.normalized()
		var along := (a * a - b * b + d * d) / (2.0 * d)
		var out := sqrt(maxf(a * a - along * along, 0.0))
		var side := (pole - axis * pole.dot(axis)).normalized()
		return root + axis * along + side * out

	## Puts a hand's grip (the middle of a closed hand: `grip.x` past the wrist, `grip.y` toward the palm) on
	## `target`, all in the skeleton's space, the elbow bending toward `pole`, the back of the hand toward `back`.
	## Gives back how far the grip ends up from the target (metres, at the figure's size).
	func _arm(side: String, target: Vector3, back: Vector3, pole: Vector3, chest: Transform3D, grip: Vector2) -> float:
		var upper_rest := _rest("upper_arm_" + side)
		var fore_rest := _rest("forearm_" + side)
		var hand_rest := _rest("hand_" + side)
		var shoulder := chest * upper_rest
		var a := fore_rest.length()
		var b := hand_rest.length()
		var reach_dir := (target - shoulder).normalized()
		var wrist := target - reach_dir * grip.x
		var upper := Basis.IDENTITY
		var fore := Basis.IDENTITY
		for i in 3:
			var elbow := _bend(shoulder, wrist, a, b, pole)
			upper = _aim(fore_rest, Vector3.UP, elbow - shoulder, back)
			fore = _aim(hand_rest, Vector3.UP, wrist - elbow, back)
			var grip_off := fore * (hand_rest.normalized() * grip.x - Vector3.UP * grip.y)
			wrist = target - grip_off
		_turn("upper_arm_" + side, Quaternion((chest.basis.inverse() * upper).orthonormalized()))
		_turn("forearm_" + side, Quaternion((upper.inverse() * fore).orthonormalized()))
		_turn("hand_" + side, Quaternion.IDENTITY)
		var wrist_now := shoulder + upper * fore_rest + fore * hand_rest
		var grip_now := wrist_now + fore * (hand_rest.normalized() * grip.x - Vector3.UP * grip.y)
		return (grip_now - target).length() / _root_to_skeleton.basis.get_scale().x

	## Puts an ankle on `ankle` (the skeleton's space), the knee bending toward `pole`, the foot level and turned
	## `foot_yaw`. The leg's bones hang from the hips side by side (the rig's way), so the shin and foot are moved.
	func _leg(side: String, ankle: Vector3, pole: Vector3, hips: Transform3D, foot_pitch := 0.0) -> void:
		var thigh_rest := _rest("thigh_" + side)
		var shin_rest := _rest("shin_" + side)
		var foot_rest := _rest("foot_" + side)
		var hip := hips * thigh_rest
		var a := (shin_rest - thigh_rest).length()
		var b := (foot_rest - shin_rest).length()
		var knee := _bend(hip, ankle, a, b, pole)
		var to_hips := hips.affine_inverse()
		var thigh := _aim(Vector3.DOWN, Vector3.BACK, knee - hip, pole)
		var shin := _aim(Vector3.DOWN, Vector3.BACK, ankle - knee, pole)
		var q_thigh := Quaternion((hips.basis.inverse() * thigh).orthonormalized())
		var q_shin := Quaternion((hips.basis.inverse() * shin).orthonormalized())
		_turn("thigh_" + side, q_thigh)
		_turn("shin_" + side, q_shin)
		skeleton.set_bone_pose_position(_bone("shin_" + side), to_hips * knee)
		var f := _bone("foot_" + side)
		skeleton.set_bone_pose_position(f, to_hips * ankle)
		_turn("foot_" + side, Quaternion((hips.basis.inverse() * Basis(Vector3.RIGHT, foot_pitch)).orthonormalized()))
		# (the boy's knee and seat bones: the knee goes with it, half way between thigh and shin; the seat half way
		# round with the thigh)
		var k := _bone("knee_" + side)
		if k >= 0:
			skeleton.set_bone_pose_position(k, to_hips * knee)
			skeleton.set_bone_pose_rotation(k, q_thigh.slerp(q_shin, 0.5))
		var s := _bone("seat_" + side)
		if s >= 0:
			skeleton.set_bone_pose_rotation(s, Quaternion.IDENTITY.slerp(q_thigh, 0.5))

	## Each foot where it stands at rest (feet planted while the hips move).
	func _planted(side: String) -> Vector3:
		return _rest("hips") + _rest("foot_" + side)

	# --- The boy at the console ---

	func _sit_at_console(delta: float) -> void:
		var breath := sin(_time * TAU / 3.8)
		# The stick: small slow moves, as if steering something.
		var stick := Vector3(0.03 * sin(_time * 1.3) + 0.012 * sin(_time * 3.1), 0.0, 0.022 * sin(_time * 0.9 + 1.0))
		var lean := stick.x * 1.6
		# Sat: the hips down onto the seat (his seat 0.06 under his hip joints), a little back, upright.
		var seat_y := (_here(Vector3(0.0, BOY_SEAT_HEIGHT, 0.0))).y
		var hip_joint_y := _rest("hips").y + _rest("thigh_l").y
		var drop := seat_y + 0.06 - hip_joint_y
		var body := _trunk(Vector3(0.0, drop, -0.02), Vector3(0.0, 0.0, -lean * 0.3),
				Vector3(0.10 + breath * 0.01, 0.0, -lean * 0.4), Vector3(0.06 - breath * 0.015, -lean * 0.3, -lean * 0.5))
		for side in ["l", "r"]:
			var s := 1.0 if side == "l" else -1.0
			var foot := BOY_RUNG + Vector3(-s * BOY_FEET_APART * 0.5, 0.05, 0.0)
			_leg(side, _here(foot), _way(Vector3(-s * 0.15, 0.25, -1.0)), body[0])
		var look := _look_toward(delta, Vector2(sin(_time * 0.31) * 0.12, 0.08 + sin(_time * 0.23) * 0.04), Vector2(1.0, 0.5))
		_head(look.x, look.y - 0.06, lean * 0.4)
		var grip := Vector2(0.05, 0.015)
		miss.x = _arm("l", _here(BOY_LEFT_HAND + stick), _way(Vector3(0.3, 1.0, 0.0)), _way(Vector3(-0.6, -1.0, 0.4)), body[1], grip)
		miss.y = _arm("r", _here(BOY_RIGHT_HAND + Vector3(0.0, -0.006 * maxf(sin(_time * 2.3), 0.0), 0.0)), _way(Vector3(-0.2, 1.0, 0.0)),
				_way(Vector3(0.6, -1.0, 0.4)), body[1], grip)
		_curl(0.7)

	# --- The captain at the wheel ---

	func _steer(delta: float) -> void:
		var breath := sin(_time * TAU / 4.4)
		# The wheel: held near the middle, a turn one way or the other every so often.
		wheel = 0.32 * sin(_time * TAU / 9.0) + 0.12 * sin(_time * TAU / 3.7 + 0.5)
		var shift := sin(_time * TAU / 6.5)
		var body := _trunk(Vector3(0.012 * shift, -0.004 + 0.003 * absf(shift), 0.0), Vector3(0.0, 0.0, -0.02 * shift),
				Vector3(0.04 + breath * 0.008, -wheel * 0.08, 0.02 * shift), Vector3(0.02 - breath * 0.014, -wheel * 0.1, 0.012 * shift))
		for side in ["l", "r"]:
			var s := 1.0 if side == "l" else -1.0
			_leg(side, _planted(side), _way(Vector3(-s * 0.15, 0.0, -1.0)), body[0])
		# Now and then a glance out to the side, to his left, then to his right.
		var glance := clampf(sin(_time * TAU / 8.0) * 3.0 - 2.0, 0.0, 1.0)
		var which := 1.0 if fmod(_time, 16.0) < 8.0 else -1.0
		var look := _look_toward(delta, Vector2(glance * 0.9 * which + sin(_time * 0.4) * 0.08, 0.04), Vector2(1.2, 0.5))
		_head(look.x, look.y, 0.0)
		var hub := CAPTAIN_WHEEL_HUB
		var grip := Vector2(0.055, 0.012)
		for side in ["l", "r"]:
			# ten o'clock on his left, two on his right; going round with the rim
			var at := (-PI / 3.0 if side == "l" else PI / 3.0) + wheel
			var rim := hub + Vector3(sin(at), cos(at), 0.0) * CAPTAIN_WHEEL_RADIUS
			var out := (rim - hub).normalized()
			var s := 1.0 if side == "l" else -1.0
			var m := _arm(side, _here(rim), _way(out + Vector3(0.0, 0.0, 0.6)), _way(Vector3(-s * 0.7, -1.0, 0.5)), body[1], grip)
			if side == "l":
				miss.x = m
			else:
				miss.y = m
		_curl(0.9)

	# --- The diver at the pump ---

	func _crank(delta: float) -> void:
		crank = fmod(_time, DIVER_CRANK_TURN) / DIVER_CRANK_TURN * TAU
		var forward := sin(crank)
		var low := -cos(crank)
		var lean := 0.32 + 0.16 * forward + 0.12 * maxf(low, 0.0) + 0.1 * maxf(forward * low, 0.0)
		var heave := 0.5 + 0.5 * forward
		var body := _trunk(Vector3(0.0, -0.02 - 0.012 * heave - 0.03 * maxf(low, 0.0), -0.04 + 0.025 * forward), Vector3(0.06 * lean, 0.0, 0.0),
				Vector3(lean * 0.45, 0.04 * sin(crank * 2.0), 0.02 * forward), Vector3(lean * 0.55, 0.03 * sin(crank * 2.0), 0.0))
		for side in ["l", "r"]:
			var s := 1.0 if side == "l" else -1.0
			_leg(side, _planted(side) + Vector3(s * 0.008, 0.0, 0.01), _way(Vector3(-s * 0.2, 0.0, -1.0)), body[0])
		_look_toward(delta, Vector2.ZERO, Vector2(0.5, 0.3))
		var handle := DIVER_CRANK_HUB + Vector3(0.0, cos(crank), -sin(crank)) * DIVER_CRANK_RADIUS
		var grip := Vector2(0.055, 0.012)
		for side in ["l", "r"]:
			var s := 1.0 if side == "l" else -1.0
			# both hands on the handle's bar (it sticks out across him), side by side, the backs of the hands up
			var m := _arm(side, _here(handle + Vector3(-s * 0.055, 0.0, 0.0)), _way(Vector3(-s, 0.7, 0.0)), _way(Vector3(-s * 0.8, -1.0, 0.3)), body[1], grip)
			if side == "l":
				miss.x = m
			else:
				miss.y = m
		_curl(0.95)
