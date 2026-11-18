class_name Anomalocaris
extends Node3D
## An anomalocaris (Anomalocaris canadensis, of the Cambrian seas), 0.8 m from the front of its
## head to the tips of its tail fan: a flattened, segmented reddish-brown body with a row of paler
## swimming lobes down each side, a fan of three pairs of blades at its tail, two big compound eyes
## on stalks, two spiny grasping arms curled under its head and a round mouth of radial plates
## beneath.
##
## How it looks and moves only: whatever moves it puts it where it is and turns it the way it
## goes. Its head points along its own -Z (Godot's forward), its back up; its origin is on its
## middle line half way from the front of its head to the tips of its tail fan. `scale` it for a
## bigger or smaller one. No sound.
##
## Everything moves in the shader (no bones), on `phase`, 0 to 1 through one `beat`: in a beat its
## lobes make one stroke, in a wave running back along each side, and a gentle wave runs down its
## body to the tail fan. `grasp` (0 to 1) reaches its arms out ahead from their curl: drive it up
## and back down for a strike. Either call `step(velocity, delta)` each frame, which moves `phase`
## on by delta / beat, or set `phase` yourself.
##
## The models are creatures/anomalocaris/models/anomalocaris.glb (and _lo, and _game), built by
## tools/build_anomalocaris.py; anomalocaris.gdshader draws the markings and moves it.

const MODEL := "res://creatures/anomalocaris/models/anomalocaris%s.glb"
const SHADER := preload("res://creatures/anomalocaris/anomalocaris.gdshader")
## As the model is built (tools/build_anomalocaris.py), metres at scale 1: from the front of its
## head to the tips of its tail fan, how deep its body is (at the head) and how wide (at its widest,
## the lobes not counted).
const LENGTH := 0.8
const DEPTH := 0.057
const WIDTH := 0.128
## How far its lobes reach out to each side; how far below its middle line its curled arms hang;
## how far ahead of its origin its arms reach at `grasp` 1.
const SPAN := 0.149
const ARMS_BELOW := 0.111
const GRASP_REACH := 0.55

## Seconds one beat takes (one stroke of its lobes).
@export var beat := 0.9
## How strongly its body waves and its tail fan sways: 1 swimming, 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How widely its lobes beat: 0 still, 1 swimming.
@export_range(0.0, 1.5) var flap := 1.0:
	set(value):
		flap = value
		_send(&"flap", value)
## Its arms: 0 curled down and back under its head, 1 reaching straight out ahead.
@export_range(0.0, 1.0) var grasp := 0.0:
	set(value):
		grasp = clampf(value, 0.0, 1.0)
		_send(&"grasp", grasp)
## The low model (about a seventeenth of the full one's triangles), for far off or for several.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (about a twelfth of the full one's triangles, spent where the eye looks: the
## outline of its body and lobes, the eyes, the spiny arms), shown in place of the full one; `low`
## still shows the low model. Each model is loaded only when it is first shown: with `game` on,
## the full model is never loaded.
@export var game := false:
	set(value):
		game = value
		_show()
## 0 its eyes as they are; 1 cartoon eyes (big, glossy and hungry: see the README).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = clampf(value, 0.0, 1.0)
		_send(&"cartoon_eyes", cartoon_eyes)
## Where its cartoon eyes look, -1..1 each way: x towards its front (+) or its tail, y up or down.
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value.clamp(-Vector2.ONE, Vector2.ONE)
		_send(&"eye_look", eye_look)
## A blink: 0 open, 1 shut (a lid the colour of its skin comes down over each eye).
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = clampf(value, 0.0, 1.0)
		_send(&"blink", blink)
## How far through a beat it is, 0 to 1 (only the fraction counts).
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send(&"phase", phase)

static var _meshes := {}

var _material: ShaderMaterial
var _full: MeshInstance3D
var _low: MeshInstance3D
var _game: MeshInstance3D


## The full model's mesh, or the low one's (each one surface, to wear `new_material()`).
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % ("_lo" if low_wanted else ""))


## The game model's mesh (one surface, to wear `new_material()`), without the importer's automatic
## LODs (a body bent in the shader would bend in straight pieces far off).
static func game_mesh() -> Mesh:
	return _mesh_at(MODEL % "_game", true)


## A copy of `mesh` without its automatic LODs.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain


static func _mesh_at(path: String, plain := false) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = without_lods(found.mesh) if plain else found.mesh
		made.free()
	return _meshes[path]


## A new material for these meshes. Its shader settings are the game's to set: `phase` (0..1
## through one beat), `sway`, `flap`, `grasp`, `cartoon_eyes`, `eye_look`, `blink` and the colours
## (the top of the shader lists them).
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	_show()
	_send(&"phase", phase)
	_send(&"sway", sway)
	_send(&"flap", flap)
	_send(&"grasp", grasp)
	_send(&"cartoon_eyes", cartoon_eyes)
	_send(&"eye_look", eye_look)
	_send(&"blink", blink)


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the other animals' are; set `beat`, `sway` and
## `flap` from its speed yourself.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: its colours (`body_colour`, `lobe_colour`, `dark`, `pale`),
## or `sway`, `flap`, `grasp`, `cartoon_eyes`, `eye_look`, `blink` for a game's own material.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (every model wears it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# Shows the model wanted, making (and loading) it the first time it is wanted.
func _show() -> void:
	if not is_inside_tree():
		return
	if low and not _low:
		_low = _instance_of(mesh_of(true), "AnomalocarisLo")
	elif not low and game and not _game:
		_game = _instance_of(game_mesh(), "AnomalocarisGame")
	elif not low and not game and not _full:
		_full = _instance_of(mesh_of(false), "Anomalocaris")
	for shown: MeshInstance3D in [_full, _low, _game]:
		if shown:
			shown.visible = shown == (_low if low else (_game if game else _full))


func _instance_of(mesh_wanted: Mesh, named: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = mesh_wanted
	mesh.material_override = _material
	# (its lobes beat and its arms reach out past where the still model ends)
	mesh.extra_cull_margin = 0.2
	mesh.name = named
	add_child(mesh)
	return mesh
