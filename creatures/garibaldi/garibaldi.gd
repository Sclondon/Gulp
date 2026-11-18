class_name Garibaldi
extends Node3D
## A garibaldi (Hypsypops rubicundus), the big damselfish of Californian reefs, 0.3 m long: a
## deep oval body, vivid orange all over, with big scales, a steep blunt head, a small mouth
## with full lips, yellow eyes, a dorsal and an anal fin whose soft lobes trail back, and a
## heart-shaped tail.
##
## It rows with its pectoral fins, both together, its body held all but still: `sway` is 0.3
## as it comes (raise it when it hurries, and its tail works).
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it
## goes. Its nose points along its own -Z (Godot's forward), its belly down; its origin is on
## its middle line, half way along its length. `scale` it for a bigger or smaller one. No sound.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its tail beats
## `tail_beats` times (a whole number) and its pectoral fins scull as often, so its motion comes
## round again exactly every beat. Either call `step(velocity, delta)` each frame, which moves
## `phase` on by delta / beat, or set `phase` yourself (for a picture that must loop). The same
## names and meanings as GameCommon's yellowfin tuna and sardine.
##
## Its mouth opens: `gape` 0 shut to 1 wide, as when it bites (the lower jaw swings down about
## its hinge, the snout lifts a little, the dark inside of the mouth shows).
##
## The model is creatures/garibaldi/models/garibaldi.glb (and _lo, far off, and _game, the game model), built by
## tools/build_garibaldi.py; garibaldi.gdshader draws its markings and moves it (no bones).

const MODEL := "res://creatures/garibaldi/models/garibaldi%s.glb"
const SHADER := preload("res://creatures/garibaldi/garibaldi.gdshader")
## As the model is built (tools/build_garibaldi.py): from the tip of its snout to the tips of its
## tail, and how deep and how wide its body is at its deepest (metres, at scale 1).
const LENGTH := 0.3
const DEPTH := 0.126
const WIDTH := 0.042

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 1.5
## How many times in a beat its tail beats and its pectoral fins scull (there and back).
@export var tail_beats := 2:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How widely its body and tail beat: 1 cruising, 0 still (hovering on its pectoral fins alone).
@export_range(0.0, 2.0) var sway := 0.3:
	set(value):
		sway = value
		_send(&"sway", value)
## How hard its pectoral fins scull: 1 as it hovers or cruises, 0 folded in and still.
@export_range(0.0, 2.0) var scull := 1.0:
	set(value):
		scull = value
		_send(&"scull", value)
## Its mouth: 0 shut, 1 wide open, as when it bites.
@export_range(0.0, 1.0) var gape := 0.0:
	set(value):
		gape = value
		_send(&"gape", value)
## How far the spines of its dorsal fin are raised: 1 up, 0 folded back.
@export_range(0.0, 1.0) var dorsal := 1.0:
	set(value):
		dorsal = value
		_send(&"dorsal", value)
## The low model (about a twelfth of the triangles), for far off or for many of them.
@export var low := false:
	set(value):
		low = value
		_show()
## The game model (Twilight Princess weight: a few thousand triangles, spent on its outline, eye,
## lips and fin edges) in place of the full one. `low` still shows the low model. With it on the
## full model is never loaded.
@export var game := false:
	set(value):
		game = value
		_show()
## The cartoon eye: 0 its eye as it is, 1 bigger, with a white, a big pupil, a highlight and a lid
## line of its own (see the README for its character).
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = value
		_send(&"cartoon_eyes", value)
## Where the cartoon eye looks, -1..1 each way: x towards its snout (+) or its tail (-), y up or down.
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value
		_send(&"eye_look", value)
## The cartoon eye's blink: 0 open, 1 shut.
@export_range(0.0, 1.0) var blink := 0.0:
	set(value):
		blink = value
		_send(&"blink", value)
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


## The full model's mesh, or the low one's (each one surface, to wear `new_material()`): for
## drawing one without this node.
static func mesh_of(low_wanted := false) -> Mesh:
	var path := MODEL % ("_lo" if low_wanted else "")
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = found.mesh
		made.free()
	return _meshes[path]


## The game model's mesh (one surface, to wear `new_material()`), without the thinned copies
## Godot's importer makes for far off (a body bent in the vertex shader would bend in straight
## pieces): for drawing one without this node.
static func game_mesh() -> Mesh:
	var path := MODEL % "_game"
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = without_lods(found.mesh)
		made.free()
	return _meshes[path]


## A copy of `mesh` without its level-of-detail meshes.
static func without_lods(mesh: Mesh) -> ArrayMesh:
	var plain := ArrayMesh.new()
	for surface in mesh.get_surface_count():
		plain.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, mesh.surface_get_arrays(surface))
	return plain


## A new material for `mesh_of()`'s meshes. Its shader settings are the game's to set: `phase`
## (0..1 through one beat of the tail), `sway`, `scull`, `gape`, `dorsal`, `curl`, `wave` and
## the colours (the top of the shader lists them).
static func new_material() -> ShaderMaterial:
	var made := ShaderMaterial.new()
	made.shader = SHADER
	return made


func _init() -> void:
	_material = new_material()


func _ready() -> void:
	# (deferred: what is set just after it enters the tree, `game` and `low` among them, comes
	# first, so that a model it will not show is never loaded)
	_show.call_deferred()
	_send_phase()
	for setting: StringName in [&"sway", &"scull", &"gape", &"dorsal", &"cartoon_eyes", &"eye_look", &"blink"]:
		_send(setting, get(setting))


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the other fish's are; its beat here does not
## change with its speed: set `sway`, `scull` and `beat` for that.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `curl` (bends the body round to one side behind the head,
## radians from gills to tail; more than 0 and the tail comes round to +X), `wave` (the length
## of the wave along its body), `mouth` (the colour inside its mouth) and its colours
## (`orange`, `deep`, `light`, `iris`, `iris_ring`, and `scale_show`, how strongly its scales show).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (every model wears it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (the shader is given how far through one beat of the tail it is)
func _send_phase() -> void:
	_send(&"phase", fposmod(phase * tail_beats, 1.0))


# (each model is loaded only when it is first shown: a game showing only the game model never
# loads the full one)
func _show() -> void:
	if not is_inside_tree():
		return
	var which := "_lo" if low else ("_game" if game else "")
	if which == "" and _full == null:
		_full = _instance_of(which)
	elif which == "_lo" and _low == null:
		_low = _instance_of(which)
	elif which == "_game" and _game == null:
		_game = _instance_of(which)
	for shown: MeshInstance3D in [_full, _low, _game]:
		if shown:
			shown.visible = shown == (_low if low else (_game if game else _full))


func _instance_of(which: String) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = game_mesh() if which == "_game" else mesh_of(which == "_lo")
	mesh.material_override = _material
	# (its tail and fins swing out past where the still model ends)
	mesh.extra_cull_margin = LENGTH * 0.25
	mesh.name = "Garibaldi" + {"": "", "_lo": "Lo", "_game": "Game"}[which]
	add_child(mesh)
	return mesh
