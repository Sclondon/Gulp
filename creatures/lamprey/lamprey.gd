class_name Lamprey
extends Node3D
## A sea lamprey (Petromyzon marinus): a long, eel-like, scaleless body, mottled olive-brown
## above and pale below; seven round gill openings in a row behind each eye; one nostril on the
## top of the head; two low dorsal fins, the second running back into the tail fin; no paired
## fins, no jaws. Its mouth is a round sucker ringed with rows of horny teeth: `gape` opens it,
## from a puckered slit (0) to the full round sucker with its teeth showing (1). All of its
## markings are drawn by its shader (no texture files). Its nose points along its own -Z, its
## belly down; its origin is the middle of its length.
##
## It swims as an eel does, by a wave that runs the whole length of its body (drawn by the
## shader, no bones). Everything that moves runs on `phase`, 0 to 1 through one `beat`: in a
## beat `tail_beats` waves run down its body (a whole number), so its motion comes round again
## exactly every beat. Either call `step(velocity, delta)` each frame, or set `phase` yourself
## (with `beat` 0, `step` leaves `phase` alone).
##
## A game that keeps its own MeshInstance3Ds needs no Lamprey node: `Lamprey.mesh_of(low)` (or
## `Lamprey.game_mesh()`) is the mesh and `Lamprey.new_material()` a material for it.
##
## The models are creatures/lamprey/models/lamprey.glb (the full model), lamprey_game.glb (the
## game model: about 2,400 triangles, `game`) and lamprey_lo.glb, built by
## tools/build_lamprey.py; its shader is lamprey.gdshader. Each is loaded only when it is first
## shown: with `game` on, the full model is never loaded.

const MODEL := "res://creatures/lamprey/models/lamprey%s.glb"
const GAME_MODEL := "res://creatures/lamprey/models/lamprey_game.glb"
const SHADER := preload("res://creatures/lamprey/lamprey.gdshader")
## From the front of the sucker to the tip of the tail (metres, at scale 1).
const LENGTH := 0.7
## The body's greatest depth and width (metres, at scale 1). With its fins it is 0.07 m deep;
## the open sucker is 0.045 m across.
const DEPTH := 0.055
const WIDTH := 0.043

static var _meshes := {}

## Seconds one beat takes: everything it does comes round again each beat. 0 for a caller that
## sets `phase` itself (`step` then leaves `phase` alone).
@export var beat := 1.6
## How many waves run down its body in a beat.
@export var tail_beats := 2:
	set(value):
		tail_beats = maxi(value, 0)
		_send(&"tail_beats", float(tail_beats))
## How hard it swims when it is not going anywhere: 0 lies still, 1 swings its tail about a
## fifteenth of its length each way. `step` swims it harder when it goes faster.
@export_range(0.0, 2.0) var sway := 0.8:
	set(value):
		sway = value
		_effort = value
		_send(&"sway", value)
## The speed (m/s, at scale 1) at which `step` has it swimming as hard as `sway` 1.
@export var top_speed := 1.0
## Its sucker: 0 folded shut into a slit (as it swims), 1 open full and round, its teeth
## showing (as it latches on).
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## The low model (far off, phones) in place of the full one (or of the game model).
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (about 2,400 triangles, as a Twilight Princess figure spends them) in place
## of the full one. With it on, the full model is never loaded.
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye: 0 the eye as the species has it, 1 a much bigger cartoon eye (a pale glassy
## iris, a pin of a pupil, a lower lid pushed up into a hungry leer).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = clampf(value, 0.0, 1.0)
		_send(&"cartoon_eyes", cartoon_eyes)
## Where it looks: the iris and pupil slide that way (x towards its snout, y up; -1..1).
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value
		_send(&"eye_look", eye_look)
## 0 eyes open, 1 shut (squashed flat, the lid drawn down).
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = clampf(value, 0.0, 1.0)
		_send(&"blink", blink)
## How far through a beat it is, 0 to 1. `step` moves it on; or set it yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send(&"phase", phase)

var _material: ShaderMaterial
# The MeshInstance3Ds made so far, by model ("", "_lo", "_game"): each made when first shown.
var _shown := {}
var _effort := 0.8


## The mesh (the low one for far off, phones), for a game that keeps its own
## MeshInstance3Ds. Each is loaded once and kept.
static func mesh_of(low_wanted := false) -> Mesh:
	var path := MODEL % ("_lo" if low_wanted else "")
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = found.mesh
		made.free()
	return _meshes[path]


## The game model's mesh, loaded once and kept, without the importer's automatic LODs (a body
## bent in the vertex shader would bend in straight pieces far off).
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


## A new material for the mesh. Its shader settings are the game's to set: phase (0..1), sway,
## tail_beats, gape, curl and the colours (the top of the shader lists them).
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	_show()
	_send(&"tail_beats", float(tail_beats))
	_send(&"sway", _effort)
	_send(&"gape", gape)
	_send(&"phase", phase)
	_send(&"cartoon_eyes", cartoon_eyes)
	_send(&"eye_look", eye_look)
	_send(&"blink", blink)


## Each frame, after putting it where it is: moves its beat on by `delta` seconds (unless
## `beat` is 0), and has it swim harder the faster it is going (`velocity`, world, m/s; give
## Vector3.ZERO for one that holds its place, and it swims as `sway` says).
func step(velocity: Vector3, delta: float) -> void:
	if beat > 0.0:
		phase += delta / beat
	var size := maxf(global_basis.get_scale().z, 0.001) if is_inside_tree() else 1.0
	var wanted := maxf(sway, clampf(velocity.length() / (top_speed * size), 0.0, 1.0))
	_effort = move_toward(_effort, wanted, delta * 1.5)
	_send(&"sway", _effort)


## Sets one of the shader's settings: how it moves (curl, gape, sway, phase, tail_beats), a
## colour (back, side, belly, mottle_colour, disc_face, disc_rim, throat, tooth, tooth_tip,
## eye_ring, fin_colour) or an amount (mottle, sheen); also cartoon_eyes, eye_look, blink.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_send(setting, value)


## The material it is drawn with.
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


func _show() -> void:
	if not is_node_ready():
		return
	var wanted := "_lo" if low else ("_game" if game else "")
	if not _shown.has(wanted):
		var mesh := mesh_of(true) if low else (game_mesh() if game else mesh_of(false))
		_shown[wanted] = _instance_of("Lamprey" + wanted, mesh)
	for which: String in _shown:
		_shown[which].visible = which == wanted


## The MeshInstance3D showing now (the full, game or low model).
func shown_mesh() -> MeshInstance3D:
	_show()
	return _shown.get("_lo" if low else ("_game" if game else ""))


func _instance_of(called: String, mesh: Mesh) -> MeshInstance3D:
	var made := MeshInstance3D.new()
	made.mesh = mesh
	made.material_override = _material
	# (its body swings out past the still model's box)
	made.extra_cull_margin = LENGTH * 0.1
	made.name = called
	add_child(made)
	return made
