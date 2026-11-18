class_name YellowPerch
extends Node3D
## A yellow perch (Perca flavescens), 0.3 m long: an oval, humped body, golden yellow with six to
## eight dark olive bars across its sides (broad on the back, narrowing to points below its middle),
## an olive back and a cream belly; two separate dorsal fins, the first of spines with a black
## blotch at its back, the second soft; orange-red pelvic and anal fins; clear amber pectoral fins;
## a lightly forked tail.
##
## It swims with its body and tail (a wave down its rear half) and sculls with its pectoral
## fins, which row in turn; with `sway` 0 it hovers on them alone.
##
## How it looks and swims only: whatever moves it puts it where it is and turns it the way it
## goes. Its nose points along its own -Z (Godot's forward), its belly down; its origin is on
## its middle line, half way along its length. `scale` it for a bigger or smaller one. No sound.
##
## Everything that moves runs on `phase`, 0 to 1 through one `beat`, in which its tail beats
## `tail_beats` times (a whole number) and its pectoral fins scull as often, so its motion comes
## round again exactly every beat. Either call `step(velocity, delta)` each frame, which moves
## `phase` on by delta / beat, or set `phase` yourself (for a picture that must loop). The same
## names and meanings as GameCommon's yellowfin tuna, snapper and walleye.
##
## Its mouth opens: `gape` 0 shut to 1 wide, as when it bites (the lower jaw swings down about
## its hinge, the snout lifts a little, the dark inside of the mouth shows).
##
## The models are creatures/yellow_perch/models/yellow_perch.glb (the full one),
## yellow_perch_game.glb (the game model, at Twilight Princess weight) and yellow_perch_lo.glb
## (far off), built by tools/build_yellow_perch.py; yellow_perch.gdshader draws its markings
## and moves it (no bones).

const MODEL := "res://creatures/yellow_perch/models/yellow_perch%s.glb"
const SHADER := preload("res://creatures/yellow_perch/yellow_perch.gdshader")
## As the model is built (tools/build_yellow_perch.py): from the tip of its snout to the tips of
## its tail, and how deep and how wide its body is at its deepest (metres, at scale 1).
const LENGTH := 0.3
const DEPTH := 0.08
const WIDTH := 0.035

## Seconds one beat takes: everything it does comes round again each beat.
@export var beat := 1.2
## How many times in a beat its tail beats and its pectoral fins scull (there and back).
@export var tail_beats := 2:
	set(value):
		tail_beats = maxi(value, 0)
		_send_phase()
## How widely its body and tail beat: 1 cruising, 0 still (hovering on its pectoral fins alone).
@export_range(0.0, 2.0) var sway := 1.0:
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
## How far the spines of its first dorsal fin are raised: 1 up, 0 folded back.
@export_range(0.0, 1.0) var dorsal := 1.0:
	set(value):
		dorsal = value
		_send(&"dorsal", value)
## The low model (about a tenth of the triangles), for far off or for many of them.
## The game model (a tenth or so of the full model's triangles, spent on its outline, eye, mouth
## and fin edges: the same look and the same settings), in place of the full one. With `game` on
## the full model is never loaded (each model is loaded only when first shown), so a game's web
## export can leave the full .glb out. `low` still wins over it.
@export var game := false:
	set(value):
		game = value
		_show()
@export var low := false:
	set(value):
		low = value
		_show()
## The cartoon eye: 0 the eye as it is, 1 bigger, with a white, an iris, a big pupil, a shine,
## a dark outline and lids of its own character (Gulp sets 1). See the README.
@export_range(0.0, 1.0) var cartoon_eyes := 0.0:
	set(value):
		cartoon_eyes = value
		_send(&"cartoon_eyes", value)
## Where the cartoon eye looks, -1..1 each way: x more than 0 forward (towards its snout), y up.
@export var eye_look := Vector2.ZERO:
	set(value):
		eye_look = value
		_send(&"eye_look", value)
## A blink: 0 open, 1 shut (the eye squashes flat; the cartoon eye's lid comes down over it).
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
# (the full, low and game models' nodes, each made when first shown)
var _models: Array[MeshInstance3D] = [null, null, null]


## The full model's mesh, or the low one's (each two surfaces, the body and the throat with its gills,
## both to wear `new_material()`): for
## drawing one without this node.
static func mesh_of(low_wanted := false) -> Mesh:
	var path := MODEL % ("_lo" if low_wanted else "")
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = found.mesh
		made.free()
	return _meshes[path]


## The game model's mesh (one surface, to wear `new_material()`; without the importer's LOD meshes,
## which would bend in straight pieces far off): for drawing one without this node.
static func game_mesh() -> Mesh:
	var path := MODEL % "_game"
	if not _meshes.has(path):
		var made := (load(path) as PackedScene).instantiate()
		var found: MeshInstance3D = made.find_children("*", "MeshInstance3D", true, false)[0]
		_meshes[path] = without_lods(found.mesh)
		made.free()
	return _meshes[path]


## `mesh` again without its LOD meshes.
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
	_pick()
	_send_phase()
	for setting: StringName in [&"cartoon_eyes", &"eye_look", &"blink", &"sway", &"scull", &"gape", &"dorsal"]:
		_send(setting, get(setting))


## Each frame, for one that is not having its `phase` set for it: moves it on through its beat.
## (`velocity` is taken so that it is called as the other fish's are; its beat here does not
## change with its speed: set `sway`, `scull` and `beat` for that.)
func step(_velocity: Vector3, delta: float) -> void:
	phase += delta / maxf(beat, 0.01)


## Sets one of the shader's settings: `curl` (bends the body round to one side behind the head,
## radians from gills to tail; more than 0 and the tail comes round to +X), `wave` (the length
## of the wave along its body), `mouth` (the colour inside its mouth), `bar_count` and its
## colours (`back`, `flank`, `belly`, `bars`, `fin_red`, `fin`, `fin_clear`, `blotch`, `iris`,
## `iris_ring`).
func set_shader_parameter(setting: StringName, value: Variant) -> void:
	_material.set_shader_parameter(setting, value)


## Its one material (all three models wear it).
func material() -> ShaderMaterial:
	return _material


func _send(setting: StringName, value: Variant) -> void:
	if _material:
		_material.set_shader_parameter(setting, value)


# (the shader is given how far through one beat of the tail it is)
func _send_phase() -> void:
	_send(&"phase", fposmod(phase * tail_beats, 1.0))


func _show() -> void:
	if is_node_ready():
		_pick()


# (shows the model wanted, making its node the first time)
func _pick() -> void:
	var which := 1 if low else (2 if game else 0)
	if _models[which] == null:
		_models[which] = _instance_of(which)
	for i in _models.size():
		if _models[i]:
			_models[i].visible = i == which


func _instance_of(which: int) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	mesh.mesh = game_mesh() if which == 2 else mesh_of(which == 1)
	mesh.material_override = _material
	# (its tail and fins swing out past where the still model ends)
	mesh.extra_cull_margin = LENGTH * 0.25
	mesh.name = ["YellowPerch", "YellowPerchLo", "YellowPerchGame"][which]
	add_child(mesh)
	return mesh
