class_name Grouper
extends Node3D
## A broomtail grouper (Mycteroperca xenarcha) of the eastern Pacific's rocky reefs, 1.2 m long:
## robust, a big thick-lipped mouth with the lower jaw standing forward, one long dorsal fin
## (eleven spines, then soft rays), a square tail whose rays stand out past its edge like the
## bristles of a broom; greenish brown mottled pale, with darker oval blotches.
##
## How it looks and moves only: whatever moves it puts it where it is and turns it the way it
## goes. Its nose points along its own -Z, its belly down; its origin is on its middle line, half
## way along its length. `scale` it for a bigger or smaller one. No sound.
##
## It swims by a wave down its body and tail, drawn by the shader (no bones): the head nearly
## still, the tail swinging widest. It hovers and turns by sculling its pectoral fins, which never
## stop; it breathes with its mouth and gill covers. `gape` opens its mouth: 0 shut, 1 wide open
## into a round tube, the lower jaw dropped and the upper jaw pushed forward, as when it sucks in
## its prey.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`: in a beat the tail beats
## `tail_beats` times, it breathes `breaths` times and its fins scull `sculls` times (whole
## numbers), so its motion comes round again exactly every beat. Either call
## `step(velocity, delta)` each frame, which moves `phase` on by delta / beat (and swims harder
## the faster it is going), or set `phase` yourself (for a picture that must loop).
##
## A game that keeps its own MeshInstance3Ds needs no Grouper node: `Grouper.mesh_of(low)` (or
## `Grouper.game_mesh()`) is the mesh and `Grouper.new_material()` a material for it, whose shader settings (phase, sway,
## tail_beats, breaths, sculls, gape, curl, scull, flash, rim, the colours) the game sets itself.
##
## The models are creatures/grouper/models/grouper.glb (and _lo, _game), built by
## tools/build_grouper.py; grouper.gdshader draws its markings and moves it.

const MODEL := "res://creatures/grouper/models/grouper%s.glb"
const GAME_MODEL := "res://creatures/grouper/models/grouper_game.glb"
const SHADER := preload("res://creatures/grouper/grouper.gdshader")
## As the model is built (tools/build_grouper.py): from the tip of its lower jaw to the tip of its
## tail, and how deep and how wide its body is at its deepest, fins left out (metres, at scale 1).
const LENGTH := 1.2
const DEPTH := 0.35
const WIDTH := 0.21

static var _meshes := {}

## Seconds one beat takes: everything it does comes round again each beat. 0 for a caller that
## sets `phase` itself (`step` then leaves `phase` alone).
@export var beat := 2.6
## How many times in a beat its tail beats, it breathes, and its pectoral fins scull.
@export var tail_beats := 2:
	set(value):
		tail_beats = maxi(value, 0)
		_send(&"tail_beats", float(tail_beats))
@export var breaths := 2:
	set(value):
		breaths = maxi(value, 0)
		_send(&"breaths", float(breaths))
@export var sculls := 2:
	set(value):
		sculls = maxi(value, 0)
		_send(&"sculls", float(sculls))
## How hard it swims when it is not going anywhere (hovering): 0 still, 1 its tail tip swinging
## about a tenth of its length each way. `step` raises it with speed.
@export_range(0.0, 1.5) var sway := 0.3:
	set(value):
		sway = value
		_effort = value
		_send(&"sway", _effort)
## The speed (m/s, at scale 1) at which `step` has it swimming as hard as it can.
@export var top_speed := 1.4
## How wide its mouth is open: 0 shut, 1 wide open (it still breathes a little either way).
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = value
		_send(&"gape", value)
## The low model (about a tenth of the triangles), for far off, phones, many of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (Twilight Princess weight: a few thousand triangles, spent on the outline, the
## eye and the mouth; the same shader and settings) in place of the full one; `low` still shows
## the low model. With `game` on the full model is never loaded, so a web export may leave it out.
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye: 0 as in life, 1 bigger, a white, a big pupil, its own lids (the grouper's is
## sleepy, under a heavy half lid).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = value
		_send(&"cartoon_eyes", value)
## Where its eyes look: x + towards its nose, y + up (-1..1).
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value
		_send(&"eye_look", value)
## 0 its eyes open, 1 shut (a lid the colour of its skin comes down over them).
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = value
		_send(&"blink", value)
## How far through a beat it is, 0 to 1 (only the fraction counts). `step` moves it on; or set it
## yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send(&"phase", phase)

var _material: ShaderMaterial
var _full: MeshInstance3D
var _low: MeshInstance3D
var _game: MeshInstance3D
var _effort := 0.3


## The mesh (`low` for the low one), for a game that keeps its own MeshInstance3Ds. Each is
## loaded once and kept.
static func mesh_of(low_wanted := false) -> Mesh:
	var path := MODEL % ("_lo" if low_wanted else "")
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = found.mesh
		made.free()
	return _meshes[path]


## The game model's mesh (loaded once and kept), without the thinner levels of detail Godot's
## importer makes: bent in the shader, they would bend in straight pieces far off.
static func game_mesh() -> Mesh:
	if not _meshes.has(GAME_MODEL):
		var made := (load(GAME_MODEL) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		var plain := ArrayMesh.new()
		for surface in found.mesh.get_surface_count():
			plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, found.mesh.surface_get_arrays(surface))
		_meshes[GAME_MODEL] = plain
		made.free()
	return _meshes[GAME_MODEL]


## A new material for its mesh. Its shader settings are the game's to set (the top of the shader
## lists them).
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


func _init() -> void:
	_material = new_material()
	_effort = sway


func _ready() -> void:
	_show()
	for setting: StringName in [&"tail_beats", &"breaths", &"sculls", &"cartoon_eyes", &"eye_look", &"blink"]:
		_send(setting, get(setting) if get(setting) is Vector2 else float(get(setting)))
	_send(&"sway", _effort)
	_send(&"gape", gape)
	_send(&"phase", phase)


## Each frame, after putting it where it is: moves its beat on by `delta` seconds (unless `beat`
## is 0), and has it swim harder the faster it is going (`velocity`, world, m/s; Vector3.ZERO for
## one that hovers, and it swims as `sway` says).
func step(velocity: Vector3, delta: float) -> void:
	if beat > 0.0:
		phase += delta / beat
	var size := maxf(global_basis.get_scale().z, 0.001) if is_inside_tree() else 1.0
	var wanted := maxf(sway, clampf(velocity.length() / (top_speed * size), 0.0, 1.0))
	_effort = move_toward(_effort, wanted, delta * 1.5)
	_send(&"sway", _effort)


## Sets one of the shader's settings: a colour (back, side, belly, blotch, pale, fin_dark, fin_tail, fin_paired, mouth, eye_ring, iris, gill_red, gill_deep, gill_raker), an amount
## (blotch_amount, mottle, scales, sheen), how it moves (curl, gape_breath, gill_flare, scull), or
## a game's effects (flash, rim).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_send(setting, value)


## Its one material (both models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


func _show() -> void:
	if not is_node_ready():
		return
	# (each model is loaded and put in only when it is first shown)
	if low and not _low:
		_low = _instance_of("Grouper_lo", mesh_of(true))
	elif not low and game and not _game:
		_game = _instance_of("Grouper_game", game_mesh())
	elif not low and not game and not _full:
		_full = _instance_of("Grouper", mesh_of(false))
	if _full:
		_full.visible = not low and not game
	if _low:
		_low.visible = low
	if _game:
		_game.visible = not low and game


func _instance_of(called: String, model: Mesh) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = model
	mesh.material_override = _material
	# (its tail swings, and its mouth opens, out past the still model's box)
	mesh.extra_cull_margin = LENGTH * 0.25
	mesh.name = called
	add_child(mesh)
	return mesh
