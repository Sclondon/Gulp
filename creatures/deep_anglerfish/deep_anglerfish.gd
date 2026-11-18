class_name DeepAnglerfish
extends Node3D
## A female humpback anglerfish, or black seadevil (Melanocetus johnsonii), 0.30 m long: a black globe of a
## body, a huge upturned mouth of long glassy needle teeth, tiny eyes, small rounded fins, and a rod (illicium) on
## its snout ending in a bulb (esca) that glows blue-white. (Not GameCommon's `anglerfish`, a monster made for
## another game.)
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it goes. Its nose
## points along its own -Z (Godot's forward), its belly down; its origin is on its middle line at the height of
## the tail, half way along, so it reaches 0.15 m ahead and 0.15 m behind. `scale` it for a bigger one (a game
## may well want it much bigger than life). No sound.
##
## The swimming, the mouth (`gape`), the rod's sway and flick (`flick`) and the light of the lure (`lure`,
## `glow`) are all drawn by the shader (no bones), and run on `phase`, 0 to 1 through one `beat`, in which its
## tail beats `tail_beats` times (a whole number), so its motion comes round again exactly every beat. Either call
## `step(velocity, delta)` each frame, which moves `phase` on by delta / beat, or set `phase` yourself (for a
## picture that must loop: frame / frames in a beat). The same names and meanings as GameCommon's yellowfin tuna
## and sardine, so they are driven the same way.
##
## The models are creatures/deep_anglerfish/models/deep_anglerfish.glb (and _lo), built by
## tools/build_deep_anglerfish.py; deep_anglerfish.gdshader draws the markings, swims it and lights the lure.

const MODEL := "res://creatures/deep_anglerfish/models/deep_anglerfish%s.glb"
const SHADER := preload("res://creatures/deep_anglerfish/deep_anglerfish.gdshader")
## As the model is built (tools/build_deep_anglerfish.py): from the tip of its jaw to the edge of its tail, and
## how deep and how wide its body is at its deepest (metres, at scale 1).
const LENGTH := 0.30
const DEPTH := 0.164
const WIDTH := 0.128
## Where the middle of the lure's bulb is with the rod at rest (in the node's own space, at scale 1): for a
## game that puts a light there.
const LURE_AT := Vector3(0.0, 0.1147, -0.1929)

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 1.6
## How many times in a beat its tail beats (there and back).
@export var tail_beats := 2:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How widely it beats: 1 as one drifting along, 0 still.
@export_range(0.0, 2.0) var sway := 1.0:
	set(value):
		sway = value
		_send(&"sway", value)
## How far its mouth is open: 0 shut, 1 wide open (as when it strikes).
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = clampf(value, 0.0, 1.0)
		_send(&"gape", gape)
## How bright the lure is: 0 dark, 1 lit.
@export_range(0.0, 1.0) var lure := 1.0:
	set(value):
		lure = clampf(value, 0.0, 1.0)
		_send(&"lure", lure)
## How strongly its light glows (0 none, 1 as made, 2 twice as bright).
@export_range(0.0, 2.0) var glow := 1.0:
	set(value):
		glow = clampf(value, 0.0, 2.0)
		_send(&"glow", glow)
## How hard the rod is flicked forward once each beat of the tail (0 never: it only sways).
@export_range(0.0, 1.0) var flick := 0.0:
	set(value):
		flick = clampf(value, 0.0, 1.0)
		_send(&"flick", flick)
## The cartoon eye (0 the eye as made, 1 the cartoon one: a tiny mean dot under a scowling lid).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = clampf(value, 0.0, 1.0)
		_send(&"cartoon_eyes", cartoon_eyes)
## Where the cartoon eye looks: x towards the snout (more than 0) or the tail, y up or down; -1..1.
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value.clamp(Vector2(-1.0, -1.0), Vector2(1.0, 1.0))
		_send(&"eye_look", eye_look)
## The cartoon eye's lid: 0 open, 1 shut.
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = clampf(value, 0.0, 1.0)
		_send(&"blink", blink)
## The low model (about a twelfth of the triangles), for far off or for several of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (about a ninth of the full model's triangles, spent on the outline, the eye, the mouth and the
## lure) in place of the full one: what a game draws near. `low` still shows the low model. With it on, the full
## model is never loaded (each model is loaded when it is first shown).
@export var game := false:
	set(value):
		game = value
		_show()
## How far through a beat it is, 0 to 1 (only the fraction counts). `step` moves it on; or set it yourself.
var phase := 0.0:
	set(value):
		phase = fposmod(value, 1.0)
		_send_phase()

static var _meshes := {}

var _material: ShaderMaterial
var _full: MeshInstance3D
var _low: MeshInstance3D
var _game: MeshInstance3D
var _started := false


## The full model's mesh, or the low one's (each one surface, to wear `new_material()`): for drawing one
## without this node.
static func mesh_of(low_wanted := false) -> Mesh:
	return _mesh_at(MODEL % ("_lo" if low_wanted else ""))


## The game model's mesh (one surface, to wear `new_material()`): for drawing one without this node.
static func game_mesh() -> Mesh:
	return _mesh_at(MODEL % "_game")


## A new material for `mesh_of()`'s meshes. Its shader settings are the game's to set: `phase` (0..1 through one
## beat of the tail), `sway`, `gape`, `curl`, `lure`, `glow`, `flick`, `rod_lean` and the colours (the top of the
## shader lists them).
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	_started = true
	_show()
	_send_phase()
	_send(&"sway", sway)
	_send(&"gape", gape)
	_send(&"lure", lure)
	_send(&"glow", glow)
	_send(&"flick", flick)
	_send(&"cartoon_eyes", cartoon_eyes)
	_send(&"eye_look", eye_look)
	_send(&"blink", blink)


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat. (`velocity` is
## taken so that it is called as the other fish's are; set `sway` and `beat` from its speed yourself.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `curl` (bent round into a turn: radians from gills to tail, more than 0 the
## tail comes round to its left, +X), `rod_lean` (the rod leant forward, radians), its colours (`skin`,
## `skin_brown`, `fin`, `mouth_inside`, `tooth`, `rod_tip`, `bulb`, `lure_light`).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (both models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (the shader is given how far through one beat of the tail it is)
func _send_phase() -> void:
	_send(&"phase", fposmod(phase * tail_beats, 1.0))


func _show() -> void:
	if not _started:
		return
	var which := "_lo" if low else ("_game" if game else "")
	# (each model is loaded the first time it is shown, so that a game with `game` on never loads the full one)
	if which == "" and _full == null:
		_full = _instance_of(which)
	if which == "_lo" and _low == null:
		_low = _instance_of(which)
	if which == "_game" and _game == null:
		_game = _instance_of(which)
	if _full:
		_full.visible = which == ""
	if _low:
		_low.visible = which == "_lo"
	if _game:
		_game.visible = which == "_game"


func _instance_of(which: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = _mesh_at(MODEL % which)
	mesh.material_override = _material
	# (its tail and rod swing out past where the still model ends, and the jaw drops below it)
	mesh.extra_cull_margin = 0.08
	mesh.name = "DeepAnglerfish" + which
	add_child(mesh)
	return mesh


## The mesh as imported but without the thinned LOD meshes Godot's importer adds: those were made from the still
## model, and a body bent in the shader then bends in straight pieces far off.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain


static func _mesh_at(path: String) -> Mesh:
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		# (the game model without the importer's LODs; the full and low ones as they always were)
		_meshes[path] = without_lods(found.mesh) if path.ends_with("_game.glb") else found.mesh
		made.free()
	return _meshes[path]
