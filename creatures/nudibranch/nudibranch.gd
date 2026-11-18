class_name Nudibranch
extends Node3D
## A nudibranch: a Spanish shawl (Flabellinopsis iodinea), 0.07 m long. A slim vivid violet sea
## slug with a mane of bright orange finger-like cerata along its back, two scarlet ringed
## rhinophores on its head and two long violet oral tentacles reaching forward.
##
## How it looks and moves only: whatever moves it puts it where it is and turns it the way it
## goes. Its head points along its own -Z (Godot's forward). **Its origin is on the ground under
## its middle** (it is a bottom animal: its foot lies on y = 0), so it reaches 0.035 m ahead and
## 0.035 m behind. It is life size: `scale` it up for a game. No sound.
##
## It crawls with a slow ripple running back along its body and its cerata waving. It can also
## swim, as Spanish shawls do: flexing its whole body to one side into a U, then to the other.
## `swim` 0..1 blends from crawling to that (a game lifts it off the bottom itself).
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which it ripples (or
## strokes) `tail_beats` times (a whole number), so its motion comes round again exactly every
## beat. Either call `step(velocity, delta)` each frame, which moves `phase` on by delta / beat,
## or set `phase` yourself. The same names as GameCommon's fish, so it is driven the same way.
## It has no `gape` and no `curl`.
##
## It has no `cartoon_eyes`: a Spanish shawl's eyes are specks under its skin, and the model has none.
##
## The model is creatures/nudibranch/models/nudibranch.glb (and _game, _lo), built by
## tools/build_nudibranch.py; nudibranch.gdshader colours it and moves it.

const MODEL := "res://creatures/nudibranch/models/nudibranch%s.glb"
const SHADER := preload("res://creatures/nudibranch/nudibranch.gdshader")
## As the model is built (tools/build_nudibranch.py): from the front of its head to the tip of
## its tail, and how high and how wide its body is without what stands on it (metres, at scale 1).
const LENGTH := 0.07
const DEPTH := 0.008
const WIDTH := 0.01

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 2.4
## How many times in a beat its ripple runs (crawling) or it strokes there and back (swimming).
@export var tail_beats := 1:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How strongly it moves: 1 as it lives, 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## 0 crawling on the bottom, 1 swimming (flexing into a U one way, then the other).
@export_range(0.0, 1.0) var swim := 0.0:
	set(value):
		swim = clampf(value, 0.0, 1.0)
		_send(&"swim", swim)
## The low model (about an eleventh of the triangles), for far off or for several of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (Twilight Princess weight: about 900 triangles, spent on the outline; the same
## shader and settings) in place of the full one; `low` still shows the low model. Each model is
## loaded only when it is first shown, so with `game` on the full model is never loaded and a
## game's web export may leave nudibranch.glb out.
@export var game := false:
	set(value):
		game = value
		_show()
## How far through a beat it is, 0 to 1 (only the fraction counts). `step` moves it on; or set
## it yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send_phase()

static var _meshes := {}

var _material: ShaderMaterial
var _full: MeshInstance3D
var _low: MeshInstance3D
var _game: MeshInstance3D


## `mesh` again without the lower levels of detail Godot's importer makes for it: they are made
## from the still model and thin its body to a few rings, which then bend in straight pieces.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain


## The full model's mesh, or the low one's (each one surface, to wear `new_material()`): for
## drawing one without this node.
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % ("_lo" if low_wanted else ""))


## The game model's mesh (see `game`), one surface, to wear `new_material()`. Loaded once and kept.
static func game_mesh() -> Mesh:
	return _mesh_at(MODEL % "_game")


static func _mesh_at(path: String) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = without_lods(found.mesh)
		made.free()
	return _meshes[path]


## A new material for `mesh_of()`'s meshes. Its shader settings are the game's to set: `phase`
## (0..1 through one ripple or stroke), `swim`, `sway`, and those `set_shader_parameter` lists.
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	_full = _instance_of("Nudibranch")
	_low = _instance_of("NudibranchLo")
	_game = _instance_of("NudibranchGame")
	_show()
	_send_phase()
	_send(&"sway", sway)
	_send(&"swim", swim)


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the fish's are, and is not used: set `swim`,
## `sway` and `beat` yourself.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `flex` (how far round it bends at the height of a swimming
## stroke: radians from head to tail, 2.7), `ripples` (how many lie along its body as it crawls),
## its colours (`body`, `body_pale`, `cerata`, `cerata_tip`, `rhinophore`) and `vivid` (how much
## of its colour shows with no light on it).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (both models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


func _send_phase() -> void:
	_send(&"phase", fposmod(phase * tail_beats, 1.0))


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
	# (swimming, its ends come round to one side past where the still model ends)
	mesh.extra_cull_margin = 0.03
	mesh.name = called
	add_child(mesh)
	return mesh
