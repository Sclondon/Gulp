class_name ReefBack
extends Node3D
## The reef-back: an original giant amphibious reptile (not any published monster), 35 m from nose to tail, that
## walks slowly on the sea floor. A heavy four-legged iguana-like beast with a thick tail and a saw-edged fin along
## it, a back of rock slabs piled up like a cairn and overgrown with coral, kelp, barnacles and sponges, a broad
## blunt head with a heavy brow, pink gill frills, a glowing green throat, and broad clawed feet.
##
## How it looks and moves only (no thinking, no sound): whatever moves it puts it where it is and turns it the way
## it goes. Its nose points along its own -Z (Godot's forward), up is +Y. Its origin is ON THE FLOOR under its
## middle: its feet stand on y 0 (it reaches 17.5 m ahead of its origin and 17.5 m behind, 9 m to each side with
## its feet, 20.6 m up to the top of the kelp on its back; its back is 13 m up). `scale` it for a bigger one.
##
## It walks with a small skeleton (23 bones) and two baked clips, "walk" (one cycle of a slow four-legged walk, in
## which it goes STRIDE metres) and "stand" (one slow breath), blended by `walk`. Everything runs on `phase`, 0 to
## 1 through one cycle: `step(velocity, delta)` moves it on by the distance it has gone (so its feet do not slide)
## and eases `walk` towards 1 while it moves and towards 0 when it stops; standing, `phase` goes on at one cycle a
## `beat`. Or set `phase` and `walk` yourself. The jaw is its skeleton's jaw bone, turned by `gape`; the kelp and
## frills sway, the throat glows and the body bends for a turn (`curl`) in its shader.
##
## Decision (Claude's pick, 2026-11-18): a skeleton with baked clips, not a walk drawn in the vertex shader. A
## four-legged walk plants each foot and bends knees and elbows to keep it there; that is a skeleton's work, and
## Godot's own guidance keeps vertex-shader animation for crowds of simple, cyclic movers (its "animating thousands
## of fish"). Here there is one creature, 23 bones cost nothing, and GameCommon's figures already use baked clips
## (character-controller README, "Decision: baked clips"). The clips are baked by the build script with two-bone
## IK, so the feet are planted in the clip itself.
##
## The models are creatures/reef_back/models/reef_back.glb (full), _game and _lo, built by
## tools/build_reef_back.py; reef_back.gdshader draws its markings.

const MODEL := "res://creatures/reef_back/models/reef_back%s.glb"
const SHADER := preload("res://creatures/reef_back/reef_back.gdshader")
## As the model is built (metres, at scale 1): nose to tail tip, from the outside of one foot to the other, and
## up to the top of the kelp on its back.
const LENGTH := 35.0
const WIDTH := 17.9
const HEIGHT := 20.6
## How far it goes in one cycle of its walk (metres, at scale 1), and how long a cycle of the clips is (seconds).
const STRIDE := 4.0
const CYCLE := 6.0
## How far its jaw opens at `gape` 1 (radians).
const GAPE_MAX := 0.55

## Seconds one cycle takes when it is not going anywhere (its breath standing).
@export var beat := CYCLE
## How much it is walking: 0 standing, 1 walking (`step` eases it).
@export_range(0.0, 1.0) var walk := 0.0:
	set(value):
		walk = clampf(value, 0.0, 1.0)
		_pose()
## Its mouth: 0 shut, 1 open.
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_pose()
## How brightly its throat glows (0 dark, 1 as built; more is brighter still).
@export_range(0.0, 3.0) var glow := 1.0:
	set(value):
		glow = maxf(value, 0.0)
		_send(&"glow", glow)
## How far its body is bent round behind its shoulders, as when it turns: radians from the shoulders to the tail tip
## (more than 0 the tail comes round to +X, its right).
@export_range(-1.5, 1.5) var curl := 0.0:
	set(value):
		curl = value
		_send(&"curl", value)
## The low model (about 2,500 triangles), for far off.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model: about 5,800 triangles, Twilight Princess boss weight, shown in place of the full one (`low`
## still shows the low one). Each model is loaded only when it is first shown, so with `game` on (set before it
## enters the tree) the full model is never loaded and a web export can leave it out.
@export var game := false:
	set(value):
		game = value
		_show()
## Its eyes: 0 as in life, 1 cartoon eyes with a character (old, sleepy and gentle: a big pale green iris, a round
## pupil, a heavy upper lid half down).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = clampf(value, 0.0, 1.0)
		_send(&"cartoon_eyes", cartoon_eyes)
## Where its cartoon eyes look, each in its own plane: x +1 towards its nose, y +1 up.
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value.clamp(Vector2(-1.0, -1.0), Vector2(1.0, 1.0))
		_send(&"eye_look", eye_look)
## Its lids: 0 open, 1 shut.
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = clampf(value, 0.0, 1.0)
		_send(&"blink", blink)
## How far through a cycle it is, 0 to 1 (only the fraction counts).
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send(&"phase", phase)
		_pose()

static var _scenes := {}
static var _meshes := {}

var _material: ShaderMaterial
# (each model shown so far, by its file's ending: its root, skeleton, animation tree, jaw bone and the jaw's rest)
var _shown := {}
var _started := false


## The full model's mesh, or the low one's (one surface each, skinned, to wear `new_material()`; without its
## skeleton it stands as built).
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at("_lo" if low_wanted else "")


## The game model's mesh (as `mesh_of`).
static func game_mesh() -> Mesh:
	return _mesh_at("_game")


static func _scene_at(ending: String) -> PackedScene:
	var path := MODEL % ending
	if not _scenes.has(path):
		_scenes[path] = load(path)
	return _scenes[path]


static func _mesh_at(ending: String) -> Mesh:
	if not _meshes.has(ending):
		var made := _scene_at(ending).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[ending] = found.mesh
		made.free()
	return _meshes[ending]


## A new material for these meshes. Its shader settings are the game's to set: `phase`, `glow`, `curl`, `sway`,
## `cartoon_eyes`, `eye_look`, `blink` and the colours (the top of the shader lists them).
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	_started = true
	_show()
	for setting: StringName in [&"phase", &"glow", &"curl", &"cartoon_eyes", &"eye_look", &"blink"]:
		_send(setting, get(setting))


## Each frame: moves it on through its walk by how far it has gone (`velocity` in the world, its own scale taken
## out), easing `walk` towards 1 while it goes and towards 0 when it stops; standing, it breathes at one cycle a
## `beat`.
func step(velocity: Vector3, delta: float) -> void:
	var size := global_basis.get_scale().x if is_inside_tree() else 1.0
	var speed := Vector2(velocity.x, velocity.z).length() / maxf(size, 0.001)
	var going := speed > 0.05
	walk = move_toward(walk, 1.0 if going else 0.0, delta * 0.7)
	if walk > 0.5:
		phase += speed * delta / STRIDE
	else:
		phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: its colours (`back`, `flank`, `belly`, `spot`, `glow_colour`, `mouth`, `rock`,
## `lichen`, `coral`, `kelp`, `barnacle`, `sponge`, `frill`, `claw`, `iris`) and `sway` (how far its weed sways).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (all its models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


func _show() -> void:
	if not _started:
		return
	var wanted := "_lo" if low else ("_game" if game else "")
	if not _shown.has(wanted):
		_shown[wanted] = _instance_of(wanted)
	for ending: String in _shown:
		(_shown[ending].root as Node3D).visible = ending == wanted
	_pose()


func _instance_of(ending: String) -> Dictionary:
	var root := _scene_at(ending).instantiate() as Node3D
	root.name = "ReefBack" + ending
	add_child(root)
	var mesh: MeshInstance3D = root.find_children("*", "MeshInstance3D", true, false)[0]
	mesh.material_override = _material
	# (its tail swings, its legs reach and the kelp sways past where the still model ends)
	mesh.extra_cull_margin = 6.0
	var skeleton: Skeleton3D = root.find_children("*", "Skeleton3D", true, false)[0]
	var player: AnimationPlayer = root.find_children("*", "AnimationPlayer", true, false)[0]
	# The two clips, each sought to the same point of its cycle, blended by `walk`.
	var blend_tree := AnimationNodeBlendTree.new()
	for clip: StringName in [&"stand", &"walk"]:
		var node := AnimationNodeAnimation.new()
		node.animation = clip
		blend_tree.add_node(clip, node)
		blend_tree.add_node(StringName(clip + "_seek"), AnimationNodeTimeSeek.new())
		blend_tree.connect_node(StringName(clip + "_seek"), 0, clip)
	blend_tree.add_node(&"blend", AnimationNodeBlend2.new())
	blend_tree.connect_node(&"blend", 0, &"stand_seek")
	blend_tree.connect_node(&"blend", 1, &"walk_seek")
	blend_tree.connect_node(&"output", 0, &"blend")
	var tree := AnimationTree.new()
	tree.tree_root = blend_tree
	tree.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	root.add_child(tree)
	tree.anim_player = tree.get_path_to(player)
	tree.active = true
	var jaw := skeleton.find_bone("jaw")
	# (the jaw turns about the creature's own side to side, whichever way its bone's axes lie)
	var jaw_axis := (skeleton.get_bone_global_rest(jaw).basis.inverse() * Vector3.RIGHT).normalized()
	return {"root": root, "skeleton": skeleton, "tree": tree, "jaw": jaw, "jaw_rest": skeleton.get_bone_rest(jaw).basis.get_rotation_quaternion(), "jaw_axis": jaw_axis}


# Poses the model shown: both clips at `phase`, blended by `walk`, then the jaw.
func _pose() -> void:
	if not _started:
		return
	var wanted := "_lo" if low else ("_game" if game else "")
	if not _shown.has(wanted):
		return
	var shown: Dictionary = _shown[wanted]
	var tree: AnimationTree = shown.tree
	tree.set(&"parameters/stand_seek/seek_request", phase * CYCLE)
	tree.set(&"parameters/walk_seek/seek_request", phase * CYCLE)
	tree.set(&"parameters/blend/blend_amount", walk)
	tree.advance(0.0)
	var skeleton: Skeleton3D = shown.skeleton
	var jaw: int = shown.jaw
	skeleton.set_bone_pose_rotation(jaw, (shown.jaw_rest as Quaternion) * Quaternion(shown.jaw_axis, -GAPE_MAX * gape))
