class_name Ammonite
extends Node3D
## An ammonite, 0.4 m across its shell: a ribbed shell coiled tightly in one plane, cream with
## reddish-brown flames and a pearly sheen, and out of its opening a rounded head with two big
## eyes, a thick leathery hood over it and ten short tentacles trailing back.
##
## How it looks and moves only: whatever moves it puts it where it is and turns it the way it
## goes. IT JETS SHELL FIRST: its -Z (Godot's forward, so `look_at` points it) is the way it
## goes, the shell's outer edge leading; the opening, the head and the tentacles face +Z, behind
## it. It hangs shell-up, the coil's axis along its X, the opening at the bottom of the coil.
## Its origin is the middle of the shell's outline (half way from its front to its back and from
## its top to its bottom), on its middle plane. `scale` it for a bigger or smaller one. No sound.
##
## Everything moves in the shader (no bones), on `phase`, 0 to 1 through one `beat`: one jet, in
## which it rocks and bobs a little, its head draws in and its tentacles bunch, then trail and curl
## again. `withdraw` (0 to 1) pulls its head and tentacles into the shell and turns the hood down
## over the opening. Either call `step(velocity, delta)` each frame, which moves `phase` on by
## delta / beat, or set `phase` yourself.
##
## The models are creatures/ammonite/models/ammonite.glb (and _game, _lo), built by
## tools/build_ammonite.py; ammonite.gdshader draws the markings and moves it.

const MODEL := "res://creatures/ammonite/models/ammonite%s.glb"
const SHADER := preload("res://creatures/ammonite/ammonite.gdshader")
## As the model is built (tools/build_ammonite.py), metres at scale 1: across the shell at its
## widest (from its top to its bottom, through the coil), how deep it is along the way it goes
## (front to back, the tentacles not counted) and how wide (side to side).
const LENGTH := 0.4
const DEPTH := 0.33
const WIDTH := 0.109
## How far its tentacles reach behind its origin and below it.
const TENTACLE_REACH := Vector2(0.174, 0.257)

## Seconds one beat takes (one jet).
@export var beat := 1.6
## How strongly it rocks, bobs and jets and its tentacles trail and curl: 1 swimming, 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## Its head and tentacles: 0 out, 1 pulled right into the shell behind the hood.
@export_range(0.0, 1.0) var withdraw := 0.0:
	set(value):
		withdraw = clampf(value, 0.0, 1.0)
		_send(&"withdraw", withdraw)
## The low model (about a tenth of the triangles), for far off or for several of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (Twilight Princess weight: about 1,800 triangles, spent on the outline; the same
## shader and settings) in place of the full one; `low` still shows the low model. Each model is
## loaded only when it is first shown, so with `game` on the full model is never loaded and a
## game's web export may leave ammonite.glb out.
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye: 0 the eye as in life, 1 a bigger cartoon eye of its own character (old, slow
## and kindly: a heavy drooping lid over an amber eye with a bar of a pupil). In between blends.
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = clampf(value, 0.0, 1.0)
		_send(&"cartoon_eyes", cartoon_eyes)
## Where its pupils look, -1..1 each way: x towards its front (where its tentacles reach), y up,
## in each eye's own plane.
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value.clamp(Vector2(-1.0, -1.0), Vector2.ONE)
		_send(&"eye_look", eye_look)
## A blink: 0 open, 1 shut (lids the colour of its skin close over each eye).
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


## The full model's mesh, or the low one's (each one surface, to wear `new_material()`). Loaded
## once and kept.
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % ("_lo" if low_wanted else ""))


## The game model's mesh (see `game`), one surface, to wear `new_material()`. Loaded once and kept.
## (Without the lower levels of detail Godot's importer makes: thinned from the still model, its
## curling tentacles would bend in straight pieces far off.)
static func game_mesh() -> Mesh:
	return _mesh_at(MODEL % "_game", true)


static func _mesh_at(path: String, plain := false) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = without_lods(found.mesh) if plain else found.mesh
		made.free()
	return _meshes[path]


## `mesh` again without the lower levels of detail Godot's importer makes for it.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var bare := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		bare.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return bare


## A new material for `mesh_of()`'s meshes. Its shader settings are the game's to set: `phase`
## (0..1 through one beat), `sway`, `withdraw` and the colours (the top of the shader lists them).
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	_full = _instance_of("Ammonite")
	_low = _instance_of("AmmoniteLo")
	_game = _instance_of("AmmoniteGame")
	_show()
	_send(&"phase", phase)
	_send(&"sway", sway)
	_send(&"withdraw", withdraw)
	_send(&"cartoon_eyes", cartoon_eyes)
	_send(&"eye_look", eye_look)
	_send(&"blink", blink)


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the other animals' are; set `beat` and `sway`
## from its speed yourself.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: its colours (`cream`, `flame`, `skin`, `hide`, `tentacle`),
## `flames_show`, `pearl` (how pearly the shell is), or `sway`, `withdraw` for a game's own material.
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (both models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


func _show() -> void:
	if _full == null:
		return
	_full.visible = not low and not game
	_low.visible = low
	_game.visible = game and not low
	# (each model is loaded the first time it is shown, never before)
	if _full.visible and _full.mesh == null:
		_full.mesh = mesh_of(false)
	if _low.visible and _low.mesh == null:
		_low.mesh = mesh_of(true)
	if _game.visible and _game.mesh == null:
		_game.mesh = game_mesh()


func _instance_of(called: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.material_override = _material
	# (it rocks and bobs, and its tentacles swing, past where the still model ends)
	mesh.extra_cull_margin = 0.05
	mesh.name = called
	add_child(mesh)
	return mesh
